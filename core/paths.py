"""Runtime path resolution for source and PyInstaller EXE runs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def project_root() -> Path:
    """Return the directory that should contain .env, config.yaml, data/, assets/."""
    if _is_frozen():
        # EXE runs next to its bundled files; do NOT use sys._MEIPASS for writes.
        return Path(sys.executable).resolve().parent
    # Source run: core/paths.py -> core/ -> project root.
    return Path(__file__).resolve().parent.parent


def meipass_root() -> Path | None:
    """PyInstaller's temporary extraction folder, for bundled read-only resources only."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def data_path(relative: str | Path = "") -> Path:
    base = project_root() / "data"
    if not relative:
        return base
    return base / relative


def ensure_data_dir() -> Path:
    path = data_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return project_root() / "config.yaml"


def dotenv_path() -> Path:
    return project_root() / ".env"


def assets_path(relative: str | Path = "") -> Path:
    base = project_root() / "assets"
    if not relative:
        return base
    return base / relative


def application_icon_path() -> Path:
    """Prefer external icon, otherwise fall back to a bundled read-only icon."""
    external = assets_path("coding_plan.ico")
    if external.exists():
        return external
    meipass = meipass_root()
    if meipass:
        bundled = meipass / "assets" / "coding_plan.ico"
        if bundled.exists():
            return bundled
    return external


def load_dotenv_if_present(override: bool = False) -> None:
    """Load external .env if it exists."""
    from dotenv import load_dotenv

    path = dotenv_path()
    if path.exists():
        load_dotenv(str(path), override=override)


def resolve_configured_path(configured: str | Path) -> Path:
    """Resolve a configured relative path against the runtime project root."""
    path = Path(configured)
    return path if path.is_absolute() else project_root() / path
