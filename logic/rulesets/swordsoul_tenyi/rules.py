"""Ruleset handlers for Swordsoul Tenyi."""

from __future__ import annotations


def _no_action(_context: object, _state: dict) -> list:
    return []


def register_rules(registry, profile: dict) -> None:
    monsters = profile.get("monsters", [])
    spells = profile.get("spells", [])
    traps = profile.get("traps", [])

    for name in monsters + spells + traps:
        registry.register(name)(_no_action)

    registry.register("Swordsoul of Mo Ye")(handle_mo_ye)
    registry.register("Swordsoul of Taia")(handle_taia)
    registry.register("Swordsoul Strategist Longyuan")(handle_longyuan)
    registry.register("Swordsoul Emergence")(handle_emergence)
    registry.register("Swordsoul Blackout")(handle_blackout)
    registry.register("Tenyi Spirit - Ashuna")(handle_ashuna)


def handle_mo_ye(_context: object, _state: dict) -> list:
    return []


def handle_taia(_context: object, _state: dict) -> list:
    return []


def handle_longyuan(_context: object, _state: dict) -> list:
    return []


def handle_emergence(_context: object, _state: dict) -> list:
    return []


def handle_blackout(_context: object, _state: dict) -> list:
    return []


def handle_ashuna(_context: object, _state: dict) -> list:
    return []
