"""Harlequin Enamel I1 — candidate 1950s linoleum/inlay lacquer.

SPB-105 / owner doctrine / 2026-08-30.  Unlike rejected Argyle Bouclé, this is
not a dark textile lattice. Fine 10–30px irregular enamel diamonds carry a
bright 1950s linoleum palette in coherent colour territories. Each diamond
has a painted core, bevel rim, chrome seam, tiny pearl nick and dark inset;
M/R/Cc follows those exact physical features.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
_PAL=np.array(((.92,.10,.29),(.99,.52,.05),(.96,.76,.05),(.10,.66,.59),(.12,.30,.82),(.55,.12,.68),(.88,.15,.53)),np.float32)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&0xffff)*.00119
    u=(x+3.7*np.sin(y/101.+phase)+1.6*np.sin((x-y)/43.))* .70710678
    v=(y+3.3*np.sin(x/117.-phase*.7)+1.5*np.sin((x+y)/49.))* .70710678
    p=20.0;fx=np.mod(u,p)/p-.5;fy=np.mod(v,p)/p-.5
    diamond=np.clip(1.-(np.abs(fx)+np.abs(fy))*1.93,0,1)
    rim=np.exp(-np.square((np.abs(fx)+np.abs(fy)-.48)/.047))
    core=np.clip((diamond-.32)/.68,0,1)
    notch=np.exp(-np.square(np.sin((u-v)*.31+.41*np.sin((u+v)*.17))/.17))*core
    inset=np.clip((.20-diamond)/.20,0,1)
    region=(.48*np.sin(x/221.+.24*np.sin(y/83.)+phase)+.32*np.sin(y/179.-.20*np.sin(x/107.)-phase*.6)+.20*np.sin((x+y)/313.+phase*1.2))
    dye=np.mod(np.floor((region+1.15)*2.95).astype(np.int32)+np.floor(u/p).astype(np.int32)-2*np.floor(v/p).astype(np.int32),len(_PAL))
    # Adjacent diamonds differ within a coherent colour territory, but cannot
    # become a one-colour flat or a random independent fleck population.
    enamel=_PAL[dye]; companion=_PAL[np.mod(dye+1+(region>.15).astype(np.int32),len(_PAL))]
    paint=np.zeros((h,w,3),np.float32)+np.array((.025,.010,.041),np.float32)
    paint+=enamel*(.24+.46*core)[...,None]
    paint+=companion*(notch*(.13+.19*diamond))[...,None]
    paint+=np.array((.77,.74,.67),np.float32)*(rim*.17)[...,None]
    paint+=np.array((.94,.56,.70),np.float32)*(notch*.10)[...,None]
    paint+=np.array((.07,.02,.09),np.float32)*(inset*.32)[...,None]
    M=18+113*core+81*rim+53*notch+29*(dye==3)+22*(dye==5)-36*inset
    R=221-74*core-103*rim-69*notch+31*inset+19*(dye==2)
    C=18+96*core+113*rim+71*notch+25*(dye==4)+19*(dye==6)-24*inset
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_harlequin_enamel(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_harlequin_enamel(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
