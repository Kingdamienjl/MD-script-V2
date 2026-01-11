"""Swordsoul Tenyi opener planner."""

from __future__ import annotations

from typing import Iterable, List, Optional

from logic.action_queue import Action
from logic.hand_reader import HandCard

# Optional tenyi extension planner
try:
    from logic.tenyi_extension import plan_tenyi_extension  # type: ignore
except Exception:  # pragma: no cover
    def plan_tenyi_extension(_state: dict, _hand: List[HandCard], _profile: dict, _cfg) -> List[Action]:
        return []

# Optional handler-based planner
try:
    from logic.rulesets.swordsoul_tenyi.handlers import build_handlers  # type: ignore
except Exception:  # pragma: no cover
    build_handlers = None  # type: ignore


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


def plan_main1_swordsoul_tenyi(state: dict, hand: List[HandCard], profile: dict, cfg) -> List[Action]:
    """
    Two-layer approach:
    1) If profile.priority_groups exists AND build_handlers() exists -> use handler-priority loop.
    2) Else fallback to simple deterministic heuristic opener plan.
    """

    # (1) handler-based priority planning
    priority_groups = profile.get("priority_groups")
    if isinstance(priority_groups, dict) and callable(build_handlers):
        handlers = build_handlers(profile)
        for group_name in ("normal_summon", "special_summon", "spells", "sets", "extra_deck"):
            cards = priority_groups.get(group_name, [])
            if not isinstance(cards, list):
                continue
            for card_name in cards:
                handler = handlers.get(card_name)
                if handler is None:
                    continue
                actions = handler(state, hand, profile, getattr(cfg, "client", None), cfg)  # client may not be needed
                if actions:
                    return actions

    # (2) heuristic fallback (works even if priority_groups not present)
    mo_ye = _find_by_name(hand, "Swordsoul of Mo Ye")
    if mo_ye:
        search_target = (
            "Swordsoul Emergence"
            if _find_by_name(hand, "Swordsoul Strategist Longyuan")
            else "Swordsoul Strategist Longyuan"
        )
        return [
            Action(type="normal_summon", args={"index": mo_ye.index, "position": "attack"}, description="Normal summon Mo Ye"),
            Action(type="extra_summon", args={"name": "Swordsoul Grandmaster - Chixiao", "positions": ["attack"]}, description="Synchro summon Chixiao"),
            Action(type="activate_field", args={"position": 0, "search_target": search_target}, description=f"Chixiao search {search_target}"),
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
            Action(type="activate_hand", args={"index": ashuna.index}, description="Activate Ashuna from hand"),
        ]
        actions.extend(plan_tenyi_extension(state, hand, profile, cfg))
        if not _find_by_name(hand, "Swordsoul of Mo Ye"):
            actions.append(
                Action(type="extra_summon", args={"name": "Monk of the Tenyi", "positions": ["attack"]}, description="Link summon Monk of the Tenyi")
            )
        return actions

    return [Action(type="pass", args={}, description="Planner fallback -> pass")]
