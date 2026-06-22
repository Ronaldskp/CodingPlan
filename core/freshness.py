"""Cache age classification shared by the CLI and desktop UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CacheFreshness:
    status: str
    age_minutes: int | None
    display_text: str


def compute_cache_freshness(
    updated_at: str | None,
    now: datetime | None = None,
) -> CacheFreshness:
    if not updated_at:
        return CacheFreshness("Unknown", None, "Unknown")
    try:
        updated = datetime.fromisoformat(str(updated_at))
        current = now or datetime.now().astimezone()
        if updated.tzinfo is None:
            updated = updated.astimezone()
        if current.tzinfo is None:
            current = current.astimezone()
        age_minutes = max(0, int((current - updated).total_seconds() // 60))
    except (TypeError, ValueError, OverflowError):
        return CacheFreshness("Unknown", None, "Unknown")

    if age_minutes <= 5:
        return CacheFreshness("Fresh", age_minutes, "Fresh")
    if age_minutes <= 15:
        return CacheFreshness("Stale", age_minutes, f"Stale {age_minutes}m")
    return CacheFreshness("Expired", age_minutes, f"Expired {age_minutes}m")


def format_updated_with_freshness(value: Any, now: datetime | None = None) -> str:
    freshness = compute_cache_freshness(str(value) if value else None, now)
    if not value:
        return f"Updated --:-- · {freshness.display_text}"
    try:
        updated_text = datetime.fromisoformat(str(value)).astimezone().strftime("%H:%M")
    except (TypeError, ValueError, OverflowError):
        updated_text = "--:--"
    return f"Updated {updated_text} · {freshness.display_text}"
