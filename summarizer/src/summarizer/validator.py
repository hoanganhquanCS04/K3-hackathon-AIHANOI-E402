"""Kiểm chứng bản tóm tắt bằng code, không bằng LLM.

Toàn bộ module này là phép so sánh tập hợp và regex. Không có lời gọi mạng nào.
Lý do ở plan §8.1: dùng LLM để kiểm tra LLM thì có hai nguồn sai thay vì một.

Phân biệt error và warning:

- **error** — sai về mặt dữ liệu, không sửa được một cách an toàn. Ví dụ trích
  dẫn sang buổi khác, hoặc bịa ra một `section_id` không tồn tại. Ném
  `ValidationError`, chặn build.
- **warning** — sửa được một cách xác định. Ví dụ một citation không có trong
  phạm vi thì bỏ citation đó đi; một mục bị bỏ quên ở bước reduce thì lấy lại
  abstract từ section summary đã kiểm chứng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from summarizer.schemas import (
    Chunk,
    CitedItem,
    CitedItemDraft,
    Coverage,
    OutlineItem,
    SectionRef,
    SectionSummary,
    SectionSummaryDraft,
    SessionKeyPoint,
    SessionRef,
    SessionSummary,
    SessionSummaryDraft,
    session_of_citation,
)


class ValidationError(Exception):
    """Bản tóm tắt vi phạm một bất biến không sửa được."""

    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_failed(self) -> None:
        if self.errors:
            raise ValidationError(self.errors)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def clean_cited_items(
    items: list[CitedItemDraft],
    *,
    allowed: frozenset[str],
    session_id: str,
    label: str,
    report: ValidationReport,
    tolerated: frozenset[str] = frozenset(),
) -> tuple[CitedItem, ...]:
    """Lọc citation không hợp lệ, loại item không còn citation nào.

    `allowed` là tập citation được chấp nhận không điều kiện. `tolerated` là tập
    được giữ lại kèm cảnh báo — dùng ở bước reduce, khi model trích một đoạn có
    thật trong buổi nhưng không nằm trong citation của section summary nguồn.
    """

    cleaned: list[CitedItem] = []

    for index, item in enumerate(items):
        text = item.text.strip()
        if not text:
            report.warnings.append(f"{label}[{index}]: văn bản rỗng, đã loại")
            continue

        kept: list[str] = []
        for citation in item.citations:
            citation = citation.strip()
            owner = session_of_citation(citation)
            if owner is None:
                report.warnings.append(
                    f"{label}[{index}]: citation sai định dạng {citation!r}, đã loại"
                )
                continue
            if owner != session_id:
                report.errors.append(
                    f"{label}[{index}]: citation {citation} thuộc buổi {owner}, "
                    f"không phải {session_id}"
                )
                continue
            if citation in allowed:
                kept.append(citation)
                continue
            if citation in tolerated:
                report.warnings.append(
                    f"{label}[{index}]: citation {citation} không có trong section "
                    "summary nguồn nhưng có thật trong buổi, đã giữ"
                )
                kept.append(citation)
                continue
            report.warnings.append(
                f"{label}[{index}]: citation {citation} không thuộc phạm vi, đã loại"
            )

        if not kept:
            report.warnings.append(
                f"{label}[{index}]: không còn citation hợp lệ, đã loại ý {text[:60]!r}"
            )
            continue

        cleaned.append(CitedItem(text=text, citations=_dedupe(kept)))

    return tuple(cleaned)


# --------------------------------------------------------------------------
# Section
# --------------------------------------------------------------------------


def build_section_summary(
    draft: SectionSummaryDraft,
    *,
    section: SectionRef,
    chunks: tuple[Chunk, ...],
    content_hash: str,
    prompt_version: str,
    model: str,
    report: ValidationReport | None = None,
) -> tuple[SectionSummary, ValidationReport]:
    """Ghép draft của LLM với số liệu đo được thành artifact cuối."""

    report = report or ValidationReport()

    if not chunks:
        report.errors.append(f"{section.section_id}: không có chunk nào")
        report.raise_if_failed()

    allowed = frozenset(chunk.chunk_id for chunk in chunks)

    key_points = clean_cited_items(
        draft.key_points,
        allowed=allowed,
        session_id=section.session_id,
        label=f"{section.section_id}.key_points",
        report=report,
    )
    examples = clean_cited_items(
        draft.examples,
        allowed=allowed,
        session_id=section.session_id,
        label=f"{section.section_id}.examples",
        report=report,
    )
    student_questions = clean_cited_items(
        draft.student_questions,
        allowed=allowed,
        session_id=section.session_id,
        label=f"{section.section_id}.student_questions",
        report=report,
    )

    abstract = draft.abstract.strip()
    if not abstract:
        report.errors.append(f"{section.section_id}: abstract rỗng")
    if not key_points:
        report.errors.append(f"{section.section_id}: không còn key_point hợp lệ nào")

    # Bất biến của plan §8 rule 3: chỉ chunk do học viên nói mới được vào
    # student_questions. Kiểm tra được vì loader giữ speaker_role.
    student_chunk_ids = frozenset(
        chunk.chunk_id for chunk in chunks if chunk.speaker_role == "student"
    )
    for index, item in enumerate(student_questions):
        if not student_chunk_ids.intersection(item.citations):
            report.warnings.append(
                f"{section.section_id}.student_questions[{index}]: citation không trỏ "
                "vào lời học viên nào"
            )

    report.raise_if_failed()

    covered = _dedupe(
        [
            citation
            for group in (key_points, examples, student_questions)
            for item in group
            for citation in item.citations
        ]
    )

    summary = SectionSummary(
        session_id=section.session_id,
        section_id=section.section_id,
        section_title=section.section_title,
        section_order=section.section_order,
        abstract=abstract,
        key_points=key_points,
        concepts=_dedupe([c.strip() for c in draft.concepts if c.strip()]),
        examples=examples,
        student_questions=student_questions,
        source_chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
        covered_chunk_ids=tuple(sorted(covered)),
        has_unclear=any(chunk.has_unclear for chunk in chunks),
        unclear_chunk_ids=tuple(c.chunk_id for c in chunks if c.has_unclear),
        activity_chunk_ids=tuple(c.chunk_id for c in chunks if c.is_activity),
        content_hash=content_hash,
        prompt_version=prompt_version,
        model=model,
        generated_at=datetime.now(UTC),
    )
    return summary, report


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------


def build_session_summary(
    draft: SessionSummaryDraft,
    *,
    session: SessionRef,
    sections: tuple[SectionRef, ...],
    section_summaries: tuple[SectionSummary, ...],
    chunks: tuple[Chunk, ...],
    prompt_version: str,
    model_map: str,
    model_reduce: str,
    report: ValidationReport | None = None,
) -> tuple[SessionSummary, ValidationReport]:
    report = report or ValidationReport()

    by_id = {summary.section_id: summary for summary in section_summaries}
    known_sections = {ref.section_id: ref for ref in sections}

    missing = [ref.section_id for ref in sections if ref.section_id not in by_id]
    if missing:
        report.errors.append(
            f"{session.session_id}: thiếu section summary cho {', '.join(missing)}"
        )
        report.raise_if_failed()

    # Citation của bước reduce phải nằm trong citation của các section summary.
    # Đoạn có thật trong buổi nhưng section summary không trích thì vẫn giữ, kèm
    # cảnh báo — xem clean_cited_items.
    allowed = frozenset(
        citation for summary in section_summaries for citation in summary.covered_chunk_ids
    )
    tolerated = frozenset(chunk.chunk_id for chunk in chunks)

    key_points: list[SessionKeyPoint] = []
    for index, item in enumerate(draft.key_points):
        section_id = item.section_id.strip()
        if section_id not in known_sections:
            report.errors.append(
                f"{session.session_id}.key_points[{index}]: section_id {section_id!r} "
                "không tồn tại trong buổi"
            )
            continue
        cleaned = clean_cited_items(
            [CitedItemDraft(text=item.text, citations=item.citations)],
            allowed=allowed,
            session_id=session.session_id,
            label=f"{session.session_id}.key_points",
            report=report,
            tolerated=tolerated,
        )
        if cleaned:
            key_points.append(
                SessionKeyPoint(
                    text=cleaned[0].text,
                    citations=cleaned[0].citations,
                    section_id=section_id,
                )
            )

    # Outline: dựng theo thứ tự section thật, không theo thứ tự LLM trả về.
    drafted = {}
    for index, item in enumerate(draft.outline):
        section_id = item.section_id.strip()
        if section_id not in known_sections:
            report.errors.append(
                f"{session.session_id}.outline[{index}]: section_id {section_id!r} "
                "không tồn tại trong buổi"
            )
            continue
        if section_id in drafted:
            report.warnings.append(
                f"{session.session_id}.outline: {section_id} xuất hiện nhiều lần, "
                "giữ lần đầu"
            )
            continue
        drafted[section_id] = item

    report.raise_if_failed()

    outline: list[OutlineItem] = []
    for ref in sorted(sections, key=lambda item: item.section_order):
        source = by_id[ref.section_id]
        item = drafted.get(ref.section_id)
        if item is None:
            report.warnings.append(
                f"{session.session_id}.outline: thiếu {ref.section_id}, "
                "đã lấy lại abstract từ section summary"
            )
            abstract = source.abstract
            citations = source.covered_chunk_ids[:3]
        else:
            cleaned = clean_cited_items(
                [CitedItemDraft(text=item.abstract, citations=item.citations)],
                allowed=allowed,
                session_id=session.session_id,
                label=f"{session.session_id}.outline[{ref.section_id}]",
                report=report,
                tolerated=tolerated,
            )
            if cleaned:
                abstract, citations = cleaned[0].text, cleaned[0].citations
            else:
                abstract = source.abstract
                citations = source.covered_chunk_ids[:3]

        outline.append(
            OutlineItem(
                section_id=ref.section_id,
                section_order=ref.section_order,
                section_title=ref.section_title,
                abstract=abstract,
                citations=citations,
            )
        )

    open_questions = clean_cited_items(
        draft.open_questions,
        allowed=allowed,
        session_id=session.session_id,
        label=f"{session.session_id}.open_questions",
        report=report,
        tolerated=tolerated,
    )

    tldr = draft.tldr.strip()
    if not tldr:
        report.errors.append(f"{session.session_id}: tldr rỗng")
    if not key_points:
        report.errors.append(f"{session.session_id}: không còn key_point hợp lệ nào")

    report.raise_if_failed()

    cited = {
        citation
        for summary in section_summaries
        for citation in summary.covered_chunk_ids
    }
    cited.update(c for point in key_points for c in point.citations)
    cited.update(c for item in outline for c in item.citations)
    cited.update(c for item in open_questions for c in item.citations)

    warnings = list(report.warnings)
    for summary in sorted(section_summaries, key=lambda item: item.section_order):
        if summary.unclear_chunk_ids:
            warnings.append(
                f"Mục {summary.section_order} ({summary.section_title}) có "
                f"{len(summary.unclear_chunk_ids)} đoạn [không nghe rõ]; "
                "nội dung tóm tắt có thể thiếu."
            )

    coverage = Coverage(
        total_sections=len(sections),
        covered_sections=len(outline),
        total_chunks=len(chunks),
        cited_chunks=len(cited),
        unclear_chunks=sum(1 for chunk in chunks if chunk.has_unclear),
        activity_chunks=sum(1 for chunk in chunks if chunk.is_activity),
    )

    summary = SessionSummary(
        session_id=session.session_id,
        session_title=session.session_title,
        session_locator=session.session_locator,
        tldr=tldr,
        key_points=tuple(key_points),
        outline=tuple(outline),
        concepts=_dedupe([c.strip() for c in draft.concepts if c.strip()]),
        open_questions=open_questions,
        coverage=coverage,
        warnings=tuple(warnings),
        prompt_version=prompt_version,
        model_map=model_map,
        model_reduce=model_reduce,
        generated_at=datetime.now(UTC),
    )
    return summary, report
