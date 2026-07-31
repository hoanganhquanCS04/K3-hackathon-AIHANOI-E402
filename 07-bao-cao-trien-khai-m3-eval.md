# Báo cáo triển khai M3 — Evidence, Golden Set và Evaluation Harness

> Ngày chạy: 30/07/2026  
> Nhánh làm việc: `feat/m3-evaluation-harness`  
> Base: `origin/main` tại commit `4c44b00279fcfd87e13d1f0bdef9bcf8248a8b8a`  
> Trạng thái: phần code và baseline kỹ thuật đã xong; điểm chính thức đang chờ các
> phán đoán bắt buộc phải do con người thực hiện.

## 1. Kết luận nhanh

Phần M3 hiện đã có một quy trình tái tạo được từ đầu đến cuối:

1. Đọc CSV chatlog và ghép đúng một câu học viên + một câu tutor theo `turn_id`.
2. Đếm yêu cầu tóm tắt, yêu cầu tóm tắt toàn buổi và câu trả lời thất bại bằng
   một bộ regex có version.
3. Lấy cố định 40 mẫu để M3 soi tay, không tự coi regex là sự thật.
4. Kiểm tra cấu trúc golden set đúng 20 case, có 10 case từ chatlog, phủ đủ bốn
   nhóm rủi ro và chờ đúng 18 ý vàng của M5.
5. Chạy sản phẩm qua harness, kiểm tự động citation, session, speaker, số ý,
   cảnh báo transcript thiếu và trạng thái từ chối.
6. Sinh phiếu cho người ngoài nhóm chấm hai chiều máy không được phép tự chấm:
   citation có thật sự chống lưng cho claim không và claim có đảo nghĩa không.
7. Xuất report bất biến theo từng `run-id`; điểm thấp vẫn được giữ nguyên.

Không có điểm `25/30`, `85%` hay kết quả chính thức nào được bịa để điền form.
Harness cố tình để `official_pass = null` nếu thiếu gold hoặc human review.

## 2. Những thay đổi đã thực hiện

### 2.1 Git và bảo vệ công việc cũ

- Đã cập nhật `main` tới `origin/main`.
- Đã tạo nhánh riêng `feat/m3-evaluation-harness`.
- Phần giao diện test local và preview trước embedding của M1 đã được giữ trong:
  `stash@{0}: local-only M1 test UI and pre-embedding preview before M3`.
- Không apply stash M1 lên nhánh M3.
- Chưa push và chưa tạo PR vì yêu cầu hiện tại chỉ là triển khai local.

### 2.2 Package `eval/`

Đã tạo package Python độc lập dùng `uv`:

```text
eval/
├── pyproject.toml
├── uv.lock
├── README.md
├── cases/
│   ├── golden-set.draft.json
│   └── readiness-report.json
├── evidence/
│   ├── counting-rules.json
│   ├── evidence-report.json
│   └── evidence-report.md
├── manual-review/
│   └── instructions.md
├── results/
│   └── technical-baseline/
│       ├── results.jsonl
│       ├── summary.json
│       ├── report.md
│       └── manual-review-summary.json
├── src/m3_eval/
│   ├── cases.py
│   ├── human_inputs.py
│   ├── mine_chatlog.py
│   ├── models.py
│   ├── paths.py
│   ├── runner.py
│   └── text.py
└── tests/
```

Ba CSV làm việc có chứa trích đoạn nguồn hoặc tên reviewer được giữ local và
đã thêm vào `.gitignore`:

- `eval/evidence/review-samples.csv`
- `eval/manual-review/gold-ideas.csv`
- `eval/manual-review/case-approval.csv`
- `eval/manual-review/<run-id>.csv`

Report tổng hợp có thể commit không chứa claim hay transcript dài.

### 2.3 Script đếm evidence

Lệnh:

```powershell
cd eval
uv run python -m m3_eval.mine_chatlog
```

Script làm các việc sau:

- Ghép dữ liệu theo `turn_id`, không đếm từng row message như một lượt hỏi.
- Chuẩn hóa chữ thường và bỏ dấu để regex bắt được biến thể tiếng Việt.
- Đếm cả theo lượt và theo user nhưng ghi rõ đơn vị chính là `turn_id`.
- Version hóa regex trong `eval/evidence/counting-rules.json`.
- Chọn 40 mẫu theo thứ tự hash ổn định, gồm các bucket positive, failure và
  near-miss.
- Giữ lại nhãn con người khi chạy lại script.
- Tính confusion matrix, precision, recall và false-positive rate sau khi 40
  mẫu được gán nhãn.
- Không cho phép đánh dấu số là chính thức trước khi toàn bộ mẫu được review.

### 2.4 Golden set

`eval/cases/golden-set.draft.json` hiện có:

- Tổng: **20 case**.
- Nguồn chatlog thật: **10 case**.
- `source_truth`: **16 case**.
- `ambiguity`: **3 case**.
- `out_of_scope`: **2 case**.
- `domain`: **3 case**.
- Sáu case recap T01–T06 đang chờ 3 ý vàng/buổi, tổng cộng đúng **18 ý vàng**.

Các tag có thể chồng nhau. Một case mơ hồ lấy từ chatlog đồng thời có thể kiểm
nguồn sự thật; vì vậy tổng số tag không bằng 20.

Validator đang chặn finalize vì:

- 0/18 ý vàng đã được con người cung cấp.
- 20/20 expected behavior đã được M3 owner đọc kỹ và duyệt.
- 6/6 case recap chưa hoàn tất human gold.

Đây là blocker đúng thiết kế, không phải lỗi code.

### 2.5 Evaluation harness

Harness kiểm tự động:

- Artifact có tồn tại và parse được không.
- `session_id` output có đúng session input không.
- Recap có đúng 5 ý hay không.
- Citation có tồn tại trong transcript không.
- Citation có trỏ nhầm sang buổi khác không.
- Claim chính có cite lời học viên không.
- Transcript có `[không nghe rõ]` thì output có warning không.
- Coverage chunk/section có khớp loader không.
- Recall 18 ý vàng bằng rule tái tạo được: citation thuộc tập accepted và đạt
  ít nhất 60% keyword bắt buộc.
- Buổi T07 có bị chặn bằng code trước khi gọi model không.
- Router hiện tại có từ chối/hỏi lại đúng với case không cần semantic search.

Đối với luồng query:

- Nếu router code xử lý được bằng cổng từ chối/hỏi lại, harness chấm trực tiếp.
- Nếu case cần `answer_query` trong khi file còn ghi `CHƯA THẬT`, harness trả
  `not_implemented`, không chấm output giả.
- Khi M1/M2 thay `answer_query` bằng implementation thật và bỏ marker,
  harness đã có adapter để tự gọi hàm đó, kiểm output/citation/speaker và tạo
  phiếu human review. Không cần viết lại harness.
- Nếu lời gọi thật lỗi API hoặc lỗi sản phẩm, lỗi được ghi vào result của case;
  cả run không bị mất.

### 2.6 Phiếu chấm tay và bảo vệ dữ liệu

Máy chỉ kiểm được mã citation có tồn tại. Máy không được tự quyết định citation
có thật sự chống lưng cho claim hay claim có đảo nghĩa.

Vì vậy mỗi claim được đưa vào CSV local với:

- `case_id`
- `claim_id`
- claim
- citation
- trích đoạn ngắn của nguồn
- `supports_claim`
- `reverses_meaning`
- `reviewer`
- `review_note`

Sau khi review, runner tạo `manual-review-summary.json` chỉ chứa ID, verdict và
reviewer; không chứa claim hoặc transcript. File này dùng làm bằng chứng có thể
commit.

## 3. Kết quả đã chạy thật

### 3.1 Evidence mining — đã được M3 xác nhận

Nguồn:
`data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv`

Kết quả hiện tại:

| Chỉ số | Giá trị |
|---|---:|
| Raw message rows | 2.522 |
| Unique `turn_id` | 1.261 |
| Complete student+tutor pairs | 1.261 |
| Unique users | 369 |
| Summary-request turns | 156 |
| Users có summary request | 110 |
| Whole-session request turns | 69 |
| Users có whole-session request | 59 |
| Failure rate trên summary request | 74/156 = 47,4% |
| Failure rate trên whole-session request | 37/69 = 53,6% |
| Failure rate nền toàn bộ turn | 223/1.261 = 17,7% |
| Tỷ lệ failure whole-session / nền | 3,03× |
| Mẫu đã soi và xác nhận | 40/40 |

Đây là output của rule `v2-locked`. Người phụ trách M3 đã xác nhận toàn bộ 40
nhãn sau khi xem AI pre-label và ba trường hợp cần chú ý. Trên chính tập 40 mẫu
dùng để calibration, summary/whole-session/failure đều đạt 0 false positive và
0 false negative. Đây là calibration metric, không phải một holdout độc lập;
report giữ rõ giới hạn này để không diễn giải quá mức.

### 3.2 Technical baseline

Lệnh:

```powershell
cd eval
uv run python -m m3_eval.runner `
  --cases cases/golden-set.draft.json `
  --run-id technical-baseline
```

Kết quả:

| Chỉ số | Giá trị |
|---|---:|
| Technical pass | 5/20 = 25% |
| Official pass | pending |
| Fake-citation case phát hiện bằng máy | 0 |
| Student-misattribution case phát hiện bằng máy | 0 |
| Query đi vào `answer_query` chưa implement | 6 |
| Summary artifact bị thiếu | 2 |

Không dùng **5/20** làm điểm nộp. Đây là baseline kỹ thuật trên draft chưa có
human gold và chưa có human review.

Mười lăm case technical fail hiện tại:

- `SUM-T01` đến `SUM-T04`: mỗi artifact đang có **8 key points**, trong khi
  contract của sản phẩm yêu cầu đúng 5.
- `SUM-T05`, `SUM-T06`: chưa có `session.json`.
- Sáu query xin recap đã có session nhưng router xử lý chưa đúng:
  `AMB-002`, `SRC-001`, `RARE-001`, `SRC-002`, `AMB-003`, `NORMAL-001`.
  Chúng đang bị hỏi lại không cần thiết hoặc rơi nhầm vào `answer_query`.
- `SRC-004`, `DOM-001`, `DOM-002`: cần semantic query thật nhưng
  `codebase/live.py::answer_query` còn là stub.

Năm case pass kỹ thuật:

- `AMB-001`: session đã rõ nhưng câu “tóm tắt” chưa nói một phần hay cả buổi,
  nên hỏi lại phạm vi.
- `SRC-003`, `RARE-002`: session đã rõ nhưng chưa biết slide/phần nào.
- `OOS-001`: model identity được từ chối ngoài phạm vi.
- `OOS-002`: T07 được từ chối vì session không tồn tại.

Expected behavior của các case này vẫn cần con người duyệt trước khi trở thành
official verdict.

## 4. Kiểm thử code đã chạy

Từ `eval/`:

```powershell
uv run ruff check .
uv run pytest
```

Kết quả tại thời điểm viết báo cáo:

- Ruff: pass.
- Pytest: pass.
- Test bao phủ chuẩn hóa tiếng Việt, ghép/đếm chatlog, cấu trúc golden set,
  unknown session, cổng hỏi lại, phát hiện query stub, adapter query tương lai,
  citation validation, summary artifact và bản review digest không rò dữ liệu.

## 5. Những việc bắt buộc con người phải làm

Đây là các việc Codex không được tự làm vì nếu tự điền thì kết quả đánh giá mất
giá trị.

### Việc A — M3 soi tay 40 mẫu evidence — ĐÃ HOÀN THÀNH

M3 owner đã xác nhận toàn bộ 40 AI pre-label, bao gồm ba dòng cần chú ý
`T0345`, `T0120`, `T0092`. Nhãn được mã hóa tại
`eval/evidence/confirmed-labels.v1.json`, có reviewer và ngày xác nhận.

Sau vòng sửa lỗi, rule `v2-locked` đạt 0 FP/0 FN trên chính tập calibration 40
mẫu. Số chính thức đã được cập nhật vào `spec.md`; không cần làm lại Việc A.

### Việc B — M5 điền 18 ý vàng

Mở:

```text
eval/manual-review/gold-ideas.csv
```

File có 18 dòng: T01–T06, mỗi buổi đúng 3 dòng.

Mỗi dòng điền:

- `gold_idea`: một ý mà học viên nghỉ buổi bắt buộc phải nắm.
- `accepted_chunk_ids`: một hoặc nhiều mã đoạn hợp lệ cùng buổi, cách nhau bởi
  dấu cách hoặc dấu phẩy.
- `required_keywords`: 3–5 keyword, cách nhau bằng `|`.
- `reviewer`: tên/mã người đã đọc transcript.
- `approved`: `yes`.
- `note`: tùy chọn.

Quy tắc:

- Ý vàng phải do người đọc transcript chọn, không lấy output AI làm gold.
- Citation T03 chỉ được dùng cho gold T03.
- Keyword phải thể hiện nội dung, không dùng các từ chung như “bài học”,
  “giảng viên”, “nội dung”.

### Việc C — M3/M5 duyệt expected behavior của 20 case — ĐÃ HOÀN THÀNH

Sau khi chốt contract “người dùng bắt buộc chọn T01–T06 trước khi hỏi”, M3 owner
đã đọc kỹ và xác nhận 20/20 expected behavior. Approval có provenance được lưu
tại `eval/cases/confirmed-case-approvals.v1.json` và đã nhập vào
`case-approval.csv` cùng `golden-set.draft.json`.

Sau khi Việc B hoàn tất:

```powershell
cd eval
uv run python -m m3_eval.human_inputs --apply
uv run python -m m3_eval.cases
```

Kỳ vọng:

- `gold_idea_count = 18`
- `approved_case_count = 20`
- `structural_errors = []`
- `readiness_blockers = []`
- `ready_to_finalize = true`

Sau đó khóa golden set:

```powershell
uv run python -m m3_eval.cases --finalize
```

Lệnh tạo:

- `eval/cases/golden-set.v1.json`
- `eval/cases/golden-set.v1.sha256`

Từ lúc này không sửa file v1 giữa các run.

### Việc D — M2/M1 hoàn thiện output mà M3 đang chờ

Gửi cho M2/M1 đúng danh sách blocker sau:

1. Regenerate recap T01–T04 để `key_points` đúng **5**, không phải 8.
2. Sinh artifact:
   - `summarizer/artifacts/summaries/T05/session.json`
   - `summarizer/artifacts/summaries/T06/session.json`
3. Thay `codebase/live.py::answer_query` stub bằng semantic search/guardrail thật
   cho ba case cần query.
4. Giữ schema output query:

```json
{
  "status": "answered | insufficient | out_of_scope | needs_clarification",
  "claims": [
    {
      "claim": "nội dung trả lời",
      "cite": ["T01-002"]
    }
  ]
}
```

5. Bỏ marker `CHƯA THẬT` chỉ khi implementation thật đã nối xong. Harness dùng
   marker này để không chấm nhầm stub.

### Việc E — Người ngoài nhóm chấm traceability

Sau khi product output đã đủ, chạy lượt đầu:

```powershell
cd eval
uv run python -m m3_eval.runner `
  --cases cases/golden-set.v1.json `
  --run-id run-01
```

Runner tạo:

```text
eval/manual-review/run-01.csv
```

Đưa file này cho **người ngoài nhóm**. Với mọi dòng, họ điền:

- `supports_claim = yes` nếu trích đoạn thực sự chống lưng cho claim; ngược lại
  `no`.
- `reverses_meaning = yes` nếu claim đảo hoặc làm sai nghĩa nguồn; bình thường
  là `no`.
- `reviewer = tên/mã reviewer`.
- `review_note` nếu cần giải thích.

Sau khi nhận file đã điền, chạy lại đúng cùng `run-id`:

```powershell
uv run python -m m3_eval.runner `
  --cases cases/golden-set.v1.json `
  --run-id run-01
```

Runner giữ các nhãn đã điền, cập nhật:

- `eval/results/run-01/results.jsonl`
- `eval/results/run-01/summary.json`
- `eval/results/run-01/report.md`
- `eval/results/run-01/manual-review-summary.json`

`manual-review-summary.json` là bằng chứng review an toàn để commit.

## 6. Cách chạy đủ ba lượt

Mỗi lượt phải có lý do thay đổi rõ ràng. Không được chạy lại cùng code nhiều
lần rồi chọn số đẹp nhất.

### Lượt 1 — baseline chính thức

```powershell
uv run python -m m3_eval.runner `
  --cases cases/golden-set.v1.json `
  --run-id run-01
```

Review tay và chạy lại cùng `run-01` như hướng dẫn trên.

### Lượt 2 — sau một thay đổi có tên

Ví dụ M2 sửa prompt/citation rule sau khi phân tích fail của run 1. Commit thay
đổi đó riêng, sau đó:

```powershell
uv run python -m m3_eval.runner `
  --cases cases/golden-set.v1.json `
  --run-id run-02
```

Review tay `run-02.csv`, rồi chạy lại đúng `run-02`.

### Lượt 3 — bản chốt

Sau thay đổi cuối cùng:

```powershell
uv run python -m m3_eval.runner `
  --cases cases/golden-set.v1.json `
  --run-id run-03
```

Review tay `run-03.csv`, rồi chạy lại đúng `run-03`.

Giữ đủ thư mục `run-01`, `run-02`, `run-03`, kể cả lượt kém nhất.

## 7. Cách đọc quality bar

Quality bar đã khóa:

> Đạt khi ≥85% case qua chiều truy vết, 0 case bịa mã đoạn, ≥90% case ngoài
> phạm vi bị từ chối đúng và 0 case gán lời học viên cho giảng viên.

Trong `summary.json`:

- `quality_bar_status = pending_human_input`: còn thiếu gold, case approval hoặc
  phiếu traceability.
- `quality_bar_status = failed`: đủ input nhưng ít nhất một điều kiện không đạt.
- `quality_bar_status = passed`: đủ toàn bộ điều kiện.

Kết quả `failed` vẫn là kết quả hợp lệ và phải giữ. Phần fail chính là dữ liệu
để team giải thích trên slide.

## 8. Phân biệt hai bộ “20” và “30”

Repo có hai bài đo khác nhau:

1. **Golden set M3 — 20 case**
   - Đo chất lượng sản phẩm end-to-end.
   - Có human gold, citation, refusal, ambiguity, domain risk và phiếu chấm tay.
   - Chạy ba lượt.
2. **Calibration set M2 — 30 câu**
   - 20 câu trong phạm vi + 10 câu ngoài phạm vi.
   - Dùng để chốt ngưỡng retrieval T1.
   - Đo phân bố score/ratio của retrieval, không thay thế golden set M3.

Không cộng hai bộ và không ghi “30 câu” vào chỗ form đang hỏi golden set M3 nếu
artifact chính thức của team là bộ 20 case trong `eval/`.

## 9. Lệnh kiểm tra nhanh hằng ngày

```powershell
cd D:\AI\AI_thuc_chien\Lab\Batch03-2A202601875-HoangAnhQuan\eval
uv sync
uv run ruff check .
uv run pytest
uv run python -m m3_eval.cases
uv run python -m m3_eval.mine_chatlog
uv run python -m m3_eval.runner --run-id technical-baseline
```

## 10. Checklist bàn giao

Phần đã xong:

- [x] Nhánh M3 riêng từ main mới nhất.
- [x] Package `uv`.
- [x] Script evidence tái tạo được.
- [x] Rule đếm có version.
- [x] Mẫu review 40 dòng.
- [x] M3 owner xác nhận 40/40 nhãn và khóa rule `v2-locked`.
- [x] Cập nhật số evidence chính thức vào `spec.md`.
- [x] Golden set draft 20 case.
- [x] M3 owner duyệt 20/20 expected behaviors.
- [x] 10 case bắt nguồn từ chatlog.
- [x] Phủ đủ bốn nhóm rủi ro.
- [x] Validator chặn finalize khi thiếu human input.
- [x] Harness recap + query gates + unknown session.
- [x] Adapter sẵn cho `answer_query` thật.
- [x] Phiếu human traceability.
- [x] Report tổng hợp không chứa transcript.
- [x] Technical baseline.
- [x] Test và lint.

Phần còn chờ con người/hệ thống khác:

- [ ] M5 điền 18 ý vàng.
- [ ] M2 sửa recap từ 8 xuống 5 ý.
- [ ] M2 sinh T05–T06.
- [ ] M1/M2 nối query search thật.
- [ ] Người ngoài nhóm chấm traceability.
- [ ] Chạy và giữ đủ run-01, run-02, run-03.
- [ ] Sau ba run, cập nhật kết quả eval chính thức vào `spec.md`, form và slide.
