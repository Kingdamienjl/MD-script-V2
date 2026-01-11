"""Tenyi extension helpers."""

from __future__ import annotations

from typing import List

from logic.action_queue import Action
from logic.hand_reader import HandCard


def _find_by_name(hand: List[HandCard], name: str) -> HandCard | None:
    for card in hand:
        if card.name == name:
            return card
    return None


def plan_tenyi_extension(state: dict, hand: List[HandCard], profile: dict, cfg) -> List[Action]:
    actions: List[Action] = []

    vishuda = _find_by_name(hand, "Tenyi Spirit - Vishuda")
    if vishuda:
        actions.append(
            Action(
                type="activate_hand",
                args={"index": vishuda.index},
                description="Activate Vishuda from hand",
            )
        )

    adhara = _find_by_name(hand, "Tenyi Spirit - Adhara")
    if adhara:
        actions.append(
            Action(
                type="activate_hand",
                args={"index": adhara.index},
                description="Activate Adhara from hand",
            )
        )

    return actions
