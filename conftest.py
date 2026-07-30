"""Cau hinh pytest dung chung cho ca workspace.

Luat: `pytest` khong key phai xanh 100%. Test cham mang mang marker `live`
va tu skip khi thieu bien moi truong tuong ung.
"""

from __future__ import annotations

import os

import pytest

_LIVE_REQUIREMENTS = ("OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY")


def pytest_collection_modifyitems(config, items):
    missing = [name for name in _LIVE_REQUIREMENTS if not os.getenv(name, "").strip()]
    if not missing:
        return
    skip = pytest.mark.skip(reason=f"can bien moi truong: {', '.join(missing)}")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
