"""Private Houdini I25 — Veiled Reliquary, P1.

The ordinary carrier is fine obsidian jacquard.  Detailed small skulls recur
over the entire 2048² field but exist only as patterned M/Rough/Cc states: they
are absent from paint and must be discovered through material response.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock(); _TAU=np.float32(6.283185307179586)

def _h(i,j,s): return np.mod(np.sin(i*127.1+j*311.7+s*73.9)*43758.5453,1.0).astype(np.float32)
def _ell(x,y,sx,sy): return np.exp(-((x/sx)**2+(y/sy)**2)).astype(np.float32)

def _arrays(shape, seed):
    key=(*map(int,shape),int(seed))
    with _LOCK:
        if key in _CACHE: _CACHE.move_to_end(key); return _CACHE[key]
    h,w=map(int,shape); scale=min(1.,1024./max(h,w)); hh,ww=max(256,round(h*scale)),max(256,round(w*scale))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32); X,Y=xx/scale,yy/scale
    phase=(seed%7919)*.00081
    # Normal surface: two fine physical jacquard directions plus a very quiet
    # third thread. Components are 5–16px wide, dense, and intentional.
    U=(X*.866+Y*.500+3.0*np.sin(Y*.014+phase))/6.2
    V=(X*.500-Y*.866+2.5*np.sin(X*.016-phase))/7.1
    warp=.5+.5*np.sin(U*_TAU); weft=.5+.5*np.sin(V*_TAU)
    jac=np.clip(.50*warp+.42*weft+.22*warp*weft,0,1)
    tooth=.5+.5*np.sin((X*.31-Y*.18)+.8*np.sin(X*.027))
    # A deliberately distributed, slightly hand-set skull grammar. One full
    # skull is 34x39px, composed from 8–32px cranium, jaw, sockets, nasal and
    # tooth pieces. There are hundreds over a whole car, never one giant icon.
    dx=3.6*np.sin(Y*.012+phase)+2.0*np.sin((X+Y)*.009-phase)
    dy=3.2*np.sin(X*.014-phase*.7)-1.8*np.sin((X-Y)*.011+phase)
    # P2 — P1's 55px pitch made a skull technically present but unreadable as
    # a complete form.  72px spacing still repeats hundreds of discoveries on
    # a whole car, while preserving a real 8–32px eye/jaw/cranium anatomy.
    GX,GY=(X+dx)/72.,(Y+dy)/74.
    ci,cj=np.floor(GX),np.floor(GY)
    # P7 — P6's reveal was anatomically right but sat on a visible ruler grid.
    # Hand-set reliquary inlays vary placement, scale and rotation in a bounded
    # way; density remains full-canvas and nothing becomes a free scatter mark.
    cx=ci+.5+(_h(ci,cj,seed+11)-.5)*.48 + .13*np.sin(cj*1.37+ci*.41+phase)
    cy=cj+.5+(_h(ci,cj,seed+29)-.5)*.46 + .12*np.sin(ci*1.19-cj*.53-phase)
    qx,qy=(GX-cx)*72.,(GY-cy)*74.
    a=(_h(ci,cj,seed+47)-.5)*.72; ca,sa=np.cos(a),np.sin(a); qx,qy=qx*ca+qy*sa,-qx*sa+qy*ca
    setting=.87+.25*_h(ci,cj,seed+59); qx,qy=qx/setting,qy/setting
    cranium=_ell(qx,qy+5.5,19.5,18.5)
    cheek_l=_ell(qx+11.5,qy+9.5,8.4,9.2); cheek_r=_ell(qx-11.5,qy+9.5,8.4,9.2)
    jaw=np.clip(1-(np.maximum(np.abs(qx)/14.5,np.abs(qy-20.0)/8.5))**2,0,1)
    skull=np.clip(np.maximum(cranium,np.maximum(cheek_l,cheek_r))*.92+jaw*.82,0,1)
    eye_outer_l=_ell(qx+8.5,qy+4.5,7.5,8.2); eye_outer_r=_ell(qx-8.5,qy+4.5,7.5,8.2)
    eye_l=_ell(qx+8.5,qy+4.5,5.5,6.4); eye_r=_ell(qx-8.5,qy+4.5,5.5,6.4)
    orbital=np.clip(np.maximum(eye_outer_l,eye_outer_r)-np.maximum(eye_l,eye_r)*.72,0,1)
    nose=_ell(qx,qy+10.8,4.3,5.6)
    toothbar=np.exp(-((qy-20.0)/2.8)**2)*np.clip(1-(np.abs(qx)/13.0)**2,0,1)
    teeth=toothbar*(.5+.5*np.sin(qx*.72)**10)
    holes=np.clip(np.maximum(np.maximum(eye_l,eye_r),nose),0,1)
    # P4 — give the hidden skull real craft anatomy: raised orbital rims,
    # brow bar and cheek engraving, each literal to the material silhouette.
    brow=np.exp(-((qy+1.4)/2.3)**2)*np.clip(1-(np.abs(qx)/16.0)**2,0,1)
    cheek_cut=np.maximum(_ell(qx+12.2,qy+12.0,5.4,2.1),_ell(qx-12.2,qy+12.0,5.4,2.1))
    inner=np.clip(skull-holes*.92-teeth*.38,0,1)
    rim=np.clip(cv2.GaussianBlur(skull,(0,0),1.55)-inner*.63 + orbital*.54+brow*.32+cheek_cut*.30,0,1)
    # Paint must remain innocent: the skull mask never enters this section.
    # P6 — the P1–P5 neutral jacquard was structurally correct but too brown
    # and dead. Give the actual woven carrier a restrained sapphire/indigo
    # body and interference thread; this still contains zero skull-derived
    # paint data.
    tide=.5+.5*np.sin(X*.010+Y*.014+phase)
    base=np.dstack((.070+.060*jac+.018*tide, .043+.036*jac+.010*tide, .026+.022*jac+.006*tide))
    thread=np.dstack((.023*tooth, .013*tooth, .007*tooth))
    paint=np.clip(base+thread,0,1)
    # Material roles: woven satin is deliberately subdued. The recurring skull
    # uses four nested physical states so it resolves only as light moves.
    M=66+32*jac+13*tooth; R=178-34*jac-12*tooth; C=158-29*jac-10*tooth
    # P3 — P2 made each whole skull a single bright pill.  Separate rim,
    # bone, socket and tooth material roles so light can describe anatomy.
    # P8 — P7 revealed too much at once. Narrow the material window so the
    # skulls can recede in ordinary light and assemble more selectively.
    # P9 — alternate the physical plating depth per hand-set skull. The form
    # is still everywhere, but light does not activate every inlay equally.
    discovery=.24+.76*_h(ci,cj,seed+151)
    M=M+(108*rim+28*inner-47*holes+58*teeth+32*orbital+22*brow)*discovery
    R=R-(93*rim+22*inner-50*holes+39*teeth+25*orbital+16*brow)*discovery
    C=C-(111*rim+30*inner-55*holes+53*teeth+31*orbital+20*brow)*discovery
    # Small state changes stay inside the skull anatomy: documented dark
    # chrome/satin/candy/pearl/frozen/Fractured parcels, no paint recoloring.
    state=np.mod((ci.astype(np.int32)*5+cj.astype(np.int32)*3+np.floor(qx/8).astype(np.int32)),6)
    tabm=np.array((250,250,200,100,225,252),np.float32); tabr=np.array((15,45,15,40,140,38),np.float32); tabc=np.array((40,40,16,16,100,255),np.float32)
    parcel=(np.clip(.88*rim+.56*teeth,0,1)>.44) & (discovery>.48)
    M=np.where(parcel,.70*M+.30*tabm[state],M); R=np.where(parcel,.70*R+.30*tabr[state],R); C=np.where(parcel,.70*C+.30*tabc[state],C)
    # P5 — no identical wallpaper skulls. A deterministic, process-bound
    # plating history gives each complete inlay one of three restrained light
    # behaviors (buried satin / dark chrome / active coat), never a paint tint.
    history=np.floor(_h(ci,cj,seed+131)*3.0)-1.0
    M=np.clip(M + history*31.0*skull, 0, 255)
    R=np.clip(R - history*24.0*skull, 15, 255)
    C=np.clip(C - history*29.0*skull, 16, 255)
    spec=np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8)
    if (hh,ww)!=(h,w): paint=cv2.resize(paint.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC); spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_CUBIC)
    result=(np.clip(paint,0,1).astype(np.float32),spec)
    with _LOCK:
        _CACHE[key]=result
        if len(_CACHE)>2: _CACHE.popitem(last=False)
    return result

def paint_veiled_reliquary_i25(paint,shape,mask,seed,pattern_mix,bbox):
    del bbox; art,_=_arrays(shape,seed); source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5: source/=255.
    alpha=np.asarray(mask,np.float32); alpha=alpha[...,0] if alpha.ndim==3 else alpha; alpha=(np.clip(alpha,0,1)*np.clip(float(pattern_mix),0,1))[...,None]
    return np.clip(source*(1-alpha)+art*alpha,0,1).astype(np.float32)

def spec_veiled_reliquary_i25(shape,seed,spec_mix,base_metal,base_rough):
    del spec_mix,base_metal,base_rough; return _arrays(shape,seed)[1]
