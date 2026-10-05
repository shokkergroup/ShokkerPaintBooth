"""Build and evaluate a local reviewed Smart TGA decal embedding library."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.spec_sculpt.decal_embeddings import (
    EmbeddingReference,
    embed_decal,
    query_embedding_library,
)


SCHEMA = "smart-tga-reviewed-embedding-library-v1"


def _crop(entry: dict[str, Any]) -> tuple[np.ndarray, np.ndarray | None]:
    image = np.asarray(Image.open(entry["source_image"]).convert("RGB"))
    x, y, width, height = [int(value) for value in entry["bbox"]]
    if min(x, y) < 0 or width <= 0 or height <= 0 or y + height > image.shape[0] or x + width > image.shape[1]:
        raise ValueError(f"invalid bbox for {entry.get('id')}")
    crop = image[y:y + height, x:x + width]
    mask_source = entry.get("mask_image")
    if not mask_source:
        return crop, None
    mask = np.asarray(Image.open(mask_source).convert("L")) > 0
    if mask.shape != image.shape[:2]:
        raise ValueError(f"mask shape mismatch for {entry.get('id')}")
    return crop, mask[y:y + height, x:x + width]


def build_and_evaluate(
    manifest: dict[str, Any],
    *,
    min_similarity: float = 0.84,
    ambiguity_margin: float = 0.04,
    min_family_support: int = 2,
) -> tuple[list[EmbeddingReference], dict[str, Any]]:
    references = []
    query_entries = []
    for entry in manifest.get("entries") or ():
        crop, mask = _crop(entry)
        embedding = embed_decal(crop, mask)
        if entry.get("role") == "reference":
            references.append(EmbeddingReference(
                reference_id=str(entry["id"]),
                family_id=str(entry["family_id"]),
                reviewed_owner=str(entry["reviewed_owner"]),
                review_label=str(entry.get("review_label") or "reviewed_decal"),
                source=str(entry["source_image"]),
                bbox=tuple(int(value) for value in entry["bbox"]),
                embedding=embedding,
            ))
        else:
            query_entries.append((entry, embedding))
    results = []
    for entry, embedding in query_entries:
        result = query_embedding_library(
            embedding,
            references,
            min_similarity=min_similarity,
            ambiguity_margin=ambiguity_margin,
            min_family_support=min_family_support,
        )
        expected_family = entry.get("expected_family_id")
        expected_status = str(entry.get("expected_status") or (
            "corroborated" if expected_family else "abstained"
        ))
        passed = result.status == expected_status and (
            expected_family is None or result.family_id == expected_family
        )
        results.append({
            "id": entry.get("id"),
            "expected_status": expected_status,
            "expected_family_id": expected_family,
            "passed": passed,
            **result.__dict__,
        })
    family_counts: dict[str, int] = {}
    for reference in references:
        family_counts[reference.family_id] = family_counts.get(reference.family_id, 0) + 1
    return references, {
        "schema": SCHEMA,
        "reference_count": len(references),
        "family_counts": dict(sorted(family_counts.items())),
        "query_count": len(results),
        "passed_count": sum(item["passed"] for item in results),
        "all_passed": all(item["passed"] for item in results),
        "min_similarity": min_similarity,
        "ambiguity_margin": ambiguity_margin,
        "min_family_support": min_family_support,
        "casts_votes": False,
        "ownership_authority": False,
        "results": results,
    }


def save_library(
    references: Sequence[EmbeddingReference],
    report: dict[str, Any],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    arrays = {reference.reference_id: reference.embedding.views for reference in references}
    np.savez_compressed(output_dir / "embeddings.npz", **arrays)
    index = {
        "schema": SCHEMA,
        "embeddings_file": "embeddings.npz",
        "casts_votes": False,
        "ownership_authority": False,
        "references": [{
            "reference_id": item.reference_id,
            "family_id": item.family_id,
            "reviewed_owner": item.reviewed_owner,
            "review_label": item.review_label,
            "source": item.source,
            "bbox": list(item.bbox),
            "descriptor_side": item.embedding.descriptor_side,
            "source_shape": list(item.embedding.source_shape),
        } for item in references],
    }
    (output_dir / "library.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    (output_dir / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-similarity", type=float, default=0.84)
    parser.add_argument("--ambiguity-margin", type=float, default=0.04)
    parser.add_argument("--min-family-support", type=int, default=2)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    references, report = build_and_evaluate(
        manifest,
        min_similarity=args.min_similarity,
        ambiguity_margin=args.ambiguity_margin,
        min_family_support=args.min_family_support,
    )
    save_library(references, report, args.output)
    print(json.dumps({key: report[key] for key in (
        "schema", "reference_count", "family_counts", "query_count",
        "passed_count", "all_passed", "casts_votes", "ownership_authority"
    )}, indent=2))
    return 0 if report["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
