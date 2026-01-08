"""Strategy registry for card handlers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict


Handler = Callable[[object, dict], list]


def default_handler(_context: object, _state: dict) -> list:
    return []


@dataclass
class StrategyRegistry:
    _handlers: Dict[str, Handler] = field(default_factory=dict)

    def register(self, name: str) -> Callable[[Handler], Handler]:
        def decorator(fn: Handler) -> Handler:
            self._handlers[name] = fn
            return fn
        return decorator

    def get(self, name: str) -> Handler:
        handler = self._handlers.get(name)
        if handler is None:
            logging.info("[STRATEGY] missing_handler name=%s -> default", name)
            return default_handler
        return handler
