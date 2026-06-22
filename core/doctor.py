"""Non-fatal environment diagnostics."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from core.cache import resolve_cache_path
from core.paths import dotenv_path
from core.process_env import command_found
from core.security import sanitize_message


def run_doctor(project_root: Path, config: dict[str, Any]) -> list[tuple[str, bool, str]]:
    cache_path = resolve_cache_path(project_root, config["app"]["cache_path"])
    env_path = dotenv_path()
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Python", sys.version_info >= (3, 10), sys.version.split()[0]))
    checks.append(("PySide6", *_module_check("PySide6")))
    checks.append(("PyYAML", *_module_check("yaml")))
    checks.append(("python-dotenv", *_module_check("dotenv")))
    checks.append(("pytest", *_module_check("pytest")))
    checks.append((".env file", env_path.exists(), "found" if env_path.exists() else "missing"))
    checks.append(("KIMI_API_KEY", bool(os.getenv("KIMI_API_KEY")), _set_text("KIMI_API_KEY")))
    checks.append(("KIMI_CODING_API_KEY", bool(os.getenv("KIMI_CODING_API_KEY")), _set_text("KIMI_CODING_API_KEY")))
    checks.append(("DEEPSEEK_API_KEY", bool(os.getenv("DEEPSEEK_API_KEY")), _set_text("DEEPSEEK_API_KEY")))
    deepseek_enabled = bool(config.get("deepseek", {}).get("enabled", True))
    if not deepseek_enabled:
        checks.append(("DeepSeek provider", False, "disabled"))
    daily_path = resolve_cache_path(project_root, config.get("deepseek", {}).get("daily_snapshot_path", "data/deepseek_daily.json"))
    checks.append(("DeepSeek daily snapshot", daily_path.exists(), "exists" if daily_path.exists() else "missing"))
    checks.append(("Cache writable", *_check_writable(cache_path)))
    checks.append(("kimi-usage", command_found("kimi-usage"), _found_text("kimi-usage")))
    checks.append(("codex CLI", command_found("codex"), _found_text("codex")))
    auth_path = Path.home() / ".codex" / "auth.json"
    checks.append(("Codex login file", auth_path.exists(), "exists (content hidden)" if auth_path.exists() else "not found"))
    checks.append(("Codex usage source", True, "OAuth/local login"))
    checks.append(
        (
            "Codex network diagnostics",
            True,
            "Network errors may be caused by proxy, TLS interception, or Codex endpoint changes.",
        )
    )
    checks.append(("CC Switch", *_detect_cc_switch()))
    config_path = project_root / "config.yaml"
    checks.append(("config.yaml", config_path.exists(), "exists" if config_path.exists() else "not found"))
    return checks


def format_doctor(checks: list[tuple[str, bool, str]]) -> str:
    lines = ["CODING PLAN WIDGET DOCTOR", ""]
    for label, ok, detail in checks:
        state = "OK" if ok else "WARN"
        lines.append(f"[{state}] {label}: {sanitize_message(detail)}")
    return "\n".join(lines)


def _check_writable(cache_path: Path) -> tuple[bool, str]:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache_path.parent, prefix=".doctor-", delete=True):
            pass
        return True, str(cache_path)
    except OSError as exc:
        return False, sanitize_message(exc)


def _module_check(name: str) -> tuple[bool, str]:
    found = importlib.util.find_spec(name) is not None
    return found, "installed" if found else "not installed"


def _set_text(name: str) -> str:
    return "set" if os.getenv(name) else "not set"


def _found_text(command: str) -> str:
    return "found" if command_found(command) else "not found"


def _detect_cc_switch() -> tuple[bool, str]:
    if command_found("cc-switch"):
        return True, "command found"
    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / "CC Switch",
        Path(os.getenv("APPDATA", "")) / "CC Switch",
        Path(os.getenv("LOCALAPPDATA", "")) / "cc-switch",
        Path(os.getenv("APPDATA", "")) / "cc-switch",
    ]
    if any(path.exists() for path in candidates):
        return True, "installation data found"
    return False, "not detected (optional)"
