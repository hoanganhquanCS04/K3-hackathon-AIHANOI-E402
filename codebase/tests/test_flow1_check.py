"""Test cổng 3. Chủ: M2 (khối E), dùng bộ kiểm của M1. KHÔNG gọi mạng."""

from flow1.check import GAP_LABEL, STUDENT_LABEL, check, context_codes
from flow1.models import Answer, Chunk, Claim, Hit, Retrieval, Seg


def seg(code, *, speaker="instructor", has_gap=False, is_activity=False):
    return Seg(
        code=code, session="03", session_title="Buổi 03", locate_confidence="vừa",
        section_idx=1, section_title="S1", order=1, text=f"nguyên văn {code}",
        speaker=speaker, has_gap=has_gap, is_activity=is_activity, n_chars=12,
    )


SEGS = [
    seg("T03-001", is_activity=True),
    seg("T03-002"),
    seg("T03-003", has_gap=True),
    seg("T03-004", speaker="student"),                # marker trần
    seg("T03-005", speaker="student"),                # marker in đậm — cùng nhãn
    seg("T03-006"),
    seg("T03-099"),                                   # mã THẬT nhưng KHÔNG trong context
]


def hit(codes, rank=0):
    chunk = Chunk(
        chunk_id=codes[0], session="03", session_title="Buổi 03", section_idx=1,
        section_title="S1", parts=[(c, f"nguyên văn {c}") for c in codes], has_gap=False,
    )
    return Hit(chunk=chunk, bm25=9.0, emb=None, rank=rank, score=9.0)


def retrieval_of(*code_groups):
    return Retrieval(
        hits=[hit(list(g), i) for i, g in enumerate(code_groups)],
        top1_abs=9.0, ratio=3.0,
    )


CONTEXT = retrieval_of(
    ["T03-002", "T03-003"], ["T03-004", "T03-005"], ["T03-006"],
)


def answer(*claims, status="answered", gaps=None):
    return Answer(status=status, claims=list(claims), gaps=list(gaps or []))


def claim(text, codes, speaker="instructor"):
    return Claim(text=text, cite=list(codes), speaker=speaker)


# --- context_codes ---------------------------------------------------------

def test_context_codes_is_the_union_of_every_hit_segment_code():
    assert context_codes(CONTEXT) == {"T03-002", "T03-003", "T03-004", "T03-005", "T03-006"}


def test_context_codes_on_an_empty_retrieval_is_empty():
    assert context_codes(Retrieval(hits=[], top1_abs=0.0, ratio=0.0)) == set()


# --- Đường sạch -----------------------------------------------------------

def test_a_clean_answer_keeps_every_claim():
    verdict = check(answer(claim("Điều A.", ["T03-002"])), CONTEXT, SEGS)
    assert [c.text for c in verdict.claims] == ["Điều A."]
    assert verdict.drops == []
    assert verdict.status == "answered"


# --- Mã bịa: LOẠI, không sửa ----------------------------------------------

def test_a_fabricated_code_drops_the_whole_claim():
    verdict = check(answer(claim("Điều bịa.", ["T03-777"])), CONTEXT, SEGS)
    assert verdict.claims == []
    assert [d.kind for d in verdict.drops] == ["unknown_code"]


def test_the_drop_record_names_the_fabricated_code_and_the_claim():
    verdict = check(answer(claim("Điều bịa.", ["T03-777"])), CONTEXT, SEGS)
    assert "T03-777" in verdict.drops[0].detail
    assert verdict.drops[0].claim_text == "Điều bịa."


def test_a_fabricated_code_is_never_repaired_into_a_nearby_real_one():
    verdict = check(answer(claim("Điều bịa.", ["T03-777"])), CONTEXT, SEGS)
    assert all("T03-777" not in c.cite for c in verdict.claims)
    assert verdict.claims == [], "sửa mã hộ model là đoán — đúng cái lớp ① đang phòng"


def test_a_claim_with_no_codes_at_all_is_dropped():
    verdict = check(answer(claim("Không nguồn.", [])), CONTEXT, SEGS)
    assert [d.kind for d in verdict.drops] == ["no_codes"]
    assert verdict.claims == []


def test_only_the_offending_claim_is_dropped_the_others_survive():
    verdict = check(
        answer(claim("Điều bịa.", ["T03-777"]), claim("Điều thật.", ["T03-002"])),
        CONTEXT, SEGS,
    )
    assert [c.text for c in verdict.claims] == ["Điều thật."]
    assert len(verdict.drops) == 1


# --- Mã thật NHƯNG ngoài context: riêng của luồng 1 -----------------------

def test_a_real_code_that_was_not_in_the_context_is_still_a_fabrication():
    # T03-099 tồn tại trong 700 mã thật, nhưng không nằm trong 5 chunk đã đưa vào
    # prompt. Model không thể "biết" nội dung nó — nên đây vẫn là bịa.
    verdict = check(answer(claim("Điều ngoài context.", ["T03-099"])), CONTEXT, SEGS)
    assert [d.kind for d in verdict.drops] == ["outside_context"]
    assert verdict.claims == []


def test_the_outside_context_drop_explains_the_difference_from_unknown_code():
    verdict = check(answer(claim("x", ["T03-099"])), CONTEXT, SEGS)
    assert "context" in verdict.drops[0].detail.lower()


def test_a_claim_citing_an_activity_note_is_dropped():
    ctx = retrieval_of(["T03-001", "T03-002"])
    verdict = check(answer(claim("Điểm danh.", ["T03-001"])), ctx, SEGS)
    assert verdict.claims == []
    assert verdict.drops[0].kind in ("cites_activity", "unknown_code")


# --- Lớp ④: giọng học viên, HAI mức --------------------------------------

def test_citing_a_student_segment_forces_the_student_label():
    verdict = check(answer(claim("Một ý.", ["T03-004"])), CONTEXT, SEGS)
    assert "T03-004" in verdict.student_codes
    assert STUDENT_LABEL


def test_the_student_label_is_forced_even_when_the_model_claimed_instructor():
    # Model gán lời học viên thành lời giảng viên là học viên học sai kiến thức
    # nghề. Nhãn do CODE quyết định, không do model tự khai.
    verdict = check(answer(claim("Một ý.", ["T03-004"], speaker="instructor")), CONTEXT, SEGS)
    assert "T03-004" in verdict.student_codes


def test_a_bold_marker_student_segment_gets_the_same_label():
    # 18/69 đoạn dùng marker in đậm. Chúng là lời học viên y như 51 đoạn kia —
    # không có mức nhãn thứ hai nào cả.
    verdict = check(answer(claim("Một ý.", ["T03-005"])), CONTEXT, SEGS)
    assert "T03-005" in verdict.student_codes


def test_an_instructor_segment_gets_no_voice_label():
    verdict = check(answer(claim("Một ý.", ["T03-002"])), CONTEXT, SEGS)
    assert verdict.student_codes == []


# --- Lớp ①: cờ bản ghi thiếu, tính TẤT ĐỊNH -----------------------------

def test_a_gapped_segment_is_flagged_from_the_segment_data_not_from_the_model():
    # Model không khai gaps, nhưng cổng 3 vẫn phải bật cờ — nó đọc Seg.has_gap.
    verdict = check(answer(claim("Một ý.", ["T03-003"]), gaps=[]), CONTEXT, SEGS)
    assert "T03-003" in verdict.gap_codes
    assert GAP_LABEL


def test_a_clean_segment_is_never_flagged_as_gapped():
    verdict = check(answer(claim("Một ý.", ["T03-002"])), CONTEXT, SEGS)
    assert verdict.gap_codes == []


def test_a_gap_flag_does_not_drop_the_claim():
    # Bản ghi thiếu ≠ ý sai. Gắn cờ để người đọc tự phán, không xoá.
    verdict = check(answer(claim("Một ý.", ["T03-003"])), CONTEXT, SEGS)
    assert len(verdict.claims) == 1


def test_gap_codes_are_deduplicated_across_claims():
    verdict = check(
        answer(claim("A.", ["T03-003"]), claim("B.", ["T03-003", "T03-002"])),
        CONTEXT, SEGS,
    )
    assert verdict.gap_codes == ["T03-003"]


# --- Trạng thái ----------------------------------------------------------

def test_dropping_every_claim_turns_the_status_into_insufficient():
    # Không được trả danh sách rỗng rồi im lặng — phải nói ra là không đủ căn cứ.
    verdict = check(answer(claim("Bịa.", ["T03-777"])), CONTEXT, SEGS)
    assert verdict.status == "insufficient"


def test_a_model_declared_insufficient_is_respected_and_not_upgraded():
    verdict = check(answer(status="insufficient"), CONTEXT, SEGS)
    assert verdict.status == "insufficient"
    assert verdict.claims == []


def test_a_model_declared_out_of_scope_is_respected():
    verdict = check(answer(status="out_of_scope"), CONTEXT, SEGS)
    assert verdict.status == "out_of_scope"


def test_surviving_claims_keep_the_answered_status():
    verdict = check(
        answer(claim("Bịa.", ["T03-777"]), claim("Thật.", ["T03-002"])), CONTEXT, SEGS
    )
    assert verdict.status == "answered"


# --- Bộ kiểm DÙNG CHUNG là thật, không phải khẩu hiệu -------------------

def test_check_delegates_the_real_code_lookup_to_the_shared_verifier():
    seen = {}

    def spy_check_citations(points, segments):
        seen["points"] = points
        seen["segments"] = segments
        return []

    check(answer(claim("Một ý.", ["T03-002"])), CONTEXT, SEGS,
          check_citations=spy_check_citations)
    assert seen["segments"] is SEGS
    assert [p.codes for p in seen["points"]] == [["T03-002"]]


def test_the_shared_verifier_sees_a_codes_attribute_because_that_is_its_contract():
    # sotay.verify đọc point.codes và point.statement. Adapter phải cung cấp đúng
    # hai tên đó, nếu không bộ kiểm dùng chung sẽ vỡ khi ghép thật ở Task 12.
    seen = {}

    def spy(points, segments):
        seen["ok"] = all(hasattr(p, "codes") and hasattr(p, "statement") for p in points)
        return []

    check(answer(claim("Một ý.", ["T03-002"])), CONTEXT, SEGS, check_citations=spy)
    assert seen["ok"]


def test_a_finding_from_the_shared_verifier_drops_the_claim():
    class Finding:
        def __init__(self):
            self.point_index = 0
            self.kind = "unknown_code"
            self.detail = "Ý 1 trích mã T03-002 — mã này không có trong transcript."

    verdict = check(answer(claim("Một ý.", ["T03-002"])), CONTEXT, SEGS,
                    check_citations=lambda p, s: [Finding()])
    assert verdict.claims == []
    assert verdict.drops[0].kind == "unknown_code"


def test_check_imports_sotay_lazily_so_flow1_works_without_it():
    import flow1.check as check_module

    source = open(check_module.__file__, encoding="utf-8").read()
    header = source.split("def ")[0]
    assert "sotay" not in header, "import sotay phải nằm TRONG thân hàm"


def test_check_never_touches_the_llm():
    import flow1.check as check_module

    source = open(check_module.__file__, encoding="utf-8").read()
    assert "anthropic" not in source
    assert "sotay.generate" not in source
    assert "complete_json" not in source
