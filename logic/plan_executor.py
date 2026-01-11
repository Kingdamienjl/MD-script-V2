"""Plan executor for safe action execution (with retry)."""

from __future__ import annotations

import logging
import time
from typing import Iterable, Optional

try:
    from logic.action_queue import Action
except Exception:  # pragma: no cover
    from logic.strategy_registry import Action  # type: ignore

LOG = logging.getLogger("plan_executor")


class PlanExecutor:
    def execute(self, actions: Iterable[Action], client: object, cfg: Optional[object] = None) -> None:
        for action in actions:
            self._execute_with_retry(client, action, cfg)

    def execute_next(self, actions: list[Action], index: int, client: object, cfg: Optional[object] = None) -> bool:
        if index < 0 or index >= len(actions):
            return False
        return self._execute_with_retry(client, actions[index], cfg)

    def _execute_with_retry(self, client: object, action: Action, cfg: Optional[object]) -> bool:
        attempts = max(1, getattr(action, "retries", 1))
        delay_ms = int(getattr(action, "delay_ms", 120))

        for attempt in range(attempts):
            ok = self._execute_action(client, action)
            if ok:
                LOG.info("[EXEC] ok type=%s desc=%s", action.type, getattr(action, "description", ""))
                self._post_action_delay(cfg)
                return True

            if attempt < attempts - 1:
                time.sleep(delay_ms / 1000)

        LOG.warning("[EXEC] fail type=%s desc=%s err=exhausted", action.type, getattr(action, "description", ""))
        self._post_action_delay(cfg)
        return False

    @staticmethod
    def _post_action_delay(cfg: Optional[object]) -> None:
        if cfg is None:
            time.sleep(0.12)
            return
        delay = getattr(cfg, "action_delay_s", None)
        if isinstance(delay, (int, float)) and delay > 0:
            time.sleep(float(delay))
        else:
            time.sleep(0.12)

    @staticmethod
    def _call(client: object, name: str, *args, **kwargs) -> None:
        fn = getattr(client, name, None)
        if not callable(fn):
            raise AttributeError(f"Client missing method: {name}")
        try:
            fn(*args, **kwargs)
        except TypeError:
            fn(*args)

    def _execute_action(self, client: object, action: Action) -> bool:
        args = getattr(action, "args", {}) or {}
        try:
            t = action.type

            if t == "normal_summon":
                self._call(client, "normal_summon_monster", args["index"], args["position"])
                return True

            if t == "special_summon_hand":
                try:
                    self._call(client, "special_summon_monster_from_hand", args["index"], args["position"])
                except TypeError:
                    self._call(client, "special_summon_monster_from_hand", args["index"], args["position"], 5)
                return True

            if t == "activate_hand":
                self._call(client, "activate_monster_effect_from_hand", args["index"])
                return True

            if t == "activate_field":
                self._call(client, "activate_monster_effect_from_field", args["position"])
                return True

            if t == "activate_spell_hand":
                self._call(client, "activate_spell_or_trap_from_hand", args["index"], args["position"])
                return True

            if t == "set_spell_hand":
                self._call(client, "set_spell_or_trap_from_hand", args["index"], args["position"])
                return True

            if t in ("extra_summon", "extra_deck_summon"):
                self._call(client, "perform_extra_deck_summon", args["name"], args["positions"])
                return True

            if t in ("advance_phase", "move_phase"):
                self._call(client, "move_phase", args.get("phase_enum") or args.get("phase"))
                return True

            if t == "wait_input":
                self._call(client, "wait_for_input_enabled")
                return True

            if t == "pass":
                try:
                    self._call(client, "move_phase", "battle")
                    time.sleep(0.1)
                    self._call(client, "move_phase", "end")
                except Exception:
                    pass
                return True

            LOG.debug("[EXEC] unknown action type=%s args=%s", t, args)
            return False

        except Exception as exc:
            LOG.warning("[EXEC] fail type=%s desc=%s err=%s", action.type, getattr(action, "description", ""), exc)
            return False
