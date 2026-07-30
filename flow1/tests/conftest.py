import pytest

from flow1.models import Seg


def _seg(code, session, order, text, section_idx=1, section_title="Attention va Transformer"):
    return Seg(
        code=code, session=session, session_title=f"Buoi {session}",
        locate_confidence="cao", section_idx=section_idx,
        section_title=section_title, order=order, text=text,
        speaker="instructor", has_gap=False, is_activity=False, n_chars=len(text),
    )


@pytest.fixture
def sample_segs():
    return [
        _seg("T04-001", "04", 1, "Cơ chế attention cho phép mô hình tập trung vào token liên quan."),
        _seg("T04-002", "04", 2, "Multi-head attention chạy nhiều đầu attention song song."),
        _seg("T04-003", "04", 3, "Transformer bỏ hẳn recurrent, chỉ dùng attention."),
        _seg("T02-001", "02", 1, "Automation là thay người làm, augmentation là hỗ trợ người làm.",
             2, "Automation va augmentation"),
    ]


@pytest.fixture
def bm25_store(sample_segs):
    """Store cho retrieve(store=...). Task 6 doi kieu tra ve cua fixture nay."""
    from flow1.index import build_store

    return build_store(sample_segs)
