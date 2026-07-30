"""Test tích hợp flow1 ↔ sotay. Chủ: M1 + M2 cùng ngồi.

Task này chứng minh ba hợp đồng ở design §2 là THẬT chứ không phải khẩu hiệu:
  1. bộ kiểm mã trích dẫn dùng chung hai luồng
  2. hai parser không lệch nhau
  3. chiều phụ thuộc một hướng flow1 → sotay
"""

import pathlib

import pytest

CODEBASE = pathlib.Path(__file__).resolve().parents[1]


def _need_sotay():
    pytest.importorskip(
        "sotay.verify",
        reason="chờ Task 3 của plan luồng 2 (sotay/verify.py). "
        "Luồng 1 CHƯA xong khi test này còn skip.",
    )


def _need_check_citations():
    _need_sotay()
    import sotay.verify as verify_module

    if not hasattr(verify_module, "check_citations"):
        pytest.skip(
            "sotay.verify chưa tách check_citations — xem design §2.3. "
            "M1 cần tách phần đếm số ý ra khỏi phần kiểm mã."
        )


# --- Hợp đồng 1: bộ kiểm dùng chung là THẬT --------------------------

def test_the_shared_verifier_accepts_a_flow1_seg_without_any_change():
    # Đây là chỗ duck-typing được nghiệm thu: Seg của luồng 1 mang đúng 4 tên
    # attribute mà sotay.verify đọc, nên bộ kiểm của M1 chạy trên nó không cần sửa.
    _need_check_citations()
    from sotay.verify import check_citations

    from flow1.models import Seg

    seg = Seg(
        code="T03-002", session="03", session_title="t", locate_confidence="vừa",
        section_idx=1, section_title="s", order=1, text="nội dung",
        speaker="instructor", has_gap=False, is_activity=False, n_chars=8,
    )

    class Point:
        statement = "Một ý."
        codes = ["T03-002"]

    assert check_citations([Point()], [seg]) == []


def test_the_shared_verifier_catches_a_fabricated_code_on_flow1_data():
    _need_check_citations()
    from sotay.verify import check_citations

    from flow1.models import Seg

    seg = Seg(
        code="T03-002", session="03", session_title="t", locate_confidence="vừa",
        section_idx=1, section_title="s", order=1, text="nội dung",
        speaker="instructor", has_gap=False, is_activity=False, n_chars=8,
    )

    class Point:
        statement = "Ý bịa."
        codes = ["T03-777"]

    findings = check_citations([Point()], [seg])
    assert any(f.kind == "unknown_code" for f in findings)


def test_gate3_wired_to_the_real_shared_verifier_drops_a_fabricated_claim():
    _need_check_citations()
    from flow1.check import check
    from flow1.models import Answer, Chunk, Claim, Hit, Retrieval, Seg

    seg = Seg(
        code="T03-002", session="03", session_title="t", locate_confidence="vừa",
        section_idx=1, section_title="s", order=1, text="nội dung",
        speaker="instructor", has_gap=False, is_activity=False, n_chars=8,
    )
    chunk = Chunk(
        chunk_id="T03-002", session="03", session_title="t", section_idx=1,
        section_title="s", parts=[("T03-002", "nội dung")], has_gap=False,
    )
    retrieval = Retrieval(
        hits=[Hit(chunk=chunk, bm25=9.0, emb=None, rank=0, score=9.0)],
        top1_abs=9.0, ratio=3.0,
    )
    answer = Answer(
        status="answered",
        claims=[Claim(text="Ý bịa.", cite=["T03-777"], speaker="instructor")],
        gaps=[],
    )

    verdict = check(answer, retrieval, [seg])      # KHÔNG inject — dùng sotay thật
    assert verdict.claims == []
    assert verdict.status == "insufficient"


def test_flow2_verify_behaviour_is_unchanged_after_the_extraction():
    # M1 tách check_citations ra khỏi verify(). verify() phải còn nguyên hành vi,
    # kể cả check "đúng 5 ý" — nếu không thì luồng 2 vỡ.
    _need_check_citations()
    from sotay.verify import EXPECTED_POINTS, verify

    assert EXPECTED_POINTS == 5

    class Point:
        statement = "x"
        codes = []

    findings = verify(
        type("NB", (), {"session_title": "t", "points": [Point()]})(), []
    )
    assert any(f.kind == "wrong_point_count" for f in findings)


# --- Hợp đồng 2: hai parser KHÔNG lệch nhau ------------------------

def test_the_two_parsers_produce_the_identical_list_of_codes():
    # Cái phanh của phương án "hai thư mục riêng". Lệch một mã là fail — và đây
    # cũng là câu trả lời gọn cho TA ở CP5 khi bị hỏi "sao có hai bộ parse".
    _need_sotay()
    from sotay.ingest import TRANSCRIPT_DIR, load_session

    from flow1.parse import SESSIONS, parse_session

    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")

    for session_id in SESSIONS:
        mine = [s.code for s in parse_session(session_id)]
        theirs = [s.code for s in load_session(session_id)[1]]
        assert mine == theirs, f"buổi {session_id} lệch giữa flow1.parse và sotay.ingest"


def test_the_two_parsers_agree_on_which_segments_have_gaps():
    _need_sotay()
    from sotay.ingest import TRANSCRIPT_DIR, load_session

    from flow1.parse import SESSIONS, parse_session

    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")

    for session_id in SESSIONS:
        mine = {s.code for s in parse_session(session_id) if s.has_gap}
        theirs = {s.code for s in load_session(session_id)[1] if s.has_gap}
        assert mine == theirs, f"buổi {session_id} lệch cờ has_gap"


def test_sotay_ingest_no_longer_swallows_section_headings():
    # Bug đã báo M1 ở design §0.1. Test này là cái phanh, KHÔNG phải chỗ để tắt đi.
    # Nếu nó fail thì sotay/ingest.py chưa sửa, và prompt luồng 2 vẫn đang nhận
    # text lẫn tiêu đề section.
    _need_sotay()
    from sotay.ingest import TRANSCRIPT_DIR, load_session

    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")

    polluted = [
        s.code
        for session_id in ("01", "02", "03", "04", "05", "06")
        for s in load_session(session_id)[1]
        if "\n## " in s.text or s.text.startswith("## ")
    ]
    assert polluted == [], (
        f"sotay/ingest.py còn hút heading vào {len(polluted)} đoạn — xem design §0.1"
    )


# --- Hợp đồng 3: chiều phụ thuộc MỘT HƯỚNG ------------------------

def test_sotay_never_imports_flow1():
    sotay_dir = CODEBASE / "sotay"
    if not sotay_dir.exists():
        pytest.skip("sotay/ chưa có")
    offenders = [
        path.name
        for path in sotay_dir.glob("*.py")
        if "flow1" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"sotay không được biết tới flow1: {offenders}"


def test_flow1_never_imports_the_flow2_generator():
    offenders = [
        path.name
        for path in (CODEBASE / "src" / "flow1").glob("*.py")
        if "sotay.generate" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"hai luồng không kéo nhau sập: {offenders}"


def test_flow1_borrows_exactly_two_things_from_sotay():
    # Ranh giới provider duy nhất (llm) + bộ kiểm dùng chung (verify). Không hơn.
    allowed = {"sotay.llm", "sotay.verify"}
    found = set()
    for path in (CODEBASE / "src" / "flow1").glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "sotay." in line and ("import" in line or "from" in line):
                for name in allowed | {"sotay.generate", "sotay.ingest", "sotay.render",
                                       "sotay.cli", "sotay.registry", "sotay.prompts"}:
                    if name in line:
                        found.add(name)
    assert found <= allowed, f"flow1 mượn thêm thứ không được phép: {found - allowed}"


def test_flow1_is_importable_even_when_sotay_is_absent():
    # Mọi import sotay phải LAZY. Test này chạy được vì flow1 đã import xong ở đây.
    import flow1.ask
    import flow1.check
    import flow1.gates

    for module in (flow1.gates, flow1.check, flow1.ask):
        header = open(module.__file__, encoding="utf-8").read().split("def ")[0]
        assert "sotay" not in header, f"{module.__name__} import sotay ở đầu file"
