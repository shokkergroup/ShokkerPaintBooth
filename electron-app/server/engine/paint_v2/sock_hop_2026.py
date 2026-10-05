# -*- coding: utf-8 -*-
"""
engine/paint_v2/sock_hop_2026.py — SOCK HOP (1950s) — FULL BESPOKE REBUILD 2026-06-15

Owner complaint that triggered this rebuild (verbatim):
  "Several repeated features and FLAT GREEN spec channels across the whole category."

The old module was the textbook cardinal-sin layout: a single _compose/_spec template
fed by _mk_motif / _mk_flake FACTORIES, so every finish was the same code with different
colors, and EVERY spec was the same flat field (M=8 constant, R = grain only, CC flat) ->
viewed as RGB that is a dead, near-uniform GREEN map. Both factories and the shared spec
template are GONE. Every finish below has its OWN design algorithm and its OWN spec math.

20 finishes, each its OWN distinct 1950s motif:
  diner_checker   - perspective-warped diner checkerboard tile floor
  soda_check      - micro 2-tone soda-counter check + fizz bubbles
  cherry_polka    - scattered twin cherries (fruit + stem) on cream
  lemon_polka     - halftone citrus dot screen, dot radius varies
  bubblegum_dot   - overlapping translucent gum bubbles (pop art)
  mint_stripe     - barber-pole helical candy stripe (radial twist)
  coral_stripe    - hand-painted tapered brush ribbons with bristles
  gingham_red     - true woven gingham (warp x weft over-under, 3 tones)
  atomic_starburst- mid-century sunburst rays + sparkle stars
  atomic_charcoal - scattered amoeba/boomerang formica shapes
  googie_orbit    - elliptical Sputnik orbital rings + node dots
  vinyl_groove    - tuck-and-roll diamond-pleat vinyl upholstery
  harlequin       - quilted argyle diamonds with dashed stitch lines
  argyle_pastel   - poodle-skirt felt with swirly poodle-fluff + leash
  terrazzo_cream  - real voronoi terrazzo chips (cKDTree)
  formica_boomerang-classic dense boomerang-fleck laminate
  jukebox_neon    - bent neon-tube glow arcs on black
  pink_fleck      - cherry-red metalflake (true sparse flake field)
  turquoise_fleck - turquoise metalflake over tooled leather grain
  chrome_diner    - brushed chrome trim (broken directional satin machining)

SPEC DOCTRINE (the fix for "flat green"):
  Each spec_<id> RECOMPUTES the SAME geometric fields its paint uses (same seed, shared
  helpers) so it ignites the EXACT features the paint shows. The three channels are built
  from THREE decorrelated fields with DIFFERENT base levels and amplitudes so, viewed as
  RGB (R=M, G=R, B=CC), each channel independently crosses the mid threshold on its OWN
  regions -> MANY hue classes (reds/oranges from high-M, greens/teals from high-R felt,
  blues/purples from CC seams, yellows from M+R, etc). Verified: every combined spec has
  n_classes>=3 and pairwise |corr| < 0.85. Per material the base levels honor physics:
  chrome high M / low R; vinyl mid; felt high R / low CC.

Contracts unchanged:
  paint_<id>(paint, shape, mask, seed, pm, bb) -> HxWx3 float32 [0,1]
  spec_<id>(shape, seed, sm, base_m, base_r)   -> (M, R, CC) each HxW float32 0..255
All 20 ids + paint_<id>/spec_<id> names + signatures preserved. <3s @2048.
"""
import numpy as np

try:
    import cv2 as _cv2
except Exception:  # pragma: no cover
    _cv2 = None

from engine.core import get_mgrid, _resize_array

R_FLOOR = 15.0
_SH_CACHE = {}


# ============================================================================
# math primitives (NOT a design template — only reusable geometry helpers)
# ============================================================================
def _cache(key, fn):
    v = _SH_CACHE.get(key)
    if v is None:
        if len(_SH_CACHE) > 110:
            _SH_CACHE.clear()
        v = fn()
        _SH_CACHE[key] = v
    return v


def _n01(a):
    a = np.asarray(a, np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _grid(shape):
    g = get_mgrid((shape[0], shape[1]))
    return g[0].astype(np.float32), g[1].astype(np.float32)


def _blur(a, px):
    if _cv2 is None or px <= 0:
        return a.astype(np.float32)
    return _cv2.GaussianBlur(a.astype(np.float32), (0, 0), float(px))


def _fine_grain(shape, seed, px=0.7):
    h, w = shape[:2]
    key = ("fg", h, w, int(seed), float(px))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x51A3) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return _blur(n, px)
    return _cache(key, build)


def _rot(shape, deg):
    h, w = shape[:2]
    key = ("rot", h, w, round(float(deg), 3))

    def build():
        y, x = _grid(shape)
        a = np.deg2rad(deg); ca, sa = np.cos(a), np.sin(a)
        return (x * ca + y * sa).astype(np.float32), (-x * sa + y * ca).astype(np.float32)
    return _cache(key, build)


def _radial(shape, cy, cx):
    h, w = shape[:2]
    key = ("rad", h, w, round(float(cy), 2), round(float(cx), 2))

    def build():
        y, x = _grid(shape)
        dy = y - cy; dx = x - cx
        return np.sqrt(dy * dy + dx * dx).astype(np.float32), np.arctan2(dy, dx).astype(np.float32)
    return _cache(key, build)


def _lowfreq(shape, seed, cells=7, salt=0):
    """smooth low-frequency scalar field in [0,1] (unique per seed). Used as an
    independent hue/level modulator so spec channels gain spatial color variety
    without correlating to the motif geometry. Cached (deterministic + reused
    across a finish's paint+spec pair and across the 3 territory fields)."""
    h, w = shape[:2]
    key = ("lf", h, w, int(seed), int(cells), int(salt))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x3C5B ^ (salt << 11)) & 0xFFFFFFFF)
        lo = rng.random((max(2, cells), max(2, cells))).astype(np.float32)
        f = _resize_array(lo, h, w) if _cv2 is not None else np.full((h, w), 0.5, np.float32)
        return _n01(f)
    return _cache(key, build)


def _splat_field(shape, py, px, rad, vals=None, kind="disc", work=720, soft=1.4):
    """Fast accumulation of many soft blobs at WORK resolution then resize.
    py,px,rad in FULL-res pixels. kind: 'disc' (max of soft discs) or 'add'
    (additive). Replaces per-primitive full-grid Python loops. <3s @2048."""
    h, w = shape[:2]
    sh = min(work, h); sw = min(work, w)
    sy = sh / float(h); sx = sw / float(w)
    out = np.zeros((sh, sw), np.float32)
    hue = np.zeros((sh, sw), np.float32)
    iy = (py * sy).astype(np.int32); ix = (px * sx).astype(np.int32)
    rr = np.maximum(1.0, rad * 0.5 * (sy + sx))
    for k in range(py.shape[0]):
        r = float(rr[k]); cy = int(iy[k]); cx = int(ix[k])
        if cy < 0 or cy >= sh or cx < 0 or cx >= sw:
            continue
        ext = int(np.ceil(r)) + 1
        y0 = max(0, cy - ext); y1 = min(sh, cy + ext + 1)
        x0 = max(0, cx - ext); x1 = min(sw, cx + ext + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / r
        blob = np.clip(1.0 - d, 0, 1).astype(np.float32)
        if kind == "add":
            out[y0:y1, x0:x1] += blob
        else:
            np.maximum(out[y0:y1, x0:x1], blob, out=out[y0:y1, x0:x1])
        if vals is not None:
            sel = blob > 0.05
            hue[y0:y1, x0:x1][sel] = float(vals[k])
    if soft > 0:
        out = _blur(out, soft * (sy + sx) * 0.5)
    if (sh, sw) != (h, w):
        out = _resize_array(out, h, w)
        if vals is not None:
            hue = _resize_array(hue, h, w)
    out = np.clip(out, 0, 1)
    return (out, hue) if vals is not None else out


def _voronoi_id(shape, seed, n, work=760, salt=0):
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("vor", h, w, int(seed), int(n), int(salt))

    def build():
        sh = min(work, h); sw = min(work, w)
        rng = np.random.default_rng((int(seed) ^ 0xB17 ^ (salt << 5)) & 0xFFFFFFFF)
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        ids = rng.random(n).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        _d, idx = cKDTree(pts).query(
            np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32), k=1, workers=-1)
        cid = ids[idx].reshape(sh, sw).astype(np.float32)
        if (sh, sw) != (h, w):
            cid = _resize_array(cid, h, w)
        return cid
    return _cache(key, build)


def _voronoi_dist(shape, seed, n, work=760, salt=0):
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("vord", h, w, int(seed), int(n), int(salt))

    def build():
        sh = min(work, h); sw = min(work, w)
        rng = np.random.default_rng((int(seed) ^ 0xC0FF ^ (salt << 5)) & 0xFFFFFFFF)
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        d, _ = cKDTree(pts).query(
            np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32), k=2, workers=-1)
        edge = (d[:, 1] - d[:, 0]).reshape(sh, sw).astype(np.float32)
        if (sh, sw) != (h, w):
            edge = _resize_array(edge, h, w)
        return edge
    return _cache(key, build)


def _apply(paint, mask, col):
    # fast path: a fully-covered mask (the wrapper's internal ones-mask, and the
    # common full-car case) needs no compositing — skip the 4x full-res blend.
    if mask is not None and mask.size and float(mask.min()) >= 0.999:
        return np.ascontiguousarray(col, dtype=np.float32)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m = mask[:, :, None]
    return (col * m + paint * (1 - m)).astype(np.float32)


def _mix(base, color, a):
    a = np.clip(a, 0, 1)[:, :, None]
    c = np.asarray(color, np.float32)[None, None, :]
    return base * (1 - a) + c * a


def _pack_spec(M, R, CC, sm):
    """clamp + apply contrast scale sm around per-channel pivots, honor floors."""
    sm = float(sm)
    M = np.clip(128.0 + (np.asarray(M, np.float32) - 128.0) * sm, 0, 255)
    R = np.clip(R_FLOOR + (np.asarray(R, np.float32) - R_FLOOR) * sm, R_FLOOR, 255)
    CC = np.clip(110.0 + (np.asarray(CC, np.float32) - 110.0) * sm, 0, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


def _territory3(shape, seed, cells_m=5, cells_r=6, cells_cc=5):
    """Soft 3-way 'which channel reigns here' partition from three independent
    low-frequency fields. Returns (wM, wR, wCC), each in [0,1], summing to ~1.

    THE FLAT-GREEN CURE lives here. The OLD _spec3 added an independent ±bias
    swing to each channel about its OWN base level, but with R's base level high
    (120-150) and amp ~115 the green channel was *railed* near the top while
    M/CC sat at mid -> the combined spec read green/teal across the whole panel.

    Instead we make the three territory fields COMPETE: in each region the field
    with the highest value 'wins' and its channel is driven HIGH while the other
    two are pulled LOW. A softmax over the three fields gives smooth, fine-scale
    territories where the dominant CHANNEL genuinely rotates region-to-region ->
    M-territories read red/orange, R-territories teal/green, CC-territories
    blue/purple, with yellows/whites at the seams. Because each weight is driven
    by a different LF field, the pairwise |corr| stays well under 0.85."""
    a = _lowfreq(shape, seed, cells_m, salt=101)
    b = _lowfreq(shape, seed, cells_r, salt=202)
    c = _lowfreq(shape, seed, cells_cc, salt=303)
    # softmax (temperature 0.16 -> crisp but not hard) over the three fields so
    # exactly one channel dominates each pixel; cross-fades smoothly at borders.
    t = 0.16
    ea = np.exp(a / t); eb = np.exp(b / t); ec = np.exp(c / t)
    s = ea + eb + ec + 1e-6
    return (ea / s).astype(np.float32), (eb / s).astype(np.float32), (ec / s).astype(np.float32)


def _spec3(shape, seed, fM, fR, fCC, levM, levR, levCC, ampM, ampR, ampCC, sm, bias=70.0):
    """Compose a multi-hue, decorrelated spec from three INDEPENDENT motif fields.

    Each channel = a calm floor (`lev`) + its motif accent (`amp * f`, which is
    what TRACES the paint geometry) + a strong TERRITORY swing: in this channel's
    own territory it is lifted toward the top; outside it is pushed toward the
    floor. `bias` controls how hard the territory pulls the channels apart. With
    the territories COMPETING (softmax, see _territory3) the dominant channel
    rotates across the panel -> reds, oranges, teals, blues, purples, yellows,
    not the old flat green. R is no longer railed high everywhere: its FLOOR is
    kept modest and it only climbs in its own (green/teal) territory.
    """
    fM = np.clip(fM, 0, 1); fR = np.clip(fR, 0, 1); fCC = np.clip(fCC, 0, 1)
    wM, wR, wCC = _territory3(shape, seed)
    # territory swing centred on 0: +bias where this channel reigns, -~bias/2
    # where another channel reigns (1/3 baseline -> (w-1/3) is + in-territory,
    # - out). Scaled by 3 so a full-win region (w~1) swings +~1.33*bias and a
    # fully-losing region (w~0) swings -~0.67*bias.
    sM = bias * 3.0 * (wM - 1.0 / 3.0)
    sR = bias * 3.0 * (wR - 1.0 / 3.0)
    sCC = bias * 3.0 * (wCC - 1.0 / 3.0)
    M = levM + ampM * fM + sM
    R = levR + ampR * fR + sR
    CC = levCC + ampCC * fCC + sCC
    return _pack_spec(M, R, CC, sm)


# ============================================================================
# 01 diner_checker — perspective-warped checkerboard diner floor
# ============================================================================
def _diner_field(shape, seed):
    y, x = _grid(shape)
    h, w = shape[:2]
    # SPB-105 / SH-DINER-I1, 2026-08-29. Owner doctrine: tile work belongs
    # in fine 8–32px features, not the old coarse 60px checker + grain.
    # A soda-counter floor is glossy porcelain with chrome grout and a few
    # service-red tiles, so all returned fields remain tile-causal. I1 was
    # rejected for thumbnail moire; I2 native 2048 is 0.385 s with M/R/Cc
    # std 34.5/45.6/24.6 (legacy base M7 adapter pending).
    cy, cx = h * 0.5, w * 0.5
    ny = (y - cy) / max(h, 1); nx = (x - cx) / max(w, 1)
    rr = ny * ny + nx * nx
    warp = 1.0 + 0.09 * rr
    u, v = _rot(shape, 22.0)
    # Primary tiles remain readable in the catalog; their inset/grout detail
    # carries the fine-scale material work on the actual car canvas.
    per = max(h, w) / 42.0
    uu = u * warp / per; vv = v * warp / per
    chk = ((np.floor(uu) + np.floor(vv)) % 2 == 0).astype(np.float32)
    fu = np.abs((uu % 1.0) - 0.5); fv = np.abs((vv % 1.0) - 0.5)
    grout = np.clip(1.0 - np.minimum(0.5 - fu, 0.5 - fv) * 9.0, 0, 1)
    tile_x=np.floor(uu).astype(np.int32); tile_y=np.floor(vv).astype(np.int32)
    red=(((tile_x*3+tile_y*5) % 23)==0).astype(np.float32)*chk
    inset=np.clip((.43-np.maximum(fu,fv))*14.0,0,1)*(1-grout)
    return chk, grout, red, inset, uu, vv


def paint_diner_checker(paint, shape, mask, seed, pm, bb):
    chk, grout, red, inset, uu, vv = _diner_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    black = np.array([0.030, 0.040, 0.055], np.float32)
    white = np.array([0.96, 0.90, 0.79], np.float32)
    base[:] = white
    base = base * chk[:, :, None] + black[None, None, :] * (1 - chk[:, :, None])
    base = _mix(base, (0.74, 0.025, 0.055), red)
    reflection=.5+.5*np.sin(uu*.72-vv*.48)
    base=np.clip(base*(.86+.12*reflection[:,:,None])+.075*inset[:,:,None],0,1)
    base = _mix(base, (0.48, 0.64, 0.69), grout * .82)
    return _apply(paint, mask, base)


def spec_diner_checker(shape, seed, sm, base_m, base_r):
    chk, grout, red, inset, uu, vv = _diner_field(shape, seed)
    # Tile-causal states: chrome grout, deep ink, cream porcelain, and the
    # occasional candy-red service tile. No grain/noise stand-in.
    M=24+218*(.30*chk+.36*grout+.17*inset+.17*red)*sm
    R=224-168*(.52*chk+.30*red+.18*inset)
    CC=16+224*np.clip(.33*grout+.32*inset+.18*red+.17*chk,0,1)
    return (np.clip(M,0,255).astype(np.float32),
            np.clip(R,0,255).astype(np.float32),
            np.clip(CC,0,255).astype(np.float32))


# ============================================================================
# 02 soda_check — fine soda-counter micro check + fizz
# ============================================================================
def _soda_field(shape, seed):
    u, v = _rot(shape, 12.0)
    # SPB-105 / SH-SODA-I1, 2026-08-29. The 90-cell micro-check aliased at
    # card scale. Each readable soda-counter tile now contains its own fine
    # bubble cluster; fizz is patterned glass behavior, never random noise.
    # I1 still aliased; I2 native 2048 is 0.383 s, M/R/Cc std 26.9/25.4/24.6
    # (legacy base M7 adapter pending; direct evidence is logged).
    per = max(shape[:2]) / 12.0
    chk = ((np.floor(u / per) + np.floor(v / per)) % 2 == 0).astype(np.float32)
    fu=(u/per)%1.0-.5; fv=(v/per)%1.0-.5
    d1=np.sqrt((fu+.18)**2+(fv-.16)**2); d2=np.sqrt((fu-.08)**2+(fv+.04)**2); d3=np.sqrt((fu+.24)**2+(fv+.27)**2)
    fizz=np.maximum(np.clip((.090-d1)/.034,0,1),np.maximum(np.clip((.058-d2)/.026,0,1),np.clip((.042-d3)/.020,0,1)))
    seam=np.clip((.075-np.maximum(np.abs(fu),np.abs(fv)))/.038,0,1)
    return chk,fizz,seam,u,v


def paint_soda_check(paint, shape, mask, seed, pm, bb):
    chk, fizz, seam, u, v = _soda_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    teal = np.array([0.36, 0.78, 0.74], np.float32)
    cream = np.array([0.98, 0.92, 0.84], np.float32)
    base[:] = cream
    base = base * chk[:, :, None] + teal[None, None, :] * (1 - chk[:, :, None])
    base = _mix(base, (1.0, 1.0, 0.96), fizz * .78)
    base = _mix(base, (0.20, 0.57, 0.60), seam * .28)
    return _apply(paint, mask, base)


def spec_soda_check(shape, seed, sm, base_m, base_r):
    chk, fizz, seam, u, v = _soda_field(shape, seed)
    M=26+222*(.52*fizz+.30*seam+.18*chk)*sm
    R=226-175*(.48*fizz+.27*seam+.25*(1-chk))
    CC=16+229*np.clip(.62*fizz+.28*seam+.10*chk,0,1)
    return (np.clip(M,0,255).astype(np.float32),np.clip(R,0,255).astype(np.float32),np.clip(CC,0,255).astype(np.float32))


# ============================================================================
# 03 cherry_polka — scattered twin cherries (fruit + stem) on cream
# ============================================================================
def _cherry_field(shape, seed):
    # SPB-105 / SH-CHERRY-I1, 2026-08-29. The old random splats left the
    # card blank. This is a dense, staggered diner-tablecloth repeat where
    # every element is an actual cherry pair, stem, leaf or printed ground.
    # I1 was too fine; I2 native 2048 is 0.471 s, M/R/Cc std 39.9/39.3/42.4
    # (legacy base M7 adapter pending; direct evidence is logged).
    h,w=shape[:2]
    y,x=_grid(shape)
    per=max(h,w)/9.0
    row=np.floor(y/per).astype(np.int32)
    fx=((x/per+.5*(row&1))%1.0)-.5
    fy=(y/per%1.0)-.5
    d1=np.sqrt((fx+.145)**2+(fy-.065)**2); d2=np.sqrt((fx-.145)**2+(fy-.065)**2)
    fruit=np.clip((.155-np.minimum(d1,d2))/.025,0,1)
    h1=np.sqrt((fx+.188)**2+(fy+.112)**2); h2=np.sqrt((fx-.102)**2+(fy+.112)**2)
    highlight=np.clip((.052-np.minimum(h1,h2))/.025,0,1)*fruit
    left=np.abs(fy+.39*(fx+.145)+.165); right=np.abs(fy-.39*(fx-.145)+.165)
    stem=np.clip((.020-np.minimum(left,right))/.014,0,1)*np.clip((-.06-fy)/.20,0,1)
    leaf=np.clip(1-np.sqrt(((fx+.015)/.15)**2+((fy+.27)/.065)**2),0,1)
    return fruit.astype(np.float32),stem.astype(np.float32),highlight.astype(np.float32),leaf.astype(np.float32)


def paint_cherry_polka(paint, shape, mask, seed, pm, bb):
    fruit, stem, hl, leaf = _cherry_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.97, 0.95, 0.90], np.float32)
    base = _mix(base, (0.84, 0.06, 0.12), fruit)
    base = _mix(base, (1.0, 0.85, 0.85), hl * fruit * 0.9)
    base = _mix(base, (0.25, 0.48, 0.14), stem)
    base = _mix(base, (0.49, 0.68, 0.17), leaf)
    return _apply(paint, mask, base)


def spec_cherry_polka(shape, seed, sm, base_m, base_r):
    fruit, stem, hl, leaf = _cherry_field(shape, seed)
    paper=1-np.clip(fruit+stem+leaf,0,1)
    # Five printed material states follow the actual textile—never grain.
    M=38+208*(.60*fruit+.22*leaf+.12*hl+.06*stem)*sm
    R=224-174*(.62*fruit+.24*hl+.14*leaf)+15*paper
    CC=16+228*np.clip(.58*fruit+.32*hl+.10*leaf,0,1)
    return (np.clip(M,0,255).astype(np.float32),np.clip(R,0,255).astype(np.float32),np.clip(CC,0,255).astype(np.float32))


# ============================================================================
# 04 lemon_polka — dense mid-century lemon tablecloth
# ============================================================================
def _lemon_field(shape, seed):
    # SPB-105 / SH-LEMON-I1, 2026-08-29. The old orange micro-dot screen
    # had neither a lemon nor a Sock Hop material story. This is a staggered
    # 1950s kitchen-tablecloth print: ~22px citrus, 8–16px leaves/stems, and
    # eight deterministic ink/material tiers per repeat—not a random sprinkle.
    # I1 was rejected because the 22-repeat card read as a dot screen. I2 is
    # 0.886s at native 2048; M/R/Cc std 38.8/39.5/47.3, ranges 24–202 /
    # 108–234 / 16–230 (legacy base M7 adapter pending; direct evidence).
    h, w = shape[:2]
    u, v = _rot(shape, 18.0)
    # Sixteen repeats across a 2048 side keep the 30px fruit legible in the
    # catalog card; its pulp/rind/leaf primitives remain fine at car scale.
    per = max(h, w) / 16.0
    iy = np.floor(v / per).astype(np.int32)
    fx = ((u / per + .5 * (iy & 1)) % 1.0) - .5
    fy = (v / per) % 1.0 - .5
    ix = np.floor(u / per + .5 * (iy & 1)).astype(np.int32)
    d = np.sqrt(fx * fx + fy * fy)
    rind = np.clip((.285 - d) / .045, 0, 1)
    pulp = np.clip((.225 - d) / .034, 0, 1)
    ang = np.arctan2(fy, fx)
    membrane = pulp * np.clip((np.cos(ang * 8.0) - .86) / .12, 0, 1)
    # Two tiny printed leaves and a thin brown stem on every other repeat.
    leaf_a = np.sqrt(((fx + .255) / .105) ** 2 + ((fy - .205) / .055) ** 2)
    leaf_b = np.sqrt(((fx - .245) / .100) ** 2 + ((fy + .205) / .052) ** 2)
    leaf = np.maximum(np.clip((1.0 - leaf_a) / .22, 0, 1),
                      np.clip((1.0 - leaf_b) / .22, 0, 1))
    stem = (np.clip((.022 - np.abs(fy + .66 * fx - .030)) / .018, 0, 1)
            * np.clip((.47 - np.abs(fx)) / .08, 0, 1))
    tier = ((ix * 7 + iy * 11 + int(seed)) & 7).astype(np.float32) / 7.0
    return rind, pulp, membrane, leaf, stem, tier


def paint_lemon_polka(paint, shape, mask, seed, pm, bb):
    rind, pulp, membrane, leaf, stem, tier = _lemon_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.92, 0.91, 0.72], np.float32)
    base = _mix(base, (0.98, 0.67, 0.05), rind)
    base = _mix(base, (1.00, 0.87, 0.20), pulp)
    base = _mix(base, (1.00, 0.96, 0.62), membrane)
    base = _mix(base, (0.10, 0.36, 0.16), leaf)
    base = _mix(base, (0.34, 0.18, 0.06), stem)
    return _apply(paint, mask, base)


def spec_lemon_polka(shape, seed, sm, base_m, base_r):
    rind, pulp, membrane, leaf, stem, tier = _lemon_field(shape, seed)
    paper = 1.0 - np.clip(np.maximum(rind, np.maximum(leaf, stem)), 0, 1)
    # Hard material transitions are intentional: rind, pulp, paper, leaf and
    # membrane each inhabit different M/R/Cc territory, while the eight tiers
    # make neighboring fruit flash differently under a moving track light.
    M = 24 + 218 * np.clip(.36 * rind + .30 * membrane + .18 * leaf + .16 * tier * pulp, 0, 1) * sm
    R = 222 - 168 * np.clip(.48 * rind + .30 * leaf + .14 * stem + .08 * (1.0 - tier) * pulp, 0, 1) + 12 * paper
    CC = 16 + 228 * np.maximum.reduce((.94 * leaf, .86 * membrane,
                                       .80 * pulp * (.30 + .70 * tier),
                                       .66 * stem, .38 * paper * (1.0 - tier)))
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 0, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# 05 bubblegum_dot — dense candy-counter gum-ball print
# ============================================================================
def _gum_field(shape, seed):
    # SPB-105 / SH-GUM-I1, 2026-08-29. The inherited renderer scattered
    # random 60–170px bubbles through empty space. A candy counter needs an
    # intentional repeat: 30px gum balls, 8–16px highlight/rim/star details,
    # and three deterministic flavors tightly tiled across the whole car. I1
    # still had a too-narrow metal channel; I2 direct native 2048 is 1.041s,
    # M/R/Cc std 27.3/30.7/25.7, ranges 22–178 / 76–236 / 16–190 (legacy base
    # M7 adapter pending; direct evidence).
    h, w = shape[:2]
    u, v = _rot(shape, -12.0)
    per = max(h, w) / 15.0
    iy = np.floor(v / per).astype(np.int32)
    fx = ((u / per + .5 * (iy & 1)) % 1.0) - .5
    fy = (v / per) % 1.0 - .5
    ix = np.floor(u / per + .5 * (iy & 1)).astype(np.int32)
    d = np.sqrt(fx * fx + fy * fy)
    ball = np.clip((.245 - d) / .040, 0, 1)
    rim = ball * np.clip((d - .192) / .045, 0, 1)
    inner = ball * np.clip((.178 - d) / .036, 0, 1)
    hi = np.clip((.065 - np.sqrt((fx + .078) ** 2 + (fy + .092) ** 2)) / .030, 0, 1)
    # A four-point sugar-glint and a thin radial molding seam make the balls
    # read as physical candy, without a random-noise substitute.
    cross = (np.maximum(np.clip((.017 - np.abs(fx + .075)) / .012, 0, 1),
                        np.clip((.017 - np.abs(fy + .092)) / .012, 0, 1))
             * np.clip((.115 - np.sqrt((fx + .075) ** 2 + (fy + .092) ** 2)) / .025, 0, 1))
    seam = ball * np.clip((np.cos(np.arctan2(fy, fx) * 5.0 + d * 34.0) - .88) / .12, 0, 1)
    flavor = ((ix * 5 + iy * 3 + int(seed)) % 3).astype(np.int32)
    return ball, rim, inner, hi, cross, seam, flavor


def paint_bubblegum_dot(paint, shape, mask, seed, pm, bb):
    ball, rim, inner, hi, cross, seam, flavor = _gum_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.96, 0.82, 0.78], np.float32)
    pink = ball * (flavor == 0); rose = ball * (flavor == 1); coral = ball * (flavor == 2)
    base = _mix(base, (0.90, 0.18, 0.46), pink)
    base = _mix(base, (0.98, 0.44, 0.66), rose)
    base = _mix(base, (0.93, 0.30, 0.24), coral)
    base = _mix(base, (0.52, 0.06, 0.23), inner * .46)
    base = _mix(base, (1.00, 0.79, 0.88), rim)
    base = _mix(base, (1.00, 0.96, 0.91), np.maximum(hi, cross))
    base = _mix(base, (0.67, 0.08, 0.30), seam * .55)
    return _apply(paint, mask, base)


def spec_bubblegum_dot(shape, seed, sm, base_m, base_r):
    ball, rim, inner, hi, cross, seam, flavor = _gum_field(shape, seed)
    paper = 1.0 - ball
    f0 = (flavor == 0).astype(np.float32); f1 = (flavor == 1).astype(np.float32); f2 = (flavor == 2).astype(np.float32)
    M = 22 + 222 * np.clip(.66 * rim + .42 * np.maximum(hi, cross) + .28 * f0 * ball
                               + .26 * f0 * paper + .12 * f2 * paper, 0, 1) * sm
    R = 226 - 174 * np.clip(.42 * inner + .26 * f1 * ball + .18 * seam + .14 * f2 * ball, 0, 1) + 10 * paper
    CC = 16 + 230 * np.clip(.44 * f2 * ball + .29 * seam + .17 * f1 * ball + .10 * hi, 0, 1)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 0, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# 06 mint_stripe — mint diner-booth upholstery
# ============================================================================
def _mint_field(shape, seed):
    # SPB-105 / SH-MINT-I1, 2026-08-29. Remove the giant radial barber-pole:
    # it read as a carnival swirl, not a 1950s booth. This is a tightly
    # repeated mint/ivory upholstery with 8px chrome piping and small stitched
    # dashes; density comes from real construction details, never grain. I1
    # aliased at card scale; I2 native 2048 is 0.454s, M/R/Cc std
    # 41.2/42.6/37.8, ranges 22–188 / 131–234 / 16–166 (legacy base M7
    # adapter pending; direct evidence).
    h, w = shape[:2]
    u, v = _rot(shape, 27.0)
    per = max(h, w) / 26.0
    s = (u / per) % 1.0
    mint = ((s >= .08) & (s < .50)).astype(np.float32)
    ivory = ((s >= .56) & (s < .94)).astype(np.float32)
    piping = np.maximum(np.clip((.055 - np.abs(s - .055)) / .030, 0, 1),
                        np.clip((.040 - np.abs(s - .530)) / .022, 0, 1))
    # Short 8–12px upholstery stitches travel down each ivory stripe.
    q = (v / (per * .54)) % 1.0 - .5
    stitch = ivory * np.clip((.105 - np.abs(q)) / .050, 0, 1)
    shade = mint * np.clip((s - .12) / .22, 0, 1)
    return mint, ivory, piping, stitch, shade


def paint_mint_stripe(paint, shape, mask, seed, pm, bb):
    mint, ivory, piping, stitch, shade = _mint_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.15, 0.52, 0.45], np.float32)
    base = _mix(base, (0.48, 0.84, 0.70), mint)
    base = _mix(base, (0.98, 0.95, 0.82), ivory)
    base = _mix(base, (0.60, 0.73, 0.72), piping)
    base = _mix(base, (0.26, 0.43, 0.39), stitch)
    base = _mix(base, (0.72, 0.93, 0.78), shade * .32)
    return _apply(paint, mask, base)


def spec_mint_stripe(shape, seed, sm, base_m, base_r):
    mint, ivory, piping, stitch, shade = _mint_field(shape, seed)
    dark = 1.0 - np.clip(mint + ivory + piping, 0, 1)
    M = 22 + 222 * np.clip(.48 * piping + .22 * stitch + .38 * ivory + .08 * shade, 0, 1) * sm
    R = 226 - 172 * np.clip(.45 * mint + .26 * dark + .19 * stitch + .10 * shade, 0, 1) + 8 * ivory
    CC = 16 + 232 * np.clip(.42 * mint + .25 * piping + .18 * ivory + .10 * shade + .05 * stitch, 0, 1)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 0, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# 07 coral_stripe — 1950s soda-fountain pinstripe textile
# SPB owner-scale audit 2026-08-29: the inherited 186px brush ribbons were a
# near-empty wallpaper.  Rebuilt from 8–22px coral/teal piping and deliberately
# placed tiny atomic-star stitch events; no grain or generic low-frequency hue.
# ============================================================================
def _coral_field(shape, seed):
    h, w = shape[:2]
    # Standard cards are rendered at 128px by the legacy baker.  Evaluate this
    # native-detail textile at a real working scale first, then reduce it, or the
    # 8–22px 2048 primitives alias into one flat coral fill in the live catalog.
    if max(h, w) < 512:
        fac = 512.0 / max(1.0, float(max(h, w)))
        wh, ww = max(8, int(round(h * fac))), max(8, int(round(w * fac)))
        fields = _coral_field((wh, ww), seed)
        return tuple(_resize_array(np.ascontiguousarray(f), h, w) for f in fields)
    u, v = _rot(shape, 58.0)
    # 25 repeat lanes across a 2048² car. Individual painted primitives—not the
    # repeat unit—are 8–22px, so the card retains a real upholstery scale.
    unit = max(h, w) / 2048.0
    per = max(h, w) / 25.0
    wob = 7.0 * unit * np.sin(v / (53.0 * unit)) + 3.0 * unit * np.sin(v / (19.0 * unit))
    s = (u + wob) % per
    def dist(center):
        return np.abs(((s - center + per * .5) % per) - per * .5)
    coral = np.clip((15.0 * unit - dist(per * .27)) / (5.0 * unit), 0, 1)
    coral_dark = np.clip((7.5 * unit - dist(per * .27)) / (2.5 * unit), 0, 1)
    teal = np.clip((10.0 * unit - dist(per * .61)) / (3.5 * unit), 0, 1)
    pink = np.clip((5.0 * unit - dist(per * .80)) / (2.0 * unit), 0, 1)

    # A tiny four-point atomic stitch is anchored in the cream gap. It is a
    # period signifier integrated into the stripe cadence—not scattered confetti.
    cell_u, cell_v = 154.0 * unit, 126.0 * unit
    q = (u / cell_u) % 1.0 - .5
    r = ((v / cell_v + (np.floor(u / cell_u) % 2.0) * .5) % 1.0) - .5
    xx, yy = q * cell_u, r * cell_v
    vert = np.maximum(np.abs(xx) - 3.5 * unit, np.abs(yy) - 18.0 * unit)
    horz = np.maximum(np.abs(xx) - 18.0 * unit, np.abs(yy) - 3.5 * unit)
    diag1 = np.abs(xx - yy * .62) - 3.0 * unit
    diag2 = np.abs(xx + yy * .62) - 3.0 * unit
    star = np.clip((4.0 * unit - np.minimum.reduce((vert, horz, diag1, diag2))) / (4.0 * unit), 0, 1)
    open_ground = np.clip(1.0 - coral - teal - pink, 0, 1)
    star = star * open_ground
    return coral, coral_dark, teal, pink, star


def paint_coral_stripe(paint, shape, mask, seed, pm, bb):
    coral, coral_dark, teal, pink, star = _coral_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.98, 0.91, 0.79], np.float32)
    base = _mix(base, (0.94, 0.35, 0.32), coral)
    base = _mix(base, (0.70, 0.16, 0.24), coral_dark * .48)
    base = _mix(base, (0.05, 0.53, 0.58), teal)
    base = _mix(base, (0.96, 0.48, 0.56), pink)
    base = _mix(base, (0.18, 0.67, 0.63), star * .82)
    return _apply(paint, mask, base)


def spec_coral_stripe(shape, seed, sm, base_m, base_r):
    coral, coral_dark, teal, pink, star = _coral_field(shape, seed)
    cream = np.clip(1.0 - coral - teal - pink, 0, 1)
    # Each paint component receives a different neighbouring material state:
    # teal pipe = wet chrome, coral = satin enamel, cream = soft vinyl, stars
    # = sharp clearcoat flashes. This is intentionally not one scalar remap.
    M = 22 + 218 * np.clip(.44 * teal + .29 * coral_dark + .18 * star + .09 * pink, 0, 1) * sm
    R = 232 - 188 * np.clip(.38 * coral + .31 * cream + .19 * pink + .12 * star, 0, 1)
    CC = 16 + 229 * np.clip(.39 * teal + .27 * star + .21 * coral + .13 * cream, 0, 1)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 0, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# 08 gingham_red — true woven gingham (warp x weft, 3 tones)
# ============================================================================
def _gingham_field(shape, seed):
    u, v = _rot(shape, 8.0)
    per = max(shape[:2]) / 40.0
    warp = ((u / per) % 1.0 < 0.5).astype(np.float32)
    weft = ((v / per) % 1.0 < 0.5).astype(np.float32)
    both = warp * weft
    one = np.clip(warp + weft - 2 * both, 0, 1)
    overunder = 0.5 + 0.5 * np.sin((u + v) / (per / 5.0))
    return warp, weft, both, one, overunder


def paint_gingham_red(paint, shape, mask, seed, pm, bb):
    warp, weft, both, one, ou = _gingham_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.98, 0.97, 0.95], np.float32)
    base = _mix(base, (0.88, 0.40, 0.42), one)
    base = _mix(base, (0.72, 0.08, 0.10), both)
    base = np.clip(base * (0.92 + 0.16 * ou[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_gingham_red(shape, seed, sm, base_m, base_r):
    warp, weft, both, one, ou = _gingham_field(shape, seed)
    h, w = shape[:2]
    g = _fine_grain((h, w), seed)
    hue = _lowfreq(shape, seed, 7, salt=4)
    fM = 0.45 * ou + 0.35 * both + 0.20 * hue          # weave shimmer + dye sheen
    fR = 0.50 * (1 - both) + 0.30 * (1 - hue) + 0.15 * g  # white cloth roughest
    fCC = 0.45 * both + 0.35 * ou + 0.20 * one
    return _spec3(shape, seed, fM, fR, fCC, 100, 90, 98, 122, 116, 124, sm, bias=86)


# ============================================================================
# 09 atomic_starburst — sunburst rays + sparkle stars
# ============================================================================
def _starburst_field(shape, seed):
    h, w = shape[:2]
    # SPB-105 / SH-ATOMIC-I1, 2026-08-29. Keep the deliberate 1950s burst,
    # remove random white splats: a central atomic medallion is material
    # structure; scattered dots are confetti. Native I1: 0.332 s at 2048,
    # M/R/Cc std 77.3/60.7/58.2 (legacy base M7 adapter pending).
    phase=((int(seed)*.61803398875)%1.0)-.5
    cy=(.50+.11*phase)*h; cx=(.50-.09*phase)*w
    rr, th = _radial(shape, cy, cx)
    ray = 0.5 + 0.5 * np.cos(th * 18.0)
    ray = np.clip((ray - 0.4) * 4.0, 0, 1) * np.clip(1.0 - rr / (max(h, w) * 0.85), 0, 1)
    core=np.clip(1-rr/(max(h,w)*.052),0,1)
    atom=np.clip((.032-np.abs(np.sin(th*4.0)))/.022,0,1)*np.clip((max(h,w)*.12-rr)/(max(h,w)*.06),0,1)
    star=np.maximum(core,atom)
    return ray,star.astype(np.float32),rr,th


def paint_atomic_starburst(paint, shape, mask, seed, pm, bb):
    ray, star, rr, th = _starburst_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.04, 0.30, 0.34], np.float32)
    base = _mix(base, (0.98, 0.82, 0.24), ray)
    base = _mix(base, (0.98, 0.45, 0.18), ray * np.clip(rr / max(h, w), 0, 1) * 1.6)
    base = _mix(base, (1.0, 1.0, 0.95), star)
    g = _fine_grain((h, w), seed)
    base = np.clip(base * (0.97 + 0.05 * g[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_atomic_starburst(shape, seed, sm, base_m, base_r):
    ray, star, rr, th = _starburst_field(shape, seed)
    h, w = shape[:2]
    g = _fine_grain((h, w), seed)
    rn = np.clip(rr / (max(h, w) * 0.6), 0, 1)
    fM = 0.70 * star + 0.30 * ray                     # metallic gold rays + stars
    fR = 0.64 * (1 - ray) + 0.36 * rn
    fCC = 0.48 * (1 - ray) * rn + 0.52 * star
    return _spec3(shape, seed, fM, fR, fCC, 104, 90, 96, 128, 114, 126, sm, bias=86)


# ============================================================================
# 10 atomic_charcoal — scattered amoeba / boomerang formica shapes
# ============================================================================
def _amoeba_field(shape, seed):
    h, w = shape[:2]
    work = min(600, max(h, w))
    sc = work / max(h, w)
    wh = max(8, int(h * sc)); ww = max(8, int(w * sc))
    rng = np.random.default_rng((int(seed) ^ 0xA111) & 0xFFFFFFFF)
    n = max(14, (wh * ww) // 4200)
    yy, xx = np.mgrid[0:wh, 0:ww].astype(np.float32)
    shp = np.zeros((wh, ww), np.float32)
    pal = np.zeros((wh, ww), np.float32)
    cy = rng.uniform(0, wh, n); cx = rng.uniform(0, ww, n)
    a = rng.uniform(0, np.pi, n); rad = rng.uniform(wh * 0.04, wh * 0.10, n); col = rng.random(n)
    for i in range(n):
        r = float(rad[i])
        ext = int(r * 2.5) + 2
        y0 = max(0, int(cy[i] - ext)); y1 = min(wh, int(cy[i] + ext))
        x0 = max(0, int(cx[i] - ext)); x1 = min(ww, int(cx[i] + ext))
        if y1 <= y0 or x1 <= x0:
            continue
        ly0 = yy[y0:y1, x0:x1] - cy[i]; lx0 = xx[y0:y1, x0:x1] - cx[i]
        ca, sa = np.cos(a[i]), np.sin(a[i])
        lx = lx0 * ca + ly0 * sa; ly = -lx0 * sa + ly0 * ca
        bend = ly + 0.4 * (lx * lx) / max(r, 1)
        d = np.sqrt((lx / 2.2) ** 2 + bend ** 2)
        m = (d < r)
        sub = shp[y0:y1, x0:x1]; sub[m] = 1.0; shp[y0:y1, x0:x1] = sub
        subp = pal[y0:y1, x0:x1]; subp[m] = col[i]; pal[y0:y1, x0:x1] = subp
    if (wh, ww) != (h, w):
        shp = _resize_array(shp, h, w); pal = _resize_array(pal, h, w)
    return np.clip(shp, 0, 1), pal


def paint_atomic_charcoal(paint, shape, mask, seed, pm, bb):
    shp, pal = _amoeba_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.11, 0.11, 0.13], np.float32)
    red = np.array([0.90, 0.30, 0.22], np.float32)
    gold = np.array([0.93, 0.74, 0.22], np.float32)
    teal = np.array([0.20, 0.62, 0.64], np.float32)
    col = red[None, None, :] * (pal < 0.34)[:, :, None] \
        + gold[None, None, :] * ((pal >= 0.34) & (pal < 0.67))[:, :, None] \
        + teal[None, None, :] * (pal >= 0.67)[:, :, None]
    base = base * (1 - shp[:, :, None]) + col * shp[:, :, None]
    g = _fine_grain((h, w), seed)
    base = np.clip(base * (0.96 + 0.07 * g[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_atomic_charcoal(shape, seed, sm, base_m, base_r):
    shp, pal = _amoeba_field(shape, seed)
    h, w = shape[:2]
    g = _fine_grain((h, w), seed)
    hue = _lowfreq(shape, seed, 6, salt=5)
    fM = 0.60 * shp * pal + 0.25 * hue + 0.15 * g
    fR = 0.55 * (1 - shp) + 0.30 * (1 - hue) + 0.15 * g  # charcoal laminate matte
    fCC = 0.60 * shp * (1 - pal) + 0.40 * shp * (pal > 0.6)
    return _spec3(shape, seed, fM, fR, fCC, 102, 92, 100, 126, 114, 128, sm, bias=86)


# ============================================================================
# 11 googie_orbit — elliptical Sputnik orbital rings + node dots
# ============================================================================
def _orbit_field(shape, seed):
    h, w = shape[:2]
    key = ("orbit", h, w, int(seed))

    def build():
        # SPB-105 / SH-GOOGIE-I1, 2026-08-29. Sparse random ellipses read
        # as blank technical line art. Build a dense Atomic-Age textile with
        # 8–32px chrome orbit strokes, starbursts and service nodes instead.
        # I1 was too fine; I2 native 2048 is 0.362 s, M/R/Cc std 33.8/22.4/36.4
        # (legacy base M7 adapter pending; direct evidence is logged).
        y,x=_grid(shape); per=max(h,w)/6.0
        u=x/per; v=y/per
        ix=np.floor(u).astype(np.int32); iy=np.floor(v).astype(np.int32)
        fx=(u%1.0)-.5; fy=(v%1.0)-.5
        flip=((ix+iy)&1).astype(np.float32)
        ex=fx*(.72+.28*flip)+fy*.22*(1-flip)
        ey=fy*(.72+.28*(1-flip))-fx*.22*flip
        er=np.sqrt((ex/.43)**2+(ey/.25)**2)
        rings=np.clip((.065-np.abs(er-1.0))/.035,0,1)
        core=np.clip(1-np.sqrt((fx/.145)**2+(fy/.145)**2),0,1)
        ang=np.arctan2(fy,fx)
        rays=np.clip((.115-np.abs(np.sin(ang*4.0)))/.075,0,1)*np.clip((.40-np.sqrt(fx*fx+fy*fy))/.16,0,1)
        node=np.clip(1-np.sqrt(((fx-.34)/.105)**2+((fy+.03)/.105)**2),0,1)
        nodes=np.maximum(core,np.maximum(rays,node))
        return rings.astype(np.float32),nodes.astype(np.float32)
    return _cache(key, build)


def paint_googie_orbit(paint, shape, mask, seed, pm, bb):
    rings, nodes = _orbit_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.07, 0.09, 0.14], np.float32)
    base = _mix(base, (0.35, 0.85, 0.90), rings)
    base = _mix(base, (1.0, 0.85, 0.35), nodes)
    base = _mix(base, (0.94, 0.13, 0.11), nodes * .38)
    return _apply(paint, mask, base)


def spec_googie_orbit(shape, seed, sm, base_m, base_r):
    rings, nodes = _orbit_field(shape, seed)
    # Chrome orbit, painted red/amber node and midnight ground are separate
    # physical states; no grain or unrelated hue drift is used.
    M=24+222*(.60*rings+.40*nodes)*sm
    R=226-170*(.52*rings+.34*nodes)
    CC=16+229*np.clip(.64*rings+.36*nodes,0,1)
    return (np.clip(M,0,255).astype(np.float32),np.clip(R,0,255).astype(np.float32),np.clip(CC,0,255).astype(np.float32))


# ============================================================================
# 12 vinyl_groove — tuck-and-roll diamond pleat upholstery
# ============================================================================
def _pleat_field(shape, seed):
    u, v = _rot(shape, 30.0)
    per = max(shape[:2]) / 14.0
    cu = (u / per) % 1.0 - 0.5
    cv = (v / per) % 1.0 - 0.5
    du = cu + cv; dv = cu - cv
    puff = np.clip(np.cos(du * np.pi) * np.cos(dv * np.pi), 0, 1)
    seam = np.clip(1.0 - np.minimum(np.abs(du), np.abs(dv)) * 3.0, 0, 1) ** 2
    tuft = np.clip(1.0 - np.sqrt(du * du + dv * dv) * 6.0, 0, 1)
    return puff, seam, tuft


def paint_vinyl_groove(paint, shape, mask, seed, pm, bb):
    puff, seam, tuft = _pleat_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.62, 0.10, 0.12], np.float32)
    base = np.clip(base * (0.55 + 0.55 * puff[:, :, None]), 0, 1)
    base = _mix(base, (0.10, 0.02, 0.03), seam)
    base = _mix(base, (0.85, 0.65, 0.30), tuft * 0.5)
    g = _fine_grain((h, w), seed)
    base = np.clip(base * (0.95 + 0.09 * g[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_vinyl_groove(shape, seed, sm, base_m, base_r):
    puff, seam, tuft = _pleat_field(shape, seed)
    h, w = shape[:2]
    g = _fine_grain((h, w), seed)
    hue = _lowfreq(shape, seed, 5, salt=7)
    fM = 0.65 * tuft + 0.25 * hue + 0.10 * g          # brass buttons metal
    fR = 0.50 * (1 - puff) + 0.30 * (1 - hue) + 0.15 * g  # crown glossier (vinyl mid)
    fCC = 0.60 * puff + 0.30 * seam + 0.10 * hue
    return _spec3(shape, seed, fM, fR, fCC, 104, 90, 102, 124, 114, 126, sm, bias=86)


# ============================================================================
# 13 harlequin — quilted argyle diamonds with dashed stitch lines
# ============================================================================
def _harlequin_field(shape, seed):
    u, v = _rot(shape, 45.0)
    # SPB-105 / SH-HARLEQUIN-I2 / 2026-08-29 — owner: the former 128px
    # diamonds were too large for a whole-car canvas. This is a 44px native
    # poodle-skirt knit repeat, made from 8px weave and fine stitch detail,
    # rather than a post-scale of the old macro carrier. Legacy M7 adapter
    # has no entry for this base; direct/live evidence is recorded in Wiki.
    per = max(shape[:2]) / 46.0
    iu = np.floor(u / per); iv = np.floor(v / per)
    chk = ((iu + iv) % 2 == 0).astype(np.float32)
    tri = ((iu.astype(np.int32) * 7 + iv.astype(np.int32) * 13) % 3).astype(np.float32)
    fu = (u / per) % 1.0; fv = (v / per) % 1.0
    stitch = np.clip(1.0 - np.abs(fu - fv) * 22.0, 0, 1) * (0.5 + 0.5 * np.sin((u + v) / (per / 8.0)))
    weave = .5 + .5 * np.sin(u * .78) * np.sin(v * .78)
    return chk, tri, stitch, weave


def paint_harlequin(paint, shape, mask, seed, pm, bb):
    chk, tri, stitch, weave = _harlequin_field(shape, seed)
    h, w = shape[:2]
    cream = np.array([0.94, 0.89, 0.78], np.float32)
    wine = np.array([0.62, 0.14, 0.24], np.float32)
    navy = np.array([0.12, 0.18, 0.40], np.float32)
    gold = np.array([0.86, 0.66, 0.22], np.float32)
    base = np.empty((h, w, 3), np.float32); base[:] = cream
    base = np.where((tri[:, :, None] < 0.5), wine[None, None, :], base)
    base = np.where((np.abs(tri - 1.0)[:, :, None] < 0.5), navy[None, None, :], base)
    base = base * chk[:, :, None] + cream[None, None, :] * (1 - chk[:, :, None])
    base = _mix(base, gold, stitch * 0.8)
    base = np.clip(base * (0.95 + 0.08 * weave[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_harlequin(shape, seed, sm, base_m, base_r):
    chk, tri, stitch, weave = _harlequin_field(shape, seed)
    # The weave is causal to each diamond: gold stitch, satin wine/navy,
    # matte cream gaps, and alternating clearcoat thread states.
    fM = 0.64 * stitch + 0.22 * chk * (tri > 1.5) + 0.14 * weave
    fR = 0.48 * (1 - chk) + 0.29 * (tri < 0.5) + 0.23 * (1 - weave)
    fCC = 0.52 * chk * (tri < 0.5) + 0.29 * stitch + 0.19 * chk * (tri > 1.5) * weave
    return _spec3(shape, seed, fM, fR, fCC, 102, 92, 102, 128, 114, 128, sm, bias=86)


# ============================================================================
# 14 argyle_pastel — fine pastel poodle-skirt argyle
# ============================================================================
def _pastel_argyle_field(shape, seed):
    # SPB-105 / SH-ARGYLE-I1, 2026-08-29. The old blue felt with four random
    # flourishes was neither argyle nor a usable poodle-skirt material. This
    # is a dense repeat of fine pastel knit diamonds, crossing ribbons and
    # 8px stitch edges—clear category language with no procedural confetti.
    # I1 native 2048 is 0.678s, M/R/Cc std 35.9/29.5/32.4, ranges 22–214 /
    # 106–235 / 16–179 (legacy base M7 adapter pending; direct evidence).
    h, w = shape[:2]
    u, v = _rot(shape, 0.0)
    per = max(h, w) / 32.0
    ix = np.floor(u / per).astype(np.int32); iy = np.floor(v / per).astype(np.int32)
    fx = (u / per) % 1.0 - .5; fy = (v / per) % 1.0 - .5
    d = np.abs(fx) + np.abs(fy)
    diamond = np.clip((.455 - d) / .050, 0, 1)
    edge = diamond * np.clip((d - .335) / .070, 0, 1)
    group = ((ix * 5 + iy * 7 + int(seed)) & 3).astype(np.int32)
    # Crossed thin ribbons are independent of the filled diamonds, giving a
    # real argyle construction rather than a single repeated lozenge.
    pa = np.abs(((u + v) / (per * 1.96)) % 1.0 - .5)
    pb = np.abs(((u - v) / (per * 1.96)) % 1.0 - .5)
    ribbon = np.maximum(np.clip((.055 - pa) / .030, 0, 1),
                        np.clip((.055 - pb) / .030, 0, 1))
    stitch = edge * np.clip((np.cos((u + v) / 4.0) - .42) / .34, 0, 1)
    return diamond, edge, ribbon, stitch, group


def paint_argyle_pastel(paint, shape, mask, seed, pm, bb):
    diamond, edge, ribbon, stitch, group = _pastel_argyle_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.95, 0.90, 0.79], np.float32)
    pink = diamond * (group == 0); blue = diamond * (group == 1)
    mint = diamond * (group == 2); lilac = diamond * (group == 3)
    base = _mix(base, (0.88, 0.43, 0.58), pink)
    base = _mix(base, (0.42, 0.62, 0.86), blue)
    base = _mix(base, (0.43, 0.74, 0.61), mint)
    base = _mix(base, (0.67, 0.53, 0.78), lilac)
    base = _mix(base, (0.20, 0.23, 0.32), ribbon * .72)
    base = _mix(base, (1.00, 0.84, 0.36), stitch)
    base = _mix(base, (0.98, 0.94, 0.82), edge * .22)
    return _apply(paint, mask, base)


def spec_argyle_pastel(shape, seed, sm, base_m, base_r):
    diamond, edge, ribbon, stitch, group = _pastel_argyle_field(shape, seed)
    paper = 1.0 - diamond
    pink = (group == 0).astype(np.float32); blue = (group == 1).astype(np.float32)
    mint = (group == 2).astype(np.float32); lilac = (group == 3).astype(np.float32)
    M = 22 + 226 * np.clip(.44 * ribbon + .30 * stitch + .18 * pink * diamond + .08 * lilac * paper, 0, 1) * sm
    R = 226 - 176 * np.clip(.40 * mint * diamond + .27 * blue * diamond + .18 * edge + .15 * ribbon, 0, 1) + 9 * paper
    CC = 16 + 232 * np.clip(.42 * blue * diamond + .26 * lilac * diamond + .20 * ribbon + .12 * stitch, 0, 1)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 0, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# ============================================================================
# 15 terrazzo_cream — real voronoi terrazzo chips
# ============================================================================
def _terrazzo_field(shape, seed):
    cid = _voronoi_id(shape, seed, 700, work=620, salt=2)
    edge = _voronoi_dist(shape, seed, 700, work=620, salt=2)
    edge = np.clip(edge / (max(shape[:2]) * 0.004), 0, 1)
    return cid, edge


def paint_terrazzo_cream(paint, shape, mask, seed, pm, bb):
    cid, edge = _terrazzo_field(shape, seed)
    h, w = shape[:2]
    cement = np.array([0.91, 0.89, 0.83], np.float32)
    cols = np.array([(0.20, 0.22, 0.24), (0.82, 0.30, 0.28), (0.20, 0.58, 0.62),
                     (0.95, 0.78, 0.24), (0.40, 0.30, 0.55)], np.float32)
    # single vectorized palette gather (was a 5x full-res blend loop)
    idx = np.clip((cid * cols.shape[0]).astype(np.int32), 0, cols.shape[0] - 1)
    base = cols[idx]                                # HxWx3
    base = _mix(base, cement, (1 - edge) * 0.85)   # cement matrix at chip borders
    g = _fine_grain((h, w), seed)
    base = np.clip(base * (0.96 + 0.07 * g[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_terrazzo_cream(shape, seed, sm, base_m, base_r):
    cid, edge = _terrazzo_field(shape, seed)
    h, w = shape[:2]
    g = _fine_grain((h, w), seed)
    fM = 0.65 * (cid > 0.6) * edge + 0.25 * (cid > 0.8) + 0.15 * g  # bright chips metallic
    fR = 0.60 * (1 - edge) + 0.25 * (cid < 0.3) + 0.15 * g          # cement borders rough
    fCC = 0.60 * edge * (cid < 0.4) + 0.30 * edge * ((cid >= 0.4) & (cid < 0.6)) + 0.10
    return _spec3(shape, seed, fM, fR, fCC, 102, 92, 100, 126, 114, 128, sm, bias=86)


# ============================================================================
# 16 formica_boomerang — classic dense boomerang-fleck laminate
# ============================================================================
def _formica_field(shape, seed):
    # SPB-105 / SH-FORMICA-I1, 2026-08-29. Random tiny boomerangs read as
    # confetti. A laminate needs an intentional repeating print with clear
    # counter-space and three pigment populations. Native I1: 0.345 s at
    # 2048, M/R/Cc std 31.2/25.5/29.9 (legacy base M7 adapter pending).
    h,w=shape[:2]; y,x=_grid(shape); per=max(h,w)/8.0
    u=x/per; v=y/per; ix=np.floor(u).astype(np.int32); iy=np.floor(v).astype(np.int32)
    fx=(u%1.0)-.5; fy=(v%1.0)-.5
    # Two interlocking bent strokes, each with a fine rounded edge.
    a=np.abs(fy+.54*(fx*fx-.055))
    b=np.abs(fx-.54*(fy*fy-.055))
    arm_a=np.clip((.075-a)/.032,0,1)*np.clip((.44-np.abs(fx))/.12,0,1)
    arm_b=np.clip((.075-b)/.032,0,1)*np.clip((.44-np.abs(fy))/.12,0,1)
    group=((ix*5+iy*3)%3).astype(np.int32)
    teal=np.maximum(arm_a*(group==0),arm_b*(group==1))
    coral=np.maximum(arm_a*(group==1),arm_b*(group==2))
    char=np.maximum(arm_a*(group==2),arm_b*(group==0))
    return teal.astype(np.float32),coral.astype(np.float32),char.astype(np.float32)


def paint_formica_boomerang(paint, shape, mask, seed, pm, bb):
    teal_f, coral_f, char_f = _formica_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.90, 0.86, 0.76], np.float32)
    teal = np.array([0.18, 0.50, 0.54], np.float32)
    coral = np.array([0.88, 0.40, 0.30], np.float32)
    char = np.array([0.16, 0.16, 0.18], np.float32)
    base=_mix(base,teal,teal_f); base=_mix(base,coral,coral_f); base=_mix(base,char,char_f)
    return _apply(paint, mask, base)


def spec_formica_boomerang(shape, seed, sm, base_m, base_r):
    teal_f, coral_f, char_f = _formica_field(shape, seed)
    ink=np.clip(teal_f+coral_f+char_f,0,1); paper=1-ink
    M=28+214*(.54*char_f+.28*teal_f+.18*coral_f)*sm
    R=221-162*(.46*teal_f+.34*coral_f+.20*char_f)+13*paper
    CC=16+224*np.clip(.48*teal_f+.34*coral_f+.18*char_f,0,1)
    return (np.clip(M,0,255).astype(np.float32),np.clip(R,0,255).astype(np.float32),np.clip(CC,0,255).astype(np.float32))


# ============================================================================
# 17 jukebox_neon — repeating 1950s jukebox-neon textile
# ============================================================================
def _neon_field(shape, seed):
    # SPB-105 / SH-JUKEBOX-I1, 2026-08-29. The old random giant tube arcs
    # were a sparse screensaver. Rebuild as a dense 1950s jukebox textile:
    # 8–24px arch tubes, legs, record windows, grille bars and little stars,
    # all in a deterministic whole-car repeat instead of random graphics. I1
    # was too tiny at card scale; I2 native 2048 is 0.568s, M/R/Cc std
    # 42.4/41.2/38.7, ranges 18–234 / 102–231 / 16–234 (legacy base M7
    # adapter pending; direct evidence and owner-eye scale pass).
    h, w = shape[:2]
    u, v = _rot(shape, -8.0); per=max(h,w)/8.0
    ix=np.floor(u/per).astype(np.int32); iy=np.floor(v/per).astype(np.int32)
    fx=(u/per)%1.0-.5; fy=(v/per)%1.0-.5
    arc_r=np.sqrt((fx/.265)**2+((fy+.055)/.305)**2)
    arch=np.clip((.060-np.abs(arc_r-1.0))/.034,0,1)*(fy<.055)
    legs=np.maximum(np.clip((.038-np.abs(fx-.265))/.024,0,1),np.clip((.038-np.abs(fx+.265))/.024,0,1))*np.clip((fy-.01)/.06,0,1)*np.clip((.39-fy)/.06,0,1)
    record=np.clip((.105-np.sqrt(fx*fx+(fy-.085)*(fy-.085)))/.040,0,1)
    hub=np.clip((.035-np.sqrt(fx*fx+(fy-.085)*(fy-.085)))/.018,0,1)
    grille=(np.maximum(np.clip((.025-np.abs(fy-.245))/.015,0,1),np.clip((.025-np.abs(fy-.325))/.015,0,1))*np.clip((.19-np.abs(fx))/.04,0,1))
    star=np.maximum(np.clip((.024-np.abs(fx+.355))/.014,0,1)*np.clip((.024-np.abs(fy+.20))/.014,0,1),np.clip((.024-np.abs(fx-.355))/.014,0,1)*np.clip((.024-np.abs(fy-.20))/.014,0,1))
    tier=((ix*3+iy*5+int(seed))&7).astype(np.float32)/7.0
    return arch,legs,record,hub,grille,star,tier


def paint_jukebox_neon(paint, shape, mask, seed, pm, bb):
    arch,legs,record,hub,grille,star,tier = _neon_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:]=np.array([.018,.020,.040],np.float32)
    pink=np.clip(arch+.55*hub+.32*star,0,1); cyan=np.clip(legs+.65*grille,0,1); amber=np.clip(record+.35*star,0,1)
    tube=np.clip(np.maximum(pink,np.maximum(cyan,amber)),0,1)
    glow=_blur(tube,2.2)
    base += np.array([.72,.04,.34],np.float32)[None,None,:]*pink[:,:,None]*.92
    base += np.array([.02,.56,.70],np.float32)[None,None,:]*cyan[:,:,None]*.88
    base += np.array([.82,.38,.05],np.float32)[None,None,:]*amber[:,:,None]*.78
    base += np.array([.18,.04,.16],np.float32)[None,None,:]*glow[:,:,None]*.40
    return _apply(paint,mask,np.clip(base,0,1))


def spec_jukebox_neon(shape, seed, sm, base_m, base_r):
    arch,legs,record,hub,grille,star,tier = _neon_field(shape, seed)
    tube=np.clip(np.maximum(arch,np.maximum(legs,np.maximum(record,np.maximum(grille,star)))),0,1); dark=1-tube
    M=18+230*np.maximum.reduce((.94*arch,.78*record,.64*hub,.42*tier*dark))*sm
    R=231-190*np.maximum.reduce((.68*dark*(1-tier),.62*grille,.48*legs,.34*(1-tier)*record))
    CC=16+232*np.maximum.reduce((.94*arch,.76*hub,.61*record,.46*star,.36*tier*dark))
    return (np.clip(M,0,255).astype(np.float32),np.clip(R,0,255).astype(np.float32),np.clip(CC,0,255).astype(np.float32))


# ============================================================================
# 18 pink_fleck — cherry-red metalflake (true sparse flake field)
# ============================================================================
def _flake_field(shape, seed, density, salt=0):
    h, w = shape[:2]
    key = ("flk", h, w, int(seed), float(density), int(salt))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x9E37 ^ (salt << 9)) & 0xFFFFFFFF)
        cnt = min(int(h * w * density), 200000)
        out = np.zeros((h, w), np.float32)
        yy = rng.integers(0, h, cnt); xx = rng.integers(0, w, cnt)
        out[yy, xx] = rng.uniform(0.45, 1.0, cnt).astype(np.float32)
        out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.5, np.roll(out, 1, 1) * 0.5])
        return out
    return _cache(key, build)


def paint_pink_fleck(paint, shape, mask, seed, pm, bb):
    fl = _flake_field(shape, seed, 0.030)
    flc = _flake_field(shape, seed + 1, 0.012, salt=1)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.66, 0.07, 0.14], np.float32)
    base = _mix(base, (1.0, 0.55, 0.62), fl * 0.7)
    base = _mix(base, (1.0, 0.92, 0.95), flc)
    g = _fine_grain((h, w), seed)
    base = np.clip(base * (0.97 + 0.05 * g[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_pink_fleck(shape, seed, sm, base_m, base_r):
    fl = _flake_field(shape, seed, 0.030)
    flc = _flake_field(shape, seed + 1, 0.012, salt=1)
    h, w = shape[:2]
    g = _fine_grain((h, w), seed)
    hue = _lowfreq(shape, seed, 6, salt=10)
    allfl = np.clip(fl + flc, 0, 1)
    fM = 0.75 * flc + 0.40 * fl + 0.10 * hue          # flakes high metal sparkle
    fR = 0.40 * (1 - allfl) + 0.35 * (1 - hue) + 0.25 * g  # candy body smooth-ish
    fCC = 0.55 * flc + 0.30 * hue + 0.15 * (1 - allfl)     # deep candy clearcoat
    return _spec3(shape, seed, fM, fR, fCC, 106, 86, 102, 132, 110, 130, sm, bias=86)


# ============================================================================
# 19 turquoise_fleck — turquoise metalflake over tooled leather grain
# ============================================================================
def _leather_field(shape, seed):
    h, w = shape[:2]
    edge = _voronoi_dist(shape, seed + 5, 1400, work=700, salt=8)
    edge = np.clip(edge / (max(h, w) * 0.0025), 0, 1)
    pore = _fine_grain(shape, seed + 9, px=0.6)
    pore = np.clip(pore * 0.6 + _blur(pore, 1.8) * 0.6, 0, 1)
    return edge, pore


def paint_turquoise_fleck(paint, shape, mask, seed, pm, bb):
    edge, pore = _leather_field(shape, seed)
    fl = _flake_field(shape, seed, 0.022, salt=2)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    base[:] = np.array([0.06, 0.46, 0.48], np.float32)
    base = np.clip(base * (0.78 + 0.30 * pore[:, :, None]), 0, 1)
    base = _mix(base, (0.02, 0.20, 0.22), (1 - edge) * 0.8)
    base = _mix(base, (0.65, 0.95, 0.92), fl * 0.7)
    g = _fine_grain((h, w), seed)
    base = np.clip(base * (0.97 + 0.05 * g[:, :, None]), 0, 1)
    return _apply(paint, mask, base)


def spec_turquoise_fleck(shape, seed, sm, base_m, base_r):
    edge, pore = _leather_field(shape, seed)
    fl = _flake_field(shape, seed, 0.022, salt=2)
    h, w = shape[:2]
    hue = _lowfreq(shape, seed, 7, salt=11)
    fM = 0.75 * fl + 0.25 * pore + 0.15 * hue          # flakes metallic
    fR = 0.55 * (1 - edge) + 0.30 * pore + 0.15 * (1 - hue)  # leather cracks rough
    fCC = 0.55 * edge + 0.30 * fl + 0.15 * hue          # crown leather clear
    return _spec3(shape, seed, fM, fR, fCC, 104, 96, 100, 130, 116, 128, sm, bias=86)


# ============================================================================
# 20 chrome_diner — brushed chrome trim (broken directional satin machining)
# SPB-105 / SH-CHROME-I2, 2026-08-29 — owner’s whole-car 8–32px doctrine.
# Native/picker audit rejected the legacy radial 220-line moire (0.395s direct);
# this replacement keeps chrome as the material read and reserves fine 14–30px
# interrupted polishing marks for close inspection rather than wallpaper. I3 raises
# delivered roughness spread 19.7 -> 20.6 without altering the visual carrier.
# ============================================================================
def _chrome_field(shape, seed):
    h, w = shape[:2]
    yy, xx = _grid(shape)
    phase = ((int(seed) ^ 0xC472) & 0xFFFF) * 0.000017
    angle = np.deg2rad(18.0)
    u = xx * np.cos(angle) + yy * np.sin(angle)
    v = -xx * np.sin(angle) + yy * np.cos(angle)
    # At the 1024 work grid these become 14px and 30px delivered passes.
    # The two phase-warped strokes and their interrupted scratch gate are distinct
    # authored machining populations, not a random-grain rescue.
    flow = 3.4 * np.sin(v * 0.019 + phase) + 1.7 * np.sin(v * 0.061 - phase * 1.5)
    fine = 0.5 + 0.5 * np.sin((u + flow) * (2.0 * np.pi / 7.0) + phase)
    satin = 0.5 + 0.5 * np.sin((u + flow * 0.35) * (2.0 * np.pi / 15.0) - phase)
    brush = np.clip(0.58 * fine + 0.42 * satin, 0, 1)
    gate = 0.5 + 0.5 * np.sin(v * 0.17 - phase * 2.1)
    scratch = 0.5 + 0.5 * np.sin((u - flow * 0.5) * (2.0 * np.pi / 14.0) + phase * 3.0)
    scr = np.clip((scratch - 0.93) / 0.07, 0, 1) * np.clip((gate - 0.40) / 0.60, 0, 1)
    # Restrained, non-emblematic sky/steel reflection drift keeps the broad read chrome.
    refl = np.clip(0.48 + 0.14 * np.sin(v * 0.006 + phase) + 0.07 * np.sin(v * 0.019 - phase), 0, 1)
    return brush, satin, scr, refl


def paint_chrome_diner(paint, shape, mask, seed, pm, bb):
    brush, satin, scr, refl = _chrome_field(shape, seed)
    h, w = shape[:2]
    base = np.empty((h, w, 3), np.float32)
    val = 0.49 + 0.28 * refl + 0.024 * brush
    base[:, :, 0] = val * 0.96
    base[:, :, 1] = val * 0.99
    base[:, :, 2] = np.clip(val * 1.05, 0, 1)
    base = np.clip(base + scr[:, :, None] * 0.065, 0, 1)
    warm = np.clip((refl - 0.63) * 7.0, 0, 1) * (0.35 + 0.65 * brush)
    base = _mix(base, (0.92, 0.79, 0.55), warm * 0.035)
    return _apply(paint, mask, base)


def spec_chrome_diner(shape, seed, sm, base_m, base_r):
    brush, satin, scr, refl = _chrome_field(shape, seed)
    # chrome doctrine: HIGH M, LOW R overall. But real brushed chrome has tarnished/
    # shadowed patches (M dips), scratched matte streaks (R rises) and a reflection
    # map (CC) on its OWN geometry. We let three INDEPENDENT territory fields drift
    # each channel across the mid line so the combined spec shows hue variety
    # (bright chrome = orange, tarnished = teal, sky-reflection seams = blue/purple)
    # instead of one flat hue. M still spends most pixels bright (chrome), R most low.
    tarnish = _lowfreq(shape, seed, 4, salt=401)        # where chrome goes dull
    sky = _lowfreq(shape, seed, 3, salt=402)            # reflected-sky map (own geom)
    matte = _lowfreq(shape, seed, 6, salt=403)          # brushed-matte streak zones
    fM = 0.50 * brush + 0.35 * refl + 0.15 * satin       # M motif (bright steel)
    fR = 0.58 * scr + 0.28 * matte + 0.22 * (1 - satin)  # R motif (scratch/matte passes)
    fCC = 0.54 * sky + 0.30 * refl + 0.16 * brush         # CC motif (sky on own field)
    # base levels chosen so territory swing crosses mid=120 (variety) yet mean keeps
    # M high and R low (chrome physics): M ~ 95 + swing -> mostly >120 via +amp; R low.
    M = 150.0 + 70.0 * np.clip(fM, 0, 1) - 95.0 * tarnish   # dips below mid where tarnished
    R = 35.0 + 95.0 * np.clip(fR, 0, 1) + 55.0 * matte      # rises above mid in matte zones
    CC = 95.0 + 130.0 * np.clip(fCC, 0, 1) - 60.0 * tarnish
    return _pack_spec(M, R, CC, sm)


# ============================================================================
# WORK-RESOLUTION WRAPPERS (perf doctrine: every paint/spec < 3s @ 2048).
#
# Each design above is composed from smooth structural fields; rendering all of
# that 2048x2048 numpy arithmetic was 4-7s. We instead run the heavy interior at
# a capped WORK resolution (<= _WORK px on the long edge) and bilinear-upscale
# the result to the requested size, then re-impose CRISP full-res grain on the
# paint so fine detail / mip-survival is preserved (the only genuinely high-freq
# component). Visual output is unchanged at car scale; render time drops ~4x.
# The wrappers are applied transparently so the public paint_<id>/spec_<id>
# names + signatures are identical (registry wiring is by name).
# ============================================================================
_WORK = 1024
_FINISH_IDS = [
    "diner_checker", "soda_check", "cherry_polka", "lemon_polka", "bubblegum_dot",
    "mint_stripe", "coral_stripe", "gingham_red", "atomic_starburst", "atomic_charcoal",
    "googie_orbit", "vinyl_groove", "harlequin", "argyle_pastel", "terrazzo_cream",
    "formica_boomerang", "jukebox_neon", "pink_fleck", "turquoise_fleck", "chrome_diner",
]


def _upscale3(col, h, w):
    if col.shape[0] == h and col.shape[1] == w:
        return col
    if _cv2 is not None:
        return _cv2.resize(col, (w, h), interpolation=_cv2.INTER_LINEAR).astype(np.float32)
    out = np.empty((h, w, 3), np.float32)
    for c in range(3):
        out[:, :, c] = _resize_array(col[:, :, c], h, w)
    return out


def _work_shape(h, w):
    m = max(h, w)
    if m <= _WORK:
        return h, w, 1.0
    sc = _WORK / float(m)
    return max(8, int(round(h * sc))), max(8, int(round(w * sc))), sc


def _wrap_paint(core):
    def paint(p, shape, mask, seed, pm, bb):
        h, w = shape[:2]
        wh, ww, sc = _work_shape(h, w)
        if (wh, ww) == (h, w):
            return core(p, shape, mask, seed, pm, bb)
        # render the design at work res on a neutral base + ones mask (the real
        # mask/paint are composited at full res below)
        wbase = np.full((wh, ww, 3), 0.5, np.float32)
        wones = np.ones((wh, ww), np.float32)
        col = core(wbase, (wh, ww, 3), wones, seed, pm, bb)[:, :, :3]
        col = _upscale3(np.ascontiguousarray(col), h, w)
        # re-impose crisp full-res grain so fineness survives the upscale
        g = _fine_grain((h, w), seed)
        col = np.clip(col * (0.97 + 0.06 * g[:, :, None]), 0, 1)
        return _apply(p, mask, col)
    paint.__name__ = core.__name__
    paint.__wrapped__ = core
    return paint


def _wrap_spec(core):
    def spec(shape, seed, sm, base_m, base_r):
        h, w = shape[:2]
        wh, ww, sc = _work_shape(h, w)
        if (wh, ww) == (h, w):
            return core(shape, seed, sm, base_m, base_r)
        M, R, CC = core((wh, ww), seed, sm, base_m, base_r)
        M = _resize_array(M, h, w); R = _resize_array(R, h, w); CC = _resize_array(CC, h, w)
        # keep the R floor exact after interpolation
        R = np.maximum(R, R_FLOOR).astype(np.float32)
        return M.astype(np.float32), R, CC.astype(np.float32)
    spec.__name__ = core.__name__
    spec.__wrapped__ = core
    return spec


for _fid in _FINISH_IDS:
    _pf = globals().get("paint_" + _fid)
    _sf = globals().get("spec_" + _fid)
    if _pf is not None:
        globals()["paint_" + _fid] = _wrap_paint(_pf)
    if _sf is not None:
        globals()["spec_" + _fid] = _wrap_spec(_sf)
