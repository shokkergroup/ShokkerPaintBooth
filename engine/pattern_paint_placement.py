"""Place authored direct-pattern paint without moving the customer's pixels.

SPB-105 / scale repair tick 1 (2026-09-07): owner reports "the whole
pattern disappears" below 1.00x. The old compositor used a scaled texture as
an additional mask over unscaled paint. Transform the pattern's signed ink
instead. Native construction/quality scores are unchanged; scaling evidence
and regression results live in docs/PATTERN_SCALE_REPAIR_2026-09-07.md.
"""
import numpy as np


def composite_pattern_layer(fn, paint, shape, mask, seed, *, opacity=1.,
                            strength=1., intensity=1., mode='overlay', texture_fn=None,
                            hue_shift=0., saturation=0.,
                            **placement):
    """Composite the authored pattern plate, then attenuate once at the destination.

    SPB-105 / visibility tick 2, owner09-07: "100% ... FULL PATTERN".
    No finish geometry/spec/thumbnail changes (M7 unchanged). The legacy paint
    callback is sampled on neutral paint at full strength, independently of the
    source, layer count and sliders. Evidence: PATTERN_VISIBILITY_REPAIR_2026-09-07.
    """
    amount = (np.clip(float(opacity), 0, 1) * np.clip(float(strength), 0, 1)
              * np.clip(float(intensity), 0, 1))
    source = np.asarray(paint, np.float32)[:, :, :3]
    if amount <= 0:
        return source.copy()
    neutral = np.full((*shape[:2], 3), .5, np.float32)
    full_mask = np.ones(shape[:2], np.float32)
    plate = np.asarray(fn(neutral.copy(), shape, full_mask, seed, 1.8, 0.), np.float32)[:, :, :3]
    if float(np.ptp(plate, axis=(0, 1)).max()) <= 1e-7 and texture_fn is not None:
        texture = texture_fn(shape, full_mask, seed, 1.)
        field = np.asarray(texture['pattern_val'] if isinstance(texture, dict) else texture, np.float32)
        plate = np.repeat(field[:, :, None], 3, axis=2)
    # Recover full tonal coverage from the existing low-amplitude authored ink.
    # A common range preserves chroma when a direct paint callback supplies it.
    lo, hi = float(plate.min()), float(plate.max())
    if hi - lo <= 1e-7:
        return source.copy()
    plate = np.clip((plate - lo) / (hi - lo), 0, 1)
    # Place the isolated authored plate, including older non-additive callbacks.
    # The wrapper is additive only for the existing placement adapter.
    def plate_ink(background, _shape, coverage, _seed, _pm, _bb):
        return background + (plate - .5) * coverage[:, :, None]
    plate_ink._spb_pattern_direct_paint = True
    placed = render_pattern_paint(plate_ink, neutral, shape, full_mask, seed, 1., 0., **placement)
    return composite_pattern_pixels(source, placed, mask, amount=amount, mode=mode,
                                    hue_shift=hue_shift, saturation=saturation)


def composite_pattern_pixels(paint, plate, mask, *, amount=1., mode='overlay',
                             hue_shift=0., saturation=0.):
    amount = float(np.clip(amount, 0, 1))
    source = np.asarray(paint, np.float32)[:, :, :3]
    # SPB-105 tick5 (owner09-07): color controls belong to the pattern only.
    # Blend retains source H/S and applies strong pattern value detail. The old
    # RGB hard-light blend changed color and could nearly vanish. M7 artwork
    # unchanged; behavioral evidence: PATTERN_MATERIAL_CONTROLS_2026-09-07.
    if mode == 'blend':
        import cv2
        detail = np.asarray(plate, np.float32) @ np.array([.2126, .7152, .0722], np.float32)
        lo, hi = float(detail.min()), float(detail.max())
        detail = (detail-lo)/(hi-lo) if hi-lo > 1e-7 else np.full_like(detail, .5)
        hsv = cv2.cvtColor(np.clip(source, 0, 1), cv2.COLOR_RGB2HSV)
        hsv[:, :, 2] = .2*hsv[:, :, 2] + .8*(.1 + .85*detail)
        plate = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    elif abs(float(hue_shift)) > 1e-6 or abs(float(saturation)) > 1e-6:
        import cv2
        hsv = cv2.cvtColor(np.ascontiguousarray(np.clip(plate, 0, 1), dtype=np.float32), cv2.COLOR_RGB2HSV)
        hsv[:, :, 0] = (hsv[:, :, 0] + float(hue_shift)) % 360.
        shift = float(np.clip(saturation, -100, 100))/100.
        sat = hsv[:, :, 1]
        hsv[:, :, 1] = sat + (1-sat)*shift if shift >= 0 else sat*(1+shift)
        plate = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    alpha = np.clip(np.asarray(mask, np.float32), 0, 1)[:, :, None] * amount
    return np.ascontiguousarray(source * (1 - alpha) + plate * alpha, dtype=np.float32)


def render_pattern_paint(fn, paint, shape, mask, seed, pm, bb, *, scale=1.,
                         rotation=0., offset_x=.5, offset_y=.5,
                         flip_h=False, flip_v=False, fit_zone=False):
    """Direct rebuilt patterns add signed ink; other paint functions stay native.

    A neutral, fully covered plate isolates that ink before any placement.
    The destination mask is applied last, so neither zone edges nor logos can
    be tiled. Identity settings call the original renderer byte for byte.
    """
    direct = getattr(fn, '_spb_pattern_direct_paint', False)
    native = (abs(scale-1) < 1e-6 and abs(rotation % 360) < 1e-6
              and abs(offset_x-.5) < 1e-6 and abs(offset_y-.5) < 1e-6
              and not flip_h and not flip_v and not fit_zone)
    if not direct or native:
        return fn(paint, shape, mask, seed, pm, bb)
    from engine.core import _tile_fractional, _crop_center_array, _rotate_single_array
    from engine.compose import _apply_pattern_offset, _fit_pattern_to_mask_bbox
    h, w = shape[:2]
    neutral = np.full((h, w, 3), .5, np.float32)
    ink = np.asarray(fn(neutral.copy(), shape, np.ones((h, w), np.float32),
                        seed, pm, bb), np.float32)[:, :, :3] - neutral
    scale = max(.1, min(4., float(scale)))
    for ch in range(3):
        field = ink[:, :, ch]
        if scale < 1.:
            field = _tile_fractional(field, 1. / scale, h, w)
        elif scale > 1.:
            field = _crop_center_array(field, scale, h, w)
        if abs(rotation % 360) > 1e-6:
            field = _rotate_single_array(field, rotation, (h, w))
        field = np.array(field, dtype=np.float32, copy=True)
        _apply_pattern_offset(field, (h, w), offset_x, offset_y)
        if flip_h:
            field = np.fliplr(field)
        if flip_v:
            field = np.flipud(field)
        if fit_zone:
            field = _fit_pattern_to_mask_bbox(field, mask)
        ink[:, :, ch] = field
    source = np.asarray(paint, np.float32)[:, :, :3]
    return np.ascontiguousarray(np.clip(source + ink * np.asarray(mask)[:, :, None], 0, 1))
