"""Legacy strategy wrapper for the Swordsoul Tenyi ruleset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.context_builder import build_context
from logic.profile import ProfileIndex
from logic.state_manager import Snapshot, TurnCooldowns
from logic.strategy_base import CardSelection, Strategy
from logic.rulesets.base import BaseRuleset
from logic.rulesets.swordsoul_tenyi import get_ruleset


@dataclass(frozen=True)
class SwordsoulTenyiStrategy(Strategy):
    name: str
    deck_name: str
    profile: dict
    ruleset: BaseRuleset

    def plan_main_phase_1(
        self, state: Snapshot, client: object, cfg: BotConfig
    ) -> list[Action]:
        profile_index = ProfileIndex(self.profile)
        ctx = build_context(client, profile_index, state)
        ctx["ruleset"] = self.ruleset
        ctx["turn_cooldowns"] = TurnCooldowns()
        return self.ruleset.plan_main_phase_1(ctx, state, cfg)

    def on_dialog(
        self,
        dialog_cards: list[str],
        state: Snapshot,
        client: object,
        cfg: BotConfig,
    ) -> Optional[list[CardSelection]]:
        return None


def get_strategy(profile: dict, strategy_name: str = "default") -> Strategy:
    name = strategy_name or "default"
    return SwordsoulTenyiStrategy(
        name=name,
        deck_name="swordsoul_tenyi",
        profile=profile,
        ruleset=get_ruleset(profile),
    )
