"""Giao diện dòng lệnh của hệ thống Sổ tay buổi học (Luồng 1 + Luồng 2).

    python -m flow1 index                          # dựng BM25, chạy một lần
    python -m flow1 ask "cơ chế attention là gì"
    python -m flow1 ask "chỉ số thành công" --session 02    # đường correction
    python -m flow1 build 03                       # luồng 2: tóm tắt cả buổi 03
    python -m flow1 build 07                       # từ chối + liệt kê 6 buổi có sẵn

Mã thoát:
    0  trả lời được, HOẶC từ chối/hỏi lại đúng — từ chối đúng cũng là thành công
    1  lỗi gọi model
    3  chưa dựng index, hoặc thiếu data pack
"""

from __future__ import annotations

import argparse
import sys

from flow1.ask import ask
from flow1.index import IndexMissing, build_from_data
from flow1.render import render

_ANSWER_CALL = None
_CLASSIFY_CALL = None
_CHECK_CITATIONS = None


def _run_ask(question: str, session: str | None, want_trace: bool = False) -> int:
    from flow1.parse import TRANSCRIPT_DIR, parse_all
    from flow1.trace import new_trace

    segs = parse_all() if TRANSCRIPT_DIR.exists() else None
    trace = new_trace(question, enabled=want_trace)

    try:
        result = ask(
            question,
            session=session,
            segs=segs,
            trace=trace,
            classify_call=_CLASSIFY_CALL,
            answer_call=_ANSWER_CALL,
            check_citations=_CHECK_CITATIONS,
        )
    except IndexMissing as exc:
        print(exc)
        return 3

    print(render(result, segs or []))

    if want_trace:
        from flow1.trace_render import render_trace

        print(render_trace(trace), file=sys.stderr)
        print(f"Trace da ghi: {trace.save()}", file=sys.stderr)

    return 1 if result.outcome == "error" else 0


def _run_index() -> int:
    try:
        count = build_from_data()
    except FileNotFoundError as exc:
        print(
            f"Không đọc được data pack ({exc}). Cần data/vlearn-pack/transcript/ "
            f"có mặt để dựng index."
        )
        return 3
    print(f"Da index {count} doan nguyen tu.")
    print("Nhanh semantic lay tu Qdrant va Neo4j luc chay — khong can build them.")
    return 0


def _run_build(session_id: str) -> int:
    sid = str(session_id).zfill(2)
    if sid not in ("01", "02", "03", "04", "05", "06"):
        print(
            f"Buổi {session_id} không có trong 6 buổi đã ghi. "
            f"Hệ thống có bản ghi cho 6 buổi: 01, 02, 03, 04, 05, 06."
        )
        return 0

    try:
        from helpers import branch_table  # noqa: F401
        from live import build_recap, get_session, load_outline, summarize_part
    except ImportError:
        from flow1.app.live import build_recap, get_session, load_outline, summarize_part

    sessions = load_outline()
    session = get_session(sessions, sid)
    if not session:
        print(f"Không tìm thấy cấu trúc buổi {sid} trong outline.")
        return 3

    print(f"=== SỔ TAY BUỔI {session['id']} — {session['title']} ===")
    done = {}
    for idx in range(1, len(session["parts"]) + 1):
        print(f"Đang đọc và tóm tắt phần {idx}/{len(session['parts'])}...")
        done[idx] = summarize_part(session, idx)

    recap = build_recap(session, done)
    print("\n--- Ý CHÍNH CẢ BUỔI ---")
    for i, kp in enumerate(recap.get("key_points", []), 1):
        cites = ", ".join(kp.get("cite", []))
        claim = kp.get("claim") or kp.get("quote") or ""
        print(f"{i}. {claim} [{cites}]")

    if recap.get("gaps"):
        print("\n--- ⚠ CHỖ BẢN GHI THIẾU ---")
        for g in recap["gaps"]:
            print(f"- {g}")

    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="flow1", description="Tra cứu và tóm tắt nội dung buổi học (Luồng 1 & Luồng 2)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="Dựng BM25 index từ data pack.")

    ask_parser = sub.add_parser("ask", help="Hỏi một câu về nội dung khoá (Luồng 1).")
    ask_parser.add_argument("question", help="Câu hỏi, đặt trong ngoặc kép.")
    ask_parser.add_argument(
        "--session", default=None,
        help="Giới hạn trong một buổi, ví dụ 02. Dùng khi hệ thống hỏi lại buổi nào.",
    )
    ask_parser.add_argument(
        "--trace", action="store_true",
        help="In bang chi tiet tung chang ra stderr va ghi JSON vao flow1/trace/.",
    )

    build_parser = sub.add_parser("build", help="Sinh sổ tay 1 trang cho cả buổi học (Luồng 2).")
    build_parser.add_argument("session_id", help="Mã buổi học, ví dụ 03 hoặc 07.")

    args = parser.parse_args(argv)

    if args.command == "index":
        return _run_index()
    if args.command == "build":
        return _run_build(args.session_id)
    return _run_ask(args.question, args.session, args.trace)
