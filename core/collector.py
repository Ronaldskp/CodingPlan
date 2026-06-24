"""Provider orchestration; UI consumes only this module's cached schema."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from core.cache import read_usage, resolve_cache_path, write_usage
from core.normalizer import empty_provider
from core.paths import project_root as project_root_func
from core.security import sanitize_message
from providers import CodexProvider, DeepSeekProvider, KimiProvider

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "refresh_interval_seconds": 180,
        "cache_path": "data/usage.json",
        "timezone": "local",
    },
    "ui": {
        "always_on_top": True,
        "opacity": 0.92,
        "width": 280,
        "height": 300,
        "collapsible": True,
        "collapsed_height": 64,
        "expanded_height": 300,
        "click_title_to_toggle_collapse": True,
        "show_reset_times": True,
        "reset_display_mode": "time",
        "compact_summary_show_reset": True,
    },
    "provider": {"timeout_seconds": 15},
    "kimi": {"enabled": True, "command": "kimi-usage --json"},
    "codex": {"enabled": True, "mode": "auto", "custom_command": ""},
    "deepseek": {
        "enabled": True,
        "balance_url": "https://api.deepseek.com/user/balance",
        "preferred_currency": "CNY",
        "daily_snapshot_path": "data/deepseek_daily.json",
    },
    "security": {"redact_secrets": True, "log_level": "info"},
}


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or project_root_func()
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(str(env_path), override=False)
    path = root / "config.yaml"
    data: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, yaml.YAMLError):
            data = {}
    return _deep_merge(DEFAULT_CONFIG, data)


def collect_usage(project_root: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config(project_root)
    providers: dict[str, dict[str, Any]] = {}
    timeout_seconds = _timeout_seconds(config)
    instances = (
        CodexProvider(_provider_config(config.get("codex"), timeout_seconds), project_root),
        KimiProvider(_provider_config(config.get("kimi"), timeout_seconds), project_root),
        DeepSeekProvider(_provider_config(config.get("deepseek"), timeout_seconds), project_root),
    )
    with ThreadPoolExecutor(max_workers=len(instances), thread_name_prefix="provider") as executor:
        futures = {provider: executor.submit(provider.collect) for provider in instances}
        for provider in instances:
            try:
                providers[provider.key] = futures[provider].result()
            except Exception as exc:
                providers[provider.key] = empty_provider(
                    provider.display_name,
                    "error",
                    f"Unexpected provider error: {sanitize_message(exc)}",
                )
    usage = {
        "updatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "providers": providers,
    }
    path = resolve_cache_path(project_root, config["app"]["cache_path"])
    old_usage = read_usage(path, create_if_missing=False)
    usage = _preserve_stale_values(old_usage, usage)
    write_usage(path, usage)
    return usage


def _timeout_seconds(config: dict[str, Any]) -> float:
    value = config.get("provider", {}).get("timeout_seconds", 15)
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return 15.0


def _provider_config(section: Any, timeout_seconds: float) -> dict[str, Any]:
    result = dict(section) if isinstance(section, dict) else {}
    result["timeout_seconds"] = timeout_seconds
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in base.items():
        if isinstance(value, dict):
            incoming = override.get(key)
            result[key] = _deep_merge(value, incoming if isinstance(incoming, dict) else {})
        else:
            result[key] = override.get(key, value)
    for key, value in override.items():
        if key not in result:
            result[key] = value
    return result


def _preserve_stale_values(
    old_usage: dict[str, Any], new_usage: dict[str, Any]
) -> dict[str, Any]:
    old_providers = old_usage.get("providers", {}) if isinstance(old_usage, dict) else {}
    new_providers = new_usage.get("providers", {})
    for key, new_provider in new_providers.items():
        if new_provider.get("status") == "ok":
            continue
        old_provider = old_providers.get(key)
        if not isinstance(old_provider, dict):
            continue
        fallback = _provider_fallback_values(old_provider)
        if fallback:
            debug = sanitize_message(
                new_provider.get("debug") or new_provider.get("message", "")
            )
            new_provider.update(fallback)
            new_provider["debug"] = debug
            new_provider["message"] = "Last value shown; refresh failed."
    return new_usage


def _provider_fallback_values(old_provider: dict[str, Any]) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    five = old_provider.get("fiveHour")
    weekly = old_provider.get("weekly")
    if isinstance(five, dict) and five.get("remainingPercent") is not None:
        result["fiveHour"] = five
    if isinstance(weekly, dict) and weekly.get("remainingPercent") is not None:
        result["weekly"] = weekly
    balance = old_provider.get("balance")
    if isinstance(balance, dict) and balance.get("total") is not None:
        result["balance"] = balance
    today = old_provider.get("today")
    if isinstance(today, dict) and today.get("estimatedSpend") is not None:
        result["today"] = today
    return result if result else None
