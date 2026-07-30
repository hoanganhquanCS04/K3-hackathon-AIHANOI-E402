"""Sổ tay buổi học — giao diện demo.

Chạy:  streamlit run codebase/app.py

Hai màn hình:
  1. Danh sách 6 buổi học
  2. Buổi đang mở:  slide bên trái  |  chat bên phải  (mục lục nằm trong gợi ý chat)

Hai điểm vào — bấm gợi ý, hoặc gõ câu hỏi — đi vào CÙNG một handler `handle()`.
Đó là chủ đích: nút để demo không bị gõ sai, ô chat để chứng minh router hoạt động.
"""

from __future__ import annotations

import streamlit as st

from stubs import (
    answer_query,
    build_recap,
    get_session,
    load_outline,
    refusal,
    resolve_part,
    route,
    summarize_part,
)
from theme import BASE_CSS, campus_data_uri, hero_css

st.set_page_config(page_title="Sổ tay buổi học · VLearn", page_icon="📓", layout="wide")
st.markdown(BASE_CSS, unsafe_allow_html=True)

BLANK = '<span class="blank">ý tóm tắt do AI sinh sẽ nằm ở đây</span>'


# ─────────────────────────────────────────────────────────────────────────────
# State  — chính là {session, outline, done} trong sơ đồ luồng
# ─────────────────────────────────────────────────────────────────────────────

SESSIONS = load_outline()
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


def handle(query: str, session: dict) -> None:
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
        say("ai", "recap", build_recap(session, st.session_state.done))
        return

    if intent == "tom_tat_phan":
        idx, why = resolve_part(r["part_ref"], session, st.session_state.done)
        if idx is None:
            say("ai", "text", f"Mình chưa xác định được phần nào ({why}).")
            say("ai", "outline", session)
            return
        result = summarize_part(session, idx)
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
            '<div class="mock-banner"><b>Bản giả lập giao diện.</b> Mục lục, mã đoạn, '
            "câu nguyên văn và mọi con số là <b>thật</b> — đọc trực tiếp từ transcript. "
            "Riêng <b>câu tóm tắt còn là chỗ trống</b>, chưa gọi AI.</div>",
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
                # HAX G2 — nói thẳng buổi nào mình không chắc là buổi nào
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
    """Chỗ giữ chỗ cho slide bài giảng.

    Khi có slide thật: bỏ khối HTML này, thay bằng
        st.image(f"slides/{session['id']}-{part['idx']:02d}.png")
    Bố cục xung quanh không cần đổi.
    """
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
                return
            for i, kp in enumerate(p["key_points"], 1):
                tag = ' <b>· một học viên nêu</b>' if kp["has_student_speech"] else ""
                st.markdown(
                    f'{i}. {BLANK} <span class="cite">{kp["cite"][0]}</span>{tag}'
                    f'<blockquote class="q">“{kp["quote"]}”</blockquote>',
                    unsafe_allow_html=True,
                )
            for g in p["gaps"]:
                st.caption(f"⚠ Chỗ bản ghi thiếu: {g}")

        elif kind == "recap":
            s = p["session"]
            st.markdown(f"### Sổ tay buổi {s['id']} — {s['title']}")
            st.caption(
                f"Gộp từ {p['n_parts_done']}/{p['n_parts_total']} phần đã tóm · "
                f"độ tin cậy định vị buổi: {s['locate_confidence'].upper()}"
            )
            st.markdown("**Ý chính**")
            for i, kp in enumerate(p["key_points"], 1):
                st.markdown(
                    f'{i}. {BLANK} <span class="cite">{kp["cite"][0]}</span>',
                    unsafe_allow_html=True,
                )
            if p["student_points"]:
                st.markdown("**Học viên nêu trong buổi**")
                for kp in p["student_points"]:
                    st.markdown(
                        f'- {BLANK} <span class="cite">{kp["cite"][0]}</span>',
                        unsafe_allow_html=True,
                    )
            if p["gaps"]:
                st.markdown("**⚠ Chỗ bản ghi thiếu**")
                for g in p["gaps"]:
                    st.markdown(f"- {g}")
            if p["n_parts_done"] < p["n_parts_total"]:
                st.info(f"Còn {p['n_parts_total'] - p['n_parts_done']} phần chưa tóm — "
                        "sổ tay sẽ đầy hơn khi tóm tiếp.")

        elif kind == "answer":
            for c in p["claims"]:
                st.markdown(
                    f'- {BLANK} <span class="cite">{c["cite"][0]}</span>'
                    f'<blockquote class="q">“{c["quote"]}”</blockquote>',
                    unsafe_allow_html=True,
                )
            st.caption(p["note"])


def render_suggestions(session: dict) -> None:
    """Một gợi ý duy nhất: mở mục lục.

    Cố ý KHÔNG có nút "tóm phần 1/2/3…". Mục lục do bước này in ra đã liệt kê đủ các
    phần; từ đó người dùng gõ tiếp. Giữ đúng một cửa vào bằng ngôn ngữ tự nhiên nghĩa
    là router phải thật sự hoạt động — không có nút nào đi đường tắt qua nó.
    """
    if st.button("🔎 Buổi này có mấy phần?", key="sgtoc", width="stretch"):
        st.session_state.pending = "buổi này có mấy phần?"
        st.rerun()


def screen_session(session: dict) -> None:
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

if st.session_state.sid is None:
    screen_list()
else:
    session = get_session(SESSIONS, st.session_state.sid)
    if session is None:
        st.session_state.sid = None
        st.rerun()

    # xử lý query đang chờ TRƯỚC khi vẽ, để tin nhắn mới hiện ngay trong lượt này
    if st.session_state.pending:
        q, st.session_state.pending = st.session_state.pending, None
        handle(q, session)

    screen_session(session)
