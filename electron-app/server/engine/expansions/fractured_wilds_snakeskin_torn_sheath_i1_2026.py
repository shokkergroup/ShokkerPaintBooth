# -*- coding: utf-8 -*-
"""Isolated native-2048 Snakeskin torn-sheath study.

SPB-105 / Wilds attempt 88 / 2026-08-25. One continuous shed membrane is torn
through an off-canvas chronology into lifted area-forming flaps. Exposed
underlayer, hinge lips, curled rims, adhesive bridges, split fibrils, ghost
windows, stress-white notches and healed stops remain attached to that tear.
There is no diamond/hex scale wallpaper, site scatter, sampled noise, shredded
rail cluster, paver, recolour fallback or shared composer. All local edges and
bridges are 8--32 px at native; large form emerges only from connected flaps.

Native-2048 verdict: REJECTED. The connected flaps become giant leaf/ribbon
panels crossed by thick black roads; bridges, fibrils, windows, notches and
stops collapse into tiny decoration. It reads as a panel collage, not layered
shed material. Frozen before spec/M7/runtime. No flap, spine, width, palette,
substrate, event, density, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fc_snakeskin"
ATTEMPT = 88
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (3, 7, 17), (5, 20, 38), (6, 40, 60), (7, 65, 77),
    (10, 93, 85), (18, 123, 85), (33, 153, 79), (55, 181, 70),
    (84, 204, 66), (119, 220, 72), (158, 230, 88), (196, 229, 113),
    (224, 214, 146), (240, 184, 184), (227, 143, 225),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (18, 3, 25), (42, 4, 49), (71, 6, 68), (101, 10, 80),
    (132, 17, 86), (163, 29, 87), (191, 45, 83), (216, 66, 77),
    (235, 91, 74), (247, 121, 77), (248, 155, 89), (238, 188, 111),
    (214, 216, 141), (177, 231, 177), (128, 229, 211),
], np.float32) / 255.0


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _spine(t):
    t = np.asarray(t, np.float32)
    x = -92.0 + 1220.0 * t + 67.0 * np.sin(2.2 * np.pi * t + .31)
    y = 892.0 - 706.0 * t + 116.0 * np.sin(3.1 * np.pi * t - .44)
    dx = 1220.0 + 67.0 * 2.2 * np.pi * np.cos(2.2 * np.pi * t + .31)
    dy = -706.0 + 116.0 * 3.1 * np.pi * np.cos(3.1 * np.pi * t - .44)
    length = np.sqrt(dx * dx + dy * dy) + 1e-6
    tx, ty = dx / length, dy / length
    return np.stack((x, y), axis=-1), np.stack((tx, ty), axis=-1)


def _ribbon(t0, t1, side, width0, width1, bow):
    t = np.linspace(t0, t1, 26, dtype=np.float32)
    centre, tangent = _spine(t)
    normal = np.stack((-tangent[:, 1], tangent[:, 0]), axis=1) * side
    q = np.linspace(0, 1, len(t), dtype=np.float32)
    width = width0 + (width1 - width0) * q + bow * np.sin(q * np.pi)
    outer = centre + normal * width[:, None]
    # Unequal lip corrugation changes actual silhouette, not only color.
    outer += normal * (6.0 * np.sin(7.0 * q + t0 * 13.0)
                       + 3.0 * np.sin(19.0 * q + side))[:, None]
    poly = np.concatenate((centre, outer[::-1]), axis=0)
    return np.rint(poly).astype(np.int32), np.rint(centre).astype(np.int32), np.rint(outer).astype(np.int32)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Calm, continuous thin-film substrate; its contrast is deliberately low
    # so the explicit tear chronology remains the buyer-visible carrier.
    fold = (.16 * np.sin((xx + .37 * yy) / 91.0)
            + .11 * np.sin((yy - .23 * xx) / 63.0)
            + .07 * np.cos((xx + yy) / 37.0))
    gy, gx = np.gradient(fold)
    travel = (np.arctan2(gy, gx) / (2 * np.pi) + .5
              + (.22 if angle_b else 0.0)) % 1.0
    paint = _ramp(travel, palette) * (.12 + .17 * (fold[..., None] + .4))

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "continuous_sheath", "exposed_underlayer", "lifted_flaps", "hinge_lips",
        "curled_rims", "adhesive_bridges", "split_fibrils", "ghost_windows",
        "stress_white_notches", "healed_stops")}
    masks["continuous_sheath"][:] = 255

    segments = (
        (.00, .18, -1, 58, 132, 44), (.09, .30, 1, 73, 158, 36),
        (.19, .42, -1, 92, 187, 61), (.31, .55, 1, 64, 151, 53),
        (.44, .68, -1, 84, 198, 47), (.57, .79, 1, 71, 169, 68),
        (.69, .91, -1, 65, 154, 39), (.80, 1.00, 1, 94, 178, 55),
    )
    flap_records = []
    for j, (t0, t1, side, w0, w1, bow) in enumerate(segments):
        poly, centre, outer = _ribbon(t0, t1, side, w0, w1, bow)
        mask = np.zeros((WORK, WORK), np.uint8)
        cv2.fillPoly(mask, [poly], 255, cv2.LINE_AA)
        # Flap optical depth varies perpendicular to its hinge and by chronology.
        distance = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
        distance /= float(distance.max()) + 1e-6
        phase = (distance * (.61 + .09 * j) + (xx * .00071 + yy * .00043)
                 + .087 * j + (.24 if angle_b else 0.0)) % 1.0
        color = _ramp(phase, palette)
        shade = .42 + .46 * distance + .10 * np.sin((xx - yy) / (41 + 3 * j))
        active = mask > 0
        paint[active] = color[active] * shade[active, None]
        masks["lifted_flaps"] = np.maximum(masks["lifted_flaps"], mask)
        cv2.polylines(masks["hinge_lips"], [centre], False, 255, 5 + j % 3, cv2.LINE_AA)
        cv2.polylines(masks["curled_rims"], [outer], False, 255, 4 + (j + 1) % 3, cv2.LINE_AA)
        cv2.polylines(paint, [centre], False, (0.003, 0.005, 0.012), 7 + j % 3, cv2.LINE_AA)
        cv2.polylines(paint, [centre], False,
                      tuple(float(v) for v in np.clip(palette[(j * 3 + 11) % 15] * 1.16, 0, 1)),
                      2, cv2.LINE_AA)
        cv2.polylines(paint, [outer], False,
                      tuple(float(v) for v in np.clip(palette[(j * 5 + 8) % 15] * 1.19, 0, 1)),
                      3, cv2.LINE_AA)
        flap_records.append((j, centre, outer, side))

    full_spine = np.rint(_spine(np.linspace(-.04, 1.04, 240, dtype=np.float32))[0]).astype(np.int32)
    cv2.polylines(paint, [full_spine], False, (0.002, 0.003, 0.008), 13, cv2.LINE_AA)
    cv2.polylines(masks["exposed_underlayer"], [full_spine], False, 255, 13, cv2.LINE_AA)

    # Short attached events bridge or fracture the actual flap boundaries.
    for j, centre, outer, side in flap_records:
        for k in range(3, 23, 3 + j % 2):
            if k >= len(centre):
                break
            a = centre[k].astype(np.float32)
            b = outer[min(len(outer) - 1, k)].astype(np.float32)
            vec = b - a
            frac = .18 + .55 * (((j * 11 + k * 7) % 17) / 16.0)
            p = a + vec * frac
            unit = vec / (np.linalg.norm(vec) + 1e-6)
            tangent = np.asarray((-unit[1], unit[0]), np.float32)
            if (j + k) % 3 == 0:
                p0, p1 = p - tangent * (3 + j % 4), p + tangent * (4 + k % 5)
                cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                         tuple(float(v) for v in np.clip(palette[(j + k + 10) % 15] * 1.2, 0, 1)),
                         3, cv2.LINE_AA)
                cv2.line(masks["adhesive_bridges"], tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 3, cv2.LINE_AA)
            else:
                p0, p1 = p, p + unit * (5 + (j * k) % 8)
                cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                         (0.003, 0.005, 0.011), 2, cv2.LINE_AA)
                cv2.line(masks["split_fibrils"], tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 2, cv2.LINE_AA)
        # Ghost windows and stress notches remain inside their parent flap.
        for k in (7, 14, 20):
            if k >= len(centre):
                continue
            p = centre[k] * .35 + outer[k] * .65
            axes = (5 + (j + k) % 4, 2 + j % 3)
            ang = int(np.degrees(np.arctan2(*(outer[k] - centre[k])[::-1])))
            cv2.ellipse(paint, tuple(np.rint(p).astype(int)), axes, ang, 0, 360,
                        (0.007, 0.012, 0.019), 2, cv2.LINE_AA)
            cv2.ellipse(masks["ghost_windows"], tuple(np.rint(p).astype(int)), axes,
                        ang, 0, 360, 255, 2, cv2.LINE_AA)
            n0 = p + np.asarray((3 * side, -4), np.float32)
            n1 = n0 + np.asarray((6 + j % 4, 3 * side), np.float32)
            cv2.line(paint, tuple(np.rint(n0).astype(int)), tuple(np.rint(n1).astype(int)),
                     tuple(float(v) for v in np.clip(palette[(j + 12) % 15] * 1.2, 0, 1)),
                     2, cv2.LINE_AA)
            cv2.line(masks["stress_white_notches"], tuple(np.rint(n0).astype(int)),
                     tuple(np.rint(n1).astype(int)), 255, 2, cv2.LINE_AA)
        stop = tuple(centre[-3])
        cv2.circle(paint, stop, 4 + j % 3,
                   tuple(float(v) for v in np.clip(palette[(j * 2 + 9) % 15] * 1.17, 0, 1)),
                   2, cv2.LINE_AA)
        cv2.circle(masks["healed_stops"], stop, 4 + j % 3, 255, 2, cv2.LINE_AA)
    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/snakeskin_torn_sheath_i1")
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
    crop = native_a[704:1344, 704:1344]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {"id": ID, "module": __name__, "attempt": ATTEMPT,
              "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
              "timings_s": timings,
              "deterministic": bool(all(np.array_equal(repeats[0], x) for x in repeats[1:])),
              "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
              "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, .95)),
              "coverage": {k: float((v > 8).mean()) for k, v in masks.items()},
              "owner_accepted": False, "production_wired": False}
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-snakeskin-torn-sheath-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
