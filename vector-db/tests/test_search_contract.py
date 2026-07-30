import pytest

from vector_db.models import SearchHit
from vector_db.search import find_chunks, find_sessions, retrieve


def test_empty_query_is_rejected_without_api_call() -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        find_sessions("")


def test_invalid_top_k_is_rejected_without_api_call() -> None:
    with pytest.raises(ValueError, match="between 1 and 20"):
        find_sessions("RAG", top_k=0)


def test_empty_session_is_rejected_without_api_call() -> None:
    with pytest.raises(ValueError, match="session_id"):
        find_chunks("RAG", "")


def test_retrieve_returns_structured_clarification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = SearchHit(
        point_id="point",
        score=0.9,
        payload={
            "session_id": "T03",
            "session_title": "Tên buổi",
            "session_locator": "Day 2 chiều — Tên buổi",
            "toc_text": "1. RAG",
        },
    )
    monkeypatch.setattr(
        "vector_db.search.find_sessions",
        lambda _query, top_k: (candidate,),
    )

    response = retrieve("RAG")

    assert response.status == "needs_clarification"
    assert response.reason == "missing_session_context"
    assert response.candidate_sessions[0]["session_id"] == "T03"
