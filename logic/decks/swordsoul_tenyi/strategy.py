"""
Swordsoul Tenyi strategy module.

Required by logic.strategy_registry.load_strategy():
- expose get_strategy(profile, strategy_name)

This is intentionally a "skeleton that plays nice":
- It returns a minimal plan (pass) unless you wire in deeper hand reading.
- Dialog priorities come from profile.json and are handled by the outer bot loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.strategy")


@dataclass
class SwordsoulTenyiStrategy:
    profile: dict
    name: str = "default"
    deck_name: str = "swordsoul_tenyi"

    def plan_main_phase_1(self, state: dict, hand: list, client: object, cfg) -> List[Action]:
        # We keep this safe until we wire reliable "hand -> card names".
        return [Action(type="pass", description="Skeleton strategy (no hand introspection yet) -> pass")]

    def on_dialog(self, dialog_cards, state, client: object, cfg):
        return None


def get_strategy(profile: dict, strategy_name: str):
    name = (strategy_name or "default").lower().strip()
    return SwordsoulTenyiStrategy(profile=profile, name=name)
