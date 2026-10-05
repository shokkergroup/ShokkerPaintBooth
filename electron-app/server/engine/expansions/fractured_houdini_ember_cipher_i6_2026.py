"""FRACTURED HOUDINI H2-I6 — Ember Cipher, isolated P1 candidate.

Owner directive, 2026-08-31: rebuild one Houdini card from zero.  This is not
an RGB flame treatment.  The visible finish is a smoked-copper damascene
lacquer built from fine forged curls, anneal seams, mica pinwork and blackened
recesses.  Repeated ember glyphs are M/R/Cc substitutions only; every glyph is
assembled from 8–32px-native strokes and is distributed across the full car
canvas rather than being one large central icon.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _fract(a: np.ndarray) -> np.ndarray:
    return a - np.floor(a)


def _ink(mask: np.ndarray, pts: list[tuple[float, float]], value: int, width: int) -> None:
    cv2.polylines(mask, [np.rint(pts).astype(np.int32)], False, value, width, cv2.LINE_AA)


def _authored(shape: tuple[int, int], seed: int) -> tuple[np.ndarray, np.ndarray]:
    h, w = map(int, shape)
    scale = min(1.0, 1024.0 / max(h, w))
    hh, ww = max(128, round(h * scale)), max(128, round(w * scale))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    phase = (int(seed) % 4093) * .00419
    rng = np.random.default_rng(int(seed) ^ 0xE2C1)

    # A non-tiled forge field.  The subtle long flow only positions small
    # authored events; it is never allowed to become a broad wallpaper stripe.
    # P2 / owner-eye correction: P1's wide state ramps became loud contour
    # wallpaper in the material view.  Keep only a quiet, fine-scale patina
    # drift; the authored curls themselves now carry almost all visible rhythm.
    flow = (.50 + .08*np.sin(x/11.7 + np.sin(y/15.1 + phase))
            + .06*np.cos((.67*x + .31*y)/17.3 - phase)
            + .04*np.sin((x-y)/23.9 + phase*.6))
    forge = np.zeros((hh, ww), np.uint8)
    hair = np.zeros((hh, ww), np.uint8)
    mica = np.zeros((hh, ww), np.uint8)
    oxide = np.zeros((hh, ww), np.uint8)
    # P3: a quiet nonperiodic anneal variation supports the authored marks;
    # unlike P2's procedural state lattice, this can never resolve as fabric.
    anneal_noise = rng.standard_normal((hh, ww)).astype(np.float32)
    anneal_noise = cv2.GaussianBlur(anneal_noise, (0, 0), 4.2)
    anneal_noise = (anneal_noise-anneal_noise.min())/(np.ptp(anneal_noise)+1e-6)
    # P1 carrier vocabulary: irregular 8–28px native curls, split seams and
    # mica stitches.  They are intentionally phase-broken, not a repeated grid.
    # P5: picker-scale review showed that P4 had the right *kind* of mark but
    # too few of them.  Increase density, never primitive size.
    for _ in range(max(1900, int(hh*ww/540))):
        cx, cy = rng.uniform(-18, ww+18), rng.uniform(-18, hh+18)
        rx, ry = rng.uniform(3.8, 10.2), rng.uniform(2.4, 7.5)
        a0 = rng.uniform(0, 2*np.pi); sweep = rng.uniform(.72, 2.35)
        theta = np.linspace(a0, a0+sweep, 9)
        pts = np.column_stack((cx + rx*np.cos(theta), cy + ry*np.sin(theta)))
        _ink(forge, pts, int(rng.integers(84, 218)), int(rng.integers(1, 3)))
        if rng.random() < .28:
            _ink(oxide, pts[2:7], int(rng.integers(105, 215)), 1)
        if rng.random() < .62:
            cut = theta[2:7] + rng.uniform(-.22, .22)
            pts2 = np.column_stack((cx + rx*.56*np.cos(cut), cy + ry*.56*np.sin(cut)))
            _ink(hair, pts2, int(rng.integers(96, 224)), 1)
        if rng.random() < .42:
            cv2.circle(mica, (round(cx + rx*.76*np.cos(a0+sweep*.5)), round(cy + ry*.76*np.sin(a0+sweep*.5))), int(rng.integers(1, 3)), int(rng.integers(110, 255)), -1, cv2.LINE_AA)

    # P6: replace P5's all-over random-curl read with deliberately authored
    # damascene sweepwork.  Each sweep is a chain of 8–16px-native dashes and
    # fine inner stitches, so composition comes from the path—not macro art.
    for _ in range(max(165, int(hh*ww/8700))):
        cx, cy = rng.uniform(-40, ww+40), rng.uniform(-25, hh+25)
        span, amp = rng.uniform(24, 58), rng.uniform(6, 16)
        angle = rng.uniform(-.72, .72); sign = rng.choice((-1., 1.))
        rot=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]],np.float32)
        ts=np.linspace(-1.,1.,15)
        local=np.column_stack((ts*span, sign*amp*np.sin(ts*np.pi*.92)+ts*ts*sign*amp*.27))
        curve=local@rot.T+np.array([cx,cy],np.float32)
        for a,b in zip(curve[::2][:-1],curve[::2][1:]):
            cv2.line(forge,tuple(np.rint(a).astype(int)),tuple(np.rint(b).astype(int)),int(rng.integers(96,210)),int(rng.integers(2,4)),cv2.LINE_AA)
        inner=curve[2:-2:3]
        for a,b in zip(inner[:-1],inner[1:]):
            cv2.line(hair,tuple(np.rint(a).astype(int)),tuple(np.rint(b).astype(int)),int(rng.integers(120,226)),1,cv2.LINE_AA)
        if rng.random() < .38:
            for a,b in zip(curve[3:10:2],curve[5:12:2]):
                cv2.line(oxide,tuple(np.rint(a).astype(int)),tuple(np.rint(b).astype(int)),int(rng.integers(115,220)),1,cv2.LINE_AA)
        for a in curve[3:-3:4]:
            cv2.circle(mica,tuple(np.rint(a).astype(int)),int(rng.integers(1,3)),int(rng.integers(135,255)),-1,cv2.LINE_AA)

    # Twenty-eight repeated, varied fire-glyph opportunities.  A glyph has no
    # paint effect: it is a broken local material state made from small tongues,
    # inner licks and ember beads nested inside the carrier's own micro-work.
    secret = np.zeros((hh, ww), np.uint8)
    glyph_state = np.zeros((hh, ww), np.uint8)
    # P15: retain the smaller 14–22px construction but stop treating every
    # discovery as equal visual punctuation.  Thirty-two is enough to land on
    # several car panels while preserving quiet areas in the forged surface.
    count = max(32, int(hh*ww/32000))
    for n in range(count):
        cx, cy = rng.uniform(28, ww-28), rng.uniform(30, hh-30)
        s = rng.uniform(7.2, 11.2); lean = rng.uniform(-.42, .42)
        # A flame is three tapered curved strokes, all only 2–7px authored
        # (4–14px on a 2048 carrier), plus 4–10px native ember nodes.
        base = np.array([[0, .90], [-.48, .35], [-.25, -.20], [lean, -.88], [.23, -.10], [.48, .34], [0, .90]], np.float32)
        inner = np.array([[0, .67], [-.21, .23], [lean*.45, -.42], [.22, .20], [0, .67]], np.float32)
        side = np.array([[-.18, .65], [-.62, .04], [-.42, -.44], [-.03, -.13]], np.float32)
        angle = rng.uniform(-.42, .42); rot = np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]], np.float32)
        def p(path: np.ndarray) -> np.ndarray:
            return path @ rot.T * s + np.array([cx, cy], np.float32)
        strength = int(96 + (n % 8) * 19)
        # P10: every secret stroke has a mundane counterpart in the visible
        # damascene vocabulary.  In neutral paint these are simply more curls,
        # stitches and ember beads; only their changed M/R/Cc personality can
        # ever connect them into a flame discovery.
        _ink(forge, p(base), int(rng.integers(72, 168)), int(rng.integers(1, 3)))
        _ink(hair, p(inner), int(rng.integers(92, 176)), 1)
        _ink(hair, p(side), int(rng.integers(78, 154)), 1)
        _ink(secret, p(base), strength, int(rng.integers(1, 3)))
        _ink(secret, p(inner), min(255, strength+34), 1)
        _ink(secret, p(side), max(70, strength-23), 1)
        state = (n*5 + int(seed) + rng.integers(0,8)) % 8
        beads = p(np.array([[-.18,.49],[.20,.38],[0,.08]],np.float32))
        for px, py in beads:
            cv2.circle(secret, (round(px), round(py)), int(rng.integers(1,3)), min(255, strength+50), -1, cv2.LINE_AA)
        # P15: each component receives a neighbouring physical card—outer rim,
        # hot core, side lobe, and ember beads.  That is the dense local state
        # choreography the owner requested, without adding pigment or size.
        # Later glyphs can still interleave with earlier marks at crossings.
        delta = np.zeros_like(secret); _ink(delta, p(base), int(state+1), int(rng.integers(1,3)))
        _ink(delta, p(inner), int((state+3)%8+1), 1)
        _ink(delta, p(side), int((state+5)%8+1), 1)
        for px, py in beads:
            cv2.circle(delta, (round(px), round(py)), int(rng.integers(1,3)), int((state+7)%8+1), -1, cv2.LINE_AA)
        glyph_state = np.where(delta > 0, delta, glyph_state)

    curls = forge.astype(np.float32)/255.0
    seams = hair.astype(np.float32)/255.0
    sparks = mica.astype(np.float32)/255.0
    oxid = oxide.astype(np.float32)/255.0
    # P4: soft relief belongs to each tiny forged event.  It enlarges neither
    # the primitive nor the secret; it simply lets fine work catch light.
    relief = cv2.GaussianBlur(np.maximum(curls, seams*.82), (0, 0), 2.15)
    # P8: cool oxidized pools live underneath the copper work.  Their edges
    # are dictated by the same local anneal field, so this remains metalwork,
    # not a broad blue/green graphic layer.
    cool_pool = np.clip((anneal_noise-.58)*2.35, 0, 1) * (1-np.clip(relief*1.3,0,1))
    smoke = np.clip(flow, 0, 1)
    coal = np.array((.115, .038, .038), np.float32)
    oxblood = np.array((.455, .105, .042), np.float32)
    copper = np.array((.820, .245, .075), np.float32)
    rose_gold = np.array((.930, .470, .170), np.float32)
    pearl = np.array((1.00, .740, .360), np.float32)
    paint = coal[None,None,:]*(.54+.17*smoke[...,None]) + oxblood[None,None,:]*(.46+.26*smoke[...,None])
    paint = paint*(1-(relief*.33)[...,None]) + copper[None,None,:]*(relief*.33)[...,None]
    paint = paint*(1-(curls*.66)[...,None]) + copper[None,None,:]*(curls*.66)[...,None]
    paint = paint*(1-(seams*.52)[...,None]) + rose_gold[None,None,:]*(seams*.52)[...,None]
    paint = paint*(1-(sparks*.56)[...,None]) + pearl[None,None,:]*(sparks*.56)[...,None]
    # P7: these are genuine patina seams, not secret geometry.
    paint = paint*(1-(oxid*.62)[...,None]) + np.array((.020,.078,.082),np.float32)[None,None,:]*(oxid*.62)[...,None]
    paint = paint*(1-(cool_pool*.46)[...,None]) + np.array((.026,.115,.120),np.float32)[None,None,:]*(cool_pool*.46)[...,None]

    # P14 restores P12's healthy carrier breadth after P13's satin experiment
    # fell below direct spread.  The size/density change above—not a broad
    # state flattening—is the isolated variable under review this pass.
    metal=83 + smoke*38 + anneal_noise*30 + relief*51 + curls*68 + seams*43 + sparks*74 - oxid*28 - cool_pool*23
    rough=191 - smoke*34 - anneal_noise*28 - relief*49 - curls*65 - seams*45 - sparks*69 + oxid*31 + cool_pool*26
    coat=61 + smoke*40 + anneal_noise*31 + relief*58 + curls*75 + seams*48 + sparks*83 - oxid*26 - cool_pool*22
    # P12 — owner Houdini rebuild / SPB RGB Spec Encyclopedia: replace the
    # earlier arbitrary tuple ladder with eight named, physically distinct
    # production neighborhoods.  Adjacent 4–14px strokes can now trade dark
    # chrome, satin, candy, pearl, frozen metal, patina, dead recess and a
    # restrained Fractured carrier as the light travels.  This is the desired
    # "different spec next to different spec" event, not RGB recoloring.
    inside = secret > 0
    q = np.mod(np.maximum(glyph_state, 1)-1, 8)
    sm=np.array([250,250,200,100,225,80,8,252],np.float32)
    sr=np.array([15,45,15,40,140,120,210,38],np.float32)
    sc=np.array([40,40,16,16,100,140,166,255],np.float32)
    metal=np.where(inside, sm[q], metal); rough=np.where(inside, sr[q], rough); coat=np.where(inside, sc[q], coat)

    if (hh,ww)!=(h,w):
        up=lambda a: cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint); metal,rough,coat=map(up,(metal,rough,coat))
    return np.clip(paint,0,1).astype(np.float32), np.dstack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255))).astype(np.uint8)


def _arrays(shape: tuple[int,int], seed: int) -> tuple[np.ndarray,np.ndarray]:
    key=(int(shape[0]),int(shape[1]),int(seed))
    with _LOCK:
        got=_CACHE.get(key)
        if got is not None:
            _CACHE.move_to_end(key); return got
    value=_authored(shape,seed)
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2: _CACHE.popitem(last=False)
    return value


def paint_ember_cipher_i6(paint, shape, mask, seed, pm, bb):
    del bb
    authored,_=_arrays(shape,seed)
    src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_ember_cipher_i6(shape, seed, sm, base_m, base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
