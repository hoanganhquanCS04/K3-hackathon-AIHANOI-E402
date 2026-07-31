from types import SimpleNamespace

from m3_eval import runner
from m3_eval.cases import load_cases
from m3_eval.paths import DRAFT_CASES_PATH
from m3_eval.runner import (
    _evaluate_live_query,
    _review_digest,
    _source_catalog,
    evaluate_query_case,
    evaluate_summary_case,
    evaluate_unknown_session,
)


def _case(case_id: str):
    return next(case for case in load_cases(DRAFT_CASES_PATH) if case.case_id == case_id)


def test_unknown_session_is_refused_without_calling_an_llm() -> None:
    loader, _, _, _ = _source_catalog()
    result = evaluate_unknown_session(_case("OOS-002"), loader=loader)

    assert result.actual_status == "refused"
    assert result.technical_pass is True
    assert result.official_pass is True


def test_selected_session_with_ambiguous_summary_scope_is_clarified() -> None:
    result, review_rows = evaluate_query_case(_case("AMB-001"))

    assert result.actual_status == "needs_clarification"
    assert result.technical_pass is True
    assert result.official_pass is True
    assert review_rows == []


def test_query_that_requires_search_is_reported_as_not_implemented() -> None:
    result, review_rows = evaluate_query_case(_case("SRC-004"))

    assert result.actual_status == "not_implemented"
    assert result.technical_pass is False
    assert result.official_pass is None
    assert review_rows == []


def test_future_live_query_adapter_validates_citations(monkeypatch) -> None:
    fake_live = SimpleNamespace(
        load_outline=lambda: [{"id": "01"}],
        get_session=lambda sessions, session_id: sessions[0],
        answer_query=lambda session, query: {
            "status": "answered",
            "claims": [
                {"claim": "Không thể kết luận thị trường thiếu AI engineer.", "cite": ["T01-002"]}
            ],
        },
    )
    monkeypatch.setattr(runner, "_live_product", lambda: fake_live)
    _, _, _, chunks = _source_catalog()
    result, review_rows = _evaluate_live_query(
        _case("DOM-002"),
        chunks=chunks,
        manual_rows={
            ("DOM-002", "CLAIM-01"): {
                "supports_claim": "yes",
                "reverses_meaning": "no",
                "reviewer": "external-reviewer",
            }
        },
    )

    assert result.actual_status == "ok"
    assert result.technical_pass is True
    assert len(review_rows) == 1
    assert next(check for check in result.checks if check.name == "citation_valid").passed is True


def test_review_digest_excludes_claims_and_source_excerpts() -> None:
    digest = _review_digest(
        [
            {
                "case_id": "SUM-T01",
                "claim_id": "KP-01",
                "claim": "sensitive generated claim",
                "source_excerpts": "sensitive transcript",
                "supports_claim": "yes",
                "reverses_meaning": "no",
                "reviewer": "reviewer-01",
            }
        ]
    )

    assert digest["complete_row_count"] == 1
    assert digest["reviewers"] == ["reviewer-01"]
    assert "claim" not in digest["decisions"][0]
    assert "source_excerpts" not in digest["decisions"][0]


def test_existing_summary_artifact_gets_deterministic_checks() -> None:
    _, sessions, sections, chunks = _source_catalog()
    result, review_rows = evaluate_summary_case(
        _case("SUM-T01"),
        sessions=sessions,
        sections=sections,
        chunks=chunks,
        manual_rows={},
    )

    assert result.actual_status == "ok"
    assert len(review_rows) == 8
    assert any(check.name == "citation_valid" for check in result.checks)
    assert any(check.name == "manual_traceability" for check in result.checks)
    exactly_five = next(check for check in result.checks if check.name == "exactly_five_key_points")
    assert exactly_five.passed is False
    assert result.official_pass is None
