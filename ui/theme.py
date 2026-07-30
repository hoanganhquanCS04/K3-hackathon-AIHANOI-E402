"""Theme CSS và hiệu ứng giao diện Sổ tay Buổi học VLearn."""

from __future__ import annotations

import base64
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"
CAMPUS_NAMES = ("campus.jpg", "campus.jpeg", "campus.png", "campus.webp")

FONT_STACK = (
    'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
)


def campus_data_uri() -> str | None:
    for name in CAMPUS_NAMES:
        p = ASSETS / name
        if p.exists():
            mime = "image/png" if p.suffix == ".png" else (
                "image/webp" if p.suffix == ".webp" else "image/jpeg"
            )
            b64 = base64.b64encode(p.read_bytes()).decode()
            return f"data:{mime};base64,{b64}"
    return None


BASE_CSS = f"""
<style>
  :root {{
    --navy: #0f172a;
    --navy-light: #1e293b;
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --accent: #dc2626;
    --bg-main: #f8fafc;
    --card-bg: #ffffff;
    --border: #e2e8f0;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --chip-bg: #eff6ff;
  }}

  html, body, .stApp {{
    font-family: {FONT_STACK};
    background-color: var(--bg-main);
    color: var(--text-main);
  }}

  /* Sidebar styling */
  section[data-testid="stSidebar"] {{
    background-color: #ffffff;
    border-right: 1px solid var(--border);
  }}

  /* Card Containers */
  div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--card-bg);
    border: 1px solid var(--border) !important;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    padding: 8px;
  }}

  /* Titles */
  h1, h2, h3, h4 {{
    color: var(--navy);
    font-weight: 700;
  }}

  /* Badges */
  .sess-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #2563eb;
    color: #ffffff;
    font-weight: 800;
    font-size: 0.9rem;
    padding: 4px 12px;
    border-radius: 20px;
  }}

  .sess-title-text {{
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--navy);
  }}

  .sess-subtitle {{
    font-size: 0.88rem;
    color: var(--text-muted);
  }}

  .cite-badge {{
    font-family: monospace;
    font-size: 0.78rem;
    font-weight: 600;
    background: #dbeafe;
    color: #1e40af;
    border-radius: 4px;
    padding: 2px 8px;
    margin-right: 4px;
  }}

  .quote-box {{
    background: #f1f5f9;
    border-left: 3px solid #3b82f6;
    padding: 10px 14px;
    border-radius: 6px;
    margin-top: 6px;
    font-size: 0.9rem;
    color: #334155;
  }}

  .warning-pill {{
    background: #fef3c7;
    color: #92400e;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
  }}
</style>
"""
