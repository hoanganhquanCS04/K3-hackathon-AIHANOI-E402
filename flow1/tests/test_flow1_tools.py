import pytest

from flow1.retrieve import Toggles
from flow1.tools import TOOL_SCHEMAS, tom_tat, tra_cuu
from flow1.trace import Trace


def _intent_noi_dung(system, blocks, schema):
    from flow1.models import Intent

    return Intent(label="nội_dung_khoá", reason="test")


def _no_model(*args):
    raise RuntimeError("khong goi model trong test")


def _rewrite_thang(system, blocks, schema):
    from flow1.retrievers import RewrittenQuery

    return RewrittenQuery(keywords=["attention"], cau_hoi="attention la gi", thuc_the=["attention"])


def _chi_bm25(store):
    from flow1.retrievers import BM25Retriever, NullRetriever

    return {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "tat trong test"),
        "neo4j": NullRetriever("neo4j", "tat trong test"),
    }


def test_co_dung_hai_tool():
    assert {s["function"]["name"] for s in TOOL_SCHEMAS} == {"tra_cuu", "tom_tat"}


def test_schema_tool_khai_du_tham_so_bat_buoc():
    tra = next(s for s in TOOL_SCHEMAS if s["function"]["name"] == "tra_cuu")
    assert "query" in tra["function"]["parameters"]["required"]

    tom = next(s for s in TOOL_SCHEMAS if s["function"]["name"] == "tom_tat")
    assert "session_id" in tom["function"]["parameters"]["required"]


def test_tra_cuu_di_qua_viet_lai_query_roi_moi_retrieve(bm25_store):
    trace = Trace("q")
    tra_cuu(
        "cơ chế attention là gì",
        store=bm25_store, trace=trace, segs=[], retrievers=_chi_bm25(bm25_store),
        rewrite_call=_rewrite_thang, classify_call=_intent_noi_dung, answer_call=_no_model,
    )
    names = [s.name for s in trace.stages]
    assert names.index("rewrite") < names.index("bm25")


def test_tra_cuu_truyen_toggles_xuong_retrieve(bm25_store):
    trace = Trace("q")
    tra_cuu(
        "attention", store=bm25_store, trace=trace, segs=[], retrievers=_chi_bm25(bm25_store),
        toggles=Toggles(bm25=True, qdrant=False, neo4j=False),
        rewrite_call=_rewrite_thang, classify_call=_intent_noi_dung, answer_call=_no_model,
    )
    qdrant = next(s for s in trace.stages if s.name == "qdrant")
    assert qdrant.data["gop_vao_fusion"] is False


def test_tom_tat_tra_ve_tom_tat_co_ma_doan():
    def load_summary(session_id):
        return {"session_id": session_id, "key_points": [{"claim": "x", "cite": ["T03-001"]}]}

    got = tom_tat("T03", load_summary=load_summary)
    assert got["session_id"] == "T03"
    assert got["key_points"][0]["cite"] == ["T03-001"]


def test_tom_tat_buoi_khong_ton_tai_thi_tu_choi_liet_ke_buoi_co_san():
    def load_summary(session_id):
        raise FileNotFoundError(session_id)

    got = tom_tat("T07", load_summary=load_summary)
    assert got["status"] == "out_of_scope"
    assert "T01" in got["message"]


def test_tom_tat_chuan_hoa_ma_buoi():
    ghi = {}

    def load_summary(session_id):
        ghi["session_id"] = session_id
        return {"session_id": session_id, "key_points": []}

    tom_tat("3", load_summary=load_summary)
    assert ghi["session_id"] == "T03"


def test_tom_tat_ghi_trace():
    trace = Trace("tom tat buoi 3")
    tom_tat("T03", trace=trace, load_summary=lambda s: {"session_id": s, "key_points": []})
    stage = next(s for s in trace.stages if s.name == "tom_tat")
    assert stage.data["session_id"] == "T03"
