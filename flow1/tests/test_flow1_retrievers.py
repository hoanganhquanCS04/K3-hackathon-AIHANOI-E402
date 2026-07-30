from flow1.retrievers import (
    BM25Retriever,
    NullRetriever,
    QdrantRetriever,
    RewrittenQuery,
    safe_rank,
)


def _q(keywords=None, cau_hoi="attention la gi", thuc_the=None):
    return RewrittenQuery(
        keywords=keywords if keywords is not None else ["attention"],
        cau_hoi=cau_hoi,
        thuc_the=thuc_the if thuc_the is not None else ["attention"],
    )


def test_passthrough_dat_cung_mot_chuoi_vao_ca_ba_truong():
    q = RewrittenQuery.passthrough("cơ chế attention là gì")
    assert q.cau_hoi == "cơ chế attention là gì"
    assert q.keywords == ["cơ chế attention là gì"]
    assert q.thuc_the == ["cơ chế attention là gì"]


def test_bm25_tra_ma_doan_va_diem_giam_dan(bm25_store):
    got = BM25Retriever(bm25_store).rank(_q(), session=None, k=5)
    assert got
    assert all(ma.startswith("T") for ma, _ in got)
    assert [d for _, d in got] == sorted((d for _, d in got), reverse=True)


def test_bm25_dung_truong_keywords_khong_dung_cau_hoi(bm25_store):
    """Moi retriever an mot truong khac nhau — do la ly do viet lai query."""
    got = BM25Retriever(bm25_store).rank(
        _q(keywords=["automation", "augmentation"], cau_hoi="hoan toan khong lien quan"),
        session=None, k=5,
    )
    assert got[0][0].startswith("T02")


def test_bm25_loc_duoc_theo_buoi(bm25_store):
    got = BM25Retriever(bm25_store).rank(_q(keywords=["attention"]), session="02", k=5)
    assert all(ma.startswith("T02") for ma, _ in got)


def test_bm25_query_rong_tra_rong(bm25_store):
    assert BM25Retriever(bm25_store).rank(_q(keywords=[]), session=None, k=5) == []


def test_null_tra_rong_va_mang_ly_do():
    r = NullRetriever("qdrant", "thieu QDRANT_URL")
    assert r.rank(_q(), session=None, k=5) == []
    assert r.reason == "thieu QDRANT_URL"
    assert r.name == "qdrant"


def test_qdrant_doi_hit_thanh_ma_doan_va_diem(monkeypatch):
    class Hit:
        def __init__(self, code, score):
            self.payload = {"citation_id": code}
            self.score = score

    monkeypatch.setattr(
        "vector_db.search.find_chunks",
        lambda q, session_id=None, top_k=5, **kw: (Hit("T04-072", 0.91), Hit("T04-071", 0.88)),
    )
    assert QdrantRetriever().rank(_q(), session=None, k=5) == [
        ("T04-072", 0.91), ("T04-071", 0.88)
    ]


def test_qdrant_dung_truong_cau_hoi_va_doi_ma_buoi(monkeypatch):
    ghi = {}

    def fake(q, session_id=None, top_k=5, **kw):
        ghi["query"] = q
        ghi["session_id"] = session_id
        ghi["top_k"] = top_k
        return ()

    monkeypatch.setattr("vector_db.search.find_chunks", fake)
    QdrantRetriever().rank(_q(cau_hoi="co che attention"), session="04", k=7)

    assert ghi["query"] == "co che attention"
    assert ghi["session_id"] == "T04"
    assert ghi["top_k"] == 7


def test_qdrant_bo_hit_thieu_citation_id(monkeypatch):
    class Hit:
        def __init__(self, payload, score):
            self.payload = payload
            self.score = score

    monkeypatch.setattr(
        "vector_db.search.find_chunks",
        lambda q, **kw: (Hit({}, 0.9), Hit({"citation_id": "T01-001"}, 0.8)),
    )
    assert QdrantRetriever().rank(_q(), session=None, k=5) == [("T01-001", 0.8)]


def test_safe_rank_bat_loi_va_khong_nem_ra_ngoai():
    class Vo:
        name = "vo"

        def rank(self, q, *, session, k):
            raise ConnectionError("mat mang")

    got = safe_rank(Vo(), _q(), session=None, k=5)
    assert got.ranking == []
    assert got.name == "vo"
    assert "mat mang" in got.error
    assert got.ms >= 0.0


def test_safe_rank_ghi_ly_do_khi_retriever_la_null():
    got = safe_rank(NullRetriever("neo4j", "Neo4j chet"), _q(), session=None, k=5)
    assert got.ranking == []
    assert got.error is None
    assert got.skipped_reason == "Neo4j chet"


def test_safe_rank_dedupe_ma_trung():
    """Retriever tra trung ma thi RRF se cong diem hai lan cho cung mot doan."""

    class Trung:
        name = "trung"

        def rank(self, q, *, session, k):
            return [("T01-001", 0.9), ("T01-001", 0.8), ("T01-002", 0.7)]

    got = safe_rank(Trung(), _q(), session=None, k=5)
    assert [ma for ma, _ in got.ranking] == ["T01-001", "T01-002"]


def test_neo4j_retriever_dung_truong_thuc_the(monkeypatch):
    import graph_db.retrieve as gr

    from flow1.retrievers import Neo4jRetriever

    ghi = {}

    def fake(thuc_the, *, session, k):
        ghi["thuc_the"] = thuc_the
        ghi["session"] = session
        return [("T04-072", 3.2)]

    monkeypatch.setattr(gr, "turns_for_concepts", fake)
    got = Neo4jRetriever().rank(_q(thuc_the=["attention", "transformer"]), session="04", k=5)

    assert ghi["thuc_the"] == ["attention", "transformer"]
    assert ghi["session"] == "04"
    assert got == [("T04-072", 3.2)]
