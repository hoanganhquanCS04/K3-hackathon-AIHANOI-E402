from scripts.check_env import REQUIREMENTS, check_env


def test_env_du_thi_khong_bao_gi():
    full = {name: "x" for group in REQUIREMENTS.values() for name in group}
    assert check_env(full) == []


def test_bao_dung_bien_thieu_va_package_chet_vi_no():
    partial = {name: "x" for group in REQUIREMENTS.values() for name in group}
    del partial["QDRANT_URL"]
    lines = check_env(partial)
    assert len(lines) == 1
    assert "QDRANT_URL" in lines[0]
    assert "vector-db" in lines[0]


def test_bien_rong_tinh_la_thieu():
    full = {name: "x" for group in REQUIREMENTS.values() for name in group}
    full["OPENAI_API_KEY"] = "   "
    lines = check_env(full)
    assert any("OPENAI_API_KEY" in line for line in lines)


def test_requirements_khop_voi_bien_ma_qdrant_that_su_doi():
    """REQUIREMENTS phai khop code THAT, khong phai khop chinh no.

    Neu ai do them mot bien bat buoc vao QdrantStore ma quen cap nhat
    REQUIREMENTS thi check_env.py se bao 'OK' nham — dung loi ma task nay
    ton tai de chan.
    """
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    src = Path(__file__).resolve().parents[2] / "vector-db" / "src" / "vector_db"
    text = (src / "qdrant_store.py").read_text(encoding="utf-8")
    for name in ("QDRANT_URL", "QDRANT_API_KEY"):
        assert name in text, f"{name} khong con duoc qdrant_store.py nhac toi"
        assert name in REQUIREMENTS["vector-db"]


def test_requirements_khop_voi_bien_ma_graph_db_that_su_doi():
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    conn = (
        Path(__file__).resolve().parents[2]
        / "graph-db" / "src" / "graph_db" / "connection.py"
    )
    text = conn.read_text(encoding="utf-8")
    for name in REQUIREMENTS["graph-db"]:
        assert name in text, f"REQUIREMENTS khai {name} ma connection.py khong doc"


def test_neo4j_database_co_trong_env_example_du_khong_bat_buoc():
    """connection.py:45 co doc NEO4J_DATABASE (co mac dinh 'neo4j').

    Khong bat buoc nen KHONG vao REQUIREMENTS, nhung phai co mat trong
    .env.example de nguoi dung Neo4j tu host biet duong doi.
    """
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    example = Path(__file__).resolve().parents[2] / ".env.example"
    assert "NEO4J_DATABASE" in example.read_text(encoding="utf-8")
    assert "NEO4J_DATABASE" not in REQUIREMENTS["graph-db"]
