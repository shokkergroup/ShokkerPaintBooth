"""Beetle Jewel I2 — process-first Chrysina photonic cuticle.

SPB-105 / owner 2026-09-01, iterations P1-P6: replace the rejected periodic
lozenge prototype with a bounded-jitter elytral pave. Every visible event is
part of a shell facet: crown, cuticle seam, growth stria, wax pit or polished
lip. Spec is carved from those same structures with continuous per-facet
variation, not a colour-grid or a shared scalar field.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, _fine, coords, h2, n01

GEN = 768


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h, w = _hw(shape)
    if a.shape[:2] == (h, w):
        return np.asarray(a, np.float32)
    return cv2.resize(np.asarray(a, np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    a = np.clip(mask * pm * 0.94, 0, 1)[:, :, None]
    paint[:, :, :3] = paint[:, :, :3] * (1-a) + np.clip(colour, 0, 1) * a
    return np.clip(paint, 0, 1).astype(np.float32)


def _surface(seed):
    yy, xx = coords(GEN)
    dx, dy, d1, fid, d2 = _cells(GEN, 9.2, int(seed) % 7919 + 310, jit=0.92, taps=9, need2=True)
    edge_dist = np.clip((d2-d1) / 4.2, 0, 1)
    seam = 1.0 - np.clip(edge_dist * 4.3, 0, 1)
    crown = np.clip(1.0 - (d1/5.7)**1.7, 0, 1)

    # Each facet owns an orientation and a thickness phase. Striae remain
    # inside their parent facet, so they cannot become a page-wide wallpaper.
    ang = fid * 6.2831853
    u = dx*np.cos(ang) + dy*np.sin(ang)
    stria = (np.sin(u * (1.45 + fid*1.2) + fid*17.0)*0.5+0.5) * crown
    stria = np.clip((stria-.34)*1.55, 0, 1)
    lip = np.clip((crown-.48)*3.8, 0, 1) * np.clip(1.0-seam*1.6, 0, 1)

    # Cuticle pores are not sprinkled noise: one possible dimple is locked to
    # a subset of facets and domed by local radius.
    pore_gate = np.clip((h2(np.floor((xx-dx)/9.2), np.floor((yy-dy)/9.2), int(seed)+613)-.73)*4.1, 0, 1)
    pore = np.clip(1.0-d1/1.55, 0, 1)**2 * pore_gate
    micro = _fine(GEN, int(seed)+29, .18)
    # Sample a slow optical flow at every facet centre. Because centre
    # coordinates are constant inside one Voronoi cell, the flow groups cells
    # into living cuticle waves without slicing colour bands through them.
    cx,cy=xx-dx,yy-dy
    regional=(np.sin(cx/51.0+cy/87.0)+.68*np.sin(cx/103.0-cy/69.0+seed*.013)+.34*np.cos((cx+cy)/37.0))
    regional=n01(regional)
    # Two additional slow fields cross the shell at different biological
    # growth angles.  They are sampled at facet centres, so every channel can
    # have its own coherent optical response without devolving into noise.
    regional_r=n01(np.cos(cx/73.0-cy/43.0+seed*.019)+.53*np.sin(cx/131.0+cy/57.0))
    regional_c=n01(np.sin(cx/39.0-cy/119.0-seed*.011)+.61*np.cos(cx/91.0+cy/63.0))
    thickness=np.mod(regional*.66 + fid*.24 + stria*.06 + crown*.04,1.0)
    return (crown.astype(np.float32), seam.astype(np.float32), lip.astype(np.float32),
            stria.astype(np.float32), pore.astype(np.float32), micro.astype(np.float32),
            thickness.astype(np.float32), fid.astype(np.float32), regional.astype(np.float32),
            regional_r.astype(np.float32), regional_c.astype(np.float32))


def paint_beetle_jewel_i2(paint, shape, mask, seed, pm, bb):
    crown,seam,lip,stria,pore,micro,t,fid,regional,regional_r,regional_c = _surface(seed+9400)
    # Deliberately narrow structural gamut: emerald -> lime-gold -> old gold,
    # with deep blue-green cuticle recesses. It reads as beetle shell, not RGB.
    stops=np.array([
        (.004,.018,.020),(.006,.052,.045),(.012,.130,.078),(.025,.245,.105),
        (.065,.390,.130),(.170,.535,.135),(.390,.630,.120),(.650,.680,.105),
        (.820,.710,.180),(.920,.815,.380)
    ],np.float32)
    pos=np.clip(t,0,.9999)*(len(stops)-1); lo=pos.astype(np.int32); hi=np.minimum(lo+1,len(stops)-1); f=(pos-lo)[...,None]
    col=stops[lo]*(1-f)+stops[hi]*f
    # Relief lighting gives every facet a convex shell read.
    gx=cv2.Sobel(crown-seam*.35-pore*.45,cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(crown-seam*.35-pore*.45,cv2.CV_32F,0,1,ksize=3)
    lam=np.clip(.61-gx*.34-gy*.24,0.28,1.16)
    aniso=np.exp(-((gx*.80+gy*.25)*2.4)**2)*stria
    col=col*(.50+.48*lam[...,None])
    col+=aniso[...,None]*np.array([.12,.16,.065],np.float32)
    col+=lip[...,None]*np.array([.095,.085,.025],np.float32)
    col*=1-seam[...,None]*.62-pore[...,None]*.38
    # Cool buried cuticle appears only in the deepest recesses; this keeps the
    # green-gold Chrysina identity while preventing polished-stone flatness.
    depth=np.clip(seam*.72+pore*.55-crown*.25,0,1)
    col=col*(1-depth[...,None]*.38)+np.array([.008,.045,.095],np.float32)*depth[...,None]*.38
    col+=micro[...,None]*np.array([.012,.018,.009],np.float32)

    # P6 owner-eye/M5 correction: make the real 8-32px elytral anatomy carry
    # the visible energy.  Thresholding only after the 2048 resize restores
    # crisp wax ridges and dark growth grooves that cubic sampling otherwise
    # erases.  These marks are bounded by their parent facet—not page noise.
    col_hi=_resize(np.clip(col,0,1),shape)
    crown_hi=_resize(crown,shape); stria_hi=_resize(stria,shape)
    seam_hi=_resize(seam,shape); lip_hi=_resize(lip,shape); pore_hi=_resize(pore,shape)
    ridge=np.clip((stria_hi-.48)*4.8,0,1)*crown_hi
    groove=np.clip((.56-stria_hi)*4.2,0,1)*crown_hi
    cuticle_edge=np.clip((seam_hi-.24)*4.0,0,1)
    col_hi*=1.0-groove[...,None]*.34-cuticle_edge[...,None]*.28
    col_hi+=ridge[...,None]*np.array([.25,.20,.055],np.float32)
    col_hi+=lip_hi[...,None]*np.array([.12,.11,.035],np.float32)
    col_hi*=1.0-pore_hi[...,None]*.31
    return _blend(paint,mask,pm,np.clip(col_hi,0,1))


def spec_beetle_jewel_i2(shape, seed, sm, base_m, base_r):
    crown,seam,lip,stria,pore,micro,t,fid,regional,regional_r,regional_c = _surface(seed+9400)
    # P6: material identities follow the Spec Encyclopedia.  Each channel
    # traverses the same eight proven anchor palettes along a different slow
    # facet-centred growth field.  The resulting thousands of M/R/Cc triplets
    # are coherent cuticle neighborhoods, never independently scattered RGB.
    anchors=np.array([
        (250,15,40),(250,45,40),(200,15,16),(100,40,16),
        (225,140,100),(80,120,140),(0,200,160),(252,38,255)
    ],np.float32)
    phases=(np.mod(regional*.79+fid*.21+.083,1.0),
            np.mod(regional_r*.74+fid*.19+stria*.07+.317,1.0),
            np.mod(regional_c*.76+fid*.16+seam*.08+.613,1.0))
    channels=[]
    for axis,phase in enumerate(phases):
        pos=np.clip(phase,0,.99999)*(len(anchors)-1)
        lo=pos.astype(np.int32); hi=np.minimum(lo+1,len(anchors)-1); f=pos-lo
        channels.append(anchors[lo,axis]*(1-f)+anchors[hi,axis]*f)
    M=channels[0] + crown*15 + lip*28 + stria*8 - seam*43 - pore*58 + micro*6
    R=channels[1] - crown*13 - lip*20 + stria*7 + seam*39 + pore*51 - micro*4
    C=channels[2] - crown*12 - lip*23 + stria*9 + seam*42 + pore*46 + micro*7
    M=np.clip(M*sm,0,255); R=np.clip(R,15,255); C=np.clip(C,0,255)
    # P7 balance: the prior full-range M/R pair overpowered the visible shell.
    # Keep thousands of independently varying material coordinates and the
    # full clearcoat flip, but constrain metal/roughness to credible polished
    # cuticle ranges.  This makes the light response support—not bury—the art.
    M=60.0+(M/255.0)*165.0
    R=35.0+((R-15.0)/240.0)*135.0
    return np.clip(_resize(M,shape),0,255),np.clip(_resize(R,shape),15,255),np.clip(_resize(C,shape),0,255)
