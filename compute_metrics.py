from __future__ import annotations

import csv
from typing import List, Dict


INPUT_FILE = "evaluation_outputs/evaluation_results.csv"


def load_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def compute_metrics(rows: List[Dict[str, str]]) -> None:
    # --- PREREQUISITE ACCURACY ---
    prereq_rows = [r for r in rows if r["category"] == "prereq_check"]
    prereq_total = len(prereq_rows)
    prereq_correct = sum(to_bool(r["manual_correct"]) for r in prereq_rows)

    # --- CITATION COVERAGE ---
    # Only count grounded responses where the system actually attempted a factual answer.
    # Clarification-only responses with planner_result_present = False are excluded.
    citation_rows = [
        r for r in rows
        if to_bool(r.get("planner_result_present", ""))
    ]
    citation_total = len(citation_rows)
    citation_covered = sum(to_bool(r["has_citation"]) for r in citation_rows)

    # --- ABSTENTION ACCURACY ---
    abstain_rows = [r for r in rows if r["category"] == "not_in_docs"]
    abstain_total = len(abstain_rows)
    abstain_correct = sum(to_bool(r["manual_correct"]) for r in abstain_rows)

    # --- CLARIFICATION ACCURACY ---
    clarify_rows = [r for r in rows if r["expected_label"] == "clarify"]
    clarify_total = len(clarify_rows)
    clarify_correct = sum(to_bool(r["manual_correct"]) for r in clarify_rows)

    print("\n=== EVALUATION METRICS ===\n")

    if prereq_total:
        print(
            f"Prerequisite Accuracy: {prereq_correct}/{prereq_total} = {prereq_correct / prereq_total:.2%}"
        )

    if citation_total:
        print(
            f"Citation Coverage (grounded responses only): {citation_covered}/{citation_total} = {citation_covered / citation_total:.2%}"
        )

    if abstain_total:
        print(
            f"Abstention Accuracy: {abstain_correct}/{abstain_total} = {abstain_correct / abstain_total:.2%}"
        )

    if clarify_total:
        print(
            f"Clarification Accuracy: {clarify_correct}/{clarify_total} = {clarify_correct / clarify_total:.2%}"
        )

    print("\n==========================\n")


def main() -> None:
    rows = load_rows(INPUT_FILE)
    compute_metrics(rows)


if __name__ == "__main__":
    main()