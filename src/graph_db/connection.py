"""Kết nối Neo4j.

Driver của Neo4j đã thread-safe và tự quản connection pool, nên tạo ĐÚNG MỘT lần
cho cả process rồi dùng lại. Tạo driver mới mỗi query là lỗi phổ biến nhất — nó
làm cạn socket và chậm gấp nhiều lần.
"""

from __future__ import annotations

import atexit
import os
from functools import lru_cache

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

load_dotenv()

_REQUIRED = ("NEO4J_URL", "NEO4J_USERNAME", "NEO4J_PASSWORD")


def _read_env() -> tuple[str, str, str]:
    missing = [k for k in _REQUIRED if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Thiếu biến môi trường: {', '.join(missing)}. "
            "Điền vào .env ở gốc repo (xem .env.example)."
        )
    return os.environ["NEO4J_URL"], os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]


@lru_cache(maxsize=1)
def get_driver() -> Driver:
    """Driver dùng chung. verify_connectivity() để sai URL/mật khẩu là báo ngay tại đây,
    không phải đợi đến câu Cypher đầu tiên mới lộ."""
    url, user, password = _read_env()
    driver = GraphDatabase.driver(url, auth=(user, password))
    driver.verify_connectivity()
    atexit.register(driver.close)
    return driver


def get_database() -> str:
    """Aura Free chỉ có một database tên `neo4j` — không phải tên instance bạn đặt."""
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
