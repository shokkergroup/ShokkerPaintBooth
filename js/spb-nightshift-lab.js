/* ============================================================================
   SPB — FRACTURED NIGHTSHIFT catalog injection                     2026-08-01
   ----------------------------------------------------------------------------
   Owner mission: TRUE color-flip finishes for iRacing (day hue -> DIFFERENT
   night hue). Engine: engine/expansions/nightshift_lab_2026.py; theory:
   docs/NIGHTSHIFT_LAB_THEORY.md.
   Runtime-push (NO edit to paint-booth-0-finish-data.js — Kimi K3 is mid-flight
   in that file): MONOLITHICS entries + SPECIAL_GROUPS group + FRACTURED section
   membership. Loads right after the finish-data script.
   ============================================================================ */
(function () {
    var GROUP = '🌗 FRACTURED NIGHTSHIFT';
    var DEFS = [
        ['ns_ember_reversal', 'Ember Reversal', 'DAY crimson linen — NIGHT the body vanishes black and only branching ember veins smolder orange. A red car that becomes lightning in the dark.', '#a8161c'],
        ['ns_indigo_inferno', 'Indigo Inferno', 'DAY deep indigo twill — NIGHT the weave ignites RED. The flagship blue-to-red flip: two different cars in one paint.', '#243084'],
        ['ns_violet_verdict', 'Violet Verdict', 'DAY cobalt shatter-glass — NIGHT every cell wall fires VIOLET. Blue by sunlight, purple under the floodlights.', '#1e40a8'],
        ['ns_solar_betrayal', 'Solar Betrayal', 'DAY blood red ripple — NIGHT interfering rings blaze GOLD. Red turns to molten yellow under the lights.', '#9e1018'],
        ['ns_toxic_handshake', 'Toxic Handshake', 'DAY burnt-orange reptile scales — NIGHT the scale edges arc ACID GREEN. Orange to toxin, panel by panel.', '#c45c12'],
        ['ns_bubblegum_abyss', 'Bubblegum Abyss', 'DAY bubblegum pink dots — NIGHT the web between them floods ELECTRIC BLUE. Sweet by day, deep-sea by night.', '#ee78a8'],
        ['ns_ghost_prism', 'Ghost Prism', 'DAY soft white pearl — NIGHT flow-combed facets fire a moving RAINBOW, a different hue on every panel. White car, spectral night.', '#e1e1e6'],
        ['ns_dead_channel', 'Dead Channel', 'DAY flat teal broadcast — NIGHT the glitch slivers between scanline blocks scream MAGENTA. Signal lost, color found.', '#168080'],
        ['ns_triple_cross', 'Triple Cross', 'TRI-STATE: slate argyle by DAY, crimson diamonds by NIGHT, white razor seams that flash in direct beams. Three finishes in one.', '#404e6a'],
        ['ns_furnace_glass', 'Furnace Glass', 'DAY molten-orange crackle plates — NIGHT the cracks between them flood ICE BLUE. Fire by day, frost by night.', '#de5c14'],
        // ---- WAVE 2 (2026-08-01, owner: "expand to 100 - go CRAZY") ----
        // GENERATED from engine/expansions/nightshift_lab_wave2_2026.py
        // (emit_js_defs) - edit the python DEFS, not these rows.
        ['ns2_tide_turner', 'Tide Turner', 'DAY deep harbor blue with fine tide lines — NIGHT every crest glows seafoam. The ocean turning over in the dark.', '#103e60'],
        ['ns2_breaker_bay', 'Breaker Bay', 'DAY storm-sea teal — NIGHT hundreds of curling breakers flash white foam. Surf report: firing.', '#145078'],
        ['ns2_caustic_royale', 'Caustic Royale', 'DAY pool-floor navy — NIGHT the double caustic web dances electric aqua. Sunlight through water, at midnight.', '#0a285a'],
        ['ns2_kelp_cathedral', 'Kelp Cathedral', 'DAY dark kelp-forest green — NIGHT the swaying columns light up lime. A dive at dusk.', '#0e3c2c'],
        ['ns2_rain_ritual', 'Rain Ritual', 'DAY slate rain-cloud grey — NIGHT overlapping raindrop rings ripple ice blue. First drops on still water.', '#2c3446'],
        ['ns2_maelstrom', 'Maelstrom', 'DAY midnight sea — NIGHT four spiral whirlpools churn glowing turquoise arms. Do not sail here.', '#122242'],
        ['ns2_foam_lace', 'Foam Lace', 'DAY weathered sea-glass grey — NIGHT the lace between bubbles burns warm white. Champagne surf.', '#96aab9'],
        ['ns2_undertow', 'Undertow', 'DAY calm banded blue — NIGHT alternating current bands reveal hidden AMBER chevrons pulling sideways. The current you can\'t see.', '#1a2e50'],
        ['ns2_plankton_wake', 'Plankton Wake', 'DAY near-black abyss — NIGHT a bioluminescent wake of teal-green sparks. Every touch leaves light.', '#081828'],
        ['ns2_jelly_ballet', 'Jelly Ballet', 'DAY deep violet water — NIGHT drifting jellyfish bells and tentacles glow neon pink. Graceful and slightly menacing.', '#1e163c'],
        ['ns2_abyss_lines', 'Abyss Lines', 'DAY charcoal-navy void — NIGHT ragged sonar strata lines sweep pale blue. The depth chart of nowhere.', '#0c101c'],
        ['ns2_sonar_ghost', 'Sonar Ghost', 'DAY blackout naval green — NIGHT a sonar sweep, range rings and contact blips burn radar green. Something\'s out there.', '#0a1e1e'],
        ['ns2_granule_sun', 'Granule Sun', 'DAY burnt solar orange — NIGHT every convection cell core boils gold. The surface of the sun, idling.', '#963c0a'],
        ['ns2_corona_crown', 'Corona Crown', 'DAY eclipse-plum dusk — NIGHT a fan of corona rays streams warm white from above. Totality, then fire.', '#5a1e3c'],
        ['ns2_fork_daddy', 'Fork Daddy', 'DAY storm-front graphite — NIGHT forked lightning rips top to bottom in blue-white. The strike, frozen.', '#1e1e2c'],
        ['ns2_thunder_topo', 'Thunder Topo', 'DAY brooding cloud grey — NIGHT the thunderhead\'s contour lines glow amber like a storm map. Weather radar couture.', '#282c3a'],
        ['ns2_aurora_veil', 'Aurora Veil', 'DAY polar midnight blue — NIGHT folded aurora curtains wash green-to-violet across the panels. The sky came down.', '#101c2c'],
        ['ns2_nebula_dust', 'Nebula Dust', 'DAY starless black — NIGHT a whole starfield ignites with violet-magenta nebula wisps. Deep space on a quarter panel.', '#0a0a12'],
        ['ns2_first_light', 'First Light', 'DAY warm adobe tan — NIGHT dawn rays fan gold across the body. Sunrise you can drive.', '#be7846'],
        ['ns2_hailstorm', 'Hailstorm', 'DAY cold front grey-blue — NIGHT steep hail streaks and impact rings flash ice white. Duck.', '#464e5c'],
        ['ns2_monsoon_glass', 'Monsoon Glass', 'DAY rain-dark cyan-grey — NIGHT two crossing rain angles etch bright silver-blue. A downpour lit by headlights.', '#182834'],
        ['ns2_cloudbreak', 'Cloudbreak', 'DAY soft overcast white — NIGHT the gaps between clouds pour amber sunset through. The hole in the weather.', '#c8cdd7'],
        ['ns2_eclipse_order', 'Eclipse Order', 'TRI-STATE: violet-slate day, blood-red concentric rings at night, and a razor WHITE flash ring at totality\'s edge. Ceremonial.', '#241e30'],
        ['ns2_ion_river', 'Ion River', 'DAY deep space blue — NIGHT charged streamlines flow cyan along an invisible magnetic field. Plasma with a current.', '#14243c'],
        ['ns2_static_sky', 'Static Sky', 'DAY analog-grey — NIGHT dead-channel static rows dance pale gold. Broadcast over.', '#32323c'],
        ['ns2_fissure_king', 'Fissure King', 'DAY cooled basalt brown — NIGHT ridged magma fissures split open molten orange. The crust is thin here.', '#3c1814'],
        ['ns2_ash_procession', 'Ash Procession', 'DAY volcanic ash grey — NIGHT falling embers streak hot orange through the plume. After the eruption.', '#423e3c'],
        ['ns2_geyser_field', 'Geyser Field', 'DAY mineral sage green — NIGHT steam plumes erupt glowing white-teal. Yellowstone, floored.', '#506058'],
        ['ns2_agate_heart', 'Agate Heart', 'DAY dusty mauve stone — NIGHT jagged geode bands ring out in pink crystal light. Split the rock, find the glow.', '#5a3250'],
        ['ns2_dune_sea', 'Dune Sea', 'DAY desert ochre — NIGHT wind-carved ripple crests light pale gold. Sand under a full moon.', '#8c6437'],
        ['ns2_fault_line', 'Fault Line', 'DAY layered canyon earth — NIGHT the strata glow red where the faults stepped them sideways. Geology with a grudge.', '#544639'],
        ['ns2_obsidian_court', 'Obsidian Court', 'DAY volcanic glass black — NIGHT facet edges spark violet and random whole shards ignite. Knapped by lightning.', '#1a161e'],
        ['ns2_crevasse_blue', 'Crevasse Blue', 'DAY glacier white — NIGHT the crevasse cracks glow that impossible deep-ice blue. Beautiful. Do not step.', '#becdd7'],
        ['ns2_rust_prophet', 'Rust Prophet', 'DAY bare steel grey — NIGHT rust blooms and speckle halos burn corrosion orange. Entropy wins, gorgeously.', '#60646c'],
        ['ns2_peel_out', 'Peel Out', 'DAY faded barn red — NIGHT the peeling paint chips flash the old cyan coat underneath. Layers of history, lit.', '#a03c32'],
        ['ns2_oil_omen', 'Oil Omen', 'DAY wet-asphalt black — NIGHT the oil-slick marble swirls a full spectral rainbow. A puddle that means trouble.', '#121216'],
        ['ns2_patchwork_slab', 'Patchwork Slab', 'DAY tired concrete — NIGHT the crack web and repair patches sodium-lamp amber. Infrastructure noir.', '#787670'],
        ['ns2_gutter_glam', 'Gutter Glam', 'DAY grimy charcoal — NIGHT every drip streak runs toxic slime green. The gutter, but make it fashion.', '#363a36'],
        ['ns2_swirl_mark', 'Swirl Mark', 'TRI-STATE: show-car black day, silver scratch arcs at night, plus razor-white micro flashes in direct beams. Every detailer\'s nightmare, weaponized.', '#1e1e22'],
        ['ns2_overspray_law', 'Overspray Law', 'DAY masked-off purple — NIGHT the stencil edges and spray drift light up gold. Evidence of the crime.', '#462e5a'],
        ['ns2_wheatpaste', 'Wheatpaste', 'DAY sun-bleached poster tan — NIGHT torn sheet edges and a lucky whole layer glow hot pink. Forty years of gig flyers.', '#827460'],
        ['ns2_spatter_creed', 'Spatter Creed', 'DAY shop-floor steel — NIGHT weld spatter and spark bursts sizzle amber. Made, not bought.', '#28282e'],
        ['ns2_acid_verdict', 'Acid Verdict', 'DAY etched pewter green — NIGHT every pit rim rings acid teal. The chemical peel nobody ordered.', '#5a695a'],
        ['ns2_tar_rite', 'Tar Rite', 'DAY cracked blacktop — NIGHT the seams between plates run lava red. The road remembers heat.', '#181618'],
        ['ns2_hail_damage', 'Hail Damage', 'DAY insurance-claim silver — NIGHT two hundred dent crescents catch pale gold light. Totaled, beautifully.', '#6e747e'],
        ['ns2_checker_reaper', 'Checker Reaper', 'TRI-STATE: warped checker in black by day, alternate squares ignite RED at night, white razor grid seams flash in beams. The flag, possessed.', '#1e1e20'],
        ['ns2_tread_lord', 'Tread Lord', 'DAY tire-rubber black-brown — NIGHT the chevron tread blocks light amber like heat cycling through. Fresh off the stacker.', '#2c2826'],
        ['ns2_terminal_v', 'Terminal V', 'DAY deep gunmetal blue — NIGHT tapered speed streaks scream cyan past the panels. The car looks fast parked. At night it looks faster.', '#141c28'],
        ['ns2_slipstream_cult', 'Slipstream Cult', 'DAY quiet indigo-grey — NIGHT nested draft arcs glow gold behind invisible cars. Tow, granted.', '#242434'],
        ['ns2_rotor_glow', 'Rotor Glow', 'DAY machined grey — NIGHT drilled rotor rings burn brake-orange after the big stop. Fade is a myth.', '#28282c'],
        ['ns2_kerb_appeal', 'Kerb Appeal', 'DAY track-limit red — NIGHT the kerb stripe edges and rubbered-in wear flash white. Ride it harder.', '#962828'],
        ['ns2_apex_hunter', 'Apex Hunter', 'DAY racing green — NIGHT lanes of arrowheads point lime at every apex. The line, illuminated.', '#1a2c22'],
        ['ns2_telemetry_ghost', 'Telemetry Ghost', 'DAY matte data-slate — NIGHT rows of telemetry traces scroll mint green. Your lap, haunting you.', '#161a22'],
        ['ns2_gear_church', 'Gear Church', 'DAY oily bronze-grey — NIGHT interlocked gear trains shine brass. The drivetrain\'s cathedral.', '#34302c'],
        ['ns2_drift_sermon', 'Drift Sermon', 'DAY faded asphalt violet — NIGHT tire arcs and smoke wisps glow white. The angle was the point.', '#262228'],
        ['ns2_photo_verdict', 'Photo Verdict', 'DAY dark slit-scan grey — NIGHT the finish-line slits strobe gold with jitter. Won it by the bumper.', '#1c1e24'],
        ['ns2_pit_board', 'Pit Board', 'DAY blank LED panels — NIGHT the dot-matrix lights amber like a pit board mid-message. P1. BOX. PUSH.', '#141418'],
        ['ns2_nano_hive', 'Nano Hive', 'DAY carbon-teal micro hex — NIGHT the lattice and random lit cells pulse cyan. A hive of machines agreeing.', '#1e262c'],
        ['ns2_trace_route', 'Trace Route', 'DAY PCB-mask green-black — NIGHT routed traces and via dots light circuit green. The packet always arrives.', '#102820'],
        ['ns2_datamosh_ritual', 'Datamosh Ritual', 'DAY corrupted plum — NIGHT displaced blocks and fringe columns tear magenta-cyan across rows. The keyframe never came.', '#281a30'],
        ['ns2_lissajous_love', 'Lissajous Love', 'DAY oscilloscope navy — NIGHT sixteen phase curves trace pale gold loops. Two signals, in love.', '#181e28'],
        ['ns2_laser_horizon', 'Laser Horizon', 'DAY retrowave dusk purple — NIGHT the perspective grid rolls hot pink to a starfield horizon. 1986 called; it wants a ride.', '#161028'],
        ['ns2_wireframe_west', 'Wireframe West', 'DAY topo-sim olive — NIGHT stacked terrain polylines glow mint with hidden-line gaps. Flying over the map, not the land.', '#1e221e'],
        ['ns2_holo_decree', 'Holo Decree', 'DAY projector-off slate — NIGHT scan bands, row lines and edge ticks shimmer cyan-magenta hologram. Authenticity: verified.', '#1a222e'],
        ['ns2_rain_of_code', 'Rain of Code', 'DAY terminal-black green — NIGHT dotted columns rain down phosphor green at different speeds. You\'ve seen this rain before.', '#0e1610'],
        ['ns2_quasi_star', 'Quasi Star', 'DAY muted amethyst — NIGHT a five-fold quasicrystal interference lattice blooms pink-white. Order without repetition.', '#282438'],
        ['ns2_glitch_bloom', 'Glitch Bloom', 'DAY dark violet static — NIGHT random cells detonate into streak fans of gold. Beautiful crash logs.', '#1e1a22'],
        ['ns2_tiger_verdict', 'Tiger Verdict', 'DAY blazing tiger orange — NIGHT the brush slashes go VOID BLACK, eating the light between them. The stripes hunt after dark.', '#be6e1e'],
        ['ns2_zebra_current', 'Zebra Current', 'DAY ivory white — NIGHT the flowing stripes drop to charcoal, reversing the animal. Day zebra, night negative.', '#e1e1dc'],
        ['ns2_rosette_court', 'Rosette Court', 'DAY savanna gold — NIGHT every broken rosette ring flares ember orange. Spotted, then hunted.', '#b48c3c'],
        ['ns2_viper_lattice', 'Viper Lattice', 'DAY olive scale-diamond weave — NIGHT the swaying lattice glows venom green. It was never rope.', '#3c4628'],
        ['ns2_peacock_court', 'Peacock Court', 'DAY deep teal-navy plumage — NIGHT a hundred feather eyes open in shifting blue-green iridescence. The tail is watching.', '#14283c'],
        ['ns2_wing_chapel', 'Wing Chapel', 'DAY dusty violet membrane — NIGHT the wing veins and radiating ribs glow orchid. Stained glass that flies.', '#46325a'],
        ['ns2_mycelium_mind', 'Mycelium Mind', 'DAY bone white — NIGHT the fungal thread network lights lavender, thinking. The forest\'s internet.', '#f0eee6'],
        ['ns2_dendrite_choir', 'Dendrite Choir', 'DAY neural dark — NIGHT branches, somata and synapse sparks fire gold. A thought, mid-flight.', '#1e1e28'],
        ['ns2_koi_dynasty', 'Koi Dynasty', 'DAY koi orange-red — NIGHT the crescent scale rows shimmer pearl. Four hundred years old and showing off.', '#c85a3c'],
        ['ns2_moth_omen', 'Moth Omen', 'DAY dusty taupe wing — NIGHT the powder gradient and wing bars glow pale orchid. Drawn to your headlights.', '#6e645a'],
        ['ns2_moire_prophet', 'Moiré Prophet', 'DAY quiet graphite — NIGHT two off-center ring gratings interfere in cyan beat patterns that move as you do. The pattern isn\'t ON the car.', '#28282e'],
        ['ns2_rhomb_royalty', 'Rhomb Royalty', 'DAY plum rhombus tiling — NIGHT alternating rhombs and seam lines ignite amber. Penrose would drive it.', '#3c2c46'],
        ['ns2_hyper_rings', 'Hyper Rings', 'DAY abyssal blue-grey — NIGHT log-spaced rings from five poles collapse inward in magenta. Non-Euclidean parking only.', '#141e28'],
        ['ns2_frost_sermon', 'Frost Sermon', 'DAY frosted-glass white — NIGHT feather crystals grow ice blue from every edge. Winter\'s handwriting.', '#d2dce6'],
        ['ns2_spiro_seance', 'Spiro Séance', 'DAY dark mulberry — NIGHT ten spirograph orbits trace warm gold geometry. Summoned with a pen and two gears.', '#1e1824'],
        ['ns2_kaleid_kingdom', 'Kaleid Kingdom', 'DAY muted royal violet — NIGHT the eight-fold mirror bloom erupts in shifting rainbow symmetry. Turn the tube.', '#2c2236'],
        ['ns2_pulse_doctrine', 'Pulse Doctrine', 'DAY op-art moss grey — NIGHT warped concentric squares pulse hot rose from the center. Stare too long and it staresback.', '#222622'],
        ['ns2_stair_heresy', 'Stair Heresy', 'DAY isometric slate — NIGHT the impossible staircase bands glow mint, going up forever in both directions. Escher\'s daily driver.', '#383840'],
        ['ns2_anamorph_altar', 'Anamorph Altar', 'DAY sepia leather — NIGHT stretched rings resolve gold from exactly one viewing angle. Park it right or park it wrong.', '#2e241e'],
        ['ns2_chroma_heresy', 'Chroma Heresy', 'DAY soft black — NIGHT the same pattern fires three times, offset like misregistered print, hue split along the offset. Your eyes are fine. Mostly.', '#1c1c20'],
        ['ns2_dazzle_doctrine', 'Dazzle Doctrine', 'DAY WWI dazzle-ship grey — NIGHT each angular zone\'s stripes fire yellow at its own angle. Built to confuse rangefinders; still works.', '#5a5a64'],
        ['ns2_ferro_gospel', 'Ferro Gospel', 'DAY magnet-black steel — NIGHT ferrofluid spike rosettes bristle silver-blue. The field made flesh.', '#1e2228'],
        ['ns2_singularity', 'Singularity', 'TRI-STATE: void black day, a full-canvas gold accretion spiral at night, and a white-hot event-horizon ring in direct light. Beyond this line, nothing escapes.', '#101016'],
        ['ns2_iris_reactor', 'Iris Reactor', 'DAY reactor-core plum — NIGHT the ring cascade dilates teal like a machine iris opening. Power at 108 percent.', '#241428'],
    ];
    function injectDesc() {
        // separate from install(): SPB_ATLAS loads AFTER this script, so the
        // rich description must keep retrying even once the group exists
        try {
            if (window.SPB_ATLAS && SPB_ATLAS.DESC && !SPB_ATLAS.DESC[GROUP]) {
                SPB_ATLAS.DESC[GROUP] = 'The color-flip lab — ONE HUNDRED experiments in making a car change HUE between day and night, not just blow out to white. Two interleaved pixel populations: a matte skin that owns the daylight and a metal lattice that fires a DIFFERENT color under the lights. Blue-to-red, red-to-gold, orange-to-green, pink-to-blue, white-to-rainbow… every build names its flip. Oceans, storms, lightning, grunge, racing, glitch, animals and pure math — the whole spectrum, wave 2 style. Fresh from the lab — run them at night and report back.';
                return true;
            }
        } catch (e) {}
        return !!(window.SPB_ATLAS && SPB_ATLAS.DESC && SPB_ATLAS.DESC[GROUP]);
    }
    function install() {
        if (typeof MONOLITHICS === 'undefined' || typeof SPECIAL_GROUPS === 'undefined') return false;
        injectDesc();
        if (SPECIAL_GROUPS[GROUP]) return true;                     // already installed
        var ids = [];
        DEFS.forEach(function (d) {
            ids.push(d[0]);
            if (!MONOLITHICS.some(function (m) { return m.id === d[0]; })) {
                MONOLITHICS.push({ id: d[0], name: d[1], desc: d[2] + ' A FRACTURED NIGHTSHIFT color-flip experiment — verdict comes from the track.', swatch: d[3] });
            }
        });
        SPECIAL_GROUPS[GROUP] = ids;
        try {
            if (typeof SPECIALS_SECTIONS !== 'undefined' && SPECIALS_SECTIONS.FRACTURED
                && SPECIALS_SECTIONS.FRACTURED.indexOf(GROUP) < 0) {
                SPECIALS_SECTIONS.FRACTURED.push(GROUP);
            }
        } catch (e) {}
        return true;
    }
    function boot() { var ok = install(); if (!injectDesc() || !ok) setTimeout(boot, 800); }
    if (!install() || !injectDesc()) {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
        setTimeout(boot, 1200);                                     // late-load safety
    }
})();
