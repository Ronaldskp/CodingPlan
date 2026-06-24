# UI Notes

## Design Principles

- Information first: show percentages, balances, and reset times at a glance.
- Small window: default 280×300 expanded, compact collapsed mode.
- Short error text in cards (`offline`, `network error`, `unsupported`).
- Full provider messages go to debug logs/tooltips, not the small card.

## Reset Time Display

- Codex reset time comes from the official usage response or custom command JSON.
- Kimi reset time comes from `kimi-usage --json` (`5h Limit` / `Weekly Usage` items).
- If reset time is missing or unparsable, the UI shows `--`.
- Stale fallback preserves the last known reset time alongside the last known percentage.

## Collapsed Summary

```text
C 99/75  K 70/52  DS 58.23
R C18:44 K18:44    Fresh
```

- First line: Codex/Kimi 5H/WEEK percentages and DeepSeek balance.
- Second line (optional): 5H reset times and cache freshness.

## Config

```yaml
ui:
  show_reset_times: true
  reset_display_mode: "time"
  compact_summary_show_reset: true
```
