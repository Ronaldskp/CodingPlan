"""Reset time parsing and display helpers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


_TIME_ONLY_RE = re.compile(r"^\d{1,2}:\d{2}$")
_SHORT_RE = re.compile(r"^(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})$")


def _try_parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone(timedelta()))
        return parsed
    except (TypeError, ValueError):
        return None


def _try_parse_short(value: str, now: datetime) -> datetime | None:
    match = _SHORT_RE.match(value)
    if not match:
        return None
    month, day, hour, minute = (int(g) for g in match.groups())
    candidate = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
    while candidate <= now:
        candidate = candidate.replace(year=candidate.year + 1)
    return candidate


def _try_parse_time_only(value: str, now: datetime) -> datetime | None:
    if not _TIME_ONLY_RE.match(value):
        return None
    hour, minute = (int(part) for part in value.split(":"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def parse_reset_time(value: Any, now: datetime | None = None) -> datetime | None:
    """Parse a reset time from supported string formats.

    Returns ``None`` when ``value`` is ``None``/empty or cannot be parsed.
    """
    if value is None or value == "":
        return None
    text = str(value).strip()
    current = now or datetime.now().astimezone()
    parsed = _try_parse_iso(text)
    if parsed is not None:
        return parsed
    parsed = _try_parse_short(text, current)
    if parsed is not None:
        return parsed
    parsed = _try_parse_time_only(text, current)
    if parsed is not None:
        return parsed
    return None


def _normalize_tz(parsed: datetime, current: datetime) -> tuple[datetime, datetime]:
    if parsed.tzinfo is None and current.tzinfo is not None:
        parsed = parsed.replace(tzinfo=current.tzinfo)
    elif current.tzinfo is None and parsed.tzinfo is not None:
        current = current.replace(tzinfo=parsed.tzinfo)
    return parsed, current


def format_reset_time(reset_at: Any, now: datetime | None = None) -> str:
    """Return a human-readable reset time string."""
    parsed = parse_reset_time(reset_at, now)
    if parsed is None:
        return "--" if reset_at in (None, "") else str(reset_at)
    current = now or datetime.now().astimezone()
    parsed, current = _normalize_tz(parsed, current)
    if parsed <= current:
        return "soon"
    if parsed.date() == current.date():
        return parsed.strftime("%H:%M")
    return parsed.strftime("%m-%d %H:%M")


def format_reset_countdown(reset_at: Any, now: datetime | None = None) -> str:
    """Return a compact countdown until reset (e.g. ``"2h05m"``)."""
    parsed = parse_reset_time(reset_at, now)
    if parsed is None:
        return "--"
    current = now or datetime.now().astimezone()
    parsed, current = _normalize_tz(parsed, current)
    delta = parsed - current
    if delta.total_seconds() <= 0:
        return "soon"
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes:02d}m"
