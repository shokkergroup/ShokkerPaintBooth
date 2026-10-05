"""ASTRA scalar utilities and material packing; no shared decorative fields.

SPB-105 / ASTRA A1, 2026-09-05. Owner: "the best bases/patterns and specs".
M7 movement: unscored -> measured in docs/ASTRA_2026-09-05.md. Blue is inverted:
16 is strongest active coat, 255 suppresses coat. Never call it emission.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

TAU = np.float32(2 * np.pi)
_CACHE = OrderedDict()
_LOCK = RLock()


def grid(shape,limit=2048):
    h, w = map(int, shape[:2])
    q = min(1., float(limit) / max(h, w))
    hh, ww = max(1, round(h*q)), max(1, round(w*q))
    y, x = np.mgrid[:hh, :ww].astype(np.float32)
    return (x+.5)*(2048./w/q), (y+.5)*(2048./h/q)


def hash01(x, y, seed):
    x, y = np.asarray(x, np.int64), np.asarray(y, np.int64)
    z = (x*374761393 + y*668265263 + int(seed)*982451653) & 0xffffffff
    z = ((z ^ (z >> 13))*1274126177) & 0xffffffff
    return ((z ^ (z >> 16)) & 0xffffff).astype(np.float32) / 16777216.


def cell(x, y, pitch, seed, stagger=0.):
    iy = np.floor(y/pitch).astype(np.int32)
    u = x + (iy % 2)*pitch*stagger
    ix = np.floor(u/pitch).astype(np.int32)
    # Keep geometry float32: subtracting int32 grids implicitly promoted every
    # downstream field to float64, doubling traffic on the 2048 hot path.
    return ix, iy, u/pitch-ix.astype(np.float32)-.5, y/pitch-iy.astype(np.float32)-.5, hash01(ix, iy, seed)


def palette(*hexes):
    return np.array([[int(c[i:i+2],16)/255. for i in (0,2,4)] for c in hexes],np.float32)


def shade(shape, labels, relief, grain, tint, colors, accents, states, salt,coat_spread=48):
    """Pack feature-bound materials. Grain/tint come from THIS carrier's objects.

    Eight tiers within every named family; independent channel variation never
    changes feature ownership. No global rainbow/noise field is superimposed.
    """
    tier = np.minimum((np.clip(grain,0,.9999)*8).astype(np.int32),7)
    t = np.array([.18,.28,.38,.48,.58,.68,.78,.92],np.float32)[tier]
    c = colors[labels]; a = accents[labels]
    relief = np.clip(relief,0,1)
    paint = c*(.47+.82*t[...,None]) + a*(.05+.19*tint[...,None])
    paint *= (.70+.39*relief[...,None])
    # A3: stronger pigment separation inside the 8-32px geometry. This preserves
    # local density while making the fine metallic facets survive car mip levels.
    paint=(paint-.15)*1.55+.15
    # Each role has an independent M/R/Cc centre; per-object tiers subdivide it.
    spec = np.array(states,np.float32)[labels].copy()
    spec[...,0] += (t-.5)*54 + (relief-.5)*22
    # A2: brighter tiers expose smoother material inside the same feature.
    # This removes unrelated roughness grain while retaining channel independence.
    spec[...,1] += (t-.5)*-52 + (tint-.5)*16 - (relief-.5)*30
    spec[...,2] += (((tier*3+salt)%8).astype(np.float32)/7.-.5)*coat_spread + (tint-.5)*24
    spec[...,0] = np.clip(spec[...,0],4,255)
    spec[...,1:] = np.clip(spec[...,1:],16,255)
    paint = np.clip(paint,0,1).astype(np.float32)
    spec = spec.astype(np.float32)
    h,w = map(int,shape[:2])
    if paint.shape[:2] != (h,w):
        paint = cv2.resize(paint,(w,h),interpolation=cv2.INTER_LINEAR)
        spec = cv2.resize(spec,(w,h),interpolation=cv2.INTER_LINEAR)
    return paint, spec


def pair(module, shape, seed):
    # A6 / live-export discovery: the engine requests the same base with job
    # seeds 6654 (material), 42 (source) and 4284 (colour source). Using those
    # as construction seeds splits paint from spec and builds three carriers.
    # ASTRA is an authored collection: seed 42 defines each finish everywhere.
    # module.build remains seedable for research; public adapters are stable.
    authored_seed=42
    key = (module.__name__,tuple(shape[:2]),authored_seed)
    with _LOCK:
        if key not in _CACHE:
            # A2: always integrate microfeatures before shrinking previews.
            # Sampling the 8-32px carrier directly at 128/256 made alias patterns.
            native=(max(2048,int(shape[0])),max(2048,int(shape[1])))
            p,s = module.build(native,authored_seed)
            if tuple(shape[:2]) != native:
                size=(int(shape[1]),int(shape[0]))
                p=cv2.resize(p,size,interpolation=cv2.INTER_AREA)
                s=cv2.resize(s,size,interpolation=cv2.INTER_AREA)
            p.setflags(write=False); s.setflags(write=False)
            _CACHE[key]=(p,s)
            while len(_CACHE)>2:
                _CACHE.popitem(last=False)
        _CACHE.move_to_end(key)
        return _CACHE[key]


def clear_cache():
    with _LOCK:
        _CACHE.clear()


def bind(module):
    def paint_fn(paint,shape,mask,seed,intensity=1.,color=None):
        target,_=pair(module,shape,seed)
        # Full-canvas export/picker fast path: preserve the immutable cached
        # texture while avoiding three 48MB arithmetic temporaries per call.
        if float(intensity)>=1. and np.all(np.asarray(mask)>=1.):
            return target.copy()
        if float(intensity)<=0.:
            return np.asarray(paint,np.float32).copy()
        alpha=np.clip(np.asarray(mask,np.float32)*float(intensity),0,1)[...,None]
        return np.asarray(paint,np.float32)*(1-alpha)+target*alpha
    def spec_fn(shape,seed,intensity=1.,M=128.,R=128.):
        _,s=pair(module,shape,seed)
        # Engine owns intensity/base blending; authored pair must remain aligned.
        return s[...,0].copy(),s[...,1].copy(),s[...,2].copy()
    paint_fn.__module__=module.__name__; spec_fn.__module__=module.__name__
    # The picker already supports explicit transitive factory dependencies.
    # Invalidate on either this utility or the finish's own construction edit.
    for fn in (paint_fn,spec_fn):
        fn._spb_picker_dependency_modules=(module.__name__,__name__)
    return paint_fn,spec_fn


def contract(fid,name,promise,grammar,marks,binding,neighbors,source):
    return dict(schema='spb-finish-identity/1',finish_id=fid,display_name=name,
        promise=promise,carrier_grammar=grammar,spec_grammar=binding,
        reference_physics=dict(mechanism=promise+' Artistic pigment/material analogue; no additional simulator shader.',sources=[source]),
        native_scale_px=[8,32],mark_types=[dict(name=m,role=r) for m,r in marks],
        material_binding={k:[m for m,r in marks] for k in ('M','R','Cc')},
        material_tiers=['per-feature '+str(v) for v in (.18,.28,.38,.48,.58,.68,.78,.92)],
        nearest_neighbors=[dict(finish_id=k,difference=v) for k,v in neighbors],
        name_truth=dict(hidden_title_verdict='pass',assessment='Pre-render intended name test; final rendered agent/owner review recorded separately.',visible_evidence=[r for m,r in marks[:3]]),
        construction_key=fid+':'+grammar,spec_key=fid+':'+binding)
