"""Per-card handler stubs for the Swordsoul Tenyi ruleset."""

from __future__ import annotations

import logging

from logic.strategy_registry import Action

LOG = logging.getLogger("swordsoul_tenyi.handlers")


def _log_stub(name: str) -> None:
    LOG.debug("handler stub=%s", name)


def handle_moye(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("mo_ye")
    return []


def handle_longyuan(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("longyuan")
    return []


def handle_emergence(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("emergence")
    return []


def handle_taia(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("taia")
    return []


def handle_ecclesia(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("ecclesia")
    return []


def handle_ashuna(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("ashuna")
    return []


def handle_vishuda(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("vishuda")
    return []


def handle_adhara(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("adhara")
    return []


def handle_shthana(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("shthana")
    return []


def handle_blackout(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("blackout")
    return []


def handle_imperm(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("imperm")
    return []


def handle_called_by(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("called_by")
    return []


def handle_crossout(state: dict, profile: dict, client: object, cfg) -> list[Action]:
    _log_stub("crossout")
    return []
