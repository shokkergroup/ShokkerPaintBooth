"""Pressed Vinyl I1 — dense 1950s tuck-and-roll upholstery.

SPB-105 / SH-VINYL-GROOVE-I1, 2026-08-30.  The former Vinyl Groove used
~146px mattress tufts, which read as a macro wallpaper on a whole-car canvas.
This is a fresh material carrier: 36px stations constructed from 2–24px
seams, crowns, sidewall highlights, stitch dashes, buttons and pin glints.
Each of those visible print/material states owns a different M/R/Cc response.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _soft_band(value, center, halfwidth, feather):
    return np.clip((halfwidth - np.abs(value - center)) / max(feather, 1e-4), 0, 1)


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    q = min(1.0, 1024.0 / max(h, w)); hh, ww = max(16, round(h*q)), max(16, round(w*q))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32); X, Y = x/q, y/q
    # A 36px upholstery station; all component widths below are 2–24px.
    a = np.deg2rad(32.0); ca, sa = np.cos(a), np.sin(a)
    U = X*ca + Y*sa + 1.8*np.sin(Y/109.0)
    V =-X*sa + Y*ca + 1.2*np.sin(X/127.0)
    per = 36.0; fu = np.mod(U/per, 1.0)-.5; fv = np.mod(V/per, 1.0)-.5
    ix = np.floor(U/per).astype(np.int32); iy = np.floor(V/per).astype(np.int32)
    state = np.mod(ix*17 + iy*31 + (ix ^ iy)*5 + int(seed), 4).astype(np.int32)
    d = np.abs(fu) + np.abs(fv)
    # Individual visible marks: vinyl panel, 2–4px recessed seam, 5–9px
    # crown, short sidewall shine, per-cell 3px stitch dash and 5px button.
    panel = np.clip((.465-d)/.090, 0, 1)
    seam = _soft_band(d, .472, .034, .020)
    channel = _soft_band(d, .385, .070, .035) * panel
    crown = np.clip((.235-d)/.105, 0, 1)
    side = np.maximum(_soft_band(fu, -.245, .040, .018), _soft_band(fv, -.245, .040, .018))*panel
    dash_a = np.clip((.031-np.abs(fu+.30))/ .018,0,1)*np.clip((.085-np.abs(fv))/ .045,0,1)
    dash_b = np.clip((.031-np.abs(fv+.30))/ .018,0,1)*np.clip((.085-np.abs(fu))/ .045,0,1)
    stitch = np.maximum(dash_a, dash_b)
    bx = ((state==0)*.14 + (state==1)*-.14 + (state==2)*.11 + (state==3)*-.11).astype(np.float32)
    by = ((state==0)*-.12 + (state==1)*.12 + (state==2)*.14 + (state==3)*-.14).astype(np.float32)
    button = np.clip(1-np.hypot((fu-bx)/.073,(fv-by)/.073),0,1)
    pin = np.clip(1-np.hypot((fu-bx+.018)/.026,(fv-by-.018)/.026),0,1)
    # This is restrained material lot variation, only within visible vinyl;
    # it is not a generic grain or an independent noise layer.
    lot = .5 + .5*np.sin((U+2*V)/73.0 + .45*np.sin(V/31.0))
    cherry = np.array((.72,.025,.042),np.float32); scarlet = np.array((.95,.09,.065),np.float32)
    oxblood = np.array((.29,.008,.018),np.float32); shadow = np.array((.035,.006,.010),np.float32)
    wine = np.array((.45,.014,.028),np.float32); cream = np.array((.92,.72,.31),np.float32)
    chrome = np.array((.80,.86,.83),np.float32); pink = np.array((1.0,.34,.27),np.float32)
    panel_col = np.where((state[...,None]&1)>0, scarlet, cherry)
    paint = oxblood*(.80+.15*lot[...,None])
    paint = paint*(1-panel[...,None]) + panel_col*(panel[...,None])
    paint = paint*(1-channel[...,None]*.35) + wine*(channel[...,None]*.35)
    paint = paint*(1-seam[...,None]*.96) + shadow*(seam[...,None]*.96)
    paint = paint*(1-crown[...,None]*.18) + pink*(crown[...,None]*.18)
    paint = paint*(1-side[...,None]*.57) + scarlet*(side[...,None]*.57)
    paint = paint*(1-stitch[...,None]*.75) + cream*(stitch[...,None]*.75)
    paint = paint*(1-button[...,None]*.92) + cream*(button[...,None]*.92)
    paint = paint*(1-pin[...,None]*.96) + chrome*(pin[...,None]*.96)
    # Per-feature material states: plush vinyl crown, recessed seam, printed
    # stitch, brass button and chrome pin — deliberately not a channel noise.
    M = 36 + 20*lot + 33*panel + 21*channel + 13*crown + 49*side + 62*seam + 131*stitch + 167*button + 201*pin
    R = 209 - 19*lot - 43*panel - 25*channel - 54*crown - 70*side - 30*seam - 105*stitch - 148*button - 190*pin
    C = 29 + 17*lot + 40*panel + 27*channel + 72*crown + 105*side + 21*seam + 109*stitch + 159*button + 205*pin
    if (hh, ww) != (h, w):
        up = lambda z: cv2.resize(z.astype(np.float32), (w,h), interpolation=cv2.INTER_LINEAR)
        paint = up(paint); M,R,C = map(up,(M,R,C))
    value = (np.clip(paint,0,1).astype(np.float32), np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2: _CACHE.popitem(last=False)
    return value


def paint_vinyl_pressed(paint, shape, mask, seed, pm, bb):
    del bb
    authored,_ = _arrays(shape,seed); src = np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0) > 1.5: src = src/255.0
    m = np.asarray(mask,np.float32); m = m[...,0] if m.ndim == 3 else m
    mix = (np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_vinyl_pressed(shape, seed, sm, base_m, base_r):
    del sm,base_m,base_r
    _,spec = _arrays(shape,seed); return spec
