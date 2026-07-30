"""Ba nhanh retrieve sau MOT interface, cong lop bat loi dung chung.

KHOA NOI: moi retriever tra ve [(ma doan Txx-NNN, diem)]. Ma doan la citation
unit cua ca he — Qdrant co payload.citation_id, Neo4j co Turn {id}, BM25 index
chunk_id chinh la ma doan. Khong lop anh xa nao phai nuoi tay.

DIEM KHONG CAN CUNG THANG: RRF chi doc THU HANG. BM25 tra diem tho, Qdrant tra
cosine, Neo4j tra diem full-text — khong chuan hoa gi giua chung.

safe_rank la noi DUY NHAT bat loi. Retriever tu no duoc phep nem; tach vai nhu
vay de moi ben mot viec va de test duoc duong loi rieng.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class RewrittenQuery(BaseModel):
    """Ba dang cua cung mot cau hoi, moi retriever an mot dang."""

    keywords: list[str] = Field(
        description="Tu khoa cho BM25, da bo sung dong nghia Viet-Anh."
    )
    cau_hoi: str = Field(
        description="Cau hoi viet lai thanh mot cau tu nhien day du, cho vector search."
    )
    thuc_the: list[str] = Field(
        description="Ten khai niem/thuc the de khop vao knowledge graph."
    )

    @classmethod
    def passthrough(cls, query: str) -> "RewrittenQuery":
        """Khong goi LLM: dat nguyen cau hoi vao ca ba truong."""
        return cls(keywords=[query], cau_hoi=query, thuc_the=[query])


@dataclass(frozen=True)
class RankedList:
    name: str
    ranking: list[tuple[str, float]]
    ms: float
    error: str | None = None
    skipped_reason: str | None = None


class Retriever(Protocol):
    name: str

    def rank(self, q: RewrittenQuery, *, session: str | None, k: int) -> list[tuple[str, float]]:
        """[(ma doan, diem)] da sap giam dan."""
        ...


class NullRetriever:
    """Khong tra ve gi. Chon khi tat toggle, thieu key, hoac service chet."""

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def rank(self, q, *, session, k):
        return []


class BM25Retriever:
    """BM25 offline tren doan nguyen tu. An truong `keywords`."""

    name = "bm25"
    reason = ""

    def __init__(self, store) -> None:
        self.store = store

    def rank(self, q, *, session, k):
        from flow1.index import tokenize

        tokens = tokenize(" ".join(q.keywords))
        if not tokens:
            return []
        scores = self.store.bm25.get_scores(tokens)
        pairs = [
            (atomic.chunk_id, float(scores[i]))
            for i, atomic in enumerate(self.store.atomics)
            if session is None or atomic.session == session
        ]
        pairs.sort(key=lambda pair: pair[1], reverse=True)
        return pairs[:k]


class QdrantRetriever:
    """Vector search trong Qdrant tren atomic_chunk. An truong `cau_hoi`."""

    name = "qdrant"
    reason = ""

    def rank(self, q, *, session, k):
        from vector_db.search import find_chunks

        hits = find_chunks(
            q.cau_hoi,
            session_id=f"T{session}" if session else None,
            top_k=k,
        )
        return [
            (hit.payload["citation_id"], float(hit.score))
            for hit in hits
            if hit.payload.get("citation_id")
        ]


class Neo4jRetriever:
    """Doan lien quan QUA QUAN HE trong knowledge graph. An truong `thuc_the`."""

    name = "neo4j"
    reason = ""

    def rank(self, q, *, session, k):
        import graph_db.retrieve as gr

        return gr.turns_for_concepts(q.thuc_the, session=session, k=k)


def safe_rank(
    retriever: Retriever, q: RewrittenQuery, *, session: str | None, k: int
) -> RankedList:
    """Goi mot retriever, bat moi loi, dedupe ma trung. KHONG BAO GIO nem."""
    start = time.perf_counter()
    error = None
    try:
        raw = retriever.rank(q, session=session, k=k)
    except Exception as exc:
        raw = []
        error = f"{type(exc).__name__}: {exc}"

    seen: dict[str, float] = {}
    for code, score in raw:
        if code not in seen:
            seen[code] = float(score)

    return RankedList(
        name=retriever.name,
        ranking=list(seen.items()),
        ms=(time.perf_counter() - start) * 1000.0,
        error=error,
        skipped_reason=getattr(retriever, "reason", "") or None,
    )
