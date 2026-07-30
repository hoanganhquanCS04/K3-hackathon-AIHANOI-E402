"""Test embedding + RRF. Chủ: M2. KHÔNG tải model trong test — vector dựng tay."""

import numpy as np
import pytest

from flow1.embed import load_embeddings, rrf
from flow1.index import build
from flow1.models import Chunk
from flow1.retrieve import retrieve


def chunk(chunk_id, text, *, session="09"):
    return Chunk(
        chunk_id=chunk_id, session=session, session_title="Buổi thử",
        section_idx=1, section_title="S1", parts=[(chunk_id, text)], has_gap=False,
    )


CORPUS = [
    chunk("C1", "Cơ chế attention trong transformer"),
    chunk("C2", "Xác định bài toán kinh doanh cho AI"),
    chunk("C3", "RAG và tool calling"),
]


# --- RRF -----------------------------------------------------------------

def test_rrf_scores_a_document_ranked_first_by_both_retrievers_highest():
    scores = rrf([[0, 1, 2], [0, 2, 1]], k=60)
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_rrf_uses_ranks_not_raw_scores():
    # Chính là lý do dùng RRF: BM25 và cosine không cùng thang, cộng thẳng là so
    # hai đơn vị khác nhau.
    scores = rrf([[5, 3]], k=60)
    assert scores[5] == pytest.approx(1 / 61)
    assert scores[3] == pytest.approx(1 / 62)


def test_rrf_sums_across_retrievers():
    scores = rrf([[7], [7]], k=60)
    assert scores[7] == pytest.approx(2 / 61)


def test_rrf_includes_a_document_found_by_only_one_retriever():
    scores = rrf([[1], [2]], k=60)
    assert set(scores) == {1, 2}


def test_rrf_on_empty_rankings_returns_an_empty_mapping():
    assert rrf([], k=60) == {}


# --- Lùi êm khi thiếu emb.npy -------------------------------------------

def test_load_embeddings_returns_none_when_the_file_is_absent(tmp_path):
    assert load_embeddings(tmp_path / "khong-co.npy") is None


def test_retrieve_works_normally_when_embeddings_are_absent():
    result = retrieve("attention transformer", store=(CORPUS, build(CORPUS)), embeddings=None)
    assert result.hits
    assert all(h.emb is None for h in result.hits)
    assert all(h.score == h.bm25 for h in result.hits)


# --- Bật embedding ------------------------------------------------------

def test_retrieve_fills_in_the_emb_score_when_embeddings_are_supplied():
    # Vector dựng tay: C3 gần truy vấn nhất. Không tải model trong test.
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]], dtype="float32")
    result = retrieve(
        "attention transformer", store=(CORPUS, build(CORPUS)),
        embeddings=embeddings, query_vector=np.array([0.7, 0.7], dtype="float32"),
    )
    assert all(h.emb is not None for h in result.hits)


def test_gate_stats_stay_on_raw_bm25_even_when_embeddings_are_on():
    # Ngưỡng T1 hiệu chỉnh ở Task 11 KHÔNG được mất hiệu lực khi bật hybrid.
    store = (CORPUS, build(CORPUS))
    plain = retrieve("attention transformer", store=store, embeddings=None)
    embeddings = np.array([[0.0, 1.0], [1.0, 0.0], [0.7, 0.7]], dtype="float32")
    hybrid = retrieve(
        "attention transformer", store=store, embeddings=embeddings,
        query_vector=np.array([1.0, 0.0], dtype="float32"),
    )
    assert hybrid.top1_abs == plain.top1_abs
    assert hybrid.ratio == plain.ratio


def test_embedding_can_change_the_order_of_the_hits():
    store = (CORPUS, build(CORPUS))
    plain = retrieve("attention", store=store, embeddings=None)
    embeddings = np.array([[0.0, 1.0], [0.0, 1.0], [1.0, 0.0]], dtype="float32")
    hybrid = retrieve(
        "attention", store=store, embeddings=embeddings,
        query_vector=np.array([1.0, 0.0], dtype="float32"),
    )
    assert [h.chunk.chunk_id for h in hybrid.hits] != [] and plain.hits


def test_a_session_filter_still_applies_with_embeddings_on():
    mixed = [chunk("C1", "attention", session="06"), chunk("C2", "attention", session="01")]
    embeddings = np.array([[1.0, 0.0], [1.0, 0.0]], dtype="float32")
    result = retrieve(
        "attention", store=(mixed, build(mixed)), session="01",
        embeddings=embeddings, query_vector=np.array([1.0, 0.0], dtype="float32"),
    )
    assert {h.session for h in result.hits} == {"01"}


# --- Bảo mật data -------------------------------------------------------

def test_embed_module_names_a_local_model_and_no_remote_endpoint():
    import flow1.embed as embed_module

    source = open(embed_module.__file__, encoding="utf-8").read()
    assert "multilingual-e5-small" in source
    assert "api.openai.com" not in source
    assert "anthropic" not in source
    assert "requests.post" not in source
