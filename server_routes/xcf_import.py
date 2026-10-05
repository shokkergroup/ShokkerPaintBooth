"""GIMP native .xcf reader with a psd_tools-compatible facade.

Owner request 2026-07-04: full built-in GIMP support — .ora (ora_import.py)
covers the zero-dependency path; THIS module reads GIMP's native .xcf directly
via the pure-python `gimpformats` package (pip install gimpformats).

Facade contract (same as ora_import.py): objects quack like psd_tools'
PSDImage/Layer at every touchpoint psd_import_routes.py uses — width/height,
len()/iter() bottom-up, layer.kind/.name/.visible (settable)/.opacity (0-255)/
.bbox/.blend_mode, group iteration, layer.composite() -> PIL RGBA,
root.composite() -> flattened image. All three PSD routes and the booth layer
system therefore work on .xcf untouched.

DEPENDENCY IS OPTIONAL: if gimpformats is missing (e.g. a packaged build that
didn't bundle it), open() raises XcfSupportMissing with a user-facing message
steering the painter to GIMP's File > Export As > .ora / .psd — the app keeps
working, the error is honest.

RELEASE NOTE (beta checklist): `gimpformats` must be in requirements.txt AND
present in the build's Python env or packaged .xcf import degrades to the
XcfSupportMissing message (by design, never a crash).
"""

from __future__ import annotations

from PIL import Image


class XcfSupportMissing(RuntimeError):
    """Raised when gimpformats is not installed in this environment."""

    USER_MESSAGE = (
        ".xcf support needs the 'gimpformats' package (pip install gimpformats). "
        "Meanwhile: in GIMP use File > Export As > yourcar.ora (or .psd) — both "
        "import with layers intact."
    )


def _opacity_255(value):
    """gimpformats exposes opacity as 0.0-1.0 float; psd_tools uses 0-255."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 255
    if v <= 1.0:
        v *= 255.0
    return max(0, min(255, int(round(v))))


def _blend_name(raw):
    """Best-effort GIMP blend -> psd_tools-style name (NORMAL when unsure)."""
    s = str(raw or '').upper()
    for name in ('MULTIPLY', 'SCREEN', 'OVERLAY', 'DARKEN', 'LIGHTEN',
                 'DODGE', 'BURN', 'HARD_LIGHT', 'SOFT_LIGHT', 'DIFFERENCE'):
        if name.replace('_', '') in s.replace('_', '').replace(' ', ''):
            return 'COLOR_DODGE' if name == 'DODGE' else ('COLOR_BURN' if name == 'BURN' else name)
    return 'NORMAL'


class XcfLayer:
    """A pixel layer. Quacks like a psd_tools pixel layer for our routes."""

    kind = 'pixel'

    def __init__(self, gimp_layer):
        self._layer = gimp_layer
        self.name = gimp_layer.name or 'Layer'
        self.visible = bool(getattr(gimp_layer, 'visible', True))
        self.opacity = _opacity_255(getattr(gimp_layer, 'opacity', 1.0))
        self.blend_mode = _blend_name(getattr(gimp_layer, 'blendMode', None))
        x = int(getattr(gimp_layer, 'xOffset', 0) or 0)
        y = int(getattr(gimp_layer, 'yOffset', 0) or 0)
        w = int(getattr(gimp_layer, 'width', 0) or 0)
        h = int(getattr(gimp_layer, 'height', 0) or 0)
        self.bbox = (x, y, x + w, y + h)

    def composite(self, force=False):  # noqa: ARG002 (signature parity)
        img = self._layer.image
        if img is None:
            return Image.new('RGBA', (max(1, self.bbox[2] - self.bbox[0]),
                                      max(1, self.bbox[3] - self.bbox[1])), (0, 0, 0, 0))
        return img.convert('RGBA')


class XcfGroup:
    """A layer group. Iterable like a psd_tools group."""

    kind = 'group'

    def __init__(self, name, children, visible=True, opacity=255):
        self.name = name or 'Group'
        self._children = children  # bottom-up, matching psd_tools iteration
        self.visible = visible
        self.opacity = opacity
        self.blend_mode = 'NORMAL'
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
        x1, y1, x2, y2 = self.bbox
        out = Image.new('RGBA', (max(1, x2 - x1), max(1, y2 - y1)), (0, 0, 0, 0))
        for child in self._children:  # bottom-up paint order
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


class XcfImage:
    """Root document. Quacks like psd_tools.PSDImage for our routes."""

    def __init__(self, doc, tree, children):
        self._doc = doc
        self._tree = tree
        self.width = int(doc.width)
        self.height = int(doc.height)
        self._children = children  # bottom-up

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def composite(self, force=False):  # noqa: ARG002
        try:
            return self._doc.render(self._tree).convert('RGBA')
        except Exception:
            # Manual flatten fallback — same approach as OraImage.
            canvas = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            root = XcfGroup('root', self._children)
            flat = root.composite()
            canvas.alpha_composite(flat, (max(0, root.bbox[0]), max(0, root.bbox[1])))
            return canvas

    @classmethod
    def open(cls, path):
        try:
            from gimpformats.gimpXcfDocument import GimpDocument
        except ImportError as err:
            raise XcfSupportMissing(XcfSupportMissing.USER_MESSAGE) from err

        doc = GimpDocument(str(path))
        tree = doc.walkTree()

        def convert_children(group_node):
            """gimpformats tree children are TOP-first; reverse for psd_tools
            bottom-up parity. Duck-type: .children => group, .image => layer."""
            out_top_down = []
            for child in getattr(group_node, 'children', []) or []:
                if hasattr(child, 'children'):  # nested GimpGroup
                    opts = getattr(child, 'layer_options', None)
                    out_top_down.append(XcfGroup(
                        getattr(child, 'name', None),
                        convert_children(child),
                        visible=bool(getattr(opts, 'visible', True)) if opts is not None else True,
                        opacity=_opacity_255(getattr(opts, 'opacity', 1.0)) if opts is not None else 255,
                    ))
                elif hasattr(child, 'image'):
                    if getattr(child, 'isGroup', False):
                        continue  # group placeholder layer already handled as a group node
                    out_top_down.append(XcfLayer(child))
            return list(reversed(out_top_down))

        return cls(doc, tree, convert_children(tree))
