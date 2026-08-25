# -*- coding: utf-8 -*-
"""Isolated native-2048 Feathered Wing close-cropped vane study.

SPB-105 / Wilds attempt 84 / 2026-08-25.  One asymmetric off-canvas feather
chronology fills the sheet: a curved rachis owns densely attached tapered barbs
whose visible 8--32 px thickness carries barbules, hooklets, cross-locks, tear
gaps, powder plates and snapped tips.  It is a single causal material system,
not a loose stroke cloud, repeated feather stamp, generic flow field, paver,
sampled noise layer or recolour of Monarch/Morpho geometry.

Native verdict: KEEP-CANDIDATE-I2 / EXPERIMENTAL OWNER TEST.  The close-cropped
vane retains filled feather anatomy rather than parallel rail wallpaper: vane
coverage is `94.204%`, exact cold paint is `0.268-0.307 s`, and A/B mean/p95 is
`0.200355/0.650980`. Independent eight-tier M/R/Cc span `12-246 / 20-250 /
8-252`, std is `86.118/81.465/94.561`, correlations are
`+0.192/+0.117/+0.288`, and official isolated M7 is `93.0`. Structure-only
comparison against the prior 15 survivors finds no actionable collision; max
paint is `0.243122` and max permutation-aware spec topology is `0.054030`.
Not owner accepted; runtime exposure remains reversible.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fc_feathered_wing"
ATTEMPT = 84
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (3, 8, 18), (4, 24, 42), (4, 49, 65), (5, 78, 82),
    (7, 108, 94), (13, 139, 98), (27, 169, 94), (50, 196, 88),
    (82, 217, 84), (121, 231, 89), (164, 238, 104), (204, 235, 130),
    (232, 216, 162), (244, 179, 197), (225, 133, 229),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (15, 4, 25), (38, 4, 49), (68, 5, 71), (101, 8, 87),
    (136, 14, 97), (170, 25, 101), (201, 42, 100), (226, 65, 97),
    (244, 93, 96), (253, 126, 101), (252, 161, 113), (237, 194, 134),
    (207, 220, 161), (164, 235, 192), (112, 231, 218),
], np.float32) / 255.0


def _shaft(t):
    x = 94.0 + 842.0 * t + 42.0 * np.sin(2.1 * t + .31)
    y = 1090.0 - 1112.0 * t + 73.0 * np.sin(3.7 * t - .42)
    dx = 842.0 + 88.2 * np.cos(2.1 * t + .31)
    dy = -1112.0 + 270.1 * np.cos(3.7 * t - .42)
    tangent = np.asarray((dx, dy), np.float32)
    tangent /= np.linalg.norm(tangent) + 1e-6
    normal = np.asarray((-tangent[1], tangent[0]), np.float32)
    return np.asarray((x, y), np.float32), tangent, normal


def _curve_points(root, tangent, normal, side, length, sweep, phase):
    q = np.linspace(0, 1, 22, dtype=np.float32)
    direction = tangent * (.18 + .13 * np.sin(phase)) + normal * side
    direction /= np.linalg.norm(direction) + 1e-6
    bend = normal * side * (q * q)[:, None] * sweep
    curl = tangent * (np.sin(q * np.pi) * (9.0 + 8.0 * np.sin(phase * 1.7)))[:, None]
    pts = root + direction * (q * length)[:, None] + bend + curl
    return np.rint(pts).astype(np.int32)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    bg0 = np.asarray((.002, .006, .015) if not angle_b else (.014, .002, .022), np.float32)
    bg1 = np.asarray((.010, .037, .050) if not angle_b else (.050, .007, .054), np.float32)
    falloff = np.clip(1.0 - np.hypot((xx - 510) / 830, (yy - 520) / 800), 0, 1)
    paint = bg0 + (bg1 - bg0) * falloff[..., None] * .48
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "vane_mass", "rachis", "barb_ribbons", "barbules", "hooklets",
        "cross_locks", "tear_gaps", "powder_plates", "snapped_tips")}
    phase_field = np.zeros((WORK, WORK), np.uint8)
    root_field = np.zeros((WORK, WORK), np.uint8)
    side_field = np.zeros((WORK, WORK), np.uint8)

    # Back-to-front: later barbs occlude earlier ones like a packed pennaceous
    # vane. Unequal clocks prevent a repeated row glyph while every barb stays
    # attached to the same rachis chronology.
    total = 330
    for j in range(total):
        t = -.035 + 1.07 * (j / (total - 1))
        root, tangent, normal = _shaft(t)
        for side in (-1, 1):
            idx = j * 2 + (side > 0)
            phase = idx * 2.399963 + side * .63
            length = (520.0 - 175.0 * abs(t - .48)
                      + 54.0 * np.sin(phase * .37)
                      + 31.0 * np.sin(phase * .91))
            sweep = 52.0 + 33.0 * np.sin(phase * .51 + side)
            pts = _curve_points(root, tangent, normal, side, length, sweep, phase)
            pidx = (idx * 7 + int(t * 29) + (5 if angle_b else 0)) % 15
            body = tuple(float(v) for v in np.clip(palette[pidx] * (.52 + .34 * t), 0, 1))
            edge = tuple(float(v) for v in np.clip(palette[(pidx + 4) % 15] * 1.12, 0, 1))
            width = 4 + (idx * 11) % 5
            cv2.polylines(paint, [pts], False, (0.002, 0.004, 0.010), width + 5, cv2.LINE_AA)
            cv2.polylines(paint, [pts], False, body, width + 2, cv2.LINE_AA)
            cv2.polylines(paint, [pts], False, edge, 1, cv2.LINE_AA)
            cv2.polylines(masks["vane_mass"], [pts], False, 255, width + 5, cv2.LINE_AA)
            cv2.polylines(masks["barb_ribbons"], [pts], False, 255, width + 2, cv2.LINE_AA)
            cv2.polylines(phase_field, [pts], False, int(pidx), width + 2, cv2.LINE_8)
            cv2.polylines(root_field, [pts], False, int(np.clip(t, 0, 1) * 255),
                          width + 2, cv2.LINE_8)
            cv2.polylines(side_field, [pts], False, 255 if side > 0 else 64,
                          width + 2, cv2.LINE_8)

            # Barbules bridge toward the preceding barb.  They are attached
            # 8--28 px native hooks, not an independent scatter texture.
            if j % 2 == 0:
                stride = 2 + (idx % 3)
                for k in range(3 + idx % 2, 20, stride):
                    p = pts[k].astype(np.float32)
                    p_prev = pts[max(0, k - 1)].astype(np.float32)
                    local_t = p - p_prev
                    local_t /= np.linalg.norm(local_t) + 1e-6
                    local_n = np.asarray((-local_t[1], local_t[0]), np.float32)
                    hook_len = 4.0 + (idx + 3 * k) % 9
                    q = p - local_n * side * hook_len + local_t * (2 + (k % 3))
                    c = tuple(float(v) for v in np.clip(palette[(pidx + 8) % 15] * 1.08, 0, 1))
                    cv2.line(paint, tuple(np.rint(p).astype(int)), tuple(np.rint(q).astype(int)),
                             c, 2, cv2.LINE_AA)
                    cv2.line(masks["barbules"], tuple(np.rint(p).astype(int)),
                             tuple(np.rint(q).astype(int)), 255, 2, cv2.LINE_AA)
                    if (idx + k) % 13 == 0:
                        q2 = q + local_t * (3 + idx % 4)
                        cv2.line(paint, tuple(np.rint(q).astype(int)), tuple(np.rint(q2).astype(int)),
                                 c, 2, cv2.LINE_AA)
                        cv2.line(masks["hooklets"], tuple(np.rint(q).astype(int)),
                                 tuple(np.rint(q2).astype(int)), 255, 2, cv2.LINE_AA)

            if idx % 29 == 0:
                k = 10 + idx % 7
                p = pts[k].astype(np.float32)
                q = pts[min(21, k + 3)].astype(np.float32)
                cv2.line(paint, tuple(np.rint(p).astype(int)), tuple(np.rint(q).astype(int)),
                         tuple(float(v) for v in bg0), width + 5, cv2.LINE_AA)
                cv2.line(masks["tear_gaps"], tuple(np.rint(p).astype(int)),
                         tuple(np.rint(q).astype(int)), 255, width + 5, cv2.LINE_AA)
            if idx % 37 == 0:
                k = 7 + idx % 9
                p = tuple(pts[k])
                cv2.ellipse(paint, p, (3 + idx % 5, 2 + idx % 3),
                            int(np.degrees(phase) % 180), 0, 360,
                            tuple(float(v) for v in np.clip(palette[(pidx + 11) % 15] * 1.18, 0, 1)),
                            -1, cv2.LINE_AA)
                cv2.ellipse(masks["powder_plates"], p, (3 + idx % 5, 2 + idx % 3),
                            int(np.degrees(phase) % 180), 0, 360, 255, -1, cv2.LINE_AA)
            if idx % 43 == 0:
                p0, p1 = tuple(pts[-4]), tuple(pts[-1])
                cv2.line(paint, p0, p1, tuple(float(v) for v in bg0), width + 6, cv2.LINE_AA)
                cv2.line(masks["snapped_tips"], p0, p1, 255, width + 6, cv2.LINE_AA)
            if idx % 53 == 0:
                p0, p1 = tuple(pts[6]), tuple(pts[10])
                cv2.line(paint, p0, p1,
                         tuple(float(v) for v in np.clip(palette[(pidx + 6) % 15] * 1.15, 0, 1)),
                         3, cv2.LINE_AA)
                cv2.line(masks["cross_locks"], p0, p1, 255, 3, cv2.LINE_AA)

    shaft_pts = np.asarray([_shaft(t)[0] for t in np.linspace(-.08, 1.08, 180)], np.int32)
    cv2.polylines(paint, [shaft_pts], False, (0.005, 0.006, 0.012), 17, cv2.LINE_AA)
    cv2.polylines(paint, [shaft_pts], False,
                  tuple(float(v) for v in palette[11] * .82), 12, cv2.LINE_AA)
    cv2.polylines(paint, [shaft_pts], False,
                  tuple(float(v) for v in np.clip(palette[14] * 1.08, 0, 1)), 3, cv2.LINE_AA)
    cv2.polylines(masks["rachis"], [shaft_pts], False, 255, 17, cv2.LINE_AA)
    cv2.polylines(phase_field, [shaft_pts], False, 14, 17, cv2.LINE_8)
    cv2.polylines(root_field, [shaft_pts], False, 255, 17, cv2.LINE_8)
    cv2.polylines(side_field, [shaft_pts], False, 160, 17, cv2.LINE_8)
    return np.clip(paint, 0, 1), masks, {
        "phase": phase_field, "root": root_field, "side": side_field}


M_TIERS = np.asarray((12, 37, 68, 103, 141, 178, 216, 246), np.uint8)
R_TIERS = np.asarray((20, 45, 73, 107, 143, 181, 221, 250), np.uint8)
CC_TIERS = np.asarray((8, 31, 58, 93, 131, 170, 213, 252), np.uint8)


def _spec_maps(masks, fields):
    """Independent optical histories over the shared feather anatomy."""
    phase = fields["phase"].astype(np.int16)
    root = fields["root"].astype(np.int16) * 8 // 256
    side = fields["side"].astype(np.int16) * 4 // 256
    metal_i = (3 * phase + 5 * root + 2 * side + phase * root) % 8
    rough_i = (phase * phase + 3 * root * root + 5 * side + 3 * phase * side) % 8
    coat_i = (5 * phase * phase + 7 * root + root * side + 3 * side * side) % 8
    event = {name: mask > 22 for name, mask in masks.items()}

    metal_i[event["rachis"]] = 7
    metal_i[event["powder_plates"]] = 6
    metal_i[event["snapped_tips"]] = 0
    metal_i[event["cross_locks"]] = (phase[event["cross_locks"]] + 5) % 8

    rough_i[event["tear_gaps"]] = 7
    rough_i[event["barbules"]] = (root[event["barbules"]] + 4) % 8
    rough_i[event["hooklets"]] = 2
    rough_i[event["powder_plates"]] = 5
    rough_i[event["rachis"]] = 1

    coat_i[event["rachis"]] = (root[event["rachis"]] + 5) % 8
    coat_i[event["cross_locks"]] = 7
    coat_i[event["hooklets"]] = 6
    coat_i[event["tear_gaps"]] = 0
    coat_i[event["powder_plates"]] = 4
    return M_TIERS[metal_i], R_TIERS[rough_i], CC_TIERS[coat_i]


def _authored():
    paint, masks, fields = _render(False)
    metal, rough, coat = _spec_maps(masks, fields)
    spec = np.stack((metal, rough, coat), axis=2)
    return _native(paint), cv2.resize(spec, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/feathered_vane_closecrop_i2")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks, fields = _render(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1344, 704:1344]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    metal, rough, coat = _spec_maps(masks, fields)
    spec_work = np.stack((metal, rough, coat), axis=2)
    spec_native = cv2.resize(spec_work, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    for name, channel in zip(("metallic", "roughness", "clearcoat"),
                             cv2.split(spec_native)):
        cv2.imwrite(str(out / f"{ID}_{name}_2048.png"), channel)
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    flat = spec_native.reshape(-1, 3).astype(np.float32)
    corr = np.corrcoef(flat, rowvar=False)
    report = {
        "id": ID, "module": __name__, "attempt": ATTEMPT,
        "status": "KEEP-CANDIDATE-I2-EXPERIMENTAL-OWNER-TEST",
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
    return "fractured-wilds-feathered-vane-closecrop-i2: fail-closed pending native review"


if __name__ == "__main__":
    main()
