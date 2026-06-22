from __future__ import annotations

import json

from core.cache import read_usage


def test_missing_cache_creates_fallback_data(tmp_path) -> None:
    path = tmp_path / "data" / "usage.json"
    usage = read_usage(path, create_if_missing=True)
    assert path.exists()
    assert usage["providers"]["codex"]["status"] == "unsupported"
    assert usage["providers"]["kimi"]["status"] == "unsupported"
    assert json.loads(path.read_text(encoding="utf-8"))["providers"]


def test_corrupt_cache_is_replaced_with_fallback(tmp_path) -> None:
    path = tmp_path / "usage.json"
    path.write_text("{broken", encoding="utf-8")
    usage = read_usage(path, create_if_missing=True)
    assert usage["providers"]["codex"]["status"] == "unsupported"
    assert json.loads(path.read_text(encoding="utf-8"))["providers"]
