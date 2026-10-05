# -*- coding: utf-8 -*-
"""Native-2048 topology tournament after Wilds attempt 97.

These contacts are deliberately unassigned. A concept receives an attempt
number only if its dominant full-size topology survives review. No RNG/noise,
spec maps, runtime installation, registry mutation, commit, or push occurs.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter


WORK = 1024
NATIVE = 2048
OUT = Path("_wilds_fullres_progress_20260824/native_batch98_scout")
PALETTE = np.asarray([
    (3, 7, 21), (12, 18, 52), (34, 25, 94), (75, 32, 128),
    (127, 39, 145), (181, 49, 141), (224, 68, 121), (247, 100, 90),
    (252, 145, 63), (243, 194, 55), (199, 225, 67), (127, 229, 91),
    (55, 205, 123), (17, 158, 139), (7, 91, 121),
], np.float32) / 255.0


def _xy(n=WORK):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    return (xx + .5) / n * 2 - 1, (yy + .5) / n * 2 - 1


def _norm(a):
    lo, hi = np.quantile(a, (.006, .994))
    return np.clip((a - lo) / max(float(hi - lo), 1e-6), 0, 1).astype(np.float32)


def _color(field, relief, seam=0):
    t = np.mod(_norm(field) * .92 + .04, 1.0)
    q = t * len(PALETTE)
    i = np.floor(q).astype(np.int16) % len(PALETTE)
    f = (q - np.floor(q))[..., None]
    rgb = PALETTE[i] * (1 - f) + PALETTE[(i + 1) % len(PALETTE)] * f
    light = .50 + .62 * _norm(relief)
    rgb *= light[..., None]
    if np.isscalar(seam):
        seam = np.zeros_like(field)
    rgb += np.clip(seam, 0, 1)[..., None] * np.asarray((.18, .22, .17), np.float32)
    return np.clip(rgb, 0, 1)


def differential_growth_lamina():
    """Nested nonconcentric growth lips with local pinch and split events."""
    x, y = _xy()
    z = x + 1j * y
    warp_x = x + .11 * np.sin(5.3 * y + 1.1 * np.sin(3.1 * x))
    warp_y = y + .09 * np.sin(4.1 * x - 1.3 * np.cos(2.7 * y))
    r = np.sqrt((warp_x * (1 + .18 * y)) ** 2 + (warp_y * (1 - .13 * x)) ** 2)
    a = np.arctan2(warp_y, warp_x)
    chronology = (r * (31 + 4 * np.sin(3 * a)) + 1.7 * np.sin(5 * a)
                  + .8 * np.sin(9 * a + 8 * r) + .35 * np.real(z ** 3))
    lips = np.abs(np.sin(np.pi * chronology))
    split = np.abs(np.sin(np.pi * (chronology * .503 + 5.7 * a)))
    relief = (1 - lips) ** 2 + .38 * (1 - split) ** 4
    field = chronology / 31 + .16 * np.sin(2 * a + 7 * r)
    return _color(field, relief, (1 - lips) ** 7)


def magnetic_domain_walls():
    """Curved nematic domains whose walls carry fine alternating face states."""
    x, y = _xy()
    potentials = []
    for k in range(11):
        a = 2 * np.pi * ((k * .61803398875) % 1)
        cx, cy = .73 * np.cos(a) * (1 - .025 * k), .73 * np.sin(a) * (1 - .018 * k)
        theta = a * 1.7 + .4 * np.sin(k)
        u = (x - cx) * np.cos(theta) + (y - cy) * np.sin(theta)
        v = -(x - cx) * np.sin(theta) + (y - cy) * np.cos(theta)
        potentials.append((u / (.24 + .025 * (k % 4))) ** 2 + (v / (.48 + .03 * (k % 3))) ** 2 + .09 * np.sin(8 * u + k))
    stack = np.stack(potentials)
    order = np.partition(stack, 1, axis=0)
    labels = np.argmin(stack, axis=0)
    gap = order[1] - order[0]
    theta = labels * 1.137 + .25 * np.sin(3 * x - 2 * y)
    comb = np.sin((x * np.cos(theta) + y * np.sin(theta)) * np.pi * 126 + labels * .7)
    wall = np.exp(-gap * 22)
    relief = .25 + .55 * (comb * .5 + .5) + wall * .85
    field = labels / 11 + .075 * comb + .12 * wall
    return _color(field, relief, wall ** 2)


def capillary_finger_sheet():
    """Unequal viscous fingers from several off-canvas pressure histories."""
    x, y = _xy()
    potential = np.zeros_like(x)
    angle_mix = np.zeros_like(x)
    sources = [(-1.18, -.72, 1.0), (-1.1, .35, -.8), (.22, -1.18, .72), (1.17, .62, -1.1), (.72, 1.15, .84)]
    for j, (cx, cy, strength) in enumerate(sources):
        dx, dy = x - cx, y - cy
        r = np.sqrt(dx * dx + dy * dy) + .025
        a = np.arctan2(dy, dx)
        potential += strength * np.log(r)
        angle_mix += (.17 + .035 * j) * np.sin((5 + 2 * j) * a + (9 + j) * r)
    history = potential * 13 + angle_mix * 7 + 1.1 * np.sin(4 * x * y + 3 * x)
    face = np.sin(np.pi * history)
    neck = np.abs(np.cos(np.pi * (history * .5 + 3.1 * x - 2.4 * y)))
    relief = (face * .5 + .5) ** 2 + .45 * (1 - neck) ** 5
    field = history / 13 + .13 * neck
    return _color(field, relief, np.clip(1 - np.abs(face), 0, 1) ** 5)


def projected_shell_fabric():
    """Stereographic shell projection with unequal great-circle cage families."""
    x, y = _xy()
    r2 = x * x + y * y
    sphere = np.stack((2 * x, 2 * y, 1 - r2), axis=-1) / (1 + r2)[..., None]
    distances = []
    signed = []
    for k in range(17):
        phi = 2 * np.pi * ((k * .61803398875) % 1)
        z = -.82 + 1.64 * ((k * .41421356237) % 1)
        radial = math.sqrt(max(0., 1 - z * z))
        normal = np.asarray((radial * np.cos(phi), radial * np.sin(phi), z), np.float32)
        d = sphere @ normal
        signed.append(d)
        distances.append(np.abs(d - (.055 * np.sin(k * 1.7))))
    ds = np.stack(distances)
    sg = np.stack(signed)
    first = np.min(ds, axis=0)
    second = np.partition(ds, 1, axis=0)[1]
    cage = np.exp(-first * 155) + .55 * np.exp(-second * 125)
    cells = np.argmin(ds, axis=0)
    pore = np.abs(np.sin(47 * sg[cells, np.arange(WORK)[:, None], np.arange(WORK)[None, :]]))
    relief = cage + .22 * pore
    field = cells / 17 + .1 * sphere[..., 2] + .04 * pore
    return _color(field, relief, np.clip(cage - .35, 0, 1))


def seismic_slip_laminate():
    """Fine strata displaced by interacting finite faults and healed splays."""
    x, y = _xy()
    u, v = x.copy(), y.copy()
    seam = np.zeros_like(x)
    faults = [(-.46, -.28, .72, .22), (.36, -.12, -1.04, -.18), (-.08, .54, 1.78, .16), (.61, .48, 2.54, -.13), (-.63, .66, .18, .12)]
    for cx, cy, ang, slip in faults:
        nx, ny = -np.sin(ang), np.cos(ang)
        tx, ty = np.cos(ang), np.sin(ang)
        normal = (x - cx) * nx + (y - cy) * ny
        along = (x - cx) * tx + (y - cy) * ty
        finite = .5 * (np.tanh((along + .65) * 12) - np.tanh((along - .65) * 12))
        move = np.tanh(normal * 38) * slip * finite
        u += move * tx
        v += move * ty
        seam += np.exp(-(normal * 85) ** 2) * finite
    strata = 93 * (v + .11 * np.sin(3.7 * u) + .045 * np.sin(11 * u + 2.5 * v))
    micro = np.sin(np.pi * strata)
    relay = np.sin(np.pi * (strata * .37 + 8.3 * u - 3.1 * v))
    relief = (micro * .5 + .5) * .72 + (relay * .5 + .5) * .28 + seam * .8
    field = strata / 93 + .12 * seam + .035 * relay
    return _color(field, relief, seam)


def excitable_front_relief():
    """Continuous excitable wavefront sheet from deterministic catalytic scars."""
    m = 512
    yy, xx = np.mgrid[0:m, 0:m].astype(np.float32)
    u = np.ones((m, m), np.float32)
    v = np.zeros((m, m), np.float32)
    for k in range(13):
        a = 2 * np.pi * ((k * .61803398875) % 1)
        cx = m * (.5 + .39 * np.cos(a) * (.62 + .03 * (k % 5)))
        cy = m * (.5 + .39 * np.sin(a) * (.62 + .025 * (k % 7)))
        rx, ry = 5 + (k * 3) % 13, 8 + (k * 5) % 17
        seed = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1
        u[seed], v[seed] = .35 + .03 * (k % 4), .72
    for _ in range(420):
        lu = (-u + .2 * (np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1))
              + .05 * (np.roll(np.roll(u, 1, 0), 1, 1) + np.roll(np.roll(u, 1, 0), -1, 1)
                       + np.roll(np.roll(u, -1, 0), 1, 1) + np.roll(np.roll(u, -1, 0), -1, 1)))
        lv = (-v + .2 * (np.roll(v, 1, 0) + np.roll(v, -1, 0) + np.roll(v, 1, 1) + np.roll(v, -1, 1))
              + .05 * (np.roll(np.roll(v, 1, 0), 1, 1) + np.roll(np.roll(v, 1, 0), -1, 1)
                       + np.roll(np.roll(v, -1, 0), 1, 1) + np.roll(np.roll(v, -1, 0), -1, 1)))
        uvv = u * v * v
        u += .92 * lu - uvv + .034 * (1 - u)
        v += .47 * lv + uvv - (.034 + .061) * v
    u = cv2.resize(u, (WORK, WORK), interpolation=cv2.INTER_CUBIC)
    v = cv2.resize(v, (WORK, WORK), interpolation=cv2.INTER_CUBIC)
    gx, gy = np.gradient(v)
    relief = _norm(np.hypot(gx, gy) * 12 + v * .32)
    field = _norm(v - .42 * u + .12 * gaussian_filter(v, 7))
    seam = np.clip(relief * 1.35 - .45, 0, 1)
    return _color(field, relief, seam)


CONCEPTS = [
    ("differential_growth_lamina", differential_growth_lamina),
    ("magnetic_domain_walls", magnetic_domain_walls),
    ("capillary_finger_sheet", capillary_finger_sheet),
    ("projected_shell_fabric", projected_shell_fabric),
    ("seismic_slip_laminate", seismic_slip_laminate),
    ("excitable_front_relief", excitable_front_relief),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records, thumbs = [], []
    for name, fn in CONCEPTS:
        started = time.perf_counter()
        rgb = fn()
        native = cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)
        elapsed = time.perf_counter() - started
        u8 = np.clip(native * 255 + .5, 0, 255).astype(np.uint8)
        cv2.imwrite(str(OUT / f"{name}_2048.png"), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR))
        thumb = cv2.resize(u8, (768, 768), interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumb, (0, 704), (768, 768), (0, 0, 0), -1)
        cv2.putText(thumb, name, (18, 746), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2, cv2.LINE_AA)
        thumbs.append(thumb)
        records.append({"concept": name, "render_s": elapsed, "native": f"{name}_2048.png",
                        "attempt_assigned": False, "spec_built": False, "runtime_wired": False})
    montage = np.vstack((np.hstack(thumbs[:3]), np.hstack(thumbs[3:])))
    cv2.imwrite(str(OUT / "NATIVE_BATCH98_CONTACT.png"), cv2.cvtColor(montage, cv2.COLOR_RGB2BGR))
    (OUT / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
