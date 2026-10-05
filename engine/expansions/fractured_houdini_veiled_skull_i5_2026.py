"""FRACTURED HOUDINI H1-I5 — Veiled Skull / nocturne lacquer atlas.

Clean replacement after I4a–I4d were rejected: no outlined skulls, no checker
carrier, no flat red/cyan icon.  A complete graphite-violet engraved lacquer
owns the paint.  Hidden skulls only bias the distribution of fine physical
states within the lacquer, allowing the form to emerge from moving material.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock(); _WORK = 640


def _f(a): return a-np.floor(a)
def _up(a,w,h): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)


def _points(rng,w,h,n):
    out=[]
    for _ in range(n*160):
        if len(out)>=n: break
        p=(float(rng.uniform(-30,w+30)),float(rng.uniform(-38,h+38)))
        if all((p[0]-q[0])**2+(p[1]-q[1])**2>67**2 for q in out): out.append(p)
    return out


def _arrays(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE: _CACHE.move_to_end(key); return _CACHE[key]
    sc=min(1.,_WORK/max(h,w)); hh,ww=max(160,round(h*sc)),max(160,round(w*sc))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32); rng=np.random.default_rng(int(seed)^0xC0FF17)

    # A continuous engraved-lacquer carrier: five related mark families, all
    # fine at final scale—ribbon engravings, crossgrain, mica pools, pin scars,
    # and elongated brush catches. No single regular cell/carpet is present.
    u=xx+9*np.sin(yy/28)+3.5*np.sin((xx-yy)/46)+2*np.cos(yy/8.3)
    v=yy+8*np.cos(xx/34)+3*np.sin((xx+2*yy)/58)
    ribbon=np.clip(.15-np.abs(np.sin((u+8*np.sin(v/21)+3*np.sin(u/39))/3.25))*.78,0,1)
    cross=np.clip(.10-np.abs(np.sin((v+6*np.cos(u/25)+4*np.sin(v/47))/4.15))*.59,0,1)
    poolraw=.5+.5*np.sin(u/33+.8*np.sin(v/45)+np.cos((u-v)/67))
    poolraw*=.5+.5*np.cos(v/37+.6*np.sin(u/31))
    pool=np.clip((poolraw-.54)*2.8,0,1)
    scratch=np.clip(.09-np.abs(np.sin((u*.94+v*.19)/2.15))*1.10,0,1)*(1-pool*.5)
    q=.5+.5*np.sin(u*1.51+v*.37+np.sin(v/7.0)*1.9)
    mica=np.clip((q-.89)*8.3,0,1)*(1-ribbon*.36)

    # Material-only skull envelopes.  These are intentionally not stroked:
    # anatomy is a population bias filled with existing lacquer marks.  Eyes,
    # nose and jaw only alter the fine state probabilities, eliminating a
    # cartoon silhouette in paint or the literal Combined diagnostic.
    skull=np.zeros((hh,ww),np.float32); orbital=np.zeros_like(skull); jaw=np.zeros_like(skull); halo=np.zeros_like(skull)
    for cx,cy in _points(rng,ww,hh,max(18,int(hh*ww/35000))):
        rx,ry=rng.uniform(21,29),rng.uniform(27,36); ang=rng.uniform(-.38,.38); ca,sa=np.cos(ang),np.sin(ang)
        X=((xx-cx)*ca+(yy-cy)*sa)/rx; Y=(-(xx-cx)*sa+(yy-cy)*ca)/ry
        crown=np.clip(1-(X*X+((Y+.12)/.88)**2),0,1)
        chin=np.clip(1-((np.abs(X)/.60)**2+((Y-.57)/.35)**2),0,1)
        body=np.maximum(crown,chin)
        e1=np.clip(1-(((X+.31)/.29)**2+((Y+.04)/.22)**2),0,1)
        e2=np.clip(1-(((X-.31)/.29)**2+((Y+.04)/.22)**2),0,1)
        nn=np.clip(1-((X/.12)**2+((Y-.27)/.18)**2),0,1)
        skull=np.maximum(skull,body)
        orbital=np.maximum(orbital,np.maximum(e1,e2))
        orbital=np.maximum(orbital,nn*.72)
        jaw=np.maximum(jaw,chin*np.clip((Y-.33)*2.7,0,1))
        rr=np.sqrt(X*X+Y*Y)
        halo=np.maximum(halo,np.clip(.12-np.abs(rr-1.06),0,1)*8.0)
    # Fine state grammar, not a visible motif: texture phase changes inside
    # each envelope and cavity. The skull only exists in repeated relationships.
    phase=.5+.5*np.sin((u+13*np.sin(v/29)+5*np.sin(u/61))/7.25)
    state=np.clip((phase*10).astype(np.int32),0,9)
    secret_phase=np.clip((phase+skull*.23-orbital*.31+jaw*.17+halo*.10)*10,0,9).astype(np.int32)
    mix=np.clip(skull*.50+halo*.18,0,.62)
    use=np.where(mix>.13,secret_phase,state)

    # Visible colour remains the lacquer, with no anatomy variables below.
    graphite=np.array((.075,.090,.135),np.float32); violet=np.array((.155,.145,.245),np.float32)
    steel=np.array((.265,.300,.470),np.float32); mica_rgb=np.array((.50,.43,.68),np.float32)
    paint=np.broadcast_to(graphite,(hh,ww,3)).copy()
    paint=paint*(1-(pool*.46)[...,None])+violet*(pool*.46)[...,None]
    paint=paint*(1-(ribbon*.34)[...,None])+steel*(ribbon*.34)[...,None]
    paint=paint*(1-(cross*.18)[...,None])+violet*(cross*.18)[...,None]
    paint=paint*(1-(scratch*.16)[...,None])+steel*(scratch*.16)[...,None]
    paint=paint*(1-(mica*.31)[...,None])+mica_rgb*(mica*.31)[...,None]

    # Ten deliberately independent material cards—the Hologram Metal lesson—
    # chosen to pack as graphite/violet/rose rather than a childish R/G mask.
    M=np.array((95,130,165,205,232,248,215,178,140,110),np.float32)
    R=np.array((145,112,88,61,40,24,36,73,105,128),np.float32)
    C=np.array((205,175,144,210,175,226,155,190,130,170),np.float32)
    metal=M[use]; rough=R[use]; coat=C[use]
    # Carrier anatomy moves all channels differently.  The secret does not
    # overwrite them; it changes their local distribution and gets its own
    # subtle polish/recess terms, providing real angle disagreement.
    metal += pool*31+ribbon*37+cross*19+mica*24-scratch*18
    rough += -pool*32-ribbon*39-cross*17-mica*21+scratch*28
    coat += -pool*36-ribbon*31-cross*14-mica*17+scratch*26
    metal += skull*18-orbital*32+jaw*11+halo*20
    rough += -skull*21+orbital*44-jaw*12+halo*9
    coat += -skull*18+orbital*34-jaw*17+halo*14
    if (hh,ww)!=(h,w): paint=_up(paint,w,h); metal,rough,coat=(_up(a,w,h) for a in (metal,rough,coat))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_veiled_skull_i5(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    cov=np.asarray(mask,np.float32); cov=cov[...,0] if cov.ndim==3 else cov
    return np.clip(src*(1-np.clip(cov,0,1)[...,None]*pm)+authored*(np.clip(cov,0,1)[...,None]*pm),0,1).astype(np.float32)


def spec_veiled_skull_i5(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
