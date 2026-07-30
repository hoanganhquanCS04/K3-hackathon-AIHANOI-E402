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

import router as _router
import sources
from part_reduce import summarize_part_sections
from stubs import (  # noqa: F401  — phần đã thật sẵn thì dùng lại nguyên
    get_session,
    load_outline,
    refusal,
    resolve_part,
)
from summarizer.cache import SummaryCache
from summarizer.config import settings
from summarizer.llm import OpenAIStructuredLLM
from summarizer.loader import get_loader
from summarizer.mapper import summarize_sections
from summarizer.reducer import summarize_session
from summarizer.schemas import Chunk, SectionSummary

# Model gộp cả buổi — đây là "bản tóm tắt cuối cùng" người dùng đọc, nên dùng
# model mạnh. Bước MAP giữ model rẻ trong settings (gpt-4o-mini): nó chạy nhiều
# lần hơn hẳn, và khoá cache có tên model nên đổi map model là ~120 bản tóm tắt
# mục đang nằm trong artifacts/summary_cache/ thành vô dụng.
REDUCE_MODEL = "gpt-5.6-sol"

# ─────────────────────────────────────────────────────────────────────────────
# Tài nguyên dùng chung
# ─────────────────────────────────────────────────────────────────────────────

_loader = None
_llm = None
_cache = None
_force = False

# Quyết định của router ở lượt gần nhất. `build_recap()` đọc lại thay vì nhận
# thêm tham số: app.py gọi route() rồi mới gọi hàm tóm tắt trong CÙNG một lượt
# handle(), nên module state là đủ, và chữ ký mà UI đang gọi không phải sửa.
_use_graph_outline = False
_graph_note = ""


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
    router: str = ""       # model nào đã định tuyến, và vì sao
    outline: str = ""      # dàn ý knowledge graph: đã dùng, hay vì sao không


_last = Stats()


def last_stats() -> Stats:
    return _last


def backend_label() -> str:
    graph_ok, graph_why = sources.graph_available()
    return (
        f"router `{_router.ROUTER_MODEL}` · nội dung {settings.loader_backend} · "
        f"map `{settings.map_model}` · gộp `{REDUCE_MODEL}` · "
        f"KG {'sẵn sàng' if graph_ok else f'chưa dùng được ({graph_why})'}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CỔNG 0 — router
# ─────────────────────────────────────────────────────────────────────────────


def route(query: str, state: dict) -> dict:
    """Giữ đúng chữ ký `stubs.route(query, state)` để `app.py` không phải sửa.

    Buổi đang mở được suy ra từ `state["sid"]` chứ không nhận thêm tham số — nhờ
    vậy router LLM có ngữ cảnh (tên buổi, số phần) mà giao diện vẫn gọi y như cũ.
    """

    global _use_graph_outline

    session = get_session(load_outline(), state.get("sid")) if state.get("sid") else None
    decision = _router.route(query, state, session)
    _use_graph_outline = bool(decision.get("use_graph_outline"))
    return decision


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


def _to_ui_points(items, chunks: dict[str, Chunk], section_title: str = "") -> list[dict]:
    """Đổi CitedItem sang đúng hình dạng mà render_msg() đang đọc.

    UI hiện `cite[0]` và `quote`, nên `quote` phải là nguyên văn của chính đoạn
    được trích đầu tiên — không phải câu do model viết lại.
    """

    points = []
    for item in items:
        first = item.citations[0]
        chunk = chunks.get(first)
        points.append(
            {
                "claim": item.text,
                "cite": list(item.citations),
                "has_student_speech": bool(chunk and chunk.speaker_role == "student"),
                "quote": chunk.text if chunk else "(không tìm thấy đoạn gốc)",
                "section_title": section_title or (chunk.section_title if chunk else ""),
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
    summaries = tuple(result.summary for result in results)
    activity_heavy = part["activity_heavy"]

    # Bước GỘP cấp phần. Không có bước này thì "tóm phần" chỉ là phép nối
    # key_points của từng mục — phần 2 mục ra 7 ý rời, phần 4 mục ra ~15 ý, và
    # người đọc thấy đúng là một đống ý chứ không phải bản tóm tắt.
    part_result = None
    if not activity_heavy:
        part_result = summarize_part_sections(
            part_title=part["title"],
            part_index=part_idx,
            total_parts=len(session["parts"]),
            session_id=session_id,
            summaries=summaries,
            llm=llm,
            cache=cache,
            model=REDUCE_MODEL,
            force=_force,
        )
    elapsed = time.perf_counter() - started

    engine, why = _router.last_route_info()
    map_calls = sum(0 if result.cache_hit else 1 for result in results)
    map_hits = sum(1 for result in results if result.cache_hit)
    warnings = [w for result in results for w in result.report.warnings]
    if part_result is not None:
        map_calls += 0 if part_result.cache_hit else 1
        map_hits += 1 if part_result.cache_hit else 0
        warnings += part_result.report.warnings
    _last = Stats(
        llm_calls=map_calls,
        cache_hits=map_hits,
        seconds=elapsed,
        warnings=warnings,
        router=f"{engine} — {why}" if why else engine,
        outline="không dùng dàn ý KG (chỉ tóm một phần)",
    )

    chunks = _chunk_index(session_id)
    gaps = []
    for summary in summaries:
        if summary.unclear_chunk_ids:
            gaps.append(
                f"{len(summary.unclear_chunk_ids)} đoạn trong “{summary.section_title}” "
                f"có [không nghe rõ] ({', '.join(summary.unclear_chunk_ids)})"
            )

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
        "abstract": part_result.abstract if part_result else "",
        "key_points": (
            [] if part_result is None else _to_ui_points(part_result.key_points, chunks)
        ),
        "gaps": gaps,
        "_summaries": summaries,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LUỒNG 2 — sổ tay cả buổi  (REDUCE thật)
# ─────────────────────────────────────────────────────────────────────────────


def build_recap(session: dict, done: dict) -> dict:
    """Tóm cả buổi — luôn chạy REDUCE thật trên 100% mục.

    Trước đây hàm này chỉ gộp bằng code những phần người dùng đã tóm sẵn. Kết quả
    là "tóm cả buổi" sau khi mới tóm 1/5 phần chỉ ra một xâu ý rời của phần đó,
    đúng như phản ánh: tóm theo từng đoạn nhỏ rồi ghép, không đi hết bài.

    Giờ hàm tự chạy map cho những mục còn thiếu rồi mới reduce. Mục nào đã tóm
    thì lấy từ cache, nên chỉ trả tiền cho phần thật sự còn thiếu.
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

    chunks = _chunk_index(session_id)
    started = time.perf_counter()

    missing = tuple(ref for ref in all_refs if ref.section_id not in have)
    map_calls = map_hits = 0
    if missing:
        results = summarize_sections(
            session=session_ref,
            sections=missing,
            chunks_by_section={
                ref.section_id: loader.get_section_content(ref.section_id)
                for ref in missing
            },
            llm=llm,
            cache=cache,
            force=_force,
        )
        for item in results:
            have[item.summary.section_id] = item.summary
            map_calls += 0 if item.cache_hit else 1
            map_hits += 1 if item.cache_hit else 0

    # Dàn ý knowledge graph — tuỳ chọn. Chuỗi rỗng thì bước gộp chạy y như cũ.
    hint, hint_note = ("", "router không yêu cầu dàn ý KG")
    if _use_graph_outline:
        hint, hint_note = sources.outline_hint(session_id)
        if hint and not hint_note:
            hint_note = f"đã dùng dàn ý KG ({len(hint.splitlines())} dòng)"

    ordered = tuple(sorted(have.values(), key=lambda s: s.section_order))
    result = summarize_session(
        session=session_ref,
        sections=all_refs,
        section_summaries=ordered,
        chunks=loader.get_session_content(session_id),
        llm=llm,
        cache=cache,
        force=_force,
        model=REDUCE_MODEL,
        outline_hint=hint,
    )
    elapsed = time.perf_counter() - started

    summary = result.summary
    engine, why = _router.last_route_info()
    _last = Stats(
        llm_calls=map_calls + (0 if result.cache_hit else 1),
        cache_hits=map_hits + (1 if result.cache_hit else 0),
        seconds=elapsed,
        warnings=list(summary.warnings),
        router=f"{engine} — {why}" if why else engine,
        outline=hint_note,
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
    """CHƯA THẬT. Đây là luồng SEARCH, thuộc module khác, không phải M2.

    Giữ nguyên hành vi giả lập của `stubs.py` và nói thẳng ra trong `note` để
    không ai nhầm là AI đã trả lời. Tóm tắt thì đã thật.
    """

    global _last
    _last = Stats()
    quotes = [q for p in session["parts"] for q in p["quotes"]][:2]
    return {
        "status": "answered",
        "claims": [
            {"claim": None, "cite": [q["seg_id"]], "quote": q["text"]} for q in quotes
        ],
        "note": "Luồng TRA CỨU chưa nối — đây vẫn là chỗ trống. Chỉ luồng TÓM TẮT "
        "(“tóm phần 1”, “tóm cả buổi”) là đã gọi AI thật.",
    }
