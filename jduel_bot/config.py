"""Shared configuration for bot runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BotConfig:
    action_delay_ms: int
    dialog_click_delay_ms: int
    dialog_max_cycles: int
    dump_dir: Path
    max_actions_per_tick: int
    profile_path: Path
    strict_profile: bool


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def load_config() -> BotConfig:
    """Load configuration from environment variables."""
    action_delay_ms = _parse_int(os.getenv("BOT_ACTION_DELAY_MS"), 120)
    dialog_click_delay_ms = _parse_int(os.getenv("BOT_DIALOG_CLICK_DELAY_MS"), 120)
    dialog_max_cycles = _parse_int(os.getenv("BOT_DIALOG_MAX_CYCLES"), 12)
    dump_dir = Path(os.getenv("BOT_DUMP_DIR", "artifacts")).expanduser()
    max_actions_per_tick = _parse_int(os.getenv("BOT_MAX_ACTIONS_PER_TICK"), 2)
    profile_path = Path(os.getenv("BOT_PROFILE_PATH", "logic/deck_profile.json")).expanduser()
    strict_profile = _parse_bool(os.getenv("BOT_STRICT_PROFILE"), True)

    dump_dir.mkdir(parents=True, exist_ok=True)
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    return BotConfig(
        action_delay_ms=action_delay_ms,
        dialog_click_delay_ms=dialog_click_delay_ms,
        dialog_max_cycles=dialog_max_cycles,
        dump_dir=dump_dir,
        max_actions_per_tick=max_actions_per_tick,
        profile_path=profile_path,
        strict_profile=strict_profile,
    )
