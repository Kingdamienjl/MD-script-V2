"""Tenyi extensions for Swordsoul opener plans."""

from __future__ import annotations

from typing import Iterable

from logic.profile import ProfileIndex
from logic.swordsoul_planner import Intent


def extend_plan_with_tenyi(plan: list[Intent], profile: ProfileIndex, state) -> list[Intent]:
    hand_names = [card.name for card in state.hand if card.name]
    if "Tenyi Spirit - Ashuna" not in hand_names:
        return plan

    monster_count = getattr(state, "monster_count", 0)
    if monster_count > 0:
        return plan

    ashuna_intent = Intent("ACTIVATE_HAND_EFFECT", "Tenyi Spirit - Ashuna")

    has_mo_ye = "Swordsoul of Mo Ye" in hand_names
    has_taia = "Swordsoul of Taia" in hand_names
    if has_mo_ye or has_taia:
        return [ashuna_intent, *plan]

    return plan + [ashuna_intent]
