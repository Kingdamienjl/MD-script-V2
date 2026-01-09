"""Plan executor for safe action execution."""

from __future__ import annotations

import logging
import time
from typing import Iterable, Optional

LOG = logging.getLogger("plan_executor")


class PlanExecutor:
    def execute(self, actions: Iterable[object], client: object, cfg: Optional[object] = None) -> None:
        for action in actions:
            self._execute_with_retry(client, action, cfg=cfg)

    def execute_next(self, actions: list[object], index: int, client: object, cfg: Optional[object] = None) -> bool:
        if index < 0 or index >= len(actions):
            return False
        return self._execute_with_retry(client, actions[index], cfg=cfg)

    def _execute_with_retry(self, client: object, action: object, cfg: Optional[object] = None) -> bool:
        retries = int(getattr(action, "retries", 1) or 1)
        delay_ms = int(getattr(action, "delay_ms", 80) or 80)

        for attempt in range(retries):
            ok = self._execute_action(client, action)
            if ok:
                LOG.info("[EXEC] ok type=%s desc=%s", getattr(action, "type", "?"), getattr(action, "description", ""))
                time.sleep(float(getattr(cfg, "action_delay_s", 0.10)) if cfg else 0.10)
                return True

            if attempt < retries - 1:
                time.sleep(delay_ms / 1000.0)

        LOG.warning("[EXEC] fail type=%s desc=%s err=exhausted", getattr(action, "type", "?"), getattr(action, "description", ""))
        return False

    def _execute_action(self, client: object, action: object) -> bool:
        t = getattr(action, "type", "")
        args = getattr(action, "args", {}) or {}

        try:
            if t == "wait_input":
                getattr(client, "wait_for_input_enabled")()
                return True

            if t in ("move_phase", "advance_phase"):
                phase = args.get("phase_enum") or args.get("phase")
                getattr(client, "move_phase")(phase)
                return True

            if t == "pass":
                try:
                    getattr(client, "move_phase")("battle")
                    time.sleep(0.1)
                    getattr(client, "move_phase")("end")
                except Exception:
                    pass
                return True

            if t == "normal_summon":
                getattr(client, "normal_summon_monster")(args["index"], args.get("position", "attack"))
                return True

            if t == "special_summon_hand":
                fn = getattr(client, "special_summon_monster_from_hand")
                try:
                    fn(args["index"], args.get("position", "attack"), timeout_seconds=5)
                except TypeError:
                    fn(args["index"], args.get("position", "attack"))
                return True

            if t == "activate_hand":
                getattr(client, "activate_monster_effect_from_hand")(args["index"])
                return True

            if t == "activate_field":
                getattr(client, "activate_monster_effect_from_field")(args["position"])
                return True

            if t == "activate_spell_hand":
                getattr(client, "activate_spell_or_trap_from_hand")(args["index"], args.get("position", "face_up"))
                return True

            if t == "set_spell_hand":
                getattr(client, "set_spell_or_trap_from_hand")(args["index"], args.get("position", "set"))
                return True

            if t == "extra_summon":
                getattr(client, "perform_extra_deck_summon")(args["name"], args.get("positions", ["attack"]))
                return True

            LOG.debug("[EXEC] unknown action type=%s args=%s", t, args)
            return True

        except Exception as exc:
            LOG.warning("[EXEC] fail type=%s desc=%s err=%s", t, getattr(action, "description", ""), exc)
            return False
