"""Oil Slick Groove I3 — dense wet-film interference lenses.

SPB-105 / GV-OIL-SLICK-I3, 2026-08-30.  The legacy groove is literal rainbow
stripes plus an unrelated green spec panel.  I3 takes the owner-approved
Oil-Slick/Fractured insight into a new mechanism: packed 8–24px wet-film
lenses with per-lens pigment, mica rim, dark trough and clearcoat state.
Neighboring cells differ deliberately; there are no global bands, confetti,
or a shared generic spec texture.
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
    # Staggered 24px wet-film cells; gentle local warp breaks a wallpaper grid
    # while each individual lens remains a fine physical oil-interference unit.
    gy=v+1.2*np.sin(u/83.)+.55*np.cos(u/29.);row=np.floor(gy/20.).astype(np.int32)
    gx=u+((row&1)*12.)+1.0*np.sin(v/91.)+.42*np.cos(v/37.);col=np.floor(gx/24.).astype(np.int32)
    lx=np.mod(gx,24.)-12.;ly=np.mod(gy,20.)-10.
    code=np.mod(col*17+row*31+(col^row)*7+int(seed),8).astype(np.int32)
    # Cell-local aspect/shift gives lens variety without loose particles.
    jx=((code%4).astype(np.float32)-1.5)*.55;jy=((code//2).astype(np.float32)-1.5)*.45
    rr=np.sqrt(np.square((lx-jx)/(9.3+(code%3)))+np.square((ly-jy)/(7.3+((code+1)%3))))
    body=np.clip((1.03-rr)/.23,0,1)
    rim=np.exp(-np.square((rr-.77)/.105));inner=np.exp(-np.square((rr-.46)/.16))
    trough=np.clip((rr-.98)/.18,0,1)
    # A short 3–8px oil highlight crescent is tied to its lens geometry.
    cres=np.exp(-np.square((rr-.60)/.075))*np.clip((ly-jy+2.7)/4.0,0,1)
    mica=np.exp(-np.square((rr-.27)/.11))*np.clip((lx-jx+4.0)/5.0,0,1)
    pal=np.array(((.11,.025,.28),(.025,.18,.52),(.018,.47,.49),(.25,.035,.58),(.73,.035,.34),(.78,.23,.035),(.54,.62,.04),(.06,.37,.66)),np.float32)
    pigment=pal[code]
    troughc=np.array((.004,.003,.013),np.float32);mica_c=np.array((.74,.96,.98),np.float32)
    hot=np.array((.98,.27,.67),np.float32);gold=np.array((.96,.76,.22),np.float32)
    paint=troughc*(.92+.08*np.sin((u+v)/73.)[...,None])
    paint=paint*(1-body[...,None]*.94)+pigment*(body[...,None]*.94)
    paint=paint*(1-inner[...,None]*.25)+hot*(inner[...,None]*.25)
    paint=paint*(1-rim[...,None]*.60)+gold*(rim[...,None]*.60)
    paint=paint*(1-cres[...,None]*.73)+mica_c*(cres[...,None]*.73)
    paint=paint*(1-mica[...,None]*.52)+mica_c*(mica[...,None]*.52)
    s=code.astype(np.float32)
    M=16+s*12+body*(55+s*7)+inner*42+rim*149+cres*89+mica*64-trough*8
    R=241-s*12-body*(46+s*6)-inner*31-rim*163-cres*77-mica*53-trough*5
    C=11+s*15+body*(57+s*8)+inner*53+rim*166+cres*108+mica*81-trough*4
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_oil_lens(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_oil_lens(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
