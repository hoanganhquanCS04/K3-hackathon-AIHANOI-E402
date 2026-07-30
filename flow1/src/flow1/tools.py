"""Hai tool cua agent.

tra_cuu  — viet lai query -> fuse ba nhanh -> 4 cong -> cau tra loi co ma doan.
tom_tat  — tra so tay ca buoi tu package summarizer (co cache).

RANH GIOI: tool KHONG tu quyet dinh duoc goi hay khong — do la viec cua agent.
Tool cung khong biet gi ve LLM dieu phoi; no chi lam dung phan viec cua no.
"""

from __future__ import annotations

from typing import Any

SESSIONS_CO_SAN = ("T01", "T02", "T03", "T04", "T05", "T06")

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tra_cuu",
            "description": (
                "Tra cuu noi dung LOI GIANG trong 6 buoi co ban ghi va tra loi "
                "kem ma doan trich dan. Dung cho moi cau hoi ve kien thuc, khai "
                "niem, vi du, cach lam ma giang vien da noi trong buoi."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Cau hoi cua hoc vien, giu nguyen van.",
                    },
                    "session": {
                        "type": "string",
                        "description": (
                            "Ma buoi de gioi han pham vi, dang '01'..'06'. "
                            "Bo trong khi hoc vien khong noi ro buoi nao."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tom_tat",
            "description": (
                "Tra so tay tom tat CA MOT BUOI hoc: cac y chinh kem ma doan. "
                "Dung khi hoc vien xin tom tat, xin y chinh, hoac hoi 'buoi X noi ve gi'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Ma buoi, dang 'T01'..'T06'.",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
]


def _chuan_hoa_buoi(session_id: str) -> str:
    """'3' | '03' | 'T03' -> 'T03'."""
    raw = str(session_id).strip().upper().removeprefix("T")
    return f"T{int(raw):02d}" if raw.isdigit() else f"T{raw}"


def tra_cuu(
    query: str,
    *,
    session: str | None = None,
    toggles=None,
    store=None,
    retrievers=None,
    trace=None,
    rewrite_call=None,
    **kw,
):
    """Viet lai query -> retrieve ba nhanh -> 4 cong. Tra ve `flow1.ask.Result`.

    `retrievers` phai di xuyen xuong toi retrieve, khong duoc nuot: test goi
    tra_cuu voi mot dict chi co BM25 that de KHONG cham mang. Nuot tham so nay
    la moi test co .env deu goi Qdrant that.
    """
    from flow1.ask import ask
    from flow1.rewrite import rewrite_query

    q = rewrite_query(query, call=rewrite_call, trace=trace)
    return ask(
        query,
        session=session,
        store=store,
        trace=trace,
        rewritten=q,
        toggles=toggles,
        retrievers=retrievers,
        **kw,
    )


def _load_summary_that(session_id: str) -> dict[str, Any]:
    """Doc session summary da sinh boi package summarizer."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    path = root / "summarizer" / "artifacts" / "summaries" / session_id / "session.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def tom_tat(session_id: str, *, trace=None, load_summary=None, **kw) -> dict[str, Any]:
    """So tay ca buoi. Buoi khong co ban ghi -> tu choi + liet ke buoi co san.

    `**kw` nuot cac tham so cua tool KIA (toggles, store, segs...). agent_run
    truyen mot bo tool_kwargs chung xuong tool nao duoc chon; khong nuot thi
    model chon tom_tat la TypeError.
    """
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(session_id)
    load_summary = load_summary if load_summary is not None else _load_summary_that

    with trace.stage("tom_tat") as tdata:
        sid = _chuan_hoa_buoi(session_id)
        tdata["session_id"] = sid
        tdata["xin_ban_dau"] = session_id

        try:
            summary = load_summary(sid)
        except FileNotFoundError:
            tdata["ket_luan"] = f"khong co ban ghi cho {sid}"
            return {
                "status": "out_of_scope",
                "session_id": sid,
                "message": (
                    f"Minh khong co ban ghi cua buoi {sid}. Sau buoi minh co ban "
                    f"ghi: {', '.join(SESSIONS_CO_SAN)}."
                ),
            }

        tdata["n_y_chinh"] = len(summary.get("key_points", []))
        return summary
