#!/usr/bin/env python3
"""Render isolated Fractured Wilds work at the owner's 2048x2048 target.

This is visual review evidence, not registry wiring.  It deliberately avoids
picker-size acceptance logic: native paint, material channels, angle states,
and unscaled 512px detail crops are the decision surfaces.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "_wilds_fullres_progress_20260824" / "retained_existing"
TARGET = 2048

CANDIDATES = (
    (
        "fmo_morpho_blue",
        "engine.expansions.fractured_wilds_morpho_bio_independent_w2_2026",
        "five-state wing-flow nanoridge domains",
    ),
    (
        "fc_webbed_membrane",
        "engine.expansions.fractured_wilds_cryptid_rebuild_2026",
        "hierarchical tension membrane with load paths, cells, nodes and tears",
    ),
    (
        "fpe_amber_plankton",
        "engine.expansions.fractured_wilds_petri_independent_w7_2026",
        "deterministic chaotic-advection lamellae and collision history",
    ),
)


def _rgb8(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, np.float32)
    if value.max(initial=0.0) > 1.5:
        value = value / 255.0
    return np.rint(np.clip(value[..., :3], 0.0, 1.0) * 255.0).astype(np.uint8)


def _sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _save_rgb(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), cv2.cvtColor(value, cv2.COLOR_RGB2BGR)):
        raise RuntimeError(f"could not write {path}")


def _detail_board(paint: np.ndarray) -> np.ndarray:
    """Four literal 512x512, 1:1 crops from the native 2048 raster."""
    starts = ((128, 128), (1408, 192), (256, 1344), (1280, 1280))
    crops = [paint[y:y + 512, x:x + 512] for x, y in starts]
    return np.concatenate((np.concatenate(crops[:2], axis=1),
                           np.concatenate(crops[2:], axis=1)), axis=0)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "spb-wilds-fullres-progress/1",
        "target": "native 2048x2048; picker size is diagnostic only",
        "owner_accepted": False,
        "production_wired": False,
        "candidates": [],
    }
    for fid, module_name, topology in CANDIDATES:
        module = importlib.import_module(module_name)
        clear = getattr(module, "clear_cache", None)
        if clear:
            clear()
        started = time.perf_counter()
        authored_paint, authored_spec = module._authored(fid)
        paint = cv2.resize(_rgb8(authored_paint), (TARGET, TARGET),
                           interpolation=cv2.INTER_NEAREST)
        spec = cv2.resize(np.asarray(authored_spec)[..., :3], (TARGET, TARGET),
                          interpolation=cv2.INTER_NEAREST).astype(np.uint8)
        angle_a, angle_b, _difference = module.debug_angle_pair(fid)
        angle_a = cv2.resize(_rgb8(angle_a), (TARGET, TARGET),
                             interpolation=cv2.INTER_NEAREST)
        angle_b = cv2.resize(_rgb8(angle_b), (TARGET, TARGET),
                             interpolation=cv2.INTER_NEAREST)
        elapsed = time.perf_counter() - started

        finish_dir = OUT / fid
        _save_rgb(finish_dir / "paint_2048.png", paint)
        _save_rgb(finish_dir / "angle_a_2048.png", angle_a)
        _save_rgb(finish_dir / "angle_b_2048.png", angle_b)
        _save_rgb(finish_dir / "detail_crops_1to1.png", _detail_board(paint))
        for index, name in enumerate(("metal", "roughness", "clearcoat")):
            channel = np.repeat(spec[..., index, None], 3, axis=2)
            _save_rgb(finish_dir / f"{name}_2048.png", channel)

        report["candidates"].append({
            "id": fid,
            "module": module_name,
            "topology": topology,
            "seconds_cold_authored_plus_native_resize": round(elapsed, 4),
            "paint_sha256": _sha(paint),
            "spec_sha256": _sha(spec),
            "angle_a_sha256": _sha(angle_a),
            "angle_b_sha256": _sha(angle_b),
            "spec_std_m_r_cc": [round(float(spec[..., i].std()), 3) for i in range(3)],
            "spec_channel_correlations_mr_mc_rc": [
                round(float(value), 6) for value in (
                    np.corrcoef(spec[..., 0].ravel(), spec[..., 1].ravel())[0, 1],
                    np.corrcoef(spec[..., 0].ravel(), spec[..., 2].ravel())[0, 1],
                    np.corrcoef(spec[..., 1].ravel(), spec[..., 2].ravel())[0, 1],
                )
            ],
            "spec_channel_sha256_m_r_cc": [_sha(spec[..., i]) for i in range(3)],
            "paint": str((finish_dir / "paint_2048.png").relative_to(ROOT)),
            "detail_crops": str((finish_dir / "detail_crops_1to1.png").relative_to(ROOT)),
        })
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                     encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
