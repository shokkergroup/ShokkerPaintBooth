"""Formica Boomerang I3 — dense 1950s countertop print clusters.

SPB-105 / SH-FORMICA-BOOMERANG-I3, 2026-08-30.  Replaces the prior ~94px
single-motif station.  The first native screen was correctly small but too
quiet (M/R/Cc 18.6/17.9/21.7); I3b raised it to 32.7/31.6/37.8 but picker
coverage remained too timid. I3c reached 37.6/36.0/42.2; I3d now composes
multiple 8–24px marks into a readable 48px print cluster, never enlarging a
primitive. The owner doctrine is density > size. Paint and M/R/Cc match.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arc(dx,dy,radius,width,side):
    r=np.hypot(dx,dy);theta=np.arctan2(dy,dx)
    # A real boomerang is an open curved arm, not a circle or a loose line.
    gate=np.clip(1-np.abs(np.angle(np.exp(1j*(theta-side))))/.92,0,1)
    return np.clip(1-np.abs(r-radius)/width,0,1)*gate


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);u,v=x/q,y/q
    # 48px printed clusters, offset by a slight counter-layup drift.  Every
    # cluster holds several small components—never a single macro icon.
    gx=u+1.25*np.sin(v/107.)+.42*np.cos(v/41.);gy=v+.92*np.sin(u/97.)+.38*np.cos(u/33.)
    px,py=np.mod(gx,48.),np.mod(gy,48.)
    ix,iy=np.floor(gx/48.).astype(np.int32),np.floor(gy/48.).astype(np.int32)
    state=np.mod(ix*19+iy*11+(ix^iy)*7+int(seed),8).astype(np.int32)
    mirror=((ix+iy)&1).astype(np.float32)*2-1
    dx=(px-24.)*mirror;dy=py-24.
    # Three 8–24px nested arms and a tiny terminal make one period-specific
    # Formica print cluster. The state shifts their register, not their scale.
    nudge=(state.astype(np.float32)-3.5)*.28
    dark=_arc(dx+13.8,dy+7.2,8.2+nudge,2.00,-1.48)
    teal=_arc(dx+8.2,dy+11.4,10.9-nudge*.45,1.82,-1.32)
    coral=_arc(dx+12.2,dy+12.7,13.3+nudge*.25,1.60,-1.18)
    gold=_arc(dx+6.7,dy+6.2,6.1,1.34,-1.63)
    # A second offset cluster multiplies density while every arm remains
    # smaller than 24px. It is an authentic laminated print repeat, not grain.
    dark2=_arc(dx-13.0,dy-10.3,7.3-nudge*.35,1.78,1.60)
    teal2=_arc(dx-11.2,dy-9.5,9.4+nudge*.30,1.55,1.76)
    coral2=_arc(dx-14.5,dy-7.0,11.6,1.42,1.92)
    gold2=_arc(dx-12.0,dy-10.3,5.3,1.08,1.48)
    dark3=_arc(dx+1.5,dy-16.5,6.8+nudge*.25,1.42,-.14)
    teal3=_arc(dx-1.2,dy-14.6,9.1,1.26,.02)
    coral3=_arc(dx+2.9,dy-13.7,11.4,1.14,.19)
    terminal=np.clip(1-np.hypot(dx-7.6,dy+4.3)/2.25,0,1)*((state%3)!=0)
    # Quiet non-square base print lots preserve laminate body without creating
    # a large background tile.
    lot=.5+.5*np.sin((ix*2.17+iy*1.31)*1.7)
    cream=np.array((.88,.80,.65),np.float32); parchment=np.array((.72,.63,.49),np.float32)
    black=np.array((.045,.060,.070),np.float32); aqua=np.array((.025,.43,.50),np.float32)
    red=np.array((.83,.18,.105),np.float32); brass=np.array((.89,.64,.16),np.float32); pearl=np.array((.72,.84,.82),np.float32)
    paint=cream*(.86+.12*lot[...,None])+parchment*(.02+.03*(1-lot[...,None]))
    for layer,color,amt in ((dark,black,1.0),(teal,aqua,1.0),(coral,red,1.0),(gold,brass,.96),
                            (dark2,black,.92),(teal2,aqua,.91),(coral2,red,.91),(gold2,brass,.82),
                            (dark3,black,.82),(teal3,aqua,.82),(coral3,red,.82),(terminal,pearl,.82)):
        alpha=np.clip(layer*amt,0,1)[...,None];paint=paint*(1-alpha)+color*alpha
    s=state.astype(np.float32)
    M=25+s*9+dark*151+teal*184+coral*148+gold*194+dark2*131+teal2*165+coral2*132+gold2*174+dark3*121+teal3*150+coral3*126+terminal*112
    R=222-s*9-dark*174-teal*151-coral*125-gold*178-dark2*151-teal2*142-coral2*119-gold2*159-dark3*142-teal3*137-coral3*116-terminal*91
    C=22+s*12+dark*153+teal*190+coral*142+gold*171+dark2*142+teal2*181+coral2*134+gold2*157+dark3*137+teal3*169+coral3*129+terminal*129
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_formica_micro_boomerang(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_formica_micro_boomerang(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
