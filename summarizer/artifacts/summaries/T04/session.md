# Day 1 — Foundation: cách LLM hoạt động (transformer, attention, agent)

Buổi học đầu tiên giới thiệu về cách hoạt động của các mô hình ngôn ngữ lớn (LLM) dựa trên nền tảng Transformer, nhấn mạnh tầm quan trọng của dữ liệu, attention và các yếu tố như evaluation trong phát triển sản phẩm AI. Học viên cũng được hướng dẫn cách chọn mô hình phù hợp và gọi API để tương tác với các mô hình này.

> Đã đọc **98/98** đoạn của 21 mục; 73 đoạn được trích dẫn.

## Ý chính cả buổi

- Khoảng 70% học viên là sinh viên năm cuối, 30% là những người đã có kinh nghiệm làm việc. — `T04-002`
- AI là hệ thống có trí thông minh, bao gồm các khái niệm như machine learning, deep learning và generative AI. — `T04-015`
- Bài kiểm tra Turing được thiết kế để xác định xem máy có thể mô phỏng trí thông minh của con người hay không. — `T04-018`
- Deep learning là nền tảng cho việc máy móc học từ dữ liệu thông qua việc tái tạo mạng neuron thần kinh giống như con người. — `T04-030`
- OpenAI là công ty đầu tiên đưa ChatGPT ra thị trường đại chúng. — `T04-041`
- Bản chất của mô hình Transformer là dự đoán token tiếp theo dựa trên xác suất học được từ hàng triệu câu. — `T04-047`
- Attention trong kiến trúc Transformer giúp mô hình chú ý đến những thông tin quan trọng trong ngữ cảnh. — `T04-053`
- Evaluation quyết định đến 80% thành công sản phẩm và phần lớn các công ty dành 80% nguồn lực để xây dựng hạ tầng evaluation tự động. — `T04-075`

## Nội dung theo mục

**1. Chào lớp và giới thiệu giảng viên**

Giảng viên giới thiệu về bản thân và nội dung khóa học về AI, đặc biệt là các mô hình ngôn ngữ lớn (LLM). — `T04-002` `T04-003` `T04-005` `T04-008` `T04-011` `T04-012`

**2. Nội dung ngày học và bức tranh tổng quan về AI**

Buổi học này tập trung vào tổng quan về AI, lịch sử phát triển và cơ chế hoạt động của các mô hình ngôn ngữ lớn. — `T04-013` `T04-014` `T04-015`

**3. Lịch sử AI: Turing test và hai mùa đông**

Bài giảng trình bày lịch sử của trí tuệ nhân tạo (AI), nhấn mạnh vào các mốc quan trọng như bài kiểm tra Turing và hai mùa đông của AI. — `T04-016` `T04-018` `T04-022` `T04-024` `T04-025` `T04-029`

**4. Deep learning và sức mạnh của dữ liệu**

Nội dung chính của mục này là khám phá cách deep learning hoạt động và tầm quan trọng của dữ liệu trong quá trình học của máy móc. — `T04-030` `T04-031` `T04-032` `T04-033`

**5. AlphaGo và kiến trúc Transformer**

Mục này trình bày về AlphaGo và kiến trúc Transformer, nhấn mạnh sự đột phá của AlphaGo trong cờ vây và sự phát triển của mô hình Transformer trong xử lý ngôn ngữ tự nhiên. — `T04-034` `T04-036` `T04-037` `T04-038` `T04-040`

**6. Cuộc đua AI sau ChatGPT**

Bài giảng trình bày về sự phát triển của AI sau sự ra đời của ChatGPT, sự cạnh tranh giữa các công ty như Google và OpenAI, cũng như các chiến lược của Trung Quốc trong lĩnh vực này. — `T04-041` `T04-042` `T04-043` `T04-044` `T04-045`

**7. Mổ xẻ mô hình ngôn ngữ lớn: dự đoán token và context**

Phần này giải thích cách hoạt động cơ bản của mô hình ngôn ngữ lớn (LLM) dựa trên dự đoán token tiếp theo trong ngữ cảnh, khái niệm token và context cùng những giới hạn của chúng. — `T04-046` `T04-047` `T04-048` `T04-049` `T04-051` `T04-052`

**8. Attention, multi-head và bài học quản lý context**

Nội dung chính của mục này là khái niệm attention trong mô hình Transformer và tầm quan trọng của việc quản lý context khi làm việc với AI. — `T04-053` `T04-054` `T04-056` `T04-057`

**9. Tham số, RLHF và ngành gán nhãn dữ liệu**

Nội dung chính của mục này là thảo luận về tham số trong mô hình AI, vai trò của RLHF trong việc đào tạo mô hình và ngành gán nhãn dữ liệu. — `T04-058` `T04-059` `T04-060` `T04-061` `T04-062` `T04-063`

**10. Thí nghiệm bàn cờ, giới hạn kiến thức và các mức tiếp cận mô hình**

Nội dung chính của mục này là thí nghiệm bàn cờ nhằm kiểm tra khả năng hiểu biết của mô hình LLM và giới hạn kiến thức của nó. — `T04-064` `T04-066` `T04-067` `T04-068` `T04-070` `T04-071`

**11. Temperature và top-k/top-p**

Nội dung chính của mục này là giải thích về cách thức hoạt động của temperature và các chỉ số top-k/top-p trong mô hình LLM. — `T04-072`

**12. Từ mô hình đến AI agent**

Nội dung chính của mục này là quá trình chuyển đổi từ mô hình cơ bản thành AI agent có khả năng tương tác và hoạt động trong thế giới thực. — `T04-073`

**13. Các lớp bao quanh LLM và tầm quan trọng của evaluation**

Nội dung chính của mục này đề cập đến các lớp bao quanh LLM và tầm quan trọng của việc đánh giá (evaluation) trong quá trình phát triển sản phẩm AI. — `T04-074` `T04-075`

**14. Bức tranh thị trường mô hình và tốc độ thay đổi**

Nội dung chính của mục này là sự thay đổi nhanh chóng trong thị trường mô hình và cách mà các mô hình mới có thể thay thế các kiến trúc cũ chỉ trong thời gian ngắn. — `T04-076` `T04-077` `T04-078` `T04-079`

**15. Làn sóng mã nguồn mở Trung Quốc và khoảnh khắc DeepSeek**

Nội dung chính đề cập đến sự nổi lên của các mô hình mã nguồn mở tại Trung Quốc và ảnh hưởng của khoảnh khắc DeepSeek đến thị trường AI. — `T04-080`

**16. Benchmark năng lực và xu hướng chi phí tính toán**

Nội dung chính của mục này là phân tích benchmark năng lực của các mô hình AI và xu hướng chi phí tính toán trong lĩnh vực AI. — `T04-081` `T04-082` `T04-083`

**17. Chọn mô hình phù hợp với công việc**

Nội dung chính của mục này là hướng dẫn cách chọn mô hình AI phù hợp với công việc dựa trên hiểu biết về bài toán và sức mạnh của các mô hình. — `T04-084` `T04-085`

**18. Mixture of Experts**

Nội dung chính của mục này là giới thiệu về kiến trúc Mixture of Experts trong các mô hình ngôn ngữ lớn, nhấn mạnh lợi ích của việc tiết kiệm chi phí và thời gian khi chỉ kích hoạt một số cụm tham số nhất định. — `T04-086`

**19. Cơ bản về gọi API mô hình LLM**

Nội dung chính của mục này là hướng dẫn cơ bản về cách gọi API của mô hình LLM, bao gồm các nguyên tắc chi phí và cấu trúc của prompt. — `T04-087` `T04-088` `T04-089`

**20. Tóm tắt buổi học**

Buổi học đầu tiên tập trung vào cách hoạt động của các mô hình ngôn ngữ lớn dựa trên nền tảng Transformer và tầm quan trọng của việc hiểu rõ mô hình khi xây dựng sản phẩm. — `T04-091`

**21. Tương tác cuối buổi**

Buổi học tập trung vào cách thức hoạt động của Transformer và các khía cạnh liên quan đến LLM, bao gồm cơ chế attention và các yếu tố ảnh hưởng đến hiệu suất của mô hình. — `T04-094` `T04-096`

**Khái niệm:** AI, LLM, Transformer, attention, deep learning, AlphaGo, ChatGPT, API

## Cảnh báo

- Mục 1 (Chào lớp và giới thiệu giảng viên) có 2 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 3 (Lịch sử AI: Turing test và hai mùa đông) có 1 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 4 (Deep learning và sức mạnh của dữ liệu) có 1 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 5 (AlphaGo và kiến trúc Transformer) có 1 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 6 (Cuộc đua AI sau ChatGPT) có 3 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 9 (Tham số, RLHF và ngành gán nhãn dữ liệu) có 2 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 12 (Từ mô hình đến AI agent) có 1 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 16 (Benchmark năng lực và xu hướng chi phí tính toán) có 1 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 17 (Chọn mô hình phù hợp với công việc) có 1 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.
- Mục 21 (Tương tác cuối buổi) có 2 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu.

<sub>map: gpt-4o-mini · reduce: gpt-4o-mini · prompt: v1</sub>