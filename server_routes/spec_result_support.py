"""Spec result normalization shared by render and Finish Viewer routes."""

import numpy as np


def normalize_spec_result_to_rgba(
    spec_result,
    shape,
    default_m=5,
    default_r=100,
    default_cc=16,
    *,
    strict_shapes=False,
):
    """Normalize spec outputs from all engine contracts to HxWx4 float32."""
    h, w = shape[:2]

    def _plane(value, fallback, channel="spec"):
        if value is None:
            return np.full((h, w), float(fallback), dtype=np.float32)
        arr = np.asarray(value, dtype=np.float32)
        if arr.ndim == 0:
            return np.full((h, w), float(arr), dtype=np.float32)
        if arr.shape != (h, w):
            if strict_shapes:
                raise ValueError(
                    f"Invalid {channel} channel shape {arr.shape}; expected {(h, w)}"
                )
            try:
                arr = np.resize(arr, (h, w)).astype(np.float32)
            except Exception:
                if strict_shapes:
                    raise
                return np.full((h, w), float(fallback), dtype=np.float32)
        return arr

    if isinstance(spec_result, dict):
        for key in ("spec", "rgba", "result"):
            if key in spec_result:
                return normalize_spec_result_to_rgba(
                    spec_result[key],
                    shape,
                    default_m,
                    default_r,
                    default_cc,
                    strict_shapes=strict_shapes,
                )
        if any(k in spec_result for k in ("M", "R", "CC")):
            if strict_shapes:
                missing = [k for k in ("M", "R", "CC") if k not in spec_result]
                if missing:
                    raise ValueError(
                        f"Missing strict spec channel(s): {', '.join(missing)}; expected M, R, CC"
                    )
            m = _plane(spec_result.get("M"), default_m, "M")
            r = _plane(spec_result.get("R"), default_r, "R")
            cc = _plane(spec_result.get("CC"), default_cc, "CC")
            out = np.empty((h, w, 4), dtype=np.float32)
            out[:, :, 0] = np.clip(m, 0, 255)
            out[:, :, 1] = np.clip(r, 0, 255)
            out[:, :, 2] = np.clip(cc, 0, 255)
            out[:, :, 3] = 255
            return out
        return None

    if isinstance(spec_result, (tuple, list)) and len(spec_result) >= 2:
        if strict_shapes and len(spec_result) < 3:
            raise ValueError("Missing strict spec channel(s): CC; expected M, R, CC")
        m = _plane(spec_result[0], default_m, "M")
        r = _plane(spec_result[1], default_r, "R")
        cc = _plane(spec_result[2] if len(spec_result) >= 3 else None, default_cc, "CC")
        out = np.empty((h, w, 4), dtype=np.float32)
        out[:, :, 0] = np.clip(m, 0, 255)
        out[:, :, 1] = np.clip(r, 0, 255)
        out[:, :, 2] = np.clip(cc, 0, 255)
        out[:, :, 3] = 255
        return out

    if spec_result is None:
        return None

    arr = np.asarray(spec_result, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[0] in (3, 4) and arr.shape[1:3] == (h, w):
        arr = np.moveaxis(arr, 0, -1)
    if arr.ndim == 2:
        if strict_shapes:
            raise ValueError("Missing strict spec channel(s): R, CC; expected M, R, CC")
        out = np.empty((h, w, 4), dtype=np.float32)
        out[:, :, 0] = np.clip(_plane(arr, default_m, "M"), 0, 255)
        out[:, :, 1] = default_r
        out[:, :, 2] = default_cc
        out[:, :, 3] = 255
        return out
    if arr.ndim == 3 and arr.shape[:2] == (h, w):
        out = np.empty((h, w, 4), dtype=np.float32)
        chans = arr.shape[2]
        if strict_shapes and chans < 3:
            raise ValueError(
                f"Invalid strict spec channel count {chans}; expected at least 3 channels"
            )
        out[:, :, 0] = np.clip(arr[:, :, 0], 0, 255)
        out[:, :, 1] = np.clip(arr[:, :, 1] if chans > 1 else default_r, 0, 255)
        out[:, :, 2] = np.clip(arr[:, :, 2] if chans > 2 else default_cc, 0, 255)
        out[:, :, 3] = np.clip(arr[:, :, 3] if chans > 3 else 255, 0, 255)
        return out
    return None
