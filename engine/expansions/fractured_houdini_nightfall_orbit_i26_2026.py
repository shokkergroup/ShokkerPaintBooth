"""Private Houdini I26 — Nightfall Orbit, P1.

An ordinary midnight-pearl moiré carries no visible symbol.  Across the full
surface, hand-set 8–32px logarithmic spiral arm/rim/core parcels exist only in
M/Rough/Cc, so compact galaxy forms assemble under changing illumination.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock(); _TAU=np.float32(6.283185307179586)
def _h(i,j,s): return np.mod(np.sin(i*127.1+j*311.7+s*73.9)*43758.5453,1.0).astype(np.float32)

def _arrays(shape,seed):
    key=(*map(int,shape),int(seed))
    with _LOCK:
        if key in _CACHE: _CACHE.move_to_end(key); return _CACHE[key]
    h,w=map(int,shape); scale=min(1.,1024./max(h,w)); hh,ww=max(256,round(h*scale)),max(256,round(w*scale))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32); X,Y=xx/scale,yy/scale
    phase=(seed%7919)*.00077
    # Innocent carrier: deliberately ordered pearl moiré, three fine optical
    # threads and a slow tide; no hidden-spiral field is used in paint.
    u=(X*.91+Y*.41+2.4*np.sin(Y*.014+phase))/8.0
    v=(X*.41-Y*.91+2.1*np.sin(X*.012-phase))/10.5
    warp=.5+.5*np.sin(u*_TAU); weft=.5+.5*np.sin(v*_TAU)
    pearl=.5+.5*np.sin(u*_TAU)*np.sin(v*_TAU)
    thread=.5+.5*np.sin((X*.27-Y*.19)+.6*np.sin(Y*.030))
    tide=.5+.5*np.sin(X*.009+Y*.012+phase)
    # P4 — P3's neutral pearl is too flat.  Add restrained blue-teal/violet
    # optical drift to the weave itself; no orbit coordinate is consulted.
    cyan=.5+.5*np.sin(X*.007-Y*.011+phase); violet=.5+.5*np.sin(X*.010+Y*.006-phase)
    # P10 — a fine oil-slick interference lies inside the pearl threads. It
    # is 8–20px optical weave structure, not a large color band or an orbit.
    slick=.5+.5*np.sin(X*.205+Y*.143+.75*np.sin(X*.031-Y*.022))
    paint=np.dstack((.070+.050*pearl+.019*tide+.014*thread+.030*cyan+.014*slick,
                      .040+.030*pearl+.011*tide+.007*thread+.020*cyan,
                      .052+.041*pearl+.016*tide+.011*thread+.034*violet+.014*(1-slick)))
    # Distributed compact orbits.  These are not a field of free curls: each
    # local setting has three coherent logarithmic arms, edge, body and core.
    dx=4*np.sin(Y*.010+phase)+2.2*np.sin((X+Y)*.008-phase); dy=3.2*np.sin(X*.011-phase*.6)-1.6*np.sin((X-Y)*.009+phase)
    GX,GY=(X+dx)/93.,(Y+dy)/91.; ci,cj=np.floor(GX),np.floor(GY)
    # P2 — P1's individual spirals read, but their rows were too regular.
    # Bounded setting variation maintains repeated full-car discovery without
    # creating a free random-curl field.
    cx=ci+.5+(_h(ci,cj,seed+17)-.5)*.54+.15*np.sin(cj*1.29+ci*.37+phase)
    cy=cj+.5+(_h(ci,cj,seed+31)-.5)*.52+.14*np.sin(ci*1.17-cj*.49-phase)
    qx,qy=(GX-cx)*93.,(GY-cy)*91.; a=(_h(ci,cj,seed+49)-.5)*_TAU; ca,sa=np.cos(a),np.sin(a); qx,qy=qx*ca+qy*sa,-qx*sa+qy*ca
    setting=.84+.29*_h(ci,cj,seed+59); qx,qy=qx/setting,qy/setting
    r=np.hypot(qx,qy)+.001; theta=np.arctan2(qy,qx); temper=_h(ci,cj,seed+67)
    # arm phase is radial-logarithmic; only 6–18px arm, rim and core pieces.
    spiral=theta-np.log(r/7.5)*(.82+.24*temper)+temper*_TAU
    # P6 — a single identical winding still felt stamped.  Each hand-set
    # orbit uses a bounded 1–3 arm cadence from the same spiral anatomy.
    arms=1.15+.88*_h(ci,cj,seed+83)
    arm=np.exp(-((np.sin(spiral*arms)/.24)**2))*np.exp(-(r/31.)**2)*(r>5)
    rim=np.exp(-((r-29.)/2.4)**2); core=np.exp(-(r/6.0)**2)
    # P5 — give each material-only galaxy an inner halo, a second 3–8px
    # physical annulus that makes an actual layered astronomical form.
    halo=np.exp(-((r-14.0)/1.65)**2)*(r>7)
    arm2=np.exp(-((np.sin(spiral*arms+1.07)/.18)**2))*np.exp(-(r/21.)**2)*(r>7)
    particle=np.exp(-((np.sin(spiral*(arms+1.35)+r*.21)/.14)**2))*np.exp(-((r-24.)/9.)**2)
    # Normal material follows pearl weave only; spiral details below are
    # material-only and therefore cannot print a galaxy into neutral paint.
    # P8 — P7's selective galaxies were correct but R spread fell below the
    # direct floor. Restore variation from the real fine weave itself, not a
    # louder motif: crossing threads take different satin/coat states.
    weave_delta=24.0*(warp-weft)
    M=70+32*pearl+15*thread+.35*weave_delta; R=174-36*pearl-14*thread+weave_delta; C=160-31*pearl-13*thread+.86*weave_delta
    # P3 — P2 advertised every outer ring like a printed gold coin. The rim
    # becomes a quiet shoulder; the smaller arms/core retain the discovery.
    # P7 — light must reveal a changing constellation, not equal bright
    # spirals. History drives the complete orbital hierarchy, not paint.
    history=.30+.70*_h(ci,cj,seed+173)
    M=M+(119*arm+78*rim+82*core+71*halo+96*arm2+56*particle)*history
    R=R-(92*arm+61*rim+59*core+52*halo+71*arm2+41*particle)*history
    C=C-(108*arm+73*rim+74*core+66*halo+85*arm2+51*particle)*history
    state=np.mod(ci.astype(np.int32)*7+cj.astype(np.int32)*5+np.floor(r/8).astype(np.int32),6)
    tm=np.array((250,250,200,100,225,252),np.float32); tr=np.array((15,45,15,40,140,38),np.float32); tc=np.array((40,40,16,16,100,255),np.float32)
    discovery=.32+.68*_h(ci,cj,seed+149)
    parcel=(np.clip(.78*arm+.33*rim+.47*halo+.61*arm2+.44*particle,0,1)>.40) & (discovery>.58)
    M=np.where(parcel,.64*M+.36*tm[state],M); R=np.where(parcel,.64*R+.36*tr[state],R); C=np.where(parcel,.64*C+.36*tc[state],C)
    # P9 — material chemistry varies inside the exact same orbit anatomy:
    # some are chrome-forward, some satin-buried, some clearcoat-active.
    chemistry=np.floor(_h(ci,cj,seed+211)*3.0)-1.0
    anatomy=np.clip(.72*arm+.31*rim+.43*halo+.58*arm2+.36*particle,0,1)
    M=np.clip(M+chemistry*24.0*anatomy,0,255)
    R=np.clip(R-chemistry*18.0*anatomy,15,255)
    C=np.clip(C-chemistry*22.0*anatomy,16,255)
    spec=np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8)
    if (hh,ww)!=(h,w): paint=cv2.resize(paint.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC); spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_CUBIC)
    result=(np.clip(paint,0,1).astype(np.float32),spec)
    with _LOCK:
        _CACHE[key]=result
        if len(_CACHE)>2: _CACHE.popitem(last=False)
    return result

def paint_nightfall_orbit_i26(paint,shape,mask,seed,pattern_mix,bbox):
    del bbox; art,_=_arrays(shape,seed); source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5: source/=255.
    alpha=np.asarray(mask,np.float32); alpha=alpha[...,0] if alpha.ndim==3 else alpha; alpha=(np.clip(alpha,0,1)*np.clip(float(pattern_mix),0,1))[...,None]
    return np.clip(source*(1-alpha)+art*alpha,0,1).astype(np.float32)
def spec_nightfall_orbit_i26(shape,seed,spec_mix,base_metal,base_rough):
    del spec_mix,base_metal,base_rough; return _arrays(shape,seed)[1]
