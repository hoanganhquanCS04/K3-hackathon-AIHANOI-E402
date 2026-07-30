# VLearn Vector Database

Pipeline M1 dùng OpenAI `text-embedding-3-small` với output 768 chiều
và Qdrant Cloud để lập chỉ mục 6 transcript sạch.

## Kiến trúc dữ liệu

Một collection chứa ba loại point:

```text
session_toc
└── section_parent
    └── atomic_chunk
```

- `atomic_chunk`: giữ nguyên citation `TXX-NNN`.
- `section_parent`: đại diện một mục, chứa danh sách và toàn văn child.
- `session_toc`: định vị buổi và chứa mục lục.

Collection mặc định:

```text
vlearn_transcripts_openai_small_768_v1
```

Vector:

```text
model: text-embedding-3-small
dimensions: 768
distance: Cosine
```

## Cài môi trường

Từ thư mục `vector-db`:

```powershell
uv sync --locked
```

Không cần kích hoạt `.venv`; chạy lệnh qua `uv run`.

## Cấu hình

Copy `vector-db/.env.example` thành `.env` ở root repository hoặc trong
`vector-db`, rồi điền:

```dotenv
OPENAI_API_KEY=

QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=vlearn_transcripts_openai_small_768_v1

OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=768
```

Không commit `.env`.

## Kiểm tra local không gọi API

```powershell
uv run ruff check .
uv run pytest
uv run python -m vector_db.build --dry-run
```

Inventory kỳ vọng:

```text
6 sessions
96 sections
700 atomic chunks
802 total points
```

## Build Qdrant

Build idempotent:

```powershell
uv run python -m vector_db.build
```

Build sẽ:

1. Parse và validate toàn bộ transcript.
2. Tạo 700 atomic points, 96 parent points và 6 TOC points.
3. Tạo embedding atomic/TOC; parent dùng normalized mean child vector.
4. Tạo collection và payload indexes nếu chưa có.
5. Replace dữ liệu theo `session_id`.
6. Upsert 802 points.
7. Exact-count collection.
8. Ghi `artifacts/manifest.json`.

Chỉ dùng khi chủ động xóa đúng collection cấu hình:

```powershell
uv run python -m vector_db.build --recreate
```

## Search

Tìm buổi:

```powershell
uv run python -m vector_db.search `
  "Buổi nào nói về tool calling và RAG?" `
  --level session `
  --top-k 3
```

Tìm mục trong một buổi:

```powershell
uv run python -m vector_db.search `
  "tool calling và RAG" `
  --level section `
  --session-id T03 `
  --top-k 3
```

Tìm citation:

```powershell
uv run python -m vector_db.search `
  "LLM có trực tiếp gọi công cụ không?" `
  --level chunk `
  --session-id T03 `
  --section-id T03-SEC-004 `
  --top-k 5
```

Python API:

```python
from vector_db import find_chunks, find_sections, find_sessions, retrieve
```

Nếu chưa có `session_id`, gọi `retrieve(query)` sẽ trả
`status="needs_clarification"` và danh sách session thật được xếp hạng từ
`session_toc`. M1 chỉ trả metadata cấu trúc; tầng hội thoại chịu trách nhiệm
render câu hỏi làm rõ.

## Structured reader phục vụ tóm tắt

Lấy outline:

```powershell
uv run python -m vector_db.session_reader --session-id T03 --outline
```

Lấy đủ toàn buổi theo thứ tự:

```powershell
uv run python -m vector_db.session_reader --session-id T03
```

Lấy đủ một section:

```powershell
uv run python -m vector_db.session_reader --section-id T03-SEC-004
```

Python API:

```python
from vector_db import (
    get_section_content,
    get_session_content,
    get_session_outline,
    get_session_sections,
)
```

Các hàm structured reader dùng filter và order metadata, không dùng
semantic top-k, nên có thể cung cấp đủ nội dung cho map-reduce summary.

## Retrieval evaluation

```powershell
uv run python -m vector_db.evaluate
```

Test set nằm tại `tests/retrieval_cases.json`. Không xem score là xác
suất đúng; dùng Hit@K và Recall@K để đánh giá.

## Artifact

- `artifacts/manifest.json`: thông tin build có thể commit.
- `artifacts/manifest.dry-run.json`: kết quả parse/validate không ghi đè
  manifest của build thật.
- `artifacts/embedding_cache.sqlite3`: cache local, không commit.

## An toàn

- Không đưa API key vào frontend.
- Không log API key hoặc authorization header.
- Không dùng `--recreate` với collection ngoài phạm vi.
- Đổi model/dimension phải tạo collection version mới và embed lại.
