"""Result → text hiển thị. Chủ: M2, giao M4 khi ghép giao diện.

Nguyên tắc: mỗi khẳng định đi kèm mã đoạn VÀ nguyên văn đoạn đó ngay bên dưới.
Người đọc kiểm được tại chỗ, không phải mở file khác. Đây là chiều đo *truy vết*
của quality bar, và là chỗ trỏ vào HAX G11 — làm rõ nguồn.

Ba mục KHÔNG được giấu, kể cả khi chúng làm output trông kém đẹp:
  - nhãn "một học viên nêu"          (lớp ④)
  - cảnh báo bản ghi thiếu           (lớp ①)
  - danh sách khẳng định đã bị loại  (lớp ①)
"""

from __future__ import annotations

from flow1.check import GAP_LABEL, STUDENT_LABEL
from flow1.models import Seg
from flow1.parse import index_by_code

_NO_ANSWER = (
    "Các đoạn mình tìm được không đủ căn cứ để trả lời câu này. "
    "Mình không đoán tiếp."
)


def _render_citation(code: str, seg: Seg | None, verdict) -> list[str]:
    if seg is None:
        return [f"   `[{code}]`", "   > (không tìm thấy đoạn này trong transcript)"]

    lines = [f"   `[{code}]` ({seg.session_title})"]

    notes: list[str] = []
    if code in verdict.student_codes:
        notes.append(STUDENT_LABEL)
    if code in verdict.gap_codes:
        notes.append(GAP_LABEL)
    if notes:
        lines.append(f"   > **{' · '.join(notes)}**")

    lines.append(f"   > {seg.text}")
    return lines


def render(result, segs: list[Seg]) -> str:
    """Text hiển thị cho một lượt hỏi."""
    lines: list[str] = [f"❓ {result.question}", ""]

    # Các outcome không có verdict: cổng 0, cổng 1, hoặc lỗi cổng 2.
    if result.verdict is None:
        lines.append(result.message)
        return "\n".join(lines)

    verdict = result.verdict
    index = index_by_code(segs)

    if verdict.claims:
        for i, claim in enumerate(verdict.claims, 1):
            lines.append(f"{i}. {claim.text}")
            for code in claim.cite:
                lines.extend(_render_citation(code, index.get(code), verdict))
            lines.append("")
    else:
        lines.append(_NO_ANSWER)
        lines.append("")

    if verdict.drops:
        lines.append("---")
        lines.append("")
        lines.append("**Khẳng định đã bị loại** — ghi lại để minh bạch, không giấu:")
        lines.append("")
        for drop in verdict.drops:
            lines.append(f"- `{drop.kind}` — \"{drop.claim_text}\" · {drop.detail}")
        lines.append("")

    if result.retrieval is not None and result.retrieval.hits:
        first = result.retrieval.hits[0]
        lines.append(
            f"_Nguồn: {first.chunk.session_title} · "
            f"{len(result.retrieval.hits)} đoạn được xét._"
        )

    return "\n".join(lines)
