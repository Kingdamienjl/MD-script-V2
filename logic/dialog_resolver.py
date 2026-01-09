"""Dialog resolver with loop detection and safe bailout."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

from logic.dialog_manager import DialogManager
from logic.strategy_base import Strategy


class DialogButtonType(str, Enum):
    Left = "left"
    Middle = "middle"
    Right = "right"


LOG = logging.getLogger("dialog_resolver")


class DialogResolver:
    def __init__(self, max_repeat: int = 3) -> None:
        self.dialog_manager = DialogManager(repeat_limit=max_repeat)

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

        state_obj = state or {}
        profile = getattr(strategy, "profile", {}) if strategy else {}
        handled = self.dialog_manager.resolve_once(client, state_obj, profile, cfg)
        return "selected" if handled else "no_action"

    @staticmethod
    def _log(dialog_list: list[str], action: str, reason: str) -> None:
        LOG.info("[DIALOG] cards=%s action=%s reason=%s", dialog_list, action, reason)
