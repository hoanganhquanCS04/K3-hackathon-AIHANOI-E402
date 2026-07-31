import csv
import json
from pathlib import Path

from m3_eval.mine_chatlog import (
    TurnPair,
    _compile_rules,
    apply_confirmed_labels,
    build_counts,
    classify_turn,
    load_turns,
    review_metrics,
)


def _write_chatlog(path: Path) -> None:
    fieldnames = [
        "conversation_id",
        "turn_id",
        "user_id",
        "day_code",
        "role",
        "content",
    ]
    rows = [
        {
            "conversation_id": "C1",
            "turn_id": "T1",
            "user_id": "U1",
            "day_code": "D1",
            "role": "student",
            "content": "Tóm tắt cả buổi học hôm nay",
        },
        {
            "conversation_id": "C1",
            "turn_id": "T1",
            "user_id": "U1",
            "day_code": "D1",
            "role": "tutor",
            "content": "Xin lỗi, tôi không thể truy cập toàn bộ buổi học.",
        },
        {
            "conversation_id": "C2",
            "turn_id": "T2",
            "user_id": "U2",
            "day_code": "D1",
            "role": "student",
            "content": "Giải thích khái niệm RAG",
        },
        {
            "conversation_id": "C2",
            "turn_id": "T2",
            "user_id": "U2",
            "day_code": "D1",
            "role": "tutor",
            "content": "RAG là retrieval augmented generation.",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_rules(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "summary_request_regex": r"\btom tat\b",
                "whole_session_regex": r"\bca buoi\b",
                "failure_regex": r"\bxin loi\b.*\bkhong the\b",
                "near_miss_regex": r"\bgiai thich\b",
            }
        ),
        encoding="utf-8",
    )


def test_load_classify_and_count_turn_pairs(tmp_path: Path) -> None:
    chatlog = tmp_path / "chatlog.csv"
    rules_path = tmp_path / "rules.json"
    _write_chatlog(chatlog)
    _write_rules(rules_path)

    turns, diagnostics = load_turns(chatlog)
    _, patterns = _compile_rules(rules_path)
    predictions = {turn.turn_id: classify_turn(turn, patterns) for turn in turns}
    counts = build_counts(turns, predictions, diagnostics)

    assert diagnostics["raw_message_rows"] == 4
    assert diagnostics["complete_turn_pairs"] == 2
    assert predictions["T1"] == {
        "regex_summary": True,
        "regex_whole_session": True,
        "regex_failure": True,
        "regex_near_miss": False,
    }
    assert counts["summary_request_turns"] == 1
    assert counts["whole_session_request_turns"] == 1
    assert counts["summary_failure_rate"] == 1.0


def test_summary_regex_does_not_match_tuy_chinh_substring(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.json"
    _write_rules(rules_path)
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    payload["summary_request_regex"] = r"\b(?:tom\s*tat|y\s*chinh)\b"
    rules_path.write_text(json.dumps(payload), encoding="utf-8")
    _, patterns = _compile_rules(rules_path)
    turn = TurnPair(
        turn_id="T1",
        conversation_id="C1",
        user_id="U1",
        day_code="D1",
        student="Mở PDF để tùy chỉnh mức độ zoom",
        tutor="Bạn có thể mở bằng phần mềm đọc PDF.",
    )

    prediction = classify_turn(turn, patterns)

    assert prediction["regex_summary"] is False


def test_failure_regex_only_scans_response_prefix(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.json"
    _write_rules(rules_path)
    _, patterns = _compile_rules(rules_path)
    turn = TurnPair(
        turn_id="T1",
        conversation_id="C1",
        user_id="U1",
        day_code="D1",
        student="Cho ví dụ",
        tutor=("Đây là câu trả lời hợp lệ. " * 30) + "Nếu không tìm thấy thì thử lại.",
    )

    prediction = classify_turn(turn, patterns, failure_prefix_chars=100)

    assert prediction["regex_failure"] is False


def test_apply_confirmed_labels_records_human_provenance(tmp_path: Path) -> None:
    review_path = tmp_path / "review.csv"
    labels_path = tmp_path / "labels.json"
    review_path.write_text(
        "turn_id,regex_summary,regex_whole_session,regex_failure,"
        "human_summary,human_whole_session,human_failure\n"
        "T1,true,true,false,,,\n",
        encoding="utf-8",
    )
    labels_path.write_text(
        json.dumps(
            {
                "reviewer": "M3 owner",
                "confirmed_at": "2026-07-30",
                "labels": [
                    {
                        "turn_id": "T1",
                        "human_summary": "yes",
                        "human_whole_session": "yes",
                        "human_failure": "no",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    apply_confirmed_labels(review_path, labels_path)
    metrics = review_metrics(review_path)

    assert metrics["review_complete"] is True
    assert metrics["reviewers"] == ["M3 owner"]
