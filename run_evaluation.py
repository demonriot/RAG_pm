from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


API_URL = "http://localhost:8000/query"
INPUT_CSV = "evaluation_queries.csv"
OUTPUT_DIR = Path("evaluation_outputs")
RAW_JSON_DIR = OUTPUT_DIR / "raw_json"
SUMMARY_CSV = OUTPUT_DIR / "evaluation_results.csv"


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    RAW_JSON_DIR.mkdir(exist_ok=True)


def load_queries(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def post_query(query: str) -> Dict[str, Any]:
    response = requests.post(
        API_URL,
        json={"query": query},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def save_raw_json(test_id: str, payload: Dict[str, Any]) -> None:
    out_path = RAW_JSON_DIR / f"{test_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def infer_actual_label(result: Dict[str, Any]) -> str:
    """
    Best-effort label inference from your current response format.
    You can refine this later if needed.
    """
    planner_result = result.get("planner_result")
    output = result.get("output", {})

    clarifying_questions = output.get("clarifying_questions", [])
    assumptions = output.get("assumptions_or_not_in_catalog", [])
    why = output.get("why", [])

    if clarifying_questions:
        return "clarify"

    if planner_result is None:
        answer_text = (output.get("answer_or_plan") or "").lower()
        if "not in" in answer_text or "don't have" in answer_text:
            return "abstain"
        return "clarify"

    eligible_now = planner_result.get("eligible_now", [])
    not_eligible = planner_result.get("not_eligible", [])
    need_more_info = planner_result.get("need_more_info", [])

    total = len(eligible_now) + len(not_eligible) + len(need_more_info)

    # Single-target eligibility case
    if total == 1:
        if len(eligible_now) == 1:
            return "eligible"
        if len(not_eligible) == 1:
            return "not_eligible"
        if len(need_more_info) == 1:
            return "need_more_info"

    # Not-in-docs heuristic
    answer_text = (output.get("answer_or_plan") or "").lower()
    joined_assumptions = " ".join(assumptions).lower()
    joined_why = " ".join(why).lower()

    abstain_markers = [
        "i don't have that information",
        "not in the catalog",
        "not in the provided catalog",
        "not available in the catalog",
    ]
    if any(marker in answer_text for marker in abstain_markers):
        return "abstain"
    if "not in catalog" in joined_assumptions or "not in docs" in joined_assumptions:
        return "abstain"

    # Multi-course or planning output
    return "answer"


def count_citations(result: Dict[str, Any]) -> int:
    output = result.get("output", {})
    citations = output.get("citations", [])
    return len(citations)


def has_clarifying_question(result: Dict[str, Any]) -> bool:
    output = result.get("output", {})
    return len(output.get("clarifying_questions", [])) > 0


def looks_like_abstention(result: Dict[str, Any]) -> bool:
    output = result.get("output", {})
    answer = (output.get("answer_or_plan") or "").lower()
    assumptions = " ".join(output.get("assumptions_or_not_in_catalog", [])).lower()

    abstain_markers = [
        "i don't have that information",
        "not in the provided catalog",
        "not in the catalog",
        "check the advisor",
        "check the schedule of classes",
        "check the department page",
    ]
    return any(marker in answer for marker in abstain_markers) or any(
        marker in assumptions for marker in abstain_markers
    )


def build_summary_row(test: Dict[str, str], result: Dict[str, Any], elapsed_s: float) -> Dict[str, Any]:
    output = result.get("output", {})
    planner_result = result.get("planner_result")

    return {
        "id": test["id"],
        "category": test["category"],
        "query": test["query"],
        "expected_label": test["expected_label"],
        "actual_label": infer_actual_label(result),
        "status": "ok",
        "elapsed_s": round(elapsed_s, 3),
        "citation_count": count_citations(result),
        "has_citation": count_citations(result) > 0,
        "asked_clarifying_question": has_clarifying_question(result),
        "abstained": looks_like_abstention(result),
        "answer_or_plan": output.get("answer_or_plan", ""),
        "why_count": len(output.get("why", [])),
        "clarifying_question_count": len(output.get("clarifying_questions", [])),
        "assumption_count": len(output.get("assumptions_or_not_in_catalog", [])),
        "planner_result_present": planner_result is not None,
        "manual_correct": "",
        "review_notes": "",
    }


def build_error_row(test: Dict[str, str], error_text: str, elapsed_s: float) -> Dict[str, Any]:
    return {
        "id": test["id"],
        "category": test["category"],
        "query": test["query"],
        "expected_label": test["expected_label"],
        "actual_label": "error",
        "status": "error",
        "elapsed_s": round(elapsed_s, 3),
        "citation_count": 0,
        "has_citation": False,
        "asked_clarifying_question": False,
        "abstained": False,
        "answer_or_plan": error_text,
        "why_count": 0,
        "clarifying_question_count": 0,
        "assumption_count": 0,
        "planner_result_present": False,
        "manual_correct": "",
        "review_notes": "",
    }


def write_summary(rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "category",
        "query",
        "expected_label",
        "actual_label",
        "status",
        "elapsed_s",
        "citation_count",
        "has_citation",
        "asked_clarifying_question",
        "abstained",
        "answer_or_plan",
        "why_count",
        "clarifying_question_count",
        "assumption_count",
        "planner_result_present",
        "manual_correct",
        "review_notes",
    ]

    with open(SUMMARY_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ensure_dirs()
    tests = load_queries(INPUT_CSV)

    summary_rows: List[Dict[str, Any]] = []

    for test in tests:
        test_id = test["id"]
        query = test["query"]

        print(f"Running {test_id}: {query}")

        start = time.time()
        try:
            result = post_query(query)
            elapsed_s = time.time() - start

            save_raw_json(test_id, result)
            summary_rows.append(build_summary_row(test, result, elapsed_s))

        except Exception as e:
            elapsed_s = time.time() - start
            summary_rows.append(build_error_row(test, str(e), elapsed_s))

    write_summary(summary_rows)
    print(f"\nSaved summary to: {SUMMARY_CSV}")
    print(f"Saved raw JSON outputs to: {RAW_JSON_DIR}")


if __name__ == "__main__":
    main()