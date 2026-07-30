from vector_db.parser import parse_all_transcripts
from vector_db.point_builder import build_point_drafts
from vector_db.validation import validate_point_drafts


def test_point_inventory_and_hierarchy() -> None:
    sessions = parse_all_transcripts()
    drafts = build_point_drafts(sessions)

    assert len(drafts) == 802
    assert sum(draft.point_type == "atomic_chunk" for draft in drafts) == 700
    assert sum(draft.point_type == "section_parent" for draft in drafts) == 96
    assert sum(draft.point_type == "session_toc" for draft in drafts) == 6
    validate_point_drafts(drafts, sessions)


def test_atomic_payload_preserves_citation_and_locator() -> None:
    sessions = parse_all_transcripts()
    draft = next(
        item for item in build_point_drafts(sessions) if item.logical_id == "T03-034"
    )

    assert draft.payload["citation_id"] == "T03-034"
    assert draft.payload["section_id"] == "T03-SEC-004"
    assert draft.payload["parent_chunk_id"] == "T03-SEC-004"
    assert "Day 2 (chiều)" in draft.embedding_text
    assert "tool calling và RAG" in draft.embedding_text


def test_parent_full_text_and_unclear_are_derived() -> None:
    sessions = parse_all_transcripts()
    parent = next(
        item
        for item in build_point_drafts(sessions)
        if item.logical_id == "T03-SEC-004"
    )

    assert parent.child_chunk_ids == (
        "T03-034",
        "T03-035",
        "T03-036",
    )
    assert parent.payload["child_count"] == 3
    assert "[T03-034]" in parent.payload["full_text"]
    assert "[T03-036]" in parent.payload["full_text"]


def test_toc_lists_every_section() -> None:
    sessions = parse_all_transcripts()
    toc = next(
        item for item in build_point_drafts(sessions) if item.logical_id == "T03-TOC"
    )

    assert toc.payload["section_count"] == 19
    assert len(toc.payload["section_ids"]) == 19
    assert "Giới hạn của LLM, tool calling và RAG" in (toc.payload["toc_text"])
