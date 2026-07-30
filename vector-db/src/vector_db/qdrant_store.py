"""Qdrant Cloud collection lifecycle, upload, query, and scrolling."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from qdrant_client import QdrantClient, models

from vector_db.config import Settings, settings
from vector_db.models import SearchHit

PAYLOAD_INDEXES: dict[str, models.PayloadSchemaType] = {
    "point_type": models.PayloadSchemaType.KEYWORD,
    "session_id": models.PayloadSchemaType.KEYWORD,
    "section_id": models.PayloadSchemaType.KEYWORD,
    "session_day": models.PayloadSchemaType.INTEGER,
    "session_period": models.PayloadSchemaType.KEYWORD,
    "has_unclear": models.PayloadSchemaType.BOOL,
    "is_activity": models.PayloadSchemaType.BOOL,
    "speaker_role": models.PayloadSchemaType.KEYWORD,
    "content_type": models.PayloadSchemaType.KEYWORD,
}


def make_point_id(point_type: str, logical_id: str) -> str:
    """Create a stable Qdrant-compatible UUID."""

    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{point_type}:{logical_id}",
        )
    )


class QdrantStore:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        missing = [
            name
            for name, value in {
                "QDRANT_URL": app_settings.qdrant_url,
                "QDRANT_API_KEY": app_settings.qdrant_api_key,
            }.items()
            if not value.strip()
        ]
        if missing:
            raise RuntimeError(
                "Missing required Qdrant configuration: " + ", ".join(missing)
            )
        self.client = QdrantClient(
            url=app_settings.qdrant_url,
            api_key=app_settings.qdrant_api_key,
            timeout=app_settings.qdrant_timeout_seconds,
        )

    @property
    def collection_name(self) -> str:
        return self.settings.qdrant_collection

    def check_connection(self) -> list[str]:
        response = self.client.get_collections()
        return [item.name for item in response.collections]

    def ensure_collection(self, *, recreate: bool = False) -> None:
        exists = self.client.collection_exists(self.collection_name)
        if exists and recreate:
            self.client.delete_collection(self.collection_name)
            exists = False

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.settings.embedding_dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
        else:
            self._validate_collection_configuration()

        self.ensure_payload_indexes()

    def _validate_collection_configuration(self) -> None:
        info = self.client.get_collection(self.collection_name)
        vectors = info.config.params.vectors
        size = getattr(vectors, "size", None)
        distance = getattr(vectors, "distance", None)
        if size != self.settings.embedding_dimensions:
            raise RuntimeError(
                f"Existing collection has vector size {size}; expected "
                f"{self.settings.embedding_dimensions}. Use a new "
                "collection name or --recreate."
            )
        distance_name = str(distance).lower()
        if "cosine" not in distance_name:
            raise RuntimeError(
                f"Existing collection distance is {distance}; expected Cosine."
            )

    def ensure_payload_indexes(self) -> None:
        info = self.client.get_collection(self.collection_name)
        existing = set((info.payload_schema or {}).keys())
        for field_name, schema in PAYLOAD_INDEXES.items():
            if field_name in existing:
                continue
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=schema,
                wait=True,
            )

    def replace_sessions(self, session_ids: Iterable[str]) -> None:
        for session_id in sorted(set(session_ids)):
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="session_id",
                                match=models.MatchValue(value=session_id),
                            )
                        ]
                    )
                ),
                wait=True,
            )

    def upload_points(
        self,
        points: Iterable[models.PointStruct],
        *,
        batch_size: int = 64,
    ) -> None:
        point_list = list(points)
        for start in range(0, len(point_list), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=point_list[start : start + batch_size],
                wait=True,
            )

    def exact_count(
        self,
        query_filter: models.Filter | None = None,
    ) -> int:
        response = self.client.count(
            collection_name=self.collection_name,
            count_filter=query_filter,
            exact=True,
        )
        return int(response.count)

    def query(
        self,
        vector: list[float],
        *,
        query_filter: models.Filter,
        limit: int,
    ) -> tuple[SearchHit, ...]:
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return tuple(
            SearchHit(
                point_id=str(point.id),
                score=float(point.score),
                payload=dict(point.payload or {}),
            )
            for point in response.points
        )

    def scroll_all(
        self,
        *,
        query_filter: models.Filter,
        batch_size: int = 128,
    ) -> tuple[dict[str, Any], ...]:
        offset = None
        records: list[dict[str, Any]] = []
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            records.extend(
                {
                    "point_id": str(point.id),
                    **dict(point.payload or {}),
                }
                for point in points
            )
            if next_offset is None:
                break
            offset = next_offset
        return tuple(records)
