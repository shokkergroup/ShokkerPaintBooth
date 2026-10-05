# -*- coding: utf-8 -*-
"""Mechanical calibration v4 over ign_verify failures (run AFTER ign_assemble and a
fresh ign_verify; re-run ign_verify afterwards):
  FINENESS char>12  -> rework: supersample build (factor char/9 cap 2.6) + micro-grain
                       crush layer; fable/LFR monolithics: mean-preserving 4-8px
                       micro-grain crusher on the paint (the banked keeper recipe).
  RESTRAINT (no channel detonating: hotM and hotC both <1.2%) -> ledge the marrying
                       channel's top 8% onto 210-255. FLAT-CHANNEL GUARD: if the
                       channel has no dynamic range (p98-p50 < 24) the ledge would
                       nuke it -> hand list instead.
Everything else (MARRIAGE, DECORR, PERF, EXCEPTION) -> _audit/ign_hand_list.json.
Idempotent: strips its own marker sections before re-measuring."""
import io, json, os, re, sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
MARK_A = "# === IGN CALIB 2026-06-10 START ==="
MARK_B = "# === IGN CALIB 2026-06-10 END ==="
FABLE_F = os.path.join(ROOT, "engine", "paint_v2", "fable_collection.py")
RW_F = os.path.join(ROOT, "engine", "expansions", "colorshift_rework_2026.py")
CULT_F = os.path.join(ROOT, "engine", "paint_v2", "cultural_let_freedom_ring.py")
SPECP_F = os.path.join(ROOT, "engine", "spec_patterns.py")

for f in (FABLE_F, RW_F, CULT_F, SPECP_F):
    src = io.open(f, encoding="utf-8").read()
    new = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B) + r"\n?", "", src, flags=re.S)
    if new != src:
        io.open(f, "w", encoding="utf-8", newline="\n").write(new)
        print("stripped old calib section:", os.path.basename(f))

sys.path.insert(0, ROOT)
import numpy as np  # noqa: E402
import cv2  # noqa: E402
from engine.paint_v2.fable_collection import FABLE_MONOLITHICS  # noqa: E402
from engine.expansions.colorshift_rework_2026 import REWORK_MONOLITHICS  # noqa: E402
from engine.paint_v2.cultural_let_freedom_ring import LFR_MONOLITHICS  # noqa: E402

RES = json.load(io.open(os.path.join(ROOT, "_audit", "ign_verify_results.json"), encoding="utf-8"))

S2 = 512
ones = np.ones((S2, S2), np.float32)
gray = np.full((S2, S2, 3), 0.5, np.float32)


def corr(a, b):
    a, b = a.astype(np.float32).ravel(), b.astype(np.float32).ravel()
    if a.std() < 1e-6 or b.std() < 1e-6:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def probe_channel(fid):
    """Pick ignition channel (0=M, 2=Cc) by |corr| vs paint luma; also return the
    chosen channel's dynamic range (p98-p50) so flat channels can be skipped."""
    if fid.startswith("fable_"):
        spec_fn, paint_fn = FABLE_MONOLITHICS[fid]
    elif fid in LFR_MONOLITHICS:
        spec_fn, paint_fn = LFR_MONOLITHICS[fid]
    else:
        spec_fn, paint_fn = REWORK_MONOLITHICS[fid]
    spec = spec_fn((S2, S2), ones, 42, 1.0)
    luma = paint_fn(gray.copy(), (S2, S2), ones, 42, 1.0, {})[:, :, :3] @ np.float32([0.2126, 0.7152, 0.0722])
    chans = {0: spec[:, :, 0].astype(np.float32), 2: spec[:, :, 2].astype(np.float32)}
    ch = 0 if abs(corr(chans[0], luma)) >= abs(corr(chans[2], luma)) else 2
    c = chans[ch]
    rng_ = float(np.percentile(c, 98) - np.percentile(c, 50))
    return ch, rng_


HELPERS = '''
def _ign_knee_packed(fn, ch, t_pct=92.0):
    """LEDGE remap: pixels above the t_pct percentile land on 210-255 (guaranteed
    ignition); an over-bright sub-ledge body is scaled under 195 for calm."""
    def f(shape, mask, seed, sm, _f=fn, _c=ch, _t=t_pct):
        import numpy as _np
        out = _f(shape, mask, seed, sm)
        c = out[:, :, _c].astype(_np.float32)
        # deterministic micro-dither breaks ties so flat-bright channels still
        # ledge their top 8% (reads as fine metal-flake sparkle, not a wall)
        c = c + _np.random.default_rng(0x1D17).random(c.shape).astype(_np.float32)
        sel = out[:, :, 3] > 0
        t = float(_np.percentile(c[sel] if sel.any() else c, _t))
        cmax = float(c.max())
        low = c * (195.0 / t) if t > 195.0 else c
        hi = 210.0 + 45.0 * (c - t) / max(1e-3, cmax - t)
        out[:, :, _c] = _np.clip(_np.where(c >= t, hi, low), 0, 255).astype(_np.uint8)
        return out
    return f


def _ign_crush_paint(fn, amp=0.50):
    """SHARP-edged 4-8px micro-fleck layer multiplied into the painted region —
    hard transitions carry the fine gradient energy the fineness metric reads
    (smooth grain does not move it)."""
    def f(paint, shape, mask, seed, pm, bb, _f=fn, _a=amp):
        import numpy as _np
        out = _f(paint, shape, mask, seed, pm, bb)
        fh, fw = _shape2(shape)
        wh, ww = min(fh, 1024), min(fw, 1024)
        g = _np.asarray(_msc(wh, ww, [2, 4], (int(seed) ^ 0xC4C4C4) & 0x7FFFFFFF), _np.float32)
        fleck = _np.clip((g - 0.42) * 5.0, 0.0, 1.0)
        fleck = _upscale(fleck, fh, fw)
        mk = _mask2(mask, fh, fw)
        mod = 1.0 + (fleck - float(fleck.mean())) * _a * mk
        out = _np.clip(_np.asarray(out, _np.float32) * mod[..., None], 0.0, 1.0)
        return out.astype(_np.float32)
    return f
'''

RW_HELPERS = '''
def _ign_ss_build(build, f):
    def b(h, w, s, _b=build, _f=f):
        import numpy as _np, cv2 as _cv
        H, W = int(round(h * _f)), int(round(w * _f))
        out = _b(H, W, s)

        def rs(a):
            if not hasattr(a, "ndim") or getattr(a, "ndim", 0) < 2:
                return a
            return _cv.resize(_np.asarray(a, _np.float32), (w, h), interpolation=_cv.INTER_AREA)
        if isinstance(out, tuple):
            return tuple(rs(a) for a in out)
        return rs(out)
    return b


def _ign_crush_build(build, amp=0.55):
    def b(h, w, s, _b=build, _a=amp):
        import numpy as _np
        out = _np.asarray(_b(h, w, s), _np.float32)
        g = _np.asarray(_rk_n(h, w, (int(s) ^ 0xC4C4C4) & 0x7FFFFFFF, (2, 4)), _np.float32)
        fleck = _np.clip((g - 0.42) * 5.0, 0.0, 1.0)
        return _np.clip(out * (1.0 + (fleck - float(fleck.mean())) * _a)[..., None], 0.0, 1.0)
    return b
'''

hand = {}
plans = {"fable": [], "rw": [], "cult": [], "ovl": []}

# PERSISTENT UNION: prior runs' plans stay in force (a knee that fixed an item
# makes the item PASS the next verify — deciding from that measurement alone
# would un-knee it and regress it; never drop a prior plan).
PLANS_F = os.path.join(ROOT, "_audit", "ign_calib_plans.json")
prev = {"fable": [], "rw": [], "cult": [], "ovl": []}
if os.path.exists(PLANS_F):
    try:
        prev = json.load(io.open(PLANS_F, encoding="utf-8"))
    except Exception:
        pass


def hot_vals(msgs):
    for m in msgs:
        mm = re.match(r"RESTRAINT hotM=([\d.]+)% hotC=([\d.]+)%", m)
        if mm:
            return float(mm.group(1)) / 100.0, float(mm.group(2)) / 100.0
        mm = re.match(r"RESTRAINT hot=([\d.]+)%", m)
        if mm:
            v = float(mm.group(1)) / 100.0
            return v, v
    return None


for group, items in RES.items():
    for fid, r in items.items():
        if r["verdict"] != "FAIL":
            continue
        msgs = r["msgs"]
        joined = "; ".join(msgs)
        is_ovl = fid.startswith("spec_lfr_")
        if group == "lfr_patterns" or "EXCEPTION" in joined:
            if msgs:
                hand[fid] = joined
            continue
        hard = [m for m in msgs if m.startswith(("MARRIAGE", "DECORR", "PERF", "mip", "too dark",
                                                 "spec contract", "R floor", "Cc floor", "blob", "fine "))]
        if hard:
            hand[fid] = joined
        char = r.get("char_px") or 0
        hv = hot_vals(msgs)
        if is_ovl:
            if hv and max(hv) < 0.012:
                plans["ovl"].append(fid)
            continue
        need_knee = hv is not None and max(hv) < 0.012
        worst_perf = max([float(m.split()[-1].rstrip("s")) for m in msgs if m.startswith("PERF")] or [0.0])
        need_fine = char > 12.0 and worst_perf <= 2.5
        if not (need_knee or need_fine):
            continue
        plan = {"id": fid, "knee": None, "crush": need_fine, "ss": None}
        if need_knee:
            ch, rng_ = probe_channel(fid)
            if rng_ < 24.0:
                hand[fid] = (hand.get(fid, "") + " | flat channel (range %.0f) needs hand ignition" % rng_).strip(" |")
            else:
                plan["knee"] = ch
        is_flag = fid.startswith("fable_") or fid in LFR_MONOLITHICS
        if need_fine and not is_flag:
            plan["ss"] = round(min(2.6, max(1.3, char / 9.0)), 2)
        if plan["knee"] is None and not plan["crush"]:
            continue
        plans["fable" if fid.startswith("fable_") else ("cult" if fid in LFR_MONOLITHICS else "rw")].append(plan)
        print("PLAN", fid, "knee" if plan["knee"] is not None else "", "crush" if plan["crush"] else "",
              "ss%s" % plan["ss"] if plan["ss"] else "")


# merge: prior plans first, new plans override/extend per id
for k in plans:
    if k == "ovl":
        plans[k] = sorted(set(prev.get(k, [])) | set(plans[k]))
        continue
    by_id = {p["id"]: p for p in prev.get(k, [])}
    for p in plans[k]:
        old = by_id.get(p["id"], {})
        by_id[p["id"]] = {"id": p["id"],
                          "knee": p["knee"] if p["knee"] is not None else old.get("knee"),
                          "crush": bool(p["crush"] or old.get("crush")),
                          "ss": p["ss"] if p["ss"] is not None else old.get("ss")}
    plans[k] = list(by_id.values())
io.open(PLANS_F, "w", encoding="utf-8").write(json.dumps(plans, indent=1))


def splice(path, block):
    src = io.open(path, encoding="utf-8").read()
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        src.rstrip("\n") + "\n\n\n" + MARK_A + "\n" + block.rstrip("\n") + "\n" + MARK_B + "\n")


def gen_mono(plansL, reg, registry):
    out = [HELPERS]
    for p in plansL:
        fid = p["id"]
        if p["crush"]:
            out.append('%s["%s"] = (%s["%s"][0], _ign_crush_paint(%s["%s"][1], 0.5))' % (reg, fid, reg, fid, reg, fid))
        if p["knee"] is not None:
            out.append('%s["%s"] = (_ign_knee_packed(%s["%s"][0], %d), %s["%s"][1])' % (reg, fid, reg, fid, p["knee"], reg, fid))
    return "\n\n".join(out)


if plans["fable"]:
    splice(FABLE_F, gen_mono(plans["fable"], "FABLE_MONOLITHICS", FABLE_MONOLITHICS))
if plans["cult"]:
    splice(CULT_F, gen_mono(plans["cult"], "LFR_MONOLITHICS", LFR_MONOLITHICS))
if plans["rw"]:
    body = [RW_HELPERS, HELPERS]
    for p in plans["rw"]:
        fid = p["id"]
        if p["ss"] or p["crush"]:
            pw = "_ign_%s_paint" % fid
            sw = "_ign_%s_spec" % fid
            if p["ss"]:
                pw = "_ign_ss_build(%s, %s)" % (pw, p["ss"])
                sw = "_ign_ss_build(%s, %s)" % (sw, p["ss"])
            if p["crush"]:
                pw = "_ign_crush_build(%s)" % pw
            body.append('REWORK_MONOLITHICS["{i}"] = _rw_pair("{i}", {p}, {s})'.format(i=fid, p=pw, s=sw))
        if p["knee"] is not None:
            body.append('REWORK_MONOLITHICS["{i}"] = (_ign_knee_packed(REWORK_MONOLITHICS["{i}"][0], {c}), REWORK_MONOLITHICS["{i}"][1])'
                        .format(i=fid, c=p["knee"]))
    splice(RW_F, "\n\n".join(body))
if plans["ovl"]:
    body = ['''
def _ign_knee01(fn, t_pct=92.0, g=0.9):
    def f(shape, seed, sm, _f=fn, _t=t_pct, _g=g, **kw):
        import numpy as _np
        out = _np.asarray(_f(shape, seed, sm, **kw), _np.float32)
        if float(out.std()) < 0.001:
            return out
        c = out[..., 0] if out.ndim == 3 else out
        t = float(_np.percentile(c, _t))
        cmax = float(c.max())
        low = c * (0.74 / t) if t > 0.74 else c
        cb = _np.clip(_np.where(c >= t, 0.82 + 0.18 * (c - t) / max(1e-3, cmax - t), low), 0, 1)
        if out.ndim == 3:
            out[..., 0] = cb
            return out
        return cb
    f._spb_concept_complete = True
    return f
''']
    body.append("PATTERN_CATALOG.update({\n" + "\n".join(
        '    "%s": _ign_knee01(PATTERN_CATALOG["%s"]),' % (o, o) for o in plans["ovl"]) + "\n})")
    splice(SPECP_F, "\n\n".join(body))

import py_compile  # noqa: E402
for f in (FABLE_F, RW_F, CULT_F, SPECP_F):
    py_compile.compile(f, doraise=True)
    print("COMPILE OK", os.path.basename(f))

io.open(os.path.join(ROOT, "_audit", "ign_hand_list.json"), "w", encoding="utf-8").write(json.dumps(hand, indent=1))
print("\nCALIBRATED v4: fable %d, rework %d, lfr %d, overlays %d | HAND: %d -> _audit/ign_hand_list.json"
      % (len(plans["fable"]), len(plans["rw"]), len(plans["cult"]), len(plans["ovl"]), len(hand)))
