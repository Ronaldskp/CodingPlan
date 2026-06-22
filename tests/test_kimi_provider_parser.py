from __future__ import annotations

from pathlib import Path

from core.normalizer import normalize_kimi_cli
from providers.kimi_provider import KimiProvider


REAL_KIMI_PAYLOAD = {
    "kimi": [
        {
            "label": "Weekly Usage",
            "used": 18.0,
            "limit": 100.0,
            "remaining": 82.0,
            "percent": 18.0,
            "reset_at": "06-25 13:44",
            "unit": "%",
        },
        {
            "label": "5h Limit",
            "used": 91.0,
            "limit": 100.0,
            "remaining": 9.0,
            "percent": 91.0,
            "reset_at": "06-18 18:44",
            "unit": "%",
        },
    ]
}


def test_real_kimi_payload_is_normalized() -> None:
    result = normalize_kimi_cli(REAL_KIMI_PAYLOAD)
    assert result["status"] == "ok"
    assert result["weekly"]["remainingPercent"] == 82
    assert result["weekly"]["usedPercent"] == 18
    assert result["fiveHour"]["remainingPercent"] == 9
    assert result["fiveHour"]["usedPercent"] == 91
    assert result["weekly"]["resetAt"] == "06-25 13:44"
    assert result["fiveHour"]["resetAt"] == "06-18 18:44"


def test_missing_required_kimi_field_returns_error() -> None:
    payload = {
        "kimi": [
            {"label": "Weekly Usage", "percent": 18, "remaining": 82},
            {"label": "5h Limit", "percent": 91},
        ]
    }
    result = normalize_kimi_cli(payload)
    assert result["status"] == "error"
    assert "5h Limit" in result["message"]


def test_unknown_labels_do_not_get_guessed() -> None:
    result = normalize_kimi_cli(
        {"kimi": [{"label": "Daily Usage", "percent": 10, "remaining": 90}]}
    )
    assert result["status"] == "error"


def test_missing_kimi_key_is_unsupported(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_CODING_API_KEY", raising=False)
    result = KimiProvider({"enabled": True}, tmp_path).collect()
    assert result["status"] == "unsupported"
    assert "not configured" in result["message"]
