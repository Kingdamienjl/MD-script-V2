"""Ruleset loader controlled by BOT_RULESET."""

from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path

from logic.profile import load_profile
from logic.rulesets.base import BaseRuleset


def load_ruleset(name: str | None = None) -> BaseRuleset:
    ruleset_name = name or os.getenv("BOT_RULESET", "swordsoul_tenyi")
    profile_path = Path("logic") / "decks" / ruleset_name / "profile.json"
    profile = load_profile(str(profile_path))

    logging.info(
        "[RULESET] name=%s profile=%s",
        ruleset_name,
        profile_path,
    )

    module = importlib.import_module(f"logic.rulesets.{ruleset_name}")
    get_ruleset = getattr(module, "get_ruleset", None)
    if not callable(get_ruleset):
        raise ImportError(f"Ruleset module {ruleset_name} missing get_ruleset()")

    ruleset = get_ruleset(profile)
    logging.info("[RULESET] loaded=%s", ruleset_name)
    return ruleset
