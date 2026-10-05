# -*- coding: utf-8 -*-
"""Re-open VC-I1 on the owner's actual native-2048 decision surface.

The 2026-08-24 verdict mixed a picker-scale objection into the decision. The
owner later explicitly ruled that Fractured Wilds must be judged at the full
2048 canvas. This script preserves the frozen builder byte-for-byte and emits
literal nearest-resized runtime paint/spec plus A/B evidence for re-adjudication.
It does not register, sync, or wire the finish.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

from engine.expansions.fractured_wilds_petri_violet_chains_i1_2026 import (
    _authored,
    clear_cache,
    debug_angle_pair,
)


ID = "fpe_violet_chains"


def _write_rgb(path: Path, image: np.ndarray) -> None:
    arr = np.clip(np.asarray(image, np.float32) * 255.0, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "_wilds_fullres_progress_20260824" / "violet_chains_native_recheck"
    out.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache()
        start = time.perf_counter()
        paint, spec = _authored(ID)
        angle_a, angle_b, delta = debug_angle_pair(ID)
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
    _write_rgb(out / f"{ID}_paint_2048.png", paint)
    _write_rgb(out / f"{ID}_angle_a_2048.png", angle_a)
    _write_rgb(out / f"{ID}_angle_b_2048.png", angle_b)
    _write_rgb(out / f"{ID}_angle_delta_x2_2048.png", np.clip(delta * 2.0, 0, 1))
    _write_rgb(out / f"{ID}_crop_1to1.png", angle_a[512:1280, 640:1408])
    for index, name in enumerate(("metal", "roughness", "clearcoat")):
        channel = spec[:, :, index].astype(np.float32) / 255.0
        _write_rgb(out / f"{ID}_{name}_2048.png", np.repeat(channel[..., None], 3, axis=2))
    report = {
        "id": ID,
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
