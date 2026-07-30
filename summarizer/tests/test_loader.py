"""Loader phải trả đủ và đúng thứ tự. Không cần API key, không cần Qdrant."""

from __future__ import annotations

import pytest

from summarizer.loader import LocalParserLoader, section_content_hash

EXPECTED = {
    "T01": (11, 89),
    "T02": (5, 43),
    "T03": (19, 154),
    "T04": (21, 98),
    "T05": (19, 154),
    "T06": (21, 162),
}


@pytest.fixture(scope="module")
def loader() -> LocalParserLoader:
    return LocalParserLoader()


def test_all_sessions_are_loaded(loader):
    assert [ref.session_id for ref in loader.list_sessions()] == sorted(EXPECTED)


@pytest.mark.parametrize(("session_id", "expected"), EXPECTED.items())
def test_section_and_chunk_counts(loader, session_id, expected):
    section_count, chunk_count = expected
    assert len(loader.get_session_sections(session_id)) == section_count
    assert len(loader.get_session_content(session_id)) == chunk_count


@pytest.mark.parametrize("session_id", EXPECTED)
def test_sections_partition_the_session_exactly(loader, session_id):
    """Bất biến cốt lõi: gộp mọi section ra đúng toàn bộ buổi, không thừa không thiếu."""

    session_chunks = loader.get_session_content(session_id)
    from_sections = [
        chunk
        for ref in loader.get_session_sections(session_id)
        for chunk in loader.get_section_content(ref.section_id)
    ]
    assert [chunk.chunk_id for chunk in from_sections] == [
        chunk.chunk_id for chunk in session_chunks
    ]


@pytest.mark.parametrize("session_id", EXPECTED)
def test_chunks_are_in_reading_order(loader, session_id):
    orders = [chunk.chunk_order_in_session for chunk in loader.get_session_content(session_id)]
    assert orders == sorted(orders)
    assert orders == list(range(1, len(orders) + 1))


@pytest.mark.parametrize("session_id", EXPECTED)
def test_no_cross_session_contamination(loader, session_id):
    assert all(
        chunk.session_id == session_id for chunk in loader.get_session_content(session_id)
    )


def test_sections_are_ordered(loader):
    orders = [ref.section_order for ref in loader.get_session_sections("T03")]
    assert orders == list(range(1, 20))


def test_unknown_ids_raise(loader):
    with pytest.raises(KeyError):
        loader.get_session("T99")
    with pytest.raises(KeyError):
        loader.get_section_content("T99-SEC-001")


def test_speaker_role_is_available(loader):
    """Không có speaker_role thì quy tắc chống gán nhầm vai không thực thi được."""

    roles = {chunk.speaker_role for chunk in loader.get_session_content("T03")}
    assert "instructor" in roles
    assert "student" in roles


def test_content_hash_is_deterministic_and_content_sensitive(loader):
    chunks = loader.get_section_content("T03-SEC-004")
    assert section_content_hash(chunks) == section_content_hash(chunks)
    assert section_content_hash(chunks) != section_content_hash(chunks[:-1])
