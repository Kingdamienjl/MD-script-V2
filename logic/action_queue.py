"""Action queue for executing planned moves."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Iterable, List

from jduel_bot.config import BotConfig
from logic.state_manager import TurnCooldowns


@dataclass(frozen=True)
class Action:
    type: str
    args: dict[str, Any]
    description: str


class ActionQueue:
    def __init__(self) -> None:
        self._queue: List[Action] = []

    def push(self, actions: Iterable[Action]) -> None:
        self._queue.extend(actions)

    def pop(self) -> Action | None:
        if not self._queue:
            return None
        return self._queue.pop(0)

    def execute(self, client: object, cfg: BotConfig, dialog_resolver) -> None:
        actions_executed = 0
        while actions_executed < min(3, cfg.max_actions_per_tick):
            action = self.pop()
            if action is None:
                return
            ok = self._execute_action(client, action)
            logging.info("[EXEC] action=%s %s", action.description, "ok" if ok else "fail")
            actions_executed += 1

            getattr(client, "handle_unexpected_prompts", lambda: None)()
            if getattr(client, "is_inputting", lambda: False)():
                dialog_resolver.resolve(client)
                return

            getattr(client, "wait_for_input_enabled", lambda: None)()
            time.sleep(cfg.action_delay_ms / 1000)
            if getattr(client, "is_inputting", lambda: False)():
                dialog_resolver.resolve(client)
                return

    def _execute_action(self, client: object, action: Action) -> bool:
        cooldowns = getattr(client, "turn_cooldowns", None)
        try:
            if "card_name" in action.args and hasattr(client, "state"):
                try:
                    client.state.last_used_card_name = action.args["card_name"]
                except Exception:
                    pass
            if isinstance(cooldowns, TurnCooldowns):
                self._update_cooldowns(cooldowns, action)
            if action.type == "normal_summon":
                getattr(client, "normal_summon_from_hand", lambda _idx: None)(
                    action.args["hand_index"]
                )
                return True
            if action.type == "special_summon":
                getattr(client, "special_summon_from_hand", lambda _idx: None)(
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
            if action.type == "extra_deck_summon":
                getattr(client, "perform_extra_deck_summon", lambda _name: None)(
                    action.args["name"]
                )
                return True
            if action.type == "set_spell_trap":
                getattr(client, "set_spell_trap_from_hand", lambda _idx: None)(
                    action.args["hand_index"]
                )
                return True
            if action.type == "advance_phase":
                getattr(client, "advance_phase", lambda _phase: None)(
                    action.args["phase"]
                )
                return True
        except Exception:
            return False
        return False

    def _update_cooldowns(self, cooldowns: TurnCooldowns, action: Action) -> None:
        if action.type == "normal_summon":
            cooldowns.normal_summon_attempts += 1
        elif action.type == "special_summon" and action.args.get("card_name") == "Swordsoul Strategist Longyuan":
            cooldowns.longyuan_attempts += 1
        elif action.type == "activate_effect":
            if action.args.get("card_name") == "Swordsoul of Mo Ye":
                cooldowns.mo_ye_effect_attempts += 1
            if action.args.get("card_name") == "Swordsoul of Taia":
                cooldowns.taia_effect_attempts += 1
        elif action.type == "extra_deck_summon":
            cooldowns.extra_deck_attempts += 1
