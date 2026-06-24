from __future__ import annotations

from core.normalizer import normalize_kimi_cli


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
