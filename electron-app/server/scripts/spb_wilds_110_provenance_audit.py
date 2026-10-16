"""Report whether every FRACTURED WILDS ID has an independent physical source.

SPB-105 / Wilds rebuild guard, 2026-08-25.  This is deliberately a *debt
report*, not an approval metric: an M7 score or a unique colourway cannot make
a finish independent.  The report proves the true 110-ID census, identifies
legacy shared-composer families, and verifies the root/package mirrors for the
owner-reviewed independent overrides.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EXPANSIONS = ROOT / "engine" / "expansions"
PACKAGE = ROOT / "electron-app" / "server" / "engine" / "expansions"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# These twelve are the only native-screened experimental escape hatches from the
# 110 legacy composers at this checkpoint.  Adding an ID here requires its own
# full-size visual/material/performance evidence; it is not a whitelist for a
# palette variation.
INDEPENDENT_OVERRIDES = {
    "fmo_morpho_blue": "fractured_wilds_morpho_bio_independent_w2_2026.py",
    "fpe_amber_plankton": "fractured_wilds_petri_independent_w7_2026.py",
    "fpe_violet_garden": "fractured_wilds_violet_growthsheet_i1_2026.py",
    "fmo_soap_bubble": "fractured_wilds_soap_minimal_i1_2026.py",
    "fmo_nacre_brick": "fractured_wilds_nacre_brick_i1_2026.py",
    "fpe_cyan_spineball": "fractured_wilds_cyan_spineball_cage_i1_2026.py",
    "fpe_cyan_colony": "fractured_wilds_cyan_colony_reaction_i2_2026.py",
    "fc_dragon_hex_glass": "fractured_wilds_dragon_scute_i1_2026.py",
    "fc_bark_camo": "fractured_wilds_bark_cambium_i1_2026.py",
    "fc_claw_rake": "fractured_wilds_claw_cuticle_i2_2026.py",
    "fmo_oil_slick": "fractured_wilds_oil_slick_advection_i1_2026.py",
    "fmo_scarab_horn": "fractured_wilds_scarab_horn_bouligand_i1_2026.py",
    "fc_snakeskin": "fractured_wilds_snakeskin_shed_i2_2026.py",
    "fc_sasquatch_fur": "fractured_wilds_sasquatch_follicle_i3_2026.py",
    "fc_gator_hide": "fractured_wilds_gator_osteoderm_i2_2026.py",
    "fc_feathered_wing": "fractured_wilds_feathered_vane_closecrop_i2_2026.py",
    "fmo_owl_eye": "fractured_wilds_owl_eye_ocellus_i1_2026.py",
    "fmo_raven_flash": "fractured_wilds_raven_nematic_i1_2026.py",
    "fmo_moonstone_adular": "fractured_wilds_moonstone_adular_relief_i1_2026.py",
    "fc_batwing": "fractured_wilds_batwing_membrane_asset_i2_2026.py",
    "fc_toad_skin": "fractured_wilds_toad_skin_asset_i3_2026.py",
    "fc_antler_bone": "fractured_wilds_antler_bone_asset_i2_2026.py",
    "fc_dorsal_ridge": "fractured_wilds_dorsal_ridge_asset_i2_2026.py",
    "fc_mossy_stone": "fractured_wilds_mossy_stone_asset_i2_2026.py",
    "fc_will_o_wisp": "fractured_wilds_will_o_wisp_asset_i2_2026.py",
    "fc_crackle_eyeshine_glass": "fractured_wilds_crackle_eyeshine_asset_i2_2026.py",
    "fmo_sunset_moth": "fractured_wilds_sunset_moth_asset_i2_2026.py",
    "fmo_luna_dust": "fractured_wilds_luna_dust_asset_i2_2026.py",
    "fmo_atlas_wing": "fractured_wilds_atlas_wing_asset_i2_2026.py",
    "fmo_ulysses_flash": "fractured_wilds_ulysses_flash_asset_i2_2026.py",
    "fmo_black_opal": "fractured_wilds_black_opal_asset_i2_2026.py",
    "fmo_black_pearl": "fractured_wilds_black_pearl_asset_i2_2026.py",
    "fmo_bornite_patina": "fractured_wilds_bornite_oxide_asset_i2_2026.py",
    "fc_quill_bristle": "fractured_wilds_quill_bristle_asset_i2_2026.py",
    "fmo_hummingbird_gorget": "fractured_wilds_hummingbird_gorget_asset_i2_2026.py",
    "fmo_alexandrite_dusk": "fractured_wilds_alexandrite_dusk_asset_i2_2026.py",
    "fmo_paua_storm": "fractured_wilds_paua_storm_asset_i2_2026.py",
    "fmo_chalcopyrite": "fractured_wilds_chalcopyrite_asset_i2_2026.py",
    "fmo_oil_beetle": "fractured_wilds_oil_beetle_asset_i2_2026.py",
    "fmo_sunstone_glitter": "fractured_wilds_sunstone_glitter_asset_i2_2026.py",
    "fc_bog_murk": "fractured_wilds_bog_murk_asset_i2_2026.py",
    "fbl_coral_stamen": "fractured_wilds_coral_stamen_asset_i2_2026.py",
    "fpe_violet_chains": "fractured_wilds_violet_chains_asset_i2_2026.py",
    "fmo_spectrolite_vein": "fractured_wilds_spectrolite_vein_asset_i2_2026.py",
    "fbl_pink_rose": "fractured_wilds_pink_rose_asset_i2_2026.py",
    "fbl_lilac_stamen": "fractured_wilds_lilac_stamen_asset_i2_2026.py",
    "fbl_white_pollen": "fractured_wilds_moon_pollen_asset_i2_2026.py",
    "fpe_lime_diatom": "fractured_wilds_lime_diatom_asset_i2_2026.py",
    "fbl_coral_vine": "fractured_wilds_coral_vine_asset_i2_2026.py",
    "fc_coarse_hide": "fractured_wilds_coarse_hide_asset_i2_2026.py",
    "fc_eyeshine": "fractured_wilds_eyeshine_asset_i2_2026.py",
    "fc_webbed_membrane": "fractured_wilds_webbed_membrane_asset_i3_2026.py",
    "fc_hide_scale_glass": "fractured_wilds_hide_scale_glass_asset_i3_2026.py",
    "fmo_glasswing": "fractured_wilds_glasswing_asset_i2_2026.py",
    "fpe_magenta_bloom": "fractured_wilds_magenta_bloom_asset_i2_2026.py",
    "fmo_ground_beetle": "fractured_wilds_ground_beetle_asset_i2_2026.py",
    "fmo_fire_agate": "fractured_wilds_fire_agate_asset_i3_2026.py",
    "fmo_magpie_wing": "fractured_wilds_magpie_wing_asset_i2_2026.py",
    "fmo_swallowtail": "fractured_wilds_swallowtail_flash_asset_i2_2026.py",
    "fmo_weevil_pit": "fractured_wilds_weevil_pit_asset_i2_2026.py",
    "fmo_ladybird_dome": "fractured_wilds_ladybird_dome_asset_i2_2026.py",
    "fmo_jewel_scarab": "fractured_wilds_jewel_scarab_asset_i2_2026.py",
    "fbl_pink_stamen": "fractured_wilds_pink_stamen_asset_i2_2026.py",
    "fpe_lime_culture": "fractured_wilds_lime_culture_asset_i2_2026.py",
    "fpe_amber_diatom": "fractured_wilds_amber_diatom_asset_i2_2026.py",
    "fmo_mussel_shell": "fractured_wilds_mussel_shell_asset_i2_2026.py",
    "fmo_monarch_vein": "fractured_wilds_monarch_vein_asset_i2_2026.py",
    "fmo_ammolite_skin": "fractured_wilds_ammolite_skin_asset_i2_2026.py",
    "fmo_pearl_oyster": "fractured_wilds_pearl_oyster_asset_i2_2026.py",
    "fpe_violet_frustule": "fractured_wilds_violet_frustule_asset_i2_2026.py",
    "fpe_amber_agar": "fractured_wilds_amber_agar_asset_i2_2026.py",
    "fbl_butter_pollen": "fractured_wilds_butter_pollen_asset_i5_2026.py",
    "fpe_violet_membrane": "fractured_wilds_violet_membrane_asset_i3_2026.py",
    "fpe_lime_mold": "fractured_wilds_lime_mold_asset_i2_2026.py",
    "fpe_cyan_mold": "fractured_wilds_cyan_mold_asset_i2_2026.py",
    "fmo_emperor_scale": "fractured_wilds_emperor_scale_asset_i3_2026.py",
    "fmo_tiger_beetle": "fractured_wilds_tiger_beetle_asset_i3_2026.py",
    "fmo_foam_film": "fractured_wilds_foam_film_asset_i3_2026.py",
    "fmo_cassowary_quill": "fractured_wilds_cassowary_quill_asset_i3_2026.py",
    "fmo_labradorite": "fractured_wilds_labradorite_asset_i4_2026.py",
    "fpe_magenta_radiolaria": "fractured_wilds_magenta_radiolaria_asset_i3_2026.py",
    "fpe_lime_chains": "fractured_wilds_lime_chains_asset_i3_2026.py",
    "fpe_amber_moldring": "fractured_wilds_amber_moldring_asset_i3_2026.py",
    "fmo_peacock_eye": "fractured_wilds_peacock_eye_asset_i1_2026.py",
    "fmo_stag_carapace": "fractured_wilds_stag_carapace_asset_i1_2026.py",
    "fmo_firefly_shell": "fractured_wilds_firefly_shell_asset_i1_2026.py",
    "fbl_magenta_whorl": "fractured_wilds_magenta_whorl_asset_i1_2026.py",
    "fpe_magenta_mosaic": "fractured_wilds_magenta_mosaic_asset_i1_2026.py",
    "fbl_butter_mosaic": "fractured_wilds_butter_mosaic_asset_i1_2026.py",
    "fmo_duck_speculum": "fractured_wilds_duck_speculum_asset_i1_2026.py",
    "fmo_abalone_drift": "fractured_wilds_abalone_drift_asset_i1_2026.py",
    "fmo_pigeon_neck": "fractured_wilds_pigeon_neck_asset_i1_2026.py",
    "fmo_chrysina_gold": "fractured_wilds_chrysina_gold_asset_i2_2026.py",
    "fmo_mother_of_pearl": "fractured_wilds_mother_of_pearl_asset_i1_2026.py",
    "fmo_sunbird_throat": "fractured_wilds_sunbird_throat_asset_i2_2026.py",
    "fbl_lilac_vine": "fractured_wilds_lilac_vine_asset_i2_2026.py",
    "fbl_leafvine_drape": "fractured_wilds_leafvine_drape_asset_i2_2026.py",
    "fbl_butter_whorl": "fractured_wilds_butter_whorl_asset_i1_2026.py",
    "fpe_cyan_membrane": "fractured_wilds_cyan_membrane_asset_i3_2026.py",
    "fbl_leaf_whorl": "fractured_wilds_leaf_whorl_asset_i1_2026.py",
    "fbl_pink_pollen": "fractured_wilds_pink_pollen_spray_i1_2026.py",
    "fmo_grackle_oil": "fractured_wilds_grackle_oil_asset_i4_2026.py",
    "fmo_starling_sheen": "fractured_wilds_starling_sheen_asset_i4_2026.py",
    "fbl_lilac_rose": "fractured_wilds_lilac_rose_asset_i2_2026.py",
    "fbl_white_whorl": "fractured_wilds_white_whorl_asset_i2_2026.py",
    "fbl_magenta_mosaic": "fractured_wilds_magenta_mosaic_asset_i2_2026.py",
    "fbl_blush_rose": "fractured_wilds_blush_rose_asset_i2_2026.py",
    "fbl_coral_cluster": "fractured_wilds_coral_cluster_asset_i4_2026.py",
    "fbl_magenta_pollen": "fractured_wilds_magenta_pollen_asset_i2_2026.py",
    "fpe_magenta_plankton": "fractured_wilds_magenta_plankton_asset_i3_2026.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _declared_ids() -> dict[str, tuple[str, ...]]:
    # Importing makes this audit use the same declarations as the real 110
    # registry, rather than a hand-maintained list that can drift.
    from engine.expansions import (fractured_bloom_2026 as bloom,
                                  fractured_morpho_2026 as morpho,
                                  fractured_petri_2026 as petri,
                                  fractured_themes_2026 as cryptid)
    return {
        "cryptid": tuple(cryptid.CRYPTID), "morpho": tuple(morpho.ALL),
        "bloom": tuple(bloom._BLOOM), "petri": tuple(petri._PETRI),
    }


def main() -> int:
    groups = _declared_ids()
    all_ids = tuple(fid for ids in groups.values() for fid in ids)
    if len(all_ids) != 110 or len(set(all_ids)) != 110:
        raise SystemExit(f"Wilds registry must contain 110 unique IDs, got {len(all_ids)}/{len(set(all_ids))}")

    missing_sources, drift = [], []
    for fid, filename in INDEPENDENT_OVERRIDES.items():
        root_file, package_file = EXPANSIONS / filename, PACKAGE / filename
        if not root_file.is_file() or not package_file.is_file():
            missing_sources.append({"id": fid, "file": filename})
        elif _sha256(root_file) != _sha256(package_file):
            drift.append({"id": fid, "file": filename})
    adapter_root = EXPANSIONS / "fractured_wilds_accepted_2026.py"
    adapter_package = PACKAGE / "fractured_wilds_accepted_2026.py"
    if not adapter_root.is_file() or not adapter_package.is_file() or _sha256(adapter_root) != _sha256(adapter_package):
        drift.append({"id": "adapter", "file": adapter_root.name})

    records = []
    for family, ids in groups.items():
        legacy = "signature-composer" if family in ("cryptid", "morpho") else "FineFractureKit-profile"
        for fid in ids:
            if fid in INDEPENDENT_OVERRIDES:
                records.append({"id": fid, "family": family, "source": "independent-override",
                                "file": INDEPENDENT_OVERRIDES[fid]})
            else:
                records.append({"id": fid, "family": family, "source": legacy,
                                "file": None})
    report = {
        "purpose": "debt audit only; no visual or M7 acceptance is inferred",
        "counts": {family: len(ids) for family, ids in groups.items()},
        "total": len(all_ids), "independent_override_count": len(INDEPENDENT_OVERRIDES),
        "legacy_shared_composer_count": len(all_ids) - len(INDEPENDENT_OVERRIDES),
        "missing_sources": missing_sources, "mirror_drift": drift,
        "records": records,
    }
    print(json.dumps(report, indent=2))
    return 1 if missing_sources or drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
