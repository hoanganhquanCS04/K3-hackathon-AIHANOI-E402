"""Truy vấn → Retrieval. Chủ: M1 (khối B), dùng bởi cổng 1 của M2.

QUYẾT ĐỊNH THIẾT KẾ QUAN TRỌNG NHẤT của file này:

  `top1_abs` và `ratio` LUÔN tính trên điểm BM25 THÔ, không bao giờ trên điểm đã
  fuse. Điểm RRF là 1/(K+rank) — một dãy gần như cố định (1/61, 1/62, 1/63...),
  nên `ratio` tính sau fuse sẽ luôn ≈ 1,02 bất kể câu hỏi là gì, và cổng 1 chết
  im lặng đúng vào lúc bật hybrid.

  Hệ quả tốt: hiệu chỉnh T1 MỘT LẦN là dùng được cho cả chế độ bật và tắt
  embedding. RRF chỉ đổi *thứ tự nạp chunk vào context*, không đổi *quyết định có
  đủ căn cứ hay không*.

Hai ca biên của `ratio`, mỗi ca một test:
  - mọi điểm = 0  → (0.0, 0.0) → cổng 1 chặn
  - mean(top2..5) = 0 mà top1 > 0 (đúng 1 chunk khớp, thường là câu chứa token
    hiếm như "lab" hay "pretrain") → ratio = inf, QUA cổng ratio. Chỉ sàn tuyệt
    đối chặn được ca này — đó là lý do cổng 1 có hai ngưỡng chứ không một.
"""

from __future__ import annotations

import math
from pathlib import Path

from flow1.index import BM25_PATH, load, tokenize
from flow1.models import Chunk, Hit, Retrieval

TOP_K = 5
_RATIO_WINDOW = 5      # ratio = top1 / mean(top2..top5)


def gate_stats(bm25_desc: list[float]) -> tuple[float, float]:
    """Trả (top1_abs, ratio) từ danh sách điểm BM25 ĐÃ SẮP GIẢM DẦN."""
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
) -> Retrieval:
    """Retrieve top-k chunk. `store` inject được để test không cần file trên đĩa.

    `session` lọc theo buổi — đây là đường "correction": người dùng được hỏi lại
    "buổi 2 hay buổi 5?" thì trả lời được bằng cờ này.
    """
    chunks, bm25 = store if store is not None else load(path)

    tokens = tokenize(query)
    if not tokens:
        return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

    all_scores = bm25.get_scores(tokens)
    pool = [
        (chunk, float(score))
        for chunk, score in zip(chunks, all_scores)
        if session is None or chunk.session == session
    ]
    if not pool:
        return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

    pool.sort(key=lambda pair: pair[1], reverse=True)
    top1_abs, ratio = gate_stats([score for _, score in pool])

    hits = [
        Hit(chunk=chunk, bm25=score, emb=None, rank=rank, score=score)
        for rank, (chunk, score) in enumerate(pool[:k])
    ]
    return Retrieval(hits=hits, top1_abs=top1_abs, ratio=ratio)
