"""Dialog resolver with loop detection and safe bailout."""

from __future__ import annotations

import logging
import time
from typing import Optional

from jduel_bot.jduel_bot_enums import ActivateConfirmMode, CardSelection, DialogButtonType

LOG = logging.getLogger("dialog_resolver")


class DialogResolver:
    """
    Resolves in-game dialogs by:
    - detecting repeated identical dialogs
    - choosing a selection via Strategy.on_dialog or ProfileIndex
    - clicking in a safe confirmation sequence
    """

    def __init__(self, max_repeat: int = 3, repeat_window_s: float = 2.0, click_delay_ms: int = 120) -> None:
        self.max_repeat = max_repeat
        self.repeat_window_s = repeat_window_s
        self.click_delay_ms = click_delay_ms

        self._last_fp: Optional[str] = None
        self._last_seen: float = 0.0
        self._repeat_count: int = 0

    def reset(self) -> None:
        self._last_fp = None
        self._last_seen = 0.0
        self._repeat_count = 0

    @staticmethod
    def _fingerprint(dialog_cards: list[str]) -> str:
        # include indices so duplicates produce stable fp
        return "|".join(f"{i}:{name}" for i, name in enumerate(dialog_cards))

    @staticmethod
    def _safe_call(client: object, name: str, *args):
        fn = getattr(client, name, None)
        if callable(fn):
            return fn(*args)
        return None

    @staticmethod
    def _maybe_set_confirm_on(client: object) -> None:
        fn = getattr(client, "set_activation_confirmation", None)
        if callable(fn):
            try:
                fn(ActivateConfirmMode.On)
            except Exception:
                pass

    def resolve(
        self,
        client: object,
        profile_index: Optional[object] = None,
        strategy: Optional[object] = None,
        state: Optional[dict] = None,
        cfg: Optional[object] = None,
    ) -> str:
        dialog_list = list(self._safe_call(client, "get_dialog_card_list") or [])
        if not dialog_list:
            self.reset()
            return "no_dialog"

        now = time.monotonic()
        fp = self._fingerprint(dialog_list)

        if fp == self._last_fp and (now - self._last_seen) < self.repeat_window_s:
            self._repeat_count += 1
        else:
            self._repeat_count = 1

        self._last_fp = fp
        self._last_seen = now

        LOG.info("[DIALOG] cards=%s repeat=%s", dialog_list, self._repeat_count)

        # Bailout if we're repeating
        if self._repeat_count >= self.max_repeat:
            LOG.warning("[DIALOG] bailout -> cancel prompts + try close")
            self._safe_call(client, "cancel_activation_prompts")
            try:
                self._safe_call(client, "set_activation_confirmation", ActivateConfirmMode.Default)
            except Exception:
                pass

            # try closing the dialog
            for _ in range(2):
                self._safe_call(client, "select_card_from_dialog", None, DialogButtonType.Right, self.click_delay_ms)
                time.sleep(0.12)

            self.reset()
            return "bailout"

        self._maybe_set_confirm_on(client)

        selection = self._pick_selection(dialog_list, profile_index, strategy, state or {}, client, cfg)

        # If we saw the same dialog more than once, rotate the chosen index to avoid deadlocking on duplicates
        if self._repeat_count > 1 and dialog_list:
            idx = (self._repeat_count - 1) % len(dialog_list)
            selection = CardSelection(card_name=str(dialog_list[idx]), card_index=idx)

        sequences = [
            [(selection, DialogButtonType.Middle), (None, DialogButtonType.Right)],
            [(selection, DialogButtonType.Right), (None, DialogButtonType.Right)],
            [(None, DialogButtonType.Right)],
            [(None, DialogButtonType.Middle)],
        ]

        for seq in sequences:
            for sel, btn in seq:
                self._safe_call(client, "select_card_from_dialog", sel, btn, self.click_delay_ms)
                time.sleep(0.12)

                # Stop early if input is cleared
                is_inputting = self._safe_call(client, "is_inputting")
                if not is_inputting:
                    return "selected" if sel is not None else "canceled"

        return "attempted"

    @staticmethod
    def _pick_selection(dialog_list: list[str], profile_index: Optional[object], strategy: Optional[object], state: dict, client: object, cfg: Optional[object]) -> CardSelection:
        # Strategy override
        if strategy is not None:
            on_dialog = getattr(strategy, "on_dialog", None)
            if callable(on_dialog):
                try:
                    out = on_dialog(dialog_list, state, client, cfg)
                    if isinstance(out, CardSelection):
                        return out
                except Exception:
                    pass

        # ProfileIndex preference
        if profile_index is not None:
            pick = getattr(profile_index, "pick_dialog_choice", None)
            if callable(pick):
                try:
                    out = pick(dialog_list)
                    if isinstance(out, CardSelection):
                        return out
                except Exception:
                    pass

        # Default: pick first
        return CardSelection(card_name=str(dialog_list[0]), card_index=0)
