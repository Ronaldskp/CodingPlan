# Packaging Notes

## Why PyInstaller

PyInstaller bundles the Python interpreter and dependencies into a single folder that behaves like a native Windows application. It requires no changes to the PySide6 code beyond path handling.

## Why onedir instead of onefile

- PySide6 onefile EXEs have slower cold-start because the onefile bootloader extracts everything to a temp folder before importing Qt.
- onedir makes it easier to inspect bundled files and debug missing plugins.
- External `config.yaml`, `.env`, and `data/` are clearer in onedir layout.

## Entry Point

`app_launcher.py` is the PyInstaller entry point. It calls `main(["widget"])`, so the EXE always launches the GUI. The original `main.py` CLI remains available from source.

## External Files

The EXE reads and writes from its own directory, not from `sys._MEIPASS`:

- `.env` — loaded from `CodingPlanWidget.exe` sibling directory.
- `config.yaml` — loaded from the same directory.
- `data/` — created and written there.
- `assets/coding_plan.ico` — preferred external; bundled icon is a fallback.

## Why .env is not embedded

Embedding API keys in a binary does not provide real security and makes key rotation impossible. Keeping `.env` external lets users configure keys without rebuilding.

## V1.4.1+ UI Behavior

The EXE supports the same collapse/expand and in-window refresh button as the source version:

- Title-bar `↻` triggers a background refresh.
- Title-bar `˄`/`˅` toggles collapsed summary mode.
- Clicking the title bar (without dragging) also toggles collapse if enabled in `config.yaml`.
- The collapsed summary includes Fresh/Stale/Expired and shows `Refreshing...` during a background refresh.
- Folded state and window position are saved to `data/ui_state.json`.

## V1.5+ Reset Time Display

V1.5 shows Codex/Kimi 5H reset times in expanded cards and the optional collapsed summary line. No packaging changes are required; `config.yaml` enables the new options by default.

## Release Layout

```text
release\CodingPlanWidget\
├─ CodingPlanWidget.exe
├─ config.yaml
├─ .env.example
├─ README_RELEASE.md
├─ assets\coding_plan.ico
└─ data\
   ├─ .gitkeep
   └─ README.md
```

## Troubleshooting

### PySide6 plugin missing

If the widget fails with platform plugin errors, add the `platforms` directory to `datas` in the spec.

### Icon not showing

Ensure `assets/coding_plan.ico` exists next to the EXE. If missing, the app falls back to a generated CP icon.

### .env not read

Check that `.env` is in the same folder as `CodingPlanWidget.exe`, not inside `dist/`.

### Cannot write data

The EXE must have write permission to its own `data/` directory. Do not install into `Program Files` without adjusting permissions.

### Antivirus false positive

PyInstaller bootloaders are sometimes flagged. If this happens, add an exclusion or build with a custom signed bootloader.

## Future Options

- onefile mode for a single-file distribution.
- WiX/NSIS installer for `Program Files` deployment.
- Windows Task Scheduler for startup.
