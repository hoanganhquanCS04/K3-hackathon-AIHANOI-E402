"""OpenAI embedding service with validation, retry, batching, and cache."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import numpy as np
import tiktoken
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from vector_db.config import Settings, settings

RETRYABLE_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)


class EmbeddingService:
    """Generate and cache embeddings using one locked model configuration."""

    def __init__(
        self,
        app_settings: Settings = settings,
        *,
        cache_path: Path | None = None,
    ) -> None:
        self.settings = app_settings
        if not app_settings.openai_api_key.strip():
            raise RuntimeError(
                "Missing OPENAI_API_KEY. It is required for embedding "
                "API calls but not for parser tests or --dry-run."
            )
        self.client = OpenAI(
            api_key=app_settings.openai_api_key,
            base_url=app_settings.openai_base_url or None,
        )
        app_settings.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = (
            cache_path or app_settings.artifact_dir / "embedding_cache.sqlite3"
        )
        self._connection = sqlite3.connect(self.cache_path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                vector_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()
        try:
            self._encoding = tiktoken.encoding_for_model(app_settings.embedding_model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")
        self.api_requests = 0
        self.api_inputs = 0
        self.api_tokens = 0
        self.cache_hits = 0

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _cache_key(self, text: str) -> str:
        material = (
            f"{self.settings.embedding_model}\0"
            f"{self.settings.embedding_dimensions}\0{text}"
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _validate_text(self, text: str, logical_id: str) -> None:
        if not text.strip():
            raise ValueError(f"Empty embedding input: {logical_id}")
        token_count = len(self._encoding.encode(text))
        if token_count > 8192:
            raise ValueError(
                f"Embedding input exceeds 8192 tokens: "
                f"{logical_id} ({token_count} tokens)"
            )

    def _read_cache(self, cache_key: str) -> list[float] | None:
        row = self._connection.execute(
            """
            SELECT vector_json
            FROM embeddings
            WHERE cache_key = ?
              AND model = ?
              AND dimensions = ?
            """,
            (
                cache_key,
                self.settings.embedding_model,
                self.settings.embedding_dimensions,
            ),
        ).fetchone()
        if row is None:
            return None
        vector = json.loads(row[0])
        self._validate_vector(vector)
        self.cache_hits += 1
        return vector

    def _write_cache(
        self,
        cache_key: str,
        vector: list[float],
    ) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO embeddings (
                cache_key,
                model,
                dimensions,
                vector_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                self.settings.embedding_model,
                self.settings.embedding_dimensions,
                json.dumps(vector, separators=(",", ":")),
                datetime.now(UTC).isoformat(),
            ),
        )

    def _validate_vector(self, vector: list[float]) -> None:
        actual = len(vector)
        expected = self.settings.embedding_dimensions
        if actual != expected:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected}, received {actual}"
            )
        if not all(np.isfinite(value) for value in vector):
            raise ValueError("Embedding contains a non-finite value")

    @retry(
        retry=retry_if_exception_type(RETRYABLE_ERRORS),
        wait=wait_random_exponential(min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _request(self, texts: list[str]):
        return self.client.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
            dimensions=self.settings.embedding_dimensions,
            encoding_format="float",
        )

    def embed_many(
        self,
        items: Iterable[tuple[str, str]],
    ) -> dict[str, list[float]]:
        """Embed `(logical_id, text)` pairs while preserving identity."""

        pairs = list(items)
        if len({logical_id for logical_id, _ in pairs}) != len(pairs):
            raise ValueError("Duplicate logical IDs in embedding batch")

        result: dict[str, list[float]] = {}
        misses: list[tuple[str, str, str]] = []
        for logical_id, text in pairs:
            self._validate_text(text, logical_id)
            cache_key = self._cache_key(text)
            cached = self._read_cache(cache_key)
            if cached is not None:
                result[logical_id] = cached
            else:
                misses.append((logical_id, text, cache_key))

        batch_size = self.settings.embedding_batch_size
        for start in range(0, len(misses), batch_size):
            batch = misses[start : start + batch_size]
            response = self._request([text for _, text, _ in batch])
            self.api_requests += 1
            self.api_inputs += len(batch)
            self.api_tokens += response.usage.total_tokens
            if len(response.data) != len(batch):
                raise RuntimeError(
                    "OpenAI returned a different number of embeddings than requested"
                )
            ordered = sorted(response.data, key=lambda item: item.index)
            for (logical_id, _text, cache_key), item in zip(
                batch,
                ordered,
                strict=True,
            ):
                vector = list(item.embedding)
                self._validate_vector(vector)
                result[logical_id] = vector
                self._write_cache(cache_key, vector)
            self._connection.commit()

        return result

    def embed_one(self, logical_id: str, text: str) -> list[float]:
        return self.embed_many([(logical_id, text)])[logical_id]

    @staticmethod
    def mean_normalized(
        child_vectors: Iterable[list[float]],
    ) -> list[float]:
        vectors = list(child_vectors)
        if not vectors:
            raise ValueError("Cannot build parent vector without children")
        matrix = np.asarray(vectors, dtype=np.float32)
        parent = matrix.mean(axis=0)
        norm = float(np.linalg.norm(parent))
        if norm == 0:
            raise ValueError("Parent vector has zero norm")
        return (parent / norm).tolist()

    def usage_summary(self) -> dict[str, int | str]:
        return {
            "model": self.settings.embedding_model,
            "dimensions": self.settings.embedding_dimensions,
            "api_requests": self.api_requests,
            "api_inputs": self.api_inputs,
            "api_tokens": self.api_tokens,
            "cache_hits": self.cache_hits,
        }
