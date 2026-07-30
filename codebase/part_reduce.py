"""Bước gộp cấp PHẦN — tổng hợp các mục của một phần thành một bản tóm tắt.

Vì sao file này tồn tại: "phần" là khái niệm của giao diện, không phải của
summarizer. Summarizer làm việc ở hai mức — mục (section) và buổi (session) —
nên không có chỗ nào gộp ở giữa. Trước khi có file này, "tóm phần 2" chỉ NỐI
key_points của từng mục lại với nhau: phần 2 mục ra 7 ý rời, phần 4 mục ra ~15 ý.
Đó là ghép, không phải tóm tắt, và người đọc nhìn ra ngay.

Cùng luật với bước gộp cả buổi, không đẻ luật mới:

- Chỉ đọc bản tóm tắt mục, KHÔNG đọc lại transcript gốc.
- Không được tạo mã trích dẫn mới; citation phải nằm trong citation của các mục.
- Citation kiểm bằng code qua `clean_cited_items` của validator, không bằng LLM.
- Có cache riêng, khoá gồm nội dung + phiên bản prompt + tên model.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from summarizer.cache import SummaryCache, cache_key
from summarizer.llm import StructuredLLM
from summarizer.schemas import CitedItem, CitedItemDraft, SectionSummary
from summarizer.validator import ValidationReport, clean_cited_items

PART_PROMPT_VERSION = "p1"


class PartPointDraft(BaseModel):
    text: str = Field(description="Một ý của phần, 1–2 câu.")
    citations: list[str] = Field(
        description="Mã đoạn dạng TXX-NNN, lấy lại từ phần tóm tắt mục bên dưới."
    )


class PartSummaryDraft(BaseModel):
    abstract: str = Field(
        description="2–3 câu nêu phần này bàn chuyện gì và đi tới đâu."
    )
    key_points: list[PartPointDraft] = Field(
        description="3–5 ý tổng hợp cho CẢ PHẦN."
    )


@dataclass
class PartResult:
    abstract: str
    key_points: tuple[CitedItem, ...]
    cache_hit: bool
    report: ValidationReport


PART_SYSTEM = """\
Bạn gộp các bản tóm tắt mục thành bản tóm tắt của MỘT PHẦN trong buổi học. Bạn \
KHÔNG được đọc transcript gốc, nên không thêm bất cứ chi tiết nào ngoài phần \
được cung cấp.

Quy tắc bắt buộc:

1. `key_points`: 3–5 ý cho CẢ PHẦN. Đây là bước TỔNG HỢP, không phải bước chép \
lại. Một chủ đề được bàn ở nhiều mục thì phải GỘP thành MỘT ý, kèm đủ mã trích \
dẫn của các mục liên quan. Nếu bạn trả về đúng bằng số ý của các mục cộng lại \
thì bạn đang chép chứ không tổng hợp.
2. Ưu tiên ý xuyên suốt cả phần hơn chi tiết lẻ của một mục. Ý chỉ xuất hiện ở \
một mục mà không nối với mạch chung thì bỏ được.
3. `abstract`: 2–3 câu nêu mạch của phần — đi từ đâu đến đâu, không phải danh \
sách chủ đề.
4. Không tạo mã trích dẫn mới. Chỉ dùng lại mã đã xuất hiện bên dưới.
5. Mỗi ý viết 1–2 câu, nêu được nội dung và lý do/hệ quả. Tránh câu rỗng kiểu \
"phần này nói về chủ đề X".
6. Ngôn ngữ: tiếng Việt, văn phong trung tính, không mở bài, không tự xưng.\
"""


def _format(summary: SectionSummary) -> str:
    lines = [
        f"### MỤC {summary.section_order} — {summary.section_title}",
        f"Tóm tắt: {summary.abstract}",
    ]
    for point in summary.key_points:
        lines.append(f"- {point.text} [{', '.join(point.citations)}]")
    for example in summary.examples:
        lines.append(f"- (ví dụ) {example.text} [{', '.join(example.citations)}]")
    for question in summary.student_questions:
        lines.append(f"- (học viên) {question.text} [{', '.join(question.citations)}]")
    if summary.concepts:
        lines.append(f"Khái niệm: {', '.join(summary.concepts)}")
    return "\n".join(lines)


def build_part_user(
    *,
    part_title: str,
    part_index: int,
    total_parts: int,
    summaries: tuple[SectionSummary, ...],
) -> str:
    ordered = sorted(summaries, key=lambda item: item.section_order)
    body = "\n\n".join(_format(summary) for summary in ordered)
    return (
        f"PHẦN {part_index}/{total_parts}: {part_title}\n"
        f"SỐ MỤC TRONG PHẦN: {len(ordered)}\n\n"
        f"TÓM TẮT TỪNG MỤC:\n\n{body}"
    )


def summarize_part_sections(
    *,
    part_title: str,
    part_index: int,
    total_parts: int,
    session_id: str,
    summaries: tuple[SectionSummary, ...],
    llm: StructuredLLM,
    cache: SummaryCache,
    model: str,
    temperature: float = 0.3,
    force: bool = False,
) -> PartResult:
    ordered = tuple(sorted(summaries, key=lambda item: item.section_order))
    key = cache_key(
        "part",
        *[summary.content_hash for summary in ordered],
        PART_PROMPT_VERSION,
        model,
    )

    if not force:
        cached = cache.get(key)
        if cached is not None:
            return PartResult(
                abstract=cached["abstract"],
                key_points=tuple(CitedItem(**item) for item in cached["key_points"]),
                cache_hit=True,
                report=ValidationReport(),
            )

    draft = llm.parse(
        model=model,
        system=PART_SYSTEM,
        user=build_part_user(
            part_title=part_title,
            part_index=part_index,
            total_parts=total_parts,
            summaries=ordered,
        ),
        schema=PartSummaryDraft,
        temperature=temperature,
    )

    report = ValidationReport()
    allowed = frozenset(
        citation for summary in ordered for citation in summary.covered_chunk_ids
    )
    points = clean_cited_items(
        [CitedItemDraft(text=p.text, citations=p.citations) for p in draft.key_points],
        allowed=allowed,
        session_id=session_id,
        label=f"{session_id}.part{part_index}",
        report=report,
    )

    # Không còn ý nào trụ lại sau khi lọc citation thì thà quay về các ý của mục
    # — chúng đã được kiểm chứng ở bước map — còn hơn hiện một phần rỗng.
    if not points:
        report.warnings.append(
            f"Phần {part_index}: bước gộp không còn ý hợp lệ, đã dùng lại ý của từng mục"
        )
        points = tuple(item for summary in ordered for item in summary.key_points)

    abstract = draft.abstract.strip() or " ".join(s.abstract for s in ordered)

    cache.put(
        key,
        {
            "abstract": abstract,
            "key_points": [item.model_dump(mode="json") for item in points],
        },
    )
    return PartResult(
        abstract=abstract,
        key_points=points,
        cache_hit=False,
        report=report,
    )
