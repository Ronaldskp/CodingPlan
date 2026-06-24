from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.time_display import format_reset_countdown, format_reset_time, parse_reset_time


def test_format_none_returns_dash():
    assert format_reset_time(None) == "--"


def test_format_empty_string_returns_dash():
    assert format_reset_time("") == "--"


def test_format_iso_full_returns_short_time():
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_time("2026-06-18T18:44:00+08:00", now=now) == "18:44"


def test_format_short_month_day_time():
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_time("06-18 18:44", now=now) == "18:44"


def test_format_time_only_returns_time():
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_time("18:44", now=now) == "18:44"


def test_format_unparseable_returns_raw():
    assert format_reset_time("tomorrow") == "tomorrow"


def test_format_expired_shows_soon():
    now = datetime(2026, 6, 18, 19, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_time("2026-06-18T18:44:00+08:00", now=now) == "soon"


def test_format_future_different_day_shows_month_day_time():
    now = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_time("2026-06-19T18:44:00+08:00", now=now) == "06-19 18:44"


def test_parse_reset_time_returns_none_for_unparseable():
    assert parse_reset_time("not a time") is None


def test_countdown_unparseable_returns_dash():
    assert format_reset_countdown("tomorrow") == "--"


def test_countdown_expired_returns_soon():
    now = datetime(2026, 6, 18, 19, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_countdown("2026-06-18T18:44:00+08:00", now=now) == "soon"


def test_countdown_hours_and_minutes():
    now = datetime(2026, 6, 18, 16, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_countdown("2026-06-18T18:44:00+08:00", now=now) == "2h44m"


def test_countdown_minutes_padded():
    now = datetime(2026, 6, 18, 18, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert format_reset_countdown("2026-06-18T19:05:00+08:00", now=now) == "1h05m"
