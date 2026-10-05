"""Retire current SPB_RATE_10 visible failures pending reference-image rebuild.

This does not mark anything KEEP and does not delete renderer code. It records
the weak visible queue in `_rate10_thumbs/reference_rebuild_retired.json` so
`generate_audit_queue.py` hides those IDs while Ricky sends replacement images
in 10-at-a-time batches.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "_rate10_thumbs" / "audit_queue.json"
OUT = ROOT / "_rate10_thumbs" / "reference_rebuild_retired.json"

PRESERVE_IDS = {
    "viper_pit_hex",
    "wave_ripple",
    "samhain_ritual",
    "ouija_mystic",
    "stardust_fine",
    "spec_terrain_erosion",
    "spec_stress_fractures",
    "spec_snake_scales",
    "spec_liquid_metal",
    "spec_fresnel_gradient",
}


def main() -> int:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    visible = queue.get("patterns", [])
    retired = [p for p in visible if p.get("id") not in PRESERVE_IDS]
    payload = {
        "schema": 1,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "Hide old RATE10 visible finishes pending owner-supplied reference-image replacements; KEEP items are not included.",
        "preserved_reference_ids": sorted(PRESERVE_IDS),
        "source_totals_before": queue.get("totals", {}),
        "retired_count": len(retired),
        "retired_ids": [p["id"] for p in retired],
        "retired_patterns": retired,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"visible before: {len(visible)}")
    print(f"preserved reference visible: {len(visible) - len(retired)}")
    print(f"retired pending reference rebuild: {len(retired)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
