from flow1.retrievers import RewrittenQuery
from flow1.rewrite import rewrite_query
from flow1.trace import Trace


def _call_tra(keywords, cau_hoi, thuc_the):
    def call(system, user_blocks, schema):
        return RewrittenQuery(keywords=keywords, cau_hoi=cau_hoi, thuc_the=thuc_the)

    return call


def test_tra_du_ba_truong():
    got = rewrite_query(
        "cơ chế chú ý là gì",
        call=_call_tra(["chú ý", "attention"], "Cơ chế attention hoạt động thế nào?", ["attention"]),
    )
    assert got.keywords == ["chú ý", "attention"]
    assert got.cau_hoi == "Cơ chế attention hoạt động thế nào?"
    assert got.thuc_the == ["attention"]


def test_loi_goi_model_thi_lui_ve_passthrough_khong_nem():
    def no(system, user_blocks, schema):
        raise RuntimeError("het quota")

    got = rewrite_query("cơ chế attention", call=no)
    assert got.cau_hoi == "cơ chế attention"
    assert got.keywords == ["cơ chế attention"]


def test_model_tra_thieu_truong_thi_lui_ve_passthrough():
    def hong(system, user_blocks, schema):
        return "khong phai RewrittenQuery"

    got = rewrite_query("attention", call=hong)
    assert got == RewrittenQuery.passthrough("attention")


def test_keywords_rong_thi_lui_ve_passthrough():
    """keywords rong lam BM25 tra rong, ma BM25 la nguon cua cong 1."""
    got = rewrite_query("attention", call=_call_tra([], "attention la gi", ["attention"]))
    assert got.keywords == ["attention"]


def test_trace_ghi_ca_query_goc_lan_ba_dang():
    trace = Trace("cơ chế chú ý là gì")
    rewrite_query(
        "cơ chế chú ý là gì",
        call=_call_tra(["chú ý", "attention"], "Attention la gi?", ["attention"]),
        trace=trace,
    )
    stage = next(s for s in trace.stages if s.name == "rewrite")
    assert stage.data["goc"] == "cơ chế chú ý là gì"
    assert stage.data["keywords"] == ["chú ý", "attention"]
    assert stage.data["cau_hoi"] == "Attention la gi?"
    assert stage.data["thuc_the"] == ["attention"]


def test_trace_ghi_ly_do_khi_lui():
    def no(system, user_blocks, schema):
        raise RuntimeError("het quota")

    trace = Trace("q")
    rewrite_query("attention", call=no, trace=trace)
    stage = next(s for s in trace.stages if s.name == "rewrite")
    assert "het quota" in stage.data["da_lui"]


def test_khong_truyen_call_va_khong_co_provider_thi_van_chay(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "summarizer.llm.OpenAIStructuredLLM.parse",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no key")),
    )
    got = rewrite_query("attention")
    assert got.cau_hoi == "attention"
