# Sổ tay buổi học — Phân công 5 người (bản 2 luồng)

**Ngày:** 2026-07-30 · **Hướng C** · Thiết kế kỹ thuật: `canvas-va-luong-du-lieu.md`
**Quan hệ với file cũ:** mở rộng `2026-07-30-phan-cong-5-nguoi.md` sang kiến trúc 2 luồng. Giữ nguyên tên vai M1-M5. Chỗ nào hai file lệch nhau thì **lấy file này**.

---

## Làm cái gì

Sinh **sổ tay 1 trang gồm đúng 5 ý chính của một buổi học** từ transcript, mỗi ý gắn mã đoạn `[Txx-NNN]` bấm được về nguyên văn lời giảng.

- **Cho ai:** học viên nghỉ buổi / vào muộn / mất mạch, cần nắm lại buổi trong 10 phút.
- **Tại sao:** tutor là RAG theo đoạn bôi đen — nó không có đường nhìn thấy cả buổi, nên yêu cầu tóm tắt cấp buổi bị trả "không tìm thấy" ở tỉ lệ cao hơn hẳn mức nền. *(Con số chốt: output script M3.)*
- **Hai luồng, một quyết định AI:** luồng 2 sinh sổ tay (sản phẩm) · luồng 1 tra cứu + từ chối (cổng bảo vệ). **Hết giờ thì cắt luồng 1, không bao giờ cắt luồng 2.**

---

## Đầu việc tổng — 8 khối

| Khối       | Đầu việc                                                                 | Chủ | Điểm rubric                          |
| ----------- | --------------------------------------------------------------------------- | ---- | -------------------------------------- |
| **A** | `parse.py` → `segments.jsonl` (700 đoạn, 3 cờ metadata)             | M1   | nền cho tất cả                      |
| **B** | `chunk.py` + `index.py` (BM25) — **chỉ phục vụ luồng 1**     | M1   | —                                     |
| **C** | `citation_validator.py` — bộ kiểm mã trích dẫn dùng chung 2 luồng | M1   | R3 · 11đ                             |
| **D** | Luồng 2: vỏ gọi model + prompt + sinh 5 ý                               | M2   | R5 · 8đ                              |
| **E** | Luồng 1: 4 cổng từ chối + hiệu chỉnh ngưỡng T1                      | M2   | R3 · 11đ                             |
| **F** | Golden set 20 case + script đếm bằng chứng + 3 lượt đo               | M3   | R4 · 15đ                             |
| **G** | Sổ tay hiển thị + CLI + slide 6 trang + dry run                          | M4   | R5 · 8đ                              |
| **H** | Khảo sát 20 người + 18 ý vàng + validation +`spec.md` + repo        | M5   | R1 15đ + R2/R3 26đ + R6 8đ + R7 3đ |

---

## M1 — Pipeline & Bộ kiểm *(tech)*

Làm phần **tất định**: không gọi AI, chạy là ra kết quả giống nhau mọi lần.

- [ ] **`parse.py`** — 6 file `.md` → `segments.jsonl`, mỗi dòng có: `seg_id · session · session_title · locate_confidence · section_idx · section_title · order · text · speaker · has_unclear · is_activity · n_chars`
- [ ] **Danh mục buổi** — 6 buổi có transcript. Xin buổi 07 → **từ chối + liệt kê 6 buổi có sẵn**, chặn *trước khi* gọi AI
- [ ] **`chunk.py`** — gộp đoạn liền kề trong cùng section, target 1.100 / trần 1.800 ký tự, overlap 1 đoạn, không gộp qua section hay qua buổi, đoạn >1.800 ký tự tách theo câu nhưng **giữ mã gốc khi trích dẫn**
- [ ] **`index.py`** — BM25 trên `f"{session_title} › {section_title}\n{chunk_text}"`, bỏ đoạn `is_activity`
- [ ] **`citation_validator.py`** — đối chiếu mọi mã AI trả về với 700 đoạn thật. Mã bịa → **loại ý đó + ghi lại, KHÔNG tự sửa**. Cite trỏ vào `speaker=student` → buộc gắn nhãn "một học viên nêu". Chunk có `has_unclear` → chèn cảnh báo
- [ ] Test cho cả 5 phần trên

**Số phải khớp khi chạy xong:** `700 đoạn · 55 is_activity · 103 has_unclear · 69 speaker=student`. Lệch một con là parse sai, dừng lại sửa ngay.

**Ràng buộc chéo:** bộ kiểm **không được** dùng chung code với người viết prompt. M1 kiểm, M2 viết prompt — hai người, để lớp ① có đối trọng thật.

---

## M2 — AI Engineer *(tech)*

Sở hữu **quyết định AI duy nhất** của sản phẩm.

### Luồng 2 — làm trước, đây là sản phẩm

- [ ] **Vỏ gọi model** — nạp cả buổi (8-38k token) vào **một** call, nhận JSON đúng schema. Đây là ranh giới provider duy nhất; đổi provider chỉ sửa file này
- [ ] **Prompt 5 quy tắc:** không bịa mã · không vá chỗ `[không nghe rõ]` · **không đảo ý giảng viên** · ý chính là nội dung học không phải việc hành chính · mỗi ý một câu tự hiểu được
- [ ] Ghép: đọc `segments.jsonl` → gửi model → 5 ý có mã → qua validator của M1
- [ ] Chỉnh prompt sau lượt đo 1, **commit riêng** để M3 truy được lượt nào dùng prompt nào
- [ ] **Luật đổi kiến trúc:** nếu lượt đo 1 có ≥1 mã bịa → chuyển sang map-reduce theo section (chi tiết ở `canvas-va-luong-du-lieu.md` §6.2), giữ số đo của bản one-shot làm bằng chứng cho phương án bị loại

**Không dùng retrieval cho luồng 2. Nạp cả buổi.** Đây là điểm khác kiến trúc so với tutor — và là lập luận chính khi giám khảo hỏi "khác gì NotebookLM".

### Luồng 1 — làm sau, cắt được nếu trễ

- [ ] **Cổng 0** phân loại ý định: `nội_dung_khoá | logistics | ngoài_phạm_vi | chào_hỏi`
- [ ] **Cổng 1** (code, trước generate): top-1 < T1 → từ chối cứng + liệt kê 3 heading gần nhất · top-1 ≈ top-2 khác buổi → hỏi lại một câu
- [ ] **Cổng 2** (trong generate): JSON schema có `status: answered | insufficient | out_of_scope`
- [ ] **Cổng 3**: gọi validator của M1
- [ ] **Hiệu chỉnh T1**: 30 câu (20 trong phạm vi + 10 ngoài, lấy thật từ chatlog), ghi bảng phân bố điểm, chốt T1 bằng số, đưa bảng cho M3 đưa vào spec §7

**Mốc cứng: có 1 lời gọi AI chạy thật trước CP3.** Làm việc này trước phần render/CLI.

---

## M3 — Eval Engineer *(tech)* — R4, 15đ

- [ ] **Script đếm bằng chứng** — sinh lại **mọi** con số ở spec §1-§2 từ CSV chatlog. Tiêu chí nghiệm thu #2 đòi "đếm kiểm lại được", script này chính là câu trả lời
- [ ] **Chốt một quy tắc đếm duy nhất** và ghi ra: đếm theo lượt hay theo user · regex nhận "yêu cầu tóm tắt cả buổi" · regex nhận "trả lời không tìm thấy" · chạy trên bao nhiêu mẫu
- [ ] **Soi tay ≥30 mẫu** đo tỉ lệ false positive của regex, ghi số đó vào spec
- [ ] **Mã hoá golden set** — nhận 18 ý vàng từ M5 → JSON + 2 ca đặc biệt (buổi 07 ngoài phạm vi, đoạn bản ghi thiếu) = **20 case**, phủ đủ ≥2 case/lớp chỗ khó
- [ ] **Harness** — chạy 20 case, xuất bảng: mã trích dẫn có thật không · recall so với ý vàng · từ chối đúng không · cờ bản ghi thiếu có bật không · có gán nhầm lời học viên không
- [ ] **Phiếu chấm tay** cho 2 chiều máy không đo được — *đoạn có thật sự chống lưng ý này không* và *có đảo ý giảng viên không* → đưa **người ngoài nhóm** điền
- [ ] **Chạy 3 lượt, ghi cả 3**, kể cả lượt kém nhất

**Luật cứng:** lượt không đạt ngưỡng **vẫn ghi nguyên**. Rubric tính đủ điểm cho kết quả trung thực; số bị chỉnh hoặc lượt bị xoá thì không được tính điểm nào.

**M3 là nguồn số duy nhất.** Số nào chưa qua script M3 thì đánh dấu `[chờ M3 xác nhận]`, không được lên slide.

---

## M4 — Interface & Demo *(tech nhẹ)* — R5, 8đ

- [ ] **Sổ tay hiển thị** — mỗi ý: số thứ tự · nội dung · mã đoạn · **nguyên văn đoạn đó ngay bên dưới** (người đọc kiểm tại chỗ, không phải mở file khác)
- [ ] **Mục "Học viên nêu trong buổi"** tách riêng, không trộn vào 5 ý chính
- [ ] **Mục "⚠ Chỗ bản ghi thiếu"** — ý nào neo vào đoạn có `[không nghe rõ]` thì in cảnh báo
- [ ] **Mục "Ý đã bị loại"** — ghi lại ý bị validator loại, không giấu
- [ ] **Dòng độ tin cậy định vị buổi** (buổi 05/06 là `—`) hiện ngay đầu sổ tay
- [ ] **Lệnh chạy:** `python -m sotay build 03` (happy path) · `build 07` (ca từ chối) · `ask "..."` (luồng 1, nếu kịp)
- [ ] **Cache** kết quả ra `cache/` để demo không phải chờ — nhưng **giữ một nút chạy live** để chứng minh AI thật
- [ ] **Slide 6 trang:** pain+số · lát cắt · khác gì NotebookLM/tutor · kiến trúc 2 luồng · 4 lớp chỗ khó · kết quả đo vs bar
- [ ] **Dry run bấm giờ 2 lần** + đường lùi nếu mạng chết ở CP6

---

## M5 — Product & Research *(non-tech)* — 52 điểm

Không viết code. Giữ khối điểm lớn nhất trong nhóm.

- [ ] **Khảo sát ≥20 người ngoài nhóm**, đúng 4 câu, không đổi cách hỏi giữa các người:

  1. Từng nghỉ / vào muộn / mất mạch một buổi chưa?
  2. Lúc đó làm gì để nắm lại? *(ghi nguyên văn)*
  3. Mất bao lâu?
  4. Có sổ tay 1 trang 5 ý bấm được về nguyên văn thì có dùng không?

  → Log **toàn bộ**: câu đã hỏi, từng câu trả lời nguyên văn, ai trả lời. Đạt khi ≥20 người và ≥50% trả lời "có" ở câu 1
- [ ] **≥5 trích dẫn nguyên văn** của học viên thật từ chatlog, minh hoạ pain
- [ ] **Bảng impact ≥3 ứng viên** — bao nhiêu người × tần suất × tốn gì mỗi lần + lý do chọn bằng số + **giữ lại ứng viên đã loại** (3 điểm R1 nằm ở đây, rất nhiều nhóm quên)
- [ ] **Gán nhãn 18 ý vàng** — đọc 6 transcript, mỗi buổi chọn 3 ý mà người nghỉ buổi *bắt buộc* phải nắm. Mỗi ý ghi: mã đoạn nói điều đó + 3-5 từ khoá mà cách diễn đạt đúng nào cũng phải chứa. **Việc phán đoán của người đọc, không sinh bằng AI.** Đưa M3 mã hoá
- [ ] **Validation ≥3 người thật ngoài nhóm** thử prototype trước demo — tên cụ thể, câu nói nguyên văn, họ bỏ ở bước nào. Cần ≥5 mẩu feedback từ ≥5 người cho đủ R6
- [ ] **`spec.md`** theo `03-template-ai-spec.md` — **hạn cứng 23:59 ngày 1**, quality bar chốt từ thời điểm commit
- [ ] **`README.md`** + dựng đúng cấu trúc repo nộp bài + nhắc 5 người viết `reflection/`

**Nếu khảo sát <50% xác nhận:** ghi thật là persona "nghỉ buổi" không được chống lưng, đổi persona chính sang "ôn lại sau buổi". **Không sửa số khảo sát.**

---

## Ai chờ ai

```
M5 khảo sát ──────────────────────────────────► spec.md (M5)
M5 gán nhãn 18 ý vàng ──► M3 mã hoá ──┐
M1 parse ──► M2 luồng 2 ──────────────┼──► M3 đo 3 lượt ──► M4 slide
   └──► M1 chunk+index ──► M2 luồng 1 ─┘
   └──► M1 validator ────────► dùng chung 2 luồng
                    M2 luồng 2 ──► M4 render/CLI ──► M5 validation ─┘
```

- **M5 và M3 chạy được ngay từ đầu**, không chờ code. M5 đi khảo sát, M3 viết script đếm.
- **M2 chờ M1 xong `parse.py`** — đây là đường găng. Nếu 11:00 chưa có `segments.jsonl` thì cả nhóm nghẽn, ai rảnh ghép vào giúp M1.
- **M4 chờ M2** xong luồng 2.
- **M3 đo được** khi M2 xong luồng 2 + M5 gán nhãn xong.
- `chunk.py` / `index.py` / luồng 1 nằm **ngoài** đường găng — cắt được mà không ảnh hưởng sản phẩm chính.

Ghép đôi bắt buộc: M5↔M3 (golden set) · M5↔M3 (số liệu) · M1↔M2 (kiểm ↔ prompt).

---

## Lịch 6 mốc

| Mốc                        | M1                                              | M2                                        | M3                                           | M4                     | M5                                      |
| --------------------------- | ----------------------------------------------- | ----------------------------------------- | -------------------------------------------- | ---------------------- | --------------------------------------- |
| **CP1** Canvas        | —                                              | —                                        | bắt đầu script đếm                      | —                     | **chốt canvas + đi khảo sát** |
| **CP2** Bấm được  | **`parse.py` chạy được, số khớp** | dựng vỏ gọi model                      | script đếm xong                            | —                     | khảo sát tiếp                        |
| **CP3** AI thật      | danh mục buổi + validator                     | **1 lời gọi AI thật (luồng 2)** | golden set 20 case +**bảng lượt 1** | bắt đầu render      | gán nhãn 18 ý vàng                  |
| **CP4** Spec 23:59 N1 | chunk + index xong                              | prompt v1 + bắt đầu luồng 1           | lượt đo 2                                 | CLI chạy              | **`spec.md` nộp**              |
| **CP5** Xác minh     | giải thích được file mình                 | luồng 1 + chốt T1                       | **3 lượt đo + phiếu chấm tay**    | dry run ×2            | **validation ≥5 mẩu có tên**  |
| **CP6** Demo          | —                                              | —                                        | —                                           | **demo 5 phút** | —                                      |

Mỗi người phải giải thích được phần có tên mình tại CP5 — không giải thích được thì phần đó 0 điểm.

---

## Cắt gì khi trễ — theo thứ tự

1. Embedding (giữ BM25 thuần)
2. **Cả luồng 1** — sổ tay vẫn là sản phẩm hoàn chỉnh không có nó
3. Mục "3 câu tự kiểm" trong sổ tay
4. Số buổi demo: chỉ cần chạy được **1 buổi** + **1 ca từ chối**

**Không bao giờ cắt:** validator mã trích dẫn · golden set 20 case · 3 lượt đo · log khảo sát · `spec.md` đúng hạn 23:59.

---

## Định nghĩa "xong"

| #  | Điều kiện                                                                                      |
| -- | ------------------------------------------------------------------------------------------------- |
| 1  | `python -m sotay build 03` ra sổ tay 5 ý, **mọi mã đoạn tồn tại thật**           |
| 2  | `python -m sotay build 07` từ chối + liệt kê 6 buổi có sẵn                               |
| 3  | `segments.jsonl` khớp đúng 700 / 55 / 103 / 69                                               |
| 4  | Golden set 20 case, phủ ≥2 case mỗi lớp chỗ khó, 18 ý vàng do**người** gán nhãn |
| 5  | 3 lượt đo trong`eval/`, kể cả lượt kém, có % đối chiếu quality bar                  |
| 6  | ≥20 người khảo sát đã log toàn bộ Q&A nguyên văn                                       |
| 7  | ≥5 mẩu feedback từ ≥5 người ngoài nhóm, có tên, trong`validation/`                    |
| 8  | `spec.md` commit trước 23:59 N1, quality bar chốt cứng, không sửa sau                     |
| 9  | 5 file`reflection/`, mỗi người 1                                                             |
| 10 | `data/` **không** có trong repo nộp bài · không commit API key                      |
