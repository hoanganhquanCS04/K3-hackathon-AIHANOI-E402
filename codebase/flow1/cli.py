"""Giao diện dòng lệnh của luồng 1. Chủ: M2 → M4.

    python -m flow1 index                          # dựng BM25, chạy một lần
    python -m flow1 ask "cơ chế attention là gì"
    python -m flow1 ask "chỉ số thành công" --session 02    # đường correction

Mã thoát:
    0  trả lời được, HOẶC từ chối/hỏi lại đúng — từ chối đúng cũng là thành công
    1  lỗi gọi model
    3  chưa dựng index, hoặc thiếu data pack

Ba biến `_*_CALL` mặc định None (tức là dùng provider thật). Test monkeypatch chúng
để chạy offline — không cần mạng, không cần API key.
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


def _run_ask(question: str, session: str | None) -> int:
    from flow1.parse import TRANSCRIPT_DIR, parse_all

    segs = parse_all() if TRANSCRIPT_DIR.exists() else None

    try:
        result = ask(
            question,
            session=session,
            segs=segs,
            classify_call=_CLASSIFY_CALL,
            answer_call=_ANSWER_CALL,
            check_citations=_CHECK_CITATIONS,
        )
    except IndexMissing as exc:
        print(exc)
        return 3

    print(render(result, segs or []))
    return 1 if result.outcome == "error" else 0


def _run_index(with_embedding: bool = False) -> int:
    try:
        count = build_from_data()
    except FileNotFoundError as exc:
        print(
            f"Không đọc được data pack ({exc}). Cần data/vlearn-pack/transcript/ "
            f"có mặt để dựng index."
        )
        return 3
    print(f"Đã index {count} chunk.")

    if with_embedding:
        from flow1.embed import EMB_PATH, MODEL_NAME, build_embeddings
        from flow1.index import load

        chunks, _ = load()
        print(f"Đang embed bằng {MODEL_NAME} (chạy local, không gửi data ra ngoài)...")
        n = build_embeddings(chunks)
        print(f"Đã ghi {n} vector → {EMB_PATH}")

    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="flow1", description="Tra cứu nội dung buổi học, có 4 cổng từ chối."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    index_parser = sub.add_parser("index", help="Dựng BM25 index từ data pack.")
    index_parser.add_argument(
        "--with-embedding", action="store_true",
        help="Thêm embedding local (multilingual-e5-small). Chậm hơn, chất lượng khớp tốt hơn.",
    )

    ask_parser = sub.add_parser("ask", help="Hỏi một câu về nội dung khoá.")
    ask_parser.add_argument("question", help="Câu hỏi, đặt trong ngoặc kép.")
    ask_parser.add_argument(
        "--session", default=None,
        help="Giới hạn trong một buổi, ví dụ 02. Dùng khi hệ thống hỏi lại buổi nào.",
    )

    args = parser.parse_args(argv)

    if args.command == "index":
        return _run_index(args.with_embedding)
    return _run_ask(args.question, args.session)
