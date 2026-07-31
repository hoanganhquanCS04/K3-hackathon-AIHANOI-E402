"""Validate the draft golden set and finalize it only after human approval."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from m3_eval.models import CaseSetReport, EvalCase
from m3_eval.paths import CASES_DIR, DRAFT_CASES_PATH, FINAL_CASES_PATH

RISK_TAGS = ("source_truth", "ambiguity", "out_of_scope", "domain")


def load_cases(path: Path) -> tuple[EvalCase, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("Golden set root must be a JSON array")
    return tuple(EvalCase.model_validate(item) for item in payload)


def _known_chunks() -> dict[str, str]:
    """Return chunk_id -> session_id from the deterministic local loader."""

    from summarizer.loader import LocalParserLoader

    loader = LocalParserLoader()
    return {
        chunk.chunk_id: session.session_id
        for session in loader.list_sessions()
        for chunk in loader.get_session_content(session.session_id)
    }


def validate_case_set(cases: tuple[EvalCase, ...]) -> CaseSetReport:
    structural_errors: list[str] = []
    blockers: list[str] = []
    case_ids = [case.case_id for case in cases]
    duplicates = [key for key, count in Counter(case_ids).items() if count > 1]

    if len(cases) != 20:
        structural_errors.append(f"Expected exactly 20 unique cases, found {len(cases)}")
    if duplicates:
        structural_errors.append(f"Duplicate case IDs: {', '.join(sorted(duplicates))}")

    risk_counts = {tag: sum(tag in case.tags for case in cases) for tag in RISK_TAGS}
    for tag, count in risk_counts.items():
        if count < 2:
            structural_errors.append(f"Risk class {tag!r} has {count} cases; expected >=2")

    chatlog_count = sum(case.source_type == "chatlog" for case in cases)
    if chatlog_count < 10:
        structural_errors.append(f"Only {chatlog_count} chatlog cases; rubric requires at least 10")

    summary_cases = [case for case in cases if case.input_type == "session_summary"]
    summary_ids = {case.input.session_id for case in summary_cases}
    expected_sessions = {f"T{index:02d}" for index in range(1, 7)}
    if summary_ids != expected_sessions:
        structural_errors.append(
            "Summary cases must cover exactly T01-T06; "
            f"received {sorted(value for value in summary_ids if value)}"
        )

    gold_count = sum(len(case.expected.required_ideas) for case in cases)
    if gold_count != 18:
        blockers.append(f"Need exactly 18 human gold ideas; currently {gold_count}")

    known_chunks = _known_chunks()
    for case in cases:
        for idea in case.expected.required_ideas:
            if not idea.accepted_chunk_ids:
                structural_errors.append(
                    f"{case.case_id}/{idea.gold_id}: accepted_chunk_ids is empty"
                )
            if len(idea.required_keywords) < 3:
                structural_errors.append(
                    f"{case.case_id}/{idea.gold_id}: needs at least 3 keywords"
                )
            for citation in idea.accepted_chunk_ids:
                owner = known_chunks.get(citation)
                if owner is None:
                    structural_errors.append(
                        f"{case.case_id}/{idea.gold_id}: unknown citation {citation}"
                    )
                expected_owner = case.input.session_id
                if expected_owner and owner and owner != expected_owner:
                    structural_errors.append(
                        f"{case.case_id}/{idea.gold_id}: citation {citation} "
                        f"belongs to {owner}, not {expected_owner}"
                    )

    approved = sum(case.human_approved for case in cases)
    if approved != len(cases):
        blockers.append(f"Human approval missing for {len(cases) - approved} cases")

    incomplete_gold = [case.case_id for case in summary_cases if not case.human_gold_complete]
    if incomplete_gold:
        blockers.append("Human gold incomplete for summary cases: " + ", ".join(incomplete_gold))

    return CaseSetReport(
        case_count=len(cases),
        chatlog_case_count=chatlog_count,
        approved_case_count=approved,
        gold_idea_count=gold_count,
        risk_counts=risk_counts,
        structural_errors=tuple(structural_errors),
        readiness_blockers=tuple(blockers),
        ready_to_finalize=not structural_errors and not blockers,
    )


def finalize(cases: tuple[EvalCase, ...], report: CaseSetReport) -> tuple[Path, str]:
    if not report.ready_to_finalize:
        raise RuntimeError(
            "Golden set is not ready: "
            + "; ".join((*report.structural_errors, *report.readiness_blockers))
        )
    rendered = (
        json.dumps(
            [case.model_dump(mode="json") for case in cases],
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    FINAL_CASES_PATH.write_text(rendered, encoding="utf-8")
    FINAL_CASES_PATH.with_suffix(".sha256").write_text(digest + "\n", encoding="utf-8")
    return FINAL_CASES_PATH, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DRAFT_CASES_PATH)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()

    cases = load_cases(args.path)
    report = validate_case_set(cases)
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    (CASES_DIR / "readiness-report.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    print(report.model_dump_json(indent=2))
    if args.finalize:
        output, digest = finalize(cases, report)
        print(f"Finalized: {output}")
        print(f"SHA256: {digest}")


if __name__ == "__main__":
    main()
