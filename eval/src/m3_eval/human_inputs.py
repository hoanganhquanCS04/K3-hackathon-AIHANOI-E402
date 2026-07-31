"""Prepare and apply the two CSV files that require human judgment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from m3_eval.cases import load_cases, validate_case_set
from m3_eval.paths import (
    CASES_DIR,
    CONFIRMED_CASE_APPROVALS_PATH,
    DRAFT_CASES_PATH,
    MANUAL_REVIEW_DIR,
)

GOLD_TEMPLATE = MANUAL_REVIEW_DIR / "gold-ideas.csv"
APPROVAL_TEMPLATE = MANUAL_REVIEW_DIR / "case-approval.csv"


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    *,
    force: bool,
) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare(path: Path = DRAFT_CASES_PATH, *, force: bool = False) -> None:
    cases = load_cases(path)
    gold_rows: list[dict[str, str]] = []
    for case in cases:
        if case.input_type != "session_summary":
            continue
        for index in range(1, 4):
            gold_rows.append(
                {
                    "session_id": case.input.session_id or "",
                    "gold_id": f"{case.input.session_id}-GOLD-{index:02d}",
                    "gold_idea": "",
                    "accepted_chunk_ids": "",
                    "required_keywords": "",
                    "reviewer": "",
                    "approved": "",
                    "note": "",
                }
            )
    _write_csv(
        GOLD_TEMPLATE,
        [
            "session_id",
            "gold_id",
            "gold_idea",
            "accepted_chunk_ids",
            "required_keywords",
            "reviewer",
            "approved",
            "note",
        ],
        gold_rows,
        force=force,
    )

    approval_rows = [
        {
            "case_id": case.case_id,
            "session_id": case.input.session_id or "",
            "input": case.input.query or case.input.session_id or "",
            "expected_status": case.expected.status,
            "expected_notes": case.expected.notes,
            "approved": "",
            "reviewer": "",
            "review_note": "",
        }
        for case in cases
    ]
    _write_csv(
        APPROVAL_TEMPLATE,
        [
            "case_id",
            "session_id",
            "input",
            "expected_status",
            "expected_notes",
            "approved",
            "reviewer",
            "review_note",
        ],
        approval_rows,
        force=force,
    )


def _yes(value: str) -> bool:
    return value.strip().casefold() in {"yes", "y", "true", "1", "có", "co"}


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Human input file not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def apply_confirmed_case_approvals(
    confirmation_path: Path = CONFIRMED_CASE_APPROVALS_PATH,
    *,
    draft_path: Path = DRAFT_CASES_PATH,
    approval_path: Path = APPROVAL_TEMPLATE,
) -> None:
    """Import the M3 owner's explicit approval with an auditable snapshot."""

    confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    current_hash = hashlib.sha256(draft_path.read_bytes()).hexdigest()
    if current_hash != confirmation["draft_sha256"]:
        raise ValueError(
            "Golden-set draft changed after confirmation; ask the reviewer to approve it again"
        )

    approvals = {item["case_id"]: item["expected_status"] for item in confirmation["approvals"]}
    with approval_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    row_ids = {row["case_id"] for row in rows}
    if row_ids != set(approvals):
        raise ValueError("Confirmed case IDs do not match case-approval.csv")
    for row in rows:
        expected_status = approvals[row["case_id"]]
        if row["expected_status"] != expected_status:
            raise ValueError(
                f"{row['case_id']} status changed from confirmed value {expected_status}"
            )
        row["approved"] = "yes"
        row["reviewer"] = confirmation["reviewer"]
        row["review_note"] = confirmation["statement"]

    with approval_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def apply_human_inputs(path: Path = DRAFT_CASES_PATH) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    approvals = {row["case_id"]: row for row in _read_rows(APPROVAL_TEMPLATE)}
    gold_by_session: dict[str, list[dict[str, str]]] = {}
    for row in _read_rows(GOLD_TEMPLATE):
        gold_by_session.setdefault(row["session_id"], []).append(row)

    for case in payload:
        approval = approvals.get(case["case_id"])
        case["human_approved"] = bool(
            approval and _yes(approval.get("approved", "")) and approval.get("reviewer", "").strip()
        )

        if case["input_type"] != "session_summary":
            continue
        session_id = case["input"]["session_id"]
        rows = gold_by_session.get(session_id, [])
        valid_rows = [
            row
            for row in rows
            if row.get("gold_idea", "").strip()
            and row.get("accepted_chunk_ids", "").strip()
            and len([item for item in row.get("required_keywords", "").split("|") if item.strip()])
            >= 3
            and row.get("reviewer", "").strip()
            and _yes(row.get("approved", ""))
        ]
        case["expected"]["required_ideas"] = [
            {
                "gold_id": row["gold_id"].strip(),
                "text": row["gold_idea"].strip(),
                "accepted_chunk_ids": [
                    item for item in row["accepted_chunk_ids"].replace(",", " ").split() if item
                ],
                "required_keywords": [
                    item.strip() for item in row["required_keywords"].split("|") if item.strip()
                ],
            }
            for row in valid_rows
        ]
        case["human_gold_complete"] = len(valid_rows) == 3

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = validate_case_set(load_cases(path))
    (CASES_DIR / "readiness-report.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(report.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--apply-confirmed-case-approvals",
        type=Path,
        help="Apply a versioned M3-owner approval snapshot, then update the draft.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--path", type=Path, default=DRAFT_CASES_PATH)
    args = parser.parse_args()
    if not args.prepare and not args.apply and not args.apply_confirmed_case_approvals:
        parser.error("Choose --prepare, --apply or --apply-confirmed-case-approvals")
    if args.prepare:
        prepare(args.path, force=args.force)
        print(f"Prepared: {GOLD_TEMPLATE}")
        print(f"Prepared: {APPROVAL_TEMPLATE}")
    if args.apply:
        apply_human_inputs(args.path)
    if args.apply_confirmed_case_approvals:
        apply_confirmed_case_approvals(
            args.apply_confirmed_case_approvals,
            draft_path=args.path,
        )
        apply_human_inputs(args.path)


if __name__ == "__main__":
    main()
