"""Hand reader that maps card IDs to profile names."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from jduel_bot.jduel_bot_enums import CardPosition, Player

LOG = logging.getLogger("hand_reader")


@dataclass(frozen=True)
class HandCard:
    index: int
    card_id: int | None
    name: str


def _get_hand_name_lookup(client: object) -> Callable[[int], Optional[str]]:
    name_method = getattr(client, "get_hand_card_name", None)
    if callable(name_method):
        def _lookup(index: int) -> Optional[str]:
            try:
                return name_method(index)
            except Exception:
                return None
        return _lookup
    return lambda _index: None


def read_hand(client: object, profile: dict) -> List[HandCard]:
    cards_by_id: Dict[int, str] = profile.get("cards_by_id", {})
    if not isinstance(cards_by_id, dict):
        cards_by_id = {}

    get_hand_size = getattr(client, "get_hand_size", None)
    if not callable(get_hand_size):
        return []

    get_card_id = getattr(client, "get_card_id", None)
    if not callable(get_card_id):
        return []

    lookup_name = _get_hand_name_lookup(client)
    hand_cards: List[HandCard] = []
    for index in range(int(get_hand_size())):
        card_id = None
        try:
            card_id = get_card_id(Player.Myself, CardPosition.Hand, index)
        except Exception:
            card_id = None
        name = cards_by_id.get(card_id) if card_id is not None else None
        if not name:
            name = lookup_name(index)
        if not name:
            name = "unknown"
        hand_cards.append(HandCard(index=index, card_id=card_id, name=name))
    return hand_cards
