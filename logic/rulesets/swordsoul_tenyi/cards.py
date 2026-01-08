"""Card name constants and match helpers for Swordsoul Tenyi."""

from __future__ import annotations

MO_YE = "Swordsoul of Mo Ye"
TAIA = "Swordsoul of Taia"
LONGYUAN = "Swordsoul Strategist Longyuan"
ECCLESIA = "Incredible Ecclesia, the Virtuous"
EMERGENCE = "Swordsoul Emergence"
BLACKOUT = "Swordsoul Blackout"
ASHUNA = "Tenyi Spirit - Ashuna"
VISHUDA = "Tenyi Spirit - Vishuda"
ADHARA = "Tenyi Spirit - Adhara"
CHIXIAO = "Swordsoul Grandmaster - Chixiao"


def in_hand(hand_names: list[str], name: str) -> bool:
    return name in hand_names
