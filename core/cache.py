"""Safe local usage cache with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.normalizer import empty_provider
from core.security import sanitize_data, sanitize_message


def resolve_cache_path(project_root: Path, configured_path: str) -> Path:
    path = Path(os.path.expandvars(configured_path)).expanduser()
    return path if path.is_absolute() else project_root / path


def initial_usage(message: str = "No usage data collected yet.") -> dict[str, Any]:
    return {
        "updatedAt": None,
        "providers": {
            "codex": empty_provider("Codex", "unsupported", message),
            "kimi": empty_provider("Kimi", "unsupported", message),
            "deepseek": empty_provider("DeepSeek", "unsupported", message),
        },
    }


def write_usage(path: Path, usage: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = sanitize_data(usage)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".usage-",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(clean, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def read_usage(path: Path, create_if_missing: bool = True) -> dict[str, Any]:
    if not path.exists():
        data = initial_usage()
        if create_if_missing:
            write_usage(path, data)
        return data
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or not isinstance(data.get("providers"), dict):
            raise ValueError("cache root is invalid")
        return sanitize_data(data)
    except Exception as exc:
        data = initial_usage(f"Cache error: {sanitize_message(exc)}")
        if create_if_missing:
            write_usage(path, data)
        return data
