"""Dialog resolver with loop detection and safe bailout."""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Optional

from logic.strategy_base import CardSelection, Strategy


class DialogButtonType(str, Enum):
    Left = "left"
    Right = "right"


LOG = logging.getLogger("dialog_resolver")


class DialogResolver:
    def __init__(self, max_repeat: int = 3, repeat_window_s: float = 2.0) -> None:
        self.last_dialog_cards: Optional[tuple[str, ...]] = None
        self.last_dialog_seen_at: float = 0.0
        self.same_dialog_count: int = 0
        self.max_repeat = max_repeat
        self.repeat_window_s = repeat_window_s

    def resolve(
        self,
        client: object,
        strategy: Optional[Strategy] = None,
        state: Optional[dict] = None,
        cfg: Optional[object] = None,
    ) -> str:
        dialog_list = list(getattr(client, "get_dialog_card_list", lambda: [])())
        if not dialog_list:
            return "no_dialog"

        now = time.monotonic()
        cards_tuple = tuple(dialog_list)
        if cards_tuple == self.last_dialog_cards and (now - self.last_dialog_seen_at) < self.repeat_window_s:
            self.same_dialog_count += 1
        else:
            self.same_dialog_count = 1
        self.last_dialog_cards = cards_tuple
        self.last_dialog_seen_at = now

        if self.same_dialog_count >= self.max_repeat:
            LOG.warning(
                "[DIALOG] cards=%s action=bailout reason=repeat count=%s",
                dialog_list,
                self.same_dialog_count,
            )
            getattr(client, "cancel_activation_prompts", lambda: None)()
            getattr(client, "select_card_from_dialog", lambda *_args: None)(
                None, DialogButtonType.Right
            )
            self.same_dialog_count = 0
            return "bailout"

        preferences = self._get_preferences(strategy, dialog_list, state or {}, client, cfg)
        if preferences:
            selection = preferences[0]
            self._select(client, selection)
            LOG.info("[DIALOG] cards=%s action=select reason=preference", dialog_list)
            return "selected"

        getattr(client, "select_card_from_dialog", lambda *_args: None)(None, DialogButtonType.Right)
        LOG.info("[DIALOG] cards=%s action=cancel reason=no_preference", dialog_list)
        return "canceled"

    @staticmethod
    def _get_preferences(
        strategy: Optional[Strategy],
        dialog_cards: list[str],
        state: dict,
        client: object,
        cfg: Optional[object],
    ) -> Optional[list[CardSelection]]:
        if strategy is None:
            return None
        on_dialog = getattr(strategy, "on_dialog", None)
        if not callable(on_dialog):
            return None
        return on_dialog(dialog_cards, state, client, cfg)

    @staticmethod
    def _select(client: object, selection: CardSelection) -> None:
        button = DialogButtonType.Right if selection.button == "right" else DialogButtonType.Left
        getattr(client, "select_card_from_dialog", lambda *_args: None)(
            selection.index,
            button,
        )
