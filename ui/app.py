import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UI_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

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
    from helpers import branch_table
except ImportError:
    from ui.live import (
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
    from ui.theme import BASE_CSS, campus_data_uri, hero_css
    from ui.helpers import branch_table

if st.runtime.exists():
    st.set_page_config(page_title="Sổ tay buổi học · VLearn", page_icon="📓", layout="wide")
    st.markdown(BASE_CSS, unsafe_allow_html=True)

BLANK = '<span class="blank">ý tóm tắt do AI sinh sẽ nằm ở đây</span>'


def claim_html(kp: dict) -> str:
    return kp["claim"] if kp.get("claim") else BLANK


try:
    SESSIONS = load_outline()
except Exception:
    SESSIONS = []

if st.runtime.exists():
    st.session_state.setdefault("sid", "01" if SESSIONS else None)
    st.session_state.setdefault("msgs", [])
    st.session_state.setdefault("done", {})
    st.session_state.setdefault("slide_part", 1)
    st.session_state.setdefault("pending", None)


def open_session(sid: str) -> None:
    st.session_state.update(sid=sid, msgs=[], done={}, slide_part=1, pending=None)


def say(role: str, kind: str, payload) -> None:
    st.session_state.msgs.append({"role": role, "kind": kind, "payload": payload})


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

    ans = answer_query(session, query, toggles=toggles)
    ans["_stats"] = last_stats()
    say("ai", "answer", ans)


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

    with st.container(border=True):
        st.markdown(
            '<div class="mock-banner"><b>Luồng TÓM TẮT (Luồng 2)</b>: Tóm tắt từng phần & gộp sổ tay cả buổi qua Map-Reduce.<br>'
            "<b>Luồng TRA CỨU (Luồng 1)</b>: Tra cứu nội dung chi tiết qua RRF 3 nhánh (BM25, Qdrant, Neo4j) có 4 cổng từ chối.</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.markdown(f"### 📚 Chọn 1 trong {len(SESSIONS)} buổi học bên dưới:")

    for i, s in enumerate(SESSIONS, start=1):
        with st.container(border=True):
            badge, body, action = st.columns([0.1, 0.7, 0.2], vertical_alignment="center")
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
                if st.button(f"Mở Buổi {s['id']}", key=f"open_home_{s['id']}", use_container_width=True, type="primary"):
                    open_session(s["id"])
                    st.rerun()


def render_slide(session: dict) -> None:
    part = session["parts"][st.session_state.slide_part - 1]
    st.markdown(
        f"""
        <div class="slide-frame">
          <div class="slide-kicker">Buổi {session['id']} · Phần {part['idx']}</div>
          <div class="slide-title">{part['title']}</div>
          <div class="slide-foot">
            <span class="slide-stamp">SLIDE MINH HOẠ</span>
            <span>Phần {part['idx']} / {len(session['parts'])}</span>
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
    if stats.seconds:
        bits.append(f"⏱️ Tổng thời gian: **{stats.seconds:.2f}s**")
    if stats.llm_calls:
        bits.append(f"🔴 gọi LLM **{stats.llm_calls}** lần")
    if stats.cache_hits:
        bits.append(f"⚡ dùng cache {stats.cache_hits} lần")
    if bits:
        st.caption(" · ".join(bits))

    for w in stats.warnings[:3]:
        st.caption(f"⚠ {w}")

    if getattr(stats, "stage_timings", None):
        with st.expander("⏱️ Chi tiết thời gian từng bước (Latency Breakdown)", expanded=False):
            data_rows = []
            for stage_name, ms, note in stats.stage_timings:
                data_rows.append({
                    "Bước / Công đoạn": stage_name,
                    "Thời gian (ms)": f"{ms:.1f} ms",
                    "Ghi chú": note or "—"
                })
            st.dataframe(data_rows, use_container_width=True, hide_index=True)


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
            if p.get("abstract"):
                st.info(p["abstract"])
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
                f"Tổng hợp từ toàn bộ {s['n_sections']} mục · {s['n_segments']} đoạn "
                f"đã đọc · độ tin cậy định vị buổi: {s['locate_confidence'].upper()}"
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
            if p.get("claims"):
                for c in p["claims"]:
                    st.markdown(
                        f'- {claim_html(c)} <span class="cite">{c["cite"][0]}</span>'
                        f'<blockquote class="q">“{c["quote"]}”</blockquote>',
                        unsafe_allow_html=True,
                    )
            if p.get("note"):
                st.caption(p["note"])
            render_stats(p.get("_stats"))


def render_suggestions(session: dict) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📌 Tóm phần 1", key="sg_p1", use_container_width=True):
            st.session_state.pending = "tóm phần 1"
            st.rerun()
    with c2:
        if st.button("📑 Tóm cả buổi", key="sg_all", use_container_width=True):
            st.session_state.pending = "tóm cả buổi"
            st.rerun()
    with c3:
        if st.button("🔎 Mục lục buổi này", key="sg_toc", use_container_width=True):
            st.session_state.pending = "buổi này có mấy phần?"
            st.rerun()


def screen_session(session: dict, toggles: Toggles) -> None:
    st.markdown(f"## 📖 Buổi {session['id']} — {session['title']}")

    left, right = st.columns([0.45, 0.55], gap="medium")

    with left:
        render_slide(session)

    with right:
        n_done = len(st.session_state.done)
        st.markdown(f"### 💬 Trợ lý AI Buổi {session['id']}  <small style='font-size:0.8rem; color:#64748b;'>(đã tóm {n_done}/{len(session['parts'])} phần)</small>", unsafe_allow_html=True)

        box = st.container(height=480)
        with box:
            if not st.session_state.msgs:
                with st.chat_message("assistant"):
                    st.write(
                        f"Xin chào! Buổi này gồm **{len(session['parts'])} phần**. "
                        "Bạn có thể gõ *“tóm phần 1”*, *“tóm cả buổi”*, hoặc đặt câu hỏi tra cứu kiến thức bên dưới!"
                    )
            for m in st.session_state.msgs:
                render_msg(m)

        render_suggestions(session)

        if typed := st.chat_input("Nhập câu hỏi hoặc yêu cầu (ví dụ: tóm phần 1)..."):
            st.session_state.pending = typed
            st.rerun()


def run_app():
    with st.sidebar:
        st.title("📓 Sổ Tay Buổi Học")
        st.markdown("---")

        st.markdown("### 📚 Chọn Buổi Học")
        options = ["Trang chủ (Danh sách)"] + [f"Buổi {s['id']} — {s['title'][:25]}..." for s in SESSIONS]
        
        current_idx = 0
        if st.session_state.sid:
            for idx, s in enumerate(SESSIONS, start=1):
                if s["id"] == st.session_state.sid:
                    current_idx = idx
                    break
                    
        selected = st.selectbox(
            "Danh sách buổi học",
            options=options,
            index=current_idx,
            label_visibility="collapsed"
        )
        
        if selected == "Trang chủ (Danh sách)":
            if st.session_state.sid is not None:
                st.session_state.sid = None
                st.rerun()
        else:
            sid_chosen = selected.split(" — ")[0].replace("Buổi ", "").strip()
            if st.session_state.sid != sid_chosen:
                open_session(sid_chosen)
                st.rerun()

        st.markdown("---")
        st.markdown("#### ⚙️ Cấu hình RRF (Luồng 1)")
        use_bm25 = st.toggle("BM25 (offline)", value=True)
        use_qdrant = st.toggle("Qdrant (vector)", value=True)
        use_neo4j = st.toggle("Neo4j (graph)", value=True)
        toggles = Toggles(bm25=use_bm25, qdrant=use_qdrant, neo4j=use_neo4j)

        st.markdown("---")
        st.markdown("#### ⚡ Chế độ Real-time AI")
        st.caption(backend_label())
        force = st.toggle(
            "Bỏ qua cache",
            value=False,
            help="Bật thì mỗi lần tóm đều gọi LLM mới.",
        )
        set_force(force)

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
