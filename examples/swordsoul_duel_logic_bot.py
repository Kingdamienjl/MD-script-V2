"""
Swordsoul Duel Logic Bot (ruleset-driven)

Defensive loop:
- Never hard-crashes just because a dialog is "stuck"
- Tries multiple ways to confirm/close dialogs
- Falls back to safe actions (advance phase / pass) when unsure

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
from jduel_bot.jduel_bot_enums import ActivateConfirmMode, Phase

from logic.dialog_resolver import DialogResolver
from logic.hand_reader import read_hand
from logic.plan_executor import PlanExecutor
from logic.profile import ProfileIndex
from logic.strategy_registry import load_strategy

try:
    from logic.action_queue import Action  # preferred canonical Action
except Exception:  # pragma: no cover
    from logic.strategy_registry import Action  # type: ignore


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


def _activation_mode_from_cfg(cfg: BotConfig) -> ActivateConfirmMode:
    # Preferred: cfg.activation_confirm_mode() -> ActivateConfirmMode
    fn = getattr(cfg, "activation_confirm_mode", None)
    if callable(fn):
        try:
            mode = fn()
            if isinstance(mode, ActivateConfirmMode):
                return mode
        except Exception:
            pass

    # Fallback: cfg.confirm_mode string ("on"/"off"/"default")
    raw = getattr(cfg, "confirm_mode", None)
    if isinstance(raw, ActivateConfirmMode):
        return raw
    if isinstance(raw, str):
        key = raw.strip().lower()
        if key == "on":
            return ActivateConfirmMode.On
        if key == "off":
            return ActivateConfirmMode.Off
        return ActivateConfirmMode.Default

    return ActivateConfirmMode.On


def _set_confirm_mode(client: JDuelBotClient, cfg: BotConfig) -> None:
    mode = _activation_mode_from_cfg(cfg)
    _try(f"set_activation_confirmation({mode.name})", client.set_activation_confirmation, mode)


def _call_strategy_plan(strategy, state: dict, hand_snapshot, client: JDuelBotClient, cfg: BotConfig):
    """
    Call plan_main_phase_1 in a signature-tolerant way.
    Supported (common) variants:
      - plan_main_phase_1(state, hand, client, cfg)
      - plan_main_phase_1(state, hand, cfg)
      - plan_main_phase_1(state, hand)
    """
    fn = getattr(strategy, "plan_main_phase_1", None)
    if not callable(fn):
        return []

    try:
        sig = inspect.signature(fn)
        n_params = len(sig.parameters)
    except Exception:
        n_params = 4

    try:
        if n_params >= 4:
            return fn(state, hand_snapshot, client, cfg)
        if n_params == 3:
            return fn(state, hand_snapshot, cfg)
        return fn(state, hand_snapshot)
    except TypeError:
        for args in [
            (state, hand_snapshot, client, cfg),
            (state, hand_snapshot, cfg),
            (state, hand_snapshot),
        ]:
            try:
                return fn(*args)
            except TypeError:
                continue
        raise


def main() -> int:
    _setup_logging()
    cfg = BotConfig.from_env()

    LOG.info('"Swordsoul Duel Logic Bot" has been started...')
    LOG.info("Using address: %s", cfg.zmq_address)

    deck_profile_path = Path(cfg.decks_dir) / cfg.ruleset / "profile.json"
    profile_path_used = deck_profile_path if deck_profile_path.exists() else Path(cfg.legacy_profile_path)

    LOG.info(
        "[CONFIG] ruleset=%s strategy=%s decks_dir=%s confirm_mode=%s profile_path=%s",
        cfg.ruleset,
        cfg.strategy,
        cfg.decks_dir,
        getattr(cfg, "confirm_mode", "On"),
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
    LOG.info("[CONFIG] strategy_loaded=%s", type(strategy).__name__)

    dialog_resolver = DialogResolver(max_repeat=getattr(cfg, "dialog_max_repeat", 3))
    plan_executor = PlanExecutor()
    cooldowns = TurnCooldowns()

    pending_plan: list[Action] = []
    pending_index = 0
    actions_this_turn = 0
    last_turn: Optional[int] = None

    # Initial hand snapshot (debug visibility only)
    try:
        hand_snapshot = read_hand(client, profile_index.profile)
        LOG.info("[HAND] summary=%s", [c.name for c in hand_snapshot])
    except Exception:
        pass

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

        if _try("is_inputting", client.is_inputting):
            _try("handle_unexpected_prompts", client.handle_unexpected_prompts)
            _set_confirm_mode(client, cfg)
            dialog_resolver.resolve(
                client,
                profile_index=profile_index,
                strategy=strategy,
                state=state,
                cfg=cfg,
            )
            time.sleep(cfg.tick_s)
            continue

        turn = _try("get_turn_number", client.get_turn_number)
        if isinstance(turn, int) and turn != last_turn:
            last_turn = turn
            cooldowns.stuck_dialog_cycles = 0
            pending_plan = []
            pending_index = 0
            actions_this_turn = 0
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

        if phase_name not in ("main1", "main_phase_1", "main_phase1", "main_phase"):
            time.sleep(cfg.tick_s)
            continue

        # MAIN PHASE 1
        if pending_plan:
            if actions_this_turn >= getattr(cfg, "max_actions_per_turn", 8):
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
            ok = plan_executor.execute_next(pending_plan, pending_index, client, cfg)
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

        if actions_this_turn >= getattr(cfg, "max_actions_per_turn", 8):
            time.sleep(cfg.tick_s)
            continue

        try:
            actions = _call_strategy_plan(strategy, state, hand_snapshot, client, cfg)
        except Exception:
            LOG.error("strategy.plan_main_phase_1 crashed:\n%s", traceback.format_exc())
            actions = [Action(type="pass", args={}, description="Fallback pass after strategy crash")]

        if not actions:
            actions = [Action(type="pass", args={}, description="No actions planned -> pass")]

        opener = actions[0].description if actions else "unknown"
        LOG.info("[PLAN] built n_actions=%s opener=%s", len(actions), opener)

        pending_plan = list(actions)
        pending_index = 0

        time.sleep(cfg.tick_s)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception:
        LOG.error("Fatal crash:\n%s", traceback.format_exc())
        raise
