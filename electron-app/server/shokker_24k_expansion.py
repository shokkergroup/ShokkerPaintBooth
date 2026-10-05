# =============================================================================
# COMPATIBILITY SHIM - shokker_24k_expansion.py
# =============================================================================
# Canonical module: engine/expansions/arsenal_24k.py
# =============================================================================
"""Compatibility shim for the Arsenal 24K expansion pack.

This module re-exports the public API of :mod:`engine.expansions.arsenal_24k`
so that legacy code paths -- in particular :mod:`shokker_engine_v2` -- can
continue to import ``shokker_24k_expansion`` without refactor.

The Arsenal 24K pack adds 24 premium automotive finishes targeting the
"Gold-to-Platinum" tier: tungsten-heavy metallics, OEM automotive, MIL-spec
OD greens, matte wraps, sun-fade weathering, race-day gloss, quantum black,
and Bentley-silver luxury variants.

Spec channel targets (R=metallic, G=roughness, B=clearcoat - 16 = max gloss):
    - ``spec_exotic_metal``           R=255, G<=40,  CC=16 (mirror-bright)
    - ``spec_oem_automotive_24k``     R=200, G~90,  CC=16 (factory showroom)
    - ``spec_industrial_tactical_24k``R<=60,  G~210, CC>=16 (matte-tough)
    - ``spec_satin_wrap``             R<=40,  G~180, CC~18 (satin sheen)
    - ``spec_weathered_aged_24k``     R<=120, G~180, CC~30 (dull patina)
    - ``spec_racing_heritage_24k``    R<=80,  G~55,  CC=16 (show gloss)
    - ``spec_premium_luxury_24k``     R=220, G<=70, CC=16 (deep luxury)

Iron-rule reminder:
    For every non-chrome finish, clearcoat (B) must be >= 16 and metallic (R)
    must be >= 15 to pass the registry lint in ``base_registry_data.py``.
    Use :func:`_enforce_iron_rule` locally if you post-process a spec array.

Dependencies:
    - :mod:`engine.expansions.arsenal_24k` (canonical, must import cleanly)
    - :mod:`shokker_engine_v2`             (invokes ``integrate_expansion``)

See also:
    - :mod:`shokker_paradigm_expansion`    -- sibling expansion shim
    - :mod:`shokker_fusions_expansion`     -- sibling expansion shim
    - :mod:`shokker_specials_overhaul`     -- sibling expansion shim
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

import numpy as np

__version__ = "6.1.1"
_EXPANSION_NAME = "arsenal_24k"
_CANONICAL_MODULE = "engine.expansions.arsenal_24k"

# Clearcoat/metallic iron-rule constants (see base_registry_data.py lint).
IRON_CC_MIN: int = 16       # B-channel minimum for non-chrome finishes
IRON_R_MIN: int = 15        # R-channel minimum for non-chrome finishes
SPEC_NEUTRAL_M: int = 180   # safe metallic fallback
SPEC_NEUTRAL_G: int = 60    # safe roughness fallback
SPEC_NEUTRAL_CC: int = 16   # safe (inverted) clearcoat fallback -- max gloss

logger = logging.getLogger(f"spb.expansion.{_EXPANSION_NAME}")


def _enforce_iron_rule(
    spec: np.ndarray,
    *,
    allow_chrome: bool = False,
) -> np.ndarray:
    """Clamp a uint8 spec array so it satisfies the Platinum iron rule.

    The renderer requires ``B >= IRON_CC_MIN`` and (unless the finish is
    explicitly chrome) ``R >= IRON_R_MIN``. This helper is idempotent and
    safe to call on already-compliant arrays.

    Args:
        spec: uint8 RGBA spec map of shape ``(H, W, 4)`` or ``(H, W, 3)``.
        allow_chrome: If True, do not touch the R channel (chrome finishes
            legitimately use R=255 with G=0).

    Returns:
        The same array, clamped in-place, for call-chaining convenience.

    Raises:
        ValueError: If ``spec`` is not a 3- or 4-channel array.
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
    """Validate a ``(H, W)`` shape tuple used by paint/spec callbacks."""
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
    """Clip ``arr`` to ``[lo, hi]`` after scrubbing NaN/Inf (NaN->lo, Inf->hi)."""
    out = np.nan_to_num(arr, nan=lo, posinf=hi, neginf=lo)
    return np.clip(out, lo, hi)


def _neutral_spec(shape: Tuple[int, int]) -> np.ndarray:
    """Return a safe neutral spec map to use as a fallback on error."""
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
    from engine.expansions.arsenal_24k import *  # noqa: F401,F403
    from engine.expansions.arsenal_24k import integrate_expansion  # noqa: F401
except ImportError as exc:
    logger.exception(
        "[%s] failed to import canonical module %s", _EXPANSION_NAME, _CANONICAL_MODULE
    )
    raise ImportError(
        f"[{_EXPANSION_NAME}] canonical module "
        f"'{_CANONICAL_MODULE}' could not be loaded: {exc}"
    ) from exc

# Optional group/count accessors -- present on newer builds only.
try:
    from engine.expansions.arsenal_24k import (  # noqa: F401
        get_expansion_group_map,
        get_expansion_counts,
    )
    _HAS_GROUP_MAP = True
except ImportError:
    _HAS_GROUP_MAP = False
    logger.debug(
        "[%s] group/count accessors not available in %s (older build?)",
        _EXPANSION_NAME,
        _CANONICAL_MODULE,
    )


def _validate_registry_on_import() -> None:
    """Smoke-check that the canonical module really exposed ``integrate_expansion``."""
    if "integrate_expansion" not in globals():
        raise ImportError(
            f"[{_EXPANSION_NAME}] canonical module did not export "
            f"'integrate_expansion' -- registry is broken."
        )


_validate_registry_on_import()


__all__ = [
    "integrate_expansion",
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
    __all__ += ["get_expansion_group_map", "get_expansion_counts"]
