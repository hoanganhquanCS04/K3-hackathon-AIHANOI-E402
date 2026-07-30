"""Test RRF + bao mat data."""

import pytest

from flow1.embed import rrf


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


# --- Bảo mật data -------------------------------------------------------

def test_flow1_khong_co_duong_nao_embed_hang_loat_qua_api():
    """Dieu 4 bao mat data: gui ca corpus ra provider ngoai KHONG phai
    'phan toi thieu can thiet'. Corpus da embed mot lan boi vector-db va ket
    qua nam trong Qdrant. flow1 chi duoc embed DUNG CAU HOI.

    Test nay thay cho test_embed_module_names_a_local_model_and_no_remote_endpoint:
    quyet dinh 'model phai local' da bi spec 2026-07-30-agent-2-tool lat, nhung
    bao dam ben duoi no thi khong.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "flow1"
    cam = ("build_embeddings", "embed_all", "embed_corpus", ".encode(")
    for file in src.rglob("*.py"):
        text = file.read_text(encoding="utf-8")
        for tu in cam:
            assert tu not in text, (
                f"{file.name} co '{tu}' — flow1 chi duoc embed cau hoi, khong "
                f"duoc embed hang loat. Xem canvas §4.3."
            )
