"""[SPB-REV-WEAR 2026-10-10] Race Wear Studio - engine post-pass (lane REV-WEAR, Claude).

The client tool (``js/rev/wear/``) generates a race-worn look in REV-FADE car space (dirt and
tyre spray behind the wheels, bug splats and stone chips on the leading edges, rubber at door
height, brake dust at the arches, dulled clear) and sends it as ONE optional key inside the
existing REV-MATERIAL payload: ``zone["_spb_rev_material"]["wear"]`` =

    {"v": 1, "size": [W, H], "bbox": [x, y, w, h],
     "pv":  PNG (RGB)  wear paint colour,
     "sv":  PNG (RGB)  wear spec  R = metallic, G = roughness, B = clearcoat,
     "aux": PNG (RGB)  R = paint coverage, G = spec coverage, B = dull delta (CC points added to the clear)}

Order (so the render writes exactly what the preview shows):
  1. dulled clear: where the base clear is ON (CC >= 16): CC += dCC, R += 0.35 * dCC (a worn clear is
     both less glossy and a little rougher);
  2. spec  out = base * (1 - sc) + wear * sc, per channel; the clearcoat channel never crosses the
     16 line by blending: when base and wear sit on opposite sides (none 0-15 vs clear 16-255) the
     pixel takes whichever side owns >= 50 % coverage, so a chip edge can't land in 1-15 by accident
     and a dust edge on a matte (no-clear) panel can't flash max gloss (16..40);
  3. roughness floor 15 unless metallic >= 240 (the iron rule; CC is deliberately NOT floored - a
     bare-metal chip or a rubber mark has no clear, that is the point);
  4. paint  out = base * (1 - pc) + wear * pc.

Runs LAST in ``build_multi_zone`` (after material instances, REV-MATERIAL coats/layers and fades),
so wear sits on top of everything incl. decals - exactly like the client layer. No ``wear`` key, or
env ``SPB_REV_WEAR_OFF=1``, returns the inputs untouched (byte-identical; golden net 2026-10-10).
Measured on the ARCA 2048 sheet, endurance 70 laps: see _easy_claude_work/rev_tools/wear/REPORT.md.
"""
import hashlib
import json
import os
import struct
import threading
import time
from collections import OrderedDict

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from engine.rev_material_layer import find_layer, _decode_png_rgb, _dest_rect, _fit

ROUGH_FLOOR = 15
CHROME_M = 240
CC_LINE = 16
DULL_ROUGH = 0.35


def disabled():
    return str(os.environ.get("SPB_REV_WEAR_OFF", "")).strip() not in ("", "0", "false", "False")


def disabled2():
    """[SPB-REV-WEAR2 2026-10-10] kill switch for the by-reference layer store (env SPB_REV_WEAR2_OFF=1: refs are ignored, inline payloads work as before)."""
    return str(os.environ.get("SPB_REV_WEAR2_OFF", "")).strip() not in ("", "0", "false", "False")


# ---------------------------------------------------------------------------------------------------------------------------------
# [SPB-REV-WEAR2 2026-10-10] Layer store: the page uploads each finished wear layer ONCE (binary container, no base64, sent while the
# user looks at the preview); the server decodes it right there (off the render's critical path) and keeps the decoded planes. Every
# later /preview-render and /render then carries only {"rw2": "<key>", "size", "bbox"} (about 150 bytes instead of 4-14 MB), and the pass
# starts from decoded arrays instead of hashing + base64-decoding + PNG-decoding 3 strings. The key is the sha256 (first 40 hex) of the
# container bytes, computed HERE, so a ref can only ever resolve to the exact bytes it names (same idea as PERF-3). Output pixels are
# identical to the inline path by construction (same cv2.imdecode on the same PNG bytes); proof in _easy_claude_work/rev_tools/wear2.
# Container: b"RW2\0" | u32 header_len | header JSON {"v":2,"size":[W,H],"bbox":[x,y,w,h],"res":"full"|"half","n":[len_pv,len_sv,len_aux]} | PNG pv | PNG sv | PNG aux
# ---------------------------------------------------------------------------------------------------------------------------------
MAGIC = b"RW2\x00"
STORE_BUDGET = 320 * 1024 * 1024     # decoded bytes (a full 2048 layer is ~38 MB, its half-res preview copy ~9 MB)
_STORE = OrderedDict()
_STORE_BYTES = [0]
_STORE_LOCK = threading.Lock()
LAST = {}                            # timing of the most recent pass (read by the lane harness / printed in the server log)


def _decode_png_bytes(b):
    """PNG bytes -> HxWx3 uint8 RGB. Same pipeline as rev_material_layer._decode_png_rgb (imdecode COLOR, BGR->RGB), so inline and stored layers are identical."""
    try:
        img = cv2.imdecode(np.frombuffer(b, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return None
    if img is None or img.ndim != 3:
        return None
    return np.ascontiguousarray(img[:, :, ::-1])


def parse_container(buf):
    """-> (header dict, [png_pv, png_sv, png_aux] byte slices). Raises ValueError on anything malformed."""
    mv = memoryview(buf)
    if len(mv) < 12 or bytes(mv[:4]) != MAGIC:
        raise ValueError("not a wear container")
    hl = struct.unpack("<I", bytes(mv[4:8]))[0]
    if hl <= 0 or 8 + hl > len(mv) or hl > 4096:
        raise ValueError("bad header length")
    hdr = json.loads(bytes(mv[8:8 + hl]).decode("utf-8"))
    n = hdr.get("n")
    if hdr.get("v") != 2 or not isinstance(n, list) or len(n) != 3 or any((not isinstance(v, int)) or v <= 0 for v in n):
        raise ValueError("bad header")
    off, out = 8 + hl, []
    for v in n:
        out.append(mv[off:off + v])
        off += v
    if off != len(mv):
        raise ValueError("container length mismatch")
    size, bbox = hdr.get("size"), hdr.get("bbox")
    if not (isinstance(size, list) and len(size) == 2 and isinstance(bbox, list) and len(bbox) == 4):
        raise ValueError("bad size/bbox")
    return hdr, out


def put_layer(buf):
    """Decode + store one uploaded container. Returns (key, entry, was_new). Raises ValueError when it can't be decoded."""
    if cv2 is None:
        raise ValueError("opencv unavailable")
    key = hashlib.sha256(buf).hexdigest()[:40]
    with _STORE_LOCK:
        ent = _STORE.get(key)
        if ent is not None:
            _STORE.move_to_end(key)
            return key, ent, False
    t0 = time.perf_counter()
    hdr, blobs = parse_container(buf)
    pv, sv, aux = (_decode_png_bytes(b) for b in blobs)
    if pv is None or sv is None or aux is None or not (pv.shape == sv.shape == aux.shape):
        raise ValueError("layer PNGs did not decode to matching sizes")
    ent = {"size": hdr["size"], "bbox": hdr["bbox"], "res": hdr.get("res", "full"), "pv": pv, "sv": sv, "aux": aux,
           "nbytes": int(pv.nbytes + sv.nbytes + aux.nbytes), "rs": {}, "ms": round((time.perf_counter() - t0) * 1000, 1), "wire": len(buf)}
    with _STORE_LOCK:
        _STORE[key] = ent
        _STORE_BYTES[0] += ent["nbytes"]
        while len(_STORE) > 1 and _STORE_BYTES[0] > STORE_BUDGET:
            _k, _old = _STORE.popitem(last=False)
            _STORE_BYTES[0] -= _old["nbytes"]
    return key, ent, True


def get_layer(key):
    with _STORE_LOCK:
        ent = _STORE.get(str(key))
        if ent is not None:
            _STORE.move_to_end(str(key))
        return ent


def has_layer(key):
    with _STORE_LOCK:
        return str(key) in _STORE


def store_stats():
    with _STORE_LOCK:
        return {"layers": len(_STORE), "bytes": _STORE_BYTES[0]}


def find_wear(zones):
    lay = find_layer(zones)
    w = lay.get("wear") if isinstance(lay, dict) else None
    if not isinstance(w, dict):
        return None
    return w if (w.get("rw2") or (w.get("pv") and w.get("aux"))) else None


def _resize_premul(val, cov, dw, dh):
    """Resize a colour/value image that is only meaningful where cov > 0 (premultiplied, then divided back)."""
    interp = cv2.INTER_AREA if dw < val.shape[1] else cv2.INTER_LINEAR
    c = cov.astype(np.float32) * (1.0 / 255.0)
    pm = cv2.resize(val.astype(np.float32) * c[..., None], (dw, dh), interpolation=interp)
    cc = cv2.resize(c, (dw, dh), interpolation=interp)
    out = pm / np.maximum(cc, 1e-6)[..., None]
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def apply_wear(paint_rgb, spec_u8, zones):
    """Return (paint_rgb, spec_u8) with the Race Wear layer applied. Inputs are never modified in place."""
    if disabled() or cv2 is None:
        return paint_rgb, spec_u8
    wear = find_wear(zones)
    if wear is None:
        return paint_rgb, spec_u8
    h, w = spec_u8.shape[:2]
    if paint_rgb.dtype != np.uint8 or spec_u8.dtype != np.uint8 or paint_rgb.shape[:2] != (h, w):
        return paint_rgb, spec_u8
    t_pass = time.perf_counter()
    ent = None
    if wear.get("rw2"):
        # [SPB-REV-WEAR2 2026-10-10] by reference: decoded planes already in the store (uploaded while the user looked at the preview)
        ent = None if disabled2() else get_layer(wear.get("rw2"))
        if ent is None:
            print(f"  [REV-WEAR] layer {str(wear.get('rw2'))[:10]}... is not in the store (server restarted or evicted); wear skipped")
            return paint_rgb, spec_u8
        size, bbox = ent["size"], ent["bbox"]
    else:
        size, bbox = wear.get("size") or [w, h], wear.get("bbox") or [0, 0, (wear.get("size") or [w, h])[0], (wear.get("size") or [w, h])[1]]
    rect = _dest_rect(bbox, size, w, h)
    if rect is None:
        return paint_rgb, spec_u8
    x0, y0, x1, y1 = rect
    dw, dh = x1 - x0, y1 - y0
    if ent is not None:
        rsk = (dw, dh)
        got = ent["rs"].get(rsk)
        if got is None:
            pv, sv, aux = ent["pv"], ent["sv"], ent["aux"]
            if aux.shape[:2] != (dh, dw):
                pv = _resize_premul(pv, aux[..., 0], dw, dh)
                sv = _resize_premul(sv, aux[..., 1], dw, dh)
                aux = cv2.resize(aux, (dw, dh), interpolation=cv2.INTER_AREA if dw < aux.shape[1] else cv2.INTER_LINEAR)
                if len(ent["rs"]) < 3:
                    ent["rs"][rsk] = (pv, sv, aux)
            got = (pv, sv, aux)
        pv, sv, aux = got
    else:
        pv, sv, aux = _decode_png_rgb(wear.get("pv")), _decode_png_rgb(wear.get("sv")), _decode_png_rgb(wear.get("aux"))
        if pv is None or aux is None:
            return paint_rgb, spec_u8
        if aux.shape[:2] != (dh, dw):   # preview at a lower resolution: premultiplied resize, so uncovered (0) texels don't darken the edges
            pv = _resize_premul(pv, aux[..., 0], dw, dh)
            if sv is not None:
                sv = _resize_premul(sv, aux[..., 1], dw, dh)
            aux = cv2.resize(aux, (dw, dh), interpolation=cv2.INTER_AREA if dw < aux.shape[1] else cv2.INTER_LINEAR)
    t_dec = time.perf_counter()
    pcu, scu, dcu = cv2.split(np.ascontiguousarray(aux))
    touched = cv2.compare(cv2.max(cv2.max(pcu, scu), dcu), 0, cv2.CMP_GT)
    if not cv2.countNonZero(touched):
        return paint_rgb, spec_u8
    # OpenCV ops on the bbox rect (lane measurement 2026-10-10, ARCA endurance layer, 64 % of the sheet touched, machine at 90 % CPU from other lanes:
    # gather + fancy indexing 1.9 s -> dense numpy float32 1.2 s -> these multithreaded cv2 ops ~0.5 s + PNG decode (cache-hit on render after a preview)).
    # Untouched pixels come out bit-identical: blendLinear with weights (0, 1) returns the base value, the dull delta is 0 there.
    pcf = pcu.astype(np.float32) * (1.0 / 255.0)
    scf = scu.astype(np.float32) * (1.0 / 255.0)
    spec = spec_u8.copy()
    s = spec[y0:y1, x0:x1]
    m0, r0, c0 = np.ascontiguousarray(s[..., 0]), np.ascontiguousarray(s[..., 1]), np.ascontiguousarray(s[..., 2])
    # 1. dulled clear (only where there IS a clear, CC >= 16); a worn clear is a little rougher too
    d = cv2.bitwise_and(dcu, cv2.compare(c0, CC_LINE - 1, cv2.CMP_GT))
    c0 = cv2.add(c0, d)
    r0 = cv2.add(r0, cv2.convertScaleAbs(d, alpha=DULL_ROUGH))
    # 2. spec composite; the clearcoat never crosses the 16 line by blending (>= 50 % coverage owns the side)
    if sv is not None:
        v0, v1, v2 = cv2.split(np.ascontiguousarray(sv))
        inv = 1.0 - scf
        m1, r1, lin = cv2.blendLinear(v0, m0, scf, inv), cv2.blendLinear(v1, r0, scf, inv), cv2.blendLinear(v2, c0, scf, inv)
        cross = cv2.bitwise_xor(cv2.compare(c0, CC_LINE - 1, cv2.CMP_GT), cv2.compare(v2, CC_LINE - 1, cv2.CMP_GT))
        side = np.where(cv2.compare(scu, 127, cv2.CMP_GT) > 0, v2, c0)
        c1 = np.where(cross > 0, side, lin)
    else:
        m1, r1, c1 = m0, r0, c0
    # 3. roughness floor on touched pixels (iron rule); CC left as authored (bare metal / rubber / tape have no clear on purpose)
    fl = cv2.bitwise_and(touched, cv2.compare(m1, CHROME_M, cv2.CMP_LT))
    r1 = np.where(fl > 0, cv2.max(r1, ROUGH_FLOOR), r1)
    s[..., 0] = m1
    s[..., 1] = r1
    s[..., 2] = c1
    # 4. paint composite
    paint = paint_rgb.copy()
    q = paint[y0:y1, x0:x1]
    q[...] = cv2.blendLinear(np.ascontiguousarray(pv), np.ascontiguousarray(q), pcf, 1.0 - pcf)
    t_end = time.perf_counter()
    LAST.update({"ref": ent is not None, "resolve_ms": round((t_dec - t_pass) * 1000, 1), "blend_ms": round((t_end - t_dec) * 1000, 1), "total_ms": round((t_end - t_pass) * 1000, 1), "rect": [x0, y0, x1, y1]})
    print(f"  [REV-WEAR] pass {LAST['total_ms']:.0f} ms (resolve {LAST['resolve_ms']:.0f} ms{' by reference' if ent is not None else ' from the inline payload'}, blend {LAST['blend_ms']:.0f} ms)")
    return paint, spec
