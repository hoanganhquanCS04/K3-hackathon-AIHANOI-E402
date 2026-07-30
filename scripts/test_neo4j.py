"""
Test Neo4j Connection Script

Run this script to test the connection to Neo4j AuraDB.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import get_neo4j_config
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def test_connection():
    """Test the Neo4j connection."""

    print("=" * 60)
    print("Neo4j Connection Test")
    print("=" * 60)

    try:
        # Get config
        config = get_neo4j_config()
        print(f"\nConnecting to: {config.uri}")
        print(f"   Username: {config.username}")
        print(f"   Database: {config.database}")

        # Import here to avoid circular imports
        from neo4j import GraphDatabase

        # Connect
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password)
        )
        print("Connection established!")

        # Run test query
        with driver.session(database=config.database) as session:
            result = session.run("RETURN 'Neo4j Connected!' as message, datetime() as timestamp")
            record = result.single()
            print(f"\nTest Query Result:")
            print(f"   {record['message']}")
            print(f"   Timestamp: {record['timestamp']}")

            # Get database info
            result = session.run("SHOW DATABASES")
            print(f"\nAvailable Databases:")
            for record in result:
                print(f"   - {record['name']} ({record['type']})")

            # Check if there are any nodes
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            count = result.single()["total_nodes"]
            print(f"\nTotal Nodes in database: {count}")

            # List labels
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            print(f"\nNode Labels: {labels if labels else '(none yet)'}")

            # List relationship types
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            print(f"Relationship Types: {rel_types if rel_types else '(none yet)'}")

        driver.close()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour Neo4j database is ready. You can now:")
        print("  1. Run setup: python scripts/setup_neo4j.py")
        print("  2. Open Neo4j Browser at your AuraDB URL to visualize data")

    except Exception as e:
        print("\n" + "=" * 60)
        print("CONNECTION FAILED!")
        print("=" * 60)
        print(f"\nError: {e}")

        if "FÓR" in str(e).upper() or "password" in str(e).lower():
            print("\nFix: Check your .env file")
            print("   - NEO4J_URI should be like: neo4j+s://xxxxx.databases.neo4j.io")
            print("   - NEO4J_PASSWORD should be your actual AuraDB password")
        elif "Connection refused" in str(e):
            print("\nFix: Check your internet connection")
        else:
            print("\nPlease check your Neo4j credentials in .env")

        sys.exit(1)


if __name__ == "__main__":
    setup_logging(log_level="INFO")
    test_connection()
