"""[SPB-REV-MATERIAL 2026-10-10] Material Brush / Spec Brush / Wear Brush post-pass.

The client tools in ``js/rev/material/`` send ONE optional field,
``_spb_rev_material``, on a server zone:

    {"v": 1, "size": [W, H],                        # document pixels the crops refer to
     "coats": [{"zone": <server zone dict, region_mask = RLE soft alpha 0..255>}],
     "spec":  {"bbox": [x, y, w, h], "val": "data:image/png;base64,...",   # RGB = M, R, CC
               "cov": "data:image/png;base64,..."},                         # RGB = per-channel coverage
     "paint": {"bbox": [x, y, w, h], "val": "...png...", "cov": "...png..."}}   # paint RGB + coverage (R)

* coats  = Material Brush: each is a real SPB finish. They are rendered by the engine
  itself (one nested ``build_multi_zone`` call in preview mode, hard ownership on the
  brushed area), then composited with the brushed SOFT alpha, so opacity and feathered
  edges are linear: out = engine * (1 - a) + coat * a.
* spec / paint = Spec Brush + Wear Brush layers, painted per pixel on the client and
  composited with per-channel coverage: out = engine * (1 - cov) + val * cov.

Runs after every zone, the iron-rule floors and material instances, and before the
preview return / TGA write, so live preview and RENDER share one code path. Touched
pixels get the iron-rule floors again (CC >= 16; R >= 15 unless M >= 240).
No field, or env ``SPB_REV_MAT_OFF=1``, returns the inputs untouched (byte-identical).
"""
import base64
import hashlib
import math
import os

import numpy as np

try:  # cv2 is a hard dependency elsewhere in the engine; keep the import soft here.
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

CC_FLOOR = 16
ROUGH_FLOOR = 15
CHROME_M = 240

_PNG_CACHE = {}
_PNG_CACHE_MAX = 24


def disabled():
    return str(os.environ.get("SPB_REV_MAT_OFF", "")).strip() not in ("", "0", "false", "False")


# [PERF-3 2026-10-10] Nested coat / fade render memo. Kill switch: env SPB_PERF3_OFF=1.
# Every Material Brush coat set (and every fade finish stop) is rendered by a nested preview-mode
# build_multi_zone call on EVERY preview and render, even when the coats did not change (the
# owner edits another zone, or presses Render right after the preview). Profiled on the QA ARCA
# payload (1 zone + 2 coats): the nested call was 2.1-2.7 s of a 6.2 s preview. Its output is a
# pure function of the source paint CONTENT, seed, car id and the coat zones, so the engine tags
# its render_coats closure with `_perf3_ctx` (content sig "rgb:..." + seed + car id; no tag = no
# memo) and the result is kept here under ctx + a full blake2b of every coat-zone field and mask.
# Same id-to-finish stability assumption as the engine's own zone cache (which already serves
# these nested zones "(cached)"). Hit = fresh copies of the stored arrays; an aborted nested
# render is never stored. Numbers + identity: _easy_claude_work/perf2/PERF3_PROGRESS.md.
# Measured (QA ARCA payload, medians of 5, busy host), coats unchanged: 2-coat preview 9.25 -> 5.76 s,
# 4-coat 12.32 -> 6.47 s; Render 12.25 -> 8.12 s. Preview arrays + render TGA bytes equal ON vs OFF.
# Not done: the first render after a coat edit still pays the nested build (a crop-to-coat-bbox
# nested build would need a crop-invariance proof per finish family).
from collections import OrderedDict as _p3_OrderedDict
import json as _p3_json
import threading as _p3_threading

_P3_RENDER_MEMO = _p3_OrderedDict()
_P3_RENDER_MEMO_BYTES = [0]
_P3_RENDER_MEMO_BUDGET = 256 * 1024 * 1024
_P3_RENDER_MEMO_LOCK = _p3_threading.Lock()


def _p3_off():
    return str(os.environ.get("SPB_PERF3_OFF", "")).strip().lower() in ("1", "true", "yes", "on")


class _P3Unkeyable(Exception):
    pass


def _p3_default(v):
    if isinstance(v, np.ndarray):
        a = np.ascontiguousarray(v)
        return {"__nd__": [list(a.shape), str(a.dtype), hashlib.blake2b(a.tobytes(), digest_size=20).hexdigest()]}
    if isinstance(v, np.generic):
        return {"__np__": [str(v.dtype), repr(v.item())]}
    if isinstance(v, (set, frozenset)):
        raise _P3Unkeyable("set")
    if isinstance(v, (bytes, bytearray)):
        return {"__b__": hashlib.blake2b(bytes(v), digest_size=20).hexdigest()}
    raise _P3Unkeyable(type(v).__name__)


def _p3_zones_key(ctx, zones):
    try:
        text = _p3_json.dumps([list(ctx) if isinstance(ctx, tuple) else ctx, zones], sort_keys=False,
                              default=_p3_default, separators=(",", ":"), allow_nan=True)
    except (_P3Unkeyable, TypeError, ValueError):
        return None
    return hashlib.blake2b(text.encode("utf-8"), digest_size=24).hexdigest()


def _p3_copy_res(res):
    return tuple(np.array(x, copy=True) if isinstance(x, np.ndarray) else x for x in res)


def _p3_memo_render(render_coats):
    ctx = getattr(render_coats, "_perf3_ctx", None)
    if render_coats is None or ctx is None or _p3_off():
        return render_coats
    abort_event = getattr(render_coats, "_perf3_abort", None)

    def _memo_render(zones):
        key = _p3_zones_key(ctx, zones)
        if key is not None:
            with _P3_RENDER_MEMO_LOCK:
                hit = _P3_RENDER_MEMO.get(key)
                if hit is not None:
                    _P3_RENDER_MEMO.move_to_end(key)
            if hit is not None:
                print(f"  [PERF-3] nested coat render memo hit ({len(zones)} zone(s))")
                return _p3_copy_res(hit)
        res = render_coats(zones)
        try:
            if (key is not None and isinstance(res, tuple) and len(res) >= 2
                    and all(isinstance(x, np.ndarray) for x in res[:2])
                    and not (abort_event is not None and abort_event.is_set())):
                stored = _p3_copy_res(res[:2])
                nbytes = sum(x.nbytes for x in stored)
                if nbytes <= _P3_RENDER_MEMO_BUDGET:
                    with _P3_RENDER_MEMO_LOCK:
                        old = _P3_RENDER_MEMO.pop(key, None)
                        if old is not None:
                            _P3_RENDER_MEMO_BYTES[0] -= sum(x.nbytes for x in old)
                        _P3_RENDER_MEMO[key] = stored
                        _P3_RENDER_MEMO_BYTES[0] += nbytes
                        while _P3_RENDER_MEMO and _P3_RENDER_MEMO_BYTES[0] > _P3_RENDER_MEMO_BUDGET:
                            _k, _old = _P3_RENDER_MEMO.popitem(last=False)
                            _P3_RENDER_MEMO_BYTES[0] -= sum(x.nbytes for x in _old)
        except Exception as e:  # a memo must never break a render
            print(f"  [PERF-3] coat memo store skipped: {e}")
        return res

    return _memo_render


def find_layer(zones):
    for z in zones or []:
        if isinstance(z, dict):
            lay = z.get("_spb_rev_material")
            if isinstance(lay, dict):
                return lay
    return None


def _decode_png_rgb(s):
    """data-URL / base64 PNG -> HxWx3 uint8 RGB (cached by content hash)."""
    if not isinstance(s, str) or not s or cv2 is None:
        return None
    key = hashlib.sha1(s.encode("ascii", "ignore")).hexdigest()
    hit = _PNG_CACHE.get(key)
    if hit is not None:
        return hit
    b64 = s.split(",", 1)[1] if s.startswith("data:") else s
    try:
        buf = np.frombuffer(base64.b64decode(b64), dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception:
        return None
    if img is None or img.ndim != 3:
        return None
    img = np.ascontiguousarray(img[:, :, ::-1])
    if len(_PNG_CACHE) >= _PNG_CACHE_MAX:
        _PNG_CACHE.pop(next(iter(_PNG_CACHE)))
    _PNG_CACHE[key] = img
    return img


def _decode_rle(payload):
    """UI RLE mask {width, height, runs:[[value 0..255, len], ...]} -> HxW float32 0..1."""
    if isinstance(payload, str):
        import json
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        return None
    rw, rh = int(payload.get("width", 0)), int(payload.get("height", 0))
    runs = payload.get("runs") or []
    if rw <= 0 or rh <= 0 or rw > 4096 or rh > 4096 or not isinstance(runs, list) or not runs:
        return None
    try:
        arr = np.asarray(runs, dtype=np.float64)
        vals = np.clip(arr[:, 0], 0, 255).astype(np.float32) / 255.0
        lens = arr[:, 1].astype(np.int64)
    except Exception:
        return None
    if np.any(lens <= 0) or int(lens.sum()) != rw * rh:
        return None
    return np.repeat(vals, lens).reshape((rh, rw))


def _dest_rect(bbox, size, w, h):
    try:
        W, H = float(size[0]), float(size[1])
        bx, by, bw, bh = [float(v) for v in bbox]
    except Exception:
        return None
    if W <= 0 or H <= 0 or bw <= 0 or bh <= 0 or not all(math.isfinite(v) for v in (bx, by, bw, bh)):
        return None
    sx, sy = w / W, h / H
    x0, y0 = int(math.floor(bx * sx + 1e-6)), int(math.floor(by * sy + 1e-6))
    x1, y1 = int(math.ceil((bx + bw) * sx - 1e-6)), int(math.ceil((by + bh) * sy - 1e-6))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _fit(arr, dw, dh):
    """Resize a float crop to the destination rect (exact passthrough at 1:1)."""
    if arr.shape[1] == dw and arr.shape[0] == dh:
        return arr
    interp = cv2.INTER_AREA if (dw < arr.shape[1] or dh < arr.shape[0]) else cv2.INTER_LINEAR
    out = cv2.resize(arr, (dw, dh), interpolation=interp)
    if out.ndim == 2 and arr.ndim == 3:
        out = out[:, :, None]
    return out


def _p2_off():
    """[SPB-PERF2 2026-10-10] kill switch for the tight-bbox work below (env SPB_PERF2_OFF=1 = the old full-rect work)."""
    return str(os.environ.get("SPB_PERF2_OFF", "")).strip() not in ("", "0", "false", "False")


def _touched_xy(cov_any):
    """[SPB-PERF2 2026-10-10] coordinates of the "touched" pixels. The old test was ``max(cov.astype(f32) / 255.0) > 0.5/255``: a u8 value k gives
    float32(k)/255 >= 1/255 > 0.5/255 for every k >= 1 and exactly 0 for k = 0, so "touched" == "some channel > 0" (bit-identical, no float pass).
    Every later step of the spec/paint layer is element-wise, so running it on this gather gives the same bytes as on the whole rect; the strokes
    cover a few % of the canvas but their bbox is the whole car, so a bbox crop is no help - the gather costs ~ the stroke area."""
    return np.nonzero(cov_any)


def _floors(spec_f, touched):
    """Iron rules on touched pixels only: CC >= 16, R >= 15 unless chrome (M >= 240)."""
    m, r, cc = spec_f[..., 0], spec_f[..., 1], spec_f[..., 2]
    spec_f[..., 1] = np.where(touched & (m < CHROME_M), np.maximum(r, ROUGH_FLOOR), r)
    spec_f[..., 2] = np.where(touched, np.maximum(cc, CC_FLOOR), cc)
    return spec_f


KEEP_SIGMA = 12.0   # px: structure larger than this is "tone" (dropped), finer is "surface texture" (kept)
KEEP_FLOOR = 2.5    # [SPB-TICKETS-FIX T-2] levels: finish micro-grain finer than this does not move the colour
KEEP_CAP = 2.5      # [SPB-TICKETS-FIX T-2] texture outliers are capped at this x the stroke's own 95th percentile


def _tfix_off(tag):
    """[SPB-TICKETS-FIX 2026-10-10] kill switch: env SPB_TFIX_OFF=1 (all) or SPB_TFIX_<tag>_OFF=1."""
    for k in ("SPB_TFIX_OFF", "SPB_TFIX_%s_OFF" % tag):
        if str(os.environ.get(k, "")).strip() not in ("", "0", "false", "False"):
            return True
    return False


def _lum(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _local_mean(y, m, sigma=KEEP_SIGMA):
    """Normalised convolution: the local mean of ``y`` over the stroke only (pixels where m > 0), so the
    paint outside the stroke never bleeds into the texture at its edge."""
    num = cv2.GaussianBlur((y * m).astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
    den = cv2.GaussianBlur(m.astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
    return num / np.maximum(den, 1e-4)


def keep_colour_paint(main_p, coat_p, src_p, m):
    """Paint of a Keep Colour coat: the colour that is ALREADY on the car (``main_p``) plus only the fine surface
    texture the finish adds, never its hue. All float32 HxWx3 (0..255); ``m`` = float HxW stroke region (0/1).

    texture = high-pass of the finish's luminance minus the part that merely echoes the paint underneath
    (``beta`` x the high-pass of the source paint, fitted over the stroke), added to every channel equally.
    A flat finish (chrome) adds ~nothing, so the colour is kept exactly; a weave / flake / grain finish adds its
    fine light-dark structure on top of the existing colour."""
    yc, ys = _lum(coat_p), _lum(src_p)
    hc, hs = yc - _local_mean(yc, m), ys - _local_mean(ys, m)
    inside = m > 0.5
    den = float(np.sum(hs[inside] ** 2))
    beta = float(np.sum(hc[inside] * hs[inside]) / den) if den > 1e-3 else 0.0
    beta = min(max(beta, 0.0), 1.5)
    added = (hc - beta * hs) * m
    if not _tfix_off("T2") and np.any(inside):
        # [SPB-TICKETS-FIX 2026-10-10 T-2] INTEGRATION-QA: a chrome Keep Colour coat on the real ARCA livery moved the paint by mean 2.25 levels / p95 7 /
        # max 42 (only 19% of the pixels identical; dE76 mean 0.88, p95 2.5, max 18.1). A flat finish was supposed to add ~nothing: chrome's own
        # brushed micro-grain (std 3.5 levels, long tail) was being added as "texture". Two small changes on the texture only (replay of the real
        # server inputs, t14g_variants.py): outliers are capped at KEEP_CAP x the stroke's own 95th percentile, then everything finer than
        # KEEP_FLOOR levels is dropped (soft threshold: a texture of std 7 keeps ~74% of its contrast, std 12 ~84%, std 20 ~90%).
        # Result on the same pixels: mean 0.73 / p95 4 / max 16 levels, 73% identical, dE76 mean 0.28 / p95 1.5 / max 8.9.
        p95 = float(np.percentile(np.abs(added[inside]), 95))
        if p95 > 0.0:
            added = np.clip(added, -KEEP_CAP * p95, KEEP_CAP * p95)
        added = np.sign(added) * np.maximum(np.abs(added) - KEEP_FLOOR, 0.0)
    return np.clip(main_p + added[..., None], 0.0, 255.0)


# [BRUSH-STUDIO 2026-10-10] Brush any finish with its pattern, colour and scale, or its spec only (lane BRUSH-STUDIO,
# _easy_claude_work/rev_tools/brush_studio/PROGRESS.md). A "studio" coat carries {"anchor": "car", "plane": "paint"|"spec",
# "keep_colour": bool, "bs": {finish, params, label}} beside its zone. Unlike a legacy coat (rendered with the stroke as its
# region, so fit/auto-scale/crop-noise follow the stroke and the pattern restarts per stroke), a studio coat's finish is
# rendered ONCE on the FULL canvas (texture_anchor=canvas, render_seed_index from the client), i.e. exactly what a whole-car
# zone with the same slider values renders, and memoised per (source paint, seed, car, zone fields) WITHOUT the mask
# (PERF-3 store): every later stroke of the same finish + params is only a re-composite, and two overlapping strokes cut
# the same car-space texture (seamless). Planes are two independent partitions (the client keeps sum(alpha) <= 255 per plane):
#   paint = paint * (1 - sum a_paint) + sum(coat_paint_k * a_k)      ("Paint + Spec" sends a paint AND a spec coat)
#   spec  = spec  * (1 - sum a_spec)  + sum(coat_spec_k  * a_k)       ("Spec only" = spec coat with keep_colour: the T-2
#   Keep Colour texture is added to the paint; "Paint only" = paint coat: the spec under it stays)
# At alpha 255 the output IS the coat render (zone-match maxdiff proof in the lane PROGRESS). Legacy coats (no "anchor")
# keep the old path byte-identical. Kill switch: env SPB_BRUSH_STUDIO_OFF=1 = studio coats go through the legacy path.
def _bs_off():
    return str(os.environ.get("SPB_BRUSH_STUDIO_OFF", "")).strip() not in ("", "0", "false", "False")


def _bs_is_studio(c):
    return (isinstance(c, dict) and c.get("anchor") == "car" and c.get("plane") in ("paint", "spec")
            and isinstance(c.get("zone"), dict))


def _bs_render_full(raw_render, zz, h, w, local):
    """One full-canvas render of a studio coat zone -> (paint u8 HxWx3+, spec u8 HxWx4), or None.
    `local` dedupes inside one call (a Paint + Spec stroke sends two coats with the same zone); the PERF-3 store keeps it
    across previews / renders when the engine tagged the closure with the source-paint content identity."""
    ctx = getattr(raw_render, "_perf3_ctx", None)
    abort_event = getattr(raw_render, "_perf3_abort", None)
    key = _p3_zones_key(("bs-full-v1", ctx, int(h), int(w)), [zz])
    lk = key if key is not None else id(zz)
    if lk in local:
        return local[lk]
    res = None
    use_memo = key is not None and ctx is not None and not _p3_off()
    if use_memo:
        with _P3_RENDER_MEMO_LOCK:
            res = _P3_RENDER_MEMO.get(key)
            if res is not None:
                _P3_RENDER_MEMO.move_to_end(key)
        if res is not None:
            print("  [BRUSH-STUDIO] coat render memo hit (%s)" % (zz.get("base") or zz.get("finish") or "?"))
    if res is None:
        import time as _bs_time
        _bs_t0 = _bs_time.time()
        z2 = dict(zz)
        z2["region_mask"] = np.ones((h, w), dtype=np.float32)
        z2["hard_edge"] = True
        out = raw_render([z2])
        print("  [BRUSH-STUDIO] coat %s full-canvas %dx%d render %.2fs (memo %s)" % (
            zz.get("base") or zz.get("finish") or "?", w, h, _bs_time.time() - _bs_t0, "store" if use_memo else "off"))
        if not isinstance(out, tuple) or len(out) < 2:
            local[lk] = None
            return None
        cp, cs = np.asarray(out[0]), np.asarray(out[1])
        if cp.shape[:2] != (h, w) or cs.shape[:2] != (h, w):
            local[lk] = None
            return None
        res = (cp, cs)
        if use_memo and not (abort_event is not None and abort_event.is_set()):
            try:
                stored = _p3_copy_res(res)
                nbytes = sum(x.nbytes for x in stored)
                if nbytes <= _P3_RENDER_MEMO_BUDGET:
                    with _P3_RENDER_MEMO_LOCK:
                        old = _P3_RENDER_MEMO.pop(key, None)
                        if old is not None:
                            _P3_RENDER_MEMO_BYTES[0] -= sum(x.nbytes for x in old)
                        _P3_RENDER_MEMO[key] = stored
                        _P3_RENDER_MEMO_BYTES[0] += nbytes
                        while _P3_RENDER_MEMO and _P3_RENDER_MEMO_BYTES[0] > _P3_RENDER_MEMO_BUDGET:
                            _k, _old = _P3_RENDER_MEMO.popitem(last=False)
                            _P3_RENDER_MEMO_BYTES[0] -= sum(x.nbytes for x in _old)
                    res = stored
            except Exception as e:  # a memo must never break a render
                print(f"  [BRUSH-STUDIO] coat memo store skipped: {e}")
    local[lk] = res
    return res


def _composite_studio(paint, spec, coats, raw_render, source_paint=None):
    if not coats or raw_render is None:
        return paint, spec
    h, w = spec.shape[:2]
    items = []
    for c in coats:
        z = c["zone"]
        a = _decode_rle(z.get("region_mask"))
        if a is None or not np.any(a > 0):
            continue
        if a.shape != (h, w):
            a = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA if a.shape[1] > w else cv2.INTER_LINEAR)
        a = np.clip(a, 0.0, 1.0).astype(np.float32)
        zz = {k: v for k, v in z.items() if k not in ("region_mask", "_spb_rev_material")}
        zz["texture_anchor"] = "canvas"
        zz["name"] = "Brush Studio coat"   # the name never changes pixels; one render serves the paint AND the spec coat
        items.append([c["plane"], bool(c.get("keep_colour")), a, zz, None])
    if not items:
        return paint, spec
    any_a = None
    for it in items:
        any_a = (it[2] > 0) if any_a is None else (any_a | (it[2] > 0))
    ys, xs = np.nonzero(any_a)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    local = {}
    for it in items:
        it[4] = _bs_render_full(raw_render, it[3], h, w, local)
    items = [it for it in items if it[4] is not None]
    if not items:
        return paint, spec
    P = paint[y0:y1, x0:x1, :3].astype(np.float32)
    S = spec[y0:y1, x0:x1, :4].astype(np.float32)
    shp = (y1 - y0, x1 - x0)
    sum_p, acc_p = np.zeros(shp, np.float32), np.zeros(shp + (3,), np.float32)
    sum_s, acc_s = np.zeros(shp, np.float32), np.zeros(shp + (4,), np.float32)
    for plane, keep, a, zz, (cp, cs) in items:
        ac = a[y0:y1, x0:x1]
        if plane == "paint":
            sum_p += ac
            acc_p += cp[y0:y1, x0:x1, :3].astype(np.float32) * ac[..., None]
        else:
            sum_s += ac
            acc_s += cs[y0:y1, x0:x1, :4].astype(np.float32) * ac[..., None]
    for sm, acc in ((sum_p, acc_p), (sum_s, acc_s)):   # the client keeps each plane <= 255; guard resampling overshoot
        over = sm > 1.0
        if np.any(over):
            acc[over] /= sm[over][:, None]
            sm[over] = 1.0
    Pn = P * (1.0 - sum_p)[..., None] + acc_p
    Sn = S * (1.0 - sum_s)[..., None] + acc_s
    touched_p = sum_p > 0
    keeps = [it for it in items if it[0] == "spec" and it[1]]
    if keeps:
        try:
            src = source_paint() if callable(source_paint) else source_paint
            src = np.asarray(src) if src is not None else None
            src_c = (src[y0:y1, x0:x1, :3].astype(np.float32) if (src is not None and src.shape[:2] == (h, w)) else P)
            for plane, keep, a, zz, (cp, cs) in keeps:
                ac = a[y0:y1, x0:x1]
                region = (ac > (0.5 / 255.0)).astype(np.float32)
                tex = keep_colour_paint(Pn, cp[y0:y1, x0:x1, :3].astype(np.float32), src_c, region) - Pn
                Pn = Pn + tex * ac[..., None]
                touched_p |= ac > 0
        except Exception as e:  # never break a render over an optional blend
            print(f"  [BRUSH-STUDIO] keep colour texture skipped: {e}")
    touched_s = sum_s > 0
    Sn = _floors(Sn, touched_s)
    paint = paint.copy()
    spec = spec.copy()
    pr = paint[y0:y1, x0:x1, :3]
    sr = spec[y0:y1, x0:x1, :4]
    pr[touched_p] = np.clip(np.rint(Pn[touched_p]), 0, 255).astype(np.uint8)
    sr[touched_s] = np.clip(np.rint(Sn[touched_s]), 0, 255).astype(np.uint8)
    return paint, spec


def _composite_coats(paint, spec, lay, render_coats, source_paint=None, raw_render=None):
    coats = lay.get("coats")
    if not isinstance(coats, list) or not coats or render_coats is None:
        return paint, spec
    if not _bs_off() and any(_bs_is_studio(c) for c in coats):
        # [BRUSH-STUDIO 2026-10-10] legacy coats first (old path, same maths), studio coats composite on top
        legacy = [c for c in coats if not _bs_is_studio(c)]
        studio = [c for c in coats if _bs_is_studio(c)]
        if legacy:
            paint, spec = _composite_coats(paint, spec, dict(lay, coats=legacy), render_coats, source_paint)
        return _composite_studio(paint, spec, studio, raw_render if raw_render is not None else render_coats, source_paint)
    h, w = spec.shape[:2]
    zones, alpha = [], None
    keep_num, a_sum = None, None   # Keep Colour: sum of the keep coats' alpha / sum of all coats' alpha
    for c in coats:
        z = c.get("zone") if isinstance(c, dict) else None
        if not isinstance(z, dict):
            continue
        a = _decode_rle(z.get("region_mask"))
        if a is None or not np.any(a > 0):
            continue
        if a.shape != (h, w):
            a = cv2.resize(a, (w, h), interpolation=cv2.INTER_AREA if a.shape[1] > w else cv2.INTER_LINEAR)
        a = np.clip(a, 0.0, 1.0).astype(np.float32)
        zz = {k: v for k, v in z.items() if k not in ("region_mask", "_spb_rev_material")}
        zz["region_mask"] = (a > (0.5 / 255.0)).astype(np.float32)
        zz["hard_edge"] = True
        zones.append(zz)
        alpha = a if alpha is None else (1.0 - (1.0 - alpha) * (1.0 - a))
        a_sum = a.copy() if a_sum is None else a_sum + a
        if c.get("keep_colour"):
            keep_num = a.copy() if keep_num is None else keep_num + a
    if not zones or alpha is None:
        return paint, spec
    res = render_coats(zones)
    if not isinstance(res, tuple) or len(res) < 2:
        return paint, spec
    c_paint, c_spec = np.asarray(res[0]), np.asarray(res[1])
    if c_paint.shape[:2] != (h, w) or c_spec.shape[:2] != (h, w):
        return paint, spec
    ys, xs = np.nonzero(alpha > 0)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    a3 = alpha[y0:y1, x0:x1, None]
    touched = a3[..., 0] > 0
    p = paint[y0:y1, x0:x1, :3].astype(np.float32)
    c_p = c_paint[y0:y1, x0:x1, :3].astype(np.float32)
    if keep_num is not None and np.any(keep_num[y0:y1, x0:x1] > 0):
        # [REV-MATERIAL-2 2026-10-10] Keep Colour: spec + fine surface texture from the finish, colour from the car
        try:
            src = source_paint() if callable(source_paint) else source_paint
            src = np.asarray(src) if src is not None else None
            src_c = (src[y0:y1, x0:x1, :3].astype(np.float32) if (src is not None and src.shape[:2] == (h, w)) else p)
            region = (alpha[y0:y1, x0:x1] > (0.5 / 255.0)).astype(np.float32)
            kw = (keep_num[y0:y1, x0:x1] / np.maximum(a_sum[y0:y1, x0:x1], 1e-6))[..., None]
            c_p = c_p * (1.0 - kw) + keep_colour_paint(p, c_p, src_c, region) * kw
        except Exception as e:  # never break a render over an optional blend
            print(f"  [REV-MATERIAL] keep colour skipped: {e}")
    p = p * (1.0 - a3) + c_p * a3
    s = spec[y0:y1, x0:x1, :4].astype(np.float32)
    s = s * (1.0 - a3) + c_spec[y0:y1, x0:x1, :4].astype(np.float32) * a3
    s = _floors(s, touched)
    paint = paint.copy()
    spec = spec.copy()
    pr = paint[y0:y1, x0:x1, :3]
    sr = spec[y0:y1, x0:x1, :4]
    pr[touched] = np.clip(np.rint(p[touched]), 0, 255).astype(np.uint8)
    sr[touched] = np.clip(np.rint(s[touched]), 0, 255).astype(np.uint8)
    return paint, spec


def _composite_spec(spec, part, size):
    if not isinstance(part, dict):
        return spec
    h, w = spec.shape[:2]
    rect = _dest_rect(part.get("bbox"), size, w, h)
    val, cov = _decode_png_rgb(part.get("val")), _decode_png_rgb(part.get("cov"))
    if rect is None or val is None or cov is None or val.shape != cov.shape:
        return spec
    x0, y0, x1, y1 = rect
    dw, dh = x1 - x0, y1 - y0
    if not _p2_off() and cov.shape[1] == dw and cov.shape[0] == dh and val.shape == cov.shape:
        # [SPB-PERF2 2026-10-10] 1:1 crop (the normal case): the same maths on the touched pixels only (byte-identical, T-1)
        ys, xs = _touched_xy(cov.any(axis=2))
        if ys.size == 0:
            return spec
        cs = cov[ys, xs].astype(np.float32) / 255.0
        vs = val[ys, xs].astype(np.float32) * cs
        vs = np.where(cs > 1e-6, vs / np.maximum(cs, 1e-6), 0.0)
        gy, gx = ys + y0, xs + x0
        ss = spec[gy, gx, :3].astype(np.float32)
        ss = ss * (1.0 - cs) + vs * cs
        ss = _floors(ss, np.ones(ss.shape[0], dtype=bool))
        spec = spec.copy()
        spec[gy, gx, :3] = np.clip(np.rint(ss), 0, 255).astype(np.uint8)
        return spec
    c = cov.astype(np.float32) / 255.0
    v = _fit(val.astype(np.float32) * c, dw, dh)
    c = _fit(c, dw, dh)
    v = np.where(c > 1e-6, v / np.maximum(c, 1e-6), 0.0)
    touched = np.max(c, axis=2) > (0.5 / 255.0)
    if not np.any(touched):
        return spec
    s = spec[y0:y1, x0:x1, :3].astype(np.float32)
    s = s * (1.0 - c) + v * c
    s = _floors(s, touched)
    spec = spec.copy()
    sr = spec[y0:y1, x0:x1, :3]
    sr[touched] = np.clip(np.rint(s[touched]), 0, 255).astype(np.uint8)
    return spec


def _composite_paint(paint, part, size):
    if not isinstance(part, dict):
        return paint
    h, w = paint.shape[:2]
    rect = _dest_rect(part.get("bbox"), size, w, h)
    val, cov = _decode_png_rgb(part.get("val")), _decode_png_rgb(part.get("cov"))
    if rect is None or val is None or cov is None or val.shape[:2] != cov.shape[:2]:
        return paint
    x0, y0, x1, y1 = rect
    dw, dh = x1 - x0, y1 - y0
    if not _p2_off() and cov.shape[1] == dw and cov.shape[0] == dh and val.shape[:2] == cov.shape[:2]:
        # [SPB-PERF2 2026-10-10] 1:1 crop: the same maths on the touched pixels only (byte-identical, T-1)
        ys, xs = _touched_xy(cov[:, :, 0] > 0)
        if ys.size == 0:
            return paint
        cs = cov[ys, xs, :1].astype(np.float32) / 255.0
        vs = val[ys, xs].astype(np.float32) * cs
        vs = np.where(cs > 1e-6, vs / np.maximum(cs, 1e-6), 0.0)
        gy, gx = ys + y0, xs + x0
        ps = paint[gy, gx, :3].astype(np.float32)
        ps = ps * (1.0 - cs) + vs * cs
        paint = paint.copy()
        paint[gy, gx, :3] = np.clip(np.rint(ps), 0, 255).astype(np.uint8)
        return paint
    c = cov[:, :, :1].astype(np.float32) / 255.0
    v = _fit(val.astype(np.float32) * c, dw, dh)
    c = _fit(c, dw, dh)
    if c.ndim == 2:
        c = c[:, :, None]
    v = np.where(c > 1e-6, v / np.maximum(c, 1e-6), 0.0)
    touched = c[..., 0] > (0.5 / 255.0)
    if not np.any(touched):
        return paint
    p = paint[y0:y1, x0:x1, :3].astype(np.float32)
    p = p * (1.0 - c) + v * c
    paint = paint.copy()
    pr = paint[y0:y1, x0:x1, :3]
    pr[touched] = np.clip(np.rint(p[touched]), 0, 255).astype(np.uint8)
    return paint


def apply_rev_material_layers(paint_rgb, spec_u8, zones, render_coats=None, source_paint=None):
    """Return (paint_rgb, spec_u8) with the brushed material layers applied.

    ``render_coats(zone_list) -> (paint_u8, spec_u8)`` renders Material Brush coats
    with the real engine at the same resolution (the caller passes a closure over
    ``build_multi_zone`` in preview mode). ``source_paint`` (array or zero-arg callable, optional) is the
    untouched source paint, only read for Keep Colour coats. Inputs are never modified in place.
    """
    if disabled() or cv2 is None:
        return paint_rgb, spec_u8
    lay = find_layer(zones)
    if lay is None:
        return paint_rgb, spec_u8
    h, w = spec_u8.shape[:2]
    if paint_rgb.dtype != np.uint8 or spec_u8.dtype != np.uint8 or paint_rgb.shape[:2] != (h, w):
        return paint_rgb, spec_u8
    size = lay.get("size") or [w, h]
    raw_render = render_coats   # [BRUSH-STUDIO 2026-10-10] studio coats memo per zone WITHOUT the mask (needs the tagged raw closure)
    try:
        render_coats = _p3_memo_render(render_coats)   # [PERF-3 2026-10-10] coats + fade stops share it
    except Exception as e:
        print(f"  [PERF-3] coat memo skipped: {e}")
    try:
        paint_rgb, spec_u8 = _composite_coats(paint_rgb, spec_u8, lay, render_coats, source_paint, raw_render=raw_render)
    except Exception as e:  # never break a render over an optional layer
        print(f"  [REV-MATERIAL] coats skipped: {e}")
    try:
        spec_u8 = _composite_spec(spec_u8, lay.get("spec"), size)
    except Exception as e:
        print(f"  [REV-MATERIAL] spec layer skipped: {e}")
    try:
        paint_rgb = _composite_paint(paint_rgb, lay.get("paint"), size)
    except Exception as e:
        print(f"  [REV-MATERIAL] paint layer skipped: {e}")
    # [SPB-REV-FADE 2026-10-10] Car-Space Fade post-pass: fades ride in the same payload (lay["fade"]) and run LAST, so a fade's colour and spec
    # replace what is under it exactly as the preview overlay shows. Own kill switch SPB_REV_FADE_OFF (checked inside). Additive: no "fade" key = no-op.
    if lay.get("fade"):
        try:
            from engine.rev_fade_layer import apply_fades as _apply_fades
            paint_rgb, spec_u8 = _apply_fades(paint_rgb, spec_u8, lay, render_coats, size)
        except Exception as e:  # never break a render over an optional layer
            print(f"  [REV-FADE] fades skipped: {e}")
    return paint_rgb, spec_u8
