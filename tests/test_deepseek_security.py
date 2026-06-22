from __future__ import annotations

import json

import pytest

from core.cache import write_usage
from core.deepseek_daily import save_snapshot
from core.security import redact_text, sanitize_data


@pytest.mark.parametrize(
    "secret",
    [
        "DEEPSEEK_API_KEY=top-secret-value",
        "Authorization: Bearer sk-abc123.def456",
        "sk-test-deepseek-key-xyz",
    ],
)
def test_redact_text_hides_deepseek_secrets(secret: str) -> None:
    redacted = redact_text(secret)
    assert "top-secret-value" not in redacted
    assert "sk-abc123.def456" not in redacted
    assert "sk-test-deepseek-key-xyz" not in redacted
    assert "[REDACTED]" in redacted or redacted.count("=") == 0


def test_usage_cache_never_persists_deepseek_key(tmp_path) -> None:
    path = tmp_path / "usage.json"
    write_usage(
        path,
        {
            "updatedAt": None,
            "providers": {
                "deepseek": {
                    "name": "DeepSeek",
                    "status": "ok",
                    "balance": {"currency": "CNY", "total": 23.42},
                    "today": {"estimatedSpend": 0.18, "isEstimated": True},
                    "message": "DEEPSEEK_API_KEY=super-secret",
                }
            },
            "DEEPSEEK_API_KEY": "super-secret",
        },
    )
    text = path.read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert "super-secret" not in text
    assert "DEEPSEEK_API_KEY" not in parsed
    assert parsed["providers"]["deepseek"]["message"] == "DEEPSEEK_API_KEY=[REDACTED]"


def test_daily_snapshot_never_persists_deepseek_key(tmp_path) -> None:
    path = tmp_path / "deepseek_daily.json"
    save_snapshot(
        path,
        {
            "date": "2026-06-18",
            "currency": "CNY",
            "startBalance": 23.60,
            "latestBalance": 23.42,
            "todaySpend": 0.18,
            "DEEPSEEK_API_KEY": "super-secret",
            "message": "sk-test-key",
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "super-secret" not in text
    assert "DEEPSEEK_API_KEY" not in text
    assert "sk-test-key" not in text


def test_sanitize_data_removes_sensitive_deepseek_fields() -> None:
    clean = sanitize_data(
        {
            "providers": {
                "deepseek": {
                    "status": "ok",
                    "balance": {"total": 23.42},
                    "DEEPSEEK_API_KEY": "secret",
                }
            },
            "api_key": "secret",
        }
    )
    assert "api_key" not in clean
    assert "DEEPSEEK_API_KEY" not in clean["providers"]["deepseek"]
    assert clean["providers"]["deepseek"]["balance"]["total"] == 23.42
