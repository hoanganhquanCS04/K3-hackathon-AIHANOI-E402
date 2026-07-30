import pytest

from vector_db import search
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


def test_find_chunks_khong_can_session_id(monkeypatch):
    """Cong 1 cua flow1 tim xuyen buoi de phat hien mo ho da buoi."""
    ghi = {}

    def fake(query, **kwargs):
        ghi.update(kwargs)
        return ()

    monkeypatch.setattr(search, "_semantic_search", fake)
    search.find_chunks("attention la gi")

    assert ghi["session_id"] is None
    assert ghi["point_type"] == "atomic_chunk"


def test_find_chunks_van_loc_duoc_theo_buoi(monkeypatch):
    ghi = {}

    def fake(query, **kwargs):
        ghi.update(kwargs)
        return ()

    monkeypatch.setattr(search, "_semantic_search", fake)
    search.find_chunks("attention", session_id="T04")

    assert ghi["session_id"] == "T04"


def test_session_id_rong_bi_tu_choi(monkeypatch):
    monkeypatch.setattr(search, "_semantic_search", lambda q, **k: ())
    with pytest.raises(ValueError):
        search.find_chunks("attention", session_id="   ")


def test_find_chunks_mac_dinh_loai_hoat_dong_lop(monkeypatch):
    ghi = {}

    def fake(query, **kwargs):
        ghi.update(kwargs)
        return ()

    monkeypatch.setattr(search, "_semantic_search", fake)
    search.find_chunks("attention")

    assert ghi["exclude_activities"] is True
