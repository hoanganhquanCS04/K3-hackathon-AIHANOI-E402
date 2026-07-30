"""Hierarchical semantic retrieval API and command-line smoke test."""

from __future__ import annotations

import argparse
import json
from typing import Literal

from qdrant_client import models

from vector_db.embeddings import EmbeddingService
from vector_db.models import RetrievalResponse, SearchHit
from vector_db.qdrant_store import QdrantStore


def _validate_query(query: str, top_k: int) -> str:
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    return query


def _semantic_search(
    query: str,
    *,
    point_type: Literal[
        "session_toc",
        "section_parent",
        "atomic_chunk",
    ],
    session_id: str | None = None,
    section_id: str | None = None,
    top_k: int = 5,
    exclude_activities: bool = False,
) -> tuple[SearchHit, ...]:
    query = _validate_query(query, top_k)
    must: list[models.Condition] = [
        models.FieldCondition(
            key="point_type",
            match=models.MatchValue(value=point_type),
        )
    ]
    must_not: list[models.Condition] = []
    if session_id is not None:
        must.append(
            models.FieldCondition(
                key="session_id",
                match=models.MatchValue(value=session_id.strip()),
            )
        )
    if section_id is not None:
        must.append(
            models.FieldCondition(
                key="section_id",
                match=models.MatchValue(value=section_id.strip()),
            )
        )
    if exclude_activities:
        must_not.append(
            models.FieldCondition(
                key="is_activity",
                match=models.MatchValue(value=True),
            )
        )
    with EmbeddingService() as embedder:
        vector = embedder.embed_one(f"query:{query}", query)
    return QdrantStore().query(
        vector,
        query_filter=models.Filter(
            must=must,
            must_not=must_not or None,
        ),
        limit=top_k,
    )


def find_sessions(
    query: str,
    top_k: int = 3,
) -> tuple[SearchHit, ...]:
    return _semantic_search(
        query,
        point_type="session_toc",
        top_k=top_k,
    )


def find_sections(
    query: str,
    session_id: str,
    top_k: int = 3,
) -> tuple[SearchHit, ...]:
    if not session_id.strip():
        raise ValueError("session_id must not be empty")
    return _semantic_search(
        query,
        point_type="section_parent",
        session_id=session_id,
        top_k=top_k,
    )


def find_chunks(
    query: str,
    session_id: str | None = None,
    section_id: str | None = None,
    top_k: int = 5,
    *,
    exclude_activities: bool = True,
) -> tuple[SearchHit, ...]:
    """Tim doan nguyen tu.

    session_id=None nghia la tim xuyen ca 6 buoi — cong 1 cua flow1 can the de
    phat hien chu de nam o nhieu buoi va hoi lai thay vi doan.
    """
    if session_id is not None and not session_id.strip():
        raise ValueError("session_id must not be empty")
    return _semantic_search(
        query,
        point_type="atomic_chunk",
        session_id=session_id,
        section_id=section_id,
        top_k=top_k,
        exclude_activities=exclude_activities,
    )


def retrieve(
    query: str,
    *,
    session_id: str | None = None,
    section_id: str | None = None,
    top_k: int = 5,
) -> RetrievalResponse:
    """Return evidence or structured session-clarification metadata."""

    query = _validate_query(query, top_k)
    if session_id is None or not session_id.strip():
        candidates = find_sessions(query, top_k=min(3, top_k))
        if not candidates:
            return RetrievalResponse(
                status="no_evidence",
                reason="no_matching_session",
            )
        return RetrievalResponse(
            status="needs_clarification",
            reason="missing_session_context",
            candidate_sessions=tuple(
                {
                    "session_id": hit.payload["session_id"],
                    "session_title": hit.payload["session_title"],
                    "session_locator": hit.payload["session_locator"],
                    "matched_toc": hit.payload["toc_text"],
                    "retrieval_score": hit.score,
                }
                for hit in candidates
            ),
        )

    hits = find_chunks(
        query,
        session_id=session_id,
        section_id=section_id,
        top_k=top_k,
    )
    if not hits:
        return RetrievalResponse(
            status="no_evidence",
            reason="no_matching_chunk",
        )
    return RetrievalResponse(status="ok", hits=hits)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search transcript data.")
    parser.add_argument("query")
    parser.add_argument(
        "--level",
        choices=("session", "section", "chunk"),
        default="chunk",
    )
    parser.add_argument("--session-id")
    parser.add_argument("--section-id")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.level == "session":
        hits = find_sessions(args.query, top_k=args.top_k)
    elif args.level == "section":
        if not args.session_id:
            parser.error("--session-id is required for section search")
        hits = find_sections(
            args.query,
            args.session_id,
            top_k=args.top_k,
        )
    else:
        hits = find_chunks(
            args.query,
            session_id=args.session_id,
            section_id=args.section_id,
            top_k=args.top_k,
        )

    print(
        json.dumps(
            [hit.model_dump() for hit in hits],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
