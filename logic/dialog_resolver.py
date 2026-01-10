"""Dialog resolver with loop detection + safe bailout."""

from __future__ import annotations

import logging
import time
from typing import Optional

from jduel_bot.jduel_bot_enums import ActivateConfirmMode, CardSelection, DialogButtonType

LOG = logging.getLogger("dialog_resolver")


class DialogResolver:
    """
    Resolve selection dialogs deterministically.

    - Prefer strategy-provided preferences (strategy.on_dialog)
    - Else fall back to profile priority (ProfileIndex.pick_dialog_choice)
    - Detect repeated dialogs and bail out safely (cancel prompts + confirm)
    """

    def __init__(self, max_repeat: int = 3, repeat_window_s: float = 2.5) -> None:
        self.max_repeat = max_repeat
        self.repeat_window_s = repeat_window_s

        self._last_fingerprint: Optional[str] = None
        self._last_seen_at: float = 0.0
        self._repeat_count: int = 0

    def resolve(
        self,
        client: object,
        profile_index: Optional[object] = None,
        strategy: Optional[object] = None,
        state: Optional[dict] = None,
        cfg: Optional[object] = None,
    ) -> str:
        get_list = getattr(client, "get_dialog_card_list", None)
        if not callable(get_list):
            return "no_dialog"

        dialog_cards = list(get_list())
        if not dialog_cards:
            return "no_dialog"

        fingerprint = "|".join(str(x) for x in dialog_cards)
        now = time.monotonic()

        if fingerprint == self._last_fingerprint and (now - self._last_seen_at) < self.repeat_window_s:
            self._repeat_count += 1
        else:
            self._repeat_count = 1

        self._last_fingerprint = fingerprint
        self._last_seen_at = now

        if self._repeat_count >= self.max_repeat:
            LOG.warning("[DIALOG] repeat detected -> bailout fingerprint=%s count=%s", fingerprint, self._repeat_count)
            self._repeat_count = 0
            return self._bailout(client)

        # 1) Strategy preference
        selection = self._strategy_preference(strategy, dialog_cards, state or {}, client, cfg)

        # 2) Profile fallback
        if selection is None and profile_index is not None:
            pick = getattr(profile_index, "pick_dialog_choice", None)
            if callable(pick):
                selection = pick(dialog_cards)

        if selection is None:
            self._confirm(client)
            return "canceled"

        return "selected" if self._select_and_confirm(client, selection) else "no_action"

    @staticmethod
    def _strategy_preference(strategy: Optional[object], dialog_cards: list[str], state: dict, client: object, cfg: Optional[object]):
        if strategy is None:
            return None
        on_dialog = getattr(strategy, "on_dialog", None)
        if not callable(on_dialog):
            return None
        try:
            pref = on_dialog(dialog_cards, state, client, cfg)
        except Exception as exc:
            LOG.debug("[DIALOG] strategy.on_dialog failed: %s", exc)
            return None

        if pref is None:
            return None
        if isinstance(pref, CardSelection):
            return pref
        if isinstance(pref, list) and pref and isinstance(pref[0], CardSelection):
            return pref[0]
        return None

    def _bailout(self, client: object) -> str:
        cancel = getattr(client, "cancel_activation_prompts", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                pass

        set_conf = getattr(client, "set_activation_confirmation", None)
        if callable(set_conf):
            try:
                set_conf(ActivateConfirmMode.Default)
            except Exception:
                pass

        for _ in range(2):
            self._confirm(client)
            time.sleep(0.12)

        if callable(set_conf):
            try:
                set_conf(ActivateConfirmMode.On)
            except Exception:
                pass

        return "bailout"

    @staticmethod
    def _confirm(client: object) -> None:
        sel = getattr(client, "select_card_from_dialog", None)
        if not callable(sel):
            return
        try:
            sel(None, DialogButtonType.Right, 120)
        except TypeError:
            try:
                sel(None, DialogButtonType.Right)
            except Exception:
                pass
        except Exception:
            pass

    @staticmethod
    def _select_and_confirm(client: object, selection: CardSelection) -> bool:
        sel = getattr(client, "select_card_from_dialog", None)
        is_inputting = getattr(client, "is_inputting", None)
        if not callable(sel):
            return False

        try:
            sel(selection, DialogButtonType.Middle, 120)
        except TypeError:
            try:
                sel(selection, DialogButtonType.Middle)
            except Exception:
                pass
        except Exception:
            pass

        time.sleep(0.12)
        DialogResolver._confirm(client)
        time.sleep(0.12)

        if callable(is_inputting):
            try:
                return not bool(is_inputting())
            except Exception:
                return True
        return True
