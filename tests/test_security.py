from __future__ import annotations

import json

import pytest

from core.cache import write_usage
from core.security import redact_text, sanitize_data


@pytest.mark.parametrize(
    "secret",
    [
        "KIMI_API_KEY=top-secret-value",
        "Authorization: Bearer abc.def.ghi",
        "Bearer abcdef123456",
        "sk-exampleSecret123",
        "cookie=session-secret",
        "access_token=access-secret",
        "refresh_token=refresh-secret",
    ],
)
def test_redact_text_hides_common_secrets(secret: str) -> None:
    redacted = redact_text(secret)
    assert "top-secret-value" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "abcdef123456" not in redacted
    assert "sk-exampleSecret123" not in redacted
    assert "session-secret" not in redacted
    assert "access-secret" not in redacted
    assert "refresh-secret" not in redacted


def test_sensitive_keys_are_removed_recursively() -> None:
    clean = sanitize_data(
        {
            "providers": {"kimi": {"status": "ok"}},
            "api_key": "secret",
            "nested": {"access_token": "secret", "cookie": "secret"},
        }
    )
    assert clean == {"providers": {"kimi": {"status": "ok"}}, "nested": {}}


def test_usage_cache_never_persists_sensitive_fields(tmp_path) -> None:
    path = tmp_path / "usage.json"
    write_usage(
        path,
        {
            "updatedAt": None,
            "providers": {},
            "KIMI_API_KEY": "secret",
            "authorization": "Bearer secret-token",
            "message": "cookie=session-secret",
        },
    )
    text = path.read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert "secret" not in text
    assert "KIMI_API_KEY" not in parsed
    assert "authorization" not in parsed
