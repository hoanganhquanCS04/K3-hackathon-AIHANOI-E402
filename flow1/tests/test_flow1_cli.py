"""Test CLI. Chủ: M2 → M4. KHÔNG gọi mạng."""

import pytest

from flow1.cli import main
from flow1.models import Answer, Claim, Intent, Seg


def seg(code, text):
    return Seg(
        code=code, session="03", session_title="Buổi 03 — Soi bài toán",
        locate_confidence="vừa", section_idx=1, section_title="RAG và tool calling",
        order=1, text=text, speaker="instructor",
        has_gap=False, is_activity=False, n_chars=len(text),
    )


SEGS = [seg("T03-002", "RAG là retrieval augmented generation.")]


@pytest.fixture
def offline(monkeypatch):
    """Chặn mọi lối ra mạng và mọi phụ thuộc vào đĩa."""
    from flow1 import ask as ask_module
    from flow1 import parse as parse_module

    monkeypatch.setattr(ask_module, "parse_all", lambda *a, **k: SEGS, raising=False)
    monkeypatch.setattr(parse_module, "parse_all", lambda *a, **k: SEGS, raising=False)

    def fake_retrieve(query, **kwargs):
        from flow1.index import build
        from flow1.models import Chunk, Hit, Retrieval

        chunk = Chunk(
            chunk_id="T03-002", session="03", session_title="Buổi 03 — Soi bài toán",
            section_idx=1, section_title="RAG và tool calling",
            parts=[("T03-002", SEGS[0].text)], has_gap=False,
        )
        if "kubernetes" in query:
            return Retrieval(hits=[], top1_abs=0.0, ratio=0.0)
        return Retrieval(
            hits=[Hit(chunk=chunk, bm25=99.0, emb=None, rank=0, score=99.0)],
            top1_abs=99.0, ratio=float("inf"),
        )

    monkeypatch.setattr(ask_module, "retrieve", fake_retrieve)
    return monkeypatch


def stub_answer(system, user_blocks, schema):
    return Answer(
        status="answered",
        claims=[Claim(text="RAG nạp thêm ngữ cảnh.", cite=["T03-002"], speaker="instructor")],
        gaps=[],
    )


def stub_intent(system, user_blocks, schema):
    return Intent(label="nội_dung_khoá", reason="test")


@pytest.fixture
def wired(offline, monkeypatch):
    from flow1 import cli as cli_module

    monkeypatch.setattr(cli_module, "_ANSWER_CALL", stub_answer, raising=False)
    monkeypatch.setattr(cli_module, "_CLASSIFY_CALL", stub_intent, raising=False)
    monkeypatch.setattr(cli_module, "_CHECK_CITATIONS", lambda p, s: [], raising=False)
    return monkeypatch


# --- ask ------------------------------------------------------------------

def test_ask_prints_the_answer_and_exits_zero(wired, capsys):
    assert main(["ask", "RAG là gì"]) == 0
    out = capsys.readouterr().out
    assert "RAG nạp thêm ngữ cảnh." in out


def test_ask_prints_the_citation_and_the_verbatim_segment(wired, capsys):
    main(["ask", "RAG là gì"])
    out = capsys.readouterr().out
    assert "T03-002" in out
    assert "retrieval augmented generation" in out


def test_a_refusal_also_exits_zero_because_refusing_correctly_is_success(wired, capsys):
    assert main(["ask", "kubernetes helm istio"]) == 0
    assert "6 buổi" in capsys.readouterr().out


def test_an_off_topic_question_exits_zero_and_prints_the_template(wired, capsys):
    assert main(["ask", "bạn là GPT hay Claude hay Gemini"]) == 0
    assert "ngoài phạm vi" in capsys.readouterr().out.lower()


def test_a_model_error_exits_one(offline, monkeypatch, capsys):
    from flow1 import cli as cli_module

    def boom(system, user_blocks, schema):
        raise RuntimeError("mạng chết")

    monkeypatch.setattr(cli_module, "_ANSWER_CALL", boom, raising=False)
    monkeypatch.setattr(cli_module, "_CLASSIFY_CALL", stub_intent, raising=False)
    monkeypatch.setattr(cli_module, "_CHECK_CITATIONS", lambda p, s: [], raising=False)
    assert main(["ask", "RAG là gì"]) == 1
    assert "không trả lời" in capsys.readouterr().out


def test_the_session_flag_is_accepted_so_the_correction_path_works(wired, capsys):
    assert main(["ask", "RAG là gì", "--session", "03"]) == 0


def test_a_missing_index_exits_three_with_the_fix_command(monkeypatch, capsys):
    from flow1 import ask as ask_module
    from flow1.index import IndexMissing

    def missing(*args, **kwargs):
        raise IndexMissing("Chưa có index. Dựng trước bằng:  python -m flow1 index")

    monkeypatch.setattr(ask_module, "retrieve", missing)
    monkeypatch.setattr(ask_module, "parse_all", lambda *a, **k: SEGS, raising=False)
    from flow1 import cli as cli_module

    monkeypatch.setattr(cli_module, "_CLASSIFY_CALL", stub_intent, raising=False)
    assert main(["ask", "RAG là gì"]) == 3
    assert "python -m flow1 index" in capsys.readouterr().out


# --- index ---------------------------------------------------------------

def test_index_reports_how_many_chunks_it_built(monkeypatch, capsys, tmp_path):
    from flow1 import cli as cli_module

    monkeypatch.setattr(cli_module, "build_from_data", lambda **kwargs: 412)
    assert main(["index"]) == 0
    assert "412" in capsys.readouterr().out


def test_index_reports_a_missing_data_pack_instead_of_a_traceback(monkeypatch, capsys):
    from flow1 import cli as cli_module

    def missing(**kwargs):
        raise FileNotFoundError("transcript-01-clean.md")

    monkeypatch.setattr(cli_module, "build_from_data", missing)
    assert main(["index"]) == 3
    assert "data pack" in capsys.readouterr().out


# --- build ---------------------------------------------------------------

def test_build_invalid_session_prints_refusal(capsys):
    assert main(["build", "07"]) == 0
    out = capsys.readouterr().out
    assert "07 không có trong 6 buổi đã ghi" in out
    assert "01, 02, 03, 04, 05, 06" in out


# --- Hình dạng CLI -------------------------------------------------------

def test_a_command_is_required():
    with pytest.raises(SystemExit):
        main([])


def test_an_unknown_command_exits_nonzero():
    with pytest.raises(SystemExit):
        main(["khong-co-lenh"])

