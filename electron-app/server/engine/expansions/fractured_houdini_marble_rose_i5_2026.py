"""H10-I5 Marble Rose P2: micro-enamel field; roses exist only in M/R/Cc.

SPB-HOUDINI / owner 2026-08-31: rejects I4's generic cloud and tiny symbol
sprites.  RGB is a complete subtle whole-car material; repeated rose anatomy
is encoded only through 8–24px petal components in the three spec channels.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()

def _field(shape, seed):
    key = (*map(int, shape), int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    h,w = map(int,shape); scale=min(1.,1024/max(h,w)); hh,ww=max(192,round(h*scale)),max(192,round(w*scale))
    rng=np.random.default_rng(seed ^ 0xA105); y,x=np.mgrid[:hh,:ww].astype(np.float32)
    def noise(cell):
        return cv2.resize(rng.random((max(4,hh//cell),max(4,ww//cell))).astype(np.float32),(ww,hh),interpolation=cv2.INTER_CUBIC)
    lo,mid,fine=noise(130),noise(38),noise(12)
    bed=.60*lo+.29*mid+.11*fine; bed=(bed-bed.min())/(np.ptp(bed)+1e-6)
    warp=cv2.GaussianBlur(mid,(0,0),3)*9
    # 10–14px enamel tesserae keep the carrier handsome at picker scale,
    # while soft field variation prevents literal wallpaper repetition.
    gx=np.minimum(np.mod(x+warp,13.0),13.0-np.mod(x+warp,13.0)); gy=np.minimum(np.mod(y-warp*.6,11.0),11.0-np.mod(y-warp*.6,11.0))
    grout=np.exp(-np.minimum(gx,gy)**2/1.15); micro=.5+.5*np.sin(x*.78+y*.43+fine*4.1)
    base=np.array((.070,.011,.027),np.float32); wine=np.array((.35,.030,.105),np.float32); blush=np.array((.56,.108,.175),np.float32)
    paint=base*(1-bed[...,None])+wine*bed[...,None]
    paint=paint*(1-(.10*micro)[...,None])+blush*(.10*micro)[...,None]
    paint=np.clip(paint*(1-(.18*grout)[...,None]),0,1)
    state=np.mod((np.floor((x+warp)/13)+np.floor((y-warp*.6)/11)*3+np.floor(bed*7)).astype(np.int32),8)
    m=np.take(np.array([62,80,96,112,72,128,91,104],np.float32),state)+bed*27+micro*12
    r=np.take(np.array([192,168,145,123,179,108,157,136],np.float32),state)-bed*28-micro*11
    c=np.take(np.array([54,76,101,128,67,151,89,113],np.float32),state)+bed*35+micro*13
    petal=np.zeros((hh,ww),np.uint8); tier=np.zeros_like(petal)
    # Full-canvas recurring anatomy: each rose is built from 8–24px petal
    # ellipses, nested crescent cores, and short sepals; never RGB paint art.
    spacing=116
    for row,cy in enumerate(range(35,hh+spacing,spacing)):
        for col,cx0 in enumerate(range(20,ww+spacing,spacing)):
            cx=cx0+(row%2)*spacing*.47+rng.uniform(-13,13); cy2=cy+rng.uniform(-12,12); rot=rng.uniform(-.28,.28)
            if not (-36<cx<ww+36 and -36<cy2<hh+36): continue
            for ring,(rad,ax,ay) in enumerate(((10,9,5),(20,11,6),(30,13,7))):
                for j in range(6):
                    a=rot+j*np.pi/3+ring*.18; px=int(cx+np.cos(a)*rad); py=int(cy2+np.sin(a)*rad)
                    tmp=np.zeros_like(petal); cv2.ellipse(tmp,(px,py),(ax,ay),a*57.2958,22,338,1,2,cv2.LINE_AA)
                    hit=tmp>0; petal[hit]=1; tier[hit]=((row*3+col*5+ring*2+j+seed)%8)+1
            for rad in (4,8,12):
                tmp=np.zeros_like(petal); cv2.ellipse(tmp,(int(cx),int(cy2)),(rad,rad),rot*57.3,35,305,1,2,cv2.LINE_AA)
                hit=tmp>0; petal[hit]=1; tier[hit]=((row*7+col+rad+seed)%8)+1
            for side in (-1,1):
                q=np.array([[cx+side*4,cy2+29],[cx+side*12,cy2+39],[cx+side*20,cy2+51]],np.int32)
                tmp=np.zeros_like(petal); cv2.polylines(tmp,[q],False,1,2,cv2.LINE_AA); hit=tmp>0; petal[hit]=1; tier[hit]=((row+col*3+side+seed)%8)+1
    halo=cv2.GaussianBlur(petal.astype(np.float32),(0,0),2.2)
    q=np.mod(np.maximum(tier,1)-1,8)
    sm=np.array([247,181,229,116,252,158,207,91]); sr=np.array([18,64,33,119,11,78,42,132]); sc=np.array([249,159,218,87,253,143,196,72])
    hit=petal>0; m=np.where(hit,sm[q],m+halo*8); r=np.where(hit,sr[q],r-halo*8); c=np.where(hit,sc[q],c+halo*12)
    if (hh,ww)!=(h,w):
        up=lambda v:cv2.resize(v.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);m,r,c=map(up,(m,r,c))
    result=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,12,255),np.clip(c,12,255))).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=result
        if len(_CACHE)>2: _CACHE.popitem(last=False)
    return result

def paint_marble_rose_i5(paint,shape,mask,seed,paint_mix,base_blend):
    del base_blend; art,_=_field(shape,seed); src=np.asarray(paint,np.float32)[...,:3]; src=src/255 if src.max(initial=0)>1.5 else src
    ma=np.asarray(mask,np.float32); ma=ma[...,0] if ma.ndim==3 else ma; ma=(np.clip(ma,0,1)*np.clip(float(paint_mix),0,1))[...,None]
    return np.clip(src*(1-ma)+art*ma,0,1).astype(np.float32)

def spec_marble_rose_i5(shape,seed,spec_mix,base_metallic,base_roughness):
    del spec_mix,base_metallic,base_roughness; return _field(shape,seed)[1]
