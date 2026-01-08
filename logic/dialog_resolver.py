"""Dialog resolver with loop detection and safe bailout."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, Sequence


class DialogButtonType(str, Enum):
    Left = "left"
    Right = "right"


@dataclass(frozen=True)
class DialogSnapshot:
    cards: tuple[str, ...]
    timestamp: float


class DialogResolver:
    def __init__(self, max_memory: int = 5) -> None:
        self._memory: Deque[DialogSnapshot] = deque(maxlen=max_memory)

    def resolve(self, client: object) -> str:
        dialog_list = list(getattr(client, "get_dialog_card_list", lambda: [])())
        snapshot = DialogSnapshot(cards=tuple(dialog_list), timestamp=time.monotonic())
        self._memory.append(snapshot)
        logging.info("[DIALOG] snapshot=%s", dialog_list)

        repeats = self._count_repeats(snapshot)
        if repeats >= 3:
            logging.warning("[DIALOG] stuck_detected repeats=%s", repeats)
            getattr(client, "cancel_activation_prompts", lambda: None)()
            getattr(client, "handle_unexpected_prompts", lambda: None)()
            getattr(client, "select_card_from_dialog", lambda *_args: None)(
                None, DialogButtonType.Right
            )
            if getattr(client, "is_inputting", lambda: False)():
                logging.warning("[DIALOG] bailout")
                return "bailout"
        return "handled"

    def _count_repeats(self, snapshot: DialogSnapshot) -> int:
        window_start = snapshot.timestamp - 5.0
        repeats = 0
        for item in self._memory:
            if item.timestamp >= window_start and item.cards == snapshot.cards:
                repeats += 1
        return repeats
