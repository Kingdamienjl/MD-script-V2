"""Minimal combo sequencing helpers."""

from __future__ import annotations

from dataclasses import dataclass

from logic.action_queue import Action


@dataclass(frozen=True)
class ComboSequencer:
    profile: object

    def plan_extra_deck_actions(self) -> list[Action]:
        priority = list(getattr(self.profile, "extra_deck_priority", []))
        actions: list[Action] = []
        for name in priority:
            actions.append(
                Action(
                    type="extra_deck_summon",
                    args={"name": name},
                    description=f"Extra deck summon {name}",
                )
            )
        return actions
