# -*- coding: utf-8 -*-
"""Isolated native-2048 Cyan Membrane relief study.

SPB-105 / Wilds attempt 77 / 2026-08-25.  A single continuously shaded lipid
sheet is mechanically deformed by several *different* local events: paired
leaflet folds, fusion saddles, open pores, vesicle buds, protein rafts,
rupture lips, channel gates and exposed ends.  Every event changes the shared
surface height or normal; none is free decoration and no RNG/noise/FBM is used.

Native feature radii are 8--30 px.  Native-2048 verdict: REJECTED.  The shared
surface collapses into huge smooth cyan/orange gradient islands, while folds,
pores, buds, gates and rupture lips read as tiny repeated capsules/rings placed
on top.  This is the prohibited decorative-event-over-macro-carrier failure.
Frozen before spec/M7/runtime; no heightfield, event, palette, lighting,
density, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_cyan_membrane"
WORK = 1024
NATIVE = 2048


def _norm(a):
    a = np.asarray(a, np.float32)
    return (a - float(a.min())) / (float(np.ptp(a)) + 1e-7)


def _smoothstep(lo, hi, a):
    t = np.clip((a - lo) / (hi - lo + 1e-7), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _sites(count, phase, margin=18):
    """Deterministic low-discrepancy coordinates, never a random/noise source."""
    result = []
    for i in range(count):
        x = margin + (WORK - 2 * margin) * ((phase + i * .6180339887498948) % 1.0)
        y = margin + (WORK - 2 * margin) * ((phase * 1.73 + i * .4142135623730950) % 1.0)
        result.append((x, y, i))
    return result


def _stamp(field, cx, cy, rx, ry, value, mode="add", angle=0.0):
    pad = int(max(rx, ry) * 3.1) + 2
    x0, x1 = max(0, int(cx) - pad), min(WORK, int(cx) + pad + 1)
    y0, y1 = max(0, int(cy) - pad), min(WORK, int(cy) + pad + 1)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ca, sa = np.cos(angle), np.sin(angle)
    dx, dy = xx - cx, yy - cy
    u = (ca * dx + sa * dy) / rx
    v = (-sa * dx + ca * dy) / ry
    d2 = u * u + v * v
    shape = np.exp(-2.4 * d2).astype(np.float32)
    if mode == "max":
        field[y0:y1, x0:x1] = np.maximum(field[y0:y1, x0:x1], shape * value)
    else:
        field[y0:y1, x0:x1] += shape * value
    return shape, (x0, x1, y0, y1), d2


def _surface():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Broad deformation merely orients one sheet; visible anatomy is supplied
    # by the sub-32-native-pixel physical events below.
    h = (.22 * np.sin(xx / 47.0 + .55 * np.sin(yy / 71.0))
         + .18 * np.cos(yy / 41.0 - .47 * np.sin(xx / 83.0))
         + .11 * np.sin((xx + 1.31 * yy) / 63.0)
         + .08 * np.cos((1.73 * xx - yy) / 57.0)).astype(np.float32)

    masks = {name: np.zeros((WORK, WORK), np.float32) for name in (
        "paired_leaflet_folds", "fusion_saddles", "open_pores",
        "vesicle_buds", "protein_rafts", "rupture_lips",
        "channel_gates", "exposed_ends")}

    # Paired leaflet folds: two close, unequal ridges with a genuine trough.
    for cx, cy, i in _sites(128, .071):
        a = (i * 2.399963229728653 + .3 * np.sin(i * .71)) % np.pi
        rx, ry = 10 + (i * 7) % 6, 3.2 + (i * 5) % 3
        nx, ny = -np.sin(a), np.cos(a)
        for side, gain in ((-1, .18), (1, .25)):
            shape, box, _ = _stamp(h, cx + nx * 4.0 * side, cy + ny * 4.0 * side,
                                   rx, ry, gain, angle=a)
            x0, x1, y0, y1 = box
            masks["paired_leaflet_folds"][y0:y1, x0:x1] = np.maximum(
                masks["paired_leaflet_folds"][y0:y1, x0:x1], shape)
        _stamp(h, cx, cy, rx * .78, 2.3, -.21, angle=a)

    # Fusion saddles: opposed lobes joined through a narrow negative neck.
    for cx, cy, i in _sites(39, .263):
        a = (i * 1.941611 + .8) % np.pi
        ax, ay = np.cos(a), np.sin(a)
        r = 5 + (i * 3) % 6
        for side in (-1, 1):
            _stamp(h, cx + ax * r * .72 * side, cy + ay * r * .72 * side,
                   r, r * .66, .31, angle=a)
        shape, box, _ = _stamp(h, cx, cy, r * .75, r * .31, -.34, angle=a)
        x0, x1, y0, y1 = box
        masks["fusion_saddles"][y0:y1, x0:x1] = np.maximum(
            masks["fusion_saddles"][y0:y1, x0:x1], shape)

    # Pores are real annular depressions, not painted rings.
    for cx, cy, i in _sites(54, .427):
        r = 4.0 + (i * 5) % 7
        angle = (i * .83) % np.pi
        outer, box, d2 = _stamp(h, cx, cy, r * 1.15, r * (.68 + .04 * (i % 4)),
                                -.46, angle=angle)
        x0, x1, y0, y1 = box
        annulus = np.exp(-11.0 * (np.sqrt(d2 + 1e-7) - .72) ** 2)
        h[y0:y1, x0:x1] += annulus * .24
        masks["open_pores"][y0:y1, x0:x1] = np.maximum(
            masks["open_pores"][y0:y1, x0:x1], np.maximum(outer, annulus))

    # Buds are domes with an offset pinched collar, distinct from pore bowls.
    for cx, cy, i in _sites(43, .613):
        r = 4.5 + (i * 4) % 7
        dome, box, d2 = _stamp(h, cx, cy, r, r * (.78 + .05 * (i % 3)),
                              .52, angle=i * .61)
        x0, x1, y0, y1 = box
        collar = np.exp(-13.0 * (np.sqrt(d2 + 1e-7) - .91) ** 2)
        h[y0:y1, x0:x1] -= collar * .18
        masks["vesicle_buds"][y0:y1, x0:x1] = np.maximum(
            masks["vesicle_buds"][y0:y1, x0:x1], np.maximum(dome, collar))

    # Rafts are broad shallow islands whose internal bars become gate sites.
    for cx, cy, i in _sites(31, .781):
        a = (i * 1.17) % np.pi
        rx, ry = 11 + (i * 5) % 5, 5 + (i * 3) % 4
        raft, box, d2 = _stamp(h, cx, cy, rx, ry, .13, angle=a)
        x0, x1, y0, y1 = box
        masks["protein_rafts"][y0:y1, x0:x1] = np.maximum(
            masks["protein_rafts"][y0:y1, x0:x1], raft)
        gate = np.exp(-5.0 * d2) * (np.cos((d2 ** .5) * 12.0 + i) > .35)
        masks["channel_gates"][y0:y1, x0:x1] = np.maximum(
            masks["channel_gates"][y0:y1, x0:x1], gate.astype(np.float32))
        h[y0:y1, x0:x1] += gate * .10

    # Ruptures and exposed ends are short physical cuts with asymmetric lips.
    for cx, cy, i in _sites(46, .918):
        a = (i * 2.13 + .4) % np.pi
        ax, ay, nx, ny = np.cos(a), np.sin(a), -np.sin(a), np.cos(a)
        length = 7 + (i * 7) % 8
        canvas = np.zeros((WORK, WORK), np.uint8)
        p0 = (int(cx - ax * length), int(cy - ay * length))
        p1 = (int(cx + ax * length), int(cy + ay * length))
        cv2.line(canvas, p0, p1, 255, 2 + i % 2, cv2.LINE_AA)
        cut = canvas.astype(np.float32) / 255.0
        h -= .24 * cut
        lip = np.zeros_like(canvas)
        q0 = (int(p0[0] + nx * 3), int(p0[1] + ny * 3))
        q1 = (int(p1[0] + nx * 3), int(p1[1] + ny * 3))
        cv2.line(lip, q0, q1, 255, 2, cv2.LINE_AA)
        lipf = lip.astype(np.float32) / 255.0
        h += .19 * lipf
        masks["rupture_lips"] = np.maximum(masks["rupture_lips"], np.maximum(cut, lipf))
        if i % 3 == 0:
            end = np.zeros_like(canvas)
            cv2.ellipse(end, p1, (4 + i % 4, 2 + i % 2), int(np.degrees(a)),
                        30, 330, 255, 2, cv2.LINE_AA)
            masks["exposed_ends"] = np.maximum(masks["exposed_ends"], end / 255.0)
            h += .17 * (end / 255.0)

    h = cv2.GaussianBlur(h, (0, 0), .72)
    return h, masks


def _ramp(t, colors):
    colors = np.asarray(colors, np.float32)
    u = np.clip(t, 0, 1) * (len(colors) - 1)
    i = np.minimum(u.astype(np.int32), len(colors) - 2)
    f = (u - i)[..., None]
    return colors[i] * (1 - f) + colors[i + 1] * f


def _render(angle_b=False):
    h, masks = _surface()
    gy, gx = np.gradient(h)
    nz = np.ones_like(h) * .72
    length = np.sqrt(gx * gx + gy * gy + nz * nz)
    nx, ny, nz = -gx / length, -gy / length, nz / length
    if angle_b:
        light = np.clip(nx * -.52 + ny * .31 + nz * .79, 0, 1)
        phase = _norm(.54 * h - .34 * nx + .52 * ny)
        palette = [(0.015, .035, .09), (.22, .02, .36), (.88, .08, .52),
                   (.98, .38, .12), (.90, .88, .18), (.20, .93, .62),
                   (.03, .55, .82), (.34, .12, .88), (.96, .18, .58)]
    else:
        light = np.clip(nx * .44 + ny * -.39 + nz * .81, 0, 1)
        phase = _norm(.54 * h + .43 * nx - .29 * ny)
        palette = [(0.005, .028, .05), (.01, .18, .26), (.02, .55, .62),
                   (.20, .88, .73), (.82, .96, .38), (.99, .66, .08),
                   (.90, .12, .38), (.35, .04, .52), (.02, .26, .40)]
    paint = _ramp(phase, palette)
    paint *= (.28 + .79 * light[..., None])
    rim = np.clip((1.0 - nz) ** 1.4, 0, 1)
    paint += rim[..., None] * np.asarray((.23, .88, 1.0) if not angle_b else
                                         (1.0, .30, .72), np.float32) * .46

    accents = {
        "fusion_saddles": ((.86, 1.0, .34), (.20, 1.0, .74), .34),
        "open_pores": ((.01, .025, .04), (.02, .01, .05), .58),
        "vesicle_buds": ((.94, .98, .72), (1.0, .42, .16), .31),
        "protein_rafts": ((.99, .48, .08), (.98, .13, .62), .22),
        "channel_gates": ((.99, .91, .22), (.48, 1.0, .64), .48),
        "rupture_lips": ((.96, .30, .35), (.32, .77, 1.0), .36),
        "exposed_ends": ((.88, .98, 1.0), (1.0, .82, .29), .54),
    }
    for name, (ca, cb, alpha) in accents.items():
        mask = masks[name][..., None]
        color = np.asarray(cb if angle_b else ca, np.float32)
        paint = paint * (1 - mask * alpha) + color * mask * alpha
    return np.clip(paint, 0, 1), h, masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/cyan_membrane_relief_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, _height, masks = _render(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _height, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID, "module": __name__, "attempt": 77,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float((mask > .08).mean()) for name, mask in masks.items()},
        "owner_accepted": False, "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-cyan-membrane-relief-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
