# -*- coding: utf-8 -*-
"""SPB Uniqueness Gate — the HARD LINE every new finish must clear.

THE LAW (docs/UNIQUENESS_LAW.md):
  1. A finish that is >= 80% structurally similar to ANY other finish in the WHOLE
     catalog (cross-category) FAILS and must be redone. No exceptions.
  2. A finish's SPEC must mirror the PAINT's structure (the spec complements the
     finish) UNLESS it is deliberately listed as intentionally-different.

Structural similarity is COLOR-INDEPENDENT (luma pHash + structural descriptor),
so a recolor of an existing design is caught even with a totally different palette.

Run BEFORE you ship any new/rebuilt finishes:
  python scripts/spb_catalog_fingerprint.py            # make sure the index is current
  python scripts/spb_uniqueness_gate.py --ids new1,new2
  python scripts/spb_uniqueness_gate.py --module groovy_vibes_2026   # all ids in a module
  python scripts/spb_uniqueness_gate.py --report       # list existing dup pairs (rebuild worklist)

Exit code is non-zero if anything FAILS, so it works as a build/CI gate.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from spb_catalog_fingerprint import (FP_RES, SEED, NPZ, META, SOLID_STD, fingerprint, _sim_matrix)  # noqa: E402

SIM_FAIL = 0.80          # >= this structural similarity to ANY finish => FAIL (owner's 80% line). HARD GATE.
# spec-trace is ADVISORY only: a linear structural-cosine "spec mirrors paint" check over-flags
# legitimately-complementary specs (validated 2026-06-15 — it flagged owner-APPROVED Tactical 17/17,
# Ceramic 14/15). It surfaces the worst-decoupled specs to eyeball; it does NOT fail the gate.
TRACE_MIN = 0.20
EXEMPT_FILE = REPO / "scripts" / "uniqueness_exemptions.json"


def _load_index():
    if not NPZ.exists():
        sys.exit("No fingerprint index. Run: python scripts/spb_catalog_fingerprint.py")
    z = np.load(NPZ, allow_pickle=True)
    ids = [str(x) for x in z["ids"]]
    meta = json.loads(META.read_text(encoding="utf-8")).get("items", {}) if META.exists() else {}
    return ids, z["struct"], z["phash"], meta


def _exempt():
    if EXEMPT_FILE.exists():
        try:
            return set(json.loads(EXEMPT_FILE.read_text(encoding="utf-8")).get("intentional_spec", []))
        except Exception:
            return set()
    return set()


def _cand_sim(cand_struct, cand_phash, idx_struct, idx_phash):
    """combined similarity of one candidate vs every index row -> vector[N]."""
    cos = idx_struct @ cand_struct
    cb = np.unpackbits(cand_phash)[None, :].astype(np.int16) * 2 - 1
    ib = np.unpackbits(idx_phash, axis=1).astype(np.int16) * 2 - 1
    phash_sim = ((ib @ cb[0]).astype(np.float32) + 256.0) / 512.0
    return 0.5 * cos + 0.5 * phash_sim


def _render(eng, item_id, kind, meta):
    from spb_visual_workbench import _render_item
    rgb, spec, _ = _render_item(eng, item_id, kind, FP_RES, SEED, meta)
    return fingerprint(rgb, spec)


def _kind_of(eng, item_id):
    if item_id in eng.BASE_REGISTRY:
        return "base"
    if item_id in eng.MONOLITHIC_REGISTRY:
        return "monolithic"
    if item_id in eng.PATTERN_REGISTRY:
        return "pattern"
    return "base"


def gate_ids(cand_ids):
    ids, idx_struct, idx_phash, meta = _load_index()
    exempt = _exempt()
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as eng
        if hasattr(eng, "_ensure_expansions_loaded"):
            eng._ensure_expansions_loaded()
    id_pos = {i: k for k, i in enumerate(ids)}
    solid_mask = np.array([bool(meta.get(i, {}).get("solid")) for i in ids])
    fails = 0
    print(f"UNIQUENESS GATE  (sim>={SIM_FAIL:.0%} FAIL, trace<{TRACE_MIN} = spec doesn't mirror paint)\n")
    for cid in cand_ids:
        kind = _kind_of(eng, cid)
        try:
            cs, cph, trace, energy = _render(eng, cid, kind, {})
        except Exception as e:
            print(f"  ✗ {cid:28s} RENDER ERROR: {e}"); fails += 1; continue
        if energy < SOLID_STD:
            print(f"  ◐ SOLID  {cid:28s}  — flat finish, structural rules N/A (judged by spec/color)")
            continue
        sims = _cand_sim(cs, cph, idx_struct, idx_phash)
        sims[solid_mask] = -1.0            # never flag 'similar to a flat solid'
        if cid in id_pos:
            sims[id_pos[cid]] = -1.0       # don't compare to self
        j = int(np.argmax(sims)); top = float(sims[j])
        nn = ids[j]; nn_cat = meta.get(nn, {}).get("category", "?")
        sim_bad = top >= SIM_FAIL
        trace_bad = (trace < TRACE_MIN) and (cid not in exempt)
        ok = not sim_bad          # the 80% clone rule is the HARD gate; spec-trace is advisory only
        flag = "✓ PASS" if ok else "✗ FAIL"
        if not ok:
            fails += 1
        adv = "   ⚠ spec-trace low (advisory — eyeball it)" if trace_bad else ""
        tail = (f"  — {top:.0%} similar to '{nn}' [{nn_cat}]" if sim_bad
                else f"  (nearest '{nn}' {top:.0%}, trace {trace:.2f})")
        print(f"  {flag}  {cid:28s}{tail}{adv}")
    print(f"\n{'='*60}\nRESULT: {len(cand_ids)-fails}/{len(cand_ids)} pass, {fails} FAIL")
    return fails


def report(threshold):
    ids, struct, phash, meta = _load_index()
    if len(ids) < 2:
        sys.exit("index too small")
    S = _sim_matrix(struct, phash)
    np.fill_diagonal(S, -1.0)
    solid_mask = np.array([bool(meta.get(i, {}).get("solid")) for i in ids])
    S[solid_mask, :] = -1.0           # flat solids legitimately match each other — exclude
    S[:, solid_mask] = -1.0
    pairs = []
    seen = set()
    for a in range(len(ids)):
        b = int(np.argmax(S[a]))
        s = float(S[a][b])
        key = tuple(sorted((ids[a], ids[b])))
        if s >= threshold and key not in seen:
            seen.add(key)
            pairs.append((s, ids[a], meta.get(ids[a], {}).get("category", "?"),
                          ids[b], meta.get(ids[b], {}).get("category", "?")))
    pairs.sort(reverse=True)
    print(f"EXISTING DUPLICATE PAIRS >= {threshold:.0%}  ({len(pairs)} pairs — the rebuild worklist)\n")
    for s, a, ca, b, cb in pairs:
        print(f"  {s:.0%}  {a:26s} [{ca:18s}]  ≈  {b:26s} [{cb}]")
    low = [i for i in ids if meta.get(i, {}).get("trace", 1) < TRACE_MIN
           and not meta.get(i, {}).get("solid") and i not in _exempt()]
    print(f"\nSPEC-DOESN'T-MIRROR-PAINT (trace < {TRACE_MIN}): {len(low)} finishes")
    for i in low[:40]:
        print(f"  {i:28s} trace={meta.get(i,{}).get('trace')}  [{meta.get(i,{}).get('category','?')}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--module", default="", help="check every paint_<id> in engine/paint_v2/<module>")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--threshold", type=float, default=SIM_FAIL)
    args = ap.parse_args()

    if args.report:
        report(args.threshold); return
    cand = [x.strip() for x in args.ids.split(",") if x.strip()]
    if args.module:
        mod = importlib.import_module("engine.paint_v2." + args.module.replace(".py", ""))
        cand += sorted(n[6:] for n in dir(mod) if n.startswith("paint_") and hasattr(mod, "spec_" + n[6:]))
    if not cand:
        sys.exit("give --ids, --module, or --report")
    fails = gate_ids(cand)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
