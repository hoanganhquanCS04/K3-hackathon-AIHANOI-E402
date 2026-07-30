r"""6 file transcript .md → list[Seg]. Chủ: M1 (khối B).

BẢN MỞ RỘNG của sotay/ingest.py, thêm section + giọng nói + độ tin cậy định vị.

Ba chỗ dễ sai, mỗi chỗ có test riêng:

1. BIÊN ĐOẠN. Đoạn kết thúc ở mã kế tiếp HOẶC dòng "## " HOẶC hết file. Bỏ nhánh
   "## " ra là đoạn cuối mỗi section sẽ hút luôn tiêu đề section sau vào thân nó
   (~90 đoạn trên toàn corpus). Đây đúng là bug đang có ở sotay/ingest.py.
2. FRONT MATTER. Các dòng "> " đầu file CHỨA "[không nghe rõ]" như chú giải. Không
   loại chúng thì đếm chỗ khuyết sai.
3. MARKER GIỌNG NÓI CÓ HAI DẠNG: "[Học viên]:" trần (51 đoạn) và "**[Học viên]:**"
   in đậm (18 đoạn) — tổng 69. Regex phải là ^\*{0,2}\[Học viên\]; bỏ \*{0,2} là
   mất 18 đoạn và gán nhầm lời học viên thành lời giảng viên. Và PHÂN BIỆT HOA
   THƯỜNG: "[học viên]" chữ thường là tên đã ẩn danh (59 chỗ), không phải marker.
4. VÙNG TRƯỚC HEADING ĐẦU TIÊN không rỗng. T02-001 và T05-001 nằm ở đó. Duyệt
   theo section mà bỏ vùng này là mất 2 đoạn: tổng ra 698/53 thay vì 700/55.
   Chúng nhận section_idx = 0.
"""

from __future__ import annotations

import re
from pathlib import Path

from flow1.models import Seg

TRANSCRIPT_DIR = Path(__file__).resolve().parents[3] / "data" / "vlearn-pack" / "transcript"
SESSIONS: tuple[str, ...] = ("01", "02", "03", "04", "05", "06")

GAP_MARKER = "[không nghe rõ]"
ACTIVITY_PREFIX = "[Hoạt động lớp"
STUDENT_MARKER = "[Học viên]"     # PHÂN BIỆT HOA/THƯỜNG — xem docstring
PRELUDE_TITLE = "(mở đầu buổi)"   # section_idx 0 — vùng trước heading `##` đầu tiên
# Khớp cả "[Học viên]:" trần lẫn "**[Học viên]:**" in đậm ở ĐẦU đoạn. Dựng từ
# STUDENT_MARKER (re.escape) để chỉ có MỘT nguồn sự thật cho chuỗi marker.
_STUDENT_START_RE = re.compile(r"^\*{0,2}" + re.escape(STUDENT_MARKER))

_TITLE_RE = re.compile(r"^#\s*Transcript bài giảng \(bản sạch\)\s*—\s*(.+?)\s*$", re.MULTILINE)
_CONF_RE = re.compile(r"độ tin cậy:\s*([^\s(]+)")
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_SEGMENT_RE = re.compile(
    r"\*\*\[(T\d{2}-\d{3})\]\*\*(.*?)(?=\*\*\[T\d{2}-\d{3}\]\*\*|\n##\s|\Z)",
    re.DOTALL,
)


def _split_front_matter(text: str) -> tuple[str, str]:
    """Trả (front matter, phần còn lại đã bỏ front matter).

    Front matter = các dòng bắt đầu bằng "> " NẰM TRƯỚC heading đầu tiên. Chỉ cắt
    trong vùng đó để không lỡ ăn mất nội dung nào ở giữa file.
    """
    head, sep, rest = text.partition("\n## ")
    lines = head.split("\n")
    front = "\n".join(line for line in lines if line.startswith("> "))
    kept = "\n".join(line for line in lines if not line.startswith("> "))
    return front, kept + (sep + rest if sep else "")


def _sections(body: str) -> list[tuple[int, str, str]]:
    """[(section_idx, section_title, text)], 1-based theo heading.

    Mục 0 là vùng NẰM TRƯỚC heading `##` đầu tiên. Vùng đó không rỗng trên data
    thật: `T02-001` và `T05-001` nằm ở đó. Bỏ nó đi là mất 2 đoạn và tổng tụt
    xuống 698/53 thay vì 700/55.
    """
    headings = list(_HEADING_RE.finditer(body))
    first = headings[0].start() if headings else len(body)

    out: list[tuple[int, str, str]] = [(0, PRELUDE_TITLE, body[:first])]
    for idx, heading in enumerate(headings, start=1):
        start = heading.end()
        end = headings[idx].start() if idx < len(headings) else len(body)
        out.append((idx, heading.group(1).strip(), body[start:end]))
    return out


def parse_text(text: str, session_id: str) -> list[Seg]:
    """Parse nội dung một file transcript. `session_id` dạng "03"."""
    text = text.replace("\r\n", "\n")

    title_match = _TITLE_RE.search(text)
    session_title = title_match.group(1) if title_match else "Buổi học không rõ tên"

    front, body = _split_front_matter(text)
    conf_match = _CONF_RE.search(front)
    locate_confidence = conf_match.group(1) if conf_match else "—"

    segs: list[Seg] = []
    order = 0

    for idx, section_title, chunk_text in _sections(body):
        for code, raw in _SEGMENT_RE.findall(chunk_text):
            content = raw.strip()
            order += 1
            segs.append(
                Seg(
                    code=code,
                    session=session_id,
                    session_title=session_title,
                    locate_confidence=locate_confidence,
                    section_idx=idx,
                    section_title=section_title,
                    order=order,
                    text=content,
                    speaker="student" if _STUDENT_START_RE.match(content) else "instructor",
                    has_gap=GAP_MARKER in content,
                    is_activity=content.startswith(ACTIVITY_PREFIX),
                    n_chars=len(content),
                )
            )

    return segs


def parse_session(session_id: str, data_dir: Path = TRANSCRIPT_DIR) -> list[Seg]:
    """Đọc transcript-<session_id>-clean.md."""
    path = data_dir / f"transcript-{session_id}-clean.md"
    return parse_text(path.read_text(encoding="utf-8"), session_id)


def parse_all(data_dir: Path = TRANSCRIPT_DIR) -> list[Seg]:
    """Cả 6 buổi, theo thứ tự buổi."""
    return [seg for sid in SESSIONS for seg in parse_session(sid, data_dir)]


def content_segs(segs: list[Seg]) -> list[Seg]:
    """Chỉ giữ đoạn nội dung giảng — loại 55 ghi chú hoạt động lớp."""
    return [s for s in segs if not s.is_activity]


def index_by_code(segs: list[Seg]) -> dict[str, Seg]:
    """Chỉ mục mã → đoạn. Dùng ở cổng 3."""
    return {s.code: s for s in segs}
