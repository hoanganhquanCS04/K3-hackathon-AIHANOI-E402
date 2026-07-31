# Nhãn AI đề xuất cho 40 mẫu evidence

> Đây là bản pre-label để người phụ trách M3 kiểm tra nhanh, **không phải human
> review chính thức**. Các cột `human_*` trong `review-samples.csv` vẫn được để
> trống. Sau khi con người xác nhận, mới chuyển nhãn vào file chính thức.

## Quy ước

- `summary=yes`: học viên yêu cầu tóm tắt, khái quát hoặc nêu ý chính.
- `whole=yes`: phạm vi là cả buổi, cả bài, toàn bộ slide/tài liệu hoặc toàn bộ
  các khái niệm của buổi.
- `failure=yes`: tutor nói không tìm thấy, không truy cập được hoặc không đủ
  nội dung để thực hiện yêu cầu.

## Bảng đề xuất

| # | turn_id | summary | whole | failure | Lý do ngắn |
|---:|---|:---:|:---:|:---:|---|
| 1 | `T0224` | yes | yes | yes | Xin tóm nội dung chính của cả bài; tutor nói không thấy nội dung tổng quát. |
| 2 | `T0039` | yes | yes | no | Xin tóm buổi học; tutor đã đưa ra bản tóm tắt. |
| 3 | `T0542` | yes | yes | yes | Xin tóm toàn bộ slide; tutor nói không thể truy xuất toàn bộ. |
| 4 | `T0607` | yes | yes | yes | Xin tóm bài học; tutor nói không tìm thấy bản tóm tắt tổng quát. |
| 5 | `T1202` | yes | yes | yes | Xin các đầu kiến thức của cả bài giảng; tutor không tìm thấy. |
| 6 | `T0730` | yes | yes | yes | Xin tóm lại bài giảng; tutor không tìm thấy tài liệu tổng quát. |
| 7 | `T1054` | yes | yes | no | Xin tóm bài học và checkpoint; tutor đã trả nội dung. |
| 8 | `T0236` | yes | yes | no | Xin tóm toàn bộ tài liệu; tutor đã tóm tắt. |
| 9 | `T0213` | yes | yes | yes | Xin tóm tất cả slide; tutor nói không thể tổng hợp toàn bộ. |
| 10 | `T0170` | yes | yes | yes | Xin tóm tất cả nội dung buổi học; tutor không truy xuất được. |
| 11 | `T0649` | yes | no | yes | Xin tóm một slide cụ thể; tutor không tìm thấy slide đó. |
| 12 | `T1119` | yes | yes | yes | Xin tóm cả bài giảng; tutor không truy xuất được bản tổng thể. |
| 13 | `T1024` | yes | yes | no | Xin tóm bài hôm nay; tutor đã trả bản tóm tắt. |
| 14 | `T0603` | yes | yes | yes | Xin tóm toàn bộ slide; tutor nói không tìm thấy nội dung. |
| 15 | `T0737` | yes | no | yes | Xin ba ý chính của một slide; tutor nói không tìm thấy. |
| 16 | `T0789` | yes | yes | yes | Xin kiến thức cốt lõi của toàn tài liệu; tutor không tìm thấy nguồn. |
| 17 | `T0379` | yes | yes | yes | “summary this lecture”; tutor không tìm thấy tóm tắt tổng quát. |
| 18 | `T0973` | no | no | no | Nội dung về cách mở PDF, không phải yêu cầu tóm tắt; tutor trả hướng dẫn. |
| 19 | `T0345` | yes | yes | yes | Xin tóm slide của cả Day 4; tutor nói chưa có bản tóm tắt ngày học. |
| 20 | `T0385` | yes | no | yes | Xin ý chính của một slide; tutor không truy cập được nội dung slide. |
| 21 | `T0458` | no | no | yes | Hỏi nội dung slide 9, không yêu cầu tóm tắt; tutor không tìm thấy slide. |
| 22 | `T1095` | no | no | no | Yêu cầu giải thích đoạn bôi đen; tutor giải thích đầy đủ. |
| 23 | `T0035` | no | no | yes | Yêu cầu giải thích một thuật ngữ; tutor nói tài liệu không có thuật ngữ. |
| 24 | `T0384` | yes | no | yes | Xin tóm một slide; tutor không tìm thấy trang và chuyển sang nội dung khác. |
| 25 | `T0673` | no | no | yes | Truy vấn một khái niệm cụ thể; tutor nói không tìm thấy trong tài liệu. |
| 26 | `T0120` | yes | yes | yes | Xin khái quát toàn bộ các khái niệm Day 01; tutor không tìm thấy nguồn tổng hợp. |
| 27 | `T0831` | no | no | yes | Hỏi “React là gì”; tutor nói tài liệu không có nội dung đó. |
| 28 | `T0196` | no | no | no | Xin một ví dụ; tutor đưa ví dụ cụ thể. |
| 29 | `T0092` | no | no | yes | Đầu vào là danh sách chủ đề, không nói rõ xin tóm; tutor không tìm thấy tài liệu Day 04. |
| 30 | `T0953` | no | no | yes | Xin nói sâu hơn về một trang; tutor không tìm thấy trang. |
| 31 | `T0848` | no | no | no | Hỏi ba kiểu hệ thống AI; tutor trả lời trực tiếp. |
| 32 | `T1075` | no | no | no | Yêu cầu giải thích đoạn về feedback signal; tutor giải thích đầy đủ. |
| 33 | `T0163` | no | no | no | Hỏi nghĩa bốn chiến lược prompting; tutor trả lời trực tiếp. |
| 34 | `T0981` | no | no | no | Truy vấn “AI agent”; tutor giải thích khái niệm. |
| 35 | `T0147` | no | no | no | Yêu cầu giải thích Transformer; tutor trả lời. |
| 36 | `T1008` | no | no | no | Đầu vào là bài tập xác định bốn thành phần prompt; tutor giải thích. |
| 37 | `T0198` | no | no | no | Hỏi cách xác định bài toán kinh doanh cho AI; tutor trả lời. |
| 38 | `T0022` | no | no | no | Hỏi vị trí tài liệu giảng viên; tutor hướng dẫn. |
| 39 | `T0269` | no | no | no | Yêu cầu giải thích đoạn Key Takeaways; tutor giải thích, không phải yêu cầu tự tóm cả buổi. |
| 40 | `T0300` | no | no | no | Hỏi phân biệt ImageNet và kiến trúc sâu; tutor trả lời trực tiếp. |

## Các dòng nên được con người xem kỹ hơn

Ba dòng có yếu tố diễn giải nên cần ưu tiên xác nhận:

1. `T0345`: “slide day 4” được hiểu là phạm vi toàn bộ tài liệu Day 4, nên
   `whole=yes`.
2. `T0120`: “khái quát lại các khái niệm” được hiểu là toàn bộ các khái niệm
   của Day 01, nên `summary=yes`, `whole=yes`.
3. `T0092`: đầu vào chỉ liệt kê ba chủ đề, không có động từ yêu cầu tóm tắt,
   nên đề xuất `summary=no`, dù tutor diễn giải nó như một yêu cầu tổng hợp.

## Tổng nhãn đề xuất

- `summary=yes`: 21/40.
- `whole=yes`: 17/40.
- `failure=yes`: 23/40.

