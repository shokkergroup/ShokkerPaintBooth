"""Build FORBIDDEN DRAGON cultural paint plates.

Scales the source dragon-brocade art (any size) to the canonical 2048 canvas,
writes a clean `{fd_id}.png` + `jpg_2048/{fd_id}.jpg`, and a manifest.json.

No spec plates are baked here — the runtime module
`engine/paint_v2/cultural_forbidden_dragon.py` derives a rich, decorrelated
M/R/CC spec FROM the paint image at render time via the proven Viva Mexico
sculptor (gold->metal, chroma->spec triplets, edges->ridges, micro-grit). That
keeps the spec always in sync with the art and means each new dragon is a pure
drop-in.

Usage:  python scripts/build_cultural_forbidden_dragon.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "reference_textures" / "cultural" / "forbidden_dragon"
JPG = ASSET / "jpg_2048"
SIZE = 2048

# (source display filename stem, finish_id, display name, picker swatch)
FINISHES = [
    ("Azure Celestial",    "fd_azure_celestial", "Azure Celestial",  "#2a52be"),
    ("Vermilion Fire",     "fd_vermilion_fire",  "Vermilion Fire",   "#e3431f"),
    ("Abyssal Sea",        "fd_abyssal_sea",     "Abyssal Sea",      "#1f7a6b"),
    ("Imperial Gold",      "fd_imperial_gold",   "Imperial Gold",    "#d4af37"),
    ("Storm Black",        "fd_storm_black",     "Storm Black",      "#2c3e50"),
    ("Jade Empress",       "fd_jade_empress",    "Jade Empress",     "#2e8b57"),
    ("Frost Emperor",      "fd_frost_emperor",   "Frost Emperor",    "#9fd3e0"),
    ("Bronze Relic",       "fd_bronze_relic",    "Bronze Relic",     "#8c6a3f"),
    ("Pearl Chaser",       "fd_pearl_chaser",    "Pearl Chaser",     "#c8102e"),
    ("Dragon and Phoenix", "fd_dragon_phoenix",  "Dragon & Phoenix", "#b5432f"),
    # ── FORBIDDEN BEASTS (11–20) ──
    ("Phoenix Fenghuang",   "fd_phoenix_fenghuang",   "Phoenix Fenghuang",   "#d4502a"),
    ("Jade Qilin",          "fd_jade_qilin",          "Jade Qilin",          "#2e8b57"),
    ("Guardian Foo Lion",   "fd_guardian_foo_lion",   "Guardian Foo Lion",   "#b8252b"),
    ("Vermilion Bird",      "fd_vermilion_bird",      "Vermilion Bird",      "#e0401e"),
    ("Black Tortoise",      "fd_black_tortoise",      "Black Tortoise",      "#20413a"),
    ("White Tiger Baihu",   "fd_white_tiger_baihu",   "White Tiger Baihu",   "#c9a84a"),
    ("Crane Garden",        "fd_crane_garden",        "Crane Garden",        "#9cc5a1"),
    ("Koi Ascension",       "fd_koi_ascension",       "Koi Ascension",       "#1b3fa0"),
    ("Pixiu Fortune",       "fd_pixiu_fortune",       "Pixiu Fortune",       "#b8860b"),
    ("Golden Toad Jinchan", "fd_golden_toad_jinchan", "Golden Toad Jinchan", "#c8881f"),
]


def main() -> int:
    JPG.mkdir(parents=True, exist_ok=True)
    finishes = []
    for stem, fid, name, swatch in FINISHES:
        src = ASSET / f"{stem}.png"
        if not src.exists():
            print(f"  MISSING source: {src}")
            continue
        im = Image.open(src).convert("RGB")
        if im.size != (SIZE, SIZE):
            im = im.resize((SIZE, SIZE), Image.LANCZOS)
        im.save(ASSET / f"{fid}.png")
        im.save(JPG / f"{fid}.jpg", quality=92)
        finishes.append({
            "id": fid,
            "name": name,
            "texture": f"assets/reference_textures/cultural/forbidden_dragon/{fid}.png",
            "swatch": swatch,
            "size": [SIZE, SIZE],
        })
        print(f"  baked {fid}  ({name})")
    manifest = {"set": "FORBIDDEN DRAGON", "family": "Cultural", "finishes": finishes}
    (ASSET / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest written: {len(finishes)} finishes")
    return 0 if len(finishes) == len(FINISHES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
