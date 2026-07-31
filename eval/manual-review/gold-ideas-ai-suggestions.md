# 18 ý vàng đề xuất sau khi đọc transcript gốc

Trạng thái: **AI-assisted draft — chưa phải human gold chính thức**.

Tài liệu này là bản đọc hộ để M3 owner duyệt. Mỗi buổi có đúng 3 ý chính, được diễn đạt lại từ transcript gốc. `accepted_chunk_ids` là các đoạn bằng chứng được phép dùng khi đánh giá; `required_keywords` là 3–5 khái niệm dùng để kiểm tra ý tương đương, không bắt buộc câu trả lời phải giống nguyên văn.

## T01 — Xác định đúng bài toán trước khi chọn giải pháp

### T01-G01

- **Ý vàng:** Trước khi chọn công nghệ hoặc xây giải pháp AI, nhóm phải xác định đúng vấn đề thực tế cần giải quyết; công nghệ chỉ là phương tiện phục vụ vấn đề.
- **accepted_chunk_ids:** `T01-002`, `T01-004`, `T01-005`
- **required_keywords:** `đúng vấn đề`, `trước giải pháp`, `AI`, `nhu cầu thực tế`

### T01-G02

- **Ý vàng:** Double Diamond gồm hai vòng khám phá: phân kỳ rồi hội tụ để tìm đúng vấn đề, sau đó tiếp tục phân kỳ rồi hội tụ để tìm đúng giải pháp.
- **accepted_chunk_ids:** `T01-049`, `T01-069`
- **required_keywords:** `Double Diamond`, `phân kỳ`, `hội tụ`, `vấn đề`, `giải pháp`

### T01-G03

- **Ý vàng:** First Principles yêu cầu phân rã bài toán đến các nguyên lý nền tảng không thể rút gọn thêm và chủ động chất vấn những cách làm cũ.
- **accepted_chunk_ids:** `T01-062`, `T01-064`
- **required_keywords:** `First Principles`, `phân rã`, `nguyên lý nền tảng`, `chất vấn giả định`

## T02 — Đo giá trị và chọn mức tự động hóa

### T02-G01

- **Ý vàng:** Một problem statement tốt phải nêu người dùng mục tiêu, workflow hiện tại, điểm nghẽn và tác động, đồng thời định nghĩa thành công bằng đại lượng đo được như thời gian, khối lượng công việc hoặc chi phí.
- **accepted_chunk_ids:** `T02-015`, `T02-018`
- **required_keywords:** `problem statement`, `workflow`, `điểm nghẽn`, `tác động`, `đo lường`

### T02-G02

- **Ý vàng:** Metric chính phải phản ánh kết quả cuối mà sản phẩm tạo ra, không chỉ là vanity metric về lượt truy cập hay mức sử dụng; có thể dùng North Star metric cùng các chỉ số trung gian để kiểm chứng giả định.
- **accepted_chunk_ids:** `T02-024`, `T02-025`
- **required_keywords:** `North Star`, `kết quả`, `vanity metric`, `chỉ số trung gian`

### T02-G03

- **Ý vàng:** Chọn automation hay augmentation theo mức rủi ro và hậu quả; nên bắt đầu bằng AI hỗ trợ có con người giám sát rồi chỉ tăng dần tự động hóa khi hệ thống đã đủ tin cậy.
- **accepted_chunk_ids:** `T02-032`, `T02-033`, `T02-034`
- **required_keywords:** `automation`, `augmentation`, `rủi ro`, `con người giám sát`, `tăng dần`

## T03 — Thiết kế hệ thống AI có kiểm soát

### T03-G01

- **Ý vàng:** Những phần cần kết quả chắc chắn phải dùng công thức, code hoặc tool mang tính deterministic; chỉ giao cho LLM các phần cần xử lý ngôn ngữ hoặc linh hoạt vì đầu ra LLM mang tính xác suất.
- **accepted_chunk_ids:** `T03-074`, `T03-078`, `T03-079`
- **required_keywords:** `deterministic`, `công thức`, `tool`, `LLM xác suất`, `tách nhiệm vụ`

### T03-G02

- **Ý vàng:** Với hành động có hậu quả thật, hệ thống cần guardrail hoặc lớp an toàn cứng có quyền chặn đầu ra LLM và cần human-in-the-loop trước khi thực thi.
- **accepted_chunk_ids:** `T03-080`, `T03-088`, `T03-130`
- **required_keywords:** `guardrail`, `lớp an toàn`, `hậu quả`, `human-in-the-loop`, `phê duyệt`

### T03-G03

- **Ý vàng:** Đánh giá hệ thống AI phải bao phủ các tổ hợp lỗi, tình huống đối nghịch và lỗi hệ thống, không chỉ kiểm thử happy path.
- **accepted_chunk_ids:** `T03-142`, `T03-143`
- **required_keywords:** `kiểm thử`, `tổ hợp lỗi`, `đối nghịch`, `lỗi hệ thống`, `happy path`

## T04 — Nền tảng LLM và cách lựa chọn mô hình

### T04-G01

- **Ý vàng:** LLM hiện đại dựa trên Transformer và sinh văn bản bằng cách dự đoán token tiếp theo; để dùng hiệu quả trong sản phẩm thật còn cần các lớp tool, context và hệ thống bao quanh mô hình.
- **accepted_chunk_ids:** `T04-091`
- **required_keywords:** `Transformer`, `token tiếp theo`, `tool`, `context`, `lớp hệ thống`

### T04-G02

- **Ý vàng:** Quản lý sự chú ý và context của mô hình là năng lực cốt lõi: cần chủ động lưu các quyết định quan trọng, kiểm soát việc compact/tóm tắt và tránh kéo dài context gây giảm hiệu năng, tăng chi phí.
- **accepted_chunk_ids:** `T04-057`, `T04-088`
- **required_keywords:** `context`, `sự chú ý`, `tóm tắt`, `hiệu năng`, `chi phí`

### T04-G03

- **Ý vàng:** Không chọn model chỉ theo leaderboard; phải hiểu bài toán, thử nghiệm trên công việc thực tế và dùng model rẻ cho việc đơn giản, model suy luận mạnh cho việc khó.
- **accepted_chunk_ids:** `T04-084`, `T04-085`, `T04-091`
- **required_keywords:** `chọn model`, `bài toán`, `thử nghiệm`, `chi phí`, `suy luận`

## T05 — Scoping, kiến trúc và đánh giá sản phẩm AI

### T05-G01

- **Ý vàng:** Trước khi code, nhóm cần quyết định có nên xây sản phẩm hay không bằng một problem statement gồm actor, workflow hiện tại, bottleneck, impact đo được, success measurement và giới hạn vận hành.
- **accepted_chunk_ids:** `T05-003`, `T05-005`, `T05-145`
- **required_keywords:** `problem statement`, `workflow`, `bottleneck`, `impact`, `success measurement`

### T05-G02

- **Ý vàng:** Chọn mức giải pháp đơn giản nhất phù hợp: script cho logic ổn định, LLM feature cho đầu vào biến đổi và đầu ra linh hoạt, agent cho quy trình nhiều bước có tool và trạng thái thay đổi.
- **accepted_chunk_ids:** `T05-137`, `T05-138`, `T05-139`
- **required_keywords:** `script`, `LLM feature`, `agent`, `nhiều bước`, `tool`

### T05-G03

- **Ý vàng:** Builder sản phẩm AI không chỉ biết build mà phải biết eval, phát hiện hallucination, thiết lập metric, monitoring, guardrail và human review.
- **accepted_chunk_ids:** `T05-086`, `T05-138`, `T05-147`
- **required_keywords:** `eval`, `hallucination`, `metric`, `guardrail`, `human review`

## T06 — Cơ chế Transformer, hallucination và huấn luyện LLM

### T06-G01

- **Ý vàng:** Transformer biến token thành vector rồi dùng self-attention để mỗi token xem các token khác trong ngữ cảnh và xử lý song song trước khi dự đoán token kế tiếp.
- **accepted_chunk_ids:** `T06-126`, `T06-127`, `T06-132`
- **required_keywords:** `Transformer`, `vector`, `self-attention`, `ngữ cảnh`, `xử lý song song`

### T06-G02

- **Ý vàng:** LLM dự đoán token theo xác suất chứ không hiểu ngôn ngữ như con người, nên không thể đúng 100%; bias trong dữ liệu và quá trình fine-tuning vẫn có thể gây hallucination.
- **accepted_chunk_ids:** `T06-136`, `T06-138`, `T06-139`
- **required_keywords:** `xác suất`, `token`, `bias`, `hallucination`, `không đúng 100%`

### T06-G03

- **Ý vàng:** Quá trình tạo LLM gồm pretraining để học tri thức, supervised fine-tuning để học cách trả lời, rồi alignment/reinforcement learning để câu trả lời phù hợp và an toàn.
- **accepted_chunk_ids:** `T06-141`, `T06-143`, `T06-144`, `T06-145`
- **required_keywords:** `pretraining`, `supervised fine-tuning`, `alignment`, `reinforcement learning`, `an toàn`

## Cách M3 owner xác nhận

Đọc từng ý và đối chiếu các chunk đã liệt kê trong transcript gốc. Nếu toàn bộ đúng với cách hiểu của bạn, hãy xác nhận rõ rằng bạn chấp thuận **cả nội dung ý, accepted chunk IDs và required keywords** của 18 mục. Chỉ sau xác nhận đó mới được nhập chúng thành human gold chính thức trong `gold-ideas.csv` và `golden-set.draft.json`.
