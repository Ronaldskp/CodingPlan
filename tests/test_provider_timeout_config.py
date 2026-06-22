from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.collector import load_config
from providers.kimi_provider import KimiProvider


ROOT = Path(__file__).resolve().parents[1]


def test_provider_timeout_exists_in_config() -> None:
    config = load_config(ROOT)
    assert config["provider"]["timeout_seconds"] == 15


def test_kimi_subprocess_receives_configured_timeout(monkeypatch, tmp_path) -> None:
    observed: dict[str, float] = {}

    monkeypatch.setattr("providers.kimi_provider.command_found", lambda executable: True)
    monkeypatch.setattr(
        "providers.kimi_provider.subprocess_env",
        lambda: {"KIMI_API_KEY": "test-only-placeholder"},
    )

    def fake_run(*args, **kwargs):
        observed["timeout"] = kwargs["timeout"]
        return SimpleNamespace(returncode=1, stderr="failed", stdout="")

    monkeypatch.setattr("providers.kimi_provider.subprocess.run", fake_run)
    result = KimiProvider(
        {"command": "kimi-usage --json", "timeout_seconds": 7},
        tmp_path,
    ).collect()

    assert observed["timeout"] == 7
    assert result["status"] == "error"
