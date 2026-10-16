"""Refresh shipping scorecard signals for exactly 178 Gradient finishes.

SPB-GRADIENT-OVERHAUL 2026-08-23.  The overhaul keeps the 125 ``grad_*``
finishes and 10 ``gradient_*`` material finishes, and expands the distinctive
``grd_*`` showcase lane from 11 to 43 cards, including the 12-card mathematical
composition wave.  Audit renders are intentionally
isolated from shipping metadata; this command is the explicit, fail-closed
promotion step for their render-derived scorecard signals.

The command renders the final production registry at the standard 512px audit
size and updates only the 178 corresponding ``monolithic:`` rows.  It writes
atomically only with ``--write`` and never touches mirrors, thumbnails, metric
outputs, a running server, or the retired third copy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_refresh_wilds_shipping_scorecard import (  # noqa: E402
    _paint_metrics,
    _scorecard_parts,
    _sha256,
    _spec_metrics,
)


SCORECARD = ROOT / "paint-booth-0-catalog-scorecard.js"
FINISH_DATA = ROOT / "paint-booth-0-finish-data.js"
AUDIT_SIZE = 512
SEED = 20260823
EXPECTED_COUNTS = {"legacy": 125, "showcase": 43, "material": 10}
EXPECTED_TOTAL = sum(EXPECTED_COUNTS.values())
EXPECTED_CATEGORIES = {
    "Gradient Directional": 34,
    "Gradient Extended": 101,
    "🌈 GRADIENTS": 43,
}


def _decode_js_string(value: str) -> str:
    return json.loads('"' + value + '"')


def _named_arrays(source: str, name: str) -> list[list[str]]:
    matches = list(re.finditer(
        rf'"{re.escape(name)}"\s*:\s*\[(.*?)\]',
        source,
        flags=re.S,
    ))
    if not matches:
        raise RuntimeError(f"Could not find catalog array: {name}")
    arrays: list[list[str]] = []
    for match in matches:
        try:
            values = json.loads("[" + match.group(1) + "]")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Could not parse catalog array: {name}") from exc
        if not all(isinstance(value, str) for value in values):
            raise RuntimeError(f"Catalog array contains a non-string value: {name}")
        arrays.append(values)
    return arrays


def _named_array(source: str, name: str) -> list[str]:
    return _named_arrays(source, name)[0]


def _catalog_census(path: Path = FINISH_DATA) -> tuple[list[str], dict[str, str], dict[str, str]]:
    source = path.read_text(encoding="utf-8")

    defs_match = re.search(
        r"const\s+GRADIENT_DEFS\s*=\s*\[(.*?)\n\];",
        source,
        flags=re.S,
    )
    if defs_match is None:
        raise RuntimeError("Could not locate GRADIENT_DEFS")
    legacy_names = {
        match.group(1): _decode_js_string(match.group(2))
        for match in re.finditer(
            r'\[\s*"(grad_[^"]+)",\s*"((?:\\.|[^"])*)"',
            defs_match.group(1),
        )
    }

    explicit_names: dict[str, str] = {}
    for match in re.finditer(
        r'\{\s*id:\s*"((?:grd_|gradient_)[^"]+)",\s*'
        r'name:\s*"((?:\\.|[^"])*)"',
        source,
    ):
        explicit_names[match.group(1)] = _decode_js_string(match.group(2))

    directional = _named_array(source, "Gradient Directional")
    vortex = _named_array(source, "Gradient Vortex")
    extended_arrays = _named_arrays(source, "Gradient Extended")
    if len(extended_arrays) != 2:
        raise RuntimeError(
            "Expected the Color Science and material Gradient Extended arrays, "
            f"got {len(extended_arrays)}"
        )
    extended, material = extended_arrays
    showcase = _named_array(source, "🌈 GRADIENTS")

    category_by_id: dict[str, str] = {}
    for finish_id in directional + vortex:
        category_by_id[finish_id] = "Gradient Directional"
    for finish_id in extended + material:
        category_by_id[finish_id] = "Gradient Extended"
    for finish_id in showcase:
        category_by_id[finish_id] = "🌈 GRADIENTS"

    names = dict(legacy_names)
    names.update({finish_id: explicit_names[finish_id] for finish_id in material + showcase})
    finish_ids = sorted(category_by_id)
    counts = {
        "legacy": sum(finish_id.startswith("grad_") for finish_id in finish_ids),
        "showcase": sum(finish_id.startswith("grd_") for finish_id in finish_ids),
        "material": sum(finish_id.startswith("gradient_") for finish_id in finish_ids),
    }
    category_counts = {
        category: sum(value == category for value in category_by_id.values())
        for category in EXPECTED_CATEGORIES
    }

    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"Gradient catalog census drift: {counts}")
    if category_counts != EXPECTED_CATEGORIES:
        raise RuntimeError(f"Gradient category census drift: {category_counts}")
    if len(finish_ids) != EXPECTED_TOTAL or len(category_by_id) != EXPECTED_TOTAL:
        raise RuntimeError(f"Gradient catalog duplicate/drift: ids={len(finish_ids)}")
    if set(names) != set(finish_ids):
        missing = sorted(set(finish_ids) - set(names))
        extra = sorted(set(names) - set(finish_ids))
        raise RuntimeError(f"Gradient name census mismatch: missing={missing}, extra={extra}")
    if set(legacy_names) != set(directional + vortex + extended):
        raise RuntimeError("GRADIENT_DEFS and Color Science catalog membership disagree")
    if set(showcase) != {finish_id for finish_id in explicit_names if finish_id.startswith("grd_")}:
        raise RuntimeError("Showcase metadata and 🌈 GRADIENTS membership disagree")
    return finish_ids, names, category_by_id


def _engine_registry(finish_ids: list[str]):
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()
    registry_ids = {
        finish_id
        for finish_id in engine.MONOLITHIC_REGISTRY
        if finish_id.startswith(("grad_", "grd_", "gradient_"))
    }
    if registry_ids != set(finish_ids):
        missing = sorted(set(finish_ids) - registry_ids)
        extra = sorted(registry_ids - set(finish_ids))
        raise RuntimeError(f"Gradient catalog/registry mismatch: missing={missing}, extra={extra}")
    return engine.MONOLITHIC_REGISTRY


def _refresh_entry(entry: dict, finish_id: str, name: str, category: str, paint, spec) -> dict:
    paint_metrics = _paint_metrics(paint)
    spec_metrics = _spec_metrics(spec)
    result = dict(entry)
    result.update({
        "id": finish_id,
        "name": name,
        "category": category,
        "surface": "Special / Monolithic",
        "surface_kind": "monolithic",
        "specMRange": round(spec_metrics["m_range"], 4),
        "specRRange": round(spec_metrics["r_range"], 4),
        "specCcRange": round(spec_metrics["cc_range"], 4),
        "specMStd": round(spec_metrics["m_std"], 4),
        "specRStd": round(spec_metrics["r_std"], 4),
        "specCcStd": round(spec_metrics["cc_std"], 4),
        "specChannelIndependence": round(spec_metrics["independence"], 4),
        "paintLumaStd": round(paint_metrics["paint_luma_std"], 4),
        "paintLumaSpan": round(paint_metrics["paint_luma_span"], 4),
        "paintFineEnergy": round(paint_metrics["paint_fine_energy"], 6),
        "paintResidualEnergy": round(paint_metrics["paint_residual_energy"], 6),
        "paintBlockEnergy": round(paint_metrics["paint_block_energy"], 6),
        "paintMacroEnergy": round(paint_metrics["paint_macro_energy"], 6),
        "paintMicroMacroRatio": round(paint_metrics["paint_micro_macro_ratio"], 6),
        "paintColorPopulation": paint_metrics["paint_color_population"],
        "paintSaturationMean": round(paint_metrics["paint_saturation_mean"], 6),
    })
    return result


def refresh(*, write: bool, census_only: bool = False, size: int = AUDIT_SIZE) -> dict:
    header, scorecard, tail = _scorecard_parts(SCORECARD)
    before_bytes = SCORECARD.read_bytes()
    finish_ids, names, category_by_id = _catalog_census()
    registry = _engine_registry(finish_ids)
    target_keys = {f"monolithic:{finish_id}" for finish_id in finish_ids}
    existing_gradient_keys = {
        key for key in scorecard
        if key.startswith("monolithic:")
        and key.split(":", 1)[1].startswith(("grad_", "grd_", "gradient_"))
    }
    if existing_gradient_keys - target_keys:
        raise RuntimeError(
            "Scorecard contains non-shipping Gradient rows: "
            f"{sorted(existing_gradient_keys - target_keys)}"
        )

    summary = {
        "count": len(finish_ids),
        "families": dict(EXPECTED_COUNTS),
        "categories": dict(EXPECTED_CATEGORIES),
        "scorecardBefore": len(existing_gradient_keys),
        "scorecardMissingBefore": len(target_keys - existing_gradient_keys),
        "written": False,
    }
    if census_only:
        return summary

    before_scorecard = {key: dict(value) for key, value in scorecard.items()}
    shape = (size, size)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    base_boost = np.zeros(shape, np.float32)

    for index, finish_id in enumerate(finish_ids, 1):
        entry = registry[finish_id]
        spec_fn, paint_fn = entry[:2]
        paint = paint_fn(source.copy(), shape, mask.copy(), SEED, 1.0, base_boost.copy())
        spec = spec_fn(shape, mask.copy(), SEED, 1.0)
        key = f"monolithic:{finish_id}"
        scorecard[key] = _refresh_entry(
            scorecard.get(key, {}),
            finish_id,
            names[finish_id],
            category_by_id[finish_id],
            paint,
            spec,
        )
        if index == 1 or index % 10 == 0 or index == len(finish_ids):
            print(f"[gradient-scorecard] {index:03d}/{EXPECTED_TOTAL} {finish_id}", flush=True)

    after_gradient_keys = {
        key for key in scorecard
        if key.startswith("monolithic:")
        and key.split(":", 1)[1].startswith(("grad_", "grd_", "gradient_"))
    }
    if after_gradient_keys != target_keys:
        raise RuntimeError(
            f"Refreshed scorecard Gradient census is not exactly {EXPECTED_TOTAL}"
        )

    all_keys = set(before_scorecard) | set(scorecard)
    changed_keys = {
        key for key in all_keys
        if before_scorecard.get(key) != scorecard.get(key)
    }
    non_target_changes = changed_keys - target_keys
    if non_target_changes:
        raise RuntimeError(f"Non-Gradient scorecard rows changed: {sorted(non_target_changes)}")

    rendered = (
        header + json.dumps(scorecard, ensure_ascii=False, indent=2) + tail
    ).encode("utf-8")
    summary.update({
        "changedRows": len(changed_keys),
        "scorecardAfter": len(after_gradient_keys),
        "beforeSha256": _sha256(before_bytes),
        "afterSha256": _sha256(rendered),
        "changed": before_bytes != rendered,
        "written": bool(write),
    })

    if write:
        if SCORECARD.read_bytes() != before_bytes:
            raise RuntimeError("Scorecard changed concurrently; refusing to overwrite it")
        temporary = SCORECARD.with_name(f"{SCORECARD.name}.tmp.{os.getpid()}")
        temporary.write_bytes(rendered)
        os.replace(temporary, SCORECARD)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Atomically update the root shipping scorecard")
    parser.add_argument("--census-only", action="store_true", help="Validate catalog, registry, and row census without rendering")
    parser.add_argument("--size", type=int, default=AUDIT_SIZE)
    args = parser.parse_args(argv)
    if args.size != AUDIT_SIZE:
        raise SystemExit(f"Release scorecard size is fixed at {AUDIT_SIZE}, got {args.size}")
    if args.write and args.census_only:
        raise SystemExit("--write and --census-only are mutually exclusive")
    summary = refresh(write=args.write, census_only=args.census_only, size=args.size)
    mode = "CENSUS" if args.census_only else ("WROTE" if args.write else "DRY RUN")
    print(f"[gradient-scorecard] {mode} " + json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
