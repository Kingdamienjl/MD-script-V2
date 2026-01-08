"""Expectation-driven dialog handling."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

from logic.dialog_resolver import DialogButtonType


@dataclass
class DialogExpectation:
    purpose: str
    allowed_names: list[str]
    count: int
    confirm: str


class DialogManager:
    def __init__(self, repeat_limit: int = 3) -> None:
        self._expectation: Optional[DialogExpectation] = None
        self._recent: Deque[tuple[str, ...]] = deque(maxlen=repeat_limit)
        self._repeat_limit = repeat_limit

    def expect_cards(
        self,
        purpose: str,
        allowed_names: list[str],
        count: int = 1,
        confirm: str = "right",
    ) -> None:
        self._expectation = DialogExpectation(
            purpose=purpose,
            allowed_names=allowed_names,
            count=count,
            confirm=confirm,
        )

    def clear_expectation(self) -> None:
        self._expectation = None

    def handle_if_present(self, client: object) -> bool:
        dialog_list = list(getattr(client, "get_dialog_card_list", lambda: [])())
        if not dialog_list:
            return False
        logging.info("[DIALOG] list=%s", dialog_list)
        self._recent.append(tuple(dialog_list))

        if self._expectation:
            handled = self._handle_expected_dialog(client, dialog_list)
            logging.info(
                "[DIALOG] expected=%s handled=%s",
                self._expectation.purpose,
                handled,
            )
            if handled:
                self.clear_expectation()
            return handled

        if self._is_stuck():
            logging.warning("[DIALOG] unknown -> canceled")
            self.clear_expectation()
            return self.safe_cancel_unknown_dialog(client)
        return False

    def safe_cancel_unknown_dialog(self, client: object) -> bool:
        select = getattr(client, "select_card_from_dialog", None)
        if callable(select):
            select(None, DialogButtonType.Right)
            select(None, DialogButtonType.Left)
            return True
        return False

    def _handle_expected_dialog(self, client: object, dialog_list: list[str]) -> bool:
        if not self._expectation:
            return False
        allowed = set(self._expectation.allowed_names)
        select = getattr(client, "select_card_from_dialog", None)
        if not callable(select):
            return False
        matches = [idx for idx, name in enumerate(dialog_list) if name in allowed]
        if not matches:
            return False
        for idx in matches[: self._expectation.count]:
            select(idx, DialogButtonType.Left)
        if self._expectation.confirm == "right":
            select(None, DialogButtonType.Right)
        return True

    def _is_stuck(self) -> bool:
        if len(self._recent) < self._repeat_limit:
            return False
        first = self._recent[0]
        return all(entry == first for entry in self._recent)
