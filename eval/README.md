# M3 Eval — bằng chứng, golden set và ba lượt đo

Package này là nguồn số duy nhất cho phần M3. Nó không sửa prompt, không gọi
LLM để chấm LLM và không tự tạo nhãn vàng.

## Quality bar đã khóa

> Đạt khi **≥85%** case qua chiều truy vết · **0 case** bịa mã đoạn ·
> **≥90%** case ngoài phạm vi bị từ chối đúng · **0 case** gán lời học viên
> cho giảng viên.

## Cài đặt

```powershell
cd eval
uv sync
```

## 1. Mining chatlog

```powershell
uv run python -m m3_eval.mine_chatlog
```

Output:

- `evidence/evidence-report.json`: số đếm máy.
- `evidence/evidence-report.md`: bản đọc nhanh.
- `evidence/review-samples.csv`: 40 mẫu local đã được M3 owner xác nhận.
- `evidence/confirmed-labels.v1.json`: nhãn versioned và provenance xác nhận.

`review-samples.csv` có trích đoạn chatlog nên đã được `.gitignore`. Chỉ commit
report tổng hợp; không commit phiếu local chứa nội dung nguồn.

Rule `v2-locked` đã được hiệu chỉnh sau khi M3 owner xác nhận đủ 40 mẫu. Chạy
lại cùng lệnh để tái tạo precision/recall/false-positive rate và các số đưa vào
`spec.md`. Các metric này là calibration trên tập 40 mẫu cố định, không phải
holdout độc lập.

## 2. Kiểm tra golden set

Tạo hai phiếu con người cần điền:

```powershell
uv run python -m m3_eval.human_inputs --prepare
```

Sau khi điền `manual-review/gold-ideas.csv` và
`manual-review/case-approval.csv`:

```powershell
uv run python -m m3_eval.human_inputs --apply
```

Expected behavior hiện đã được M3 owner duyệt 20/20. Snapshot xác nhận nằm tại
`cases/confirmed-case-approvals.v1.json`; phần còn thiếu ở bước này chỉ là 18 ý
vàng trong `gold-ideas.csv`.

Sau đó kiểm tra:

```powershell
uv run python -m m3_eval.cases
```

File `cases/golden-set.draft.json` cố tình là bản nháp: 6 case summary đang chờ
18 ý vàng từ M5 và toàn bộ case đang chờ con người duyệt. Khi đã điền đủ:

```powershell
uv run python -m m3_eval.cases --finalize
```

Lệnh finalize chỉ tạo `golden-set.v1.json` nếu đủ 20 case, đủ 18 ý vàng,
≥10 nguồn chatlog, đủ 4 lớp rủi ro và tất cả case đã được duyệt.

## 3. Chạy technical baseline

```powershell
uv run python -m m3_eval.runner `
  --cases cases/golden-set.draft.json `
  --run-id technical-baseline
```

Đây chưa phải điểm chính thức. `official_pass` luôn để `null` khi thiếu nhãn
vàng hoặc phiếu chấm tay.

Harness chạy trực tiếp các cổng code đang được giao diện sử dụng. Khi
`codebase/live.py::answer_query` còn đánh dấu `CHƯA THẬT`, case cần semantic
search được ghi đúng là `not_implemented`; harness không biến output giả thành
điểm. Khi M1/M2 thay bằng implementation thật và bỏ marker, harness tự gọi
`answer_query`, kiểm status, citation, session, speaker và sinh thêm dòng cần
người ngoài nhóm chấm.

Phiếu `manual-review/<run-id>.csv` cũng được `.gitignore` vì có nguyên văn đoạn
nguồn. Sau khi người ngoài nhóm điền `supports_claim`, `reverses_meaning` và
`reviewer`, chạy lại **đúng cùng `run-id`**; tool giữ nguyên nhãn đã điền và cập
nhật report tổng hợp không chứa transcript dài.

## 4. Test

```powershell
uv run pytest
uv run ruff check .
```

## Nguyên tắc không được phá

1. Không sửa kết quả JSON bằng tay.
2. Không xóa run thấp.
3. Không dùng output AI để làm gold.
4. Không xem cosine score là xác suất đúng.
5. Không công bố số mining trước khi review mẫu.
6. Không commit nguyên chatlog hoặc transcript dài vào `eval/`.
