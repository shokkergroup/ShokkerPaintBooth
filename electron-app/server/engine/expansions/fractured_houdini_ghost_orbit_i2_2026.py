"""FRACTURED HOUDINI H3-I2 — Ghost Orbit, isolated P1.

The neutral finish is midnight opal enamel: fine lapidary crescents, short
guilloche cuts, pearl pinwork and cooled indigo seams.  It contains no galaxy
paint.  Thirty distributed 8–32px-native spiral discoveries only alter M/R/Cc.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
_CACHE,_LOCK=OrderedDict(),RLock()

def _make(shape,seed):
    h,w=map(int,shape); sc=min(1.,1024./max(h,w)); hh,ww=max(128,round(h*sc)),max(128,round(w*sc)); y,x=np.mgrid[0:hh,0:ww].astype(np.float32); rng=np.random.default_rng(int(seed)^0x3A71)
    cuts=np.zeros((hh,ww),np.uint8); rims=np.zeros_like(cuts); pearls=np.zeros_like(cuts); seam=np.zeros_like(cuts)
    # Fine non-rowed lapidary anatomy: every mark is 2–14 authored pixels,
    # resolving to 8–28px on a 2048 carrier; no tessellation or macro spiral.
    # P2: P1's lapidary grammar was right but too quiet at picker scale.
    # Increase fine-event density, never its native size.
    for _ in range(max(3600,int(hh*ww/290))):
        cx,cy=rng.uniform(-18,ww+18),rng.uniform(-18,hh+18); rx,ry=rng.uniform(3.0,9.5),rng.uniform(1.8,6.5); a0=rng.uniform(0,6.28); arc=rng.uniform(.36,1.72); th=int(rng.integers(1,3)); t=np.linspace(a0,a0+arc,8); pts=np.column_stack((cx+rx*np.cos(t),cy+ry*np.sin(t))).astype(np.int32)
        cv2.polylines(cuts,[pts],False,int(rng.integers(75,190)),th,cv2.LINE_AA)
        if rng.random()<.54: cv2.polylines(rims,[pts[2:7]],False,int(rng.integers(95,230)),1,cv2.LINE_AA)
        if rng.random()<.32: cv2.circle(pearls,tuple(pts[len(pts)//2]),int(rng.integers(1,3)),int(rng.integers(110,255)),-1,cv2.LINE_AA)
    # Fine guilloche fragments make the field authored rather than a bag of arcs.
    for _ in range(max(150,int(hh*ww/8500))):
        cx,cy=rng.uniform(-32,ww+32),rng.uniform(-28,hh+28); ang=rng.uniform(-.7,.7); span=rng.uniform(18,45); amp=rng.uniform(4,10); ts=np.linspace(-1,1,13); pts=np.column_stack((ts*span,amp*np.sin(ts*np.pi)+ts*ts*amp*.35)); R=np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]],np.float32); pts=(pts@R.T+np.array((cx,cy))).astype(np.int32)
        for a,b in zip(pts[::2][:-1],pts[::2][1:]): cv2.line(seam,tuple(a),tuple(b),int(rng.integers(92,205)),2,cv2.LINE_AA)
    # Every secret is a small, uneven galaxy, repeated across the whole carrier.
    secret=np.zeros_like(cuts); state=np.zeros_like(cuts)
    for n in range(max(30,int(hh*ww/34000))):
        cx,cy=rng.uniform(24,ww-24),rng.uniform(24,hh-24); rad=rng.uniform(9.5,15.5); ang=rng.uniform(-.65,.65); R=np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]],np.float32)
        for arm in range(2):
            t=np.linspace(.25,5.1,34); r=rad*(.08+.135*t); p=np.column_stack((np.cos(t+arm*np.pi+arm*.28)*r,np.sin(t+arm*np.pi+arm*.28)*r*.73))@R.T+np.array((cx,cy)); p=p.astype(np.int32); cv2.polylines(secret,[p],False,int(110+(n+arm*3)%8*17),int(rng.integers(1,3)),cv2.LINE_AA); cv2.polylines(cuts,[p],False,int(rng.integers(74,164)),1,cv2.LINE_AA); cv2.polylines(rims,[p[8:27]],False,int(rng.integers(85,177)),1,cv2.LINE_AA); q=(n*3+arm*5+seed)%8; tmp=np.zeros_like(state);cv2.polylines(tmp,[p],False,int(q+1),int(rng.integers(1,3)),cv2.LINE_AA);state=np.where(tmp>0,tmp,state)
        cv2.circle(secret,(round(cx),round(cy)),int(rng.integers(2,4)),255,-1,cv2.LINE_AA)
    c=cuts.astype(np.float32)/255; r=rims.astype(np.float32)/255; p=pearls.astype(np.float32)/255; s=seam.astype(np.float32)/255; relief=cv2.GaussianBlur(np.maximum(c,r*.85),(0,0),2.0); field=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);field=(field-field.min())/(np.ptp(field)+1e-6)
    # P5: richer, local violet rim enamel makes the neutral lapidary material
    # read at picker scale; it follows ordinary rim cuts only, never a secret.
    ink=np.array((.016,.030,.092),np.float32); indigo=np.array((.065,.155,.390),np.float32); violet=np.array((.255,.105,.475),np.float32); pearl=np.array((.52,.66,.98),np.float32); paint=ink*(.57+.16*field[...,None])+indigo*(.31+.18*field[...,None]); paint=paint*(1-(relief*.28)[...,None])+indigo*(relief*.28)[...,None];paint=paint*(1-(c*.56)[...,None])+indigo*(c*.56)[...,None];paint=paint*(1-(r*.54)[...,None])+violet*(r*.54)[...,None];paint=paint*(1-(p*.60)[...,None])+pearl*(p*.60)[...,None];paint=paint*(1-(s*.38)[...,None])+pearl*(s*.38)[...,None]
    # P3: P2's channels were mechanically inverse copies (M↔R↔Cc).  Give
    # each local enamel element a separate fine response phase so chrome,
    # satin and clearcoat lighting can disagree rather than brighten as one.
    mphase=.5+.5*np.sin(x/7.3 + .71*np.sin(y/9.7) + seed*.013)
    rphase=.5+.5*np.sin((x-y)/8.9 + .54*np.cos(y/6.1) - seed*.017)
    cphase=.5+.5*np.cos((.43*x+.77*y)/10.1 + .38*np.sin(x/5.7) + seed*.011)
    # P4: amplify independent 8–24px phase parcels and ease the common
    # relief contribution.  The ornamental carrier remains continuous while
    # its metallic, satin and clearcoat personalities stop moving in lockstep.
    m=48+field*22+mphase*61+relief*43+c*67+r*38+p*79+s*52
    rough=214-field*17-rphase*55-relief*39-c*59-r*44-p*67-s*37
    coat=37+field*19+cphase*66+relief*49+c*72+r*47+p*86+s*59
    q=np.mod(np.maximum(state,1)-1,8); sm=np.array([250,155,216,91,238,173,122,200],np.float32); sr=np.array([14,68,35,129,25,81,108,47],np.float32); sc=np.array([249,142,203,92,234,171,116,190],np.float32); hit=secret>0;m=np.where(hit,sm[q],m);rough=np.where(hit,sr[q],rough);coat=np.where(hit,sc[q],coat)
    if (hh,ww)!=(h,w):
        up=lambda a:cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,rough,coat=map(up,(m,rough,coat))
    return np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(rough,15,255),np.clip(coat,16,255))).astype(np.uint8)
def _arrays(shape,seed):
    k=(*map(int,shape),int(seed))
    with _LOCK:
        if k in _CACHE:_CACHE.move_to_end(k);return _CACHE[k]
    v=_make(shape,seed)
    with _LOCK:_CACHE[k]=v;_CACHE.popitem(last=False) if len(_CACHE)>2 else None
    return v
def paint_ghost_orbit_i2(paint,shape,mask,seed,pm,bb):
    del bb;a,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;mask=np.asarray(mask,np.float32);mask=mask[...,0] if mask.ndim==3 else mask;mix=(np.clip(mask,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+a*mix,0,1).astype(np.float32)
def spec_ghost_orbit_i2(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r;return _arrays(shape,seed)[1]
