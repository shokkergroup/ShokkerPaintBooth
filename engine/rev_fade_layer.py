"""[SPB-REV-FADE 2026-10-10] Car-Space Fade post-pass (js/rev/fade).

Runs inside ``rev_material_layer.apply_rev_material_layers`` (one call at its end), i.e. after every zone, the iron-rule floors, the material
instances and the Material / Spec / Wear layer, and before the preview return / TGA write. Live preview and RENDER share this one code path,
so a render writes exactly what the preview shows. No ``fade`` list in the ``_spb_rev_material`` payload (or env ``SPB_REV_FADE_OFF=1``)
returns the inputs untouched (byte-identical).

Payload, one entry per fade, applied in list order::

    {"v": 1, "size": [W, H],                    # document pixels the crops refer to
     "bbox": [x, y, w, h],                      # the covered area (w, h are multiples of ts)
     "cov":  "data:image/png;base64,...",       # gray 8 bit, w x h: coverage 0..255 (selected parts x selection / zone clip)
     "t":    "data:image/png;base64,...",       # RGB, (w/ts) x (h/ts): position along the fade as 16 bit, R = high byte, G = low byte
     "ts": 4, "paint": true,
     "stops": [{"p": 0..1, "color": [r,g,b] | null, "spec": [M,R,CC] | null, "zone": {server zone} | null}, ...]}

Per pixel the stops get piecewise-linear weights from t (flat before the first / after the last stop) and
    out = base * (1 - cov) + sum_i(w_i * value_i) * cov
 * a colour stop contributes its colour (paint) and its spec triple;
 * a finish stop (``zone``) contributes the paint + spec the real engine renders for that finish (one nested preview-mode render per finish
   stop, the same mechanism the Material Brush coats use);
 * a stop with no colour (or no spec / zone) keeps what is already there for that plane.
iRacing spec semantics: R = metallic, G = roughness (0 mirror), B = clearcoat (0-15 none, 16 max gloss, 255 dull), A = specular mask.
Every channel is interpolated linearly in the 8-bit values, EXCEPT that a stop's clearcoat is raised to 16 BEFORE blending (the iron rule every
SPB material obeys): the ramp is then a clean 16 -> 255 line and never walks through the 0-15 "no clearcoat" band nor plateaus at 16.
Touched pixels get the iron-rule floors again (CC >= 16; G >= 15 unless M >= 240).
"""
import os

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

CC_FLOOR = 16
ROUGH_FLOOR = 15
CHROME_M = 240


def disabled():
    return str(os.environ.get("SPB_REV_FADE_OFF", "")).strip() not in ("", "0", "false", "False")


def find_fades(lay):
    f = lay.get("fade") if isinstance(lay, dict) else None
    return [x for x in f if isinstance(x, dict)] if isinstance(f, list) else []


def stop_weights(t, ps):
    """Piecewise-linear 'hat' weights of the stops at every t (HxW float32 0..1). Returns a list of arrays, one per stop (sorted by p), sum == 1."""
    n = len(ps)
    ps = [float(p) for p in ps]
    for i in range(1, n):  # strictly increasing for np.interp
        if ps[i] <= ps[i - 1]:
            ps[i] = ps[i - 1] + 1e-6
    out = []
    for i in range(n):
        if n == 1:
            out.append(np.ones_like(t, dtype=np.float32))
        elif i == 0:
            out.append(np.interp(t, [ps[0], ps[1]], [1.0, 0.0]).astype(np.float32))
        elif i == n - 1:
            out.append(np.interp(t, [ps[n - 2], ps[n - 1]], [0.0, 1.0]).astype(np.float32))
        else:
            out.append(np.interp(t, [ps[i - 1], ps[i], ps[i + 1]], [0.0, 1.0, 0.0]).astype(np.float32))
    return out


def floor_spec_triple(spec):
    """A stop's spec [M, R, CC] with the clearcoat raised to 16 (the rule above); R is floored later, on the blended value."""
    m, r, cc = [float(v) for v in spec[:3]]
    return [m, r, max(cc, float(CC_FLOOR))]


def _floors(s, touched):
    m, r, cc = s[..., 0], s[..., 1], s[..., 2]
    s[..., 1] = np.where(touched & (m < CHROME_M), np.maximum(r, ROUGH_FLOOR), r)
    s[..., 2] = np.where(touched, np.maximum(cc, CC_FLOOR), cc)
    return s


def _decode_fields(f, size, w, h, helpers):
    """-> (rect, cov float dh x dw, t float dh x dw) placed on the output grid, or None."""
    _decode_png_rgb, _dest_rect, _fit = helpers
    rect = _dest_rect(f.get("bbox"), size, w, h)
    cov_img, t_img = _decode_png_rgb(f.get("cov")), _decode_png_rgb(f.get("t"))
    if rect is None or cov_img is None or t_img is None:
        return None
    x0, y0, x1, y1 = rect
    dw, dh = x1 - x0, y1 - y0
    cov = cov_img[:, :, 0].astype(np.float32) / 255.0
    t16 = (t_img[:, :, 0].astype(np.float32) * 256.0 + t_img[:, :, 1].astype(np.float32)) / 65535.0
    cov = _fit(cov, dw, dh)
    if cov.ndim == 3:
        cov = cov[:, :, 0]
    if t16.shape[1] != dw or t16.shape[0] != dh:
        t16 = cv2.resize(t16, (dw, dh), interpolation=cv2.INTER_LINEAR)
    return rect, np.clip(cov, 0.0, 1.0).astype(np.float32), np.clip(t16, 0.0, 1.0).astype(np.float32)


def _render_finish(zone, rect, cov, size_hw, render_coats, decode_rle):
    """Nested engine render of one finish stop over the whole fade area. -> (paint HxWx3 float32, spec HxWx4 float32) at full output size, or None."""
    h, w = size_hw
    x0, y0, x1, y1 = rect
    zz = {k: v for k, v in zone.items() if k not in ("region_mask", "_spb_rev_material")}
    m = np.zeros((h, w), np.float32)
    m[y0:y1, x0:x1] = (cov > (0.5 / 255.0)).astype(np.float32)
    zz["region_mask"] = m
    zz["hard_edge"] = True
    res = render_coats([zz])
    if not isinstance(res, tuple) or len(res) < 2:
        print(f"  [REV-FADE] finish stop skipped: nested render returned {type(res).__name__}")
        return None
    p, s = np.asarray(res[0]), np.asarray(res[1])
    if p.shape[:2] != (h, w) or s.shape[:2] != (h, w):
        print(f"  [REV-FADE] finish stop skipped: nested render {p.shape} / {s.shape} != {(h, w)}")
        return None
    return p[..., :3].astype(np.float32), s[..., :4].astype(np.float32)


def apply_fades(paint, spec, lay, render_coats=None, size=None):
    """Return (paint_u8 HxWx3, spec_u8 HxWx4) with every fade of ``lay['fade']`` applied. Inputs are never modified in place."""
    if disabled() or cv2 is None:
        return paint, spec
    fades = find_fades(lay)
    if not fades:
        return paint, spec
    from engine.rev_material_layer import _decode_png_rgb, _dest_rect, _fit, _decode_rle
    h, w = spec.shape[:2]
    size = size or lay.get("size") or [w, h]
    paint = paint.copy()
    spec = spec.copy()
    for f in fades:
        try:
            stops = [s for s in (f.get("stops") or []) if isinstance(s, dict)]
            if len(stops) < 1:
                continue
            stops.sort(key=lambda s: float(s.get("p", 0.0)))
            fd = _decode_fields(f, f.get("size") or size, w, h, (_decode_png_rgb, _dest_rect, _fit))
            if fd is None:
                continue
            rect, cov, t = fd
            x0, y0, x1, y1 = rect
            touched = cov > (0.5 / 255.0)
            if not np.any(touched):
                continue
            ws = stop_weights(t, [s.get("p", 0.0) for s in stops])
            paint_on = bool(f.get("paint", True))
            p0 = paint[y0:y1, x0:x1, :3].astype(np.float32)
            s0 = spec[y0:y1, x0:x1, :4].astype(np.float32)
            P = np.zeros_like(p0)
            S = np.zeros_like(s0)
            any_finish = False
            cache = {}
            for st, wi in zip(stops, ws):
                zone = st.get("zone") if isinstance(st.get("zone"), dict) else None
                fin = None
                if zone is not None and render_coats is None:
                    print("  [REV-FADE] finish stop skipped: no nested renderer")
                if zone is not None and render_coats is not None:
                    key = repr(sorted((k, repr(v)[:80]) for k, v in zone.items() if k != "region_mask"))
                    if key not in cache:
                        cache[key] = _render_finish(zone, rect, cov, (h, w), render_coats, _decode_rle)
                    fin = cache[key]
                    any_finish = any_finish or fin is not None
                col = st.get("color")
                if fin is not None:
                    pv = fin[0][y0:y1, x0:x1]
                    sv = fin[1][y0:y1, x0:x1]
                else:
                    pv = np.asarray([float(c) for c in col[:3]], np.float32)[None, None, :] if (isinstance(col, (list, tuple)) and len(col) >= 3) else p0
                    sp = st.get("spec")
                    sv = s0.copy()
                    if isinstance(sp, (list, tuple)) and len(sp) >= 3:
                        sv[..., :3] = np.asarray(floor_spec_triple(sp), np.float32)[None, None, :]
                P += wi[..., None] * pv
                S += wi[..., None] * sv
            c3 = cov[..., None]
            if paint_on:
                np_ = p0 * (1.0 - c3) + P * c3
                pr = paint[y0:y1, x0:x1, :3]
                pr[touched] = np.clip(np.rint(np_[touched]), 0, 255).astype(np.uint8)
            ns = s0 * (1.0 - c3) + S * c3
            if not any_finish:
                ns[..., 3] = s0[..., 3]  # colour / spec stops never touch the specular mask
            ns = _floors(ns, touched)
            sr = spec[y0:y1, x0:x1, :4]
            sr[touched] = np.clip(np.rint(ns[touched]), 0, 255).astype(np.uint8)
        except Exception as e:  # never break a render over an optional layer
            print(f"  [REV-FADE] fade skipped: {e}")
    return paint, spec
