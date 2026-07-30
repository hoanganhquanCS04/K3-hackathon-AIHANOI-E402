from __future__ import annotations

import pytest

from summarizer.schemas import Chunk, SectionRef, SessionRef


def make_chunk(
    chunk_id: str,
    text: str = "Nội dung mẫu.",
    *,
    section_id: str = "T03-SEC-004",
    section_order: int = 4,
    order_in_section: int = 1,
    order_in_session: int = 34,
    speaker_role: str = "instructor",
    has_unclear: bool = False,
    is_activity: bool = False,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        session_id=chunk_id.split("-", 1)[0],
        section_id=section_id,
        section_title="Giới hạn của LLM, tool calling và RAG",
        section_order=section_order,
        chunk_order_in_section=order_in_section,
        chunk_order_in_session=order_in_session,
        text=text,
        has_unclear=has_unclear,
        is_activity=is_activity,
        speaker_role=speaker_role,
    )


@pytest.fixture
def section() -> SectionRef:
    return SectionRef(
        section_id="T03-SEC-004",
        session_id="T03",
        section_title="Giới hạn của LLM, tool calling và RAG",
        section_order=4,
    )


@pytest.fixture
def session() -> SessionRef:
    return SessionRef(
        session_id="T03",
        session_title="Soi bài toán các nhóm",
        session_locator="Day 2 (chiều) — Soi bài toán các nhóm",
        session_day=2,
        session_period="chiều",
    )


@pytest.fixture
def chunks() -> tuple[Chunk, ...]:
    return (
        make_chunk("T03-034", "LLM không truy cập được dữ liệu mới.", order_in_section=1),
        make_chunk("T03-035", "Tool calling để gọi hệ thống ngoài.", order_in_section=2),
        make_chunk(
            "T03-036",
            "[học viên]: RAG có thay được fine-tuning không?",
            order_in_section=3,
            speaker_role="student",
        ),
    )


class FakeLLM:
    """LLM giả: trả về draft đã dựng sẵn, đếm số lần được gọi."""

    def __init__(self, *drafts) -> None:
        self.drafts = list(drafts)
        self.calls = 0
        self.last_user: str | None = None

    def parse(self, *, model, system, user, schema, temperature):
        self.calls += 1
        self.last_user = user
        if not self.drafts:
            raise AssertionError("FakeLLM hết draft nhưng vẫn bị gọi")
        draft = self.drafts.pop(0) if len(self.drafts) > 1 else self.drafts[0]
        return draft
