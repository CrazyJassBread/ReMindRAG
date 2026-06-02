import argparse
import json
from pathlib import Path


USAGE_FIELDS = ["requests", "prompt_tokens", "completion_tokens", "total_tokens"]


def add_usage(total, item):
    for field in USAGE_FIELDS:
        total[field] += item.get(field, 0)


def empty_usage():
    return {field: 0 for field in USAGE_FIELDS}


def load_records(database_dir, test_name, question_type=None):
    root = Path(database_dir) / test_name
    records = []
    if not root.exists():
        raise FileNotFoundError(f"Run directory not found: {root}")

    for input_path in sorted(root.glob("*/input_*.json"), key=lambda p: (int(p.parent.name), p.name)):
        qtype = input_path.stem.removeprefix("input_")
        if question_type and qtype != question_type:
            continue
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        usage = data.get("usage", {})
        records.append(
            {
                "index": int(input_path.parent.name),
                "question_type": qtype,
                "correct": data.get("check_response") == "True",
                "query": data.get("query", ""),
                "answer": data.get("rewrite_response", ""),
                "total_usage": usage.get("total", empty_usage()),
                "construction_usage": usage.get("construction", empty_usage()),
                "query_and_grade_usage": usage.get("query_and_grade", usage.get("total", empty_usage())),
                "path": input_path,
            }
        )
    return records


def summarize(records):
    summary = {
        "count": len(records),
        "correct": sum(1 for record in records if record["correct"]),
        "total_usage": empty_usage(),
        "construction_usage": empty_usage(),
        "query_and_grade_usage": empty_usage(),
    }
    for record in records:
        add_usage(summary["total_usage"], record["total_usage"])
        add_usage(summary["construction_usage"], record["construction_usage"])
        add_usage(summary["query_and_grade_usage"], record["query_and_grade_usage"])
    summary["accuracy"] = summary["correct"] / summary["count"] if summary["count"] else 0
    return summary


def print_summary(label, records):
    summary = summarize(records)
    print(f"[{label}]")
    print(f"records: {summary['count']}")
    print(f"accuracy: {summary['correct']}/{summary['count']} = {summary['accuracy']:.4f}" if summary["count"] else "accuracy: n/a")
    print(f"total usage: {summary['total_usage']}")
    print(f"construction usage: {summary['construction_usage']}")
    print(f"query+grade usage: {summary['query_and_grade_usage']}")
    for record in records:
        print(
            f"  index={record['index']} type={record['question_type']} "
            f"correct={record['correct']} query+grade_tokens={record['query_and_grade_usage'].get('total_tokens', 0)}"
        )
    print()
    return summary


def main():
    parser = argparse.ArgumentParser(description="Summarize ReMindRAG Hotpot evaluation outputs.")
    parser.add_argument("test_names", nargs="+", help="Run names under eval/database")
    parser.add_argument("--database_dir", default="database", help="Evaluation database directory")
    parser.add_argument("--question_type", choices=["origin", "similar", "different"], help="Only include one question type")
    args = parser.parse_args()

    summaries = {}
    for test_name in args.test_names:
        records = load_records(args.database_dir, test_name, args.question_type)
        summaries[test_name] = print_summary(test_name, records)

    if len(args.test_names) == 2:
        left, right = args.test_names
        left_tokens = summaries[left]["query_and_grade_usage"]["total_tokens"]
        right_tokens = summaries[right]["query_and_grade_usage"]["total_tokens"]
        if right_tokens:
            saved = right_tokens - left_tokens
            print("[query+grade token delta]")
            print(f"{left} vs {right}: {left_tokens} vs {right_tokens}")
            print(f"saved tokens: {saved}")
            print(f"saved ratio: {saved / right_tokens:.4f}")


if __name__ == "__main__":
    main()
