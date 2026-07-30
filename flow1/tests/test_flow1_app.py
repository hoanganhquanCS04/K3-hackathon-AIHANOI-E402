try:
    from helpers import branch_table
except ImportError:
    from flow1.app.helpers import branch_table


def test_branch_table_tra_du_hang_va_truong():
    raw_fuse = [
        {"ma": "T01-001", "rank_bm25": 0, "rank_qdrant": 1, "rank_neo4j": None, "rrf": 0.032},
        {"ma": "T02-005", "rank_bm25": None, "rank_qdrant": 0, "rank_neo4j": None, "rrf": 0.016},
    ]
    got = branch_table(raw_fuse)
    assert len(got) == 2
    assert got[0]["Mã đoạn"] == "T01-001"
    assert got[0]["BM25"] == "#1"
    assert got[0]["Qdrant"] == "#2"
    assert got[0]["Neo4j"] == "—"
    assert got[0]["Chỉ nhánh này?"] == "—"

    # T02-005 chi Qdrant tim ra
    assert got[1]["Chỉ nhánh này?"] == "Qdrant"


def test_chi_nhanh_nay_danh_dau_dung_nhanh_doc_quyen():
    raw = [{"ma": "T03-009", "rank_bm25": None, "rank_qdrant": None, "rank_neo4j": 0, "rrf": 0.016}]
    got = branch_table(raw)
    assert got[0]["Chỉ nhánh này?"] == "Neo4j"
