"""Safety checks for the release package produced by build_exe.bat."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RELEASE_ROOT = Path(__file__).resolve().parent.parent / "release" / "CodingPlanWidget"
SENSITIVE_RE = re.compile(
    r"(Bearer\s+[A-Za-z0-9._~+/=-]+|"
    r"sk-[A-Za-z0-9_-]{6,}|"
    r"eyJ[A-Za-z0-9._-]{10,})",
    re.IGNORECASE,
)


def test_release_dotenv_example_exists():
    if not RELEASE_ROOT.exists():
        pytest.skip("release package not built yet")
    assert (RELEASE_ROOT / ".env.example").exists()


def test_release_real_dotenv_missing():
    if not RELEASE_ROOT.exists():
        pytest.skip("release package not built yet")
    assert not (RELEASE_ROOT / ".env").exists()


def test_release_data_directory_empty_of_caches():
    if not RELEASE_ROOT.exists():
        pytest.skip("release package not built yet")
    data_dir = RELEASE_ROOT / "data"
    assert data_dir.exists()
    for forbidden in ("usage.json", "deepseek_daily.json", "ui_state.json"):
        assert not (data_dir / forbidden).exists(), f"{forbidden} should not be shipped"


def test_release_no_auth_json():
    if not RELEASE_ROOT.exists():
        pytest.skip("release package not built yet")
    for path in RELEASE_ROOT.rglob("auth.json"):
        pytest.fail(f"Codex auth.json found in release: {path}")


def test_release_text_files_contain_no_secrets():
    if not RELEASE_ROOT.exists():
        pytest.skip("release package not built yet")
    for path in RELEASE_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".exe", ".dll", ".pyd", ".ico", ".png", ".jpg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if SENSITIVE_RE.search(text):
            pytest.fail(f"Potential secret found in {path}")
