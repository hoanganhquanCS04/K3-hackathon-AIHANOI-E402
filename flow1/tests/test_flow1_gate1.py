"""Test cổng 1 — code thuần, chạy TRƯỚC generate. Chủ: M2 (khối E).

Amendment 2026-07-30 (a): brief gốc còn có mục cổng 0 trong gates.py — đã BỎ.
Cổng 0 là stubs.route(), vá ở task khác. File này và test này chỉ nói về cổng 1.

Amendment 2026-07-30 (b): thêm `refusal_message(r, all_sessions=...)` — câu từ
chối làm giàu bằng một Retrieval dò rộng (không lọc buổi), CHỈ để lấy heading.
gates.py không được import flow1.retrieve — việc dò rộng là I/O của tầng điều
phối ở task sau; gates.py chỉ nhận Retrieval đã có sẵn làm tham số.
"""

import math

from flow1.gates import Decision, gate1, nearest_headings, refusal_message
from flow1.models import Chunk, Hit, Retrieval
from flow1.thresholds import AMBIG_BAND, T1_ABS, T1_RATIO


def hit(chunk_id, *, session, section_title, bm25, rank):
    chunk = Chunk(
        chunk_id=chunk_id, session=session, session_title=f"Buổi {session}",
        section_idx=1, section_title=section_title,
        parts=[(chunk_id, "nội dung")], has_gap=False,
    )
    return Hit(chunk=chunk, bm25=bm25, emb=None, rank=rank, score=bm25)


def retrieval(pairs, *, top1_abs=None, ratio=None):
    """pairs = [(session, section_title, bm25)]"""
    hits = [
        hit(f"C{i}", session=s, section_title=t, bm25=b, rank=i)
        for i, (s, t, b) in enumerate(pairs)
    ]
    scores = [b for _, _, b in pairs]
    return Retrieval(
        hits=hits,
        top1_abs=scores[0] if top1_abs is None else top1_abs,
        ratio=(scores[0] / (sum(scores[1:5]) / len(scores[1:5])))
        if ratio is None and len(scores) > 1 and sum(scores[1:5]) > 0
        else (ratio if ratio is not None else math.inf),
    )


def strong_single_session():
    """Điểm cao, phân bố nhọn, cùng một buổi → phải qua."""
    return retrieval(
        [("03", "RAG và tool calling", 20.0),
         ("03", "Ba track nghề nghiệp", 2.5),
         ("03", "Chọn dự án", 2.5),
         ("03", "Giới thiệu", 2.5),
         ("03", "Metric", 2.5)],
    )


# --- Đường happy -----------------------------------------------------------

def test_a_strong_peaked_result_passes():
    assert gate1(strong_single_session()).action == "pass"


def test_passing_carries_the_retrieval_forward_untouched():
    r = strong_single_session()
    assert gate1(r).retrieval is r


# --- Từ chối cứng: sàn tuyệt đối -------------------------------------------

def test_a_low_absolute_score_is_refused_even_when_the_ratio_is_huge():
    # Ca "token hiếm": đúng 1 chunk khớp → ratio = inf nhưng abs bé tí.
    # Chỉ sàn tuyệt đối chặn được — đây là lý do cổng 1 có HAI ngưỡng.
    r = retrieval([("03", "RAG và tool calling", -1.0),
                   ("03", "Ba track", 0.0), ("01", "Bài toán", 0.0)],
                  ratio=math.inf)
    assert gate1(r).action == "refuse"


def test_a_zero_score_result_is_refused():
    r = retrieval([("03", "RAG", 0.0)], top1_abs=0.0, ratio=0.0)
    assert gate1(r).action == "refuse"


def test_an_empty_retrieval_is_refused_and_does_not_crash():
    r = Retrieval(hits=[], top1_abs=0.0, ratio=0.0)
    assert gate1(r).action == "refuse"


# --- Từ chối cứng: tỷ số --------------------------------------------------

def test_a_flat_distribution_is_refused_even_when_absolute_scores_are_high():
    flat = 20.0
    r = retrieval([("03", "RAG", flat), ("01", "Bài toán", flat),
                   ("02", "Metric", flat), ("05", "Dữ liệu", flat),
                   ("06", "Attention", flat)])
    assert r.ratio < T1_RATIO
    assert gate1(r).action == "refuse"


# --- Câu từ chối phải MANG THÔNG TIN, không phải ngõ cụt -------------------

def test_the_refusal_says_plainly_that_the_content_is_not_in_the_six_sessions():
    r = retrieval([("03", "RAG", 0.0)], top1_abs=0.0, ratio=0.0)
    assert "6 buổi" in gate1(r).message


def test_the_refusal_lists_the_three_nearest_headings():
    flat = 20.0
    r = retrieval([("03", "RAG và tool calling", flat), ("01", "Bài toán mơ hồ", flat),
                   ("02", "Chỉ số thành công", flat), ("05", "Dữ liệu", flat),
                   ("06", "Attention", flat)])
    message = gate1(r).message
    for title in ("RAG và tool calling", "Bài toán mơ hồ", "Chỉ số thành công"):
        assert title in message


def test_the_refusal_names_the_session_of_each_nearest_heading():
    flat = 20.0
    r = retrieval([("03", "RAG", flat), ("01", "Bài toán", flat), ("02", "Metric", flat),
                   ("05", "Dữ liệu", flat), ("06", "Attention", flat)])
    message = gate1(r).message
    assert "Buổi 03" in message and "Buổi 01" in message


def test_nearest_headings_deduplicates_repeated_sections():
    r = retrieval([("03", "RAG", 9.0), ("03", "RAG", 8.0), ("01", "Bài toán", 7.0),
                   ("02", "Metric", 6.0), ("05", "Dữ liệu", 5.0)])
    assert nearest_headings(r, 3) == ["Buổi 03 › RAG", "Buổi 01 › Bài toán", "Buổi 02 › Metric"]


def test_nearest_headings_on_an_empty_retrieval_returns_an_empty_list():
    assert nearest_headings(Retrieval(hits=[], top1_abs=0.0, ratio=0.0)) == []


def test_a_refusal_with_no_hits_at_all_still_produces_a_usable_message():
    r = Retrieval(hits=[], top1_abs=0.0, ratio=0.0)
    message = gate1(r).message
    assert "6 buổi" in message
    assert message.strip().endswith(".") or "Buổi" not in message


# --- Hỏi lại: mơ hồ đa buổi ----------------------------------------------

def test_two_close_hits_in_DIFFERENT_sessions_trigger_a_clarifying_question():
    top = 20.0
    r = retrieval([("02", "Chỉ số thành công", top),
                   ("05", "Đánh giá đầu ra", top * AMBIG_BAND),
                   ("03", "RAG", top * 0.2), ("03", "Ba track", top * 0.2),
                   ("01", "Bài toán", top * 0.2)])
    decision = gate1(r)
    assert decision.action == "clarify"


def test_the_clarifying_question_names_both_candidate_sessions():
    top = 20.0
    r = retrieval([("02", "Chỉ số thành công", top),
                   ("05", "Đánh giá đầu ra", top * AMBIG_BAND),
                   ("03", "RAG", top * 0.2), ("03", "Ba track", top * 0.2),
                   ("01", "Bài toán", top * 0.2)])
    message = gate1(r).message
    assert "buổi 02" in message.lower() and "buổi 05" in message.lower()


def test_the_clarifying_question_tells_the_user_how_to_answer_it():
    # Hỏi lại mà người dùng không có cách trả lời thì đường "correction" chỉ có
    # trên giấy. Câu hỏi phải chỉ ra cờ --session.
    top = 20.0
    r = retrieval([("02", "Chỉ số", top), ("05", "Đánh giá", top * AMBIG_BAND),
                   ("03", "RAG", top * 0.2), ("03", "Ba track", top * 0.2),
                   ("01", "Bài toán", top * 0.2)])
    assert "--session" in gate1(r).message


def test_two_close_hits_in_the_SAME_session_do_not_trigger_a_question():
    top = 20.0
    r = retrieval([("03", "RAG", top), ("03", "Ba track", top * AMBIG_BAND),
                   ("03", "Metric", top * 0.2), ("03", "Giới thiệu", top * 0.2),
                   ("03", "Chọn dự án", top * 0.2)])
    assert gate1(r).action == "pass", "cùng buổi thì không mơ hồ về buổi"


def test_the_refusal_check_runs_BEFORE_the_ambiguity_check():
    # Điểm thấp + hai buổi gần nhau: phải TỪ CHỐI, không phải hỏi lại. Hỏi lại một
    # câu mà mình vốn không có căn cứ trả lời là làm người dùng mất thêm một lượt.
    r = retrieval([("02", "Chỉ số", -1.5), ("05", "Đánh giá", -1.5 * AMBIG_BAND),
                   ("03", "RAG", 0.0), ("03", "Ba track", 0.0), ("01", "Bài toán", 0.0)])
    assert gate1(r).action == "refuse"


def test_a_single_hit_never_triggers_the_ambiguity_check():
    r = retrieval([("03", "RAG", 20.0)], ratio=math.inf)
    assert gate1(r).action == "pass"


# --- Amendment (b): làm giàu câu từ chối bằng dò rộng ---------------------
#
# Giao diện mở một buổi tại một thời điểm nên `r` truyền vào gate1/refusal_message
# đã bị lọc theo buổi đang mở. Khi bị chặn, tầng điều phối (task sau) dò thêm cả
# 6 buổi và truyền kết quả đó vào đây qua `all_sessions` CHỈ để lấy heading.
# gate1() tự nó không nhận all_sessions — nó chấm điểm trong phạm vi đang mở.
# refusal_message() thì có, vì nó là hàm build câu chữ, không phải hàm chấm điểm.

def test_refusal_message_without_all_sessions_matches_the_bare_behaviour():
    r = retrieval([("03", "RAG", 0.0)], top1_abs=0.0, ratio=0.0)
    assert refusal_message(r) == gate1(r).message
    assert "6 buổi" in refusal_message(r)


def test_refusal_message_enriched_with_a_wide_retrieval_names_the_other_session():
    r = retrieval([("03", "RAG", 0.0)], top1_abs=0.0, ratio=0.0)
    wide = retrieval([("05", "Đánh giá chất lượng đầu ra", 9.0), ("03", "RAG", 8.0)])
    message = refusal_message(r, all_sessions=wide)
    assert "Buổi 05" in message
    assert "Đánh giá chất lượng đầu ra" in message
    assert "buổi khác" in message.lower()


def test_refusal_message_enrichment_skips_headings_already_in_the_narrow_session():
    # `wide` chỉ chứa cùng buổi với `r` → không có gì mới để nói, giữ nguyên câu gốc.
    r = retrieval([("03", "RAG", 0.0)], top1_abs=0.0, ratio=0.0)
    wide = retrieval([("03", "RAG", 9.0), ("03", "Ba track", 8.0)])
    message = refusal_message(r, all_sessions=wide)
    assert message == refusal_message(r)


def test_refusal_message_enrichment_on_an_empty_wide_retrieval_does_not_crash():
    r = retrieval([("03", "RAG", 0.0)], top1_abs=0.0, ratio=0.0)
    wide = Retrieval(hits=[], top1_abs=0.0, ratio=0.0)
    message = refusal_message(r, all_sessions=wide)
    assert message == refusal_message(r)


def test_gates_module_does_not_import_flow1_retrieve():
    # Kiểm thật (AST), không phải substring trên source: docstring của gates.py
    # nhắc tới "flow1.retrieve" bằng văn xuôi để giải thích RÀNG BUỘC này, nên
    # một check substring ngây thơ sẽ tự báo fail nhầm trên chính lời giải thích
    # của nó. Phải phân biệt "import statement thật" với "nhắc tên trong prose".
    import ast

    import flow1.gates as gates_module

    source = open(gates_module.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)

    assert not any(
        name == "flow1.retrieve" or name.endswith(".retrieve") or name == "retrieve"
        for name in imported_names
    )


# --- Ràng buộc kiến trúc --------------------------------------------------

def test_gate1_is_pure_code_and_never_calls_a_model():
    import flow1.gates as gates_module

    source = open(gates_module.__file__, encoding="utf-8").read()
    gate1_src = source.split("def gate1(")[1].split("\ndef ")[0]
    assert "call" not in gate1_src
    assert "complete_json" not in gate1_src


def test_thresholds_are_plain_numbers_so_cp5_can_point_at_them():
    import flow1.thresholds as thresholds_module

    source = open(thresholds_module.__file__, encoding="utf-8").read()
    assert "def " not in source, "thresholds.py chỉ chứa số, không chứa code"
    assert isinstance(T1_ABS, float) and isinstance(T1_RATIO, float)
    assert 0.0 < AMBIG_BAND < 1.0


def test_decision_is_immutable():
    decision = gate1(strong_single_session())
    assert isinstance(decision, Decision)
    try:
        decision.action = "refuse"
    except Exception:
        return
    raise AssertionError("Decision phải là frozen dataclass")
