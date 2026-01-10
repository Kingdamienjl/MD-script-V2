"""Swordsoul Tenyi ruleset package."""

from __future__ import annotations

from logic.strategy_registry import StrategyRegistry

from . import rules
from .ruleset import build_ruleset as _build_ruleset, SwordsoulTenyiRuleset


def build_ruleset(profile: dict) -> SwordsoulTenyiRuleset:
    registry = StrategyRegistry()
    rules.register_rules(registry, profile)
    return _build_ruleset(profile, registry)


def get_ruleset(profile: dict) -> SwordsoulTenyiRuleset:
    return build_ruleset(profile)
