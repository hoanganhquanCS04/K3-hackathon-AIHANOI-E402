import pytest

from vector_db.config import Settings
from vector_db.embeddings import EmbeddingService
from vector_db.qdrant_store import QdrantStore


def test_parser_settings_do_not_require_api_credentials(tmp_path) -> None:
    config = Settings(
        transcript_dir=tmp_path,
        artifact_dir=tmp_path,
    )

    assert config.embedding_dimensions == 768
    assert config.openai_api_key == ""
    assert config.qdrant_api_key == ""


def test_api_clients_validate_credentials_at_use_time(tmp_path) -> None:
    config = Settings(
        transcript_dir=tmp_path,
        artifact_dir=tmp_path,
    )

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        EmbeddingService(config)
    with pytest.raises(RuntimeError, match="QDRANT"):
        QdrantStore(config)
