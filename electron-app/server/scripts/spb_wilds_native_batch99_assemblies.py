# -*- coding: utf-8 -*-
"""Native-2048 Wilds dimensional-assembly tournament.

Four unassigned contacts use causal geometry/depth rather than coloring a
scalar contour field. They remain paint-only and fail-closed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import ConvexHull


W = 1024
N = 2048
OUT = Path("_wilds_fullres_progress_20260824/native_batch99_assemblies")
PAL = np.asarray([
    (5, 9, 23), (15, 20, 55), (39, 28, 91), (78, 34, 122),
    (126, 42, 136), (174, 53, 132), (213, 72, 113), (239, 103, 84),
    (248, 145, 64), (237, 187, 58), (195, 216, 68), (132, 221, 88),
    (67, 204, 114), (24, 159, 132), (10, 101, 124),
], np.float32) / 255.0


def rgb(index, lift=1.0):
    return tuple(int(v) for v in np.clip(PAL[index % 15] * lift * 255, 0, 255))


def substrate(index=0):
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    x, y = xx / W, yy / W
    a = PAL[index % 15]
    b = PAL[(index + 3) % 15]
    t = np.clip(.16 + .68 * (x * .43 + y * .57), 0, 1)
    base = a[None, None] * (1 - t[..., None]) + b[None, None] * t[..., None]
    shade = .17 + .07 * (np.sin(2 * np.pi * (2.1 * x - 1.7 * y)) * .5 + .5)
    return np.clip(base * shade[..., None] * 255, 0, 255).astype(np.uint8)


def radiolarian_depth_shell():
    """One close-cropped projected shell with outer cage, inner cage and braces."""
    canvas = substrate(1)
    count = 430
    k = np.arange(count, dtype=np.float32)
    z = 1 - 2 * (k + .5) / count
    theta = 2 * np.pi * np.mod(k * .61803398875, 1)
    r = np.sqrt(np.maximum(0, 1 - z * z))
    points = np.stack((r * np.cos(theta), r * np.sin(theta), z), axis=1)
    ax, ay = .63, -.41
    rx = np.asarray([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]], np.float32)
    ry = np.asarray([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]], np.float32)
    points = points @ rx.T @ ry.T
    hull = ConvexHull(points)

    def project(scale):
        depth = points[:, 2]
        perspective = 1.0 / (1.32 - .28 * depth)
        px = 512 + points[:, 0] * scale * perspective
        py = 512 + points[:, 1] * scale * perspective
        return np.stack((px, py), axis=1), depth

    outer, depth = project(735)
    inner, _ = project(520)
    faces = []
    for tri in hull.simplices:
        if np.mean(depth[tri]) > -.08:
            faces.append((float(np.mean(depth[tri])), tri))
    faces.sort()
    # Inner cage is visible through outer apertures.
    for dep, tri in faces[::2]:
        poly = np.rint(inner[tri]).astype(np.int32)
        cv2.polylines(canvas, [poly], True, rgb(int((dep + 1) * 6) + 9, .52), 2, cv2.LINE_AA)
    # Outer shell faces and depth-shaped struts.
    edges = set()
    for dep, tri in faces:
        poly = np.rint(outer[tri]).astype(np.int32)
        face_col = rgb(int((dep + 1) * 7), .22 + .16 * max(dep, 0))
        overlay = canvas.copy()
        cv2.fillConvexPoly(overlay, poly, face_col, cv2.LINE_AA)
        cv2.addWeighted(overlay, .27, canvas, .73, 0, canvas)
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edges.add(tuple(sorted((int(a), int(b)))))
    for j, (a, b) in enumerate(sorted(edges)):
        dep = float((depth[a] + depth[b]) * .5)
        if dep < -.08:
            continue
        p0, p1 = tuple(np.rint(outer[a]).astype(int)), tuple(np.rint(outer[b]).astype(int))
        width = 3 + int(np.clip((dep + .08) * 4, 0, 5))
        cv2.line(canvas, p0, p1, rgb(j * 7 + int(dep * 19), .68 + .45 * max(dep, 0)), width + 3, cv2.LINE_AA)
        cv2.line(canvas, p0, p1, rgb(j * 11 + 8, 1.13), max(2, width // 2), cv2.LINE_AA)
    # Causal radial braces join selected outer vertices to their inner cage locus.
    for j in range(0, count, 37):
        if depth[j] > .1:
            cv2.line(canvas, tuple(np.rint(inner[j]).astype(int)), tuple(np.rint(outer[j]).astype(int)), rgb(j + 10, .92), 3 + j % 4, cv2.LINE_AA)
            cv2.circle(canvas, tuple(np.rint(outer[j]).astype(int)), 4 + j % 5, rgb(j + 5, 1.15), 2, cv2.LINE_AA)
    return canvas


def anastomosing_delta():
    """Area-forming braided flow: channels split, merge, erode and redeposit."""
    canvas = substrate(7)
    overlay = canvas.copy()
    channels = []
    for lineage in range(34):
        ys = np.linspace(-80, 1100, 190, dtype=np.float32)
        phase = lineage * 1.372
        x0 = 24 + ((lineage * 67) % 976)
        x = (x0 + 94 * np.sin(ys / (77 + lineage % 9) + phase)
             + 41 * np.sin(ys / (29 + lineage % 7) - phase * .7)
             + 18 * np.sin(ys / 13.7 + phase * 1.9))
        # Pull paired histories together over finite confluence windows.
        target = 512 + 270 * np.sin(ys / 151 + (lineage % 6))
        gate = np.exp(-((ys - (130 + (lineage * 83) % 780)) / (95 + 8 * (lineage % 5))) ** 2)
        x = x * (1 - .44 * gate) + target * (.44 * gate)
        pts = np.rint(np.stack((x, ys), axis=1)).astype(np.int32)
        width = 5 + lineage % 7
        col = rgb(lineage * 5 + 2, .66 + .07 * (lineage % 5))
        cv2.polylines(overlay, [pts], False, col, width + 7, cv2.LINE_AA)
        cv2.polylines(overlay, [pts], False, rgb(lineage * 3 + 10, 1.05), width, cv2.LINE_AA)
        # Depositional side bars remain attached to channel curvature.
        for k in range(14 + lineage % 8, len(pts) - 10, 31 + lineage % 11):
            p = pts[k]
            d = pts[k + 3].astype(np.float32) - pts[k - 3]
            d /= max(float(np.linalg.norm(d)), 1e-5)
            nrm = np.asarray((-d[1], d[0]))
            side = -1 if (lineage + k) % 2 else 1
            a = p + nrm * side * (width + 2)
            b = a + nrm * side * (7 + (lineage + k) % 7) + d * (5 + lineage % 6)
            cv2.line(overlay, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), rgb(lineage + k, 1.12), 3, cv2.LINE_AA)
        channels.append(pts)
    cv2.addWeighted(overlay, .86, canvas, .14, 0, canvas)
    # True confluences get bright sediment knots; not scattered independently.
    for j in range(0, len(channels) - 1, 3):
        a, b = channels[j][::10], channels[j + 1][::10]
        d = np.sum((a[:, None, :] - b[None, :, :]) ** 2, axis=2)
        ia, ib = np.unravel_index(np.argmin(d), d.shape)
        if d[ia, ib] < 180:
            c = tuple(((a[ia] + b[ib]) // 2).astype(int))
            cv2.ellipse(canvas, c, (7 + j % 5, 4 + j % 3), j * 17, 0, 360, rgb(j * 7, 1.18), 3, cv2.LINE_AA)
    return canvas


def buckled_cuticle():
    """Dimensional thin sheet with crease lips, saddles, pores and abrasion."""
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    x, y = (xx - 512) / 512, (yy - 512) / 512
    height = np.zeros_like(x)
    crease = np.zeros_like(x)
    for j in range(19):
        ang = 2 * np.pi * ((j * .61803398875) % 1)
        nx, ny = np.cos(ang), np.sin(ang)
        tx, ty = -ny, nx
        offset = -.82 + 1.64 * ((j * .41421356237) % 1)
        along = x * tx + y * ty
        normal = x * nx + y * ny - offset - .11 * np.sin(along * (2.2 + .17 * j) + j)
        finite = np.exp(-((along - .15 * np.sin(j)) / (.48 + .03 * (j % 7))) ** 8)
        sigma = .008 + .0025 * (j % 4)
        ridge = np.exp(-(normal / sigma) ** 2) * finite
        height += ridge * (.045 + .012 * (j % 5)) * (-1 if j % 3 == 0 else 1)
        crease += ridge
    height += .018 * np.sin(31 * x + 7 * np.sin(4 * y)) * np.sin(27 * y - 5 * np.sin(3 * x))
    height = gaussian_filter(height, .8)
    gy, gx = np.gradient(height)
    normal = np.dstack((-gx * 18, -gy * 18, np.ones_like(height)))
    normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-6)
    lights = [np.asarray((-.45, -.35, .82)), np.asarray((.66, -.12, .74)), np.asarray((-.12, .75, .65))]
    lights = [v / np.linalg.norm(v) for v in lights]
    lobes = [np.clip(normal @ v, 0, 1) ** p for v, p in zip(lights, (7, 18, 38))]
    hue = np.mod(np.arctan2(normal[..., 1], normal[..., 0]) / (2 * np.pi) + .5 + height * 9, 1)
    q = hue * 15
    i = np.floor(q).astype(np.int16) % 15
    f = (q - np.floor(q))[..., None]
    base = PAL[i] * (1 - f) + PAL[(i + 1) % 15] * f
    light = .18 + .38 * lobes[0] + .42 * lobes[1] + .55 * lobes[2]
    base *= light[..., None]
    # Abrasion belongs to the highest-curvature crease lips.
    abrasion = np.clip(crease - .42, 0, 1) * (.5 + .5 * np.sin(73 * x - 59 * y))
    base += abrasion[..., None] * np.asarray((.24, .18, .12))
    return np.clip(base * 255, 0, 255).astype(np.uint8)


def scar_callus_relief():
    """A healed fracture chronology with raised lips and cross-grain stitches."""
    canvas = substrate(10)
    mask = np.zeros((W, W), np.uint8)
    scars = []
    frontier = [(np.asarray((512., 500.)), np.asarray((.83, -.12)), 0)]
    while frontier and len(scars) < 185:
        p, direction, depth = frontier.pop(0)
        length = 24 + ((len(scars) * 17 + depth * 11) % 43)
        turn = .24 * np.sin(len(scars) * 1.73 + depth)
        c, s = np.cos(turn), np.sin(turn)
        d = np.asarray((direction[0] * c - direction[1] * s, direction[0] * s + direction[1] * c))
        q = p + d * length
        if not (-90 < q[0] < 1114 and -90 < q[1] < 1114):
            continue
        scars.append((p, q, depth))
        if depth < 8:
            frontier.append((q, d, depth + 1))
            if (len(scars) + depth) % 3 != 1:
                split = (.47 + .12 * ((len(scars) + depth) % 4)) * (-1 if len(scars) % 2 else 1)
                cs, ss = np.cos(split), np.sin(split)
                frontier.append((q, np.asarray((d[0] * cs - d[1] * ss, d[0] * ss + d[1] * cs)), depth + 1))
    for p, q, depth in scars:
        width = max(3, 9 - depth // 2)
        cv2.line(mask, tuple(np.rint(p).astype(int)), tuple(np.rint(q).astype(int)), 255, width, cv2.LINE_AA)
    distance = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    lip = np.exp(-(distance / 7.5) ** 2)
    core = np.exp(-(distance / 2.2) ** 2)
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    field = np.mod((xx * .006 + yy * .004 + lip * .32), 1)
    q = field * 15
    i = np.floor(q).astype(np.int16) % 15
    f = (q - np.floor(q))[..., None]
    colored = PAL[i] * (1 - f) + PAL[(i + 1) % 15] * f
    base = canvas.astype(np.float32) / 255
    base = base * (1 - lip[..., None] * .72) + colored * lip[..., None] * (1.05 - core[..., None] * .62)
    # Stitches bridge only deep primary scars.
    for j, (p, q, depth) in enumerate(scars):
        if depth > 3 or j % 4:
            continue
        d = q - p
        d /= max(float(np.linalg.norm(d)), 1e-5)
        nrm = np.asarray((-d[1], d[0]))
        c = (p + q) * .5
        a, b = c - nrm * (7 + j % 5), c + nrm * (7 + j % 5)
        cv2.line(base, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), tuple(v / 255 for v in rgb(j * 5, 1.2)), 3, cv2.LINE_AA)
    return np.clip(base * 255, 0, 255).astype(np.uint8)


CONCEPTS = [("radiolarian_depth_shell", radiolarian_depth_shell),
            ("anastomosing_delta", anastomosing_delta),
            ("buckled_cuticle", buckled_cuticle),
            ("scar_callus_relief", scar_callus_relief)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records, thumbs = [], []
    for name, fn in CONCEPTS:
        started = time.perf_counter()
        work = fn()
        native = cv2.resize(work, (N, N), interpolation=cv2.INTER_CUBIC)
        elapsed = time.perf_counter() - started
        cv2.imwrite(str(OUT / f"{name}_2048.png"), cv2.cvtColor(native, cv2.COLOR_RGB2BGR))
        thumb = cv2.resize(native, (768, 768), interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumb, (0, 704), (768, 768), (0, 0, 0), -1)
        cv2.putText(thumb, name, (18, 746), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2, cv2.LINE_AA)
        thumbs.append(thumb)
        records.append({"concept": name, "render_s": elapsed, "native": f"{name}_2048.png",
                        "attempt_assigned": False, "spec_built": False, "runtime_wired": False})
    montage = np.vstack((np.hstack(thumbs[:2]), np.hstack(thumbs[2:])))
    cv2.imwrite(str(OUT / "NATIVE_BATCH99_CONTACT.png"), cv2.cvtColor(montage, cv2.COLOR_RGB2BGR))
    (OUT / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
