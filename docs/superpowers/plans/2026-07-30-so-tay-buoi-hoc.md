# Sổ tay buổi học có trích dẫn transcript — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sinh sổ tay 1 trang gồm đúng 5 ý chính của một buổi học từ transcript, mỗi ý gắn mã đoạn `[Txx-NNN]` kiểm lại được, kèm bộ kiểm tất định chặn mã bịa và cờ bản ghi thiếu.

**Architecture:** Ba tầng — tầng tất định parse transcript và chặn buổi ngoài phạm vi; **đúng một lời gọi AI** nạp cả buổi (~40k token, không retrieval) và trả JSON có schema; tầng tất định đối chiếu mọi mã trích dẫn với chỉ mục 700 đoạn thật rồi render markdown. `verify.py` không import `llm.py` — người viết prompt (M2) và người viết bộ kiểm (M1) là hai người khác nhau.

**Tech Stack:** Python 3.13 · `anthropic` SDK (model `claude-opus-5`, structured output qua `messages.parse()` + Pydantic) · `pydantic` · `pytest` · stdlib `re`/`json`/`dataclasses`. Không web framework, không DB, không deploy.

**Spec:** `docs/superpowers/specs/2026-07-30-so-tay-buoi-hoc-design.md`

---

## Global Constraints

Mọi task đều chịu các ràng buộc này.

- **Python 3.13**, venv sẵn tại `.venv/` (Windows: `.venv/Scripts/python.exe`).
- **Không commit API key.** `llm.py` đọc `ANTHROPIC_API_KEY` từ biến môi trường. `.env` đã nằm trong `.gitignore`.
- **Model: `claude-opus-5`** (chuỗi ID chính xác, không thêm hậu tố ngày). Đây là ranh giới provider duy nhất, chỉ ở `llm.py`.
- **`data/` không vào repo nộp bài.** Test đọc data thật từ đường dẫn tương đối; nếu thiếu data thì test `skip`, không `fail`.
- **`verify.py` KHÔNG được import `llm.py` hay `generate.py`.** Có test kiểm điều này.
- **Đúng 5 ý** mỗi sổ tay. Ràng buộc ép ở `verify`, **không** ép ở JSON schema (structured output không hỗ trợ `minItems`/`maxItems`).
- **Mọi mã đoạn dạng `Txx-NNN`** (2 chữ số buổi, gạch, 3 chữ số đoạn). Trong markdown transcript chúng xuất hiện dạng `**[T03-014]**`.
- **File transcript dùng CRLF** (`\r\n`). Parser phải chịu được.
- **Tiếng Việt có dấu.** Mọi `open()` phải `encoding="utf-8"`. Khi chạy script in ra tiếng Việt trên Windows, đặt `PYTHONUTF8=1`.
- **Quality bar (chốt, không đổi sau 23:59 N1):** citation validity 100% · citation support ≥27/30 ý · recall ≥11/18 ý vàng · bịa/đảo ý 0/30 · từ chối đúng ca ③ 100% · cờ bản ghi thiếu 100%.
- **Số liệu ghi trung thực.** Lượt chạy không đạt bar vẫn ghi nguyên vào `eval/results/`, không xoá, không sửa.

**Số đo tham chiếu của data thật** (dùng làm assertion trong test — đã kiểm bằng script):

| File | Đoạn | `[không nghe rõ]` | `[Hoạt động lớp` |
|---|---|---|---|
| transcript-01-clean.md | 89 | 14 | 2 |
| transcript-02-clean.md | 43 | 10 | 6 |
| transcript-03-clean.md | 154 | 11 | 10 |
| transcript-04-clean.md | 98 | 15 | 9 |
| transcript-05-clean.md | 154 | 25 | 17 |
| transcript-06-clean.md | 162 | 28 | 11 |
| **Tổng** | **700** | **103** | **55** |

---

## Phân công

| Task | Chủ | Vai |
|---|---|---|
| 0 | M1 | Scaffold |
| 1 | M1 | `models.py` + `ingest.py` |
| 2 | M1 | `registry.py` (chỗ khó ③) |
| 3 | M1 | `verify.py` (chỗ khó ①②④) |
| 4 | M2 | `llm.py` — **lời gọi AI thật đầu tiên, mốc CP3** |
| 5 | M2 | `generate.py` + prompt |
| 6 | M4 | `render.py` |
| 7 | M4 | `cli.py` |
| 8 | M3 | `eval/mining/count_evidence.py` — sinh lại §2.1 |
| 9 | M3 + M5 | Golden set 20 case |
| 10 | M3 | `eval/harness.py` + 3 lượt chạy |
| 11 | M5 | Khảo sát 20 người + validation ≥3 người |
| 12 | M5 | `spec.md` + `README.md` + repo |
| 13 | M4 | `demo-slides.pdf` + dry run |

Task 1-3 (M1) chạy song song được với Task 8 (M3), 9 (M5), 11 (M5). Task 4-5 (M2) cần Task 1 xong. Task 6-7 (M4) cần Task 5 xong. Task 10 cần Task 5 + 9 xong.

---

### Task 0: Scaffold (M1)

**Files:**
- Create: `codebase/sotay/__init__.py`
- Create: `codebase/tests/__init__.py`
- Create: `codebase/pyproject.toml`
- Create: `.gitignore` (sửa file có sẵn)

**Interfaces:**
- Consumes: không
- Produces: package `sotay` import được; `pytest` chạy được từ `codebase/`

- [ ] **Step 1: Cài dependency**

```bash
cd codebase
../.venv/Scripts/python.exe -m pip install anthropic pydantic pytest
```

- [ ] **Step 2: Tạo pyproject.toml**

```toml
[project]
name = "sotay"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["anthropic", "pydantic"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Tạo hai file __init__.py rỗng**

```bash
cd codebase && touch sotay/__init__.py tests/__init__.py
```

- [ ] **Step 4: Bổ sung .gitignore ở gốc repo**

Thêm các dòng sau vào `.gitignore` (giữ nguyên nội dung cũ):

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
out/
```

- [ ] **Step 5: Xác nhận pytest chạy**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest -q`
Expected: `no tests ran` (exit code 5) — không phải lỗi import.

- [ ] **Step 6: Commit**

```bash
git add .gitignore codebase/pyproject.toml codebase/sotay/__init__.py codebase/tests/__init__.py
git commit -m "chore: scaffold sotay package"
```

---

### Task 1: `models.py` + `ingest.py` — parse transcript (M1)

**Files:**
- Create: `codebase/sotay/models.py`
- Create: `codebase/sotay/ingest.py`
- Create: `codebase/tests/test_ingest.py`

**Interfaces:**
- Consumes: không
- Produces:
  - `Segment(code: str, text: str, has_gap: bool, is_activity: bool)` — frozen dataclass
  - `KeyPoint(BaseModel)` với `statement: str`, `codes: list[str]`
  - `Notebook(BaseModel)` với `session_title: str`, `points: list[KeyPoint]`
  - `Finding(point_index: int, kind: str, detail: str)` — frozen dataclass
  - `parse_transcript(text: str) -> tuple[str, list[Segment]]` → `(session_title, segments)`
  - `load_session(session_id: str, data_dir: Path) -> tuple[str, list[Segment]]`
  - `content_segments(segments: list[Segment]) -> list[Segment]` — loại `is_activity`
  - `TRANSCRIPT_DIR: Path` — mặc định `data/vlearn-pack/transcript`

- [ ] **Step 1: Viết test thất bại**

`codebase/tests/test_ingest.py`:

```python
from pathlib import Path
import pytest
from sotay.ingest import parse_transcript, load_session, content_segments, TRANSCRIPT_DIR

SAMPLE = (
    "# Transcript bài giảng (bản sạch) — Day 2 (chiều) — Soi bài toán\r\n"
    "\r\n"
    "> **Quy ước:** `[Txx-NNN]` mã đoạn · `[không nghe rõ]` chỗ không khôi phục được\r\n"
    "\r\n"
    "## Giới thiệu\r\n"
    "\r\n"
    "**[T03-001]** [Hoạt động lớp: ổn định lớp, bật ghi hình.]\r\n"
    "\r\n"
    "**[T03-002]** Mình tên là [giảng viên], hiện đang là AI Research Engineer.\r\n"
    "\r\n"
    "**[T03-003]** Rồi mình sang một startup robot giao hàng [không nghe rõ]. Nếu các bạn ở gần đây.\r\n"
)


def test_title_excludes_the_boilerplate_prefix():
    title, _ = parse_transcript(SAMPLE)
    assert title == "Day 2 (chiều) — Soi bài toán"


def test_parses_every_segment_in_order():
    _, segs = parse_transcript(SAMPLE)
    assert [s.code for s in segs] == ["T03-001", "T03-002", "T03-003"]


def test_front_matter_legend_is_not_parsed_as_a_gap():
    # Dòng "> **Quy ước:**" chứa "[không nghe rõ]" như chú giải, không phải chỗ khuyết thật.
    _, segs = parse_transcript(SAMPLE)
    assert [s.has_gap for s in segs] == [False, False, True]


def test_flags_class_activity_notes():
    _, segs = parse_transcript(SAMPLE)
    assert [s.is_activity for s in segs] == [True, False, False]


def test_segment_text_is_stripped_and_excludes_its_own_code():
    _, segs = parse_transcript(SAMPLE)
    assert segs[1].text.startswith("Mình tên là")
    assert segs[1].text.endswith("Engineer.")
    assert "T03-002" not in segs[1].text


def test_content_segments_drops_activity_notes():
    _, segs = parse_transcript(SAMPLE)
    assert [s.code for s in content_segments(segs)] == ["T03-002", "T03-003"]


# --- Đối chiếu data thật. Skip nếu không có data pack (repo nộp bài không chứa data). ---

REAL = [
    ("01", 89, 14, 2),
    ("02", 43, 10, 6),
    ("03", 154, 11, 10),
    ("04", 98, 15, 9),
    ("05", 154, 25, 17),
    ("06", 162, 28, 11),
]


@pytest.mark.parametrize("session_id,n_segs,n_gaps,n_activity", REAL)
def test_real_transcript_counts(session_id, n_segs, n_gaps, n_activity):
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    _, segs = load_session(session_id, TRANSCRIPT_DIR)
    assert len(segs) == n_segs
    assert sum(s.has_gap for s in segs) == n_gaps
    assert sum(s.is_activity for s in segs) == n_activity


def test_real_corpus_totals():
    if not TRANSCRIPT_DIR.exists():
        pytest.skip("data pack không có mặt")
    all_segs = [s for sid, *_ in REAL for s in load_session(sid, TRANSCRIPT_DIR)[1]]
    assert len(all_segs) == 700
    assert sum(s.has_gap for s in all_segs) == 103
    assert sum(s.is_activity for s in all_segs) == 55
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_ingest.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.ingest'`

- [ ] **Step 3: Viết `models.py`**

`codebase/sotay/models.py`:

```python
"""Kiểu dữ liệu dùng chung. Chủ: M1."""

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Segment:
    """Một đoạn giảng có mã trích dẫn."""

    code: str          # "T03-014"
    text: str          # nguyên văn đoạn, đã strip
    has_gap: bool      # chứa "[không nghe rõ]" — bản ghi khuyết (chỗ khó ②)
    is_activity: bool  # là ghi chú "[Hoạt động lớp: ...]", không phải nội dung giảng (chỗ khó ④)


class KeyPoint(BaseModel):
    """Một ý chính của buổi học, kèm mã đoạn chống lưng."""

    statement: str = Field(description="Ý chính, viết thành MỘT câu tiếng Việt hoàn chỉnh.")
    codes: list[str] = Field(
        description="Mã đoạn chống lưng cho ý này, dạng T03-014. Tối thiểu 1 mã."
    )


class Notebook(BaseModel):
    """Sổ tay một buổi học."""

    session_title: str = Field(description="Tên buổi học.")
    points: list[KeyPoint] = Field(description="Đúng 5 ý chính, quan trọng nhất trước.")


@dataclass(frozen=True)
class Finding:
    """Phát hiện của bộ kiểm tất định."""

    point_index: int  # chỉ số ý trong Notebook.points; -1 = phát hiện cấp sổ tay
    kind: str         # unknown_code | wrong_point_count | no_codes | cites_activity | transcript_gap
    detail: str
```

- [ ] **Step 4: Viết `ingest.py`**

`codebase/sotay/ingest.py`:

```python
"""Parse transcript bản sạch thành list[Segment]. Chủ: M1.

Quy ước của data pack (xem data/vlearn-pack/transcript/README.md):
  - Dòng đầu: "# Transcript bài giảng (bản sạch) — <tên buổi>"
  - Front matter: các dòng bắt đầu bằng "> " — CHỨA "[không nghe rõ]" như chú giải,
    nên phải bỏ qua, nếu không sẽ đếm sai chỗ khuyết.
  - Đoạn giảng: "**[Txx-NNN]** <nội dung>"
  - "[Hoạt động lớp: ...]" = ghi chú hành chính đã rút gọn, KHÔNG phải nội dung giảng.
"""

from __future__ import annotations

import re
from pathlib import Path

from sotay.models import Segment

TRANSCRIPT_DIR = Path(__file__).resolve().parents[2] / "data" / "vlearn-pack" / "transcript"

GAP_MARKER = "[không nghe rõ]"
ACTIVITY_PREFIX = "[Hoạt động lớp"

_TITLE_RE = re.compile(r"^#\s*Transcript bài giảng \(bản sạch\)\s*—\s*(.+?)\s*$", re.MULTILINE)
# Bắt từ mã đoạn này tới mã đoạn kế tiếp (hoặc hết file). Chỉ khớp dạng in đậm.
_SEGMENT_RE = re.compile(
    r"\*\*\[(T\d{2}-\d{3})\]\*\*(.*?)(?=\*\*\[T\d{2}-\d{3}\]\*\*|\Z)",
    re.DOTALL,
)


def parse_transcript(text: str) -> tuple[str, list[Segment]]:
    """Trả (tên buổi, danh sách đoạn theo đúng thứ tự trong file)."""
    text = text.replace("\r\n", "\n")

    title_match = _TITLE_RE.search(text)
    title = title_match.group(1) if title_match else "Buổi học không rõ tên"

    segments: list[Segment] = []
    for code, body in _SEGMENT_RE.findall(text):
        body = body.strip()
        segments.append(
            Segment(
                code=code,
                text=body,
                has_gap=GAP_MARKER in body,
                is_activity=body.startswith(ACTIVITY_PREFIX),
            )
        )
    return title, segments


def load_session(session_id: str, data_dir: Path = TRANSCRIPT_DIR) -> tuple[str, list[Segment]]:
    """Đọc transcript-<session_id>-clean.md."""
    path = data_dir / f"transcript-{session_id}-clean.md"
    return parse_transcript(path.read_text(encoding="utf-8"))


def content_segments(segments: list[Segment]) -> list[Segment]:
    """Chỉ giữ đoạn nội dung giảng — loại ghi chú hoạt động lớp (chỗ khó ④)."""
    return [s for s in segments if not s.is_activity]


def index_by_code(segments: list[Segment]) -> dict[str, Segment]:
    """Chỉ mục mã → đoạn, dùng cho bộ kiểm ở verify.py."""
    return {s.code: s for s in segments}
```

- [ ] **Step 5: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_ingest.py -q`
Expected: PASS — 13 passed (7 unit + 6 parametrize + 1 totals; các test data thật sẽ skip nếu không có data pack)

- [ ] **Step 6: Commit**

```bash
git add codebase/sotay/models.py codebase/sotay/ingest.py codebase/tests/test_ingest.py
git commit -m "feat(ingest): parse transcript thanh Segment, danh dau gap va hoat dong lop"
```

---

### Task 2: `registry.py` — chặn buổi ngoài phạm vi (M1)

Đây là hiện thực của **chỗ khó ③**. Chặn **trước khi gọi AI** để không có đường nào cho AI bịa.

**Files:**
- Create: `codebase/sotay/registry.py`
- Create: `codebase/tests/test_registry.py`

**Interfaces:**
- Consumes: `sotay.ingest.TRANSCRIPT_DIR`
- Produces:
  - `SESSIONS: dict[str, str]` — mã buổi → tên buổi (6 buổi)
  - `SessionNotAvailable(Exception)` với thuộc tính `.session_id` và `.message`
  - `resolve(session_id: str) -> str` — trả tên buổi, hoặc raise `SessionNotAvailable`
  - `refusal_message(session_id: str) -> str` — câu từ chối kèm liệt kê buổi có sẵn

- [ ] **Step 1: Viết test thất bại**

`codebase/tests/test_registry.py`:

```python
import pytest
from sotay.registry import SESSIONS, SessionNotAvailable, refusal_message, resolve


def test_exactly_six_sessions_are_available():
    assert sorted(SESSIONS) == ["01", "02", "03", "04", "05", "06"]


def test_resolve_returns_the_session_title():
    assert "Day 2" in resolve("03")


def test_resolve_raises_for_a_session_with_no_transcript():
    with pytest.raises(SessionNotAvailable) as exc:
        resolve("07")
    assert exc.value.session_id == "07"


def test_refusal_names_the_missing_session():
    msg = refusal_message("07")
    assert "07" in msg


def test_refusal_lists_every_available_session_so_the_user_can_pick():
    msg = refusal_message("07")
    for session_id, title in SESSIONS.items():
        assert session_id in msg
        assert title in msg


def test_refusal_does_not_guess_or_apologise_vaguely():
    msg = refusal_message("07").lower()
    # Phải nói rõ KHÔNG CÓ transcript, không phải "hệ thống không tìm thấy".
    assert "không có transcript" in msg


def test_registry_does_not_touch_the_llm():
    import sotay.registry as registry

    source = open(registry.__file__, encoding="utf-8").read()
    assert "llm" not in source
    assert "anthropic" not in source
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_registry.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.registry'`

- [ ] **Step 3: Viết `registry.py`**

`codebase/sotay/registry.py`:

```python
"""Buổi nào có transcript. Chỗ khó ③ — ngoài phạm vi. Chủ: M1.

Chặn ở đây, TRƯỚC khi gọi AI: buổi không có transcript thì không có nguồn sự thật,
nên không có đường nào để AI bịa. Tốn 0 token.

Tên buổi lấy từ bảng ánh xạ trong data/vlearn-pack/transcript/README.md.
"""

from __future__ import annotations

SESSIONS: dict[str, str] = {
    "01": "Day 2 sáng — Xác định bài toán kinh doanh cho AI",
    "02": "Day 2 — Chỉ số thành công & mức tự động hoá",
    "03": "Day 2 chiều — Soi bài toán các nhóm · tự động hoá & ràng buộc",
    "04": "Day 1 — Foundation: cách LLM hoạt động",
    "05": "Buổi về bài toán · đánh giá · dữ liệu",
    "06": "Buổi Foundation: transformer & attention",
}


class SessionNotAvailable(Exception):
    """Buổi được yêu cầu không có transcript trong data pack."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.message = refusal_message(session_id)
        super().__init__(self.message)


def resolve(session_id: str) -> str:
    """Trả tên buổi. Raise SessionNotAvailable nếu buổi không có transcript."""
    if session_id not in SESSIONS:
        raise SessionNotAvailable(session_id)
    return SESSIONS[session_id]


def refusal_message(session_id: str) -> str:
    """Câu từ chối: nói rõ không có gì, rồi liệt kê có gì. Không đoán."""
    available = "\n".join(f"  - Buổi {sid}: {title}" for sid, title in sorted(SESSIONS.items()))
    return (
        f"Chưa làm được sổ tay cho buổi {session_id}: "
        f"khoá không có transcript của buổi này trong data pack, "
        f"nên mình không có nguồn nào để trích dẫn.\n\n"
        f"Sáu buổi hiện có transcript:\n{available}"
    )
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_registry.py -q`
Expected: PASS — 7 passed

- [ ] **Step 5: Commit**

```bash
git add codebase/sotay/registry.py codebase/tests/test_registry.py
git commit -m "feat(registry): tu choi buoi khong co transcript truoc khi goi AI"
```

---

### Task 3: `verify.py` — bộ kiểm tất định (M1)

Hiện thực **chỗ khó ①②④** ở phía kiểm. **Không import `llm.py` hay `generate.py`.**

**Files:**
- Create: `codebase/sotay/verify.py`
- Create: `codebase/tests/test_verify.py`

**Interfaces:**
- Consumes: `sotay.models.{Segment, KeyPoint, Notebook, Finding}`, `sotay.ingest.index_by_code`
- Produces:
  - `EXPECTED_POINTS: int = 5`
  - `verify(notebook: Notebook, segments: list[Segment]) -> list[Finding]`
  - `drop_invalid(notebook: Notebook, segments: list[Segment]) -> tuple[Notebook, list[Finding]]` — loại ý có mã bịa, giữ nguyên các ý còn lại
  - `gap_codes(notebook: Notebook, segments: list[Segment]) -> set[str]` — mã đoạn khuyết được trích

- [ ] **Step 1: Viết test thất bại**

`codebase/tests/test_verify.py`:

```python
import pytest
from sotay.models import KeyPoint, Notebook, Segment
from sotay.verify import EXPECTED_POINTS, drop_invalid, gap_codes, verify


def seg(code, text="nội dung giảng", has_gap=False, is_activity=False):
    return Segment(code=code, text=text, has_gap=has_gap, is_activity=is_activity)


SEGMENTS = [
    seg("T03-001", "[Hoạt động lớp: ổn định lớp.]", is_activity=True),
    seg("T03-002"),
    seg("T03-003", "robot giao hàng [không nghe rõ]", has_gap=True),
    seg("T03-004"),
    seg("T03-005"),
    seg("T03-006"),
]


def nb(*points, title="Buổi 3"):
    return Notebook(session_title=title, points=list(points))


def five_good_points():
    return [KeyPoint(statement=f"Ý số {i}", codes=[f"T03-00{i + 1}"]) for i in range(1, 6)]


def test_a_clean_notebook_yields_no_findings():
    assert verify(nb(*five_good_points()), SEGMENTS) == []


def test_flags_a_fabricated_code():
    book = nb(KeyPoint(statement="Ý bịa", codes=["T03-999"]), *five_good_points()[:4])
    kinds = {f.kind for f in verify(book, SEGMENTS)}
    assert "unknown_code" in kinds


def test_fabricated_code_finding_names_the_code():
    book = nb(KeyPoint(statement="Ý bịa", codes=["T03-999"]), *five_good_points()[:4])
    unknown = [f for f in verify(book, SEGMENTS) if f.kind == "unknown_code"]
    assert "T03-999" in unknown[0].detail


def test_flags_a_point_with_no_codes_at_all():
    book = nb(KeyPoint(statement="Ý không nguồn", codes=[]), *five_good_points()[:4])
    kinds = {f.kind for f in verify(book, SEGMENTS)}
    assert "no_codes" in kinds


def test_flags_the_wrong_number_of_points():
    book = nb(*five_good_points()[:3])
    findings = [f for f in verify(book, SEGMENTS) if f.kind == "wrong_point_count"]
    assert len(findings) == 1
    assert findings[0].point_index == -1
    assert str(EXPECTED_POINTS) in findings[0].detail


def test_flags_a_point_that_cites_a_class_activity_note():
    book = nb(KeyPoint(statement="Điểm danh", codes=["T03-001"]), *five_good_points()[:4])
    kinds = {f.kind for f in verify(book, SEGMENTS)}
    assert "cites_activity" in kinds


def test_flags_a_point_anchored_to_a_gap_deterministically():
    # AI không cần khai; verify tự tính từ Segment.has_gap.
    book = nb(
        KeyPoint(statement="Ý neo vào đoạn khuyết", codes=["T03-003"]),
        *five_good_points()[:4],
    )
    findings = [f for f in verify(book, SEGMENTS) if f.kind == "transcript_gap"]
    assert len(findings) == 1
    assert "T03-003" in findings[0].detail


def test_gap_codes_returns_the_gapped_codes_that_were_cited():
    book = nb(KeyPoint(statement="x", codes=["T03-002", "T03-003"]), *five_good_points()[:4])
    assert gap_codes(book, SEGMENTS) == {"T03-003"}


def test_drop_invalid_removes_only_points_with_fabricated_codes():
    good = five_good_points()[:4]
    book = nb(KeyPoint(statement="Ý bịa", codes=["T03-999"]), *good)
    cleaned, findings = drop_invalid(book, SEGMENTS)
    assert [p.statement for p in cleaned.points] == [p.statement for p in good]
    assert any(f.kind == "unknown_code" for f in findings)


def test_drop_invalid_never_repairs_a_code():
    book = nb(KeyPoint(statement="Ý bịa", codes=["T03-999"]))
    cleaned, _ = drop_invalid(book, SEGMENTS)
    assert cleaned.points == []


def test_drop_invalid_keeps_the_title():
    book = nb(KeyPoint(statement="Ý bịa", codes=["T03-999"]), title="Buổi 3 chiều")
    cleaned, _ = drop_invalid(book, SEGMENTS)
    assert cleaned.session_title == "Buổi 3 chiều"


def test_verify_is_independent_of_the_llm():
    # Người viết prompt (M2) và người viết bo kiem (M1) là hai người khác nhau.
    import sotay.verify as verify_module

    source = open(verify_module.__file__, encoding="utf-8").read()
    assert "import" in source
    assert "llm" not in source
    assert "generate" not in source
    assert "anthropic" not in source
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_verify.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.verify'`

- [ ] **Step 3: Viết `verify.py`**

`codebase/sotay/verify.py`:

```python
"""Bộ kiểm tất định cho output của AI. Chủ: M1.

KHÔNG import llm.py hay generate.py — bộ kiểm phải độc lập với người viết prompt.
Có test kiểm điều này (test_verify_is_independent_of_the_llm).

Nguyên tắc: phát hiện thì BÁO và LOẠI, không bao giờ tự sửa. Sửa mã đoạn hộ AI
tức là đoán, và đoán là đúng cái chỗ khó ① đang phòng.
"""

from __future__ import annotations

from sotay.ingest import index_by_code
from sotay.models import Finding, Notebook, Segment

EXPECTED_POINTS = 5


def verify(notebook: Notebook, segments: list[Segment]) -> list[Finding]:
    """Trả mọi phát hiện. Danh sách rỗng = sổ tay sạch."""
    index = index_by_code(segments)
    findings: list[Finding] = []

    if len(notebook.points) != EXPECTED_POINTS:
        findings.append(
            Finding(
                point_index=-1,
                kind="wrong_point_count",
                detail=(
                    f"Sổ tay có {len(notebook.points)} ý, "
                    f"quy ước là đúng {EXPECTED_POINTS} ý."
                ),
            )
        )

    for i, point in enumerate(notebook.points):
        if not point.codes:
            findings.append(
                Finding(
                    point_index=i,
                    kind="no_codes",
                    detail=f"Ý {i + 1} không có mã đoạn nào chống lưng.",
                )
            )
            continue

        for code in point.codes:
            segment = index.get(code)
            if segment is None:
                findings.append(
                    Finding(
                        point_index=i,
                        kind="unknown_code",
                        detail=f"Ý {i + 1} trích mã {code} — mã này không có trong transcript.",
                    )
                )
                continue
            if segment.is_activity:
                findings.append(
                    Finding(
                        point_index=i,
                        kind="cites_activity",
                        detail=(
                            f"Ý {i + 1} trích mã {code} — đoạn này là ghi chú hoạt động lớp, "
                            f"không phải nội dung giảng."
                        ),
                    )
                )
            if segment.has_gap:
                findings.append(
                    Finding(
                        point_index=i,
                        kind="transcript_gap",
                        detail=(
                            f"Ý {i + 1} neo vào mã {code} — đoạn này có chỗ [không nghe rõ]."
                        ),
                    )
                )

    return findings


def gap_codes(notebook: Notebook, segments: list[Segment]) -> set[str]:
    """Mã đoạn khuyết đang được sổ tay trích dẫn."""
    index = index_by_code(segments)
    return {
        code
        for point in notebook.points
        for code in point.codes
        if code in index and index[code].has_gap
    }


def drop_invalid(notebook: Notebook, segments: list[Segment]) -> tuple[Notebook, list[Finding]]:
    """Loại ý có mã bịa. Không sửa mã, không bù ý mới.

    Ý neo vào đoạn khuyết hoặc đoạn hoạt động lớp thì GIỮ LẠI — chúng được gắn cờ
    khi render, chứ không bị xoá, vì nội dung vẫn có thể đúng.
    """
    index = index_by_code(segments)
    kept = [p for p in notebook.points if p.codes and all(c in index for c in p.codes)]
    cleaned = Notebook(session_title=notebook.session_title, points=kept)
    return cleaned, verify(notebook, segments)
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_verify.py -q`
Expected: PASS — 13 passed

- [ ] **Step 5: Chạy toàn bộ test**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest -q`
Expected: PASS — toàn bộ Task 1-3

- [ ] **Step 6: Commit**

```bash
git add codebase/sotay/verify.py codebase/tests/test_verify.py
git commit -m "feat(verify): bo kiem tat dinh cho ma trich dan, doan khuyet, hoat dong lop"
```

---

### Task 4: `llm.py` — lời gọi AI thật (M2) · **MỐC CP3**

Đây là file duy nhất biết tới provider. Task này phải xong **trước CP3**.

**Files:**
- Create: `codebase/sotay/llm.py`
- Create: `codebase/tests/test_llm.py`
- Create: `codebase/scripts/smoke_llm.py`

**Interfaces:**
- Consumes: không (chỉ `anthropic` SDK)
- Produces:
  - `MODEL: str = "claude-opus-5"`
  - `MAX_TOKENS: int = 4096`
  - `complete_json(system: str, user_blocks: list[dict], schema: type[T]) -> T` — trả instance đã validate của `schema`
  - `LlmError(Exception)`

- [ ] **Step 1: Viết test thất bại (không gọi mạng)**

`codebase/tests/test_llm.py`:

```python
"""Test cho llm.py. KHÔNG gọi mạng — chỉ kiểm hợp đồng và cách dựng request."""

import pytest
from sotay import llm


def test_model_is_pinned_to_an_exact_id():
    assert llm.MODEL == "claude-opus-5"


def test_max_tokens_leaves_room_for_five_points():
    assert llm.MAX_TOKENS >= 2048


def test_api_key_is_never_hardcoded():
    source = open(llm.__file__, encoding="utf-8").read()
    assert "sk-ant" not in source
    assert "ANTHROPIC_API_KEY" in source


def test_complete_json_raises_a_typed_error_when_the_key_is_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    from pydantic import BaseModel

    class Tiny(BaseModel):
        x: str

    with pytest.raises(llm.LlmError):
        llm.complete_json("sys", [{"type": "text", "text": "hi"}], Tiny)


def test_build_request_caches_the_long_transcript_block():
    # Transcript ~40k token được gửi lại mỗi lượt eval → phải bật prompt caching.
    blocks = [
        {"type": "text", "text": "TRANSCRIPT DÀI"},
        {"type": "text", "text": "câu hỏi ngắn"},
    ]
    request = llm.build_request("system prompt", blocks, max_tokens=4096)
    assert request["model"] == "claude-opus-5"
    assert request["max_tokens"] == 4096
    cached = [b for b in request["messages"][0]["content"] if "cache_control" in b]
    assert len(cached) == 1
    assert cached[0]["text"] == "TRANSCRIPT DÀI"


def test_build_request_puts_the_volatile_block_after_the_cache_breakpoint():
    blocks = [
        {"type": "text", "text": "TRANSCRIPT DÀI"},
        {"type": "text", "text": "câu hỏi ngắn"},
    ]
    content = llm.build_request("s", blocks, max_tokens=100)["messages"][0]["content"]
    assert "cache_control" in content[0]
    assert "cache_control" not in content[-1]
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_llm.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.llm'`

- [ ] **Step 3: Viết `llm.py`**

`codebase/sotay/llm.py`:

```python
"""Vỏ mỏng quanh Anthropic SDK. Chủ: M2.

ĐÂY LÀ RANH GIỚI PROVIDER DUY NHẤT của prototype. Muốn đổi sang provider khác thì
đổi đúng file này, không file nào khác import SDK.

Dùng structured output (messages.parse + Pydantic) để output luôn parse được.
Bật prompt caching trên khối transcript dài — eval chạy 6 buổi × 3 lượt, nếu không
cache thì trả tiền đọc lại ~40k token mỗi lượt.

Ràng buộc schema: structured output KHÔNG hỗ trợ minItems/maxItems, nên "đúng 5 ý"
phải ép ở verify.py, không ép ở đây.
"""

from __future__ import annotations

import os
from typing import TypeVar

from pydantic import BaseModel

MODEL = "claude-opus-5"
MAX_TOKENS = 4096

# KHÔNG truyền output_config ở đây: messages.parse() tự dựng output_config.format từ
# tham số output_format, nên truyền thêm output_config sẽ đụng nhau. Effort mặc định
# của API đã là "high" — đúng mức mình cần.

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    """Lỗi khi gọi model, kể cả thiếu credential."""


def build_request(system: str, user_blocks: list[dict], max_tokens: int) -> dict:
    """Dựng payload. Tách riêng để test được mà không cần mạng.

    Khối ĐẦU TIÊN trong user_blocks được coi là khối ổn định (transcript) và được
    đánh dấu cache; các khối sau là phần đổi theo lượt, đặt sau điểm cache.
    """
    blocks: list[dict] = []
    for i, block in enumerate(user_blocks):
        block = dict(block)
        if i == 0:
            block["cache_control"] = {"type": "ephemeral"}
        blocks.append(block)

    return {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": blocks}],
    }


def complete_json(system: str, user_blocks: list[dict], schema: type[T]) -> T:
    """Gọi model một lần, trả về instance đã validate của schema."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise LlmError(
            "Chưa có credential. Đặt biến môi trường ANTHROPIC_API_KEY "
            "(hoặc chạy `ant auth login`). Không commit key vào repo."
        )

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise LlmError("Chưa cài SDK: pip install anthropic") from exc

    client = anthropic.Anthropic()
    request = build_request(system, user_blocks, MAX_TOKENS)

    try:
        response = client.messages.parse(output_format=schema, **request)
    except Exception as exc:
        raise LlmError(f"Gọi model thất bại: {exc}") from exc

    if response.stop_reason == "refusal":
        raise LlmError(f"Model từ chối yêu cầu: {response.stop_details}")
    if response.parsed_output is None:
        raise LlmError(f"Model không trả JSON đúng schema (stop_reason={response.stop_reason})")

    return response.parsed_output
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_llm.py -q`
Expected: PASS — 7 passed

- [ ] **Step 5: Viết script smoke test gọi mạng thật**

`codebase/scripts/smoke_llm.py`:

```python
"""Bằng chứng AI chạy thật cho CP3. Chạy tay, không nằm trong pytest.

Cách chạy (Windows):
    set ANTHROPIC_API_KEY=...
    cd codebase && ..\\.venv\\Scripts\\python.exe scripts/smoke_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel

from sotay.llm import complete_json


class Ping(BaseModel):
    answer: str


result = complete_json(
    system="Trả lời cực ngắn bằng tiếng Việt.",
    user_blocks=[{"type": "text", "text": "Một cộng một bằng mấy?"}],
    schema=Ping,
)
print("AI trả về:", result.answer)
```

- [ ] **Step 6: Chạy smoke test — đây là bằng chứng CP3**

Run: `cd codebase && ../.venv/Scripts/python.exe scripts/smoke_llm.py`
Expected: in ra `AI trả về: ...`. Chụp ảnh output này để show tại CP3.

- [ ] **Step 7: Commit**

```bash
git add codebase/sotay/llm.py codebase/tests/test_llm.py codebase/scripts/smoke_llm.py
git commit -m "feat(llm): vo Anthropic SDK voi structured output va prompt caching"
```

---

### Task 5: `generate.py` + prompt — quyết định AI duy nhất (M2)

**Files:**
- Create: `codebase/sotay/prompts.py`
- Create: `codebase/sotay/generate.py`
- Create: `codebase/tests/test_generate.py`

**Interfaces:**
- Consumes: `sotay.ingest.{load_session, content_segments}`, `sotay.registry.resolve`, `sotay.llm.complete_json`, `sotay.models.Notebook`
- Produces:
  - `SYSTEM_PROMPT: str`
  - `format_segments(segments: list[Segment]) -> str`
  - `build_notebook(session_id: str, *, call=llm.complete_json) -> tuple[Notebook, list[Segment]]` — `call` inject được để test không gọi mạng

- [ ] **Step 1: Viết test thất bại**

`codebase/tests/test_generate.py`:

```python
import pytest
from sotay.generate import SYSTEM_PROMPT, build_notebook, format_segments
from sotay.models import KeyPoint, Notebook, Segment
from sotay.registry import SessionNotAvailable


def seg(code, text, has_gap=False, is_activity=False):
    return Segment(code=code, text=text, has_gap=has_gap, is_activity=is_activity)


def test_prompt_forbids_inventing_codes():
    assert "không được bịa" in SYSTEM_PROMPT.lower() or "chỉ dùng mã" in SYSTEM_PROMPT.lower()


def test_prompt_names_the_exact_point_count():
    assert "5" in SYSTEM_PROMPT


def test_prompt_forbids_filling_in_transcript_gaps():
    assert "không nghe rõ" in SYSTEM_PROMPT


def test_prompt_forbids_reversing_the_lecturer_meaning():
    assert "đảo" in SYSTEM_PROMPT.lower() or "ngược" in SYSTEM_PROMPT.lower()


def test_format_segments_labels_each_segment_with_its_code():
    text = format_segments([seg("T03-002", "nội dung A"), seg("T03-004", "nội dung B")])
    assert "[T03-002]" in text
    assert "nội dung A" in text
    assert "[T03-004]" in text


def test_format_segments_marks_gapped_segments_so_the_model_can_see_them():
    text = format_segments([seg("T03-003", "abc [không nghe rõ] def", has_gap=True)])
    assert "T03-003" in text
    assert "[không nghe rõ]" in text


def test_build_notebook_refuses_a_session_with_no_transcript_without_calling_the_model():
    calls = []

    def spy(*args, **kwargs):
        calls.append(1)
        raise AssertionError("không được gọi model cho buổi ngoài phạm vi")

    with pytest.raises(SessionNotAvailable):
        build_notebook("07", call=spy)
    assert calls == []


def test_build_notebook_never_shows_class_activity_notes_to_the_model():
    captured = {}

    def fake_call(system, user_blocks, schema):
        captured["blocks"] = user_blocks
        return Notebook(
            session_title="x",
            points=[KeyPoint(statement="y", codes=["T03-002"])],
        )

    build_notebook("03", call=fake_call)
    sent = "".join(b["text"] for b in captured["blocks"])
    assert "[Hoạt động lớp" not in sent


def test_build_notebook_returns_the_segments_alongside_the_notebook():
    def fake_call(system, user_blocks, schema):
        return Notebook(
            session_title="x", points=[KeyPoint(statement="y", codes=["T03-002"])]
        )

    notebook, segments = build_notebook("03", call=fake_call)
    assert isinstance(notebook, Notebook)
    assert any(s.code == "T03-001" for s in segments), "trả về TẤT CẢ đoạn, kể cả activity, để verify dùng"


def test_build_notebook_sends_the_transcript_as_the_first_cacheable_block():
    captured = {}

    def fake_call(system, user_blocks, schema):
        captured["blocks"] = user_blocks
        return Notebook(
            session_title="x", points=[KeyPoint(statement="y", codes=["T03-002"])]
        )

    build_notebook("03", call=fake_call)
    assert len(captured["blocks"]) >= 2
    assert len(captured["blocks"][0]["text"]) > len(captured["blocks"][-1]["text"])
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_generate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.generate'`

- [ ] **Step 3: Viết `prompts.py`**

`codebase/sotay/prompts.py`:

```python
"""Prompt cho quyết định AI duy nhất. Chủ: M2.

Sửa file này thì phải chạy lại eval và ghi thành một lượt mới — prompt là biến
độc lập của phép đo.
"""

SYSTEM_PROMPT = """\
Bạn là người soạn sổ tay ôn tập cho học viên khoá AI Thực Chiến đã nghỉ hoặc mất \
mạch một buổi học. Đầu vào là transcript lời giảng của buổi đó, mỗi đoạn có một mã \
trích dẫn dạng [Txx-NNN].

Việc của bạn: chọn ra ĐÚNG 5 ý chính của buổi, xếp ý quan trọng nhất trước, và với \
mỗi ý ghi mã đoạn chống lưng cho nó.

Quy tắc bắt buộc:

1. NGUỒN SỰ THẬT. Chỉ dùng mã đoạn xuất hiện trong transcript được cung cấp. Không \
được bịa mã. Mỗi ý phải có tối thiểu một mã, và mã đó phải là đoạn thực sự nói điều \
mà ý của bạn khẳng định. Nếu một ý bạn muốn viết không neo được vào đoạn nào, hãy bỏ \
ý đó và chọn ý khác — đừng gán một mã gần gần.

2. KHÔNG VÁ CHỖ KHUYẾT. Chỗ ghi [không nghe rõ] là chỗ bản ghi bị mất, không phải chỗ \
để bạn suy diễn. Nếu ý chính nằm ở một đoạn có [không nghe rõ], chỉ viết đúng phần \
nghe được; không đoán phần mất.

3. KHÔNG ĐẢO Ý GIẢNG VIÊN. Đây là khoá dạy nghề — học viên hiểu ngược một khái niệm \
là học sai kiến thức nghề. Giữ đúng chiều của câu giảng: ai làm gì, ai KHÔNG làm gì, \
cái nào thuộc cái nào. Nếu giảng viên nói "X không phải là Y" thì tuyệt đối không tóm \
thành "X là Y".

4. Ý CHÍNH LÀ NỘI DUNG HỌC, không phải việc hành chính của lớp (điểm danh, nghỉ giữa \
giờ, chia nhóm, deadline nộp bài).

5. Mỗi ý viết thành MỘT câu tiếng Việt hoàn chỉnh, tự hiểu được mà không cần đọc các ý \
khác. Viết cho người vắng mặt buổi đó: đừng dùng đại từ trỏ về ngữ cảnh họ không có.
"""


def user_instruction(session_title: str) -> str:
    return (
        f"Trên đây là transcript buổi: {session_title}\n\n"
        f"Hãy soạn sổ tay: đúng 5 ý chính, mỗi ý một câu, mỗi ý kèm mã đoạn chống lưng. "
        f"session_title điền đúng tên buổi ở trên."
    )
```

- [ ] **Step 4: Viết `generate.py`**

`codebase/sotay/generate.py`:

```python
"""Quyết định AI duy nhất: chọn 5 ý chính + gắn mã đoạn. Chủ: M2.

Không retrieval — nạp cả buổi vào một lời gọi. Đây chính là điểm khác kiến trúc so
với AI tutor của VLearn: tutor buộc phải retrieve theo đoạn học viên bôi đen, nên nó
không bao giờ thấy được cả buổi.
"""

from __future__ import annotations

from pathlib import Path

from sotay import llm
from sotay.ingest import TRANSCRIPT_DIR, content_segments, load_session
from sotay.models import Notebook, Segment
from sotay.prompts import SYSTEM_PROMPT, user_instruction
from sotay.registry import resolve

__all__ = ["SYSTEM_PROMPT", "format_segments", "build_notebook"]


def format_segments(segments: list[Segment]) -> str:
    """Đánh nhãn mỗi đoạn bằng mã của nó để model trích dẫn được."""
    return "\n\n".join(f"[{s.code}] {s.text}" for s in segments)


def build_notebook(
    session_id: str,
    *,
    call=llm.complete_json,
    data_dir: Path = TRANSCRIPT_DIR,
) -> tuple[Notebook, list[Segment]]:
    """Sinh sổ tay cho một buổi.

    Trả (notebook, TẤT CẢ đoạn của buổi) — verify cần cả đoạn hoạt động lớp trong
    chỉ mục để phát hiện được lỗi cites_activity.

    Raise SessionNotAvailable TRƯỚC khi gọi model nếu buổi không có transcript.
    """
    session_title = resolve(session_id)  # chỗ khó ③ — chặn ở đây, chưa tốn token
    _, segments = load_session(session_id, data_dir)

    lecture_only = content_segments(segments)  # chỗ khó ④ — model không thấy ghi chú lớp
    user_blocks = [
        {"type": "text", "text": format_segments(lecture_only)},
        {"type": "text", "text": user_instruction(session_title)},
    ]

    notebook = call(SYSTEM_PROMPT, user_blocks, Notebook)
    return notebook, segments
```

- [ ] **Step 5: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_generate.py -q`
Expected: PASS — 10 passed

- [ ] **Step 6: Chạy thật một lần trên transcript-03**

```bash
cd codebase && ../.venv/Scripts/python.exe -c "
from sotay.generate import build_notebook
from sotay.verify import verify
nb, segs = build_notebook('03')
for i, p in enumerate(nb.points, 1):
    print(i, p.statement, p.codes)
print('FINDINGS:', verify(nb, segs))
"
```

Expected: 5 ý có mã thật; `FINDINGS: []` hoặc chỉ có `transcript_gap`.

- [ ] **Step 7: Commit**

```bash
git add codebase/sotay/prompts.py codebase/sotay/generate.py codebase/tests/test_generate.py
git commit -m "feat(generate): mot loi goi AI sinh 5 y chinh co ma doan"
```

---

### Task 6: `render.py` — sổ tay 1 trang (M4)

**Files:**
- Create: `codebase/sotay/render.py`
- Create: `codebase/tests/test_render.py`

**Interfaces:**
- Consumes: `sotay.models.{Notebook, Segment, Finding}`, `sotay.verify.gap_codes`
- Produces: `render_markdown(notebook, segments, findings, session_id) -> str`

- [ ] **Step 1: Viết test thất bại**

`codebase/tests/test_render.py`:

```python
from sotay.models import Finding, KeyPoint, Notebook, Segment
from sotay.render import render_markdown


def seg(code, text="nội dung", has_gap=False, is_activity=False):
    return Segment(code=code, text=text, has_gap=has_gap, is_activity=is_activity)


SEGMENTS = [
    seg("T03-002", "Track một là AI Engineer."),
    seg("T03-003", "robot giao hàng [không nghe rõ]", has_gap=True),
]

NOTEBOOK = Notebook(
    session_title="Day 2 chiều — Soi bài toán",
    points=[
        KeyPoint(statement="Khoá có ba track nghề nghiệp.", codes=["T03-002"]),
        KeyPoint(statement="Giảng viên từng làm robot giao hàng.", codes=["T03-003"]),
    ],
)


def test_renders_the_session_title_as_the_heading():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert out.startswith("# ")
    assert "Day 2 chiều" in out


def test_numbers_every_point():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert "1." in out
    assert "2." in out


def test_shows_each_statement():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert "ba track nghề nghiệp" in out


def test_shows_the_citation_code_for_every_point():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert "T03-002" in out
    assert "T03-003" in out


def test_quotes_the_source_segment_so_the_reader_can_check_without_leaving_the_page():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert "Track một là AI Engineer." in out


def test_warns_on_a_point_anchored_to_a_transcript_gap():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert "bản ghi thiếu" in out


def test_does_not_warn_on_a_clean_point():
    single = Notebook(session_title="t", points=[NOTEBOOK.points[0]])
    out = render_markdown(single, SEGMENTS, [], "03")
    assert "bản ghi thiếu" not in out


def test_reports_dropped_points_instead_of_hiding_them():
    findings = [Finding(point_index=0, kind="unknown_code", detail="Ý 1 trích mã T03-999")]
    out = render_markdown(NOTEBOOK, SEGMENTS, findings, "03")
    assert "T03-999" in out


def test_states_the_source_file_so_the_citation_is_traceable():
    out = render_markdown(NOTEBOOK, SEGMENTS, [], "03")
    assert "transcript-03-clean.md" in out
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_render.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.render'`

- [ ] **Step 3: Viết `render.py`**

`codebase/sotay/render.py`:

```python
"""Render sổ tay 1 trang. Chủ: M4.

Nguyên tắc trình bày: người đọc phải kiểm được ngay tại chỗ. Mỗi ý đi kèm mã đoạn
VÀ nguyên văn đoạn đó, nên không cần mở file khác để phán ý có đúng không.
Đây chính là chiều đo "citation support" của quality bar.
"""

from __future__ import annotations

from sotay.ingest import index_by_code
from sotay.models import Finding, Notebook, Segment

GAP_WARNING = "⚠ bản ghi thiếu ở đoạn này — đọc nguyên văn trước khi tin"


def render_markdown(
    notebook: Notebook,
    segments: list[Segment],
    findings: list[Finding],
    session_id: str,
) -> str:
    index = index_by_code(segments)
    lines: list[str] = [
        f"# Sổ tay buổi học — {notebook.session_title}",
        "",
        f"Nguồn: `data/vlearn-pack/transcript/transcript-{session_id}-clean.md` · "
        f"{len(segments)} đoạn · mỗi ý bên dưới trích dẫn mã đoạn để bạn tự kiểm.",
        "",
    ]

    for i, point in enumerate(notebook.points, 1):
        codes = " ".join(f"`[{c}]`" for c in point.codes)
        lines.append(f"## {i}. {point.statement}")
        lines.append("")
        lines.append(f"Trích: {codes}")
        lines.append("")
        for code in point.codes:
            segment = index.get(code)
            if segment is None:
                continue
            if segment.has_gap:
                lines.append(f"> {GAP_WARNING}")
                lines.append(">")
            lines.append(f"> **[{code}]** {segment.text}")
            lines.append("")

    dropped = [f for f in findings if f.kind in ("unknown_code", "no_codes", "cites_activity")]
    if dropped:
        lines.append("---")
        lines.append("")
        lines.append("## Ý đã bị bộ kiểm loại")
        lines.append("")
        lines.append("Ghi lại để minh bạch, không giấu:")
        lines.append("")
        for finding in dropped:
            lines.append(f"- `{finding.kind}` — {finding.detail}")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_render.py -q`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add codebase/sotay/render.py codebase/tests/test_render.py
git commit -m "feat(render): so tay 1 trang co ma doan va nguyen van de tu kiem"
```

---

### Task 7: `cli.py` — chạy được đầu-cuối (M4)

**Files:**
- Create: `codebase/sotay/cli.py`
- Create: `codebase/sotay/__main__.py`
- Create: `codebase/tests/test_cli.py`

**Interfaces:**
- Consumes: `sotay.generate.build_notebook`, `sotay.verify.drop_invalid`, `sotay.render.render_markdown`, `sotay.registry.SessionNotAvailable`
- Produces: `main(argv: list[str] | None = None) -> int` — 0 = thành công, 2 = buổi ngoài phạm vi, 1 = lỗi khác

- [ ] **Step 1: Viết test thất bại**

`codebase/tests/test_cli.py`:

```python
from sotay.cli import main
from sotay.models import KeyPoint, Notebook


def fake_build(session_id, **kwargs):
    from sotay.ingest import load_session

    _, segments = load_session(session_id)
    return (
        Notebook(
            session_title="Buổi test",
            points=[KeyPoint(statement=f"Ý {i}", codes=["T03-002"]) for i in range(1, 6)],
        ),
        segments,
    )


def test_writes_the_notebook_to_the_requested_path(tmp_path, monkeypatch):
    monkeypatch.setattr("sotay.cli.build_notebook", fake_build)
    out = tmp_path / "sotay-03.md"
    assert main(["build", "03", "--out", str(out)]) == 0
    assert "Sổ tay buổi học" in out.read_text(encoding="utf-8")


def test_refuses_an_out_of_scope_session_with_exit_code_2(capsys):
    assert main(["build", "07"]) == 2
    printed = capsys.readouterr().out
    assert "không có transcript" in printed


def test_refusal_lists_the_available_sessions(capsys):
    main(["build", "07"])
    printed = capsys.readouterr().out
    assert "Buổi 03" in printed


def test_default_output_path_is_derived_from_the_session_id(tmp_path, monkeypatch):
    monkeypatch.setattr("sotay.cli.build_notebook", fake_build)
    monkeypatch.chdir(tmp_path)
    assert main(["build", "03"]) == 0
    assert (tmp_path / "out" / "sotay-03.md").exists()
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotay.cli'`

- [ ] **Step 3: Viết `cli.py`**

`codebase/sotay/cli.py`:

```python
"""Giao diện dòng lệnh. Chủ: M4.

    python -m sotay build 03
    python -m sotay build 03 --out out/sotay-03.md
    python -m sotay build 07        # thử ca ngoài phạm vi
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sotay.generate import build_notebook
from sotay.llm import LlmError
from sotay.registry import SessionNotAvailable
from sotay.render import render_markdown
from sotay.verify import drop_invalid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sotay", description="Sinh sổ tay buổi học.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Sinh sổ tay cho một buổi.")
    build.add_argument("session_id", help="Mã buổi, ví dụ 03")
    build.add_argument("--out", default=None, help="Đường dẫn file ra")
    args = parser.parse_args(argv)

    try:
        notebook, segments = build_notebook(args.session_id)
    except SessionNotAvailable as exc:
        print(exc.message)
        return 2
    except LlmError as exc:
        print(f"Lỗi gọi model: {exc}")
        return 1

    cleaned, findings = drop_invalid(notebook, segments)
    markdown = render_markdown(cleaned, segments, findings, args.session_id)

    out_path = Path(args.out) if args.out else Path("out") / f"sotay-{args.session_id}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    print(f"Đã ghi {out_path} — {len(cleaned.points)} ý, {len(findings)} phát hiện.")
    for finding in findings:
        print(f"  [{finding.kind}] {finding.detail}")
    return 0
```

- [ ] **Step 4: Viết `__main__.py`**

`codebase/sotay/__main__.py`:

```python
import sys

from sotay.cli import main

sys.exit(main())
```

- [ ] **Step 5: Chạy test để xác nhận nó pass**

Run: `cd codebase && ../.venv/Scripts/python.exe -m pytest tests/test_cli.py -q`
Expected: PASS — 4 passed

- [ ] **Step 6: Chạy thật đầu-cuối cả hai đường**

```bash
cd codebase && ../.venv/Scripts/python.exe -m sotay build 03
cd codebase && ../.venv/Scripts/python.exe -m sotay build 07
```

Expected: lệnh đầu ghi `out/sotay-03.md`; lệnh sau in câu từ chối + 6 buổi, exit 2.

- [ ] **Step 7: Commit**

```bash
git add codebase/sotay/cli.py codebase/sotay/__main__.py codebase/tests/test_cli.py
git commit -m "feat(cli): python -m sotay build chay dau-cuoi"
```

---

### Task 8: `eval/mining/count_evidence.py` — sinh lại §2.1 (M3)

Tiêu chí #2 đòi "phương pháp đếm kiểm lại được". Script này là hiện thực của yêu cầu đó.

**Files:**
- Create: `eval/mining/count_evidence.py`
- Create: `eval/mining/README.md`

**Interfaces:**
- Consumes: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv`
- Produces: bảng markdown in ra stdout, khớp từng số với spec §2.1

- [ ] **Step 1: Viết script**

`eval/mining/count_evidence.py`:

```python
"""Sinh lại mọi con số ở spec.md §2.1. Chủ: M3.

Chạy:  PYTHONUTF8=1 .venv/Scripts/python.exe eval/mining/count_evidence.py

Mọi số trong spec §2.1 phải khớp output của script này. Nếu lệch, sửa spec theo
script, không sửa script theo spec.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "vlearn-pack"
    / "chatlog"
    / "chat_history_anonymized_for_hackathon.csv"
)

# Lớp bọc do nền tảng thêm vào khi học viên bôi đen slide. Bỏ đi để chỉ đếm phần
# học viên tự gõ — nếu không sẽ đếm lẫn chữ trên slide.
WRAPPER = re.compile(r'^\(trang \d+, đoạn được chọn: ".*?"\)\s*', re.DOTALL)

SUMMARY_VERB = r"(tóm tắt|tóm lược|tổng hợp|tổng kết|summary)"
SESSION_SCOPE = r"(toàn bộ|tất cả|cả buổi|cả bài|cả slide|cả ngày|buổi học|bài giảng|hôm nay|\.pdf|day ?0?\d|slide)"
SESSION_LEVEL = [
    re.compile(SUMMARY_VERB + r".{0,40}" + SESSION_SCOPE, re.DOTALL),
    re.compile(SESSION_SCOPE + r".{0,40}" + SUMMARY_VERB, re.DOTALL),
]

REFUSAL_CUES = [
    "rất tiếc", "xin lỗi", "không tìm thấy", "không thể truy cập",
    "không thể truy xuất", "không có dữ liệu", "không được hiển thị",
    "không khớp", "không bao gồm", "không hiển thị", "hệ thống không",
    "không đề cập",
]


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def student_ask(content: str) -> str:
    """Phần học viên tự gõ, đã bỏ lớp bọc của nền tảng."""
    return WRAPPER.sub("", normalise(content))


def is_session_level(ask: str) -> bool:
    return any(pattern.search(ask) for pattern in SESSION_LEVEL)


def is_refusal(answer: str) -> bool:
    lowered = normalise(answer)
    return any(cue in lowered for cue in REFUSAL_CUES)


def vn_hour(timestamp: str) -> int:
    return (dt.datetime.fromisoformat(timestamp.replace("Z", "")).hour + 7) % 24


def main() -> int:
    if not CSV_PATH.exists():
        print(f"Không thấy chatlog tại {CSV_PATH} — cần data pack để chạy.")
        return 1

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    by_turn: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in rows:
        by_turn[row["turn_id"]][row["role"]] = row
    turns = [t for t in by_turn.values() if "student" in t and "tutor" in t]

    total = len(turns)
    refused = [t for t in turns if is_refusal(t["tutor"]["content"])]
    session_turns = [t for t in turns if is_session_level(student_ask(t["student"]["content"]))]
    session_refused = [t for t in session_turns if is_refusal(t["tutor"]["content"])]

    downvotes = [t for t in turns if t["tutor"].get("rating") == "down"]
    down_summary_refused = [
        t
        for t in downvotes
        if re.search(SUMMARY_VERB, student_ask(t["student"]["content"]))
        and is_refusal(t["tutor"]["content"])
    ]

    depth = collections.Counter(t["student"]["conversation_id"] for t in turns)
    one_turn = [cid for cid, n in depth.items() if n == 1]
    off_hours = [t for t in turns if vn_hour(t["student"]["message_created_at"]) >= 19
                 or vn_hour(t["student"]["message_created_at"]) < 7]

    def pct(part: int, whole: int) -> str:
        return f"{100 * part / whole:.1f}%" if whole else "n/a"

    print("| Chỉ số | Giá trị |")
    print("|---|---|")
    print(f"| Tổng lượt hỏi-đáp | {total} |")
    print(f"| Học viên riêng biệt | {len({t['student']['user_id'] for t in turns})} |")
    print(f"| Hội thoại riêng biệt | {len(depth)} |")
    print(f"| Tutor bó tay (mức nền) | {len(refused)}/{total} = {pct(len(refused), total)} |")
    print(f"| Lượt xin tóm tắt CẤP BUỔI | {len(session_turns)} |")
    print(f"| — học viên riêng biệt | {len({t['student']['user_id'] for t in session_turns})} |")
    print(f"| — hội thoại riêng biệt | {len({t['student']['conversation_id'] for t in session_turns})} |")
    print(
        f"| — tutor bó tay | {len(session_refused)}/{len(session_turns)} = "
        f"{pct(len(session_refused), len(session_turns))} |"
    )
    print(f"| Tổng downvote | {len(downvotes)} |")
    print(
        f"| Downvote là xin-tóm-tắt-bị-từ-chối | {len(down_summary_refused)}/{len(downvotes)} = "
        f"{pct(len(down_summary_refused), len(downvotes))} |"
    )
    print(f"| Hội thoại chết sau 1 lượt | {len(one_turn)}/{len(depth)} = {pct(len(one_turn), len(depth))} |")
    print(f"| Lượt ngoài giờ lớp (19h-7h) | {len(off_hours)}/{total} = {pct(len(off_hours), total)} |")
    print()
    print("Mã lượt downvote trích dẫn được:")
    print(", ".join(sorted(t["student"]["turn_id"] for t in down_summary_refused)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Chạy script**

Run: `cd "d:/Batch03-2A202601875-HoangAnhQuan" && PYTHONUTF8=1 .venv/Scripts/python.exe eval/mining/count_evidence.py`
Expected: bảng có `Lượt xin tóm tắt CẤP BUỔI | 92`, `tutor bó tay | 60/92 = 65.2%`, `Tổng downvote | 37`, `7/37 = 18.9%`.

- [ ] **Step 3: Đối chiếu từng số với spec §2.1**

Nếu bất kỳ số nào lệch: **sửa spec theo script**, không sửa script theo spec. Ghi lại chỗ đã sửa.

- [ ] **Step 4: Viết `eval/mining/README.md`**

```markdown
# Mining evidence — cách kiểm lại

Mọi con số ở `spec.md` §2.1 sinh ra từ `count_evidence.py`. Cách kiểm lại:

    PYTHONUTF8=1 .venv/Scripts/python.exe eval/mining/count_evidence.py

Ba quyết định đếm đáng lưu ý:

1. **Bỏ lớp bọc của nền tảng.** Câu học viên trong CSV bị nền tảng bọc thành
   `(Trang N, đoạn được chọn: "...")` + câu thật. Chúng tôi bỏ lớp bọc để không
   đếm lẫn chữ trên slide thành câu hỏi của học viên.
2. **"Cấp buổi" là gì.** Chỉ tính lượt vừa có động từ tóm tắt vừa có phạm vi cấp
   buổi trong cùng một câu (cửa sổ 40 ký tự, hai chiều). Lượt xin tóm tắt một đoạn
   không tính — tutor làm được việc đó.
3. **"Bó tay" là gì.** 12 cụm từ chối, liệt kê trong `REFUSAL_CUES`. Đây là heuristic
   trên câu trả lời, không phải nhãn của hệ thống — nên chúng tôi công bố danh sách
   để người khác kiểm lại hoặc phản biện.
```

- [ ] **Step 5: Commit**

```bash
git add eval/mining/
git commit -m "feat(eval): script dem lai toan bo so lieu bang chung"
```

---

### Task 9: Golden set 20 case (M5 gán nhãn, M3 mã hoá)

**Files:**
- Create: `eval/golden/G-{01..06}-01.json` (6 file `key_point`, mỗi file 3 ý vàng)
- Create: `eval/golden/G-OUT-01.json` (ca ③)
- Create: `eval/golden/G-GAP-01.json` (ca ②)
- Create: `eval/golden/README.md`

**Interfaces:**
- Consumes: transcript thật
- Produces: 20 case; schema JSON dùng bởi `eval/harness.py` (Task 10)

- [ ] **Step 1: M5 — gán nhãn ý vàng cho 6 buổi**

Với mỗi buổi, M5 đọc transcript và viết ra **3 ý vàng**: ý mà một học viên nghỉ buổi đó *bắt buộc* phải nắm. Với mỗi ý ghi:
- `expected_codes` — mã đoạn nói điều đó (1-3 mã)
- `must_include_any` — 3-5 từ khoá mà bất kỳ cách diễn đạt đúng nào cũng phải chứa ít nhất một

Không cần code. Đây là việc phán đoán của người đọc.

- [ ] **Step 2: M3 — mã hoá thành JSON**

`eval/golden/G-03-01.json` (mẫu đã điền, dùng làm khuôn cho 5 file còn lại):

```json
{
  "case_id": "G-03-01",
  "session": "03",
  "type": "key_point",
  "source_chatlog_turns": ["T0408", "T0443"],
  "golden_points": [
    {
      "id": "gp1",
      "expected_codes": ["T03-014", "T03-015", "T03-016"],
      "must_include_any": ["ba track", "AI Engineer", "MLOps", "AI PM"]
    },
    {
      "id": "gp2",
      "expected_codes": ["T03-017"],
      "must_include_any": ["global view", "local view", "spot out", "không phải người giải quyết"]
    },
    {
      "id": "gp3",
      "expected_codes": ["T03-021"],
      "must_include_any": ["bài toán nào", "dùng AI", "AI agent", "LLM"]
    }
  ]
}
```

- [ ] **Step 3: M3 — ca ③ ngoài phạm vi**

`eval/golden/G-OUT-01.json`:

```json
{
  "case_id": "G-OUT-01",
  "session": "07",
  "type": "out_of_scope",
  "expect_refusal": true,
  "must_list_sessions": ["01", "02", "03", "04", "05", "06"]
}
```

- [ ] **Step 4: M3 — ca ② bản ghi khuyết**

`eval/golden/G-GAP-01.json`. Chọn một đoạn khuyết thật trong transcript-03 (có 11 đoạn như vậy) và ghi mã của nó:

```json
{
  "case_id": "G-GAP-01",
  "session": "03",
  "type": "gap",
  "gapped_code": "T03-003",
  "expect_gap_flag": true,
  "note": "Nếu sổ tay trích đoạn này thì render bắt buộc phải in cảnh báo bản ghi thiếu."
}
```

- [ ] **Step 5: Kiểm mọi mã trong golden set đều tồn tại thật**

```bash
cd "d:/Batch03-2A202601875-HoangAnhQuan" && PYTHONUTF8=1 .venv/Scripts/python.exe -c "
import json, glob, sys
sys.path.insert(0, 'codebase')
from sotay.ingest import load_session
index = {}
for sid in ['01','02','03','04','05','06']:
    for s in load_session(sid)[1]:
        index[s.code] = s
bad = []
for path in glob.glob('eval/golden/*.json'):
    case = json.load(open(path, encoding='utf-8'))
    codes = [c for gp in case.get('golden_points', []) for c in gp['expected_codes']]
    if case.get('gapped_code'): codes.append(case['gapped_code'])
    for c in codes:
        if c not in index: bad.append((case['case_id'], c))
print('MÃ KHÔNG TỒN TẠI:', bad if bad else 'không có — sạch')
gp = sum(len(json.load(open(p, encoding='utf-8')).get('golden_points', [])) for p in glob.glob('eval/golden/*.json'))
print('Tổng ý vàng:', gp, '(cần 18)')
print('Tổng case:', len(glob.glob('eval/golden/*.json')), '(cần 8 file = 18 ý vàng + 2 ca đặc biệt = 20 case)')
"
```

Expected: `MÃ KHÔNG TỒN TẠI: không có — sạch`, `Tổng ý vàng: 18`.

- [ ] **Step 6: Viết `eval/golden/README.md`**

```markdown
# Golden set — 20 case

| Loại | Số case | File |
|---|---|---|
| `key_point` — 6 buổi × 3 ý vàng | 18 | `G-01-01.json` … `G-06-01.json` |
| `out_of_scope` — buổi 07 không có transcript | 1 | `G-OUT-01.json` |
| `gap` — ý neo vào đoạn `[không nghe rõ]` | 1 | `G-GAP-01.json` |
| **Tổng** | **20** | |

**Ai gán nhãn:** M5 đọc transcript và chọn ý vàng — đây là phán đoán của người,
không sinh bằng AI. M3 mã hoá thành JSON và chạy.

**Cách khớp recall (tất định, kiểm lại được):** một ý vàng tính là bắt được nếu
tồn tại một ý trong sổ tay mà (a) `codes` giao với `expected_codes`, VÀ (b)
`statement` chứa ít nhất một từ khoá trong `must_include_any`. Hai điều kiện cùng
lúc — chỉ trích đúng đoạn nhưng nói sai nội dung thì không tính là bắt được.

**Không dán nguyên văn dài.** Golden set ghi mã đoạn; ai muốn đọc nguyên văn thì
mở data pack. Đây là yêu cầu bảo mật data của khoá.
```

- [ ] **Step 7: Commit**

```bash
git add eval/golden/
git commit -m "feat(eval): golden set 20 case, 18 y vang + ca ngoai pham vi + ca ban ghi khuyet"
```

---

### Task 10: `eval/harness.py` + 3 lượt chạy (M3)

**Files:**
- Create: `eval/harness.py`
- Create: `eval/results/run-01.md`, `run-02.md`, `run-03.md`

**Interfaces:**
- Consumes: `sotay.generate.build_notebook`, `sotay.verify.{verify, drop_invalid}`, `eval/golden/*.json`
- Produces: `python eval/harness.py --run 01` → ghi `eval/results/run-01.md`

- [ ] **Step 1: Viết `harness.py`**

`eval/harness.py`:

```python
"""Chạy golden set, xuất bảng kết quả. Chủ: M3.

    PYTHONUTF8=1 .venv/Scripts/python.exe eval/harness.py --run 01

Chỉ đo được các chiều TẤT ĐỊNH. Hai chiều cần người phán (citation support,
bịa/đảo ý) được in ra dạng phiếu trống để người ngoài nhóm điền tay.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "codebase"))
sys.stdout.reconfigure(encoding="utf-8")

from sotay.generate import build_notebook  # noqa: E402
from sotay.ingest import index_by_code  # noqa: E402
from sotay.llm import MODEL  # noqa: E402
from sotay.registry import SessionNotAvailable, refusal_message  # noqa: E402
from sotay.verify import verify  # noqa: E402

GOLDEN_DIR = ROOT / "eval" / "golden"
RESULTS_DIR = ROOT / "eval" / "results"


def load_cases() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(GOLDEN_DIR.glob("*.json"))]


def point_matches(point, golden_point) -> bool:
    """Khớp tất định: giao mã VÀ chứa từ khoá. Thiếu một trong hai là không tính."""
    if not set(point.codes) & set(golden_point["expected_codes"]):
        return False
    statement = point.statement.lower()
    return any(kw.lower() in statement for kw in golden_point["must_include_any"])


def prompt_commit() -> str:
    try:
        return subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", "codebase/sotay/prompts.py"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip() or "chưa commit"
    except Exception:
        return "không xác định"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="Số lượt, ví dụ 01")
    args = parser.parse_args()

    cases = load_cases()
    lines: list[str] = [
        f"# Kết quả eval — lượt {args.run}",
        "",
        f"- Thời điểm: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"- Model: `{MODEL}`",
        f"- Commit của prompt: `{prompt_commit()}`",
        f"- Số case: {len(cases)}",
        "",
    ]

    total_codes = valid_codes = 0
    golden_total = golden_hit = 0
    gap_flag_total = gap_flag_ok = 0
    refusal_total = refusal_ok = 0
    all_points: list[tuple[str, int, str, list[str]]] = []

    for case in cases:
        case_id, session = case["case_id"], case["session"]

        if case["type"] == "out_of_scope":
            refusal_total += 1
            try:
                build_notebook(session)
                lines.append(f"- ❌ `{case_id}` — KHÔNG từ chối, đã sinh sổ tay cho buổi {session}")
            except SessionNotAvailable:
                message = refusal_message(session)
                listed = all(sid in message for sid in case["must_list_sessions"])
                refusal_ok += 1 if listed else 0
                lines.append(
                    f"- {'✅' if listed else '⚠'} `{case_id}` — từ chối đúng"
                    f"{'' if listed else ', nhưng không liệt kê đủ buổi có sẵn'}"
                )
            continue

        notebook, segments = build_notebook(session)
        index = index_by_code(segments)
        findings = verify(notebook, segments)

        for i, point in enumerate(notebook.points):
            all_points.append((case_id, i + 1, point.statement, point.codes))
            for code in point.codes:
                total_codes += 1
                valid_codes += 1 if code in index else 0

        if case["type"] == "key_point":
            for golden_point in case["golden_points"]:
                golden_total += 1
                golden_hit += 1 if any(point_matches(p, golden_point) for p in notebook.points) else 0

        if case["type"] == "gap":
            gapped = case["gapped_code"]
            cited = [i for i, p in enumerate(notebook.points) if gapped in p.codes]
            if cited:
                gap_flag_total += len(cited)
                flagged = {f.point_index for f in findings if f.kind == "transcript_gap"}
                gap_flag_ok += sum(1 for i in cited if i in flagged)
                lines.append(f"- `{case_id}` — trích {gapped}, gắn cờ {gap_flag_ok}/{gap_flag_total}")
            else:
                lines.append(f"- `{case_id}` — sổ tay không trích {gapped}, ca này không áp dụng lượt này")

    def ratio(part: int, whole: int) -> str:
        return f"{part}/{whole} = {100 * part / whole:.1f}%" if whole else "n/a"

    lines += [
        "",
        "## Chiều đo tất định",
        "",
        "| Chiều | Kết quả | Ngưỡng | Đạt? |",
        "|---|---|---|---|",
        f"| Citation validity | {ratio(valid_codes, total_codes)} | 100% | "
        f"{'✅' if valid_codes == total_codes else '❌'} |",
        f"| Recall so với ý vàng | {ratio(golden_hit, golden_total)} | ≥11/18 | "
        f"{'✅' if golden_hit >= 11 else '❌'} |",
        f"| Từ chối đúng ca ③ | {ratio(refusal_ok, refusal_total)} | 100% | "
        f"{'✅' if refusal_ok == refusal_total else '❌'} |",
        f"| Cờ bản ghi thiếu | {ratio(gap_flag_ok, gap_flag_total)} | 100% | "
        f"{'✅' if gap_flag_ok == gap_flag_total else '❌'} |",
        "",
        "## Phiếu chấm tay — người NGOÀI NHÓM điền",
        "",
        "Mở mã đoạn trong transcript, đọc, rồi phán. Không xem golden set trước khi chấm.",
        "",
        "| Case | Ý | Nội dung ý | Mã trích | Đoạn có chống lưng ý này? (có/không) | Có đảo ý / bịa? (có/không) |",
        "|---|---|---|---|---|---|",
    ]
    for case_id, idx, statement, codes in all_points:
        lines.append(f"| {case_id} | {idx} | {statement} | {' '.join(codes)} | | |")

    lines += [
        "",
        f"Tổng số ý cần chấm tay: **{len(all_points)}**. "
        f"Ngưỡng: citation support ≥27/30 · bịa/đảo ý 0/30.",
        "",
        "## Kết luận",
        "",
        "_(M3 điền sau khi có phiếu chấm tay. Ghi trung thực kể cả khi không đạt bar.)_",
        "",
    ]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"run-{args.run}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {out}")
    print(f"Citation validity {ratio(valid_codes, total_codes)} · Recall {ratio(golden_hit, golden_total)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Chạy lượt 01**

Run: `cd "d:/Batch03-2A202601875-HoangAnhQuan" && PYTHONUTF8=1 .venv/Scripts/python.exe eval/harness.py --run 01`
Expected: ghi `eval/results/run-01.md` với bảng 4 chiều tất định + phiếu chấm tay 30 dòng.

- [ ] **Step 3: Lấy phiếu chấm tay lượt 01**

M3 đưa phiếu trong `run-01.md` cho **≥1 người ngoài nhóm**. Người đó mở mã đoạn trong transcript, điền hai cột cuối. M3 tổng hợp vào mục "Kết luận".

- [ ] **Step 4: M2 chỉnh prompt dựa trên lượt 01, chạy lượt 02**

Chỉ sửa `prompts.py`. Commit riêng để `prompt_commit()` bắt được. Rồi:

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe eval/harness.py --run 02`

- [ ] **Step 5: Chạy lượt 03**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe eval/harness.py --run 03`

- [ ] **Step 6: Ghi trung thực cả ba lượt**

Cả ba file `run-01.md`, `run-02.md`, `run-03.md` phải còn trong repo, **kể cả lượt kém nhất**. Rubric tính đủ điểm cho kết quả không đạt nếu ghi thật; số bị chỉnh hoặc lượt bị xoá thì không được tính.

- [ ] **Step 7: Commit**

```bash
git add eval/harness.py eval/results/
git commit -m "feat(eval): harness 6 chieu do + 3 luot chay ghi trung thuc"
```

---

### Task 11: Khảo sát 20 người + validation ≥3 người (M5)

Không code. Đây là khối R1 (15đ) + R6 (8đ).

**Files:**
- Create: `validation/khao-sat.md`
- Create: `validation/feedback-log.md`

**Interfaces:**
- Consumes: `spec.md` §2.2 (bộ 4 câu hỏi đã chốt)
- Produces: bằng chứng đường (A) cho persona; ≥3 người thật đã thử prototype

- [ ] **Step 1: Khảo sát ≥20 người ngoài nhóm**

Dùng đúng 4 câu ở spec §2.2, **không đổi cách hỏi giữa các người** — đổi câu hỏi thì mất tính so sánh được.

- [ ] **Step 2: Log toàn bộ vào `validation/khao-sat.md`**

Khuôn:

```markdown
# Khảo sát persona — 20 người ngoài nhóm

**Bộ câu hỏi (không đổi giữa các người trả lời):**
1. Bạn từng nghỉ, vào muộn, hoặc mất mạch giữa một buổi của khoá này chưa? (có/không)
2. Nếu có: lúc đó bạn làm gì để nắm lại nội dung buổi? (ghi nguyên văn)
3. Bạn mất khoảng bao lâu cho việc đó? (phút)
4. Nếu có sẵn sổ tay 1 trang gồm 5 ý chính của buổi, mỗi ý bấm được về nguyên văn
   lời giảng, bạn có dùng không? (có/không/tuỳ)

**Tiêu chí đạt:** ≥20 người trả lời, ≥50% trả lời "có" ở câu 1.

| # | Mã HV | Q1 | Q2 (nguyên văn) | Q3 (phút) | Q4 |
|---|---|---|---|---|---|
| 1 | | | | | |

**Tổng hợp:** N người trả lời · X% có ở Q1 · trung vị Q3 = Y phút · Z% có ở Q4

**Kết luận:** _(đạt / không đạt tiêu chí #2 đường A, ghi thật)_
```

- [ ] **Step 3: Ghi rõ nếu khảo sát KHÔNG đạt ngưỡng**

Nếu <50% trả lời "có" ở Q1: **ghi thật vào spec** rằng persona "nghỉ buổi" không được khảo sát chống lưng, và chuyển persona chính sang "ôn lại sau buổi" (có 10,2% lượt ngoài giờ lớp chống lưng). Không sửa số khảo sát.

- [ ] **Step 4: Validation — ≥3 người thật thử prototype**

Mỗi người: cho họ `out/sotay-03.md`, hỏi buổi họ từng nghỉ, xem họ dùng thế nào.

- [ ] **Step 5: Log vào `validation/feedback-log.md`**

```markdown
# Feedback log — người thật thử prototype

| # | Tên | Mã HV | Buổi từng nghỉ | Sổ tay giúp được không | Câu nói nguyên văn | Bỏ ở bước nào |
|---|---|---|---|---|---|---|
| 1 | | | | | | |

**Ba thứ sửa được ngay từ feedback:**
1.
2.
3.

**Ba thứ ghi nhận nhưng không sửa trong sự kiện (kèm lý do):**
1.
2.
3.
```

- [ ] **Step 6: Commit**

```bash
git add validation/
git commit -m "docs(validation): khao sat 20 nguoi + feedback 3 nguoi thu prototype"
```

---

### Task 12: `spec.md` + `README.md` (M5)

**Files:**
- Create: `spec.md` (theo `03-template-ai-spec.md`)
- Create: `README.md` (ghi đè file có sẵn của package đề bài trong repo nhóm)

**Interfaces:**
- Consumes: design doc, `eval/mining/` output, `eval/results/`, `validation/`
- Produces: deliverable trung tâm, **hạn cứng 23:59 ngày 1**

- [ ] **Step 1: Đọc template**

Run: `cat 03-template-ai-spec.md`

- [ ] **Step 2: Viết `spec.md` theo template, kéo nội dung từ design doc**

Ánh xạ: design §1 → spec §4 (lát cắt) · §2 → spec §1-§2 (bằng chứng + impact) · §3 → spec §3 (khác gì công cụ có sẵn) · §5-§6 → spec §5-§6 (chỗ khó + rủi ro) · §7 → spec §7 (kiểm thử).

**Mọi số ở spec §1-§2 phải là output của `eval/mining/count_evidence.py`.** Không gõ tay số.

- [ ] **Step 3: Chốt quality bar trong spec, đánh dấu là không đổi**

Copy nguyên bảng §7.1 của design doc vào spec, kèm câu: *"Quality bar chốt tại đây lúc 23:59 ngày 1 và giữ nguyên sau đó."*

- [ ] **Step 4: Viết `README.md` với bảng phân công có tên**

```markdown
# Sổ tay buổi học có trích dẫn transcript

Nhóm ... — Batch 03 AI Product Hackathon — Hướng C (Làn mở)

## Thành viên và phân công

| Mã HV | Tên | Vai | Sở hữu file |
|---|---|---|---|
| | | M1 · Pipeline & Bộ kiểm | `sotay/models.py`, `ingest.py`, `registry.py`, `verify.py` |
| | | M2 · AI Engineer | `sotay/llm.py`, `generate.py`, `prompts.py` |
| | | M3 · Eval Engineer | `eval/harness.py`, `eval/mining/`, `eval/results/` |
| | | M4 · Interface & Demo | `sotay/render.py`, `cli.py`, `demo-slides.pdf` |
| | | M5 · Product & Research | khảo sát, `eval/golden/` (gán nhãn), `spec.md`, `validation/` |

## Chạy thử

    python -m pip install anthropic pydantic pytest
    set ANTHROPIC_API_KEY=...
    cd codebase && python -m pytest -q
    cd codebase && python -m sotay build 03      # sinh sổ tay
    cd codebase && python -m sotay build 07      # thử ca ngoài phạm vi

## Prototype level

**Working** — chạy thật đầu-cuối trên transcript thật, 1 lời gọi AI thật, không có
phần mock. Không có UI web, không deploy — output là file markdown 1 trang.

## Data

`data/` KHÔNG nằm trong repo này theo quy định bảo mật data của khoá. Trích dẫn
trong `eval/golden/` dùng mã đoạn `[Txx-NNN]`, không dán nguyên văn dài.
```

- [ ] **Step 5: Kiểm cấu trúc repo khớp design §13**

```bash
cd "d:/Batch03-2A202601875-HoangAnhQuan" && ls README.md spec.md codebase eval validation reflection 2>&1
```

Expected: mọi mục tồn tại. `reflection/` cần 5 file, mỗi người 1.

- [ ] **Step 6: Commit trước hạn 23:59 N1**

```bash
git add README.md spec.md
git commit -m "docs: AI spec + README voi phan cong co ten"
```

---

### Task 13: Demo (M4)

**Files:**
- Create: `demo-slides.pdf` (6 trang, theo `02-guide.md` §5.1)
- Create: `docs/demo-script.md`

**Interfaces:**
- Consumes: `out/sotay-03.md`, `eval/results/run-03.md`, `validation/feedback-log.md`
- Produces: demo 5 phút chạy được

- [ ] **Step 1: Viết kịch bản demo**

`docs/demo-script.md`:

```markdown
# Kịch bản demo — 5 phút

| Phút | Làm gì | Nói gì |
|---|---|---|
| 0:00-0:45 | Chiếu số 65,2% vs 26,8% | 72 học viên xin tóm tắt cả buổi, 2/3 số lần tutor xin lỗi. Không phải vì nó sinh câu trả lời kém — vì nó là RAG theo đoạn được bôi đen, nó không có đường thấy cả buổi |
| 0:45-1:30 | `python -m sotay build 03` | Không retrieval. Nạp cả 154 đoạn vào một lời gọi. Đây là chỗ khác kiến trúc |
| 1:30-2:45 | Mở `out/sotay-03.md`, đọc ý 1, bấm mã đoạn | Mỗi ý gắn mã đoạn. Mở transcript ra là kiểm được. Người ngoài nhóm kiểm lại là ra cùng kết luận |
| 2:45-3:15 | Chỉ vào ý có cảnh báo bản ghi thiếu | 103 chỗ [không nghe rõ] trong corpus. Chỗ nào bản ghi khuyết thì nói rõ khuyết, không vá bằng suy diễn |
| 3:15-3:45 | `python -m sotay build 07` | Không có transcript buổi 7 thì từ chối và nói rõ có buổi nào. Chặn trước khi gọi AI — không có đường để nó bịa |
| 3:45-4:30 | Chiếu `run-03.md` | Citation validity, recall, và số thật của phiếu chấm tay do người ngoài nhóm điền |
| 4:30-5:00 | Chiếu feedback log | 3 người thật đã thử. Câu họ nói. Chỗ họ bỏ |
```

- [ ] **Step 2: Làm 6 trang slide**

1. Pain + số (65,2% vs 26,8%, 72 học viên)
2. Lát cắt một câu
3. Khác gì NotebookLM — 3 điểm ở design §3
4. Kiến trúc 3 tầng + chỗ 1 lời gọi AI
5. 4 lớp chỗ khó, mỗi lớp một dòng + ca ④ `T03-017` nguyên văn
6. Kết quả eval 3 lượt + validation

- [ ] **Step 3: Dry run — bấm giờ thật, 2 lần**

Chạy lệnh thật, không chiếu ảnh chụp. Nếu quá 5 phút, cắt phút 3:45-4:30 xuống còn 30 giây.

- [ ] **Step 4: Chuẩn bị đường lùi nếu mạng chết tại CP6**

Lưu sẵn `out/sotay-03.md` đã sinh + ảnh chụp output của `build 07`. Nói rõ với người chấm rằng đây là bản đã sinh trước, kèm log lượt chạy.

- [ ] **Step 5: Commit**

```bash
git add demo-slides.pdf docs/demo-script.md
git commit -m "docs(demo): slide 6 trang + kich ban demo 5 phut"
```

---

## Self-review của plan

**Spec coverage — đối chiếu từng mục design với task:**

| Design § | Task |
|---|---|
| §1 lát cắt | 5 (quyết định AI), 7 (chạy đầu-cuối) |
| §2.1 mining | 8 |
| §2.2 khảo sát | 11 |
| §2.3 impact | 12 (viết vào spec) |
| §3 khác gì NotebookLM | 2 + 3 (mã đoạn + từ chối), 13 (trình bày) |
| §4 kiến trúc | 1-7 |
| §5 ① nguồn sự thật | 3 (`verify`), 5 (prompt) |
| §5 ② bản ghi khuyết | 1 (`has_gap`), 3 (cờ), 6 (render cảnh báo) |
| §5 ③ ngoài phạm vi | 2 |
| §5 ④ đặc thù domain | 1 (`is_activity`), 3 (`cites_activity`), 9 (ca đảo ý trong golden) |
| §6 rủi ro | 4 (mốc CP3), 10 (ghi trung thực), 12 (phân công vibe-coding) |
| §7.1 quality bar | 10 |
| §7.2 golden set | 9 |
| §7.3 ba lượt | 10 |
| §8 validation | 11 |
| §9 prototype level | 7, 12 |
| §11 phân công | 12 |
| §13 cấu trúc repo | 12 |

Không có mục design nào thiếu task.

**Placeholder scan:** không có TBD/TODO. Ba chỗ cố ý để trống là **dữ liệu người phải điền**, không phải code thiếu: bảng khảo sát (Task 11), phiếu chấm tay (Task 10 Step 3), tên/mã HV thành viên (Task 12).

**Type consistency:** `Segment`/`KeyPoint`/`Notebook`/`Finding` định nghĩa một lần ở Task 1 và dùng nguyên tên ở Task 3, 5, 6, 7, 10. `index_by_code` khai ở Task 1 Step 4, dùng ở Task 3 và 6 và 10. `build_notebook` trả `tuple[Notebook, list[Segment]]` ở Task 5, mọi caller (Task 7, 10) unpack đúng 2 giá trị. `complete_json(system, user_blocks, schema)` ở Task 4 khớp cách gọi `call(SYSTEM_PROMPT, user_blocks, Notebook)` ở Task 5 và signature `fake_call(system, user_blocks, schema)` trong test.
