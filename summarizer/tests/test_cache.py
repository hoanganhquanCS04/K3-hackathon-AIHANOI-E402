from __future__ import annotations

from summarizer.cache import SummaryCache, cache_key


def test_key_depends_on_all_three_components():
    base = cache_key("hash", "v1", "gpt-4o-mini")
    assert base != cache_key("hash-khac", "v1", "gpt-4o-mini")
    assert base != cache_key("hash", "v2", "gpt-4o-mini")
    assert base != cache_key("hash", "v1", "gpt-4o")
    assert base == cache_key("hash", "v1", "gpt-4o-mini")


def test_roundtrip(tmp_path):
    cache = SummaryCache(tmp_path)
    assert cache.get("k") is None
    assert cache.has("k") is False

    cache.put("k", {"abstract": "Tiếng Việt có dấu"})
    assert cache.has("k") is True
    assert cache.get("k") == {"abstract": "Tiếng Việt có dấu"}
    assert cache.count() == 1


def test_corrupt_entry_is_treated_as_miss(tmp_path):
    cache = SummaryCache(tmp_path)
    cache.put("k", {"a": 1})
    (tmp_path / "k.json").write_text("{ not json", encoding="utf-8")
    assert cache.get("k") is None


def test_put_leaves_no_temporary_file(tmp_path):
    SummaryCache(tmp_path).put("k", {"a": 1})
    assert [path.name for path in tmp_path.iterdir()] == ["k.json"]
