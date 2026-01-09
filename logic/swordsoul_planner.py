"""
Swordsoul planner (placeholder).

This module will eventually:
- read your hand + board state
- choose an opening line (Mo Ye, Taia, Longyuan, Ecclesia, Tenyi start, etc.)
- emit an ordered list of Actions

Right now it exists mainly to keep imports stable while we iterate.
"""

from __future__ import annotations

from typing import List

from logic.strategy_registry import Action


def plan_default_turn(profile: dict, state: dict) -> List[Action]:
    return [Action(type="pass", description="planner: not implemented -> pass")]
