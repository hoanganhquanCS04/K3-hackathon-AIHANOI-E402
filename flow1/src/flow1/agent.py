"""Agent dieu phoi hai tool, co RULE TAT DINH chan truoc.

THU TU LA CO CHU Y:
  rule (0 token)  -> chan chao hoi, logistics, ngoai pham vi, jailbreak
  agent (1 call)  -> chon tool va dien tham so
  tool            -> lam viec that

Chan bang rule truoc giu duoc hai thu: moi cau rac khong ton mot loi goi model,
va lop chan tat dinh ma 4 cong dang dua vao khong bi thay bang phan doan cua
model. Day la khac biet voi "agent thuan" — va la thu giai thich duoc o CP5.

LUI VE TRA_CUU: model hong, tra tool la, hay khong chon tool nao thi mac dinh
tra_cuu. Cau hoi ve noi dung la da so, va tra_cuu con 4 cong dung sau no —
doan sai o day khong lam mat lop bao ve nao.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flow1.gates import CONTENT_LABEL, classify_rule, template_for
from flow1.tools import TOOL_SCHEMAS

AGENT_SYSTEM = """Ban dieu phoi mot tro ly hoc tap cho khoa AI co ban ghi 6 buoi.

Chon DUNG MOT tool cho moi cau hoi:
- tra_cuu: hoc vien hoi ve kien thuc, khai niem, vi du, cach lam.
- tom_tat: hoc vien xin tom tat ca mot buoi, xin y chinh cua buoi, hoac hoi
  "buoi X noi ve gi".

Khi hoc vien khong noi ro buoi nao thi BO TRONG tham so buoi — he thong se
hoi lai neu can, dung tu doan mot buoi."""


@dataclass(frozen=True)
class AgentResult:
    outcome: str
    message: str
    tool_name: str | None = None
    result: Any = None
    trace: object | None = None


def _default_tool_call(system: str, user: str, tools: list[dict]) -> dict[str, Any]:
    import json
    import os

    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    response = client.chat.completions.create(
        model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        tools=tools,
        tool_choice="required",
        temperature=0.0,
    )
    call = response.choices[0].message.tool_calls[0]
    return {"name": call.function.name, "arguments": json.loads(call.function.arguments)}


def agent_run(
    question: str,
    *,
    tool_call=None,
    tools: dict | None = None,
    trace=None,
    **tool_kwargs,
) -> AgentResult:
    """Rule chan truoc, roi agent chon tool, roi chay tool do."""
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(question)

    # ---- RULE TAT DINH, 0 token ------------------------------------------
    with trace.stage("rule_gate") as tdata:
        label = classify_rule(question)
        tdata["nhan"] = label
        tdata["chan"] = label is not None and label != CONTENT_LABEL
    if label is not None and label != CONTENT_LABEL:
        return AgentResult(
            outcome="off_topic", message=template_for(label), trace=trace
        )

    if tools is None:
        from flow1 import tools as _tools_mod

        tools = {"tra_cuu": _tools_mod.tra_cuu, "tom_tat": _tools_mod.tom_tat}

    # ---- AGENT chon tool --------------------------------------------------
    with trace.stage("agent") as tdata:
        call = tool_call if tool_call is not None else _default_tool_call
        chon: dict[str, Any]
        try:
            chon = call(AGENT_SYSTEM, question, TOOL_SCHEMAS)
        except Exception as exc:
            tdata["da_lui"] = f"{type(exc).__name__}: {exc}"
            chon = {"name": "tra_cuu", "arguments": {"query": question}}

        ten = chon.get("name")
        if ten not in tools:
            tdata["tool_la"] = ten
            tdata["da_lui"] = f"model chon tool khong co that: {ten!r}"
            chon = {"name": "tra_cuu", "arguments": {"query": question}}
            ten = "tra_cuu"

        args = dict(chon.get("arguments") or {})
        if ten == "tra_cuu":
            args.setdefault("query", question)
            if not (args.get("session") or "").strip():
                args.pop("session", None)
        tdata["tool_da_chon"] = ten
        tdata["tham_so"] = args

    ket_qua = tools[ten](**args, trace=trace, **tool_kwargs)
    return AgentResult(
        outcome=getattr(ket_qua, "outcome", None) or getattr(ket_qua, "get", lambda k, d=None: d)("status", "answered"),
        message=getattr(ket_qua, "message", "") or getattr(ket_qua, "get", lambda k, d=None: d)("message", ""),
        tool_name=ten,
        result=ket_qua,
        trace=trace,
    )
