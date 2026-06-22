"""Local daily DeepSeek balance snapshot for estimated spend."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.security import sanitize_data, sanitize_message


def _today_str() -> str:
    return date.today().isoformat()


def load_or_create_snapshot(
    path: Path,
    currency: str,
    start_balance: float,
) -> dict[str, Any]:
    snapshot = _read_snapshot(path)
    today = _today_str()
    if snapshot.get("date") != today or snapshot.get("currency") != currency:
        snapshot = {
            "date": today,
            "currency": currency,
            "startBalance": start_balance,
            "latestBalance": start_balance,
            "todaySpend": 0.0,
            "updatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    return snapshot


def compute_today_spend(snapshot: dict[str, Any], latest_balance: float) -> dict[str, Any]:
    snapshot["latestBalance"] = latest_balance
    spend = max(0.0, snapshot["startBalance"] - latest_balance)
    snapshot["todaySpend"] = spend
    snapshot["topUpWarning"] = latest_balance > snapshot["startBalance"]
    snapshot["updatedAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return snapshot


def save_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = sanitize_data(snapshot)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".deepseek_daily-",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(clean, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def _read_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return sanitize_data(data)
    except Exception as exc:
        return {"_read_error": sanitize_message(exc)}
    return {}
