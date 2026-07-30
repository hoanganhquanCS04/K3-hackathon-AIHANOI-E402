# summarizer — M2 Luồng tóm tắt

Sinh bản tóm tắt buổi học và mục học từ transcript VLearn, mọi ý đều gắn citation
`TXX-NNN` truy ngược được.

Thiết kế đầy đủ: [`../06-ke-hoach-trien-khai-m2-tom-tat.md`](../06-ke-hoach-trien-khai-m2-tom-tat.md).

## Ba nguyên tắc

1. **Tóm tắt không dùng semantic top-k.** Đọc đủ 100% chunk qua structured
   reader của M1. Top-k chỉ dùng để xác định phạm vi.
2. **Map–Reduce theo section.** 96 section → 96 section summary → 6 session
   summary. Bước reduce đọc section summary, không đọc lại transcript gốc.
3. **Validator bằng code, không bằng LLM.** Citation sai phạm vi bị loại;
   citation sang buổi khác làm fail build.

## Cài đặt

```powershell
uv sync
```

Cần `OPENAI_API_KEY` trong `.env` ở gốc repo để gọi LLM. Mọi phần không gọi LLM
(loader, validator, cache) chạy được mà không cần key.

## Lệnh

```powershell
# Xem cache đang có gì, không gọi API
uv run python -m summarizer.build --dry-run

# Sinh section summary + session summary cho mọi buổi (dùng cache)
uv run python -m summarizer.build

# Một buổi
uv run python -m summarizer.build --session T03

# Chỉ bước map
uv run python -m summarizer.build --sections-only

# Bỏ qua cache
uv run python -m summarizer.build --force

# Đọc từ Qdrant thay vì parse file local
uv run python -m summarizer.build --loader qdrant
```

Kết quả ghi vào:

```text
artifacts/summaries/{session_id}/{section_id}.json
artifacts/summaries/{session_id}/session.json
artifacts/summaries/{session_id}/session.md
artifacts/summary_cache/{key}.json
artifacts/summary_manifest.json
```

## Demo Streamlit

```powershell
uv run streamlit run app.py
```

App chỉ **đọc** artifact đã precompute — render không gọi LLM. Ba tab:

- **Tóm tắt buổi** — tldr, ý chính, mục lục; bấm vào nguồn để mở đúng đoạn
  transcript gốc kèm vai người nói.
- **Tóm tắt từng mục** — bản tóm tắt mục cạnh transcript gốc để đối chiếu.
- **Kiểm chứng** — tính lại tại thời điểm render: citation không tồn tại,
  citation chéo buổi, mục thiếu trong outline. Không tin validator lúc build.

## Test

```powershell
uv run pytest -q          # không cần API key
uv run ruff check .
```

## Cấu hình

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `OPENAI_API_KEY` | — | Bắt buộc khi gọi LLM |
| `SUMMARIZER_MAP_MODEL` | `gpt-4o-mini` | Model bước map |
| `SUMMARIZER_REDUCE_MODEL` | `gpt-4o` | Model bước reduce |
| `SUMMARIZER_LOADER` | `local` | `local` hoặc `qdrant` |
| `SUMMARIZER_CONCURRENCY` | `5` | Số request map song song |
| `SUMMARIZER_ARTIFACT_DIR` | `./artifacts` | Nơi ghi cache và summary |

## Cache

Khoá cache = `sha256(content_hash + prompt_version + model)`.

Sửa bất kỳ chuỗi nào trong `prompts.py` thì **phải tăng `PROMPT_VERSION`**, nếu
không build sẽ trả lại kết quả của prompt cũ.

## Trước buổi demo

```powershell
uv run python -m summarizer.build
uv run python -m summarizer.build --dry-run   # xác nhận missing_sections = 0
```

Cache đủ thì tóm tắt mục là 0 lời gọi LLM, tóm tắt buổi là 1 lời gọi.
