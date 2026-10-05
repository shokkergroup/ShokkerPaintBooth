#!/usr/bin/env bash
# Overnight finish improvement loop — wakes every 15 minutes.
# Run: bash scripts/overnight_loop.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
INTERVAL_SEC=$((15 * 60))
echo "SPB overnight loop — every ${INTERVAL_SEC}s — worker: scripts/overnight_finish_worker.py"
python scripts/overnight_finish_worker.py || true
while true; do
  sleep "$INTERVAL_SEC"
  echo "AGENT_LOOP_TICK_overnight {\"prompt\":\"Run python scripts/overnight_finish_worker.py for next finish batch\"}"
  python scripts/overnight_finish_worker.py || true
done
