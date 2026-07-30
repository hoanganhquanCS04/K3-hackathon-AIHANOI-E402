"""Truy vấn → Retrieval. Chủ: M1 (khối B), dùng bởi cổng 1 của M2.

QUYẾT ĐỊNH THIẾT KẾ QUAN TRỌNG NHẤT của file này:

  `top1_abs` và `ratio` LUÔN tính trên điểm BM25 THÔ, không bao giờ trên điểm đã
  fuse. Điểm RRF là 1/(K+rank) — một dãy gần như cố định (1/61, 1/62, 1/63...),
  nếu `ratio` tính sau fuse sẽ luôn ≈ 1,02 bất kể câu hỏi là gì, và cổng 1 chết
  im lặng đúng vào lúc bật hybrid.

  Hệ quả tốt: hiệu chỉnh T1 MỘT LẦN là dùng được cho cả chế độ bật và tắt
  embedding. RRF chỉ đổi *thứ tự nạp chunk vào context*, không đổi *quyết định có
  đủ căn cứ hay không*.

Ba ca biên của `ratio`, mỗi ca một test:
  - mọi điểm = 0  → (0.0, 0.0) → cổng 1 chặn
  - mean(top2..5) = 0 mà top1 > 0 (đúng 1 chunk khớp, thường là câu chứa token
    hiếm như "lab" hay "pretrain") → ratio = inf, QUA cổng ratio. Chỉ sàn tuyệt
    đối chặn được ca này — đó là lý do cổng 1 có hai ngưỡng chứ không một.
  - ít hơn 5 hit → mean tính trên số hit có thật, không chia cho 5.

Tiền điều kiện: `gate_stats` CHỈ nhận điểm BM25 thô đã sắp giảm dần — không
bao giờ điểm đã fuse (RRF). Vi phạm bị `gate_stats` raise ngay (xem guard bên
dưới) thay vì tự sort hộ, vì tự sort hộ sẽ che mất đúng lỗi truyền nhầm danh
sách mà cảnh báo này đang nói tới.
"""

from __future__ import annotations

import math
from pathlib import Path

from flow1.index import BM25_PATH, load, tokenize
from flow1.models import Chunk, Hit, Retrieval

TOP_K = 5
_RATIO_WINDOW = 5      # ratio = top1 / mean(top2..top5)
CAND = 10              # số ứng viên lấy từ mỗi retriever trước khi fuse


def gate_stats(bm25_desc: list[float]) -> tuple[float, float]:
    """Trả (top1_abs, ratio) từ danh sách điểm BM25 THÔ ĐÃ SẮP GIẢM DẦN."""
    window = bm25_desc[:_RATIO_WINDOW]
    for i in range(len(window) - 1):
        if window[i] < window[i + 1]:
            raise ValueError(
                "gate_stats yêu cầu bm25_desc là điểm BM25 thô đã sắp giảm "
                f"dần; vi phạm tại index {i}: {window[i]!r} < "
                f"{window[i + 1]!r}. Đừng truyền danh sách điểm đã fuse "
                "(RRF) vào đây — sort giảm dần theo BM25 thô trước khi gọi."
            )

    if not bm25_desc:
        return 0.0, 0.0

    top1 = float(bm25_desc[0])
    if top1 <= 0.0:
        return 0.0, 0.0

    rest = [float(s) for s in bm25_desc[1:_RATIO_WINDOW]]
    if not rest:
        return top1, math.inf

    mean_rest = sum(rest) / len(rest)
    if mean_rest == 0.0:
        return top1, math.inf

    return top1, top1 / mean_rest


def retrieve(
    query: str,
    *,
    session: str | None = None,
    k: int = TOP_K,
    store: tuple[list[Chunk], object] | None = None,
    path: Path = BM25_PATH,
    embeddings=None,
    query_vector=None,
) -> Retrieval:
    """Retrieve top-k chunk.

    `embeddings` là ma trận vector của TOÀN BỘ chunk, hoặc None để chạy BM25 thuần.
    Mặc định tự thử nạp store/emb.npy; thiếu file thì lùi êm.

    top1_abs và ratio LUÔN tính trên BM25 thô, kể cả khi fuse — xem docstring module.
    """
    chunks, bm25 = store if store is not None else load(path)

    tokens = tokenize(query)
    if not tokens:
        return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

    all_scores = bm25.get_scores(tokens)
    keep = [
        i for i, chunk in enumerate(chunks)
        if session is None or chunk.session == session
    ]
    if not keep:
        return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

    bm25_scores = {i: float(all_scores[i]) for i in keep}
    bm25_order = sorted(keep, key=lambda i: bm25_scores[i], reverse=True)

    # Hai chỉ số của cổng 1 — trên BM25 THÔ, trước và độc lập với mọi fusion.
    top1_abs, ratio = gate_stats([bm25_scores[i] for i in bm25_order])

    if embeddings is None and store is None:
        try:
            from flow1.embed import load_embeddings
            embeddings = load_embeddings()
        except ImportError:
            embeddings = None

    emb_scores: dict[int, float] = {}
    if embeddings is not None:
        if query_vector is None:
            from flow1.embed import embed_query
            query_vector = embed_query(query)
        emb_scores = {i: float(embeddings[i] @ query_vector) for i in keep}
        emb_order = sorted(keep, key=lambda i: emb_scores[i], reverse=True)

        from flow1.embed import rrf
        from flow1.thresholds import RRF_K

        fused = rrf([bm25_order[:CAND], emb_order[:CAND]], RRF_K)
        final_order = sorted(fused, key=lambda i: fused[i], reverse=True)
        final_score = fused
    else:
        final_order = bm25_order
        final_score = bm25_scores

    hits = [
        Hit(
            chunk=chunks[i],
            bm25=bm25_scores[i],
            emb=emb_scores.get(i) if embeddings is not None else None,
            rank=rank,
            score=final_score[i],
        )
        for rank, i in enumerate(final_order[:k])
    ]
    return Retrieval(hits=hits, top1_abs=top1_abs, ratio=ratio)
