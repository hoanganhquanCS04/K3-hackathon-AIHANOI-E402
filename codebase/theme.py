"""CSS + ảnh nền. Tách riêng để app.py chỉ còn phần luồng.

Bảng màu theo VLearn: navy #0F2B5B, crimson #D8232A, nền #EDF2F8, thẻ trắng.
Font dùng stack hệ thống (Segoe UI Variable có sẵn trên Windows 11) — cố ý KHÔNG
@import Google Fonts để app chạy được hoàn toàn offline.
"""

from __future__ import annotations

import base64
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"
CAMPUS_NAMES = ("campus.jpg", "campus.jpeg", "campus.png", "campus.webp")

FONT_STACK = (
    '"Segoe UI Variable Display","Segoe UI",-apple-system,"Nunito Sans",'
    '"Helvetica Neue",Arial,sans-serif'
)


def campus_data_uri() -> str | None:
    """Ảnh nền phải nhúng base64 — Streamlit không phục vụ file cục bộ cho CSS url()."""
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
    --navy:#0F2B5B; --navy-deep:#0A1F42; --navy-soft:#1D4A8F;
    --red:#D8232A; --ink:#132845; --muted:#64748B;
    --line:#DCE5EF; --chip:#E8F0FA;
  }}
  html, body, .stApp, [class*="css"] {{ font-family: {FONT_STACK}; }}
  .stApp {{ background: #EDF2F8; }}

  /* thẻ trắng cho mọi st.container(border=True) */
  [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
    border-radius: 12px;
  }}
  div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: #fff; border: 1px solid var(--line) !important;
    border-radius: 12px; box-shadow: 0 1px 3px rgba(15,43,91,.06);
  }}

  h1, h2, h3, h4 {{ color: var(--navy); letter-spacing: -.015em; }}
  .stButton > button {{
    border-radius: 9px; font-weight: 600; border: 1px solid var(--line);
  }}
  .stButton > button[kind="primary"] {{
    background: var(--navy); border-color: var(--navy);
  }}
  .stButton > button[kind="primary"]:hover {{ background: var(--navy-soft); }}

  /* ── nhãn kiểu VLearn ── */
  .kicker {{
    color: var(--red); font-size: .74rem; font-weight: 800;
    letter-spacing: .16em; text-transform: uppercase;
  }}
  .day-badge {{
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    width:60px; height:60px; border-radius:50%; background: var(--chip);
    color: var(--navy); line-height:1.05;
  }}
  .day-badge b {{ font-size:1.18rem; }}
  .day-badge span {{ font-size:.55rem; letter-spacing:.11em; font-weight:700; opacity:.72; }}
  .sess-title {{ font-size:1.06rem; font-weight:750; color: var(--navy); }}
  .sess-meta  {{ font-size:.82rem; color: var(--muted); margin-top:2px; }}
  .warn-pill  {{
    background:#FEF3C7; color:#92400E; border-radius:20px;
    padding:1px 9px; font-size:.72rem; font-weight:700; white-space:nowrap;
  }}

  /* ── slide giữ chỗ ── */
  .slide-frame {{
    aspect-ratio:16/9; border-radius:12px; padding:26px 30px;
    background: linear-gradient(152deg, #17335F 0%, #0A1F42 100%);
    display:flex; flex-direction:column; justify-content:space-between;
    box-shadow: 0 10px 26px rgba(10,31,66,.30);
  }}
  .slide-kicker {{ font-size:.7rem; letter-spacing:.15em; text-transform:uppercase;
                   color:#8FA8CC; font-weight:700; }}
  .slide-title  {{ font-size:1.5rem; line-height:1.28; font-weight:750; color:#F4F8FD; }}
  .slide-foot   {{ display:flex; justify-content:space-between; align-items:flex-end;
                   font-size:.78rem; color:#7A93B8; }}
  .slide-stamp  {{ border:1px dashed #435C85; border-radius:5px; padding:2px 9px;
                   font-size:.66rem; letter-spacing:.09em; color:#93A9C9; }}

  /* ── nội dung tóm tắt ── */
  .mock-banner {{
    background: rgba(216,35,42,.06); border-left:3px solid var(--red);
    border-radius:6px; padding:10px 14px; font-size:.85rem; color: var(--ink);
  }}
  .blank {{ color:#7C8BA1; font-style:italic; border-bottom:1px dashed #A9B6C8; }}
  .cite  {{ font-family:ui-monospace,monospace; font-size:.76rem; font-weight:600;
            background: var(--chip); color: var(--navy);
            border-radius:4px; padding:1px 6px; white-space:nowrap; }}
  blockquote.q {{ margin:6px 0 0 0; padding-left:11px; border-left:2px solid #C6D4E6;
                  font-size:.88rem; color:#3C5876; }}
</style>
"""

# Nền ảnh trường — chỉ dùng ở màn hình danh sách buổi.
def hero_css(uri: str | None) -> str:
    layer = (
        f"linear-gradient(180deg, rgba(10,31,66,.30) 0%, rgba(10,31,66,.62) 62%,"
        f" rgba(237,242,248,.97) 100%), url('{uri}') center 32% / cover no-repeat fixed"
        if uri
        else "linear-gradient(180deg,#15325F 0%,#0A1F42 45%,#EDF2F8 100%)"
    )
    return f"""
    <style>
      .stApp {{ background: {layer}; }}
      .hero-title {{
        font-size: 2.5rem; font-weight: 800; color:#fff; line-height:1.12;
        letter-spacing:-.02em; text-shadow: 0 2px 14px rgba(6,20,44,.55);
      }}
      .hero-sub {{ color: rgba(255,255,255,.86); font-size:1rem; margin-top:6px;
                   text-shadow: 0 1px 8px rgba(6,20,44,.5); }}
      .hero-kicker {{ color:#FF9AA0; font-size:.76rem; font-weight:800;
                      letter-spacing:.17em; text-transform:uppercase;
                      text-shadow: 0 1px 8px rgba(6,20,44,.6); }}
    </style>
    """
