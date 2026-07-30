# Báo cáo kiểm thử toàn hệ

## Lần 1 — trước khi đổi kiến trúc retrieve

**Ngày:** 2026-07-30 · **Commit:** `afb202f0f3c79ef49fe2fe4fd13b288fffdd690e`

| Package | Collect | Pass | Fail | Skip |
|---|---|---|---|---|
| flow1 | 284 | 276 | 0 | 8 |
| vector-db | 18 | 18 | 0 | 0 |
| summarizer | 56 | 56 | 0 | 0 |
| graph-db | 0 | 0 | 0 | 0 |
| scripts | 6 | 6 | 0 | 0 |

## Lần 2 — sau khi hoàn thành 3 nhánh retrieve, agent tool-calling và Streamlit

**Ngày:** 2026-07-30 · **Commit:** HEAD

| Package | Collect | Pass | Fail | Skip |
|---|---|---|---|---|
| flow1 | 338 | 330 | 0 | 8 |
| vector-db | 22 | 22 | 0 | 0 |
| summarizer | 56 | 56 | 0 | 0 |
| graph-db | 8 | 8 | 0 | 0 |
| **Tổng cộng** | **424** | **416** | **0** | **8** |

### Trạng thái hạ tầng

- `scripts/check_env.py`: OK
- Qdrant: Collection `vlearn_transcripts_openai_small_768_v1`, 802 point (700 atomic + 96 section + 6 session_toc), 768 chiều.
- Neo4j Aura: Sẵn sàng schema v4 (Constraints, Indexes và Full-text Index `concept_name_ft`).
- Fallback logic: Hệ thống hạ cấp êm (graceful degradation) sang `NullRetriever` nếu dịch vụ đám mây tạm gián đoạn.

### Các vết trace mẫu kiểm chứng (Trace Samples)

- `eval/traces/trace-01-tra-cuu-thanh-cong.json`: Tra cứu thành công qua RRF 3 nhánh.
- `eval/traces/trace-02-hoi-lai-buoi.json`: Cổng 1 phát hiện câu hỏi đa buổi mơ hồ.
- `eval/traces/trace-03-ngoai-pham-vi.json`: Rule-based gate 0 chặn câu ngoài phạm vi (0 token).
- `eval/traces/trace-04-tom-tat.json`: Agent chọn tool `tom_tat` tra cứu sổ tay buổi.
