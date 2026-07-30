"""Viet lai cau hoi thanh ba dang, MOT loi goi model.

VI SAO BA DANG: moi retriever manh o mot dang dau vao khac nhau. BM25 an tu
khoa (va can dong nghia Viet-Anh vi bai giang lan ca hai). Vector an cau tu
nhien day du. KG an ten khai niem de khop vao Concept.name. Dua cung mot chuoi
cho ca ba la phi it nhat hai cai.

KHONG BAO GIO NEM: hong o day khong duoc lam chet ca truy van. Loi gi cung lui
ve passthrough (nguyen cau hoi vao ca ba truong) va ghi ly do vao trace — ket
qua kem hon nhung van co ket qua.
"""

from __future__ import annotations

from flow1.prompts import REWRITE_SYSTEM, rewrite_user
from flow1.retrievers import RewrittenQuery


def _default_call(system, user_blocks, schema):
    from summarizer.llm import OpenAIStructuredLLM

    user = "\n\n".join(b["text"] for b in user_blocks if b["type"] == "text")
    return OpenAIStructuredLLM().parse(
        model="gpt-4o-mini",
        system=system,
        user=user,
        schema=schema,
        temperature=0.0,
    )


def rewrite_query(question: str, *, call=None, trace=None) -> RewrittenQuery:
    """Mot call -> ba dang. Hong thi lui ve passthrough, khong nem."""
    from flow1.trace import NullTrace

    trace = trace if trace is not None else NullTrace(question)
    lui = RewrittenQuery.passthrough(question)

    with trace.stage("rewrite") as tdata:
        tdata["goc"] = question

        call = call if call is not None else _default_call

        # Moi loi deu bat o day, ke ca ImportError khi thieu package provider:
        # `_default_call` import ben trong than ham nen loi nap chi noi len o
        # day chu khong o cho gan `call`.
        try:
            got = call(
                REWRITE_SYSTEM,
                [{"type": "text", "text": rewrite_user(question)}],
                RewrittenQuery,
            )
        except Exception as exc:
            tdata["da_lui"] = f"{type(exc).__name__}: {exc}"
            return lui

        if not isinstance(got, RewrittenQuery):
            tdata["da_lui"] = f"model tra ve {type(got).__name__}, khong phai RewrittenQuery"
            return lui

        # keywords rong lam BM25 tra rong, ma BM25 la nguon so lieu cua cong 1.
        if not got.keywords or not got.cau_hoi.strip():
            tdata["da_lui"] = "model tra thieu keywords hoac cau_hoi"
            return lui

        tdata["keywords"] = got.keywords
        tdata["cau_hoi"] = got.cau_hoi
        tdata["thuc_the"] = got.thuc_the
        return got
