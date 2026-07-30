from flow1.trace import Trace
from flow1.trace_render import render_trace


def test_bang_co_ten_chang_va_thoi_gian():
    trace = Trace("attention la gi")
    with trace.stage("bm25") as data:
        data["top10"] = [("T04-001", 12.5), ("T04-002", 9.1)]

    text = render_trace(trace)
    assert "bm25" in text
    assert "T04-001" in text
    assert "ms" in text


def test_hien_ca_hai_ve_cua_so_sanh_nguong():
    trace = Trace("q")
    with trace.stage("gate1") as data:
        data["vi_sao"] = "ratio=1.13 < T1_RATIO=1.20"
        data["action"] = "refuse"

    text = render_trace(trace)
    assert "ratio=1.13 < T1_RATIO=1.20" in text
    assert "refuse" in text


def test_hien_dict_long_nhau_khong_no():
    trace = Trace("q")
    with trace.stage("fuse") as data:
        data["bang"] = [{"ma": "T01-001", "rank_bm25": 0, "rrf": 0.0164}]

    text = render_trace(trace)
    assert "T01-001" in text


def test_trace_rong_khong_no():
    assert render_trace(Trace("q")) != ""
