"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
REPOSITORY_ROOT = PROJECT_DIR.parent

# Prefer a project-local file when present, while retaining compatibility with
# the hackathon repository's root .env file.
load_dotenv(REPOSITORY_ROOT / ".env")
load_dotenv(PROJECT_DIR / ".env", override=True)


class Settings(BaseModel):
    """Validated runtime settings."""

    model_config = ConfigDict(frozen=True)

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "vlearn_transcripts_openai_small_768_v1"
    openai_api_key: str = ""
    # Blank means api.openai.com; set it to route through an OpenAI-compatible
    # relay such as YEScale.
    openai_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 768
    qdrant_timeout_seconds: int = 60
    embedding_batch_size: int = 32
    transcript_dir: Path = Field(
        default=REPOSITORY_ROOT / "data" / "vlearn-pack" / "transcript"
    )
    artifact_dir: Path = Field(default=PROJECT_DIR / "artifacts")

    @field_validator(
        "qdrant_collection",
        "embedding_model",
    )
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("configuration value must not be blank")
        return value

    @field_validator("embedding_dimensions")
    @classmethod
    def dimensions_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("embedding dimensions must be positive")
        return value

    @field_validator("embedding_batch_size")
    @classmethod
    def batch_size_must_be_valid(cls, value: int) -> int:
        if not 1 <= value <= 2048:
            raise ValueError("embedding batch size must be between 1 and 2048")
        return value


def load_settings() -> Settings:
    """Load settings; API clients validate credentials when instantiated."""

    return Settings(
        qdrant_url=os.getenv("QDRANT_URL", ""),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", ""),
        qdrant_collection=os.getenv(
            "QDRANT_COLLECTION",
            "vlearn_transcripts_openai_small_768_v1",
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
        embedding_dimensions=int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "768")),
        qdrant_timeout_seconds=int(os.getenv("QDRANT_TIMEOUT_SECONDS", "60")),
        embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
        transcript_dir=Path(
            os.getenv(
                "TRANSCRIPT_DIR",
                str(REPOSITORY_ROOT / "data" / "vlearn-pack" / "transcript"),
            )
        ).resolve(),
        artifact_dir=Path(
            os.getenv("ARTIFACT_DIR", str(PROJECT_DIR / "artifacts"))
        ).resolve(),
    )


settings = load_settings()
