# =============================================================================
# COMPATIBILITY SHIM - shokker_specials_overhaul.py
# =============================================================================
# Canonical module: engine/expansions/specials_overhaul.py
# =============================================================================
"""Compatibility shim for the Specials Overhaul expansion.

This module re-exports :mod:`engine.expansions.specials_overhaul` so legacy
imports of ``shokker_specials_overhaul`` continue to work.

The Specials Overhaul expansion owns the horror/spectral/experimental corner
of the catalog: cursed, eclipse, nightmare, possessed, reaper, voodoo,
wraith, plus effect-driven variants (depth-map, double-exposure, infrared,
polarized, UV blacklight, X-ray, chromatic aberration v2, halftone v2,
negative v2, solarization v2, embossed v2, cyberpunk, firefly, laser-grid,
LED matrix).

Many specials are **color-override** -- the spectral/horror look drives the
final paint. Effect-driven specials (infrared/x-ray/halftone) are
**color-safe** tints that modulate the user's chosen base color.

Spec channel targets (R=metallic, G=roughness, B=clearcoat - 16 = max gloss):
    - Cursed / Reaper / Wraith      low-M, high-G, CC>=20 (matte spectral)
    - Eclipse / Nightmare           deep-black M=~220, G<=25, CC=16
    - Possessed / Voodoo            varied M, dramatic G noise, CC>=16
    - Infrared / UV / X-ray         effect-driven, tuned per finish
    - Cyberpunk / Laser / LED       high-M neon, CC=16 (mirror)

Iron-rule reminder:
    The canonical module already honors CC >= 16 / R >= 15 on every
    non-chrome spec; use :func:`_enforce_iron_rule` if you post-process.

Dependencies:
    - :mod:`engine.expansions.specials_overhaul` (canonical)
    - Invoked by :mod:`shokker_engine_v2`.

See also:
    - :mod:`shokker_paradigm_expansion`    -- procedural paradigms
    - :mod:`shokker_fusions_expansion`     -- material fusions
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

import numpy as np

__version__ = "6.1.1"
_EXPANSION_NAME = "specials_overhaul"
_CANONICAL_MODULE = "engine.expansions.specials_overhaul"

IRON_CC_MIN: int = 16
IRON_R_MIN: int = 15
SPEC_NEUTRAL_M: int = 140
SPEC_NEUTRAL_G: int = 90
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
    """Fallback spec tuned for matte-spectral specials."""
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
    from engine.expansions.specials_overhaul import *  # noqa: F401,F403
except ImportError as exc:
    logger.exception(
        "[%s] failed to import canonical module %s", _EXPANSION_NAME, _CANONICAL_MODULE
    )
    raise ImportError(
        f"[{_EXPANSION_NAME}] canonical module "
        f"'{_CANONICAL_MODULE}' could not be loaded: {exc}"
    ) from exc

try:
    from engine.expansions.specials_overhaul import integrate_specials_overhaul  # noqa: F401
    _HAS_INTEGRATE = True
except ImportError:
    _HAS_INTEGRATE = False
    logger.debug(
        "[%s] integrate_specials_overhaul not present in %s (older build?)",
        _EXPANSION_NAME,
        _CANONICAL_MODULE,
    )


def _validate_registry_on_import() -> None:
    """Smoke-check that the canonical module loaded at least one public symbol.

    Unlike the other shims, ``specials_overhaul`` historically registered its
    finishes via ``*``-import side-effects and did not always expose an
    ``integrate_X`` entry point -- so we only require *some* symbol to have
    made it through.
    """
    # The canonical module exposes dozens of ``spec_*`` and ``paint_*``
    # callables; if none made it through the star-import the module is
    # effectively empty and we should fail loudly.
    public = [k for k in globals() if k.startswith(("spec_", "paint_"))]
    if not public:
        raise ImportError(
            f"[{_EXPANSION_NAME}] canonical module exposed no spec_/paint_ "
            f"callables -- registry is broken."
        )


_validate_registry_on_import()


__all__ = [
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
if _HAS_INTEGRATE:
    __all__ += ["integrate_specials_overhaul"]
