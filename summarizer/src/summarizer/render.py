"""Render artifact JSON thành Markdown cho người đọc."""

from __future__ import annotations

from summarizer.schemas import CitedItem, SectionSummary, SessionSummary


def _cite(citations: tuple[str, ...]) -> str:
    return " ".join(f"`{citation}`" for citation in citations)


def _bullets(items: tuple[CitedItem, ...]) -> list[str]:
    return [f"- {item.text} — {_cite(item.citations)}" for item in items]


def render_section(summary: SectionSummary) -> str:
    lines = [
        f"## Mục {summary.section_order} — {summary.section_title}",
        "",
        summary.abstract,
        "",
        "**Ý chính**",
        "",
        *_bullets(summary.key_points),
    ]

    if summary.examples:
        lines += ["", "**Ví dụ**", "", *_bullets(summary.examples)]
    if summary.student_questions:
        lines += ["", "**Học viên nêu**", "", *_bullets(summary.student_questions)]
    if summary.concepts:
        lines += ["", f"**Khái niệm:** {', '.join(summary.concepts)}"]
    if summary.unclear_chunk_ids:
        lines += [
            "",
            f"> ⚠️ {len(summary.unclear_chunk_ids)} đoạn không nghe rõ: "
            f"{_cite(summary.unclear_chunk_ids)}",
        ]

    lines += [
        "",
        f"<sub>Đọc {len(summary.source_chunk_ids)} đoạn, trích dẫn "
        f"{len(summary.covered_chunk_ids)}.</sub>",
    ]
    return "\n".join(lines)


def render_session(summary: SessionSummary) -> str:
    coverage = summary.coverage
    lines = [
        f"# {summary.session_locator}",
        "",
        summary.tldr,
        "",
        f"> Đã đọc **{coverage.total_chunks}/{coverage.total_chunks}** đoạn của "
        f"{coverage.total_sections} mục; {coverage.cited_chunks} đoạn được trích dẫn.",
        "",
        "## Ý chính cả buổi",
        "",
    ]
    for point in summary.key_points:
        lines.append(f"- {point.text} — {_cite(point.citations)}")

    lines += ["", "## Nội dung theo mục", ""]
    for item in summary.outline:
        lines.append(f"**{item.section_order}. {item.section_title}**")
        lines.append("")
        lines.append(f"{item.abstract} — {_cite(item.citations)}")
        lines.append("")

    if summary.open_questions:
        lines += ["## Câu hỏi còn để ngỏ", "", *_bullets(summary.open_questions), ""]

    if summary.concepts:
        lines += [f"**Khái niệm:** {', '.join(summary.concepts)}", ""]

    if summary.warnings:
        lines += ["## Cảnh báo", ""]
        lines += [f"- {warning}" for warning in summary.warnings]
        lines.append("")

    lines.append(
        f"<sub>map: {summary.model_map} · reduce: {summary.model_reduce} · "
        f"prompt: {summary.prompt_version}</sub>"
    )
    return "\n".join(lines)
