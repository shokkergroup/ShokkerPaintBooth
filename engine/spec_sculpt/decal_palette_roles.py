"""Immutable intrinsic palette-role submasks for Smart TGA decal instances."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


@dataclass(frozen=True)
class PaletteRoleMask:
    role: str
    local_mask: np.ndarray = field(repr=False, compare=False)
    area: int
    parent_fraction: float

    def __post_init__(self) -> None:
        mask = np.ascontiguousarray(np.asarray(self.local_mask) > 0)
        if mask.ndim != 2 or int(np.count_nonzero(mask)) != int(self.area):
            raise ValueError("palette-role mask area mismatch")
        mask.setflags(write=False)
        object.__setattr__(self, "local_mask", mask)


def derive_palette_role_masks(
    rgb: np.ndarray,
    parent_mask: np.ndarray,
    *,
    min_pixels: int = 24,
    min_parent_fraction: float = 0.012,
) -> tuple[PaletteRoleMask, ...]:
    """Derive light, dark, chromatic, and minority ink hypotheses.

    These masks are intrinsic observations inside a preserved parent instance.
    They never replace the parent, assign an owner, or manufacture pixels.
    """
    image = np.asarray(rgb)
    parent = np.ascontiguousarray(np.asarray(parent_mask) > 0)
    if image.ndim != 3 or image.shape[:2] != parent.shape or image.shape[2] < 3:
        raise ValueError("palette roles require matching RGB and 2D parent mask")
    parent_area = int(np.count_nonzero(parent))
    if parent_area < max(1, int(min_pixels)):
        return ()
    pixels = image[:, :, :3].astype(np.uint8, copy=False)
    if cv2 is not None:
        lab = cv2.cvtColor(pixels, cv2.COLOR_RGB2LAB)
        hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
        lightness = lab[:, :, 0].astype(np.float32)
        saturation = hsv[:, :, 1].astype(np.float32)
    else:  # pragma: no cover
        lightness = np.mean(pixels, axis=2).astype(np.float32)
        saturation = np.ptp(pixels.astype(np.float32), axis=2)
    values_l = lightness[parent]
    values_s = saturation[parent]
    l_median = float(np.median(values_l))
    l_spread = float(np.percentile(values_l, 90) - np.percentile(values_l, 10))
    s_median = float(np.median(values_s))
    candidates: list[tuple[str, np.ndarray]] = []
    if l_median >= 178.0 and l_spread <= 55.0:
        candidates.append(("light_ink", parent.copy()))
    else:
        light_cut = max(178.0, float(np.percentile(values_l, 72)))
        candidates.append(("light_ink", parent & (lightness >= light_cut)))
    if l_median <= 78.0 and l_spread <= 55.0:
        candidates.append(("dark_ink", parent.copy()))
    else:
        dark_cut = min(78.0, float(np.percentile(values_l, 28)))
        candidates.append(("dark_ink", parent & (lightness <= dark_cut)))
    if s_median >= 105.0 and float(np.percentile(values_s, 25)) >= 75.0:
        candidates.append(("chromatic_ink", parent.copy()))
    else:
        sat_cut = max(105.0, float(np.percentile(values_s, 72)))
        candidates.append(("chromatic_ink", parent & (saturation >= sat_cut)))

    # A dominant flat badge color is often backing panel, while smaller color
    # clusters are the actual wordmark. Quantized RGB yields a deterministic
    # minority-contrast hypothesis without fitting or external training.
    quantized = (pixels // 32).astype(np.int16)
    packed = quantized[:, :, 0] * 64 + quantized[:, :, 1] * 8 + quantized[:, :, 2]
    ids, counts = np.unique(packed[parent], return_counts=True)
    if len(ids) >= 2:
        dominant = int(ids[int(np.argmax(counts))])
        candidates.append(("minority_contrast", parent & (packed != dominant)))

    roles = []
    seen = set()
    for role, mask in candidates:
        area = int(np.count_nonzero(mask))
        fraction = area / float(parent_area)
        if area < int(min_pixels) or fraction < float(min_parent_fraction):
            continue
        fingerprint = np.packbits(mask.reshape(-1)).tobytes()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        roles.append(PaletteRoleMask(
            role=role,
            local_mask=mask,
            area=area,
            parent_fraction=round(fraction, 6),
        ))
    return tuple(roles)


__all__ = ["PaletteRoleMask", "derive_palette_role_masks"]
