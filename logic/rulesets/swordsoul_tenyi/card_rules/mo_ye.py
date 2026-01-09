"""Mo Ye card rule."""

from __future__ import annotations

from logic.rulesets.swordsoul_tenyi.plan import PlanAction, PlanStep


def plan() -> list[PlanStep]:
    return [
        PlanStep(PlanAction.NORMAL_SUMMON, "Swordsoul of Mo Ye"),
        PlanStep(PlanAction.ACTIVATE_FROM_FIELD, "Swordsoul of Mo Ye"),
        PlanStep(PlanAction.EXTRA_DECK_SUMMON, "Swordsoul Grandmaster - Chixiao"),
    ]
