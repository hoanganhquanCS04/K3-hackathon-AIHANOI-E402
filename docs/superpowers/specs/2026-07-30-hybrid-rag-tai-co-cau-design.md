# Hybrid RAG + tái cơ cấu repo + trace debug — thiết kế

**Ngày:** 2026-07-30 · **Nhánh:** `so-tay-buoi-hoc`
**Quan hệ với file khác:** mở rộng `canvas-va-luong-du-lieu.md` ở đúng một điểm — §4.3 để ngỏ "CP3 nếu kịp: thêm embedding, hợp nhất điểm với BM25". File này chốt việc đó bằng số và bằng đường code. Mọi phần khác của canvas giữ nguyên.

---

## 1. Làm gì trong đợt này

Ba việc, theo yêu cầu:

1. **Kiểm thử toàn bộ hệ thống** — hiện chỉ 1 trong 3 package chạy được test.
2. **Tái cơ cấu thư mục + thêm trace debug** — cho dễ debug và cải tiến.
3. **Đổi retrieve từ BM25 thuần sang hybrid BM25 × semantic**, dùng vector database có metadata đầy đủ.

**Không làm trong đợt này:** nối Neo4j/knowledge graph vào luồng RAG hay luồng tóm tắt (lý do ở §7).

---

## 2. Hiện trạng đã kiểm chứng

Repo có **ba pipeline song song, không nối với nhau**:

| Khối | Trạng thái | Test |
|---|---|---|
| `codebase/` (flow1) | parse→chunk→index BM25→retrieve→gates→ask→render + Streamlit. `store/bm25.pkl` đã build, **419 chunk** | **276 pass, 8 skip** |
| `vector-db/` | Collection `vlearn_transcripts_openai_small_768_v1` **đã build**: 802 point (700 atomic + 96 section + 6 session_toc), 9 payload index, manifest + eval hit@5 = 1.0 / recall@5 = 0.93 | **6 file lỗi collect** |
| `summarizer/` | map-reduce, artifact T01–T04 đã sinh | **lỗi collect** |

Hai package sau không collect nổi test vì deps không nằm trong venv gốc — mỗi package một môi trường riêng, không có workspace.

**Rác kiến trúc:** `src/` (1 file thật + 1 file rỗng), `neo4j/` (1 file 656 dòng + 1 file import chết), `scripts/` (3 script ad-hoc), `requirements.txt` ở gốc (llama-index — không ai import), `PROJECT_STRUCTURE.md` (mô tả `src/ingestion/`, `src/retrieval/` — không tồn tại).

**Ba bộ tên biến môi trường đá nhau** (§4.2). Hệ quả nặng nhất: `.env` hiện tại **không có `QDRANT_URL`**, nên `vector-db` chết ngay ở config. Collection build được là nhờ cache embedding (`manifest.json`: `api_requests: 0, cache_hits: 706`).

**Hybrid đã có sẵn khung, chưa bật:** `codebase/flow1/retrieve.py` đã có nhánh RRF, `embed.py` đã có `build_embeddings`/`rrf` (dùng `multilingual-e5-small` local). Chưa có `emb.npy` nên đang chạy BM25 thuần.

---

## 3. Quyết định kiến trúc

| # | Quyết định | Phương án bị loại và vì sao |
|---|---|---|
| Q1 | Nhánh semantic lấy vector từ **Qdrant** (`vector-db`) | *e5 local + `emb.npy`*: chạy offline, RRF dùng được ngay, nhưng `.npy` không phải "vector database có metadata", và collection 802 point đã build + đã eval sẽ nằm chết. |
| Q2 | BM25 và vector cùng index **700 đoạn nguyên tử**, nở lên chunk gộp khi nạp context | *Giữ 419 chunk gộp, re-embed*: tốn tiền API và gửi lại ~445k ký tự ra ngoài. *Index hai tầng, fuse qua lớp map*: thêm một lớp ánh xạ phải nuôi tay — đúng loại code khó debug mà đợt này đang muốn giảm. |
| Q3 | **uv workspace**, giữ 4 package tách biệt | *Monorepo một package*: sạch nhất nhưng mọi đường import đổi → nhánh đang mở của thành viên khác conflict nặng, và CP5 mỗi người khó chỉ "file của tôi". |
| Q4 | Debug bằng **trace record theo stage** + `--trace` | *Chỉ logging theo `LOG_LEVEL`*: log dòng rời rạc, muốn biết "vì sao câu này bị cổng 1 chặn" phải đọc chéo nhiều dòng, và không dùng lại được cho eval. |
| Q5 | Test **offline mặc định + marker `live`** | *Chạy thật toàn bộ*: tốn tiền mỗi lần chạy, vỡ khi mạng hỏng, người không có key không chạy được test nào. |
| Q6 | Neo4j **sửa cho chạy được, để ngoài luồng** | *Nối KG vào RAG/tóm tắt*: §7. *Xoá hẳn*: mất 656 dòng ingest đã viết. |

---

## 4. Cấu trúc repo

### 4.1 uv workspace, 4 member

```
pyproject.toml              MỚI — [tool.uv.workspace] members
.env.example                viết lại theo tên biến code THẬT SỰ đọc
scripts/check_env.py        MỚI — soát .env, in đúng biến thiếu + package nào chết vì nó
                            (thư mục scripts/ ở gốc CHỈ còn file này)

flow1/                      đổi tên từ codebase/, chuyển sang src-layout
├── pyproject.toml          name = "flow1"
├── src/flow1/              parse chunk index retrieve embed gates ask check render cli trace
├── app/                    app.py live.py theme.py stubs.py  (Streamlit)
├── scripts/calibrate_t1.py chuyển từ codebase/scripts/
├── tools/build_outline.py  chuyển từ codebase/tools/
└── tests/

vector-db/                  nới chữ ký find_chunks (§5.4)
├── src/vector_db/
├── scripts/                nhận test_qdrant.py + test_exist_collection.py từ scripts/ gốc
└── tests/

summarizer/                 giữ nguyên
graph-db/                   gom src/graph_db/ + neo4j/, sửa cho chạy được, ngoài luồng
├── pyproject.toml
├── src/graph_db/
└── scripts/                ingest_transcripts.py · query_neo4j.py · check_neo4j.py
```

Ba script ad-hoc ở `scripts/` gốc tách theo đúng thứ chúng chạm tới: hai script Qdrant về `vector-db/scripts/`, script Neo4j về `graph-db/scripts/`.

**Vì sao src-layout cho `flow1/`:** import vẫn là `from flow1.parse import ...`, y hệt hiện nay → **276 test đang xanh không phải sửa một dòng**. Đổi thẳng `codebase/` → `flow1/` không được vì bên trong đã có package tên `flow1` (sẽ thành `flow1/flow1/`). Sau đổi, cả 4 member cùng khuôn `X/src/x/` + `X/tests/`.

**Xoá:** `PROJECT_STRUCTURE.md`, `requirements.txt` ở gốc.
**Giữ có điều kiện:** `docs/FLOW_IMPLEMENTATION.md` — thêm banner đầu file *"tầm nhìn, chưa phải kiến trúc đang chạy"*, và sửa `1536 dimensions` thành **768** cho khớp collection đã build.

Kết quả nghiệm thu: `uv run pytest` ở gốc chạy cả 4 member trong một venv.

### 4.2 Thống nhất biến môi trường

Chốt theo **tên code đang đọc** — sửa `.env` rẻ hơn sửa code đã có test.

| Biến chuẩn | Ai đọc | `.env` hiện tại | Việc |
|---|---|---|---|
| `QDRANT_URL` | `vector-db/config.py`, `vector-db/scripts/test_qdrant.py` | thiếu (có `QDRANT_HOST`+`QDRANT_PORT`) | thêm; **bỏ** HOST/PORT |
| `QDRANT_COLLECTION` | `vector-db/scripts/test_exist_collection.py` | thiếu | thêm, `vlearn_transcripts_openai_small_768_v1` |
| `OPENAI_EMBEDDING_DIMENSIONS` | `vector-db/config.py` | thiếu (có `QDRANT_VECTOR_DIM`) | đổi tên, giá trị **768** |
| `NEO4J_URL` | `src/graph_db/connection.py` | `NEO4J_URI` | chốt `NEO4J_URL` |

**Bỏ khỏi `.env.example`** các biến không ai đọc — tàn dư kế hoạch llama-index, để lại là đánh bẫy người sau: `OPENAI_MODEL`, `QDRANT_CHILD_CHUNKS_COLLECTION`, `QDRANT_PARENT_CHUNKS_COLLECTION`, `PARENT_CHUNK_SIZE`, `DEFAULT_TOP_K`, `MAX_RETRIEVAL_RESULTS`, `LOG_FILE`, `DATA_DIR`, `CACHE_DIR`.

---

## 5. Hybrid retrieval

### 5.1 Khoá nối hai retriever = mã đoạn

Hai retriever nối nhau bằng **mã đoạn `Txx-NNN`**, không bằng chỉ số mảng (mỗi bên một tập khác nhau). Mã đoạn vốn đã là danh tính nguyên tử của cả hệ: `Seg.code` ở flow1, `citation_id` trong payload Qdrant, và là thứ `check.py` đối chiếu ở cổng 3. Không phát sinh lớp ánh xạ phải nuôi bằng tay.

```
                    câu hỏi
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
   BM25 offline                  Qdrant atomic_chunk
   700 đoạn nguyên tử            filter point_type + is_activity
   → [T03-014, T03-015, ...]     → [T03-015, T01-088, ...]
   + ĐIỂM THÔ  ─────┐                     │
        └───────────┼─────────────────────┘
                    │            ▼
                    │     RRF trên mã đoạn → thứ tự nạp context
                    │
                    ▼
             gate_stats(điểm BM25 thô) → top1_abs, ratio → CỔNG 1
```

**Bất biến giữ nguyên từ `retrieve.py` hiện tại:** cổng 1 luôn quyết định trên **điểm BM25 thô**, không bao giờ trên điểm RRF. Điểm RRF là `1/(K+rank)` — dãy gần như cố định, `ratio` sau fuse luôn ≈ 1,02 bất kể câu hỏi, cổng 1 sẽ chết im lặng đúng lúc bật hybrid. Nhờ bất biến này, nhánh vector chỉ đổi *thứ tự nạp chunk vào context*, không đổi *có đủ căn cứ hay không* — tắt Qdrant đi hệ vẫn từ chối đúng như cũ.

### 5.2 Đơn vị index vs đơn vị context — hai vai, không lẫn

| | Đơn vị | Ai dùng |
|---|---|---|
| **Index** | 700 đoạn nguyên tử | BM25 + Qdrant xếp hạng |
| **Context** | 419 chunk gộp hiện có | nạp vào prompt cổng 2 |

Sau khi RRF ra thứ tự mã đoạn, mỗi mã nở ra chunk gộp chứa nó, dedupe, giữ thứ tự theo mã tốt nhất trong chunk. Map `code → chunk_id` **dẫn xuất** từ `Chunk.seg_codes` lúc build index — không phải file phải bảo trì.

Cái được: retrieve chính xác ở mức đoạn, model vẫn thấy đủ ngữ cảnh xung quanh, và luật chunk §4.2 của canvas cùng `chunk.py` với test của nó còn nguyên giá trị — chỉ đổi vai từ "đơn vị index" sang "cửa sổ ngữ cảnh".

Qdrant còn 96 `section_parent` nếu sau này muốn ngữ cảnh rộng hơn; mặc định dùng chunk gộp của flow1 vì cả section ở buổi dài là quá lớn.

### 5.3 Hệ quả bắt buộc: hiệu chỉnh lại T1

BM25 chuyển từ 419 chunk gộp sang 700 đoạn nguyên tử → độ dài trung bình và `idf` đều đổi → phân bố điểm đổi. **`T1_RATIO = 1.20` hết hiệu lực.**

- Chạy lại `flow1/scripts/calibrate_t1.py` trên đúng 30 câu cũ ở `eval/t1/questions.jsonl`.
- Cập nhật `thresholds.py` và `eval/t1/distribution.md` **trong cùng một commit** — đúng luật file `thresholds.py` tự ghi.
- Giữ bảng phân bố cũ trong `distribution.md` dưới mục *"trước khi đổi sang đơn vị nguyên tử"*: bằng chứng cho phương án bị thay.

**Rủi ro đã biết, xử lý đã định trước:** đoạn nguyên tử ngắn hơn → điểm có thể bẹt hơn → `ratio` có thể không còn tách sạch 20 câu trong phạm vi khỏi 10 câu ngoài. Nếu ma trận ngưỡng mới **không có điểm cắt nào đạt "10/10 câu ngoài phạm vi bị chặn"**, thì dừng lại báo người dùng và trình bày cả hai bảng — **không nới ngưỡng cho đẹp số**.

### 5.4 Backend semantic thay được, hỏng thì lùi êm

```python
class SemanticBackend(Protocol):
    def rank(self, query: str, *, session: str | None, k: int) -> list[tuple[str, float]]:
        """[(mã đoạn, điểm cosine)] đã sắp giảm dần."""
```

- `QdrantBackend` — gọi `vector-db`, filter `point_type=atomic_chunk`, loại `is_activity=true`.
- `NullBackend` — trả `[]`. Chọn khi thiếu key, thiếu mạng, hoặc `--no-semantic`.

Thiếu key / Qdrant không tới được → **tự lùi về BM25 thuần**, ghi lý do vào trace, **không ném lỗi ra người dùng**. Đây cũng là thứ giữ cho 276 test hiện có chạy offline không sửa gì.

**Một API phải nới ở `vector-db`:** `find_chunks` đang **bắt buộc** `session_id`. Cổng 1 cần tìm xuyên buổi để phát hiện "top-1 ≈ top-2 khác buổi → hỏi lại". Đổi `session_id` thành optional — `_semantic_search` bên dưới đã hỗ trợ `None` sẵn, nên chỉ là nới chữ ký + test.

### 5.5 Chi phí và bảo mật

Corpus **đã embed xong** (`manifest.json`: `api_requests: 0, cache_hits: 706`) — đợt này không gửi thêm byte transcript nào ra ngoài. Mỗi câu hỏi phát sinh đúng 1 lời gọi embed cho ~20 token của chính câu hỏi. Điều canvas §4.3 lo ngại là embed cả 445k ký tự corpus; việc đó đã xảy ra và không lặp lại.

Đổi lại, `flow1 ask` từ nay cần mạng + `OPENAI_API_KEY` để có nhánh semantic. Đường lùi ở §5.4 là thứ giữ cho demo không chết khi mạng hỏng — team-assignment có ghi "đường lùi nếu mạng chết ở CP6".

---

## 6. Trace debug

### 6.1 `flow1/src/flow1/trace.py`

```python
@dataclass(frozen=True)
class Stage:
    name: str
    ms: float
    data: dict

class Trace:
    run_id: str          # "2026-07-30T18-42-11Z-a3f9"
    query: str
    stages: list[Stage]

    def stage(self, name: str) -> ContextManager[dict]   # bấm giờ, bắt lỗi, ghi lại
    def save(self, dir: Path) -> Path

class NullTrace:         # ĐÚNG API đó, không làm gì
```

`NullTrace` giữ cho thiết kế không làm bẩn code: **không một dòng `if trace is not None` nào rải trong `retrieve`/`gates`/`ask`**. Tắt và bật trace đi qua đúng một đường code — nghĩa là trace không bao giờ "chỉ hỏng khi bật".

Ghi ra `flow1/trace/<run_id>.json` (gitignore).

### 6.2 Mỗi chặng ghi gì

| Stage | Nội dung |
|---|---|
| `gate0` | nhãn, lý do, **rule tất định hay LLM** quyết |
| `bm25` | token của query, top-10 `(mã đoạn, điểm thô)` |
| `semantic` | backend đã dùng, top-10 `(mã đoạn, cosine)` — **hoặc lý do đã lùi** |
| `fuse` | bảng RRF: mã · rank BM25 · rank emb · điểm RRF · thứ tự cuối |
| `gate1` | `top1_abs`, `ratio`, **và cả `T1_ABS`, `T1_RATIO` đã so** → action |
| `context` | chunk_id đã nạp, tổng ký tự, ước token |
| `generate` | model, phiên bản prompt, status trả về, số claim |
| `gate3` | claim qua · drop kèm `kind` · `student_codes` · `gap_codes` |

**Quy tắc làm nên toàn bộ giá trị của mục này: so sánh nào cũng ghi cả hai vế.** Không ghi `refuse`, mà ghi `ratio=1.13 < T1_RATIO=1.20 → refuse`.

Bảng `fuse` trả lời "hybrid có ăn thua gì không": nhìn thấy ngay đoạn nào **chỉ BM25 tìm ra**, đoạn nào **chỉ vector tìm ra**.

**Mặt vào:**
- `python -m flow1 ask "..." --trace` — in bảng người đọc được ra stderr, đồng thời ghi JSON.
- Streamlit: expander *"Vì sao ra kết quả này"*, dựng từ cùng object đó.

**Commit sẵn 4 trace mẫu vào `eval/traces/`:** một ca trả lời được, một ca từ chối, một ca hỏi lại, một ca bị cổng 3 loại claim. R5 đòi log/trace trong repo để chứng minh AI chạy thật; M3 dùng lại được làm input cho harness đo.

---

## 7. Vì sao Neo4j nằm ngoài luồng

Ba lý do, ghi lại để CP5 trả lời được khi bị hỏi:

1. **KG được sinh RA TỪ transcript bằng LLM.** `neo4j/ingest_transcripts.py` trích `Concept`/`Question`/`Reference` bằng một lời gọi LLM trên chính transcript. "Khái niệm này quan trọng" là ý kiến của model, lưu vào DB rồi lấy ra dùng như thể là cấu trúc có thật. Đưa vào bước reduce là để model tự xác nhận phán đoán của chính nó. Mà chiều chất lượng chính của sản phẩm là *truy vết* — node `Concept` không mang bảo đảm có mã đoạn thật.
2. **Luồng 2 không thiếu thông tin để graph đi tìm hộ.** Graph có ích khi không nhìn thấy hết cùng lúc. `reducer.py` đọc ~4k token của toàn bộ section summary — mọi ứng viên đã nằm sẵn trong một prompt. Cắm retrieval/graph vào luồng 2 là tự bỏ đúng luận điểm kiến trúc của canvas §3 (*"tutor không bao giờ thấy cả buổi; sổ tay nạp trọn buổi"*).
3. **Chỗ graph thật sự mạnh thì spec đã cấm.** KG toả sáng ở tóm tắt đa buổi; canvas non-goal #4: *"Không tóm tắt đa buổi, không so sánh giữa các buổi."*

**Nếu bản tóm cần "hợp lý hơn"**, nút vặn rẻ hơn nhiều: tiêu chí chọn trong prompt reduce · tín hiệu đếm được không cần LLM (số đoạn/section, section giảng viên nói dài nhất, khái niệm lặp qua nhiều section — vài chục dòng `dict` trên `segments.jsonl`) · đo recall so với 18 ý vàng của M5. Đó là việc của đợt sau, không thuộc phạm vi file này.

**Đợt này với Neo4j:** gom vào `graph-db/`, thống nhất `NEO4J_URL`, vá import chết trong `query_neo4j.py` (đang import `src.config.config` và `src.utils.logger` — hai module không tồn tại), cho `check_neo4j.py` chạy được. Không nối vào retrieval, không nối vào tóm tắt.

---

## 8. Chiến lược kiểm thử

**Sửa trước cái đang chết.** `vector-db` và `summarizer` hiện không collect nổi test. uv workspace (§4.1) giải quyết chính chỗ này, nên nó phải làm **đầu tiên** — không có nó thì không kiểm chứng được gì.

**Không key vẫn phải xanh 100%:**
- `conftest.py` ở gốc workspace: đăng ký marker `live`, tự skip khi thiếu `OPENAI_API_KEY`/`QDRANT_URL`.
- `FakeSemanticBackend` đọc bảng xếp hạng đóng hộp từ fixture → RRF và các cổng test được tất định, không mạng.

**Test mới:**

| Nhóm | Ca |
|---|---|
| RRF | tất định · một backend rỗng · hoà điểm · thứ tự đúng |
| Nở context | `code → chunk` dedupe · giữ thứ tự theo mã tốt nhất |
| Lùi êm | Qdrant ném lỗi → BM25 thuần, trace ghi đúng lý do, **không ném ra ngoài** |
| Cổng 1 | `gate_stats` trên đơn vị nguyên tử; 3 ca biên cũ vẫn đúng |
| Trace | end-to-end đủ 8 stage · `NullTrace` cùng API surface với `Trace` |
| Env | `check_env.py` phát hiện đúng biến thiếu |

**`@pytest.mark.live`** (chỉ chạy khi có key): 1 truy vấn Qdrant thật — khẳng định vector 768 chiều, payload có `citation_id`, filter `point_type` ăn; 1 lời gọi embed thật.

---

## 9. Thứ tự làm

1. **uv workspace + thống nhất `.env`** → `pytest` gốc chạy cả 4 member. *Không có bước này thì không đo được gì.*
2. **Chụp trạng thái nền** → `docs/system-test-report.md`: cái gì xanh, cái gì đỏ, vì sao.
3. **`trace.py` + gắn vào đường chạy hiện tại** (còn BM25 thuần).
4. **Index nguyên tử + nhánh Qdrant + RRF.**
5. **Hiệu chỉnh lại T1**, cập nhật `thresholds.py` + `distribution.md` cùng commit.
6. **Sửa `graph-db/` cho chạy được**, để ngoài luồng.
7. Chạy lại toàn hệ, cập nhật report, commit 4 trace mẫu vào `eval/traces/`.

Bước 3 trước bước 4 là có chủ ý: trace là dụng cụ đo, phải có dụng cụ trước khi thay động cơ.

---

## 10. Định nghĩa "xong"

| # | Điều kiện |
|---|---|
| 1 | `uv run pytest` ở gốc: cả 4 member collect được và **xanh, không cần API key** |
| 2 | `uv run pytest -m live` xanh khi có key |
| 3 | `python scripts/check_env.py` báo đúng biến thiếu; `.env.example` khớp tên code đọc |
| 4 | `python -m flow1 ask "..." --trace` sinh JSON đủ 8 stage, mọi so sánh ngưỡng ghi cả hai vế |
| 5 | Rút cáp mạng → `ask` vẫn trả lời bằng BM25 thuần, trace ghi rõ lý do đã lùi |
| 6 | Bảng `fuse` trong trace chỉ ra được đoạn nào chỉ BM25 tìm ra, đoạn nào chỉ vector tìm ra |
| 7 | `thresholds.py` và `eval/t1/distribution.md` cập nhật cùng commit, bảng cũ giữ lại |
| 8 | `docs/system-test-report.md` có trạng thái trước và sau |
| 9 | 4 trace mẫu trong `eval/traces/` |
| 10 | `graph-db/`: `check_neo4j.py` chạy được, và **không** package nào trong đường chạy import `graph_db` |
