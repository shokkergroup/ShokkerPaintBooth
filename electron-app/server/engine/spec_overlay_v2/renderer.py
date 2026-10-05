"""Canonical sampling/cache for independently authored overlay constructions."""
from functools import lru_cache
from pathlib import Path
import hashlib
import cv2
import numpy as np
from .geometry import Surface

ROOT=Path(__file__).resolve().parent

@lru_cache(maxsize=6)
def _master(construction,names,seed):
    surface=Surface((1024,1024),seed);construction(surface)
    if tuple(surface.names)!=names:raise ValueError('Authored features differ from the identity contract')
    return surface.finish()

def build_renderer(construction,contract):
    files=[Path(construction.__code__.co_filename),ROOT/'geometry.py',ROOT/'renderer.py',ROOT/'contract.py',ROOT/'compose.py']
    h=hashlib.sha256()
    for path in files:h.update(path.read_bytes())
    names=tuple(mark['name'] for mark in contract['mark_types'])
    # Review prose/verdicts do not affect pixels and must not stale every bake.
    h.update(str((contract['finish_id'],names)).encode('utf-8'));fingerprint=h.hexdigest()
    def renderer(shape,seed,sm,**params):
        h,w=int(shape[0]),int(shape[1]);amount=float(np.clip(sm,0,1))
        if amount==0:return np.zeros((h,w,4),np.float32)
        fields=_master(construction,names,int(seed))
        interpolation=cv2.INTER_AREA if max(h,w)<1024 else cv2.INTER_LINEAR
        if (h,w)!=(1024,1024):
            packed=fields.copy();packed[:,:,:3]*=packed[:,:,3:4]
            out=cv2.resize(packed,(w,h),interpolation=interpolation)
            out[:,:,:3]/=np.maximum(out[:,:,3:4],1e-8)
        else:out=fields.copy()
        out[:,:,3]*=amount
        return out.astype(np.float32,copy=False)
    renderer.__name__=contract['finish_id'];renderer.__qualname__=contract['finish_id']
    renderer.__doc__='Spec-only v2 material targets plus coverage. Targets R=Metallic G=Roughness B=Clearcoat.'
    renderer._spb_overlay_version=2;renderer._spb_source_fingerprint=fingerprint
    renderer.IDENTITY_CONTRACT=contract;renderer.clear_cache=_master.cache_clear
    return renderer
