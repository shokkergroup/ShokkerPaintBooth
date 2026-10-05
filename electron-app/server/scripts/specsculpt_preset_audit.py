"""Spec Sculpt preset audit (campaign #12, 2026-06-24).

Renders EVERY wired scratch preset on a test paint and flags broken ones:
  - error      : raised an exception (e.g. points at a finish id that no longer exists)
  - dead       : output identical to the no-preset baseline (id didn't resolve / not wired)
  - degenerate : near-flat output (std < 2) — no material variation
  - illegal    : fails the iRacing iron rules (iron_validate)

Run:  python scripts/specsculpt_preset_audit.py   (exit 1 if any preset is broken)
Set AUDIT_PAINT to override the test paint.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from engine.spec_sculpt.core import load_paint_rgb_float01  # noqa: E402
from engine.spec_sculpt.generate import scratch_spec_from_any_paint, iron_validate  # noqa: E402
from engine.spec_sculpt.presets import normalize_preset_stack  # noqa: E402


def _preset_ids():
    import server  # builds the live preset list exactly as the app serves it
    c = server.app.test_client()
    pj = c.get('/api/spec-sculpt/presets').get_json()
    ids = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('id'), str):
                ids.append(o['id'])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(pj)
    return list(dict.fromkeys(ids))


def main():
    paint = os.environ.get('AUDIT_PAINT') or 'SPB Chevy Truck Starting Example PSD.psd'
    paint = os.path.abspath(paint)
    tex, _, _ = load_paint_rgb_float01(paint, target_size=320)
    base = scratch_spec_from_any_paint(tex, seed=7)
    ids = _preset_ids()
    res = {'ok': [], 'dead': [], 'error': [], 'degenerate': [], 'illegal': []}
    for pid in ids:
        try:
            ps = normalize_preset_stack([{'id': pid, 'weight': 100}])
            spec = scratch_spec_from_any_paint(tex, seed=7, preset_stack=ps)
        except Exception as e:
            res['error'].append((pid, repr(e)[:80]))
            continue
        if np.array_equal(spec, base):
            res['dead'].append(pid)
            continue
        if float(np.asarray(spec).std()) < 2.0:
            res['degenerate'].append(pid)
            continue
        if not iron_validate(spec)['valid']:
            res['illegal'].append(pid)
        res['ok'].append(pid)
    print("=== SPEC SCULPT PRESET AUDIT ===")
    print(f"total {len(ids)} | OK {len(res['ok'])} | dead {len(res['dead'])} | "
          f"degenerate {len(res['degenerate'])} | error {len(res['error'])} | illegal {len(res['illegal'])}")
    broken = res['error'] + res['dead'] + res['degenerate'] + res['illegal']
    for k in ('error', 'dead', 'degenerate', 'illegal'):
        if res[k]:
            print(k.upper(), '->', res[k][:30])
    return 0 if not broken else 1


if __name__ == '__main__':
    sys.exit(main())
