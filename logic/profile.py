"""
Profile loading + helpers.

A "profile" is deck metadata used for heuristics:
- dialog pick priority (which card to pick when a dialog shows a list)
- priority_groups for planners (order to try cards/handlers)
- per-card tags/weights for future strategy work
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from jduel_bot.jduel_bot_enums import CardSelection

LOG = logging.getLogger("profile")

ALLOWED_TAGS = {
    "opener",
    "extender",
    "starter",
    "disruption",
    "brick",
    "search",
    "discard_fodder",
}


def _normalize_card_entry(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    out.setdefault("count", 1)
    out.setdefault("tags", [])
    out.setdefault("main1_priority", 0)
    out.setdefault("set_priority", 0)
    out.setdefault("hold_priority", 0)

    # sanitize
    try:
        out["count"] = int(out.get("count", 1))
    except Exception:
        out["count"] = 1

    tags = out.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(t) for t in tags if isinstance(t, (str, int, float))]
    out["tags"] = [t for t in tags if t in ALLOWED_TAGS]

    for k in ("main1_priority", "set_priority", "hold_priority"):
        try:
            out[k] = float(out.get(k, 0))
        except Exception:
            out[k] = 0.0

    return out


def build_cards_by_id(profile: Dict[str, Any]) -> Dict[int, str]:
    cards = profile.get("cards", {})
    if not isinstance(cards, dict):
        return {}
    mapping: Dict[int, str] = {}
    for name, data in cards.items():
        if not isinstance(data, dict):
            continue
        card_id = data.get("id")
        if isinstance(card_id, int):
            mapping[card_id] = str(name)
        elif isinstance(card_id, str) and card_id.isdigit():
            mapping[int(card_id)] = str(name)
    return mapping


def validate_and_normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(profile.get("deck_name"), str):
        profile["deck_name"] = "unknown"

    # dialog_pick_priority is optional; but keep as list
    if not isinstance(profile.get("dialog_pick_priority"), list):
        profile["dialog_pick_priority"] = []

    cards = profile.get("cards")
    if not isinstance(cards, dict):
        profile["cards"] = {}
        cards = profile["cards"]

    normalized_cards: Dict[str, Any] = {}
    for name, data in cards.items():
        if isinstance(data, dict):
            normalized_cards[str(name)] = _normalize_card_entry(data)
    profile["cards"] = normalized_cards

    # extra deck
    if not isinstance(profile.get("extra_deck"), dict):
        profile["extra_deck"] = {}
    if not isinstance(profile.get("extra_deck_priority"), list):
        profile["extra_deck_priority"] = list(profile["extra_deck"].keys())

    # priority_groups is optional but should be dict
    if not isinstance(profile.get("priority_groups"), dict):
        profile["priority_groups"] = {}

    profile["cards_by_id"] = build_cards_by_id(profile)
    return profile


def load_profile(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object")
    return validate_and_normalize_profile(data)


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
        if isinstance(self.profile.get("dialog_pick_priority"), list):
            return [str(x) for x in self.profile["dialog_pick_priority"]]
        return []

    def pick_dialog_choice(self, dialog_cards: List[str]) -> Optional[CardSelection]:
        if not dialog_cards:
            return None

        cards = [str(c) for c in dialog_cards]
        priority = self._dialog_priority()

        for wanted in priority:
            for i, c in enumerate(cards):
                if c == wanted:
                    return CardSelection(card_name=c, card_index=i)

        return CardSelection(card_name=cards[0], card_index=0)
