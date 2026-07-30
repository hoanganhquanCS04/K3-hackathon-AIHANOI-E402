# Hybrid RAG + tái cơ cấu repo + trace debug — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gộp 3 package rời thành một uv workspace chạy được `pytest` toàn hệ, thêm trace debug theo chặng, và đổi retrieve từ BM25 thuần sang hybrid BM25 × Qdrant fuse bằng RRF trên mã đoạn.

**Architecture:** BM25 (offline) và Qdrant (semantic) cùng xếp hạng **700 đoạn nguyên tử**, nối nhau bằng **mã đoạn `Txx-NNN`** — không có lớp ánh xạ nào phải nuôi tay. Sau khi fuse, mỗi mã nở ra chunk gộp chứa nó để làm ngữ cảnh cho prompt. Cổng 1 vẫn quyết định trên **điểm BM25 thô của bảng xếp hạng nguyên tử**, độc lập hoàn toàn với fusion.

**Tech Stack:** Python 3.13 · uv workspace · rank_bm25 · qdrant-client · openai (embedding) · pydantic · pytest · Streamlit

**Spec:** `docs/superpowers/specs/2026-07-30-hybrid-rag-tai-co-cau-design.md`

## Global Constraints

- **Python `>=3.13`** cho cả 4 package. `.python-version` hiện là `3.12` — **sai**, phải đổi thành `3.13`, nếu không `uv sync` từ chối cả workspace.
- **`uv run pytest` ở gốc phải xanh mà KHÔNG cần API key nào.** Test chạm mạng bắt buộc mang `@pytest.mark.live`.
- **Khoá nối hai retriever luôn là mã đoạn `Txx-NNN`**, không bao giờ là chỉ số mảng.
- **`gate_stats` chỉ nhận điểm BM25 thô đã sắp giảm dần.** Truyền điểm RRF vào là bug — hàm đã có guard raise sẵn, đừng gỡ.
- **Không nới ngưỡng T1 cho đẹp số.** Nếu ma trận ngưỡng mới không tách được hai phân bố, ghi thật và dừng lại báo người dùng.
- **Không commit API key.** `.env` đã nằm trong `.gitignore`, giữ nguyên.
- Mọi commit message dùng **tiếng Việt không dấu** (khớp lịch sử repo), kết bằng dòng `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## File Structure

| File | Trách nhiệm |
|---|---|
| `pyproject.toml` (gốc) | khai `[tool.uv.workspace]` 4 member + cấu hình pytest chung |
| `conftest.py` (gốc) | đăng ký marker `live`, tự skip khi thiếu key |
| `scripts/check_env.py` | soát `.env` với danh sách biến từng package thật sự đọc |
| `flow1/src/flow1/trace.py` | `Stage` · `Trace` · `NullTrace` · `new_trace` — **chỉ ghi chép, không logic nghiệp vụ** |
| `flow1/src/flow1/atomic.py` | `atomic_chunks` · `build_code_map` — đơn vị nguyên tử và map mã→ngữ cảnh |
| `flow1/src/flow1/store.py` | `Store` — gói 4 thứ mà retrieve cần, thay tuple 2 phần tử |
| `flow1/src/flow1/semantic.py` | `SemanticBackend` · `NullBackend` · `QdrantBackend` · `default_backend` |
| `flow1/src/flow1/index.py` | build/save/load `Store`; BM25 trên atomics |
| `flow1/src/flow1/retrieve.py` | fuse RRF trên mã, nở context, ghi trace |
| `vector-db/src/vector_db/search.py` | nới `find_chunks` cho `session_id` optional |
| `graph-db/` | Neo4j, **ngoài luồng** — sửa cho chạy được, không ai import |

**Không đụng tới:** `gates.py`, `prompts.py`, `check.py`, `render.py`, `models.py`, `chunk.py`, `parse.py`. Thiết kế cố tình giữ `Retrieval.hits` là danh sách chunk ngữ cảnh với `Hit.bm25` là điểm nguyên tử tốt nhất trong chunk đó — nhờ vậy 4 cổng và bộ render không biết gì về việc bên dưới đã đổi.

---

## Task 1: uv workspace + di chuyển thư mục

**Files:**
- Create: `pyproject.toml`, `conftest.py`
- Modify: `.python-version`, `.gitignore`
- Move: `codebase/` → `flow1/` (src-layout) · `src/graph_db/` + `neo4j/` → `graph-db/` · `scripts/test_qdrant.py`, `scripts/test_exist_collection.py` → `vector-db/scripts/` · `scripts/check_neo4j.py` → `graph-db/scripts/`
- Delete: `PROJECT_STRUCTURE.md`, `requirements.txt`, `src/`

**Interfaces:**
- Consumes: không có (task đầu)
- Produces: `uv run pytest` ở gốc collect được cả 4 member. Import path `from flow1.X import ...` **không đổi**.

- [ ] **Step 1: Sửa `.python-version`**

```
3.13
```

Lý do: cả 3 `pyproject.toml` hiện có đều khai `requires-python = ">=3.13"`, còn `.python-version` đang là `3.12` → `uv sync` từ chối toàn workspace.

- [ ] **Step 2: Di chuyển `codebase/` sang src-layout**

```bash
git mv codebase flow1
mkdir -p flow1/src flow1/app
git mv flow1/flow1 flow1/src/flow1
git mv flow1/app.py flow1/live.py flow1/theme.py flow1/stubs.py flow1/app/
```

`flow1/tests/`, `flow1/scripts/`, `flow1/tools/`, `flow1/pyproject.toml` đã ở đúng chỗ, không đụng.

- [ ] **Step 3: Di chuyển Neo4j và các script ad-hoc**

```bash
mkdir -p graph-db/src graph-db/scripts vector-db/scripts
git mv src/graph_db graph-db/src/graph_db
git mv neo4j/ingest_transcripts.py neo4j/query_neo4j.py graph-db/scripts/
git mv neo4j/README.md graph-db/README.md
git mv scripts/check_neo4j.py graph-db/scripts/
git mv scripts/test_qdrant.py scripts/test_exist_collection.py vector-db/scripts/
git rm -r --cached src neo4j 2>/dev/null; rm -rf src neo4j
git rm PROJECT_STRUCTURE.md requirements.txt
```

- [ ] **Step 4: Viết `pyproject.toml` ở gốc**

```toml
[project]
name = "vlearn-sotay"
version = "0.1.0"
requires-python = ">=3.13"

[tool.uv.workspace]
members = ["flow1", "vector-db", "summarizer", "graph-db"]

[tool.uv.sources]
flow1 = { workspace = true }
vector-db = { workspace = true }
summarizer = { workspace = true }
graph-db = { workspace = true }

[dependency-groups]
dev = ["pytest>=9.1.1", "pytest-cov>=7.1.0", "ruff>=0.16.0"]

[tool.pytest.ini_options]
testpaths = ["flow1/tests", "vector-db/tests", "summarizer/tests", "graph-db/tests"]
markers = ["live: cham API that (OpenAI/Qdrant/Neo4j); can key that de chay"]
addopts = "-ra"
```

- [ ] **Step 5: Viết `flow1/pyproject.toml` cho src-layout**

```toml
[project]
name = "flow1"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["pydantic", "rank_bm25", "numpy", "streamlit", "vector-db"]

[tool.uv.sources]
vector-db = { workspace = true }

[build-system]
requires = ["uv_build>=0.12.0,<0.13.0"]
build-backend = "uv_build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Bỏ `anthropic` khỏi dependencies: grep cả `flow1/` không có dòng nào `import anthropic` — `ask.py` gọi `summarizer.llm.OpenAIStructuredLLM`.

- [ ] **Step 6: Viết `graph-db/pyproject.toml`**

```toml
[project]
name = "graph-db"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["neo4j>=5.14.0", "python-dotenv>=1.2.2"]

[build-system]
requires = ["uv_build>=0.12.0,<0.13.0"]
build-backend = "uv_build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 7: Viết `conftest.py` ở gốc**

```python
"""Cau hinh pytest dung chung cho ca workspace.

Luat: `pytest` khong key phai xanh 100%. Test cham mang mang marker `live`
va tu skip khi thieu bien moi truong tuong ung.
"""

from __future__ import annotations

import os

import pytest

_LIVE_REQUIREMENTS = ("OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY")


def pytest_collection_modifyitems(config, items):
    missing = [name for name in _LIVE_REQUIREMENTS if not os.getenv(name, "").strip()]
    if not missing:
        return
    skip = pytest.mark.skip(reason=f"can bien moi truong: {', '.join(missing)}")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 8: Thêm dòng vào `.gitignore`**

```gitignore
flow1/store/
flow1/cache/
flow1/trace/
```

Bỏ hai dòng cũ `codebase/store/`, `codebase/cache/` (thư mục không còn tồn tại).

- [ ] **Step 9: Đồng bộ và chạy thử**

Run: `uv sync --all-packages`
Expected: 4 member cài xong, không lỗi resolve.

Run: `uv run pytest --collect-only -q 2>&1 | tail -5`
Expected: collect được cả 4 thư mục test, **không có `ModuleNotFoundError`**. Số test flow1 vẫn 284 (276 pass + 8 skip).

- [ ] **Step 10: Chạy toàn bộ test**

Run: `uv run pytest -q`
Expected: flow1 xanh như cũ. `vector-db` và `summarizer` **có thể còn đỏ** vì lỗi logic, nhưng phải **collect được** — đó là mốc của task này. Ghi lại con số chính xác, Task 3 cần.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "refactor: gop 4 package vao mot uv workspace

- codebase/ -> flow1/ theo src-layout, import path giu nguyen
- src/graph_db + neo4j/ -> graph-db/, ngoai luong
- script ad-hoc ve dung package chung cham toi
- xoa PROJECT_STRUCTURE.md va requirements.txt goc (mo ta kien truc khong ton tai)
- .python-version 3.12 -> 3.13, khop requires-python cua ca 3 package

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Thống nhất biến môi trường + `check_env.py`

**Files:**
- Create: `scripts/check_env.py`, `scripts/tests/test_check_env.py`
- Modify: `.env.example`, `graph-db/src/graph_db/connection.py`

**Interfaces:**
- Consumes: workspace từ Task 1
- Produces: `check_env(environ: dict) -> list[str]` trả danh sách dòng mô tả biến thiếu, rỗng nghĩa là đủ

- [ ] **Step 1: Viết test thất bại**

Tạo `scripts/tests/test_check_env.py`:

```python
from scripts.check_env import REQUIREMENTS, check_env


def test_env_du_thi_khong_bao_gi():
    full = {name: "x" for group in REQUIREMENTS.values() for name in group}
    assert check_env(full) == []


def test_bao_dung_bien_thieu_va_package_chet_vi_no():
    partial = {name: "x" for group in REQUIREMENTS.values() for name in group}
    del partial["QDRANT_URL"]
    lines = check_env(partial)
    assert len(lines) == 1
    assert "QDRANT_URL" in lines[0]
    assert "vector-db" in lines[0]


def test_bien_rong_tinh_la_thieu():
    full = {name: "x" for group in REQUIREMENTS.values() for name in group}
    full["OPENAI_API_KEY"] = "   "
    lines = check_env(full)
    assert any("OPENAI_API_KEY" in line for line in lines)
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest scripts/tests/test_check_env.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.check_env'`

- [ ] **Step 3: Viết `scripts/check_env.py`**

```python
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
```

Tạo `scripts/__init__.py` và `scripts/tests/__init__.py` rỗng để import được.

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest scripts/tests/test_check_env.py -q`
Expected: 3 passed

- [ ] **Step 5: Viết lại `.env.example`**

```bash
# =============================================================================
# VLearn So tay buoi hoc — bien moi truong
# Ten bien duoi day lay tu code THAT SU doc chung. Doi ten o day la lam chet code.
# Soat lai bang:  uv run python scripts/check_env.py
# =============================================================================

# --- OpenAI (embedding cho vector-db, generate cho summarizer va flow1) ---
OPENAI_API_KEY=sk-...
# De trong = api.openai.com. Dat khi di qua relay tuong thich OpenAI.
OPENAI_BASE_URL=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# PHAI la 768 — khop collection da build, xem vector-db/artifacts/manifest.json
OPENAI_EMBEDDING_DIMENSIONS=768

# --- Qdrant Cloud ---
QDRANT_URL=https://xxx.qdrant.tech:6333
QDRANT_API_KEY=...
QDRANT_COLLECTION=vlearn_transcripts_openai_small_768_v1

# --- Neo4j (NGOAI LUONG — khong package nao trong duong chay import) ---
NEO4J_URL=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
```

Đã bỏ khỏi file: `OPENAI_MODEL`, `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_VECTOR_DIM`, `QDRANT_CHILD_CHUNKS_COLLECTION`, `QDRANT_PARENT_CHUNKS_COLLECTION`, `NEO4J_DATABASE`, `PARENT_CHUNK_SIZE`, `DEFAULT_TOP_K`, `MAX_RETRIEVAL_RESULTS`, `LOG_LEVEL`, `LOG_FILE`, `DATA_DIR`, `CACHE_DIR` — không dòng code nào đọc chúng.

- [ ] **Step 6: Chạy check trên `.env` thật**

Run: `uv run python scripts/check_env.py`
Expected: liệt kê đúng `QDRANT_URL`, `NEO4J_URL` đang thiếu (`.env` hiện có `QDRANT_HOST`/`QDRANT_PORT` và `NEO4J_URI`).

Báo cho người dùng đổi `.env` của họ theo `.env.example`. **Không tự sửa `.env`** — file đó chứa secret và không nằm trong git.

- [ ] **Step 7: Commit**

```bash
git add scripts .env.example
git commit -m "fix(config): thong nhat ten bien moi truong theo code thuc doc

.env dang khai QDRANT_HOST/PORT nhung vector-db doc QDRANT_URL -> chet o config.
Bo 14 bien khong dong code nao doc (tan du ke hoach llama-index).
Them scripts/check_env.py bao dung bien thieu + package chet vi no.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Báo cáo trạng thái nền

**Files:**
- Create: `docs/system-test-report.md`

**Interfaces:**
- Consumes: kết quả `uv run pytest` từ Task 1 Step 10
- Produces: mốc so sánh cho Task 14

- [ ] **Step 1: Thu thập số liệu**

Run: `uv run pytest -q 2>&1 | tail -30`
Run: `uv run pytest --collect-only -q 2>&1 | tail -3`
Run: `uv run python scripts/check_env.py`

- [ ] **Step 2: Viết `docs/system-test-report.md`**

Khung bắt buộc — điền số thật đo được, **không làm tròn cho đẹp**:

```markdown
# Bao cao kiem thu toan he

## Lan 1 — truoc khi doi retrieval (sau Task 1-2)

**Ngay:** <ngày chạy> · **Commit:** <sha>

| Package | Collect | Pass | Fail | Skip | Ghi chu |
|---|---|---|---|---|---|
| flow1 | | | | | |
| vector-db | | | | | |
| summarizer | | | | | |
| graph-db | | | | | |

### Cai gi da hong truoc Task 1

- vector-db va summarizer khong collect noi test: moi package mot venv rieng,
  deps khong nam trong venv goc.
- .env khai QDRANT_HOST/PORT nhung vector-db doc QDRANT_URL.

### Cai gi con do sau Task 1-2

<liet ke tung test do + ly do, KHONG bo qua cai nao>
```

- [ ] **Step 3: Commit**

```bash
git add docs/system-test-report.md
git commit -m "docs: bao cao kiem thu toan he lan 1, truoc khi doi retrieval

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: `trace.py` — Stage, Trace, NullTrace

**Files:**
- Create: `flow1/src/flow1/trace.py`, `flow1/tests/test_flow1_trace.py`

**Interfaces:**
- Consumes: không có
- Produces:
  - `Stage(name: str, ms: float, data: dict)` — frozen dataclass
  - `Trace(query: str)` với `.run_id: str`, `.stages: list[Stage]`, `.stage(name) -> ContextManager[dict]`, `.to_dict() -> dict`, `.save(dir: Path) -> Path`
  - `NullTrace(query: str = "")` — **đúng API đó**, không ghi gì, `.save()` trả `None`
  - `new_trace(query: str, *, enabled: bool) -> Trace | NullTrace`

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_trace.py`:

```python
import json

import pytest

from flow1.trace import NullTrace, Trace, new_trace


def test_stage_ghi_lai_du_lieu_va_thoi_gian():
    trace = Trace("cau hoi")
    with trace.stage("bm25") as data:
        data["top"] = [("T01-001", 12.5)]

    assert len(trace.stages) == 1
    assert trace.stages[0].name == "bm25"
    assert trace.stages[0].data["top"] == [("T01-001", 12.5)]
    assert trace.stages[0].ms >= 0.0


def test_stage_giu_thu_tu_goi():
    trace = Trace("q")
    for name in ("gate0", "bm25", "semantic", "fuse"):
        with trace.stage(name):
            pass
    assert [s.name for s in trace.stages] == ["gate0", "bm25", "semantic", "fuse"]


def test_loi_trong_stage_van_duoc_ghi_roi_moi_nem_tiep():
    trace = Trace("q")
    with pytest.raises(ValueError):
        with trace.stage("semantic") as data:
            data["backend"] = "qdrant"
            raise ValueError("mat mang")

    assert trace.stages[0].name == "semantic"
    assert trace.stages[0].data["backend"] == "qdrant"
    assert "mat mang" in trace.stages[0].data["error"]


def test_save_ghi_json_doc_lai_duoc(tmp_path):
    trace = Trace("attention la gi")
    with trace.stage("bm25") as data:
        data["n"] = 3

    path = trace.save(tmp_path)
    blob = json.loads(path.read_text(encoding="utf-8"))

    assert blob["query"] == "attention la gi"
    assert blob["run_id"] == trace.run_id
    assert blob["stages"][0]["name"] == "bm25"
    assert blob["stages"][0]["data"]["n"] == 3


def test_run_id_khac_nhau_giua_hai_lan_chay():
    assert Trace("q").run_id != Trace("q").run_id


def test_nulltrace_co_dung_api_cua_trace():
    for name in ("run_id", "query", "stages", "stage", "to_dict", "save"):
        assert hasattr(NullTrace(), name), f"NullTrace thieu {name}"


def test_nulltrace_khong_ghi_gi_va_khong_no():
    null = NullTrace()
    with null.stage("bm25") as data:
        data["top"] = [1, 2, 3]
    assert null.stages == []
    assert null.save(None) is None


def test_new_trace_chon_dung_loai():
    assert isinstance(new_trace("q", enabled=True), Trace)
    assert isinstance(new_trace("q", enabled=False), NullTrace)
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_trace.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.trace'`

- [ ] **Step 3: Viết `flow1/src/flow1/trace.py`**

```python
"""Trace debug theo chang. Chi ghi chep — khong mot dong logic nghiep vu nao.

VI SAO CO NullTrace: de KHONG co dong `if trace is not None` nao rai trong
retrieve/gates/ask. Tat va bat trace di qua dung mot duong code — nghia la
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
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        self.run_id = f"{stamp}-{uuid.uuid4().hex[:4]}"
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
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
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
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_trace.py -q`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add flow1/src/flow1/trace.py flow1/tests/test_flow1_trace.py
git commit -m "feat(flow1): trace debug theo chang, NullTrace giu code sach

NullTrace cung API voi Trace nen khong co `if trace is not None` nao rai
trong duong chay — tat va bat trace di qua dung mot duong code.
Loi trong stage duoc ghi lai roi moi nem tiep.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Gắn trace vào đường chạy hiện tại (còn BM25 thuần)

**Files:**
- Modify: `flow1/src/flow1/retrieve.py`, `flow1/src/flow1/ask.py`
- Test: `flow1/tests/test_flow1_trace_wiring.py`

**Interfaces:**
- Consumes: `new_trace`, `Trace`, `NullTrace` từ Task 4
- Produces: `retrieve(..., trace=None)` và `ask(..., trace=None)`. `Result` có thêm field `trace: object | None = None`.

Làm bước này **trước** khi đổi retrieval là có chủ ý: trace là dụng cụ đo, phải có dụng cụ trước khi thay động cơ.

**Biết trước:** phần sửa `retrieve.py` ở task này sẽ bị Task 10 viết đè. Đó là chấp nhận được — cái sống sót là `ask.py` (5 trong 6 chặng nằm ở đó) và việc có trace chạy thật trên đường chạy cũ để đối chiếu trước/sau khi đổi động cơ.

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_trace_wiring.py`:

```python
from flow1.ask import ask
from flow1.models import Intent
from flow1.trace import NullTrace, Trace


def _intent_noi_dung(system, blocks, schema):
    return Intent(label="nội_dung_khoá", reason="test")


def test_ask_ghi_stage_gate0_va_gate1(bm25_store):
    trace = Trace("attention la gi")
    ask(
        "cơ chế attention là gì",
        store=bm25_store,
        segs=[],
        trace=trace,
        classify_call=_intent_noi_dung,
        answer_call=lambda *a: (_ for _ in ()).throw(RuntimeError("khong goi model")),
    )
    names = [s.name for s in trace.stages]
    assert "gate0" in names
    assert "bm25" in names
    assert "gate1" in names


def test_gate1_ghi_ca_hai_ve_cua_moi_so_sanh(bm25_store):
    from flow1.thresholds import T1_ABS, T1_RATIO

    trace = Trace("q")
    ask(
        "cơ chế attention là gì",
        store=bm25_store,
        segs=[],
        trace=trace,
        classify_call=_intent_noi_dung,
        answer_call=lambda *a: (_ for _ in ()).throw(RuntimeError("stop")),
    )
    gate1 = next(s for s in trace.stages if s.name == "gate1")
    assert gate1.data["T1_ABS"] == T1_ABS
    assert gate1.data["T1_RATIO"] == T1_RATIO
    assert "top1_abs" in gate1.data
    assert "ratio" in gate1.data
    assert gate1.data["action"] in {"pass", "refuse", "clarify"}


def test_khong_truyen_trace_thi_khong_no(bm25_store):
    result = ask(
        "cơ chế attention là gì",
        store=bm25_store,
        segs=[],
        classify_call=_intent_noi_dung,
        answer_call=lambda *a: (_ for _ in ()).throw(RuntimeError("stop")),
    )
    assert isinstance(result.trace, NullTrace)
```

Thêm fixture `bm25_store` vào `flow1/tests/conftest.py` (tạo file nếu chưa có):

```python
import pytest

from flow1.index import build, save
from flow1.models import Seg


def _seg(code, session, order, text, section_idx=1):
    return Seg(
        code=code, session=session, session_title=f"Buoi {session}",
        locate_confidence="cao", section_idx=section_idx,
        section_title="Attention va Transformer", order=order, text=text,
        speaker="instructor", has_gap=False, is_activity=False, n_chars=len(text),
    )


@pytest.fixture
def sample_segs():
    return [
        _seg("T04-001", "04", 1, "Cơ chế attention cho phép mô hình tập trung vào token liên quan."),
        _seg("T04-002", "04", 2, "Multi-head attention chạy nhiều đầu attention song song."),
        _seg("T04-003", "04", 3, "Transformer bỏ hẳn recurrent, chỉ dùng attention."),
        _seg("T02-001", "02", 1, "Automation là thay người làm, augmentation là hỗ trợ người làm.", 2),
    ]


@pytest.fixture
def bm25_store(sample_segs, tmp_path):
    """Store dung duoc cho retrieve(store=...). Task 7 doi kieu tra ve cua ham nay."""
    from flow1.chunk import chunk_all

    chunks = chunk_all(sample_segs)
    return chunks, build(chunks)
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_trace_wiring.py -q`
Expected: FAIL — `ask() got an unexpected keyword argument 'trace'`

- [ ] **Step 3: Thêm `trace` vào `retrieve.py`**

Trong `flow1/src/flow1/retrieve.py`, đổi chữ ký và bọc phần tính điểm:

```python
def retrieve(
    query: str,
    *,
    session: str | None = None,
    k: int = TOP_K,
    store: tuple[list[Chunk], object] | None = None,
    path: Path = BM25_PATH,
    embeddings=None,
    query_vector=None,
    trace=None,
) -> Retrieval:
```

Ngay đầu thân hàm:

```python
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(query)
```

Bọc phần BM25 (từ `tokens = tokenize(query)` tới sau khi có `top1_abs, ratio`):

```python
    with trace.stage("bm25") as tdata:
        tokens = tokenize(query)
        tdata["tokens"] = tokens
        if not tokens:
            tdata["ket_luan"] = "query khong con token nao sau khi tokenize"
            return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

        all_scores = bm25.get_scores(tokens)
        keep = [
            i for i, chunk in enumerate(chunks)
            if session is None or chunk.session == session
        ]
        tdata["session_filter"] = session
        tdata["n_ung_vien"] = len(keep)
        if not keep:
            tdata["ket_luan"] = f"khong chunk nao thuoc buoi {session}"
            return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

        bm25_scores = {i: float(all_scores[i]) for i in keep}
        bm25_order = sorted(keep, key=lambda i: bm25_scores[i], reverse=True)
        top1_abs, ratio = gate_stats([bm25_scores[i] for i in bm25_order])
        tdata["top10"] = [
            (chunks[i].chunk_id, round(bm25_scores[i], 3)) for i in bm25_order[:10]
        ]
        tdata["top1_abs"] = top1_abs
        tdata["ratio"] = ratio if ratio != math.inf else "inf"
```

- [ ] **Step 4: Thêm `trace` vào `ask.py`**

Thêm field vào `Result`:

```python
    trace: object | None = None
```

Đổi chữ ký `ask` thêm `trace=None`, và ngay đầu thân hàm:

```python
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(question)
```

Bọc cổng 0:

```python
    with trace.stage("gate0") as tdata:
        intent = gate0(question, call=classify_call)
        tdata["label"] = intent.label
        tdata["reason"] = intent.reason
        tdata["quyet_boi"] = "rule" if "rule tất định" in intent.reason else "llm"
    if intent.label != CONTENT_LABEL:
        return Result(outcome="off_topic", question=question,
                      message=template_for(intent.label), intent=intent, trace=trace)
```

Truyền trace vào retrieve:

```python
    retrieval = retrieve(question, session=session, store=store, path=path, trace=trace)
```

Bọc cổng 1 — **đây là chỗ luật "ghi cả hai vế" phải thấy được**:

```python
    with trace.stage("gate1") as tdata:
        from flow1.thresholds import T1_ABS, T1_RATIO

        decision = gate1(retrieval)
        tdata["top1_abs"] = retrieval.top1_abs
        tdata["ratio"] = retrieval.ratio if retrieval.ratio != math.inf else "inf"
        tdata["T1_ABS"] = T1_ABS
        tdata["T1_RATIO"] = T1_RATIO
        tdata["action"] = decision.action
        tdata["vi_sao"] = (
            f"top1_abs={retrieval.top1_abs:.2f} < T1_ABS={T1_ABS} "
            if retrieval.top1_abs < T1_ABS else ""
        ) + (
            f"ratio={retrieval.ratio:.2f} < T1_RATIO={T1_RATIO}"
            if retrieval.ratio < T1_RATIO else ""
        ) or "ca hai nguong deu qua"
```

Thêm `import math` vào đầu `ask.py`. Thêm `trace=trace` vào **mọi** lệnh `return Result(...)` còn lại.

Bọc cổng 2 và cổng 3:

```python
    with trace.stage("context") as tdata:
        user_blocks = [
            {"type": "text", "text": format_context(retrieval)},
            {"type": "text", "text": answer_user(question, session)},
        ]
        tdata["chunk_ids"] = [h.chunk.chunk_id for h in retrieval.hits]
        tdata["n_chars"] = sum(len(b["text"]) for b in user_blocks)

    with trace.stage("generate") as tdata:
        try:
            answer = answer_call(ANSWER_SYSTEM, user_blocks, Answer)
        except Exception as exc:
            tdata["that_bai"] = str(exc)
            return Result(outcome="error", question=question,
                          message=f"Không gọi được model, nên mình không trả lời: {exc}",
                          intent=intent, decision=decision, retrieval=retrieval, trace=trace)
        tdata["status"] = answer.status
        tdata["n_claim"] = len(answer.claims)

    ...

    with trace.stage("gate3") as tdata:
        verdict = check(answer, retrieval, segs, check_citations=check_citations)
        tdata["status"] = verdict.status
        tdata["n_claim_qua"] = len(verdict.claims)
        tdata["drops"] = [(d.kind, d.claim_text[:60]) for d in verdict.drops]
        tdata["student_codes"] = verdict.student_codes
        tdata["gap_codes"] = verdict.gap_codes
```

Lưu ý: `generate` phải bắt exception **bên trong** `with` để `tdata["that_bai"]` được ghi trước khi return — nhưng `return` trong `with` vẫn chạy `finally` nên stage được ghi lại đầy đủ.

- [ ] **Step 5: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_trace_wiring.py -q`
Expected: 3 passed

Run: `uv run pytest flow1/tests -q`
Expected: toàn bộ test flow1 cũ vẫn xanh — `trace` có giá trị mặc định nên không phá ai.

- [ ] **Step 6: Commit**

```bash
git add flow1/src/flow1/retrieve.py flow1/src/flow1/ask.py flow1/tests/
git commit -m "feat(flow1): gan trace vao 6 chang cua duong chay

gate0 bm25 gate1 context generate gate3. Cong 1 ghi ca top1_abs/ratio lan
T1_ABS/T1_RATIO da so — cau hoi 'vi sao con nay bi chan' tra loi duoc bang
mot lan doc thay vi mot lan debug.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: `--trace` trên CLI + bảng người đọc được

**Files:**
- Modify: `flow1/src/flow1/cli.py`
- Create: `flow1/src/flow1/trace_render.py`
- Test: `flow1/tests/test_flow1_trace_render.py`

**Interfaces:**
- Consumes: `Trace.to_dict()` từ Task 4
- Produces: `render_trace(trace) -> str` — bảng nhiều dòng cho người đọc

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_trace_render.py`:

```python
from flow1.trace import Trace
from flow1.trace_render import render_trace


def test_bang_co_ten_chang_va_thoi_gian():
    trace = Trace("attention la gi")
    with trace.stage("bm25") as data:
        data["top10"] = [("T04-001", 12.5), ("T04-002", 9.1)]

    text = render_trace(trace)
    assert "bm25" in text
    assert "T04-001" in text
    assert "ms" in text


def test_hien_ca_hai_ve_cua_so_sanh_nguong():
    trace = Trace("q")
    with trace.stage("gate1") as data:
        data["vi_sao"] = "ratio=1.13 < T1_RATIO=1.20"
        data["action"] = "refuse"

    text = render_trace(trace)
    assert "ratio=1.13 < T1_RATIO=1.20" in text
    assert "refuse" in text


def test_trace_rong_khong_no():
    assert render_trace(Trace("q")) != ""
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_trace_render.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.trace_render'`

- [ ] **Step 3: Viết `flow1/src/flow1/trace_render.py`**

```python
"""Trace -> bang cho nguoi doc. Chi dinh dang, khong tinh toan gi."""

from __future__ import annotations


def _fmt_value(value) -> str:
    if isinstance(value, list) and value and isinstance(value[0], (list, tuple)):
        return "\n".join(f"        {a}  {b}" for a, b in value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:10])
    return str(value)


def render_trace(trace) -> str:
    lines = [
        "",
        "=" * 68,
        f"TRACE {trace.run_id}",
        f"  hoi: {trace.query}",
        "=" * 68,
    ]
    for stage in trace.stages:
        lines.append(f"\n[{stage.name}]  {stage.ms:.1f} ms")
        for key, value in stage.data.items():
            rendered = _fmt_value(value)
            if "\n" in rendered:
                lines.append(f"    {key}:")
                lines.append(rendered)
            else:
                lines.append(f"    {key}: {rendered}")
    lines.append("=" * 68)
    return "\n".join(lines)
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_trace_render.py -q`
Expected: 3 passed

- [ ] **Step 5: Gắn `--trace` vào CLI**

Trong `flow1/src/flow1/cli.py`, đổi `_run_ask`:

```python
def _run_ask(question: str, session: str | None, want_trace: bool = False) -> int:
    from flow1.parse import TRANSCRIPT_DIR, parse_all
    from flow1.trace import new_trace

    segs = parse_all() if TRANSCRIPT_DIR.exists() else None
    trace = new_trace(question, enabled=want_trace)

    try:
        result = ask(
            question,
            session=session,
            segs=segs,
            trace=trace,
            classify_call=_CLASSIFY_CALL,
            answer_call=_ANSWER_CALL,
            check_citations=_CHECK_CITATIONS,
        )
    except IndexMissing as exc:
        print(exc)
        return 3

    print(render(result, segs or []))

    if want_trace:
        from flow1.trace_render import render_trace

        print(render_trace(trace), file=sys.stderr)
        path = trace.save()
        print(f"Trace da ghi: {path}", file=sys.stderr)

    return 1 if result.outcome == "error" else 0
```

Thêm argument và sửa dispatch:

```python
    ask_parser.add_argument(
        "--trace", action="store_true",
        help="In bang chi tiet tung chang ra stderr va ghi JSON vao flow1/trace/.",
    )
```

```python
    return _run_ask(args.question, args.session, args.trace)
```

- [ ] **Step 6: Chạy test để chắc không phá gì**

Run: `uv run pytest flow1/tests -q`
Expected: toàn bộ xanh

- [ ] **Step 7: Commit**

```bash
git add flow1/src/flow1/cli.py flow1/src/flow1/trace_render.py flow1/tests/test_flow1_trace_render.py
git commit -m "feat(flow1): --trace in bang tung chang ra stderr va ghi JSON

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Đơn vị nguyên tử + map mã → ngữ cảnh + `Store`

**Files:**
- Create: `flow1/src/flow1/atomic.py`, `flow1/src/flow1/store.py`, `flow1/tests/test_flow1_atomic.py`
- Modify: `flow1/src/flow1/index.py`

**Interfaces:**
- Consumes: `Seg`, `Chunk` từ `flow1.models`; `chunk_all` từ `flow1.chunk`
- Produces:
  - `atomic_chunks(segs: list[Seg]) -> list[Chunk]` — đúng 1 Chunk cho mỗi Seg, `chunk_id == seg.code`
  - `build_code_map(contexts: list[Chunk]) -> dict[str, tuple[int, ...]]` — mã đoạn → **mọi** chỉ số context chứa nó
  - `Store(atomics, contexts, code_to_contexts, bm25)` — frozen dataclass
  - `index.load(path) -> Store` (đổi kiểu trả về từ `tuple[list[Chunk], BM25Okapi]`)

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_atomic.py`:

```python
from flow1.atomic import atomic_chunks, build_code_map
from flow1.chunk import chunk_all


def test_moi_seg_thanh_dung_mot_chunk(sample_segs):
    atomics = atomic_chunks(sample_segs)
    assert len(atomics) == len(sample_segs)


def test_chunk_id_chinh_la_ma_doan(sample_segs):
    atomics = atomic_chunks(sample_segs)
    assert [c.chunk_id for c in atomics] == [s.code for s in sample_segs]


def test_moi_atomic_chi_co_dung_mot_ma(sample_segs):
    for chunk in atomic_chunks(sample_segs):
        assert len(chunk.seg_codes) == 1


def test_atomic_giu_nguyen_van_va_co_prefix_heading(sample_segs):
    atomic = atomic_chunks(sample_segs)[0]
    assert atomic.text == sample_segs[0].text
    assert sample_segs[0].section_title in atomic.index_text


def test_atomic_giu_co_has_gap(sample_segs):
    atomics = atomic_chunks(sample_segs)
    assert [c.has_gap for c in atomics] == [s.has_gap for s in sample_segs]


def test_map_tro_moi_ma_ve_it_nhat_mot_context(sample_segs):
    contexts = chunk_all(sample_segs)
    code_map = build_code_map(contexts)
    for seg in sample_segs:
        assert seg.code in code_map
        assert len(code_map[seg.code]) >= 1


def test_map_bat_duoc_ma_nam_trong_hai_context_do_overlap():
    """Overlap 1 doan nghia la mot ma co the thuoc 2 chunk lien ke."""
    from flow1.models import Chunk

    contexts = [
        Chunk("c0", "01", "B1", 1, "S", [("T01-001", "a"), ("T01-002", "b")], False),
        Chunk("c1", "01", "B1", 1, "S", [("T01-002", "b"), ("T01-003", "c")], False),
    ]
    code_map = build_code_map(contexts)
    assert code_map["T01-001"] == (0,)
    assert code_map["T01-002"] == (0, 1)
    assert code_map["T01-003"] == (1,)


def test_map_giu_moi_manh_cua_doan_khong_lo():
    """split_giant tach 1 ma thanh #a/#b — ca hai manh phai vao map."""
    from flow1.models import Chunk

    contexts = [
        Chunk("T06-123#a", "06", "B6", 1, "S", [("T06-123", "phan dau")], False),
        Chunk("T06-123#b", "06", "B6", 1, "S", [("T06-123", "phan sau")], False),
    ]
    assert build_code_map(contexts)["T06-123"] == (0, 1)


def test_chi_so_trong_map_luon_hop_le(sample_segs):
    contexts = chunk_all(sample_segs)
    code_map = build_code_map(contexts)
    for indices in code_map.values():
        for i in indices:
            assert 0 <= i < len(contexts)
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_atomic.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.atomic'`

- [ ] **Step 3: Viết `flow1/src/flow1/atomic.py`**

```python
"""Don vi nguyen tu cho retrieval + map ma doan -> chunk ngu canh.

VI SAO TACH LAM HAI DON VI:
  index   = 700 doan nguyen tu. Ma doan la citation unit, nen xep hang o day
            thi diem tro dung cho, va hai retriever noi nhau bang chinh ma do.
  context = 419 chunk gop cua chunk.py. Model can nhin thay xung quanh moi hieu.

Map `code -> tuple[int, ...]` la DAN XUAT, dung mot lan luc build index, khong
phai file phai bao tri. Mot ma co the tro toi NHIEU context: overlap 1 doan lam
ma nam o hai chunk lien ke, va split_giant tach mot ma thanh #a/#b/#c.
"""

from __future__ import annotations

from flow1.models import Chunk, Seg


def atomic_chunks(segs: list[Seg]) -> list[Chunk]:
    """Moi Seg thanh dung mot Chunk. chunk_id chinh la ma doan."""
    return [
        Chunk(
            chunk_id=seg.code,
            session=seg.session,
            session_title=seg.session_title,
            section_idx=seg.section_idx,
            section_title=seg.section_title,
            parts=[(seg.code, seg.text)],
            has_gap=seg.has_gap,
        )
        for seg in segs
    ]


def build_code_map(contexts: list[Chunk]) -> dict[str, tuple[int, ...]]:
    """Ma doan -> moi chi so context chua no, giu thu tu tang dan."""
    mapping: dict[str, list[int]] = {}
    for i, chunk in enumerate(contexts):
        for code in chunk.seg_codes:
            mapping.setdefault(code, []).append(i)
    return {code: tuple(indices) for code, indices in mapping.items()}
```

- [ ] **Step 4: Viết `flow1/src/flow1/store.py`**

```python
"""Goi mot lan build index thanh mot doi tuong.

Thay cho tuple `(chunks, bm25)` cu: gio retrieve can 4 thu chu khong phai 2,
va tuple 4 phan tu thi khong ai nho duoc thu tu.
"""

from __future__ import annotations

from dataclasses import dataclass

from flow1.models import Chunk


@dataclass(frozen=True)
class Store:
    atomics: list[Chunk]                       # 700 — BM25 va Qdrant xep hang tren day
    contexts: list[Chunk]                      # 419 — nap vao prompt
    code_to_contexts: dict[str, tuple[int, ...]]
    bm25: object                               # BM25Okapi tren atomics
```

- [ ] **Step 5: Sửa `index.py` để build và nạp `Store`**

Thay `build`, `save`, `load`, `build_from_data` trong `flow1/src/flow1/index.py`:

```python
def build(chunks: list[Chunk]) -> BM25Okapi:
    """Dung BM25 tren `index_text` — co prefix session_title > section_title."""
    return BM25Okapi([tokenize(c.index_text) for c in chunks])


def save(store: Store, path: Path = BM25_PATH) -> None:
    """Ghi ca Store vao mot file pickle. Nap lai can rank_bm25 da cai."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(
            {
                "atomics": store.atomics,
                "contexts": store.contexts,
                "code_to_contexts": store.code_to_contexts,
                "bm25": store.bm25,
            },
            handle,
        )


def load(path: Path = BM25_PATH) -> Store:
    """Nap lai Store da luu. Nem `IndexMissing` kem lenh sua neu thieu file."""
    if not path.exists():
        raise IndexMissing(
            f"Chua co index tai {path}. Dung truoc bang:  python -m flow1 index"
        )
    with path.open("rb") as handle:
        blob = pickle.load(handle)
    if "atomics" not in blob:
        raise IndexMissing(
            f"Index tai {path} theo dinh dang cu (chi co chunk gop). Dung lai "
            f"bang:  python -m flow1 index"
        )
    return Store(
        atomics=blob["atomics"],
        contexts=blob["contexts"],
        code_to_contexts=blob["code_to_contexts"],
        bm25=blob["bm25"],
    )


def build_store(segs: list[Seg]) -> Store:
    """Seg -> Store. Atomic de xep hang, chunk gop de lam ngu canh."""
    from flow1.atomic import atomic_chunks, build_code_map
    from flow1.chunk import chunk_all

    atomics = atomic_chunks(segs)
    contexts = chunk_all(segs)
    return Store(
        atomics=atomics,
        contexts=contexts,
        code_to_contexts=build_code_map(contexts),
        bm25=build(atomics),
    )


def build_from_data(data_dir: Path | None = None, path: Path = BM25_PATH) -> int:
    """Doc data pack -> parse -> build store -> ghi dia. Tra so doan nguyen tu."""
    from flow1.parse import TRANSCRIPT_DIR, content_segs, parse_all

    segs = content_segs(parse_all(data_dir or TRANSCRIPT_DIR))
    store = build_store(segs)
    save(store, path)
    return len(store.atomics)
```

Thêm import ở đầu file: `from flow1.models import Chunk, Seg` và `from flow1.store import Store`.

Thông báo `IndexMissing` cho index định dạng cũ là có chủ ý: pickle cũ nạp được nhưng thiếu `atomics` sẽ gây `KeyError` khó hiểu ở tận `retrieve`.

- [ ] **Step 6: Cập nhật fixture `bm25_store`**

Trong `flow1/tests/conftest.py`, đổi fixture để trả `Store`:

```python
@pytest.fixture
def bm25_store(sample_segs):
    from flow1.index import build_store

    return build_store(sample_segs)
```

- [ ] **Step 7: Chạy test**

Run: `uv run pytest flow1/tests/test_flow1_atomic.py -q`
Expected: 9 passed

Run: `uv run pytest flow1/tests -q`
Expected: `test_flow1_index.py` và `test_flow1_retrieve.py` **đỏ** — chúng gọi `load()` mong nhận tuple. Đây là thay đổi hợp đồng có chủ ý. Sửa chúng ở Task 10, không sửa vội ở đây.

- [ ] **Step 8: Commit**

```bash
git add flow1/src/flow1/atomic.py flow1/src/flow1/store.py flow1/src/flow1/index.py flow1/tests/
git commit -m "feat(flow1): don vi nguyen tu cho index, chunk gop cho ngu canh

BM25 chuyen sang index 700 doan nguyen tu — ma doan la citation unit nen
xep hang o day thi diem tro dung cho, va la khoa noi voi Qdrant.
Chunk gop cua chunk.py giu nguyen, doi vai thanh cua so ngu canh.
Map code -> context la dan xuat, dung mot lan luc build.

test_flow1_index va test_flow1_retrieve con do — hop dong load() da doi,
sua o commit sau.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: Nới `find_chunks` cho `session_id` optional

**Files:**
- Modify: `vector-db/src/vector_db/search.py:105-122`
- Test: `vector-db/tests/test_search_contract.py`

**Interfaces:**
- Consumes: `_semantic_search` (đã hỗ trợ `session_id=None` sẵn)
- Produces: `find_chunks(query, session_id: str | None = None, section_id=None, top_k=5, *, exclude_activities=True)`

Cổng 1 cần tìm **xuyên buổi** để phát hiện "top-1 ≈ top-2 khác buổi → hỏi lại". `find_chunks` hiện bắt buộc `session_id` nên không làm được.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `vector-db/tests/test_search_contract.py`:

```python
import pytest

from vector_db import search


def test_find_chunks_khong_can_session_id(monkeypatch):
    """Cong 1 cua flow1 tim xuyen buoi de phat hien mo ho da buoi."""
    ghi = {}

    def fake(query, **kwargs):
        ghi.update(kwargs)
        return ()

    monkeypatch.setattr(search, "_semantic_search", fake)
    search.find_chunks("attention la gi")

    assert ghi["session_id"] is None
    assert ghi["point_type"] == "atomic_chunk"


def test_find_chunks_van_loc_duoc_theo_buoi(monkeypatch):
    ghi = {}

    def fake(query, **kwargs):
        ghi.update(kwargs)
        return ()

    monkeypatch.setattr(search, "_semantic_search", fake)
    search.find_chunks("attention", session_id="T04")

    assert ghi["session_id"] == "T04"


def test_session_id_rong_bi_tu_choi(monkeypatch):
    monkeypatch.setattr(search, "_semantic_search", lambda q, **k: ())
    with pytest.raises(ValueError):
        search.find_chunks("attention", session_id="   ")
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest vector-db/tests/test_search_contract.py -q`
Expected: FAIL — `find_chunks() missing 1 required positional argument: 'session_id'`

- [ ] **Step 3: Sửa `find_chunks`**

```python
def find_chunks(
    query: str,
    session_id: str | None = None,
    section_id: str | None = None,
    top_k: int = 5,
    *,
    exclude_activities: bool = True,
) -> tuple[SearchHit, ...]:
    """Tim doan nguyen tu. session_id=None nghia la tim xuyen ca 6 buoi —
    cong 1 cua flow1 can the de phat hien chu de nam o nhieu buoi."""
    if session_id is not None and not session_id.strip():
        raise ValueError("session_id must not be empty")
    return _semantic_search(
        query,
        point_type="atomic_chunk",
        session_id=session_id,
        section_id=section_id,
        top_k=top_k,
        exclude_activities=exclude_activities,
    )
```

Trong `main()` cùng file, bỏ dòng `parser.error("--session-id is required for chunk search")` ở nhánh `chunk` — giờ không bắt buộc nữa.

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest vector-db/tests/test_search_contract.py -q`
Expected: 3 test mới passed

- [ ] **Step 5: Commit**

```bash
git add vector-db/src/vector_db/search.py vector-db/tests/test_search_contract.py
git commit -m "feat(vector-db): find_chunks cho phep session_id=None de tim xuyen buoi

Cong 1 cua flow1 phai so top-1 voi top-2 khac BUOI de biet co phai hoi lai
khong — khong lam duoc neu bat buoc chot mot buoi tu dau.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: `SemanticBackend` — Qdrant, Null, và đường lùi

**Files:**
- Create: `flow1/src/flow1/semantic.py`, `flow1/tests/test_flow1_semantic.py`

**Interfaces:**
- Consumes: `vector_db.search.find_chunks` (Task 8)
- Produces:
  - `SemanticBackend` Protocol với `rank(query, *, session, k) -> list[tuple[str, float]]`
  - `NullBackend(reason: str)` — trả `[]`, mang `.reason`
  - `QdrantBackend()` — gọi vector-db
  - `default_backend() -> SemanticBackend` — tự chọn, không bao giờ ném ra ngoài

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_semantic.py`:

```python
import pytest

from flow1.semantic import NullBackend, QdrantBackend, default_backend


def test_nullbackend_tra_rong_va_mang_ly_do():
    backend = NullBackend("thieu QDRANT_URL")
    assert backend.rank("attention", session=None, k=5) == []
    assert backend.reason == "thieu QDRANT_URL"


def test_qdrant_backend_doi_hit_thanh_ma_doan_va_diem(monkeypatch):
    class Hit:
        def __init__(self, code, score):
            self.payload = {"citation_id": code}
            self.score = score

    monkeypatch.setattr(
        "vector_db.search.find_chunks",
        lambda q, session_id=None, top_k=5, **kw: (
            Hit("T04-072", 0.91), Hit("T04-071", 0.88),
        ),
    )
    got = QdrantBackend().rank("temperature", session=None, k=5)
    assert got == [("T04-072", 0.91), ("T04-071", 0.88)]


def test_qdrant_backend_truyen_dung_session_xuong_duoi(monkeypatch):
    ghi = {}

    def fake(q, session_id=None, top_k=5, **kw):
        ghi["session_id"] = session_id
        ghi["top_k"] = top_k
        return ()

    monkeypatch.setattr("vector_db.search.find_chunks", fake)
    QdrantBackend().rank("q", session="04", k=7)

    assert ghi["session_id"] == "T04"
    assert ghi["top_k"] == 7


def test_qdrant_backend_bo_hit_thieu_citation_id(monkeypatch):
    class Hit:
        def __init__(self, payload, score):
            self.payload = payload
            self.score = score

    monkeypatch.setattr(
        "vector_db.search.find_chunks",
        lambda q, **kw: (Hit({}, 0.9), Hit({"citation_id": "T01-001"}, 0.8)),
    )
    assert QdrantBackend().rank("q", session=None, k=5) == [("T01-001", 0.8)]


def test_default_backend_lui_em_khi_thieu_cau_hinh(monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)
    backend = default_backend()
    assert isinstance(backend, NullBackend)
    assert "QDRANT_URL" in backend.reason


def test_default_backend_lui_em_khi_import_that_bai(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "https://x")
    monkeypatch.setenv("QDRANT_API_KEY", "k")
    monkeypatch.setenv("OPENAI_API_KEY", "k")

    import builtins

    that = builtins.__import__

    def no_vector_db(name, *args, **kwargs):
        if name.startswith("vector_db"):
            raise ImportError("khong cai vector-db")
        return that(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_vector_db)
    backend = default_backend()
    assert isinstance(backend, NullBackend)


def test_qdrant_backend_khong_bao_gio_nem_ra_ngoai(monkeypatch):
    def no(*a, **k):
        raise ConnectionError("mat mang")

    monkeypatch.setattr("vector_db.search.find_chunks", no)
    with pytest.raises(ConnectionError):
        QdrantBackend().rank("q", session=None, k=5)
```

Ghi chú test cuối: `QdrantBackend.rank` **được phép ném** — việc bắt lỗi và lùi là trách nhiệm của `retrieve` (Task 10), để trace ghi được lý do. Tách vai như vậy giữ mỗi bên một việc.

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_semantic.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.semantic'`

- [ ] **Step 3: Viết `flow1/src/flow1/semantic.py`**

```python
"""Nhanh semantic cua hybrid. Thay backend duoc, hong thi lui em.

TAI SAO CO NullBackend thay vi tra None: retrieve chi co MOT duong code —
`backend.rank(...)` luon goi duoc, chi la co the tra rong. Khong `if backend`.

QdrantBackend.rank DUOC PHEP nem loi. Bat loi va lui la viec cua retrieve,
vi chi retrieve moi co trace de ghi ly do da lui.

LUU Y ma buoi: flow1 dung "04", Qdrant dung "T04". Doi o day, dung chỗ khac.
"""

from __future__ import annotations

import os
from typing import Protocol


class SemanticBackend(Protocol):
    def rank(
        self, query: str, *, session: str | None, k: int
    ) -> list[tuple[str, float]]:
        """[(ma doan, diem cosine)] da sap giam dan."""
        ...

    @property
    def name(self) -> str: ...


class NullBackend:
    """Khong tra ve gi. Chon khi thieu key, thieu mang, hoac --no-semantic."""

    name = "null"

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def rank(self, query: str, *, session: str | None, k: int) -> list[tuple[str, float]]:
        return []


class QdrantBackend:
    """Xep hang doan nguyen tu bang vector trong Qdrant."""

    name = "qdrant"
    reason = ""

    def rank(self, query: str, *, session: str | None, k: int) -> list[tuple[str, float]]:
        from vector_db.search import find_chunks

        hits = find_chunks(
            query,
            session_id=f"T{session}" if session else None,
            top_k=k,
        )
        return [
            (hit.payload["citation_id"], float(hit.score))
            for hit in hits
            if hit.payload.get("citation_id")
        ]


_REQUIRED = ("QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY")


def default_backend() -> SemanticBackend:
    """Tu chon backend. KHONG BAO GIO nem — thieu gi thi lui ve NullBackend."""
    missing = [name for name in _REQUIRED if not os.getenv(name, "").strip()]
    if missing:
        return NullBackend(f"thieu bien moi truong: {', '.join(missing)}")
    try:
        import vector_db.search  # noqa: F401
    except ImportError as exc:
        return NullBackend(f"khong import duoc vector_db: {exc}")
    return QdrantBackend()
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_semantic.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add flow1/src/flow1/semantic.py flow1/tests/test_flow1_semantic.py
git commit -m "feat(flow1): SemanticBackend thay duoc, NullBackend giu mot duong code

default_backend khong bao gio nem: thieu key hay thieu package thi lui ve
NullBackend kem ly do doc duoc. Doi ma buoi 04 <-> T04 dong o day, mot cho.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: RRF trên mã đoạn + nở ngữ cảnh trong `retrieve`

**Files:**
- Modify: `flow1/src/flow1/retrieve.py`, `flow1/tests/test_flow1_retrieve.py`, `flow1/tests/test_flow1_index.py`
- Create: `flow1/tests/test_flow1_hybrid.py`

**Interfaces:**
- Consumes: `Store` (Task 7), `SemanticBackend`/`default_backend` (Task 9), `rrf` từ `flow1.embed`, `trace` (Task 4)
- Produces: `retrieve(query, *, session=None, k=TOP_K, store=None, path=BM25_PATH, backend=None, trace=None) -> Retrieval`.
  `Retrieval.hits` là **chunk ngữ cảnh**; `Hit.bm25` là điểm BM25 thô của **đoạn nguyên tử tốt nhất** trong chunk đó. Nhờ vậy `gates.py`, `prompts.py`, `check.py`, `render.py` không phải sửa dòng nào.

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_hybrid.py`:

```python
import math

from flow1.retrieve import retrieve
from flow1.semantic import NullBackend


class FakeBackend:
    name = "fake"
    reason = ""

    def __init__(self, ranking):
        self._ranking = ranking

    def rank(self, query, *, session, k):
        return self._ranking[:k]


def test_khong_co_backend_thi_bang_bm25_thuan(bm25_store):
    chi_bm25 = retrieve("attention", store=bm25_store, backend=NullBackend("tat"))
    assert [h.chunk.chunk_id for h in chi_bm25.hits]


def test_gate_stats_tinh_tren_bm25_tho_khong_doi_khi_bat_semantic(bm25_store):
    tat = retrieve("attention", store=bm25_store, backend=NullBackend("tat"))
    bat = retrieve(
        "attention",
        store=bm25_store,
        backend=FakeBackend([("T02-001", 0.99)]),
    )
    assert bat.top1_abs == tat.top1_abs
    assert bat.ratio == tat.ratio


def test_semantic_doi_duoc_thu_tu_nap_context(bm25_store):
    tat = retrieve("attention", store=bm25_store, backend=NullBackend("tat"))
    bat = retrieve(
        "attention",
        store=bm25_store,
        backend=FakeBackend([("T02-001", 0.99), ("T04-003", 0.98)]),
    )
    assert [h.chunk.chunk_id for h in bat.hits] != [h.chunk.chunk_id for h in tat.hits]


def test_backend_tra_trung_ma_thi_khong_cong_diem_hai_lan(bm25_store):
    from flow1.trace import Trace

    trace = Trace("attention")
    retrieve(
        "attention",
        store=bm25_store,
        backend=FakeBackend([("T04-002", 0.9), ("T04-002", 0.8)]),
        trace=trace,
    )
    semantic = next(s for s in trace.stages if s.name == "semantic")
    ma = [code for code, _ in semantic.data["top10"]]
    assert len(ma) == len(set(ma))


def test_backend_nem_loi_thi_lui_ve_bm25_va_ghi_ly_do(bm25_store):
    from flow1.trace import Trace

    class Vo:
        name = "vo"

        def rank(self, query, *, session, k):
            raise ConnectionError("mat mang")

    trace = Trace("attention")
    got = retrieve("attention", store=bm25_store, backend=Vo(), trace=trace)

    assert got.hits, "phai van tra ve ket qua BM25 thuan"
    stage = next(s for s in trace.stages if s.name == "semantic")
    assert "mat mang" in stage.data["da_lui"]


def test_ma_khong_co_trong_map_bi_bo_qua_khong_no(bm25_store):
    got = retrieve(
        "attention",
        store=bm25_store,
        backend=FakeBackend([("T99-999", 0.99)]),
    )
    assert got.hits


def test_hit_bm25_la_diem_cua_doan_nguyen_tu_tot_nhat_trong_chunk(bm25_store):
    got = retrieve("attention", store=bm25_store, backend=NullBackend("tat"))
    assert all(h.bm25 >= 0.0 for h in got.hits)
    assert got.hits[0].bm25 >= got.hits[-1].bm25


def test_loc_theo_buoi_van_dung(bm25_store):
    got = retrieve("automation", store=bm25_store, session="02", backend=NullBackend("tat"))
    assert all(h.session == "02" for h in got.hits)


def test_trace_ghi_bang_fuse_co_ca_hai_rank(bm25_store):
    from flow1.trace import Trace

    trace = Trace("attention")
    retrieve(
        "attention",
        store=bm25_store,
        backend=FakeBackend([("T04-002", 0.9)]),
        trace=trace,
    )
    fuse = next(s for s in trace.stages if s.name == "fuse")
    hang = fuse.data["bang"][0]
    assert set(hang) >= {"ma", "rank_bm25", "rank_emb", "rrf"}


def test_query_rong_tra_ve_retrieval_rong(bm25_store):
    got = retrieve("   ", store=bm25_store, backend=NullBackend("tat"))
    assert got.hits == []
    assert got.top1_abs == 0.0
    assert got.ratio == 0.0
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_hybrid.py -q`
Expected: FAIL — `retrieve() got an unexpected keyword argument 'backend'`

- [ ] **Step 3: Viết lại thân `retrieve`**

Thay toàn bộ hàm `retrieve` trong `flow1/src/flow1/retrieve.py`:

```python
def retrieve(
    query: str,
    *,
    session: str | None = None,
    k: int = TOP_K,
    store: Store | None = None,
    path: Path = BM25_PATH,
    backend=None,
    trace=None,
) -> Retrieval:
    """Hybrid BM25 x semantic, fuse bang RRF tren MA DOAN.

    top1_abs va ratio LUON tinh tren BM25 tho cua bang xep hang NGUYEN TU,
    truoc va doc lap voi moi fusion — xem docstring module.
    """
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(query)
    store = store if store is not None else load(path)
    if backend is None:
        from flow1.semantic import default_backend

        backend = default_backend()

    # ---- BM25 tren doan nguyen tu -----------------------------------------
    with trace.stage("bm25") as tdata:
        tokens = tokenize(query)
        tdata["tokens"] = tokens
        if not tokens:
            tdata["ket_luan"] = "query khong con token nao"
            return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

        all_scores = store.bm25.get_scores(tokens)
        keep = [
            i for i, atomic in enumerate(store.atomics)
            if session is None or atomic.session == session
        ]
        tdata["session_filter"] = session
        tdata["n_ung_vien"] = len(keep)
        if not keep:
            tdata["ket_luan"] = f"khong doan nao thuoc buoi {session}"
            return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

        by_code = {store.atomics[i].chunk_id: float(all_scores[i]) for i in keep}
        bm25_order = sorted(by_code, key=lambda c: by_code[c], reverse=True)
        top1_abs, ratio = gate_stats([by_code[c] for c in bm25_order])

        tdata["top10"] = [(c, round(by_code[c], 3)) for c in bm25_order[:10]]
        tdata["top1_abs"] = round(top1_abs, 3)
        tdata["ratio"] = "inf" if ratio == math.inf else round(ratio, 3)

    # ---- Semantic ----------------------------------------------------------
    with trace.stage("semantic") as tdata:
        tdata["backend"] = getattr(backend, "name", type(backend).__name__)
        emb_order: list[str] = []
        emb_scores: dict[str, float] = {}
        try:
            ranked = backend.rank(query, session=session, k=CAND)
        except Exception as exc:
            tdata["da_lui"] = f"{type(exc).__name__}: {exc}"
            tdata["hau_qua"] = "chay BM25 thuan, cong 1 khong doi"
            ranked = []
        else:
            if not ranked:
                tdata["da_lui"] = getattr(backend, "reason", "backend tra rong")
        allowed = set(by_code)
        for code, score in ranked:
            # Dedupe: backend tra trung ma thi RRF se cong diem hai lan cho
            # cung mot doan. Giu lan xuat hien dau (diem cao nhat).
            if code in allowed and code not in emb_scores:
                emb_order.append(code)
                emb_scores[code] = score
        tdata["top10"] = [(c, round(emb_scores[c], 4)) for c in emb_order[:10]]
        tdata["bo_qua_ngoai_pham_vi"] = len(ranked) - len(emb_order)

    # ---- Fuse --------------------------------------------------------------
    with trace.stage("fuse") as tdata:
        if emb_order:
            fused = rrf([bm25_order[:CAND], emb_order[:CAND]], RRF_K)
            final_order = sorted(fused, key=lambda c: fused[c], reverse=True)
        else:
            fused = {c: 1.0 / (RRF_K + r + 1) for r, c in enumerate(bm25_order)}
            final_order = bm25_order

        rank_bm25 = {c: r for r, c in enumerate(bm25_order)}
        rank_emb = {c: r for r, c in enumerate(emb_order)}
        tdata["bang"] = [
            {
                "ma": c,
                "rank_bm25": rank_bm25.get(c),
                "rank_emb": rank_emb.get(c),
                "rrf": round(fused[c], 5),
            }
            for c in final_order[:10]
        ]
        tdata["chi_bm25_tim_ra"] = [c for c in final_order[:10] if c not in rank_emb]
        tdata["chi_vector_tim_ra"] = [
            c for c in final_order[:10] if rank_bm25.get(c, 99) >= CAND
        ]

    # ---- No len chunk ngu canh --------------------------------------------
    with trace.stage("context") as tdata:
        hits: list[Hit] = []
        da_lay: set[int] = set()
        for code in final_order:
            for idx in store.code_to_contexts.get(code, ()):
                if idx in da_lay:
                    continue
                da_lay.add(idx)
                hits.append(
                    Hit(
                        chunk=store.contexts[idx],
                        bm25=by_code[code],
                        emb=emb_scores.get(code),
                        rank=len(hits),
                        score=fused[code],
                    )
                )
                if len(hits) >= k:
                    break
            if len(hits) >= k:
                break
        tdata["chunk_ids"] = [h.chunk.chunk_id for h in hits]
        tdata["n_chars"] = sum(h.chunk.n_chars for h in hits)

    return Retrieval(hits=hits, top1_abs=top1_abs, ratio=ratio)
```

Sửa import ở đầu file: bỏ `from flow1.models import Chunk`, thêm

```python
from flow1.embed import rrf
from flow1.index import BM25_PATH, load, tokenize
from flow1.models import Hit, Retrieval
from flow1.store import Store
from flow1.thresholds import RRF_K
```

Bỏ hai tham số `embeddings` và `query_vector` khỏi chữ ký: nhánh e5 local đã bị thay bằng `SemanticBackend`. `flow1/src/flow1/embed.py` giữ lại **chỉ vì hàm `rrf`** — xoá phần `build_embeddings`/`load_embeddings`/`embed_query`/`_get_model` và bỏ `sentence-transformers` khỏi dependencies.

- [ ] **Step 4: Cập nhật `cli.py` cho `--with-embedding` không còn nghĩa**

Trong `_run_index`, bỏ nhánh `with_embedding` và bỏ argument tương ứng. Thay bằng dòng in:

```python
    print(f"Da index {count} doan nguyen tu.")
    print("Nhanh semantic lay tu Qdrant luc chay — khong can build gi them.")
```

- [ ] **Step 5: Sửa test cũ theo hợp đồng mới**

Trong `flow1/tests/test_flow1_index.py` và `flow1/tests/test_flow1_retrieve.py`, đổi mọi chỗ `chunks, bm25 = load(...)` thành `store = load(...)` rồi dùng `store.atomics` / `store.bm25`. Mọi lời gọi `retrieve(..., store=(chunks, bm25))` đổi thành `store=build_store(segs)`. Mọi test kỳ vọng `retrieve` trả chunk gộp theo thứ tự BM25 thuần phải thêm `backend=NullBackend("test")` để không chạm mạng.

- [ ] **Step 6: Chạy test**

Run: `uv run pytest flow1/tests/test_flow1_hybrid.py -q`
Expected: 10 passed

Run: `uv run pytest flow1/tests -q`
Expected: toàn bộ xanh

- [ ] **Step 7: Dựng lại index thật và thử tay**

Run: `uv run python -m flow1 index`
Expected: `Da index 645 doan nguyen tu.` — con số là số đoạn sau khi bỏ 55 `is_activity` (700 − 55). **Ghi lại con số thật**; nếu không phải 645 thì `content_segs` đang lọc khác dự kiến, dừng lại tìm hiểu trước khi đi tiếp.

Run: `uv run python -m flow1 ask "cơ chế attention là gì" --trace 2>&1 | tail -40`
Expected: bảng trace hiện đủ các chặng; chặng `semantic` ghi `da_lui` nếu chưa có key Qdrant.

- [ ] **Step 8: Commit**

```bash
git add flow1/ 
git commit -m "feat(flow1): hybrid BM25 x Qdrant, fuse RRF tren ma doan

Hai retriever cung xep hang 700 doan nguyen tu, noi nhau bang ma doan chu
khong bang chi so mang. Sau fuse, moi ma no ra chunk gop chua no lam ngu canh.

Giu nguyen bat bien: top1_abs va ratio luon tinh tren BM25 THO cua bang xep
hang nguyen tu, doc lap voi fusion — nen cong 1 quyet dinh y het nhau du bat
hay tat semantic, va mot lan hieu chinh T1 dung cho ca hai che do.

Backend nem loi -> lui ve BM25 thuan, ghi ly do vao trace, khong nem ra
nguoi dung. Bo nhanh e5 local, giu lai ham rrf.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: Hiệu chỉnh lại T1 trên đơn vị nguyên tử

**Files:**
- Modify: `flow1/scripts/calibrate_t1.py`, `flow1/src/flow1/thresholds.py`, `eval/t1/distribution.md`

**Interfaces:**
- Consumes: `retrieve` (Task 10), `eval/t1/questions.jsonl` (30 câu, đã có)
- Produces: `T1_ABS`, `T1_RATIO` mới, đo trên đơn vị nguyên tử

**Đây là hệ quả bắt buộc của Task 7**, không phải việc tuỳ chọn: BM25 đổi đơn vị thì phân bố điểm đổi, `T1_RATIO = 1.20` hết hiệu lực.

- [ ] **Step 1: Giữ lại bảng cũ trước khi ghi đè**

```bash
cp eval/t1/distribution.md eval/t1/distribution-truoc-nguyen-tu.md
```

Thêm dòng đầu vào file vừa sao chép:

```markdown
> **LƯU TRỮ.** Bảng này đo khi BM25 còn index 419 chunk gộp. Giữ lại làm bằng
> chứng cho phương án bị thay — xem `distribution.md` cho bản đang có hiệu lực.
```

- [ ] **Step 2: Sửa `calibrate_t1.py` cho đường dẫn và backend mới**

Sửa `measure` để không chạm mạng — hiệu chỉnh T1 phải tất định:

```python
def measure(questions: list[dict]) -> list[dict]:
    from flow1.semantic import NullBackend

    backend = NullBackend("hieu chinh T1 chay tren BM25 tho, khong can semantic")
    rows = []
    for q in questions:
        r = retrieve(q["text"], backend=backend)
        rows.append({
            **q,
            "top1_abs": r.top1_abs,
            "ratio": r.ratio,
            "top_session": r.hits[0].session if r.hits else "—",
            "top_section": r.hits[0].section_title if r.hits else "—",
        })
    return rows
```

Sửa `sys.path.insert` và `ROOT`:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
...
ROOT = Path(__file__).resolve().parents[2]
```

Sửa dòng "Cách kiểm lại" ở cuối để khớp lệnh mới:

```python
    lines += ["", "## Cách kiểm lại", "",
              "```", "uv run python flow1/scripts/calibrate_t1.py", "```", ""]
```

- [ ] **Step 3: Chạy hiệu chỉnh**

Run: `uv run python flow1/scripts/calibrate_t1.py`
Expected: in ra `Đề xuất: T1_ABS = <x> · T1_RATIO = <y> → chặn <n>/10 · qua <m>/20`

**ĐIỂM DỪNG BẮT BUỘC.** Đọc dòng cuối của `eval/t1/distribution.md`:

- Nếu có **"Hai phân bố tách được"** và chặn **10/10** → đi tiếp Step 4.
- Nếu có **"KHÔNG tách được hoàn toàn"** → **dừng lại, báo người dùng**, đưa cả hai bảng (cũ và mới) và hỏi hướng xử lý. **Không tự nới ngưỡng, không tự quay về đơn vị cũ.** Script đã tự ghi phần "hệ quả" vào file — đó là bằng chứng trung thực cho R4, không phải thất bại phải giấu.

- [ ] **Step 4: Cập nhật `thresholds.py`**

Sửa hai hằng số theo output script, và cập nhật docstring:

```python
"""Ngưỡng của cổng 1. CHỈ CHỨA SỐ — không hàm, không logic. Chủ: M2.

...

TRẠNG THÁI: T1_ABS và T1_RATIO dưới đây đo trên ĐƠN VỊ NGUYÊN TỬ (700 đoạn),
sau khi retrieve chuyển sang hybrid. Bản đo trên 419 chunk gộp lưu ở
eval/t1/distribution-truoc-nguyen-tu.md.
Kiểm lại bằng:  uv run python flow1/scripts/calibrate_t1.py
Sửa hai số này thì phải chạy lại script và cập nhật distribution.md cùng lúc.
"""
```

- [ ] **Step 5: Chạy lại toàn bộ test flow1**

Run: `uv run pytest flow1/tests -q`
Expected: xanh. Nếu có test hardcode `T1_RATIO == 1.20` thì sửa test đọc từ `thresholds` thay vì gõ số.

- [ ] **Step 6: Commit — hai số và hai bảng đi CÙNG một commit**

```bash
git add flow1/src/flow1/thresholds.py flow1/scripts/calibrate_t1.py eval/t1/
git commit -m "fix(flow1): hieu chinh lai T1 tren don vi nguyen tu

Doi don vi index tu 419 chunk gop sang 700 doan nguyen tu lam phan bo diem
BM25 doi -> T1_RATIO=1.20 het hieu luc. Do lai tren dung 30 cau cu.
Bang cu giu o distribution-truoc-nguyen-tu.md lam bang chung cho phuong an
bi thay.

Hai so va hai bang di cung mot commit, dung luat file thresholds tu ghi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 12: `graph-db` chạy được, ngoài luồng

**Files:**
- Modify: `graph-db/src/graph_db/connection.py`, `graph-db/scripts/query_neo4j.py`
- Create: `graph-db/tests/test_graph_db_connection.py`, `graph-db/README.md`

**Interfaces:**
- Consumes: `NEO4J_URL`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` (Task 2)
- Produces: `graph_db.get_driver()`, `get_database()`, `query()` — **không package nào trong đường chạy được import**

- [ ] **Step 1: Viết test thất bại**

Tạo `graph-db/tests/test_graph_db_connection.py`:

```python
import pytest


def test_thieu_bien_thi_bao_ro_bien_nao(monkeypatch):
    from graph_db import connection

    for name in ("NEO4J_URL", "NEO4J_USERNAME", "NEO4J_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    connection.get_driver.cache_clear()

    with pytest.raises(RuntimeError) as exc:
        connection.get_driver()
    assert "NEO4J_URL" in str(exc.value)


def test_query_neo4j_import_duoc():
    """File nay tung import src.config.config va src.utils.logger — hai module
    khong ton tai trong repo. Test giu cho no khong chet lai."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "query_neo4j.py"
    spec = importlib.util.spec_from_file_location("query_neo4j", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "run_sample_queries")


def test_khong_package_nao_trong_duong_chay_import_graph_db():
    """Neo4j NGOAI LUONG — dieu kiem nay giu no o do."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for package in ("flow1/src", "summarizer/src", "vector-db/src"):
        for file in (root / package).rglob("*.py"):
            text = file.read_text(encoding="utf-8")
            assert "graph_db" not in text, f"{file} import graph_db"


@pytest.mark.live
def test_ket_noi_that_duoc():
    from graph_db import get_driver

    get_driver().verify_connectivity()
```

Tạo `graph-db/tests/__init__.py` rỗng.

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest graph-db/tests -q`
Expected: FAIL — `test_query_neo4j_import_duoc` đỏ vì `ModuleNotFoundError: No module named 'src'`

- [ ] **Step 3: Sửa `query_neo4j.py`**

Thay đầu file (bỏ `sys.path.insert` và hai import chết):

```python
"""Cac query mau de kham pha du lieu trong graph database.

NGOAI LUONG: khong package nao trong duong chay san pham import file nay.
Chay tay:  uv run python graph-db/scripts/query_neo4j.py
"""

from __future__ import annotations

import logging

from graph_db import query

logger = logging.getLogger(__name__)
```

Sửa thân `run_sample_queries` dùng `query(...)` thay cho `Neo4jClientManager`. Nếu hàm còn tham chiếu `setup_logging`, thay bằng `logging.basicConfig(level=logging.INFO)` trong `if __name__ == "__main__":`.

- [ ] **Step 4: Đảm bảo `connection.py` báo đúng biến thiếu**

Kiểm tra `_REQUIRED` trong `graph-db/src/graph_db/connection.py` là `("NEO4J_URL", "NEO4J_USERNAME", "NEO4J_PASSWORD")` — đã đúng, không đổi. Chỉ xác nhận thông báo lỗi có kèm tên biến.

- [ ] **Step 5: Viết `graph-db/README.md`**

```markdown
# graph-db — Neo4j knowledge graph

> **NGOÀI LUỒNG.** Không package nào trong đường chạy sản phẩm import `graph_db`.
> Có một test giữ điều đó: `tests/test_graph_db_connection.py`.

## Vì sao không dùng cho RAG hay tóm tắt

Ba lý do, chi tiết ở `docs/superpowers/specs/2026-07-30-hybrid-rag-tai-co-cau-design.md` §7:

1. KG được sinh RA TỪ transcript bằng LLM — concept là ý kiến của model, không
   mang bảo đảm có mã đoạn thật, nên phá chiều *truy vết*.
2. Luồng 2 nạp trọn buổi nên không thiếu thông tin để graph đi tìm hộ.
3. Chỗ graph mạnh nhất là tóm tắt đa buổi — đúng thứ non-goal #4 của canvas cấm.

Giữ lại vì đây là **phương án đã cân nhắc và loại bằng lý do**, không phải code chết.

## Chạy

```bash
uv run python graph-db/scripts/check_neo4j.py        # smoke test ket noi
uv run python graph-db/scripts/ingest_transcripts.py # ingest (can OPENAI_API_KEY)
uv run python graph-db/scripts/query_neo4j.py        # query mau
```

Cần `NEO4J_URL`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — xem `.env.example`.
```

- [ ] **Step 6: Chạy test để chắc nó xanh**

Run: `uv run pytest graph-db/tests -q`
Expected: 3 passed, 1 skipped (`live`)

- [ ] **Step 7: Commit**

```bash
git add graph-db/
git commit -m "fix(graph-db): va import chet, them test giu Neo4j ngoai luong

query_neo4j.py dang import src.config.config va src.utils.logger — hai module
khong ton tai trong repo. Thay bang graph_db.query.
Them test quet ca flow1/summarizer/vector-db de chac khong ai import graph_db.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 13: Panel trace trong Streamlit

**Files:**
- Modify: `flow1/app/app.py`

**Interfaces:**
- Consumes: `new_trace` (Task 4), `render_trace` (Task 6), `Result.trace` (Task 5)
- Produces: expander "Vì sao ra kết quả này" trong giao diện

- [ ] **Step 1: Tìm chỗ gọi `ask` trong app**

Run: `grep -n "ask(" flow1/app/app.py`

- [ ] **Step 2: Bật trace và hiện panel**

Tại chỗ gọi `ask`, đổi thành:

```python
from flow1.trace import new_trace

trace = new_trace(question, enabled=True)
result = ask(question, session=session, segs=segs, trace=trace)
```

Sau khi hiển thị câu trả lời, thêm:

```python
with st.expander("Vì sao ra kết quả này"):
    for stage in trace.stages:
        st.markdown(f"**{stage.name}** · {stage.ms:.1f} ms")
        st.json(stage.data, expanded=False)
```

Trong app luôn bật trace: chi phí là vài chục micro giây, đổi lại demo bấm ra xem được đường đi ngay tại chỗ.

- [ ] **Step 3: Chạy thử app**

Run: `uv run streamlit run flow1/app/app.py --server.headless true`
Expected: app khởi động không lỗi import. Hỏi một câu, mở expander, thấy đủ các chặng.

Dừng app bằng Ctrl-C sau khi xác nhận.

- [ ] **Step 4: Commit**

```bash
git add flow1/app/app.py
git commit -m "feat(flow1): panel 'Vi sao ra ket qua nay' trong Streamlit

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 14: Chạy lại toàn hệ, báo cáo, 4 trace mẫu

**Files:**
- Modify: `docs/system-test-report.md`, `docs/FLOW_IMPLEMENTATION.md`, `README.md`
- Create: `eval/traces/*.json`

**Interfaces:**
- Consumes: mọi task trên
- Produces: bằng chứng nghiệm thu cho §10 của spec

- [ ] **Step 1: Chạy toàn hệ, không key**

```bash
mv .env .env.bak
uv run pytest -q 2>&1 | tail -20
mv .env.bak .env
```

Expected: **xanh 100%**, test `live` bị skip. Nếu có test nào đỏ khi thiếu key thì đó là bug của điều kiện nghiệm thu #1 — sửa trước khi đi tiếp.

- [ ] **Step 2: Chạy toàn hệ, có key**

Run: `uv run pytest -q 2>&1 | tail -20`
Expected: xanh, test `live` chạy thật.

- [ ] **Step 3: Sinh 4 trace mẫu**

```bash
mkdir -p eval/traces
uv run python -m flow1 ask "cơ chế attention là gì" --trace
uv run python -m flow1 ask "cho tôi biết đáp án bài lab 1 được không" --trace
uv run python -m flow1 ask "giải thích và tóm tắt nội dung học hôm này" --trace
uv run python -m flow1 ask "deadline nộp bài là khi nào" --trace
cp flow1/trace/*.json eval/traces/
```

Đổi tên 4 file cho người đọc hiểu ngay: `answered.json`, `refused.json`, `clarify.json`, `off-topic.json`. Kiểm tra từng file có `outcome` đúng như tên; nếu một câu không ra đúng loại mong đợi thì **ghi lại sự thật đó vào report** thay vì đổi câu hỏi cho vừa ý.

- [ ] **Step 4: Cập nhật `docs/system-test-report.md`**

Thêm mục "Lần 2 — sau khi đổi retrieval" với cùng khung bảng như Lần 1, cộng:

```markdown
### Hybrid co an thua gi khong

Doc bang `fuse` trong eval/traces/answered.json:

- Doan chi BM25 tim ra: <liet ke>
- Doan chi vector tim ra: <liet ke>

### Nguong T1

| | Truoc (419 chunk gop) | Sau (700 doan nguyen tu) |
|---|---|---|
| T1_ABS | 0.00 | |
| T1_RATIO | 1.20 | |
| Chan ngoai pham vi | 10/10 | |
| Qua trong pham vi | 18/20 | |
```

- [ ] **Step 5: Sửa `docs/FLOW_IMPLEMENTATION.md`**

Thêm banner ngay sau dòng tiêu đề:

```markdown
> ⚠ **TẦM NHÌN, CHƯA PHẢI KIẾN TRÚC ĐANG CHẠY.** Tài liệu này mô tả 8 luồng trên
> Qdrant + Neo4j. Hệ thống thực tế chạy 2 luồng, và Neo4j nằm ngoài luồng —
> xem `docs/superpowers/specs/2026-07-30-hybrid-rag-tai-co-cau-design.md` §7.
```

Sửa `1536 dimensions` thành `768` trong mục 2.2 (3 chỗ) cho khớp collection đã build.

- [ ] **Step 6: Cập nhật `README.md`**

Thêm mục "Chạy thử":

```markdown
## Chạy thử

```bash
uv sync --all-packages
cp .env.example .env      # điền key vào
uv run python scripts/check_env.py

uv run python -m flow1 index
uv run python -m flow1 ask "cơ chế attention là gì" --trace
uv run pytest             # xanh không cần key
uv run pytest -m live     # cần key
```
```

- [ ] **Step 7: Commit**

```bash
git add docs/ eval/traces/ README.md
git commit -m "docs: bao cao kiem thu lan 2 + 4 trace mau lam bang chung

FLOW_IMPLEMENTATION.md them banner 'tam nhin, chua phai kien truc dang chay'
va sua 1536 -> 768 cho khop collection da build.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Đối chiếu với "định nghĩa xong" của spec

| # | Điều kiện | Task |
|---|---|---|
| 1 | `uv run pytest` xanh không cần key | 1, 14 |
| 2 | `uv run pytest -m live` xanh khi có key | 12, 14 |
| 3 | `check_env.py` báo đúng; `.env.example` khớp code | 2 |
| 4 | `--trace` sinh JSON đủ chặng, so sánh ghi cả hai vế | 4, 5, 6 |
| 5 | Mất mạng → BM25 thuần, trace ghi lý do | 9, 10 |
| 6 | Bảng `fuse` chỉ ra đoạn nào chỉ BM25 / chỉ vector tìm ra | 10, 14 |
| 7 | `thresholds.py` + `distribution.md` cùng commit, bảng cũ giữ | 11 |
| 8 | `system-test-report.md` có trước và sau | 3, 14 |
| 9 | 4 trace mẫu trong `eval/traces/` | 14 |
| 10 | `graph-db` chạy được, không ai import | 12 |
