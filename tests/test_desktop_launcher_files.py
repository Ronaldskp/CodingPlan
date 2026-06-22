from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_desktop_launcher_files_exist() -> None:
    for name in (
        "start_widget.bat",
        "start_widget_silent.vbs",
        "create_desktop_shortcut.ps1",
    ):
        assert (ROOT / name).is_file()


def test_silent_launcher_uses_pythonw_and_widget_command() -> None:
    text = (ROOT / "start_widget_silent.vbs").read_text(encoding="utf-8")
    assert "codingplan\\Scripts\\pythonw.exe" in text
    assert '""" widget"' in text
    assert "shell.Run cmd, 0, False" in text


def test_shortcut_script_uses_optional_local_icon() -> None:
    text = (ROOT / "create_desktop_shortcut.ps1").read_text(encoding="utf-8")
    assert "CodingPlanWidget.lnk" in text
    assert "start_widget_silent.vbs" in text
    assert "assets\\coding_plan.ico" in text
    assert "KIMI_API_KEY" not in text
