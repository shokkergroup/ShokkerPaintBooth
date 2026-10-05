"""Focused verification for the RATE10 Ricky reference batch 2 overlays."""
from __future__ import annotations

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.spec_patterns import PATTERN_CATALOG


IDS = [
    "king_cobra_coil",
    "widow_web_venom",
    "tiger_fang_fracture",
    "scorpion_ember_hex",
    "hornet_swarm_static",
    "croc_delta_armor",
    "panther_shadow_claw",
    "piranha_frenzy_current",
    "jellyshock_drift",
    "sharkbite_riptide",
    "bayou_hex_burlap",
    "candle_wax_veve",
    "pins_and_thread",
    "swamp_charm_patina",
    "mojo_bag_grain",
    "midnight_gris_gris",
    "bayou_smoke_script",
    "coffin_nail_rust",
    "root_doctor_copper",
    "spanish_moss_static",
    "seigaiha_chrome",
    "sakura_static",
    "kintsugi_rift",
    "torii_ember_lattice",
    "oni_veil_mosaic",
    "shogun_scale_brocade",
    "kyoto_lantern_filigree",
    "bonsai_drift_circuit",
    "fuji_frost_crest",
    "rising_sun_prismwave",
]


def main() -> int:
    bad = []
    times = []
    print("id,M_std,R_std,CC_std,ms2048")
    for finish_id in IDS:
        t0 = time.perf_counter()
        arr = PATTERN_CATALOG[finish_id]((2048, 2048), 777, 1.0)
        ms = (time.perf_counter() - t0) * 1000.0
        stds = [float(arr[:, :, idx].std() * 255.0) for idx in range(3)]
        times.append(ms)
        print(f"{finish_id},{stds[0]:.1f},{stds[1]:.1f},{stds[2]:.1f},{ms:.0f}")
        if min(stds) < 20.0:
            bad.append((finish_id, stds))
    print(f"bad={bad}")
    print(f"max_ms={max(times):.0f} avg_ms={sum(times) / len(times):.0f}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
