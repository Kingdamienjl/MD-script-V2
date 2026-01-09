#!/usr/bin/env python3
"""Build Swordsoul Tenyi profile.json from a deck list text file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_DECKLISTS = [
    "swordsoul_decklist.txt",
    "A competitive Swordsoul Tenyi deck.txt",
]
DEFAULT_PROFILE = Path("logic") / "decks" / "swordsoul_tenyi" / "profile.json"

SECTION_HEADERS = {
    "main deck",
    "extra deck",
    "side deck",
    "monster",
    "monsters",
    "spell",
    "spells",
    "trap",
    "traps",
    "extra",
    "side",
}

COUNT_PREFIX = re.compile(r"^(?:x?\d+)\s*x?\s*(.+)$", re.IGNORECASE)
COUNT_SUFFIX = re.compile(r"^(.+?)\s+x?\d+$", re.IGNORECASE)


def _normalize_header(text: str) -> str:
    return re.sub(r"[^a-z ]", "", text.lower()).strip()


def parse_decklist(path: Path) -> list[str]:
    cards: list[str] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if _normalize_header(line) in SECTION_HEADERS:
            continue
        if set(line) <= {"-", "="}:
            continue
        line = line.split(" #", 1)[0].strip()
        if " (" in line:
            line = line.split(" (", 1)[0].strip()
        match = COUNT_PREFIX.match(line)
        if match:
            line = match.group(1).strip()
        else:
            match = COUNT_SUFFIX.match(line)
            if match:
                line = match.group(1).strip()
        if not line or not re.search(r"[A-Za-z]", line):
            continue
        if line not in seen:
            seen.add(line)
            cards.append(line)
    return cards


def resolve_decklists(decklists: list[str], repo_root: Path) -> list[Path]:
    if decklists:
        resolved = []
        for path in decklists:
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = repo_root / candidate
            resolved.append(candidate)
        return resolved
    candidates = [repo_root / name for name in DEFAULT_DECKLISTS]
    return [path for path in candidates if path.exists()]


def build_profile(decklists: list[Path], profile_path: Path) -> dict:
    dialog_priority: list[str] = []
    seen: set[str] = set()
    for decklist in decklists:
        for card in parse_decklist(decklist):
            if card not in seen:
                seen.add(card)
                dialog_priority.append(card)

    if not dialog_priority:
        raise ValueError("No card names parsed from decklist(s).")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["dialog_pick_priority"] = dialog_priority
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decklist",
        action="append",
        default=[],
        help="Decklist file path (can be provided multiple times).",
    )
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help="Path to the profile.json to update.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    decklists = resolve_decklists(args.decklist, repo_root)
    if not decklists:
        raise FileNotFoundError(
            "No decklist files found. Provide --decklist or add one of: "
            + ", ".join(DEFAULT_DECKLISTS)
        )

    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = repo_root / profile_path
    updated_profile = build_profile(decklists, profile_path)
    profile_path.write_text(json.dumps(updated_profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {profile_path} using {', '.join(str(p) for p in decklists)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
