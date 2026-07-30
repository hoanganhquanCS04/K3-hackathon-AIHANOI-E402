# Hiệu chỉnh ngưỡng T1 — bảng phân bố 30 câu

- Số câu: 30 (20 trong phạm vi · 10 ngoài phạm vi)
- Câu lấy thật từ chatlog: 26
- Câu do người soạn (đã kiểm grep không có trong 6 buổi): 4

> Điểm dưới đây là điểm BM25 THÔ. Cổng 1 luôn quyết định trên điểm thô, không
> trên điểm RRF đã fuse — nên bảng này vẫn có hiệu lực khi bật embedding.

## Phân bố từng câu

| id | expect | top1_abs | ratio | buổi | section top-1 | source |
|---|---|---|---|---|---|---|
| Q01 | in_scope | 74.26 | 3.25 | 01 | Mô hình Double Diamond: làm đúng c | chatlog:T0474 |
| Q02 | in_scope | 72.40 | 3.21 | 01 | Mô hình Double Diamond: làm đúng c | chatlog:T0889 |
| Q03 | in_scope | 44.54 | 3.54 | 01 | Tri thức ẩn của chuyên gia và việc | chatlog:T0920 |
| Q04 | in_scope | 37.21 | 1.36 | 04 | Attention, multi-head và bài học q | chatlog:T0966 |
| Q05 | in_scope | 34.06 | 1.21 | 06 | AI, machine learning, deep learnin | chatlog:T0315 |
| Q06 | in_scope | 32.20 | 1.31 | 04 | Attention, multi-head và bài học q | chatlog:T0068 |
| Q07 | in_scope | 31.98 | 1.53 | 04 | AlphaGo và kiến trúc Transformer | chatlog:T0422 |
| Q08 | in_scope | 29.90 | 1.18 | 05 | Làm việc với AI: đừng để não quá t | chatlog:T0741 |
| Q09 | in_scope | 29.78 | 1.32 | 06 | AI, machine learning, deep learnin | chatlog:T0914 |
| Q10 | in_scope | 29.30 | 1.24 | 04 | Attention, multi-head và bài học q | chatlog:T0985 |
| Q11 | in_scope | 28.82 | 2.42 | 01 | Ma trận tác động – nỗ lực (impact- | chatlog:T0807 |
| Q12 | in_scope | 27.81 | 1.43 | 04 | Attention, multi-head và bài học q | chatlog:T0257 |
| Q13 | in_scope | 27.78 | 1.19 | 01 | Bài tập: bài toán trợ giảng cho lớ | chatlog:T0907 |
| Q14 | in_scope | 27.19 | 1.10 | 06 | Ba nhóm AI và lịch sử phát triển | chatlog:T0180 |
| Q15 | in_scope | 27.05 | 1.74 | 06 | Self-attention: ví dụ "con mèo ngồ | chatlog:T0312 |
| Q16 | in_scope | 26.98 | 1.12 | 04 | Lịch sử AI: Turing test và hai mùa | chatlog:T1238 |
| Q17 | in_scope | 25.92 | 1.28 | 04 | Chọn mô hình phù hợp với công việc | chatlog:T0633 |
| Q18 | in_scope | 25.92 | 1.46 | 04 | Attention, multi-head và bài học q | chatlog:T1060 |
| Q19 | in_scope | 25.64 | 1.34 | 04 | Attention, multi-head và bài học q | chatlog:T1202 |
| Q20 | in_scope | 25.61 | 1.25 | 05 | Ba mức độ giải pháp: script — LLM  | chatlog:T0570 |
| Q25 | out_of_scope | 40.84 | 1.40 | 03 | Scope, chi phí và đạo đức nghề ngh | chatlog:T0470 |
| Q24 | out_of_scope | 19.61 | 1.13 | 05 | Chọn kiến trúc cho giải pháp AI: c | chatlog:T0148 |
| Q22 | out_of_scope | 17.87 | 1.14 | 04 | Cuộc đua AI sau ChatGPT | chatlog:T0664 |
| Q26 | out_of_scope | 17.17 | 1.11 | 03 | Bài toán sinh đề toán tự động — ý  | chatlog:T0837 |
| Q21 | out_of_scope | 13.01 | 1.19 | 05 | Hỏi đáp về xe tự lái | chatlog:T0733 |
| Q29 | out_of_scope | 8.69 | 1.09 | 02 | Chỉ số thành công và đo lường sản  | người soạn |
| Q28 | out_of_scope | 8.34 | 1.20 | 03 | Fine-tuning hay RAG — và cách thuy | người soạn |
| Q30 | out_of_scope | 8.12 | 1.14 | 06 | Ba nhóm AI và lịch sử phát triển | người soạn |
| Q23 | out_of_scope | 7.96 | 1.24 | 04 | AlphaGo và kiến trúc Transformer | chatlog:T1237 |
| Q27 | out_of_scope | 4.60 | 1.10 | 01 | Phát triển sản phẩm AI có gì khác | người soạn |

## Ma trận ngưỡng — (chặn ngoài-phạm-vi / qua trong-phạm-vi)

| T1_ABS ↓ / T1_RATIO → | 1.00 | 1.10 | 1.20 | 1.30 | 1.40 | 1.50 | 1.75 | 2.00 |
|---|---|---|---|---|---|---|---|---|
| **0.0** | 0/20 | 1/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **2.0** | 0/20 | 1/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **3.0** | 0/20 | 1/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **4.0** | 0/20 | 1/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **5.0** | 1/20 | 2/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **6.0** | 1/20 | 2/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **7.0** | 1/20 | 2/19 | 8/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **8.0** | 2/20 | 3/19 | 9/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **10.0** | 5/20 | 5/19 | 9/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |
| **12.0** | 5/20 | 5/19 | 9/16 | 9/12 | 10/8 | 10/6 | 10/4 | 10/4 |

## Cặp đề xuất

- `T1_ABS = 0.00` · `T1_RATIO = 1.40`
- Chặn **10/10** câu ngoài phạm vi · cho qua **8/20** câu trong phạm vi

Hai phân bố tách được. Ở cặp này 10/10 câu ngoài phạm vi bị chặn và 8/20 câu trong phạm vi vẫn qua.

## Cách kiểm lại

```
cd codebase && PYTHONUTF8=1 ../.venv/Scripts/python.exe scripts/calibrate_t1.py
```
