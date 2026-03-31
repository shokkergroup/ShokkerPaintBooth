@echo off
REM ============================================
REM  Wake SPB Dev Agent — Trigger a heartbeat NOW
REM  Double-click to run the agent immediately
REM ============================================

echo [Shokker] Waking SPB Dev Agent...
echo [Shokker] The agent will read PRIORITIES.md, pick a task, and log to CHANGELOG.md
echo.

npx paperclipai heartbeat run --agent-id bd16f76b-cb32-4c72-a351-be7d981d1c2e --source on_demand --trigger manual

echo.
echo [Shokker] Heartbeat complete. Check CHANGELOG.md for what changed.
pause
