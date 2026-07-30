# VLearn · React UI (Long Document)

Frontend moi thay the `codebase/app.py` (Streamlit). Streamlit van giu nguyen de khong pha production.

## Stack

- **Vite + React 18 + TypeScript** (`web/`)
- **FastAPI** wrapper goi lai `codebase/live.py` (`api/main.py`)
- **Tokens** trong `web/src/styles/tokens.css` — OKLCH, navy + crimson (VLearn brand)
- **Fonts**: Instrument Serif (display) + Inter (body) + JetBrains Mono (code) qua Google Fonts

## Chay

Tao 2 terminal rieng:

```powershell
# Terminal 1 — FastAPI (port 8000)
$env:SUMMARIZER_VENV = "C:\temp\summarizer_venv"
.\scripts\start_vlearn.ps1 -Only api

# Terminal 2 — Vite dev server (port 5173)
.\scripts\start_vlearn.ps1 -Only web
```

Hoac chay ca hai:

```powershell
$env:SUMMARIZER_VENV = "C:\temp\summarizer_venv"
.\scripts\start_vlearn.ps1
```

Sau do mo `http://127.0.0.1:5173`.

## Layout

| Trang          | URL                  | Muc dich                                          |
| -------------- | -------------------- | ------------------------------------------------- |
| Home (Muc luc) | `/`                  | Hero + grid 6 buoi                                |
| Buoi           | `/buoi/{sid}`        | Slide + outline ben trai, chat ben phai          |

## Hallmark discipline

- **Macrostructure**: Long Document (chapter → annotations rail)
- **Theme**: custom VLearn brand — paper `oklch(98% 0.012 250)`, accent `oklch(50% 0.21 27)`, navy `oklch(28% 0.08 265)`
- **Anti-slop**: italic headers banned (chi o quote nguyen van), 4pt scale, 3 named easings, only transform/opacity animation, mobile responsive (gate 51)
- **Diversification**: differs from Streamlit theme on display style (serif vs sans) + structure (long-document vs split-pane)

## Lock the system

Sau khi UI on dinh, noi `lock the system` de trich tokens + voice ra `.hallmark/design.md` (portable giua cac project).
