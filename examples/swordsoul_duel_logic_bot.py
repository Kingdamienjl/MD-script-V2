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

from jduel_bot.env_config import BotConfig, load_config


class DialogButtonType(str, Enum):
    Left = "left"
    Right = "right"


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


@dataclass
class DialogSignatureTracker:
    last_signature: Optional[tuple[str, ...]] = None
    repeats_count: int = 0
    last_change_time: float = 0.0


class DialogResolver:
    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self.signature = DialogSignatureTracker()
        self.escape_step = 0

    def resolve(self, bot: "SwordsoulDuelLogicBot") -> bool:
        if not bot.is_inputting():
            self._reset_signature()
            self.escape_step = 0
            return False

        dialog_list = bot.get_dialog_card_list()
        self._update_signature(dialog_list)

        if self.signature.repeats_count > self.cfg.dialog_max_cycles:
            logging.warning("Dialog signature stuck; attempting escape sequence.")
            bot.state.stuck_dialog_cycles += 1
            bot.dump_dialog_snapshot(
                dialog_list=dialog_list,
                last_used_card_name=bot.state.last_used_card_name,
            )
            return self._run_escape_sequence(bot)

        if dialog_list:
            bot.select_dialog_card_by_index(0, dialog_list)
            return bot.is_inputting()

        bot.confirm_dialog()
        return bot.is_inputting()

    def _run_escape_sequence(self, bot: "SwordsoulDuelLogicBot") -> bool:
        if self.escape_step == 0:
            self.escape_step = 1
        interactions = 0
        while interactions < 2 and self.escape_step:
            interactions += 1
            if self.escape_step == 1:
                bot.cancel_activation_prompts()
                self.escape_step = 2
            elif self.escape_step == 2:
                bot.handle_unexpected_prompts()
                self.escape_step = 3
            elif self.escape_step == 3:
                bot.confirm_dialog()
                self.escape_step = 4
            elif self.escape_step == 4:
                bot.wait_for_input_enabled()
                self.escape_step = 5
            elif self.escape_step == 5:
                if bot.is_inputting():
                    bot.toggle_activation_confirmation_for_escape()
                self.escape_step = 0
            self._sleep_click_delay()
        return bot.is_inputting()

    def _sleep_click_delay(self) -> None:
        time.sleep(self.cfg.dialog_click_delay_ms / 1000)

    def _update_signature(self, dialog_list: Sequence[str]) -> None:
        signature = tuple(dialog_list)
        if signature == self.signature.last_signature:
            self.signature.repeats_count += 1
        else:
            self.signature.last_signature = signature
            self.signature.repeats_count = 0
            self.signature.last_change_time = time.monotonic()

    def _reset_signature(self) -> None:
        self.signature = DialogSignatureTracker()


def _configure_logging(cfg: BotConfig) -> None:
    logging.basicConfig(
        filename=cfg.log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


class SwordsoulDuelLogicBot:
    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self.state = DuelState()
        self.dialog_resolver = DialogResolver(cfg)

    def run(self) -> None:
        _configure_logging(self.cfg)
        logging.info("Connecting to duel service at %s", self.cfg.zmq_address)

        while self._within_failsafe_limits():
            if not self._perform_turn():
                break

        logging.info(
            "Exited after %s turns and %s actions",
            self.state.turn_count,
            self.state.action_count,
        )

    def _within_failsafe_limits(self) -> bool:
        if not self.cfg.failsafe_enabled:
            return True
        if self.state.action_count >= self.cfg.failsafe_action_limit:
            logging.warning("Failsafe action limit reached.")
            return False
        if self.state.turn_count >= self.cfg.failsafe_turn_limit:
            logging.warning("Failsafe turn limit reached.")
            return False
        if self.state.stuck_dialog_cycles >= self.cfg.stuck_dialog_cycle_limit:
            logging.warning("Stuck dialog cycle limit reached.")
            return False
        return True

    def _perform_turn(self) -> bool:
        self.state.turn_count += 1
        for attempt in range(1, self.cfg.max_retries + 1):
            if self._request_action(attempt):
                return True
            logging.info("Retrying action after timeout.")
        return False

    def _request_action(self, attempt: int) -> bool:
        self.state.action_count += 1
        logging.info("Attempt %s with timeout %sms", attempt, self.cfg.timeout_ms)
        time.sleep(self.cfg.action_delay_ms / 1000)

        if self.dialog_resolver.resolve(self):
            return True

        self.handle_my_main_phase_1()
        return True

    def handle_my_main_phase_1(self) -> None:
        logging.info("Handling main phase 1 logic.")

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
        delay_ms: int,
    ) -> None:
        _ = (card_index, button, delay_ms)

    def wait_for_input_enabled(self) -> None:
        return None

    def set_activation_confirmation(self, mode: ActivateConfirmMode) -> None:
        _ = mode

    def get_board_state(self) -> dict:
        return {}


if __name__ == "__main__":
    cfg = load_config()
    bot = SwordsoulDuelLogicBot(cfg)
    bot.run()
