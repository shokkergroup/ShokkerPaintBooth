#!/usr/bin/env bash
# Arm the next SHOKK DROP agent wake (default 15m). Emits AGENT_LOOP_WAKE_shokk_drop for monitored shell.
set -euo pipefail
SEC="${SHOKK_DROP_LOOP_SEC:-900}"
PROMPT='SHOKK DROP 15m tick. Read docs/SHOKK_DROP_LOOP_LOG.md and docs/USER_IMPORTS_OVERNIGHT.md backlog — pick next unchecked item. Ship one improvement; append a dated line to SHOKK_DROP_LOOP_LOG.md; post a short summary in chat; run pytest tests/test_user_imports.py && npm run sync-runtime; mark backlog done; re-arm via scripts/shokk_drop_loop_arm.sh.'
sleep "$SEC"
printf 'AGENT_LOOP_WAKE_shokk_drop %s\n' "{\"prompt\":$(python -c "import json,sys; print(json.dumps(sys.argv[1]))" "$PROMPT")}"
