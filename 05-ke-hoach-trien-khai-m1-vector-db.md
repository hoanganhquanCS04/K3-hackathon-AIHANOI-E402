# Kế hoạch triển khai M1 — Vector Database với Qdrant Cloud và OpenAI Embeddings

## 1. Thông tin tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Hạng mục | M1 — Vector Database / Retrieval Layer |
| Bài toán | Hiểu, truy xuất và hỗ trợ tóm tắt transcript các buổi học |
| Vector database | Qdrant Cloud |
| Embedding provider | OpenAI |
| Embedding model | `text-embedding-3-small` |
| Kích thước vector dự kiến | 1536 chiều |
| Distance metric | Cosine |
| Công cụ quản lý Python | `uv` |
| Trạng thái tài liệu | Kế hoạch triển khai |
| Phạm vi | Thiết kế, xây dựng, kiểm thử và bàn giao lớp dữ liệu truy xuất |

---

## 2. Tóm tắt điều hành

Mục tiêu của M1 là xây dựng một lớp dữ liệu vector có cấu trúc từ transcript sạch được ban tổ chức cung cấp. Lớp này phải phục vụ đồng thời hai nhóm nhu cầu:

1. **Retrieval có citation**: từ câu hỏi tiếng Việt, tìm đúng buổi, đúng mục và đúng đoạn transcript gốc để tầng phía sau tạo câu trả lời có căn cứ.
2. **Đọc và tóm tắt toàn buổi**: cung cấp đầy đủ nội dung của một buổi học theo đúng cấu trúc mục lục và đúng thứ tự, để module tóm tắt không bỏ sót nội dung do chỉ lấy semantic top-k.

M1 không chỉ thực hiện thao tác “đưa embedding lên Qdrant”. Phần việc gồm bốn năng lực cốt lõi:

- Parse transcript chính xác và tái lập được.
- Chuẩn hóa metadata phục vụ định vị, filter, citation và kiểm soát phạm vi.
- Tạo embedding nhất quán bằng OpenAI `text-embedding-3-small`.
- Cung cấp retrieval contract rõ ràng cho các module hỏi–đáp và tóm tắt.

Thiết kế đề xuất sử dụng một collection Qdrant với ba loại point:

```text
session_toc
└── section_parent
    └── atomic_chunk
```

Trong đó:

- `atomic_chunk` giữ nguyên từng đoạn gốc có mã `TXX-NNN`.
- `section_parent` đại diện cho một mục lớn trong mục lục và liên kết tới toàn bộ atomic chunk thuộc mục đó.
- `session_toc` đại diện cho toàn buổi, chứa metadata định vị và mục lục.

---

## 3. Bối cảnh và bản chất bài toán

### 3.1. Bài toán sản phẩm

Hệ thống cuối cần hỗ trợ các câu hỏi như:

- “Giảng viên nói gì về tool calling?”
- “Buổi nào giải thích về RAG?”
- “Trong buổi chiều ngày 2 có nói gì về AI PM?”
- “Tóm tắt buổi T03.”
- “Tóm tắt mục nói về giới hạn của LLM.”
- “Các ý chính, ví dụ và kết luận của buổi học là gì?”

Kết quả phải:

- Dựa trên nội dung transcript thật.
- Không trộn nội dung giữa các buổi.
- Không gắn lời học viên thành phát biểu của giảng viên.
- Giữ được citation về đoạn gốc như `T03-034`.
- Nhận biết đoạn có nội dung không nghe rõ.
- Có khả năng lấy đủ một buổi để tóm tắt toàn diện.

### 3.2. Hai chế độ truy xuất khác nhau

#### Chế độ A — Semantic retrieval

Dùng cho câu hỏi cụ thể:

```text
Câu hỏi
→ embedding câu hỏi
→ semantic search có filter
→ atomic chunks liên quan
→ evidence và citation
```

Ví dụ:

```text
“Giảng viên nói gì về RAG?”
→ T03-034
→ T03-035
```

#### Chế độ B — Structured reading

Dùng cho yêu cầu tóm tắt toàn buổi hoặc toàn mục:

```text
session_id
→ lấy mục lục
→ lấy đủ section theo thứ tự
→ lấy đủ atomic chunk trong từng section
→ trả nội dung có cấu trúc cho module tóm tắt
```

Chế độ này không được dựa vào semantic top-k. Nếu một buổi có 43 chunk nhưng chỉ lấy top 10 chunk gần nghĩa với từ “tóm tắt”, hệ thống có thể bỏ mất các mục quan trọng.

### 3.3. Vai trò của Qdrant

Qdrant là lớp lưu trữ và truy vấn:

- Vector embedding.
- Payload metadata.
- Nội dung transcript gốc.
- Liên kết buổi → mục → đoạn.
- Filter theo phạm vi.
- Trả evidence và citation.

Qdrant không trực tiếp:

- Sinh câu trả lời cuối.
- Viết bản tóm tắt bằng ngôn ngữ tự nhiên.
- Điều phối giao diện.
- Đánh giá chất lượng văn phong của câu trả lời.

---

## 4. Phạm vi trách nhiệm của M1

### 4.1. Trong phạm vi

M1 chịu trách nhiệm:

1. Khảo sát cấu trúc transcript đầu vào.
2. Viết parser đọc transcript.
3. Giữ nguyên các atomic chunk `TXX-NNN`.
4. Chuẩn hóa metadata.
5. Xác định quan hệ giữa session, section và atomic chunk.
6. Tạo `session_toc`.
7. Tạo `section_parent`.
8. Tạo embedding bằng OpenAI.
9. Tạo và cấu hình collection trên Qdrant Cloud.
10. Tạo payload indexes.
11. Upsert point theo cơ chế idempotent.
12. Cung cấp hàm semantic search.
13. Cung cấp hàm đọc toàn bộ session/section.
14. Trả metadata citation đầy đủ.
15. Kiểm thử parser, metadata, ingest và retrieval.
16. Tạo manifest để tái lập database.
17. Viết README và contract bàn giao.

### 4.2. Ngoài phạm vi

M1 không chịu trách nhiệm chính cho:

- Prompt sinh câu trả lời.
- LLM generation.
- Viết bản tóm tắt cuối cùng.
- Giao diện người dùng.
- Thiết kế hội thoại.
- Chấm điểm câu trả lời cuối.
- Logic trình bày citation trên frontend.

Tuy nhiên, M1 phải cung cấp dữ liệu đủ sạch và contract đủ rõ để các phần trên hoạt động đúng.

---

## 5. Kiến trúc tổng thể đề xuất

```text
Transcript sạch
    │
    ▼
Parser và Normalizer
    │
    ├── Session metadata
    ├── Section metadata
    └── Atomic chunks TXX-NNN
    │
    ▼
Metadata Validation
    │
    ▼
Point Builder
    │
    ├── session_toc
    ├── section_parent
    └── atomic_chunk
    │
    ▼
OpenAI Embedding Service
    │
    ├── atomic vectors
    ├── parent vectors
    └── TOC vectors
    │
    ▼
Qdrant Cloud
    │
    ├── Vector index
    └── Payload indexes
    │
    ▼
Retrieval Layer
    │
    ├── find_sessions()
    ├── find_sections()
    ├── find_chunks()
    ├── get_session_outline()
    ├── get_section_content()
    └── get_session_content()
```

---

## 6. Quyết định kỹ thuật ban đầu

| Thành phần | Quyết định |
|---|---|
| Python | 3.12 |
| Dependency manager | `uv` |
| OpenAI SDK | Package `openai` |
| Embedding model | `text-embedding-3-small` |
| Vector dimension | 1536 |
| Encoding format | Float |
| Vector store | Qdrant Cloud |
| Distance | Cosine |
| Collection strategy | Một collection, ba `point_type` |
| Atomic chunking | Giữ nguyên `TXX-NNN`, không chia lại |
| Qdrant physical ID | Deterministic UUID v5 |
| Citation ID | Giữ nguyên `TXX-NNN` |
| Parent vector | Trung bình chuẩn hóa từ child vectors |
| Ingest | Idempotent upsert |
| Rebuild | Lệnh riêng có cờ `--recreate` |
| Validation | Pydantic + invariant checks |
| Test | Pytest |
| Lint | Ruff |

### 6.1. Lý do giữ vector 1536 chiều

`text-embedding-3-small` trả vector 1536 chiều theo mặc định. Bản hackathon nên giữ cấu hình mặc định vì:

- Giảm số quyết định cần thử nghiệm.
- Tránh lỗi collection và query dùng dimension khác nhau.
- Tránh phải đánh giá lại chất lượng khi rút gọn vector.
- Quy mô transcript dự kiến chưa đủ lớn để chi phí lưu trữ 1536 chiều trở thành nút thắt chính.

Nếu sau này cần giảm dimension, phải:

1. Chọn dimension mới.
2. Tạo collection version mới.
3. Embed lại toàn bộ dữ liệu.
4. Chạy lại retrieval evaluation.
5. Chỉ chuyển traffic sau khi collection mới đạt yêu cầu.

---

## 7. Thiết kế dữ liệu phân cấp

### 7.1. Atomic chunk

Atomic chunk là đơn vị nguyên tử do dữ liệu nguồn cung cấp:

```text
T03-001
T03-002
...
T03-043
```

Quy tắc:

- Không chia nhỏ thêm.
- Không gộp làm mất ID.
- Không đánh số lại.
- Không thay đổi nội dung nguyên văn.
- Không dùng một ID mới thay thế citation ID.
- Có thể dùng UUID làm physical point ID, nhưng payload luôn giữ `chunk_id`.

### 7.2. Section parent

Mỗi heading lớn trong mục lục tạo một section:

```text
T03-SEC-001
T03-SEC-002
...
```

Section parent:

- Chứa tên mục.
- Chứa danh sách child chunk.
- Chứa khoảng chunk bắt đầu/kết thúc.
- Chứa toàn bộ nội dung mục theo đúng thứ tự.
- Tổng hợp trạng thái `has_unclear`.
- Có vector đại diện cho toàn mục.

### 7.3. Session TOC

Mỗi buổi có một TOC point:

```text
T03-TOC
```

TOC point:

- Định vị toàn buổi.
- Chứa tên buổi.
- Chứa ngày và buổi sáng/chiều.
- Chứa danh sách mục.
- Chứa ranh giới chunk của từng mục.
- Có vector giúp tìm đúng buổi từ câu hỏi tự nhiên.

---

## 8. Thiết kế metadata

### 8.1. Metadata định vị buổi

```json
{
  "session_id": "T03",
  "session_day": 2,
  "session_period": "chiều",
  "session_title": "Soi bài toán các nhóm · tự động hoá & ràng buộc",
  "session_locator": "Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc",
  "location_confidence": "vừa"
}
```

Mục tiêu của `session_locator` là tạo một chuỗi định vị tự nhiên để:

- Đưa vào embedding text.
- Hiển thị trong kết quả tìm buổi.
- Hỗ trợ câu hỏi dùng mô tả thay vì mã kỹ thuật.

### 8.2. Payload atomic chunk

```json
{
  "schema_version": "1.0",
  "point_type": "atomic_chunk",

  "chunk_id": "T03-034",
  "citation_id": "T03-034",

  "session_id": "T03",
  "session_day": 2,
  "session_period": "chiều",
  "session_title": "Soi bài toán các nhóm · tự động hoá & ràng buộc",
  "session_locator": "Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc",
  "location_confidence": "vừa",

  "section_id": "T03-SEC-004",
  "section_title": "Giới hạn của LLM, tool calling và RAG",
  "section_order": 4,

  "parent_chunk_id": "T03-SEC-004",
  "chunk_order_in_session": 34,
  "chunk_order_in_section": 1,

  "has_unclear": false,
  "is_activity": false,

  "text": "Nội dung transcript nguyên văn...",
  "source_file": "03.md",
  "content_hash": "sha256:..."
}
```

### 8.3. Payload section parent

```json
{
  "schema_version": "1.0",
  "point_type": "section_parent",
  "chunk_id": "T03-SEC-004",

  "session_id": "T03",
  "session_day": 2,
  "session_period": "chiều",
  "session_title": "Soi bài toán các nhóm · tự động hoá & ràng buộc",
  "session_locator": "Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc",

  "section_id": "T03-SEC-004",
  "section_title": "Giới hạn của LLM, tool calling và RAG",
  "section_order": 4,

  "start_chunk_id": "T03-034",
  "end_chunk_id": "T03-036",
  "child_chunk_ids": [
    "T03-034",
    "T03-035",
    "T03-036"
  ],
  "child_count": 3,

  "has_unclear": false,
  "unclear_chunk_ids": [],
  "unclear_count": 0,

  "full_text": "[T03-034] ...\n\n[T03-035] ...\n\n[T03-036] ..."
}
```

### 8.4. Payload session TOC

```json
{
  "schema_version": "1.0",
  "point_type": "session_toc",
  "chunk_id": "T03-TOC",

  "session_id": "T03",
  "session_day": 2,
  "session_period": "chiều",
  "session_title": "Soi bài toán các nhóm · tự động hoá & ràng buộc",
  "session_locator": "Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc",

  "section_ids": [
    "T03-SEC-001",
    "T03-SEC-002",
    "T03-SEC-003",
    "T03-SEC-004",
    "T03-SEC-005"
  ],

  "toc": [
    {
      "section_id": "T03-SEC-001",
      "section_order": 1,
      "section_title": "Tên mục thứ nhất",
      "start_chunk_id": "T03-001",
      "end_chunk_id": "T03-013",
      "child_count": 13
    }
  ],

  "toc_text": "1. Tên mục thứ nhất\n2. Tên mục thứ hai"
}
```

---

## 9. Quy tắc tạo các field dẫn xuất

### 9.1. `has_unclear`

Không dùng LLM để phân loại:

```python
has_unclear = "[không nghe rõ]" in text.lower()
```

Đối với section parent:

```python
parent_has_unclear = any(
    child.has_unclear
    for child in children
)
```

### 9.2. `is_activity`

Ví dụ quy tắc ban đầu:

```python
is_activity = text.lstrip().startswith("[Hoạt động lớp:")
```

Quy tắc thực tế phải điều chỉnh sau khi khảo sát toàn bộ cách đánh dấu trong dữ liệu.

### 9.3. `content_hash`

Tạo hash từ nội dung canonical:

```text
SHA-256(text UTF-8 sau khi chuẩn hóa line ending)
```

Mục đích:

- Phát hiện dữ liệu thay đổi.
- Cache embedding.
- Tránh gọi lại OpenAI với nội dung không đổi.
- Hỗ trợ audit và tái lập.

---

## 10. Chiến lược embedding

### 10.1. Atomic embedding text

Không embed nội dung trần. Cần thêm metadata định vị:

```text
Buổi: Day 2 (chiều) — Soi bài toán các nhóm · tự động hoá & ràng buộc
Mục: Giới hạn của LLM, tool calling và RAG

[T03-034] Nội dung nguyên văn...
```

Payload vẫn giữ `text` nguyên văn. `embedding_text` chỉ là biểu diễn phục vụ retrieval.

### 10.2. Section parent vector

Không mặc định gửi toàn bộ `full_text` dài lên embedding API. Phương án v1:

1. Embed từng atomic chunk.
2. Tập hợp child vectors.
3. Lấy trung bình theo từng chiều.
4. Chuẩn hóa L2.

```python
matrix = np.asarray(child_vectors, dtype=np.float32)
parent = matrix.mean(axis=0)
parent = parent / np.linalg.norm(parent)
```

Ưu điểm:

- Không bị truncate một section dài.
- Mọi child đều đóng góp.
- Không cần thêm LLM.
- Deterministic.

### 10.3. Session TOC vector

Embed:

```text
Day 2 (chiều) — Tên buổi

Mục lục:
1. Tên mục thứ nhất
2. Tên mục thứ hai
...
```

TOC vector phục vụ tìm buổi, không thay thế atomic retrieval.

### 10.4. Query embedding

Query phải dùng cùng:

- Model.
- Dimension.
- Encoding.
- Version collection.

Không được:

```text
Ingest bằng model A
Search bằng model B
```

Kể cả hai model trả cùng dimension, không gian vector vẫn khác nhau.

---

## 11. Thiết kế Qdrant collection

### 11.1. Collection

Tên đề xuất:

```text
vlearn_transcripts_openai_small_v1
```

Cấu hình:

```text
Vector size: 1536
Distance: Cosine
```

### 11.2. Payload indexes

Tạo trước khi ingest:

| Field | Kiểu index | Mục đích |
|---|---|---|
| `point_type` | keyword | Tách TOC, parent và atomic |
| `session_id` | keyword | Filter đúng buổi |
| `section_id` | keyword | Filter đúng mục |
| `session_day` | integer | Filter theo ngày |
| `session_period` | keyword | Filter sáng/chiều |
| `has_unclear` | bool | Loại/cảnh báo nội dung không rõ |
| `is_activity` | bool | Loại hoạt động khỏi QA kiến thức khi cần |

Không index mặc định:

- `text`
- `full_text`
- `child_chunk_ids`
- `source_file`
- `content_hash`

Các field này chủ yếu dùng để render, citation và validation.

### 11.3. Point ID

Qdrant physical ID dùng UUID v5:

```python
def make_point_id(point_type: str, logical_id: str) -> str:
    raw = f"{point_type}:{logical_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, raw))
```

Ví dụ:

```text
atomic_chunk:T03-001
section_parent:T03-SEC-001
session_toc:T03-TOC
```

Điều này bảo đảm ingest lại sinh đúng ID và không nhân đôi point.

---

## 12. Thiết lập môi trường với uv

### 12.1. Cài uv trên Windows

Kiểm tra:

```powershell
uv --version
```

Cài bằng WinGet:

```powershell
winget install --id=astral-sh.uv -e
```

Hoặc dùng installer chính thức:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 12.2. Cài Python

```powershell
uv python install 3.12
uv python list
```

### 12.3. Khởi tạo project

```powershell
uv init --package vector-db
cd vector-db
```

### 12.4. Cài runtime dependency

```powershell
uv add openai qdrant-client python-dotenv pydantic tenacity numpy tiktoken
```

### 12.5. Cài development dependency

```powershell
uv add --dev pytest pytest-cov ruff
```

### 12.6. Đồng bộ môi trường

```powershell
uv sync
uv lock --check
uv tree
```

### 12.7. Nguyên tắc vận hành

Dùng:

```powershell
uv run python ...
uv run pytest ...
uv run ruff ...
```

Không bắt buộc kích hoạt `.venv` bằng tay.

Các file cần commit:

- `pyproject.toml`
- `uv.lock`
- `.python-version`

Không commit:

- `.venv/`
- `.env`

---

## 13. Cấu hình môi trường và secret

### 13.1. `.env.example`

```dotenv
OPENAI_API_KEY=

QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=vlearn_transcripts_openai_small_v1

OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

### 13.2. Quy tắc bảo mật

- Không hard-code API key.
- Không commit `.env`.
- Không in key ra terminal/log.
- Không đặt OpenAI/Qdrant key trong frontend.
- Nếu backend demo công khai, key chỉ nằm ở environment của backend.
- Key dùng cho ingest có thể có read/write.
- Key dành cho search production nên giới hạn quyền nếu Qdrant Cloud plan hỗ trợ.

---

## 14. Cấu trúc source code dự kiến

```text
vector-db/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env
├── .env.example
├── .gitignore
├── README.md
│
├── data/
│   └── transcripts/
│
├── src/
│   └── vector_db/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── parser.py
│       ├── metadata.py
│       ├── validation.py
│       ├── embeddings.py
│       ├── point_builder.py
│       ├── qdrant_store.py
│       ├── build.py
│       ├── search.py
│       └── session_reader.py
│
├── tests/
│   ├── fixtures/
│   ├── retrieval_cases.json
│   ├── test_parser.py
│   ├── test_metadata.py
│   ├── test_point_builder.py
│   ├── test_embeddings.py
│   ├── test_ingestion.py
│   ├── test_search.py
│   └── test_session_reader.py
│
└── artifacts/
    ├── manifest.json
    └── rejected_records.jsonl
```

---

## 15. Kế hoạch triển khai theo từng giai đoạn

## Giai đoạn 1 — Khởi tạo môi trường

### Công việc

1. Cài `uv`.
2. Cài Python 3.12.
3. Khởi tạo package.
4. Cài dependency.
5. Tạo `.env.example`.
6. Cập nhật `.gitignore`.
7. Xác nhận `uv.lock`.

### Kiểm tra

```powershell
uv --version
uv run python --version
uv lock --check
uv run python -c "import openai, qdrant_client, pydantic, numpy"
```

### Điều kiện hoàn thành

- Project chạy qua `uv run`.
- Dependency được khóa.
- `.env` không nằm trong Git.

---

## Giai đoạn 2 — Kết nối dịch vụ

### Công việc

1. Tạo Qdrant Cloud cluster.
2. Lấy cluster URL.
3. Tạo Database API key.
4. Chuẩn bị OpenAI API key.
5. Viết `config.py`.
6. Viết smoke test OpenAI.
7. Viết smoke test Qdrant.

### Kiểm tra

```text
OpenAI:
- Gửi một chuỗi ngắn.
- Nhận đúng một vector.
- Vector có 1536 phần tử.

Qdrant:
- Gọi get_collections().
- Nhận response hợp lệ.
```

### Điều kiện hoàn thành

- Kết nối được cả hai dịch vụ.
- Không log secret.
- Lỗi key/URL được báo rõ ràng.

---

## Giai đoạn 3 — Khảo sát dữ liệu nguồn

### Công việc

Tạo báo cáo khảo sát:

- Số file transcript.
- Danh sách session.
- Số atomic chunk mỗi session.
- Số section mỗi session.
- Quy tắc tiêu đề.
- Quy tắc mục lục.
- Quy tắc đánh dấu unclear.
- Quy tắc đánh dấu hoạt động.
- Chunk thiếu hoặc trùng.
- Nội dung nằm ngoài section.

### Deliverable

```text
artifacts/source_inventory.json
```

### Điều kiện hoàn thành

- Team biết chính xác số dữ liệu cần ingest.
- Các ngoại lệ được liệt kê trước khi viết parser hoàn chỉnh.

---

## Giai đoạn 4 — Xây parser

### Công việc

Parser đọc file và trả:

```python
ParsedSession(
    session_metadata=...,
    sections=...,
    atomic_chunks=...,
)
```

Parser không được:

- Gọi OpenAI.
- Gọi Qdrant.
- Tự sửa nội dung transcript.
- Bỏ qua record lỗi mà không báo.

### Kiểm tra

- Snapshot kết quả parse.
- Đếm chunk trước/sau.
- So sánh text với source.
- Kiểm tra thứ tự.

### Điều kiện hoàn thành

- 100% chunk hợp lệ được parse.
- Mọi lỗi nguồn được báo cụ thể theo file và ID.

---

## Giai đoạn 5 — Xây metadata và validation

### Công việc

1. Định nghĩa Pydantic models.
2. Tạo metadata session.
3. Gán section cho atomic chunk.
4. Tạo field dẫn xuất.
5. Tạo content hash.
6. Viết invariant validation.

### Invariant bắt buộc

1. `chunk_id` duy nhất.
2. Mọi atomic chunk có đúng một parent.
3. Parent có ít nhất một child.
4. Child tồn tại trong source.
5. Child cùng session với parent.
6. Child cùng section với parent.
7. Không section vượt session boundary.
8. `start_chunk_id` là child đầu.
9. `end_chunk_id` là child cuối.
10. `full_text` đúng thứ tự.
11. `has_unclear` parent bằng OR của child.
12. TOC chứa đủ section.
13. Citation ID tồn tại.

### Chính sách lỗi

- Lỗi nghiêm trọng: fail build.
- Record lỗi: ghi `rejected_records.jsonl`.
- Không tự sửa ngầm.

---

## Giai đoạn 6 — Xây point builder

### Công việc

Từ parsed session, tạo:

- Atomic points.
- Section parent points.
- Session TOC points.
- Deterministic UUID.
- Embedding text.

### Kiểm tra tính deterministic

Chạy point builder hai lần:

- Physical UUID giống nhau.
- Payload giống nhau.
- Thứ tự point ổn định.
- Content hash giống nhau.

---

## Giai đoạn 7 — Xây embedding service

### Công việc

1. Tạo OpenAI client.
2. Viết `embed_text`.
3. Viết `embed_batch`.
4. Retry lỗi tạm thời.
5. Kiểm soát batch size.
6. Kiểm tra token input.
7. Kiểm tra vector dimension.
8. Cache theo content hash.
9. Tạo parent vector.
10. Ghi usage vào manifest/log.

### Chính sách retry

Áp dụng exponential backoff cho:

- Rate limit.
- Timeout.
- Lỗi server tạm thời.

Không retry vô hạn với:

- API key sai.
- Input không hợp lệ.
- Model không tồn tại.

### Điều kiện hoàn thành

- Embedding tiếng Việt hoạt động.
- Mỗi vector có đúng 1536 phần tử.
- Batch giữ đúng thứ tự input/output.
- Chạy lại có thể tái sử dụng cache.

---

## Giai đoạn 8 — Tạo collection và indexes

### Trình tự bắt buộc

```text
Create collection
→ Create payload indexes
→ Upload points
```

### Kiểm tra collection hiện có

Nếu collection tồn tại:

- Kiểm tra dimension.
- Kiểm tra distance.
- Kiểm tra schema/version nếu có.
- Không ghi vào collection cấu hình không tương thích.

### Chính sách version

Nếu đổi model hoặc dimension:

```text
vlearn_transcripts_openai_small_v1
→ vlearn_transcripts_openai_small_v2
```

Không thay đổi âm thầm collection đang dùng.

---

## Giai đoạn 9 — Build và ingest

### Lệnh chuẩn

```powershell
uv run python -m vector_db.build
```

Luồng:

```text
Load config
→ inventory
→ parse
→ validate source
→ build points
→ validate payload
→ embed
→ ensure collection
→ ensure indexes
→ upsert
→ exact count
→ sample verification
→ manifest
```

### Rebuild có chủ đích

```powershell
uv run python -m vector_db.build --recreate
```

Yêu cầu:

- Cảnh báo rõ collection bị xóa/tạo lại.
- Chỉ xóa đúng collection được cấu hình.
- Không có hành vi xóa collection trong luồng mặc định.

### Idempotency

Chạy build lần hai:

- Point count không tăng.
- UUID không đổi.
- Point được cập nhật theo ID.
- Không còn stale point nếu session đã thay đổi.

Chiến lược stale point cần chốt:

1. Xóa theo `session_id` rồi upsert lại session; hoặc
2. So sánh manifest và xóa các ID không còn tồn tại.

Với quy mô hackathon, replace theo session là đơn giản và dễ kiểm chứng hơn, nhưng field `session_id` phải có payload index trước.

---

## Giai đoạn 10 — Semantic retrieval

### API đề xuất

```python
def find_sessions(
    query: str,
    top_k: int = 3,
) -> list[SessionHit]:
    ...


def find_sections(
    query: str,
    session_id: str,
    top_k: int = 3,
) -> list[SectionHit]:
    ...


def find_chunks(
    query: str,
    session_id: str,
    section_id: str | None = None,
    top_k: int = 5,
    exclude_activities: bool = True,
) -> list[ChunkHit]:
    ...
```

### Luồng hierarchical retrieval

```text
Query
→ find_sessions
→ find_sections trong session
→ find_chunks trong section
→ evidence TXX-NNN
```

### Quy tắc

- Query rỗng: `ValueError`.
- `top_k < 1`: `ValueError`.
- Giới hạn `top_k`, ví dụ tối đa 20.
- Session không tồn tại: trả trạng thái rõ ràng.
- Không fallback âm thầm từ session sai sang toàn collection.
- Luôn filter `point_type`.

### Output atomic retrieval

```json
{
  "point_id": "uuid",
  "score": 0.84,
  "chunk_id": "T03-034",
  "citation_id": "T03-034",
  "session_id": "T03",
  "session_title": "...",
  "section_id": "T03-SEC-004",
  "section_title": "...",
  "has_unclear": false,
  "is_activity": false,
  "text": "..."
}
```

---

## Giai đoạn 11 — Structured reader phục vụ tóm tắt

### API đề xuất

```python
def get_session_outline(
    session_id: str,
) -> SessionOutline:
    ...


def get_session_sections(
    session_id: str,
) -> list[SectionParent]:
    ...


def get_section_content(
    section_id: str,
) -> list[AtomicChunk]:
    ...


def get_session_content(
    session_id: str,
) -> list[AtomicChunk]:
    ...
```

### Quy tắc quan trọng

Các hàm này:

- Không dùng semantic score.
- Không dùng top-k.
- Dùng payload filter.
- Lấy đủ dữ liệu.
- Sắp xếp theo order.
- Giữ citation.

### Luồng tóm tắt phía sau

```text
get_session_outline()
→ với mỗi section:
     get_section_content()
     → tóm tắt section
→ tổng hợp các section summary
→ session summary
```

M1 bảo đảm tính đầy đủ và thứ tự. Module LLM phía sau chịu trách nhiệm viết bản tóm tắt.

---

## Giai đoạn 12 — Clarification metadata

### Mục tiêu

Nếu câu hỏi không có session và nhiều buổi cùng liên quan, retrieval layer không nên tự chọn một buổi.

### Contract gợi ý

```json
{
  "status": "needs_clarification",
  "reason": "ambiguous_session",
  "missing_metadata": [
    "session_id"
  ],
  "candidate_sessions": [
    {
      "session_id": "T02",
      "session_title": "...",
      "matched_section": "...",
      "best_score": 0.84
    },
    {
      "session_id": "T05",
      "session_title": "...",
      "matched_section": "...",
      "best_score": 0.82
    }
  ]
}
```

M1 trả metadata có cấu trúc. Frontend hoặc module hội thoại có thể chuyển thành câu hỏi tự nhiên.

### Không quyết định ambiguity chỉ bằng một threshold tùy ý

Cần nhóm kết quả theo session:

- Best score.
- Hit count.
- Score distribution.
- Matched sections.

Threshold chỉ chốt sau retrieval evaluation.

---

## 16. Kế hoạch kiểm thử

## 16.1. Parser tests

- Đọc đúng số session.
- Đọc đúng số section.
- Đọc đúng số chunk.
- Không trùng ID.
- Không đổi text.
- Giữ đúng thứ tự.
- Báo lỗi nguồn có vị trí rõ ràng.

## 16.2. Metadata tests

- Field bắt buộc đầy đủ.
- `has_unclear` đúng.
- `is_activity` đúng.
- Quan hệ parent/child đúng.
- TOC đầy đủ.
- Content hash ổn định.

## 16.3. Embedding tests

- Model name đúng.
- Vector dimension 1536.
- Batch output đúng số lượng.
- Batch output giữ đúng thứ tự.
- Parent vector có norm hợp lệ.
- Input quá dài được phát hiện.

## 16.4. Ingestion tests

- Collection tồn tại.
- Index tồn tại.
- Exact point count đúng.
- Không point trùng.
- Chạy lại không nhân đôi.
- Random sample payload khớp source.

## 16.5. Filter tests

```python
results = find_chunks(
    query="tool calling",
    session_id="T03",
    top_k=5,
)

assert all(
    result.session_id == "T03"
    for result in results
)
```

Test thêm:

- Section filter không rò section khác.
- `point_type=atomic_chunk` không trả parent/TOC.
- `exclude_activities=True` không trả activity.

## 16.6. Retrieval relevance tests

File `retrieval_cases.json`:

```json
[
  {
    "query": "Giảng viên nói gì về tool calling?",
    "session_id": "T03",
    "expected_chunk_ids": [
      "T03-034",
      "T03-035"
    ]
  }
]
```

Metric:

- Hit@1.
- Hit@3.
- Hit@5.
- Recall@5.
- MRR nếu đủ thời gian.

Không xem một câu hỏi thử thành bằng chứng chất lượng. Cần tập query đại diện.

## 16.7. Summary input completeness tests

Với mỗi session:

```text
count(get_session_content(session_id))
=
atomic chunk count trong source
```

Đồng thời:

- Chunk đầu đúng.
- Chunk cuối đúng.
- Thứ tự không đảo.
- Không trộn session.
- Mỗi section có đủ child.

## 16.8. Edge cases

- Query rỗng.
- `top_k=0`.
- `top_k` quá lớn.
- Session không tồn tại.
- Section không tồn tại.
- Collection chưa tạo.
- OpenAI mất kết nối.
- Qdrant mất kết nối.
- API key sai.
- Vector dimension không khớp.
- Transcript có chunk trùng.
- Transcript có mục lục tham chiếu chunk không tồn tại.

---

## 17. Manifest và khả năng tái lập

### Manifest mẫu

```json
{
  "collection_name": "vlearn_transcripts_openai_small_v1",
  "schema_version": "1.0",

  "embedding": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "dimensions": 1536,
    "encoding_format": "float",
    "distance": "cosine"
  },

  "point_counts": {
    "atomic_chunk": 0,
    "section_parent": 0,
    "session_toc": 0,
    "total": 0
  },

  "payload_indexes": [
    "point_type",
    "session_id",
    "section_id",
    "session_day",
    "session_period",
    "has_unclear",
    "is_activity"
  ],

  "parent_embedding_strategy": "normalized_mean_of_child_vectors_v1",

  "source": {
    "file_count": 0,
    "source_hashes": {}
  },

  "build": {
    "created_at": "...",
    "git_commit": "...",
    "python_version": "3.12",
    "uv_lock_hash": "..."
  }
}
```

### Tính tái lập

Một thành viên khác phải có thể:

```powershell
git clone ...
uv sync
copy .env.example .env
# điền key
uv run python -m vector_db.build
```

và tạo lại collection tương đương từ transcript.

---

## 18. Logging và quan sát

Log nên có:

- Build ID.
- Session đang xử lý.
- Số chunk parse.
- Số chunk rejected.
- Số embedding request.
- Tổng token embedding.
- Số point upsert.
- Thời gian từng phase.
- Exact count sau ingest.

Không log:

- API key.
- Authorization header.
- Vector đầy đủ.
- Toàn bộ transcript nếu không cần.

Ví dụ:

```text
[INFO] Parsing session T03
[INFO] Parsed atomic chunks: 43
[INFO] Built section parents: 5
[INFO] Built session TOC: 1
[INFO] Embedding atomic chunks: batch 1/2
[INFO] Upserted points: 49
[INFO] Exact collection count: 49
```

---

## 19. Rủi ro và phương án giảm thiểu

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Parser hiểu sai mục lục | Gán sai section | Inventory + parser snapshot tests |
| Mất chunk ID gốc | Citation không kiểm chứng được | Invariant bắt buộc |
| Embed text thiếu tên buổi | Khó tìm buổi bằng ngôn ngữ tự nhiên | Bổ sung session locator |
| Trộn ba point type | Kết quả top-k trùng lặp | Luôn filter `point_type` |
| Dùng semantic top-k để tóm tắt | Bỏ sót nội dung | Structured reader riêng |
| Model/dimension không đồng nhất | Query lỗi hoặc retrieval sai | Manifest + collection version |
| Chạy ingest tạo bản sao | Point count sai | UUID v5 + idempotent upsert |
| Stale point sau sửa transcript | Trả nội dung cũ | Replace theo session |
| Tạo index sau ingest | Filter kém hiệu quả | Tạo index trước upload |
| OpenAI rate limit | Build gián đoạn | Batch + retry + cache |
| Lộ API key | Rủi ro bảo mật | `.env`, `.gitignore`, không log |
| Threshold retrieval tùy ý | Demo thiếu ổn định | Retrieval evaluation |
| Parent text quá dài | Embedding bị loãng/truncate | Mean child vectors |
| Count từ collection info chưa chính xác tức thời | Verify sai | Dùng exact count API |

---

## 20. Kế hoạch thực hiện theo ngày/buổi

### Buổi 1 — Môi trường và dịch vụ

- Cài `uv`.
- Khởi tạo package.
- Cài dependency.
- Cấu hình `.env`.
- Kết nối OpenAI.
- Kết nối Qdrant Cloud.

Đầu ra:

- Project chạy được.
- Hai smoke test pass.

### Buổi 2 — Dữ liệu và parser

- Inventory transcript.
- Chốt quy tắc parser.
- Viết parser.
- Viết parser tests.

Đầu ra:

- Parsed sessions.
- Báo cáo số chunk/section.

### Buổi 3 — Metadata và hierarchy

- Viết Pydantic schema.
- Tạo atomic metadata.
- Tạo section parent.
- Tạo session TOC.
- Viết validation.

Đầu ra:

- Tập point chưa có vector.
- Validation pass.

### Buổi 4 — Embedding và Qdrant

- Viết embedding service.
- Batch/retry/cache.
- Tạo collection.
- Tạo payload indexes.
- Ingest dữ liệu.

Đầu ra:

- Collection có dữ liệu.
- Exact count đúng.
- Idempotency pass.

### Buổi 5 — Retrieval và summary reader

- Viết hierarchical search.
- Viết structured reader.
- Viết output contract.
- Kiểm tra session/section filter.

Đầu ra:

- Search API.
- Session reader API.

### Buổi 6 — Evaluation và bàn giao

- Tạo retrieval cases.
- Tính Hit@K/Recall@K.
- Sửa metadata/embedding text nếu cần.
- Tạo manifest.
- Hoàn thiện README.
- Chạy full test suite.

Đầu ra:

- Bộ code tái lập.
- Collection demo.
- Báo cáo test.

---

## 21. Các checkpoint bắt buộc

### Checkpoint A — Environment ready

```powershell
uv run python --version
uv lock --check
uv run python -c "import openai, qdrant_client"
```

### Checkpoint B — Services ready

```text
OpenAI embedding trả vector 1536 chiều.
Qdrant get_collections thành công.
```

### Checkpoint C — Parser ready

```text
Source chunk count = parsed atomic chunk count.
Không trùng ID.
Không đổi text.
```

### Checkpoint D — Metadata ready

```text
0 cross-session child.
0 cross-section child.
0 citation không tồn tại.
0 payload thiếu field.
```

### Checkpoint E — Ingestion ready

```text
Exact point count đúng.
Chạy lại không nhân đôi.
Random payload khớp source.
```

### Checkpoint F — Retrieval ready

```text
Session filter không rò dữ liệu.
Section filter không rò dữ liệu.
Atomic search không trả parent/TOC.
```

### Checkpoint G — Summarization input ready

```text
get_session_content trả đủ mọi chunk.
Thứ tự đúng.
Citation đầy đủ.
```

---

## 22. Definition of Done

M1 chỉ được coi là hoàn thành khi:

- [ ] Project sử dụng `uv` và có `uv.lock`.
- [ ] OpenAI và Qdrant Cloud kết nối thành công.
- [ ] Collection được tạo bằng code.
- [ ] Collection dùng vector size 1536 và Cosine.
- [ ] Payload indexes được tạo trước ingest.
- [ ] Mọi atomic chunk `TXX-NNN` được giữ nguyên.
- [ ] Không có chunk trùng hoặc mất.
- [ ] Có đủ `atomic_chunk`, `section_parent`, `session_toc`.
- [ ] Mỗi atomic chunk có session và section metadata.
- [ ] Mỗi atomic chunk có `has_unclear`.
- [ ] Section parent chứa đủ child và `full_text`.
- [ ] Session TOC chứa đủ mục lục.
- [ ] Physical point ID deterministic.
- [ ] Build mặc định idempotent.
- [ ] Rebuild có cờ riêng và cảnh báo.
- [ ] Search luôn filter theo `point_type`.
- [ ] Session filter không rò buổi khác.
- [ ] Citation trả về đúng `TXX-NNN`.
- [ ] Có API lấy đủ section.
- [ ] Có API lấy đủ toàn session theo đúng thứ tự.
- [ ] Có retrieval test và metric.
- [ ] Có manifest.
- [ ] Có README hướng dẫn tái lập.
- [ ] Không có secret trong repository hoặc log.

---

## 23. Contract bàn giao cho các thành viên khác

### Cho module hỏi–đáp

M1 bàn giao:

```python
find_chunks(
    query,
    session_id,
    section_id=None,
    top_k=5,
)
```

Output có:

- Text.
- Citation.
- Session.
- Section.
- Score.
- `has_unclear`.
- `is_activity`.

### Cho module tóm tắt

M1 bàn giao:

```python
get_session_outline(session_id)
get_session_sections(session_id)
get_section_content(section_id)
get_session_content(session_id)
```

Cam kết:

- Nội dung đầy đủ.
- Đúng thứ tự.
- Không trộn session.
- Giữ citation.

### Cho frontend hoặc orchestration

M1 bàn giao metadata:

- Candidate sessions.
- Candidate sections.
- Session title.
- Section title.
- Citation IDs.
- Clarification status nếu phạm vi mơ hồ.

---

## 24. Lệnh vận hành dự kiến

### Cài môi trường

```powershell
uv sync
```

### Kiểm tra code

```powershell
uv run ruff check .
uv run pytest -v
```

### Kiểm tra kết nối

```powershell
uv run python -m vector_db.qdrant_store
uv run python -m vector_db.embeddings
```

### Build

```powershell
uv run python -m vector_db.build
```

### Rebuild

```powershell
uv run python -m vector_db.build --recreate
```

### Search thử

```powershell
uv run python -m vector_db.search
```

### Chạy evaluation

```powershell
uv run python -m vector_db.evaluate
```

---

## 25. Tài liệu kỹ thuật tham khảo

- OpenAI Embeddings guide:  
  <https://developers.openai.com/api/docs/guides/embeddings>

- OpenAI `text-embedding-3-small`:  
  <https://developers.openai.com/api/docs/models/text-embedding-3-small>

- Qdrant Cloud quickstart:  
  <https://qdrant.tech/documentation/cloud/quickstart-cloud/>

- Qdrant collections:  
  <https://qdrant.tech/documentation/manage-data/collections/>

- Qdrant payload indexing:  
  <https://qdrant.tech/documentation/manage-data/indexing/>

- Qdrant filtering:  
  <https://qdrant.tech/documentation/search/filtering/>

- Qdrant points:  
  <https://qdrant.tech/documentation/manage-data/points/>

- uv installation:  
  <https://docs.astral.sh/uv/getting-started/installation/>

- uv project dependencies:  
  <https://docs.astral.sh/uv/concepts/projects/dependencies/>

- uv locking and syncing:  
  <https://docs.astral.sh/uv/concepts/projects/sync/>

---

## 26. Kết luận

Phần M1 là nền móng dữ liệu cho toàn hệ thống. Chất lượng của câu trả lời và bản tóm tắt phía sau phụ thuộc trực tiếp vào:

```text
Parser đúng
+
Metadata đúng
+
Embedding nhất quán
+
Filter đúng phạm vi
+
Citation truy ngược được
+
Structured reader lấy đủ nội dung
```

Một vector database đạt yêu cầu không chỉ “search ra kết quả gần nghĩa”. Nó phải chứng minh được:

- Đoạn đó thuộc buổi nào.
- Thuộc mục nào.
- Có citation nào.
- Nội dung có bị không nghe rõ hay không.
- Có phải hoạt động lớp hay không.
- Có thể lấy lại đầy đủ toàn bộ buổi theo đúng thứ tự hay không.

Thiết kế ba tầng `session_toc → section_parent → atomic_chunk` giúp cùng một collection phục vụ được cả định vị buổi, tìm kiếm chi tiết và tóm tắt toàn diện. Đây là contract chính M1 cần triển khai và bàn giao cho team.
