"""
Profile loading + small helpers.

A "profile" is deck metadata used for heuristics:
- dialog pick priority (which card to pick when a dialog shows a list)
- optional per-card weights / tags for future strategy work
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from jduel_bot.jduel_bot_enums import CardSelection

LOG = logging.getLogger("profile")

REQUIRED_CARD_FIELDS = {"count", "tags", "main1_priority", "set_priority", "hold_priority"}
ALLOWED_TAGS = {
    "opener",
    "extender",
    "starter",
    "disruption",
    "brick",
    "search",
    "discard_fodder",
}


def _validate_cards(cards: Dict[str, Any]) -> None:
    for name, data in cards.items():
        if not isinstance(data, dict):
            raise ValueError(f"Card entry for {name} must be an object.")
        missing = REQUIRED_CARD_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Card entry for {name} missing fields: {sorted(missing)}")
        if not isinstance(data["count"], int) or data["count"] <= 0:
            raise ValueError(f"Card entry for {name} has invalid count.")
        tags = data["tags"]
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"Card entry for {name} tags must be a list of strings.")
        invalid = sorted(set(tags) - ALLOWED_TAGS)
        if invalid:
            raise ValueError(f"Card entry for {name} has invalid tags: {invalid}")
        for key in ("main1_priority", "set_priority", "hold_priority"):
            if not isinstance(data[key], (int, float)):
                raise ValueError(f"Card entry for {name} {key} must be numeric.")


def validate_profile(profile: Dict[str, Any]) -> None:
    if not isinstance(profile.get("deck_name"), str):
        raise ValueError("Profile missing deck_name.")
    if not isinstance(profile.get("dialog_pick_priority"), list):
        raise ValueError("Profile missing dialog_pick_priority list.")
    cards = profile.get("cards")
    if not isinstance(cards, dict) or not cards:
        raise ValueError("Profile must include a non-empty cards mapping.")
    _validate_cards(cards)
    extra_deck = profile.get("extra_deck")
    if not isinstance(extra_deck, dict) or not extra_deck:
        raise ValueError("Profile must include extra_deck mapping.")
    if not isinstance(profile.get("extra_deck_priority"), list):
        raise ValueError("Profile missing extra_deck_priority list.")


def load_profile(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object")
    validate_profile(data)
    return data


def _read_profile_from_deck(deck_name: str, decks_dir: str, fallback_path: str) -> Dict[str, Any]:
    deck_profile = Path(decks_dir) / deck_name / "profile.json"
    if deck_profile.exists():
        return load_profile(str(deck_profile))
    fb = Path(fallback_path)
    if fb.exists():
        LOG.warning("Deck profile missing in %s, falling back to %s", deck_profile, fb)
        return load_profile(str(fb))
    raise FileNotFoundError(f"Missing {deck_profile} and fallback {fb}")


@dataclass(frozen=True)
class ProfileIndex:
    """Convenience accessors + ranking for dialogs."""
    profile: Dict[str, Any]

    @classmethod
    def from_deck(cls, deck_name: str, decks_dir: str, fallback_path: str) -> "ProfileIndex":
        return cls(profile=_read_profile_from_deck(deck_name, decks_dir, fallback_path))

    def _dialog_priority(self) -> List[str]:
        # supported schemas:
        # - {"dialog_pick_priority": [...]}
        # - {"priorities": {"dialog_pick": [...]}}
        if isinstance(self.profile.get("dialog_pick_priority"), list):
            return [str(x) for x in self.profile["dialog_pick_priority"]]
        pr = self.profile.get("priorities") or {}
        if isinstance(pr, dict) and isinstance(pr.get("dialog_pick"), list):
            return [str(x) for x in pr["dialog_pick"]]
        return []

    def pick_dialog_choice(self, dialog_cards: List[str]) -> Optional[CardSelection]:
        """
        Choose a CardSelection for a dialog list.

        - Prefers the first matching name found in the profile priority list.
        - Falls back to index 0 if nothing matches.
        """
        if not dialog_cards:
            return None

        cards = [str(c) for c in dialog_cards]
        priority = self._dialog_priority()

        for wanted in priority:
            for i, c in enumerate(cards):
                if c == wanted:
                    return CardSelection(card_name=c, card_index=i)

        return CardSelection(card_name=cards[0], card_index=0)


@dataclass(frozen=True)
class DeckProfile:
    profile: Dict[str, Any]

    @classmethod
    def from_deck(cls, deck_name: str, decks_dir: str, fallback_path: str) -> "DeckProfile":
        return cls(profile=_read_profile_from_deck(deck_name, decks_dir, fallback_path))

    def _card_data(self, name: str) -> Optional[Dict[str, Any]]:
        cards = self.profile.get("cards", {})
        if isinstance(cards, dict):
            return cards.get(name)
        return None

    def tags_for(self, name: str) -> List[str]:
        data = self._card_data(name) or {}
        tags = data.get("tags", [])
        return [str(tag) for tag in tags] if isinstance(tags, list) else []

    def has_tag(self, name: str, tag: str) -> bool:
        return tag in self.tags_for(name)

    def is_opener(self, name: str) -> bool:
        return self.has_tag(name, "opener")

    def is_extender(self, name: str) -> bool:
        return self.has_tag(name, "extender")

    def is_starter(self, name: str) -> bool:
        return self.has_tag(name, "starter")

    def is_disruption(self, name: str) -> bool:
        return self.has_tag(name, "disruption")

    def is_brick(self, name: str) -> bool:
        return self.has_tag(name, "brick")

    def is_search(self, name: str) -> bool:
        return self.has_tag(name, "search")

    def is_discard_fodder(self, name: str) -> bool:
        return self.has_tag(name, "discard_fodder")

    def count(self, name: str) -> int:
        data = self._card_data(name) or {}
        count = data.get("count", 0)
        return int(count) if isinstance(count, int) else 0

    def main1_priority(self, name: str) -> float:
        return float((self._card_data(name) or {}).get("main1_priority", 0))

    def set_priority(self, name: str) -> float:
        return float((self._card_data(name) or {}).get("set_priority", 0))

    def hold_priority(self, name: str) -> float:
        return float((self._card_data(name) or {}).get("hold_priority", 0))

    def extra_deck_priority(self) -> List[str]:
        priority = self.profile.get("extra_deck_priority", [])
        return [str(name) for name in priority] if isinstance(priority, list) else []

    def extra_deck_counts(self) -> Dict[str, int]:
        extra_deck = self.profile.get("extra_deck", {})
        if not isinstance(extra_deck, dict):
            return {}
        counts: Dict[str, int] = {}
        for name, data in extra_deck.items():
            if isinstance(data, dict) and isinstance(data.get("count"), int):
                counts[str(name)] = data["count"]
        return counts
