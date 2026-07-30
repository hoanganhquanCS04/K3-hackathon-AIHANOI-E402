from flow1.ask import ask
from flow1.models import Intent
from flow1.trace import NullTrace, Trace


def _intent_noi_dung(system, blocks, schema):
    return Intent(label="nội_dung_khoá", reason="test")


def _no_model(*args):
    raise RuntimeError("khong goi model trong test")


def test_ask_ghi_stage_gate0_bm25_gate1(bm25_store):
    trace = Trace("attention la gi")
    ask("cơ chế attention là gì", store=bm25_store, segs=[], trace=trace,
        classify_call=_intent_noi_dung, answer_call=_no_model)
    names = [s.name for s in trace.stages]
    assert "gate0" in names
    assert "bm25" in names
    assert "gate1" in names


def test_gate1_ghi_ca_hai_ve_cua_moi_so_sanh(bm25_store):
    from flow1.thresholds import T1_ABS, T1_RATIO

    trace = Trace("q")
    ask("cơ chế attention là gì", store=bm25_store, segs=[], trace=trace,
        classify_call=_intent_noi_dung, answer_call=_no_model)
    gate1 = next(s for s in trace.stages if s.name == "gate1")
    assert gate1.data["T1_ABS"] == T1_ABS
    assert gate1.data["T1_RATIO"] == T1_RATIO
    assert "top1_abs" in gate1.data
    assert gate1.data["action"] in {"pass", "refuse", "clarify"}


def test_khong_truyen_trace_thi_khong_no(bm25_store):
    result = ask("cơ chế attention là gì", store=bm25_store, segs=[],
                 classify_call=_intent_noi_dung, answer_call=_no_model)
    assert isinstance(result.trace, NullTrace)
