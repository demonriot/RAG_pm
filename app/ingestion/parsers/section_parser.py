from __future__ import annotations

import re
from typing import List

from app.ingestion.schemas.catalog_models import CatalogSection


COURSE_ENTRY_PATTERN = re.compile(
    r"^([A-Z]{2,4}\s+\d+[A-Z]{0,2}\s*,\s*.+?,\s*\d+(?:-\d+)?\s+Credits?)$",
    re.MULTILINE,
)

POLICY_HEADING_PATTERN = re.compile(
    r"^(AR\s+\d+\.\s+.+)$",
    re.MULTILINE,
)


def _clean_block(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_course_sections(clean_text: str) -> List[CatalogSection]:
    """
    Parse a department-wide course listing page into one section per course entry.
    Example heading:
      CS 161, INTRODUCTION TO COMPUTER SCIENCE I, 4 Credits
    """
    matches = list(COURSE_ENTRY_PATTERN.finditer(clean_text))
    sections: List[CatalogSection] = []

    if not matches:
        return [
            CatalogSection(
                heading="Full Course Page",
                text=_clean_block(clean_text),
                order=0,
                metadata={"parser": "course_fallback"},
            )
        ]

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)

        heading = match.group(1).strip()
        block = clean_text[start:end].strip()

        sections.append(
            CatalogSection(
                heading=heading,
                text=_clean_block(block),
                order=i,
                metadata={"parser": "course_entry"},
            )
        )

    return sections


def parse_policy_sections(clean_text: str) -> List[CatalogSection]:
    """
    Parse academic regulations into sections keyed by AR headings.
    Example heading:
      AR 17. Grades
    """
    matches = list(POLICY_HEADING_PATTERN.finditer(clean_text))
    sections: List[CatalogSection] = []

    if not matches:
        return [
            CatalogSection(
                heading="Full Policy Page",
                text=_clean_block(clean_text),
                order=0,
                metadata={"parser": "policy_fallback"},
            )
        ]

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)

        heading = match.group(1).strip()
        block = clean_text[start:end].strip()

        sections.append(
            CatalogSection(
                heading=heading,
                text=_clean_block(block),
                order=i,
                metadata={"parser": "policy_heading"},
            )
        )

    return sections


def parse_program_sections(clean_text: str) -> List[CatalogSection]:
    """
    First-pass program parser.

    Since program pages are often semi-structured and may not have perfectly
    consistent heading markup after text cleaning, we use a lightweight rule:
    split on likely heading lines with title-style capitalization and avoid
    overfitting too early.

    This can be refined once we inspect more program pages.
    """
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    sections: List[CatalogSection] = []

    current_heading = "Program Overview"
    current_lines: List[str] = []
    order = 0

    def flush() -> None:
        nonlocal current_heading, current_lines, order
        if current_lines:
            sections.append(
                CatalogSection(
                    heading=current_heading,
                    text=_clean_block("\n".join(current_lines)),
                    order=order,
                    metadata={"parser": "program_heading"},
                )
            )
            order += 1

    for line in lines:
        if _looks_like_program_heading(line):
            flush()
            current_heading = line
            current_lines = [line]
        else:
            current_lines.append(line)

    flush()

    if not sections:
        return [
            CatalogSection(
                heading="Full Program Page",
                text=_clean_block(clean_text),
                order=0,
                metadata={"parser": "program_fallback"},
            )
        ]

    return sections


def _looks_like_program_heading(line: str) -> bool:
    known_headings = {
        "Options available:",
        "Major Code:",
        "Degree Requirements",
        "Honors Baccalaureate",
        "Sample Four-Year Plan",
        "Program Learning Outcomes",
        "Requirements",
    }
    return line in known_headings


def parse_sections(clean_text: str, doc_type: str) -> List[CatalogSection]:
    if doc_type == "course":
        return parse_course_sections(clean_text)
    if doc_type == "program":
        return parse_program_sections(clean_text)
    if doc_type == "policy":
        return parse_policy_sections(clean_text)

    return [
        CatalogSection(
            heading="Full Document",
            text=_clean_block(clean_text),
            order=0,
            metadata={"parser": "generic_fallback"},
        )
    ]