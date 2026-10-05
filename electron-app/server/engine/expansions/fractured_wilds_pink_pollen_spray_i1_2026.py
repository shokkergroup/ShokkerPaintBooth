# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Pink Pollen I1, fractured acceleration-spray livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  “Pollen” here is a graphic paint
spray: linked anisotropic shard wakes leave directional pink, fuchsia, amber
and cyan split-flip marks.  It intentionally avoids literal biology, noise,
stamps, repeated grids, and border-spanning geometry.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fbl_pink_pollen';NATIVE=2048;WORK=1024
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _poly(img,p,color):cv2.fillConvexPoly(img,np.rint(p).astype(np.int32),color,lineType=cv2.LINE_AA)
def _spray(img,cx,cy,theta,rng):
    # Every flake belongs to this asymmetric acceleration wake, never scatter.
    palette=((37,17,92),(68,25,151),(117,39,213),(167,62,255),(205,119,255),(225,174,255)) # BGR
    edge=((19,13,39),(13,10,27),(47,21,74)); flip=((79,230,255),(85,184,255),(134,221,255),(148,255,229))
    direction=np.array((np.cos(theta),np.sin(theta)));normal=np.array((-direction[1],direction[0]))
    for k in range(int(rng.integers(18,31))):
        # forward, fan-shaped drift: useful as a livery flow at any scale.
        t=rng.uniform(-.18,1.12); lateral=rng.normal(0,.12+.30*t)
        p=np.array((cx,cy))+direction*(t*rng.uniform(68,154))+normal*(lateral*115)
        length=rng.uniform(7,26)*(1+.48*t);width=rng.uniform(2.3,8.5);a=theta+rng.normal(0,.16+.13*t)
        u=np.array((np.cos(a),np.sin(a)));v=np.array((-u[1],u[0]))
        # Unequal trapezoids give a genuine broken lacquer edge, not confetti.
        quad=np.array((p-u*length*.58-v*width,p+u*length*.56-v*width*rng.uniform(.28,.8),p+u*length*.74+v*width*rng.uniform(.20,.92),p-u*length*.42+v*width))
        _poly(img,quad,edge[int(rng.integers(len(edge)))])
        inner=quad*.82+p*.18;_poly(img,inner,palette[int(rng.integers(len(palette)))])
        if k%3==0:
            stripe=np.array((p-u*length*.18-v*width*.24,p+u*length*.57-v*width*.16,p+u*length*.61+v*width*.20,p-u*length*.14+v*width*.28))
            _poly(img,stripe,flip[int(rng.integers(len(flip)))])
    # A short, broken spine binds the wake while preventing a flower/star hub.
    for j in range(3):
        o=direction*(rng.uniform(14,45)+j*28)+normal*rng.uniform(-8,8);p0=(int(cx+o[0]),int(cy+o[1]));p1=(int(cx+o[0]+direction[0]*rng.uniform(18,51)),int(cy+o[1]+direction[1]*rng.uniform(18,51)))
        cv2.line(img,p0,p1,edge[j],int(rng.integers(2,5)),cv2.LINE_AA);cv2.line(img,p0,p1,flip[j],1,cv2.LINE_AA)
@lru_cache(maxsize=2)
def _f():
    rng=np.random.default_rng(2026082627);period=WORK;extent=period*3
    base=np.empty((extent,extent,3),np.uint8);yy,xx=np.mgrid[:extent,:extent].astype(np.float32)
    # A quiet carbon carrier supports the design; there is no granular noise field.
    carrier=.5+.5*np.sin((xx+yy*.43)*.006)+.18*np.sin((xx*.017-yy*.011))
    base[:,:,0]=np.clip(8+carrier*5,0,255);base[:,:,1]=np.clip(7+carrier*4,0,255);base[:,:,2]=np.clip(13+carrier*9,0,255)
    # 60 linked wakes retain dense 8–32px full-canvas shards while holding the
    # cold 2048 renderer inside the owner’s 2–3 second budget.
    anchors=rng.uniform(0,period,(60,2))
    for i,(x,y) in enumerate(anchors):
        # Same finite event is drawn around the central periodic cell; no modulo
        # is applied to individual vertices, eliminating long seam/card rails.
        theta=.16*np.sin(y*.010)+.42*np.sin(x*.007)+rng.normal(.10,.37)
        for ox in (-period,0,period):
            for oy in (-period,0,period):_spray(base,x+period+ox,y+period+oy,theta,np.random.default_rng(9131+i))
    base=base[period:2*period,period:2*period]
    x=cv2.cvtColor(cv2.resize(base,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);lip=np.hypot(gx,gy);lip/=lip.max()+1e-8;slant=np.abs(.84*gx+.54*gy);slant/=slant.max()+1e-8;chip=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.05));chip/=chip.max()+1e-8
    wake=cv2.GaussianBlur(lum,(0,0),18);wake=(wake-wake.min())/(wake.max()-wake.min()+1e-8);void=np.clip((.12-lum)/.12,0,1)
    pink=np.clip((1.12*x[:,:,0]-.26*x[:,:,1]+.69*x[:,:,2]-.35)/.45,0,1);fuchsia=np.clip((.95*x[:,:,0]-.48*x[:,:,1]+1.14*x[:,:,2]-.38)/.44,0,1);amber=np.clip((1.11*x[:,:,0]+.70*x[:,:,1]-.44*x[:,:,2]-.49)/.35,0,1);cyan=np.clip((-.62*x[:,:,0]+1.13*x[:,:,1]+1.18*x[:,:,2]-.61)/.31,0,1)
    return dict(x=x,sat=sat,lip=lip,slant=slant,chip=chip,wake=wake,void=void,pink=pink,fuchsia=fuchsia,amber=amber,cyan=cyan)
def _paint(b=False):
    f=_f();a=np.clip(f['x']*.58+np.dstack((.27*f['pink']*f['lip']+.12*f['amber']*f['chip'],.18*f['pink']*f['slant']+.15*f['cyan']*f['lip'],.30*f['fuchsia']*f['slant']+.15*f['cyan']*f['chip']))-.11*f['void'][:,:,None],0,1)
    if not b:return a,f
    p=.34+.66*np.clip(.35*f['wake']+.29*f['sat']+.21*f['slant']+.15*f['chip'],0,1);b=.009*a+np.dstack((.42+.47*f['pink']+.24*f['amber'],.18+.48*f['cyan']+.25*f['pink'],.30+.50*f['fuchsia']+.26*f['cyan']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
    m=_q(np.clip(.30*f['pink']+.24*f['fuchsia']+.20*f['amber']+.17*f['cyan']+.09*f['chip'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['void']+.27*f['slant']+.22*f['lip']+.16*f['chip'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['wake']+.25*f['sat']+.19*f['pink']+.14*f['fuchsia']+.09*f['lip'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
    d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
    for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
    a,b,s=last;delta=np.abs(a-b)
    for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
    o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'pink_pollen_spray_i1'),indent=2))
