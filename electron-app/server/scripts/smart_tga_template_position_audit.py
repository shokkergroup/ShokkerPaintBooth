"""Apply a learned template map to immutable Smart TGA instances in shadow."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
from engine.spec_sculpt.decal_template_position import compute_template_position_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--panel-map", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    routes = json.loads(args.inspection.read_text(encoding="utf-8"))
    panel_map = json.loads(args.panel_map.read_text(encoding="utf-8"))
    counts = Counter()
    samples = []
    by_paint = []
    for route in routes:
        records = (
            route.get("route_adjudicator_shadow", {}).get("candidate_evidence", {})
            .get("decal_instances", {}).get("features", {}).get("records", ())
        )
        local = Counter()
        for record in records:
            if not record.get("mask_rle"):
                continue
            evidence = compute_template_position_evidence(
                record["bbox"], decode_instance_mask_rle(record["mask_rle"]),
                (1024, 1024), panel_map,
            )
            owners = set(record.get("proposed_owners") or ())
            counts["instances"] += 1
            local["instances"] += 1
            cue = None
            if "sponsors" in owners and evidence.best_number_fraction >= 0.50:
                cue = "sponsor_proposal_inside_number_block"
            elif (
                "numbers" in owners and evidence.best_number_fraction < 0.35
                and max(evidence.best_sponsor_fraction, evidence.best_mandatory_fraction) >= 0.45
            ):
                cue = "number_proposal_inside_nonnumber_block"
            if cue:
                counts[cue] += 1
                local[cue] += 1
                if len(samples) < 80:
                    samples.append({
                        "paint_label": route.get("paint_label"),
                        "instance_id": record.get("instance_id"),
                        "bbox": record.get("bbox"),
                        "proposed_owners": sorted(owners),
                        "cue": cue,
                        "best_number_fraction": evidence.best_number_fraction,
                        "best_sponsor_fraction": evidence.best_sponsor_fraction,
                        "best_mandatory_fraction": evidence.best_mandatory_fraction,
                    })
        by_paint.append({"paint_label": route.get("paint_label"), **dict(local)})
    report = {
        "schema": "smart-tga-template-position-audit-v1",
        "template": panel_map.get("template"),
        **{key: int(counts.get(key, 0)) for key in (
            "instances", "sponsor_proposal_inside_number_block",
            "number_proposal_inside_nonnumber_block",
        )},
        "paint_reports": by_paint,
        "samples": samples,
        "casts_votes": False,
        "ownership_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "schema", "template", "instances", "sponsor_proposal_inside_number_block",
        "number_proposal_inside_nonnumber_block", "casts_votes", "ownership_authority",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
