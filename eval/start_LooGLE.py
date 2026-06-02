import subprocess
import argparse
import os
import time
from datetime import datetime
import json
import sys

def run_title_test(title_index, test_name, data_type, question_type, model_name,
                   judge_model, backbone_api_index, judge_api_index, do_update,
                   strong_connection_threshold, max_questions):
    cmd = [ sys.executable, "eval_LooGLE.py",
            "--title_index", str(title_index), 
            "--test_name", test_name,
            "--data_type", data_type,
            "--question_type", question_type,
            "--model_name", model_name,
            "--judge_model", judge_model,
            "--backbone_api_index", str(backbone_api_index),
            "--judge_api_index", str(judge_api_index),
            "--strong_connection_threshold", str(strong_connection_threshold)
        ]
    if not do_update:
        cmd.append("--no_update")
    if max_questions is not None:
        cmd.extend(["--max_questions", str(max_questions)])
    
    print(f"Run Command: {' '.join(cmd)}")
    
    process = subprocess.Popen(cmd)
    return process

def main():
    parser = argparse.ArgumentParser(description='Auto Run ReMindRAG Test')
    parser.add_argument('--start_index', type=int, default=0, help='Starting title index')
    parser.add_argument('--test_count', type=int, default=20, help='Number of titles to test')
    parser.add_argument('--test_name', type=str, default="test", help='Test name')
    parser.add_argument('--parallel', type=int, default=3, help='Number of parallel tests to run')
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
    
    start_index = args.start_index
    test_count = args.test_count
    test_name = args.test_name
    parallel = args.parallel
    data_type = args.data_type
    question_type = args.question_type
    model_name = args.model_name
    judge_model = args.judge_model

    if parallel < 1:
        parallel = 1
    
    print(f"Starting test execution...")
    print(f"Test name: {test_name}")
    print(f"Starting index: {start_index}")
    print(f"Number of tests: {test_count}")
    print(f"Parallel processes: {parallel}")
    print(f"Question type: {question_type}")
    print(f"Update memory: {args.do_update}")
    print(f"Max questions per title: {args.max_questions}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"./results_{test_name}_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    
    with open(f"{results_dir}/config.txt", "w") as f:
        f.write(f"Test name: {test_name}\n")
        f.write(f"Start index: {start_index}\n")
        f.write(f"Number of tests: {test_count}\n")
        f.write(f"Parallel processes: {parallel}\n")
        f.write(f"Data type: {data_type}\n")
        f.write(f"Question type: {question_type}\n")
        f.write(f"Backbone model: {model_name}\n")
        f.write(f"Judge model: {judge_model}\n")
        f.write(f"Update memory: {args.do_update}\n")
        f.write(f"Strong connection threshold: {args.strong_connection_threshold}\n")
        f.write(f"Max questions per title: {args.max_questions}\n")
        f.write(f"Start time: {timestamp}\n")
    
    active_processes = []
    results = []
    
    end_index = start_index + test_count
    current_index = start_index
    
    while current_index < end_index or active_processes:
        while current_index < end_index and len(active_processes) < parallel:
            input_file = f"database/{test_name}/{current_index}/input_{question_type}.json"
            if os.path.exists(input_file):
                print(f"Title index {current_index} has already been tested, skipping...")
                current_index += 1
                continue

            process = run_title_test(
                current_index, test_name, data_type, question_type, model_name,
                judge_model, args.backbone_api_index, args.judge_api_index,
                args.do_update, args.strong_connection_threshold, args.max_questions
            )
            active_processes.append((process, current_index))
            print(f"Started test for title index {current_index}, PID: {process.pid}")
            current_index += 1
        
        for i in range(len(active_processes) - 1, -1, -1):
            process, index = active_processes[i]
            if process.poll() is not None:
                active_processes.pop(i)
                status = "Success" if process.returncode == 0 else f"Failed (Return Code: {process.returncode})"
                print(f"Test for title index {index} completed, Status: {status}")
                
                try:
                    all_titles = []
                    with open("./dataset_cache/LooGLE-rewrite-data/titles.json","r",encoding='utf-8') as f:
                        title_data = json.load(f)

                    for title_iter in title_data.values():
                        all_titles.append(title_iter)
                    
                    title = all_titles[index]
                    result_file = f"database/{test_name}/{index}/result_{question_type}.txt"
                    input_file = f"database/{test_name}/{index}/input_{question_type}.json"
                    
                    if os.path.exists(result_file):
                        with open(result_file, "r") as f:
                            content = f.read()
                            correct = 0
                            total = 0
                            for line in content.split("\n"):
                                if line.startswith("Correct:"):
                                    parts = line.split(":")
                                    if len(parts) >= 2:
                                        fraction = parts[1].strip()
                                        correct, total = map(int, fraction.split("/"))
                            
                            usage = {}
                            construction_usage = {}
                            query_and_grade_usage = {}
                            if os.path.exists(input_file):
                                with open(input_file, "r", encoding="utf-8") as data_file:
                                    input_data = json.load(data_file)
                                usage = input_data.get("usage", {}).get("total", {})
                                construction_usage = input_data.get("usage", {}).get("construction", {})
                                query_and_grade_usage = input_data.get("usage", {}).get("query_and_grade", {})

                            results.append({
                                "index": index,
                                "title": title,
                                "correct": correct,
                                "total": total,
                                "rate": correct/total if total > 0 else 0,
                                "usage": usage,
                                "construction_usage": construction_usage,
                                "query_and_grade_usage": query_and_grade_usage,
                            })
                except Exception as e:
                    print(f"Failed to read result: {e}")
        
        if active_processes:
            time.sleep(2)
    
    total_correct = sum(r["correct"] for r in results)
    total_questions = sum(r["total"] for r in results)
    total_usage = {
        field: sum(r.get("usage", {}).get(field, 0) for r in results)
        for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
    }
    construction_usage = {
        field: sum(r.get("construction_usage", {}).get(field, 0) for r in results)
        for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
    }
    query_and_grade_usage = {
        field: sum(r.get("query_and_grade_usage", {}).get(field, 0) for r in results)
        for field in ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]
    }
    
    print(f"\nTest completed!")
    print(f"Total correct answers: {total_correct}/{total_questions}")
    print(f"Overall accuracy: {total_correct/total_questions:.4f}" if total_questions > 0 else "No results")
    print(f"API usage: {total_usage}")
    print(f"Construction usage: {construction_usage}")
    print(f"Query and grade usage: {query_and_grade_usage}")
    
    with open(f"{results_dir}/summary.txt", "w") as f:
        f.write(f"Test name: {test_name}\n")
        f.write(f"Total correct answers: {total_correct}/{total_questions}\n")
        if total_questions > 0:
            f.write(f"Overall accuracy: {total_correct/total_questions:.4f}\n\n")
        f.write(f"API usage: {total_usage}\n")
        f.write(f"Construction usage: {construction_usage}\n")
        f.write(f"Query and grade usage: {query_and_grade_usage}\n\n")
        
        f.write("Per-title results:\n")
        for r in results:
            f.write(f"Title {r['index']} ({r['title']}): {r['correct']}/{r['total']} = {r['rate']:.4f}\n")
    
    with open(f"{results_dir}/detailed_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"Results saved to directory: {results_dir}")

if __name__ == "__main__":
    main()
