# HERMES Recon Loop

This gives Ricky a simple DeepSeek V4 scout loop for SPB.

## What It Does

- Uses the existing Hermes/OpenRouter key when available.
- Calls OpenRouter with `deepseek/deepseek-v4-flash` by default.
- Runs as a Windows scheduled task every 15 minutes when started.
- Reads project context and writes idea briefs to `codex_recon_inbox`.
- Does not edit app source files.

## Buttons

- `START_HERMES_RECON.bat` starts the 15-minute loop in the background.
- `STOP_HERMES_RECON.bat` stops and removes the scheduled task.
- `STATUS_HERMES_RECON.bat` shows whether it is running and where the last brief went.
- `RUN_HERMES_RECON_ONCE.bat` creates one brief immediately.
- `EDIT_HERMES_RECON_MISSION.bat` opens the mission file in Notepad.
- `OPEN_HERMES_RECON_INBOX.bat` opens the folder where briefs are written.
- `OPEN_HERMES_RECON_LOG.bat` opens the low-level run log.

## How To Tell It What To Do

Double-click `EDIT_HERMES_RECON_MISSION.bat`, change the mission text, and save.
The next scheduled run will read `HERMES_RECON_MISSION.md`.

This recon setup is intentionally not an interactive console. It is a quiet
background scout. To verify it is working, double-click `STATUS_HERMES_RECON.bat`
or `OPEN_HERMES_RECON_INBOX.bat`.

## Changing Model Or Timing

Edit `tools/hermes_recon/config.json`.

Cheap default:

```json
"model": "deepseek/deepseek-v4-flash"
```

Higher quality DeepSeek V4 option:

```json
"model": "deepseek/deepseek-v4-pro"
```

Change the interval with:

```json
"interval_minutes": 15
```

## If The Key Is Missing

The runner checks these places:

1. `OPENROUTER_API_KEY` environment variable
2. `tools/hermes_recon/.env`
3. `~/.hermes/.env`
4. `~/.hermes/hermes-agent/.env`
5. `~/.hermes/hermes-agent/cli-config.yaml`

If needed, create `tools/hermes_recon/.env` containing:

```text
OPENROUTER_API_KEY=your-openrouter-key-here
```

That `.env` file is ignored by git.
