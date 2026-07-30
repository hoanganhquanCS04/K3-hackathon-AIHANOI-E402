"""Ba chỗ sẽ được thay bằng logic thật. Giao diện KHÔNG cần sửa khi thay.

    route()          ← 1 LLM call rẻ, phân loại ý định + trích slot   (canvas §5 CỔNG 0)
    summarize_part() ← MAP call: nạp đoạn của 1 phần → JSON ý + mã đoạn
    answer_query()   ← luồng 1: BM25 → 4 cổng từ chối → generate

Hiện tại cả ba đều GIẢ LẬP:
  · mục lục, mã đoạn, câu nguyên văn, các con số   → THẬT (đọc từ outline.json)
  · nội dung câu tóm tắt / câu trả lời             → GIẢ, là chỗ trống có hình dạng đúng

Cố ý để chỗ trống nhìn rõ là chỗ trống. Đừng làm nó "nghe hay" — demo mà giám khảo
tưởng AI đã chạy trong khi chưa chạy thì hỏng nặng hơn là chưa có gì.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "outline.json"


# ─────────────────────────────────────────────────────────────────────────────
# Tầng dữ liệu (thật)
# ─────────────────────────────────────────────────────────────────────────────


def load_outline() -> list[dict]:
    if not FIXTURE.exists():
        raise FileNotFoundError(
            f"Chưa có {FIXTURE.name}. Chạy: python codebase/tools/build_outline.py"
        )
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["sessions"]


def get_session(sessions: list[dict], sid: str) -> dict | None:
    return next((s for s in sessions if s["id"] == sid), None)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER  — TODO: thay bằng 1 LLM call trả JSON {intent, part_ref, ...}
# ─────────────────────────────────────────────────────────────────────────────

_ORDINALS = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5, "sáu": 6,
    "nhất": 1, "đầu": 1, "đầu tiên": 1,
}

_RE_PART = re.compile(r"ph[ầâ]n\s+([ivx]+|\d+|một|hai|ba|bốn|năm|sáu|đầu tiên|đầu|nhất)", re.I)

_LOGISTICS = ("deadline", "nộp bài", "hạn nộp", "link zoom", "điểm số", "lịch học", "đáp án")
_OUT_OF_SCOPE = ("gpt", "claude", "gemini", "bạn là ai", "model nào", "pretrain")
_GREETING = ("xin chào", "hello", "hi ", "chào bạn")


def route(query: str, state: dict) -> dict:
    """Phân loại ý định. Ở bản thật đây là LLM call; ở đây là rule.

    Điểm quan trọng giữ nguyên khi thay: router CHỈ trả `part_ref` THÔ.
    Việc quy `part_ref` thành số phần là của resolve_part() — CODE, không phải LLM.
    """
    q = query.lower().strip()

    if any(k in q for k in _LOGISTICS):
        return {"intent": "logistics", "part_ref": None}
    if any(k in q for k in _OUT_OF_SCOPE):
        return {"intent": "ngoai_pham_vi", "part_ref": None}
    if any(q.startswith(k.strip()) for k in _GREETING):
        return {"intent": "chao_hoi", "part_ref": None}

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
        # "tóm tắt cho tôi" — thiếu slot phần → phải HỎI LẠI, không được đoán  [lớp ②]
        return {"intent": "tom_tat_thieu_slot", "part_ref": None}
    if m:
        return {"intent": "tom_tat_phan", "part_ref": m.group(1)}

    return {"intent": "tra_cuu", "part_ref": None}


def resolve_part(part_ref: str | None, session: dict, done: dict) -> tuple[int | None, str]:
    """Quy số thứ tự thành số phần — CODE THUẦN, đối chiếu mục lục đang hiển thị.

    Không để LLM làm bước này: router "hiểu" phần II thành phần 3 thì bản tóm đúng
    hình thức nhưng sai nội dung, và người đọc không có cách nào biết.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# LUỒNG 2  — TODO: thay bằng MAP call (nạp segments của phần → JSON ý)
# ─────────────────────────────────────────────────────────────────────────────


def summarize_part(session: dict, part_idx: int) -> dict:
    """Trả về cấu trúc ĐÚNG NHƯ bản thật sẽ trả. Chỉ `claim` là chỗ trống."""
    part = session["parts"][part_idx - 1]

    # Non-goal #2: phần chủ yếu là hoạt động lớp thì KHÔNG tóm, nhưng vẫn nói ra
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
            "claim": None,  # ← LLM sinh ở đây
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
    """REDUCE: gộp các phần ĐÃ tóm thành sổ tay 1 trang.

    Luật giữ nguyên ở bản thật: model chỉ được CHỌN và SẮP LẠI claim đã có,
    không được viết claim mới → mã đoạn tự động đúng.
    """
    picked = [kp for i in sorted(done) for kp in done[i]["key_points"]]
    return {
        "session": session,
        "n_parts_done": len(done),
        "n_parts_total": len(session["parts"]),
        "key_points": picked[:5],
        "student_points": [kp for kp in picked if kp["has_student_speech"]],
        "gaps": [g for i in sorted(done) for g in done[i].get("gaps", [])],
    }


# ─────────────────────────────────────────────────────────────────────────────
# LUỒNG 1  — TODO: thay bằng BM25 retrieve + 4 cổng từ chối + generate
# ─────────────────────────────────────────────────────────────────────────────


def answer_query(session: dict, query: str) -> dict:
    """Giả lập luồng tra cứu. Bản thật: retrieve top-5 → cổng T1 → generate → validator."""
    quotes = [q for p in session["parts"] for q in p["quotes"]]
    hits = quotes[:2]
    return {
        "status": "answered",
        "claims": [{"claim": None, "cite": [q["seg_id"]], "quote": q["text"]} for q in hits],
        "note": "Bản thật: BM25 top-5 → nếu điểm top-1 dưới ngưỡng T1 thì TỪ CHỐI CỨNG, "
        "không gọi generate.",
    }


def refusal(intent: str, session: dict | None = None) -> str:
    """Ba intent không được retrieve, không được generate (canvas §5, lớp ③)."""
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
