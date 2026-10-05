"""Flower Power I6 — dense 1960s silk-screen garden cloth.

SPB-105 / GV-FLOWER-POWER-I6, 2026-08-30.  The live I5 has believable
flowers but macro vine sweeps and a separate diagonal weave. I6 uses 64px
screen-print clusters containing only 8–28px flower petals, seed discs,
buds, leaf curls and registration rims. Initial I6 was material-valid but
too shy at picker (M/R/Cc 28.2/25.7/28.4); I6b increases coverage/contrast,
not primitive size. No unrelated lattice or grain rescue.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _flower(u,v,cx,cy,scale,count,rot):
    dx,dy=u-cx,v-cy;r=np.hypot(dx,dy);a=np.arctan2(dy,dx)-rot
    lobe=.66+.34*np.cos(count*a)
    petals=np.clip((scale*lobe-r)/(scale*.20),0,1)*np.clip((r-scale*.20)/(scale*.16),0,1)
    rim=np.exp(-np.square((r-scale*lobe)/(scale*.085)))*np.power(.5+.5*np.cos(count*a),5)
    seed=np.clip(1-r/(scale*.25),0,1)
    return petals,rim,seed


def _leaf(u,v,cx,cy,angle):
    dx,dy=u-cx,v-cy;ca,sa=np.cos(angle),np.sin(angle);a=dx*ca+dy*sa;b=-dx*sa+dy*ca
    return np.clip(1-(a/10.)**2-(b/3.4)**2,0,1)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);X,Y=x/q,y/q
    cell=64.;gx=X+1.1*np.sin(Y/151.)+.45*np.cos(Y/57.);gy=Y+.9*np.sin(X/137.)+.38*np.cos(X/49.)
    u,v=np.mod(gx,cell)-32.,np.mod(gy,cell)-32.;ix,iy=np.floor(gx/cell).astype(np.int32),np.floor(gy/cell).astype(np.int32)
    state=np.mod(ix*11+iy*23+(ix^iy)*5+int(seed),4).astype(np.int32);rot=(state.astype(np.float32)-1.5)*.27
    # Per-print-cell offsets stop the old stamped cadence. Every flower is
    # still 6–28px: variation is placement, colour pass and petal anatomy,
    # never an oversized decal.
    h1=np.mod(np.sin(ix*17.31+iy*31.73+seed*.11)*43758.545,1.)
    h2=np.mod(np.sin(ix*41.17-iy*19.29+seed*.07)*21743.321,1.)
    h3=np.mod(np.sin(ix*23.71+iy*11.49+seed*.13)*13271.917,1.)
    cx1=2.+(h1-.5)*18.;cy1=-5.+(h2-.5)*16.;s1=13.5+h3*4.8
    cx2=-18.+(h2-.5)*10.;cy2=15.+(h3-.5)*9.;s2=7.0+h1*4.3
    cx3=18.+(h3-.5)*10.;cy3=17.+(h1-.5)*10.;s3=5.3+h2*3.6
    p1,r1,c1=_flower(u,v,cx1,cy1,s1,5+(state&1)*2,rot+(h1-.5)*.65)
    p2,r2,c2=_flower(u,v,cx2,cy2,s2,5+(state>>1),rot+.72+(h2-.5)*.8)
    p3,r3,c3=_flower(u,v,cx3,cy3,s3,6-(state&1),rot-.46+(h3-.5)*.9)
    leaf1=_leaf(u,v,cx1-12,cy1-12,rot+.23);leaf2=_leaf(u,v,cx2+5,cy2-13,rot-.62);leaf3=_leaf(u,v,cx3-13,cy3-7,rot+1.12)
    # Small curved stem segments are part of flowers, short enough to avoid
    # the former macro-vine problem.
    stem=np.clip(1-np.abs((v-(cy1+9))-.10*(u-cx1)**2)/1.35,0,1)*np.clip((20-np.abs(u-cx1))/6.,0,1)
    stem2=np.clip(1-np.abs((v-(cy2-4))+.10*(u-cx2)**2)/1.15,0,1)*np.clip((14-np.abs(u-cx2))/5.,0,1)
    navy=np.array((.025,.075,.13),np.float32);ink=np.array((.045,.17,.23),np.float32)
    pink=np.array((.93,.10,.37),np.float32);purple=np.array((.53,.12,.75),np.float32);orange=np.array((.98,.34,.08),np.float32)
    yellow=np.array((.98,.72,.12),np.float32);mint=np.array((.05,.68,.48),np.float32);pearl=np.array((.73,.86,.76),np.float32)
    paint=navy*(.82+.10*np.sin((X-Y)/89.)[...,None])+ink*(.08+.04*np.cos((X+Y)/67.)[...,None])
    primary=np.where((state[...,None]&1)>0,pink,purple);secondary=np.where((state[...,None]&1)>0,purple,pink)
    for layer,color,amt in ((stem,mint,.84),(stem2,mint,.76),(leaf1,mint,.98),(leaf2,mint,.94),(leaf3,mint,.88),
                            (p1,primary,1.0),(r1,pearl,.73),(c1,yellow,1.0),(p2,orange,.98),(r2,pearl,.62),(c2,yellow,.97),
                            (p3,secondary,.96),(r3,pearl,.57),(c3,yellow,.94)):
        alpha=np.clip(layer*amt,0,1)[...,None];paint=paint*(1-alpha)+color*alpha
    M=27+stem*51+stem2*43+leaf1*82+leaf2*76+leaf3*71+p1*142+r1*99+c1*163+p2*111+r2*86+c2*132+p3*105+r3*78+c3*121
    R=213-stem*57-stem2*49-leaf1*98-leaf2*89-leaf3*83-p1*121-r1*78-c1*142-p2*92-r2*64-c2*111-p3*87-r3*60-c3*104
    C=31+stem*74+stem2*63+leaf1*116+leaf2*104+leaf3*94+p1*127+r1*117+c1*151+p2*102+r2*101+c2*132+p3*111+r3*96+c3*125
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_flower_garden(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_flower_garden(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
