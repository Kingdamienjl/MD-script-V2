"""Swordsoul Tenyi opener planner."""

from __future__ import annotations

from typing import Iterable, List, Optional

from logic.action_queue import Action
from logic.hand_reader import HandCard
from logic.tenyi_extension import plan_tenyi_extension


def _card_tags(profile: dict, name: str) -> list[str]:
    cards = profile.get("cards", {})
    if not isinstance(cards, dict):
        return []
    data = cards.get(name, {})
    if not isinstance(data, dict):
        return []
    tags = data.get("tags", [])
    return [str(tag) for tag in tags] if isinstance(tags, list) else []


def _find_by_name(hand: Iterable[HandCard], name: str) -> Optional[HandCard]:
    for card in hand:
        if card.name == name:
            return card
    return None


def _find_discard_fodder(hand: Iterable[HandCard], profile: dict, exclude: str) -> Optional[HandCard]:
    for card in hand:
        if card.name == exclude:
            continue
        if "discard_fodder" in _card_tags(profile, card.name):
            return card
    return None


def _pick_extra_target(profile: dict, options: list[str]) -> Optional[str]:
    priority = profile.get("extra_deck_priority", [])
    if isinstance(priority, list):
        for name in priority:
            if name in options:
                return name
    for name in options:
        return name
    return None


def plan_main1_swordsoul_tenyi(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    cfg,
) -> List[Action]:
    mo_ye = _find_by_name(hand, "Swordsoul of Mo Ye")
    if mo_ye:
        search_target = (
            "Swordsoul Emergence"
            if _find_by_name(hand, "Swordsoul Strategist Longyuan")
            else "Swordsoul Strategist Longyuan"
        )
        return [
            Action(
                type="normal_summon",
                args={"index": mo_ye.index, "position": "attack"},
                description="Normal summon Swordsoul of Mo Ye",
            ),
            Action(
                type="extra_summon",
                args={"name": "Swordsoul Grandmaster - Chixiao", "positions": ["attack"]},
                description="Synchro summon Chixiao",
            ),
            Action(
                type="activate_field",
                args={"position": 0, "search_target": search_target},
                description=f"Chixiao search {search_target}",
            ),
        ]

    longyuan = _find_by_name(hand, "Swordsoul Strategist Longyuan")
    if longyuan:
        fodder = _find_discard_fodder(hand, profile, longyuan.name)
        if fodder:
            extra_target = _pick_extra_target(
                profile,
                ["Baronne de Fleur", "Swordsoul Supreme Sovereign - Chengying"],
            )
            actions = [
                Action(
                    type="special_summon_hand",
                    args={"index": longyuan.index, "position": "attack"},
                    description=f"Special summon Longyuan (discard {fodder.name})",
                )
            ]
            if extra_target:
                actions.append(
                    Action(
                        type="extra_summon",
                        args={"name": extra_target, "positions": ["attack"]},
                        description=f"Synchro summon {extra_target}",
                    )
                )
            return actions

    ashuna = _find_by_name(hand, "Tenyi Spirit - Ashuna")
    if ashuna:
        actions = [
            Action(
                type="activate_hand",
                args={"index": ashuna.index},
                description="Activate Ashuna from hand",
            )
        ]
        actions.extend(plan_tenyi_extension(state, hand, profile, cfg))
        if not _find_by_name(hand, "Swordsoul of Mo Ye"):
            actions.append(
                Action(
                    type="extra_summon",
                    args={"name": "Monk of the Tenyi", "positions": ["attack"]},
                    description="Link summon Monk of the Tenyi",
                )
            )
        return actions

    return [Action(type="pass", description="Swordsoul Tenyi planner fallback -> pass")]
