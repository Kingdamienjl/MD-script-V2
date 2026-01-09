"""Context builder for strategy/planner consumption."""

from __future__ import annotations

import json
import logging
from typing import Any


def _safe_getattr(obj: object, attr: str, default):
    value = getattr(obj, attr, None)
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return default


def _summarize_board_state(board_state: Any) -> dict:
    summary: dict[str, Any] = {}
    if isinstance(board_state, dict):
        for key, value in board_state.items():
            if isinstance(value, (str, int, float, bool)):
                summary[key] = value
            elif isinstance(value, list) and len(value) <= 8:
                summary[key] = value
        return summary
    return {"repr": repr(board_state)[:200]}


def _extract_names(board_state: Any, keys: list[str]) -> list[str]:
    if not isinstance(board_state, dict):
        return []
    for key in keys:
        if key not in board_state:
            continue
        value = board_state[key]
        if isinstance(value, list):
            names: list[str] = []
            for entry in value:
                if isinstance(entry, dict) and "name" in entry:
                    names.append(entry["name"])
                elif isinstance(entry, str):
                    names.append(entry)
            if names:
                return names
    return []


def build_context(client: object, profile_index, state_manager) -> dict:
    board_state = None
    getter = getattr(client, "get_board_state", None)
    if callable(getter):
        try:
            board_state = getter()
        except Exception:
            board_state = None

    context = {
        "phase": getattr(getattr(client, "state", None), "phase", "unknown"),
        "turn": getattr(getattr(client, "state", None), "turn_count", 0),
        "is_my_turn": _safe_getattr(client, "is_my_turn", True),
        "is_inputting": _safe_getattr(client, "is_inputting", False),
        "hand_size": _safe_getattr(client, "get_hand_size", 0),
        "lp": _safe_getattr(client, "get_life_points", 0),
        "known_dialog_cards": list(_safe_getattr(client, "get_dialog_card_list", [])),
        "last_used_card": getattr(getattr(client, "state", None), "last_used_card_name", None),
        "raw_board_state_type": type(board_state).__name__,
        "board_state_summary": _summarize_board_state(board_state),
        "profile_index": profile_index,
        "state_manager": state_manager,
    }

    context["hand_names"] = _extract_names(
        board_state, ["hand", "hand_cards", "handCards", "hand_list"]
    )
    context["field_names"] = _extract_names(
        board_state, ["field", "monsters", "monster_zones", "field_cards"]
    )

    logging.debug(
        "[CONTEXT] %s",
        json.dumps(
            {
                "raw_board_state_type": context["raw_board_state_type"],
                "board_state_summary": context["board_state_summary"],
            },
            default=str,
        ),
    )

    return context
