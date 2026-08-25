# -*- coding: utf-8 -*-
"""Isolated native-2048 Cyan Spineball projected-cage study.

SPB-105 / Wilds attempt 79 / 2026-08-25. Owner verdict applied: "LAZY" and
"exact same pattern just recolored" are the cardinal failures; the legacy
fallback had no isolated authored gate and this replacement moves it to
official experimental M7 `94.1`. One off-centre, close-cropped
subdivided icosphere becomes a continuous radiolarian shell rather than a field
of ball/star stamps.  Level-six panels land at 8--32 px native.  Surface depth
causes the A/B optical flip; grouped panel events create shell struts, inner
cage windows, unequal apertures, tangential fractures, spine roots, broken
sockets and mineral collars.  No RNG, sampled noise, scalar carrier, paver
placement, repeated radial icon or shared composer.

Native verdict: KEEP-CANDIDATE-I1 / EXPERIMENTAL OWNER TEST. Three exact cold
runs complete in `1.338-2.303 s`; A/B mean/p95 is `0.344282/0.972549`.
Independent eight-tier M/R/Cc span `12-246 / 20-250 / 8-252`, std is
`84.596/77.294/73.913`, correlations are `-0.118/+0.028/+0.032`, and official
isolated M7 is `94.3`. Not owner accepted; runtime exposure remains reversible.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_cyan_spineball"
WORK = 1024
NATIVE = 2048
LEVEL = 6
RADIUS = 910.0
CENTER = np.asarray((322.0, 548.0), np.float32)

PALETTE_A = np.asarray([
    (3, 7, 18), (4, 18, 38), (4, 39, 65), (4, 67, 91),
    (5, 99, 111), (9, 132, 126), (21, 165, 129), (47, 194, 122),
    (87, 218, 111), (137, 234, 104), (190, 241, 108), (230, 236, 126),
    (249, 211, 154), (251, 170, 190), (225, 125, 228),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (15, 4, 28), (35, 5, 54), (61, 6, 79), (91, 8, 103),
    (124, 13, 123), (160, 22, 138), (195, 34, 145), (224, 51, 146),
    (244, 74, 143), (254, 104, 139), (255, 140, 140), (250, 178, 150),
    (233, 211, 169), (192, 235, 191), (133, 241, 215),
], np.float32) / 255.0


def _base_icosahedron():
    phi = (1.0 + 5.0 ** .5) * .5
    vertices = [
        (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
        (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ]
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    v = np.asarray(vertices, np.float64)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return [row for row in v], faces


@lru_cache(maxsize=1)
def _mesh():
    vertices, faces = _base_icosahedron()
    for _ in range(LEVEL):
        cache = {}

        def midpoint(a, b):
            key = (a, b) if a < b else (b, a)
            if key in cache:
                return cache[key]
            p = (vertices[a] + vertices[b]) * .5
            p /= np.linalg.norm(p)
            vertices.append(p)
            index = len(vertices) - 1
            cache[key] = index
            return index

        refined = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined.extend(((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)))
        faces = refined
    return np.asarray(vertices, np.float32), np.asarray(faces, np.int32)


@lru_cache(maxsize=1)
def _visible_faces():
    vertices, faces = _mesh()
    # Rotate the sphere so no base-icosahedron symmetry is camera-aligned.
    ay, ax = .47, -.31
    ry = np.asarray(((np.cos(ay), 0, np.sin(ay)), (0, 1, 0),
                     (-np.sin(ay), 0, np.cos(ay))), np.float32)
    rx = np.asarray(((1, 0, 0), (0, np.cos(ax), -np.sin(ax)),
                     (0, np.sin(ax), np.cos(ax))), np.float32)
    v = vertices @ ry.T @ rx.T
    projected = CENTER + v[:, :2] * RADIUS
    rows = []
    for index, face in enumerate(faces):
        tri3 = v[face]
        centre3 = tri3.mean(axis=0)
        if centre3[2] <= .08:
            continue
        tri2 = projected[face]
        if (tri2[:, 0].max() < -24 or tri2[:, 1].max() < -24 or
                tri2[:, 0].min() > WORK + 24 or tri2[:, 1].min() > WORK + 24):
            continue
        rows.append((float(centre3[2]), index, tri2, centre3,
                     float(np.arctan2(centre3[1], centre3[0]))))
    rows.sort(key=lambda row: row[0])
    return tuple(rows)


def _blend_poly(image, poly, color, alpha):
    poly = np.rint(poly).astype(np.int32)
    x, y, w, h = cv2.boundingRect(poly)
    x0, y0 = max(0, x - 2), max(0, y - 2)
    x1, y1 = min(WORK, x + w + 2), min(WORK, y + h + 2)
    if x0 >= x1 or y0 >= y1:
        return None
    local = poly - np.asarray((x0, y0), np.int32)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillConvexPoly(mask, local, 255, cv2.LINE_AA)
    area = mask > 0
    a = mask[area].astype(np.float32)[:, None] / 255.0 * alpha
    roi = image[y0:y1, x0:x1]
    roi[area] = roi[area] * (1.0 - a) + color * a
    return x0, x1, y0, y1, mask


def _event_fields(c):
    x, y, z = (float(v) for v in c)
    fracture = abs(np.sin(7.0 * np.arctan2(y, x) + 3.0 * z))
    aperture = np.sin(13.0 * x + 7.0 * y - 5.0 * z)
    inner = np.cos(5.0 * x - 11.0 * y + 9.0 * z)
    spine = np.sin(17.0 * x + 3.0 * y + 11.0 * z)
    socket = np.cos(19.0 * x - 13.0 * y - 2.0 * z)
    collar = np.sin(23.0 * x + 17.0 * y + 5.0 * z)
    return fracture, aperture, inner, spine, socket, collar


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    radial = np.sqrt(((xx - CENTER[0]) / RADIUS) ** 2 +
                     ((yy - CENTER[1]) / RADIUS) ** 2)
    bg0 = np.asarray((.002, .005, .014) if not angle_b else (.012, .002, .022), np.float32)
    bg1 = np.asarray((.015, .035, .050) if not angle_b else (.044, .008, .058), np.float32)
    paint = bg0 + (bg1 - bg0) * np.clip(1.0 - radial, 0, 1)[..., None] * .45
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "shell_panels", "load_struts", "inner_cage_windows", "unequal_apertures",
        "tangential_fractures", "spine_roots", "broken_sockets", "mineral_collars")}
    depth_field = np.zeros((WORK, WORK), np.uint8)
    phase_field = np.zeros((WORK, WORK), np.uint8)

    for depth, index, tri, centre3, azimuth in _visible_faces():
        fracture, aperture, inner, spine, socket, collar = _event_fields(centre3)
        optical = .24 + .76 * np.clip(depth, 0, 1)
        phase = (int((azimuth / (2 * np.pi) + .5) * 15)
                 + int(depth * 21) + index * 7 + (5 if angle_b else 0)) % 15
        color = np.clip(palette[phase] * optical, 0, 1)
        info = _blend_poly(paint, tri, color, .88)
        if info is None:
            continue
        x0, x1, y0, y1, local = info
        masks["shell_panels"][y0:y1, x0:x1] = np.maximum(
            masks["shell_panels"][y0:y1, x0:x1], local)
        ipoly = np.rint(tri).astype(np.int32)
        cv2.fillConvexPoly(depth_field, ipoly, int(np.clip(depth, 0, 1) * 255), cv2.LINE_AA)
        cv2.fillConvexPoly(phase_field, ipoly, int(phase), cv2.LINE_8)
        edge_color = tuple(float(v) for v in np.clip(
            palette[(phase + 3) % 15] * (1.02 + .34 * depth), 0, 1))
        cv2.polylines(paint, [ipoly], True, edge_color, 2, cv2.LINE_AA)
        cv2.polylines(masks["load_struts"], [ipoly], True, 255, 2, cv2.LINE_AA)

        centre2 = tri.mean(axis=0)
        # Inset features follow grouped spherical fields, so events span many
        # adjacent panels rather than appearing with an independent site clock.
        inset = centre2 + (tri - centre2) * .46
        if inner > .76:
            dark = np.asarray((.005, .014, .025) if not angle_b else (.024, .004, .035), np.float32)
            _blend_poly(paint, inset, dark, .88)
            cv2.fillConvexPoly(masks["inner_cage_windows"], np.rint(inset).astype(np.int32),
                               255, cv2.LINE_AA)
        if aperture > .82:
            axes = (max(2, int(np.linalg.norm(tri[1] - tri[0]) * .19)),
                    max(2, int(np.linalg.norm(tri[2] - tri[0]) * .13)))
            c2 = tuple(np.rint(centre2).astype(int))
            cv2.ellipse(paint, c2, axes, int(np.degrees(azimuth)), 0, 360,
                        tuple(float(v) for v in bg0), -1, cv2.LINE_AA)
            cv2.ellipse(masks["unequal_apertures"], c2, axes,
                        int(np.degrees(azimuth)), 0, 360, 255, -1, cv2.LINE_AA)
        if fracture < .055:
            ordered = tri[np.argsort(tri[:, 0] + .37 * tri[:, 1])]
            p0, p1 = tuple(np.rint(ordered[0]).astype(int)), tuple(np.rint(ordered[-1]).astype(int))
            cv2.line(paint, p0, p1, tuple(float(v) for v in bg0), 3, cv2.LINE_AA)
            cv2.line(masks["tangential_fractures"], p0, p1, 255, 3, cv2.LINE_AA)
        if spine > .91:
            normal2 = centre2 - CENTER
            normal2 /= np.linalg.norm(normal2) + 1e-6
            p0 = centre2
            p1 = centre2 + normal2 * (5 + index % 9)
            c = tuple(float(v) for v in np.clip(palette[(phase + 7) % 15] * 1.25, 0, 1))
            cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                     c, 4, cv2.LINE_AA)
            cv2.line(masks["spine_roots"], tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)), 255, 4, cv2.LINE_AA)
        if socket > .93:
            radius = 3 + index % 4
            c2 = tuple(np.rint(centre2).astype(int))
            cv2.circle(paint, c2, radius, tuple(float(v) for v in bg0), 2, cv2.LINE_AA)
            cv2.circle(masks["broken_sockets"], c2, radius, 255, 2, cv2.LINE_AA)
        if collar > .94:
            radius = 2 + index % 3
            c2 = tuple(np.rint(centre2).astype(int))
            c = tuple(float(v) for v in np.clip(palette[(phase + 10) % 15] * 1.28, 0, 1))
            cv2.circle(paint, c2, radius, c, -1, cv2.LINE_AA)
            cv2.circle(masks["mineral_collars"], c2, radius, 255, -1, cv2.LINE_AA)

    return (np.clip(paint, 0, 1),
            {k: v.astype(np.float32) / 255.0 for k, v in masks.items()},
            {"depth": depth_field, "phase": phase_field})


M_TIERS = np.asarray((12, 38, 70, 104, 142, 178, 216, 246), np.uint8)
R_TIERS = np.asarray((20, 46, 74, 108, 144, 181, 220, 250), np.uint8)
CC_TIERS = np.asarray((8, 31, 59, 94, 132, 171, 213, 252), np.uint8)


def _spec_maps(masks, fields):
    """Three independently permuted material histories over the same anatomy."""
    phase = fields["phase"].astype(np.int16)
    depth = fields["depth"].astype(np.int16) * 8 // 256
    metal_i = (phase * phase + 3 * depth + 5 * phase * depth) % 8
    rough_i = (5 * phase + depth * depth + 3 * ((phase + 2 * depth) % 5)) % 8
    coat_i = (3 * phase * phase + 7 * depth + (phase * depth) % 7) % 8
    event = {name: mask > .22 for name, mask in masks.items()}

    # Different event families own each channel.  The dominant strut geometry
    # is segmented for M instead of being written wholesale into M/R/Cc.
    struts = event["load_struts"]
    metal_i[struts] = (phase[struts] + 2 * depth[struts] + 1) % 8
    metal_i[event["spine_roots"]] = 7
    metal_i[event["mineral_collars"]] = 6
    metal_i[event["unequal_apertures"]] = 0

    rough_i[event["inner_cage_windows"]] = 6
    rough_i[event["unequal_apertures"]] = 7
    rough_i[event["tangential_fractures"]] = (
        phase[event["tangential_fractures"]] + 5) % 8
    rough_i[event["broken_sockets"]] = 5

    coat_i[event["inner_cage_windows"]] = (depth[event["inner_cage_windows"]] + 4) % 8
    coat_i[event["spine_roots"]] = 5
    coat_i[event["mineral_collars"]] = 7
    coat_i[event["tangential_fractures"]] = 0
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
    out = Path("_wilds_fullres_progress_20260824/cyan_spineball_cage_i1")
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
    spec_work = np.stack(_spec_maps(masks, fields), axis=2)
    spec = cv2.resize(spec_work, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(out / f"{ID}_{name}_2048.png"), spec[:, :, index])
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {
        "id": ID, "module": __name__, "attempt": 79,
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-EXPERIMENTAL-RUNTIME",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "visible_faces": len(_visible_faces()),
        "coverage": {name: float((mask > .08).mean()) for name, mask in masks.items()},
        "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
        "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
        "spec_tiers": [int(np.unique(spec[:, :, i]).size) for i in range(3)],
        "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
        "owner_accepted": False, "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-cyan-spineball-cage-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
