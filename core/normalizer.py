"""Convert provider-specific payloads into the stable usage schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping

VALID_STATUSES = {"ok", "error", "unsupported", "offline"}


def empty_window() -> dict[str, Any]:
    return {"remainingPercent": None, "usedPercent": None, "resetAt": None}


def empty_provider(name: str, status: str = "unsupported", message: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "status": status if status in VALID_STATUSES else "error",
        "fiveHour": empty_window(),
        "weekly": empty_window(),
        "message": message,
    }


def empty_deepseek_provider(status: str = "unsupported", message: str = "") -> dict[str, Any]:
    return {
        "name": "DeepSeek",
        "status": status if status in VALID_STATUSES else "error",
        "balance": None,
        "today": None,
        "message": message,
    }


def normalize_deepseek_balance(
    balance: dict[str, Any] | None,
    status: str = "ok",
    message: str = "",
) -> dict[str, Any]:
    result = empty_deepseek_provider(status, message)
    if balance is not None:
        result["balance"] = {
            "currency": str(balance.get("currency") or "CNY"),
            "total": float(balance.get("total", 0.0)),
            "granted": float(balance.get("granted", 0.0)),
            "toppedUp": float(balance.get("toppedUp", 0.0)),
            "isAvailable": bool(balance.get("isAvailable", True)),
        }
        result["today"] = None
    return result


def clamp_percent(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(max(0.0, min(100.0, number)))


def normalize_window(
    remaining: Any = None,
    used: Any = None,
    reset_at: Any = None,
) -> dict[str, Any]:
    remaining_pct = clamp_percent(remaining)
    used_pct = clamp_percent(used)
    if remaining_pct is None and used_pct is not None:
        remaining_pct = 100 - used_pct
    if used_pct is None and remaining_pct is not None:
        used_pct = 100 - remaining_pct
    return {
        "remainingPercent": remaining_pct,
        "usedPercent": used_pct,
        "resetAt": format_reset(reset_at),
    }


def format_reset(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value).astimezone().isoformat(timespec="minutes")
        except (OSError, OverflowError, ValueError):
            return str(value)
    return str(value)


def _lookup(mapping: Mapping[str, Any], *names: str) -> Any:
    lowered = {str(k).lower().replace("_", "").replace("-", ""): v for k, v in mapping.items()}
    for name in names:
        key = name.lower().replace("_", "").replace("-", "")
        if key in lowered:
            return lowered[key]
    return None


def _mapping_window(value: Any) -> dict[str, Any]:
    if isinstance(value, (int, float, str)) and not isinstance(value, bool):
        return normalize_window(remaining=value)
    if not isinstance(value, Mapping):
        return empty_window()
    return normalize_window(
        _lookup(value, "remainingPercent", "remaining_percent", "percent_left", "remaining"),
        _lookup(value, "usedPercent", "used_percent", "percent", "utilization"),
        _lookup(value, "resetAt", "resetsAt", "reset_at", "resetTime", "reset_time"),
    )


def normalize_generic_payload(payload: Mapping[str, Any], name: str) -> dict[str, Any]:
    root: Mapping[str, Any] = payload
    provider_key = name.lower()
    nested = _lookup(payload, provider_key)
    if isinstance(nested, Mapping):
        root = nested

    five = _lookup(root, "fiveHour", "five_hour", "five-hour-limit", "fiveHourLimit")
    weekly = _lookup(root, "weekly", "weekly-limit", "seven_day", "weeklyLimit")

    primary = _lookup(root, "primary", "primary_window", "primaryWindow")
    secondary = _lookup(root, "secondary", "secondary_window", "secondaryWindow")
    if five is None and isinstance(primary, Mapping):
        five = primary
    if weekly is None and isinstance(secondary, Mapping):
        weekly = secondary

    result = empty_provider(name, "ok", "")
    result["fiveHour"] = _mapping_window(five)
    result["weekly"] = _mapping_window(weekly)
    result["fiveHour"] = _merge_flat_window(
        result["fiveHour"],
        root,
        ("fiveHour", "five_hour", "five-hour-limit", "primary"),
    )
    result["weekly"] = _merge_flat_window(
        result["weekly"],
        root,
        ("weekly", "weekly-limit", "secondary"),
    )
    if all(
        window["remainingPercent"] is None
        for window in (result["fiveHour"], result["weekly"])
    ):
        result["status"] = "error"
        result["message"] = "Usage JSON did not contain recognizable quota fields."
    return result


def _merge_flat_window(
    current: dict[str, Any],
    root: Mapping[str, Any],
    prefixes: tuple[str, ...],
) -> dict[str, Any]:
    lowered = {str(key).lower(): value for key, value in root.items()}

    def flat(*suffixes: str) -> Any:
        for prefix in prefixes:
            for suffix in suffixes:
                key = f"{prefix}.{suffix}".lower()
                if key in lowered:
                    return lowered[key]
        return None

    remaining = current.get("remainingPercent")
    used = current.get("usedPercent")
    reset = current.get("resetAt")
    return normalize_window(
        remaining if remaining is not None else flat("remainingPercent", "remaining_percent"),
        used if used is not None else flat("usedPercent", "used_percent", "utilization"),
        reset if reset is not None else flat("resetAt", "resetsAt", "reset_at"),
    )


def normalize_kimi_cli(payload: Mapping[str, Any]) -> dict[str, Any]:
    items: Any = _lookup(payload, "kimi")
    if isinstance(items, Mapping):
        return normalize_generic_payload(items, "Kimi")
    if not isinstance(items, list):
        # Older/single-provider versions may emit the list at the root.
        items = payload.get("data") if isinstance(payload.get("data"), list) else None
    if not isinstance(items, list):
        errors = payload.get("errors")
        if isinstance(errors, Mapping) and errors.get("kimi"):
            result = empty_provider("Kimi", "error", str(errors["kimi"]))
            return result
        return empty_provider("Kimi", "error", "Kimi usage JSON did not contain a kimi data list.")

    result = empty_provider("Kimi", "ok", "")
    found_targets: set[str] = set()
    invalid_targets: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        label = str(item.get("label") or "")
        target = None
        if label == "Weekly Usage":
            target = "weekly"
        elif label == "5h Limit":
            target = "fiveHour"
        if target is None:
            continue

        used_pct = _number(item.get("percent"))
        if used_pct is None:
            used_pct = _number(item.get("used"))
        remaining_pct = _number(item.get("remaining"))
        reset_at = item.get("reset_at")
        if used_pct is None or remaining_pct is None:
            invalid_targets.append(label)
            continue
        result[target] = normalize_window(
            remaining_pct,
            used_pct,
            reset_at,
        )
        found_targets.add(target)

    missing = {"weekly", "fiveHour"} - found_targets
    if missing or invalid_targets:
        result["status"] = "error"
        details: list[str] = []
        if missing:
            labels = ["Weekly Usage" if item == "weekly" else "5h Limit" for item in sorted(missing)]
            details.append(f"missing valid entries: {', '.join(labels)}")
        if invalid_targets:
            details.append(
                f"entries missing percent/used, remaining, or reset_at: {', '.join(invalid_targets)}"
            )
        result["message"] = f"Kimi usage JSON is incomplete ({'; '.join(details)})."
    return result


def normalize_codex_rate_limit(payload: Mapping[str, Any]) -> dict[str, Any]:
    rate_limit = _lookup(payload, "rate_limit", "rateLimit")
    if not isinstance(rate_limit, Mapping):
        return normalize_generic_payload(payload, "Codex")

    result = empty_provider("Codex", "ok", "")
    windows: Iterable[Any] = (
        _lookup(rate_limit, "primary_window", "primaryWindow", "primary"),
        _lookup(rate_limit, "secondary_window", "secondaryWindow", "secondary"),
    )
    fallback_targets = iter(("fiveHour", "weekly"))
    for window in windows:
        if not isinstance(window, Mapping):
            continue
        seconds = _number(_lookup(window, "limit_window_seconds", "limitWindowSeconds"))
        if seconds is not None and seconds <= 24 * 3600:
            target = "fiveHour"
        elif seconds is not None:
            target = "weekly"
        else:
            target = next(fallback_targets, "weekly")
        result[target] = normalize_window(
            used=_lookup(window, "used_percent", "usedPercent", "utilization"),
            reset_at=_lookup(window, "reset_at", "resetAt", "resetsAt"),
        )

    if result["fiveHour"]["remainingPercent"] is None and result["weekly"]["remainingPercent"] is None:
        result["status"] = "error"
        result["message"] = "Codex usage response contained no rate-limit windows."
    return result


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
