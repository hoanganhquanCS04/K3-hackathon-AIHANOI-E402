"""FastAPI wrapper cho backend Streamlit của VLearn.

KHONG sua `codebase/` — chi goi lai. Endpoint moi chi lam viec:
  - GET  /outline          — danh sach 6 buoi
  - GET  /session/{sid}    — metadata 1 buoi
  - POST /chat             — gui 1 query, lay ket qua (route + summarize/recap/answer)
  - GET  /backend          — nhan label (router / loader / map / reduce / KG)
  - POST /force            — bat/tat bo-qua-cache

Chay:
  uv pip install -r api/requirements.txt
  SUMMARIZER_VENV=C:\\temp\\summarizer_venv   # hoac venv mac dinh
  python api/main.py                        # uvicorn :8000

Frontend (web/) goi qua Vite proxy /api → :8000.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Quan trong: them codebase vao sys.path de import live.py, stubs.py, etc.
# KHONG sua codebase/ — chi thinh-controll no tu ben ngoai.
_ROOT = Path(__file__).resolve().parent.parent
_CODEBASE = _ROOT / "codebase"
if str(_CODEBASE) not in sys.path:
    sys.path.insert(0, str(_CODEBASE))

# Tu nap .env goc (chua OPENAI_API_KEY, NEO4J_*, QDRANT_*)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

# Them `summarizer/` (parent chua package `summarizer/`) va `src/` (graph_db, vector_db stub)
# vao sys.path TRUOC khi import live.py, vi live import `summarizer.llm`, `vector_db.session_reader`,
# va `graph_db.query`.
_SUMMARIZER_SRC = _ROOT / "summarizer" / "src"   # chua package 'summarizer/' ben trong (src layout cua uv_build)
_SRC = _ROOT / "src"
for p in (_SUMMARIZER_SRC, _SRC, _CODEBASE):
    sp = str(p)
    if p.is_dir() and sp not in sys.path:
        sys.path.insert(0, sp)

import live  # codebase/live.py  (se auto-import summarizer.llm, vector_db.session_reader, graph_db.query)

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import live  # codebase/live.py
import sources  # codebase/sources.py (graph_available)
from stubs import get_session, load_outline, refusal  # noqa: E402

app = FastAPI(title="VLearn API", version="0.1.0")

# CORS: cho phep Vite dev server goi tu :5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    sid: str
    query: str


class ForceRequest(BaseModel):
    force: bool


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/api/outline")
def get_outline() -> list[dict]:
    """Danh sach 6 buoi — giu nguyen shape ma live.load_outline() tra."""

    return load_outline()


@app.get("/api/session/{sid}")
def get_session_endpoint(sid: str) -> dict:
    sessions = load_outline()
    s = get_session(sessions, sid)
    if s is None:
        raise HTTPException(status_code=404, detail=f"khong tim thay buoi {sid}")
    return s


@app.get("/api/backend")
def get_backend() -> dict:
    graph_ok, graph_why = sources.graph_available()
    return {
        "label": live.backend_label(),
        "kg": {"ok": graph_ok, "why": graph_why},
    }


@app.post("/api/force")
def post_force(req: ForceRequest) -> dict:
    live.set_force(req.force)
    return {"force": req.force}


@app.post("/api/chat")
def post_chat(req: ChatRequest) -> dict:
    """Mot query, mot response — giong het `handle()` trong codebase/app.py.

    Tra ve JSON co `kind` de frontend render:
      - outline  : hien thi muc luc
      - part     : tom tat 1 phan
      - recap    : so tay ca buoi
      - answer   : tra cuu (van la cho trong)
      - text     : tu choi / chao hoi / yeu cau them thong tin
    """

    sessions = load_outline()
    session = get_session(sessions, req.sid)
    if session is None:
        raise HTTPException(status_code=404, detail=f"khong co buoi {req.sid}")

    state = {"sid": req.sid}
    decision = live.route(req.query, state)
    intent = decision["intent"]
    stats = live.last_stats()

    if intent in ("logistics", "ngoai_pham_vi", "chao_hoi"):
        return {
            "kind": "text",
            "payload": {"text": refusal(intent, session)},
            "intent": intent,
            "reason": decision.get("reason", ""),
            "stats": _stats_dict(stats),
        }

    if intent == "xem_muc_luc":
        return {
            "kind": "outline",
            "payload": session,
            "intent": intent,
            "reason": decision.get("reason", ""),
            "stats": None,
        }

    if intent == "tom_tat_thieu_slot":
        return {
            "kind": "text",
            "payload": {
                "text": (
                    f"Ban muon tom phan nao? Buoi nay co {len(session['parts'])} phan — "
                    'go "tom phan 2" hoac "tom ca buoi".'
                )
            },
            "intent": intent,
            "reason": decision.get("reason", ""),
            "stats": None,
        }

    if intent == "tom_tat_buoi":
        # Su dung done = {} — build_recap se tu chay map cho cac muc con thieu.
        result = live.build_recap(session, {})
        result["_stats"] = stats
        return {
            "kind": "recap",
            "payload": result,
            "intent": intent,
            "reason": decision.get("reason", ""),
            "stats": _stats_dict(stats),
        }

    if intent == "tom_tat_phan":
        from live import resolve_part

        idx, why = resolve_part(decision.get("part_ref"), session, {})
        if idx is None:
            return {
                "kind": "text",
                "payload": {"text": f"Minh chua xac dinh duoc phan nao ({why})."},
                "intent": intent,
                "reason": decision.get("reason", ""),
                "stats": None,
            }
        result = live.summarize_part(session, idx)
        result["_stats"] = stats
        return {
            "kind": "part",
            "payload": result,
            "intent": intent,
            "reason": decision.get("reason", ""),
            "stats": _stats_dict(stats),
        }

    # tra_cuu — van la cho trong giong app.py
    result = live.answer_query(session, req.query)
    return {
        "kind": "answer",
        "payload": result,
        "intent": intent,
        "reason": decision.get("reason", ""),
        "stats": _stats_dict(stats),
    }


def _stats_dict(s) -> dict | None:
    if s is None:
        return None
    return {
        "llm_calls": s.llm_calls,
        "cache_hits": s.cache_hits,
        "seconds": s.seconds,
        "router": s.router,
        "outline": s.outline,
        "warnings": list(s.warnings),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
