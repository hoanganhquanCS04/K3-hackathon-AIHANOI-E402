"""Typed source records, payloads, and API responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PointType = Literal["atomic_chunk", "section_parent", "session_toc"]


class FrozenModel(BaseModel):
    """Immutable base model so parsed source records cannot drift."""

    model_config = ConfigDict(frozen=True)


class SessionMetadata(FrozenModel):
    session_id: str
    session_order: int
    session_day: int | None
    session_period: str
    session_title: str
    session_locator: str
    location_confidence: str
    source_file: str
    source_hash: str


class AtomicChunk(FrozenModel):
    chunk_id: str
    citation_id: str
    session_id: str
    section_id: str
    section_title: str
    section_order: int
    chunk_order_in_session: int
    chunk_order_in_section: int
    text: str
    has_unclear: bool
    is_activity: bool
    speaker_role: str
    content_type: str
    content_hash: str


class Section(FrozenModel):
    section_id: str
    session_id: str
    section_title: str
    section_order: int
    chunks: tuple[AtomicChunk, ...]


class ParsedSession(FrozenModel):
    metadata: SessionMetadata
    sections: tuple[Section, ...]

    @property
    def chunks(self) -> tuple[AtomicChunk, ...]:
        return tuple(chunk for section in self.sections for chunk in section.chunks)


class PointDraft(FrozenModel):
    logical_id: str
    point_type: PointType
    payload: dict[str, Any]
    embedding_text: str | None = None
    child_chunk_ids: tuple[str, ...] = ()


class SearchHit(FrozenModel):
    point_id: str
    score: float
    payload: dict[str, Any]


class RetrievalResponse(FrozenModel):
    status: Literal["ok", "needs_clarification", "no_evidence"]
    hits: tuple[SearchHit, ...] = ()
    reason: str | None = None
    candidate_sessions: tuple[dict[str, Any], ...] = ()


class BuildSummary(FrozenModel):
    collection_name: str
    atomic_chunk_count: int
    section_parent_count: int
    session_toc_count: int
    total_point_count: int
    exact_collection_count: int | None = None
    manifest_path: str | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)
