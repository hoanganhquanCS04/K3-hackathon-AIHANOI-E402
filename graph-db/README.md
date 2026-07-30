# VLearn Neo4j Knowledge Graph

## Overview

Hệ thống Knowledge Graph xây dựng trên Neo4j để lưu trữ và truy vấn dữ liệu từ các bài giảng VLearn qua 3 nhánh RRF (BM25, Qdrant, Neo4j).

## Cấu trúc Dữ liệu & Fulltext Index

### Graph Schema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           KNOWLEDGE GRAPH                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  (Lecture)                                                              │
│      │                                                                  │
│      ├──[:BELONGS_TO]──▶ (Section)                                      │
│      │                        │                                         │
│      │                        ├──[:BELONGS_TO]──▶ (Turn)               │
│      │                        │                                         │
│      │                        └──[:COVERS]──────▶ (Concept)            │
│      │                                               │                  │
│      └──[:INTRODUCES]──▶ (Concept) ◀──[:RELATED_TO]──▶ (Concept)     │
│                                                                         │
│  (Lecture)──[:HAS_QUESTION]──▶ (Question)                               │
│  (Lecture)──[:INTRODUCES]──▶ (Reference)                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Fulltext Index cho Retrieve

Fulltext Index `concept_name_ft` trên `(c:Concept)` cho phép tra cứu khái niệm bằng từ khóa thực thể do LLM viết lại:

```cypher
CREATE FULLTEXT INDEX concept_name_ft IF NOT EXISTS FOR (c:Concept) ON EACH [c.name, c.name_en]
```

API `turns_for_concepts(thuc_the, session, k)` trong `graph_db.retrieve` thực hiện truy vấn lan từ Concept -> Section -> Turn (0-hop và 1..2-hop) để lấy mã đoạn `Turn.id` và điểm số mà KHÔNG lấy `Concept.description` vào prompt (bảo đảm ranh giới thẩm quyền).

## Các bước sử dụng

### 1. Cấu hình môi trường

Tạo file `.env` (hoặc copy từ `.env.example`):

```env
# Neo4j AuraDB
NEO4J_URL=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# OpenAI (cho việc trích xuất metadata)
OPENAI_API_KEY=sk-xxxxx
```

### 2. Upload Data lên Neo4j

Chạy script `ingest_transcripts.py` để upload tất cả transcript:

```bash
uv run python graph-db/scripts/ingest_transcripts.py
```

### 3. Kiểm tra kết nối & Retrieval

```bash
uv run python graph-db/scripts/check_neo4j.py
uv run pytest graph-db/tests
```
