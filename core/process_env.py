"""Environment helpers for commands installed beside the active Python."""

from __future__ import annotations

import os
import shutil
import sys


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    scripts_dir = str(os.path.dirname(sys.executable))
    current_path = env.get("PATH", "")
    path_items = current_path.split(os.pathsep) if current_path else []
    if scripts_dir and scripts_dir.lower() not in {item.lower() for item in path_items}:
        env["PATH"] = os.pathsep.join([scripts_dir, current_path]) if current_path else scripts_dir
    return env


def command_found(executable: str) -> bool:
    env = subprocess_env()
    return shutil.which(executable, path=env.get("PATH")) is not None
