import subprocess
import argparse
import os
import time
from datetime import datetime
import json
import sys


def run_title_test(
    title_index,
    test_name,
    data_type,
    question_type,
    model_name,
    judge_model_name=None,
    system_prompt=None,
    use_context=False,
):
    cmd = [
        sys.executable,
        "eval_LooGLE_llm_only.py",
        "--title_index",
        str(title_index),
        "--test_name",
        test_name,
        "--data_type",
        data_type,
        "--question_type",
        question_type,
        "--model_name",
        model_name,
    ]

    if judge_model_name:
        cmd.extend(["--judge_model_name", judge_model_name])

    if system_prompt:
        cmd.extend(["--system_prompt", system_prompt])

    if use_context:
        cmd.append("--use_context")

    print(f"Run Command: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    return process


def main():
    parser = argparse.ArgumentParser(description='Auto Run LooGLE LLM-only Test')
    parser.add_argument('--start_index', type=int, default=0, help='Starting title index')
    parser.add_argument('--test_count', type=int, default=20, help='Number of titles to test')
    parser.add_argument('--test_name', type=str, default='llm-only-mimov2.5', help='Test name')
    parser.add_argument('--parallel', type=int, default=1, help='Number of parallel tests to run')
    parser.add_argument('--data_type', type=str, choices=['longdep_qa', 'shortdep_qa'], help='Data Type: longdep_qa or shortdep_qa')
    parser.add_argument('--question_type', type=str, default='origin', choices=['origin', 'similar'], help='Question Type: origin or similar')
    parser.add_argument('--model_name', type=str, default='mimo-v2.5', help='Backbone Model Name')
    parser.add_argument('--judge_model_name', type=str, default=None, help='Model name for answer rewrite/check')
    parser.add_argument('--system_prompt', type=str, default=None, help='Optional system prompt for the LLM')
    parser.add_argument('--use_context', action='store_true', help='If set, prepend the full context to the question')

    args = parser.parse_args()

    start_index = args.start_index
    test_count = args.test_count
    test_name = args.test_name
    parallel = args.parallel
    data_type = args.data_type
    question_type = args.question_type
    model_name = args.model_name
    judge_model_name = args.judge_model_name
    system_prompt = args.system_prompt
    use_context = args.use_context

    if parallel < 1:
        parallel = 1

    print("Starting test execution...")
    print(f"Test name: {test_name}")
    print(f"Starting index: {start_index}")
    print(f"Number of tests: {test_count}")
    print(f"Parallel processes: {parallel}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"./results_{test_name}_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)

    with open(f"{results_dir}/config.txt", "w") as f:
        f.write(f"Test name: {test_name}\n")
        f.write(f"Start index: {start_index}\n")
        f.write(f"Number of tests: {test_count}\n")
        f.write(f"Parallel processes: {parallel}\n")
        f.write(f"Start time: {timestamp}\n")
        f.write(f"Model name: {model_name}\n")
        if judge_model_name:
            f.write(f"Judge model name: {judge_model_name}\n")
        if system_prompt:
            f.write(f"System prompt: {system_prompt}\n")
        f.write(f"Use context: {use_context}\n")

    active_processes = []
    results = []

    end_index = start_index + test_count
    current_index = start_index

    while current_index < end_index or active_processes:
        while current_index < end_index and len(active_processes) < parallel:
            process = run_title_test(
                current_index,
                test_name,
                data_type,
                question_type,
                model_name,
                judge_model_name,
                system_prompt,
                use_context,
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
                    with open("./dataset_cache/LooGLE-rewrite-data/titles.json", "r", encoding="utf-8") as f:
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
                                "rate": correct / total if total > 0 else 0,
                            })
                except Exception as e:
                    print(f"Failed to read result: {e}")

        if active_processes:
            time.sleep(2)

    total_correct = sum(r["correct"] for r in results)
    total_questions = sum(r["total"] for r in results)

    print("\nTest completed!")
    print(f"Total correct answers: {total_correct}/{total_questions}")
    print(
        f"Overall accuracy: {total_correct / total_questions:.4f}"
        if total_questions > 0
        else "No results"
    )

    with open(f"{results_dir}/summary.txt", "w") as f:
        f.write(f"Test name: {test_name}\n")
        f.write(f"Total correct answers: {total_correct}/{total_questions}\n")
        if total_questions > 0:
            f.write(f"Overall accuracy: {total_correct / total_questions:.4f}\n\n")

        f.write("Per-title results:\n")
        for r in results:
            f.write(
                f"Title {r['index']} ({r['title']}): {r['correct']}/{r['total']} = {r['rate']:.4f}\n"
            )

    with open(f"{results_dir}/detailed_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"Results saved to directory: {results_dir}")


if __name__ == "__main__":
    main()
