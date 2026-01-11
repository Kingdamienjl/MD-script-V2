"""Swordsoul Tenyi strategy implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from jduel_bot.jduel_bot_enums import CardSelection

from logic.swordsoul_planner import plan_main1_swordsoul_tenyi

LOG = logging.getLogger("swordsoul_tenyi.strategy")


def _dialog_priority(profile: dict) -> list[str]:
    if isinstance(profile.get("dialog_pick_priority"), list):
        return [str(x) for x in profile["dialog_pick_priority"]]
    return []


def _pick_by_priority(dialog_cards: list[str], priority: list[str]) -> Optional[CardSelection]:
    if not dialog_cards:
        return None
    cards = [str(card) for card in dialog_cards]
    for wanted in priority:
        for index, card in enumerate(cards):
            if card == wanted:
                return CardSelection(card_name=card, card_index=index)
    return CardSelection(card_name=cards[0], card_index=0)


@dataclass
class SwordsoulTenyiStrategy:
    profile: dict
    name: str = "default"

    def plan_main_phase_1(self, state: dict, hand, client: object, cfg) -> list:
        return plan_main1_swordsoul_tenyi(state, hand, self.profile, client, cfg)

    def on_dialog(
        self,
        dialog_cards: list[str],
        state: dict,
        client: object,
        cfg,
    ) -> Optional[CardSelection]:
        if not dialog_cards:
            return None
        priority = _dialog_priority(self.profile)
        selection = _pick_by_priority(dialog_cards, priority)
        if selection:
            LOG.info("[DIALOG] prefer=%s index=%s", selection.card_name, selection.card_index)
        return selection


def get_strategy(profile: dict, strategy_name: str):
    name = (strategy_name or "default").lower().strip()
    return SwordsoulTenyiStrategy(profile=profile, name=name)
