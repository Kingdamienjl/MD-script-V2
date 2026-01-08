"""Swordsoul Tenyi strategy implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.profile import ProfileIndex
from logic.state_manager import Snapshot, TurnCooldowns
from logic.strategy_base import CardSelection, Strategy
from logic.swordsoul_planner import SwordsoulPlanner
from logic.tenyi_extension import extend_plan_with_tenyi


@dataclass(frozen=True)
class SwordsoulTenyiStrategy(Strategy):
    name: str
    deck_name: str
    profile: dict

    def plan_main_phase_1(
        self, state: Snapshot, ctx: dict, cfg: BotConfig
    ) -> list[Action]:
        profile_index = ProfileIndex(self.profile)
        planner = SwordsoulPlanner(profile_index)
        intents = planner.plan(ctx)
        intents = extend_plan_with_tenyi(intents, profile_index, ctx)

        self._apply_ruleset_handlers(ctx)

        cooldowns = ctx.get("turn_cooldowns")

        actions: list[Action] = []
        name_to_index = {
            card.name: card.index for card in state.hand if card.name is not None
        }
        for intent in intents:
            if intent.name and cfg.strict_profile and not profile_index.is_allowed(intent.name):
                logging.info("[PROFILE] blocked unknown card name=%s", intent.name)
                continue
            if intent.kind == "NORMAL_SUMMON" and intent.name:
                if isinstance(cooldowns, TurnCooldowns) and cooldowns.normal_summon_attempts > 0:
                    continue
                hand_index = name_to_index.get(intent.name)
                if hand_index is None:
                    continue
                actions.append(
                    Action(
                        type="normal_summon",
                        args={"hand_index": hand_index, "card_name": intent.name},
                        description=f"Normal summon {intent.name}",
                    )
                )
            elif intent.kind == "ACTIVATE_FIELD_EFFECT" and intent.name:
                if intent.name in profile_index.starters_priority:
                    if intent.name == profile_index.starters_priority[0] and isinstance(
                        cooldowns, TurnCooldowns
                    ):
                        if cooldowns.mo_ye_effect_attempts > 0:
                            continue
                    if len(profile_index.starters_priority) > 1 and intent.name == profile_index.starters_priority[1] and isinstance(
                        cooldowns, TurnCooldowns
                    ):
                        if cooldowns.taia_effect_attempts > 0:
                            continue
                actions.append(
                    Action(
                        type="activate_effect",
                        args={"field_index": 0, "card_name": intent.name},
                        description=f"Activate effect of {intent.name}",
                    )
                )
            elif intent.kind == "ACTIVATE_HAND_EFFECT" and intent.name:
                hand_index = name_to_index.get(intent.name)
                if hand_index is None:
                    continue
                actions.append(
                    Action(
                        type="activate_hand_effect",
                        args={"hand_index": hand_index, "card_name": intent.name},
                        description=f"Activate {intent.name}",
                    )
                )
            elif intent.kind == "SPECIAL_SUMMON_FROM_HAND" and intent.name:
                if intent.name in profile_index.extenders_priority and isinstance(
                    cooldowns, TurnCooldowns
                ):
                    if cooldowns.longyuan_attempts > 0:
                        continue
                hand_index = name_to_index.get(intent.name)
                if hand_index is None:
                    continue
                actions.append(
                    Action(
                        type="special_summon",
                        args={"hand_index": hand_index, "card_name": intent.name},
                        description=f"Special summon {intent.name}",
                    )
                )
            elif intent.kind == "EXTRA_DECK_SUMMON":
                if isinstance(cooldowns, TurnCooldowns) and cooldowns.extra_deck_attempts > 0:
                    continue
                for name in intent.candidates:
                    if cfg.strict_profile and not profile_index.is_allowed(name):
                        logging.info("[PROFILE] blocked unknown card name=%s", name)
                        continue
                    actions.append(
                        Action(
                            type="extra_deck_summon",
                            args={"name": name},
                            description=f"Extra deck summon {name}",
                        )
                    )
                    break
            elif intent.kind == "SET_BACKROW" and intent.name:
                hand_index = name_to_index.get(intent.name)
                if hand_index is None:
                    continue
                actions.append(
                    Action(
                        type="set_spell_trap",
                        args={"hand_index": hand_index, "card_name": intent.name},
                        description=f"Set {intent.name}",
                    )
                )
        return actions

    def on_dialog(
        self,
        dialog_cards: list[str],
        state: Snapshot,
        ctx: dict,
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

    def _apply_ruleset_handlers(self, ctx: dict) -> None:
        ruleset = ctx.get("ruleset")
        if ruleset is None:
            return
        for name in ctx.get("hand_names", []):
            ruleset.registry.get(name)(ruleset, {"card": name})


def get_strategy(profile: dict, strategy_name: str = "default") -> Strategy:
    name = strategy_name or "default"
    return SwordsoulTenyiStrategy(name=name, deck_name="swordsoul_tenyi", profile=profile)
