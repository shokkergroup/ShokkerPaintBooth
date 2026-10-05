# -*- coding: utf-8 -*-
"""DAY / NIGHT APPEARANCE — simulate what a paint+spec pair looks like under
broad daylight versus track point-lighting, and measure the hue shift between.

Owner on FRACTURED NIGHTSHIFT, 2026-08-31: *"This was supposed to make cars
change hues between day and night and not JUST blow it out to white but this
category did NOT live up to the hype of what it was supposed to do."*

Nothing in the pipeline ever measured that claim, so nothing enforced it. This
module is the measurement.

THE PHYSICS THAT MAKES A HUE FLIP POSSIBLE
------------------------------------------
From Spec Guide v1 §1: *"Metallic reflection is tinted by the paint/albedo and
suppresses diffuse color. Dielectric and clearcoat highlights are substantially
white."* That single sentence is the whole mechanism:

  * a DIELECTRIC pixel (M≈0) shows its albedo diffusely, and its highlight is
    WHITE — so under a hard light it washes toward white;
  * a METALLIC pixel (M≈255) shows almost no diffuse, and its reflection is
    TINTED BY ITS OWN ALBEDO — so under a hard light it glows in its own hue.

So a car changes hue between day and night when it carries TWO populations:
one dielectric in hue A, one metallic in a DIFFERENT hue B. Daylight is broad
and diffuse, so population A's diffuse response dominates and the car reads A.
Night is a few hard point lights, so population B's tinted specular dominates
and the car reads B.

And it blows out to white — the exact failure the owner describes — when the
night population is near-white albedo, or when it is dielectric (white
highlight), or when both populations share a hue.

WHAT THIS IS NOT: a renderer. It is a deliberately simple Cook-Torrance-ish
evaluation whose only job is to be *directionally* right about hue and
saturation under two very different illuminations, so a gate can hold a
category to its own promise. Real proof is still a track capture.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None


def _srgb_to_lin(x):
    x = np.clip(np.asarray(x, np.float32), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def _lin_to_srgb(x):
    x = np.clip(np.asarray(x, np.float32), 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055).astype(np.float32)


# Illumination presets. `amb` is broad hemispherical light (sky), `key` is the
# directional/point term, `spread` is how much of the highlight lobe a surface
# sees — daylight fills a wide cone, a night pit lamp is nearly a point.
DAY = dict(amb=1.00, key=0.85, spread=0.85, tint=(1.00, 0.99, 0.97), name="day")
DUSK = dict(amb=0.34, key=0.70, spread=0.45, tint=(1.00, 0.86, 0.72), name="dusk")
NIGHT = dict(amb=0.055, key=1.45, spread=0.10, tint=(0.97, 0.98, 1.00), name="night")


def appearance(paint, spec, light=NIGHT, exposure=None):
    """Approximate sRGB appearance of a paint+spec pair under one lighting rig.

    paint: HxWx3 float 0..1 (albedo).  spec: HxWx3 uint8 (M, Rough, Cc).
    """
    a = np.asarray(paint, np.float32)
    if a.max() > 1.5:
        a = a / 255.0
    a = _srgb_to_lin(a[..., :3])

    s = np.asarray(spec, np.float32)[..., :3]
    m = np.clip(s[..., 0] / 255.0, 0.0, 1.0)
    rough = np.clip(np.maximum(s[..., 1], 4.0) / 255.0, 0.02, 1.0)
    # Cc is INVERTED: 16 is the strongest active coat, 255 is none.
    cc_raw = s[..., 2]
    coat = np.clip(1.0 - (cc_raw - 16.0) / 239.0, 0.0, 1.0)
    coat = np.where(cc_raw < 16.0, 0.0, coat).astype(np.float32)

    L = np.asarray(light["tint"], np.float32)[None, None, :]

    # DIFFUSE — suppressed by metalness. This is what daylight mostly shows.
    diffuse = a * (1.0 - m)[..., None] * (light["amb"] * 0.85 + light["key"] * 0.25)

    # SPECULAR — F0 is the whole trick: 4% white for a dielectric, the ALBEDO
    # ITSELF for a metal. A metal's highlight therefore carries its own colour
    # while a dielectric's highlight is white.
    f0 = 0.04 * (1.0 - m)[..., None] + a * m[..., None]
    # narrow lobes concentrate energy; a point light through a smooth surface is
    # the brightest thing on a night car
    lobe = (light["spread"] + (1.0 - light["spread"]) * (1.0 - rough)) ** 3.0
    gain = light["key"] * (0.35 + 2.6 * (1.0 - rough) ** 2)
    specular = f0 * (lobe * gain)[..., None]

    # CLEARCOAT — a second, substantially WHITE lobe on top. This is the term
    # that washes a car out when it is the only thing responding at night.
    ccl = coat * light["key"] * (0.30 + 1.5 * (1.0 - rough) ** 2) * light["spread"] ** 0.5
    clear = np.repeat(ccl[..., None], 3, axis=2) * 0.16

    out = (diffuse + specular + clear) * L
    if exposure is None:
        # auto-expose to a common mid-grey so day and night are compared on
        # appearance, not on brightness
        lum = float(np.mean(0.2126 * out[..., 0] + 0.7152 * out[..., 1] + 0.0722 * out[..., 2]))
        exposure = 0.32 / max(lum, 1e-4)
    out = out * float(exposure)
    out = out / (1.0 + out)                                   # Reinhard
    return np.clip(_lin_to_srgb(out), 0.0, 1.0)


def _hue_sat(rgb, min_sat=0.05, bins=72):
    """DOMINANT hue (the mode of the saturation-weighted hue histogram) and mean
    saturation.

    Not the circular mean. These finishes are deliberately BIMODAL — two
    populations in two different hues — and a circular mean of a bimodal
    distribution sits between the two modes and barely moves as the balance
    changes: a near-opposite pair (magenta against green) measured a 6 deg
    shift while visibly flipping from one to the other. The mode is what the
    eye actually reports, and for a bimodal field it moves cleanly from one
    population to the other, which is the event being measured.
    """
    if cv2 is None:
        return 0.0, 0.0
    hsv = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    h = hsv[..., 0].ravel()
    sv = (hsv[..., 1] * np.clip(hsv[..., 2], 0, 1)).ravel()
    sel = sv > min_sat
    if sel.sum() < 64:
        return 0.0, float(hsv[..., 1].mean())
    hist, edges = np.histogram(h[sel], bins=bins, range=(0.0, 360.0), weights=sv[sel])
    # circular 3-bin smoothing so a mode split across a bin edge still wins
    hist = (np.roll(hist, 1) + 2.0 * hist + np.roll(hist, -1)) / 4.0
    k = int(np.argmax(hist))
    peak = 0.5 * (edges[k] + edges[k + 1])
    return float(peak % 360.0), float(hsv[..., 1][sel.reshape(hsv.shape[:2])].mean())


def hue_shift(paint, spec, a=DAY, b=NIGHT, stride=3):
    """(shift_degrees, day_hue, night_hue, day_sat, night_sat, whiteout).

    `whiteout` is the fraction of the night image that has gone essentially
    colourless — the specific failure the owner named. A finish can post a big
    hue number and still be a failure if it got there by washing out.
    """
    p = np.asarray(paint)[::stride, ::stride]
    s = np.asarray(spec)[::stride, ::stride]
    ia = appearance(p, s, a)
    ib = appearance(p, s, b)
    ha, sa = _hue_sat(ia)
    hb, sb = _hue_sat(ib)
    d = abs(hb - ha) % 360.0
    d = min(d, 360.0 - d)
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(ib, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        white = float(((hsv[..., 1] < 0.12) & (hsv[..., 2] > 0.55)).mean())
    else:
        white = 0.0
    return float(d), ha, hb, sa, sb, white


def _hue_mass(rgb, centre, half=40.0, min_sat=0.05):
    """Saturation-weighted mass of pixels whose hue is within `half` of `centre`."""
    if cv2 is None:
        return 0.0
    hsv = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    h = hsv[..., 0]
    sv = hsv[..., 1] * np.clip(hsv[..., 2], 0, 1)
    d = np.abs((h - float(centre) + 180.0) % 360.0 - 180.0)
    return float((sv * (d <= float(half)) * (sv > min_sat)).sum())


def two_modes(rgb, min_gap=45.0, bins=72, min_sat=0.05):
    """The two dominant hue modes of an image, at least `min_gap` apart.

    Used so the swing test can be run on ANY finish — including the old ones
    that carry no declared hue pair — which is what makes it a fair control."""
    if cv2 is None:
        return 0.0, 180.0
    hsv = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    h = hsv[..., 0].ravel()
    sv = (hsv[..., 1] * np.clip(hsv[..., 2], 0, 1)).ravel()
    sel = sv > min_sat
    if sel.sum() < 64:
        return 0.0, 180.0
    hist, edges = np.histogram(h[sel], bins=bins, range=(0.0, 360.0), weights=sv[sel])
    hist = (np.roll(hist, 1) + 2.0 * hist + np.roll(hist, -1)) / 4.0
    ctr = 0.5 * (edges[:-1] + edges[1:])
    k1 = int(np.argmax(hist))
    d = np.abs((ctr - ctr[k1] + 180.0) % 360.0 - 180.0)
    far = hist.copy()
    far[d < min_gap] = -1.0
    k2 = int(np.argmax(far))
    return float(ctr[k1]), float(ctr[k2])


def hue_swing(paint, spec, a=DAY, b=NIGHT, stride=3, hues=None):
    """How much of the car's COLOUR BALANCE moves from one hue to the other
    between day and night.

    This is the honest measure for a deliberately BIMODAL finish, and it is the
    third metric this file has carried — the first two both failed in
    instructive ways. A circular MEAN of two opposed populations sits at the
    midpoint and barely moves (a visible magenta-to-green flip measured 6°). The
    dominant MODE moves in all-or-nothing jumps (the same set gave twenty
    finishes 0° and the rest 180°). What a driver actually sees is neither: it
    is one colour taking over from the other, so measure the SHARE.

        swing = (night share of hue B) - (day share of hue B)

    in 0..1, where 0.20 is a clearly visible takeover and 0.5+ is dramatic.
    Returns (swing, sep, day_share_B, night_share_B, night_sat, whiteout).
    """
    p = np.asarray(paint)[::stride, ::stride]
    s = np.asarray(spec)[::stride, ::stride]
    ia = appearance(p, s, a)
    ib = appearance(p, s, b)
    hA, hB = hues if hues else two_modes(ia)
    sep = abs((hB - hA + 180.0) % 360.0 - 180.0)

    def share(img):
        mA = _hue_mass(img, hA)
        mB = _hue_mass(img, hB)
        return mB / max(mA + mB, 1e-6)

    da, nb = share(ia), share(ib)
    _hn, sn = _hue_sat(ib)
    if cv2 is not None:
        hsv = cv2.cvtColor(np.clip(ib, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        white = float(((hsv[..., 1] < 0.12) & (hsv[..., 2] > 0.55)).mean())
    else:
        white = 0.0
    return float(nb - da), float(sep), float(da), float(nb), float(sn), float(white)
