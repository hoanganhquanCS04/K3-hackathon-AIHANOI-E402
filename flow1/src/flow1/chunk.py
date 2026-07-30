"""list[Seg] → list[Chunk]. CHỈ phục vụ luồng 1. Chủ: M1 (khối B).

Luồng 2 KHÔNG dùng file này — nó nạp thẳng cả buổi, không retrieval.

Sáu luật, mỗi luật có test:
  1. Đoạn [Txx-NNN] là NGUYÊN TỬ khi gộp — mã đoạn là citation unit.
  2. Gộp đoạn liền kề trong CÙNG section, target ~1.100, trần cứng 1.800 ký tự.
  3. Không gộp qua ranh giới section, không gộp qua ranh giới buổi.
  4. Overlap ĐÚNG 1 đoạn giữa hai chunk liền kề cùng section.
  5. 18 đoạn vượt trần → tách theo câu thành #a/#b/#c, nhưng seg_codes VẪN là mã
     gốc. Đoạn khổng lồ là chunk riêng, không gộp với ai, không tham gia overlap
     — luật này giữ vòng lặp đơn giản và luôn tiến.
  6. 55 đoạn is_activity đã bị loại từ trước (gọi content_segs).
"""

from __future__ import annotations

import itertools
import re

from flow1.models import Chunk, Seg

TARGET_CHARS = 1100
CAP_CHARS = 1800

# Tách sau dấu kết câu. Transcript đã được ngắt câu khi làm sạch nên dấu câu đáng tin.
_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")

# Chunk.text nối các phần bằng "\n\n" (2 ký tự) — phải cộng dồn overhead này khi
# quyết định gộp, nếu không tổng n_chars thật của Chunk (đã nối) có thể vượt
# CAP_CHARS dù tổng n_chars thô của từng Seg vẫn nằm trong trần. Đây là lệch so
# với bản brief: brief cộng thẳng seg.n_chars mà không cộng dồn overhead nối.
_JOIN_OVERHEAD = len("\n\n")


def _split_oversized_run(text: str) -> list[str]:
    """Tách một CÂU (giữa hai dấu kết câu) mà tự nó đã vượt CAP_CHARS, theo
    khoảng trắng, thành các mảnh <= CAP_CHARS.

    Nếu một "từ" đơn (không có khoảng trắng để tách tiếp) tự nó đã vượt trần
    thì giữ nguyên — cùng luật miễn trừ như `split_giant`: thà một mảnh quá
    trần còn hơn cắt ngang giữa từ hoặc rơi vào vòng lặp vô hạn.
    """
    words = [w for w in text.split(" ") if w]
    pieces: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if current and len(candidate) > CAP_CHARS:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    if not pieces:
        pieces = [text]

    return pieces


def _make_chunk(segs: list[Seg], *, chunk_id: str | None = None, text: str | None = None) -> Chunk:
    """Dựng Chunk từ các đoạn liền kề. `text` chỉ truyền khi tách đoạn khổng lồ."""
    head = segs[0]
    parts = [(head.code, text)] if text is not None else [(s.code, s.text) for s in segs]
    return Chunk(
        chunk_id=chunk_id or head.code,
        session=head.session,
        session_title=head.session_title,
        section_idx=head.section_idx,
        section_title=head.section_title,
        parts=parts,
        has_gap=any(s.has_gap for s in segs),
    )


def split_giant(seg: Seg) -> list[Chunk]:
    """Tách một đoạn vượt trần theo câu. Mọi mảnh giữ MÃ GỐC.

    Không tách được (không có dấu câu nào) → trả về đúng 1 mảnh nguyên đoạn. Thà
    có một chunk quá trần còn hơn cắt ngang giữa từ hoặc rơi vào vòng lặp vô hạn.

    Một câu ĐƠN (giữa hai dấu kết câu) có thể tự nó đã vượt CAP_CHARS — bản đầu
    chỉ kiểm tra `len(candidate) > CAP_CHARS` khi `current` đã có nội dung, nên
    câu đơn khổng lồ đầu tiên lọt qua kiểm tra và bị đẩy nguyên xi thành một
    mảnh vượt trần. Sửa: mọi câu tự nó vượt trần được tách tiếp theo khoảng
    trắng (`_split_oversized_run`) trước khi được xếp vào `pieces`.
    """
    sentences = [s for s in _SENTENCE_RE.split(seg.text) if s]
    pieces: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > CAP_CHARS:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_oversized_run(sentence))
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > CAP_CHARS:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)
    if not pieces:
        pieces = [seg.text]

    return [
        _make_chunk([seg], chunk_id=f"{seg.code}#{chr(ord('a') + i)}", text=piece)
        for i, piece in enumerate(pieces)
    ]


def _chunk_one_section(segs: list[Seg]) -> list[Chunk]:
    """Gộp trong một section. `segs` đã theo đúng thứ tự `order`."""
    chunks: list[Chunk] = []
    i = 0
    # True khi `i` hiện tại là đoạn overlap mượn lại từ chunk vừa phát ra —
    # nếu nhóm bắt đầu từ đây không gộp thêm được đoạn nào mới thì nhóm đó chỉ
    # là bản sao của đuôi chunk trước, không thêm nội dung gì cho index BM25.
    overlap_start = False

    while i < len(segs):
        if segs[i].n_chars > CAP_CHARS:
            chunks.extend(split_giant(segs[i]))       # luật 5 — không gộp, không overlap
            i += 1
            overlap_start = False
            continue

        group = [segs[i]]
        size = segs[i].n_chars
        j = i + 1
        while (
            j < len(segs)
            and size < TARGET_CHARS
            and segs[j].n_chars <= CAP_CHARS
            and size + _JOIN_OVERHEAD + segs[j].n_chars <= CAP_CHARS
        ):
            group.append(segs[j])
            size += _JOIN_OVERHEAD + segs[j].n_chars
            j += 1

        if overlap_start and len(group) == 1:
            # Đoạn overlap một mình không gộp thêm được đoạn nào mới — bỏ qua,
            # không phát chunk trùng lặp hoàn toàn với đuôi chunk liền trước.
            i = j
            overlap_start = False
            continue

        chunks.append(_make_chunk(group))

        # Overlap 1 đoạn — CHỈ khi group có ≥2 đoạn, nếu không vòng lặp không tiến.
        if len(group) > 1 and j < len(segs):
            i = j - 1
            overlap_start = True
        else:
            i = j
            overlap_start = False

    return chunks


def chunk_session(segs: list[Seg]) -> list[Chunk]:
    """Chunk các đoạn của MỘT buổi. Tự nhóm theo section, giữ thứ tự."""
    ordered = sorted(segs, key=lambda s: s.order)
    chunks: list[Chunk] = []
    for _, group in itertools.groupby(ordered, key=lambda s: s.section_idx):
        chunks.extend(_chunk_one_section(list(group)))
    return chunks


def chunk_all(segs: list[Seg]) -> list[Chunk]:
    """Chunk cả corpus. Không bao giờ gộp qua ranh giới buổi (luật 3)."""
    chunks: list[Chunk] = []
    for _, group in itertools.groupby(sorted(segs, key=lambda s: (s.session, s.order)),
                                      key=lambda s: s.session):
        chunks.extend(chunk_session(list(group)))
    return chunks
