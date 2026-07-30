"""Knowledge Graph DB — Neo4j."""

from graph_db.connection import get_database, get_driver, query

__all__ = ["get_database", "get_driver", "query"]
