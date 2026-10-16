# -*- coding: utf-8 -*-
"""Render any frozen isolated Wilds builder at the owner's native 2048 target.

The requested module must expose ``_authored(fid)``, ``clear_cache()`` and
``debug_angle_pair(fid)``. This is an evidence-only tool: it never registers,
syncs, packages, or runtime-wires a finish.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


def _write_rgb(path: Path, image: np.ndarray) -> None:
    arr = np.clip(np.asarray(image, np.float32) * 255.0, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    module = importlib.import_module(args.module)
    authored = getattr(module, "_authored")
    clear_cache = getattr(module, "clear_cache")
    angle_pair = getattr(module, "debug_angle_pair")

    root = Path(__file__).resolve().parents[1]
    out = root / "_wilds_fullres_progress_20260824" / args.label
    out.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache()
        start = time.perf_counter()
        paint, spec = authored(args.id)
        angle_a, angle_b, delta = angle_pair(args.id)
        paint = cv2.resize(paint, (2048, 2048), interpolation=cv2.INTER_NEAREST)
        spec = cv2.resize(spec, (2048, 2048), interpolation=cv2.INTER_NEAREST)
        angle_a = cv2.resize(angle_a, (2048, 2048), interpolation=cv2.INTER_NEAREST)
        angle_b = cv2.resize(angle_b, (2048, 2048), interpolation=cv2.INTER_NEAREST)
        delta = cv2.resize(delta, (2048, 2048), interpolation=cv2.INTER_NEAREST)
        timings.append(time.perf_counter() - start)
        blob = (np.ascontiguousarray(paint).tobytes()
                + np.ascontiguousarray(spec).tobytes()
                + np.ascontiguousarray(angle_a).tobytes()
                + np.ascontiguousarray(angle_b).tobytes())
        digests.append(hashlib.sha256(blob).hexdigest())
        last = paint, spec, angle_a, angle_b, delta
    paint, spec, angle_a, angle_b, delta = last
    _write_rgb(out / f"{args.id}_paint_2048.png", paint)
    _write_rgb(out / f"{args.id}_angle_a_2048.png", angle_a)
    _write_rgb(out / f"{args.id}_angle_b_2048.png", angle_b)
    _write_rgb(out / f"{args.id}_angle_delta_x2_2048.png", np.clip(delta * 2.0, 0, 1))
    _write_rgb(out / f"{args.id}_crop_1to1.png", angle_a[512:1280, 640:1408])
    for index, name in enumerate(("metal", "roughness", "clearcoat")):
        channel = spec[:, :, index].astype(np.float32) / 255.0
        _write_rgb(out / f"{args.id}_{name}_2048.png", np.repeat(channel[..., None], 3, axis=2))
    report = {
        "id": args.id,
        "module": args.module,
        "status": "NATIVE-2048-RECHECK-FROZEN-BUILDER-NOT-WIRED",
        "timings_s": timings,
        "deterministic": len(set(digests)) == 1,
        "digest": digests[0],
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, 0.95)),
        "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
