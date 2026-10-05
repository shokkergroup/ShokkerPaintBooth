"""
engine.paint_v2 — Permanent v2 base paint/spec implementations.
Copied from _staging/paint_functions and wired via engine.registry_patches.
Do not depend on _staging at runtime.
"""
from collections import OrderedDict

import numpy as np


_BB_SCALAR_CACHE = OrderedDict()
_BB_SCALAR_CACHE_MAX = 8


def ensure_bb_2d(bb, shape):
    """Expand scalar or 0-d bb to (H, W) so paint_fns can use bb[:,:,np.newaxis].
    Returns CuPy array when GPU compute is active, numpy otherwise."""
    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
        h, w = shape[:2] if len(shape) > 2 else shape
        bb_value = float(bb)
        try:
            from engine.gpu import is_gpu, _cupy
            if is_gpu() and _cupy is not None:
                key = ("cupy", int(h), int(w), bb_value)
                cached = _BB_SCALAR_CACHE.get(key)
                if cached is not None:
                    _BB_SCALAR_CACHE.move_to_end(key)
                    return cached
                out = _cupy.full((int(h), int(w)), bb_value, dtype=_cupy.float32)
                _BB_SCALAR_CACHE[key] = out
                _BB_SCALAR_CACHE.move_to_end(key)
                while len(_BB_SCALAR_CACHE) > _BB_SCALAR_CACHE_MAX:
                    _BB_SCALAR_CACHE.popitem(last=False)
                return out
        except ImportError:
            pass
        # SPB paint-finish perf loop tick 2026-05-31 06:08; owner: "Speed is king in this app."
        # Exact scalar-BB reuse avoids repeated 2048² zero/constant array allocation; latest regular-base overlap
        # 20.356s -> 19.372s with paint/spec std drift 0 when paired with the base-registry adapter cache.
        key = ("numpy", int(h), int(w), bb_value)
        cached = _BB_SCALAR_CACHE.get(key)
        if cached is not None:
            _BB_SCALAR_CACHE.move_to_end(key)
            return cached
        out = np.full((int(h), int(w)), bb_value, dtype=np.float32)
        _BB_SCALAR_CACHE[key] = out
        _BB_SCALAR_CACHE.move_to_end(key)
        while len(_BB_SCALAR_CACHE) > _BB_SCALAR_CACHE_MAX:
            _BB_SCALAR_CACHE.popitem(last=False)
        return out
    return bb
