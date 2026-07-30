from vector_db.qdrant_store import PAYLOAD_INDEXES, make_point_id


def test_point_id_is_deterministic_and_type_scoped() -> None:
    first = make_point_id("atomic_chunk", "T03-034")
    second = make_point_id("atomic_chunk", "T03-034")
    parent = make_point_id("section_parent", "T03-034")

    assert first == second
    assert first != parent


def test_required_payload_indexes_are_declared() -> None:
    assert {
        "point_type",
        "session_id",
        "section_id",
        "session_day",
        "session_period",
        "has_unclear",
        "is_activity",
        "speaker_role",
        "content_type",
    } == set(PAYLOAD_INDEXES)
