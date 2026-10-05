#!/usr/bin/env python3
"""Wire the FOUNDATION EFX shelf into the registry + the static JS catalog (AI-as-compiler).

Reads engine/paint_v2/foundation_efx_2026.py ROWS and patches:
  * engine/base_registry_data.py      — merge FOUNDATION_EFX after the legacy EFX merge
  * paint-booth-0-finish-data.js      — BASES entries (new ids), renamed/re-described
                                        reworked ids, chalky_base un-retired, BASE_GROUPS["Foundation EFX"]
  * paint-booth-0-finish-metadata.js  — BASE_METADATA entries for new ids
  * paint-booth-0-finish-tags.js      — FINISH_TAGS for new ids
  * scripts/runtime-sync-manifest.json — ship the module
Idempotent: every patch checks whether it is already applied.
"""
from __future__ import annotations
import json, re, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, r"C:\Users\RICKY'~1\AppData\Local\Temp\claude\C--DRIVE-E-BACKUP-Shokker-Paint-Booth-Gold-to-Platinum\98e16c45-3af3-4c65-b78e-127ca6e6a41e\scratchpad")
from spbedit import Editor  # noqa: E402

# import ROWS without booting the engine (the module imports kits only)
import engine.paint_v2.foundation_efx_2026 as X  # noqa: E402

TAGS = {
    "efx_holo_flake": ["holographic", "flake", "glitter", "rainbow", "sparkle"],
    "efx_holo_prism_cells": ["holographic", "cells", "rainbow", "prism"],
    "efx_holo_scan": ["holographic", "scanline", "moire", "rainbow"],
    "efx_micro_glitter": ["glitter", "sparkle", "flake", "chrome"],
    "efx_chunky_flake": ["flake", "metallic", "candy", "sparkle"],
    "efx_glass_flake": ["glass", "flake", "sparkle", "clear"],
    "efx_gold_leaf": ["gold", "leaf", "metallic", "luxury"],
    "efx_surface_rust": ["rust", "weathered", "orange", "aged"],
    "efx_rust_through": ["rust", "weathered", "steel", "aged", "pitted"],
    "efx_peeling_clear": ["weathered", "clearcoat", "peeling", "aged"],
    "efx_sun_faded": ["weathered", "faded", "sun", "aged"],
    "efx_galvanized_spangle": ["galvanized", "zinc", "metal", "spangle"],
    "efx_verdigris": ["patina", "copper", "green", "weathered"],
    "efx_soot_wash": ["soot", "black", "weathered", "smoke"],
    "efx_salt_bloom": ["salt", "white", "crystal", "weathered"],
    "efx_hammered": ["hammered", "metal", "dents", "industrial"],
    "efx_cast_iron": ["iron", "cast", "dark", "industrial", "rough"],
    "efx_knurled": ["knurled", "metal", "machined", "industrial"],
    "efx_engine_turned": ["jeweled", "machined", "metal", "swirl"],
    "efx_sandblasted": ["blasted", "metal", "matte", "industrial"],
    "efx_wire_brushed": ["brushed", "metal", "scratches", "industrial"],
    "efx_mill_scale": ["steel", "scale", "dark", "industrial"],
    "efx_orange_peel": ["gloss", "orange peel", "texture"],
    "efx_crackle_lacquer": ["crackle", "lacquer", "craze", "vintage"],
    "efx_wrinkle_coat": ["wrinkle", "powder", "texture", "industrial"],
    "efx_raku_glaze": ["ceramic", "glaze", "copper", "crackle"],
    "efx_powder_texture": ["powder", "texture", "grit", "industrial"],
    "efx_terrazzo": ["terrazzo", "stone", "chips", "floor"],
    "efx_leather_grain": ["leather", "grain", "pebble", "texture"],
    "efx_rain_beads": ["water", "rain", "beads", "gloss"],
    "efx_snow_crust": ["snow", "white", "frost", "sparkle"],
    "efx_nacre": ["pearl", "nacre", "iridescent", "shell"],
}


def main():
    rows = X.ROWS
    by_id = X.BY_ID
    kept = list(X.KEPT)

    # ── registry merge ────────────────────────────────────────────────────────
    e = Editor(str(ROOT / "engine/base_registry_data.py"))
    marker = "# FOUNDATION EFX shelf (owner 2026-09-03, Phase B)"
    if marker not in e.s:
        anchor = "BASE_REGISTRY.update(ENHANCED_FOUNDATION_EXOTIC)\n"
        assert e.s.count(anchor) == 1
        e.rep(anchor, anchor + f'''
{marker}: textured foundations that carry paint AND spec.
# Built by engine/paint_v2/foundation_efx_2026.py; overrides the reworked efx_* ids and
# chalky_base, never the locked keeper (efx_holographic_drift). Import failure degrades to
# the legacy EFX renderers so the picker never goes dark.
try:
    from engine.paint_v2.foundation_efx_2026 import install as _install_foundation_efx
    _install_foundation_efx(BASE_REGISTRY)
except Exception as _efx2_exc:  # pragma: no cover
    _logging.getLogger(__name__).warning("FOUNDATION EFX install failed: %s", _efx2_exc)
''')
        e.save()
    else:
        print("registry merge already present")

    # ── JS catalog: BASES entries ─────────────────────────────────────────────
    e = Editor(str(ROOT / "paint-booth-0-finish-data.js"))
    existing_ids = set(re.findall(r'\{ id: "([^"]+)"', e.s))
    new_lines = []
    for r in rows:
        fid = r["fid"]
        desc = r["desc"].replace('"', "'")
        line = f'    {{ id: "{fid}", name: "{r["name"]}", desc: "{desc}", swatch: "{r["swatch"]}", colorSafe: true }},\n'
        m = re.search(r'^[ \t]*\{ id: "%s",[^\n]*\n' % re.escape(fid), e.s, re.M)
        if m:
            if m.group(0) != line:
                e.s = e.s.replace(m.group(0), line, 1)
                e.n += 1
        else:
            new_lines.append(line)
    if new_lines:
        anchor = re.search(r'^[ \t]*\{ id: "efx_frost_mercury_duo",[^\n]*\n', e.s, re.M).group(0)
        e.rep(anchor, anchor + "    // FOUNDATION EFX shelf (Phase B, 2026-09-03) — new textured foundations\n" + "".join(new_lines))
    # group line
    order = kept + [r["fid"] for r in rows]
    gline = re.search(r'^    "Foundation EFX": \[[^\n]*\n', e.s, re.M).group(0)
    newg = '    "Foundation EFX": [%s],\n' % ", ".join('"%s"' % i for i in order)
    if gline != newg:
        e.rep(gline, newg)
    e.save()

    # ── metadata + tags for ids that lack them ────────────────────────────────
    e = Editor(str(ROOT / "paint-booth-0-finish-metadata.js"))
    tmpl = '''  "%s": {
    "family": "Foundation",
    "browserGroup": "Materials",
    "browserSection": "Foundation EFX",
    "hero": false,
    "featured": false,
    "advanced": false,
    "utility": false,
    "readability": 80,
    "distinctness": 74,
    "sortPriority": 55,
    "score": 80
  },
'''
    anchor = re.search(r'^  "f_metallic": \{\n', e.s, re.M).group(0)
    add = "".join(tmpl % r["fid"] for r in rows if ('"%s": {' % r["fid"]) not in e.s)
    if add:
        e.rep(anchor, add + anchor)
        e.save()
    else:
        print("metadata already present")
    e = Editor(str(ROOT / "paint-booth-0-finish-tags.js"))
    anchor = '    "f_metallic": ["flake", "matte", "metallic"],\n'
    add = "".join('    "%s": %s,\n' % (fid, json.dumps(tags)) for fid, tags in TAGS.items() if ('"%s":' % fid) not in e.s)
    if add:
        e.rep(anchor, anchor + add)
        e.save()
    else:
        print("tags already present")

    # ── sync manifest ─────────────────────────────────────────────────────────
    mp = ROOT / "scripts/runtime-sync-manifest.json"
    raw = mp.read_bytes().decode("utf-8")
    if "engine/paint_v2/foundation_efx_2026.py" not in raw:
        anchor = '    "engine/paint_v2/foundation_enhanced.py",\n'
        assert raw.count(anchor) == 1
        raw = raw.replace(anchor, anchor + '    "engine/paint_v2/foundation_efx_2026.py",\n')
        mp.write_bytes(raw.encode("utf-8"))
        print("manifest: module added")
    else:
        print("manifest already lists the module")


if __name__ == "__main__":
    main()
