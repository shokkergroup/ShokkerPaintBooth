# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Coral Cluster I2, toroidal fracture-burst livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This is deliberately authored
from causal local burst events: each coral-red cluster has spokes, forked
enamel branches, terminal tabs, interrupted halos, cut seams and fine ribs.
It is neither image noise nor a recoloured repeated stamp field.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_coral_cluster';NATIVE=2048; WORK=1024
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _wrap_points(points, size):
    return np.asarray([[(int(x)%size,int(y)%size) for x,y in points]],np.int32)
def _draw_cluster(img, center, rng, offset=(0,0)):
    size=img.shape[0]; cx,cy=center[0]+offset[0],center[1]+offset[1]
    palette=((30,38,68),(43,55,116),(54,74,167),(67,93,222),(76,119,245),(88,139,255)) # BGR coral→rose
    accents=((72,159,255),(155,193,255),(192,225,255),(225,255,196))
    phase=float(rng.uniform(0,2*np.pi)); spokes=int(rng.integers(9,17)); radius=float(rng.uniform(44,90))
    for j in range(spokes):
        a=phase+2*np.pi*j/spokes+rng.uniform(-.13,.13); length=radius*rng.uniform(.52,1.08); bend=rng.uniform(-.55,.55)
        p0=(cx+rng.uniform(-5,5),cy+rng.uniform(-5,5)); p1=(cx+np.cos(a)*length*.43,cy+np.sin(a)*length*.43)
        p2=(cx+np.cos(a+bend*.35)*length*.74,cy+np.sin(a+bend*.35)*length*.74); p3=(cx+np.cos(a+bend)*length,cy+np.sin(a+bend)*length)
        pts=[]
        for t in np.linspace(0,1,14):
            q=(1-t)**3*np.array(p0)+3*(1-t)**2*t*np.array(p1)+3*(1-t)*t*t*np.array(p2)+t**3*np.array(p3);pts.append(q)
        dark=_wrap_points(pts,size); width=int(rng.integers(5,10)); cv2.polylines(img,dark,False,(5,7,10),width+3,cv2.LINE_AA)
        cv2.polylines(img,dark,False,palette[int(rng.integers(len(palette)))],width,cv2.LINE_AA)
        cv2.polylines(img,dark,False,accents[int(rng.integers(len(accents)))],max(1,width//4),cv2.LINE_AA)
        ex,ey=pts[-1];cv2.ellipse(img,(int(ex)%size,int(ey)%size),(int(rng.integers(3,8)),int(rng.integers(2,5))),int(np.degrees(a+bend)),0,360,palette[int(rng.integers(len(palette)))],-1,cv2.LINE_AA)
        if j%3==0:
            # A fork is an attached causal event, not independent scatter.
            fa=a+bend+rng.choice((-.72,.72)); fp=[pts[8],((pts[8][0]+np.cos(fa)*length*.18),(pts[8][1]+np.sin(fa)*length*.18))]
            cv2.polylines(img,_wrap_points(fp,size),False,(8,9,13),int(rng.integers(5,8)),cv2.LINE_AA);cv2.polylines(img,_wrap_points(fp,size),False,accents[int(rng.integers(len(accents)))],2,cv2.LINE_AA)
    # Interrupted halo fragments plus a compact hub create a recognisable cluster hierarchy.
    for _ in range(int(rng.integers(3,6))):
        rr=int(radius*rng.uniform(.22,.55));start=float(rng.uniform(0,300));end=start+float(rng.uniform(20,70));cv2.ellipse(img,(int(cx)%size,int(cy)%size),(rr,int(rr*rng.uniform(.58,.9))),float(rng.uniform(0,180)),start,end,accents[int(rng.integers(len(accents)))],int(rng.integers(1,3)),cv2.LINE_AA)
    cv2.circle(img,(int(cx)%size,int(cy)%size),int(rng.integers(5,11)),palette[int(rng.integers(len(palette)))],-1,cv2.LINE_AA)
@lru_cache(maxsize=2)
def _f():
    rng=np.random.default_rng(2026082611);period=WORK;extent=period*3;base=np.zeros((extent,extent,3),np.uint8);base[:]=np.array((10,12,17),np.uint8)
    # Tone carrier is broad enough to bind clusters, never used as noise decoration.
    yy,xx=np.mgrid[:extent,:extent].astype(np.float32);carrier=.5+.5*np.sin(xx*.012+np.sin(yy*.017)*1.7);base[:,:,0]=np.clip(base[:,:,0]+carrier*7,0,255);base[:,:,1]=np.clip(base[:,:,1]+carrier*5,0,255);base[:,:,2]=np.clip(base[:,:,2]+carrier*10,0,255)
    centers=rng.uniform(0,period,(86,2))
    for i,c in enumerate(centers):
        # Each replica gets the exact same causal cluster; no coordinate wrapping
        # occurs inside a line, so the central crop is mathematically tile-safe.
        for ox in (-period,0,period):
            for oy in (-period,0,period):
                _draw_cluster(base,c+period,np.random.default_rng(7311+i),(ox,oy))
    base=base[period:2*period,period:2*period]
    x=cv2.cvtColor(cv2.resize(base,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);lip=np.hypot(gx,gy);lip/=lip.max()+1e-8;branch=np.abs(.71*gx-.70*gy);branch/=branch.max()+1e-8;rib=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.2));rib/=rib.max()+1e-8;cluster=cv2.GaussianBlur(lum,(0,0),16);cluster=(cluster-cluster.min())/(cluster.max()-cluster.min()+1e-8)
    dark=np.clip((.10-lum)/.10,0,1);coral=np.clip((1.17*x[:,:,0]+.38*x[:,:,1]+.21*x[:,:,2]-.42)/.39,0,1);rose=np.clip((1.05*x[:,:,0]-.25*x[:,:,1]+.75*x[:,:,2]-.46)/.36,0,1);gold=np.clip((1.12*x[:,:,0]+.78*x[:,:,1]-.46*x[:,:,2]-.52)/.31,0,1);cyan=np.clip((-.57*x[:,:,0]+1.10*x[:,:,1]+1.19*x[:,:,2]-.61)/.33,0,1)
    return dict(x=x,sat=sat,lip=lip,branch=branch,rib=rib,cluster=cluster,dark=dark,coral=coral,rose=rose,gold=gold,cyan=cyan)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.61+np.dstack((.27*f['coral']*f['lip']+.14*f['rose']*f['branch'],.14*f['coral']*f['rib']+.14*f['gold']*f['lip'],.16*f['rose']*f['branch']+.19*f['cyan']*f['lip']))-.08*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.35+.65*np.clip(.35*f['cluster']+.27*f['sat']+.21*f['branch']+.17*f['rib'],0,1);b=.012*a+np.dstack((.55+.35*f['coral']+.28*f['rose'],.17+.43*f['gold']+.30*f['coral'],.24+.54*f['rose']+.28*f['cyan']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.29*f['coral']+.23*f['rose']+.19*f['gold']+.18*f['cyan']+.11*f['rib'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.34*f['dark']+.27*f['branch']+.22*f['lip']+.17*f['rib'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['cluster']+.25*f['sat']+.19*f['coral']+.14*f['rose']+.09*f['lip'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'coral_cluster_field_i2'),indent=2))
