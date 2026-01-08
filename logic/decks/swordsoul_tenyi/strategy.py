"""Swordsoul Tenyi strategy implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.state_manager import Snapshot
from logic.strategy_base import CardSelection, Strategy


@dataclass(frozen=True)
class SwordsoulTenyiStrategy(Strategy):
    name: str
    deck_name: str
    profile: dict

    def plan_main_phase_1(
        self, state: Snapshot, client: object, cfg: BotConfig
    ) -> list[Action]:
        actions: list[Action] = []
        starters = tuple(self.profile.get("starters", []))
        spells = tuple(self.profile.get("spells", []))
        traps = tuple(self.profile.get("traps", []))
        extra_deck_priority = tuple(self.profile.get("extra_deck_priority", []))
        strict_profile = cfg.strict_profile

        if state.can_normal_summon and state.free_monster_zones > 0:
            starter_pick = self._pick_card_by_preference(
                state.hand,
                ["Swordsoul of Mo Ye", "Swordsoul of Taia"],
                starters,
                strict_profile,
            )
            if starter_pick:
                hand_index, card_name = starter_pick
                actions.append(
                    Action(
                        type="normal_summon",
                        args={"hand_index": hand_index, "card_name": card_name},
                        description=f"Normal summon {card_name}",
                    )
                )
                actions.append(
                    Action(
                        type="activate_effect",
                        args={"field_index": 0, "card_name": card_name},
                        description=f"Activate effect of {card_name}",
                    )
                )
                for name in extra_deck_priority:
                    actions.append(
                        Action(
                            type="extra_deck_summon",
                            args={"name": name},
                            description=f"Extra deck summon {name}",
                        )
                    )
                return actions

        if state.free_spell_trap_zones > 0:
            backrow_pick = self._pick_card_by_preference(
                state.hand,
                [],
                spells + traps,
                strict_profile,
            )
            if backrow_pick:
                hand_index, card_name = backrow_pick
                actions.append(
                    Action(
                        type="set_spell_trap",
                        args={"hand_index": hand_index, "card_name": card_name},
                        description=f"Set {card_name}",
                    )
                )
                return actions

        actions.append(
            Action(
                type="advance_phase",
                args={"phase": "battle"},
                description="Advance to battle phase",
            )
        )
        return actions

    def on_dialog(
        self,
        dialog_cards: list[str],
        state: Snapshot,
        client: object,
        cfg: BotConfig,
    ) -> Optional[list[CardSelection]]:
        return None

    def _pick_card_by_preference(
        self,
        hand,
        preferred_names: Iterable[str],
        allowed_names: Iterable[str],
        strict_profile: bool,
    ) -> Optional[tuple[int, str]]:
        allowed_set = set(allowed_names)
        named_cards = [card for card in hand if card.name]
        for card in named_cards:
            if strict_profile and card.name not in allowed_set:
                logging.info("[PROFILE] blocked unknown card name=%s", card.name)
        for name in preferred_names:
            for card in named_cards:
                if card.name == name and name in allowed_set:
                    return card.index, card.name
        for card in named_cards:
            if strict_profile:
                if card.name in allowed_set:
                    return card.index, card.name
            else:
                return card.index, card.name
        return None


def get_strategy(profile: dict, strategy_name: str = "default") -> Strategy:
    name = strategy_name or "default"
    return SwordsoulTenyiStrategy(name=name, deck_name="swordsoul_tenyi", profile=profile)
