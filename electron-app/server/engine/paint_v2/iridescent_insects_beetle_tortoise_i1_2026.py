"""Tortoise Glass I1 — transparent shield over a gold/red reflector.

SPB-105 / owner 2026-09-01.  Charidotella research describes transparent
lateral cuticle, a gold endocuticular chirped reflector, pore/fluid-controlled
optical change and a gold-to-red stress state.  Here each 12-28px shield owns
its reflector core, growth rings, pore, brass rim and abraded transparent lip.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.expansions.fractured_relics_kit_2026 import _cells, coords, h2, n01

GEN=1024


def _hw(shape): return shape[:2] if len(shape)>2 else shape


def _resize(a,shape):
    h,w=_hw(shape)
    return np.asarray(a,np.float32) if a.shape[:2]==(h,w) else cv2.resize(np.asarray(a,np.float32),(w,h),interpolation=cv2.INTER_CUBIC)


def _blend(paint,mask,pm,col):
    if paint.ndim==3 and paint.shape[2]>3: paint=paint[:,:,:3].copy()
    a=np.clip(mask*pm*.94,0,1)[...,None]
    paint[:,:,:3]=paint[:,:,:3]*(1-a)+np.clip(col,0,1)*a
    return np.clip(paint,0,1).astype(np.float32)


def _surface(seed):
    y,x=coords(GEN)
    dx,dy,d1,fid,d2=_cells(GEN,13.8,int(seed)%7919+771,jit=.68,taps=9,need2=True)
    ang=fid*6.2831853
    u=dx*np.cos(ang)+dy*np.sin(ang); v=-dx*np.sin(ang)+dy*np.cos(ang)
    # P3: overlapping transparent scutes, not isolated pebbles.  The broad
    # superellipse nearly fills each Voronoi ownership cell; the ownership
    # boundary becomes the fine seam between adjacent pieces of glass armor.
    q=(np.abs(u)/9.1)**4+(np.abs(v)/7.35)**4
    shield=np.clip(1-q,0,1)**.34
    crown=np.clip((shield-.08)*1.10,0,1)
    boundary=np.clip(1-(d2-d1)/1.28,0,1)
    rim=np.clip((shield-.05)*4.7,0,1)*np.clip(1-(shield-.78)*5.1,0,1)
    inner=np.clip((shield-.35)*1.75,0,1)

    # Two-to-three growth rings per native 20px shield, plus a single aligned
    # fluid pore. Marks are radial anatomy, not texture noise.
    ring_wave=np.sin(np.sqrt(np.clip(q,0,1.5))*np.pi*5.2)*.5+.5
    rings=np.clip((ring_wave-.64)*4.2,0,1)*shield*(1-inner*.58)
    cell_x=x-dx; cell_y=y-dy
    row=np.floor(cell_y/13.8); col=np.floor(cell_x/13.8)
    pore_gate=np.clip((h2(col,row,int(seed)+383)-.86)*5.9,0,1)
    pore=np.clip(1-(u/1.55)**2-(v/1.35)**2,0,1)**2*pore_gate
    abrasion=np.clip((h2(col*5+np.floor(dx*2),row*7+np.floor(dy*2),int(seed)+619)-.62)*2.7,0,1)*rim

    # Slow reflector/fluid states sampled at shield centres; three separate
    # fields prevent one scalar from driving every material channel.
    f0=n01(np.sin(cell_x/71+cell_y/109)+.58*np.cos(cell_x/137-cell_y/53))
    f1=n01(np.cos(cell_x/89-cell_y/67)+.62*np.sin(cell_x/149+cell_y/43))
    f2=n01(np.sin(cell_x/47-cell_y/127)+.55*np.cos(cell_x/113+cell_y/83))
    stress=np.clip((n01(np.sin(cell_x/151+cell_y/97)+.53*np.cos(cell_x/79-cell_y/181))-.64)*3.2,0,1)
    return tuple(np.asarray(a,np.float32) for a in (shield,crown,boundary,rim,inner,rings,pore,abrasion,f0,f1,f2,stress))


def paint_beetle_tortoise_i1(paint,shape,mask,seed,pm,bb):
    shield,crown,boundary,rim,inner,rings,pore,abrasion,f0,f1,f2,stress=_surface(seed+9410)
    smoke=np.array([.17,.075,.018],np.float32)
    amber=np.array([.74,.36,.028],np.float32)
    gold=np.array([1.00,.82,.20],np.float32)
    red=np.array([.68,.028,.014],np.float32)
    glass=np.array([.72,.92,.78],np.float32)
    core=amber[None,None,:]*(1-f0[...,None])+gold[None,None,:]*f0[...,None]
    core=core*(1-stress[...,None])+red[None,None,:]*stress[...,None]
    # P4: the gold/red reflector is continuous beneath a transparent shell.
    # Cell ownership is visible only as glass seams and anatomical rings; it
    # must never turn the finish into a field of isolated chips.
    col=core*.84+smoke[None,None,:]*.16
    col+=crown[...,None]*np.array([.035,.048,.032],np.float32)
    col+=rings[...,None]*np.array([.065,.035,.010],np.float32)
    col+=rim[...,None]*np.array([.045,.040,.018],np.float32)
    col=col*(1-boundary[...,None]*.10)+glass[None,None,:]*boundary[...,None]*.12
    col*=1-pore[...,None]*.20
    col+=abrasion[...,None]*np.array([.08,.10,.085],np.float32)
    hi=_resize(np.clip(col,0,1),shape)
    ring_hi=_resize(rings,shape); rim_hi=_resize(rim,shape); pore_hi=_resize(pore,shape)
    hi+=np.clip((ring_hi-.42)*5.0,0,1)[...,None]*np.array([.045,.025,.008],np.float32)
    hi+=np.clip((rim_hi-.48)*4.2,0,1)[...,None]*np.array([.035,.030,.012],np.float32)
    hi*=1-pore_hi[...,None]*.10
    return _blend(paint,mask,pm,np.clip(hi,0,1))


def spec_beetle_tortoise_i1(shape,seed,sm,base_m,base_r):
    shield,crown,boundary,rim,inner,rings,pore,abrasion,f0,f1,f2,stress=_surface(seed+9410)
    # Clear resin, brass rim, pearl interior, smoked underlayer, chrome pore
    # lip, matte abrasion and stressed red reflector all occupy distinct MRC.
    m=38+170*(.61*f0+.16*inner+.14*rim+.09*rings)-boundary*20-pore*28
    r=34+142*(.65*f1+.17*boundary+.12*abrasion+.06*pore)-crown*18-rim*13
    cc=10+238*(.62*f2+.17*boundary+.13*crown+.08*rings)-pore*24-abrasion*16
    m+=stress*26; r+=stress*19; cc-=stress*22
    m=np.clip(m*sm,0,235); r=np.clip(r,18,215); cc=np.clip(cc,0,255)
    return _resize(m,shape),_resize(r,shape),_resize(cc,shape)
