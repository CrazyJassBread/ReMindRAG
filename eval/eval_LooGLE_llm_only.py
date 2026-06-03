import sys
sys.path.append('../')

from datasets import load_dataset
from ReMindRag.llms import OpenaiAgent

import json
from datetime import datetime
import os
import argparse


def main():
    parser = argparse.ArgumentParser(description='Run LooGLE LLM-only Test')
    parser.add_argument('--title_index', type=int, required=True, help='Test Index')
    parser.add_argument('--test_name', type=str, default='llm-only-mimov2.5', help='Test Name')
    parser.add_argument('--data_type', type=str, choices=['longdep_qa', 'shortdep_qa'], help='Data Type: longdep_qa or shortdep_qa')
    parser.add_argument('--question_type', type=str, choices=['origin', 'similar'], help='Question Type: origin or similar')
    parser.add_argument('--model_name', type=str, default='mimo-v2.5', help='Backbone Model Name')
    parser.add_argument('--judge_model_name', type=str, default=None, help='Model name for answer rewrite/check')
    parser.add_argument('--system_prompt', type=str, default=None, help='Optional system prompt for the LLM')
    parser.add_argument('--use_context', action='store_true', help='If set, prepend the full context to the question')
    args = parser.parse_args()

    title_index = args.title_index
    test_name = args.test_name
    data_type = args.data_type
    model_name = args.model_name
    judge_model_name = args.judge_model_name or model_name
    question_type = args.question_type
    system_prompt = args.system_prompt
    use_context = args.use_context

    if system_prompt is None:
        system_prompt = (
            'You are a QA assistant. Answer the question concisely. '
            'If you are unsure, respond with "I don\'t know".'
        )

    print(f"Model name: {model_name}")
    print(f"Judge model name: {judge_model_name}")
    print(f"Data type: {data_type}")
    print(f"Use context: {use_context}")

    response_format = """
Origin Query: {query}
LLM Output: {output}

Reference Chunks: []
Reference Edges: []

"""

    ans_check_prompt = """
Given one question, there is a groundtruth and a predict answer.
Please decide whether they are the same or not in semantic.
Please only output True or False.
Question: {question}
groundtruth = {reference_answer}
predicted answer = {generated_output}

Only output one word(True or False), without any additional content.
"""

    ans_rewrite_prompt = """
Instruction: Given a question and an original answer, please rewrite the original answer. If the original answer is not related to any option in the question, output "I don't know". Otherwise, rewrite the answer to only contain the actual response to the question without any related analysis or references.
If the Original answer outputs "I don't know", directly output "I don't know".
Please output the rewritten answer directly.
Question = {question}
Original answer = {generated_answer}
"""

    with open('../api_key.json', 'r', encoding='utf-8') as file:
        api_data = json.load(file)

    base_url = api_data[0]['base_url']
    api_key = api_data[0]['api_key']

    answer_agent = OpenaiAgent(base_url, api_key, model_name)
    ans_rewrite_agent = OpenaiAgent(base_url, api_key, judge_model_name)
    ans_check_agent = OpenaiAgent(base_url, api_key, judge_model_name)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_path = f"./database/{test_name}/{{title}}/log_{timestamp}.log"

    ds = load_dataset('bigai-nlco/LooGLE', data_type, split='test', cache_dir='./dataset_cache')

    all_titles = []
    with open('./dataset_cache/LooGLE-rewrite-data/titles.json', 'r', encoding='utf-8') as f:
        title_data = json.load(f)

    for title_iter in title_data.values():
        all_titles.append(title_iter)

    if title_index < 0 or title_index >= len(all_titles):
        print(f"Error: Title index {title_index} is out of range. Valid range: 0 - {len(all_titles) - 1}")
        return

    title = all_titles[title_index]
    print(f"Test Title: {title}")

    filtered_data = ds.filter(lambda example: example['title'] == title)
    context = filtered_data[0]['context']

    with open(f"./dataset_cache/LooGLE-rewrite-data/choice-format/{data_type}/{title}.json", "r", encoding="utf-8") as f:
        cleaned_data = json.load(f)

    with open(f"./dataset_cache/LooGLE-rewrite-data/similar-data/{data_type}/{title}.json", "r", encoding="utf-8") as f:
        rewrite_data = json.load(f)

    os.makedirs(f"database/{test_name}/{title_index}", exist_ok=True)

    right_num = 0
    total_num = 0
    all_inputs = []

    for data_iter, cleaned_data_iter, rewrite_data_iter in zip(filtered_data, cleaned_data, rewrite_data):
        print(f"{title_index} Handle question {total_num + 1}")
        if question_type == 'origin':
            query = cleaned_data_iter['question']
        else:
            query = rewrite_data_iter['question']

        answer = cleaned_data_iter['answer']
        cleaned_query = cleaned_data_iter['question']
        evidence = cleaned_data_iter['evidence']

        if use_context:
            user_input = f"Context:\n{context}\n\nQuestion: {query}".strip()
        else:
            user_input = query

        raw_response = answer_agent.generate_response(system_prompt, [{"role": "user", "content": user_input}])
        response = response_format.format(query=query, output=raw_response)

        ans_rewrite_input = ans_rewrite_prompt.format(question=cleaned_query, generated_answer=response)
        rewrite_response = ans_rewrite_agent.generate_response("", [{"role": "user", "content": ans_rewrite_input}]).strip()

        ans_check_input = ans_check_prompt.format(
            question=cleaned_query,
            reference_answer=answer,
            generated_output=rewrite_response
        )
        ans_check_response = ans_check_agent.generate_response("", [{"role": "user", "content": ans_check_input}]).strip()

        all_inputs.append({
            "query": query,
            "cleaned_query": cleaned_query,
            "response": response,
            "rewrite_response": rewrite_response,
            "real_ans": answer,
            "evidence": evidence,
            "ans_check_input": ans_check_input,
            "check_response": ans_check_response
        })

        total_num += 1

        if ans_check_response == "True":
            print(f"{title_index} Get Right Ans")
            right_num += 1
        elif ans_check_response == "False":
            print(f"{title_index} Get Wrong Ans")
        else:
            print(f"Ans Check Output Error: {ans_check_response}")

    print(f"Correct:({right_num}/{total_num}) Rate:{right_num / total_num}")
    with open(f"database/{test_name}/{title_index}/input.json", "w", encoding="utf-8") as f:
        json.dump(all_inputs, f, ensure_ascii=False, indent=4)

    with open(f"database/{test_name}/{title_index}/result.txt", "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Correct: {right_num}/{total_num}\n")
        f.write(f"Accuracy Rate: {right_num / total_num:.4f}\n")


if __name__ == '__main__':
    main()
