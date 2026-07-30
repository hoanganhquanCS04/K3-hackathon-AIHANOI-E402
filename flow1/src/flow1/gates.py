"""Cổng 0 (phân loại ý định) và Cổng 1 (từ chối cứng và hỏi lại khi mơ hồ).

Chủ: M2 (khối E).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from flow1.models import Intent, Retrieval
from flow1.prompts import GATE0_SYSTEM, gate0_user
from flow1.thresholds import AMBIG_BAND, T1_ABS, T1_RATIO

CONTENT_LABEL = "nội_dung_khoá"
VALID_LABELS = (CONTENT_LABEL, "logistics", "ngoài_phạm_vi", "chào_hỏi")

RULE_EVIDENCE: dict[str, tuple[str, ...]] = {
    "ngoài_phạm_vi": (
        "T0733", "T0664", "T1237", "T0072", "T0790", "T0171", "T0407", "T0527",
        "T1241", "T0414", "T0928", "T0594",
        "T0148", "T0470", "T0874",
        "T0837",
    ),
    "chào_hỏi": ("T0495", "T0327", "T0402", "T0438", "T0271", "T1104"),
    "logistics": (),
}

_HIGHLIGHT_PREFIX = re.compile(r"^\s*(giải thích|giai thich|tóm tắt|tom tat|dịch)\b", re.I)

_GREETING_ONLY = re.compile(
    r"^\s*(hi+|hello+|hey|chào|xin chào|ok|okay|cảm ơn|cám ơn|thanks|thank you|hí)"
    r"[\s\.\!\?,]*$",
    re.I,
)

_JAILBREAK = re.compile(
    r"bỏ qua\s+(các\s+)?(cảnh báo|ràng buộc|guardrail|giới hạn|quy tắc)"
    r"|ignore\s+(all\s+)?(previous|prior)\s+instruction"
    r"|giả sử bạn là",
    re.I,
)

_ASKS_ABOUT_BOT = re.compile(
    r"\b(bạn|ban|b|you|your|tutor)\b[^?!.]{0,45}\b(model|gpt|claude|gemini|chatgpt|pretrain)\b"
    r"|\b(model|pretrain)\b[^?!.]{0,45}\b(bạn|ban|you|your|tutor)\b",
    re.I,
)

_WANTS_ANSWER_KEY = re.compile(
    r"(đáp án|dap an|lời giải|loi giai|solution)[^?!.]{0,30}(lab|bài tập|bai tap|quiz|assignment)",
    re.I,
)

_LOGISTICS = re.compile(
    r"\b(deadline|hạn nộp|nộp bài|nộp ở đâu|link zoom|lịch học|điểm danh|học phí)\b",
    re.I,
)

TEMPLATES: dict[str, str] = {
    "logistics": (
        "Mình chỉ tra được nội dung lời giảng trong 6 buổi có bản ghi, không nắm "
        "việc hành chính của khoá (deadline, cách nộp bài, link). Chỗ đó bạn hỏi "
        "trong kênh lớp sẽ nhanh hơn."
    ),
    "ngoài_phạm_vi": (
        "Câu này ngoài phạm vi của mình. Mình chỉ trả lời dựa trên nội dung lời "
        "giảng của 6 buổi có bản ghi, và mọi câu trả lời đều kèm mã đoạn để bạn "
        "tự kiểm."
    ),
    "chào_hỏi": (
        "Chào bạn. Hỏi mình một câu về nội dung buổi học đi — mình tra trong bản "
        "ghi 6 buổi và trả lời kèm mã đoạn để bạn bấm về nguyên văn lời giảng."
    ),
}


def template_for(label: str) -> str:
    """Câu khuôn mẫu cho nhãn không phải nội dung. Nhãn lạ → rỗng."""
    return TEMPLATES.get(label, "")


def classify_rule(question: str) -> str | None:
    """Phân loại bằng rule tất định. None = rule không kết luận, để LLM xử."""
    text = question.strip()
    if not text:
        return "chào_hỏi"
    if _GREETING_ONLY.match(text):
        return "chào_hỏi"
    if _JAILBREAK.search(text):
        return "ngoài_phạm_vi"
    if _HIGHLIGHT_PREFIX.match(text):
        return None
    if _ASKS_ABOUT_BOT.search(text) or _WANTS_ANSWER_KEY.search(text):
        return "ngoài_phạm_vi"
    if _LOGISTICS.search(text):
        return "logistics"
    return None


def gate0(question: str, *, call=None) -> Intent:
    """Cổng 0. Rule trước; rule im lặng thì 1 lời gọi model rẻ."""
    label = classify_rule(question)
    if label is not None:
        return Intent(label=label, reason=f"rule tất định khớp nhãn {label}")

    if call is None:
        try:
            from sotay.llm import complete_json      # LAZY
            call = complete_json
        except ImportError:
            def dummy_call(system, user_blocks, schema):
                return Intent(label=CONTENT_LABEL, reason="fallback")
            call = dummy_call

    try:
        intent = call(GATE0_SYSTEM, [{"type": "text", "text": gate0_user(question)}], Intent)
    except Exception as exc:
        return Intent(label=CONTENT_LABEL, reason=f"cổng 0 lỗi ({exc}), fail mở, cổng 1 sẽ chặn")

    if getattr(intent, "label", None) not in VALID_LABELS:
        return Intent(label=CONTENT_LABEL, reason="cổng 0 trả nhãn lạ, fail mở")

    return Intent(label=intent.label, reason=intent.reason)


@dataclass(frozen=True)
class Decision:
    """Kết luận của cổng 1."""

    action: Literal["pass", "refuse", "clarify"]
    message: str          # rỗng khi action == "pass"
    retrieval: Retrieval


def nearest_headings(r: Retrieval, n: int = 3) -> list[str]:
    """`n` heading gần nhất, dạng "Buổi 03 › RAG và tool calling", đã dedupe."""
    seen: dict[str, None] = {}
    for hit in r.hits:
        seen.setdefault(f"Buổi {hit.session} › {hit.section_title}", None)
        if len(seen) == n:
            break
    return list(seen)


def _first_other_session_heading(
    wide: Retrieval, exclude: set[str]
) -> tuple[str, str] | None:
    seen: set[tuple[str, str]] = set()
    for hit in wide.hits:
        key = (hit.session, hit.section_title)
        if key in seen:
            continue
        seen.add(key)
        if hit.session not in exclude:
            return key
    return None


def refusal_message(r: Retrieval, all_sessions: Retrieval | None = None) -> str:
    headings = nearest_headings(r)
    base = "Nội dung này không có trong 6 buổi mình có bản ghi."
    if not headings:
        message = f"{base} Bạn thử diễn đạt lại bằng từ khoá khác xem sao."
    else:
        listed = "\n".join(f"  - {h}" for h in headings)
        message = f"{base} Gần nhất là:\n{listed}"

    if all_sessions is not None:
        extra = _first_other_session_heading(all_sessions, exclude=set(r.sessions))
        if extra is not None:
            session, section_title = extra
            message += (
                f"\n\nBuổi {session} › {section_title} có nói tới nội dung này "
                "(một buổi khác)."
            )

    return message


def _clarify_message(r: Retrieval) -> str:
    first, second = r.hits[0], r.hits[1]
    return (
        f"Chủ đề này có ở cả buổi {first.session} ({first.section_title}) "
        f"và buổi {second.session} ({second.section_title}) — bạn hỏi buổi nào?\n"
        f"Chạy lại kèm buổi, ví dụ:  --session {first.session}"
    )


def gate1(r: Retrieval) -> Decision:
    """Cổng 1. THỨ TỰ KIỂM CÓ Ý NGHĨA: từ chối trước, hỏi lại sau."""
    if r.top1_abs < T1_ABS or r.ratio <= T1_RATIO:
        return Decision(action="refuse", message=refusal_message(r), retrieval=r)

    if len(r.hits) >= 2:
        first, second = r.hits[0], r.hits[1]
        if second.bm25 >= AMBIG_BAND * first.bm25 and first.session != second.session:
            return Decision(action="clarify", message=_clarify_message(r), retrieval=r)

    return Decision(action="pass", message="", retrieval=r)
