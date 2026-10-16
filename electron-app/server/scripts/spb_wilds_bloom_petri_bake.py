"""Bake the 40 SPB-WILDS BLOOM/PETRI thumbnails through the real engine.

The generic thumbnail harness now explicitly selects the same-finish ``mono:``
color source for every monolithic (systemic fix, 2026-08-23).  This focused
harness keeps a separate 40-ID hard-fail gate so a future malformed zone, flat
paint, or missing output cannot silently become accepted M7 evidence.

SPB-WILDS, tick 4 (2026-08-23). Owner verdict: "Too much redundancy way too
similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping
stuff." A gray bake is a hard failure, not valid M7 evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from engine.expansions import fractured_bloom_2026 as bloom
    from engine.expansions import fractured_petri_2026 as petri
    from engine.registry import MONOLITHIC_REGISTRY
    import rebuild_thumbnails as rt

    bloom.install_into_engine(MONOLITHIC_REGISTRY)
    petri.install_into_engine(MONOLITHIC_REGISTRY)
    ids = list(bloom.ALL) + list(petri.ALL)
    original_zone = rt.make_zone_for_finish

    def wilds_zone(finish_type, finish_key, default_base="living_matte"):
        zone = original_zone(finish_type, finish_key, default_base)
        if finish_type == "monolithic" and finish_key in ids:
            zone["base_color_mode"] = "special"
            zone["base_color_source"] = f"mono:{finish_key}"
        return zone

    rt.make_zone_for_finish = wilds_zone
    failures = []
    for fid in ids:
        sys.argv = ["rebuild_thumbnails.py", "--type", "monolithic", "--key", fid,
                    "--output", "thumbnails", "--quiet"]
        try:
            rt.main()
            path = ROOT / "thumbnails" / "monolithic" / f"{fid}.png"
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None or float(image.std()) < 4.0:
                failures.append(f"{fid}: missing/flat output")
            else:
                print(f"[wilds-bake] OK {fid} std={float(image.std()):.2f}", flush=True)
        except Exception as exc:  # keep baking, then fail with the full list
            failures.append(f"{fid}: {type(exc).__name__}: {exc}")
    if failures:
        print("[wilds-bake] FAILURES:", flush=True)
        for failure in failures:
            print(f"  {failure}", flush=True)
        return 1
    print(f"[wilds-bake] PASS {len(ids)}/40 non-flat real-engine thumbnails", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
