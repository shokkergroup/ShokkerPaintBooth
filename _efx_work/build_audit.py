#!/usr/bin/env python3
"""Audit page for the FOUNDATION category (docs/AUDIT_PAGE_SPEC.md, category key `foundation`).

Two shelves on one page:
  * BASES  — the 20 flat cells. A flat cell has no artwork, so its card shows the booth's
             own live split swatch (paint | spec behaviour) fetched from the running server,
             plus its M/R/Cc cell and the ladder neighbours it must stay distinct from.
  * EFX    — the textured foundations, rendered through their registry paint/spec fns on the
             neutral gray plate at 2048: [full 2048 view | true 1:1 on-car crop | spec at 1:1].

    python _efx_work/build_audit.py            # both shelves
    python _efx_work/build_audit.py --efx-only
"""
from __future__ import annotations
import argparse, contextlib, io, json, logging, os, re, sys, time, urllib.request

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import cv2                                                       # noqa: E402
import numpy as np                                               # noqa: E402
from spb_audit_page_builder import build_page                     # noqa: E402

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CATEGORY = "foundation"
PORT = int(os.environ.get("SHOKKER_PORT", "59876"))
SHAPE = (2048, 2048)
PANEL = 512
THUMBS = os.path.join(ROOT, "thumbnails", "audit", CATEGORY)
REUSE = False


def _js_group(name):
    src = open(os.path.join(ROOT, "paint-booth-0-finish-data.js"), "rb").read().decode("utf-8", "surrogateescape")
    m = re.search(r'^\s*"%s":\s*\[([^\]]*)\]' % re.escape(name), src, re.M)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def _js_bases():
    src = open(os.path.join(ROOT, "paint-booth-0-finish-data.js"), "rb").read().decode("utf-8", "surrogateescape")
    out = {}
    for m in re.finditer(r'\{ id: "([^"]+)", name: "([^"]*)", desc: "([^"]*)"', src):
        out[m.group(1)] = (m.group(2), m.group(3))
    return out


def _cells():
    src = open(os.path.join(ROOT, "engine", "base_registry_data.py"), "rb").read().decode("utf-8", "surrogateescape")
    cells = {}
    for m in re.finditer(r'^\s*"([a-z_]+)":\s*\{[^\n]*?"M":\s*(\d+)[^\n]*?"R":\s*(\d+)[^\n]*?"CC":\s*(\d+)', src, re.M):
        cells.setdefault(m.group(1), (int(m.group(2)), int(m.group(3)), int(m.group(4))))
    return cells


def _fetch_swatch(fid, size=384):
    url = f"http://127.0.0.1:{PORT}/api/swatch/base/{fid}?color=6a8fb5&size={size}&mode=split&prefer=live&v=audit"
    with urllib.request.urlopen(url, timeout=120) as r:
        data = np.frombuffer(r.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def bases_cards(names):
    cells = _cells()
    ids = _js_group("Foundation")
    meta = []
    for fid in ids:
        try:
            img = _fetch_swatch(fid)
        except Exception as ex:                                  # noqa: BLE001
            print("swatch fetch failed", fid, ex)
            img = np.full((384, 768, 3), 40, np.uint8)
        m, r, c = cells.get(fid, (0, 0, 0))
        tile = np.full((img.shape[0] + 26, img.shape[1], 3), 14, np.uint8)
        tile[26:, :] = img
        cv2.putText(tile, f"LIVE SWATCH  paint | spec    cell M/R/Cc = {m}/{r}/{c}", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
        cv2.imwrite(os.path.join(THUMBS, fid + ".png"), tile)
        name, desc = names.get(fid, (fid, ""))
        meta.append({"id": fid, "name": "BASES · " + name, "kind": "finish",
                     "desc": f"{desc}  [cell {m}/{r}/{c}]", "technique": "flat cell"})
        print("base", fid, flush=True)
    return meta


def efx_cards(names):
    logging.disable(logging.CRITICAL)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2 as eng
    ids = _js_group("Foundation EFX")
    mask = np.ones(SHAPE, np.float32)
    meta = []
    for fid in ids:
        e = eng.BASE_REGISTRY.get(fid)
        if not e:
            print("missing in registry", fid)
            continue
        name, desc = names.get(fid, (fid, e.get("desc", "")))
        png = os.path.join(THUMBS, fid + ".png")
        if REUSE and os.path.exists(png):
            meta.append({"id": fid, "name": "EFX · " + name, "kind": "finish", "desc": desc,
                         "technique": "kept as-is" if fid in ("efx_holographic_drift", "efx_frost_fractal", "efx_frost_mercury_duo") else "paint + spec"})
            continue
        t0 = time.time()
        p = e["paint_fn"](np.full(SHAPE + (3,), 0.5, np.float32), SHAPE, mask, 51, 1.0, None)
        _M, _R, _C = e["base_spec_fn"](SHAPE, 51, 1.0, e.get("M", 0), e.get("R", 100))
        dt = time.time() - t0
        p8 = np.clip(np.asarray(p, np.float32)[..., :3] * 255.0, 0, 255).astype(np.uint8)
        s8 = np.clip(np.dstack([_M, _R, _C]), 0, 255).astype(np.uint8)
        c0 = (2048 - PANEL) // 2
        imgs = {"full": cv2.resize(p8, (PANEL, PANEL), interpolation=cv2.INTER_AREA),
                "crop": p8[c0:c0 + PANEL, c0:c0 + PANEL],
                "spec": s8[c0:c0 + PANEL, c0:c0 + PANEL]}
        tile = np.full((PANEL + 26, PANEL * 3 + 16, 3), 14, np.uint8)
        for i, (lab, key) in enumerate((("FULL 2048 VIEW", "full"), ("TRUE 1:1 ON-CAR CROP", "crop"), ("SPEC M/R/Cc (1:1)", "spec"))):
            x0 = i * (PANEL + 8)
            tile[26:26 + PANEL, x0:x0 + PANEL] = imgs[key]
            cv2.putText(tile, lab, (x0 + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
        cv2.imwrite(os.path.join(THUMBS, fid + ".png"), tile[..., ::-1])
        name, desc = names.get(fid, (fid, e.get("desc", "")))
        meta.append({"id": fid, "name": "EFX · " + name, "kind": "finish", "render_s": round(float(dt), 2),
                     "desc": desc, "technique": "kept as-is" if fid in ("efx_holographic_drift", "efx_frost_fractal", "efx_frost_mercury_duo") else "paint + spec"})
        print("efx", fid, "%.2fs" % dt, flush=True)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--efx-only", action="store_true")
    ap.add_argument("--bases-only", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="reuse EFX card PNGs already rendered")
    a = ap.parse_args()
    global REUSE
    REUSE = a.reuse
    os.makedirs(THUMBS, exist_ok=True)
    names = _js_bases()
    meta = []
    if not a.efx_only:
        meta += bases_cards(names)
    if not a.bases_only:
        meta += efx_cards(names)
    title = ('<span class="flag">🏁 FOUNDATION</span> — one category, two shelves '
             '<span style="color:var(--dim);font-weight:400">(BASES flat cells + EFX textured)</span>')
    sub = ("Your brief 2026-09-03: <i>“We have 3 FOUNDATION categories. We should really just have ONE that has "
           "the best of all of them in it and get rid of some that are too similar.”</i> The 30 ★ Enhanced were retired "
           "(their spec had been forced flat since April, so they were the flat cells wearing a premium label). "
           "<b>BASES</b> is now a ladder of flat cells with NO colour of their own — every pair differs by ≥40 M, "
           "≥½ octave of roughness or ≥40 Cc (the rule is fitted to your Living Matte ≈ Matte verdict). "
           "<b>EFX</b> foundations carry their own paint AND spec: rust, gold leaf, holographic flake, hammered, "
           "terrazzo… source paint / solid colour still work on top. Holographic Drift is untouched; Frost Fractal and "
           "Frost Mercury Duo are kept on their original renderers. Rate anything: KEEP · REBUILD · REPLACE · RENAME · REMOVE.")
    out = os.path.join(ROOT, "SPB_AUDIT_%s.html" % CATEGORY)
    build_page(CATEGORY, title, sub, meta, THUMBS, out, accent="#e8c050")
    print("PAGE OK", out, len(meta), "cards")


if __name__ == "__main__":
    main()
