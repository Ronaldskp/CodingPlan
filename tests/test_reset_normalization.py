from __future__ import annotations

from core.normalizer import (
    normalize_codex_rate_limit,
    normalize_generic_payload,
    normalize_kimi_cli,
)


def test_kimi_preserves_reset_at_without_percent() -> None:
    payload = {
        "kimi": [
            {"label": "5h Limit", "percent": 91, "remaining": 9, "reset_at": "18:44"},
            {
                "label": "Weekly Usage",
                "percent": 18,
                "remaining": 82,
                "reset_at": "06-25 13:44",
            },
        ]
    }
    result = normalize_kimi_cli(payload)
    assert result["status"] == "ok"
    assert result["fiveHour"]["resetAt"] == "18:44"
    assert result["weekly"]["resetAt"] == "06-25 13:44"


def test_kimi_missing_reset_at_still_ok() -> None:
    payload = {
        "kimi": [
            {"label": "5h Limit", "percent": 91, "remaining": 9},
            {"label": "Weekly Usage", "percent": 18, "remaining": 82},
        ]
    }
    result = normalize_kimi_cli(payload)
    assert result["status"] == "ok"
    assert result["fiveHour"]["resetAt"] is None
    assert result["weekly"]["resetAt"] is None


def test_codex_rate_limit_window_reset_aliases() -> None:
    payload = {
        "rate_limit": {
            "primary_window": {"used_percent": 1, "reset_at": "2026-06-18T18:44:00+08:00"},
            "secondary_window": {"used_percent": 25, "reset_at": "2026-06-25T13:44:00+08:00"},
        }
    }
    result = normalize_codex_rate_limit(payload)
    assert result["status"] == "ok"
    assert result["fiveHour"]["resetAt"] == "2026-06-18T18:44:00+08:00"
    assert result["weekly"]["resetAt"] == "2026-06-25T13:44:00+08:00"


def test_codex_generic_payload_reset_aliases() -> None:
    payload = {
        "fiveHour": {"remainingPercent": 99, "resetAt": "18:44"},
        "weekly": {"remainingPercent": 75, "resets_at": "06-25 13:44"},
    }
    result = normalize_generic_payload(payload, "Codex")
    assert result["status"] == "ok"
    assert result["fiveHour"]["resetAt"] == "18:44"
    assert result["weekly"]["resetAt"] == "06-25 13:44"


def test_codex_flat_root_reset_aliases() -> None:
    payload = {
        "fiveHour.remainingPercent": 99,
        "fiveHour.resets_at": "18:44",
        "weekly.remainingPercent": 75,
        "weekly.resets_at": "06-25 13:44",
    }
    result = normalize_generic_payload(payload, "Codex")
    assert result["status"] == "ok"
    assert result["fiveHour"]["resetAt"] == "18:44"
    assert result["weekly"]["resetAt"] == "06-25 13:44"


def test_codex_missing_reset_returns_none() -> None:
    payload = {
        "fiveHour": {"remainingPercent": 99},
        "weekly": {"remainingPercent": 75},
    }
    result = normalize_generic_payload(payload, "Codex")
    assert result["status"] == "ok"
    assert result["fiveHour"]["resetAt"] is None
    assert result["weekly"]["resetAt"] is None
