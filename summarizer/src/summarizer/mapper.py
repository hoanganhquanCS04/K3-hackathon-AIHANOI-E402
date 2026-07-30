"""Bước MAP: tóm tắt từng section.

Đơn vị map là section chứ không phải buổi. Lý do ở plan §4.1: buổi dài nhất
(T03, ~51k token) sẽ hỏng trước nếu nhồi cả buổi vào một prompt, còn section thì
luôn nằm gọn trong context.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from summarizer.cache import SummaryCache, cache_key
from summarizer.config import settings
from summarizer.llm import StructuredLLM, count_tokens
from summarizer.loader import section_content_hash
from summarizer.prompts import MAP_SYSTEM, PROMPT_VERSION, build_map_user
from summarizer.schemas import (
    Chunk,
    CitedItemDraft,
    SectionRef,
    SectionSummary,
    SectionSummaryDraft,
    SessionRef,
)
from summarizer.validator import ValidationReport, build_section_summary

logger = logging.getLogger(__name__)

# Ngưỡng cảnh báo, không phải ngưỡng chặn. Vượt ngưỡng thì section cần được chia
# nhỏ hoặc map hai tầng — xem plan §15.
SECTION_TOKEN_WARNING = 60_000


@dataclass
class MapResult:
    summary: SectionSummary
    cache_hit: bool
    report: ValidationReport


def _activity_only_draft(chunks: tuple[Chunk, ...]) -> SectionSummaryDraft:
    """Section chỉ gồm hoạt động lớp thì không cần gọi LLM.

    Nói thẳng đó là hoạt động lớp còn trung thực hơn là bắt model tóm tắt một
    đoạn không có nội dung kiến thức.
    """

    citations = [chunk.chunk_id for chunk in chunks]
    return SectionSummaryDraft(
        abstract="Mục này chỉ gồm hoạt động lớp, không có nội dung kiến thức.",
        key_points=[
            CitedItemDraft(
                text="Phần này là hoạt động lớp hoặc nội dung hành chính đã rút gọn.",
                citations=citations,
            )
        ],
        concepts=[],
        examples=[],
        student_questions=[],
    )


def summarize_section(
    *,
    session: SessionRef,
    section: SectionRef,
    chunks: tuple[Chunk, ...],
    total_sections: int,
    llm: StructuredLLM,
    cache: SummaryCache,
    model: str | None = None,
    temperature: float | None = None,
    force: bool = False,
) -> MapResult:
    model = model or settings.map_model
    temperature = settings.map_temperature if temperature is None else temperature

    content_hash = section_content_hash(chunks)
    key = cache_key(content_hash, PROMPT_VERSION, model)

    if not force:
        cached = cache.get(key)
        if cached is not None:
            return MapResult(
                summary=SectionSummary.model_validate(cached),
                cache_hit=True,
                report=ValidationReport(),
            )

    # Hoạt động lớp bị loại khỏi prompt nhưng vẫn nằm trong source_chunk_ids để
    # coverage phản ánh đúng số đoạn đã đọc (plan §8 rule 5).
    content_chunks = tuple(chunk for chunk in chunks if not chunk.is_activity)

    if not content_chunks:
        draft = _activity_only_draft(chunks)
    else:
        user = build_map_user(
            session=session,
            section=section,
            chunks=content_chunks,
            total_sections=total_sections,
        )
        tokens = count_tokens(user, model)
        if tokens > SECTION_TOKEN_WARNING:
            logger.warning(
                "%s dài %d token, vượt ngưỡng cảnh báo %d",
                section.section_id,
                tokens,
                SECTION_TOKEN_WARNING,
            )
        draft = llm.parse(
            model=model,
            system=MAP_SYSTEM,
            user=user,
            schema=SectionSummaryDraft,
            temperature=temperature,
        )

    summary, report = build_section_summary(
        draft,
        section=section,
        chunks=chunks,
        content_hash=content_hash,
        prompt_version=PROMPT_VERSION,
        model=model,
    )
    cache.put(key, summary.model_dump(mode="json"))
    return MapResult(summary=summary, cache_hit=False, report=report)


def summarize_sections(
    *,
    session: SessionRef,
    sections: tuple[SectionRef, ...],
    chunks_by_section: dict[str, tuple[Chunk, ...]],
    llm: StructuredLLM,
    cache: SummaryCache,
    model: str | None = None,
    force: bool = False,
    max_workers: int | None = None,
) -> tuple[MapResult, ...]:
    """Map song song. Giữ nguyên thứ tự section trong kết quả trả về."""

    workers = max_workers or settings.max_concurrency
    total = len(sections)

    def run(section: SectionRef) -> MapResult:
        return summarize_section(
            session=session,
            section=section,
            chunks=chunks_by_section[section.section_id],
            total_sections=total,
            llm=llm,
            cache=cache,
            model=model,
            force=force,
        )

    if workers == 1 or total == 1:
        return tuple(run(section) for section in sections)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return tuple(pool.map(run, sections))
