"""Provider interface shared by desktop and future hardware front ends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    key: str
    display_name: str

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @property
    def timeout_seconds(self) -> float:
        value = self.config.get("timeout_seconds", 15)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
        return 15.0

    @abstractmethod
    def collect(self) -> dict[str, Any]:
        """Collect and return one normalized provider object."""
