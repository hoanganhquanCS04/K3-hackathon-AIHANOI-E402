"""Prompt cho bước map và bước reduce.

`PROMPT_VERSION` nằm trong khoá cache. Sửa bất kỳ chuỗi nào trong file này thì
phải tăng version, nếu không build sẽ trả lại kết quả cũ.
"""

from __future__ import annotations

from summarizer.schemas import Chunk, SectionRef, SectionSummary, SessionRef

PROMPT_VERSION = "v1"

SPEAKER_LABELS = {
    "instructor": "giảng viên",
    "student": "học viên",
    "teaching_assistant": "trợ giảng",
    "guest": "khách mời",
    "activity": "hoạt động lớp",
}


MAP_SYSTEM = """\
Bạn trích xuất nội dung từ transcript bài giảng tiếng Việt. Đây là tác vụ trích \
xuất, không phải viết lại hay bình luận.

Quy tắc bắt buộc:

1. Chỉ dùng thông tin có trong đoạn transcript được cung cấp. Không thêm kiến \
thức bên ngoài, không suy rộng.
2. Mỗi ý trong `key_points`, `examples`, `student_questions` phải kèm ít nhất \
một mã trích dẫn dạng TXX-NNN, và mã đó phải xuất hiện nguyên văn trong phần \
transcript bên dưới. Tuyệt đối không tạo mã mới.
3. Phân biệt rõ người nói. Lời của giảng viên và lời của học viên không được \
trộn. Câu hỏi hoặc ý kiến do học viên nêu phải nằm ở `student_questions`, \
không nằm ở `key_points`.
4. Gặp `[không nghe rõ]` thì bỏ qua phần đó, không đoán nội dung bị mất.
5. `abstract`: 1–2 câu nêu nội dung chính của mục.
6. `key_points`: 3–6 ý, mỗi ý một câu, cụ thể và kiểm chứng được từ transcript. \
Tránh câu chung chung kiểu "giảng viên nói về chủ đề này".
7. `concepts`: các thuật ngữ hoặc khái niệm được nhắc tới, viết như trong bài.
8. `examples`: ví dụ, case, con số cụ thể được nêu. Không có thì để mảng rỗng.
9. `student_questions`: câu hỏi hoặc phản hồi của học viên. Không có thì để \
mảng rỗng.
10. Ngôn ngữ: tiếng Việt, văn phong trung tính, không tự xưng, không mở bài.\
"""


REDUCE_SYSTEM = """\
Bạn tổng hợp bản tóm tắt một buổi học từ các bản tóm tắt của từng mục. Bạn KHÔNG \
được đọc transcript gốc, nên không được thêm bất cứ chi tiết nào ngoài phần \
được cung cấp.

Quy tắc bắt buộc:

1. `outline` phải liệt kê ĐỦ và ĐÚNG THỨ TỰ mọi mục được cung cấp. Không gộp \
mục, không bỏ mục, không đổi thứ tự. Mỗi phần tử gồm `section_id` đúng như đã \
cho, một `abstract` 1–2 câu, và các citation lấy từ chính mục đó.
2. `key_points`: chọn 5–8 ý quan trọng nhất của cả buổi. Mỗi ý phải ghi \
`section_id` của mục nguồn và giữ nguyên các mã trích dẫn TXX-NNN từ mục đó.
3. `tldr`: 2–3 câu nêu trọng tâm cả buổi. Phải phản ánh cả những mục ở giữa và \
cuối buổi, không chỉ mục đầu.
4. Không tạo mã trích dẫn mới. Chỉ dùng lại mã đã xuất hiện trong phần tóm tắt \
mục bên dưới.
5. `open_questions`: những câu hỏi còn để ngỏ hoặc do học viên nêu mà buổi học \
chưa chốt. Không có thì để mảng rỗng.
6. Ngôn ngữ: tiếng Việt, văn phong trung tính.\
"""


def format_chunk(chunk: Chunk) -> str:
    speaker = SPEAKER_LABELS.get(chunk.speaker_role, chunk.speaker_role)
    return f"[{chunk.chunk_id}] ({speaker}) {chunk.text}"


def build_map_user(
    *,
    session: SessionRef,
    section: SectionRef,
    chunks: tuple[Chunk, ...],
    total_sections: int,
) -> str:
    body = "\n\n".join(format_chunk(chunk) for chunk in chunks)
    return (
        f"BUỔI: {session.session_locator}\n"
        f"MỤC {section.section_order}/{total_sections}: {section.section_title}\n"
        f"MÃ TRÍCH DẪN HỢP LỆ: {', '.join(chunk.chunk_id for chunk in chunks)}\n\n"
        f"TRANSCRIPT:\n\n{body}"
    )


def _format_section_summary(summary: SectionSummary) -> str:
    lines = [
        f"### MỤC {summary.section_order} — {summary.section_title}",
        f"section_id: {summary.section_id}",
        f"Tóm tắt: {summary.abstract}",
    ]
    for point in summary.key_points:
        lines.append(f"- {point.text} [{', '.join(point.citations)}]")
    if summary.examples:
        for example in summary.examples:
            lines.append(f"- (ví dụ) {example.text} [{', '.join(example.citations)}]")
    if summary.student_questions:
        for question in summary.student_questions:
            lines.append(
                f"- (học viên) {question.text} [{', '.join(question.citations)}]"
            )
    if summary.concepts:
        lines.append(f"Khái niệm: {', '.join(summary.concepts)}")
    if summary.unclear_chunk_ids:
        lines.append(f"Lưu ý: {len(summary.unclear_chunk_ids)} đoạn không nghe rõ.")
    return "\n".join(lines)


def build_reduce_user(
    *,
    session: SessionRef,
    section_summaries: tuple[SectionSummary, ...],
) -> str:
    ordered = sorted(section_summaries, key=lambda item: item.section_order)
    body = "\n\n".join(_format_section_summary(summary) for summary in ordered)
    ids = ", ".join(summary.section_id for summary in ordered)
    return (
        f"BUỔI: {session.session_locator}\n"
        f"SỐ MỤC: {len(ordered)}\n"
        f"DANH SÁCH section_id BẮT BUỘC CÓ ĐỦ TRONG outline: {ids}\n\n"
        f"TÓM TẮT TỪNG MỤC:\n\n{body}"
    )
