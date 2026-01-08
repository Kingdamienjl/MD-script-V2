"""Example duel logic bot for Swordsoul."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from jduel_bot.env_config import BotConfig, load_config


@dataclass
class DuelState:
    turn_count: int = 0
    action_count: int = 0
    stuck_dialog_cycles: int = 0


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
        time.sleep(self.cfg.action_delay)

        if self._detect_dialog_stuck():
            self._resolve_dialog()
            return True

        return True

    def _detect_dialog_stuck(self) -> bool:
        if self.state.action_count % 5 == 0:
            self.state.stuck_dialog_cycles += 1
            return True
        return False

    def _resolve_dialog(self) -> None:
        if self.state.stuck_dialog_cycles >= self.cfg.stuck_dialog_cycle_limit:
            logging.warning("Dialog stuck limit reached; aborting.")
            self.state.action_count = self.cfg.failsafe_action_limit
            return
        logging.info("Resolving dialog with click delay %ss", self.cfg.dialog_click_delay)
        time.sleep(self.cfg.dialog_click_delay)


if __name__ == "__main__":
    cfg = load_config()
    bot = SwordsoulDuelLogicBot(cfg)
    bot.run()
