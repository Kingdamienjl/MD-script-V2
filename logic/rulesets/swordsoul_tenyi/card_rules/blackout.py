"""Blackout card rule."""

from __future__ import annotations

from logic.rulesets.swordsoul_tenyi.plan import PlanAction, PlanStep


def plan() -> list[PlanStep]:
    return [
        PlanStep(PlanAction.SET_SPELL_TRAP, "Swordsoul Blackout"),
    ]
