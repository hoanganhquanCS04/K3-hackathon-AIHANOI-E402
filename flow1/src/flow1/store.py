"""Goi mot lan build index thanh mot doi tuong.

Thay cho tuple `(chunks, bm25)` cu: gio retrieve can 4 thu chu khong phai 2,
va tuple 4 phan tu thi khong ai nho duoc thu tu.
"""

from __future__ import annotations

from dataclasses import dataclass

from flow1.models import Chunk


@dataclass(frozen=True)
class Store:
    atomics: list[Chunk]                        # BM25 va cac retriever xep hang tren day
    contexts: list[Chunk]                       # nap vao prompt
    code_to_contexts: dict[str, tuple[int, ...]]
    bm25: object                                # BM25Okapi tren atomics
