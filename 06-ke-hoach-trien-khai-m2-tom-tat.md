# Kế hoạch triển khai M2 — Luồng Tóm tắt (Summarization)

## 1. Thông tin tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Hạng mục | M2 — Summarization Layer |
| Phụ thuộc | M1 (Vector DB / Retrieval Layer) — xem `05-ke-hoach-trien-khai-m1-vector-db.md` |
| Bài toán | Tóm tắt buổi học / mục học từ transcript sạch, có citation truy ngược |
| Chiến lược | Hierarchical Map–Reduce, precompute ở build time |
| LLM provider | OpenAI |
| Model map (section) | `gpt-4o-mini` |
| Model reduce (session) | `gpt-4o` |
| Output | JSON có schema + Markdown render |
| Trạng thái | Kế hoạch triển khai |

---

## 2. Phạm vi sau khi cắt gọn

Hệ thống chốt **3 luồng**, bỏ `COMPARISON` và `RECOMMEND`:

| Luồng | Giữ | Nguồn dữ liệu | Tài liệu |
|---|---|---|---|
| `SEARCH` — hỏi–đáp có citation | ✅ | Vector DB (atomic chunk) | M1 §10 |
| `SUMMARY` — tóm tắt buổi/mục | ✅ | Vector DB (structured reader) | **Tài liệu này** |
| `GRAPH` — quan hệ khái niệm / định vị buổi | ✅ | Neo4j + TOC vector | M3 |
| `COMPARISON` | ❌ bỏ | — | — |
| `RECOMMEND` | ❌ bỏ | — | — |

Việc bỏ 2 luồng kia gỡ được toàn bộ phụ thuộc vào `RELATED_TO {type: prerequisite}` và `Lecture.order` — hai thứ trong `FLOW_IMPLEMENTATION.md` không có cách sinh ra đáng tin từ transcript, mà chỉ do LLM đoán.

---

## 3. Tóm tắt điều hành

M2 nhận đầu vào là nội dung transcript **đầy đủ và đúng thứ tự** do M1 cung cấp, và sản xuất bản tóm tắt có cấu trúc, mọi ý đều gắn citation `TXX-NNN`.

Ba quyết định kiến trúc chính:

1. **Không dùng semantic top-k làm input cho tóm tắt.** Tóm tắt buổi phải đọc đủ 100% chunk của buổi qua structured reader. Top-k chỉ dùng để *định vị* scope, không dùng để *lấy nội dung*.
2. **Map–Reduce theo section.** Mỗi section là một đơn vị map. Section summary vừa là sản phẩm trung gian của tóm tắt buổi, vừa là câu trả lời trực tiếp cho yêu cầu "tóm tắt mục X".
3. **Precompute ở build time, không sinh lúc demo.** Toàn bộ 96 section summary được sinh một lần khi ingest, cache theo `content_hash`, ghi ngược vào payload Qdrant. Lúc demo chỉ còn 1 lần gọi LLM cho bước reduce.

Hệ quả của quyết định (3): tóm tắt mục = 0 lần gọi LLM (tra payload), tóm tắt buổi = 1 lần gọi LLM (~3s), chi phí xác định trước, không phụ thuộc rate limit khi trình bày.

---

## 4. Khảo sát dữ liệu nguồn

| Session | Sections | Atomic chunks | Words | Ước tính tokens |
|---|---|---|---|---|
| T01 | 11 | 89 | 14.046 | ~28.000 |
| T02 | 5 | 43 | 5.910 | ~12.000 |
| T03 | 19 | 154 | 25.419 | ~51.000 |
| T04 | 21 | 98 | 19.541 | ~39.000 |
| T05 | 19 | 154 | 17.053 | ~34.000 |
| T06 | 21 | 162 | 17.369 | ~35.000 |
| **Tổng** | **96** | **700** | **99.338** | **~199.000** |

Ước tính tokens dùng hệ số ~2.0 token/từ cho tiếng Việt với tokenizer OpenAI — phải đo lại bằng `tiktoken` ở Giai đoạn 1, không được lấy con số này làm cam kết.

Marker đặc biệt trong corpus:

| Marker | Số lần | Xử lý |
|---|---|---|
| `[không nghe rõ]` | 131 | Không suy diễn nội dung thiếu. Đánh dấu `has_unclear` ở section summary. |
| `[Hoạt động lớp: ...]` | 61 | Loại khỏi nội dung tóm tắt kiến thức, **vẫn tính vào coverage**. |
| `[học viên]` | nhiều | Giữ nguyên vai. Không được gán lời học viên thành phát biểu của giảng viên. |

### 4.1. Nhận xét về phân bố

T03 một mình chiếm 25% corpus và có section dài nhất. Nếu chọn hướng "nhồi cả buổi vào một prompt", T03 là ca sẽ hỏng trước. Map–Reduce theo section làm phẳng rủi ro này: section dài nhất mới là đơn vị cần lo, không phải buổi dài nhất.

---

## 5. Ba loại tóm tắt

| Mã | Loại | Câu hỏi mẫu | Scope | Nguồn nội dung |
|---|---|---|---|---|
| `S1` | Session summary | "Tóm tắt buổi T03", "Buổi chiều ngày 2 nói gì?" | 1 session | Structured reader — đủ 100% chunk |
| `S2` | Section summary | "Tóm tắt mục nói về giới hạn của LLM" | 1 section | Structured reader — đủ chunk của section |
| `S3` | Topic summary | "Tổng hợp mọi thứ về RAG trong khoá" | nhiều session | Semantic retrieval + gom nhóm |

**Ưu tiên triển khai: S2 → S1 → S3.**

S2 là nền của S1 (map step). S3 là loại duy nhất được phép dùng semantic top-k, vì bản chất nó là "tóm tắt kết quả tìm kiếm", và nó **phải tự khai báo là không đảm bảo đầy đủ**. Nếu thiếu thời gian, cắt S3 trước.

---

## 6. Kiến trúc luồng tóm tắt

```text
User query: "Tóm tắt buổi chiều ngày 2"
    │
    ▼
┌─────────────────────────────────────────────┐
│ STEP 1 — SCOPE RESOLUTION                   │
│  - session_id tường minh?      → dùng luôn  │
│  - mô tả tự nhiên?             → find_sessions() trên TOC vector
│  - mô tả mục?                  → find_sections() trong session
│  - mơ hồ (nhiều buổi sát điểm) → needs_clarification
└─────────────────────────────────────────────┘
    │  scope = {session_id: "T03", section_id: None, summary_type: "S1"}
    ▼
┌─────────────────────────────────────────────┐
│ STEP 2 — STRUCTURED LOAD  (KHÔNG semantic)  │
│   get_session_outline(session_id)           │
│   get_session_sections(session_id)          │
│   get_section_content(section_id) × N       │
│  → 19 sections, 154 chunks, đúng thứ tự     │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ STEP 3 — MAP: tóm tắt từng section          │
│   cache hit theo content_hash?              │
│     ├── có  → lấy summary đã precompute     │
│     └── không → gọi LLM (gpt-4o-mini)       │
│   output: SectionSummary có citations       │
└─────────────────────────────────────────────┘
    │  19 × SectionSummary
    ▼
┌─────────────────────────────────────────────┐
│ STEP 4 — VALIDATE (deterministic, no LLM)   │
│   - mọi citation tồn tại trong scope?       │
│   - mọi section có ≥1 dòng trong output?    │
│   - không có citation ngoài session?        │
│   - coverage = covered/total                │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ STEP 5 — REDUCE: tổng hợp session summary   │
│   input: 19 section summary (KHÔNG phải     │
│          transcript gốc)                    │
│   model: gpt-4o                             │
│   output: tldr + key_points + outline       │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ STEP 6 — VALIDATE lần 2 + RENDER            │
│   JSON contract → Markdown / UI             │
└─────────────────────────────────────────────┘
```

### 6.1. Vì sao reduce đọc section summary chứ không đọc transcript gốc

Nếu bước reduce đọc lại toàn bộ 51.000 token của T03, ta mất luôn lợi ích của map và quay về bài toán context dài, đồng thời không kiểm soát được việc model thiên vị phần đầu prompt. Đọc 19 bản tóm tắt (~4.000 token) cho kết quả cân bằng giữa các section và rẻ hơn một bậc.

Đánh đổi: chi tiết cấp câu bị mất ở bước reduce. Bù lại bằng cách bắt buộc mỗi `key_point` mang citation trỏ về chunk gốc, và UI cho phép mở rộng xuống section summary → chunk gốc.

---

## 7. Contract đầu ra

### 7.1. `SectionSummary`

```json
{
  "schema_version": "1.0",
  "summary_type": "section",
  "session_id": "T03",
  "section_id": "T03-SEC-004",
  "section_title": "Giới hạn của LLM, tool calling và RAG",
  "section_order": 4,

  "abstract": "Giảng viên chỉ ra ba giới hạn cốt lõi của LLM và cách bù bằng tool calling và RAG.",

  "key_points": [
    {
      "text": "LLM không tự truy cập dữ liệu ngoài thời điểm huấn luyện.",
      "citations": ["T03-034"]
    },
    {
      "text": "Tool calling để LLM gọi hệ thống ngoài thay vì tự bịa số liệu.",
      "citations": ["T03-035", "T03-036"]
    }
  ],

  "concepts": ["tool calling", "RAG", "context window"],
  "examples": [
    { "text": "Case lập kế hoạch du lịch", "citations": ["T03-035"] }
  ],
  "student_questions": [
    { "text": "RAG có thay được fine-tuning không?", "citations": ["T03-036"] }
  ],

  "source_chunk_ids": ["T03-034", "T03-035", "T03-036"],
  "covered_chunk_ids": ["T03-034", "T03-035", "T03-036"],
  "has_unclear": false,
  "unclear_chunk_ids": [],
  "activity_chunk_ids": [],

  "content_hash": "sha256:...",
  "model": "gpt-4o-mini",
  "generated_at": "2026-07-30T10:00:00Z"
}
```

### 7.2. `SessionSummary`

```json
{
  "schema_version": "1.0",
  "summary_type": "session",
  "session_id": "T03",
  "session_locator": "Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc",

  "tldr": "Buổi tập trung vào việc soi lại bài toán của từng nhóm, tách phần deterministic khỏi LLM và dựng con số chi phí vận hành trước khi trình lãnh đạo.",

  "key_points": [
    { "text": "...", "citations": ["T03-034"], "section_id": "T03-SEC-004" }
  ],

  "outline": [
    {
      "section_id": "T03-SEC-004",
      "section_order": 4,
      "section_title": "Giới hạn của LLM, tool calling và RAG",
      "abstract": "...",
      "citations": ["T03-034", "T03-036"]
    }
  ],

  "concepts": ["tool calling", "RAG", "ODD", "deterministic"],
  "open_questions": [{ "text": "...", "citations": ["T03-141"] }],

  "coverage": {
    "total_sections": 19,
    "covered_sections": 19,
    "total_chunks": 154,
    "cited_chunks": 61,
    "unclear_chunks": 7,
    "activity_chunks": 12
  },

  "warnings": [
    "Mục 9 có 3 đoạn [không nghe rõ]; nội dung tóm tắt có thể thiếu."
  ],

  "model": { "map": "gpt-4o-mini", "reduce": "gpt-4o" },
  "generated_at": "2026-07-30T10:00:00Z"
}
```

### 7.3. Nguyên tắc của contract

- `citations` là bắt buộc ở mọi `key_point`, `example`, `student_question`. Mảng rỗng → item bị loại ở bước validate.
- `coverage` là số liệu **đo được**, không phải LLM tự khai. Do validator tính.
- `warnings` do validator sinh, không phải LLM viết.
- `covered_chunk_ids ⊆ source_chunk_ids` — kiểm tra bằng code.

---

## 8. Quy tắc chống bịa (grounding rules)

Đây là phần quyết định điểm số, không phải phần prompt cho đẹp.

| # | Quy tắc | Cách thực thi |
|---|---|---|
| 1 | Mọi ý phải có citation trỏ đúng chunk trong scope | Validator regex + set membership. Vi phạm → loại item, ghi log. |
| 2 | Không trộn nội dung giữa các buổi | Citation ngoài `session_id` → **fail build**, không phải warning. |
| 3 | Lời học viên không được ghi thành lời giảng viên | Prompt truyền `speaker` từng chunk; section summary tách `student_questions` riêng. |
| 4 | `[không nghe rõ]` không được suy diễn | Prompt cấm; `has_unclear=true` sinh warning tự động. |
| 5 | `[Hoạt động lớp]` không vào nội dung kiến thức | Lọc trước khi vào prompt; vẫn đếm trong coverage. |
| 6 | Không thêm kiến thức ngoài transcript | Prompt cấm + eval groundedness lấy mẫu. |
| 7 | Không bỏ sót section | Validator: mọi `section_id` phải xuất hiện trong `outline`. Thiếu → fail. |

### 8.1. Vì sao validator phải deterministic

Nếu dùng LLM-as-judge để kiểm tra citation, ta có hai nguồn sai thay vì một. Kiểm tra `citation_id ∈ source_chunk_ids` là phép so sánh tập hợp, viết 10 dòng Python, chạy 0ms, đúng 100%. LLM-as-judge chỉ dùng cho `groundedness` — thứ không kiểm được bằng string matching, và chỉ chạy trên mẫu ở khâu eval.

---

## 9. Thiết kế prompt

### 9.1. Map prompt — tóm tắt section

Input dựng từ chunk đã sắp thứ tự, giữ nguyên ID và vai:

```text
BUỔI: Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc
MỤC 4/19: Giới hạn của LLM, tool calling và RAG

[T03-034] (giảng viên) Nội dung nguyên văn...
[T03-035] (giảng viên) Nội dung nguyên văn...
[T03-036] (học viên) Nội dung nguyên văn...
```

Ràng buộc trong system prompt:

1. Chỉ dùng thông tin trong đoạn transcript được cung cấp.
2. Mỗi ý phải kèm ít nhất một mã `TXX-NNN` lấy từ chính đoạn trên.
3. Không được tạo mã citation không xuất hiện trong input.
4. Phân biệt rõ lời giảng viên và lời học viên; câu hỏi của học viên đưa vào `student_questions`.
5. Gặp `[không nghe rõ]` thì bỏ qua, không đoán nội dung.
6. Trả về JSON đúng schema `SectionSummary` (dùng structured output).
7. Ngôn ngữ: tiếng Việt, văn phong trung tính, không tự xưng.

### 9.2. Reduce prompt — tóm tắt session

Input là danh sách section summary theo đúng `section_order`, mỗi mục kèm citation sẵn có. Ràng buộc thêm so với map:

1. `outline` phải liệt kê **đủ và đúng thứ tự** mọi mục được cung cấp; không gộp, không bỏ.
2. `key_points` chọn 5–8 ý quan trọng nhất toàn buổi, mỗi ý giữ nguyên citation từ section nguồn.
3. `tldr` 2–3 câu, phải phản ánh mục có trọng số lớn, không chỉ mục đầu.
4. Không tạo citation mới ngoài tập citation của các section summary.

### 9.3. Tham số

| Bước | Model | Temperature | Response format |
|---|---|---|---|
| Map | `gpt-4o-mini` | 0.2 | `json_schema` (strict) |
| Reduce | `gpt-4o` | 0.3 | `json_schema` (strict) |

Temperature thấp vì đây là tác vụ trích xuất, không phải sáng tác. Dùng `json_schema` strict thay vì `json_object` để không phải viết code sửa JSON hỏng.

---

## 10. Precompute và cache

### 10.1. Build time

```powershell
uv run python -m summarizer.build            # sinh mọi section summary còn thiếu
uv run python -m summarizer.build --session T03
uv run python -m summarizer.build --force    # bỏ qua cache, sinh lại
```

Luồng build:

```text
load parsed sessions (từ M1)
→ với mỗi section:
     content_hash = sha256(nội dung canonical của section)
     cache hit?  → skip
     cache miss? → gọi LLM map → validate → ghi cache
→ ghi summary vào:
     artifacts/summaries/{session_id}/{section_id}.json
     payload Qdrant: section_parent.section_summary
→ ghi manifest
```

### 10.2. Cache

Khoá cache = `sha256(content_hash + prompt_version + model)`.

Ba thành phần đều phải nằm trong khoá:

- `content_hash` — transcript sửa thì phải sinh lại.
- `prompt_version` — sửa prompt mà không đổi khoá là lỗi kinh điển: kết quả cũ dính lại, tưởng prompt mới không có tác dụng.
- `model` — đổi model thì output khác chất.

Lưu tại `artifacts/summary_cache/`, commit được (dung lượng nhỏ, ~96 file JSON), giúp người khác `git clone` là chạy được ngay không tốn API.

### 10.3. Ghi ngược vào Qdrant

Thêm 2 field vào payload `section_parent` (không đổi vector, không đổi dimension):

```json
{
  "section_summary": "Giảng viên chỉ ra ba giới hạn cốt lõi của LLM...",
  "section_key_points": ["...", "..."],
  "summary_content_hash": "sha256:...",
  "summary_prompt_version": "v1"
}
```

Nhờ vậy S2 (tóm tắt mục) trả về ngay từ một lần `scroll` có filter, không gọi LLM.

**Yêu cầu M1**: bước upsert phải hỗ trợ `set_payload` để cập nhật payload mà không cần embed lại. Nếu M1 chưa có, M2 dùng file JSON làm nguồn chính và coi Qdrant payload là bản sao tiện dụng.

---

## 11. Chi phí và hiệu năng

### 11.1. Ước tính build một lần

| Hạng mục | Số lượng | Token in | Token out |
|---|---|---|---|
| Map (96 section) | 96 call | ~199.000 | ~29.000 |
| Reduce (6 session) | 6 call | ~24.000 | ~6.000 |

Với `gpt-4o-mini` cho map và `gpt-4o` cho reduce, tổng chi phí build đầy đủ nằm ở mức vài chục cent — không phải yếu tố cần tối ưu. Điều cần tối ưu là **số lần build lại**, và cache lo việc đó.

### 11.2. Runtime lúc demo

| Thao tác | LLM call | Độ trễ mục tiêu |
|---|---|---|
| S2 — tóm tắt mục (cache hit) | 0 | < 300 ms |
| S1 — tóm tắt buổi (section cache hit) | 1 | < 4 s |
| S1 — cache miss hoàn toàn | 20 | < 60 s |
| S3 — tóm tắt theo chủ đề | 2 | < 8 s |

Đường cache-miss phải chạy được, nhưng không phải đường dùng khi trình bày. Trước buổi demo: chạy `summarizer.build` cho cả 6 session, xác nhận cache đủ 96/96.

### 11.3. Song song hoá

Bước map là embarrassingly parallel. Dùng `asyncio` với semaphore giới hạn 5 request đồng thời + retry backoff cho rate limit. Không chạy 96 request cùng lúc.

---

## 12. Cấu trúc source code

```text
src/summarizer/
├── __init__.py
├── config.py          # model, prompt_version, cache dir, concurrency
├── schemas.py         # Pydantic: KeyPoint, SectionSummary, SessionSummary, Scope
├── scope.py           # resolve query → Scope | NeedsClarification
├── loader.py          # adapter lấy nội dung (2 nguồn: parser local / Qdrant reader)
├── prompts.py         # PROMPT_VERSION + template map/reduce
├── llm.py             # OpenAI client, structured output, retry, đếm token
├── mapper.py          # summarize_section()
├── reducer.py         # summarize_session()
├── topic.py           # S3 — tóm tắt theo chủ đề (giai đoạn sau)
├── validator.py       # citation check, coverage, warnings
├── cache.py           # đọc/ghi cache theo (content_hash, prompt_version, model)
├── render.py          # JSON → Markdown
├── build.py           # CLI precompute
└── api.py             # summarize(query) cho tầng orchestration

tests/summarizer/
├── fixtures/
│   ├── section_small.json
│   ├── section_with_unclear.json
│   └── section_with_student.json
├── test_schemas.py
├── test_scope.py
├── test_validator.py      # không cần API key
├── test_cache.py          # không cần API key
├── test_mapper.py         # mock LLM
├── test_reducer.py        # mock LLM
└── test_e2e_live.py       # đánh dấu @pytest.mark.live

artifacts/
├── summaries/{session_id}/{section_id}.json
├── summary_cache/
├── summary_manifest.json
└── summary_eval.json
```

### 12.1. Điểm tách quan trọng: `loader.py`

`loader.py` định nghĩa một interface duy nhất:

```python
class ContentLoader(Protocol):
    def get_session_outline(self, session_id: str) -> SessionOutline: ...
    def get_session_sections(self, session_id: str) -> list[SectionParent]: ...
    def get_section_content(self, section_id: str) -> list[AtomicChunk]: ...
```

Hai implementation:

- `LocalParserLoader` — đọc thẳng từ parser của M1, không cần Qdrant.
- `QdrantLoader` — gọi structured reader của M1.

Nhờ vậy M2 **không bị chặn** khi M1 chưa ingest xong. Bắt đầu bằng `LocalParserLoader`, đổi sang `QdrantLoader` bằng một dòng config khi M1 sẵn sàng. Đây là ràng buộc tích hợp đáng lo nhất giữa hai phần việc, và đây là cách gỡ nó.

---

## 13. Kế hoạch triển khai theo giai đoạn

### Giai đoạn 1 — Nền và schema (không cần LLM)

1. Định nghĩa Pydantic schemas.
2. Viết `ContentLoader` + `LocalParserLoader`.
3. Đo token thật bằng `tiktoken` trên cả 96 section, ghi lại section dài nhất.
4. Viết `cache.py` và test.

**Đầu ra**: gọi được `get_section_content("T03-SEC-004")` và nhận đúng 3 chunk theo thứ tự.

**Điều kiện hoàn thành**: test pass mà không cần API key.

---

### Giai đoạn 2 — Validator (không cần LLM)

1. Viết `validate_section_summary()` và `validate_session_summary()`.
2. Viết fixture "summary bịa" (citation không tồn tại, citation chéo buổi, thiếu section).
3. Test: mọi fixture xấu đều bị bắt.

**Điều kiện hoàn thành**:

```text
citation ngoài scope       → fail
citation chéo session      → fail (không phải warning)
section thiếu trong outline→ fail
key_point không citation   → item bị loại + log
coverage tính đúng
```

Làm validator **trước** mapper là có chủ đích: khi mapper ra kết quả đầu tiên, đã có sẵn công cụ đo nó đúng hay sai, thay vì đọc bằng mắt.

---

### Giai đoạn 3 — Map: tóm tắt section

1. Viết `llm.py` với structured output + retry.
2. Viết prompt map, gắn `PROMPT_VERSION = "v1"`.
3. Chạy thử trên 3 section đại diện: một section ngắn, một section có `[không nghe rõ]`, một section có `[học viên]`.
4. Soi tay 3 kết quả này trước khi chạy hàng loạt.
5. Chạy đủ 96 section, ghi cache.

**Điều kiện hoàn thành**:

- 96/96 section có summary hợp lệ.
- 0 citation không tồn tại.
- 0 citation chéo session.
- Section có `[học viên]` tách đúng `student_questions`.
- Chạy lại lần 2 → 96 cache hit, 0 API call.

---

### Giai đoạn 4 — Reduce: tóm tắt session

1. Viết prompt reduce.
2. Chạy cho cả 6 session.
3. Kiểm tra `outline` đủ và đúng thứ tự section.

**Điều kiện hoàn thành**:

```text
T01: outline có đủ 11 mục, đúng thứ tự
T02: 5 mục   T03: 19 mục   T04: 21 mục
T05: 19 mục  T06: 21 mục
0 citation ngoài session tương ứng
tldr không rỗng, key_points 5–8 ý
```

---

### Giai đoạn 5 — Scope resolution

1. Session tường minh: `"tóm tắt T03"`, `"tóm tắt buổi 3"`.
2. Mô tả tự nhiên: `"buổi chiều ngày 2"` → `find_sessions()` trên TOC vector.
3. Mô tả mục: `"mục nói về giới hạn của LLM"` → `find_sections()` trong session.
4. Mơ hồ → trả `needs_clarification` theo contract M1 §12.

**Điều kiện hoàn thành**: bộ 15 câu hỏi scope mẫu resolve đúng ≥ 13; các ca sai phải là ca mơ hồ thật, và phải rơi vào nhánh clarification chứ không đoán bừa.

---

### Giai đoạn 6 — Ghi ngược Qdrant + API

1. `set_payload` cho `section_parent`.
2. Viết `api.summarize(query) -> SessionSummary | SectionSummary | NeedsClarification`.
3. Viết `render.py` cho Markdown.
4. Nối vào Streamlit/FastAPI.

**Điều kiện hoàn thành**: S2 trả về < 300ms không gọi LLM.

---

### Giai đoạn 7 — Evaluation và bàn giao

1. Chạy bộ eval (§14).
2. Ghi `summary_manifest.json` và `summary_eval.json`.
3. Viết README phần tóm tắt.

---

### Giai đoạn 8 — S3 topic summary (nếu còn thời gian)

Cắt trước nếu thiếu thời gian. Khi làm, bắt buộc:

- Output ghi rõ `"completeness": "partial"`.
- Liệt kê các session đã quét và số chunk lấy được.
- Không được trình bày như thể đã đọc đủ khoá học.

---

## 14. Kế hoạch đánh giá

### 14.1. Metric tự động (chạy trong CI/test)

| Metric | Cách đo | Ngưỡng |
|---|---|---|
| Citation validity | % citation tồn tại trong scope | **100%** |
| Cross-session leakage | số citation ngoài session | **0** |
| Section coverage | % section xuất hiện trong outline | **100%** |
| Chunk citation rate | % chunk được ít nhất một ý trích dẫn | ≥ 30% |
| Schema validity | % output parse đúng Pydantic | 100% |
| Unclear handling | section có `[không nghe rõ]` sinh warning | 100% |
| Cache determinism | build lần 2 → 0 API call | đạt |

Ba metric đầu là hard gate: không đạt thì không được coi là xong.

`Chunk citation rate` chỉ ở mức 30% là hợp lý — bản tóm tắt tốt không trích dẫn mọi câu. Đặt ngưỡng cao hơn sẽ khuyến khích nhồi citation vô nghĩa.

### 14.2. Metric thủ công (lấy mẫu)

| Metric | Cách đo | Ngưỡng |
|---|---|---|
| Groundedness | 20 key_point ngẫu nhiên, người đọc chunk gốc và chấm đúng/sai | ≥ 18/20 |
| Speaker attribution | 10 section có `[học viên]`, kiểm tra không gán nhầm vai | 10/10 |
| Độ hữu ích | 3 người đọc `tldr` của 6 session, chấm 1–5 | ≥ 4.0 |

### 14.3. File eval

`artifacts/summary_eval.json` ghi lại số liệu từng lần chạy, kèm `prompt_version` và `model`. Đây là bằng chứng cho rubric, không phải chỉ để tự kiểm.

---

## 15. Rủi ro và giảm thiểu

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Dùng semantic top-k để tóm tắt buổi | Bỏ sót mục, tóm tắt sai trọng tâm | Structured reader riêng, validator ép đủ 100% section |
| LLM bịa citation ID | Mất tin cậy toàn hệ thống | Validator deterministic, fail build |
| Trộn nội dung giữa buổi | Sai nghiêm trọng về mặt nội dung | Filter `session_id` ở loader + validator fail |
| Gán lời học viên thành lời giảng viên | Sai bản chất transcript | Truyền `speaker` vào prompt, tách `student_questions` |
| Suy diễn chỗ `[không nghe rõ]` | Bịa nội dung | Prompt cấm + warning tự động |
| Section quá dài vượt context | Map hỏng ở section dài nhất | Đo token ở GĐ1; section vượt ngưỡng → chia theo chunk, map 2 tầng |
| Sửa prompt nhưng cache giữ kết quả cũ | Tưởng prompt không tác dụng | `prompt_version` nằm trong khoá cache |
| M1 chưa xong, M2 bị chặn | Mất song song hoá công việc | `LocalParserLoader` cho phép làm trước |
| Rate limit khi build 96 section | Build gián đoạn | Semaphore 5 + exponential backoff + cache từng phần |
| Gọi LLM lúc demo | Demo lag hoặc lỗi mạng | Precompute + xác nhận 96/96 cache trước buổi trình bày |
| Reduce thiên vị mục đầu | Mục cuối bị bỏ | Reduce đọc section summary (ngắn, đều), validator ép đủ outline |
| Đổi model giữa chừng | Kết quả không đồng nhất | `model` nằm trong khoá cache + ghi vào manifest |

---

## 16. Checkpoint bắt buộc

### Checkpoint S-A — Loader ready
```text
get_section_content("T03-SEC-004") trả đúng số chunk, đúng thứ tự
Không cần API key
```

### Checkpoint S-B — Validator ready
```text
Fixture "summary bịa" bị bắt 100%
Citation chéo session → fail, không phải warning
```

### Checkpoint S-C — Map ready
```text
96/96 section có summary hợp lệ
0 citation không tồn tại
Chạy lại → 0 API call
```

### Checkpoint S-D — Reduce ready
```text
6/6 session summary
outline đủ và đúng thứ tự section (11/5/19/21/19/21)
```

### Checkpoint S-E — Scope ready
```text
Bộ query mẫu resolve đúng ≥ 13/15
Ca mơ hồ rơi vào needs_clarification
```

### Checkpoint S-F — Serving ready
```text
S2 < 300ms, 0 LLM call
S1 < 4s, 1 LLM call
```

---

## 17. Definition of Done

- [ ] Schema Pydantic cho `SectionSummary` và `SessionSummary`.
- [ ] `ContentLoader` có 2 implementation, đổi bằng config.
- [ ] Tóm tắt buổi đọc đủ 100% chunk, không dùng top-k.
- [ ] 96/96 section summary được sinh và cache.
- [ ] 6/6 session summary được sinh.
- [ ] Mọi `key_point` có ít nhất một citation hợp lệ.
- [ ] 0 citation không tồn tại trong scope.
- [ ] 0 citation chéo session.
- [ ] Mọi section xuất hiện trong outline của session tương ứng.
- [ ] `[Hoạt động lớp]` bị loại khỏi nội dung kiến thức nhưng vẫn tính coverage.
- [ ] `[không nghe rõ]` sinh warning, không bị suy diễn.
- [ ] Lời học viên tách riêng, không gán cho giảng viên.
- [ ] Cache có `content_hash` + `prompt_version` + `model` trong khoá.
- [ ] Build lần 2 không gọi API.
- [ ] Section summary ghi vào payload Qdrant.
- [ ] Có `summary_manifest.json` và `summary_eval.json`.
- [ ] Có bộ test chạy được không cần API key.
- [ ] README hướng dẫn build lại từ đầu.
- [ ] Không có secret trong repo hoặc log.

---

## 18. Contract bàn giao

### Cho tầng orchestration / API

```python
def summarize(
    query: str,
    session_id: str | None = None,
    section_id: str | None = None,
) -> SessionSummary | SectionSummary | NeedsClarification:
    ...
```

Cam kết:

- Tóm tắt buổi luôn dựa trên đủ 100% chunk của buổi đó.
- Mọi ý đều có citation `TXX-NNN` truy ngược được.
- Không trộn nội dung giữa các buổi.
- Scope mơ hồ trả `NeedsClarification` với danh sách buổi ứng viên, không tự đoán.

### Cho frontend

- `tldr` để hiển thị đầu tiên.
- `outline` để render mục lục có thể mở rộng.
- `key_points[].citations` để render chip citation bấm được → hiện chunk gốc.
- `warnings` hiển thị dạng cảnh báo, không lẫn vào nội dung tóm tắt.
- `coverage` hiển thị dạng "đã đọc 154/154 đoạn" — đây là điểm khác biệt so với một RAG thông thường và nên cho người xem thấy.

### Phụ thuộc ngược lên M1

M2 cần M1 cung cấp:

| API | Bắt buộc | Ghi chú |
|---|---|---|
| `get_session_outline(session_id)` | ✅ | Dựng outline |
| `get_session_sections(session_id)` | ✅ | Danh sách section theo thứ tự |
| `get_section_content(section_id)` | ✅ | Đủ chunk, đúng thứ tự, có `speaker` |
| `find_sessions(query)` | ✅ | Scope resolution |
| `find_sections(query, session_id)` | ✅ | Scope resolution cấp mục |
| `set_payload` cho `section_parent` | ⚠️ nên có | Không có thì dùng file JSON |

Payload chunk phải có: `chunk_id`, `speaker`, `has_unclear`, `is_activity`, `text`, `section_id`, `session_id`, `chunk_order_in_section`.

**`speaker` chưa nằm trong payload atomic chunk của M1 (§8.2).** Cần bổ sung trước Giai đoạn 3, nếu không quy tắc chống gán nhầm vai không thực thi được.

---

## 19. Kết luận

Luồng tóm tắt không phải là "gọi LLM với một prompt dài". Chất lượng nó phụ thuộc vào:

```text
Đọc đủ nội dung (structured reader, không top-k)
+
Chia đúng đơn vị (section làm đơn vị map)
+
Ép citation ở mọi ý
+
Validator deterministic thay vì tin LLM
+
Precompute để lúc demo không phụ thuộc API
```

Điểm phân biệt với một bản tóm tắt RAG thông thường: hệ thống này chứng minh được nó đã đọc đủ 154/154 đoạn của buổi T03, mọi ý trỏ về được đoạn gốc, và không có ý nào lấy từ buổi khác. Đó là thứ cần đưa ra khi trình bày, không phải độ mượt của câu văn.
