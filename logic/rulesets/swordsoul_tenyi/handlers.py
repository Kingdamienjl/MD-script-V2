"""Per-card handlers for the Swordsoul Tenyi ruleset."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List

from logic.action_queue import Action
from logic.command_inspector import (
    can_activate_hand,
    can_normal_summon_hand,
    can_set_spell,
    can_special_summon_hand,
)
from logic.hand_reader import HandCard

LOG = logging.getLogger("swordsoul_tenyi.handlers")

Handler = Callable[[dict, List[HandCard], dict, object, object], List[Action]]


def _find_by_name(hand: List[HandCard], name: str) -> HandCard | None:
    for card in hand:
        if card.name == name:
            return card
    return None


def _stub_handler(name: str) -> Handler:
    def _handler(
        _state: dict,
        _hand: List[HandCard],
        _profile: dict,
        _client: object,
        _cfg: object,
    ) -> List[Action]:
        LOG.debug("handler stub=%s", name)
        return []

    return _handler


def handle_moye(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Swordsoul of Mo Ye")
    if not card or not can_normal_summon_hand(client, card.index):
        return []
    return [
        Action(
            type="normal_summon",
            args={"index": card.index, "position": "attack"},
            description="Normal summon Swordsoul of Mo Ye",
        )
    ]


def handle_longyuan(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Swordsoul Strategist Longyuan")
    if not card or not can_special_summon_hand(client, card.index):
        return []
    return [
        Action(
            type="special_summon_hand",
            args={"index": card.index, "position": "attack"},
            description="Special summon Longyuan",
        )
    ]


def handle_taia(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Swordsoul of Taia")
    if not card or not can_normal_summon_hand(client, card.index):
        return []
    return [
        Action(
            type="normal_summon",
            args={"index": card.index, "position": "attack"},
            description="Normal summon Swordsoul of Taia",
        )
    ]


def handle_ecclesia(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Incredible Ecclesia, the Virtuous")
    if not card or not can_normal_summon_hand(client, card.index):
        return []
    return [
        Action(
            type="normal_summon",
            args={"index": card.index, "position": "attack"},
            description="Normal summon Incredible Ecclesia, the Virtuous",
        )
    ]


def handle_emergence(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Swordsoul Emergence")
    if not card or not can_activate_hand(client, card.index):
        return []
    return [
        Action(
            type="activate_spell_hand",
            args={"index": card.index, "position": "face_up"},
            description="Activate Swordsoul Emergence",
        )
    ]


def handle_blackout(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Swordsoul Blackout")
    if not card or not can_set_spell(client, card.index):
        return []
    return [
        Action(
            type="set_spell_hand",
            args={"index": card.index, "position": "set"},
            description="Set Swordsoul Blackout",
        )
    ]


def handle_ashuna(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Tenyi Spirit - Ashuna")
    if not card or not can_activate_hand(client, card.index):
        return []
    return [
        Action(
            type="activate_hand",
            args={"index": card.index},
            description="Activate Tenyi Spirit - Ashuna",
        )
    ]


def handle_vishuda(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Tenyi Spirit - Vishuda")
    if not card or not can_activate_hand(client, card.index):
        return []
    return [
        Action(
            type="activate_hand",
            args={"index": card.index},
            description="Activate Tenyi Spirit - Vishuda",
        )
    ]


def handle_adhara(
    state: dict,
    hand: List[HandCard],
    profile: dict,
    client: object,
    cfg: object,
) -> List[Action]:
    card = _find_by_name(hand, "Tenyi Spirit - Adhara")
    if not card or not can_activate_hand(client, card.index):
        return []
    return [
        Action(
            type="activate_hand",
            args={"index": card.index},
            description="Activate Tenyi Spirit - Adhara",
        )
    ]


def build_handlers(profile: dict) -> Dict[str, Handler]:
    handlers: Dict[str, Handler] = {
        "Swordsoul of Mo Ye": handle_moye,
        "Swordsoul Strategist Longyuan": handle_longyuan,
        "Swordsoul of Taia": handle_taia,
        "Incredible Ecclesia, the Virtuous": handle_ecclesia,
        "Swordsoul Emergence": handle_emergence,
        "Swordsoul Blackout": handle_blackout,
        "Tenyi Spirit - Ashuna": handle_ashuna,
        "Tenyi Spirit - Vishuda": handle_vishuda,
        "Tenyi Spirit - Adhara": handle_adhara,
    }
    cards = profile.get("cards", {})
    if isinstance(cards, dict):
        for name in cards.keys():
            if name not in handlers:
                handlers[name] = _stub_handler(name)
    return handlers
