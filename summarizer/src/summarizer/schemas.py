"""Typed contracts for the summarization layer.

Ba nhóm model, tách bạch có chủ đích:

1. `Chunk` / `SectionRef` / `SessionRef` — dữ liệu nguồn đã chuẩn hoá. Mọi loader
   phải trả về đúng các kiểu này, bất kể lấy từ parser local hay từ Qdrant.
2. `*Draft` — thứ LLM được phép sinh ra. Cố tình hẹp: chỉ chứa phần văn bản và
   citation. Mọi số liệu đếm được (coverage, source_chunk_ids, has_unclear) do
   code tính, không hỏi LLM — xem plan §7.3.
3. `SectionSummary` / `SessionSummary` — artifact cuối, đã qua validator.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"

CITATION_PATTERN = re.compile(r"^T\d{2}-\d{3}$")
SECTION_ID_PATTERN = re.compile(r"^T\d{2}-SEC-\d{3}$")


def session_of_citation(citation: str) -> str | None:
    """`"T03-034"` -> `"T03"`. None nếu sai định dạng."""

    if not CITATION_PATTERN.match(citation):
        return None
    return citation.split("-", 1)[0]


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


# --------------------------------------------------------------------------
# 1. Dữ liệu nguồn đã chuẩn hoá
# --------------------------------------------------------------------------


class Chunk(FrozenModel):
    """Một đoạn transcript nguyên tử `TXX-NNN`."""

    chunk_id: str
    session_id: str
    section_id: str
    section_title: str
    section_order: int
    chunk_order_in_section: int
    chunk_order_in_session: int
    text: str
    has_unclear: bool
    is_activity: bool
    speaker_role: str


class SectionRef(FrozenModel):
    section_id: str
    session_id: str
    section_title: str
    section_order: int


class SessionRef(FrozenModel):
    session_id: str
    session_title: str
    session_locator: str
    session_day: int | None
    session_period: str


# --------------------------------------------------------------------------
# 2. Draft — schema mà LLM phải trả về (structured output, strict)
# --------------------------------------------------------------------------
#
# Không dùng default value, không dùng Optional: OpenAI strict mode yêu cầu mọi
# field đều required. Dùng list chứ không dùng tuple vì JSON Schema không có
# khái niệm tuple bất biến.


class CitedItemDraft(BaseModel):
    text: str
    citations: list[str]


class SectionSummaryDraft(BaseModel):
    abstract: str
    key_points: list[CitedItemDraft]
    concepts: list[str]
    examples: list[CitedItemDraft]
    student_questions: list[CitedItemDraft]


class SessionKeyPointDraft(BaseModel):
    text: str
    citations: list[str]
    section_id: str


class OutlineItemDraft(BaseModel):
    section_id: str
    abstract: str
    citations: list[str]


class SessionSummaryDraft(BaseModel):
    tldr: str
    key_points: list[SessionKeyPointDraft]
    outline: list[OutlineItemDraft]
    concepts: list[str]
    open_questions: list[CitedItemDraft]


# --------------------------------------------------------------------------
# 3. Artifact cuối
# --------------------------------------------------------------------------


class CitedItem(FrozenModel):
    text: str
    citations: tuple[str, ...]


class SectionSummary(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    summary_type: Literal["section"] = "section"

    session_id: str
    section_id: str
    section_title: str
    section_order: int

    abstract: str
    key_points: tuple[CitedItem, ...]
    concepts: tuple[str, ...]
    examples: tuple[CitedItem, ...]
    student_questions: tuple[CitedItem, ...]

    # Do code tính, không lấy từ LLM.
    source_chunk_ids: tuple[str, ...]
    covered_chunk_ids: tuple[str, ...]
    has_unclear: bool
    unclear_chunk_ids: tuple[str, ...]
    activity_chunk_ids: tuple[str, ...]

    content_hash: str
    prompt_version: str
    model: str
    generated_at: datetime


class SessionKeyPoint(FrozenModel):
    text: str
    citations: tuple[str, ...]
    section_id: str


class OutlineItem(FrozenModel):
    section_id: str
    section_order: int
    section_title: str
    abstract: str
    citations: tuple[str, ...]


class Coverage(FrozenModel):
    total_sections: int
    covered_sections: int
    total_chunks: int
    cited_chunks: int
    unclear_chunks: int
    activity_chunks: int


class SessionSummary(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    summary_type: Literal["session"] = "session"

    session_id: str
    session_title: str
    session_locator: str

    tldr: str
    key_points: tuple[SessionKeyPoint, ...]
    outline: tuple[OutlineItem, ...]
    concepts: tuple[str, ...]
    open_questions: tuple[CitedItem, ...]

    coverage: Coverage
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    prompt_version: str
    model_map: str
    model_reduce: str
    generated_at: datetime


class NeedsClarification(FrozenModel):
    status: Literal["needs_clarification"] = "needs_clarification"
    reason: str
    missing_metadata: tuple[str, ...]
    candidate_sessions: tuple[dict, ...] = Field(default_factory=tuple)
