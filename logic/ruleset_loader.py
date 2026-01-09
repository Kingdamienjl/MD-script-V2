"""Ruleset loader for deck-specific strategy handlers."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from logic.profile import load_profile
from logic.strategy_registry import StrategyRegistry


@dataclass(frozen=True)
class RulesetContext:
    name: str
    profile: dict
    registry: StrategyRegistry


def _import_rules_module(ruleset: str) -> object:
    module_path = Path("logic") / "rulesets" / ruleset / "rules.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Missing rules module at {module_path}")
    spec = importlib.util.spec_from_file_location(
        f"logic.rulesets.{ruleset}.rules", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import rules module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_ruleset(ruleset: str | None = None) -> RulesetContext:
    ruleset_name = ruleset or os.getenv("BOT_RULESET", "swordsoul_tenyi")
    profile_path = Path("logic") / "decks" / ruleset_name / "profile.json"
    profile = load_profile(str(profile_path))
    registry = StrategyRegistry()
    module = _import_rules_module(ruleset_name)
    register_rules = getattr(module, "register_rules", None)
    if callable(register_rules):
        register_rules(registry, profile)
    return RulesetContext(name=ruleset_name, profile=profile, registry=registry)
