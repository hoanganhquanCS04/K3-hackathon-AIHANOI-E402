"""Vietnamese-friendly deterministic text normalization."""

from __future__ import annotations

import re
import unicodedata

WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Lowercase, strip accents and normalize whitespace for regex/keywords."""

    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return WHITESPACE_RE.sub(" ", without_marks.replace("đ", "d")).strip()


def excerpt(value: str, limit: int = 280) -> str:
    compact = WHITESPACE_RE.sub(" ", value).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def keyword_recall(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    normalized = normalize_text(text)
    matched = sum(normalize_text(keyword) in normalized for keyword in keywords)
    return matched / len(keywords)
