import sys
sys.path.append('../')

from datasets import load_dataset
from ReMindRag.llms import OpenaiAgent
from ReMindRag.embeddings import HgEmbedding
from ReMindRag.chunking import MetaChunker, NaiveChunker
from ReMindRag import ReMindRag

import json
import torch
from datetime import datetime
import logging
import os
import argparse
from transformers import AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description='Run ReMindRag LooGLE Test')
    parser.add_argument('--title_index', type=int, required=True, help='Test Index')
    parser.add_argument('--test_name', type=str, default="test", help='Test Name')
    parser.add_argument('--data_type', type=str, choices=["longdep_qa", "shortdep_qa"], help='Data Type: longdep_qa or shortdep_qa')
    parser.add_argument('--question_type', type=str, default="origin", choices=["origin", "similar"], help='Question Type: origin or similar')
    parser.add_argument('--model_name', type=str, default="gpt-4o-mini", help='Backbone Model Name')
    parser.add_argument('--judge_model', type=str, default="gpt-4o", help='Model for answer rewriting and grading')
    parser.add_argument('--backbone_api_index', type=int, default=0, help='API entry used by the backbone model')
    parser.add_argument('--judge_api_index', type=int, default=0, help='API entry used by the judge model')
    parser.add_argument('--do_update', dest='do_update', action='store_true', default=True, help='Update traversal memory after answering each query')
    parser.add_argument('--no_update', dest='do_update', action='store_false', help='Disable traversal-memory updates for this run')
    parser.add_argument('--strong_connection_threshold', type=float, default=0.5, help='Strong-memory connection threshold')
    parser.add_argument('--max_questions', type=int, default=None, help='Limit questions per title for budget-controlled smoke runs')
    args = parser.parse_args()

    title_index = args.title_index
    test_name = args.test_name
    data_type = args.data_type
    model_name = args.model_name
    judge_model = args.judge_model
    question_type = args.question_type

    right_num = 0
    total_num = 0

    response_format = """
Origin Query: {query}
LLM Output: {output}

Reference Chunks: {chunks}
Reference Edges: {edges}

"""

    ans_checck_prompt = """
Given one question, there is a groundtruth and a predict answer. 
Please decide whether they are the same or not in semantic. 
Please only output True or False. 
Question: {question}  
groundtruth = {reference_answer}  
predicted answer = {generated_output}

Only output one word(True or False), without any additional content.
"""

    ans_rewrite_prompt =  """
Instruction: Given a question and an original answer, please rewrite the original answer. If the original answer is not related to any option in the question, output "I don't know". Otherwise, rewrite the answer to only contain the actual response to the question without any related analysis or references.
If the Original answer outputs "I don't know", directly output "I don't know".
Please output the rewritten answer directly.
Question = {question}
Original answer = {generated_answer}
"""

    print(f"cuda: {torch.cuda.is_available()}")

    with open('../api_key.json', 'r', encoding='utf-8') as file:
        api_data = json.load(file)

    backbone_api = api_data[args.backbone_api_index]
    judge_api = api_data[args.judge_api_index]
    base_url = backbone_api["base_url"]
    api_key = backbone_api["api_key"]

    model_cache = "../model_cache"

    chunk_agent = OpenaiAgent(base_url, api_key, model_name)
    kg_agent = OpenaiAgent(base_url, api_key, model_name)
    generate_agent = OpenaiAgent(base_url, api_key, model_name)

    embedding = HgEmbedding("nomic-ai/nomic-embed-text-v2-moe", model_cache)
    chunker = NaiveChunker("nomic-ai/nomic-embed-text-v2-moe", model_cache, max_token_length=750)
    tokenizer = AutoTokenizer.from_pretrained("nomic-ai/nomic-embed-text-v2-moe",cache_dir = model_cache)

    ans_rewrite_agent = OpenaiAgent(judge_api["base_url"], judge_api["api_key"], judge_model)
    ans_check_agent = OpenaiAgent(judge_api["base_url"], judge_api["api_key"], judge_model)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = f"./database/{test_name}/{{title}}/log_{timestamp}.log"

    ds = load_dataset("bigai-nlco/LooGLE", data_type, split='test', cache_dir="./dataset_cache") 

    all_titles = []
    with open("./dataset_cache/LooGLE-rewrite-data/titles.json","r",encoding='utf-8') as f:
        title_data = json.load(f)

    for title_iter in title_data.values():
        all_titles.append(title_iter)
    
    if title_index < 0 or title_index >= len(all_titles):
        print(f"Error: Title index {title_index} is out of range. Valid range: 0 - {len(all_titles) - 1}")
        return
    
    title = all_titles[title_index]
    print(f"Test Title: {title}")

    all_inputs = []
    filtered_data = ds.filter(lambda example: example["title"] == title)
    context = filtered_data[0]["context"]

    with open(f"./dataset_cache/LooGLE-rewrite-data/choice-format/{data_type}/{title}.json", "r", encoding="utf-8") as f:
        cleaned_data = json.load(f)

    with open(f"./dataset_cache/LooGLE-rewrite-data/similar-data/{data_type}/{title}.json", "r", encoding="utf-8") as f:
        rewrite_data = json.load(f)
    
    need_load_data = os.path.exists(f"database/{test_name}/{title_index}")
    
    if not need_load_data:
        os.makedirs(f"database/{test_name}", exist_ok=True)
        os.makedirs(f"database/{test_name}/{title_index}", exist_ok=True)

    rag = ReMindRag(
        logger_level = 10,
        log_path= log_path.format(title=title_index),
        chunk_agent = chunk_agent, 
        kg_agent = kg_agent,
        generate_agent = generate_agent, 
        embedding = embedding,
        chunker = chunker,
        tokenizer = tokenizer,
        database_description = f"Database title: {title}.",
        save_dir = f"database/{test_name}/{title_index}",
        edge_weight_coefficient = 0.1,
        strong_connection_threshold = args.strong_connection_threshold
    )

    if not need_load_data:
        print(f"Load Data: {title}")
        rag.load_content(context, "en")
    else:
        print(f"{title} --- Data already loaded.")

    agents = {
        "chunk_agent": chunk_agent,
        "kg_agent": kg_agent,
        "generate_agent": generate_agent,
        "ans_rewrite_agent": ans_rewrite_agent,
        "ans_check_agent": ans_check_agent,
    }
    construction_usage = {
        field: sum(agent.get_usage()[field] for agent in agents.values())
        for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
    }
    query_and_grade_usage = {
        "requests": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }

    for data_iter, cleaned_data_iter, rewrite_data_iter in zip(filtered_data, cleaned_data, rewrite_data):
        if args.max_questions is not None and total_num >= args.max_questions:
            break
        print(f"{title_index} Handle question {total_num+1}")
        if(question_type=="origin"):
            query = cleaned_data_iter["question"]  
        else:
            query = rewrite_data_iter["question"]

        ans = cleaned_data_iter["answer"]

        before_question_usage = {
            field: sum(agent.get_usage()[field] for agent in agents.values())
            for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
        }

        raw_response, chunks, edges = rag.generate_response(chat_history=[], user_input=query, do_update=args.do_update, force_do_rag=True, max_jumps=10)
        response = response_format.format(query = query, output = raw_response, chunks = str(chunks), edges = str(edges))

        cleaned_query = cleaned_data_iter["question"]
        
        evidence = cleaned_data_iter["evidence"]

        ans_rewrite_input = ans_rewrite_prompt.format(question = cleaned_query, generated_answer= response)
        rewrite_response = ans_rewrite_agent.generate_response("", [{"role":"user","content":ans_rewrite_input}])

        ans_check_input = ans_checck_prompt.format(question= cleaned_query, reference_answer=ans, generated_output=rewrite_response)
        ans_check_response = ans_check_agent.generate_response("", [{"role":"user","content":ans_check_input}])

        after_question_usage = {
            field: sum(agent.get_usage()[field] for agent in agents.values())
            for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
        }
        question_usage = {
            field: after_question_usage[field] - before_question_usage[field]
            for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
        }
        for field in query_and_grade_usage:
            query_and_grade_usage[field] += question_usage[field]

        all_inputs.append({
            "query": query,
            "cleaned_query": cleaned_query,
            "response": response,
            "rewrite_response": rewrite_response,
            "real_ans": ans,
            "evidence": evidence,
            "ans_check_input": ans_check_input,
            "check_response": ans_check_response,
            "usage": question_usage,
        })

        total_num += 1

        if ans_check_response == "True":
            print(f"{title_index} Get Right Ans")
            right_num += 1
        elif ans_check_response == "False":
            print(f"{title_index} Get Wrong Ans")
            pass
        else:
            print(f"Ans Check Output Error: {ans_check_response}")


    usage = {name: agent.get_usage() for name, agent in agents.items()}
    usage["total"] = {
        field: sum(item[field] for item in usage.values())
        for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
    }
    usage["construction"] = construction_usage
    usage["query_and_grade"] = query_and_grade_usage

    output_data = {
        "title": title,
        "data_type": data_type,
        "question_type": question_type,
        "config": {
            "model_name": model_name,
            "judge_model": judge_model,
            "do_update": args.do_update,
            "strong_connection_threshold": args.strong_connection_threshold,
            "max_questions": args.max_questions,
            "backbone_api_index": args.backbone_api_index,
            "judge_api_index": args.judge_api_index,
        },
        "usage": usage,
        "records": all_inputs,
    }

    rate = right_num / total_num if total_num else 0
    print(f"Correct:({right_num}/{total_num}) Rate:{rate}")
    with open(f"database/{test_name}/{title_index}/input_{question_type}.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    with open(f"database/{test_name}/{title_index}/result_{question_type}.txt", "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Correct: {right_num}/{total_num}\n")
        f.write(f"Accuracy Rate: {rate:.4f}\n")
        f.write(f"API usage: {usage['total']}\n")
        f.write(f"Construction usage: {usage['construction']}\n")
        f.write(f"Query and grade usage: {usage['query_and_grade']}\n")

    return {
        "title": title,
        "correct": right_num,
        "total": total_num,
        "rate": right_num/total_num if total_num > 0 else 0
    }

if __name__ == "__main__":
    main()
