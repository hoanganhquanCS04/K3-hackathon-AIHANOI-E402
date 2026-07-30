"""Summary queries"""
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

print('=' * 60)
print('TOM TAT NOI DUNG BAI GIANG')
print('=' * 60)

with driver.session(database=database) as session:
    print('\n=== TOM TAT THEO BAI GIANG ===')
    result = session.run('''
        MATCH (l:Lecture)
        OPTIONAL MATCH (l)-[:COVERS]->(t:Topic)
        OPTIONAL MATCH (l)-[:INTRODUCES]->(c:Concept)
        OPTIONAL MATCH (l)-[:INTRODUCES]->(r:Reference)
        OPTIONAL MATCH (l)<-[:BELONGS_TO]-(turn:Turn)
        RETURN l.id as lecture_id, l.title as title, l.day as day,
               count(DISTINCT t) as topics,
               count(DISTINCT c) as concepts,
               count(DISTINCT r) as references,
               count(DISTINCT turn) as turns
        ORDER BY l.day, l.title
    ''')
    for r in result:
        print(f'\n[{r["lecture_id"]}] {r["title"]}')
        print(f'  Day: {r["day"] or "N/A"}')
        print(f'  Topics: {r["topics"]} | Concepts: {r["concepts"]} | References: {r["references"]}')
        print(f'  Turns: {r["turns"]}')

    print('\n\n=== CAC CONCEPT CHINH ===')
    result = session.run('''
        MATCH (c:Concept)
        RETURN c.name as concept, c.description as description
        ORDER BY concept
    ''')
    for r in result:
        desc = r["description"] or ""
        print(f'  - {r["concept"]}: {desc[:60]}...' if desc else f'  - {r["concept"]}')

    print('\n\n=== CAC TAI LIEU THAM CHIEU ===')
    result = session.run('''
        MATCH (r:Reference)
        RETURN r.title as title, r.author as author, r.type as type
        ORDER BY title
    ''')
    for r in result:
        print(f'  - {r["title"]} by {r["author"]} ({r["type"]})')

    print('\n\n=== TOPICS NOI BAT ===')
    result = session.run('''
        MATCH (l:Lecture)-[:COVERS]->(t:Topic)
        RETURN t.name as topic, collect(l.title)[0] as lecture, count(*) as mentions
        ORDER BY mentions DESC
        LIMIT 15
    ''')
    for r in result:
        print(f'  [{r["mentions"]}] {r["topic"]}')

driver.close()
print('\n' + '=' * 60)
