"""Cache kết quả LLM trên đĩa.

Khoá cache gồm ba thành phần (plan §10.2): nội dung, phiên bản prompt, và model.
Thiếu `prompt_version` là lỗi kinh điển — sửa prompt xong chạy lại, cache cũ trả
về kết quả cũ, và người viết prompt tưởng thay đổi của mình không có tác dụng.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(*parts: str) -> str:
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class SummaryCache:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Cache hỏng thì coi như miss và ghi đè, không làm hỏng cả build.
            return None

    def put(self, key: str, payload: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    def has(self, key: str) -> bool:
        return self._path(key).is_file()

    def count(self) -> int:
        if not self.directory.is_dir():
            return 0
        return sum(1 for _ in self.directory.glob("*.json"))
