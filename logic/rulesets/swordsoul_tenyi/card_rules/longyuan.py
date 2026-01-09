"""Longyuan card rule."""

from __future__ import annotations

from logic.rulesets.swordsoul_tenyi.plan import PlanAction, PlanStep


def plan() -> list[PlanStep]:
    return [
        PlanStep(PlanAction.SPECIAL_FROM_HAND, "Swordsoul Strategist Longyuan"),
    ]
