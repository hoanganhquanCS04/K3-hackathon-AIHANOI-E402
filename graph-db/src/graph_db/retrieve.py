"""Tim doan giang lien quan qua KNOWLEDGE GRAPH.

DAY LA THU VECTOR SEARCH KHONG LAM DUOC: tra ve doan lien quan QUA QUAN HE,
khong phai doan giong chu. Vi du "hoc xong attention thi hoc gi tiep" — khong
doan nao chua cum tu do, nhung graph di duoc tu Concept "attention" sang
Concept lien quan roi ve Turn noi ve chung.

RANH GIOI THAM QUYEN: chi lay Turn.id va diem. KHONG lay Concept.description
hay Concept.name vao ket qua — concept la phan doan cua LLM luc ingest, dua noi
dung cua no vao prompt la bien KG thanh nguon khang dinh. Co test canh dieu
nay: test_cypher_khong_lay_mo_ta_concept.

XEP HANG: (hop, -diem). Doan noi THANG ve concept dung truoc doan cach 1-2
quan he, du diem full-text cua doan xa co the cao hon.
"""

from __future__ import annotations

CYPHER = """
CALL db.index.fulltext.queryNodes('concept_name_ft', $thuc_the) YIELD node AS c, score
MATCH (c)<-[:COVERS]-(s:Section)<-[:BELONGS_TO]-(t:Turn)
WHERE t.is_activity = false AND ($session IS NULL OR t.lecture_id ENDS WITH $session)
RETURN t.id AS ma, score AS diem, 0 AS hop
UNION
CALL db.index.fulltext.queryNodes('concept_name_ft', $thuc_the) YIELD node AS c, score
MATCH (c)-[:RELATED_TO*1..2]-(:Concept)<-[:COVERS]-(s:Section)<-[:BELONGS_TO]-(t:Turn)
WHERE t.is_activity = false AND ($session IS NULL OR t.lecture_id ENDS WITH $session)
RETURN t.id AS ma, score * 0.5 AS diem, 1 AS hop
"""


def turns_for_concepts(
    thuc_the: list[str],
    *,
    session: str | None,
    k: int,
    run=None,
) -> list[tuple[str, float]]:
    """[(ma doan, diem)] xep theo (hop, -diem), da dedupe. `run` de test offline."""
    if not thuc_the:
        return []

    if run is None:
        from graph_db import query as run

    rows = run(
        CYPHER,
        {
            "thuc_the": " OR ".join(thuc_the),
            "session": f"T{session}" if session else None,
        },
    )

    rows = sorted(rows, key=lambda r: (r["hop"], -float(r["diem"])))
    seen: dict[str, float] = {}
    for row in rows:
        if row["ma"] not in seen:
            seen[row["ma"]] = float(row["diem"])
    return list(seen.items())[:k]
