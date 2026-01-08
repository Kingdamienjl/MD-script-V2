"""Swordsoul Tenyi ruleset package."""

from __future__ import annotations

from logic.rulesets.base import SimpleRuleset
from logic.strategy_registry import StrategyRegistry

from . import rules


def get_ruleset(profile: dict) -> SimpleRuleset:
    registry = StrategyRegistry()
    rules.register_rules(registry, profile)
    return SimpleRuleset(name="swordsoul_tenyi", profile=profile, registry=registry)
