"""Promote only fully audited X LAB rows into the live picker scorecard."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SHIPPING = ROOT / "paint-booth-0-catalog-scorecard.js"
AUDITED = ROOT / "_x_lab_work" / "official_m7" / "scorecard_x_lab.js"
REPORT = ROOT / "_x_lab_work" / "official_m7" / "report.json"


def _load(path: Path) -> dict:
    source = path.read_text(encoding="utf-8", errors="strict")
    match = re.search(r"=\s*(\{.*\});", source, flags=re.S)
    if match is None:
        raise RuntimeError(f"could not parse scorecard: {path}")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def main() -> None:
    from engine.expansions.x_lab_2026 import RECIPES

    shipping, audited = _load(SHIPPING), _load(AUDITED)
    report = json.loads(REPORT.read_text(encoding="utf-8", errors="strict"))
    if report.get("failed"):
        raise SystemExit(f"X LAB M7 failures block promotion: {report['failed']}")
    keys = tuple("monolithic:" + recipe.fid for recipe in RECIPES)
    for key in keys:
        score = report.get("scores", {}).get(key)
        if not isinstance(score, (int, float)) or score < 85.0 or key not in audited:
            raise SystemExit(f"X LAB row lacks passing M7 evidence: {key}")
        quality = int(round(float(score)))
        row = dict(audited[key])
        row.update({
            "overallQuality": quality, "paintQuality": quality, "specQuality": quality,
            "priority": "PASS", "status": "OK", "reasonFlags": "",
            "category": "X LAB", "m7Composite": float(score),
            "m7Tier": "keeper", "m7Intent": "full", "m7Pass85": True,
        })
        shipping[key] = row
    header = """// ============================================================
// PAINT-BOOTH-0-CATALOG-SCORECARD.JS - Compact active scorecard
// ============================================================
// Generated from measured render/audit signals used by picker rankings.
// SPB-105 X-LAB-1: 30 native-2048 materials promoted after isolated M7 >=85.
// ============================================================
"""
    SHIPPING.write_text(
        header + "const CATALOG_SCORECARD_METRICS = " + json.dumps(shipping, indent=2, ensure_ascii=False)
        + ";\n\nif (typeof window !== 'undefined') window.CATALOG_SCORECARD_METRICS = CATALOG_SCORECARD_METRICS;\n",
        encoding="utf-8",
    )
    print(f"promoted {len(keys)} X LAB rows; min M7={min(report['scores'][key] for key in keys):.1f}")


if __name__ == "__main__":
    main()
