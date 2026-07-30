r"""list[Chunk] → BM25 index trên đĩa. Chủ: M1 (khối B).

BM25 THUẦN PYTHON, CHẠY OFFLINE — không byte nào rời máy. Đây là lựa chọn có chủ ý
theo điều 4 mục bảo mật data của khoá: embed cả corpus là gửi ~445.000 ký tự
transcript ra provider ngoài, không phải "phần tối thiểu cần thiết". Lời gọi AI
thật (điều kiện tính điểm R5) nằm ở bước generate của cổng 2, không ở retrieval.

Tokenizer: casefold rồi lấy mọi cụm \w+ (Unicode-aware nên giữ nguyên dấu tiếng
Việt). Tiếng Việt tách âm tiết theo space nên BM25 khớp được từ khoá; bộ câu hỏi
của khoá này lẫn nhiều thuật ngữ Anh (RAG, attention, tool calling, embedding) —
đúng chỗ BM25 mạnh nhất.
"""

from __future__ import annotations

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from flow1.models import Chunk

STORE_DIR = Path(__file__).resolve().parents[1] / "store"
BM25_PATH = STORE_DIR / "bm25.pkl"

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class IndexMissing(Exception):
    """Chưa dựng index. Thông báo luôn kèm cách sửa."""


def tokenize(text: str) -> list[str]:
    """casefold rồi tách mọi token chữ/số/gạch dưới theo Unicode — giữ nguyên dấu tiếng Việt."""
    return _TOKEN_RE.findall(text.casefold())


def build(chunks: list[Chunk]) -> BM25Okapi:
    """Dựng BM25 trên `index_text` — có prefix session_title › section_title."""
    return BM25Okapi([tokenize(c.index_text) for c in chunks])


def save(chunks: list[Chunk], path: Path = BM25_PATH) -> None:
    """Ghi chunk + index vào một file pickle. Nạp lại cần rank_bm25 đã cài."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump({"chunks": chunks, "bm25": build(chunks)}, handle)


def load(path: Path = BM25_PATH) -> tuple[list[Chunk], BM25Okapi]:
    """Nạp lại (chunks, bm25) đã lưu. Ném `IndexMissing` kèm lệnh sửa nếu thiếu file."""
    if not path.exists():
        raise IndexMissing(
            f"Chưa có index tại {path}. Dựng trước bằng:  python -m flow1 index"
        )
    with path.open("rb") as handle:
        blob = pickle.load(handle)
    return blob["chunks"], blob["bm25"]


def build_from_data(data_dir: Path | None = None, path: Path = BM25_PATH) -> int:
    """Đọc data pack → parse → chunk → index → ghi đĩa. Trả số chunk đã index."""
    from flow1.chunk import chunk_all
    from flow1.parse import TRANSCRIPT_DIR, content_segs, parse_all

    segs = parse_all(data_dir or TRANSCRIPT_DIR)
    chunks = chunk_all(content_segs(segs))
    save(chunks, path)
    return len(chunks)
