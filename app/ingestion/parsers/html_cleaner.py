from __future__ import annotations

import re
from bs4 import BeautifulSoup


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean_html(html: str) -> tuple[str, str]:
    """
    Convert raw HTML into:
    - page title
    - cleaned text

    This is a generic first-pass cleaner.
    Later we can make it OSU-structure-aware if needed.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove obvious noise
    for tag in soup(["script", "style", "noscript", "svg", "img", "footer"]):
        tag.decompose()

    # Try to remove nav-like sections
    for selector in ["nav", "header"]:
        for tag in soup.select(selector):
            tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    text = soup.get_text(separator="\n")
    text = normalize_whitespace(text)

    return title, text