"""Codex provider with custom-command and official OAuth strategies."""

from __future__ import annotations

import json
import shlex
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from core.normalizer import (
    empty_provider,
    normalize_codex_rate_limit,
    normalize_generic_payload,
)
from core.process_env import command_found, subprocess_env
from core.security import sanitize_message
from providers.base import BaseProvider

CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


def _short_network_message(exc: Exception) -> str:
    text = sanitize_message(exc, max_length=200).lower()
    if "ssl" in text:
        return "SSL/network error"
    if "proxy" in text or "tunnel" in text:
        return "Proxy/network error"
    if "time" in text:
        return "Network timeout"
    return "Network error"


def _network_failure(exc: Exception, message: str | None = None) -> dict[str, Any]:
    result = empty_provider("Codex", "offline", message or _short_network_message(exc))
    debug = sanitize_message(exc, max_length=200)
    if debug:
        result["debug"] = debug
    return result


class CodexProvider(BaseProvider):
    key = "codex"
    display_name = "Codex"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> None:
        super().__init__(config)
        self.project_root = project_root or Path.cwd()

    def collect(self) -> dict[str, Any]:
        if not self.config.get("enabled", True):
            return empty_provider("Codex", "unsupported", "Codex provider is disabled.")

        mode = str(self.config.get("mode") or "auto").lower()
        custom_command = str(self.config.get("custom_command") or "").strip()
        if mode == "custom_command" or custom_command:
            if not custom_command:
                return empty_provider("Codex", "unsupported", "Codex custom command is empty.")
            return self._collect_custom(custom_command)

        if mode in {"auto", "official_oauth", "cc_switch"}:
            official = self._collect_official_oauth()
            if official["status"] != "unsupported":
                return official

        return empty_provider(
            "Codex",
            "unsupported",
            "Codex quota source is not configured yet.",
        )

    def _collect_custom(self, command: str) -> dict[str, Any]:
        executable = _command_executable(command)
        if not executable or not command_found(executable):
            return empty_provider("Codex", "unsupported", "Codex custom command was not found.")
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
                env=subprocess_env(),
            )
        except subprocess.TimeoutExpired:
            return empty_provider("Codex", "offline", "Codex custom command timed out.")
        except OSError as exc:
            return empty_provider("Codex", "error", sanitize_message(exc))

        if completed.returncode != 0:
            message = completed.stderr or completed.stdout or "Codex custom command failed."
            return empty_provider("Codex", "error", sanitize_message(message))
        try:
            payload = json.loads(completed.stdout)
            if not isinstance(payload, Mapping):
                raise ValueError("JSON root is not an object")
        except (json.JSONDecodeError, ValueError) as exc:
            return empty_provider("Codex", "error", f"Invalid Codex JSON: {sanitize_message(exc)}")

        result = normalize_codex_rate_limit(payload)
        if result["status"] != "ok":
            result = normalize_generic_payload(payload, "Codex")
        result["message"] = sanitize_message(result.get("message", ""))
        return result

    def _collect_official_oauth(self) -> dict[str, Any]:
        auth_path = Path.home() / ".codex" / "auth.json"
        if not auth_path.exists():
            return empty_provider(
                "Codex",
                "unsupported",
                "Codex OAuth login was not found. Run codex login or configure a custom command.",
            )
        try:
            with auth_path.open("r", encoding="utf-8") as handle:
                auth = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            return empty_provider("Codex", "error", f"Unable to read Codex login state: {sanitize_message(exc)}")

        if not isinstance(auth, Mapping) or auth.get("auth_mode") != "chatgpt":
            return empty_provider(
                "Codex",
                "unsupported",
                "Codex login is not using ChatGPT OAuth; official quota is unavailable.",
            )
        tokens = auth.get("tokens")
        if not isinstance(tokens, Mapping):
            return empty_provider("Codex", "error", "Codex OAuth login state has no usable tokens.")
        access_token = tokens.get("access_token")
        account_id = tokens.get("account_id")
        if not isinstance(access_token, str) or not access_token:
            return empty_provider("Codex", "error", "Codex OAuth access token is unavailable.")

        request = urllib.request.Request(
            CODEX_USAGE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "codex-cli",
                "Accept": "application/json",
            },
            method="GET",
        )
        if isinstance(account_id, str) and account_id:
            request.add_header("ChatGPT-Account-Id", account_id)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return empty_provider("Codex", "error", "Codex session expired. Please sign in again.")
            if exc.code == 407:
                return _network_failure(exc, "Proxy/network error")
            if exc.code in (408, 504):
                return _network_failure(exc, "Network timeout")
            return empty_provider("Codex", "error", f"Codex usage request failed (HTTP {exc.code}).")
        except urllib.error.URLError as exc:
            reason = exc.reason if hasattr(exc, "reason") else exc
            if isinstance(reason, ssl.SSLError) or (isinstance(reason, Exception) and "SSL" in str(reason)):
                return _network_failure(reason, "SSL/network error")
            return _network_failure(reason)
        except TimeoutError as exc:
            return _network_failure(exc, "Network timeout")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return empty_provider("Codex", "error", f"Invalid Codex usage response: {sanitize_message(exc)}")
        except OSError as exc:
            return _network_failure(exc)

        if not isinstance(payload, Mapping):
            return empty_provider("Codex", "error", "Codex usage response is not a JSON object.")
        result = normalize_codex_rate_limit(payload)
        result["message"] = sanitize_message(result.get("message", ""))
        return result


def _command_executable(command: str) -> str | None:
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        return None
    return parts[0].strip("\"'") if parts else None
