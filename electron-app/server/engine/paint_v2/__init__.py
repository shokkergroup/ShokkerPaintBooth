"""Shared helpers for permanent v2 paint/spec implementations."""
from collections import OrderedDict

import numpy as np


_BB_SCALAR_CACHE = OrderedDict()
_BB_SCALAR_CACHE_MAX = 8


def ensure_bb_2d(bb, shape):
    """Expand scalar/0-d brightness bounds to the requested two-dimensional canvas."""
    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
        height, width = shape[:2] if len(shape) > 2 else shape
        value = float(bb)
        try:
            from engine.gpu import is_gpu, _cupy
            if is_gpu() and _cupy is not None:
                key = ("cupy", int(height), int(width), value)
                cached = _BB_SCALAR_CACHE.get(key)
                if cached is not None:
                    _BB_SCALAR_CACHE.move_to_end(key)
                    return cached
                out = _cupy.full((int(height), int(width)), value, dtype=_cupy.float32)
                _BB_SCALAR_CACHE[key] = out
                _BB_SCALAR_CACHE.move_to_end(key)
                while len(_BB_SCALAR_CACHE) > _BB_SCALAR_CACHE_MAX:
                    _BB_SCALAR_CACHE.popitem(last=False)
                return out
        except ImportError:
            pass
        key = ("numpy", int(height), int(width), value)
        cached = _BB_SCALAR_CACHE.get(key)
        if cached is not None:
            _BB_SCALAR_CACHE.move_to_end(key)
            return cached
        out = np.full((int(height), int(width)), value, dtype=np.float32)
        _BB_SCALAR_CACHE[key] = out
        _BB_SCALAR_CACHE.move_to_end(key)
        while len(_BB_SCALAR_CACHE) > _BB_SCALAR_CACHE_MAX:
            _BB_SCALAR_CACHE.popitem(last=False)
        return out
    return bb
