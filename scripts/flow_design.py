"""Design the optimal flow for VLearn system combining HybridGraph + VectorDB"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              LUONG HE THONG DE XUAT - VLEARN                                                ║
║                         HybridGraph + VectorDB Integration Flow                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")

# Phase 1: Data Ingestion
print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LUONG 1: DATA INGESTION (Khi them transcript moi)                                                          │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  INPUT: transcript-0X-clean.md (file transcript moi)                                                    │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                               │
│                                              ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1.1: CHIA NAN (Chunking)                                                                      │  │
│  │  ├── Tach transcript thanh cac Turn (cuoc hoi thoai)                                                 │  │
│  │  ├── Moi Turn co: speaker_role, content, timestamp                                                     │  │
│  │  └── Output: List[Turn]                                                                              │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                               │
│                                              ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 1.2: TRICH XUAT (Extraction)                                                                  │  │
│  │  ├── Dung LLM de trich xuat:                                                                        │  │
│  │  │   ├── Topics (chu de chinh)                                                                       │  │
│  │  │   ├── Concepts (khai niem)                                                                       │  │
│  │  │   ├── Questions (cau hoi)                                                                        │  │
│  │  │   └── References (tai lieu tham khao)                                                            │  │
│  │  └── Output: Structured metadata                                                                     │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                               │
│                         ┌────────────────────┼────────────────────┐                                        │
│                         ▼                    ▼                    ▼                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐                    │
│  │  STEP 1.3a: NEO4J       │  │  STEP 1.3b: VECTOR DB  │  │  STEP 1.3c: SIMILARITY │                    │
│  │  (Graph Database)       │  │  (Semantic Index)       │  │  CHECK                 │                    │
│  │                         │  │                        │  │                        │                    │
│  │  Tao nodes & edges:     │  │  Tao embedding cho:    │  │  Neu similarity > 0.85: │                    │
│  │  ├── Lecture node       │  │  ├── Turn.content      │  │  ├── LINK topics       │                    │
│  │  ├── Topic nodes        │  │  ├── Topic.name        │  │  └── RELATED_TO edge   │                    │
│  │  ├── Concept nodes      │  │  └── Concept.desc      │  │                        │                    │
│  │  ├── Question nodes     │  │                        │  │  Neu similarity < 0.85:│                    │
│  │  └── Relationships:     │  │  Index voi:           │  │  └── Tao node moi      │                    │
│  │      COVERS,            │  │  ├── topic_id          │  │                        │                    │
│  │      INTRODUCES,        │  │  ├── lecture_id        │  │                        │                    │
│  │      BELONGS_TO         │  │  └── metadata          │  │                        │                    │
│  └─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘                    │
│                                              │                                                               │
│                                              ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  OUTPUT: He thong dong bo                                                                             │  │
│  │  ├── Neo4j: Graph relationships                                                                       │  │
│  │  └── VectorDB: Semantic index                                                                         │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

# Phase 2: Query Flow
print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LUONG 2: USER QUERY (Khi hoc vien hoi cau hoi)                                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  INPUT: "Lam the nao de xac dinh bai toan AI cho doanh nghiep?"                                       │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                               │
│                                              ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 2.1: INTENT DETECTION (Router)                                                                  │  │
│  │                                                                                                      │  │
│  │  LLM phan tich cau hoi de xac dinh intent:                                                          │  │
│  │                                                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐                      │  │
│  │  │  INTENT TYPES:                                                            │                      │  │
│  │  │                                                                              │                      │  │
│  │  │  1. SEMANTIC_SEARCH (don gian)                                           │                      │  │
│  │  │     "Transformer la gi?"                                                │                      │  │
│  │  │     → Chi can VectorDB                                                   │                      │  │
│  │  │                                                                              │                      │  │
│  │  │  2. GRAPH_QUERY (co quan he)                                            │                      │  │
│  │  │     "Concept nao lien quan den Agent?"                                   │                      │  │
│  │  │     → Can Neo4j graph traversal                                          │                      │  │
│  │  │                                                                              │                      │  │
│  │  │  3. MULTI_HOP (nhieu buoc)                                              │                      │  │
│  │  │     "Transformer → Agent → Workflow lien quan nhu the nao?"             │                      │  │
│  │  │     → Can Hybrid (Vector + Graph)                                        │                      │  │
│  │  │                                                                              │                      │  │
│  │  │  4. COMPARISON (so sanh)                                                │                      │  │
│  │  │     "Khac nhau giua Automation va Augmentation?"                         │                      │  │
│  │  │     → Can Graph + Synthesis                                             │                      │  │
│  │  │                                                                              │                      │  │
│  │  │  5. RECOMMENDATION (de xuat)                                            │                      │  │
│  │  │     "Toi nen hoc gi tiep theo?"                                          │                      │  │
│  │  │     → Can Learning Path (Graph)                                          │                      │  │
│  │  │                                                                              │                      │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘                      │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                               │
│                         ┌────────────────────┼────────────────────┐                                        │
│                         ▼                    ▼                    ▼                                         │
│                        / SEMANTIC   \\ GRAPH     / MULTI    \\ RECOMMEND              │
│                       /   SEARCH    \\ QUERY    /   HOP     \\    ATION               │
│                      ▼               ▼          ▼            ▼                       │
│           ┌─────────────┐   ┌─────────────┐  ┌─────────────┐ ┌─────────────┐           │
│           │  VectorDB  │   │   Neo4j    │  │  HYBRID    │ │  Learning   │           │
│           │   ONLY     │   │   ONLY     │  │   BOTH     │ │    Path     │           │
│           │            │   │            │  │            │ │  (Graph)    │           │
│           └─────────────┘   └─────────────┘  └─────────────┘ └─────────────┘           │
│                                              │                                                               │
│                                              ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  STEP 2.2: RESPONSE GENERATION                                                                       │  │
│  │  ├── Dong goi ket qua voi ngon ngu tu nhien                                                            │  │
│  │  ├── Kem ngu canh tu graph (neu co)                                                                   │  │
│  │  └── Tra ve cho hoc vien                                                                               │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

# Phase 3: Specific Flows
print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LUONG 3: CHI TIET THEO TUNG INTENT                                                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│  INTENT 1: SEMANTIC_SEARCH (Don gian - Chi can VectorDB)                                                  │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│                                                                                                              │
│  Cau hoi: "Transformer la gi?"                                                                             │
│                                                                                                              │
│  Flow:                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │ 1. Encode query → embedding vector                                          │                          │
│  │ 2. VectorDB.search(query_embedding, k=5)                                   │                          │
│  │ 3. Return noi dung gan nhat                                                 │                          │
│  │ 4. Format: "Transformer la kien truc core cua LLM, giup model hieu..."    │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
│  TOC DO: ~20-50ms                                                                                          │
│  CHI PHI: Thap                                                                                             │
│                                                                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│  INTENT 2: GRAPH_QUERY (Co quan he - Chi can Neo4j)                                                        │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│                                                                                                              │
│  Cau hoi: "Nhung concept nao duoc gioi thieu trong bai giang Transformer?"                                  │
│                                                                                                              │
│  Flow:                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │ 1. Tim Lecture co title chua "Transformer"                                    │                          │
│  │ 2. MATCH (l:Lecture {title: "..."})-[:INTRODUCES]->(c:Concept)              │                          │
│  │ 3. Tra ve danh sach concepts + descriptions                                 │                          │
│  │ 4. Format: "Buoi hoc gioi thieu: Agent, Workflow, Rule-based..."            │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
│  TOC DO: ~100-300ms                                                                                        │
│  CHI PHI: Trung binh                                                                                       │
│                                                                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│  INTENT 3: MULTI_HOP (Phuc tap - Can Hybrid)                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│                                                                                                              │
│  Cau hoi: "Transformer lien quan gi den Agent nhu the nao?"                                                │
│                                                                                                              │
│  Flow:                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │ 1. VectorDB: Tim "Transformer" & "Agent" embeddings                          │                          │
│  │ 2. Neo4j: Duyet graph                                                        │                          │
│  │    │                                                                          │                          │
│  │    ├── (Transformer) ←INTRODUCES← (Lecture)                                 │                          │
│  │    │                                                                          │                          │
│  │    └── (Agent) ←INTRODUCES← (Lecture) [SAME LECTURE!]                         │                          │
│  │                                                                              │                          │
│  │ 3. Lay noi dung tu Lecture do                                               │                          │
│  │ 4. Synthesis: "Transformer la nen tang, Agent la ung dung..."               │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
│  TOC DO: ~500ms-1s                                                                                         │
│  CHI PHI: Cao hon                                                                                          │
│                                                                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│  INTENT 4: COMPARISON (So sanh - Can Graph + Synthesis)                                                    │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│                                                                                                              │
│  Cau hoi: "Su khac nhau giua Automation va Augmentation?"                                                 │
│                                                                                                              │
│  Flow:                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │ 1. Neo4j: MATCH (Automation), MATCH (Augmentation)                          │                          │
│  │ 2. Lay descriptions, examples, related concepts                             │                          │
│  │ 3. Tim common neighbors (ca hai cung lien quan den gi?)                      │                          │
│  │ 4. Synthesis:                                                                 │                          │
│  │    ┌─────────────────────────────────────────────────────────────────┐      │                          │
│  │    │  Automation:                                                      │      │                          │
│  │    │  - AI tu dong lam thay vi con nguoi                              │      │                          │
│  │    │  - Phu hop: tac vu lap lai, quy trinh co dinh                    │      │                          │
│  │    │                                                                  │      │                          │
│  │    │  Augmentation:                                                    │      │                          │
│  │    │  - AI ho tro con nguoi, khong thay the                           │      │                          │
│  │    │  - Phu hop: quyet dinh phuc tap, sang tao                        │      │                          │
│  │    │                                                                  │      │                          │
│  │    │  COMMON: Ca hai deu su dung Agent, deu lien quan den Workflow     │      │                          │
│  │    └─────────────────────────────────────────────────────────────────┘      │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│  INTENT 5: RECOMMENDATION (De xuat - Learning Path)                                                      │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│                                                                                                              │
│  Cau hoi: "Toi da hoc xong Transformer, nen hoc gi tiep?"                                                 │
│                                                                                                              │
│  Flow:                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │ 1. Tim concept "Transformer" trong graph                                     │                          │
│  │ 2. Tim cac concept thuong xuat hien SAU "Transformer" trong cung Lecture:   │                          │
│  │    ├── Self-attention (Q-K-V)                                               │                          │
│  │    ├── Token & context window                                              │                          │
│  │    └── Agent                                                               │                          │
│  │ 3. Sap xep theo thu tu xuat hien trong khoa hoc                            │                          │
│  │ 4. De xuat:                                                                 │                          │
│  │    ┌─────────────────────────────────────────────────────────────────┐      │                          │
│  │    │  Ban nen hoc tiep:                                                 │      │                          │
│  │    │  1. Self-Attention (nen tang cua Transformer)                     │      │                          │
│  │    │  2. Token & Context Window (cach LLM xu ly van ban)                │      │                          │
│  │    │  3. Agent (ung dung cua cac khai niem tren)                        │      │                          │
│  │    └─────────────────────────────────────────────────────────────────┘      │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

# Phase 4: Duplicate Detection Flow
print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  LUONG 4: PHAT HIEN & XU LY TRUNG LAP                                                               │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│  TRUONG HOP: Topic/Concept bi trung lap                                                            │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════  │
│                                                                                                              │
│  Ví dụ data hien tai:                                                                                    │
│  ├── "LLM: encoder-decoder, transformer va attention" (5 lan)                                           │
│  └── "Transformer - trai tim cua LLM" (5 lan)                                                          │
│                                                                                                              │
│  Luong xu ly:                                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │                                                                              │                          │
│  │    ┌───────────────────────────────────────────────────────────────────┐      │                          │
│  │    │  STEP A: SIMILARITY CHECK                                        │      │                          │
│  │    │                                                                   │      │                          │
│  │    │  Khi nhap topic moi:                                             │      │                          │
│  │    │  1. Encode topic moi → embedding                                 │      │                          │
│  │    │  2. VectorDB.similarity_search(topic_embedding, threshold=0.85)   │      │                          │
│  │    │  3. Neu tim thay similar topics:                                 │      │                          │
│  │    │     └── Chuyen sang STEP B                                         │      │                          │
│  │    │  4. Neu khong tim thay:                                           │      │                          │
│  │    │     └── Tao node moi binh thuong                                  │      │                          │
│  │    └───────────────────────────────────────────────────────────────────┘      │                          │
│  │                                    │                                                   │                          │
│  │                                    ▼                                                   │                          │
│  │    ┌───────────────────────────────────────────────────────────────────┐      │                          │
│  │    │  STEP B: CONTEXT ANALYSIS                                         │      │                          │
│  │    │                                                                   │      │                          │
│  │    │  Phan tich xem chung co cung context khong:                       │      │                          │
│  │    │                                                                   │      │                          │
│  │    │  Case 1: Cung Lecture                                             │      │                          │
│  │    │    → Merge thanh 1 topic (chi giu 1 node)                         │      │                          │
│  │    │    → Giu tat ca edges cu                                                               │                          │
│  │    │                                                                   │      │                          │
│  │    │  Case 2: Khac Lecture                                            │      │                          │
│  │    │    → KHONG merge                                                 │                          │                          │
│  │    │    → Tao relationship RELATED_TO giua 2 topics                   │                          │
│  │    │                                                                   │      │                          │
│  │    │  Case 3: Rat giong nhau nhung khac context                       │      │                          │
│  │    │    → Tao relationship "SIMILAR_TO"                              │                          │
│  │    │    → Co the tham chieu chross-lecture                           │                          │
│  │    └───────────────────────────────────────────────────────────────────┘      │                          │
│  │                                                                              │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
│  Ket qua mong muon:                                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐                          │
│  │                                                                              │                          │
│  │  (Topic: "Transformer")                                                               │                          │
│  │       │                                                                          │                          │
│  │       ├─── RELATED_TO ─── (Topic: "Encoder-Decoder")                             │                          │
│  │       │                                                                          │                          │
│  │       └─── INTRODUCED_IN ─── (Lecture 1, Lecture 2, ...)                         │                          │
│  │                                                                              │                          │
│  │  Thay vi: Topic trung lap 5 lan                                                  │                          │
│  │  Chi con: 1 Topic + nhieu relationship voi cac Lecture                          │                          │
│  │                                                                              │                          │
│  └──────────────────────────────────────────────────────────────────────────────┘                          │
│                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

# Summary
print("""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              TOM TAT LUONG HE THONG                                                         ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐  ║
║  │  DATA INGESTION:                                                                                      │  ║
║  │  transcript.md → Chunking → LLM Extraction → Neo4j + VectorDB + Similarity Check                         │  ║
║  └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘  ║
║                                              │                                                               ║
║                                              ▼                                                               ║
║  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐  ║
║  │  USER QUERY:                                                                                         │  ║
║  │  Question → Intent Detection (LLM) → Route to appropriate handler                                     │  ║
║  └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘  ║
║                                              │                                                               ║
║          ┌───────────────────────────────────┼───────────────────────────────────┐                          ║
║          │                                   │                                   │                          ║
║          ▼                                   ▼                                   ▼                          ║
║  ┌───────────────┐                   ┌───────────────┐                   ┌───────────────┐               ║
║  │ SEMANTIC      │                   │ GRAPH         │                   │ MULTI-HOP     │               ║
║  │ SEARCH        │                   │ QUERY         │                   │ /COMPARISON   │               ║
║  │ (VectorDB)    │                   │ (Neo4j)       │                   │ (Hybrid)      │               ║
║  │               │                   │               │                   │               │               ║
║  │ ~50ms         │                   │ ~300ms        │                   │ ~1s           │               ║
║  │ Chi phi thap  │                   │ Chi phi TB    │                   │ Chi phi cao   │               ║
║  └───────────────┘                   └───────────────┘                   └───────────────┘               ║
║                                                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                              ║
║  TRI TUE:                                                                                                  ║
║  ───────────────────────────────────────────────────────────────────────────────────────────────────────────  ║
║  • VectorDB = Tra cuu nhanh (semantic search, < 50ms)                                                      ║
║  • Neo4j = Tra cuu thong minh (relationships, reasoning)                                                    ║
║  • Hybrid = Ket hop ca hai khi can multi-hop hoac complex reasoning                                        ║
║  • Trung lap = LINK (RELATED_TO) thay vi MERGE                                                            ║
║                                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")

# Next steps
print("""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              CAC BUOC TIEP THEO                                                            ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                              ║
║  1. THUC HIEN similarity check cho data hien tai:                                                         ║
║     python scripts/check_duplicate_topics.py                                                                ║
║                                                                                                              ║
║  2. TAO API endpoint moi:                                                                                  ║
║     - /api/query/ route (Intent detection + handlers)                                                      ║
║     - /api/ingest/ route (Data ingestion)                                                                   ║
║                                                                                                              ║
║  3. THEM VECTOR DB (neu chua co):                                                                          ║
║     - Qdrant (local, free)                                                                                 ║
║     - Pinecone (cloud)                                                                                     ║
║     - Milvus (self-hosted)                                                                                  ║
║                                                                                                              ║
║  4. IMPLEMENT Intent Detection:                                                                             ║
║     - LLM-based classifier                                                                                ║
║     - Tra ve 1 trong 5 intent types                                                                        ║
║                                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")
