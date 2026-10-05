#!/usr/bin/env python3
"""Archive frozen V1 MONEY SHOKK bake-off thumbnails for COLOR_CHANGE_BREAKTHROUGH.html."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.paint_v2.money_shokk import _make_money_shokk
from scripts.spb_rate_portal_lib import SEED, TINT_CC, TINT_M, TINT_R, _spec_array, _tint_channel

SRC = ROOT / "_rate_money_shokk_thumbs"
DEST = ROOT / "docs" / "color-change-breakthrough-reference" / "money_shokk_v1"
SIZE = 512
SUFFIXES = ("_paint", "", "_M", "_R", "_CC")

COMPOSER_V1 = [
    dict(finish_id="msh_canary_coffin", seed_off=9700, pf_id="pf_bright_canary_glass", spec_id="coffin_nail_rust", hue_deg=-167.0, spec_scale=0.40, sat_adj=0.0, bri_adj=5.0),
    dict(finish_id="msh_magenta_widow", seed_off=9701, pf_id="pf_bright_magenta_arc", spec_id="widow_web_venom", hue_deg=120.0, spec_scale=0.38, sat_adj=0.0, bri_adj=4.0),
    dict(finish_id="msh_cerulean_cobra", seed_off=9702, pf_id="pf_bright_cerulean_pop", spec_id="king_cobra_coil", hue_deg=-95.0, spec_scale=0.42, sat_adj=0.0, bri_adj=6.0),
    dict(finish_id="msh_hyperpink_torii", seed_off=9704, pf_id="pf_bright_hyperpink", spec_id="torii_ember_lattice", hue_deg=-115.0, spec_scale=0.40, sat_adj=0.0, bri_adj=5.0),
    dict(finish_id="msh_seafoam_piranha", seed_off=9705, pf_id="pf_bright_seafoam_bolt", spec_id="piranha_frenzy_current", hue_deg=145.0, spec_scale=0.37, sat_adj=0.0, bri_adj=4.0),
    dict(finish_id="msh_peach_jellyshock", seed_off=9707, pf_id="pf_bright_peach_fizz", spec_id="jellyshock_drift", hue_deg=125.0, spec_scale=0.39, sat_adj=0.0, bri_adj=6.0),
    dict(finish_id="msh_daffodil_bayou", seed_off=9708, pf_id="pf_bright_solar_daffodil", spec_id="bayou_smoke_script", hue_deg=-172.0, spec_scale=0.36, sat_adj=0.0, bri_adj=5.0),
]
V1_COMPOSER_IDS = {r["finish_id"] for r in COMPOSER_V1}

ALL_IDS = [
    "msh_canary_coffin", "msh_magenta_widow", "msh_cerulean_cobra", "msh_lime_scorpion", "msh_hyperpink_torii",
    "msh_seafoam_piranha", "msh_orchid_kintsugi", "msh_peach_jellyshock", "msh_daffodil_bayou", "msh_neonice_rising",
    "mshc_tigerblood_voltage", "mshc_oxblood_seigaiha", "mshc_emerald_sharkbite", "mshc_amber_panther", "mshc_violet_kyoto",
    "mshc_acid_hornet", "mshc_oni_orchid_glass", "mshc_copper_jubilee", "mshc_canary_widow_redux", "mshc_rosethorn_bonsai",
    "msha_canary_gris_gris", "msha_emerald_brocade", "msha_fuji_neon_crest", "msha_volcanic_croc", "msha_cherry_blossom_flux",
    "msha_waxen_voodoo", "msha_hyperpink_threads", "msha_peach_burlap", "msha_seafoam_charm", "msha_solar_moss",
    "mshx_blueprint_jackpot", "mshx_venom_cashmere", "mshx_glacier_pinkslip", "mshx_lime_afterburner", "mshx_miami_blacklight",
    "mshx_royal_sunstroke", "mshx_kintsugi_ransom", "mshx_coral_sharkskin", "mshx_dover_jackpot", "mshx_prism_tipjar",
]


def write_png(rgb_uint8: np.ndarray, path: Path) -> None:
    try:
        import cv2

        cv2.imwrite(str(path), rgb_uint8[:, :, [2, 1, 0]])
    except Exception:
        from PIL import Image

        Image.fromarray(rgb_uint8, mode="RGB").save(path)


def render_custom_v1(row: dict) -> None:
    fid = row["finish_id"]
    cfg = {k: v for k, v in row.items() if k != "finish_id"}
    cfg["finish_id"] = fid
    cfg["desc"] = ""
    paint_fn, spec_fn = _make_money_shokk(**cfg)
    shape = (SIZE, SIZE)
    mask = np.ones(shape, dtype=np.float32)
    neutral = np.full((SIZE, SIZE, 3), 0.5, dtype=np.float32)
    paint_rgb = paint_fn(neutral, shape, mask, SEED, 1.0, np.ones(shape, dtype=np.float32))
    spec_u8 = _spec_array(spec_fn(shape, SEED, 1.0, 180.0, 80.0), shape)
    paint_u8 = (np.clip(paint_rgb[:, :, :3], 0, 1) * 255).astype(np.uint8)
    spec_f = spec_u8.astype(np.float32)
    if float(spec_f.max()) > 1.5:
        spec_f /= 255.0
    spec_f = np.clip(spec_f, 0, 1)
    M_arr, R_arr, CC_arr = spec_f[:, :, 0], spec_f[:, :, 1], spec_f[:, :, 2]
    spec_rgb = (spec_f * 255).astype(np.uint8)
    write_png(paint_u8, DEST / f"{fid}_paint.png")
    write_png(spec_rgb, DEST / f"{fid}.png")
    write_png(_tint_channel(M_arr, TINT_M), DEST / f"{fid}_M.png")
    write_png(_tint_channel(R_arr, TINT_R), DEST / f"{fid}_R.png")
    write_png(_tint_channel(CC_arr, TINT_CC), DEST / f"{fid}_CC.png")


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    copied = rerendered = 0
    for fid in ALL_IDS:
        if fid in V1_COMPOSER_IDS:
            render_custom_v1(next(r for r in COMPOSER_V1 if r["finish_id"] == fid))
            rerendered += 1
            continue
        for suf in SUFFIXES:
            src = SRC / f"{fid}{suf}.png"
            if src.exists():
                shutil.copy2(src, DEST / f"{fid}{suf}.png")
                copied += 1
    manifest = {
        "version": "v1",
        "baked": "2026-05-28",
        "count": len(ALL_IDS),
        "composer_v1_rerendered": sorted(V1_COMPOSER_IDS),
        "note": "Frozen V1 bake-off archive for COLOR_CHANGE_BREAKTHROUGH.html. Composer REBUILD entries restored from pre-V2 recipes.",
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"archive money_shokk_v1: ids={len(ALL_IDS)} copied={copied} composer_rerendered={rerendered} -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
