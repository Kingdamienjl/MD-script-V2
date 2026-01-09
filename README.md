# MD-script-V2

## Dialog and planning configuration

The bot configuration is driven by environment variables so you can tune dialog safety and planning behavior without code changes.

### Adding a new deck

1) Copy `logic/decks/_template` to `logic/decks/<newdeck>`.
2) Edit `logic/decks/<newdeck>/profile.json` to match your deck list.
3) Implement `logic/rulesets/<newdeck>/strategy.py` exporting `get_strategy(profile, strategy_name)`.
4) Set `BOT_RULESET=<newdeck>` when launching the bot.

### Profile location and strict filtering

Profiles live at `logic/decks/<deck>/profile.json` (preferred) or the legacy `logic/deck_profile.json`. When `BOT_STRICT_PROFILE=1`, the bot will only select card names found in the active profile and will log `[PROFILE] blocked unknown card name=<name>` for any unknown names. Add new card names to the appropriate profile list to make them eligible for selection.

### Regenerating the Swordsoul Tenyi profile

Run the helper script to rebuild `logic/decks/swordsoul_tenyi/profile.json` from the decklist text file:

```
python tools/build_profile_from_decklist.py
```

By default, it looks for `swordsoul_decklist.txt` (preferred) or `A competitive Swordsoul Tenyi deck.txt` at the repo root. You can pass `--decklist path/to/file.txt` to target a specific list.

### Environment variables

- `BOT_ACTION_DELAY_MS`: Delay in milliseconds between actions (default: `120`).
- `BOT_DIALOG_CLICK_DELAY_MS`: Delay in milliseconds between dialog interactions (default: `120`).
- `BOT_DIALOG_MAX_CYCLES`: Maximum repeated dialog signatures before treating the dialog as stuck (default: `12`).
- `BOT_DUMP_DIR`: Directory to write dialog debug snapshots (default: `artifacts`).
- `BOT_MAX_ACTIONS_PER_TICK`: Maximum actions executed per tick (default: `2`).
- `BOT_PROFILE_PATH`: Legacy path to the deck profile JSON (defaults to `logic/decks/swordsoul_tenyi/profile.json` if present, otherwise `logic/deck_profile.json`).
- `BOT_STRICT_PROFILE`: If true, only use card names listed in the profile (default: `1`).
- `BOT_DECK`: Deck folder name under `BOT_DECKS_DIR` (default: `swordsoul_tenyi`).
- `BOT_DECKS_DIR`: Base directory for deck profiles/strategies (default: `logic/decks`).
- `BOT_STRATEGY`: Strategy variant name (default: `default`).
