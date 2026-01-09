"""Action dataclass for plan execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class Action:
    type: str
    args: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    retries: int = 1
    delay_ms: int = 80
