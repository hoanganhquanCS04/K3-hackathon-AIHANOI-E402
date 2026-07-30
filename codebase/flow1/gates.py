"""Cổng 1 — từ chối cứng và hỏi lại khi mơ hồ đa buổi. Chủ: M2 (khối E).

Cổng 0 (phân loại ý định) SỐNG Ở NƠI KHÁC: `stubs.route()`. Dự án chỉ có một
bộ phân loại ý định — xem `.superpowers/sdd/2026-07-30-luong-1-tra-cuu-tu-choi/
amendment.md` mục C2. File này KHÔNG chứa gate0, TEMPLATES hay classify_rule,
và không import `flow1.prompts`.

Cổng 1 là CODE THUẦN, không bao giờ gọi model. "Từ chối khi thiếu căn cứ" phải
là một tính chất của hệ thống, không phải một câu nhờ vả trong prompt — có test
kiểm rằng thân hàm gate1 không chứa lời gọi nào.

RÀNG BUỘC KIẾN TRÚC: module này KHÔNG import `flow1.retrieve`. Giao diện của
luồng 1 mở một buổi tại một thời điểm, nên cổng 1 chấm điểm trong phạm vi buổi
đang mở (Retrieval được truyền vào đã bị lọc theo buổi từ trước, ở lời gọi
`retrieve(query, session=...)`). Khi cổng 1 chặn, tầng điều phối (task sau) có
thể dò thêm cả 6 buổi để lấy heading làm giàu câu từ chối — đó là I/O, không
thuộc lớp code thuần này. `refusal_message()` nhận sẵn kết quả dò rộng đó qua
tham số `all_sessions` (một `Retrieval` đã có, không tự đi lấy).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from flow1.models import Retrieval
from flow1.thresholds import AMBIG_BAND, T1_ABS, T1_RATIO


@dataclass(frozen=True)
class Decision:
    """Kết luận của cổng 1."""

    action: Literal["pass", "refuse", "clarify"]
    message: str          # rỗng khi action == "pass"
    retrieval: Retrieval


def nearest_headings(r: Retrieval, n: int = 3) -> list[str]:
    """`n` heading gần nhất, dạng "Buổi 03 › RAG và tool calling", đã dedupe.

    Lúc từ chối ta ĐÃ có 5 hit trong tay — dùng chúng để câu từ chối mang thông
    tin thay vì thành ngõ cụt.
    """
    seen: dict[str, None] = {}
    for hit in r.hits:
        seen.setdefault(f"Buổi {hit.session} › {hit.section_title}", None)
        if len(seen) == n:
            break
    return list(seen)


def _first_other_session_heading(
    wide: Retrieval, exclude: set[str]
) -> tuple[str, str] | None:
    """Hit đầu tiên của `wide` mà buổi KHÔNG nằm trong `exclude`, đã dedupe.

    Dùng để làm giàu câu từ chối bằng dò rộng: chỉ báo buổi khác khi nó THỰC SỰ
    khác buổi đang mở, tránh nói "buổi khác" về chính buổi đang xét.
    """
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
    """Câu từ chối của cổng 1, có thể làm giàu bằng kết quả dò rộng.

    `all_sessions` là một `Retrieval` thứ hai, dò trên cả 6 buổi (không lọc theo
    buổi đang mở) — CHỈ dùng để lấy heading, không đổi quyết định từ chối. Mặc
    định `None` giữ nguyên hành vi gốc: chỉ liệt kê 3 heading gần nhất trong
    phạm vi `r` (đã lọc theo buổi đang mở).

    Có `all_sessions` và nó chứa một heading ở buổi KHÁC buổi trong `r` → ghép
    thêm một câu nói rõ đó là buổi khác, kiểu: "Buổi 05 › Đánh giá chất lượng
    đầu ra có nói tới nội dung này (một buổi khác)."
    """
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
    """Cổng 1. THỨ TỰ KIỂM CÓ Ý NGHĨA: từ chối trước, hỏi lại sau.

    Điểm thấp mà lại đi hỏi lại "buổi nào" là bắt người dùng tốn thêm một lượt cho
    một câu mình vốn không có căn cứ trả lời ở buổi nào cả.
    """
    if r.top1_abs < T1_ABS or r.ratio < T1_RATIO:
        return Decision(action="refuse", message=refusal_message(r), retrieval=r)

    if len(r.hits) >= 2:
        first, second = r.hits[0], r.hits[1]
        if second.bm25 >= AMBIG_BAND * first.bm25 and first.session != second.session:
            return Decision(action="clarify", message=_clarify_message(r), retrieval=r)

    return Decision(action="pass", message="", retrieval=r)
