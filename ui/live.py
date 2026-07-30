"""Bản THẬT của ba chỗ trống trong `stubs.py` — gọi LLM ngay lúc người dùng hỏi.

Cùng chữ ký, cùng hình dạng dữ liệu trả về như `stubs.py`.

Chạy:
    uv run streamlit run ui/app.py

Phải chạy từ venv workspace vì cần `summarizer` + `vector_db` + `streamlit` + `flow1`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

try:
    from stubs import (  # noqa: F401
        get_session,
        load_outline,
        refusal,
        resolve_part,
        route,
    )
except ImportError:
    from ui.stubs import (  # noqa: F401
        get_session,
        load_outline,
        refusal,
        resolve_part,
        route,
    )

from summarizer.cache import SummaryCache
from summarizer.config import settings
from summarizer.llm import OpenAIStructuredLLM
from summarizer.loader import get_loader
from summarizer.mapper import summarize_sections
from summarizer.reducer import summarize_session
from summarizer.schemas import Chunk, SectionSummary
from flow1.trace import Trace

_loader = None
_llm = None
_cache = None
_force = False


def _resources():
    global _loader, _llm, _cache
    if _loader is None:
        _loader = get_loader(settings.loader_backend)
        _llm = OpenAIStructuredLLM()
        _cache = SummaryCache(settings.cache_dir)
    return _loader, _llm, _cache


def set_force(value: bool) -> None:
    global _force
    _force = value


@dataclass
class Stats:
    llm_calls: int = 0
    cache_hits: int = 0
    seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    stage_timings: list[tuple[str, float, str]] = field(default_factory=list)


_last = Stats()


def last_stats() -> Stats:
    return _last


def backend_label() -> str:
    return (
        f"{settings.loader_backend} · map `{settings.map_model}` · "
        f"reduce `{settings.reduce_model}`"
    )


def _sid(session: dict) -> str:
    return f"T{session['id']}"


def _sections_of_part(session: dict, part: dict):
    loader, _, _ = _resources()
    low, high = part["section_range"]
    return tuple(
        ref
        for ref in loader.get_session_sections(_sid(session))
        if low <= ref.section_order <= high
    )


def _chunk_index(session_id: str) -> dict[str, Chunk]:
    loader, _, _ = _resources()
    return {chunk.chunk_id: chunk for chunk in loader.get_session_content(session_id)}


def _to_ui_points(
    summaries: tuple[SectionSummary, ...], chunks: dict[str, Chunk]
) -> list[dict]:
    points = []
    for summary in summaries:
        for item in summary.key_points:
            first = item.citations[0]
            chunk = chunks.get(first)
            points.append(
                {
                    "claim": item.text,
                    "cite": list(item.citations),
                    "has_student_speech": bool(chunk and chunk.speaker_role == "student"),
                    "quote": chunk.text if chunk else "(không tìm thấy đoạn gốc)",
                    "section_title": summary.section_title,
                }
            )
    return points


def summarize_part(session: dict, part_idx: int) -> dict:
    global _last
    part = session["parts"][part_idx - 1]

    loader, llm, cache = _resources()
    session_id = _sid(session)
    session_ref = loader.get_session(session_id)
    refs = _sections_of_part(session, part)

    started = time.perf_counter()
    results = summarize_sections(
        session=session_ref,
        sections=refs,
        chunks_by_section={
            ref.section_id: loader.get_section_content(ref.section_id) for ref in refs
        },
        llm=llm,
        cache=cache,
        force=_force,
    )
    elapsed = time.perf_counter() - started

    summaries = tuple(result.summary for result in results)
    timings = [
        ("MAP Tóm từng section (LLM)", round(elapsed * 1000.0, 1), f"{len(refs)} sections")
    ]

    _last = Stats(
        llm_calls=sum(0 if result.cache_hit else 1 for result in results),
        cache_hits=sum(1 for result in results if result.cache_hit),
        seconds=elapsed,
        warnings=[w for result in results for w in result.report.warnings],
        stage_timings=timings,
    )

    chunks = _chunk_index(session_id)
    gaps = []
    for summary in summaries:
        if summary.unclear_chunk_ids:
            gaps.append(
                f"{len(summary.unclear_chunk_ids)} đoạn trong “{summary.section_title}” "
                f"có [không nghe rõ] ({', '.join(summary.unclear_chunk_ids)})"
            )

    activity_heavy = part["activity_heavy"]
    return {
        "part": part,
        "skipped": activity_heavy,
        "reason": (
            f"{part['n_activity']}/{part['n_segments']} đoạn là [Hoạt động lớp] — đây là "
            "ghi chú hành chính, không phải nội dung học. Mục vẫn được đọc để tính "
            "phủ, chỉ không hiện ý tóm tắt."
        )
        if activity_heavy
        else None,
        "key_points": [] if activity_heavy else _to_ui_points(summaries, chunks),
        "gaps": gaps,
        "_summaries": summaries,
    }


def build_recap(session: dict, done: dict) -> dict:
    global _last
    loader, llm, cache = _resources()
    session_id = _sid(session)
    session_ref = loader.get_session(session_id)
    all_refs = loader.get_session_sections(session_id)

    have: dict[str, SectionSummary] = {}
    for result in done.values():
        for summary in result.get("_summaries", ()):
            have[summary.section_id] = summary

    complete = len(have) == len(all_refs)
    chunks = _chunk_index(session_id)

    if not complete:
        _last = Stats(
            warnings=[f"mới có {len(have)}/{len(all_refs)} mục, chưa gọi reduce"],
            stage_timings=[("Gộp sơ bộ (Code)", 0.5, "chưa tóm đủ các phần")],
        )
        picked = _to_ui_points(
            tuple(sorted(have.values(), key=lambda s: s.section_order)), chunks
        )
        return {
            "session": session,
            "n_parts_done": len(done),
            "n_parts_total": len(session["parts"]),
            "key_points": picked[:5],
            "student_points": [p for p in picked if p["has_student_speech"]][:5],
            "gaps": [g for i in sorted(done) for g in done[i].get("gaps", [])],
            "tldr": None,
        }

    ordered = tuple(sorted(have.values(), key=lambda s: s.section_order))
    started = time.perf_counter()
    result = summarize_session(
        session=session_ref,
        sections=all_refs,
        section_summaries=ordered,
        chunks=loader.get_session_content(session_id),
        llm=llm,
        cache=cache,
        force=_force,
    )
    elapsed = time.perf_counter() - started

    summary = result.summary
    _last = Stats(
        llm_calls=0 if result.cache_hit else 1,
        cache_hits=1 if result.cache_hit else 0,
        seconds=elapsed,
        warnings=list(summary.warnings),
        stage_timings=[("REDUCE Gộp sổ tay (LLM)", round(elapsed * 1000.0, 1), "cả buổi")],
    )

    def to_ui(item) -> dict:
        first = item.citations[0]
        chunk = chunks.get(first)
        return {
            "claim": item.text,
            "cite": list(item.citations),
            "has_student_speech": bool(chunk and chunk.speaker_role == "student"),
            "quote": chunk.text if chunk else "(không tìm thấy đoạn gốc)",
        }

    return {
        "session": session,
        "n_parts_done": len(done),
        "n_parts_total": len(session["parts"]),
        "key_points": [to_ui(item) for item in summary.key_points],
        "student_points": [to_ui(item) for item in summary.open_questions],
        "gaps": list(summary.warnings),
        "tldr": summary.tldr,
    }


def answer_query(session: dict, query: str, toggles=None, stream_callback=None) -> dict:
    """ĐÃ NỐI THẬT với Agent & Tra cứu RRF 3 nhánh, ghi nhận thời gian từng chặng."""
    global _last
    
    try:
        from flow1.agent import agent_run
    except Exception as e:
        import traceback
        traceback.print_exc()
        _last = Stats()
        return {
            "status": "error",
            "claims": [],
            "note": f"Lỗi: Không import được flow1.agent. Chi tiết: {e}"
        }

    trace = Trace(query)
    started = time.perf_counter()

    agent_res = agent_run(
        query,
        session=session["id"],
        toggles=toggles,
        trace=trace,
        stream_callback=stream_callback,
    )
    elapsed = time.perf_counter() - started

    stage_labels = {
        "rule_gate": "🛡️ Rule Gate (Phân loại 0-token)",
        "agent": "🤖 Agent Reasoning (Chọn Tool)",
        "rewrite": "✍️ Query Rewrite (LLM 1 -> 3 dạng)",
        "bm25": "🔎 BM25 Retrieval (Offline Keyword)",
        "qdrant": "🎯 Qdrant Retrieval (Vector Cloud)",
        "neo4j": "🌐 Neo4j Retrieval (Knowledge Graph)",
        "gate_stats": "📊 Cổng 1 (Tính điểm BM25 thô)",
        "fuse": "🔀 RRF Fusion (Gộp 3 nhánh)",
        "context": "📦 Context Expansion (Gỡ đoạn nguyên tử)",
        "gate1": "🛡️ Cổng 1 Decision (So ngưỡng T1)",
        "generate": "💬 Generate Answer (LLM Verdict)",
        "citation": "✅ Cổng 3 Validator (Kiểm mã trích dẫn)",
        "tom_tat": "📄 Tóm tắt cả buổi (Map-Reduce Cache)",
    }

    timings = []
    for s in trace.stages:
        name_pretty = stage_labels.get(s.name, f"⚡ Stage `{s.name}`")
        ms_val = s.data.get("ms", s.ms)
        note = ""
        if "top10" in s.data:
            note = f"{len(s.data['top10'])} hits"
        elif "tool_da_chon" in s.data:
            note = f"Tool `{s.data['tool_da_chon']}`"
        elif "nhan" in s.data and s.data["nhan"]:
            note = f"Nhãn `{s.data['nhan']}`"

        timings.append((name_pretty, round(float(ms_val), 1), note))

    verdict = None
    if hasattr(agent_res, "result") and agent_res.result:
        verdict = getattr(agent_res.result, "verdict", None)

    _last = Stats(
        llm_calls=1 if verdict else 0,
        seconds=elapsed,
        warnings=[drop.detail for drop in getattr(verdict, "drops", [])] if verdict else [],
        stage_timings=timings,
    )

    if agent_res.outcome in ("answered", "ok") and verdict:
        chunks = _chunk_index(_sid(session))
        
        claims = []
        for claim in verdict.claims:
            first_cite = claim.cite[0] if claim.cite else ""
            chunk = chunks.get(first_cite)
            claims.append({
                "claim": claim.text,
                "cite": claim.cite,
                "quote": chunk.text if chunk else "(không tìm thấy đoạn gốc)"
            })
            
        return {
            "status": "answered",
            "claims": claims,
            "note": getattr(agent_res.result, "message", "") or "Đã tra cứu thành công."
        }
    else:
        message = agent_res.message
        if not message:
            if agent_res.outcome == "insufficient":
                message = "Các đoạn bản ghi không đủ căn cứ để trả lời câu hỏi này."
            else:
                message = f"Thông báo: {agent_res.outcome}"
                
        return {
            "status": agent_res.outcome,
            "claims": [],
            "note": message
        }
