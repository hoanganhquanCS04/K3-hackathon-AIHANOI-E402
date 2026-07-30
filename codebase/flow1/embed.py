"""Embedding LOCAL + hợp nhất RRF. Chủ: M2. Bước cắt đầu tiên khi trễ.

BẢO MẬT DATA: model chạy trên máy, không byte transcript nào rời máy. Embed cả
corpus qua API là gửi ~445.000 ký tự ra provider ngoài — không phải "phần tối
thiểu cần thiết" theo điều 4 mục bảo mật data của khoá. Bước generate ở cổng 2
gửi 5 chunk ra API thì hợp lệ, đó mới đúng nghĩa tối thiểu.

e5 ĐÒI PREFIX: passage phải là "passage: <text>", query phải là "query: <text>".
Bỏ prefix là mất phần lớn chất lượng của model này mà không có lỗi nào báo ra.

RRF thay vì cộng điểm: BM25 và cosine không cùng thang. Cộng thẳng là so hai đơn
vị khác nhau.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from flow1.index import STORE_DIR
from flow1.models import Chunk

EMB_PATH = STORE_DIR / "emb.npy"
MODEL_NAME = "intfloat/multilingual-e5-small"

_model = None


def _get_model():
    """Nạp model một lần. Import trong hàm để thiếu package không làm vỡ import flow1."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def build_embeddings(chunks: list[Chunk], path: Path = EMB_PATH) -> int:
    """Embed toàn bộ chunk, ghi ra .npy. Trả số vector."""
    texts = [f"passage: {c.index_text}" for c in chunks]
    vectors = _normalise(np.asarray(_get_model().encode(texts), dtype="float32"))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, vectors)
    return len(vectors)


def load_embeddings(path: Path = EMB_PATH) -> np.ndarray | None:
    """Nạp vector. None khi chưa có file — gọi retrieve vẫn chạy, chỉ là BM25 thuần."""
    if not path.exists():
        return None
    return np.load(path)


def embed_query(text: str) -> np.ndarray:
    vector = np.asarray(_get_model().encode([f"query: {text}"]), dtype="float32")
    return _normalise(vector)[0]


def rrf(rankings: list[list[int]], k: int) -> dict[int, float]:
    """Reciprocal Rank Fusion. `rankings` = danh sách các list chỉ số, đã sắp tốt→kém.

    score(doc) = Σ 1/(k + rank_i(doc) + 1), rank 0-based.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)
    return scores
