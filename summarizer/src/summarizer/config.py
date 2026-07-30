"""Cấu hình runtime cho tầng tóm tắt."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, field_validator

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
REPOSITORY_ROOT = PROJECT_DIR.parent

# .env ở gốc repo là nguồn chung của cả team; .env riêng của project ghi đè lên.
load_dotenv(REPOSITORY_ROOT / ".env")
load_dotenv(PROJECT_DIR / ".env", override=True)


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    openai_api_key: str = ""

    # Để rỗng nếu dùng api.openai.com. Điền khi đi qua relay tương thích OpenAI
    # (YEScale, LiteLLM, Azure gateway...).
    openai_base_url: str = ""

    # Map rẻ và chạy 96 lần; reduce đắt hơn nhưng chỉ chạy 6 lần. Xem plan §9.3.
    map_model: str = "gpt-4o-mini"
    reduce_model: str = "gpt-4o"
    map_temperature: float = 0.2
    reduce_temperature: float = 0.3

    # Nguồn nội dung: "local" đọc thẳng transcript qua parser của M1,
    # "qdrant" gọi structured reader. Xem plan §12.1.
    loader_backend: str = "local"

    # Song song hoá bước map. Đừng nâng cao hơn nếu chưa đo rate limit.
    max_concurrency: int = 5
    request_timeout_seconds: int = 120
    max_retries: int = 5

    artifact_dir: Path = PROJECT_DIR / "artifacts"

    @field_validator("loader_backend")
    @classmethod
    def backend_must_be_known(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"local", "qdrant"}:
            raise ValueError("SUMMARIZER_LOADER must be 'local' or 'qdrant'")
        return value

    @field_validator("max_concurrency")
    @classmethod
    def concurrency_must_be_sane(cls, value: int) -> int:
        if not 1 <= value <= 32:
            raise ValueError("SUMMARIZER_CONCURRENCY must be between 1 and 32")
        return value

    @property
    def cache_dir(self) -> Path:
        return self.artifact_dir / "summary_cache"

    @property
    def summaries_dir(self) -> Path:
        return self.artifact_dir / "summaries"

    @property
    def manifest_path(self) -> Path:
        return self.artifact_dir / "summary_manifest.json"


def load_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        map_model=os.getenv("SUMMARIZER_MAP_MODEL", "gpt-4o-mini"),
        reduce_model=os.getenv("SUMMARIZER_REDUCE_MODEL", "gpt-4o"),
        map_temperature=float(os.getenv("SUMMARIZER_MAP_TEMPERATURE", "0.2")),
        reduce_temperature=float(os.getenv("SUMMARIZER_REDUCE_TEMPERATURE", "0.3")),
        loader_backend=os.getenv("SUMMARIZER_LOADER", "local"),
        max_concurrency=int(os.getenv("SUMMARIZER_CONCURRENCY", "5")),
        request_timeout_seconds=int(os.getenv("SUMMARIZER_TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("SUMMARIZER_MAX_RETRIES", "5")),
        artifact_dir=Path(
            os.getenv("SUMMARIZER_ARTIFACT_DIR", str(PROJECT_DIR / "artifacts"))
        ).resolve(),
    )


settings = load_settings()
