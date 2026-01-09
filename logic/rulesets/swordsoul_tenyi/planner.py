"""Planner scaffolding for the Swordsoul Tenyi ruleset."""

from __future__ import annotations

import logging

from logic.rulesets.swordsoul_tenyi.cards import (
    adhara,
    ashuna,
    blackout,
    circle,
    ecclesia,
    emergence,
    longyuan,
    mo_ye,
    taia,
    vessel,
    vishuda,
)
from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.planner")

HANDLERS = [
    ("Swordsoul of Mo Ye", mo_ye),
    ("Swordsoul of Taia", taia),
    ("Swordsoul Strategist Longyuan", longyuan),
    ("Incredible Ecclesia, the Virtuous", ecclesia),
    ("Swordsoul Emergence", emergence),
    ("Swordsoul Blackout", blackout),
    ("Tenyi Spirit - Ashuna", ashuna),
    ("Tenyi Spirit - Vishuda", vishuda),
    ("Tenyi Spirit - Adhara", adhara),
    ("Vessel for the Dragon Cycle", vessel),
    ("Heavenly Dragon Circle", circle),
]


def plan_actions(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    candidates: list[tuple[int, str, object]] = []
    for name, handler in HANDLERS:
        try:
            value = handler.score(state, profile, client, cfg)
        except Exception as exc:
            LOG.warning("[PLANNER] score failed card=%s err=%s", name, exc)
            value = 0
        if value > 0:
            candidates.append((value, name, handler))

    if not candidates:
        LOG.info("[PLANNER] no candidates -> fallback pass")
        return [Action(type="pass", description="Planner fallback -> pass")]

    candidates.sort(key=lambda item: item[0], reverse=True)

    for score_value, name, handler in candidates:
        LOG.info("[PLANNER] candidate card=%s score=%s", name, score_value)
        try:
            actions = handler.plan(state, profile, client, cfg)
        except Exception as exc:
            LOG.warning("[PLANNER] plan failed card=%s err=%s", name, exc)
            continue
        if actions:
            LOG.info("[PLANNER] selected card=%s actions=%s", name, len(actions))
            return actions

    LOG.info("[PLANNER] candidates produced no actions -> fallback pass")
    return [Action(type="pass", description="Planner fallback -> pass")]
