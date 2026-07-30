"""Prompt cho bước map và bước reduce.

`PROMPT_VERSION` nằm trong khoá cache. Sửa bất kỳ chuỗi nào trong file này thì
phải tăng version, nếu không build sẽ trả lại kết quả cũ.
"""

from __future__ import annotations

from summarizer.schemas import Chunk, SectionRef, SectionSummary, SessionRef

# Hai version TÁCH RIÊNG vì hai bước có cache riêng. Sửa prompt của bước gộp mà
# dùng chung một version thì toàn bộ ~120 bản tóm tắt mục đang nằm trong cache
# cũng bị coi là hết hạn, và phải gọi lại LLM cho mọi mục — trả tiền cho một thay
# đổi không liên quan tới chúng.
PROMPT_VERSION = "v2"          # bước MAP (tóm từng mục)
REDUCE_PROMPT_VERSION = "v3"   # bước REDUCE (gộp cả buổi)

SPEAKER_LABELS = {
    "instructor": "giảng viên",
    "student": "học viên",
    "teaching_assistant": "trợ giảng",
    "guest": "khách mời",
    "activity": "hoạt động lớp",
}


MAP_SYSTEM = """\
Bạn TỔNG HỢP nội dung một mục trong bài giảng tiếng Việt. Người đọc đã vắng buổi \
học và muốn nắm mạch lập luận, không muốn đọc lại lời thoại.

Điều quan trọng nhất — GỘP, ĐỪNG CHÉP:

Transcript được cắt thành nhiều đoạn nhỏ chỉ vì lý do kỹ thuật. Một luận điểm \
của giảng viên thường trải dài qua nhiều đoạn liên tiếp: nêu vấn đề ở đoạn này, \
giải thích ở đoạn sau, cho ví dụ ở đoạn sau nữa. Nhiệm vụ của bạn là nhận ra \
chúng thuộc CÙNG MỘT Ý và gộp lại thành một câu, rồi ghi ĐỦ mã của mọi đoạn đã \
gộp.

SAI (chép lại từng đoạn, mỗi ý một mã, mã chạy tuần tự):
  - Kỹ năng xác định bài toán rất quan trọng. [T01-001]
  - Nhiều công ty tuyển AI engineer nhưng thiếu người ra đề bài. [T01-002]
  - 70% thành công đến từ con người và vận hành. [T01-003]

ĐÚNG (gộp thành luận điểm, nhiều mã trên một ý):
  - Nút thắt khi doanh nghiệp ứng dụng AI không nằm ở công nghệ mà ở khâu xác \
định bài toán: nhiều nơi tuyển được AI engineer nhưng không có ai ra được đề bài \
cụ thể, và khoảng 70% yếu tố thành công đến từ con người cùng quy trình vận hành. \
[T01-001, T01-002, T01-003]

Quy tắc bắt buộc:

1. Chỉ dùng thông tin có trong đoạn transcript được cung cấp. Không thêm kiến \
thức bên ngoài, không suy rộng.
2. Mỗi ý trong `key_points`, `examples`, `student_questions` phải kèm mã trích \
dẫn dạng TXX-NNN, và mã đó phải xuất hiện nguyên văn trong phần transcript bên \
dưới. Tuyệt đối không tạo mã mới.
3. `key_points`: TỐI ĐA 5 ý, và phải ÍT HƠN HẲN số đoạn của mục. Mục có 12 đoạn \
thì khoảng 3–4 ý là hợp lý. Thà ít ý mà mỗi ý là một luận điểm hoàn chỉnh, còn \
hơn nhiều ý vụn.
4. Phần lớn các ý phải có TỪ 2 MÃ TRÍCH DẪN TRỞ LÊN. Nếu gần như mọi ý của bạn \
chỉ có đúng một mã, và các mã chạy liên tiếp theo thứ tự đoạn, thì bạn đang chép \
chứ không tổng hợp — hãy gộp lại.
5. Mỗi ý viết 1–2 câu, nêu được nội dung và lý do/hệ quả, không chỉ nhắc chủ đề. \
Tránh câu rỗng kiểu "giảng viên nói về chủ đề này".
6. Đoạn nào không mang nội dung học (chào hỏi, nhắc giờ nghỉ, điểm danh, loay \
hoay kỹ thuật) thì bỏ hẳn, không cần ép vào ý nào.
7. Phân biệt rõ người nói. Lời giảng viên và lời học viên không được trộn. Câu \
hỏi hoặc ý kiến do học viên nêu phải nằm ở `student_questions`, không nằm ở \
`key_points`.
8. Gặp `[không nghe rõ]` thì bỏ qua phần đó, không đoán nội dung bị mất.
9. `abstract`: 1–2 câu nêu mục này bàn chuyện gì và đi đến đâu.
10. `concepts`: các thuật ngữ hoặc khái niệm được nhắc tới, viết như trong bài.
11. `examples`: ví dụ, case, con số cụ thể được nêu. Không có thì để mảng rỗng.
12. Ngôn ngữ: tiếng Việt, văn phong trung tính, không tự xưng, không mở bài.\
"""


REDUCE_SYSTEM = """\
Bạn tổng hợp bản tóm tắt một buổi học từ các bản tóm tắt của từng mục. Bạn KHÔNG \
được đọc transcript gốc, nên không được thêm bất cứ chi tiết nào ngoài phần \
được cung cấp.

Quy tắc bắt buộc:

1. `outline` phải liệt kê ĐỦ và ĐÚNG THỨ TỰ mọi mục được cung cấp. Không gộp \
mục, không bỏ mục, không đổi thứ tự. Mỗi phần tử gồm `section_id` đúng như đã \
cho, một `abstract` 1–2 câu, và các citation lấy từ chính mục đó.
2. `key_points`: 5–8 ý cho CẢ BUỔI. Đây là bước tổng hợp xuyên suốt, không phải \
bước chọn lọc. Một chủ đề được bàn ở nhiều mục khác nhau thì phải GỘP thành MỘT \
ý duy nhất, kèm đủ mã trích dẫn của tất cả các mục liên quan. Chép lại nguyên si \
một ý từ một mục là làm sai — trừ khi ý đó thật sự chỉ xuất hiện ở đúng mục ấy. \
Ưu tiên những ý xuyên suốt buổi hơn là chi tiết lẻ của một mục.
3. `tldr`: 2–3 câu nêu buổi học đi từ đâu đến đâu — mạch chính, không phải danh \
sách chủ đề. Phải phản ánh cả những mục ở giữa và cuối buổi, không chỉ mục đầu.
4. Không tạo mã trích dẫn mới. Chỉ dùng lại mã đã xuất hiện trong phần tóm tắt \
mục bên dưới.
5. `open_questions`: những câu hỏi còn để ngỏ hoặc do học viên nêu mà buổi học \
chưa chốt. Không có thì để mảng rỗng.
6. Ngôn ngữ: tiếng Việt, văn phong trung tính.
7. Nếu có phần DÀN Ý THAM KHẢO ở cuối: đó là danh sách khái niệm và câu hỏi rút \
từ knowledge graph, dùng để bạn GỌI TÊN khái niệm cho nhất quán và để biết ý nào \
là ý xuyên suốt đáng đưa lên. Nó KHÔNG phải nguồn nội dung. Không được lấy bất kỳ \
thông tin nào chỉ có ở đó mà không có trong phần tóm tắt mục, và không được trích \
dẫn nó. Dàn ý mâu thuẫn với tóm tắt mục thì tin tóm tắt mục.\
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
    outline_hint: str = "",
) -> str:
    """`outline_hint` là dàn ý rút từ knowledge graph, có thể rỗng.

    Đặt SAU phần tóm tắt mục là có chủ đích: phần cuối prompt được model chú ý
    nhiều hơn, nhưng ở đây ta muốn ngược lại — tóm tắt mục mới là nguồn, dàn ý
    chỉ là gợi ý. Nên nó vừa đứng cuối vừa được đánh dấu rõ là không phải nguồn,
    và quy tắc 7 của REDUCE_SYSTEM nói thẳng điều đó.
    """

    ordered = sorted(section_summaries, key=lambda item: item.section_order)
    body = "\n\n".join(_format_section_summary(summary) for summary in ordered)
    ids = ", ".join(summary.section_id for summary in ordered)
    prompt = (
        f"BUỔI: {session.session_locator}\n"
        f"SỐ MỤC: {len(ordered)}\n"
        f"DANH SÁCH section_id BẮT BUỘC CÓ ĐỦ TRONG outline: {ids}\n\n"
        f"TÓM TẮT TỪNG MỤC:\n\n{body}"
    )
    if outline_hint.strip():
        prompt += (
            "\n\n---\n"
            "DÀN Ý THAM KHẢO (từ knowledge graph — KHÔNG phải nguồn nội dung, "
            "không được trích dẫn, không được lấy thông tin chỉ có ở đây):\n\n"
            f"{outline_hint.strip()}"
        )
    return prompt
