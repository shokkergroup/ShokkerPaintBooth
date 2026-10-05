# -*- coding: utf-8 -*-
"""Isolated native-2048 Will-o'-Wisp closed-filament-knot study.

SPB-105 / Wilds attempt 92 / 2026-08-25. One deterministic closed harmonic
filament is expanded into an unequal braided sheath that repeatedly crosses and
re-enters itself across the full canvas. Cores, spectral sheaths, crossing
crowns, torsion clamps, lumen windows, snapped gaps, repair hooks, fork locks,
return stitches and cooled afterimages remain attached to the same chronology.
There is no sampled noise, curl-flow field, loose comet/dot scatter, placed knot
stamp, paver, recolour fallback or shared composer. Primitive widths are
8--32 px native; canvas-scale organization emerges from the single closed path.

Native-2048 verdict: REJECTED. The closed chronology is genuinely distinct but
still reads as one giant multistrand spaghetti/loop gesture floating over large
black basins. Crowns, clamps, lumens, gaps, hooks, locks and stitches decorate
the same macro path rather than forming a full-car material. Frozen before
spec/M7/runtime. No curve, strand, crop, density, palette, accessory, scale,
spec or noise repair is authorized; a successor must replace the path carrier.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fc_will_o_wisp"
ATTEMPT = 92
WORK = 1024
NATIVE = 2048
SAMPLES = 7168

PALETTE_A = np.asarray([
    (2, 5, 18), (3, 16, 43), (4, 34, 70), (5, 58, 94), (6, 85, 111),
    (9, 114, 120), (16, 144, 119), (29, 173, 108), (50, 199, 92),
    (79, 219, 79), (116, 232, 77), (158, 237, 91), (198, 232, 119),
    (226, 215, 155), (241, 190, 198),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (20, 2, 29), (48, 3, 55), (79, 4, 76), (111, 7, 90), (143, 12, 97),
    (174, 20, 99), (202, 32, 95), (225, 49, 88), (241, 70, 83),
    (249, 96, 83), (250, 126, 91), (245, 158, 109), (232, 189, 135),
    (210, 215, 168), (178, 233, 207),
], np.float32) / 255.0


def _curve():
    t = np.linspace(0, 2 * np.pi, SAMPLES, endpoint=False, dtype=np.float32)
    x = (512 + 245 * np.sin(3 * t + .21) + 132 * np.sin(7 * t + 1.03)
         + 70 * np.sin(13 * t - .61) + 31 * np.sin(19 * t + .37))
    y = (512 + 238 * np.sin(4 * t - .46) + 137 * np.sin(9 * t + .83)
         + 67 * np.sin(17 * t + .19) + 28 * np.sin(23 * t - .72))
    dx, dy = np.gradient(x), np.gradient(y)
    length = np.sqrt(dx * dx + dy * dy) + 1e-6
    tangent = np.stack((dx / length, dy / length), axis=1)
    normal = np.stack((-tangent[:, 1], tangent[:, 0]), axis=1)
    curvature = np.abs(np.gradient(tangent[:, 0]) * normal[:, 0]
                       + np.gradient(tangent[:, 1]) * normal[:, 1])
    return t, np.stack((x, y), axis=1), tangent, normal, curvature


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    ground_phase = (xx * .00037 + yy * .00023 + (.17 if angle_b else 0)) % 1
    paint = palette[(ground_phase * 14).astype(np.int32)] * .045
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "closed_filament_mass", "spectral_sheaths", "bright_cores",
        "crossing_crowns", "torsion_clamps", "lumen_windows", "snapped_gaps",
        "repair_hooks", "fork_locks", "return_stitches", "cooled_afterimages")}

    t, centre, tangent, normal, curvature = _curve()
    offsets = (-52, -43, -34, -26, -18, -11, -5, 0, 7, 15, 24, 34, 45, 56)
    chunk = 32
    # Cooled afterimages are the same chronology at two physical lag distances,
    # not a second random field.
    for lag, opacity in ((93, .16), (181, .10)):
        ghost = np.roll(centre, lag, axis=0) + np.roll(normal, lag, axis=0) * (7 + lag % 11)
        poly = np.rint(ghost).astype(np.int32)
        color = tuple(float(v) for v in np.clip(palette[(lag // 7) % 15] * opacity, 0, 1))
        cv2.polylines(paint, [poly], True, color, 4 + lag % 3, cv2.LINE_AA)
        cv2.polylines(masks["cooled_afterimages"], [poly], True, 255, 4 + lag % 3, cv2.LINE_AA)

    for strand, offset in enumerate(offsets):
        breathing = offset + (2.4 + strand % 4) * np.sin(t * (5 + strand % 5) + strand * .73)
        points = centre + normal * breathing[:, None]
        poly = np.rint(points).astype(np.int32)
        sheath_width = 6 + strand % 5  # 12--20 px native.
        dark = tuple(float(v) for v in np.clip(palette[(strand * 3 + 1) % 15] * .24, 0, 1))
        cv2.polylines(paint, [poly], True, dark, sheath_width + 4, cv2.LINE_AA)
        cv2.polylines(masks["closed_filament_mass"], [poly], True, 255, sheath_width + 4, cv2.LINE_AA)
        # Optical order changes along the literal curve; chunks avoid a flat
        # recolor while preserving the same physical strand.
        for start in range(0, SAMPLES, chunk):
            end = min(SAMPLES, start + chunk + 1)
            segment = poly[start:end]
            if len(segment) < 2:
                continue
            order = (start // chunk * 5 + strand * 7 + (9 if angle_b else 0)) % 15
            color = tuple(float(v) for v in np.clip(palette[order] * (.62 + .06 * (strand % 4)), 0, 1))
            cv2.polylines(paint, [segment], False, color, sheath_width, cv2.LINE_AA)
            cv2.polylines(masks["spectral_sheaths"], [segment], False, 255, sheath_width, cv2.LINE_AA)
        core_color = tuple(float(v) for v in np.clip(palette[(strand * 7 + 12) % 15] * 1.2, 0, 1))
        cv2.polylines(paint, [poly], True, core_color, 2 + strand % 2, cv2.LINE_AA)
        cv2.polylines(masks["bright_cores"], [poly], True, 255, 2 + strand % 2, cv2.LINE_AA)

    # Curvature-selected anatomy is attached to one timeline. Events are
    # explicitly separated by arc length, not scattered random coordinates.
    order = np.argsort(curvature)[::-1]
    chosen = []
    for index in order:
        if all(min(abs(int(index) - q), SAMPLES - abs(int(index) - q)) > 137 for q in chosen):
            chosen.append(int(index))
        if len(chosen) == 31:
            break
    chosen.sort()
    for event, index in enumerate(chosen):
        c = centre[index]
        tg, nm = tangent[index], normal[index]
        family = event % 7
        if family == 0:  # crossing crown
            for k in (-2, -1, 0, 1, 2):
                a = c - tg * (8 + abs(k) * 2) + nm * k * 4
                b = c + tg * (8 + abs(k) * 2) - nm * k * 3
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                         tuple(float(v) for v in np.clip(palette[(event * 3 + k + 10) % 15] * 1.2, 0, 1)), 3, cv2.LINE_AA)
                cv2.line(masks["crossing_crowns"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)
        elif family == 1:  # clamp
            a, b = c - nm * 13, c + nm * 13
            cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), (0.004, .003, .009), 6, cv2.LINE_AA)
            cv2.line(masks["torsion_clamps"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 6, cv2.LINE_AA)
        elif family == 2:  # lumen
            cv2.ellipse(paint, tuple(np.rint(c).astype(int)), (8 + event % 5, 4 + event % 3),
                        int(np.degrees(np.arctan2(tg[1], tg[0]))), 0, 360, (0.002, .003, .007), 3, cv2.LINE_AA)
            cv2.ellipse(masks["lumen_windows"], tuple(np.rint(c).astype(int)), (8 + event % 5, 4 + event % 3), 0, 0, 360, 255, 3, cv2.LINE_AA)
        elif family == 3:  # snapped gap
            a, b = c - tg * 10, c + tg * 10
            cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), (0.001, .001, .003), 16, cv2.LINE_AA)
            cv2.line(masks["snapped_gaps"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 16, cv2.LINE_AA)
        elif family == 4:  # repair hook
            pts = np.asarray((c - tg * 8, c + nm * 8, c + tg * 9 + nm * 2), np.float32)
            cv2.polylines(paint, [np.rint(pts).astype(np.int32)], False,
                          tuple(float(v) for v in np.clip(palette[(event * 4 + 11) % 15] * 1.2, 0, 1)), 4, cv2.LINE_AA)
            cv2.polylines(masks["repair_hooks"], [np.rint(pts).astype(np.int32)], False, 255, 4, cv2.LINE_AA)
        elif family == 5:  # fork lock
            for side in (-1, 1):
                a = c - tg * 5
                b = c + tg * 10 + nm * side * 8
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                         tuple(float(v) for v in np.clip(palette[(event + side + 9) % 15] * 1.17, 0, 1)), 3, cv2.LINE_AA)
                cv2.line(masks["fork_locks"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)
        else:  # return stitches
            for k in (-2, 0, 2):
                a = c + tg * k * 4 - nm * 7
                b = c + tg * k * 4 + nm * 7
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                         tuple(float(v) for v in np.clip(palette[(event * 2 + k + 12) % 15] * 1.18, 0, 1)), 2, cv2.LINE_AA)
                cv2.line(masks["return_stitches"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 2, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/will_o_wisp_closed_knot_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks = _render(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(native_a[704:1344, 704:1344], cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {"id": ID, "module": __name__, "attempt": ATTEMPT,
              "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED", "timings_s": timings,
              "deterministic": bool(all(np.array_equal(repeats[0], x) for x in repeats[1:])),
              "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95)),
              "coverage": {k: float((v > 8).mean()) for k, v in masks.items()},
              "owner_accepted": False, "production_wired": False}
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-will-o-wisp-closed-knot-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
