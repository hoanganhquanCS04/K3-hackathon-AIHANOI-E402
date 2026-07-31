"""Reproduce chatlog evidence counts and prepare a human review sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from m3_eval.paths import (
    CHATLOG_PATH,
    CONFIRMED_LABELS_PATH,
    COUNTING_RULES_PATH,
    EVIDENCE_DIR,
    REVIEW_SAMPLES_PATH,
)
from m3_eval.text import excerpt, normalize_text

HUMAN_FIELDS = ("human_summary", "human_whole_session", "human_failure")
HUMAN_METADATA_FIELDS = ("human_reviewer", "human_confirmed_at", "review_note")


@dataclass(frozen=True)
class TurnPair:
    turn_id: str
    conversation_id: str
    user_id: str
    day_code: str
    student: str
    tutor: str


def _compile_rules(path: Path) -> tuple[dict[str, Any], dict[str, re.Pattern[str]]]:
    rules = json.loads(path.read_text(encoding="utf-8"))
    patterns = {
        name: re.compile(rules[name])
        for name in (
            "summary_request_regex",
            "whole_session_regex",
            "failure_regex",
            "near_miss_regex",
        )
    }
    return rules, patterns


def load_turns(path: Path) -> tuple[list[TurnPair], dict[str, int]]:
    """Group raw message rows into one student+tutor record per turn."""

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    row_count = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_count += 1
            grouped[row["turn_id"]].append(row)

    turns: list[TurnPair] = []
    incomplete = 0
    duplicate_role = 0
    for turn_id, rows in grouped.items():
        students = [row for row in rows if row["role"] == "student"]
        tutors = [row for row in rows if row["role"] == "tutor"]
        if len(students) != 1 or len(tutors) != 1:
            incomplete += int(not students or not tutors)
            duplicate_role += int(len(students) > 1 or len(tutors) > 1)
            continue
        student = students[0]
        tutor = tutors[0]
        turns.append(
            TurnPair(
                turn_id=turn_id,
                conversation_id=student["conversation_id"],
                user_id=student["user_id"],
                day_code=student["day_code"],
                student=student["content"],
                tutor=tutor["content"],
            )
        )

    turns.sort(key=lambda item: item.turn_id)
    diagnostics = {
        "raw_message_rows": row_count,
        "unique_turn_ids": len(grouped),
        "complete_turn_pairs": len(turns),
        "incomplete_turn_ids": incomplete,
        "duplicate_role_turn_ids": duplicate_role,
    }
    return turns, diagnostics


def classify_turn(
    turn: TurnPair,
    patterns: dict[str, re.Pattern[str]],
    *,
    failure_prefix_chars: int = 500,
) -> dict[str, bool]:
    student = normalize_text(turn.student)
    tutor = normalize_text(turn.tutor)
    summary = bool(patterns["summary_request_regex"].search(student))
    whole = summary and bool(patterns["whole_session_regex"].search(student))
    failure = bool(patterns["failure_regex"].search(tutor[:failure_prefix_chars]))
    near_miss = bool(patterns["near_miss_regex"].search(student)) and not summary
    return {
        "regex_summary": summary,
        "regex_whole_session": whole,
        "regex_failure": failure,
        "regex_near_miss": near_miss,
    }


def _safe_rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def build_counts(
    turns: list[TurnPair],
    predictions: dict[str, dict[str, bool]],
    diagnostics: dict[str, int],
) -> dict[str, Any]:
    summary_turns = [turn for turn in turns if predictions[turn.turn_id]["regex_summary"]]
    whole_turns = [turn for turn in turns if predictions[turn.turn_id]["regex_whole_session"]]
    failure_turns = [turn for turn in turns if predictions[turn.turn_id]["regex_failure"]]
    summary_failures = [
        turn for turn in summary_turns if predictions[turn.turn_id]["regex_failure"]
    ]
    whole_failures = [turn for turn in whole_turns if predictions[turn.turn_id]["regex_failure"]]

    all_users = {turn.user_id for turn in turns}
    summary_users = {turn.user_id for turn in summary_turns}
    whole_users = {turn.user_id for turn in whole_turns}

    return {
        **diagnostics,
        "unique_users": len(all_users),
        "summary_request_turns": len(summary_turns),
        "summary_request_users": len(summary_users),
        "summary_user_rate": _safe_rate(len(summary_users), len(all_users)),
        "whole_session_request_turns": len(whole_turns),
        "whole_session_request_users": len(whole_users),
        "whole_session_user_rate": _safe_rate(len(whole_users), len(all_users)),
        "all_failure_turns": len(failure_turns),
        "baseline_failure_rate": _safe_rate(len(failure_turns), len(turns)),
        "summary_failure_turns": len(summary_failures),
        "summary_failure_rate": _safe_rate(len(summary_failures), len(summary_turns)),
        "whole_session_failure_turns": len(whole_failures),
        "whole_session_failure_rate": _safe_rate(len(whole_failures), len(whole_turns)),
    }


def _stable_order(turn: TurnPair, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{turn.turn_id}".encode()).hexdigest()


def _existing_human_labels(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["turn_id"]: {
                field: row.get(field, "") for field in (*HUMAN_FIELDS, *HUMAN_METADATA_FIELDS)
            }
            for row in csv.DictReader(handle)
        }


def select_review_samples(
    turns: list[TurnPair],
    predictions: dict[str, dict[str, bool]],
    *,
    target: int,
) -> list[tuple[str, TurnPair]]:
    """Choose deterministic, distinct positive/failure/near-miss samples."""

    selected: list[tuple[str, TurnPair]] = []
    used: set[str] = set()

    def take(bucket: str, candidates: list[TurnPair], count: int) -> None:
        ordered = sorted(candidates, key=lambda item: _stable_order(item, bucket))
        for turn in ordered:
            if turn.turn_id in used:
                continue
            selected.append((bucket, turn))
            used.add(turn.turn_id)
            if sum(name == bucket for name, _ in selected) >= count:
                break

    take(
        "whole_session_positive",
        [turn for turn in turns if predictions[turn.turn_id]["regex_whole_session"]],
        10,
    )
    take(
        "summary_positive",
        [turn for turn in turns if predictions[turn.turn_id]["regex_summary"]],
        10,
    )
    take(
        "failure_positive",
        [turn for turn in turns if predictions[turn.turn_id]["regex_failure"]],
        10,
    )
    take(
        "near_miss",
        [turn for turn in turns if predictions[turn.turn_id]["regex_near_miss"]],
        10,
    )

    if len(selected) < target:
        remaining = sorted(turns, key=lambda item: _stable_order(item, "fill"))
        for turn in remaining:
            if turn.turn_id in used:
                continue
            selected.append(("fill", turn))
            used.add(turn.turn_id)
            if len(selected) == target:
                break
    return selected[:target]


def _fixed_review_samples(
    path: Path,
    turns: list[TurnPair],
    *,
    target: int,
) -> list[tuple[str, TurnPair]] | None:
    """Reuse the first deterministic sample so rule revisions remain comparable."""

    if not path.exists():
        return None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != target:
        return None
    by_id = {turn.turn_id: turn for turn in turns}
    if any(row["turn_id"] not in by_id for row in rows):
        return None
    return [(row["sample_bucket"], by_id[row["turn_id"]]) for row in rows]


def write_review_samples(
    samples: list[tuple[str, TurnPair]],
    predictions: dict[str, dict[str, bool]],
    path: Path,
) -> None:
    existing = _existing_human_labels(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_bucket",
        "turn_id",
        "conversation_id",
        "user_id",
        "day_code",
        "student_excerpt",
        "tutor_excerpt",
        "regex_summary",
        "regex_whole_session",
        "regex_failure",
        *HUMAN_FIELDS,
        *HUMAN_METADATA_FIELDS,
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for bucket, turn in samples:
            prediction = predictions[turn.turn_id]
            labels = existing.get(turn.turn_id, {})
            writer.writerow(
                {
                    "sample_bucket": bucket,
                    "turn_id": turn.turn_id,
                    "conversation_id": turn.conversation_id,
                    "user_id": turn.user_id,
                    "day_code": turn.day_code,
                    "student_excerpt": excerpt(turn.student),
                    "tutor_excerpt": excerpt(turn.tutor),
                    "regex_summary": str(prediction["regex_summary"]).lower(),
                    "regex_whole_session": str(prediction["regex_whole_session"]).lower(),
                    "regex_failure": str(prediction["regex_failure"]).lower(),
                    **{field: labels.get(field, "") for field in HUMAN_FIELDS},
                    **{field: labels.get(field, "") for field in HUMAN_METADATA_FIELDS},
                }
            )


def apply_confirmed_labels(
    review_path: Path,
    labels_path: Path = CONFIRMED_LABELS_PATH,
) -> None:
    """Apply a versioned label decision only after explicit user confirmation."""

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    reviewer = payload["reviewer"].strip()
    confirmed_at = payload["confirmed_at"].strip()
    labels = {item["turn_id"]: item for item in payload["labels"]}
    if not reviewer or not confirmed_at:
        raise ValueError("Confirmed labels require reviewer and confirmed_at")

    with review_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    sample_ids = {row["turn_id"] for row in rows}
    if sample_ids != set(labels):
        missing = sorted(sample_ids - set(labels))
        extra = sorted(set(labels) - sample_ids)
        raise ValueError(
            f"Confirmed labels do not match current sample; missing={missing}, extra={extra}"
        )

    for field in HUMAN_METADATA_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    for row in rows:
        decision = labels[row["turn_id"]]
        for field in HUMAN_FIELDS:
            value = decision[field]
            if value not in {"yes", "no"}:
                raise ValueError(f"{row['turn_id']}/{field} must be yes or no")
            row[field] = value
        row["human_reviewer"] = reviewer
        row["human_confirmed_at"] = confirmed_at
        row["review_note"] = decision.get(
            "review_note",
            "AI pre-label reviewed and explicitly confirmed by M3 owner.",
        )

    with review_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_human(value: str) -> bool | None:
    normalized = value.strip().casefold()
    if normalized in {"yes", "y", "true", "1", "có", "co"}:
        return True
    if normalized in {"no", "n", "false", "0", "không", "khong"}:
        return False
    return None


def review_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"reviewed_rows": 0, "complete_rows": 0, "metrics": {}}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    mapping = {
        "summary": ("regex_summary", "human_summary"),
        "whole_session": ("regex_whole_session", "human_whole_session"),
        "failure": ("regex_failure", "human_failure"),
    }
    metrics: dict[str, Any] = {}
    for name, (predicted_field, human_field) in mapping.items():
        confusion = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "labeled": 0}
        for row in rows:
            human = _parse_human(row.get(human_field, ""))
            if human is None:
                continue
            predicted = row[predicted_field].strip().casefold() == "true"
            confusion["labeled"] += 1
            if predicted and human:
                confusion["tp"] += 1
            elif predicted and not human:
                confusion["fp"] += 1
            elif not predicted and human:
                confusion["fn"] += 1
            else:
                confusion["tn"] += 1
        tp = confusion["tp"]
        fp = confusion["fp"]
        fn = confusion["fn"]
        tn = confusion["tn"]
        confusion["precision"] = _safe_rate(tp, tp + fp)
        confusion["recall"] = _safe_rate(tp, tp + fn)
        confusion["false_positive_rate"] = _safe_rate(fp, fp + tn)
        metrics[name] = confusion

    complete_rows = sum(
        all(_parse_human(row.get(field, "")) is not None for field in HUMAN_FIELDS)
        and bool(row.get("human_reviewer", "").strip())
        and bool(row.get("human_confirmed_at", "").strip())
        for row in rows
    )
    return {
        "reviewed_rows": len(rows),
        "complete_rows": complete_rows,
        "review_complete": bool(rows) and complete_rows == len(rows),
        "reviewers": sorted(
            {
                row.get("human_reviewer", "").strip()
                for row in rows
                if row.get("human_reviewer", "").strip()
            }
        ),
        "confirmed_at": sorted(
            {
                row.get("human_confirmed_at", "").strip()
                for row in rows
                if row.get("human_confirmed_at", "").strip()
            }
        ),
        "metrics": metrics,
    }


def _format_percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    review = report["human_review"]
    lines = [
        "# Evidence mining report — M3",
        "",
        f"- Sinh lúc: `{report['generated_at']}`",
        f"- Rules: `{report['rules_version']}` ({report['rules_status']})",
        f"- Đơn vị đếm: `{report['count_unit']}`",
        "",
        "## Số đếm máy",
        "",
        f"- Raw rows: **{counts['raw_message_rows']}**",
        f"- Complete turns: **{counts['complete_turn_pairs']}**",
        f"- Unique users: **{counts['unique_users']}**",
        (
            f"- Summary requests: **{counts['summary_request_turns']} turns / "
            f"{counts['summary_request_users']} users**"
        ),
        (
            f"- Whole-session requests: **{counts['whole_session_request_turns']} "
            f"turns / {counts['whole_session_request_users']} users**"
        ),
        (f"- Summary failure rate: **{_format_percent(counts['summary_failure_rate'])}**"),
        (
            f"- Whole-session failure rate: "
            f"**{_format_percent(counts['whole_session_failure_rate'])}**"
        ),
        (f"- Baseline failure rate: **{_format_percent(counts['baseline_failure_rate'])}**"),
        "",
        "## Kiểm tra tay",
        "",
        (f"- Mẫu đã điền đủ ba nhãn: **{review['complete_rows']}/{review['reviewed_rows']}**"),
    ]
    if not review["review_complete"]:
        lines += [
            "- Trạng thái: **PENDING HUMAN REVIEW**",
            "- Không dùng các số phía trên làm số chính thức trong spec/slide.",
        ]
    else:
        lines.append("- Trạng thái: **REVIEW COMPLETE**")
        lines.append(f"- Reviewer: **{', '.join(review['reviewers'])}**")
        for name, metric in review["metrics"].items():
            lines.append(
                f"- `{name}` precision={_format_percent(metric['precision'])}, "
                f"recall={_format_percent(metric['recall'])}, "
                f"FPR={_format_percent(metric['false_positive_rate'])}"
            )
    lines += [
        "",
        "## Cách tái tạo",
        "",
        "```powershell",
        "cd eval",
        "uv run python -m m3_eval.mine_chatlog",
        "```",
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    chatlog_path: Path = CHATLOG_PATH,
    rules_path: Path = COUNTING_RULES_PATH,
    review_path: Path = REVIEW_SAMPLES_PATH,
) -> dict[str, Any]:
    if not chatlog_path.exists():
        raise FileNotFoundError(f"Chatlog not found: {chatlog_path}")
    rules, patterns = _compile_rules(rules_path)
    turns, diagnostics = load_turns(chatlog_path)
    predictions = {
        turn.turn_id: classify_turn(
            turn,
            patterns,
            failure_prefix_chars=int(rules.get("failure_prefix_chars", 500)),
        )
        for turn in turns
    }
    counts = build_counts(turns, predictions, diagnostics)
    target = int(rules["review_sample_target"])
    samples = _fixed_review_samples(review_path, turns, target=target)
    if samples is None:
        samples = select_review_samples(turns, predictions, target=target)
    write_review_samples(samples, predictions, review_path)
    review = review_metrics(review_path)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(chatlog_path),
        "rules_version": rules["rules_version"],
        "rules_status": rules.get("rules_status", "draft"),
        "count_unit": rules["count_unit"],
        "review_sample_policy": rules.get("review_sample_policy", ""),
        "review_instructions": rules.get("review_instructions", ""),
        "rules": {
            key: rules[key]
            for key in (
                "summary_request_regex",
                "whole_session_regex",
                "failure_regex",
            )
        },
        "counts": counts,
        "human_review": review,
        "official_numbers_ready": (
            review["review_complete"] and rules.get("rules_status") == "locked"
        ),
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "evidence-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "evidence-report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chatlog", type=Path, default=CHATLOG_PATH)
    parser.add_argument("--rules", type=Path, default=COUNTING_RULES_PATH)
    parser.add_argument("--review", type=Path, default=REVIEW_SAMPLES_PATH)
    parser.add_argument(
        "--apply-confirmed-labels",
        type=Path,
        help="Apply a versioned user-confirmed label file, then regenerate report.",
    )
    args = parser.parse_args()
    report = run(
        chatlog_path=args.chatlog,
        rules_path=args.rules,
        review_path=args.review,
    )
    if args.apply_confirmed_labels:
        apply_confirmed_labels(args.review, args.apply_confirmed_labels)
        report = run(
            chatlog_path=args.chatlog,
            rules_path=args.rules,
            review_path=args.review,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
