"""Shared authored-art routing for the regular pattern picker and paint layers.

SPB-105 / color routing tick3 (owner2026-09-07): "Abstract Gradient ... full
color ... Leg Warmer does not. Funk Zigzag doesn't." Use the existing artwork
already promised by the picker. No new finish construction or M7 score claim.
Evidence: docs/PATTERN_COLOR_ROUTING_2026-09-07.md.
"""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def picker_pattern_artwork(pattern_id):
    import shokker_engine_v2 as engine
    path = getattr(engine, '_SPB_REGULAR_IMAGE_OVERRIDES', {}).get(pattern_id)
    if not path:
        return None
    resolved = ROOT / path
    if not resolved.is_file():
        raise FileNotFoundError(f'Pattern artwork missing [{pattern_id}]: {resolved}')
    return str(resolved)


def pattern_color_source(pattern_id, entry, mode):
    if mode in ('overlay', 'blend'):
        artwork = picker_pattern_artwork(pattern_id)
        if artwork:
            return artwork
    return entry.get('image_path')


def pattern_paint_source(entry, mode):
    if mode in ('overlay', 'blend') and callable(entry.get('_spb_authored_paint_fn')):
        return entry['_spb_authored_paint_fn'], entry.get('_spb_authored_texture_fn')
    return entry.get('paint_fn'), entry.get('texture_fn')


def load_pattern_artwork(path, shape, *, scale=1., rotation=0., offset_x=.5,
                         offset_y=.5, flip_h=False, flip_v=False, fit_zone=False,
                         mask=None):
    from engine.render import _load_color_image_pattern
    from engine.compose import _apply_pattern_offset, _fit_pattern_to_mask_bbox
    # Full overlays respect authored alpha. Dark colors are artwork, not a key.
    cached = _load_color_image_pattern(path, shape, scale=scale, rotation=rotation,
                                       preserve_alpha=True)
    if cached is None:
        raise ValueError(f'Cannot load pattern color artwork: {path}')
    rgba = np.array(cached, copy=True)
    for ch in range(4):
        _apply_pattern_offset(rgba[:, :, ch], shape, offset_x, offset_y)
    if flip_h:
        rgba = np.fliplr(rgba)
    if flip_v:
        rgba = np.flipud(rgba)
    if fit_zone and mask is not None:
        rgba = _fit_pattern_to_mask_bbox(rgba, mask)
    return np.ascontiguousarray(rgba)


def composite_zone_pattern(paint, pattern_id, shape, mask, seed, zone, *,
                           layer=None, scale=1., rotation=0., opacity=1.):
    """Use the regular pattern color contract over a monolithic finish, too.

    SPB-105 / color routing tick4, owner09-07: "LEG WARMER at Overlay - full
    pattern ... not really got any color". The monolithic caller bypassed the
    color repair and still shaded its base. Authored geometry/M7 are unchanged;
    real Soul Core preview/export evidence is in PATTERN_COLOR_ROUTING_2026-09-07.
    """
    from engine.registry import PATTERN_REGISTRY
    from engine.spec_paint import paint_none
    from engine.pattern_paint_placement import composite_pattern_layer, composite_pattern_pixels

    mode = zone.get('pattern_paint_mode', 'overlay')
    strength = float(zone.get('pattern_spec_mult', 1.))
    try:
        intensity = float(zone.get('pattern_intensity', 100)) / 100.
    except (TypeError, ValueError):
        intensity = 1.
    amount = (np.clip(opacity, 0, 1) * np.clip(strength, 0, 1)
              * np.clip(intensity, 0, 1))
    if amount <= 0:
        return np.asarray(paint, np.float32)[:, :, :3].copy()
    entry = PATTERN_REGISTRY[pattern_id]
    controls = zone if layer is None else layer
    prefix = 'pattern_' if layer is None else ''
    color_controls = dict(hue_shift=float(controls.get(prefix+'hue_shift', 0)),
                          saturation=float(controls.get(prefix+'saturation', 0)))
    placement = dict(scale=scale, rotation=rotation,
        offset_x=float(controls.get(prefix+'offset_x', .5)),
        offset_y=float(controls.get(prefix+'offset_y', .5)),
        flip_h=bool(controls.get(prefix+'flip_h', False)),
        flip_v=bool(controls.get(prefix+'flip_v', False)),
        fit_zone=bool(controls.get(prefix+'fit_zone', False)))
    hard_mask = np.where(mask > .5, mask, 0.).astype(np.float32)
    path = pattern_color_source(pattern_id, entry, mode)
    if path:
        rgba = load_pattern_artwork(path, shape, mask=hard_mask, **placement)
        return composite_pattern_pixels(paint, rgba[:, :, :3],
            hard_mask * rgba[:, :, 3], amount=amount, mode=mode, **color_controls)
    painter, texture = pattern_paint_source(entry, mode)
    return composite_pattern_layer(painter or paint_none, paint, shape, hard_mask,
        seed, opacity=opacity, strength=strength, intensity=intensity,
        mode=mode, texture_fn=texture, **color_controls, **placement)
