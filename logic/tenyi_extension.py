"""Tenyi extensions for Swordsoul opener plans."""

from __future__ import annotations

from logic.profile import ProfileIndex
from logic.swordsoul_planner import Intent


def extend_plan_with_tenyi(plan: list[Intent], profile: ProfileIndex, ctx: dict) -> list[Intent]:
    hand_names = list(ctx.get("hand_names", []))
    ashuna = "Tenyi Spirit - Ashuna"
    if ashuna not in hand_names or not profile.is_allowed(ashuna):
        return plan

    monster_count = ctx.get("monster_count", 0)
    if monster_count > 0:
        return plan

    ashuna_intent = Intent("ACTIVATE_HAND_EFFECT", ashuna)
    starter = profile.main_priority[0] if profile.main_priority else None
    if starter and starter in hand_names:
        return [ashuna_intent, *plan]

    return plan + [ashuna_intent]
