"""Render a dedicated finish candidate for owner-eye preflight.

This is deliberately an advisory tool. It reports render time and M/R/Cc
spread and writes a 256px paint|spec proof, but it never ranks, approves or
installs a finish. The owner-eye gate remains authoritative.

Example:
  python scripts/spb_finish_candidate_screen.py \
    --module engine.expansions.groovy_tie_dye_crumple_i1_2026 \
    --paint paint_tie_dye_crumple --spec spec_tie_dye_crumple \
    --out _houdini_proof/example.png
"""
import argparse
import importlib
import sys
import time
from pathlib import Path

import cv2
import numpy as np


# Run from the project root or directly from scripts/ without depending on a
# developer's PYTHONPATH.  Candidates live in the root-level ``engine`` package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _call_spec(fn, shape, seed):
    """Support the dedicated base and monolithic candidate signatures."""
    try:
        value = fn(shape, seed, 1.0, 0, 0)
    except TypeError:
        value = fn(shape, np.ones(shape, np.float32), seed, 1.0)
    if isinstance(value, tuple):
        value = np.stack(value, axis=2)
    value = np.asarray(value)
    if value.ndim == 3 and value.shape[2] >= 3:
        return value[..., :3].astype(np.uint8)
    raise ValueError("spec function did not return an M/R/Cc array")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True)
    parser.add_argument("--paint", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--native-crop-out", type=Path,
                        help="optional centered 256px 1:1 paint|spec crop")
    parser.add_argument("--size", default=2048, type=int)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()

    mod = importlib.import_module(args.module)
    paint_fn, spec_fn = getattr(mod, args.paint), getattr(mod, args.spec)
    shape = (args.size, args.size)
    mask = np.ones(shape, np.float32)
    source = np.zeros((args.size, args.size, 3), np.float32)
    started = time.perf_counter()
    paint = paint_fn(source, shape, mask, args.seed, 1.0, None)
    spec = _call_spec(spec_fn, shape, args.seed)
    seconds = time.perf_counter() - started
    paint = np.clip(np.asarray(paint)[..., :3], 0, 1)
    if paint.max(initial=0) > 1.5:
        paint = paint / 255.0
    std = spec.reshape(-1, 3).std(axis=0)
    lo, hi = spec.reshape(-1, 3).min(axis=0), spec.reshape(-1, 3).max(axis=0)
    left = cv2.cvtColor((paint * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    right = cv2.cvtColor(spec, cv2.COLOR_RGB2BGR)
    proof = np.hstack((
        cv2.resize(left, (256, 256), interpolation=cv2.INTER_AREA),
        cv2.resize(right, (256, 256), interpolation=cv2.INTER_AREA),
    ))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.out), proof):
        raise RuntimeError(f"could not write {args.out}")
    if args.native_crop_out:
        crop = min(256, args.size)
        top, left_edge = (args.size - crop) // 2, (args.size - crop) // 2
        native = np.hstack((
            left[top:top + crop, left_edge:left_edge + crop],
            right[top:top + crop, left_edge:left_edge + crop],
        ))
        args.native_crop_out.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(args.native_crop_out), native):
            raise RuntimeError(f"could not write {args.native_crop_out}")
    print(f"NATIVE={seconds:.3f}s STD={std[0]:.1f}/{std[1]:.1f}/{std[2]:.1f} "
          f"RANGE={lo.tolist()}-{hi.tolist()} PROOF={args.out}"
          + (f" NATIVE_CROP={args.native_crop_out}" if args.native_crop_out else ""))


if __name__ == "__main__":
    main()
