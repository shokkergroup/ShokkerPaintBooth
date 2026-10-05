"""Consolidate reviewed missed-instance probes into a durable candidate bank.

The bank contains immutable raw-instance features plus human review truth.  It
is offline evidence only: it never casts votes, adds pixels, or grants runtime
ownership.  Duplicate review/candidate pairs are collapsed deterministically.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


def _review_target(record: Mapping[str, Any]) -> str:
    explicit = str(record.get("review_target_layer") or "")
    if explicit:
        return explicit
    family = str(record.get("family_id") or "").split(":", 1)[0]
    return {"number": "numbers", "sponsor": "sponsors"}.get(family, family or "uncertain")


def build_bank(probes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    reviewed_count = 0
    for probe in probes:
        if probe.get("casts_votes") or probe.get("ownership_authority") or probe.get("adds_pixels"):
            raise ValueError("candidate probe claimed runtime authority")
        reviewed_count += int(probe.get("reviewed_instance_count") or 0)
        for record in probe.get("records") or ():
            instance_id = str(record.get("best_instance_id") or "")
            features = dict(record.get("best_instance_features") or {})
            if not instance_id or not features:
                continue
            key = (
                str(record.get("paint_label") or ""),
                str(record.get("family_id") or ""),
                str(record.get("copy") or record.get("review_id") or ""),
                instance_id,
            )
            rows[key] = {
                "paint_label": key[0], "family_id": key[1], "copy": key[2],
                "instance_id": instance_id, "review_target_layer": _review_target(record),
                "candidate_status": record.get("status"),
                "best_review_coverage": record.get("best_review_coverage"),
                "best_candidate_coverage": record.get("best_candidate_coverage"),
                "best_iou": record.get("best_iou"),
                "proposed_owners": list(record.get("best_proposed_owners") or ()),
                "source_stages": list(record.get("best_source_stages") or ()),
                "sources": list(record.get("best_sources") or ()),
                "merge_reasons": list(record.get("best_merge_reasons") or ()),
                "features": features,
            }
    reviewed = [rows[key] for key in sorted(rows)]
    return {
        "schema": "smart-tga-reviewed-candidate-bank-v1",
        "probe_count": len(probes), "reviewed_region_count": reviewed_count,
        "reviewed_candidate_count": len(reviewed),
        "class_counts": dict(sorted(Counter(row["review_target_layer"] for row in reviewed).items())),
        "status_counts": dict(sorted(Counter(str(row["candidate_status"]) for row in reviewed).items())),
        "owner_path_counts": dict(sorted(Counter(
            "+".join(sorted(row["proposed_owners"])) or "none" for row in reviewed
        ).items())),
        "source_stage_counts": dict(sorted(Counter(
            stage for row in reviewed for stage in row["source_stages"]
        ).items())),
        "reviewed_candidates": reviewed,
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    probes = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.probe]
    bank = build_bank(probes)
    Path(args.output).write_text(json.dumps(bank, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in bank.items() if key != "reviewed_candidates"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
