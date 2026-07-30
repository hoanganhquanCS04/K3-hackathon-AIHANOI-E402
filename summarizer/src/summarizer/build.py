"""CLI precompute: sinh toàn bộ section summary và session summary.

    uv run python -m summarizer.build                # mọi buổi, dùng cache
    uv run python -m summarizer.build --session T03
    uv run python -m summarizer.build --sections-only
    uv run python -m summarizer.build --dry-run      # không gọi API, chỉ báo cache
    uv run python -m summarizer.build --force        # bỏ qua cache

Chạy lệnh này TRƯỚC buổi demo. Lúc trình bày, tóm tắt mục phải là 0 lời gọi LLM
và tóm tắt buổi là 1 lời gọi (plan §11.2).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime

from summarizer.cache import SummaryCache, cache_key
from summarizer.config import settings
from summarizer.llm import OpenAIStructuredLLM, StructuredLLM
from summarizer.loader import ContentLoader, get_loader, section_content_hash
from summarizer.mapper import summarize_sections
from summarizer.prompts import PROMPT_VERSION
from summarizer.reducer import summarize_session
from summarizer.render import render_session
from summarizer.schemas import SectionSummary
from summarizer.validator import ValidationError

logger = logging.getLogger("summarizer.build")


def build_session(
    session_id: str,
    *,
    loader: ContentLoader,
    llm: StructuredLLM,
    cache: SummaryCache,
    sections_only: bool = False,
    force: bool = False,
) -> dict:
    session = loader.get_session(session_id)
    sections = loader.get_session_sections(session_id)
    chunks = loader.get_session_content(session_id)
    chunks_by_section = {
        ref.section_id: loader.get_section_content(ref.section_id) for ref in sections
    }

    # Bất biến quan trọng nhất của luồng tóm tắt: đọc đủ, không bỏ đoạn nào.
    total_from_sections = sum(len(group) for group in chunks_by_section.values())
    if total_from_sections != len(chunks):
        raise ValidationError(
            [
                f"{session_id}: tổng chunk theo section ({total_from_sections}) khác "
                f"tổng chunk theo session ({len(chunks)})"
            ]
        )

    map_results = summarize_sections(
        session=session,
        sections=sections,
        chunks_by_section=chunks_by_section,
        llm=llm,
        cache=cache,
        force=force,
    )
    section_summaries = tuple(result.summary for result in map_results)
    cache_hits = sum(1 for result in map_results if result.cache_hit)

    warnings: list[str] = []
    for result in map_results:
        warnings.extend(result.report.warnings)

    report = {
        "session_id": session_id,
        "session_locator": session.session_locator,
        "section_count": len(sections),
        "chunk_count": len(chunks),
        "map_cache_hits": cache_hits,
        "map_llm_calls": len(map_results) - cache_hits,
        "warnings": warnings,
    }

    _write_sections(session_id, section_summaries)

    if sections_only:
        report["session_summary"] = "skipped"
        return report

    result = summarize_session(
        session=session,
        sections=sections,
        section_summaries=section_summaries,
        chunks=chunks,
        llm=llm,
        cache=cache,
        force=force,
    )
    _write_session(session_id, result.summary)

    report["reduce_cache_hit"] = result.cache_hit
    report["reduce_llm_calls"] = 0 if result.cache_hit else 1
    report["coverage"] = result.summary.coverage.model_dump()
    report["warnings"] = warnings + list(result.report.warnings)
    return report


def _write_sections(session_id: str, summaries: tuple[SectionSummary, ...]) -> None:
    directory = settings.summaries_dir / session_id
    directory.mkdir(parents=True, exist_ok=True)
    for summary in summaries:
        path = directory / f"{summary.section_id}.json"
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _write_session(session_id: str, summary) -> None:
    directory = settings.summaries_dir / session_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "session.json").write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (directory / "session.md").write_text(render_session(summary), encoding="utf-8")


def dry_run(loader: ContentLoader, cache: SummaryCache, session_ids: list[str]) -> dict:
    """Báo cáo trạng thái cache mà không gọi API."""

    rows = []
    for session_id in session_ids:
        sections = loader.get_session_sections(session_id)
        hits = 0
        for ref in sections:
            chunks = loader.get_section_content(ref.section_id)
            key = cache_key(
                section_content_hash(chunks),
                PROMPT_VERSION,
                settings.map_model,
            )
            hits += int(cache.has(key))
        rows.append(
            {
                "session_id": session_id,
                "sections": len(sections),
                "cached_sections": hits,
                "missing_sections": len(sections) - hits,
            }
        )
    return {"prompt_version": PROMPT_VERSION, "map_model": settings.map_model, "sessions": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Precompute VLearn transcript summaries.")
    parser.add_argument("--session", action="append", dest="sessions", help="vd: T03")
    parser.add_argument("--sections-only", action="store_true", help="chỉ chạy bước map")
    parser.add_argument("--force", action="store_true", help="bỏ qua cache")
    parser.add_argument("--dry-run", action="store_true", help="chỉ báo cache, không gọi API")
    parser.add_argument("--loader", choices=("local", "qdrant"), default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    loader = get_loader(args.loader)
    cache = SummaryCache(settings.cache_dir)
    session_ids = args.sessions or [ref.session_id for ref in loader.list_sessions()]

    if args.dry_run:
        print(json.dumps(dry_run(loader, cache, session_ids), ensure_ascii=False, indent=2))
        return 0

    llm = OpenAIStructuredLLM()
    reports = []
    failed = False

    for session_id in session_ids:
        logger.info("Đang xử lý %s", session_id)
        try:
            report = build_session(
                session_id,
                loader=loader,
                llm=llm,
                cache=cache,
                sections_only=args.sections_only,
                force=args.force,
            )
        except ValidationError as error:
            failed = True
            logger.error("%s thất bại: %s", session_id, error)
            reports.append({"session_id": session_id, "status": "failed", "errors": error.messages})
            continue

        reports.append(report)
        logger.info(
            "%s xong: %d mục, %d đoạn, map %d cache / %d gọi LLM",
            session_id,
            report["section_count"],
            report["chunk_count"],
            report["map_cache_hits"],
            report["map_llm_calls"],
        )

    manifest = {
        "prompt_version": PROMPT_VERSION,
        "map_model": settings.map_model,
        "reduce_model": settings.reduce_model,
        "loader_backend": args.loader or settings.loader_backend,
        "generated_at": datetime.now(UTC).isoformat(),
        "sessions": reports,
    }
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Manifest: %s", settings.manifest_path)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
