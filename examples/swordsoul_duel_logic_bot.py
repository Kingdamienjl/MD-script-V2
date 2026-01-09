"""
Swordsoul Duel Logic Bot (ruleset-driven)

This module is intentionally defensive:
- It never raises just because a dialog is "stuck"
- It tries multiple ways to confirm/close dialogs
- It falls back to safe actions (advance phase / pass) when unsure

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
from jduel_bot.jduel_bot_enums import Phase

from logic.dialog_manager import DialogManager
from logic.hand_reader import read_hand
from logic.plan_executor import PlanExecutor
from logic.profile import ProfileIndex
from logic.strategy_registry import Action, load_strategy

# Optional (repo may already provide these)
try:
    from logic.state_manager import TurnCooldowns, snapshot_state  # type: ignore
except Exception:  # pragma: no cover
    @dataclass
    class TurnCooldowns:  # minimal fallback
        last_turn: int = -1
        stuck_dialog_cycles: int = 0

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


def main() -> int:
    _setup_logging()
    cfg = BotConfig.from_env()

    LOG.info('"Swordsoul Duel Logic Bot" has been started...')
    LOG.info("Using address: %s", cfg.zmq_address)

    deck_profile_path = Path(cfg.decks_dir) / cfg.ruleset / "profile.json"
    if deck_profile_path.exists():
        profile_path_used = deck_profile_path
    else:
        profile_path_used = Path(cfg.legacy_profile_path)

    LOG.info(
        "[CONFIG] ruleset=%s strategy=%s decks_dir=%s confirm_mode=%s profile_path=%s",
        cfg.ruleset,
        cfg.strategy,
        cfg.decks_dir,
        cfg.confirm_mode,
        profile_path_used,
    )

    client = JDuelBotClient(address=cfg.zmq_address, timeout_ms=cfg.timeout_ms)
    LOG.info("[ZMQ] Connected to %s", cfg.zmq_address)

    dump_debug_info_once(client)

    profile_index = ProfileIndex.from_deck(cfg.ruleset, cfg.decks_dir, cfg.legacy_profile_path)
    strategy = load_strategy(
        deck_name=cfg.ruleset,
        strategy_name=cfg.strategy,
        decks_dir=cfg.decks_dir,
        profile_path=cfg.legacy_profile_path,
    )
    LOG.info("[CONFIG] strategy_loaded=%s profile=%s", type(strategy).__name__, profile_path_used)
    dialog_manager = DialogManager(repeat_limit=cfg.dialog_max_repeat)
    plan_executor = PlanExecutor()
    cooldowns = TurnCooldowns()
    pending_plan: list[Action] = []
    pending_index = 0
    actions_this_turn = 0
    last_plan_signature: tuple | None = None
    plan_cooldown_ticks = 0

    hand_snapshot = read_hand(client, profile_index.profile)
    unknown_ids = sorted(
        {
            card.card_id
            for card in hand_snapshot
            if card.card_id is not None and card.name == "unknown"
        }
    )
    hand_summary = [card.name for card in hand_snapshot]
    LOG.info("[HAND] summary=%s", hand_summary)
    if unknown_ids:
        LOG.warning("[HAND] unknown_card_ids=%s", unknown_ids)

    last_turn: Optional[int] = None

    while True:
        if not _try("is_dueling", client.is_dueling):
            time.sleep(0.5)
            continue

        if _try("is_duel_ended", client.is_duel_ended):
            LOG.info("[DUEL] ended -> exiting")
            _try("duel_ended_exit_duel", client.duel_ended_exit_duel)
            return 0

        if plan_cooldown_ticks > 0:
            plan_cooldown_ticks -= 1

        state = snapshot_state(client) or {}
        hand_snapshot = read_hand(client, profile_index.profile)

        if _try("is_inputting", client.is_inputting):
            dialog_manager.resolve_once(client, state, profile_index.profile, cfg)
            time.sleep(cfg.tick_s)
            continue

        turn = _try("get_turn_number", client.get_turn_number)
        if isinstance(turn, int) and turn != last_turn:
            last_turn = turn
            cooldowns.stuck_dialog_cycles = 0
            pending_plan = []
            pending_index = 0
            actions_this_turn = 0
            last_plan_signature = None
            plan_cooldown_ticks = 0
            LOG.info("[TURN] New turn detected: %s", turn)

        if not _try("is_my_turn", client.is_my_turn):
            time.sleep(cfg.tick_s)
            continue

        phase = _try("get_current_phase", client.get_current_phase)
        if phase is None:
            time.sleep(cfg.tick_s)
            continue

        if isinstance(phase, Phase):
            phase_name = phase.name.lower()
        else:
            phase_name = str(phase).lower()

        if phase_name in ("main1", "main_phase_1", "main_phase1", "main_phase"):
            if pending_plan:
                if actions_this_turn >= 6:
                    time.sleep(cfg.tick_s)
                    continue
                action = pending_plan[pending_index]
                LOG.info(
                    "[EXEC] step %s/%s type=%s desc=%s",
                    pending_index + 1,
                    len(pending_plan),
                    action.type,
                    action.description,
                )
                ok = plan_executor.execute_next(pending_plan, pending_index, client)
                if ok:
                    pending_index += 1
                    actions_this_turn += 1
                if _try("is_inputting", client.is_inputting):
                    time.sleep(cfg.tick_s)
                    continue
                if pending_index >= len(pending_plan):
                    pending_plan = []
                    pending_index = 0
                time.sleep(cfg.tick_s)
                continue

            if actions_this_turn >= 6:
                time.sleep(cfg.tick_s)
                continue

            try:
                actions = strategy.plan_main_phase_1(state, hand_snapshot, client, cfg)
            except Exception:
                LOG.error("strategy.plan_main_phase_1 crashed:\n%s", traceback.format_exc())
                actions = [Action(type="pass", args={}, description="Fallback pass after strategy crash")]

            if not actions:
                actions = [Action(type="pass", args={}, description="No actions planned -> pass")]

            signature = tuple((action.type, action.description) for action in actions)
            if signature == last_plan_signature and plan_cooldown_ticks > 0:
                time.sleep(cfg.tick_s)
                continue

            opener = actions[0].description if actions else "unknown"
            LOG.info("[PLAN] built n_actions=%s opener=%s", len(actions), opener)
            pending_plan = actions
            pending_index = 0
            last_plan_signature = signature
            plan_cooldown_ticks = 4
        else:
            time.sleep(cfg.tick_s)
            continue

        time.sleep(cfg.tick_s)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception:
        LOG.error("Fatal crash:\n%s", traceback.format_exc())
        raise
