"""MULE — cars that do not want to be seen.

Owner mandate 2026-09-04: four new shelves, minimum 15 finishes each.

THE ARC
-------
Automotive PROTOTYPE DISGUISE, specifically: the visual language a manufacturer
uses to hide an unreleased car from a spy photographer. Erlkonig swirl vinyl,
cladding, false shutlines, camera-defeating moire, painted anti-form shading,
retroreflective flash traps. The subject is DEFEATING A CAMERA AND AN EYE.

WHY THIS SHELF, WITH EVIDENCE
-----------------------------
Deliberately NOT military camouflage — the catalog already holds woodland,
MARPAT, DPM, Kryptek, digital and dazzle (30 hits), and those were ruled off
limits when this shelf was scoped. Prototype-disguise vocabulary itself measured
near zero: swirl camo 0, prototype disguise 0, Erlkonig 0.

HOW IT WAS BUILT
----------------
Each finish was authored against `_authoring_contract.md` by a dedicated agent
and then audited against the same contract by a second one, because the contract
encodes measured facts that are not guessable — the exact SCALE annulus, the
fact that a blur can never be load-bearing, and that FOLLOW must be CONSTRUCTED
(the spec rebuilds the paint's own field through a shared cache key) rather than
reasoned about. Each finish then declares a knob SPACE, and
`scripts/spb_variant_search.py` renders and scores ten samples of it, writing the
winner to `mule_2026_params.json` with the full score table beside it — so "best of
ten" is checkable rather than asserted.
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


def _hash2(a, b, salt=0.0):
    """Per-cell pseudo-random in 0..1 from two integer lattice coords."""
    v = np.sin(a * 127.1 + b * 311.7 + salt) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)


# ═══════════════════════════════════════════════════════ 01 · ERLKONIG SWIRL ══
def _swirl(shape, seed, P):
    """The iconic prototype wrap: interlocking swirls printed to destroy curvature.

    Warp the plane hard enough that a simple field's contour CURLS BACK on itself,
    then threshold. The hard threshold is what makes it read as printed vinyl; a
    gradient version reads as smoke and fools nobody.
    """
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 3, float(P["warp"]), float(P["warp_px"]))
        f = K.norm(K.mid(shape, float(P["arm_px"]) * 2.0, seed + 5, octaves=2))
        # a second, rotated field turns simple blobs into interlocking arms
        g = 0.5 + 0.5 * np.sin((px * 0.7 + py * 0.7) / float(P["arm_px"]) + f * 9.0)
        sel = ((f * 0.55 + g * 0.45) > 0.5).astype(np.float32)
        return K.box(sel, 1)

    return K.cache(("mulsw", h, w, int(seed), _k(P)), build)


def paint_mul_erlkonig_swirl(paint, shape, mask, seed, pm, bb):
    """Black-and-white swirl vinyl, printed to make a shape unreadable."""
    P = _P("mul_erlkonig_swirl")
    src = K.incoming(paint, shape)
    sel = _swirl(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - 0.5 * k + k * sel[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_erlkonig_swirl(shape, seed, sm, base_m, base_r):
    """GRAMMAR: hard two-tone. Two printed inks, two flat materials, no gradient."""
    sel = _swirl(shape, seed, _P("mul_erlkonig_swirl"))
    M = np.clip(20.0 + 44.0 * sel * sm, 0, 255)
    R = np.clip(130.0 - 70.0 * sel, 15, 255)
    CC = np.clip(80.0 - 46.0 * sel, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 02 · CONFUSION BLOB ══
def _blobs(shape, seed, P):
    """High-contrast blobs in exactly THREE tones.

    Three flat tones is deliberate: it reads as printed vinyl, whereas a continuous
    field reads as organic camouflage, which is a different shelf and already in
    the catalog.
    """
    h, w = shape[:2]

    def build():
        f = K.norm(K.mid(shape, float(P["blob_px"]), seed + 7, octaves=2))
        return K.ladder(f, 3, 0.0, 1.0)

    return K.cache(("mulbl", h, w, int(seed), _k(P)), build)


def paint_mul_confusion_blob(paint, shape, mask, seed, pm, bb):
    """Blobs placed to sit across panel gaps so the eye cannot find the body line."""
    P = _P("mul_confusion_blob")
    src = K.incoming(paint, shape)
    t = _blobs(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - 0.5 * k + k * t[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_confusion_blob(shape, seed, sm, base_m, base_r):
    """GRAMMAR: domain-constant three-tone palette — each blob holds ONE flat value."""
    t = _blobs(shape, seed, _P("mul_confusion_blob"))
    M = np.clip(K.ladder(t, 3, 22.0, 96.0) * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - t, 3, 60.0, 170.0), 15, 255)
    CC = np.clip(K.ladder(1.0 - t, 3, 30.0, 96.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 03 · FAKE SHUTLINE ══
def _shutline(shape, seed, P):
    """Printed false panel gaps: a dark line with a bright lip on ONE side.

    The asymmetric pair is what sells it — a real gap has a shadow and a lit edge,
    and a symmetric line reads as a stripe instead.
    """
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 11, 10.0, 300.0)
        pitch = float(P["pitch"])
        ang = np.deg2rad(float(P["angle"]))
        u = px * np.cos(ang) + py * np.sin(ang)
        t = u / pitch
        f = (t - np.floor(t)) * pitch
        gap = np.clip(1.0 - np.abs(f - pitch * 0.5) / float(P["gap_px"]), 0, 1)
        lip = np.clip(1.0 - np.abs(f - pitch * 0.5 - float(P["gap_px"]) * 1.7)
                      / float(P["gap_px"]), 0, 1)
        k = float(P["depth"])
        return np.clip(1.0 - k * gap + 0.55 * k * lip, 0, 2).astype(np.float32)

    return K.cache(("mulsl", h, w, int(seed), _k(P)), build)


def paint_mul_shutline_fake(paint, shape, mask, seed, pm, bb):
    """False panel gaps printed at angles that contradict the real bodywork."""
    P = _P("mul_shutline_fake")
    src = K.incoming(paint, shape)
    mod = _shutline(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_shutline_fake(shape, seed, sm, base_m, base_r):
    """GRAMMAR: line-pair edge-driven — printed ink over wrap, so the gap is matte
    ink and the lip is where the film still shines."""
    mod = _shutline(shape, seed, _P("mul_shutline_fake"))
    m = K.norm(mod)
    M = np.clip(45.0 + 40.0 * m * sm, 0, 255)
    R = np.clip(120.0 - 74.0 * m, 15, 255)
    CC = np.clip(70.0 - 48.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════ 04 · FOAM CLADDING ══
def _foam(shape, seed, P):
    """Padding blocks taped over the body: quilted rectangles with sagging middles."""
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["block_px"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        fu, fv = u - iu - 0.5, v - iv - 0.5
        # rounded-rectangle block: a soft square with a domed middle
        blk = np.clip(1.0 - (np.abs(fu) ** 4 + np.abs(fv) ** 4) * 5.0, 0, 1)
        dome = np.clip(1.0 - (fu * fu + fv * fv) * 3.2, 0, 1)
        gap = 1.0 - blk
        strap = np.clip(1.0 - np.abs(fv) * float(P["strap"]), 0, 1)
        k = float(P["depth"])
        return (np.clip(1.0 + k * (0.62 * dome - 0.50 * gap - 0.34 * strap), 0, 2)
                .astype(np.float32), gap.astype(np.float32), strap.astype(np.float32))

    return K.cache(("mulfm", h, w, int(seed), _k(P)), build)


def paint_mul_foam_clad(paint, shape, mask, seed, pm, bb):
    """Blocks of padding foam strapped over the panels to bury a shape."""
    P = _P("mul_foam_clad")
    src = K.incoming(paint, shape)
    mod, gap, strap = _foam(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_foam_clad(shape, seed, sm, base_m, base_r):
    """GRAMMAR: three-material stack — open-cell foam, tape strap and shadow gap."""
    mod, gap, strap = _foam(shape, seed, _P("mul_foam_clad"))
    m = K.norm(mod)
    M = np.clip(15.0 + 26.0 * m * sm, 0, 255)
    R = np.clip(210.0 - 70.0 * m, 15, 255)
    CC = np.clip(140.0 - 66.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 05 · BUBBLE CLADDING ══
def _bubbles(shape, seed, P):
    """Protective bubble sheet: a regular lattice of air domes under a milky film.

    The highlight sits OFF CENTRE on every dome, because a sphere lit from one
    side does that, and a centred highlight is what makes CG bubbles look wrong.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        fu = (u - np.floor(u) - 0.5) * pitch
        fv = (v - np.floor(v) - 0.5) * pitch
        r = np.sqrt(fu * fu + fv * fv)
        rad = pitch * 0.42
        dome = np.clip(1.0 - (r / rad) ** 2, 0, 1)
        off = float(P["hi_off"]) * rad
        rh = np.sqrt((fu + off) ** 2 + (fv + off) ** 2)
        hi = np.clip(1.0 - rh / (rad * 0.45), 0, 1) ** 2
        k = float(P["depth"])
        return np.clip(0.62 + k * (0.62 * dome + 1.05 * hi), 0, 2).astype(np.float32), hi

    return K.cache(("mulbu", h, w, int(seed), _k(P)), build)


def paint_mul_bubble_clad(paint, shape, mask, seed, pm, bb):
    """Bubble sheet taped under a translucent cover film."""
    P = _P("mul_bubble_clad")
    src = K.incoming(paint, shape)
    mod, hi = _bubbles(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_bubble_clad(shape, seed, sm, base_m, base_r):
    """GRAMMAR: per-dome radial ramp — every bubble carries the SAME gloss gradient
    from its lit shoulder to its base, so the sheet reads as one repeated optic."""
    mod, hi = _bubbles(shape, seed, _P("mul_bubble_clad"))
    m = K.norm(mod)
    M = np.clip(25.0 + 40.0 * m * sm, 0, 255)
    R = np.clip(110.0 - 78.0 * m, 15, 255)
    CC = np.clip(95.0 - 62.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 06 · MOIRE DEFEAT ══
def _moire(shape, seed, P):
    """Two Ronchi gratings at a small relative angle: the BEAT is the weapon.

    Each grating is near the resolution floor, so a camera cannot resolve either —
    but their beat lands squarely in the visible band and turns to mush in a photo.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        per = float(P["grating_px"])
        a1 = np.deg2rad(float(P["angle"]))
        a2 = a1 + np.deg2rad(float(P["split"]))
        # beat period = per / (2 sin(split/2)); at the first build's 1.5-5 degree
        # split that came out ~115px, far above the car window. 14-34 degrees puts
        # the beat at 12-20px, which is the whole point of the finish.
        g1 = np.sign(np.sin((px * np.cos(a1) + py * np.sin(a1)) * (6.2832 / per)))
        g2 = np.sign(np.sin((px * np.cos(a2) + py * np.sin(a2)) * (6.2832 / per)))
        beat = (g1 * g2) * 0.5 + 0.5
        return np.clip(0.5 + float(P["depth"]) * (beat - 0.5), 0, 2).astype(np.float32)

    return K.cache(("mulmo", h, w, int(seed), _k(P)), build)


def paint_mul_moire_defeat(paint, shape, mask, seed, pm, bb):
    """A pattern tuned to alias in a sensor and ruin the photographer's day."""
    P = _P("mul_moire_defeat")
    src = K.incoming(paint, shape)
    mod = _moire(shape, seed, P)
    out = src * (0.55 + 0.90 * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_moire_defeat(shape, seed, sm, base_m, base_r):
    """GRAMMAR: beat-phase anisotropy — the two ink states differ in sheen along
    the grating axis, which is what makes the beat survive at a glancing angle."""
    mod = _moire(shape, seed, _P("mul_moire_defeat"))
    m = K.norm(mod)
    M = np.clip(35.0 + 50.0 * m * sm, 0, 255)
    R = np.clip(120.0 - 66.0 * m, 15, 255)
    CC = np.clip(60.0 - 38.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 07 · COUNTERSHADE ══
def _counter(shape, seed, P):
    """Tone painted to CANCEL the body's own shading, delivered as a halftone.

    A smooth inverted-form gradient is pure macro energy the SCALE gate discards,
    so the tone is carried by DOT SIZE on a fixed lattice — which is also how it
    would really be printed.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        tone = K.norm(K.mid(shape, 420.0, seed + 13, octaves=1))
        u, v = px / pitch, py / pitch
        fu = (u - np.floor(u) - 0.5) * pitch
        fv = (v - np.floor(v) - 0.5) * pitch
        r = np.sqrt(fu * fu + fv * fv)
        rad = pitch * (0.14 + 0.34 * tone)          # dot size carries the tone
        dot = np.clip((rad - r) / 1.3, 0, 1)
        return np.clip(1.0 - float(P["depth"]) * dot, 0, 2).astype(np.float32)

    return K.cache(("mulct", h, w, int(seed), _k(P)), build)


def paint_mul_countershade(paint, shape, mask, seed, pm, bb):
    """Shading painted backwards, so the form the eye expects is not there."""
    P = _P("mul_countershade")
    src = K.incoming(paint, shape)
    mod = _counter(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_countershade(shape, seed, sm, base_m, base_r):
    """GRAMMAR: halftone dot-size ramp — ink dot versus bare film, with the dot's
    coverage carrying the tone rather than its darkness."""
    mod = _counter(shape, seed, _P("mul_countershade"))
    m = K.norm(mod)
    M = np.clip(22.0 + 34.0 * m * sm, 0, 255)
    R = np.clip(150.0 - 80.0 * m, 15, 255)
    CC = np.clip(96.0 - 58.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 08 · FALSE SHADOW ══
def _false_shadow(shape, seed, P):
    """Airbrushed dark/light PAIRS that invent creases which are not there.

    A crease is a shadow with a highlight beside it. Painting the pair at an angle
    that contradicts the real panel is what makes a flat door look folded.
    """
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 17, 16.0, 260.0)
        pitch = float(P["pitch"])
        ang = np.deg2rad(float(P["angle"]))
        u = px * np.cos(ang) + py * np.sin(ang)
        t = (u / pitch)
        f = (t - np.floor(t)) - 0.5
        dark = np.clip(1.0 - np.abs(f + 0.16) * float(P["soft"]), 0, 1)
        light = np.clip(1.0 - np.abs(f - 0.16) * float(P["soft"]), 0, 1)
        k = float(P["depth"])
        return np.clip(1.0 - k * dark + 0.85 * k * light, 0, 2).astype(np.float32)

    return K.cache(("mulfs", h, w, int(seed), _k(P)), build)


def paint_mul_false_shadow(paint, shape, mask, seed, pm, bb):
    """Painted creases that are not there, hiding the ones that are."""
    P = _P("mul_false_shadow")
    src = K.incoming(paint, shape)
    mod = _false_shadow(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_false_shadow(shape, seed, sm, base_m, base_r):
    """GRAMMAR: bimodal soft pair — airbrushed tone on one film, so the material
    barely changes and only its lightness does. The subtlest spec on this shelf."""
    mod = _false_shadow(shape, seed, _P("mul_false_shadow"))
    m = K.norm(mod)
    M = np.clip(18.0 + 26.0 * m * sm, 0, 255)
    R = np.clip(150.0 - 40.0 * m, 15, 255)
    CC = np.clip(92.0 - 34.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════ 09 · QR SCRAMBLE ══
def _qr(shape, seed, P):
    """Machine-readable-looking code blocks: hard squares on a strict lattice.

    Two nested module sizes, because a real code has finder blocks that are whole
    multiples of its module — and it is that nesting, not the randomness, that
    makes it read as a code rather than as noise.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        m1 = float(P["module_px"])
        iu, iv = np.floor(px / m1), np.floor(py / m1)
        a = (_hash2(iu, iv, 3.1) > 0.5).astype(np.float32)
        m2 = m1 * 3.0
        ju, jv = np.floor(px / m2), np.floor(py / m2)
        b = (_hash2(ju, jv, 8.6) > 0.72).astype(np.float32)
        return np.clip(a * 0.72 + b * 0.28, 0, 1).astype(np.float32)

    return K.cache(("mulqr", h, w, int(seed), _k(P)), build)


def paint_mul_qr_scramble(paint, shape, mask, seed, pm, bb):
    """Dense code blocks: a pattern a camera reads and a person cannot."""
    P = _P("mul_qr_scramble")
    src = K.incoming(paint, shape)
    t = _qr(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - 0.5 * k + k * t[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_qr_scramble(shape, seed, sm, base_m, base_r):
    """GRAMMAR: nested block-count ladder — the two module scales deal two ink
    weights, so the spec has exactly as many levels as the print does."""
    t = _qr(shape, seed, _P("mul_qr_scramble"))
    M = np.clip(K.ladder(t, 4, 30.0, 92.0) * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - t, 4, 46.0, 150.0), 15, 255)
    CC = np.clip(K.ladder(1.0 - t, 3, 38.0, 92.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════ 10 · WIREFRAME PRINT ══
def _wire(shape, seed, P):
    """A printed mesh whose perspective contradicts the real body.

    The doubled lines matter: where two meshes overlap in the print, the line is
    twice as bright, and that is the detail that makes it look printed rather
    than modelled.
    """
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 19, 12.0, 340.0)
        c = float(P["cell_px"])
        ang = np.deg2rad(float(P["angle"]))
        u = (px * np.cos(ang) + py * np.sin(ang)) / c
        v = (-px * np.sin(ang) + py * np.cos(ang)) / c
        lu = np.clip(1.0 - np.abs(u - np.round(u)) * c / float(P["line_px"]), 0, 1)
        lv = np.clip(1.0 - np.abs(v - np.round(v)) * c / float(P["line_px"]), 0, 1)
        return np.clip(lu + lv, 0, 1).astype(np.float32)

    return K.cache(("mulwf", h, w, int(seed), _k(P)), build)


def paint_mul_wireframe(paint, shape, mask, seed, pm, bb):
    """A wireframe printed onto the car for a surface that does not exist."""
    P = _P("mul_wireframe")
    src = K.incoming(paint, shape)
    line = _wire(shape, seed, P)
    out = src * (0.86 - 0.30 * line[:, :, None] * float(pm))
    out = out + line[:, :, None] * float(P["glow"]) * float(pm)
    return K.finish(out, src, mask)


def spec_mul_wireframe(shape, seed, sm, base_m, base_r):
    """GRAMMAR: line-lattice duotone — printed line against bare film, two flat
    materials with nothing in between."""
    line = _wire(shape, seed, _P("mul_wireframe"))
    M = np.clip(60.0 + 90.0 * line * sm, 0, 255)
    R = np.clip(50.0 + 90.0 * (1.0 - line), 15, 255)
    CC = np.clip(26.0 + 60.0 * (1.0 - line), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 11 · MATTE COVER ══
def _matte(shape, seed, P):
    """The shelf's quiet member: a plain cover wrap and its own film tooth.

    Almost no colour contrast — the interest is the calendered tooth of the film
    plus the occasional seam where two panels of it meet.
    """
    h, w = shape[:2]

    def build():
        tooth = K.norm(K.streak(K.mid(shape, float(P["tooth_px"]), seed + 23, octaves=1),
                                4, axis=1))
        py, px = K.warp(shape, seed + 25, 20.0, 400.0)
        s = px / float(P["seam_px"])
        seam = np.clip(1.0 - np.abs(s - np.round(s)) * float(P["seam_px"]) / 2.0, 0, 1)
        k = float(P["depth"])
        return np.clip(1.0 - 0.5 * k + k * tooth - 0.30 * seam, 0, 2).astype(np.float32)

    return K.cache(("mulmt", h, w, int(seed), _k(P)), build)


def paint_mul_matte_cover(paint, shape, mask, seed, pm, bb):
    """A plain matte cover wrap, seams and all."""
    P = _P("mul_matte_cover")
    src = K.incoming(paint, shape)
    mod = _matte(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_matte_cover(shape, seed, sm, base_m, base_r):
    """GRAMMAR: smooth inverse-roughness — one material, its roughness following
    the tooth. Deliberately the flattest spec on the shelf."""
    mod = _matte(shape, seed, _P("mul_matte_cover"))
    m = K.norm(mod)
    M = np.clip(10.0 + 18.0 * m * sm, 0, 255)
    R = np.clip(215.0 - 40.0 * m, 15, 255)
    CC = np.clip(160.0 - 34.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 12 · RETRO PATCH ══
def _retro(shape, seed, P):
    """Retroreflective patches that blow out white under a flash.

    Two populations with a HARD boundary: glass-bead film, which is a dense lattice
    of tiny lenses, and ordinary matte wrap, which is nothing at all.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        region = (K.norm(K.mid(shape, float(P["patch_px"]), seed + 27, octaves=2))
                  > float(P["cover"])).astype(np.float32)
        pitch = float(P["bead_px"])
        fu = (px / pitch - np.floor(px / pitch) - 0.5) * pitch
        fv = (py / pitch - np.floor(py / pitch) - 0.5) * pitch
        r = np.sqrt(fu * fu + fv * fv)
        bead = np.clip(1.0 - r / (pitch * 0.38), 0, 1) ** 2
        k = float(P["depth"])
        return np.clip(0.72 + k * bead * region, 0, 2).astype(np.float32), region

    return K.cache(("mulrt", h, w, int(seed), _k(P)), build)


def paint_mul_retro_patch(paint, shape, mask, seed, pm, bb):
    """Glass-bead patches that turn a photographer's flash into a white void."""
    P = _P("mul_retro_patch")
    src = K.incoming(paint, shape)
    mod, region = _retro(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_retro_patch(shape, seed, sm, base_m, base_r):
    """GRAMMAR: dual population — bead film is a mirror lattice, matte wrap is not,
    and the boundary between them is hard because it is a cut edge."""
    mod, region = _retro(shape, seed, _P("mul_retro_patch"))
    m = K.norm(mod)
    M = np.clip(30.0 + 190.0 * m * sm, 0, 255)
    R = np.clip(180.0 - 150.0 * m, 15, 255)
    CC = np.clip(90.0 - 70.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════ 13 · TAPE SEAM ══
def _tape(shape, seed, P):
    """Gaffer strips crossing the body, with FRAYED edges.

    Gaffer tape tears along its weave, so the edge is fibrous rather than clean —
    that fray is the difference between gaffer and vinyl.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        fray = (K.norm(K.mid(shape, 5.0, seed + 29, octaves=1)) - 0.5) * float(P["fray"])
        acc = np.zeros((h, w), np.float32)
        for i, ang in enumerate((18.0, 74.0, 132.0)):
            a = np.deg2rad(ang + float(P["angle"]))
            u = (px * np.cos(a) + py * np.sin(a)) / float(P["pitch"]) + fray
            f = np.abs(u - np.round(u))
            acc = np.maximum(acc, np.clip(1.0 - f * float(P["width"]), 0, 1))
        k = float(P["depth"])
        return np.clip(1.0 - k * acc, 0, 2).astype(np.float32), acc

    return K.cache(("multp", h, w, int(seed), _k(P)), build)


def paint_mul_tape_seam(paint, shape, mask, seed, pm, bb):
    """Gaffer tape holding the disguise on, crossing at whatever angle worked."""
    P = _P("mul_tape_seam")
    src = K.incoming(paint, shape)
    mod, acc = _tape(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_tape_seam(shape, seed, sm, base_m, base_r):
    """GRAMMAR: strip duotone with a fibrous edge — cloth tape and film are two
    materials, and cloth is the matte one."""
    mod, acc = _tape(shape, seed, _P("mul_tape_seam"))
    m = K.norm(mod)
    M = np.clip(28.0 + 30.0 * m * sm, 0, 255)
    R = np.clip(200.0 - 76.0 * m, 15, 255)
    CC = np.clip(120.0 - 56.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 14 · PIXEL BREAK ══
def _pixel(shape, seed, P):
    """Disruption at TWO block scales at once.

    One block size is decoration. Two — large blocks broken by smaller ones along
    their edges — is what actually destroys the read of a depth cue, which is why
    every digital disruption pattern in the world is built this way.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        big = float(P["block_px"])
        iu, iv = np.floor(px / big), np.floor(py / big)
        a = _hash2(iu, iv, 4.7)
        small = big * 0.5
        ju, jv = np.floor(px / small), np.floor(py / small)
        b = _hash2(ju, jv, 9.2)
        edge = ((np.abs(px / big - iu - 0.5) > 0.32) |
                (np.abs(py / big - iv - 0.5) > 0.32)).astype(np.float32)
        t = a * (1.0 - edge) + b * edge
        return K.ladder(t, 3, 0.0, 1.0)

    return K.cache(("mulpx", h, w, int(seed), _k(P)), build)


def paint_mul_pixel_break(paint, shape, mask, seed, pm, bb):
    """Blocks inside blocks, sized to destroy the eye's depth cues."""
    P = _P("mul_pixel_break")
    src = K.incoming(paint, shape)
    t = _pixel(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - 0.5 * k + k * t[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_pixel_break(shape, seed, sm, base_m, base_r):
    """GRAMMAR: two-scale block ladder — three flat tones, and the SMALL blocks
    take the same three, so the two scales deal from one deck."""
    t = _pixel(shape, seed, _P("mul_pixel_break"))
    M = np.clip(K.ladder(t, 3, 34.0, 110.0) * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - t, 3, 50.0, 140.0), 15, 255)
    CC = np.clip(K.ladder(t, 3, 42.0, 96.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════ 15 · DECOY BLACKOUT ══
def _blackout(shape, seed, P):
    """Badges and lamps taped out so the shapes read as voids.

    A void with a bright tape outline and a soft adhesive halo — the outline is
    what stops it reading as a hole and starts it reading as something covered.
    """
    h, w = shape[:2]

    def build():
        f = K.norm(K.mid(shape, float(P["void_px"]), seed + 31, octaves=2))
        void = (f > float(P["cover"])).astype(np.float32)
        soft = K.box(void, 2)
        outline = np.clip(np.abs(void - soft) * 3.4, 0, 1)
        halo = np.clip(K.box(void, 4) - void, 0, 1)
        k = float(P["depth"])
        return (np.clip(1.0 - k * void + 1.10 * k * outline - 0.22 * halo, 0, 2)
                .astype(np.float32), outline.astype(np.float32))

    return K.cache(("mulbo", h, w, int(seed), _k(P)), build)


def paint_mul_decoy_blackout(paint, shape, mask, seed, pm, bb):
    """Badges and lights blacked out and outlined, so the car has no face."""
    P = _P("mul_decoy_blackout")
    src = K.incoming(paint, shape)
    mod, outline = _blackout(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_decoy_blackout(shape, seed, sm, base_m, base_r):
    """GRAMMAR: region void duotone with an outline — three materials, but the
    third one exists only on a 2px boundary."""
    mod, outline = _blackout(shape, seed, _P("mul_decoy_blackout"))
    m = K.norm(mod)
    M = np.clip(12.0 + 34.0 * m * sm, 0, 255)
    R = np.clip(190.0 - 90.0 * m, 15, 255)
    CC = np.clip(140.0 - 78.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 16 · EDGE CHAMFER ══
def _chamfer(shape, seed, P):
    """Printed false chamfers: a hard bright top edge falling to a soft dark base.

    Asymmetry is the mechanism. A real chamfer catches light on its upper facet
    and loses it on the lower one, so a symmetric ramp reads as a stripe and an
    asymmetric one reads as a fold.
    """
    h, w = shape[:2]

    def build():
        py, px = K.warp(shape, seed + 33, 14.0, 280.0)
        pitch = float(P["pitch"])
        ang = np.deg2rad(float(P["angle"]))
        u = px * np.cos(ang) + py * np.sin(ang)
        t = u / pitch
        f = t - np.floor(t)
        top = np.clip(1.0 - f * float(P["hard"]), 0, 1)          # hard lit edge
        fall = np.clip((f - 0.12) / 0.88, 0, 1) ** float(P["curve"])
        k = float(P["depth"])
        return np.clip(1.0 + k * (0.85 * top - 0.55 * fall), 0, 2).astype(np.float32)

    return K.cache(("mulch", h, w, int(seed), _k(P)), build)


def paint_mul_edge_chamfer(paint, shape, mask, seed, pm, bb):
    """Fake creases printed onto flat panels at contradicting angles."""
    P = _P("mul_edge_chamfer")
    src = K.incoming(paint, shape)
    mod = _chamfer(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_mul_edge_chamfer(shape, seed, sm, base_m, base_r):
    """GRAMMAR: directional ramp with a hard top edge — the lit facet is polished
    film and the falling face is printed ink, so the two differ in gloss."""
    mod = _chamfer(shape, seed, _P("mul_edge_chamfer"))
    m = K.norm(mod)
    M = np.clip(38.0 + 46.0 * m * sm, 0, 255)
    R = np.clip(130.0 - 84.0 * m, 15, 255)
    CC = np.clip(78.0 - 50.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)



# ══════════════════════════════════════════════════════════════ CATALOG ══
CATALOG = {
    "mul_erlkonig_swirl": {"M": 20,  "R": 95,  "CC": 40,
                           "desc": "Erlkonig Swirl — the swirl vinyl that makes a shape unreadable"},
    "mul_confusion_blob": {"M": 30,  "R": 120, "CC": 55,
                           "desc": "Confusion Blob — printed blobs laid across the panel gaps"},
    "mul_shutline_fake":  {"M": 45,  "R": 60,  "CC": 25,
                           "desc": "Fake Shutline — false panel gaps printed at contradicting angles"},
    "mul_foam_clad":      {"M": 15,  "R": 175, "CC": 85,
                           "desc": "Foam Cladding — padding blocks strapped over the bodywork"},
    "mul_bubble_clad":    {"M": 25,  "R": 70,  "CC": 60,
                           "desc": "Bubble Cladding — bubble sheet taped under a cover film"},
    "mul_moire_defeat":   {"M": 35,  "R": 85,  "CC": 30,
                           "desc": "Moire Defeat — two gratings whose beat aliases in a camera"},
    "mul_countershade":   {"M": 22,  "R": 110, "CC": 48,
                           "desc": "Countershade — shading painted backwards to cancel the form"},
    "mul_false_shadow":   {"M": 18,  "R": 130, "CC": 70,
                           "desc": "False Shadow — creases invented in paint, real ones erased"},
    "mul_qr_scramble":    {"M": 40,  "R": 100, "CC": 38,
                           "desc": "QR Scramble — code blocks a sensor reads and an eye cannot"},
    "mul_wireframe":      {"M": 60,  "R": 50,  "CC": 26,
                           "desc": "Wireframe Print — a printed mesh for a surface that is not there"},
    "mul_matte_cover":    {"M": 10,  "R": 205, "CC": 150,
                           "desc": "Matte Cover — a plain cover wrap, its tooth and its seams"},
    "mul_retro_patch":    {"M": 175, "R": 35,  "CC": 18,
                           "desc": "Retro Patch — glass-bead film that turns a flash into a void"},
    "mul_tape_seam":      {"M": 28,  "R": 160, "CC": 75,
                           "desc": "Tape Seam — gaffer strips holding the disguise on"},
    "mul_pixel_break":    {"M": 50,  "R": 90,  "CC": 42,
                           "desc": "Pixel Break — blocks inside blocks, killing the depth cues"},
    "mul_decoy_blackout": {"M": 12,  "R": 145, "CC": 95,
                           "desc": "Decoy Blackout — badges and lamps taped out to voids"},
    "mul_edge_chamfer":   {"M": 38,  "R": 65,  "CC": 34,
                           "desc": "Edge Chamfer — false creases printed onto flat panels"},
}

SPACE = {
    "mul_erlkonig_swirl": {"arm_px": (9.0, 16.0), "warp": (18.0, 46.0), "warp_px": (60.0, 150.0),
                           "depth": (0.70, 1.45)},
    "mul_confusion_blob": {"blob_px": (10.0, 18.0), "depth": (0.65, 1.40)},
    "mul_shutline_fake":  {"pitch": (11.0, 20.0), "gap_px": (1.4, 3.0), "angle": (0.0, 180.0),
                           "depth": (0.60, 1.40)},
    "mul_foam_clad":      {"block_px": (11.0, 19.0), "strap": (2.0, 5.0), "depth": (0.60, 1.35)},
    "mul_bubble_clad":    {"pitch": (11.0, 18.0), "hi_off": (0.20, 0.46), "depth": (0.85, 1.70)},
    "mul_moire_defeat":   {"grating_px": (4.0, 8.0), "split": (14.0, 34.0), "angle": (0.0, 180.0),
                           "depth": (0.60, 1.30)},
    "mul_countershade":   {"pitch": (10.0, 16.0), "depth": (0.60, 1.35)},
    "mul_false_shadow":   {"pitch": (12.0, 20.0), "soft": (2.4, 5.5), "angle": (0.0, 180.0),
                           "depth": (0.55, 1.25)},
    "mul_qr_scramble":    {"module_px": (7.0, 13.0), "depth": (0.65, 1.40)},
    "mul_wireframe":      {"cell_px": (11.0, 19.0), "line_px": (1.4, 3.0), "angle": (0.0, 90.0),
                           "glow": (0.10, 0.34)},
    "mul_matte_cover":    {"tooth_px": (7.0, 13.0), "seam_px": (90.0, 200.0), "depth": (0.55, 1.30)},
    "mul_retro_patch":    {"patch_px": (40.0, 90.0), "cover": (0.42, 0.62), "bead_px": (7.0, 12.0),
                           "depth": (0.60, 1.40)},
    "mul_tape_seam":      {"pitch": (13.0, 24.0), "width": (2.2, 5.0), "fray": (0.05, 0.20),
                           "angle": (0.0, 60.0), "depth": (0.55, 1.25)},
    "mul_pixel_break":    {"block_px": (11.0, 20.0), "depth": (0.65, 1.40)},
    "mul_decoy_blackout": {"void_px": (13.0, 24.0), "cover": (0.48, 0.66), "depth": (0.60, 1.30)},
    "mul_edge_chamfer":   {"pitch": (11.0, 19.0), "hard": (5.0, 12.0), "curve": (0.7, 2.0),
                           "angle": (0.0, 180.0), "depth": (0.60, 1.35)},
}

_CHOSEN = chooser(__name__, SPACE)


def install(registry):
    """Wire this shelf into a BASE_REGISTRY. Returns the number installed."""
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
