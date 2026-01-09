"""Swordsoul Tenyi planner (priority_groups + handlers)."""

from __future__ import annotations

from typing import List

from logic.action_queue import Action
from logic.hand_reader import HandCard
from logic.rulesets.swordsoul_tenyi.handlers import build_handlers


def _default_priority_groups() -> dict:
    return {
        "normal_summon": [
            "Swordsoul of Mo Ye",
            "Swordsoul of Taia",
            "Incredible Ecclesia, the Virtuous",
        ],
        "special_summon": [
            "Swordsoul Strategist Longyuan",
        ],
        "spells": [
            "Swordsoul Emergence",
        ],
        "sets": [
            "Swordsoul Blackout",
            "Infinite Impermanence",
            "Called by the Grave",
            "Crossout Designator",
        ],
        "tenyi": [
            "Tenyi Spirit - Ashuna",
            "Tenyi Spirit - Vishuda",
            "Tenyi Spirit - Adhara",
            "Tenyi Spirit - Shthana",
        ],
    }


def plan_main1_swordsoul_tenyi(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg,
) -> List[Action]:
    priority_groups = profile.get("priority_groups")
    if not isinstance(priority_groups, dict) or not priority_groups:
        priority_groups = _default_priority_groups()

    handlers = build_handlers(profile)

    # ordered passes through groups
    for group_name in ("normal_summon", "special_summon", "spells", "sets", "tenyi", "extra_deck"):
        cards = priority_groups.get(group_name, [])
        if not isinstance(cards, list):
            continue

        for card_name in cards:
            handler = handlers.get(card_name)
            if handler is None:
                continue
            actions = handler(state, hand, profile, client, cfg)
            if actions:
                return actions

    return [Action(type="pass", args={}, description="Swordsoul Tenyi planner fallback -> pass")]
