"""Promote the audited 25-row Neon v4 scorecard slice into the live catalog.

The isolated workbook run is immutable evidence. This script copies only its
25 measured rows into the current shipping scorecard and changes lifecycle
labels; every unrelated catalog row stays sourced from the current live file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SHIPPING = ROOT / "paint-booth-0-catalog-scorecard.js"
AUDITED = ROOT / "_neon_v4_work" / "official_m7" / "scorecard_neon_v4.js"
REPORT = ROOT / "_neon_v4_work" / "official_m7" / "report.json"
BASE_IDS = {
    "neon_blacklight", "neon_cyber_yellow", "neon_dual_glow", "neon_electric_blue",
    "neon_ice_white", "neon_orange_hazard", "neon_pink_blaze", "neon_rainbow_tube",
    "neon_red_alert", "neon_toxic_green",
}


def _keys() -> tuple[str, ...]:
    from engine.expansions.neon_underground_v4.catalog import ORDER
    return tuple(("base:" if finish_id in BASE_IDS else "monolithic:") + finish_id
                 for finish_id in ORDER)


def _load(path: Path) -> dict:
    source = path.read_text(encoding="utf-8", errors="strict")
    match = re.search(r"=\s*(\{.*\});", source, flags=re.S)
    if match is None:
        raise RuntimeError(f"could not parse scorecard: {path}")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def main() -> None:
    shipping = _load(SHIPPING)
    audited = _load(AUDITED)
    official = json.loads(REPORT.read_text(encoding="utf-8", errors="strict"))
    if not official.get("all_pass_85"):
        raise SystemExit("official Neon v4 M7 report is not all-pass")
    keys = _keys()
    missing = [key for key in keys if key not in audited]
    if missing:
        raise SystemExit(f"audited Neon rows missing: {missing}")

    for key in keys:
        proof = official["byFinish"].get(key)
        if not proof or not proof.get("pass_85"):
            raise SystemExit(f"Neon v4 row failed ship bar: {key}")
        composite = float(proof["composite"])
        legacy_quality = int(round(composite))
        row = dict(audited[key])
        # The live picker still consumes these three legacy quality fields
        # independently. The isolated v4 scorecard intentionally inherited its
        # template fields, so promote the official M7 result into all three and
        # retain the full proof alongside them for auditability.
        row.update({
            "overallQuality": legacy_quality,
            "paintQuality": legacy_quality,
            "specQuality": legacy_quality,
            "priority": "PASS",
            "status": "OK",
            "reasonFlags": "",
            "category": "Neon",
            "m7Composite": composite,
            "m7Tier": proof.get("tier"),
            "m7Intent": proof.get("intent"),
            "m7Components": proof.get("components"),
            "m7Pass85": True,
        })
        shipping[key] = row

    header = """// ============================================================
// PAINT-BOOTH-0-CATALOG-SCORECARD.JS - Compact active scorecard
// ============================================================
// Generated from measured render/audit signals used by picker rankings.
// SPB-105 NU-V4-LIVE-1: 25 Neon v4 rows promoted from their official isolated
// workbook run; owner-eye/full-canvas contact remains the governing art gate.
// ============================================================
"""
    payload = json.dumps(shipping, indent=2, ensure_ascii=False)
    SHIPPING.write_text(
        header
        + "const CATALOG_SCORECARD_METRICS = " + payload + ";\n\n"
        + "if (typeof window !== 'undefined') window.CATALOG_SCORECARD_METRICS = CATALOG_SCORECARD_METRICS;\n",
        encoding="utf-8",
    )
    print(f"promoted {len(keys)} Neon v4 rows into {SHIPPING}")


if __name__ == "__main__":
    main()
