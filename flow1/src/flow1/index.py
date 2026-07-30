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

from flow1.models import Chunk, Seg
from flow1.store import Store

STORE_DIR = Path(__file__).resolve().parents[2] / "store"
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


def save(store: Store, path: Path = BM25_PATH) -> None:
    """Ghi ca Store vao mot file pickle. Nap lai can rank_bm25 da cai."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(
            {
                "atomics": store.atomics,
                "contexts": store.contexts,
                "code_to_contexts": store.code_to_contexts,
                "bm25": store.bm25,
            },
            handle,
        )


def load(path: Path = BM25_PATH) -> Store:
    """Nap lai Store da luu. Nem `IndexMissing` kem lenh sua neu thieu/cu."""
    if not path.exists():
        raise IndexMissing(
            f"Chua co index tai {path}. Dung truoc bang:  python -m flow1 index"
        )
    with path.open("rb") as handle:
        blob = pickle.load(handle)
    if "atomics" not in blob:
        raise IndexMissing(
            f"Index tai {path} theo dinh dang cu (chi co chunk gop). Dung lai "
            f"bang:  python -m flow1 index"
        )
    return Store(
        atomics=blob["atomics"],
        contexts=blob["contexts"],
        code_to_contexts=blob["code_to_contexts"],
        bm25=blob["bm25"],
    )


def build_store(segs: list[Seg]) -> Store:
    """Seg -> Store. Atomic de xep hang, chunk gop de lam ngu canh."""
    from flow1.atomic import atomic_chunks, build_code_map
    from flow1.chunk import chunk_all

    contexts = chunk_all(segs)
    atomics = atomic_chunks(segs)
    return Store(
        atomics=atomics,
        contexts=contexts,
        code_to_contexts=build_code_map(contexts),
        bm25=build(atomics),
    )


def build_from_data(data_dir: Path | None = None, path: Path = BM25_PATH) -> int:
    """Doc data pack -> parse -> build store -> ghi dia. Tra so doan nguyen tu."""
    from flow1.parse import TRANSCRIPT_DIR, content_segs, parse_all

    segs = content_segs(parse_all(data_dir or TRANSCRIPT_DIR))
    store = build_store(segs)
    save(store, path)
    return len(store.atomics)
