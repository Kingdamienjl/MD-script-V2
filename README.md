# MD-script-V2

## Dialog and planning configuration

The bot configuration is driven by environment variables so you can tune dialog safety and planning behavior without code changes. Edit `logic/deck_profile.json` to match your deck list, or point to a different profile with `BOT_PROFILE_PATH`.

- `BOT_ACTION_DELAY_MS`: Delay in milliseconds between actions (default: `120`).
- `BOT_DIALOG_CLICK_DELAY_MS`: Delay in milliseconds between dialog interactions (default: `120`).
- `BOT_DIALOG_MAX_CYCLES`: Maximum repeated dialog signatures before treating the dialog as stuck (default: `12`).
- `BOT_DUMP_DIR`: Directory to write dialog debug snapshots (default: `artifacts`).
- `BOT_MAX_ACTIONS_PER_TICK`: Maximum actions executed per tick (default: `2`).
- `BOT_PROFILE_PATH`: Path to the deck profile JSON (default: `logic/deck_profile.json`).
- `BOT_STRICT_PROFILE`: If true, only use card names listed in the profile (default: `1`).
