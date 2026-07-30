"""Build hierarchical Qdrant point drafts from validated transcripts."""

from __future__ import annotations

from vector_db.models import ParsedSession, PointDraft

SCHEMA_VERSION = "1.0"


def _session_payload(session: ParsedSession) -> dict:
    metadata = session.metadata
    return {
        "session_id": metadata.session_id,
        "session_order": metadata.session_order,
        "session_day": metadata.session_day,
        "session_period": metadata.session_period,
        "session_title": metadata.session_title,
        "session_locator": metadata.session_locator,
        "location_confidence": metadata.location_confidence,
        "source_file": metadata.source_file,
        "source_hash": metadata.source_hash,
    }


def build_atomic_embedding_text(
    session: ParsedSession,
    *,
    section_title: str,
    chunk_id: str,
    text: str,
) -> str:
    return (
        f"Buổi: {session.metadata.session_locator}\n"
        f"Mục: {section_title}\n\n"
        f"[{chunk_id}] {text}"
    )


def build_point_drafts(
    sessions: tuple[ParsedSession, ...],
) -> tuple[PointDraft, ...]:
    """Create atomic, parent, and TOC drafts in stable order."""

    drafts: list[PointDraft] = []

    for session in sessions:
        session_payload = _session_payload(session)

        for section in session.sections:
            for chunk in section.chunks:
                payload = {
                    "schema_version": SCHEMA_VERSION,
                    "point_type": "atomic_chunk",
                    "chunk_id": chunk.chunk_id,
                    "citation_id": chunk.citation_id,
                    **session_payload,
                    "section_id": chunk.section_id,
                    "section_title": chunk.section_title,
                    "section_order": chunk.section_order,
                    "parent_chunk_id": section.section_id,
                    "chunk_order_in_session": (chunk.chunk_order_in_session),
                    "chunk_order_in_section": (chunk.chunk_order_in_section),
                    "has_unclear": chunk.has_unclear,
                    "is_activity": chunk.is_activity,
                    "speaker_role": chunk.speaker_role,
                    "content_type": chunk.content_type,
                    "text": chunk.text,
                    "content_hash": chunk.content_hash,
                }
                drafts.append(
                    PointDraft(
                        logical_id=chunk.chunk_id,
                        point_type="atomic_chunk",
                        payload=payload,
                        embedding_text=build_atomic_embedding_text(
                            session,
                            section_title=chunk.section_title,
                            chunk_id=chunk.chunk_id,
                            text=chunk.text,
                        ),
                    )
                )

        for section in session.sections:
            children = section.chunks
            child_ids = tuple(chunk.chunk_id for chunk in children)
            unclear_ids = [chunk.chunk_id for chunk in children if chunk.has_unclear]
            full_text = "\n\n".join(
                f"[{chunk.chunk_id}] {chunk.text}" for chunk in children
            )
            payload = {
                "schema_version": SCHEMA_VERSION,
                "point_type": "section_parent",
                "chunk_id": section.section_id,
                **session_payload,
                "section_id": section.section_id,
                "section_title": section.section_title,
                "section_order": section.section_order,
                "start_chunk_id": children[0].chunk_id,
                "end_chunk_id": children[-1].chunk_id,
                "child_chunk_ids": list(child_ids),
                "child_count": len(child_ids),
                "has_unclear": bool(unclear_ids),
                "unclear_chunk_ids": unclear_ids,
                "unclear_count": len(unclear_ids),
                "full_text": full_text,
            }
            drafts.append(
                PointDraft(
                    logical_id=section.section_id,
                    point_type="section_parent",
                    payload=payload,
                    child_chunk_ids=child_ids,
                )
            )

        toc = [
            {
                "section_id": section.section_id,
                "section_order": section.section_order,
                "section_title": section.section_title,
                "start_chunk_id": section.chunks[0].chunk_id,
                "end_chunk_id": section.chunks[-1].chunk_id,
                "child_count": len(section.chunks),
            }
            for section in session.sections
        ]
        toc_text = "\n".join(
            f"{item['section_order']}. {item['section_title']}" for item in toc
        )
        toc_id = f"{session.metadata.session_id}-TOC"
        toc_payload = {
            "schema_version": SCHEMA_VERSION,
            "point_type": "session_toc",
            "chunk_id": toc_id,
            **session_payload,
            "section_ids": [section.section_id for section in session.sections],
            "section_count": len(session.sections),
            "toc": toc,
            "toc_text": toc_text,
        }
        drafts.append(
            PointDraft(
                logical_id=toc_id,
                point_type="session_toc",
                payload=toc_payload,
                embedding_text=(
                    f"{session.metadata.session_locator}\n\nMục lục:\n{toc_text}"
                ),
            )
        )

    return tuple(drafts)
