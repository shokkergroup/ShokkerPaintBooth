# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Paua Storm CA I1 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 60, 2026-08-25. Owner verdict being answered:
"EXACT SAME pattern just recolored" and "do NOT just put random noise in the
patterns." This isolated contact records a deterministic fifteen-state cyclic
mineral-front chronology. Neighbour capture, front collisions, arrested wakes,
skip reactions, junctions and healed cells are all consequences of the same
evolution. No RNG/noise, stamps, particles, repeated cells, contour overlay, or
shared Wilds composer. The 256-state lattice makes every causal cell 8 native
pixels; derived junction/front anatomy grows to 8-32 px at 2048.

Paint-only gate: do not add spec, register, package, or runtime-wire unless the
literal 2048 frame and 1:1 crop survive owner-eye review.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_paua_storm"
STATE_RES = 256
WORK = 512
N_STATES = 15

PALETTE_A = np.asarray([
    (4, 8, 18), (10, 25, 56), (11, 55, 96), (6, 91, 129),
    (5, 130, 145), (17, 166, 148), (57, 197, 133), (115, 218, 108),
    (185, 229, 83), (239, 211, 68), (255, 164, 70), (249, 110, 91),
    (220, 66, 126), (165, 43, 145), (92, 31, 126),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (5, 7, 17), (30, 15, 57), (72, 20, 102), (123, 27, 131),
    (178, 41, 137), (222, 65, 120), (248, 103, 91), (255, 153, 68),
    (243, 202, 64), (188, 225, 78), (117, 221, 105), (55, 199, 135),
    (18, 163, 155), (7, 116, 153), (14, 66, 119),
], np.float32) / 255.0

OFFSETS = ((-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1),
           (-2, -1), (-1, -2), (1, -2), (2, -1),
           (2, 1), (1, 2), (-1, 2), (-2, 1))


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.roll(np.roll(a, dy, axis=0), dx, axis=1)
    if dy < 0: out[dy:, :] = out[dy - 1:dy, :]
    elif dy > 0: out[:dy, :] = out[dy:dy + 1, :]
    if dx < 0: out[:, dx:] = out[:, dx - 1:dx]
    elif dx > 0: out[:, :dx] = out[:, dx:dx + 1]
    return out


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = STATE_RES
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    y = (yy + 0.5) / n

    # Aperiodic analytic nucleation: unequal off-frame phase sources establish
    # the initial mineral ages, then disappear into the recorded chronology.
    phase = (4.13 * x - 3.27 * y
             + 0.73 * x * y + 0.41 * x * x - 0.29 * y * y)
    sources = ((-0.17, 0.19, 0.83), (0.22, -0.13, -0.61),
               (0.71, 0.18, 0.77), (1.16, 0.41, -0.93),
               (0.83, 1.21, 0.69), (0.28, 1.11, -0.57),
               (-0.13, 0.77, 0.88))
    for sx, sy, charge in sources:
        dx, dy = x - sx, y - sy
        phase += charge * np.arctan2(dy, dx) / np.pi
        phase += 0.17 * charge * np.log1p(19.0 * (dx * dx + dy * dy))
    state = np.floor(np.mod(phase * 7.3, N_STATES)).astype(np.int16)
    age = np.zeros((n, n), np.float32)
    changes = np.zeros_like(age)
    skips = np.zeros_like(age)
    collision_history = np.zeros_like(age)
    heal_history = np.zeros_like(age)

    for step in range(132):
        target1 = (state + 1) % N_STATES
        target2 = (state + 2) % N_STATES
        count1 = np.zeros_like(state, np.int16)
        count2 = np.zeros_like(state, np.int16)
        diversity = np.zeros_like(state, np.float32)
        for k, (dy, dx) in enumerate(OFFSETS):
            nb = _shift(state, dy, dx)
            count1 += (nb == target1)
            count2 += (nb == target2)
            if k < 8:
                diversity += (nb != state)
        threshold = 3 + (1 if step % 11 in {3, 7} else 0)
        advance = count1 >= threshold
        skip = (~advance) & (count2 >= 8) & ((step + state) % 5 == 0)
        collision = (count1 >= 6) & (count2 >= 5)
        healed = (~advance) & (~skip) & (diversity >= 6) & (age >= 3)
        state = np.where(skip, target2, np.where(advance, target1, state)).astype(np.int16)
        changed = advance | skip
        age = np.where(changed, 0.0, np.minimum(age + 1.0, 31.0))
        changes += changed.astype(np.float32)
        skips += skip.astype(np.float32)
        collision_history += collision.astype(np.float32)
        heal_history += healed.astype(np.float32)

    neighbours = [_shift(state, dy, dx) for dy, dx in OFFSETS[:8]]
    front = np.mean(np.stack([(nb != state).astype(np.float32) for nb in neighbours]), axis=0)
    next_state = (state + 1) % N_STATES
    capture = np.mean(np.stack([(nb == next_state).astype(np.float32) for nb in neighbours]), axis=0)
    junction = _norm(front * (1.0 - np.abs(capture - 0.5) * 1.6))
    fields = {
        "state": state.astype(np.float32) / N_STATES,
        "front": _norm(front),
        "capture": _norm(capture),
        "junction": junction,
        "wake": _norm(changes),
        "skip": _norm(skips),
        "collision": _norm(collision_history),
        "healed": _norm(heal_history),
        "age": age / 31.0,
    }
    return {key: cv2.resize(value, (WORK, WORK), interpolation=cv2.INTER_CUBIC)
            for key, value in fields.items()}


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    f = _fields()
    travel = (f["state"] + 0.19 * f["wake"] + 0.13 * f["collision"]
              + 0.11 * f["skip"] - 0.09 * f["age"])
    if angle_b:
        travel = (1.0 - travel + 0.31 * f["capture"]
                  - 0.21 * f["healed"] + 0.16 * f["junction"])
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    relief = (0.29 + 0.33 * f["wake"] + 0.41 * f["front"]
              + 0.49 * f["junction"] + 0.36 * f["collision"]
              + 0.27 * f["skip"] + 0.22 * f["healed"]
              - 0.19 * f["age"])
    rgb *= np.clip(relief, 0.08, 1.28)[..., None]
    rgb += np.asarray((0.08, 0.33, 0.36) if not angle_b else (0.36, 0.09, 0.28), np.float32) * f["front"][..., None]
    rgb += np.asarray((0.39, 0.22, 0.05) if not angle_b else (0.04, 0.31, 0.31), np.float32) * f["collision"][..., None]
    rgb += np.asarray((0.28, 0.05, 0.35) if not angle_b else (0.38, 0.25, 0.04), np.float32) * f["skip"][..., None]
    return cv2.resize(np.clip(rgb, 0.0, 1.0).astype(np.float32),
                      (2048, 2048), interpolation=cv2.INTER_LANCZOS4)


def clear_cache() -> None:
    _paint.cache_clear(); _fields.cache_clear()


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); start = time.perf_counter(); a = _paint(False); b = _paint(True)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes()
        digests.append(hashlib.sha256(blob).hexdigest()); last = a, b
    a, b = last; delta = np.abs(a - b)
    for suffix, image in (("paint", a), ("angle_a", a), ("angle_b", b),
                          ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        arr = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out_dir / f"{ID}_{suffix}_2048.png"),
                    cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / f"{ID}_crop_1to1.png"),
                cv2.cvtColor(np.clip(a[512:1280, 640:1408] * 255.0, 0, 255).astype(np.uint8),
                             cv2.COLOR_RGB2BGR))
    report = {"id": ID, "status": "NATIVE-2048-PAINT-CONTACT-NO-SPEC-NOT-WIRED",
              "timings_s": timings, "deterministic": len(set(digests)) == 1,
              "digest": digests[0], "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, 0.95))}
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" /
                                     "paua_storm_ca_i1"), indent=2))
