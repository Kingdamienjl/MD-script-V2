"""
Swordsoul Duel Logic Bot (ruleset-driven)

Defensive by design:
- never raises just because a dialog is "stuck"
- tries multiple ways to confirm/close dialogs
- falls back to safe actions (advance phase / pass) when unsure

Env vars (see jduel_bot/config.py):
- BOT_ZMQ_ADDRESS (default tcp://127.0.0.1:5555)
- BOT_RULESET (default swordsoul_tenyi)
- BOT_STRATEGY (default default)
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

try:
    from jduel_bot.jduel_bot_enums import ActivateConfirmMode, Phase
except Exception:  # pragma: no cover
    ActivateConfirmMode = None  # type: ignore
    Phase = None  # type: ignore

from logic.dialog_resolver import DialogResolver
from logic.plan_executor import PlanExecutor
from logic.hand_reader import read_hand
from logic.profile import ProfileIndex

# Strategy loader (ruleset -> deck strategy module)
try:
    from logic.strategy_registry import load_strategy  # type: ignore
except Exception:  # pragma: no cover
    from logic.strategy_registry import load_strategy  # type: ignore

# Optional state snapshotter (repo may already provide these)
try:
    from logic.state_manager import TurnCooldowns, snapshot_state  # type: ignore
except Exception:  # pragma: no cover
    @dataclass
    class TurnCooldowns:  # minimal fallback
        last_turn: int = -1
        stuck_dialog_cycles: int = 0
        last_dialog_fingerprint: Optional[str] = None
        dialog_repeat_count: int = 0

    def snapshot_state(_client: JDuelBotClient) -> dict:
        return {}


LOG = logging.getLogger("swordsoul_duel_logic_bot")


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


def _sleep(cfg: BotConfig) -> None:
    time.sleep(float(getattr(cfg, "tick_s", 0.25)))


def _phase_name(phase_obj) -> str:
    if phase_obj is None:
        return ""
    if Phase is not None and isinstance(phase_obj, Phase):
        return phase_obj.name.lower()
    return str(phase_obj).lower()


def _call_plan(strategy, state: dict, hand_snapshot, client: JDuelBotClient, cfg: BotConfig):
    """
    Call plan_main_phase_1 in a way that tolerates minor signature drift.
    """
    fn = getattr(strategy, "plan_main_phase_1", None)
    if not callable(fn):
        return []
    try:
        return fn(state, hand_snapshot, client, cfg)
    except TypeError:
        try:
            return fn(state, hand_snapshot, client)
        except TypeError:
            try:
                return fn(state, client, cfg)
            except TypeError:
                return fn(state, client)


def main() -> int:
    _setup_logging()
    cfg = BotConfig.from_env()

    LOG.info('"Swordsoul Duel Logic Bot" has been started...')
    LOG.info("Using address: %s", cfg.zmq_address)

    deck_profile_path = Path(getattr(cfg, "decks_dir", "logic/decks")) / cfg.ruleset / "profile.json"
    legacy_profile = Path(getattr(cfg, "legacy_profile_path", "logic/profile.json"))
    profile_path_used = deck_profile_path if deck_profile_path.exists() else legacy_profile

    LOG.info(
        "[CONFIG] ruleset=%s strategy=%s decks_dir=%s confirm_mode=%s profile_path=%s",
        cfg.ruleset,
        cfg.strategy,
        getattr(cfg, "decks_dir", "logic/decks"),
        getattr(cfg, "confirm_mode", "Default"),
        profile_path_used,
    )

    client = JDuelBotClient(address=cfg.zmq_address, timeout_ms=getattr(cfg, "timeout_ms", 8000))
    LOG.info("[ZMQ] Connected to %s", cfg.zmq_address)

    dump_debug_info_once(client)

    profile_index = ProfileIndex.from_deck(cfg.ruleset, getattr(cfg, "decks_dir", "logic/decks"), str(legacy_profile))
    strategy = load_strategy(
        deck_name=cfg.ruleset,
        strategy_name=cfg.strategy,
        decks_dir=getattr(cfg, "decks_dir", "logic/decks"),
        profile_path=str(legacy_profile),
    )
    LOG.info("[CONFIG] strategy_loaded=%s", type(strategy).__name__)

    dialog_resolver = DialogResolver(max_repeat=int(getattr(cfg, "dialog_max_repeat", 3)))
    executor = PlanExecutor()
    cooldowns = TurnCooldowns()
    last_turn: Optional[int] = None

    while True:
        if not _try("is_dueling", client.is_dueling):
            time.sleep(0.5)
            continue

        if _try("is_duel_ended", client.is_duel_ended):
            LOG.info("[DUEL] ended -> exiting")
            _try("duel_ended_exit_duel", client.duel_ended_exit_duel)
            return 0

        state = snapshot_state(client) or {}
        hand_snapshot = read_hand(client, profile_index.profile)

        # Resolve dialogs/prompts first.
        if _try("is_inputting", client.is_inputting):
            dialog_resolver.resolve(
                client=client,
                profile_index=profile_index,
                cooldowns=cooldowns,
                cfg=cfg,
                strategy=strategy,
                state=state,
            )
            _sleep(cfg)
            continue

        turn = _try("get_turn_number", client.get_turn_number)
        if isinstance(turn, int) and turn != last_turn:
            last_turn = turn
            cooldowns.stuck_dialog_cycles = 0
            cooldowns.last_dialog_fingerprint = None
            cooldowns.dialog_repeat_count = 0
            LOG.info("[TURN] New turn detected: %s", turn)

        if not _try("is_my_turn", client.is_my_turn):
            _sleep(cfg)
            continue

        phase = _try("get_current_phase", client.get_current_phase)
        pname = _phase_name(phase)

        if pname in ("main1", "main_phase_1", "main_phase1", "main_phase"):
            LOG.info(">>> ENTER handle_my_main_phase_1")
            try:
                actions = _call_plan(strategy, state, hand_snapshot, client, cfg)
            except Exception:
                LOG.error("strategy.plan_main_phase_1 crashed:\n%s", traceback.format_exc())
                actions = []

            if not actions:
                # Safe fallback: go to battle then end.
                actions = [{"type": "pass", "args": {}, "description": "No actions -> pass"}]

            executor.execute(actions, client, cfg)
        else:
            _sleep(cfg)
            continue

        _sleep(cfg)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception:
        LOG.error("Fatal crash:\n%s", traceback.format_exc())
        raise
