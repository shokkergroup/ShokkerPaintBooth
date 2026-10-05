"""Audit immutable foreground subinstances over real Smart TGA route records."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
from engine.spec_sculpt.decal_subinstances import derive_intrinsic_subinstances


def audit_records(records: list[dict]) -> dict:
    paint_reports = []
    totals = Counter()
    hypothesis_counts = Counter()
    fractions = []
    for route in records:
        source = np.asarray(Image.open(route["source_1024"]).convert("RGB"))
        components = (
            route.get("route_adjudicator_shadow", {})
            .get("candidate_evidence", {})
            .get("decal_instances", {})
            .get("features", {})
            .get("records", ())
        )
        local = Counter()
        for record in components:
            encoded = record.get("mask_rle")
            if not encoded:
                continue
            x, y, width, height = [int(value) for value in record["bbox"]]
            parent = decode_instance_mask_rle(encoded)
            crop = source[y:y + height, x:x + width]
            totals["parents"] += 1
            local["parents"] += 1
            items = derive_intrinsic_subinstances(crop, parent)
            if items:
                totals["parents_with_subinstances"] += 1
                local["parents_with_subinstances"] += 1
            for item in items:
                totals["subinstances"] += 1
                local["subinstances"] += 1
                if item.component_count >= 2:
                    totals["assembled_subinstances"] += 1
                    local["assembled_subinstances"] += 1
                if np.any(item.local_mask & ~parent):
                    totals["added_pixel_violations"] += 1
                if item.area >= int(np.count_nonzero(parent)):
                    totals["strict_subset_violations"] += 1
                hypothesis_counts[item.hypothesis.split(":", 1)[0]] += 1
                fractions.append(float(item.parent_fraction))
        paint_reports.append({"paint_label": route.get("paint_label"), **dict(local)})
    count_fields = {
        key: int(totals.get(key, 0))
        for key in (
            "parents", "parents_with_subinstances", "subinstances",
            "assembled_subinstances", "added_pixel_violations",
            "strict_subset_violations",
        )
    }
    return {
        "schema": "smart-tga-intrinsic-subinstance-audit-v1",
        **count_fields,
        "hypothesis_role_counts": dict(sorted(hypothesis_counts.items())),
        "parent_fraction_percentiles": {
            str(percentile): round(float(np.percentile(fractions, percentile)), 6)
            for percentile in (10, 25, 50, 75, 90)
        } if fractions else {},
        "paint_reports": paint_reports,
        "casts_votes": False,
        "ownership_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    records = json.loads(args.inspection.read_text(encoding="utf-8"))
    report = audit_records(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report.get(key) for key in (
        "schema", "parents", "parents_with_subinstances", "subinstances",
        "assembled_subinstances", "added_pixel_violations",
        "strict_subset_violations", "casts_votes", "ownership_authority",
    )}, indent=2))
    return 0 if not report.get("added_pixel_violations") and not report.get("strict_subset_violations") else 2


if __name__ == "__main__":
    raise SystemExit(main())
