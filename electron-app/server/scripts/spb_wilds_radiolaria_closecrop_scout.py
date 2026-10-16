# -*- coding: utf-8 -*-
"""Unassigned native-2048 close-cropped radiolarian shell scout.

Replaces Batch 99's visible wireframe-ball silhouette with two offset cages
whose spherical boundaries remain outside the frame. Paint only; no attempt,
spec, runtime, registry, commit, or push.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.spatial import ConvexHull


W, N = 1024, 2048
OUT = Path("_wilds_fullres_progress_20260824/radiolaria_closecrop_scout")
PAL = np.asarray([
    (4, 5, 18), (18, 12, 48), (47, 20, 86), (91, 27, 119),
    (139, 36, 132), (187, 50, 126), (225, 72, 106), (247, 105, 80),
    (250, 149, 61), (235, 192, 58), (193, 219, 70), (129, 224, 91),
    (65, 207, 116), (25, 162, 135), (9, 101, 125),
], np.float32) / 255.0


def color(i, lift=1.0):
    return tuple(int(v) for v in np.clip(PAL[i % 15] * lift * 255, 0, 255))


def fibonacci_shell(count, ax, ay):
    k = np.arange(count, dtype=np.float32)
    z = 1 - 2 * (k + .5) / count
    theta = 2 * np.pi * np.mod(k * .61803398875, 1)
    r = np.sqrt(np.maximum(0, 1 - z * z))
    p = np.stack((r * np.cos(theta), r * np.sin(theta), z), axis=1)
    rx = np.asarray([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]], np.float32)
    ry = np.asarray([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]], np.float32)
    return p @ rx.T @ ry.T


def project(points, scale, centre):
    depth = points[:, 2]
    perspective = 1 / (1.30 - .30 * depth)
    x = centre[0] + points[:, 0] * scale * perspective
    y = centre[1] + points[:, 1] * scale * perspective
    return np.stack((x, y), axis=1), depth


def render():
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    x, y = xx / W, yy / W
    t = np.clip(.18 + .62 * (.44 * x + .56 * y), 0, 1)
    base = PAL[0] * (1 - t[..., None]) + PAL[2] * t[..., None]
    base *= (.19 + .055 * (np.sin(2 * np.pi * (1.7 * x - 2.1 * y)) * .5 + .5))[..., None]
    canvas = np.clip(base * 255, 0, 255).astype(np.uint8)

    layers = [
        (fibonacci_shell(6000, -.19, .72), 780, (512, 512), .24, 2),
        (fibonacci_shell(24000, .61, -.38), 1120, (512, 512), .82, 7),
    ]
    semantic = {"outer_strut": 0, "inner_cage": 0, "aperture_rim": 0,
                "radial_brace": 0, "broken_socket": 0, "spine_root": 0}

    for layer_index, (points, scale, centre, opacity, seed) in enumerate(layers):
        projected, depth = project(points, scale, centre)
        hull = ConvexHull(points)
        faces = []
        for tri in hull.simplices:
            dep = float(np.mean(depth[tri]))
            poly = projected[tri]
            if dep > -.16 and poly[:, 0].max() > -80 and poly[:, 0].min() < W + 80 and poly[:, 1].max() > -80 and poly[:, 1].min() < W + 80:
                faces.append((dep, tri))
        faces.sort(key=lambda item: item[0])
        overlay = canvas.copy()
        edges = set()
        for index, (dep, tri) in enumerate(faces):
            poly = np.rint(projected[tri]).astype(np.int32)
            # Translucent shell skin exists only in selected material bays.
            if (int(tri.sum()) * 7 + index * 3 + seed) % 11 in (0, 1, 4):
                cv2.fillConvexPoly(overlay, poly, color(index * 5 + int(dep * 13), .22 + .18 * max(dep, 0)), cv2.LINE_AA)
            for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                key = tuple(sorted((int(a), int(b))))
                # Remove a deterministic minority to break the triangle carrier.
                if (key[0] * 17 + key[1] * 31 + seed) % 9 not in (0, 1):
                    edges.add(key)
        cv2.addWeighted(overlay, opacity, canvas, 1 - opacity, 0, canvas)
        for j, (a, b) in enumerate(sorted(edges)):
            dep = float((depth[a] + depth[b]) * .5)
            if dep < -.16:
                continue
            p0, p1 = tuple(np.rint(projected[a]).astype(int)), tuple(np.rint(projected[b]).astype(int))
            width = (3 if layer_index == 0 else 4) + int(np.clip((dep + .16) * (2 if layer_index == 0 else 3), 0, 4))
            cv2.line(canvas, p0, p1, color(j * 7 + seed, .42 + .38 * max(dep, 0)), width + 3, cv2.LINE_AA)
            cv2.line(canvas, p0, p1, color(j * 11 + 8 + seed, .78 + .42 * max(dep, 0)), max(1, width // 2), cv2.LINE_AA)
            semantic["inner_cage" if layer_index == 0 else "outer_strut"] += 1

        if layer_index == 1:
            # Aperture rims belong to unusually large visible faces.
            areas = []
            for dep, tri in faces:
                poly = projected[tri].astype(np.float32)
                area = abs(float(cv2.contourArea(poly)))
                if dep > .08 and 24 < area < 420:
                    areas.append((area, dep, tri))
            for j, (_area, dep, tri) in enumerate(sorted(areas, key=lambda item: item[0], reverse=True)[:31]):
                poly = np.rint(projected[tri] * .82 + projected[tri].mean(axis=0) * .18).astype(np.int32)
                cv2.polylines(canvas, [poly], True, color(j * 4 + 12, 1.16), 3 + j % 4, cv2.LINE_AA)
                semantic["aperture_rim"] += 1
            # Braces connect outer nodes to the corresponding inner direction.
            inner_points, _, _, _, _ = layers[0]
            inner_proj, _ = project(inner_points, layers[0][1], layers[0][2])
            for j in range(13, len(points), 977):
                if depth[j] < .18:
                    continue
                target = inner_proj[(j * 37) % len(inner_proj)]
                p = projected[j]
                if np.linalg.norm(p - target) < 430:
                    cv2.line(canvas, tuple(np.rint(target).astype(int)), tuple(np.rint(p).astype(int)), color(j + 5, .84), 3 + j % 5, cv2.LINE_AA)
                    cv2.circle(canvas, tuple(np.rint(p).astype(int)), 5 + j % 5, color(j + 11, 1.18), 2, cv2.LINE_AA)
                    semantic["radial_brace"] += 1
                    semantic["broken_socket"] += 1
            # A few depth-owned spine roots terminate outside the crop.
            for j in range(29, len(points), 1997):
                if depth[j] < .42:
                    continue
                p = projected[j]
                outward = p - np.asarray(layers[1][2], np.float32)
                outward /= max(float(np.linalg.norm(outward)), 1e-5)
                q = p + outward * (18 + j % 15)
                cv2.line(canvas, tuple(np.rint(p).astype(int)), tuple(np.rint(q).astype(int)), color(j + 3, 1.2), 4, cv2.LINE_AA)
                semantic["spine_root"] += 1
    return canvas, semantic


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    times, repeats, semantics = [], [], None
    for _ in range(3):
        started = time.perf_counter()
        work, semantics = render()
        native = cv2.resize(work, (N, N), interpolation=cv2.INTER_CUBIC)
        times.append(time.perf_counter() - started)
        repeats.append(native)
    cv2.imwrite(str(OUT / "radiolaria_closecrop_2048.png"), cv2.cvtColor(repeats[0], cv2.COLOR_RGB2BGR))
    report = {"status": "UNASSIGNED-NATIVE-SCOUT", "timings_s": times,
              "deterministic": bool(all(np.array_equal(repeats[0], im) for im in repeats[1:])),
              "semantic_counts": semantics, "attempt_assigned": False,
              "spec_built": False, "runtime_wired": False}
    (OUT / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
