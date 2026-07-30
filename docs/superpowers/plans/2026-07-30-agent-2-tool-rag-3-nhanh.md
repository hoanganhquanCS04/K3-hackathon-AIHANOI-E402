# Agent 2 tool + RAG 3 nhánh — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng agent tool-calling với 2 tool (tra cứu, tóm tắt), trong đó tool tra cứu viết lại query bằng 1 lời gọi LLM rồi fuse 3 nhánh retrieve (BM25 · Qdrant · Neo4j KG) bằng RRF trên mã đoạn, bật/tắt được từng nhánh trên UI để đo hiệu năng.

**Architecture:** Rule tất định chặn trước agent. Ba retriever cùng interface `Retriever`, cùng xếp hạng **700 đoạn nguyên tử**, nối nhau bằng **mã đoạn `Txx-NNN`** — Neo4j có `Turn {id}` đúng khoá đó nên không cần lớp ánh xạ. Cổng 1 luôn quyết định trên **điểm BM25 thô**, độc lập với fusion và với toggle.

**Tech Stack:** Python 3.13 · uv workspace · rank_bm25 · qdrant-client · neo4j · openai (embedding + tool-calling) · pydantic · pytest · Streamlit

**Spec:** `docs/superpowers/specs/2026-07-30-agent-2-tool-rag-3-nhanh-design.md`
**Spec nền (còn hiệu lực trừ §7):** `docs/superpowers/specs/2026-07-30-hybrid-rag-tai-co-cau-design.md`

**Đã xong trước kế hoạch này:** Task 1 (uv workspace 4 package) và Task 2 (thống nhất biến môi trường) của kế hoạch `2026-07-30-hybrid-rag-tai-co-cau.md`. Baseline hiện tại: **353 passed, 8 skipped**. Kế hoạch này bắt đầu từ Task 3 và thay thế Task 3-14 của kế hoạch đó.

## Global Constraints

- **`uv run pytest` ở gốc phải xanh mà KHÔNG cần API key nào.** Test chạm mạng bắt buộc mang `@pytest.mark.live`. Baseline không được tụt dưới 353 passed.
- **Khoá nối ba retriever luôn là mã đoạn `Txx-NNN`**, không bao giờ là chỉ số mảng.
- **BM25 luôn chạy.** Toggle chỉ điều khiển BM25 có góp vào fusion hay không. Cổng 1 luôn quyết định trên điểm BM25 thô đã sắp giảm dần. `gate_stats` có guard raise sẵn — đừng gỡ.
- **KG mở rộng recall, không mở rộng thẩm quyền.** Không một chữ nào của `Concept.description` được đưa vào prompt sinh câu trả lời. Chỉ `Turn.id` và nguyên văn Turn.
- **Mọi retriever phải lùi êm.** Thiếu key, mất mạng, service chết → trả rỗng kèm lý do đọc được, không ném ra người dùng.
- **Không nới ngưỡng T1 cho đẹp số.** Không tách được hai phân bố thì ghi thật và dừng lại báo.
- **Không commit API key.** `.env` gitignored, đừng sửa nó.
- Commit message **tiếng Việt không dấu**, kết bằng `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Mọi lệnh chạy qua `uv run` từ gốc repo.

## File Structure

| File | Trách nhiệm |
|---|---|
| `flow1/src/flow1/trace.py` | `Stage` · `Trace` · `NullTrace` · `new_trace` — chỉ ghi chép |
| `flow1/src/flow1/trace_render.py` | Trace → bảng người đọc được |
| `flow1/src/flow1/atomic.py` | `atomic_chunks` · `build_code_map` |
| `flow1/src/flow1/store.py` | `Store` — gói 4 thứ retrieve cần |
| `flow1/src/flow1/retrievers.py` | `Retriever` Protocol · `BM25Retriever` · `QdrantRetriever` · `Neo4jRetriever` · `NullRetriever` |
| `flow1/src/flow1/rewrite.py` | 1 LLM call → `RewrittenQuery{keywords, cau_hoi, thuc_the}` |
| `flow1/src/flow1/retrieve.py` | fuse RRF 3 nhánh theo toggle, nở context, ghi trace |
| `flow1/src/flow1/tools.py` | `tra_cuu` · `tom_tat` — hai tool của agent |
| `flow1/src/flow1/agent.py` | rule gate + vòng tool-calling |
| `graph-db/src/graph_db/retrieve.py` | Cypher concept → Turn |
| `flow1/app/app.py` | 3 toggle + bảng so sánh nhánh + panel trace |

**Không đụng tới:** `gates.py`, `prompts.py`, `check.py`, `render.py`, `models.py`, `chunk.py`, `parse.py`. `Retrieval.hits` vẫn là chunk ngữ cảnh với `Hit.bm25` là điểm nguyên tử tốt nhất trong chunk — nhờ vậy 4 cổng và bộ render không biết bên dưới đã đổi.

---

## Task 3: Vá 2 finding treo của Task 2 + báo cáo nền

**Files:**
- Modify: `.env.example`, `scripts/check_env.py`
- Test: `scripts/tests/test_check_env.py`
- Create: `docs/system-test-report.md`

**Interfaces:**
- Consumes: `check_env(environ) -> list[str]`, `REQUIREMENTS` (đã có từ Task 2)
- Produces: `REQUIREMENTS` có thêm test đối chiếu với config thật

Review Task 2 để lại 2 finding Important chưa xử. Task này đóng chúng, cộng chụp trạng thái nền trước khi đổi kiến trúc.

- [ ] **Step 1: Viết test thất bại cho finding #2**

Finding: 3 test hiện có tự dựng input **từ chính `REQUIREMENTS`**, nên `REQUIREMENTS` sai thì không test nào bắt được. Thêm test đối chiếu với module config thật.

Thêm vào `scripts/tests/test_check_env.py`:

```python
def test_requirements_khop_voi_bien_ma_qdrant_that_su_doi():
    """REQUIREMENTS phai khop code THAT, khong phai khop chinh no.

    Neu ai do them mot bien bat buoc vao QdrantStore ma quen cap nhat
    REQUIREMENTS thi check_env.py se bao 'OK' nham — dung loi ma task nay
    ton tai de chan.
    """
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    src = Path(__file__).resolve().parents[2] / "vector-db" / "src" / "vector_db"
    text = (src / "qdrant_store.py").read_text(encoding="utf-8")
    for name in ("QDRANT_URL", "QDRANT_API_KEY"):
        assert name in text, f"{name} khong con duoc qdrant_store.py nhac toi"
        assert name in REQUIREMENTS["vector-db"]


def test_requirements_khop_voi_bien_ma_graph_db_that_su_doi():
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    conn = (
        Path(__file__).resolve().parents[2]
        / "graph-db" / "src" / "graph_db" / "connection.py"
    )
    text = conn.read_text(encoding="utf-8")
    for name in REQUIREMENTS["graph-db"]:
        assert name in text, f"REQUIREMENTS khai {name} ma connection.py khong doc"


def test_neo4j_database_co_trong_env_example_du_khong_bat_buoc():
    """connection.py:45 co doc NEO4J_DATABASE (co mac dinh 'neo4j').

    Khong bat buoc nen KHONG vao REQUIREMENTS, nhung phai co mat trong
    .env.example de nguoi dung Neo4j tu host biet duong doi.
    """
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    example = Path(__file__).resolve().parents[2] / ".env.example"
    assert "NEO4J_DATABASE" in example.read_text(encoding="utf-8")
    assert "NEO4J_DATABASE" not in REQUIREMENTS["graph-db"]
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest scripts/tests -q`
Expected: FAIL — `test_neo4j_database_co_trong_env_example_du_khong_bat_buoc` đỏ vì `.env.example` không còn biến đó.

- [ ] **Step 3: Trả `NEO4J_DATABASE` vào `.env.example`**

Trong mục Neo4j của `.env.example`, sửa thành:

```bash
# --- Neo4j (nhanh KG cua tool tra cuu) ---
NEO4J_URL=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
# Tuy chon. Mac dinh 'neo4j'. Aura Free chi co dung mot database ten neo4j,
# chi can dat khi tu host va dat ten khac. Doc boi graph_db/connection.py.
NEO4J_DATABASE=neo4j
```

Sửa luôn dòng chú thích cũ nói Neo4j "NGOAI LUONG" — giờ nó là nhánh thứ ba của tool tra cứu.

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest scripts/tests -q`
Expected: 6 passed

- [ ] **Step 5: Thu số liệu nền**

Run: `uv run pytest -q 2>&1 | tail -20`
Run: `uv run pytest --collect-only -q 2>&1 | tail -3`
Run: `uv run python scripts/check_env.py`

Chạy thêm để biết Neo4j sống hay chết (kết quả nào cũng ghi lại, không sửa gì):

```bash
uv run python graph-db/scripts/check_neo4j.py
```

- [ ] **Step 6: Viết `docs/system-test-report.md`**

Điền số thật đo được, **không làm tròn cho đẹp**:

```markdown
# Bao cao kiem thu toan he

## Lan 1 — truoc khi doi kien truc retrieve

**Ngay:** <ngay chay> · **Commit:** <sha>

| Package | Collect | Pass | Fail | Skip |
|---|---|---|---|---|
| flow1 | | | | |
| vector-db | | | | |
| summarizer | | | | |
| graph-db | | | | |
| scripts | | | | |

### Trang thai ha tang

- `scripts/check_env.py`: <output>
- Neo4j: <song / chet + thong bao loi nguyen van>
- Qdrant collection: vlearn_transcripts_openai_small_768_v1, 802 point
  (700 atomic + 96 section + 6 session_toc), 768 chieu — theo
  vector-db/artifacts/manifest.json

### Da hong truoc Task 1 (da sua)

- vector-db va summarizer khong collect noi test: moi package mot venv rieng.
- .env khai QDRANT_HOST/PORT nhung vector-db doc QDRANT_URL.

### Con do bay gio

<liet ke tung test do + ly do, KHONG bo qua cai nao. Neu khong co thi ghi "khong co">
```

- [ ] **Step 7: Commit**

```bash
git add .env.example scripts/ docs/system-test-report.md
git commit -m "fix(config): tra NEO4J_DATABASE ve .env.example, them test doi chieu

Review Task 2 tim ra 2 loi:
- NEO4J_DATABASE co duoc graph_db/connection.py:45 doc that (co mac dinh
  'neo4j') nhung bi xoa khoi .env.example voi ly do sai la 'khong ai doc'.
  Tra lai duoi dang tuy chon, khong dua vao REQUIREMENTS vi khong bat buoc.
- 3 test cu tu dung input tu chinh REQUIREMENTS nen khong the bat duoc
  REQUIREMENTS sai. Them 3 test doi chieu voi module config that.

Kem bao cao kiem thu toan he lan 1.

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
  - `Trace(query: str)` với `.run_id: str`, `.stages: list[Stage]`, `.stage(name) -> ContextManager[dict]`, `.to_dict() -> dict`, `.save(dir: Path | None) -> Path`
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
    for name in ("rule_gate", "rewrite", "bm25", "qdrant", "neo4j", "fuse"):
        with trace.stage(name):
            pass
    assert [s.name for s in trace.stages] == [
        "rule_gate", "rewrite", "bm25", "qdrant", "neo4j", "fuse"
    ]


def test_loi_trong_stage_van_duoc_ghi_roi_moi_nem_tiep():
    trace = Trace("q")
    with pytest.raises(ValueError):
        with trace.stage("neo4j") as data:
            data["backend"] = "neo4j"
            raise ValueError("mat mang")

    assert trace.stages[0].name == "neo4j"
    assert trace.stages[0].data["backend"] == "neo4j"
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
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_trace.py -q`
Expected: 8 passed

- [ ] **Step 5: Thêm `flow1/trace/` vào `.gitignore`**

Kiểm tra dòng đó đã có chưa (Task 1 đã thêm). Nếu chưa thì thêm.

- [ ] **Step 6: Commit**

```bash
git add flow1/src/flow1/trace.py flow1/tests/test_flow1_trace.py
git commit -m "feat(flow1): trace debug theo chang, NullTrace giu code sach

NullTrace cung API voi Trace nen khong co `if trace is not None` nao rai
trong duong chay — tat va bat trace di qua dung mot duong code.
Loi trong stage duoc ghi lai roi moi nem tiep.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: `trace_render.py` + `--trace` trên CLI

**Files:**
- Create: `flow1/src/flow1/trace_render.py`, `flow1/tests/test_flow1_trace_render.py`
- Modify: `flow1/src/flow1/cli.py`, `flow1/src/flow1/ask.py`

**Interfaces:**
- Consumes: `Trace`, `NullTrace`, `new_trace` (Task 4)
- Produces:
  - `render_trace(trace) -> str` — bảng nhiều dòng
  - `ask(..., trace=None)`; `Result` có thêm field `trace: object | None = None`
  - `python -m flow1 ask "..." --trace`

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


def test_hien_dict_long_nhau_khong_no():
    trace = Trace("q")
    with trace.stage("fuse") as data:
        data["bang"] = [{"ma": "T01-001", "rank_bm25": 0, "rrf": 0.0164}]

    text = render_trace(trace)
    assert "T01-001" in text


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

from typing import Any

_WIDTH = 72


def _fmt_value(value: Any) -> str:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return "\n".join(
            "        " + "  ".join(f"{k}={v}" for k, v in row.items())
            for row in value[:10]
        )
    if isinstance(value, list) and value and isinstance(value[0], (list, tuple)):
        return "\n".join(f"        {row[0]}  {row[1]}" for row in value[:10])
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:12])
    return str(value)


def render_trace(trace) -> str:
    lines = [
        "",
        "=" * _WIDTH,
        f"TRACE {trace.run_id}",
        f"  hoi: {trace.query}",
        "=" * _WIDTH,
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
    lines.append("=" * _WIDTH)
    return "\n".join(lines)
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_trace_render.py -q`
Expected: 4 passed

- [ ] **Step 5: Thêm `trace` vào `ask.py`**

Thêm `import math` ở đầu file. Thêm field vào `Result`:

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

Truyền trace vào retrieve: `retrieval = retrieve(question, session=session, store=store, path=path, trace=trace)`

Bọc cổng 1 — **đây là chỗ luật "ghi cả hai vế" phải thấy được**:

```python
    with trace.stage("gate1") as tdata:
        from flow1.thresholds import T1_ABS, T1_RATIO

        decision = gate1(retrieval)
        tdata["top1_abs"] = retrieval.top1_abs
        tdata["ratio"] = "inf" if retrieval.ratio == math.inf else retrieval.ratio
        tdata["T1_ABS"] = T1_ABS
        tdata["T1_RATIO"] = T1_RATIO
        tdata["action"] = decision.action
        ly_do = []
        if retrieval.top1_abs < T1_ABS:
            ly_do.append(f"top1_abs={retrieval.top1_abs:.2f} < T1_ABS={T1_ABS}")
        if retrieval.ratio < T1_RATIO:
            ly_do.append(f"ratio={retrieval.ratio:.2f} < T1_RATIO={T1_RATIO}")
        tdata["vi_sao"] = " va ".join(ly_do) if ly_do else "ca hai nguong deu qua"
```

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
                          intent=intent, decision=decision, retrieval=retrieval,
                          trace=trace)
        tdata["status"] = answer.status
        tdata["n_claim"] = len(answer.claims)
```

```python
    with trace.stage("gate3") as tdata:
        verdict = check(answer, retrieval, segs, check_citations=check_citations)
        tdata["status"] = verdict.status
        tdata["n_claim_qua"] = len(verdict.claims)
        tdata["drops"] = [(d.kind, d.claim_text[:60]) for d in verdict.drops]
        tdata["student_codes"] = verdict.student_codes
        tdata["gap_codes"] = verdict.gap_codes
```

Thêm `trace=trace` vào **mọi** lệnh `return Result(...)` còn lại.

- [ ] **Step 6: Thêm `trace` vào `retrieve.py`**

Đổi chữ ký thêm `trace=None`. Ngay đầu thân hàm:

```python
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(query)
```

Bọc toàn bộ phần BM25 hiện có trong `with trace.stage("bm25") as tdata:` và ghi `tdata["tokens"]`, `tdata["n_ung_vien"]`, `tdata["top10"]`, `tdata["top1_abs"]`, `tdata["ratio"]`.

**Biết trước:** Task 10 viết đè toàn bộ `retrieve.py`. Phần sửa ở bước này là tạm — cái sống sót là `ask.py` và việc có trace chạy thật trên đường chạy cũ để đối chiếu trước/sau.

- [ ] **Step 7: Gắn `--trace` vào CLI**

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
        print(f"Trace da ghi: {trace.save()}", file=sys.stderr)

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

- [ ] **Step 8: Viết test cho phần gắn kết**

Tạo `flow1/tests/test_flow1_trace_wiring.py`:

```python
from flow1.ask import ask
from flow1.models import Intent
from flow1.trace import NullTrace, Trace


def _intent_noi_dung(system, blocks, schema):
    return Intent(label="nội_dung_khoá", reason="test")


def _no_model(*args):
    raise RuntimeError("khong goi model trong test")


def test_ask_ghi_stage_gate0_bm25_gate1(bm25_store):
    trace = Trace("attention la gi")
    ask("cơ chế attention là gì", store=bm25_store, segs=[], trace=trace,
        classify_call=_intent_noi_dung, answer_call=_no_model)
    names = [s.name for s in trace.stages]
    assert "gate0" in names
    assert "bm25" in names
    assert "gate1" in names


def test_gate1_ghi_ca_hai_ve_cua_moi_so_sanh(bm25_store):
    from flow1.thresholds import T1_ABS, T1_RATIO

    trace = Trace("q")
    ask("cơ chế attention là gì", store=bm25_store, segs=[], trace=trace,
        classify_call=_intent_noi_dung, answer_call=_no_model)
    gate1 = next(s for s in trace.stages if s.name == "gate1")
    assert gate1.data["T1_ABS"] == T1_ABS
    assert gate1.data["T1_RATIO"] == T1_RATIO
    assert "top1_abs" in gate1.data
    assert gate1.data["action"] in {"pass", "refuse", "clarify"}


def test_khong_truyen_trace_thi_khong_no(bm25_store):
    result = ask("cơ chế attention là gì", store=bm25_store, segs=[],
                 classify_call=_intent_noi_dung, answer_call=_no_model)
    assert isinstance(result.trace, NullTrace)
```

Tạo `flow1/tests/conftest.py` (nếu chưa có) với fixture:

```python
import pytest

from flow1.models import Seg


def _seg(code, session, order, text, section_idx=1, section_title="Attention va Transformer"):
    return Seg(
        code=code, session=session, session_title=f"Buoi {session}",
        locate_confidence="cao", section_idx=section_idx,
        section_title=section_title, order=order, text=text,
        speaker="instructor", has_gap=False, is_activity=False, n_chars=len(text),
    )


@pytest.fixture
def sample_segs():
    return [
        _seg("T04-001", "04", 1, "Cơ chế attention cho phép mô hình tập trung vào token liên quan."),
        _seg("T04-002", "04", 2, "Multi-head attention chạy nhiều đầu attention song song."),
        _seg("T04-003", "04", 3, "Transformer bỏ hẳn recurrent, chỉ dùng attention."),
        _seg("T02-001", "02", 1, "Automation là thay người làm, augmentation là hỗ trợ người làm.",
             2, "Automation va augmentation"),
    ]


@pytest.fixture
def bm25_store(sample_segs):
    """Store cho retrieve(store=...). Task 6 doi kieu tra ve cua fixture nay."""
    from flow1.chunk import chunk_all
    from flow1.index import build

    chunks = chunk_all(sample_segs)
    return chunks, build(chunks)
```

- [ ] **Step 9: Chạy test**

Run: `uv run pytest flow1/tests -q`
Expected: toàn bộ xanh — `trace` có giá trị mặc định nên không phá test cũ.

- [ ] **Step 10: Commit**

```bash
git add flow1/
git commit -m "feat(flow1): trace 6 chang + --trace tren CLI

gate0 bm25 gate1 context generate gate3. Cong 1 ghi ca top1_abs/ratio lan
T1_ABS/T1_RATIO da so — cau hoi 'vi sao con nay bi chan' tra loi duoc bang
mot lan doc thay vi mot lan debug.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: Đơn vị nguyên tử + map mã → ngữ cảnh + `Store`

**Files:**
- Create: `flow1/src/flow1/atomic.py`, `flow1/src/flow1/store.py`, `flow1/tests/test_flow1_atomic.py`
- Modify: `flow1/src/flow1/index.py`, `flow1/tests/conftest.py`

**Interfaces:**
- Consumes: `Seg`, `Chunk` từ `flow1.models`; `chunk_all` từ `flow1.chunk`
- Produces:
  - `atomic_chunks(segs: list[Seg]) -> list[Chunk]` — 1 Chunk mỗi Seg, `chunk_id == seg.code`
  - `build_code_map(contexts: list[Chunk]) -> dict[str, tuple[int, ...]]`
  - `Store(atomics, contexts, code_to_contexts, bm25)` — frozen dataclass
  - `index.build_store(segs) -> Store`, `index.load(path) -> Store`, `index.save(store, path)`

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_atomic.py`:

```python
from flow1.atomic import atomic_chunks, build_code_map
from flow1.chunk import chunk_all
from flow1.models import Chunk


def test_moi_seg_thanh_dung_mot_chunk(sample_segs):
    assert len(atomic_chunks(sample_segs)) == len(sample_segs)


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
    code_map = build_code_map(chunk_all(sample_segs))
    for seg in sample_segs:
        assert seg.code in code_map
        assert len(code_map[seg.code]) >= 1


def test_map_bat_duoc_ma_nam_trong_hai_context_do_overlap():
    """Overlap 1 doan nghia la mot ma co the thuoc 2 chunk lien ke."""
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
    contexts = [
        Chunk("T06-123#a", "06", "B6", 1, "S", [("T06-123", "phan dau")], False),
        Chunk("T06-123#b", "06", "B6", 1, "S", [("T06-123", "phan sau")], False),
    ]
    assert build_code_map(contexts)["T06-123"] == (0, 1)


def test_chi_so_trong_map_luon_hop_le(sample_segs):
    contexts = chunk_all(sample_segs)
    for indices in build_code_map(contexts).values():
        for i in indices:
            assert 0 <= i < len(contexts)


def test_build_store_gom_du_bon_thu(sample_segs):
    from flow1.index import build_store

    store = build_store(sample_segs)
    assert len(store.atomics) == len(sample_segs)
    assert len(store.contexts) >= 1
    assert set(store.code_to_contexts) == {s.code for s in sample_segs}
    assert store.bm25 is not None


def test_load_index_dinh_dang_cu_bao_loi_ro_rang(tmp_path):
    """Pickle cu chi co chunk gop — nap tiep se gay KeyError kho hieu o tan retrieve."""
    import pickle

    from flow1.index import IndexMissing, load

    path = tmp_path / "bm25.pkl"
    with path.open("wb") as handle:
        pickle.dump({"chunks": [], "bm25": None}, handle)

    try:
        load(path)
    except IndexMissing as exc:
        assert "python -m flow1 index" in str(exc)
    else:
        raise AssertionError("phai nem IndexMissing cho index dinh dang cu")
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_atomic.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.atomic'`

- [ ] **Step 3: Viết `flow1/src/flow1/atomic.py`**

```python
"""Don vi nguyen tu cho retrieval + map ma doan -> chunk ngu canh.

VI SAO TACH LAM HAI DON VI:
  index   = 700 doan nguyen tu. Ma doan la citation unit, nen xep hang o day
            thi diem tro dung cho, va BA retriever noi nhau bang chinh ma do
            (Neo4j co Turn {id: "T01-001"} — dung khoa nay).
  context = chunk gop cua chunk.py. Model can nhin thay xung quanh moi hieu.

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
    atomics: list[Chunk]                        # BM25 va cac retriever xep hang tren day
    contexts: list[Chunk]                       # nap vao prompt
    code_to_contexts: dict[str, tuple[int, ...]]
    bm25: object                                # BM25Okapi tren atomics
```

- [ ] **Step 5: Sửa `index.py`**

Thêm import: `from flow1.models import Chunk, Seg` và `from flow1.store import Store`. Thay `save`, `load`, thêm `build_store`, sửa `build_from_data`:

```python
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
    """Nap lai Store da luu. Nem `IndexMissing` kem lenh sua neu thieu/cu."""
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

    contexts = chunk_all(segs)
    atomics = atomic_chunks(segs)
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

- [ ] **Step 6: Cập nhật fixture**

Trong `flow1/tests/conftest.py`, đổi fixture `bm25_store` thành:

```python
@pytest.fixture
def bm25_store(sample_segs):
    from flow1.index import build_store

    return build_store(sample_segs)
```

- [ ] **Step 7: Chạy test**

Run: `uv run pytest flow1/tests/test_flow1_atomic.py -q`
Expected: 11 passed

Run: `uv run pytest flow1/tests -q`
Expected: `test_flow1_index.py`, `test_flow1_retrieve.py`, `test_flow1_embed.py` **đỏ** — hợp đồng `load()` đã đổi. Đây là thay đổi có chủ ý; Task 10 sửa chúng. Ghi lại đúng tên test nào đỏ.

- [ ] **Step 8: Commit**

```bash
git add flow1/src/flow1/atomic.py flow1/src/flow1/store.py flow1/src/flow1/index.py flow1/tests/
git commit -m "feat(flow1): don vi nguyen tu cho index, chunk gop cho ngu canh

BM25 chuyen sang index doan nguyen tu — ma doan la citation unit nen xep hang
o day thi diem tro dung cho, va la khoa noi chung cua ca ba retriever
(Neo4j co Turn {id} dung khoa nay).
Map code -> context la dan xuat, dung mot lan luc build.

test_flow1_index / retrieve / embed con do — hop dong load() da doi, sua o
commit sau.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Nới `find_chunks` cho `session_id` optional

**Files:**
- Modify: `vector-db/src/vector_db/search.py`
- Test: `vector-db/tests/test_search_contract.py`

**Interfaces:**
- Consumes: `_semantic_search` (đã hỗ trợ `session_id=None` sẵn)
- Produces: `find_chunks(query, session_id: str | None = None, section_id=None, top_k=5, *, exclude_activities=True)`

Tool tra cứu cần tìm **xuyên buổi** để cổng 1 phát hiện "top-1 ≈ top-2 khác buổi → hỏi lại". `find_chunks` hiện bắt buộc `session_id` nên không làm được.

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


def test_find_chunks_mac_dinh_loai_hoat_dong_lop(monkeypatch):
    ghi = {}

    def fake(query, **kwargs):
        ghi.update(kwargs)
        return ()

    monkeypatch.setattr(search, "_semantic_search", fake)
    search.find_chunks("attention")

    assert ghi["exclude_activities"] is True
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
    """Tim doan nguyen tu.

    session_id=None nghia la tim xuyen ca 6 buoi — cong 1 cua flow1 can the de
    phat hien chu de nam o nhieu buoi va hoi lai thay vi doan.
    """
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

Trong `main()` cùng file, bỏ dòng `parser.error("--session-id is required for chunk search")` ở nhánh `chunk`.

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest vector-db/tests -q`
Expected: toàn bộ xanh, có 4 test mới

- [ ] **Step 5: Commit**

```bash
git add vector-db/
git commit -m "feat(vector-db): find_chunks cho phep session_id=None de tim xuyen buoi

Cong 1 cua flow1 phai so top-1 voi top-2 khac BUOI de biet co phai hoi lai
khong — khong lam duoc neu bat buoc chot mot buoi tu dau.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: `Retriever` Protocol + BM25 · Qdrant · Null

**Files:**
- Create: `flow1/src/flow1/retrievers.py`, `flow1/tests/test_flow1_retrievers.py`

**Interfaces:**
- Consumes: `Store` (Task 6), `vector_db.search.find_chunks` (Task 7)
- Produces:
  - `RewrittenQuery(keywords: list[str], cau_hoi: str, thuc_the: list[str])` — pydantic model, có `RewrittenQuery.passthrough(query)`
  - `RankedList(name, ranking, ms, error, skipped_reason)` — frozen dataclass
  - `Retriever` Protocol: `name: str`, `rank(q, *, session, k) -> list[tuple[str, float]]`
  - `BM25Retriever(store)` · `QdrantRetriever()` · `NullRetriever(name, reason)`
  - `safe_rank(retriever, q, *, session, k) -> RankedList` — bắt mọi lỗi, không bao giờ ném

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_retrievers.py`:

```python
from flow1.retrievers import (
    BM25Retriever,
    NullRetriever,
    QdrantRetriever,
    RewrittenQuery,
    safe_rank,
)


def _q(keywords=None, cau_hoi="attention la gi", thuc_the=None):
    return RewrittenQuery(
        keywords=keywords if keywords is not None else ["attention"],
        cau_hoi=cau_hoi,
        thuc_the=thuc_the if thuc_the is not None else ["attention"],
    )


def test_passthrough_dat_cung_mot_chuoi_vao_ca_ba_truong():
    q = RewrittenQuery.passthrough("cơ chế attention là gì")
    assert q.cau_hoi == "cơ chế attention là gì"
    assert q.keywords == ["cơ chế attention là gì"]
    assert q.thuc_the == ["cơ chế attention là gì"]


def test_bm25_tra_ma_doan_va_diem_giam_dan(bm25_store):
    got = BM25Retriever(bm25_store).rank(_q(), session=None, k=5)
    assert got
    assert all(ma.startswith("T") for ma, _ in got)
    assert [d for _, d in got] == sorted((d for _, d in got), reverse=True)


def test_bm25_dung_truong_keywords_khong_dung_cau_hoi(bm25_store):
    """Moi retriever an mot truong khac nhau — do la ly do viet lai query."""
    got = BM25Retriever(bm25_store).rank(
        _q(keywords=["automation", "augmentation"], cau_hoi="hoan toan khong lien quan"),
        session=None, k=5,
    )
    assert got[0][0].startswith("T02")


def test_bm25_loc_duoc_theo_buoi(bm25_store):
    got = BM25Retriever(bm25_store).rank(_q(keywords=["attention"]), session="02", k=5)
    assert all(ma.startswith("T02") for ma, _ in got)


def test_bm25_query_rong_tra_rong(bm25_store):
    assert BM25Retriever(bm25_store).rank(_q(keywords=[]), session=None, k=5) == []


def test_null_tra_rong_va_mang_ly_do():
    r = NullRetriever("qdrant", "thieu QDRANT_URL")
    assert r.rank(_q(), session=None, k=5) == []
    assert r.reason == "thieu QDRANT_URL"
    assert r.name == "qdrant"


def test_qdrant_doi_hit_thanh_ma_doan_va_diem(monkeypatch):
    class Hit:
        def __init__(self, code, score):
            self.payload = {"citation_id": code}
            self.score = score

    monkeypatch.setattr(
        "vector_db.search.find_chunks",
        lambda q, session_id=None, top_k=5, **kw: (Hit("T04-072", 0.91), Hit("T04-071", 0.88)),
    )
    assert QdrantRetriever().rank(_q(), session=None, k=5) == [
        ("T04-072", 0.91), ("T04-071", 0.88)
    ]


def test_qdrant_dung_truong_cau_hoi_va_doi_ma_buoi(monkeypatch):
    ghi = {}

    def fake(q, session_id=None, top_k=5, **kw):
        ghi["query"] = q
        ghi["session_id"] = session_id
        ghi["top_k"] = top_k
        return ()

    monkeypatch.setattr("vector_db.search.find_chunks", fake)
    QdrantRetriever().rank(_q(cau_hoi="co che attention"), session="04", k=7)

    assert ghi["query"] == "co che attention"
    assert ghi["session_id"] == "T04"
    assert ghi["top_k"] == 7


def test_qdrant_bo_hit_thieu_citation_id(monkeypatch):
    class Hit:
        def __init__(self, payload, score):
            self.payload = payload
            self.score = score

    monkeypatch.setattr(
        "vector_db.search.find_chunks",
        lambda q, **kw: (Hit({}, 0.9), Hit({"citation_id": "T01-001"}, 0.8)),
    )
    assert QdrantRetriever().rank(_q(), session=None, k=5) == [("T01-001", 0.8)]


def test_safe_rank_bat_loi_va_khong_nem_ra_ngoai():
    class Vo:
        name = "vo"

        def rank(self, q, *, session, k):
            raise ConnectionError("mat mang")

    got = safe_rank(Vo(), _q(), session=None, k=5)
    assert got.ranking == []
    assert got.name == "vo"
    assert "mat mang" in got.error
    assert got.ms >= 0.0


def test_safe_rank_ghi_ly_do_khi_retriever_la_null():
    got = safe_rank(NullRetriever("neo4j", "Neo4j chet"), _q(), session=None, k=5)
    assert got.ranking == []
    assert got.error is None
    assert got.skipped_reason == "Neo4j chet"


def test_safe_rank_dedupe_ma_trung():
    """Retriever tra trung ma thi RRF se cong diem hai lan cho cung mot doan."""

    class Trung:
        name = "trung"

        def rank(self, q, *, session, k):
            return [("T01-001", 0.9), ("T01-001", 0.8), ("T01-002", 0.7)]

    got = safe_rank(Trung(), _q(), session=None, k=5)
    assert [ma for ma, _ in got.ranking] == ["T01-001", "T01-002"]
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_retrievers.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.retrievers'`

- [ ] **Step 3: Viết `flow1/src/flow1/retrievers.py`**

```python
"""Ba nhanh retrieve sau MOT interface, cong lop bat loi dung chung.

KHOA NOI: moi retriever tra ve [(ma doan Txx-NNN, diem)]. Ma doan la citation
unit cua ca he — Qdrant co payload.citation_id, Neo4j co Turn {id}, BM25 index
chunk_id chinh la ma doan. Khong lop anh xa nao phai nuoi tay.

DIEM KHONG CAN CUNG THANG: RRF chi doc THU HANG. BM25 tra diem tho, Qdrant tra
cosine, Neo4j tra diem full-text — khong chuan hoa gi giua chung.

safe_rank la noi DUY NHAT bat loi. Retriever tu no duoc phep nem; tach vai nhu
vay de moi ben mot viec va de test duoc duong loi rieng.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class RewrittenQuery(BaseModel):
    """Ba dang cua cung mot cau hoi, moi retriever an mot dang."""

    keywords: list[str] = Field(
        description="Tu khoa cho BM25, da bo sung dong nghia Viet-Anh."
    )
    cau_hoi: str = Field(
        description="Cau hoi viet lai thanh mot cau tu nhien day du, cho vector search."
    )
    thuc_the: list[str] = Field(
        description="Ten khai niem/thuc the de khop vao knowledge graph."
    )

    @classmethod
    def passthrough(cls, query: str) -> "RewrittenQuery":
        """Khong goi LLM: dat nguyen cau hoi vao ca ba truong."""
        return cls(keywords=[query], cau_hoi=query, thuc_the=[query])


@dataclass(frozen=True)
class RankedList:
    name: str
    ranking: list[tuple[str, float]]
    ms: float
    error: str | None = None
    skipped_reason: str | None = None


class Retriever(Protocol):
    name: str

    def rank(self, q: RewrittenQuery, *, session: str | None, k: int) -> list[tuple[str, float]]:
        """[(ma doan, diem)] da sap giam dan."""
        ...


class NullRetriever:
    """Khong tra ve gi. Chon khi tat toggle, thieu key, hoac service chet."""

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason

    def rank(self, q, *, session, k):
        return []


class BM25Retriever:
    """BM25 offline tren doan nguyen tu. An truong `keywords`."""

    name = "bm25"
    reason = ""

    def __init__(self, store) -> None:
        self.store = store

    def rank(self, q, *, session, k):
        from flow1.index import tokenize

        tokens = tokenize(" ".join(q.keywords))
        if not tokens:
            return []
        scores = self.store.bm25.get_scores(tokens)
        pairs = [
            (atomic.chunk_id, float(scores[i]))
            for i, atomic in enumerate(self.store.atomics)
            if session is None or atomic.session == session
        ]
        pairs.sort(key=lambda pair: pair[1], reverse=True)
        return pairs[:k]


class QdrantRetriever:
    """Vector search trong Qdrant tren atomic_chunk. An truong `cau_hoi`."""

    name = "qdrant"
    reason = ""

    def rank(self, q, *, session, k):
        from vector_db.search import find_chunks

        hits = find_chunks(
            q.cau_hoi,
            session_id=f"T{session}" if session else None,
            top_k=k,
        )
        return [
            (hit.payload["citation_id"], float(hit.score))
            for hit in hits
            if hit.payload.get("citation_id")
        ]


def safe_rank(
    retriever: Retriever, q: RewrittenQuery, *, session: str | None, k: int
) -> RankedList:
    """Goi mot retriever, bat moi loi, dedupe ma trung. KHONG BAO GIO nem."""
    start = time.perf_counter()
    error = None
    try:
        raw = retriever.rank(q, session=session, k=k)
    except Exception as exc:
        raw = []
        error = f"{type(exc).__name__}: {exc}"

    seen: dict[str, float] = {}
    for code, score in raw:
        if code not in seen:
            seen[code] = float(score)

    return RankedList(
        name=retriever.name,
        ranking=list(seen.items()),
        ms=(time.perf_counter() - start) * 1000.0,
        error=error,
        skipped_reason=getattr(retriever, "reason", "") or None,
    )
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_retrievers.py -q`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add flow1/src/flow1/retrievers.py flow1/tests/test_flow1_retrievers.py
git commit -m "feat(flow1): Retriever Protocol + BM25/Qdrant/Null, safe_rank bat loi

Ba nhanh sau mot interface, cung tra [(ma doan, diem)]. RRF chi doc thu hang
nen khong phai chuan hoa diem giua BM25 tho, cosine va diem full-text.
safe_rank la noi duy nhat bat loi va dedupe ma trung.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: `Neo4jRetriever` — Concept lan ra Turn

**Files:**
- Create: `graph-db/src/graph_db/retrieve.py`, `graph-db/tests/test_graph_db_retrieve.py`
- Modify: `flow1/src/flow1/retrievers.py`, `flow1/tests/test_flow1_retrievers.py`, `flow1/pyproject.toml`, `graph-db/scripts/ingest_transcripts.py`

**Interfaces:**
- Consumes: `graph_db.query` (đã có)
- Produces:
  - `graph_db.retrieve.CYPHER` — hằng chuỗi, để test soi được nội dung
  - `graph_db.retrieve.turns_for_concepts(thuc_the, *, session, k, run=None) -> list[tuple[str, float]]`
  - `flow1.retrievers.Neo4jRetriever()` — ăn trường `thuc_the`

- [ ] **Step 1: Viết test thất bại**

Tạo `graph-db/tests/test_graph_db_retrieve.py`:

```python
from graph_db.retrieve import CYPHER, turns_for_concepts


def _fake_run(rows):
    """Gia lap graph_db.query: tra ve danh sach dict nhu driver that."""

    def run(cypher, params):
        return rows

    return run


def test_tra_ve_ma_doan_that_khong_phai_ten_concept():
    rows = [
        {"ma": "T04-072", "diem": 3.2, "hop": 0},
        {"ma": "T04-071", "diem": 1.6, "hop": 1},
    ]
    got = turns_for_concepts(["attention"], session=None, k=5, run=_fake_run(rows))
    assert [ma for ma, _ in got] == ["T04-072", "T04-071"]


def test_hop_0_luon_dung_truoc_hop_1_du_diem_thap_hon():
    """Doan noi thang ve concept dang tin hon doan cach 1 quan he."""
    rows = [
        {"ma": "T01-005", "diem": 0.4, "hop": 0},
        {"ma": "T09-001", "diem": 9.9, "hop": 1},
    ]
    got = turns_for_concepts(["x"], session=None, k=5, run=_fake_run(rows))
    assert [ma for ma, _ in got] == ["T01-005", "T09-001"]


def test_dedupe_giu_lan_xuat_hien_tot_nhat():
    rows = [
        {"ma": "T01-001", "diem": 5.0, "hop": 0},
        {"ma": "T01-001", "diem": 1.0, "hop": 1},
        {"ma": "T01-002", "diem": 2.0, "hop": 0},
    ]
    got = turns_for_concepts(["x"], session=None, k=5, run=_fake_run(rows))
    assert [ma for ma, _ in got] == ["T01-001", "T01-002"]
    assert got[0][1] == 5.0


def test_cat_dung_k():
    rows = [{"ma": f"T01-{i:03d}", "diem": 10 - i, "hop": 0} for i in range(1, 8)]
    assert len(turns_for_concepts(["x"], session=None, k=3, run=_fake_run(rows))) == 3


def test_thuc_the_rong_khong_goi_graph():
    def no(cypher, params):
        raise AssertionError("khong duoc goi graph khi khong co thuc the")

    assert turns_for_concepts([], session=None, k=5, run=no) == []


def test_truyen_session_xuong_lam_tham_so():
    ghi = {}

    def run(cypher, params):
        ghi.update(params)
        return []

    turns_for_concepts(["attention"], session="04", k=5, run=run)
    assert ghi["session"] == "T04"
    assert "attention" in ghi["thuc_the"]


def test_cypher_khong_lay_mo_ta_concept():
    """KG mo rong recall, KHONG mo rong tham quyen — chi lay Turn.id.

    Mot chu nao cua Concept.description lot vao prompt la KG tro thanh nguon
    khang dinh, ma concept do LLM sinh ra luc ingest.
    """
    assert "description" not in CYPHER
    sau_return = CYPHER.split("RETURN", 1)[1]
    assert "c.name" not in sau_return


def test_cypher_loai_hoat_dong_lop():
    assert "is_activity = false" in CYPHER
```

Thêm vào `flow1/tests/test_flow1_retrievers.py`:

```python
def test_neo4j_retriever_dung_truong_thuc_the(monkeypatch):
    import graph_db.retrieve as gr

    from flow1.retrievers import Neo4jRetriever

    ghi = {}

    def fake(thuc_the, *, session, k):
        ghi["thuc_the"] = thuc_the
        ghi["session"] = session
        return [("T04-072", 3.2)]

    monkeypatch.setattr(gr, "turns_for_concepts", fake)
    got = Neo4jRetriever().rank(_q(thuc_the=["attention", "transformer"]), session="04", k=5)

    assert ghi["thuc_the"] == ["attention", "transformer"]
    assert ghi["session"] == "04"
    assert got == [("T04-072", 3.2)]
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest graph-db/tests -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'graph_db.retrieve'`

- [ ] **Step 3: Viết `graph-db/src/graph_db/retrieve.py`**

```python
"""Tim doan giang lien quan qua KNOWLEDGE GRAPH.

DAY LA THU VECTOR SEARCH KHONG LAM DUOC: tra ve doan lien quan QUA QUAN HE,
khong phai doan giong chu. Vi du "hoc xong attention thi hoc gi tiep" — khong
doan nao chua cum tu do, nhung graph di duoc tu Concept "attention" sang
Concept lien quan roi ve Turn noi ve chung.

RANH GIOI THAM QUYEN: chi lay Turn.id va diem. KHONG lay Concept.description
hay Concept.name vao ket qua — concept la phan doan cua LLM luc ingest, dua noi
dung cua no vao prompt la bien KG thanh nguon khang dinh. Co test canh dieu
nay: test_cypher_khong_lay_mo_ta_concept.

XEP HANG: (hop, -diem). Doan noi THANG ve concept dung truoc doan cach 1-2
quan he, du diem full-text cua doan xa co the cao hon.
"""

from __future__ import annotations

CYPHER = """
CALL db.index.fulltext.queryNodes('concept_name_ft', $thuc_the) YIELD node AS c, score
MATCH (c)<-[:COVERS]-(s:Section)<-[:BELONGS_TO]-(t:Turn)
WHERE t.is_activity = false AND ($session IS NULL OR t.lecture_id ENDS WITH $session)
RETURN t.id AS ma, score AS diem, 0 AS hop
UNION
CALL db.index.fulltext.queryNodes('concept_name_ft', $thuc_the) YIELD node AS c, score
MATCH (c)-[:RELATED_TO*1..2]-(:Concept)<-[:COVERS]-(s:Section)<-[:BELONGS_TO]-(t:Turn)
WHERE t.is_activity = false AND ($session IS NULL OR t.lecture_id ENDS WITH $session)
RETURN t.id AS ma, score * 0.5 AS diem, 1 AS hop
"""


def turns_for_concepts(
    thuc_the: list[str],
    *,
    session: str | None,
    k: int,
    run=None,
) -> list[tuple[str, float]]:
    """[(ma doan, diem)] xep theo (hop, -diem), da dedupe. `run` de test offline."""
    if not thuc_the:
        return []

    if run is None:
        from graph_db import query as run

    rows = run(
        CYPHER,
        {
            "thuc_the": " OR ".join(thuc_the),
            "session": f"T{session}" if session else None,
        },
    )

    rows = sorted(rows, key=lambda r: (r["hop"], -float(r["diem"])))
    seen: dict[str, float] = {}
    for row in rows:
        if row["ma"] not in seen:
            seen[row["ma"]] = float(row["diem"])
    return list(seen.items())[:k]
```

- [ ] **Step 4: Thêm `Neo4jRetriever` vào `flow1/src/flow1/retrievers.py`**

```python
class Neo4jRetriever:
    """Doan lien quan QUA QUAN HE trong knowledge graph. An truong `thuc_the`."""

    name = "neo4j"
    reason = ""

    def rank(self, q, *, session, k):
        import graph_db.retrieve as gr

        return gr.turns_for_concepts(q.thuc_the, session=session, k=k)
```

Sửa `flow1/pyproject.toml`:

```toml
dependencies = ["pydantic", "rank_bm25", "numpy", "streamlit", "vector-db", "graph-db"]

[tool.uv.sources]
vector-db = { workspace = true }
graph-db = { workspace = true }
```

Chạy `uv sync --all-packages` sau khi sửa.

- [ ] **Step 5: Thêm full-text index vào ingest**

Trong `graph-db/scripts/ingest_transcripts.py`, chỗ tạo các index, thêm:

```python
    # Full-text index cho nhanh KG cua tool tra cuu. Khop ten concept voi
    # `thuc_the` do buoc viet lai query trich ra. Dung full-text thay vi embed
    # ten concept: tat dinh, khong ton API, va khong them mot chieu vector nua
    # phai dong bo voi Qdrant.
    session.run(
        "CREATE FULLTEXT INDEX concept_name_ft IF NOT EXISTS "
        "FOR (c:Concept) ON EACH [c.name, c.name_en]"
    )
```

- [ ] **Step 6: Chạy test**

Run: `uv run pytest graph-db/tests flow1/tests/test_flow1_retrievers.py -q`
Expected: 8 test graph-db + 13 test retrievers, tất cả xanh

- [ ] **Step 7: Thử graph thật**

Run: `uv run python graph-db/scripts/check_neo4j.py`

- **Nếu chết:** ghi thông báo lỗi nguyên văn vào report và đi tiếp. Nhánh KG đã có test offline đầy đủ, `safe_rank` lùi êm khi service chết.
- **Nếu sống:** chạy `MATCH (n:Concept) RETURN count(n) AS c`. Nếu **0 Concept** thì ghi rõ vào report rằng graph rỗng và nhánh KG sẽ luôn trả rỗng cho tới khi chạy ingest. **KHÔNG tự chạy ingest** — nó gọi LLM cho 6 buổi, tốn tiền, phải hỏi trước.

- [ ] **Step 8: Commit**

```bash
git add graph-db/ flow1/
git commit -m "feat(graph-db): Neo4jRetriever - khop Concept full-text roi lan ra Turn

Tra ve doan lien quan QUA QUAN HE, thu vector search khong lam duoc.
Xep hang (hop, -diem): doan noi thang ve concept dung truoc doan cach 1-2 hop.

Ranh gioi tham quyen co test canh: Cypher chi lay Turn.id, khong lay
Concept.description — concept la phan doan cua LLM luc ingest, dua noi dung
no vao prompt la bien KG thanh nguon khang dinh.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: RRF 3 nhánh + toggle + nở ngữ cảnh

**Files:**
- Modify: `flow1/src/flow1/retrieve.py`, `flow1/tests/test_flow1_retrieve.py`, `flow1/tests/test_flow1_index.py`, `flow1/tests/test_flow1_embed.py`
- Create: `flow1/tests/test_flow1_hybrid.py`

**Interfaces:**
- Consumes: `Store` (Task 6), retrievers + `safe_rank` + `RewrittenQuery` (Task 8-9), `rrf` từ `flow1.embed`, trace (Task 4)
- Produces:
  - `Toggles(bm25: bool = True, qdrant: bool = True, neo4j: bool = True)` — frozen dataclass
  - `retrieve(query_or_rewritten, *, session=None, k=TOP_K, store=None, path=BM25_PATH, toggles=None, retrievers=None, trace=None) -> Retrieval`
  - `Retrieval.hits` là **chunk ngữ cảnh**; `Hit.bm25` là điểm BM25 thô của **đoạn nguyên tử tốt nhất** trong chunk đó

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_hybrid.py`:

```python
from flow1.retrieve import Toggles, retrieve
from flow1.retrievers import NullRetriever, RewrittenQuery
from flow1.trace import Trace


class FakeRetriever:
    def __init__(self, name, ranking):
        self.name = name
        self.ranking = ranking
        self.reason = ""

    def rank(self, q, *, session, k):
        return self.ranking[:k]


def _only_bm25(store):
    """Chi BM25 that, hai nhanh kia im lang — de test khong cham mang."""
    from flow1.retrievers import BM25Retriever

    return {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "tat trong test"),
        "neo4j": NullRetriever("neo4j", "tat trong test"),
    }


def test_chi_bm25_thi_van_tra_ket_qua(bm25_store):
    got = retrieve("attention", store=bm25_store, retrievers=_only_bm25(bm25_store))
    assert [h.chunk.chunk_id for h in got.hits]


def test_gate_stats_khong_doi_khi_bat_them_nhanh(bm25_store):
    """Cong 1 luon quyet dinh tren BM25 tho, doc lap voi fusion."""
    rs = _only_bm25(bm25_store)
    tat = retrieve("attention", store=bm25_store, retrievers=rs)

    rs2 = dict(rs)
    rs2["qdrant"] = FakeRetriever("qdrant", [("T02-001", 0.99)])
    bat = retrieve("attention", store=bm25_store, retrievers=rs2)

    assert bat.top1_abs == tat.top1_abs
    assert bat.ratio == tat.ratio


def test_tat_bm25_khoi_fusion_thi_cong_1_VAN_hoat_dong(bm25_store):
    """Bat biến §5.1: toggle chi dieu khien fusion, khong tat cong 1."""
    rs = _only_bm25(bm25_store)
    rs["qdrant"] = FakeRetriever("qdrant", [("T02-001", 0.99)])
    got = retrieve(
        "attention", store=bm25_store, retrievers=rs,
        toggles=Toggles(bm25=False, qdrant=True, neo4j=False),
    )
    assert got.top1_abs > 0.0, "BM25 phai van chay du da tat khoi fusion"


def test_tat_bm25_thi_thu_tu_theo_nhanh_con_lai(bm25_store):
    rs = _only_bm25(bm25_store)
    rs["qdrant"] = FakeRetriever("qdrant", [("T02-001", 0.99)])
    got = retrieve(
        "attention", store=bm25_store, retrievers=rs,
        toggles=Toggles(bm25=False, qdrant=True, neo4j=False),
    )
    assert got.hits[0].chunk.seg_codes[0] == "T02-001"


def test_nhanh_nem_loi_thi_lui_em_va_ghi_ly_do(bm25_store):
    class Vo:
        name = "neo4j"

        def rank(self, q, *, session, k):
            raise ConnectionError("mat mang")

    rs = _only_bm25(bm25_store)
    rs["neo4j"] = Vo()
    trace = Trace("attention")
    got = retrieve("attention", store=bm25_store, retrievers=rs, trace=trace)

    assert got.hits, "phai van tra ve ket qua tu cac nhanh con lai"
    stage = next(s for s in trace.stages if s.name == "neo4j")
    assert "mat mang" in stage.data["loi"]


def test_ma_khong_co_trong_store_bi_bo_qua(bm25_store):
    rs = _only_bm25(bm25_store)
    rs["neo4j"] = FakeRetriever("neo4j", [("T99-999", 9.9)])
    got = retrieve("attention", store=bm25_store, retrievers=rs)
    assert got.hits
    assert all("T99-999" not in h.chunk.seg_codes for h in got.hits)


def test_nhan_duoc_ca_chuoi_lan_RewrittenQuery(bm25_store):
    rs = _only_bm25(bm25_store)
    a = retrieve("attention", store=bm25_store, retrievers=rs)
    b = retrieve(
        RewrittenQuery.passthrough("attention"), store=bm25_store, retrievers=rs
    )
    assert [h.chunk.chunk_id for h in a.hits] == [h.chunk.chunk_id for h in b.hits]


def test_hit_bm25_la_diem_doan_nguyen_tu_tot_nhat_trong_chunk(bm25_store):
    got = retrieve("attention", store=bm25_store, retrievers=_only_bm25(bm25_store))
    assert all(h.bm25 >= 0.0 for h in got.hits)
    assert got.hits[0].bm25 >= got.hits[-1].bm25


def test_loc_theo_buoi_van_dung(bm25_store):
    got = retrieve(
        "automation", store=bm25_store, session="02",
        retrievers=_only_bm25(bm25_store),
    )
    assert all(h.session == "02" for h in got.hits)


def test_trace_bang_fuse_co_thu_hang_tung_nhanh(bm25_store):
    rs = _only_bm25(bm25_store)
    rs["qdrant"] = FakeRetriever("qdrant", [("T04-002", 0.9)])
    trace = Trace("attention")
    retrieve("attention", store=bm25_store, retrievers=rs, trace=trace)

    fuse = next(s for s in trace.stages if s.name == "fuse")
    hang = fuse.data["bang"][0]
    assert set(hang) >= {"ma", "rank_bm25", "rank_qdrant", "rank_neo4j", "rrf"}
    assert "chi_mot_nhanh_tim_ra" in fuse.data


def test_query_rong_tra_retrieval_rong(bm25_store):
    got = retrieve("   ", store=bm25_store, retrievers=_only_bm25(bm25_store))
    assert got.hits == []
    assert got.top1_abs == 0.0
    assert got.ratio == 0.0
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_hybrid.py -q`
Expected: FAIL — `cannot import name 'Toggles' from 'flow1.retrieve'`

- [ ] **Step 3: Viết lại `flow1/src/flow1/retrieve.py`**

Giữ nguyên `gate_stats` và docstring của nó. Thay phần còn lại:

```python
"""Truy van -> Retrieval. Fuse ba nhanh bang RRF tren MA DOAN.

QUYET DINH THIET KE QUAN TRONG NHAT cua file nay:

  `top1_abs` va `ratio` LUON tinh tren diem BM25 THO, khong bao gio tren diem
  da fuse. Diem RRF la 1/(K+rank) — mot day gan nhu co dinh (1/61, 1/62...),
  neu `ratio` tinh sau fuse se luon ~1,02 bat ke cau hoi la gi, va cong 1 chet
  im lang dung vao luc bat hybrid.

  He qua tot: hieu chinh T1 MOT LAN la dung duoc cho moi to hop toggle.

BAT BIEN §5.1 CUA SPEC: BM25 LUON CHAY, ke ca khi toggles.bm25 = False.
Toggle chi dieu khien BM25 co gop vao FUSION hay khong. Neu toggle tat luon
cong 1 thi bat "chi Qdrant" de do se vo tinh tat mat lop tu choi — dung thu
ca san pham dang phong.

Tien dieu kien: `gate_stats` CHI nhan diem BM25 tho da sap giam dan.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from flow1.embed import rrf
from flow1.index import BM25_PATH, load
from flow1.models import Hit, Retrieval
from flow1.retrievers import RewrittenQuery, safe_rank
from flow1.store import Store
from flow1.thresholds import RRF_K

TOP_K = 5
_RATIO_WINDOW = 5
CAND = 10
_NHANH = ("bm25", "qdrant", "neo4j")


@dataclass(frozen=True)
class Toggles:
    """Bat/tat tung nhanh KHOI FUSION. BM25 van luon chay cho cong 1."""

    bm25: bool = True
    qdrant: bool = True
    neo4j: bool = True

    def bat(self, name: str) -> bool:
        return bool(getattr(self, name))


def default_retrievers(store: Store) -> dict[str, object]:
    """Ba retriever that. Thieu cau hinh thi nhanh do thanh NullRetriever."""
    import os

    from flow1.retrievers import (
        BM25Retriever,
        Neo4jRetriever,
        NullRetriever,
        QdrantRetriever,
    )

    def _co(*names: str) -> str:
        thieu = [n for n in names if not os.getenv(n, "").strip()]
        return ", ".join(thieu)

    thieu_qdrant = _co("QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY")
    thieu_neo4j = _co("NEO4J_URL", "NEO4J_USERNAME", "NEO4J_PASSWORD")

    return {
        "bm25": BM25Retriever(store),
        "qdrant": (
            NullRetriever("qdrant", f"thieu bien moi truong: {thieu_qdrant}")
            if thieu_qdrant else QdrantRetriever()
        ),
        "neo4j": (
            NullRetriever("neo4j", f"thieu bien moi truong: {thieu_neo4j}")
            if thieu_neo4j else Neo4jRetriever()
        ),
    }


def retrieve(
    query,
    *,
    session: str | None = None,
    k: int = TOP_K,
    store: Store | None = None,
    path: Path = BM25_PATH,
    toggles: Toggles | None = None,
    retrievers: dict | None = None,
    trace=None,
) -> Retrieval:
    """Fuse ba nhanh bang RRF tren ma doan, roi no len chunk ngu canh.

    `query` nhan ca str lan RewrittenQuery — str duoc passthrough vao ca ba truong.
    """
    from flow1.trace import NullTrace

    q = query if isinstance(query, RewrittenQuery) else RewrittenQuery.passthrough(str(query))
    trace = trace if trace is not None else NullTrace(q.cau_hoi)
    store = store if store is not None else load(path)
    toggles = toggles if toggles is not None else Toggles()
    retrievers = retrievers if retrievers is not None else default_retrievers(store)

    ma_hop_le = {atomic.chunk_id for atomic in store.atomics}

    # ---- Chay ca ba nhanh. BM25 chay du toggle tat — xem docstring. --------
    ket: dict[str, object] = {}
    for name in _NHANH:
        retriever = retrievers.get(name)
        if retriever is None:
            continue
        with trace.stage(name) as tdata:
            ranked = safe_rank(retriever, q, session=session, k=CAND)
            loc = [(ma, d) for ma, d in ranked.ranking if ma in ma_hop_le]
            ket[name] = loc
            tdata["gop_vao_fusion"] = toggles.bat(name)
            tdata["top10"] = [(ma, round(d, 4)) for ma, d in loc[:10]]
            tdata["ms"] = round(ranked.ms, 2)
            if ranked.error:
                tdata["loi"] = ranked.error
                tdata["hau_qua"] = "bo qua nhanh nay, cac nhanh con lai van chay"
            elif ranked.skipped_reason:
                tdata["bo_qua"] = ranked.skipped_reason
            tdata["bo_ma_ngoai_store"] = len(ranked.ranking) - len(loc)
            if name == "bm25" and not toggles.bm25:
                tdata["luu_y"] = (
                    "BM25 da tat khoi fusion nhung VAN CHAY: cong 1 quyet dinh "
                    "tren diem BM25 tho, tat no di la tat lop tu choi."
                )

    # ---- Cong 1 lay so lieu tu BM25 THO, doc lap toggle va fusion ---------
    bm25_pairs = ket.get("bm25", [])
    with trace.stage("gate_stats") as tdata:
        top1_abs, ratio = gate_stats([d for _, d in bm25_pairs])
        tdata["nguon"] = "BM25 tho, doc lap voi fusion va voi toggle"
        tdata["top1_abs"] = round(top1_abs, 3)
        tdata["ratio"] = "inf" if ratio == math.inf else round(ratio, 3)

    if not bm25_pairs and not any(ket.get(n) for n in _NHANH):
        return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)

    # ---- Fuse chi cac nhanh dang bat --------------------------------------
    with trace.stage("fuse") as tdata:
        thu_hang = {
            name: {ma: r for r, (ma, _) in enumerate(ket.get(name, []))}
            for name in _NHANH
        }
        bang_xep = [
            [ma for ma, _ in ket.get(name, [])[:CAND]]
            for name in _NHANH
            if toggles.bat(name) and ket.get(name)
        ]
        if bang_xep:
            fused = rrf(bang_xep, RRF_K)
        else:
            fused = {ma: 1.0 / (RRF_K + r + 1) for r, (ma, _) in enumerate(bm25_pairs)}
        thu_tu = sorted(fused, key=lambda ma: fused[ma], reverse=True)

        tdata["nhanh_gop"] = [n for n in _NHANH if toggles.bat(n) and ket.get(n)]
        tdata["bang"] = [
            {
                "ma": ma,
                "rank_bm25": thu_hang["bm25"].get(ma),
                "rank_qdrant": thu_hang["qdrant"].get(ma),
                "rank_neo4j": thu_hang["neo4j"].get(ma),
                "rrf": round(fused[ma], 5),
            }
            for ma in thu_tu[:10]
        ]
        tdata["chi_mot_nhanh_tim_ra"] = {
            n: [
                ma for ma in thu_tu[:10]
                if thu_hang[n].get(ma) is not None
                and all(thu_hang[o].get(ma) is None for o in _NHANH if o != n)
            ]
            for n in _NHANH
        }

    diem_bm25 = dict(bm25_pairs)

    # ---- No len chunk ngu canh --------------------------------------------
    with trace.stage("context") as tdata:
        hits: list[Hit] = []
        da_lay: set[int] = set()
        for ma in thu_tu:
            for idx in store.code_to_contexts.get(ma, ()):
                if idx in da_lay:
                    continue
                da_lay.add(idx)
                hits.append(
                    Hit(
                        chunk=store.contexts[idx],
                        bm25=diem_bm25.get(ma, 0.0),
                        emb=dict(ket.get("qdrant", [])).get(ma),
                        rank=len(hits),
                        score=fused[ma],
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

- [ ] **Step 4: Dọn `embed.py` xuống còn `rrf`**

`flow1/src/flow1/embed.py` giữ lại **chỉ** hàm `rrf` và docstring giải thích vì sao RRF thay vì cộng điểm. Xoá `_get_model`, `build_embeddings`, `load_embeddings`, `embed_query`, `_normalise`, hằng `MODEL_NAME`, `EMB_PATH`, và import `numpy`/`SentenceTransformer`. Bỏ `sentence-transformers` khỏi `summarizer/pyproject.toml` nếu không module nào khác dùng (kiểm bằng grep trước khi bỏ).

- [ ] **Step 5: Viết lại `test_flow1_embed.py`**

Giữ 5 test của `rrf`. Xoá các test dùng `load_embeddings`, `retrieve(embeddings=...)`, `retrieve(query_vector=...)` — chúng đã chuyển thành `test_flow1_hybrid.py`.

Test `test_embed_module_names_a_local_model_and_no_remote_endpoint` khoá cứng quyết định *"embedding phải chạy local"* — đúng thứ spec mới cố ý lật. **Không xoá trắng**, thay bằng test khoá bảo đảm thật sự cần giữ:

```python
def test_flow1_khong_co_duong_nao_embed_hang_loat_qua_api():
    """Dieu 4 bao mat data: gui ca corpus ra provider ngoai KHONG phai
    'phan toi thieu can thiet'. Corpus da embed mot lan boi vector-db va ket
    qua nam trong Qdrant. flow1 chi duoc embed DUNG CAU HOI.

    Test nay thay cho test_embed_module_names_a_local_model_and_no_remote_endpoint:
    quyet dinh 'model phai local' da bi spec 2026-07-30-agent-2-tool lat, nhung
    bao dam ben duoi no thi khong.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "flow1"
    cam = ("build_embeddings", "embed_all", "embed_corpus", ".encode(")
    for file in src.rglob("*.py"):
        text = file.read_text(encoding="utf-8")
        for tu in cam:
            assert tu not in text, (
                f"{file.name} co '{tu}' — flow1 chi duoc embed cau hoi, khong "
                f"duoc embed hang loat. Xem canvas §4.3."
            )
```

- [ ] **Step 6: Sửa `test_flow1_index.py` và `test_flow1_retrieve.py`**

Đổi mọi `chunks, bm25 = load(...)` thành `store = load(...)` rồi dùng `store.atomics` / `store.bm25`. Mọi `retrieve(..., store=(chunks, bm25))` đổi thành `store=build_store(segs)`. Mọi test gọi `retrieve` phải truyền `retrievers=` chỉ có BM25 thật để không chạm mạng.

- [ ] **Step 7: Sửa `cli.py` — bỏ `--with-embedding`**

Trong `_run_index`, bỏ nhánh `with_embedding` và argument tương ứng, thay bằng:

```python
    print(f"Da index {count} doan nguyen tu.")
    print("Nhanh semantic lay tu Qdrant va Neo4j luc chay — khong can build them.")
```

- [ ] **Step 8: Chạy test**

Run: `uv run pytest flow1/tests/test_flow1_hybrid.py -q`
Expected: 11 passed

Run: `uv run pytest -q`
Expected: toàn bộ xanh

- [ ] **Step 9: Dựng lại index thật và thử tay**

Run: `uv run python -m flow1 index`
Expected: `Da index 645 doan nguyen tu.` — 700 đoạn trừ 55 `is_activity`. **Ghi lại con số thật**; nếu khác 645 thì `content_segs` lọc khác dự kiến, dừng lại tìm hiểu trước khi đi tiếp.

- [ ] **Step 10: Commit**

```bash
git add flow1/
git commit -m "feat(flow1): fuse ba nhanh bang RRF tren ma doan, toggle tung nhanh

BM25 LUON CHAY ke ca khi tat toggle — toggle chi dieu khien co gop vao fusion
hay khong. Cong 1 quyet dinh tren diem BM25 tho nen tat BM25 khoi fusion van
khong tat lop tu choi. Co test canh bat bien nay.

Bang fuse trong trace chi ra doan nao CHI mot nhanh tim ra — do la cach doc
xem nhanh nao dang dong gop gi.

Bo nhanh e5 local, giu lai ham rrf. Test khoa 'model phai local' doi thanh
test khoa 'flow1 chi duoc embed cau hoi, khong embed hang loat'.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: Viết lại query — 1 call → 3 dạng

**Files:**
- Create: `flow1/src/flow1/rewrite.py`, `flow1/tests/test_flow1_rewrite.py`
- Modify: `flow1/src/flow1/prompts.py`

**Interfaces:**
- Consumes: `RewrittenQuery` (Task 8)
- Produces: `rewrite_query(question, *, call=None, trace=None) -> RewrittenQuery` — **không bao giờ ném**; lỗi thì lùi về `RewrittenQuery.passthrough(question)`

Mỗi retriever mạnh ở một dạng đầu vào khác nhau — BM25 ăn từ khoá, vector ăn câu tự nhiên, KG ăn tên thực thể. Đưa cùng một chuỗi cho cả ba là phí ít nhất hai cái. Một lời gọi trả cả ba.

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_rewrite.py`:

```python
from flow1.retrievers import RewrittenQuery
from flow1.rewrite import rewrite_query
from flow1.trace import Trace


def _call_tra(keywords, cau_hoi, thuc_the):
    def call(system, user_blocks, schema):
        return RewrittenQuery(keywords=keywords, cau_hoi=cau_hoi, thuc_the=thuc_the)

    return call


def test_tra_du_ba_truong():
    got = rewrite_query(
        "cơ chế chú ý là gì",
        call=_call_tra(["chú ý", "attention"], "Cơ chế attention hoạt động thế nào?", ["attention"]),
    )
    assert got.keywords == ["chú ý", "attention"]
    assert got.cau_hoi == "Cơ chế attention hoạt động thế nào?"
    assert got.thuc_the == ["attention"]


def test_loi_goi_model_thi_lui_ve_passthrough_khong_nem():
    def no(system, user_blocks, schema):
        raise RuntimeError("het quota")

    got = rewrite_query("cơ chế attention", call=no)
    assert got.cau_hoi == "cơ chế attention"
    assert got.keywords == ["cơ chế attention"]


def test_model_tra_thieu_truong_thi_lui_ve_passthrough():
    def hong(system, user_blocks, schema):
        return "khong phai RewrittenQuery"

    got = rewrite_query("attention", call=hong)
    assert got == RewrittenQuery.passthrough("attention")


def test_keywords_rong_thi_lui_ve_passthrough():
    """keywords rong lam BM25 tra rong, ma BM25 la nguon cua cong 1."""
    got = rewrite_query("attention", call=_call_tra([], "attention la gi", ["attention"]))
    assert got.keywords == ["attention"]


def test_trace_ghi_ca_query_goc_lan_ba_dang():
    trace = Trace("cơ chế chú ý là gì")
    rewrite_query(
        "cơ chế chú ý là gì",
        call=_call_tra(["chú ý", "attention"], "Attention la gi?", ["attention"]),
        trace=trace,
    )
    stage = next(s for s in trace.stages if s.name == "rewrite")
    assert stage.data["goc"] == "cơ chế chú ý là gì"
    assert stage.data["keywords"] == ["chú ý", "attention"]
    assert stage.data["cau_hoi"] == "Attention la gi?"
    assert stage.data["thuc_the"] == ["attention"]


def test_trace_ghi_ly_do_khi_lui():
    def no(system, user_blocks, schema):
        raise RuntimeError("het quota")

    trace = Trace("q")
    rewrite_query("attention", call=no, trace=trace)
    stage = next(s for s in trace.stages if s.name == "rewrite")
    assert "het quota" in stage.data["da_lui"]


def test_khong_truyen_call_va_khong_co_provider_thi_van_chay(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    got = rewrite_query("attention")
    assert got.cau_hoi == "attention"
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_rewrite.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.rewrite'`

- [ ] **Step 3: Thêm prompt vào `flow1/src/flow1/prompts.py`**

```python
REWRITE_SYSTEM = """Ban viet lai cau hoi cua hoc vien thanh BA dang, moi dang
phuc vu mot cach tra cuu khac nhau trong ban ghi 6 buoi hoc ve AI.

1. keywords — tu khoa cho tim kiem theo tu (BM25).
   Bo tu de, giu tu mang nghia. BO SUNG dong nghia Viet-Anh vi bai giang lan
   ca hai: "co che chu y" -> them "attention"; "mo hinh ngon ngu lon" -> them
   "LLM"; "tinh chinh" -> them "fine-tuning".

2. cau_hoi — mot cau hoi tu nhien, day du, ro rang, cho tim kiem theo nghia.
   Giai dai tu, lam ro thu bi hoi. Giu nguyen y dinh cua nguoi hoi.

3. thuc_the — ten cac KHAI NIEM duoc hoi toi, dang danh tu ngan.
   Vi du "attention", "transformer", "RAG". Khong phai cau, khong phai dong tu.

LUAT: khong bia them chu de nguoi ta khong hoi. Khong doi cau hoi thanh cau
hoi khac. Neu cau hoi da ro thi cu giu gan nguyen."""


def rewrite_user(question: str) -> str:
    return f"Cau hoi cua hoc vien:\n{question}"
```

- [ ] **Step 4: Viết `flow1/src/flow1/rewrite.py`**

```python
"""Viet lai cau hoi thanh ba dang, MOT loi goi model.

VI SAO BA DANG: moi retriever manh o mot dang dau vao khac nhau. BM25 an tu
khoa (va can dong nghia Viet-Anh vi bai giang lan ca hai). Vector an cau tu
nhien day du. KG an ten khai niem de khop vao Concept.name. Dua cung mot chuoi
cho ca ba la phi it nhat hai cai.

KHONG BAO GIO NEM: hong o day khong duoc lam chet ca truy van. Loi gi cung lui
ve passthrough (nguyen cau hoi vao ca ba truong) va ghi ly do vao trace — ket
qua kem hon nhung van co ket qua.
"""

from __future__ import annotations

from flow1.prompts import REWRITE_SYSTEM, rewrite_user
from flow1.retrievers import RewrittenQuery


def _default_call(system, user_blocks, schema):
    from summarizer.llm import OpenAIStructuredLLM

    user = "\n\n".join(b["text"] for b in user_blocks if b["type"] == "text")
    return OpenAIStructuredLLM().parse(
        model="gpt-4o-mini",
        system=system,
        user=user,
        schema=schema,
        temperature=0.0,
    )


def rewrite_query(question: str, *, call=None, trace=None) -> RewrittenQuery:
    """Mot call -> ba dang. Hong thi lui ve passthrough, khong nem."""
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(question)
    lui = RewrittenQuery.passthrough(question)

    with trace.stage("rewrite") as tdata:
        tdata["goc"] = question

        call = call if call is not None else _default_call

        # Moi loi deu bat o day, ke ca ImportError khi thieu package provider:
        # `_default_call` import ben trong than ham nen loi nap chi noi len o
        # day chu khong o cho gan `call`.
        try:
            got = call(
                REWRITE_SYSTEM,
                [{"type": "text", "text": rewrite_user(question)}],
                RewrittenQuery,
            )
        except Exception as exc:
            tdata["da_lui"] = f"{type(exc).__name__}: {exc}"
            return lui

        if not isinstance(got, RewrittenQuery):
            tdata["da_lui"] = f"model tra ve {type(got).__name__}, khong phai RewrittenQuery"
            return lui

        # keywords rong lam BM25 tra rong, ma BM25 la nguon so lieu cua cong 1.
        if not got.keywords or not got.cau_hoi.strip():
            tdata["da_lui"] = "model tra thieu keywords hoac cau_hoi"
            return lui

        tdata["keywords"] = got.keywords
        tdata["cau_hoi"] = got.cau_hoi
        tdata["thuc_the"] = got.thuc_the
        return got
```

- [ ] **Step 5: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_rewrite.py -q`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add flow1/src/flow1/rewrite.py flow1/src/flow1/prompts.py flow1/tests/test_flow1_rewrite.py
git commit -m "feat(flow1): viet lai query thanh ba dang bang mot loi goi model

BM25 an tu khoa (co dong nghia Viet-Anh vi bai giang lan ca hai), vector an
cau tu nhien, KG an ten khai niem. Dua cung mot chuoi cho ca ba la phi it
nhat hai cai.

Khong bao gio nem: hong gi cung lui ve passthrough va ghi ly do vao trace.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 12: Agent tool-calling + 2 tool

**Files:**
- Create: `flow1/src/flow1/tools.py`, `flow1/src/flow1/agent.py`, `flow1/tests/test_flow1_tools.py`, `flow1/tests/test_flow1_agent.py`

**Interfaces:**
- Consumes: `rewrite_query` (Task 11), `retrieve`/`Toggles` (Task 10), `ask` (Task 5), `gate0`/`template_for`/`CONTENT_LABEL` từ `flow1.gates`
- Produces:
  - `TOOL_SCHEMAS: list[dict]` — khai báo 2 tool theo chuẩn function-calling
  - `tra_cuu(query, *, session=None, toggles=None, store=None, trace=None, **kw) -> Result`
  - `tom_tat(session_id, *, trace=None, load_summary=None) -> dict`
  - `agent_run(question, *, tool_call=None, trace=None, **kw) -> AgentResult`
  - `AgentResult(outcome, message, tool_name, result, trace)`

- [ ] **Step 1: Viết test thất bại cho tools**

Tạo `flow1/tests/test_flow1_tools.py`:

```python
import pytest

from flow1.retrieve import Toggles
from flow1.tools import TOOL_SCHEMAS, tom_tat, tra_cuu
from flow1.trace import Trace


def _intent_noi_dung(system, blocks, schema):
    from flow1.models import Intent

    return Intent(label="nội_dung_khoá", reason="test")


def _no_model(*args):
    raise RuntimeError("khong goi model trong test")


def _rewrite_thang(system, blocks, schema):
    from flow1.retrievers import RewrittenQuery

    return RewrittenQuery(keywords=["attention"], cau_hoi="attention la gi", thuc_the=["attention"])


def test_co_dung_hai_tool():
    assert {s["function"]["name"] for s in TOOL_SCHEMAS} == {"tra_cuu", "tom_tat"}


def test_schema_tool_khai_du_tham_so_bat_buoc():
    tra = next(s for s in TOOL_SCHEMAS if s["function"]["name"] == "tra_cuu")
    assert "query" in tra["function"]["parameters"]["required"]

    tom = next(s for s in TOOL_SCHEMAS if s["function"]["name"] == "tom_tat")
    assert "session_id" in tom["function"]["parameters"]["required"]


def test_tra_cuu_di_qua_viet_lai_query_roi_moi_retrieve(bm25_store):
    trace = Trace("q")
    tra_cuu(
        "cơ chế attention là gì",
        store=bm25_store, trace=trace, segs=[],
        rewrite_call=_rewrite_thang, classify_call=_intent_noi_dung, answer_call=_no_model,
    )
    names = [s.name for s in trace.stages]
    assert names.index("rewrite") < names.index("bm25")


def test_tra_cuu_truyen_toggles_xuong_retrieve(bm25_store):
    trace = Trace("q")
    tra_cuu(
        "attention", store=bm25_store, trace=trace, segs=[],
        toggles=Toggles(bm25=True, qdrant=False, neo4j=False),
        rewrite_call=_rewrite_thang, classify_call=_intent_noi_dung, answer_call=_no_model,
    )
    qdrant = next(s for s in trace.stages if s.name == "qdrant")
    assert qdrant.data["gop_vao_fusion"] is False


def test_tom_tat_tra_ve_tom_tat_co_ma_doan():
    def load_summary(session_id):
        return {"session_id": session_id, "key_points": [{"claim": "x", "cite": ["T03-001"]}]}

    got = tom_tat("T03", load_summary=load_summary)
    assert got["session_id"] == "T03"
    assert got["key_points"][0]["cite"] == ["T03-001"]


def test_tom_tat_buoi_khong_ton_tai_thi_tu_choi_liet_ke_buoi_co_san():
    def load_summary(session_id):
        raise FileNotFoundError(session_id)

    got = tom_tat("T07", load_summary=load_summary)
    assert got["status"] == "out_of_scope"
    assert "T01" in got["message"]


def test_tom_tat_chuan_hoa_ma_buoi():
    ghi = {}

    def load_summary(session_id):
        ghi["session_id"] = session_id
        return {"session_id": session_id, "key_points": []}

    tom_tat("3", load_summary=load_summary)
    assert ghi["session_id"] == "T03"


def test_tom_tat_ghi_trace():
    trace = Trace("tom tat buoi 3")
    tom_tat("T03", trace=trace, load_summary=lambda s: {"session_id": s, "key_points": []})
    stage = next(s for s in trace.stages if s.name == "tom_tat")
    assert stage.data["session_id"] == "T03"
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_tools.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.tools'`

- [ ] **Step 3: Viết `flow1/src/flow1/tools.py`**

```python
"""Hai tool cua agent.

tra_cuu  — viet lai query -> fuse ba nhanh -> 4 cong -> cau tra loi co ma doan.
tom_tat  — tra so tay ca buoi tu package summarizer (co cache).

RANH GIOI: tool KHONG tu quyet dinh duoc goi hay khong — do la viec cua agent.
Tool cung khong biet gi ve LLM dieu phoi; no chi lam dung phan viec cua no.
"""

from __future__ import annotations

from typing import Any

SESSIONS_CO_SAN = ("T01", "T02", "T03", "T04", "T05", "T06")

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tra_cuu",
            "description": (
                "Tra cuu noi dung LOI GIANG trong 6 buoi co ban ghi va tra loi "
                "kem ma doan trich dan. Dung cho moi cau hoi ve kien thuc, khai "
                "niem, vi du, cach lam ma giang vien da noi trong buoi."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Cau hoi cua hoc vien, giu nguyen van.",
                    },
                    "session": {
                        "type": "string",
                        "description": (
                            "Ma buoi de gioi han pham vi, dang '01'..'06'. "
                            "Bo trong khi hoc vien khong noi ro buoi nao."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tom_tat",
            "description": (
                "Tra so tay tom tat CA MOT BUOI hoc: cac y chinh kem ma doan. "
                "Dung khi hoc vien xin tom tat, xin y chinh, hoac hoi 'buoi X noi ve gi'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Ma buoi, dang 'T01'..'T06'.",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
]


def _chuan_hoa_buoi(session_id: str) -> str:
    """'3' | '03' | 'T03' -> 'T03'."""
    raw = str(session_id).strip().upper().removeprefix("T")
    return f"T{int(raw):02d}" if raw.isdigit() else f"T{raw}"


def tra_cuu(
    query: str,
    *,
    session: str | None = None,
    toggles=None,
    store=None,
    retrievers=None,
    trace=None,
    rewrite_call=None,
    **kw,
):
    """Viet lai query -> retrieve ba nhanh -> 4 cong. Tra ve `flow1.ask.Result`.

    `retrievers` phai di xuyen xuong toi retrieve, khong duoc nuot: test goi
    tra_cuu voi mot dict chi co BM25 that de KHONG cham mang. Nuot tham so nay
    la moi test co .env deu goi Qdrant that.
    """
    from flow1.ask import ask
    from flow1.rewrite import rewrite_query

    q = rewrite_query(query, call=rewrite_call, trace=trace)
    return ask(
        query,
        session=session,
        store=store,
        trace=trace,
        rewritten=q,
        toggles=toggles,
        retrievers=retrievers,
        **kw,
    )


def _load_summary_that(session_id: str) -> dict[str, Any]:
    """Doc session summary da sinh boi package summarizer."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    path = root / "summarizer" / "artifacts" / "summaries" / session_id / "session.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def tom_tat(session_id: str, *, trace=None, load_summary=None, **kw) -> dict[str, Any]:
    """So tay ca buoi. Buoi khong co ban ghi -> tu choi + liet ke buoi co san.

    `**kw` nuot cac tham so cua tool KIA (toggles, store, segs...). agent_run
    truyen mot bo tool_kwargs chung xuong tool nao duoc chon; khong nuot thi
    model chon tom_tat la TypeError.
    """
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(session_id)
    load_summary = load_summary if load_summary is not None else _load_summary_that

    with trace.stage("tom_tat") as tdata:
        sid = _chuan_hoa_buoi(session_id)
        tdata["session_id"] = sid
        tdata["xin_ban_dau"] = session_id

        try:
            summary = load_summary(sid)
        except FileNotFoundError:
            tdata["ket_luan"] = f"khong co ban ghi cho {sid}"
            return {
                "status": "out_of_scope",
                "session_id": sid,
                "message": (
                    f"Minh khong co ban ghi cua buoi {sid}. Sau buoi minh co ban "
                    f"ghi: {', '.join(SESSIONS_CO_SAN)}."
                ),
            }

        tdata["n_y_chinh"] = len(summary.get("key_points", []))
        return summary
```

- [ ] **Step 4: Nới `ask()` nhận `rewritten`, `toggles`, `retrievers`**

Trong `flow1/src/flow1/ask.py`, thêm ba tham số `rewritten=None, toggles=None, retrievers=None` vào chữ ký `ask` và truyền **hết** xuống `retrieve`:

```python
    retrieval = retrieve(
        rewritten if rewritten is not None else question,
        session=session, store=store, path=path,
        toggles=toggles, retrievers=retrievers, trace=trace,
    )
```

`retrievers` phải đi xuyên xuống, không được nuốt — nuốt là mọi test có `.env` trên máy đều gọi Qdrant thật qua `default_retrievers`.

Trong test của Task 12, dựng sẵn dict chỉ có BM25 thật:

```python
def _chi_bm25(store):
    from flow1.retrievers import BM25Retriever, NullRetriever

    return {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "tat trong test"),
        "neo4j": NullRetriever("neo4j", "tat trong test"),
    }
```

và truyền `retrievers=_chi_bm25(bm25_store)` vào mọi lời gọi `tra_cuu` trong `test_flow1_tools.py`.

- [ ] **Step 5: Viết test thất bại cho agent**

Tạo `flow1/tests/test_flow1_agent.py`:

```python
from flow1.agent import agent_run
from flow1.trace import Trace


def _goi_tool(name, args):
    def tool_call(system, user, tools):
        return {"name": name, "arguments": args}

    return tool_call


def test_rule_chan_chao_hoi_truoc_khi_toi_agent():
    def khong_duoc_goi(system, user, tools):
        raise AssertionError("rule phai chan truoc, khong duoc goi model")

    got = agent_run("hi", tool_call=khong_duoc_goi)
    assert got.outcome == "off_topic"
    assert got.tool_name is None


def test_rule_chan_logistics_truoc_khi_toi_agent():
    def khong_duoc_goi(system, user, tools):
        raise AssertionError("rule phai chan truoc")

    got = agent_run("deadline nop bai la khi nao", tool_call=khong_duoc_goi)
    assert got.outcome == "off_topic"


def test_rule_chan_cau_hoi_ve_chinh_bot():
    def khong_duoc_goi(system, user, tools):
        raise AssertionError("rule phai chan truoc")

    got = agent_run("ban la gpt hay claude", tool_call=khong_duoc_goi)
    assert got.outcome == "off_topic"


def test_agent_chon_tom_tat_thi_goi_dung_tool():
    ghi = {}

    def tom_tat_gia(session_id, *, trace=None, **kw):
        ghi["session_id"] = session_id
        return {"session_id": session_id, "key_points": []}

    got = agent_run(
        "tom tat buoi 3 cho minh",
        tool_call=_goi_tool("tom_tat", {"session_id": "T03"}),
        tools={"tom_tat": tom_tat_gia},
    )
    assert got.tool_name == "tom_tat"
    assert ghi["session_id"] == "T03"


def test_agent_chon_tra_cuu_thi_truyen_dung_tham_so():
    ghi = {}

    def tra_cuu_gia(query, *, session=None, trace=None, **kw):
        ghi["query"] = query
        ghi["session"] = session
        return {"outcome": "answered"}

    got = agent_run(
        "co che attention la gi",
        tool_call=_goi_tool("tra_cuu", {"query": "co che attention la gi", "session": "04"}),
        tools={"tra_cuu": tra_cuu_gia},
    )
    assert got.tool_name == "tra_cuu"
    assert ghi["query"] == "co che attention la gi"
    assert ghi["session"] == "04"


def test_model_chon_tool_khong_ton_tai_thi_lui_ve_tra_cuu():
    ghi = {}

    def tra_cuu_gia(query, **kw):
        ghi["goi"] = True
        return {"outcome": "answered"}

    got = agent_run(
        "attention la gi",
        tool_call=_goi_tool("tool_bia_ra", {}),
        tools={"tra_cuu": tra_cuu_gia},
    )
    assert ghi.get("goi") is True
    assert got.tool_name == "tra_cuu"


def test_goi_model_that_bai_thi_lui_ve_tra_cuu():
    ghi = {}

    def no(system, user, tools):
        raise RuntimeError("het quota")

    def tra_cuu_gia(query, **kw):
        ghi["goi"] = True
        return {"outcome": "answered"}

    got = agent_run("attention la gi", tool_call=no, tools={"tra_cuu": tra_cuu_gia})
    assert ghi.get("goi") is True


def test_trace_ghi_rule_gate_va_lua_chon_tool():
    trace = Trace("attention la gi")
    agent_run(
        "attention la gi",
        tool_call=_goi_tool("tra_cuu", {"query": "attention la gi"}),
        tools={"tra_cuu": lambda query, **kw: {"outcome": "answered"}},
        trace=trace,
    )
    names = [s.name for s in trace.stages]
    assert "rule_gate" in names
    assert "agent" in names
    agent = next(s for s in trace.stages if s.name == "agent")
    assert agent.data["tool_da_chon"] == "tra_cuu"
```

- [ ] **Step 6: Viết `flow1/src/flow1/agent.py`**

```python
"""Agent dieu phoi hai tool, co RULE TAT DINH chan truoc.

THU TU LA CO CHU Y:
  rule (0 token)  -> chan chao hoi, logistics, ngoai pham vi, jailbreak
  agent (1 call)  -> chon tool va dien tham so
  tool            -> lam viec that

Chan bang rule truoc giu duoc hai thu: moi cau rac khong ton mot loi goi model,
va lop chan tat dinh ma 4 cong dang dua vao khong bi thay bang phan doan cua
model. Day la khac biet voi "agent thuan" — va la thu giai thich duoc o CP5.

LUI VE TRA_CUU: model hong, tra tool la, hay khong chon tool nao thi mac dinh
tra_cuu. Cau hoi ve noi dung la da so, va tra_cuu con 4 cong dung sau no —
doan sai o day khong lam mat lop bao ve nao.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flow1.gates import CONTENT_LABEL, classify_rule, template_for
from flow1.tools import TOOL_SCHEMAS

AGENT_SYSTEM = """Ban dieu phoi mot tro ly hoc tap cho khoa AI co ban ghi 6 buoi.

Chon DUNG MOT tool cho moi cau hoi:
- tra_cuu: hoc vien hoi ve kien thuc, khai niem, vi du, cach lam.
- tom_tat: hoc vien xin tom tat ca mot buoi, xin y chinh cua buoi, hoac hoi
  "buoi X noi ve gi".

Khi hoc vien khong noi ro buoi nao thi BO TRONG tham so buoi — he thong se
hoi lai neu can, dung tu doan mot buoi."""


@dataclass(frozen=True)
class AgentResult:
    outcome: str
    message: str
    tool_name: str | None = None
    result: Any = None
    trace: object | None = None


def _default_tool_call(system: str, user: str, tools: list[dict]) -> dict[str, Any]:
    import json
    import os

    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    response = client.chat.completions.create(
        model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        tools=tools,
        tool_choice="required",
        temperature=0.0,
    )
    call = response.choices[0].message.tool_calls[0]
    return {"name": call.function.name, "arguments": json.loads(call.function.arguments)}


def agent_run(
    question: str,
    *,
    tool_call=None,
    tools: dict | None = None,
    trace=None,
    **tool_kwargs,
) -> AgentResult:
    """Rule chan truoc, roi agent chon tool, roi chay tool do."""
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(question)

    # ---- RULE TAT DINH, 0 token ------------------------------------------
    with trace.stage("rule_gate") as tdata:
        label = classify_rule(question)
        tdata["nhan"] = label
        tdata["chan"] = label is not None and label != CONTENT_LABEL
    if label is not None and label != CONTENT_LABEL:
        return AgentResult(
            outcome="off_topic", message=template_for(label), trace=trace
        )

    if tools is None:
        from flow1 import tools as _tools_mod

        tools = {"tra_cuu": _tools_mod.tra_cuu, "tom_tat": _tools_mod.tom_tat}

    # ---- AGENT chon tool --------------------------------------------------
    with trace.stage("agent") as tdata:
        call = tool_call if tool_call is not None else _default_tool_call
        chon: dict[str, Any]
        try:
            chon = call(AGENT_SYSTEM, question, TOOL_SCHEMAS)
        except Exception as exc:
            tdata["da_lui"] = f"{type(exc).__name__}: {exc}"
            chon = {"name": "tra_cuu", "arguments": {"query": question}}

        ten = chon.get("name")
        if ten not in tools:
            tdata["tool_la"] = ten
            tdata["da_lui"] = f"model chon tool khong co that: {ten!r}"
            chon = {"name": "tra_cuu", "arguments": {"query": question}}
            ten = "tra_cuu"

        args = dict(chon.get("arguments") or {})
        if ten == "tra_cuu":
            args.setdefault("query", question)
            if not (args.get("session") or "").strip():
                args.pop("session", None)
        tdata["tool_da_chon"] = ten
        tdata["tham_so"] = args

    ket_qua = tools[ten](**args, trace=trace, **tool_kwargs)
    return AgentResult(
        outcome=getattr(ket_qua, "outcome", None) or "answered",
        message=getattr(ket_qua, "message", "") or "",
        tool_name=ten,
        result=ket_qua,
        trace=trace,
    )
```

- [ ] **Step 7: Chạy test**

Run: `uv run pytest flow1/tests/test_flow1_tools.py flow1/tests/test_flow1_agent.py -q`
Expected: 8 + 8 = 16 passed

Run: `uv run pytest -q`
Expected: toàn bộ xanh

- [ ] **Step 8: Commit**

```bash
git add flow1/
git commit -m "feat(flow1): agent tool-calling 2 tool, rule tat dinh chan truoc

Rule chan chao hoi/logistics/ngoai pham vi/jailbreak voi 0 token, truoc khi
toi agent. Giu duoc lop chan tat dinh ma 4 cong dang dua vao thay vi thay
bang phan doan cua model.

Model hong, tra tool la, hay khong chon tool nao thi lui ve tra_cuu — cau hoi
noi dung la da so, va tra_cuu con 4 cong dung sau no.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 13: Streamlit — 3 toggle + bảng so sánh nhánh + panel trace

**Files:**
- Modify: `flow1/app/app.py`
- Create: `flow1/src/flow1/branch_table.py`, `flow1/tests/test_flow1_branch_table.py`

**Interfaces:**
- Consumes: `Trace` (Task 4), `Toggles` (Task 10), `agent_run` (Task 12)
- Produces: `branch_table(trace) -> list[dict]` — mỗi nhánh một dòng: tên · số mã trả về · ms · mã **chỉ** nhánh đó tìm ra · lý do bỏ qua

Tách phần tính bảng ra khỏi `app.py` để test được mà không cần chạy Streamlit.

- [ ] **Step 1: Viết test thất bại**

Tạo `flow1/tests/test_flow1_branch_table.py`:

```python
from flow1.branch_table import branch_table
from flow1.trace import Trace


def _trace_mau():
    trace = Trace("attention la gi")
    with trace.stage("bm25") as d:
        d["top10"] = [("T04-001", 12.5), ("T04-002", 9.1)]
        d["ms"] = 0.8
        d["gop_vao_fusion"] = True
    with trace.stage("qdrant") as d:
        d["top10"] = [("T04-002", 0.91), ("T04-099", 0.88)]
        d["ms"] = 210.4
        d["gop_vao_fusion"] = True
    with trace.stage("neo4j") as d:
        d["top10"] = []
        d["ms"] = 0.1
        d["gop_vao_fusion"] = False
        d["bo_qua"] = "thieu bien moi truong: NEO4J_URL"
    with trace.stage("fuse") as d:
        d["chi_mot_nhanh_tim_ra"] = {
            "bm25": ["T04-001"], "qdrant": ["T04-099"], "neo4j": []
        }
    return trace


def test_mot_dong_moi_nhanh():
    assert [r["nhanh"] for r in branch_table(_trace_mau())] == ["bm25", "qdrant", "neo4j"]


def test_dem_dung_so_ma_va_thoi_gian():
    rows = {r["nhanh"]: r for r in branch_table(_trace_mau())}
    assert rows["bm25"]["so_ma"] == 2
    assert rows["qdrant"]["ms"] == 210.4


def test_chi_ra_ma_chi_mot_nhanh_tim_duoc():
    """Day la con so tra loi 'nhanh nay dong gop gi'."""
    rows = {r["nhanh"]: r for r in branch_table(_trace_mau())}
    assert rows["bm25"]["chi_minh_no"] == ["T04-001"]
    assert rows["qdrant"]["chi_minh_no"] == ["T04-099"]


def test_hien_ly_do_bo_qua():
    rows = {r["nhanh"]: r for r in branch_table(_trace_mau())}
    assert "NEO4J_URL" in rows["neo4j"]["ghi_chu"]


def test_hien_loi_khi_nhanh_no():
    trace = Trace("q")
    with trace.stage("qdrant") as d:
        d["top10"] = []
        d["ms"] = 5.0
        d["gop_vao_fusion"] = True
        d["loi"] = "ConnectionError: mat mang"
    rows = {r["nhanh"]: r for r in branch_table(trace)}
    assert "mat mang" in rows["qdrant"]["ghi_chu"]


def test_trace_khong_co_chang_nhanh_nao_thi_tra_rong():
    assert branch_table(Trace("q")) == []
```

- [ ] **Step 2: Chạy test để chắc nó đỏ**

Run: `uv run pytest flow1/tests/test_flow1_branch_table.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'flow1.branch_table'`

- [ ] **Step 3: Viết `flow1/src/flow1/branch_table.py`**

```python
"""Trace -> bang so sanh ba nhanh retrieve.

Tach khoi app.py de test duoc ma khong phai chay Streamlit.

Cot dat gia nhat la `chi_minh_no`: ma doan ma CHI nhanh do tim ra. Do la con
so tra loi truc tiep cau "bat nhanh nay len thi duoc them gi" — thu ma toggle
sinh ra de do.
"""

from __future__ import annotations

from typing import Any

NHANH = ("bm25", "qdrant", "neo4j")


def branch_table(trace) -> list[dict[str, Any]]:
    theo_ten = {s.name: s for s in trace.stages}
    fuse = theo_ten.get("fuse")
    chi_minh_no = (fuse.data.get("chi_mot_nhanh_tim_ra", {}) if fuse else {})

    rows = []
    for name in NHANH:
        stage = theo_ten.get(name)
        if stage is None:
            continue
        data = stage.data
        ghi_chu = data.get("loi") or data.get("bo_qua") or ""
        rows.append(
            {
                "nhanh": name,
                "bat": bool(data.get("gop_vao_fusion")),
                "so_ma": len(data.get("top10", [])),
                "ms": data.get("ms", round(stage.ms, 2)),
                "chi_minh_no": list(chi_minh_no.get(name, [])),
                "ghi_chu": ghi_chu,
            }
        )
    return rows
```

- [ ] **Step 4: Chạy test để chắc nó xanh**

Run: `uv run pytest flow1/tests/test_flow1_branch_table.py -q`
Expected: 6 passed

- [ ] **Step 5: Gắn vào `flow1/app/app.py`**

Đọc `app.py` trước để bám đúng cấu trúc hiện có. Thêm vào sidebar:

```python
import streamlit as st

from flow1.retrieve import Toggles

st.sidebar.subheader("Nhánh retrieve")
st.sidebar.caption("Tắt từng nhánh để đo nhánh nào đóng góp gì.")
bat_bm25 = st.sidebar.checkbox("BM25 (từ khoá)", value=True)
bat_qdrant = st.sidebar.checkbox("Qdrant (ngữ nghĩa)", value=True)
bat_neo4j = st.sidebar.checkbox("Neo4j (quan hệ)", value=True)
toggles = Toggles(bm25=bat_bm25, qdrant=bat_qdrant, neo4j=bat_neo4j)

if not bat_bm25:
    st.sidebar.warning(
        "BM25 đã tắt khỏi fusion nhưng **vẫn chạy** — cổng 1 quyết định "
        "trên điểm BM25 thô, tắt hẳn nó là tắt luôn lớp từ chối."
    )
```

Chỗ gọi, thay bằng `agent_run` và luôn bật trace:

```python
from flow1.agent import agent_run
from flow1.trace import new_trace

trace = new_trace(question, enabled=True)
ket_qua = agent_run(question, trace=trace, toggles=toggles, segs=segs)
```

Sau khi hiển thị câu trả lời:

```python
from flow1.branch_table import branch_table

rows = branch_table(trace)
if rows:
    st.subheader("So sánh ba nhánh")
    st.dataframe(rows, use_container_width=True)
    st.caption(
        "`chi_minh_no` = mã đoạn mà CHỈ nhánh đó tìm ra. Đây là con số trả lời "
        "'bật nhánh này lên thì được thêm gì'."
    )

with st.expander("Vì sao ra kết quả này"):
    for stage in trace.stages:
        st.markdown(f"**{stage.name}** · {stage.ms:.1f} ms")
        st.json(stage.data, expanded=False)
```

- [ ] **Step 6: Chạy thử app**

Run: `uv run streamlit run flow1/app/app.py --server.headless true`
Expected: khởi động không lỗi import. Hỏi một câu, tắt/bật từng checkbox, xác nhận bảng đổi theo. Ctrl-C sau khi xác nhận.

- [ ] **Step 7: Commit**

```bash
git add flow1/
git commit -m "feat(flow1): 3 toggle nhanh retrieve + bang so sanh + panel trace

Cot chi_minh_no la con so tra loi truc tiep 'bat nhanh nay len thi duoc them
gi' — thu ma toggle sinh ra de do.
Tat BM25 hien canh bao ro: no VAN CHAY vi cong 1 quyet dinh tren diem BM25 tho.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 14: Hiệu chỉnh lại T1 trên pipeline hoàn chỉnh

**Files:**
- Modify: `flow1/scripts/calibrate_t1.py`, `flow1/src/flow1/thresholds.py`, `eval/t1/distribution.md`
- Create: `eval/t1/distribution-truoc-nguyen-tu.md`

**Interfaces:**
- Consumes: `retrieve` (Task 10), `rewrite_query` (Task 11), `eval/t1/questions.jsonl` (30 câu, đã có)
- Produces: `T1_ABS`, `T1_RATIO` mới

**Làm ở CUỐI là có chủ ý.** Hai thứ dịch phân bố điểm BM25 so với lần hiệu chỉnh trước: đổi sang đơn vị nguyên tử, và BM25 nhận `keywords` đã viết lại thay vì câu hỏi thô. Hiệu chỉnh sớm hơn là đo sai thứ sẽ chạy thật.

- [ ] **Step 1: Giữ lại bảng cũ**

```bash
cp eval/t1/distribution.md eval/t1/distribution-truoc-nguyen-tu.md
```

Thêm dòng đầu vào file vừa sao chép:

```markdown
> **LƯU TRỮ.** Bảng này đo khi BM25 còn index 419 chunk gộp và nhận câu hỏi
> thô. Giữ lại làm bằng chứng cho phương án bị thay — xem `distribution.md`
> cho bản đang có hiệu lực.
```

- [ ] **Step 2: Sửa `calibrate_t1.py`**

Sửa `sys.path.insert` thành `parents[1] / "src"`. Sửa `measure` để chạy **đúng pipeline thật** nhưng tất định:

```python
def measure(questions: list[dict]) -> list[dict]:
    """Do tren dung duong chay that: co viet lai query, nhung KHONG cham mang.

    Viet lai query goi LLM nen khong tat dinh. De hieu chinh lap lai duoc, ta
    goi that MOT LAN roi cache ket qua ra eval/t1/rewritten.json. Chay lai lan
    sau doc cache -> cung mot dau vao, cung mot ket qua.
    """
    import json

    from flow1.index import load
    from flow1.retrieve import Toggles, retrieve
    from flow1.retrievers import BM25Retriever, NullRetriever
    from flow1.rewrite import rewrite_query

    cache_path = ROOT / "eval" / "t1" / "rewritten.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    store = load()
    retrievers = {
        "bm25": BM25Retriever(store),
        "qdrant": NullRetriever("qdrant", "hieu chinh T1 chi can BM25 tho"),
        "neo4j": NullRetriever("neo4j", "hieu chinh T1 chi can BM25 tho"),
    }

    rows = []
    for q in questions:
        if q["id"] not in cache:
            cache[q["id"]] = rewrite_query(q["text"]).model_dump()
        rewritten = RewrittenQuery.model_validate(cache[q["id"]])
        r = retrieve(
            rewritten, store=store, retrievers=retrievers,
            toggles=Toggles(bm25=True, qdrant=False, neo4j=False),
        )
        rows.append({
            **q,
            "top1_abs": r.top1_abs,
            "ratio": r.ratio,
            "top_session": r.hits[0].session if r.hits else "—",
            "top_section": r.hits[0].section_title if r.hits else "—",
        })

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows
```

Thêm `from flow1.retrievers import RewrittenQuery` vào import đầu file. Sửa dòng "Cách kiểm lại" ở cuối thành `uv run python flow1/scripts/calibrate_t1.py`.

- [ ] **Step 3: Chạy hiệu chỉnh**

Run: `uv run python flow1/scripts/calibrate_t1.py`
Expected: in ra `Đề xuất: T1_ABS = <x> · T1_RATIO = <y> → chặn <n>/10 · qua <m>/20`

**ĐIỂM DỪNG BẮT BUỘC.** Đọc dòng cuối `eval/t1/distribution.md`:

- Có **"Hai phân bố tách được"** và chặn **10/10** → đi tiếp Step 4.
- Có **"KHÔNG tách được hoàn toàn"** → **dừng lại, báo người dùng**, đưa cả hai bảng. **Không tự nới ngưỡng, không tự quay về đơn vị cũ.** Script tự ghi phần "hệ quả" vào file — đó là bằng chứng trung thực cho R4, không phải thất bại phải giấu.

- [ ] **Step 4: Cập nhật `thresholds.py`**

Sửa hai hằng số theo output script, và sửa docstring:

```python
TRẠNG THÁI: T1_ABS và T1_RATIO dưới đây đo trên PIPELINE HOÀN CHỈNH — đơn vị
nguyên tử (700 đoạn) và BM25 nhận `keywords` đã viết lại. Bản đo trên 419 chunk
gộp với câu hỏi thô lưu ở eval/t1/distribution-truoc-nguyen-tu.md.
Kiểm lại bằng:  uv run python flow1/scripts/calibrate_t1.py
Sửa hai số này thì phải chạy lại script và cập nhật distribution.md cùng lúc.
```

- [ ] **Step 5: Chạy lại toàn bộ test**

Run: `uv run pytest -q`
Expected: xanh. Test nào hardcode `T1_RATIO == 1.20` thì sửa để đọc từ `thresholds` thay vì gõ số.

- [ ] **Step 6: Commit — hai số và hai bảng đi CÙNG một commit**

```bash
git add flow1/src/flow1/thresholds.py flow1/scripts/calibrate_t1.py eval/t1/
git commit -m "fix(flow1): hieu chinh lai T1 tren pipeline hoan chinh

Hai thu dich phan bo diem BM25 so voi lan truoc: don vi index doi tu 419 chunk
gop sang doan nguyen tu, va BM25 gio nhan keywords da viet lai thay vi cau hoi
tho. Do lai tren dung 30 cau cu, cache ket qua viet lai de lap lai duoc.

Bang cu giu o distribution-truoc-nguyen-tu.md lam bang chung cho phuong an
bi thay. Hai so va hai bang di cung mot commit, dung luat file thresholds tu ghi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 15: Chạy lại toàn hệ, báo cáo, trace mẫu, tài liệu

**Files:**
- Modify: `docs/system-test-report.md`, `docs/FLOW_IMPLEMENTATION.md`, `README.md`, `graph-db/README.md`
- Create: `eval/traces/*.json`

- [ ] **Step 1: Chạy toàn hệ, không key**

```bash
mv .env .env.bak
uv run pytest -q 2>&1 | tail -20
mv .env.bak .env
```

Expected: **xanh 100%**, test `live` bị skip. Test nào đỏ khi thiếu key là vi phạm Global Constraint — sửa trước khi đi tiếp.

- [ ] **Step 2: Chạy toàn hệ, có key**

Run: `uv run pytest -q 2>&1 | tail -20`
Expected: xanh, test `live` chạy thật.

- [ ] **Step 3: Sinh trace mẫu**

```bash
mkdir -p eval/traces
uv run python -m flow1 ask "cơ chế attention là gì" --trace
uv run python -m flow1 ask "cho tôi biết đáp án bài lab 1 được không" --trace
uv run python -m flow1 ask "giải thích và tóm tắt nội dung học hôm này" --trace
uv run python -m flow1 ask "deadline nộp bài là khi nào" --trace
cp flow1/trace/*.json eval/traces/
```

Đổi tên cho người đọc hiểu ngay: `answered.json`, `refused.json`, `clarify.json`, `off-topic.json`. Kiểm từng file có `outcome` đúng như tên. Câu nào không ra đúng loại mong đợi thì **ghi sự thật đó vào report** thay vì đổi câu hỏi cho vừa ý.

- [ ] **Step 4: Cập nhật `docs/system-test-report.md`**

Thêm mục "Lần 2 — sau khi đổi kiến trúc retrieve", cùng khung bảng như Lần 1, cộng:

```markdown
### Ba nhanh dong gop gi

Doc bang `fuse` va `branch_table` trong eval/traces/answered.json:

| Nhanh | So ma tra ve | ms | Ma CHI nhanh do tim ra |
|---|---|---|---|
| bm25 | | | |
| qdrant | | | |
| neo4j | | | |

### Trang thai Neo4j

<song / chet + thong bao nguyen van. Neu song thi so Concept node.
Neu 0 Concept thi ghi ro nhanh KG luon tra rong cho toi khi chay ingest.>

### Nguong T1

| | Truoc (419 chunk gop, cau hoi tho) | Sau (doan nguyen tu, keywords viet lai) |
|---|---|---|
| T1_ABS | 0.00 | |
| T1_RATIO | 1.20 | |
| Chan ngoai pham vi | 10/10 | |
| Qua trong pham vi | 18/20 | |
```

- [ ] **Step 5: Sửa `docs/FLOW_IMPLEMENTATION.md`**

Thêm banner ngay sau dòng tiêu đề:

```markdown
> ⚠ **MỘT PHẦN ĐÃ THÀNH HIỆN THỰC, MỘT PHẦN CHƯA.** Tài liệu này mô tả 8 luồng.
> Hệ thống thực tế chạy **agent 2 tool**: tra cứu (hybrid BM25 + Qdrant + Neo4j)
> và tóm tắt. Các luồng multi-hop, comparison, recommendation ở đây **chưa**
> được xây. Kiến trúc đang chạy:
> `docs/superpowers/specs/2026-07-30-agent-2-tool-rag-3-nhanh-design.md`.
```

Sửa `1536 dimensions` thành `768` trong mục 2.2 (kiểm bằng grep, sửa hết mọi chỗ) cho khớp `vector-db/artifacts/manifest.json`.

- [ ] **Step 6: Sửa `graph-db/README.md`**

Nếu file này (do Task 12 của kế hoạch cũ, hoặc bản gốc) nói Neo4j "ngoài luồng" thì viết lại — giờ nó là **nhánh thứ ba của tool tra cứu**. Ghi rõ vai trò và ranh giới thẩm quyền:

```markdown
# graph-db — Neo4j knowledge graph

Nhánh thứ ba của tool tra cứu, bên cạnh BM25 và Qdrant. Trả về đoạn giảng
**liên quan qua quan hệ** — thứ vector search không làm được.

## Ranh giới thẩm quyền

KG mở rộng **recall**, không mở rộng **thẩm quyền**. `Concept` do LLM sinh lúc
ingest, nên nó chỉ được dùng để tìm đường tới `Turn`. Không một chữ nào của
`Concept.description` vào prompt sinh câu trả lời. Có test canh:
`graph-db/tests/test_graph_db_retrieve.py::test_cypher_khong_lay_mo_ta_concept`.

## Chạy

```bash
uv run python graph-db/scripts/check_neo4j.py         # smoke test ket noi
uv run python graph-db/scripts/ingest_transcripts.py  # ingest (can OPENAI_API_KEY)
uv run python graph-db/scripts/query_neo4j.py         # query mau
```

Cần `NEO4J_URL`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — xem `.env.example`.
```

- [ ] **Step 7: Cập nhật `README.md`**

Thêm mục "Chạy thử":

```markdown
## Chạy thử

```bash
uv sync --all-packages
cp .env.example .env      # điền key vào
uv run python scripts/check_env.py

uv run python -m flow1 index
uv run python -m flow1 ask "cơ chế attention là gì" --trace
uv run streamlit run flow1/app/app.py

uv run pytest             # xanh không cần key
uv run pytest -m live     # cần key
```
```

- [ ] **Step 8: Commit**

```bash
git add docs/ eval/traces/ README.md graph-db/README.md
git commit -m "docs: bao cao kiem thu lan 2, trace mau, cap nhat vai tro Neo4j

FLOW_IMPLEMENTATION.md them banner phan biet phan da xay va phan chua,
sua 1536 -> 768 cho khop collection da build.
graph-db/README viet lai: tu 'ngoai luong' thanh nhanh thu ba cua tool tra cuu,
kem ranh gioi tham quyen va test canh no.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Đối chiếu với "định nghĩa xong" của spec

| # | Điều kiện | Task |
|---|---|---|
| 1 | `uv run pytest` xanh không cần key | 3, 15 |
| 2 | Agent chọn đúng tool cho từng loại câu | 12 |
| 3 | Rule chặn chào hỏi/logistics/ngoài phạm vi trước agent, 0 token | 12 |
| 4 | Viết lại query trả đủ 3 trường, trace ghi cả gốc lẫn 3 dạng | 11 |
| 5 | Tắt nhánh trên UI thì kết quả đổi, bảng chỉ ra đoạn nào chỉ nhánh đó tìm ra | 10, 13 |
| 6 | Tắt BM25 khỏi fusion thì cổng 1 vẫn hoạt động, UI nói rõ | 10, 13 |
| 7 | Neo4j chết → vẫn trả lời bằng 2 nhánh còn lại, trace ghi lý do | 8, 9, 10 |
| 8 | Mọi mã KG trả về đều qua được cổng 3 | 9, 10 |
| 9 | T1 hiệu chỉnh lại trên pipeline hoàn chỉnh, bảng cũ giữ | 14 |
| 10 | `system-test-report.md` có trước và sau, trace mẫu trong `eval/traces/` | 3, 15 |
