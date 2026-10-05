# =============================================================================
# COMPATIBILITY SHIM - shokker_fusions_expansion.py
# =============================================================================
# Canonical module: engine/expansions/fusions.py
# =============================================================================
"""Compatibility shim for the Fusions expansion pack.

This module re-exports :mod:`engine.expansions.fusions` so legacy imports of
``shokker_fusions_expansion`` keep working.

Fusions blend two material profiles (gradient, ghost, anisotropic, reactive,
sparkle) into a single finish -- for example a candy-over-flake gradient or a
ghost-chrome grain fusion. Fusions are **color-override** finishes: they
synthesize the paint buffer directly based on the fusion recipe.

Spec channel targets (R=metallic, G=roughness, B=clearcoat - 16 = max gloss):
    - Gradient fusions   blend two spec profiles across a chosen axis
    - Ghost fusions      preserve base metallic, vary G and CC spatially
    - Anisotropic        stretch flake highlights along a grain direction
    - Reactive           temperature/light reactive, wide M range
    - Sparkle variants   diamond-dust, starfield, galaxy, firefly, snowfall,
                         champagne, meteor, constellation, confetti

All fusion specs honor CC >= 16 via :func:`_enforce_iron_rule` guards in the
canonical module; use the helper below if you post-process here.

Performance note:
    Fusion renders are the most expensive pipeline in SPB because each frame
    runs two material resolves plus a blend field. Avoid invoking these at
    full resolution during interactive preview -- ``renderZones()`` in
    ``paint-booth-2-state-zones.js`` already downsamples before preview.

Dependencies:
    - :mod:`engine.expansions.fusions` (canonical)
    - Invoked by :mod:`shokker_engine_v2` via ``integrate_fusions``.

See also:
    - :mod:`shokker_24k_expansion`         -- color-safe metallic base
    - :mod:`shokker_color_monolithics`     -- color-override solid/gradient
    - :mod:`shokker_paradigm_expansion`    -- procedural paradigm finishes
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

import numpy as np

__version__ = "6.1.1"
_EXPANSION_NAME = "fusions"
_CANONICAL_MODULE = "engine.expansions.fusions"

IRON_CC_MIN: int = 16
IRON_R_MIN: int = 15
SPEC_NEUTRAL_M: int = 160
SPEC_NEUTRAL_G: int = 50
SPEC_NEUTRAL_CC: int = 20

logger = logging.getLogger(f"spb.expansion.{_EXPANSION_NAME}")


def _enforce_iron_rule(
    spec: np.ndarray,
    *,
    allow_chrome: bool = False,
) -> np.ndarray:
    """Clamp a uint8 spec array to satisfy the Platinum iron rule.

    Args:
        spec: uint8 (H, W, 3|4) spec map.
        allow_chrome: If True, skip R-channel clamp.

    Returns:
        The clamped array (modified in-place).

    Raises:
        ValueError: On invalid shape.
    """
    if spec.ndim != 3 or spec.shape[-1] not in (3, 4):
        raise ValueError(
            f"[{_EXPANSION_NAME}] iron-rule expects (H,W,3|4) got {spec.shape}"
        )
    spec[..., 2] = np.maximum(spec[..., 2], IRON_CC_MIN)
    if not allow_chrome:
        spec[..., 0] = np.maximum(spec[..., 0], IRON_R_MIN)
    return spec


def _validate_shape(shape: Any) -> Tuple[int, int]:
    """Validate a ``(H, W)`` shape tuple."""
    if not isinstance(shape, tuple) or len(shape) < 2:
        raise ValueError(
            f"[{_EXPANSION_NAME}] shape must be (H,W[,C]) got {shape!r}"
        )
    h, w = int(shape[0]), int(shape[1])
    if h <= 0 or w <= 0:
        raise ValueError(
            f"[{_EXPANSION_NAME}] shape dims must be positive got {(h, w)}"
        )
    return h, w


def _validate_seed(seed: Any) -> int:
    """Coerce ``seed`` to a deterministic non-negative 32-bit int."""
    try:
        s = int(seed)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"[{_EXPANSION_NAME}] seed must be int-coercible got {seed!r}"
        ) from exc
    return s & 0x7FFFFFFF


def _safe_clip(arr: np.ndarray, lo: float = 0.0, hi: float = 255.0) -> np.ndarray:
    """Scrub NaN/Inf then clip to ``[lo, hi]``."""
    out = np.nan_to_num(arr, nan=lo, posinf=hi, neginf=lo)
    return np.clip(out, lo, hi)


def _neutral_spec(shape: Tuple[int, int]) -> np.ndarray:
    """Safe metallic-leaning fallback spec for fusion renders."""
    h, w = _validate_shape(shape)
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 0] = SPEC_NEUTRAL_M
    out[..., 1] = SPEC_NEUTRAL_G
    out[..., 2] = SPEC_NEUTRAL_CC
    out[..., 3] = 255
    return out


# ---------------------------------------------------------------------------
# Re-export canonical API
# ---------------------------------------------------------------------------
try:
    from engine.expansions.fusions import *  # noqa: F401,F403
    from engine.expansions.fusions import integrate_fusions  # noqa: F401
except ImportError as exc:
    logger.exception(
        "[%s] failed to import canonical module %s", _EXPANSION_NAME, _CANONICAL_MODULE
    )
    raise ImportError(
        f"[{_EXPANSION_NAME}] canonical module "
        f"'{_CANONICAL_MODULE}' could not be loaded: {exc}"
    ) from exc

try:
    from engine.expansions.fusions import get_fusion_group_map  # noqa: F401
    _HAS_GROUP_MAP = True
except ImportError:
    _HAS_GROUP_MAP = False
    logger.debug(
        "[%s] group map accessor not available in %s (older build?)",
        _EXPANSION_NAME,
        _CANONICAL_MODULE,
    )


def _validate_registry_on_import() -> None:
    """Smoke-check that the canonical module exposed ``integrate_fusions``."""
    if "integrate_fusions" not in globals():
        raise ImportError(
            f"[{_EXPANSION_NAME}] canonical module did not export "
            f"'integrate_fusions' -- registry is broken."
        )


_validate_registry_on_import()


__all__ = [
    "integrate_fusions",
    "_enforce_iron_rule",
    "_neutral_spec",
    "_safe_clip",
    "_validate_shape",
    "_validate_seed",
    "IRON_CC_MIN",
    "IRON_R_MIN",
    "SPEC_NEUTRAL_M",
    "SPEC_NEUTRAL_G",
    "SPEC_NEUTRAL_CC",
    "__version__",
]
if _HAS_GROUP_MAP:
    __all__ += ["get_fusion_group_map"]
