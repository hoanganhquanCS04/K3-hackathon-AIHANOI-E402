"""Analyze HybridGraph vs VectorDatabase use cases for VLearn data"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('NEO4J_URI', 'neo4j+s://6a80f29b.databases.neo4j.io')
username = os.getenv('NEO4J_USERNAME', '6a80f29b')
password = os.getenv('NEO4J_PASSWORD', '')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

driver = GraphDatabase.driver(uri, auth=(username, password))

def extract_text(content):
    if content is None:
        return ""
    if isinstance(content, list):
        return " ".join([str(c) for c in content if c])
    return str(content)

print('=' * 100)
print('       HYBRIDGRAPH vs VECTOR DATABASE - USE CASE ANALYSIS')
print('=' * 100)

with driver.session(database=database) as session:
    # Lay cau truc hien tai
    print("\n[1] PHAN TICH CAU TRUC DU LIEU HIEN TAI")
    print("-" * 60)
    
    stats = session.run("""
        MATCH (l:Lecture) WITH count(l) as lectures
        MATCH (t:Topic) WITH lectures, count(t) as topics
        MATCH (c:Concept) WITH lectures, topics, count(c) as concepts
        MATCH (turn:Turn) WITH lectures, topics, concepts, count(turn) as turns
        MATCH (sp:Speaker) WITH lectures, topics, concepts, turns, count(sp) as speakers
        RETURN lectures, topics, concepts, turns, speakers
    """).single()
    
    print(f"  - So bai giang: {stats['lectures']}")
    print(f"  - So chu de (topics): {stats['topics']}")
    print(f"  - So khai niem (concepts): {stats['concepts']}")
    print(f"  - So cuoc hoi thoai: {stats['turns']}")
    print(f"  - So dien gia: {stats['speakers']}")
    
    # Lay mau noi dung
    print("\n[2] MAU NOI DUNG TRONG HE THONG")
    print("-" * 60)
    
    sample_topics = list(session.run("""
        MATCH (t:Topic) RETURN t.name as topic LIMIT 10
    """))
    
    sample_concepts = list(session.run("""
        MATCH (c:Concept) RETURN c.name as name LIMIT 10
    """))
    
    print("  Topics hien tai:")
    for t in sample_topics:
        print(f"    - {t['topic']}")
    
    print("\n  Concepts hien tai:")
    for c in sample_concepts:
        print(f"    - {c['name']}")
    
    # Tinh toan thong ke
    print("\n[3] THONG KE DE XAC DINH TRUNG LAP")
    print("-" * 60)
    
    # Kiem tra topics co trung nhau
    all_topics = list(session.run("""
        MATCH (l:Lecture)-[:COVERS]->(t:Topic)
        RETURN t.name as topic, count(DISTINCT l) as lecture_count
        ORDER BY lecture_count DESC
    """))
    
    highly_repeated = [t for t in all_topics if t['lecture_count'] >= 4]
    unique_topics = [t for t in all_topics if t['lecture_count'] == 1]
    
    print(f"  - Topics xuat hien >= 4 lan: {len(highly_repeated)} (trung lap)")
    print(f"  - Topics xuat hien chi 1 lan: {len(unique_topics)} (dac thu)")
    
    # Tinh so luong relationships
    rel_stats = session.run("""
        MATCH ()-[r:INTRODUCES]->()
        WITH count(r) as intro_count
        MATCH ()-[r:COVERS]->()
        WITH intro_count, count(r) as cover_count
        MATCH ()-[r:BELONGS_TO]->()
        WITH intro_count, cover_count, count(r) as belongs_count
        RETURN intro_count, cover_count, belongs_count
    """).single()
    
    print(f"  - So quan he INTRODUCES: {rel_stats['intro_count']}")
    print(f"  - So quan he COVERS: {rel_stats['cover_count']}")
    print(f"  - So quan he BELONGS_TO: {rel_stats['belongs_count']}")

driver.close()

# Phan tich use case
print("\n" + "=" * 100)
print("       USE CASE ANALYSIS - HYBRIDGRAPH vs VECTOR DATABASE")
print("=" * 100)

print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              HYBRIDGRAPH USE CASES                                                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  1. TIM KIEM NGUS NHIEN CAU HOI ("RAG thong minh")                                                  │
│     ─────────────────────────────────────────────────────────────────────                              │
│     Input: "lam the nao de xac dinh bai toan phu hop cho AI?"                                       │
│     HybridGraph se:                                                                                 │
│       • Tim cac Topic/Concept lien quan qua vector similarity                                        │
│       • Duyet graph de lay cau hoi cung Transcript/Lecture                                          │
│       • Tra ve cau tra loi co ngu canh                                                                 │
│                                                                                                      │
│  2. HOI DAP CO NGU CANH ("Multi-hop Q&A")                                                          │
│     ─────────────────────────────────────────────────────────────────────                              │
│     Input: "Transformer lien quan gi den Agent nhu the nao?"                                        │
│     HybridGraph se:                                                                                 │
│       • Tim "Transformer" trong graph                                                                │
│       • Duyet qua Agent (neu co relationship)                                                        │
│       • Tra ve noi dung tu nhieu Transcript cung luc                                                 │
│                                                                                                      │
│  3. DE XUAT NOI DUNG THEO CHUOI ("Learning Path")                                                  │
│     ─────────────────────────────────────────────────────────────────────                              │
│     Input: Hoc vien da hoc "Transformer"                                                            │
│     HybridGraph se:                                                                                 │
│       • Tim concept lien quan trong graph                                                            │
│       • Xep thu tu theo tien quyet (prerequisites)                                                 │
│       • De xuat buoc tiep theo                                                                           │
│                                                                                                      │
│  4. PHAT HIEN TRUNG LAP TU DONG ("Duplicate Detection")                                             │
│     ─────────────────────────────────────────────────────────────────────                              │
│     Khi nhap topic moi:                                                                              │
│       • Vector similarity tim topic giong nhau                                                         │
│       • Graph relationship kiem tra co trung hay khong                                                │
│       • Canh bao neu trung lap                                                                          │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            VECTOR DATABASE USE CASES                                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  1. TIM KIEM NGUS NHIEN DON GIAN ("Semantic Search")                                                │
│     ─────────────────────────────────────────────────────────────────────                              │
│     Input: "Transformer la gi?"                                                                      │
│     VectorDB se:                                                                                     │
│       • Tim vector gan nhat voi "Transformer"                                                         │
│       • Tra ve noi dung co embedding tuong tu                                                         │
│       • Nhanh, don gian                                                                               │
│                                                                                                      │
│  2. GOI Y TU DONG ("Auto-completion")                                                               │
│     ─────────────────────────────────────────────────────────────────────                              │
│     Khi hoc vien go:                                                                                 │
│       • Encoding input                                                                                │
│       • Tim embedding gan nhat                                                                        │
│       • De xuat noi dung tiep theo                                                                    │
│                                                                                                      │
│  3. PHAN CUM NOI DUNG ("Content Clustering")                                                        │
│     ─────────────────────────────────────────────────────────────────────                              │
│     VectorDB se:                                                                                     │
│       • Encoding tat ca noi dung                                                                       │
│       • Phan cum theo vector similarity                                                               │
│       • Tim cac nhom noi dung gan nhau                                                                │
│                                                                                                      │
│  4. SAN PHAM "NHANH" vs "CHINH XAC"                                                                │
│     ─────────────────────────────────────────────────────────────────────                              │
│     • Tra cuu nhanh: VectorDB (ms)                                                                    │
│     • Phan tich chi tiet: HybridGraph (s)                                                            │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                         KHI NAO DUNG CAI NAO?                                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  ┌─────────────────┬────────────────────────────────────────────────────────────────┐             │
│  │ Tinh nang       │ Vector Database          │ HybridGraph                        │             │
│  ├─────────────────┼────────────────────────────────────────────────────────────────┤             │
│  │ Toc do          │ RAPID (ms)               │ SLOWER (1-3s)                     │             │
│  │ Tim kiem ngay   │ Khong                    │ Co (theo graph)                   │             │
│  │ Tra cuu ngu canh│ Don gian                 │ Phuc tap                          │             │
│  │ Multi-hop       │ Khong                    │ Co                                │             │
│  │ Relationship    │ Khong                    │ Co                                │             │
│  │ Memory sang     │ Thap                     │ Cao                               │             │
│  └─────────────────┴────────────────────────────────────────────────────────────────┘             │
│                                                                                                      │
│  GIAI PHAP DOI VOI TRUNG LAP:                                                                        │
│  ───────────────────────────────────────────────────────────────────────                              │
│  1. Dung VectorDB de phat hien trung lap (semantic similarity > 0.85)                               │
│  2. Dung HybridGraph de xu ly trung lap (merge hoac tach)                                           │
│  3. Trong he thong cua ban:                                                                          │
│     • VectorDB = "Index nhanh" cho tim kiem                                                          │
│     • Neo4j = "Graph that" cho quan he                                                              │
│     • HybridGraph = KET HOP ca hai                                                                   │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

# Use case cu the cho data VLearn
print("\n" + "=" * 100)
print("       USE CASE CU THE CHO DATA VLEARN")
print("=" * 100)

use_cases = """
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  USE CASE 1: HOC VIEN HOI "CAC BUOC XAC DINH BAI TOAN AI"                                          │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  Câu hỏi: "Mình muốn xác định bài toán AI cho doanh nghiệp, cần làm những bước nào?"             │
│                                                                                                      │
│  VECTOR DATABASE approach:                                                                           │
│  ├── Tìm embedding gần nhất với query                                                               │
│  ├── Trả về: "Double Diamond, First Principle Thinking, Impact-Effort Matrix..."                    │
│  └── Vấn đề: KHÔNG biết thứ tự, KHÔNG biết mối liên hệ                                             │
│                                                                                                      │
│  HYBRIDGRAPH approach:                                                                              │
│  ├── Tìm concept "Problem Discovery" → concept "Double Diamond"                                     │
│  ├── Duyệt graph: Double Diamond → Five Whys → Impact-Effort Matrix                                │
│  ├── Trả về: Chain hoàn chỉnh với thứ tự và giải thích                                            │
│  └── Kết quả: "Bước 1: Problem Discovery → Bước 2: Define (Five Whys)..."                         │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  USE CASE 2: PHAT HIEN TRUNG LAP TOPIC                                                             │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  Hiện tại trong data:                                                                               │
│  ├── "Vì sao 2025-2026 là bước ngoặt" xuất hiện 6 lần                                             │
│  ├── "LLM: encoder–decoder, transformer và attention" xuất hiện 5 lần                              │
│  └── "Transformer — trái tim của LLM" xuất hiện 5 lần                                             │
│                                                                                                      │
│  VECTOR DATABASE:                                                                                   │
│  ├── Encode tất cả topics                                                                           │
│  ├── Tính similarity matrix                                                                         │
│  └── Phát hiện: "Transformer" topic gần với "Encoder-Decoder" topic (>0.9)                       │
│                                                                                                      │
│  HYBRIDGRAPH:                                                                                       │
│  ├── Khi phát hiện trùng lặp                                                                       │
│  ├── Kiểm tra graph: chúng thuộc cùng Lecture không?                                                │
│  ├── Nếu cùng Lecture → MERGE topics                                                                │
│  ├── Nếu khác Lecture → KEEP nhưng LINK together                                                    │
│  └── Cập nhật Neo4j relationship                                                                   │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  USE CASE 3: CHATBOT HỎI ĐÁP THÔNG MINH                                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  Câu hỏi: "Sự khác biệt giữa Automation và Augmentation là gì?"                                    │
│                                                                                                      │
│  RAG đơn thuần (VectorDB):                                                                         │
│  ├── Tìm context gần nhất                                                                           │
│  ├── Trả về: "Automation: using AI without human..."                                               │
│  └── Vấn đề: KHÔNG có giải thích mối quan hệ với các concept khác                                  │
│                                                                                                      │
│  HybridGraph RAG:                                                                                   │
│  ├── Tìm "Automation" và "Augmentation" trong graph                                                │
│  ├── Trích xuất:                                                                                   │
│  │   ├── Automation: Agent có thể tự động hóa tác vụ lặp lại                                       │
│  │   ├── Augmentation: Agent hỗ trợ con người, không thay thế                                     │
│  │   └── Cả hai đều liên quan đến "Workflow" và "Agent"                                           │
│  ├── Tạo câu trả lời với ngữ cảnh graph                                                            │
│  └── Kết quả: "Automation thay thế con người, Augmentation hỗ trợ..."                              │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  USE CASE 4: ĐỀ XUẤT LEARNING PATH CÁ NHÂN                                                         │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  Tình huống: Học viên đã hoàn thành "Transformer" và hỏi "Tiếp theo học gì?"                     │
│                                                                                                      │
│  HybridGraph xử lý:                                                                                │
│  ├── Tìm "Transformer" trong graph                                                                 │
│  ├── Kiểm tra prerequisite relationships                                                           │
│  ├── Tìm concept thường xuất hiện SAU "Transformer" trong cùng Lecture:                            │
│  │   ├── Self-attention (Q-K-V)                                                                    │
│  │   ├── Agent                                                                                     │
│  │   └── Workflow                                                                                   │
│  ├── Sắp xếp theo thứ tự xuất hiện trong khóa học                                                  │
│  └── Đề xuất: "Bạn nên học Self-Attention trước (nền tảng), sau đó học Agent (ứng dụng)"          │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
"""

print(use_cases)

# Giai phap de xuat
print("\n" + "=" * 100)
print("       GIAI PHAP KIEN NGHICH - TRUNG HOP TINH NANG")
print("=" * 100)

print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           KIẾN TRÚC ĐỀ XUẤT                                                        │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│                          ┌─────────────────────┐                                                    │
│                          │   User Query        │                                                    │
│                          └──────────┬──────────┘                                                    │
│                                     │                                                              │
│                          ┌──────────▼──────────┐                                                    │
│                          │   ROUTER            │                                                    │
│                          │   (Intent Detection)│                                                    │
│                          └──────────┬──────────┘                                                    │
│                    ┌───────────────┼───────────────┐                                                │
│                    ▼               ▼               ▼                                                │
│          ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                                        │
│          │ Vector Search│  │  Graph Walk │  │  Hybrid     │                                        │
│          │ (Fast, Simple│  │ (Context,   │  │  (Complex   │                                        │
│          │  Retrieval)  │  │  Reasoning) │  │  Q&A)       │                                        │
│          └─────────────┘  └─────────────┘  └─────────────┘                                        │
│                                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  KHI NÀO TRÙNG LẶP (VÀ CÁCH GIẢI QUYẾT):                                                          │
│                                                                                                      │
│  ╔════════════════════════════════════════════════════════════════════════════════════════════════╗   │
│  ║  Trùng lặp đang xảy ra:                                                                         ║   │
│  ║  - Topic "LLM: encoder–decoder, transformer và attention" xuất hiện 5 lần                     ║   │
│  ║  - Topic "Transformer — trái tim của LLM" xuất hiện 5 lần                                     ║   │
│  ║  ═══════════════════════════════════════════════════════════════════════════════════════════║   │
│  ║  VectorDB chỉ xử lý:                                                                           ║   │
│  ║  → Tìm semantic similarity > 0.85 → Cảnh báo "Có thể trùng lặp"                               ║   │
│  ║                                                                                                  ║   │
│  ║  HybridGraph xử lý:                                                                             ║   │
│  ║  → MERGE nodes nếu cùng context (trong 1 Lecture)                                             ║   │
│  ║  → LINK với relationship "RELATED_TO" nếu khác context (khác Lecture)                          ║   │
│  ╚════════════════════════════════════════════════════════════════════════════════════════════════╝   │
│                                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                      │
│  CÁC BƯỚC THỰC HIỆN:                                                                                │
│                                                                                                      │
│  1. GIAI QUYET TRUNG LAP HIEN TAI:                                                                 │
│     ├── Tạo embedding cho tất cả Topics                                                            │
│     ├── Tính similarity matrix                                                                      │
│     ├── Gợi ý merge cho similarity > 0.85                                                          │
│     └── Hoặc tạo relationship "RELATED_TO" thay vì trùng lặp                                        │
│                                                                                                      │
│  2. THEM HYBRIDGRAPH (mở rộng Neo4j):                                                              │
│     ├── Thêm vector properties cho mỗi node (topic, concept, turn)                                  │
│     ├── Tạo endpoint hybrid search                                                                  │
│     └── Implement multi-hop reasoning                                                                │
│                                                                                                      │
│  3. THEM VECTOR DATABASE (Pinecone/Milvus/Qdrant):                                                │
│     ├── Index tất cả content (turns, topics)                                                        │
│     ├── Sử dụng cho semantic search nhanh                                                           │
│     └── Kết hợp với Neo4j cho retrieval                                                             │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

print("\n" + "=" * 100)
print("       KET LUAN")
print("=" * 100)

print("""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                      │
│  1. TRUNG LAP LA CO - NHƯNG CO LOI:                                                                │
│     • Topic xuất hiện nhiều lần = ĐƯỢC NHẮC LAI = Quan trọng                                       │
│     • Không cần merge tất cả, chỉ cần LINK lại                                                      │
│                                                                                                      │
│  2. HAI CONG NGHE KHAC NHAU:                                                                        │
│     • VectorDB = Tra cuu nhanh (semantic search)                                                   │
│     • HybridGraph = Tra cuu thong minh (reasoning, relationships)                                   │
│                                                                                                      │
│  3. DE XUAT CHO HE THONG CUA BAN:                                                                  │
│     • Giữ Neo4j như Graph Database chính                                                            │
│     • Thêm VectorDB cho semantic search nhanh                                                       │
│     • Dùng HybridGraph approach khi cần multi-hop reasoning                                          │
│     • Sử dụng similarity threshold để phát hiện trùng lặp thay vì merge                            │
│                                                                                                      │
│  4. CODE MINH HOA:                                                                                 │
│     Trong project của bạn, bạn có thể thêm:                                                         │
│     • /embeddings - VectorDB cho semantic search                                                     │
│     • /graph/walk - HybridGraph cho multi-hop                                                        │
│     • /similarity - Phat hien trung lap                                                             │
│                                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")
