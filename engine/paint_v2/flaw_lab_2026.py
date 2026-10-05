"""FLAW LAB — non-destructive testing, and the invisible made visible.

Owner mandate 2026-09-04: "do another all new category of 25 ... OUTSIDE OF THE
BOX. UNIQUE. DIVERSE. INTERESTING. SHOKKER-FIED. Look for things we've not even
attempted."

WHY THIS SHELF, WITH EVIDENCE
-----------------------------
The domain was chosen by measurement, not taste. Scanning all 4010 base finishes
in `paint-booth-0-finish-data.js` for twenty candidate material domains:

    NDT / inspection imaging ......  1 hit   <- and that one is a false positive
    fluid instability .............  3
    erosion / geomorphology .......  4
    leather / hide ................  8
    camouflage science ............  9
    corrosion electrochemistry ....  10
    ...
    ice / frost ................... 159      (an entire ELM weather deck already)
    lattice / foam ................  79      (fm_gyroid, honeycombs, meshes)
    medical / anatomy ............. 123

Two instincts that felt novel — ice and TPMS lattices — were already the most
covered things in the catalog. Inspection imaging was the one real hole, and it
is a big one: dye penetrant, magnetic particle, photoelasticity, interferometry,
ultrasonics, radiography, thermography, acoustic emission, strain gauges and
etch inspection are all missing entirely.

THE ARC
-------
Every finish here is a real technique an engineer uses to SEE A FLAW the naked
eye cannot. That is one story told twenty-five ways, not a colour-by-pattern
grid. It is also motorsport-native: this is what happens to a race part between
sessions, and a livery built out of crack-detection imagery is exactly the kind
of thing a sim racer puts on a car.

WHAT MAKES A FINISH HERE DIFFERENT FROM A COLOURMAP
---------------------------------------------------
The obvious failure mode for this shelf is twenty-five false-colour maps of
twenty-five noise fields. So each finish's STRUCTURE comes from the mechanism of
its own technique — fringes, filings, speckle, crack networks, nodal lines,
porosity, grain flow, indent lattices — and never from the palette. The spec
grammar is likewise unique per finish and stated in each spec docstring.

Feature sizes are held to 10-30px at 2048 because the FINISH LAW's SCALE axis is
a RATIO of car-window energy to coarse energy: a technique that is naturally
large-scale gets its macro term deliberately flattened and its contrast carried
in the fine band. Two WRAP SHOP finishes were cut for exactly this.

ITERATION
---------
Each finish declares a knob SPACE; `scripts/spb_variant_search.py` renders and
scores ten samples of it and writes the winner to `flaw_lab_2026_params.json`,
with the full score table beside it — so "best of ten" is checkable.
"""

from __future__ import annotations

import numpy as np

from engine.paint_v2 import _finish_kit_2026 as K
from engine.paint_v2._variant_params import chooser

OVERRIDE = None          # (finish_id, params) — set by the variant search harness


def _P(fid):
    if OVERRIDE is not None and OVERRIDE[0] == fid:
        return OVERRIDE[1]
    return _CHOSEN[fid]


def _k(P):
    return K.kkey(P)


# ═══════════════════════════════════════════════════════════ FINISHES ══
# (authored per-finish below; each block is one technique)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════ FL · PENETRANT BLEED ══
def _penetrant_bleed_field(shape, seed, P):
    """Fluorescent penetrant inspection, built in the order the process happens.

    A fatigue crack is far too narrow to see. Dye is drawn into it by capillary
    action, the surface is wiped clean, chalk developer is dusted on, and the
    developer BLOTS the dye back out sideways — so what the inspector reads is an
    indication several times wider than the crack that made it. That sideways
    widening is the technique, and it is what this builder computes.

    The whole crack path runs at HALF the render resolution and is upsampled once.
    Measured on this box: K.cells at 2048 costs 3.66s on its own, against a 3s
    budget for paint+spec together; at 1024 it costs 0.44s. Nothing in the crack
    path is finer than the bleed itself (~6px), so half-res carries every feature
    the eye gets, and the box blur that follows the upsample removes the step.
    """
    h, w = shape[:2]

    def build():
        hh, ww = (h + 1) // 2, (w + 1) // 2
        cph = max(3.0, float(P["cell_px"]) * 0.5)

        # 1. THE CRACK NETWORK. Worley walls are the right geometry for fatigue
        #    cracking: branchy, closed, meeting at triple points. K.cells returns
        #    F2-F1 in CELL units, so the scale back to pixels is via cph — 1.05
        #    puts the hairline near 1px, a crack rather than a drawn line.
        _val, edge, ang = K.cells((hh, ww), int(seed) + 17, cph, jitter=0.92)
        wall = edge * np.float32(-1.05 * cph)
        wall += 1.0
        np.clip(wall, 0.0, 1.0, out=wall)

        # 2. How much dye a crack holds varies with how far it opened. `ang` is
        #    K.cells' per-cell random, independent of `val`, so the dye load does
        #    not track anything else the field does.
        hold = ang * np.float32(1.0 / np.pi)
        load = hold * np.float32(0.78)
        load += np.float32(0.22)
        wall *= load

        # 3. BREAK THE NETWORK. Whole Worley walls render as a glowing honeycomb
        #    — measured, that is what the first cut of this finish did, and it is
        #    both wrong for FPI and a collision with the 79 lattice/foam finishes
        #    already in the catalog. A crack runs through some grain boundaries
        #    and ARRESTS at others, so a 9px grain field opens the wall only
        #    where it went through, leaving dashes 10-25px long.
        dash = K.mid((hh, ww), 4.5, int(seed) + 7, octaves=1)
        keep = dash * np.float32(6.0)
        keep -= np.float32(6.0 * float(P["arrest"]))
        np.clip(keep, 0.0, 1.0, out=keep)
        wall *= keep

        # 4. ROUND INDICATIONS. A pore holds dye and bleeds a dot rather than a
        #    line — the second morphology every FPI report distinguishes.
        pore = hold - np.float32(1.0 - float(P["pores"]))
        pore *= np.float32(60.0)
        np.clip(pore, 0.0, 0.46, out=pore)
        wall += pore
        np.clip(wall, 0.0, 1.0, out=wall)

        # 5. Indications cluster at stress risers. Measured: this envelope costs
        #    almost nothing on SCALE (band 0.548 -> 0.546) because it multiplies
        #    a field whose energy is already at the cell period, so it is allowed
        #    real contrast — it is what makes the dye read as found evidence.
        stress = K.mid((hh, ww), 16.0, int(seed) + 23, octaves=2)
        gate = stress * np.float32(2.6)
        gate -= np.float32(2.6 * 0.42)
        np.clip(gate, 0.0, 1.0, out=gate)
        gate *= np.float32(0.70)
        gate += np.float32(0.30)
        wall *= gate

        # 6. CAPILLARY BLEED-OUT. Core + mid + faint wide halo, so the indication
        #    has a gradient edge instead of the plateau one blur gives. The
        #    weights are measured, not chosen: at soft/wide/core = 1.05/1.45/0.15
        #    the band ratio is 0.196 and at 1.40/0.62/0.22 it is 0.250, because
        #    every box blur moves power out of the car window. The bleed is the
        #    mechanism but it must not be the load-bearing structure.
        soft = K.box(wall, 1)
        wide = K.box(soft, max(1, int(round(float(P["bleed_px"]) * 0.5))))
        dye = soft * np.float32(1.40)
        dye += wide * np.float32(0.62)
        dye += wall * np.float32(0.22)
        # lamp gain: exposure is set by the inspector, so the knobs that change
        # the CRACKS cannot also change how bright the booth reads.
        dye *= np.float32(0.140 * float(P["dye"]) / max(float(dye.mean()), 1e-6))
        np.clip(dye, 0.0, 1.0, out=dye)
        dyef = np.repeat(np.repeat(dye, 2, 0), 2, 1)[:h, :w]

        # 7. THE DEVELOPER: sprayed chalk, genuinely uneven at ~12px. Deliberately
        #    soft and low-contrast — a high-passed version measured better on
        #    SCALE and rendered a visible axis-aligned weave, because K.mid is a
        #    bilinear lattice and high-passing it exposes the lattice. Look wins.
        chalk = K.mid((h, w), 12.0, int(seed) + 41, octaves=1)
        return chalk, dyef

    return K.cache(("flpen", h, w, int(seed), _k(P)), build)


def paint_fl_penetrant_bleed(paint, shape, mask, seed, pm, bb):
    """Chalk developer over the painter's colour, bleeding fluorescent dye."""
    P = _P("fl_penetrant_bleed")
    src = K.incoming(paint, shape)
    chalk, dye = _penetrant_bleed_field(shape, seed, P)
    h, w = shape[:2]

    # The dye EMITS. Fixed fluorescent yellow-green (ZL-27A reads ~550nm under
    # UV-A) pulled 30% toward the base's own hue, so a red car glows amber and a
    # blue one cool green and the painter's choice still reads. Rotated on the
    # MEAN colour, not per pixel: the dye is one chemical and the base is flat,
    # and that keeps a hue rotate off the full canvas. Its brightness is then
    # rescaled to the dye's own, because emission belongs to the chemical and not
    # to the paint under it — measured, without that rescale a 0.95 white base
    # drives 4.05% of the canvas past the COVERAGE dead-white line; with it,
    # 0.000% on every base from 0.03 to 0.95.
    mean = src.reshape(-1, 3).mean(0).reshape(1, 1, 3)
    tint = np.clip(K.hue_rotate(mean, 0.55).reshape(3), 0.02, 1.0)
    tint = tint * np.float32(0.60 / max(float(0.2126 * tint[0] + 0.7152 * tint[1]
                                              + 0.0722 * tint[2]), 0.04))
    dye_col = 0.70 * np.array([0.55, 1.00, 0.12], np.float32) + 0.30 * np.clip(tint, 0, 1)
    hot_col = np.array([0.15, 0.17, 0.03], np.float32)
    # FPI is READ in a darkened booth under UV-A, where white chalk goes dim
    # violet-grey and only the dye is bright. That is the honest look and it is
    # also where the contrast lives: the same finish with a daylight-white
    # developer measures sd/mean 0.073 on a white base — under the 0.10
    # visibility floor — and puts 59.7% of the canvas into dead white.
    dev = np.array([0.30, 0.31, 0.40], np.float32)

    ck = float(P["chalk"])
    g = dye if float(pm) == 1.0 else np.clip(dye * float(pm), 0.0, 1.0)
    hot = g * g                                    # saturated cores read paler
    hide = g * np.float32(-0.78)                   # dye film hides the developer
    hide += 1.0
    wdev = chalk * np.float32(1.15)                # powder thickness -> brightness
    wdev += np.float32(0.45)
    wdev *= hide
    wdev *= np.float32(ck)
    keep = hide * np.float32(1.0 - ck)             # painter's colour still showing

    out = np.empty((h, w, 3), np.float32)
    for c in range(3):                             # per channel, so the ground +
        oc = src[:, :, c] * keep                   # dye + hot composite never
        oc += wdev * np.float32(dev[c])            # materialises three HxWx3
        oc += g * np.float32(dye_col[c])           # temporaries (48MB each at
        oc += hot * np.float32(hot_col[c])         # 2048) on top of `out`
        out[:, :, c] = oc
    return K.finish(out, src, mask)


def spec_fl_penetrant_bleed(shape, seed, sm, base_m, base_r):
    """GRAMMAR: two-population, soft boundary — wet dye film vs dry chalk developer.

    Background M20/R150/CC60 is the developer: dielectric, chalk-matte, dull
    clear. The indication is liquid dye standing in and around the crack — the
    same dielectric, but WET, so it flattens toward gloss in R and CC and picks
    up a little specular in M. Both populations and the ramp between them come
    off `dye` and `chalk`, the identical two fields the paint modulated with, in
    the same ratio the paint uses them (measured amp_corr 0.78 at 1024).

    No quantiser here on purpose: the assigned grammar is a SOFT boundary, and a
    ladder would both contradict it and terrace the chalk.

    Measured at the shipped knobs: dry developer M20.4/R149.1/CC59.6 over 84.4%
    of the canvas, halo edge M28/R128/CC52, wet crack core M46/R80/CC28. CC
    bottoms at 22.1, never 16.
    """
    chalk, dye = _penetrant_bleed_field(shape, seed, _P("fl_penetrant_bleed"))
    wet = dye - np.float32(0.26)
    wet *= np.float32(2.8)
    np.clip(wet, 0.0, 1.0, out=wet)                # soft population boundary
    gr = chalk - np.float32(0.5)                   # symmetric, so the DRY
    #                                                population sits ON 20/150/60
    M = wet * np.float32(26.0)
    M += gr * np.float32(11.0 * float(sm))
    M += np.float32(20.0)
    np.clip(M, 0.0, 255.0, out=M)

    R = wet * np.float32(-70.0)
    R += gr * np.float32(26.0)
    R += np.float32(150.0)
    np.clip(R, 15.0, 255.0, out=R)

    CC = wet * np.float32(-32.0)
    CC += gr * np.float32(12.0)
    CC += np.float32(60.0)
    np.clip(CC, 16.0, 255.0, out=CC)
    return M, R, CC


# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════════ NN · MAGNETIC PARTICLE ══
def _magpart(shape, seed, P):
    """Wet-method magnetic particle inspection, built in the order the physics runs.

    1. A crack in a magnetised part IS a pair of opposite poles straddling it —
       that pair is the flux leakage, not a metaphor for it. Riding under them is
       the yoke's own applied field: uniform in magnitude, slowly turning, which
       is what gives the whole panel a comb direction instead of leaving the
       indications as islands on a dead plate.
    2. Field lines are the integral curves of B, so the powder is transported
       ALONG B by line-integral convolution.
    3. Force on a particle goes as grad(B^2): powder migrates INTO the flux
       crowding, so the seeding threshold moves with the LEAKAGE FRACTION.

    Two measured choices the code would not otherwise explain.

    The transport is a directional MAXIMUM, not a directional mean. A dragged
    particle leaves a streak of its own value; averaging along the line instead
    melts neighbouring grains together — measured, the mean-blur cut read as 50px
    amoebas at 1:1 while max-dilation reads as discrete 10-16px filings, at
    identical cost (the same eight gathers).

    And the grain is high-passed against its own local mean before thresholding.
    Without it the noise floor wanders, so a plain threshold carves 30-50px
    connected continents instead of separate filings: measured band 0.29 -> 0.60
    at 1024, and on the 1:1 sheet the difference is smoke versus powder.
    """
    h, w = shape[:2]

    def build():
        # EVERY length here is authored at the 2048 ship canvas and scaled by s.
        # This is deliberate and it is the single thing that decides whether the
        # finish lives. spb_finish_law renders at RES=1024 and its band edges are
        # canvas FRACTIONS, so a field authored in absolute pixels is measured one
        # octave coarser there than it ships: the first cut of this finish scored
        # 0.320 at 2048 and 0.077 at 1024 against a 0.20 floor. Scaling by s makes
        # the two agree (measured 0.597 / 0.600), so the gate's verdict is the
        # truth about the car and the filings are 12px where it counts.
        s = np.float32(h / 2048.0)
        f = max(1, int(round(h / 256.0)))
        gh, gw = -(-h // f), -(-w // f)

        # ── 1. the pole ensemble, solved on a fixed 256 grid ──────────────
        # A 2-D pole field is harmonic: it carries no detail finer than its cell,
        # so solving it at 256 and interpolating up is an approximation only of
        # the arithmetic, for 1/64 of the work. The 4-step loop is a MEMORY
        # chunker over poles, not a per-feature loop — the whole ensemble is one
        # broadcast, and chunking holds the transient under ~40MB.
        rng = np.random.default_rng((int(seed) * 9176 + 41) & 0xFFFFFFFF)
        nc = int(P["cracks"])
        gap = np.float32(26.0) * s          # a crack indication is ~26px on the car
        cy = rng.random(nc, dtype=np.float32) * np.float32(h)
        cx = rng.random(nc, dtype=np.float32) * np.float32(w)
        th = rng.random(nc, dtype=np.float32) * np.float32(np.pi)
        sy = np.sin(th) * (gap * np.float32(0.5))
        sx = np.cos(th) * (gap * np.float32(0.5))
        pyc = np.concatenate([cy + sy, cy - sy])[:, None, None]
        pxc = np.concatenate([cx + sx, cx - sx])[:, None, None]
        qq = np.concatenate([np.ones(nc, np.float32),
                             -np.ones(nc, np.float32)])[:, None, None]
        yy = (np.arange(gh, dtype=np.float32)[:, None] + np.float32(0.5)) * np.float32(f)
        xx = (np.arange(gw, dtype=np.float32)[None, :] + np.float32(0.5)) * np.float32(f)
        soft = (gap * np.float32(0.34)) ** 2        # pole core scales with the defect
        Ly = np.zeros((gh, gw), np.float32)
        Lx = np.zeros((gh, gw), np.float32)
        cs = -(-pyc.shape[0] // 4)
        for st in range(0, pyc.shape[0], cs):
            dy = yy - pyc[st:st + cs]
            dx = xx - pxc[st:st + cs]
            inv = qq[st:st + cs] / (dy * dy + dx * dx + soft)
            Ly += (dy * inv).sum(0)
            Lx += (dx * inv).sum(0)

        # The applied field is set to exactly the leakage at a crack lip (1/soft),
        # so the leakage FRACTION below is 0.5 there by construction and needs no
        # tuned constant. It matters: the first cut used a weak applied field and
        # leakage covered 42% of the panel, which is a macro density gradient, not
        # an indication. At this strength 3.1% of the panel is above 0.5 — compact
        # defects on a clean part, which is what an inspector actually photographs.
        b0 = np.float32(1.0) / soft
        ang = (K.mid((gh, gw), 52.5, seed + 3, octaves=2) - np.float32(0.5)) * np.float32(1.8)
        By_c = Ly + np.sin(ang) * b0
        Bx_c = Lx + np.cos(ang) * b0
        leak = np.sqrt(Ly * Ly + Lx * Lx)
        lk_c = leak / (leak + b0)

        def up(a):
            return K.box(np.repeat(np.repeat(a, f, 0), f, 1)[:h, :w], max(1, f // 2))

        By, Bx, lk = up(By_c), up(Bx_c), up(lk_c)

        # ── 2. line-integral convolution along the field lines ────────────
        # rint() on the offset admits only ~20 directions, and a constant-direction
        # contour is visible as a seam. The dither is a 4px field on the OFFSET
        # only — never on brightness — so neighbouring filings take neighbouring
        # bins and the seam dissolves into the angular scatter real powder has.
        mag = np.sqrt(By * By + Bx * Bx) + np.float32(1e-12)
        step = np.float32(P["step_px"]) * s
        dth = (K.mid(shape, max(2.0, 4.0 * float(s)), seed + 21, octaves=1)
               - np.float32(0.5)) * np.float32(1.5)
        oy = np.rint(By / mag * step + dth).astype(np.int32)
        ox = np.rint(Bx / mag * step - dth).astype(np.int32)
        rr = np.arange(h, dtype=np.int32)[:, None]
        cc = np.arange(w, dtype=np.int32)[None, :]
        ip = np.clip(rr + oy, 0, h - 1) * w + np.clip(cc + ox, 0, w - 1)
        im = np.clip(rr - oy, 0, h - 1) * w + np.clip(cc - ox, 0, w - 1)

        # ── 3. the suspension, and where it piles ─────────────────────────
        # Threshold FIRST: these are the particles that found a grip. Only the
        # leakage fraction moves the threshold, and it is ~0 over the clean part,
        # so the defects buy their contrast without laying a coarse gradient over
        # the whole canvas (SCALE is a ratio — macro contrast costs more than it
        # buys). Then four decaying max-advections carry each particle's OWN value
        # +-4 steps along its field line, so a filing reads as a comet with a dense
        # root. Four short steps rather than two long ones: a coarse max-comb
        # terraces visibly inside each hair.
        gp = max(2.0, float(P["grain_px"]) * float(s))
        raw = K.mid(shape, gp, seed + 7, octaves=2)
        grain = K.norm(raw - K.box(raw, max(1, int(round(gp * 0.9)))))
        thr = np.float32(P["thresh"]) - np.float32(P["crowd"]) * lk
        pile = np.clip((grain - thr) * np.float32(22.0), 0, 1)
        dec = np.float32(0.80)
        for _ in range(4):
            flat = pile.ravel()
            pile = np.maximum(pile, dec * np.maximum(flat[ip], flat[im]))
        return K.box(pile, max(1, int(round(float(s))))).astype(np.float32)

    return K.cache(("magp", h, w, int(seed), _k(P)), build)


def paint_fl_magnetic_particle(paint, shape, mask, seed, pm, bb):
    """Black iron powder standing up along the flux leaking out of every crack."""
    P = _P("fl_magnetic_particle")
    base = K.incoming(paint, shape)
    pile = _magpart(shape, seed, P)
    # The technique's first step is a thin white contrast lacquer — without it the
    # powder is invisible on a dark part. Flat, so it adds not one joule of coarse
    # structure, and it keeps the painter's own hue in the ground between
    # indications. The lift is what makes a near-black base still work: measured
    # band_abs 0.0211 on a pure black base against a 0.010 floor, and the mix tops
    # out at 0.92 luma so a white base can never go dead-white either.
    lac = base * np.float32(0.58) + np.float32(0.34)
    k = np.clip(pile * (float(P["amp"]) * float(pm)), 0, 1)[:, :, None]
    # A heavy pile is velvety dead black; it is the THIN edge of an indication, a
    # few filings deep over wet steel, that throws a highlight. Hence pile*(1-pile)
    # rather than pile — and every term stays a function of the one field, which is
    # what lets the spec below reconstruct it exactly.
    sheen = (pile * (np.float32(1.0) - pile) * np.float32(4.0))[:, :, None]
    iron = np.float32([0.088, 0.096, 0.118])[None, None, :]      # magnetite, cool cast
    out = lac * (np.float32(1.0) - k) + (iron + np.float32(0.15) * sheen) * k
    return K.finish(out, base, mask)


def spec_fl_magnetic_particle(shape, seed, sm, base_m, base_r):
    """GRAMMAR: particle-count ladder. Eight rungs of POWDER COUNT per unit area,
    each rung dealt its own material, because loose ferrous powder is at once the
    most metallic and the most matte thing on the panel: M climbs WITH R instead
    of against it, which no coating on this shelf can do. Rung 0 is the lacquered
    part itself at M110/R90/CC30 and holds 44% of the canvas — the finish's own
    background bucket. Spans chosen so all eight rungs land in DIFFERENT quantised
    material cells against the signature's 42.5-wide buckets: measured 8 distinct
    STORY cells, the smallest still covering 4.3%.
    """
    P = _P("fl_magnetic_particle")
    pile = _magpart(shape, seed, P)          # the SAME cached field the paint used
    cnt = K.ladder(pile, 8, 0.0, 1.0)        # particles per unit area, quantised
    M = np.clip(110.0 + 96.0 * cnt * float(sm), 0, 255)     # iron: the part, then powder
    R = np.clip(90.0 + 146.0 * cnt * float(sm), 15, 255)    # loose powder scatters
    CC = np.clip(30.0 + 188.0 * cnt * float(sm), 16, 255)   # carrier film gone by rung 7
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════ NN · ISOCHROMATIC FRINGE ══
def _iso_fringe(shape, seed, P):
    """Retardation and isoclinic fields of a transparent model under load.

    A birefringent specimen between crossed polarisers shows fringes on the loci
    of constant principal-stress DIFFERENCE. Both stress terms here are real ones
    and they are separate on purpose:

      BENDING  a beam in pure bending has sigma1-sigma2 rising linearly across
               its depth, so its fringes are straight and EVENLY spaced. This is
               what puts a fringe every `pitch` px over the WHOLE canvas. Point
               loads alone go flat a few hundred px out and the far half of the
               panel would carry no car-window energy at all — SCALE is a ratio,
               so a dead half is a failed gate, not a cosmetic problem.
      FLAMANT  a normal point load on a half-plane gives a purely radial stress
               state, sigma1-sigma2 = 2P.cos(theta)/(pi.r), whose loci are
               circles tangent at the load. Written as (d.n)/|d|^2 it is 4 ops
               per load, and it is what curls the straight fringes into the
               closed loops and isotropic points seen under a loading nose.

    `curl` IS THE WHOLE FINISH, AND ITS UNITS ARE THE POINT.
    Fringe spacing is 1/|grad N|, so anything that adds phase changes the LOCAL
    pitch. Bending contributes exactly 1/pitch. Measured on this field, the load
    term's gradient is ~1.5*amp/soft, so the lobes are normalised to unit peak
    and then scaled by soft/(1.5*pitch): `curl` is therefore the ratio of peak
    load-induced gradient to bending gradient, independent of pitch, of canvas
    size and of the seed's own peak.

    The first build of this finish set curl to 0.45 to protect SCALE. It passed
    every gate — SCALE 0.999, FOLLOW +0.92, dead 0.001 — while looking like a
    CRT scanline pattern: dead-straight parallel rules, not one closed fringe on
    the canvas, nothing an engineer would recognise as a polariscope. Only the
    1:1 contact sheet caught it. SCALE is a ratio against a 0.20 floor and that
    build was sitting on 5x the headroom, so the headroom got spent. At
    curl 2.6 with soft = 0.115*canvas the fringes close into real rosettes and
    isotropic points, and SCALE still measures 0.937 (0.784 at the top of the
    knob, 0.970 at the bottom). Spending SCALE on the look is the whole reason
    to measure it rather than fear it.

    Thickness is the same lever one level down. Retardation = stress x thickness
    and N reaches ~150 orders here, so a 12% thickness swing — the physically
    ordinary number — moves the fringe frequency by ~250% and shreds the band.
    Held to +/-1.4% it moves it by ~25%, which is the gentle wander of a real
    cast specimen and nothing more.

    Everything slow is built at 1/4 scale and lifted with repeat + a radius-3
    box. The narrowest of these fields softens over 247px, so none of them has
    content anywhere near the 4px lift step; it turns the 9-load accumulation
    from ~63 full-canvas ops into ~4.
    """
    h, w = shape[:2]

    def build():
        py, pxx = K.px(shape)
        rng = np.random.default_rng((int(seed) * 2654435761 ^ 0x50E1) & 0xFFFFFFFF)

        qh, qw = (h + 3) // 4, (w + 3) // 4
        gy = (np.arange(qh, dtype=np.float32) * 4.0 + 1.5)[:, None]
        gx = (np.arange(qw, dtype=np.float32) * 4.0 + 1.5)[None, :]
        soft = float(min(h, w)) * 0.115 + 12.0          # ~247px at 2048
        rr = np.float32(soft * soft)
        ang = float(rng.random()) * 3.14159265
        ca, sa = float(np.cos(ang)), float(np.sin(ang))

        def lift(a):
            """1/4-scale field -> full canvas. repeat is nearest, so the box
            radius-3 that follows is not cosmetic: without it the 4px blocks
            step the phase and print a faint 4px grid under the fringes."""
            b = np.repeat(np.repeat(np.asarray(a, np.float32), 4, 0), 4, 1)
            return K.box(b[:h, :w], 3)

        # c2/s2 accumulate the principal-stress DIRECTION as a doubled-angle
        # vector, the only correct way to average an axial field. The bending
        # direction seeds them at weight 0.10 rather than 1.0 so that the loads,
        # not the constant term, decide where the trajectories point.
        lobes = np.zeros((qh, qw), np.float32)
        c2 = np.full((qh, qw), np.float32(0.10 * np.cos(2.0 * ang)))
        s2 = np.full((qh, qw), np.float32(0.10 * np.sin(2.0 * ang)))
        # Nine loads on a 3x3 STRATIFIED grid, jittered inside their cell. Nine
        # uniformly random points clump and leave whole quadrants of a 2048
        # canvas with no rosette in them — the difference between a FIELD and a
        # poster with two big motifs on it. Nine iterations of ~7 ops on a
        # 512x512 array is ~4 full-canvas ops, not a per-feature render loop,
        # and there is no np.exp or np.sin on an array anywhere inside it.
        for i in range(9):
            ly = (i // 3 + 0.15 + 0.70 * float(rng.random())) * (h / 3.0)
            lx = (i % 3 + 0.15 + 0.70 * float(rng.random())) * (w / 3.0)
            th = float(rng.random()) * 6.28318530718
            ny, nx = float(np.cos(th)), float(np.sin(th))
            mag = (0.55 + 0.75 * float(rng.random())) * (1.0 if (i & 1) else -1.0)
            dy, dx = (gy - ly).astype(np.float32), (gx - lx).astype(np.float32)
            inv = np.float32(1.0) / (dy * dy + dx * dx + rr)
            sig = (dy * ny + dx * nx) * (np.float32(mag) * inv)   # Flamant radial
            lobes += sig
            wgt = np.abs(sig) * np.float32(soft * 2.0)
            c2 += wgt * ((dx * dx - dy * dy) * inv)
            s2 += wgt * ((np.float32(2.0) * dx * dy) * inv)

        # ISOCLINIC. The plane-polariscope equation is
        #     I = sin^2(2(theta - alpha)) . sin^2(pi.N)
        # and the first factor is a smooth multiplicative envelope on fringe
        # CONTRAST — the broad sweeping bands where the stress trajectories line
        # up with the polariser and the fringes fade out. sin(2theta - 2alpha)
        # falls straight out of the doubled-angle vector, so no atan2 and no
        # sine are needed. It is here for the LOOK and only the look: replacing
        # it with a constant was measured, and FOLLOW only moves +0.955 -> +0.912
        # (M) and +0.812 -> +0.757 (CC), because what actually carries FOLLOW is
        # that the spec reads `fv` itself. Claiming this term for the gate would
        # have been a nice story and a false one.
        a2 = 2.0 * (ang + 0.9)
        cq, sq = np.float32(np.cos(a2)), np.float32(np.sin(a2))
        vis = (s2 * cq - c2 * sq) ** 2 / (c2 * c2 + s2 * s2 + np.float32(1e-9))
        vfl = np.float32(1.0 - float(P["iso"]))         # never let it reach zero
        vis = lift(vfl + (np.float32(1.0) - vfl) * vis)

        pitch = min(30.0, max(10.0, float(P["pitch"])))
        peak = float(np.max(np.abs(lobes))) + 1e-9
        lobes = lift(lobes * np.float32(float(P["curl"]) * soft / (1.5 * pitch * peak)))
        bend = (pxx * np.float32(ca) + py * np.float32(sa)) * np.float32(1.0 / pitch)
        tq = K.norm(K.box(K.mid((qh, qw), 160.0, int(seed) + 11, octaves=2), 24))
        thick = np.float32(0.986) + np.float32(0.028) * lift(tq)
        N = ((bend + lobes) * thick).astype(np.float32)
        # sin^2(pi.N): dark on every integer order — the fringe an engineer counts.
        frin = np.float32(0.5) - np.float32(0.5) * np.cos(np.float32(6.28318530718) * N)
        fv = (np.float32(0.5) + vis * (frin - np.float32(0.5))).astype(np.float32)
        return N, fv, vis

    return K.cache(("fliso", h, w, int(seed), _k(P)), build)


def paint_fl_photoelastic_iso(paint, shape, mask, seed, pm, bb):
    """White-light polariscope: the fringe ORDER read out as spectral colour.

    N is defined at 550nm and fringe order is delta/lambda, so the SAME
    retardation is a lower order in red (550/650 = 0.846) and a higher one in
    blue (550/450 = 1.222). Those two ratios are the whole colour mechanism —
    black at N=0, then straw, red, the magenta tint of passage, blue-green, and
    on up the Michel-Levy sequence. `disp` scales the source bandwidth: low is a
    filtered near-monochromatic lamp, 1.0 is full white light.

    The composite is a transmission model, not a tint. The specimen darkens the
    painter's colour where the fringe extinguishes, and the light that clears
    the analyser is SCREENED over it. Screening is not a stylistic preference:
    the same field composited ADDITIVELY onto a 0.92 base clips 31.9% of its
    pixels and reads dead over 39.8% of the canvas — the fringes burn out into
    flat white. Screened, that base measures dead 0.000 and clips 0.000, and
    every base from 0.05 to 0.92 stays under dead 0.017. `a` is capped at 1.6 so
    transmission (1 - 0.62a) cannot go negative at pm = 2.
    """
    P = _P("fl_photoelastic_iso")
    src = K.incoming(paint, shape)
    N, fv, vis = _iso_fringe(shape, seed, P)
    a = min(1.6, float(P["amp"]) * float(pm))
    d = float(P["disp"])
    tp = np.float32(6.28318530718)
    half = np.float32(0.5)
    ir = half - half * np.cos(tp * np.float32(1.0 - 0.154 * d) * N)
    ib = half - half * np.cos(tp * np.float32(1.0 + 0.222 * d) * N)

    # The isoclinic scales each intensity ABOUT 0.5, never the whole level. Let
    # it scale the level (fv = vis*frin) and its mean becomes a coarse luminance
    # field of its own: measured, that one change drags the dominant period from
    # 22px to 568px. Contrast modulation lands in sidebands and stays in band.
    rv = half + vis * (ir - half)
    bv = half + vis * (ib - half)
    ev = np.float32(0.50 * a)
    inv = np.float32(1.0) - src * (np.float32(1.0) - np.float32(0.62 * a)
                                   * (np.float32(1.0) - fv))[:, :, None]
    inv[:, :, 0] *= np.float32(1.0) - ev * rv
    inv[:, :, 1] *= np.float32(1.0) - ev * fv
    inv[:, :, 2] *= np.float32(1.0) - ev * bv
    return K.finish(np.float32(1.0) - inv, src, mask)


def spec_fl_photoelastic_iso(shape, seed, sm, base_m, base_r):
    """GRAMMAR: fringe-order ladder carried in CC.

    Background 30/40/20 — the clear, glossy, near-dielectric polymer the model
    is cut from. All three channels read the SAME array the paint modulated
    with: `fv`, the visibility-scaled transmitted intensity at the reference
    wavelength, returned from the one shared cache entry rather than rebuilt.

    Both linear channels are kept strictly inside material bucket 0 (the story
    quantiser's first boundary is 42.5, only 2.5 above the assigned R). M is
    centred on 30 and swings +/-5.5; R is driven DOWN from a 41.5 ceiling. That
    R direction is a gate argument, not a material one — any upward drive would
    push the plurality of the canvas into the next bucket and hand this finish
    somebody else's material cell.

    The LADDER is the grammar and it is literal: the fringe order is quantised
    into six flat gloss terraces, and a strip `duty` wide centred on the dark
    fringe (integer N — the fringe an engineer actually counts) carries a second
    six-level terrace that resets every sixth order, so the gloss numbers the
    fringes the way a technician numbers them by hand. Nothing here is smooth
    and nothing is grain: the channel lands on 30-55 flat values from CC 20 to
    44 (mode 20 = the bare polymer, max gloss).

    THE SPAN RATIO OF THE TWO LADDERS IS A GATE, NOT A TASTE.
    An earlier build gave the six-order terrace the big span (0..25) and the
    fringe ladder the small one (0..15). Every term still came from the shared
    array, but the terrace resets on a 6-order period that knows nothing about
    the fringe, so it OWNED this channel's band-limited amplitude envelope and
    FOLLOW measured +0.019 / +0.174 / -0.113 at the three knob corners — the
    classic "one channel off a different field" failure, arrived at without ever
    reading a different field. Inverting the spans (fringe 0..24, terrace 0..12)
    is what fixes it: +0.81 / +0.75 / +0.84.

    `vq` is the third reader of the shared field and it is a LADDER so it adds
    shades, not grain. Physically: where the analyser extinguishes there is no
    fringe left to number, so the whole gloss readout fades with the isoclinic.
    It is worth ~+0.03 of FOLLOW on its own; it is in for the shade count (13
    flat CC values without it, 30-55 with) and because it is what makes this
    channel read `vis` as well as `fv` and N, so all three of the paint's terms
    are represented.
    """
    P = _P("fl_photoelastic_iso")
    N, fv, vis = _iso_fringe(shape, seed, P)
    duty = float(P["duty"])
    band = (np.abs(np.mod(N, np.float32(1.0)) - np.float32(0.5))
            > np.float32(0.5 - 0.5 * duty)).astype(np.float32)
    lvl = K.ladder(np.mod(N, np.float32(6.0)) * np.float32(1.0 / 6.0), 6, 0.0, 12.0)
    vq = K.ladder(vis, 4, 0.30, 1.0)

    M = np.clip(30.0 + 11.0 * (fv - 0.5) * float(sm), 0, 255)
    R = np.clip(41.5 - 13.0 * fv, 15, 255)
    CC = np.clip(20.0 + vq * (K.ladder(fv, 6, 0.0, 24.0) + lvl * band), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════ NN · ISOCLINIC BAND ══
def _isoclinic(shape, seed, P):
    """The ORIENTATION field of a plane-stress tensor, read through crossed polars.

    An Airy stress function is superposed from n_w plane waves; any smooth Airy
    function satisfies in-plane equilibrium identically, which is why real stress
    analysis is done with them. For one wave phi = a*cos(k.r) the exact second
    derivatives (sxx = phi_yy, syy = phi_xx, sxy = -phi_xy) give a tensor that is
    uniaxial along the wave vector, so the deviator pair collapses to
    (sxx-syy, 2sxy) = (cos2psi, sin2psi) * a*k^2*cos(k.r): ONE cosine per load
    component, and the 2-vector (U, V) that comes out has DIRECTION 2*theta.

    Isoclinics are the loci where a principal axis lies along the polariser,
    I = sin^2(2(theta - alpha)). Recording the dark loci at all n standard
    azimuths alpha = m*pi/2n at once -- which is what an isoclinic parameter map
    IS -- is exactly the zero set of sin(2n*theta). Written in U and V that whole
    construction is algebraic, so there is no atan2, no normalisation and no
    per-pixel trig anywhere below the wave loop. For n = 3, measured on the
    canvas rather than derived on paper:
        sin(6th) = V(4U^2 - r2) / r^3   ->   A = V^2 (4U^2-r2)^2 / r2^3
        cos(6th) = U(4U^2 - 3r2) / r^3  ->   sign is U(4U^2-3r2), r^3 > 0
    An earlier cut normalised (c, s) first and ran a Chebyshev step on them; the
    algebraic form is the same field and drops one full-canvas sqrt and two
    full-canvas divides -- 2048^2 paint+spec 0.98 s vs 1.26 s, same pixels.

    The FIRST cut built phi from banded value noise and failed by eye: the noise
    lattice is axis-aligned, so the principal axes snapped to x/y and the bands
    came out a rectilinear maze. Every metric was green in that version (band
    0.48, follow 0.70) -- only a 1:1 crop caught it. Plane waves at irregular
    azimuths are both the honest Airy construction and the fix.
    """
    h, w = shape[:2]

    def build():
        rng = np.random.default_rng((int(seed) * 91711 + 0x15C1) & 0xFFFFFFFF)
        n = int(P["orders"])
        n_w = int(P["loads"])
        # Band spacing measured against band_px at 2048: spacing / lambda is
        # 0.45 / 0.32 / 0.26 for 2 / 3 / 4 azimuth orders. The knob is therefore
        # stated in the SCALE gate's own units (px between bands) and the load
        # wavelength is DERIVED from it, so the variant search cannot wander out
        # of the car window. Measured over the whole SPACE: 13.2 .. 26.2 px.
        lam0 = float(P["band_px"]) / {2: 0.45, 3: 0.32, 4: 0.26}.get(n, 0.32)
        yy = np.arange(h, dtype=np.float32)[:, None]
        xx = np.arange(w, dtype=np.float32)[None, :]
        U = np.zeros((h, w), np.float32)          # sxx - syy
        V = np.zeros((h, w), np.float32)          # 2 * sxy
        C = np.empty((h, w), np.float32)          # reused: one buffer, not n_w
        for j in range(n_w):
            psi = float(np.pi * (j * 0.6180339887 + 0.31 * rng.random()))
            kk = 2.0 * np.pi / (lam0 * (0.70 + 0.95 * float(rng.random())))
            np.add(np.float32(kk * np.cos(psi)) * xx,
                   np.float32(kk * np.sin(psi)) * yy + np.float32(rng.random() * 6.2831853),
                   out=C)
            np.cos(C, out=C)
            a = 0.6 + 0.8 * float(rng.random())
            U += np.float32(a * np.cos(2.0 * psi)) * C
            V += np.float32(a * np.sin(2.0 * psi)) * C
        # Residual stress left in the part: a slow uniform state the loads ride
        # on. It steers WHERE the bands run while adding NO coarse luminance,
        # because everything downstream reads only the DIRECTION of (U, V) and
        # never its magnitude -- which is how a naturally large-scale organiser
        # stays out of the SCALE ratio. Measured coarse energy 0.219 against
        # band 0.561 at the midpoint.
        rz = np.float32(0.175 * n_w)
        U += rz * (K.mid(shape, 520.0, seed + 31, octaves=1) - np.float32(0.5))
        V += rz * (K.mid(shape, 520.0, seed + 32, octaves=1) - np.float32(0.5))

        u2 = U * U
        v2 = V * V
        r2 = u2 + v2                              # |s1 - s2|^2, no sqrt needed
        r2 += np.float32(1e-8)
        if n == 2:                                # alpha every 45 deg
            q = u2 * v2
            d = u2 - v2
            par = (d >= 0).astype(np.float32)     # sign cos(4 theta)
            A = (np.float32(4.0) * q) / (r2 * r2)
        elif n == 4:                              # alpha every 22.5 deg
            q = u2 * v2
            d = u2 - v2
            d *= d
            par = (d >= np.float32(4.0) * q).astype(np.float32)
            r4 = r2 * r2
            A = (np.float32(16.0) * q * d) / (r4 * r4)
        else:                                     # alpha every 30 deg
            t = np.float32(4.0) * u2 - r2
            par = (U * (t - np.float32(2.0) * r2) >= 0).astype(np.float32)
            t *= V
            t *= t
            A = t / (r2 * r2 * r2)
        del u2, v2
        np.clip(A, 0.0, 1.0, out=A)               # float32 can overshoot 1 at A=1
        # The plate's H&D characteristic curve applied to that intensity: a
        # saturating film response, so it is both physical and 3 cheap ops --
        # a fractional np.power on 4.2M floats was the alternative.
        kb = np.float32(P["plate"])
        T = A * np.float32(1.0 + kb)
        A += kb
        T /= A
        del A
        # Isotropic points: r -> 0, s1 = s2, retardation is zero. Every isoclinic
        # converges there and the plate extinguishes DARK (the zero-order
        # fringe), not bright -- an earlier cut had this backwards and drew
        # bright hairlines down the band centres. These are the four-armed
        # pinwheels visible at 1:1; they EMERGE, nothing draws them.
        rho = np.sqrt(r2, out=r2)
        zero = np.float32(1.0) - rho * np.float32(1.0 / (float(rho.mean()) * 0.45 + 1e-9))
        np.clip(zero, 0.0, 1.0, out=zero)
        return T, par, zero

    return K.cache(("isodk", h, w, int(seed), _k(P)), build)


def paint_fl_isoclinic_dark(paint, shape, mask, seed, pm, bb):
    """Plane polariscope in white light: the isoclinic family is ACHROMATIC black.

    That is the whole difference from its isochromatic sister -- these bands
    carry no spectral order, so the finish desaturates toward the painter's own
    grey as it extinguishes instead of tinting.
    """
    P = _P("fl_isoclinic_dark")
    src = K.incoming(paint, shape)
    T, par, zero = _isoclinic(shape, seed, P)
    g = src[:, :, 0] * 0.299 + src[:, :, 1] * 0.587 + src[:, :, 2] * 0.114
    dark = np.float32(1.0) - T                    # computed once, used three times
    # EVERY term below is scaled by pm, so pm=0 returns the painter's paint
    # untouched -- checked, not assumed (max|out-src| = 0.000000 at pm=0; an
    # earlier cut left the zero-order fringe and the desaturation still running).
    ach = np.clip(dark * np.float32(float(P["desat"]) * float(pm)), 0.0, 1.0)
    ext = np.clip(np.float32(1.0) - np.float32(float(pm)) *
                  (np.float32(float(P["amp"])) * dark + np.float32(0.16) * zero), 0.06, 1.0)
    # src + (g - src)*ach, then * ext, folded to premultiplied weights: 12
    # channel-ops instead of 16. Verified identical to the literal two-step form
    # to 5.96e-08, i.e. float32 epsilon.
    w_src = ((np.float32(1.0) - ach) * ext)[:, :, None]
    w_g = (ach * ext * g)[:, :, None]
    # A polariscope is a TRANSMISSION instrument, so its readout ADDS to the
    # specimen rather than only multiplying it. Measured, and the reason this
    # term exists: on a near-black livery a pure multiply leaves band_abs under
    # the 0.010 hard gate. With it the black-base render reads 0.01549, and the
    # base still plainly reads black at 1:1 (looked at it, did not trust it).
    out = src * w_src + w_g + (np.float32(0.055 * float(pm)) * T)[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_isoclinic_dark(shape, seed, sm, base_m, base_r):
    """GRAMMAR: dark-band hard duotone.

    Two flat materials, no ramps, hard-selected off the SAME cached T the paint
    used -- unstressed plate vs extinguished band. The band population splits by
    azimuth parity because that is the label an isoclinic parameter map actually
    carries, and `par` is sign(cos(2n*theta)) out of the same tensor, not an
    independent field. `zero` (the isotropic locus, also from that tensor) adds
    the only continuous term and is held small enough that the dominant cell
    cannot drift out of its bucket even at sm=2 (verified: cells and channel
    ranges identical at sm=1 and sm=2). Measured amp_corr 0.773 .. 0.849.
    """
    P = _P("fl_isoclinic_dark")
    T, par, zero = _isoclinic(shape, seed, P)
    sel = (T < 0.42).astype(np.float32)
    fld = np.float32(1.0) - sel
    z = zero * np.float32(float(sm))
    # FIELD 25/120/130 = this finish's own material cell, measured 75.9% of
    # canvas with median M/R/CC landing exactly on 25/120/130: a dull, low-metal
    # test plate. BAND = dark glossy metal, far from it in all three channels.
    M = np.clip((25.0 + 7.0 * z) * fld + (118.0 + 42.0 * par) * sel, 0, 255)
    R = np.clip((120.0 - 8.0 * z) * fld + (34.0 + 18.0 * par) * sel, 15, 255)
    CC = np.clip(130.0 * fld + (18.0 + 26.0 * par) * sel, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════ NN · MOIRE DEFLECTOMETRY ══
def _moire_deflect(shape, seed, P):
    """Two Ronchi rulings crossed by a few degrees; their BEAT contours surface slope.

    The instrument: a collimated beam is ruled by G1, propagates a lever arm, and
    is re-ruled by G2. A surface slope deflects the ray, so G1's self-image lands
    displaced at the plane of G2. The camera records the PRODUCT of the two
    rulings, whose local average beats at d = pitch / (2 sin(cross/2)). The
    deflection enters as a PHASE SHIFT and never as brightness, so the fringes are
    contours of constant SLOPE — the specimen is invisible except through where
    its fringes go, which is the whole point of the technique.

    THE FRINGE SPACING IS A KNOB, NOT A CONSEQUENCE. `fringe` is the beat d in
    pixels and `cross` is solved from it, because the SCALE gate is a cliff here.
    scale_axis takes the FFT ring between radii 64 and 256 — those bounds are
    FIXED, while a p-pixel feature sits at radius n/p, so the gate's own RES=1024
    render judges an absolute p as if it were 2p. In-band is 4-16px at 1024 and
    8-32px at 2048; only their intersection, 8-16px, is safe at both. Measured:
    an 18px beat scores SCALE 0.694 at 2048 and 0.114 at 1024 — a fail. This
    SPACE spans 10.5-14.0px, i.e. FFT radius 73-98 at 1024 and 146-195 at 2048.

    Beat/pitch is 3.5-5.4 bars per fringe, found by eye. At ~2 bars the product
    degenerates into a plain diamond lattice with no fringe at all; that draft
    passed every number and was cut at 1:1. The ruling itself (2.6-3.0px, with a
    fixed 1.15px edge, so it is a near-triangle rather than a hard bar) is
    deliberately below the window and low-contrast — a real deflectometer does not
    resolve its own ruling, and a triangle carries far weaker harmonics to dilute
    the SCALE denominator than a square would.
    """
    h, w = shape[:2]

    def build():
        py, pxx = K.px(shape)
        pitch = float(P["pitch"])
        # cross angle solved from the wanted fringe spacing: d = pitch/(2 sin(half))
        half = float(np.arcsin(np.clip(pitch / (2.0 * float(P["fringe"])), 0, 0.5)))
        # the bisector is seeded, so no two cars are ruled on the same axis
        ang = ((int(seed) * 2654435761) % 997) / 997.0 * np.pi
        c1, s1 = float(np.cos(ang - half)), float(np.sin(ang - half))
        c2, s2 = float(np.cos(ang + half)), float(np.sin(ang + half))

        # THE SPECIMEN: a seeded saddle (panel form) plus sparse local defects.
        # Value noise is NOT used for the form. _mid bilinearly upsamples a coarse
        # lattice, so its GRADIENT is discontinuous at every cell line, and a
        # directional difference of it printed straight seams right across the
        # fringes at 2048. Two incommensurate lattices plus one box kill them;
        # dropping the box and widening the difference instead brought the seams
        # back as horizontal smears and moved coarse 0.030 -> 0.087.
        hx = ((int(seed) * 2654435761) % 1009) / 1009.0
        hy = ((int(seed) * 40503) % 1013) / 1013.0
        X = (pxx - 0.5 * w) * (2.0 / w)
        Y = (py - 0.5 * h) * (2.0 / h)
        form = (0.6 + hx) * X * X - (0.6 + hy) * Y * Y + (2.0 * hx - 1.0) * X * Y
        nz = ((K.mid((h, w), 197.0, seed + 12, octaves=1) - 0.5)
              + 0.72 * (K.mid((h, w), 119.0, seed + 13, octaves=1) - 0.5))
        # nz*|nz| keeps the peaks and crushes the middle, so most of the panel is
        # gently swept and a few places carry a real defect the fringes fork around.
        surf = K.box(0.55 * form + float(P["dent"]) * 4.4 * nz * np.abs(nz), 18)

        # Only the slope ACROSS the rulings deflects the self-image, so one
        # directional difference along (c1,s1) is the whole gradient needed — 3 ops
        # instead of the 9 a full np.gradient projection would cost.
        oy, ox = int(round(3.0 * s1)), int(round(3.0 * c1))
        dW = np.roll(surf, (-oy, -ox), (0, 1)) - np.roll(surf, (oy, ox), (0, 1))
        swing = float(P["orders"]) * pitch          # `orders` reads in FRINGES at 3 sigma
        dW *= swing / (3.0 * float(dW.std()) + 1e-6)
        # Soft saturation, not np.clip. Every real deflectometer runs out of range
        # past a few fringe orders, and the soft form bounds the phase GRADIENT as
        # well as the value: d(defl)/d(dW) falls to 0.25 exactly where |dW| is
        # largest. With a hard clip the canvas corners aliased into hash — the
        # saddle's gradient grows linearly outward, so the corners always take the
        # steepest phase, and the carrier sits near Nyquist with no room to spare.
        defl = dW / (1.0 + np.abs(dW) * (0.5 / swing))

        inv = 1.0 / pitch
        u1 = (pxx * c1 + py * s1 + defl) * inv      # deflected self-image of G1
        u2 = (pxx * c2 + py * s2) * inv             # G2, fixed to the instrument
        # |frac - 0.5| is the triangle; clipping it against the duty gives a 50%
        # ruling with a ~1.15px edge and no ringing.
        soft = pitch / 1.15
        g1 = np.clip((0.25 - np.abs(u1 - np.floor(u1) - 0.5)) * soft + 0.5, 0, 1)
        g2 = np.clip((0.25 - np.abs(u2 - np.floor(u2) - 0.5)) * soft + 0.5, 0, 1)
        prod = g1 * g2                              # transmitted intensity

        # A box of TWO ruling periods (kernel 2r+1 ~ 2*pitch) attenuates period
        # pitch/n by sinc(2n) = 0 for every integer n, so it nulls the carrier AND
        # all of its harmonics AND the k1+k2 sum term in one pass, leaving the
        # beat at ~0.73. The residual prod-avg IS the carrier, reused free below.
        avg = K.box(prod, max(2, int(round(pitch - 0.5))))
        # Standardised, not K.norm: min/max normalisation let the odd extreme
        # squash the fringe, and a 3-sigma map already reaches 0.03..0.97.
        beat = np.clip(0.5 + (avg - float(avg.mean()))
                       * (0.5 / (1.55 * float(avg.std()) + 1e-6)), 0, 1)
        fld = np.clip(0.10 + 0.80 * beat
                      + float(P["bar_mix"]) * 1.8 * (prod - avg), 0, 1)

        # ACROSS-FRINGE axis for the spec grammar. k_beat = k1 - k2 is exactly
        # proportional to (sin ang, -cos ang), so one roll pair along that normal
        # gives the fringe flank — anisotropic, and still the same field.
        step = max(2, int(round(float(P["fringe"]) / 6.0)))
        ny, nx = int(round(-step * np.cos(ang))), int(round(step * np.sin(ang)))
        flank = np.abs(np.roll(fld, (-ny, -nx), (0, 1)) - np.roll(fld, (ny, nx), (0, 1)))
        flank = np.clip(flank * (0.5 / (float(flank.mean()) + 1e-6)), 0, 1)

        mu, sg = float(fld.mean()), float(fld.std())
        crest = np.clip((fld - (mu + 0.90 * sg)) * (1.0 / (0.55 * sg + 1e-6)), 0, 1)
        return (fld.astype(np.float32), crest.astype(np.float32),
                flank.astype(np.float32))

    return K.cache(("flmoire", h, w, int(seed), _k(P)), build)


def paint_fl_moire_deflect(paint, shape, mask, seed, pm, bb):
    """The deflectogram is PROJECTED onto the painter's colour, so their base reads."""
    P = _P("fl_moire_deflect")
    src = K.incoming(paint, shape)
    f, cr, fl = _moire_deflect(shape, seed, P)
    a = 0.34 * float(P["amp"]) * float(pm)
    # A deflectogram is formed in TRANSMISSION, so part of it is light the paint
    # never had — and light only shows in the headroom the paint leaves. Gating
    # the additive term on `hd` keeps the fringes alive on a near-black livery
    # (dead 0.762 -> 0.479 at base 0.03) without blowing a white one out.
    hd = 1.0 - np.clip(src.max(2), 0, 1)
    out = src * (1.0 - a + 2.0 * a * f)[:, :, None]
    out = out + ((0.13 * cr + 0.14 * a * f) * float(pm) * hd)[:, :, None]
    # A ruled edge disperses, so the fringe carries a +-0.17 rad chromatic swing —
    # not a false-colour palette. This technique images in monochrome, so the
    # painter's hue must survive; checked at 1:1 on red, blue, gold and near-black.
    return K.finish(K.hue_rotate(out, (f - 0.5) * 0.34), src, mask)


def spec_fl_moire_deflect(shape, seed, sm, base_m, base_r):
    """GRAMMAR: beat-phase anisotropy. Every channel is a read of the SAME field the
    paint used, along the axis the crossed rulings define — the beat phase is
    constant ALONG a fringe and sweeps ACROSS it, so metallic steps in quantised
    FRINGE ORDERS across the beat, roughness ramps across it and is then tilted by
    the across-fringe FLANK (the anisotropic member — the one directional quantity
    on this shelf), and clearcoat takes the complement. The crest deals the second
    material. Measured amp_corr 0.87-0.995 over every corner, seed and base tried.

    Background is pinned with literals rather than base_m/base_r because the
    (M,R,CC) bucket is itself a gate: measured 76% of canvas at M 55 / R 70 /
    CC 27, this finish's material cell alone.

    The plate is chrome on glass. Where transmission is LOW you are on the
    deposited chrome bar — metallic, micro-rough, duller clear. Where it is HIGH
    you look through the clear aperture to the paint — glass: dielectric,
    near-mirror, max gloss. Both are monotone in t = 1 - f.
    """
    f, cr, fl = _moire_deflect(shape, seed, _P("fl_moire_deflect"))
    t = 1.0 - f
    g = float(np.clip(sm, 0.35, 1.55))
    M = K.ladder(t, 5, 51.0 - 15.0 * g, 51.0 + 15.0 * g) * (1.0 - cr) + 20.0 * cr
    R = (np.clip(66.0 + 30.0 * (t - 0.5) * g + 16.0 * (fl - 0.5) * g, 15, 255)
         * (1.0 - cr) + 30.0 * cr)
    CC = np.clip(17.0 + 16.0 * t * g, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════ FL · SHEAROGRAPHY ══
def _shearo(shape, seed, P):
    """Laser shearing interferometry — two real optical stages, in order.

    1. OBJECTIVE SPECKLE. A rough surface under coherent light returns a random
       walk of phasors, so the complex amplitude A = ar + i*ai is a BAND-LIMITED
       GAUSSIAN field and the sensor records |A|^2 = ar*ar + ai*ai — negative
       exponential: a dark ground with hot grains. The band limit IS the imaging
       aperture, which is why the quadratures are blurred BEFORE squaring;
       blurring the intensity instead gives mush with none of the statistics.
       The two lattices are deliberately incommensurate (g and 0.77g): measured,
       a single lattice left a faint square grid at exactly `grain`.

    2. CORRELATION FRINGES. Shearography does not measure out-of-plane
       displacement w, it measures w(x+dx) - w(x), so `surf - roll(surf, 16)` IS
       the shearing element, not a stand-in. A disbond bulges under load and the
       sheared difference of a round bulge is the two-lobed BUTTERFLY with a null
       down its middle. Specimen tilt supplies the straight carrier every real
       head shows, so a defect reads as a LOCAL DISTORTION of a uniform field.

    That last point is what keeps SCALE honest: the disbonds are ~150px across
    yet carry ZERO coarse contrast — the fringe amplitude is uniform everywhere
    and the defect only bends phase. Measured on the law's own maths (RES 1024,
    8-32px-at-2048 annulus): paint band 0.788, coarse 0.201.
    """
    h, w = shape[:2]

    def build():
        # ---- 1. the coherent carrier ----------------------------------------
        g = float(P["grain"])
        rad = max(1, int(round(g * 0.30)))
        ar = K.box(K.mid((h, w), g, seed + 21, octaves=1) - np.float32(0.5), rad)
        ai = K.box(K.mid((h, w), g * 0.77, seed + 22, octaves=1) - np.float32(0.5), rad)
        np.multiply(ar, ar, out=ar)
        np.multiply(ai, ai, out=ai)
        ar += ai                              # |A|^2
        del ai
        # Normalising by 2*mean rather than by max keeps the exponential tail —
        # a handful of grains blow out, which is what speckle actually does.
        ar *= np.float32(1.0 / max(float(ar.mean()) * 2.0, 1e-6))
        spk = np.clip(ar, 0.0, 1.0, out=ar)

        # ---- 2. the specimen: a bonded skin with a scatter of disbonds -------
        # Folded coordinates, not a per-defect loop: one warped 210px lattice
        # gives an unbounded field of round C1 domes in ~10 array ops. The first
        # cut built this by box-blurring a coarse noise field and measured 0.31s
        # of a 3s budget for a diamond-faceted bulge; this is rounder and free.
        inv = np.float32(1.0 / 210.0)
        u = K.mid((h, w), 340.0, seed + 31, octaves=1) - np.float32(0.5)
        u *= np.float32(120.0)
        u += np.arange(h, dtype=np.float32)[:, None]
        u *= inv
        v = K.mid((h, w), 340.0, seed + 32, octaves=1) - np.float32(0.5)
        v *= np.float32(120.0)
        v += np.arange(w, dtype=np.float32)[None, :]
        v *= inv
        u -= np.floor(u)
        u -= np.float32(0.5)
        v -= np.floor(v)
        v -= np.float32(0.5)
        np.multiply(u, u, out=u)
        np.multiply(v, v, out=v)
        u += v
        u *= np.float32(1.0 / (0.36 * 0.36))
        np.clip(u, 0.0, 1.0, out=u)
        u -= np.float32(1.0)
        np.multiply(u, u, out=u)              # C1 dome, peak 1.0 at the site
        v = K.mid((h, w), 470.0, seed + 33, octaves=2) - np.float32(P["bond"])
        v *= np.float32(4.0)
        np.clip(v, 0.0, 1.0, out=v)
        u *= v                                # only some sites have let go
        del v

        d = u - np.roll(u, 16, axis=1)        # <- the shearing element
        del u

        # `orders` is normalised against the measured peak of d, so it means what
        # it says (fringe orders at the worst defect) whatever the geometry does,
        # and the local fringe period near a defect cannot alias: the steepest
        # phase gradient at orders=8 is 0.74 rad/px -> a 8.4px local period.
        gain = np.float32(float(P["orders"]) * 6.2832
                          / max(float(d.max()), -float(d.min()), 1e-5))
        ang = 0.22 + 0.62 * (((int(seed) * 2654435761) % 997) / 997.0)
        kk = 6.2832 / float(P["pitch"])
        d *= gain
        d += np.arange(h, dtype=np.float32)[:, None] * np.float32(kk * np.sin(ang))
        d += np.arange(w, dtype=np.float32)[None, :] * np.float32(kk * np.cos(ang))
        np.cos(d, out=d)
        d *= np.float32(-0.46)
        d += np.float32(0.54)                 # 0.08 + 0.92 * (0.5 - 0.5cos ph)

        # Fringe and speckle keep their OWN pedestals. Measured: with one shared
        # pedestal the speckle (sd/mean ~1) buried the fringes and the whole
        # finish read as flat cloth at 3:1.
        sl = np.float32(P["spkl"])
        spk *= (np.float32(1.0) - sl)
        spk += sl
        d *= spk
        return np.clip(d, 0, 1, out=d)

    return K.cache(("flshear", h, w, int(seed), _k(P)), build)


def paint_fl_shearography(paint, shape, mask, seed, pm, bb):
    """The monitor image of a shearography head: fringes carried on laser speckle."""
    P = _P("fl_shearography")
    src = K.incoming(paint, shape)
    vis = _shearo(shape, seed, P)
    drive = np.float32(float(P["drive"]) * (0.55 + 0.45 * float(pm)))
    # Peak-normalised so `drive` buys CONTRAST, never exposure: measured, the raw
    # 0.46 + drive*vis blew 47% of a white base past 0.94 at drive 1.55; this
    # holds it to 15% and leaves band_abs higher (0.135 vs 0.051) either way.
    bn = np.float32(1.18 / (0.46 + float(drive)))
    # Monochromatic illumination: the ground is the painter's own colour returned
    # at ONE wavelength. hue_rotate runs on the MEAN colour — a 1x1x3 array —
    # not the canvas, which is ~15 full-canvas ops saved for the same result on a
    # flat base. The exposure normalisation is the head gaining up, and it has to
    # be a real normalisation: a 0.25 floor there left a near-black base 89% dead.
    c = src.mean(axis=(0, 1))
    c = np.clip(c + (c - float(c.mean())) * 1.8, 0.02, 1.0)
    c = c / max(float(c.max()), 0.02)
    lasr = np.clip(K.hue_rotate(c.reshape(1, 1, 3), 0.42), 0, 1).reshape(3)
    hot = np.clip((vis - np.float32(0.62)) * np.float32(2.9), 0, 1)
    hot *= hot                                # grains that blew out the sensor
    hot *= np.float32(0.40) * drive * bn
    emit = vis * vis                          # returned intensity, ADDITIVE: the
    emit *= np.float32(0.34) * drive * bn     # sensor image is emitted light, and
    emit += hot                               # a multiplicative-only build left a
    body = vis * drive                        # near-black base 89% dead (now 69%).
    body += np.float32(0.46)
    body *= bn
    out = src * body[:, :, None]
    for ch in range(3):                       # 3 channel adds, not one HxWx3 temp
        out[:, :, ch] += float(lasr[ch]) * emit
    return K.finish(out, src, mask)


def spec_fl_shearography(shape, seed, sm, base_m, base_r):
    """GRAMMAR: speckle-modulated smooth ramp — nothing quantised anywhere.

    The correlation image is a continuous field, so the material is a continuous
    ramp off it. `mod` is the paint's own luminance envelope rebuilt term for
    term — same pedestal, same drive, same quadratic emission, same hot term —
    so FOLLOW is true by construction rather than by argument. The peak
    normaliser `bn` cancels exactly under K.norm (it multiplies every term),
    which is why it is absent here. Measured amp_corr 0.998.

    Background (M,R,CC) = 15 / 190 / 90 — a matte dielectric composite skin,
    which is WHY the part speckles at all: a mirror returns no objective speckle.
    Up the ramp the hot grains are facets that caught the beam square, so they go
    slightly metallic, tighter and glossier together. Measured medians on the
    law's own 0.5-grey base: 21.5 / 181.9 / 89.2, dominant cell (0,4,2) at 59%.
    """
    P = _P("fl_shearography")
    vis = _shearo(shape, seed, P)             # cached — the SAME field, bit-exact
    drive = np.float32(P["drive"])
    hot = np.clip((vis - np.float32(0.62)) * np.float32(2.9), 0, 1)
    hot *= hot
    hot *= np.float32(0.40) * drive
    mod = vis * vis
    mod *= np.float32(0.34) * drive
    mod += hot
    mod += vis * drive
    mod += np.float32(0.46)
    mod = K.norm(mod)
    M = np.clip(15.0 + 34.0 * mod * sm, 0, 255)
    R = np.clip(196.0 - 74.0 * mod * sm, 15, 255)
    CC = np.clip(106.0 - 88.0 * mod * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════ NN · HOLOGRAPHIC INTERFEROGRAM ══
# Second lattice: pitch 1.29x, rotated 31 deg. Folding ONE lattice returns its
# exact nearest point, so min() of two folds is an exact Voronoi F1 over their
# UNION for the cost of two folds instead of a 9-neighbour search - and two
# incommensurate lattices never repeat. The first cut used a single fold and
# passed every gate at band 0.68 while the 1:1 sheet was wallpaper: identical
# bullseyes in rows, and the fold's four-fold symmetry printing the same little
# concentric diamond at every cell corner. Warping harder never touched it (a
# warp moves a symmetric pattern, it does not break the symmetry).
_HI_RATIO, _HI_COS, _HI_SIN = 1.29, 0.85749, 0.51459
_HI_DM = 0.40625      # exact period-mean of d*(0.5+0.5d^2) - see the DC note below
_HI_RC = 0.42         # chirp saturates at 0.42*cell_px, so rim_px is a hard FLOOR
_HI_RMAX = 0.7071     # largest fold radius possible (cell corner of lattice 1)


def _holo_interfero(shape, seed, P):
    """Double-exposure holographic interferometry of a bulging skin disbond.

    A hologram of the part at rest is re-exposed with the part under load; the
    two reconstructions interfere and the fringe ORDER counts out-of-plane
    displacement in half-wavelength steps. A pressurised void under the skin
    bulges as a paraboloid, so t ~ r^2 and the fringe SPACING, 1/(dt/dr), goes as
    1/r - it SHRINKS OUTWARD. Every other ring field in this catalog is a uniform
    sin(d*f); the chirp IS the technique.

    GEOMETRY IS AUTHORED AS hub_px -> rim_px, NEVER AS COEFFICIENTS, and the
    chirp SATURATES. A pure paraboloid runs both ends out of the car window at
    once: measured on the un-clamped first cut, 6.9% of the canvas sat coarser
    than 32px at the wide corner of the space and 5.7% finer than 8px at the
    tight corner, and both ends are pure dilution to a RATIO gate. Here
    S = 1/hub_px pins the spacing at each bulge centre, B carries it down to
    1/rim_px at 0.42*cell_px, and past that radius the pitch is HELD - so rim_px
    is a floor, not a limit approached. Measured at 2048 over all ten sampled
    knob sets: spectral peak 15.2-23.0px, 87-95% of paint energy inside the
    8-32px window, 2.5-7.9% coarser than 32px.

    THE VISIBILITY TERMS MULTIPLY THE AC ONLY. Speckle and order decorrelation
    are real (a reconstruction is speckled, and high-order fringes wash out
    between exposures), but `dark` has a period-mean of _HI_DM, so scaling it by
    a slow envelope injects _HI_DM*d(envelope) of pure COARSE DC - the exact
    energy a RATIO gate counts against. Subtracting _HI_DM first makes the
    returned field zero-mean, so the envelope becomes amplitude modulation
    sitting beside the carrier instead of under it: measured pcoarse 0.069 ->
    0.048 on the same knobs. It is also why this finish now brightens as well as
    darkens - dead on a near-black base went 1.000 -> 0.424.

    Returns (sig, ordn): sig is the bipolar fringe signal, + on a constructive
    crest and - in a cancelled core; ordn is the normalised fringe ORDER.
    """
    h, w = shape[:2]

    def build():
        C = float(P["cell_px"])
        # One displacement of the whole plate at roughly the void size. K.warp is
        # octaves=2, so its own second octave supplies the finer wobble that keeps
        # the fringe outlines lumpy rather than drawn - a separate jitter pair
        # cost two more cached noise builds for the same look.
        wy, wx = K.warp(shape, seed + 31, 0.62 * C, 0.85 * C)

        def _fold2(qx, qy, cc):
            """SQUARED distance to the nearest point of a lattice of pitch cc.

            Squared, so the two lattices can be compared and only the winner
            takes the sqrt. Every step is in-place: a 2048^2 float32 temporary
            costs ~28ms of pure allocation on this box, measured against a 4.7ms
            hot multiply, and the whole finish is allocation-bound not FLOP-bound.
            """
            u = qx * np.float32(1.0 / cc)
            u -= np.floor(u)
            u -= np.float32(0.5)
            u *= u
            v = qy * np.float32(1.0 / cc)
            v -= np.floor(v)
            v -= np.float32(0.5)
            v *= v
            u += v
            u *= np.float32(cc * cc)
            return u

        ca, sa = np.float32(_HI_COS), np.float32(_HI_SIN)
        rx = wx * ca
        rx -= wy * sa
        ry = wx * sa
        ry += wy * ca
        r = np.minimum(_fold2(wx, wy, C), _fold2(rx, ry, C * _HI_RATIO))
        del rx, ry
        np.sqrt(r, out=r)

        rc = _HI_RC * C
        S = 1.0 / float(P["hub_px"])
        F = 1.0 / float(P["rim_px"])
        B = (F - S) / (2.0 * rc)
        rq = np.minimum(r, np.float32(rc))
        t = rq * np.float32(B)
        t += np.float32(S)
        t *= rq                                  # S*rq + B*rq^2 : the paraboloid
        r -= rq
        r *= np.float32(F)
        t += r                                   # held at the tightest pitch past rc
        del r, rq
        # Different voids hold different pressure, so they carry different fringe
        # counts. A SMOOTH field, not a per-cell lookup: a per-cell value jumps at
        # the cell wall and draws the lattice back in as a visible grid.
        bmul = K.mid(shape, 1.15 * C, seed + 13, octaves=2) * np.float32(0.28)
        bmul += np.float32(0.86)
        t *= bmul
        del bmul

        # The order an analyst writes on the print, normalised on the largest
        # radius the union can produce.
        nmax = S * rc + B * rc * rc + F * (_HI_RMAX * C - rc)
        ordn = t * np.float32(1.0 / max(nmax, 1e-3))
        np.clip(ordn, 0, 1, out=ordn)

        # Two-beam intensity is cos^2(phi/2), so the dark fringe locus is
        # sin^2(pi*t); the cubic tightens the cores the way a hard-printed
        # negative does. A polynomial and not a gamma because np.power with a
        # float exponent measured 33ms against 5ms for the equivalent multiply.
        t *= np.float32(2.0 * np.pi)
        d = np.cos(t, out=t)
        d *= np.float32(-0.5)
        d += np.float32(0.5)
        dark = d * d
        dark *= np.float32(0.5)
        dark += np.float32(0.5)
        dark *= d
        del d, t

        vis = ordn * np.float32(-0.42)           # high orders decorrelate
        vis += np.float32(1.0)
        spk = K.mid(shape, 12.0, seed + 77, octaves=1) * np.float32(0.22)
        spk += np.float32(0.78)                  # laser speckle: 12px and coherent
        vis *= spk
        del spk

        sig = np.float32(_HI_DM) - dark          # zero-mean BEFORE the envelope
        sig *= vis
        return sig, ordn

    return K.cache(("holoint", h, w, int(seed), _k(P)), build)


def paint_fl_holo_interfero(paint, shape, mask, seed, pm, bb):
    """Bright constructive crests and cancelled dark cores about the painter's own
    tone, packing tighter the further they run from each bulge centre."""
    P = _P("fl_holo_interfero")
    src = K.incoming(paint, shape)
    sig, ordn = _holo_interfero(shape, seed, P)

    g = sig * np.float32(1.30 * float(P["depth"]) * float(pm))
    g += np.float32(1.0)
    np.clip(g, 0.05, 1.85, out=g)

    m01 = sig * np.float32(1.35)
    m01 += np.float32(0.5)
    np.clip(m01, 0, 1, out=m01)
    m01 *= g

    # The reconstruction is monochromatic - one laser line - but these are BASE
    # finishes, so the line is derived FROM the painter's colour instead of
    # imposed on it. K.hue_rotate turns about the grey axis and preserves r+g+b
    # exactly, so neither line carries luminance structure of its own: crests
    # take the reconstructing line, cancelled cores fall back to the undiffracted
    # ground, and a blue car reconstructs blue. Rotating the MEAN colour keeps the
    # colour stage off the 3-channel broadcast path, which measured 1120ms against
    # 190ms for the per-channel form below.
    mc = src.reshape(-1, 3).mean(0).reshape(1, 1, 3)
    T = min(0.80, float(P["tint"]) * float(pm))
    c_hi = K.hue_rotate(mc, 0.62)[0, 0]
    c_lo = K.hue_rotate(mc, -0.85)[0, 0]

    gA = g * np.float32(1.0 - T)
    chans = []
    for c in range(3):
        lo = np.float32(float(c_lo[c]) * T)
        dv = np.float32((float(c_hi[c]) - float(c_lo[c])) * T)
        ch = src[:, :, c] * gA
        ch += g * lo
        ch += m01 * dv
        chans.append(ch)
    return K.finish(np.dstack(chans), src, mask)


def spec_fl_holo_interfero(shape, seed, sm, base_m, base_r):
    """GRAMMAR: ring-order ladder.

    The print is density-sliced - the analyst's isodensity read of a fringe
    negative - so each fringe resolves into flat contour bands with no grain in
    them at all. The second ladder is the ORDER itself: because visibility decays
    with order, how deep a ring is allowed to cut is set by WHICH ring it is.
    Ring one bottoms out on the lowest material, ring eight barely leaves the
    ground. Both ladders quantise the SAME `sig` the paint modulated with, and
    all three channels come off the one scalar `d`, so the spec cannot drift off
    the paint's geometry: measured amp_corr 0.945-0.987 across the whole space,
    both strength knobs and four base colours.

    Only the CUT side is laddered. `sig` is bipolar, so keying the material off it
    directly puts the washed-out high-order plate in the MIDDLE of the ladder
    instead of on the plate's own card, and the background cell fell to 0.20 of
    the canvas at steps=7 - a different finish's identity. Clipping at the crest
    side says what the technique says: the interfringe ground and the washed-out
    region are the SAME bare plate, and only fringe cores cut into it.

    BACKGROUND M/R/CC = 75/35/18, a bleached silver-halide holographic plate:
    residual silver leaves it half metallic, the emulsion is polished glass-flat,
    the cover glass deep clear. Measured, that cell holds 0.47-0.55 of the canvas
    on every one of the ten sampled knob sets - four times the next card - with
    7-8 cards dealt and an effective richness of 4.3-5.3.
    """
    P = _P("fl_holo_interfero")
    sig, ordn = _holo_interfero(shape, seed, P)

    cut = sig * np.float32(-1.242)
    cut += np.float32(0.262)
    np.clip(cut, 0, 1, out=cut)
    d = K.ladder(cut, int(P["steps"]), 0.0, 1.0)
    d *= K.ladder(ordn, 5, 1.0, 0.48)            # ring 1 cuts deep, ring 8 barely
    d *= np.float32(sm)

    M = d * np.float32(-68.0)
    M += np.float32(75.0)
    np.clip(M, 0, 255, out=M)
    R = d * np.float32(158.0)
    R += np.float32(35.0)
    np.clip(R, 15, 255, out=R)
    CC = d * np.float32(104.0)
    CC += np.float32(18.0)
    np.clip(CC, 16, 255, out=CC)
    return M, R, CC


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════ 07 · ULTRASONIC C-SCAN ══
def _cscan_gate(shape, seed, P):
    """The gated echo amplitude of a raster ultrasonic scan, as the instrument draws it.

    A C-scan is not a picture of the part. A transducer is dragged across it under a
    couplant film, one pass at a time, and the gate keeps ONE number per probe
    POSITION — the height of the echo returning from inside. So the image inherits the
    SCAN's geometry, not the part's: one flat cell per trigger, stepped at the pass
    pitch in y and the encoder step in x, serrated wherever the sweep reversed, and
    blank wherever the couplant broke and nothing came back at all.

    Every raster term (pass index, rule profile, parity, per-pass gain) is a COLUMN
    of shape (h,1), so the cos() below runs over 2048 elements rather than 4.2M — the
    dominant structure of this finish is nearly free to build.
    """
    h, w = shape[:2]

    def build():
        pitch = float(P["pitch"])
        rows = np.arange(h, dtype=np.float32)[:, None] * np.float32(1.0 / pitch)
        line = np.floor(rows)                       # which pass this row belongs to
        frac = rows - line                          # where inside the pass it sits
        rng = np.random.default_rng((int(seed) * 2654435761 + 0x5CA9) & 0xFFFFFFFF)
        gl = rng.random(int(h / pitch) + 3, dtype=np.float32)
        gain_l = gl[line.astype(np.int32)]          # this pass's coupling / gain
        # The plotted raster rule, as a RAISED COSINE. Measured: a hard-edged rule of
        # 0.30 duty put its 2nd harmonic at pitch/2 = 7.5px, i.e. BELOW the 8px window,
        # where it is pure dilution — the spec's spectral peak landed at 7.5px. A raised
        # cosine is a single spectral line exactly at the pass pitch and nothing else,
        # which is why this finish's peak sits at 10-16px on every SPACE sample.
        ink = 0.5 + 0.5 * np.cos(frac * np.float32(2.0 * np.pi))
        par = np.mod(line, 2.0) * 2.0 - 1.0         # bidirectional sweep parity
        # What the probe is looking at: through-thickness attenuation. Disbonds and
        # porosity are hand-sized on a car panel (~150px) and can NEVER be allowed to
        # touch luminance directly — see the AM trick in `tone`. The 9px octave exists
        # only to be point-sampled once per probe cell, which turns it into honest
        # cell-to-cell grain scatter rather than any visible 9px texture.
        A = K.norm(0.55 * K.mid(shape, 150.0, seed + 11, octaves=3)
                   + 0.27 * K.mid(shape, 39.0, seed + 12, octaves=2)
                   + 0.18 * K.mid(shape, 9.0, seed + 13, octaves=1))
        # ONE sample per probe position, held across the whole cell. This gather IS the
        # instrument: it is what makes a smooth attenuation field come out as a lattice
        # of flat square cells at the scan pitch instead of a smooth blob.
        yi = np.clip((line + 0.5) * pitch, 0, h - 1).astype(np.int32)
        xc = np.arange(w, dtype=np.float32)[None, :] * np.float32(1.0 / pitch)
        xs = np.clip((np.floor(xc) + 0.5) * pitch, 3.0, w - 4.0).astype(np.int32)
        # Encoder lag on the reverse sweep offsets alternate passes by 3px, so every
        # palette boundary comes out serrated at exactly the pass pitch. It is the
        # artefact that dates a real C-scan.
        xi = xs + (par * 3.0).astype(np.int32)
        att = A[yi, xi]
        g = float(P["gain"])
        # Coupling gain rides the amplitude BEFORE the gate quantises it, so the palette
        # walks a step or two between neighbouring passes — the line banding every
        # operator knows on sight.
        echo = np.clip(1.62 * (att - 0.5) + 0.5 + g * 0.24 * (gain_l - 0.5), 0, 1)
        disp = K.ladder(echo, int(P["steps"]), 0.0, 1.0)     # the display's palette
        # Coupling loss shows up first where the echo was already weak: a starved pass
        # goes blank for the run where it crosses a low-return region.
        drop = ((gain_l < 0.075) & (att < 0.44)).astype(np.float32)
        # THE WHOLE LUMINANCE STORY, and it is deliberately built out of the raster.
        # The plotter modulates LINE WEIGHT per palette level, so the 150px amplitude
        # map reaches luminance only as an AMPLITUDE MODULATION of the pass-pitch
        # carrier — energy at f_c +/- f_m, still inside the car window. Measured: the
        # first cut drove luminance off the map directly and scored paint_band 0.077
        # with its spectral peak at 683px; carrying the same information as AM of the
        # rule takes it to 0.50-0.72 with the peak at the pitch.
        tone = ((1.0 - float(P["rule"]) * (0.30 + 0.70 * disp) * ink)
                * (1.0 + 0.055 * g * par)           # forward vs reverse sweep gain
                * (0.90 + 0.20 * gain_l)            # per-pass coupling drift
                * (1.0 - 0.55 * drop))              # dropout runs
        return disp.astype(np.float32), tone.astype(np.float32)

    return K.cache(("c_scan", h, w, int(seed), _k(P)), build)


def paint_fl_c_scan(paint, shape, mask, seed, pm, bb):
    """A gated amplitude map painted by a raster scan, in the instrument's palette."""
    P = _P("fl_c_scan")
    src = K.incoming(paint, shape)
    disp, tone = _cscan_gate(shape, seed, P)
    p = float(pm)
    wgt = np.float32([0.2126, 0.7152, 0.0722])
    # FALSE COLOUR THAT IS EXACTLY ISOLUMINANT. K.hue_rotate turns about the RGB grey
    # axis, which is NOT luma-neutral under Rec709 — measured, rotating a livery red
    # dumped the entire 150px amplitude map into luminance (81% of the paint's energy
    # coarse). Subtracting the rotated luma leaves a pure zero-luma chroma vector, so
    # amplitude lives in HUE, the raster keeps the contrast, and the painter's own
    # colour stays the axis the palette turns about.
    rot = K.hue_rotate(src, (disp - 0.45) * (float(P["span"]) * p))
    l0 = src @ wgt
    chroma = rot - (rot @ wgt)[:, :, None]
    # A rotation cannot colour an achromatic livery — a white car came back as bare
    # raster lines. So the palette also EMITS the NDT cold/hot opponent, along the
    # (1, -0.1963, -1) direction whose Rec709 luma is exactly zero, small enough that a
    # coloured base still owns the hue.
    e = (float(P["emit"]) * p) * (disp - 0.45)
    # The readout is a printed film, and it carries its own density — without it a
    # near-black livery multiplies to nothing and band_abs fails. Dark bases get the
    # most print, light bases the least, so a white car never clips its raster flat.
    lift = 0.14 * (1.0 - 0.55 * l0)
    lum = (l0 * (1.0 - 0.16 * p) + p * lift) * (1.0 + p * (tone - 1.0))
    out = lum[:, :, None] + chroma * (1.0 + p * (0.95 * disp - 0.42))[:, :, None]
    out[:, :, 0] += e
    out[:, :, 1] -= 0.1963 * e
    out[:, :, 2] -= e
    return K.finish(out, src, mask)


def spec_fl_c_scan(shape, seed, sm, base_m, base_r):
    """GRAMMAR: hard colormap ladder. The readout owns a fixed palette, so every channel
    is cut into discrete material steps off the one displayed field — 11 / 14 / 9 levels
    plus a 5-level substrate ladder, no two sharing a step boundary, and no grain.

    Material story: a dry couplant/print film over the panel (M10 R200 CC200 — the
    dominant cell at 0.70 of canvas), slicker where the ink went down dense on a strong
    return, and as-rolled mill-finish panel showing through the unprinted rules and the
    dropout runs (M to 184, ~3% of canvas — the second material).
    """
    P = _P("fl_c_scan")
    disp, tone = _cscan_gate(shape, seed, P)
    # FOLLOW by construction: because every colour operation above is exactly
    # zero-luma, the paint's luminance IS `tone`, so cutting all three channels from it
    # is not an analogy, it is the same field. Measured amp_corr 0.93-0.99.
    # The affine is PARAMETRIC, not K.norm: `rule` sets both where tone sits and how far
    # it spreads (fitted, median = 1 - 0.34*rule to within 0.006 over the whole SPACE),
    # and K.norm would have let the dropout runs drag the canvas off the assigned
    # background. With it, the spec median is 12/197/200 on all ten SPACE samples.
    rule = float(P["rule"])
    mod = np.clip(0.5 + (tone - (1.0 - 0.34 * rule)) / (0.16 + 1.30 * rule), 0, 1)
    bare = np.clip((0.155 - mod) * 7.0, 0, 1)          # unprinted substrate
    M = np.clip(10.0 + (K.ladder(1.0 - mod, 11, -22.0, 26.0)
                        + K.ladder(bare, 5, 0.0, 148.0)) * sm, 0, 255)
    R = np.clip(200.0 + K.ladder(mod, 14, 44.0, -44.0) * sm, 15, 255)
    CC = np.clip(200.0 + K.ladder(mod, 9, 34.0, -34.0) * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════ A-SCAN GATE ══
_ASCAN_TRIG = 0.62      # gate trigger: the fraction of full screen height an echo
                        # must reach before the instrument calls it a hit
_ASCAN_PHASE = 2.05     # radians the trace phosphor sits off the painter's colour
_ASCAN_GA = 0.30        # flaw gate, centred at this fraction of the sweep
_ASCAN_GB = 0.66        # backwall gate — the two brackets the operator sets
_ASCAN_GW = 0.055       # gate half-width, as a fraction of the sweep


def _ascan(shape, seed, P):
    """Ultrasonic pulse-echo, stacked trace by trace — how a B-scan is built.

    X is TIME OF FLIGHT and Y is trace number, so one row band IS one A-scan.
    The probe fires, the wall reverberates, and echoes come back at equal
    intervals dying away until the next pulse re-triggers the sweep. Wall
    thickness and probe lift-off both shift the whole train in time, so every
    trace arrives a little early or late — that jitter is what turns a 1-D
    waveform into an image. The gate cursors do NOT move with it: they sit on
    the instrument's clock, which is exactly why a shifted echo falls out of
    gate.

    Costed deliberately: everything that is a function of TIME ONLY (the sweep
    sawtooth, the transmit pulse, both gates and their rules) is built as a
    (1,w) ROW and everything that is a function of TRACE only as an (h,1)
    COLUMN, so only six fields are ever materialised full-canvas. Building
    those as HxW first measured 4.67x the shelf's reference finish at 2048;
    broadcasting them is 2.45x, for identical pixels (max |diff| 9e-8).
    """
    h, w = shape[:2]

    def build():
        pitch = float(P["pitch"])
        sweep = float(P["sweep"])
        th = max(2, int(round(float(P["trace"]))))
        # ---- (1,w): the instrument's own clock. NEVER jittered — the traces
        # wander, the time base does not, and that contrast is the whole idea.
        xr = np.arange(w, dtype=np.float32)[None, :]
        s = xr - sweep * np.floor(xr * (1.0 / sweep))      # time since the pulse
        nm = s * (1.0 / pitch)                             # echoes elapsed
        dp = np.minimum(s, sweep - s)
        pulse = 1.6 - dp * (1.6 / (0.018 * sweep))         # transmit pulse, off-scale
        gh = _ASCAN_GW * sweep
        de = np.minimum(np.abs(s - _ASCAN_GA * sweep), np.abs(s - _ASCAN_GB * sweep))
        gwin = (de < gh).astype(np.float32)                # the two gate windows
        grule = (np.abs(de - gh) < 2.2).astype(np.float32)  # their four cursor rules
        # ---- (h,1): per-TRACE arrival time, CONSTANT down a trace and stepping
        # at the next one. A streaked 2-D noise was tried first and read as smooth
        # pinstripes on the 1:1 sheet; stepping per trace is what makes the field
        # read as stacked waveforms, and it is nearly free.
        rows = (np.arange(h, dtype=np.int32) // th) * th
        drift = K.mid((h, 4), 3.4 * th, seed + 17, octaves=1)[:, :1]   # wall thickness
        lift = K.mid((h, 4), 1.15 * th, seed + 23, octaves=1)[:, :1]   # probe lift-off
        jc = K.norm(0.64 * drift[rows] + 0.36 * lift[rows])
        # ---- the genuinely 2-D work
        t = xr + (jc - 0.5) * (2.0 * float(P["wobble"]) * pitch)
        # Disbond domains: sparse patches where the sound never reaches the far wall.
        fl = np.clip((K.mid((h, w), 110.0, seed + 29, octaves=1) - 0.58) * 4.5, 0, 1)
        # Fold the time axis — ONE pass draws every reverberation in the train.
        ad = np.abs(t - pitch * np.round(t * (1.0 / pitch)))
        hw = pitch * float(P["pfrac"])
        inv = 1.0 / (hw * hw)
        q = ad * ad * inv
        # Ricker wavelet (1-3.8u²)e^(-1.9u²) — the standard pulse-echo model, and
        # the reason the trough is 0.446 of the peak instead of the ~0.05 a squared
        # cosine gave: measured, and the dark ringing bands either side of each echo
        # were invisible on the sheet until this replaced it.
        rf = (1.0 - 3.8 * q) * np.exp(np.float32(-1.9) * q)
        # A disbond reflects from half the wall depth, so a SECOND train appears
        # interleaved between the wall echoes over the bad patches. Only its
        # amplitude is gated by `fl`; re-scaling the pitch instead was tried and
        # tore the echo phase at the domain edges — GRIT 0.010 -> 0.214, measured.
        d2 = ad - 0.5 * pitch
        q2 = d2 * d2 * inv
        rf += ((1.0 - 3.8 * q2) * np.exp(np.float32(-1.9) * q2)) * fl
        # Die-away, normalised so the last echo of a train is 26% of the first at
        # ANY sweep length; a disbond shadows the backwall, so the train dies
        # faster there. `an` is (1,w) — the whole envelope costs three HxW ops.
        an = (2.80 * pitch / sweep) * nm
        rf /= (1.0 + an * (1.0 + 1.6 * fl))
        # Couplant: transmission is best with the probe square to the surface and
        # falls off with tilt EITHER way, which bands the traces in Y.
        rf *= (1.0 - 1.10 * np.abs(jc - 0.5))
        rf = np.maximum(rf, pulse)
        # SOFT screen saturation, never a hard clip. Clipping at |1| with gain 1.5
        # flattened every echo to the same white and DELETED the die-away — the one
        # thing an A-scan exists to show. u/(1+|u|) is monotone, so a decayed echo
        # always draws dimmer than a fresh one at any gain.
        u = rf * float(P["gain"])
        mod = 0.5 + 0.5 * (u / (1.0 + np.abs(u)))
        return mod.astype(np.float32, copy=False), gwin, grule

    return K.cache(("ascan", h, w, int(seed), _k(P)), build)


def paint_fl_a_scan_gate(paint, shape, mask, seed, pm, bb):
    """The flaw detector's screen: a couplant-wet part written over with its own
    echo train and the box's gate graphics."""
    P = _P("fl_a_scan_gate")
    src = K.incoming(paint, shape)
    mod, gwin, grule = _ascan(shape, seed, P)
    sig = (mod - 0.5) * 2.0                                   # the signed RF trace
    pos = np.maximum(sig, 0.0)
    hit = np.clip((mod - _ASCAN_TRIG) * (1.0 / (1.0 - _ASCAN_TRIG)), 0, 1)
    # Three colours, all of them the painter's: the part, the phosphor the trace is
    # written in (their colour rotated about the grey axis), and the near-white ink
    # the box draws its own graphics in. Their base choice drives all three.
    avg = src[::8, ::8].reshape(-1, 3).mean(0).astype(np.float32)[None, None, :]
    trace = np.clip(K.hue_rotate(avg, _ASCAN_PHASE)[0, 0] * 1.25 + 0.12, 0, 1)
    ink = np.clip(trace * 0.30 + 0.72, 0, 1)
    # Alphas. EVERY modulation scales with pm, so pm=0 is the instrument switched
    # off and hands the part back flat (band 0.000, measured). The gate panel
    # SHADES the trace behind it, which is what makes a window read as an overlay
    # rather than as more stripes, and lets a trip inside one stand out.
    ga = np.clip((0.32 * pos + 0.80 * hit) * ((1.0 - 0.55 * gwin) * float(pm)), 0, 1)
    gb = np.clip(((0.95 * gwin) * hit + (0.16 * gwin + 0.62 * grule)) * float(pm), 0, 1)
    # The part reads dark and wet, the ringing troughs darker still. The couplant
    # film has its own low sheen, which is what keeps a near-black base off the
    # floor: without it a 0.03 base measured 78% DEAD, and 55% with it.
    dim = np.maximum(0.52 + (0.42 * float(pm)) * np.minimum(sig, 0.0), 0.05)
    film = 0.026 + (0.034 * float(pm)) * pos
    inv_gb = 1.0 - gb
    keep = (1.0 - ga) * inv_gb
    out = src * (dim * keep)[:, :, None]
    out += trace[None, None, :] * (ga * inv_gb)[:, :, None]
    out += ink[None, None, :] * gb[:, :, None]
    out += (film * keep)[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_a_scan_gate(shape, seed, sm, base_m, base_r):
    """GRAMMAR: echo-spike duotone. The trigger splits the surface into exactly two
    materials — couplant-wet part below it, hard mirror metal above — each carrying
    its own rungs of a nine-step ladder, with the box's printed graphics stamped
    over both as a third, dead-flat gloss ink.

    All three channels are driven off ONE field, `drv`, rebuilt from the same
    `mod`/`gwin`/`grule` the paint used. Splitting them across different fields is
    what failed FOLLOW before: an earlier mapping drew the instrument ink BRIGHT in
    spec luma while the echoes drew dark, the two cancelled where they overlap, and
    amp_corr fell to 0.300 against a 0.35 floor. One driver, one sign: 0.77-0.84
    across all ten variants of the space.
    """
    P = _P("fl_a_scan_gate")
    mod, gwin, grule = _ascan(shape, seed, P)
    sh = K.ladder(mod, 9, 0.0, 1.0)                 # nine clean rungs, zero grain
    spike = (mod > _ASCAN_TRIG).astype(np.float32)
    lit = spike * sh                                # echo amplitude, in instrument steps
    ink = np.maximum(spike * gwin, grule)           # the rules, and the trips inside a gate
    drv = 16.0 * sh + 118.0 * lit + 34.0 * spike    # the one driver
    M = np.clip(45.0 + sm * (drv - 37.0 * ink), 0, 255)
    R = np.clip(160.0 - sm * (0.62 * drv + 120.0 * ink + 8.0 * gwin), 15, 255)
    CC = np.clip(40.0 - sm * (0.10 * drv + 9.0 * sh + 24.0 * ink), 16, 255)
    return (M.astype(np.float32, copy=False), R.astype(np.float32, copy=False),
            CC.astype(np.float32, copy=False))


# ════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════ NN · WELD RADIOGRAPH ══
_FILM_BASE = np.float32([0.052, 0.062, 0.098])     # blue-grey polyester film base
_LIGHTBOX = np.float32([1.000, 0.972, 0.918])      # warm viewing-box fluorescent


def _radiograph(shape, seed, P):
    """X-ray film of a multipass weld overlay: metal path length -> film density.

    The physics in the order the beam meets it. (1) DEPOSITED THICKNESS — parallel
    hardfacing passes, each a parabolic crown carrying the crescent "stacked dime"
    ripples that are the frozen trailing edge of the puddle. (2) POROSITY — trapped
    gas that REMOVES a chord of metal. (3) THE FILM — Beer-Lambert attenuation read
    by a log-response emulsion, which makes density LINEAR in path length, so the
    whole conversion is a subtraction and never needs an exp().
    """
    h, w = shape[:2]

    def build():
        # The coupon is never square to the tube. 0.14 rad off-axis costs two ops
        # and is the single biggest reason this stops reading as wallpaper: axis-
        # aligned passes plus axis-aligned ripples looked like corrugated hose on
        # the 1:1 sheet even while every gate was green.
        ry, rx = K.px(shape)
        ca, sa = np.float32(0.99022), np.float32(0.13954)      # cos/sin(0.14 rad)
        py = ry * ca - rx * sa
        pxx = rx * ca + ry * sa

        bead = float(P["bead_px"])
        # ONE noise field spent twice: the welder's wander across the plate AND the
        # broad density drift of the film itself (uneven development / beam heel).
        # A second build cost 0.26s of a 3s budget and bought nothing the eye reads.
        wn = K.mid(shape, 190.0, seed + 41, octaves=2)
        t = (pxx + (wn - 0.5) * 13.0) * np.float32(1.0 / bead)
        row = np.floor(t)
        fb = t - row - 0.5
        fb2 = fb * fb
        crown = 1.0 - 4.0 * fb2                    # parabolic crown, 0 at both toes

        rg = np.random.default_rng((int(seed) * 6151 + 907) & 0xFFFFFFFF)
        # 1.40x because the rotation pushes the bead index past w/bead in the far
        # corner; sized at w/bead the clip flattened ~6 passes onto one phase and
        # printed a visible identical-ripple wedge.
        rows = int(w * 1.40 / max(bead, 6.0)) + 6
        phase = rg.random(rows, dtype=np.float32)
        ph = phase[np.clip(row.astype(np.int32), 0, rows - 1)]

        # ONE gather carries three per-pass variations, COUPLED the way the
        # welder's hand couples them: a slower pass deposits a taller bead AND lays
        # its ripples closer together. The 2.30*bead shear is what curves a rung
        # into a CRESCENT — at 0.62 the arcs were straight rungs and the field read
        # as corduroy; at 2.30 a rung sweeps ~1.4 ripple periods across half a pass
        # and reads as stacked dimes.
        s = ((py + 2.30 * bead * fb2)
             * ((0.86 + 0.30 * ph) * np.float32(1.0 / float(P["rip_px"]))) + ph * 7.0)
        # smoothstep, not the parabola 1-4fr^2. A periodic parabola has a slope
        # CUSP at its trough; that cusp drew a hard dark outline round every arc and
        # the 1:1 sheet came back reading as fish scales. Smoothstep is C1 at both
        # ends, so the ripple is a density undulation instead of an embossed relief.
        fr = np.abs(s - np.floor(s) - 0.5) * 2.0
        rip0 = 0.5 - fr * fr * (3.0 - 2.0 * fr)    # ZERO-MEAN carrier, see below
        fine = rip0 * ((0.55 + 0.45 * crown) * (0.62 + 0.52 * ph))
        seam = np.clip((np.abs(fb) - 0.40) * 9.0, 0, 1)   # dark line where beads butt
        # WHY rip0 is zero-meaned: leaving its DC in meant every per-pass amplitude
        # change also changed that pass's BRIGHTNESS, which is a bead-pitch (30-44px)
        # term. Measured, that put 84.8% of the field's power above 32px and SCALE
        # read 0.147 against a 0.20 floor. Zero-meaning turns the same modulation
        # into pure AM — sidebands beside the ripple, inside the car window — and
        # SCALE went 0.147 -> 0.498. The crown survives only as a low-contrast
        # organiser; it is the ripple and the pores that carry the contrast.
        t_eff = (0.50 * fine + 0.40 * (crown - 0.66667) - 0.22 * seam
                 + 0.16 * (wn - 0.5))

        # POROSITY, poisson-disk. A jittered lattice whose jitter (+-0.22 cells) plus
        # radius (<=0.27 cells) stays under half a cell IS a poisson-disk set: every
        # pore keeps a guaranteed 0.56-cell clearance from every other AND can never
        # spill into a neighbour and be sliced by the lattice it was drawn on. That
        # even spacing is the entire tell — clumped dots read as noise, evenly
        # spaced dots read as gas porosity.
        p = float(P["pitch"])
        gh, gw = int(h * 1.40 / p) + 2, int(w * 1.40 / p) + 2
        jy = (rg.random((gh, gw), dtype=np.float32) - 0.5) * 0.44
        jx = (rg.random((gh, gw), dtype=np.float32) - 0.5) * 0.44
        rad = ((0.185 + 0.085 * rg.random((gh, gw), dtype=np.float32))
               * (rg.random((gh, gw), dtype=np.float32) < float(P["poros"])))

        u = pxx * np.float32(1.0 / p)
        v = (py + 0.32 * h) * np.float32(1.0 / p)   # rotation makes py negative
        fu, fv = np.floor(u), np.floor(v)
        iu, iv = fu.astype(np.int32), fv.astype(np.int32)
        du = u - fu - 0.5 - jx[iv, iu]
        dv = v - fv - 0.5 - jy[iv, iu]
        r = rad[iv, iu]
        # A spherical pore removes a CHORD of metal, 2*sqrt(r^2 - d^2). The square
        # root is why a pore prints with a hard rim rather than a soft blob — it is
        # geometry, not a chosen falloff. Gas collects where the metal freezes last,
        # so depth is biased onto the pass centreline at full pixel accuracy (a
        # per-cell centreline bias drifts off the wandering bead by up to 6px).
        chord = np.sqrt(np.clip(r * r - du * du - dv * dv, 0.0, None))
        pmask = np.clip(chord * float(P["depth"]), 0, 1) * (0.42 + 0.58 * crown)

        # Density is LINEAR in path length (log-response emulsion), so: subtract.
        # Centred on its own MEDIAN (subsampled, 65k samples, ~1ms) rather than its
        # mean, which parks the parent plate on the exact middle rung of the ladder
        # the spec reads this field with — measured R 175 / CC 150 dead on the
        # assigned background, on all ten variant samples.
        med = float(np.median(t_eff[::8, ::8]))
        # Film grain, ONE octave: silver halide CLUMPS, so a ~4.6px lattice is the
        # right model and a 1px hash is not. Amplitude 0.076 pk-pk is under a
        # quarter of a ladder rung, so it grains the rung edges instead of
        # dithering them into confetti (measured grit 0.05-0.08, coherence 0.62).
        g = K.mid(shape, 4.6, seed + 77, octaves=1)
        base = np.clip(0.5 - 0.95 * (t_eff - med) + (g - 0.5) * 0.076, 0.0, 1.0)
        # The pore does not merely darken the plate, it OVERRIDES it toward fully
        # exposed film — that much metal is simply gone, so the ripple cannot show
        # through. Blending toward 1 (rather than subtracting) is also what makes a
        # pore read as a separate round void instead of a notch in the ripple.
        return (base + (1.0 - base) * pmask).astype(np.float32)

    return K.cache(("flrad", h, w, int(seed), _k(P)), build)


def paint_fl_radiograph_weld(paint, shape, mask, seed, pm, bb):
    """The livery as the beam wrote it: density darkens the paint, pores punch black."""
    P = _P("fl_radiograph_weld")
    src = K.incoming(paint, shape)
    dens = _radiograph(shape, seed, P)
    a = float(np.clip(float(P["amp"]) * float(pm), 0.0, 1.7))
    # cool and warm are disjoint by construction (dens > 0.50 vs dens < 0.30), so
    # the two sequential blends the first cut used collapse into one weighted sum —
    # six fewer full-canvas channel ops for identical pixels.
    cool = np.clip((dens - 0.50) * 1.7, 0, 1) * (0.52 * a)   # film base in the pores
    warm = np.clip((0.30 - dens) * 3.2, 0, 1) * (0.30 * a)   # lightbox through the crowns
    # Multiplicative, so the painter's hue survives — the film only decides how much
    # of their colour the beam let through, and the emitted film colours ride on top.
    gain = (1.0 - 0.72 * a * (dens - 0.5)) * (1.0 - cool - warm)
    out = (src * gain[:, :, None]
           + _FILM_BASE * cool[:, :, None] + _LIGHTBOX * warm[:, :, None])
    return K.finish(out, src, mask)


def spec_fl_radiograph_weld(shape, seed, sm, base_m, base_r):
    """GRAMMAR: film-density ladder — the densitometer step wedge a radiograph is read against.

    Thirteen flat density rungs — a step wedge, not a ramp — every one of them cut
    from the SAME cached field object the paint used, so the spec cannot drift off
    the picture (measured FOLLOW 0.958-0.987 across all ten variants). Heavier
    silver deposit reads smoother and deeper, so R and CC fall together; only the
    saturated pore cores earn real metallic, because that is where the halide
    reduced all the way to silver.

    Thirteen rungs and gamma 0.95 together: measured, 13 rungs lift the shade count
    to 0.365 and 0.95 is the gain at which the field actually reaches rung 0 and
    rung 12 (at 0.70 the plate only spanned rungs 2-12 and threw two materials
    away). The field is centred on its own median, so the middle rung IS the
    assigned background — measured median M10 / R175 / CC150.
    """
    dens = _radiograph(shape, seed, _P("fl_radiograph_weld"))
    pore = np.clip((dens - 0.72) * 3.6, 0.0, 1.0)
    M = np.clip(K.ladder(dens, 13, 0.0, 20.0) + K.ladder(pore, 6, 0.0, 96.0) * sm, 0, 255)
    R = np.clip(K.ladder(dens, 13, 231.0, 119.0), 15, 255)
    CC = np.clip(K.ladder(dens, 13, 206.0, 94.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════ CT SLICE ══
def _ct_slice(shape, seed, P):
    """Filtered-backprojection reconstruction carrying its two signature artifacts.

    RING ARTIFACT — one mis-calibrated detector CHANNEL reports the same wrong
    value at the same distance from the isocentre in EVERY projection, so it
    back-projects into a complete circle at exactly that channel's radius. Which
    channels have drifted is a sparse irregular set, and that is where the
    NON-uniform ring spacing genuinely comes from. Built literally that way: a
    1-D per-channel gain error, gathered through the radial coordinate — so the
    whole ring field costs one 1-D array and one gather, never a loop over rings.

    METAL STREAK — a dense implant starves the detector along every ray that
    passes through it, and filtered backprojection smears that missing data back
    out as straight alternating bright/dark rays.

    Returns the artifact split into the two components the paint SUMS, so the
    spec can re-weight those same two fields instead of inventing one.
    """
    h, w = shape[:2]

    def build():
        py, pxx = K.px(shape)
        rng = np.random.default_rng((int(seed) ^ 0x0C7A5) & 0xFFFFFFFF)
        # The isocentre is placed just OFF the panel. A reconstructed slice is
        # 500mm across and a car panel is a crop of it, so an off-axis crop is the
        # honest geometry — and it is the only way to be rid of the bullseye: with
        # the centre on canvas the innermost rings collapse into a 200px target
        # motif, which is a poster, not a field. It also pays on the axis that
        # matters: across ten sampled variants, worst-case coarse energy fell from
        # 0.48 to 0.21 and worst-case SCALE rose from 0.46 to 0.77.
        sgn = np.float32(1.0) if rng.random() > 0.5 else np.float32(-1.0)
        off = 1.18 + 0.34 * rng.random()
        cy = (0.5 + sgn * off * (0.35 + 0.30 * rng.random())) * h
        cx = (0.5 - sgn * off * (0.35 + 0.30 * rng.random())) * w
        dy, dx = py - cy, pxx - cx
        r = np.sqrt(dy * dy + dx * dx)

        # ── ring artifact: a 1-D detector gain error gathered through the radius ──
        rpx = float(P["ring_px"])
        nb = 18                                       # channels per detector module
        cpx = rpx / float(nb)                         # one channel, in canvas px
        nch = int(2.6 * np.hypot(h, w) / cpx) + 8
        nblk = nch // nb + 1
        # TWO drifted channels per butted detector module, each at its own jittered
        # offset, so the mean ring pitch is rpx/2 (13-22px) while the gaps are
        # genuinely irregular — a tight pair, then a wide clean run. One impulse
        # per module was the first build and it is a jittered COMB: the eye reads
        # even spacing and the panel goes flat between rings.
        j = rng.random(2 * nblk).astype(np.float32)
        err = rng.random(2 * nblk).astype(np.float32) * 2.0 - 1.0
        err *= 0.30 + 0.70 * rng.random(2 * nblk).astype(np.float32) ** 2  # a few loud rings
        pos = np.clip((np.repeat(np.arange(nblk), 2) * nb + nb * j).astype(np.int32),
                      0, nch - 1)
        # QUANTUM MOTTLE, and it costs nothing: EVERY channel is slightly off, not
        # only the loud ones, so the noise floor goes into the same 1-D profile and
        # comes out of the same gather. That is why the filler texture here is
        # concentric micro-fringe rather than blobs — it is the identical mechanism
        # one order down, and a real slice is never flat between its rings. The
        # first build left the floor out and the 1:1 crop was flat paint over half
        # the canvas (measured: 0.50 of the panel below 0.02 local contrast, now
        # 0.30), which is the empty-field look the coverage law is aimed at even
        # though SCALE passed at 0.77.
        bad = (rng.random(nch).astype(np.float32) - 0.5) * np.float32(float(P["mottle"]))
        bad[pos] += err
        # A bad channel does not reconstruct as a plain line: FBP's RAMP FILTER is
        # a derivative-like operator, so an impulse comes back as a bright core
        # flanked by two dark lobes. Building the ring from that point-spread
        # function is both the correct physics and what pins the energy in the car
        # window — the DC-free hat cannot leak into the coarse band, which a plain
        # smoothed impulse train did (measured, ring field: energy above 32px
        # 0.48 -> 0.03, dominant period 57px -> 16px).
        psf = np.convolve(np.array([0.25, 0.62, 1.0, 0.62, 0.25], np.float32),
                          np.array([-0.5, 0.0, 1.0, 0.0, -0.5], np.float32))
        prof = np.convolve(bad, psf, mode="same").astype(np.float32)
        # A helical acquisition moves the table while the gantry turns, so the
        # isocentre wanders and the rings come out slightly out of round. This is
        # PHASE modulation of a fine carrier, so it costs nothing in the coarse
        # band while stopping the arcs from reading as drafted circles.
        rq = r + (K.mid(shape, 260.0, seed + 11, octaves=2) - 0.5) * np.float32(0.8 * rpx)
        rq *= np.float32(1.0 / cpx)
        np.clip(rq, 0.0, nch - 1.002, out=rq)
        i0 = rq.astype(np.int32)
        # LINEAR gather, not nearest. Nearest-neighbour indexing quantises each
        # channel into a 1.4-2.4px stair along every arc, and that stair is exactly
        # what the anti-confetti term reads as incoherent pixel energy: measured
        # over ten variants, grit 0.21-0.27 -> 0.04-0.08 and neighbour coherence
        # 0.12-0.21 -> 0.50-0.74, for four array ops.
        fr = rq - i0
        ring = prof[i0] * (1.0 - fr) + prof[i0 + 1] * fr

        # ── metal streaks from three dense points ──
        # The fan is windowed to the annulus where its lobes are 6-15px wide. A
        # sin(lobes*theta) fan has lobe width r*2pi/lobes, so inside r=lobes it
        # aliases into 1px hash — confetti — and beyond r=2.4*lobes it is coarse
        # smear. Both ends are OFF the car window, so both are windowed away and
        # only the correctly-sized part of the artifact survives.
        lob = float(P["lobes"])
        star = np.zeros((h, w), np.float32)
        ri2 = np.float32(lob * lob)
        inv_span = np.float32(1.0 / (((2.4 * lob) ** 2) - lob * lob))
        inv_c2 = np.float32(1.0 / (0.55 * lob) ** 2)
        ry = rng.permutation(3)
        rad_out = int(2.4 * lob) + 2
        for i in range(3):
            # One implant per canvas third in BOTH axes. Free placement let two
            # fans land on top of each other and the 1:1 crop came back as op-art
            # moire — two angular carriers of nearly the same pitch beating into a
            # dot lattice — and stratifying x alone left all three on one line.
            sy = (ry[i] * 0.333 + 0.06 + 0.21 * rng.random()) * h
            sx = (i * 0.333 + 0.06 + 0.21 * rng.random()) * w
            # Each fan is evaluated ONLY inside its own support box. Its window is
            # exactly zero beyond r = 2.4*lobes (<=175px), so a full-canvas
            # evaluation spent 4.2M arctan2 + 4.2M sin per implant to write zeros
            # over 98% of them: measured at 2048, that alone was the difference
            # between 3.63s and 1.49s at the expensive corner of the knob space,
            # i.e. the whole render-budget breach.
            y0, y1 = max(0, int(sy) - rad_out), min(h, int(sy) + rad_out)
            x0, x1 = max(0, int(sx) - rad_out), min(w, int(sx) + rad_out)
            ey, ex = py[y0:y1, x0:x1] - sy, pxx[y0:y1, x0:x1] - sx
            q2 = ey * ey
            q2 += ex * ex
            th = np.arctan2(ey, ex)
            th *= lob * (0.82 + 0.36 * rng.random())
            th += 6.2832 * rng.random()
            np.sin(th, out=th)
            core = q2 * inv_c2
            np.clip(core, 0.0, 1.0, out=core)
            core -= 1.0
            core *= core                     # (1-q2/c2)^2 — the polynomial falloff
            u = q2 - ri2
            u *= inv_span
            np.clip(u, 0.0, 1.0, out=u)
            v = 1.0 - u
            u *= v
            u *= 4.0                         # hump: 0 at both ends, 1 mid-annulus
            th *= u
            th += core * 1.5                 # the implant, saturating the window
            star[y0:y1, x0:x1] += th
        # How hard a ray is starved depends on what else it passed through, so the
        # fan is not a uniform spoke wheel. Without this the three fans render as
        # symmetric rosettes — a decorative motif, and the one thing on the 2048
        # sheet that did not read as an inspection image.
        star *= 0.22 + 1.45 * K.mid(shape, 70.0, seed + 23, octaves=2)
        # Each component is standardised on its own so the `streak` knob is a true
        # balance between the two artifacts rather than a level control.
        ring *= np.float32(1.0 / max(1e-4, float(ring.std())))
        star *= np.float32(1.0 / max(1e-4, float(star.std())))
        sw = float(P["streak"])
        t = 0.25 / float(np.sqrt(1.0 + sw * sw))      # combined sd lands ~0.25
        # Beam hardening: the cup is the one macro term, normalised to 18% of the
        # fine layer and mean-removed so it can neither dominate SCALE nor drag the
        # background material cell off M35/R55/CC95.
        cup = r * r
        cup -= float(cup.mean())
        cup *= np.float32(0.18 * t / max(1e-4, float(cup.std())))
        rad = np.clip(ring * np.float32(t) + cup, -1.0, 1.0)
        stw = np.clip(star * np.float32(sw * t), -1.0, 1.0)
        return rad.astype(np.float32), stw.astype(np.float32)

    return K.cache(("ctsl", h, w, int(seed), _k(P)), build)


def paint_fl_ct_slice(paint, shape, mask, seed, pm, bb):
    """CT Slice — the painter's colour is the reconstructed bulk; the scanner's
    artifacts are ADDED on top of it exactly the way a real scanner adds them."""
    P = _P("fl_ct_slice")
    src = K.incoming(paint, shape)
    rad, stw = _ct_slice(shape, seed, P)
    art = np.clip(rad + stw, -1.0, 1.0)
    g = float(P["gain"]) * float(pm)
    out = src * (1.0 + g * art)[:, :, None]
    # Photon starvation saturates the display window, which is why metal always
    # reads as a blown hole in a real slice rather than as a bright object.
    out = out + np.clip(art * 2.0 - 1.4, 0.0, 1.0)[:, :, None] * 0.45
    hue = float(P["hue"])
    if hue > 0.02:
        # CT viewers false-colour by density. Rotating ABOUT the painter's own hue
        # by the artifact amount leaves the bulk (art ~ 0) at their chosen colour.
        out = K.hue_rotate(out, art * hue)
    return K.finish(out, src, mask)


def spec_fl_ct_slice(shape, seed, sm, base_m, base_r):
    """GRAMMAR: radial ramp with streak overlay. Every channel reads BOTH of the
    two fields the paint summed — the continuous artifact ramp `a`, which is the
    paint's own modulation term rebuilt exactly, and one shared quantised streak
    overlay `o` laid over it. No channel reads a field the other two do not, which
    is what puts FOLLOW at 0.87-0.96 across the whole knob space.
    Background — the reconstructed bulk, where both terms are zero by
    construction — lands on M35 / R55 / CC95, held by 0.60-0.74 of the canvas.
    """
    P = _P("fl_ct_slice")
    rad, stw = _ct_slice(shape, seed, P)
    a = np.clip(rad + stw, -1.0, 1.0) * float(sm)      # the paint's exact field
    # The overlay is the streak component alone, quantised into 5 flat steps: it
    # deals distinct material shades with zero added grain, and it is centred so
    # that stw = 0 contributes exactly 0 to all three channels.
    o = K.ladder(np.clip(stw * 0.6 + 0.5, 0, 1), 5, -1.0, 1.0) * float(sm)
    # Metallic reads asymmetrically on purpose: a hot artifact drives the readout
    # hard toward metal, while the ABSENCE of one can only bottom out at
    # dielectric. A symmetric gain piled a visible mass of canvas on the M=0 clip.
    M = np.clip(35.0 + 70.0 * (a + 0.5 * np.abs(a)) + 26.0 * o, 0, 255)
    R = np.clip(55.0 - 74.0 * a - 30.0 * o, 15, 255)
    CC = np.clip(95.0 - 52.0 * a + 34.0 * o, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════ NN · EDDY IMPEDANCE ══
_EDDY_ROW = 1.06        # index step / sweep pitch. Doubles as the isotropy factor:
                        # v is rescaled by it so the loop is drawn in SQUARE units
                        # and a trace is the same width whichever way it runs.
_EDDY_FIT = 1.30        # shrinks the signature to ~77% of its tile. Without it the
                        # lobes of neighbouring tiles touch and the field reads as
                        # connected diagonal bars instead of separate probe readings.
_EDDY_LIFT = 0.24       # the LIFT-OFF SLIVER: loop opening over sound metal. The
                        # curve collapses onto the lift-off line, which is exactly
                        # what an operator sees with no flaw under the coil.
# Phase-coded false colour, the way an impedance screen reads depth: the five
# calibration rungs swept round the colour wheel, shallow (amber) to deep (cyan).
# One row per rung, gathered per pixel — no full-canvas colour maths anywhere.
_EDDY_FALSE = np.array([[1.00, 0.84, 0.34],
                        [1.00, 0.52, 0.20],
                        [0.97, 0.28, 0.44],
                        [0.44, 0.50, 1.00],
                        [0.22, 0.92, 0.88]], np.float32)


def _eddy(shape, seed, P):
    """The impedance plane of an eddy-current probe, tiled on its own scan raster.

    An ECT probe is a coil; the instrument plots its complex impedance as ONE
    point on an XY screen. Sweep the coil and that point draws a curve. Over sound
    metal it only rocks along the LIFT-OFF LINE — a squashed sliver. Over a crack
    the curve opens into the classic figure-eight, and the DEPTH of the crack
    ROTATES the whole signature by a phase angle. Phase analysis is that rotation,
    which is why this finish's spec grammar is a phase ladder.

    Built as the implicit 1:2 Lissajous `v^2 = a^2 u^2 (1 - u^2)` — the curve an
    ECT flaw signal actually draws — folded onto the probe raster at `pitch` px,
    rotated by a QUANTISED phase, and opened only where the sweep crosses a flaw.

    The dominant structure is the loop tile itself, 14-22px, so it sits inside the
    car window: measured at 2048, band 0.650 against coarse 0.029. The only fields
    coarser than a tile are the raster wander and the phase zones, and neither
    carries luminance of its own.

    Returns (mod, rung): the trace field, and the integer phase rung 0-4 that the
    rotation and the false colour are both gathered from.
    """
    h, w = shape[:2]

    def build():
        pitch = float(P["pitch"])
        rowh = pitch * _EDDY_ROW
        py, pxx = K.px(shape)

        # Hand-scanned, not machine-scanned: the operator's index wanders a couple
        # of px over a few hundred, so the raster breathes instead of ruling a grid.
        yy = py + (K.mid(shape, 300.0, seed + 5, octaves=2) - 0.5) * 5.0
        ry = yy * (1.0 / rowh)
        row = np.floor(ry)
        fv = (ry - row - 0.5) * (2.0 * _EDDY_ROW)           # square units, see _EDDY_ROW
        half = row * 0.5
        ux = pxx * (1.0 / pitch) + (half - np.floor(half))  # alternate passes index half
                                                            # a tile over (frac of row/2 is
                                                            # exactly 0 or 0.5, and measured
                                                            # cheaper than np.mod)
        fu = (ux - np.floor(ux) - 0.5) * 2.0                # -1..1 along the sweep

        # ── THE FLAW. A crack is a filament, never a blob, so it is the median
        #    level-set of a noise field, not the noise field. Streaking the field
        #    along Y before taking the level-set aligns the cracks with Y, which
        #    means the X sweep CROSSES them — a probe only sees a flaw it cuts
        #    across, and that geometric fact is the whole point of a raster scan.
        n = K.norm(K.streak(K.mid(shape, float(P["crack_px"]), seed + 21, octaves=2), 26, axis=0))
        ridge = 1.0 - np.abs(n * 2.0 - 1.0)
        flaw = np.clip((ridge - 0.80) * 5.0, 0, 1)
        flaw = flaw * flaw                                  # squared -> a hairline, not a smear

        # ── THE PHASE LADDER. Depth rotates the signature. Quantised into five
        #    bands because a phase screen is read against discrete calibration
        #    angles (lift-off, ID notch, OD notch), never a continuum. This is
        #    K.ladder(.., 5, 0, 1) written so the INTEGER rung survives, which
        #    turns cos/sin into a 5-row gather instead of two full-canvas
        #    transcendentals — and gives the paint its palette index for free.
        #    K.norm first, and it is not cosmetic: raw K.mid at octaves=2 is a mean
        #    of two uniforms, so it spans only ~0.09-0.79 and the deepest rung
        #    measured 0.000-0.001 of the canvas over three seeds. The deepest
        #    calibration angle — and the top of the spec ladder with it — never
        #    fired at all. Normalised, the five rungs measure 0.06-0.40 each.
        rung = np.floor(K.norm(K.mid(shape, 330.0, seed + 11, octaves=2)) * 4.999)
        rung = rung.astype(np.int32)
        angs = 0.35 + float(P["span"]) * (np.arange(5, dtype=np.float32) * 0.25)
        ca = (np.cos(angs) * _EDDY_FIT).astype(np.float32)[rung]
        sa = (np.sin(angs) * _EDDY_FIT).astype(np.float32)[rung]
        u = fu * ca + fv * sa
        v = fv * ca - fu * sa

        # ── THE SIGNATURE. `a` is the loop opening, and it is the FLAW that opens
        #    it: as a falls the curve collapses onto the lift-off line, which is
        #    literally what a sound-metal trace does. Distance to the curve is
        #    |F| / |grad F| — measured, the explicit branch form
        #    v = +/- a*u*sqrt(1-u^2) smears at the turnarounds where the tangent
        #    goes vertical, and this Newton form does not.
        a = _EDDY_LIFT + float(P["open"]) * flaw
        aa = a * a
        u2 = u * u
        f = v * v - aa * u2 * (1.0 - u2)
        gx = aa * u * (4.0 * u2 - 2.0)
        gy = v + v
        d = np.abs(f) / (np.sqrt(gx * gx + gy * gy) + 0.05)
        t = np.clip(1.0 - d * (pitch * 0.5 / float(P["thick"])), 0, 1)
        trace = t * t * (3.0 - 2.0 * t)      # smoothstep: a phosphor trace has no hard
                                             # edge, and a hard edge would spill energy
                                             # below the 8px floor, where it counts
                                             # AGAINST the car-window ratio, not for it

        # ONE field, and the only spatial modulation either function uses. Signal
        # strength is (deeper phase -> hotter trace) x (on the crack -> hotter
        # still), so a shallow zone can only climb part way up the spec ladder.
        lvl = rung.astype(np.float32) * 0.25
        mod = np.clip(trace * (0.62 + 0.38 * lvl) * (0.60 + 0.62 * flaw), 0, 1)
        return mod.astype(np.float32), rung.astype(np.uint8)

    return K.cache(("fleddy", h, w, int(seed), _k(P)), build)


def paint_fl_eddy_impedance(paint, shape, mask, seed, pm, bb):
    """Metal under test, with the probe's own impedance trace written onto it."""
    P = _P("fl_eddy_impedance")
    src = K.incoming(paint, shape)
    mod, rung = _eddy(shape, seed, P)
    # An instrument colour-codes the trace BY PHASE ANGLE so depth reads at a
    # glance. Both halves of that colour are built as a 5-ROW PALETTE and gathered:
    # the painter's own colour rotated by the same phase the loop is rotated by,
    # plus the emitted false colour. Rotating a 5x3 palette instead of the canvas
    # is exact and measured 0.20s cheaper per 2048 render than a full-canvas
    # K.hue_rotate — the phase only ever takes five values, so per-pixel hue
    # maths was 4.2M evaluations of a five-entry table.
    avg = src[::16, ::16].reshape(-1, 3).mean(0).astype(np.float32)
    angs = (0.35 + float(P["span"]) * (np.arange(5, dtype=np.float32) * 0.25))[None, :]
    pal = np.clip(K.hue_rotate(np.repeat(avg[None, None, :], 5, axis=1), angs)[0] * 0.42
                  + _EDDY_FALSE * 0.70, 0, 1)
    # The substrate is left FLAT on purpose: `mod` is then the paint's only spatial
    # modulation, so FOLLOW is true by construction rather than by argument
    # (measured amp_corr 0.977 against a 0.35 floor). The painter's colour still
    # carries the panel — it is the whole field between traces, and it tints every
    # phosphor colour on top of it.
    lift = (float(P["amp"]) * float(pm)) * (mod + 0.55 * mod * mod)   # squared term = hot core
    out = src * (0.62 + 0.20 * lift)[:, :, None] + pal[rung] * lift[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_eddy_impedance(shape, seed, sm, base_m, base_r):
    """GRAMMAR: loop-phase ladder — the trace field quantised into six impedance
    rungs, where a phase zone can only climb as high up the ladder as its own phase
    angle drives it. Measured: over sound metal the lift-off zone caps at rung 2 of
    6 and reaches 4 only where a crack opens the loop, while the deepest phase zone
    reaches the top rung. Background is 130/60/22 over 85% of the canvas —
    half-metallic mill stock under a hard-gloss clear, this shelf's only M-130
    story."""
    mod, _rung = _eddy(shape, seed, _P("fl_eddy_impedance"))   # the SAME field the paint used
    q = K.ladder(mod, 6, 0.0, 1.0)
    # The probe shoe drags: where it wrote, the metal is burnished (M up, R down)
    # and the clear above it is hazed by the scuff (CC up, never below the 16 floor).
    # All three channels read q and nothing else, which is the whole of FOLLOW.
    M = np.clip(130.0 + 118.0 * q * sm, 0, 255)
    R = np.clip(60.0 - 42.0 * q * sm, 15, 255)
    CC = np.clip(22.0 + 52.0 * q * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════ NN · THERMOELASTIC STRESS ══
def _tsa(shape, seed, P):
    """TSA: the first stress invariant, delivered on a focal-plane array.

    Under cyclic load a part's temperature swings in phase with the sum of the
    principal stresses; a lock-in IR camera integrates that microkelvin swing
    into a full-field stress map. The map therefore never exists as a continuum
    — it exists at DETECTOR resolution. So the whole physics is computed on the
    (gh, gw) detector lattice (~26k elements) and read out onto the canvas.

    Returns the TWO components the paint modulates with — the pad reading `mod`
    and the fill-factor lane `lane` — so the spec can rebuild the identical
    combination instead of inventing a field of its own.
    """
    h, w = shape[:2]

    def build():
        pitch = float(P["pitch"])
        gh = int(h / pitch) + 2
        gw = int(w / pitch) + 2
        rng = np.random.default_rng((int(seed) ^ 0x7A51) & 0xFFFFFFFF)

        # -- the specimen: first stress invariant around eight raisers --------
        # Kirsch: the invariant round a hole decays as a2/(r2+a2) with a cos2th
        # lobe. Eight superposed raisers (fastener holes, a notch root, a weld
        # toe) is what a cyclically loaded panel actually maps as, and
        # superposition is legitimate because the invariant is linear in the
        # elastic regime. The loop is 8 x ~6 ops on 26k elements — 0.4% of ONE
        # full-canvas op; the no-trig-in-loops rule is about the canvas, which
        # this never touches.
        gy = (np.arange(gh, dtype=np.float32)[:, None] + 0.5) * pitch
        gx = (np.arange(gw, dtype=np.float32)[None, :] + 0.5) * pitch
        cy = rng.random(8).astype(np.float32) * (h * 1.2) - h * 0.1
        cx = rng.random(8).astype(np.float32) * (w * 1.2) - w * 0.1
        sgn = np.where(rng.random(8) < 0.4, -1.0, 1.0).astype(np.float32)
        amp = (rng.random(8).astype(np.float32) * 1.2 + 0.5) * sgn
        # cubed uniform: MOST raisers are tight, one or two are the broad
        # far-field gradient. A flat radius draw rendered as one soft blob, and
        # a stress map with no lobes in it is not a stress map.
        a2 = (0.004 + 0.085 * rng.random(8).astype(np.float32) ** 3) * np.float32(h * h)
        th = rng.random(8).astype(np.float32) * np.float32(np.pi)
        s = np.zeros((gh, gw), np.float32)
        for i in range(8):
            dy = gy - cy[i]
            dx = gx - cx[i]
            lobe = 1.0 + 0.55 * np.cos(2.0 * (np.arctan2(dy, dx) - th[i]))
            s += amp[i] * a2[i] * lobe / (dy * dy + dx * dx + a2[i])
        # a lock-in legend CLIPS at percentile ends; min/max would compress the
        # whole field into two display levels behind one hot raiser.
        lo, hi = np.percentile(s, (3.0, 97.0))
        s = np.clip((s - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0).astype(np.float32)

        # -- the readout: residual non-uniformity after a two-point NUC -------
        # Ordered COLUMN (one ROIC amplifier per column) > row > per-detector,
        # so 85% of the FPN variance is full-height striping. Measured against a
        # 0.62/0.26/0.30 mix at 1:1: identical on every axis (pband 0.370 vs
        # 0.382, FOLLOW 0.528 vs 0.530, grit 0.136 vs 0.137) but visibly calmer —
        # bad COLUMNS instead of per-pad speckle, which is both the real dominant
        # residual after a two-point NUC and the anti-confetti choice.
        col = rng.standard_normal(gw).astype(np.float32)[None, :]
        row = rng.standard_normal(gh).astype(np.float32)[:, None]
        det = rng.standard_normal((gh, gw)).astype(np.float32)
        fpn = (0.72 * col + 0.24 * row + 0.18 * det) / 0.79

        # `stress` is deliberately the SMALL term. Measured: at stress 1.0 the
        # radially-summed power peak jumps off the 12.8px pitch onto the 512px
        # map on a light base — the macro carrying the contrast, which is the
        # documented way this shelf loses SCALE. Capped at 0.72 in SPACE the peak
        # stays on the pitch (or its harmonic) across 65 runs of 4 base colours,
        # and the map still spans 0.14-0.86 of the legend.
        v = 0.5 + float(P["stress"]) * (s - 0.5) + float(P["fpn"]) * fpn * 0.20

        # -- the defect map every array ships with ----------------------------
        u = rng.random((gh, gw)).astype(np.float32)
        v = np.where(u < 0.0035, 0.98, v)            # stuck-high detectors
        v = np.where(u > 0.9973, 0.02, v)            # dead, non-responsive
        # the display LUT: 18 discrete levels, applied on the LATTICE so the
        # canvas pays a gather instead of a quantiser.
        cell = K.ladder(np.clip(v, 0.0, 1.0), 18, 0.0, 1.0)

        # -- read the array out onto the canvas -------------------------------
        # A sensor grid is axis-aligned, so every coordinate term is SEPARABLE:
        # row and column indices are 1-D and the only canvas-wide operations are
        # one gather and one broadcast minimum. The 2-D fancy-index version of
        # this cost 3x the time for identical pixels.
        inv = np.float32(1.0 / pitch)
        uy = np.arange(h, dtype=np.float32) * inv
        ux = np.arange(w, dtype=np.float32) * inv
        iy, ix = uy.astype(np.int32), ux.astype(np.int32)
        # Fill factor: a detector is not the whole cell. The lane between pads is
        # unresponsive silicon over the ROIC, and that lattice — one line every
        # `pitch` px — is this finish's fine, perfectly coherent band.
        g = float(P["fill"])
        wy = np.clip((0.5 - np.abs(uy - iy - 0.5)) / g, 0.0, 1.0)
        wx = np.clip((0.5 - np.abs(ux - ix - 0.5)) / g, 0.0, 1.0)
        lvl = cell[iy][:, ix]
        web = np.minimum(wy[:, None], wx[None, :]).astype(np.float32)
        lane = (lvl - lvl * web).astype(np.float32)      # the pad reading LOST to the lane
        # 0.82, not the 0.66 first tried: a deeper lane took the paint's own fine
        # band from 0.353 to 0.472 AND lifted the worst-corner FOLLOW from 0.352
        # (a fail) to 0.438, because it moves paint contrast out of the smooth map
        # and onto the lattice. Same two numbers, one constant.
        mod = np.clip(lvl - 0.82 * lane, 0.0, 1.0).astype(np.float32)
        return mod, lane

    return K.cache(("tsa", h, w, int(seed), _k(P)), build)


def _iron(ph, b):
    """The IRON scale as a 256-entry LUT, pre-rotated and pre-scaled by `blend`.

    Two measured reasons for the shape of this. (1) A RAINBOW legend dropped
    FOLLOW to -0.03: a rainbow's luminance is a tent in the signal, so blending
    it over the paint cancelled the map's own luminance ramp. An iron scale
    (black-purple-red-orange-yellow-white) climbs monotonically, and the `y`
    line below forces that exactly. It must run AFTER the rotation, not before:
    hue_rotate preserves r+g+b but not luma, so rotating a pre-normalised iron
    scale onto a BLUE base flattened its luma ramp and took FOLLOW to 0.214.
    (2) Evaluating the three ramps on the canvas and then hue-rotating the image
    cost ~30 full-canvas ops for a function of ONE scalar field — as a LUT it is
    a gather.
    """
    t = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    lut = np.stack([np.clip(2.60 * t - 0.30, 0, 1),
                    np.clip(2.40 * t - 1.25, 0, 1),
                    np.clip(0.85 - 2.7 * np.abs(t - 0.30), 0, 1)
                    + np.clip(3.60 * t - 2.60, 0, 1)], axis=1)
    lut = np.clip(K.hue_rotate(lut[:, None, :], ph)[:, 0, :], 0.0, 1.0)
    y = lut @ np.float32([0.2126, 0.7152, 0.0722])
    lut *= ((0.10 + 0.95 * t) / (y + 0.03))[:, None]
    return (lut * float(b)).astype(np.float32)


def paint_fl_tsa_stress(paint, shape, mask, seed, pm, bb):
    """Thermoelastic stress map, read out on the camera's own detector grid.

    A TSA map is FALSE COLOUR — one of the cases the brief allows a finish to
    emit its own colour — so the legend is emitted rather than borrowed. But it
    is rotated onto the painter's hue and BLENDED over their paint: their colour
    is the unloaded datum the scale runs out of.
    """
    P = _P("fl_tsa_stress")
    src = K.incoming(paint, shape)
    mod, lane = _tsa(shape, seed, P)

    # Anchor the scale's characteristic hue on the painter's own. Measured: a
    # fixed legend brought a white, a silver and a black base back as
    # near-identical maps — the base choice stopped reading. The phase is a
    # SCALAR off a 1/64-area sample, and it fades to zero on an achromatic base,
    # which leaves the native iron scale.
    q = src[::8, ::8]
    e1 = float(2.0 * q[:, :, 0].mean() - q[:, :, 1].mean() - q[:, :, 2].mean())
    e2 = float(1.7320508 * (q[:, :, 1].mean() - q[:, :, 2].mean()))
    ph = np.clip(float(np.arctan2(e2, e1)), -1.05, 1.05) * min(1.0, float(np.hypot(e1, e2)) / 0.12)
    b = float(P["blend"])
    lutb = _iron(ph, b)

    # Display gain works on the specimen, the legend is BLENDED over it: an
    # additive overlay clipped a white base to paper and still left a black one
    # unlit. The clip is not cosmetic — at pm=2 with gain at the top of SPACE
    # the factor would otherwise go NEGATIVE in the lane.
    gain = np.clip(1.0 + (mod - 0.5) * (float(P["gain"]) * float(pm)), 0.06, 2.2)
    idx = (mod * 255.0).astype(np.uint8)
    out = src * (gain * (1.0 - b))[:, :, None] + lutb[idx]
    return K.finish(out, src, mask)


def spec_fl_tsa_stress(shape, seed, sm, base_m, base_r):
    """GRAMMAR: sensor-grid quantised map. Every material value is dealt on the
    detector lattice — flat across a pad, stepped between pads — and the only
    second material is the unresponsive fill-factor lane.

    FOLLOW is constructed, not argued: `mod` and `lane` here are the SAME cached
    arrays the paint modulated with, and all three channels are an affine
    function of that one pair. The RATIO matters as much as the fields — the
    paint's luma is (lvl - 0.82*lane), and when the spec's luma ran 4.3x more
    lane than pad, FOLLOW measured 0.38-0.43. Bringing the ratio to ~1.1x (wide
    lam spans, moderate lane spans) put it at 0.48-0.81 over 65 runs.

    Dominant material (pad, lane~0): M 5-37 / R 86-116 / CC 33-61 — the quantised
    cell (0, 2, 1), the assigned 18/100/45 bucket, at 81-90% of canvas. Channel
    means measured 14-17 / 108-113 / 54-59, all inside the assigned +/-15. The
    lane is the only departure and it supplies the other two signature cells,
    (0, 3, 1) at 6-10% and (0, 2, 0) at 4-8%.
    """
    P = _P("fl_tsa_stress")
    mod, lane = _tsa(shape, seed, P)
    lam = K.ladder(mod, 9, 0.0, 1.0)      # material ladder, coarser than the display LUT
    # A hotter pad is polished bright by the load it is reading; the lane is bare
    # matte silicon over the readout circuit — dielectric, rough, no clear.
    M = np.clip(5.0 + 32.0 * lam * sm - 3.4 * lane, 0, 255)
    R = np.clip(116.0 - 30.0 * lam + 34.0 * lane, 15, 255)
    CC = np.clip(33.0 + 28.0 * (1.0 - lam) + 32.0 * lane, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════ PULSE THERMOGRAPHY ══
# Flash the panel with a heat pulse, then film it cool.  Sound laminate sinks
# that heat straight into the bulk and goes dark; a subsurface delamination
# blocks the conduction path, so it holds its heat and lights up LATE.  Two
# measured facts of the technique drive the whole finish: a flaw's contrast
# peaks at a time that goes as the SQUARE of its depth (t_peak ~ z^2/alpha),
# and the same diffusion that delays it also spreads it sideways — so deeper
# flaws arrive later, dimmer AND blurrier.  One depth map therefore sets
# brightness, edge softness and, where there is no flaw at all, the back-wall
# thickness contours that fill the cool field (wall-thinning mapping is what
# this kit is actually sold to do).
_PT_FLOOR = 0.30           # sound-material plateau — the cool background of the frame
_PT_ZLO, _PT_ZHI = 0.40, 2.45   # depth ladder ends, in units of sqrt(frame time)
_PT_HALO = 0.100           # lateral-diffusion penumbra width per unit depth
_PT_FPN = 0.030            # focal-plane-array fixed-pattern noise level
_PT_IRON = 0.85            # how far the emitted iron palette displaces the base at peak
_PT_COLD = np.float32([0.10, 0.06, 0.24])   # the violet an iron palette shows below plateau


def _pulse_thermo(shape, seed, P):
    """The thermogram: temperature ABOVE the sound-material plateau, one frame."""
    h, w = shape[:2]

    def build():
        # Sizes are canvas FRACTIONS, not raw pixels.  scale_axis puts its annulus
        # at FFT radii 64-256 whatever the render size, so it always scores the
        # 8-32px-at-2048 window; a literal 18px lattice rendered at the law's 1024
        # would be scored there as a 36px feature.  With S the same code measures
        # band 0.494 at 1024 and 0.498 at 2048, and mean luma 0.302/0.299/0.303 at
        # 256/512/1536 — the agreement IS the check that this is right.
        S = h / 2048.0
        fp = max(5.0, float(P["flaw_px"]) * S)

        # WHERE the disbonds are.  The 0.05 ruffle is not decoration: thresholding
        # a bilinear lattice at high gain shows straight facets and diamond
        # corners at 1:1, and a fine offset on the threshold field breaks them
        # into the irregular outlines a real disbond has.
        site = (K.mid((h, w), fp, seed + 11, octaves=3, falloff=0.46)
                + 0.05 * (K.mid((h, w), fp * 0.34, seed + 14, octaves=2) - 0.5))

        # HOW DEEP each one is, quantised.  Quantising is the technique, not a
        # shortcut: pulse thermography is read as time-of-flight, and a depth map
        # is delivered as discrete iso-depth contours.  Every step is one
        # decay-time family, and this ladder is also the spec grammar below.
        zf = K.mid((h, w), fp * 1.8, seed + 12, octaves=1)
        z = K.ladder(zf, int(round(float(P["depths"]))), _PT_ZLO, _PT_ZHI)

        # WHEN we look.  u = t_peak/t, and the peak-normalised flaw-contrast curve
        # u*e^(1-u) is 1 at u=1 and falls away both sides — families whose moment
        # has passed have faded back into the plate, families deeper than the
        # frame have not surfaced yet.  That is the whole job of "frame".  One
        # exp over the canvas, never one inside a loop.
        u = (z * z) * (1.0 / float(P["frame"]))
        resp = u * np.exp(1.0 - np.minimum(u, 9.0))

        # Depth drives BOTH ramps, which is how "deeper = blurrier" costs nothing.
        # The alternative — blur passes blended by a per-depth weight — cuts every
        # halo at a depth-plateau seam, because the weight is piecewise constant
        # and the halo is not.  (A blur could not be the load-bearing mechanism
        # here anyway: every low-pass moves power across the gate's 32px cutoff.)
        d = site - float(P["thresh"])
        g = d * (float(P["sharp"]) / z)
        edge = np.clip(g, 0.0, 1.0)
        core = edge + 0.30 * np.clip(g - 1.0, 0.0, 1.0)     # centres keep climbing
        pen = np.clip(d / (_PT_HALO * z) + 1.0, 0.0, 1.0)   # the diffusion penumbra
        prof = core + 0.40 * (pen - edge)
        # In-plane conduction in a laminate is anisotropic — heat runs along the
        # surface ply — so each indication gets a short tail on one axis.
        flaw = K.streak(prof * resp, max(2, int(round(3.0 * S))), axis=1)

        # Focal-plane-array fixed-pattern noise: per-detector column and row
        # offsets plus ROIC readout-channel banding.  This is the opposite of
        # sprinkled hash — every value is constant down a whole column, so the
        # residual correlates with its own neighbour (measured grit 0.024,
        # coherence 0.75 at 2048).  Block sizes are 7/5/34px at 2048, not the
        # 3/2/26 first drafted: at 3px the striping sits BELOW the gate's 8px
        # edge, where it is pure denominator — invisible on a car and a drag on
        # SCALE.  Two 1-D vectors, two broadcasts, no full-canvas RNG.
        rng = np.random.default_rng((int(seed) * 9176 + 31) & 0xFFFFFFFF)
        cw, rh = max(1, int(round(7.0 * S))), max(1, int(round(5.0 * S)))
        bw = max(2, int(round(34.0 * S)))
        cols = np.repeat(rng.random(-(-w // cw), dtype=np.float32), cw)[:w] - 0.5
        rows = np.repeat(rng.random(-(-h // rh), dtype=np.float32), rh)[:h] - 0.5
        band = np.repeat(rng.random(-(-w // bw), dtype=np.float32), bw)[:w] - 0.5
        fpn = (cols + 0.30 * band)[None, :] + 0.55 * rows[:, None]

        # The only macro term is the flash lamp's own uneven heating, and it is
        # held at 5%.  SCALE is a RATIO, so a loud coarse layer cannot be bought
        # back with fine detail — it just moves both halves of the fraction.
        lamp = K.mid((h, w), 520.0 * S, seed + 13, octaves=1) - 0.5
        # Where nothing is delaminated the echo comes off the BACK WALL, so the
        # same depth map reads as wall thickness: thicker sinks more heat and runs
        # cooler.  This is what puts stepped thickness contours through the ~80%
        # of the canvas that is sound material instead of leaving it flat grey.
        # Held at 0.075: pushed to 0.090 the paint's own band fell 0.396 -> 0.331.
        zn = (z - _PT_ZLO) * (1.0 / (_PT_ZHI - _PT_ZLO))

        return (float(P["amp"]) * flaw
                - 0.075 * (zn - 0.5)
                + _PT_FPN * fpn
                + 0.050 * lamp).astype(np.float32)

    return K.cache(("pulse_thermo", h, w, int(seed), _k(P)), build)


def paint_fl_pulse_thermo(paint, shape, mask, seed, pm, bb):
    """One frame off the IR camera, false-coloured ON TOP of the owner's paint."""
    P = _P("fl_pulse_thermo")
    src = K.incoming(paint, shape)
    hot = np.clip(_PT_FLOOR + _pulse_thermo(shape, seed, P) * float(pm), 0.0, 1.0)
    exc = hot - _PT_FLOOR
    # Gain 0.30 + 0.86*hot, not 0.34 + 1.02*hot: the steeper ramp clipped every
    # indication to white on a white livery, where the finish measured amp 0.079
    # against 0.255 on grey.  At this slope the base only saturates past hot 0.81,
    # by which point the iron blend below is already at full weight — white now
    # measures amp 0.141 / band_abs 0.042 (was 0.079 / 0.027).
    body = src * (0.30 + 0.86 * hot)[:, :, None]
    # A true ironbow is TWO-ENDED, so the palette is dealt at both ends and the
    # painter's colour keeps the middle.  This replaces a per-pixel K.hue_rotate
    # that cost 300+ full-canvas ops by itself: measured, the finish went from
    # 772 to 459 full-canvas ops total, i.e. from ~1.5-2x a shipped sibling on
    # this shelf to parity with it.  The two-ended blend is the truer palette
    # anyway — an iron LUT is violet at the cold end, not desaturated base.
    iron = np.dstack([np.clip(hot * 2.40 - 0.42, 0, 1),
                      np.clip(hot * 2.30 - 1.35, 0, 1),
                      np.clip(hot * 2.40 - 1.98, 0, 1)])
    fc = (np.clip(exc * 2.6, 0.0, 1.0) * _PT_IRON)[:, :, None]
    out = body + (iron - body) * fc
    # The cold shoulder lands ONLY on the thickest back-wall steps, so the sound
    # field stays the painter's own colour, tinted by wall thickness — measured
    # dead 0.000 on white, grey, red, blue and near-black bases.
    cold = (np.clip(exc * -6.0, 0.0, 1.0) * 0.42)[:, :, None]
    return K.finish(out + (_PT_COLD - out) * cold, src, mask)


def spec_fl_pulse_thermo(shape, seed, sm, base_m, base_r):
    """GRAMMAR: decay-time ladder.  The SAME thermogram field the paint used,
    quantised THREE ways off one expression — coarse steps for the flaw decay
    families, two finer steps for back-wall thickness inside sound material.
    All three channels read that one field, which is what makes FOLLOW true by
    construction (measured 0.883 at 2048, 0.881 at 1024, worst of ten SPACE
    samples 0.665 — the axis wants 0.35).

    Story: heat-soaked, resin-rich delamination glazes up — metallic climbs,
    roughness drops, clearcoat tightens toward gloss — over a matte, near
    dielectric composite skin.  Background cell is M8 / R130 / CC75, this
    shelf's alone.  The wall ladders are one-sided UP on M and R deliberately:
    130 sits only 2.5 above the R cell boundary at 127.5, so a centred spread
    would drop a slice of the dominant area into a neighbouring material cell
    and split the story.  Measured dominant cell (0,3,1) at 81.6% of canvas,
    mean 18/141/65 — inside the +/-15 the STORY axis allows, with room to spare.
    """
    P = _P("fl_pulse_thermo")
    t = _PT_FLOOR + _pulse_thermo(shape, seed, P)
    q = K.ladder(np.clip((t - 0.375) * 1.85, 0.0, 1.0),
                 int(round(float(P["depths"]))), 0.0, 1.0)
    wall = K.ladder(np.clip((t - 0.230) * 5.4, 0.0, 1.0), 7, 0.0, 1.0)
    fine = K.ladder(np.clip((t - 0.262) * 11.0, 0.0, 1.0), 11, 0.0, 1.0)
    # sm drives the two channels that carry the flaw story; CC is left alone so
    # the gloss depth of the glaze is the same at any strength and never walks
    # into the 16 floor from a user slider (measured CC min 18 at sm 0 and sm 2).
    M = np.clip(base_m + 150.0 * q * sm + 13.0 * wall + 6.0 * fine, 0, 255)
    R = np.clip(base_r - 96.0 * q * sm + 15.0 * wall + 6.0 * fine, 15, 255)
    CC = np.clip(75.0 - 38.0 * q - 14.0 * wall - 5.0 * fine, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════ FLAW LAB · ACOUSTIC EMISSION ══
def _ae_hits(shape, seed, P):
    """AE source-location plot: a crack that is GROWING radiates elastic bursts, the
    sensor array triangulates each burst, and the display draws it where it happened,
    ringed by its own amplitude.

    TWO POPULATIONS, because real AE data has two: a canvas-wide background of low-dB
    hits (friction, benign creaking) and, along the damage filament, a second high-dB
    population from the crack itself on a HALF-CELL-OFFSET lattice. Density and dB both
    rise with damage, which is the whole reading of an AE plot.

    The offset is load-bearing, not decoration: a build that put both populations in
    the SAME cell was ~0.11s cheaper and shipped a visible row/column grid on the 1:1
    sheet — the eye completes the rows when there is only one lattice period. Two
    interleaved lattices under a +/-0.8-cell warp read as scattered events.

    No Python loop over events: the site lattice is FOLDED and the plane is
    domain-warped before folding, so sites bunch and thin for the price of one cached
    warp. Each population's radius is capped below its own site's minimum distance to
    the cell wall (0.22 pitch against a site roaming 0.24..0.76; 0.29 against one
    roaming 0.30..0.70), so no marker is ever cut by the fold.
    """
    h, w = shape[:2]

    def build():
        pitch = float(P["pitch"])
        # +/-0.8 cell of displacement over a ~100px scale. The draft's +/-0.53 cell left
        # the lattice legible between clusters; this does not, and costs nothing.
        py, pxx = K.warp(shape, seed + 41, pitch * 1.60, 100.0)

        # DAMAGE FILAMENT. Ridged noise -> lines (a crack front is a line, not a blob),
        # x11 to keep the ridge NARROW, then laddered to 4 flat plateaus. SCALE is a
        # RATIO, so this 260px organiser is allowed to MOVE events and nothing else —
        # it never touches luminance directly. octaves=2, not 3: the third octave lands
        # at ~65px, which is pure coarse-term dilution for a field that is only a map.
        f = K.mid(shape, 260.0, seed + 7, octaves=2)
        dq = K.ladder(np.clip(1.0 - np.abs(f - 0.5) * 11.0, 0.0, 1.0), 4, 0.0, 1.0)

        gh, gw = max(2, int(round(h / pitch))), max(2, int(round(w / pitch)))
        rng = np.random.default_rng((int(seed) ^ 0x4AE7) & 0xFFFFFFFF)
        g = rng.random((6, gh * gw), dtype=np.float32)      # FLAT: np.take beats a 2-D
        #                                                     fancy index (27 vs 54 ms)

        uy = py * np.float32(1.0 / pitch)
        ux = pxx * np.float32(1.0 / pitch)
        inv_sp = np.float32(1.0 / float(P["ring_px"]))
        sharp2 = np.float32(2.0 * float(P["sharp"]))

        def _site(u, v):
            """Cell fraction + ONE flat lattice index, built once and reused by every
            gather off that cell — the index arithmetic costs more than the gathers."""
            fu, fv = np.floor(u), np.floor(v)
            i = np.mod(fu.astype(np.int32), gh)
            i *= gw
            i += np.mod(fv.astype(np.int32), gw)
            return u - fu, v - fv, i

        def _burst(cu, cv, ja, jb, rad, off, spread):
            """One located hit per cell: a filled marker carrying its burst's amplitude
            rings. The ring wave has FIXED pitch and the decay envelope dies at `rad`,
            so a louder event does not draw bigger rings — it draws MORE of them, which
            is what the dB of a burst actually buys on a real display.

            The marker is FILLED (0.38 floor) rather than rings alone: measured, hollow
            rings modulated ~7% of the canvas and band_abs came in at 0.0057 against a
            0.010 floor. Ring pitch and core are held at/above the 8px car window on
            purpose — the draft's 1.4-2px core and 3.2px ring pitch were both BELOW it,
            i.e. pure SCALE dilution, and widening them moved grit 0.154 -> 0.137 and
            coherence 0.339 -> 0.398."""
            dy = cu - (off + spread * ja)
            dx = cv - (off + spread * jb)
            np.multiply(dy, dy, out=dy)
            np.multiply(dx, dx, out=dx)
            dy += dx
            r = np.sqrt(dy, out=dy)
            r *= pitch
            q = rad - r                              # signed distance inside the marker
            t = r * inv_sp
            t -= np.floor(t)
            t -= 0.5
            np.abs(t, out=t)
            t *= sharp2
            t -= 1.0
            ring = np.clip(t, -1.0, 0.0, out=t)      # = -(1 - |saw| * sharp), clipped
            ring *= np.clip(q / rad, 0.0, 1.0)       # the front loses energy as it spreads
            ring *= -0.62
            ring += 0.38                             # filled marker + rings ON it
            ring *= np.clip(q * 0.55, 0.0, 1.0)
            core = np.clip(q - 0.42 * rad, 0.0, 1.4, out=q)   # the located hit itself:
            core *= 0.42                             # a hard 0.58*rad disc, 5-13px wide
            return ring, core

        # --- population 1: background emission. Friction and benign creaking are always
        # there, all over the structure. Low dB, so most of these plot DARK.
        cu1, cv1, i1 = _site(uy, ux)
        amp = np.take(g[2], i1)
        hit = 0.55 * amp                             # no clip: the sum spans 0.02..0.69
        hit += 0.12 * dq
        hit += 0.02
        rad = (0.07 * pitch) * hit
        rad += 0.15 * pitch                          # <=0.22 pitch: the widest safe roam
        ev, core = _burst(cu1, cv1, np.take(g[0], i1), np.take(g[1], i1),
                          rad, 0.24, 0.52)
        # THRESHOLD REJECTION, off the same draw as the amplitude: every AE system has a
        # dB threshold and never records a hit below it, so the cells that go silent are
        # exactly the quietest ones. It also earns its keep visually — silencing a sixth
        # of the cells is what killed the grid read; widening the jitter alone did not.
        awake = np.clip((amp - 0.18) * 8.0, 0.0, 1.0)
        ev *= awake
        core *= awake

        # --- population 2: the crack. Half-cell-offset lattice, and the only place the
        # two readings of an AE plot are separated: `fire` is whether the cell emits at
        # all (DENSITY -> damage) and `loud` is how hard (dB -> damage). A cell far from
        # the filament still fires if its own draw is high enough, so the population
        # thins out into the sound metal instead of stopping at a line.
        cu2, cv2, i2 = _site(uy + 0.5, ux + 0.5)
        q5 = np.take(g[5], i2)
        fire = np.clip((dq + 0.55 * q5 - float(P["gate"])) * 2.5, 0.0, 1.0)
        loud = np.clip(0.15 + 0.62 * dq + 0.34 * q5, 0.0, 1.0)
        rad2 = (0.09 * pitch) * loud
        rad2 += 0.20 * pitch                         # 0.20..0.29 pitch: never clipped
        ev2, core2 = _burst(cu2, cv2, np.take(g[3], i2), np.take(g[4], i2),
                            rad2, 0.30, 0.40)
        vis = np.clip(fire * 4.0, 0.0, 1.0)          # hard-off where the cell is silent,
        ev2 *= vis                                   # so no sub-pixel specks survive
        core2 *= vis
        loud *= vis

        # THE SPECIMEN. An AE plot is drawn ON a structure, and a rolled plate is never
        # optically flat. Streaked 13px noise = mill grain at a tenth of a marker's
        # contrast: it fills the sound metal between clusters (the owner's full-canvas
        # law — measured cover 1.000) without competing with the data. octaves=1, so its
        # whole band sits at 13-23px instead of leaking a 6px octave under the window.
        grain = K.norm(K.streak(K.mid(shape, 13.0, seed + 23, octaves=1), 5, axis=1))
        grain -= 0.5

        # the six-band amplitude legend every AE display is read against
        hit *= awake
        d = K.ladder(np.maximum(hit, loud), 6, 0.0, 1.0)
        return np.maximum(ev, ev2), np.maximum(core, core2), d, grain

    return K.cache(("aehit", h, w, int(seed), _k(P)), build)


def _ae_drive(ev, core, d, grain, gmix):
    """The ONE field the paint modulates with and all three spec channels read back.

    Bipolar on purpose: a low-dB hit plots DARK and a high-dB hit plots BRIGHT, so a
    cluster raises local VARIANCE without raising the local mean — which is what keeps
    the 260px filament out of the coarse half of the SCALE ratio (measured paint_band
    0.500 / spec_band 0.534 against a 0.20 floor).

    The grain enters at a different weight for paint and spec (0.22 / 0.07) and that is
    the ONLY asymmetry: at paint weight it would swing the plate's own bucket by +/-35
    on roughness, and the plate has to stay on 60/110/55 to hold its material story.
    Both still read the SAME field, so FOLLOW measures 0.876-0.948 per channel.
    """
    return (ev * (2.25 * d - 0.78) - 0.85 * core + gmix * grain).astype(np.float32)


def paint_fl_acoustic_emission(paint, shape, mask, seed, pm, bb):
    """Listening for cracks growing: every burst the structure emits is located and
    plotted back onto it, ringed by its own amplitude."""
    P = _P("fl_acoustic_emission")
    src = K.incoming(paint, shape)
    ev, core, d, grain = _ae_hits(shape, seed, P)
    a = np.clip(_ae_drive(ev, core, d, grain, 0.22) * (float(P["gain"]) * float(pm)),
                -1.0, 1.0)

    # THE LEGEND, built as a 6-entry LUT rather than a full-canvas hue rotation: an AE
    # display colours each hit by its dB BAND, and three np.take gathers cost 82ms
    # against 420ms for rotating 4.2M pixels — the same picture for a fifth of the
    # budget. The palette is the painter's OWN colour rotated across the scale, so a
    # blue car plots blue->violet->red and their base choice still reads.
    band = np.arange(6, dtype=np.float32) / 5.0
    # ::16 subsample, not the whole canvas: the full strided mean(0) measured 450ms to
    # produce three numbers, and on a flat base the two agree to float precision.
    seed_rgb = src[::16, ::16].reshape(-1, 3).mean(0).astype(np.float32)
    pal = K.hue_rotate(np.tile(seed_rgb, (1, 6, 1)),
                       ((band - 0.30) * float(P["span"]))[None, :])
    pal *= (0.42 + 0.65 * band)[None, :, None]
    # A false-colour display EMITS: a purely multiplicative marker goes invisible on the
    # liveries that need it most. The draft's emissive floor measured band_abs 0.0100 on
    # a near-black livery — under the 0.010 hard-fail; this one measures 0.0135, and
    # 0.0161-0.0378 on blue / green / grey / white.
    pal += np.stack([0.42 * band + 0.05,
                     0.17 * band + 0.03,
                     0.33 - 0.30 * band], 1)[None]
    pal = pal.reshape(6, 3)

    # Two SCALAR weights, then one 3-channel combine. Compositing plate and marker as
    # HxWx3 (the obvious way) measured 2.9s at 2048 against 0.55s for this; six ops on
    # 12.6M elements is 18 full-canvas ops hiding in four lines.
    idx = (d * 5.0 + 0.5).astype(np.int32)
    pos = np.clip(a, 0.0, 1.0)
    w_src = np.clip(a, -1.0, 0.0)
    w_src *= 0.80                                    # floor 0.05*src, never negative
    # the display's dark field is a MODULATION too, so it scales with pm — at pm=0 this
    # finish hands back the painter's paint untouched, not a 15%-dimmed version
    w_src += 1.0 - min(0.15 * float(pm), 0.32)
    w_src *= 1.0 - pos                               # low dB = DARK
    w_src += 0.24 * pos                              # high dB = HOT
    w_hot = pos * 0.86
    out = np.dstack([src[:, :, c] * w_src + np.take(pal[:, c], idx) * w_hot
                     for c in range(3)])
    return K.finish(out, src, mask)


def spec_fl_acoustic_emission(shape, seed, sm, base_m, base_r):
    """GRAMMAR: event-amplitude rings, three-material. Plate under test / plotted
    amplitude ring / located hit — three materials dealt off ONE field, the same bipolar
    drive the paint painted with, so FOLLOW is true by construction (measured amp_corr
    0.949; M 0.948, R 0.929, CC 0.876 against a 0.35 floor).

    The two rectifier gains are equal in magnitude per channel on purpose: that keeps
    each channel's amplitude envelope proportional to |drive| instead of leaning on one
    half of it (an earlier split of 97 vs 35 on CC measured 0.34 — below the floor —
    while M and R, which were balanced, sat at 0.98).

    Plate 60/110/55 is machined structural alloy under a thin inspection coat:
    half-metal, matte-ish, barely cleared. That bucket is this shelf's alone, and it
    measures 89.6% of the canvas at 59.9 / 110.1 / 55.0.
    """
    ev, core, d, grain = _ae_hits(shape, seed, _P("fl_acoustic_emission"))
    drive = _ae_drive(ev, core, d, grain, 0.07)
    ring = np.clip(drive * 1.9, 0.0, 1.0)        # plotted trace: burnished, hot
    ring *= 0.55 + 0.45 * d       # ...and burnished BY dB: d is already the 6-band
    flaw = np.clip(drive * -2.1, 0.0, 1.0)    # legend, so this deals six clean gloss
    u = (ring - flaw) * float(sm)             # levels inside one material, no grain
    M = np.clip(60.0 + 80.0 * u, 0.0, 255.0)
    R = np.clip(110.0 - 100.0 * u, 15.0, 255.0)
    CC = np.clip(55.0 - 57.0 * u, 16.0, 255.0)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════ NN · STRAIN ROSETTE ══
def _rosette_foil(shape, seed, P):
    """A bonded foil strain-gauge mat: three-element delta rosettes, each element
    a serpentine constantan grid acid-etched from a continuous foil sheet on its
    amber polyimide carrier.

    Etched foil is a SUBTRACTIVE process - the acid opens narrow channels and
    whatever is left is the conductor - so foil is the MAJORITY material and the
    exposed carrier reads as the dark slots between traces. That is why the
    dominant spec area here is metal (M165) rather than backing.

    The three element POSITIONS are 120 deg apart while the three gauge AXES are
    60 deg apart. That difference is the whole point of a delta rosette: it is
    what resolves the full plane strain tensor instead of measuring one direction
    three times.

    SIZING, measured, because this is where the finish nearly died. The law's
    scale_axis fixes its band radii at 256/64 REGARDLESS of render size, so at
    the default --res 1024 the car window is features of 4-16 rendered px, while
    at 2048 it is 8-32. A finish authored in absolute pixels is therefore judged
    twice as coarse at 1024. At a 22px trace pitch this field measured fine=0.183
    at 1024 (FAIL, floor 0.20) and 0.746 at 2048 - it would have passed or failed
    purely on which resolution the gate happened to run. At the 14.75px pitch
    shipped here it measures 0.724 at 1024 and 0.807 at 2048, so it passes either
    way. The hairpin rows (48px) and the site lattice (122px) carry no brightness
    contrast of their own - duty cycle is constant everywhere, so a 60 deg wedge
    and a 0 deg wedge have the same local mean and their boundary is a phase
    discontinuity, not a bright block.
    """
    h, w = shape[:2]

    def build():
        S = float(P["site_px"])
        p = float(P["trace_px"])
        L = float(P["seg_px"])
        duty = float(P["duty"])
        sg = float(P["strain"])

        # Gauges are bonded by hand. A 5px wander over 300px is what an installed
        # mat actually looks like; without it every site is a pixel-exact copy of
        # its neighbour and the canvas reads as wallpaper - compared side by side
        # at 1:1, the rigid version is visibly a repeat and this one is not.
        py, pxx = K.warp(shape, seed + 31, 5.0, 300.0)
        fu = pxx - S * np.round(pxx * (1.0 / S))     # site-local coords, +/- S/2
        fv = py - S * np.round(py * (1.0 / S))

        # ONE noise field serves two things that both follow the part contour:
        # the strain the gauges are reading, and the slow wander of the bonded
        # axis. A second field for the wander cost a whole extra K.mid build and
        # moved no measured axis.
        strain = K.mid(shape, 420.0, seed + 9, octaves=2)
        base = (strain - 0.5) * 0.55

        # Wedge index k picks BOTH the element's position and its axis. Taken mod
        # 3: without that, k lands on -1 or 3 along the +/-pi ray, which negates
        # `lane` there and slips the hairpin pairing by half a period on one ray
        # of every site. mod 3 makes the wrap contiguous - the k=-1 sliver is
        # geometrically adjacent to the k=2 wedge, and k=3 to k=0.
        th = np.arctan2(fv, fu) - base
        k = np.mod(np.floor((th + np.float32(np.pi)) * np.float32(3.0 / (2.0 * np.pi))), 3.0)
        ang = base + k * np.float32(np.pi / 3.0)
        # The builder otherwise holds ~14 live 16MB planes at 2048; freeing each
        # as it dies keeps the peak near 5 and the allocator off the OS.
        del th, k, base
        ca = np.cos(ang)
        sa = np.sin(ang)
        del ang

        lane = (fv * ca - fu * sa) * (1.0 / p)       # across the traces
        s = (fu * ca + fv * sa) * (1.0 / L)          # along the conductor
        del ca, sa

        # ── the serpentine grid ────────────────────────────────────────────
        # The conductor is continuous in `along` and folds at every hairpin row,
        # so the element fills its wedge edge to edge. Clipping it to a fixed
        # rectangle instead would leave a dead carrier block at each site corner,
        # and a dead block at site pitch is exactly the coarse energy SCALE
        # punishes.
        q = np.abs(lane - np.round(lane))
        foil = np.clip((q - (0.5 - duty * 0.5)) * (p / 1.2), 0.0, 1.0)
        del q

        bidx = np.round(s)                           # nearest hairpin row
        dbound = np.abs(s - bidx) * L                # px to that row
        del s
        # Row parity alternates WHICH lane pair turns, so lane 0 joins 1 at one
        # row and 1 joins 2 at the next: a true boustrophedon, one conductor.
        # Folded to a single parity test - frac(lane*0.5 - 0.25 + frac(bidx/2))
        # < 0.5 is the same predicate as floor(lane + bidx - 0.5) being even, and
        # costs three fewer full-canvas ops.
        pair = np.mod(np.floor(lane + bidx - 0.5), 2.0) < 0.5
        del lane, bidx
        # End loops are etched WIDER than the trace on a real gauge - that is how
        # transverse sensitivity is suppressed - hence 0.65 duty here, not 0.5.
        cap = np.clip((duty * 0.65 * p - dbound) * (1.0 / 1.2), 0.0, 1.0) * pair
        del dbound, pair
        np.maximum(foil, cap, out=foil)
        del cap

        # ── solder tab + lead wires ────────────────────────────────────────
        # Both are Chebyshev distance from the site centre, so ONE maximum serves
        # both: inside `rp` is the rectangular terminal tab where the three
        # elements share a pad, outside `e` is the lead wire running along the
        # carrier's die-cut edge. One band test rather than two thresholds and a
        # max is three ops cheaper and is honest about them being one copper
        # plane.
        ch = np.maximum(np.abs(fu), np.abs(fv))
        del fu, fv
        rp = S * 0.075
        e = S * 0.5 - max(1.5, S * 0.020)
        frame = np.clip((np.abs(ch - (rp + e) * 0.5) - (e - rp) * 0.5) * (1.0 / 1.2), 0.0, 1.0)
        del ch
        np.maximum(foil, frame, out=foil)
        del frame

        # THE POINT OF THE TECHNIQUE: the gauge shows the strain the eye cannot.
        # It rides ONLY on the foil and is capped at `strain` <= 0.30 of the
        # foil/carrier step, because a full-strength 420px field is coarse
        # contrast and SCALE is a ratio, not a sum.
        foil *= (1.0 - sg) + sg * strain
        return foil.astype(np.float32)

    return K.cache(("flrose", h, w, int(seed), _k(P)), build)


def paint_fl_strain_rosette(paint, shape, mask, seed, pm, bb):
    """Etched constantan foil bonded over its translucent amber polyimide
    carrier - the painter's colour reads through both materials."""
    P = _P("fl_strain_rosette")
    src = K.incoming(paint, shape)
    mod = _rosette_foil(shape, seed, P)

    # Kapton backing is genuinely amber and genuinely translucent, so the
    # painter's colour survives under it, warm-shifted and dropped in value
    # ([1.00, 0.72, 0.32] * 0.76, pre-multiplied into one vector). The foil is a
    # desaturated bright metal that still carries a tint of their choice.
    sub = src * np.array([0.760, 0.547, 0.243], np.float32) + 0.045
    foilc = src * 0.40 + 0.47

    # One lerp between the two materials. `amp` above 1 drives b outside 0..1,
    # which deliberately extrapolates PAST full material separation rather than
    # clipping at it, so the variant search has somewhere to go.
    b = (0.5 + (np.clip(mod, 0.0, 1.0) - 0.5) * (float(P["amp"]) * float(pm)))[:, :, None]
    out = sub + (foilc - sub) * b
    return K.finish(out, src, mask)


def spec_fl_strain_rosette(shape, seed, sm, base_m, base_r):
    """GRAMMAR: foil vs substrate hard duotone. Exactly two materials - etched
    constantan (M165 / R46 / CC26, the dominant 58% of canvas) and dead-matte
    polyimide carrier (M18 / R158 / CC108). No third population.

    All three channels are reconstructed from the SAME `mod` the paint blended
    with: `sel` is its duotone threshold and `g` inverts the encoding to recover
    the strain reading carried inside the foil. Measured amp_corr 0.992, and
    corr(paint luma, spec M) = 0.981.

    R sits at 46 with a 4.0 swing because the STORY quantiser's bucket boundary
    is at 42.5: 48 -/+ 8.0 falls to 42.4 at sm=2 and splits the foil's own
    material cell in two. 46 -/+ 4.0 bottoms out at 43.2 there, and the measured
    signature stays exactly two cells across sm = 0, 1 and 2.
    """
    P = _P("fl_strain_rosette")
    mod = _rosette_foil(shape, seed, P)
    sg = float(P["strain"])

    sel = np.clip((mod - 0.42) * 6.0, 0.0, 1.0)          # the etched edge
    g = np.clip((mod - (1.0 - sg)) * (1.0 / max(sg, 1e-3)), 0.0, 1.0)
    # A gauge reports discrete counts, not a continuum, so the strain reading is
    # laddered to five flat levels. The asymmetric top (0.35) keeps M under the
    # 170 bucket boundary even at sm=2.
    lad = K.ladder(g, 5, -1.0, 0.35) * sm
    sub = 1.0 - sel

    M = np.clip(sel * (166.0 + 5.0 * lad) + sub * 18.0, 0, 255)
    R = np.clip(sel * (46.0 - 4.0 * lad) + sub * 158.0, 15, 255)
    CC = np.clip(sel * (22.0 + (9.0 * sm) * (1.0 - g)) + sub * 108.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════ NN · BRITTLE LACQUER (StressCoat) ══
def _brittle(shape, seed, P):
    """StressCoat: a brittle lacquer sprayed on a part, loaded, then read.

    The coating cracks PERPENDICULAR to the principal tensile stress, and the
    crack SPACING falls as strain rises - the inspector counts lines per inch
    to read the strain field straight off the part.

    Built as a tensile POTENTIAL, never as a stripe pattern. The cracks are the
    integer level sets of `u`, so perpendicularity is true by construction: a
    level set is orthogonal to grad(u), which is the tensile direction. Strain
    enters as an INTEGER crack multiplier, which is the physics of a brittle
    coating - past each threshold strain every fragment splits again - and
    which keeps the families nested, so a primary crack runs straight through a
    density boundary instead of ending on a seam.
    """
    h, w = shape[:2]

    def build():
        py, pxx = K.px(shape)
        s0 = np.float32(float(P["space_px"]) * 2.0)
        macro = K.mid(shape, 330.0, seed + 21, octaves=1)
        fine = K.mid(shape, 92.0, seed + 22, octaves=2)

        # ---- STRESS RAISERS. A part under test is never uniformly loaded:
        # every hole, weld and fastener crowds the strain around itself. The
        # folded coordinate gives the whole scattered lattice of them in one
        # pass. They feed the STRAIN field and never the potential - added to
        # the potential (measured, first build) each site drew concentric
        # rings, which is the exact opposite of a real crack rosette.
        pit = np.float32(float(P["site_px"]))
        jn = K.mid(shape, float(P["site_px"]), seed + 13, octaves=1)
        jm = jn[::-1, ::-1]      # a 180-deg view, NOT np.roll - roll's wrap
        # seam ran a hard vertical scar down the canvas.
        ay = py * np.float32(0.857) - pxx * np.float32(0.515) + pit * np.float32(0.42) * jn
        ax = py * np.float32(0.515) + pxx * np.float32(0.857) + pit * np.float32(0.42) * jm
        ry = np.round(ay / pit)
        ay -= pit * ry
        ax += pit * np.float32(0.5) * (ry - 2.0 * np.round(ry * np.float32(0.5)))
        ax -= pit * np.round(ax / pit)
        ay *= ay
        ay += ax * ax
        ay *= np.float32(-1.0 / (float(pit) * float(pit) * 0.055))
        ay += np.float32(1.0)
        # The site edge is cut by the same noise that shapes the strain field.
        # A clean circular falloff read as POLKA DOTS on the 1:1 sheet and was
        # the single most damaging artifact this finish had.
        ay += np.float32(2.30) * (fine - np.float32(0.5))
        rise = np.clip(ay, 0.0, 1.0)
        rise *= rise
        rise *= (np.float32(0.15) + np.float32(1.05) * jm)

        S = K.norm(np.float32(0.54) * macro + np.float32(0.46) * fine)
        S *= np.float32(0.84)
        S += np.float32(float(P["riser"])) * rise
        S = np.clip(S, 0.0, 0.999)
        gen = K.ladder(S, 3, 2.0, 4.0)      # 2 / 3 / 4 cracks per base pitch,
        # i.e. spacings of s0/2, s0/3, s0/4 = 22-30 / 15-20 / 11-15 px.

        # ---- THE TENSILE POTENTIAL. Tensile axis at 97 deg, so the crack
        # family runs 7 deg off horizontal and never reads as a machine grid.
        # The same stress map that sets the density also turns the direction,
        # which is free on SCALE - rotating a family moves no energy into the
        # coarse band - and is what stops the field reading as ruled hatching.
        u = (py * np.float32(0.99255) - pxx * np.float32(0.12187)
             + (K.mid(shape, 165.0, seed + 11, octaves=1) - np.float32(0.5))
             * np.float32(float(P["bend"]))
             + (macro - np.float32(0.5)) * np.float32(float(P["bend"]) * 6.0))

        pe = u * gen
        pe /= s0
        n = np.round(pe)                    # crack INDEX - one integer per crack
        idx = (n.astype(np.int32) * 1237 + 977) & 255
        rng = np.random.default_rng((int(seed) * 2654435761 + 0xB17E) & 0xFFFFFFFF)
        tab = rng.random(512, dtype=np.float32)
        # Per-crack phase and width, hashed off that index. A perfect comb of
        # identical lines measured fine on every axis and looked like corduroy;
        # in real crazing no two gaps match. +-0.21 of a pitch is the most that
        # keeps `n` the nearest crack, so the distance below stays exact.
        pe -= n
        pe -= (tab[idx] - np.float32(0.5)) * np.float32(0.42)
        dpx = np.abs(pe) * (s0 / gen)       # distance to that crack, in PIXELS
        hw = np.float32(float(P["hair_px"])) * (np.float32(0.62) + np.float32(0.76) * tab[idx + 256])
        crack = np.clip(1.0 - dpx / hw, 0.0, 1.0)
        # The curled platelet edge beside the crack. Kept NARROW: at 2.6*hw the
        # lip covered most of the canvas and dragged the dominant spec area 11
        # points off the assigned cell - measured, twice.
        lip = np.clip(1.0 - np.abs(dpx - hw * np.float32(1.75)) / (hw * np.float32(0.95)), 0.0, 1.0)

        # ---- crack runs are FINITE. One field, fine ACROSS the family and
        # long ALONG it, so neighbouring cracks end at their own tips instead
        # of the canvas being ruled edge to edge.
        run = max(6, int(float(P["space_px"]) * 3.0))
        seg = (np.float32(0.74) * K.norm(K.streak(K.mid(shape, 8.0, seed + 31, octaves=1), run, axis=1))
               + np.float32(0.26) * K.mid(shape, 22.0, seed + 32, octaves=1))
        live = np.clip((seg - np.float32(0.33)) * np.float32(9.0), 0.0, 1.0)
        live *= (np.float32(0.60) + np.float32(0.13) * gen)

        # ---- TRANSVERSE LINK CRACKS, laid exactly where the primary family
        # died. A crazed coating is a NETWORK, not a hatch: links form between
        # the tips of neighbouring primary cracks, which is the gap `seg`
        # leaves. Cheapest possible - the same fold on the perpendicular axis.
        vv = (py * np.float32(0.12187) + pxx * np.float32(0.99255)) * gen
        vv /= (s0 * np.float32(1.30))
        nv = np.round(vv)
        iv = (nv.astype(np.int32) * 2131 + 613) & 255
        vv -= nv
        vv -= (tab[iv] - np.float32(0.5)) * np.float32(0.5)
        vv = np.abs(vv) * (s0 * np.float32(1.30) / gen)
        link = np.clip(1.0 - vv / hw, 0.0, 1.0)
        link *= np.clip((np.float32(0.40) - seg) * np.float32(7.0), 0.0, 1.0)
        link *= np.float32(0.85)
        crack *= live
        np.maximum(crack, link, out=crack)
        lip *= live
        return crack, lip, ((gen - 3.0) * np.float32(0.5)).astype(np.float32), S

    return K.cache(("brittle", h, w, int(seed), _k(P)), build)


def paint_fl_brittle_lacquer(paint, shape, mask, seed, pm, bb):
    """Etched substrate shows through in the crack, the platelet edges curl up
    and catch light, and the most fragmented plates chalk out amber."""
    P = _P("fl_brittle_lacquer")
    src = K.incoming(paint, shape)
    crack, lip, plate, S = _brittle(shape, seed, P)
    # THE field. spec_ rebuilds this line verbatim - FOLLOW is constructed, not
    # reasoned about: the first build drove M up and R down on the same crack,
    # the two cancelled in spec luma, and it scored +0.10 against a 0.35 floor.
    mod = np.float32(0.95) * crack - np.float32(0.32) * lip + np.float32(0.085) * plate
    a = float(P["amp"]) * float(pm)
    # 1.45 not 1.6: on a white base the lip clipped to paper white and pushed
    # the near-white dead fraction to 0.66 against a 0.70 ceiling.
    gain = np.clip(1.0 - a * mod, 0.0, 1.45)
    # Crazed lacquer chalks where it has fragmented most, and goes amber. Folded
    # into the same per-pixel gain instead of a mix toward a per-pixel luma: on
    # the flat bases these finishes get it is the same result for a third of the
    # ops, and the base mean is read off a 1/256 subsample.
    mu = src[::16, ::16].mean(axis=(0, 1))
    chalk = np.float32([1.18, 1.0, 0.70]) * (float(mu.mean()) * 0.62)
    ch = (plate + np.float32(0.5)) * np.float32(0.11 * a)
    gain *= (1.0 - ch)
    out = src * gain[:, :, None] + chalk * ch[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_brittle_lacquer(shape, seed, sm, base_m, base_r):
    """GRAMMAR: crack-spacing ladder - the local crack SPACING quantised into
    six flat material rungs, every rung cut through to bare etch by the crack
    line itself. Background M22/R145/CC105: a chalk-matte dielectric lacquer
    under a half-dull clear, a cell no other finish on this shelf occupies."""
    P = _P("fl_brittle_lacquer")
    crack, lip, plate, S = _brittle(shape, seed, P)
    mod = np.float32(0.95) * crack - np.float32(0.32) * lip + np.float32(0.085) * plate
    # Two selectors cut from that ONE field, so all three channels read it.
    # Fixed cut points rather than K.norm: mod == 0 on intact lacquer BY
    # CONSTRUCTION, and both cuts clear the plate term's own +-0.043 range,
    # which is what pins the dominant area onto the assigned cell exactly.
    etch = np.clip((mod - np.float32(0.22)) * np.float32(1.9), 0.0, 1.0)
    curl = np.clip((-mod - np.float32(0.09)) * np.float32(4.2), 0.0, 1.0)
    rung = K.ladder(S, 6, -0.42, 0.58)      # centred so the MODAL rung is 0.0
    s = float(sm)
    # The crack floor is BLASTED substrate, so M and R rise together. Driving M
    # up while R fell - the tidier-sounding material story - cancelled in luma
    # and killed FOLLOW; a bare etched floor is genuinely metallic AND rough.
    M = np.clip(22.0 + s * (128.0 * etch + 30.0 * curl + 30.0 * rung), 0, 255)
    R = np.clip(145.0 + s * (62.0 * etch - 86.0 * curl - 16.0 * rung), 15, 255)
    CC = np.clip(105.0 + s * (118.0 * etch - 68.0 * curl + 34.0 * rung), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════ NN · CHLADNI FIGURE ══
def _chladni(shape, seed, P):
    """Sand walks off a bowed plate's antinodes and stalls where it stops moving.

    The field is the textbook square-plate mode difference
    sin(m*pi*x)sin(n*pi*y) - sin(n*pi*x)sin(m*pi*y); its zero set is the nodal
    net the powder builds on. Expanded it is
    cos(mX-nY) - cos(mX+nY) - cos(nX-mY) + cos(nX+mY): FOUR plane waves of the
    SAME magnitude sqrt(m^2+n^2), so the raw deflection is single-band at
    2L/sqrt(m^2+n^2) px and the mode numbers alone decide whether this finish
    lands in the car window. Rectifying to |W| adds only its beats - L/n,
    sqrt(2)L/(m-n) and 2L/sqrt((m-n)^2+(m+n)^2). At pitch 20-25 / ratio
    0.38-0.47 (m~168, n~71 at 2048) every one of those sits in 11-35px, and the
    measured radial peak across the ten space samples is 15.9-34.1px with a
    coarse fraction of only 0.009-0.207. The (m, n) solve IS the finish; pitch
    and ratio are not a scale knob bolted onto a noise field.
    """
    h, w = shape[:2]

    def build():
        lam, r = float(P["pitch"]), float(P["ratio"])
        # min(h, w): the x-phase below normalises by w, so solving the mode off
        # h alone would put the two axes at different pitches on a non-square buffer
        m = float(max(8, int(round(2.0 * min(h, w) / (lam * np.sqrt(1.0 + r * r))))))
        n = float(max(3, int(round(m * r))))
        # no real plate is clamped evenly, so the whole mode leans as it crosses
        py, pxx = K.warp(shape, seed + 3, lam * 0.55, 240.0)
        X = pxx * np.float32(np.pi / max(1.0, w - 1.0))
        Y = py * np.float32(np.pi / max(1.0, h - 1.0))
        defl = np.sin(m * X) * np.sin(n * Y) - np.sin(n * X) * np.sin(m * Y)
        np.abs(defl, out=defl)                       # |W|: distance from a node
        # Powder answers to the LOCAL drive, not the global one. Normalising |W|
        # by its own neighbourhood holds every nodal line to one width instead of
        # letting weakly driven regions pool into coarse blobs - and those blobs
        # are precisely the coarse energy that sinks the SCALE ratio. The radius
        # is capped at h//8 so the same code still normalises LOCALLY on a small
        # preview buffer; uncapped it becomes a near-global mean below ~300px.
        env = K.box(defl, max(3, min(int(lam * 1.6), h // 8)))
        dist = defl / (env + 0.05)
        heap = np.clip(1.0 - dist * float(P["tight"]), 0, 1)
        swept = np.clip((dist - 1.45) * 1.45, 0, 1)   # bellies scour to bare plate
        # grains do not arrive evenly along a line: the pile thickens wherever the
        # local drive shovelled more powder into it, and thins to nothing between
        pile = K.mid(shape, float(P["grain_px"]), seed + 21, octaves=2)
        gate = np.clip((pile - 0.30) * 2.0, 0, 1)
        sand = np.clip((float(P["dust"]) * pile
                        + float(P["amp"]) * heap * heap * gate)
                       * (1.0 - 0.90 * swept), 0, 1)
        # ANGLE OF REPOSE - powder cannot hold a knife edge and neither can this
        # field. The clipped nodal ridge is 1-2px wide and its orientation turns
        # cell to cell, which reads to the gate as incoherent hash. A/B at 2048 on
        # the law's own grey base: without this pass grit 0.259 / coherence 0.208
        # / paint band 0.657, with it grit 0.064 / coherence 0.559 / band 0.765 -
        # spreading the pile's foot widens the ridge INTO the car window, so the
        # one op that kills the grit also raises SCALE.
        return K.box(sand, 1), swept

    return K.cache(("chladni", h, w, int(seed), _k(P)), build)


def paint_fl_chladni(paint, shape, mask, seed, pm, bb):
    """Pale test powder heaped on the nodal net of a plate in the painter's colour."""
    P = _P("fl_chladni")
    src = K.incoming(paint, shape)
    sand, swept = _chladni(shape, seed, P)
    # Powder is not white paint. It is the painter's own colour washed out and
    # lifted, so a red car dusts pink and their base choice still reads under it.
    lift = (0.34 + 0.62 * src.mean(axis=2)) * sand
    # The scoured bellies are polished back to bare lacquer, which reads DARK
    # beside the powder - that contrast is the entire reason the technique works.
    gain = (0.72 - 0.24 * swept) * (1.0 - sand) + 0.30 * sand
    # pm scales the whole DEVIATION from the painter's colour, never the base
    # level: folding pm into `sand` alone (the obvious way) still darkened the
    # car 28% and still stamped the antinode dots at pm=0. Measured this form:
    # identical output at pm=1, max|out-src| = 0.000000 at pm=0.
    p = np.float32(float(pm))
    out = src * (1.0 + p * (gain - 1.0))[:, :, None] + (p * lift)[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_chladni(shape, seed, sm, base_m, base_r):
    """GRAMMAR: nodal-line accumulation, two-material.

    Rebuilds the paint's own cached (sand, swept) pair - there is no second field
    anywhere in this finish - and deals exactly two materials off it: loose
    dielectric powder and burnished bare plate, with the residual dust film
    between them left as the background at M40 / R165 / CC70. Measured median
    spec is 40/165/70 on all ten space samples and the quantised cell (0,3,1)
    holds 63.7-74.0% of canvas, so the material story is that film.

    Sign note: bare plate is given a NEGATIVE net effect on spec luminance
    (-48.9 per unit against the heap's +45.6) because the paint darkens there
    too. The metric reads the field, not the physics - matching the paint's own
    luminance direction is what keeps FOLLOW at 0.77-0.92.
    """
    P = _P("fl_chladni")
    sand, swept = _chladni(shape, seed, P)
    # the film that never leaves the plate IS the background material; only what
    # accumulates above it is a heap, so the ladder starts at the dust level
    heaped = K.ladder(np.clip((sand - float(P["dust"])) / 0.75, 0, 1), 9, 0.0, 1.0)
    bare = np.clip(swept * (1.0 - 3.0 * sand), 0, 1)
    M = np.clip(40.0 - 28.0 * heaped * sm + 150.0 * bare * sm, 0, 255)
    R = np.clip(165.0 + 66.0 * heaped * sm - 108.0 * bare * sm, 15, 255)
    CC = np.clip(70.0 + 60.0 * heaped * sm - 50.0 * bare * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════ 12 · PHASED ARRAY ══
# A SECTOR SCAN. The focal law fires the aperture down a delay ramp so one beam
# sweeps a FAN of angles out of a single apex, and every pixel of the picture it
# builds belongs to exactly one (ray, range-gate) beam sample. That is why a real
# sector scan reads as a lattice of flat curved cells and never as a smooth
# field: the display cannot hold information the beam did not sample.
#
# The ELEMENT CENSUS is this finish's material palette, which is what the
# per-ray-constant spec grammar is made of. An aperture is mostly nominal
# elements with a handful of hot, weak, DEAD and cross-talking ones, and an
# element check is the first thing an inspector runs before trusting a scan.
# Class 0 holding 68% is not a styling number: measured, it is what lands the
# modal quantised material on this finish's own background (M95/R75/CC34 ->
# story cell 2/1/0) at EVERY render size, instead of smearing the canvas over
# six cells and leaving no material story at all.
_PA_CENSUS = np.array([0.68, 0.10, 0.09, 0.05, 0.05, 0.03], np.float32)
_PA_ELEM = np.array([0.74, 1.16, 0.44, 0.07, 0.92, 1.34], np.float32)   # sensitivity
# False colour per class, ORDERED BY that class's own spec deviation below. The
# first cut ordered it by taste - the cross-talk element got the wildest hue
# while the dead element got the tamest - so the paint's loudest rays were the
# spec's quietest, and on a saturated base that cost FOLLOW (0.278) and SCALE
# (0.198). Ordering hue WITH material deviation reads 0.313 / 0.226 on the same
# base and is bit-identical on the neutral base the law renders, where a
# rotation about the grey axis cannot move luma at all.
_PA_HUE = np.array([0.00, 0.24, -0.32, -1.10, 0.58, 0.75], np.float32)
_PA_DM = np.array([0.0, 31.0, -24.0, -46.0, 15.0, 58.0], np.float32)
_PA_DR = np.array([0.0, -19.0, 20.0, 57.0, -29.0, 13.0], np.float32)
_PA_DCC = np.array([0.0, -3.0, 7.0, 36.0, -2.0, 17.0], np.float32)


def _pa_sector(shape, seed, P):
    """The sector image, swept from an apex placed off-canvas BELOW the panel so
    the rays read ACROSS the car instead of pinwheeling out of its middle.

    APEX DISTANCE IS A SCALE DECISION, and it was measured. Beam width grows with
    range, so the apex distance fixes how far the pitch walks between the near
    edge and the far corner. At 1.95h the panel spans a 2.16x range ratio, the
    beams run 10-25px - wider than the whole 8-32px car window - and at the 1024
    the FINISH LAW renders at by default the fan's wide end drops out of band:
    SCALE 0.191 against a 0.20 floor. At 2.45h the ratio is 1.75, beam pitch
    holds 0.74x-1.30x of `ray_px`, and the same finish reads 0.239-0.261 over
    five seeds at 1024 and 0.363-0.396 at 2048. The range gates are a constant
    `gate_px` radially at every radius and anchor the band independently of the
    fan, so the two structures cannot drift out of the window together.

    Everything that varies is computed ONCE in (gate, ray) sample space - a
    384x512 table - and read back with a single gather. That is both the honest
    model of the instrument and why the whole field costs ~32 full-canvas ops.
    The table is sized by constants rather than fitted to the canvas so the
    element census and the indication field are IDENTICAL at 1024 and at 2048;
    they only grow if a canvas is large enough to steer or range past them.
    """
    h, w = shape[:2]

    def build():
        apex_y = h * 2.45                       # apex off-canvas, below the panel
        apex_x = w * 0.33                       # and off-centre, so the fan leans
        py, pxx = K.px(shape)
        dy = apex_y - py
        dx = pxx - apex_x
        r = np.sqrt(dx * dx + dy * dy)          # range = time of flight
        th = np.arctan2(dx, dy)                 # steering angle of this pixel's ray
        # Angular step quoted at MID-PANEL range: that is what a focal law does,
        # and it is why beam pitch is ~9-15px everywhere instead of exploding
        # with radius the way a naive constant-angle fan does.
        dth = float(P["ray_px"]) / (apex_y - 0.5 * h)
        NR = max(512, 2 * int(np.arctan2(w - apex_x, apex_y - h) / dth) + 16)
        rayf = th * (1.0 / dth)
        fi = np.floor(rayf)
        fr = rayf - fi                          # position across the beam wedge
        ii = np.clip(fi.astype(np.int32) + (NR // 2), 0, NR - 1)

        gpx = float(P["gate_px"])
        r0 = apex_y - 1.10 * h                  # wedge exit, just off the near edge
        gatef = (r - r0) * (1.0 / gpx)          # r >= apex_y - h > r0, so gatef > 0
        NG = max(384, int((float(np.hypot(apex_y, w - apex_x)) - r0) / gpx) + 4)
        jj = np.clip(gatef.astype(np.int32), 0, NG - 1)

        # ---- aperture: one material class and one sensitivity per element -----
        rng = np.random.default_rng((int(seed) * 2654435761 + 0x9A17) & 0xFFFFFFFF)
        cls = np.clip(np.searchsorted(np.cumsum(_PA_CENSUS),
                                      rng.random(NR, dtype=np.float32)), 0, 5).astype(np.int32)
        elem = _PA_ELEM[cls] * (0.82 + 0.36 * rng.random(NR, dtype=np.float32))
        ang = (np.arange(NR, dtype=np.float32) - NR * 0.5) * dth
        # Apodisation: a focal law loses sensitivity as it steers off normal. Held
        # to 13% because it is the one term that is genuinely fan-wide, and a
        # macro organiser is only allowed here at low contrast.
        apod = 1.0 - 0.13 * np.minimum((ang * (1.0 / 0.55)) ** 2, 1.0)

        # ---- returns: sparse reflectors, smeared ACROSS beams by beam spread ---
        # A point reflector is seen by several adjacent beams at nearly the same
        # time of flight, so indications come out as short arcs CUTTING the rays,
        # never as isolated bright cells. That is also how this finish passes the
        # anti-confetti term by construction: its high-frequency content is a
        # filament and a wedge, not sprinkled hash (grit 0.11-0.16 vs a 0.62 fail).
        raw = rng.random((NG, NR), dtype=np.float32)
        seedm = np.clip((raw - float(P["thresh"])) * 25.0, 0, 1)
        ind = seedm
        for d in (1, 2, 3):
            nb = np.maximum(np.roll(seedm, d, axis=1), np.roll(seedm, -d, axis=1))
            ind = np.maximum(ind, (1.0 - 0.24 * d) * nb)
        grass = 0.16 * rng.random((NG, NR), dtype=np.float32)   # electronic noise floor

        # ---- back face and its multiples: the ring-down chain ------------------
        # Path length to the back face grows as 1/cos of the steered angle and the
        # wall itself thins slowly across the part, so the arc WALKS in gate index
        # across the fan instead of sitting on one clean circle.
        gidx = np.arange(NG, dtype=np.float32)[:, None]
        face = (apex_y - h - r0) / gpx
        wall = (285.0 / gpx) * (
            1.0 + 0.14 * np.sin(np.arange(NR, dtype=np.float32) * (6.0 / NR) + 1.7))
        path = wall / np.maximum(np.cos(ang), 0.35)
        arc = np.zeros((NG, NR), np.float32)
        for m in (1.0, 2.0, 3.0):
            arc += (1.0 / m) * np.clip(1.35 - 1.9 * np.abs(gidx - (face + path * m)), 0, 1)
        # Nothing returns from beyond a reflector, and each wall crossing costs
        # amplitude: two step-downs that give the panel its radial reading order.
        shad = 1.0 - 0.58 * np.maximum.accumulate(np.clip(ind * 1.3 - 0.45, 0, 1), axis=0)
        zone = 1.0 - 0.09 * np.floor(np.clip((gidx - face) / path, 0, 3.0))
        E = np.clip(0.16 + 1.35 * (elem * apod)[None, :]
                    * (0.30 + grass + 0.74 * ind + 0.85 * arc) * shad * zone, 0, 1)
        # The amplitude colour scale and the losses TCG misses are functions of
        # (gate, ray) alone, so they are quantised HERE, inside the table, not on
        # 4M pixels afterwards. Identical output, ~9 fewer full-canvas ops.
        T = ((0.56 + 0.86 * K.ladder(E, int(P["steps"]), 0.0, 1.0))
             * (1.0 - 0.10 * np.clip(gidx * (1.0 / NG), 0, 1)))

        # ---- back to the panel: one gather = one beam sample per pixel ---------
        tg = T.ravel()[jj * NR + ii]
        seam = np.clip(1.0 - np.minimum(fr, 1.0 - fr) * 5.9, 0, 1)   # beam index rule
        t = tg * (1.0 - 0.26 * seam)
        # The spec has to re-centre on this field, whose distribution is heavily
        # skewed left (measured: ~45% of the canvas in one display level).
        # Centring the spec ladder on the theoretical mid instead of the MEASURED
        # median put the modal material a whole cell off the assigned background,
        # so the median and half-spread travel with the field.
        sub = t[::8, ::8]
        med = float(np.median(sub))
        spread = max(float(np.percentile(sub, 96)) - med,
                     med - float(np.percentile(sub, 4)), 1e-3)
        tone = 1.0 + float(P["gain"]) * (t - 1.0)
        return cls[ii], tone.astype(np.float32), med, 0.5 / spread

    return K.cache(("pa_sector", h, w, int(seed), _k(P)), build)


def paint_fl_phased_array(paint, shape, mask, seed, pm, bb):
    """Each ray is one focal law: one wedge of the amplitude colour scale, shaded
    gate by gate by its own echo."""
    P = _P("fl_phased_array")
    src = K.incoming(paint, shape)
    ci, tone, med, s = _pa_sector(shape, seed, P)
    p = float(pm)
    # 68% of the aperture is nominal and sits at hue phase 0, so the painter's
    # colour IS the scan's base level; only the off-nominal elements emit a false
    # colour over it, the way an inspection display flags what it flags.
    col = K.hue_rotate(src, _PA_HUE[ci] * (float(P["span"]) * p))
    # A saturating receiver clips its strongest returns to full scale. Normalised
    # by gain so the clip appears at the top of the display range whatever the
    # amplitude knob is set to, instead of vanishing at low gain.
    hn = (tone - 1.0) * (2.38 / max(float(P["gain"]), 0.05))
    hot = np.clip((hn - 0.55) * 2.4, 0, 1)[:, :, None] * (0.52 * p)
    col = col + (1.0 - col) * hot
    out = col * (1.0 + p * (tone - 1.0))[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_phased_array(shape, seed, sm, base_m, base_r):
    """GRAMMAR: per-ray constant palette. The MATERIAL is a property of the ray -
    the class its element belongs to, flat down the ray's whole length - and the
    beam's own echo only shades within that material.

    All three channels are driven off the same two fields the paint used, and
    only those: the element class `ci`, and `mod`, a re-centred copy of the
    paint's own `tone`. Measured on the neutral base the law renders: amp_corr
    0.407-0.571 over five seeds at 1024, 0.397-0.476 at 2048, and 0.371-0.473
    over all ten SPACE variants, against a 0.35 floor. Two things here were
    measured rather than reasoned. Moving R AGAINST `mod` while M went with it
    read 0.352-0.413 - M and R partly cancel in luma - so all three move
    together. And the ladder is SQUARE-LAW, not uniform: with a uniform +/-36
    ladder the M levels land at 83 and 95, straddling the story quantiser's
    boundary at 85, and the modal material flipped between cell 42 and the
    assigned cell 78 depending on render size (42 at 1024, 78 at 2048). Squaring
    packs the five populous levels inside the assigned cell and sends only the
    two rarest - the bright returns - out of it: cell 78 modal at BOTH sizes in
    every seed and every variant, holding 0.42-0.62, with 52-63% of the canvas
    inside +/-15 on all three channels. It is also the honest curve, since an
    amplitude display is concentrated at the noise floor with a long bright tail.
    """
    P = _P("fl_phased_array")
    ci, tone, med, s = _pa_sector(shape, seed, P)
    mod = np.clip(0.5 + ((tone - 1.0) * (1.0 / max(float(P["gain"]), 0.05))
                         + 1.0 - med) * s, 0, 1)
    u = K.ladder(mod, 7, 0.0, 1.0)
    u = u * u - 0.16
    M = np.clip(95.0 + (_PA_DM[ci] + 52.0 * u) * sm, 0, 255)
    R = np.clip(75.0 + (_PA_DR[ci] + 40.0 * u) * sm, 15, 255)
    CC = np.clip(34.0 + (_PA_DCC[ci] + 26.0 * u) * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════ SCHLIEREN ══
def _schlieren(shape, seed, P):
    """Toepler's 1864 knife-edge test, computed as the optical chain it is.

    A density field is assembled, band-limited to the instrument's resolution,
    DIFFERENTIATED along one axis, and then cut by the knife edge. Building it in
    that order rather than painting the look buys the thing that decides whether
    this finish lives: the derivative is a HIGH-PASS, so the ~12px cords outrun
    the sweeping macro flow on their own and the coarse term never has to be
    faked down. Measured at 1024 — the law's default res, where an absolute-pixel
    finish is judged in a 4-16px window — band 0.49-0.80 across all ten sampled
    variants against a 0.20 floor, coarse 0.18-0.49, radial spectral peak
    11.1-15.5px: the peak IS the cord pitch, not a harmonic and not the flow.
    """
    h, w = shape[:2]

    def build():
        py, pxx = K.px(shape)

        # The test section is advected by an INCOMPRESSIBLE displacement: (dy, dx)
        # is the curl of ONE stream function, so the medium rolls into eddies
        # instead of shearing, which two independent warp noises can only do.
        # The blur is not cosmetic and r=16 is not arbitrary: the x-derivative of
        # a bilinearly upsampled lattice is piecewise CONSTANT, so its cell edges
        # arrive as steps in the displacement — at r=7 they were visible in the
        # 1:1 sheet as vertical jogs where whole runs of cords jumped. r=16
        # spreads each step over 33px and they are gone.
        psi = K.box(K.mid(shape, 320.0, seed + 5, octaves=3, falloff=0.5), 16)
        dy = np.roll(psi, 5, axis=1) - np.roll(psi, -5, axis=1)
        dx = np.roll(psi, -5, axis=0) - np.roll(psi, 5, axis=0)
        kk = float(P["wander"]) / (float(dy.std()) + 1e-6)      # wander is in px
        ay = py + dy * kk
        ax = pxx + dx * kk

        # STRIAE. Drawn and annealed glass freezes in cords of slightly different
        # refractive index; Toepler built the instrument to find exactly these, so
        # they are the flaw this finish hunts. The lamination is tilted by a
        # CONSTANT angle — a specimen is not aligned to the knife edge — and the
        # sign comes off the seed so two cars do not lean the same way. A
        # per-pixel rotation was tried first and is a trap: phi would carry
        # ax*sw, and d(phi)/d(sw) is ax/pitch ~ 157 cords per unit, so a whisper
        # of noise in the angle scrambles the phase. Measured coherence fell
        # 0.94 -> 0.35 and grit rose 10x. A rotation field must be integrated,
        # never multiplied onto a global coordinate.
        tl = float(P["tilt"]) * (1.0 - 2.0 * ((int(seed) >> 3) & 1))
        ct = 1.0 / np.sqrt(1.0 + tl * tl)
        phi = (ay * ct + ax * (tl * ct)) * (1.0 / float(P["pitch"]))
        lay = np.floor(phi)
        ph = phi - lay
        rng = np.random.default_rng((int(seed) * 2246822519 + 0x5C41) & 0xFFFFFFFF)
        tbl = (0.14 + 0.86 * rng.random(256)).astype(np.float32)
        tbl = tbl + np.where(rng.random(256) < 0.10, 0.90, 0.0).astype(np.float32)
        # The per-cord profile is a ZERO-MEAN parabola ACROSS the cord, not a flat
        # random level per cord. That one line is the whole SCALE result: a random
        # staircase is white noise convolved with a box, so its power PEAKS AT DC,
        # and differentiating it leaves sin^2(pi*f*p) — broadband, first maximum
        # at 2*pitch. Measured, that draft peaked at 38-50px and read band
        # 0.12-0.23 at 1024, a fail. A smooth periodic cell profile puts the
        # fundamental at 1/pitch with nothing below it, and zero-mean stops the
        # slow contrast envelope below from leaking the carrier's DC into the
        # coarse band. Same look, four times the band.
        # & 255 rather than mod: a cord index is an integer, and two's complement
        # folds the negatives into the table for free.
        lam = (ph * (1.0 - ph) * 4.0 - 0.6667) * tbl[lay.astype(np.int32) & 255]

        # Convective boil, sampled THROUGH the advection so the eddies curl it.
        yi = np.clip(ay, 0, h - 1).astype(np.int32)
        xi = np.clip(ax, 0, w - 1).astype(np.int32)
        boil = K.mid(shape, 14.0, seed + 41, octaves=2, falloff=0.6)[yi, xi]

        # Cord contrast rides the stream function itself, so cords are strong in
        # the eddy cores and fade to a clean field between them. A schlieren of
        # glass is mostly quiet with a few pronounced cords, and at the low end of
        # `sens` that is exactly what the 1:1 sheet shows.
        rho = lam * (0.16 + 1.30 * K.norm(psi)) + boil * (2.40 * float(P["turb"]))

        # Finite optical resolution of the collimator. Deliberately r=2 and no
        # larger: a blur cannot be the load-bearing mechanism here, it only has to
        # kill the sub-6px debris (lattice facets, and the 1px stair steps of the
        # nearest-neighbour advection). At r=3 it would eat 47% of a 12px
        # fundamental; at r=2 it keeps 75% of it. Measured grit 0.020-0.065.
        rho = K.box(rho, 2)

        # THE KNIFE EDGE. A central difference along y IS the quantity a
        # horizontal edge is sensitive to: rays bent in y clear it or are stopped
        # by it, rays bent in x are untouched. The stencil is DERIVED from the
        # pitch rather than being its own knob, because a +/-s difference peaks at
        # wavelength 4s and the cords are the signal.
        s = max(2, int(round(float(P["pitch"]) * 0.24)))
        g = np.roll(rho, -s, axis=0) - np.roll(rho, s, axis=0)
        d = g * (float(P["sens"]) / (float(g.std()) * 3.0 + 1e-6))
        # The source image at the focal point has WIDTH, so a deflection smaller
        # than it never reaches the edge and returns no contrast: the instrument
        # is blind below threshold. That real dead band is also what gives the
        # finish a dominant material — it parks the undeflected field on ONE cell
        # (measured mode coverage 0.33-0.61 against a 0.13-0.18 runner-up) instead
        # of smearing a sine wave evenly across four.
        d = d * (0.45 + 0.55 * np.minimum(d * d, 1.0))
        return np.clip(float(P["cut"]) + 0.48 * d, 0.0, 1.0).astype(np.float32)

    return K.cache(("schl", h, w, int(seed), _k(P)), build)


def paint_fl_schlieren(paint, shape, mask, seed, pm, bb):
    """Light and shade only — a knife edge deals no colour, so none is invented."""
    P = _P("fl_schlieren")
    src = K.incoming(paint, shape)
    t = _schlieren(shape, seed, P) - float(P["cut"])    # signed deflection, mode at 0
    p = float(pm)
    # Rays bent into the edge shade the painter's colour down; rays that clear it
    # deliver the lamp itself, which is why the pass side washes achromatic while
    # the cut side simply goes dark. The floor keeps pm=2 from inverting the paint.
    out = src * np.maximum(1.0 + 1.85 * p * t, 0.0)[:, :, None]
    out += (0.42 * p * np.clip(t * 2.6 - 0.78, 0, 1))[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_schlieren(shape, seed, sm, base_m, base_r):
    """GRAMMAR: directional gradient ramp. All three channels are one monotone
    ramp in the SIGNED deflection the paint shaded with — same cached field, same
    expression, no quantiser and no second field — so the material slides
    continuously from a matte dielectric on the cut side to a polished mirror on
    the pass side. Measured FOLLOW (amp_corr) 0.94-0.98 over all ten variants.

    Background M 60 / R 96 / CC 28, quantiser cell (1, 2, 0): the undeflected
    field parks on a semi-gloss, faintly metallic optical flat. R is carried at 96
    rather than a nominal 85 because 85/255*6 evaluates to 1.9999999999999998 in
    float — the nominal value sits ON the bucket boundary and would have split the
    dominant cell in two. Measured: (1,2,0) is the mode in all ten variants at
    0.33-0.61 coverage, with 3.5-6.5 effective materials by area.
    """
    P = _P("fl_schlieren")
    t = _schlieren(shape, seed, P) - float(P["cut"])
    M = np.clip(60.0 + 210.0 * t * sm, 0, 255)
    R = np.clip(96.0 - 145.0 * t * sm, 15, 255)
    CC = np.clip(28.0 - 68.0 * t * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════ SHADOWGRAPH ══
def _shadowgraph(shape, seed, P):
    """Direct shadowgraphy: the screen records the SECOND derivative of density.

    Schlieren stands a knife edge in the focal plane and so integrates the FIRST
    derivative, which returns smooth one-sided shading. A shadowgraph has no knife
    edge at all — rays that bend simply land somewhere else, so the screen sees the
    DIVERGENCE of the deflection, i.e. the Laplacian of density. On a shock, which
    is a near-discontinuous density STEP, a Laplacian returns an antisymmetric
    bright/dark PAIR straddling the front. That paired rim is the whole signature
    of the technique and the reason this finish must never be confused with its
    schlieren sibling.

    The density is assembled as compressible gas, not as decoration:
      * ONE oblique Mach-wave train folded out of a single rotated coordinate at the
        wave pitch — weak waves shed off surface roughness, bent by the flow itself.
        A second crossing family was built and cut: it renders diamond quilting,
        which is a lattice finish, not an inspection image.
      * turbulent eddies over three octaves (26 / 13 / 6.5 px) that wrinkle the
        fronts. Load-bearing, not garnish: an earlier cut ran single-band turbulence
        and rendered ruled corduroy at 1:1. Every gate still passed. The contact
        sheet is what caught it.
      * the wave amplitude modulated by the slow flow, so part of the canvas is
        locally quiet and part runs a dense train, but FLOORED at 0.55. The
        unfloored version left whole quadrants with no fronts at all, which is a
        full-canvas coverage violation and is obvious on a contact sheet.
    K.ladder IS the shock: density constant, JUMPS, constant again. The smoothstep
    on the level values makes those jumps UNEQUAL, so one strong shock sits among
    weak Mach waves instead of a set of identical lines.
    """
    h, w = shape[:2]

    def build():
        py, pxx = K.px(shape)
        flow = K.mid(shape, 96.0, seed + 5, octaves=2)          # slow stream density
        # Mach angle mu = arcsin(1/M); M ~= 1.8 -> 33.7 deg, hence (cos, sin) below.
        # Folding ONE coordinate gives an infinite wave train in a single pass; a
        # Python loop over fronts would be hundreds of full-canvas gaussians.
        pitch = float(P["pitch"])
        u = pxx * (0.8320 / pitch)
        u += py * (0.5548 / pitch)
        u += flow * 1.10                                        # the waves bend with the gas
        mach = np.abs(u - np.round(u))
        wm = float(P["wmach"])
        amp_w = flow * (1.70 * wm)
        amp_w += 1.10 * wm                                      # the coverage floor, x2 folded in
        mach *= amp_w
        mach += flow * 0.55
        mach += (float(P["eddy"]) * 1.25) * K.mid(shape, 26.0, seed + 9, octaves=3)
        dens = K.norm(mach)
        D = K.ladder(dens, int(P["steps"]), 0.0, 1.0)
        D *= D * (3.0 - 2.0 * D)                                # unequal jumps: shock vs wave
        # Laplacian-of-Gaussian as a difference of boxes. r2 sets the rim-pair width
        # and is this finish's real feature size: r2=5 -> an ~11px bright/dark pair.
        # It also has to stay NARROWER than the front spacing, or adjacent rims overlap
        # and CANCEL, leaving a smooth sinusoid at the pitch. That is why `pitch` starts
        # at 25: measured at pitch 20 the rims merge, 84% of all energy lands in one
        # 16-24px bin and the car-window share collapses from 0.51 to 0.14.
        r2 = max(3, int(float(P["rim"]) + 0.5))
        r1 = max(1, int(r2 * 0.34 + 0.5))
        lap = K.box(D, r1)
        lap -= K.box(D, r2)
        # Scaled by its own sigma, NOT by max(): the max is one outlier pixel and it
        # drifts ~7% between 1024 and 2048, which would make this finish's contrast a
        # function of render size. Sigma holds to under 2% across both.
        lap *= 1.0 / (3.6 * float(lap.std()) + 1e-6)
        return lap.astype(np.float32), D.astype(np.float32)

    return K.cache(("shdg", h, w, int(seed), _k(P)), build)


def paint_fl_shadowgraph(paint, shape, mask, seed, pm, bb):
    """Screen intensity I = I0 (1 + k grad^2 rho): flat where the gas is undisturbed,
    a DARK rim where rays are swept away and a BRIGHT rim where they pile up.

    Both lobes carry comparable amplitude on purpose. A one-sided rim — the first cut
    weighted the dark side 4.5x and then SQUARED the bright side, leaving it 20x
    weaker — is exactly the smooth one-sided shading a knife edge produces, i.e. it
    renders the schlieren this finish is supposed to be the sibling of.

    Written in-place because at 2048 every temporary is a 16 MB allocation and the
    naive single-expression form asks for nine of them just for `shade`. Cold
    paint+spec measures 1.2-1.6s at 2048 against the 3s gate.
    """
    P = _P("fl_shadowgraph")
    src = K.incoming(paint, shape)
    lap, D = _shadowgraph(shape, seed, P)
    a = float(P["amp"]) * float(pm)
    # The plateau term is the weak ray-divergence loss across a compressed slab. It is
    # a LADDER, never a ramp (a ramp is schlieren shading), and it is held to 14% of
    # the rim amplitude: SCALE is a RATIO, so plateau contrast is coarse energy that
    # would drag the car window down.
    shade = np.clip(-lap, 0.0, 1.0)
    shade *= 1.25
    shade += 0.18 * D
    shade -= 0.09
    shade *= -a
    shade += 1.0
    np.clip(shade, 0.06, 1.3, out=shade)
    # The bright half of the pair is UNDEFLECTED BEAM piling up on the screen, so it
    # washes toward white instead of saturating the livery colour — which is what keeps
    # the painter's base reading at any strength. The negative lobe clips to zero here,
    # so no separate clip is needed to isolate it. Capped at 0.68 so pm=2 cannot push
    # the rims past the coverage gate's near-white cutoff (measured dead 0.151 at pm=2).
    lift = np.clip(lap * a, 0.0, 0.68)
    shade *= 1.0 - lift
    out = src * shade[:, :, None]
    out += lift[:, :, None]
    return K.finish(out, src, mask)


def spec_fl_shadowgraph(shape, seed, sm, base_m, base_r):
    """GRAMMAR: rim-pair three-material. The SIGN of the Laplacian deals the material,
    so one field cuts the canvas into three: undisturbed panel at M28/R115/CC62 (the
    plurality cell — a satin semi-dielectric nobody else on this shelf sits on), a
    compressed rim that reads as dense polished metal, and a rarefied rim gone chalky
    and dull. The plateau's own shade steps through a 6-rung ladder driven by the
    density level — the same term the paint darkens compressed slabs by — so the
    background carries clean distinct shades with no grain anywhere.

    FOLLOW is true by construction rather than by argument: `lap` and `D` here are the
    SAME cached arrays the paint modulated with, and all three channels are driven off
    them. Measured amp_corr +0.85 to +0.89 across all ten knob samples.
    """
    lap, D = _shadowgraph(shape, seed, _P("fl_shadowgraph"))
    # A dead band below |lap| = 0.20: a shadowgraph plate records nothing at all until
    # the ray deflection clears the emulsion grain. It is also what holds the plateau
    # at 50-57% of canvas — a plurality, not a smear of ramps — measured over the whole
    # knob space, with the cell mean landing at M25.6-27.3 / R116.1-118.4 / CC63.0-64.7,
    # i.e. inside +/-3 of the assigned background everywhere in the space.
    c = np.clip((lap - 0.20) * (1.0 / 0.30), 0, 1)
    e = np.clip((-lap - 0.20) * (1.0 / 0.30), 0, 1)
    pl = K.ladder(D, 6, -1.0, 1.0)
    M = pl * 7.0
    M += 28.0
    M += (142.0 * sm) * c
    M -= (18.0 * sm) * e
    R = pl * -9.0
    R += 115.0
    R += (100.0 * sm) * e
    R -= (70.0 * sm) * c
    CC = pl * -7.0
    CC += 62.0
    CC += (106.0 * sm) * e
    CC -= (40.0 * sm) * c
    np.clip(M, 0, 255, out=M)
    np.clip(R, 15, 255, out=R)
    np.clip(CC, 16, 255, out=CC)          # 16 is MAX GLOSS; never below it
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════ CRACK TIP ══
# The reach budget, in units of the flaw pitch. Flaws are FOLDED, not looped, so
# a pixel only ever sees its own cell's tip and anything reaching past the cell
# wall wraps and prints a straight-edged rectangle (it did, until this was
# budgeted). Worst case: crack _CT_LEN behind the tip, lit contour 1.38*rp0 in
# front (0.93 yield locus x 1.22 mode-II swelling x 1.22 out to the sigma=0.905
# edge of the contour), the mark bounding box centred on the cell, plus the
# scatter:  (0.34 + 1.38*0.22)/2 + 0.16 = 0.482 < 0.5.  Do not raise one of these
# without lowering another.
_CT_MIX = 0.22      # mode-II mixity ceiling; |sk| < 1 also keeps (r + sk*b) > 0
_CT_CAP = 0.22      # plastic-zone scale rp0 <= 0.22*pitch
_CT_LEN = 0.34      # crack length <= 0.34*pitch behind its tip
_CT_JIT = 0.16      # per-flaw scatter inside the cell, +/- 0.16*pitch
_CT_OPEN = 1.15     # CTOD half-opening at the crack mouth, px
_CT_SLIP = 8.0      # slip-trace spacing inside the yielded metal, px
_CT_TINT = 0.085    # temper-oxide colour emitted over the painter's base
_CT_LIFT = 0.20     # albedo-independent return off the lit contour
_CT_ANI = (0.38, 0.60, 0.20)    # M / R / CC sensitivity to lobe orientation


def _crack_tip(shape, seed, P):
    """The plastic zone at a crack tip - the butterfly an inspector hunts for.

    Linear elastic fracture mechanics puts the stress round a tip at
    sigma ~ K/sqrt(2*pi*r)*f(theta), and metal yields wherever the von Mises stress
    reaches sigma_y. That locus is the textbook butterfly

        r_y(theta) = (rp0/4) * [3 sin^2(theta) + 2*c0*(1 + cos theta)]

    with c0 = (1-2nu)^2 ~ 0.16 in plane strain (wings at +/-87 deg, five times the
    reach of the notch dead ahead) and c0 -> 1 in plane stress (a fat forward
    kidney). A real panel is both at once, so c0 is a knob and the shelf ships
    somewhere between the two.

    Written in the crack frame (a ahead of the tip, b across it) the half-angle
    identities cos^2(t/2) = (r+a)/2r and sin^2(t/2) = (r-a)/2r collapse that to
    algebra, so the lobe field costs NO trig at all:

        (sigma_vm/sigma_y)^2 = rp0 * (r+a) * ((2c0+3)r - 3a) * (r + sk*b) / (4 r^4)

    which is exactly "cos(theta/2) lobes scaled by 1/sqrt(r)", clipped at 1 into a
    visible zone. Four things are read off it:

      * ZONE - sigma_vm >= sigma_y, graded rather than solid because sigma keeps
        climbing as 1/sqrt(r) inside it. Thresholded hard, every mark flattened
        into a blob and the wing shape was thrown away.
      * SLIP - yielded metal deforms on its shear planes, and the slip traces at
        45 deg to the crack are what an etch actually reveals. They live INSIDE
        the zone only, so they are structure, never sprinkled grit.
      * RIM - the sigma = sigma_y contour, the elastic-plastic boundary, which is
        the line an inspector reads. Two px wide and lit: at 5px (the first cut)
        every mark read as a glowing pill and the butterfly notch vanished.
      * CRACK - the slit that owns the tip, hairline at the tip and opening to
        the mouth as the CTOD says, kinked off the lobe axis by its own mode-II
        shear so it never reads as a pin stuck through a bean.

    sk = sin(2*theta) is the resolved shear for a uniaxial load on a plane at that
    angle, i.e. the mode-II mixity: it swells one wing, starves the other, and
    tilts the crack - which is what makes a mixed-mode flaw look sheared rather
    than stamped.
    """
    h, w = shape[:2]

    def build():
        pitch = float(P["pitch"])
        # A fold gives an unbounded flaw population for the cost of one, and the
        # whole job then is stopping the fold from reading as a LATTICE. Measured
        # at 1:1: a gentle warp (0.55 pitch over 220px) left the rows plainly
        # visible - it translates whole neighbourhoods instead of shearing them.
        # A 1.15-pitch throw over 2.4 pitches shifts the lattice phase by most of
        # a cell every two cells, and per-flaw scatter finishes the job. Cell
        # walls move WITH the flaws they contain, so warping costs no cut marks.
        wy, wx = K.warp(shape, seed + 3, pitch * 1.15, pitch * 2.4)
        inv = 1.0 / pitch
        v, u = wy * inv, wx * inv
        iv, iu = np.floor(v), np.floor(u)
        gh, gw = int(h / pitch) + 3, int(w / pitch) + 3
        fi = ((iv + 1.0).astype(np.int32) % gh) * gw + ((iu + 1.0).astype(np.int32) % gw)

        # ---- per-flaw properties live on the tiny gh x gw grid, so they are free
        rng = np.random.default_rng((int(seed) * 2246822519 + 0xC7A6) & 0xFFFFFFFF)
        dir0 = float(rng.random()) * np.pi
        # Cracks in a loaded part are not randomly oriented: they run roughly
        # normal to the principal stress with scatter. +/-50 deg about one axis
        # reads as a stressed PART; a uniform 0..pi reads as scattered stickers.
        th = dir0 + (rng.random((gh, gw), dtype=np.float32) - 0.5) * 1.75
        cg = np.cos(th).astype(np.float32).ravel()
        sg = np.sin(th).astype(np.float32).ravel()
        rr = rng.random((gh, gw), dtype=np.float32)
        # Cracks do not bloom evenly across a part - they bloom where the part is
        # LOADED. A smooth field over the FLAW GRID walks the bloom threshold, so
        # live indications arrive in clusters with quiet metal between them
        # instead of one even grid of marks. Built on the small grid, so this
        # macro organiser is free and carries no coarse contrast of its own.
        thr = np.clip(float(P["dorm"]) + 0.9 * (K.mid((gh, gw), 5.0, seed + 77, octaves=2) - 0.5),
                      0.02, 0.86)
        gr = (rr - thr) / np.maximum(1e-3, 1.0 - thr)
        kf = np.where(rr > thr, 0.52 + 0.48 * gr, 0.0)
        # A flaw below threshold lies DORMANT and shows as a bare hairline with no
        # zone at all. Those sites are what break the fold's regularity - for
        # free, and truthfully.
        rp = (np.minimum(kf * float(P["zone"]), _CT_CAP) * pitch).astype(np.float32).ravel()
        jy = ((rng.random((gh, gw), dtype=np.float32) - 0.5)
              * (2.0 * _CT_JIT * pitch)).astype(np.float32).ravel()
        jx = ((rng.random((gh, gw), dtype=np.float32) - 0.5)
              * (2.0 * _CT_JIT * pitch)).astype(np.float32).ravel()

        # One flat index, five takes: repeated 2-D fancy indexing recomputes the
        # same flat offsets five times over 4.2M pixels.
        ca, sa = np.take(cg, fi), np.take(sg, fi)
        rpx = np.take(rp, fi)
        fv = (v - iv - 0.5) * pitch - np.take(jy, fi)
        fu = (u - iu - 0.5) * pitch - np.take(jx, fi)

        # ---- crack frame: a runs along the crack, b across it, tip at a = 0 ----
        # A longer crack carries a bigger K and so a bigger zone; running that the
        # other way keeps the two in proportion for free. The subtracted term
        # centres the mark's bounding box on the cell (see the reach budget).
        cl = (_CT_LEN * 0.55) * pitch + (_CT_LEN * 0.45 / _CT_CAP) * rpx
        a0 = fu * ca + fv * sa - (0.5 * cl - 0.69 * rpx)
        b = fv * ca - fu * sa
        sk = (2.0 * _CT_MIX) * ca * sa
        # A second superposed tip (a centre crack, a butterfly at each end) was
        # built and CUT: the two fields add, sigma doubles between them and the
        # merged zone came out an oval. The silhouette is only legible when one
        # singularity owns a mark.
        r2 = a0 * a0 + b * b + 0.8      # +0.8px^2 = CTOD blunting. A real tip opens
        r = np.sqrt(r2)                 # to a finite radius, and that is what kills
        k3 = 3.0 + 2.0 * float(P["c0"])  # the 1/sqrt(r) singularity in the metal too.
        q = (r + a0) * (k3 * r - 3.0 * a0) * (r + sk * b)
        q *= (0.25 * rpx) / (r2 * r2)
        sig = np.sqrt(q)                          # sigma_vm / sigma_y
        zone = np.clip((sig - 1.0) * 4.0, 0.0, 1.0)       # yielded metal
        rim = np.clip(1.0 - np.abs(sig - 0.95) * 22.0, 0.0, 1.0)   # sigma = sigma_y
        # Slip traces on the 45 deg shear planes. A triangle wave, not a sine:
        # same look, no transcendental over 4.2M pixels.
        ph = (a0 + b) * (0.7071 / _CT_SLIP)
        slip = 1.0 - float(P["slip"]) * np.abs(ph - np.floor(ph) - 0.5) * 2.0
        # The crack itself: opening ~ sqrt of distance behind the tip (CTOD), so
        # it is a hairline where it matters and never a stick. The -a0 gate keeps
        # it strictly behind the tip AND fades the thin end, which is what stops a
        # sub-pixel line rasterising into a dotted trail - measured, it did.
        op = np.sqrt(np.clip(-a0 / cl, 0.0, 1.0))
        bc = np.abs(b - (2.0 * sk) * a0)
        crack = (np.clip((0.45 + _CT_OPEN * op - bc) * 1.3, 0.0, 1.0)
                 * np.clip(-a0 * 0.7, 0.0, 1.0)
                 * np.clip((a0 + cl) * (4.0 / (_CT_LEN * pitch)), 0.0, 1.0))
        # The etched panel the indication sits on. 14px keeps the surface inside
        # the car window, so it pays INTO the scale axis instead of against it.
        etch = K.mid(shape, 14.0, seed + 9, octaves=2)

        dmg = np.clip(zone * (0.86 * slip) + crack * 0.80, 0.0, 1.0)
        # ONE field carries the whole finish and both fns read it. Sound panel sits
        # at 0.66-0.84 either side of 0.75; the zone runs it down toward 0.11; the
        # crack takes it to 0.15. It tops out ABOVE 1 on purpose - the yield
        # contour is allowed back BRIGHTER than sound metal, which is the only way
        # a lit contour survives.
        fld = np.clip((1.0 - dmg) * (0.66 + 0.18 * etch) + rim * 0.23, 0.0, 1.10)
        ani = ca * ca              # = (1 + cos 2*theta)/2, the lobe axis, for the spec
        return (fld.astype(np.float32), zone.astype(np.float32),
                rim.astype(np.float32), ani.astype(np.float32))

    return K.cache(("crack_tip", h, w, int(seed), _k(P)), build)


def paint_fl_crack_tip(paint, shape, mask, seed, pm, bb):
    """A crack's plastic zone etched out of the panel, with its yield contour lit."""
    P = _P("fl_crack_tip")
    src = K.incoming(paint, shape)
    fld, zone, rim, _ = _crack_tip(shape, seed, P)
    p = float(pm)
    # Deformed metal etches faster and goes dark. Centred on the SOUND PANEL, not
    # on white: fld sits at 0.75 wherever the metal is good, so g is exactly 1
    # there and the painter keeps the colour they chose - only the indication
    # moves. (Anchoring at 1.0 instead darkened the whole panel 40% at the top of
    # the depth range, which is not a thing a BASE finish may do to a livery.)
    g = 1.0 + float(P["depth"]) * p * (fld - 0.75)
    # A mirror contour returns light regardless of what colour the panel is, so
    # the lit boundary is added, not multiplied: src*(g-L) + L is that same lift
    # for one extra array op. Measured: without it the finish read only as the
    # temper tint on a 0.05 base.
    L = rim * (_CT_LIFT * p)
    # TEMPER COLOURS, not a false-colour ramp: plastic work heats the yielded
    # metal and the oxide it grows runs straw in the worked core and blue at the
    # elastic boundary. Scaled by depth as well - at a shallow reveal the tint was
    # the only structure left in the luma, and the spec (which follows fld)
    # decorrelated from it.
    e = _CT_TINT * float(P["depth"]) * p
    out = (src * (g - L)[:, :, None]
           + np.dstack((L + e * (zone * 0.85 + rim * 0.20),
                        L + e * (zone * 0.34 + rim * 0.35),
                        L + e * (rim * 0.85 - zone * 0.62))))
    return K.finish(out, src, mask)


def spec_fl_crack_tip(shape, seed, sm, base_m, base_r):
    """GRAMMAR: lobe-orientation anisotropy. One field, three channels, each with
    its own SENSITIVITY to the axis its lobe happens to be lying on.

    Yielded metal is directionally roughened - the slip bands run on the crack's
    own shear planes - and an isotropic BRDF cannot express that, so the
    anisotropy is BAKED: an indication lying across the light gets its roughness
    pushed hardest, its metallic less, its clearcoat least. Every weight stays
    strictly positive, because a sign flip between channels is exactly what
    cancels FOLLOW. The weights are gated by the indication itself, so sound metal
    is untouched - ungated, the per-flaw constant printed a faint cell grid over
    the whole panel.

    Material story: an etched-and-repolished steel coupon (M70 R95 CC40 - the
    dominant cell at 89% of canvas, and EXACT wherever the panel is sound),
    running to near-mirror at the lit yield contour and to dull grown oxide inside
    the zone.
    """
    P = _P("fl_crack_tip")
    fld, zone, rim, ani = _crack_tip(shape, seed, P)
    s = float(sm)
    # FOLLOW by construction: this IS the paint's driver, one ladder later. Ten
    # steps is coarse enough that sound panel quantises onto the background cell
    # and fine enough to deal a dozen materials across the indication with no
    # grain anywhere. Measured FOLLOW 0.88-0.96 against a 0.35 floor.
    t = K.ladder(1.0 - fld, 10, 0.0, 1.0) - 0.2222
    d = np.clip(zone + rim, 0.0, 1.0) * (1.0 - ani)
    M = np.clip(70.0 - 60.0 * t * (1.0 - _CT_ANI[0] * d) * s, 0.0, 255.0)
    R = np.clip(95.0 + 150.0 * t * (1.0 - _CT_ANI[1] * d) * s, 15.0, 255.0)
    CC = np.clip(40.0 + 105.0 * t * (1.0 - _CT_ANI[2] * d) * s, 16.0, 255.0)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════ FLAW LAB · BARKHAUSEN NOISE ══
def _bark(shape, seed, P):
    """Magnetic domain walls jumping in avalanches under a slowly swept field.

    Put a pickup coil on a steel part and ramp an applied field. The domain wall
    does not glide — it sticks on dislocations and precipitates, then JUMPS.
    Every jump is one avalanche, heard as a click in the coil, and the jump sizes
    obey a power law. Inspectors read the statistics of those clicks to find
    grinding burn and residual stress no surface method can see.

    THE SIZE DISTRIBUTION IS THE PHYSICS, so it is CONSTRUCTED, not hoped for out
    of noise. Four merge levels claim area fractions 0.55 / 0.25 / 0.13 / 0.07 at
    1 / 4 / 16 / 64 cells, so the event COUNTS come out 0.55/1 : 0.25/4 : 0.13/16
    : 0.07/64 = 503 : 57 : 7.4 : 1 — ~8x fewer events per 4x of area, i.e.
    tau = ln 8 / ln 4 = 1.50, the mean-field Barkhausen exponent. (For P(S)~S^-tau
    the area fractions must go as S^(1-tau) = S^-0.5, which is that exact set.)

    AFFORDABLE because every avalanche decision — including a Voronoi merge per
    level, so events are irregular polygons and never blocks — happens in LATTICE
    space (a 90x250 grid, 22k cells) and reaches the 4.2M-pixel canvas through ONE
    gather. Four decades of event size cost no extra full-canvas op.
    """
    h, w = shape[:2]

    def build():
        cx = float(P["cell_px"])                 # domain width across the easy axis
        cy = cx * float(P["aspect"])             # 180-degree domains are lamellae, not blobs
        ca, sa = 0.9171, 0.3986                  # easy axis at 0.41 rad — never axis-aligned
        gw = int(np.ceil((w * ca + h * sa) / cx)) + 8
        gh = int(np.ceil((h * ca + w * sa) / cy)) + 8

        # ---- LATTICE SPACE — the whole power law is decided here -------------
        rng = np.random.default_rng((int(seed) * 9176 + 5507) & 0xFFFFFFFF)
        iy = np.arange(gh, dtype=np.float32)[:, None]
        ix = np.arange(gw, dtype=np.float32)[None, :]
        vals = [rng.random((gh, gw), dtype=np.float32)]      # level 0: one cell, one event
        for s in (2, 4, 8):                                  # merged events of 4, 16, 64 cells
            bh, bw = gh // s + 2, gw // s + 2
            jy = rng.random((bh, bw), dtype=np.float32) * 0.9
            jx = rng.random((bh, bw), dtype=np.float32) * 0.9
            vv = rng.random((bh, bw), dtype=np.float32)
            by, bx = iy * (1.0 / s), ix * (1.0 / s)
            fy, fx = np.floor(by), np.floor(bx)
            yi, xi = fy.astype(np.int32), fx.astype(np.int32)
            best = np.full((gh, gw), 1e9, np.float32)
            out = np.zeros((gh, gw), np.float32)
            for dy in (-1, 0, 1):                            # 9-neighbour Voronoi over 22k
                for dx in (-1, 0, 1):                        # cells = 0.6 Mop, i.e. free
                    ky, kx = (yi + dy) % bh, (xi + dx) % bw
                    d = (by - (fy + dy + jy[ky, kx])) ** 2 + (bx - (fx + dx + jx[ky, kx])) ** 2
                    c = d < best
                    out = np.where(c, vv[ky, kx], out)
                    best = np.where(c, d, best)
            vals.append(out)
        # Weak-pinning territory. A Barkhausen scan is USED to locate these, so the
        # big events must CLUSTER into soft zones rather than scatter one cell at a
        # time: a block-coherent selector at 0.74 against 0.26 of per-cell noise
        # keeps a merged block mostly on one level.
        soft = rng.random((gh // 8 + 2, gw // 8 + 2), dtype=np.float32)
        soft = np.repeat(np.repeat(soft, 8, 0), 8, 1)[:gh, :gw]
        lf = 0.74 * soft + 0.26 * rng.random((gh, gw), dtype=np.float32)
        t0, t1, t2 = np.quantile(lf, (0.55, 0.80, 0.93))
        lvl = (lf > t0).astype(np.int32) + (lf > t1) + (lf > t2)
        hsw = np.choose(lvl, vals).astype(np.float32)    # switching field, flat per event
        szl = lvl.astype(np.float32) * (1.0 / 3.0)       # avalanche size class, 0..1
        # A wall exists ONLY between two DIFFERENT events, so a merged avalanche
        # stays one uninterrupted domain the way a real one does — and a big event
        # is legible by the ABSENCE of walls inside it as much as by its tone.
        br = (hsw != np.roll(hsw, -1, axis=1)).astype(np.float32)
        bd = (hsw != np.roll(hsw, -1, axis=0)).astype(np.float32)
        lat = np.dstack([hsw, szl, br, bd])

        # ---- ONE gather to the canvas ---------------------------------------
        # Three warp bands (44 / 22 / 11px, falloff 0.85 so the finest keeps 28% of
        # the amplitude) rather than K.warp's two: the coarse bands bend the
        # lamellae and the 11px band eats the lattice's straight edges. Without it
        # this rendered as digital camouflage — staircase blocks, and a near-certain
        # uniqueness collision with the camo/digicam finishes already in the catalog.
        py, pxx = K.px(shape)
        wy = py + (K.mid(shape, 44.0, int(seed) + 31, octaves=3, falloff=0.85) - 0.5) * 26.0
        wx = pxx + (K.mid(shape, 44.0, int(seed) + 32, octaves=3, falloff=0.85) - 0.5) * 26.0
        u = (wx * ca + wy * sa) * (1.0 / cx) + 4.0
        v = (wy * ca - wx * sa) * (1.0 / cy) + (w * sa / cy + 4.0)
        flu, flv = np.floor(u), np.floor(v)
        fu, fv = u - flu, v - flv
        g = lat[flv.astype(np.int32) % gh, flu.astype(np.int32) % gw]
        hf = g[:, :, 0].copy()
        sf = g[:, :, 1].copy()
        # Bitter powder, one-sided over 0.30 of a cell (~3.2px): every internal
        # boundary is some cell's right or bottom edge, so the network closes with
        # two flags instead of four. The cross-wall runs at 0.55 because the ends of
        # a 180-degree lamella are closure caps, not full walls, and hold less
        # powder — measured, that split also lifts FOLLOW 0.938 -> 0.974.
        wall = np.maximum(np.clip((fu - 0.70) * 3.33, 0, 1) * g[:, :, 2],
                          np.clip((fv - 0.70) * 3.33, 0, 1) * g[:, :, 3] * 0.55)

        # ---- lancet closure structure ---------------------------------------
        # Surface closure domains break into fine fir-tree lancets across the main
        # lamellae — the reason a real Kerr plate is never flat inside a domain.
        # ZERO-MEAN on purpose: this carrier gets multiplied by per-event envelopes
        # below, and a DC-carrying stripe would drag those envelopes straight into
        # the coarse band (measured: coarse 0.40 -> 0.28, median feature 66 -> 19px).
        # The +hf phase term restarts the comb at every wall, so each domain grows
        # its own closure structure instead of one global grating.
        lz = (wx * sa - wy * ca) * (1.0 / (cx * 0.82)) + hf * 3.0
        tri = np.abs(lz - np.floor(lz) - 0.5) * 2.0
        fir = tri * tri - 0.3333

        # ---- the sweep --------------------------------------------------------
        # H is the field the probe ramps across the part. Held to +/-0.075: it slides
        # the reversed FRACTION slowly and contributes almost no coarse contrast of
        # its own, which is the term SCALE punishes. At 0.12 the radial spectrum's
        # argmax jumped to the 1024px bin.
        H = 0.5 + (K.mid(shape, 320.0, int(seed) + 9, octaves=1) - 0.5) * 0.15
        adv = np.clip((H - hf) * float(P["gain"]) + 0.5, 0.0, 1.0)  # 0 unreversed, 1 reversed
        burst = 1.0 - np.abs(adv * 2.0 - 1.0)          # peaks on the events JUMPING NOW
        raw = (((adv - 0.5) * 0.62                     # two magnetisation populations
                + (hf - 0.5) * 0.30)                   # plus each event's own switching field
               * (1.0 - 0.45 * sf)                     # merged events tone DOWN, never up
               + burst * (0.30 + 0.70 * sf) * fir * float(P["spike"])  # the click, sized by
               + fir * (0.40 + 0.60 * hf) * float(P["lance"])          # the event but drawn
               - wall * float(P["wall"]))                              # as FINE lancets
        # A bigger jump is a bigger click, but paying that out as flat per-event
        # tone is what a 92px avalanche does to SCALE: an earlier cut boosted tone
        # with size (exc = 0.75 + 0.25*sf) and measured band 0.336 / coarse 0.492.
        # Spending it on the lancet carrier instead keeps the physics and reads at
        # 10-20px: band 0.446 / coarse 0.284.
        m = float(raw.mean())
        s = max(float(raw.std()), 1e-6)                # +/-2 sigma. Min/max normalising let
        mod = np.clip((raw - m) * (1.0 / (4.0 * s)) + 0.5, 0.0, 1.0)   # one rare spike eat it
        return mod, sf, wall

    return K.cache(("bark", h, w, int(seed), _k(P)), build)


def paint_fl_barkhausen(paint, shape, mask, seed, pm, bb):
    """Kerr image of the domain pattern caught mid-sweep: reversed domains bright,
    un-reversed dark, iron filings dark along every wall between two avalanches."""
    P = _P("fl_barkhausen")
    src = K.incoming(paint, shape)
    mod, _sz, _wl = _bark(shape, seed, P)
    lum = 0.52 + 0.70 * mod * float(pm)
    # A Kerr analyser turns the two magnetisation senses into COMPLEMENTARY tints,
    # so the hue split IS the sign of the domain, not decoration — and it rides the
    # same field the brightness does, which is why the painter's own colour still
    # reads through it at every base tested (red, steel, blue).
    out = K.hue_rotate(src * lum[:, :, None], (mod - 0.5) * (0.40 * float(pm)))
    return K.finish(out, src, mask)


def spec_fl_barkhausen(shape, seed, sm, base_m, base_r):
    """GRAMMAR: avalanche-size ladder — the rung COUNT is set by how big the event
    was, which is the one quantity this technique actually measures. Small events
    get 14 fine rungs and hold the finish's own material cell (M150/R118/CC54,
    ~54% of canvas); the largest get 4 coarse rungs and swing the whole excursion,
    the way a big jump throws a big spike in the coil. All three channels are one
    affine map of ONE driver rebuilt from the paint's own field, so they cannot
    drift apart — measured FOLLOW 0.979, identical on M, R and CC."""
    P = _P("fl_barkhausen")
    mod, szf, wall = _bark(shape, seed, P)
    sN = 14.0 - 10.0 * szf                                    # 14 / 10.7 / 7.3 / 4 rungs
    q = np.floor(np.clip(mod, 0.0, 0.9999) * sN) / (sN - 1.0)
    # wall^2 keeps the filings on the line core, so they read as their own matte
    # non-metallic material without claiming a second quantised story cell.
    d = ((q - 0.5) - 0.34 * wall * wall) * float(sm)
    M = np.clip(150.0 + 84.0 * d, 0.0, 255.0)     # a reversed domain reads more metallic
    R = np.clip(118.0 - 36.0 * d, 15.0, 255.0)    # and slightly tighter
    CC = np.clip(54.0 - 42.0 * d, 16.0, 255.0)    # and slightly glossier
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════ MACRO ETCH ══
def _macro_etch(shape, seed, P):
    """Blue etch anodise on a forging: the grain flow the naked eye cannot see.

    THE TECHNIQUE. Saw a forged part in half, etch the face, anodise it, and the
    macro structure appears in blue: the fibre STREAMS around whatever the die
    put in its way and CROWDS where the metal was compressed. The inspector is
    looking for flow that was CUT by machining instead of wrapped around.

    THE MECHANISM IS THE PHYSICS, NOT A LOOKALIKE. Forging flow is irrotational,
    so the field is the textbook one: a uniform stream past two circular bosses,
    each a doublet, superposed. `psi` is the stream function and its contours ARE
    the grain flow lines; `phi` is the conjugate potential and runs across the
    fibres, so the pair is the flow net itself. Crowding is not painted on — it
    falls out of |grad psi|, which is the line density the geometry produces.

    SOFT = 0.40 in every doublet denominator is the boss FILLET radius, and it is
    also what keeps the finish inside the car window: the singular ideal doublet
    drives contour spacing sub-pixel inside the boss. Measured over the whole
    2048 canvas at the shipped pitch, SOFT=0.40 caps |grad psi| at 1.52, giving a
    local line spacing of p0.1 10.4px / median 14.2px / p98 31.6px, with 0.00000
    of the canvas below the 8px car-window floor.
    """
    h, w = shape[:2]

    def build():
        # A forging is not a textbook diagram; the die flash wanders. 900px is
        # slow enough that the induced strain stays near 0.3, so this bends the
        # fibre without ever squeezing the line pitch out of the car window.
        Y, X = K.warp(shape, seed + 31, float(P["wander"]), 900.0)

        # The forging axis is not the canvas axis. Rotating the two flow
        # coordinates once is cheaper than rotating anything downstream, and it
        # keeps the far-field fibre off horizontal, where it reads as banding.
        ang = ((int(seed) * 2654435761) >> 6) % 997 / 997.0 * 3.14159265
        ca, sa = np.float32(np.cos(ang)), np.float32(np.sin(ang))
        u0 = Y * ca - X * sa                   # across the axis -> stream function
        v0 = X * ca + Y * sa                   # along it        -> potential
        del X, Y
        psi = u0.copy()
        phi = v0.copy()

        # Two bosses, the second smaller. They are kept in separate halves of the
        # plate on purpose: two doublets landing on top of each other collapse
        # into one big swirl and the "flow around an obstruction" story is lost.
        rng = np.random.default_rng((int(seed) ^ 0x5A17) & 0xFFFFFFFF)
        rad = float(P["boss_px"])
        for i in (0, 1):
            a2 = np.float32((rad * (1.0 - 0.34 * i)) ** 2)
            cx = (0.18 + 0.30 * float(rng.random()) + 0.34 * i) * w
            cy = (0.22 + 0.56 * float(rng.random())) * h
            # dx/dy are taken from the UNTOUCHED u0/v0, never from the running
            # psi/phi — otherwise boss two would be sited on boss one's wake.
            dy = u0 - np.float32(cy * ca - cx * sa)
            dx = v0 - np.float32(cx * ca + cy * sa)
            rr = dx * dx
            rr += dy * dy
            rr += np.float32(0.40) * a2        # SOFT: the boss fillet, see above
            np.divide(a2, rr, out=rr)          # rr is now the doublet weight
            np.multiply(rr, dy, out=dy)
            psi -= dy                          # doublet stream function
            np.multiply(rr, dx, out=dx)
            phi += dx                          # its conjugate potential
        del u0, v0, dx, dy, rr

        # CROWDING = |grad psi|, differenced rather than derived. The analytic
        # form costs ~12 more full-canvas ops AND misses the warp's own Jacobian,
        # so it would report crowding the pixels do not have. This is the real
        # local line density, which is what "the grain is compressed" means.
        g2 = np.zeros((h, w), np.float32)
        d = psi[1:, :-1] - psi[:-1, :-1]
        g2[:-1, :-1] = d * d
        d = psi[:-1, 1:] - psi[:-1, :-1]
        g2[:-1, :-1] += d * d
        g2[-1, :] = g2[-2, :]
        g2[:, -1] = g2[:, -2]
        crowd = np.sqrt(g2, out=g2)
        crowd *= np.float32(0.62)              # far-field |grad psi| = 1 -> 0.62
        np.clip(crowd, 0.0, 1.0, out=crowd)
        del d

        # The etch line: a hard ~3px groove core inside a soft shoulder. One wide
        # triangle read as a smooth stripe (timber, not metal); the etchant
        # actually undercuts a narrow boundary and stains the shoulder either
        # side. The 5.0 core slope rather than a sharper one is deliberate — a
        # 2px core throws a fifth of the finish's energy below the 8px window,
        # where SCALE counts it as dilution and a MIP drops it entirely.
        ip = np.float32(1.0 / float(P["pitch"]))
        q = psi * ip
        gi = np.floor(q)                                      # flow-band index
        fr = q - gi
        fr *= np.float32(2.0)
        fr -= np.float32(1.0)
        np.abs(fr, out=fr)
        halo = np.clip(1.0 - fr * np.float32(2.2), 0.0, 1.0)
        core = np.clip(1.0 - fr * np.float32(5.0), 0.0, 1.0)
        line = halo * np.float32(0.35)
        line += core * np.float32(0.65)
        del q, fr, halo, core, psi

        # Macro-grains, addressed in FLOW coordinates: bounded across by the psi
        # bands (in wrought metal the grain boundaries ARE the flow lines) and
        # 1.6 bands long down phi, so each grain is a fibre, elongated the way
        # forging elongates it. 1.6 keeps the cell (~14 x 23px) wholly inside the
        # car window; the first cut at 2.8 bands put a 46px along-flow period in
        # the spectrum and it measured as the largest single peak.
        # The along-fibre tone is interpolated, not stepped: laddering it put
        # hard rectangular seams across the flow and the sheet looked blocked.
        tj = phi * np.float32(ip / 1.6)
        gj = np.floor(tj)
        fj = tj - gj
        # frac(a*gi + b*gj) alone is a LINEAR function mod 1, i.e. a repeating
        # diagonal ramp — measured as a regular along-flow beat, not grain. The
        # quadratic fold below breaks that; s1 is the same hash one cell further
        # down the fibre, so the interpolation stays continuous at cell walls.
        s0 = gi * np.float32(0.7548776662)
        s0 += gj * np.float32(0.5698402910)
        s0 -= np.floor(s0)
        s1 = s0 + np.float32(0.5698402910)
        s1 -= np.floor(s1)
        s0 *= (s0 * np.float32(71.37) + np.float32(29.11))
        s0 -= np.floor(s0)
        s1 *= (s1 * np.float32(71.37) + np.float32(29.11))
        s1 -= np.floor(s1)
        sm3 = fj * fj
        sm3 *= (np.float32(3.0) - np.float32(2.0) * fj)
        s1 -= s0
        s1 *= sm3
        s1 += s0                                              # grain tone
        del fj, sm3, gj, phi

        # Three things set how hard a boundary etched, and all three are real:
        # the band's own boundary character (hb, one value per fibre, folded the
        # same way for the same reason), stored strain (crowd), and the etchant
        # beading along the groove (td, ~9px down the fibre).
        hb = gi * np.float32(0.1031)
        hb += np.float32(0.117)
        hb -= np.floor(hb)
        hb *= (hb * np.float32(59.73) + np.float32(23.31))
        hb -= np.floor(hb)
        td = tj * np.float32(2.4)
        td -= np.floor(td)
        td *= np.float32(2.0)
        td -= np.float32(1.0)
        np.abs(td, out=td)
        del tj, gi

        # They scale the line's contrast ABOUT ITS OWN MEAN — analytically 0.145
        # for this duty cycle — because an ADDITIVE crowd term dumps energy above
        # 32px and costs SCALE, while a multiplicative one only puts sidebands
        # either side of the 14px carrier.
        gexp = crowd * np.float32(0.78)
        gexp += np.float32(0.42)
        hb *= np.float32(1.20)
        hb += np.float32(0.40)
        gexp *= hb
        td *= np.float32(-0.34)
        td += np.float32(1.0)
        gexp *= td
        del hb, td, crowd

        PIV = np.float32(0.145)
        line -= PIV
        line *= gexp
        line += PIV
        gm = float(P["grain"])
        s1 *= np.float32(gm)
        line *= np.float32((1.0 - gm) * 1.55)
        s1 += line
        np.clip(s1, 0.0, 1.0, out=s1)
        return s1

    return K.cache(("fl_macro_etch", h, w, int(seed), _k(P)), build)


def paint_fl_macro_etch(paint, shape, mask, seed, pm, bb):
    """Etched forging section: dark grain-flow grooves under an anodic blue film."""
    P = _P("fl_macro_etch")
    src = K.incoming(paint, shape)
    mod = _macro_etch(shape, seed, P)                 # etch attack, 0..1
    t = float(P["tint"])
    u = np.float32(0.40) - mod                        # +ve where the acid barely bit
    tone = u * np.float32(float(P["depth"]) * 0.95 * float(pm))
    tone += np.float32(1.0)
    tone *= np.float32(1.0 - t)                       # the film's share of the mix
    out = src * tone[:, :, None]
    # The face is anodised AFTER etching, so the whole section carries film and
    # its colour is an INTERFERENCE SERIES in film thickness — which is why
    # neighbouring macro-grains come out as different blues. Both ends of the
    # series are the tank indigo rotated about grey; doing that on a 1x1 swatch
    # instead of per pixel measured 0.5s cheaper for the same chroma spread.
    tank = np.float32([0.16, 0.34, 0.80]).reshape(1, 1, 3)
    lo = K.hue_rotate(tank, -0.34)[0, 0]
    hi = K.hue_rotate(tank, 0.30)[0, 0]
    gain = u * np.float32(1.10 * float(pm))
    gain += np.float32(0.50)
    np.clip(gain, 0.02, 1.0, out=gain)                # film is thin in the pits
    gain *= np.float32(t)
    step = K.ladder(mod, 5, 0.0, 1.0)                 # five thickness orders
    step *= gain
    for c in range(3):                                # 3 iterations, not a feature loop
        out[:, :, c] += gain * np.float32(lo[c])
        out[:, :, c] += step * np.float32(float(hi[c]) - float(lo[c]))
    return K.finish(out, src, mask)


def spec_fl_macro_etch(shape, seed, sm, base_m, base_r):
    """GRAMMAR: flow-crowding ladder. The etch-attack field is quantised into
    seven flat metallurgical rungs, and because that field's contrast is scaled
    by the streamline crowding, how far up the ladder a region can climb is set
    by how hard the grain was compressed: the open shank works the low rungs,
    the crowded boss shoulders span the whole ladder. Attack exposes fresh metal
    (M up), leaves etch pits (R up) and eats the film's gloss (CC up), so ONE
    field carries all three — the same cached field the paint used, not a
    re-invented one (measured amp_corr +0.97).

    The pivot is rung 1 exactly, because rung 1 is the modal rung of this field
    over the whole knob space (measured 0.33-0.45 of the canvas at every corner),
    so this finish's identity cell lands on M 85 / R 130 / CC 36 dead on. The
    three step sizes are not free either: they are chosen so consecutive rungs
    cross a quantiser boundary (85 / 127.5 / 170 / 212.5) in at least one
    channel, which is what keeps all seven rungs as SEVEN distinct material
    cells instead of collapsing into three — measured before and after.
    """
    mod = _macro_etch(shape, seed, _P("fl_macro_etch"))
    lad = K.ladder(mod, 7, 0.0, 1.0) - (1.0 / 6.0)
    lad *= np.float32(sm)
    M = np.clip(85.0 + 156.0 * lad, 0, 255)
    R = np.clip(130.0 + 90.0 * lad, 15, 255)
    CC = np.clip(36.0 + 78.0 * lad, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════ NN · HARDNESS INDENT ══
def _vickers(shape, seed, P):
    """A Vickers traverse: the machine-rastered row-and-column array of diamond
    pyramid indents, each ringed by the metal it displaced.

    The whole finish hangs off one decision — the distance metric is L1, not L2.
    `|a| + |b|` draws a SQUARE STOOD ON ITS CORNER, which is exactly what a
    square-based 136-degree pyramid leaves in a surface and exactly the shape
    whose two diagonals the operator measures. Nothing else in the catalog uses
    a non-Euclidean metric: measured top structural similarity 0.352 against the
    live 2794-entry fingerprint index, versus the 0.80 fail line.
    """
    h, w = shape[:2]

    def build():
        # The traverse step and the line step are not equal on a real stage, and
        # making them equal was a visible mistake: an isotropic lattice has 4-fold
        # symmetry and reads as a quilted diamond-plate wallpaper. 1.14 breaks the
        # symmetry and still keeps BOTH periods inside the 8-32px car window —
        # measured spectral peak 13.9-25.9px across all 10 SPACE samples. At the
        # 1.15 x 29px this started from, sample 6 peaked at 33.0px and dumped
        # 0.146 of its energy into SCALE's coarse denominator.
        pu = np.float32(P["pitch"])
        pv = pu * np.float32(1.14)
        py, pxx = K.px(shape)

        # ONE low-frequency field, spent twice: the hardness of the coupon
        # (quantised to flat plateaus, below) and the tester's stage drift. They
        # are independent in reality, but a 2px drift correlated with a ~300px
        # hardness patch is invisible, and a second noise build costs 0.26s of a
        # 3s budget. 300px is fixed rather than a knob because the SIZE of a
        # hardness patch barely reads while its amplitude, below, changes the panel.
        raw = K.mid(shape, 300.0, seed + 11, octaves=2)

        # The coupon is never mounted square to the stage.
        ca, sa = np.float32(0.98162), np.float32(0.19081)      # 11 degrees
        wob = (raw - 0.5) * np.float32(3.6)
        u = (pxx * ca + py * sa + wob) / pu
        v = (py * ca - pxx * sa - wob * np.float32(0.6)) / pv

        # THE MEASUREMENT ITSELF. A traverse exists to read hardness, and hardness
        # is read as indent SIZE — soft metal takes a wider diamond under the same
        # load. This is the only macro term and it is deliberately FLAT (plateaus,
        # no gradient): SCALE is a ratio, so a smooth coarse field here would eat
        # the fine band it is meant to organise. Measured coarse energy <= 0.013
        # of total on every sample; it changes the size of the fine structure and
        # the pile-up/crack balance, never the brightness of the panel.
        soft = 1.0 - K.ladder(np.clip((raw - 0.5) * 2.6 + 0.5, 0, 1), 5, 0.0, 1.0)

        a = (u - np.floor(u) - 0.5) * pu
        b = (v - np.floor(v) - 0.5) * pv
        aa, ab = np.abs(a), np.abs(b)
        d1 = aa + ab                                   # L1 -> DIAMOND, not a disc
        rad = pu * np.float32(P["fill"]) * (0.80 + 0.42 * soft)
        t = rad - d1
        pit = np.clip(t * 0.77, 0, 1)                  # ~1.3px antialiased edge
        cone = np.clip(t / np.maximum(rad, 1.0), 0, 1)  # linear in L1 = a true pyramid

        # FOUR FACETS. The pyramid's faces meet along the axes of the (a, b) frame
        # — which are the diamond's vertex directions, i.e. exactly where a real
        # indenter's edges run — so the face you stand on is just the quadrant of
        # (sign a, sign b), and a Lambert term on a plane whose normal is
        # (sa, sb, k) is LINEAR in those two signs. Two ops buy the two-bright /
        # two-dark diamond every micrograph shows, with no per-facet work.
        # The -1.35 bias is not cosmetic: EVERY wall of a pit tilts away from a
        # vertical illuminator, so all four must read darker than the flat land.
        # Without it the lit quadrant matched the land and the impression read as
        # a triangle — visible at 4x, invisible in every metric.
        lit = np.float32(P["light"]) * 0.45
        facet = (np.sign(a) * 0.62 + np.sign(b) * 0.34 - 1.35) * lit

        # PILE-UP. The displaced metal has to go somewhere: it stands proud in a
        # lip just outside the impression, greatest at the middle of each face and
        # least at the corners (min(|a|,|b|)/d1 is exactly that ratio), and it only
        # forms in low-work-hardening (soft) material. Two numbers here were set by
        # eye at 4x, not by metric: the lip width is 0.26*rad because a fixed 1.35px
        # lip is invisible on the car while 0.42*rad quilts the four crescents into
        # a bubble field and destroys the diamond outline; and the corner floor is
        # 0.30 rather than 0 so the lip stays a continuous OUTLINE — the outline is
        # what makes a viewer read "diamond" instead of "four bright arcs".
        rw = rad * np.float32(0.26)
        spine = np.minimum(aa, ab)                     # 0 on the two indent diagonals
        edge = spine * 2.0 / np.maximum(d1, 1e-3)      # 0 at a corner, 1 mid-face
        rim = np.clip(1.0 - np.abs(t + rw) / rw, 0, 1) * (0.30 + 0.70 * edge) * (0.42 + 0.80 * soft)

        # AND THE OPPOSITE RESPONSE. Where the coupon is hard it does not pile up,
        # it CRACKS: four radial cracks run out of the four corners, which is the
        # whole basis of indentation fracture toughness. Same field, inverted by
        # hardness. The crack width is set in PIXELS off `spine`, NOT as an angular
        # ratio of `edge`: an angular wedge is sub-pixel near the corner (edge<1/9
        # means |b| < |a|/18, i.e. under 0.7px at this radius), so it aliased into
        # scattered specks — confetti that delivered none of the stated mechanism.
        # In pixels it is a 2.8px filament, which is what a crack actually is.
        crk = (np.clip(1.0 - spine * np.float32(0.72), 0, 1)
               * np.clip(-t * 0.9, 0, 1)
               * np.clip((rad * 2.1 - d1) * 0.34, 0, 1)
               * np.float32(P["crack"]) * (1.15 - soft))

        # The coupon was mirror-polished before it was indented and the wheel leaves
        # long unidirectional traces. Coherent filaments, not hash, and held at
        # 0.055 so they stay micro-texture: measured GRIT 0.118-0.269 against the
        # 0.62 fail line.
        pol = K.norm(K.streak(K.mid(shape, 3.4, seed + 23, octaves=1), 24, axis=1)) - 0.5

        relief = (rim * np.float32(P["rim_amp"])
                  - cone * np.float32(P["depth"])
                  - crk * np.float32(0.62)
                  + pit * facet
                  + pol * np.float32(0.055))
        return (relief.astype(np.float32), pit.astype(np.float32),
                np.clip(rim, 0, 1).astype(np.float32), np.clip(crk, 0, 1).astype(np.float32))

    return K.cache(("vickers", h, w, int(seed), _k(P)), build)


def paint_fl_hardness_indent(paint, shape, mask, seed, pm, bb):
    """Pyramid pits sunk into the painter's coupon — four lit facets each, the
    displaced metal standing proud around them, cracks out of the hard ones."""
    P = _P("fl_hardness_indent")
    src = K.incoming(paint, shape)
    relief, pit, rim, crk = _vickers(shape, seed, P)
    # Metal worked this hard tears its oxide and comes back a few degrees off the
    # polished land. Blended, never replaced: this technique images a flaw, it does
    # not emit its own colour, so the painter's base still owns the panel. (A
    # per-pixel phase into K.hue_rotate is the obvious one-call version and was
    # measured at 7.6s against 1.5s for the scalar phase plus this blend.)
    dw = np.clip(pit * 0.66 + rim * 0.44 + crk * 0.70, 0, 1)[:, :, None]
    src2 = src + (K.hue_rotate(src, np.float32(0.34)) - src) * dw
    lum = np.clip(1.0 + relief * float(pm), 0.18, 2.0)[:, :, None]
    return K.finish(src2 * lum, src, mask)


def spec_fl_hardness_indent(shape, seed, sm, base_m, base_r):
    """GRAMMAR: indent-vs-land duotone with a pile-up rim. Two materials far apart
    in every channel — a mirror-polished mounted coupon and a deformed, oxide-torn
    pit floor — plus the burnished lip as a thin third population, which is the one
    surface on the coupon glossier than the land. Every channel is driven off the
    SAME `relief` the paint modulated with and off relief's OWN terms, so FOLLOW is
    true by construction: measured 0.776-0.966 over all 10 samples against the 0.35
    floor. base_m/base_r are ignored deliberately — the coupon's material IS the
    finish, and a caller's flat defaults would collapse the duotone into one
    material and move this shelf's background off its assigned cell.
    """
    P = _P("fl_hardness_indent")
    relief, pit, rim, crk = _vickers(shape, seed, P)
    mod = K.norm(relief)                  # the EXACT field the paint modulated with
    # the duotone is cut from relief's OWN terms — pit and crack are both "not
    # polished land" and scatter the same way, so they deal the same material.
    sel = np.clip(pit * 1.6 + crk * 1.5, 0, 1)
    lip = np.clip(rim * 1.4, 0, 1)        # its pile-up term
    # LAND = M105 / R25 / CC16, a mounted, mirror-polished metallographic coupon.
    # Only the modulation is scaled by sm, so the land sits on the assigned cell at
    # any strength: measured median (105.0, 25.0, 16.0) at sm 0 and (101.8, 28.7,
    # 19.4) at sm 2, dominant material cell (2,0,0) over 51-71% of canvas throughout.
    M = np.clip(105.0 + (96.0 * lip - 70.0 * sel + 26.0 * (mod - 0.55)) * sm, 0, 255)
    R = np.clip(25.0 + (168.0 * sel - 16.0 * lip - 30.0 * (mod - 0.55)) * sm, 15, 255)
    CC = np.clip(16.0 + (58.0 * sel - 12.0 * lip + 15.0 * (0.60 - mod)) * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)



# ══════════════════════════════════════════════════════════════ CATALOG ══
CATALOG = {
    "fl_penetrant_bleed":  {"M": 20, "R": 150, "CC": 60,
                        "desc": "Penetrant Bleed — fluorescent dye wicking out of a cracked surface into a chalk developer"},
    "fl_magnetic_particle": {"M": 110, "R": 90, "CC": 30,
                             "desc": "Magnetic Particle — iron powder dragged along the flux leaking out of a crack in a magnetised part"},
    "fl_photoelastic_iso": {"M": 30, "R": 40, "CC": 20,
                            "desc": "Isochromatic Fringe — a stressed transparent model in a polariscope, its fringe order read out in spectral colour"},
    "fl_isoclinic_dark":   {"M": 25,  "R": 120, "CC": 130,
                            "desc": "Isoclinic Band — the dark loci where a principal stress axis lines up with the polariser"},
    "fl_moire_deflect":    {"M": 55,  "R": 70, "CC": 25,
                            "desc": "Moire Deflectometry — two Ronchi rulings crossed a few degrees, their beat contouring surface slope"},
    "fl_shearography":     {"M": 15,  "R": 190, "CC": 90,
                            "desc": "Shearography — laser shearing interferometry: correlation fringes riding a coherent speckle carrier, bent into a butterfly where a subsurface disbond bulges under load"},
    "fl_holo_interfero":   {"M": 75, "R": 35, "CC": 18,
                            "desc": "Holographic Interferogram — two exposures of a disbonded skin interfered, each ring one half-wavelength of out-of-plane bulge"},
    "fl_c_scan":          {"M": 10, "R": 200, "CC": 200,
                           "desc": "Ultrasonic C-Scan — gated echo amplitude, one sample per probe position, plotted pass by pass in the instrument's quantised false-colour palette"},
    "fl_a_scan_gate":      {"M": 45, "R": 160, "CC": 40,
                            "desc": "A-Scan Gate — ultrasonic echo trains stacked trace by trace, gate cursors bracketing the backwall echo"},
    "fl_radiograph_weld":  {"M": 5, "R": 175, "CC": 150,
                            "desc": "Weld Radiograph — X-ray film of a multipass weld overlay, gas porosity printing through the stacked-dime beads as evenly spaced voids"},
    "fl_ct_slice":         {"M": 35,  "R": 55, "CC": 95,
                            "desc": "CT Slice — a tomographic reconstruction read out with its own artifacts: rings thrown by drifted detector channels, star streaks thrown by dense metal"},
    "fl_eddy_impedance":   {"M": 130, "R": 60, "CC": 22,
                            "desc": "Eddy Current — the impedance-plane loop a probe's coil traces as it crosses a crack"},
    "fl_tsa_stress":       {"M": 18,  "R": 100, "CC": 45,
                            "desc": "Thermoelastic Stress — a lock-in IR camera's full-field map of the stress in a cyclically loaded part, dealt on the detector grid it was measured on"},
    "fl_pulse_thermo":     {"M": 8, "R": 130, "CC": 75,
                            "desc": "Pulse Thermography — a flash of heat, then the subsurface delaminations that hold it while sound material cools away"},
    "fl_acoustic_emission": {"M": 60,  "R": 110, "CC": 55,
                             "desc": "Acoustic Emission — a growing crack's own elastic bursts, triangulated by the sensor array and plotted as amplitude rings"},
    "fl_strain_rosette":   {"M": 165, "R": 46, "CC": 26,
                            "desc": "Strain Rosette — bonded foil strain gauges, three serpentine constantan grids etched per site on amber polyimide, reading the strain the eye cannot see"},
    "fl_brittle_lacquer":  {"M": 22, "R": 145, "CC": 105,
                            "desc": "Brittle Lacquer — a StressCoat test skin cracked across the tensile axis, the lines crowding tighter wherever the part is strained harder"},
    "fl_chladni": {"M": 40, "R": 165, "CC": 70, "desc": "Chladni Figure — fine test powder heaped on the nodal net of a plate driven at a high square-mode difference, the antinode bellies scoured back to bare metal"},
    "fl_phased_array":    {"M": 95, "R": 75, "CC": 34,
                       "desc": "Phased Array — a delay-steered beam swept through a fan of angles, every ray reading its own range gates"},
    "fl_schlieren": {"M": 60, "R": 96, "CC": 28, "desc": "Schlieren — Toepler's knife edge cut into the focal point of the test section, so the image is the DENSITY GRADIENT along one axis: directional light and shade over glass cords, never colour"},
    "fl_shadowgraph": {"M": 28, "R": 115, "CC": 62, "desc": "Shadowgraph — the second spatial derivative of gas density, where every shock front prints as a paired bright/dark rim"},
    "fl_crack_tip": {"M": 70, "R": 95, "CC": 40,
                     "desc": "Crack Tip Field — the butterfly plastic zone that yields around the tip of a fatigue crack"},
    "fl_barkhausen":      {"M": 150, "R": 120, "CC": 50,
                        "desc": "Barkhausen Noise — magnetic domain walls jumping in power-law avalanches as an applied field is swept across the steel"},
    "fl_macro_etch":       {"M": 85,  "R": 130, "CC": 36,
                            "desc": "Macro Etch — an etched and anodised forging section, where the acid attack reads out grain flow streaming around the die bosses and crowding where the metal was compressed"},
    "fl_hardness_indent":  {"M": 105, "R": 25, "CC": 16,
                            "desc": "Hardness Indent — a Vickers traverse of diamond pyramid indents, each ringed by its pile-up"},
}
FLAW_LAB = CATALOG          # convenience alias

SPACE = {
    "fl_penetrant_bleed":  {"cell_px": (10.5, 13.5), "arrest": (0.34, 0.58),
                        "bleed_px": (2.0, 5.0), "dye": (0.70, 1.90),
                        "chalk": (0.35, 0.70), "pores": (0.008, 0.030)},
    "fl_magnetic_particle": {"amp": (0.60, 1.70), "grain_px": (9.0, 15.0),
                             "step_px": (1.8, 3.0), "thresh": (0.58, 0.72),
                             "crowd": (0.12, 0.30), "cracks": [22, 34, 48]},
    "fl_photoelastic_iso": {"pitch": (14.0, 24.0), "amp": (0.55, 1.60), "disp": (0.35, 1.30),
                            "curl": (1.6, 3.6), "iso": (0.30, 0.70), "duty": (0.25, 0.50)},
    "fl_isoclinic_dark":   {"band_px": (14.0, 27.0), "orders": [3, 2, 4], "loads": [5, 4, 6],
                            "plate": (0.08, 0.40), "amp": (0.35, 1.45), "desat": (0.20, 0.85)},
    "fl_moire_deflect":    {"fringe": (10.5, 14.0), "pitch": (2.6, 3.0), "orders": (2.0, 5.0),
                            "dent": (0.4, 1.6), "amp": (0.80, 2.00), "bar_mix": (0.06, 0.20)},
    "fl_shearography":     {"grain": (6.0, 11.0), "pitch": (8.0, 14.0), "orders": (3.0, 8.0),
                            "bond": (0.40, 0.66), "spkl": (0.18, 0.55), "drive": (0.45, 1.55)},
    "fl_holo_interfero":   {"cell_px": (150.0, 265.0), "hub_px": (24.0, 36.0),
                            "rim_px": (12.0, 17.0), "depth": (0.45, 1.30),
                            "tint": (0.16, 0.52), "steps": [5, 4, 6, 7]},
    "fl_c_scan":          {"pitch": (10.0, 16.0), "rule": (0.30, 0.72), "gain": (0.45, 1.60),
                           "span": (1.00, 2.60), "emit": (0.06, 0.30), "steps": [8, 10, 12, 16]},
    "fl_a_scan_gate":      {"pitch": (15.0, 26.0), "sweep": (260.0, 460.0),
                            "pfrac": (0.24, 0.38), "wobble": (0.20, 0.42),
                            "trace": (7.0, 18.0), "gain": (1.80, 3.80)},
    "fl_radiograph_weld":  {"bead_px": (30.0, 44.0), "rip_px": (11.5, 15.5), "pitch": (24.0, 32.0),
                            "poros": (0.22, 0.55), "depth": (2.0, 4.4), "amp": (0.40, 1.45)},
    "fl_ct_slice":         {"ring_px": (26.0, 44.0), "lobes": (40.0, 72.0),
                            "streak": (0.35, 1.10), "mottle": (0.25, 0.95),
                            "gain": (0.35, 1.45), "hue": (0.0, 0.90)},
    "fl_eddy_impedance":   {"pitch": (14.0, 22.0), "thick": (1.5, 2.6), "open": (0.50, 0.95),
                            "span": (0.75, 2.30), "crack_px": (54.0, 112.0), "amp": (0.35, 1.20)},
    "fl_tsa_stress":       {"pitch": (10.5, 15.0), "stress": (0.28, 0.72), "fpn": (0.40, 1.25),
                            "fill": (0.12, 0.24), "gain": (0.40, 1.60), "blend": (0.18, 0.50)},
    "fl_pulse_thermo":     {"flaw_px": (14.0, 22.0), "thresh": (0.620, 0.700),
                            "frame": (0.55, 1.75), "sharp": (6.0, 16.0),
                            "amp": (0.45, 1.55), "depths": [6, 4, 8]},
    "fl_acoustic_emission": {"pitch": (24.0, 38.0), "ring_px": (4.6, 7.6), "sharp": (1.0, 2.0),
                             "gate": (0.28, 0.62), "gain": (0.62, 1.75), "span": (0.9, 2.6)},
    "fl_strain_rosette":   {"site_px": (96.0, 148.0), "trace_px": (11.5, 18.0),
                            "seg_px": (34.0, 62.0), "duty": (0.53, 0.66),
                            "amp": (0.50, 1.55), "strain": (0.10, 0.30)},
    "fl_brittle_lacquer":  {"space_px": (22.0, 30.0), "hair_px": (1.7, 2.9),
                            "bend": (2.5, 9.0), "site_px": (110.0, 190.0),
                            "riser": (0.20, 0.60), "amp": (0.85, 1.75)},
    "fl_chladni": {"pitch": (20.0, 25.0), "ratio": (0.38, 0.47), "tight": (1.05, 1.95), "amp": (0.45, 1.70), "dust": (0.14, 0.34), "grain_px": [22.0, 16.0, 28.0]},
    "fl_phased_array":    {"ray_px": (9.5, 14.0), "gate_px": (8.5, 13.0), "gain": (0.70, 1.75),
                       "thresh": (0.880, 0.975), "span": (0.40, 1.10), "steps": [9, 6, 12, 16]},
    "fl_schlieren": {"pitch": (10.0, 15.0), "wander": (18.0, 46.0), "sens": (0.95, 2.35), "turb": (0.25, 1.15), "tilt": (0.05, 0.55), "cut": (0.44, 0.56)},
    "fl_shadowgraph": {"pitch": (25.0, 34.0), "steps": [5, 4, 6, 7], "rim": (4.4, 6.2), "wmach": (0.75, 1.45), "eddy": (0.55, 0.95), "amp": (0.45, 1.60)},
    "fl_crack_tip": {"pitch": (28.0, 38.0), "zone": (0.24, 0.36), "depth": (1.45, 2.70),
                     "c0": (0.08, 0.34), "dorm": (0.10, 0.42), "slip": (0.15, 0.55)},
    "fl_barkhausen":      {"cell_px": (9.0, 12.5), "aspect": (1.45, 2.00), "gain": (2.6, 5.0),
                        "spike": (0.35, 1.45), "wall": (0.40, 0.75), "lance": (0.10, 0.28)},
    "fl_macro_etch":       {"pitch": (12.5, 16.0), "boss_px": (170.0, 330.0), "grain": (0.24, 0.42),
                            "depth": (0.80, 1.95), "tint": (0.30, 0.58), "wander": (90.0, 260.0)},
    "fl_hardness_indent":  {"pitch": (18.0, 26.0), "fill": (0.26, 0.38),
                            "depth": (0.30, 0.72), "rim_amp": (0.25, 1.15),
                            "light": (0.16, 0.42), "crack": (0.10, 0.62)},
}

_CHOSEN = chooser(__name__, SPACE)


def install(registry):
    """Wire FLAW LAB into a BASE_REGISTRY. Returns the number of finishes installed."""
    import sys as _sys
    me = _sys.modules[__name__]
    n = 0
    for fid, meta in CATALOG.items():
        entry = registry.setdefault(fid, {})
        entry.update(meta)
        entry["paint_fn"] = getattr(me, "paint_" + fid)
        entry["base_spec_fn"] = getattr(me, "spec_" + fid)
        n += 1
    return n
