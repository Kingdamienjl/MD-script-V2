"""Decision engine for main phase planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from logic.action_queue import Action
from logic.combo_sequencer import ComboSequencer
from logic.state_manager import Snapshot, filter_names


@dataclass(frozen=True)
class DeckProfile:
    starters: tuple[str, ...]
    extenders: tuple[str, ...]
    spells: tuple[str, ...]
    traps: tuple[str, ...]
    extra_deck_priority: tuple[str, ...]


def load_profile(path: Path) -> DeckProfile:
    data = json.loads(path.read_text())
    return DeckProfile(
        starters=tuple(data.get("starters", [])),
        extenders=tuple(data.get("extenders", [])),
        spells=tuple(data.get("spells", [])),
        traps=tuple(data.get("traps", [])),
        extra_deck_priority=tuple(data.get("extra_deck_priority", [])),
    )


def _select_card_index(
    cards, preferred_names: Iterable[str], strict: bool
) -> Optional[tuple[int, str]]:
    preferred = list(preferred_names)
    if not cards:
        return None
    if preferred:
        for name in preferred:
            for card in cards:
                if card.name == name:
                    return card.index, name
    if strict:
        return None
    for card in cards:
        if card.name:
            return card.index, card.name
    return None


class DecisionEngine:
    def __init__(self, profile: DeckProfile, strict_profile: bool) -> None:
        self.profile = profile
        self.strict_profile = strict_profile
        self.combo_sequencer = ComboSequencer(profile)

    def plan_main_phase_1(self, snapshot: Snapshot, client: object) -> list[Action]:
        actions: list[Action] = []
        starters_set = set(self.profile.starters)
        spell_trap_set = set(self.profile.spells + self.profile.traps)

        if snapshot.can_normal_summon and snapshot.free_monster_zones > 0:
            starter_cards = filter_names(snapshot.hand, starters_set, self.strict_profile)
            preferred_order = [
                "Swordsoul of Mo Ye",
                "Swordsoul of Taia",
            ] + list(self.profile.starters)
            selected = _select_card_index(starter_cards, preferred_order, self.strict_profile)
            if selected:
                hand_index, card_name = selected
                actions.append(
                    Action(
                        type="normal_summon",
                        args={"hand_index": hand_index, "card_name": card_name},
                        description=f"Normal summon {card_name}",
                    )
                )
                actions.append(
                    Action(
                        type="activate_effect",
                        args={"field_index": 0, "card_name": card_name},
                        description=f"Activate effect of {card_name}",
                    )
                )
                if hasattr(client, "perform_extra_deck_summon"):
                    actions.extend(self.combo_sequencer.plan_extra_deck_actions())
                return actions

        if snapshot.free_spell_trap_zones > 0:
            spell_trap_cards = filter_names(
                snapshot.hand, spell_trap_set, self.strict_profile
            )
            selected = _select_card_index(spell_trap_cards, [], self.strict_profile)
            if selected:
                hand_index, card_name = selected
                actions.append(
                    Action(
                        type="set_spell_trap",
                        args={"hand_index": hand_index, "card_name": card_name},
                        description=f"Set {card_name}",
                    )
                )
                return actions

        actions.append(
            Action(
                type="advance_phase",
                args={"phase": "battle"},
                description="Advance to battle phase",
            )
        )
        return actions
