# Arm the next SHOKK DROP agent wake (default 15m). Emits AGENT_LOOP_WAKE_shokk_drop for monitored shell.
$ErrorActionPreference = 'Stop'
$sec = if ($env:SHOKK_DROP_LOOP_SEC) { [int]$env:SHOKK_DROP_LOOP_SEC } else { 900 }
$prompt = @'
SHOKK DROP 15m tick. Read docs/SHOKK_DROP_LOOP_LOG.md and docs/USER_IMPORTS_OVERNIGHT.md backlog — pick next unchecked item. Ship one improvement; append a dated line to SHOKK_DROP_LOOP_LOG.md; post a short summary in chat; run pytest tests/test_user_imports.py; npm run sync-runtime; mark backlog done; re-arm via scripts/shokk_drop_loop_arm.ps1 (Windows) or shokk_drop_loop_arm.sh (Git Bash).
'@

Start-Sleep -Seconds $sec
$line = python -c "import json,sys; print('AGENT_LOOP_WAKE_shokk_drop ' + json.dumps({'prompt': sys.argv[1]}))" $prompt
Write-Output $line
