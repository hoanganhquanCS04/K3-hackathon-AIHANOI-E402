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
) -> Result:
    """Một lượt hỏi qua 4 cổng. Mọi lời gọi model inject được để test không cần mạng."""
    # ---- CỔNG 0 -----------------------------------------------------------
    intent = gate0(question, call=classify_call)
    if intent.label != CONTENT_LABEL:
        return Result(outcome="off_topic", question=question,
                      message=template_for(intent.label), intent=intent)

    # ---- RETRIEVE ---------------------------------------------------------
    retrieval = retrieve(question, session=session, store=store, path=path)

    # ---- CỔNG 1 -----------------------------------------------------------
    decision = gate1(retrieval)
    if decision.action == "refuse":
        return Result(outcome="refused", question=question, message=decision.message,
                      intent=intent, decision=decision, retrieval=retrieval)
    if decision.action == "clarify":
        return Result(outcome="clarify", question=question, message=decision.message,
                      intent=intent, decision=decision, retrieval=retrieval)

    # ---- CỔNG 2 -----------------------------------------------------------
    if answer_call is None:
        try:
            from summarizer.llm import OpenAIStructuredLLM
            def _llm_call(system, user_blocks, schema):
                llm = OpenAIStructuredLLM()
                user = "\n\n".join(b["text"] for b in user_blocks if b["type"] == "text")
                return llm.parse(
                    model="gpt-4o-mini",
                    system=system,
                    user=user,
                    schema=schema,
                    temperature=0.0
                )
            answer_call = _llm_call
        except ImportError:
            def dummy_answer_call(system, user_blocks, schema):
                raise RuntimeError("summarizer.llm chưa khả dụng")
            answer_call = dummy_answer_call

    user_blocks = [
        {"type": "text", "text": format_context(retrieval)},
        {"type": "text", "text": answer_user(question, session)},
    ]
    try:
        answer = answer_call(ANSWER_SYSTEM, user_blocks, Answer)
    except Exception as exc:
        # FAIL ĐÓNG. Không có câu trả lời nào tốt hơn một câu trả lời bịa.
        return Result(outcome="error", question=question,
                      message=f"Không gọi được model, nên mình không trả lời: {exc}",
                      intent=intent, decision=decision, retrieval=retrieval)

    # ---- CỔNG 3 -----------------------------------------------------------
    if segs is None:
        from flow1.parse import parse_all        # nạp 700 đoạn để kiểm mã

        segs = parse_all()

    verdict = check(answer, retrieval, segs, check_citations=check_citations)

    return Result(outcome=verdict.status, question=question, message="",
                  intent=intent, decision=decision, verdict=verdict, retrieval=retrieval)
