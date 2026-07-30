"""Dàn ý từ Knowledge Graph cho bước gộp cả buổi.

Phân vai giống FLOW_IMPLEMENTATION.md §10, và đây là điểm dễ hiểu nhầm nhất nên
nói rõ một lần:

    Qdrant  → NỘI DUNG. Đọc đủ 100% đoạn của buổi. Bắt buộc, không thay thế được.
    Neo4j   → DÀN Ý. Danh sách khái niệm và câu hỏi. Tuỳ chọn, chỉ để gợi ý.

KG KHÔNG phải nguồn thay thế cho Qdrant. Tóm tắt cần đủ lời giảng, mà graph chỉ
lưu khái niệm đã trích — dựng tóm tắt từ đó thì mất phần lớn nội dung. Vai của
graph là giúp bước gộp gọi tên khái niệm cho nhất quán và biết ý nào là ý xuyên
suốt cả buổi, chứ không cung cấp dữ kiện mới. Quy tắc 7 trong REDUCE_SYSTEM chặn
model lấy nội dung từ dàn ý, và validator vẫn đòi mọi ý phải có mã trích dẫn từ
tóm tắt mục — nên dù dàn ý có sai thì nó cũng không chui được vào bản tóm tắt.

Cypher dưới đây bám vào SCHEMA THẬT đang chạy trên Aura (806 node), không bám
vào FLOW_IMPLEMENTATION.md §2.3 — hai thứ lệch nhau ở ba chỗ đã kiểm chứng:

- `Lecture.id` là "01".."06", không phải "transcript_01" như doc viết.
- Quan hệ `HAS_QUESTION` KHÔNG tồn tại. `Question` chỉ nối với buổi qua thuộc
  tính `lecture_id`, nên phải lọc bằng thuộc tính chứ không đi theo cạnh.
- `Section.lecture_id` sai: cả 21 Section đều mang giá trị "06". Vì vậy mọi câu
  truy vấn ở đây định vị buổi bằng `Turn.id STARTS WITH 'T01-'` — mã đoạn là thứ
  đã đối chiếu được với Qdrant (T01: 89 Turn, khớp đúng 89 chunk), còn thuộc tính
  lecture_id trên Section thì không tin được.
"""

from __future__ import annotations

import functools
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent

# Tự nạp .env thay vì trông vào việc `summarizer.config` được import trước. Phụ
# thuộc thứ tự import là kiểu lỗi chỉ lộ ra khi ai đó đổi thứ tự dòng import, và
# lúc đó triệu chứng là "KG tự nhiên tắt" chứ không phải một lỗi đọc được.
load_dotenv(_ROOT / ".env")

# `graph_db` nằm ở src/ của gốc repo, không phải dependency của venv summarizer.
#
# APPEND chứ không insert(0): trong src/ còn có `vector_db/__init__.py` rỗng —
# một stub bỏ lại. Đặt src/ lên đầu sys.path thì stub đó che mất package
# `vector_db` thật đã cài từ ../vector-db, và loader Qdrant chết với lỗi
# "cannot import name 'session_reader'".
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

URL_KEYS = ("NEO4J_URL", "NEO4J_URI")   # Aura phát file credentials dùng tên URI
NEO4J_ENV = ("NEO4J_USERNAME", "NEO4J_PASSWORD")

# Bao nhiêu khái niệm/câu hỏi là đủ. Dàn ý dài quá thì nó cạnh tranh chú ý với
# chính phần tóm tắt mục — mà tóm tắt mục mới là nguồn.
MAX_CONCEPTS = 20
MAX_QUESTIONS = 8


@functools.lru_cache(maxsize=1)
def graph_available() -> tuple[bool, str]:
    """(dùng được chưa, lý do nếu chưa).

    lru_cache vì hàm này bị gọi mỗi lượt tóm tắt; mở lại kết nối mỗi lần thì UI
    đứng. Đổi .env xong phải khởi động lại app — chấp nhận được cho bản demo.
    """

    if not any(os.getenv(key) for key in URL_KEYS):
        return False, f"chưa có {' hoặc '.join(URL_KEYS)} trong .env"
    missing = [key for key in NEO4J_ENV if not os.getenv(key)]
    if missing:
        return False, f"chưa có {', '.join(missing)} trong .env"
    try:
        from graph_db import query
    except ImportError as error:
        return False, f"chưa import được graph_db ({error})"
    try:
        count = query("MATCH (n) RETURN count(n) AS n")[0]["n"]
    except Exception as error:  # noqa: BLE001 — mọi lỗi kết nối cùng dẫn tới một kết luận
        return False, f"không truy vấn được Neo4j ({type(error).__name__})"
    if not count:
        return False, "đã kết nối được nhưng graph còn rỗng"
    return True, ""


# Định vị buổi bằng `Lecture-[:INTRODUCES]->Concept`, KHÔNG bằng
# `Section-[:COVERS]->Concept`.
#
# Lý do là một lỗi dữ liệu trong graph: chỉ có 21 node Section mang id
# `section_01..section_21` và chúng DÙNG CHUNG cho cả 6 buổi — mỗi Section nối
# `BELONGS_TO` tới đủ 6 Lecture. Đi qua Section thì buổi nào cũng ra đúng một tập
# ~30 khái niệm giống hệt nhau, tức dàn ý vô dụng và còn sai lệch (T04 sẽ được
# gợi ý các khái niệm của T01). INTRODUCES thì đúng theo buổi: 01→5, 02→10,
# 03→10, 04→10, 05→8, 06→7 khái niệm.
#
# Khi nào người dựng KG đánh lại id Section theo từng buổi thì có thể quay lại
# đường COVERS để lấy khái niệm chi tiết hơn.

_Q_CONCEPTS = """
MATCH (l:Lecture {id: $lecture_id})-[:INTRODUCES]->(c:Concept)
RETURN DISTINCT c.name AS name, coalesce(c.frequency, 0) AS frequency
ORDER BY frequency DESC, name
LIMIT $limit
"""

_Q_RELATIONS = """
MATCH (l:Lecture {id: $lecture_id})-[:INTRODUCES]->(a:Concept)
MATCH (a)-[r:RELATED_TO]-(b:Concept)
RETURN DISTINCT a.name AS source, b.name AS target,
                coalesce(r.type, 'related') AS type
ORDER BY source, target
LIMIT $limit
"""

# Question KHÔNG có cạnh nối tới Turn — chỉ có thuộc tính `lecture_id` dạng "01".
# Đây là chỗ schema thật lệch doc, kiểm chứng bằng `MATCH ()-[r:HAS_QUESTION]->()`
# trả về 0.
_Q_QUESTIONS = """
MATCH (q:Question)
WHERE q.lecture_id = $lecture_id
RETURN DISTINCT q.text AS text
ORDER BY text
LIMIT $limit
"""


def outline_hint(session_id: str) -> tuple[str, str]:
    """Trả (dàn ý dạng text, ghi chú nếu không lấy được).

    Chuỗi rỗng nghĩa là bước gộp chạy y như trước khi có KG — không hỏng gì.
    """

    ok, why = graph_available()
    if not ok:
        return "", f"Knowledge graph {why} — bước gộp chạy không có dàn ý."

    from graph_db import query

    lecture_id = session_id.lstrip("Tt")  # "T01" -> "01", đúng dạng Lecture.id thật
    try:
        concepts = query(_Q_CONCEPTS, lecture_id=lecture_id, limit=MAX_CONCEPTS)
        relations = query(_Q_RELATIONS, lecture_id=lecture_id, limit=MAX_CONCEPTS)
        questions = query(_Q_QUESTIONS, lecture_id=lecture_id, limit=MAX_QUESTIONS)
    except Exception as error:  # noqa: BLE001 — dàn ý là tuỳ chọn, hỏng thì bỏ qua
        logger.warning("Không lấy được dàn ý từ graph: %s", error)
        return "", f"Truy vấn knowledge graph lỗi ({type(error).__name__}) — bỏ qua dàn ý."

    parts: list[str] = []
    if concepts:
        names = ", ".join(row["name"] for row in concepts if row.get("name"))
        if names:
            parts.append(f"Khái niệm xuất hiện trong buổi: {names}")
    if relations:
        lines = [
            f"- {row['source']} → {row['target']} ({row['type']})"
            for row in relations
            if row.get("source") and row.get("target")
        ]
        if lines:
            parts.append("Quan hệ giữa các khái niệm:\n" + "\n".join(lines))
    if questions:
        lines = [f"- {row['text']}" for row in questions if row.get("text")]
        if lines:
            parts.append("Câu hỏi nổi bật:\n" + "\n".join(lines))

    if not parts:
        return "", "Knowledge graph không có khái niệm nào cho buổi này."
    return "\n\n".join(parts), ""
