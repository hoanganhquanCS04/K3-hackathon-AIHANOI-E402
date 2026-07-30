"""Demo Streamlit cho M2 — luồng tóm tắt.

    uv run streamlit run app.py

App này ĐỌC artifact đã precompute, không sinh tóm tắt khi render. Đó chính là
điều cần chứng minh: lúc trình bày, tóm tắt mục là 0 lời gọi LLM và tóm tắt buổi
cũng chỉ đọc file (plan §11.2). Nút build nằm riêng ở sidebar và có cảnh báo.
"""

from __future__ import annotations

import json
import re
import time

import streamlit as st

from summarizer.cache import SummaryCache, cache_key
from summarizer.config import settings
from summarizer.loader import LocalParserLoader, section_content_hash
from summarizer.prompts import PROMPT_VERSION
from summarizer.render import render_section
from summarizer.schemas import Chunk, SectionSummary, SessionSummary

st.set_page_config(page_title="Tóm tắt buổi học · VLearn M2", page_icon="📝", layout="wide")

SPEAKER = {
    "instructor": "🎓 giảng viên",
    "student": "🙋 học viên",
    "teaching_assistant": "🧑‍🏫 trợ giảng",
    "guest": "👤 khách mời",
    "activity": "📋 hoạt động lớp",
}


# ---------------------------------------------------------------------------
# Nạp dữ liệu
# ---------------------------------------------------------------------------


@st.cache_resource
def get_loader() -> LocalParserLoader:
    return LocalParserLoader()


@st.cache_data
def load_session_summary(session_id: str, _stamp: float) -> dict | None:
    path = settings.summaries_dir / session_id / "session.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_section_summaries(session_id: str, _stamp: float) -> dict[str, dict]:
    directory = settings.summaries_dir / session_id
    if not directory.is_dir():
        return {}
    out = {}
    for path in directory.glob("*-SEC-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        out[data["section_id"]] = data
    return out


def artifact_stamp(session_id: str) -> float:
    """Đổi khi artifact được ghi lại, để st.cache_data tự làm mới."""

    directory = settings.summaries_dir / session_id
    if not directory.is_dir():
        return 0.0
    return max((path.stat().st_mtime for path in directory.glob("*.json")), default=0.0)


def chunk_map(session_id: str) -> dict[str, Chunk]:
    return {chunk.chunk_id: chunk for chunk in get_loader().get_session_content(session_id)}


# ---------------------------------------------------------------------------
# Thành phần hiển thị
# ---------------------------------------------------------------------------


def show_chunk(chunk: Chunk) -> None:
    label = SPEAKER.get(chunk.speaker_role, chunk.speaker_role)
    flags = []
    if chunk.has_unclear:
        flags.append("⚠️ có đoạn không nghe rõ")
    if chunk.is_activity:
        flags.append("📋 hoạt động lớp")
    st.markdown(f"**`{chunk.chunk_id}`** · {label}{' · ' + ' · '.join(flags) if flags else ''}")
    st.write(chunk.text)


def cited_line(text: str, citations: list[str], chunks: dict[str, Chunk], key: str) -> None:
    st.markdown(f"- {text}")
    with st.expander(f"nguồn: {'  '.join(citations)}", expanded=False):
        for citation in citations:
            chunk = chunks.get(citation)
            if chunk is None:
                st.error(f"{citation} không tồn tại trong buổi này")
                continue
            show_chunk(chunk)
            st.divider()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

loader = get_loader()
sessions = loader.list_sessions()

with st.sidebar:
    st.title("📝 Tóm tắt M2")

    session_id = st.selectbox(
        "Buổi học",
        options=[ref.session_id for ref in sessions],
        format_func=lambda sid: f"{sid} — {loader.get_session(sid).session_title[:40]}",
    )
    session = loader.get_session(session_id)

    st.caption(session.session_locator)

    st.divider()
    st.subheader("Trạng thái build")

    cache = SummaryCache(settings.cache_dir)
    section_refs = loader.get_session_sections(session_id)
    cached = sum(
        cache.has(
            cache_key(
                section_content_hash(loader.get_section_content(ref.section_id)),
                PROMPT_VERSION,
                settings.map_model,
            )
        )
        for ref in section_refs
    )
    st.metric("Mục có cache khớp cấu hình", f"{cached}/{len(section_refs)}")
    st.caption(
        f"map: `{settings.map_model}` · reduce: `{settings.reduce_model}` · "
        f"prompt: `{PROMPT_VERSION}`"
    )

    if cached < len(section_refs):
        st.warning(f"Còn {len(section_refs) - cached} mục chưa có cache cho cấu hình này.")

    with st.expander("⚡ Sinh tóm tắt (tốn API)"):
        st.caption(
            f"Sẽ gọi LLM cho {len(section_refs) - cached} mục còn thiếu và 1 lần "
            "tổng hợp buổi. Bình thường nên chạy trước bằng CLI:\n\n"
            f"`uv run python -m summarizer.build --session {session_id}`"
        )
        if st.button("Chạy build cho buổi này", type="primary"):
            from summarizer.build import build_session
            from summarizer.llm import OpenAIStructuredLLM

            with st.spinner("Đang gọi LLM..."):
                started = time.perf_counter()
                report = build_session(
                    session_id,
                    loader=loader,
                    llm=OpenAIStructuredLLM(),
                    cache=cache,
                )
                elapsed = time.perf_counter() - started
            st.success(
                f"Xong trong {elapsed:.1f}s — map {report['map_llm_calls']} lần gọi, "
                f"{report['map_cache_hits']} lần dùng cache."
            )
            st.cache_data.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Nội dung
# ---------------------------------------------------------------------------

stamp = artifact_stamp(session_id)
started = time.perf_counter()
data = load_session_summary(session_id, stamp)
section_data = load_section_summaries(session_id, stamp)
load_ms = (time.perf_counter() - started) * 1000

if data is None:
    st.title(session.session_locator)
    st.info(
        "Buổi này chưa có bản tóm tắt. Chạy:\n\n"
        f"```powershell\nuv run python -m summarizer.build --session {session_id}\n```\n\n"
        "hoặc dùng nút ở sidebar."
    )
    st.stop()

summary = SessionSummary.model_validate(data)
chunks = chunk_map(session_id)

st.title(summary.session_locator)
st.caption(
    f"Đọc từ artifact trong {load_ms:.0f} ms · 0 lời gọi LLM · "
    f"map `{summary.model_map}` · reduce `{summary.model_reduce}`"
)

# Model nằm trong khoá cache, nên đổi model là mọi cache cũ thành miss. Nói rõ
# ra còn hơn để sidebar báo 0/5 mà màn hình vẫn hiện tóm tắt.
if summary.model_map != settings.map_model or summary.model_reduce != settings.reduce_model:
    st.warning(
        f"Bản tóm tắt này sinh bằng map `{summary.model_map}` / reduce "
        f"`{summary.model_reduce}`, khác cấu hình hiện tại (`{settings.map_model}` / "
        f"`{settings.reduce_model}`). Chạy lại build nếu muốn đồng bộ."
    )

coverage = summary.coverage
columns = st.columns(5)
columns[0].metric("Mục", f"{coverage.covered_sections}/{coverage.total_sections}")
columns[1].metric("Đoạn đã đọc", f"{coverage.total_chunks}/{coverage.total_chunks}")
columns[2].metric("Đoạn được trích", coverage.cited_chunks)
columns[3].metric("Không nghe rõ", coverage.unclear_chunks)
columns[4].metric("Hoạt động lớp", coverage.activity_chunks)

tab_session, tab_section, tab_check = st.tabs(
    ["Tóm tắt buổi", "Tóm tắt từng mục", "Kiểm chứng"]
)


# --- Tab 1 ------------------------------------------------------------------

with tab_session:
    st.subheader("Tóm tắt nhanh")
    st.info(summary.tldr)

    if summary.warnings:
        with st.expander(f"⚠️ {len(summary.warnings)} cảnh báo", expanded=False):
            for warning in summary.warnings:
                st.markdown(f"- {warning}")

    st.subheader("Ý chính cả buổi")
    for index, point in enumerate(summary.key_points):
        cited_line(point.text, list(point.citations), chunks, f"sk{index}")

    st.subheader("Nội dung theo mục")
    for item in summary.outline:
        with st.expander(f"{item.section_order}. {item.section_title}"):
            st.write(item.abstract)
            st.caption("Trích dẫn: " + "  ".join(f"`{c}`" for c in item.citations))

            detail = section_data.get(item.section_id)
            if detail:
                st.markdown("**Ý chính của mục**")
                for point in detail["key_points"]:
                    st.markdown(
                        f"- {point['text']} "
                        + " ".join(f"`{c}`" for c in point["citations"])
                    )

            if st.toggle("Xem đoạn transcript gốc", key=f"raw-{item.section_id}"):
                for chunk in loader.get_section_content(item.section_id):
                    show_chunk(chunk)
                    st.divider()

    if summary.open_questions:
        st.subheader("Câu hỏi còn để ngỏ")
        for index, question in enumerate(summary.open_questions):
            cited_line(question.text, list(question.citations), chunks, f"oq{index}")

    if summary.concepts:
        st.subheader("Khái niệm")
        st.write("  ·  ".join(summary.concepts))


# --- Tab 2 ------------------------------------------------------------------

with tab_section:
    if not section_data:
        st.info("Chưa có tóm tắt mục nào.")
    else:
        ordered = sorted(section_data.values(), key=lambda item: item["section_order"])
        choice = st.selectbox(
            "Chọn mục",
            options=[item["section_id"] for item in ordered],
            format_func=lambda sid: (
                f"{section_data[sid]['section_order']}. {section_data[sid]['section_title']}"
            ),
        )

        started = time.perf_counter()
        detail = SectionSummary.model_validate(section_data[choice])
        elapsed_ms = (time.perf_counter() - started) * 1000
        st.caption(f"Tra từ artifact trong {elapsed_ms:.1f} ms · 0 lời gọi LLM")

        left, right = st.columns([3, 2])
        with left:
            st.markdown(render_section(detail))
        with right:
            st.markdown("#### Transcript gốc")
            for chunk in loader.get_section_content(choice):
                show_chunk(chunk)
                st.divider()


# --- Tab 3 ------------------------------------------------------------------

with tab_check:
    st.markdown(
        "Ba cột dưới đây tính lại **tại thời điểm render**, từ file artifact đối "
        "chiếu với transcript gốc — không tin vào validator lúc build."
    )

    valid_ids = set(chunks)
    found: set[str] = set()
    for path in (settings.summaries_dir / session_id).glob("*.json"):
        found.update(re.findall(r"T\d{2}-\d{3}", path.read_text(encoding="utf-8")))

    unknown = sorted(found - valid_ids)
    cross = sorted(c for c in found if not c.startswith(session_id))
    outline_ids = [item.section_id for item in summary.outline]
    expected_ids = [ref.section_id for ref in section_refs]

    checks = [
        ("Citation không tồn tại trong buổi", len(unknown), unknown),
        ("Citation trỏ sang buổi khác", len(cross), cross),
        (
            "Mục thiếu trong outline",
            len(set(expected_ids) - set(outline_ids)),
            sorted(set(expected_ids) - set(outline_ids)),
        ),
    ]

    for label, count, offenders in checks:
        if count == 0:
            st.success(f"✅ {label}: 0")
        else:
            st.error(f"❌ {label}: {count} — {', '.join(offenders)}")

    st.divider()
    left, right = st.columns(2)
    left.metric(
        "Tỷ lệ đoạn được trích dẫn",
        f"{coverage.cited_chunks / coverage.total_chunks:.0%}",
        help="Bản tóm tắt tốt không trích mọi câu. Ngưỡng plan đặt là ≥ 30%.",
    )
    right.metric("Thứ tự mục", "đúng" if outline_ids == expected_ids else "SAI")

    with st.expander("Toàn bộ JSON của session summary"):
        st.json(data)
