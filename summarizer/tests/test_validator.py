"""Validator phải bắt được mọi kiểu 'summary bịa'. Không cần API key."""

from __future__ import annotations

import pytest

from summarizer.schemas import (
    CitedItemDraft,
    OutlineItemDraft,
    SectionSummaryDraft,
    SessionKeyPointDraft,
    SessionSummaryDraft,
)
from summarizer.validator import (
    ValidationError,
    build_section_summary,
    build_session_summary,
)


def draft(**overrides) -> SectionSummaryDraft:
    base = {
        "abstract": "Giới hạn của LLM và cách bù bằng tool calling.",
        "key_points": [
            CitedItemDraft(text="LLM không truy cập dữ liệu mới.", citations=["T03-034"])
        ],
        "concepts": ["tool calling", "RAG"],
        "examples": [],
        "student_questions": [],
    }
    base.update(overrides)
    return SectionSummaryDraft(**base)


def build(section, chunks, **overrides):
    return build_section_summary(
        draft(**overrides),
        section=section,
        chunks=chunks,
        content_hash="hash",
        prompt_version="v1",
        model="fake",
    )


# --- ca hợp lệ ---------------------------------------------------------------


def test_valid_draft_passes(section, chunks):
    summary, report = build(section, chunks)
    assert report.ok
    assert summary.covered_chunk_ids == ("T03-034",)
    assert summary.source_chunk_ids == ("T03-034", "T03-035", "T03-036")


def test_derived_fields_come_from_chunks_not_llm(section, chunks):
    from tests.conftest import make_chunk

    noisy = chunks + (
        make_chunk("T03-037", "[không nghe rõ]", order_in_section=4, has_unclear=True),
        make_chunk("T03-038", "[Hoạt động lớp: chia nhóm]", order_in_section=5, is_activity=True),
    )
    summary, _ = build(section, noisy)
    assert summary.has_unclear is True
    assert summary.unclear_chunk_ids == ("T03-037",)
    assert summary.activity_chunk_ids == ("T03-038",)


# --- ca bịa ------------------------------------------------------------------


def test_cross_session_citation_is_an_error(section, chunks):
    with pytest.raises(ValidationError) as excinfo:
        build(
            section,
            chunks,
            key_points=[CitedItemDraft(text="Ý lấy từ buổi khác.", citations=["T05-012"])],
        )
    assert "thuộc buổi T05" in str(excinfo.value)


def test_citation_outside_section_is_dropped(section, chunks):
    summary, report = build(
        section,
        chunks,
        key_points=[
            CitedItemDraft(text="Ý hợp lệ.", citations=["T03-034", "T03-999"]),
        ],
    )
    assert summary.key_points[0].citations == ("T03-034",)
    assert any("T03-999" in warning for warning in report.warnings)


def test_malformed_citation_is_dropped(section, chunks):
    summary, report = build(
        section,
        chunks,
        key_points=[
            CitedItemDraft(text="Ý hợp lệ.", citations=["đoạn 34", "T03-034"]),
        ],
    )
    assert summary.key_points[0].citations == ("T03-034",)
    assert any("sai định dạng" in warning for warning in report.warnings)


def test_item_without_any_valid_citation_is_removed(section, chunks):
    with pytest.raises(ValidationError) as excinfo:
        build(
            section,
            chunks,
            key_points=[CitedItemDraft(text="Ý không có nguồn.", citations=[])],
        )
    assert "không còn key_point hợp lệ" in str(excinfo.value)


def test_empty_abstract_is_an_error(section, chunks):
    with pytest.raises(ValidationError):
        build(section, chunks, abstract="   ")


def test_student_question_not_pointing_at_student_warns(section, chunks):
    _, report = build(
        section,
        chunks,
        student_questions=[
            CitedItemDraft(text="Câu hỏi giả.", citations=["T03-034"]),
        ],
    )
    assert any("không trỏ vào lời học viên" in warning for warning in report.warnings)


def test_duplicate_citations_are_deduped(section, chunks):
    summary, _ = build(
        section,
        chunks,
        key_points=[
            CitedItemDraft(text="Ý.", citations=["T03-034", "T03-034", "T03-035"]),
        ],
    )
    assert summary.key_points[0].citations == ("T03-034", "T03-035")


# --- session -----------------------------------------------------------------


@pytest.fixture
def two_sections(section, chunks):
    from summarizer.schemas import SectionRef
    from tests.conftest import make_chunk

    second = SectionRef(
        section_id="T03-SEC-005",
        session_id="T03",
        section_title="Chọn dự án",
        section_order=5,
    )
    second_chunks = (
        make_chunk("T03-040", "Chọn dự án theo giá trị cạnh tranh.", section_id="T03-SEC-005",
                   section_order=5, order_in_section=1, order_in_session=40),
    )
    first, _ = build(section, chunks)
    second_summary, _ = build_section_summary(
        SectionSummaryDraft(
            abstract="Cách chọn dự án.",
            key_points=[CitedItemDraft(text="Chọn theo giá trị.", citations=["T03-040"])],
            concepts=[],
            examples=[],
            student_questions=[],
        ),
        section=second,
        chunks=second_chunks,
        content_hash="hash2",
        prompt_version="v1",
        model="fake",
    )
    return (
        (section, second),
        (first, second_summary),
        chunks + second_chunks,
    )


def session_draft(**overrides) -> SessionSummaryDraft:
    base = {
        "tldr": "Buổi nói về giới hạn LLM và cách chọn dự án.",
        "key_points": [
            SessionKeyPointDraft(
                text="LLM không truy cập dữ liệu mới.",
                citations=["T03-034"],
                section_id="T03-SEC-004",
            )
        ],
        "outline": [
            OutlineItemDraft(
                section_id="T03-SEC-004",
                abstract="Giới hạn của LLM.",
                citations=["T03-034"],
            ),
            OutlineItemDraft(
                section_id="T03-SEC-005",
                abstract="Chọn dự án.",
                citations=["T03-040"],
            ),
        ],
        "concepts": ["RAG"],
        "open_questions": [],
    }
    base.update(overrides)
    return SessionSummaryDraft(**base)


def build_session(session, two_sections, **overrides):
    sections, summaries, chunks = two_sections
    return build_session_summary(
        session_draft(**overrides),
        session=session,
        sections=sections,
        section_summaries=summaries,
        chunks=chunks,
        prompt_version="v1",
        model_map="fake-map",
        model_reduce="fake-reduce",
    )


def test_session_outline_covers_every_section(session, two_sections):
    summary, report = build_session(session, two_sections)
    assert report.ok
    assert [item.section_id for item in summary.outline] == [
        "T03-SEC-004",
        "T03-SEC-005",
    ]
    assert summary.coverage.covered_sections == summary.coverage.total_sections == 2
    assert summary.coverage.total_chunks == 4


def test_missing_section_is_repaired_from_map_output(session, two_sections):
    summary, report = build_session(
        session,
        two_sections,
        outline=[
            OutlineItemDraft(
                section_id="T03-SEC-004",
                abstract="Giới hạn của LLM.",
                citations=["T03-034"],
            )
        ],
    )
    assert len(summary.outline) == 2
    assert summary.outline[1].abstract == "Cách chọn dự án."
    assert any("thiếu T03-SEC-005" in warning for warning in report.warnings)


def test_unknown_section_id_is_an_error(session, two_sections):
    with pytest.raises(ValidationError) as excinfo:
        build_session(
            session,
            two_sections,
            outline=[
                OutlineItemDraft(
                    section_id="T03-SEC-099",
                    abstract="Mục không tồn tại.",
                    citations=["T03-034"],
                )
            ],
        )
    assert "không tồn tại trong buổi" in str(excinfo.value)


def test_session_outline_is_reordered_by_section_order(session, two_sections):
    summary, _ = build_session(
        session,
        two_sections,
        outline=[
            OutlineItemDraft(
                section_id="T03-SEC-005", abstract="Chọn dự án.", citations=["T03-040"]
            ),
            OutlineItemDraft(
                section_id="T03-SEC-004", abstract="Giới hạn LLM.", citations=["T03-034"]
            ),
        ],
    )
    assert [item.section_order for item in summary.outline] == [4, 5]


def test_session_cross_session_citation_is_an_error(session, two_sections):
    with pytest.raises(ValidationError):
        build_session(
            session,
            two_sections,
            key_points=[
                SessionKeyPointDraft(
                    text="Ý lạ.", citations=["T01-001"], section_id="T03-SEC-004"
                )
            ],
        )


def test_uncited_but_real_chunk_is_tolerated_with_warning(session, two_sections):
    summary, report = build_session(
        session,
        two_sections,
        key_points=[
            SessionKeyPointDraft(
                text="Ý trỏ vào đoạn có thật nhưng section summary chưa trích.",
                citations=["T03-035"],
                section_id="T03-SEC-004",
            )
        ],
    )
    assert summary.key_points[0].citations == ("T03-035",)
    assert any("không có trong section summary nguồn" in w for w in report.warnings)
