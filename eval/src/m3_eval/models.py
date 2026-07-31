"""Typed contracts for draft cases and immutable run results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class GoldIdea(FrozenModel):
    gold_id: str
    text: str
    accepted_chunk_ids: tuple[str, ...]
    required_keywords: tuple[str, ...]


class CaseInput(FrozenModel):
    session_id: str | None = None
    query: str | None = None


class CaseExpected(FrozenModel):
    status: Literal[
        "ok",
        "needs_clarification",
        "insufficient",
        "out_of_scope",
        "refused",
    ]
    required_ideas: tuple[GoldIdea, ...] = ()
    must_have_exactly_five_points: bool = False
    must_have_valid_citations: bool = True
    must_warn_unclear: bool = False
    max_student_misattributions: int = 0
    notes: str = ""


class EvalCase(FrozenModel):
    case_id: str
    title: str
    input_type: Literal["session_summary", "query", "unknown_session"]
    input: CaseInput
    source_type: Literal["chatlog", "human_gold", "synthetic_risk"]
    source_ref: str
    source_excerpt: str = ""
    tags: tuple[str, ...]
    expected: CaseExpected
    human_approved: bool = False
    human_gold_complete: bool = False


class CheckResult(FrozenModel):
    name: str
    passed: bool | None
    observed: Any = None
    expected: Any = None
    detail: str = ""


class EvalResult(FrozenModel):
    case_id: str
    actual_status: str
    technical_pass: bool
    official_pass: bool | None = None
    checks: tuple[CheckResult, ...] = ()
    blockers: tuple[str, ...] = ()
    error: str | None = None


class CaseSetReport(FrozenModel):
    case_count: int
    chatlog_case_count: int
    approved_case_count: int
    gold_idea_count: int
    risk_counts: dict[str, int]
    structural_errors: tuple[str, ...] = ()
    readiness_blockers: tuple[str, ...] = ()
    ready_to_finalize: bool


class RunSummary(FrozenModel):
    run_id: str
    created_at: str
    git_commit: str | None
    cases_path: str
    case_count: int
    technical_pass_count: int
    technical_pass_rate: float
    official_pass_count: int | None = None
    official_pass_rate: float | None = None
    fake_citation_cases: int
    student_misattribution_cases: int
    not_implemented_cases: int
    missing_artifact_cases: int
    quality_bar_status: Literal["passed", "failed", "pending_human_input"]
    blockers: tuple[str, ...] = Field(default_factory=tuple)
