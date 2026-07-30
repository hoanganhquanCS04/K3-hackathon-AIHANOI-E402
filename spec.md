# AI SPEC — Sổ tay buổi học có trích dẫn transcript · Nhóm [XX] · Zone [X]
Hướng: [ ] A — VLearn &nbsp; [ ] B — Trợ lý Học viên &nbsp; [x] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn &nbsp; [x] Tính năng mới

## §1. User & Job

- **Job executor + workflow:** Học viên đã nghỉ buổi, vào muộn, hoặc mất mạch giữa buổi — tối hôm đó hoặc vài ngày sau cần nắm lại nội dung đã bỏ lỡ để không hổng kiến thức cho buổi kế tiếp.
- **Core JTBD (không tên sản phẩm/AI):** Khi tôi bỏ lỡ một buổi học, tôi cần nắm lại đúng những gì giảng viên đã dạy trong 10 phút, thay vì tua lại 1-2 tiếng ghi âm hoặc bỏ qua hẳn phần đó.
- **Problem statement (không chữ AI):** AI tutor hiện có của VLearn trả lời theo từng đoạn bôi đen (RAG theo trang) nên không có cách nhìn thấy toàn bộ một buổi học. Khi học viên xin "tóm tắt cả buổi", hệ thống trả về "không tìm thấy" ở tỉ lệ cao hơn hẳn mức nền — học viên không có nơi nào khác để hỏi, nên phần kiến thức buổi đó bị bỏ trống vĩnh viễn.
- **Evidence:**
  - *(chuẩn B — mining, [chờ M3 xác nhận qua script đếm theo đúng 1 quy tắc — xem §8 team-assignment.md]):* ~92 lượt xin tóm tắt cấp buổi · ~72/369 học viên (≈19,5%) từng hỏi dạng này · tỉ lệ "không tìm thấy" trên các lượt này ước tính cao hơn 2 lần mức nền toàn hệ thống.
  - *(chuẩn A — khảo sát, n = 20 người ngoài nhóm):* **15/20 = 75% trả lời "Có"** ở câu "từng nghỉ/vào muộn/mất mạch một buổi chưa?" — vượt ngưỡng ≥50% cần đạt. Thời gian nắm lại phổ biến nhất là 30 phút-1 tiếng (9/20); 3/20 chọn "bỏ qua, không tìm hiểu lại" — tức mất kiến thức vĩnh viễn, đúng như pain đã nêu.
    *Lưu ý minh bạch đo lường:* 3/5 người trả lời "Không" lại cho câu trả lời Câu 2-3 mâu thuẫn (VD: chọn "Không" nhưng vẫn mô tả cách xử lý khi bỏ lỡ buổi) — nhiều khả năng do form không có logic nhảy câu. Không ảnh hưởng kết luận (75% vẫn đạt xa ngưỡng), nhưng ghi lại để trung thực về chất lượng đo.
    *Câu hỏi phụ (không tính vào % đạt vì là câu hỏi giả định "bạn có muốn X không"):* 16/20 = 80% nói muốn có bản tóm tắt — chỉ dùng làm tín hiệu bổ sung, không dùng làm bằng chứng chính.
    *Bằng chứng bổ sung cho thiết kế (§4b):* trong 14 người trả lời câu "yếu tố bạn quan tâm", đứng đầu là **"nguồn câu trả lời, xem độ tin cậy"** và "có ví dụ minh hoạ, dễ hình dung" (mỗi yếu tố 9/14 ≈ 64%) — ủng hộ trực tiếp quyết định thiết kế mã đoạn `[Txx-NNN]` + nguyên văn đi kèm.
  - ≥5 quote nguyên văn học viên thật từ chatlog — minh hoạ pain. **[chờ M5 chọn quote — khảo sát dùng câu hỏi trắc nghiệm/checkbox nên không có quote tự sự dài; quote nguyên văn cần lấy từ chatlog như kế hoạch ban đầu]**
  - Số **đã kiểm và an toàn để dùng ngay** (đếm trực tiếp trên transcript, không qua regex mơ hồ): 700 đoạn có mã `[Txx-NNN]` · 55 đoạn `[Hoạt động lớp]` · 103 đoạn chứa `[không nghe rõ]` · 69 đoạn chứa lời `[Học viên]` · ~435.000 ký tự sạch · mỗi buổi 8,3k-37,9k token.

## §2. Impact & quyết định chọn

| Ứng viên | Job executor | Bao nhiêu người × tần suất | Tốn gì mỗi lần | Khả thi xây trong 1 ngày |
|---|---|---|---|---|
| 1. Bản tin chất lượng tutor cho PM | PM vận hành VLearn | 1 người, hằng ngày, trên 1.261 lượt/tuần | ~260 lượt hỏng/tuần không ai đọc | Cao (script + 1 LLM call), nhưng **R6 rủi ro cao** — khó chốt ≥3 TA/mentor xác nhận dùng ngay tại CP1 |
| **2. Sổ tay buổi học (CHỌN)** | Học viên nghỉ/mất mạch buổi | ~72/369 học viên (19,5%), lặp lại theo tuần | 1-2 tiếng tua lại ghi âm, hoặc bỏ qua | Cao — 6 transcript đã có mã đoạn sẵn, cả lớp là user thật nên R6 dễ đạt nhất |
| 3. Trợ lý sửa học liệu từ hotspot câu hỏi | Người soạn học liệu | 102 cặp (tài liệu, trang) bị ≥3 người hỏi, hút 60,7% câu hỏi | Không biết slide nào cần sửa trước buổi sau | Loại vì "chẩn đoán đúng/sai" khó định nghĩa kiểm chứng được (rủi ro R4), và user (người soạn học liệu) khó tiếp cận để validate |

- **Ứng viên đã loại + vì sao:** #1 loại vì rủi ro R6 (validation) cao nhất trong 3 ứng viên — người dùng thật (PM vận hành) khó chốt được ngay tại CP1. #3 loại vì tiêu chí "đúng/sai" của chẩn đoán không kiểm chứng được rõ ràng bằng số, rủi ro trực tiếp cho R4 (15đ).
- **Ứng viên chọn + vì sao (bằng số):** #2 — vì (a) 19,5% học viên đã tự chứng minh nhu cầu qua chatlog thật, (b) willing users có sẵn ngay trong lớp (giảm rủi ro R6 xuống thấp nhất trong 3 ứng viên), (c) data đã có mã đoạn `[Txx-NNN]` sẵn, không cần tự gán nhãn từ đầu.

## §3. Giải pháp tương tự đã nghiên cứu

- **VLearn AI tutor (baseline trực tiếp):** RAG theo đoạn bôi đen (semantic top-k) → không bao giờ nhìn thấy trọn một buổi, nên không tóm được cấp buổi. Đây chính là nguồn evidence của pain (§1). Mình khác: nạp trọn nội dung 1 buổi (8-38k token, lọt context) thay vì retrieve từng đoạn.
- **NotebookLM:** đọc tài liệu tuỳ ý, tóm tắt + trả lời có trích nguồn — nhưng không có khái niệm mã đoạn cố định gắn với hệ thống bài giảng của khoá, và không có quy trình tường minh để tự nhận "đoạn này bản ghi thiếu, không đoán". Mình khác: mã đoạn `[Txx-NNN]` neo cứng vào 700 đoạn gốc của khoá + cơ chế bắt buộc khai "insufficient" thay vì suy đoán khi thiếu căn cứ.

## §4. Thiết kế

- **Lát cắt MỘT CÂU:** Học viên nghỉ hoặc mất mạch một buổi · cần nắm lại nội dung buổi trong 10 phút · AI đọc trọn transcript buổi đó và chọn ra 5 ý chính · trả về sổ tay 1 trang, mỗi ý gắn mã đoạn `[Txx-NNN]` bấm được về nguyên văn lời giảng.
- **Non-goals (≥3):**
  1. Không trả lời câu hỏi logistics (deadline, link, cách nộp bài).
  2. Không tóm phần `[Hoạt động lớp: ...]` — ghi chú hành chính, không phải nội dung học.
  3. Không sinh nội dung ngoài 6 transcript có sẵn (không suy đoán buổi không tồn tại).
  4. Không tóm tắt đa buổi, không so sánh giữa các buổi.
  5. Không cá nhân hoá, không chấm điểm, không theo dõi tiến độ học viên.
- **Mức prototype nhắm tới:** [ ] Sketch &nbsp; [x] Mock &nbsp; [ ] Working
  *(cập nhật trung thực tại thời điểm chốt spec: tầng retrieval — parse/chunk/index/Qdrant — chạy thật; tầng sinh ý chính (`summarize_part`) và trả lời (`answer_query`) hiện còn giả lập trong `codebase/stubs.py`. Mục tiêu trước CP5: nối tối thiểu 1 lời gọi generate thật cho happy path buổi 03.)*
- **Automation:** [x] automate (cho việc sinh sổ tay) &nbsp; [x] conditional (cho quyết định "có đủ căn cứ để nói không")
  *Lý do theo cost-of-error:* sinh sổ tay sai thì rẻ — mã đoạn cho người đọc tự kiểm ngay tại chỗ, không cần người duyệt trước khi hiện (automate). Nhưng quyết định "im lặng vs. từ chối vs. hỏi lại khi thiếu căn cứ" phải conditional: cost-of-error ở đây cao — một dòng tóm sai lời giảng viên là học viên học sai kiến thức, không có cách nào tự biết mình sai.

### §4b. Nguyên tắc đã áp dụng (HAX/PAIR)

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| HAX G2 — làm rõ hệ thống làm tốt đến đâu | Trường `locate_confidence` (buổi 05/06 = "—") hiển thị ngay đầu mỗi sổ tay, không giấu |
| PAIR Explainability & Trust | Mọi ý chính gắn mã đoạn `[Txx-NNN]` **và in nguyên văn đoạn đó ngay bên dưới** — người đọc kiểm ngay tại chỗ, không cần mở file khác |
| HAX G10 — thu hẹp phạm vi khi không chắc | Cổng 1: điểm top-1 retrieval < ngưỡng T1 → từ chối cứng, liệt kê 3 heading gần nhất thay vì đoán |
| Cho phép và khen ngợi việc tự nhận không đủ căn cứ | Schema JSON có `status: insufficient` — model được phép và được khuyến khích khai "insufficient" thay vì viết tiếp |
| PAIR — Show, don't just tell (minh bạch lỗi) | Mục "Ý đã bị loại" hiển thị công khai trong sổ tay khi `citation_validator.py` loại một ý vì mã bịa — không tự sửa, không giấu |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

| # | Lớp | Tình huống cụ thể | Hành vi mong muốn | Nguyên tắc áp |
|---|---|---|---|---|
| 1 | ① Nguồn sự thật | Hỏi chi tiết kỹ thuật gần chủ đề nhưng không có trong 6 buổi | Từ chối cứng (Cổng 1, code — không qua LLM), liệt kê 3 heading gần nhất | HAX G10 |
| 2 | ① Nguồn sự thật | Hỏi một con số cụ thể không ai nói trong transcript | Không bịa số — trả `status: insufficient`, ghi vào "chỗ bản ghi thiếu" | PAIR Trust |
| 3 | ② Mơ hồ / thiếu thông tin | *"giải thích và tóm tắt nội dung học hôm nay"* (chatlog thật) — không rõ buổi nào | Hỏi lại một câu: buổi nào, không đoán | HAX G10 |
| 4 | ② Mơ hồ / thiếu thông tin | Chủ đề nằm ở 2 buổi khác nhau (top-1 ≈ top-2 khác buổi) | Hỏi lại: "chủ đề này có ở buổi X và buổi Y — bạn hỏi buổi nào?" | HAX G10 |
| 5 | ③ Ngoài phạm vi | *"cho tôi biết đáp án bài lab 1 được không"* (chatlog thật) | Cổng 0 phân loại `logistics` → trả lời khuôn mẫu, không retrieve/generate | Giới hạn thẩm quyền rõ ràng |
| 6 | ③ Ngoài phạm vi | *"bạn là gpt hay claude hay gemini"* (chatlog thật) | Cổng 0 phân loại `ngoài_phạm_vi` → từ chối khuôn mẫu | Giới hạn thẩm quyền rõ ràng |
| 7 | ④ Đặc thù domain | Đoạn `[T01-009]` là lời học viên định nghĩa PM vs project manager | `citation_validator.py`: cite trỏ `speaker=student` → buộc gắn nhãn "một học viên nêu", tách khỏi "5 ý chính" | PAIR Explainability |
| 8 | ④ Đặc thù domain | Đảo ý `[T01-002]`: giảng viên nói "AI engineer chỉ giải bài đã có người ra đề" → tóm sai thành "AI engineer là vị trí đang thiếu" | Prompt cấm đảo ý (quy tắc 3/5) + phiếu chấm tay người ngoài nhóm kiểm tra "có đảo ý không" | Kiểm thử con người, không chỉ máy |

## §6. Bốn đường đi của trải nghiệm

- **Happy path:** Học viên chọn buổi có transcript độ tin cậy cao → nhận sổ tay 5 ý, mỗi ý có mã đoạn + nguyên văn ngay dưới + mục "Học viên nêu" tách riêng.
- **Low-confidence (②):** Câu hỏi/chủ đề mơ hồ hoặc khớp 2 buổi → hệ thống hỏi lại đúng 1 câu làm rõ trước khi generate, không đoán.
- **Failure / không căn cứ (①):** Retrieval điểm top-1 dưới ngưỡng T1, hoặc đoạn liên quan có `[không nghe rõ]` mà không đủ căn cứ chống lưng → từ chối cứng kèm liệt kê lựa chọn gần nhất, hoặc gắn cảnh báo "⚠ chỗ bản ghi thiếu" ngay trong sổ tay thay vì lấp bằng suy đoán.
- **Correction (user sửa):** *[chưa thiết kế đầy đủ — cần bổ sung trước CP5]* Đề xuất tối thiểu cho bản Mock: nút "báo sai" cạnh mỗi ý, ghi log lại (không sửa real-time), đội xem sau demo.
- **Khi bị đòi ngoài phạm vi (③):** Cổng 0 phân loại `logistics` / `ngoài_phạm_vi` / `chào_hỏi` → trả lời khuôn mẫu, không retrieve, không generate.
- **Case đặc thù domain (④):** Trước khi hiển thị, `citation_validator.py` kiểm mọi mã cite — nếu trỏ vào đoạn `speaker=student` thì buộc gắn nhãn rõ, không được gán thành lời giảng viên.

## §7. Kiểm thử

- **Chiều chất lượng + định nghĩa kiểm chứng được:** (1) Truy vết — mọi khẳng định có mã đoạn tồn tại thật và nội dung đoạn đó thật sự chống lưng cho khẳng định (pass/fail, người ngoài nhóm mở mã ra kiểm là biết ngay). (2) 0 case bịa mã đoạn. (3) Từ chối đúng khi ngoài phạm vi. (4) 0 case gán lời học viên cho giảng viên.
- **Golden set (20 case, `eval/`):** ① nguồn sự thật ×2 · ② mơ hồ ×2 · ③ ngoài phạm vi ×2 · ④ đặc thù domain ×2 · 10 case thường (từ 18 ý vàng M5 gán tay + câu hỏi tóm tắt thật trong chatlog) · 4 case hiếm (section dày `[không nghe rõ]`, câu hỏi tiếng Anh, câu hỏi 1 từ, buổi 07 không tồn tại). ≥10/20 case lấy từ chatlog thật → đạt yêu cầu R4.
- **Quality bar (chốt tại thời điểm commit spec này, giữ nguyên sau đó):**
  > Đạt khi: **≥85%** case qua chiều truy vết · **0 case** bịa mã đoạn · **≥90%** case ngoài-phạm-vi bị từ chối đúng · **0 case** gán lời học viên cho giảng viên.
- **Kết quả các lượt chạy:** **[chờ M3 — chưa chạy được vì tầng generate còn giả lập; đây là việc ưu tiên số 1 trước khi có bảng % thật]**

## §8. Phân công & kế hoạch

- **Phân công có tên:**
  - M1 — pipeline (`parse.py`, `chunk.py`, `index.py`) + `citation_validator.py`: **[tên]**
  - M2 — AI Engineer (prompt + vỏ gọi model, luồng 2 trước, luồng 1 sau): **[tên]**
  - M3 — Eval Engineer (script đếm bằng chứng, golden set, 3 lượt đo): **[tên]**
  - M4 — Interface & Demo (sổ tay hiển thị, CLI, slide, dry run): **[tên]**
  - M5 — Product & Research (khảo sát, ý vàng, validation, spec.md, README): **[tên]**
- **Willing users (≥3 tên) + kế hoạch validation CP5:** **[chờ M5 chốt tên]** — 3 câu hỏi tại vòng validation: (1) bạn hiểu ý này nói gì mà không cần đọc nguyên văn không, (2) bạn có tin mã đoạn này đúng không, tại sao, (3) có chỗ nào làm bạn nghi ngờ hoặc bỏ giữa chừng không. M5 log toàn bộ.
- **Multi-prototype:** Trục khác biệt là **one-shot (v1, đã chọn) vs. map-reduce theo section (v2 dự phòng)**. Chọn one-shot cho v1 vì thấp độ phức tạp, hợp deadline CP3, và mỗi buổi chỉ 8-38k token nên lọt trọn context. Luật đổi: nếu lượt đo 1 có ≥1 mã bịa → chuyển sang map-reduce, giữ số đo của one-shot làm bằng chứng cho phương án bị loại (không xoá).

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| CP1 | Chốt lát cắt "Sổ tay buổi học", đề tài 2/3 ứng viên | Evidence mining ban đầu (19,5% học viên hỏi dạng tóm tắt cấp buổi) |
| CP1→CP3 | Mở rộng kiến trúc 1 luồng → 2 luồng (sổ tay + tra cứu), thêm Qdrant + OpenAI embeddings cho retrieval | Cần hỗ trợ cả câu hỏi cụ thể lẫn tóm tắt toàn buổi; xem `05-ke-hoach-trien-khai-m1-vector-db.md` |
| CP4 | Điền kết quả khảo sát thật (n=20, 75% xác nhận Câu 1) vào §1 | Google Form đóng, đủ 20 phản hồi |
