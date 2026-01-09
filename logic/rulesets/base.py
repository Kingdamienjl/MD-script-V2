"""Base ruleset interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.strategy_registry import StrategyRegistry
from logic.state_manager import Snapshot


class BaseRuleset(Protocol):
    name: str
    profile: dict
    registry: StrategyRegistry

    def plan_main_phase_1(self, ctx: dict, snapshot: Snapshot, cfg: BotConfig) -> list[Action]:
        ...


@dataclass(frozen=True)
class SimpleRuleset:
    name: str
    profile: dict
    registry: StrategyRegistry

    def plan_main_phase_1(self, ctx: dict, snapshot: Snapshot, cfg: BotConfig) -> list[Action]:
        return []
