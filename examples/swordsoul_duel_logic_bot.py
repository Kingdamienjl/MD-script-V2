"""
Swordsoul Duel Logic Bot (ruleset-driven)

Defensive behaviors:
- Never crashes just because a dialog is "stuck"
- Detects repeating dialogs and bails out safely
- Executes strategy plans via PlanExecutor
- Falls back to safe pass/advance-phase behaviors when unsure

Env vars (typically in jduel_bot/config.py):
- BOT_ZMQ_ADDRESS (default tcp://127.0.0.1:5555)
- BOT_RULESET (default swordsoul_tenyi)
- BOT_STRATEGY (default default)
- BOT_CONFIRM_MODE (Default|Off|On)
- BOT_DIALOG_MAX_REPEAT (default 3)
- BOT_LOG_LEVEL (default INFO)
"""

from __future__ import annotations

import inspect
import logging
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jduel_bot.config import BotConfig
from jduel_bot.jduel_bot_client import JDuelBotClient
from jduel_bot.jduel_bot_enums import ActivateConfirmMode, Phase

from logic.action_queue import Action
from logic.dialog_resolver import DialogResolver
from logic.hand_reader import read_hand
from logic.plan_executor import PlanExecutor
from logic.profile import ProfileIndex
from logic.strategy_registry import load_strategy


LOG = logging.getLogger("swordsoul_duel_logic_bot")


# Optional: repo may provide richer versions; keep a fallback so the bot never import-crashes.
try:
    from logic.state_manager import TurnCooldowns, snapshot_state  # type: ignore
except Exception:  # pragma: no cover
    @dataclass
    class TurnCooldowns:
        last_turn: int = -1
        stuck_dialog_cycles: int = 0

    def snapshot_state(_client: JDuelBotClient) -> dict:
        return {}


def _setup_logging() -> None:
    level = os.getenv("BOT_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)5s | %(name)s:%(lineno)d - %(message)s",
    )


def dump_debug_info_once(client: JDuelBotClient) -> None:
    """Print callable methods and a few signatures to help future debugging."""
    try:
        methods = sorted(
            [
                name
                for name in dir(client)
                if callable(getattr(client, name)) and not name.startswith("_")
            ]
        )
        LOG.info("=== JDuelBotClient callable methods ===")
        LOG.info("%s", ", ".join(methods))
        LOG.info("=== end ===")

        LOG.info("=== Action method signatures (selected) ===")
        for name in [
            "get_board_state",
            "get_dialog_card_list",
            "select_card_from_dialog",
            "select_cards_from_dialog",
            "set_activation_confirmation",
            "handle_unexpected_prompts",
            "cancel_activation_prompts",
            "wait_for_input_enabled",
            "normal_summon_monster",
            "activate_monster_effect_from_field",
            "activate_spell_or_trap_from_hand",
            "set_spell_or_trap_from_hand",
            "perform_extra_deck_summon",
        ]:
            fn = getattr(client, name, None)
            if fn is None:
                continue
            try:
                sig = str(inspect.signature(fn))
            except Exception:
                sig = "(signature unavailable)"
            LOG.info("%s%s", name, sig)
        LOG.info("=== end signatures ===")
    except Exception as exc:
        LOG.warning("debug dump failed: %s", exc)


def _try(label: str, fn, *args, **kwargs):
    try:
        out = fn(*args, **kwargs)
        LOG.debug("[ACTION OK] %s args=%s kwargs=%s", label, args, kwargs)
        return out
    except Exception as exc:
        LOG.warning("[ACTION FAIL] %s err=%s", label, exc)
        return None


def _coerce_confirm_mode(value) -> Optional[ActivateConfirmMode]:
    if value is None:
        return None
    if isinstance(value, ActivateConfirmMode):
        return value
    if isinstance(value, int):
        try:
            return ActivateConfirmMode(value)
        except Exception:
            return None
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("default", "0"):
            return ActivateConfirmMode.Default
        if v in ("off", "1"):
            return ActivateConfirmMode.Off
        if v in ("on", "2"):
            return ActivateConfirmMode.On
    return None


def _set_confirm_mode(client: JDuelBotClient, cfg: BotConfig) -> None:
    # try cfg.confirm_mode, otherwise BOT_CONFIRM_MODE
    raw = getattr(cfg, "confirm_mode", None)
    if raw is None:
        raw = os.getenv("BOT_CONFIRM_MODE", None)
    mode = _coerce_confirm_mode(raw)
    if mode is None:
        return
    _try(f"set_activation_confirmation({mode.name})", client.set_activation_confirmation, mode)


def _call_plan_main_phase_1(strategy, state: dict, hand, client: JDuelBotClient, cfg: BotConfig) -> list[Action]:
    """
    Tolerate small signature drift across strategy implementations.
    Try common calling conventions and fall back safely.
    """
    candidates = [
        (state, hand, client, cfg),
        (state, hand, client),
        (state, hand, cfg),
        (state, hand),
    ]
    fn = getattr(strategy, "plan_main_phase_1", None)
    if not callable(fn):
        return [Action(type="pass", args={}, description="Strategy missing plan_main_phase_1 -> pass")]

    last_exc: Optional[Exception] = None
    for args in candidates:
        try:
            out = fn(*args)
            return out or []
        except TypeError as exc:
            last_exc = exc
            continue
    if last_exc:
        LOG.error("plan_main_phase_1 signature mismatch: %s", last_exc)
    return [Action(type="pass", args={}, description="Strategy signature mismatch -> pass")]


def main() -> int:
    _setup_logging()
    cfg = BotConfig.from_env()

    # Pull commonly-used config safely (fallback if config.py differs)
    zmq_address = getattr(cfg, "zmq_address", os.getenv("BOT_ZMQ_ADDRESS", "tcp://127.0.0.1:5555"))
    ruleset = getattr(cfg, "ruleset", os.getenv("BOT_RULESET", "swordsoul_tenyi"))
    strategy_name = getattr(cfg, "strategy", os.getenv("BOT_STRATEGY", "default"))
    decks_dir = getattr(cfg, "decks_dir", os.getenv("BOT_DECKS_DIR", "logic/decks"))
    legacy_profile_path = getattr(cfg, "legacy_profile_path", os.getenv("BOT_LEGACY_PROFILE_PATH", "logic/profile.json"))
    dialog_max_repeat = int(getattr(cfg, "dialog_max_repeat", os.getenv("BOT_DIALOG_MAX_REPEAT", "3")))
    tick_s = float(getattr(cfg, "tick_s", 0.25))
    timeout_ms = int(getattr(cfg, "timeout_ms", 1500))

    LOG.info('"Swordsoul Duel Logic Bot" has been started...')
    LOG.info("Using address: %s", zmq_address)

    deck_profile_path = Path(decks_dir) / ruleset / "profile.json"
    profile_path_used = deck_profile_path if deck_profile_path.exists() else Path(legacy_profile_path)

    LOG.info(
        "[CONFIG] ruleset=%s strategy=%s decks_dir=%s confirm_mode=%s profile_path=%s",
        ruleset,
        strategy_name,
        decks_dir,
        getattr(cfg, "confirm_mode", os.getenv("BOT_CONFIRM_MODE", "Default")),
        profile_path_used,
    )

    client = JDuelBotClient(address=zmq_address, timeout_ms=timeout_ms)
    LOG.info("[ZMQ] Connected to %s", zmq_address)

    dump_debug_info_once(client)

    profile_index = ProfileIndex.from_deck(ruleset, decks_dir, legacy_profile_path)
    strategy = load_strategy(
        deck_name=ruleset,
        strategy_name=strategy_name,
        decks_dir=decks_dir,
        profile_path=legacy_profile_path,
    )

    dialog_resolver = DialogResolver(max_repeat=dialog_max_repeat)
    plan_executor = PlanExecutor()
    cooldowns = TurnCooldowns()

    last_turn: Optional[int] = None

    # Initial hand snapshot (useful debug; won't crash if unknown)
    try:
        hand_snapshot = read_hand(client, profile_index.profile)
        LOG.info("[HAND] summary=%s", [c.name for c in hand_snapshot])
    except Exception:
        LOG.warning("[HAND] unable to read initial hand:\n%s", traceback.format_exc())

    while True:
        if not _try("is_dueling", client.is_dueling):
            time.sleep(0.5)
            continue

        if _try("is_duel_ended", client.is_duel_ended):
            LOG.info("[DUEL] ended -> exiting")
            _try("duel_ended_exit_duel", client.duel_ended_exit_duel)
            return 0

        _set_confirm_mode(client, cfg)

        state = snapshot_state(client) or {}
        try:
            hand_snapshot = read_hand(client, profile_index.profile)
        except Exception:
            hand_snapshot = []

        # Dialog/prompt handling
        if _try("is_inputting", client.is_inputting):
            _try("handle_unexpected_prompts", client.handle_unexpected_prompts)
            dialog_resolver.resolve(
                client,
                profile_index=profile_index,
                strategy=strategy,
                state=state,
                cfg=cfg,
            )
            time.sleep(tick_s)
            continue

        turn = _try("get_turn_number", client.get_turn_number)
        if isinstance(turn, int) and turn != last_turn:
            last_turn = turn
            cooldowns.stuck_dialog_cycles = 0
            LOG.info("[TURN] New turn detected: %s", turn)

        if not _try("is_my_turn", client.is_my_turn):
            time.sleep(tick_s)
            continue

        phase = _try("get_current_phase", client.get_current_phase)
        if phase is None:
            time.sleep(tick_s)
            continue

        if isinstance(phase, Phase):
            phase_name = phase.name.lower()
        else:
            phase_name = str(phase).lower()

        if phase_name in ("main1", "main_phase_1", "main_phase1", "main_phase"):
            LOG.info(">>> ENTER main phase 1")
            try:
                actions = _call_plan_main_phase_1(strategy, state, hand_snapshot, client, cfg)
            except Exception:
                LOG.error("strategy planning crashed:\n%s", traceback.format_exc())
                actions = [Action(type="pass", args={}, description="Fallback pass after planning crash")]

            if not actions:
                actions = [Action(type="pass", args={}, description="No actions planned -> pass")]

            plan_executor.execute(actions, client, cfg)
        else:
            time.sleep(tick_s)
            continue

        time.sleep(tick_s)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception:
        LOG.error("Fatal crash:\n%s", traceback.format_exc())
        raise
