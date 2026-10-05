"""Leave-one-out acceptance evaluation for reviewed Smart TGA decal families."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.spec_sculpt.decal_embeddings import EmbeddingReference, query_embedding_library
from scripts.smart_tga_embedding_library import _crop
from engine.spec_sculpt.decal_embeddings import embed_decal


SCHEMA = "smart-tga-reviewed-embedding-holdout-v1"


def evaluate_holdouts(
    entries: Sequence[dict[str, Any]],
    *,
    min_similarity: float = 0.84,
    ambiguity_margin: float = 0.04,
    min_family_support: int = 2,
    include_palette_roles: bool = False,
    include_foreground_subinstances: bool = False,
) -> dict[str, Any]:
    embedded = []
    for entry in entries:
        crop, mask = _crop(entry)
        embedded.append((entry, embed_decal(
            crop, mask, include_palette_roles=include_palette_roles,
            include_foreground_subinstances=include_foreground_subinstances,
        )))
    references = [
        EmbeddingReference(
            reference_id=str(entry["id"]),
            family_id=str(entry["family_id"]),
            reviewed_owner=str(entry["reviewed_owner"]),
            review_label=str(entry.get("review_label") or "reviewed_decal"),
            source=str(entry.get("source_image") or ""),
            bbox=tuple(int(value) for value in entry["bbox"]),
            embedding=embedding,
        )
        for entry, embedding in embedded
    ]
    family_counts: dict[str, int] = {}
    family_paints: dict[str, set[str]] = {}
    for entry, _embedding in embedded:
        family = str(entry["family_id"])
        family_counts[family] = family_counts.get(family, 0) + 1
        family_paints.setdefault(family, set()).add(str(entry.get("paint_label") or ""))
    positives = []
    negatives = []
    for entry, embedding in embedded:
        family = str(entry["family_id"])
        if family_counts.get(family, 0) >= int(min_family_support) + 1:
            result = query_embedding_library(
                embedding,
                [item for item in references if item.reference_id != str(entry["id"])],
                min_similarity=min_similarity,
                ambiguity_margin=ambiguity_margin,
                min_family_support=min_family_support,
            )
            positives.append({
                "id": entry["id"],
                "family_id": family,
                "passed": result.status == "corroborated" and result.family_id == family,
                "distinct_paints_in_family": len(family_paints.get(family, set()) - {""}),
                **result.__dict__,
            })
        other_references = [item for item in references if item.family_id != family]
        result = query_embedding_library(
            embedding,
            other_references,
            min_similarity=min_similarity,
            ambiguity_margin=ambiguity_margin,
            min_family_support=min_family_support,
        )
        negatives.append({
            "id": entry["id"],
            "excluded_family_id": family,
            "passed": result.status == "abstained",
            **result.__dict__,
        })
    eligible = {
        family: count for family, count in family_counts.items()
        if count >= int(min_family_support) + 1
    }
    return {
        "schema": SCHEMA,
        "family_counts": dict(sorted(family_counts.items())),
        "eligible_positive_families": dict(sorted(eligible.items())),
        "cross_paint_positive_families": sorted(
            family for family in eligible if len(family_paints.get(family, set()) - {""}) >= 2
        ),
        "positive_trials": len(positives),
        "positive_passed": sum(item["passed"] for item in positives),
        "negative_trials": len(negatives),
        "negative_passed": sum(item["passed"] for item in negatives),
        "all_passed": all(item["passed"] for item in positives + negatives),
        "min_similarity": min_similarity,
        "ambiguity_margin": ambiguity_margin,
        "min_family_support": min_family_support,
        "include_palette_roles": include_palette_roles,
        "include_foreground_subinstances": include_foreground_subinstances,
        "casts_votes": False,
        "ownership_authority": False,
        "positive_results": positives,
        "negative_results": negatives,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-similarity", type=float, default=0.84)
    parser.add_argument("--ambiguity-margin", type=float, default=0.04)
    parser.add_argument("--min-family-support", type=int, default=2)
    parser.add_argument("--palette-roles", action="store_true")
    parser.add_argument("--foreground-subinstances", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = evaluate_holdouts(
        manifest.get("entries") or (),
        min_similarity=args.min_similarity,
        ambiguity_margin=args.ambiguity_margin,
        min_family_support=args.min_family_support,
        include_palette_roles=args.palette_roles,
        include_foreground_subinstances=args.foreground_subinstances,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "schema", "family_counts", "eligible_positive_families",
        "cross_paint_positive_families", "positive_trials", "positive_passed",
        "negative_trials", "negative_passed", "all_passed", "casts_votes",
        "ownership_authority"
    )}, indent=2))
    return 0 if report["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
