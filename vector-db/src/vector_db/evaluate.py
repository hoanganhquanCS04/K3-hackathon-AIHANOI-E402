"""Run the small, versioned retrieval relevance test set."""

from __future__ import annotations

import json
from pathlib import Path

from vector_db.config import PROJECT_DIR, settings
from vector_db.search import find_chunks

DEFAULT_CASES = PROJECT_DIR / "tests" / "retrieval_cases.json"


def evaluate(path: Path = DEFAULT_CASES) -> dict:
    cases = json.loads(path.read_text(encoding="utf-8"))
    hits = 0
    recalls: list[float] = []
    details = []

    for case in cases:
        results = find_chunks(
            case["query"],
            case["session_id"],
            top_k=case.get("top_k", 5),
        )
        returned = [result.payload["chunk_id"] for result in results]
        expected = set(case["expected_chunk_ids"])
        matched = expected.intersection(returned)
        hit = bool(matched)
        hits += int(hit)
        recalls.append(len(matched) / len(expected))
        details.append(
            {
                "query": case["query"],
                "session_id": case["session_id"],
                "expected": sorted(expected),
                "returned": returned,
                "matched": sorted(matched),
                "hit": hit,
            }
        )

    count = len(cases)
    return {
        "case_count": count,
        "hit_at_5": hits / count if count else 0.0,
        "recall_at_5": (sum(recalls) / count if count else 0.0),
        "details": details,
    }


def main() -> None:
    report = evaluate()
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.artifact_dir / "retrieval_evaluation.json"
    output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
