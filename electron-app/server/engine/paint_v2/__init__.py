"""
engine.paint_v2 — Permanent v2 base paint/spec implementations.
Copied from _staging/paint_functions and wired via engine.registry_patches.
Do not depend on _staging at runtime.
"""
import numpy as np


def ensure_bb_2d(bb, shape):
    """Expand scalar or 0-d bb to (H, W) so paint_fns can use bb[:,:,np.newaxis]."""
    if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
        h, w = shape[:2] if len(shape) > 2 else shape
        return np.full((int(h), int(w)), float(bb), dtype=np.float32)
    return bb
