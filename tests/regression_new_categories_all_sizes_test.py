# -*- coding: utf-8 -*-
"""Every 2026 expansion finish must render at EVERY size the app asks for.

Owner, 2026-08-30: "FRACTURED TESSERA finishes are not loading ... the thumbnail
previews won't load nor will the finishes themselves."

Root cause: `kit.glass_spec` consumed the label map raw whenever
`res <= WORK` (1152). Labels are solved at GEN (768), so the branch only lined
up when the render happened to be 768 wide. The 2048 car render took the OTHER
branch — the one that resizes — which is why the build gates (all run at 2048)
were green while every swatch (48/256) and every 1024 live preview raised
"operands could not be broadcast together with shapes (1024,1024,3)
(768,768,3)" and the app served 503s.

The lesson this test encodes: a size-dependent branch means the gate has to
sweep sizes, not just the biggest one. 48 = picker swatch, 256 = hover popout,
512 = card, 1024 = live preview, 2048 = the car.

Run:  python tests/regression_new_categories_all_sizes_test.py
"""
import os
import sys
import traceback

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# The sizes the running app actually requests. 2048 is the car; the four below
# it are all served by /api/swatch and preview_render.
SIZES = (48, 256, 512, 1024, 2048)

# Prefixes of the categories built in this cycle. Each maps to the module that
# owns it, so a failure names the file to open.
PREFIXES = {
    "ffl_": "engine/expansions/fractured_flames_2026.py",
    "fts_": "engine/expansions/fractured_tessera_2026.py",
    "ffo_": "engine/expansions/fractured_foundry_2026.py",
    "frl_": "engine/expansions/fractured_relics_2026.py",
    "xlab_": "engine/expansions/x_lab_shift_2026.py",
    # 2026-08-31 overnight rebuild. TESSERA shipped broken because every gate
    # only ever measured 2048 and the labels were solved at 768 — these five
    # prefixes go in the same net.
    "nsx_": "engine/expansions/fractured_nightshift_2026.py",
    "cos_": "engine/expansions/fractured_cosmos_2026.py",
    "elm_": "engine/expansions/fractured_elements_2026.py",
    "pdg_": "engine/expansions/paradigm_2026.py",
}


def _load_registry():
    import shokker_engine_v2 as eng
    return eng.MONOLITHIC_REGISTRY


def _render_once(spec_fn, paint_fn, res):
    """Exercise BOTH channels exactly as build_multi_zone does."""
    shape = (res, res, 3)
    mask = np.ones((res, res), np.float32)
    paint = np.full((res, res, 3), 0.5, np.float32)
    spec = spec_fn(shape, mask, 51, 1.0)
    art = paint_fn(paint, shape, mask, 51, 1.0, None)
    spec = np.asarray(spec)
    art = np.asarray(art)
    if spec.shape[0] != res or spec.shape[1] != res:
        raise AssertionError("spec came back %s, expected %dx%d" % (spec.shape, res, res))
    if art.shape[0] != res or art.shape[1] != res:
        raise AssertionError("paint came back %s, expected %dx%d" % (art.shape, res, res))
    return spec, art


def main(argv):
    only = argv[1] if len(argv) > 1 else ""
    sizes = SIZES
    if len(argv) > 2:
        sizes = tuple(int(s) for s in argv[2].split(","))

    reg = _load_registry()
    ids = sorted(i for i in reg
                 if any(i.startswith(p) for p in PREFIXES)
                 and (not only or i.startswith(only)))
    if not ids:
        print("RESULT: FAIL - no finishes matched %r" % only)
        return 1

    failures = []
    for fid in ids:
        spec_fn, paint_fn = reg[fid]
        bad = []
        for res in sizes:
            try:
                _render_once(spec_fn, paint_fn, res)
            except Exception as exc:                       # noqa: BLE001 - reporting
                bad.append((res, "%s: %s" % (type(exc).__name__, exc)))
                if os.environ.get("SPB_TRACE"):
                    traceback.print_exc()
        if bad:
            failures.append((fid, bad))
            print("FAIL %-28s %s" % (fid, "; ".join("%d -> %s" % b for b in bad)))

    print("")
    print("checked %d finishes x %d sizes (%s)"
          % (len(ids), len(sizes), ", ".join(str(s) for s in sizes)))
    if failures:
        mods = sorted({PREFIXES[p] for fid, _ in failures for p in PREFIXES if fid.startswith(p)})
        print("RESULT: FAIL - %d finish(es) broken; see %s" % (len(failures), ", ".join(mods)))
        return 1
    print("RESULT: OK - every finish rendered at every size")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
