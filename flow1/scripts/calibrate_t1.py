"""Hiệu chỉnh T1_ABS và T1_RATIO trên 30 câu. Chủ: M2 (khối E).

    cd codebase && PYTHONUTF8=1 ../.venv/Scripts/python.exe scripts/calibrate_t1.py

Ba việc:
  1. In bảng phân bố: mỗi câu một dòng, có top1_abs và ratio.
  2. Quét lưới (T1_ABS × T1_RATIO), in ma trận (chặn out /N_out, qua in /N_in).
  3. Đề xuất cặp: ƯU TIÊN chặn hết out_of_scope, RỒI tối đa hoá in_scope qua được.

LUẬT TRUNG THỰC: nếu không cặp nào chặn hết out_of_scope mà vẫn giữ được phần lớn
in_scope, GHI THẬT là hai phân bố chồng nhau không tách được, kèm hệ quả. Không
chọn một ngưỡng nhìn đẹp rồi im. Bảng phân bố là artifact mạnh cho R4 kể cả khi
kết quả không đẹp.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from flow1.retrieve import retrieve  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "eval" / "t1" / "questions.jsonl"
OUT = ROOT / "eval" / "t1" / "distribution.md"

ABS_GRID = [0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0]
RATIO_GRID = [1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.75, 2.00]


def load_questions() -> list[dict]:
    if not QUESTIONS.exists():
        raise SystemExit(f"Chưa có {QUESTIONS}. Xem Task 11 Step 1-3 của plan.")
    return [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]


def measure(questions: list[dict]) -> list[dict]:
    rows = []
    for q in questions:
        r = retrieve(q["text"])
        rows.append({
            **q,
            "top1_abs": r.top1_abs,
            "ratio": r.ratio,
            "top_session": r.hits[0].session if r.hits else "—",
            "top_section": r.hits[0].section_title if r.hits else "—",
        })
    return rows


def blocked(row: dict, t_abs: float, t_ratio: float) -> bool:
    """Cổng 1 chặn khi MỘT trong hai dưới ngưỡng — khớp đúng flow1.gates.gate1."""
    return row["top1_abs"] < t_abs or row["ratio"] < t_ratio


def fmt(value: float) -> str:
    return "inf" if value == math.inf else f"{value:.2f}"


def main() -> int:
    rows = measure(load_questions())
    ins = [r for r in rows if r["expect"] == "in_scope"]
    outs = [r for r in rows if r["expect"] == "out_of_scope"]

    lines = [
        "# Hiệu chỉnh ngưỡng T1 — bảng phân bố 30 câu",
        "",
        f"- Số câu: {len(rows)} ({len(ins)} trong phạm vi · {len(outs)} ngoài phạm vi)",
        f"- Câu lấy thật từ chatlog: {sum(1 for r in rows if r['source'].startswith('chatlog'))}",
        f"- Câu do người soạn (đã kiểm grep không có trong 6 buổi): "
        f"{sum(1 for r in rows if r['source'] == 'người soạn')}",
        "",
        "> Điểm dưới đây là điểm BM25 THÔ. Cổng 1 luôn quyết định trên điểm thô, không",
        "> trên điểm RRF đã fuse — nên bảng này vẫn có hiệu lực khi bật embedding.",
        "",
        "## Phân bố từng câu",
        "",
        "| id | expect | top1_abs | ratio | buổi | section top-1 | source |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: (x["expect"], -x["top1_abs"])):
        lines.append(
            f"| {r['id']} | {r['expect']} | {r['top1_abs']:.2f} | {fmt(r['ratio'])} | "
            f"{r['top_session']} | {r['top_section'][:34]} | {r['source']} |"
        )

    lines += ["", "## Ma trận ngưỡng — (chặn ngoài-phạm-vi / qua trong-phạm-vi)", ""]
    lines.append("| T1_ABS ↓ / T1_RATIO → | " + " | ".join(f"{t:.2f}" for t in RATIO_GRID) + " |")
    lines.append("|---" * (len(RATIO_GRID) + 1) + "|")

    best = None
    for t_abs in ABS_GRID:
        cells = []
        for t_ratio in RATIO_GRID:
            n_blocked = sum(1 for r in outs if blocked(r, t_abs, t_ratio))
            n_passed = sum(1 for r in ins if not blocked(r, t_abs, t_ratio))
            cells.append(f"{n_blocked}/{n_passed}")
            score = (n_blocked, n_passed)
            if best is None or score > best[0]:
                best = (score, t_abs, t_ratio)
        lines.append(f"| **{t_abs:.1f}** | " + " | ".join(cells) + " |")

    (n_blocked, n_passed), t_abs, t_ratio = best
    perfect = n_blocked == len(outs)

    lines += [
        "",
        "## Cặp đề xuất",
        "",
        f"- `T1_ABS = {t_abs:.2f}` · `T1_RATIO = {t_ratio:.2f}`",
        f"- Chặn **{n_blocked}/{len(outs)}** câu ngoài phạm vi · "
        f"cho qua **{n_passed}/{len(ins)}** câu trong phạm vi",
        "",
    ]
    if perfect:
        lines.append(
            f"Hai phân bố tách được. Ở cặp này {n_blocked}/{len(outs)} câu ngoài phạm vi "
            f"bị chặn và {n_passed}/{len(ins)} câu trong phạm vi vẫn qua."
        )
    else:
        lines.append(
            f"**KHÔNG tách được hoàn toàn.** Cặp tốt nhất vẫn để lọt "
            f"{len(outs) - n_blocked}/{len(outs)} câu ngoài phạm vi. Ghi thật ở đây thay vì "
            f"chọn một ngưỡng nhìn đẹp. Hệ quả: cổng 1 một mình không đủ, phần chặn còn "
            f"lại dựa vào rule cổng 0 và vào cổng 3 (mã bịa vẫn bị loại kể cả khi cổng 1 "
            f"cho qua). Đây là giới hạn đã biết, ghi vào spec §6."
        )

    lines += ["", "## Cách kiểm lại", "",
              "```", "cd codebase && PYTHONUTF8=1 ../.venv/Scripts/python.exe scripts/calibrate_t1.py",
              "```", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {OUT}")
    print(f"Đề xuất: T1_ABS = {t_abs:.2f} · T1_RATIO = {t_ratio:.2f} "
          f"→ chặn {n_blocked}/{len(outs)} · qua {n_passed}/{len(ins)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
