"""Strategy interface for deck-specific planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.state_manager import Snapshot


@dataclass(frozen=True)
class CardSelection:
    index: Optional[int]
    button: str = "left"


class Strategy(Protocol):
    name: str
    deck_name: str

    def plan_main_phase_1(
        self, state: Snapshot, client: object, cfg: BotConfig
    ) -> list[Action]:
        ...

    def on_dialog(
        self,
        dialog_cards: list[str],
        state: Snapshot,
        client: object,
        cfg: BotConfig,
    ) -> Optional[list[CardSelection]]:
        ...
