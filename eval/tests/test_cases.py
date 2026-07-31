from m3_eval.cases import load_cases, validate_case_set
from m3_eval.paths import DRAFT_CASES_PATH


def test_draft_has_required_structure_but_is_not_falsely_finalized() -> None:
    cases = load_cases(DRAFT_CASES_PATH)
    report = validate_case_set(cases)

    assert report.case_count == 20
    assert report.chatlog_case_count >= 10
    assert all(count >= 2 for count in report.risk_counts.values())
    assert report.structural_errors == ()
    assert report.gold_idea_count == 0
    assert report.ready_to_finalize is False
    assert any("18 human gold ideas" in item for item in report.readiness_blockers)
