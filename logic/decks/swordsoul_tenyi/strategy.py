"""
Swordsoul Tenyi strategy module.

Required by logic.strategy_registry.load_strategy():
- expose get_strategy(profile, strategy_name)

This module forwards to the ruleset implementation in logic/rulesets/swordsoul_tenyi.
"""

from __future__ import annotations

from logic.rulesets.swordsoul_tenyi.strategy import get_strategy as get_ruleset_strategy


def get_strategy(profile: dict, strategy_name: str):
    return get_ruleset_strategy(profile, strategy_name)
