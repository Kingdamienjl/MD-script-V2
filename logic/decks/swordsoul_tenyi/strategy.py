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
        self, state: Snapshot, client: object, cfg: BotConfig
    ) -> list[Action]:
        profile_index = ProfileIndex(self.profile)
        planner = SwordsoulPlanner(profile_index)
        hand_names = self._collect_hand_names(state, client)
        intents = planner.plan(
            hand_names,
            dialog_cards=list(getattr(client, "get_dialog_card_list", lambda: [])()),
            board_state=self._safe_board_state(client),
        )
        intents = extend_plan_with_tenyi(intents, profile_index, state)

        cooldowns = getattr(client, "turn_cooldowns", None)

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
                if intent.name == "Swordsoul of Mo Ye" and isinstance(cooldowns, TurnCooldowns):
                    if cooldowns.mo_ye_effect_attempts > 0:
                        continue
                if intent.name == "Swordsoul of Taia" and isinstance(cooldowns, TurnCooldowns):
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
                if intent.name == "Swordsoul Strategist Longyuan" and isinstance(
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

    def _collect_hand_names(self, state: Snapshot, client: object) -> list[str]:
        names = [card.name for card in state.hand if card.name]
        if names:
            return names
        board_state = self._safe_board_state(client)
        if not board_state:
            return []
        hand = board_state.get("hand") if isinstance(board_state, dict) else None
        if isinstance(hand, list):
            extracted = []
            for entry in hand:
                if isinstance(entry, dict) and "name" in entry:
                    extracted.append(entry["name"])
                elif isinstance(entry, str):
                    extracted.append(entry)
            return extracted
        return []

    def _safe_board_state(self, client: object) -> dict | None:
        getter = getattr(client, "get_board_state", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None


def get_strategy(profile: dict, strategy_name: str = "default") -> Strategy:
    name = strategy_name or "default"
    return SwordsoulTenyiStrategy(name=name, deck_name="swordsoul_tenyi", profile=profile)
