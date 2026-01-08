"""Swordsoul Tenyi ruleset package."""

from __future__ import annotations

from logic.strategy_registry import StrategyRegistry

from . import rules
from .ruleset import build_ruleset, SwordsoulTenyiRuleset


def get_ruleset(profile: dict) -> SwordsoulTenyiRuleset:
    registry = StrategyRegistry()
    rules.register_rules(registry, profile)
    return build_ruleset(profile, registry)
