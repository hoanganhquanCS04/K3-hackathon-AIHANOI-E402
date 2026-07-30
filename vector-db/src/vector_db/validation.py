"""Cross-record validation for parsed transcripts and Qdrant point drafts."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

from vector_db.models import ParsedSession, PointDraft

CHUNK_ID_PATTERN = re.compile(r"^T(\d{2})-(\d{3})$")


def validate_sessions(sessions: Iterable[ParsedSession]) -> None:
    """Validate source-level invariants and fail before any API call."""

    sessions = tuple(sessions)
    if not sessions:
        raise ValueError("Dataset contains no sessions")

    session_ids = [session.metadata.session_id for session in sessions]
    duplicate_sessions = [
        value for value, count in Counter(session_ids).items() if count > 1
    ]
    if duplicate_sessions:
        raise ValueError(f"Duplicate session IDs: {sorted(duplicate_sessions)}")

    all_chunk_ids: list[str] = []
    for session in sessions:
        chunks = session.chunks
        if not chunks:
            raise ValueError(f"Session has no chunks: {session.metadata.session_id}")

        expected_session_order = list(range(1, len(chunks) + 1))
        actual_session_order = [chunk.chunk_order_in_session for chunk in chunks]
        if actual_session_order != expected_session_order:
            raise ValueError(f"Non-contiguous order in {session.metadata.session_id}")

        for section in session.sections:
            if not section.chunks:
                raise ValueError(f"Section has no chunks: {section.section_id}")
            expected_section_order = list(range(1, len(section.chunks) + 1))
            actual_section_order = [
                chunk.chunk_order_in_section for chunk in section.chunks
            ]
            if actual_section_order != expected_section_order:
                raise ValueError(f"Non-contiguous order in {section.section_id}")

            for chunk in section.chunks:
                match = CHUNK_ID_PATTERN.match(chunk.chunk_id)
                if not match:
                    raise ValueError(f"Invalid chunk ID: {chunk.chunk_id}")
                if f"T{match.group(1)}" != session.metadata.session_id:
                    raise ValueError(f"Cross-session chunk: {chunk.chunk_id}")
                if chunk.session_id != session.metadata.session_id:
                    raise ValueError(f"Incorrect session metadata: {chunk.chunk_id}")
                if chunk.section_id != section.section_id:
                    raise ValueError(f"Cross-section chunk: {chunk.chunk_id}")
                if chunk.citation_id != chunk.chunk_id:
                    raise ValueError(f"Incorrect citation ID: {chunk.chunk_id}")
                if not chunk.text.strip():
                    raise ValueError(f"Empty text: {chunk.chunk_id}")

        numeric_ids = [
            int(CHUNK_ID_PATTERN.match(chunk.chunk_id).group(2))
            for chunk in chunks
            if CHUNK_ID_PATTERN.match(chunk.chunk_id)
        ]
        if numeric_ids != list(range(1, len(chunks) + 1)):
            raise ValueError(
                f"Chunk IDs are missing or out of order in "
                f"{session.metadata.session_id}"
            )
        all_chunk_ids.extend(chunk.chunk_id for chunk in chunks)

    duplicates = [value for value, count in Counter(all_chunk_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate chunk IDs: {sorted(duplicates)}")


def validate_point_drafts(
    drafts: Iterable[PointDraft],
    sessions: Iterable[ParsedSession],
) -> None:
    """Validate hierarchy and payload consistency before embedding."""

    drafts = tuple(drafts)
    sessions = tuple(sessions)
    known_atomic_ids = {
        chunk.chunk_id for session in sessions for chunk in session.chunks
    }
    logical_ids = [draft.logical_id for draft in drafts]
    duplicates = [value for value, count in Counter(logical_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate logical point IDs: {sorted(duplicates)}")

    atomic_drafts = [draft for draft in drafts if draft.point_type == "atomic_chunk"]
    if {draft.logical_id for draft in atomic_drafts} != known_atomic_ids:
        raise ValueError("Atomic point IDs do not exactly match source chunk IDs")

    for draft in drafts:
        payload = draft.payload
        if payload.get("point_type") != draft.point_type:
            raise ValueError(f"Incorrect point_type payload: {draft.logical_id}")
        if payload.get("chunk_id") != draft.logical_id:
            raise ValueError(f"Incorrect chunk_id payload: {draft.logical_id}")
        if draft.point_type == "atomic_chunk":
            if payload.get("citation_id") != draft.logical_id:
                raise ValueError(f"Incorrect citation: {draft.logical_id}")
            if not draft.embedding_text:
                raise ValueError(f"Missing embedding text: {draft.logical_id}")
        elif draft.point_type == "section_parent":
            if not draft.child_chunk_ids:
                raise ValueError(f"Parent has no children: {draft.logical_id}")
            missing = set(draft.child_chunk_ids) - known_atomic_ids
            if missing:
                raise ValueError(f"Parent references missing chunks: {sorted(missing)}")
            expected_full_text = "\n\n".join(
                f"[{chunk_id}] "
                + next(
                    chunk.text
                    for session in sessions
                    for chunk in session.chunks
                    if chunk.chunk_id == chunk_id
                )
                for chunk_id in draft.child_chunk_ids
            )
            if payload.get("full_text") != expected_full_text:
                raise ValueError(f"Incorrect parent full_text: {draft.logical_id}")
        elif draft.point_type == "session_toc":
            if not draft.embedding_text:
                raise ValueError(f"Missing TOC embedding text: {draft.logical_id}")
