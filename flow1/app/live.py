"""Bản THẬT của ba chỗ trống trong `stubs.py` — gọi LLM ngay lúc người dùng hỏi.

Cùng chữ ký, cùng hình dạng dữ liệu trả về như `stubs.py`, nên `app.py` chỉ cần
đổi một dòng import. Khác biệt duy nhất: `claim` không còn là `None`.

Chạy:
    cd summarizer
    uv run streamlit run ../codebase/app.py

Phải chạy từ venv của `summarizer` vì cần `summarizer` + `vector_db` + `streamlit`.

Ghi chú về "real time": mỗi lần bấm tóm một phần là gọi LLM thật, đo được bằng
`last_stats()`. Cache vẫn bật — hỏi lại đúng phần đó thì trả tức thì và
`llm_calls = 0`. Muốn ép gọi lại thì bật `set_force(True)` ở sidebar.
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
    from flow1.app.stubs import (  # noqa: F401
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

# ─────────────────────────────────────────────────────────────────────────────
# Tài nguyên dùng chung
# ─────────────────────────────────────────────────────────────────────────────

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
    """Bỏ qua cache — để tự tay kiểm chứng là LLM có chạy thật."""

    global _force
    _force = value


@dataclass
class Stats:
    llm_calls: int = 0
    cache_hits: int = 0
    seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)


_last = Stats()


def last_stats() -> Stats:
    return _last


def backend_label() -> str:
    return (
        f"{settings.loader_backend} · map `{settings.map_model}` · "
        f"reduce `{settings.reduce_model}`"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cầu nối giữa hai cách đánh số
# ─────────────────────────────────────────────────────────────────────────────
#
# UI gọi buổi là "01".."06" và gom section thành "phần"; summarizer gọi buổi là
# "T01".."T06" và làm việc ở mức section. `section_range` trong outline.json là
# khoảng section_order 1-based, khớp thẳng với `SectionRef.section_order`.


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
    """Đổi CitedItem sang đúng hình dạng mà render_msg() đang đọc.

    UI hiện `cite[0]` và `quote`, nên `quote` phải là nguyên văn của chính đoạn
    được trích đầu tiên — không phải câu do model viết lại.
    """

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


# ─────────────────────────────────────────────────────────────────────────────
# LUỒNG 2 — tóm tắt một phần  (MAP thật)
# ─────────────────────────────────────────────────────────────────────────────


def summarize_part(session: dict, part_idx: int) -> dict:
    """Tóm một phần. Phần chủ yếu là hoạt động lớp thì KHÔNG hiện ý tóm tắt,
    nhưng vẫn phải chạy map cho các mục trong đó.

    Lý do: bước reduce đòi đủ 100% mục của buổi. Bỏ hẳn phần hoạt động thì
    "tóm cả buổi" vĩnh viễn thiếu mục và không bao giờ chạy được — đúng lỗi đã
    gặp: tóm hết 5/5 phần mà chỉ gom được 4/5 mục. Mục toàn hoạt động lớp được
    mapper xử lý không tốn lời gọi LLM nào, nên giữ lại gần như miễn phí.
    """

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
    _last = Stats(
        llm_calls=sum(0 if result.cache_hit else 1 for result in results),
        cache_hits=sum(1 for result in results if result.cache_hit),
        seconds=elapsed,
        warnings=[w for result in results for w in result.report.warnings],
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


# ─────────────────────────────────────────────────────────────────────────────
# LUỒNG 2 — sổ tay cả buổi  (REDUCE thật)
# ─────────────────────────────────────────────────────────────────────────────


def build_recap(session: dict, done: dict) -> dict:
    """Gộp các phần đã tóm thành sổ tay.

    Bước reduce của summarizer cần đủ 100% section của buổi. Nếu người dùng mới
    tóm vài phần thì chưa đủ điều kiện — khi đó gộp bằng CODE từ những phần đã
    có, không gọi LLM và nói rõ là bản chưa đầy đủ.
    """

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
        _last = Stats(warnings=[f"mới có {len(have)}/{len(all_refs)} mục, chưa gọi reduce"])
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


# ─────────────────────────────────────────────────────────────────────────────
# LUỒNG 1 — tra cứu
# ─────────────────────────────────────────────────────────────────────────────


def answer_query(session: dict, query: str) -> dict:
    """ĐÃ NỐI THẬT với luồng 1 (flow1)."""
    global _last
    import time
    
    try:
        from flow1.ask import ask
    except Exception as e:
        import traceback
        traceback.print_exc()
        _last = Stats()
        return {
            "status": "error",
            "claims": [],
            "note": f"Lỗi: Không import được flow1.ask. Chi tiết: {e}"
        }

    started = time.perf_counter()
    result = ask(query, session=session["id"])
    elapsed = time.perf_counter() - started
    
    _last = Stats(
        llm_calls=1 if getattr(result, "verdict", None) else 0,
        seconds=elapsed,
        warnings=[drop.detail for drop in getattr(result.verdict, "drops", [])] if getattr(result, "verdict", None) else []
    )

    if result.outcome == "answered" and getattr(result, "verdict", None):
        chunks = _chunk_index(_sid(session))
        
        claims = []
        for claim in result.verdict.claims:
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
            "note": result.message
        }
    else:
        message = result.message
        if not message:
            if result.outcome == "insufficient":
                message = "Các đoạn bản ghi không đủ căn cứ để trả lời câu hỏi này (hoặc các ý đã bị bộ lọc từ chối)."
            else:
                message = f"Không thể trả lời: {result.outcome}"
                
        return {
            "status": result.outcome,
            "claims": [],
            "note": message
        }
