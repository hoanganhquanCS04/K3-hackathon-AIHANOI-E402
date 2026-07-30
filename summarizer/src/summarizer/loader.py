"""Lấy nội dung transcript đầy đủ và đúng thứ tự.

Đây là ranh giới giữa M2 và M1. Hai implementation cùng một interface:

- `LocalParserLoader` đọc thẳng file transcript qua parser của M1. Không cần
  Qdrant, không cần mạng — dùng cho test và cho build offline.
- `QdrantLoader` gọi structured reader của M1.

Quan trọng: KHÔNG có hàm nào ở đây dùng semantic search. Tóm tắt phải đọc đủ
100% chunk của phạm vi được hỏi (plan §3, §6). Top-k chỉ dùng để xác định phạm
vi, và việc đó nằm ở `scope.py`, không nằm ở đây.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from summarizer.schemas import Chunk, SectionRef, SessionRef


class ContentLoader(Protocol):
    def list_sessions(self) -> tuple[SessionRef, ...]: ...

    def get_session(self, session_id: str) -> SessionRef: ...

    def get_session_sections(self, session_id: str) -> tuple[SectionRef, ...]: ...

    def get_section_content(self, section_id: str) -> tuple[Chunk, ...]: ...

    def get_session_content(self, session_id: str) -> tuple[Chunk, ...]: ...


def section_content_hash(chunks: tuple[Chunk, ...]) -> str:
    """Hash nội dung canonical của một section.

    Đây là thành phần đầu tiên của khoá cache (plan §10.2). Bao gồm cả chunk_id
    chứ không chỉ text: nếu đoạn bị đánh số lại thì citation trong bản tóm tắt
    cũ không còn đúng, phải sinh lại.
    """

    canonical = "\n".join(f"{chunk.chunk_id}\t{chunk.text}" for chunk in chunks)
    canonical = canonical.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Local
# --------------------------------------------------------------------------


class LocalParserLoader:
    """Đọc transcript qua parser của M1, giữ kết quả trong bộ nhớ."""

    def __init__(self, transcript_dir=None) -> None:
        from vector_db.parser import parse_all_transcripts

        self._sessions: dict[str, SessionRef] = {}
        self._sections: dict[str, list[SectionRef]] = {}
        self._section_chunks: dict[str, tuple[Chunk, ...]] = {}
        self._session_chunks: dict[str, tuple[Chunk, ...]] = {}

        for parsed in parse_all_transcripts(transcript_dir):
            meta = parsed.metadata
            self._sessions[meta.session_id] = SessionRef(
                session_id=meta.session_id,
                session_title=meta.session_title,
                session_locator=meta.session_locator,
                session_day=meta.session_day,
                session_period=meta.session_period,
            )
            refs: list[SectionRef] = []
            session_chunks: list[Chunk] = []
            for section in parsed.sections:
                refs.append(
                    SectionRef(
                        section_id=section.section_id,
                        session_id=section.session_id,
                        section_title=section.section_title,
                        section_order=section.section_order,
                    )
                )
                chunks = tuple(
                    Chunk(
                        chunk_id=chunk.chunk_id,
                        session_id=chunk.session_id,
                        section_id=chunk.section_id,
                        section_title=chunk.section_title,
                        section_order=chunk.section_order,
                        chunk_order_in_section=chunk.chunk_order_in_section,
                        chunk_order_in_session=chunk.chunk_order_in_session,
                        text=chunk.text,
                        has_unclear=chunk.has_unclear,
                        is_activity=chunk.is_activity,
                        speaker_role=chunk.speaker_role,
                    )
                    for chunk in section.chunks
                )
                self._section_chunks[section.section_id] = chunks
                session_chunks.extend(chunks)

            self._sections[meta.session_id] = refs
            self._session_chunks[meta.session_id] = tuple(session_chunks)

    def list_sessions(self) -> tuple[SessionRef, ...]:
        return tuple(self._sessions[key] for key in sorted(self._sessions))

    def get_session(self, session_id: str) -> SessionRef:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Unknown session_id: {session_id}") from None

    def get_session_sections(self, session_id: str) -> tuple[SectionRef, ...]:
        self.get_session(session_id)
        return tuple(sorted(self._sections[session_id], key=lambda ref: ref.section_order))

    def get_section_content(self, section_id: str) -> tuple[Chunk, ...]:
        try:
            return self._section_chunks[section_id]
        except KeyError:
            raise KeyError(f"Unknown section_id: {section_id}") from None

    def get_session_content(self, session_id: str) -> tuple[Chunk, ...]:
        self.get_session(session_id)
        return self._session_chunks[session_id]


# --------------------------------------------------------------------------
# Qdrant
# --------------------------------------------------------------------------


def _chunk_from_payload(payload: dict) -> Chunk:
    return Chunk(
        chunk_id=payload["chunk_id"],
        session_id=payload["session_id"],
        section_id=payload["section_id"],
        section_title=payload["section_title"],
        section_order=payload["section_order"],
        chunk_order_in_section=payload["chunk_order_in_section"],
        chunk_order_in_session=payload["chunk_order_in_session"],
        text=payload["text"],
        has_unclear=payload["has_unclear"],
        is_activity=payload["is_activity"],
        speaker_role=payload["speaker_role"],
    )


class QdrantLoader:
    """Gọi structured reader của M1 (`vector_db.session_reader`)."""

    def __init__(self) -> None:
        from vector_db import session_reader

        self._reader = session_reader

    def list_sessions(self) -> tuple[SessionRef, ...]:
        # Không có API liệt kê session trong M1, nên đi qua TOC point.
        from qdrant_client import models as qmodels
        from vector_db.qdrant_store import QdrantStore

        records = QdrantStore().scroll_all(
            query_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="point_type",
                        match=qmodels.MatchValue(value="session_toc"),
                    )
                ]
            )
        )
        refs = [
            SessionRef(
                session_id=item["session_id"],
                session_title=item["session_title"],
                session_locator=item["session_locator"],
                session_day=item.get("session_day"),
                session_period=item["session_period"],
            )
            for item in records
        ]
        return tuple(sorted(refs, key=lambda ref: ref.session_id))

    def get_session(self, session_id: str) -> SessionRef:
        outline = self._reader.get_session_outline(session_id)
        return SessionRef(
            session_id=outline["session_id"],
            session_title=outline["session_title"],
            session_locator=outline["session_locator"],
            session_day=outline.get("session_day"),
            session_period=outline["session_period"],
        )

    def get_session_sections(self, session_id: str) -> tuple[SectionRef, ...]:
        records = self._reader.get_session_sections(session_id)
        if not records:
            raise KeyError(f"Unknown session_id: {session_id}")
        return tuple(
            SectionRef(
                section_id=item["section_id"],
                session_id=item["session_id"],
                section_title=item["section_title"],
                section_order=item["section_order"],
            )
            for item in records
        )

    def get_section_content(self, section_id: str) -> tuple[Chunk, ...]:
        records = self._reader.get_section_content(section_id)
        if not records:
            raise KeyError(f"Unknown section_id: {section_id}")
        return tuple(_chunk_from_payload(item) for item in records)

    def get_session_content(self, session_id: str) -> tuple[Chunk, ...]:
        records = self._reader.get_session_content(session_id)
        if not records:
            raise KeyError(f"Unknown session_id: {session_id}")
        return tuple(_chunk_from_payload(item) for item in records)


def get_loader(backend: str | None = None) -> ContentLoader:
    from summarizer.config import settings

    choice = (backend or settings.loader_backend).lower()
    if choice == "local":
        return LocalParserLoader()
    if choice == "qdrant":
        return QdrantLoader()
    raise ValueError(f"Unknown loader backend: {choice}")
