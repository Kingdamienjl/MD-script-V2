"""Swordsoul Tenyi strategy entrypoint."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from logic.rulesets.swordsoul_tenyi import combos, handlers
from logic.strategy_base import CardSelection
from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.strategy")


def _dialog_priority(profile: dict) -> list[str]:
    if isinstance(profile.get("dialog_pick_priority"), list):
        return [str(x) for x in profile["dialog_pick_priority"]]
    priorities = profile.get("priorities")
    if isinstance(priorities, dict) and isinstance(priorities.get("dialog_pick"), list):
        return [str(x) for x in priorities["dialog_pick"]]
    return []


@dataclass
class SwordsoulTenyiStrategy:
    profile: dict
    name: str = "default"

    def plan_main_phase_1(self, state: dict, client: object, cfg) -> list[Action]:
        LOG.info("[STRATEGY] planning main phase 1")
        actions = []

        actions.extend(handlers.handle_moye(state, self.profile, client, cfg))
        actions.extend(handlers.handle_longyuan(state, self.profile, client, cfg))
        actions.extend(handlers.handle_emergence(state, self.profile, client, cfg))
        actions.extend(handlers.handle_taia(state, self.profile, client, cfg))
        actions.extend(handlers.handle_ecclesia(state, self.profile, client, cfg))
        actions.extend(handlers.handle_ashuna(state, self.profile, client, cfg))
        actions.extend(handlers.handle_vishuda(state, self.profile, client, cfg))
        actions.extend(handlers.handle_adhara(state, self.profile, client, cfg))
        actions.extend(handlers.handle_shthana(state, self.profile, client, cfg))
        actions.extend(handlers.handle_blackout(state, self.profile, client, cfg))
        actions.extend(handlers.handle_imperm(state, self.profile, client, cfg))
        actions.extend(handlers.handle_called_by(state, self.profile, client, cfg))
        actions.extend(handlers.handle_crossout(state, self.profile, client, cfg))

        if actions:
            return actions

        LOG.info("[STRATEGY] no immediate handler actions, try opener combos")
        for planner in (combos.plan_moye_line, combos.plan_longyuan_line, combos.plan_ashuna_line):
            combo_actions = planner(state, self.profile, client, cfg)
            if combo_actions:
                return combo_actions

        return [Action(type="pass", description="Swordsoul Tenyi fallback -> pass")]

    def on_dialog(
        self,
        dialog_cards: list[str],
        state: dict,
        client: object,
        cfg,
    ) -> Optional[list[CardSelection]]:
        priority = _dialog_priority(self.profile)
        if not dialog_cards or not priority:
            return None
        cards = [str(card) for card in dialog_cards]
        for wanted in priority:
            for index, card in enumerate(cards):
                if card == wanted:
                    LOG.info("[DIALOG] prefer=%s index=%s", wanted, index)
                    return [CardSelection(index=index, button="left")]
        return None


def get_strategy(profile: dict, strategy_name: str):
    name = (strategy_name or "default").lower().strip()
    return SwordsoulTenyiStrategy(profile=profile, name=name)
