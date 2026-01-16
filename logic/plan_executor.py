"""Plan executor for safe action execution."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from logic.action_queue import Action

LOG = logging.getLogger("plan_executor")


class PlanExecutor:
    def execute(self, actions: Iterable[Action], client: object, cfg: object | None = None) -> None:
        for action in actions:
            normalized = self._normalize_action(action)
            if normalized is None:
                LOG.warning("[EXEC] skip action=%s (unable to normalize)", action)
                continue
            self._execute_with_retry(client, normalized, cfg)

    # Keep compatibility with older incremental executors
    def execute_next(self, actions: list[Action], index: int, client: object, cfg: object | None = None) -> bool:
        if index < 0 or index >= len(actions):
            return False
        normalized = self._normalize_action(actions[index])
        if normalized is None:
            LOG.warning("[EXEC] skip action=%s (unable to normalize)", actions[index])
            return False
        return self._execute_with_retry(client, normalized, cfg)

    @staticmethod
    def _normalize_action(action: object) -> Action | None:
        if isinstance(action, Action):
            return action
        if isinstance(action, dict):
            action_type = action.get("type")
            if not action_type:
                return None
            return Action(
                type=action_type,
                args=action.get("args", {}) or {},
                description=action.get("description", "") or "",
                retries=int(action.get("retries", 1) or 1),
                delay_ms=int(action.get("delay_ms", 80) or 80),
            )
        action_type = getattr(action, "type", None)
        if not action_type:
            return None
        return Action(
            type=action_type,
            args=getattr(action, "args", {}) or {},
            description=getattr(action, "description", "") or "",
            retries=int(getattr(action, "retries", 1) or 1),
            delay_ms=int(getattr(action, "delay_ms", 80) or 80),
        )

    def _execute_with_retry(self, client: object, action: Action, cfg: object | None = None) -> bool:
        attempts = max(1, int(getattr(action, "retries", 1)))
        delay_ms = int(getattr(action, "delay_ms", 120))

        for attempt in range(attempts):
            ok = self._execute_action(client, action)
            if ok:
                LOG.info("[EXEC] ok type=%s desc=%s", action.type, action.description)
                return True
            if attempt < attempts - 1:
                time.sleep(delay_ms / 1000)

        LOG.warning("[EXEC] fail type=%s desc=%s err=exhausted", action.type, action.description)
        return False

    def _execute_action(self, client: object, action: Action) -> bool:
        try:
            a = action.args or {}
            t = action.type

            if t == "wait_input":
                getattr(client, "wait_for_input_enabled")()
                return True

            if t in ("advance_phase", "move_phase"):
                phase = a.get("phase_enum") or a.get("phase")
                getattr(client, "move_phase")(phase)
                return True

            if t == "normal_summon":
                idx = a.get("index", a.get("hand_index"))
                pos = a.get("position", "attack")
                getattr(client, "normal_summon_monster")(idx, pos)
                return True

            if t == "special_summon_hand":
                idx = a.get("index", a.get("hand_index"))
                pos = a.get("position", "attack")
                fn = getattr(client, "special_summon_monster_from_hand", None)
                if fn is None:
                    return False
                # Some clients accept timeout_seconds; keep it optional.
                try:
                    fn(idx, pos, timeout_seconds=5)
                except TypeError:
                    fn(idx, pos)
                return True

            if t == "activate_hand":
                idx = a.get("index", a.get("hand_index"))
                getattr(client, "activate_monster_effect_from_hand")(idx)
                return True

            if t == "activate_field":
                pos = a.get("position", 0)
                getattr(client, "activate_monster_effect_from_field")(pos)
                return True

            if t == "activate_spell_hand":
                idx = a.get("index", a.get("hand_index"))
                pos = a.get("position", "face_up")
                getattr(client, "activate_spell_or_trap_from_hand")(idx, pos)
                return True

            if t == "set_spell_hand":
                idx = a.get("index", a.get("hand_index"))
                pos = a.get("position", "set")
                getattr(client, "set_spell_or_trap_from_hand")(idx, pos)
                return True

            if t in ("extra_summon", "extra_deck_summon"):
                name = a.get("name")
                positions = a.get("positions", ["attack"])
                getattr(client, "perform_extra_deck_summon")(name, positions)
                return True

            if t == "pass":
                # safest generic pass: attempt battle then end
                try:
                    getattr(client, "move_phase")("battle")
                    time.sleep(0.1)
                    getattr(client, "move_phase")("end")
                except Exception:
                    pass
                return True

            LOG.debug("Unknown action type=%s args=%s", t, a)
            return False

        except Exception as exc:
            LOG.warning("[EXEC] fail type=%s desc=%s err=%s", action.type, action.description, exc)
            return False
