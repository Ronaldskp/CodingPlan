# DeepSeek API Balance Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-_SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a DeepSeek API balance provider that displays current balance and estimated daily spend in CLI and UI without affecting existing Codex/Kimi behavior.

**Architecture:** A new `DeepSeekProvider` fetches balance from `https://api.deepseek.com/user/balance` using `urllib.request`, a dedicated `deepseek_daily.py` module manages the local daily spend snapshot, and the existing normalizer/collector/doctor/cache/UI/CLI layers are extended to include DeepSeek as a third provider.

**Tech Stack:** Python 3.14, PySide6, PyYAML, python-dotenv, pytest, urllib.request.

---

## File Map

| File | Responsibility |
|------|----------------|
| `providers/deepseek_provider.py` | New provider: env check, HTTP GET balance, error handling, sanitize. |
| `core/deepseek_daily.py` | Daily snapshot persistence and `todaySpend` estimation. |
| `core/normalizer.py` | Add `normalize_deepseek_balance()` returning balance + today schema. |
| `core/collector.py` | Wire DeepSeek provider into parallel collection. |
| `core/cache.py` | Include deepseek in `initial_usage()`. |
| `core/doctor.py` | Add DeepSeek key and snapshot checks. |
| `main.py` | Render DeepSeek section in `format_status()`. |
| `ui/widget.py` | Add third DeepSeek provider card and resize to height 300. |
| `config.yaml` | Add `deepseek` section. |
| `.env` | Append `DEEPSEEK_API_KEY=` (do NOT touch existing KIMI key). |
| `.env.example` | Add DeepSeek placeholder. |
| `.gitignore` | Ensure `.env`, `data/usage.json`, `data/ui_state.json`, `data/deepseek_daily.json` excluded. |
| `tests/test_deepseek_provider_parser.py` | Balance JSON parsing tests. |
| `tests/test_deepseek_daily_snapshot.py` | Snapshot create/update/top-up tests. |
| `tests/test_deepseek_security.py` | No key in cache/snapshot output. |
| `README.md`, `docs/development_log.md`, `docs/deepseek_provider_notes.md` | Documentation updates. |

---

## Task 1: Add DeepSeek Provider

**Files:**
- Create: `providers/deepseek_provider.py`
- Modify: `providers/__init__.py`

- [ ] **Step 1: Create provider implementation**

```python
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
            return balance_result

        balance = balance_result["balance"]
        snapshot_path = _snapshot_path(self.project_root, self.config)
        snapshot = load_or_create_snapshot(
            snapshot_path,
            currency=balance["currency"],
            start_balance=balance["total"],
        )
        snapshot = compute_today_spend(snapshot, latest_balance=balance["total"])
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

    def _float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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


def _snapshot_path(project_root: Path, config: Mapping[str, Any]) -> Path:
    configured = config.get("daily_snapshot_path") or "data/deepseek_daily.json"
    path = Path(configured)
    return path if path.is_absolute() else project_root / path
```

- [ ] **Step 2: Export provider**

Modify `providers/__init__.py` to add `DeepSeekProvider` and update `__all__`.

---

## Task 2: Add Daily Snapshot Module

**Files:**
- Create: `core/deepseek_daily.py`

- [ ] **Step 1: Implement snapshot helpers**

```python
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
```

---

## Task 3: Extend Normalizer for DeepSeek

**Files:**
- Modify: `core/normalizer.py`

- [ ] **Step 1: Add DeepSeek normalizer**

Insert after `empty_provider`:

```python
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
```

---

## Task 4: Wire Provider into Collector

**Files:**
- Modify: `core/collector.py`

- [ ] **Step 1: Import and instantiate**

```python
from providers import CodexProvider, DeepSeekProvider, KimiProvider
```

- [ ] **Step 2: Add default config and instances**

Add to `DEFAULT_CONFIG`:

```python
"deepseek": {
    "enabled": True,
    "balance_url": "https://api.deepseek.com/user/balance",
    "preferred_currency": "CNY",
    "daily_snapshot_path": "data/deepseek_daily.json",
},
```

Add to `instances` tuple:

```python
DeepSeekProvider(_provider_config(config.get("deepseek"), timeout_seconds), project_root),
```

---

## Task 5: Update Cache Initial Usage

**Files:**
- Modify: `core/cache.py`

- [ ] **Step 1: Include deepseek**

```python
"deepseek": empty_provider("DeepSeek", "unsupported", message),
```

Note: `empty_provider` currently emits `fiveHour`/`weekly`; acceptable fallback until first refresh writes the deepseek schema. If strict, create deepseek-specific empty in `core/normalizer` and use it.

---

## Task 6: Update Doctor

**Files:**
- Modify: `core/doctor.py`

- [ ] **Step 1: Add DeepSeek checks**

After Kimi checks add:

```python
deepseek_enabled = bool(config.get("deepseek", {}).get("enabled", True))
checks.append(("DEEPSEEK_API_KEY", bool(os.getenv("DEEPSEEK_API_KEY")), _set_text("DEEPSEEK_API_KEY")))
daily_path = resolve_cache_path(project_root, config.get("deepseek", {}).get("daily_snapshot_path", "data/deepseek_daily.json"))
checks.append(("DeepSeek daily snapshot", daily_path.exists(), "exists" if daily_path.exists() else "missing"))
```

If `deepseek_enabled` is False, append a disabled note. Implementation can simply check key presence regardless; disabled provider still shows key status.

---

## Task 7: Update CLI Status Output

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Extend format_status**

Change provider iteration to include `("deepseek", "DeepSeek")` and render balance/today:

```python
for key, label in (("codex", "Codex"), ("kimi", "Kimi"), ("deepseek", "DeepSeek")):
    provider = providers.get(key, {})
    lines.append(label)
    if key == "deepseek":
        balance = provider.get("balance") or {}
        today = provider.get("today") or {}
        if balance.get("total") is not None:
            lines.append(f"  Balance  {balance.get('currency', 'CNY')} {balance['total']:.2f}")
        if today.get("estimatedSpend") is not None:
            lines.append(f"  Today    ~ {today.get('currency', balance.get('currency', 'CNY'))} {today['estimatedSpend']:.2f}")
    else:
        ...existing 5H/Week logic...
    lines.append(f"  Status {provider.get('status', 'error')}")
    ...
```

Currency for today should be taken from `today.get("currency")` if present, else balance currency.

---

## Task 8: Update UI Widget

**Files:**
- Modify: `ui/widget.py`

- [ ] **Step 1: Add DeepSeekCard**

Create subclass of `ProviderCard` or extend `ProviderCard` to render balance/today instead of 5H/Week. Recommended: create `DeepSeekCard(ProviderCard)` that overrides `_row` setup and `update_data`.

- [ ] **Step 2: Add card and resize**

In `_build_ui`:

```python
self.deepseek_card = DeepSeekCard("DeepSeek")
root.addWidget(self.deepseek_card)
```

Set default height to 300 in `DEFAULT_CONFIG` (`core/collector.py`) and `config.yaml`.

- [ ] **Step 3: Update load_cache and _remaining_values**

Render deepseek card, and include deepseek in `_remaining_values` for face calculation (balance remaining percent is not applicable; only include if a numeric value exists, but for face keep Codex/Kimi windows only).

---

## Task 9: Update Configuration Files

**Files:**
- Modify: `config.yaml`
- Modify: `.env`
- Modify: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: config.yaml**

```yaml
deepseek:
  enabled: true
  balance_url: "https://api.deepseek.com/user/balance"
  preferred_currency: "CNY"
  daily_snapshot_path: "data/deepseek_daily.json"
```

- [ ] **Step 2: .env**

Append only (do not modify existing KIMI key):

```
# DeepSeek API key for balance query.
DEEPSEEK_API_KEY=
```

- [ ] **Step 3: .env.example**

Append:

```
# DeepSeek API key for balance query.
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

- [ ] **Step 4: .gitignore**

Ensure `data/deepseek_daily.json` is excluded (add line after `data/ui_state.json`).

---

## Task 10: Write Tests

**Files:**
- Create: `tests/test_deepseek_provider_parser.py`
- Create: `tests/test_deepseek_daily_snapshot.py`
- Create: `tests/test_deepseek_security.py`

- [ ] **Step 1: Parser tests**

Cover CNY single entry, multi-currency preference, missing CNY fallback to first, string to float conversion, missing total_balance error, missing balance_infos error, no `DEEPSEEK_API_KEY` unsupported.

- [ ] **Step 2: Snapshot tests**

Cover first creation, same day spend calculation, top-up warning and zero spend, currency/date reset.

- [ ] **Step 3: Security tests**

Cover `usage.json` and `deepseek_daily.json` do not contain key; `redact_text` catches `sk-...` and `DEEPSEEK_API_KEY=...`.

---

## Task 11: Run Verification

- [ ] **Step 1: Run tests**

```powershell
cd E:\Ronald\CodingPlanWidget
.\codingplan\Scripts\Activate.ps1
python -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run CLI commands**

```powershell
python main.py doctor
python main.py refresh
python main.py status
```

Expected: no traceback; DeepSeek shows unsupported if key missing, otherwise balance/today.

- [ ] **Step 3: Security scan**

Search `data/usage.json`, `data/deepseek_daily.json`, `.env.example`, README, docs for any secret material. Ensure no real key leaked.

---

## Task 12: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/development_log.md`
- Create: `docs/deepseek_provider_notes.md`

- [ ] **Step 1: README**

Add `## DeepSeek API Balance` section after Kimi configuration, explaining `.env` key, balance source, estimated daily spend, and snapshot reset.

- [ ] **Step 2: development_log.md**

Add V1.3 section summarizing DeepSeek provider, daily snapshot, CLI/UI updates, tests.

- [ ] **Step 3: deepseek_provider_notes.md**

Document endpoint, request headers (Authorization redacted), response schema, parsing rules, daily spend estimation, security notes, known limitations.
