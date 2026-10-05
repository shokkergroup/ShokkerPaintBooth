"""Mark patterns as "agent-addressed" in SPB_AUDIT.json.

Pairs with the SPB_AUDIT.html workbook: once the owner clicks SUBMIT on a
card, the card hides. The agent (this script) marks `agent_addressed_at`
on patterns it has just re-worked, which re-surfaces those cards at the
FRONT of the queue with a "🔁 AGENT UPDATED — RE-REVIEW" badge.

Usage (call at end of every tick after committing changes):

    python scripts/mark_audit_addressed.py cc_spot_polish spec_stress_fractures magnetic_field

Reads + writes SPB_AUDIT.json at project root. If an entry does not yet
exist (owner never submitted), creates one — that way agent work on
unsubmitted patterns still shows owner the badge so they know to
re-rate.

Server (scripts/audit_server.py) sees the file change and the running
SPB_AUDIT.html polls /state every 8s, so the owner's browser updates
automatically — no manual refresh.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON = ROOT / "SPB_AUDIT.json"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: mark_audit_addressed.py <pattern_id> [<pattern_id> ...]")
        return 2
    # Owner browser writes ISO with Z suffix (UTC). Use UTC with Z so string
    # compare works correctly across timezones.
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    if AUDIT_JSON.exists():
        try:
            data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[mark_audit_addressed] bad JSON ({e}); starting fresh")
            data = {}
    else:
        data = {}
    data.setdefault("generated", now)
    entries = data.setdefault("entries", {})

    touched = []
    for pid in argv:
        e = entries.setdefault(pid, {
            "verdict": None,
            "reasons": [],
            "comment": "",
            "submitted_at": None,
            "agent_addressed_at": None,
            "score": None,
            "tier": None,
        })
        e["agent_addressed_at"] = now
        touched.append(pid)

    # Atomic write
    tmp = AUDIT_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, AUDIT_JSON)

    print(f"[mark_audit_addressed] {now}  agent_addressed_at on: {', '.join(touched)}")
    print(f"  -> {AUDIT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
