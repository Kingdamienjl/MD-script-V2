"""Plan steps for Swordsoul Tenyi ruleset."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlanAction(str, Enum):
    NORMAL_SUMMON = "normal_summon"
    ACTIVATE_FROM_HAND = "activate_hand_effect"
    ACTIVATE_FROM_FIELD = "activate_effect"
    SPECIAL_FROM_HAND = "special_summon"
    SET_SPELL_TRAP = "set_spell_trap"
    EXTRA_DECK_SUMMON = "extra_deck_summon"


@dataclass(frozen=True)
class PlanStep:
    action: PlanAction
    card_name: Optional[str] = None
    note: str = ""

    def describe(self) -> str:
        if self.card_name:
            return f"{self.action}({self.card_name})"
        return str(self.action)
