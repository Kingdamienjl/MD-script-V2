"""Profile loading and indexing helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def load_profile(path: str) -> dict:
    return json.loads(Path(path).read_text())


@dataclass(frozen=True)
class ProfileIndex:
    profile: dict

    def __post_init__(self) -> None:
        object.__setattr__(self, "deck_name", self.profile.get("deck_name", ""))
        object.__setattr__(self, "monsters", tuple(self.profile.get("monsters", [])))
        object.__setattr__(self, "spells", tuple(self.profile.get("spells", [])))
        object.__setattr__(self, "traps", tuple(self.profile.get("traps", [])))
        object.__setattr__(self, "starters_priority", tuple(self.profile.get("starters_priority", [])))
        object.__setattr__(self, "extenders_priority", tuple(self.profile.get("extenders_priority", [])))
        object.__setattr__(self, "discard_priority", tuple(self.profile.get("discard_priority", [])))
        object.__setattr__(self, "set_backrow_priority", tuple(self.profile.get("set_backrow_priority", [])))
        object.__setattr__(self, "extra_deck_priority", tuple(self.profile.get("extra_deck_priority", [])))
        allowed = set(
            self.monsters
            + self.spells
            + self.traps
            + self.extra_deck_priority
            + self.starters_priority
            + self.extenders_priority
            + self.discard_priority
            + self.set_backrow_priority
        )
        object.__setattr__(self, "allowed_names", allowed)

    deck_name: str = ""
    monsters: tuple[str, ...] = ()
    spells: tuple[str, ...] = ()
    traps: tuple[str, ...] = ()
    starters_priority: tuple[str, ...] = ()
    extenders_priority: tuple[str, ...] = ()
    discard_priority: tuple[str, ...] = ()
    set_backrow_priority: tuple[str, ...] = ()
    extra_deck_priority: tuple[str, ...] = ()
    allowed_names: set[str] = None  # type: ignore[assignment]

    def is_allowed(self, name: str) -> bool:
        return name in self.allowed_names

    def filter_allowed(self, names: Iterable[str]) -> list[str]:
        return [name for name in names if name in self.allowed_names]
