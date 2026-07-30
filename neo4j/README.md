# VLearn Neo4j Knowledge Graph

## Overview

Day la he thong Knowledge Graph xay dung tren Neo4j de luu tru va truy van du lieu tu cac bai giang VLearn.

## Cau truc Du Lieu

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

### Node Types

| Node | Mo ta | Vi du |
|------|-------|-------|
| `Lecture` | Bai giang | "Xac dinh bai toan kinh doanh cho AI" |
| `Section` | Phan trong bai | "Ky nang xac dinh bai toan" |
| `Turn` | Cau hoi/tra loi | [T01-001] "Mot trong nhung ky nang..." |
| `Concept` | Khai niem | "bai toan AI", "yêu cau mo ho" |
| `Question` | Cau hoi noi bat | "Lam the nao de xac dinh bai toan?" |
| `Reference` | Tai lieu tham khao | "Thinking, Fast and Slow" |

### Relationships

| Relationship | Tu | Den | Mo ta |
|-------------|-----|-----|-------|
| `BELONGS_TO` | Section | Lecture | Section thuoc bai giang |
| `BELONGS_TO` | Turn | Section | Turn thuoc section |
| `COVERS` | Section | Concept | Section chua khai niem |
| `INTRODUCES` | Lecture | Concept | Bai giang gioi thieu khai niem |
| `RELATED_TO` | Concept | Concept | Khai niem lien quan |
| `HAS_QUESTION` | Lecture | Question | Bai giang co cau hoi |

## Transcript Format

### Quy uoc

Moi transcript tuyen theo format:

```markdown
# Transcript bai giang (bản sạch) — Day 2 (sáng) — Xác định bài toán kinh doanh cho AI

> **Nguồn:** `transcript_2/01.md` · **Định vị buổi:** Day 2 (sáng)
> **Quy ước:** `[Txx-NNN]` mã đoạn để trích dẫn

## Kỹ năng xác định bài toán từ yêu cầu mơ hồ

**[T01-001]** Một trong những kỹ năng mình nghĩ quan trọng và đang cần nhất...

**[T01-002]** Trong khoảng hai năm trở lại đây...

## Product manager, project manager

**[T01-007]** Bây giờ các vị trí trong một team bắt đầu xoá mờ...
```

### Quy tac Parse

| Ky hieu | Y nghia |
|---------|---------|
| `[Txx-NNN]` | Ma turn (turn_id) |
| `## Heading` | Section moi |
| `[Học viên]:` | Hoi tu phia hoc vien |
| `[Hoạt động lớp:]` | Hoat dong lop |
| `[không nghe rõ]` | Khong nghe duoc |

## Cac Buoc Su Dung

### 1. Cau hinh moi truong

Tao file `.env` (hoac copy tu `.env.example`):

```env
# Neo4j AuraDB
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# OpenAI (cho viec trich xuat metadata)
OPENAI_API_KEY=sk-xxxxx
```

### 2. Upload Data len Neo4j

Chay script `ingest_transcripts.py` de upload tat ca transcript:

```bash
cd neo4j
python ingest_transcripts.py
```

**Script se:**
1. Drop toan bo data cu trong Neo4j
2. Tao schema moi (constraints, indexes)
3. Parse tat ca transcript files trong `data/vlearn-pack/transcript/`
4. Trich xuat metadata (topics, concepts, questions, references) bang LLM
5. Upload len Neo4j

**Ket qua:**
```
============================================================
INGESTION COMPLETE!
============================================================

Total imported:
  - Lectures: 6
  - Sections: 96
  - Turns: 698
  - Concepts: 50
  - Questions: 30
  - References: 1
```

### 3. Query Test

Chay script `query_neo4j.py` de kham pha du lieu:

```bash
python query_neo4j.py
```

**Cac query mau:**
- Lay tat ca concepts
- Tim quan he giua concepts
- Tim topics trong moi bai giang
- Tim tai lieu tham khao
- Tim concept theo tu khoa
- Tim cac concept lien quan

## Cau truc Folder

```
neo4j/
├── ingest_transcripts.py   # Upload data len Neo4j
├── query_neo4j.py          # Query mau de test
└── README.md               # File nay

data/
└── vlearn-pack/
    └── transcript/          # Chua cac transcript files
        ├── transcript-01-clean.md
        ├── transcript-02-clean.md
        └── ...
```

## Requirements

```txt
neo4j>=5.14.0
python-dotenv>=1.0.0
openai>=1.0.0
```

Cai dat:
```bash
pip install -r requirements.txt
```

## Ghi Chu

- **Chunking:** 1 turn = 1 chunk (theo format `[Txx-NNN]`)
- **Sections:** Duoc tao tu cac `## Heading` trong transcript
- **Metadata Extraction:** Su dung GPT-4o de trich xuat topics, concepts, questions, references
- **Concept Relationships:** Duoc tao dua tren co-occurrence trong cung bai giang

## Troubleshooting

### Loi ket noi Neo4j
- Kiem tra `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` trong `.env`
- Dam bao Neo4j AuraDB dang chay

### Loi OpenAI
- Kiem tra `OPENAI_API_KEY` trong `.env`
- Dam bao credit con du

### Khong tim thay transcript
- Kiem tra duong dan `data/vlearn-pack/transcript/`
- Dam bao file co dinh dang `*-clean.md`
