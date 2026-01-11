"""Swordsoul Tenyi opener planner."""

from __future__ import annotations

from typing import List

from logic.action_queue import Action
from logic.hand_reader import HandCard
from logic.rulesets.swordsoul_tenyi.handlers import build_handlers


def plan_main1_swordsoul_tenyi(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg,
) -> List[Action]:
    priority_groups = profile.get("priority_groups", {})
    if not isinstance(priority_groups, dict):
        priority_groups = {}

    handlers = build_handlers(profile)

    for group_name in ("normal_summon", "special_summon", "spells", "sets", "extra_deck"):
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

    return [Action(type="pass", description="Swordsoul Tenyi planner fallback -> pass")]
