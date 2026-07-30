"""Helper thuần không phụ thuộc Streamlit."""

from __future__ import annotations


def branch_table(raw_fuse: list[dict]) -> list[dict]:
    """Chuyển fuse.data['bang'] thành format hiển thị bảng so sánh 3 nhánh."""
    out = []
    for r in raw_fuse:
        b = r.get("rank_bm25")
        q = r.get("rank_qdrant")
        n = r.get("rank_neo4j")
        doc_quyen = []
        if b is not None and q is None and n is None:
            doc_quyen.append("BM25")
        if q is not None and b is None and n is None:
            doc_quyen.append("Qdrant")
        if n is not None and b is None and q is None:
            doc_quyen.append("Neo4j")

        out.append(
            {
                "Mã đoạn": r.get("ma", ""),
                "BM25": f"#{b + 1}" if b is not None else "—",
                "Qdrant": f"#{q + 1}" if q is not None else "—",
                "Neo4j": f"#{n + 1}" if n is not None else "—",
                "RRF": f"{r.get('rrf', 0.0):.4f}",
                "Chỉ nhánh này?": doc_quyen[0] if doc_quyen else "—",
            }
        )
    return out
