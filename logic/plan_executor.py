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
            self._execute_with_retry(client, action)

    def _execute_with_retry(self, client: object, action: Action) -> None:
        attempts = max(1, action.retries)
        for attempt in range(attempts):
            ok = self._execute_action(client, action)
            if ok:
                LOG.info("[EXEC] ok type=%s desc=%s", action.type, action.description)
                return
            if attempt < attempts - 1:
                time.sleep(action.delay_ms / 1000)
        LOG.warning("[EXEC] fail type=%s desc=%s err=exhausted", action.type, action.description)

    def _execute_action(self, client: object, action: Action) -> bool:
        try:
            if action.type == "normal_summon":
                client.normal_summon_monster(action.args["index"], action.args["position"])
                return True
            if action.type == "special_summon_hand":
                client.special_summon_monster_from_hand(
                    action.args["index"],
                    action.args["position"],
                    timeout_seconds=5,
                )
                return True
            if action.type == "activate_hand":
                client.activate_monster_effect_from_hand(action.args["index"])
                return True
            if action.type == "activate_field":
                client.activate_monster_effect_from_field(action.args["position"])
                return True
            if action.type == "activate_spell_hand":
                client.activate_spell_or_trap_from_hand(action.args["index"], action.args["position"])
                return True
            if action.type == "set_spell_hand":
                client.set_spell_or_trap_from_hand(action.args["index"], action.args["position"])
                return True
            if action.type == "extra_summon":
                client.perform_extra_deck_summon(action.args["name"], action.args["positions"])
                return True
            if action.type == "advance_phase":
                client.move_phase(action.args["phase_enum"])
                return True
        except Exception as exc:
            LOG.warning(
                "[EXEC] fail type=%s desc=%s err=%s",
                action.type,
                action.description,
                exc,
            )
        return False
