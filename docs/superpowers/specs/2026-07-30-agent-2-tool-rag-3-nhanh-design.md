# Agent 2 tool + RAG 3 nhánh — thiết kế

**Ngày:** 2026-07-30 · **Nhánh:** `so-tay-buoi-hoc`
**Thay thế:** §7 của `2026-07-30-hybrid-rag-tai-co-cau-design.md` (mục đó lập luận Neo4j nên nằm ngoài luồng — **quyết định đó đã bị đảo**). Mọi phần khác của spec đó còn hiệu lực.
**Đã thi công theo spec cũ:** Task 1 (uv workspace, 4 package) và Task 2 (thống nhất biến môi trường) — cả hai là nền, không phụ thuộc kiến trúc retrieve, giữ nguyên.

---

## 1. Vì sao đảo quyết định

Spec cũ để Neo4j ngoài luồng với ba lý do: concept do LLM sinh nên phá chiều truy vết · luồng 2 nạp trọn buổi nên không thiếu gì để graph tìm hộ · chỗ graph mạnh nhất là tóm tắt đa buổi thì non-goal cấm.

Yêu cầu mới thay đổi tiền đề của lý do thứ nhất và thứ hai:

- KG **không** được dùng làm nguồn khẳng định. Nó chỉ dùng để **tìm đường tới Turn**. Mọi nội dung vào prompt vẫn là nguyên văn Turn thật, cổng 3 vẫn đối chiếu mã với 700 đoạn gốc. KG mở rộng *recall*, không mở rộng *thẩm quyền* — nên lý do 1 không còn áp dụng.
- KG cắm vào **luồng 1 (tra cứu)**, không phải luồng 2. Luồng 2 vẫn nạp trọn buổi. Lý do 2 nói về luồng 2 nên không chạm tới thay đổi này.
- Lý do 3 vẫn đúng và vẫn được tôn trọng: không tóm tắt đa buổi.

---

## 2. Kiến trúc

```
câu hỏi
   │
   ▼ CỔNG RULE (tất định, tái dùng gate0)
   │   chào hỏi · logistics · ngoài phạm vi · jailbreak → khuôn mẫu, DỪNG, 0 token
   ▼
   ▼ AGENT — tool-calling
   │   tra_cuu(query, session?)   |   tom_tat(session_id)
   │
   ├──► TOOL 1: tra_cuu
   │      ▼ VIẾT LẠI QUERY — 1 LLM call → JSON 3 trường
   │      │    {keywords: [...], cau_hoi: "...", thuc_the: [...]}
   │      │
   │      ├─► BM25(keywords)    → [(mã đoạn, điểm thô)]      [toggle]
   │      ├─► Qdrant(cau_hoi)   → [(mã đoạn, cosine)]        [toggle]
   │      └─► Neo4j(thuc_the)   → [(mã đoạn, hạng graph)]    [toggle]
   │      │
   │      ▼ RRF trên MÃ ĐOẠN — chỉ các nhánh đang bật
   │      ▼ CỔNG 1 trên BM25 thô → từ chối / hỏi lại / qua
   │      ▼ nở lên chunk ngữ cảnh
   │      ▼ CỔNG 2 generate JSON có status
   │      ▼ CỔNG 3 citation_validator
   │
   └──► TOOL 2: tom_tat(session_id) → summarizer map-reduce (có cache)
```

**Khoá nối ba nhánh vẫn là mã đoạn `Txx-NNN`.** Neo4j có `Turn {id: "T01-001"}` — đúng khoá đó. Ba nhánh fuse được mà không cần lớp ánh xạ nào, và mọi mã KG trả về vẫn qua được cổng 3.

---

## 3. Quyết định

| # | Quyết định | Phương án bị loại và vì sao |
|---|---|---|
| Q1 | KG: khớp Concept qua full-text → lan ra Turn qua `COVERS`/`BELONGS_TO`, cộng `RELATED_TO` 1-2 hop | *LLM sinh Cypher*: thêm một lời gọi LLM mỗi truy vấn, Cypher sai khó debug, khó test offline. *Chỉ dùng quan hệ cấu trúc, bỏ Concept*: an toàn nhưng gần như không thêm gì so với đọc `segments.jsonl`. |
| Q2 | Agent tool-calling thật, có **rule tất định chặn trước** | *Router tất định thuần*: rẻ hơn nhưng không xử được câu cần cả hai tool. *Tool-calling thuần, bỏ rule*: mỗi câu rác tốn một lời gọi model, và mất lớp chặn tất định mà 4 cổng đang dựa vào. |
| Q3 | Viết lại query: **1 call → 3 dạng**, mỗi retriever một dạng | *Một query duy nhất*: không khai thác được thế mạnh riêng từng nhánh. *Multi-query 3-5 biến thể*: recall cao hơn nhưng nhân số lần retrieve lên 3-5 và bảng trace không đọc nổi — ngược mục tiêu dễ debug. |
| Q4 | Tool 2 bọc package `summarizer` đã có | *Tóm theo kết quả retrieve*: bỏ không dùng toàn bộ `summarizer/` đã xây. |
| Q5 | UI: 3 checkbox + bảng so sánh từng nhánh | *Chỉ checkbox*: muốn biết nhánh nào đóng góp gì phải mở trace đọc tay. *Thêm nút chạy cả 8 tổ hợp*: 8 lần retrieve mỗi lần bấm, mỗi lần tốn API embed. |

---

## 4. Nhánh KG

`ingest_transcripts.py` đã tạo index `concept_name_idx` trên `Concept.name`. Bước ingest bổ sung thêm một full-text index:

```cypher
CREATE FULLTEXT INDEX concept_name_ft IF NOT EXISTS FOR (c:Concept) ON EACH [c.name, c.name_en]
```

Truy vấn:

```cypher
CALL db.index.fulltext.queryNodes('concept_name_ft', $thuc_the) YIELD node AS c, score
MATCH (c)<-[:COVERS]-(s:Section)<-[:BELONGS_TO]-(t:Turn)
WHERE t.is_activity = false
RETURN t.id AS ma, score AS diem, 0 AS hop
UNION
CALL db.index.fulltext.queryNodes('concept_name_ft', $thuc_the) YIELD node AS c, score
MATCH (c)-[:RELATED_TO*1..2]-(:Concept)<-[:COVERS]-(s:Section)<-[:BELONGS_TO]-(t:Turn)
WHERE t.is_activity = false
RETURN t.id AS ma, score * 0.5 AS diem, 1 AS hop
```

Xếp theo `(hop, -diem)`, dedupe theo `ma`, giữ lần xuất hiện đầu. **RRF chỉ cần thứ hạng**, không cần điểm cùng thang — nên không phải chuẩn hoá gì giữa ba nhánh.

---

## 5. Ba bất biến dễ sai

### 5.1 Tắt BM25 KHÔNG tắt cổng 1

BM25 **luôn chạy** — nó offline, dưới 1ms, và cổng 1 cần điểm thô của nó để quyết định có đủ căn cứ hay không. Toggle chỉ điều khiển **BM25 có góp vào fusion hay không**.

Nếu toggle tắt luôn cổng 1 thì bật "chỉ Qdrant" để đo sẽ vô tình tắt mất lớp từ chối — đúng thứ cả sản phẩm đang phòng. UI và trace phải in rõ dòng này khi BM25 bị tắt khỏi fusion.

### 5.2 T1 hiệu chỉnh ở CUỐI, sau khi pipeline hoàn chỉnh

Có **hai** thứ dịch phân bố điểm BM25 so với lần hiệu chỉnh trước: đổi sang đơn vị nguyên tử, và BM25 nhận `keywords` đã viết lại thay vì câu hỏi thô. Hiệu chỉnh trước khi có bước viết lại query là đo sai thứ sẽ chạy thật.

Giữ nguyên luật trung thực: nếu ma trận ngưỡng mới không tách được hai phân bố thì ghi thật và dừng lại báo, **không nới ngưỡng cho đẹp số**.

### 5.3 KG mở rộng recall, không mở rộng thẩm quyền

Node `Concept` là phán đoán của model lúc ingest. Nó chỉ được dùng để tìm đường tới Turn. Không một chữ nào của `Concept.description` được đưa vào prompt sinh câu trả lời.

---

## 6. Rủi ro đã biết

- **Neo4j không kết nối được lúc viết spec này** (`ServiceUnavailable — Unable to retrieve routing information`). Aura Free tự tạm dừng instance sau vài ngày không dùng. Cần resume trước khi kiểm được nhánh KG thật.
- **Chưa biết graph có dữ liệu chưa.** Nếu rỗng thì phải chạy `ingest_transcripts.py` cho 6 buổi, script đó gọi LLM trích concept — tốn tiền và cần soát chất lượng concept trước khi tin.
- Không thứ nào trong hai thứ trên chặn phần còn lại: `Neo4jRetriever` lùi êm về rỗng như `NullRetriever`, và test dùng graph giả.

---

## 7. Định nghĩa "xong"

| # | Điều kiện |
|---|---|
| 1 | `uv run pytest` xanh, **không cần API key nào** |
| 2 | Agent chọn đúng tool cho: câu hỏi nội dung → `tra_cuu`; "tóm tắt buổi 3" → `tom_tat` |
| 3 | Rule tất định chặn chào hỏi/logistics/ngoài phạm vi **trước** khi tới agent, 0 lời gọi model |
| 4 | Viết lại query trả đủ 3 trường, trace ghi cả query gốc lẫn 3 dạng |
| 5 | Tắt từng nhánh trên UI thì kết quả đổi theo, và bảng so sánh chỉ ra đoạn nào **chỉ** nhánh đó tìm ra |
| 6 | Tắt BM25 khỏi fusion thì cổng 1 **vẫn** hoạt động, UI nói rõ điều đó |
| 7 | Neo4j chết → `tra_cuu` vẫn trả lời bằng 2 nhánh còn lại, trace ghi lý do |
| 8 | Mọi mã đoạn KG trả về đều qua được cổng 3 (tồn tại trong 700 đoạn thật) |
| 9 | T1 hiệu chỉnh lại trên pipeline hoàn chỉnh, bảng cũ giữ lại |
| 10 | `docs/system-test-report.md` có trước và sau; trace mẫu trong `eval/traces/` |
