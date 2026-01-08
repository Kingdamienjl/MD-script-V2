# MD-script-V2

## Dialog configuration

The duel dialog resolver is driven by environment variables so you can tune safety thresholds and delays without code changes:

- `BOT_DIALOG_MAX_CYCLES`: Maximum number of repeated dialog signatures before treating the dialog as stuck (default: `12`).
- `BOT_DIALOG_CLICK_DELAY_MS`: Delay in milliseconds between dialog interactions (default: `400`).
- `BOT_ACTION_DELAY_MS`: Delay in milliseconds between actions (default: `200`).
- `BOT_DUMP_DIR`: Directory to write dialog debug snapshots (default: `./bot_dumps`).
- `BOT_SCREENSHOT_ON_ERROR`: Enable screenshots on error if supported (default: `false`).
