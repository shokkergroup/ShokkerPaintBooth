# =============================================================================
# COMPATIBILITY SHIM - shokker_paradigm_expansion.py
# =============================================================================
# Canonical module: engine/expansions/paradigm.py
# =============================================================================
"""Compatibility shim for the Paradigm expansion pack.

This module re-exports :mod:`engine.expansions.paradigm` so legacy imports of
``shokker_paradigm_expansion`` continue to work.

Paradigm finishes are procedurally-driven, often dramatic materials built on
cached noise fields: singularity, bioluminescent, liquid obsidian, fresnel
ghost, caustics, dimensional warp, neural, plasma, holographic, circuit
board, soundwave, topographic, tessellation, void.

Most Paradigm finishes are **color-override** -- they compute RGB directly
from procedural fields rather than tinting the user's base color. Exceptions
(color-safe tints) are documented per-finish in the canonical module.

Spec channel targets (R=metallic, G=roughness, B=clearcoat - 16 = max gloss):
    - Singularity / Void     R>=200, G<=30, CC=16 (mirror-deep)
    - Bioluminescent         R<=60,  G~180, CC>=20 (glowing-matte)
    - Liquid Obsidian        R~200,  G<=25, CC=16 (wet-black)
    - Fresnel Ghost          R varies spatially, CC clamped to 16
    - Caustic / Plasma       high-contrast M field, CC>=16
    - Holographic            chromatic CC sweep (still >= 16 minimum)

Performance note:
    Paradigm finishes lean on a module-level field cache keyed by ``(name,
    seed, shape)`` -- call :func:`clear_paradigm_cache` (re-exported from the
    canonical module) between renders that change global noise parameters,
    otherwise stale fields will be reused.

Dependencies:
    - :mod:`engine.expansions.paradigm` (canonical)
    - Invoked by :mod:`shokker_engine_v2` via ``integrate_paradigm``.

See also:
    - :mod:`shokker_fusions_expansion`     -- material fusions
    - :mod:`shokker_specials_overhaul`     -- horror/spectral specials
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

import numpy as np

__version__ = "6.1.1"
_EXPANSION_NAME = "paradigm"
_CANONICAL_MODULE = "engine.expansions.paradigm"

IRON_CC_MIN: int = 16
IRON_R_MIN: int = 15
SPEC_NEUTRAL_M: int = 200
SPEC_NEUTRAL_G: int = 45
SPEC_NEUTRAL_CC: int = 16

logger = logging.getLogger(f"spb.expansion.{_EXPANSION_NAME}")


def _enforce_iron_rule(
    spec: np.ndarray,
    *,
    allow_chrome: bool = False,
) -> np.ndarray:
    """Clamp a uint8 spec array to satisfy the Platinum iron rule.

    Args:
        spec: uint8 (H, W, 3|4) spec map.
        allow_chrome: Skip R clamp for chrome-class finishes.

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
    """Fallback spec favoring a dark-glossy paradigm look."""
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
    from engine.expansions.paradigm import *  # noqa: F401,F403
    from engine.expansions.paradigm import integrate_paradigm  # noqa: F401
except ImportError as exc:
    logger.exception(
        "[%s] failed to import canonical module %s", _EXPANSION_NAME, _CANONICAL_MODULE
    )
    raise ImportError(
        f"[{_EXPANSION_NAME}] canonical module "
        f"'{_CANONICAL_MODULE}' could not be loaded: {exc}"
    ) from exc

try:
    from engine.expansions.paradigm import get_paradigm_group_map  # noqa: F401
    _HAS_GROUP_MAP = True
except ImportError:
    _HAS_GROUP_MAP = False
    logger.debug(
        "[%s] group map accessor not available in %s (older build?)",
        _EXPANSION_NAME,
        _CANONICAL_MODULE,
    )

try:
    from engine.expansions.paradigm import clear_paradigm_cache  # noqa: F401
    _HAS_CACHE_CLEAR = True
except ImportError:
    _HAS_CACHE_CLEAR = False
    logger.debug(
        "[%s] clear_paradigm_cache not available in %s (older build?)",
        _EXPANSION_NAME,
        _CANONICAL_MODULE,
    )


def _validate_registry_on_import() -> None:
    """Smoke-check that the canonical module exposed ``integrate_paradigm``."""
    if "integrate_paradigm" not in globals():
        raise ImportError(
            f"[{_EXPANSION_NAME}] canonical module did not export "
            f"'integrate_paradigm' -- registry is broken."
        )


_validate_registry_on_import()


__all__ = [
    "integrate_paradigm",
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
    __all__ += ["get_paradigm_group_map"]
if _HAS_CACHE_CLEAR:
    __all__ += ["clear_paradigm_cache"]
