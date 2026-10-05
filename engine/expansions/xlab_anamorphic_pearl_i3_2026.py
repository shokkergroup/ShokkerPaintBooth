"""X LAB Anamorphic Pearl I3 — warped pearl cells with independent local states.

SPB-105 / owner note, 2026-08-29.  The live card is preserved.  This isolated
study removes its straight vertical read: every 8–28px native cell has a
different pearl/chrome/matte/flake response, but the cells are gently warped
into an optical sheet rather than assembled as a wallpaper grid.
"""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

WORK = 1024
_CACHE = OrderedDict()
_LOCK = RLock()


def _build():
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    xn, yn = (x/(WORK-1))*2-1, (y/(WORK-1))*2-1
    # Each 1024 cell doubles to ~27px native.  Sub-cell panels are 8–14px.
    u = .83*xn + .56*yn + .025*np.sin(9.0*yn + 2.2*xn)
    v = -.56*xn + .83*yn + .022*np.sin(8.0*xn - 1.5*yn)
    density = 37.0
    cu, cv = (u+1.50)*density, (v+1.50)*density
    gx, gy = np.floor(cu).astype(np.int32), np.floor(cv).astype(np.int32)
    fu, fv = np.mod(cu,1.0), np.mod(cv,1.0)
    edge = np.minimum(np.minimum(fu,1-fu),np.minimum(fv,1-fv))
    radius = np.sqrt((fu-.5)**2+(fv-.5)**2)
    # Tiles have a pearl lens, an interrupted clear shoulder and a quiet seam.
    lens = np.exp(-((radius-.20)/.22)**2)
    rim = np.exp(-((radius-.34)/.045)**2)
    seam = np.clip((.060-edge)/.060,0,1)
    code = np.mod(19*gx + 37*gy + 7*gx*gy, 8)
    broad = .5+.5*np.sin(2.35*u-1.9*v+.33*np.sin(3.7*v))
    micro = (np.floor(fu*2).astype(np.int32)+2*np.floor(fv*2).astype(np.int32)+code) & 3
    # Paint remains a dark pearl sheet. State changes are intentionally subtle
    # in pigment yet drastic in M/R/Cc, so symbols/optics reveal with lighting.
    states=np.asarray(((.09,.04,.16),(.17,.07,.28),(.31,.13,.39),(.12,.22,.40),
                       (.42,.14,.42),(.16,.34,.42),(.46,.24,.50),(.12,.12,.22)),np.float32)
    base=states[code]
    bright=(.14+.27*lens+.10*broad)[...,None]
    pearl=np.asarray((.88,.70,1.0),np.float32)[None,None,:]
    paint=np.clip(base*.68+pearl*bright,0,1)
    # Inside each cell, four small pearl faces retain the layout but avoid a
    # uniform checker: their intensities follow the cell's own state + phase.
    face=np.select((micro==0,micro==1,micro==2),(1.0,.70,.42),default=.22).astype(np.float32)
    paint=np.clip(paint + pearl*(.075*face*lens)[...,None] + np.asarray((1,.32,.82),np.float32)*(rim*.12)[...,None],0,1)
    paint=paint*(1-.30*seam[...,None])+np.asarray((.025,.016,.045),np.float32)*(.30*seam[...,None])
    # Eight genuinely distinct material states. Hard boundaries live only in
    # the design's own warped cells and their four facelets.
    mtab=np.asarray((242,30,178,92,218,56,198,126),np.float32)
    rtab=np.asarray((20,190,96,150,42,172,72,122),np.float32)
    ctab=np.asarray((232,54,166,112,202,76,186,134),np.float32)
    metal=mtab[(code+micro)&7]; rough=rtab[(code+2*micro)&7]; coat=ctab[(code+3*micro)&7]
    hot=np.clip((broad-.63)/.37,0,1)
    metal=np.clip(metal*(.72+.28*lens)+22*hot+20*rim-38*seam,0,255)
    rough=np.clip(rough*(.80+.20*(1-lens))+28*seam-18*rim,0,255)
    coat=np.clip(coat*(.72+.28*lens)+24*rim-30*seam,0,255)
    return paint.astype(np.float32), np.stack((metal,rough,coat),axis=2).astype(np.uint8)


def _arrays():
    with _LOCK:
        if 'v' not in _CACHE:
            p,s=_build(); p.setflags(write=False); s.setflags(write=False); _CACHE['v']=(p,s)
        return _CACHE['v']


def _mask(mask,h,w):
    m=np.asarray(mask,np.float32)
    if m.ndim==3:m=m[...,0]
    if m.shape!=(h,w):m=cv2.resize(m,(w,h),interpolation=cv2.INTER_LINEAR)
    return np.clip(m,0,1)


def paint_anamorphic_pearl(paint,shape,mask,seed,pm,bb):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.0
    if src.shape[:2]!=(h,w):src=cv2.resize(src,(w,h),interpolation=cv2.INTER_LINEAR)
    authored,_=_arrays()
    if authored.shape[:2]!=(h,w):authored=cv2.resize(authored,(w,h),interpolation=cv2.INTER_CUBIC)
    mix=(_mask(mask,h,w)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_anamorphic_pearl(shape,mask,seed,sm):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=_arrays()
    if spec.shape[:2]!=(h,w):spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
    cov=_mask(mask,h,w)[...,None]; out=np.empty((h,w,4),np.uint8)
    out[...,:3]=(spec.astype(np.float32)*cov).astype(np.uint8); out[...,3]=(cov[...,0]*255).astype(np.uint8)
    return out
