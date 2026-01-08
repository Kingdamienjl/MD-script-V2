"""Strategy registry and loader."""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path

from jduel_bot.config import BotConfig
from logic.action_queue import Action
from logic.profile import load_profile
from logic.strategy_base import Strategy


@dataclass(frozen=True)
class NoopStrategy:
    name: str = "noop"
    deck_name: str = "unknown"

    def plan_main_phase_1(self, state, client: object, cfg: BotConfig) -> list[Action]:
        return [
            Action(
                type="advance_phase",
                args={"phase": "battle"},
                description="Advance phase (noop strategy)",
            )
        ]

    def on_dialog(self, dialog_cards, state, client: object, cfg: BotConfig):
        return None


def load_profile_for_deck(deck_dir: str, fallback_path: str) -> dict:
    profile_path = Path(deck_dir) / "profile.json"
    if profile_path.exists():
        return load_profile(str(profile_path))
    fallback = Path(fallback_path)
    if fallback.exists():
        logging.warning(
            "Profile missing in %s; falling back to legacy profile at %s",
            deck_dir,
            fallback,
        )
        return load_profile(str(fallback))
    raise FileNotFoundError(f"Missing profile.json in {deck_dir} and legacy profile")


def _import_strategy_module(deck_dir: Path) -> object:
    module_path = deck_dir / "strategy.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Missing strategy.py in {deck_dir}")
    spec = importlib.util.spec_from_file_location(
        f"logic.decks.{deck_dir.name}.strategy", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import strategy module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_strategy(deck_name: str, strategy_name: str, decks_dir: str, profile_path: str) -> Strategy:
    deck_dir = Path(decks_dir) / deck_name
    try:
        profile = load_profile_for_deck(str(deck_dir), profile_path)
        module = _import_strategy_module(deck_dir)
        get_strategy = getattr(module, "get_strategy", None)
        if get_strategy is None:
            raise AttributeError("strategy.py missing get_strategy(profile, strategy_name)")
        strategy = get_strategy(profile, strategy_name)
        return strategy
    except Exception as exc:
        logging.error(
            "Failed to load strategy deck=%s strategy=%s: %s",
            deck_name,
            strategy_name,
            exc,
        )
        return NoopStrategy()
