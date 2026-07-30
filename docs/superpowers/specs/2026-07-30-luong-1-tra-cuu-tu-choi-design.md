# Luồng 1 — tra cứu trong buổi + 4 cổng từ chối (phần M2) — Design

**Ngày:** 2026-07-30 · **Chủ:** M2 (khối E), có phần M1 (khối B) · **Hướng C**

**Quan hệ với tài liệu khác:**
- `canvas-va-luong-du-lieu.md` §5 là đặc tả gốc của luồng 1. File này là bản thiết kế thi công của §5, đã hiệu chỉnh theo số đo thật.
- `team-assignment.md` khối B + E.
- `2026-07-30-so-tay-buoi-hoc.md` là plan của luồng 2. Luồng 1 dùng lại `sotay.llm` và `sotay.verify` từ đó.
- **Chỗ nào file này lệch với canvas thì lấy file này** — lý do lệch ghi ở §0.

---

## 0. Ba chỗ số liệu trong canvas không khớp data thật

Đo lại bằng script trên `data/vlearn-pack/transcript/`, dùng regex có `## ` làm biên đoạn. Phép tự nghiệm: 645 đoạn nội dung + 55 đoạn hoạt động lớp = 700 ✓.

| # | Canvas khai | Data thật | Hệ quả thiết kế |
|---|---|---|---|
| 1 | *(không nêu)* | Regex trong plan luồng 2 **hút dòng `## ` vào thân đoạn cuối mỗi section** — 10/89 đoạn ở buổi 01, ~90 đoạn toàn corpus | `flow1/parse.py` lấy `## ` làm biên. **Báo M1 sửa `sotay/ingest.py` cho khớp** — bug này cũng làm bẩn prompt luồng 2 |
| 2 | `69 speaker=student` | **ĐÚNG — 69.** Marker có **hai dạng**: `[Học viên]:` trần (51 đoạn) và `**[Học viên]:**` in đậm (18 đoạn). Cả hai đều mở đầu đoạn. **0 đoạn** có marker chỉ ở giữa. Thêm: **18 đoạn** mở đầu `**Giảng viên:**`. Ngoài ra **59** chỗ `[học viên]` chữ thường là tên đã ẩn danh, **khác hoàn toàn** | Regex nhận `^\*{0,2}\[Học viên\]` — bỏ `\*{0,2}` là mất 18 đoạn. **Phân biệt hoa/thường.** Chỉ cần **một** field `speaker`, không có ca "trộn giọng" nào trên corpus này |
| 3 | *"có **1** đoạn ~5.000 ký tự vượt trần → tách `#a`/`#b`"* | **18 đoạn** vượt trần 1.800. Max 4.999 (`T06-059`), kế đó 3.601 (`T03-124`) | Tách đoạn khổng lồ là **đường code chạy thường xuyên**, không phải ngoại lệ hiếm — phải có test riêng, sinh ~25-30 mảnh |

Số đo tham chiếu, dùng làm assertion:

| Chỉ số | Giá trị |
|---|---|
| Đoạn có mã `[Txx-NNN]` | 700 |
| Đoạn nội dung (bỏ hoạt động lớp) | 645 |
| Đoạn `[Hoạt động lớp: ...]` | 55 |
| Đoạn chứa `[không nghe rõ]` | 103 |
| Đoạn `speaker="student"` | **69** (51 marker trần + 18 marker in đậm) |
| — theo buổi 01·02·03·04·05·06 | 8 · 0 · 19 · 0 · 21 · 21 |
| Đoạn mở đầu `**Giảng viên:**` | 18 |
| Đoạn có marker học viên **chỉ ở giữa** | **0** — không có ca trộn giọng |
| Section (`## `) toàn bộ 6 buổi | 96 (11·5·19·21·19·21) |
| Ký tự/đoạn nội dung: median · p90 · max | 606 · 1.268 · 4.999 |
| Đoạn nội dung < 300 ký tự | 147 = 23% |

---

## 1. Luồng 1 làm gì, và không làm gì

**Làm:** học viên gõ một câu hỏi về nội dung khoá → hệ thống tìm các đoạn giảng khớp → trả lời có mã đoạn bấm được, **hoặc từ chối và nói rõ mình có gì**.

**Không phải feature thứ hai của sản phẩm.** Canvas §2 đã cảnh báo điểm số: đem luồng 1 ra demo như một sản phẩm hỏi-đáp riêng thì giám khảo thấy lát cắt một câu không khớp bản build, mất điểm ở R2 (15đ). Cách khai:

- Sổ tay (luồng 2) **là** sản phẩm.
- Luồng 1 là **cổng bảo vệ** + đường đi *"hỏi sâu"* trong 4 đường đi trải nghiệm của spec §6.
- Hết giờ thì **cắt luồng 1 trước, không bao giờ cắt luồng 2**.

**Quyết định AI vẫn là một:** *đoạn giảng nào chống lưng cho khẳng định nào — và khi không đoạn nào chống lưng được thì nói ra điều đó thay vì viết tiếp.* Luồng 1 là điểm vào thứ hai của cùng quyết định đó.

---

## 2. Kiến trúc và ranh giới file

```
codebase/
├── sotay/                  ← luồng 2, chủ M1+M2. flow1 KHÔNG sửa (1 ngoại lệ, §2.3)
│   models.py  ingest.py  registry.py  verify.py  llm.py  generate.py  prompts.py
│
├── flow1/                  ← luồng 1. Cắt khi trễ = xoá thư mục, luồng 2 không hay biết
│   models.py     Seg · Chunk · Hit · Retrieval · Claim · Answer · Verdict · Intent
│   parse.py      6 file .md → list[Seg]           (bản mở rộng, đã sửa bug heading)
│   chunk.py      list[Seg] → list[Chunk]
│   index.py      list[Chunk] → store/bm25.pkl (+ emb.npy nếu có)
│   retrieve.py   query → Retrieval
│   thresholds.py T1_ABS · T1_RATIO · AMBIG_BAND · RRF_K   ← chốt bằng số, §5
│   gates.py      Cổng 0 (rule → LLM) · Cổng 1 (code thuần)
│   check.py      Cổng 3 — adapter quanh sotay.verify + ∈context + giọng học viên
│   ask.py        ghép 4 cổng; Cổng 2 nằm ở đây
│   prompts.py    prompt cổng 0 + cổng 2        ← COMMIT, giám khảo cần đọc
│   cli.py  __main__.py    python -m flow1 {index,ask}
│
├── store/        .gitignore — chunks.jsonl · bm25.pkl · emb.npy
├── scripts/calibrate_t1.py
└── tests/        test_flow1_*.py

eval/t1/
├── questions.jsonl        30 câu, 10 câu ngoài phạm vi có turn_id thật
└── distribution.md        bảng phân bố + ma trận ngưỡng   ← COMMIT
```

### 2.1 Chiều phụ thuộc một hướng

`flow1 → sotay`, không bao giờ ngược lại. `flow1` import đúng hai thứ từ `sotay`:

- `sotay.llm` — ranh giới provider duy nhất của cả dự án. **Không dựng cái thứ hai.**
- `sotay.verify` — bộ kiểm mã trích dẫn dùng chung hai luồng.

`flow1` **không** import `sotay.generate` — hai luồng không kéo nhau sập. Có test: file nào trong `sotay/**` chứa chuỗi `flow1` là fail.

### 2.2 Duck-typing thay vì kế thừa

`flow1.models.Seg` mang đúng 4 tên attribute mà `sotay.verify` đọc — `code` · `text` · `has_gap` · `is_activity` — cộng các field riêng của luồng 1. Nhờ vậy `sotay.verify` chạy trên `Seg` **không cần sửa dòng nào**. Đây là thứ làm câu "bộ kiểm dùng chung" thành sự thật trong code chứ không phải khẩu hiệu trên slide.

Lưu ý tên: canvas gọi `has_unclear`, `sotay` gọi `has_gap`. **Dùng `has_gap`** vì đó là hợp đồng dùng chung.

### 2.3 Ngoại lệ duy nhất phải sửa trong `sotay/`

`sotay.verify.verify()` có check `len(points) != 5 → wrong_point_count`. Luồng 1 trả 1-3 claim nên check đó nổ mọi lần.

**Chốt:** M1 tách phần đếm ra khỏi phần kiểm —

```python
def check_citations(points, segments) -> list[Finding]:   # không đếm số ý
def verify(notebook, segments) -> list[Finding]:          # đếm + check_citations
```

Hành vi luồng 2 không đổi; test hiện có của `test_verify.py` phải pass y nguyên. Đây là lần duy nhất luồng 1 chạm vào file của M1, và là điều kiện để "dùng chung" có thật.

---

## 3. Tầng dữ liệu (khối B)

### 3.1 `parse.py`

`Seg` — frozen dataclass, 13 field:

```python
code                str    # "T03-014"  — tên `code` để duck-type với sotay.Segment
session             str    # "03"
session_title       str
locate_confidence   str    # "cao" | "vừa" | "—"
section_idx         int
section_title       str
order               int    # thứ tự trong buổi, 1-based
text                str
speaker             str    # "instructor" | "student"
has_gap             bool
is_activity         bool
n_chars             int
```

Bốn luật parse, mỗi luật một test:

| Luật | Chi tiết |
|---|---|
| **Biên đoạn** | Đoạn kết thúc ở mã kế tiếp **hoặc dòng `## `** hoặc hết file. Assert `T01-006` không chứa `##` — đây là chỗ sửa bug §0.1 |
| **Front matter** | Bỏ mọi dòng `> ` trước khi đếm gap: chú giải front matter *có chứa* `[không nghe rõ]`. Trích `locate_confidence` từ `độ tin cậy: X`; buổi 05/06 dùng `**Buổi:**` không có trường này → `"—"` |
| **Giọng nói** | `^\*{0,2}\[Học viên\]` → `speaker="student"` (69 đoạn). Marker có **hai dạng** — `[Học viên]:` trần và `**[Học viên]:**` in đậm — bỏ `\*{0,2}` là mất 18 đoạn. `[học viên]` **thường** = tên đã ẩn danh, bỏ qua. Có test khoá: **0 đoạn** được phép có marker chỉ ở giữa; test này nổ nếu data đổi và ca trộn giọng xuất hiện |
| **Section** | Dòng `## ` tăng `section_idx`, đặt `section_title` cho mọi đoạn sau nó. **Vùng trước heading đầu tiên không rỗng** — `T02-001` và `T05-001` nằm ở đó; chúng nhận `section_idx = 0`. Bỏ vùng này là tổng ra 698/53 thay vì 700/55 |

Assert đủ bộ số §0. Cộng **một test đối chiếu ngang**: `flow1.parse` và `sotay.ingest` phải ra **danh sách mã đoạn y hệt nhau** — lệch một mã là fail. Đây cũng là câu trả lời gọn cho TA ở CP5 khi bị hỏi "sao có hai bộ parse".

### 3.2 `chunk.py`

1. Đoạn `[Txx-NNN]` là **nguyên tử** — không cắt ngang khi gộp. Mã đoạn là citation unit.
2. Gộp đoạn liền kề **trong cùng section**, target ~1.100 ký tự, trần cứng 1.800.
3. **Không gộp qua section, không gộp qua buổi.**
4. **Overlap 1 đoạn** giữa hai chunk liền kề cùng section.
5. **18 đoạn vượt trần** tách theo câu (biên `. ` `! ` `? ` và hết đoạn) thành `T06-059#a`, `#b`… — nhưng `cite_code` của mọi mảnh **vẫn là mã gốc** `T06-059`. Sinh ~25-30 mảnh.
6. Bỏ 55 đoạn `is_activity` khỏi chunk.

```python
Chunk(chunk_id, session, session_title, section_idx, section_title,
      text, seg_codes: list[str], has_gap: bool, n_chars: int)
```

`seg_codes` là **mã gốc đã dedupe** — cổng 3 dùng nó để kiểm `cite ∈ context`.

**Số đo thật sau khi thi công** (canvas ước ~400; đo thật bằng `chunk_all(content_segs(parse_all()))`):

| Chỉ số | Giá trị |
|---|---|
| Số chunk | **419** |
| Ký tự/chunk: median · p90 | 1.319 · 1.686 |
| Đoạn/chunk (median) | 2 |
| Mảnh tách `#a`/`#b` từ 18 đoạn khổng lồ | 38 |
| Cặp chunk liền kề còn overlap 1 đoạn | 165 |
| Đoạn nội dung được phủ | **645/645** — không mất đoạn nào |

**Không hardcode con số này vào test** — assert khoảng `[300, 550]`.

Hai luật bổ sung phát hiện khi thi công, cả hai đã có test trên corpus thật:

7. **Tính cả overhead nối chuỗi khi quyết định gộp.** `Chunk.text` nối bằng `"\n\n"`, nên bỏ qua 2 ký tự đó làm `T04-016` ra chunk 1.806 ký tự — vượt trần cứng. Cộng `len("\n\n")` vào phép tính kích thước.
8. **Không phát chunk chỉ chứa đúng đoạn overlap.** Khi đoạn overlap một mình đã ≥ target, hoặc bị chặn không gộp tiếp vì hàng xóm là đoạn khổng lồ, thuật toán gốc sinh ra một chunk không mang nội dung mới nào — **49 chunk** như vậy trên corpus, tức ~12% index BM25 bị nhân bản và một đoạn được đánh trọng số hai lần. Bất biến: không chunk nào có `seg_codes` là tập con của chunk liền trước, *trừ* các mảnh `#a`/`#b` cùng mã gốc.

### 3.3 `index.py`

BM25 (`rank_bm25`) trên:

```python
index_text = f"{session_title} › {section_title}\n{chunk_text}"
```

Prefix heading là **bắt buộc**: 23% đoạn nội dung dưới 300 ký tự, đứng một mình không đủ ngữ cảnh để match.

Tokenizer: lowercase → bỏ dấu câu → split whitespace. Tiếng Việt tách âm tiết theo space nên BM25 khớp được từ khoá; bộ câu hỏi của khoá này lẫn nhiều thuật ngữ Anh (`RAG`, `attention`, `tool calling`, `embedding`) — đúng chỗ BM25 mạnh nhất.

**Embedding:** `multilingual-e5-small` **chạy local** (~470MB, CPU thừa sức cho ~400 chunk), ghi `store/emb.npy`. Không byte transcript nào rời máy — đúng điều 4 mục bảo mật data, và giữ được lập luận đó ở CP5.

Hợp nhất bằng **RRF** `score = Σ 1/(RRF_K + rank_i)`, không cộng điểm thô: BM25 và cosine không cùng thang, cộng thẳng là so hai đơn vị khác nhau.

**Thiếu `emb.npy` → tự lùi về BM25 thuần, in một dòng ghi chú, không crash.** Đường cắt #1 trong danh sách cắt vẫn còn nguyên.

---

## 4. Bốn cổng từ chối

```
câu hỏi
   │
   ▼ CỔNG 0 — phân loại ý định: rule trước, LLM bắt phần còn lại
   │   nội_dung_khoá | logistics | ngoài_phạm_vi | chào_hỏi
   │   → 3 nhãn sau: khuôn mẫu, KHÔNG retrieve, KHÔNG generate          [lớp ③]
   ▼
   ▼ retrieve top-5 (BM25 [+ embedding qua RRF])
   ▼
   ▼ CỔNG 1 — CODE, TRƯỚC generate
   │   top1_abs < T1_ABS  HOẶC  ratio < T1_RATIO  → TỪ CHỐI CỨNG        [lớp ①]
   │   top2/top1 ≥ AMBIG_BAND  VÀ  khác buổi     → HỎI LẠI 1 câu        [lớp ②]
   ▼
   ▼ CỔNG 2 — LLM, output JSON có schema
   │   status: answered | insufficient | out_of_scope
   ▼
   ▼ CỔNG 3 — CODE, SAU generate                                        [lớp ①④]
   │   sotay.verify.check_citations  +  cite ∈ context  +  nhãn giọng  +  cờ gap
   ▼
hiển thị: mỗi claim + [mã] + nguyên văn đoạn ngay bên dưới
```

### 4.1 Cổng 0 — rule trước, LLM sau

Rule chạy trên query đã normalize (lowercase, bỏ dấu câu). **Mọi pattern phải đào từ chatlog thật và ghi kèm `turn_id` đã thúc nó ra đời** — vừa là bằng chứng cho R4, vừa chặn việc bịa rule cho vui.

| Nhãn | Rule | Ví dụ thật từ chatlog |
|---|---|---|
| `chào_hỏi` | query ∈ tập đóng nhỏ các câu chào/cảm ơn | `"hi"`, `"cảm ơn"` |
| `ngoài_phạm_vi` | hỏi về chính con bot (`bạn là gpt\|claude\|gemini`, `model nào`, `pretrain`) · xin đáp án (`đáp án\|lời giải` + `lab\|bài tập\|quiz`) | *"bạn là gpt hay claude hay gemini"* · *"cho tôi biết đáp án bài lab 1 được không"* · *"Which model do the tutor pretrain on?"* |
| `logistics` | `deadline\|hạn nộp\|nộp bài\|nộp ở đâu\|link\|lịch học\|điểm danh` | — |
| `nội_dung_khoá` | mặc định khi không rule nào khớp | — |

Không rule nào khớp → **1 LLM call rẻ** phân loại, schema `Intent(label, reason)`, qua `sotay.llm.complete_json`.

Ba nhãn ≠ `nội_dung_khoá` → trả câu khuôn mẫu, **không retrieve, không generate**. Với `logistics` và `ngoài_phạm_vi`, câu trả lời nói rõ *mình làm gì* và *chỗ nào hỏi được* — không phải "tôi không hiểu".

### 4.2 Cổng 1 — code thuần, trước generate

`retrieve.py` trả sẵn mọi thứ cổng 1 cần, để cổng 1 không tự tính lại:

```python
Hit(chunk: Chunk, bm25: float, emb: float | None, rank: int, score: float)
    # .session, .section_title  = property đọc xuyên qua .chunk
Retrieval(hits: list[Hit],        # đã sắp theo score (RRF nếu có emb, BM25 nếu không)
          top1_abs: float,        # LUÔN là điểm BM25 thô cao nhất
          ratio: float,           # LUÔN tính trên điểm BM25 thô
          sessions: list[str])
```

> ⚠ **Cổng 1 luôn quyết định trên điểm BM25 thô, không bao giờ trên điểm đã fuse.**
> Điểm RRF là `1/(RRF_K + rank)` — một dãy gần như cố định: top1 = 1/61, top2 = 1/62, nên `ratio` sau fuse **luôn ≈ 1,02 bất kể câu hỏi là gì**. Tính cổng 1 trên điểm fuse là làm cổng 1 chết im lặng đúng vào lúc bật hybrid.
> Hệ quả tốt: **T1 hiệu chỉnh một lần là dùng được cho cả hai chế độ** — bật/tắt embedding không làm bảng phân bố ở §5 mất hiệu lực. RRF chỉ đổi *thứ tự nạp chunk vào context*, không đổi *quyết định có đủ căn cứ hay không*.

`ratio = bm25_sorted[0] / mean(bm25_sorted[1:5])` · `AMBIG_BAND` cũng so trên `bm25_sorted`.

**Hai ngưỡng, vì chúng bị lỗ hổng ở hai hướng khác nhau:**

- `ratio` đo **độ nhọn**, không đo độ liên quan. Câu ngoài phạm vi chứa đúng một token hiếm (`lab`, `pretrain`) chỉ khớp 1 chunk → ratio rất cao → lọt.
- `top1_abs` đo **độ khớp thô**, không đo tính riêng biệt. Câu chung chung khớp lem nhem nhiều chunk → abs khá cao → lọt.

Chặn nếu **một trong hai** dưới ngưỡng. Lọt cả hai là khó.

Hai ca biên phải có test — đây là chỗ code retrieval hay chết âm thầm:

| Ca | Xử lý |
|---|---|
| Mọi điểm = 0 (không token nào khớp) | `top1_abs = ratio = 0.0` → chặn |
| `mean(top2..5) = 0` mà `top1 > 0` (đúng 1 chunk khớp) | `ratio = inf` → qua cổng ratio, **sàn tuyệt đối vẫn chặn** |
| Ít hơn 5 hit | mean tính trên số hit có thật |

**Từ chối vẫn phải mang thông tin.** Lúc chặn, ta *đã có* 5 hit trong tay → câu từ chối liệt kê `section_title` của 3 hit đầu kèm số buổi:

> *"Nội dung này không có trong 6 buổi mình có. Gần nhất là: Buổi 04 › Cách LLM sinh token · Buổi 06 › Cơ chế attention · Buổi 03 › Giới hạn của LLM, tool calling và RAG"*

Đây là chỗ trỏ vào **HAX G2 — làm rõ nó làm tốt đến đâu**, chứ không phải một ngõ cụt.

**Mơ hồ đa buổi:** `top2/top1 ≥ AMBIG_BAND` **và** `hits[0].session != hits[1].session` → hỏi lại đúng một câu, nêu tên hai buổi.

### 4.3 Cổng 2 — LLM có schema

```python
class Claim(BaseModel):
    text: str
    cite: list[str]                              # mã đoạn gốc
    speaker: Literal["instructor", "student"]

class Answer(BaseModel):
    status: Literal["answered", "insufficient", "out_of_scope"]
    claims: list[Claim]
    gaps: list[str]
```

Context = 5 chunk, mỗi chunk gắn nhãn mã đoạn gốc của nó. Prompt nói rõ: **model được phép và được khen khi tự khai `insufficient`** — khai không đủ căn cứ là hành vi đúng, không phải thất bại.

### 4.4 Cổng 3 — code thuần, sau generate

`check.py` trả `Verdict(kept_claims, dropped, labels, gap_notes, status)`:

| Kiểm | Cơ chế | Vi phạm thì làm gì |
|---|---|---|
| Mã ∈ 700 mã thật | `sotay.verify.check_citations` | **Loại claim đó**, ghi lại, **không tự sửa** |
| Mã ∈ tập chunk đã đưa vào context | union `seg_codes` của 5 hit | Loại claim, kind `outside_context` |
| Đoạn `speaker="student"` | 69 đoạn | **Buộc** gắn nhãn *"một học viên nêu"* |
| Đoạn `has_gap` | 103 đoạn | Chèn *"⚠ bản ghi đoạn này thiếu"* |

Kiểm thứ hai là **riêng của luồng 1** — luồng 2 nạp cả buổi nên "∈ context" trùng với "∈ 700 mã"; luồng 1 chỉ đưa 5 chunk nên mã thật *nhưng không có trong context* vẫn là bịa.

Nhãn giọng học viên do **code** quyết định, không do model tự khai — model khai `speaker` gì thì `speaker` trong `Seg` vẫn thắng. Đây là lớp ④ cụ thể hoá bằng kỹ thuật, không phải bằng một dòng trong prompt. 69/645 đoạn nội dung là lời học viên (10,7%), nên đây không phải ca hiếm.

**Loại hết claim → `status` chuyển `insufficient`.** Không được trả về danh sách rỗng rồi im lặng.

### 4.5 Bốn đường đi trải nghiệm (R3, 3đ)

| Đường | Kích hoạt | Kết quả |
|---|---|---|
| **happy** | cổng 0 `nội_dung_khoá`, qua cổng 1, cổng 3 sạch | `answered` + mã + nguyên văn |
| **low-confidence** | ratio/abs dưới ngưỡng, hoặc mơ hồ đa buổi | từ chối kèm 3 heading, hoặc hỏi lại 1 câu |
| **failure** | cổng 3 loại claim | `insufficient` + mục "ý đã bị loại" |
| **correction** | người dùng trả lời câu hỏi lại | `ask --session 02 "..."` chạy lại có lọc buổi |

Cờ `--session` tồn tại **vì** đường correction: hỏi lại mà người dùng không có cách trả lời thì đường đi đó chỉ có trên giấy.

---

## 5. Hiệu chỉnh T1 bằng số

`scripts/calibrate_t1.py`, input `eval/t1/questions.jsonl` — 30 dòng:

```json
{"id": "Q01", "text": "...", "expect": "in_scope", "source": "người soạn"}
{"id": "Q21", "text": "cho tôi biết đáp án bài lab 1 được không", "expect": "out_of_scope", "source": "chatlog:T0408"}
```

20 câu trong phạm vi + **10 câu ngoài phạm vi bắt buộc lấy thật từ chatlog, có `turn_id`**.

Script làm 3 việc:

1. Chạy retrieve cả 30 câu, in bảng `id · text · expect · top1_abs · ratio · buổi top1 · section top1`.
2. **Quét lưới** `T1_ABS × T1_RATIO`, in ma trận: mỗi cặp → `(chặn ngoài-phạm-vi /10, qua trong-phạm-vi /20)`.
3. Đề xuất cặp: **ưu tiên chặn hết ngoài phạm vi trước**, rồi tối đa hoá câu trong phạm vi qua được.

Ghi ra `eval/t1/distribution.md` (commit). Ngưỡng chốt vào `flow1/thresholds.py` — **một file duy nhất** để CP5 chỉ tay vào được.

Vào spec §7 theo **khuôn** này (số dưới đây là ví dụ khuôn dạng, **không phải kết quả** — giá trị thật do bước 9 đo ra):

> *"T1_ABS = ⟨đo⟩ · T1_RATIO = ⟨đo⟩ — ở cặp này ⟨n⟩/10 câu ngoài phạm vi bị chặn, ⟨m⟩/20 câu trong phạm vi qua."*

**Luật trung thực:** nếu hai phân bố chồng nhau không tách được, **ghi thật là không tách được** + hệ quả kèm theo. Không chọn một ngưỡng nhìn đẹp rồi im. Bảng phân bố đó là artifact mạnh cho R4 kể cả khi kết quả không đẹp.

---

## 6. Xử lý lỗi — hướng fail bất đối xứng, có chủ ý

| Lỗi | Xử lý |
|---|---|
| `store/bm25.pkl` thiếu | báo chạy `python -m flow1 index` trước, exit 3 |
| `store/emb.npy` thiếu | **lùi êm** về BM25 thuần + in một dòng ghi chú |
| **Cổng 0 LLM lỗi/timeout** | **fail MỞ** — coi là `nội_dung_khoá`, đi tiếp xuống cổng 1 |
| **Cổng 2 LLM lỗi** | **fail ĐÓNG** — `status=insufficient`, in lỗi, exit 1 |
| Model trả JSON sai schema | `sotay.llm` raise `LlmError`, bắt ở `ask.py` |
| Query rỗng | cổng 0 rule → `chào_hỏi` |
| Query 1 từ | xuống cổng 1; ratio/abs thường thấp → chặn. Có case trong golden set |

Bất đối xứng có lý do: cổng 0 chỉ **phân loại**, hỏng nó thì cổng 1 tất định vẫn đứng sau. Cổng 2 **sinh nội dung**, hỏng nó mà đi tiếp là mở đường cho đúng thứ cả sản phẩm đang phòng.

---

## 7. Kiểm thử

Mỗi module một file test. Nguyên tắc chung:

- **Không test nào gọi mạng.** Cổng 0 và cổng 2 nhận `call=` inject được, y hệt `build_notebook` của luồng 2.
- Test đọc data thật → `pytest.skip` nếu thiếu data pack (repo nộp bài không chứa `data/`).
- Không hardcode số chunk; assert khoảng.

Test kiến trúc — chúng giữ cho §2 không mục theo thời gian:

| Test | Assert |
|---|---|
| `sotay` không biết `flow1` | không file nào trong `sotay/**` chứa chuỗi `flow1` |
| `flow1` không kéo luồng 2 | `flow1/**` không import `sotay.generate` |
| Bộ kiểm dùng chung là thật | `flow1/check.py` có import `sotay.verify` |
| Hai parser không lệch | `flow1.parse` và `sotay.ingest` ra danh sách mã y hệt |
| Luồng 2 không đổi hành vi | `tests/test_verify.py` cũ pass y nguyên sau khi tách `check_citations` |

---

## 8. Thứ tự thi công và điểm cắt

| Bước | Chủ | Cắt được? |
|---|---|---|
| 1. `models.py` + `parse.py` + test | M1 | không — nền của cả khối |
| 2. `chunk.py` + test | M1 | không |
| 3. `index.py` BM25 + `retrieve.py` + test | M1 | không |
| 4. `thresholds.py` (giá trị tạm) + `gates.py` cổng 1 + test | M2 | không |
| 5. `prompts.py` + `gates.py` cổng 0 + test | M2 | rule giữ, phần LLM cắt được |
| 6. `check.py` cổng 3 + test | M2 | **không bao giờ cắt** |
| 7. `ask.py` cổng 2 + ghép + test | M2 | không |
| 8. `cli.py` + `__main__.py` | M2 → M4 | `--session` cắt được (mất đường correction) |
| 9. `calibrate_t1.py` + 30 câu + chốt ngưỡng | M2 | không — artifact R4 |
| 10. Embedding + RRF | M2 | **cắt đầu tiên** khi trễ |

Điểm cắt thô nhất: **xoá cả `flow1/`**. Luồng 2 chạy y nguyên, chỉ mất một đường đi trong spec §6. Đó là lý do thư mục nằm riêng.

---

## 9. Quyết định: KHÔNG nối luồng 1 vào graph Neo4j

Nhóm có một instance Neo4j Aura chứa transcript dưới dạng node `Turn` (`id` = mã đoạn `Txx-NNN`, `speaker_role`, `is_question`, `content`). Nó trùng phạm vi với tầng dữ liệu ở §3, nên phải nói rõ vì sao luồng 1 không dùng.

**Ba lý do, theo thứ tự sức nặng:**

1. **Bản sao trong graph đã mất dữ liệu.** `T03-062` trong Neo4j là `"**** Em nghĩ..."`, transcript thật là `"**[Học viên]:** Em nghĩ..."` — bước nạp đã nuốt marker `[Học viên]`. Luồng 1 in **nguyên văn đoạn ngay dưới mỗi khẳng định** để người đọc kiểm tại chỗ; in `****` là hỏng đúng chiều đo *truy vết* của quality bar. Đáng chú ý: chính marker in đậm này là thứ làm bộ đếm của tôi sai ở §0.2 — nó khó thấy ở cả hai phía.
2. **Canvas §4.2 đã chốt ngược lại, bằng lý do có tên:** *"Với ~400 chunk thì mọi thứ chạy trong RAM. Không dựng Chroma/FAISS/Docker — thêm 2 tiếng setup, không thêm điểm nào, và CP5 lại phải giải thích thứ mình không viết."*
3. **Bảo mật data — cần nhóm tự quyết.** `data/vlearn-pack/transcript/README.md` mục "Luật dùng & bảo mật": *"chỉ dùng trong phạm vi hackathon · không chia sẻ ra ngoài khoá · không commit nguyên file vào repo nộp bài"*. Một instance hosted chứa toàn văn 700 đoạn là transcript nằm trên hạ tầng bên thứ ba. Có vi phạm hay không tuỳ instance đó có được tính là "trong phạm vi khoá" — nhóm biết, tài liệu này không.

**Chỗ graph có ích:** phía **M3**, không phải luồng 1. Truy vấn kiểu *"đoạn nào là lời học viên trong buổi 03"* hoặc *"đoạn nào là câu hỏi"* bằng Cypher nhanh hơn viết script — hữu ích khi M5 gán nhãn 18 ý vàng và khi M3 dựng golden set.

**Ranh giới cứng:** nguồn sự thật cho **mã trích dẫn** vẫn là 6 file `.md`. `flow1.check` kiểm mã bằng `parse_all()` đọc file, không qua mạng. Nếu graph và file lệch nhau thì **file đúng**.

---

## 10. Rủi ro đã biết

| Rủi ro | Dấu hiệu | Đường lùi |
|---|---|---|
| Hai phân bố T1 chồng nhau không tách được | ma trận không có cặp nào đạt 10/10 mà giữ được ≥15/20 | Ghi thật; dựa nhiều hơn vào cổng 0 rule; nêu đây là giới hạn đã biết trong spec §6 |
| BM25 kém với câu hỏi diễn đạt vòng | nhiều câu in-scope có ratio thấp | Bật embedding (bước 10) — đây là lý do giữ nó trong plan |
| M1 chậm ở khối B, M2 nghẽn | 3 bước đầu chưa xong khi tới CP4 | M2 làm bước 4-6 trên `Seg` dựng tay trong test trước, ghép sau |
| Bug parse của luồng 2 không được sửa | `sotay.ingest` vẫn hút heading | Test đối chiếu ngang **sẽ fail** — nó là cái phanh, không phải chỗ để tắt đi |
| `multilingual-e5-small` tải chậm/hỏng ở sự kiện | pip/tải model treo | Bước 10 là bước cắt đầu tiên; BM25 đã đủ điều kiện tính điểm R5 vì lời gọi AI thật nằm ở cổng 2 |
