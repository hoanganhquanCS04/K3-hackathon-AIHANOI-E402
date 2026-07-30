"""Bước REDUCE: tổng hợp session summary từ các section summary.

Bước này KHÔNG đọc lại transcript gốc. Lý do ở plan §6.1: đọc 19 bản tóm tắt
(~4k token) cho kết quả cân bằng giữa các mục, còn đọc lại 51k token thì model
thiên vị phần đầu prompt và mục cuối buổi hay bị bỏ.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from summarizer.cache import SummaryCache, cache_key
from summarizer.config import settings
from summarizer.llm import StructuredLLM
from summarizer.prompts import (
    PROMPT_VERSION,
    REDUCE_PROMPT_VERSION,
    REDUCE_SYSTEM,
    build_reduce_user,
)
from summarizer.schemas import (
    Chunk,
    SectionRef,
    SectionSummary,
    SessionRef,
    SessionSummary,
    SessionSummaryDraft,
)
from summarizer.validator import ValidationReport, build_session_summary


@dataclass
class ReduceResult:
    summary: SessionSummary
    cache_hit: bool
    report: ValidationReport


def session_cache_key(
    section_summaries: tuple[SectionSummary, ...],
    *,
    map_model: str,
    reduce_model: str,
    outline_hint: str = "",
) -> str:
    """`outline_hint` nằm trong khoá vì nó đi vào prompt.

    Thiếu nó thì bật/tắt dàn ý knowledge graph xong chạy lại sẽ nhận đúng bản
    tóm tắt cũ, và người bật tưởng dàn ý không có tác dụng gì — cùng loại lỗi mà
    `PROMPT_VERSION` sinh ra để chặn (xem cache.py).
    """

    ordered = sorted(section_summaries, key=lambda item: item.section_order)
    hint_digest = hashlib.sha256(outline_hint.strip().encode("utf-8")).hexdigest()
    return cache_key(
        "session",
        *[summary.content_hash for summary in ordered],
        REDUCE_PROMPT_VERSION,
        map_model,
        reduce_model,
        hint_digest,
    )


def summarize_session(
    *,
    session: SessionRef,
    sections: tuple[SectionRef, ...],
    section_summaries: tuple[SectionSummary, ...],
    chunks: tuple[Chunk, ...],
    llm: StructuredLLM,
    cache: SummaryCache,
    model: str | None = None,
    map_model: str | None = None,
    temperature: float | None = None,
    force: bool = False,
    outline_hint: str = "",
) -> ReduceResult:
    model = model or settings.reduce_model
    map_model = map_model or settings.map_model
    temperature = settings.reduce_temperature if temperature is None else temperature

    key = session_cache_key(
        section_summaries,
        map_model=map_model,
        reduce_model=model,
        outline_hint=outline_hint,
    )

    if not force:
        cached = cache.get(key)
        if cached is not None:
            return ReduceResult(
                summary=SessionSummary.model_validate(cached),
                cache_hit=True,
                report=ValidationReport(),
            )

    draft = llm.parse(
        model=model,
        system=REDUCE_SYSTEM,
        user=build_reduce_user(
            session=session,
            section_summaries=section_summaries,
            outline_hint=outline_hint,
        ),
        schema=SessionSummaryDraft,
        temperature=temperature,
    )

    summary, report = build_session_summary(
        draft,
        session=session,
        sections=sections,
        section_summaries=section_summaries,
        chunks=chunks,
        prompt_version=PROMPT_VERSION,
        model_map=map_model,
        model_reduce=model,
    )
    cache.put(key, summary.model_dump(mode="json"))
    return ReduceResult(summary=summary, cache_hit=False, report=report)
