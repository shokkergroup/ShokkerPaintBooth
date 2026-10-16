"""Exact private proposal: recover leaf pixels independently of display visibility.

The saved-scheme subscription journey exposed transparent rasters beneath hidden
PSD groups. This is an import correction, not permission to show those groups.
"""
import inspect


def rasterize_leaf_pixels(layer):
    from psd_tools.api.layers import Layer

    if isinstance(layer, Layer):
        if layer.is_group():
            # The on-demand endpoint can also name a group. Keep its existing
            # composite semantics; do not reveal every child of that group.
            return layer.composite()
        # Leaf-only routes: retain masks/effects while ignoring ancestor display
        # visibility. Do not mutate the cached PSD or awaken sibling layers.
        return layer.composite(force=True, layer_filter=lambda _: True)
    # SPB's ORA/XCF facades already return their individual raster; they do not
    # implement psd-tools' layer_filter parameter.
    return layer.composite(force=True)


def candidate(source):
    before = '''                    was_visible = bool(child.visible)
                    if not was_visible:
                        child.visible = True
                    try:
                        img = child.composite(force=True)
                    finally:
                        if not was_visible:
                            child.visible = False'''
    replacements = [
        (before, '                    img = rasterize_leaf_pixels(child)'),
        ('            img = current.composite()', '            img = rasterize_leaf_pixels(current)'),
    ]
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError('PSD route changed; review the new source before applying this candidate')
        source = source.replace(old, new, 1)
    marker = 'def register_psd_import_routes('
    if source.count(marker) != 1:
        raise ValueError('PSD route registration changed')
    return source.replace(marker, inspect.getsource(rasterize_leaf_pixels) + '\n\n' + marker, 1)
