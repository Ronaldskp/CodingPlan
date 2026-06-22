"""Tests for runtime path resolution."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import core.paths as paths


def test_project_root_in_source_mode():
    root = paths.project_root()
    assert (root / "main.py").exists()
    assert (root / "config.yaml").exists()


def test_data_path_creates_parent_on_demand(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    assert paths.data_path() == tmp_path / "data"


def test_ensure_data_dir_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    result = paths.ensure_data_dir()
    assert result.exists()
    assert result.is_dir()


def test_config_path_and_dotenv_path(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    assert paths.config_path() == tmp_path / "config.yaml"
    assert paths.dotenv_path() == tmp_path / ".env"


def test_assets_path_returns_external_path(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    assert paths.assets_path("coding_plan.ico") == tmp_path / "assets" / "coding_plan.ico"


def test_application_icon_path_prefers_external(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "coding_plan.ico").write_text("fake", encoding="utf-8")
    assert paths.application_icon_path() == tmp_path / "assets" / "coding_plan.ico"


def test_application_icon_path_falls_back_to_meipass(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    meipass = tmp_path / "_internal"
    (meipass / "assets").mkdir(parents=True)
    (meipass / "assets" / "coding_plan.ico").write_text("bundled", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert paths.application_icon_path() == meipass / "assets" / "coding_plan.ico"


def test_application_icon_path_returns_nonexistent_external_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    expected = tmp_path / "assets" / "coding_plan.ico"
    assert paths.application_icon_path() == expected
    assert not paths.application_icon_path().exists()


def test_resolve_configured_path_absolute():
    assert paths.resolve_configured_path("C:\\tmp\\x.json") == Path("C:\\tmp\\x.json")


def test_resolve_configured_path_relative(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "project_root", lambda: tmp_path)
    assert paths.resolve_configured_path("data/usage.json") == tmp_path / "data" / "usage.json"
