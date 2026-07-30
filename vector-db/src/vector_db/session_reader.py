"""Structured, exhaustive readers for summarization workflows."""

from __future__ import annotations

import argparse
import json

from qdrant_client import models

from vector_db.qdrant_store import QdrantStore


def _filter(
    point_type: str,
    *,
    session_id: str | None = None,
    section_id: str | None = None,
) -> models.Filter:
    must: list[models.Condition] = [
        models.FieldCondition(
            key="point_type",
            match=models.MatchValue(value=point_type),
        )
    ]
    if session_id is not None:
        must.append(
            models.FieldCondition(
                key="session_id",
                match=models.MatchValue(value=session_id),
            )
        )
    if section_id is not None:
        must.append(
            models.FieldCondition(
                key="section_id",
                match=models.MatchValue(value=section_id),
            )
        )
    return models.Filter(must=must)


def get_session_outline(session_id: str) -> dict:
    records = QdrantStore().scroll_all(
        query_filter=_filter(
            "session_toc",
            session_id=session_id,
        )
    )
    if not records:
        raise KeyError(f"Unknown session_id: {session_id}")
    if len(records) != 1:
        raise RuntimeError(f"Expected one TOC for {session_id}, found {len(records)}")
    return records[0]


def get_session_sections(session_id: str) -> tuple[dict, ...]:
    records = QdrantStore().scroll_all(
        query_filter=_filter(
            "section_parent",
            session_id=session_id,
        )
    )
    return tuple(sorted(records, key=lambda item: item["section_order"]))


def get_section_content(section_id: str) -> tuple[dict, ...]:
    records = QdrantStore().scroll_all(
        query_filter=_filter(
            "atomic_chunk",
            section_id=section_id,
        )
    )
    return tuple(
        sorted(
            records,
            key=lambda item: item["chunk_order_in_section"],
        )
    )


def get_session_content(session_id: str) -> tuple[dict, ...]:
    records = QdrantStore().scroll_all(
        query_filter=_filter(
            "atomic_chunk",
            session_id=session_id,
        )
    )
    return tuple(
        sorted(
            records,
            key=lambda item: item["chunk_order_in_session"],
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read complete ordered session or section content."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session-id")
    group.add_argument("--section-id")
    parser.add_argument(
        "--outline",
        action="store_true",
        help="Return only the session TOC.",
    )
    args = parser.parse_args()

    if args.section_id:
        result = get_section_content(args.section_id)
    elif args.outline:
        result = get_session_outline(args.session_id)
    else:
        result = get_session_content(args.session_id)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
