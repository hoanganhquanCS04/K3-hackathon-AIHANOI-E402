"""Sinh outline.json — mục lục "phần" cho 6 buổi, đọc trực tiếp từ transcript.

Chạy:  python codebase/tools/build_outline.py

Đây là bước KHÔNG dùng AI, và có chủ đích: tên section trong 6 transcript do người
biên tập đặt sẵn, đã sạch và có nghĩa. Câu hỏi "buổi này có mấy phần" là câu hỏi
deterministic — đưa cho LLM chỉ thêm đường bịa mà không thêm giá trị.

Output là fixture GITIGNORE (dẫn xuất của data pack — README điều 3).
Ai cần thì chạy lại script này.

TODO(M5): sau khi chạy, sửa tay `title` của từng phần cho gọn và đúng mạch giảng.
          Chỗ nào còn "title_auto": true là chỗ chưa ai duyệt.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "vlearn-pack" / "transcript"
OUT = ROOT / "flow1" / "fixtures" / "outline.json"

# Buổi nào có ít section thì mỗi section là một phần; nhiều thì gộp lại còn ~5.
MAX_SECTIONS_1_1 = 7
TARGET_PARTS = 5

RE_SECTION = re.compile(r"^## (.+)$", re.M)
RE_SEGMENT = re.compile(r"\*\*\[(T\d{2}-\d{3})\]\*\*")
RE_TITLE = re.compile(r"^# Transcript bài giảng \(bản sạch\) — (.+)$", re.M)
RE_CONFIDENCE = re.compile(r"độ tin cậy:\s*([^\n·]+)")
RE_ACTIVITY = re.compile(r"\[Hoạt động lớp")
RE_UNCLEAR = re.compile(r"\[không nghe rõ\]")

# ⚠ HAI QUY ƯỚC KHÁC NHAU, TUYỆT ĐỐI KHÔNG GỘP (đây là lớp ④ trong canvas §4.1):
#   `[Học viên]:`  hoa + dấu hai chấm  → LỜI HỌC VIÊN nói ra          (69 đoạn)
#   `[học viên]`   thường, không dấu   → TÊN học viên đã ẩn danh, do
#                                        GIẢNG VIÊN nhắc tới          (59 chỗ)
# Dùng regex case-insensitive ở đây là gán 59 đoạn lời giảng viên thành lời học viên.
RE_STUDENT_SPEECH = re.compile(r"\[Học viên\]:")
RE_STUDENT_NAMED = re.compile(r"\[học viên\]")


def split_segments(body: str) -> list[dict]:
    """Cắt thân section thành các đoạn [Txx-NNN]. Đoạn là ĐƠN VỊ NGUYÊN TỬ."""
    hits = list(RE_SEGMENT.finditer(body))
    out = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(body)
        text = body[m.end() : end].strip()
        out.append(
            {
                "seg_id": m.group(1),
                "text": text,
                # đoạn CÓ CHỨA lời học viên — không có nghĩa là cả đoạn là lời học viên
                "has_student_speech": bool(RE_STUDENT_SPEECH.search(text)),
                "mentions_student": bool(RE_STUDENT_NAMED.search(text)),
                "is_activity": bool(RE_ACTIVITY.search(text)),
                "has_unclear": bool(RE_UNCLEAR.search(text)),
                "n_chars": len(text),
            }
        )
    return out


def parse_sections(raw: str) -> list[dict]:
    """Cắt theo heading `##`. Số section phải giữ đúng 96 cho cả 6 buổi (canvas §8).

    Buổi 02 và 05 có đúng 1 đoạn nằm TRƯỚC heading đầu tiên (T02-001, T05-001).
    Gộp chúng vào section 1 thay vì tạo section giả — nếu tạo section giả thì con số
    96 sẽ thành 98 và lệch với §8.
    """
    chunks = RE_SECTION.split(raw)
    orphans = split_segments(chunks[0])  # đoạn mồ côi trong phần mở đầu

    sections = []
    for i in range(1, len(chunks), 2):
        title, body = chunks[i].strip(), chunks[i + 1]
        sections.append(
            {"title": title, "n_chars": len(body), "segments": split_segments(body)}
        )

    if orphans and sections:
        sections[0]["segments"] = orphans + sections[0]["segments"]
        sections[0]["n_chars"] += sum(s["n_chars"] for s in orphans)
    return sections


def group_into_parts(sections: list[dict]) -> list[list[int]]:
    """Gộp các section LIỀN KỀ thành phần. Không bao giờ gộp qua ranh giới buổi.

    Section liền kề trong một buổi vốn đã liền chủ đề, nên gộp theo thứ tự là an toàn
    về mặt ngữ nghĩa — và giữ được tính "bấm vào là về đúng chỗ trong buổi".
    """
    if len(sections) <= MAX_SECTIONS_1_1:
        return [[i] for i in range(len(sections))]

    total = sum(s["n_chars"] for s in sections)
    target = total / TARGET_PARTS
    parts, buf, acc = [], [], 0
    for i, s in enumerate(sections):
        buf.append(i)
        acc += s["n_chars"]
        remaining = len(sections) - i - 1
        # đóng phần khi đủ nặng, nhưng phải chừa đủ section cho các phần còn lại
        if acc >= target * 0.8 and remaining >= TARGET_PARTS - len(parts) - 1:
            parts.append(buf)
            buf, acc = [], 0
    if buf:
        parts.append(buf)
    return parts


def pick_quotes(segments: list[dict], k: int = 3) -> list[dict]:
    """Vài câu nguyên văn NGẮN để giao diện có nội dung thật mà xem.

    Cố ý cắt ngắn (≤170 ký tự) — README điều 3 cho phép "trích dẫn ngắn để minh hoạ".
    """
    cands = [s for s in segments if not s["is_activity"] and s["n_chars"] > 400]
    cands.sort(key=lambda s: -s["n_chars"])
    out = []
    for s in cands[:k]:
        body = RE_STUDENT_SPEECH.sub("", s["text"]).strip()
        sentences = re.split(r"(?<=[.?!])\s+", body)
        text = next((x for x in sentences if len(x) > 60), body)
        if len(text) > 170:
            text = text[:167].rsplit(" ", 1)[0] + "…"
        out.append(
            {
                "seg_id": s["seg_id"],
                "text": text,
                "has_student_speech": s["has_student_speech"],
                "has_unclear": s["has_unclear"],
            }
        )
    return out


def short_title(section_titles: list[str]) -> str:
    """Nháp tên phần từ tên các section — M5 sẽ sửa tay."""
    first = section_titles[0].split(":")[0].split("—")[0].strip()
    if len(section_titles) == 1:
        return section_titles[0]
    last = section_titles[-1].split(":")[0].split("—")[0].strip()
    return f"{first} → {last}"


def build_session(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    sid = re.search(r"transcript-(\d{2})", path.name).group(1)

    m = RE_TITLE.search(raw)
    title = m.group(1).strip() if m else f"Buổi {sid}"
    # README transcript ghi kiểu "cao (khớp title bài học trong chatlog tutor)" —
    # tách lấy mức để UI so sánh được, giữ nguyên phần giải thích ở field riêng.
    mc = RE_CONFIDENCE.search(raw)
    raw_conf = mc.group(1).strip() if mc else "—"
    confidence = raw_conf.split("(")[0].strip() or "—"

    sections = parse_sections(raw)
    parts = []
    for pidx, idxs in enumerate(group_into_parts(sections), start=1):
        segs = [s for i in idxs for s in sections[i]["segments"]]
        titles = [sections[i]["title"] for i in idxs]
        n_act = sum(s["is_activity"] for s in segs)
        parts.append(
            {
                "idx": pidx,
                "title": short_title(titles),
                "title_auto": True,  # M5 sửa tay thì đổi thành false
                "section_titles": titles,
                "section_range": [idxs[0] + 1, idxs[-1] + 1],
                "n_chars": sum(sections[i]["n_chars"] for i in idxs),
                "n_segments": len(segs),
                "seg_ids": [s["seg_id"] for s in segs],
                "n_activity": n_act,
                "n_unclear": sum(s["has_unclear"] for s in segs),
                "n_student": sum(s["has_student_speech"] for s in segs),
                # phần chủ yếu là hoạt động lớp → non-goal #2: KHÔNG tóm, nhưng vẫn hiện
                "activity_heavy": bool(segs) and n_act / len(segs) >= 0.5,
                "quotes": pick_quotes(segs),
            }
        )

    all_segs = [s for sec in sections for s in sec["segments"]]
    return {
        "id": sid,
        "title": title,
        "locate_confidence": confidence,
        "locate_confidence_note": raw_conf,
        "n_sections": len(sections),
        "n_segments": len(all_segs),
        "n_activity": sum(s["is_activity"] for s in all_segs),
        "n_unclear": sum(s["has_unclear"] for s in all_segs),
        "n_student": sum(s["has_student_speech"] for s in all_segs),
        "parts": parts,
    }


def main() -> None:
    files = sorted(SRC.glob("transcript-*-clean.md"))
    if not files:
        raise SystemExit(f"Không thấy transcript nào trong {SRC}")

    sessions = [build_session(p) for p in files]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"sessions": sessions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Số phải khớp canvas §8: 700 đoạn · 55 hoạt động · 103 không-nghe-rõ · 69 học viên
    tot = {k: sum(s[k] for s in sessions) for k in ("n_segments", "n_sections", "n_activity", "n_unclear", "n_student")}
    print(f"→ {OUT.relative_to(ROOT)}")
    for s in sessions:
        print(f"   buổi {s['id']}: {s['n_sections']:2d} section → {len(s['parts'])} phần · {s['n_segments']:3d} đoạn")
    print(f"\nTổng: {tot['n_segments']} đoạn · {tot['n_sections']} section · "
          f"{tot['n_activity']} hoạt động · {tot['n_unclear']} không-nghe-rõ · {tot['n_student']} học viên")
    print("Đối chiếu canvas §8: 700 · 96 · 55 · 103 · 69")


if __name__ == "__main__":
    main()
