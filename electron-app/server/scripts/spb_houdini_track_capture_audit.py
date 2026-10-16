"""Validate a matched-lighting FRACTURED HOUDINI capture set.

This does not claim that a material reveal occurred. It only records whether
the supplied iRacing screenshots have matching dimensions, broadly aligned
scene geometry and materially different luminance, so an owner-eye inspection
has trustworthy like-for-like frames to review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def _features(gray: np.ndarray):
    orb = cv2.ORB_create(nfeatures=1800)
    return orb.detectAndCompute(gray, None)


def _pair(a: np.ndarray, b: np.ndarray) -> dict[str, float | int]:
    ka, da = _features(a); kb, db = _features(b)
    if da is None or db is None:
        return {"matches": 0, "inliers": 0, "alignment_ratio": 0.0}
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    matches = sorted(matches, key=lambda m: m.distance)[:300]
    if len(matches) < 8:
        return {"matches": len(matches), "inliers": 0, "alignment_ratio": 0.0}
    pa = np.float32([ka[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    pb = np.float32([kb[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(pa, pb, cv2.RANSAC, 4.0)
    inliers = int(mask.sum()) if mask is not None else 0
    return {"matches": len(matches), "inliers": inliers,
            "alignment_ratio": round(inliers / max(len(matches), 1), 4)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit same-location Houdini screenshots")
    ap.add_argument("capture_dir", type=Path, help="Directory containing h1_*.png/jpg captures")
    ap.add_argument("--output", type=Path, default=Path("_houdini_proof/h1_track_capture_audit.json"))
    args = ap.parse_args()
    files = sorted([*args.capture_dir.glob("h1_*.png"), *args.capture_dir.glob("h1_*.jpg"), *args.capture_dir.glob("h1_*.jpeg")])
    if len(files) < 3:
        raise SystemExit("Need at least h1_neutral plus two matched-light h1_*.png/jpg captures")
    images = [cv2.imread(str(p), cv2.IMREAD_COLOR) for p in files]
    if any(image is None for image in images):
        raise SystemExit("One or more captures could not be read")
    shapes = [list(image.shape) for image in images]
    if len({tuple(shape) for shape in shapes}) != 1:
        raise SystemExit("Captures must have identical pixel dimensions")
    gray = [cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) for image in images]
    baseline = gray[0]
    records = []
    for path, image in zip(files, gray):
        records.append({"file": path.name, "mean_luminance": round(float(image.mean()), 3),
                        "std_luminance": round(float(image.std()), 3)})
    pairs = [{"baseline": files[0].name, "other": files[idx].name,
              **_pair(baseline, gray[idx]),
              "mean_luminance_delta": round(abs(float(baseline.mean()) - float(gray[idx].mean())), 3)}
             for idx in range(1, len(files))]
    payload = {"status": "review_required", "files": records, "pairs": pairs,
               "note": "Alignment/luminance checks are capture hygiene only; owner-eye review must confirm the material-only reveal."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
