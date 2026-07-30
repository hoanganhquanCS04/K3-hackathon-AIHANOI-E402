# Sổ tay buổi học — Canvas & luồng xử lý dữ liệu

**Hướng:** C (Làn mở) · **Ngày:** 2026-07-30
**Quan hệ với file khác:** `2026-07-30-so-tay-buoi-hoc-design.md` là bản design gốc (1 luồng). File này mở rộng sang **2 luồng** và đặc tả tầng dữ liệu dùng chung. Phân công theo `team-assignment.md`.

---

## 1. Canvas CP1 — 7 dòng

```
Hướng:          C — Làn mở. Sản phẩm mới, KHÔNG nằm trong khung chat của AI tutor.

Job executor:   Học viên đã nghỉ buổi / vào muộn / mất mạch, tối hôm đó cần nắm lại buổi.

Pain 1 câu:     Học viên mất mạch một buổi phải tua lại 2 tiếng ghi âm hoặc đi hỏi tutor —
                nhưng tutor là RAG theo đoạn bôi đen, nó không có đường nhìn thấy cả buổi,
                nên yêu cầu tóm tắt cấp buổi bị trả "không tìm thấy" ở tỉ lệ cao hơn hẳn nền.
                Hậu quả: học viên bỏ luôn, phần kiến thức buổi đó trống vĩnh viễn.

Bằng chứng:     (B) mining chatlog — số chốt lấy từ script của M3, xem §7
                (A) khảo sát ≥20 người ngoài nhóm, 4 câu cố định, ≥50% xác nhận

Lát cắt:        Học viên nghỉ buổi 2 · nắm lại nội dung buổi trong 10 phút ·
                AI chọn và tóm 5 ý chính từ transcript buổi đó ·
                nhận sổ tay 1 trang, mỗi ý gắn mã đoạn [Txx-NNN] bấm được về nguyên văn.

Automation:     Automate CÓ KIỂM CHỨNG cho việc sinh sổ tay — sai thì rẻ, vì mã đoạn cho
                người đọc tự kiểm ngay tại chỗ.
                RIÊNG quyết định "có đủ căn cứ để nói không" là CONDITIONAL — dưới ngưỡng
                thì từ chối, không đoán. Cost-of-error: một dòng tóm sai lời giảng viên là
                học viên học sai kiến thức và không có cách nào biết mình sai.

Willing users:  [3 tên — M5 chốt tại CP1]
Phân công:      M1 pipeline · M2 AI · M3 eval · M4 giao diện+demo · M5 product+research
```

### Non-goals (bản build không được vi phạm — R2 chấm đúng chỗ này)

1. Không trả lời câu hỏi logistics (deadline, link, cách nộp bài).
2. Không tóm phần `[Hoạt động lớp: ...]` — đó là ghi chú hành chính, không phải nội dung học.
3. Không sinh bất kỳ nội dung nào ngoài 6 transcript có sẵn.
4. Không tóm tắt đa buổi, không so sánh giữa các buổi.
5. Không cá nhân hoá, không chấm điểm, không theo dõi tiến độ học viên.

---

## 2. Nguyên tắc kiến trúc: MỘT quyết định AI, HAI điểm vào

Nhóm build 2 luồng, nhưng **lát cắt vẫn phải là một câu**. Cách giữ cho hai thứ đó không mâu thuẫn:

> **Quyết định AI duy nhất của sản phẩm:** *đoạn giảng nào chống lưng cho khẳng định nào — và khi không đoạn nào chống lưng được thì nói ra điều đó thay vì viết tiếp.*

Hai luồng là **hai điểm vào của cùng một quyết định**:

| | Luồng 2 — sinh sổ tay | Luồng 1 — tra cứu trong buổi |
|---|---|---|
| Kích hoạt | Người dùng chọn một buổi | Người dùng hỏi một câu |
| Duyệt gì | Toàn bộ buổi, tuần tự | Các đoạn khớp câu hỏi |
| Ra gì | 5 ý chính + mã đoạn | Câu trả lời + mã đoạn |
| Khi không có căn cứ | Ghi vào mục "chỗ bản ghi thiếu" | Từ chối + liệt kê cái mình có |
| Bộ kiểm mã trích dẫn | **Dùng chung** | **Dùng chung** |

⚠ **Cảnh báo điểm số (R2, 15đ):** nếu đem luồng 1 ra demo như một sản phẩm hỏi-đáp riêng, giám khảo sẽ thấy lát cắt một câu **không khớp bản build** và nhóm mất điểm ở đúng khối nặng nhất. Cách trình bày an toàn:

- Slide và spec khai **luồng 2 là sản phẩm**.
- Luồng 1 khai là **cổng bảo vệ + đường đi "hỏi sâu"** trong §6 (bốn đường đi trải nghiệm), không phải feature thứ hai.
- Nếu hết thời gian, **cắt luồng 1 trước, không bao giờ cắt luồng 2.**

---

## 3. Sơ đồ tổng

```
data/vlearn-pack/transcript/*.md      6 file · 700 đoạn có mã [Txx-NNN]
            │
            ▼  parse.py
     segments.jsonl        700 dòng — ĐƠN VỊ NGUYÊN TỬ, không bao giờ cắt nhỏ hơn
            │
            ├───────────────────────────────────┐
            ▼  chunk.py                         │   luồng 2 đọc THẲNG segments
     chunks.jsonl   ~340-400 chunk              │   (không dùng chunks.jsonl)
            │                                   │
            ▼  index.py                         │
     bm25.pkl   (+ emb.npy nếu kịp)             │
            │                                   │
   ┌────────▼──── LUỒNG 1 ─────┐      ┌─────────▼──── LUỒNG 2 ─────┐
   │ tra cứu + 4 cổng từ chối  │      │ sổ tay 1 trang / buổi      │
   └────────┬──────────────────┘      └─────────┬──────────────────┘
            └────────► citation_validator.py ◄──┘
                       mã không có trong context → LOẠI Ý ĐÓ, ghi lại
```

**Quyết định kiến trúc quan trọng nhất, ghi thẳng vào spec §4:**

| Buổi | Ký tự (đã bỏ hoạt động lớp) | ≈ Token | Section |
|---|---|---|---|
| transcript-01 | 62.450 | ~20,8k | 11 |
| transcript-02 | 25.015 | ~8,3k | 5 |
| transcript-03 | 113.561 | ~37,9k | 19 |
| transcript-04 | 85.059 | ~28,4k | 21 |
| transcript-05 | 73.036 | ~24,3k | 18 |
| transcript-06 | 75.902 | ~25,3k | 21 |

> **Cả một buổi chỉ 8k-38k token — lọt trong context window. Luồng 2 KHÔNG cần retrieval, không cần embedding, không đụng vector store.** Chỉ luồng 1 mới cần index.

Đây cũng là câu trả lời cho *"khác gì NotebookLM / khác gì tutor?"*: tutor là RAG theo đoạn bôi đen nên không bao giờ nhìn thấy cả buổi; sổ tay nạp trọn buổi nên nhìn thấy được mạch giảng.

---

## 4. Tầng dữ liệu

### 4.1 `segments.jsonl` — 700 dòng

```json
{
  "seg_id": "T01-009",
  "session": "01",
  "session_title": "Day 2 sáng — Xác định bài toán kinh doanh cho AI",
  "locate_confidence": "cao",
  "section_idx": 1,
  "section_title": "Product manager, project manager và văn hoá làm product",
  "order": 9,
  "text": "[Học viên]: Project thì kiểu một dự án tạo ra xong rồi là xong luôn...",
  "speaker": "student",
  "has_unclear": false,
  "is_activity": false,
  "n_chars": 612
}
```

Ba cờ metadata này không phải để trang trí — chúng là chỗ ăn điểm R3 (chỗ khó, 11đ):

| Field | Số đã đếm | Phục vụ lớp chỗ khó nào |
|---|---|---|
| `speaker` | **69 đoạn** chứa lời `[Học viên]` | **④ đặc thù domain** — gán lời học viên thành lời giảng viên là học sai kiến thức. Ví dụ `[T01-009]` là *học viên* định nghĩa PM vs project manager, model rất dễ tóm thành "giảng viên nói…" |
| `has_unclear` | **103 đoạn** chứa `[không nghe rõ]` | **① nguồn sự thật** — chỗ bản ghi thiếu phải nói ra, không lấp bằng suy đoán |
| `is_activity` | **55 đoạn** `[Hoạt động lớp: ...]` | Loại khỏi index và khỏi bản tóm. Vẫn giữ trong file để đếm và để báo "phần này là hoạt động lớp, không tóm" |

`locate_confidence` lấy từ bảng trong `data/vlearn-pack/transcript/README.md` — buổi 05 và 06 không gắn được số ngày (giá trị `—`). **Hiển thị thẳng ra sổ tay**, đúng nguyên tắc HAX **G2 — làm rõ nó làm tốt đến đâu**.

**Số phải khớp khi M1 chạy xong:** `700 đoạn · 55 is_activity · 103 has_unclear · 69 speaker=student`.

### 4.2 Luật chunk — CHỈ cho luồng 1

1. **Đoạn `[Txx-NNN]` là nguyên tử, không bao giờ cắt ngang.** Mã đoạn chính là citation unit; cắt ngang là mất khả năng truy vết — mất luôn chiều chất lượng chính của cả sản phẩm.
2. **Gộp các đoạn liền kề trong CÙNG section**, mục tiêu ~1.100 ký tự, trần cứng 1.800.
3. **Không gộp qua ranh giới section, không gộp qua ranh giới buổi.** Heading `##` là ranh giới ngữ nghĩa người biên tập đã đặt sẵn — dùng miễn phí.
4. **Overlap 1 đoạn** giữa hai chunk liền kề cùng section.
5. **Ngoại lệ đoạn khổng lồ:** có 1 đoạn ~5.000 ký tự (transcript-06) vượt trần → tách theo câu thành `#a`, `#b`, nhưng **khi trích dẫn vẫn in mã gốc**.
6. Bỏ 55 đoạn `is_activity` khỏi index.

Kết quả chạy thử 3 cấu hình trên data thật:

| Target / trần | Số chunk | Ký tự/chunk (median · p90) | Đoạn/chunk (median) |
|---|---|---|---|
| 900 / 1.500 | 389 | 1.089 · 1.490 | 1 |
| **1.100 / 1.800** ← chọn | **~340** | 1.289 · 1.728 | **2** |
| 1.500 / 2.400 | 265 | 1.699 · 2.246 | 2 |

Chọn 1.100/1.800: median 2 đoạn/chunk là điểm cân bằng — đủ ngữ cảnh để hiểu, đủ hẹp để mã đoạn còn chỉ đúng chỗ. Cộng overlap ra **~400 chunk**. *(Con số này M1 chạy lại sẽ ra chính xác; ~340 là đo khi chưa bật overlap.)*

Với ~400 chunk thì **mọi thứ chạy trong RAM. Không dựng Chroma/FAISS/Docker** — thêm 2 tiếng setup, không thêm điểm nào, và CP5 lại phải giải thích thứ mình không viết.

### 4.3 Embed cái gì

```python
embed_text = f"{session_title} › {section_title}\n{chunk_text}"
```

Prefix heading là **bắt buộc**: 28% đoạn dưới 300 ký tự, đứng một mình không đủ ngữ cảnh để match. Chỉ embed `embed_text`; metadata không embed, lọc bằng code sau khi retrieve.

⚠ **Cân nhắc bảo mật trước khi embed** (README gốc, mục Bảo mật dữ liệu điều 4): embed cả corpus = gửi ~445.000 ký tự transcript ra provider ngoài. Đó không phải "phần tối thiểu cần thiết". Thứ tự làm:

- **CP2 — mặc định: BM25** (`rank_bm25`, thuần Python, chạy offline, **không byte nào rời máy**). Với câu hỏi nặng thuật ngữ Việt–Anh lẫn lộn của khoá này, BM25 chạy tốt bất ngờ.
- **CP3 — nếu kịp:** thêm embedding, hợp nhất điểm với BM25. Dùng model **local** (`multilingual-e5-small`, ~470MB, CPU thừa sức cho 400 chunk) hoặc API bằng **key trả phí có cam kết không dùng data để train**.
- Bước generate gửi 3-5 chunk ra API là hợp lệ — đó mới đúng nghĩa "phần tối thiểu".

**Lời gọi AI thật bắt buộc (R5) nằm ở bước generate, không phải retrieval** → dùng BM25 vẫn đủ điều kiện tính điểm.

### 4.4 Lưu ở đâu

```
codebase/
├── pipeline/
│   ├── parse.py          transcript .md  → segments.jsonl
│   ├── chunk.py          segments        → chunks.jsonl
│   └── index.py          chunks          → bm25.pkl (+ emb.npy)
├── store/                ← .gitignore TOÀN BỘ (dẫn xuất của data pack)
│   ├── segments.jsonl    700 dòng, ~450KB
│   ├── chunks.jsonl      ~400 dòng
│   ├── bm25.pkl          ~2MB
│   └── emb.npy           400 × 768 float32 ≈ 1,2MB
├── flow1_ask.py
├── flow2_recap.py
├── citation_validator.py
├── cache/                ← .gitignore — section-summary đã sinh, để demo không phải gọi lại
└── prompts/*.txt         ← COMMIT (giám khảo cần đọc prompt)
```

Retrieval = `np.dot(emb, q)` trên 400 vector: dưới 1ms.

Bổ sung vào `.gitignore`:

```gitignore
codebase/store/
codebase/cache/
data/vlearn-pack/
*.env
.env.local
```

---

## 5. Luồng 1 — tra cứu + từ chối khi thiếu căn cứ

Từ chối **không phải một câu trong prompt**. Nó là 4 cổng, trong đó **2 cổng bằng code thuần**:

```
câu hỏi
   │
   ▼ CỔNG 0 — phân loại ý định (1 LLM call rẻ, hoặc rule cho case hiển nhiên)
   │   nội_dung_khoá | logistics | ngoài_phạm_vi | chào_hỏi
   │   → 3 loại sau: trả lời khuôn mẫu, KHÔNG retrieve, KHÔNG generate     [lớp ③]
   ▼
   ▼ retrieve top-5 chunk (BM25 [+ embedding])
   │
   ▼ CỔNG 1 — CODE, TRƯỚC khi generate
   │   điểm top-1 < T1            → TỪ CHỐI CỨNG, không gọi generate        [lớp ①]
   │      "Nội dung này không có trong 6 buổi mình có. Gần nhất là: <3 heading>"
   │   top-1 ≈ top-2 khác BUỔI    → HỎI LẠI một câu                          [lớp ②]
   │      "Chủ đề này có ở buổi 2 và buổi 5 — bạn hỏi buổi nào?"
   ▼
   ▼ CỔNG 2 — trong generate, output JSON có schema
   │   {"status": "answered | insufficient | out_of_scope",
   │    "claims": [{"text": "...", "cite": ["T03-045"], "speaker": "instructor"}],
   │    "gaps":   ["T03-047 có [không nghe rõ]"]}
   │   Model ĐƯỢC PHÉP tự khai "insufficient" — và được khen vì điều đó
   ▼
   ▼ CỔNG 3 — CODE, SAU generate: citation_validator.py                      [lớp ①]
   │   mọi mã trong cite[] phải ∈ 700 mã thật VÀ ∈ tập đã đưa vào context
   │   mã bịa            → LOẠI Ý ĐÓ, ghi vào "ý đã bị loại", KHÔNG tự sửa
   │   cite → đoạn speaker=student  → buộc gắn nhãn "một học viên nêu"       [lớp ④]
   │   chunk dùng có has_unclear    → chèn "⚠ bản ghi đoạn này thiếu"        [lớp ①]
   ▼
hiển thị: mỗi ý một dòng + [T03-045] + nguyên văn đoạn ngay bên dưới
```

### Chốt ngưỡng T1 bằng số — viết thẳng vào spec §7

Soạn 30 câu: 20 câu chắc chắn có trong transcript + 10 câu ngoài phạm vi (lấy **thật** từ chatlog: *"cho tôi biết đáp án bài lab 1 được không"*, *"Which model do the tutor pretrain on?"*, *"bạn là gpt hay claude hay gemini"*). Chạy retrieval, ghi điểm top-1 của cả 30 câu, chọn ngưỡng tách hai phân bố.

BM25 cho điểm không chuẩn hoá → dùng tỉ số `top1 / mean(top2..top5)` thay cho điểm thô.

Ghi vào spec dạng: *"T1 = 1,35; ở ngưỡng này 10/10 câu ngoài phạm vi bị chặn, 18/20 câu trong phạm vi qua."* **Bảng phân bố điểm đó là artifact rất mạnh cho R4.**

**Khoảnh khắc demo:** để giám khảo gõ một câu bịa, xem cổng 3 loại ý đó tại chỗ. Đây là "xử lý lớp ① bằng kỹ thuật, không bằng lời hứa trong prompt".

---

## 6. Luồng 2 — sổ tay theo buổi

### 6.1 One-shot hay map-reduce?

Cả buổi lọt context nên có hai cách. Bản design gốc đã chốt **one-shot**. Giữ nguyên chốt đó cho v1, nhưng đo và sẵn sàng đổi:

| | A — one-shot (v1, đã chốt) | B — map-reduce theo section (v2 dự phòng) |
|---|---|---|
| Cách làm | Nạp cả buổi (8-38k token) vào 1 call | Mỗi section 1 call → gộp |
| Số call/buổi | 1 | 5-21 map + 1 reduce |
| Rủi ro bịa mã | **Cao** — model phải nhớ tới 162 mã trong một lượt | Thấp — mỗi call chỉ thấy 4-28 đoạn |
| Bỏ sót | Nặng ở giữa/cuối buổi dài (buổi 03: 37,9k token) | Không — mọi section đều được đọc |
| Hỏng một phần | Hỏng cả bản tóm | Chỉ hỏng 1 section, ghi rõ và đi tiếp |
| Độ phức tạp | Thấp — hợp deadline CP3 | Trung bình |

**Luật đổi (ghi vào spec §8 làm multi-prototype):** chạy v1 qua golden set. Quality bar có điều kiện cứng *"0 case bịa mã đoạn"*. **Nếu lượt 1 có ≥1 mã bịa → chuyển sang B**, giữ lại số đo của A làm bằng chứng cho phương án bị loại. Đây đúng là thứ rubric §3.3 khuyến khích: hai phương án khác nhau ở một trục có tên, chọn bằng số chứ không bằng cảm tính.

### 6.2 Nếu chạy map-reduce (v2)

**MAP** — mỗi section một call, input là toàn văn section:

```json
{"section_title": "Từ đề bài mơ hồ đến vấn đề thực sự",
 "key_points": [
   {"claim": "Kỹ năng thiếu nhất không phải code AI mà là bóc tách đề bài mơ hồ thành thứ triển khai được",
    "cite": ["T01-001", "T01-005"],
    "speaker": "instructor",
    "quote": "từ mục tiêu, yêu cầu mơ hồ, biến nó thành thứ cụ thể có thể triển khai được"}],
 "skipped": [], "gaps": ["T01-014 có [không nghe rõ]"]}
```

Luật trong prompt map: tối đa 3 ý/section · mọi ý bắt buộc ≥1 mã đoạn · đoạn `speaker=student` phải ghi `"speaker":"student"` · section chỉ có hoạt động lớp → `key_points: []` và ghi vào `skipped`.

**REDUCE** — gom 5-21 JSON section (chỉ còn ~2-4k token) → 1 call. Model **chỉ được chọn và sắp xếp lại claim đã có, không được viết claim mới** → mã đoạn tự động đúng.

### 6.3 Cấu trúc sổ tay đầu ra

```markdown
# Sổ tay buổi — Day 2 sáng: Xác định bài toán kinh doanh cho AI
> Nguồn: transcript-01 · 89 đoạn · độ tin cậy định vị buổi: CAO
> Mọi ý dưới đây bấm được về nguyên văn. Không có mã đoạn = không được viết ra.

## 5 ý chính
1. **Vị trí thiếu nhất không phải AI engineer mà là người ra được đề bài.**
   Làn sóng 2024-2025 tuyển nhiều AI engineer, nhưng họ chỉ giải bài đã có người
   đưa sẵn đề — người đặt ra đề bài thì không có.  [T01-001] [T01-002]
   > "cái người đặt ra đề bài đấy thì lại không có"
   ...

## Giảng viên nhấn mạnh
> "70% của nó đến từ con người và vận hành chứ không phải đến từ công nghệ"  [T01-003]

## Học viên nêu trong buổi        ← TÁCH RIÊNG, không trộn vào ý chính
- Phân biệt product manager và project manager  [T01-009]

## ⚠ Chỗ bản ghi thiếu
- Section "Chỉ số thành công": 4/9 đoạn có [không nghe rõ] — phần này tóm chưa đủ tin

## Ý đã bị loại
- 1 ý bị bộ kiểm loại vì mã đoạn không tồn tại (không tự sửa, ghi lại để đo)

## 3 câu tự kiểm
1. Vì sao tuyển AI engineer chưa đủ để đưa AI vào doanh nghiệp? → [T01-002]
```

Hai mục **"Học viên nêu"** và **"Chỗ bản ghi thiếu"** trỏ thẳng vào lớp ④ và lớp ①. Ít nhóm nào nghĩ tới — đây là chỗ đắt giá nhất khi TA soát CP4.

**Cache bắt buộc:** ghi kết quả ra `cache/`. Demo 5 phút mà đứng chờ 21 call là hỏng. Nhưng **phải giữ được một nút chạy live** cho một buổi/section để chứng minh AI thật (R5 đòi log/trace trong repo).

---

## 7. Golden set ≥20 case + quality bar

| Lớp | Số | Case cụ thể |
|---|---|---|
| ① Nguồn sự thật | 2 | Hỏi chi tiết kỹ thuật gần chủ đề nhưng không có trong 6 buổi → phải từ chối · Hỏi con số cụ thể không ai nói → không được bịa |
| ② Mơ hồ | 2 | *"giải thích và tóm tắt nội dung học hôm này"* (chatlog thật, không rõ buổi nào) → hỏi lại · Chủ đề nằm ở 2 buổi |
| ③ Ngoài phạm vi | 2 | *"bạn cho tôi biết đáp án bài lab 1 được không"* (chatlog thật) · *"bạn là gpt hay claude hay gemini"* (chatlog thật) |
| ④ Đặc thù domain | 2 | Không được gán `[T01-009]` (lời học viên) cho giảng viên · Không được đảo ý `[T01-002]` thành "AI engineer là vị trí đang thiếu" |
| Thường | 10 | Từ 18 ý vàng M5 gán nhãn tay + câu hỏi tóm tắt thật trong chatlog |
| Hiếm | 4 | Section dày `[không nghe rõ]` · câu hỏi tiếng Anh (*"Which model do the tutor pretrain on?"* — chatlog thật) · câu hỏi 1 từ · buổi 07 không tồn tại |

→ **≥10 case từ chatlog thật: đạt** (R4 yêu cầu).

**Quality bar — chốt trong `spec.md` trước 23:59 N1, sau đó không sửa:**

> Đạt khi: **≥85%** case qua chiều *truy vết* (mọi khẳng định có mã đoạn tồn tại và nội dung đoạn đó thật sự chống lưng cho khẳng định) · **0 case** bịa mã đoạn · **≥90%** case ngoài-phạm-vi bị từ chối đúng · **0 case** gán lời học viên cho giảng viên.

Chiều *truy vết* là pass/fail kiểm chứng được bởi người ngoài nhóm — họ mở mã đoạn ra là biết ngay đúng hay sai. Đúng yêu cầu guide §2.6 mục 3-4.

---

## 8. Luật số liệu — một nguồn duy nhất

Trong repo hiện có hai bộ số đếm theo hai quy tắc khác nhau (ví dụ: "72/369 học viên xin tóm tắt cả buổi, 65,2% fail, nền 26,8%" so với các cách đếm theo lượt). **Hai bộ không được xuất hiện cạnh nhau trong `spec.md`.**

Luật:

1. **M3 sở hữu script đếm.** Mọi con số trong `spec.md`, slide và README đều là output của script đó, không ai gõ tay.
2. **Chốt đúng một quy tắc đếm** và ghi ra: đếm theo *lượt* hay theo *user*; "yêu cầu tóm tắt cả buổi" định nghĩa bằng regex nào; "trả lời không tìm thấy" định nghĩa bằng regex nào; chạy trên bao nhiêu mẫu.
3. **Soi tay ≥30 mẫu** để đo tỉ lệ false positive của regex, ghi con số đó vào spec. Tiêu chí nghiệm thu #2 đòi "phương pháp đếm kiểm lại được" — chính là mục này.
4. Con số nào chưa qua script M3 thì đánh dấu `[chờ M3 xác nhận]`, không đưa vào slide.

Các số **đã kiểm và an toàn để dùng ngay** (đếm trực tiếp trên file transcript, không qua regex mơ hồ):

| Số | Giá trị |
|---|---|
| Đoạn có mã `[Txx-NNN]` | 700 |
| Đoạn `[Hoạt động lớp: ...]` | 55 |
| Đoạn chứa `[không nghe rõ]` | 103 |
| Đoạn chứa lời `[Học viên]` | 69 |
| Tổng ký tự sạch (bỏ hoạt động lớp) | ~435.000 |
| Buổi nhỏ nhất / lớn nhất | 8,3k / 37,9k token |
| Section (heading `##`) toàn bộ 6 buổi | 96 |
