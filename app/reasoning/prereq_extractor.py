from __future__ import annotations

import re
from typing import Optional


STOP_PHRASES = [
    "Available via Ecampus",
    "Corequisite:",
    "Corequisites:",
    "Equivalent to:",
    "Prerequisite:",
    "Prerequisites:",
]


def extract_prereq_text(content: str) -> Optional[str]:
    """
    Extract prerequisite text from a course chunk.
    Designed for OSU catalog course-entry chunks.
    """
    if not content or not content.strip():
        return None

    text = content.strip()

    m = re.search(r"Prerequisites?\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None

    extracted = m.group(1).strip()

    # Stop at known trailing phrases if present
    stop_positions = []
    for phrase in STOP_PHRASES:
        if phrase.lower().startswith("prereq"):
            continue
        pos = extracted.lower().find(phrase.lower())
        if pos != -1:
            stop_positions.append(pos)

    if stop_positions:
        extracted = extracted[: min(stop_positions)]

    extracted = " ".join(extracted.split()).strip()
    return extracted or None