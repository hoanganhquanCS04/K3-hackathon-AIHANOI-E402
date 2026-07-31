"""Run deterministic technical checks over the M2 artifacts and guardrail surface."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from m3_eval.cases import load_cases
from m3_eval.models import CheckResult, EvalCase, EvalResult, RunSummary
from m3_eval.paths import (
    DRAFT_CASES_PATH,
    MANUAL_REVIEW_DIR,
    REPOSITORY_ROOT,
    RESULTS_DIR,
    SUMMARY_ARTIFACT_DIR,
)
from m3_eval.text import excerpt, keyword_recall

MANUAL_BOOLEAN_VALUES = {"yes": True, "no": False}


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _source_catalog():
    from summarizer.loader import LocalParserLoader

    loader = LocalParserLoader()
    sessions = {item.session_id: item for item in loader.list_sessions()}
    sections: dict[str, tuple] = {}
    chunks: dict[str, Any] = {}
    for session_id in sessions:
        refs = loader.get_session_sections(session_id)
        sections[session_id] = refs
        for chunk in loader.get_session_content(session_id):
            chunks[chunk.chunk_id] = chunk
    return loader, sessions, sections, chunks


def _manual_value(value: str) -> bool | None:
    return MANUAL_BOOLEAN_VALUES.get(value.strip().casefold())


def _load_manual_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["claim_id"]): row for row in csv.DictReader(handle)}


def _manual_case_status(
    case_id: str,
    claim_ids: list[str],
    manual_rows: dict[tuple[str, str], dict[str, str]],
) -> tuple[bool | None, list[str]]:
    blockers: list[str] = []
    values: list[bool] = []
    for claim_id in claim_ids:
        row = manual_rows.get((case_id, claim_id))
        if row is None:
            blockers.append(f"missing manual review row {claim_id}")
            continue
        supports = _manual_value(row.get("supports_claim", ""))
        reversed_meaning = _manual_value(row.get("reverses_meaning", ""))
        reviewer = row.get("reviewer", "").strip()
        if supports is None or reversed_meaning is None or not reviewer:
            blockers.append(f"manual review incomplete for {claim_id}")
            continue
        values.append(supports and not reversed_meaning)
    if blockers:
        return None, blockers
    return all(values), blockers


def _check(
    name: str,
    passed: bool | None,
    *,
    observed: Any = None,
    expected: Any = None,
    detail: str = "",
) -> CheckResult:
    return CheckResult(
        name=name,
        passed=passed,
        observed=observed,
        expected=expected,
        detail=detail,
    )


def _evaluate_gold(
    case: EvalCase,
    key_points: list[dict[str, Any]],
) -> CheckResult:
    ideas = case.expected.required_ideas
    if not ideas:
        return _check(
            "gold_idea_recall",
            None,
            observed=0,
            expected=3 if case.input_type == "session_summary" else None,
            detail="Waiting for human gold ideas from M5.",
        )

    matched: list[str] = []
    for idea in ideas:
        accepted = set(idea.accepted_chunk_ids)
        for point in key_points:
            citations = set(point.get("citations", []))
            recall = keyword_recall(point.get("text", ""), list(idea.required_keywords))
            if citations.intersection(accepted) and recall >= 0.6:
                matched.append(idea.gold_id)
                break
    return _check(
        "gold_idea_recall",
        len(matched) == len(ideas),
        observed={"matched": matched, "count": len(matched)},
        expected={"gold_ids": [idea.gold_id for idea in ideas], "count": len(ideas)},
        detail="Deterministic match requires accepted citation and >=60% gold keywords.",
    )


def evaluate_summary_case(
    case: EvalCase,
    *,
    sessions: dict[str, Any],
    sections: dict[str, tuple],
    chunks: dict[str, Any],
    manual_rows: dict[tuple[str, str], dict[str, str]],
) -> tuple[EvalResult, list[dict[str, str]]]:
    session_id = case.input.session_id or ""
    path = SUMMARY_ARTIFACT_DIR / session_id / "session.json"
    blockers: list[str] = []
    review_rows: list[dict[str, str]] = []

    if not path.exists():
        return (
            EvalResult(
                case_id=case.case_id,
                actual_status="missing_artifact",
                technical_pass=False,
                official_pass=None,
                checks=(
                    _check(
                        "status",
                        False,
                        observed="missing_artifact",
                        expected=case.expected.status,
                    ),
                ),
                blockers=(f"M2 artifact missing: {path}",),
            ),
            review_rows,
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (
            EvalResult(
                case_id=case.case_id,
                actual_status="invalid_artifact",
                technical_pass=False,
                official_pass=None,
                checks=(),
                blockers=("Artifact cannot be parsed.",),
                error=str(error),
            ),
            review_rows,
        )

    key_points = payload.get("key_points", [])
    source_chunks = {
        chunk_id: chunk for chunk_id, chunk in chunks.items() if chunk.session_id == session_id
    }
    citations = [citation for point in key_points for citation in point.get("citations", [])]
    fake = sorted({citation for citation in citations if citation not in chunks})
    cross_session = sorted(
        {
            citation
            for citation in citations
            if citation in chunks and chunks[citation].session_id != session_id
        }
    )
    student_points = []
    for index, point in enumerate(key_points, start=1):
        cited = [chunks[c] for c in point.get("citations", []) if c in chunks]
        if any(chunk.speaker_role == "student" for chunk in cited):
            student_points.append(index)

    source_unclear = [chunk for chunk in source_chunks.values() if chunk.has_unclear]
    warnings = payload.get("warnings", [])
    coverage = payload.get("coverage", {})
    expected_sections = len(sections.get(session_id, ()))

    checks = [
        _check("status", True, observed="ok", expected=case.expected.status),
        _check(
            "session_id",
            payload.get("session_id") == session_id,
            observed=payload.get("session_id"),
            expected=session_id,
        ),
        _check(
            "exactly_five_key_points",
            (len(key_points) == 5 if case.expected.must_have_exactly_five_points else True),
            observed=len(key_points),
            expected=5 if case.expected.must_have_exactly_five_points else "not enforced",
        ),
        _check(
            "citation_valid",
            not fake and not cross_session,
            observed={"fake": fake, "cross_session": cross_session},
            expected={"fake": [], "cross_session": []},
        ),
        _check(
            "student_misattribution",
            len(student_points) <= case.expected.max_student_misattributions,
            observed=student_points,
            expected=f"<= {case.expected.max_student_misattributions}",
            detail="Main key point cites at least one student chunk.",
        ),
        _check(
            "unclear_warning",
            (bool(warnings) if case.expected.must_warn_unclear and source_unclear else True),
            observed={
                "source_unclear_chunks": len(source_unclear),
                "warnings": len(warnings),
            },
            expected="warning present when source has unclear chunks",
        ),
        _check(
            "coverage_total_chunks",
            coverage.get("total_chunks") == len(source_chunks),
            observed=coverage.get("total_chunks"),
            expected=len(source_chunks),
        ),
        _check(
            "coverage_total_sections",
            coverage.get("total_sections") == expected_sections,
            observed=coverage.get("total_sections"),
            expected=expected_sections,
        ),
        _evaluate_gold(case, key_points),
    ]

    for index, point in enumerate(key_points, start=1):
        claim_id = f"KP-{index:02d}"
        citations_for_claim = point.get("citations", [])
        quotes = [
            f"[{citation}] {excerpt(chunks[citation].text, 220)}"
            for citation in citations_for_claim
            if citation in chunks
        ]
        review_rows.append(
            {
                "case_id": case.case_id,
                "session_id": session_id,
                "claim_id": claim_id,
                "claim": point.get("text", ""),
                "citations": " ".join(citations_for_claim),
                "source_excerpts": " | ".join(quotes),
                "supports_claim": "",
                "reverses_meaning": "",
                "reviewer": "",
                "review_note": "",
            }
        )

    manual_status, manual_blockers = _manual_case_status(
        case.case_id,
        [row["claim_id"] for row in review_rows],
        manual_rows,
    )
    checks.append(
        _check(
            "manual_traceability",
            manual_status,
            expected="all claims supported and no reversed meaning",
            detail="; ".join(manual_blockers),
        )
    )

    decisive = [check for check in checks if check.passed is not None]
    technical_pass = all(check.passed for check in decisive if check.name != "manual_traceability")

    if not case.human_approved:
        blockers.append("Case expectation has not been approved by a human.")
    if not case.human_gold_complete:
        blockers.append("Human gold ideas are incomplete.")
    blockers.extend(manual_blockers)

    official_pass: bool | None = None
    gold_check = next(check for check in checks if check.name == "gold_idea_recall")
    if (
        case.human_approved
        and case.human_gold_complete
        and gold_check.passed is not None
        and manual_status is not None
    ):
        official_pass = technical_pass and bool(gold_check.passed) and manual_status

    return (
        EvalResult(
            case_id=case.case_id,
            actual_status="ok",
            technical_pass=technical_pass,
            official_pass=official_pass,
            checks=tuple(checks),
            blockers=tuple(blockers),
        ),
        review_rows,
    )


def evaluate_unknown_session(
    case: EvalCase,
    *,
    loader: Any,
) -> EvalResult:
    session_id = case.input.session_id or ""
    try:
        loader.get_session(session_id)
        actual = "ok"
    except KeyError:
        actual = "refused"
    passed = actual == case.expected.status
    official = passed if case.human_approved else None
    blockers = () if case.human_approved else ("Case expectation needs human approval.",)
    return EvalResult(
        case_id=case.case_id,
        actual_status=actual,
        technical_pass=passed,
        official_pass=official,
        checks=(
            _check(
                "status",
                passed,
                observed=actual,
                expected=case.expected.status,
            ),
        ),
        blockers=blockers,
    )


@lru_cache(maxsize=1)
def _product_rules() -> ModuleType:
    """Load the same deterministic router used by the Streamlit product."""

    path = REPOSITORY_ROOT / "codebase" / "stubs.py"
    spec = importlib.util.spec_from_file_location("m3_product_rules", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load product router: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def _live_product() -> ModuleType:
    """Load codebase/live.py only after its search marker has been removed."""

    codebase_dir = REPOSITORY_ROOT / "codebase"
    path = codebase_dir / "live.py"
    spec = importlib.util.spec_from_file_location("m3_live_product", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load live product: {path}")
    sys.path.insert(0, str(codebase_dir))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(codebase_dir))
    return module


def _evaluate_live_query(
    case: EvalCase,
    *,
    chunks: dict[str, Any],
    manual_rows: dict[tuple[str, str], dict[str, str]],
) -> tuple[EvalResult, list[dict[str, str]]]:
    """Call the future real answer_query adapter and validate its structured output."""

    session_id = case.input.session_id or ""
    review_rows: list[dict[str, str]] = []
    try:
        live = _live_product()
        sessions = live.load_outline()
        ui_session_id = session_id.removeprefix("T")
        session = live.get_session(sessions, ui_session_id)
        if session is None:
            raise KeyError(f"Session not found in product outline: {session_id}")
        payload = live.answer_query(session, case.input.query or "")
    except Exception as error:  # noqa: BLE001 - product errors must become eval results
        return (
            EvalResult(
                case_id=case.case_id,
                actual_status="execution_error",
                technical_pass=False,
                official_pass=None,
                blockers=("The live query adapter raised an error.",),
                error=f"{type(error).__name__}: {error}",
            ),
            review_rows,
        )

    status_map = {"answered": "ok"}
    actual = status_map.get(payload.get("status"), payload.get("status", "invalid_output"))
    claims = payload.get("claims", [])
    citations = [
        citation for claim in claims for citation in claim.get("cite", claim.get("citations", []))
    ]
    fake = sorted({citation for citation in citations if citation not in chunks})
    cross_session = sorted(
        {
            citation
            for citation in citations
            if citation in chunks and chunks[citation].session_id != session_id
        }
    )
    student_claims: list[int] = []
    for index, claim in enumerate(claims, start=1):
        claim_citations = claim.get("cite", claim.get("citations", []))
        if any(
            chunks[citation].speaker_role == "student"
            for citation in claim_citations
            if citation in chunks
        ):
            student_claims.append(index)
        review_rows.append(
            {
                "case_id": case.case_id,
                "session_id": session_id,
                "claim_id": f"CLAIM-{index:02d}",
                "claim": claim.get("claim", claim.get("text", "")) or "",
                "citations": " ".join(claim_citations),
                "source_excerpts": " | ".join(
                    f"[{citation}] {excerpt(chunks[citation].text, 220)}"
                    for citation in claim_citations
                    if citation in chunks
                ),
                "supports_claim": "",
                "reverses_meaning": "",
                "reviewer": "",
                "review_note": "",
            }
        )

    claim_ids = [row["claim_id"] for row in review_rows]
    if claim_ids:
        manual_status, manual_blockers = _manual_case_status(
            case.case_id,
            claim_ids,
            manual_rows,
        )
    else:
        manual_status, manual_blockers = True, []

    checks = [
        _check(
            "status",
            actual == case.expected.status,
            observed=actual,
            expected=case.expected.status,
        ),
        _check(
            "citation_valid",
            not fake and not cross_session,
            observed={"fake": fake, "cross_session": cross_session},
            expected={"fake": [], "cross_session": []},
        ),
        _check(
            "student_misattribution",
            len(student_claims) <= case.expected.max_student_misattributions,
            observed=student_claims,
            expected=f"<= {case.expected.max_student_misattributions}",
        ),
        _check(
            "manual_traceability",
            manual_status,
            expected="all claims supported and no reversed meaning",
            detail="; ".join(manual_blockers),
        ),
    ]
    technical_pass = all(
        check.passed
        for check in checks
        if check.name != "manual_traceability" and check.passed is not None
    )
    blockers = list(manual_blockers)
    if not case.human_approved:
        blockers.append("Case expectation needs human approval.")
    official = (
        technical_pass and manual_status
        if case.human_approved and manual_status is not None
        else None
    )
    return (
        EvalResult(
            case_id=case.case_id,
            actual_status=actual,
            technical_pass=technical_pass,
            official_pass=official,
            checks=tuple(checks),
            blockers=tuple(blockers),
        ),
        review_rows,
    )


def evaluate_query_case(
    case: EvalCase,
    *,
    chunks: dict[str, Any] | None = None,
    manual_rows: dict[tuple[str, str], dict[str, str]] | None = None,
) -> tuple[EvalResult, list[dict[str, str]]]:
    """Evaluate real code-only gates and refuse to score the unimplemented search."""

    chunks = chunks or {}
    manual_rows = manual_rows or {}
    rules = _product_rules()
    query = case.input.query or ""
    route_result = rules.route(query, {})
    intent = route_result.get("intent")
    marker_path = REPOSITORY_ROOT / "codebase" / "live.py"
    source = marker_path.read_text(encoding="utf-8") if marker_path.exists() else ""
    is_stub = "CHƯA THẬT" in source and "answer_query" in source

    if intent in {"logistics", "ngoai_pham_vi"}:
        actual = "out_of_scope"
        detail = f"Code gate route() returned intent={intent!r}; no retrieval needed."
    elif not case.input.session_id or intent == "tom_tat_thieu_slot":
        actual = "needs_clarification"
        detail = "No session_id is available, so the request must not guess a session."
    elif is_stub:
        actual = "not_implemented"
        detail = "The request requires answer_query(), which current main marks as a stub."
    else:
        return _evaluate_live_query(case, chunks=chunks, manual_rows=manual_rows)

    passed = actual == case.expected.status
    official = passed if case.human_approved and actual != "not_implemented" else None
    blockers = []
    if not case.human_approved:
        blockers.append("Case expectation needs human approval.")
    if actual == "not_implemented":
        blockers.append("M2/M1 query guardrail is not connected.")

    return (
        EvalResult(
            case_id=case.case_id,
            actual_status=actual,
            technical_pass=passed,
            official_pass=official,
            checks=(
                _check(
                    "status",
                    passed,
                    observed=actual,
                    expected=case.expected.status,
                    detail=detail,
                ),
            ),
            blockers=tuple(blockers),
        ),
        [],
    )


def _merge_review_rows(
    rows: list[dict[str, str]],
    existing: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    merged = []
    for row in rows:
        old = existing.get((row["case_id"], row["claim_id"]), {})
        for field in ("supports_claim", "reverses_meaning", "reviewer", "review_note"):
            row[field] = old.get(field, row[field])
        merged.append(row)
    return merged


def _write_review_sheet(
    rows: list[dict[str, str]],
    path: Path,
    existing: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = _merge_review_rows(rows, existing)
    fieldnames = [
        "case_id",
        "session_id",
        "claim_id",
        "claim",
        "citations",
        "source_excerpts",
        "supports_claim",
        "reverses_meaning",
        "reviewer",
        "review_note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)
    return merged


def _review_digest(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Return commit-safe review evidence without claims or transcript excerpts."""

    decisions = []
    for row in rows:
        supports = _manual_value(row.get("supports_claim", ""))
        reverses = _manual_value(row.get("reverses_meaning", ""))
        reviewer = row.get("reviewer", "").strip()
        complete = supports is not None and reverses is not None and bool(reviewer)
        decisions.append(
            {
                "case_id": row["case_id"],
                "claim_id": row["claim_id"],
                "supports_claim": supports,
                "reverses_meaning": reverses,
                "reviewer": reviewer or None,
                "complete": complete,
            }
        )
    return {
        "review_row_count": len(decisions),
        "complete_row_count": sum(item["complete"] for item in decisions),
        "reviewers": sorted(
            {item["reviewer"] for item in decisions if item["reviewer"] is not None}
        ),
        "decisions": decisions,
    }


def _failed_check(result: EvalResult, name: str) -> bool:
    return any(check.name == name and check.passed is False for check in result.checks)


def _quality_bar(
    cases: tuple[EvalCase, ...],
    results: list[EvalResult],
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if any(result.official_pass is None for result in results):
        blockers.append("Not every case has an official human-reviewed verdict.")
        return "pending_human_input", blockers

    passed = sum(result.official_pass is True for result in results)
    overall = passed / len(results) if results else 0.0
    fake_cases = sum(_failed_check(result, "citation_valid") for result in results)
    speaker_cases = sum(_failed_check(result, "student_misattribution") for result in results)
    by_id = {result.case_id: result for result in results}
    oos = [case for case in cases if "out_of_scope" in case.tags]
    oos_passed = sum(by_id[case.case_id].official_pass is True for case in oos)
    oos_rate = oos_passed / len(oos) if oos else 0.0
    passed_bar = overall >= 0.85 and fake_cases == 0 and speaker_cases == 0 and oos_rate >= 0.9
    return ("passed" if passed_bar else "failed"), blockers


def render_report(summary: RunSummary, results: list[EvalResult]) -> str:
    lines = [
        f"# Eval run — {summary.run_id}",
        "",
        f"- Git commit: `{summary.git_commit or 'unknown'}`",
        f"- Cases: **{summary.case_count}**",
        (
            f"- Technical pass: **{summary.technical_pass_count}/{summary.case_count} "
            f"({summary.technical_pass_rate:.1%})**"
        ),
        f"- Official quality bar: **{summary.quality_bar_status}**",
        f"- Fake-citation cases: **{summary.fake_citation_cases}**",
        f"- Student-attribution cases: **{summary.student_misattribution_cases}**",
        f"- Query not implemented: **{summary.not_implemented_cases}**",
        f"- Missing summary artifact: **{summary.missing_artifact_cases}**",
        "",
        "## Từng case",
        "",
        "| Case | Actual | Technical | Official | Blocker |",
        "|---|---|---:|---:|---|",
    ]
    for result in results:
        blocker = result.blockers[0] if result.blockers else ""
        official = "pending" if result.official_pass is None else str(result.official_pass)
        lines.append(
            f"| `{result.case_id}` | `{result.actual_status}` | "
            f"{result.technical_pass} | {official} | {blocker} |"
        )
    if summary.blockers:
        lines += ["", "## Blocker", ""]
        lines += [f"- {item}" for item in summary.blockers]
    lines += [
        "",
        "> Đây là technical baseline nếu official verdict còn pending. Không đưa tỷ lệ",
        "> technical vào form như kết quả golden set chính thức.",
        "",
    ]
    return "\n".join(lines)


def run(cases_path: Path, run_id: str) -> tuple[list[EvalResult], RunSummary]:
    cases = load_cases(cases_path)
    loader, sessions, sections, chunks = _source_catalog()
    review_path = MANUAL_REVIEW_DIR / f"{run_id}.csv"
    existing_review = _load_manual_rows(review_path)

    results: list[EvalResult] = []
    review_rows: list[dict[str, str]] = []
    for case in cases:
        if case.input_type == "session_summary":
            result, rows = evaluate_summary_case(
                case,
                sessions=sessions,
                sections=sections,
                chunks=chunks,
                manual_rows=existing_review,
            )
            review_rows.extend(rows)
        elif case.input_type == "unknown_session":
            result = evaluate_unknown_session(case, loader=loader)
        else:
            result, rows = evaluate_query_case(
                case,
                chunks=chunks,
                manual_rows=existing_review,
            )
            review_rows.extend(rows)
        results.append(result)

    merged_review_rows = _write_review_sheet(review_rows, review_path, existing_review)
    quality_status, quality_blockers = _quality_bar(cases, results)
    technical_count = sum(result.technical_pass for result in results)
    official_values = [result.official_pass for result in results]
    all_official = all(value is not None for value in official_values)
    official_count = sum(value is True for value in official_values) if all_official else None
    summary = RunSummary(
        run_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        git_commit=_git_commit(),
        cases_path=str(cases_path),
        case_count=len(cases),
        technical_pass_count=technical_count,
        technical_pass_rate=technical_count / len(cases) if cases else 0.0,
        official_pass_count=official_count,
        official_pass_rate=(
            official_count / len(cases) if official_count is not None and cases else None
        ),
        fake_citation_cases=sum(_failed_check(result, "citation_valid") for result in results),
        student_misattribution_cases=sum(
            _failed_check(result, "student_misattribution") for result in results
        ),
        not_implemented_cases=sum(result.actual_status == "not_implemented" for result in results),
        missing_artifact_cases=sum(
            result.actual_status == "missing_artifact" for result in results
        ),
        quality_bar_status=quality_status,
        blockers=tuple(quality_blockers),
    )

    output_dir = RESULTS_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.jsonl").write_text(
        "".join(result.model_dump_json() + "\n" for result in results),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        summary.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "manual-review-summary.json").write_text(
        json.dumps(_review_digest(merged_review_rows), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        render_report(summary, results),
        encoding="utf-8",
    )
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DRAFT_CASES_PATH)
    parser.add_argument("--run-id", default="technical-baseline")
    args = parser.parse_args()
    _, summary = run(args.cases, args.run_id)
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
