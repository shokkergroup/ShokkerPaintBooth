"""
SPB-67 Standalone Effects v2 - Source-owned atomic rebuilds.
Every finish has FULLY INDEPENDENT spatial generation, spec, and paint.
No shared DNA. No formulaic templates. Unique physics per finish.
"""

from __future__ import annotations
from functools import lru_cache
import cv2
import numpy as np

STANDALONE_V2_IDS = (
    "thermal_titanium","galaxy_nebula_base","dark_sigil","deep_space_void",
    "polished_obsidian_mono","patinated_bronze","reactive_plasma","molten_metal",
    "oil_slick_base","aurora_borealis_mono",
    "prismatic_fracture","void_mirror","bio_lume","heat_death","corona_arc",
    "liquid_mercury","diamond_carbon","event_horizon","geode_soul","static_storm",
)

def _hsv2rgb(h,s,v):
    h=np.asarray(h,dtype=np.float32)%1.0;s=np.clip(np.asarray(s,dtype=np.float32),0,1);v=np.clip(np.asarray(v,dtype=np.float32),0,1)
    i=np.floor(h*6.0).astype(np.int32);f=h*6.0-i;p=v*(1.0-s);q=v*(1.0-f*s);t=v*(1.0-(1.0-f)*s);im=i%6
    r=np.select([im==0,im==1,im==2,im==3,im==4],[v,q,p,p,t],default=v)
    g=np.select([im==0,im==1,im==2,im==3,im==4],[t,v,v,q,p],default=p)
    b=np.select([im==0,im==1,im==2,im==3,im==4],[p,p,t,v,v],default=q)
    return np.stack([r,g,b],axis=2).astype(np.float32)

def _xy(shape):
    h,w=shape;y=np.linspace(0.0,1.0,h,dtype=np.float32).reshape(h,1);x=np.linspace(0.0,1.0,w,dtype=np.float32).reshape(1,w);return x,y

def _pxy(shape):
    h,w=shape;x,y=_xy(shape);return x*float(w),y*float(h)

def _hash_field(shape,seed):
    x,y=_xy(shape);n=np.sin((x*127.1+y*311.7+float(seed)*0.0173)*43758.5453);return (n-np.floor(n)).astype(np.float32)

def _smooth(a,r=1):
    out=np.asarray(a,dtype=np.float32)
    for _ in range(r):out=(out+np.roll(out,1,0)+np.roll(out,-1,0)+np.roll(out,1,1)+np.roll(out,-1,1))*0.2
    return out

def _normalize(a):
    arr=np.asarray(a,dtype=np.float32);lo,hi=float(arr.min()),float(arr.max());span=hi-lo
    if span<1e-8:return np.zeros_like(arr,dtype=np.float32)
    return ((arr-lo)/span).astype(np.float32)

def _resize(a,shape):
    arr=np.asarray(a,dtype=np.float32)
    if arr.shape[:2]==tuple(shape):return arr
    return cv2.resize(arr,(shape[1],shape[0]),interpolation=cv2.INTER_LINEAR).astype(np.float32)

def _work_shape(shape,limit=1024):
    h,w=shape;scale=min(1.0,float(limit)/float(max(h,w)))
    if scale>=1.0:return shape
    return max(96,int(round(h*scale))),max(96,int(round(w*scale)))

def _pack_spec(shape,mask,seed,sm,m_map,r_map,cc_map,mo=8.0,ro=120.0,co=80.0):
    h,w=shape;msk=np.asarray(mask,dtype=np.float32) if mask is not None else np.ones((h,w),dtype=np.float32);sm_f=float(sm)
    spec=np.zeros((h,w,4),dtype=np.uint8)
    spec[:,:,0]=np.clip(m_map*msk*sm_f+mo*(1.0-msk),0,255).astype(np.uint8)
    spec[:,:,1]=np.clip(r_map*msk+ro*(1.0-msk),15,255).astype(np.uint8)
    spec[:,:,2]=np.clip(cc_map*msk*sm_f+co*(1.0-msk),16,255).astype(np.uint8)
    spec[:,:,3]=np.clip(msk*255.0,0,255).astype(np.uint8)
    return spec

def _pack_paint(paint,shape,mask,seed,pm,bb,rgb):
    if paint.ndim==3 and paint.shape[2]>3:paint=paint[:,:,:3].copy()
    h,w=shape[:2];msk=np.asarray(mask,dtype=np.float32) if mask is not None else np.ones((h,w),dtype=np.float32)
    blend=np.clip(float(pm)*0.90,0,1)*msk
    out=paint[:,:,:3]*(1.0-blend[:,:,None])+rgb*blend[:,:,None]
    return np.ascontiguousarray(np.clip(out,0,1).astype(np.float32))

