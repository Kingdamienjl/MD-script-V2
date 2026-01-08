"""Example duel logic bot for Swordsoul."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence

from jduel_bot.config import BotConfig, load_config
from logic.action_queue import ActionQueue
from logic.dialog_resolver import DialogButtonType, DialogResolver
from logic.state_manager import TurnCooldowns, snapshot_state
from logic.strategy_registry import load_strategy


class ActivateConfirmMode(str, Enum):
    On = "on"
    Off = "off"


@dataclass
class DuelState:
    turn_count: int = 0
    action_count: int = 0
    stuck_dialog_cycles: int = 0
    last_used_card_name: Optional[str] = None
    phase: str = "main1"


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


class SwordsoulDuelLogicBot:
    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self.state = DuelState()
        self.turn_cooldowns = TurnCooldowns()
        self.dialog_resolver = DialogResolver()
        self.action_queue = ActionQueue()
        self.profile_path = self._resolve_profile_path()
        self.strategy = load_strategy(
            cfg.deck, cfg.strategy, str(cfg.decks_dir), str(self.profile_path)
        )

    def run(self) -> None:
        _configure_logging()
        logging.info(
            "[DECK] deck=%s strategy=%s profile_path=%s",
            self.cfg.deck,
            self.cfg.strategy,
            self.profile_path,
        )
        logging.info("Starting duel logic bot.")

        while True:
            self._start_turn()
            self.handle_my_main_phase_1()
            time.sleep(self.cfg.action_delay_ms / 1000)

    def _start_turn(self) -> None:
        self.state.turn_count += 1
        self.turn_cooldowns.reset_for_new_turn()
        hand_size = self.get_hand_size()
        lp = self.get_life_points()
        logging.info(
            "[TURN] n=%s phase=%s hand_size=%s lp=%s",
            self.state.turn_count,
            self.state.phase,
            hand_size,
            lp,
        )
        board_state = self._safe_board_state()
        if board_state is not None:
            self._write_turn_snapshot(board_state)

    def handle_my_main_phase_1(self) -> None:
        if self.is_inputting():
            result = self.dialog_resolver.resolve(self)
            if result == "bailout":
                return
            return

        snapshot = snapshot_state(self)
        actions = self.strategy.plan_main_phase_1(snapshot, self, self.cfg)
        if not actions:
            self._handle_empty_plan()
            return

        self.turn_cooldowns.empty_ticks = 0
        logging.info(
            "[PLAN] actions=[%s]",
            ", ".join(action.description for action in actions),
        )
        self.action_queue.push(actions)
        self.action_queue.execute(self, self.cfg, self.dialog_resolver)

    def _handle_empty_plan(self) -> None:
        self.turn_cooldowns.empty_ticks += 1
        if self.turn_cooldowns.empty_ticks < 2:
            return
        if self.turn_cooldowns.phase_advanced:
            return
        if self.can_we_battle() and self.has_attackers():
            self.advance_phase("battle")
        else:
            self.advance_phase("end")
        self.turn_cooldowns.phase_advanced = True

    def _resolve_profile_path(self) -> Path:
        deck_profile = self.cfg.decks_dir / self.cfg.deck / "profile.json"
        if deck_profile.exists():
            return deck_profile
        return self.cfg.profile_path

    def _write_turn_snapshot(self, board_state: dict) -> None:
        path = Path("replay/recorded")
        path.mkdir(parents=True, exist_ok=True)
        filename = path / f"turn_{self.state.turn_count}_state.json"
        filename.write_text(json.dumps(board_state, indent=2, sort_keys=True))

    def is_inputting(self) -> bool:
        return False

    def get_dialog_card_list(self) -> Sequence[str]:
        return []

    def select_dialog_card_by_index(
        self, index: int, dialog_list: Sequence[str]
    ) -> None:
        if not dialog_list:
            return
        selected_name = dialog_list[min(index, len(dialog_list) - 1)]
        self.state.last_used_card_name = selected_name
        self.select_card_from_dialog(index, DialogButtonType.Left, self.cfg.dialog_click_delay_ms)

    def confirm_dialog(self) -> None:
        self.select_card_from_dialog(None, DialogButtonType.Right, self.cfg.dialog_click_delay_ms)

    def dump_dialog_snapshot(
        self,
        dialog_list: Sequence[str],
        last_used_card_name: Optional[str],
    ) -> None:
        snapshot = {
            "turn": self.state.turn_count,
            "phase": self.state.phase,
            "is_inputting": self.is_inputting(),
            "dialog_list": list(dialog_list),
            "last_used_card_name": last_used_card_name,
            "board_state": self._safe_board_state(),
        }
        self._write_snapshot(self.cfg.dump_dir, snapshot)

    def _safe_board_state(self) -> Optional[dict]:
        try:
            return self.get_board_state()
        except Exception:
            return None

    def _write_snapshot(self, dump_dir: Path, snapshot: dict) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        path = dump_dir / f"dialog_snapshot_{timestamp}.json"
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True))

    def toggle_activation_confirmation_for_escape(self) -> None:
        self.set_activation_confirmation(ActivateConfirmMode.Off)
        time.sleep(self.cfg.dialog_click_delay_ms / 1000)
        self.select_card_from_dialog(None, DialogButtonType.Right, self.cfg.dialog_click_delay_ms)
        time.sleep(self.cfg.dialog_click_delay_ms / 1000)
        self.set_activation_confirmation(ActivateConfirmMode.On)

    def cancel_activation_prompts(self) -> None:
        return None

    def handle_unexpected_prompts(self) -> None:
        return None

    def select_card_from_dialog(
        self,
        card_index: Optional[int],
        button: DialogButtonType,
        delay_ms: int | None = None,
    ) -> None:
        _ = (card_index, button, delay_ms)

    def wait_for_input_enabled(self) -> None:
        return None

    def set_activation_confirmation(self, mode: ActivateConfirmMode) -> None:
        _ = mode

    def get_board_state(self) -> dict:
        return {}

    def get_hand_size(self) -> int:
        return 0

    def get_hand_card_name(self, index: int) -> Optional[str]:
        _ = index
        return None

    def get_life_points(self) -> int:
        return 0

    def can_normal_summon(self) -> bool:
        return True

    def get_free_spell_trap_zones(self) -> int:
        return 0

    def get_free_monster_zones(self) -> int:
        return 1

    def get_field_monster_count(self) -> int:
        return 0

    def normal_summon_from_hand(self, hand_index: int) -> None:
        self.state.last_used_card_name = self._get_known_hand_name(hand_index)

    def special_summon_from_hand(self, hand_index: int) -> None:
        self.state.last_used_card_name = self._get_known_hand_name(hand_index)

    def activate_effect_from_hand(self, hand_index: int) -> None:
        self.state.last_used_card_name = self._get_known_hand_name(hand_index)

    def activate_effect_from_field(self, field_index: int) -> None:
        _ = field_index

    def perform_extra_deck_summon(self, name: str) -> None:
        _ = name

    def set_spell_trap_from_hand(self, hand_index: int) -> None:
        self.state.last_used_card_name = self._get_known_hand_name(hand_index)

    def advance_phase(self, phase: str) -> None:
        self.state.phase = phase

    def can_we_battle(self) -> bool:
        return False

    def has_attackers(self) -> bool:
        return False

    def _get_known_hand_name(self, hand_index: int) -> Optional[str]:
        try:
            return self.get_hand_card_name(hand_index)
        except Exception:
            return None


if __name__ == "__main__":
    cfg = load_config()
    bot = SwordsoulDuelLogicBot(cfg)
    bot.run()
