"""Minimal Swordsoul opener planner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from logic.profile import ProfileIndex


@dataclass(frozen=True)
class Intent:
    kind: str
    name: Optional[str] = None
    candidates: tuple[str, ...] = ()

    def describe(self) -> str:
        if self.name:
            return f"{self.kind}({self.name})"
        if self.candidates:
            return f"{self.kind}({', '.join(self.candidates)})"
        return self.kind


class SwordsoulPlanner:
    def __init__(self, profile_index: ProfileIndex) -> None:
        self.profile_index = profile_index

    def plan(
        self,
        hand_names: Iterable[str],
        dialog_cards: Iterable[str] | None = None,
        board_state: dict | None = None,
    ) -> list[Intent]:
        _ = (dialog_cards, board_state)
        intents: list[Intent] = []
        hand = list(hand_names)

        if "Swordsoul of Mo Ye" in hand:
            intents.append(Intent("NORMAL_SUMMON", "Swordsoul of Mo Ye"))
            intents.append(Intent("ACTIVATE_FIELD_EFFECT", "Swordsoul of Mo Ye"))
        elif "Swordsoul of Taia" in hand:
            intents.append(Intent("NORMAL_SUMMON", "Swordsoul of Taia"))
            intents.append(Intent("ACTIVATE_FIELD_EFFECT", "Swordsoul of Taia"))

        if "Swordsoul Strategist Longyuan" in hand:
            discardables = [
                name for name in hand
                if name in self.profile_index.extenders and name != "Swordsoul Strategist Longyuan"
            ]
            if discardables:
                intents.append(
                    Intent("SPECIAL_SUMMON_FROM_HAND", "Swordsoul Strategist Longyuan")
                )

        if self.profile_index.extra_deck_priority:
            intents.append(
                Intent(
                    "EXTRA_DECK_SUMMON",
                    candidates=self.profile_index.extra_deck_priority,
                )
            )

        backrow = list(self.profile_index.traps + self.profile_index.spells)
        for name in backrow:
            if name in hand:
                intents.append(Intent("SET_BACKROW", name))
                break

        return intents
