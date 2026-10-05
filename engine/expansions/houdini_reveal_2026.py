# -*- coding: utf-8 -*-
"""FRACTURED HOUDINI — proof of the REVEAL mechanism (2026-09-02, unregistered).

Owner: "the whole concept was to HIDE designs like SKULLS, GLYPH SIGNALS, UFOs,
GHOSTS, Flames, WHATEVER - hiding features IN the paint that ONLY show up when it
FRACTURES. Cleverly hidden otherwise."

WHAT "FRACTURES" MEANS HERE, PHYSICALLY (Spec Guide v1 §1, proven on NIGHTSHIFT):
a dielectric pixel shows its albedo diffusely and its highlight is white; a
metallic pixel shows almost no diffuse and its reflection is TINTED BY ITS OWN
ALBEDO. Under broad daylight the diffuse term dominates, so two pixels with the
same albedo look the same whatever their spec. Under a hard point light the
specular term dominates, so a chrome-tier smooth pixel is the brightest thing on
the car and a matte dielectric pixel is dark. So:

    paint  : the carrier texture, IDENTICAL inside and outside the design.
    spec   : the carrier's own material quilt, with the population FLIPPED inside
             the design silhouette — body cells dielectric-matte, design cells
             chrome-tier smooth (or the inverse) — and the flip applied only on
             the carrier's own fine cells, so at 1:1 the spec is still that
             texture and the silhouette is a halftone that resolves at car scale.

Why Codex's twenty failed (wiki log 2026-08-31): proofs with no engine basis,
secrets that were literal decals or scattered punctuation, generic carriers, and
no number for "hidden in day / legible at night". This module measures both with
engine/paint_v2/daynight.py: HIDDEN = |luma(design) - luma(surround)| in DAY,
REVEAL = the same in NIGHT.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from engine.paint_v2 import era_kit_2026 as EK
from engine.expansions import nightshift_forms_2026 as NF
from engine.paint_v2 import daynight as DN

GEN = 1024


# ─────────────────────────────── silhouettes ────────────────────────────────
def _grid(h, w, cx, cy, s, rot):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    X = (x - cx) / s
    Y = (y - cy) / s
    c, sn = np.cos(rot), np.sin(rot)
    return X * c - Y * sn, X * sn + Y * c


def skull(h, w, cx, cy, s, rot=0.0):
    X, Y = _grid(h, w, cx, cy, s, rot)
    cranium = (X / 0.68) ** 2 + ((Y + 0.14) / 0.70) ** 2 < 1.0
    jaw = (np.abs(X) < 0.46) & (Y > 0.20) & (Y < 0.70) & ((np.abs(X) + 0.55 * (Y - 0.20)) < 0.50)
    eye_l = ((X + 0.26) / 0.20) ** 2 + ((Y + 0.04) / 0.16) ** 2 < 1.0
    eye_r = ((X - 0.26) / 0.20) ** 2 + ((Y + 0.04) / 0.16) ** 2 < 1.0
    nose = (np.abs(X) < 0.09) & (Y > 0.14) & (Y < 0.36) & (np.abs(X) < 0.05 + 0.25 * (Y - 0.14))
    gap = (Y > 0.44) & (Y < 0.50) & (np.abs(X) < 0.34)
    teeth = (np.abs(X) < 0.34) & (Y > 0.50) & (Y < 0.66) & (np.mod(np.floor((X + 0.34) * 9.0), 2) == 0)
    return ((cranium | jaw) & ~(eye_l | eye_r | nose | gap | teeth)).astype(np.float32)


def ufo(h, w, cx, cy, s, rot=0.0):
    X, Y = _grid(h, w, cx, cy, s, rot)
    saucer = (X / 1.0) ** 2 + (Y / 0.22) ** 2 < 1.0
    dome = (X / 0.42) ** 2 + ((Y + 0.16) / 0.34) ** 2 < 1.0
    dome = dome & (Y < 0.0)
    ports = np.zeros_like(X, bool)
    for px in (-0.62, -0.31, 0.0, 0.31, 0.62):
        ports |= ((X - px) / 0.07) ** 2 + ((Y - 0.05) / 0.06) ** 2 < 1.0
    beam = (Y > 0.22) & (Y < 0.95) & (np.abs(X) < 0.10 + 0.45 * (Y - 0.22))
    beam_rays = beam & (np.mod(np.floor((X + 2.0) * 10.0 + Y * 6.0), 3) == 0)
    return ((saucer & ~ports) | dome | beam_rays).astype(np.float32)


def ghost(h, w, cx, cy, s, rot=0.0):
    X, Y = _grid(h, w, cx, cy, s, rot)
    head = (X / 0.62) ** 2 + ((Y + 0.30) / 0.60) ** 2 < 1.0
    body = (np.abs(X) < 0.62) & (Y > -0.30) & (Y < 0.60 + 0.10 * np.sin(X * 15.0))
    eye_l = ((X + 0.22) / 0.12) ** 2 + ((Y + 0.30) / 0.17) ** 2 < 1.0
    eye_r = ((X - 0.22) / 0.12) ** 2 + ((Y + 0.30) / 0.17) ** 2 < 1.0
    mouth = (X / 0.14) ** 2 + ((Y - 0.02) / 0.12) ** 2 < 1.0
    return ((head | body) & ~(eye_l | eye_r | mouth)).astype(np.float32)


def flame(h, w, cx, cy, s, rot=0.0):
    X, Y = _grid(h, w, cx, cy, s, rot)
    Yf = -Y
    body = (Yf > -0.9) & (np.abs(X) < 0.55 * np.clip(1.0 - (Yf + 0.9) / 1.9, 0, 1) ** 0.6)
    lick1 = (np.abs(X - 0.22 * (Yf + 0.2)) < 0.12 * np.clip(1.4 - Yf, 0, 1)) & (Yf > 0.2) & (Yf < 1.4)
    lick2 = (np.abs(X + 0.30 + 0.15 * Yf) < 0.10 * np.clip(1.1 - Yf, 0, 1)) & (Yf > 0.0) & (Yf < 1.1)
    core = (Yf > -0.7) & (np.abs(X) < 0.22 * np.clip(1.0 - (Yf + 0.7) / 1.2, 0, 1))
    return ((body | lick1 | lick2) & ~core).astype(np.float32)


def glyph(h, w, cx, cy, s, rot=0.0, seed=1):
    """A rune: 4-7 straight strokes on a 3x5 lattice, one per seed."""
    X, Y = _grid(h, w, cx, cy, s, rot)
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    pts = [(-0.5 + 0.5 * i, -1.0 + 0.5 * j) for i in range(3) for j in range(5)]
    n = int(rng.integers(4, 8))
    out = np.zeros_like(X, bool)
    thick = 0.11
    for _ in range(n):
        a, b = rng.choice(len(pts), 2, replace=False)
        (x0, y0), (x1, y1) = pts[a], pts[b]
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy + 1e-6
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        d = np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy))
        out |= d < thick
    return out.astype(np.float32)


def eye(h, w, cx, cy, s, rot=0.0):
    X, Y = _grid(h, w, cx, cy, s, rot)
    lid = (np.abs(Y) < 0.45 * (1.0 - np.clip(np.abs(X), 0, 1) ** 2)) & (np.abs(X) < 1.0)
    iris = X ** 2 + Y ** 2 < 0.36 ** 2
    pupil = X ** 2 + Y ** 2 < 0.16 ** 2
    return ((lid & ~iris) | (iris & ~pupil)).astype(np.float32)


SHAPES = {"skull": skull, "ufo": ufo, "ghost": ghost, "flame": flame, "glyph": glyph, "eye": eye}


def field(shape, seed, kind, count=5, size=(0.17, 0.30), rot=0.35, full_rot=True, blur=1.5):
    """A distributed, jittered, non-tiled field of one silhouette. Returns 0..1 mask.

    Owner 2026-09-02: the 2048 canvas is a WHOLE CAR whose UV islands point every way,
    so the silhouettes are SMALL (a few percent of the canvas) and ORIENTATION-FREE:
    every instance gets its own full-circle rotation and a coin-flip mirror, so a bat
    upside down on one island reads as well as one upright on another. Each instance is
    rasterised on a local patch (cost is per-shape, not per-canvas) so forty instances
    are as cheap as four.
    """
    h, w = int(shape[0]), int(shape[1])
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    out = np.zeros((h, w), np.float32)
    # stratified placement: a jittered sqrt(count) grid so every panel of the car gets its
    # share (pure rejection sampling clustered 14 skulls into one quarter of the canvas),
    # then a minimum-distance pass so instances never overlap
    pts = []
    n = int(np.ceil(np.sqrt(count)))
    cells = [(i, j) for i in range(n) for j in range(n)]
    rng.shuffle(cells)
    smax = size[1] * min(h, w)
    for (i, j) in cells[:count]:
        for _ in range(40):
            cx = (j + rng.uniform(0.15, 0.85)) / n * w
            cy = (i + rng.uniform(0.15, 0.85)) / n * h
            if all(np.hypot(cx - px, cy - py) > 0.9 * smax for px, py in pts):
                pts.append((cx, cy))
                break
    fn = SHAPES[kind]
    for i, (cx, cy) in enumerate(pts):
        s = rng.uniform(size[0], size[1]) * min(h, w)
        r = rng.uniform(-np.pi, np.pi) if full_rot else rng.uniform(-rot, rot)
        # local patch: silhouettes fit inside ~0.8*s of their centre; keep a margin for rotation
        R = int(np.ceil(0.95 * s)) + 2
        x0, x1 = max(0, int(cx) - R), min(w, int(cx) + R)
        y0, y1 = max(0, int(cy) - R), min(h, int(cy) + R)
        if x1 <= x0 or y1 <= y0:
            continue
        if kind == "glyph":
            m = fn(y1 - y0, x1 - x0, cx - x0, cy - y0, s, r, seed=int(seed) * 7 + i)
        else:
            m = fn(y1 - y0, x1 - x0, cx - x0, cy - y0, s, r)
        if rng.random() < 0.5 and kind != "glyph":
            m = m[:, ::-1]
            # mirror about the instance centre: flip the patch then shift so the centre stays put
            dx = int(round((x1 - x0) - 2 * (cx - x0)))
            m = np.roll(m, dx, axis=1)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], m)
    if cv2 is not None:
        out = cv2.GaussianBlur(out, (0, 0), max(0.8, h / 2048.0 * blur))
    return np.clip(out, 0, 1)


# ─────────────────────────────── the reveal ─────────────────────────────────
# spec cards as (M, R, Cc). Cc: 16 = strongest coat, 255 = none.
BODY_MATTE = (0, 214, 214)      # dielectric matte: dark under a point light
BODY_SATIN = (0, 120, 110)
SECRET_CHROME = (255, 8, 70)    # chrome-tier smooth: the brightest thing at night, tinted by its own albedo
SECRET_GLASS = (0, 8, 16)       # dielectric mirror: a WHITE flash (use when the paint is near-black)


def compose_reveal(carrier, mask, body=BODY_MATTE, secret=SECRET_CHROME, cell_thresh=0.45, invert=False):
    """Spec HxWx3 uint8 from a carrier field (0..1) and a design mask (0..1).

    The body gets `body` on every pixel; the design gets `secret` ONLY where the
    carrier's own fine cells are above `cell_thresh`, so the secret is a halftone
    made of the carrier's texture — no decal outline anywhere in the map.
    `invert` swaps roles (glossy body, dead-matte design: a dark hole at night).
    """
    h, w = carrier.shape
    body_c = np.asarray(body, np.float32)
    sec_c = np.asarray(secret, np.float32)
    if invert:
        body_c, sec_c = sec_c, body_c
    spec = np.empty((h, w, 3), np.float32)
    spec[...] = body_c
    # the body is not one flat material either: its cells take a second, close
    # card so the spec map reads as the carrier's quilt (richness), not a wash
    cells = carrier > cell_thresh
    alt = body_c * 0.7 + np.array([0.0, -60.0, -50.0], np.float32) * 0.3 + np.array([40.0, 0.0, 0.0], np.float32)
    alt = np.clip(alt, 0, 255)
    spec[cells] = alt
    on = (mask > 0.5) & cells
    spec[on] = sec_c
    # a soft band just outside the silhouette in the secret's neighbour tone, so the
    # edge is a gradient of cell states rather than a hard step
    rim = (mask > 0.15) & (mask <= 0.5) & cells
    spec[rim] = body_c * 0.5 + sec_c * 0.5
    return np.clip(spec, 0, 255).astype(np.uint8)


def scores(paint, spec, mask):
    """HIDDEN (day) and REVEAL (night): |mean luma inside - outside| of the mask."""
    def luma(img):
        return 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    inside = mask > 0.5
    outside = mask < 0.05
    out = {}
    for name, light in (("day", DN.DAY), ("dusk", DN.DUSK), ("night", DN.NIGHT)):
        img = DN.appearance(paint, spec, light=light)
        l = luma(img)
        out[name] = float(abs(l[inside].mean() - l[outside].mean()))
    return out


def build_form(form, params, shape, seed):
    fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
    out = fn(shape, seed, **params)
    f = out[0] if isinstance(out, tuple) else out
    f = np.asarray(f, np.float32)
    f = (f - float(f.min())) / max(float(f.max() - f.min()), 1e-6)
    return f
