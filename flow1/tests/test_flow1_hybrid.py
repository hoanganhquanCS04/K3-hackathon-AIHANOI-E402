from flow1.retrieve import Toggles, retrieve
from flow1.retrievers import NullRetriever, RewrittenQuery
from flow1.trace import Trace


class FakeRetriever:
    def __init__(self, name, ranking):
        self.name = name
        self.ranking = ranking
        self.reason = ""

    def rank(self, q, *, session, k):
        return self.ranking[:k]


def _only_bm25(store):
    """Chi BM25 that, hai nhanh kia im lang — de test khong cham mang."""
    from flow1.retrievers import BM25Retriever

    return {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "tat trong test"),
        "neo4j": NullRetriever("neo4j", "tat trong test"),
    }


def test_chi_bm25_thi_van_tra_ket_qua(bm25_store):
    got = retrieve("attention", store=bm25_store, retrievers=_only_bm25(bm25_store))
    assert [h.chunk.chunk_id for h in got.hits]


def test_gate_stats_khong_doi_khi_bat_them_nhanh(bm25_store):
    """Cong 1 luon quyet dinh tren BM25 tho, doc lap voi fusion."""
    rs = _only_bm25(bm25_store)
    tat = retrieve("attention", store=bm25_store, retrievers=rs)

    rs2 = dict(rs)
    rs2["qdrant"] = FakeRetriever("qdrant", [("T02-001", 0.99)])
    bat = retrieve("attention", store=bm25_store, retrievers=rs2)

    assert bat.top1_abs == tat.top1_abs
    assert bat.ratio == tat.ratio


def test_tat_bm25_khoi_fusion_thi_cong_1_VAN_hoat_dong(bm25_store):
    """Bat biến §5.1: toggle chi dieu khien fusion, khong tat cong 1."""
    rs = _only_bm25(bm25_store)
    rs["qdrant"] = FakeRetriever("qdrant", [("T02-001", 0.99)])
    got = retrieve(
        "attention", store=bm25_store, retrievers=rs,
        toggles=Toggles(bm25=False, qdrant=True, neo4j=False),
    )
    assert got.top1_abs > 0.0, "BM25 phai van chay du da tat khoi fusion"


def test_tat_bm25_thi_thu_tu_theo_nhanh_con_lai(bm25_store):
    rs = _only_bm25(bm25_store)
    rs["qdrant"] = FakeRetriever("qdrant", [("T02-001", 0.99)])
    got = retrieve(
        "attention", store=bm25_store, retrievers=rs,
        toggles=Toggles(bm25=False, qdrant=True, neo4j=False),
    )
    assert got.hits[0].chunk.seg_codes[0] == "T02-001"


def test_nhanh_nem_loi_thi_lui_em_va_ghi_ly_do(bm25_store):
    class Vo:
        name = "neo4j"

        def rank(self, q, *, session, k):
            raise ConnectionError("mat mang")

    rs = _only_bm25(bm25_store)
    rs["neo4j"] = Vo()
    trace = Trace("attention")
    got = retrieve("attention", store=bm25_store, retrievers=rs, trace=trace)

    assert got.hits, "phai van tra ve ket qua tu cac nhanh con lai"
    stage = next(s for s in trace.stages if s.name == "neo4j")
    assert "mat mang" in stage.data["loi"]


def test_ma_khong_co_trong_store_bi_bo_qua(bm25_store):
    rs = _only_bm25(bm25_store)
    rs["neo4j"] = FakeRetriever("neo4j", [("T99-999", 9.9)])
    got = retrieve("attention", store=bm25_store, retrievers=rs)
    assert got.hits
    assert all("T99-999" not in h.chunk.seg_codes for h in got.hits)


def test_nhan_duoc_ca_chuoi_lan_RewrittenQuery(bm25_store):
    rs = _only_bm25(bm25_store)
    a = retrieve("attention", store=bm25_store, retrievers=rs)
    b = retrieve(
        RewrittenQuery.passthrough("attention"), store=bm25_store, retrievers=rs
    )
    assert [h.chunk.chunk_id for h in a.hits] == [h.chunk.chunk_id for h in b.hits]


def test_hit_bm25_la_diem_doan_nguyen_tu_tot_nhat_trong_chunk(bm25_store):
    got = retrieve("attention", store=bm25_store, retrievers=_only_bm25(bm25_store))
    assert all(h.bm25 >= 0.0 for h in got.hits)
    assert got.hits[0].bm25 >= got.hits[-1].bm25


def test_loc_theo_buoi_van_dung(bm25_store):
    got = retrieve(
        "automation", store=bm25_store, session="02",
        retrievers=_only_bm25(bm25_store),
    )
    assert all(h.session == "02" for h in got.hits)


def test_trace_bang_fuse_co_thu_hang_tung_nhanh(bm25_store):
    rs = _only_bm25(bm25_store)
    rs["qdrant"] = FakeRetriever("qdrant", [("T04-002", 0.9)])
    trace = Trace("attention")
    retrieve("attention", store=bm25_store, retrievers=rs, trace=trace)

    fuse = next(s for s in trace.stages if s.name == "fuse")
    hang = fuse.data["bang"][0]
    assert set(hang) >= {"ma", "rank_bm25", "rank_qdrant", "rank_neo4j", "rrf"}
    assert "chi_mot_nhanh_tim_ra" in fuse.data


def test_query_rong_tra_retrieval_rong(bm25_store):
    got = retrieve("   ", store=bm25_store, retrievers=_only_bm25(bm25_store))
    assert got.hits == []
    assert got.top1_abs == 0.0
    assert got.ratio == 0.0
