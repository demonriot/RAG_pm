from __future__ import annotations

import re
from typing import List, Tuple

from app.core.schemas.planning import PlannerCourseResult


GENERIC_TITLE_KEYWORDS = {
    "seminar",
    "special topics",
    "projects",
    "project",
    "research",
    "internship",
    "thesis",
    "reading and conference",
}


def parse_course_number(course_code: str) -> Tuple[str, int, str]:
    m = re.fullmatch(r"([A-Z]{2,4})\s(\d{3})([A-Z]?)", course_code.strip().upper())
    if not m:
        return (course_code, 999, "")
    return (m.group(1), int(m.group(2)), m.group(3))


def get_highest_completed_number(
    completed_courses: List[str],
    subject_prefix: str = "CS",
) -> int:
    numbers = []
    for course in completed_courses:
        subject, number, _ = parse_course_number(course)
        if subject == subject_prefix:
            numbers.append(number)
    return max(numbers) if numbers else 0


def recommendation_score(
    item: PlannerCourseResult,
    completed_courses: List[str],
) -> tuple:
    subject, number, suffix = parse_course_number(item.course_code)
    title = (item.title or "").lower()
    debug = item.debug or {}

    highest_completed = get_highest_completed_number(completed_courses, subject_prefix=subject)

    penalty = 0

    # Strongly penalize courses below the student's highest completed level
    if highest_completed:
        if number < highest_completed:
            penalty += 200 + (highest_completed - number)
        else:
            # Prefer courses slightly above current level
            gap = number - highest_completed
            penalty += gap

    # Boost if the course actually matched completed prerequisites
    matched_courses = debug.get("matched_courses", [])
    if matched_courses:
        penalty -= 100

    # Penalize generic course types
    for keyword in GENERIC_TITLE_KEYWORDS:
        if keyword in title:
            penalty += 75
            break

    # Slight penalty for suffix variants
    if suffix:
        penalty += 5

    return (
        penalty,
        number,
        item.course_code,
    )


def rank_recommendations(
    eligible_courses: List[PlannerCourseResult],
    completed_courses: List[str],
    limit: int = 8,
) -> List[PlannerCourseResult]:
    ranked = sorted(
        eligible_courses,
        key=lambda item: recommendation_score(item, completed_courses),
    )
    return ranked[:limit]