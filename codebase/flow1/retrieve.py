"""Truy vấn → Retrieval. Chủ: M1 (khối B), dùng bởi cổng 1 của M2.

QUYẾT ĐỊNH THIẾT KẾ QUAN TRỌNG NHẤT của file này:

  `top1_abs` và `ratio` LUÔN tính trên điểm BM25 THÔ, không bao giờ trên điểm đã
  fuse. Điểm RRF là 1/(K+rank) — một dãy gần như cố định (1/61, 1/62, 1/63...),
  nên `ratio` tính sau fuse sẽ luôn ≈ 1,02 bất kể câu hỏi là gì, và cổng 1 chết
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


def gate_stats(bm25_desc: list[float]) -> tuple[float, float]:
    """Trả (top1_abs, ratio) từ danh sách điểm BM25 THÔ ĐÃ SẮP GIẢM DẦN.

    Guard tiền điều kiện: raise ValueError nếu đầu vào không giảm dần TRONG
    CỬA SỔ được dùng thật (index 0.._RATIO_WINDOW), thay vì tự sort hộ. Chỉ
    xét trong cửa sổ vì mọi thứ sau rank 5 vốn dĩ bị bỏ qua (xem test
    `test_gate_stats_ignores_scores_beyond_rank_five`) nên không có tiền điều
    kiện gì để vi phạm ở đó. Đây là nơi duy nhất phát hiện được nếu Task 13 lỡ
    truyền danh sách điểm đã fuse (RRF) vào thay vì BM25 thô — hỏng đó nếu
    không chặn ở đây sẽ chỉ lộ ra dưới dạng `ratio` gần như hằng số 1,02, và
    cổng 1 mất tác dụng trong im lặng.
    """
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
    # `bm25_ranked` là điểm BM25 THÔ, sắp giảm dần — dùng để chấm cổng 1. Khi
    # Task 13 thêm RRF, thứ tự dùng để dựng `hits` hiển thị sẽ đến từ MỘT danh
    # sách khác (đã fuse) — không được lẫn hai danh sách này vào nhau, đó là
    # đúng lỗi mà guard trong `gate_stats` được viết để bắt.
    bm25_ranked = [
        (chunk, float(score))
        for chunk, score in zip(chunks, all_scores)
        if session is None or chunk.session == session
    ]
    if not bm25_ranked:
        return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

    bm25_ranked.sort(key=lambda pair: pair[1], reverse=True)
    bm25_scores_desc = [score for _, score in bm25_ranked]
    top1_abs, ratio = gate_stats(bm25_scores_desc)

    hits = [
        Hit(chunk=chunk, bm25=score, emb=None, rank=rank, score=score)
        for rank, (chunk, score) in enumerate(bm25_ranked[:k])
    ]
    return Retrieval(hits=hits, top1_abs=top1_abs, ratio=ratio)
