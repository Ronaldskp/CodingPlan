from __future__ import annotations

from pathlib import Path

from core.normalizer import normalize_deepseek_balance
from providers.deepseek_provider import DeepSeekProvider, _parse_balance


REAL_DEEPSEEK_PAYLOAD = {
    "is_available": True,
    "balance_infos": [
        {
            "currency": "CNY",
            "total_balance": "23.42",
            "granted_balance": "0.00",
            "topped_up_balance": "23.42",
        }
    ],
}


MULTI_CURRENCY_PAYLOAD = {
    "is_available": True,
    "balance_infos": [
        {
            "currency": "USD",
            "total_balance": "3.20",
            "granted_balance": "1.00",
            "topped_up_balance": "2.20",
        },
        {
            "currency": "CNY",
            "total_balance": "23.42",
            "granted_balance": "0.00",
            "topped_up_balance": "23.42",
        },
    ],
}


def test_real_deepseek_payload_is_normalized() -> None:
    result = _parse_balance(REAL_DEEPSEEK_PAYLOAD, {"preferred_currency": "CNY"})
    assert result["status"] == "ok"
    balance = result["balance"]
    assert balance["currency"] == "CNY"
    assert balance["total"] == 23.42
    assert balance["granted"] == 0.0
    assert balance["toppedUp"] == 23.42
    assert balance["isAvailable"] is True


def test_multi_currency_prefers_cny() -> None:
    result = _parse_balance(MULTI_CURRENCY_PAYLOAD, {"preferred_currency": "CNY"})
    assert result["status"] == "ok"
    assert result["balance"]["currency"] == "CNY"
    assert result["balance"]["total"] == 23.42


def test_missing_cny_uses_first_currency() -> None:
    payload = {
        "is_available": False,
        "balance_infos": [
            {
                "currency": "USD",
                "total_balance": "5.50",
                "granted_balance": "0.50",
                "topped_up_balance": "5.00",
            }
        ],
    }
    result = _parse_balance(payload, {"preferred_currency": "CNY"})
    assert result["status"] == "ok"
    assert result["balance"]["currency"] == "USD"
    assert result["balance"]["total"] == 5.50
    assert result["balance"]["isAvailable"] is False


def test_string_balances_convert_to_float() -> None:
    payload = {
        "balance_infos": [
            {
                "currency": "CNY",
                "total_balance": "12.34",
                "granted_balance": "5.67",
                "topped_up_balance": "6.67",
            }
        ]
    }
    result = _parse_balance(payload, {"preferred_currency": "CNY"})
    assert result["balance"]["total"] == 12.34
    assert result["balance"]["granted"] == 5.67
    assert result["balance"]["toppedUp"] == 6.67


def test_missing_total_balance_returns_error() -> None:
    payload = {
        "balance_infos": [
            {"currency": "CNY", "granted_balance": "1.00", "topped_up_balance": "2.00"}
        ]
    }
    result = _parse_balance(payload, {"preferred_currency": "CNY"})
    assert result["status"] == "error"
    assert "total_balance" in result["message"]


def test_missing_balance_infos_returns_error() -> None:
    result = _parse_balance({"is_available": True}, {"preferred_currency": "CNY"})
    assert result["status"] == "error"
    assert "balance_infos" in result["message"]


def test_disabled_provider_returns_unsupported() -> None:
    result = DeepSeekProvider({"enabled": False}, Path.cwd()).collect()
    assert result["status"] == "unsupported"
    assert "disabled" in result["message"]


def test_missing_deepseek_key_is_unsupported(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = DeepSeekProvider({"enabled": True}, tmp_path).collect()
    assert result["status"] == "unsupported"
    assert "not configured" in result["message"]


def test_normalize_deepseek_balance_schema() -> None:
    result = normalize_deepseek_balance(
        {
            "currency": "CNY",
            "total": 10.0,
            "granted": 1.0,
            "toppedUp": 9.0,
            "isAvailable": True,
        },
        status="ok",
    )
    assert result["status"] == "ok"
    assert result["balance"]["total"] == 10.0
    assert result["today"] is None
