"""
Bot configuration (environment driven)

Codex/GitHub secrets usually supply only KEY=VALUE pairs. This module reads those keys
and provides sane defaults for local runs.

Important env vars:
- BOT_ZMQ_ADDRESS: ZMQ endpoint JDuelBotClient connects to (default tcp://127.0.0.1:5555)
- BOT_RULESET: deck/ruleset folder name (default swordsoul_tenyi)
- BOT_STRATEGY: strategy variant name passed to deck's get_strategy() (default default)
- BOT_DECKS_DIR: where deck folders live (default logic/decks)
- BOT_PROFILE_PATH: legacy fallback profile path (default logic/profile.json)
- BOT_LOG_LEVEL: INFO/DEBUG (default INFO)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from jduel_bot.jduel_bot_enums import ActivateConfirmMode


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class BotConfig:
    zmq_address: str = "tcp://127.0.0.1:5555"
    ruleset: str = "swordsoul_tenyi"
    strategy: str = "default"
    decks_dir: str = "logic/decks"
    legacy_profile_path: str = "logic/profile.json"

    # runtime tuning
    timeout_ms: int = 1200
    tick_s: float = 0.25
    action_delay_s: float = 0.15

    # activation prompt behavior
    activate_confirm: str = "on"  # on|off|default

    @classmethod
    def from_env(cls) -> "BotConfig":
        return cls(
            zmq_address=os.getenv("BOT_ZMQ_ADDRESS", cls.zmq_address),
            ruleset=os.getenv("BOT_RULESET", cls.ruleset),
            strategy=os.getenv("BOT_STRATEGY", cls.strategy),
            decks_dir=os.getenv("BOT_DECKS_DIR", cls.decks_dir),
            legacy_profile_path=os.getenv("BOT_PROFILE_PATH", cls.legacy_profile_path),
            timeout_ms=_get_int("BOT_TIMEOUT_MS", cls.timeout_ms),
            tick_s=_get_float("BOT_TICK_S", cls.tick_s),
            action_delay_s=_get_float("BOT_ACTION_DELAY_S", cls.action_delay_s),
            activate_confirm=os.getenv("BOT_ACTIVATE_CONFIRM", cls.activate_confirm).lower(),
        )

    def activation_confirm_mode(self) -> ActivateConfirmMode:
        v = (self.activate_confirm or "default").lower().strip()
        if v in ("on", "true", "1", "yes"):
            return ActivateConfirmMode.On
        if v in ("off", "false", "0", "no"):
            return ActivateConfirmMode.Off
        return ActivateConfirmMode.Default
