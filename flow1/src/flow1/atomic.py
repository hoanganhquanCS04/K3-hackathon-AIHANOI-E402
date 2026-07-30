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
