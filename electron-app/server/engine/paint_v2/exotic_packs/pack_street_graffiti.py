"""STREET ART / GRAFFITI — bold, urban, aggressive generative-math engines for
Shokker Paint Booth. Each produces a FULL-COVERAGE high-contrast scalar field in 0..1
over a whole car. Each is a DIFFERENT algorithm (not a recolor of another, and NOT a
member of any existing family — no voronoi/marble/RD/curl/etc):

  * spray_drip_curtains   — gravity-pulled spray paint: many overspray nozzles deposit
                            soft dot clouds, then a per-column threshold spawns vertical
                            DRIP runs whose length scales with paint load (curtain of runs).
  * splatter_fleck_burst  — explosive splatter: radial droplet ejecta from impact points
                            (ballistic streaks + satellite flecks), DENSE flecking layer
                            fills every gap so coverage is total.
  * stencil_cut_mask      — hard-edge stencil: layered cut shapes (polygon bridges) ANDed
                            into a 1-bit mask, then knocked back with registration offset
                            ghosts -> crisp cut-paper edges everywhere.
  * tape_block_geometry   — masking-tape constructivism: recursive axis-locked rectangle
                            subdivision, each block a flat tone with taped hairline borders
                            and torn-tape feathered edges.
  * wildstyle_blades      — abstract wildstyle: a directional arrow/blade tessellation built
                            from sheared chevron lanes that interlock and bevel into each
                            other (hard diagonal energy, no letters).
  * throwup_scribble      — throw-up fill: a single long self-avoiding-ish scribble polyline
                            rasterized thick with rounded caps, packed to flood the panel
                            (loops over the whole sheet).
  * pasteup_torn_layers   — torn paste-up posters: stacked rectangular poster sheets with
                            fractal-torn edges, peeling corners and print-bleed, layered z.
  * marker_crosshatch     — marker cross-hatching: multiple oriented stroke fields (chisel-tip
                            streaks) multiplied to build tonal hatch density with bleed.
  * bubble_lattice        — segmented bubble letters abstracted to a packed lattice of fat
                            rounded capsules with highlight rims and hard outline (no voronoi:
                            this is a jittered grid of distance-capsules, outlined).
  * tag_ribbon_flow       — tag-stroke calligraphy: pressure-modulated ribbon strokes (variable
                            width swept polylines) flowing edge to edge, hard ink edges.
  * roller_block_fill     — roller / fill-in: broad roller passes (wide overlapping bands with
                            roller-nap streaks and drip skips) building a heavy block coat.

Pure numpy + cv2 + scipy. Deterministic by seed. Computed at low res then upscaled.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
from scipy import ndimage


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _rng(seed):
    return np.random.default_rng(int(seed) & 0xffffffff)


def _norm(a):
    a = a.astype(np.float32)
    p = float(np.ptp(a))
    return (a - a.min()) / (p + 1e-9)


def _up(field, h, w):
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def _fbm(res, rng, octaves=5, base=4, gain=0.55):
    out = np.zeros((res, res), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = min(base * (2 ** o), res)
        lat = rng.standard_normal((n, n)).astype(np.float32)
        out += amp * cv2.resize(lat, (res, res), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= gain
    return out / (tot + 1e-9)


def _sharpen(a, sigma=2.0, amt=0.9):
    return a + amt * (a - cv2.GaussianBlur(a, (0, 0), sigma))


def _halftone(res, rng, pitch=5, jitter=0.0):
    """Crisp halftone dot grid (print screen) -> adds hard edges + fineness to flat fills."""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    ang = rng.uniform(0, np.pi)
    ca, sa = np.cos(ang), np.sin(ang)
    u = xx * ca + yy * sa
    v = -xx * sa + yy * ca
    du = ((u / pitch) % 1.0) - 0.5
    dv = ((v / pitch) % 1.0) - 0.5
    d = np.hypot(du, dv)
    return (d < 0.32).astype(np.float32)


def _grain(res, rng, scale=2):
    """Hard 1-px-ish speckle grain (crisp, not blurred) to keep edges after upscale."""
    g = rng.random((res, res)).astype(np.float32)
    return (g > 0.5).astype(np.float32)


# ---------------------------------------------------------------------------
# 1. SPRAY DRIP CURTAINS — overspray clouds + gravity drip runs
# ---------------------------------------------------------------------------
def spray_drip_curtains(h, w, seed, *, res=512):
    rng = _rng(seed)
    load = np.zeros((res, res), np.float32)
    # many overspray nozzle bursts -> soft dot clouds (stamp gaussians)
    nnoz = 90
    for _ in range(nnoz):
        cx, cy = rng.uniform(0, res, 2)
        spread = rng.uniform(10, 55)
        ndots = int(rng.uniform(120, 320))
        ang = rng.uniform(0, np.pi)
        # elliptical spray cone
        dx = rng.standard_normal(ndots) * spread
        dy = rng.standard_normal(ndots) * spread * rng.uniform(0.5, 1.4)
        ca, sa = np.cos(ang), np.sin(ang)
        px = np.clip((cx + ca * dx - sa * dy).astype(np.int32), 0, res - 1)
        py = np.clip((cy + sa * dx + ca * dy).astype(np.int32), 0, res - 1)
        np.add.at(load, (py, px), rng.uniform(0.4, 1.0, ndots).astype(np.float32))
    load = cv2.GaussianBlur(load, (0, 0), 1.6)
    load = _norm(load)
    # gravity DRIP runs: where column paint load is heavy, paint runs DOWN
    drip = load.copy()
    col_heavy = load.copy()
    # propagate downward with decay -> vertical streaks (curtain of runs)
    decay = 0.965 + 0.02 * rng.random((res,)).astype(np.float32)  # per-column run length
    cur = np.zeros((res,), np.float32)
    for y in range(res):
        spawn = np.where(load[y] > 0.62, load[y], 0.0)
        cur = np.maximum(cur * decay, spawn)
        drip[y] = np.maximum(drip[y], cur)
    # thin the drips (capillary): erode horizontally so runs are narrow
    drip = cv2.erode(drip, np.ones((1, 2), np.uint8))
    out = np.maximum(load * 0.9, drip)
    # crisp spatter speckle to fill any bare spots
    speck = (rng.random((res, res)) > 0.985).astype(np.float32)
    speck = cv2.dilate(speck, np.ones((2, 2), np.uint8))
    out = np.maximum(out, speck * 0.85)
    out = _sharpen(out, 2.0, 0.8)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 2. SPLATTER & FLECK BURST — ballistic ejecta + dense flecking
# ---------------------------------------------------------------------------
def splatter_fleck_burst(h, w, seed, *, res=512):
    rng = _rng(seed)
    canvas = np.zeros((res, res), np.float32)
    # impact bursts: radial droplet streaks (ballistic) from each impact center
    nburst = 26
    for _ in range(nburst):
        cx, cy = rng.uniform(0, res, 2)
        ndrop = int(rng.uniform(40, 120))
        angs = rng.uniform(0, 2 * np.pi, ndrop)
        dist = rng.uniform(4, 90, ndrop) * rng.uniform(0.6, 1.6)
        for k in range(ndrop):
            x1, y1 = cx, cy
            x2 = cx + np.cos(angs[k]) * dist[k]
            y2 = cy + np.sin(angs[k]) * dist[k]
            cv2.line(canvas, (int(x1), int(y1)), (int(x2), int(y2)),
                     float(rng.uniform(0.6, 1.0)), 1, cv2.LINE_AA)
            # satellite drop at end (a fat fleck)
            cv2.circle(canvas, (int(x2), int(y2)),
                       int(rng.uniform(1, 4)), float(rng.uniform(0.7, 1.0)), -1, cv2.LINE_AA)
        # core blob
        cv2.circle(canvas, (int(cx), int(cy)), int(rng.uniform(3, 9)),
                   float(rng.uniform(0.8, 1.0)), -1, cv2.LINE_AA)
    # DENSE flecking layer so coverage is total (thousands of tiny flecks)
    nfl = 9000
    fx = rng.integers(0, res, nfl)
    fy = rng.integers(0, res, nfl)
    np.add.at(canvas, (fy, fx), rng.uniform(0.5, 1.0, nfl).astype(np.float32))
    fleck = (rng.random((res, res)) > 0.94).astype(np.float32)
    fleck = cv2.dilate(fleck, np.ones((2, 2), np.uint8)) * 0.7
    canvas = np.maximum(canvas, fleck)
    canvas = cv2.GaussianBlur(canvas, (0, 0), 0.6)
    canvas = _sharpen(canvas, 1.5, 1.0)
    return _norm(_up(canvas, h, w))


# ---------------------------------------------------------------------------
# 3. STENCIL CUT MASK — layered hard-edge cut shapes + registration ghosts
# ---------------------------------------------------------------------------
def stencil_cut_mask(h, w, seed, *, res=512):
    rng = _rng(seed)
    mask = np.zeros((res, res), np.float32)
    nshapes = 70
    for _ in range(nshapes):
        cx, cy = rng.uniform(0, res, 2)
        sides = int(rng.integers(3, 7))
        r = rng.uniform(18, 70)
        ang0 = rng.uniform(0, 2 * np.pi)
        pts = []
        for s in range(sides):
            a = ang0 + 2 * np.pi * s / sides
            rr = r * rng.uniform(0.55, 1.25)
            pts.append([cx + np.cos(a) * rr, cy + np.sin(a) * rr])
        poly = np.array(pts, np.int32).reshape(-1, 1, 2)
        val = float(rng.uniform(0.55, 1.0))
        cv2.fillPoly(mask, [poly], val, cv2.LINE_8)  # hard edge (no AA)
    # stencil "bridges": cut thin slots so shapes look cut from paper
    bridges = np.zeros((res, res), np.float32)
    for _ in range(140):
        x1, y1 = rng.uniform(0, res, 2)
        ang = rng.uniform(0, np.pi)
        L = rng.uniform(20, 80)
        x2 = x1 + np.cos(ang) * L
        y2 = y1 + np.sin(ang) * L
        cv2.line(bridges, (int(x1), int(y1)), (int(x2), int(y2)), 1.0,
                 int(rng.uniform(2, 5)), cv2.LINE_8)
    mask = mask * (1.0 - bridges)
    # registration-offset ghost (misprint), knocked back
    ghost = np.roll(np.roll(mask, int(rng.uniform(4, 9)), 0), int(rng.uniform(4, 9)), 1)
    out = np.maximum(mask, ghost * 0.45)
    # halftone screen INSIDE the painted shapes (spray-through-stencil dot texture)
    ht = _halftone(res, rng, pitch=rng.uniform(4, 6))
    inside = (out > 0.3).astype(np.float32)
    out = np.where(inside > 0, np.clip(out - ht * 0.35 * inside, 0, 1), out)
    # background gets a crisp halftone + speckle so cells aren't dead-flat (coverage+edge)
    bg_ht = _halftone(res, rng, pitch=rng.uniform(5, 8)) * 0.45
    bg_sp = (_fbm(res, rng, octaves=4, base=10) > 0.15).astype(np.float32) * 0.2
    out = np.maximum(out, np.maximum(bg_ht * (1 - inside), bg_sp * (1 - inside)))
    out = _sharpen(out, 1.2, 0.6)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 4. TAPE BLOCK GEOMETRY — recursive axis-locked rect subdivision + tape edges
# ---------------------------------------------------------------------------
def tape_block_geometry(h, w, seed, *, res=512):
    rng = _rng(seed)
    field = np.zeros((res, res), np.float32)
    edges = np.zeros((res, res), np.float32)

    def split(x0, y0, x1, y1, depth):
        wd, ht = x1 - x0, y1 - y0
        if depth <= 0 or (wd < 24 and ht < 24) or rng.random() < 0.12:
            field[y0:y1, x0:x1] = rng.uniform(0.15, 1.0)
            # taped hairline border
            edges[y0:y0 + 2, x0:x1] = 1.0
            edges[y1 - 2:y1, x0:x1] = 1.0
            edges[y0:y1, x0:x0 + 2] = 1.0
            edges[y0:y1, x1 - 2:x1] = 1.0
            return
        if wd >= ht:
            cut = int(x0 + wd * rng.uniform(0.28, 0.72))
            split(x0, y0, cut, y1, depth - 1)
            split(cut, y0, x1, y1, depth - 1)
        else:
            cut = int(y0 + ht * rng.uniform(0.28, 0.72))
            split(x0, y0, x1, cut, depth - 1)
            split(x0, cut, x1, y1, depth - 1)

    split(0, 0, res, res, 8)
    # torn-tape feathering on the borders
    feather = cv2.GaussianBlur(edges, (0, 0), 1.0)
    noise = _fbm(res, rng, octaves=5, base=10)
    edges = np.clip(edges + (feather * (noise * 0.6)), 0, 1)
    out = np.clip(field * (1.0 - 0.85 * edges) + edges * 0.05, 0, 1)
    # crisp halftone tooth inside blocks so every cell has hard high-freq edges
    ht = _halftone(res, rng, pitch=rng.uniform(4, 6))
    out = np.clip(out - ht * 0.28 * (1 - edges), 0, 1)
    # diagonal hatch streaks within blocks (screen-print feel)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    hatch = (((xx + yy) * 0.25) % 1.0 < 0.5).astype(np.float32)
    out = np.clip(out - hatch * 0.12 * (1 - edges), 0, 1)
    out = _sharpen(out, 1.0, 0.8)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 5. WILDSTYLE BLADES — sheared chevron/arrow tessellation, interlocking bevels
# ---------------------------------------------------------------------------
def wildstyle_blades(h, w, seed, *, res=512):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    field = np.zeros((res, res), np.float32)
    nlanes = int(rng.integers(7, 11))
    shear = rng.uniform(0.6, 1.4) * (1 if rng.random() < 0.5 else -1)
    for li in range(nlanes):
        freq = rng.uniform(7, 14)
        phase = rng.uniform(0, 1)
        u = (xx + shear * yy) / res
        # sawtooth -> sharp chevron ramps (asymmetric for arrow/blade thrust)
        saw = (u * freq + phase) % 1.0
        chevron = np.where(saw < 0.5, saw / 0.5, 1.0 - (saw - 0.5) / 0.5)
        # perpendicular blade tip notch
        v = (yy - shear * 0.4 * xx) / res
        saw2 = (v * (freq * 0.7) + phase * 1.7) % 1.0
        notch = np.where(saw2 < 0.5, saw2 / 0.5, 1.0 - (saw2 - 0.5) / 0.5)
        blade = np.maximum(chevron, notch * 0.85)
        # quantize into hard beveled bands (crisp graffiti facets)
        bands = np.floor(blade * 5.0) / 5.0
        field = np.maximum(field, bands * rng.uniform(0.7, 1.0))
        shear += rng.uniform(-0.25, 0.25)
    # hard keyline outline at facet boundaries (graffiti pop)
    e = _norm(np.hypot(*np.gradient(field)))
    field = np.maximum(field, (e > 0.12).astype(np.float32))
    field = _sharpen(field, 1.0, 0.9)
    return _norm(_up(field, h, w))


# ---------------------------------------------------------------------------
# 6. THROW-UP SCRIBBLE — single thick wandering polyline flooding the panel
# ---------------------------------------------------------------------------
def throwup_scribble(h, w, seed, *, res=512):
    rng = _rng(seed)
    canvas = np.zeros((res, res), np.float32)
    # run several long scribbles to flood coverage
    for strand in range(5):
        x, y = rng.uniform(0, res, 2)
        ang = rng.uniform(0, 2 * np.pi)
        thick = int(rng.uniform(5, 11))
        nsteps = 900
        step = rng.uniform(4, 7)
        # bias the heading so the scribble sweeps across the whole sheet (boustrophedon-ish)
        for i in range(nsteps):
            ang += rng.uniform(-0.7, 0.7)
            # gentle pull toward un-painted regions via a slowly rotating drift
            ang += 0.12 * np.sin(i * 0.05 + strand)
            nx = x + np.cos(ang) * step
            ny = y + np.sin(ang) * step
            # bounce off walls (keeps it on-canvas, dense)
            if nx < 4 or nx > res - 5:
                ang = np.pi - ang
                nx = np.clip(nx, 4, res - 5)
            if ny < 4 or ny > res - 5:
                ang = -ang
                ny = np.clip(ny, 4, res - 5)
            cv2.line(canvas, (int(x), int(y)), (int(nx), int(ny)),
                     1.0, thick, cv2.LINE_AA)
            x, y = nx, ny
    # rounded-cap look + hard ink edge
    canvas = cv2.GaussianBlur(canvas, (0, 0), 0.8)
    ink = (canvas > 0.35).astype(np.float32)
    # inner highlight (fill-in shading) via halftone screen inside the ink
    ht = _halftone(res, rng, pitch=rng.uniform(4, 6))
    out = ink * (0.85 - 0.3 * ht)
    # hard keyline outline (thick) around the throw-up
    e = _norm(np.hypot(*np.gradient(ink)))
    key = cv2.dilate((e > 0.2).astype(np.float32), np.ones((2, 2), np.uint8))
    out = np.maximum(out, key)
    # background = crisp halftone + speckle so empty areas are textured, not dead
    bg_ht = _halftone(res, rng, pitch=rng.uniform(6, 9)) * 0.4
    bg_sp = (_fbm(res, rng, octaves=3, base=14) > 0.2).astype(np.float32) * 0.2
    out = np.maximum(out, np.maximum(bg_ht, bg_sp) * (1 - ink))
    out = _sharpen(out, 1.0, 0.6)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 7. PASTE-UP TORN LAYERS — stacked poster sheets w/ fractal-torn edges
# ---------------------------------------------------------------------------
def pasteup_torn_layers(h, w, seed, *, res=512):
    rng = _rng(seed)
    out = np.full((res, res), 0.08, np.float32)  # wall base
    npost = 22
    for _ in range(npost):
        pw = int(rng.uniform(res * 0.22, res * 0.55))
        ph = int(rng.uniform(res * 0.22, res * 0.55))
        px = int(rng.uniform(-pw * 0.2, res - pw * 0.8))
        py = int(rng.uniform(-ph * 0.2, res - ph * 0.8))
        x0, y0 = max(0, px), max(0, py)
        x1, y1 = min(res, px + pw), min(res, py + ph)
        if x1 <= x0 or y1 <= y0:
            continue
        tone = float(rng.uniform(0.3, 1.0))
        # poster print texture: crisp halftone screen + fbm grain (each sheet printed)
        sub = _fbm(res, rng, octaves=4, base=12)[y0:y1, x0:x1]
        full_ht = _halftone(res, rng, pitch=rng.uniform(4, 7))[y0:y1, x0:x1]
        sub = tone * (0.7 + 0.3 * _norm(sub))
        sub = np.clip(sub - full_ht * 0.3 * tone, 0, 1)
        # fractal-torn edge mask: irregular boundary via thresholded noise near edges
        hh, ww = y1 - y0, x1 - x0
        m = np.ones((hh, ww), np.float32)
        en = _norm(_fbm(max(hh, ww), rng, octaves=5, base=8)[:hh, :ww])
        edge_w = max(4, int(min(hh, ww) * 0.12))
        ramp_x = np.minimum(np.arange(ww), np.arange(ww)[::-1]) / edge_w
        ramp_y = np.minimum(np.arange(hh), np.arange(hh)[::-1]) / edge_w
        ramp = np.minimum(ramp_x[None, :], ramp_y[:, None])
        ramp = np.clip(ramp, 0, 1)
        m = (ramp > (en * 0.9)).astype(np.float32)  # torn ragged border
        # peeling corner: knock a triangular flap
        if rng.random() < 0.5:
            cw = int(min(hh, ww) * rng.uniform(0.15, 0.35))
            for r in range(cw):
                m[r, ww - (cw - r):ww] = 0.0
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - m) + sub * m
        # dark torn-edge shadow line
        em = (cv2.dilate(m, np.ones((3, 3), np.uint8)) - m)
        out[y0:y1, x0:x1] = np.clip(out[y0:y1, x0:x1] - em * 0.4, 0, 1)
    # wall texture on any bare base so background cells aren't dead-flat
    base_ht = _halftone(res, rng, pitch=rng.uniform(6, 9))
    bare = (out < 0.12).astype(np.float32)
    out = np.maximum(out, base_ht * 0.3 * bare)
    out = _sharpen(out, 1.0, 0.8)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 8. MARKER CROSSHATCH — multiplied oriented chisel-stroke fields
# ---------------------------------------------------------------------------
def marker_crosshatch(h, w, seed, *, res=512):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    accum = np.ones((res, res), np.float32)
    ndir = int(rng.integers(3, 5))
    for d in range(ndir):
        ang = rng.uniform(0, np.pi)
        freq = rng.uniform(28, 60)
        ca, sa = np.cos(ang), np.sin(ang)
        u = (xx * ca + yy * sa)
        # chisel-tip streaks: sharp square wave with jittered phase + width
        phase = _fbm(res, rng, octaves=3, base=16) * 12.0
        stripe = ((u + phase) * (freq / res)) % 1.0
        duty = rng.uniform(0.4, 0.6)
        line = (stripe < duty).astype(np.float32)
        # marker bleed along the stroke
        line = cv2.GaussianBlur(line, (0, 0), rng.uniform(0.6, 1.2))
        # ink intensity variation (running-dry marker)
        ink = 0.55 + 0.45 * _norm(_fbm(res, rng, octaves=4, base=10))
        layer = 1.0 - line * ink * rng.uniform(0.5, 0.8)
        accum *= layer
    out = 1.0 - accum  # built-up hatch density (dark = many crossings)
    # hard edge boost
    out = _sharpen(out, 1.2, 1.0)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 9. BUBBLE LATTICE — jittered grid of fat capsules, rimmed + hard outline
# ---------------------------------------------------------------------------
def bubble_lattice(h, w, seed, *, res=384):
    rng = _rng(seed)
    # jittered grid of capsule segments (NOT voronoi — explicit distance to segments,
    # computed via a distance transform of stamped segments for speed)
    g = int(rng.integers(8, 12))
    cell = res / g
    seg_img = np.ones((res, res), np.uint8)  # 1 = far, 0 = on a segment
    for gy in range(g + 1):
        for gx in range(g + 1):
            cx = gx * cell + rng.uniform(-0.25, 0.25) * cell
            cy = gy * cell + rng.uniform(-0.25, 0.25) * cell
            ang = rng.uniform(0, 2 * np.pi)
            L = rng.uniform(0.1, 0.45) * cell
            ax, ay = int(cx + np.cos(ang) * L), int(cy + np.sin(ang) * L)
            bx, by = int(cx - np.cos(ang) * L), int(cy - np.sin(ang) * L)
            cv2.line(seg_img, (ax, ay), (bx, by), 0, 1)
    dist = cv2.distanceTransform(seg_img, cv2.DIST_L2, 3)
    rad = cell * 0.5
    body = np.clip(1.0 - dist / rad, 0, 1)
    bubble = (body > 0.15).astype(np.float32)
    # glossy rim highlight (gradient near the edge of the body)
    rim = np.clip(1.0 - np.abs(body - 0.3) / 0.15, 0, 1)
    # hard black outline ring between bubbles (thick keyline)
    outline = ((body > 0.04) & (body < 0.18)).astype(np.float32)
    out = body * 0.55 + rim * 0.6 + bubble * 0.1
    out = np.clip(out - outline * 0.95, 0, 1)
    # halftone shade inside bubbles + halftone background tooth
    ht = _halftone(res, rng, pitch=rng.uniform(4, 6))
    out = np.clip(out - ht * 0.2 * bubble, 0, 1)
    bg = _halftone(res, rng, pitch=rng.uniform(5, 8)) * 0.3
    out = np.maximum(out, bg * (1 - bubble))
    out = _sharpen(out, 1.0, 0.8)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 10. TAG RIBBON FLOW — pressure-modulated variable-width swept strokes
# ---------------------------------------------------------------------------
def tag_ribbon_flow(h, w, seed, *, res=512):
    rng = _rng(seed)
    canvas = np.zeros((res, res), np.float32)
    nstrokes = 14
    for _ in range(nstrokes):
        x, y = rng.uniform(0, res), rng.uniform(0, res)
        ang = rng.uniform(0, 2 * np.pi)
        nseg = int(rng.uniform(60, 120))
        step = rng.uniform(5, 9)
        base_w = rng.uniform(3, 9)
        prev = (int(x), int(y))
        for i in range(nseg):
            # calligraphic curvature + pressure (width) modulation
            ang += rng.uniform(-0.35, 0.35) + 0.18 * np.sin(i * 0.18)
            x += np.cos(ang) * step
            y += np.sin(ang) * step
            if x < 3 or x > res - 4:
                ang = np.pi - ang
                x = np.clip(x, 3, res - 4)
            if y < 3 or y > res - 4:
                ang = -ang
                y = np.clip(y, 3, res - 4)
            press = base_w * (0.4 + 0.6 * (0.5 + 0.5 * np.sin(i * 0.25 + base_w)))
            cv2.line(canvas, prev, (int(x), int(y)), 1.0, max(1, int(press)), cv2.LINE_AA)
            prev = (int(x), int(y))
    # hard ink edge + thin keyline
    canvas = cv2.GaussianBlur(canvas, (0, 0), 0.7)
    ink = (canvas > 0.3).astype(np.float32)
    e = _norm(np.hypot(*np.gradient(ink)))
    out = ink * 0.85 + (e > 0.2).astype(np.float32) * 0.6
    # drips off the strokes (downward runs)
    drip = ink.copy()
    cur = np.zeros((res,), np.float32)
    for yy in range(res):
        spawn = np.where((ink[yy] > 0.5) & (rng.random(res) > 0.985), 1.0, 0.0)
        cur = np.maximum(cur * 0.95, spawn)
        drip[yy] = np.maximum(drip[yy], cur)
    drip = cv2.erode(drip, np.ones((1, 2), np.uint8))
    out = np.maximum(out, drip * 0.7)
    bg = (_fbm(res, rng, octaves=3, base=14) > 0.25).astype(np.float32) * 0.15
    out = np.maximum(out, bg)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
# 11. ROLLER BLOCK FILL — wide overlapping roller passes w/ nap streaks + skips
# ---------------------------------------------------------------------------
def roller_block_fill(h, w, seed, *, res=512):
    rng = _rng(seed)
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    # base roller coat over the whole panel (nap streaks) -> guaranteed full coverage
    base_ang = rng.uniform(0, np.pi)
    bv = -xx * np.sin(base_ang) + yy * np.cos(base_ang)
    field = 0.3 + 0.15 * np.cos(bv * rng.uniform(0.3, 0.7) + rng.uniform(0, 6))
    field = field.astype(np.float32)
    npass = int(rng.integers(10, 16))
    for _ in range(npass):
        # a roller pass = a wide oriented band with internal nap streaks
        ang = rng.uniform(0, np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        u = xx * ca + yy * sa          # along-roll axis
        v = -xx * sa + yy * ca         # across-roll axis (width)
        center = rng.uniform(0, res)
        width = rng.uniform(40, 110)
        band = np.clip(1.0 - np.abs(v - center) / (width * 0.5), 0, 1)
        band = (band > 0).astype(np.float32) * band
        tone = rng.uniform(0.4, 1.0)
        # roller-nap streaks: fine ridges ALONG the roll direction
        nap = 0.5 + 0.5 * np.cos(v * rng.uniform(0.3, 0.8) + rng.uniform(0, 6))
        # roller skips (paint runs out) modulate along u
        skip = _norm(_fbm(res, rng, octaves=3, base=8))
        skip = (np.interp(u, (u.min(), u.max()), (0, 1)) * 0 + skip)
        load = np.clip(0.55 + 0.45 * skip, 0, 1)
        pass_val = band * tone * (0.6 + 0.4 * nap) * load
        field = np.maximum(field, pass_val)
    # edge buildup where roller laps overlap -> hard band edges
    field = _sharpen(field, 1.5, 0.9)
    # gravity drips off heavy passes
    drip = field.copy()
    cur = np.zeros((res,), np.float32)
    for y in range(res):
        spawn = np.where(field[y] > 0.7, field[y], 0.0)
        cur = np.maximum(cur * 0.96, spawn * (rng.random(res) > 0.97))
        drip[y] = np.maximum(drip[y], cur)
    drip = cv2.erode(drip, np.ones((1, 2), np.uint8))
    out = np.maximum(field, drip * 0.8)
    return _norm(_up(out, h, w))


# ---------------------------------------------------------------------------
ENGINES = {
    "spray_drip_curtains": spray_drip_curtains,
    "splatter_fleck_burst": splatter_fleck_burst,
    "stencil_cut_mask": stencil_cut_mask,
    "tape_block_geometry": tape_block_geometry,
    "wildstyle_blades": wildstyle_blades,
    "throwup_scribble": throwup_scribble,
    "pasteup_torn_layers": pasteup_torn_layers,
    "marker_crosshatch": marker_crosshatch,
    "bubble_lattice": bubble_lattice,
    "tag_ribbon_flow": tag_ribbon_flow,
    "roller_block_fill": roller_block_fill,
}

DESCRIPTIONS = {
    "spray_drip_curtains": "Gravity-pulled spray overspray clouds with vertical drip-run curtains.",
    "splatter_fleck_burst": "Explosive ballistic droplet ejecta plus a dense flecking flood layer.",
    "stencil_cut_mask": "Layered hard-edge stencil cut shapes with bridges and registration ghosts.",
    "tape_block_geometry": "Recursive axis-locked tape-block subdivision with torn taped edges.",
    "wildstyle_blades": "Abstract sheared chevron/arrow blade tessellation, interlocked and outlined.",
    "throwup_scribble": "Thick wandering scribble polylines flooding the panel with hard ink edges.",
    "pasteup_torn_layers": "Stacked paste-up poster sheets with fractal-torn edges and peeling corners.",
    "marker_crosshatch": "Multiplied oriented chisel-tip marker stroke fields building hatch density.",
    "bubble_lattice": "Jittered grid of fat rounded capsules with glossy rims and hard outlines.",
    "tag_ribbon_flow": "Pressure-modulated calligraphic ribbon strokes flowing edge to edge with drips.",
    "roller_block_fill": "Wide overlapping roller passes with nap streaks, skips and lap-edge buildup.",
}


def _selftest(H=1024, seed=12345):
    print(f"{'engine':24s} {'secs':>6s} {'fine':>6s} {'cov':>6s} {'edge':>6s} "
          f"{'std':>6s}  ok")
    allok = True
    rows = []
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(H, H, seed)
        secs = time.time() - t0
        f = np.asarray(f, np.float32)
        finite = bool(np.isfinite(f).all())
        nf = (f - f.min()) / (np.ptp(f) + 1e-9)
        fine = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
        # coverage: 8x8 grid cells with std > 0.035
        cells = []
        for i in range(8):
            for j in range(8):
                c = f[i * H // 8:(i + 1) * H // 8, j * H // 8:(j + 1) * H // 8]
                cells.append(c.std() > 0.035)
        cov = float(np.mean(cells))
        sx = cv2.Sobel(nf, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(nf, cv2.CV_32F, 0, 1, ksize=3)
        eg = np.hypot(sx, sy)
        eg = (eg - eg.min()) / (np.ptp(eg) + 1e-9)
        edge = float(np.mean(eg > 0.18))
        std = float(f.std())
        ok = (secs < 2.5 and fine >= 0.12 and cov >= 0.82 and edge >= 0.12
              and finite and f.min() >= -1e-4 and f.max() <= 1.0 + 1e-4)
        allok = allok and ok
        rows.append((name, secs, fine, cov, edge, std, ok))
        print(f"{name:24s} {secs:6.3f} {fine:6.3f} {cov:6.3f} {edge:6.3f} "
              f"{std:6.3f}  {'OK' if ok else 'FAIL'}")
    print("ALL PASS" if allok else "SOME FAILED")
    if not allok:
        raise SystemExit("self-test failed")
    return rows


if __name__ == "__main__":
    _selftest()
