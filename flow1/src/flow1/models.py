"""Kiểu dữ liệu của luồng 1. Không logic — logic nằm ở các module khác.

QUAN TRỌNG — duck-typing với luồng 2: `Seg` mang đúng 4 tên attribute mà
`sotay.verify` đọc (`code`, `text`, `has_gap`, `is_activity`), nên bộ kiểm mã
trích dẫn của M1 chạy được trên `Seg` mà KHÔNG cần sửa dòng nào. Đổi tên bốn
field đó là phá hợp đồng dùng chung — đừng đổi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Seg:
    """Một đoạn giảng có mã trích dẫn. Đơn vị nguyên tử — không bao giờ cắt nhỏ hơn."""

    code: str                 # "T03-014" — tên `code` để duck-type với sotay.models.Segment
    session: str              # "03"
    session_title: str
    locate_confidence: str    # "cao" | "vừa" | "—"
    section_idx: int          # 1-based
    section_title: str
    order: int                # thứ tự trong buổi, 1-based
    text: str
    speaker: Literal["instructor", "student"]   # 69 đoạn "student"; xem parse.py
    has_gap: bool             # chứa "[không nghe rõ]"  (tên `has_gap`, không phải has_unclear)
    is_activity: bool         # là ghi chú "[Hoạt động lớp: ...]"
    n_chars: int


@dataclass(frozen=True)
class Chunk:
    """Đơn vị đưa vào index. Gộp 1..n đoạn LIỀN KỀ trong CÙNG section."""

    chunk_id: str
    session: str
    session_title: str
    section_idx: int
    section_title: str
    parts: list[tuple[str, str]]   # [(mã đoạn GỐC, nguyên văn)] — thứ tự như trong buổi
    has_gap: bool

    @property
    def seg_codes(self) -> list[str]:
        """Mã đoạn gốc, đã dedupe, giữ thứ tự. Cổng 3 dùng để kiểm `cite ∈ context`."""
        seen: dict[str, None] = {}
        for code, _ in self.parts:
            seen.setdefault(code, None)
        return list(seen)

    @property
    def text(self) -> str:
        """Nguyên văn thuần — dùng để INDEX. Không có mã đoạn lẫn vào."""
        return "\n\n".join(t for _, t in self.parts)

    @property
    def labelled(self) -> str:
        """Nguyên văn có gắn mã — dùng để đưa vào PROMPT, để model trích dẫn được."""
        return "\n\n".join(f"[{c}] {t}" for c, t in self.parts)

    @property
    def index_text(self) -> str:
        """Prefix heading là BẮT BUỘC: 23% đoạn dưới 300 ký tự, đứng một mình
        không đủ ngữ cảnh để match."""
        return f"{self.session_title} › {self.section_title}\n{self.text}"

    @property
    def n_chars(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class Hit:
    """Một chunk đã được retrieve, kèm điểm."""

    chunk: Chunk
    bm25: float
    emb: float | None    # None khi chưa bật embedding
    rank: int            # 0-based, theo `score`
    score: float         # điểm dùng để SẮP THỨ TỰ (RRF nếu có emb, BM25 nếu không)

    @property
    def session(self) -> str:
        return self.chunk.session

    @property
    def section_title(self) -> str:
        return self.chunk.section_title


@dataclass(frozen=True)
class Retrieval:
    """Kết quả retrieve. Mang sẵn mọi thứ cổng 1 cần, để cổng 1 không tự tính lại.

    top1_abs và ratio LUÔN tính trên điểm BM25 thô, KHÔNG BAO GIỜ trên điểm đã
    fuse. Điểm RRF là 1/(K+rank) — một dãy gần như cố định (1/61, 1/62, ...) nên
    ratio sau fuse luôn ≈ 1,02 bất kể câu hỏi là gì. Nhờ tính trên BM25 mà một
    lần hiệu chỉnh T1 dùng được cho cả chế độ bật và tắt embedding.
    """

    hits: list[Hit]
    top1_abs: float
    ratio: float

    @property
    def sessions(self) -> list[str]:
        return [h.session for h in self.hits]


class Intent(BaseModel):
    """Output cổng 0."""

    label: Literal["nội_dung_khoá", "logistics", "ngoài_phạm_vi", "chào_hỏi"] = Field(
        description="Loại ý định của câu hỏi."
    )
    reason: str = Field(description="Một câu ngắn giải thích vì sao chọn nhãn đó.")


class Claim(BaseModel):
    """Một khẳng định trong câu trả lời, kèm mã đoạn chống lưng."""

    text: str = Field(description="Khẳng định, viết thành một câu tiếng Việt hoàn chỉnh.")
    cite: list[str] = Field(description="Mã đoạn chống lưng, dạng T03-014. Tối thiểu 1 mã.")
    speaker: Literal["instructor", "student"] = Field(
        description="instructor nếu đoạn là lời giảng viên, student nếu là lời học viên."
    )


class Answer(BaseModel):
    """Output cổng 2."""

    status: Literal["answered", "insufficient", "out_of_scope"] = Field(
        description="answered khi các đoạn được cung cấp trả lời được câu hỏi; "
        "insufficient khi chúng không đủ căn cứ; out_of_scope khi câu hỏi không "
        "thuộc nội dung khoá."
    )
    claims: list[Claim] = Field(description="Rỗng khi status khác answered.")
    gaps: list[str] = Field(description="Mã đoạn có [không nghe rõ] mà bạn đã dùng.")


@dataclass(frozen=True)
class Drop:
    """Một claim bị cổng 3 loại. Ghi lại, không bao giờ tự sửa."""

    claim_text: str
    kind: str      # unknown_code | outside_context | no_codes
    detail: str


@dataclass(frozen=True)
class Verdict:
    """Output cổng 3."""

    status: Literal["answered", "insufficient", "out_of_scope"]
    claims: list[Claim] = field(default_factory=list)         # chỉ claim đã qua kiểm
    drops: list[Drop] = field(default_factory=list)
    student_codes: list[str] = field(default_factory=list)     # speaker=student → buộc gắn nhãn
    gap_codes: list[str] = field(default_factory=list)          # has_gap → chèn cảnh báo
