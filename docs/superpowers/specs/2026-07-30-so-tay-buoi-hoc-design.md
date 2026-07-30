# Sổ tay buổi học có trích dẫn transcript — Design

**Hướng:** C (Làn mở) — sản phẩm AI mới cho khoá, không phải tối ưu AI tutor có sẵn.
**Ngày chốt design:** 2026-07-30
**Trạng thái:** design đã chốt, chờ review trước khi viết plan.

---

## 1. Lát cắt

> **Học viên đã nghỉ hoặc mất mạch buổi 2 · cần nắm lại nội dung buổi trong 10 phút · AI chọn và tóm 5 ý chính từ transcript · nhận sổ tay 1 trang, mỗi ý gắn mã đoạn `[Txx-NNN]` bấm được về nguyên văn.**

**Một quyết định AI duy nhất:** *đoạn giảng nào chứa một ý chính của buổi, và diễn đạt nó thành một dòng mà mọi khẳng định trace được về đúng mã đoạn.*

Không có quyết định AI thứ hai. Cụ thể là **không** làm: xếp hạng độ khó, cá nhân hoá theo học viên, sinh quiz, chấm hiểu bài, tóm tắt đa buổi, so sánh với câu hỏi cá nhân của học viên.

## 2. Bằng chứng

### 2.1 Mining chatlog (đường B)

Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` — 2.522 dòng = 1.261 lượt hỏi-đáp, 369 học viên, 585 hội thoại, 22/07→29/07/2026.

Phương pháp đếm (script đếm lại được, đặt tại `eval/mining/`):
1. Ghép 2 dòng cùng `turn_id` thành một lượt (student + tutor).
2. Bỏ lớp bọc nền tảng `(Trang N, đoạn được chọn: "...")` khỏi câu học viên để chỉ đếm **phần học viên tự gõ**, không đếm lẫn chữ trên slide.
3. Lượt "xin tóm tắt cấp buổi" = khớp `(tóm tắt|tóm lược|tổng hợp|tổng kết|summary)` **và** một trong `(toàn bộ|tất cả|cả buổi|cả bài|cả slide|cả ngày|buổi học|bài giảng|hôm nay|\.pdf|day ?0?\d|slide)` trong cùng câu (cửa sổ 40 ký tự, hai chiều).
4. Lượt "tutor bó tay" = câu trả lời chứa một trong 12 cụm: `rất tiếc · xin lỗi · không tìm thấy · không thể truy cập · không thể truy xuất · không có dữ liệu · không được hiển thị · không khớp · không bao gồm · không hiển thị · hệ thống không · không đề cập`.

| Chỉ số | Giá trị |
|---|---|
| Lượt xin tóm tắt **cấp buổi** | **92** |
| Học viên riêng biệt đã hỏi | **72 / 369 = 19,5%** |
| Hội thoại riêng biệt | **84 / 585** |
| Tutor bó tay với các lượt này | **60 / 92 = 65,2%** |
| Tutor bó tay trên toàn bộ 1.261 lượt (mức nền) | **338 / 1.261 = 26,8%** |
| Downvote là "xin tóm tắt + bị bó tay" | **7 / 37 = 19%** tổng downvote |
| Mã lượt downvote trích dẫn được | `T0135, T0176, T0408, T0443, T0776, T0938, T1258` |
| Hoạt động ngoài giờ lớp (19h-7h) | **129 / 1.261 lượt = 10,2%**, 34 học viên, 49 hội thoại |

Con số quyết định: **65,2% so với mức nền 26,8% — gấp 2,3 lần.** Tutor trả lời câu hỏi về một đoạn thì tốt; hỏi cấp buổi thì 2/3 số lần nó xin lỗi.

**Nguyên nhân là kiến trúc, không phải chất lượng sinh câu trả lời.** 63 lần tutor tóm tắt thành công phần lớn là do học viên tình cờ bôi đen đúng slide Agenda/mục lục (xem `T0028` trang 3 = Agenda, `T0186` trang 7, `T0206` trang 3); khi đó chất lượng ổn — median 955 ký tự, có `[trang N]`. Tutor là RAG theo đoạn được chọn, nên nó **không có đường nào** để thấy cả buổi. Học viên hỏi sai chỗ vì không có chỗ nào khác để hỏi.

### 2.2 Giới hạn của bằng chứng — phải bù bằng khảo sát (đường A)

`conversation_mode` = **100% `in_class`** trong toàn bộ file. Chatlog **chứng minh được nhu cầu** (72 học viên xin tóm tắt cấp buổi, 65,2% bị từ chối) nhưng **không chứng minh được persona "đã nghỉ buổi"** — người nghỉ buổi thì không có log để đếm. Mức chống lưng gián tiếp duy nhất là 10,2% lượt ngoài giờ lớp.

Vì vậy persona **bắt buộc** phải có bằng chứng đường (A): khảo sát ≥20 người ngoài nhóm, ≥50% xác nhận, log toàn bộ câu hỏi + từng câu trả lời vào `validation/khao-sat.md`.

Câu hỏi khảo sát (chốt, không đổi giữa các người trả lời):
1. Bạn từng nghỉ, vào muộn, hoặc mất mạch giữa một buổi của khoá này chưa? (có/không)
2. Nếu có: lúc đó bạn làm gì để nắm lại nội dung buổi? (câu trả lời mở, ghi nguyên văn)
3. Bạn mất khoảng bao lâu cho việc đó? (ước lượng phút)
4. Nếu có sẵn một sổ tay 1 trang gồm 5 ý chính của buổi, mỗi ý bấm được về nguyên văn lời giảng, bạn có dùng không? (có/không/tuỳ)

Tiêu chí đạt: ≥20 người ngoài nhóm trả lời, ≥50% trả lời "có" ở câu 1.

### 2.3 Bảng impact — 3 ứng viên

| Ứng viên | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Chọn? |
|---|---|---|---|---|
| **A. Sổ tay buổi học có trích dẫn** | 72 học viên đã chủ động hỏi (19,5% của 369); thực tế lớn hơn vì người nghỉ buổi không có log | Mỗi buổi học, mỗi người nghỉ/mất mạch | Xem lại video 2-3 tiếng, hoặc hỏi bạn, hoặc bỏ luôn | ✅ **Chọn** |
| B. Bản đồ lỗ hổng của lớp cho giảng viên | ~5-10 giảng viên/TA | Mỗi buổi | TA đọc tay chatlog, hoặc không ai làm | ❌ Loại: người dùng ít, và không có TA nào trong nhóm để validate → tiêu chí #5 khó đạt trong 1,5 ngày |
| C. Kiểm tra hiểu thật cuối buổi | ~1.000 học viên | Mỗi buổi | Không tốn gì — vì hiện không tồn tại | ❌ Loại: pain là giả định, không đếm được trong data. `asked_check_question=True` chỉ 3/2.518 lượt chứng minh **tutor không làm**, không chứng minh **học viên cần** |

Lý do chọn A: là ứng viên duy nhất có cả (a) số đếm được từ data thật, (b) trích dẫn nguyên văn của người dùng thật, (c) người dùng có mặt ngay trong lớp để validate.

## 3. Khác gì NotebookLM / ChatGPT

Rủi ro lớn nhất của lát cắt này là "đã có NotebookLM rồi". Ba điểm khác biệt cụ thể:

1. **Mã đoạn của khoá.** Mọi khẳng định gắn `[Txx-NNN]` — mã trích dẫn do khoá quy ước, bấm được về nguyên văn lời giảng viên trong transcript của khoá. NotebookLM trích theo đoạn nó tự cắt; người ngoài nhóm không kiểm lại được bằng một mã ổn định.
2. **Biết từ chối khi bản ghi thiếu.** 103 chỗ `[không nghe rõ]` và 55 đoạn `[Hoạt động lớp: ...]` được xử lý tường minh: một ý neo vào đoạn khuyết được đánh dấu "bản ghi thiếu ở đoạn này"; đoạn hành chính bị loại khỏi ứng viên. Công cụ tổng quát không biết hai quy ước này.
3. **Biết phạm vi của mình.** Xin sổ tay cho buổi không có transcript → từ chối kèm liệt kê buổi nào có. Không đoán.

## 4. Kiến trúc

Ba tầng, mỗi tầng một trách nhiệm, chỉ tầng giữa gọi AI.

```
transcript-0N-clean.md
        │
        ▼
  ┌───────────┐   ingest: parse **[Txx-NNN]** → Segment(code, text, has_gap, is_activity)
  │  Tất định  │   registry: buổi nào có transcript (không có → từ chối, KHÔNG gọi AI)
  └───────────┘
        │  list[Segment] đã loại 55 đoạn [Hoạt động lớp]
        ▼
  ┌───────────┐
  │  1 AI call │   generate: toàn bộ transcript (~40k token) + schema JSON
  │            │   → Notebook{session_title, points: [KeyPoint{statement, codes}]}
  └───────────┘
        │
        ▼
  ┌───────────┐   verify: mã trích dẫn có thật? đúng 5 ý? đoạn được trích có khuyết?
  │  Tất định  │   render: sổ tay 1 trang, mỗi ý + mã đoạn + cờ "bản ghi thiếu"
  └───────────┘
        │
        ▼
   sotay-03.md
```

**Không có retrieval.** Đây là điểm khác biệt kiến trúc so với tutor. transcript-03 = 118.989 ký tự ≈ 40k token, nằm gọn trong context window; nạp cả buổi vào một lần gọi. Chính vì tutor *phải* retrieve theo đoạn được chọn nên nó không tóm được cấp buổi — sổ tay không retrieve nên làm được.

### 4.1 File và trách nhiệm

| File | Trách nhiệm | Gọi AI? |
|---|---|---|
| `codebase/sotay/models.py` | `Segment`, `KeyPoint`, `Notebook`, `Finding` — kiểu dùng chung | — |
| `codebase/sotay/ingest.py` | Parse markdown → `list[Segment]`; gắn `has_gap`, `is_activity` | Không |
| `codebase/sotay/registry.py` | Buổi nào có transcript; sinh câu từ chối cho buổi không có | Không |
| `codebase/sotay/llm.py` | Vỏ mỏng quanh Anthropic SDK. **Ranh giới provider duy nhất** | Có |
| `codebase/sotay/generate.py` | Dựng prompt + gọi `llm` + trả `Notebook` | Qua `llm` |
| `codebase/sotay/verify.py` | Kiểm tất định output của AI; loại ý có mã bịa | Không |
| `codebase/sotay/render.py` | `Notebook` + `Findings` → markdown 1 trang | Không |
| `codebase/sotay/cli.py` | `python -m sotay build 03` | Qua generate |
| `eval/mining/count_evidence.py` | Sinh lại toàn bộ số ở §2.1 | Không |
| `eval/golden/*.json` | 20 case vàng | — |
| `eval/harness.py` | Chạy 20 case, xuất bảng kết quả | Qua generate |

Ranh giới quan trọng: **`verify.py` không import `llm.py`.** Người viết prompt và người viết bộ kiểm là hai người khác nhau (M2 và M1) — kiểm tại CP5 sẽ hỏi đúng chỗ này.

### 4.2 Kiểu dữ liệu

```python
@dataclass(frozen=True)
class Segment:
    code: str          # "T03-014"
    text: str          # nguyên văn đoạn, đã strip
    has_gap: bool      # chứa "[không nghe rõ]"
    is_activity: bool  # bắt đầu bằng "[Hoạt động lớp"

class KeyPoint(BaseModel):
    statement: str     # một dòng, tiếng Việt
    codes: list[str]   # >=1 mã đoạn chống lưng cho statement

class Notebook(BaseModel):
    session_title: str
    points: list[KeyPoint]

@dataclass(frozen=True)
class Finding:
    point_index: int   # -1 nếu là phát hiện cấp sổ tay
    kind: str          # unknown_code | wrong_point_count | no_codes | cites_activity | transcript_gap
    detail: str
```

`transcript_gap` **do `verify` tính tất định** từ `Segment.has_gap`, không phải do AI khai. AI khai thì AI có thể quên; tính tất định thì 100% đúng theo định nghĩa.

Lưu ý schema: structured output của API **không hỗ trợ** `minItems`/`maxItems`, nên ràng buộc "đúng 5 ý" ép ở `verify`, không ép ở schema.

## 5. Bốn lớp chỗ khó

| # | Lớp | Chỗ hỏng cụ thể | Xử lý | Ở đâu |
|---|---|---|---|---|
| ① | **Nguồn sự thật** | AI bịa mã đoạn không tồn tại, hoặc gán ý vào đoạn không nói điều đó | Prompt bắt mọi ý phải kèm ≥1 mã. `verify` đối chiếu mã với chỉ mục 700 đoạn thật; mã không có → **loại ý đó, ghi Finding**, không đoán, không tự sửa | `generate.py` + `verify.py` |
| ② | **Mơ hồ / thiếu thông tin** | 103 chỗ `[không nghe rõ]` — bản ghi khuyết, AI dễ "vá" bằng suy diễn | `verify` gắn cờ tất định mọi ý neo vào đoạn có `has_gap`; `render` in "⚠ bản ghi thiếu ở đoạn này, đã kiểm lại nguyên văn trước khi tin". Prompt cấm suy diễn nội dung ở chỗ khuyết | `verify.py` + `render.py` |
| ③ | **Ngoài phạm vi** | "tóm tắt luôn buổi 7 đi" — không có transcript buổi 7 | `registry` chặn **trước khi gọi AI**: từ chối + liệt kê 6 buổi có sẵn kèm tên. Tốn 0 token, không có đường để AI bịa | `registry.py` |
| ④ | **Đặc thù domain** | Đảo ý giảng viên → học viên học sai kiến thức nghề. Và 55 đoạn `[Hoạt động lớp: ...]` bị tóm thành "ý chính buổi học" | `ingest` gắn `is_activity`, loại khỏi ứng viên; `verify` báo `cites_activity` nếu AI vẫn trích. Ca đảo ý đưa vào golden set | `ingest.py` + `verify.py` + golden set |

**Ca ④ nguyên văn — `[T03-017]`:**

> *"Kỹ sư rất giỏi xử lý những việc cụ thể — mình hay chia làm hai góc nhìn: local view với global view. Ông PM ở trên bắt buộc phải nhìn được global view... **Ông PM không phải người giải quyết vấn đề đấy, ổng chỉ spot out vấn đề**."*

Đảo ý phải bắt được: tóm thành *"PM là người giải quyết vấn đề kỹ thuật"*. Học viên đang học để làm đúng nghề này — hiểu lộn vai trò PM/engineer là học sai kiến thức ngay. Đảo ý nằm gọn trong **một đoạn duy nhất** nên test pass/fail sạch: mở `T03-017` ra là phán được.

## 6. Kịch bản rủi ro

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Không kịp CP3 (AI chạy thật) | 12:00 N1 chưa có lời gọi AI nào chạy | `llm.py` + `generate.py` là Task 4-5, làm trước `render`/`cli`. Mốc cứng: có 1 lời gọi thật trước CP3 |
| Không có API key | Team chưa có key Anthropic | `llm.py` là ranh giới provider duy nhất — đổi 1 file sang provider khác. Không commit key; đọc từ biến môi trường |
| Golden set không đủ 20 case | Đến CP5 mới đếm | M5 gán nhãn song song từ Task 1, không chờ code xong. Sàn: 6 buổi × 3 ý vàng = 18 + 1 ca ③ + 1 ca ② = 20 |
| Recall thấp, không đạt quality bar | Kết quả lượt 1 dưới ngưỡng | **Ghi nhận trung thực, không sửa số.** Rubric tính đủ điểm cho kết quả không đạt nếu ghi thật. Chỉnh prompt rồi chạy lượt 2, ghi cả hai lượt |
| Vibe-coding rule (CP5) | Có người không giải thích được phần tên mình | Mỗi file có đúng một chủ; §4.1 là bảng phân công. Mỗi người viết `reflection/` giải thích file mình sở hữu |
| Bảo mật data | Commit transcript vào repo nộp bài | Repo nộp bài **không chứa** data pack. Golden set ghi mã đoạn `[Txx-NNN]`, không dán nguyên văn dài. `.gitignore` chặn `data/` |

## 7. Kiểm thử

### 7.1 Quality bar — chốt tại đây, không đổi sau 23:59 N1

| Chiều đo | Ngưỡng | Mẫu số | Cách đo |
|---|---|---|---|
| **Citation validity** | **100%** | tổng số mã xuất hiện trong output của 18 ca `key_point` (6 buổi × 5 ý × ≥1 mã) | Tất định: mọi mã có trong chỉ mục 700 đoạn |
| **Citation support** | **≥90%** | **30 ý** = 6 buổi × 5 ý | Người **ngoài nhóm** mở mã đoạn ra đọc, phán ý có được đoạn đó chống lưng không. Blind: không thấy nhãn vàng |
| **Recall@5 so với ý vàng** | **≥60%** | **18 ý vàng** = 6 buổi × 3 | Khớp tất định: một ý vàng tính là bắt được nếu tồn tại ý sinh ra có mã giao với `expected_codes` **và** statement chứa ≥1 từ khoá trong `must_include_any` |
| **Bịa / đảo ý** | **0** | **30 ý** = 6 buổi × 5 ý | Người ngoài nhóm phán, kèm mã đoạn đối chiếu |
| **Từ chối đúng ca ③** | **100%** | 1 ca `out_of_scope` | Tất định: buổi không có transcript → từ chối + liệt kê buổi có sẵn |
| **Cờ bản ghi thiếu** | **100%** | mọi ý neo vào đoạn có `has_gap` trong 30 ý | Tất định từ `Segment.has_gap` |

Ngưỡng cụ thể hoá: citation support cần **≥27/30 ý**; recall cần **≥11/18 ý vàng**; bịa/đảo ý phải **0/30**.

Chiều "citation support" là chiều pass/fail chính, và điều kiện đạt là: **người ngoài nhóm mở đoạn ra kiểm là ra cùng kết luận.**

### 7.2 Golden set — 20 case

| Loại | Số case | Nguồn |
|---|---|---|
| `key_point` — 6 buổi, mỗi buổi 3 ý vàng do người gán nhãn | 18 | M5 đọc transcript, gán nhãn tay |
| `out_of_scope` — xin buổi 07 (không có transcript) | 1 | Bắt buộc từ chối + liệt kê 6 buổi |
| `gap` — ý neo vào đoạn có `[không nghe rõ]` | 1 | Chọn từ 103 đoạn khuyết |
| **Tổng** | **20** | Vượt sàn 20 của rubric |

10 trong số 18 ca `key_point` phải neo vào câu hỏi thật đã fail trong chatlog (dùng mã lượt `T0135, T0176, T0408, T0443, T0776, T0938, T1258` + 3 lượt nữa chọn từ 92 lượt cấp buổi) — để chứng minh sổ tay trả lời được đúng thứ tutor đã bó tay.

Định dạng một case (`eval/golden/G-03-01.json`):

```json
{
  "case_id": "G-03-01",
  "session": "03",
  "type": "key_point",
  "source_chatlog_turn": "T0408",
  "golden_points": [
    {
      "id": "gp1",
      "expected_codes": ["T03-014", "T03-015", "T03-016"],
      "must_include_any": ["ba track", "AI Engineer", "MLOps", "AI PM"]
    }
  ]
}
```

### 7.3 Ba lượt chạy, ghi cả ba

`eval/results/run-01.md`, `run-02.md`, `run-03.md` — mỗi file: ngày giờ, model, commit hash của prompt, bảng 6 chiều đo × 20 case, và **kết luận trung thực** kể cả khi không đạt bar. Không xoá lượt xấu.

## 8. Validation với user

≥3 người thật ngoài nhóm, tên cụ thể, thử prototype trước CP6. Log vào `validation/feedback-log.md`: tên, mã HV, buổi họ nghỉ, sổ tay có giúp không, câu nói nguyên văn, họ bỏ ở bước nào.

Cả lớp là user thật nên lấy 5 feedback trong giờ nghỉ là khả thi — đây là chỗ dễ ăn điểm nhất của lát cắt này (R6, 8đ).

## 9. Prototype level

**Working** — pipeline chạy thật đầu-cuối trên transcript thật, ≥1 lời gọi AI thật. Phần mock: không có. Phần không làm: không có UI web, không deploy, không xác thực người dùng, không lưu trạng thái. Output là file markdown 1 trang mở bằng bất cứ gì.

Demo 5 phút: chạy `python -m sotay build 03` → mở sổ tay → bấm một mã đoạn → mở transcript đúng dòng → chạy `python -m sotay build 07` → thấy từ chối đúng.

## 10. Quyết định phạm vi đã chốt

1. **Một sổ tay = một file transcript**, không phải một "ngày học". Day 2 nằm ở 3 file (T01+T02+T03 = 286 đoạn) — gộp thì retrieval nhoè và golden set khó chấm. 6 file → 6 sổ tay → golden set 6×3 = 18 + 2 = 20 case.
2. **Demo dùng `transcript-03`** (Day 2 chiều, 154 đoạn, 118.989 ký tự) — giàu nội dung nhất và chứa sẵn ca ④ `T03-017`.
3. **Không dùng slide.** `data/vlearn-pack/slides/` chưa tồn tại. Grounding 100% transcript, trích dẫn `[Txx-NNN]`. Nếu slide về trước sự kiện thì **vẫn không dùng** — thêm nguồn thứ hai là đổi kiến trúc giữa đường.
4. **5 ý, cứng.** Không phải "5-8". Số cố định làm recall đo được sạch.
5. **Model:** `claude-opus-5` qua Anthropic SDK. Provider gói trong `llm.py`.

## 11. Phân công 5 người

Mỗi người sở hữu file cụ thể — đây là bảng dùng để kiểm vibe-coding rule tại CP5.

| Người | Vai | Sở hữu | Khối điểm |
|---|---|---|---|
| **M1** | Pipeline & Bộ kiểm | `models.py`, `ingest.py`, `registry.py`, `verify.py` + test | R2 (một phần), ①②③④ phần tất định |
| **M2** | AI Engineer | `llm.py`, `generate.py`, prompt + test | R2, R3, ①②④ phần prompt |
| **M3** | Eval Engineer | `eval/harness.py`, `eval/mining/count_evidence.py`, `eval/results/` | **R4 (15đ)** |
| **M4** | Interface & Demo | `render.py`, `cli.py`, `demo-slides.pdf`, kịch bản demo | **R5 (8đ)** |
| **M5** | Product & Research *(non-tech)* | khảo sát 20 người, `eval/golden/` (gán nhãn), `spec.md`, `validation/`, `README.md` | **R1 (15đ) + R6 (8đ) + R7 (3đ)** |

**M5 không viết code và vẫn giữ khối điểm lớn nhất (26đ).** Việc của M5 là việc người: phỏng vấn 20 người, đọc transcript để gán nhãn ý vàng, viết spec, chạy validation. Gán nhãn golden set là việc phán đoán của người — M3 chỉ mã hoá thành JSON và chạy.

Ghép đôi bắt buộc:
- M5 (gán nhãn) ↔ M3 (mã hoá + chạy) — golden set
- M5 (chọn trích dẫn nguyên văn) ↔ M3 (chạy script đếm) — §2.1
- M1 (bộ kiểm) ↔ M2 (prompt) — hai người khác nhau, để ① có đối trọng

## 12. Lịch theo 6 mốc

| Mốc | Phải show gì |
|---|---|
| CP1 · Chốt Canvas | Canvas nháp: lát cắt §1 + bảng impact §2.3 + 3 số đầu của §2.1 |
| CP2 · Show được thứ bấm được | `ingest` chạy: in ra 154 đoạn của transcript-03, đếm đúng 11 gap + 10 activity |
| CP3 · AI chạy thật + đo lượt đầu | `generate` trả về 5 ý có mã thật; `verify` chạy; `run-01.md` có số |
| CP4 · Chốt tiến độ — spec **23:59 N1** | `spec.md` đầy đủ §1-§7, quality bar §7.1 chốt cứng, golden set ≥20 case |
| CP5 · Xác minh + validation + dry run | 3 lượt chạy; ≥3 feedback thật; mỗi người giải thích được file mình sở hữu |
| CP6 · Demo | Demo 5 phút theo §9; `demo-slides.pdf` 6 trang |

## 13. Cấu trúc repo nộp bài

```
repo/
├── README.md              ← thành viên (mã HV + tên) + bảng phân công §11
├── spec.md                ← AI Spec theo 03-template-ai-spec.md
├── demo-slides.pdf        ← 6 trang
├── codebase/
│   ├── sotay/             ← §4.1
│   └── tests/
├── eval/
│   ├── mining/            ← script sinh lại §2.1
│   ├── golden/            ← 20 case JSON
│   ├── harness.py
│   └── results/           ← run-01..03.md
├── validation/
│   ├── khao-sat.md        ← 20 người, log toàn bộ Q&A
│   └── feedback-log.md    ← ≥3 người thử prototype
└── reflection/            ← 5 file, mỗi người 1
```

`data/` **không** vào repo nộp bài (`.gitignore`). Trích dẫn minh hoạ dùng mã đoạn, vài dòng.