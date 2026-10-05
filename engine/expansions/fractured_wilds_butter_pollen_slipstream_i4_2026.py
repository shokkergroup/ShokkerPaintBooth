# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Butter Pollen I4, fractured butter-gold slipstream.

SPB-105 / owner Butter Pollen correction, 2026-08-26.  This replaces the
microscopic/botanical image language with a race-car livery: unequal torn
acceleration ribbons, abrupt black release cuts, small lacquer chips and thin
cyan/violet flip lips.  Geometry is periodic by replicated finite strokes;
individual vertices are never modulo-connected across a card edge.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fbl_butter_pollen';NATIVE=2048;WORK=1024
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _curve(p0,p1,p2,p3,n=40):
 t=np.linspace(0,1,n)[:,None];return (1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
def _ribbon(img,seed,xoff,yoff):
 rng=np.random.default_rng(seed);w=img.shape[1];h=img.shape[0]
 # Each panel is an irregular torn skin, assembled in a different oblique
 # direction.  There are deliberately no rounded caps, rails, flower hubs or
 # repeated stripes.
 y=rng.uniform(-120,WORK+120)+yoff;tilt=rng.uniform(-.78,.78)
 p0=np.array((-220+xoff,y));p1=np.array((WORK*.18+xoff,y+rng.uniform(-330,330)));p2=np.array((WORK*.69+xoff,y+rng.uniform(-330,330)));p3=np.array((WORK+220+xoff,y+tilt*WORK+rng.uniform(-300,300)))
 pts=_curve(p0,p1,p2,p3,34);d=np.gradient(pts,axis=0);n=np.stack((-d[:,1],d[:,0]),1);n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-8
 thickness=rng.uniform(18,62,len(pts))*(.78+.34*np.sin(np.linspace(0,np.pi*2,len(pts))+rng.uniform(0,6.28)))
 # Tear the body into unequal finite segments; cuts are topology, not texture.
 outer=((4,6,9),(7,8,11),(11,10,8))[seed%3];gold=((22,89,176),(31,126,224),(43,162,255),(78,199,255),(116,224,255));foil=((111,238,255),(169,207,255),(226,183,249),(246,245,255))
 i=0
 while i<len(pts)-4:
  run=int(rng.integers(4,10));j=min(len(pts)-1,i+run);a=pts[i:j+1];nn=n[i:j+1];tt=thickness[i:j+1,None]
  shell=np.vstack((a+nn*(tt+5), (a-nn*(tt+5))[::-1]));body=np.vstack((a+nn*(tt*.78), (a-nn*(tt*.78))[::-1]))
  cv2.fillPoly(img,[np.rint(shell).astype(np.int32)],outer,lineType=cv2.LINE_AA);cv2.fillPoly(img,[np.rint(body).astype(np.int32)],gold[int(rng.integers(len(gold)))],lineType=cv2.LINE_AA)
  # An exposed asymmetric foil lip and 2–4 fine cross tears give hierarchy.
  lip=a+nn*(tt*.43);cv2.polylines(img,[np.rint(lip).astype(np.int32)],False,foil[int(rng.integers(len(foil)))],int(rng.integers(1,3)),cv2.LINE_AA)
  for _ in range(int(rng.integers(2,5))):
   k=int(rng.integers(i,j+1));u=d[k]/(np.linalg.norm(d[k])+1e-8);v=n[k];c=pts[k];ln=rng.uniform(3,9);wd=thickness[k]*rng.uniform(.44,.78);cut=np.array((c-u*ln-v*wd,c+u*ln-v*wd*.72,c+u*ln+v*wd*.72,c-u*ln+v*wd))
   cv2.fillConvexPoly(img,np.rint(cut).astype(np.int32),(2,3,5),lineType=cv2.LINE_AA)
  i=j+int(rng.integers(2,5))
@lru_cache(maxsize=2)
def _f():
 rng=np.random.default_rng(2026082639);period=WORK;extent=period*3;yy,xx=np.mgrid[:extent,:extent].astype(np.float32);carrier=.5+.5*np.sin((xx*.004+yy*.006)+.48*np.sin(yy*.012))
 base=np.empty((extent,extent,3),np.uint8);base[:,:,0]=np.clip(8+carrier*6,0,255);base[:,:,1]=np.clip(8+carrier*5,0,255);base[:,:,2]=np.clip(10+carrier*7,0,255)
 for i in range(23):
  # Replicated full paths make all four tile joins continuous without a border.
  for ox in (-period,0,period):
   for oy in (-period,0,period):_ribbon(base,801+i,ox+period,oy+period)
 base=base[period:2*period,period:2*period]
 x=cv2.cvtColor(cv2.resize(base,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);lip=np.hypot(gx,gy);lip/=lip.max()+1e-8;flow=np.abs(.68*gx-.73*gy);flow/=flow.max()+1e-8;chip=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.12));chip/=chip.max()+1e-8;band=cv2.GaussianBlur(lum,(0,0),15);band=(band-band.min())/(band.max()-band.min()+1e-8);void=np.clip((.13-lum)/.13,0,1)
 butter=np.clip((1.12*x[:,:,0]+.82*x[:,:,1]-.42*x[:,:,2]-.45)/.40,0,1);amber=np.clip((1.15*x[:,:,0]+.48*x[:,:,1]-.63*x[:,:,2]-.36)/.43,0,1);cyan=np.clip((-.61*x[:,:,0]+1.11*x[:,:,1]+1.16*x[:,:,2]-.60)/.32,0,1);violet=np.clip((.68*x[:,:,0]-.55*x[:,:,1]+1.17*x[:,:,2]-.38)/.43,0,1)
 return dict(x=x,sat=sat,lip=lip,flow=flow,chip=chip,band=band,void=void,butter=butter,amber=amber,cyan=cyan,violet=violet)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.56+np.dstack((.31*f['butter']*f['lip']+.15*f['amber']*f['chip'],.23*f['butter']*f['flow']+.17*f['cyan']*f['lip'],.19*f['cyan']*f['flow']+.17*f['violet']*f['chip']))-.10*f['void'][:,:,None],0,1)
 if not b:return a,f
 p=.34+.66*np.clip(.34*f['band']+.28*f['sat']+.23*f['flow']+.15*f['chip'],0,1);b=.010*a+np.dstack((.48+.43*f['butter']+.23*f['amber'],.20+.49*f['cyan']+.29*f['butter'],.20+.52*f['violet']+.25*f['cyan']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['butter']+.23*f['amber']+.19*f['cyan']+.18*f['violet']+.09*f['chip'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.34*f['void']+.28*f['flow']+.22*f['lip']+.16*f['chip'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['band']+.25*f['sat']+.19*f['butter']+.14*f['amber']+.09*f['lip'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'butter_pollen_slipstream_i4'),indent=2))
