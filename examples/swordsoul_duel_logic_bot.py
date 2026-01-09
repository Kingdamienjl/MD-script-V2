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
codex/create-script-to-generate-deck-profile-rknkyi
from jduel_bot.jduel_bot_enums import Phase

from jduel_bot.jduel_bot_enums import (
    ActivateConfirmMode,
    CardSelection,
    DialogButtonType,
    Phase,
)
main

from logic.dialog_resolver import DialogResolver
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

 codex/create-script-to-generate-deck-profile-rknkyi

def _set_confirm_mode(client: JDuelBotClient, cfg: BotConfig) -> None:
    mode = cfg.activation_confirm_mode()
    _try(f"set_activation_confirmation({mode.name})", client.set_activation_confirmation, mode)


def _dialog_card_signature(card: object) -> str:
    if isinstance(card, dict):
        name = card.get("name") or card.get("card_name") or card.get("text")
        index = card.get("card_index") or card.get("index")
    else:
        name = getattr(card, "name", None) or getattr(card, "card_name", None)
        index = getattr(card, "card_index", None) or getattr(card, "index", None)
    if name:
        return f"{index}:{name}"
    return str(card)


def _dialog_fingerprint(dialog_cards: list[CardSelection]) -> str:
    return "|".join(_dialog_card_signature(card) for card in dialog_cards)


def _resolve_dialog(
    client: JDuelBotClient,
    profile_index: ProfileIndex,
    cooldowns: TurnCooldowns,
    cfg: BotConfig,
) -> bool:
    """
    Attempt to resolve any open dialog.

    Returns True if we *think* we made progress (clicked something), else False.
    """
    dialog_cards = _try("get_dialog_card_list", client.get_dialog_card_list)
    if not dialog_cards:
        return False

    cooldowns.stuck_dialog_cycles += 1
    is_stuck = cooldowns.stuck_dialog_cycles >= 6

    fingerprint = _dialog_fingerprint(dialog_cards)
    if fingerprint == cooldowns.last_dialog_fingerprint:
        cooldowns.dialog_repeat_count += 1
    else:
        cooldowns.last_dialog_fingerprint = fingerprint
        cooldowns.dialog_repeat_count = 0

    LOG.info(
        "[DIALOG] fingerprint=%s repeat_count=%s",
        fingerprint,
        cooldowns.dialog_repeat_count,
    )

    if cooldowns.dialog_repeat_count >= 3:
        LOG.warning("[DIALOG] bailout repeat_count=%s", cooldowns.dialog_repeat_count)
        _try("cancel_activation_prompts", client.cancel_activation_prompts)
        _try(
            "set_activation_confirmation(Default)",
            client.set_activation_confirmation,
            ActivateConfirmMode.Default,
        )
        time.sleep(0.1)
        for _ in range(2):
            _try(
                "select_card_from_dialog(None,Right)",
                client.select_card_from_dialog,
                None,
                DialogButtonType.Right,
                120,
            )
            time.sleep(0.12)
        _set_confirm_mode(client, cfg)
        cooldowns.dialog_repeat_count = 0
        return True

    if cooldowns.dialog_repeat_count > 0:
        return False

    choice = profile_index.pick_dialog_choice(dialog_cards)

    sequences = [
        [("select", choice, DialogButtonType.Middle), ("confirm", None, DialogButtonType.Right)],
        [("select", choice, DialogButtonType.Right), ("confirm", None, DialogButtonType.Right)],
        [("confirm", None, DialogButtonType.Right)],
        [("confirm", None, DialogButtonType.Middle)],
    ]

    progressed = False
    for step, sel, btn in sequences:
        if sel is None:
            _try(
                f"select_card_from_dialog(None,{btn.name})",
                client.select_card_from_dialog,
                None,
                btn,
                120,
            )
        else:
            _try(
                f"select_card_from_dialog(sel={sel.card_index},{btn.name})",
                client.select_card_from_dialog,
                sel,
                btn,
                120,
            )
        progressed = True
        time.sleep(0.12)

        if not _try("is_inputting", client.is_inputting):
            cooldowns.stuck_dialog_cycles = 0
            return True

    if is_stuck:
        LOG.warning("[DIALOG] appears stuck -> trying cancel_activation_prompts + handle_unexpected_prompts")
        _try("cancel_activation_prompts", client.cancel_activation_prompts)
        time.sleep(0.1)
        _try("handle_unexpected_prompts", client.handle_unexpected_prompts)
        time.sleep(0.1)
        cooldowns.stuck_dialog_cycles = max(0, cooldowns.stuck_dialog_cycles - 3)

    return progressed


def _resolve_if_inputting(
    client: JDuelBotClient,
    cfg: BotConfig,
    profile_index: ProfileIndex,
    cooldowns: TurnCooldowns,
) -> None:
    if not _try("is_inputting", client.is_inputting):
        cooldowns.stuck_dialog_cycles = 0
        cooldowns.last_dialog_fingerprint = None
        cooldowns.dialog_repeat_count = 0
        return

    LOG.info("[STATE] is_inputting=True -> attempting prompt/dialog resolve")
    _try("handle_unexpected_prompts", client.handle_unexpected_prompts)
    _set_confirm_mode(client, cfg)

    if _resolve_dialog(client, profile_index, cooldowns, cfg):
        return

    _try("cancel_activation_prompts", client.cancel_activation_prompts)


 main
def _execute_actions(client: JDuelBotClient, cfg: BotConfig, actions: list[Action]) -> None:
    for action in actions:
        t = action.type
        a = action.args or {}
        LOG.info("[PLAN] %s %s", t, action.description or "")

        if t == "wait_input":
            _try("wait_for_input_enabled", client.wait_for_input_enabled)
        elif t == "move_phase":
            _try(f"move_phase({a.get('phase')})", client.move_phase, a["phase"])
        elif t == "advance_phase":
            _try(f"move_phase({a.get('phase')})", client.move_phase, a["phase"])
        elif t == "normal_summon":
            _try(
                f"normal_summon_monster(idx={a['hand_index']},{a['position']})",
                client.normal_summon_monster,
                a["hand_index"],
                a["position"],
            )
        elif t == "activate_monster_effect_field":
            _try(
                f"activate_monster_effect_from_field({a['position']})",
                client.activate_monster_effect_from_field,
                a["position"],
            )
        elif t == "activate_spell_hand":
            _try(
                f"activate_spell_or_trap_from_hand(idx={a['hand_index']},{a['position']})",
                client.activate_spell_or_trap_from_hand,
                a["hand_index"],
                a["position"],
            )
        elif t == "set_spell_hand":
            _try(
                f"set_spell_or_trap_from_hand(idx={a['hand_index']},{a['position']})",
                client.set_spell_or_trap_from_hand,
                a["hand_index"],
                a["position"],
            )
        elif t == "extra_deck_summon":
            _try(
                f"perform_extra_deck_summon({a['name']})",
                client.perform_extra_deck_summon,
                a["name"],
                a["positions"],
            )
        elif t == "pass":
            _try("move_phase(battle)", client.move_phase, "battle")
            time.sleep(0.1)
            _try("move_phase(end)", client.move_phase, "end")
        else:
            LOG.debug("Unknown action type=%s args=%s", t, a)

        time.sleep(cfg.action_delay_s)


def _handle_my_main_phase_1(
    client: JDuelBotClient,
    cfg: BotConfig,
    strategy,
    state: dict,
    hand,
    executor: PlanExecutor,
) -> None:
    try:
        actions = strategy.plan_main_phase_1(state, hand, client, cfg)
    except Exception:
        LOG.error("strategy.plan_main_phase_1 crashed:\n%s", traceback.format_exc())
        actions = [Action(type="pass", args={}, description="Fallback pass after strategy crash")]

    if not actions:
        actions = [Action(type="pass", args={}, description="No actions planned -> pass")]

    executor.execute(actions, client, cfg)


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
    dialog_resolver = DialogResolver(max_repeat=cfg.dialog_max_repeat)
    plan_executor = PlanExecutor()
    cooldowns = TurnCooldowns()

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

        state = snapshot_state(client) or {}
        hand_snapshot = read_hand(client, profile_index.profile)

        if _try("is_inputting", client.is_inputting):
            result = dialog_resolver.resolve(client, strategy=strategy, state=state, cfg=cfg)
            if result != "selected" and result != "canceled":
                time.sleep(cfg.tick_s)
                continue

        turn = _try("get_turn_number", client.get_turn_number)
        if isinstance(turn, int) and turn != last_turn:
            last_turn = turn
            cooldowns.stuck_dialog_cycles = 0
            cooldowns.last_dialog_fingerprint = None
            cooldowns.dialog_repeat_count = 0
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
            LOG.info(">>> ENTER handle_my_main_phase_1")
            _handle_my_main_phase_1(client, cfg, strategy, state, hand_snapshot, plan_executor)
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
