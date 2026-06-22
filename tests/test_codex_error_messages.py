from __future__ import annotations

import json
import ssl
import urllib.error
from pathlib import Path

from providers.codex_provider import CodexProvider


def _auth_home(tmp_path: Path):
    auth_dir = tmp_path / ".codex"
    auth_dir.mkdir()
    (auth_dir / "auth.json").write_text(
        json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {"access_token": "fake-token", "account_id": "fake-account"},
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_codex_ssl_error_returns_short_offline_message(monkeypatch, tmp_path: Path):
    home = _auth_home(tmp_path)
    monkeypatch.setattr("providers.codex_provider.Path.home", lambda: home)

    def raise_ssl(*args, **kwargs):
        raise urllib.error.URLError(ssl.SSLError("[SSL: UNEXPECTED_EOF_WHILE_READING]"))

    monkeypatch.setattr("urllib.request.urlopen", raise_ssl)
    result = CodexProvider({"timeout_seconds": 5}, tmp_path).collect()
    assert result["status"] == "offline"
    assert "SSL/network error" in result["message"]
    assert "UNEXPECTED_EOF" not in result["message"]
    assert "UNEXPECTED_EOF" in result["debug"]


def test_codex_urllib_error_returns_short_message(monkeypatch, tmp_path: Path):
    home = _auth_home(tmp_path)
    monkeypatch.setattr("providers.codex_provider.Path.home", lambda: home)

    def raise_error(*args, **kwargs):
        raise urllib.error.URLError("some network failure")

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    result = CodexProvider({"timeout_seconds": 5}, tmp_path).collect()
    assert result["status"] == "offline"
    assert result["message"]
    assert len(result["message"]) < 80


def test_codex_timeout_returns_short_message(monkeypatch, tmp_path: Path):
    home = _auth_home(tmp_path)
    monkeypatch.setattr("providers.codex_provider.Path.home", lambda: home)

    def raise_timeout(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr("urllib.request.urlopen", raise_timeout)
    result = CodexProvider({"timeout_seconds": 5}, tmp_path).collect()
    assert result["status"] == "offline"
    assert "timeout" in result["message"].lower()


def test_codex_direct_ssl_error_returns_short_message(monkeypatch, tmp_path: Path):
    home = _auth_home(tmp_path)
    monkeypatch.setattr("providers.codex_provider.Path.home", lambda: home)

    def raise_ssl(*args, **kwargs):
        raise ssl.SSLError("[SSL: CERTIFICATE_VERIFY_FAILED] token=sk-test-secret")

    monkeypatch.setattr("urllib.request.urlopen", raise_ssl)
    result = CodexProvider({"timeout_seconds": 5}, tmp_path).collect()
    assert result["status"] == "offline"
    assert result["message"] == "SSL/network error"
    assert "sk-test-secret" not in result["debug"]
