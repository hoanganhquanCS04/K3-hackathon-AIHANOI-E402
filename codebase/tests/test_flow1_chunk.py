"""Test chunk.py. Chủ: M1 (khối B)."""

import pytest

from flow1.chunk import CAP_CHARS, TARGET_CHARS, chunk_all, chunk_session, split_giant
from flow1.models import Seg
from flow1.parse import TRANSCRIPT_DIR, content_segs, parse_all


def seg(code, text, *, section_idx=1, section_title="S1", order=1, session="09", has_gap=False):
    return Seg(
        code=code, session=session, session_title="Buổi thử",
        locate_confidence="vừa", section_idx=section_idx, section_title=section_title,
        order=order, text=text, speaker="instructor",
        has_gap=has_gap, is_activity=False, n_chars=len(text),
    )


def filler(n, ch="a"):
    return ch * n


# --- Gộp -------------------------------------------------------------------

def test_two_small_neighbours_in_one_section_merge_into_one_chunk():
    segs = [seg("T09-001", filler(400), order=1), seg("T09-002", filler(400), order=2)]
    chunks = chunk_session(segs)
    assert len(chunks) == 1
    assert chunks[0].seg_codes == ["T09-001", "T09-002"]


def test_a_merged_chunk_never_exceeds_the_hard_cap():
    segs = [seg(f"T09-{i:03d}", filler(700), order=i) for i in range(1, 8)]
    for chunk in chunk_session(segs):
        assert chunk.n_chars <= CAP_CHARS


def test_merging_stops_once_the_target_is_reached():
    # 3 đoạn 600 ký tự: 600+600=1200 đã vượt target 1100 → dừng, không lấy đoạn thứ 3.
    segs = [seg(f"T09-{i:03d}", filler(600), order=i) for i in range(1, 4)]
    assert chunk_session(segs)[0].seg_codes == ["T09-001", "T09-002"]


def test_never_merges_across_a_section_boundary():
    segs = [
        seg("T09-001", filler(300), section_idx=1, section_title="Một", order=1),
        seg("T09-002", filler(300), section_idx=2, section_title="Hai", order=2),
    ]
    chunks = chunk_session(segs)
    assert len(chunks) == 2
    assert [c.section_title for c in chunks] == ["Một", "Hai"]


def test_never_merges_across_a_session_boundary():
    segs = [
        seg("T09-001", filler(300), session="09", order=1),
        seg("T10-001", filler(300), session="10", order=1),
    ]
    assert {c.session for c in chunk_all(segs)} == {"09", "10"}
    assert len(chunk_all(segs)) == 2


# --- Overlap ---------------------------------------------------------------

def test_adjacent_chunks_overlap_by_exactly_one_segment():
    segs = [seg(f"T09-{i:03d}", filler(600), order=i) for i in range(1, 6)]
    chunks = chunk_session(segs)
    assert len(chunks) >= 2
    for left, right in zip(chunks, chunks[1:]):
        assert left.seg_codes[-1] == right.seg_codes[0], "overlap đúng 1 đoạn"


def test_a_lone_segment_chunk_does_not_create_an_infinite_overlap():
    # Đoạn đơn không gộp được với ai thì KHÔNG overlap — nếu overlap thì vòng lặp
    # không tiến và hàm treo. Test này là cái phanh.
    segs = [seg(f"T09-{i:03d}", filler(1700), order=i) for i in range(1, 4)]
    chunks = chunk_session(segs)
    assert [c.seg_codes for c in chunks] == [["T09-001"], ["T09-002"], ["T09-003"]]


# --- Đoạn khổng lồ ---------------------------------------------------------

def test_a_segment_over_the_cap_is_split_by_sentence():
    long_text = " ".join(f"Câu số {i} dài vừa phải để test." * 6 for i in range(1, 30))
    assert len(long_text) > CAP_CHARS
    pieces = split_giant(seg("T09-001", long_text))
    assert len(pieces) >= 2
    for piece in pieces:
        assert piece.n_chars <= CAP_CHARS


def test_every_piece_of_a_split_segment_keeps_the_ORIGINAL_code():
    long_text = " ".join(f"Câu số {i} dài vừa phải để test." * 6 for i in range(1, 30))
    pieces = split_giant(seg("T09-001", long_text))
    for piece in pieces:
        assert piece.seg_codes == ["T09-001"], "mã gốc là citation unit — mất nó là mất truy vết"


def test_split_pieces_get_distinct_suffixed_chunk_ids():
    long_text = " ".join(f"Câu số {i} dài vừa phải để test." * 6 for i in range(1, 30))
    ids = [p.chunk_id for p in split_giant(seg("T09-001", long_text))]
    assert ids[0] == "T09-001#a"
    assert len(set(ids)) == len(ids)


def test_a_giant_segment_is_never_merged_with_its_neighbours():
    long_text = "Câu dài. " * 400
    segs = [
        seg("T09-001", filler(300), order=1),
        seg("T09-002", long_text, order=2),
        seg("T09-003", filler(300), order=3),
    ]
    codes = [c.seg_codes for c in chunk_session(segs)]
    assert ["T09-001"] in codes
    assert all(c == ["T09-002"] for c in codes if "T09-002" in c)
    assert ["T09-003"] in codes


def test_a_single_unsplittable_sentence_over_the_cap_still_yields_one_piece():
    # Không có dấu câu nào để tách → vẫn phải trả về 1 mảnh, không được rơi vào
    # vòng lặp vô hạn hay trả rỗng.
    pieces = split_giant(seg("T09-001", filler(2500)))
    assert len(pieces) == 1
    assert pieces[0].seg_codes == ["T09-001"]


# --- Cờ và metadata --------------------------------------------------------

def test_a_chunk_has_gap_when_any_of_its_segments_has_a_gap():
    segs = [
        seg("T09-001", filler(300), order=1),
        seg("T09-002", filler(300), order=2, has_gap=True),
    ]
    assert chunk_session(segs)[0].has_gap is True


def test_chunk_index_text_prefixes_the_session_and_section_headings():
    chunk = chunk_session([seg("T09-001", "nội dung")])[0]
    assert chunk.index_text.startswith("Buổi thử › S1\n")


def test_chunk_labelled_tags_each_part_with_its_code_for_the_prompt():
    segs = [seg("T09-001", "phần một", order=1), seg("T09-002", "phần hai", order=2)]
    labelled = chunk_session(segs)[0].labelled
    assert "[T09-001] phần một" in labelled
    assert "[T09-002] phần hai" in labelled


def test_chunk_text_stays_clean_of_codes_so_the_index_is_not_polluted():
    chunk = chunk_session([seg("T09-001", "nội dung")])[0]
    assert "T09-001" not in chunk.text


# --- Data thật -------------------------------------------------------------

def test_real_corpus_chunk_count_is_in_a_sane_range():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    chunks = chunk_all(content_segs(parse_all()))
    # Canvas ước ~400 (đo ~340 khi chưa bật overlap). Assert KHOẢNG, không hardcode.
    assert 300 <= len(chunks) <= 550, f"số chunk thật: {len(chunks)}"


def test_no_real_chunk_exceeds_the_cap():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    over = [(c.chunk_id, c.n_chars) for c in chunk_all(content_segs(parse_all())) if c.n_chars > CAP_CHARS]
    assert over == []


def test_no_activity_note_ever_reaches_the_index():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    for chunk in chunk_all(content_segs(parse_all())):
        assert "[Hoạt động lớp" not in chunk.text


def test_every_real_chunk_id_is_unique():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    ids = [c.chunk_id for c in chunk_all(content_segs(parse_all()))]
    assert len(set(ids)) == len(ids)


def test_no_real_chunk_mixes_two_sections():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    by_code = {s.code: s for s in parse_all()}
    for chunk in chunk_all(content_segs(parse_all())):
        idxs = {by_code[c].section_idx for c in chunk.seg_codes}
        assert len(idxs) == 1, f"{chunk.chunk_id} trộn section {idxs}"
