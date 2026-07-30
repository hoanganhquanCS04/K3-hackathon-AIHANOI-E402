"""Kết nối Neo4j.

Driver của Neo4j đã thread-safe và tự quản connection pool, nên tạo ĐÚNG MỘT lần
cho cả process rồi dùng lại. Tạo driver mới mỗi query là lỗi phổ biến nhất — nó
làm cạn socket và chậm gấp nhiều lần.
"""

from __future__ import annotations

import atexit
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

_REQUIRED = ("NEO4J_USERNAME", "NEO4J_PASSWORD")

# Aura copy sẵn biến tên `NEO4J_URI` vào file credentials nó cho tải về, còn file
# này ban đầu đòi `NEO4J_URL`. Chấp nhận cả hai thay vì bắt mỗi người sửa .env —
# lệch một chữ mà lỗi báo ra là "thiếu biến môi trường" thì rất mất thời gian dò.
_URL_KEYS = ("NEO4J_URL", "NEO4J_URI")


def _read_env() -> tuple[str, str, str]:
    url = next((os.environ[k] for k in _URL_KEYS if os.getenv(k)), None)
    missing = [k for k in _REQUIRED if not os.getenv(k)]
    if url is None:
        missing.insert(0, "NEO4J_URL (hoặc NEO4J_URI)")
    if missing:
        raise RuntimeError(
            f"Thiếu biến môi trường: {', '.join(missing)}. "
            "Điền vào .env ở gốc repo (xem .env.example)."
        )
    return url, os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]


@lru_cache(maxsize=1)
def get_driver() -> Any:
    """Driver dùng chung. verify_connectivity() để sai URL/mật khẩu là báo ngay tại đây,
    không phải đợi đến câu Cypher đầu tiên mới lộ."""
    url, user, password = _read_env()
    driver = GraphDatabase.driver(url, auth=(user, password))
    driver.verify_connectivity()
    atexit.register(driver.close)
    return driver


def get_database() -> str:
    """Instance của nhóm dùng chính mã instance làm tên database (`6a80f29b`), KHÔNG
    phải `neo4j` — hỏi `neo4j` trên đó là lỗi DatabaseNotFound. Nên luôn đặt
    `NEO4J_DATABASE` trong .env; `neo4j` chỉ là mặc định cho Aura Free."""
    return os.getenv("NEO4J_DATABASE") or "neo4j"


def query(cypher: str, **params) -> list[dict]:
    """Chạy một câu Cypher, trả list dict.

    execute_query() tự mở/đóng session, tự retry khi transient error và tự chọn
    routing read/write. Luôn truyền dữ liệu qua `params`, không nối chuỗi vào Cypher.
    """
    records, _summary, _keys = get_driver().execute_query(
        cypher,
        parameters_=params,
        database_=get_database(),
    )
    return [record.data() for record in records]
