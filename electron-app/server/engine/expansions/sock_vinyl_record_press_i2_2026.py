"""Vinyl Record Press I2 — fine 1950s black-lacquer groove material.

SPB-105 / SH-VINYL-GROOVE-I2 / 2026-08-30.  The rejected I1 was red
upholstery rather than a record.  This carrier is pressed black vinyl: 1–3px
groove ridges, 4–8px alternating lacquer lands, needle-polish arcs and tiny
pressing seams.  Two off-canvas stamp centres prevent a single centred disc
while keeping the entire canvas covered in authentic record microstructure.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        prior = _CACHE.get(key)
        if prior is not None:
            _CACHE.move_to_end(key); return prior
    y, x = np.mgrid[:h, :w].astype(np.float32)
    # Two physical press spindles are deliberately off canvas. Their 7–13px
    # groove pitches create only fine arcs, while the blend zone is a material
    # lot choice rather than a large painted symbol.
    r1 = np.hypot(x + 286. + 18.*np.sin(y/173.), y - 614. + 11.*np.cos(x/131.))
    r2 = np.hypot(x - (w + 254.) + 15.*np.cos(y/149.), y - (h - 477.) + 13.*np.sin(x/127.))
    phase = (int(seed) & 8191) * .0013
    g1 = .5 + .5*np.cos(r1 * (2*np.pi/8.2) + phase)
    g2 = .5 + .5*np.cos(r2 * (2*np.pi/11.7) - phase*.73)
    selector = .5 + .5*np.sin((x*.73+y*.29)/263. + .30*np.sin(y/97.))
    groove = g1*(1-selector) + g2*selector
    ridge = np.clip((groove-.77)/.23, 0, 1)       # 1–3px ridge highlight
    land = np.clip((.62-groove)/.27, 0, 1)        # 4–8px satin land
    burnish = np.clip((groove-.48)/.18, 0, 1) * (1-ridge)
    # Fine radial pressing seams, never a label/record graphic.
    seam = np.clip((np.sin(r1*(2*np.pi/42.)+phase)-.965)/.035, 0, 1)
    seam = np.maximum(seam, np.clip((np.sin(r2*(2*np.pi/51.)-phase)-.970)/.03,0,1))
    polish = np.clip(.5+.5*np.sin(r1/29.-r2/37.+.6*np.sin((x-y)/83.)),0,1)*burnish
    static = .5+.5*np.sin(x*.71+np.sin(y*.37)*.43)*np.sin(y*.67-np.sin(x*.29)*.31)
    fleck = np.clip((static-.89)/.11,0,1)*land   # sub-2px pressing specks

    black = np.array((.006,.008,.015),np.float32)
    midnight = np.array((.012,.026,.060),np.float32)
    indigo = np.array((.025,.065,.17),np.float32)
    cobalt = np.array((.06,.22,.49),np.float32)
    silver = np.array((.68,.76,.83),np.float32)
    amber = np.array((.88,.37,.07),np.float32)
    paint = black + midnight*(.42+.28*land)[...,None]
    paint = paint*(1-burnish[...,None]*.54)+indigo*(burnish[...,None]*.54)
    paint = paint*(1-ridge[...,None]*.72)+cobalt*(ridge[...,None]*.72)
    paint = paint*(1-polish[...,None]*.36)+silver*(polish[...,None]*.36)
    paint = paint*(1-seam[...,None]*.43)+amber*(seam[...,None]*.43)
    paint = paint*(1-fleck[...,None]*.14)+silver*(fleck[...,None]*.14)

    # Physical state map: deep groove / satin land / polished ridge / press
    # seam / micro-speck all differ independently in metal, roughness and coat.
    M = 17 + 29*land + 78*burnish + 139*ridge + 102*seam + 51*fleck + 21*selector
    R = 232 - 39*land - 83*burnish - 132*ridge - 67*seam - 81*fleck + 18*(1-selector)
    C = 20 + 41*land + 88*burnish + 154*ridge + 111*seam + 92*fleck + 24*selector
    value = (np.clip(paint,0,1).astype(np.float32),
             np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2: _CACHE.popitem(last=False)
    return value


def paint_vinyl_record_press(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed); src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5: src = src / 255.
    coverage = np.asarray(mask, np.float32); coverage = coverage[...,0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_vinyl_record_press(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec
