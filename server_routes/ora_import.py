"""OpenRaster (.ora) reader with a psd_tools-compatible facade.

Owner request 2026-07-04: GIMP users can't import their layered work (GIMP's
native .xcf has no dependency-free Python reader). OpenRaster is the open
layered format GIMP (File → Export As → .ora) and Krita export natively:
a ZIP containing stack.xml (the layer tree), data/*.png (layer pixels) and
mergedimage.png (the flattened composite, required by the ORA spec).

This module parses .ora into objects that quack exactly like psd_tools'
PSDImage/Layer as far as server_routes/psd_import_routes.py uses them:

    psd.width / psd.height / len(psd) / iter(psd)      (bottom-up, like psd_tools)
    layer.kind ('pixel' | 'group'), .name, .visible (settable), .opacity (0-255),
    layer.bbox (x1, y1, x2, y2), .blend_mode (str), group iteration,
    layer.composite(force=...) -> PIL RGBA image of the layer's own pixels,
    root.composite() -> flattened composite.

Because the facade is API-identical at those touchpoints, all three PSD routes
(/api/psd-import, /api/psd-rasterize-all, /api/psd-layer) and the whole booth
layer system work on .ora files with no further changes.

Native .xcf support is deliberately deferred: it needs the `gimpformats` pip
package bundled into the packaged build (owner decision + release task).
Zero new dependencies here: zipfile + ElementTree + PIL only.
"""

from __future__ import annotations

import io
import os
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _to_opacity_255(value):
    """ORA opacity is a 0.0-1.0 float string; psd_tools exposes 0-255 int."""
    try:
        return max(0, min(255, int(round(float(value) * 255))))
    except (TypeError, ValueError):
        return 255


def _blend_mode(composite_op):
    """Map ORA/SVG composite ops onto psd_tools-style blend mode names."""
    op = (composite_op or 'svg:src-over').strip().lower()
    table = {
        'svg:src-over': 'NORMAL',
        'svg:multiply': 'MULTIPLY',
        'svg:screen': 'SCREEN',
        'svg:overlay': 'OVERLAY',
        'svg:darken': 'DARKEN',
        'svg:lighten': 'LIGHTEN',
        'svg:color-dodge': 'COLOR_DODGE',
        'svg:color-burn': 'COLOR_BURN',
        'svg:hard-light': 'HARD_LIGHT',
        'svg:soft-light': 'SOFT_LIGHT',
        'svg:difference': 'DIFFERENCE',
        'svg:plus': 'LINEAR_DODGE',
    }
    return table.get(op, 'NORMAL')


class OraLayer:
    """A pixel layer. Quacks like a psd_tools pixel layer for our routes."""

    kind = 'pixel'

    def __init__(self, zf_path, name, src, x, y, opacity, visible, blend_mode, size):
        self._zf_path = zf_path
        self._src = src
        self.name = name
        self.visible = visible
        self.opacity = opacity
        self.blend_mode = blend_mode
        w, h = size
        self.bbox = (x, y, x + w, y + h)

    def composite(self, force=False):  # noqa: ARG002 (signature parity)
        with zipfile.ZipFile(self._zf_path) as zf:
            with zf.open(self._src) as fh:
                img = Image.open(fh)
                img.load()
        return img.convert('RGBA')


class OraGroup:
    """A layer group (ORA <stack>). Iterable like a psd_tools group."""

    kind = 'group'

    def __init__(self, name, children, opacity, visible):
        self.name = name
        self.visible = visible
        self.opacity = opacity
        self.blend_mode = 'NORMAL'
        self._children = children  # bottom-up, matching psd_tools iteration
        if children:
            self.bbox = (
                min(c.bbox[0] for c in children),
                min(c.bbox[1] for c in children),
                max(c.bbox[2] for c in children),
                max(c.bbox[3] for c in children),
            )
        else:
            self.bbox = (0, 0, 0, 0)

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def composite(self, force=False):
        """Flatten this group's visible children (bottom-up paste)."""
        x1, y1, x2, y2 = self.bbox
        w, h = max(1, x2 - x1), max(1, y2 - y1)
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for child in self._children:  # bottom-up: paint in iteration order
            if not child.visible and not force:
                continue
            img = child.composite(force=force)
            if img is None:
                continue
            if child.opacity < 255:
                alpha = img.getchannel('A').point(lambda a: a * child.opacity // 255)
                img.putalpha(alpha)
            out.alpha_composite(img, (child.bbox[0] - x1, child.bbox[1] - y1))
        return out


class OraImage:
    """Root document. Quacks like psd_tools.PSDImage for our routes."""

    def __init__(self, path, width, height, children, merged_src):
        self._path = path
        self._merged_src = merged_src
        self.width = width
        self.height = height
        self._children = children  # bottom-up

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def composite(self, force=False):
        # mergedimage.png is REQUIRED by the ORA spec — prefer it (it is exactly
        # what the authoring app showed). Fall back to manual flatten if absent.
        if self._merged_src:
            try:
                with zipfile.ZipFile(self._path) as zf:
                    with zf.open(self._merged_src) as fh:
                        img = Image.open(fh)
                        img.load()
                return img.convert('RGBA')
            except Exception as _spb_ex:
                _spb_swallow('composite@L159', _spb_ex)
        root = OraGroup('root', self._children, 255, True)
        canvas = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        flat = root.composite(force=force)
        canvas.alpha_composite(flat, (max(0, root.bbox[0]), max(0, root.bbox[1])))
        return canvas

    # ---- parsing -----------------------------------------------------------

    @classmethod
    def open(cls, path):
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            if 'stack.xml' not in names:
                raise ValueError('Not an OpenRaster file (missing stack.xml)')
            root = ET.fromstring(zf.read('stack.xml'))
            width = int(root.get('w', 0) or 0)
            height = int(root.get('h', 0) or 0)

            def png_size(src):
                try:
                    with zf.open(src) as fh:
                        img = Image.open(fh)
                        return img.size
                except Exception:
                    return (width, height)

            group_counter = [0]

            def parse_stack(stack_el):
                children_top_down = []
                for el in stack_el:
                    tag = el.tag.split('}')[-1]  # tolerate namespaced tags
                    visible = (el.get('visibility', 'visible') != 'hidden')
                    opacity = _to_opacity_255(el.get('opacity', '1.0'))
                    if tag == 'layer':
                        src = el.get('src', '')
                        if not src or src not in names:
                            continue
                        children_top_down.append(OraLayer(
                            path,
                            el.get('name') or os.path.basename(src),
                            src,
                            int(float(el.get('x', 0) or 0)),
                            int(float(el.get('y', 0) or 0)),
                            opacity,
                            visible,
                            _blend_mode(el.get('composite-op')),
                            png_size(src),
                        ))
                    elif tag == 'stack':
                        group_counter[0] += 1
                        kids = parse_stack(el)
                        children_top_down.append(OraGroup(
                            el.get('name') or f'Group {group_counter[0]}',
                            kids, opacity, visible,
                        ))
                # ORA stack.xml lists the TOP layer first; psd_tools iterates
                # bottom-up. Reverse every level so the facade matches.
                return list(reversed(children_top_down))

            top_stack = root.find('stack')
            if top_stack is None:
                # tolerate namespaced <stack>
                for el in root:
                    if el.tag.split('}')[-1] == 'stack':
                        top_stack = el
                        break
            children = parse_stack(top_stack) if top_stack is not None else []
            merged = 'mergedimage.png' if 'mergedimage.png' in names else None
            if not width or not height:
                if merged:
                    with zf.open(merged) as fh:
                        img = Image.open(fh)
                        width, height = img.size
                elif children:
                    width = max(c.bbox[2] for c in children)
                    height = max(c.bbox[3] for c in children)
        return cls(path, width, height, children, merged)
