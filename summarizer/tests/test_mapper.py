"""Mapper: cache, hoạt động lớp, và việc prompt mang đúng thông tin. LLM là giả."""

from __future__ import annotations

from summarizer.cache import SummaryCache
from summarizer.mapper import summarize_section, summarize_sections
from summarizer.schemas import CitedItemDraft, SectionSummaryDraft
from tests.conftest import FakeLLM, make_chunk

DRAFT = SectionSummaryDraft(
    abstract="Giới hạn của LLM.",
    key_points=[CitedItemDraft(text="LLM không truy cập dữ liệu mới.", citations=["T03-034"])],
    concepts=["RAG"],
    examples=[],
    student_questions=[
        CitedItemDraft(text="RAG có thay được fine-tuning không?", citations=["T03-036"])
    ],
)


def run(tmp_path, session, section, chunks, llm=None, **kwargs):
    return summarize_section(
        session=session,
        section=section,
        chunks=chunks,
        total_sections=19,
        llm=llm or FakeLLM(DRAFT),
        cache=SummaryCache(tmp_path),
        model="fake-model",
        **kwargs,
    )


def test_first_run_calls_llm_and_caches(tmp_path, session, section, chunks):
    llm = FakeLLM(DRAFT)
    result = run(tmp_path, session, section, chunks, llm)

    assert llm.calls == 1
    assert result.cache_hit is False
    assert result.summary.section_id == "T03-SEC-004"
    assert SummaryCache(tmp_path).count() == 1


def test_second_run_is_a_cache_hit_with_no_llm_call(tmp_path, session, section, chunks):
    run(tmp_path, session, section, chunks, FakeLLM(DRAFT))

    llm = FakeLLM()  # hết draft: bị gọi là AssertionError
    result = run(tmp_path, session, section, chunks, llm)

    assert llm.calls == 0
    assert result.cache_hit is True
    assert result.summary.abstract == "Giới hạn của LLM."


def test_force_bypasses_cache(tmp_path, session, section, chunks):
    run(tmp_path, session, section, chunks, FakeLLM(DRAFT))
    llm = FakeLLM(DRAFT)
    result = run(tmp_path, session, section, chunks, llm, force=True)
    assert llm.calls == 1
    assert result.cache_hit is False


def test_changing_content_invalidates_cache(tmp_path, session, section, chunks):
    run(tmp_path, session, section, chunks, FakeLLM(DRAFT))
    edited = chunks[:-1] + (
        make_chunk("T03-036", "Nội dung đã sửa.", order_in_section=3, speaker_role="student"),
    )
    llm = FakeLLM(DRAFT)
    run(tmp_path, session, section, edited, llm)
    assert llm.calls == 1


def test_activity_chunks_are_excluded_from_the_prompt(tmp_path, session, section, chunks):
    with_activity = chunks + (
        make_chunk(
            "T03-037",
            "[Hoạt động lớp: chia nhóm thảo luận]",
            order_in_section=4,
            is_activity=True,
        ),
    )
    llm = FakeLLM(DRAFT)
    result = run(tmp_path, session, section, with_activity, llm)

    assert "T03-037" not in llm.last_user
    # Vẫn đếm vào coverage: đã đọc, chỉ là không đưa vào nội dung kiến thức.
    assert "T03-037" in result.summary.source_chunk_ids
    assert result.summary.activity_chunk_ids == ("T03-037",)


def test_activity_only_section_skips_the_llm(tmp_path, session, section):
    only_activity = (
        make_chunk("T03-050", "[Hoạt động lớp: nghỉ giải lao]", is_activity=True),
    )
    llm = FakeLLM()
    result = run(tmp_path, session, section, only_activity, llm)

    assert llm.calls == 0
    assert "hoạt động lớp" in result.summary.abstract.lower()


def test_prompt_carries_speaker_role_and_valid_ids(tmp_path, session, section, chunks):
    llm = FakeLLM(DRAFT)
    run(tmp_path, session, section, chunks, llm)

    assert "(giảng viên)" in llm.last_user
    assert "(học viên)" in llm.last_user
    assert "MÃ TRÍCH DẪN HỢP LỆ: T03-034, T03-035, T03-036" in llm.last_user
    assert "MỤC 4/19" in llm.last_user


def test_batch_preserves_section_order(tmp_path, session, section, chunks):
    from summarizer.schemas import SectionRef

    second = SectionRef(
        section_id="T03-SEC-005",
        session_id="T03",
        section_title="Chọn dự án",
        section_order=5,
    )
    second_chunks = (
        make_chunk(
            "T03-040",
            "Chọn dự án theo giá trị.",
            section_id="T03-SEC-005",
            section_order=5,
            order_in_session=40,
        ),
    )
    second_draft = SectionSummaryDraft(
        abstract="Chọn dự án.",
        key_points=[CitedItemDraft(text="Chọn theo giá trị.", citations=["T03-040"])],
        concepts=[],
        examples=[],
        student_questions=[],
    )

    results = summarize_sections(
        session=session,
        sections=(section, second),
        chunks_by_section={
            "T03-SEC-004": chunks,
            "T03-SEC-005": second_chunks,
        },
        llm=FakeLLM(DRAFT, second_draft),
        cache=SummaryCache(tmp_path),
        model="fake-model",
        max_workers=1,
    )

    assert [result.summary.section_id for result in results] == [
        "T03-SEC-004",
        "T03-SEC-005",
    ]
