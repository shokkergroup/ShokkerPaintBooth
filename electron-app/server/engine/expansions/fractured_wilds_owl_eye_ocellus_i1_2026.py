# -*- coding: utf-8 -*-
"""Isolated native-2048 Owl Eye eccentric-ocellus study.

SPB-105 / Wilds attempt 86 / 2026-08-25.  One off-centre close-cropped
teardrop ocellus emerges from six independently shifted/rotated superelliptic
layers rather than concentric targets.  Fine layer-owned scales, broken eyelid
bars, feather combs, glint cuts, rupture gaps, hooked scars and compressed
wedges provide 8--32 px anatomy.  Two independent irrational placement axes
avoid the phase-locked lanes found in attempt 82; marks remain causal to the
ocellus layer rather than random-noise uniqueness.

Native verdict: KEEP-CANDIDATE-I1 / EXPERIMENTAL OWNER TEST. The damaged
ocellus remains one off-centre non-concentric material hierarchy rather than a
recoloured flow field: exact paint is `1.658-1.844 s`, A/B mean/p95 is
`0.296110/0.756863`, and independent eight-tier M/R/Cc span `12-246 / 20-250 /
8-252`, std `72.109/77.390/79.815`, correlations `+0.024/+0.093/+0.054`.
Official isolated M7 is `91.3`; comparison to the prior 16 survivors finds no
actionable collision (max paint `0.246964`, max spec `0.053950`). Not owner
accepted; runtime exposure remains reversible.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_owl_eye"
ATTEMPT = 86
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (2, 5, 15), (5, 13, 34), (8, 27, 54), (12, 48, 69),
    (17, 73, 78), (27, 101, 80), (45, 130, 76), (70, 158, 68),
    (101, 184, 62), (138, 204, 65), (177, 217, 79), (211, 217, 104),
    (234, 199, 139), (243, 166, 181), (224, 128, 222),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (18, 2, 24), (43, 3, 47), (73, 5, 66), (104, 8, 78),
    (136, 14, 84), (168, 25, 87), (198, 41, 86), (222, 61, 82),
    (240, 86, 79), (249, 117, 82), (248, 152, 93), (235, 187, 113),
    (209, 216, 142), (169, 231, 178), (119, 228, 211),
], np.float32) / 255.0

LAYERS = (
    # cx, cy, rx, ry, rotation, exponent, angular dent
    (405., 522., 830., 690., -.17, 1.65, .13),
    (372., 501., 663., 552., .09, 1.82, -.10),
    (430., 548., 512., 423., -.28, 2.15, .16),
    (346., 485., 365., 304., .21, 1.58, -.14),
    (418., 544., 226., 188., -.36, 2.32, .09),
    (332., 496., 105., 146., .31, 1.44, -.08),
)


def _geometry():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    qs, angles = [], []
    for cx, cy, rx, ry, rot, power, dent in LAYERS:
        cr, sr = np.cos(rot), np.sin(rot)
        dx, dy = xx - cx, yy - cy
        u, v = dx * cr + dy * sr, -dx * sr + dy * cr
        angle = np.arctan2(v / ry, u / rx)
        q = (np.abs(u / rx) ** power + np.abs(v / ry) ** power) ** (1.0 / power)
        q /= np.clip(1.0 + dent * np.cos(angle) + .055 * np.sin(3 * angle + rot), .72, 1.28)
        qs.append(q.astype(np.float32))
        angles.append(angle.astype(np.float32))
    zone = np.zeros((WORK, WORK), np.uint8)
    for index, q in enumerate(qs, 1):
        zone[q < 1.0] = index
    return zone, qs, angles


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    zone, qs, angles = _geometry()
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    paint = np.zeros((WORK, WORK, 3), np.float32)
    base = np.asarray((.003, .006, .014) if not angle_b else (.014, .002, .020), np.float32)
    paint[:] = base
    # Each anatomical layer receives a different contiguous palette bank and
    # its own angular/normal response.  There is no global radial ramp.
    for z in range(1, 7):
        mask = zone == z
        angle = angles[z - 1]
        q = qs[z - 1]
        phase = ((angle / (2 * np.pi) + .5) * (2.3 + .41 * z)
                 + (1.0 - q) * (.67 + .19 * z) + .071 * z
                 + (.23 if angle_b else 0.0)) % 1.0
        u = phase * 14
        i = np.minimum(u.astype(np.int32), 13)
        f = (u - i)[..., None]
        color = palette[i] * (1 - f) + palette[i + 1] * f
        shade = .43 + .52 * np.clip(1.0 - .62 * q + .31 * np.cos(angle - (1.9 if angle_b else .4)), 0, 1)
        paint[mask] = color[mask] * shade[mask, None]

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "ocellus_layers", "layer_scales", "broken_eyelid_bars", "feather_combs",
        "glint_cuts", "rupture_gaps", "hooked_scars", "compressed_wedges")}
    masks["ocellus_layers"][zone > 0] = 255

    alpha, beta = np.sqrt(2.0) - 1.0, np.sqrt(3.0) - 1.0
    count = 12800
    for i in range(count):
        x = int(((i * alpha + .173) % 1.0) * WORK)
        y = int(((i * beta + .319) % 1.0) * WORK)
        z = int(zone[y, x])
        if z == 0:
            continue
        angle = float(angles[z - 1][y, x]) + np.pi * .5
        tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        half = 2.0 + ((i * 11 + z * 5) % 7) * .52
        width = 1 + ((i + z) % 3)
        centre = np.asarray((x, y), np.float32)
        p0 = centre - tangent * half + normal * np.sin(i * 1.71) * 1.3
        p1 = centre + tangent * half
        pidx = (i * 5 + z * 2 + (4 if angle_b else 0)) % 15
        color = tuple(float(v) for v in np.clip(palette[pidx] * 1.12, 0, 1))
        cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                 color, width, cv2.LINE_AA)
        cv2.line(masks["layer_scales"], tuple(np.rint(p0).astype(int)),
                 tuple(np.rint(p1).astype(int)), 255, width, cv2.LINE_AA)

    # Non-concentric layer lips remain broken and unequal rather than forming
    # a clean target. Only selected arcs are exposed.
    for z, q in enumerate(qs, 1):
        edge = np.uint8(np.abs(q - 1.0) < (.004 + .001 * z)) * 255
        gate = np.cos(angles[z - 1] * (2 + z % 3) + z * .91) > (-.18 + .07 * z)
        broken = cv2.bitwise_and(edge, edge, mask=np.uint8(gate) * 255)
        color = tuple(float(v) for v in np.clip(palette[(3 * z + 7) % 15] * 1.15, 0, 1))
        paint[broken > 0] = color
        masks["broken_eyelid_bars"] = np.maximum(masks["broken_eyelid_bars"], broken)

    # Attached feather-comb packets live outside the moving eyelid, not as a
    # second full-card line field.
    for j in range(84):
        theta = -2.56 + j * .049
        root = np.asarray((405 + 835 * np.cos(theta), 522 + 694 * np.sin(theta)), np.float32)
        direction = np.asarray((np.cos(theta + .19 * np.sin(j)),
                                np.sin(theta + .19 * np.sin(j))), np.float32)
        length = 8 + (j * 13) % 9
        p1 = root + direction * length
        cv2.line(paint, tuple(np.rint(root).astype(int)), tuple(np.rint(p1).astype(int)),
                 tuple(float(v) for v in np.clip(palette[(j + 10) % 15] * 1.12, 0, 1)),
                 3, cv2.LINE_AA)
        cv2.line(masks["feather_combs"], tuple(np.rint(root).astype(int)),
                 tuple(np.rint(p1).astype(int)), 255, 3, cv2.LINE_AA)

    # Glints, rupture gaps, hooked scars and wedges attach to the pupil/eyelid
    # chronology and each use a different silhouette.
    for j, (x, y, ang) in enumerate(((274, 426, -18), (350, 501, 21), (432, 557, -33),
                                      (502, 616, 12), (217, 535, 39), (391, 392, -9))):
        p0 = (x - 4 - j % 3, y - 2)
        p1 = (x + 5 + j % 4, y + 2)
        cv2.rectangle(paint, p0, p1,
                      tuple(float(v) for v in np.clip(palette[(j * 3 + 11) % 15] * 1.22, 0, 1)),
                      -1, cv2.LINE_AA)
        cv2.rectangle(masks["glint_cuts"], p0, p1, 255, -1, cv2.LINE_AA)
        cv2.ellipse(paint, (x + 16, y - 13), (6 + j % 3, 3), ang, 25, 255,
                    tuple(float(v) for v in base), 3, cv2.LINE_AA)
        cv2.ellipse(masks["hooked_scars"], (x + 16, y - 13), (6 + j % 3, 3),
                    ang, 25, 255, 255, 3, cv2.LINE_AA)
    for j, (x, y) in enumerate(((538, 359), (573, 445), (531, 524), (454, 660), (278, 674))):
        cv2.ellipse(paint, (x, y), (8 + j % 4, 3 + j % 2), j * 23, 0, 360,
                    tuple(float(v) for v in base), -1, cv2.LINE_AA)
        cv2.ellipse(masks["rupture_gaps"], (x, y), (8 + j % 4, 3 + j % 2),
                    j * 23, 0, 360, 255, -1, cv2.LINE_AA)
        pts = np.asarray(((x - 3, y + 5), (x + 7, y + 8), (x + 2, y + 14)), np.int32)
        cv2.fillConvexPoly(paint, pts,
                           tuple(float(v) for v in np.clip(palette[(j * 2 + 8) % 15] * 1.18, 0, 1)),
                           cv2.LINE_AA)
        cv2.fillConvexPoly(masks["compressed_wedges"], pts, 255, cv2.LINE_AA)
    return np.clip(paint, 0, 1), masks


M_TIERS = np.asarray((12, 38, 69, 104, 142, 179, 216, 246), np.uint8)
R_TIERS = np.asarray((20, 46, 74, 108, 144, 182, 221, 250), np.uint8)
CC_TIERS = np.asarray((8, 31, 59, 94, 132, 171, 213, 252), np.uint8)


def _spec_maps(masks):
    """Independent tier histories from eccentric layer anatomy."""
    zone, qs, angles = _geometry()
    z = zone.astype(np.int16)
    angular = np.zeros_like(z)
    radial = np.zeros_like(z)
    for k in range(1, 7):
        active = z == k
        angular[active] = np.mod(((angles[k - 1][active] / (2 * np.pi) + .5) * 19), 8).astype(np.int16)
        radial[active] = np.clip(qs[k - 1][active] * 8, 0, 7).astype(np.int16)
    metal_i = (3 * z + angular * angular + 5 * radial + z * radial) % 8
    rough_i = (z * z + 5 * angular + 3 * radial * radial + angular * radial) % 8
    coat_i = (7 * z + 3 * angular * angular + radial + 5 * z * angular) % 8
    event = {name: mask > 22 for name, mask in masks.items()}

    metal_i[event["broken_eyelid_bars"]] = (angular[event["broken_eyelid_bars"]] + 6) % 8
    metal_i[event["glint_cuts"]] = 7
    metal_i[event["rupture_gaps"]] = 0
    metal_i[event["compressed_wedges"]] = 6

    rough_i[event["layer_scales"]] = (radial[event["layer_scales"]] + 3) % 8
    rough_i[event["rupture_gaps"]] = 7
    rough_i[event["hooked_scars"]] = 6
    rough_i[event["glint_cuts"]] = 1
    rough_i[event["feather_combs"]] = (angular[event["feather_combs"]] + 4) % 8

    coat_i[event["broken_eyelid_bars"]] = (z[event["broken_eyelid_bars"]] + 4) % 8
    coat_i[event["glint_cuts"]] = 7
    coat_i[event["rupture_gaps"]] = 0
    coat_i[event["hooked_scars"]] = 2
    coat_i[event["compressed_wedges"]] = 5
    return M_TIERS[metal_i], R_TIERS[rough_i], CC_TIERS[coat_i]


def _authored():
    paint, masks = _render(False)
    metal, rough, coat = _spec_maps(masks)
    spec = np.stack((metal, rough, coat), axis=2)
    return _native(paint), cv2.resize(spec, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/owl_eye_ocellus_i1")
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
    metal, rough, coat = _spec_maps(masks)
    spec_work = np.stack((metal, rough, coat), axis=2)
    spec_native = cv2.resize(spec_work, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    for name, channel in zip(("metallic", "roughness", "clearcoat"), cv2.split(spec_native)):
        cv2.imwrite(str(out / f"{ID}_{name}_2048.png"), channel)
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    flat = spec_native.reshape(-1, 3).astype(np.float32)
    corr = np.corrcoef(flat, rowvar=False)
    report = {
        "id": ID, "module": __name__, "attempt": ATTEMPT,
        "status": "KEEP-CANDIDATE-I1-EXPERIMENTAL-OWNER-TEST",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float((mask > 8).mean()) for name, mask in masks.items()},
        "spec_ranges": {name: [int(flat[:, i].min()), int(flat[:, i].max())]
                        for i, name in enumerate(("M", "R", "Cc"))},
        "spec_std": {name: float(flat[:, i].std())
                     for i, name in enumerate(("M", "R", "Cc"))},
        "spec_correlations": {"M_R": float(corr[0, 1]), "M_Cc": float(corr[0, 2]),
                              "R_Cc": float(corr[1, 2])},
        "owner_accepted": False, "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-owl-eye-ocellus-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
