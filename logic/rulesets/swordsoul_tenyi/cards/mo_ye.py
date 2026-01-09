"""Handler stub for Swordsoul of Mo Ye."""

from __future__ import annotations

import logging

from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.cards.mo_ye")


def score(state: dict, profile: dict, client: object, cfg) -> int:
    LOG.debug("score stub")
    return 0


def plan(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    LOG.debug("plan stub")
    return []
