"""Dialog resolver with loop detection and safe bailout."""

from __future__ import annotations

import logging
import time
from typing import Optional

from jduel_bot.jduel_bot_enums import CardSelection, DialogButtonType

LOG = logging.getLogger("dialog_resolver")


class DialogResolver:
    def __init__(self, max_repeat: int = 3, repeat_window_s: float = 2.0) -> None:
        self.max_repeat = max_repeat
        self.repeat_window_s = repeat_window_s
        self._last_fingerprint: Optional[str] = None
        self._last_seen_at: float = 0.0
        self._repeat_count: int = 0

    def resolve(
        self,
        client: object,
        profile_index: object | None = None,
        strategy: object | None = None,
        state: Optional[dict] = None,
        cfg: object | None = None,
    ) -> str:
        dialog_list = list(getattr(client, "get_dialog_card_list", lambda: [])())
        if not dialog_list:
            self._repeat_count = 0
            self._last_fingerprint = None
            return "no_dialog"

        fingerprint = "|".join(str(x) for x in dialog_list)
        now = time.monotonic()

        if fingerprint == self._last_fingerprint and (now - self._last_seen_at) < self.repeat_window_s:
            self._repeat_count += 1
        else:
            self._repeat_count = 1

        self._last_fingerprint = fingerprint
        self._last_seen_at = now

        if self._repeat_count >= self.max_repeat:
            LOG.warning("[DIALOG] repeat bailout cards=%s count=%s", dialog_list, self._repeat_count)
            getattr(client, "cancel_activation_prompts", lambda: None)()
            getattr(client, "handle_unexpected_prompts", lambda: None)()
            # attempt a safe "confirm" style click
            try:
                sel = CardSelection(card_name=str(dialog_list[0]), card_index=0)
                getattr(client, "select_card_from_dialog", lambda *_args: None)(sel, DialogButtonType.Right, 120)
            except Exception:
                pass
            self._repeat_count = 0
            return "bailout"

        selection = self._choose_selection(dialog_list, profile_index, strategy, state or {}, client, cfg)
        if selection is None:
            # default: just click first with Right
            sel = CardSelection(card_name=str(dialog_list[0]), card_index=0)
            getattr(client, "select_card_from_dialog", lambda *_args: None)(sel, DialogButtonType.Right, 120)
            LOG.info("[DIALOG] cards=%s action=default_right", dialog_list)
            return "selected"

        # Default “Middle then Right” is the least-wrong pattern across many MD dialogs.
        getattr(client, "select_card_from_dialog", lambda *_args: None)(selection, DialogButtonType.Middle, 120)
        time.sleep(0.12)
        getattr(client, "select_card_from_dialog", lambda *_args: None)(selection, DialogButtonType.Right, 120)
        LOG.info("[DIALOG] cards=%s action=select %s", dialog_list, selection.card_name)
        return "selected"

    @staticmethod
    def _choose_selection(
        dialog_cards: list[str],
        profile_index: object | None,
        strategy: object | None,
        state: dict,
        client: object,
        cfg: object | None,
    ) -> Optional[CardSelection]:
        # 1) strategy override
        if strategy is not None:
            on_dialog = getattr(strategy, "on_dialog", None)
            if callable(on_dialog):
                try:
                    pref = on_dialog(dialog_cards, state, client, cfg)
                    if isinstance(pref, CardSelection):
                        return pref
                    if isinstance(pref, int) and 0 <= pref < len(dialog_cards):
                        return CardSelection(card_name=str(dialog_cards[pref]), card_index=pref)
                    if isinstance(pref, str):
                        for i, name in enumerate(dialog_cards):
                            if name == pref:
                                return CardSelection(card_name=str(name), card_index=i)
                except Exception:
                    # never let strategy dialog crash the loop
                    pass

        # 2) profile-based pick
        if profile_index is not None:
            picker = getattr(profile_index, "pick_dialog_choice", None)
            if callable(picker):
                try:
                    picked = picker(dialog_cards)
                    if isinstance(picked, CardSelection):
                        return picked
                except Exception:
                    pass

        # 3) fallback first
        if dialog_cards:
            return CardSelection(card_name=str(dialog_cards[0]), card_index=0)
        return None
