"""CỔNG 0 — router LLM. Thay cho `route()` bằng regex trong `stubs.py`.

Trả về ĐÚNG bộ tên intent mà `app.py` đang switch, cộng thêm một trường `source`.
Nhờ vậy giao diện không phải sửa một dòng nào — đúng lời hứa ở đầu `stubs.py`:
"Ba chỗ sẽ được thay bằng logic thật. Giao diện KHÔNG cần sửa khi thay."

Hai bất biến giữ nguyên từ bản rule, và chúng quan trọng hơn việc dùng LLM:

1. Router chỉ trả `part_ref` THÔ ("hai", "II", "tiếp"). Việc quy nó thành số phần
   vẫn là của `resolve_part()` — CODE, đối chiếu mục lục đang hiển thị. Để LLM tự
   quy thì nó "hiểu" phần II thành phần 3, bản tóm đúng hình thức nhưng sai nội
   dung, và người đọc không có cách nào biết.
2. Ba intent từ chối không được đi tiếp xuống bước đọc dữ liệu hay gọi model.

Router hỏng thì KHÔNG được làm chết cả app: `route()` tự lùi về bản regex cũ.
Mất một chút thông minh còn hơn demo đứng hình vì rate limit.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel, Field
from stubs import route as rule_route
from summarizer.llm import OpenAIStructuredLLM

logger = logging.getLogger(__name__)

# Router chạy MỌI lượt chat nên phải rẻ và nhanh; nó chỉ phân loại, không viết văn.
ROUTER_MODEL = "gpt-5-mini-2025-08-07"
ROUTER_TEMPERATURE = 0.0

Intent = Literal[
    "logistics",
    "ngoai_pham_vi",
    "chao_hoi",
    "xem_muc_luc",
    "tom_tat_phan",
    "tom_tat_buoi",
    "tom_tat_thieu_slot",
    "tra_cuu",
]

class RouterDecision(BaseModel):
    """Không dùng field optional có default: structured output ở chế độ strict đòi
    mọi field đều required. Chuỗi rỗng nghĩa là "không có"."""

    intent: Intent = Field(description="Loại ý định của câu hỏi")
    part_ref: str = Field(
        description="Số phần THÔ đúng như người dùng viết: 'hai', 'II', '2', "
        "'tiếp'. Rỗng nếu câu hỏi không nhắc tới phần nào."
    )
    use_graph_outline: bool = Field(
        description="true nếu nên lấy thêm dàn ý khái niệm từ knowledge graph."
    )
    reason: str = Field(description="Một câu ngắn giải thích vì sao chọn như vậy.")


ROUTER_SYSTEM = """\
Bạn là bộ định tuyến của một trợ lý tóm tắt bài giảng. Bạn KHÔNG trả lời câu hỏi \
và KHÔNG tóm tắt gì cả — chỉ phân loại. Đầu ra phải là JSON đúng schema.

CHỌN `intent`:

- `chao_hoi` — chỉ chào, không hỏi gì.
- `logistics` — hỏi deadline, cách nộp bài, link zoom, điểm số, lịch học, đáp án \
bài lab. Đây là việc hành chính, trợ lý không trả lời.
- `ngoai_pham_vi` — hỏi về chính trợ lý (bạn là ai, bạn dùng model nào) hoặc chủ \
đề không liên quan tới nội dung buổi học.
- `xem_muc_luc` — hỏi buổi này có mấy phần, gồm những gì, học gì.
- `tom_tat_phan` — muốn TÓM TẮT và CÓ nói rõ phần nào: "tóm phần 2", "tóm tắt \
phần II", "phần tiếp theo", "cho tôi phần 3".
- `tom_tat_buoi` — muốn tóm cả buổi / toàn buổi / sổ tay / tất cả các phần.
- `tom_tat_thieu_slot` — muốn tóm tắt nhưng KHÔNG nói phần nào, cũng không nói cả \
buổi. VD "tóm tắt cho tôi đi". Phải hỏi lại, không được đoán là phần 1.
- `tra_cuu` — hỏi về nội dung đã giảng mà không phải yêu cầu tóm tắt. VD "giảng \
viên nói gì về X", "X là gì".

`part_ref`: chép NGUYÊN VĂN cách người dùng gọi phần đó, ĐỪNG quy đổi sang số. \
"phần II" → "II". "phần tiếp theo" → "tiếp". Không nhắc tới phần → "".

CHỌN `use_graph_outline`:

Nội dung buổi học LUÔN được đọc đầy đủ từ vector DB — đó không phải việc bạn \
quyết. Bạn chỉ quyết có lấy THÊM một dàn ý khái niệm từ knowledge graph để bước \
gộp gọi tên khái niệm cho nhất quán hay không.

- `true` khi người dùng muốn bản tổng hợp cả buổi, hoặc câu hỏi nhắc tới khái \
niệm / chủ đề / quan hệ giữa các ý: "tóm cả buổi", "sổ tay buổi này", "buổi này \
có những khái niệm gì", "các ý liên quan nhau thế nào".
- `false` khi chỉ tóm một phần cụ thể ("tóm phần 2"), hoặc intent không phải tóm \
tắt. Dàn ý cả buổi không giúp gì cho một phần lẻ, chỉ làm loãng prompt.\
"""


_PART_WORD = re.compile(r"^\s*(?:ph[ầâ]n|m[ụu]c|part)\s+", re.IGNORECASE)
_NEXT_WORD = re.compile(r"(?:k[ếe]\s*)?ti[ếê]p(?:\s*theo)?|sau|n[ữu]a", re.IGNORECASE)


def _normalize_part_ref(raw: str) -> str:
    """Đưa `part_ref` về đúng bộ chuỗi mà `resolve_part()` tra được.

    `resolve_part()` tra bảng bằng đúng chuỗi: "phần 2" và "tiếp theo" đều rơi
    thẳng vào nhánh "không hiểu", và người dùng bị hỏi lại dù đã nói rõ phần nào.
    Chuẩn hoá ở đây bằng regex chứ không phải bằng cách dặn model kỹ hơn — model
    có thể quên, regex thì không.

    Vẫn KHÔNG quy "II" thành 2 ở đây. Việc đó là của `resolve_part()`, nơi có
    mục lục thật để đối chiếu số phần của buổi.
    """

    cleaned = _PART_WORD.sub("", raw).strip()
    if _NEXT_WORD.fullmatch(cleaned.strip()):
        return "tiếp"
    return cleaned


def _build_user(query: str, *, session_title: str, n_parts: int) -> str:
    return (
        f"BUỔI ĐANG MỞ: {session_title}\n"
        f"SỐ PHẦN CỦA BUỔI: {n_parts}\n\n"
        f"CÂU CỦA NGƯỜI DÙNG: {query}"
    )


_llm: OpenAIStructuredLLM | None = None
_last_reason = ""
_last_engine = ""


def last_route_info() -> tuple[str, str]:
    """(engine, reason) của lượt route gần nhất — để sidebar hiện router chạy thật."""

    return _last_engine, _last_reason


def route(query: str, state: dict, session: dict | None = None) -> dict:
    """Chữ ký tương thích `stubs.route(query, state)`; `session` là tuỳ chọn.

    Trả dict có đủ khoá cũ (`intent`, `part_ref`) nên `app.py` dùng được ngay.
    """

    global _llm, _last_reason, _last_engine

    if session is None:
        # Không có ngữ cảnh buổi thì router LLM không thêm được gì. Dùng rule.
        decision = rule_route(query, state)
        _last_engine, _last_reason = "rule", "không có ngữ cảnh buổi"
        return {**decision, "use_graph_outline": False}

    if _llm is None:
        _llm = OpenAIStructuredLLM()

    try:
        parsed = _llm.parse(
            model=ROUTER_MODEL,
            system=ROUTER_SYSTEM,
            user=_build_user(
                query,
                session_title=session["title"],
                n_parts=len(session["parts"]),
            ),
            schema=RouterDecision,
            temperature=ROUTER_TEMPERATURE,
        )
    except Exception as error:  # noqa: BLE001 — router hỏng không được làm chết app
        logger.warning("Router LLM hỏng (%s), lùi về rule", type(error).__name__)
        decision = rule_route(query, state)
        _last_engine = "rule (LLM lỗi)"
        _last_reason = f"{type(error).__name__}"
        return {**decision, "use_graph_outline": False}

    intent = parsed.intent
    part_ref = _normalize_part_ref(parsed.part_ref)

    # Nói "tóm tắt" mà không chỉ được phần nào thì phải hỏi lại, không đoán.
    if intent == "tom_tat_phan" and not part_ref:
        intent = "tom_tat_thieu_slot"

    _last_engine = ROUTER_MODEL
    _last_reason = parsed.reason.strip()

    return {
        "intent": intent,
        "part_ref": part_ref or None,
        # Dàn ý chỉ có nghĩa với bước gộp cả buổi. Model hay bật cả khi tóm một
        # phần, nên chặn ở đây thay vì tin hoàn toàn vào nó.
        "use_graph_outline": bool(parsed.use_graph_outline and intent == "tom_tat_buoi"),
        "reason": _last_reason,
    }
