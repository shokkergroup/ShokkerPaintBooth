# -*- coding: utf-8 -*-
"""Production adapters for owner-reviewable FRACTURED WILDS survivors.

SPB-WILDS rollout tick 2026-08-25. The owner authorized accepted provisional
finishes to be pushed into the experimental app as they clear native-2048
paint, independent material, determinism and performance review. This module
overrides only the IDs in ``ACCEPTED_IDS`` after the legacy 110-ID Wilds
install. Unresolved IDs keep their existing fallback, making rollout additive
and reversible.

Each adapter calls the exact isolated builder that produced the reviewed
native evidence. No shared texture composer, recolor fallback, RNG, noise or
spec substitution is introduced here; this file only provides the monolithic
runtime API, resize/mask handling and a bounded cache.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable

import cv2
import numpy as np


CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)

ACCEPTED_IDS = (
    "fmo_morpho_blue",
    "fpe_amber_plankton",
    "fpe_violet_garden",
    "fmo_soap_bubble",
    "fmo_nacre_brick",
    "fpe_cyan_spineball",
    "fpe_cyan_colony",
    "fc_dragon_hex_glass",
    "fc_bark_camo",
    "fc_claw_rake",
    "fmo_oil_slick",
    "fmo_scarab_horn",
    "fc_snakeskin",
    "fc_sasquatch_fur",
    "fc_gator_hide",
    "fc_feathered_wing",
    "fmo_owl_eye",
    "fmo_raven_flash",
    "fmo_moonstone_adular",
    "fc_batwing",
    "fc_toad_skin",
    "fc_antler_bone",
    "fc_dorsal_ridge",
    "fc_mossy_stone",
    "fc_will_o_wisp",
    "fc_crackle_eyeshine_glass",
    "fmo_sunset_moth",
    "fmo_luna_dust",
    "fmo_atlas_wing",
    "fmo_ulysses_flash",
    "fmo_black_opal",
    "fmo_black_pearl",
    "fmo_bornite_patina",
    "fc_quill_bristle",
    "fmo_hummingbird_gorget",
    "fmo_alexandrite_dusk",
    "fmo_paua_storm",
    "fmo_chalcopyrite",
    "fmo_oil_beetle",
    "fmo_sunstone_glitter",
    "fc_bog_murk",
    "fbl_coral_stamen",
    "fpe_violet_chains",
    "fmo_spectrolite_vein",
    "fbl_pink_rose",
    "fbl_lilac_stamen",
    "fbl_white_pollen",
    "fpe_lime_diatom",
    "fbl_coral_vine",
    "fc_coarse_hide",
    "fc_eyeshine",
    "fc_webbed_membrane",
    "fc_hide_scale_glass",
    "fmo_glasswing",
    "fpe_magenta_bloom",
    "fmo_ground_beetle",
    "fmo_fire_agate",
    "fmo_magpie_wing",
    "fmo_swallowtail",
    "fmo_weevil_pit",
    "fmo_ladybird_dome",
    "fmo_jewel_scarab",
    "fbl_pink_stamen",
    "fpe_lime_culture",
    "fpe_amber_diatom",
    "fmo_mussel_shell",
    "fmo_monarch_vein",
    "fmo_ammolite_skin",
    "fmo_pearl_oyster",
    "fpe_violet_frustule",
    "fpe_amber_agar",
    "fbl_butter_pollen",
    "fpe_violet_membrane",
    "fpe_lime_mold",
    "fpe_cyan_mold",
    "fmo_emperor_scale",
    "fmo_tiger_beetle",
    "fmo_foam_film",
    "fmo_cassowary_quill",
    "fmo_labradorite",
    "fpe_magenta_radiolaria",
    "fpe_lime_chains",
    "fpe_amber_moldring",
    "fmo_peacock_eye",
    "fmo_stag_carapace",
    "fmo_firefly_shell",
    "fbl_magenta_whorl",
    "fpe_magenta_mosaic",
    "fbl_butter_mosaic",
    "fmo_duck_speculum",
    "fmo_abalone_drift",
    "fmo_pigeon_neck",
    "fmo_chrysina_gold",
    "fmo_mother_of_pearl",
    "fmo_sunbird_throat",
    "fbl_lilac_vine",
    "fbl_leafvine_drape",
    "fbl_butter_whorl",
    "fpe_cyan_membrane",
    "fbl_leaf_whorl",
    "fbl_pink_pollen",
    "fmo_grackle_oil",
    "fmo_starling_sheen",
    "fbl_lilac_rose",
    "fbl_white_whorl",
    "fbl_magenta_mosaic",
    "fbl_blush_rose",
    "fbl_coral_cluster",
    "fbl_magenta_pollen",
    "fpe_magenta_plankton",
)


def _float_paint(paint: np.ndarray) -> np.ndarray:
    out = np.asarray(paint)
    if out.ndim != 3 or out.shape[2] < 3:
        raise ValueError(f"accepted Wilds paint must be HxWx3+, got {out.shape}")
    out = out[:, :, :3].astype(np.float32)
    if out.size and float(out.max()) > 1.5:
        out *= np.float32(1.0 / 255.0)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _uint8_spec(spec: np.ndarray) -> np.ndarray:
    out = np.asarray(spec)
    if out.ndim != 3 or out.shape[2] < 3:
        raise ValueError(f"accepted Wilds spec must be HxWx3+, got {out.shape}")
    return np.clip(out[:, :, :3], 0, 255).astype(np.uint8)


@lru_cache(maxsize=4)
def _accepted_authored(fid: str) -> tuple[np.ndarray, np.ndarray]:
    """Build the reviewed A paint and causal M/R/Cc at authored resolution."""
    if fid == "fmo_morpho_blue":
        from . import fractured_wilds_morpho_bio_independent_w2_2026 as module
        paint, spec = module._authored(fid)
    elif fid == "fpe_amber_plankton":
        from . import fractured_wilds_petri_independent_w7_2026 as module
        paint, spec = module._authored(fid)
    elif fid == "fpe_violet_garden":
        from . import fractured_wilds_violet_growthsheet_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_soap_bubble":
        from . import fractured_wilds_soap_minimal_i1_2026 as module
        fields = module._fields()
        paint = module._compose(fields, module.PALETTE_A, False)
        spec = module._material(fields)
    elif fid == "fmo_nacre_brick":
        from . import fractured_wilds_nacre_brick_i1_2026 as module
        paint, _coverage, maps = module._paint(False)
        spec = module._material(maps)
    elif fid == "fpe_cyan_spineball":
        from . import fractured_wilds_cyan_spineball_cage_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_cyan_colony":
        # SPB-105 / Wilds attempt 111 / 2026-08-25. Owner-test provisional:
        # deterministic reaction-diffusion pellicle, not a recolored cell/grid;
        # M7 86.5, A/B mean/p95 0.101957/0.313725, native 0.167-0.183 s;
        # collision vs. 19 survivors max paint/spec 0.153929/0.038393.
        from . import fractured_wilds_cyan_colony_reaction_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_dragon_hex_glass":
        # SPB-105 / Wilds attempt 114 / 2026-08-25. Owner-test provisional:
        # aperiodic micro-scute keratin, not a uniform hex/paver grid; M7 99.0,
        # A/B mean/p95 0.134245/0.345098, native 0.205-0.092 s; collision vs.
        # 20 survivors max paint/spec 0.132291/0.014263.
        from . import fractured_wilds_dragon_scute_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_bark_camo":
        # SPB-105 / Wilds rebuild / 2026-08-25. Provisional runtime candidate:
        # a native-screened packed cambium cross-section with irregular fine
        # tissue, phloem, mineral rims, fibres, lenticels, resin and healed
        # tears. It replaces the previous macro rail study; no legacy Wilds
        # shared compositor or palette-only variation is involved. M7 95.7;
        # native complete authored pass 1.69s. Owner review remains decisive.
        from . import fractured_wilds_bark_cambium_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_claw_rake":
        # SPB-105 / Wilds rebuild / 2026-08-25. Provisional runtime candidate:
        # a continuous fine keratin cuticle with short terminating claw cuts,
        # uplift lips, exposed troughs, healed stitches and abrasion. It avoids
        # both global scratch rails and a detached-glyph field. Native 1.53s;
        # M7 gate remains the required promotion check below.
        from . import fractured_wilds_claw_cuticle_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_oil_slick":
        # SPB-105 / Wilds attempt 132 / 2026-08-25. Owner asked for tangible
        # rollout, so this is the one previously native-screened 15-colour
        # thin-film carrier promoted for isolated M7 verification. It flips
        # physical interference order A/B and retains independently authored
        # fracture materials; legacy/shared composers are never involved.
        from . import fractured_wilds_oil_slick_advection_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_scarab_horn":
        # SPB-105 / Wilds continuation / 2026-08-25. Provisional runtime
        # candidate: a native-screened irrational Bouligand horn cross-ply
        # with attached delamination, lips, pores and hooks—not a palette
        # variation or shared Wilds compositor. Native 2.35–2.49s; isolated
        # M7 97.6. Owner review remains the only acceptance decision.
        from . import fractured_wilds_scarab_horn_bouligand_i1_2026 as module
        paint, _coverage, masks = module._paint(False)
        spec = np.stack(module._spec_maps(masks), axis=2)
    elif fid == "fc_snakeskin":
        # SPB-105 / Wilds rebuild / 2026-08-25. Provisional runtime candidate:
        # a native-screened, close-crop shedded snake epidermis built from
        # overlapping scales with independently authored rim, keel, hinge,
        # wear and glint material. This replaces the rejected macro torn-skin
        # study; it is not a Dragon Hex recolour or shared Wilds composer.
        # Native authored pass 1.05s; M7 and owner review remain promotion gates.
        from . import fractured_wilds_snakeskin_shed_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_sasquatch_fur":
        # SPB-105 / owner full-size screen 2026-08-27 rejected the literal
        # fibre micrograph. I3 is dense engineered bristle armour with banked
        # pressure, inner etches and cyan/violet/copper fracture ownership.
        # M7 moves 95.5 (legacy baseline) -> 88.4; native 2048 is 1.75-1.91s.
        # Owner eye remains final approval; provisional runtime wiring only.
        from . import fractured_wilds_sasquatch_fur_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_gator_hide":
        # SPB-105 / Wilds rebuild / 2026-08-25. Provisional runtime candidate:
        # a dense non-row-ordered osteoderm dermis: shared ownership produces
        # facet, ligament, pit, keel and healed-ligament material rather than
        # detached random scutes. It replaces the rejected sparse Scute I1;
        # native authored pass 0.21s. Isolated M7 and owner review govern it.
        from . import fractured_wilds_gator_osteoderm_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_feathered_wing":
        # SPB-105 / Wilds rebuild / 2026-08-25. Provisional runtime candidate:
        # one actual close-cropped curved feather vane, with attached barbs,
        # barbules, hooklets, cross-locks, tear gaps, powder plates and snapped
        # tips. It is not a stroke wallpaper or palette variation. Native
        # authored pass 0.33–0.37s; isolated M7 and owner review remain gates.
        from . import fractured_wilds_feathered_vane_closecrop_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_owl_eye":
        # SPB-105 / Wilds rebuild / 2026-08-25. Provisional runtime candidate:
        # one eccentric, off-centre owl ocellus with unequal superelliptic
        # layers, compressed wedges, eyelid bars, feather combs, glint cuts,
        # rupture gaps and hooked scars. It is a name-matched hierarchy, not a
        # generic swirl/recolour. Native authored pass 1.96–2.06s; M7/owner
        # review remain the promotion gate.
        from . import fractured_wilds_owl_eye_ocellus_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_raven_flash":
        # SPB-105 / owner full-size screen 2026-08-27 rejected the former
        # indistinct dark barbule field. I3 is full-bleed black flash lacquer:
        # graphite shear blades, etched grain and cyan/violet/copper optic cuts.
        # M7 moves 86.9 (legacy baseline) -> 88.2; owner eye remains final.
        from . import fractured_wilds_raven_flash_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_moonstone_adular":
        # SPB-105 / owner full-size review 2026-08-27 rejected I1's repeated
        # contour-eye basins. I3 is a full-bleed moonstone cleavage lacquer:
        # unequal packets, fine lamella abrasion, fracture lips and independent
        # M/R/Cc. Its opposed optical travel preserves the packet geometry.
        # M7 moves 85.7 (legacy baseline) -> 87.9; native pass 1.56–1.70 s.
        # Owner eye remains the final gate; static buyer thumbnails stay locked.
        from . import fractured_wilds_moonstone_adular_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_batwing":
        # SPB-105 / owner verdict 2026-08-26: I2 is photographic leather/grain,
        # not an automotive Wilds finish. Tick 2026-08-27 I4 replaces it with
        # authored tension bays, fracture inlays, stitches and dry etches.
        # Exact isolated M7 moves 92.3 (photo baseline) -> 88.8, still above
        # the owner 85 ship bar; native 2048 is 1.84–2.05s. Owner eye remains
        # the promotion authority; this runtime wiring is reversible.
        from . import fractured_wilds_batwing_livery_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_toad_skin":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional runtime
        # candidate: I2's decorative dot-over-fold carrier was rejected. This
        # close glandular dermis has continuous fine pebbled tissue, recessed
        # pores, wet creases and attached interference ridges; its versioned
        # source asset and causal M/R/Cc maps ship together. Native authored
        # pass and full-size owner review remain the promotion gates.
        from . import fractured_wilds_toad_skin_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_antler_bone":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional runtime
        # candidate: a former spinodoid/foam direction was closed because it
        # read as generic static. This close calcified material instead has
        # attached lamellae, trabecular pores, growth ridges and mineral flashes
        # with independently derived M/R/Cc. It retains a richer compressed
        # read at lower scale, while full-size owner review remains decisive.
        from . import fractured_wilds_antler_bone_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_dorsal_ridge":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # compressed, heavily serrated dorsal keratin replaces the old shared
        # carrier. It has a broad, scale-responsive hierarchy but every ridge
        # contains fine stress chips and multicolor interference filaments;
        # the causal M/R/Cc maps are not copied from another Wilds finish.
        from . import fractured_wilds_dorsal_ridge_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_mossy_stone":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # I1's lamella/rail field was rejected. I2 is a continuous encrusted
        # wet mineral with attached moss, lichen, mica and fissure responses;
        # the sourced A/B flip and independent M/R/Cc maps ship together.
        from . import fractured_wilds_mossy_stone_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_will_o_wisp":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # charged vapor-glass with attached plasma fissures replaces the closed
        # knot carrier. Its Fractured angle behavior and causal physical maps
        # are owned by this source; full-size owner review remains decisive.
        from . import fractured_wilds_will_o_wisp_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_crackle_eyeshine_glass":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # smoked optical glass, fine microcrazing and embedded reflector grains
        # replace the legacy signature carrier; its causal maps stay source-owned.
        from . import fractured_wilds_crackle_eyeshine_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_sunset_moth":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # dense sunset micro-scales with physical structural platelets; source
        # owned A/B and material maps replace the legacy shared Morpho carrier.
        from . import fractured_wilds_sunset_moth_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_luna_dust":
        from . import fractured_wilds_luna_dust_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_atlas_wing":
        from . import fractured_wilds_atlas_wing_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_ulysses_flash":
        from . import fractured_wilds_ulysses_flash_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_black_opal":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # black-opal pinfire and mineral seams provide a non-wing, non-cell
        # fractured topology with source-owned angle and material behavior.
        from . import fractured_wilds_black_opal_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_black_pearl":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # folded black nacre carries fine rib direction and distinct peacock,
        # rose and host-depth material responses rather than generic iridescence.
        from . import fractured_wilds_black_pearl_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_bornite_patina":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # granular dark peacock-ore corrosion owns its copper, host-depth and
        # blue-violet response maps; it replaces the legacy shared carrier.
        from . import fractured_wilds_bornite_oxide_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_quill_bristle":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # shaft direction, follicle/hide depth and color-bearing barbs remain
        # independently causal under the Cryptid fractured material contract.
        from . import fractured_wilds_quill_bristle_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_hummingbird_gorget":
        # SPB-105 / owner Wilds rebuild / 2026-08-26. Provisional candidate:
        # dense hooked barbules own ruby, emerald/cyan and directional material
        # response independently, replacing the legacy shared Morpho carrier.
        from . import fractured_wilds_hummingbird_gorget_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_alexandrite_dusk":
        from . import fractured_wilds_alexandrite_dusk_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_paua_storm":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independently sourced
        # fine nacre storm; not a recolour or shared Wilds spec recipe.
        from . import fractured_wilds_paua_storm_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_chalcopyrite":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent fractured
        # sulfide source, with brass, bedding and tarnish material separation.
        from . import fractured_wilds_chalcopyrite_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_oil_beetle":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent folded
        # chitin interference fields; no shared color/spec topology.
        from . import fractured_wilds_oil_beetle_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_sunstone_glitter":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent aventurine
        # source; mica, feldspar bedding and clearcoat fire are separated.
        from . import fractured_wilds_sunstone_glitter_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_bog_murk":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent peat-silt
        # source whose wet-film color response is not a shared Wilds map.
        from . import fractured_wilds_bog_murk_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_coral_stamen":
        # SPB-105 / owner full-size review 2026-08-27 rejected I2's literal
        # coral photograph. I3 is an authored coral-red stamen-fan livery:
        # black fracture roots, cyan foil cuts and separate physical ownership.
        # M7 moves 93.3 (photo baseline) -> 90.2; native 2048 is 1.93-2.07s.
        # Owner eye remains final approval; provisional runtime wiring only.
        from . import fractured_wilds_coral_stamen_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_violet_chains":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent broken-chain
        # source, with link metal, substrate roughness and cool film separated.
        from . import fractured_wilds_violet_chains_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_spectrolite_vein":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent spectral
        # feldspar source with source-derived non-shared material topology.
        from . import fractured_wilds_spectrolite_vein_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_pink_rose":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent shattered
        # rose-metal film, with foil, curled edges and interference separated.
        from . import fractured_wilds_pink_rose_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_lilac_stamen":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent fractured
        # filament source; chemical hue, bead dust and resin remain separate.
        from . import fractured_wilds_lilac_stamen_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_white_pollen":
        # SPB-105 / owner full-size review 2026-08-27: previous source is a
        # framed dot/rail field. I2 is dense pearl enamel husk drift with fine
        # platelets, graphite release seams and cyan/violet exposed foil.
        from . import fractured_wilds_white_pollen_pearldrift_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_lime_diatom":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent silica
        # spindle source; color chemistry, relief and resin remain separate.
        from . import fractured_wilds_lime_diatom_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_coral_vine":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent coral-metal
        # tendril source; chemistry, fringe relief and resin remain separate.
        from . import fractured_wilds_coral_vine_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_coarse_hide":
        # SPB-105 / owner full-size screen 2026-08-27 rejected I2's literal
        # gravel photo. I3 is engineered armor with scuff, foil and tension maps.
        # M7 moves 92.5 (photo baseline) -> 88.6; native 2048 is 1.70-1.89s.
        # Owner eye remains final approval; provisional runtime wiring only.
        from . import fractured_wilds_coarse_hide_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_eyeshine":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent nocturnal
        # reflector source; glint chemistry, relief and pigment are separate.
        from . import fractured_wilds_eyeshine_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_webbed_membrane":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent torn-film
        # source; chemistry, edge relief and embedded depth remain separate.
        from . import fractured_wilds_webbed_membrane_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_hide_scale_glass":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent cuticle-glass
        # source; chemistry, chipped relief and glass depth remain separate.
        from . import fractured_wilds_hide_scale_glass_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_glasswing":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent transparent
        # film source; chemical shift, fine relief and depth remain separate.
        from . import fractured_wilds_glasswing_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_magenta_bloom":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent crystalline
        # culture after owner rejection of lazy recolors/reused specs. Its
        # isolated M7 moves fallback/unscored -> 91.1; chemistry, growth relief
        # and resin depth remain separate.
        from . import fractured_wilds_magenta_bloom_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_ground_beetle":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: uninterrupted chitin
        # groove currents, dark resin and relief are source-specific—not a
        # recolor or recycled spec topology. Isolated M7 moves fallback/unscored
        # -> 90.4; collision and distinctness gates remain mandatory.
        from . import fractured_wilds_ground_beetle_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_fire_agate":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: Fire Agate was rebuilt
        # from rejected corrugation into source-specific ruptured botryoidal
        # mineral relief. Isolated M7 moves fallback/unscored -> 90.6; collision
        # and distinctness gates remain mandatory before it ships.
        from . import fractured_wilds_fire_agate_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_magpie_wing":
        # SPB-105 / owner full-size screen 2026-08-26 rejected I2's bristle
        # photograph. Tick 2026-08-27 I4 uses black structural lacquer, broken
        # cyan/violet/silver vane inserts and attached microbarbs instead.
        # M7 moves 91.0 (photo baseline) -> 91.8; native 2048 is 1.80–2.01s.
        # Owner eye remains final approval; provisional runtime wiring only.
        from . import fractured_wilds_magpie_wing_livery_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_swallowtail":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: source-specific ridge
        # fans, gold cross-lamellae, scale dust and resin—not a recolored wing.
        # M7 moves fallback/unscored -> 88.6; collision/distinctness are clean.
        from . import fractured_wilds_swallowtail_flash_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_weevil_pit":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: asymmetric chitin pits,
        # chipped rims and resin depth remain independent of all prior specs.
        # M7 moves fallback/unscored -> 87.8; collision/distinctness are clean.
        from . import fractured_wilds_weevil_pit_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_ladybird_dome":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: repaired scarlet enamel,
        # black resin seams, copper chips and cyan interference have their own
        # material logic, not a recolor or recycled spec. M7 moves
        # fallback/unscored -> 87.4; collision and distinctness gates are clean.
        from . import fractured_wilds_ladybird_dome_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_jewel_scarab":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: independent elytral
        # mosaic of ribbed jewel plates, fracture chips, repair seams and resin.
        # It is not a recolor or reused spec. M7 moves fallback/unscored -> 88.0;
        # full collision and distinctness gates are clean.
        from . import fractured_wilds_jewel_scarab_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_pink_stamen":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dedicated bead-tipped
        # filament bundles, binding sheets, split ends and pollen dust. Its
        # material channels are independent. M7 moves fallback/unscored -> 89.1;
        # collision and distinctness gates are clean.
        from . import fractured_wilds_pink_stamen_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_lime_culture":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: mineral microbial mats,
        # dark nutrient channels, pigment grains and gold debris—not a reused
        # Petri texture/spec. M7 moves fallback/unscored -> 89.6; collision and
        # distinctness gates are clean.
        from . import fractured_wilds_lime_culture_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_amber_diatom":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: silica combs, perforated
        # wedges, crystal spines and cyan grains are an independent Petri
        # topology and material map. M7 moves fallback/unscored -> 89.2;
        # collision and distinctness gates are clean.
        from . import fractured_wilds_amber_diatom_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_mussel_shell":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: close-cropped mussel
        # nacre has real growth laminae, repaired joins, prism chips and
        # conchiolin fractures. It keeps fine detail under scaling while its
        # larger shell courses create hierarchy; A/B and M/R/Cc are causal.
        # Native 2048 pass is 1.51-1.63 s; M7 86.2 and the full collision /
        # distinctness gates are clean.
        from . import fractured_wilds_mussel_shell_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_monarch_vein":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: monarch membrane, fine
        # overlapping scales, powder-loss patches, ruptured hooks and dark
        # biological veins—not a generic scale wallpaper. Its structural A/B
        # flip is 0.148/0.435 mean/p95 at native 2048; M7 89.3 and full
        # collision/distinctness gates are clean.
        from . import fractured_wilds_monarch_vein_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_ammolite_skin":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: fractured fossil suture
        # cuticle with calcite bridges, prism terraces and mineral remnants;
        # replaces the rejected macro chamber study. Map-conditioned A/B
        # reversal is 0.132/0.287 mean/p95; native 2048 is 1.51-1.60 s;
        # M7 90.0 and full collision/distinctness gates are clean.
        from . import fractured_wilds_ammolite_skin_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_pearl_oyster":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: rough nucleated oyster
        # accretion—aragonite skins, pearl knots, conchiolin seams, voids and
        # fractured rims—not Mussel Shell's flowing nacre courses. Native 2048
        # is 1.37-1.49 s and A/B is 0.151/0.465 mean/p95. Fallback/unscored
        # -> M7 87.1; full collision and distinctness gates are clean.
        from . import fractured_wilds_pearl_oyster_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_violet_frustule":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: broken silica valves,
        # perforated bars, crystal wedges and skeletal rings; a real shattered
        # frustule topology instead of the legacy repeated radial-disc lattice.
        # Fallback/unscored -> M7 85.8; full collision/distinctness evidence
        # is recorded with the accepted set before this candidate is committed.
        from . import fractured_wilds_violet_frustule_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_amber_agar":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: ruptured translucent agar
        # sheets, meniscus rims, embedded filament colonies and mineral dust,
        # not a recoloured cell or generic orange crack pattern. Fallback/
        # unscored -> M7 86.1; full collision/distinctness evidence is recorded
        # with the accepted set before this candidate is committed.
        from . import fractured_wilds_amber_agar_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_butter_pollen":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: owner rejected I2's
        # microscopic reading. I3 is a fractured automotive livery of honey
        # shards, ribbon tears and pinwheel bursts with causal A/B and M/R/Cc;
        # I2 M7 86.2 -> I3 98.2, collision 0/82, distinctness 0/3403.
        # SPB-105 / owner correction, 2026-08-26: I3's microscopic-botanical
        # honey/pinwheel composition was rejected. I5 is a black-and-gold
        # asymmetric motorsport livery with fractured B-angle material flip.
        # SPB-105 / owner full-size review 2026-08-27: I5 is still sparse and
        # shard-led. I8 is dense butter-gold microfoil with fine platelets,
        # brush lamellae and cyan/violet fractured seam ownership.
        from . import fractured_wilds_butter_pollen_microfoil_i8_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_violet_membrane":
        # SPB-105 / owner full-size screen 2026-08-27: I3 is photo-like foam
        # and oversized cavities. I4 is a dense technical tension-film livery:
        # fine stress striations, rupture seams and optical fold lips, not pores.
        # M7 moves 85.9 -> 86.2; native pass 1.71–1.75 s. Owner eye remains final.
        from . import fractured_wilds_violet_membrane_livery_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_lime_mold":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: mineralized lime crust,
        # hyphae, spores, fissures and nutrient voids—not generic green noise.
        # Fallback/unscored -> M7 88.7; collision and distinctness gates are
        # clean across the accepted set.
        from . import fractured_wilds_lime_mold_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_cyan_mold":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: wet cyan biofilm, dark
        # nutrient seams and crusted mineral colonies—not dry Lime Mold or foam.
        # Fallback/unscored -> M7 86.7; collision and distinctness gates are
        # clean across the accepted set.
        from . import fractured_wilds_cyan_mold_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_emperor_scale":
        # SPB-105 / owner correction, 2026-08-26: I3 was a photographic grit
        # plate, rejected at literal canvas. I5 is a generated-but-not-photo
        # fractured armor livery with independent zone/rim/fracture/polish M/R/Cc;
        # native evidence 1.38-1.40s, A/B mean/p95 0.070667/0.312105. M7 and
        # whole-catalog collision movement are recorded by the post-wire gates.
        from . import fractured_wilds_emperor_scale_livery_i5_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_tiger_beetle":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: pitted black enamel armor,
        # copper abrasion channels and cyan/violet fracture light—not another
        # generic beetle or black-gold crack map. Fallback/unscored -> M7 88.3;
        # collision and distinctness gates are clean across the accepted set.
        from . import fractured_wilds_tiger_beetle_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_foam_film":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: ruptured membrane spans,
        # drained voids, brittle rims and mineral thread debris—not bubble or
        # Voronoi wallpaper. Fallback/unscored -> M7 90.6; collision and
        # distinctness gates are clean across the accepted set.
        from . import fractured_wilds_foam_film_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_cassowary_quill":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: crossing split keratin
        # quills, striations and gritty root collars—not feather, fur or weave.
        # Fallback/unscored -> M7 90.0; collision and distinctness gates are
        # clean across the accepted set.
        from . import fractured_wilds_cassowary_quill_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_labradorite":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: graphite matrix, crushed
        # feldspar cleavage and blue-green fire planes—not regular macro tiles.
        # Prior I3 M7 84.5/rejected -> I4 M7 89.3; collision and distinctness
        # gates are clean across the accepted set.
        from . import fractured_wilds_labradorite_asset_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_magenta_radiolaria":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: broken silica lace, pores,
        # needles and cultured precipitate—not the old giant repeated mesh.
        # Fallback/unscored -> M7 91.2; collision and distinctness gates are
        # clean across the accepted set.
        from . import fractured_wilds_magenta_radiolaria_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_lime_chains":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: calcified linked tubes,
        # fused collars, wet seams and carbonate cavities—not green cell noise.
        # Fallback/unscored -> M7 89.6; collision and distinctness gates are
        # clean across the accepted set.
        from . import fractured_wilds_lime_chains_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_amber_moldring":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: torn amber agar fronts,
        # wet cavities, spore grit and fissures—not a target or orange noise.
        # Fallback/unscored -> M7 98.0 after edge repair; collision 0/82 and
        # distinctness 0/3,403 are clean across the accepted set.
        from . import fractured_wilds_amber_moldring_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_peacock_eye":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: fragmented ocelli,
        # filament wakes and black fracture channels—not eye wallpaper.
        # M7 91.3, collision 0/83 and distinctness 0/3,486; 1.89-2.03s native.
        from . import fractured_wilds_peacock_eye_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_stag_carapace":
        # SPB-105 / owner full-size screen 2026-08-27: I1 is a repeating
        # dark oval-shell field. I3 is unequal protective impact armor with
        # internal cross-scuffs and optical fracture lips—not insect glyphs.
        # M7 moves 85.2 -> 86.2; native pass 1.83–1.92 s. Owner eye remains final.
        from . import fractured_wilds_stag_carapace_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_firefly_shell":
        # SPB-105 / owner Wilds rebuild, 2026-08-26 candidate: luminous
        # apertures and black armor channels, not a glow/noise background.
        # M7 91.5, collision 0/85 and distinctness 0/3,655; 1.68-1.84s native.
        from . import fractured_wilds_firefly_shell_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_magenta_whorl":
        # SPB-105 / owner Wilds rebuild, 2026-08-26 candidate: interrupted
        # chiral collars and splinter fields—not marble or repeated spirals.
        # M7 91.0, collision 0/86 and distinctness 0/3,741; 1.47-1.59s native.
        # SPB-105 / owner full-size screen 2026-08-27: I1 is a repeated
        # circular spiral-glyph field. I3 is one fractured chiral lacquer flow
        # with fine brushed interiors, split tips and travelling foil lips.
        # M7 moves 86.1 -> 87.3; native pass 1.76–1.91 s. Owner eye remains final.
        from . import fractured_wilds_magenta_whorl_livery_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_magenta_mosaic":
        # SPB-105 / owner Wilds rebuild, 2026-08-26 candidate: split lacquer
        # plaques and foil cuts—not a grid, tile wall, or crack-map recolor.
        # M7 91.2, collision 0/87 and distinctness 0/3,828; 1.70-2.21s native.
        from . import fractured_wilds_magenta_mosaic_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_butter_mosaic":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: deliberately graphic,
        # seamless livery panels, split cuts, foil shards and pinstripes—not
        # the rejected microscopic Butter Pollen language or a grain texture.
        # M7 94.9, collision 0/88 and distinctness 0/3,916; 1.60-1.70s native.
        # SPB-105 / owner full-size screen 2026-08-27: I1 is disconnected
        # confetti and rails. I2 is fused butter-gold mica lacquer with fine
        # foil abrasion and fractured optical lips; M7 88.3 -> 90.2.
        from . import fractured_wilds_butter_mosaic_livery_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_duck_speculum":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dense structural-color
        # flight-barb livery with engraved vane rows and irregular foil shards,
        # not a literal bird, generic carbon weave, or grain-texture rescue.
        # M7 91.6, collision 0/89 and distinctness 0/4,005; 1.49-1.87s native.
        from . import fractured_wilds_duck_speculum_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_abalone_drift":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: unequal nacre plates,
        # mineral-inlay rivers and contained opal flips—not a generic crack map,
        # cell field, literal shell photo, or noise-driven material texture.
        # M7 93.1, collision 0/90 and distinctness 0/4,095; 1.55-1.86s native.
        from . import fractured_wilds_abalone_drift_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_pigeon_neck":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: counter-curved collar
        # layers, engraved ribs and fractured inlay—not Duck's diagonal barbs,
        # a radial target, grid, repeated stamp, or grain-texture rescue.
        # M7 90.7, collision 0/91 and distinctness 0/4,186; 1.61-1.76s native.
        from . import fractured_wilds_pigeon_neck_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_chrysina_gold":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: emerald/gold mirror
        # facets, engraved interiors and hard fissure channels—not panel
        # wallpaper, cells, generic crack map, or a grain-texture rescue.
        # M7 92.7, collision 0/92 and distinctness 0/4,278; 1.67-1.94s native.
        from . import fractured_wilds_chrysina_gold_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_mother_of_pearl":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dense pale pearl
        # lamellae, etched interiors, broken ends and opal fracture lips—not
        # a recolored Abalone plate field, shell photo, tile wall or grain.
        # M7 89.7, collision 0/93 and distinctness 0/4,371; 1.65-1.87s native.
        from . import fractured_wilds_mother_of_pearl_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_sunbird_throat":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dense micro-flute
        # lacquer with etched ribs, split seams, chipped ends and jewel lips;
        # not literal feathers, scales, a stripe field, or random grain.
        # Candidate evidence is native 1.75-2.07s; gates follow before bake.
        from . import fractured_wilds_sunbird_throat_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_lilac_vine":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: broken engraved
        # arabesque inlay, forked flourishes, inner etching and collar joints;
        # not literal foliage, damask wallpaper, cells, plates or noise.
        # Candidate evidence is native 1.76-2.13s; gates follow before bake.
        from . import fractured_wilds_lilac_vine_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_leafvine_drape":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: folded satin-lacquer
        # hierarchy with woven interiors, brushed lanes, chipped foil cuts and
        # dark crease seams—not literal leaves, plates, cells or grain texture.
        # Candidate evidence is native 2.00-2.13s; gates follow before bake.
        from . import fractured_wilds_leafvine_drape_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_butter_whorl":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dense broken brush-lacquer
        # livery with nested pull strokes, short hooked bristles, enamel voids
        # and foil turns—not pollen, a macro pinwheel, grain, or a frame.
        # Candidate evidence is native 1.66-1.83s; gates follow before bake.
        from . import fractured_wilds_butter_whorl_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_cyan_membrane":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: continuous stressed
        # technical film with fine optical folds, pinched seam junctions and
        # iridescent fracture lips—not a map, a circuit, a panel kit or grain.
        # Candidate evidence is native 1.62-1.75s; gates follow before bake.
        from . import fractured_wilds_cyan_membrane_asset_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_leaf_whorl":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dense fractured carbon
        # lamellae, etched ribs, clipped chevrons and copper fracture lips;
        # abstract directional motion, not literal leaves, rows, plates or grain.
        # Candidate evidence is native 1.65-1.78s; gates follow before bake.
        from . import fractured_wilds_leaf_whorl_asset_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_pink_pollen":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: linked fuchsia shard
        # wakes make an abstract acceleration-spray livery, not literal pollen,
        # noise, bubbles or repeated stamps. Native evidence: 2.51–2.90s.
        from . import fractured_wilds_pink_pollen_spray_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_grackle_oil":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: petroleum-black racing
        # livery with cobalt/teal interference skins and purple split lips;
        # not the rejected dark scalar/noise-field treatment.
        from . import fractured_wilds_grackle_oil_asset_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_starling_sheen":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: prismatic black-lacquer
        # livery with silver facets, violet foil and lime interference; not a
        # bird/feather graphic or a recoloured Grackle Oil carrier.
        from . import fractured_wilds_starling_sheen_asset_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_lilac_rose":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: asymmetric plum/silver
        # torn lacquer with cyan release lips; abstract name-led livery, never
        # a literal rose or the rejected repeated rosette field.
        from . import fractured_wilds_lilac_rose_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_white_whorl":
        # SPB-105 / owner full-size review 2026-08-27: I2 is giant chrome
        # ribbon/shard illustration. I3 is dense gardenia pearl-lacquer
        # fracture with fine lamellae and cyan/violet flipped seam ownership.
        from . import fractured_wilds_white_whorl_gardenia_i3_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_magenta_mosaic":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dislocated fuchsia
        # lacquer, copper repair plates and cyan exposed fracture lines; not a
        # regular mosaic, stained-glass grid, confetti or palette-only clone.
        from . import fractured_wilds_magenta_mosaic_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_blush_rose":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: blush/burgundy couture
        # motorsport wrap bands with carbon releases, hatches and cyan register
        # marks. The generated vignette is cropped before material derivation so
        # it cannot create a tiled frame; no flower, rosette, or palette clone.
        from . import fractured_wilds_blush_rose_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_coral_cluster":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: dense coral-orange
        # coalesced lacquer deposits, black release rivers, internal hatches,
        # copper fault lips and cyan registration marks. Not reef imagery,
        # a flower, a generic blade field, or Magenta Mosaic's sparse plates.
        from . import fractured_wilds_coral_cluster_asset_i4_2026 as module
        paint, spec = module._authored()
    elif fid == "fbl_magenta_pollen":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: interlaced magenta
        # bristle-lacquer bundles, exposed black release corridors, warm foil
        # stitch marks and cyan flip lips; not Pink Pollen's shard wakes or
        # a pollen micrograph/noise field.
        from . import fractured_wilds_magenta_pollen_asset_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_magenta_plankton":
        # SPB-105 / owner Wilds rebuild, 2026-08-26: black/magenta/violet
        # bioluminescent dazzle lacquer with broken stencils, etched inserts,
        # phosphor cyan registration and champagne fracture slivers. It is a
        # full-car graphic, not a plankton micrograph, particle field or clone.
        from . import fractured_wilds_magenta_plankton_asset_i3_2026 as module
        paint, spec = module._authored()
    else:
        raise KeyError(f"Wilds ID is not accepted for runtime override: {fid}")
    paint = _float_paint(paint)
    spec = _uint8_spec(spec)
    if paint.shape[:2] != spec.shape[:2]:
        raise ValueError(f"accepted Wilds paint/spec shape mismatch for {fid}: {paint.shape} vs {spec.shape}")
    return paint, spec


def _zone_mask(mask: np.ndarray, height: int, width: int) -> np.ndarray:
    zone = np.asarray(mask, np.float32)
    if zone.ndim == 3:
        zone = zone[:, :, 0]
    if zone.shape != (height, width):
        zone = cv2.resize(zone, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(zone, 0.0, 1.0)


def _source_paint(paint: np.ndarray, height: int, width: int) -> np.ndarray:
    source = np.asarray(paint, np.float32)
    if source.ndim != 3 or source.shape[2] < 3:
        return np.zeros((height, width, 3), np.float32)
    source = source[:, :, :3]
    if source.size and float(source.max()) > 1.5:
        source = source / np.float32(255.0)
    if source.shape[:2] != (height, width):
        source = cv2.resize(source, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(source, 0.0, 1.0).astype(np.float32)


def _entry(fid: str) -> tuple[Callable, Callable]:
    def paint_fn(paint, shape, mask, seed, pm, bb):
        height, width = int(shape[0]), int(shape[1])
        source = _source_paint(paint, height, width)
        zone = _zone_mask(mask, height, width)
        authored, _spec = _accepted_authored(fid)
        authored = cv2.resize(authored, (width, height), interpolation=cv2.INTER_LANCZOS4)
        alpha = np.clip(zone * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(source * (1.0 - alpha) + authored * alpha, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        height, width = int(shape[0]), int(shape[1])
        zone = _zone_mask(mask, height, width)
        _paint, authored = _accepted_authored(fid)
        authored = cv2.resize(authored, (width, height), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC) * max(0.0, float(sm)), 0.0, 255.0)
        rgb = active * zone[..., None] + CALM_SPEC * (1.0 - zone[..., None])
        out = np.empty((height, width, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    paint_fn.__name__ = f"paint_{fid}_accepted_2026"
    spec_fn.__name__ = f"spec_{fid}_accepted_2026"
    return spec_fn, paint_fn


def clear_cache() -> None:
    _accepted_authored.cache_clear()


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the reviewed Wilds survivors in every live registry."""
    registries = [mono_reg]
    try:
        from engine.expansions import fusions
        registries.append(fusions.FUSION_REGISTRY)
    except Exception:
        pass
    try:
        from engine.registry import FUSION_REGISTRY, MONOLITHIC_REGISTRY
        registries.extend((MONOLITHIC_REGISTRY, FUSION_REGISTRY))
    except Exception:
        pass
    import sys
    engine = sys.modules.get("shokker_engine_v2")
    if engine is not None and hasattr(engine, "FUSION_REGISTRY"):
        registries.append(engine.FUSION_REGISTRY)
    unique = []
    for registry in registries:
        if all(registry is not other for other in unique):
            unique.append(registry)
    for fid in ACCEPTED_IDS:
        entry = _entry(fid)
        for registry in unique:
            registry[fid] = entry
    return f"fractured-wilds-accepted: {len(ACCEPTED_IDS)} native-reviewed experimental overrides live"


__all__ = ["ACCEPTED_IDS", "clear_cache", "install_into_engine"]
