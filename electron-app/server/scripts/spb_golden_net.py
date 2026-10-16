# -*- coding: utf-8 -*-
"""spb_golden_net.py -- the golden-image regression net (owner go, 2026-09-05).

Turns "I hope I didn't change any finish" into a test. Renders a PINNED manifest of finish
ids by calling their registered paint_fn / spec_fn / base_spec_fn / texture_fn directly
(the same convention as scripts/spb_finish_law.py: 512x512, seed 51, scale 1.0, float32
ones mask, 0.5-grey base) and records a SHA-256 of the canonical float32 bytes of every
output channel plus the resolved function identity (module.qualname). It boots the engine
exactly the way the live server does (import shokker_engine_v2, then the lazy expansion
load) and hashes from the LEGACY dicts, which is what the app renders from.

    python scripts/spb_golden_net.py --bake            # first bake / re-bake missing ids
    python scripts/spb_golden_net.py                   # --check (default): exit 1 on any CHANGED/REMOVED/ERROR
    python scripts/spb_golden_net.py --check --ids a,b # check a subset
    python scripts/spb_golden_net.py --accept a,b --reason "declared rebuild"     # re-bake after a DECLARED change
    python scripts/spb_golden_net.py --accept xlab_hologram_metal --owner-approved --reason "..."   # protected ids refuse otherwise
    python scripts/spb_golden_net.py --add id1,id2     # pin more ids into the manifest (then --bake)
    python scripts/spb_golden_net.py --list            # print the manifest summary, no engine boot

Files
    scripts/golden_manifest.json   the pinned id list + shas (commit it; ~100 KB)
    _golden/refs/<id>__<chan>.png  512px reference images (regenerable, gitignored)
    _golden/diff/<id>__<chan>.png  baseline | current | absdiff*8 for every CHANGED id
    _golden/last_check.json        machine-readable result of the last --check

Verdict lines are one per id: SAME | CHANGED | REMOVED | ADDED | ERROR | ABSENT | NONDET.
    ABSENT  = the id was not registered at bake time either (recorded so a later --check can
              report it as ADDED when a renderer comes back -- e.g. the 53 decade ids).
    NONDET  = the id rendered differently on two consecutive bakes; excluded from the gate
              and printed as a bug list (mirrors the look-refs 'deterministic:false' rule).
Summary line: GOLDEN NET: <same> same, <changed> changed, <removed> removed, <added> added, <error> error
Exit 0 only when changed + removed + error == 0.

Rules honoured: one engine boot per run; manifest written after EVERY id (kill-safe, resumable);
no repo file other than the manifest and _golden/ is written; renderers are only CALLED.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
import os
import sys
import tempfile
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MANIFEST = os.path.join(ROOT, "scripts", "golden_manifest.json")
OUT_DIR = os.path.join(ROOT, "_golden")
REFS_DIR = os.path.join(OUT_DIR, "refs")
DIFF_DIR = os.path.join(OUT_DIR, "diff")
PROTECTED_JSON = os.path.join(ROOT, "scripts", "protected_finishes.json")
FINISH_DATA_JS = os.path.join(ROOT, "paint-booth-0-finish-data.js")

SEED = 51
SM = 1.0
DEFAULT_RES = 512

MASTERCLASS_PREFIXES = ("vm_", "uj_", "rs_", "fd_", "ms_", "gf_", "gd_")
COLOR_MONO_PREFIXES = ("grad_", "cs_", "mc_", "clr_")          # engine/expansions/color_monolithics.py families
LAZY_ONLY_REPS = ("aurora_borealis", "cf_black_opal", "mc_black_marble", "acid_etched_glass",
                  "alexandrite", "decade_50s_starburst")
FOUNDATION_REPS = ("gloss", "matte", "satin", "chrome", "metallic", "flat_black", "primer", "eggshell")
DECADE_SHELF_LABELS = ("Decades 50s-80s", "90s, Skate & Surf")


# ----------------------------------------------------------------------------- utilities
def _atomic_write_json(path: str, obj) -> None:
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".golden-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def _load_manifest() -> dict:
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "entries": {}}


def _protected_ids() -> list[str]:
    try:
        with open(PROTECTED_JSON, encoding="utf-8") as f:
            return sorted(json.load(f).get("locked", {}).keys())
    except Exception:
        return []


def _fn_identity(fn) -> str:
    if fn is None:
        return ""
    mod = getattr(fn, "__module__", "?")
    qn = getattr(fn, "__qualname__", getattr(fn, "__name__", repr(type(fn))))
    return f"{mod}.{qn}"


def _sha(arr) -> str:
    a = np.ascontiguousarray(np.asarray(arr).astype(np.float32))
    return hashlib.sha256(a.tobytes()).hexdigest()


def _flatten_outputs(name: str, obj, out: dict, depth: int = 0) -> None:
    """Turn any render result (array / tuple / list / scalar / dict) into {channel: array}."""
    if depth > 3:
        return
    if isinstance(obj, np.ndarray):
        out[name] = obj
    elif isinstance(obj, (tuple, list)):
        for i, x in enumerate(obj):
            _flatten_outputs(f"{name}[{i}]", x, out, depth + 1)
    elif isinstance(obj, dict):
        for k in sorted(obj):
            _flatten_outputs(f"{name}.{k}", obj[k], out, depth + 1)
    elif isinstance(obj, (int, float, np.integer, np.floating, bool)):
        out[name] = np.asarray([float(obj)], np.float32)
    elif obj is None:
        pass
    else:
        try:
            out[name] = np.asarray(obj)
        except Exception:
            pass


def _to_png_array(arr) -> np.ndarray | None:
    x = np.asarray(arr)
    if x.ndim < 2 or x.shape[0] < 8 or x.shape[1] < 8:
        return None
    x = x.astype(np.float32)
    if x.ndim == 3:
        x = x[..., :3] if x.shape[2] >= 3 else x[..., 0]
    scale = 255.0 if float(np.nanmax(x)) <= 1.5 else 1.0
    x = np.clip(np.nan_to_num(x) * scale, 0, 255).astype(np.uint8)
    if x.ndim == 2:
        x = np.stack([x] * 3, axis=-1)
    return x


def _save_png(arr, path: str) -> bool:
    try:
        from PIL import Image
    except Exception:
        return False
    x = _to_png_array(arr)
    if x is None:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(x).save(path)
    return True


def _save_diff_png(base_png: str, current, path: str) -> bool:
    try:
        from PIL import Image
    except Exception:
        return False
    cur = _to_png_array(current)
    if cur is None or not os.path.exists(base_png):
        return False
    base = np.asarray(Image.open(base_png).convert("RGB"))
    if base.shape != cur.shape:
        return False
    diff = np.clip(np.abs(base.astype(np.int16) - cur.astype(np.int16)) * 8, 0, 255).astype(np.uint8)
    sheet = np.concatenate([base, cur, diff], axis=1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(sheet).save(path)
    return True


# ----------------------------------------------------------------------------- engine
def _engine():
    logging.disable(logging.CRITICAL)
    buf = io.StringIO()
    t0 = time.time()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2 as eng  # noqa: WPS433  (the live server's import order)
        eng._ensure_expansions_loaded()
    boot_s = time.time() - t0
    return eng, boot_s, buf.getvalue().count("\n")


def _registry_meta(eng) -> dict:
    meta = {
        "bases": len(eng.BASE_REGISTRY),
        "monolithics": len(eng.MONOLITHIC_REGISTRY),
        "patterns": len(eng.PATTERN_REGISTRY),
        "numpy": np.__version__,
        "python": sys.version.split()[0],
    }
    try:
        from engine import gpu as _gpu
        meta["gpu_backend"] = str(getattr(_gpu, "GPU_BACKEND", "?"))
        meta["xp"] = getattr(getattr(_gpu, "xp", None), "__name__", "?")
    except Exception:
        pass
    return meta


def _kind_of(eng, fid: str) -> str | None:
    if fid in eng.MONOLITHIC_REGISTRY:
        return "monolithic"
    if fid in eng.BASE_REGISTRY:
        return "base"
    if fid in eng.PATTERN_REGISTRY:
        return "pattern"
    return None


def _call_variants(fn, variants):
    """Call fn with the first argument tuple that does not raise TypeError."""
    last = None
    for args in variants:
        try:
            return fn(*args)
        except TypeError as ex:
            last = ex
            continue
    raise last if last else TypeError("no call variant")


def render_id(eng, fid: str, res: int) -> tuple[dict, dict, str]:
    """Return ({channel: array}, {fn_name: identity}, kind). Raises on failure."""
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    base = np.full(shape + (3,), 0.5, np.float32)
    outs: dict = {}
    fns: dict = {}
    kind = _kind_of(eng, fid)
    if kind is None:
        raise KeyError("not registered")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        if kind == "monolithic":
            entry = eng.MONOLITHIC_REGISTRY[fid]
            if isinstance(entry, (tuple, list)):
                spec_fn, paint_fn = entry[0], (entry[1] if len(entry) > 1 else None)
            else:
                spec_fn, paint_fn = entry.get("spec_fn"), entry.get("paint_fn")
            fns["spec_fn"] = _fn_identity(spec_fn)
            fns["paint_fn"] = _fn_identity(paint_fn)
            if spec_fn is not None:
                spec = _call_variants(spec_fn, [(shape, mask, SEED, SM), (shape, SEED, SM)])
                _flatten_outputs("spec", spec, outs)
            if paint_fn is not None:
                paint = _call_variants(paint_fn, [(base.copy(), shape, mask, SEED, SM, None),
                                                  (base.copy(), shape, mask, SEED, SM)])
                _flatten_outputs("paint", paint, outs)
        elif kind == "base":
            entry = eng.BASE_REGISTRY[fid]
            bsf = entry.get("base_spec_fn")
            pf = entry.get("paint_fn")
            fns["base_spec_fn"] = _fn_identity(bsf)
            fns["paint_fn"] = _fn_identity(pf)
            if bsf is not None:
                spec = _call_variants(bsf, [(shape, SEED, SM, entry.get("M", 0), entry.get("R", 100)),
                                            (shape, mask, SEED, SM), (shape, SEED, SM)])
                _flatten_outputs("spec", spec, outs)
            if pf is not None:
                paint = _call_variants(pf, [(base.copy(), shape, mask, SEED, SM, None),
                                            (base.copy(), shape, mask, SEED, SM)])
                _flatten_outputs("paint", paint, outs)
            for k in ("M", "R", "CC"):
                if k in entry:
                    outs[f"cell.{k}"] = np.asarray([float(entry[k])], np.float32)
        else:  # pattern
            entry = eng.PATTERN_REGISTRY[fid]
            if callable(entry):
                tex, pf = entry, None
            elif isinstance(entry, dict):
                tex, pf = entry.get("texture_fn"), entry.get("paint_fn")
            elif isinstance(entry, (tuple, list)):
                tex, pf = entry[0], (entry[1] if len(entry) > 1 else None)
            else:
                tex, pf = None, None
            fns["texture_fn"] = _fn_identity(tex)
            fns["paint_fn"] = _fn_identity(pf)
            if tex is not None:
                t = _call_variants(tex, [(shape, mask, SEED, SM), (shape, mask, SEED), (shape, SEED, SM)])
                _flatten_outputs("texture", t, outs)
            if pf is not None:
                try:
                    p = _call_variants(pf, [(base.copy(), shape, mask, SEED, SM, None),
                                            (base.copy(), shape, mask, SEED, SM)])
                    _flatten_outputs("paint", p, outs)
                except Exception as ex:  # pattern paint_fns are wrappers with several contracts
                    outs["paint.error"] = np.asarray([0.0], np.float32)
                    fns["paint_fn_error"] = f"{type(ex).__name__}: {ex}"[:160]
    if not outs:
        raise RuntimeError("renderer produced no outputs")
    return outs, fns, kind


def _shas(outs: dict) -> dict:
    return {k: _sha(v) for k, v in outs.items()}


# ----------------------------------------------------------------------------- manifest ids
def _picker_groups() -> dict:
    """{'BG':{..},'SG':{..},'PG':{..}} straight from paint-booth-0-finish-data.js via node."""
    import subprocess
    tmp = os.path.join(OUT_DIR, "_groups.json")
    os.makedirs(OUT_DIR, exist_ok=True)
    js = ("const fs=require('fs');const g={};"
          "new Function('g',fs.readFileSync('paint-booth-0-finish-data.js','utf8')"
          "+';g.SG=SPECIAL_GROUPS;g.BG=BASE_GROUPS;g.PG=(typeof PATTERN_GROUPS!==\"undefined\")?PATTERN_GROUPS:{};')(g);"
          f"fs.writeFileSync({json.dumps(tmp)},JSON.stringify({{SG:g.SG,BG:g.BG,PG:g.PG}}),'utf8');")
    try:
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, timeout=120)
        with open(tmp, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"  [golden] WARNING: node group extraction failed ({ex}); falling back to regex")
        return _picker_groups_regex()


def _picker_groups_regex() -> dict:
    import re
    txt = open(FINISH_DATA_JS, encoding="utf-8", errors="replace").read()
    out = {"BG": {}, "SG": {}, "PG": {}}
    for key, const in (("BG", "BASE_GROUPS"), ("SG", "SPECIAL_GROUPS"), ("PG", "PATTERN_GROUPS")):
        start = txt.find(f"const {const}")
        if start == -1:
            continue
        end = txt.find("\n};", start)
        block = txt[start:end]
        for m in re.finditer(r'"([^"\n]+)"\s*:\s*\[(.*?)\]', block, re.S):
            ids = re.findall(r'"([^"]+)"', m.group(2))
            if ids:
                out[key][m.group(1)] = ids
    return out


def build_default_ids(eng) -> tuple[list[str], dict]:
    groups = _picker_groups()
    ids: list[str] = []
    why: dict = {}

    def add(i, reason):
        if i and i not in why:
            ids.append(i)
            why[i] = reason

    for p in _protected_ids():
        add(p, "protected")
    for gk, label in (("BG", "base-group"), ("SG", "special-group"), ("PG", "pattern-group")):
        for gname, members in groups.get(gk, {}).items():
            if members:
                add(members[0], f"{label}:{gname}")
    for gname, members in groups.get("PG", {}).items():
        if any(lbl in gname for lbl in DECADE_SHELF_LABELS):
            for m in members:
                add(m, f"decade-shelf:{gname}")
    for f in FOUNDATION_REPS:
        add(f, "foundation")
    for r in LAZY_ONLY_REPS:
        add(r, "lazy-only-family")
    all_mono = sorted(eng.MONOLITHIC_REGISTRY)
    all_base = sorted(eng.BASE_REGISTRY)
    for pref in MASTERCLASS_PREFIXES:
        hit = next((k for k in all_mono if k.startswith(pref)), None) or next((k for k in all_base if k.startswith(pref)), None)
        add(hit, f"masterclass:{pref}")
    hou = next((k for k in all_mono if k.startswith("houdini_")), None)
    add(hou, "houdini-rep")
    for k in all_mono + all_base:
        if k.startswith(COLOR_MONO_PREFIXES):
            add(k, "color-monolithic-family (v1/v2 factory question)")
    return ids, why


# ----------------------------------------------------------------------------- modes
def do_bake(args) -> int:
    man = _load_manifest()
    eng, boot_s, boot_lines = _engine()
    meta = _registry_meta(eng)
    print(f"[golden] engine booted in {boot_s:.1f}s ({boot_lines} log lines); registries "
          f"{meta['bases']}/{meta['monolithics']}/{meta['patterns']}")
    entries = man.setdefault("entries", {})
    if args.ids:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        why = {i: "cli" for i in ids}
    elif entries and not args.rebuild_manifest:
        ids = sorted(entries)
        why = {i: entries[i].get("why", "") for i in ids}
    else:
        ids, why = build_default_ids(eng)
        print(f"[golden] pinned {len(ids)} ids into the manifest")
    protected = set(_protected_ids())
    man["meta"].update({
        "res": args.res, "seed": SEED, "sm": SM, "convention": "finish-law: float32 0.5 base, float32 ones mask, direct fn calls",
        "baked_from": "shokker_engine_v2 legacy dicts after _ensure_expansions_loaded()",
        "registry": meta, "baked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    _atomic_write_json(MANIFEST, man)
    n_done = n_skip = n_err = n_absent = n_nondet = 0
    t_all = time.time()
    for i, fid in enumerate(ids, 1):
        prev = entries.get(fid)
        if prev and prev.get("status") in ("ok", "nondet") and not args.force and fid not in (args.accept_ids or ()):
            n_skip += 1
            continue
        rec = {"why": why.get(fid, prev.get("why", "") if prev else ""), "protected": fid in protected,
               "res": args.res, "baked_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        if args.reason:
            rec["accept_reason"] = args.reason
        kind = _kind_of(eng, fid)
        if kind is None:
            rec.update({"status": "absent", "kind": None})
            entries[fid] = rec
            n_absent += 1
            print(f"  ABSENT   {fid}")
            _atomic_write_json(MANIFEST, man)
            continue
        try:
            t0 = time.time()
            outs, fns, kind = render_id(eng, fid, args.res)
            ms1 = (time.time() - t0) * 1000
            sh1 = _shas(outs)
            outs2, _, _ = render_id(eng, fid, args.res)
            sh2 = _shas(outs2)
            nondet = sh1 != sh2
            rec.update({"status": "nondet" if nondet else "ok", "kind": kind, "channels": sh1,
                        "fn": fns, "ms": round(ms1, 1),
                        "stats": {k: [round(float(np.nanmean(v)), 4), round(float(np.nanstd(v)), 4)]
                                  for k, v in outs.items() if np.asarray(v).size > 1}})
            if nondet:
                rec["nondet_channels"] = sorted(k for k in sh1 if sh1[k] != sh2.get(k))
                n_nondet += 1
            for ch, arr in outs.items():
                if np.asarray(arr).ndim >= 2 and np.asarray(arr).shape[0] >= 8:
                    _save_png(arr, os.path.join(REFS_DIR, f"{fid}__{ch}.png"))
            n_done += 1
            print(f"  {'NONDET ' if nondet else 'BAKED  '} {fid:42s} {kind:10s} {ms1:7.0f} ms  {len(outs)} ch")
        except Exception as ex:
            rec.update({"status": "error", "kind": kind, "error": f"{type(ex).__name__}: {ex}"[:200]})
            n_err += 1
            print(f"  ERROR    {fid:42s} {type(ex).__name__}: {str(ex)[:90]}")
        entries[fid] = rec
        _atomic_write_json(MANIFEST, man)
    print(f"GOLDEN BAKE: {n_done} baked, {n_skip} skipped (already baked), {n_absent} absent, "
          f"{n_nondet} nondeterministic, {n_err} error in {time.time() - t_all:.0f}s -> {MANIFEST}")
    return 0 if n_err == 0 else 1


def do_check(args) -> int:
    man = _load_manifest()
    entries = man.get("entries", {})
    if not entries:
        print("GOLDEN NET: no manifest -- run --bake first")
        return 2
    eng, boot_s, boot_lines = _engine()
    meta = _registry_meta(eng)
    base_meta = man.get("meta", {}).get("registry", {})
    res = int(man.get("meta", {}).get("res", DEFAULT_RES))
    drift = {k: (base_meta.get(k), meta.get(k)) for k in ("bases", "monolithics", "patterns")
             if base_meta.get(k) != meta.get(k)}
    if drift:
        print("REGISTRY-DRIFT (advisory): " + ", ".join(f"{k} {a}->{b}" for k, (a, b) in drift.items()))
    ids = [i.strip() for i in args.ids.split(",")] if args.ids else sorted(entries)
    counts = {"same": 0, "changed": 0, "removed": 0, "added": 0, "error": 0, "absent": 0, "nondet": 0}
    results = {}
    t_all = time.time()
    for fid in ids:
        rec = entries.get(fid)
        if rec is None:
            print(f"  UNKNOWN  {fid} (not in manifest; use --add)")
            continue
        kind_now = _kind_of(eng, fid)
        if rec.get("status") == "absent":
            if kind_now is None:
                counts["absent"] += 1
                results[fid] = "ABSENT"
                print(f"  ABSENT   {fid}")
            else:
                counts["added"] += 1
                results[fid] = "ADDED"
                print(f"  ADDED    {fid:42s} now registered as {kind_now} (was absent at bake)")
            continue
        if rec.get("status") == "error":
            # re-try: an id that errored at bake and still errors is not gated
            try:
                render_id(eng, fid, res)
                print(f"  ADDED    {fid:42s} renders now (errored at bake) -- re-bake to pin")
                counts["added"] += 1
                results[fid] = "ADDED"
            except Exception:
                counts["absent"] += 1
                results[fid] = "ABSENT"
            continue
        if kind_now is None:
            counts["removed"] += 1
            results[fid] = "REMOVED"
            print(f"  REMOVED  {fid:42s} (was {rec.get('kind')})")
            continue
        if rec.get("status") == "nondet":
            counts["nondet"] += 1
            results[fid] = "NONDET"
            print(f"  NONDET   {fid:42s} excluded from gate ({','.join(rec.get('nondet_channels', []))[:60]})")
            continue
        try:
            outs, fns, kind = render_id(eng, fid, res)
        except Exception as ex:
            counts["error"] += 1
            results[fid] = "ERROR"
            print(f"  ERROR    {fid:42s} {type(ex).__name__}: {str(ex)[:90]}")
            continue
        sh = _shas(outs)
        changed = sorted(k for k in set(sh) | set(rec.get("channels", {})) if sh.get(k) != rec.get("channels", {}).get(k))
        fn_changed = sorted(k for k in set(fns) | set(rec.get("fn", {})) if fns.get(k) != rec.get("fn", {}).get(k) and not k.endswith("_error"))
        if changed:
            counts["changed"] += 1
            results[fid] = "CHANGED"
            for ch in changed:
                if ch in outs and np.asarray(outs[ch]).ndim >= 2:
                    _save_diff_png(os.path.join(REFS_DIR, f"{fid}__{ch}.png"), outs[ch],
                                   os.path.join(DIFF_DIR, f"{fid}__{ch}.png"))
            note = (" fn:" + ";".join(f"{k}={fns.get(k, '')[-40:]}" for k in fn_changed)) if fn_changed else ""
            print(f"  CHANGED  {fid:42s} {kind:10s} channels={','.join(changed)[:70]}{note}")
        else:
            counts["same"] += 1
            results[fid] = "SAME"
            if fn_changed:
                print(f"  SAME     {fid:42s} (pixels identical; fn identity moved: {';'.join(fn_changed)})")
    summary = (f"GOLDEN NET: {counts['same']} same, {counts['changed']} changed, {counts['removed']} removed, "
               f"{counts['added']} added, {counts['error']} error"
               f" ({counts['absent']} absent, {counts['nondet']} nondet excluded) in {time.time() - t_all:.0f}s")
    print(summary)
    _atomic_write_json(os.path.join(OUT_DIR, "last_check.json"),
                       {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "registry": meta, "drift": drift,
                        "counts": counts, "results": results, "summary": summary})
    return 0 if (counts["changed"] + counts["removed"] + counts["error"]) == 0 else 1


def do_accept(args) -> int:
    ids = [i.strip() for i in args.accept.split(",") if i.strip()]
    protected = set(_protected_ids())
    blocked = [i for i in ids if i in protected]
    if blocked and not args.owner_approved:
        print("REFUSED: protected ids need --owner-approved and --reason (owner mandate 2026-08-31): " + ", ".join(blocked))
        return 3
    if not args.reason:
        print("REFUSED: --accept requires --reason \"<declared change>\"")
        return 3
    args.ids = ",".join(ids)
    args.force = True
    args.accept_ids = set(ids)
    return do_bake(args)


def do_add(args) -> int:
    man = _load_manifest()
    ids = [i.strip() for i in args.add.split(",") if i.strip()]
    new = [i for i in ids if i not in man.setdefault("entries", {})]
    for i in new:
        man["entries"][i] = {"status": "pending", "why": "added via --add"}
    _atomic_write_json(MANIFEST, man)
    print(f"[golden] added {len(new)} ids (now {len(man['entries'])}); run --bake to render them")
    return 0


def do_list(_args) -> int:
    man = _load_manifest()
    entries = man.get("entries", {})
    from collections import Counter
    c = Counter(e.get("status") for e in entries.values())
    k = Counter(e.get("kind") for e in entries.values())
    print(f"manifest: {len(entries)} ids; status={dict(c)}; kind={dict(k)}; meta={man.get('meta', {}).get('registry')}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bake", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--accept", default="")
    ap.add_argument("--add", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ids", default="")
    ap.add_argument("--res", type=int, default=DEFAULT_RES)
    ap.add_argument("--force", action="store_true", help="re-bake ids that are already baked")
    ap.add_argument("--rebuild-manifest", action="store_true", help="recompute the default id set")
    ap.add_argument("--owner-approved", action="store_true")
    ap.add_argument("--reason", default="")
    args = ap.parse_args(argv)
    args.accept_ids = set()
    os.makedirs(OUT_DIR, exist_ok=True)
    if args.list:
        return do_list(args)
    if args.add:
        return do_add(args)
    if args.accept:
        return do_accept(args)
    if args.bake:
        return do_bake(args)
    return do_check(args)


if __name__ == "__main__":
    sys.exit(main())
