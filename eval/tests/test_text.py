from m3_eval.text import keyword_recall, normalize_text


def test_normalize_text_handles_vietnamese_case_and_diacritics() -> None:
    assert normalize_text("  TÓM tắt   buổi HỌC! ") == "tom tat buoi hoc!"


def test_keyword_recall_is_deterministic() -> None:
    assert (
        keyword_recall(
            "Hệ thống dùng semantic retrieval từ transcript.",
            ["semantic", "retrieval", "transcript"],
        )
        == 1.0
    )
    assert keyword_recall("semantic retrieval", []) == 0.0
