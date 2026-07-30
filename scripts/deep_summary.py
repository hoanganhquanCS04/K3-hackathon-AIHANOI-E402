"""Deep summary queries with rich details"""
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

print('=' * 80)
print('                    TOM TAT CHI TIET BAI GIANG - NEO4J GRAPH')
print('=' * 80)

with driver.session(database=database) as session:
    # Get total stats
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
    ================================================
    |           TONG QUAN HE THONG                  |
    ================================================
    | So bai giang:        | {stats['lectures']:>20} |
    | So chu de (topics):  | {stats['topics']:>20} |
    | So concept:          | {stats['concepts']:>20} |
    | So tai lieu tham chieu: | {stats['refs']:>17} |
    | So turn (cuoc hoi thoai): | {stats['turns']:>14} |
    | So cau hoi:          | {stats['questions']:>20} |
    | So dien gia:         | {stats['speakers']:>20} |
    ================================================
    """)

    print('\n' + '=' * 80)
    print('                    CHI TIET TUNG BAI GIANG')
    print('=' * 80)

    lectures = list(session.run("""
        MATCH (l:Lecture)
        RETURN l.id as id, l.title as title, l.day as day
        ORDER BY l.day, l.title
    """))
    
    for lecture in lectures:
        print(f"\n{'━' * 80}")
        print(f"  ┃ BAI GIANG: {lecture['title']}")
        print(f"  ┃ ID: {lecture['id']} | Day: {lecture['day'] or 'N/A'}")
        print('━' * 80)
        
        # Topics for this lecture
        topics = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:COVERS]->(t:Topic)
            RETURN t.name as topic, t.description as description
            ORDER BY topic
        """, id=lecture['id']))
        
        print(f"\n  ├─ [TOPICS] ({len(topics)} topics)")
        for i, topic in enumerate(topics, 1):
            print(f"  │  {i}. {topic['topic']}")
            if topic['description']:
                desc = topic['description'][:150] + '...' if len(topic['description']) > 150 else topic['description']
                print(f"  │     Mo ta: {desc}")
        
        # Concepts for this lecture
        concepts = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:INTRODUCES]->(c:Concept)
            RETURN c.name as name, c.description as description
            ORDER BY name
        """, id=lecture['id']))
        
        if len(concepts) > 0:
            print(f"\n  ├─ [CONCEPTS] ({len(concepts)} concepts)")
            for concept in concepts:
                print(f"  │  * {concept['name']}")
                if concept['description']:
                    desc = concept['description'][:120] + '...' if len(concept['description']) > 120 else concept['description']
                    print(f"  │    {desc}")
        
        # References for this lecture
        refs = list(session.run("""
            MATCH (l:Lecture {id: $id})-[:INTRODUCES]->(r:Reference)
            RETURN r.title as title, r.author as author, r.type as type, r.url as url
            ORDER BY title
        """, id=lecture['id']))
        
        if len(refs) > 0:
            print(f"\n  ├─ [REFERENCES] ({len(refs)} references)")
            for ref in refs:
                print(f"  │  - {ref['title']}")
                print(f"  │    Tac gia: {ref['author']} | Loai: {ref['type']}")
                if ref['url']:
                    url = ref['url'][:60] + '...' if len(ref['url']) > 60 else ref['url']
                    print(f"  │    URL: {url}")
        
        # Questions in this lecture
        questions = list(session.run("""
            MATCH (l:Lecture {id: $id})<-[:BELONGS_TO]-(q:Question)
            RETURN q.content as question, q.theme as theme
            ORDER BY question
        """, id=lecture['id']))
        
        if len(questions) > 0:
            print(f"\n  ├─ [QUESTIONS] ({len(questions)} questions)")
            for q in questions:
                print(f"  │  Q: {q['question'][:100]}...")
                if q['theme']:
                    print(f"  │     Chu de: {q['theme']}")
        
        # Speaker activity
        speakers = list(session.run("""
            MATCH (l:Lecture {id: $id})<-[:BELONGS_TO]-(t:Turn)<-[:SPEAKS]-(sp:Speaker)
            RETURN sp.role as role, count(t) as turns, count(DISTINCT sp) as speakers
            ORDER BY role
        """, id=lecture['id']))
        
        print(f"\n  └─ [SPEAKER ACTIVITY]")
        total_turns = 0
        for sp in speakers:
            role_name = {'instructor': 'Giang vien', 'student': 'Hoc vien', 
                        'activity': 'Hoat dong', 'unclear': 'Khong ro'}
            print(f"     {role_name.get(sp['role'], sp['role'])}: {sp['speakers']} nguoi, {sp['turns']} turns")
            total_turns += sp['turns']
        print(f"     Tong so turns: {total_turns}")

    # Deep concept analysis
    print('\n\n' + '=' * 80)
    print('                    PHAN TICH CHI TIET CAC CONCEPT')
    print('=' * 80)
    
    all_concepts = list(session.run("""
        MATCH (c:Concept)
        OPTIONAL MATCH (c)<-[:INTRODUCES]-(l:Lecture)
        RETURN c.name as name, c.description as description,
               collect(l.title) as lectures
        ORDER BY name
    """))
    
    for c in all_concepts:
        print(f"\n{'━' * 80}")
        print(f"  ┃ CONCEPT: {c['name']}")
        print('━' * 80)
        if c['description']:
            print(f"\n  Mo ta day du:")
            # Split description into sentences
            sentences = c['description'].split('. ')
            for sent in sentences:
                if sent.strip():
                    text = sent.strip()
                    if not text.endswith('.'):
                        text += '.'
                    print(f"    {text}")
        lectures_list = [l for l in c['lectures'] if l]
        if lectures_list:
            print(f"\n  Xuat hien trong cac bai giang:")
            for l in lectures_list:
                print(f"    • {l}")
        else:
            print(f"\n  Xuat hien: Khong co")

    # Question themes analysis
    print('\n\n' + '=' * 80)
    print('                    CAC CHU DE CO BON TRONG CAC CAU HOI')
    print('=' * 80)
    
    themes = list(session.run("""
        MATCH (q:Question)
        RETURN q.theme as theme, count(*) as count,
               collect(q.content) as questions
        ORDER BY count DESC
    """))
    
    for t in themes:
        print(f"\n{'━' * 80}")
        print(f"  ┃ CHU DE: {t['theme']} ({t['count']} cau hoi)")
        print('━' * 80)
        for i, q in enumerate(t['questions'][:5], 1):  # Show first 5 questions per theme
            print(f"\n  {i}. {q[:200]}...")

    # Turn flow analysis - instructor to student
    print('\n\n' + '=' * 80)
    print('                    VI DU CUOC HOI THOAI (Giang vien -> Hoc vien)')
    print('=' * 80)
    
    flows = list(session.run("""
        MATCH (t1:Turn)-[:FOLLOWS]->(t2:Turn)
        WHERE t1.speaker_role = 'instructor' AND t2.speaker_role = 'student'
        RETURN t1.id as from_id, t1.content as from_content,
               t2.id as to_id, t2.speaker_role as to_role,
               t2.content as to_content
        LIMIT 3
    """))
    
    for i, f in enumerate(flows, 1):
        print(f"\n{'━' * 80}")
        print(f"  ┃ VI DU {i}")
        print('━' * 80)
        
        content1 = f['from_content'][0] if f['from_content'] else ''
        content2 = f['to_content'][0] if f['to_content'] else ''
        
        print(f"\n  GIANG VIEN [{f['from_id']}]:")
        # Print first 500 chars
        print(f"  {content1[:500]}...")
        
        print(f"\n  -> HOA TRO LOI CUA HOC VIEN [{f['to_id']}]:")
        print(f"  {content2[:500]}...")

    # Student questions
    print('\n\n' + '=' * 80)
    print('                    CAC CAU HOI CUA HOC VIEN (DAY DU)')
    print('=' * 80)
    
    student_questions = list(session.run("""
        MATCH (l:Lecture)<-[:BELONGS_TO]-(t:Turn)<-[:SPEAKS]-(sp:Speaker)
        WHERE t.speaker_role = 'student' AND t.is_question = true
        RETURN t.id as turn_id, t.content as content, l.title as lecture
        ORDER BY l.title, turn_id
        LIMIT 15
    """))
    
    for i, q in enumerate(student_questions, 1):
        content = q['content'][0] if q['content'] else ''
        print(f"\n  {i}. [{q['turn_id']}] - {q['lecture']}")
        print(f"     {content[:300]}...")

driver.close()
print('\n' + '=' * 80)
print('                         KET THUC BAO CAO')
print('=' * 80)
