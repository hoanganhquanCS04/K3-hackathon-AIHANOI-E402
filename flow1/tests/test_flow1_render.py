"""Test render.py. Chủ: M2 → giao M4 khi ghép giao diện."""

from flow1.ask import Result
from flow1.models import Claim, Drop, Intent, Seg, Verdict
from flow1.render import render


def seg(code, text, *, speaker="instructor", has_gap=False):
    return Seg(
        code=code, session="03", session_title="Buổi 03 — Soi bài toán",
        locate_confidence="vừa", section_idx=1, section_title="RAG và tool calling",
        order=1, text=text, speaker=speaker,
        has_gap=has_gap, is_activity=False, n_chars=len(text),
    )


SEGS = [
    seg("T03-002", "RAG là retrieval augmented generation."),
    seg("T03-003", "Tool calling [không nghe rõ] gọi hàm ngoài.", has_gap=True),
    seg("T03-004", "[Học viên]: Em nghĩ RAG khác fine-tune ạ.", speaker="student"),
    seg("T03-005", "**[Học viên]:** Em bổ sung ạ.", speaker="student"),
]


def answered(claims, **kw):
    return Result(
        outcome="answered", question="RAG là gì", message="",
        intent=Intent(label="nội_dung_khoá", reason="test"),
        verdict=Verdict(status="answered", claims=claims, **kw),
    )


# --- Đường happy ---------------------------------------------------------

def test_renders_the_claim_text():
    out = render(answered([Claim(text="RAG nạp thêm ngữ cảnh.", cite=["T03-002"],
                                speaker="instructor")]), SEGS)
    assert "RAG nạp thêm ngữ cảnh." in out


def test_renders_the_citation_code():
    out = render(answered([Claim(text="A.", cite=["T03-002"], speaker="instructor")]), SEGS)
    assert "T03-002" in out


def test_quotes_the_source_segment_so_the_reader_checks_without_leaving_the_page():
    out = render(answered([Claim(text="A.", cite=["T03-002"], speaker="instructor")]), SEGS)
    assert "RAG là retrieval augmented generation." in out


def test_numbers_multiple_claims():
    out = render(answered([
        Claim(text="Ý một.", cite=["T03-002"], speaker="instructor"),
        Claim(text="Ý hai.", cite=["T03-003"], speaker="instructor"),
    ]), SEGS)
    assert "1." in out and "2." in out


def test_states_the_session_so_the_citation_is_traceable():
    out = render(answered([Claim(text="A.", cite=["T03-002"], speaker="instructor")]), SEGS)
    assert "Buổi 03" in out


# --- Lớp ④: nhãn giọng học viên ----------------------------------------

def test_a_student_citation_is_labelled_in_the_output():
    out = render(answered(
        [Claim(text="RAG khác fine-tune.", cite=["T03-004"], speaker="student")],
        student_codes=["T03-004"],
    ), SEGS)
    assert "học viên nêu" in out


def test_a_bold_marker_student_citation_is_labelled_the_same_way():
    out = render(answered(
        [Claim(text="Một ý.", cite=["T03-005"], speaker="instructor")],
        student_codes=["T03-005"],
    ), SEGS)
    assert "học viên nêu" in out


def test_a_plain_instructor_citation_gets_no_voice_label():
    out = render(answered([Claim(text="A.", cite=["T03-002"], speaker="instructor")]), SEGS)
    assert "học viên" not in out


# --- Lớp ①: cờ bản ghi thiếu -------------------------------------------

def test_a_gapped_citation_prints_the_warning():
    out = render(answered(
        [Claim(text="Tool calling gọi hàm ngoài.", cite=["T03-003"], speaker="instructor")],
        gap_codes=["T03-003"],
    ), SEGS)
    assert "bản ghi" in out and "thiếu" in out


def test_a_clean_citation_prints_no_gap_warning():
    out = render(answered([Claim(text="A.", cite=["T03-002"], speaker="instructor")]), SEGS)
    assert "bản ghi" not in out


# --- Minh bạch: ý bị loại KHÔNG được giấu -----------------------------

def test_dropped_claims_are_reported_not_hidden():
    result = Result(
        outcome="insufficient", question="q", message="",
        verdict=Verdict(status="insufficient", claims=[], drops=[
            Drop(claim_text="Điều bịa.", kind="unknown_code",
                 detail="Trích mã T03-777 — mã này không có trong transcript."),
        ]),
    )
    out = render(result, SEGS)
    assert "T03-777" in out
    assert "bị loại" in out.lower() or "đã loại" in out.lower()


def test_the_dropped_section_names_the_reason_kind():
    result = Result(
        outcome="insufficient", question="q", message="",
        verdict=Verdict(status="insufficient", claims=[], drops=[
            Drop(claim_text="x", kind="outside_context", detail="ngoài context"),
        ]),
    )
    assert "outside_context" in render(result, SEGS)


def test_an_insufficient_result_says_so_plainly_instead_of_going_silent():
    result = Result(outcome="insufficient", question="q", message="",
                    verdict=Verdict(status="insufficient", claims=[]))
    out = render(result, SEGS)
    assert out.strip(), "không được trả về chuỗi rỗng"
    assert "không đủ" in out.lower()


# --- Các outcome không có verdict ------------------------------------

def test_a_refused_result_prints_the_gate_one_message():
    result = Result(outcome="refused", question="q",
                    message="Nội dung này không có trong 6 buổi mình có bản ghi.")
    assert "6 buổi" in render(result, SEGS)


def test_a_clarify_result_prints_the_question_back_to_the_user():
    result = Result(outcome="clarify", question="q",
                    message="Chủ đề này có ở cả buổi 02 và buổi 05 — bạn hỏi buổi nào?")
    assert "buổi nào" in render(result, SEGS)


def test_an_off_topic_result_prints_the_template():
    result = Result(outcome="off_topic", question="q", message="Câu này ngoài phạm vi.")
    assert "ngoài phạm vi" in render(result, SEGS)


def test_an_error_result_prints_the_error_and_no_answer():
    result = Result(outcome="error", question="q",
                    message="Không gọi được model, nên mình không trả lời: timeout")
    out = render(result, SEGS)
    assert "không trả lời" in out


def test_render_never_crashes_on_a_citation_whose_segment_is_missing():
    out = render(answered([Claim(text="A.", cite=["T03-999"], speaker="instructor")]), SEGS)
    assert "T03-999" in out
