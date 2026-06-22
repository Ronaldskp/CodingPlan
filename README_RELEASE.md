# CodingPlanWidget Release

## Quick Start

The recommended executable is:

```text
E:\Ronald\CodingPlanWidget\release\CodingPlanWidget\CodingPlanWidget.exe
```

An older desktop shortcut may still point to `start_widget_silent.vbs`. From the source
project directory, create or update the EXE shortcut with:

```powershell
powershell -ExecutionPolicy Bypass -File .\create_exe_desktop_shortcut.ps1
```

Alternatively, double-click `create_exe_desktop_shortcut.bat`.

## Configuration

The EXE reads configuration from:

```text
release\CodingPlanWidget\.env
```

It does not use the source directory `.env`. Copy `.env.example` to `.env` inside the
release folder, then add your own API keys. The real `.env` is intentionally not included.

- `.env` — Local API keys; create this file yourself and never share it.
- `config.yaml` — UI and provider settings.
- `data/` — Runtime caches and UI state, created automatically.
- `assets/coding_plan.ico` — Application and shortcut icon.

## Provider Setup

### Kimi

```env
KIMI_API_KEY=your_kimi_api_key_here
```

### DeepSeek

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### Codex

Codex uses the existing `codex` CLI login on this machine. Do not copy Codex
`auth.json` into this folder.

## Security

- Never share or upload `.env`.
- Never upload runtime files from `data/`.
- The EXE does not contain your API keys.

## Troubleshooting

- If the widget does not start, return to the source folder and run `python main.py doctor`.
- If the tray icon is missing, ensure `assets/coding_plan.ico` is present next to the EXE.
- If `.env` is not read, make sure it is in the same folder as `CodingPlanWidget.exe`.
- If data cannot be written, check that the `data/` folder is writable.

## Limitations

- DeepSeek "Today" spend is a local estimate and may be inaccurate after top-ups or grants.
- Codex quota depends on the official endpoint and your local login state.
