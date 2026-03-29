# app/reasoning/prereq_parser.py

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


COURSE_RE = re.compile(r"\b([A-Z]{2,4})\s?(\d{3}[A-Z]?)\b")

UNSUPPORTED_KEYWORDS = [
    "INSTRUCTOR APPROVAL",
    "APPROVAL OF INSTRUCTOR",
    "CONCURRENT",
    "COREQUISITE",
    "CO-REQUISITE",
    "CLASS STANDING",
    "MAJOR",
    "MINOR",
    "GPA",
    "PERMISSION",
]


@dataclass
class Token:
    type: str
    value: str


class ParseError(Exception):
    pass


def normalize_course_code(text: str) -> str:
    text = text.upper().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([A-Z]{2,4})\s?(\d{3}[A-Z]?)", r"\1 \2", text)
    return text


def normalize_prereq_text(text: str) -> str:
    text = text.upper()
    text = re.sub(r"\bMINIMUM GRADE OF [A-F][+-]?\b", "", text)
    text = re.sub(r"\bA MINIMUM GRADE OF [A-F][+-]?\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _boundary(text: str, start: int, length: int) -> bool:
    left_ok = start == 0 or not text[start - 1].isalnum()
    end = start + length
    right_ok = end >= len(text) or not text[end].isalnum()
    return left_ok and right_ok


def tokenize(text: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0

    while i < len(text):
        ch = text[i]

        if ch.isspace():
            i += 1
            continue

        if ch == "(":
            tokens.append(Token("LPAREN", ch))
            i += 1
            continue

        if ch == ")":
            tokens.append(Token("RPAREN", ch))
            i += 1
            continue

        if text.startswith("AND", i) and _boundary(text, i, 3):
            tokens.append(Token("AND", "AND"))
            i += 3
            continue

        if text.startswith("OR", i) and _boundary(text, i, 2):
            tokens.append(Token("OR", "OR"))
            i += 2
            continue

        m = COURSE_RE.match(text, i)
        if m:
            code = f"{m.group(1)} {m.group(2)}"
            tokens.append(Token("COURSE", code))
            i = m.end()
            continue

        if ch in ",;:.":
            i += 1
            continue

        j = i
        while j < len(text) and not text[j].isspace() and text[j] not in "(),;:.":
            j += 1
        tokens.append(Token("WORD", text[i:j]))
        i = j

    return tokens


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, token_type: str) -> Token:
        tok = self.current()
        if tok is None or tok.type != token_type:
            raise ParseError(f"Expected {token_type}, got {tok}")
        self.pos += 1
        return tok

    def parse(self) -> Dict[str, Any]:
        node = self.parse_or()
        if self.current() is not None:
            leftover = " ".join(tok.value for tok in self.tokens[self.pos:])
            return {"type": "UNKNOWN", "text": leftover}
        return node

    def parse_or(self) -> Dict[str, Any]:
        items = [self.parse_and()]
        while self.current() and self.current().type == "OR":
            self.eat("OR")
            items.append(self.parse_and())

        if len(items) == 1:
            return items[0]
        return {"type": "OR", "items": items}

    def parse_and(self) -> Dict[str, Any]:
        items = [self.parse_term()]
        while self.current() and self.current().type == "AND":
            self.eat("AND")
            items.append(self.parse_term())

        if len(items) == 1:
            return items[0]
        return {"type": "AND", "items": items}

    def parse_term(self) -> Dict[str, Any]:
        tok = self.current()
        if tok is None:
            raise ParseError("Unexpected end of input")

        if tok.type == "COURSE":
            self.eat("COURSE")
            return {"type": "COURSE", "course": tok.value}

        if tok.type == "LPAREN":
            self.eat("LPAREN")
            node = self.parse_or()
            self.eat("RPAREN")
            return node

        raise ParseError(f"Unexpected token: {tok.type} {tok.value}")


def parse_prerequisite_text(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        return {
            "node": {"type": "UNKNOWN", "text": ""},
            "flags": ["empty_prerequisite_text"],
            "normalized_text": "",
        }

    normalized = normalize_prereq_text(text)

    keyword_flags: List[str] = []
    for kw in UNSUPPORTED_KEYWORDS:
        if kw in normalized:
            keyword_flags.append(f"unsupported:{kw}")

    simplified, simplify_flags = simplify_prereq_text(normalized)

    flags = keyword_flags + simplify_flags

    has_and = " AND " in f" {simplified} "
    has_or = " OR " in f" {simplified} "
    has_parens = "(" in simplified or ")" in simplified
    if has_and and has_or and not has_parens:
        flags.append("ambiguous_and_or_without_parentheses")

    try:
        tokens = tokenize(simplified)

        filtered_tokens = [
            t for t in tokens if t.type in {"LPAREN", "RPAREN", "AND", "OR", "COURSE"}
        ]

        if not filtered_tokens:
            return {
                "node": {"type": "UNKNOWN", "text": text},
                "flags": flags + ["no_parseable_course_logic"],
                "normalized_text": simplified,
            }

        node = Parser(filtered_tokens).parse()

        return {
            "node": node,
            "flags": sorted(set(flags)),
            "normalized_text": simplified,
        }

    except Exception:
        return {
            "node": {"type": "UNKNOWN", "text": text},
            "flags": sorted(set(flags + ["parse_failed"])),
            "normalized_text": simplified,
        }
    
def simplify_prereq_text(text: str) -> tuple[str, list[str]]:
    """
    Remove unsupported natural-language fragments while preserving
    parseable course-code logic where possible.
    """
    flags: list[str] = []
    working = text.upper()

    # Remove parenthetical concurrent-enrollment notes
    if "MAY BE TAKEN CONCURRENTLY" in working:
        flags.append("unsupported:concurrent_enrollment")
        working = re.sub(
            r"\(\s*MAY BE TAKEN CONCURRENTLY\s*\)",
            "",
            working,
            flags=re.IGNORECASE,
        )

    # Remove grade requirements like "with C or better"
    if re.search(r"\bWITH\s+[A-F][+-]?\s+OR\s+BETTER\b", working, flags=re.IGNORECASE):
        flags.append("unsupported:minimum_grade")
        working = re.sub(
            r"\bWITH\s+[A-F][+-]?\s+OR\s+BETTER\b",
            "",
            working,
            flags=re.IGNORECASE,
        )

    # Detect placement tests and remove them from parseable logic
    if "MATH PLACEMENT TEST" in working or "ALEKS" in working:
        flags.append("unsupported:placement_test")
        working = re.sub(
            r"\bMATH\s+PLACEMENT\s+TEST\b.*?(?=(\bAND\b|\bOR\b|$))",
            "",
            working,
            flags=re.IGNORECASE,
        )
        working = re.sub(
            r"\bMATH\s+PLACEMENT\s*-\s*ALEKS\b.*?(?=(\bAND\b|\bOR\b|$))",
            "",
            working,
            flags=re.IGNORECASE,
        )

    # Remove empty parentheses left behind
    working = re.sub(r"\(\s*\)", "", working)

    # Collapse repeated OR/AND caused by removals
    working = re.sub(r"\b(OR\s+){2,}", "OR ", working)
    working = re.sub(r"\b(AND\s+){2,}", "AND ", working)
    working = re.sub(r"(\bOR\b\s*)+\bAND\b", "AND", working)
    working = re.sub(r"(\bAND\b\s*)+\bOR\b", "OR", working)

    # Remove leading/trailing operators
    working = re.sub(r"^\s*(AND|OR)\b", "", working).strip()
    working = re.sub(r"\b(AND|OR)\s*$", "", working).strip()

    # Normalize spaces
    working = re.sub(r"\s+", " ", working).strip()

    return working, flags