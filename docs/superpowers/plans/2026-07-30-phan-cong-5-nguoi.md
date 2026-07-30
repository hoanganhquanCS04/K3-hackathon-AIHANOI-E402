# Sổ tay buổi học — Đầu việc & phân công 5 người

Bản ngắn để in ra dán lên bàn. Chi tiết kỹ thuật từng bước: `2026-07-30-so-tay-buoi-hoc.md`.

## Làm cái gì

Sinh **sổ tay 1 trang gồm đúng 5 ý chính của một buổi học**, từ transcript bài giảng, mỗi ý gắn mã đoạn `[Txx-NNN]` bấm được về nguyên văn lời giảng.

Cho ai: học viên nghỉ buổi hoặc mất mạch, cần nắm lại buổi trong 10 phút.
Tại sao: 72/369 học viên đã xin tutor tóm tắt cả buổi, **65,2% bị tutor trả "không tìm thấy"** (mức nền chỉ 26,8%) — tutor là RAG theo đoạn bôi đen, nó không có đường thấy cả buổi.

---

## Đầu việc tổng — 7 khối

| Khối | Đầu việc | Chủ | Điểm |
|---|---|---|---|
| **A** | Đọc transcript → cấu trúc dữ liệu; chặn buổi không có transcript; bộ kiểm mã trích dẫn | M1 | — |
| **B** | Gọi AI 1 lần sinh 5 ý + viết prompt | M2 | — |
| **C** | Sổ tay hiển thị được + lệnh chạy đầu-cuối | M4 | R5 · 8đ |
| **D** | Script đếm lại bằng chứng + golden set + 3 lượt đo | M3 | R4 · 15đ |
| **E** | Khảo sát 20 người + validation 3 người thật | M5 | R1 · 15đ + R6 · 8đ |
| **F** | `spec.md` + `README.md` + cấu trúc repo | M5 | R2/R3 · 26đ + R7 · 3đ |
| **G** | Slide 6 trang + demo 5 phút | M4 | — |

---

## M1 — Pipeline & Bộ kiểm *(tech)*

Làm phần **tất định**: không gọi AI, chạy là ra kết quả giống nhau mọi lần.

- [ ] **Đọc transcript** → danh sách đoạn, mỗi đoạn có: mã `T03-014`, nguyên văn, cờ *bản ghi thiếu*, cờ *ghi chú lớp*
- [ ] **Danh mục buổi học** — 6 buổi có transcript. Xin buổi 07 thì **từ chối + liệt kê 6 buổi có sẵn**, chặn *trước khi* gọi AI
- [ ] **Bộ kiểm** — đối chiếu mọi mã AI trả về với 700 đoạn thật. Mã bịa → **loại ý đó, ghi lại**, không tự sửa
- [ ] Test cho cả ba phần trên

**Số phải khớp:** 700 đoạn · 103 chỗ `[không nghe rõ]` · 55 đoạn `[Hoạt động lớp: ...]`

**Ràng buộc:** bộ kiểm **không được** dùng chung code với người viết prompt. M1 kiểm, M2 viết prompt — hai người, để ① có đối trọng.

---

## M2 — AI Engineer *(tech)*

Sở hữu **quyết định AI duy nhất** của cả sản phẩm.

- [ ] **Vỏ gọi model** — nạp cả buổi (~40k token) vào **một** lời gọi, nhận JSON đúng schema. Đây là ranh giới provider duy nhất, đổi provider chỉ sửa file này
- [ ] **Prompt** — 5 quy tắc: không bịa mã · không vá chỗ `[không nghe rõ]` · **không đảo ý giảng viên** · ý chính là nội dung học không phải việc hành chính · mỗi ý một câu tự hiểu được
- [ ] **Ghép lại** — đọc transcript → gửi model → trả 5 ý có mã
- [ ] Chỉnh prompt sau lượt đo 1, commit riêng để M3 truy được lượt nào dùng prompt nào

**Không dùng retrieval.** Nạp cả buổi. Đây là điểm khác kiến trúc so với tutor — và là lập luận chính khi người chấm hỏi "khác gì NotebookLM".

**Mốc cứng: có 1 lời gọi AI chạy thật trước CP3.** Làm việc này trước phần render/CLI.

---

## M3 — Eval Engineer *(tech)* — R4, 15đ

- [ ] **Script đếm lại bằng chứng** — sinh lại mọi con số ở spec §2 từ CSV chatlog. Tiêu chí #2 đòi "đếm kiểm lại được", script này là câu trả lời
- [ ] **Mã hoá golden set** — nhận 18 ý vàng từ M5, chuyển thành JSON + 2 ca đặc biệt (buổi ngoài phạm vi, đoạn bản ghi thiếu) = **20 case**
- [ ] **Harness** — chạy 20 case, xuất bảng: mã trích dẫn có thật không · recall so với ý vàng · từ chối đúng không · cờ bản ghi thiếu
- [ ] **In phiếu chấm tay** cho 2 chiều máy không đo được: *đoạn có chống lưng ý này không* và *có đảo ý không* → đưa **người ngoài nhóm** điền
- [ ] **Chạy 3 lượt, ghi cả 3** — kể cả lượt kém nhất

**Quan trọng:** lượt không đạt ngưỡng **vẫn ghi nguyên**. Rubric tính đủ điểm cho kết quả trung thực; số bị chỉnh hoặc lượt bị xoá thì không được tính.

---

## M4 — Interface & Demo *(tech nhẹ)* — R5, 8đ

- [ ] **Sổ tay hiển thị** — mỗi ý: số thứ tự, nội dung, mã đoạn, **và nguyên văn đoạn đó ngay bên dưới** (để người đọc kiểm ngay tại chỗ, không phải mở file khác)
- [ ] **Cảnh báo bản ghi thiếu** — ý nào neo vào đoạn có `[không nghe rõ]` thì in cảnh báo
- [ ] **Mục "ý đã bị loại"** — ghi lại ý bị bộ kiểm loại, không giấu
- [ ] **Lệnh chạy** — `python -m sotay build 03` và `build 07` (ca từ chối)
- [ ] **Slide 6 trang**: pain+số · lát cắt · khác gì NotebookLM · kiến trúc · 4 lớp chỗ khó · kết quả đo
- [ ] **Dry run bấm giờ 2 lần**, chuẩn bị đường lùi nếu mạng chết ở CP6

---

## M5 — Product & Research *(non-tech)* — R1 15đ + R6 8đ + R7 3đ = **26 điểm**

Không viết code. Giữ khối điểm lớn nhất.

- [ ] **Khảo sát ≥20 người ngoài nhóm**, dùng đúng 4 câu, không đổi cách hỏi giữa các người:
  1. Từng nghỉ / vào muộn / mất mạch một buổi chưa?
  2. Lúc đó làm gì để nắm lại? *(ghi nguyên văn)*
  3. Mất bao lâu?
  4. Có sổ tay 1 trang 5 ý bấm được về nguyên văn thì có dùng không?
  → Log **toàn bộ** câu hỏi + từng câu trả lời. Đạt khi ≥20 người và ≥50% trả lời "có" ở câu 1
- [ ] **Chọn trích dẫn nguyên văn** — ≥5 câu học viên thật từ chatlog, minh hoạ cho pain
- [ ] **Bảng impact 3 ứng viên** — bao nhiêu người × tần suất × tốn gì mỗi lần + lý do chọn + ứng viên đã loại
- [ ] **Gán nhãn 18 ý vàng** — đọc 6 transcript, mỗi buổi chọn 3 ý mà người nghỉ buổi *bắt buộc* phải nắm. Mỗi ý ghi: mã đoạn nói điều đó + 3-5 từ khoá mà cách diễn đạt đúng nào cũng phải chứa. **Đây là việc phán đoán của người đọc, không sinh bằng AI.** Đưa M3 mã hoá
- [ ] **Validation ≥3 người thật ngoài nhóm** thử prototype trước demo — tên cụ thể, câu nói nguyên văn, họ bỏ ở bước nào
- [ ] **Viết `spec.md`** theo `03-template-ai-spec.md` — **hạn cứng 23:59 ngày 1**
- [ ] **`README.md`** + dựng đúng cấu trúc repo nộp bài + nhắc 5 người viết `reflection/`

**Số ở spec phải là output của script M3, không gõ tay.**

**Nếu khảo sát <50%:** ghi thật là persona "nghỉ buổi" không được chống lưng, đổi persona chính sang "ôn lại sau buổi" (có 10,2% lượt ngoài giờ lớp chống lưng). **Không sửa số khảo sát.**

---

## Ai chờ ai

```
M5 khảo sát ─────────────────────────────► spec (M5)
M5 gán nhãn ý vàng ──► M3 mã hoá ──┐
M1 pipeline ──► M2 gọi AI ──────────┼──► M3 đo 3 lượt ──► M4 slide
                     └──► M4 render/CLI ──► M5 validation ─┘
```

- **M5 và M3 chạy được ngay từ đầu**, không chờ code. M5 đi khảo sát, M3 viết script đếm.
- **M2 chờ M1** xong phần đọc transcript.
- **M4 chờ M2** xong phần gọi AI.
- **M3 đo được** khi M2 xong + M5 gán nhãn xong.

Ghép đôi bắt buộc: M5↔M3 (golden set) · M5↔M3 (số liệu bằng chứng) · M1↔M2 (kiểm ↔ prompt)

---

## Lịch 6 mốc

| Mốc | M1 | M2 | M3 | M4 | M5 |
|---|---|---|---|---|---|
| **CP1** Canvas | — | — | bắt đầu script đếm | — | **chốt canvas + đi khảo sát** |
| **CP2** Show bấm được | **đọc transcript chạy được** | dựng vỏ gọi model | script đếm xong | — | khảo sát tiếp |
| **CP3** AI chạy thật | danh mục buổi + bộ kiểm | **1 lời gọi AI thật** | — | bắt đầu render | gán nhãn ý vàng |
| **CP4** Spec 23:59 N1 | test xong | prompt v1 | golden set 20 case | CLI chạy | **spec.md nộp** |
| **CP5** Xác minh | giải thích file mình | prompt v2 | **3 lượt đo + phiếu chấm tay** | dry run | **validation 3 người** |
| **CP6** Demo | — | — | — | **demo 5 phút** | — |

Mỗi người phải giải thích được phần có tên mình tại CP5 — không giải thích được thì phần đó 0 điểm.

---

## Định nghĩa "xong"

| # | Điều kiện |
|---|---|
| 1 | `python -m sotay build 03` ra sổ tay 5 ý, mọi mã đoạn tồn tại thật |
| 2 | `python -m sotay build 07` từ chối + liệt kê 6 buổi có sẵn |
| 3 | Golden set 20 case, 18 ý vàng do người gán nhãn |
| 4 | 3 lượt đo trong repo, kể cả lượt kém |
| 5 | ≥20 người khảo sát đã log toàn bộ Q&A |
| 6 | ≥3 người thật đã thử prototype, có tên |
| 7 | `spec.md` nộp trước 23:59 N1, quality bar chốt cứng |
| 8 | 5 file `reflection/`, mỗi người 1 |
| 9 | `data/` **không** có trong repo nộp bài |
