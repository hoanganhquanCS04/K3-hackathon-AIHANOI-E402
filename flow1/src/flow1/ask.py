"""Ghép 4 cổng. Cổng 2 nằm ở đây. Chủ: M2 (khối E).

Thứ tự cổng là thứ tự tiết kiệm: mỗi cổng đứng trước loại bỏ được một lớp câu mà
cổng sau sẽ phải tốn token để xử.

  cổng 0 (rule)  → 0 token
  cổng 0 (LLM)   → 1 call rẻ
  cổng 1 (code)  → 0 token, chặn TRƯỚC generate
  cổng 2 (LLM)   → 1 call đắt, chỉ chạy khi 3 cổng trên đã cho qua
  cổng 3 (code)  → 0 token

HƯỚNG FAIL BẤT ĐỐI XỨNG, có chủ ý:
  cổng 0 lỗi → FAIL MỞ, đi tiếp. An toàn vì cổng 1 tất định vẫn đứng sau.
  cổng 2 lỗi → FAIL ĐÓNG, outcome="error". Cổng 2 SINH nội dung; hỏng nó mà đi
               tiếp là mở đường cho đúng thứ cả sản phẩm đang phòng.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from flow1.check import check
from flow1.gates import CONTENT_LABEL, gate0, gate1, template_for
from flow1.index import BM25_PATH
from flow1.models import Answer, Intent, Retrieval, Seg, Verdict
from flow1.prompts import ANSWER_SYSTEM, answer_user, format_context
from flow1.retrieve import retrieve


@dataclass(frozen=True)
class Result:
    """Kết quả một lượt hỏi. `outcome` là thứ CLI và render đọc để quyết hiển thị gì.

    answered    — có claim đã qua cổng 3
    insufficient— model tự khai không đủ, HOẶC cổng 3 loại hết claim
    refused     — cổng 1 chặn: không đủ căn cứ trong 6 buổi
    clarify     — cổng 1 hỏi lại: chủ đề nằm ở nhiều buổi
    off_topic   — cổng 0 chặn: logistics / ngoài phạm vi / chào hỏi
    error       — cổng 2 lỗi. KHÔNG có câu trả lời nào được sinh ra.
    """

    outcome: str
    question: str
    message: str
    intent: Intent | None = None
    decision: object | None = None
    verdict: Verdict | None = None
    retrieval: Retrieval | None = None
    trace: object | None = None


def ask(
    question: str,
    *,
    session: str | None = None,
    segs: list[Seg] | None = None,
    store: tuple | None = None,
    path: Path = BM25_PATH,
    classify_call=None,
    answer_call=None,
    check_citations=None,
    trace=None,
    rewritten=None,
    toggles=None,
    retrievers=None,
    stream_callback=None,
) -> Result:
    """Một lượt hỏi qua 4 cổng. Mọi lời gọi model inject được để test không cần mạng."""
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(question)

    # ---- CỔNG 0 -----------------------------------------------------------
    with trace.stage("gate0") as tdata:
        intent = gate0(question, call=classify_call)
        tdata["label"] = intent.label
        tdata["reason"] = intent.reason
        tdata["quyet_boi"] = "rule" if "rule tất định" in intent.reason else "llm"
    if intent.label != CONTENT_LABEL:
        return Result(outcome="off_topic", question=question,
                      message=template_for(intent.label), intent=intent, trace=trace)

    # ---- RETRIEVE ---------------------------------------------------------
    ret_kwargs = {"session": session, "store": store, "path": path, "trace": trace}
    if toggles is not None:
        ret_kwargs["toggles"] = toggles
    if retrievers is not None:
        ret_kwargs["retrievers"] = retrievers

    retrieval = retrieve(
        rewritten if rewritten is not None else question,
        **ret_kwargs,
    )

    # ---- CỔNG 1 -----------------------------------------------------------
    with trace.stage("gate1") as tdata:
        from flow1.thresholds import T1_ABS, T1_RATIO

        decision = gate1(retrieval)
        tdata["top1_abs"] = retrieval.top1_abs
        tdata["ratio"] = "inf" if retrieval.ratio == math.inf else retrieval.ratio
        tdata["T1_ABS"] = T1_ABS
        tdata["T1_RATIO"] = T1_RATIO
        tdata["action"] = decision.action
        ly_do = []
        if retrieval.top1_abs < T1_ABS:
            ly_do.append(f"top1_abs={retrieval.top1_abs:.2f} < T1_ABS={T1_ABS}")
        if retrieval.ratio < T1_RATIO:
            ly_do.append(f"ratio={retrieval.ratio:.2f} < T1_RATIO={T1_RATIO}")
        tdata["vi_sao"] = " va ".join(ly_do) if ly_do else "ca hai nguong deu qua"

    if decision.action == "refuse":
        return Result(outcome="refused", question=question, message=decision.message,
                      intent=intent, decision=decision, retrieval=retrieval, trace=trace)
    if decision.action == "clarify":
        return Result(outcome="clarify", question=question, message=decision.message,
                      intent=intent, decision=decision, retrieval=retrieval, trace=trace)

    # ---- CỔNG 2 -----------------------------------------------------------
    if answer_call is None:
        def _llm_call(system, user_blocks, schema):
            import os
            user = "\n\n".join(b["text"] for b in user_blocks if b["type"] == "text")
            if stream_callback is not None:
                from openai import OpenAI
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY", ""),
                    base_url=os.getenv("OPENAI_BASE_URL") or None,
                )
                response_stream = client.chat.completions.create(
                    model=os.getenv("ANSWER_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    stream=True,
                    temperature=0.0,
                )
                full_text = ""
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        delta = chunk.choices[0].delta.content
                        full_text += delta
                        try:
                            stream_callback(delta)
                        except Exception:
                            pass
                return schema.model_validate_json(full_text)
            else:
                from summarizer.llm import OpenAIStructuredLLM
                llm = OpenAIStructuredLLM()
                return llm.parse(
                    model="gpt-4o-mini",
                    system=system,
                    user=user,
                    schema=schema,
                    temperature=0.0,
                )
        answer_call = _llm_call

    with trace.stage("context") as tdata:
        user_blocks = [
            {"type": "text", "text": format_context(retrieval)},
            {"type": "text", "text": answer_user(question, session)},
        ]
        tdata["chunk_ids"] = [h.chunk.chunk_id for h in retrieval.hits]
        tdata["n_chars"] = sum(len(b["text"]) for b in user_blocks)

    with trace.stage("generate") as tdata:
        try:
            answer = answer_call(ANSWER_SYSTEM, user_blocks, Answer)
        except Exception as exc:
            # FAIL ĐÓNG. Không có câu trả lời nào tốt hơn một câu trả lời bịa.
            tdata["that_bai"] = str(exc)
            return Result(outcome="error", question=question,
                          message=f"Không gọi được model, nên mình không trả lời: {exc}",
                          intent=intent, decision=decision, retrieval=retrieval, trace=trace)
        tdata["status"] = answer.status
        tdata["n_claim"] = len(answer.claims)

    # ---- CỔNG 3 -----------------------------------------------------------
    if segs is None:
        from flow1.parse import parse_all        # nạp 700 đoạn để kiểm mã

        segs = parse_all()

    with trace.stage("gate3") as tdata:
        verdict = check(answer, retrieval, segs, check_citations=check_citations)
        tdata["status"] = verdict.status
        tdata["n_claim_qua"] = len(verdict.claims)
        tdata["drops"] = [(d.kind, d.claim_text[:60]) for d in verdict.drops]
        tdata["student_codes"] = verdict.student_codes
        tdata["gap_codes"] = verdict.gap_codes

    return Result(outcome=verdict.status, question=question, message="",
                  intent=intent, decision=decision, verdict=verdict, retrieval=retrieval, trace=trace)
