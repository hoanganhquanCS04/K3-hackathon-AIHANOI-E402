# =============================================================================
# HYBRID RAG & SUMMARIZATION SYSTEM
# =============================================================================
# A dual-index architecture combining:
#   - Branch A: Vector Store (Qdrant) for local/conversational context
#   - Branch B: Knowledge Graph (Neo4j) for global/distributed context
# =============================================================================

# Data directory
data/
    raw/                    # Raw transcript files
    processed/              # Processed chunks and entities
    cache/                  # Cached embeddings and results

# Source code
src/
    ingestion/              # Data ingestion pipeline
        __init__.py
        transcript_parser.py    # Parse [TXX-XXX] anchors
        chunker.py              # Child/Parent chunking logic
        document_store.py       # Local parent chunk storage
        entity_extractor.py     # LLM-based triplet extraction
    retrieval/              # Retrieval and query pipeline
        __init__.py
        vector_retriever.py     # Qdrant parent-child retriever
        graph_retriever.py      # Neo4j subgraph retrieval
        router.py               # Query routing logic
        synthesizer.py          # Result synthesis
    storage/               # Storage clients
        __init__.py
        qdrant_client.py        # Qdrant connection management
        neo4j_client.py         # Neo4j connection management
    config/
        __init__.py
        config.py               # Configuration loading
    utils/
        __init__.py
        logger.py               # Logging utilities

# Configuration files
config/
    .env.example           # Environment variables template
    settings.yaml          # Application settings

# Tests
tests/
    test_ingestion.py
    test_retrieval.py
    test_integration.py

# Notebooks (optional exploration)
notebooks/
    exploration.ipynb      # Data exploration
    testing.ipynb          # Query testing

# Scripts
scripts/
    ingest_transcripts.py  # Batch ingestion script
    query_interface.py     # Interactive query interface
    extract_entities.py     # Entity extraction pipeline

# Documentation
docs/
    ARCHITECTURE.md        # System architecture
    API.md                 # API documentation
    DATA_FORMAT.md         # Transcript format specification

# =============================================================================
# Key Design Decisions:
# =============================================================================
# 1. Child Chunks: Each [TXX-XXX] turn is a child chunk → embedded in Qdrant
# 2. Parent Chunks: 3-5 sequential turns grouped → stored in local doc store
# 3. Triplet Extraction: LLM extracts (Subject)-[REL]->(Object) triplets
# 4. Routing: Query analysis → local (Qdrant), global (Neo4j), or hybrid
# =============================================================================
