"""Priority helpers for Swordsoul Tenyi ruleset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityIndex:
    main_priority: tuple[str, ...]
    extra_priority: tuple[str, ...]


def _sorted_by_priority(entries: list[dict]) -> tuple[str, ...]:
    ordered = sorted(entries, key=lambda item: item.get("priority", 0), reverse=True)
    return tuple(item.get("name") for item in ordered if item.get("name"))


def build_priorities(profile: dict) -> PriorityIndex:
    main_entries = profile.get("main", [])
    extra_entries = profile.get("extra", [])
    return PriorityIndex(
        main_priority=_sorted_by_priority(main_entries),
        extra_priority=_sorted_by_priority(extra_entries),
    )
