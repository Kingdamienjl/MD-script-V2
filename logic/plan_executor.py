"""Plan executor for safe action execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from logic.action_queue import Action
from logic.dialog_resolver import DialogResolver


@dataclass
class ExecutionResult:
    executed: int
    bailed_out: bool


class PlanExecutor:
    def __init__(self, dialog_resolver: DialogResolver) -> None:
        self.dialog_resolver = dialog_resolver

    def execute(self, client: object, actions: Iterable[Action], ctx: dict) -> ExecutionResult:
        executed = 0
        bailed_out = False
        actions_this_tick = 0
        actions_this_turn = int(ctx.get("actions_this_turn", 0))

        for action in actions:
            if actions_this_tick >= 2:
                break
            if actions_this_turn >= 6:
                break

            ok = self._execute_action(client, action)
            logging.info("[EXEC] action=%s %s", action.description, "ok" if ok else "fail")
            executed += 1
            actions_this_tick += 1
            actions_this_turn += 1

            getattr(client, "handle_unexpected_prompts", lambda: None)()
            result = self.dialog_resolver.resolve(client)
            if result == "bailout":
                bailed_out = True
                break

        ctx["actions_this_turn"] = actions_this_turn
        return ExecutionResult(executed=executed, bailed_out=bailed_out)

    def _execute_action(self, client: object, action: Action) -> bool:
        try:
            if action.type == "normal_summon":
                getattr(client, "normal_summon_from_hand", lambda _idx: None)(
                    action.args["hand_index"]
                )
                return True
            if action.type == "activate_hand_effect":
                getattr(client, "activate_effect_from_hand", lambda _idx: None)(
                    action.args["hand_index"]
                )
                return True
            if action.type == "activate_effect":
                getattr(client, "activate_effect_from_field", lambda _idx: None)(
                    action.args["field_index"]
                )
                return True
            if action.type == "special_summon":
                getattr(client, "special_summon_from_hand", lambda _idx: None)(
                    action.args["hand_index"]
                )
                return True
            if action.type == "set_spell_trap":
                getattr(client, "set_spell_trap_from_hand", lambda _idx: None)(
                    action.args["hand_index"]
                )
                return True
            if action.type == "extra_deck_summon":
                getattr(client, "perform_extra_deck_summon", lambda _name: None)(
                    action.args["name"]
                )
                return True
        except Exception:
            return False
        return False
