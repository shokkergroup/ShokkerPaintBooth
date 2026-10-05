"""Stable-ID ledger for the Neon Underground v4 live rebuild."""
from __future__ import annotations


# Ordered for the live ★ NEON UNDERGROUND picker: five anchors, then 20
# deliberately different after-midnight tuner materials.
CATALOG = {
    "neon_electric_blue": ("neon_underglow", "Neon Underglow", "#00a8ff", "Ground-effects cyan and magenta rising through smoked wet-look paint."),
    "neon2_splatter": ("midnight_drift", "Midnight Drift", "#ff2b85", "Backlit drift haze, curved skid-light and ember heat moving laterally through black."),
    "neon2_rain": ("tokyo_rain", "Tokyo Rain", "#22c7ff", "Rain-smeared Tokyo sign color reflected through deep wet asphalt clear."),
    "neon_red_alert": ("redline_rush", "Redline Rush", "#ff163d", "Escalating redline heat and speed rhythm without a literal gauge."),
    "neon2_quarter_mile_weave": ("quarter_mile", "Quarter Mile", "#ffc21c", "Staging-light energy, fragmented micro-checks and launch streaks on a wet strip."),
    "neon_ice_white": ("nitro_purge", "Nitro Purge", "#9defff", "Electric-blue purge plumes, frost shock and white pressure cores."),
    "neon2_plasma_tubes": ("boost_spool", "Boost Spool", "#ff6a22", "Cyan intake pressure winding into orange turbine heat and compressor glints."),
    "neon_cyber_yellow": ("tunnel_vision", "Tunnel Vision", "#ffe21a", "Vanishing tunnel lights stretching into yellow, cyan and white speed wedges."),
    "neon2_torque_scar": ("wet_apex", "Wet Apex", "#00f0c8", "A luminous racing line cutting an S-curve through rain-dark pavement."),
    "neon_rainbow_tube": ("afterburn_chrome", "Afterburn Chrome", "#ff4fd8", "Heat-shifted chrome with broad spectral oxidation bands and brushed fire."),
    "neon2_wireframe": ("grid_runner", "Grid Runner", "#00e5ff", "Broken perspective grids and hard-turn light trails over a digital void."),
    "neon2_flow_tubes": ("street_pulse", "Street Pulse", "#ff315d", "Crossing long-exposure traffic rivers and wet lane reflections."),
    "neon2_honeycomb": ("carbon_voltage", "Carbon Voltage", "#36f5ff", "Edge-lit carbon weave split by charged cyan and violet seams."),
    "neon_pink_blaze": ("import_royalty", "Import Royalty", "#ff27b7", "Layered razor vinyl slashes with prismatic tuner-wrap edges."),
    "neon_blacklight": ("blacklight_garage", "Blacklight Garage", "#9c35ff", "Fluorescent solvent pools and ultraviolet shop-light reflections on concrete black."),
    "neon_orange_hazard": ("burnout_ember", "Burnout Ember", "#ff4a12", "Curved tire-heat tracks, underlit smoke and ember-red rubber fragments."),
    "neon_dual_glow": ("split_underglow", "Split Underglow", "#d92cff", "Opposed cyan and magenta ground-light fields dividing a smoked body."),
    "neon2_sign_tubes": ("signglass_shatter", "Signglass Shatter", "#ff3b88", "Broken sign-glass territories with white-hot rims and dying phosphor interiors."),
    "neon2_circuit_city": ("seoul_circuit", "Seoul Circuit", "#ff78d8", "Rounded luminous panel cascades and mint-lilac city-current seams."),
    "neon2_laser_web": ("laser_lane", "Laser Lane", "#ff205f", "Few decisive laser corridors built from tightly bundled fine beams."),
    "neon2_synthwave_sun": ("arcade_afterhours", "Arcade Afterhours", "#f82cff", "Blacklight scan waves, vector sweeps and phosphor trails after closing time."),
    "neon_toxic_green": ("toxic_overdrive", "Toxic Overdrive", "#62ff16", "Acid-green current pools with yellow pressure lips and black sink regions."),
    "neon2_phantom_mica": ("phantom_taillights", "Phantom Taillights", "#ff174f", "Red and magenta afterimage ribbons fading through midnight blue."),
    "neon2_emberwake_delam": ("turbo_heat", "Turbo Heat", "#ff6426", "Anodized titanium heat zones, weld ripples and hot turbine seams."),
    "neon2_frequency_fault": ("midnight_candy", "Midnight Candy", "#843dff", "Deep candy violet with broad cyan-magenta angle-flip shoulders."),
}

ORDER = tuple(CATALOG)


def module_name(finish_id: str) -> str:
    return "engine.expansions.neon_underground_v4." + CATALOG[finish_id][0]
