"""Small, non-sensitive UI state persisted separately from usage data."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_ui_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"collapsed": False}
    if not isinstance(data, dict):
        return {"collapsed": False}
    state: dict[str, Any] = {"collapsed": False}
    if isinstance(data.get("x"), int):
        state["x"] = data["x"]
    if isinstance(data.get("y"), int):
        state["y"] = data["y"]
    if isinstance(data.get("always_on_top"), bool):
        state["always_on_top"] = data["always_on_top"]
    if isinstance(data.get("collapsed"), bool):
        state["collapsed"] = data["collapsed"]
    for key, value in data.items():
        if key not in state:
            state[key] = value
    return state


def write_ui_state(path: Path, state: dict[str, Any]) -> None:
    existing = read_ui_state(path) if path.exists() else {}
    clean: dict[str, Any] = {**existing}
    clean["x"] = int(state["x"])
    clean["y"] = int(state["y"])
    clean["always_on_top"] = bool(state["always_on_top"])
    collapsed = state.get("collapsed")
    if isinstance(collapsed, bool):
        clean["collapsed"] = collapsed
    elif "collapsed" not in clean:
        clean["collapsed"] = False
    for key, value in state.items():
        if key not in clean:
            clean[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".ui-state-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(clean, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_name = handle.name
        os.replace(temp_name, path)
    finally:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
