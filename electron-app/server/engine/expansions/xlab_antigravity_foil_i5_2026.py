"""X LAB Anti-Gravity Foil I5 — shingled microfoil with impossible shadows.

SPB-105 / XLAB-FOIL-I5, 2026-08-30.  The generic X LAB recipe shipped as
mint dots with an unrelated magenta spec panel.  I5 is dedicated material
work: 8–20px overlapping foil lozenges, local edge chrome, and per-facet
shadow offsets that intentionally disagree with the highlight direction.
Every change in M/R/Cc follows the same physical foil pass.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);u,v=x/q,y/q
    # Continuous overlapping foil sheet: narrow 18x16px lozenges with a
    # staggered seam, not individual confetti objects or macro planes.
    gy=v+0.95*np.sin(u/79.)+.35*np.cos(u/31.);row=np.floor(gy/16.).astype(np.int32)
    gx=u+((row&1)*9.)+0.75*np.sin(v/83.)+.30*np.cos(v/41.);col=np.floor(gx/18.).astype(np.int32)
    lx=np.mod(gx,18.)-9.;ly=np.mod(gy,16.)-8.;code=np.mod(col*19+row*11+(col^row)*5+int(seed),8).astype(np.int32)
    # Primary foil diamond: 8–20px diagonal span. Soft joins keep it a woven
    # sheet rather than a regular dot field.
    diamond=np.clip(1-(np.abs(lx)/8.6+np.abs(ly)/6.8),0,1)
    inner=np.clip(1-(np.abs(lx)/5.8+np.abs(ly)/4.3),0,1)
    edge=np.clip(diamond-inner,0,1)
    # Opposite signed micro-shadows are deliberate anti-gravity information.
    sx=np.where((code&1)>0,-2.35,2.35);sy=np.where((code&2)>0,1.65,-1.65)
    shadow=np.clip(1-(np.abs(lx-sx)/8.6+np.abs(ly-sy)/6.8),0,1)*(1-diamond*.75)
    gleam=np.clip(1-(np.abs(lx+1.6)/4.0+np.abs(ly+1.4)/2.1),0,1)*inner
    # Four deliberately interleaved foil alloys; neighboring pieces own
    # different pigment and material states just like the Hologram lesson.
    alloy=np.array(((.08,.42,.31),(.44,.86,.43),(.86,.63,.17),(.50,.72,.71),(.12,.19,.22),(.76,.93,.68),(.21,.55,.47),(.92,.78,.35)),np.float32)[code]
    void=np.array((.004,.010,.012),np.float32);chrome=np.array((.75,.95,.86),np.float32);shade=np.array((.006,.018,.018),np.float32)
    paint=void*(.84+.10*np.sin((u-v)/91.)[...,None])
    paint=paint*(1-shadow[...,None]*.86)+shade*(shadow[...,None]*.86)
    paint=paint*(1-diamond[...,None]*.95)+alloy*(diamond[...,None]*.95)
    paint=paint*(1-edge[...,None]*.60)+chrome*(edge[...,None]*.60)
    paint=paint*(1-gleam[...,None]*.72)+chrome*(gleam[...,None]*.72)
    s=code.astype(np.float32)
    M=17+s*13+diamond*(69+s*7)+edge*132+gleam*74-shadow*9
    R=239-s*13-diamond*(54+s*7)-edge*153-gleam*63-shadow*4
    C=14+s*15+diamond*(61+s*8)+edge*151+gleam*92-shadow*6
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_antigravity_foil(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_antigravity_foil(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
