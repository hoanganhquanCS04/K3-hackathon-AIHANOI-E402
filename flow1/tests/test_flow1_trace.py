import json

import pytest

from flow1.trace import NullTrace, Trace, new_trace


def test_stage_ghi_lai_du_lieu_va_thoi_gian():
    trace = Trace("cau hoi")
    with trace.stage("bm25") as data:
        data["top"] = [("T01-001", 12.5)]

    assert len(trace.stages) == 1
    assert trace.stages[0].name == "bm25"
    assert trace.stages[0].data["top"] == [("T01-001", 12.5)]
    assert trace.stages[0].ms >= 0.0


def test_stage_giu_thu_tu_goi():
    trace = Trace("q")
    for name in ("rule_gate", "rewrite", "bm25", "qdrant", "neo4j", "fuse"):
        with trace.stage(name):
            pass
    assert [s.name for s in trace.stages] == [
        "rule_gate", "rewrite", "bm25", "qdrant", "neo4j", "fuse"
    ]


def test_loi_trong_stage_van_duoc_ghi_roi_moi_nem_tiep():
    trace = Trace("q")
    with pytest.raises(ValueError):
        with trace.stage("neo4j") as data:
            data["backend"] = "neo4j"
            raise ValueError("mat mang")

    assert trace.stages[0].name == "neo4j"
    assert trace.stages[0].data["backend"] == "neo4j"
    assert "mat mang" in trace.stages[0].data["error"]


def test_save_ghi_json_doc_lai_duoc(tmp_path):
    trace = Trace("attention la gi")
    with trace.stage("bm25") as data:
        data["n"] = 3

    path = trace.save(tmp_path)
    blob = json.loads(path.read_text(encoding="utf-8"))

    assert blob["query"] == "attention la gi"
    assert blob["run_id"] == trace.run_id
    assert blob["stages"][0]["name"] == "bm25"
    assert blob["stages"][0]["data"]["n"] == 3


def test_run_id_khac_nhau_giua_hai_lan_chay():
    assert Trace("q").run_id != Trace("q").run_id


def test_nulltrace_co_dung_api_cua_trace():
    for name in ("run_id", "query", "stages", "stage", "to_dict", "save"):
        assert hasattr(NullTrace(), name), f"NullTrace thieu {name}"


def test_nulltrace_khong_ghi_gi_va_khong_no():
    null = NullTrace()
    with null.stage("bm25") as data:
        data["top"] = [1, 2, 3]
    assert null.stages == []
    assert null.save(None) is None


def test_new_trace_chon_dung_loai():
    assert isinstance(new_trace("q", enabled=True), Trace)
    assert isinstance(new_trace("q", enabled=False), NullTrace)


def test_run_id_toan_doan_doc_lap_trong_batch():
    """Generate 2000 traces rapidly and verify all run_ids are unique.

    This test catches the birthday-paradox defect: the original 4-hex-char
    implementation (16 bits, 65536 buckets) would produce ~28 collisions
    when generating 2000 traces in a tight loop.
    """
    traces = [Trace(f"q{i}") for i in range(2000)]
    run_ids = [t.run_id for t in traces]

    unique_count = len(set(run_ids))
    assert unique_count == 2000, (
        f"Expected 2000 unique run_ids, got {unique_count} unique "
        f"({2000 - unique_count} collisions)"
    )


def test_save_khong_ghi_dang_khi_co_va_da_co(tmp_path):
    """save() must refuse to overwrite an existing trace file.

    If run_id collides, save() should raise FileExistsError rather than
    silently destroying the previous trace. Debug artifacts must never
    disappear without warning.
    """
    # Create first trace and save it
    trace1 = Trace("q1")
    path1 = trace1.save(tmp_path)
    assert path1.exists()

    # Force run_id collision by manually setting run_id to match trace1
    trace2 = Trace("q2")
    trace2.run_id = trace1.run_id

    # Second save should refuse to overwrite
    with pytest.raises(FileExistsError, match="already exists"):
        trace2.save(tmp_path)
