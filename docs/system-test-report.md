# Bao cao kiem thu toan he

## Lan 1 — truoc khi doi kien truc retrieve

**Ngay:** 2026-07-30 · **Commit:** afb202f0f3c79ef49fe2fe4fd13b288fffdd690e

| Package | Collect | Pass | Fail | Skip |
|---|---|---|---|---|
| flow1 | 284 | 276 | 0 | 8 |
| vector-db | 18 | 18 | 0 | 0 |
| summarizer | 56 | 56 | 0 | 0 |
| graph-db | 0 | 0 | 0 | 0 |
| scripts | 6 | 6 | 0 | 0 |

### Trang thai ha tang

- `scripts/check_env.py`: THIEU NEO4J_URL -> chet: graph-db
- Neo4j: [FAIL] RuntimeError: Thiếu biến môi trường: NEO4J_URL. Điền vào .env ở gốc repo (xem .env.example).
- Qdrant collection: vlearn_transcripts_openai_small_768_v1, 802 point
  (700 atomic + 96 section + 6 session_toc), 768 chieu — theo
  vector-db/artifacts/manifest.json

### Da hong truoc Task 1 (da sua)

- vector-db va summarizer khong collect noi test: moi package mot venv rieng.
- .env khai QDRANT_HOST/PORT nhung vector-db doc QDRANT_URL.

### Con do bay gio

khong co
