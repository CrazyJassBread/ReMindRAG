import time

PROCESS_STARTED_AT = time.perf_counter()

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


def print_timing(label, started_at=None, **details):
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    elapsed = f" elapsed={time.perf_counter() - started_at:.3f}s" if started_at is not None else ""
    detail_text = " ".join(f"{key}={value}" for key, value in details.items())
    suffix = f" {detail_text}" if detail_text else ""
    print(f"[TIMING] {timestamp} {label}{elapsed}{suffix}", flush=True)


def main():
    run_started_at = time.perf_counter()
    print_timing("run.start")
    print_timing("imports.ready", PROCESS_STARTED_AT)

    parser = argparse.ArgumentParser(description='Run ReMindRag LooGLE Test')
    parser.add_argument('--title_index', type=int, required=True, help='Test Index')
    parser.add_argument('--test_name', type=str, default="test", help='Test Name')
    parser.add_argument('--data_type', type=str, choices=["longdep_qa", "shortdep_qa"], help='Data Type: longdep_qa or shortdep_qa')
    parser.add_argument('--question_type', type=str, choices=["origin", "similar"], help='Question Type: origin or similar')
    parser.add_argument('--model_name', type=str, default="gpt-4o-mini", help='Backbone Model Name')
    parser.add_argument('--use_adaptive_lambda', action='store_true', help='Enable query-adaptive memory replay threshold')
    parser.add_argument('--lambda_0', type=float, default=0.55, help='Base lambda for adaptive threshold')
    parser.add_argument('--lambda_min', type=float, default=0.35, help='Minimum adaptive lambda')
    parser.add_argument('--lambda_max', type=float, default=0.75, help='Maximum adaptive lambda')
    parser.add_argument('--lambda_beta', type=float, default=0.10, help='Weight for query-seed similarity')
    parser.add_argument('--lambda_gamma', type=float, default=0.08, help='Weight for query complexity')
    args = parser.parse_args()

    title_index = args.title_index
    test_name = args.test_name
    type = args.data_type
    model_name = args.model_name
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

    config_started_at = time.perf_counter()
    with open('../api_key.json', 'r', encoding='utf-8') as file:
        api_data = json.load(file)

    base_url = api_data[0]["base_url"]
    api_key = api_data[0]["api_key"]

    model_cache = "../model_cache"
    print_timing("config.ready", config_started_at)

    agents_started_at = time.perf_counter()
    chunk_agent = OpenaiAgent(base_url, api_key, model_name, agent_name="chunk_extract")
    kg_agent = OpenaiAgent(base_url, api_key, model_name, agent_name="pathfinder")
    generate_agent = OpenaiAgent(base_url, api_key, model_name, agent_name="answer_generation")
    print_timing("agents.ready", agents_started_at, model=model_name)

    embedding_started_at = time.perf_counter()
    embedding = HgEmbedding("nomic-ai/nomic-embed-text-v2-moe", model_cache)
    print_timing("embedding.ready", embedding_started_at)

    chunker_started_at = time.perf_counter()
    chunker = NaiveChunker("nomic-ai/nomic-embed-text-v2-moe", model_cache, max_token_length=750)
    print_timing("chunker.ready", chunker_started_at)

    tokenizer_started_at = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained("nomic-ai/nomic-embed-text-v2-moe",cache_dir = model_cache)
    print_timing("tokenizer.ready", tokenizer_started_at)

    # ans_rewrite_agent = OpenaiAgent(base_url, api_key, "gpt-4o")
    # ans_check_agent = OpenaiAgent(base_url, api_key, "gpt-4o")
    judge_agents_started_at = time.perf_counter()
    ans_rewrite_agent = OpenaiAgent(base_url, api_key, "mimo-v2.5", agent_name="answer_rewrite")
    ans_check_agent = OpenaiAgent(base_url, api_key, "mimo-v2.5", agent_name="answer_check")
    print_timing("judge_agents.ready", judge_agents_started_at)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = f"./database/{test_name}/{{title}}/log_{timestamp}.log"

    dataset_started_at = time.perf_counter()
    ds = load_dataset("bigai-nlco/LooGLE", type, split='test', cache_dir="./dataset_cache")
    print_timing("dataset.loaded", dataset_started_at, data_type=type, rows=len(ds))

    title_data_started_at = time.perf_counter()
    all_titles = []
    with open("./dataset_cache/LooGLE-rewrite-data/titles.json","r",encoding='utf-8') as f:
        title_data = json.load(f)

    for title_iter in title_data.values():
        all_titles.append(title_iter)
    print_timing("title_index.loaded", title_data_started_at, titles=len(all_titles))
    
    if title_index < 0 or title_index >= len(all_titles):
        print(f"Error: Title index {title_index} is out of range. Valid range: 0 - {len(all_titles) - 1}")
        return
    
    title = all_titles[title_index]
    print(f"Test Title: {title}")

    sample_started_at = time.perf_counter()
    all_inputs = []
    filtered_data = ds.filter(lambda example: example["title"] == title)
    context = filtered_data[0]["context"]

    with open(f"./dataset_cache/LooGLE-rewrite-data/choice-format/{type}/{title}.json", "r", encoding="utf-8") as f:
        cleaned_data = json.load(f)

    with open(f"./dataset_cache/LooGLE-rewrite-data/similar-data/{type}/{title}.json", "r", encoding="utf-8") as f:
        rewrite_data = json.load(f)
    print_timing(
        "sample.ready",
        sample_started_at,
        questions=len(filtered_data),
        context_chars=len(context),
    )
    
    need_load_data = os.path.exists(f"database/{test_name}/{title_index}")
    
    if not need_load_data:
        os.makedirs(f"database/{test_name}", exist_ok=True)
        os.makedirs(f"database/{test_name}/{title_index}", exist_ok=True)

    rag_init_started_at = time.perf_counter()
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
        strong_connection_threshold = 0.5,
        use_adaptive_lambda = args.use_adaptive_lambda,
        lambda_0 = args.lambda_0,
        lambda_min = args.lambda_min,
        lambda_max = args.lambda_max,
        lambda_beta = args.lambda_beta,
        lambda_gamma = args.lambda_gamma
    )
    print_timing("rag.ready", rag_init_started_at, reuse_database=need_load_data)

    if not need_load_data:
        print(f"Load Data: {title}")
        load_content_started_at = time.perf_counter()
        rag.load_content(context, "en")
        print_timing("database.build.complete", load_content_started_at)
    else:
        print(f"{title} --- Data already loaded.")
        print_timing("database.reused")


    for data_iter, cleaned_data_iter, rewrite_data_iter in zip(filtered_data, cleaned_data, rewrite_data):
        question_started_at = time.perf_counter()
        question_number = total_num + 1
        print(f"{title_index} Handle question {total_num+1}")
        if(question_type=="origin"):
            query = cleaned_data_iter["question"]  
        else:
            query = rewrite_data_iter["question"]

        ans = cleaned_data_iter["answer"]

        rag_query_started_at = time.perf_counter()
        raw_response, chunks, edges = rag.generate_response(chat_history=[], user_input=query, do_update=True, force_do_rag=True, max_jumps=10)
        print_timing("question.rag.complete", rag_query_started_at, question=question_number)
        response = response_format.format(query = query, output = raw_response, chunks = str(chunks), edges = str(edges))

        cleaned_query = cleaned_data_iter["question"]
        
        evidence = cleaned_data_iter["evidence"]

        ans_rewrite_input = ans_rewrite_prompt.format(question = cleaned_query, generated_answer= response)
        rewrite_started_at = time.perf_counter()
        rewrite_response = ans_rewrite_agent.generate_response("", [{"role":"user","content":ans_rewrite_input}])
        print_timing("question.rewrite.complete", rewrite_started_at, question=question_number)

        ans_check_input = ans_checck_prompt.format(question= cleaned_query, reference_answer=ans, generated_output=rewrite_response)
        check_started_at = time.perf_counter()
        ans_check_response = ans_check_agent.generate_response("", [{"role":"user","content":ans_check_input}])
        print_timing("question.check.complete", check_started_at, question=question_number)

        all_inputs.append({
            "query": query,
            "cleaned_query": cleaned_query,
            "response": response,
            "rewrite_response": rewrite_response,
            "real_ans": ans,
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
            pass
        else:
            print(f"Ans Check Output Error: {ans_check_response}")
        print_timing("question.complete", question_started_at, question=question_number)


    print(f"Correct:({right_num}/{total_num}) Rate:{right_num/total_num}")
    save_started_at = time.perf_counter()
    with open(f"database/{test_name}/{title_index}/input.json", "w", encoding="utf-8") as f:
        json.dump(all_inputs, f, ensure_ascii=False, indent=4)
    
    with open(f"database/{test_name}/{title_index}/result.txt", "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Correct: {right_num}/{total_num}\n")
        f.write(f"Accuracy Rate: {right_num/total_num:.4f}\n")
    print_timing("results.saved", save_started_at)
    print_timing("run.complete", run_started_at, questions=total_num)

    return {
        "title": title,
        "correct": right_num,
        "total": total_num,
        "rate": right_num/total_num if total_num > 0 else 0
    }

if __name__ == "__main__":
    main()
