"""Centralized secret redaction for console, logs, errors, and cache data."""

from __future__ import annotations

import json
import re
from typing import Any

SENSITIVE_KEY_RE = re.compile(
    r"(api[_ -]?key|authorization|bearer|access[_ -]?token|refresh[_ -]?token|"
    r"session[_ -]?token|cookie|auth(?:\.json)?|password|secret)",
    re.IGNORECASE,
)

VALUE_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(access_token|refresh_token|session_token|api[_-]?key|cookie)"
               r"(\s*[=:]\s*[\"']?)[^,\s\"'}]+"),
    re.compile(r"(?i)(KIMI(?:_CODING)?_API_KEY)(\s*=\s*)[^\s\"']+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9._-]{10,}\b"),
)


def redact_text(value: Any) -> str:
    text = str(value)
    text = VALUE_PATTERNS[0].sub("Bearer [REDACTED]", text)
    for pattern in VALUE_PATTERNS[1:]:
        if pattern.groups >= 2:
            text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    text = re.sub(
        r"(?i)(auth\.json)(?:\s+content)?\s*[=:]\s*\{.*",
        r"\1 content=[REDACTED]",
        text,
    )
    return text


def sanitize_message(value: Any, max_length: int = 500) -> str:
    text = redact_text(value).replace("\r", " ").replace("\n", " ").strip()
    return text[:max_length]


def sanitize_data(value: Any) -> Any:
    """Remove sensitive fields recursively before persisted output."""
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                continue
            clean[str(key)] = sanitize_data(item)
        return clean
    if isinstance(value, list):
        return [sanitize_data(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_data(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def safe_json(value: Any) -> str:
    return json.dumps(sanitize_data(value), ensure_ascii=False, sort_keys=True)
