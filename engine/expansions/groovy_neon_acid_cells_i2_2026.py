"""Neon Acid I2 — dense 1960s chemical-dye celluloid bath.

SPB-105 / GV-NEON-ACID-I2 / 2026-08-30.  Not a macro blob wallpaper:
interlocking 5–28px dye cells, 1–3px caustic lips, gelatin cores and etched
troughs cover the whole carrier. The irregular cells are physical bath events;
neighbouring core/rim/void states get distinct M/R/Cc response.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
def _fract(a): return a-np.floor(a)

def _bath(x,y,pitch,salt):
    gx=np.floor(x/pitch);gy=np.floor(y/pitch);fx=_fract(x/pitch);fy=_fract(y/pitch)
    h1=_fract(np.sin(gx*127.1+gy*311.7+salt)*43758.5453)
    h2=_fract(np.sin(gx*269.5-gy*183.3+salt*1.7)*21347.2187)
    h3=_fract(np.sin(gx*91.7+gy*57.4+salt*2.3)*11371.1291)
    cx=.17+.66*h1;cy=.17+.66*h2;ang=(h3-.5)*2.7;ca=np.cos(ang);sa=np.sin(ang)
    dx=fx-cx;dy=fy-cy;u=dx*ca+dy*sa;v=-dx*sa+dy*ca
    a=.20+.22*h2;b=.17+.19*h1;d=np.sqrt((u/a)**2+(v/b)**2)
    body=np.clip((1-d)/.22,0,1)*(h3>.16)
    rim=np.clip((1.11-d)/.13,0,1)*np.clip((d-.61)/.24,0,1)*(h3>.16)
    core=np.clip((.52-d)/.25,0,1)*body
    return body.astype(np.float32),rim.astype(np.float32),core.astype(np.float32),h3.astype(np.float32)

def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&8191)*.0013
    u=x+3.1*np.sin(y/79.+phase)+1.9*np.cos((x+y)/47.);v=y+2.7*np.sin(x/91.-phase*.7)+1.4*np.cos((x-y)/53.)
    b1,r1,c1,h1=_bath(u,v,19.7,13.1+phase);b2,r2,c2,h2=_bath(u+8.2,v-5.7,28.9,39.7+phase);b3,r3,c3,h3=_bath(u-6.1,v+9.4,37.3,73.3+phase)
    body=np.clip(b1*.77+b2*.63+b3*.49,0,1);rim=np.clip(r1*.88+r2*.66+r3*.51,0,1);core=np.clip(c1*.74+c2*.61+c3*.47,0,1)
    ink=.5+.5*np.sin(x/181.+.31*np.sin(y/59.)+phase)*np.sin(y/211.-.27*np.sin(x/77.))
    lot=np.clip(h1*.48+h2*.33+h3*.19,0,1);void=np.clip(.61-body-rim*.22,0,1)
    deep=np.array((.005,.012,.045),np.float32);violet=np.array((.37,.025,.66),np.float32);cyan=np.array((.00,.68,.72),np.float32)
    magenta=np.array((.93,.02,.46),np.float32);lime=np.array((.33,.94,.09),np.float32);yellow=np.array((.98,.74,.06),np.float32)
    cell=violet*(1-lot[...,None])+cyan*(lot[...,None]);accent=magenta*(1-ink[...,None])+lime*(ink[...,None])
    paint=deep*(.87-.24*ink[...,None])+cell*(body[...,None]*.73)
    paint=paint*(1-core[...,None]*.46)+accent*(core[...,None]*.46)
    paint=paint*(1-rim[...,None]*.61)+yellow*(rim[...,None]*.61)
    paint*=.78+.22*(.30+.70*ink[...,None])
    M=18+29*ink+73*body+102*core+154*rim+34*lot-21*void
    R=231-28*ink-65*body-87*core-142*rim+19*(1-lot)+18*void
    C=20+36*ink+81*body+111*core+162*rim+41*lot-18*void
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value

def paint_neon_acid_cells(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)

def spec_neon_acid_cells(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
