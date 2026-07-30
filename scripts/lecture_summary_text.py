"""Comprehensive deep summary with TEXT SUMMARIES of each lecture"""
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
    """Extract text from content which could be a list or string"""
    if content is None:
        return ""
    if isinstance(content, list):
        return " ".join([str(c) for c in content if c])
    return str(content)

print('=' * 120)
print('                              TOM TAT BAI GIANG - TOM TAT VAN BAN CHI TIET')
print('=' * 120)

with driver.session(database=database) as session:
    # ========== LAY CHI TIET TUNG BAI GIANG VOI TOM TAT ==========
    lectures = list(session.run("""
        MATCH (l:Lecture)
        RETURN l.id as id, l.title as title, l.day as day
        ORDER BY l.day, l.id
    """))
    
    print(f"""
╔════════════════════════════════════════════════════════════════════════════════════════════════╗
║                              TONG QUAN                                                      ║
║  Khoa hoc co {len(lectures)} bai giang                                                              ║
╚════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    for i, lecture in enumerate(lectures, 1):
        lecture_id = lecture['id']
        title = lecture['title']
        day = lecture['day'] or 'Khong xac dinh ngay'
        
        print(f"\n{'=' * 120}")
        print(f"  BAI {i}/{len(lectures)}: {title}")
        print(f"  ID: {lecture_id} | Ngay: {day}")
        print('=' * 120)
        
        # ========== TOM TAT VAN BAN (LAY TU NOI DUNG TURN) ==========
        turns_content = list(session.run("""
            MATCH (l:Lecture {id: $id})<-[:BELONGS_TO]-(t:Turn)
            WHERE t.content IS NOT NULL AND size(t.content) > 10
            RETURN t.content as content, t.speaker_role as role, t.id as turn_id
            ORDER BY t.id
            LIMIT 100
        """, id=lecture_id))
        
        # Tinh toan so luong
        instructor_turns = [t for t in turns_content if t['role'] == 'instructor' and extract_text(t['content']).strip()]
        student_turns = [t for t in turns_content if t['role'] == 'student' and extract_text(t['content']).strip()]
        all_content = [extract_text(t['content']) for t in turns_content]
        
        print(f"\n  [TOM TAT TONG QUAN]")
        print(f"  - So cuoc hoi thoai: {len(turns_content)}")
        print(f"  - So lan giao vien noi: {len(instructor_turns)}")
        print(f"  - So lan hoc vien noi: {len(student_turns)}")
        
        # ========== CAC CHU DE CHINH ==========
        topics = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:COVERS]->(t:Topic)
            RETURN t.name as topic, t.description as description
            ORDER BY topic
        """, id=lecture_id))
        
        print(f"\n  [A. CAC CHU DE CHINH DA DAY ({len(topics)} chu de)]")
        for j, topic in enumerate(topics, 1):
            print(f"     {j}. {topic['topic']}")
            if topic['description']:
                desc = extract_text(topic['description'])
                if len(desc) > 5:
                    print(f"        {desc[:200]}{'...' if len(desc) > 200 else ''}")
        
        # ========== CAC CONCEPTS ==========
        concepts = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:INTRODUCES]->(c:Concept)
            RETURN c.name as name, c.description as description
            ORDER BY name
        """, id=lecture_id))
        
        if len(concepts) > 0:
            print(f"\n  [B. CAC KHAI NIEM (CONCEPTS) DA GIOI THIEU]")
            for c in concepts:
                desc = extract_text(c['description']) if c['description'] else ""
                print(f"     * {c['name']}")
                if desc:
                    print(f"       {desc[:150]}{'...' if len(desc) > 150 else ''}")
        
        # ========== TAI LIEU THAM KHAO ==========
        refs = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:INTRODUCES]->(r:Reference)
            RETURN r.title as title, r.author as author, r.type as type
        """, id=lecture_id))
        
        if len(refs) > 0:
            print(f"\n  [C. TAI LIEU THAM KHAO]")
            for r in refs:
                print(f"     * {r['title']} - {r['author']} ({r['type']})")
        
        # ========== VI DU NOI DUNG THUC SU ==========
        print(f"\n  [D. VI DU NOI DUNG THAO LUAN (TRICH DAy)]")
        
        # Lay noi dung thuc su
        sample_turns = [t for t in turns_content if extract_text(t['content']).strip() and len(extract_text(t['content'])) > 30]
        
        if sample_turns:
            # Hien thi 5 vi du noi dung
            shown = 0
            for t in sample_turns[:20]:  # Kiem tra nhieu hon
                content = extract_text(t['content'])
                if len(content) > 50 and shown < 5:
                    role = "Giang vien" if t['role'] == 'instructor' else "Hoc vien"
                    print(f"\n     [{role}] {t['turn_id']}:")
                    # Hien thi 2-3 cau dau tien
                    sentences = content.split('.')
                    preview = '. '.join(sentences[:3])
                    if len(preview) > 500:
                        preview = preview[:500] + "..."
                    print(f"        {preview}")
                    shown += 1
        
        # ========== CAC CAU HOI CUA HOC VIEN ==========
        questions = [t for t in turns_content if t['role'] == 'student' and ('?' in extract_text(t['content']) or 'hỏi' in extract_text(t['content']).lower() or '?' in extract_text(t['content']))]
        
        if questions:
            print(f"\n  [E. CAC CAU HOI CUA HOC VIEN ({len(questions)} cau)]")
            for q in questions[:5]:
                content = extract_text(q['content'])
                if len(content) > 20:
                    print(f"\n     * {q['turn_id']}: {content[:200]}{'...' if len(content) > 200 else ''}")

driver.close()

print('\n' + '=' * 120)
print('                         KET THUC TOM TAT BAI GIANG')
print('=' * 120)
