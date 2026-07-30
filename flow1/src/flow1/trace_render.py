"""Trace -> bang cho nguoi doc. Chi dinh dang, khong tinh toan gi."""

from __future__ import annotations

from typing import Any

_WIDTH = 72


def _fmt_value(value: Any) -> str:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return "\n".join(
            "        " + "  ".join(f"{k}={v}" for k, v in row.items())
            for row in value[:10]
        )
    if isinstance(value, list) and value and isinstance(value[0], (list, tuple)):
        return "\n".join(f"        {row[0]}  {row[1]}" for row in value[:10])
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:12])
    return str(value)


def render_trace(trace) -> str:
    lines = [
        "",
        "=" * _WIDTH,
        f"TRACE {trace.run_id}",
        f"  hoi: {trace.query}",
        "=" * _WIDTH,
    ]
    for stage in trace.stages:
        lines.append(f"\n[{stage.name}]  {stage.ms:.1f} ms")
        for key, value in stage.data.items():
            rendered = _fmt_value(value)
            if "\n" in rendered:
                lines.append(f"    {key}:")
                lines.append(rendered)
            else:
                lines.append(f"    {key}: {rendered}")
    lines.append("=" * _WIDTH)
    return "\n".join(lines)
