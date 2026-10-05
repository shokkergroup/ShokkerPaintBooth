"""Pink Fleck Shattercoat I3 — irregular Candy Apple lacquer candidate.

SPB-105 / owner doctrine / 2026-08-30.  I2's square 16px cells created a
vertical/grid read. I3 uses irregular 8–32px paint cells made by a jittered
nearest-cell field: adjacent hot-pink candy, smoked chrome, pearl mica and
flat wine states are held inside coherent hand-sprayed regions. No regular
lattice, random glitter scatter, or detached spec channel is used.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _work_fields(h,w,seed):
    p=5.0  # 20px typical native cell after 4x upsample; 8–32px range via jitter
    y,x=np.mgrid[:h,:w].astype(np.float32)
    gx=np.floor(x/p).astype(np.int32); gy=np.floor(y/p).astype(np.int32)
    gh,gw=int(np.ceil(h/p))+4,int(np.ceil(w/p))+4
    rng=np.random.default_rng((int(seed)^0xCA11D) & 0xffffffff)
    jx=rng.uniform(-.34,.34,(gh,gw)).astype(np.float32);jy=rng.uniform(-.34,.34,(gh,gw)).astype(np.float32)
    cell=rng.integers(0,4,(gh,gw),dtype=np.int8)
    # Track first/second nearest jittered centres from the local 3x3 cells.
    d1=np.full((h,w),1e9,np.float32);d2=d1.copy();state=np.zeros((h,w),np.int8)
    px=np.zeros((h,w),np.float32);py=px.copy()
    for oy in (-1,0,1):
        for ox in (-1,0,1):
            ix=np.clip(gx+ox+2,0,gw-1);iy=np.clip(gy+oy+2,0,gh-1)
            sx=(gx+ox+.5)*p+jx[iy,ix]*p;sy=(gy+oy+.5)*p+jy[iy,ix]*p
            d=(x-sx)**2+(y-sy)**2
            hit=d<d1
            d2=np.where(hit,d1,np.minimum(d2,d));d1=np.where(hit,d,d)
            state=np.where(hit,cell[iy,ix],state);px=np.where(hit,sx,px);py=np.where(hit,sy,py)
    # Actual hand-spray zones organize the neighboring physical states.
    phase=(int(seed)&0xffff)*.0013
    spray=(.49*np.sin(x/57.+.31*np.sin(y/23.)+phase)+.31*np.sin(y/47.-.24*np.sin(x/29.)-phase*.7)+.20*np.sin((x+y)/79.+phase*1.3))
    family=np.mod(state+np.floor((spray+1.12)*2.38).astype(np.int8),4)
    edge=np.clip((np.sqrt(d2)-np.sqrt(d1))/.58,0,1)
    rim=1-edge
    local=np.hypot(x-px,y-py)/p
    mica=np.clip((np.sin((x-px)*2.2+.7*np.sin((y-py)*1.7))+.24-local)*.82,0,1)
    return family.astype(np.int8),rim.astype(np.float32),mica.astype(np.float32),spray.astype(np.float32),local.astype(np.float32)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    scale=min(1.,512./max(h,w));wh,ww=max(8,int(round(h*scale))),max(8,int(round(w*scale)))
    state,rim,mica,spray,local=_work_fields(wh,ww,seed)
    hot=(state==0).astype(np.float32);chrome=(state==1).astype(np.float32);pearl=(state==2).astype(np.float32);flat=(state==3).astype(np.float32)
    candy=.54+.34*np.clip(spray,-1,1)
    paint=np.zeros((wh,ww,3),np.float32)+np.array((.052,.005,.021),np.float32)
    paint+=np.stack((.71*candy,.020+.020*candy,.15+.15*candy),2)*hot[...,None]
    paint+=np.array((.38,.31,.41),np.float32)*chrome[...,None]*(.39+.29*(1-local[...,None]))
    paint+=np.array((.72,.20,.48),np.float32)*pearl[...,None]*(.35+.28*mica[...,None])
    paint+=np.stack((.22*candy,.010+.012*candy,.050+.08*candy),2)*flat[...,None]*(.42+.19*local[...,None])
    paint+=np.array((.80,.42,.62),np.float32)*(rim*.12)[...,None]
    paint+=np.array((.94,.57,.78),np.float32)*(mica*.10)[...,None]
    M=17+119*hot+165*chrome+108*pearl+31*flat+49*mica+71*rim+21*candy
    R=224-82*hot-124*chrome-96*pearl+33*flat-38*mica-89*rim+17*(1-candy)
    C=18+112*hot+143*chrome+151*pearl+34*flat+71*mica+96*rim+23*candy
    spec=np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8)
    if (wh,ww)!=(h,w):
        paint=cv2.resize(paint,(w,h),interpolation=cv2.INTER_CUBIC);spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
    res=(np.clip(paint,0,1).astype(np.float32),spec.astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_pink_fleck_shattercoat_i3(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_pink_fleck_shattercoat_i3(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
