"""Hippie Rainbow Regional Macramé I2 — picker-hierarchy correction.

I1's native cords were real macramé but its per-crossing rainbow assignment
collapsed into a dark mesh.  I2 keeps every cord, knot, twist and fray at
2–28px but assigns the yarn in slow hand-dyed regions, so the card retains
large, intentional psychedelic colour movement without using broad primitive
stripes or a generic grid.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np
from engine.expansions.groovy_hippie_rainbow_macrame_i1_2026 import _fields

_CACHE, _LOCK = OrderedDict(), RLock()
_DYES=np.array(((.95,.07,.28),(1.0,.33,.04),(.97,.73,.04),
                (.05,.65,.58),(.08,.23,.82),(.42,.08,.68),(.88,.08,.52)),np.float32)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    body,top,under,knot,seam,ridge,fray,_old_dye,region=_fields(shape,seed)
    # Each broad dye bath controls many adjacent 8–28px cord cells.  This is
    # the Hologram lesson applied to an actual textile: coherent regions above
    # fine materially different cells, never a one-colour yarn stripe.
    selector=np.clip(np.floor((region+1.15)*3.05).astype(np.int32),0,6)
    neighboring=np.mod(selector+1+(region>.17).astype(np.int32),7)
    top_rgb=_DYES[selector]; under_rgb=_DYES[neighboring]
    ground=np.array((.022,.011,.040),np.float32)
    paint=np.broadcast_to(ground,(h,w,3)).astype(np.float32).copy()
    paint+=top_rgb*(top*(.37+.54*ridge))[...,None]
    paint+=under_rgb*(under*(.17+.30*(1-ridge)))[...,None]
    paint+=np.array((.82,.54,.73),np.float32)*(knot*(.10+.18*ridge))[...,None]
    paint+=np.array((.11,.05,.16),np.float32)*(seam*.28)[...,None]
    paint+=np.array((.24,.16,.28),np.float32)*(fray*.12)[...,None]
    # The yarn's lightness and local textile construction drive M/R/Cc.
    dye_luma=(top_rgb[...,0]*.28+top_rgb[...,1]*.55+top_rgb[...,2]*.17)
    M=16+139*top+64*under+81*knot+39*ridge+31*dye_luma-35*seam
    R=225-99*top-51*under-101*knot-39*ridge+44*seam+21*fray
    C=18+138*top+72*under+106*knot+47*ridge+26*(selector==4)+18*(selector==6)-28*seam
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_hippie_rainbow_regional(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_hippie_rainbow_regional(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
