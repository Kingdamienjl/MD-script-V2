"""Environment configuration for JDuel bots."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


@dataclass(frozen=True)
class BotConfig:
    zmq_address: str
    timeout_ms: int
    max_retries: int
    dialog_click_delay: float
    action_delay: float
    stuck_dialog_cycle_limit: int
    failsafe_action_limit: int
    failsafe_turn_limit: int
    failsafe_enabled: bool
    dump_dir: Path
    screenshot_dir: Path
    log_file: Path
    random_seed: Optional[int]


def _parse_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def load_config() -> BotConfig:
    """Load runtime configuration from environment variables."""
    zmq_address = os.getenv("BOT_ZMQ_ADDRESS", "tcp://127.0.0.1:5555")
    timeout_ms = _parse_int(os.getenv("BOT_TIMEOUT_MS"), 2000)
    max_retries = _parse_int(os.getenv("BOT_MAX_RETRIES"), 3)
    dialog_click_delay = _parse_float(os.getenv("BOT_DIALOG_CLICK_DELAY"), 0.4)
    action_delay = _parse_float(os.getenv("BOT_ACTION_DELAY"), 0.2)
    stuck_dialog_cycle_limit = _parse_int(
        os.getenv("BOT_STUCK_DIALOG_CYCLE_LIMIT"), 8
    )
    failsafe_action_limit = _parse_int(os.getenv("BOT_FAILSAFE_ACTION_LIMIT"), 120)
    failsafe_turn_limit = _parse_int(os.getenv("BOT_FAILSAFE_TURN_LIMIT"), 50)
    failsafe_enabled = _parse_bool(os.getenv("BOT_FAILSAFE_ENABLED"), True)
    dump_dir = Path(os.getenv("BOT_DUMP_DIR", "./bot_dumps")).expanduser()
    screenshot_dir = Path(
        os.getenv("BOT_SCREENSHOT_DIR", "./bot_screenshots")
    ).expanduser()
    log_file = Path(os.getenv("BOT_LOG_FILE", "./logs/bot.log")).expanduser()
    random_seed = _parse_optional_int(os.getenv("BOT_RANDOM_SEED"))

    dump_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    random.seed(random_seed)

    return BotConfig(
        zmq_address=zmq_address,
        timeout_ms=timeout_ms,
        max_retries=max_retries,
        dialog_click_delay=dialog_click_delay,
        action_delay=action_delay,
        stuck_dialog_cycle_limit=stuck_dialog_cycle_limit,
        failsafe_action_limit=failsafe_action_limit,
        failsafe_turn_limit=failsafe_turn_limit,
        failsafe_enabled=failsafe_enabled,
        dump_dir=dump_dir,
        screenshot_dir=screenshot_dir,
        log_file=log_file,
        random_seed=random_seed,
    )
