from __future__ import annotations

import os

import core.collector as collector
from core.cache import read_usage
from core.normalizer import normalize_window


def test_normalize_window_derives_both_percentages() -> None:
    assert normalize_window(remaining=82) == {
        "remainingPercent": 82,
        "usedPercent": 18,
        "resetAt": None,
    }
    assert normalize_window(used=91)["remainingPercent"] == 9


def test_provider_exception_does_not_crash_collector(tmp_path, monkeypatch) -> None:
    class BrokenCodex:
        key = "codex"
        display_name = "Codex"

        def __init__(self, config, project_root) -> None:
            pass

        def collect(self):
            raise RuntimeError("provider failed")

    class WorkingKimi:
        key = "kimi"
        display_name = "Kimi"

        def __init__(self, config, project_root) -> None:
            pass

        def collect(self):
            return {
                "name": "Kimi",
                "status": "ok",
                "fiveHour": normalize_window(remaining=9),
                "weekly": normalize_window(remaining=82),
                "message": "",
            }

    monkeypatch.setattr(collector, "CodexProvider", BrokenCodex)
    monkeypatch.setattr(collector, "KimiProvider", WorkingKimi)
    config = {
        **collector.DEFAULT_CONFIG,
        "app": {
            **collector.DEFAULT_CONFIG["app"],
            "cache_path": "data/usage.json",
        },
    }
    usage = collector.collect_usage(tmp_path, config)
    assert usage["providers"]["codex"]["status"] == "error"
    assert usage["providers"]["kimi"]["status"] == "ok"
    assert read_usage(tmp_path / "data" / "usage.json")["providers"]["kimi"]["status"] == "ok"


def test_load_config_reads_project_dotenv(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("KIMI_API_KEY=test-placeholder-only\n", encoding="utf-8")
    collector.load_config(tmp_path)
    assert os.environ.get("KIMI_API_KEY") == "test-placeholder-only"
