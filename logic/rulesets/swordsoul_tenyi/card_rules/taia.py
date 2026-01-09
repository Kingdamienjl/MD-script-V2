"""Taia card rule."""

from __future__ import annotations

from logic.rulesets.swordsoul_tenyi.plan import PlanAction, PlanStep


def plan() -> list[PlanStep]:
    return [
        PlanStep(PlanAction.NORMAL_SUMMON, "Swordsoul of Taia"),
        PlanStep(PlanAction.ACTIVATE_FROM_FIELD, "Swordsoul of Taia"),
    ]
