# -*- coding: utf-8 -*-
"""Splice authored finish blocks into a shelf module, then validate each one.

Written for the 2026-09-04 FLAW LAB build, where 25 finishes were authored in
parallel and had to be assembled deterministically rather than pasted by hand.

The validation is the point: a finish that does not parse, does not render, or
renders a constant plate is rejected HERE, with a named reason, instead of
poisoning the gate run downstream.

USAGE
    python scripts/spb_assemble_shelf.py --json <authored.json> \
        --module engine/paint_v2/flaw_lab_2026.py
    python scripts/spb_assemble_shelf.py --validate-only --module engine.paint_v2.flaw_lab_2026
"""
from __future__ import annotations

import argparse
import ast
import importlib
import io
import json
import os
import sys
import tempfile
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _safe_write(path, text):
    ast.parse(text)
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    os.close(fd)
    io.open(tmp, "w", encoding="utf-8").write(text)
    os.replace(tmp, path)


def assemble(json_path, module_path):
    data = json.load(io.open(json_path, encoding="utf-8"))
    items = data["finishes"] if isinstance(data, dict) else data
    blocks, cats, spaces, bad = [], [], [], []
    for it in items:
        fid = it.get("fid", "?")
        code = (it.get("code") or "").strip()
        # agents sometimes wrap the block in a markdown fence despite instructions
        if code.startswith("```"):
            code = code.split("\n", 1)[1]
            code = code.rsplit("```", 1)[0]
        try:
            ast.parse(code)
        except SyntaxError as exc:
            bad.append((fid, f"SyntaxError line {exc.lineno}: {exc.msg}"))
            continue
        names = {n.name for n in ast.walk(ast.parse(code)) if isinstance(n, ast.FunctionDef)}
        if f"paint_{fid}" not in names or f"spec_{fid}" not in names:
            bad.append((fid, f"missing paint_/spec_ pair (found {sorted(names)})"))
            continue
        if "import " in code:
            bad.append((fid, "contains an import inside the block"))
            continue
        blocks.append(f"\n# {'═' * 60}\n{code}\n")
        cats.append("    " + (it.get("catalog_entry") or "").strip().rstrip(","). rstrip() + ",")
        spaces.append("    " + (it.get("space_entry") or "").strip().rstrip(",").rstrip() + ",")

    src = io.open(module_path, encoding="utf-8").read()
    src = src.replace("# __FINISH_BLOCKS__", "\n".join(blocks))
    src = src.replace("    # __CATALOG_ENTRIES__", "\n".join(cats))
    src = src.replace("    # __SPACE_ENTRIES__", "\n".join(spaces))
    _safe_write(module_path, src)
    print(f"assembled {len(blocks)} finishes into {os.path.relpath(module_path, ROOT)}")
    for fid, why in bad:
        print(f"  REJECTED {fid}: {why}")
    return len(blocks), bad


def validate(module_name, res=384):
    """Render every finish small and report anything that cannot ship."""
    mod = importlib.import_module(module_name)
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    src = np.zeros(shape + (3,), np.float32)
    src[:, :, 0], src[:, :, 1], src[:, :, 2] = 0.62, 0.13, 0.16
    ok, bad = [], []
    for fid in sorted(mod.CATALOG):
        try:
            t0 = time.time()
            paint = np.asarray(getattr(mod, "paint_" + fid)(src, shape, mask, 51, 1.0, None), np.float32)
            spec = getattr(mod, "spec_" + fid)(shape, 51, 1.0,
                                               mod.CATALOG[fid].get("M", 0),
                                               mod.CATALOG[fid].get("R", 100))
            dt = time.time() - t0
            if paint.shape != shape + (3,):
                bad.append((fid, f"paint shape {paint.shape}")); continue
            if not np.isfinite(paint).all():
                bad.append((fid, "paint has non-finite values")); continue
            if len(spec) != 3:
                bad.append((fid, f"spec returned {len(spec)} channels")); continue
            M, R, CC = [np.asarray(c, np.float32) for c in spec]
            if not all(np.isfinite(c).all() for c in (M, R, CC)):
                bad.append((fid, "spec has non-finite values")); continue
            if float(CC.min()) < 15.9:
                bad.append((fid, f"CC dips to {float(CC.min()):.1f} (16 is max gloss)")); continue
            lum = paint[:, :, 0] * .299 + paint[:, :, 1] * .587 + paint[:, :, 2] * .114
            if float(lum.std()) < 1e-4:
                bad.append((fid, "paint is a constant plate")); continue
            ok.append((fid, float(lum.std()) / (float(lum.mean()) + 1e-6), dt))
        except Exception as exc:
            bad.append((fid, f"{type(exc).__name__}: {exc}"))
    print(f"\nVALIDATE {module_name} @ {res}: {len(ok)} ok, {len(bad)} broken")
    for fid, amp, dt in ok:
        print(f"  ok    {fid:26s} amp {amp:.3f}  {dt * (2048 / res) ** 2:5.1f}s est@2048")
    for fid, why in bad:
        print(f"  BROKEN {fid:26s} {why}")
    return ok, bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--module", required=True)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--res", type=int, default=384)
    a = ap.parse_args()
    if not a.validate_only:
        assemble(a.json, a.module)
    modname = a.module
    if modname.endswith(".py"):
        modname = modname.replace("/", ".").replace("\\", ".")[:-3]
    ok, bad = validate(modname, a.res)
    raise SystemExit(1 if bad else 0)
