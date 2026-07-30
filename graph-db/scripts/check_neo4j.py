"""Smoke test Neo4j — chạy trước khi viết bất kỳ logic graph nào.

    uv run python scripts/check_neo4j.py
"""

from __future__ import annotations

import sys

from neo4j.exceptions import AuthError, ConfigurationError, ServiceUnavailable

from graph_db import get_database, get_driver, query

_HINTS = {
    ServiceUnavailable: "Sai scheme hoặc không tới được server. Aura phải là neo4j+s://<id>."
    "databases.neo4j.io — không dùng bolt://, không dùng URL của Browser.",
    AuthError: "Sai NEO4J_USERNAME/NEO4J_PASSWORD. Aura mặc định user là `neo4j`.",
    ConfigurationError: "NEO4J_URL sai định dạng. Đúng: neo4j+s://... (Aura) hoặc "
    "bolt://localhost:7687 (local).",
}


def main() -> int:
    try:
        get_driver().verify_connectivity()
        print(f"[ok] connected   database={get_database()}")
        print(f"[ok] ping        {query('RETURN 1 AS ok')[0]}")
        print(f"[ok] node count  {query('MATCH (n) RETURN count(n) AS n')[0]['n']}")

        labels = [r["label"] for r in query("CALL db.labels() YIELD label RETURN label")]
        print(f"[ok] labels      {labels or '(graph còn rỗng)'}")
    except Exception as exc:  # noqa: BLE001 — script chẩn đoán, in lỗi rồi thoát
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        for exc_type, hint in _HINTS.items():
            if isinstance(exc, exc_type):
                print(f"\n  → {hint}", file=sys.stderr)
                break
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
