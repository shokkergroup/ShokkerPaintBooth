"""Shared pattern control transport for preview and Photoshop layer exports."""
import math


def copy_pattern_controls(target, source):
    """Preserve explicit zero and keep every pattern rendering path consistent."""
    if 'pattern_paint_mode' in source:
        target['pattern_paint_mode'] = 'blend' if source['pattern_paint_mode'] == 'blend' else 'overlay'
    for key, low, high in [('pattern_hue_shift', -180, 180),
                           ('pattern_saturation', -100, 100),
                           ('pattern_spec_opacity', 0, 1)]:
        if source.get(key) is None:
            continue
        try:
            value = float(source[key])
        except (ValueError, TypeError):
            value = 0.
        target[key] = max(low, min(high, value)) if math.isfinite(value) else 0.
    if source.get('pattern_stack'):
        target['pattern_stack'] = source['pattern_stack']
