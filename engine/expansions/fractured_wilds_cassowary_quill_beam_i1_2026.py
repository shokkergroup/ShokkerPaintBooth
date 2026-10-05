# -*- coding: utf-8 -*-
"""Isolated native-2048 Cassowary Quill hollow-beam-fabric study.

SPB-105 / Wilds attempt 96 / 2026-08-25. Unequal hollow rachis beams bend,
cross, buckle and terminate into one full-frame fabric. Each beam owns a lumen
slit, flange ribs and barb sockets; crossings own shear joints and pin plates;
snapped ends own collars, splinters and repair bridges. No sampled noise, quill
stamp, parallel comb, simple rail wallpaper, generic weave, branch field,
recolour fallback or shared composer is used. Primitive widths are 8--32 px
native and Fractured A/B changes optical beam faces without moving geometry.

Native-2048 verdict: REJECTED. The full-size carrier reads as colored cable
spaghetti over a black ground; ring joints and small accessories are only
decoration. Frozen with no curve/beam/count/width/palette/joint/accessory/
density/crop/scale/spec/noise repair authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_cassowary_quill"
ATTEMPT = 96
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (3, 5, 14), (7, 15, 33), (12, 31, 52), (17, 52, 68), (22, 76, 77),
    (30, 102, 78), (42, 129, 73), (58, 156, 65), (78, 181, 57),
    (103, 202, 55), (132, 218, 66), (165, 226, 86), (198, 225, 114),
    (225, 212, 150), (241, 190, 194),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (20, 2, 28), (49, 3, 54), (79, 5, 74), (110, 8, 88), (141, 13, 95),
    (172, 21, 97), (201, 33, 93), (224, 49, 87), (240, 70, 82),
    (249, 96, 82), (250, 127, 91), (245, 159, 109), (232, 190, 135),
    (210, 215, 167), (178, 233, 205),
], np.float32) / 255.0


def _bezier(p0, p1, p2, p3, count=220):
    t = np.linspace(0, 1, count, dtype=np.float32)
    q = 1 - t
    pts = (q[:, None] ** 3 * p0 + 3 * q[:, None] ** 2 * t[:, None] * p1
           + 3 * q[:, None] * t[:, None] ** 2 * p2 + t[:, None] ** 3 * p3)
    tangent = np.gradient(pts, axis=0)
    length = np.linalg.norm(tangent, axis=1) + 1e-6
    tangent /= length[:, None]
    normal = np.stack((-tangent[:, 1], tangent[:, 0]), axis=1)
    return pts, tangent, normal


def _beam_specs():
    specs = []
    # Cross-canvas beams: endpoints and controls use independent modular
    # schedules, preventing a regular parallel family.
    for j in range(13):
        p0 = np.asarray((-70.0, -30 + (j * 83) % 1110), np.float32)
        p3 = np.asarray((1090.0, 35 + (j * 137 + 191) % 1040), np.float32)
        p1 = np.asarray((185 + (j * 47) % 260, -120 + (j * 181) % 1250), np.float32)
        p2 = np.asarray((590 + (j * 71) % 300, -90 + (j * 233) % 1220), np.float32)
        specs.append((p0, p1, p2, p3, 6 + (j * 5) % 9, j))
    for j in range(10):
        p0 = np.asarray((-30 + (j * 119) % 1080, -75.0), np.float32)
        p3 = np.asarray((45 + (j * 173 + 101) % 1030, 1092.0), np.float32)
        p1 = np.asarray((-110 + (j * 227) % 1240, 180 + (j * 43) % 290), np.float32)
        p2 = np.asarray((-90 + (j * 281) % 1210, 590 + (j * 61) % 280), np.float32)
        specs.append((p0, p1, p2, p3, 7 + (j * 7) % 8, 20 + j))
    # Seven deliberately terminated beams create snapped internal ends rather
    # than another edge-to-edge rail set.
    for j in range(7):
        side = -1 if j % 2 else 1
        p0 = np.asarray((-65.0 if side > 0 else 1089.0, 95 + j * 137), np.float32)
        p3 = np.asarray((276 + (j * 113) % 510, 181 + (j * 157) % 690), np.float32)
        p1 = p0 + np.asarray((side * (230 + j * 17), -170 + j * 59), np.float32)
        p2 = p3 - np.asarray((side * (150 + j * 13), 120 - j * 21), np.float32)
        specs.append((p0, p1, p2, p3, 8 + (j * 3) % 7, 40 + j))
    return specs


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    base_order = (xx * .00031 + yy * .00023 + (.19 if angle_b else 0)) % 1
    paint = palette[(base_order * 14).astype(np.int32)] * .055
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "hollow_beam_fabric", "lumen_slits", "flange_ribs", "barb_sockets",
        "shear_joints", "pin_plates", "buckling_folds", "snapped_ends",
        "repair_collars", "splinter_fans", "repair_bridges")}

    records = []
    for beam_index, (p0, p1, p2, p3, width, lineage) in enumerate(_beam_specs()):
        pts, tangent, normal = _bezier(p0, p1, p2, p3)
        # Attached buckling is a localized displacement of the actual beam axis.
        t = np.linspace(0, 1, len(pts), dtype=np.float32)
        buckle_center = .19 + .61 * (((lineage * 37) % 101) / 100.0)
        envelope = np.exp(-((t - buckle_center) / (.055 + .018 * (lineage % 3))) ** 2)
        buckle = normal * (envelope * (5 + lineage % 7) * np.sin((t - buckle_center) * 94 + lineage))[:, None]
        pts = pts + buckle
        poly = np.rint(pts).astype(np.int32)
        dark = tuple(float(v) for v in np.clip(palette[(lineage * 3 + 1) % 15] * .19, 0, 1))
        cv2.polylines(paint, [poly], False, dark, width + 6, cv2.LINE_AA)
        cv2.polylines(masks["hollow_beam_fabric"], [poly], False, 255, width + 6, cv2.LINE_AA)
        chunk = 18 + lineage % 9
        for start in range(0, len(poly) - 1, chunk):
            segment = poly[start:min(len(poly), start + chunk + 1)]
            optical = (start // chunk * 5 + lineage * 7 + (9 if angle_b else 0)) % 15
            color = tuple(float(v) for v in np.clip(palette[optical] * (.61 + .07 * (lineage % 4)), 0, 1))
            cv2.polylines(paint, [segment], False, color, width, cv2.LINE_AA)
        # One dark lumen slit makes the beam materially hollow.
        cv2.polylines(paint, [poly], False, (0.002, .003, .006), max(2, width // 3), cv2.LINE_AA)
        cv2.polylines(masks["lumen_slits"], [poly], False, 255, max(2, width // 3), cv2.LINE_AA)

        for k in range(13 + lineage % 7, len(pts) - 8, 19 + (lineage * 3) % 13):
            c = pts[k]
            tg, nm = tangent[k], normal[k]
            family = (lineage + k // 7) % 4
            color = tuple(float(v) for v in np.clip(palette[(lineage + k + 11) % 15] * 1.18, 0, 1))
            if family == 0:  # flange rib
                a, b = c - nm * (width * .55 + 2), c + nm * (width * .55 + 2)
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), color, 3, cv2.LINE_AA)
                cv2.line(masks["flange_ribs"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)
            elif family == 1:  # socket
                socket = c + nm * (width * .38 * (-1 if k % 2 else 1))
                cv2.circle(paint, tuple(np.rint(socket).astype(int)), 3 + lineage % 3, (0.002, .003, .006), 2, cv2.LINE_AA)
                cv2.circle(masks["barb_sockets"], tuple(np.rint(socket).astype(int)), 3 + lineage % 3, 255, 2, cv2.LINE_AA)
            elif family == 2:  # buckle fold marker derived from displaced axis
                if envelope[k] > .22:
                    a, b = c - tg * 6 - nm * 4, c + tg * 7 + nm * 5
                    cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), color, 3, cv2.LINE_AA)
                    cv2.line(masks["buckling_folds"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)
            else:  # fine brace
                a, b = c - tg * 4 - nm * 5, c + tg * 5 + nm * 5
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), color, 2, cv2.LINE_AA)
                cv2.line(masks["repair_bridges"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 2, cv2.LINE_AA)

        terminated = lineage >= 40
        if terminated:
            end = pts[-1]
            tg, nm = tangent[-1], normal[-1]
            cv2.circle(paint, tuple(np.rint(end).astype(int)), width // 2 + 3, (0.002, .003, .006), 3, cv2.LINE_AA)
            cv2.circle(masks["snapped_ends"], tuple(np.rint(end).astype(int)), width // 2 + 3, 255, 3, cv2.LINE_AA)
            cv2.ellipse(paint, tuple(np.rint(end - tg * 6).astype(int)), (width + 4, 4 + lineage % 3),
                        int(np.degrees(np.arctan2(tg[1], tg[0]))), 0, 360,
                        tuple(float(v) for v in np.clip(palette[(lineage + 12) % 15] * 1.17, 0, 1)), 3, cv2.LINE_AA)
            cv2.ellipse(masks["repair_collars"], tuple(np.rint(end - tg * 6).astype(int)),
                        (width + 4, 4 + lineage % 3), 0, 0, 360, 255, 3, cv2.LINE_AA)
            for s in (-2, -1, 1, 2):
                a = end + nm * s * 3
                b = a + tg * (8 + (lineage + s) % 8) + nm * s * 2
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                         tuple(float(v) for v in np.clip(palette[(lineage + s + 9) % 15] * 1.2, 0, 1)), 2, cv2.LINE_AA)
                cv2.line(masks["splinter_fans"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 2, cv2.LINE_AA)
        records.append((pts, tangent, normal, width, lineage))

    # Deterministic pairwise crossing joints: only true axis proximities receive
    # a joint, so plates cannot become a scattered symbol layer.
    sample_records = [(pts[::13], width, lineage) for pts, _tg, _nm, width, lineage in records]
    joints = []
    for a in range(len(sample_records)):
        pa, wa, la = sample_records[a]
        for b in range(a + 1, len(sample_records)):
            pb, wb, lb = sample_records[b]
            distances = np.sum((pa[:, None, :] - pb[None, :, :]) ** 2, axis=2)
            index = np.unravel_index(np.argmin(distances), distances.shape)
            if distances[index] < (6 + .35 * (wa + wb)) ** 2:
                c = (pa[index[0]] + pb[index[1]]) * .5
                if all(np.linalg.norm(c - q) > 31 for q in joints):
                    joints.append(c)
    for j, c in enumerate(joints[:47]):
        centre = tuple(np.rint(c).astype(int))
        axes = (6 + j % 5, 4 + (j * 3) % 4)
        cv2.ellipse(paint, centre, axes, (j * 37) % 180, 0, 360,
                    tuple(float(v) for v in np.clip(palette[(j * 4 + 12) % 15] * 1.16, 0, 1)), 3, cv2.LINE_AA)
        cv2.ellipse(masks["shear_joints"], centre, axes, (j * 37) % 180, 0, 360, 255, 3, cv2.LINE_AA)
        cv2.line(paint, (centre[0] - 4, centre[1]), (centre[0] + 5, centre[1]), (0.002, .003, .006), 3, cv2.LINE_AA)
        cv2.line(masks["pin_plates"], (centre[0] - 4, centre[1]), (centre[0] + 5, centre[1]), 255, 3, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/cassowary_quill_beam_i1")
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
    return "fractured-wilds-cassowary-quill-beam-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
