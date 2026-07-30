"""Cổng 3 — bộ kiểm tất định SAU generate. Chủ: M2 (khối E).

KHÔNG BAO GIỜ CẮT FILE NÀY. Nó là chỗ lớp ① và lớp ④ được xử bằng kỹ thuật chứ
không bằng một câu nhờ vả trong prompt.

Nguyên tắc: phát hiện thì BÁO và LOẠI, không bao giờ TỰ SỬA. Sửa mã đoạn hộ model
tức là đoán, và đoán là đúng cái lớp ① đang phòng.

Ba tầng kiểm, mỗi tầng ở đúng chỗ của nó:

  1. Mã ∈ 700 mã thật     → verify.check_citations, DÙNG CHUNG với luồng 2.
                             M1 viết bộ kiểm, M2 viết prompt — hai người, để lớp ①
                             có đối trọng thật.
  2. Mã ∈ context đã gửi  → riêng luồng 1. Luồng 2 nạp cả buổi nên hai tập trùng
                             nhau; luồng 1 chỉ gửi 5 chunk, nên một mã THẬT mà
                             không nằm trong context vẫn là bịa — model không có
                             đường nào biết nội dung đoạn đó.
  3. Nhãn giọng + cờ gap  → riêng luồng 1, cần field speaker/has_gap mà chỉ Seg
                             của luồng 1 có.

`check_citations` inject được nên file này test được ngay, không chờ M1 xong verify.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from flow1.models import Answer, Claim, Drop, Retrieval, Seg, Verdict
from flow1.parse import index_by_code

STUDENT_LABEL = "một học viên nêu"
GAP_LABEL = "⚠ bản ghi đoạn này thiếu"

# Kind mà bộ kiểm dùng chung trả về và ĐÁNG bị loại claim. `transcript_gap` KHÔNG
# nằm ở đây: bản ghi thiếu không có nghĩa là ý sai — gắn cờ, không xoá.
_DROPPING_KINDS = frozenset({"unknown_code", "no_codes", "cites_activity"})


@dataclass(frozen=True)
class _PointView:
    """Adapter cho verify module — nó đọc `.codes` và `.statement`.

    Tồn tại để bộ kiểm của M1 chạy trên claim của luồng 1 mà không cần sửa. Đổi
    tên hai attribute này là phá hợp đồng dùng chung.
    """

    statement: str
    codes: list[str]


def context_codes(r: Retrieval) -> set[str]:
    """Mọi mã đoạn ĐÃ THỰC SỰ được đưa vào prompt."""
    return {code for hit in r.hits for code in hit.chunk.seg_codes}


def check(
    answer: Answer,
    retrieval: Retrieval,
    segs: list[Seg],
    *,
    check_citations=None,
) -> Verdict:
    """Kiểm output cổng 2. Trả Verdict chỉ chứa claim đã qua kiểm."""
    if answer.status != "answered":
        return Verdict(status=answer.status)

    if check_citations is None:
        def dummy_check_citations(points, segments):
            seg_codes_set = {s.code for s in segments}
            act_codes_set = {s.code for s in segments if s.is_activity}
            findings = []
            for idx, p in enumerate(points):
                if not p.codes:
                    findings.append(type("Finding", (), {"point_index": idx, "kind": "no_codes", "detail": "Khẳng định này không có mã đoạn nào chống lưng."})())
                for c in p.codes:
                    if c not in seg_codes_set:
                        findings.append(type("Finding", (), {"point_index": idx, "kind": "unknown_code", "detail": f"Trích mã {c} — mã này không có trong transcript."})())
                    elif c in act_codes_set:
                        findings.append(type("Finding", (), {"point_index": idx, "kind": "cites_activity", "detail": f"Trích mã {c} — mã này là hoạt động lớp."})())
            return findings
        check_citations = dummy_check_citations

    points = [_PointView(statement=c.text, codes=list(c.cite)) for c in answer.claims]
    findings = check_citations(points, segs)

    dropped_by_shared: dict[int, tuple[str, str]] = {}
    for finding in findings:
        if getattr(finding, "kind", None) in _DROPPING_KINDS and getattr(finding, "point_index", -1) >= 0:
            dropped_by_shared.setdefault(finding.point_index, (finding.kind, finding.detail))

    index = index_by_code(segs)
    allowed = context_codes(retrieval)

    kept: list[Claim] = []
    drops: list[Drop] = []
    student_codes: list[str] = []
    gap_codes: list[str] = []

    for i, claim in enumerate(answer.claims):
        if not claim.cite:
            drops.append(Drop(claim_text=claim.text, kind="no_codes",
                              detail="Khẳng định này không có mã đoạn nào chống lưng."))
            continue

        if i in dropped_by_shared:
            kind, detail = dropped_by_shared[i]
            drops.append(Drop(claim_text=claim.text, kind=kind, detail=detail))
            continue

        outside = [c for c in claim.cite if c not in allowed]
        if outside:
            drops.append(Drop(
                claim_text=claim.text, kind="outside_context",
                detail=(f"Trích mã {', '.join(outside)} — mã có thể tồn tại trong "
                        f"transcript, nhưng KHÔNG nằm trong context đã gửi cho model, "
                        f"nếu nội dung nó khẳng định là không có căn cứ."),
            ))
            continue

        kept.append(claim)

        # Nhãn do CODE quyết định, không do model tự khai (lớp ④).
        for code in claim.cite:
            seg = index.get(code)
            if seg is None:
                continue
            if seg.speaker == "student" and code not in student_codes:
                student_codes.append(code)
            if seg.has_gap and code not in gap_codes:
                gap_codes.append(code)

    status = "answered" if kept else "insufficient"
    return Verdict(
        status=status, claims=kept, drops=drops,
        student_codes=student_codes, gap_codes=gap_codes,
    )
