from __future__ import annotations

import core.collector as collector
from core.cache import read_usage, write_usage
from core.normalizer import normalize_window


def test_codex_failure_preserves_old_values(monkeypatch, tmp_path):
    old = {
        "updatedAt": "2026-06-22T10:00:00",
        "providers": {
            "codex": {
                "name": "Codex",
                "status": "ok",
                "fiveHour": normalize_window(remaining=98),
                "weekly": normalize_window(remaining=84),
                "message": "",
            }
        },
    }
    write_usage(tmp_path / "data" / "usage.json", old)

    class FailingCodex:
        key = "codex"
        display_name = "Codex"

        def __init__(self, config, project_root):
            pass

        def collect(self):
            from core.normalizer import empty_provider

            result = empty_provider("Codex", "offline", "SSL/network error")
            result["debug"] = "sanitized SSL detail"
            return result

    class WorkingKimi:
        key = "kimi"
        display_name = "Kimi"

        def __init__(self, config, project_root):
            pass

        def collect(self):
            return {
                "name": "Kimi",
                "status": "ok",
                "fiveHour": normalize_window(remaining=70),
                "weekly": normalize_window(remaining=52),
                "message": "",
            }

    monkeypatch.setattr(collector, "CodexProvider", FailingCodex)
    monkeypatch.setattr(collector, "KimiProvider", WorkingKimi)

    config = {
        **collector.DEFAULT_CONFIG,
        "app": {**collector.DEFAULT_CONFIG["app"], "cache_path": "data/usage.json"},
    }
    usage = collector.collect_usage(tmp_path, config)
    codex = usage["providers"]["codex"]
    assert codex["status"] == "offline"
    assert codex["fiveHour"]["remainingPercent"] == 98
    assert codex["weekly"]["remainingPercent"] == 84
    assert "Last value shown" in codex["message"]
    assert codex["debug"] == "sanitized SSL detail"
    assert usage["providers"]["kimi"]["status"] == "ok"
    cached = read_usage(tmp_path / "data" / "usage.json")
    assert cached["providers"]["codex"]["fiveHour"]["remainingPercent"] == 98


def test_codex_failure_without_old_data_keeps_short_message(monkeypatch, tmp_path):
    class FailingCodex:
        key = "codex"
        display_name = "Codex"

        def __init__(self, config, project_root):
            pass

        def collect(self):
            from core.normalizer import empty_provider

            return empty_provider("Codex", "offline", "SSL/network error")

    class WorkingKimi:
        key = "kimi"
        display_name = "Kimi"

        def __init__(self, config, project_root):
            pass

        def collect(self):
            return {
                "name": "Kimi",
                "status": "ok",
                "fiveHour": normalize_window(remaining=70),
                "weekly": normalize_window(remaining=52),
                "message": "",
            }

    monkeypatch.setattr(collector, "CodexProvider", FailingCodex)
    monkeypatch.setattr(collector, "KimiProvider", WorkingKimi)

    config = {
        **collector.DEFAULT_CONFIG,
        "app": {**collector.DEFAULT_CONFIG["app"], "cache_path": "data/usage.json"},
    }
    usage = collector.collect_usage(tmp_path, config)
    codex = usage["providers"]["codex"]
    assert codex["status"] == "offline"
    assert codex["fiveHour"]["remainingPercent"] is None
    assert "SSL/network error" in codex["message"]
