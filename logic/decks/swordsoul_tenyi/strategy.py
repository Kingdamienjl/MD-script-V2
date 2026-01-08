"""Swordsoul Tenyi strategy implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.profile import ProfileIndex
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
        profile_index = ProfileIndex(self.profile)
        strict_profile = cfg.strict_profile

        if state.can_normal_summon and state.free_monster_zones > 0:
            starter_pick = self._pick_card_by_preference(
                state.hand,
                ["Swordsoul of Mo Ye", "Swordsoul of Taia"],
                profile_index,
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
                extra_names = profile_index.extra_deck_priority
                if strict_profile:
                    extra_names = tuple(profile_index.filter_allowed(extra_names))
                for name in extra_names:
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
                profile_index,
                strict_profile,
                include_backrow=True,
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
        profile_index = ProfileIndex(self.profile)
        if not cfg.strict_profile:
            return None
        for name in dialog_cards:
            if name and not profile_index.is_allowed(name):
                logging.info("[PROFILE] blocked unknown card name=%s", name)
        allowed_indices = [
            idx for idx, name in enumerate(dialog_cards) if profile_index.is_allowed(name)
        ]
        if not allowed_indices:
            return None
        return [CardSelection(index=allowed_indices[0], button="left")]

    def _pick_card_by_preference(
        self,
        hand,
        preferred_names: Iterable[str],
        profile_index: ProfileIndex,
        strict_profile: bool,
        include_backrow: bool = False,
    ) -> Optional[tuple[int, str]]:
        allowed = profile_index.allowed_names
        named_cards = [card for card in hand if card.name]
        for card in named_cards:
            if strict_profile and card.name not in allowed:
                logging.info("[PROFILE] blocked unknown card name=%s", card.name)
        for name in preferred_names:
            for card in named_cards:
                if card.name == name and profile_index.is_allowed(name):
                    return card.index, card.name
        for card in named_cards:
            if strict_profile:
                if card.name in allowed:
                    return card.index, card.name
            else:
                return card.index, card.name
        if include_backrow and strict_profile:
            return None
        return None


def get_strategy(profile: dict, strategy_name: str = "default") -> Strategy:
    name = strategy_name or "default"
    return SwordsoulTenyiStrategy(name=name, deck_name="swordsoul_tenyi", profile=profile)
