"""Ba chỗ sẽ được thay bằng logic thật. Giao diện KHÔNG cần sửa khi thay.

    route()          ← 1 LLM call rẻ, phân loại ý định + trích slot   (canvas §5 CỔNG 0)
    summarize_part() ← MAP call: nạp đoạn của 1 phần → JSON ý + mã đoạn
    answer_query()   ← luồng 1: BM25 → 4 cổng từ chối → generate
"""

from __future__ import annotations

import json
import re
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "outline.json"
FALLBACK_FIXTURE = Path(__file__).parent.parent / "flow1" / "app" / "fixtures" / "outline.json"


def load_outline() -> list[dict]:
    if FIXTURE.exists():
        return json.loads(FIXTURE.read_text(encoding="utf-8"))["sessions"]
    if FALLBACK_FIXTURE.exists():
        return json.loads(FALLBACK_FIXTURE.read_text(encoding="utf-8"))["sessions"]
    return []


def get_session(sessions: list[dict], sid: str) -> dict | None:
    return next((s for s in sessions if s["id"] == sid), None)


_ORDINALS = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5, "sáu": 6,
    "nhất": 1, "đầu": 1, "đầu tiên": 1,
}

_RE_PART = re.compile(r"ph[ầâ]n\s+([ivx]+|\d+|một|hai|ba|bốn|năm|sáu|đầu tiên|đầu|nhất)", re.I)

_LOGISTICS = ("deadline", "nộp bài", "hạn nộp", "link zoom", "điểm số", "lịch học")

RULE_EVIDENCE: dict[str, tuple[str, ...]] = {
    "ngoai_pham_vi": (
        "T0733", "T0664", "T1237", "T0072", "T0790", "T0171", "T0407",
        "T0527", "T1241", "T0414", "T0928", "T0594", "T0537", "T0134",
        "T0148", "T0470", "T0874", "T0837",
    ),
    "chao_hoi": ("T0495", "T0327", "T0402", "T0438", "T0271", "T1104"),
    "logistics": (),
}

_RE_HIGHLIGHT_WRAPPER = re.compile(r"^\s*(giải thích|giai thich|tóm tắt|tom tat|dịch|dich)\b", re.I)

_RE_JAILBREAK = re.compile(
    r"bỏ qua (các )?(cảnh báo|ràng buộc|guardrail|giới hạn|quy tắc)"
    r"|ignore (all )?(previous|prior) instruction"
    r"|giả sử bạn là",
    re.I,
)

_BOT_SELF = r"(bạn|ban|\bb\b|you|your|tutor)"
_MODEL_WORD = r"(model|gpt|claude|gemini|chatgpt|pretrain)"
_RE_ASK_BOT_MODEL = re.compile(
    rf"{_BOT_SELF}[^.!?\n]{{0,40}}{_MODEL_WORD}|{_MODEL_WORD}[^.!?\n]{{0,40}}{_BOT_SELF}",
    re.I,
)

_RE_ASK_ANSWER = re.compile(
    r"(đáp án|dap an|lời giải|loi giai|solution)[^.!?\n]{0,40}(lab|bài tập|bai tap|quiz|assignment)"
    r"|(lab|bài tập|bai tap|quiz|assignment)[^.!?\n]{0,40}(đáp án|dap an|lời giải|loi giai|solution)",
    re.I,
)

_RE_GREETING_ONLY = re.compile(r"^\s*(xin chào|chào bạn|chào|hello|hi)\s*[!.,;]*\s*$", re.I)


def route(query: str, state: dict) -> dict:
    q = query.lower().strip()

    if q == "" or _RE_GREETING_ONLY.match(q):
        return {"intent": "chao_hoi", "part_ref": None}

    if _RE_JAILBREAK.search(q):
        return {"intent": "ngoai_pham_vi", "part_ref": None}

    if not _RE_HIGHLIGHT_WRAPPER.match(q):
        if _RE_ASK_BOT_MODEL.search(q):
            return {"intent": "ngoai_pham_vi", "part_ref": None}
        if _RE_ASK_ANSWER.search(q):
            return {"intent": "ngoai_pham_vi", "part_ref": None}

    if any(k in q for k in _LOGISTICS):
        return {"intent": "logistics", "part_ref": None}

    m = _RE_PART.search(q)
    is_summary = any(k in q for k in ("tóm", "tổng kết", "recap", "sổ tay"))

    if any(k in q for k in ("mấy phần", "bao nhiêu phần", "mục lục", "có những gì", "học gì", "gồm gì")):
        return {"intent": "xem_muc_luc", "part_ref": None}
    if is_summary and m:
        return {"intent": "tom_tat_phan", "part_ref": m.group(1)}
    if is_summary and any(k in q for k in ("tiếp", "phần sau", "kế tiếp")):
        return {"intent": "tom_tat_phan", "part_ref": "tiếp"}
    if is_summary and any(k in q for k in ("cả buổi", "toàn buổi", "sổ tay", "tất cả")):
        return {"intent": "tom_tat_buoi", "part_ref": None}
    if is_summary:
        return {"intent": "tom_tat_thieu_slot", "part_ref": None}
    if m:
        return {"intent": "tom_tat_phan", "part_ref": m.group(1)}

    return {"intent": "tra_cuu", "part_ref": None}


def resolve_part(part_ref: str | None, session: dict, done: dict) -> tuple[int | None, str]:
    n = len(session["parts"])
    if part_ref is None:
        return None, "thiếu số phần"
    if part_ref == "tiếp":
        nxt = max(done, default=0) + 1
        if nxt > n:
            return None, f"đã tóm hết {n} phần"
        return nxt, f"'tiếp' → phần {nxt}"

    idx = _ORDINALS.get(str(part_ref).lower())
    if idx is None:
        return None, f"không hiểu '{part_ref}'"
    if idx > n:
        return None, f"buổi này chỉ có {n} phần"
    return idx, f"'{part_ref}' → phần {idx}"


def summarize_part(session: dict, part_idx: int) -> dict:
    part = session["parts"][part_idx - 1]

    if part["activity_heavy"]:
        return {
            "part": part,
            "skipped": True,
            "reason": f"{part['n_activity']}/{part['n_segments']} đoạn là [Hoạt động lớp] "
            "— đây là ghi chú hành chính, không phải nội dung học.",
            "key_points": [],
        }

    key_points = [
        {
            "claim": None,
            "cite": [q["seg_id"]],
            "has_student_speech": q["has_student_speech"],
            "quote": q["text"],
        }
        for q in part["quotes"]
    ]
    return {
        "part": part,
        "skipped": False,
        "reason": None,
        "key_points": key_points,
        "gaps": [f"{part['n_unclear']} đoạn trong phần này có [không nghe rõ]"]
        if part["n_unclear"]
        else [],
    }


def build_recap(session: dict, done: dict) -> dict:
    picked = [kp for i in sorted(done) for kp in done[i]["key_points"]]
    return {
        "session": session,
        "n_parts_done": len(done),
        "n_parts_total": len(session["parts"]),
        "key_points": picked[:5],
        "student_points": [kp for kp in picked if kp["has_student_speech"]],
        "gaps": [g for i in sorted(done) for g in done[i].get("gaps", [])],
    }


def answer_query(session: dict, query: str) -> dict:
    quotes = [q for p in session["parts"] for q in p["quotes"]]
    hits = quotes[:2]
    return {
        "status": "answered",
        "claims": [{"claim": None, "cite": [q["seg_id"]], "quote": q["text"]} for q in hits],
        "note": "Bản thật: BM25 top-5 → nếu điểm top-1 dưới ngưỡng T1 thì TỪ CHỐI CỨNG, "
        "không gọi generate.",
    }


def refusal(intent: str, session: dict | None = None) -> str:
    if intent == "logistics":
        return (
            "Mình chỉ tóm nội dung học từ 6 buổi đã ghi. Câu hỏi về deadline, cách nộp bài "
            "hay đáp án bài lab thì mình không trả lời — hỏi trong kênh lớp sẽ đúng hơn."
        )
    if intent == "ngoai_pham_vi":
        return (
            "Câu này ngoài phạm vi của mình. Mình chỉ làm một việc: tóm nội dung 6 buổi "
            "học từ chính bản ghi của buổi đó."
        )
    if intent == "chao_hoi":
        n = len(session["parts"]) if session else 0
        return f"Chào bạn. Buổi này có {n} phần — bấm gợi ý bên dưới hoặc gõ “tóm phần 1”."
    return "Mình chưa hiểu ý bạn."
