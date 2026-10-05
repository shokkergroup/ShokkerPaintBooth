"""Lemon Polka Pastille I2 — fine 1950s lemon-and-pearl candy print.

SPB-105 / SH-LEMON-POLKA-I2 / 2026-08-30.  Literal polka dots are retained
because they are this card's period language, but rebuilt as 6–18px pearl
pastilles with 1–3px candy halos, inset cream hearts and enamel pin-lines.
The 30px staggered print repeats are intentional fabric/paper geometry, not
random confetti; every dot face/halo/field state owns a material response.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)

def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&8191)*.0017
    # A deliberate staggered 30px polka print with mild hand-screen warp.
    u=x+1.35*np.sin(y/113.+phase);v=y+1.05*np.sin(x/127.-phase*.6)
    pitch=30.;row=np.floor(v/pitch).astype(np.int32);vv=_fract(v/pitch)-.5;uu=_fract((u+(row&1)*pitch*.5)/pitch)-.5
    gx=np.floor((u+(row&1)*pitch*.5)/pitch).astype(np.int32);gy=row
    code=np.mod(gx*17+gy*29+(gx^gy)*7+int(seed),4)
    # 6–18px pastille, 1–3px halo and a tiny inlaid face—not just flat dots.
    skew=.88+.12*((code&1)>0);r=np.sqrt((uu/skew)**2+vv**2)
    dot=np.clip((.325-r)/.105,0,1);halo=np.clip((.39-r)/.075,0,1)*np.clip((r-.25)/.09,0,1)
    rim=np.clip((.27-r)/.050,0,1)*np.clip((r-.13)/.07,0,1)
    heart=np.clip(1-np.hypot(uu/.105,(vv+.015)/.082),0,1)*dot
    pin=np.clip((.47-np.abs(vv))/ .05,0,1)*np.clip((.47-np.abs(uu))/ .05,0,1)
    paper=.5+.5*np.sin((u+v)/167.+.31*np.sin(v/43.))*np.sin((u-v)/191.-.21*np.sin(u/59.))
    lemon=np.array((.78,.55,.035),np.float32);custard=np.array((.98,.81,.16),np.float32)
    cream=np.array((.96,.91,.68),np.float32);pearl=np.array((.92,.98,.92),np.float32)
    chrome=np.array((.75,.82,.72),np.float32);amber=np.array((.56,.25,.025),np.float32)
    field=lemon*(.65+.18*paper[...,None])+custard*(.16+.12*(1-paper[...,None]))
    dotcol=np.where((code[...,None]&1)>0,pearl,cream)
    paint=field*(1-dot[...,None]*.82)+dotcol*(dot[...,None]*.82)
    paint=paint*(1-halo[...,None]*.50)+amber*(halo[...,None]*.50)
    paint=paint*(1-rim[...,None]*.60)+chrome*(rim[...,None]*.60)
    paint=paint*(1-heart[...,None]*.23)+cream*(heart[...,None]*.23)
    paint=paint*(1-pin[...,None]*.08)+amber*(pin[...,None]*.08)
    M=26+29*paper+73*dot+108*halo+144*rim+62*heart+27*(code==2)-18*pin
    R=214-22*paper-66*dot-97*halo-137*rim-54*heart+19*(code==1)+18*pin
    C=23+33*paper+78*dot+119*halo+151*rim+76*heart+31*(code==3)-15*pin
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value

def paint_lemon_polka_pastille(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)

def spec_lemon_polka_pastille(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
