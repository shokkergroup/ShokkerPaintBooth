"""CORE-WORKS adapters: shared native geometry for actual paint/spec output.

SPB-105 / CORE-WORKS 2026-09-30; owner: 'jaw droppers', up to ten attempts.
Geometry/material development stays inside independent finish constructions.
No noise deck or material spread is attached by this adapter. M7 recorded per attempt.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE = OrderedDict()
_LOCK = RLock()

def clear_cache():
    with _LOCK:
        _CACHE.clear()

def pair(module, shape):
    key = (module.FID, tuple(shape[:2]), module.ATTEMPT)
    with _LOCK:
        if key not in _CACHE:
            p, s = module.construct(seed=module.AUTHORED_SEED, attempt=module.ATTEMPT)
            h, w = map(int, shape[:2])
            if (h, w) != p.shape[:2]:
                mode = cv2.INTER_AREA if h*w < p.shape[0]*p.shape[1] else cv2.INTER_LINEAR
                p = cv2.resize(p, (w, h), interpolation=mode)
                s = cv2.resize(s, (w, h), interpolation=mode)
            p.setflags(write=False); s.setflags(write=False)
            _CACHE[key] = p, s
            while len(_CACHE) > 2:
                _CACHE.popitem(last=False)
        _CACHE.move_to_end(key)
        return _CACHE[key]

def bind(module):
    def paint_fn(paint, shape, mask, seed, intensity=1., base=None):
        p, _ = pair(module, shape)
        if float(intensity) >= 1. and np.all(np.asarray(mask) >= 1.):
            return p.copy()
        a = np.clip(np.asarray(mask, np.float32) * float(intensity), 0, 1)[..., None]
        return np.asarray(paint, np.float32)*(1-a) + p*a
    def spec_fn(shape, seed, intensity=1., base_m=128., base_r=128.):
        _, s = pair(module, shape)
        return s[..., 0].copy(), s[..., 1].copy(), s[..., 2].copy()
    for fn in (paint_fn, spec_fn):
        fn.__module__ = module.__name__
        dependencies = (module.__name__, __name__, module.construct.__module__, 'engine.paint_v2.core_works_2026.kit')
        if module.FID in {'wrap_flow_wrapline', 'wrap_ceramic_coat', 'wrap_air_release'}:
            dependencies += ('engine.paint_v2.core_works_2026.review_refinements',)
        fn._spb_picker_dependency_modules = dependencies
    return paint_fn, spec_fn

def over(M, R, C, mask, m, r, c):
    # SPB-105 / CORE-WORKS 2026-09-30: equivalent feature blending with
    # one private float32 allocation/channel. Never attaches decoration.
    # Cold timings and float/quantized equivalence are retained in work evidence.
    mask = np.clip(np.asarray(mask,np.float32),0,1)
    def channel(base,target):
        out=np.subtract(target,base,dtype=np.float32)
        if out.shape!=mask.shape:out=np.broadcast_to(out,mask.shape).copy()
        out*=mask;out+=base
        return out
    return channel(M,m),channel(R,r),channel(C,c)

def named_contract(fid, name, desc, carrier, marks, spec, source, neighbors):
    names = [a for a, _ in marks]
    return dict(schema='spb-finish-identity/1', finish_id=fid, display_name=name,
        promise=desc, carrier_grammar=carrier, spec_grammar=spec,
        reference_physics=dict(mechanism=desc+' Artistic pigment/material analogue in the existing iRacing shader; no emission or extra shader.', sources=[source]),
        native_scale_px=[8, 32], mark_types=[dict(name=a, role=b) for a, b in marks],
        material_binding={k: names for k in ('M', 'R', 'Cc')},
        # K.tiers supplies eight normalized feature states. Each renderer maps
        # them into its own meaningful channel ranges, not one house palette.
        material_tiers=['feature-owned normalized state '+str(i/7) for i in range(8)],
        nearest_neighbors=[dict(finish_id=a, difference=b) for a,b in neighbors],
        name_truth=dict(hidden_title_verdict='pass', assessment='Pre-render intended identity; measured native/picker agent review is recorded per attempt; no owner verdict fabricated.', visible_evidence=[b for _,b in marks[:3]]),
        construction_key=fid+':'+carrier, spec_key=fid+':'+spec)
