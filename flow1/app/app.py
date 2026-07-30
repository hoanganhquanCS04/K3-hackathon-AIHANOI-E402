"""Sổ tay buổi học — giao diện demo.

Chạy:  streamlit run flow1/app/app.py
"""

from __future__ import annotations

import streamlit as st
from flow1.retrieve import Toggles
try:
    from live import (
        answer_query,
        backend_label,
        build_recap,
        get_session,
        last_stats,
        load_outline,
        refusal,
        resolve_part,
        route,
        set_force,
        summarize_part,
    )
    from theme import BASE_CSS, campus_data_uri, hero_css
except ImportError:
    from flow1.app.live import (
        answer_query,
        backend_label,
        build_recap,
        get_session,
        last_stats,
        load_outline,
        refusal,
        resolve_part,
        route,
        set_force,
        summarize_part,
    )
    from flow1.app.theme import BASE_CSS, campus_data_uri, hero_css

if st.runtime.exists():
    st.set_page_config(page_title="Sổ tay buổi học · VLearn", page_icon="📓", layout="wide")
    st.markdown(BASE_CSS, unsafe_allow_html=True)

BLANK = '<span class="blank">ý tóm tắt do AI sinh sẽ nằm ở đây</span>'


try:
    from helpers import branch_table
except ImportError:
    from flow1.app.helpers import branch_table


def claim_html(kp: dict) -> str:
    """Luồng tóm tắt đã thật; luồng tra cứu thì chưa. Chỗ nào chưa có thì vẫn để
    trống nhìn rõ là trống, đúng tinh thần ban đầu của bản giả lập."""

    return kp["claim"] if kp.get("claim") else BLANK


# ─────────────────────────────────────────────────────────────────────────────
# State  — chính là {session, outline, done} trong sơ đồ luồng
# ─────────────────────────────────────────────────────────────────────────────

try:
    SESSIONS = load_outline()
except Exception:
    SESSIONS = []

if st.runtime.exists():
    st.session_state.setdefault("sid", None)      # buổi đang mở
    st.session_state.setdefault("msgs", [])       # lịch sử hội thoại
    st.session_state.setdefault("done", {})       # {part_idx: kết quả tóm}
    st.session_state.setdefault("slide_part", 1)  # phần slide đang hiển thị
    st.session_state.setdefault("pending", None)  # query chờ xử lý (từ nút hoặc ô chat)


def open_session(sid: str) -> None:
    st.session_state.update(sid=sid, msgs=[], done={}, slide_part=1, pending=None)


def say(role: str, kind: str, payload) -> None:
    st.session_state.msgs.append({"role": role, "kind": kind, "payload": payload})


# ─────────────────────────────────────────────────────────────────────────────
# Handler — một cửa duy nhất cho cả nút bấm và ô chat
# ─────────────────────────────────────────────────────────────────────────────


def handle(query: str, session: dict, toggles: Toggles | None = None) -> None:
    say("user", "text", query)
    r = route(query, st.session_state)
    intent = r["intent"]

    if intent in ("logistics", "ngoai_pham_vi", "chao_hoi"):
        say("ai", "text", refusal(intent, session))
        return

    if intent == "xem_muc_luc":
        say("ai", "outline", session)
        return

    if intent == "tom_tat_thieu_slot":
        say("ai", "text",
            f"Bạn muốn tóm phần nào? Buổi này có {len(session['parts'])} phần — "
            "bấm gợi ý bên dưới, hoặc nói “tóm cả buổi”.")
        return

    if intent == "tom_tat_buoi":
        if not st.session_state.done:
            say("ai", "text",
                "Chưa có phần nào được tóm. Sổ tay được gộp từ các phần đã tóm — "
                "bắt đầu bằng phần 1 nhé.")
            say("ai", "outline", session)
            return
        with st.spinner("Đang gộp sổ tay..."):
            recap = build_recap(session, st.session_state.done)
        recap["_stats"] = last_stats()
        say("ai", "recap", recap)
        return

    if intent == "tom_tat_phan":
        idx, why = resolve_part(r["part_ref"], session, st.session_state.done)
        if idx is None:
            say("ai", "text", f"Mình chưa xác định được phần nào ({why}).")
            say("ai", "outline", session)
            return
        n_sec = len(session["parts"][idx - 1]["section_titles"])
        with st.spinner(f"Đang đọc {n_sec} mục của phần {idx} và gọi AI..."):
            result = summarize_part(session, idx)
        result["_stats"] = last_stats()
        st.session_state.done[idx] = result
        st.session_state.slide_part = idx
        say("ai", "part", result)
        return

    say("ai", "answer", answer_query(session, query))


# ─────────────────────────────────────────────────────────────────────────────
# Màn hình 1 — danh sách 6 buổi
# ─────────────────────────────────────────────────────────────────────────────


def screen_list() -> None:
    uri = campus_data_uri()
    st.markdown(hero_css(uri), unsafe_allow_html=True)

    st.markdown(
        '<div class="hero-kicker">VLearn · VinUni AI Thực Chiến</div>'
        '<div class="hero-title">Sổ tay buổi học</div>'
        '<div class="hero-sub">Nghỉ buổi hay mất mạch? Chọn buổi, tóm dần từng phần — '
        "mỗi ý đều bấm được về nguyên văn lời giảng.</div>",
        unsafe_allow_html=True,
    )
    st.write("")
    st.write("")

    with st.container(border=True):
        st.markdown(
            '<div class="mock-banner"><b>Luồng TÓM TẮT đã chạy thật.</b> Gõ “tóm phần 1” '
            "là gọi AI ngay lúc đó trên chính bản ghi của buổi. Mục lục, mã đoạn, câu "
            "nguyên văn và mọi con số đọc trực tiếp từ transcript. "
            "<b>Luồng TRA CỨU</b> sử dụng RRF 3 nhánh (BM25, Qdrant, Neo4j).</div>",
            unsafe_allow_html=True,
        )
        if uri is None:
            st.caption("Nền: chưa có `codebase/assets/campus.jpg` — đang dùng gradient thay thế.")

    st.write("")
    st.markdown(f"##### {len(SESSIONS)} buổi đã có bản ghi")

    for i, s in enumerate(SESSIONS, start=1):
        with st.container(border=True):
            badge, body, action = st.columns([0.09, 0.73, 0.18], vertical_alignment="center")
            with badge:
                st.markdown(
                    f'<div class="day-badge"><span>BUỔI</span><b>{s["id"]}</b></div>',
                    unsafe_allow_html=True,
                )
            with body:
                conf = s["locate_confidence"].lower()
                warn = (
                    ""
                    if conf == "cao"
                    else f'<span class="warn-pill">⚠ định vị buổi: {conf}</span>'
                )
                st.markdown(
                    f'<div class="sess-title">{s["title"]} {warn}</div>'
                    f'<div class="sess-meta">{len(s["parts"])} phần · '
                    f'{s["n_sections"]} mục nhỏ · {s["n_segments"]} đoạn · '
                    f'{s["n_unclear"]} đoạn bản ghi thiếu</div>',
                    unsafe_allow_html=True,
                )
            with action:
                if st.button("Mở buổi này", key=f"open{s['id']}", width="stretch",
                             type="primary"):
                    open_session(s["id"])
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Màn hình 2 — slide + chat
# ─────────────────────────────────────────────────────────────────────────────


def render_slide(session: dict) -> None:
    part = session["parts"][st.session_state.slide_part - 1]
    st.markdown(
        f"""
        <div class="slide-frame">
          <div class="slide-kicker">Buổi {session['id']} · Phần {part['idx']}</div>
          <div class="slide-title">{part['title']}</div>
          <div class="slide-foot">
            <span class="slide-stamp">SLIDE MINH HOẠ</span>
            <span>{part['idx']} / {len(session['parts'])}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f"Phần này gồm {len(part['section_titles'])} mục "
                     f"(mục {part['section_range'][0]}–{part['section_range'][1]} của buổi)"):
        for t in part["section_titles"]:
            st.markdown(f"- {t}")
        st.caption(
            f"{part['n_segments']} đoạn · {part['seg_ids'][0]} → {part['seg_ids'][-1]}"
            + (f" · {part['n_activity']} đoạn hoạt động lớp" if part["n_activity"] else "")
        )


def render_stats(stats) -> None:
    if stats is None:
        return
    bits = []
    if stats.llm_calls:
        bits.append(f"🔴 gọi LLM **{stats.llm_calls}** lần")
    if stats.cache_hits:
        bits.append(f"⚡ dùng cache {stats.cache_hits} lần")
    if stats.seconds:
        bits.append(f"{stats.seconds:.1f}s")
    if bits:
        st.caption(" · ".join(bits))
    for w in stats.warnings[:3]:
        st.caption(f"⚠ {w}")


def render_msg(m: dict) -> None:
    kind, p = m["kind"], m["payload"]
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        if kind == "text":
            st.write(p)

        elif kind == "outline":
            st.write(f"**Buổi {p['id']}** có **{len(p['parts'])} phần**:")
            for part in p["parts"]:
                mark = "✓" if part["idx"] in st.session_state.done else "○"
                warn = "  ⚠ chủ yếu là hoạt động lớp, sẽ không tóm" if part["activity_heavy"] else ""
                st.markdown(
                    f"{mark} **Phần {part['idx']}** · {part['title']}  \n"
                    f"&nbsp;&nbsp;&nbsp;<small>{part['n_segments']} đoạn · "
                    f"~{part['n_chars']:,} ký tự{warn}</small>",
                    unsafe_allow_html=True,
                )
            st.caption('Gõ “tóm phần 2” để tóm một phần · “tóm cả buổi” để gộp sổ tay.')

        elif kind == "part":
            part = p["part"]
            st.markdown(f"**Phần {part['idx']} · {part['title']}**")
            if p["skipped"]:
                st.warning(f"Phần này mình không tóm. {p['reason']}")
                render_stats(p.get("_stats"))
                return
            for i, kp in enumerate(p["key_points"], 1):
                tag = ' <b>· một học viên nêu</b>' if kp["has_student_speech"] else ""
                cites = " ".join(f'<span class="cite">{c}</span>' for c in kp["cite"])
                st.markdown(
                    f'{i}. {claim_html(kp)} {cites}{tag}'
                    f'<blockquote class="q">“{kp["quote"]}”</blockquote>',
                    unsafe_allow_html=True,
                )
            for g in p["gaps"]:
                st.caption(f"⚠ Chỗ bản ghi thiếu: {g}")
            render_stats(p.get("_stats"))

        elif kind == "recap":
            s = p["session"]
            st.markdown(f"### Sổ tay buổi {s['id']} — {s['title']}")
            st.caption(
                f"Gộp từ {p['n_parts_done']}/{p['n_parts_total']} phần đã tóm · "
                f"độ tin cậy định vị buổi: {s['locate_confidence'].upper()}"
            )
            if p.get("tldr"):
                st.info(p["tldr"])
            st.markdown("**Ý chính**")
            for i, kp in enumerate(p["key_points"], 1):
                cites = " ".join(f'<span class="cite">{c}</span>' for c in kp["cite"])
                st.markdown(f"{i}. {claim_html(kp)} {cites}", unsafe_allow_html=True)
            if p["student_points"]:
                st.markdown("**Câu hỏi học viên nêu trong buổi**")
                for kp in p["student_points"]:
                    cites = " ".join(f'<span class="cite">{c}</span>' for c in kp["cite"])
                    st.markdown(f"- {claim_html(kp)} {cites}", unsafe_allow_html=True)
            if p["gaps"]:
                st.markdown("**⚠ Chỗ bản ghi thiếu**")
                for g in p["gaps"]:
                    st.markdown(f"- {g}")
            if p["n_parts_done"] < p["n_parts_total"]:
                st.info(f"Còn {p['n_parts_total'] - p['n_parts_done']} phần chưa tóm — "
                        "sổ tay mới gộp bằng code từ các phần đã tóm. Tóm đủ mọi phần "
                        "thì mới chạy bước REDUCE để viết lại thành một mạch.")
            render_stats(p.get("_stats"))

        elif kind == "answer":
            for c in p["claims"]:
                st.markdown(
                    f'- {claim_html(c)} <span class="cite">{c["cite"][0]}</span>'
                    f'<blockquote class="q">“{c["quote"]}”</blockquote>',
                    unsafe_allow_html=True,
                )
            st.caption(p["note"])


def render_suggestions(session: dict) -> None:
    if st.button("🔎 Buổi này có mấy phần?", key="sgtoc", width="stretch"):
        st.session_state.pending = "buổi này có mấy phần?"
        st.rerun()


def screen_session(session: dict, toggles: Toggles) -> None:
    top = st.columns([0.1, 0.9], vertical_alignment="center")
    with top[0]:
        if st.button("← Buổi khác", width="stretch"):
            st.session_state.sid = None
            st.rerun()
    with top[1]:
        st.markdown(f"**Buổi {session['id']}** — {session['title']}")

    left, right = st.columns([0.54, 0.46], gap="large")

    with left:
        render_slide(session)

    with right:
        n_done = len(st.session_state.done)
        st.markdown(f"#### Hỏi về buổi này  <small>· đã tóm {n_done}/"
                    f"{len(session['parts'])} phần</small>", unsafe_allow_html=True)

        box = st.container(height=430)
        with box:
            if not st.session_state.msgs:
                with st.chat_message("assistant"):
                    st.write(
                        f"Buổi này có **{len(session['parts'])} phần**. Hỏi mình bất cứ gì "
                        "về buổi — ví dụ *“buổi này có mấy phần”*, *“tóm phần 1”*, "
                        "hoặc một câu về nội dung đã giảng."
                    )
            for m in st.session_state.msgs:
                render_msg(m)

        render_suggestions(session)

        if typed := st.chat_input("Ví dụ: tóm tắt phần I cho tôi"):
            st.session_state.pending = typed
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────

def run_app():
    with st.sidebar:
        st.markdown("#### Nhanh truy van (RRF)")
        use_bm25 = st.toggle("BM25 (offline)", value=True)
        use_qdrant = st.toggle("Qdrant (vector)", value=True)
        use_neo4j = st.toggle("Neo4j (graph)", value=True)
        toggles = Toggles(bm25=use_bm25, qdrant=use_qdrant, neo4j=use_neo4j)

        st.markdown("---")
        st.markdown("#### Che do chay")
        st.caption(backend_label())
        force = st.toggle(
            "Bỏ qua cache",
            value=False,
            help="Bật thì mỗi lần tóm đều gọi LLM mới, kể cả phần đã tóm rồi. "
            "Dùng để tự kiểm chứng là AI chạy thật chứ không đọc file có sẵn.",
        )
        set_force(force)
        if force:
            st.warning("Mỗi lượt tóm đều tốn API.")

    if st.session_state.sid is None:
        screen_list()
    else:
        session = get_session(SESSIONS, st.session_state.sid)
        if session is None:
            st.session_state.sid = None
            st.rerun()

        if st.session_state.pending:
            q, st.session_state.pending = st.session_state.pending, None
            handle(q, session, toggles=toggles)

        screen_session(session, toggles=toggles)


if st.runtime.exists():
    run_app()
