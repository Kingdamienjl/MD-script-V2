# MD-script-V2

## Dialog and planning configuration

The bot configuration is driven by environment variables so you can tune dialog safety and planning behavior without code changes.

### Adding a new deck

1) Copy `logic/decks/_template` to `logic/decks/<newdeck>`.
2) Edit `logic/decks/<newdeck>/profile.json` to match your deck list.
3) Implement `logic/decks/<newdeck>/strategy.py` exporting `get_strategy(profile, strategy_name)`.
4) Set `BOT_DECK=<newdeck>` when launching the bot.

### Environment variables

- `BOT_ACTION_DELAY_MS`: Delay in milliseconds between actions (default: `120`).
- `BOT_DIALOG_CLICK_DELAY_MS`: Delay in milliseconds between dialog interactions (default: `120`).
- `BOT_DIALOG_MAX_CYCLES`: Maximum repeated dialog signatures before treating the dialog as stuck (default: `12`).
- `BOT_DUMP_DIR`: Directory to write dialog debug snapshots (default: `artifacts`).
- `BOT_MAX_ACTIONS_PER_TICK`: Maximum actions executed per tick (default: `2`).
- `BOT_PROFILE_PATH`: Legacy path to the deck profile JSON (default: `logic/deck_profile.json`).
- `BOT_STRICT_PROFILE`: If true, only use card names listed in the profile (default: `1`).
- `BOT_DECK`: Deck folder name under `BOT_DECKS_DIR` (default: `swordsoul_tenyi`).
- `BOT_DECKS_DIR`: Base directory for deck profiles/strategies (default: `logic/decks`).
- `BOT_STRATEGY`: Strategy variant name (default: `default`).
