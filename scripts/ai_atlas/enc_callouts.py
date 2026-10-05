"""Encyclopedia lane S - callout annotation helper.

Draws numbered badges (and an optional outline box) on top of an app screenshot, in the app's own
colours (orange accent #f5761a on the dark panel look), so a buyer can match "1, 2, 3" in the text
to the exact control in the picture.

    from enc_callouts import annotate
    im = annotate(im, [dict(n=1, rect=(x, y, w, h)), dict(n=2, rect=(...), at="r")], scale=2)

`rect` is in CSS pixels relative to the cropped image's own top-left corner; `scale` is the
device-pixel ratio the screenshot was taken at (2 for crisp text). `at` is where the badge sits
on the rect: tl (default), tr, bl, br, l, r, t, b, c.  `box=False` draws the badge only.
"""
from PIL import Image, ImageDraw, ImageFont

ORANGE = (245, 118, 26)
DARK = (11, 14, 23)
WHITE = (255, 255, 255)
_F = {}


def _font(px):
    if px not in _F:
        for p in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
            try:
                _F[px] = ImageFont.truetype(p, px)
                break
            except Exception:
                continue
        else:
            _F[px] = ImageFont.load_default()
    return _F[px]


def _anchor(rect, at, scale, r):
    x, y, w, h = [v * scale for v in rect]
    pts = {"tl": (x, y), "tr": (x + w, y), "bl": (x, y + h), "br": (x + w, y + h),
           "l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y), "b": (x + w / 2, y + h),
           "c": (x + w / 2, y + h / 2)}
    return pts.get(at, pts["tl"])


def annotate(im, marks, scale=2, radius=11, box_width=2):
    """Return a copy of `im` with the callouts drawn. Badge radius is in CSS px (scaled up)."""
    out = im.convert("RGB").copy()
    # a soft translucent layer for the box fill keeps the target readable
    d = ImageDraw.Draw(out, "RGBA")
    r = int(radius * scale)
    bw = max(2, int(box_width * scale))
    for m in marks:
        rect = m.get("rect")
        if rect is None:
            continue
        pad = m.get("pad", 2) * scale
        x, y, w, h = [v * scale for v in rect]
        if m.get("box", True):
            d.rounded_rectangle((x - pad, y - pad, x + w + pad, y + h + pad), radius=int(4 * scale), outline=ORANGE + (255,),
                                width=bw, fill=ORANGE + (22,))
    for m in marks:
        rect = m.get("rect")
        if rect is None:
            continue
        cx, cy = _anchor(rect, m.get("at", "tl"), scale, r)
        cx += m.get("dx", 0) * scale
        cy += m.get("dy", 0) * scale
        d.ellipse((cx - r - 2 * scale, cy - r - 2 * scale, cx + r + 2 * scale, cy + r + 2 * scale), fill=DARK + (255,))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ORANGE + (255,))
        f = _font(int(r * 1.35))
        d.text((cx, cy - scale * 0.5), str(m["n"]), font=f, fill=WHITE + (255,), anchor="mm")
    return out


def side_by_side(before, after, label_a="Before", label_b="After", gap=16, label_h=34, bg=(11, 14, 23)):
    """Two images side by side with an arrow between them and a label under each (before/after pairs)."""
    h = max(before.height, after.height)
    w = before.width + after.width + gap * 3
    gap2 = gap * 3
    out = Image.new("RGB", (before.width + after.width + gap2, h + label_h + gap), bg)
    out.paste(before, (0, 0))
    out.paste(after, (before.width + gap2, 0))
    d = ImageDraw.Draw(out)
    f = _font(max(16, label_h // 2 + 2))
    d.text((before.width // 2, h + label_h // 2 + 4), label_a, font=f, fill=(238, 242, 249), anchor="mm")
    d.text((before.width + gap2 + after.width // 2, h + label_h // 2 + 4), label_b, font=f, fill=(238, 242, 249), anchor="mm")
    ax = before.width + gap2 // 2
    ay = h // 2
    s = max(8, gap)
    d.polygon([(ax - s, ay - s), (ax + s, ay), (ax - s, ay + s)], fill=ORANGE)
    return out
