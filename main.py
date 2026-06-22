"""CodingPlanWidget command-line entry point."""

from __future__ import annotations

import argparse
from typing import Any

from core.cache import read_usage, resolve_cache_path
from core.collector import collect_usage, load_config
from core.doctor import format_doctor, run_doctor
from core.freshness import format_updated_with_freshness
from core.paths import project_root
from core.security import sanitize_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex, Kimi and DeepSeek Coding Plan desktop widget")
    parser.add_argument("command", choices=("doctor", "status", "refresh", "widget"))
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = project_root()
    config = load_config(root)
    if args.command == "doctor":
        print(format_doctor(run_doctor(root, config)))
        return 0
    if args.command == "refresh":
        usage = collect_usage(root, config)
        print(format_status(usage))
        return 0
    if args.command == "status":
        path = resolve_cache_path(root, config["app"]["cache_path"])
        print(format_status(read_usage(path, create_if_missing=True)))
        return 0
    if args.command == "widget":
        try:
            from ui.widget import run_widget
        except ImportError as exc:
            print(f"Unable to start widget: {sanitize_message(exc)}")
            print("Install dependencies with: pip install -r requirements.txt")
            return 1
        return run_widget(root)
    return 2


def format_status(usage: dict[str, Any]) -> str:
    lines = ["CODING PLAN WIDGET", ""]
    providers = usage.get("providers", {})
    for key, label in (("codex", "Codex"), ("kimi", "Kimi"), ("deepseek", "DeepSeek")):
        provider = providers.get(key, {})
        lines.append(label)
        if key == "deepseek":
            balance = provider.get("balance") or {}
            today = provider.get("today") or {}
            if balance.get("total") is not None:
                currency = str(balance.get("currency") or "CNY")
                lines.append(f"  Balance  {currency} {float(balance['total']):.2f}")
            if today.get("estimatedSpend") is not None:
                today_currency = str(today.get("currency") or balance.get("currency") or "CNY")
                lines.append(f"  Today    ~ {today_currency} {float(today['estimatedSpend']):.2f}")
        else:
            five = _percent(provider.get("fiveHour", {}))
            week = _percent(provider.get("weekly", {}))
            if five is not None:
                lines.append(f"  5H    {five}%")
            if week is not None:
                lines.append(f"  Week  {week}%")
        lines.append(f"  Status {provider.get('status', 'error')}")
        message = sanitize_message(provider.get("message", ""))
        if message:
            lines.append(f"  Message {message}")
        lines.append("")
    lines.append(format_updated_with_freshness(usage.get("updatedAt")))
    return "\n".join(lines)


def _percent(window: Any) -> int | None:
    if not isinstance(window, dict):
        return None
    value = window.get("remainingPercent")
    return round(value) if isinstance(value, (int, float)) else None


if __name__ == "__main__":
    raise SystemExit(main())
