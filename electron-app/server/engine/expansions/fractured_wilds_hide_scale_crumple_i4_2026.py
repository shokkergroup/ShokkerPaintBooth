# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Hide Scale Glass I4 deterministic crumple hide.

SPB-105 / Wilds rebuild tick 51, 2026-08-25. Native 2048 is authoritative.
Before: I1 bead curtains, I2 repeated loops and I3 homogeneous ray-caustic
microtexture, all frozen. After: pending native owner-eye/M7 evidence.

I4 changes the carrier completely. An R2 low-discrepancy sheet is folded into
one piecewise-developable surface. No RNG/noise, placed scale/lens, regular
grid, shared composer or shared spec map is used. Mountain folds, valley seams,
hinge lips, stress apertures, bridge repairs and abrasion tracks are all
classified from that same 3D fold geometry.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np
from scipy.spatial import Delaunay


ID = "fc_hide_scale_glass"
AUTHORED = 1024
CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)

PALETTE_A = np.asarray([
    (4, 7, 17), (12, 27, 63), (19, 59, 112), (20, 111, 151),
    (21, 168, 170), (57, 215, 155), (131, 239, 126), (218, 241, 112),
    (255, 196, 89), (255, 128, 77), (238, 72, 115), (190, 49, 158),
    (125, 48, 178), (67, 48, 151), (25, 25, 81),
], np.float32) / 255.0

PALETTE_B = np.asarray([
    (5, 8, 20), (34, 20, 80), (91, 28, 140), (157, 38, 166),
    (220, 54, 145), (251, 89, 105), (255, 150, 72), (245, 211, 79),
    (172, 239, 105), (78, 222, 145), (21, 177, 169), (7, 124, 160),
    (8, 76, 130), (16, 43, 89), (8, 18, 45),
], np.float32) / 255.0

M_TIERS = np.asarray((6, 27, 53, 83, 117, 156, 203, 250), np.uint8)
R_TIERS = np.asarray((14, 38, 69, 104, 141, 179, 217, 249), np.uint8)
CC_TIERS = np.asarray((5, 24, 49, 81, 118, 160, 208, 252), np.uint8)


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return ((a - lo) / max(1e-6, hi - lo)).astype(np.float32)


def _tier(field: np.ndarray, values: np.ndarray) -> np.ndarray:
    cuts = np.quantile(np.asarray(field, np.float32), np.linspace(0.125, 0.875, 7))
    return values[np.digitize(field, cuts)].astype(np.uint8)


def _point_height(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    z = np.zeros_like(x, np.float32)
    modes = (
        (2.3, 0.17, 0.080, 0.2), (3.7, 0.91, 0.061, 1.4),
        (5.1, 1.49, 0.047, 2.2), (6.8, 2.11, 0.036, 0.8),
        (8.9, 2.67, 0.027, 2.8), (11.7, 0.53, 0.020, 1.9),
        (14.3, 1.25, 0.015, 0.5),
    )
    for freq, angle, amp, phase in modes:
        z += np.float32(amp) * np.sin(
            np.float32(2.0 * np.pi * freq) *
            (np.float32(np.cos(angle)) * x + np.float32(np.sin(angle)) * y)
            + np.float32(phase)
        )
    # Nonlinear fold sharpening creates real ridge/valley changes without a
    # scalar texture layer becoming directly visible.
    return (z + 0.024 * np.tanh(z * 24.0)).astype(np.float32)


@lru_cache(maxsize=1)
def _geometry() -> dict:
    n_points = 4300
    idx = np.arange(1, n_points + 1, dtype=np.float64)
    x = np.mod(0.5 + idx * 0.7548776662466927, 1.0)
    y = np.mod(0.5 + idx * 0.5698402909980532, 1.0)
    # Analytic displacement breaks the R2 near-uniformity while preserving
    # deterministic non-clumping and avoiding random/noise-driven separation.
    x = np.mod(x + 0.012 * np.sin(2.0 * np.pi * (3.0 * y + 0.7 * x)), 1.0)
    y = np.mod(y + 0.011 * np.sin(2.0 * np.pi * (2.0 * x - 1.3 * y)), 1.0)

    edge = np.linspace(0.0, 1.0, 72, dtype=np.float64)
    boundary = np.vstack((
        np.column_stack((edge, np.zeros_like(edge))),
        np.column_stack((edge, np.ones_like(edge))),
        np.column_stack((np.zeros_like(edge[1:-1]), edge[1:-1])),
        np.column_stack((np.ones_like(edge[1:-1]), edge[1:-1])),
    ))
    points = np.vstack((np.column_stack((x, y)), boundary)).astype(np.float32)
    tri = Delaunay(points)
    simplices = tri.simplices.astype(np.int32)

    z = _point_height(points[:, 0], points[:, 1])
    p3 = np.column_stack((points, z * 2.8)).astype(np.float32)
    a = p3[simplices[:, 1]] - p3[simplices[:, 0]]
    b = p3[simplices[:, 2]] - p3[simplices[:, 0]]
    normals = np.cross(a, b)
    normals /= np.maximum(1e-7, np.linalg.norm(normals, axis=1, keepdims=True))
    normals = np.where(normals[:, 2:3] < 0.0, -normals, normals)
    centroids = points[simplices].mean(axis=1)
    center_z = z[simplices].mean(axis=1)

    return {
        "points": points, "simplices": simplices, "z": z,
        "normals": normals.astype(np.float32), "centroids": centroids,
        "center_z": center_z.astype(np.float32),
    }


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    geo = _geometry()
    n = AUTHORED
    pts = np.rint(geo["points"] * (n - 1)).astype(np.int32)
    simplices = geo["simplices"]
    normals = geo["normals"]

    tri_index = np.full((n, n), -1, np.int32)
    slope = np.zeros((n, n), np.float32)
    facing = np.zeros((n, n), np.float32)
    orientation = np.zeros((n, n), np.float32)
    for ti, vertices in enumerate(simplices):
        poly = pts[vertices]
        cv2.fillConvexPoly(tri_index, poly, int(ti), cv2.LINE_8)
        normal = normals[ti]
        cv2.fillConvexPoly(slope, poly, float(np.hypot(normal[0], normal[1])), cv2.LINE_8)
        cv2.fillConvexPoly(facing, poly, float(max(0.0, normal[2])), cv2.LINE_8)
        cv2.fillConvexPoly(orientation, poly, float((np.arctan2(normal[1], normal[0]) + np.pi) / (2.0 * np.pi)), cv2.LINE_8)

    ridge = np.zeros((n, n), np.uint8)
    valley = np.zeros((n, n), np.uint8)
    hinge = np.zeros((n, n), np.uint8)
    bridge = np.zeros((n, n), np.uint8)
    edge_map: dict[tuple[int, int], list[int]] = {}
    for ti, vertices in enumerate(simplices):
        for u, v in ((vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], vertices[0])):
            key = (int(min(u, v)), int(max(u, v)))
            edge_map.setdefault(key, []).append(ti)

    curvature_at_vertex = np.zeros(len(geo["points"]), np.float32)
    for edge_order, ((u, v), owners) in enumerate(edge_map.items()):
        if len(owners) != 2:
            continue
        t0, t1 = owners
        bend = float(1.0 - np.clip(np.dot(normals[t0], normals[t1]), -1.0, 1.0))
        if bend < 0.006:
            continue
        curvature_at_vertex[u] += bend
        curvature_at_vertex[v] += bend
        mid_surface = 0.5 * (geo["center_z"][t0] + geo["center_z"][t1])
        edge_surface = 0.5 * (geo["z"][u] + geo["z"][v])
        is_mountain = mid_surface < edge_surface
        thickness = int(np.clip(4 + bend * 38.0, 4, 8))
        target = ridge if is_mountain else valley
        cv2.line(target, tuple(pts[u]), tuple(pts[v]), 255, thickness, cv2.LINE_AA)
        if bend > 0.065:
            cv2.line(hinge, tuple(pts[u]), tuple(pts[v]), 255, max(2, thickness - 2), cv2.LINE_AA)
            if edge_order % 11 in (2, 7):
                center = ((pts[u] + pts[v]) // 2).astype(int)
                direction = pts[v] - pts[u]
                length = max(1.0, float(np.linalg.norm(direction)))
                normal2 = np.asarray((-direction[1], direction[0]), np.float32) / length
                half = int(np.clip(length * 0.31, 5, 12))
                p0 = np.rint(center - normal2 * half).astype(int)
                p1 = np.rint(center + normal2 * half).astype(int)
                cv2.line(bridge, tuple(p0), tuple(p1), 255, 4, cv2.LINE_AA)

    aperture = np.zeros((n, n), np.uint8)
    hot = np.argsort(curvature_at_vertex)[-190:]
    for rank, vi in enumerate(hot):
        if curvature_at_vertex[vi] <= 0.12:
            continue
        center = tuple(pts[vi])
        axes = (int(5 + rank % 6), int(3 + (rank * 3) % 5))
        angle = float((rank * 137.507764) % 180.0)
        cv2.ellipse(aperture, center, axes, angle, 25, 312, 255, 3, cv2.LINE_AA)

    scuff = np.zeros((n, n), np.uint8)
    for ti in range(13, len(simplices), 37):
        if float(np.hypot(normals[ti, 0], normals[ti, 1])) < 0.28:
            continue
        c = np.rint(geo["centroids"][ti] * (n - 1)).astype(np.float32)
        direction = np.asarray((normals[ti, 1], -normals[ti, 0]), np.float32)
        direction /= max(1e-6, float(np.linalg.norm(direction)))
        normal2 = np.asarray((-direction[1], direction[0]), np.float32)
        for lane in (-1, 0, 1):
            p0 = np.rint(c - direction * (6 + ti % 5) + normal2 * lane * 3).astype(int)
            p1 = np.rint(c + direction * (6 + ti % 5) + normal2 * lane * 3).astype(int)
            cv2.line(scuff, tuple(p0), tuple(p1), 255, 2, cv2.LINE_AA)

    return {
        "tri_index": tri_index, "slope": slope, "facing": facing,
        "orientation": orientation, "ridge": ridge.astype(np.float32) / 255.0,
        "valley": valley.astype(np.float32) / 255.0,
        "hinge": hinge.astype(np.float32) / 255.0,
        "bridge": bridge.astype(np.float32) / 255.0,
        "aperture": aperture.astype(np.float32) / 255.0,
        "scuff": scuff.astype(np.float32) / 255.0,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    idx = fields["tri_index"]
    safe = np.maximum(idx, 0)
    hue = fields["orientation"] * 0.61 + fields["slope"] * 0.47 + safe * 0.0618034
    if angle_b:
        hue = 1.0 - hue + 0.23 * fields["facing"]
    q = np.mod(hue, 1.0) * len(palette)
    i0 = np.floor(q).astype(np.int16) % len(palette)
    frac = (q - np.floor(q))[..., None].astype(np.float32)
    rgb = palette[i0] * (1.0 - frac) + palette[(i0 + 1) % len(palette)] * frac
    shade = 0.43 + 0.51 * fields["facing"] + 0.16 * fields["slope"]
    rgb *= shade[..., None]
    rgb *= (1.0 - 0.55 * fields["valley"])[..., None]
    rgb += np.asarray((0.25, 0.20, 0.07) if not angle_b else (0.05, 0.19, 0.27), np.float32) * fields["ridge"][..., None]
    rgb += np.asarray((0.04, 0.19, 0.23) if not angle_b else (0.25, 0.05, 0.18), np.float32) * fields["hinge"][..., None]
    rgb += np.asarray((0.24, 0.06, 0.18) if not angle_b else (0.07, 0.24, 0.13), np.float32) * fields["bridge"][..., None]
    rgb += np.asarray((0.28, 0.24, 0.10) if not angle_b else (0.10, 0.21, 0.28), np.float32) * fields["aperture"][..., None]
    rgb *= (1.0 - 0.24 * fields["scuff"])[..., None]
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def _spec_maps(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    metal = (0.43 * fields["ridge"] + 0.29 * fields["bridge"]
             + 0.21 * fields["aperture"] + 0.18 * fields["slope"])
    rough = (0.46 * fields["valley"] + 0.34 * fields["scuff"]
             + 0.18 * fields["slope"] + 0.13 * (1.0 - fields["facing"])
             - 0.17 * fields["ridge"])
    coat = (0.39 * fields["facing"] + 0.31 * fields["hinge"]
            + 0.24 * fields["aperture"] + 0.17 * (1.0 - fields["slope"])
            - 0.20 * fields["scuff"])
    return _tier(metal, M_TIERS), _tier(rough, R_TIERS), _tier(coat, CC_TIERS)


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    fields = _fields()
    paint = _compose(fields, PALETTE_B if angle_b else PALETTE_A, angle_b)
    paint = cv2.resize(paint, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return np.clip(paint, 0.0, 1.0).astype(np.float32), fields


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    spec = cv2.resize(np.stack(_spec_maps(fields), axis=2), (2048, 2048), interpolation=cv2.INTER_NEAREST)
    return paint, spec.astype(np.uint8)


def clear_cache() -> None:
    _geometry.cache_clear(); _fields.cache_clear(); _paint.cache_clear()


def _save_rgb(path: Path, image: np.ndarray) -> None:
    arr = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); start = time.perf_counter()
        a, fields = _paint(False); b, _ = _paint(True)
        spec = cv2.resize(np.stack(_spec_maps(fields), axis=2), (2048, 2048), interpolation=cv2.INTER_NEAREST)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes() + spec.tobytes()
        digests.append(hashlib.sha256(blob).hexdigest()); last = a, b, spec
    a, b, spec = last; delta = np.abs(a - b)
    for suffix, image in (("paint", a), ("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        _save_rgb(out_dir / f"{ID}_{suffix}_2048.png", image)
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(out_dir / f"{ID}_{name}_2048.png"), spec[:, :, index])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {
        "id": ID, "status": "NATIVE-2048-PAINT-AND-MATERIAL-CONTACT-NOT-WIRED",
        "timings_s": timings, "deterministic": len(set(digests)) == 1,
        "digest": digests[0], "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, 0.95)),
        "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
        "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
        "spec_tiers": [int(len(np.unique(spec[:, :, i]))) for i in range(3)],
        "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
    }
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "hide_scale_glass_i4"), indent=2))
