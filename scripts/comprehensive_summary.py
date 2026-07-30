"""Comprehensive deep summary with text summaries and concept relationships"""
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

print('=' * 100)
print('                    TOM TAT TOAN DIEN - BAO CAO DAY DU TU NEO4J GRAPH')
print('=' * 100)

with driver.session(database=database) as session:
    # ========== TONG QUAN ==========
    stats = session.run("""
        MATCH (l:Lecture) WITH count(l) as lectures
        MATCH (t:Topic) WITH lectures, count(t) as topics
        MATCH (c:Concept) WITH lectures, topics, count(c) as concepts
        MATCH (r:Reference) WITH lectures, topics, concepts, count(r) as refs
        MATCH (turn:Turn) WITH lectures, topics, concepts, refs, count(turn) as turns
        MATCH (q:Question) WITH lectures, topics, concepts, refs, turns, count(q) as questions
        MATCH (sp:Speaker) WITH lectures, topics, concepts, refs, turns, questions, count(sp) as speakers
        RETURN lectures, topics, concepts, refs, turns, questions, speakers
    """).single()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                              TONG QUAN HE THONG                                             ║
╠══════════════════════════════════════════════════════════════════════════════════════════════╣
║  So bai giang:              {stats['lectures']:<10}                                                          ║
║  So chu de (topics):        {stats['topics']:<10}                                                          ║
║  So concept:                {stats['concepts']:<10}                                                          ║
║  So tai lieu tham chieu:    {stats['refs']:<10}                                                          ║
║  So turn (cuoc hoi thoai):  {stats['turns']:<10}                                                          ║
║  So cau hoi:                {stats['questions']:<10}                                                          ║
║  So dien gia:              {stats['speakers']:<10}                                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
    """)

    # ========== CAU TRUC THOI GIAN & TRINH TU BAI GIANG ==========
    print('\n' + '=' * 100)
    print('                    CAU TRUC THOI GIAN - TRINH TU CAC BAI GIANG')
    print('=' * 100)
    
    lectures_ordered = list(session.run("""
        MATCH (l:Lecture)
        OPTIONAL MATCH (l)<-[:BELONGS_TO]-(turn:Turn)
        OPTIONAL MATCH (l)<-[:BELONGS_TO]-(q:Question)
        RETURN l.id as id, l.title as title, l.day as day,
               count(DISTINCT turn) as turns,
               count(DISTINCT q) as questions
        ORDER BY l.day, l.id
    """))
    
    for i, l in enumerate(lectures_ordered, 1):
        day = l['day'] or 'Khong xac dinh'
        print(f"""
┌─ BAOI GIANG {i}/6 ──────────────────────────────────────────────────────────────────────
│  ID: {l['id']}
│  Thu tu: {i}/6
│  Day: {day}
│  Tieu de: {l['title']}
│  So cuoc hoi thoai (turns): {l['turns']}
│  So cau hoi: {l['questions']}
└─────────────────────────────────────────────────────────────────────────────────────────""")

    # ========== CHI TIET TUNG BAI GIANG VOI TOM TAT VAN BAN ==========
    print('\n\n' + '=' * 100)
    print('                    CHI TIET + TOM TAT VAN BAN TUNG BAI GIANG')
    print('=' * 100)

    for i, lecture in enumerate(lectures_ordered, 1):
        lecture_id = lecture['id']
        print(f"\n{'━' * 100}")
        print(f"  ┃ BAI {i}/6: {lecture['title']}")
        print(f"  ┃ ID: {lecture_id} | Day: {lecture['day'] or 'N/A'}")
        print('━' * 100)
        
        # Topics
        topics = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:COVERS]->(t:Topic)
            RETURN t.name as topic, t.description as description
            ORDER BY topic
        """, id=lecture_id))
        
        print(f"\n  [A. NOI DUNG CHINH - CAC CHU DE]")
        for j, topic in enumerate(topics, 1):
            print(f"     {j}. {topic['topic']}")
            if topic['description']:
                desc = topic['description'][:200] + '...' if len(topic['description']) > 200 else topic['description']
                print(f"        Mo ta: {desc}")
        
        # Concepts
        concepts = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:INTRODUCES]->(c:Concept)
            RETURN c.name as name, c.description as description
            ORDER BY name
        """, id=lecture_id))
        
        if len(concepts) > 0:
            print(f"\n  [B. CONCEPTS - KHÁI NIEM CHINH]")
            for c in concepts:
                print(f"     • {c['name']}")
                if c['description']:
                    desc = c['description'][:150] + '...' if len(c['description']) > 150 else c['description']
                    print(f"       {desc}")
        
        # References
        refs = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:INTRODUCES]->(r:Reference)
            RETURN r.title as title, r.author as author, r.type as type
            ORDER BY title
        """, id=lecture_id))
        
        if len(refs) > 0:
            print(f"\n  [C. TAI LIEU THAM KHAO]")
            for r in refs:
                print(f"     • {r['title']} - {r['author']} ({r['type']})")
        
        # Sample dialogue excerpts for summary
        sample_turns = list(session.run("""
            MATCH (l:Lecture {id: $id})<-[:BELONGS_TO]-(t:Turn)
            WHERE t.content IS NOT NULL AND size(t.content) > 20
            RETURN t.id as turn_id, t.content as content, t.speaker_role as role
            ORDER BY turn_id
            LIMIT 10
        """, id=lecture_id))
        
        if len(sample_turns) > 0:
            print(f"\n  [D. VI DU NOI DUNG THAO Luan]")
            for j, t in enumerate(sample_turns[:3], 1):
                role_name = {'instructor': 'Giang vien', 'student': 'Hoc vien'}
                content = t['content'][0] if t['content'] else ''
                print(f"\n     {j}. [{role_name.get(t['role'], t['role'])} - {t['turn_id']}]:")
                print(f"        {content[:300]}..." if len(content) > 300 else f"        {content}")

    # ========== MOI QUAN HE GIUA CAC CONCEPTS ==========
    print('\n\n' + '=' * 100)
    print('                    MOI QUAN HE GIUA CAC CONCEPTS')
    print('=' * 100)
    
    # Get all concepts with their relationships through shared lectures
    concept_relations = list(session.run("""
        MATCH (c1:Concept)<-[:INTRODUCES]-(l:Lecture)-[:INTRODUCES]->(c2:Concept)
        WHERE id(c1) < id(c2)
        WITH c1, c2, collect(l.title) as shared_lectures
        RETURN c1.name as concept1, c2.name as concept2, shared_lectures
        ORDER BY size(shared_lectures) DESC
    """))
    
    print("""
    Cac concepts thuong duoc hoc cung nhau trong cung bai giang:
    """)
    
    for rel in concept_relations:
        lectures_str = ", ".join(rel['shared_lectures']) if rel['shared_lectures'] else "Khong co"
        print(f"""
┌─ MOI QUAN HE ─────────────────────────────────────────────────────────────────────────
│  {rel['concept1']}  ⟷  {rel['concept2']}
│  Cung xuat hien trong: {lectures_str}
└────────────────────────────────────────────────────────────────────────────────────────""")

    # Concept network summary
    print("\n\n  [BANG TOM TAT MOI QUAN HE CONCEPTS]")
    print("  " + "-" * 90)
    
    concept_counts = list(session.run("""
        MATCH (c:Concept)<-[:INTRODUCES]-(l:Lecture)
        WITH c, collect(l.title) as lectures, count(l) as freq
        RETURN c.name as concept, freq, lectures
        ORDER BY freq DESC
    """))
    
    for c in concept_counts:
        lectures_str = ", ".join(c['lectures'])[:60]
        print(f"  {c['concept']:<25} | Tan suat: {c['freq']} | Bai: {lectures_str}...")

    # ========== TOM TAT THEO CHU DE LON ==========
    print('\n\n' + '=' * 100)
    print('                    TOM TAT NOI DUNG THEO CHU DE LON (TOPIC CLUSTERS)')
    print('=' * 100)
    
    # Group topics by keyword similarity
    topic_groups = list(session.run("""
        MATCH (l:Lecture)-[:COVERS]->(t:Topic)
        WITH t.name as topic, collect(l.title) as lectures
        RETURN topic, lectures, size(lectures) as freq
        ORDER BY freq DESC, topic
        LIMIT 30
    """))
    
    for t in topic_groups:
        lectures_str = ", ".join(set([l.split('—')[0].strip() for l in t['lectures'] if l]))[:70]
        print(f"""
  [{t['freq']} lan] {t['topic']}
           Bai hoc: {lectures_str}...""")

    # ========== CAC TU KHOA QUAN TRONG ==========
    print('\n\n' + '=' * 100)
    print('                    CAC TU KHOA & CONCEPT QUAN TRONG NHAT')
    print('=' * 100)
    
    # Get all unique concepts ordered by frequency
    important_concepts = list(session.run("""
        MATCH (c:Concept)<-[:INTRODUCES]-(l:Lecture)
        WITH c, count(l) as lecture_count
        RETURN c.name as concept, c.description as description, lecture_count
        ORDER BY lecture_count DESC
    """))
    
    print("""
    Danh sach concepts theo muc do quan trong (tan suat xuat hien trong cac bai):
    """)
    
    for i, c in enumerate(important_concepts, 1):
        stars = "★" * min(c['lecture_count'], 5)
        desc = c['description'][:80] + '...' if c['description'] and len(c['description']) > 80 else (c['description'] or '')
        print(f"  {i}. {c['concept']:<30} {stars:<5} ({c['lecture_count']} bai)")
        if desc:
            print(f"     Mo ta: {desc}")

    # ========== CAC TAI LIEU THAM CHIEU ==========
    print('\n\n' + '=' * 100)
    print('                    TAI LIEU THAM CHIEU - DOC THEM')
    print('=' * 100)
    
    all_refs = list(session.run("""
        MATCH (r:Reference)
        OPTIONAL MATCH (r)<-[:INTRODUCES]-(l:Lecture)
        RETURN r.title as title, r.author as author, r.type as type,
               collect(l.title) as used_in
        ORDER BY title
    """))
    
    for r in all_refs:
        used = ", ".join([u for u in r['used_in'] if u]) if r['used_in'] else "Chua su dung"
        print(f"""
┌─ TAI LIEU ───────────────────────────────────────────────────────────────────────────
│  Tieu de: {r['title']}
│  Tac gia: {r['author']}
│  Loai: {r['type']}
│  Duoc su dung trong: {used}
└────────────────────────────────────────────────────────────────────────────────────────""")

    # ========== CAC CAU HOI NOI BAT ==========
    print('\n\n' + '=' * 100)
    print('                    CAC CAU HOI NOI BAT CUA HOC VIEN')
    print('=' * 100)
    
    all_questions = list(session.run("""
        MATCH (l:Lecture)<-[:BELONGS_TO]-(t:Turn)<-[:SPEAKS]-(sp:Speaker)
        WHERE t.speaker_role = 'student' AND t.is_question = true AND t.content IS NOT NULL
        RETURN t.id as turn_id, t.content as content, l.title as lecture
        ORDER BY turn_id
        LIMIT 10
    """))
    
    for i, q in enumerate(all_questions, 1):
        content = q['content'][0] if q['content'] else ''
        print(f"""
  {i}. [{q['turn_id']}] - {q['lecture']}
     Cau hoi: {content[:250]}...""")

    # ========== BIEU DO QUAN HE ==========
    print('\n\n' + '=' * 100)
    print('                    BIEU DO MOI QUAN HE KIEN THUC')
    print('=' * 100)
    
    print("""
    HUONG DAN DOC BIEU DO:
    • Cac concept duoc bieu dien boi [CONCEPT]
    • Cac moi quan he duoc bieu dien boi -->
    • So bai xuat hien duoc hien thi boi ★
    
    """)
    
    # Create a simple text-based graph
    for c in important_concepts[:8]:
        stars = "★" * min(c['lecture_count'], 5)
        print(f"    [{c['concept']}] {stars}")
        
        # Find related concepts
        related = [r for r in concept_relations if r['concept1'] == c['concept'] or r['concept2'] == c['concept']]
        if related:
            for rel in related[:2]:
                other = rel['concept2'] if rel['concept1'] == c['concept'] else rel['concept1']
                print(f"        |--> {other}")
        print()

driver.close()
print('\n' + '=' * 100)
print('                         KET THUC BAO CAO TOAN DIEN')
print('=' * 100)
