from flow1.agent import agent_run
from flow1.trace import Trace


def _goi_tool(name, args):
    def tool_call(system, user, tools):
        return {"name": name, "arguments": args}

    return tool_call


def test_rule_chan_chao_hoi_truoc_khi_toi_agent():
    def khong_duoc_goi(system, user, tools):
        raise AssertionError("rule phai chan truoc, khong duoc goi model")

    got = agent_run("hi", tool_call=khong_duoc_goi)
    assert got.outcome == "off_topic"
    assert got.tool_name is None


def test_rule_chan_logistics_truoc_khi_toi_agent():
    def khong_duoc_goi(system, user, tools):
        raise AssertionError("rule phai chan truoc")

    got = agent_run("deadline nop bai la khi nao", tool_call=khong_duoc_goi)
    assert got.outcome == "off_topic"


def test_rule_chan_cau_hoi_ve_chinh_bot():
    def khong_duoc_goi(system, user, tools):
        raise AssertionError("rule phai chan truoc")

    got = agent_run("ban la gpt hay claude", tool_call=khong_duoc_goi)
    assert got.outcome == "off_topic"


def test_agent_chon_tom_tat_thi_goi_dung_tool():
    ghi = {}

    def tom_tat_gia(session_id, *, trace=None, **kw):
        ghi["session_id"] = session_id
        return {"session_id": session_id, "key_points": []}

    got = agent_run(
        "tom tat buoi 3 cho minh",
        tool_call=_goi_tool("tom_tat", {"session_id": "T03"}),
        tools={"tom_tat": tom_tat_gia},
    )
    assert got.tool_name == "tom_tat"
    assert ghi["session_id"] == "T03"


def test_agent_chon_tra_cuu_thi_truyen_dung_tham_so():
    ghi = {}

    def tra_cuu_gia(query, *, session=None, trace=None, **kw):
        ghi["query"] = query
        ghi["session"] = session
        return {"outcome": "answered"}

    got = agent_run(
        "co che attention la gi",
        tool_call=_goi_tool("tra_cuu", {"query": "co che attention la gi", "session": "04"}),
        tools={"tra_cuu": tra_cuu_gia},
    )
    assert got.tool_name == "tra_cuu"
    assert ghi["query"] == "co che attention la gi"
    assert ghi["session"] == "04"


def test_model_chon_tool_khong_ton_tai_thi_lui_ve_tra_cuu():
    ghi = {}

    def tra_cuu_gia(query, **kw):
        ghi["goi"] = True
        return {"outcome": "answered"}

    got = agent_run(
        "attention la gi",
        tool_call=_goi_tool("tool_bia_ra", {}),
        tools={"tra_cuu": tra_cuu_gia},
    )
    assert ghi.get("goi") is True
    assert got.tool_name == "tra_cuu"


def test_goi_model_that_bai_thi_lui_ve_tra_cuu():
    ghi = {}

    def no(system, user, tools):
        raise RuntimeError("het quota")

    def tra_cuu_gia(query, **kw):
        ghi["goi"] = True
        return {"outcome": "answered"}

    got = agent_run("attention la gi", tool_call=no, tools={"tra_cuu": tra_cuu_gia})
    assert ghi.get("goi") is True


def test_trace_ghi_rule_gate_va_lua_chon_tool():
    trace = Trace("attention la gi")
    agent_run(
        "attention la gi",
        tool_call=_goi_tool("tra_cuu", {"query": "attention la gi"}),
        tools={"tra_cuu": lambda query, **kw: {"outcome": "answered"}},
        trace=trace,
    )
    names = [s.name for s in trace.stages]
    assert "rule_gate" in names
    assert "agent" in names
    agent = next(s for s in trace.stages if s.name == "agent")
    assert agent.data["tool_da_chon"] == "tra_cuu"
