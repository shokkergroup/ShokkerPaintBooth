# =============================================================================
# COMPATIBILITY SHIM - shokker_color_monolithics.py
# =============================================================================
# Canonical module: engine/expansions/color_monolithics.py
# =============================================================================
"""Compatibility shim for the Color Monolithics expansion.

This module re-exports :mod:`engine.expansions.color_monolithics` so callers
that still import ``shokker_color_monolithics`` keep working.

The Color Monolithics expansion owns the "color-override" base layer -- solid,
gradient, color-shift, and multi-color finishes. **These finishes are
color-overriding**, meaning they paint RGB directly rather than tinting the
user's chosen base color (contrast with color-safe finishes like those in the
:mod:`shokker_24k_expansion` pack, which preserve user hue).

Spec channel targets (R=metallic, G=roughness, B=clearcoat - 16 = max gloss):
    - Solid swatches     M<=80,  G~40,  CC=16 (showroom)
    - Gradients          M<=80,  G~40,  CC=30 (slight coat character)
    - Color-shift        tuned dynamically per finish -- see spec helpers
    - Multi-color        M~150,  G~45,  CC=35 (organic worn feel)

Iron-rule reminder:
    Every non-chrome spec must have CC (B) >= 16 and metallic (R) >= 15. The
    canonical module already complies; if you post-process a spec here use
    :func:`_enforce_iron_rule`.

Dependencies:
    - :mod:`engine.expansions.color_monolithics` (canonical)
    - Invoked by :mod:`shokker_engine_v2` via ``integrate_color_monolithics``.

See also:
    - :mod:`shokker_24k_expansion`         -- color-safe tint finishes
    - :mod:`shokker_fusions_expansion`     -- material fusion finishes
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

import numpy as np

__version__ = "6.1.1"
_EXPANSION_NAME = "color_monolithics"
_CANONICAL_MODULE = "engine.expansions.color_monolithics"

IRON_CC_MIN: int = 16
IRON_R_MIN: int = 15
SPEC_NEUTRAL_M: int = 80
SPEC_NEUTRAL_G: int = 40
SPEC_NEUTRAL_CC: int = 16

logger = logging.getLogger(f"spb.expansion.{_EXPANSION_NAME}")


def _enforce_iron_rule(
    spec: np.ndarray,
    *,
    allow_chrome: bool = False,
) -> np.ndarray:
    """Clamp a spec array to satisfy the Platinum iron rule.

    Args:
        spec: uint8 (H, W, 3|4) spec map.
        allow_chrome: Skip R-channel clamp for chrome finishes.

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
    """Validate paint/spec shape tuple."""
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
    """Return a safe neutral showroom spec for fallback use."""
    h, w = _validate_shape(shape)
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 0] = SPEC_NEUTRAL_M
    out[..., 1] = SPEC_NEUTRAL_G
    out[..., 2] = SPEC_NEUTRAL_CC
    out[..., 3] = 255
    return out


def _paint_noop(
    paint: np.ndarray,
    shape: Any,
    mask: Any,
    seed: Any,
    pm: Any,
    bb: Any,
) -> np.ndarray:
    """Identity paint callback used as a defensive fallback.

    Matches the engine's paint-fn signature
    ``(paint, shape, mask, seed, pm, bb) -> paint`` so it can be slotted into
    the registry without blowing up the pipeline when an override is missing.
    """
    return paint


# ---------------------------------------------------------------------------
# Re-export canonical API
# ---------------------------------------------------------------------------
try:
    from engine.expansions.color_monolithics import *  # noqa: F401,F403
    from engine.expansions.color_monolithics import (  # noqa: F401
        integrate_color_monolithics,
    )
except ImportError as exc:
    logger.exception(
        "[%s] failed to import canonical module %s", _EXPANSION_NAME, _CANONICAL_MODULE
    )
    raise ImportError(
        f"[{_EXPANSION_NAME}] canonical module "
        f"'{_CANONICAL_MODULE}' could not be loaded: {exc}"
    ) from exc

try:
    from engine.expansions.color_monolithics import get_color_monolithic_metadata  # noqa: F401
    _HAS_METADATA = True
except ImportError:
    _HAS_METADATA = False
    logger.debug(
        "[%s] metadata accessor not available in %s (older build?)",
        _EXPANSION_NAME,
        _CANONICAL_MODULE,
    )


def _validate_registry_on_import() -> None:
    """Smoke-check that the canonical module exported ``integrate_color_monolithics``."""
    if "integrate_color_monolithics" not in globals():
        raise ImportError(
            f"[{_EXPANSION_NAME}] canonical module did not export "
            f"'integrate_color_monolithics' -- registry is broken."
        )


_validate_registry_on_import()


__all__ = [
    "integrate_color_monolithics",
    "_enforce_iron_rule",
    "_neutral_spec",
    "_paint_noop",
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
if _HAS_METADATA:
    __all__ += ["get_color_monolithic_metadata"]
