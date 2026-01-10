"""Handler stub for Swordsoul Strategist Longyuan."""

from __future__ import annotations

import logging

from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.cards.longyuan")


def score(state: dict, profile: dict, client: object, cfg) -> int:
    LOG.debug("score stub")
    return 0


def plan(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    LOG.debug("plan stub")
    return []
