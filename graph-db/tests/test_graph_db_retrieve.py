from graph_db.retrieve import CYPHER, turns_for_concepts


def _fake_run(rows):
    """Gia lap graph_db.query: tra ve danh sach dict nhu driver that."""

    def run(cypher, params):
        return rows

    return run


def test_tra_ve_ma_doan_that_khong_phai_ten_concept():
    rows = [
        {"ma": "T04-072", "diem": 3.2, "hop": 0},
        {"ma": "T04-071", "diem": 1.6, "hop": 1},
    ]
    got = turns_for_concepts(["attention"], session=None, k=5, run=_fake_run(rows))
    assert [ma for ma, _ in got] == ["T04-072", "T04-071"]


def test_hop_0_luon_dung_truoc_hop_1_du_diem_thap_hon():
    """Doan noi thang ve concept dang tin hon doan cach 1 quan he."""
    rows = [
        {"ma": "T01-005", "diem": 0.4, "hop": 0},
        {"ma": "T09-001", "diem": 9.9, "hop": 1},
    ]
    got = turns_for_concepts(["x"], session=None, k=5, run=_fake_run(rows))
    assert [ma for ma, _ in got] == ["T01-005", "T09-001"]


def test_dedupe_giu_lan_xuat_hien_tot_nhat():
    rows = [
        {"ma": "T01-001", "diem": 5.0, "hop": 0},
        {"ma": "T01-001", "diem": 1.0, "hop": 1},
        {"ma": "T01-002", "diem": 2.0, "hop": 0},
    ]
    got = turns_for_concepts(["x"], session=None, k=5, run=_fake_run(rows))
    assert [ma for ma, _ in got] == ["T01-001", "T01-002"]
    assert got[0][1] == 5.0


def test_cat_dung_k():
    rows = [{"ma": f"T01-{i:03d}", "diem": 10 - i, "hop": 0} for i in range(1, 8)]
    assert len(turns_for_concepts(["x"], session=None, k=3, run=_fake_run(rows))) == 3


def test_thuc_the_rong_khong_goi_graph():
    def no(cypher, params):
        raise AssertionError("khong duoc goi graph khi khong co thuc the")

    assert turns_for_concepts([], session=None, k=5, run=no) == []


def test_truyen_session_xuong_lam_tham_so():
    ghi = {}

    def run(cypher, params):
        ghi.update(params)
        return []

    turns_for_concepts(["attention"], session="04", k=5, run=run)
    assert ghi["session"] == "T04"
    assert "attention" in ghi["thuc_the"]


def test_cypher_khong_lay_mo_ta_concept():
    """KG mo rong recall, KHONG mo rong tham quyen — chi lay Turn.id.

    Mot chu nao cua Concept.description lot vao prompt la KG tro thanh nguon
    khang dinh, ma concept do LLM sinh ra luc ingest.
    """
    assert "description" not in CYPHER
    sau_return = CYPHER.split("RETURN", 1)[1]
    assert "c.name" not in sau_return


def test_cypher_loai_hoat_dong_lop():
    assert "is_activity = false" in CYPHER
