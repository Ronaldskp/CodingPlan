from __future__ import annotations

from ui.widget import _format_compact_summary


def test_compact_summary_without_reset():
    providers = {
        "codex": {"status": "ok", "fiveHour": {"remainingPercent": 99}, "weekly": {"remainingPercent": 75}},
        "kimi": {"status": "ok", "fiveHour": {"remainingPercent": 70}, "weekly": {"remainingPercent": 52}},
        "deepseek": {"status": "ok", "balance": {"currency": "CNY", "total": 58.23}},
    }
    text = _format_compact_summary(providers, show_reset=False)
    assert text == "C 99/75  K 70/52  DS 58.23"


def test_compact_summary_with_reset():
    providers = {
        "codex": {"status": "ok", "fiveHour": {"remainingPercent": 99, "resetAt": "18:44"}},
        "kimi": {"status": "ok", "fiveHour": {"remainingPercent": 70, "resetAt": "18:45"}},
    }
    text = _format_compact_summary(providers, show_reset=True)
    lines = text.splitlines()
    assert lines[0] == "C 99/--  K 70/--  DS offline"
    assert lines[1] == "R C18:44 K18:45"


def test_compact_summary_offline_providers():
    providers = {
        "codex": {"status": "error", "message": "network error"},
        "kimi": {"status": "offline"},
        "deepseek": {"status": "ok", "balance": {"currency": "CNY", "total": 12.34}},
    }
    text = _format_compact_summary(providers, show_reset=False)
    assert text == "C offline  K offline  DS 12.34"


def test_compact_summary_missing_reset_times():
    providers = {
        "codex": {"status": "ok", "fiveHour": {"remainingPercent": 99}, "weekly": {"remainingPercent": 75}},
        "kimi": {"status": "ok", "fiveHour": {"remainingPercent": 70}, "weekly": {"remainingPercent": 52}},
    }
    text = _format_compact_summary(providers, show_reset=True)
    assert "\nR" not in text
    assert text == "C 99/75  K 70/52  DS offline"


def test_compact_summary_partial_reset_only_codex():
    providers = {
        "codex": {"status": "ok", "fiveHour": {"remainingPercent": 99, "resetAt": "18:44"}},
        "kimi": {"status": "ok", "fiveHour": {"remainingPercent": 70}, "weekly": {"remainingPercent": 52}},
    }
    text = _format_compact_summary(providers, show_reset=True)
    lines = text.splitlines()
    assert lines[0] == "C 99/--  K 70/52  DS offline"
    assert lines[1] == "R C18:44"
