"""Hop nhat RRF (Reciprocal Rank Fusion) giua cac nhanh retrieve.

RRF THAY VI CONG DIEM: BM25, cosine, va graph full-text score khong cung thang.
Cong thang la so hai don vi khac nhau. RRF chi dua tren THU HANG nen doc lap
voi thang diem cua tung retriever.
"""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def rrf(rankings: list[list[T]], k: int) -> dict[T, float]:
    """Reciprocal Rank Fusion. `rankings` = danh sach cac list item, da sap tot->kem.

    score(item) = Σ 1/(k + rank_i(item) + 1), rank 0-based.
    """
    scores: dict[T, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return scores
