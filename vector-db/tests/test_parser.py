from vector_db.parser import parse_all_transcripts
from vector_db.validation import validate_sessions

EXPECTED_CHUNKS = {
    "T01": 89,
    "T02": 43,
    "T03": 154,
    "T04": 98,
    "T05": 154,
    "T06": 162,
}

EXPECTED_SECTIONS = {
    "T01": 11,
    "T02": 5,
    "T03": 19,
    "T04": 21,
    "T05": 19,
    "T06": 21,
}


def test_parse_all_transcripts_has_expected_inventory() -> None:
    sessions = parse_all_transcripts()

    assert len(sessions) == 6
    assert sum(len(session.chunks) for session in sessions) == 700
    assert sum(len(session.sections) for session in sessions) == 96
    assert {
        session.metadata.session_id: len(session.chunks) for session in sessions
    } == EXPECTED_CHUNKS
    assert {
        session.metadata.session_id: len(session.sections) for session in sessions
    } == EXPECTED_SECTIONS


def test_source_invariants_pass() -> None:
    validate_sessions(parse_all_transcripts())


def test_atomic_ids_and_text_are_preserved() -> None:
    sessions = parse_all_transcripts()
    first = sessions[0].chunks[0]
    last = sessions[-1].chunks[-1]

    assert first.chunk_id == "T01-001"
    assert "khả năng xác định ra một bài toán" in first.text
    assert last.chunk_id == "T06-162"
    assert last.text.strip()


def test_session_metadata_is_derived() -> None:
    sessions = {
        session.metadata.session_id: session for session in parse_all_transcripts()
    }

    assert sessions["T01"].metadata.session_day == 2
    assert sessions["T01"].metadata.session_period == "sáng"
    assert sessions["T03"].metadata.session_period == "chiều"
    assert sessions["T05"].metadata.session_day is None
    assert sessions["T05"].metadata.location_confidence == ("không xác định")
    assert sessions["T01"].metadata.source_file == (
        "data/vlearn-pack/transcript/transcript-01-clean.md"
    )
