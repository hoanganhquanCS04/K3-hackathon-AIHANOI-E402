"""Deterministic parser for the supplied clean Markdown transcripts."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from vector_db.config import REPOSITORY_ROOT, settings
from vector_db.models import (
    AtomicChunk,
    ParsedSession,
    Section,
    SessionMetadata,
)

FILE_PATTERN = re.compile(r"^transcript-(\d{2})-clean\.md$")
CHUNK_PATTERN = re.compile(r"^\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*)$")
H1_PATTERN = re.compile(r"^#\s+(.+)$")
H2_PATTERN = re.compile(r"^##\s+(.+)$")
DAY_PATTERN = re.compile(r"\bDay\s+(\d+)\b", re.IGNORECASE)
PERIOD_PATTERN = re.compile(r"\b(sáng|chiều)\b", re.IGNORECASE)
CONFIDENCE_PATTERN = re.compile(
    r"độ tin cậy:\s*(cao|vừa|thấp)",
    re.IGNORECASE,
)


def sha256_text(text: str) -> str:
    """Hash canonical UTF-8 text."""

    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_has_unclear(text: str) -> bool:
    return "[không nghe rõ]" in text.lower()


def detect_is_activity(text: str) -> bool:
    return text.lstrip().lower().startswith("[hoạt động lớp:")


def detect_speaker_role(text: str, *, is_activity: bool) -> str:
    normalized = text.lstrip().lower()
    if is_activity:
        return "activity"
    if normalized.startswith("[học viên]:"):
        return "student"
    if normalized.startswith("[ta]"):
        return "teaching_assistant"
    if normalized.startswith("[khách mời]"):
        return "guest"
    return "instructor"


def detect_content_type(
    speaker_role: str,
    *,
    is_activity: bool,
) -> str:
    if is_activity:
        return "activity"
    if speaker_role == "student":
        return "student_speech"
    if speaker_role == "teaching_assistant":
        return "teaching_assistant"
    if speaker_role == "guest":
        return "guest_speech"
    return "lecture"


def _clean_session_locator(first_heading: str) -> str:
    prefix = "Transcript bài giảng (bản sạch) — "
    if first_heading.startswith(prefix):
        return first_heading[len(prefix) :].strip()
    return first_heading.strip()


def _session_title(locator: str) -> str:
    title = re.sub(
        r"^Day\s+\d+(?:\s*\([^)]+\))?\s*—\s*",
        "",
        locator,
        flags=re.IGNORECASE,
    ).strip()
    return title or locator


def _finalize_chunk(
    *,
    chunk_id: str,
    text_parts: list[str],
    session_id: str,
    section_id: str,
    section_title: str,
    section_order: int,
    session_order: int,
    section_chunk_count: int,
) -> AtomicChunk:
    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError(f"Empty transcript chunk: {chunk_id}")
    is_activity = detect_is_activity(text)
    speaker_role = detect_speaker_role(text, is_activity=is_activity)
    return AtomicChunk(
        chunk_id=chunk_id,
        citation_id=chunk_id,
        session_id=session_id,
        section_id=section_id,
        section_title=section_title,
        section_order=section_order,
        chunk_order_in_session=session_order,
        chunk_order_in_section=section_chunk_count,
        text=text,
        has_unclear=detect_has_unclear(text),
        is_activity=is_activity,
        speaker_role=speaker_role,
        content_type=detect_content_type(
            speaker_role,
            is_activity=is_activity,
        ),
        content_hash=sha256_text(text),
    )


def parse_transcript(path: Path) -> ParsedSession:
    """Parse one clean Markdown transcript."""

    match = FILE_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Unsupported transcript filename: {path.name}")

    session_number = int(match.group(1))
    session_id = f"T{session_number:02d}"
    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    first_heading = next(
        (
            heading.group(1).strip()
            for line in lines
            if (heading := H1_PATTERN.match(line))
        ),
        None,
    )
    if first_heading is None:
        raise ValueError(f"Missing level-one heading: {path.name}")

    locator = _clean_session_locator(first_heading)
    header_text = "\n".join(lines[:8])
    day_match = DAY_PATTERN.search(header_text)
    period_match = PERIOD_PATTERN.search(header_text)
    confidence_match = CONFIDENCE_PATTERN.search(header_text)

    metadata = SessionMetadata(
        session_id=session_id,
        session_order=session_number,
        session_day=int(day_match.group(1)) if day_match else None,
        session_period=(
            period_match.group(1).lower() if period_match else "không xác định"
        ),
        session_title=_session_title(locator),
        session_locator=locator,
        location_confidence=(
            confidence_match.group(1).lower() if confidence_match else "không xác định"
        ),
        source_file=str(path.resolve().relative_to(REPOSITORY_ROOT)).replace("\\", "/"),
        source_hash=sha256_text(raw_text),
    )

    built_sections: list[Section] = []
    current_section_title: str | None = None
    current_section_order = 0
    current_section_chunks: list[AtomicChunk] = []
    current_chunk_id: str | None = None
    current_chunk_parts: list[str] = []
    session_chunk_order = 0

    def flush_chunk() -> None:
        nonlocal current_chunk_id
        nonlocal current_chunk_parts
        nonlocal session_chunk_order
        if current_chunk_id is None:
            return
        if current_section_title is None:
            raise ValueError(f"{current_chunk_id} occurs before a section heading")
        session_chunk_order += 1
        current_section_chunks.append(
            _finalize_chunk(
                chunk_id=current_chunk_id,
                text_parts=current_chunk_parts,
                session_id=session_id,
                section_id=(f"{session_id}-SEC-{current_section_order:03d}"),
                section_title=current_section_title,
                section_order=current_section_order,
                session_order=session_chunk_order,
                section_chunk_count=len(current_section_chunks) + 1,
            )
        )
        current_chunk_id = None
        current_chunk_parts = []

    def flush_section() -> None:
        nonlocal current_section_chunks
        if current_section_title is None:
            return
        flush_chunk()
        if not current_section_chunks:
            raise ValueError(
                f"Section has no chunks in {path.name}: {current_section_title}"
            )
        built_sections.append(
            Section(
                section_id=(f"{session_id}-SEC-{current_section_order:03d}"),
                session_id=session_id,
                section_title=current_section_title,
                section_order=current_section_order,
                chunks=tuple(current_section_chunks),
            )
        )
        current_section_chunks = []

    for line in lines:
        if H1_PATTERN.match(line):
            flush_chunk()
            continue

        section_match = H2_PATTERN.match(line)
        if section_match:
            flush_section()
            current_section_order += 1
            current_section_title = section_match.group(1).strip()
            continue

        chunk_match = CHUNK_PATTERN.match(line)
        if chunk_match:
            flush_chunk()
            current_chunk_id = chunk_match.group(1)
            current_chunk_parts = [chunk_match.group(2).strip()]
            continue

        if current_chunk_id is not None and (line.strip() or current_chunk_parts[-1:]):
            # Preserve explicit paragraph boundaries inside a chunk while
            # avoiding trailing blank lines.
            current_chunk_parts.append(line.rstrip())

    flush_section()

    if not built_sections:
        raise ValueError(f"No sections parsed from {path.name}")

    return ParsedSession(
        metadata=metadata,
        sections=tuple(built_sections),
    )


def parse_all_transcripts(
    transcript_dir: Path | None = None,
) -> tuple[ParsedSession, ...]:
    """Parse every supplied clean transcript in stable filename order."""

    directory = transcript_dir or settings.transcript_dir
    paths = sorted(directory.glob("transcript-*-clean.md"))
    if not paths:
        raise FileNotFoundError(f"No clean transcript files found in {directory}")
    return tuple(parse_transcript(path) for path in paths)
