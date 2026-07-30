"""
Sample Neo4j Queries Script

Các query mẫu để khám phá dữ liệu trong graph database.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config import get_neo4j_config, Neo4jClientManager
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def run_sample_queries():
    """Run sample queries to explore the graph."""

    print("=" * 60)
    print("Sample Neo4j Queries")
    print("=" * 60)

    try:
        config = get_neo4j_config()
        driver = Neo4jClientManager.get_driver(config)

        with driver.session(database=config.database) as session:

            # Query 1: Get all concepts
            print("\n📚 Query 1: All Concepts")
            print("-" * 40)
            query1 = """
            MATCH (c:Concept)
            RETURN c.name as name, c.description as description
            ORDER BY c.name
            """
            result = session.run(query1)
            for record in result:
                print(f"  • {record['name']}")
                print(f"    {record['description'][:80]}...")

            # Query 2: Get concept relationships
            print("\n🔗 Query 2: Concept Relationships")
            print("-" * 40)
            query2 = """
            MATCH (c1:Concept)-[r:RELATES_TO]->(c2:Concept)
            RETURN c1.name as from_concept, r.type as relation_type, c2.name as to_concept
            """
            result = session.run(query2)
            for record in result:
                print(f"  {record['from_concept']} --[{record['relation_type']}]--> {record['to_concept']}")

            # Query 3: Get topics covered by lectures
            print("\n📖 Query 3: Topics per Lecture")
            print("-" * 40)
            query3 = """
            MATCH (l:Lecture)-[:COVERS]->(t:Topic)
            RETURN l.title as lecture, collect(t.name) as topics
            """
            result = session.run(query3)
            for record in result:
                print(f"  📌 {record['lecture']}")
                for topic in record['topics']:
                    print(f"     - {topic}")

            # Query 4: Get references mentioned
            print("\n📚 Query 4: References")
            print("-" * 40)
            query4 = """
            MATCH (r:Reference)
            RETURN r.title as title, r.author as author, r.type as type
            ORDER BY r.type, r.title
            """
            result = session.run(query4)
            for record in result:
                print(f"  [{record['type']}] {record['title']} - {record['author']}")

            # Query 5: Semantic search simulation (full-text)
            print("\n🔍 Query 5: Search for 'design' in content")
            print("-" * 40)
            query5 = """
            MATCH (c:Concept)
            WHERE toLower(c.name) CONTAINS 'design' OR toLower(c.description) CONTAINS 'design'
            RETURN c.name as concept, c.description as description
            """
            result = session.run(query5)
            found = False
            for record in result:
                found = True
                print(f"  ✓ {record['concept']}")
                print(f"    {record['description'][:100]}...")
            if not found:
                print("  (No results found)")

            # Query 6: Graph exploration - find connected concepts
            print("\n🌐 Query 6: Find connected concepts from 'Double Diamond'")
            print("-" * 40)
            query6 = """
            MATCH path = (start:Concept {name: 'Double Diamond'})-[:RELATES_TO*1..2]-(connected)
            WHERE start <> connected
            RETURN start.name as start, connected.name as connected,
                   length(path) as distance
            ORDER BY distance
            """
            result = session.run(query6)
            for record in result:
                arrows = "→" * record['distance']
                print(f"  Double Diamond {arrows} {record['connected']} (distance: {record['distance']})")

        print("\n" + "=" * 60)
        print("✅ Query examples complete!")

    except Exception as e:
        logger.error(f"Query failed: {e}")
        print(f"\n❌ Error: {e}")

    finally:
        Neo4jClientManager.close()


if __name__ == "__main__":
    setup_logging(log_level="INFO")
    run_sample_queries()
