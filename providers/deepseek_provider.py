"""DeepSeek API balance provider."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from core.deepseek_daily import compute_today_spend, load_or_create_snapshot, save_snapshot
from core.normalizer import normalize_deepseek_balance
from core.security import sanitize_message
from providers.base import BaseProvider

DEFAULT_BALANCE_URL = "https://api.deepseek.com/user/balance"


class DeepSeekProvider(BaseProvider):
    key = "deepseek"
    display_name = "DeepSeek"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> None:
        super().__init__(config)
        self.project_root = project_root or Path.cwd()

    def collect(self) -> dict[str, Any]:
        if not self.config.get("enabled", True):
            return normalize_deepseek_balance(
                None,
                status="unsupported",
                message="DeepSeek provider is disabled.",
            )

        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            return normalize_deepseek_balance(
                None,
                status="unsupported",
                message="DeepSeek API key is not configured.",
            )

        url = str(self.config.get("balance_url") or DEFAULT_BALANCE_URL)
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "CodingPlanWidget/1.3",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return normalize_deepseek_balance(
                None,
                status="error",
                message=f"DeepSeek balance request failed (HTTP {exc.code}).",
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            reason = exc.reason if hasattr(exc, "reason") else exc
            return normalize_deepseek_balance(
                None,
                status="offline",
                message=f"DeepSeek balance service is unreachable: {sanitize_message(reason)}",
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return normalize_deepseek_balance(
                None,
                status="error",
                message=f"Invalid DeepSeek balance response: {sanitize_message(exc)}",
            )
        except OSError as exc:
            return normalize_deepseek_balance(
                None,
                status="offline",
                message=sanitize_message(exc),
            )

        if not isinstance(payload, Mapping):
            return normalize_deepseek_balance(
                None,
                status="error",
                message="DeepSeek balance response is not a JSON object.",
            )

        balance_result = _parse_balance(payload, self.config)
        if balance_result["status"] != "ok":
            balance_result["message"] = sanitize_message(balance_result.get("message", ""))
            return balance_result

        balance = balance_result["balance"]
        if not isinstance(balance, Mapping):
            return normalize_deepseek_balance(
                None,
                status="error",
                message="DeepSeek balance normalization failed.",
            )

        snapshot_path = _snapshot_path(self.project_root, self.config)
        snapshot = load_or_create_snapshot(
            snapshot_path,
            currency=str(balance.get("currency") or "CNY"),
            start_balance=float(balance.get("total", 0.0)),
        )
        snapshot = compute_today_spend(snapshot, latest_balance=float(balance.get("total", 0.0)))
        save_snapshot(snapshot_path, snapshot)

        today = {
            "estimatedSpend": snapshot["todaySpend"],
            "startBalance": snapshot["startBalance"],
            "latestBalance": snapshot["latestBalance"],
            "date": snapshot["date"],
            "isEstimated": True,
        }
        if snapshot.get("topUpWarning"):
            balance_result["message"] = sanitize_message(
                "Daily spend is estimated and may be inaccurate after top-up or grant changes."
            )
        balance_result["today"] = today
        balance_result["message"] = sanitize_message(balance_result.get("message", ""))
        return balance_result


def _parse_balance(payload: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    preferred = str(config.get("preferred_currency") or "CNY").upper()
    is_available = payload.get("is_available")
    balance_infos = payload.get("balance_infos")
    if not isinstance(balance_infos, list) or not balance_infos:
        return normalize_deepseek_balance(
            None,
            status="error",
            message="DeepSeek balance response did not contain balance_infos.",
        )

    entry = None
    for item in balance_infos:
        if isinstance(item, Mapping) and str(item.get("currency") or "").upper() == preferred:
            entry = item
            break
    if entry is None:
        entry = balance_infos[0]
    if not isinstance(entry, Mapping):
        return normalize_deepseek_balance(
            None,
            status="error",
            message="DeepSeek balance_infos entry is not an object.",
        )

    total = _float(entry.get("total_balance"))
    granted = _float(entry.get("granted_balance"))
    topped_up = _float(entry.get("topped_up_balance"))
    if total is None:
        return normalize_deepseek_balance(
            None,
            status="error",
            message="DeepSeek balance entry is missing total_balance.",
        )

    return normalize_deepseek_balance(
        {
            "currency": str(entry.get("currency") or preferred),
            "total": total,
            "granted": granted if granted is not None else 0.0,
            "toppedUp": topped_up if topped_up is not None else 0.0,
            "isAvailable": bool(is_available) if isinstance(is_available, bool) else True,
        },
        status="ok",
        message="",
    )


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _snapshot_path(project_root: Path, config: Mapping[str, Any]) -> Path:
    configured = config.get("daily_snapshot_path") or "data/deepseek_daily.json"
    path = Path(configured)
    return path if path.is_absolute() else project_root / path
