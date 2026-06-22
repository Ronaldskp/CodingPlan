"""Kimi Coding Plan provider backed by `kimi-usage --json`."""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from core.normalizer import empty_provider, normalize_kimi_cli
from core.process_env import command_found, subprocess_env
from core.security import sanitize_message
from providers.base import BaseProvider


class KimiProvider(BaseProvider):
    key = "kimi"
    display_name = "Kimi"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> None:
        super().__init__(config)
        self.project_root = project_root or Path.cwd()

    def collect(self) -> dict[str, Any]:
        if not self.config.get("enabled", True):
            return empty_provider("Kimi", "unsupported", "Kimi provider is disabled.")
        env = subprocess_env()
        if not env.get("KIMI_API_KEY") and not env.get("KIMI_CODING_API_KEY"):
            return empty_provider(
                "Kimi",
                "unsupported",
                "Kimi credentials are not configured. See README for setup instructions.",
            )

        command = str(self.config.get("command") or "kimi-usage --json").strip()
        executable = _command_executable(command)
        if not executable or not command_found(executable):
            return empty_provider(
                "Kimi",
                "unsupported",
                "kimi-usage command not found. Please install kimi-code-usage.",
            )

        try:
            completed = subprocess.run(
                command,
                cwd=self.project_root,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return empty_provider("Kimi", "offline", "kimi-usage timed out.")
        except OSError as exc:
            return empty_provider("Kimi", "error", sanitize_message(exc))

        if completed.returncode != 0:
            message = completed.stderr or completed.stdout or f"kimi-usage exited with code {completed.returncode}."
            return empty_provider("Kimi", "error", sanitize_message(message))

        try:
            payload = json.loads(completed.stdout)
            if not isinstance(payload, dict):
                raise ValueError("JSON root is not an object")
        except (json.JSONDecodeError, ValueError) as exc:
            self._log_shape({"parseError": str(exc), "stdoutType": "non-json"})
            return empty_provider("Kimi", "error", f"Invalid kimi-usage JSON: {sanitize_message(exc)}")

        result = normalize_kimi_cli(payload)
        if result["status"] != "ok":
            self._log_shape(_shape_only(payload))
        result["message"] = sanitize_message(result.get("message", ""))
        return result

    def _log_shape(self, shape: Any) -> None:
        """Record keys and types only; never record values."""
        log_path = self.project_root / "docs" / "development_log.md"
        if not log_path.exists():
            return
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("\n- Kimi JSON shape mismatch (keys/types only): ")
                handle.write(json.dumps(shape, ensure_ascii=False, sort_keys=True))
                handle.write("\n")
        except OSError:
            pass


def _command_executable(command: str) -> str | None:
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        return None
    if not parts:
        return None
    return parts[0].strip("\"'")


def _shape_only(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return type(value).__name__
    if isinstance(value, dict):
        return {str(key): _shape_only(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [_shape_only(value[0], depth + 1)] if value else []
    return type(value).__name__
