"""Shared paint recolor implementation for render endpoints."""

from __future__ import annotations

import colorsys
import os

import numpy as np
from PIL import Image as PILImage


def apply_paint_recolor_impl(
    paint_file,
    rules,
    job_dir,
    *,
    engine,
    logger,
    decode_spatial_mask_payload,
    mask_rle=None,
    mask_has_include=False,
):
    """Apply recolor rules to a paint file, saving a recolored copy."""
    img = PILImage.open(paint_file).convert("RGB")
    pixels = np.array(img, dtype=np.float32)
    original = pixels.copy()
    h, w = pixels.shape[:2]

    spatial_mask = None
    if mask_rle and isinstance(mask_rle, dict) and "runs" in mask_rle:
        spatial_mask = decode_spatial_mask_payload(
            mask_rle, "recolor spatial_mask", expected_shape=(h, w)
        )

    for rule in rules:
        src = np.array(rule["source_rgb"], dtype=np.float32)
        tgt = np.array(rule["target_rgb"], dtype=np.float32)
        tol = float(rule.get("tolerance", 40))
        use_hue_shift = rule.get("hue_shift", True)

        diff = original - src[np.newaxis, np.newaxis, :]
        dist_sq = np.sum(diff ** 2, axis=-1)
        mask = dist_sq <= (tol * tol * 3)

        if spatial_mask is not None:
            mask = mask & (spatial_mask != 2)
            if mask_has_include:
                mask = mask & (spatial_mask == 1)

        if not np.any(mask):
            continue

        if use_hue_shift:
            src_hsv = colorsys.rgb_to_hsv(src[0] / 255, src[1] / 255, src[2] / 255)
            tgt_hsv = colorsys.rgb_to_hsv(tgt[0] / 255, tgt[1] / 255, tgt[2] / 255)
            h_delta = tgt_hsv[0] - src_hsv[0]
            s_delta = tgt_hsv[1] - src_hsv[1]
            v_delta = tgt_hsv[2] - src_hsv[2]

            matched = original[mask] / 255.0
            r_ch, g_ch, b_ch = matched[:, 0], matched[:, 1], matched[:, 2]
            maxc = np.maximum(np.maximum(r_ch, g_ch), b_ch)
            minc = np.minimum(np.minimum(r_ch, g_ch), b_ch)
            delta_c = maxc - minc

            hue = np.zeros_like(r_ch)
            nonzero = delta_c > 1e-6
            m_r = (maxc == r_ch) & nonzero
            m_g = (maxc == g_ch) & nonzero & ~m_r
            m_b = nonzero & ~m_r & ~m_g
            hue[m_r] = (((g_ch[m_r] - b_ch[m_r]) / delta_c[m_r]) % 6) / 6.0
            hue[m_g] = (((b_ch[m_g] - r_ch[m_g]) / delta_c[m_g]) + 2) / 6.0
            hue[m_b] = (((r_ch[m_b] - g_ch[m_b]) / delta_c[m_b]) + 4) / 6.0

            sat = np.where(maxc > 0, delta_c / maxc, 0)
            val = maxc

            new_h = (hue + h_delta) % 1.0
            new_s = np.clip(sat + s_delta, 0, 1)
            new_v = np.clip(val + v_delta, 0, 1)

            new_r, new_g, new_b = engine.hsv_to_rgb_vec(new_h, new_s, new_v)
            pixels[mask, 0] = new_r * 255
            pixels[mask, 1] = new_g * 255
            pixels[mask, 2] = new_b * 255
        else:
            pixels[mask] = tgt

    recolored = np.clip(pixels, 0, 255).astype(np.uint8)
    recolored_path = os.path.join(job_dir, "recolored_paint.tga")
    engine.write_tga_24bit(recolored_path, recolored)
    return recolored_path
