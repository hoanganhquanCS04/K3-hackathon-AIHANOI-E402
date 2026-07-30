"""
Configuration module for Hybrid RAG & Summarization System.

This module handles secure loading of environment variables and initializes
connection clients for Qdrant (Vector Store) and Neo4j (Knowledge Graph).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv(".env", override=True)

# =============================================================================
# Individual Config Classes (No BaseSettings - use directly)
# =============================================================================

class LLMConfig(BaseModel):
    """LLM Provider Configuration."""

    api_key: str = Field(default="", description="API key for LLM provider")
    model: str = Field(default="gpt-4o", description="LLM model name")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for vectorization"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)


class QdrantConfig(BaseModel):
    """Qdrant Vector Store Configuration."""

    host: str = Field(default="", description="Qdrant Cloud host URL")
    port: int = Field(default=6333, description="Qdrant port")
    api_key: str = Field(default="", description="Qdrant API key")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # Collection names
    child_chunks_collection: str = Field(
        default="transcript_child_chunks",
        description="Collection for child chunks (individual turns)"
    )
    parent_chunks_collection: str = Field(
        default="transcript_parent_chunks",
        description="Collection for parent chunks (grouped turns)"
    )

    # Vector configuration
    vector_dim: int = Field(
        default=1536,
        description="Embedding vector dimension"
    )
    distance_metric: str = Field(
        default="Cosine",
        description="Distance metric for similarity search"
    )


class Neo4jConfig(BaseModel):
    """Neo4j Graph Database Configuration."""

    uri: str = Field(default="", description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: str = Field(default="", description="Neo4j password")
    database: str = Field(default="neo4j", description="Database name")
    max_connection_lifetime: int = Field(
        default=3600,
        description="Max connection lifetime in seconds"
    )


class ChunkingConfig(BaseModel):
    """Chunking Configuration for Transcript Processing."""

    parent_chunk_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of child turns per parent chunk"
    )
    chunk_overlap: int = Field(
        default=1,
        ge=0,
        description="Number of overlapping turns between parent chunks"
    )
    min_turn_length: int = Field(
        default=10,
        ge=1,
        description="Minimum character length for a valid turn"
    )
    max_turn_length: int = Field(
        default=5000,
        ge=100,
        description="Maximum character length for a turn before splitting"
    )


class RetrievalConfig(BaseModel):
    """Retrieval Configuration."""

    default_top_k: int = Field(
        default=5,
        ge=1,
        description="Default number of results to retrieve"
    )
    max_retrieval_results: int = Field(
        default=10,
        ge=1,
        description="Maximum number of retrieval results"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )
    enable_reranking: bool = Field(
        default=True,
        description="Enable reranking of retrieval results"
    )


class AppConfig(BaseModel):
    """Application Configuration."""

    # Paths
    data_dir: Path = Field(
        default=Path("data"),
        description="Data directory path"
    )
    cache_dir: Path = Field(
        default=Path("data/cache"),
        description="Cache directory path"
    )
    logs_dir: Path = Field(
        default=Path("logs"),
        description="Logs directory path"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )


# =============================================================================
# Config Loader Function
# =============================================================================

def load_config_from_env() -> tuple[LLMConfig, QdrantConfig, Neo4jConfig, ChunkingConfig, RetrievalConfig, AppConfig]:
    """
    Load all configuration from environment variables.

    Returns:
        Tuple of all config objects.
    """

    # LLM Config
    llm_config = LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
    )

    # Qdrant Config
    qdrant_config = QdrantConfig(
        host=os.getenv("QDRANT_HOST", ""),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        api_key=os.getenv("QDRANT_API_KEY", ""),
        timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
        child_chunks_collection=os.getenv("QDRANT_CHILD_CHUNKS_COLLECTION", "transcript_child_chunks"),
        parent_chunks_collection=os.getenv("QDRANT_PARENT_CHUNKS_COLLECTION", "transcript_parent_chunks"),
        vector_dim=int(os.getenv("QDRANT_VECTOR_DIM", "1536")),
        distance_metric=os.getenv("QDRANT_DISTANCE_METRIC", "Cosine"),
    )

    # Neo4j Config
    neo4j_config = Neo4jConfig(
        uri=os.getenv("NEO4J_URI", ""),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", ""),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
        max_connection_lifetime=int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "3600")),
    )

    # Chunking Config
    chunking_config = ChunkingConfig(
        parent_chunk_size=int(os.getenv("PARENT_CHUNK_SIZE", "5")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "1")),
        min_turn_length=int(os.getenv("MIN_TURN_LENGTH", "10")),
        max_turn_length=int(os.getenv("MAX_TURN_LENGTH", "5000")),
    )

    # Retrieval Config
    retrieval_config = RetrievalConfig(
        default_top_k=int(os.getenv("DEFAULT_TOP_K", "5")),
        max_retrieval_results=int(os.getenv("MAX_RETRIEVAL_RESULTS", "10")),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
        enable_reranking=os.getenv("ENABLE_RERANKING", "true").lower() == "true",
    )

    # App Config
    app_config = AppConfig(
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        cache_dir=Path(os.getenv("CACHE_DIR", "data/cache")),
        logs_dir=Path(os.getenv("LOG_DIR", "logs")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    return llm_config, qdrant_config, neo4j_config, chunking_config, retrieval_config, app_config


# =============================================================================
# Settings Container (with lazy loading)
# =============================================================================

class Settings:
    """
    Main settings container that aggregates all configuration sections.
    """

    _instance = None
    _llm: Optional[LLMConfig] = None
    _qdrant: Optional[QdrantConfig] = None
    _neo4j: Optional[Neo4jConfig] = None
    _chunking: Optional[ChunkingConfig] = None
    _retrieval: Optional[RetrievalConfig] = None
    _app: Optional[AppConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load all configurations from environment."""
        llm, qdrant, neo4j, chunking, retrieval, app = load_config_from_env()
        self._llm = llm
        self._qdrant = qdrant
        self._neo4j = neo4j
        self._chunking = chunking
        self._retrieval = retrieval
        self._app = app

        # Create directories
        for dir_path in [self._app.data_dir, self._app.cache_dir, self._app.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def llm(self) -> LLMConfig:
        return self._llm

    @property
    def qdrant(self) -> QdrantConfig:
        return self._qdrant

    @property
    def neo4j(self) -> Neo4jConfig:
        return self._neo4j

    @property
    def chunking(self) -> ChunkingConfig:
        return self._chunking

    @property
    def retrieval(self) -> RetrievalConfig:
        return self._retrieval

    @property
    def app(self) -> AppConfig:
        return self._app


# =============================================================================
# Client Factories (Deferred imports)
# =============================================================================

_qdrant_client = None
_neo4j_driver = None


def get_qdrant_client() -> "QdrantClient":
    """Get or create Qdrant client instance."""
    global _qdrant_client

    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        settings = Settings()
        config = settings.qdrant

        if config.host.startswith("http"):
            _qdrant_client = QdrantClient(
                url=config.host,
                port=config.port,
                api_key=config.api_key,
                timeout=config.timeout
            )
        else:
            _qdrant_client = QdrantClient(
                host=config.host,
                port=config.port,
                timeout=config.timeout
            )

    return _qdrant_client


def get_neo4j_driver():
    """Get or create Neo4j driver instance."""
    global _neo4j_driver

    if _neo4j_driver is None:
        from neo4j import GraphDatabase
        settings = Settings()
        config = settings.neo4j

        _neo4j_driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password),
            max_connection_lifetime=config.max_connection_lifetime
        )

        # Verify connectivity
        _neo4j_driver.verify_connectivity()

    return _neo4j_driver


def close_all_clients():
    """Close all client connections."""
    global _qdrant_client, _neo4j_driver

    if _neo4j_driver is not None:
        _neo4j_driver.close()
        _neo4j_driver = None

    _qdrant_client = None


# =============================================================================
# Convenience Accessors
# =============================================================================

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return get_settings().llm


def get_qdrant_config() -> QdrantConfig:
    """Get Qdrant configuration."""
    return get_settings().qdrant


def get_neo4j_config() -> Neo4jConfig:
    """Get Neo4j configuration."""
    return get_settings().neo4j


def get_chunking_config() -> ChunkingConfig:
    """Get chunking configuration."""
    return get_settings().chunking


def get_retrieval_config() -> RetrievalConfig:
    """Get retrieval configuration."""
    return get_settings().retrieval


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Hybrid RAG System - Configuration Test")
    print("=" * 60)

    try:
        settings = Settings()
        print("Settings loaded successfully!")
        print(f"  - LLM Model: {settings.llm.model}")
        print(f"  - Embedding Model: {settings.llm.embedding_model}")
        print(f"  - Qdrant Host: {settings.qdrant.host}")
        print(f"  - Neo4j URI: {settings.neo4j.uri}")
        print(f"  - Parent Chunk Size: {settings.chunking.parent_chunk_size}")

    except Exception as e:
        print(f"\nConfiguration Error: {e}")
        print("\nPlease ensure your .env file is properly configured.")
