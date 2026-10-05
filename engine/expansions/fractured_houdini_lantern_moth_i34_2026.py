"""Private I34 Lantern Moth: an enamel surface with material-only moth relief.

SPB-H1 / owner reset 2026-09-01.  P1 starts from a complete night-enamel
surface; the recurring moths are composed only from 8–32px-native wing facets,
body, and antenna strokes in M/Rough/Cc.  RGB contains no moth artwork.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_W = 768
_C: OrderedDict[tuple[int, int, int], tuple[np.ndarray, np.ndarray]] = OrderedDict()
_L = RLock()
_TAU = np.float32(6.283185307179586)


def _h(x, y, seed):
    return np.mod(np.sin(x*127.1 + y*311.7 + seed*71.3)*43758.5453, 1.).astype(np.float32)


def _moths(seed: int):
    """Non-grid full-canvas placements; a moth is several fine facets, never one blob."""
    fore = np.zeros((_W, _W), np.uint8); rear = np.zeros_like(fore)
    body = np.zeros_like(fore); filigree = np.zeros_like(fore); tempo = np.zeros_like(fore)
    rng = np.random.default_rng(8141 + seed*19); centers = []; attempts = 0
    while len(centers) < 36 and attempts < 12000:
        attempts += 1; cx, cy = int(rng.integers(28, _W-28)), int(rng.integers(28, _W-28))
        if all((cx-px)**2+(cy-py)**2 > 61**2 for px, py in centers): centers.append((cx, cy))
    for cx, cy in centers:
        sx, sy = int(rng.integers(8, 12)), int(rng.integers(9, 14)); ang = float(rng.uniform(-42, 42)); kind=int(rng.integers(0,4)); ca, sa = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
        def p(dx, dy): return int(cx+dx*ca-dy*sa), int(cy+dx*sa+dy*ca)
        # Each wing is a 21–29px-native facet with 8px-native vein strokes.
        for sign in (-1, 1):
            # I34 P3: P2's solid wing facets still read as tiny stamps.  The
            # relief becomes engraved wing architecture—outlines plus veins—
            # so it can catch as a discovered drawing rather than a dot.
            cv2.ellipse(fore, p(sign*.58*sx, -.20*sy), (sx, sy), ang+sign*24, 20, 202, 178, 3, cv2.LINE_AA)
            cv2.ellipse(rear, p(sign*.48*sx, .40*sy), (max(5, sx-2), max(5, sy-3)), ang+sign*17, 154, 338, 159, 3, cv2.LINE_AA)
            cv2.line(filigree, p(sign*.12*sx, -.34*sy), p(sign*1.18*sx, -.10*sy), 174, 3, cv2.LINE_AA)
            cv2.line(filigree, p(sign*.10*sx, .10*sy), p(sign*.96*sx, .57*sy), 152, 3, cv2.LINE_AA)
            cv2.line(fore, p(sign*.18*sx, -.10*sy), p(sign*.78*sx, -.65*sy), 160, 3, cv2.LINE_AA)
            cv2.line(rear, p(sign*.18*sx, .20*sy), p(sign*.70*sx, .82*sy), 150, 3, cv2.LINE_AA)
            cv2.ellipse(filigree, p(sign*1.05*sx, .23*sy), (max(3, sx//3), max(3, sy//4)), ang+sign*34, 194, 346, 132, 3, cv2.LINE_AA)
            # I34 P4: a subset grows a fine engraved tail back into the
            # surrounding process, so the motif belongs to the enamel rather
            # than sitting on it as a self-contained little sticker.
            if kind in (1, 3): cv2.line(filigree, p(sign*.82*sx, .56*sy), p(sign*(1.85+.25*kind)*sx, (1.02+.10*kind)*sy), 138, 3, cv2.LINE_AA)
            if kind == 2: cv2.line(rear, p(sign*.32*sx, .55*sy), p(sign*1.52*sx, .94*sy), 146, 3, cv2.LINE_AA)
        cv2.ellipse(body, p(0, .08*sy), (max(3, sx//3), sy), ang, 0, 360, 210, -1, cv2.LINE_AA)
        cv2.line(filigree, p(-.12*sx, -.84*sy), p(-.42*sx, -1.08*sy), 160, 3, cv2.LINE_AA)
        cv2.line(filigree, p(.12*sx, -.84*sy), p(.42*sx, -1.08*sy), 160, 3, cv2.LINE_AA)
        cv2.ellipse(tempo, (cx, cy), (sx+9, sy+10), ang, 0, 360, int(rng.integers(110, 245)), -1, cv2.LINE_AA)
    blur = lambda x, s: cv2.GaussianBlur(x.astype(np.float32)/255., (0, 0), s)
    return tuple(blur(x, s) for x, s in ((fore,.42),(rear,.42),(body,.38),(filigree,.45),(tempo,1.1)))


def _assets(shape, seed):
    key = (int(shape[0]), int(shape[1]), int(seed))
    with _L:
        if key in _C: return _C[key]
    yy, xx = np.mgrid[:_W, :_W].astype(np.float32); phase = seed*.113
    # A coherent physical carrier: black enamel brushed by three fine flowing cuts.
    # I34 P5 / native-scale audit: P4's broad compartments wasted car canvas.
    # Build denser 8–32px physical engraving bands directly, with three warped
    # directions and no post-hoc scale trick or macro wallpaper.
    u = xx*.352 + yy*.196 + 3.4*np.sin(yy*.027+phase) + 2.1*np.sin(xx*.043-phase)
    v = yy*.338 - xx*.174 + 2.9*np.sin(xx*.031-phase*.6)
    w = xx*.183 + yy*.361 + 2.2*np.sin((xx-yy)*.022+phase*1.3)
    a = np.clip((.46-np.abs(np.sin(u)))/.46, 0, 1); b = np.clip((.39-np.abs(np.sin(v)))/.39, 0, 1); c = np.clip((.31-np.abs(np.sin(w)))/.31, 0, 1)
    tide = .5+.5*np.sin(u*.071+np.sin(v*.053)*1.6); bloom=.5+.5*np.sin(w*.058-np.sin(u*.047))
    dark=np.stack((.014+.026*tide,.021+.031*bloom,.052+.074*tide),2); indigo=np.stack((.020+.055*bloom,.065+.115*tide,.160+.225*bloom),2); plum=np.stack((.062+.094*tide,.019+.030*bloom,.083+.131*tide),2); silver=np.stack((.24+.34*tide,.32+.37*bloom,.55+.34*tide),2)
    art=np.clip(dark*.84+indigo*(.30+.23*tide)[...,None]+plum*(.10+.13*bloom)[...,None]+silver*(.22*a+.14*b+.06*c)[...,None],0,1).astype(np.float32)
    M=49+89*tide+74*a-43*b+29*c; R=198-69*bloom-86*a+58*b-20*c; C=32+118*bloom+49*a+65*b+55*c
    spec=np.dstack((M,R,C)).clip(0,255).astype(np.float32); fore,rear,core,laces,tempo=_moths(seed); tempo=.42+.58*tempo
    # I34 P2 / owner doctrine: P1's complete bright moths read as stamps.
    # Gate each fine anatomical family differently, so it can only assemble
    # through changing light/material preference rather than one static swatch.
    gf=np.clip(.44+.72*np.sin(xx*.191+yy*.067+seed*.23),0,1); gr=np.clip(.47+.69*np.sin(xx*.083-yy*.177-seed*.31),0,1); gc=np.clip(.42+.76*np.sin(xx*.149+yy*.123+seed*.17),0,1); gl=np.clip(.50+.66*np.sin(xx*.118-yy*.109+seed*.41),0,1)
    fore*=gf*tempo; rear*=gr*tempo; core*=gc*tempo; laces*=gl*tempo
    spec[fore>.22]=.63*spec[fore>.22]+.37*np.array((246,16,238),np.float32)
    spec[rear>.22]=.65*spec[rear>.22]+.35*np.array((92,152,92),np.float32)
    spec[core>.23]=.59*spec[core>.23]+.41*np.array((252,8,250),np.float32)
    spec[laces>.22]=.70*spec[laces>.22]+.30*np.array((42,214,48),np.float32)
    # A fine multi-state weave lives inside anatomy, not as ambient glitter.
    weave=((np.floor(xx/3).astype(np.int32)*7+np.floor(yy/3).astype(np.int32)*11)%8); deck=np.asarray(((250,15,40),(250,45,40),(200,15,16),(100,40,16),(225,140,100),(252,38,255),(80,120,140),(0,200,160)),np.float32); anatomy=np.maximum.reduce((fore,rear,core,laces))>.18; spec[anatomy]=.79*spec[anatomy]+.21*deck[weave][anatomy]
    h,wid=key[:2]
    if (h,wid)!=(_W,_W): art=cv2.resize(art,(wid,h),interpolation=cv2.INTER_AREA if max(h,wid)<_W else cv2.INTER_LINEAR); spec=cv2.resize(spec,(wid,h),interpolation=cv2.INTER_NEAREST)
    out=(art.astype(np.float32),np.clip(spec,0,255).astype(np.uint8))
    with _L:
        _C[key]=out
        if len(_C)>2:_C.popitem(last=False)
    return out


def paint_lantern_moth_i34(paint, shape, mask, seed, pm, bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]; src=src/255 if src.max(initial=0)>1.5 else src; m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m; return np.clip(src*(1-(m*pm)[...,None])+art*(m*pm)[...,None],0,1).astype(np.float32)


def spec_lantern_moth_i34(shape, seed, sm, base_m, base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
