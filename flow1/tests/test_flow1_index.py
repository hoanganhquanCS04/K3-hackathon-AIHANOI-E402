"""Test index.py. Chủ: M1 (khối B)."""

import pytest

from flow1.index import IndexMissing, build, load, save, tokenize
from flow1.models import Chunk


def chunk(chunk_id, text, *, session="09", session_title="Buổi thử", section_title="S1"):
    return Chunk(
        chunk_id=chunk_id, session=session, session_title=session_title,
        section_idx=1, section_title=section_title,
        parts=[(chunk_id, text)], has_gap=False,
    )


# --- Tokenizer -------------------------------------------------------------

def test_tokenize_lowercases():
    assert tokenize("RAG Attention") == ["rag", "attention"]


def test_tokenize_keeps_vietnamese_diacritics_intact():
    assert tokenize("bài toán kinh doanh") == ["bài", "toán", "kinh", "doanh"]


def test_tokenize_drops_punctuation():
    assert tokenize("tool calling, RAG — và (embedding)?") == [
        "tool", "calling", "rag", "và", "embedding",
    ]


def test_tokenize_keeps_digits_so_session_numbers_are_searchable():
    assert tokenize("buổi 03 day 2") == ["buổi", "03", "day", "2"]


def test_tokenize_returns_empty_for_a_blank_query():
    assert tokenize("   ") == []


# --- Index -----------------------------------------------------------------

def test_a_query_scores_the_chunk_that_contains_its_term_highest():
    chunks = [
        chunk("C1", "Cơ chế attention trong transformer hoạt động thế nào"),
        chunk("C2", "Cách xác định bài toán kinh doanh cho AI"),
        chunk("C3", "Buổi tổng kết và hỏi đáp cuối khoá"),
    ]
    bm25 = build(chunks)
    scores = bm25.get_scores(tokenize("attention transformer"))
    assert scores[0] > scores[1]


def test_a_query_with_no_matching_term_scores_zero_everywhere():
    chunks = [chunk("C1", "Cơ chế attention"), chunk("C2", "bài toán kinh doanh")]
    scores = build(chunks).get_scores(tokenize("kubernetes helm chart"))
    assert max(scores) == 0.0


def test_the_section_heading_is_searchable_because_index_text_prefixes_it():
    # 23% đoạn dưới 300 ký tự — đứng một mình không đủ ngữ cảnh để match. Prefix
    # heading là bắt buộc, và test này chứng minh nó thực sự vào index.
    chunks = [
        chunk("C1", "nội dung ngắn", section_title="Cơ chế attention và transformer"),
        chunk("C2", "nội dung ngắn khác", section_title="Bảo mật dữ liệu"),
        chunk("C3", "nội dung ngắn thứ ba", section_title="Tổng kết khoá học"),
    ]
    scores = build(chunks).get_scores(tokenize("attention"))
    assert scores[0] > scores[1]


def test_the_session_title_is_searchable_too():
    chunks = [
        chunk("C1", "abc", session_title="Day 1 — Foundation: cách LLM hoạt động"),
        chunk("C2", "abc", session_title="Buổi về bài toán · đánh giá · dữ liệu"),
        chunk("C3", "abc", session_title="Buổi tổng kết cuối khoá"),
    ]
    scores = build(chunks).get_scores(tokenize("foundation"))
    assert scores[0] > scores[1]


# --- Lưu / nạp -------------------------------------------------------------

def test_save_then_load_round_trips_the_chunks(tmp_path):
    from flow1.atomic import build_code_map
    from flow1.store import Store

    chunks = [
        chunk("C1", "Cơ chế attention"),
        chunk("C2", "bài toán kinh doanh"),
        chunk("C3", "buổi tổng kết cuối khoá"),
    ]
    path = tmp_path / "bm25.pkl"
    store = Store(atomics=chunks, contexts=chunks, code_to_contexts=build_code_map(chunks), bm25=build(chunks))
    save(store, path)
    loaded_store = load(path)
    assert [c.chunk_id for c in loaded_store.atomics] == ["C1", "C2", "C3"]
    assert loaded_store.bm25.get_scores(tokenize("attention"))[0] > 0


def test_load_raises_a_typed_error_with_the_fix_command_when_the_index_is_missing(tmp_path):
    with pytest.raises(IndexMissing) as exc:
        load(tmp_path / "khong-co.pkl")
    assert "python -m flow1 index" in str(exc.value), "báo lỗi phải nói cách sửa"


def test_save_creates_the_store_directory_if_it_does_not_exist(tmp_path):
    from flow1.atomic import build_code_map
    from flow1.store import Store

    path = tmp_path / "chua" / "co" / "bm25.pkl"
    c = [chunk("C1", "abc")]
    store = Store(atomics=c, contexts=c, code_to_contexts=build_code_map(c), bm25=build(c))
    save(store, path)
    assert path.exists()


def test_index_module_does_not_touch_the_llm():
    import flow1.index as index_module

    with open(index_module.__file__, encoding="utf-8") as handle:
        source = handle.read()
    assert "anthropic" not in source
    assert "sotay.llm" not in source
