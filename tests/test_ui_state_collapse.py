from __future__ import annotations

import json

from core.ui_state import read_ui_state, write_ui_state


def test_missing_collapsed_defaults_to_false(tmp_path):
    path = tmp_path / "ui_state.json"
    path.write_text('{"x": 10, "y": 20, "always_on_top": true}', encoding="utf-8")
    assert read_ui_state(path)["collapsed"] is False


def test_collapsed_can_be_saved_and_read(tmp_path):
    path = tmp_path / "ui_state.json"
    write_ui_state(path, {"x": 1, "y": 2, "always_on_top": False, "collapsed": True})
    state = read_ui_state(path)
    assert state["collapsed"] is True


def test_write_preserves_unknown_fields(tmp_path):
    path = tmp_path / "ui_state.json"
    path.write_text('{"x": 0, "y": 0, "custom": 123}', encoding="utf-8")
    write_ui_state(path, {"x": 5, "y": 6, "always_on_top": True})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["custom"] == 123
    assert data["x"] == 5
    assert data["always_on_top"] is True
    assert "collapsed" in data
