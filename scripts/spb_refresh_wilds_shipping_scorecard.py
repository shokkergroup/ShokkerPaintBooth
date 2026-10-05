"""Refresh shipping scorecard signals for the canonical 110 Wilds finishes.

SPB-WILDS 2026-08-23, tick 6.  Owner verdict: Wilds must be very unique and
retain its Fractured color exchange.  The renderer audits use isolated
scorecards so they cannot accidentally mutate shipping metadata; this explicit
command is the fail-closed promotion step after those audits pass.

The command renders the current production registry at the catalog's standard
512px audit size, updates only render-derived fields for the exact 20/50/20/20
census, and writes atomically only with ``--write``.  It never touches runtime
mirrors, thumbnails, a running server, or the retired third copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_wilds_release_gate import canonical_wilds_110  # noqa: E402
from scripts.spb_wilds_quality_release_lock import (  # noqa: E402
    DEFAULT_MANIFEST as DEFAULT_QUALITY_RELEASE_MANIFEST,
    validate_quality_release_manifest,
)


SCORECARD = ROOT / "paint-booth-0-catalog-scorecard.js"
FINISH_DATA = ROOT / "paint-booth-0-finish-data.js"
REPORT = ROOT / "_wilds_work" / "wilds_110_shipping_scorecard_refresh.json"
AUDIT_SIZE = 512
SEED = 20260823
CATEGORY_BY_PREFIX = {
    "fc_": "👣 FRACTURED CRYPTID",
    "fmo_": "🦋 FRACTURED MORPHO",
    "fbl_": "🌸 FRACTURED BLOOM",
    "fpe_": "🧫 FRACTURED PETRI",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scorecard_parts(path: Path = SCORECARD):
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"^(.*?const\s+CATALOG_SCORECARD_METRICS\s*=\s*)(\{.*\})(;\s*\n.*)$",
        text,
        flags=re.S,
    )
    if match is None:
        raise RuntimeError(f"Could not parse scorecard wrapper: {path}")
    body = re.sub(r"//[^\n]*", "", match.group(2))
    return match.group(1), json.loads(body), match.group(3)


def _catalog_names(path: Path = FINISH_DATA) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    names: dict[str, str] = {}
    row = re.compile(
        r'\{\s*id:\s*"((?:fc|fmo|fbl|fpe)_[^"]+)",\s*'
        r'name:\s*"((?:\\.|[^"])*)"',
    )
    for match in row.finditer(source):
        names[match.group(1)] = json.loads('"' + match.group(2) + '"')
    return names


def _spec_metrics(spec: np.ndarray) -> dict[str, float]:
    arr = np.asarray(spec[:, :, :3], np.float32)
    channels = [arr[:, :, index] for index in range(3)]
    ranges = [float(channel.max() - channel.min()) for channel in channels]
    stds = [float(channel.std()) for channel in channels]
    independence = []
    for left in range(3):
        for right in range(left + 1, 3):
            x, y = channels[left].ravel(), channels[right].ravel()
            independence.append(
                0.0 if x.std() < 1e-5 or y.std() < 1e-5
                else 1.0 - abs(float(np.corrcoef(x, y)[0, 1]))
            )
    return {
        "m_range": ranges[0], "r_range": ranges[1], "cc_range": ranges[2],
        "m_std": stds[0], "r_std": stds[1], "cc_std": stds[2],
        "independence": float(np.mean(independence)),
    }


def _paint_metrics(paint: np.ndarray) -> dict[str, float]:
    rgb = np.asarray(paint, np.float32)
    if rgb.max() <= 1.5:
        rgb = rgb * 255.0
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    padded = np.pad(luma, 1, mode="edge")
    box = (
        padded[:-2, :-2] + padded[:-2, 1:-1] + padded[:-2, 2:]
        + padded[1:-1, :-2] + padded[1:-1, 1:-1] + padded[1:-1, 2:]
        + padded[2:, :-2] + padded[2:, 1:-1] + padded[2:, 2:]
    ) / 9.0
    fine = float(np.abs(luma - box).mean()) / 255.0
    macro = float(np.abs(box - box.mean()).mean()) / 255.0
    quantized = (rgb // 32).astype(np.int32)
    color_keys = quantized[:, :, 0] * 1024 + quantized[:, :, 1] * 32 + quantized[:, :, 2]
    maximum, minimum = rgb.max(axis=2), rgb.min(axis=2)
    saturation = np.where(maximum > 1e-3, (maximum - minimum) / (maximum + 1e-3), 0.0)
    return {
        "paint_luma_std": float(luma.std()),
        "paint_luma_span": float(luma.max() - luma.min()),
        "paint_fine_energy": fine,
        "paint_residual_energy": fine * 0.7,
        "paint_block_energy": macro,
        "paint_macro_energy": macro,
        "paint_micro_macro_ratio": fine / max(macro, 1e-4),
        "paint_color_population": int(np.unique(color_keys).size),
        "paint_saturation_mean": float(saturation.mean()),
    }


def _category(finish_id: str) -> str:
    for prefix, category in CATEGORY_BY_PREFIX.items():
        if finish_id.startswith(prefix):
            return category
    raise RuntimeError(f"Unexpected Wilds ID prefix: {finish_id}")


def _refresh_entry(entry: dict, finish_id: str, name: str, paint, spec) -> dict:
    paint_metrics = _paint_metrics(paint)
    spec_metrics = _spec_metrics(spec)
    result = dict(entry)
    result.update({
        "id": finish_id,
        "name": name,
        "category": _category(finish_id),
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


def refresh(
    *, write: bool, size: int = AUDIT_SIZE,
    quality_manifest: str | Path = DEFAULT_QUALITY_RELEASE_MANIFEST,
) -> dict:
    from engine.registry import MONOLITHIC_REGISTRY

    header, scorecard, tail = _scorecard_parts()
    before_bytes = SCORECARD.read_bytes()
    registry_lanes, finish_ids = canonical_wilds_110()
    quality_release = None
    if write:
        quality_release = validate_quality_release_manifest(
            quality_manifest, finish_ids, registry=MONOLITHIC_REGISTRY,
        )
    names = _catalog_names()
    if set(names) != set(finish_ids):
        missing = sorted(set(finish_ids) - set(names))
        extra = sorted(set(names) - set(finish_ids))
        raise RuntimeError(f"Wilds catalog/renderer census mismatch: missing={missing}, extra={extra}")

    shape = (size, size)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    base_boost = np.zeros(shape, np.float32)
    rows = []
    for index, finish_id in enumerate(finish_ids, 1):
        entry = __import__("engine.registry", fromlist=["MONOLITHIC_REGISTRY"]).MONOLITHIC_REGISTRY[finish_id]
        spec_fn, paint_fn = entry[:2]
        # Treat every renderer as an independent audit subject.  Defensive
        # copies prevent an accidental in-place mutation in one finish from
        # contaminating every later scorecard row.
        paint = paint_fn(source.copy(), shape, mask.copy(), SEED, 1.0, base_boost.copy())
        spec = spec_fn(shape, mask.copy(), SEED, 1.0)
        key = f"monolithic:{finish_id}"
        refreshed = _refresh_entry(scorecard.get(key, {}), finish_id, names[finish_id], paint, spec)
        scorecard[key] = refreshed
        rows.append({
            "id": finish_id,
            "category": refreshed["category"],
            "paintFineEnergy": refreshed["paintFineEnergy"],
            "paintColorPopulation": refreshed["paintColorPopulation"],
            "specRanges": [refreshed["specMRange"], refreshed["specRRange"], refreshed["specCcRange"]],
        })
        print(f"[wilds-scorecard] {index:03d}/110 {finish_id}", flush=True)

    rendered = (
        header
        + json.dumps(scorecard, ensure_ascii=False, indent=2)
        + tail
    ).encode("utf-8")
    report = {
        "schema": 1,
        "ticket": "SPB-WILDS 2026-08-23 tick 6",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "auditSize": size,
        "seed": SEED,
        "scope": {name: len(ids) for name, ids in registry_lanes.items()},
        "count": len(rows),
        "beforeSha256": _sha256(before_bytes),
        "afterSha256": _sha256(rendered),
        "changed": before_bytes != rendered,
        "written": bool(write),
        "qualityReleaseLock": (
            {
                "status": quality_release["status"],
                "ownerAccepted": quality_release["owner_accepted"],
                "productionWired": quality_release["production_wired"],
                "manifestSha256": quality_release["manifest_sha256"],
                "reviewBundleSha256": quality_release["review_bundle_sha256"],
            }
            if quality_release is not None else
            {"status": "not-required-for-dry-run"}
        ),
        "finishes": rows,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if write:
        temporary = SCORECARD.with_name(f"{SCORECARD.name}.tmp.{os.getpid()}")
        temporary.write_bytes(rendered)
        os.replace(temporary, SCORECARD)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Atomically update the root shipping scorecard")
    parser.add_argument("--size", type=int, default=AUDIT_SIZE)
    parser.add_argument("--quality-manifest", type=Path, default=DEFAULT_QUALITY_RELEASE_MANIFEST)
    args = parser.parse_args(argv)
    if args.size != AUDIT_SIZE:
        raise SystemExit(f"Release scorecard size is fixed at {AUDIT_SIZE}, got {args.size}")
    report = refresh(
        write=args.write, size=args.size, quality_manifest=args.quality_manifest,
    )
    print(
        f"[wilds-scorecard] {'WROTE' if args.write else 'DRY RUN'} "
        f"{report['count']}/110 entries; {report['beforeSha256'][:12]} -> "
        f"{report['afterSha256'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
