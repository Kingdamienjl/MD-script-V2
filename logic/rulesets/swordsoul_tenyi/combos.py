"""Starter combo scaffolding for Swordsoul Tenyi."""

from __future__ import annotations

import logging

from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.combos")


def plan_moye_line(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    LOG.info("[COMBO] Mo Ye line stub")
    return [
        Action(
            type="pass",
            description="Mo Ye line stub (token -> Chixiao -> search -> extend)",
        )
    ]


def plan_longyuan_line(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    LOG.info("[COMBO] Longyuan line stub")
    return [
        Action(
            type="pass",
            description="Longyuan line stub (discard -> token -> Baron/Chengying path)",
        )
    ]


def plan_ashuna_line(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    LOG.info("[COMBO] Ashuna line stub")
    return [
        Action(
            type="pass",
            description="Ashuna line stub (banish -> special Tenyi -> link/extend)",
        )
    ]
