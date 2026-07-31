# Hướng dẫn phần bắt buộc do con người làm

## 1. `gold-ideas.csv`

Mỗi buổi đúng 3 dòng. Người đọc transcript tự chọn ý mà học viên nghỉ buổi
bắt buộc phải nắm.

- `gold_idea`: một ý đầy đủ, không lấy output AI.
- `accepted_chunk_ids`: một hoặc nhiều mã, cách nhau bằng dấu cách.
- `required_keywords`: 3–5 cụm từ, cách nhau bằng `|`.
- `reviewer`: tên người gán nhãn.
- `approved`: điền `yes`.

Ví dụ hình thức, không phải nhãn thật:

```text
T03 | T03-GOLD-01 | <ý do người đọc viết> | T03-034 T03-035 |
tool calling|function|intent | Nguyễn Văn A | yes
```

## 2. `case-approval.csv`

Đọc từng input và expected status/notes:

- Đồng ý: điền `approved=yes` và tên reviewer.
- Không đồng ý: để `approved=no`, ghi cách sửa vào `review_note`.

Không sửa trực tiếp expected để làm kết quả model pass.

## 3. `technical-baseline.csv`

Mỗi dòng là một claim của sổ tay:

- `supports_claim=yes` nếu đoạn trích thực sự chứng minh claim.
- `reverses_meaning=yes` nếu claim đảo hoặc làm sai ý nguồn.
- `reviewer`: phải là người ngoài nhóm.

Sau khi điền, chạy lại technical baseline để harness nhập kết quả.

