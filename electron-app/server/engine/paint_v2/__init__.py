"""
engine.paint_v2 — Permanent v2 base paint/spec implementations.
Copied from _staging/paint_functions and wired via engine.registry_patches.
Do not depend on _staging at runtime.
"""
import numpy as np


def ensure_bb_2d(bb, shape):
    """Expand scalar or 0-d bb to (H, W) so paint_fns can use bb[:,:,np.newaxis].
    Returns CuPy array when GPU compute is active, numpy otherwise."""
    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
        h, w = shape[:2] if len(shape) > 2 else shape
        try:
            from engine.gpu import is_gpu, _cupy
            if is_gpu() and _cupy is not None:
                return _cupy.full((int(h), int(w)), float(bb), dtype=_cupy.float32)
        except ImportError:
            pass
        return np.full((int(h), int(w)), float(bb), dtype=np.float32)
    return bb
