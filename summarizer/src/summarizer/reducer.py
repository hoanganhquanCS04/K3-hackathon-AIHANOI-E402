"""Bước REDUCE: tổng hợp session summary từ các section summary.

Bước này KHÔNG đọc lại transcript gốc. Lý do ở plan §6.1: đọc 19 bản tóm tắt
(~4k token) cho kết quả cân bằng giữa các mục, còn đọc lại 51k token thì model
thiên vị phần đầu prompt và mục cuối buổi hay bị bỏ.
"""

from __future__ import annotations

from dataclasses import dataclass

from summarizer.cache import SummaryCache, cache_key
from summarizer.config import settings
from summarizer.llm import StructuredLLM
from summarizer.prompts import PROMPT_VERSION, REDUCE_SYSTEM, build_reduce_user
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
) -> str:
    ordered = sorted(section_summaries, key=lambda item: item.section_order)
    return cache_key(
        "session",
        *[summary.content_hash for summary in ordered],
        PROMPT_VERSION,
        map_model,
        reduce_model,
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
) -> ReduceResult:
    model = model or settings.reduce_model
    map_model = map_model or settings.map_model
    temperature = settings.reduce_temperature if temperature is None else temperature

    key = session_cache_key(
        section_summaries,
        map_model=map_model,
        reduce_model=model,
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
