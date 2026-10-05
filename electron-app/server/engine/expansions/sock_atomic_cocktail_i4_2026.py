"""Atomic Starburst I4 — compact 1950s cocktail-lounge enamel print.

SPB-105 / SH-ATOMIC-STARBURST-I4, 2026-08-30.  The legacy card had a good
atomic idea but oversized icon spacing plus an unrelated hatch grid.  I4
uses 64px compositions built from 8–28px cores, orbit arcs, star arms and
satellites, with no lattice filler. Material channels are bound to each
visible enamel/chrome/pigment component.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _angle_delta(a,b): return np.angle(np.exp(1j*(a-b)))


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);X,Y=x/q,y/q
    # Compact 64px station; the meaningful components within it are 8–28px.
    cell=64.; gx=X+1.2*np.sin(Y/167.)+.5*np.cos(Y/61.);gy=Y+1.0*np.sin(X/149.)+.4*np.cos(X/53.)
    px,py=np.mod(gx,cell)-32.,np.mod(gy,cell)-32.
    ix,iy=np.floor(gx/cell).astype(np.int32),np.floor(gy/cell).astype(np.int32)
    state=np.mod(ix*17+iy*29+(ix^iy)*3+int(seed),4).astype(np.int32)
    rot=(state.astype(np.float32)-1.5)*.19;cr,sr=np.cos(rot),np.sin(rot);u=px*cr-py*sr;v=px*sr+py*cr
    r=np.hypot(u,v);theta=np.arctan2(v,u)
    core=np.clip(1-r/7.0,0,1)
    # Six short 8–28px enamel rays, deliberately finite—not a radial macro.
    rays=np.zeros_like(r)
    for k in range(6):
        ang=-.35+k*np.pi/3
        rays=np.maximum(rays,np.exp(-np.square(_angle_delta(theta,ang)/.09))*np.clip((30-r)/8,0,1)*np.clip((r-7)/4,0,1))
    # Two chrome orbit arcs with gaps like cocktail-era screen printing.
    e1=np.sqrt((u/25.)**2+(v/10.5)**2);e2=np.sqrt((u/11.)**2+(v/24.)**2)
    orbit1=np.exp(-np.square((e1-1)/.090))*np.clip(.65+.35*np.cos(theta-.5),0,1)
    orbit2=np.exp(-np.square((e2-1)/.080))*np.clip(.60+.40*np.cos(theta+1.2),0,1)
    # Four explicit 8–14px satellites; cell state only changes their orbit.
    shift=(state.astype(np.float32)-1.5)*1.5
    def orb(cx,cy,rad): return np.clip(1-np.hypot(u-cx,v-cy)/rad,0,1)
    sat=np.maximum.reduce((orb(23+shift,5,5.8),orb(-22,10-shift,5.0),orb(6,22+shift,4.4),orb(-7,-23,4.8)))
    glint=np.maximum.reduce((orb(20+shift,4,2.1),orb(-20,9-shift,1.8),orb(5,20+shift,1.6)))
    # Subtle 8px printed halo is attached to the atomic core—no background grid.
    halo=np.exp(-np.square((r-15.5)/2.2))*np.clip(.42+.58*np.cos(3*theta+.4*np.sin(theta*2)),0,1)
    navy=np.array((.018,.085,.115),np.float32);teal=np.array((.035,.29,.32),np.float32)
    red=np.array((.90,.13,.09),np.float32);mustard=np.array((.94,.65,.11),np.float32)
    aqua=np.array((.04,.73,.68),np.float32);orange=np.array((.98,.34,.08),np.float32);pearl=np.array((.84,.87,.66),np.float32)
    paint=navy*(.80+.12*np.sin((X+Y)/81.)[...,None])+teal*(.08+.05*np.cos((X-Y)/57.)[...,None])
    # Variation is on the actual components, not a cell-wide recolor.
    ray_color=np.where((state[...,None]&1)>0,mustard,orange)
    paint=paint*(1-halo[...,None]*.34)+teal*(halo[...,None]*.34)
    paint=paint*(1-rays[...,None]*.92)+ray_color*(rays[...,None]*.92)
    paint=paint*(1-core[...,None]*.98)+red*(core[...,None]*.98)
    paint=paint*(1-orbit1[...,None]*.84)+pearl*(orbit1[...,None]*.84)
    paint=paint*(1-orbit2[...,None]*.82)+aqua*(orbit2[...,None]*.82)
    paint=paint*(1-sat[...,None]*.91)+orange*(sat[...,None]*.91)
    paint=paint*(1-glint[...,None]*.87)+pearl*(glint[...,None]*.87)
    M=29+23*halo+139*rays+164*core+182*orbit1+154*orbit2+126*sat+104*glint
    R=211-32*halo-111*rays-143*core-158*orbit1-137*orbit2-99*sat-84*glint
    C=38+31*halo+105*rays+123*core+169*orbit1+184*orbit2+111*sat+117*glint
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_atomic_cocktail(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_atomic_cocktail(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
