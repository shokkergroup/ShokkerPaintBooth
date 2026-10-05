"""Groovy Vibes Mushroom Fade I2 — connected psychedelic mycelium material.

SPB-105 / owner native-scale audit, 2026-08-29.  Replaces macro cap art and
free spores with a continuous earth-resin sheet: 8–32px gill currents and
mycelial seams are attached to broad organic flow rather than scattered.
Not wired until picker review proves it materially stronger.
"""
import cv2
import numpy as np


def _fields(shape, seed):
    h,w=shape[:2]; work=min(1024,max(h,w)); sc=work/max(h,w)
    wh,ww=max(32,int(h*sc)),max(32,int(w*sc))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); xn=x/max(ww,1); yn=y/max(wh,1)
    rng=np.random.default_rng((int(seed)^0x5A17C) & 0xffffffff)
    # Underlying continuous fungal-resin migration, never tiled or dotted.
    warp=.075*np.sin(10*yn+.7*np.sin(5*xn))+.045*np.sin(17*xn-5*yn)
    u=xn+warp; v=yn+.065*np.sin(8*xn+warp*4)
    pools=np.zeros((wh,ww),np.float32)
    for _ in range(13):
        cx,cy=rng.uniform(0,1),rng.uniform(0,1); rx,ry=rng.uniform(.10,.26),rng.uniform(.08,.21)
        pools += rng.uniform(.35,1.0)*np.exp(-(((u-cx)/rx)**2+((v-cy)/ry)**2)*2.2)
    pools=np.tanh(pools*.72)
    drift=10*u+6*v+2.5*np.sin(7*u)-1.6*np.sin(9*v)+4.0*pools
    # 8–32px native nested gill anatomy. The middle seams are not an overlay:
    # every ridge bends with the same organic migration as the pigment field.
    gill=.5+.5*np.sin(2*np.pi*drift*2.9)
    fine=np.exp(-((np.abs((drift*5.4)%1-.5)-.5)/.105)**2)
    seam=np.exp(-((np.abs((drift*1.8)%1-.5)-.5)/.070)**2)
    warm=.5+.5*np.sin(5*u-6*v+3*pools)
    cool=.5+.5*np.sin(7*v+4*u-4*pools)
    if (wh,ww)!=(h,w):
        def rs(a):return cv2.resize(a,(w,h),interpolation=cv2.INTER_CUBIC)
        pools,gill,fine,seam,warm,cool=map(rs,(pools,gill,fine,seam,warm,cool))
    return tuple(np.clip(a,0,1).astype(np.float32) for a in (pools,gill,fine,seam,warm,cool))


def _mix(a,c,t):
    t=np.clip(t,0,1)[...,None]; return a*(1-t)+np.asarray(c,np.float32)[None,None,:]*t


def _apply(paint,mask,col):
    if mask is None:return col.astype(np.float32)
    m=np.asarray(mask,np.float32)
    if m.ndim==3:m=m[...,0]
    if m.shape!=col.shape[:2]:m=cv2.resize(m,(col.shape[1],col.shape[0]),interpolation=cv2.INTER_LINEAR)
    src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    return (col*m[...,None]+src*(1-m[...,None])).astype(np.float32)


def paint_mushroom_fade(paint,shape,mask,seed,pm,bb):
    del pm,bb
    pools,gill,fine,seam,warm,cool=_fields(shape,seed); h,w=shape[:2]
    col=np.empty((h,w,3),np.float32); col[:]=(.045,.025,.055)
    col=_mix(col,(.14,.23,.12),pools*.66)       # moss under-resin
    col=_mix(col,(.52,.17,.09),warm*(.22+.48*pools)) # rust ink pools
    col=_mix(col,(.72,.38,.09),gill*(.22+.38*warm))
    col=_mix(col,(.86,.71,.42),fine*(.20+.48*cool))
    col=_mix(col,(.06,.025,.045),seam*.62)
    return _apply(paint,mask,np.clip(col,0,1))


def spec_mushroom_fade(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    pools,gill,fine,seam,warm,cool=_fields(shape,seed)
    M=22+192*np.clip(.42*pools+.33*fine+.26*warm+.16*seam,0,1)*sm
    R=238-184*np.clip(.46*gill+.31*seam+.21*(1-pools)+.17*cool,0,1)
    CC=18+218*np.clip(.39*pools+.32*seam+.25*fine+.20*cool,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))
