"""State snapshot helpers for duel logic bots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional


@dataclass(frozen=True)
class CardInfo:
    index: int
    name: Optional[str]


@dataclass(frozen=True)
class Snapshot:
    hand: tuple[CardInfo, ...]
    can_normal_summon: bool
    free_spell_trap_zones: int
    free_monster_zones: int
    monster_count: int


@dataclass
class TurnCooldowns:
    normal_summon_attempts: int = 0
    longyuan_attempts: int = 0
    mo_ye_effect_attempts: int = 0
    taia_effect_attempts: int = 0
    extra_deck_attempts: int = 0
    empty_ticks: int = 0
    phase_advanced: bool = False
    stuck_dialog_cycles: int = 0
    last_dialog_fingerprint: Optional[str] = None
    dialog_repeat_count: int = 0

    def reset_for_new_turn(self) -> None:
        self.normal_summon_attempts = 0
        self.longyuan_attempts = 0
        self.mo_ye_effect_attempts = 0
        self.taia_effect_attempts = 0
        self.extra_deck_attempts = 0
        self.empty_ticks = 0
        self.phase_advanced = False
        self.stuck_dialog_cycles = 0
        self.last_dialog_fingerprint = None
        self.dialog_repeat_count = 0


def _call_if_available(obj: object, attr: str, default):
    value = getattr(obj, attr, None)
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return default


def _get_hand_size(client: object) -> int:
    return int(_call_if_available(client, "get_hand_size", 0))


def _get_hand_name_lookup(client: object) -> Callable[[int], Optional[str]]:
    name_method = getattr(client, "get_hand_card_name", None)
    if callable(name_method):
        def _lookup(index: int) -> Optional[str]:
            try:
                return name_method(index)
            except Exception:
                return None
        return _lookup
    return lambda _index: None


def _get_free_zones(client: object, attr: str) -> int:
    return int(_call_if_available(client, attr, 0))


def snapshot_state(client: object) -> Snapshot:
    hand_size = _get_hand_size(client)
    lookup_name = _get_hand_name_lookup(client)
    hand_cards = tuple(
        CardInfo(index=i, name=lookup_name(i))
        for i in range(hand_size)
    )
    can_normal_summon = bool(_call_if_available(client, "can_normal_summon", True))
    free_spell_trap_zones = _get_free_zones(client, "get_free_spell_trap_zones")
    free_monster_zones = _get_free_zones(client, "get_free_monster_zones")
    monster_count = int(_call_if_available(client, "get_field_monster_count", 0))

    return Snapshot(
        hand=hand_cards,
        can_normal_summon=can_normal_summon,
        free_spell_trap_zones=free_spell_trap_zones,
        free_monster_zones=free_monster_zones,
        monster_count=monster_count,
    )


def filter_names(cards: Iterable[CardInfo], allowed: set[str], strict: bool) -> list[CardInfo]:
    if not strict:
        return [card for card in cards if card.name]
    return [card for card in cards if card.name in allowed]
