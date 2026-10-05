"""Morpho Lamella I1 — shingled ridge-ladder photonic scales.

SPB-105 / owner 2026-09-01.  Morpho didius research reports parallel ridges,
six-to-eight Christmas-tree lamellae, crossrib windows, dark melanin beneath,
and height offsets between neighboring ridges.  This carrier bounds those
features inside staggered 28-32px native scale plates rather than drawing
page-wide stripes.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import coords, h2, n01

GEN = 1024


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(a, shape):
    h,w=_hw(shape)
    return np.asarray(a,np.float32) if a.shape[:2]==(h,w) else cv2.resize(np.asarray(a,np.float32),(w,h),interpolation=cv2.INTER_CUBIC)


def _blend(paint,mask,pm,col):
    if paint.ndim==3 and paint.shape[2]>3: paint=paint[:,:,:3].copy()
    a=np.clip(mask*pm*.94,0,1)[...,None]
    paint[:,:,:3]=paint[:,:,:3]*(1-a)+np.clip(col,0,1)*a
    return np.clip(paint,0,1).astype(np.float32)


def _surface(seed):
    y,x=coords(GEN)
    ch,cw=14.0,16.0
    row=np.floor(y/ch); stagger=np.mod(row,2.0)*cw*.48
    xx=x+stagger
    col=np.floor(xx/cw)
    lx=np.mod(xx,cw)-cw*.5; ly=np.mod(y,ch)-ch*.5
    # Convex overlapping scale plate with a softly pointed/scalloped tail.
    tail=np.clip((ly+ch*.5)/ch,0,1)
    plate=np.clip(1.0-((lx/(cw*.50-.75*tail))**6+(ly/(ch*.51))**6),0,1)
    edge=np.clip((1-plate)*4.2,0,1)

    # Four ridges per plate (8px native pitch), never page-wide. Neighboring
    # ridges receive a height offset, the key wide-angle Morpho principle.
    orient=h2(col,row,int(seed)+137)
    ridge_phase=np.mod(lx+cw*.5+(orient-.5)*2.4+(orient-.5)*ly*.30,4.0)
    ridge=np.clip(1.0-np.abs(ridge_phase-2.0)*1.7,0,1)*plate
    ridge_id=np.floor((lx+cw*.5)/4.0)
    height=.52+.48*h2(col*5+ridge_id,row,int(seed)+211)

    # Six-to-eight visible lamellar teeth along the short plate; selected
    # windows are broken deterministically, matching natural disorder.
    tooth_phase=np.mod(ly+ch*.5+.48*np.sin(lx*.72+orient*5.0),3.15)
    tooth=np.clip(1.0-np.abs(tooth_phase-1.58)*2.15,0,1)*ridge
    tooth_id=np.floor((ly+ch*.5)/3.15)
    keep=np.clip((h2(col*7+ridge_id,row*9+tooth_id,int(seed)+419)-.17)*1.35,0,1)
    tooth*=keep
    crossrib=np.clip(1.0-np.abs(tooth_phase-1.58)*3.7,0,1)*plate*(1-ridge*.62)
    window=np.clip(plate-ridge*.62-crossrib*.48,0,1)

    # Optical states are coherent per plate yet independently shifted.
    cx=col*cw-stagger; cy=row*ch
    p0=n01(np.sin(cx/73+cy/109)+.55*np.cos(cx/137-cy/61))
    p1=n01(np.cos(cx/97-cy/67)+.61*np.sin(cx/149+cy/43))
    p2=n01(np.sin(cx/53-cy/131)+.58*np.cos(cx/113+cy/79))
    flow=n01(np.sin(cx/173+cy/227)+.55*np.cos(cx/251-cy/149))
    return tuple(np.asarray(a,np.float32) for a in (plate,edge,ridge,height,tooth,crossrib,window,p0,p1,p2,flow))


def paint_butterfly_morpho_i1(paint,shape,mask,seed,pm,bb):
    plate,edge,ridge,height,tooth,crossrib,window,p0,p1,p2,flow=_surface(seed+9402)
    deep=np.array([.006,.012,.052],np.float32)
    violet=np.array([.045,.025,.33],np.float32)
    blue=np.array([.018,.17,.88],np.float32)
    flash=np.array([.32,.68,1.0],np.float32)
    t=np.clip(.18+.56*flow+.26*p0,0,1)
    col=violet[None,None,:]*(1-t[...,None])+blue[None,None,:]*t[...,None]
    # P4: broad-angle structural flash.  High ridge-flow neighborhoods bloom
    # cyan-white while low neighborhoods fall into violet; the fine lamellae
    # remain unchanged underneath, so this is optical hierarchy, not wallpaper.
    flash_zone=np.clip((t-.58)*2.65,0,1)
    trough_zone=np.clip((.34-t)*3.1,0,1)
    col=col*(1-flash_zone[...,None]*.72)+flash[None,None,:]*flash_zone[...,None]*.72
    col=col*(1-trough_zone[...,None]*.40)+np.array([.055,.006,.24],np.float32)[None,None,:]*trough_zone[...,None]*.40
    # P2 continuous wing field: plates overlap optically instead of floating
    # as blue dots on black.  Melanin remains in the windows, not every seam.
    col=col*(.88+.12*plate[...,None])
    col+=ridge[...,None]*height[...,None]*flash*.58
    col+=tooth[...,None]*np.array([.20,.34,.70],np.float32)
    col+=crossrib[...,None]*np.array([.045,.12,.35],np.float32)
    col=col*(1-window[...,None]*.055)+deep[None,None,:]*window[...,None]*.055
    # Restore crisp ladder teeth after native enlargement.
    hi=_resize(np.clip(col,0,1),shape)
    tooth_hi=_resize(tooth,shape); ridge_hi=_resize(ridge,shape); edge_hi=_resize(edge,shape)
    hi+=np.clip((tooth_hi-.42)*5.0,0,1)[...,None]*np.array([.18,.29,.56],np.float32)
    hi+=np.clip((ridge_hi-.55)*4.0,0,1)[...,None]*np.array([.08,.17,.40],np.float32)
    return _blend(paint,mask,pm,np.clip(hi,0,1))


def spec_butterfly_morpho_i1(shape,seed,sm,base_m,base_r):
    plate,edge,ridge,height,tooth,crossrib,window,p0,p1,p2,flow=_surface(seed+9402)
    # Broad-angle pearl ridges, chrome tooth tips, satin crossribs, dielectric
    # troughs and matte plate abrasion—each channel has its own plate phase.
    m=50+150*(.61*p0+.17*ridge*height+.10*tooth+.12*flow)-edge*16-window*12
    r=38+135*(.70*p1+.17*window+.13*edge)-ridge*16-tooth*12
    cc=12+230*(.64*p2+.14*tooth+.13*crossrib+.09*ridge)-edge*15
    m=np.clip(m*sm,0,225); r=np.clip(r,18,210); cc=np.clip(cc,0,255)
    return _resize(m,shape),_resize(r,shape),_resize(cc,shape)
