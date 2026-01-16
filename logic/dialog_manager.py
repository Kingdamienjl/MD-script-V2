"""Deterministic dialog handling."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

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
        self._repeat_limit = repeat_limit
        self._state: dict[str, object] = {}

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

    def resolve_once(self, client: object, state: Optional[object], profile: dict, cfg) -> bool:
        dialog_list = list(getattr(client, "get_dialog_card_list", lambda: [])())
        if not dialog_list:
            return False

        signature = tuple(dialog_list)
        choice_name = self._choose_by_priority(dialog_list, profile)

        last_signature = self._get_state(state, "last_dialog_signature")
        last_choice = self._get_state(state, "last_dialog_choice")
        same_count = int(self._get_state(state, "same_dialog_count") or 0)

        if signature == last_signature and choice_name == last_choice:
            same_count += 1
        else:
            same_count = 0

        self._set_state(state, "last_dialog_signature", signature)
        self._set_state(state, "last_dialog_choice", choice_name)
        self._set_state(state, "same_dialog_count", same_count)

        repeat_limit = getattr(cfg, "dialog_max_repeat", self._repeat_limit)
        if same_count > repeat_limit:
            logging.warning("[DIALOG] stuck signature=%s -> cancel_activation_prompts", signature)
            getattr(client, "cancel_activation_prompts", lambda: None)()
            return True

        if choice_name is None:
            logging.info("[DIALOG] cards=%s choice=None", dialog_list)
            return False

        logging.info("[DIALOG] cards=%s choice=%s", dialog_list, choice_name)
        if self._select_and_confirm(client, dialog_list, choice_name, profile):
            return True
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

    @staticmethod
    def _choose_by_priority(dialog_list: list[str], profile: dict) -> Optional[str]:
        priority = profile.get("dialog_priority", [])
        if not isinstance(priority, list):
            return None
        for wanted in priority:
            if wanted in dialog_list:
                return wanted
        return None

    @staticmethod
    def _select_and_confirm(
        client: object,
        dialog_list: list[str],
        choice_name: str,
        profile: dict,
    ) -> bool:
        button_mode = profile.get("dialog_default_button", "middle_then_right")
        if button_mode != "middle_then_right":
            button_mode = "middle_then_right"

        try:
            index = dialog_list.index(choice_name)
        except ValueError:
            return False

        select = getattr(client, "select_card_from_dialog", None)
        if not callable(select):
            return False

        select(index, DialogButtonType.Middle)
        select(None, DialogButtonType.Right)
        return True

    def _get_state(self, state: Optional[object], key: str):
        if isinstance(state, dict):
            return state.get(key)
        if state is None:
            return self._state.get(key)
        return getattr(state, key, self._state.get(key))

    def _set_state(self, state: Optional[object], key: str, value) -> None:
        if isinstance(state, dict):
            state[key] = value
            return
        if state is None:
            self._state[key] = value
            return
        try:
            setattr(state, key, value)
        except Exception:
            self._state[key] = value
