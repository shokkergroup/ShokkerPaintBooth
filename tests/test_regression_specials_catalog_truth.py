from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def _load_special_catalog():
    return _load_catalog()


def _load_catalog():
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('paint-booth-0-finish-data.js', 'utf8');
const ctx = {
  window: {},
  console: { log() {}, warn() {} },
  setTimeout() {},
};
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });
const specialGroups = vm.runInContext('SPECIAL_GROUPS', ctx);
const sections = vm.runInContext('SPECIALS_SECTIONS', ctx);
const order = vm.runInContext('SPECIALS_SECTION_ORDER', ctx);
const baseGroups = vm.runInContext('BASE_GROUPS', ctx);
const patternGroups = vm.runInContext('PATTERN_GROUPS', ctx);
const specPatternGroups = vm.runInContext('SPEC_PATTERN_GROUPS', ctx);
const monoIds = new Set(vm.runInContext('MONOLITHICS.map(m => m.id)', ctx));
function collectOwners(groups) {
  const owners = {};
  for (const [group, ids] of Object.entries(groups)) {
  for (const id of ids || []) {
    if (!owners[id]) owners[id] = [];
    owners[id].push(group);
  }
}
  return owners;
}
function collectDuplicates(owners) {
  const duplicates = {};
  for (const [id, groups] of Object.entries(owners)) {
    if (groups.length > 1) duplicates[id] = groups;
  }
  return duplicates;
}
const owners = collectOwners(specialGroups);
const baseOwners = collectOwners(baseGroups);
const patternOwners = collectOwners(patternGroups);
const specPatternOwners = collectOwners(specPatternGroups);
const duplicates = collectDuplicates(owners);
const baseDuplicates = collectDuplicates(baseOwners);
const patternDuplicates = collectDuplicates(patternOwners);
const specPatternDuplicates = collectDuplicates(specPatternOwners);
const groupedMonos = Object.keys(owners).filter(id => monoIds.has(id));
const prunedHomes = ctx.window.SPB_PRUNED_SPECIAL_HOMES || {};
const categoryRedirects = ctx.window.SPB_SPECIAL_CATEGORY_REDIRECTS || {};
console.log(JSON.stringify({
  specialGroups, sections, order, owners, duplicates, groupedMonos, prunedHomes, categoryRedirects,
  baseGroups, baseOwners, baseDuplicates,
  patternGroups, patternOwners, patternDuplicates,
  specPatternGroups, specPatternOwners, specPatternDuplicates,
}));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def test_shipping_special_groups_have_no_duplicate_ids():
    catalog = _load_special_catalog()
    assert catalog["duplicates"] == {}


def test_neon_underground_is_one_exact_25_finish_live_group():
    catalog = _load_special_catalog()
    assert catalog["specialGroups"]["★ NEON UNDERGROUND"] == [
        "neon_electric_blue", "neon2_splatter", "neon2_rain",
        "neon_red_alert", "neon2_quarter_mile_weave", "neon_ice_white",
        "neon2_plasma_tubes", "neon_cyber_yellow", "neon2_torque_scar",
        "neon_rainbow_tube", "neon2_wireframe", "neon2_flow_tubes",
        "neon2_honeycomb", "neon_pink_blaze", "neon_blacklight",
        "neon_orange_hazard", "neon_dual_glow", "neon2_sign_tubes",
        "neon2_circuit_city", "neon2_laser_web", "neon2_synthwave_sun",
        "neon_toxic_green",
        "neon2_phantom_mica", "neon2_emberwake_delam",
        "neon2_frequency_fault",
    ]


def test_material_world_no_longer_ships_carbon_and_weave_special_bucket():
    catalog = _load_special_catalog()
    assert "Carbon & Weave" not in catalog["specialGroups"]
    assert "Carbon & Weave" not in catalog["sections"]["Material World"]
    assert "carbon_3k_weave" not in catalog["owners"]
    assert "carbon_weave" not in catalog["owners"]


def test_removed_shipping_categories_do_not_resurface():
    catalog = _load_catalog()
    assert not [group for group in catalog["baseGroups"] if "Reference" in group]
    assert not [group for group in catalog["baseGroups"] if "PARADIGM" in group.upper()]
    assert not [group for group in catalog["specialGroups"] if "Other" in group or "Legacy" in group or "Fallback" in group]


def test_owner_requested_light_categories_are_folded_without_losing_finish_ids():
    """SPB-CATALOG-CONSOLIDATION 2026-08-23: preserve IDs, retire weak shelves."""
    catalog = _load_special_catalog()
    groups = catalog["specialGroups"]
    sections = catalog["sections"]

    material_moves = {
        "Leather & Texture": "Surface & Grain",
        "Natural & Organic": "Surface & Grain",
        "Surface Treatment": "Materials & Physics",
        "Geometric & Structural": "Depth & Geometry",
        "Particles & Textures": "Surface & Grain",
        "Clearcoat Effects": "Glass & Surface",
    }
    color_science_moves = {
        "Chameleon": "Prizm",
        "Aurora & Chromatic Flow": "Prizm",
        "Color-Shift Adaptive": "Color-Shift Duos",
        "Color-Shift Presets": "Color-Shift Duos",
        "Gradient Vortex": "Gradient Directional",
    }

    assert catalog["categoryRedirects"] == {**material_moves, **color_science_moves}
    merge_src = (REPO / "paint-booth-1-data.js").read_text(encoding="utf-8")
    assert "window.SPB_SPECIAL_CATEGORY_REDIRECTS" in merge_src
    assert "const cat = categoryRedirects[sourceCat] || sourceCat;" in merge_src

    for source in material_moves:
        assert source not in groups
        assert source not in sections["Material World"]
    for source in color_science_moves:
        assert source not in groups
        assert source not in sections["Color Science"]

    expected_owners = {
        "rust": "Surface & Grain",
        "weathered_paint": "Surface & Grain",
        "worn_chrome": "Surface & Grain",
        "chameleon_amethyst": "Prizm",
        "mystichrome": "Prizm",
        "aurora_supernova": "Prizm",
        "aurora": "Prizm",
        "grad_blue_vortex": "Gradient Directional",
        "grad_white_vortex": "Gradient Directional",
    }
    for finish_id, target in expected_owners.items():
        assert catalog["owners"][finish_id] == [target]

    # Back-end-only ids are restored after /api/finish-data proves they exist;
    # their remembered destination must also be the consolidated shelf.
    assert catalog["prunedHomes"]["spec_snake_scales"] == "Surface & Grain"
    assert catalog["prunedHomes"]["spec_anodized_texture"] == "Materials & Physics"
    assert catalog["prunedHomes"]["spec_hammered_dimple"] == "Depth & Geometry"
    assert catalog["prunedHomes"]["gold_flake"] == "Surface & Grain"

    # Counts cover every currently shipping source member. Unregistered legacy
    # ids remain pruned rather than being resurrected as broken picker tiles.
    assert len(groups["Surface & Grain"]) >= 33
    assert len(groups["Materials & Physics"]) >= 31
    assert len(groups["Depth & Geometry"]) >= 41
    assert len(groups["Prizm"]) >= 71
    assert len(groups["Gradient Directional"]) >= 34


def test_shipping_picker_group_ids_do_not_duplicate_except_foundation_aliases():
    catalog = _load_catalog()
    allowed_base_dupes = {
        "ceramic": ["Foundation", "Ceramic & Glass"],
        "piano_black": ["Foundation", "Ceramic & Glass"],
    }
    assert catalog["duplicates"] == {}
    assert catalog["patternDuplicates"] == {}
    assert catalog["specPatternDuplicates"] == {}
    assert catalog["baseDuplicates"] == allowed_base_dupes


def test_singularity_is_only_grouped_under_paradigm():
    catalog = _load_special_catalog()
    assert catalog["owners"]["singularity"] == ["PARADIGM"]


def test_shipping_special_ids_do_not_use_active_catalog_fallbacks():
    import shokker_engine_v2 as eng

    eng._ensure_expansions_loaded()
    catalog = _load_special_catalog()
    fallback_to = getattr(eng, "CATALOG_FALLBACK_WIRED_TO", {})

    def _is_active_fallback(finish_id: str) -> bool:
        target = fallback_to.get(finish_id)
        return bool(
            target
            and finish_id in eng.MONOLITHIC_REGISTRY
            and target in eng.MONOLITHIC_REGISTRY
            and eng.MONOLITHIC_REGISTRY[finish_id] == eng.MONOLITHIC_REGISTRY[target]
        )

    active = {
        finish_id: fallback_to[finish_id]
        for finish_id in catalog["owners"]
        if _is_active_fallback(finish_id)
    }
    assert active == {}


def test_shipping_special_ids_resolve_or_are_declared_gradient_family():
    import shokker_engine_v2 as eng

    eng._ensure_expansions_loaded()
    catalog = _load_special_catalog()
    missing = sorted(
        finish_id
        for finish_id in catalog["owners"]
        if finish_id not in eng.MONOLITHIC_REGISTRY
        and finish_id not in eng.BASE_REGISTRY
        and finish_id not in eng.PATTERN_REGISTRY
    )
    assert all(finish_id.startswith("grad_") for finish_id in missing), missing
