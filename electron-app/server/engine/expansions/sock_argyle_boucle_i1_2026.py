"""Argyle Bouclé I1 — candidate fine 1950s sweater/intarsia lacquer.

SPB-105 / owner doctrine / 2026-08-30.  This is an authentic small-scale
argyle material, not a flat checker: 8–30px diagonally knitted diamonds use
different yarn bodies, 2–5px intarsia seams, 3–9px bouclé loops and restrained
cross-stitch highlights.  Colour placement is regionally reordered so the
whole 2048² car never resolves as a single tiled wallpaper panel.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_YARN = np.array(((.78,.14,.39), (.12,.61,.63), (.88,.74,.34),
                  (.52,.24,.70), (.82,.54,.35), (.24,.35,.72)), np.float32)


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:
            _CACHE.move_to_end(key); return prior
    y,x=np.mgrid[:h,:w].astype(np.float32); phase=(int(seed)&0xffff)*.0017
    # Knit tension gives small, non-identical diamonds while retaining the
    # characteristic diagonal intarsia geometry.
    u=x+3.7*np.sin(y/97.+phase)+1.9*np.sin((x-y)/41.)
    v=y+3.1*np.sin(x/111.-phase*.6)+1.5*np.sin((x+y)/53.)
    p=25.0
    a=(u+v)*.70710678; b=(u-v)*.70710678
    ia=np.floor(a/p).astype(np.int32); ib=np.floor(b/p).astype(np.int32)
    fa=np.mod(a,p)/p-.5; fb=np.mod(b,p)/p-.5
    diamond=np.clip(1.-(np.abs(fa)+np.abs(fb))*1.96,0,1)
    # The seam is visibly knitted into the diamond boundary, never an overlay.
    edge=np.exp(-np.square((np.abs(fa)+np.abs(fb)-.49)/.050))
    yarn_phase=.5+.5*np.sin((u*.49+v*.22)+.63*np.sin((u-v)*.17))
    boucle=np.clip((np.sin(u*.36+.5*np.sin(v*.19))
                    *np.sin(v*.31-.4*np.sin(u*.23))-.38)/.62,0,1)
    cross=np.exp(-np.square(np.sin((u-v)*.171+phase)/.19))*edge
    region=(.46*np.sin(x/203.+.22*np.sin(y/79.))+ .34*np.sin(y/181.-.17*np.sin(x/101.))
            +.20*np.sin((x+y)/307.+phase))
    # Colour changes only from one whole knitted diamond population to another.
    color=np.mod(ia-2*ib+np.floor((region+1.2)*2.5).astype(np.int32),len(_YARN))
    body=_YARN[color]
    charcoal=np.array((.032,.022,.052),np.float32)
    seam=np.array((.78,.72,.61),np.float32)
    paint=charcoal[None,None,:]+body*(.25+.57*diamond[...,None])*(.76+.24*yarn_phase[...,None])
    paint+=seam[None,None,:]*(edge*(.09+.17*cross))[...,None]
    paint+=np.array((.17,.13,.20),np.float32)*(boucle*.16)[...,None]
    # The same yarn body and local construction creates all material response.
    M=18+109*diamond+57*edge+38*cross+31*boucle+20*(color==1)+18*(color==3)
    R=221-77*diamond-96*edge-48*cross+22*(1-yarn_phase)+19*(color==2)
    C=19+93*diamond+106*edge+58*cross+28*boucle+22*(color==0)+18*(color==5)
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_argyle_boucle(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed); source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_argyle_boucle(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed); return spec[...,0],spec[...,1],spec[...,2]
