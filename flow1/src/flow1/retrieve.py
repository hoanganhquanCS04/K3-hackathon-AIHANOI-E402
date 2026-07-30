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


def gate_stats(bm25_desc: list[float]) -> tuple[float, float]:
    """Trả (top1_abs, ratio) từ danh sách điểm BM25 THÔ ĐÃ SẮP GIẢM DẦN."""
    window = bm25_desc[:_RATIO_WINDOW]
    for i in range(len(window) - 1):
        if window[i] < window[i + 1]:
            raise ValueError(
                "gate_stats yêu cầu bm25_desc là điểm BM25 thô đã sắp giảm "
                f"dần; vi phạm tại index {i}: {window[i]!r} < "
                f"{window[i + 1]!r}. Đừng truyền danh sách điểm đã fuse "
                "(RRF) vào đây — sort giảm dần theo BM25 thô trước khi gọi."
            )

    if not bm25_desc:
        return 0.0, 0.0

    top1 = float(bm25_desc[0])
    if top1 <= 0.0:
        return 0.0, 0.0

    rest = [float(s) for s in bm25_desc[1:_RATIO_WINDOW]]
    if not rest:
        return top1, math.inf

    mean_rest = sum(rest) / len(rest)
    if mean_rest == 0.0:
        return top1, math.inf

    return top1, top1 / mean_rest


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
    embeddings=None,
    query_vector=None,
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
