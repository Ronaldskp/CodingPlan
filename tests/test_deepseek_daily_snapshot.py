from __future__ import annotations

from pathlib import Path

from core.deepseek_daily import compute_today_spend, load_or_create_snapshot, save_snapshot


def test_first_snapshot_is_created(tmp_path: Path) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    assert snapshot["date"] is not None
    assert snapshot["currency"] == "CNY"
    assert snapshot["startBalance"] == 23.60
    assert snapshot["latestBalance"] == 23.60
    assert snapshot["todaySpend"] == 0.0


def test_same_day_spend_is_computed(tmp_path: Path) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    snapshot = compute_today_spend(snapshot, 23.42)
    assert round(snapshot["todaySpend"], 2) == 0.18
    assert snapshot["latestBalance"] == 23.42


def test_top_up_does_not_make_spend_negative(tmp_path: Path) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    snapshot = compute_today_spend(snapshot, 25.00)
    assert snapshot["todaySpend"] == 0.0
    assert snapshot["topUpWarning"] is True


def test_new_day_resets_start_balance(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    snapshot = compute_today_spend(snapshot, 23.42)
    save_snapshot(path, snapshot)

    monkeypatch.setattr("core.deepseek_daily._today_str", lambda: "2099-12-31")
    snapshot = load_or_create_snapshot(path, "CNY", 20.00)
    assert snapshot["date"] == "2099-12-31"
    assert snapshot["startBalance"] == 20.00
    assert snapshot["todaySpend"] == 0.0


def test_currency_change_resets_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    save_snapshot(path, snapshot)
    snapshot = load_or_create_snapshot(path, "USD", 5.00)
    assert snapshot["currency"] == "USD"
    assert snapshot["startBalance"] == 5.00


def test_saved_snapshot_contains_no_secret(tmp_path: Path) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    snapshot["note"] = "sk-test-key-should-be-redacted"
    save_snapshot(path, snapshot)
    text = path.read_text(encoding="utf-8")
    assert "sk-test-key-should-be-redacted" not in text


def test_saved_snapshot_is_readable(tmp_path: Path) -> None:
    path = tmp_path / "deepseek_daily.json"
    snapshot = load_or_create_snapshot(path, "CNY", 23.60)
    save_snapshot(path, snapshot)
    loaded = load_or_create_snapshot(path, "CNY", 999.0)
    assert loaded["startBalance"] == 23.60
    assert loaded["currency"] == "CNY"
