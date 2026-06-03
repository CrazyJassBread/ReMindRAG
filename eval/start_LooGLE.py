import subprocess
import argparse
import os
import time
from datetime import datetime
import json

def run_title_test(title_index, test_name, data_type, question_type, model_name, judge_model_name=None):
    cmd = [ "python", "eval_LooGLE.py", 
            "--title_index", str(title_index), 
            "--test_name", test_name,
            "--data_type", data_type,
            "--question_type", question_type,
            "--model_name", model_name
        ]

    if judge_model_name:
        cmd.extend(["--judge_model_name", judge_model_name])
    
    print(f"Run Command: {' '.join(cmd)}")
    
    # process = subprocess.Popen(cmd, shell=True)
    process = subprocess.Popen(cmd)
    return process

def main():
    parser = argparse.ArgumentParser(description='Auto Run ReMindRAG Test')
    parser.add_argument('--start_index', type=int, default=0, help='Starting title index')
    parser.add_argument('--test_count', type=int, default=20, help='Number of titles to test')
    parser.add_argument('--title_indices', type=str, default=None, help='Comma-separated title indices to test, e.g. "9,16,6"')
    parser.add_argument('--test_name', type=str, default="test", help='Test name')
    parser.add_argument('--parallel', type=int, default=3, help='Number of parallel tests to run')
    parser.add_argument('--data_type', type=str, choices=["longdep_qa", "shortdep_qa"], help='Data Type: longdep_qa or shortdep_qa')
    parser.add_argument('--question_type', type=str, default="origin", choices=["origin", "similar"], help='Question Type: origin or similar')
    parser.add_argument('--model_name', type=str, default="gpt-4o-mini", help='Backbone Model Name') # use deepseek v4 for instead
    parser.add_argument('--judge_model_name', type=str, default=None, help='Model name for answer rewrite/check')
    
    args = parser.parse_args()
    
    start_index = args.start_index
    test_count = args.test_count
    title_indices = None
    if args.title_indices:
        title_indices = [int(index.strip()) for index in args.title_indices.split(",") if index.strip()]
    test_name = args.test_name
    parallel = args.parallel
    data_type = args.data_type
    question_type = args.question_type
    model_name = args.model_name
    judge_model_name = args.judge_model_name

    if parallel < 1:
        parallel = 1
    
    print(f"Starting test execution...")
    print(f"Test name: {test_name}")
    if title_indices:
        print(f"Title indices: {title_indices}")
    else:
        print(f"Starting index: {start_index}")
        print(f"Number of tests: {test_count}")
    print(f"Parallel processes: {parallel}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"./results_{test_name}_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    
    with open(f"{results_dir}/config.txt", "w") as f:
        f.write(f"Test name: {test_name}\n")
        if title_indices:
            f.write(f"Title indices: {title_indices}\n")
        else:
            f.write(f"Start index: {start_index}\n")
            f.write(f"Number of tests: {test_count}\n")
        f.write(f"Parallel processes: {parallel}\n")
        f.write(f"Start time: {timestamp}\n")
    
    active_processes = []
    results = []
    
    if title_indices:
        pending_indices = title_indices
    else:
        pending_indices = list(range(start_index, start_index + test_count))
    current_position = 0
    
    while current_position < len(pending_indices) or active_processes:
        while current_position < len(pending_indices) and len(active_processes) < parallel:
            index = pending_indices[current_position]
            process = run_title_test(index, test_name, data_type, question_type, model_name, judge_model_name)
            active_processes.append((process, index))
            print(f"Started test for title index {index}, PID: {process.pid}")
            current_position += 1
        
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
                    result_file = f"database/{test_name}/{index}/result.txt"
                    
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
                            
                            results.append({
                                "index": index,
                                "title": title,
                                "correct": correct,
                                "total": total,
                                "rate": correct/total if total > 0 else 0
                            })
                except Exception as e:
                    print(f"Failed to read result: {e}")
        
        if active_processes:
            time.sleep(2)
    
    total_correct = sum(r["correct"] for r in results)
    total_questions = sum(r["total"] for r in results)
    
    print(f"\nTest completed!")
    print(f"Total correct answers: {total_correct}/{total_questions}")
    print(f"Overall accuracy: {total_correct/total_questions:.4f}" if total_questions > 0 else "No results")
    
    with open(f"{results_dir}/summary.txt", "w") as f:
        f.write(f"Test name: {test_name}\n")
        f.write(f"Total correct answers: {total_correct}/{total_questions}\n")
        if total_questions > 0:
            f.write(f"Overall accuracy: {total_correct/total_questions:.4f}\n\n")
        
        f.write("Per-title results:\n")
        for r in results:
            f.write(f"Title {r['index']} ({r['title']}): {r['correct']}/{r['total']} = {r['rate']:.4f}\n")
    
    with open(f"{results_dir}/detailed_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"Results saved to directory: {results_dir}")

if __name__ == "__main__":
    main()
