"""Soat .env: bien nao thieu, package nao chet vi no.

    uv run python scripts/check_env.py

Danh sach duoi day lay tu code THAT SU doc bien, khong lay tu .env.example —
.env.example la thu duoc sinh ra tu day, khong phai nguon.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "vector-db": ("QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY"),
    "summarizer": ("OPENAI_API_KEY",),
    "graph-db": ("NEO4J_URL", "NEO4J_USERNAME", "NEO4J_PASSWORD"),
}


def check_env(environ: dict[str, str]) -> list[str]:
    """Tra ve mot dong cho moi bien thieu, kem package chet vi no. Rong = du."""
    owners: dict[str, list[str]] = {}
    for package, names in REQUIREMENTS.items():
        for name in names:
            owners.setdefault(name, []).append(package)

    lines = []
    for name in sorted(owners):
        if not environ.get(name, "").strip():
            lines.append(f"THIEU {name} -> chet: {', '.join(owners[name])}")
    return lines


def main() -> int:
    load_dotenv()
    lines = check_env(dict(os.environ))
    if not lines:
        print("OK — moi bien bat buoc deu co mat.")
        return 0
    print("\n".join(lines))
    print(f"\n{len(lines)} bien thieu. Xem .env.example.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
