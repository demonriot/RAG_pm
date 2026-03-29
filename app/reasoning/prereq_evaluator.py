# app/reasoning/prereq_evaluator.py

from __future__ import annotations

import re
from typing import Any, Dict, List, Set


def normalize_completed_courses(courses: List[str]) -> Set[str]:
    normalized: Set[str] = set()
    for c in courses:
        c = c.upper().strip()
        c = re.sub(r"\s+", " ", c)
        c = re.sub(r"([A-Z]{2,4})\s?(\d{3}[A-Z]?)", r"\1 \2", c)
        normalized.add(c)
    return normalized


def evaluate_prereq(node: Dict[str, Any], completed: Set[str]) -> Dict[str, Any]:
    node_type = node["type"]

    if node_type == "COURSE":
        course = node["course"]
        satisfied = course in completed
        return {
            "status": "satisfied" if satisfied else "not_satisfied",
            "matched_courses": [course] if satisfied else [],
            "missing_courses": [] if satisfied else [course],
        }

    if node_type == "AND":
        child_results = [evaluate_prereq(child, completed) for child in node["items"]]

        if all(r["status"] == "satisfied" for r in child_results):
            status = "satisfied"
        elif any(r["status"] == "not_satisfied" for r in child_results):
            status = "not_satisfied"
        else:
            status = "unknown"

        matched_courses = []
        missing_courses = []
        for r in child_results:
            matched_courses.extend(r.get("matched_courses", []))
            missing_courses.extend(r.get("missing_courses", []))

        return {
            "status": status,
            "matched_courses": sorted(set(matched_courses)),
            "missing_courses": sorted(set(missing_courses)),
            "children": child_results,
        }

    if node_type == "OR":
        child_results = [evaluate_prereq(child, completed) for child in node["items"]]

        satisfied_children = [r for r in child_results if r["status"] == "satisfied"]

        if satisfied_children:
            return {
                "status": "satisfied",
                "matched_courses": satisfied_children[0].get("matched_courses", []),
                "missing_courses": [],
                "children": child_results,
            }

        if all(r["status"] == "not_satisfied" for r in child_results):
            missing_courses = []
            for r in child_results:
                missing_courses.extend(r.get("missing_courses", []))
            return {
                "status": "not_satisfied",
                "matched_courses": [],
                "missing_courses": sorted(set(missing_courses)),
                "children": child_results,
            }

        return {
            "status": "unknown",
            "matched_courses": [],
            "missing_courses": [],
            "children": child_results,
        }

    return {
        "status": "unknown",
        "matched_courses": [],
        "missing_courses": [],
    }