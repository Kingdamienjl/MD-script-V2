"""
Strategy registry and loader.

We load a deck strategy from:
  logic/decks/<deck_name>/strategy.py

That module MUST expose:
  get_strategy(profile: dict, strategy_name: str) -> object

The returned object is expected to implement:
  plan_main_phase_1(state: dict, client: object, cfg: BotConfig) -> list[Action]
  on_dialog(dialog_cards: list[str], state: dict, client: object, cfg: BotConfig) -> CardSelection|None (optional)

If anything fails, we fall back to a "noop" strategy.
"""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Protocol

from logic.profile import load_profile

LOG = logging.getLogger("strategy_registry")

try:
    from jduel_bot.config import BotConfig  # type: ignore
except Exception:  # pragma: no cover
    BotConfig = Any  # type: ignore


@dataclass(frozen=True)
class Action:
    type: str
    args: dict = field(default_factory=dict)
    description: str = ""


class StrategyLike(Protocol):
    def plan_main_phase_1(
        self, state: dict, hand: list, client: object, cfg: BotConfig
    ) -> List[Action]: ...
    def on_dialog(self, dialog_cards: list[str], state: dict, client: object, cfg: BotConfig): ...


@dataclass(frozen=True)
class NoopStrategy:
    name: str = "noop"
    deck_name: str = "unknown"

    def plan_main_phase_1(self, state: dict, hand: list, client: object, cfg: BotConfig) -> List[Action]:
        return [Action(type="pass", description="Noop strategy -> pass")]

    def on_dialog(self, dialog_cards, state, client: object, cfg: BotConfig):
        return None


def load_profile_for_deck(deck_dir: str, fallback_path: str) -> dict:
    profile_path = Path(deck_dir) / "profile.json"
    if profile_path.exists():
        return load_profile(str(profile_path))
    fallback = Path(fallback_path)
    if fallback.exists():
        LOG.warning("Profile missing in %s; falling back to legacy profile at %s", deck_dir, fallback)
        return load_profile(str(fallback))
    raise FileNotFoundError(f"Missing profile.json in {deck_dir} and legacy profile")


def _import_strategy_module(module_path: Path, module_name: str) -> object:
    if not module_path.exists():
        raise FileNotFoundError(f"Missing strategy.py in {module_path.parent}")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import strategy module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_strategy(deck_name: str, strategy_name: str, decks_dir: str, profile_path: str) -> StrategyLike:
    deck_dir = Path(decks_dir) / deck_name
    ruleset_dir = Path("logic") / "rulesets" / deck_name
    try:
        profile = load_profile_for_deck(str(deck_dir), profile_path)
        module_path = deck_dir / "strategy.py"
        module_name = f"logic.decks.{deck_dir.name}.strategy"
        if not module_path.exists():
            module_path = ruleset_dir / "strategy.py"
            module_name = f"logic.rulesets.{deck_name}.strategy"
        module = _import_strategy_module(module_path, module_name)
        get_strategy = getattr(module, "get_strategy", None)
        if get_strategy is None:
            raise AttributeError("strategy.py missing get_strategy(profile, strategy_name)")
        return get_strategy(profile, strategy_name)
    except Exception as exc:
        LOG.error("Failed to load strategy deck=%s strategy=%s: %s", deck_name, strategy_name, exc)
        return NoopStrategy()
