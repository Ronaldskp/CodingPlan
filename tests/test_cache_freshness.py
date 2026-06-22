from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.freshness import compute_cache_freshness, format_updated_with_freshness


NOW = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)


def _at(minutes_ago: int) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def test_three_minutes_is_fresh() -> None:
    result = compute_cache_freshness(_at(3), NOW)
    assert (result.status, result.age_minutes, result.display_text) == ("Fresh", 3, "Fresh")


def test_ten_minutes_is_stale() -> None:
    result = compute_cache_freshness(_at(10), NOW)
    assert (result.status, result.age_minutes, result.display_text) == ("Stale", 10, "Stale 10m")


def test_twenty_minutes_is_expired() -> None:
    result = compute_cache_freshness(_at(20), NOW)
    assert (result.status, result.age_minutes, result.display_text) == (
        "Expired",
        20,
        "Expired 20m",
    )


def test_invalid_time_is_unknown() -> None:
    result = compute_cache_freshness("not-a-time", NOW)
    assert (result.status, result.age_minutes, result.display_text) == (
        "Unknown",
        None,
        "Unknown",
    )
    assert format_updated_with_freshness(None, NOW) == "Updated --:-- · Unknown"
