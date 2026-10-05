# -*- coding: utf-8 -*-
"""Isolated native-2048 Cyan Colony excitable-medium chronology.

SPB-105 / Wilds attempt 74 / 2026-08-25. A deterministic 15-state excitable
tissue evolves around unequal nutrient sinks. Moving fronts, daughter fronts,
collision saddles, bridge necks, void halos, shed cells, healed tissue and
refractory wakes are captured from the chronology rather than placed as icons.

The simulation cell is 8 px native and derived front widths span 8--32 px. No
RNG, sampled noise, FBM, circular colony stamps, scalar ripple texture, shared
composer or recolor fallback.

Native-2048 verdict: REJECTED. The 256-cell chronology becomes a pixelated
maze/static field with repeated black sink-hole stamps. Events are numerically
distinct but visually collapse into block noise and dots. Frozen before
spec/M7/runtime. No state, grid, smoothing, source, sink, palette, density,
scale, spec or noise repair is authorized.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_cyan_colony"
SIM = 256
WORK = 1024
NATIVE = 2048
STATES = 15

PALETTE_A = np.asarray([
    (3, 12, 20), (3, 28, 42), (3, 49, 65), (3, 74, 87),
    (5, 101, 104), (10, 130, 116), (21, 159, 122), (39, 187, 122),
    (66, 211, 119), (102, 230, 121), (145, 240, 132), (188, 244, 151),
    (226, 241, 179), (248, 220, 207), (244, 178, 225),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (22, 4, 30), (44, 5, 55), (69, 7, 81), (96, 10, 105),
    (124, 15, 125), (153, 23, 142), (182, 34, 153), (208, 49, 158),
    (229, 70, 159), (244, 96, 159), (252, 127, 166), (255, 161, 181),
    (252, 196, 202), (232, 225, 221), (185, 240, 232),
], np.float32) / 255.0


def _source_arcs():
    masks = []
    for i in range(19):
        mask = np.zeros((SIM, SIM), np.uint8)
        cx = 8 + 240 * ((i * .6180339887498948 + .07 * np.sin(i * .91)) % 1.0)
        cy = 8 + 240 * ((i * .4142135623730950 + .06 * np.sin(i * 1.27)) % 1.0)
        rx = 2 + (i * 7) % 6
        ry = 2 + (i * 11) % 5
        start = 17 + (i * 31) % 94
        end = start + 111 + (i * 23) % 167
        cv2.ellipse(mask, (int(cx), int(cy)), (rx, ry),
                    (i * 137) % 180, start, end, 1, 1 + i % 2, cv2.LINE_8)
        masks.append(mask.astype(bool))
    return masks


def _sinks():
    obstacle = np.zeros((SIM, SIM), np.uint8)
    core = np.zeros_like(obstacle)
    for i in range(43):
        cx = 5 + 246 * ((i * .7548776662466927 + .03 * np.sin(i * .73)) % 1.0)
        cy = 5 + 246 * ((i * .5698402909980532 + .04 * np.sin(i * 1.11)) % 1.0)
        rx = 1 + (i * 5) % 4
        ry = 1 + (i * 7) % 4
        cv2.ellipse(obstacle, (int(cx), int(cy)), (rx + 1, ry + 1),
                    (i * 83) % 180, 0, 360, 1, -1, cv2.LINE_8)
        cv2.ellipse(core, (int(cx), int(cy)), (rx, ry),
                    (i * 83) % 180, 0, 360, 1, -1, cv2.LINE_8)
    return obstacle.astype(bool), core.astype(bool)


def _neighbors(mask):
    total = np.zeros(mask.shape, np.uint8)
    for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                   (0, 1), (1, -1), (1, 0), (1, 1)):
        total += np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return total


@lru_cache(maxsize=1)
def _chronology():
    source_masks = _source_arcs()
    obstacle, core = _sinks()
    state = np.zeros((SIM, SIM), np.uint8)
    activation = np.zeros((SIM, SIM), np.uint16)
    collision = np.zeros((SIM, SIM), np.uint16)
    last = np.full((SIM, SIM), -32768, np.int32)
    first = np.full((SIM, SIM), -1, np.int32)

    # Unequal source clocks prevent a field of synchronous target rings.
    for step in range(286):
        excited = state == 1
        count = _neighbors(excited)
        resting = state == 0
        new = state.copy()
        active = state > 0
        new[active] = (state[active] + 1) % STATES
        propagate = resting & (count >= 1) & (count <= 2) & ~obstacle
        collide = resting & (count >= 3) & ~obstacle
        new[propagate] = 1
        new[collide] = 5 + ((step + np.indices(state.shape)[0][collide]) % 4)
        collision[collide] += 1

        for index, source in enumerate(source_masks):
            period = 23 + (index * 7) % 31
            phase = (index * 13 + index * index) % period
            if step % period == phase:
                inject = source & ~obstacle
                new[inject] = 1

        newly = new == 1
        activation[newly] += 1
        last[newly] = step
        untouched = (first < 0) & newly
        first[untouched] = step
        new[obstacle] = 0
        state = new

    age = np.clip(285 - last, 0, 90)
    phase = np.mod(age, STATES).astype(np.uint8)
    phase[first < 0] = 0
    return phase, activation, collision, obstacle, core, first


def _up(mask, interpolation=cv2.INTER_NEAREST):
    return cv2.resize(mask, (WORK, WORK), interpolation=interpolation)


def _fields():
    phase, activation, collision, obstacle, core, first = _chronology()
    active_fronts = ((phase <= 1) & (first >= 0)).astype(np.float32)
    daughter_fronts = ((activation >= 3) & (phase <= 3)).astype(np.float32)
    refractory = ((phase >= 5) & (phase <= 11)).astype(np.float32)
    saddles = (collision >= 1).astype(np.float32)
    healed = (activation >= 6).astype(np.float32)
    void_halo = (cv2.dilate(obstacle.astype(np.uint8), np.ones((5, 5), np.uint8))
                 - obstacle.astype(np.uint8)).clip(0, 1).astype(np.float32)
    bridge = ((collision >= 2) & (activation >= 2)).astype(np.float32)
    shed = ((activation == 1) & (phase >= 12)).astype(np.float32)
    return {
        "phase": _up(phase, cv2.INTER_NEAREST).astype(np.uint8),
        "active_fronts": _up(active_fronts),
        "daughter_fronts": _up(daughter_fronts),
        "refractory_wakes": _up(refractory),
        "collision_saddles": _up(saddles),
        "healed_tissue": _up(healed),
        "void_halos": _up(void_halo),
        "bridge_necks": _up(bridge),
        "shed_cells": _up(shed),
        "sink_cores": _up(core.astype(np.float32)),
    }


def _paint(angle_b=False):
    f = _fields()
    palette = PALETTE_B if angle_b else PALETTE_A
    paint = palette[f["phase"]]
    if angle_b:
        layers = (
            (f["active_fronts"], (.98, .85, .29), .94),
            (f["daughter_fronts"], (.96, .31, .74), .89),
            (f["refractory_wakes"], (.18, .62, .94), .48),
            (f["collision_saddles"], (.98, .94, .68), .96),
            (f["healed_tissue"], (.56, .20, .90), .84),
            (f["void_halos"], (.68, .95, .55), .92),
            (f["bridge_necks"], (.99, .47, .27), .94),
            (f["shed_cells"], (.05, .08, .13), .96),
            (f["sink_cores"], (.01, .03, .05), .99),
        )
    else:
        layers = (
            (f["active_fronts"], (.85, 1.0, .68), .94),
            (f["daughter_fronts"], (.08, .88, .75), .89),
            (f["refractory_wakes"], (.08, .35, .55), .48),
            (f["collision_saddles"], (1.0, .84, .45), .96),
            (f["healed_tissue"], (.20, .73, .65), .84),
            (f["void_halos"], (.99, .51, .22), .92),
            (f["bridge_necks"], (.92, .18, .54), .94),
            (f["shed_cells"], (.01, .04, .06), .96),
            (f["sink_cores"], (.005, .02, .03), .99),
        )
    for mask, color, alpha in layers:
        a = np.clip(mask * alpha, 0, 1)[..., None]
        paint = paint * (1 - a) + np.asarray(color, np.float32) * a
    return np.clip(paint, 0, 1), f


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/cyan_colony_excitable_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    fields = None
    for _ in range(3):
        started = time.perf_counter()
        paint, fields = _paint(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _paint(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
    cv2.imwrite(str(out / f"{ID}_paint_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_a_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_b_2048.png"), cv2.cvtColor(native_b, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 74,
        "math": "deterministic 15-state excitable medium with unequal source clocks and sinks",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float(mask.mean()) for name, mask in fields.items()
                     if name != "phase"},
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
