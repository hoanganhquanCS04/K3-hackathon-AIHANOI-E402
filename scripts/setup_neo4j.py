"""
Neo4j Database Setup Script

How to use:
1. Ensure .env is configured with Neo4j credentials
2. Run: python scripts/setup_neo4j.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import get_neo4j_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


# =============================================================================
# GRAPH SCHEMA DEFINITIONS
# =============================================================================

NODE_TYPES = {
    "Lecture": {
        "description": "A lecture session",
        "properties": ["id", "title", "day", "date", "duration"]
    },
    "Topic": {
        "description": "A main topic discussed in lecture",
        "properties": ["id", "name", "category"]
    },
    "Concept": {
        "description": "A key concept or framework",
        "properties": ["id", "name", "description"]
    },
    "Speaker": {
        "description": "A person speaking in the lecture",
        "properties": ["id", "name", "role"]
    },
    "Turn": {
        "description": "A single speaking turn/chunk",
        "properties": ["id", "turn_id", "content", "speaker_role"]
    },
    "Question": {
        "description": "A question asked by a participant",
        "properties": ["id", "content"]
    },
    "Answer": {
        "description": "An answer or explanation",
        "properties": ["id", "content"]
    },
    "Reference": {
        "description": "Book, framework, or external reference mentioned",
        "properties": ["id", "title", "author", "type"]
    }
}

RELATIONSHIP_TYPES = {
    "BELONGS_TO": {"from": "Turn", "to": "Lecture"},
    "COVERS": {"from": "Lecture", "to": "Topic"},
    "INTRODUCES": {"from": "Lecture", "to": "Concept"},
    "SPEAKS": {"from": "Speaker", "to": "Turn"},
    "RELATES_TO": {"from": "Concept", "to": "Concept"},
    "ANSWERS": {"from": "Turn", "to": "Question"},
    "MENTIONS": {"from": "Turn", "to": "Reference"},
    "FOLLOWS": {"from": "Turn", "to": "Turn"}
}


# =============================================================================
# SCHEMA SETUP QUERIES
# =============================================================================

def create_constraints_and_indexes(session):
    """Create constraints and indexes for optimal performance."""

    print("\n--- Creating Schema ---")

    constraints = [
        "CREATE CONSTRAINT lecture_id IF NOT EXISTS FOR (n:Lecture) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (n:Topic) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT speaker_id IF NOT EXISTS FOR (n:Speaker) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT turn_id IF NOT EXISTS FOR (n:Turn) REQUIRE n.id IS UNIQUE",
    ]

    indexes = [
        "CREATE INDEX turn_content IF NOT EXISTS FOR (n:Turn) ON (n.content)",
        "CREATE INDEX concept_name IF NOT EXISTS FOR (n:Concept) ON (n.name)",
        "CREATE INDEX topic_name IF NOT EXISTS FOR (n:Topic) ON (n.name)",
    ]

    for constraint in constraints:
        try:
            session.run(constraint)
            name = constraint.split("(")[1].split(":")[0]
            print(f"  Created constraint: {name}")
        except Exception as e:
            print(f"  Warning (constraint may exist): {str(e)[:50]}")

    for index in indexes:
        try:
            session.run(index)
            name = index.split("INDEX")[1].split("IF")[0].strip()
            print(f"  Created index: {name}")
        except Exception as e:
            print(f"  Warning (index may exist): {str(e)[:50]}")


def create_sample_data(session):
    """Create sample data to verify the setup."""

    print("\n--- Creating Sample Data ---")

    # Sample lecture
    session.run("""
    CREATE (l:Lecture {
        id: 'day2-morning',
        title: 'Xac dinh bai toan kinh doanh cho AI',
        day: 'Day 2',
        date: '2024-01-15'
    })
    """)

    # Sample concepts
    concepts = [
        {"id": "double-diamond", "name": "Double Diamond", "desc": "Model thiet ke 4 giai doan: kham pha - dinh nghia - phat trien - trien khai"},
        {"id": "first-principle", "name": "First Principle Thinking", "desc": "Tu duy tu nguyen ban, boc tach van de ve nguyen ly co ban nhat"},
        {"id": "impact-effort", "name": "Impact-Effort Matrix", "desc": "Ma tran danh gia tac dong va noi luc de uu tien cong viec"},
        {"id": "five-whys", "name": "Five Whys", "desc": "Ky thuat hoi tai sao 5 lan de tim nguyen nhan goc"},
        {"id": "hcd", "name": "Human-Centered Design", "desc": "Thiet ke lay con nguoi lam trung tam"},
        {"id": "dogfooding", "name": "Dogfooding", "desc": "Chien luoc build san pham va tu su dung truoc"},
    ]

    for c in concepts:
        session.run(
            "CREATE (c:Concept {id: $id, name: $name, description: $desc})",
            id=c["id"], name=c["name"], desc=c["desc"]
        )
        print(f"  Created concept: {c['name']}")

    # Sample topics
    topics = [
        {"id": "problem-definition", "name": "Xac dinh bai toan"},
        {"id": "product-thinking", "name": "Tu duy san pham"},
        {"id": "ai-product-dev", "name": "Phat trien san pham AI"},
    ]

    for t in topics:
        session.run(
            "CREATE (t:Topic {id: $id, name: $name})",
            id=t["id"], name=t["name"]
        )
        print(f"  Created topic: {t['name']}")

    # Sample references
    refs = [
        {"id": "thinking-fast-slow", "title": "Thinking Fast and Slow", "author": "Daniel Kahneman", "type": "book"},
        {"id": "design-everyday", "title": "The Design of Everyday Things", "author": "Don Norman", "type": "book"},
        {"id": "ai-engineering", "title": "AI Engineering", "author": "Chip Huyen", "type": "book"},
    ]

    for r in refs:
        session.run(
            "CREATE (r:Reference {id: $id, title: $title, author: $author, type: $type})",
            id=r["id"], title=r["title"], author=r["author"], type=r["type"]
        )
        print(f"  Created reference: {r['title']}")

    # Relationships
    print("\n  Creating relationships...")
    session.run("""
    MATCH (l:Lecture {id: 'day2-morning'})
    MATCH (t:Topic)
    CREATE (l)-[:COVERS]->(t)
    """)

    session.run("""
    MATCH (l:Lecture {id: 'day2-morning'})
    MATCH (c:Concept)
    CREATE (l)-[:INTRODUCES]->(c)
    """)

    session.run("""
    MATCH (c1:Concept {id: 'first-principle'}), (c2:Concept {id: 'double-diamond'})
    CREATE (c1)-[:RELATES_TO {type: 'complementary'}]->(c2)
    """)


def verify_setup(session):
    """Verify the database setup."""

    print("\n--- Verification ---")

    # Count nodes by type
    for node_type in NODE_TYPES.keys():
        result = session.run(f" MATCH (n:{node_type}) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"  {node_type}: {count} nodes")

    # Count relationships
    result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count")
    print("\n  Relationships:")
    for record in result:
        print(f"    {record['rel_type']}: {record['count']}")


# =============================================================================
# MAIN SETUP FUNCTION
# =============================================================================

def setup_neo4j_database():
    """Main function to set up the Neo4j database."""

    print("=" * 60)
    print("Neo4j Graph Database Setup")
    print("=" * 60)

    setup_logging(log_level="INFO")

    try:
        # Get Neo4j configuration
        config = get_neo4j_config()
        print(f"\nConnecting to: {config.uri}")

        # Import driver
        from neo4j import GraphDatabase

        # Connect
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password)
        )

        # Verify
        driver.verify_connectivity()
        print("Connected to Neo4j AuraDB!")

        # Create session
        with driver.session(database=config.database) as session:
            session.run("RETURN 1 as test")
            print("Database connection verified!")

            # Create schema
            create_constraints_and_indexes(session)

            # Create sample data
            create_sample_data(session)

            # Verify
            verify_setup(session)

        driver.close()

        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Explore data: Use Neo4j Browser at your AuraDB URL")
        print("  2. Run queries: python scripts/query_neo4j.py")
        print("  3. Ingest transcripts: python scripts/ingest_transcripts.py")

    except Exception as e:
        print(f"\nSetup failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your .env file has correct Neo4j credentials")
        print("  2. Ensure your Neo4j AuraDB instance is running")
        print("  3. Check your internet connection")
        raise


if __name__ == "__main__":
    setup_neo4j_database()
