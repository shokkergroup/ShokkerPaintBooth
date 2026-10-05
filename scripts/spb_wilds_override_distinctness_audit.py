"""Fail-visible topology audit for provisional Fractured Wilds overrides.

M7 does not prove that two finishes have distinct carriers.  This focused gate
compares actual authored paint and causal M/R/Cc topology across every live
provisional Wilds override.  It intentionally strips colour to test structure,
then separately compares material channels; a hue-only recolour or a reused
spec topology is therefore reported even when general quality metrics pass.

This is a debt/review gate, not owner approval.  A warning must trigger visual
inspection at literal 2048 before a candidate stays in the experimental app.
"""
from __future__ import annotations

import itertools
import json
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.fractured_wilds_accepted_2026 import ACCEPTED_IDS  # noqa: E402

OUT = ROOT / "_wilds_fullres_progress_20260824" / "accepted_runtime_rollout" / "distinctness_audit.json"
SIZE = 384


def _standardize(image: np.ndarray) -> np.ndarray:
    x = np.asarray(image, np.float32)
    x -= float(x.mean())
    return x / max(float(x.std()), 1e-6)


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    x, y = _standardize(a).ravel(), _standardize(b).ravel()
    return float(np.mean(x * y))


def _features(paint: np.ndarray, spec: np.ndarray) -> dict[str, np.ndarray]:
    rgb = cv2.resize(paint.astype(np.float32), (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    # Gradient magnitude suppresses palette identity but retains actual mark,
    # cell, rail, tissue, fibre and fracture placement.
    smooth = cv2.GaussianBlur(luma, (0, 0), 0.8)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.hypot(gx, gy)
    sch = cv2.resize(spec.astype(np.float32), (SIZE, SIZE), interpolation=cv2.INTER_NEAREST)
    return {"luma": luma, "edge": edge, "M": sch[:, :, 0], "R": sch[:, :, 1], "Cc": sch[:, :, 2]}


def _extract_one(fid: str, out: Path) -> None:
    """Render exactly one source in a disposable process and persist only 384px features.

    SPB-105 / owner Wilds rebuild, 2026-08-26.  The prior in-process audit
    retained 110 isolated 2048 render caches and could grow beyond 17 GB.  A
    child process now owns each source cache and exits immediately after writing
    this audit's small, color-stripped paint + M/R/Cc evidence.
    """
    from engine.expansions.fractured_wilds_accepted_2026 import _accepted_authored
    paint, spec = _accepted_authored(fid)
    features = _features(paint, spec)
    np.savez_compressed(out, **features)


def _subprocess_features(fid: str, directory: Path) -> dict[str, np.ndarray]:
    target = directory / f"{fid}.npz"
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--extract", fid, "--out", str(target)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=45,
    )
    if result.returncode != 0 or not target.is_file():
        tail = (result.stderr or result.stdout or "no child output")[-1200:]
        raise RuntimeError(f"feature extraction failed for {fid}: {tail}")
    with np.load(target) as raw:
        return {name: raw[name] for name in raw.files}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", metavar="FINISH_ID")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.extract:
        if args.extract not in ACCEPTED_IDS or args.out is None:
            raise SystemExit("--extract requires an accepted finish ID and --out path")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        _extract_one(args.extract, args.out)
        return 0

    records = {}
    with tempfile.TemporaryDirectory(prefix="spb_wilds_distinctness_") as temp:
        directory = Path(temp)
        for fid in ACCEPTED_IDS:
            records[fid] = _subprocess_features(fid, directory)
    pairs, warnings = [], []
    for left, right in itertools.combinations(ACCEPTED_IDS, 2):
        a, b = records[left], records[right]
        row = {
            "left": left, "right": right,
            "luma_correlation": round(_corr(a["luma"], b["luma"]), 6),
            "edge_correlation": round(_corr(a["edge"], b["edge"]), 6),
            "spec_M_correlation": round(_corr(a["M"], b["M"]), 6),
            "spec_R_correlation": round(_corr(a["R"], b["R"]), 6),
            "spec_Cc_correlation": round(_corr(a["Cc"], b["Cc"]), 6),
        }
        # Near-identity across colour-stripped paint AND all material maps is
        # the lazy-recolour signature; a single high correlation just routes
        # a pair to owner-eye inspection rather than declaring it duplicate.
        near = (row["luma_correlation"] > 0.94 and row["edge_correlation"] > 0.90)
        reused_spec = min(row["spec_M_correlation"], row["spec_R_correlation"], row["spec_Cc_correlation"]) > 0.93
        row["warning"] = bool(near or reused_spec)
        if row["warning"]:
            row["reason"] = "near paint topology" if near else "near reused M/R/Cc topology"
            warnings.append(row)
        pairs.append(row)
    payload = {
        "schema": "spb-wilds-override-distinctness/1",
        "scope": "actual authored provisional runtime overrides; colour-stripped paint + M/R/Cc topology",
        "count": len(ACCEPTED_IDS), "pair_count": len(pairs), "warning_count": len(warnings),
        "thresholds": {"paint_luma": 0.94, "paint_edge": 0.90, "all_spec": 0.93},
        "warnings": warnings,
        "closest_paint_pairs": sorted(pairs, key=lambda r: (r["edge_correlation"], r["luma_correlation"]), reverse=True)[:12],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"distinctness: {payload['count']} overrides, {payload['pair_count']} pairs, {payload['warning_count']} warnings")
    for row in payload["closest_paint_pairs"][:5]:
        print(f"  {row['left']} <> {row['right']}: edge={row['edge_correlation']:.3f} luma={row['luma_correlation']:.3f}")
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
