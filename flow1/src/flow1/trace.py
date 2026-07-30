"""Trace debug theo chang. Chi ghi chep — khong mot dong logic nghiep vu nao.

VI SAO CO NullTrace: de KHONG co dong `if trace is not None` nao rai trong
retrieve/tools/agent. Tat va bat trace di qua dung mot duong code — nghia la
trace khong bao gio "chi hong khi bat".

LUAT VANG cua noi dung ghi: so sanh nao cung ghi CA HAI VE. Khong ghi
"refuse", ma ghi ratio=1.13 < T1_RATIO=1.20 -> refuse. Do la toan bo gia tri
cua module nay.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

TRACE_DIR = Path(__file__).resolve().parents[2] / "trace"


@dataclass(frozen=True)
class Stage:
    name: str
    ms: float
    data: dict[str, Any]


class Trace:
    """Ban ghi mot lan chay. Ghi ra JSON doc lai duoc."""

    def __init__(self, query: str) -> None:
        # run_id: microsecond-granular timestamp + 8 hex chars (32 bits random).
        # Total entropy: ~52 bits (2^20 microseconds/sec * 2^32 UUID space).
        # Safe for 100k+ traces per second. Avoids birthday-paradox collisions.
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S.%fZ")
        self.run_id = f"{stamp}-{uuid.uuid4().hex[:8]}"
        self.query = query
        self.stages: list[Stage] = []

    @contextmanager
    def stage(self, name: str) -> Iterator[dict[str, Any]]:
        """Bam gio mot chang. Loi van duoc GHI LAI roi moi nem tiep."""
        data: dict[str, Any] = {}
        start = time.perf_counter()
        try:
            yield data
        except Exception as exc:
            data["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            self.stages.append(Stage(name=name, ms=elapsed, data=data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "stages": [
                {"name": s.name, "ms": round(s.ms, 2), "data": s.data}
                for s in self.stages
            ],
        }

    def save(self, directory: Path | None = None) -> Path:
        target = Path(directory) if directory is not None else TRACE_DIR
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"{self.run_id}.json"

        # Refuse to overwrite existing files. Debug artifacts must not silently
        # disappear — a collision indicates a bug in run_id generation that must
        # be surfaced, not hidden by silent overwrites.
        if path.exists():
            raise FileExistsError(
                f"Trace file already exists (run_id collision): {path}"
            )

        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return path


class NullTrace:
    """Cung API voi Trace, khong lam gi. Mac dinh khi khong bat --trace."""

    run_id = ""

    def __init__(self, query: str = "") -> None:
        self.query = query
        self.stages: list[Stage] = []

    @contextmanager
    def stage(self, name: str) -> Iterator[dict[str, Any]]:
        yield {}

    def to_dict(self) -> dict[str, Any]:
        return {}

    def save(self, directory: Path | None = None) -> None:
        return None


def new_trace(query: str, *, enabled: bool) -> Trace | NullTrace:
    return Trace(query) if enabled else NullTrace(query)
