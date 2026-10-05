"""X LAB // SHIFT WAVE — twenty owner-commissioned light-dance materials.

SPB 2026-08-29, owner directive (verbatim): "EXPAND X LAB from 30 finishes to 50
... PAINSTAKINGLY build out 20 more finishes based on ... HOLOGRAM METAL ...
Not just VARIATIONS ... but the math behind it with other unique shapes and
looks ... making the car shift the way no other painter has ever done in
iRacing. The colors will DANCE and be ALIVE on the car."

MECHANISM (hyperanalysis of x_lab_2026 style 21 + `_local_material_cells` + 12
owner track screenshots): 8-32px cells following the paint geometry; each cell
holds ONE of 4-5 discrete EXTREME M/R/Cc states (chrome / fract-gloss / satin /
brushed / void); one or two SLOW selector fields reassign states in COHERENT
REGIONS (the drifting luminous shapes — never per-cell confetti); crisp chrome
cell shoulders; dark ground with the state colors visibly quilting the PAINT so
color and material dance together.

ITERATION 2 (after the iter-1 eyeball, see X_LAB_SHIFT_PROGRESS.jsonl):
region-DOMINANT state law (zone = digitize(slow selector) picks the population,
cell code only alternates within it — this is exactly hologram's hot-wave
hierarchy); paint brightened with state-keyed cell luminance so the quilt shows
in paint; poster poles pushed off-canvas (field-not-poster doctrine); geometry
rebuilt where the read failed (scales, hex, opal, meteor, bloom, ivy, circuit).

Deterministic arithmetic only (no RNG). Budget: paint+spec <=3s @2048.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock

import cv2
import numpy as np

WORK = 2048
GROUP = "X LAB"
_CACHE: OrderedDict[str, tuple[np.ndarray, np.ndarray]] = OrderedDict()
_LOCK = RLock()


@dataclass(frozen=True)
class Recipe:
    fid: str
    name: str
    swatch: str
    story: str
    ramp: tuple[tuple[float, float, float], ...]      # dark->bright paint ramp
    accents: tuple[tuple[float, float, float], ...]   # per-state paint tints
    lumin: tuple[float, float, float, float]          # per-state cell luminance
    states: tuple[tuple[int, int, int], ...]          # per-state (M,R,CC)
    edge: tuple[int, int, int]                        # cell shoulder (M,R,CC)


# ---------------------------------------------------------------- helpers
def _unit(a):
    lo, hi = float(a.min()), float(a.max())
    return np.clip((a - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def _ridge(phase, width):
    d = np.abs(np.mod(phase + .5, 1.0) - .5)
    return np.exp(-((d / width) ** 2))


def _ramp_map(field, colors):
    c = np.asarray(colors, np.float32)
    p = np.clip(field, 0.0, 1.0) * (len(c) - 1)
    low = np.minimum(np.floor(p).astype(np.int16), len(c) - 2)
    t = (p - low)[..., None]
    return c[low] * (1.0 - t) + c[low + 1] * t


def _coords():
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    return (x / (WORK - 1)) * 2.0 - 1.0, (y / (WORK - 1)) * 2.0 - 1.0


def _cells(u, v, du, dv=None):
    dv = du if dv is None else dv
    cu, cv = (u + 2.0) * du, (v + 2.0) * dv
    gx, gy = np.floor(cu).astype(np.int32), np.floor(cv).astype(np.int32)
    fu, fv = cu - gx, cv - gy
    edge_d = np.minimum(np.minimum(fu, 1.0 - fu), np.minimum(fv, 1.0 - fv))
    return gx, gy, fu, fv, edge_d


def _code(gx, gy, a=17, b=31, c=3, m=16):
    return np.mod(a * gx + b * gy + c * gx * gy, m)


def _zone_state(selector, code, cuts=(-.30, .30)):
    """THE HOLOGRAM LAW: the slow selector picks the population (zone), the
    cell code only alternates two states inside it. Regions stay coherent;
    cells stay individual. zone 0 -> states {0,1}, zone 1 -> {1,2}, zone 2 -> {2,3}.
    """
    zone = np.digitize(selector, cuts).astype(np.int32)
    return zone + np.mod(code, 2)


# ---------------------------------------------------------------- the twenty
# Builders return: body(0..1 paint form), glint(0..1 bright anatomy),
# state(int 0..3, cell-constant), edge(bool shoulder).

def _b_prism_ivy(x, y):
    # Vogel phyllotaxis: florets on the golden spiral, proper index math.
    # Bloom pole OFF-CANVAS (iter-3): the car sees arcing floret currents, not a poster.
    xo, yo = x + 1.55, y - 1.35
    r = np.sqrt(xo * xo + yo * yo) + 1e-6
    th = np.arctan2(yo, xo)
    # ring index from radius; florets per ring grow with r so cells stay ~22px
    ring = np.floor(r * 30.0).astype(np.int32)
    per = 6 + ring * 4
    aa = np.mod(th / (2 * np.pi) + 1.0 + ring.astype(np.float32) * 0.381966, 1.0)  # golden offset per ring
    slot = np.floor(aa * per).astype(np.int32)
    fa = np.mod(aa * per, 1.0) - .5
    fr = np.mod(r * 30.0, 1.0) - .5
    floret = np.exp(-((fa / .33) ** 2 + (fr / .31) ** 2) * 2.4)
    code = _code(ring, slot, 13, 29, 5)
    spiral = np.sin(2.2 * th + 7.5 * r)                       # rotating bloom arm
    state = _zone_state(spiral, code, (-.35, .40))
    body = _unit(.38 + .58 * floret + .10 * np.sin(6 * r + 2 * th))
    glint = np.exp(-((np.abs(fa) - .40) / .06) ** 2) * (.3 + .7 * floret)
    edge = (np.abs(fa) > .42) | (np.abs(fr) > .42)
    return body, glint, state, edge


def _b_shatter_royale(x, y):
    # Voronoi shards at half resolution (cells are constant — lossless upsample),
    # inner fracture grain restores fineness. Budget fix for iter-1's 3.72s.
    H = WORK // 2
    yy, xx = np.mgrid[0:H, 0:H].astype(np.float32)
    xs, ys = (xx / (H - 1)) * 2 - 1, (yy / (H - 1)) * 2 - 1
    d = 13.0
    cu, cv = (xs + 2.0) * d, (ys + 2.0) * d
    gx0, gy0 = np.floor(cu).astype(np.int32), np.floor(cv).astype(np.int32)
    f1 = np.full(xs.shape, 9.9, np.float32)
    f2 = np.full(xs.shape, 9.9, np.float32)
    own = np.zeros(xs.shape, np.int32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            gx, gy = gx0 + ox, gy0 + oy
            jx = (np.mod(gx * 127 + gy * 311, 97) / 96.0) - .5
            jy = (np.mod(gx * 269 + gy * 179, 89) / 88.0) - .5
            dx = gx + .5 + .74 * jx - cu
            dy = gy + .5 + .74 * jy - cv
            dd = dx * dx + dy * dy
            closer = dd < f1
            f2 = np.where(closer, f1, np.minimum(f2, dd))
            own = np.where(closer, np.mod(gx * 23 + gy * 41, 16), own)
            f1 = np.where(closer, dd, f1)
    rim = np.sqrt(f2) - np.sqrt(f1)
    up = lambda a, interp: cv2.resize(a, (WORK, WORK), interpolation=interp)
    rim = up(rim, cv2.INTER_LINEAR)
    own = up(own.astype(np.float32), cv2.INTER_NEAREST).astype(np.int32)
    f1u = up(np.sqrt(f1), cv2.INTER_LINEAR)
    tide = np.sin(2.1 * (x * .707 + y * .707)) + .55 * np.sin(1.2 * (x - y))
    state = _zone_state(tide, own, (-.45, .55))
    grain = _ridge((x * 31 + y * 17) + own.astype(np.float32) * .37, .07)  # per-shard fracture grain
    body = _unit(.52 - .26 * f1u + .18 * tide + .14 * grain)
    glint = np.exp(-(rim / .085) ** 2) + .35 * grain
    edge = rim < .055
    return body, np.clip(glint, 0, 1), state, edge


def _b_moire_reactor(x, y):
    def hexf(u, v, s):
        return (np.cos(s * u) + np.cos(s * (.5 * u + .866 * v)) + np.cos(s * (.5 * u - .866 * v)))
    h1 = hexf(x, y, 58.0)
    h2 = hexf(x, y, 60.3)
    beat = _unit(cv2.GaussianBlur(np.abs(h1 + h2), (0, 0), 26)) * 2.0 - 1.0
    gx, gy, fu, fv, ed = _cells(.866 * x + .5 * y, y, 30.0)
    code = _code(gx, gy, 19, 37, 7)
    state = _zone_state(beat, code, (-.30, .38))
    body = _unit(.40 + .30 * beat + .24 * _unit(h1))
    glint = _ridge(h1, .14) * (.35 + .65 * _unit(beat))
    return body, glint, state, ed < .10


def _b_serpent_scales(x, y):
    # Proper scale read: wider, taller shingles with visible rounded rims.
    rows = 30.0
    v = (y + 2.0) * rows
    gy = np.floor(v).astype(np.int32)
    u = (x + 2.0) * rows * .80 + (np.mod(gy, 2) * .5)
    gx = np.floor(u).astype(np.int32)
    fu, fv = u - gx, v - gy
    dome = np.sqrt(((fu - .5) * 1.5) ** 2 + ((fv - .10) * 1.05) ** 2)
    code = _code(gx, gy, 11, 23, 3)
    slither = np.sin(2.6 * (x + .6 * y) + 1.3 * np.sin(1.6 * y))
    state = _zone_state(slither, code, (-.30, .55))
    body = _unit(.26 + .50 * np.exp(-((dome - .34) / .30) ** 2) + .14 * slither)
    glint = np.exp(-((dome - .62) / .055) ** 2)
    edge = (dome > .60) & (dome < .70)
    return body, glint, state, edge


def _b_stained_circuit(x, y):
    # IC blocks with per-block density personality; power pulse lights blocks
    # along Manhattan distance from two off-sheet pads.
    bgx, bgy, bfu, bfv, bed = _cells(x, y, 7.0)          # macro blocks
    bcode = _code(bgx, bgy, 29, 13, 5)
    gx, gy, fu, fv, ed = _cells(x, y, 28.0)              # micro pads
    code = _code(gx, gy, 7, 19, 11)
    trace_h = _ridge((y + 2.0) * 7.0, .05)
    trace_v = _ridge((x + 2.0) * 7.0, .05)
    inner = np.maximum(_ridge(fu * 1.0, .10), _ridge(fv * 1.0, .10)) * (np.mod(bcode, 3) > 0)
    manhattan = np.minimum(np.abs(x - 1.3) + np.abs(y - .8), np.abs(x + 1.4) + np.abs(y + 1.1))
    pulse = np.sin(3.4 * manhattan)
    state = _zone_state(pulse, code + bcode, (-.25, .45))
    body = _unit(.30 + .18 * pulse + .26 * np.maximum(trace_h, trace_v) + .16 * inner + .10 * (bcode / 15.0))
    glint = np.maximum(trace_h, trace_v) * .9 + .45 * inner
    edge = (ed < .075) | (trace_h > .55) | (trace_v > .55)
    return body, np.clip(glint, 0, 1), state, edge


def _b_riptide_parquet(x, y):
    s = 30.0
    u1, v1 = (x + y) * .707, (y - x) * .707
    gxa, gya, fua, fva, eda = _cells(u1, v1, s, s * .32)
    herring = np.mod(gxa + gya, 2)
    gxb, gyb, fub, fvb, edb = _cells(v1, u1, s, s * .32)
    fu = np.where(herring == 1, fub, fua)
    fv = np.where(herring == 1, fvb, fva)
    ed = np.where(herring == 1, edb, eda)
    gx = np.where(herring == 1, gxb, gxa)
    gy = np.where(herring == 1, gyb, gya)
    code = _code(gx, gy, 7, 19, 3)
    tide = np.sin(1.9 * y + 1.0 * np.sin(2.4 * x)) + .5 * np.sin(1.1 * x)
    state = _zone_state(tide, code + herring, (-.45, .55))
    body = _unit(.34 + .22 * tide + .16 * np.sin(np.pi * fv) + .12 * herring)
    glint = _ridge(fv, .07) * .9
    return body, glint, state, ed < .09


def _b_comet_terrace(x, y):
    # Pole pushed OFF-CANVAS: on the car this is sweeping arc terraces, not a
    # bullseye. Radar arm ignites annular sectors.
    cxp, cyp = -1.55, 1.25
    r = np.sqrt((x - cxp) ** 2 + (y - cyp) ** 2) + 1e-6
    th = np.arctan2(y - cyp, x - cxp)
    ring = np.floor(r * 22.0).astype(np.int32)
    nsect = 26 + np.mod(ring, 5) * 6
    sect = np.floor((th / (2 * np.pi) + .5) * nsect).astype(np.int32)
    code = _code(ring, sect, 23, 7, 5)
    sweep = np.sin(2.6 * th + 1.1 * r)
    state = _zone_state(sweep, code, (-.30, .55))
    fr = np.mod(r * 22.0, 1.0)
    fs = np.mod((th / (2 * np.pi) + .5) * nsect, 1.0)
    body = _unit(.28 + .36 * np.exp(-((fr - .48) / .30) ** 2) + .16 * sweep + .08 * np.sin(np.pi * fs))
    glint = _ridge(r * 22.0, .055)
    edge = (fr < .08) | (fs < .07)
    return body, glint, state, edge


def _b_quasar_quilt(x, y):
    # 5-fold quasicrystal DECENTERED: origin far off-canvas so the aperiodic
    # rhombs tile as a field with no mandala.
    xo, yo = x + 1.9, y - 1.6
    acc = np.zeros_like(x)
    env = np.zeros_like(x)
    for k in range(5):
        a = k * (np.pi * 2 / 5)
        ph = 34.0 * (xo * np.cos(a) + yo * np.sin(a))
        acc += np.cos(ph)
        env += np.cos(ph * .09 + k)
    cellid = np.floor(acc * 1.35).astype(np.int32)
    gx, gy, fu, fv, ed = _cells(xo * .809 + yo * .588, yo * .809 - xo * .588, 24.0)
    code = _code(cellid + gx, gy - cellid, 19, 11, 7)
    state = _zone_state(env * .45, code, (-.40, .50))
    body = _unit(.36 + .22 * np.sin(acc * 1.9) + .20 * env * .30)
    glint = _ridge(acc * .95, .07)
    edge = np.abs(np.mod(acc * 1.35, 1.0) - .5) > .430
    return body, glint, state, edge


def _b_glacier_chord(x, y):
    l1p = (x * .94 + y * .34 + 2.0) * 13.0
    l2p = (x * -.42 + y * .91 + 2.0) * 11.0
    l3p = (x * .55 - y * .83 + 2.0) * 12.0
    l1, l2, l3 = (np.floor(p).astype(np.int32) for p in (l1p, l2p, l3p))
    code = np.mod(l1 * 7 + l2 * 13 + l3 * 29, 16)
    front = np.sin(1.6 * (x * .8 - y * .6)) + .6 * np.sin(1.9 * (y * .9 + x * .3) + 1.1)
    state = _zone_state(front * .7, code, (-.35, .45))
    e1, e2, e3 = _ridge(l1p, .05), _ridge(l2p, .05), _ridge(l3p, .05)
    seam = np.maximum(np.maximum(e1, e2), e3)
    pane = np.mod(code, 5) / 4.0
    body = _unit(.34 + .14 * front + .26 * pane + .14 * np.sin(3.1 * (l1p - l2p) * .27))
    glint = seam
    return body, glint, state, seam > .55


def _b_murmuration(x, y):
    # Brighter flock, larger ovals, alignment ignition.
    cx = np.sin(2.1 * y + .9 * np.sin(1.7 * x))
    cy = np.cos(1.8 * x - .7 * np.sin(2.3 * y))
    u = x * .90 + .34 * cx
    v = y * .90 + .34 * cy
    gx, gy, fu, fv, ed = _cells(u, v, 26.0)
    oval = np.exp(-(((fu - .5) / .46) ** 2 + ((fv - .5) / .30) ** 2) * 2.0)
    code = _code(gx, gy, 13, 37, 5)
    align = _unit(cv2.GaussianBlur(cx * cy, (0, 0), 30)) * 2.0 - 1.0
    state = _zone_state(align, code, (-.25, .45))
    body = _unit(.42 + .58 * oval + .14 * align)
    glint = np.exp(-(((fu - .62) / .12) ** 2 + ((fv - .42) / .10) ** 2) * 1.6)
    return body, glint, state, ed < .08


def _b_ember_weave(x, y):
    s = 27.0
    gx, gy, fu, fv, ed = _cells(x, y, s)
    over = np.mod(gx + gy, 2) == 0
    fv2 = np.where(over, fv, fu)
    slat = np.sin(np.pi * np.clip((fv2 - .08) / .84, 0, 1))
    code = _code(gx, gy, 23, 17, 5)
    front = np.sin(1.5 * (x + y) + .7 * np.sin(2.2 * (x - y)))
    state = _zone_state(front, code + over.astype(np.int32), (-.30, .50))
    body = _unit(.34 + .34 * slat + .14 * front + .08 * over)
    glint = _ridge(fv2 + .5, .075) * .9
    return body, glint, state, ed < .085


def _b_borealis_shards(x, y):
    # Brighter curtains; the light band is the dominant selector.
    sway = .15 * np.sin(2.5 * y + 1.1 * np.sin(1.4 * x))
    gx, gy, fu, fv, ed = _cells(x + sway, y, 38.0, 11.0)
    code = _code(gx, gy, 31, 7, 3)
    band = np.sin(1.8 * x + .9 * np.sin(2.1 * y) + 2.2 * sway)
    state = _zone_state(band, code, (-.35, .50))
    curtain = np.exp(-((fu - .5) / .36) ** 2)
    body = _unit(.30 + .38 * curtain + .20 * band)
    glint = _ridge(fu, .08) * (.4 + .6 * _unit(band))
    return body, glint, state, ed < .085


def _b_medusa_lattice(x, y):
    # Pole off-canvas: the lace sweeps across the sheet in arcs.
    cxp, cyp = 1.5, -1.35
    r = np.sqrt((x - cxp) ** 2 + (y - cyp) ** 2) + 1e-6
    th = np.arctan2(y - cyp, x - cxp)
    rw = r + .05 * np.sin(6 * th) + .04 * np.sin(11 * th + 3 * r)
    gr = np.floor(rw * 24.0).astype(np.int32)
    gt = np.floor((th / (2 * np.pi) + .5) * 64.0).astype(np.int32)
    fr = np.mod(rw * 24.0, 1.0)
    ft = np.mod((th / (2 * np.pi) + .5) * 64.0, 1.0)
    code = _code(gr, gt, 11, 29, 7)
    pulse = np.sin(7.5 * rw)
    state = _zone_state(pulse, code, (-.35, .45))
    cell = np.exp(-((fr - .5) / .32) ** 2) * np.exp(-((ft - .5) / .40) ** 2)
    body = _unit(.38 + .48 * cell + .14 * pulse)
    glint = _ridge(rw * 24.0, .06) + .4 * _ridge((th / (2 * np.pi) + .5) * 64.0, .05)
    edge = (fr < .08) | (ft < .07)
    return body, np.clip(glint, 0, 1), state, edge


def _b_static_bloom(x, y):
    # Finer RD islands with interior grain; the phase tide flips coasts.
    base = (np.sin(64 * x + 13 * np.sin(7 * y)) + np.sin(71 * y + 11 * np.sin(8 * x))
            + np.sin(52 * (x + y)) + np.sin(57 * (x - y)))
    b1 = cv2.GaussianBlur(base, (0, 0), 3)
    b2 = cv2.GaussianBlur(base, (0, 0), 9)
    spots = b1 - b2
    lab_x = np.floor((x + 2.0) * 30.0).astype(np.int32)
    lab_y = np.floor((y + 2.0) * 30.0).astype(np.int32)
    code = np.mod(lab_x * 37 + lab_y * 17, 16)
    phase = np.sin(1.5 * x + 2.1 * y)
    state = _zone_state(phase, code, (-.35, .45))
    grain = _ridge(x * 47 + y * 29 + spots * 2.0, .08)
    body = _unit(.44 + .38 * np.clip(spots * 2.8, -1, 1) + .10 * phase + .12 * grain)
    glint = np.exp(-((spots - .22) / .055) ** 2) + .3 * grain
    edge = np.abs(spots - .20) < .022
    return body, np.clip(glint, 0, 1), state, edge


def _b_chrono_strata(x, y):
    # Stronger faults + band glints; creep marches along the band index.
    fault = np.floor((x + 2.0) * 9.0).astype(np.int32)
    fx = np.mod((x + 2.0) * 9.0, 1.0)
    shift = np.mod(fault * 13, 7) / 7.0
    v = (y + 2.0) * 26.0 + shift
    band = np.floor(v).astype(np.int32)
    fv = np.mod(v, 1.0)
    code = _code(fault, band, 19, 3, 7)
    creep = np.sin(2.4 * y + .9 * x + band.astype(np.float32) * .16)
    state = _zone_state(creep, code, (-.30, .45))
    body = _unit(.32 + .30 * np.sin(np.pi * fv) + .16 * creep + .10 * (np.mod(code, 4) / 3.0))
    glint = _ridge(v, .06) + .55 * _ridge((x + 2.0) * 9.0, .035)
    edge = (fv < .085) | (fx < .05)
    return body, np.clip(glint, 0, 1), state, edge


def _b_hex_reliquary(x, y):
    # PROPER hexes via the 3-cosine hex field: cells are the hex basins, walls
    # are the field's ridges. Twin off-sheet ripples trade the enamel.
    s = 40.0
    hexf = (np.cos(s * x) + np.cos(s * (.5 * x + .866 * y)) + np.cos(s * (.5 * x - .866 * y)))
    basin = _unit(hexf)                                   # 1 at cell centers
    wall = basin < .16                                    # iter-3: thin cloisonné wires, not fat grout
    gx, gy, fu, fv, ed = _cells(x + .011 * np.sin(9 * y), .866 * y, 21.0)
    code = _code(gx, gy, 13, 29, 5)
    rip1 = np.sin(3.6 * np.sqrt((x - 1.6) ** 2 + (y - 1.3) ** 2))
    rip2 = np.sin(3.6 * np.sqrt((x + 1.7) ** 2 + (y + 1.4) ** 2))
    state = _zone_state((rip1 + rip2) * .6, code, (-.45, .55))
    body = _unit(.40 + .46 * basin + .16 * (rip1 + rip2) * .4)
    glint = np.exp(-((basin - .20) / .07) ** 2)
    return body, glint, state, wall


def _b_velvet_meteor(x, y):
    # Bigger, brighter meteors; showers ignite along the flow.
    ang = .52
    u = x * np.cos(ang) + y * np.sin(ang)
    v = -x * np.sin(ang) + y * np.cos(ang)
    u = u + .05 * np.sin(3.0 * v)
    gx, gy, fu, fv, ed = _cells(u, v, 11.0, 30.0)
    code = _code(gx, gy, 7, 31, 5)
    head = np.exp(-(((fu - .62) / .16) ** 2 + ((fv - .5) / .22) ** 2) * 1.8)
    tail = np.exp(-(((fu - .30) / .34) ** 2 + ((fv - .5) / .13) ** 2) * 1.8) * (fu < .62)
    shower = np.sin(2.2 * u + .7 * np.sin(1.8 * v))
    state = _zone_state(shower, code, (-.30, .50))
    dust = _ridge(u * 33 + v * 21, .09)                   # iter-3: velvet micro-sheen ground
    body = _unit(.38 + .68 * np.maximum(head, tail * .78) + .15 * shower + .11 * dust)
    glint = np.exp(-(((fu - .66) / .08) ** 2 + ((fv - .5) / .10) ** 2) * 1.6)
    return body, glint, state, ed < .07


def _b_labyrinth_pulse(x, y):
    gx, gy, fu, fv, ed = _cells(x, y, 24.0)
    flip = np.mod(_code(gx, gy, 5, 11, 13), 2) == 1
    a1 = np.sqrt(fu ** 2 + fv ** 2)
    a2 = np.sqrt((fu - 1) ** 2 + (fv - 1) ** 2)
    b1 = np.sqrt((fu - 1) ** 2 + fv ** 2)
    b2 = np.sqrt(fu ** 2 + (fv - 1) ** 2)
    arc = np.where(flip, np.minimum(np.abs(a1 - .5), np.abs(a2 - .5)),
                   np.minimum(np.abs(b1 - .5), np.abs(b2 - .5)))
    corridor = arc < .15
    code = _code(gx, gy, 29, 17, 3)
    pulse = np.sin(2.0 * x - 1.6 * y + 3.0 * arc)
    state = _zone_state(pulse, code + corridor.astype(np.int32), (-.30, .45))
    body = _unit(.32 + .42 * np.exp(-(arc / .12) ** 2) + .12 * pulse)
    glint = np.exp(-((arc - .095) / .04) ** 2)
    return body, glint, state, arc < .042


def _b_opal_tessellate(x, y):
    # Bigger pentagon read + saturated fire flashes.
    g1x, g1y, f1u, f1v, e1 = _cells(x, y, 12.0)
    g2x, g2y, f2u, f2v, e2 = _cells((x + y) * .707, (y - x) * .707, 12.0)
    pick = np.mod(g1x + g1y + g2x, 2) == 0
    gx = np.where(pick, g1x, g2x + 512)
    gy = np.where(pick, g1y, g2y + 512)
    ed = np.where(pick, e1, e2)
    fu = np.where(pick, f1u, f2u)
    fv = np.where(pick, f1v, f2v)
    code = _code(gx, gy, 23, 41, 7)
    fire = np.sin(1.7 * x + 2.2 * y) + .5 * np.sin(2.9 * (x - y) * .6)
    state = _zone_state(fire, code, (-.55, .65))
    tile = np.sin(np.pi * fu) * np.sin(np.pi * fv)
    body = _unit(.44 + .38 * tile + .18 * fire * .5)
    glint = _ridge(fu, .06) * .8 + _ridge(fv, .06) * .8
    return body, np.clip(glint, 0, 1), state, ed < .075


def _b_singularity_bloom(x, y):
    # Galaxy core pushed off-canvas; arms cross the sheet as luminous currents.
    cxp, cyp = 1.35, 1.15
    r = np.sqrt((x - cxp) ** 2 + (y - cyp) ** 2) + 1e-5
    th = np.arctan2(y - cyp, x - cxp)
    arm = th * 3.0 - np.log(r) * 5.4
    armf = np.mod(arm / (2 * np.pi) * 6.0, 6.0)
    ga = np.floor(armf * 4.0).astype(np.int32)
    gr = np.floor(np.log(r + .10) * 16.0).astype(np.int32)
    fa = np.mod(armf * 4.0, 1.0)
    fr = np.mod(np.log(r + .10) * 16.0, 1.0)
    code = _code(ga, gr, 17, 23, 5)
    turn = np.sin(arm * .5)
    state = _zone_state(turn, code, (-.30, .45))
    cell = np.exp(-((fa - .5) / .32) ** 2) * np.exp(-((fr - .5) / .36) ** 2)
    body = _unit(.28 + .46 * cell + .14 * turn)
    glint = _ridge(arm * .955, .05)
    edge = (fa < .08) | (fr < .08)
    return body, glint, state, edge


_BUILDERS = (
    _b_prism_ivy, _b_shatter_royale, _b_moire_reactor, _b_serpent_scales,
    _b_stained_circuit, _b_riptide_parquet, _b_comet_terrace, _b_quasar_quilt,
    _b_glacier_chord, _b_murmuration, _b_ember_weave, _b_borealis_shards,
    _b_medusa_lattice, _b_static_bloom, _b_chrono_strata, _b_hex_reliquary,
    _b_velvet_meteor, _b_labyrinth_pulse, _b_opal_tessellate, _b_singularity_bloom,
)

# State physics (M, R, CC):
CHROME, FRACT, SATIN, BRUSH, VOID = (246, 14, 246), (210, 40, 26), (24, 168, 52), (198, 92, 178), (12, 214, 232)

RECIPES = (
    Recipe("xlab_prism_ivy", "Prism Ivy", "#59FF9E", "phyllotaxis chrome florets blooming along a rotating spiral of light",
           ((.010, .022, .014), (.05, .22, .12), (.16, .84, .40), (.75, 1.0, .66)),
           ((.55, 1.0, .62), (.10, .30, .16), (1.0, 1.0, 1.0), (.72, .95, .55)),
           (.9, .35, 1.25, .8),
           (FRACT, VOID, CHROME, SATIN), (232, 30, 190)),
    Recipe("xlab_shatter_royale", "Shatter Royale", "#B44BFF", "royal glass shards trading crown-purple fire across chrome fault lines",
           ((.010, .006, .022), (.16, .06, .30), (.58, .14, .90), (.94, .72, 1.0)),
           ((.80, .35, 1.0), (.16, .06, .24), (1.0, 1.0, 1.0), (.58, .32, .80)),
           (1.0, .35, 1.3, .75),
           (FRACT, VOID, CHROME, BRUSH), (238, 26, 196)),
    Recipe("xlab_moire_reactor", "Moiré Reactor", "#2FE8FF", "twin hex lattices beating slow interference zones through a cyan mesh",
           ((.004, .016, .022), (.03, .22, .30), (.08, .76, .90), (.86, 1.0, 1.0)),
           ((.30, .95, 1.0), (.08, .24, .30), (1.0, 1.0, 1.0), (.45, .82, .92)),
           (.95, .35, 1.3, .8),
           (FRACT, VOID, CHROME, SATIN), (230, 28, 200)),
    Recipe("xlab_serpent_scales", "Serpent Scales", "#7CFF4A", "imbricated viper shingles flexing gold-green muscle bands under skin",
           ((.010, .016, .006), (.08, .22, .06), (.46, .88, .12), (.97, 1.0, .58)),
           ((.62, 1.0, .30), (.14, .24, .08), (1.0, .96, .70), (.52, .86, .30)),
           (.95, .35, 1.25, .8),
           (FRACT, VOID, CHROME, BRUSH), (226, 32, 188)),
    Recipe("xlab_stained_circuit", "Stained Circuit", "#3D6BFF", "obsidian IC blocks waking in Manhattan waves along chrome trace corridors",
           ((.006, .010, .024), (.06, .12, .30), (.20, .38, .94), (.94, .86, .50)),
           ((.35, .55, 1.0), (.10, .14, .28), (1.0, 1.0, 1.0), (1.0, .84, .38)),
           (.9, .4, 1.3, 1.0),
           (FRACT, VOID, CHROME, SATIN), (234, 26, 194)),
    Recipe("xlab_riptide_parquet", "Riptide Parquet", "#31E8C8", "herringbone slats flipping in pairs as a teal riptide pours through the weave",
           ((.005, .018, .018), (.04, .24, .22), (.12, .84, .70), (.82, 1.0, .95)),
           ((.30, 1.0, .85), (.08, .28, .24), (1.0, 1.0, 1.0), (.44, .84, .76)),
           (.95, .4, 1.25, .8),
           (FRACT, VOID, CHROME, BRUSH), (228, 30, 192)),
    Recipe("xlab_comet_terrace", "Comet Terrace", "#FF9A3E", "shattered ring terraces igniting sector by sector under a sweeping radar arm",
           ((.014, .008, .003), (.24, .08, .03), (.88, .36, .05), (1.0, .90, .56)),
           ((1.0, .60, .22), (.20, .08, .03), (1.0, 1.0, 1.0), (.90, .50, .20)),
           (1.0, .35, 1.3, .85),
           (FRACT, VOID, CHROME, BRUSH), (236, 28, 190)),
    Recipe("xlab_quasar_quilt", "Quasar Quilt", "#C9A7FF", "aperiodic rhomb quilt where five hidden waves crest violet-gold fire",
           ((.008, .006, .018), (.14, .08, .26), (.54, .30, .88), (1.0, .86, .50)),
           ((.72, .45, 1.0), (.14, .10, .22), (1.0, 1.0, 1.0), (1.0, .84, .42)),
           (.95, .4, 1.25, .95),
           (FRACT, VOID, CHROME, SATIN), (240, 24, 198)),
    Recipe("xlab_glacier_chord", "Glacier Chord", "#9FDFFF", "triangulated ice panes ringing as a pressure front migrates through the chords",
           ((.006, .012, .020), (.08, .18, .28), (.30, .64, .92), (.95, 1.0, 1.0)),
           ((.45, .80, 1.0), (.12, .20, .28), (1.0, 1.0, 1.0), (.62, .80, .94)),
           (.95, .45, 1.3, .85),
           (FRACT, VOID, CHROME, SATIN), (230, 26, 200)),
    Recipe("xlab_murmuration", "Murmuration", "#9AF29A", "a chrome starling flock banking together wherever the field aligns",
           ((.006, .012, .009), (.08, .16, .12), (.34, .70, .44), (.90, 1.0, .82)),
           ((.55, .95, .60), (.12, .20, .15), (1.0, 1.0, 1.0), (.50, .80, .58)),
           (.95, .4, 1.3, .85),
           (FRACT, VOID, CHROME, BRUSH), (228, 30, 190)),
    Recipe("xlab_ember_weave", "Ember Weave", "#FF7A3C", "carbon basketweave whose over-slats catch a creeping flame front first",
           ((.012, .006, .003), (.20, .07, .03), (.80, .30, .06), (1.0, .84, .44)),
           ((1.0, .55, .20), (.18, .08, .04), (1.0, 1.0, 1.0), (.82, .44, .18)),
           (1.0, .4, 1.3, .8),
           (FRACT, VOID, CHROME, BRUSH), (232, 30, 186)),
    Recipe("xlab_borealis_shards", "Borealis Shards", "#5CFFC9", "tall aurora curtain shards passing a horizontal band of living light",
           ((.004, .016, .020), (.03, .24, .26), (.12, .88, .66), (.75, 1.0, 1.0)),
           ((.35, 1.0, .80), (.08, .28, .28), (1.0, 1.0, 1.0), (.56, .86, .96)),
           (.95, .4, 1.3, .85),
           (FRACT, VOID, CHROME, SATIN), (226, 28, 196)),
    Recipe("xlab_medusa_lattice", "Medusa Lattice", "#FF6FB0", "polar jelly lace pulsing bioluminescent heartbeat rings outward",
           ((.010, .005, .014), (.16, .05, .20), (.74, .16, .50), (.96, .72, 1.0)),
           ((1.0, .40, .70), (.18, .06, .15), (1.0, 1.0, 1.0), (.72, .42, .86)),
           (.95, .35, 1.3, .85),
           (FRACT, VOID, CHROME, SATIN), (234, 26, 192)),
    Recipe("xlab_static_bloom", "Static Bloom", "#E86FFF", "reaction blooms flipping coast-to-coast when the phase tide crosses them",
           ((.008, .006, .018), (.14, .07, .24), (.64, .18, .86), (1.0, .76, 1.0)),
           ((.85, .40, 1.0), (.16, .08, .22), (1.0, 1.0, 1.0), (.62, .36, .80)),
           (.95, .4, 1.3, .8),
           (FRACT, VOID, CHROME, BRUSH), (238, 26, 194)),
    Recipe("xlab_chrono_strata", "Chrono Strata", "#C8A05A", "fault-stepped bronze terraces creeping band by band like a geologic clock",
           ((.012, .009, .005), (.16, .11, .05), (.64, .42, .14), (.94, .88, .60)),
           ((.85, .62, .25), (.16, .11, .06), (1.0, 1.0, 1.0), (.58, .72, .50)),
           (.95, .4, 1.25, .85),
           (FRACT, VOID, CHROME, BRUSH), (228, 32, 188)),
    Recipe("xlab_hex_reliquary", "Hex Reliquary", "#4A7BFF", "cloisonné honeycomb trading royal enamel as twin ripples interfere",
           ((.006, .009, .020), (.08, .12, .28), (.24, .40, .94), (1.0, .86, .46)),
           ((.40, .58, 1.0), (.10, .14, .28), (1.0, 1.0, 1.0), (1.0, .82, .38)),
           (.95, .4, 1.3, .95),
           (FRACT, VOID, CHROME, SATIN), (240, 22, 200)),
    Recipe("xlab_velvet_meteor", "Velvet Meteor", "#FFD27A", "meteor teardrops streaking black velvet in synchronized copper showers",
           ((.008, .006, .005), (.15, .10, .08), (.82, .52, .20), (1.0, .92, .58)),
           ((1.0, .72, .30), (.15, .11, .07), (1.0, 1.0, 1.0), (.80, .58, .28)),
           (1.0, .35, 1.3, .8),
           (FRACT, VOID, CHROME, BRUSH), (234, 28, 188)),
    Recipe("xlab_labyrinth_pulse", "Labyrinth Pulse", "#3CD9B0", "a chrome-vein maze whose rooms light as the pulse solves the labyrinth",
           ((.005, .013, .013), (.05, .19, .17), (.14, .72, .58), (.84, 1.0, .92)),
           ((.35, .95, .78), (.08, .24, .20), (1.0, 1.0, 1.0), (.95, .65, .30)),
           (.95, .4, 1.3, .9),
           (FRACT, VOID, CHROME, SATIN), (230, 28, 194)),
    Recipe("xlab_opal_tessellate", "Opal Tessellate", "#F2E8FF", "milk-opal pentagon field flashing prismatic fire cell by cell",
           ((.014, .014, .020), (.24, .21, .30), (.70, .60, .84), (1.0, .95, 1.0)),
           ((1.0, .30, .70), (.20, .25, .48), (1.0, 1.0, 1.0), (.22, .95, .85)),
           (1.0, .55, 1.30, .95),
           (FRACT, VOID, CHROME, SATIN), (242, 22, 202)),
    Recipe("xlab_singularity_bloom", "Singularity Bloom", "#B26BFF", "a turning spiral galaxy whose arm cells ignite outward from the void core",
           ((.005, .003, .012), (.12, .05, .20), (.54, .18, .86), (.96, .82, 1.0)),
           ((.75, .40, 1.0), (.13, .07, .21), (1.0, 1.0, 1.0), (.62, .46, .92)),
           (1.0, .35, 1.3, .85),
           (FRACT, VOID, CHROME, SATIN), (236, 24, 198)),
)
BY_ID = {r.fid: r for r in RECIPES}
_IDX = {r.fid: i for i, r in enumerate(RECIPES)}


def _surface(recipe: Recipe) -> tuple[np.ndarray, np.ndarray]:
    x, y = _coords()
    body, glint, state, edge = _BUILDERS[_IDX[recipe.fid]](x, y)
    body = body.astype(np.float32)
    glint = np.clip(glint, 0.0, 1.0).astype(np.float32)
    state = np.clip(state, 0, len(recipe.states) - 1).astype(np.int32)
    edge = edge.astype(bool)

    # ---- paint: the quilt must SHOW — state-keyed luminance + strong accents ----
    # iter-4: _unit() erases constant floors, so midtone visibility comes from a
    # gamma lift here (0^g stays 0 — the deep hologram blacks survive).
    bodyl = np.power(body, .60, dtype=np.float32)
    ramp = _ramp_map(np.clip(.78 * bodyl + .22 * glint, 0, 1), recipe.ramp)
    black = np.asarray(recipe.ramp[0], np.float32)
    accents = np.asarray(recipe.accents, np.float32)[state]
    lum = np.asarray(recipe.lumin, np.float32)[state]
    paint = black + ramp * ((.32 + .55 * bodyl) * lum)[..., None]
    paint += accents * ((.30 * bodyl + .14) * lum)[..., None] * ramp.max(axis=2, keepdims=True)
    paint += np.asarray((.90, .95, 1.0), np.float32) * (.16 * glint)[..., None]
    paint = np.where(edge[..., None], paint * .50 + np.asarray((.80, .86, .94), np.float32) * .12, paint)
    paint = np.clip(paint, 0.0, 1.0).astype(np.float32)

    # ---- spec: discrete state plates + chrome shoulders + interior flakes ----
    st = np.asarray(recipe.states, np.uint8)[state]
    m, r, c = st[..., 0], st[..., 1], st[..., 2]
    em, er, ec = recipe.edge
    m = np.where(edge, em, m).astype(np.uint8)
    r = np.where(edge, er, r).astype(np.uint8)
    c = np.where(edge, ec, c).astype(np.uint8)
    fx = np.floor((x + 2.0) * 128.0).astype(np.int32)
    fy = np.floor((y + 2.0) * 128.0).astype(np.int32)
    flake = (np.mod(fx * 7 + fy * 13 + fx * fy, 11) == 0) & (state >= 2) & (~edge)
    m = np.where(flake, np.minimum(m.astype(np.int32) + 46, 244), m).astype(np.uint8)
    r = np.where(flake, np.maximum(r.astype(np.int32) - 28, 18), r).astype(np.uint8)
    spec = np.stack((m, r, c), axis=2)
    return paint, spec


def arrays(fid: str) -> tuple[np.ndarray, np.ndarray]:
    if fid not in BY_ID:
        raise KeyError(fid)
    with _LOCK:
        if fid in _CACHE:
            _CACHE.move_to_end(fid)
            return _CACHE[fid]
        paint, spec = _surface(BY_ID[fid])
        paint.setflags(write=False)
        spec.setflags(write=False)
        _CACHE[fid] = (paint, spec)
        while len(_CACHE) > 4:
            _CACHE.popitem(last=False)
        return _CACHE[fid]


def _mask(mask, h: int, w: int) -> np.ndarray:
    value = np.asarray(mask, np.float32)
    if value.ndim == 3:
        value = value[..., 0]
    if value.shape != (h, w):
        value = cv2.resize(value, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(value, 0, 1)


def _pair(fid: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        del seed, bb
        h, w = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[..., :3]
        if src.max(initial=0) > 1.5:
            src = src / 255.0
        if src.shape[:2] != (h, w):
            src = cv2.resize(src, (w, h), interpolation=cv2.INTER_LINEAR)
        authored, _ = arrays(fid)
        if authored.shape[:2] != (h, w):
            authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_CUBIC)
        mix = (_mask(mask, h, w) * float(pm))[..., None]
        return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        del seed, sm
        h, w = int(shape[0]), int(shape[1])
        _, packed = arrays(fid)
        if packed.shape[:2] != (h, w):
            packed = cv2.resize(packed, (w, h), interpolation=cv2.INTER_NEAREST)
        coverage = _mask(mask, h, w)[..., None]
        out = np.empty((h, w, 4), np.uint8)
        out[..., :3] = (packed.astype(np.float32) * coverage).astype(np.uint8)
        out[..., 3] = (coverage[..., 0] * 255).astype(np.uint8)
        return out

    for fn in (paint_fn, spec_fn):
        fn._spb_mono_contract_wrapped = True
    return spec_fn, paint_fn


LIVE_PAIRS = {r.fid: _pair(r.fid) for r in RECIPES}


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    del base_reg, fusion_reg
    mono_reg.update(LIVE_PAIRS)
    return f"x-lab-shift-2026: {len(LIVE_PAIRS)} light-dance materials live"
