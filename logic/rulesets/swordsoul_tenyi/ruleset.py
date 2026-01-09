"""Swordsoul Tenyi ruleset skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.rulesets.base import BaseRuleset
from logic.rulesets.swordsoul_tenyi import cards
from logic.rulesets.swordsoul_tenyi.card_rules import (
    adhara,
    ashuna,
    blackout,
    ecclesia,
    emergence,
    longyuan,
    mo_ye,
    taia,
    vishuda,
)
from logic.rulesets.swordsoul_tenyi.plan import PlanAction, PlanStep
from logic.rulesets.swordsoul_tenyi.priorities import PriorityIndex, build_priorities
from logic.state_manager import Snapshot
from logic.strategy_registry import StrategyRegistry


@dataclass(frozen=True)
class SwordsoulTenyiRuleset(BaseRuleset):
    name: str
    profile: dict
    registry: StrategyRegistry
    priorities: PriorityIndex

    def decide(self, state: Snapshot, client: object | None = None) -> list[PlanStep]:
        hand_names = _extract_hand_names(state)
        if cards.in_hand(hand_names, cards.MO_YE):
            return mo_ye.plan()
        if cards.in_hand(hand_names, cards.ECCLESIA):
            return ecclesia.plan()
        if cards.in_hand(hand_names, cards.ASHUNA):
            return ashuna.plan()
        return []

    def plan_main_phase_1(self, ctx: dict, snapshot: Snapshot, cfg: BotConfig) -> list[Action]:
        steps = self.decide(snapshot, ctx.get("client"))
        return _steps_to_actions(steps, snapshot)


def _extract_hand_names(snapshot: Snapshot) -> list[str]:
    return [card.name for card in snapshot.hand if card.name]


def _steps_to_actions(steps: Iterable[PlanStep], snapshot: Snapshot) -> list[Action]:
    actions: list[Action] = []
    name_to_index = {card.name: card.index for card in snapshot.hand if card.name}
    for step in steps:
        if step.action == PlanAction.NORMAL_SUMMON and step.card_name:
            hand_index = name_to_index.get(step.card_name)
            if hand_index is None:
                continue
            actions.append(
                Action(
                    type="normal_summon",
                    args={"hand_index": hand_index, "card_name": step.card_name},
                    description=f"Normal summon {step.card_name}",
                )
            )
        elif step.action == PlanAction.ACTIVATE_FROM_HAND and step.card_name:
            hand_index = name_to_index.get(step.card_name)
            if hand_index is None:
                continue
            actions.append(
                Action(
                    type="activate_hand_effect",
                    args={"hand_index": hand_index, "card_name": step.card_name},
                    description=f"Activate {step.card_name}",
                )
            )
        elif step.action == PlanAction.ACTIVATE_FROM_FIELD and step.card_name:
            actions.append(
                Action(
                    type="activate_effect",
                    args={"field_index": 0, "card_name": step.card_name},
                    description=f"Activate effect of {step.card_name}",
                )
            )
        elif step.action == PlanAction.SPECIAL_FROM_HAND and step.card_name:
            hand_index = name_to_index.get(step.card_name)
            if hand_index is None:
                continue
            actions.append(
                Action(
                    type="special_summon",
                    args={"hand_index": hand_index, "card_name": step.card_name},
                    description=f"Special summon {step.card_name}",
                )
            )
        elif step.action == PlanAction.SET_SPELL_TRAP and step.card_name:
            hand_index = name_to_index.get(step.card_name)
            if hand_index is None:
                continue
            actions.append(
                Action(
                    type="set_spell_trap",
                    args={"hand_index": hand_index, "card_name": step.card_name},
                    description=f"Set {step.card_name}",
                )
            )
        elif step.action == PlanAction.EXTRA_DECK_SUMMON and step.card_name:
            actions.append(
                Action(
                    type="extra_deck_summon",
                    args={"name": step.card_name},
                    description=f"Extra deck summon {step.card_name}",
                )
            )
    return actions


def build_ruleset(profile: dict, registry: StrategyRegistry) -> SwordsoulTenyiRuleset:
    priorities = build_priorities(profile)
    return SwordsoulTenyiRuleset(
        name=profile.get("deck_name", "swordsoul_tenyi"),
        profile=profile,
        registry=registry,
        priorities=priorities,
    )
