"""Command mask inspection helpers."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Iterable, List

LOG = logging.getLogger("command_inspector")


class CommandType(str, Enum):
    NORMAL_SUMMON = "normal_summon"
    ACTIVATE_HAND = "activate_hand"
    ACTIVATE_FIELD = "activate_field"
    SET_SPELL = "set_spell"
    SPECIAL_SUMMON = "special_summon"
    EXTRA_SUMMON = "extra_summon"


def _safe_get_mask(client: object, *args) -> Iterable | None:
    get_mask = getattr(client, "get_command_mask", None)
    if not callable(get_mask):
        LOG.warning("[CMD] mask_unavailable fallback=no_mask err=missing_get_command_mask")
        return None
    try:
        return get_mask(*args)
    except Exception as exc:
        LOG.warning("[CMD] mask_unavailable fallback=no_mask err=%s", exc)
        return None


def _normalize_mask(mask) -> List[CommandType]:
    if mask is None:
        return []
    if isinstance(mask, list):
        normalized: List[CommandType] = []
        for item in mask:
            if isinstance(item, CommandType):
                normalized.append(item)
            elif isinstance(item, str):
                try:
                    normalized.append(CommandType(item))
                except ValueError:
                    continue
        return normalized
    LOG.warning("[CMD] mask_unavailable fallback=empty err=unsupported_mask")
    return []


def hand_commands(client: object, hand_index: int) -> List[CommandType]:
    mask = _safe_get_mask(client, "hand", hand_index)
    return _normalize_mask(mask)


def field_commands(client: object, card_position: int) -> List[CommandType]:
    mask = _safe_get_mask(client, "field", card_position)
    return _normalize_mask(mask)


def can_normal_summon_hand(client: object, hand_index: int) -> bool:
    return CommandType.NORMAL_SUMMON in hand_commands(client, hand_index)


def can_activate_hand(client: object, hand_index: int) -> bool:
    return CommandType.ACTIVATE_HAND in hand_commands(client, hand_index)


def can_activate_field(client: object, card_position: int) -> bool:
    return CommandType.ACTIVATE_FIELD in field_commands(client, card_position)


def can_set_spell(client: object, hand_index: int) -> bool:
    return CommandType.SET_SPELL in hand_commands(client, hand_index)


def can_special_summon_hand(client: object, hand_index: int) -> bool:
    return CommandType.SPECIAL_SUMMON in hand_commands(client, hand_index)


def can_extra_summon(client: object, card_position: int) -> bool:
    return CommandType.EXTRA_SUMMON in field_commands(client, card_position)


def execute_command(client: object, command: CommandType, *args, **kwargs) -> bool:
    execute = getattr(client, "execute_command", None)
    if not callable(execute):
        LOG.warning("[CMD] execute_unavailable command=%s", command)
        return False
    try:
        execute(command, *args, **kwargs)
        return True
    except Exception as exc:
        LOG.warning("[CMD] execute_failed command=%s err=%s", command, exc)
        return False
