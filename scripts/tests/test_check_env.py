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
