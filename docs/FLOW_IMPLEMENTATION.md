# VLearn Hybrid System - Luong Xu Ly Chi Tiet

> **Muc tieu**: Mo ta chi tiet cac luong xu ly khi da co VectorDatabase (Qdrant) va Knowledge Graph (Neo4j)

---

## Muc Luc

1. [Tong quan kien truc](#1-tong-quan-kien-truc)
2. [Data Schema](#2-data-schema)
3. [Luong 1: Data Ingestion](#3-luong-1-data-ingestion)
4. [Luong 2: Intent Detection](#4-luong-2-intent-detection)
5. [Luong 3: Semantic Search](#5-luong-3-semantic-search)
6. [Luong 4: Graph Query](#6-luong-4-graph-query)
7. [Luong 5: Multi-Hop](#7-luong-5-multi-hop)
8. [Luong 6: Comparison](#8-luong-6-comparison)
9. [Luong 7: Recommendation](#9-luong-7-recommendation)
10. [Luong 8: Summary](#10-luong-8-summary)
11. [API Endpoints](#11-api-endpoints)

---

## 1. Tong quan kien truc

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              VLEARN HYBRID SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│    ┌─────────────┐         ┌─────────────────────────────────────────────────┐       │
│    │   Client    │────────▶│              API Gateway (FastAPI)             │       │
│    │  (Streamlit)│         │                                                  │       │
│    └─────────────┘         └─────────────────────────────────────────────────┘       │
│                                       │                                              │
│                                       ▼                                              │
│                              ┌─────────────────┐                                     │
│                              │ Intent Router   │                                     │
│                              │   (LLM-based)   │                                     │
│                              └─────────────────┘                                     │
│                                       │                                              │
│           ┌───────────────────────────┼───────────────────────────┐                  │
│           │                           │                           │                  │
│           ▼                           ▼                           ▼                  │
│   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐              │
│   │  Semantic     │         │  Graph        │         │  Multi-Hop    │              │
│   │  Search       │         │  Query        │         │  / Compare    │              │
│   │  (VectorDB)   │         │  (Neo4j)      │         │  (Hybrid)     │              │
│   └───────────────┘         └───────────────┘         └───────────────┘              │
│           │                           │                           │                  │
│           │                           │                           │                  │
│           ▼                           ▼                           ▼                  │
│   ┌─────────────────────────────────────────────────────────────────────────────┐    │
│   │                         VECTOR DATABASE (Qdrant)                            │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │    │
│   │  │   Topics    │  │  Concepts   │  │   Turns     │  │  Lectures   │        │    │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │    │
│   └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐    │
│   │                         KNOWLEDGE GRAPH (Neo4j)                              │    │
│   │                                                                              │    │
│   │    (Lecture)─────[:INTRODUCES]─────▶(Topic)─────[:COVERS]─────▶(Concept)  │    │
│   │        │                                        │                            │    │
│   │        │                                        │                            │    │
│   │        ▼                                        ▼                            │    │
│   │    (Transcript)                          (Question)                          │    │
│   │                                                                              │    │
│   └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Schema

### 2.1 Quy uoc tu Transcript

Dựa trên cấu trúc transcript thực tế (`transcript-01-clean.md`):

```
# Transcript bài giảng (bản sạch) — Day 2 (sáng) — Xác định bài toán kinh doanh cho AI

> **Nguồn:** `transcript_2/01.md` · **Định vị buổi:** Day 2 (sáng)
> **Quy ước:** `[Txx-NNN]` mã đoạn để trích dẫn

## Kỹ năng xác định bài toán từ yêu cầu mơ hồ

**[T01-001]** Một trong những kỹ năng mình nghĩ quan trọng...

**[T01-002]** Trong khoảng hai năm trở lại đây...

## Product manager, project manager và văn hoá làm product

**[T01-007]** Bây giờ các vị trí trong một team bắt đầu xoá mờ...

[Học viên]: Project thì kiểu một dự án tạo ra xong...
```

**Quy tắc:**
- `[Txx-NNN]` = mã turn, xx = lecture/session, NNN = thứ tự
- `## Heading` = section mới (phục vụ summarization)
- `[Học viên]` hoặc giảng viên = speaker role

---

### 2.2 VectorDatabase Schema (Qdrant)

#### Collection: `transcript_turns` - 1 câu = 1 chunk

```python
# Muc dich: Chi tiết nhất, phuc vu tra cuu chinh xac

{
    "id": "T01-001",                          # Ma turn tu transcript
    "vector": [0.123, -0.456, ...],           # 1536 dimensions
    
    "payload": {
        # --- Content ---
        "content": "Một trong những kỹ năng mình nghĩ quan trọng và đang cần nhất...",
        
        # --- Metadata bắt buộc ---
        "turn_id": "T01-001",                  # Ma turn (unique)
        "lecture_id": "transcript_01",         # ID transcript
        "lecture_title": "Xác định bài toán kinh doanh cho AI",
        "lecture_day": "Day 2 (sáng)",
        
        "turn_index": 1,                       # Thứ tự trong lecture
        "section_title": "Kỹ năng xác định bài toán từ yêu cầu mơ hồ",
        "section_index": 1,                     # Thứ tự section
        
        "speaker": "tutor",                    # tutor | student
        "speaker_label": None,                  # "học viên" | None
        
        # --- Tu transcript gốc ---
        "raw_ref": "transcript_2/01.md",       # Nguồn gốc
        
        # --- Optional: trích xuất thêm ---
        "keywords": ["AI", "bài toán", "yêu cầu mơ hồ"],
        "has_question": False,
        "is_activity": False                    # [Hoạt động lớp: ...]
    }
}
```

#### Collection: `transcript_sections` - 1 section = 1 chunk (cho summarization)

```python
# Muc dich: Tom tat nhanh, phuc vu SUMMARY flow

{
    "id": "section_01",                        # section_01, section_02...
    "vector": [0.123, -0.456, ...],           # Embed toàn bộ section
    
    "payload": {
        # --- Content: toàn bộ nội dung section ---
        "content": "**[T01-001]** Một trong những kỹ năng mình nghĩ quan trọng...\n\n**[T01-002]** Trong khoảng hai năm trở lại đây...\n\n**[T01-003]** Thực tế có những nghiên cứu...",
        
        # --- Metadata ---
        "section_id": "section_01",
        "lecture_id": "transcript_01",
        "lecture_title": "Xác định bài toán kinh doanh cho AI",
        
        "title": "Kỹ năng xác định bài toán từ yêu cầu mơ hồ",
        "section_index": 1,
        "turn_count": 17,                       # Số turn trong section
        "turn_ids": ["T01-001", "T01-002", ...],  # Danh sách turn IDs
        
        # --- Trích xuất LLM ---
        "summary": "Bài học về việc xác định bài toán AI từ yêu cầu mơ hồ...",
        "topics": ["bài toán AI", "yêu cầu mơ hồ", "problem solving"],
        "concepts": ["xác định vấn đề", "bóc tách yêu cầu"],
        "questions": ["Làm thế nào để xác định bài toán?"],
        
        # --- Stats ---
        "word_count": 850,
        "has_student_input": True               # Co phan student hoi?
    }
}
```

#### Collection: `transcript_lectures` - 1 lecture = 1 chunk (toàn bộ bài giảng)

```python
# Muc dich: Tom tat cao nhat, overview

{
    "id": "transcript_01",
    "vector": [0.123, -0.456, ...],
    
    "payload": {
        "content": "## Kỹ năng xác định bài toán...\n\n## Product manager...\n\n## Phát triển sản phẩm AI...",
        
        "lecture_id": "transcript_01",
        "title": "Xác định bài toán kinh doanh cho AI",
        "day": "Day 2 (sáng)",
        "source": "transcript_2/01.md",
        
        "section_count": 6,                    # Số section
        "section_ids": ["section_01", "section_02", ...],
        
        "topics": ["bài toán kinh doanh", "AI", "product management"],
        "summary": "Tổng quan về cách xác định bài toán kinh doanh cho AI..."
    }
}
```

### 2.3 Knowledge Graph Schema (Neo4j)

Dựa trên cấu trúc transcript thực tế:

```cypher
// ============ NODES ============

// Lecture - Bai giang (tu transcript)
(:Lecture {
    id: "transcript_01",
    title: "Xác định bài toán kinh doanh cho AI",
    day: "Day 2 (sáng)",
    source_file: "transcript_2/01.md",
    order: 1,
    
    // Metadata tu transcript header
    source: "VLearn Production - chatlog",
    reliability: "high",
    
    // Stats
    section_count: 6,
    turn_count: 50,
    word_count: 8500,
    
    created_at: datetime()
})

// Section - Phan trong bai giang (## Heading)
(:Section {
    id: "section_01",
    title: "Kỹ năng xác định bài toán từ yêu cầu mơ hồ",
    section_index: 1,
    lecture_id: "transcript_01",
    
    // Stats
    turn_count: 17,
    word_count: 1200,
    has_student_input: true,
    
    created_at: datetime()
})

// Turn - Cau hoi/tra loi trong transcript ([Txx-NNN])
(:Turn {
    id: "T01-001",
    turn_index: 1,
    lecture_id: "transcript_01",
    section_id: "section_01",
    
    // Content
    content: "Một trong những kỹ năng mình nghĩ quan trọng và đang cần nhất...",
    
    // Speaker
    speaker: "tutor",           // tutor | student
    speaker_label: null,        // "học viên" hoặc null
    
    // Flags
    is_activity: false,         // [Hoạt động lớp: ...]
    has_question: false,
    is_illegible: false,        // [không nghe rõ]
    
    // Reference
    raw_ref: "transcript_2/01.md",
    
    created_at: datetime()
})

// Concept - Khai niem (trich xuat tu LLM)
(:Concept {
    id: "concept_001",
    name: "bài toán AI",
    name_en: "AI problem",
    
    // Trich xuat
    description: "Bài toán cụ thể mà AI có thể giải quyết trong doanh nghiệp",
    frequency: 15,               // So lan xuat hien trong corpus
    
    // Source
    source_turn: "T01-001",
    
    created_at: datetime()
})

// Question - Cau hoi noi bat (trich xuat tu LLM)
(:Question {
    id: "question_001",
    text: "Làm thế nào để xác định bài toán từ yêu cầu mơ hồ?",
    type: "conceptual",          // conceptual | explanatory | practical
    
    // Source
    source_turn: "T01-015",
    lecture_id: "transcript_01",
    
    created_at: datetime()
})

// Reference - Tai lieu tham khao (trich xuat tu transcript)
(:Reference {
    id: "ref_001",
    title: "Thinking, Fast and Slow",
    author: "Daniel Kahneman",
    type: "book",
    url: null,
    
    // Source
    source_turn: "T01-016",
    
    created_at: datetime()
})

// ============ RELATIONSHIPS ============

// BELONGS_TO: Turn thuoc Section
(:Turn)-[:BELONGS_TO {
    turn_index: 1
}]->(:Section)

// BELONGS_TO: Section thuoc Lecture
(:Section)-[:BELONGS_TO {
    section_index: 1
}]->(:Lecture)

// COVERS: Section chua Concept
(:Section)-[:COVERS {
    confidence: 0.95,
    context: "Bai giang ve cach xac dinh bai toan"
}]->(:Concept)

// HAS_QUESTION: Turn chua cau hoi
(:Turn)-[:HAS_QUESTION]->(:Question)

// HAS_REFERENCE: Turn co tai lieu tham khao
(:Turn)-[:HAS_REFERENCE]->(:Reference)

// INTRODUCES: Lecture gioi thieu Concept (lan dau xuat hien)
(:Lecture)-[:INTRODUCES {
    first_turn: "T01-001",
    is_main_topic: true
}]->(:Concept)

// REFERENCES: Concept co tai lieu tham khao
(:Concept)-[:REFERENCES]->(:Reference)

// RELATED_TO: Concept lien quan nhau
(:Concept)-[:RELATED_TO {
    similarity: 0.85,
    type: "prerequisite"         // prerequisite | related | contrast
}]->(:Concept)

// HAS_ACTIVITY: Section co hoat dong lop
(:Section)-[:HAS_ACTIVITY]->(:Turn)

// ============ INDEXES ============

CREATE INDEX lecture_id_idx FOR (l:Lecture) ON (l.id);
CREATE INDEX section_id_idx FOR (s:Section) ON (s.id);
CREATE INDEX turn_id_idx FOR (t:Turn) ON (t.id);
CREATE INDEX concept_name_idx FOR (c:Concept) ON (c.name);
CREATE INDEX concept_frequency_idx FOR (c:Concept) ON (c.frequency);
```

---

## 3. Luong 1: Data Ingestion

### 3.1 Muc tieu
Dua transcript moi vao he thong: parse markdown, tao chunks (turns + sections), trich xuat metadata, luu vao VectorDB va Neo4j.

### 3.2 Flow Chi Tiet

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LUONG 1: DATA INGESTION                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  INPUT                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  transcript-01-clean.md                                                       │  │
│  │  # Transcript bài giảng — Day 2 (sáng) — Xác định bài toán kinh doanh...  │  │
│  │                                                                               │  │
│  │  ## Kỹ năng xác định bài toán từ yêu cầu mơ hồ                         │  │
│  │  **[T01-001]** Một trong những kỹ năng...                                 │  │
│  │  **[T01-002]** Trong khoảng hai năm trở lại đây...                       │  │
│  │  ...                                                                          │  │
│  │                                                                               │  │
│  │  ## Product manager, project manager...                                      │  │
│  │  **[T01-007]** Bây giờ các vị trí trong một team...                       │  │
│  │  ...                                                                          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1: PARSE MARKDOWN                                                      │  │
│  │                                                                               │  │
│  │  Output:                                                                     │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  {                                                                   │ │  │
│  │  │    "lecture_id": "transcript_01",                                    │ │  │
│  │  │    "title": "Xác định bài toán kinh doanh cho AI",                   │ │  │
│  │  │    "day": "Day 2 (sáng)",                                           │ │  │
│  │  │    "source_file": "transcript_2/01.md",                              │ │  │
│  │  │    "sections": [                                                      │ │  │
│  │  │      {                                                                │ │  │
│  │  │        "id": "section_01",                                          │ │  │
│  │  │        "title": "Kỹ năng xác định bài toán...",                    │ │  │
│  │  │        "turns": [                                                    │ │  │
│  │  │          {"id": "T01-001", "speaker": "tutor", "content": "..."},  │ │  │
│  │  │          {"id": "T01-002", "speaker": "tutor", "content": "..."},  │ │  │
│  │  │        ]                                                              │ │  │
│  │  │      }                                                               │ │  │
│  │  │    ]                                                                 │ │  │
│  │  │  }                                                                   │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 2: CREATE CHUNKS                                                      │  │
│  │                                                                               │  │
│  │  Collection 1: transcript_turns (1 câu = 1 chunk)                           │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  T01-001: {"content": "Một trong những kỹ năng...", "section": 1}  │ │  │
│  │  │  T01-002: {"content": "Trong khoảng hai năm...", "section": 1}     │ │  │
│  │  │  T01-007: {"content": "Bây giờ các vị trí...", "section": 2}       │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                               │  │
│  │  Collection 2: transcript_sections (1 section = 1 chunk)                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  section_01: {                                                        │ │  │
│  │  │    "content": "[T01-001] ... [T01-006] Toàn bộ nội dung section 1",  │ │  │
│  │  │    "turn_ids": ["T01-001", "T01-002", ...],                          │ │  │
│  │  │    "turn_count": 17                                                   │ │  │
│  │  │  }                                                                    │ │  │
│  │  │  section_02: {                                                        │ │  │
│  │  │    "content": "[T01-007] ... [T01-016] Toàn bộ nội dung section 2",  │ │  │
│  │  │  }                                                                    │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 3: EXTRACT METADATA (LLM)                                              │  │
│  │                                                                               │  │
│  │  - Topics: ["bài toán AI", "yêu cầu mơ hồ", "product management"]         │  │
│  │  - Concepts: ["xác định vấn đề", "bóc tách yêu cầu"]                     │  │
│  │  - Questions: ["Làm thế nào để xác định bài toán?"]                     │  │
│  │  - References: ["Thinking, Fast and Slow", "AI Engineering"]              │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                         ┌──────────┴──────────┐                                    │
│                         ▼                      ▼                                     │
│  ┌────────────────────────────────────┐  ┌────────────────────────────────────┐     │
│  │  STEP 4a: INSERT TO VECTOR DB     │  │  STEP 4b: INSERT TO NEO4J         │     │
│  │  (Qdrant)                          │  │  (Knowledge Graph)                │     │
│  │                                    │  │                                    │     │
│  │  Collections:                      │  │  Nodes:                           │     │
│  │  - transcript_turns               │  │  - Lecture                        │     │
│  │  - transcript_sections            │  │  - Section                        │     │
│  │  - transcript_lectures            │  │  - Turn                           │     │
│  │                                    │  │  - Concept                        │     │
│  │                                    │  │  - Question                       │     │
│  │                                    │  │  - Reference                      │     │
│  │                                    │  │                                    │     │
│  │                                    │  │  Relationships:                   │     │
│  │                                    │  │  - BELONGS_TO (Turn→Section)     │     │
│  │                                    │  │  - BELONGS_TO (Section→Lecture)   │     │
│  │                                    │  │  - COVERS (Section→Concept)      │     │
│  │                                    │  │  - INTRODUCES (Lecture→Concept)  │     │
│  │                                    │  │  - RELATED_TO (Concept↔Concept)  │     │
│  └────────────────────────────────────┘  └────────────────────────────────────┘     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Code Implementation

```python
# scripts/ingestion_pipeline.py

"""
VLearn Transcript Ingestion Pipeline

Parse transcript markdown -> Create chunks (turns + sections) -> Index to VectorDB + Neo4j
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams

@dataclass
class Turn:
    id: str           # T01-001
    speaker: str       # tutor | student
    speaker_label: Optional[str]  # "học viên" or None
    content: str
    is_activity: bool = False
    is_illegible: bool = False

@dataclass
class Section:
    id: str
    title: str
    section_index: int
    turns: List[Turn]
    
@dataclass
class Lecture:
    id: str
    title: str
    day: str
    source_file: str
    sections: List[Section]

@dataclass
class ExtractedMetadata:
    topics: List[str]
    concepts: List[str]
    questions: List[str]
    references: List[Dict[str, str]]

class TranscriptParser:
    """Parse transcript markdown theo quy uoc VLearn"""
    
    def parse(self, file_path: str) -> Lecture:
        """Parse transcript markdown file"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Parse header (first 5 lines)
        lecture = self._parse_header(lines)
        
        # Parse sections and turns
        lecture.sections = self._parse_body(lines, lecture.id)
        
        return lecture
    
    def _parse_header(self, lines: List[str]) -> Lecture:
        """Parse header: title, day, source"""
        
        # Line 1: # Transcript bài giảng (bản sạch) — Day 2 (sáng) — Xác định bài toán kinh doanh cho AI
        title_match = re.search(r'— (.+)$', lines[0])
        title = title_match.group(1).strip() if title_match else "Unknown"
        
        # Line 3: > **Nguồn:** `transcript_2/01.md` · **Định vị buổi:** Day 2 (sáng)
        source_match = re.search(r'`([^`]+)`', lines[2])
        source_file = source_match.group(1) if source_match else ""
        
        day_match = re.search(r'Day[:\s]+(\d+)', lines[2])
        day = f"Day {day_match.group(1)}" if day_match else "Unknown"
        
        # Generate lecture_id from filename
        lecture_id = Path(source_file).stem.replace('transcript_', 'transcript_')
        
        return Lecture(
            id=lecture_id,
            title=title,
            day=day,
            source_file=source_file,
            sections=[]
        )
    
    def _parse_body(self, lines: List[str], lecture_id: str) -> List[Section]:
        """Parse body: extract sections and turns"""
        
        sections = []
        current_section = None
        current_section_turns = []
        current_section_idx = 0
        turn_index = 0
        
        for i, line in enumerate(lines[6:], start=6):  # Skip header (6 lines)
            stripped = line.strip()
            
            # Section header: ## Heading
            if stripped.startswith('## '):
                # Save previous section
                if current_section and current_section_turns:
                    sections.append(Section(
                        id=f"section_{current_section_idx:02d}",
                        title=current_section,
                        section_index=current_section_idx,
                        turns=current_section_turns
                    ))
                
                # Start new section
                current_section = stripped[3:].strip()
                current_section_idx += 1
                current_section_turns = []
            
            # Turn: **[Txx-NNN]** content
            elif stripped.startswith('**[') and ']**' in stripped:
                turn = self._parse_turn(stripped, lecture_id, turn_index, current_section_idx)
                if turn:
                    current_section_turns.append(turn)
                    turn_index += 1
            
            # Skip metadata lines
            elif stripped.startswith('>') or not stripped:
                continue
        
        # Save last section
        if current_section and current_section_turns:
            sections.append(Section(
                id=f"section_{current_section_idx:02d}",
                title=current_section,
                section_index=current_section_idx,
                turns=current_section_turns
            ))
        
        return sections
    
    def _parse_turn(self, line: str, lecture_id: str, turn_index: int, section_idx: int) -> Optional[Turn]:
        """Parse a single turn line"""
        
        # Extract turn ID: **[T01-001]**
        id_match = re.search(r'\[(T\d{2}-\d{3})\]', line)
        if not id_match:
            return None
        
        turn_id = id_match.group(1)
        
        # Extract content (after ** and before any markdown)
        content_match = re.search(r'\]\*\*\s*(.+?)(?:\s*\[|$)', line, re.DOTALL)
        content = content_match.group(1).strip() if content_match else ""
        
        if not content:
            return None
        
        # Check for activity
        if '[Hoạt động lớp:' in content:
            return Turn(
                id=turn_id,
                speaker="activity",
                speaker_label=None,
                content=content,
                is_activity=True
            )
        
        # Check for student input
        if '[học viên]:' in content or '[Học viên]:' in content:
            return Turn(
                id=turn_id,
                speaker="student",
                speaker_label="học viên",
                content=content
            )
        
        # Check for illegible
        if '[không nghe rõ]' in content:
            return Turn(
                id=turn_id,
                speaker="tutor",
                speaker_label=None,
                content=content,
                is_illegible=True
            )
        
        # Default: tutor
        return Turn(
            id=turn_id,
            speaker="tutor",
            speaker_label=None,
            content=content
        )


class IngestionPipeline:
    """Main ingestion pipeline"""
    
    def __init__(self, qdrant_url: str, qdrant_key: str,
                 neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        self.neo4j = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.parser = TranscriptParser()
        
        # Ensure collections exist
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure VectorDB collections exist"""
        vector_size = 1536  # text-embedding-3-small
        
        for collection_name in ['transcript_turns', 'transcript_sections', 'transcript_lectures']:
            try:
                self.qdrant.get_collection(collection_name)
            except:
                self.qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
    
    def run(self, transcript_path: str) -> Dict[str, Any]:
        """Main ingestion pipeline"""
        
        # Step 1: Parse transcript
        lecture = self.parser.parse(transcript_path)
        
        # Step 2: Create chunks
        turn_chunks = self._create_turn_chunks(lecture)
        section_chunks = self._create_section_chunks(lecture)
        lecture_chunk = self._create_lecture_chunk(lecture)
        
        # Step 3: Extract metadata
        metadata = self._extract_metadata(lecture)
        
        # Step 4: Insert to databases
        self._insert_to_vector_db(turn_chunks, section_chunks, lecture_chunk)
        self._insert_to_neo4j(lecture, metadata)
        
        return {
            "lecture_id": lecture.id,
            "lecture_title": lecture.title,
            "section_count": len(lecture.sections),
            "turn_count": sum(len(s.turns) for s in lecture.sections),
            "topics_extracted": len(metadata.topics),
            "concepts_extracted": len(metadata.concepts)
        }
    
    def _create_turn_chunks(self, lecture: Lecture) -> List[Dict]:
        """Create chunks for each turn (1 câu = 1 chunk)"""
        chunks = []
        
        for section in lecture.sections:
            for turn in section.turns:
                chunks.append({
                    "id": turn.id,
                    "lecture_id": lecture.id,
                    "lecture_title": lecture.title,
                    "lecture_day": lecture.day,
                    "section_id": section.id,
                    "section_title": section.title,
                    "section_index": section.section_index,
                    "turn_index": int(turn.id.split('-')[1]),
                    "speaker": turn.speaker,
                    "speaker_label": turn.speaker_label,
                    "content": turn.content,
                    "is_activity": turn.is_activity,
                    "is_illegible": turn.is_illegible,
                    "raw_ref": lecture.source_file
                })
        
        return chunks
    
    def _create_section_chunks(self, lecture: Lecture) -> List[Dict]:
        """Create chunks for each section (1 section = 1 chunk)"""
        chunks = []
        
        for section in lecture.sections:
            # Combine all turns into one content
            content_parts = []
            for turn in section.turns:
                content_parts.append(f"**[{turn.id}]** {turn.content}")
            full_content = "\n\n".join(content_parts)
            
            chunks.append({
                "id": section.id,
                "lecture_id": lecture.id,
                "lecture_title": lecture.title,
                "lecture_day": lecture.day,
                "section_id": section.id,
                "title": section.title,
                "section_index": section.section_index,
                "content": full_content,
                "turn_count": len(section.turns),
                "turn_ids": [t.id for t in section.turns],
                "has_student_input": any(t.speaker == "student" for t in section.turns)
            })
        
        return chunks
    
    def _create_lecture_chunk(self, lecture: Lecture) -> Dict:
        """Create single chunk for entire lecture"""
        section_parts = []
        for section in lecture.sections:
            section_parts.append(f"## {section.title}\n\n")
            for turn in section.turns:
                section_parts.append(f"**[{turn.id}]** {turn.content}\n\n")
        
        return {
            "id": lecture.id,
            "lecture_id": lecture.id,
            "title": lecture.title,
            "day": lecture.day,
            "source": lecture.source_file,
            "content": "".join(section_parts),
            "section_count": len(lecture.sections),
            "section_ids": [s.id for s in lecture.sections]
        }
    
    def _extract_metadata(self, lecture: Lecture) -> ExtractedMetadata:
        """Use LLM to extract topics, concepts, questions, references"""
        import openai
        
        # Combine all content for context
        all_content = f"# {lecture.title}\n\n"
        for section in lecture.sections:
            all_content += f"## {section.title}\n\n"
            for turn in section.turns:
                all_content += f"[{turn.id}]: {turn.content}\n\n"
        
        prompt = f"""
Bạn là chuyên gia AI. Trích xuất thông tin từ transcript bài giảng:

{all_content[:8000]}

Trả về JSON với cấu trúc:
{{
    "topics": ["topic1", "topic2", ...],  // 5-10 chủ đề chính
    "concepts": ["concept1", "concept2", ...],  // 5-10 khái niệm quan trọng
    "questions": ["câu hỏi 1?", "câu hỏi 2?", ...],  // 3-5 câu hỏi nổi bật
    "references": [{{"title": "...", "author": "...", "type": "book"}}]  // Sách/bài viết được đề cập
}}
"""
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        import json
        data = json.loads(response.choices[0].message.content)
        
        return ExtractedMetadata(
            topics=data.get("topics", []),
            concepts=data.get("concepts", []),
            questions=data.get("questions", []),
            references=data.get("references", [])
        )
    
    def _insert_to_vector_db(self, turn_chunks, section_chunks, lecture_chunk):
        """Insert chunks to Qdrant"""
        import openai
        
        # Insert turn chunks
        for chunk in turn_chunks:
            embedding = openai.Embedding.create(
                input=chunk["content"][:2000],  # Limit for embedding
                model="text-embedding-3-small"
            )["data"][0]["embedding"]
            
            self.qdrant.upsert(
                collection_name="transcript_turns",
                points=[PointStruct(
                    id=chunk["id"],
                    vector=embedding,
                    payload=chunk
                )]
            )
        
        # Insert section chunks
        for chunk in section_chunks:
            embedding = openai.Embedding.create(
                input=chunk["content"][:4000],
                model="text-embedding-3-small"
            )["data"][0]["embedding"]
            
            self.qdrant.upsert(
                collection_name="transcript_sections",
                points=[PointStruct(
                    id=chunk["id"],
                    vector=embedding,
                    payload=chunk
                )]
            )
        
        # Insert lecture chunk
        embedding = openai.Embedding.create(
            input=lecture_chunk["content"][:8000],
            model="text-embedding-3-small"
        )["data"][0]["embedding"]
        
        self.qdrant.upsert(
            collection_name="transcript_lectures",
            points=[PointStruct(
                id=lecture_chunk["id"],
                vector=embedding,
                payload=lecture_chunk
            )]
        )
    
    def _insert_to_neo4j(self, lecture: Lecture, metadata: ExtractedMetadata):
        """Insert to Neo4j"""
        
        with self.neo4j.session() as session:
            # Create Lecture node
            session.run("""
                MERGE (l:Lecture {id: $id})
                SET l.title = $title,
                    l.day = $day,
                    l.source_file = $source,
                    l.section_count = $section_count,
                    l.turn_count = $turn_count,
                    l.created_at = datetime()
            """, {
                "id": lecture.id,
                "title": lecture.title,
                "day": lecture.day,
                "source": lecture.source_file,
                "section_count": len(lecture.sections),
                "turn_count": sum(len(s.turns) for s in lecture.sections)
            })
            
            # Create Section nodes and relationships
            for section in lecture.sections:
                session.run("""
                    MERGE (s:Section {id: $id})
                    SET s.title = $title,
                        s.section_index = $idx,
                        s.lecture_id = $lecture_id,
                        s.turn_count = $turn_count,
                        s.has_student_input = $has_student
                    
                    WITH s
                    MATCH (l:Lecture {id: $lecture_id})
                    MERGE (s)-[:BELONGS_TO {section_index: $idx}]->(l)
                """, {
                    "id": section.id,
                    "title": section.title,
                    "idx": section.section_index,
                    "lecture_id": lecture.id,
                    "turn_count": len(section.turns),
                    "has_student": any(t.speaker == "student" for t in section.turns)
                })
                
                # Create Turn nodes
                for turn in section.turns:
                    session.run("""
                        MERGE (t:Turn {id: $id})
                        SET t.content = $content,
                            t.speaker = $speaker,
                            t.speaker_label = $label,
                            t.is_activity = $is_activity,
                            t.is_illegible = $is_illegible,
                            t.section_id = $section_id,
                            t.lecture_id = $lecture_id,
                            t.turn_index = $turn_idx
                        
                        WITH t
                        MATCH (s:Section {id: $section_id})
                        MERGE (t)-[:BELONGS_TO]->(s)
                    """, {
                        "id": turn.id,
                        "content": turn.content[:500],  # Truncate for Neo4j
                        "speaker": turn.speaker,
                        "label": turn.speaker_label,
                        "is_activity": turn.is_activity,
                        "is_illegible": turn.is_illegible,
                        "section_id": section.id,
                        "lecture_id": lecture.id,
                        "turn_idx": int(turn.id.split('-')[1])
                    })
            
            # Create Concept nodes
            for concept in metadata.concepts:
                session.run("""
                    MERGE (c:Concept {name: $name})
                    SET c.frequency = coalesce(c.frequency, 0) + 1,
                        c.lecture_id = $lecture_id,
                        c.updated_at = datetime()
                """, {"name": concept, "lecture_id": lecture.id})
            
            # Create Question nodes
            for question in metadata.questions:
                session.run("""
                    MERGE (q:Question {text: $text})
                    SET q.type = 'conceptual',
                        q.lecture_id = $lecture_id
                """, {"text": question, "lecture_id": lecture.id})
            
            # Create Reference nodes
            for ref in metadata.references:
                session.run("""
                    MERGE (r:Reference {title: $title})
                    SET r.author = $author,
                        r.type = $type
                """, {
                    "title": ref.get("title", ""),
                    "author": ref.get("author", ""),
                    "type": ref.get("type", "other")
                })


# Usage example
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    pipeline = IngestionPipeline(
        qdrant_url=os.getenv("QDRANT_HOST"),
        qdrant_key=os.getenv("QDRANT_API_KEY"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USERNAME"),
        neo4j_password=os.getenv("NEO4J_PASSWORD")
    )
    
    result = pipeline.run("data/vlearn-pack/transcript/transcript-01-clean.md")
    print(f"Done: {result}")
```
```

---

## 4. Luong 2: Intent Detection

### 4.1 Muc tieu
Phan tich cau hoi nguoi dung de xac dinh intent type, tu do route den handler phu hop.

### 4.2 Intent Types

| Intent | Mo ta | Vi du | Handler |
|--------|-------|-------|---------|
| `SEMANTIC_SEARCH` | Tra cuu semantic thuan tuy | "Transformer la gi?" | VectorDB only |
| `GRAPH_QUERY` | Tra cuu cau truc, quan he | "Concept nao lien quan den Agent?" | Neo4j only |
| `MULTI_HOP` | Tra cuu nhieu buoc | "Transformer lien quan Agent nhu the nao?" | Hybrid |
| `COMPARISON` | So sanh 2 doi tuong | "Khac nhau Automation vs Augmentation?" | Hybrid + Synthesis |
| `RECOMMEND` | De xuat learning path | "Nen hoc gi tiep theo?" | Graph-based |
| `SUMMARY` | Tom tat noi dung | "Tom tat bai giang hom nay" | VectorDB + Synthesis |

### 4.3 Implementation

```python
# scripts/intent_router.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
import openai

class IntentType(Enum):
    SEMANTIC_SEARCH = "semantic_search"
    GRAPH_QUERY = "graph_query"
    MULTI_HOP = "multi_hop"
    COMPARISON = "comparison"
    RECOMMEND = "recommend"
    SUMMARY = "summary"
    UNKNOWN = "unknown"

@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    entities: List[str]  # Entities extracted from query
    parameters: dict  # Additional parameters

class IntentRouter:
    """LLM-based intent detection router"""
    
    SYSTEM_PROMPT = """Ban la mot router cho he thong hoc tap AI. 
Phan tich cau hoi nguoi dung va tra ve intent phu hop.

INTENT TYPES:
1. semantic_search: Hoi ve dinh nghia, giai thich don gian. 
   VD: "Transformer la gi?", "AI Generation la gi?"
   
2. graph_query: Hoi ve quan he, cau truc, cac muc lien quan.
   VD: "Concept nao lien quan den Agent?", "Topic nao thuoc Transformer?"
   
3. multi_hop: Hoi ve lien he phuc tap nhieu buoc.
   VD: "Transformer lien quan gi den Agent?", "AI co the gi giup doanh nghiep?"
   
4. comparison: So sanh 2 hoac nhieu doi tuong.
   VD: "Khac nhau giua Automation va Augmentation?", "So sanh Agent va Assistant"
   
5. recommend: De xuat noi dung hoc tiep theo.
   VD: "Nen hoc gi tiep theo?", "Goi y bai hoc tiep"
   
6. summary: Tom tat, tong hop noi dung.
   VD: "Tom tat bai giang hom nay", "Noi dung chinh cua buoi hoc"

Tra ve JSON voi cau truc:
{
    "intent": "intent_type",
    "confidence": 0.95,
    "entities": ["entity1", "entity2"],
    "parameters": {{"key": "value"}}
}}
"""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
    
    def detect(self, query: str) -> IntentResult:
        """Detect intent from user query"""
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Câu hỏi: {query}"}
            ],
            response_format={"type": "json_object"}
        )
        
        import json
        data = json.loads(response.choices[0].message.content)
        
        return IntentResult(
            intent=IntentType(data["intent"]),
            confidence=data.get("confidence", 0.8),
            entities=data.get("entities", []),
            parameters=data.get("parameters", {})
        )
    
    def route(self, query: str) -> str:
        """Route to appropriate handler based on intent"""
        result = self.detect(query)
        
        handler_map = {
            IntentType.SEMANTIC_SEARCH: "handle_semantic_search",
            IntentType.GRAPH_QUERY: "handle_graph_query",
            IntentType.MULTI_HOP: "handle_multi_hop",
            IntentType.COMPARISON: "handle_comparison",
            IntentType.RECOMMEND: "handle_recommend",
            IntentType.SUMMARY: "handle_summary",
        }
        
        return handler_map.get(result.intent, "handle_unknown")
```

---

## 5. Luong 3: Semantic Search

### 5.1 Muc tieu
Tra cuu noi dung semantic nhanh bang VectorDB.

### 5.2 Flow Chi Tiet

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LUONG 3: SEMANTIC SEARCH                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  INPUT: "Transformer la gi?"                                                        │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  code/python:                                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  async def handle_semantic_search(                                     │ │  │
│  │  │      query: str,                                                        │ │  │
│  │  │      top_k: int = 5,                                                   │ │  │
│  │  │      filter_params: dict = None                                        │ │  │
│  │  │  ):                                                                    │ │  │
│  │  │                                                                       │ │  │
│  │  │      # 1. Embed query                                                 │ │  │
│  │  │      query_vector = await embedder.embed(query)                        │ │  │
│  │  │                                                                       │ │  │
│  │  │      # 2. Search VectorDB                                             │ │  │
│  │  │      results = await qdrant.search(                                   │ │  │
│  │  │          collection_name="transcript_chunks",                          │ │  │
│  │  │          query_vector=query_vector,                                   │ │  │
│  │  │          query_filter=filter_params,                                   │ │  │
│  │  │          limit=top_k                                                   │ │  │
│  │  │      )                                                                 │ │  │
│  │  │                                                                       │ │  │
│  │  │      # 3. Format response                                             │ │  │
│  │  │      return [                                                           │ │  │
│  │  │          {                                                             │ │  │
│  │  │              "content": r.payload["content"],                          │ │  │
│  │  │              "score": r.score,                                         │ │  │
│  │  │              "lecture": r.payload.get("lecture_title"),                │ │  │
│  │  │              "topics": r.payload.get("topics", [])                     │ │  │
│  │  │          }                                                             │ │  │
│  │  │          for r in results                                              │ │  │
│  │  │      ]                                                                 │ │  │
│  │  │                                                                       │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  OUTPUT:                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  [                                                                           │  │
│  │    {{                                                                        │  │
│  │      "content": "Transformer la kien truc core cua LLM, su dung...",        │  │
│  │      "score": 0.94,                                                         │  │
│  │      "lecture": " Gioi thieu ve Transformer",                              │  │
│  │      "topics": ["Transformer", "LLM Architecture"]                         │  │
│  │    }},                                                                       │  │
│  │    ...                                                                      │  │
│  │  ]                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Implementation

```python
# scripts/handlers/semantic_search.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

@dataclass
class SearchResult:
    content: str
    score: float
    lecture_id: str
    lecture_title: str
    topics: List[str]
    concepts: List[str]

class SemanticSearchHandler:
    """Handle semantic search queries using VectorDB"""
    
    def __init__(self, qdrant_client, embedder):
        self.qdrant = qdrant_client
        self.embedder = embedder
        self.collection = "transcript_chunks"
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        lecture_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        content_type: Optional[str] = None,
        speaker: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for relevant content
        
        Args:
            query: User query string
            top_k: Number of results to return
            lecture_id: Filter by specific lecture
            topics: Filter by topics (OR logic)
            content_type: Filter by content type (turn, topic, concept)
            speaker: Filter by speaker (tutor, student)
        
        Returns:
            List of search results ranked by relevance
        """
        
        # 1. Embed query
        query_vector = await self.embedder.embed(query)
        
        # 2. Build filter
        filters = self._build_filters(
            lecture_id=lecture_id,
            topics=topics,
            content_type=content_type,
            speaker=speaker
        )
        
        # 3. Search
        results = await self.qdrant.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=filters,
            limit=top_k,
            with_payload=True
        )
        
        # 4. Format results
        return [
            SearchResult(
                content=r.payload["content"],
                score=r.score,
                lecture_id=r.payload.get("lecture_id", ""),
                lecture_title=r.payload.get("lecture_title", ""),
                topics=r.payload.get("topics", []),
                concepts=r.payload.get("concepts", [])
            )
            for r in results
        ]
    
    def _build_filters(
        self,
        lecture_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        content_type: Optional[str] = None,
        speaker: Optional[str] = None
    ) -> Optional[Filter]:
        """Build Qdrant filter from parameters"""
        
        conditions = []
        
        if lecture_id:
            conditions.append(
                FieldCondition(
                    key="lecture_id",
                    match=MatchValue(value=lecture_id)
                )
            )
        
        if topics:
            # OR logic for topics
            conditions.append(
                FieldCondition(
                    key="topics",
                    match=MatchValue(any=topics)
                )
            )
        
        if content_type:
            conditions.append(
                FieldCondition(
                    key="content_type",
                    match=MatchValue(value=content_type)
                )
            )
        
        if speaker:
            conditions.append(
                FieldCondition(
                    key="speaker_role",
                    match=MatchValue(value=speaker)
                )
            )
        
        if conditions:
            return Filter(must=conditions)
        return None
    
    async def get_context_for_synthesis(
        self,
        query: str,
        max_results: int = 10
    ) -> str:
        """Get formatted context string for LLM synthesis"""
        
        results = await self.search(query, top_k=max_results)
        
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"[Result {i}] (Score: {r.score:.2f}, Lecture: {r.lecture_title})\n"
                f"{r.content}\n"
                f"Topics: {', '.join(r.topics)}"
            )
        
        return "\n\n".join(context_parts)
```

---

## 6. Luong 4: Graph Query

### 6.1 Muc tieu
Tra cuu cau truc quan he trong Knowledge Graph.

### 6.2 Flow Chi Tiet

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LUONG 4: GRAPH QUERY                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  INPUT: "Concept nao lien quan den Agent?"                                           │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  QUERY 1: Tim Concept "Agent"                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  MATCH (c:Concept {name: "Agent"})                                     │ │  │
│  │  │  RETURN c                                                               │ │  │
│  │  │                                                                         │ │  │
│  │  │  Result: {{id: "concept_001", name: "Agent", description: "..."}}       │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  QUERY 2: Tim cac concept cung thuoc Topic voi Agent                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  MATCH (c:Concept {name: "Agent"})-[:BELONGS_TO]->(t:Topic)            │ │  │
│  │  │  MATCH (other:Concept)-[:BELONGS_TO]->(t)                              │ │  │
│  │  │  WHERE other <> c                                                      │ │  │
│  │  │  RETURN other                                                          │ │  │
│  │  │                                                                         │ │  │
│  │  │  Result: ["Workflow", "Task Planning", "Tool Use", ...]                 │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  QUERY 3: Tim cac Topic/Concept lien quan truc tiep                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  MATCH (c:Concept {name: "Agent"})-[:RELATED_TO*1..2]-(other)           │ │  │
│  │  │  RETURN other                                                          │ │  │
│  │  │                                                                         │ │  │
│  │  │  Result: ["Transformer", "LLM", "Automation", ...]                     │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  OUTPUT:                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  {{                                                                      │  │
│  │    "concept": {{                                                          │  │
│  │      "name": "Agent",                                                    │  │
│  │      "description": "AI co the suy nghi va hanh dong tu dong..."          │  │
│  │    }},                                                                   │  │
│  │    "related_concepts": ["Workflow", "Task Planning", "Tool Use"],         │  │
│  │    "prerequisites": ["Transformer", "LLM"],                               │  │
│  │    "topics": ["AI Agent", "Autonomous AI"]                                │  │
│  │  }}                                                                      │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Implementation

```python
# scripts/handlers/graph_query.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from neo4j import GraphDatabase

@dataclass
class ConceptInfo:
    id: str
    name: str
    description: str
    frequency: int

@dataclass
class GraphQueryResult:
    concept: Optional[ConceptInfo]
    related_concepts: List[ConceptInfo]
    prerequisites: List[str]
    related_topics: List[str]
    lectures: List[Dict[str, str]]

class GraphQueryHandler:
    """Handle graph-based queries using Neo4j"""
    
    def __init__(self, neo4j_driver: GraphDatabase):
        self.driver = neo4j_driver
    
    async def query_concept_relations(self, concept_name: str) -> GraphQueryResult:
        """
        Query all relations for a concept
        
        Returns:
            GraphQueryResult with concept info and related entities
        """
        
        with self.driver.session() as session:
            # 1. Get concept info
            concept_data = session.run("""
                MATCH (c:Concept {name: $name})
                RETURN c.id as id, c.name as name, 
                       c.description as description,
                       c.frequency as frequency
            """, name=concept_name).single()
            
            concept = None
            if concept_data:
                concept = ConceptInfo(
                    id=concept_data["id"],
                    name=concept_data["name"],
                    description=concept_data.get("description", ""),
                    frequency=concept_data.get("frequency", 0)
                )
            
            # 2. Get related concepts (same topic)
            related = session.run("""
                MATCH (c:Concept {name: $name})-[:BELONGS_TO]->(t:Topic)
                MATCH (other:Concept)-[:BELONGS_TO]->(t)
                WHERE other <> c
                RETURN other.id as id, other.name as name,
                       other.description as description
            """, name=concept_name).data()
            
            related_concepts = [
                ConceptInfo(
                    id=r["id"],
                    name=r["name"],
                    description=r.get("description", ""),
                    frequency=0
                )
                for r in related
            ]
            
            # 3. Get prerequisites (RELATED_TO with type=prerequisite)
            prerequisites = session.run("""
                MATCH (c:Concept {name: $name})-[r:RELATED_TO]-(other)
                WHERE r.type = 'prerequisite' OR r.type = 'requires'
                RETURN other.name as name
            """, name=concept_name).data()
            
            prereq_names = [r["name"] for r in prerequisites]
            
            # 4. Get related topics
            topics = session.run("""
                MATCH (c:Concept {name: $name})-[:BELONGS_TO]->(t:Topic)
                MATCH (l:Lecture)-[:INTRODUCES]->(t)
                RETURN DISTINCT t.name as name, l.title as lecture_title
            """, name=concept_name).data()
            
            related_topics = [t["name"] for t in topics]
            lectures = [{"title": t["lecture_title"]} for t in topics]
            
            return GraphQueryResult(
                concept=concept,
                related_concepts=related_concepts,
                prerequisites=prereq_names,
                related_topics=related_topics,
                lectures=lectures
            )
    
    async def query_topic_content(self, topic_name: str) -> Dict[str, Any]:
        """Get all content related to a topic"""
        
        with self.driver.session() as session:
            # Get topic info
            topic_data = session.run("""
                MATCH (t:Topic {name: $name})
                RETURN t.id as id, t.name as name, 
                       t.description as description,
                       t.frequency as frequency
            """, name=topic_name).single()
            
            # Get all concepts under this topic
            concepts = session.run("""
                MATCH (t:Topic {name: $name})-[:COVERS]->(c:Concept)
                RETURN c.name as name, c.description as description
            """, name=topic_name).data()
            
            # Get lectures introducing this topic
            lectures = session.run("""
                MATCH (l:Lecture)-[:INTRODUCES]->(t:Topic {name: $name})
                RETURN l.id as id, l.title as title, l.order as order
                ORDER BY l.order
            """, name=topic_name).data()
            
            # Get questions related to this topic
            questions = session.run("""
                MATCH (l:Lecture)-[:INTRODUCES]->(t:Topic {name: $name})
                MATCH (l)-[:HAS_QUESTION]->(q:Question)
                RETURN q.text as text
            """, name=topic_name).data()
            
            return {
                "topic": topic_data,
                "concepts": concepts,
                "lectures": lectures,
                "questions": questions
            }
    
    async def get_learning_path(self, current_topic: str) -> List[Dict[str, Any]]:
        """Get recommended learning path after a topic"""
        
        with self.driver.session() as session:
            # Find topics that commonly follow this topic
            # (based on lecture order and frequency)
            path = session.run("""
                MATCH (current:Topic {name: $name})
                MATCH (l:Lecture)-[:INTRODUCES]->(current)
                WITH l, current
                
                // Find next topics in same or related lectures
                MATCH (next_l:Lecture)-[:INTRODUCES]->(next_t:Topic)
                WHERE next_l.order > l.order 
                   OR (next_l.order = l.order AND next_t.frequency > current.frequency)
                
                // Calculate priority score
                WITH next_t, 
                     count(*) as lecture_count,
                     max(next_t.frequency) as freq
                ORDER BY lecture_count DESC, freq DESC
                
                RETURN next_t.name as topic,
                       next_t.description as description,
                       lecture_count as weight,
                       freq as frequency
                LIMIT 5
            """, name=current_topic).data()
            
            return path
```

---

## 7. Luong 5: Multi-Hop

### 7.1 Muc tieu
Tra cuu nhieu buoc, ket hop VectorDB va Neo4j de tra loi cau hoi phuc tap.

### 7.2 Flow Chi Tiet

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LUONG 5: MULTI-HOP                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  INPUT: "Transformer lien quan gi den Agent nhu the nao?"                           │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1: Entity Extraction (LLM)                                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Input: "Transformer lien quan gi den Agent nhu the nao?"               │ │  │
│  │  │  Output: ["Transformer", "Agent"]                                       │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                         ┌──────────┴──────────┐                                    │
│                         ▼                      ▼                                     │
│  ┌────────────────────────────────────┐  ┌────────────────────────────────────┐     │
│  │  STEP 2a: VECTOR SEARCH           │  │  STEP 2b: GRAPH TRAVERSAL         │     │
│  │                                   │  │                                    │     │
│  │  Search both entities:            │  │  Find paths between them:         │     │
│  │  ┌─────────────────────────────┐ │  │  ┌─────────────────────────────┐ │     │
│  │  │ Query: "Transformer"        │ │  │  │ MATCH path = (               │ │     │
│  │  │ Results: 5 chunks (0.92+)   │ │  │  │   t1:Topic {name:"Transform"}-│ │     │
│  │  │                             │ │  │  │   r1:RELATED_TO*1..3]-      │ │     │
│  │  │ Query: "Agent"              │ │  │  │   t2:Topic {name:"Agent"}   │ │     │
│  │  │ Results: 5 chunks (0.90+)  │ │  │  │ )                           │ │     │
│  │  └─────────────────────────────┘ │  │  │ RETURN path                 │ │     │
│  │                                   │  │  └─────────────────────────────┘ │     │
│  └────────────────────────────────────┘  │                                    │     │
│                                           └────────────────────────────────────┘     │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 3: FIND COMMON GROUND                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Graph Analysis:                                                        │ │  │
│  │  │                                                                         │ │  │
│  │  │  Transformer ────INTRODUCES──▶ Lecture ────INTRODUCES──▶ Agent         │ │  │
│  │  │       │                                    │                            │ │  │
│  │  │       │                                    │                            │ │  │
│  │  │       ▼                                    ▼                            │ │  │
│  │  │  "LLM Architecture"            "AI that can reason and act"           │ │  │
│  │  │                                                                         │ │  │
│  │  │  Common ground: Ca hai deu la phan cua AI Agent framework              │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 4: LLM SYNTHESIS                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Prompt:                                                                 │ │  │
│  │  │  "Ban la mot giao suen AI. Dua tren thong tin sau, giai thich mqh      │ │  │
│  │  │   giua Transformer va Agent:                                           │ │  │
│  │  │                                                                           │ │  │
│  │  │  1. Transformer la gi?                                                   │ │  │
│  │  │     - Kien truc encoder-decoder                                          │ │  │
│  │  │     - Su dung Self-Attention                                             │ │  │
│  │  │     - La nen tang cua LLM                                                │ │  │
│  │  │                                                                           │ │  │
│  │  │  2. Agent la gi?                                                         │ │  │
│  │  │     - He thong AI co kha nang reasoning va acting                       │ │  │
│  │  │     - Su dung LLM de hieu va quyet dinh                                  │ │  │
│  │  │                                                                           │ │  │
│  │  │  3. Moi lien he:                                                         │ │  │
│  │  │     - Agent su dung Transformer/LLM lam nhan biet                       │ │  │
│  │  │     - Transformer cung cap kha nang hieu ngon ngu                       │ │  │
│  │  │     - Agent la ung dung cua Transformer                                  │ │  │
│  │  │  "                                                                       │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  OUTPUT:                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  "Transformer la nen tang kiến trúc, Agent la ung dung su dung nen tang    │  │
│  │   do. Cu the, Transformer cung cap kha nang xu ly ngon ngu thong qua       │  │
│  │   Self-Attention, trong khi Agent su dung kha nang nay de hieu yeu cau,     │  │
│  │   reasoning, va ra quyet dinh hanh dong phu hop..."                        │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Implementation

```python
# scripts/handlers/multi_hop.py

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import openai

@dataclass
class HopResult:
    entity: str
    content: str
    score: float
    source: str  # "vector" or "graph"

class MultiHopHandler:
    """Handle multi-hop queries combining VectorDB and Neo4j"""
    
    def __init__(self, qdrant_client, neo4j_driver, embedder):
        self.qdrant = qdrant_client
        self.neo4j = neo4j_driver
        self.embedder = embedder
    
    async def query(self, query: str) -> str:
        """
        Execute multi-hop query
        
        Flow:
        1. Extract entities from query
        2. Search VectorDB for each entity
        3. Traverse Graph for relationships
        4. Find common ground
        5. Synthesize answer with LLM
        """
        
        # Step 1: Extract entities
        entities = await self._extract_entities(query)
        
        if len(entities) < 2:
            # Fallback to semantic search if only 1 entity
            return await self._simple_search(entities[0] if entities else query)
        
        # Step 2: Parallel search (VectorDB + Graph)
        vector_results = await self._vector_search(entities)
        graph_results = await self._graph_traverse(entities)
        
        # Step 3: Find paths/connections
        connections = await self._find_connections(entities)
        
        # Step 4: Synthesize
        synthesis = await self._synthesize(
            entities=entities,
            vector_results=vector_results,
            graph_results=graph_results,
            connections=connections,
            query=query
        )
        
        return synthesis
    
    async def _extract_entities(self, query: str) -> List[str]:
        """Extract main entities from query"""
        
        prompt = f"""
        Trich xuat cac thuc the chinh (danh tu rieng, khai niem) trong cau hoi:
        "{query}"
        
        Chi tra ve danh sach cac thuc the, moi thuc the tren 1 dong.
        Neu khong co, tra ve empty string.
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        entities = [e.strip() for e in response.choices[0].message.content.split('\n') if e.strip()]
        return entities
    
    async def _vector_search(self, entities: List[str]) -> Dict[str, List[HopResult]]:
        """Search VectorDB for each entity"""
        
        results = {}
        
        for entity in entities:
            query_vector = await self.embedder.embed(entity)
            
            search_results = await self.qdrant.search(
                collection_name="transcript_chunks",
                query_vector=query_vector,
                limit=5
            )
            
            results[entity] = [
                HopResult(
                    entity=entity,
                    content=r.payload["content"],
                    score=r.score,
                    source="vector"
                )
                for r in search_results
            ]
        
        return results
    
    async def _graph_traverse(self, entities: List[str]) -> Dict[str, Any]:
        """Traverse Neo4j graph to find relationships"""
        
        with self.neo4j.session() as session:
            # Find shortest path between entities
            if len(entities) >= 2:
                paths = session.run("""
                    MATCH path = shortestPath(
                        (a {name: $entity1})-[*1..5]-(b {name: $entity2})
                    )
                    RETURN path
                """, entity1=entities[0], entity2=entities[1]).data()
                
                # Get nodes along the path
                nodes = []
                for path in paths:
                    for node in path["path"].nodes:
                        nodes.append({
                            "name": node.get("name", node.get("title", "")),
                            "type": list(node.labels)[0]
                        })
                
                return {"paths": nodes, "entities": entities}
            
            return {"paths": [], "entities": entities}
    
    async def _find_connections(self, entities: List[str]) -> Dict[str, Any]:
        """Find common ground between entities"""
        
        with self.neo4j.session() as session:
            # Find common neighbors
            common = session.run("""
                MATCH (a {name: $entity1})
                MATCH (b {name: $entity2})
                MATCH (a)-[]-(common)-[](b)
                RETURN DISTINCT common.name as name, 
                       labels(common)[0] as type
            """, entity1=entities[0], entity2=entities[1]).data()
            
            # Find shared topics
            shared_topics = session.run("""
                MATCH (t1:Topic)-[:COVERS]-(a {name: $entity1})
                MATCH (t2:Topic)-[:COVERS]-(b {name: $entity2})
                WHERE t1 = t2
                RETURN t1.name as topic
            """, entity1=entities[0], entity2=entities[1]).data()
            
            return {
                "common_neighbors": common,
                "shared_topics": [t["topic"] for t in shared_topics]
            }
    
    async def _synthesize(
        self,
        entities: List[str],
        vector_results: Dict[str, List[HopResult]],
        graph_results: Dict[str, Any],
        connections: Dict[str, Any],
        query: str
    ) -> str:
        """Synthesize answer from all sources"""
        
        # Build context
        context_parts = [f"Câu hỏi: {query}\n"]
        
        # Add entity information
        for entity in entities:
            context_parts.append(f"\n## {entity}")
            if entity in vector_results:
                for r in vector_results[entity][:2]:
                    context_parts.append(f"- {r.content[:200]}...")
        
        # Add connections
        if connections.get("shared_topics"):
            context_parts.append(f"\n## Điểm chung")
            context_parts.append(f"Các topic chung: {', '.join(connections['shared_topics'])}")
        
        if connections.get("common_neighbors"):
            context_parts.append(f"\nCác khái niệm liên quan: ")
            for n in connections["common_neighbors"][:3]:
                context_parts.append(f"- {n['name']} ({n['type']})")
        
        context = "\n".join(context_parts)
        
        # Synthesize with LLM
        synthesis_prompt = f"""
        Ban la mot giao suen AI. Dua tren thong tin sau, tra loi cau hoi nguoi dung:
        
        {context}
        
        Câu hỏi: {query}
        
        Yêu cầu:
        1. Giai thich moi quan he giua cac thuc the
        2. Dua ra vi du cu the neu co
        3. Neu co diem chung, noi bat
        4. Ngon ngu: Tieng Viet, de hieu
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    async def _simple_search(self, entity: str) -> str:
        """Fallback to simple semantic search"""
        
        query_vector = await self.embedder.embed(entity)
        
        results = await self.qdrant.search(
            collection_name="transcript_chunks",
            query_vector=query_vector,
            limit=5
        )
        
        context = "\n\n".join([f"- {r.payload['content']}" for r in results])
        
        prompt = f"""
        Dua tren thong tin sau, giai thich ve "{entity}":
        
        {context}
        
        Tra ve cau tra loi ngan gon, de hieu.
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
```

---

## 8. Luong 6: Comparison

### 8.1 Muc tieu
So sanh 2 doi tuong va tim diem chung.

### 8.2 Flow Chi Tiet

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LUONG 6: COMPARISON                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  INPUT: "Khac nhau giua Automation va Augmentation?"                                │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1: Extract entities to compare                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  LLM Detection:                                                         │ │  │
│  │  │  Entities: ["Automation", "Augmentation"]                               │ │  │
│  │  │  Comparison Type: "difference"                                         │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                         ┌──────────┴──────────┐                                    │
│                         ▼                      ▼                                     │
│  ┌────────────────────────────────────┐  ┌────────────────────────────────────┐     │
│  │  STEP 2a: Get Automation info    │  │  STEP 2b: Get Augmentation info   │     │
│  │                                   │  │                                    │     │
│  │  Neo4j Query:                     │  │  Neo4j Query:                     │     │
│  │  ┌─────────────────────────────┐ │  │  ┌─────────────────────────────┐ │     │
│  │  │ MATCH (a:Concept {           │ │  │  │ MATCH (a:Concept {           │ │     │
│  │  │   name: "Automation"        │ │  │  │   name: "Augmentation"      │ │     │
│  │  │ })                         │ │  │  │ })                         │ │     │
│  │  │ RETURN a                    │ │  │  │ RETURN a                    │ │     │
│  │  └─────────────────────────────┘ │  │  └─────────────────────────────┘ │     │
│  │                                   │  │                                    │     │
│  │  Result:                         │  │  Result:                          │     │
│  │  - "AI tu dong lam thay the"    │  │  - "AI ho tro con nguoi"          │     │
│  │  - Belongs to: Agent             │  │  - Belongs to: Agent              │     │
│  │  - Related: Workflow, Task       │  │  - Related: Human, Judgment      │     │
│  └────────────────────────────────────┘  └────────────────────────────────────┘     │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 3: Find common neighbors (Intersection)                                 │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Neo4j Query:                                                         │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────────────┐    │ │  │
│  │  │  │  MATCH (a:Concept {name: "Automation"})                       │    │ │  │
│  │  │  │  MATCH (b:Concept {name: "Augmentation"})                     │    │ │  │
│  │  │  │  MATCH (a)-[r1]-(common)-[r2]-(b)                             │    │ │  │
│  │  │  │  RETURN DISTINCT common                                        │    │ │  │
│  │  │  └─────────────────────────────────────────────────────────────────┘    │ │  │
│  │  │                                                                         │ │  │
│  │  │  Result:                                                               │ │  │
│  │  │  - Agent (ca hai deu la loai Agent)                                  │ │  │
│  │  │  - LLM (ca hai deu su dung LLM)                                       │ │  │
│  │  │  - Workflow (ca hai deu lien quan den workflow)                      │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 4: LLM Synthesis (Comparison Table)                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Prompt:                                                               │ │  │
│  │  │  "So sanh Automation va Augmentation:                                   │ │  │
│  │  │                                                                           │ │  │
│  │  │  AUTOMATION:                    │  AUGMENTATION:                       │ │  │
│  │  │  - AI thay the con nguoi        │  - AI ho tro con nguoi               │ │  │
│  │  │  - Khong can human oversight     │  - Human-in-the-loop                 │ │  │
│  │  │  - Tac vu lap, nhanh chong      │  - Quyet dinh phuc tap              │ │  │
│  │  │                                                                           │ │  │
│  │  │  DIEM CHUNG:                                                              │ │  │
│  │  │  - Ca hai deu la Agent, deu dung LLM, deu lien quan Workflow"           │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  OUTPUT:                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  | Tieu chi          | Automation           | Augmentation          |         │  │
│  │  |--------------------|----------------------|------------------------|---------|  │
│  │  | Muc dich           | Thay the con nguoi   | Ho tro con nguoi      |         │  │
│  │  | Human involvement  | Khong                | Co                    |         │  │
│  │  | Phu hop cho        | Tac vu lap, rut nhanh| Quyet dinh phuc tap   |         │  │
│  │  |--------------------|----------------------|------------------------|---------|  │
│  │  | DIEM CHUNG: Agent, LLM, Workflow                                     |         │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Implementation

```python
# scripts/handlers/comparison.py

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import openai

@dataclass
class EntityInfo:
    name: str
    description: str
    related_concepts: List[str]
    related_topics: List[str]

class ComparisonHandler:
    """Handle comparison queries"""
    
    def __init__(self, neo4j_driver, embedder):
        self.neo4j = neo4j_driver
        self.embedder = embedder
    
    async def compare(self, query: str) -> str:
        """
        Compare two or more entities
        
        Flow:
        1. Extract entities to compare
        2. Get info for each entity from Neo4j
        3. Find common ground
        4. Generate comparison table with LLM
        """
        
        # Step 1: Extract entities
        entities = await self._extract_entities(query)
        
        if len(entities) < 2:
            return "Cần ít nhất 2 đối tượng để so sánh."
        
        # Step 2: Get info for each entity
        entity_infos = []
        for entity in entities:
            info = await self._get_entity_info(entity)
            entity_infos.append(info)
        
        # Step 3: Find common ground
        common = await self._find_common_ground(entities)
        
        # Step 4: Generate comparison
        comparison = await self._generate_comparison(entity_infos, common, query)
        
        return comparison
    
    async def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from comparison query"""
        
        prompt = f"""
        Trich xuat 2 thuc the (khai niem) can so sanh trong cau hoi:
        "{query}"
        
        Chi tra ve 2 ten, moi ten tren 1 dong.
        VD: "Automation"
            "Augmentation"
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        entities = [e.strip() for e in response.choices[0].message.content.split('\n') if e.strip()]
        return entities[:2]  # Take first 2
    
    async def _get_entity_info(self, entity_name: str) -> EntityInfo:
        """Get detailed info for an entity from Neo4j"""
        
        with self.neo4j.session() as session:
            # Get concept info
            concept_data = session.run("""
                MATCH (c:Concept {name: $name})
                OPTIONAL MATCH (c)-[:BELONGS_TO]-(t:Topic)
                OPTIONAL MATCH (c)-[:RELATED_TO]-(other)
                RETURN c.name as name,
                       c.description as description,
                       collect(DISTINCT t.name) as topics,
                       collect(DISTINCT other.name) as related
            """, name=entity_name).single()
            
            if not concept_data:
                # Try Topic
                concept_data = session.run("""
                    MATCH (t:Topic {name: $name})
                    OPTIONAL MATCH (t)-[:COVERS]-(c:Concept)
                    OPTIONAL MATCH (t)-[:RELATED_TO]-(other)
                    RETURN t.name as name,
                           t.description as description,
                           collect(DISTINCT c.name) as concepts,
                           collect(DISTINCT other.name) as related
                """, name=entity_name).single()
                
                if concept_data:
                    return EntityInfo(
                        name=concept_data["name"],
                        description=concept_data.get("description", ""),
                        related_concepts=concept_data.get("concepts", []),
                        related_topics=[]
                    )
                
                return EntityInfo(
                    name=entity_name,
                    description="",
                    related_concepts=[],
                    related_topics=[]
                )
            
            return EntityInfo(
                name=concept_data["name"],
                description=concept_data.get("description", ""),
                related_concepts=concept_data.get("related", []),
                related_topics=concept_data.get("topics", [])
            )
    
    async def _find_common_ground(self, entities: List[str]) -> Dict[str, Any]:
        """Find common points between entities"""
        
        with self.neo4j.session() as session:
            # Find common neighbors
            common = session.run("""
                MATCH (a {name: $entity1})
                MATCH (b {name: $entity2})
                MATCH (a)-[r1]-(common)-[r2]-(b)
                WHERE type(r1) = type(r2) OR type(r1) = 'RELATED_TO' OR type(r2) = 'RELATED_TO'
                RETURN DISTINCT common.name as name, 
                       labels(common)[0] as type
            """, entity1=entities[0], entity2=entities[1]).data()
            
            # Find shared topics
            shared = session.run("""
                MATCH (t1:Topic)-[:COVERS]-(a {name: $entity1})
                MATCH (t2:Topic)-[:COVERS]-(b {name: $entity2})
                WHERE t1 = t2
                RETURN t1.name as topic
            """, entity1=entities[0], entity2=entities[1]).data()
            
            return {
                "common_neighbors": common,
                "shared_topics": [s["topic"] for s in shared]
            }
    
    async def _generate_comparison(
        self,
        entity_infos: List[EntityInfo],
        common: Dict[str, Any],
        query: str
    ) -> str:
        """Generate comparison with LLM"""
        
        # Build comparison context
        context_parts = [f"Câu hỏi: {query}\n"]
        
        for info in entity_infos:
            context_parts.append(f"""
## {info.name}
- Mô tả: {info.description or "Không có mô tả"}
- Liên quan: {', '.join(info.related_concepts[:5]) if info.related_concepts else "Không có"}
- Chủ đề: {', '.join(info.related_topics[:5]) if info.related_topics else "Không có"}
""")
        
        # Add common ground
        if common.get("shared_topics"):
            context_parts.append(f"\n## Điểm chung")
            context_parts.append(f"Chủ đề chung: {', '.join(common['shared_topics'])}")
        
        if common.get("common_neighbors"):
            context_parts.append(f"Khái niệm chung: {', '.join([n['name'] for n in common['common_neighbors'][:3]])}")
        
        context = "\n".join(context_parts)
        
        # Generate comparison
        prompt = f"""
Dựa trên thông tin sau, tạo bảng so sánh giữa các khái niệm:

{context}

Yêu cầu:
1. Tạo bảng so sánh theo các tiêu chí phù hợp
2. Nêu rõ điểm giống và khác nhau
3. Format markdown table
4. Ngôn ngữ: Tiếng Việt
"""
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content
```

---

## 9. Luong 7: Recommendation

### 9.1 Muc tieu
De xuat learning path dua tren progress hien tai.

### 9.2 Flow Chi Tiet

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LUONG 7: RECOMMENDATION                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  INPUT: "Toi da hoc xong Transformer, nen hoc gi tiep theo?"                         │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1: Identify current concept                                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Parse query: "Transformer" detected as current concept                 │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 2: Find prerequisite chain                                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Neo4j Query:                                                         │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────────────┐    │ │  │
│  │  │  │  MATCH (c:Concept {name: "Transformer"})                       │    │ │  │
│  │  │  │  MATCH (c)-[:RELATED_TO*1..3]-(next:Concept)                   │    │ │  │
│  │  │  │  WHERE NOT (next)-[:RELATED_TO*1..2]->(c)  // Forward only     │    │ │  │
│  │  │  │  RETURN next.name as name, next.description as desc            │    │ │  │
│  │  │  │  ORDER BY ...                                                   │    │ │  │
│  │  │  └─────────────────────────────────────────────────────────────────┘    │ │  │
│  │  │                                                                         │ │  │
│  │  │  Result:                                                               │ │  │
│  │  │  1. Self-Attention (Q-K-V) - 6 mentions                                │ │  │
│  │  │  2. Token & Context Window - 5 mentions                                │ │  │
│  │  │  3. Agent - 5 mentions                                                  │ │  │
│  │  │  4. Workflow - 4 mentions                                             │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 3: Order by learning sequence                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Use lecture order + frequency to rank:                               │ │  │
│  │  │                                                                         │ │  │
│  │  │  1. Self-Attention (thuong xuat hien truoc, nhieu lan)                 │ │  │
│  │  │  2. Token & Context Window (cung xuat hien nhieu)                       │ │  │
│  │  │  3. Agent (ung dung, thuong xuat hien sau)                              │ │  │
│  │  │  4. Workflow (tich hop, xau hien cuoi)                                  │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 4: Enrich with content from VectorDB                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  For each recommended concept:                                         │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────────────┐   │ │  │
│  │  │  │  VectorDB search:                                                 │   │ │  │
│  │  │  │  Query: concept_name + "la gi" + "vi du"                         │   │ │  │
│  │  │  │  Get: brief description, 1 example                               │   │ │  │
│  │  │  └─────────────────────────────────────────────────────────────────┘   │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                                 │
│                                    ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 5: Format as Learning Path                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  LLM Format:                                                            │ │  │
│  │  │  "Dựa trên lộ trình học tập, đây là gợi ý tiếp theo..."              │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  OUTPUT:                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  🎓 LEARNING PATH - Transformer                                         [5] │  │
│  │  ════════════════════════════════════════════════════════════════════════ │  │
│  │                                                                               │  │
│  │  ✅ ĐÃ HOÀN THÀNH: Transformer                                              │  │
│  │                                                                               │  │
│  │  📍 GỢI Ý TIẾP THEO:                                                         │  │
│  │                                                                               │  │
│  │  1️⃣ Self-Attention (Q-K-V)                                    [Ưu tiên cao] │  │
│  │     Nền tảng toán học của Transformer, giúp model "chú ý" vào từ nào       │  │
│  │                                                                               │  │
│  │  2️⃣ Token & Context Window                                           [Cao] │  │
│  │     Hiểu cách LLM xử lý giới hạn văn bản, giới hạn 8K/32K/128K tokens     │  │
│  │                                                                               │  │
│  │  3️⃣ Agent (Ứng dụng)                                               [Trung bình] │  │
│  │     Sử dụng kiến thức đã học vào thực tế, AI có thể reasoning và acting  │  │
│  │                                                                               │  │
│  │  4️⃣ Workflow (Tích hợp)                                           [Thấp] │  │
│  │     Kết hợp nhiều agent thành hệ thống, orchestration patterns           │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Implementation

```python
# scripts/handlers/recommendation.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import openai

@dataclass
class LearningItem:
    name: str
    description: str
    priority: str  # "high", "medium", "low"
    reason: str
    estimated_time: str
    content_preview: str

class RecommendationHandler:
    """Handle learning path recommendations"""
    
    def __init__(self, neo4j_driver, qdrant_client, embedder):
        self.neo4j = neo4j_driver
        self.qdrant = qdrant_client
        self.embedder = embedder
    
    async def recommend(self, query: str, current_topic: Optional[str] = None) -> str:
        """
        Generate learning path recommendation
        
        Args:
            query: User query (may contain current topic)
            current_topic: Explicit current topic (optional)
        """
        
        # Step 1: Determine current topic
        if not current_topic:
            current_topic = await self._extract_current_topic(query)
        
        if not current_topic:
            return "Không xác định được chủ đề hiện tại. Vui lòng nêu rõ bạn đã học gì."
        
        # Step 2: Get recommendations from Neo4j
        recommendations = await self._get_recommendations(current_topic)
        
        # Step 3: Enrich with VectorDB content
        enriched = await self._enrich_recommendations(recommendations)
        
        # Step 4: Format response
        return await self._format_learning_path(current_topic, enriched)
    
    async def _extract_current_topic(self, query: str) -> Optional[str]:
        """Extract current topic from query"""
        
        prompt = f"""
        Trích xuất chủ đề hiện tại mà người dùng đã học từ câu hỏi:
        "{query}"
        
        Ví dụ:
        - "Tôi đã học xong Transformer" → "Transformer"
        - "Học rồi Attention mechanism" → "Attention"
        - "Đã biết về Agent" → "Agent"
        
        Chỉ trả về tên chủ đề, không giải thích.
        Nếu không tìm thấy, trả về empty string.
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.choices[0].message.content.strip()
        return result if result else None
    
    async def _get_recommendations(self, current_topic: str) -> List[Dict[str, Any]]:
        """Get recommended next topics from Neo4j"""
        
        with self.neo4j.session() as session:
            # Strategy 1: Topics that commonly follow current topic
            # (based on co-occurrence in lectures)
            results = session.run("""
                MATCH (current:Topic {name: $name})
                
                // Find lectures introducing current topic
                MATCH (l1:Lecture)-[:INTRODUCES]->(current)
                
                // Find topics in same lectures or later lectures
                MATCH (l2:Lecture)-[:INTRODUCES]->(next_topic:Topic)
                WHERE l2.order >= l1.order AND next_topic <> current
                
                // Score by frequency and recency
                WITH next_topic, count(*) as co_occur,
                     max(l2.order - l1.order) as distance
                
                // Also check RELATED_TO relationships
                OPTIONAL MATCH (current)-[:RELATED_TO {type: 'prerequisite'}]->(prereq:Topic)
                
                RETURN next_topic.name as name,
                       next_topic.description as description,
                       co_occur as frequency,
                       distance
                ORDER BY frequency DESC, distance ASC
                LIMIT 5
            """, name=current_topic).data()
            
            if not results:
                # Fallback: Related topics by graph
                results = session.run("""
                    MATCH (current:Topic {name: $name})
                    MATCH (current)-[:RELATED_TO]->(next:Topic)
                    RETURN next.name as name,
                           next.description as description,
                           1 as frequency,
                           1 as distance
                    ORDER BY next.frequency DESC
                    LIMIT 5
                """, name=current_topic).data()
            
            return results
    
    async def _enrich_recommendations(self, recommendations: List[Dict]) -> List[LearningItem]:
        """Enrich recommendations with VectorDB content"""
        
        enriched = []
        
        for rec in recommendations:
            # Search for content about this topic
            query_vector = await self.embedder.embed(rec["name"])
            
            results = await self.qdrant.search(
                collection_name="transcript_chunks",
                query_vector=query_vector,
                limit=2
            )
            
            # Get first result as preview
            preview = ""
            if results:
                preview = results[0].payload["content"][:200] + "..."
            
            # Determine priority
            if rec["frequency"] >= 5:
                priority = "high"
            elif rec["frequency"] >= 3:
                priority = "medium"
            else:
                priority = "low"
            
            # Estimate time based on frequency
            estimated_time = f"~{20 + rec['frequency'] * 5} phút"
            
            enriched.append(LearningItem(
                name=rec["name"],
                description=rec.get("description", ""),
                priority=priority,
                reason=f"Xuất hiện cùng {rec['frequency']} lần trong các bài giảng liên quan",
                estimated_time=estimated_time,
                content_preview=preview
            ))
        
        return enriched
    
    async def _format_learning_path(
        self,
        current_topic: str,
        recommendations: List[LearningItem]
    ) -> str:
        """Format recommendations as learning path"""
        
        # Build items list
        items_md = []
        for i, item in enumerate(recommendations, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[item.priority]
            
            items_md.append(f"""
### {i}. {item.name} {priority_emoji}

**Độ ưu tiên:** {item.priority.upper()}
**Thời lượng ước tính:** {item.estimated_time}
**Lý do:** {item.reason}

{item.description if item.description else item.content_preview}
""")
        
        items_text = "\n".join(items_md)
        
        prompt = f"""
Tạo learning path từ thông tin sau:

**Chủ đề hiện tại:** {current_topic}
**Đề xuất tiếp theo:**
{items_text}

Yêu cầu:
1. Format markdown đẹp, có emoji
2. Sắp xếp theo độ ưu tiên
3. Thêm lời khuyên ngắn gọn cho mỗi bước
4. Tổng thời lượng ước tính ở cuối
5. Ngôn ngữ: Tiếng Việt, thân thiện
"""
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content
```

---

## 10. Luong 8: Summary

### 10.1 Muc tieu
Tom tat noi dung bai giang/hoc phan.

### 10.2 Implementation

```python
# scripts/handlers/summary.py

from typing import List, Dict, Any, Optional
import openai

class SummaryHandler:
    """Handle summarization requests"""
    
    def __init__(self, qdrant_client, neo4j_driver, embedder):
        self.qdrant = qdrant_client
        self.neo4j = neo4j_driver
        self.embedder = embedder
    
    async def summarize(
        self,
        query: str,
        lecture_id: Optional[str] = None,
        lecture_title: Optional[str] = None
    ) -> str:
        """
        Generate summary for a lecture or topic
        """
        
        # Step 1: Get relevant content
        if lecture_id:
            content = await self._get_lecture_content(lecture_id)
        elif lecture_title:
            content = await self._search_and_aggregate(lecture_title)
        else:
            # Use query to find relevant content
            content = await self._search_and_aggregate(query)
        
        # Step 2: Extract structure from Neo4j
        structure = await self._get_lecture_structure(lecture_title or query)
        
        # Step 3: Generate summary
        return await self._generate_summary(content, structure, query)
    
    async def _get_lecture_content(self, lecture_id: str) -> str:
        """Get all content from a specific lecture"""
        
        results = await self.qdrant.search(
            collection_name="transcript_chunks",
            query_filter={
                "must": [
                    {"key": "lecture_id", "match": {"value": lecture_id}}
                ]
            },
            limit=50
        )
        
        # Sort by turn index
        sorted_results = sorted(results, key=lambda x: x.payload.get("turn_index", 0))
        
        return "\n\n".join([r.payload["content"] for r in sorted_results])
    
    async def _search_and_aggregate(self, query: str) -> str:
        """Search and aggregate related content"""
        
        query_vector = await self.embedder.embed(query)
        
        results = await self.qdrant.search(
            collection_name="transcript_chunks",
            query_vector=query_vector,
            limit=20
        )
        
        return "\n\n".join([
            f"[{r.payload.get('lecture_title', 'Unknown')}]: {r.payload['content']}"
            for r in results
        ])
    
    async def _get_lecture_structure(self, topic: str) -> Dict[str, Any]:
        """Get lecture structure from Neo4j"""
        
        with self.neo4j.session() as session:
            # Get topics and concepts
            structure = session.run("""
                MATCH (l:Lecture)-[:INTRODUCES]->(t:Topic)
                WHERE l.title CONTAINS $keyword OR t.name CONTAINS $keyword
                OPTIONAL MATCH (t)-[:COVERS]->(c:Concept)
                OPTIONAL MATCH (l)-[:HAS_QUESTION]->(q:Question)
                RETURN l.title as lecture,
                       collect(DISTINCT t.name) as topics,
                       collect(DISTINCT c.name) as concepts,
                       collect(DISTINCT q.text) as questions
                LIMIT 5
            """, keyword=topic).data()
            
            return structure[0] if structure else {}
    
    async def _generate_summary(
        self,
        content: str,
        structure: Dict[str, Any],
        query: str
    ) -> str:
        """Generate comprehensive summary with LLM"""
        
        # Build context
        context_parts = []
        
        if structure:
            context_parts.append(f"""
## Cấu trúc bài giảng:
- Chủ đề: {', '.join(structure.get('topics', []))}
- Khái niệm: {', '.join(structure.get('concepts', []))}
- Câu hỏi: {'; '.join(structure.get('questions', []))}
""")
        
        context_parts.append(f"""
## Nội dung chi tiết:
{content[:8000]}  # Limit for token budget
""")
        
        context = "\n".join(context_parts)
        
        prompt = f"""
Tạo bản tóm tắt toàn diện từ nội dung sau:

{context}

Yêu cầu:
1. **Tóm tắt tổng quan** (2-3 câu): Nội dung chính của bài
2. **Các điểm chính** (bullet points): 5-7 điểm quan trọng nhất
3. **Giải thích khái niệm**: Giải thích ngắn gọn các khái niệm quan trọng
4. **Ví dụ** (nếu có): Ví dụ thực tế từ nội dung
5. **Câu hỏi gợi ý**: 2-3 câu hỏi để kiểm tra hiểu bài

Format markdown rõ ràng, dễ đọc.
Ngôn ngữ: Tiếng Việt.
"""
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        
        return response.choices[0].message.content
```

---

## 11. API Endpoints

### 11.1 FastAPI Implementation

```python
# api/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from scripts.intent_router import IntentRouter, IntentType
from scripts.handlers.semantic_search import SemanticSearchHandler
from scripts.handlers.graph_query import GraphQueryHandler
from scripts.handlers.multi_hop import MultiHopHandler
from scripts.handlers.comparison import ComparisonHandler
from scripts.handlers.recommendation import RecommendationHandler
from scripts.handlers.summary import SummaryHandler

app = FastAPI(title="VLearn Hybrid RAG API")

# Initialize handlers
router = IntentRouter()
semantic_handler = SemanticSearchHandler(qdrant_client, embedder)
graph_handler = GraphQueryHandler(neo4j_driver)
multi_hop_handler = MultiHopHandler(qdrant_client, neo4j_driver, embedder)
comparison_handler = ComparisonHandler(neo4j_driver, embedder)
recommend_handler = RecommendationHandler(neo4j_driver, qdrant_client, embedder)
summary_handler = SummaryHandler(qdrant_client, neo4j_driver, embedder)

# Models
class QueryRequest(BaseModel):
    question: str
    lecture_id: Optional[str] = None
    lecture_title: Optional[str] = None
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    intent: str
    sources: List[dict]
    confidence: float

class IngestRequest(BaseModel):
    transcript_path: str
    lecture_title: str

# Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Main query endpoint - routes to appropriate handler based on intent
    """
    
    # Step 1: Detect intent
    intent_result = router.detect(request.question)
    
    # Step 2: Route to handler
    handler_map = {
        IntentType.SEMANTIC_SEARCH: semantic_handler.search,
        IntentType.GRAPH_QUERY: graph_handler.query_concept_relations,
        IntentType.MULTI_HOP: multi_hop_handler.query,
        IntentType.COMPARISON: comparison_handler.compare,
        IntentType.RECOMMEND: recommend_handler.recommend,
        IntentType.SUMMARY: summary_handler.summarize,
    }
    
    handler = handler_map.get(intent_result.intent)
    
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unsupported intent: {intent_result.intent}")
    
    # Step 3: Execute handler
    try:
        if intent_result.intent == IntentType.SEMANTIC_SEARCH:
            results = await handler(request.question, top_k=request.top_k)
            answer = "\n\n".join([r.content for r in results])
            sources = [{"content": r.content, "score": r.score} for r in results]
        elif intent_result.intent == IntentType.GRAPH_QUERY:
            result = await handler(intent_result.entities[0] if intent_result.entities else request.question)
            answer = str(result)
            sources = []
        elif intent_result.intent == IntentType.MULTI_HOP:
            answer = await handler(request.question)
            sources = []
        elif intent_result.intent == IntentType.COMPARISON:
            answer = await handler(request.question)
            sources = []
        elif intent_result.intent == IntentType.RECOMMEND:
            answer = await handler(request.question)
            sources = []
        elif intent_result.intent == IntentType.SUMMARY:
            answer = await handler(
                request.question,
                lecture_id=request.lecture_id,
                lecture_title=request.lecture_title
            )
            sources = []
        else:
            answer = "Xin lỗi, tôi không hiểu câu hỏi của bạn."
            sources = []
        
        return QueryResponse(
            answer=answer,
            intent=intent_result.intent.value,
            sources=sources,
            confidence=intent_result.confidence
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
async def ingest(request: IngestRequest):
    """
    Ingest new transcript into the system
    """
    try:
        pipeline = IngestionPipeline(...)
        result = pipeline.run(request.transcript_path, request.lecture_title)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/topics")
async def get_topics():
    """Get all topics"""
    with neo4j.session() as session:
        results = session.run("MATCH (t:Topic) RETURN t.name as name ORDER BY t.frequency DESC")
        return {"topics": [r["name"] for r in results]}

@app.get("/api/concepts")
async def get_concepts():
    """Get all concepts"""
    with neo4j.session() as session:
        results = session.run("MATCH (c:Concept) RETURN c.name as name ORDER BY c.frequency DESC")
        return {"concepts": [r["name"] for r in results]}

# Run with: uvicorn api.main:app --reload
```

### 11.2 API Documentation

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API ENDPOINTS                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  POST /api/query                                                                    │
│  ════════════════════════════════════════════════════════════════════════════════  │
│  Main query endpoint. Routes to appropriate handler based on intent.               │
│                                                                                      │
│  Request Body:                                                                       │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  {{                                                                        │  │
│  │    "question": "Transformer la gi?",                                         │  │
│  │    "lecture_id": "optional",                                                 │  │
│  │    "lecture_title": "optional",                                               │  │
│  │    "top_k": 5                                                                 │  │
│  │  }}                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  Response:                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  {{                                                                        │  │
│  │    "answer": "Transformer la kien truc core cua LLM...",                    │  │
│  │    "intent": "semantic_search",                                              │  │
│  │    "sources": [{{"content": "...", "score": 0.92}}],                        │  │
│  │    "confidence": 0.95                                                         │  │
│  │  }}                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  POST /api/ingest                                                                   │
│  ════════════════════════════════════════════════════════════════════════════════  │
│  Ingest new transcript into VectorDB and Neo4j.                                    │
│                                                                                      │
│  GET /api/health                                                                     │
│  ════════════════════════════════════════════════════════════════════════════════  │
│  Health check. Returns {"status": "healthy"}.                                      │
│                                                                                      │
│  GET /api/topics                                                                    │
│  ════════════════════════════════════════════════════════════════════════════════  │
│  List all topics. Returns {{"topics": ["Transformer", "Agent", ...]}}             │
│                                                                                      │
│  GET /api/concepts                                                                  │
│  ════════════════════════════════════════════════════════════════════════════════  │
│  List all concepts. Returns {{"concepts": ["Self-Attention", ...]}}               │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Deployment

### 12.1 Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QDRANT_HOST=${QDRANT_HOST}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - NEO4J_URI=${NEO4J_URI}
      - NEO4J_USERNAME=${NEO4J_USERNAME}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
    depends_on:
      - qdrant
      - neo4j
    volumes:
      - ./data:/app/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage

  neo4j:
    image: neo4j:5.12
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  qdrant_storage:
  neo4j_data:
```

### 12.2 Environment Variables

```bash
# .env

# OpenAI
OPENAI_API_KEY=sk-...

# Qdrant
QDRANT_HOST=https://your-qdrant-instance.qdrant.io
QDRANT_API_KEY=your-api-key

# Neo4j
NEO4J_URI=neo4j+s://your-neo4j-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

---

## 13. Summary

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                              FLOW SUMMARY                                             ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  USER QUERY                                                                          ║
║      │                                                                              ║
║      ▼                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────────────┐    ║
║  │  INTENT ROUTER (LLM)                                                          │    ║
║  │  - SEMANTIC_SEARCH: Query don gian, tra cuu dinh nghia                       │    ║
║  │  - GRAPH_QUERY: Tra cuu cau truc, quan he                                    │    ║
║  │  - MULTI_HOP: Tra cuu nhieu buoc, ket hop ca hai                             │    ║
║  │  - COMPARISON: So sanh 2 doi tuong                                           │    ║
║  │  - RECOMMEND: De xuat learning path                                          │    ║
║  │  - SUMMARY: Tom tat noi dung                                                 │    ║
║  └──────────────────────────────────────────────────────────────────────────────┘    ║
║      │                                                                              ║
║      ├─────────────────────────────────────────────────────────────────────────────  ║
║      │                                                                              ║
║      ▼                                                                              ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                     ║
║  │   VECTOR DB     │  │     NEO4J       │  │     LLM         │                     ║
║  │   (Qdrant)      │  │   (Graph)       │  │   (Synthesis)   │                     ║
║  │                 │  │                 │  │                 │                     ║
║  │ - Semantic      │  │ - Traversal     │  │ - Format        │                     ║
║  │   Search        │  │ - Relations     │  │   Response      │                     ║
║  │ - Relevance     │  │ - Paths         │  │ - Explain       │                     ║
║  │   Ranking       │  │ - Common         │  │   Connections   │                     ║
║  │                 │  │   Neighbors      │  │                 │                     ║
║  └─────────────────┘  └─────────────────┘  └─────────────────┘                     ║
║                                                                                      ║
║                                                                                      ║
║  KET QUA: User-friendly answer voi ngu canh tu graph                               ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-30 | Initial document |
