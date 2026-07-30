"""Test retrieve.py — đặc biệt là hai ca biên của `ratio`. Chủ: M1 (khối B)."""

import math

import pytest

from flow1.atomic import build_code_map
from flow1.index import build
from flow1.models import Chunk
from flow1.retrieve import gate_stats, retrieve
from flow1.retrievers import BM25Retriever, NullRetriever
from flow1.store import Store


def chunk(chunk_id, text, *, session="09", section_title="S1"):
    return Chunk(
        chunk_id=chunk_id, session=session, session_title="Buổi thử",
        section_idx=1, section_title=section_title,
        parts=[(chunk_id, text)], has_gap=False,
    )


def store_of(chunks):
    return Store(atomics=chunks, contexts=chunks, code_to_contexts=build_code_map(chunks), bm25=build(chunks))


def _only_bm25(store):
    return {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "tat trong test"),
        "neo4j": NullRetriever("neo4j", "tat trong test"),
    }


CORPUS = [
    chunk("C1", "Cơ chế attention trong transformer, query key value", session="06"),
    chunk("C2", "Xác định bài toán kinh doanh cho AI từ yêu cầu mơ hồ", session="01"),
    chunk("C3", "Chỉ số thành công và mức tự động hoá của bài toán", session="02"),
    chunk("C4", "RAG và tool calling, giới hạn của LLM", session="03"),
    chunk("C5", "Dữ liệu và đánh giá chất lượng đầu ra", session="05"),
    chunk("C6", "Ba track nghề nghiệp AI Engineer MLOps AI PM", session="03"),
]


# --- gate_stats: ba ca biên là chỗ code retrieval hay chết âm thầm ----------

def test_gate_stats_on_an_empty_score_list_refuses():
    assert gate_stats([]) == (0.0, 0.0)


def test_gate_stats_when_nothing_matched_at_all_refuses():
    assert gate_stats([0.0, 0.0, 0.0, 0.0, 0.0]) == (0.0, 0.0)


def test_gate_stats_ratio_is_infinite_when_only_one_chunk_matched():
    # Đây là ca "token hiếm": đúng 1 chunk khớp → ratio = inf → QUA cổng ratio.
    # Sàn tuyệt đối là thứ duy nhất còn chặn được, nên nó phải trả về top1 thật.
    top1, ratio = gate_stats([8.0, 0.0, 0.0, 0.0, 0.0])
    assert top1 == 8.0
    assert ratio == math.inf


def test_gate_stats_ratio_is_infinite_when_there_is_a_single_hit():
    top1, ratio = gate_stats([3.0])
    assert top1 == 3.0
    assert ratio == math.inf


def test_gate_stats_computes_the_ratio_against_the_mean_of_ranks_two_to_five():
    # top1=10, mean(5,5,5,5)=5 → ratio 2.0
    assert gate_stats([10.0, 5.0, 5.0, 5.0, 5.0]) == (10.0, 2.0)


def test_gate_stats_ignores_scores_beyond_rank_five():
    assert gate_stats([10.0, 5.0, 5.0, 5.0, 5.0, 99.0, 99.0]) == (10.0, 2.0)


def test_gate_stats_uses_the_real_count_when_fewer_than_five_scores():
    # top1=9, mean(3,3)=3 → 3.0
    assert gate_stats([9.0, 3.0, 3.0]) == (9.0, 3.0)


def test_a_flat_distribution_gives_a_ratio_near_one():
    top1, ratio = gate_stats([4.0, 4.0, 4.0, 4.0, 4.0])
    assert ratio == 1.0


def test_gate_stats_raises_when_input_is_not_sorted_descending():
    # Bảo vệ tiền điều kiện: nếu Task 13 lỡ truyền danh sách điểm đã fuse (RRF)
    # thay vì BM25 thô đã sắp giảm dần, phải nổ ngay tại đây, không được lặng
    # lẽ trả về ratio ~hằng số 1.02 rồi cổng 1 mất tác dụng trong im lặng.
    with pytest.raises(ValueError):
        gate_stats([1.0, 5.0, 3.0, 2.0, 1.0])


# --- retrieve --------------------------------------------------------------

def test_retrieve_returns_at_most_k_hits():
    st = store_of(CORPUS)
    result = retrieve("attention transformer", k=3, store=st, retrievers=_only_bm25(st))
    assert len(result.hits) <= 3


def test_retrieve_ranks_the_best_match_first():
    st = store_of(CORPUS)
    result = retrieve("attention transformer query key value", store=st, retrievers=_only_bm25(st))
    assert result.hits[0].chunk.chunk_id == "C1"


def test_retrieve_numbers_the_ranks_from_zero():
    st = store_of(CORPUS)
    result = retrieve("bài toán", store=st, retrievers=_only_bm25(st))
    assert [h.rank for h in result.hits] == list(range(len(result.hits)))


def test_retrieve_reports_top1_abs_as_the_raw_bm25_score():
    st = store_of(CORPUS)
    result = retrieve("attention transformer", store=st, retrievers=_only_bm25(st))
    assert result.top1_abs == result.hits[0].bm25


def test_retrieve_on_a_query_matching_nothing_reports_zero_and_refusable_stats():
    st = store_of(CORPUS)
    result = retrieve("kubernetes helm istio", store=st, retrievers=_only_bm25(st))
    assert result.top1_abs == 0.0
    assert result.ratio == 0.0


def test_retrieve_on_an_empty_query_does_not_crash():
    st = store_of(CORPUS)
    result = retrieve("   ", store=st, retrievers=_only_bm25(st))
    assert result.top1_abs == 0.0
    assert result.ratio == 0.0


def test_retrieve_exposes_the_session_of_every_hit_for_the_ambiguity_check():
    st = store_of(CORPUS)
    result = retrieve("bài toán", store=st, retrievers=_only_bm25(st))
    assert result.sessions == [h.chunk.session for h in result.hits]


# --- Lọc buổi: đường "correction" của 4 đường đi trải nghiệm ---------------

def test_a_session_filter_keeps_only_chunks_from_that_session():
    st = store_of(CORPUS)
    result = retrieve("bài toán", session="02", store=st, retrievers=_only_bm25(st))
    assert {h.session for h in result.hits} == {"02"}


def test_stats_are_computed_within_the_filtered_session_only():
    st = store_of(CORPUS)
    unfiltered = retrieve("bài toán", store=st, retrievers=_only_bm25(st))
    filtered = retrieve("bài toán", session="02", store=st, retrievers=_only_bm25(st))
    assert filtered.top1_abs <= unfiltered.top1_abs


def test_a_session_filter_that_matches_no_chunk_returns_refusable_stats():
    st = store_of(CORPUS)
    result = retrieve("bài toán", session="99", store=st, retrievers=_only_bm25(st))
    assert result.hits == []
    assert (result.top1_abs, result.ratio) == (0.0, 0.0)
