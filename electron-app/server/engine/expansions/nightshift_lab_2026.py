"""NIGHTSHIFT LAB — true color-flip experiments (owner mission 2026-08-01).

THE TRICK (docs/NIGHTSHIFT_LAB_THEORY.md): iRacing's PBR tints METAL specular by
albedo but keeps dielectric/clearcoat specular WHITE, and metallic kills diffuse.
So interleave two pixel populations at 4-12px scale:
  A "day carrier"   albedo=day hue,  M~0,   G matte,   Cc dull  -> owns daylight
  B "night carrier" albedo=NIGHT hue, M~252, G lanes,  Cc dull  -> fires its OWN
                    hue under night point lights (tinted metal specular)
Day shows A's hue, night shows B's hue => a TRUE hue flip (blue->red, red->gold,
orange->green, pink->blue, teal->magenta, white->rainbow, red->black...).
Follows the owner's proven four-dial physics (clearcoat=power, roughness=
aperture, metal=amplifier, crushed paint — see shokker_engine_v2 install notes,
Blood Marble forensics M252/B255/G-lanes) but splits day/night onto DIFFERENT
pixels with DIFFERENT hues — the unexploited degree of freedom.

Spec mirrors paint geometry (same fields drive both). Features 8-32px @2048.
Multi-tier shade palettes per owner law. Verdict comes from the TRACK TEST.
"""

from __future__ import annotations

from collections import OrderedDict

import cv2
import numpy as np

_W = 1024          # work grid; resized to the render canvas (2048 -> x2)


# ---------------------------------------------------------------- field utils
def _rng(seed, salt):
    return np.random.default_rng((int(seed) & 0x7FFFFFFF) ^ salt)


def _hash01(h, w, rng, cell):
    """Per-cell hash noise upsampled with NEAREST (crisp tiles)."""
    gh, gw = max(2, h // cell), max(2, w // cell)
    g = rng.random((gh, gw), dtype=np.float32)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_NEAREST)


def _smooth(h, w, rng, cell):
    gh, gw = max(2, h // cell), max(2, w // cell)
    g = rng.random((gh, gw), dtype=np.float32)
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)


def _xy(h, w):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return x, y


def _cellF1F2(h, w, rng, cell):
    """Classic jittered-grid cellular noise -> (F1, F2, cell-id hash)."""
    gx = np.arange(-1, w // cell + 2)
    gy = np.arange(-1, h // cell + 2)
    jx = rng.random((len(gy), len(gx)), dtype=np.float32)
    jy = rng.random((len(gy), len(gx)), dtype=np.float32)
    cid = rng.random((len(gy), len(gx)), dtype=np.float32)
    px = (gx[None, :] + jx) * cell
    py = (gy[:, None] + jy) * cell
    x, y = _xy(h, w)
    F1 = np.full((h, w), 1e9, np.float32)
    F2 = np.full((h, w), 1e9, np.float32)
    ID = np.zeros((h, w), np.float32)
    cx0 = (x / cell).astype(np.int32) + 1
    cy0 = (y / cell).astype(np.int32) + 1
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sx = np.clip(cx0 + dx, 0, px.shape[1] - 1)
            sy = np.clip(cy0 + dy, 0, py.shape[0] - 1)
            d = np.sqrt((x - px[sy, sx]) ** 2 + (y - py[sy, sx]) ** 2)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            ID = np.where(closer, cid[sy, sx], ID)
            F1 = np.where(closer, d, F1)
    return F1, F2, ID


def _aa(field, lo, hi):
    """ASCENDING ramp only (lo < hi). A lo>hi call silently degenerates into a
    hard >lo threshold (denominator clamps to 1e-6) — for a descending band
    write 1.0 - _aa(f, hi, lo). This bit three geometries on run 1."""
    return np.clip((field - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)


# 8-tier shade palette per owner law ("many distinct values, not 1-2 levels")
_TIERS = np.float32([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92])


def _tiers(idfield):
    return _TIERS[(np.clip(idfield, 0, 0.999) * 8).astype(np.int32)]


# ---------------------------------------------------------- the shared factory
def _make_ns(gid, day_rgb, night_rgb, geometry, g_lanes=(10, 34, 58), tri_white=False):
    """geometry(h, w, rng) -> dict(b=night mask 0..1, micro, id, [white], [hue])
    b: night-carrier coverage; white: Cc=16 razor mask; hue: 0..1 hue-wheel
    override for the night carrier albedo (ghost_prism)."""

    def _fields(seed):
        rng = _rng(seed, hash(gid) & 0xFFFF)
        f = geometry(_W, _W, rng)
        f.setdefault("micro", _hash01(_W, _W, rng, 2))
        f.setdefault("id", _hash01(_W, _W, rng, 6))
        # macro ratio field: night coverage waxes/wanes across the car (128-256px)
        f["macro"] = _smooth(_W, _W, rng, 192)
        return f

    def _rs(a, fw, fh):
        return cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        f = _fields(seed)
        b = _rs(f["b"], fw, fh)
        micro = _rs(f["micro"], fw, fh)
        idf = _rs(f["id"], fw, fh)
        macro = _rs(f["macro"], fw, fh)
        tier = _tiers(idf)
        # population B waxes/wanes with the macro field but never disappears
        # macro modulates carrier AREA, then re-steepen: a night-carrier pixel is
        # FULLY metal (half-metal reads mushy in PBR and misses the flip) while
        # edges keep a 1px AA ramp. First run shipped soft b straight into M and
        # five finishes fell under the metal threshold — this is the fix.
        b = _aa(np.clip(b * (0.55 + 0.45 * macro), 0, 1), 0.22, 0.50)
        # M: amplifier — ~252 on night carriers, dielectric elsewhere
        M = 5.0 + b * (238.0 + tier * 18.0) + micro * 4.0
        # G: aperture — matte day skin; per-feature lane pick on night carriers
        lane = np.take(np.float32(g_lanes), (idf * len(g_lanes)).astype(np.int32) % len(g_lanes))
        G = (196.0 + micro * 38.0) * (1.0 - b) + (lane + micro * 12.0 + tier * 10.0) * b
        # Cc: PO WER stays off — dull everywhere so no white lobe pollutes the hue
        CC = (238.0 + micro * 16.0) * (1.0 - b) + (230.0 + tier * 22.0) * b
        if tri_white and "white" in f:
            wz = _rs(f["white"], fw, fh)
            CC = CC * (1.0 - wz) + 16.0 * wz          # razor lines: white POWER on
            G = G * (1.0 - wz) + (14.0 + micro * 10.0) * wz
            M = M * (1.0 - wz) + 40.0 * wz            # mostly-dielectric white flash
        out = np.zeros((fh, fw, 4), np.uint8)
        mm = np.clip(m2, 0, 1)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(np.clip(G, 8, 255) * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(np.clip(CC, 16, 255) * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        f = _fields(seed)
        b = _rs(f["b"], fw, fh)[..., None]
        micro = _rs(f["micro"], fw, fh)[..., None]
        idf = _rs(f["id"], fw, fh)
        macro = _rs(f["macro"], fw, fh)[..., None]
        tier = _tiers(idf)[..., None]
        # macro modulates carrier AREA, then re-steepen: a night-carrier pixel is
        # FULLY metal (half-metal reads mushy in PBR and misses the flip) while
        # edges keep a 1px AA ramp. First run shipped soft b straight into M and
        # five finishes fell under the metal threshold — this is the fix.
        b = _aa(np.clip(b * (0.55 + 0.45 * macro), 0, 1), 0.22, 0.50)
        day = np.float32(day_rgb) / 255.0
        if "hue" in f:                                  # spatial hue-wheel night carrier
            hf = _rs(f["hue"], fw, fh)
            hsv = np.stack([hf * 179.0, np.full_like(hf, 235.0), np.full_like(hf, 250.0)], -1)
            night = cv2.cvtColor(hsv.astype(np.uint8)[None] if hsv.ndim == 2 else hsv.astype(np.uint8),
                                 cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0
        else:
            night = np.float32(night_rgb)[None, None, :] / 255.0
        # day skin: crushed toward dark with 8-tier micro shading (pre-crushed paint dial)
        dayf = day[None, None, :] * (0.62 + 0.38 * tier) * (0.92 + 0.16 * micro)
        nightf = night * (0.70 + 0.30 * tier)
        outc = dayf * (1.0 - b) + nightf * b
        if tri_white and "white" in f:
            wz = _rs(f["white"], fw, fh)[..., None]
            outc = outc * (1.0 - wz) + np.float32([0.94, 0.94, 0.96])[None, None, :] * wz
        strength = np.clip(m2 * float(pm), 0, 1)[..., None]
        out = src * (1.0 - strength) + np.clip(outc, 0, 1) * strength
        return out.astype(np.float32)

    return spec_fn, paint_fn


# ------------------------------------------------------------- 10 geometries
def _g_ember(h, w, rng):
    """Lichtenberg ember veins: branching random walks, 2-5px, on black-out body."""
    img = np.zeros((h, w), np.float32)
    for _ in range(150):
        x, y = rng.integers(0, w), rng.integers(0, h)
        ang = rng.random() * 6.283
        for _s in range(rng.integers(18, 60)):
            nx = x + np.cos(ang) * 7
            ny = y + np.sin(ang) * 7
            # draw only when the step stays on-canvas: a %-wrapped endpoint
            # makes cv2.line rip a straight line across the whole texture
            if 0 <= nx < w and 0 <= ny < h:
                cv2.line(img, (int(x), int(y)), (int(nx), int(ny)), 1.0,
                         thickness=int(rng.integers(1, 3)))
            x, y = nx % w, ny % h
            ang += (rng.random() - 0.5) * 1.5
            if rng.random() < 0.12:                    # branch
                ang2 = ang + (0.8 if rng.random() < 0.5 else -0.8)
                bx, by = x + np.cos(ang2) * 14, y + np.sin(ang2) * 14
                if 0 <= bx < w and 0 <= by < h:
                    cv2.line(img, (int(x), int(y)), (int(bx), int(by)), 1.0, 1)
    img = cv2.dilate(img, np.ones((2, 2), np.uint8))
    return {"b": np.clip(img, 0, 1)}


def _g_twill(h, w, rng):
    """Diagonal twill day weave; night = hash-gated dash lanes riding the twill."""
    x, y = _xy(h, w)
    tw = 0.5 + 0.5 * np.sin((x + y) * (2 * np.pi / 9.0))
    gate = _hash01(h, w, rng, 5)
    dash = _aa(tw, 0.55, 0.70) * (gate > 0.42)
    return {"b": dash.astype(np.float32)}


def _g_worley_walls(h, w, rng):
    """Worley shatter: cell WALLS carry the night hue."""
    F1, F2, ID = _cellF1F2(h, w, rng, 22)
    walls = 1.0 - _aa(F2 - F1, 1.2, 3.2)               # thin AA wall band
    return {"b": walls, "id": ID}


def _g_rings(h, w, rng):
    """Interfering micro-ripple rings; ring crests carry the night hue."""
    x, y = _xy(h, w)
    acc = np.zeros((h, w), np.float32)
    for _ in range(46):
        cx, cy = rng.random() * w, rng.random() * h
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        acc += np.sin(d * (2 * np.pi / rng.uniform(9.0, 16.0)))
    acc /= 8.0
    return {"b": _aa(acc, 0.30, 0.70)}


def _g_scales(h, w, rng):
    """Reptile scale lattice: scale EDGES fire at night."""
    F1, F2, ID = _cellF1F2(h, w, rng, 16)
    edge = 1.0 - _aa(F2 - F1, 0.9, 2.6)
    face = _aa(F1, 5.0, 2.0) * 0.0                     # faces stay day carrier
    return {"b": np.clip(edge + face, 0, 1), "id": ID}


def _g_dots(h, w, rng):
    """Day dots on a night interstitial web (inverted carrier)."""
    F1, _F2, ID = _cellF1F2(h, w, rng, 12)
    return {"b": _aa(F1, 3.4, 4.6), "id": ID}          # interstitial web, full metal


def _g_prism(h, w, rng):
    """Flow-combed facets; night carrier hue rides a spatial hue wheel."""
    flow = _smooth(h, w, rng, 96)
    x, y = _xy(h, w)
    ang = flow * 6.283
    comb = 0.5 + 0.5 * np.sin((x * np.cos(ang) + y * np.sin(ang)) * (2 * np.pi / 7.0))
    hue = _smooth(h, w, rng, 128)
    return {"b": _aa(comb, 0.60, 0.80), "hue": hue}


def _g_scan(h, w, rng):
    """Glitch scanline blocks; slivers between blocks carry the night hue."""
    rows = _hash01(h, w, rng, 14)                      # 14px row bands
    cols = _hash01(h, w, rng, 34)
    sliver = ((rows * 7) % 1.0 > 0.82) | ((cols * 11) % 1.0 > 0.90)
    return {"b": sliver.astype(np.float32)}


def _g_argyle(h, w, rng):
    """Argyle diamonds (night) + razor diagonals (WHITE Cc=16) = tri-state."""
    x, y = _xy(h, w)
    u = (x + y) / 11.0
    v = (x - y) / 11.0
    par = ((np.floor(u) + np.floor(v)) % 2).astype(np.float32)
    lines = np.maximum(1.0 - _aa(np.abs(u - np.round(u)), 0.05, 0.10),
                       1.0 - _aa(np.abs(v - np.round(v)), 0.05, 0.10))
    # white mask must reach 1.0 at line cores — a 0.9 cap left Cc at ~39 (>16)
    # and the white razor state never engaged. AA fringes still blend.
    return {"b": par * (1.0 - lines), "white": lines}


def _g_crackle(h, w, rng):
    """Crackle-glaze plates; the CRACKS carry the night hue."""
    F1, F2, ID = _cellF1F2(h, w, rng, 30)
    cracks = 1.0 - _aa(F2 - F1, 0.7, 2.0)
    F1b, F2b, _ = _cellF1F2(h, w, rng, 11)             # second finer craze band
    fine = (1.0 - _aa(F2b - F1b, 0.45, 1.3)) * 0.55
    return {"b": np.clip(cracks + fine, 0, 1), "id": ID}


# ------------------------------------------------------------------ the fleet
#   id                     day RGB          night RGB        geometry     G lanes
NIGHTSHIFT_DEFS = OrderedDict([
    ("ns_ember_reversal",  ((168, 22, 28), (255, 96, 12), _g_ember, (12, 30, 52), False)),
    ("ns_indigo_inferno",  ((36, 48, 132), (255, 34, 18), _g_twill, (10, 26, 44), False)),
    ("ns_violet_verdict",  ((30, 64, 168), (196, 40, 255), _g_worley_walls, (10, 34, 58), False)),
    ("ns_solar_betrayal",  ((158, 16, 24), (255, 208, 40), _g_rings, (8, 22, 40), False)),
    ("ns_toxic_handshake", ((196, 92, 18), (110, 255, 30), _g_scales, (12, 32, 54), False)),
    ("ns_bubblegum_abyss", ((238, 120, 168), (40, 120, 255), _g_dots, (10, 28, 48), False)),
    ("ns_ghost_prism",     ((225, 225, 230), (255, 255, 255), _g_prism, (8, 24, 46), False)),
    ("ns_dead_channel",    ((22, 128, 128), (255, 40, 210), _g_scan, (10, 30, 50), False)),
    ("ns_triple_cross",    ((64, 78, 106), (216, 24, 44), _g_argyle, (12, 34, 56), True)),
    ("ns_furnace_glass",   ((222, 92, 20), (70, 160, 255), _g_crackle, (10, 26, 48), False)),
])


def install_into_engine(mono_reg, base_reg=None):
    n = 0
    for fid, (day, night, geom, lanes, tri) in NIGHTSHIFT_DEFS.items():
        mono_reg[fid] = _make_ns(fid, day, night, geom, lanes, tri)
        n += 1
    try:
        import engine.expansions.fusions as _fus
        for fid, (day, night, geom, lanes, tri) in NIGHTSHIFT_DEFS.items():
            _fus.FUSION_REGISTRY[fid] = mono_reg[fid]
    except Exception:
        pass
    return "nightshift-lab: %d true-color-flip experiments registered" % n
