"""Test parse.py của luồng 1. Chủ: M1 (khối B)."""

import pytest

from flow1.parse import (
    SESSIONS,
    STUDENT_MARKER,
    TRANSCRIPT_DIR,
    content_segs,
    parse_all,
    parse_session,
    parse_text,
)

# Mẫu dựng tay: có front matter (chứa "[không nghe rõ]" như CHÚ GIẢI, không phải chỗ
# khuyết thật), 2 section, đoạn hoạt động lớp, và CẢ HAI dạng marker học viên —
# "[Học viên]:" trần lẫn "**[Học viên]:**" in đậm. Cộng tên ẩn danh chữ thường
# "[học viên]" phải bị bỏ qua, và tiền tố "**Giảng viên:**".
SAMPLE = (
    "# Transcript bài giảng (bản sạch) — Day 9 — Buổi thử\r\n"
    "\r\n"
    "> **Nguồn:** `transcript_2/09.md` · **Định vị buổi:** Day 9 — Buổi thử — độ tin cậy: vừa\r\n"
    "> **Quy ước:** `[Txx-NNN]` mã đoạn · `[không nghe rõ]` chỗ không khôi phục được\r\n"
    "\r\n"
    "## Mở đầu\r\n"
    "\r\n"
    "**[T09-001]** [Hoạt động lớp: ổn định lớp, bật ghi hình.]\r\n"
    "\r\n"
    "**[T09-002]** Mình bắt đầu bằng một câu hỏi.\r\n"
    "\r\n"
    "**[T09-003]** Chỗ này [không nghe rõ] nên mình bỏ qua.\r\n"
    "\r\n"
    "## Phần hai\r\n"
    "\r\n"
    "**[T09-004]** [Học viên]: Em nghĩ product khác project ạ.\r\n"
    "\r\n"
    "**[T09-005]** **[Học viên]:** Em bổ sung thêm ạ.\r\n"
    "\r\n"
    "**[T09-006]** Bạn [học viên] vừa nói rất đúng.\r\n"
    "\r\n"
    "**[T09-007]** **Giảng viên:** Đúng như bạn vừa nói.\r\n"
)


# --- Bug đã sửa: heading KHÔNG được lọt vào thân đoạn -------------------------

def test_a_segment_never_swallows_the_next_section_heading():
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert "##" not in segs["T09-003"].text
    assert segs["T09-003"].text.endswith("mình bỏ qua.")


# --- Cấu trúc ----------------------------------------------------------------

def test_parses_every_segment_in_file_order():
    assert [s.code for s in parse_text(SAMPLE, "09")] == [
        "T09-001", "T09-002", "T09-003", "T09-004", "T09-005", "T09-006", "T09-007",
    ]


def test_session_title_drops_the_boilerplate_prefix():
    assert parse_text(SAMPLE, "09")[0].session_title == "Day 9 — Buổi thử"


def test_section_index_and_title_track_the_headings():
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert (segs["T09-002"].section_idx, segs["T09-002"].section_title) == (1, "Mở đầu")
    assert (segs["T09-004"].section_idx, segs["T09-004"].section_title) == (2, "Phần hai")


PRELUDE_SAMPLE = (
    "# Transcript bài giảng (bản sạch) — Day 9 — Buổi thử\r\n"
    "\r\n"
    "> **Quy ước:** `[Txx-NNN]` mã đoạn\r\n"
    "\r\n"
    "**[T09-000]** [Hoạt động lớp: mở đầu buổi, giảng viên hỏi cảm nhận.]\r\n"
    "\r\n"
    "## Mở đầu\r\n"
    "\r\n"
    "**[T09-001]** Nội dung đầu tiên.\r\n"
)


def test_a_segment_before_the_first_heading_is_not_dropped():
    # T02-001 và T05-001 nằm ở vùng này trên data thật. Duyệt theo section mà bỏ
    # vùng trước heading đầu tiên thì tổng tụt xuống 698/53 thay vì 700/55.
    assert [s.code for s in parse_text(PRELUDE_SAMPLE, "09")] == ["T09-000", "T09-001"]


def test_a_segment_before_the_first_heading_gets_section_index_zero():
    segs = {s.code: s for s in parse_text(PRELUDE_SAMPLE, "09")}
    assert segs["T09-000"].section_idx == 0
    assert segs["T09-001"].section_idx == 1


def test_order_is_one_based_and_continuous_across_sections():
    assert [s.order for s in parse_text(SAMPLE, "09")] == [1, 2, 3, 4, 5, 6, 7]


def test_segment_text_excludes_its_own_code():
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert "T09-002" not in segs["T09-002"].text
    assert segs["T09-002"].text == "Mình bắt đầu bằng một câu hỏi."


# --- Ba cờ metadata ----------------------------------------------------------

def test_front_matter_legend_is_not_counted_as_a_real_gap():
    # Front matter chứa "[không nghe rõ]" như chú giải. Chỉ T09-003 khuyết thật.
    assert [s.code for s in parse_text(SAMPLE, "09") if s.has_gap] == ["T09-003"]


def test_flags_the_class_activity_note():
    assert [s.code for s in parse_text(SAMPLE, "09") if s.is_activity] == ["T09-001"]


def test_locate_confidence_comes_from_the_front_matter():
    assert parse_text(SAMPLE, "09")[0].locate_confidence == "vừa"


def test_locate_confidence_is_a_dash_when_the_front_matter_has_none():
    no_conf = SAMPLE.replace(" — độ tin cậy: vừa", "")
    assert parse_text(no_conf, "09")[0].locate_confidence == "—"


# --- Giọng nói: marker có HAI dạng, thiếu một dạng là mất 18 đoạn -----------

def test_a_plain_student_marker_makes_the_segment_student_speech():
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert segs["T09-004"].speaker == "student"


def test_a_BOLD_student_marker_also_makes_the_segment_student_speech():
    # "**[Học viên]:**" là 18/69 đoạn thật. Regex chỉ nhận "[Học viên]" trần sẽ
    # phân loại chúng thành lời giảng viên — đúng cái sai mà lớp ④ đang phòng.
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert segs["T09-005"].speaker == "student"


def test_an_ordinary_segment_is_instructor_speech():
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert segs["T09-002"].speaker == "instructor"


def test_an_explicit_instructor_prefix_stays_instructor():
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert segs["T09-007"].speaker == "instructor"


def test_a_lowercase_anonymised_name_is_not_a_speaker_marker():
    # "[học viên]" chữ thường = tên đã ẩn danh (59 chỗ trong corpus), KHÁC "[Học viên]".
    segs = {s.code: s for s in parse_text(SAMPLE, "09")}
    assert segs["T09-006"].speaker == "instructor"


def test_n_chars_matches_the_text_length():
    for s in parse_text(SAMPLE, "09"):
        assert s.n_chars == len(s.text)


def test_content_segs_drops_activity_notes():
    assert [s.code for s in content_segs(parse_text(SAMPLE, "09"))] == [
        "T09-002", "T09-003", "T09-004", "T09-005", "T09-006", "T09-007",
    ]


# --- Data thật. Skip nếu thiếu data pack (repo nộp bài không chứa data/). ----

REAL_SECTIONS = {"01": 11, "02": 5, "03": 19, "04": 21, "05": 19, "06": 21}
REAL_CONFIDENCE = {"01": "cao", "02": "vừa", "03": "vừa", "04": "cao", "05": "—", "06": "—"}


def _need_data():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")


@pytest.mark.parametrize("session_id", SESSIONS)
def test_real_section_count_per_session(session_id):
    _need_data()
    segs = parse_session(session_id)
    assert max(s.section_idx for s in segs) == REAL_SECTIONS[session_id]


@pytest.mark.parametrize("session_id", SESSIONS)
def test_real_locate_confidence_per_session(session_id):
    _need_data()
    assert parse_session(session_id)[0].locate_confidence == REAL_CONFIDENCE[session_id]


def test_real_corpus_totals():
    _need_data()
    segs = parse_all()
    assert len(segs) == 700
    assert len(content_segs(segs)) == 645
    assert sum(s.is_activity for s in segs) == 55
    assert sum(s.has_gap for s in segs) == 103
    assert sum(s.speaker == "student" for s in segs) == 69

    # Tổng số section đếm được TRỰC TIẾP từ parse_all() — không phải cộng lại
    # dict hằng số REAL_SECTIONS khai ở trên (assertion đó không đụng tới
    # segs/parse_all() nên không thể fail dù parser sai thế nào).
    max_section_per_session: dict[str, int] = {}
    for s in segs:
        max_section_per_session[s.session] = max(
            max_section_per_session.get(s.session, 0), s.section_idx
        )
    assert sum(max_section_per_session.values()) == 96


def test_real_student_segments_per_session():
    _need_data()
    per_session = {sid: sum(s.speaker == "student" for s in parse_session(sid))
                   for sid in SESSIONS}
    assert per_session == {"01": 8, "02": 0, "03": 19, "04": 0, "05": 21, "06": 21}


def test_no_real_segment_has_the_student_marker_ONLY_in_the_middle():
    # Trên corpus này mọi đoạn chứa marker đều MỞ ĐẦU bằng nó — không có ca "trộn
    # hai giọng trong một đoạn". Test này là chốt chặn: nếu data đổi và ca đó xuất
    # hiện, nó nổ, và lúc đó mới cần thêm cảnh báo mềm ở cổng 3.
    _need_data()
    import re

    # Cùng logic với _STUDENT_START_RE trong flow1/parse.py, dựng lại từ
    # STUDENT_MARKER thay vì khai một literal riêng — một nguồn sự thật.
    starts = re.compile(r"^\*{0,2}" + re.escape(STUDENT_MARKER))
    mid_only = [s.code for s in parse_all()
                if STUDENT_MARKER in s.text and not starts.match(s.text)]
    assert mid_only == [], f"xuất hiện đoạn trộn giọng: {mid_only}"


def test_real_instructor_prefixed_segments():
    _need_data()
    assert sum(s.text.startswith("**Giảng viên:**") for s in parse_all()) == 18


def test_no_real_segment_swallowed_a_heading():
    _need_data()
    polluted = [s.code for s in parse_all() if "\n## " in s.text or s.text.startswith("## ")]
    assert polluted == [], f"heading lọt vào thân đoạn: {polluted}"


def test_the_giant_segment_is_present_and_intact():
    _need_data()
    by_code = {s.code: s for s in parse_all()}
    assert by_code["T06-059"].n_chars > 4900, "đoạn khổng lồ 4.999 ký tự, chunk.py phải tách nó"


def test_exactly_eighteen_content_segments_exceed_the_chunk_cap():
    _need_data()
    over = [s.code for s in content_segs(parse_all()) if s.n_chars > 1800]
    assert len(over) == 18, f"canvas khai 1 đoạn, thực tế 18: {over}"
