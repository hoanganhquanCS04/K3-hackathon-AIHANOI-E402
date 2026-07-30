"""Test Neo4j queries"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.getenv('NEO4J_URI', 'neo4j+s://6a80f29b.databases.neo4j.io')
username = os.getenv('NEO4J_USERNAME', '6a80f29b')
password = os.getenv('NEO4J_PASSWORD', '')
database = os.getenv('NEO4J_DATABASE', 'neo4j')

driver = GraphDatabase.driver(uri, auth=(username, password))

print("=" * 60)
print("TESTING NEO4J QUERIES")
print("=" * 60)

with driver.session(database=database) as session:
    print("\n=== QUERY 1: All Lectures ===")
    result = session.run("MATCH (l:Lecture) RETURN l.id, l.title, l.day")
    for r in result:
        print(f"  {r['l.id']}: {r['l.title']} ({r['l.day']})")
    
    print("\n=== QUERY 2: Topics by Lecture ===")
    result = session.run("""
        MATCH (l:Lecture)-[:COVERS]->(t:Topic)
        RETURN l.title as lecture, count(t) as topic_count
        ORDER BY lecture
    """)
    for r in result:
        print(f"  {r['lecture']}: {r['topic_count']} topics")
    
    print("\n=== QUERY 3: Concepts ===")
    result = session.run("MATCH (c:Concept) RETURN c.name, c.description")
    for r in result:
        print(f"  - {r['c.name']}")
    
    print("\n=== QUERY 4: Speaker Distribution ===")
    result = session.run("""
        MATCH (sp:Speaker)-[:SPEAKS]->(t:Turn)
        RETURN sp.role as role, count(DISTINCT sp) as speakers, count(t) as turns
    """)
    for r in result:
        print(f"  {r['role']}: {r['speakers']} speakers, {r['turns']} turns")
    
    print("\n=== QUERY 5: Sample Turn Flow ===")
    result = session.run("""
        MATCH (t1:Turn)-[:FOLLOWS]->(t2:Turn)
        WHERE t1.speaker_role = 'instructor'
        RETURN t1.id as from_turn, t1.content[0..50] as from_content,
               t2.id as to_turn, t2.speaker_role as to_role
        LIMIT 3
    """)
    for r in result:
        print(f"  [{r['from_turn']}] -> [{r['to_turn']}] ({r['to_role']})")
        print(f"    From: {r['from_content']}...")

driver.close()
print("\n" + "=" * 60)
print("Query completed successfully!")
