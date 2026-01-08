"""Minimal Swordsoul opener planner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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

    def plan(self, ctx: dict) -> list[Intent]:
        intents: list[Intent] = []
        hand = list(ctx.get("hand_names", []))

        starter = self._pick_first_in_priority(hand, self.profile_index.starters_priority)
        if starter:
            intents.append(Intent("NORMAL_SUMMON", starter))
            intents.append(Intent("ACTIVATE_FIELD_EFFECT", starter))

        longyuan_name = "Swordsoul Strategist Longyuan"
        if longyuan_name in hand and self.profile_index.is_allowed(longyuan_name):
            discardable = self._pick_first_in_priority(
                [name for name in hand if name != longyuan_name],
                self.profile_index.discard_priority,
            )
            if discardable:
                intents.append(Intent("SPECIAL_SUMMON_FROM_HAND", longyuan_name))

        if self.profile_index.extra_deck_priority:
            intents.append(
                Intent(
                    "EXTRA_DECK_SUMMON",
                    candidates=self.profile_index.extra_deck_priority,
                )
            )

        backrow = self._pick_first_in_priority(
            hand, self.profile_index.set_backrow_priority
        )
        if backrow:
            intents.append(Intent("SET_BACKROW", backrow))

        return intents

    def _pick_first_in_priority(
        self, hand: list[str], priority_list: tuple[str, ...]
    ) -> Optional[str]:
        for name in priority_list:
            if name in hand:
                return name
        return None
