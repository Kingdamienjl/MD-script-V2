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


def load_profile(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object")
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
