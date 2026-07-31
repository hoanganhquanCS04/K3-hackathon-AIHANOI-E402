"""Stable project paths for CLI commands."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent
REPOSITORY_ROOT = PROJECT_DIR.parent

EVIDENCE_DIR = PROJECT_DIR / "evidence"
CASES_DIR = PROJECT_DIR / "cases"
RESULTS_DIR = PROJECT_DIR / "results"
MANUAL_REVIEW_DIR = PROJECT_DIR / "manual-review"

CHATLOG_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "vlearn-pack"
    / "chatlog"
    / "chat_history_anonymized_for_hackathon.csv"
)
COUNTING_RULES_PATH = EVIDENCE_DIR / "counting-rules.json"
REVIEW_SAMPLES_PATH = EVIDENCE_DIR / "review-samples.csv"
CONFIRMED_LABELS_PATH = EVIDENCE_DIR / "confirmed-labels.v1.json"
DRAFT_CASES_PATH = CASES_DIR / "golden-set.draft.json"
CONFIRMED_CASE_APPROVALS_PATH = CASES_DIR / "confirmed-case-approvals.v1.json"
FINAL_CASES_PATH = CASES_DIR / "golden-set.v1.json"
SUMMARY_ARTIFACT_DIR = REPOSITORY_ROOT / "summarizer" / "artifacts" / "summaries"
