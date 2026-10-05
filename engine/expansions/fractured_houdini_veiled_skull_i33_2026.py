"""H1-I33 — Veiled Skull / midnight filigree, pass 1.

SPB-H1 owner reset, 2026-08-31.  I32 was rejected because its regular little
reliquaries read as a tiled skull stamp.  This is an isolated replacement:
the neutral carrier is a continuous black-cobalt/plum filigree marble; the
recurring skulls are only fine, low-amplitude M/R/Cc inlays woven through it.
No RGB paint contains a skull, a box, or a printed mark.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_W = 768
_C: OrderedDict[tuple[int, int, int], tuple[np.ndarray, np.ndarray]] = OrderedDict()
_L = RLock()


def _filigree_field(seed: int):
    """Continuous purposeful vein/scroll carrier — never cellular or tiled."""
    yy, xx = np.mgrid[:_W, :_W].astype(np.float32)
    phase = float(seed) * .173
    # Three independently warped fine contour families create marble motion.
    # P11: replace I33's too-recognizable vertical flow with forged,
    # book-matched diagonal folds and their cross-cut filament work.
    u = yy*.73 + xx*.51 + 27*np.sin(xx*.027 - yy*.041 + phase) + 9*np.sin(xx*.081 + yy*.022)
    v = xx*.84 - yy*.38 + 21*np.sin(xx*.034 + yy*.019 - phase*.7) + 8*np.sin(xx*.018 - yy*.074)
    w = (xx*.42 + yy*.88) + 17*np.sin(xx*.029 - yy*.047 + phase*1.3)
    # P5: compress the visible carrier's old broad wallpaper cadence into
    # denser 8–32px-native contour and cross-filament families.
    a = np.abs(np.sin(u*.166 + .28*np.sin(v*.093)))
    b = np.abs(np.sin(v*.184 + .23*np.sin(w*.119)))
    c = np.abs(np.sin(w*.149 + .31*np.sin(u*.081)))
    # P6: a fourth warped diagonal filament interrupts the remaining vertical
    # bias without introducing a rigid grid or any random-pixel rescue.
    d = xx*.59 + yy*.81 + 15*np.sin(xx*.029-yy*.041+phase)
    e = xx*.89 - yy*.43 + 12*np.sin(xx*.052+yy*.021-phase)
    xline = np.abs(np.sin(d*.171 + .25*np.sin(e*.091)))
    cross = np.clip((.052-xline)/.052, 0, 1)
    # P16: P15's narrowest contour energy could collapse below the 8px-native
    # owner floor. These widths resolve to purposeful 8–20px-native filaments,
    # increasing density/readability without enlarging the carrier's topology.
    hair = np.clip((.29-a)/.29, 0, 1)
    thread = np.clip((.22-b)/.22, 0, 1)
    glint = np.clip((.16-c)/.16, 0, 1)
    cloud = .5 + .5*np.sin(u*.012 + np.sin(v*.017 + phase)*1.7)
    body = .5 + .5*np.sin(w*.019 - np.sin(u*.014)*1.25)
    # P18 deterministic carrier-state routing follows the existing folded
    # filaments; it is not a screen grid or stochastic grain.
    state = (np.floor(u/4.0).astype(np.int32) + 3*np.floor(v/5.0).astype(np.int32)
             + 5*np.floor(w/6.0).astype(np.int32)) % 8
    return xx, yy, hair, thread, glint, cross, cloud, body, state


def _veiled_anatomy(seed: int):
    """Thirty staggered ornamental skull inlays; every stroke is 3–10 work px.

    A complete motif spans an area so that a side/hood receives several
    opportunities to reveal it, but no motif is enclosed in a card or a grid.
    """
    line = np.zeros((_W, _W), np.uint8)
    hollow = np.zeros_like(line)
    crest = np.zeros_like(line)
    lace = np.zeros_like(line)
    tempo = np.zeros_like(line)
    rng = np.random.default_rng(3719 + int(seed)*71)
    # P2: I33-P1 still carried a faint row cadence in literal M/R/Cc proof.
    # Use deterministic blue-noise-like placement: full-canvas coverage without
    # columns, rows, or a repeated tile boundary.
    centers: list[tuple[int, int]] = []; attempts = 0
    while len(centers) < 32 and attempts < 12000:
        attempts += 1
        cx = int(rng.integers(30, _W-30)); cy = int(rng.integers(34, _W-34))
        if all((cx-px)**2 + (cy-py)**2 > 64**2 for px, py in centers):
            centers.append((cx, cy))
    if len(centers) < 30:
        raise RuntimeError('H1-I33 could not place enough non-grid inlays')
    for cx, cy in centers:
            sx = int(rng.integers(17, 22)); sy = int(sx*(1.18 + .08*rng.random()))
            ang = float(-20 + 40*rng.random())
            kind = int(rng.integers(0, 4))
            ca, sa = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
            def p(dx, dy):
                return (int(cx + dx*ca - dy*sa), int(cy + dx*sa + dy*ca))
            # Crown / cheekbones: thin engraved curves, not a silhouette stamp.
            cv2.ellipse(line, p(0, -.16*sy), (sx, max(8, int(.56*sy))), ang, 192, 348, 188, 3, cv2.LINE_AA)
            cv2.ellipse(line, p(0, .25*sy), (max(10, int(.82*sx)), max(7, int(.38*sy))), ang, 12, 169, 164, 3, cv2.LINE_AA)
            for sign in (-1, 1):
                cv2.ellipse(hollow, p(sign*.33*sx, -.08*sy), (max(4, sx//4), max(3, int(.20*sy))), ang, 0, 360, 215, -1, cv2.LINE_AA)
                # Small filigree curls extend into the marble rather than framing it.
                cv2.ellipse(lace, p(sign*1.00*sx, -.15*sy), (max(4, sx//3), max(3, sy//5)), ang+sign*30, 24, 202, 150, 3, cv2.LINE_AA)
                cv2.ellipse(lace, p(sign*.88*sx, .35*sy), (max(4, sx//4), max(3, sy//5)), ang+sign*43, 194, 355, 136, 3, cv2.LINE_AA)
            nose = np.asarray([p(0, .02*sy), p(-.15*sx, .20*sy), p(.15*sx, .20*sy)], np.int32)
            cv2.fillConvexPoly(hollow, nose, 183, lineType=cv2.LINE_AA)
            # Four fine teeth separate only under the opposite material state.
            for dx in (-.28*sx, -.09*sx, .09*sx, .28*sx):
                cv2.line(crest, p(dx, .29*sy), p(dx, .50*sy), 210, 3, cv2.LINE_AA)
            # A small crown glint shares the parent curve, never a halo box.
            cv2.ellipse(crest, p(0, -.35*sy), (max(5, sx//2), max(3, sy//5)), ang, 198, 342, 162, 3, cv2.LINE_AA)
            # P10: vary the fine relic anatomy.  These are not colour variants
            # or repeated stamps: each skull inherits one of four handwork-like
            # crown/forehead/cheek treatments, all M/R/Cc-only.
            if kind == 1:
                cv2.ellipse(lace, p(0, -.46*sy), (max(5, sx//2), max(3, sy//5)), ang, 205, 335, 151, 3, cv2.LINE_AA)
            elif kind == 2:
                gem = np.asarray([p(0, -.25*sy), p(-.12*sx, -.08*sy), p(0, .03*sy), p(.12*sx, -.08*sy)], np.int32)
                cv2.polylines(crest, [gem], True, 166, 3, cv2.LINE_AA)
            elif kind == 3:
                cv2.ellipse(lace, p(-.57*sx, .14*sy), (max(4, sx//4), max(3, sy//5)), ang-31, 12, 186, 149, 3, cv2.LINE_AA)
                cv2.ellipse(lace, p(.57*sx, .14*sy), (max(4, sx//4), max(3, sy//5)), ang+31, 194, 354, 149, 3, cv2.LINE_AA)
            # P13: every relic owns a different material tempo. This soft,
            # local strength field affects M/R/Cc only and makes discoveries
            # occur at different positions/angles rather than all at once.
            cv2.ellipse(tempo, (cx, cy), (sx+7, sy+8), ang, 0, 360, int(rng.integers(108, 246)), -1, cv2.LINE_AA)
    blur = lambda x, sigma: cv2.GaussianBlur(x.astype(np.float32)/255., (0, 0), sigma)
    return blur(line, .45), blur(hollow, .42), blur(crest, .38), blur(lace, .48), blur(tempo, 1.2)


def _master(seed: int):
    xx, yy, hair, thread, glint, cross, cloud, body, state = _filigree_field(seed)
    # P1 visible carrier: dark black-chrome marble with small cobalt/plum veins.
    # It must satisfy the category on its own before its material secret matters.
    # P7: P6 held together, but its neutral thumbnail was too dark to sell the
    # material.  Raise only the marble's cobalt/plum/silver *filaments*, never
    # the hidden anatomy, so the card reads as premium stone at a glance.
    dark = np.stack((.024+.040*cloud, .029+.047*body, .052+.078*cloud), axis=2)
    cobalt = np.stack((.030+.078*body, .082+.154*cloud, .166+.244*body), axis=2)
    plum = np.stack((.079+.132*cloud, .025+.047*body, .105+.177*cloud), axis=2)
    silver = np.stack((.28+.42*cloud, .36+.41*body, .54+.35*cloud), axis=2)
    vein = np.clip(.64*hair + .39*thread + .16*glint, 0, 1)
    # P8: deliberately test a richer black-cherry/cobalt body.  The dark
    # valleys remain black chrome; colour lives in the natural stone motion,
    # not in any hidden-symbol contrast.
    art = dark*.78 + cobalt*(.37+.24*body)[..., None] + plum*(.13+.16*cloud)[..., None]
    art += silver*(.19*hair + .135*thread + .065*cross + .052*glint)[..., None]
    art = np.clip(np.power(np.clip(art, 0, 1), .86), 0, 1).astype(np.float32)

    # P1 spec carrier: each visible vein family has its own material response.
    M = 38 + 92*cloud + 67*hair + 56*cross - 28*thread + 31*glint
    R = 196 - 76*body - 91*hair - 55*cross + 47*thread - 23*glint
    C = 29 + 118*body + 38*hair + 71*cross + 68*thread + 53*glint
    spec = np.dstack((M, R, C)).clip(0, 255).astype(np.float32)
    # P9: Foundry/Relics comparison showed that the marble was visually sound
    # but its underlying material deck lacked range.  Expand the *carrier*
    # around physical mid-state; no hidden-mask contrast is amplified here.
    spec = np.clip(127.5 + (spec-127.5)*1.36, 0, 255)
    # P18: every fine carrier filament carries one of eight adjacent physical
    # states. This makes the normal finish more alive under light while its RGB
    # paint remains a quiet continuous filigree rather than a tiled pattern.
    carrier = np.clip(.72*hair + .58*thread + .46*cross + .23*glint, 0, 1)
    carrier_cards = np.asarray(((218, 16, 228), (42, 208, 34),
                                (170, 66, 188), (92, 156, 82),
                                (232, 24, 48), (54, 192, 202),
                                (126, 112, 154), (198, 38, 218)), np.float32)
    csel = carrier > .20
    card = carrier_cards[state]
    strength = (.07 + .12*carrier)[..., None]
    spec[csel] = (1-strength[csel])*spec[csel] + strength[csel]*card[csel]

    line, hollow, crest, lace, tempo = _veiled_anatomy(seed)
    # P4: a skull cannot have its complete anatomy peak in one lighting event.
    # Segment each material family on a different fine, vein-aligned cadence.
    # The fragments are 3–10 work pixels long and only cohere as the physical
    # M/R/Cc states trade prominence at changing view/light angles.
    edge_gate = np.clip(.48 + .76*np.sin(xx*.238 + yy*.071 + seed*.19), 0, 1)
    hollow_gate = np.clip(.46 + .78*np.sin(xx*.107 - yy*.203 + seed*.31), 0, 1)
    tooth_gate = np.clip(.44 + .80*np.sin(xx*.181 + yy*.149 - seed*.23), 0, 1)
    curl_gate = np.clip(.51 + .70*np.sin(xx*.129 - yy*.114 + seed*.37), 0, 1)
    # P13 local strength turns the same four channel families into different
    # revelation tempos across the complete vehicle canvas.
    tempo = .46 + .54*tempo
    line *= edge_gate*tempo; hollow *= hollow_gate*tempo
    crest *= tooth_gate*tempo; lace *= curl_gate*tempo
    # P3: P2 placement solved the row cadence, but the stress diagnostic still
    # assembled each secret too easily.  Compress the offsets so it is a true
    # grazing relief, carried by the marble's own material motion—not a stamp.
    # Adjoining chrome/satin/clearcoat states make parts assemble differently
    # at grazing angles, while ordinary neutral viewing reads only filigree.
    edge = line > .24
    inner = hollow > .20
    tooth = crest > .26
    curl = lace > .24
    # P12: P11's sober material simulation successfully concealed the icon,
    # but over-concealed it. Increase only glancing-state separation; channel
    # gates still prevent a complete badge from appearing under one condition.
    # P14: P13 direct evidence measured only +18.75 response over the local
    # carrier. Increase chrome/clearcoat relief and retain opposing satin wells
    # so the secret has a meaningful grazing event without a uniform bright icon.
    # P17: P16's four-condition audit showed the carrier was still too
    # channel-correlated. Separate each anatomy family into real opposing
    # material cards so chrome, satin, and clearcoat conditions reveal a
    # different subset rather than one uniformly brighter skull.
    spec[edge] = .66*spec[edge] + .34*np.array((234, 12, 240), np.float32)
    spec[inner] = .66*spec[inner] + .34*np.array((12, 244, 16), np.float32)
    spec[tooth] = .62*spec[tooth] + .38*np.array((250,  4, 250), np.float32)
    spec[curl] = .70*spec[curl] + .30*np.array((58, 208, 54), np.float32)
    # P3: an 8px-native material weave lives inside all inlays without coloured
    # pixels, giving a hand-unrepeatable response instead of a flat icon.
    tx = np.floor(xx/3).astype(np.int32); ty = np.floor(yy/3).astype(np.int32)
    # P15: use an eight-state physical weave inside the secret itself.  These
    # are deliberately adjacent chrome/satin/clearcoat cards, never RGB noise,
    # so movement can discover different relic fragments in one lighting pass.
    weave = ((tx*7 + ty*11 + (tx//5)*3) % 8)
    inlay = np.maximum.reduce((line, hollow, crest, lace)) > .17
    deck = np.asarray(((238,  8, 244), ( 24, 226,  31),
                       (180, 58, 208), ( 78, 161,  82),
                       (226, 21,  42), ( 47, 192, 198),
                       (135, 96, 168), (205, 36, 224)), np.float32)
    mixed = deck[weave]
    spec[inlay] = .80*spec[inlay] + .20*mixed[inlay]
    return art, np.clip(spec, 0, 255).astype(np.uint8)


def _assets(shape, seed):
    h, w = map(int, shape); key = (h, w, int(seed))
    with _L:
        if key in _C:
            _C.move_to_end(key); return _C[key]
    art, spec = _master(seed)
    if (h, w) != (_W, _W):
        art = cv2.resize(art, (w, h), interpolation=cv2.INTER_AREA if max(h, w) < _W else cv2.INTER_LINEAR)
        spec = cv2.resize(spec, (w, h), interpolation=cv2.INTER_NEAREST)
    out = (art.astype(np.float32), spec.astype(np.uint8))
    with _L:
        _C[key] = out
        if len(_C) > 2: _C.popitem(last=False)
    return out


def paint_veiled_skull_i33(paint, shape, mask, seed, pm, bb):
    del bb
    art, _ = _assets(shape, seed); src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5: src = src/255.0
    m = np.asarray(mask, np.float32); m = m[..., 0] if m.ndim == 3 else m
    m = (np.clip(m, 0, 1)*pm)[..., None]
    return np.clip(src*(1-m) + art*m, 0, 1).astype(np.float32)


def spec_veiled_skull_i33(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    return _assets(shape, seed)[1]
