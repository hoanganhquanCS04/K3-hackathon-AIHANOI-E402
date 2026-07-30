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
    ton tai de chan. Luu y: test nay chi kiem tra mot chieu (REQUIREMENTS toi code),
    khong kiem tra chieu nguoc (code toi REQUIREMENTS), vi vector-db khong co
    danh sach canonical _REQUIRED like graph-db co.
    """
    from pathlib import Path

    from scripts.check_env import REQUIREMENTS

    src = Path(__file__).resolve().parents[2] / "vector-db" / "src" / "vector_db"
    text = (src / "qdrant_store.py").read_text(encoding="utf-8")
    for name in ("QDRANT_URL", "QDRANT_API_KEY"):
        assert name in text, f"{name} khong con duoc qdrant_store.py nhac toi"
        assert name in REQUIREMENTS["vector-db"]


def test_requirements_khop_voi_bien_ma_graph_db_that_su_doi():
    """REQUIREMENTS phai khop chinh xac set bien bat buoc cua graph_db.connection._REQUIRED.

    Kiem tra hai chieu: neu ai do them bien vao _REQUIRED ma quen cap nhat
    REQUIREMENTS, hoac xoa khoi _REQUIRED ma quen xoa REQUIREMENTS, thi test
    se bao. Dung set equality thay vi substring check de phat hien ca hai
    huong drift.
    """
    from graph_db.connection import _REQUIRED
    from scripts.check_env import REQUIREMENTS

    assert set(REQUIREMENTS["graph-db"]) == set(_REQUIRED), (
        f"REQUIREMENTS['graph-db'] = {set(REQUIREMENTS['graph-db'])}, "
        f"but graph_db.connection._REQUIRED = {set(_REQUIRED)}"
    )


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
