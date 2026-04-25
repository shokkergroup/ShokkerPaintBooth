// ============================================================
// PAINT-BOOTH-0-FINISH-DATA.JS - All finish arrays and groups
// ============================================================
// Purpose: SINGLE SOURCE OF TRUTH for BASES, PATTERNS, MONOLITHICS,
//          BASE_GROUPS, PATTERN_GROUPS, SPECIAL_GROUPS, CLR_PALETTE,
//          GRADIENT_DEFS, COLOR_MONOLITHICS, PRESETS.
// Deps:    None (loads first, before all other scripts).
// Edit:    Add/change finish IDs here. That's it.
// See:     PROJECT_STRUCTURE.md + FINISH_WIRING_CHECKLIST.md.
// ============================================================

// =============================================================================
// BASES - Single source of truth for base materials (picker + server)
// =============================================================================
const BASES = [
    { id: "p_superfluid", name: "Absolute Zero Superfluid (PARADIGM)", desc: "Ultra-smooth flowing surface — zero-friction liquid metal look with soft cyan undertone", swatch: "#E0FFFF" },
    { id: "p_coronal", name: "Coronal Mass Ejection (PARADIGM)", desc: "Hot orange-white metallic with turbulent bright loops — solar surface look", swatch: "#FF4500" },
    { id: "p_seismic", name: "Seismic Faultline (PARADIGM)", desc: "Dark graphite base with glowing cracks — molten orange veins through matte black", swatch: "#3A1A1A" },
    { id: "p_hypercane", name: "Category 5 Hypercane (PARADIGM)", desc: "Chaotic stormy blue-gray with sharp bright streaks — turbulent weather look", swatch: "#1E3B70" },
    { id: "p_geomagnetic", name: "Geomagnetic Storm (PARADIGM)", desc: "Green-cyan aurora shimmer — soft flowing bands with metallic highlights", swatch: "#44FF88" },
    { id: "p_non_euclidean", name: "Non-Euclidean Hypercube (PARADIGM)", desc: "Deep recursive geometric grid — looks like the surface has infinite depth", swatch: "#C444FF" },
    { id: "p_time_reversed", name: "Time-Reversed Entropy (PARADIGM)", desc: "Noise-to-grid transition — chaotic base resolving into clean geometry", swatch: "#445566" },
    { id: "p_programmable", name: "Programmable Utility Fog (PARADIGM)", desc: "Binary texture — sharp transitions between ultra-matte and mirror chrome zones", swatch: "#111111" },
    { id: "p_erised", name: "Negative Normal Mirror (PARADIGM)", desc: "Hyper-reflective mirror with inverted surface normals — creates an uncanny, liquid-smooth effect", swatch: "#FFFFFF" },
    { id: "p_schrodinger", name: "Schrodinger's Dust (PARADIGM)", desc: "Dual-state metallic dust — shifts between matte and gloss in a fine random pattern", swatch: "#8A2BE2" },
    { id: "acid_rain", name: "Acid Rain", desc: "Chemical rain etched paint — pitted surface with clearcoat failure zones. Realistic environmental damage look.", swatch: "#778866" },
    { id: "ambulance_white", name: "Ambulance White", desc: "High-visibility emergency white — bright reflective finish for first responder and safety vehicle builds", swatch: "#ffffff", colorSafe: true },
    { id: "anodized", name: "Anodized", desc: "Apple-product oxide layer — color dyed into metal, not painted on. Gritty matte, no clearcoat feel. Tech/modern builds.", swatch: "#7788aa", colorSafe: true },
    { id: "anime_cel_shade_chrome", name: "Anime Cel Shade Chrome", desc: "Flat cel-shaded bands with sharp metallic highlight steps", swatch: "#5566aa" },
    { id: "anime_comic_halftone", name: "Anime Comic Halftone", desc: "Ben-Day dot pattern with size variation on paper base — manga panel screentone aesthetic for stylized builds", swatch: "#CC2255" },
    { id: "anime_crystal_facet", name: "Anime Crystal Facet", desc: "Large angular crystalline facets with jewel tones per face", swatch: "#8844cc" },
    { id: "anime_energy_aura", name: "Anime Energy Aura", desc: "Radial power glow field with energy rays and bright core", swatch: "#44aaff" },
    { id: "anime_gradient_hair", name: "Anime Gradient Hair", desc: "Vivid magenta-pink top fading to deep indigo bottom — anime character hair gradient for stylized cosplay-themed cars", swatch: "#CC22AA" },
    { id: "anime_mecha_plate", name: "Anime Mecha Plate", desc: "Hard geometric panel lines with alternating metallic zones", swatch: "#445577" },
    { id: "anime_neon_outline", name: "Anime Neon Outline", desc: "Dark base with bright cyan-magenta neon edge highlights — anime energy-rim aesthetic for night-race cyber builds", swatch: "#22DDCC" },
    { id: "anime_sakura_scatter", name: "Anime Sakura Scatter", desc: "Cherry blossom petal scatter on soft pink background — Japanese seasonal motif for itasha and JDM-styled builds", swatch: "#EE8899" },
    { id: "anime_sparkle_burst", name: "Anime Sparkle Burst", desc: "Concentrated 4-pointed starburst sparkle clusters on dark", swatch: "#ffeecc" },
    { id: "anime_speed_lines", name: "Anime Speed Lines", desc: "Directional motion lines radiating from focal point — anime action-scene speed effect for high-energy race-themed builds", swatch: "#DDDDEE" },
    { id: "antique_chrome", name: "Antique Chrome", desc: "Yellowed, pitted, cloudy chrome — decades of age showing. Warmer than clean chrome. Vintage restorations and rat rods.", swatch: "#e8e8ee" },
    { id: "aramid", name: "Aramid", desc: "Kevlar ballistic fiber weave — gold-tan aramid like bulletproof vest material. Lighter than carbon. Exotic/race builds.", swatch: "#aa9944" },
    { id: "armor_plate", name: "Armor Plate", desc: "Thick rolled steel like a tank hull — heavy, scarred from manufacturing. Military vehicle and apocalypse builds.", swatch: "#778877" },
    { id: "asphalt_grind", name: "Asphalt Grind", desc: "Ground-down pavement texture — rough aggregate with tool marks from grinding. Industrial/post-apocalyptic builds.", swatch: "#444444" },
    { id: "barn_find", name: "Barn Find", desc: "Decades of neglect — faded paint, broken clearcoat, dust and cobwebs. Authentic aged patina for weathered builds.", swatch: "#887766" },
    { id: "battleship_gray", name: "Battleship Gray", desc: "US Navy standard Haze Gray 5-H — flat, non-reflective, blends with ocean horizon. Military and stealth builds.", swatch: "#888899" },
    { id: "bentley_silver", name: "Bentley Silver", desc: "Ultra-refined silver metallic — finer flake than standard, Rolls-Royce/Bentley OEM luxury. Elegant and understated.", swatch: "#ccccdd", colorSafe: true },
    { id: "beetle_jewel", name: "Beetle Jewel", desc: "Chrysina jewel beetle green-gold iridescent shell — real insect-inspired metallic with angle-shift shimmer", swatch: "#55aa22" },
    { id: "beetle_rainbow", name: "Beetle Rainbow", desc: "Chrysochroa beetle full-spectrum thin-film iridescence — rainbow wing case effect shifting at every angle", swatch: "#7744cc" },
    { id: "beetle_stag", name: "Beetle Stag", desc: "Dark metallic stag beetle armor plates with chitin shine", swatch: "#221108" },
    { id: "bioluminescent", name: "Bioluminescent", desc: "Deep-sea creature glow — soft luminous emission like anglerfish or jellyfish. Ethereal alien look for sci-fi builds.", swatch: "#22aa88" },
    { id: "black_chrome", name: "Black Chrome", desc: "Nearly black mirror chrome — dark as possible while still reflective. Sleeker than gunmetal, darker than dark chrome.", swatch: "#334455" },
    { id: "blackout", name: "Blackout", desc: "Murdered-out stealth black — thin protective matte coat over dark base. Darker than matte, less extreme than vantablack.", swatch: "#111111" },
    { id: "blue_chrome", name: "Blue Chrome", desc: "Cool blue-tinted mirror chrome — full reflectivity with an icy sapphire hue over the chrome surface", swatch: "#8899dd" },
    { id: "brushed_aluminum", name: "Brushed Aluminum", desc: "Directional grain lines — like machined aluminum panels. The hero brushed metal. Sponsor-safe with subtle texture.", swatch: "#aabbcc", colorSafe: true },
    { id: "brushed_titanium", name: "Brushed Titanium", desc: "Heavier, darker grain than brushed aluminum — titanium warmth with strong directional lines. Aerospace/industrial.", swatch: "#8899aa", colorSafe: true },
    { id: "brushed_wrap", name: "Brushed Wrap", desc: "Vinyl wrap version of brushed aluminum — directional grain film but removable. Less realistic than paint but easy swap.", swatch: "#99aaaa", colorSafe: true },
    { id: "bugatti_blue", name: "Bugatti Blue", desc: "Bugatti Bleu de France iconic deep royal blue — rich saturated hue with dark contrast, hypercar elegance", swatch: "#2244aa", colorSafe: true },
    { id: "burnt_headers", name: "Burnt Headers", desc: "Exhaust header heat-cycle oxide — gold-to-blue temper color bands from extreme heat exposure on raw steel", swatch: "#665533" },
    { id: "butterfly_monarch", name: "Butterfly Monarch", desc: "Orange-black monarch wing pattern with vein network — biological insect wing structure for nature-inspired builds", swatch: "#EE7700" },
    { id: "butterfly_morpho", name: "Butterfly Morpho", desc: "Morpho blue structural color with angle-dependent flash — biological iridescence with no actual blue pigment, all optics", swatch: "#2255EE" },
    { id: "candy", name: "Candy", desc: "Deep transparent color over metallic base — classic hot rod candy. Your color shows through with wet depth and sparkle.", swatch: "#cc2244", colorSafe: true },
    { id: "candy_apple", name: "Satan's Apple", desc: "Deep blood-red candy gloss with extreme shadow crush — very dark, very wet", swatch: "#5E0000" },
    { id: "candy_burgundy", name: "Coagulated Blood", desc: "Ultra-dark burgundy with thick uneven texture — rough organic surface feel", swatch: "#440000" },
    { id: "candy_chrome", name: "Candy Chrome", desc: "Candy-tinted chrome — deep transparent color over mirror base for maximum wet depth and vivid reflection", swatch: "#cc4488" },
    { id: "candy_cobalt", name: "Mariana Trench Resin", desc: "Ultra-deep cobalt blue resin — thick gloss over dark scatter base", swatch: "#001B4D" },
    { id: "candy_emerald", name: "Radioactive Glass", desc: "Vivid green glass with bright edge glow — uranium glass look", swatch: "#16FF00" },
    { id: "carbon_base", name: "Carbon Base", desc: "Raw exposed carbon fiber — the weave IS the finish. Low metallic with visible fiber structure. Race car essential.", swatch: "#333333" },
    { id: "carbon_ceramic", name: "Carbon Ceramic", desc: "Carbon-ceramic brake disc surface — gray with carbon fiber flecks. Exotic supercar brakes-as-finish aesthetic.", swatch: "#333333", colorSafe: true },
    { id: "cerakote", name: "Cerakote", desc: "Military-spec ceramic polymer coating — tough, dead flat, tactical feel. Like a firearm finish on a race car.", swatch: "#667755" },
    { id: "ceramic", name: "Ceramic", desc: "Ultra-smooth ceramic nano-coating — deep wet shine with glass-like clarity and hydrophobic surface protection", swatch: "#5588bb", colorSafe: true },
    { id: "ceramic_matte", name: "Ceramic Matte", desc: "Ceramic nano-coat in matte — protected flat finish like PPF/ceramic but zero gloss. Modern stealth with UV protection.", swatch: "#667788", colorSafe: true },
    { id: "chalky_base", name: "Chalky Base", desc: "Chalky oxidised flat — near-maximum degradation, powdery dead surface like neglected fence paint. Apocalypse and abandoned-vehicle builds.", swatch: "#AAAAAA", colorSafe: true },
    { id: "chameleon", name: "Dual-Shift", desc: "Two-tone angle-dependent flip — procedural micro-spec, no hand painting. Grazing light reveals the second color.", swatch: "#7766aa" },
    { id: "champagne", name: "Champagne", desc: "Warm gold-silver blend — softer than gold, warmer than silver. Wedding cars, luxury sedans, elegant formal builds.", swatch: "#ccbb88" },
    { id: "checkered_chrome", name: "Checkered Chrome", desc: "Polished chrome with checkered flag reflection pattern — winner circle finish for victory lap builds", swatch: "#dde0ee" },
    { id: "chrome", name: "Chrome", desc: "Perfect mirror reflection — M255 R2 pure chrome. The ultimate show car base. Reflects environment like liquid metal.", swatch: "#e8e8ee" },
    { id: "chrome_wrap", name: "Chrome Wrap", desc: "Mirror chrome vinyl film — like chrome but with subtle stretch marks and wrap texture. Film-based, not paint.", swatch: "#dde0ee" },
    { id: "clear_matte", name: "Clear Matte", desc: "Flat clearcoat with real protection — unlike raw matte, resists UV and scratches. Matte look, clearcoat durability.", swatch: "#aabbaa", colorSafe: true },
    { id: "cobalt_metal", name: "Cobalt Metal", desc: "Blue-gray cobalt metallic — cool industrial tone darker than silver, bluer than gunmetal. Aerospace builds.", swatch: "#4466aa" },
    { id: "color_flip_wrap", name: "Angle Flip Wrap", desc: "Dichroic-style wrap — micro-spec drives angle-resolved color flip. Math-generated in seconds.", swatch: "#8866aa" },
    { id: "copper", name: "Copper", desc: "Warm oxidized copper metallic — rich bronze-gold tone with natural patina character. Pairs beautifully with celtic patterns.", swatch: "#cc7744" },
    { id: "crystal_clear", name: "Lucid Dream Water", desc: "Crystal-clear wet coating — ultra-smooth, glass-like surface with soft refraction", swatch: "#F0FFFF" },
    { id: "crumbling_clear", name: "Crumbling Clear", desc: "Peeling, crumbling clearcoat — paint underneath showing through where the topcoat has failed. Authentic decade-old rusted-out look.", swatch: "#887766", colorSafe: true },
    { id: "dark_chrome", name: "Abyssal Tungsten", desc: "Near-black heavy metal — rough oxidized surface that absorbs most light", swatch: "#1C1C1C" },
    { id: "dark_matter", name: "Void Reveal", desc: "Ultra-dark base — fine micro-spec variation reveals vivid color on curves when light grazes. Built mathematically.", swatch: "#111122" },
    { id: "dealer_pearl", name: "Dealer Pearl", desc: "Dealer-lot premium tri-coat pearl upgrade — the factory upsell finish with subtle shimmer and soft flop", swatch: "#dde0e8" },
    { id: "desert_worn", name: "Desert Worn", desc: "Sand-blasted and sun-bleached — the look of a car that lived in the desert. Faded, rough, wind-worn character.", swatch: "#bbaa88" },
    { id: "destroyed_coat", name: "Destroyed Coat", desc: "Completely destroyed clearcoat — maximum degradation, pure chalk-rough surface stripped to primer in places. Junkyard authenticity.", swatch: "#555544", colorSafe: true },
    { id: "diamond_coat", name: "Diamond Coat", desc: "Diamond dust ultra-fine sparkle coat — micro-crystal glitter sealed in deep clear for show car brilliance", swatch: "#ccddee", colorSafe: true },
    { id: "drag_strip_gloss", name: "Drag Strip Gloss", desc: "Ultra-polished drag strip show gloss — mirror-wet quarter-mile paint for heads-up racing and car shows", swatch: "#dd4444" },
    { id: "dragonfly_wing", name: "Dragonfly Wing", desc: "Transparent wing membrane with rainbow interference — biological thin-film optics with delicate vein network detail", swatch: "#AADDEE" },
    { id: "duracoat", name: "Duracoat", desc: "Tactical epoxy DuraCoat — mil-spec firearm-grade protective finish, flat and chemical-resistant for builds", swatch: "#556644" },
    { id: "eggshell", name: "Eggshell", desc: "Soft low-sheen eggshell — gentle warmth between flat and satin, like fine interior wall paint on a car body", swatch: "#ddddcc", colorSafe: true },
    { id: "electric_ice", name: "Electric Ice", desc: "Icy electric blue metallic with cold neon shimmer — frozen lightning trapped in pale blue metal flake", swatch: "#88ccee" },
    { id: "enamel", name: "Enamel", desc: "Hard baked enamel — traditional glossy paint with deep color and thick old-school body. Classic restorations.", swatch: "#4488aa" },
    { id: "endurance_ceramic", name: "Apollo Shield Char", desc: "Scorched ceramic heat shield — charred brown-black with rough ablative texture", swatch: "#2F2016" },
    { id: "factory_basecoat", name: "Factory Basecoat", desc: "Standard OEM factory metallic basecoat — what rolls off the assembly line. Clean, consistent, production-spec.", swatch: "#99aabc", colorSafe: true },
    { id: "ferrari_rosso", name: "Magma Core", desc: "Surface cooling magma with deep incandescent red subsurface scattering", swatch: "#880000", colorSafe: true },
    { id: "firefly_glow", name: "Firefly Glow", desc: "Dark exoskeleton with bioluminescent yellow-green lantern zones", swatch: "#88cc22" },
    { id: "fiberglass", name: "Fiberglass", desc: "Raw fiberglass gelcoat — slightly wavy semi-gloss surface straight from the mold before any finish paint", swatch: "#aaddee" },
    { id: "fire_engine", name: "Fire Engine", desc: "Deep wet fire apparatus red — thick glossy emergency red with maximum visibility. Classic American fire truck.", swatch: "#cc2222" },
    { id: "flat_black", name: "Flat Black", desc: "Dead flat zero shine — like matte but even more extreme. No clearcoat at all. Raw paint surface. Military/rat rod essential.", swatch: "#0a0a0a", colorSafe: true },
    { id: "f_pure_white", name: "Pure White (Foundation)", desc: "Plain solid white reference base — no texture or effect, just clean color. Use to isolate pattern work", swatch: "#f5f5f5", colorSafe: true },
    { id: "f_pure_black", name: "Pure Black (Foundation)", desc: "Plain solid black reference base — zero texture, zero effect. Darkest clean starting point for pattern overlays", swatch: "#0a0a0a", colorSafe: true },
    { id: "f_neutral_grey", name: "Neutral Grey (Foundation)", desc: "Plain mid-tone grey reference base — neutral and flat. Best for evaluating patterns without color bias", swatch: "#6a6a6a", colorSafe: true },
    { id: "f_soft_gloss", name: "Soft Gloss (Foundation)", desc: "Plain glossy reference base — smooth reflective surface without metallic flake. Clean sponsor-safe starting point", swatch: "#8899aa", colorSafe: true },
    { id: "f_soft_matte", name: "Soft Matte (Foundation)", desc: "Plain flat matte reference base — zero sheen, zero texture. The simplest non-reflective foundation", swatch: "#555555", colorSafe: true },
    { id: "f_clear_satin", name: "Clear Satin (Foundation)", desc: "Plain satin clearcoat reference base — soft sheen without metallic. Balanced between gloss and matte foundations", swatch: "#99aabb", colorSafe: true },
    { id: "f_warm_white", name: "Warm White (Foundation)", desc: "Plain warm-toned white reference base — slightly creamy, no texture. Softer than pure white foundation", swatch: "#e8e4dc", colorSafe: true },
    { id: "f_chrome", name: "Chrome (Foundation)", desc: "Plain mirror chrome reference base — full reflectivity, no color tint. Use when you want raw chrome under patterns", swatch: "#e8e8ee", colorSafe: true },
    { id: "f_satin_chrome", name: "Satin Chrome (Foundation)", desc: "Plain satin chrome reference base — brushed metallic sheen without color. Softer than mirror chrome foundation", swatch: "#ccccdd", colorSafe: true },
    { id: "f_metallic", name: "Metallic (Foundation)", desc: "Plain metallic reference base — flat metallic material (M/R tuned for metallic look), no baked-in flake or angle play. Clean baseline for layering a Spec Pattern Overlay on top.", swatch: "#99AACC", colorSafe: true },
    { id: "f_pearl", name: "Pearl (Foundation)", desc: "Plain pearlescent reference base — soft rainbow shimmer, no color tint. Clean pearl starting point for overlays", swatch: "#dde0e8", colorSafe: true },
    { id: "f_carbon_fiber", name: "Carbon Fiber (Foundation)", desc: "Plain carbon fiber reference base — flat dark material tuned for carbon look, no baked-in weave or resin pooling. Add a carbon-weave Spec Pattern Overlay for visible weave texture.", swatch: "#333333", colorSafe: true },
    { id: "f_brushed", name: "Brushed (Foundation)", desc: "Plain brushed-metallic reference base — flat metallic material tuned for a brushed look, no baked-in grain or brush lines. Add a brushed-grain Spec Pattern Overlay for visible linear grain.", swatch: "#99AAAA", colorSafe: true },
    { id: "f_frozen", name: "Frozen (Foundation)", desc: "Plain frozen matte reference base — cold icy sheen, no crystal detail. Simpler than the enhanced frozen version", swatch: "#99bbcc", colorSafe: true },
    { id: "f_powder_coat", name: "Powder Coat (Foundation)", desc: "Thick powder coating texture foundation — uniform durable surface, the industrial-tough baseline for tactical and utility builds.", swatch: "#667755", colorSafe: true },
    { id: "f_anodized", name: "Anodized (Foundation)", desc: "Plain anodized aluminum reference base — dyed oxide layer, no pore detail. Clean tech-metal starting point", swatch: "#7788aa", colorSafe: true },
    { id: "f_vinyl_wrap", name: "Vinyl Wrap (Foundation)", desc: "Plain vinyl wrap reference base — smooth film surface, no stretch marks or conform lines. Basic wrap look", swatch: "#555555", colorSafe: true },
    { id: "f_gel_coat", name: "Gel Coat (Foundation)", desc: "Plain fiberglass gelcoat reference base — flat high-gloss material, no baked-in flow-out waves. The marine and kit-car classic baseline.", swatch: "#AADDEE", colorSafe: true },
    { id: "f_baked_enamel", name: "Baked Enamel (Foundation)", desc: "Hard baked traditional enamel foundation — kiln-fired thick gloss like vintage refrigerator paint. Solid restoration baseline.", swatch: "#4488AA", colorSafe: true },
    { id: "fleet_white", name: "Hyper-Bleach Alabaster", desc: "The purest synthetic white designed to actively blow out localized camera sensors", swatch: "#FFFFFF" },
    { id: "forged_composite", name: "Forged Composite", desc: "Lamborghini-style forged carbon composite — random chopped fiber swirl pattern sealed in deep resin clear", swatch: "#555555" },
    { id: "frozen", name: "Frozen", desc: "Icy matte metallic — cold crystal texture like frost on metal. Unique look between chrome and matte.", swatch: "#99bbcc", colorSafe: true },
    { id: "frozen_matte", name: "Frozen Matte", desc: "BMW Individual frozen matte metallic — icy crystal sheen with zero gloss, the original luxury frozen paint", swatch: "#99aabb", colorSafe: true },
    { id: "galvanized", name: "Galvanized", desc: "Hot-dip galvanized zinc crystalline spangle — raw industrial zinc coating with visible crystal flower pattern", swatch: "#aabbbb" },
    { id: "gloss", name: "Gloss", desc: "Clean smooth gloss paint — non-metallic, pure color. The safest choice for readable sponsors and numbers.", swatch: "#44aa44", colorSafe: true },
    { id: "gloss_wrap", name: "Gloss Wrap", desc: "Glossy vinyl wrap film — smooth high-shine like paint gloss but removable and uniform. No metallic, pure clean color.", swatch: "#44aa66" },
    { id: "graphene", name: "Graphene", desc: "Single-layer graphene ultra-thin metallic — futuristic nano-material with subtle dark iridescence and depth", swatch: "#889999" },
    { id: "gunmetal", name: "Gunmetal", desc: "Dark blue-gray metallic — aggressive, industrial, masculine. The go-to for tactical and military-inspired builds.", swatch: "#556677", colorSafe: true },
    { id: "gunship_gray", name: "Gunship Gray", desc: "Military gunship flat gray — non-reflective aircraft coating for attack helicopters and close-air-support builds", swatch: "#666677" },
    { id: "heat_treated", name: "Heat Treated", desc: "Heat-treated titanium with blue-gold oxide zones — temper colors from welding heat on raw aerospace metal", swatch: "#7788cc" },
    { id: "holographic_base", name: "Holographic Base", desc: "Full holographic rainbow prismatic base — bright spectral color shift across the entire surface at every angle", swatch: "#aa88dd" },
    { id: "hybrid_weave", name: "Hybrid Weave", desc: "Carbon-kevlar hybrid bi-weave — alternating black carbon and gold aramid threads in a tight diagonal pattern", swatch: "#666655" },
    { id: "iridescent", name: "Bifrost Crystal", desc: "Rainbow prismatic metallic — strong color shift across viewing angles", swatch: "#E1A1FF" },
    { id: "jelly_pearl", name: "Jelly Pearl", desc: "Translucent jelly-like pearl coating with deep shimmer — semi-transparent gel surface that lets the base color glow through", swatch: "#DDBBEE", colorSafe: true },
    { id: "kevlar_base", name: "Kevlar Base", desc: "Same aramid as bulletproof vests — tough golden fiber weave. Pairs with carbon for hybrid. Tactical/military builds.", swatch: "#998844" },
    { id: "koenigsegg_clear", name: "Koenigsegg Clear", desc: "Clear-coated visible carbon weave Koenigsegg style — exposed fiber under deep glossy resin shell", swatch: "#3d3020" },
    { id: "lamborghini_verde", name: "Lambo Verde", desc: "Lamborghini Verde Mantis electric green — vivid acid-bright hue that screams Italian supercar aggression", swatch: "#33cc55" },
    { id: "liquid_titanium", name: "Liquid Titanium", desc: "Molten titanium pooling mirror — liquid-metal sheen with warm gray tone and flowing reflective highlights", swatch: "#8899aa" },
    { id: "liquid_wrap", name: "Liquid Wrap", desc: "PlastiDip-style removable rubber coat — textured matte you can peel off later. Temporary builds and experiments.", swatch: "#8866aa" },
    { id: "living_matte", name: "Living Matte", desc: "Organic living matte — subtle biological sheen that shifts softly like skin or natural material under light", swatch: "#666666", colorSafe: true },
    { id: "matte", name: "Matte", desc: "Dead flat with zero reflection — stealth, military, DTM race looks. Absorbs light completely. Great under carbon fiber.", swatch: "#666666", colorSafe: true },
    { id: "matte_wrap", name: "Matte Wrap", desc: "Dead-flat vinyl film — zero sheen like matte paint but removable. No orange peel. Cleaner flat than spray matte.", swatch: "#555555" },
    { id: "maybach_two_tone", name: "Maybach Two-Tone", desc: "Mercedes-Maybach duo-tone luxury split — formal upper/lower color divide with chrome accent separation line", swatch: "#4a4035", colorSafe: true },
    { id: "mclaren_orange", name: "McLaren Orange", desc: "McLaren Papaya Spark vivid orange — the iconic British racing orange from Woking, bold and unmistakable", swatch: "#ee6622" },
    { id: "mercury", name: "Mercury", desc: "Liquid mercury pooling chrome — cool desaturated silver with flowing liquid-metal movement and soft reflection", swatch: "#bbccdd" },
    { id: "metal_flake_base", name: "Metal Flake", desc: "Heavy visible metal flake basecoat — large glitter particles in clear for bold 1960s custom car sparkle", swatch: "#99aacc", colorSafe: true },
    { id: "original_metal_flake", name: "Supernova Flake", desc: "Exploding star massive metallic chunks sealed in aerospace clear", swatch: "#FFD700", colorSafe: true },
    { id: "champagne_flake", name: "Midas Touch Gold", desc: "A hyper-reflective pure 24K gold with absolute 0 roughness and high metal flake scaling", swatch: "#FFDF00" },
    { id: "fine_silver_flake", name: "Starlight Mica Resin", desc: "A dielectric clear thick resin suspending pure crushed silver mica shards", swatch: "#E0E0E0", colorSafe: true },
    { id: "blue_ice_flake", name: "Permafrost Crystalline", desc: "Jagged frozen ice fractals catching deep light in a frozen state", swatch: "#ADD8E6" },
    { id: "bronze_flake", name: "Antediluvian Brass", desc: "10,000-year oxidized shipwreck brass, aggressively dripping with rich verdigris", swatch: "#8C7853" },
    { id: "gunmetal_flake", name: "Bismuth Crystal Flake", desc: "Geometric stair-step oxidation layering of Bismuth - mind-bending refractive angles", swatch: "#8A3B66" },
    { id: "green_flake", name: "Kryptonite Shards", desc: "Dark space meteorite that fades to an intense glowing neon green at its specular angles", swatch: "#00FF00" },
    { id: "fire_flake", name: "Solar Flare Ejecta", desc: "The violent surface of the sun exploding with massive bright spots of solar plasma", swatch: "#FFA500" },
    { id: "metallic", name: "Metallic", desc: "Classic automotive metallic — visible metal flake particles in clearcoat. The standard race car base. Sponsor-safe.", swatch: "#aabbcc", colorSafe: true },
    { id: "midnight_pearl", name: "Midnight Pearl", desc: "Deep dark pearlescent with hidden sparkle — nearly black until light catches the pearl shift underneath", swatch: "#dde0e8", colorSafe: true },
    { id: "mil_spec_od", name: "Mil-Spec OD", desc: "Olive drab mil-spec CARC coating — flat OD green per military standard for tactical ground vehicle builds", swatch: "#556644" },
    { id: "mil_spec_tan", name: "Martian Regolith Dust", desc: "Extremely rusty, iron-rich, harsh and gritty red dirt directly from the surface of Mars", swatch: "#AE684F" },
    { id: "mirror_gold", name: "Mirror Gold", desc: "Pure mirror gold chrome — full 24k gold reflective surface like a Dubai showpiece, maximum opulence on wheels", swatch: "#ddaa33" },
    { id: "moonstone", name: "Moonstone", desc: "Soft translucent milky moonstone shimmer — pale opalescent glow like the real gemstone with internal light play", swatch: "#ccccdd" },
    { id: "moth_luna", name: "Moth Luna", desc: "Pale green Luna moth wing with delicate eye-spot markings — soft pastel insect-inspired organic texture", swatch: "#99cc88" },
    { id: "neutron_star", name: "Accretion Ring", desc: "Void black sink with a sharp micro-spec ring — light grazing the edge explodes into color. Procedural.", swatch: "#0A0A0A" },
    { id: "obsidian", name: "Obsidian", desc: "Volcanic obsidian glass — razor-sharp deep black with mirror sheen like polished igneous rock. Dramatic depth.", swatch: "#0a0a12" },
    { id: "opal", name: "Dragon's Pearl Scale", desc: "Massive multi-colored shifting pearl mimicking the biological armored plate of a dragon", swatch: "#E6E6FA" },
    { id: "orange_peel_gloss", name: "Orange Peel Gloss", desc: "Orange-peel texture sealed under thick clearcoat — intentional factory paint ripple for authentic OEM character", swatch: "#ddaa55", colorSafe: true },
    { id: "organic_metal", name: "Organic Metal", desc: "Living organic metallic with subtle biological shimmer — like skin made of metal, alien biotech aesthetic for sci-fi builds.", swatch: "#778866", colorSafe: true },
    { id: "oxidized_copper", name: "Oxidized Copper", desc: "Fully green patina copper — Statue of Liberty look. Rich verdigris over warm copper base. Dramatic weathered effect.", swatch: "#55aa88" },
    { id: "pace_car_pearl", name: "Pace Car Pearl", desc: "Official pace car triple-pearl coat — premium tri-stage white pearl with deep sparkle for parade lap builds", swatch: "#dde0e8" },
    { id: "pagani_tricolore", name: "Tricolore", desc: "Tri-tone angle-resolved shift — premium multi-angle reveal. Procedural micro-spec.", swatch: "#8844aa" },
    { id: "patina_bronze", name: "Patina Bronze", desc: "Museum statue bronze — green verdigris over warm brown metal. Oxidized copper-tin alloy. Art car and statement builds.", swatch: "#668855" },
    { id: "pearl", name: "Pearl", desc: "Soft color-shifting iridescence — subtle rainbow shimmer that changes with viewing angle. Premium OEM upgrade finish.", swatch: "#dde0e8", colorSafe: true },
    { id: "pearlescent_white", name: "Pearl White", desc: "Tri-coat pearlescent white with deep sparkle — three-stage pearl that shifts pink-blue in direct sunlight", swatch: "#e8e8ff" },
    { id: "pewter", name: "Necromantic Lead", desc: "A dark, cursed grey meta-lead finish pulsing with forbidden underworld geometry", swatch: "#666666" },
    // 2026-04-20 HEENAN HSIG-FOUND-1 — name-honesty fix.
    // The display name "Vortex Ebony Depth" was unfindable: every painter
    // searches "piano black" and got zero hits in the Foundation lane. The
    // poetic name is preserved as a parenthetical so the tile still reads
    // as premium without breaking discoverability.
    { id: "piano_black", name: "Piano Black (Vortex Depth)", desc: "Mirror-deep piano-black lacquer with a swirling ebony-ink interior that bends environment reflections inward upon themselves — Audi/BMW-style trim depth on a full body.", swatch: "#030303", colorSafe: true },
    { id: "plasma_core", name: "Plasma Core", desc: "Reactor-core metallic — angle-resolved micro-spec creates electric purple-blue reveal on curves.", swatch: "#8844ff" },
    { id: "plasma_metal", name: "Alien Smart-Material", desc: "Extraterrestrial smart-metal with dynamic phase-shifting liquid surface", swatch: "#5E2D85" },
    { id: "platinum", name: "Platinum", desc: "Pure platinum bright white metal — cooler and heavier than silver chrome, with a refined blue-white undertone", swatch: "#dddde8" },
    { id: "police_black", name: "Police Black", desc: "Law enforcement glossy black — high-gloss patrol car black with clean reflective surface for authority presence", swatch: "#111111", colorSafe: true },
    { id: "porcelain", name: "Shattered Bone Marrow", desc: "Fractured monolithic bone ivory finish with subsurface micro-cracks", swatch: "#E2E2D0" },
    { id: "porsche_pts", name: "Porsche PTS", desc: "Porsche Paint-to-Sample custom deep coat — bespoke factory color from the PTS catalog, ultra-exclusive OEM", swatch: "#2a2438", colorSafe: true },
    { id: "powder_coat", name: "Powder Coat", desc: "Thick electrostatic powder coating — industrial, durable, slightly textured. Like wheel powder coat on a whole car.", swatch: "#6666bb" },
    { id: "primer", name: "Primer", desc: "Raw gray primer — no clearcoat, no metallic, just bare primer surface. Unfinished build / project car aesthetic.", swatch: "#808080", colorSafe: true },
    { id: "quantum_black", name: "Quantum Black", desc: "Near-perfect light absorption ultra-black — almost vantablack darkness that flattens all surface detail", swatch: "#111111" },
    { id: "race_day_gloss", name: "Hyper-Ceramic Shell", desc: "Next-gen aerospace thermal tile - optically perfect liquid seal", swatch: "#FFFFFF" },
    { id: "rally_mud", name: "Rally Mud", desc: "Partially mud-splattered rally coating — wet dirt spray pattern over paint from hard off-road stage driving", swatch: "#886644" },
    { id: "raw_aluminum", name: "Raw Aluminum", desc: "Bare unfinished aluminum sheet metal — raw mill finish with no polish or clear, industrial and unrefined", swatch: "#aabbcc" },
    { id: "red_chrome", name: "Vampire Chrome", desc: "Blood-tinted chrome with UV-reactive subsurface thick clearcoat", swatch: "#660000" },
    { id: "rose_gold", name: "Synthesized Biomech Flesh", desc: "Disturbing synthetic flesh tone utilizing organic subsurface scattering algorithms", swatch: "#FFC0CB" },
    { id: "rugged", name: "Rugged", desc: "Rugged off-road tactical coating — thick rough-textured protective finish for overlanders and trail rigs", swatch: "#665544" },
    { id: "salt_corroded", name: "Salt Corroded", desc: "Coastal salt-air damage — white salt deposits, pitting, and corrosion. Northeast winter / beach car look.", swatch: "#aabbaa" },
    { id: "sandblasted", name: "Sandblasted", desc: "Raw sandblasted metal — coarse pitted surface from abrasive blasting, stripped bare before paint or left raw", swatch: "#999999" },
    { id: "scarab_gold", name: "Scarab Gold", desc: "Egyptian scarab beetle golden-green iridescent shift — ancient sacred jewel tone with metallic color flip", swatch: "#aacc22" },
    { id: "satin", name: "Satin", desc: "Between gloss and matte — soft sheen without harsh reflections. Understated elegance, great for professional liveries.", swatch: "#9999a0", colorSafe: true },
    { id: "satin_chrome", name: "Satin Chrome", desc: "Softer chrome with directional brushed sheen — BMW M4 style. Less mirror, more silk. Distinct from Mirror Chrome.", swatch: "#bbcccc" },
    { id: "satin_gold", name: "Satin Gold", desc: "Satin gold metallic with warm sheen — soft brushed gold without mirror glare, elegant for luxury accents", swatch: "#c9a227" },
    { id: "satin_metal", name: "Satin Metal", desc: "Subtle brushed satin metallic — soft directional grain with muted flake, quieter than chrome or gloss metal", swatch: "#8899a8", colorSafe: true },
    { id: "satin_wrap", name: "Satin Wrap", desc: "Satin-finish vinyl wrap — soft sheen without metallic flake. Removable unlike paint satin. Cleaner and more uniform.", swatch: "#777788" },
    { id: "scuffed_satin", name: "Scuffed Satin", desc: "Scuffed satin with micro-abrasion marks — lightly worn version of satin that shows use and subtle damage", swatch: "#999999", colorSafe: true },
    { id: "school_bus", name: "Hazard Synthetics", desc: "High-visibility radioactive safety polymer that practically glows under light", swatch: "#FFD700" },
    { id: "semi_gloss", name: "Semi-Gloss", desc: "Between satin and gloss — practical utility finish with moderate sheen, good for fleet and functional builds", swatch: "#44aa44", colorSafe: true },
    // 2026-04-19 HEENAN HSHKBASE — promoted to dedicated spec/paint pair.
    { id: "shokk_blood", name: "SHOKK Blood", desc: "Arterial vein topology — bright red base broken by darker venous cracks tracking the spec ridges. Reads as wet blood glossing on dried crust.", swatch: "#aa1122" },
    // 2026-04-19 HEENAN HB3 (modified) — Bockwinkel flagged the engine paint_fn
    // (paint_electric_blue_tint) as contradicting the swatch (hot pink). On
    // closer reading the engine registry desc explicitly says "hot-pink/blue",
    // i.e. an intentional pink↔blue color-shift. JS desc updated to honestly
    // surface that to painters so the rendered output matches expectation.
    { id: "shokk_pulse", name: "SHOKK Pulse", desc: "Hot pink ⇄ electric blue color-shift metallic — pulse wave that flips between the two as the angle changes. Bold and unmistakable.", swatch: "linear-gradient(135deg, #ff3366 0%, #3366ff 100%)" },
    { id: "shokk_static", name: "SHOKK Static", desc: "SHOKK signature static noise — crackling interference texture over cool metallic. TV-snow energy disruption look", swatch: "#8888cc" },
    // 2026-04-19 HEENAN HSHKBASE — promoted to dedicated spec/paint pair.
    { id: "shokk_venom", name: "SHOKK Venom", desc: "Toxic ceramic with reactive pools — acid green-yellow base with brighter neon-green wet zones where the spec smooths into chemical pools.", swatch: "#66dd22" },
    // 2026-04-19 HEENAN HSHKBASE — promoted to dedicated spec/paint pair.
    // Sparse glints (~0.3% of pixels) at sharpest Perlin edge crests now
    // give real "subtle edge shimmer" instead of an evenly-rough surface.
    { id: "shokk_void", name: "SHOKK Void", desc: "Vantablack absorption with rare edge shimmer — pure light-eating black except for sparse white glints that reveal the form at sharp angles.", swatch: "#080810" },
    { id: "shokk_flux", name: "SHOKK Flux", desc: "Thin-film interference — procedural CC thickness drives wavelength-selective reflection. Seconds, not hand layers.", swatch: "#88ddff" },
    { id: "shokk_phase", name: "SHOKK Phase", desc: "Liquid crystal domain simulation - per-domain metallic variation creates angle-dependent activation", swatch: "#cc44ff" },
    { id: "shokk_dual", name: "SHOKK Dual", desc: "Hard chromatic binary flip - two complementary colors in Voronoi tessellation", swatch: "#ff4488" },
    { id: "shokk_spectrum", name: "SHOKK Spectrum", desc: "Diffraction grating — micro-groove roughness reveals spectral bands at angle. Math-generated, no foil sheets.", swatch: "#ff8800" },
    { id: "shokk_aurora", name: "SHOKK Aurora", desc: "Fresnel curtain — flowing sine-wave folds, differential micro-spec. Angle-resolved in one procedural pass.", swatch: "#44ff88" },
    { id: "shokk_helix", name: "SHOKK Helix", desc: "Double-strand complementary spiral - R/CC phase opposition swaps dominant strand", swatch: "#ff44cc" },
    { id: "shokk_catalyst", name: "SHOKK Catalyst", desc: "BZ reaction wavefront - four-phase spiral with distinct Fresnel per chemical phase", swatch: "#ffcc22" },
    { id: "shokk_mirage", name: "SHOKK Mirage", desc: "Thermal gradient refraction - heat-shimmer domain warp on ultra-smooth metallic", swatch: "#aabbcc" },
    { id: "shokk_polarity", name: "SHOKK Polarity", desc: "Magnetic domain visualization - Ising model with hyper-reflective boundary flash network", swatch: "#4488ff" },
    { id: "shokk_reactor", name: "SHOKK Reactor", desc: "Cherenkov radiation glow - stable dielectric cores anchor shifting metallic field", swatch: "#00ccff" },
    // 2026-04-19 HEENAN HB1 — id/name disagreement: id is `shokk_prism`,
    // display name was "SHOKK Caustic". Bockwinkel SHOKK audit. Aligned to
    // the id (the brand list refers to it as Prism). Desc retained.
    { id: "shokk_prism", name: "SHOKK Prism", desc: "Caustic refraction — CC thickness variation drives concentrated light bands. Math-generated, not hand-tuned.", swatch: "#ee66ff" },
    // 2026-04-19 HEENAN HSTING1 — Sting copy fix: was engineer-speak.
    { id: "shokk_wraith", name: "SHOKK Wraith", desc: "Ghostly dithered metallic that softens at distance and sharpens up close — wraith-like depth, no two angles look the same.", swatch: "#666688" },
    // 2026-04-19 HEENAN HS2 — Sting flagged "V2" in customer-facing display
    // name as dev-sloppiness. Id keeps `_v2` suffix for legacy compatibility
    // (saved configs reference it); display name drops the version tag.
    { id: "shokk_tesseract_v2", name: "SHOKK Tesseract", desc: "4D hypercube projection — six overlapping faces with distinct spec per face", swatch: "#8866dd" },
    { id: "shokk_fusion_base", name: "SHOKK Fusion", desc: "Tokamak plasma confinement - toroidal geometry with blackbody temperature-mapped spec", swatch: "#ff6622" },
    { id: "shokk_rift", name: "SHOKK Rift", desc: "Fracture network — warm/cool split zones with mirror-bright crack edges", swatch: "#cc2266" },
    { id: "shokk_vortex", name: "SHOKK Vortex", desc: "Logarithmic spiral color drain - dual-spiral Moire interference shifts with angle", swatch: "#ff22dd" },
    { id: "shokk_surge", name: "SHOKK Surge", desc: "Standing wave superposition - constructive/destructive nodes with non-repeating pattern", swatch: "#44ddcc" },
    { id: "shokk_cipher", name: "SHOKK Cipher", desc: "Steganographic encoding - hidden pattern emerges via Fresnel amplification", swatch: "#556677" },
    { id: "shokk_inferno", name: "SHOKK Inferno", desc: "Blackbody radiation temperature map - Planck's law M/R follows thermodynamics", swatch: "#ff4400" },
    // 2026-04-19 HEENAN HSTING2 — Sting copy fix: was build-log-style.
    { id: "shokk_apex", name: "SHOKK Apex", desc: "All SHOKK techniques layered into one finish — spectral, dithered, grooved, and thin-film together. The flagship's flagship.", swatch: "#dd88ff" },
    { id: "showroom_clear", name: "Bioluminescent Slime", desc: "Bright green wet membrane — glossy slime-like surface with vivid glow effect", swatch: "#A2FF00" },
    { id: "silk", name: "Silk", desc: "Between satin and gloss — fabric-like soft sheen, no harsh reflections. Smoother than satin, less wet than gloss.", swatch: "#9999bb", colorSafe: true },
    { id: "smoked", name: "Demon's Breath Particle Shift", desc: "Deep charcoal gray with smoky internal depth — dark semi-transparent particle texture", swatch: "#2A2A2A" },
    { id: "solar_panel", name: "Solar Panel", desc: "Photovoltaic solar cell dark blue-black — silicon wafer grid pattern with anti-reflective tech surface look", swatch: "#223366" },
    { id: "spectraflame", name: "Sentient Polycarbonate", desc: "Clear optical polymer with internal color shift — changes tone under different lighting angles", swatch: "#CCFAFA" },
    { id: "bullseye_chrome", name: "Liquid Gallium", desc: "Room-temperature liquid metal, dynamic pooling specular highlights", swatch: "#B8B8C2" },
    { id: "stealth_wrap", name: "Active Camo Mesh", desc: "Dark stealth mesh — aggressive matte with fine light-scatter texture", swatch: "#1A1D1A" },
    { id: "stock_car_enamel", name: "Stock Car Enamel", desc: "Traditional thick NASCAR stock car enamel — heavy old-school race paint with deep gloss and bold body color", swatch: "#4488aa" },
    { id: "submarine_black", name: "Sub Black", desc: "Anechoic submarine hull coating — deep sonar-absorbing black with rubbery texture from naval stealth tiles", swatch: "#0a0a0f" },
    { id: "sun_baked", name: "Sun Baked", desc: "UV-damaged sun-faded paint with peeling clear — years of desert sun exposure, chalky and cracking on top", swatch: "#cc9966" },
    { id: "sun_fade", name: "Sun Fade", desc: "UV sun-damaged paint — bleached, chalky, coat breaking down from years of sunlight exposure on a southwest patina car.", swatch: "#CCBB99", colorSafe: true },
    { id: "superconductor", name: "Absolute Zero Cryo-Frost", desc: "Heavily frosted metal sitting indefinitely at absolute zero, perpetually generating micro-ice", swatch: "#E0FFFF" },
    { id: "surgical_steel", name: "Adamantium Plate", desc: "Indestructible weaponized metal alloy exhibiting incredibly aggressive, deep brushing gouges", swatch: "#C0C0C0", colorSafe: true },
    { id: "taxi_yellow", name: "Brimstone Exudate", desc: "Toxic sulfur-yellow cracked magma rock material, hot to the touch", swatch: "#DAB100" },
    { id: "tempered_glass", name: "Tempered Glass", desc: "Tempered safety glass — smooth hard transparent surface like automotive windshield glass, clean and brittle", swatch: "#99ccdd", colorSafe: true },
    { id: "textured_wrap", name: "Textured Wrap", desc: "Bumpy orange-peel textured vinyl — intentional texture like factory paint defect. Hides imperfections, adds character.", swatch: "#888866" },
    { id: "tinted_clear", name: "Tinted Clear", desc: "Deep tinted clearcoat over base color — adds rich amber or smoke tone to underlying paint for extra depth", swatch: "#449977" },
    { id: "titanium_raw", name: "Titanium Raw", desc: "Raw unpolished titanium — industrial gray-blue aerospace metal with natural grain and subtle warm undertone", swatch: "#8899aa" },
    { id: "tri_coat_pearl", name: "Tri-Coat Pearl", desc: "Three-stage pearl with base, mid-coat, and clear — premium factory process for maximum depth and color shift", swatch: "#dde0ee" },
    { id: "tungsten", name: "Tungsten", desc: "Ultra-dense dark gray tungsten — the heaviest common metal, brooding and nearly black with subtle cool sheen", swatch: "#556677" },
    { id: "vantablack", name: "Vantablack", desc: "Absolute void — absorbs 99.9% of light. No reflection, no shape, just darkness. Dramatic under stardust or lightning.", swatch: "#020204", colorSafe: true },
    { id: "victory_lane", name: "Victory Lane", desc: "Champagne-soaked celebration metallic sparkle — gold-tinged glitter finish for the post-race winner circle", swatch: "#ddbb44", colorSafe: true },
    { id: "vintage_chrome", name: "Vintage Chrome", desc: "1950s chrome with cloudy oxidation spots — aged patina and pitting from decades of weather, classic era look", swatch: "#aabbcc" },
    { id: "volcanic", name: "Volcanic", desc: "Dark gritty ash texture — rough, desaturated, primal. Like cooled lava. Best with fracture, lightning, or plasma patterns.", swatch: "#cc4422" },
    { id: "wasp_warning", name: "Wasp Warning", desc: "Yellow-black aposematic banding with metallic shimmer — predator-deterrent insect coloring for high-visibility builds", swatch: "#EECC11" },
    { id: "wet_look", name: "Wet Look", desc: "Fresh-waxed show car depth — ultra-wet clearcoat that looks perpetually just-detailed. Concours and magazine covers.", swatch: "#337755", colorSafe: true },
    // ── ENHANCED FOUNDATION (30 premium bases with spec+paint functions) ──
    { id: "enh_gloss", name: "★ Enhanced Gloss", desc: "Premium gloss with micro-ripple shimmer — more wet depth and surface detail than the plain gloss foundation", swatch: "#55aacc", colorSafe: true },
    { id: "enh_matte", name: "★ Enhanced Matte", desc: "Premium matte with organic micro-grain pore texture — more surface character than the plain matte foundation", swatch: "#667766", colorSafe: true },
    { id: "enh_satin", name: "★ Enhanced Satin", desc: "Premium satin with directional brushed grain and warm sheen — richer surface detail than the plain satin foundation", swatch: "#99aa88", colorSafe: true },
    { id: "enh_metallic", name: "★ Enhanced Metallic", desc: "Premium metallic with visible flake sparkle and depth variation — more flake pop than the plain metallic foundation", swatch: "#aabb99", colorSafe: true },
    { id: "enh_pearl", name: "★ Enhanced Pearl", desc: "Premium pearl with iridescent micro-shift shimmer — more color play and depth than the plain pearl foundation", swatch: "#ccbbdd", colorSafe: true },
    { id: "enh_chrome", name: "★ Enhanced Chrome", desc: "Premium chrome with environment distortion and reflection warping — more realism than the plain chrome foundation", swatch: "#dddddd", colorSafe: true },
    { id: "enh_satin_chrome", name: "★ Enhanced Satin Chrome", desc: "Premium satin chrome with deeper directional grain — more brushed texture than the plain satin chrome foundation", swatch: "#bbcccc", colorSafe: true },
    { id: "enh_anodized", name: "★ Enhanced Anodized", desc: "Premium anodized with visible oxide variation and pore detail — more surface realism than the plain anodized foundation", swatch: "#7799bb", colorSafe: true },
    { id: "enh_baked_enamel", name: "★ Enhanced Baked Enamel", desc: "Premium baked enamel with kiln-fired warmth and depth variation — richer gloss than the plain enamel foundation", swatch: "#5588aa", colorSafe: true },
    { id: "enh_brushed", name: "★ Enhanced Brushed", desc: "Premium brushed metal with deeper grain and metallic variation — richer detail than foundation. Worth it up close.", swatch: "#889999", colorSafe: true },
    { id: "enh_carbon_fiber", name: "★ Enhanced Carbon Fiber", desc: "Premium carbon fiber with visible resin pooling and depth — more weave detail than foundation. Worth the render cost.", swatch: "#445566", colorSafe: true },
    { id: "enh_frozen", name: "★ Enhanced Frozen", desc: "Premium frozen with crystal texture and frost haze — more icy detail and depth than the plain frozen foundation", swatch: "#aaccee", colorSafe: true },
    { id: "enh_gel_coat", name: "★ Enhanced Gel Coat", desc: "Premium gel coat with visible flow-out variation and wet depth — more surface realism than the plain gel coat foundation", swatch: "#66aacc", colorSafe: true },
    { id: "enh_powder_coat", name: "★ Enhanced Powder Coat", desc: "Premium powder coat with visible orange-peel texture — more surface detail than foundation. Industrial that pops.", swatch: "#778877", colorSafe: true },
    { id: "enh_vinyl_wrap", name: "★ Enhanced Vinyl Wrap", desc: "Premium vinyl wrap with visible stretch marks and conform lines — more realistic than foundation. Shows wrap character.", swatch: "#668899", colorSafe: true },
    { id: "enh_soft_gloss", name: "★ Enhanced Soft Gloss", desc: "Premium soft gloss with warm micro-shimmer and subtle depth — more luminous feel than the plain soft gloss foundation", swatch: "#77aabb", colorSafe: true },
    { id: "enh_soft_matte", name: "★ Enhanced Soft Matte", desc: "Premium soft matte with velvet-touch organic grain — more tactile character than the plain soft matte foundation", swatch: "#778877", colorSafe: true },
    { id: "enh_warm_white", name: "★ Enhanced Warm White", desc: "Premium warm white with creamy ceramic undertone — more tonal warmth and depth than the plain warm white foundation", swatch: "#eeddcc", colorSafe: true },
    { id: "enh_ceramic_glaze", name: "★ Enhanced Ceramic Glaze", desc: "Premium ceramic glaze with deep wet pooling and clarity depth — rich liquid-glass look for show car builds", swatch: "#55aaaa", colorSafe: true },
    { id: "enh_silk", name: "★ Enhanced Silk", desc: "Premium silk with subtle directional fabric-like sheen — smoother and more refined than the plain satin foundation", swatch: "#99aabb", colorSafe: true },
    { id: "enh_eggshell", name: "★ Enhanced Eggshell", desc: "Premium eggshell with visible orange-peel micro-texture and warm tone — more surface character than flat eggshell", swatch: "#bbaa99", colorSafe: true },
    { id: "enh_primer", name: "★ Enhanced Primer", desc: "Premium primer with sand-grit and coverage variation — more realistic than flat foundation. Project car authenticity.", swatch: "#888877", colorSafe: true },
    { id: "enh_clear_matte", name: "★ Enhanced Clear Matte", desc: "Premium clear matte with protective micro-haze — more realistic flat clearcoat than the plain clear matte foundation", swatch: "#667788", colorSafe: true },
    { id: "enh_semi_gloss", name: "★ Enhanced Semi Gloss", desc: "Premium semi-gloss with balanced sheen between satin and gloss — more nuanced surface than plain semi-gloss", swatch: "#6699aa", colorSafe: true },
    { id: "enh_wet_look", name: "★ Enhanced Wet Look", desc: "Premium wet look with ultra-deep clarity and glass-like depth — more liquid shine than the standard wet look base", swatch: "#448877", colorSafe: true },
    { id: "enh_piano_black", name: "★ Enhanced Piano Black", desc: "Premium piano black with mirror-deep reflection depth — richer and more liquid than the standard piano black base", swatch: "#111122", colorSafe: true },
    { id: "enh_living_matte", name: "★ Enhanced Living Matte", desc: "Premium living matte with biological grain texture — more organic surface character than the standard living matte", swatch: "#667755", colorSafe: true },
    { id: "enh_neutral_grey", name: "★ Enhanced Neutral Grey", desc: "Premium neutral grey with micro-grain texture — more surface detail and depth than the plain neutral grey foundation", swatch: "#777788", colorSafe: true },
    { id: "enh_clear_satin", name: "★ Enhanced Clear Satin", desc: "Premium clear satin with orange-peel micro-texture — more realistic clearcoat than the plain clear satin foundation", swatch: "#7799aa", colorSafe: true },
    { id: "enh_pure_black", name: "★ Enhanced Pure Black", desc: "Premium pure black with dead matte grain texture — more depth and surface character than the plain pure black foundation", swatch: "#0a0a0a", colorSafe: true },
    { id: "singularity", name: "Event Horizon", desc: "Near-black base with vivid color bleeding at edges — procedural micro-spec gradient, no hand work", swatch: "#000000" },
    { id: "liquid_obsidian", name: "Liquid Obsidian", desc: "Flowing glass-metal phase boundary - metallic oscillates 0-255 while roughness stays near-zero", swatch: "#080818" },
    { id: "prismatic", name: "Boundary Logic", desc: "Extreme M/R range — procedural micro-spec creates strong angle-resolved color shifts in seconds", swatch: "#E1A1FF" },
    { id: "p_mercury", name: "Mercury (PARADIGM)", desc: "Liquid metal pooling — flowing silver mercury surface with quicksilver fluidity and shifting reflective curves.", swatch: "#C0C8D0" },
    // 2026-04-19 HEENAN HSTING3 — Sting copy fix: vague ("doesn't commit to a surface" was nonsense for a paint).
    { id: "p_phantom", name: "Phantom (PARADIGM)", desc: "Near-invisible pearl haze over your base color — only catches light at sharp angles. Best on dark or chrome bases for the ghost effect.", swatch: "#D8DDE4" },
    { id: "p_volcanic", name: "Volcanic (PARADIGM)", desc: "Lava cooling to rock — glowing heat veins through dark stone for primal volcanic earth-power finishes.", swatch: "#661100" },
    { id: "arctic_ice", name: "Arctic Ice", desc: "Frozen crystalline surface — cracked ice with blue-white interior glow, perfect for winter rally and cold-themed builds.", swatch: "#C0E8FF" },
    { id: "carbon_weave", name: "Carbon Weave", desc: "Carbon fiber with metallic threads — woven diagonal weave pattern catching subtle metallic flash. Race-grade composite look.", swatch: "#2A3040" },
    { id: "nebula", name: "Stellar Dust", desc: "Cosmic dust field — fine metallic micro-spec creates star-like sparkle at grazing angles. Math-generated.", swatch: "#3322aa" },
    { id: "quantum_foam", name: "Quantum Foam (PARADIGM)", desc: "Full-range M/R noise at pixel scale — neutral base, spec does all the visual work", swatch: "#8899aa" },
    // 2026-04-19 HEENAN HSTING4 — Sting copy fix: was talking to devs not painters.
    { id: "infinite_finish", name: "Infinite Finish (PARADIGM)", desc: "Pixel-scale M/R noise with an alternate Quantum Foam seed — pair the two for non-repeating coverage on large panels.", swatch: "#99aabb" },
    // ── EXOTIC BASE FINISHES (RESEARCH-008) ──────────────────────────────────
    { id: "chromaflair", name: "ChromaFlair Light Shift", desc: "Multi-angle color flip: three distinct colors at three viewing angles", swatch: "#cc88ff", colorSafe: true },
    { id: "xirallic", name: "Xirallic Crystal Flake", desc: "Deep-sparkle alumina flakes with iron oxide blue-silver interference", swatch: "#99bbdd", colorSafe: true },
    { id: "anodized_exotic", name: "Anodized", desc: "Dye-impregnated oxide layer: semi-gloss, subtly translucent, micro-pore texture", swatch: "#7799bb", colorSafe: true },
    // ── RESEARCH SESSION 6: 9 New Base Finishes (2026-03-29) ─────────────────
    { id: "alubeam", name: "Alubeam Liquid Mirror", desc: "BASF Alubeam ultra-fine oriented aluminum — coherent blurred reflection between chrome and metallic", swatch: "#d8dce8", colorSafe: true },
    { id: "satin_candy", name: "Satin Candy", desc: "Candy pigment under satin/matte clear — glowing-coal effect: maximum saturation, zero reflection", swatch: "#cc2244", colorSafe: true },
    { id: "velvet_floc", name: "Velvet / Suede Floc", desc: "Flock coating — absolute light absorption, car becomes a pure silhouette shape", swatch: "#0a0a0a" },
    { id: "deep_pearl", name: "Deep Pearl (Type III)", desc: "Three-stage tri-coat pearl with edge-weighted flop — warm/cool color hint at raking angles", swatch: "#f0eef8", colorSafe: true },
    { id: "gunmetal_satin", name: "Gunmetal Satin Industrial", desc: "CNC-machined alloy satin — dark metallic without gloss, raw processed metal aesthetic", swatch: "#3a3a44", colorSafe: true },
    { id: "forged_carbon_vis", name: "Forged Carbon Visible", desc: "Lamborghini forged carbon — random-fiber organic weave, non-repeating charcoal with wet clearcoat depth", swatch: "#1a1a1c" },
    { id: "electroplated_gold", name: "Electroplated Gold / Rose Gold", desc: "Warm mirror — near-chrome metallic with warm gold or rose-gold albedo, Rolls-Royce Bespoke reference", swatch: "#c8a028", colorSafe: true },
    { id: "cerakote_pvd", name: "Cerakote / PVD Hard Coat", desc: "TiN/TiAlN thin hard coating — muted deep colors, flat zero-clearcoat surface, firearms/motorsport hardware aesthetic", swatch: "#445544", colorSafe: true },
    { id: "hypershift_spectral", name: "Hypershift Spectral 360°", desc: "PPG HyperShift — 6-anchor full spectral sweep with steep transitions; distinct dominant hue from every viewing angle", swatch: "#cc4488", colorSafe: true },
    // ★ COLORSHOXX — Premium dual-tone color-shifting finishes
    { id: "cx_inferno", name: "COLORSHOXX Inferno Flip", desc: "Crimson red ↔ midnight blue — red zones flash metallic at specular angle, blue holds steady. Two-color premium shift.", swatch: "#991122" },
    { id: "cx_arctic", name: "COLORSHOXX Arctic Mirage", desc: "Ice silver ↔ deep teal — silver flashes brilliantly, teal stays deep and cool. Premium cold-shift.", swatch: "#55AABB" },
    { id: "cx_venom", name: "COLORSHOXX Venom Shift", desc: "Toxic green ↔ black purple — green zones pop metallic, purple stays dark and menacing. Aggressive shift.", swatch: "#33AA22" },
    { id: "cx_solar", name: "COLORSHOXX Solar Flare", desc: "Warm gold ↔ copper red — gold flashes like liquid metal, copper glows warmly. Luxury warm-shift.", swatch: "#CC8822" },
    { id: "cx_phantom", name: "COLORSHOXX Phantom Violet", desc: "Electric violet ↔ gunmetal gray — violet pops vivid metallic flash, gunmetal stays cold and steely. Stealth premium.", swatch: "#7722AA" },
    // COLORSHOXX Wave 2 — Extreme Dual-Tone (chrome↔matte)
    { id: "cx_chrome_void", name: "CX Chrome Void", desc: "Pure mirror chrome ↔ absolute matte black. Maximum possible material contrast.", swatch: "linear-gradient(135deg, #cccccc 0%, #111111 100%)" },
    { id: "cx_blood_mercury", name: "CX Blood Mercury", desc: "Liquid chrome silver ↔ deep arterial crimson. Mercury meets blood.", swatch: "#CC3344" },
    { id: "cx_neon_abyss", name: "CX Neon Abyss", desc: "Electric hot pink chrome ↔ abyssal black-green matte. Neon drowning in void.", swatch: "#FF22AA" },
    { id: "cx_glacier_fire", name: "CX Glacier Fire", desc: "Icy white-blue chrome ↔ molten orange-red matte. Ice and fire on one surface.", swatch: "#88BBEE" },
    { id: "cx_obsidian_gold", name: "CX Obsidian Gold", desc: "Liquid 24k gold chrome ↔ volcanic obsidian dead matte. Treasure in darkness.", swatch: "#DDAA33" },
    { id: "cx_electric_storm", name: "CX Electric Storm", desc: "Crackling electric blue chrome ↔ thundercloud dark gray matte.", swatch: "#2266EE" },
    { id: "cx_rose_chrome", name: "CX Rose Chrome", desc: "Rose gold chrome mirror ↔ deep burgundy velvet matte. Luxury meets darkness.", swatch: "#DD8877" },
    { id: "cx_toxic_chrome", name: "CX Toxic Chrome", desc: "Acid green chrome ↔ chemical waste matte brown-black. Hazardous beauty.", swatch: "#66DD22" },
    { id: "cx_midnight_chrome", name: "CX Midnight Chrome", desc: "Dark blue chrome mirror ↔ pure flat black void. Stealth and flash.", swatch: "#223388" },
    { id: "cx_white_lightning", name: "CX White Lightning", desc: "Blinding white chrome ↔ charcoal matte. Lightning bolt contrast.", swatch: "#EEEEFF" },
    // COLORSHOXX Wave 2 — Three-Color
    { id: "cx_aurora_borealis", name: "CX Aurora Borealis", desc: "Electric green + deep teal + violet purple. Three-zone northern lights across the car.", swatch: "#33DD55" },
    { id: "cx_dragon_scale", name: "CX Dragon Scale", desc: "Chrome gold + ember orange + charcoal black. Three-zone fire wyrm.", swatch: "#DD9922" },
    { id: "cx_frozen_nebula", name: "CX Frozen Nebula", desc: "Ice white chrome + cosmic blue + deep purple void. Three-zone deep space.", swatch: "#8888EE" },
    { id: "cx_hellfire", name: "CX Hellfire", desc: "White-hot chrome + lava orange + scorched black. Three-zone inferno from the abyss.", swatch: "#FF6600" },
    { id: "cx_ocean_trench", name: "CX Ocean Trench", desc: "Bioluminescent teal + deep navy + abyssal black. Three-zone Mariana.", swatch: "#22BBAA" },
    // COLORSHOXX Wave 2 — Four-Color
    { id: "cx_supernova", name: "CX Supernova", desc: "White-hot + electric blue + magenta + void black. Four-stage stellar death.", swatch: "#FFDDCC" },
    { id: "cx_prism_shatter", name: "CX Prism Shatter", desc: "Chrome red + gold + teal + indigo. Shattered light through a crystal.", swatch: "#CCAA44" },
    { id: "cx_acid_rain", name: "CX Acid Rain", desc: "Toxic yellow + sick green + bruise purple + ash gray. Chemical downpour.", swatch: "#CCDD22" },
    { id: "cx_royal_spectrum", name: "CX Royal Spectrum", desc: "Chrome silver + sapphire + ruby + emerald. Four crown jewels on one car.", swatch: "#AABBCC" },
    { id: "cx_apocalypse", name: "CX Apocalypse", desc: "Scorching white + blood red + rust orange + dead black. The end of everything.", swatch: "#DD4422" },
    // ★ MORTAL SHOKK — Fighting-game-inspired married paint+spec finishes
    { id: "ms_frozen_fury", name: "MS Frozen Fury", desc: "Ice blue + frozen white chrome zones. White flashes at specular, blue holds steady.", swatch: "#88BBEE" },
    { id: "ms_venom_strike", name: "MS Venom Strike", desc: "Deep gold metallic flash + black matte fire zones. Scorching heat.", swatch: "#DDBB22" },
    { id: "ms_thunder_lord", name: "MS Thunder Lord", desc: "Electric blue + white lightning veins on dark navy base. Storm unleashed.", swatch: "#3366EE" },
    { id: "ms_chrome_cage", name: "MS Chrome Cage", desc: "Hollywood gold chrome + green energy shimmer. Star power.", swatch: "#DDCC44" },
    { id: "ms_dragon_flame", name: "MS Dragon Flame", desc: "Red + orange fire gradient with ember particles on dark smoke.", swatch: "#DD3311" },
    { id: "ms_royal_edge", name: "MS Royal Edge", desc: "Royal blue silk + silver steel blade streaks. Deadly elegance.", swatch: "#2244AA" },
    { id: "ms_feral_grin", name: "MS Feral Grin", desc: "Hot pink + venomous purple. Aggressive contrast. Unhinged energy.", swatch: "#EE2288" },
    { id: "ms_acid_scale", name: "MS Acid Scale", desc: "Acid green + dark scale cell pattern. Voronoi reptile skin.", swatch: "#66DD11" },
    { id: "ms_soul_drain", name: "MS Soul Drain", desc: "Glowing red energy mist on absolute black void. Soul extraction.", swatch: "#CC1100" },
    { id: "ms_emerald_shadow", name: "MS Emerald Shadow", desc: "Deep emerald + shadow black stealth zones. Silent strike.", swatch: "#118833" },
    { id: "ms_void_walker", name: "MS Void Walker", desc: "Absolute black with faint shadow duplicate shimmer. Nearly invisible.", swatch: "#111118" },
    { id: "ms_ghost_vapor", name: "MS Ghost Vapor", desc: "Gray smoke wisps with chrome peek-through — now you see it, now you don't, ghostly apparition finish.", swatch: "#99AABB" },
    { id: "ms_shape_shift", name: "MS Shape Shift", desc: "Morphing 3-color zones: mystic green + amber + deep purple. Never the same.", swatch: "#88AA33" },
    { id: "ms_titan_bronze", name: "MS Titan Bronze", desc: "Massive bronze metallic + dark brutal texture. Four arms of fury.", swatch: "#AA7722" },
    { id: "ms_war_hammer", name: "MS War Hammer", desc: "Dark armor plate + blood red accent veins. Conqueror finish.", swatch: "#881111" },
    // ★ NEON UNDERGROUND — Blacklight reactive neon-glow finishes
    { id: "neon_pink_blaze", name: "NU Pink Blaze", desc: "Hot pink neon with concentric pulsing glow zones. Blacklight reactive.", swatch: "#FF1493" },
    { id: "neon_toxic_green", name: "NU Toxic Green", desc: "Radioactive green with Geiger-counter scatter particles. Hazmat glow.", swatch: "#39FF14" },
    { id: "neon_electric_blue", name: "NU Electric Blue", desc: "Deep UV blue with plasma discharge veins. Lightning in a tube.", swatch: "#0033FF" },
    { id: "neon_blacklight", name: "NU Blacklight", desc: "UV-reactive purple that glows in dark zones. Inverse brightness.", swatch: "#8B00FF" },
    { id: "neon_orange_hazard", name: "NU Orange Hazard", desc: "Construction orange with diagonal warning stripe pattern. High-vis neon.", swatch: "#FF6600" },
    { id: "neon_red_alert", name: "NU Red Alert", desc: "Emergency red with siren-like concentric rings. Full alarm.", swatch: "#FF0022" },
    { id: "neon_cyber_yellow", name: "NU Cyber Yellow", desc: "Cyberpunk yellow with circuit trace PCB pattern. Digital glow.", swatch: "#FFEE00" },
    { id: "neon_ice_white", name: "NU Ice White", desc: "Cold white neon with frost crystallization dendrites. Sub-zero glow.", swatch: "#E8F0FF" },
    { id: "neon_dual_glow", name: "NU Dual Glow", desc: "Two-color neon (pink+blue) split by warped spatial field. Dual spectrum.", swatch: "#CC44DD" },
    { id: "neon_rainbow_tube", name: "NU Rainbow Tube", desc: "Full spectrum neon tube with horizontal banding. All wavelengths.", swatch: "#FF4488" },

    // === TEXTILE-INSPIRED BASES === (Session v6.1.2 additions)
    { id: "textile_denim_weave", name: "Denim Weave", desc: "Cotton denim weave finish with blue indigo tone and subtle fiber texture — perfect for casual-wear livery themes or retro workwear-inspired looks", swatch: "#3a4a6e", category: "Textile-Inspired", tags: ["textile", "fabric", "casual", "denim", "blue"], colorSafe: false },
    { id: "textile_canvas_rough", name: "Canvas Rough", desc: "Heavy canvas textile look with coarse warp-and-weft threading — evokes artist canvas or sailcloth for rugged industrial and maritime builds", swatch: "#c8b892", category: "Textile-Inspired", tags: ["textile", "fabric", "canvas", "coarse", "natural"], colorSafe: false },
    { id: "textile_silk_sheen", name: "Silk Sheen", desc: "Smooth silk with subtle sheen and directional luster — elegant luxury fabric finish for high-end fashion-themed show builds", swatch: "#e8d9c0", category: "Textile-Inspired", tags: ["textile", "fabric", "silk", "luxury", "sheen"], colorSafe: false },
    { id: "textile_velvet_crush", name: "Velvet Crushed", desc: "Crushed velvet pile texture with directional nap variation — deep plush richness that plays with light for boudoir-luxe showcase builds", swatch: "#4a1a3a", category: "Textile-Inspired", tags: ["textile", "fabric", "velvet", "luxury", "plush"], colorSafe: false },
    { id: "textile_burlap_coarse", name: "Burlap Coarse", desc: "Coarse burlap sack texture with visible jute fibers and rough weave — rustic farmhouse-country aesthetic for weathered agrarian builds", swatch: "#9a7a48", category: "Textile-Inspired", tags: ["textile", "fabric", "burlap", "rustic", "coarse"], colorSafe: false },
    { id: "textile_suede_soft", name: "Suede Soft", desc: "Soft suede nap with brushed fiber direction and muted matte surface — warm tactile leather-alternative for boutique interior-themed builds", swatch: "#8a6a4a", category: "Textile-Inspired", tags: ["textile", "fabric", "suede", "soft", "matte"], colorSafe: false },

    // === STONE & MINERAL BASES ===
    { id: "stone_slate_matte", name: "Slate Matte", desc: "Dark matte slate surface with natural cleavage lines and subtle mineral flecks — architectural stonework finish for grounded premium builds", swatch: "#404852", category: "Stone & Mineral", tags: ["stone", "mineral", "slate", "matte", "architectural"], colorSafe: false },
    { id: "stone_marble_polished", name: "Marble Polished", desc: "Polished marble sheen with flowing veins through creamy background — classical Carrara elegance for luxury statement builds", swatch: "#e8e6e2", category: "Stone & Mineral", tags: ["stone", "mineral", "marble", "polished", "luxury"], colorSafe: false },
    { id: "stone_granite_speckled", name: "Granite Speckled", desc: "Speckled granite pattern with quartz-feldspar-mica grain variation — countertop-grade mineral density for solid industrial-luxe builds", swatch: "#6a6058", category: "Stone & Mineral", tags: ["stone", "mineral", "granite", "speckled", "natural"], colorSafe: false },
    { id: "stone_sandstone_warm", name: "Sandstone Warm", desc: "Warm sandstone desert tone with layered sedimentary bedding lines — Southwest canyon aesthetic for adventure and overland builds", swatch: "#c8905a", category: "Stone & Mineral", tags: ["stone", "mineral", "sandstone", "warm", "desert"], colorSafe: false },
    { id: "stone_obsidian_mirror", name: "Obsidian Mirror", desc: "Near-mirror obsidian black with volcanic glass conchoidal fractures — razor-sharp primordial stone for sinister premium builds", swatch: "#0a0a12", category: "Stone & Mineral", tags: ["stone", "mineral", "obsidian", "mirror", "volcanic"], colorSafe: false },
    { id: "stone_travertine_cream", name: "Travertine Cream", desc: "Cream travertine quarry finish with natural porosity and layered limestone banding — Mediterranean villa elegance for refined builds", swatch: "#e4d5b8", category: "Stone & Mineral", tags: ["stone", "mineral", "travertine", "cream", "natural"], colorSafe: false },

    // === PAINT TECHNIQUE BASES ===
    { id: "paint_drip_gravity", name: "Drip Gravity", desc: "Gravity-dripped paint runs with vertical curtain streaks and pooling at lower edges — Jackson-Pollock-adjacent action painting for expressive art builds", swatch: "#3a2a52", category: "Paint Technique", tags: ["paint", "technique", "drip", "gravity", "expressive"], colorSafe: false },
    { id: "paint_splatter_loose", name: "Splatter Loose", desc: "Loose paint splatter overlay with scattered droplets and fine mist in varied sizes — graffiti-underground aesthetic for rebellious street-art builds", swatch: "#2a2a35", category: "Paint Technique", tags: ["paint", "technique", "splatter", "graffiti", "street"], colorSafe: false },
    { id: "paint_sponge_stipple", name: "Sponge Stipple", desc: "Sponge-stippled finish with irregular dabbed texture and layered tonal variation — faux-finish decorative painting for vintage interior-inspired builds", swatch: "#a88862", category: "Paint Technique", tags: ["paint", "technique", "sponge", "stipple", "vintage"], colorSafe: false },
    { id: "paint_roller_streak", name: "Roller Streak", desc: "Paint roller streak marks with directional lap lines and edge buildup — imperfect DIY garage-job charm for lo-fi honest builds", swatch: "#7a8a95", category: "Paint Technique", tags: ["paint", "technique", "roller", "streak", "diy"], colorSafe: false },
    { id: "paint_spray_fade", name: "Spray Fade", desc: "Graduated spray gun fade with soft atomized transition from dense to thin coverage — classic airbrush blend for custom show builds", swatch: "#c85a3a", category: "Paint Technique", tags: ["paint", "technique", "spray", "fade", "airbrush"], colorSafe: false },
    { id: "paint_brush_stroke", name: "Brush Stroke", desc: "Visible brushstroke texture with directional bristle marks and impasto ridges — hand-painted fine-art aesthetic for gallery-piece showpiece builds", swatch: "#5a6a48", category: "Paint Technique", tags: ["paint", "technique", "brush", "stroke", "artistic"], colorSafe: false }
];

// =============================================================================
// BASE METADATA - Structured tags for smart recommendations & discovery
// family: material family (chrome, candy, matte, pearl, metallic, satin, ceramic, vinyl, weathered, exotic, foundation)
// substrate: underlying material (metal, paint, film, composite, raw)
// coating: top coating type (clearcoat, matte_clear, none, oxide, wrap)
// tier: realism/quality tier (hero, premium, standard, utility)
// aggression: visual intensity 1-5 (1=subtle, 5=extreme)
// sponsor_safe: true if sponsor text remains readable over this finish
// best_with: array of pattern IDs that pair well with this base
// =============================================================================
const BASE_METADATA = {
    // === HERO BASES (12 flagship materials - unmistakably different) ===
    chrome:        { family: "chrome", substrate: "metal", coating: "none", tier: "hero", aggression: 4, sponsor_safe: false, best_with: ["carbon_fiber", "hex_mesh", "lightning", "ekg"], similar_to: ["dark_chrome", "blue_chrome", "mercury", "satin_chrome"] },
    candy:         { family: "candy", substrate: "metal", coating: "clearcoat", tier: "hero", aggression: 3, sponsor_safe: true, best_with: ["holographic_flake", "stardust", "tribal_flame", "carbon_fiber"], similar_to: ["spectraflame", "holographic_base", "prismatic"] },
    matte:         { family: "matte", substrate: "paint", coating: "matte_clear", tier: "hero", aggression: 1, sponsor_safe: true, best_with: ["carbon_fiber", "hex_mesh", "diamond_plate"], similar_to: ["flat_black", "blackout", "cerakote", "primer"] },
    pearl:         { family: "pearl", substrate: "paint", coating: "clearcoat", tier: "hero", aggression: 2, sponsor_safe: true, best_with: ["interference", "holographic_flake", "stardust"], similar_to: ["tri_coat_pearl", "pearlescent_white", "deep_pearl", "jelly_pearl"] },
    metallic:      { family: "metallic", substrate: "metal", coating: "clearcoat", tier: "hero", aggression: 2, sponsor_safe: true, best_with: ["metal_flake", "carbon_fiber", "tribal_flame"], similar_to: ["gunmetal", "copper", "brushed_aluminum", "rose_gold"] },
    satin:         { family: "satin", substrate: "paint", coating: "clearcoat", tier: "hero", aggression: 1, sponsor_safe: true, best_with: ["carbon_fiber", "diamond_plate", "none"], similar_to: ["silk", "eggshell", "satin_wrap", "ceramic"] },
    vantablack:    { family: "matte", substrate: "paint", coating: "none", tier: "hero", aggression: 5, sponsor_safe: false, best_with: ["stardust", "lightning", "plasma"], similar_to: ["quantum_black", "flat_black", "dark_matter", "blackout"] },
    frozen:        { family: "frozen", substrate: "paint", coating: "matte_clear", tier: "hero", aggression: 2, sponsor_safe: true, best_with: ["cracked_ice", "interference", "diamond_plate"], similar_to: ["frozen_matte", "arctic_ice", "electric_ice"] },
    chameleon:     { family: "chameleon", substrate: "metal", coating: "clearcoat", tier: "hero", aggression: 4, sponsor_safe: false, best_with: ["none", "holographic_flake", "interference"], similar_to: ["chromaflair", "iridescent", "hypershift_spectral"] },
    cerakote:      { family: "ceramic", substrate: "composite", coating: "none", tier: "hero", aggression: 1, sponsor_safe: true, best_with: ["carbon_fiber", "hex_mesh", "none"], similar_to: ["duracoat", "powder_coat", "ceramic_matte"] },
    brushed_aluminum: { family: "brushed", substrate: "metal", coating: "none", tier: "hero", aggression: 2, sponsor_safe: true, best_with: ["none", "carbon_fiber", "diamond_plate"], similar_to: ["brushed_titanium", "satin_metal", "satin_chrome"] },
    blackout:      { family: "matte", substrate: "paint", coating: "matte_clear", tier: "hero", aggression: 3, sponsor_safe: false, best_with: ["carbon_fiber", "hex_mesh", "ekg"], similar_to: ["matte", "flat_black", "vantablack", "stealth_wrap"] },

    // === PREMIUM BASES ===
    dark_chrome:   { family: "chrome", substrate: "metal", coating: "none", tier: "premium", aggression: 4, sponsor_safe: false, best_with: ["carbon_fiber", "lightning", "hex_mesh"] },
    candy_chrome:  { family: "chrome", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 5, sponsor_safe: false, best_with: ["holographic_flake", "stardust"] },
    piano_black:   { family: "gloss", substrate: "paint", coating: "clearcoat", tier: "premium", aggression: 2, sponsor_safe: true, best_with: ["none", "carbon_fiber"] },
    gloss:         { family: "gloss", substrate: "paint", coating: "clearcoat", tier: "standard", aggression: 1, sponsor_safe: true, best_with: ["none", "carbon_fiber", "tribal_flame"] },
    ceramic:       { family: "ceramic", substrate: "composite", coating: "clearcoat", tier: "premium", aggression: 1, sponsor_safe: true, best_with: ["none", "diamond_plate"] },
    barn_find:     { family: "weathered", substrate: "paint", coating: "none", tier: "premium", aggression: 3, sponsor_safe: false, best_with: ["acid_wash", "battle_worn", "rust_bloom"] },
    copper:        { family: "metallic", substrate: "metal", coating: "none", tier: "premium", aggression: 3, sponsor_safe: true, best_with: ["none", "tribal_flame", "celtic_knot"] },
    gunmetal:      { family: "metallic", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 2, sponsor_safe: true, best_with: ["carbon_fiber", "hex_mesh", "diamond_plate"] },

    // === STANDARD BASES ===
    silk:          { family: "satin", substrate: "paint", coating: "clearcoat", tier: "standard", aggression: 1, sponsor_safe: true, best_with: ["none", "interference"] },
    wet_look:      { family: "gloss", substrate: "paint", coating: "clearcoat", tier: "standard", aggression: 1, sponsor_safe: true, best_with: ["none", "carbon_fiber"] },
    flat_black:    { family: "matte", substrate: "paint", coating: "none", tier: "standard", aggression: 2, sponsor_safe: true, best_with: ["carbon_fiber", "hex_mesh", "ekg"] },
    powder_coat:   { family: "matte", substrate: "composite", coating: "none", tier: "standard", aggression: 1, sponsor_safe: true, best_with: ["none", "diamond_plate"] },
    rose_gold:     { family: "metallic", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 3, sponsor_safe: true, best_with: ["holographic_flake", "stardust"] },
    satin_chrome:  { family: "chrome", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 3, sponsor_safe: false, best_with: ["carbon_fiber", "hex_mesh"] },
    surgical_steel:{ family: "metallic", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 2, sponsor_safe: true, best_with: ["hex_mesh", "diamond_plate"] },
    heat_treated:  { family: "metallic", substrate: "metal", coating: "oxide", tier: "premium", aggression: 3, sponsor_safe: true, best_with: ["none", "tribal_flame"] },

    // === WRAP BASES ===
    satin_wrap:    { family: "vinyl", substrate: "film", coating: "matte_clear", tier: "standard", aggression: 1, sponsor_safe: true, best_with: ["none", "carbon_fiber"] },
    liquid_wrap:   { family: "vinyl", substrate: "film", coating: "clearcoat", tier: "standard", aggression: 1, sponsor_safe: true, best_with: ["none"] },
    chrome_wrap:   { family: "chrome", substrate: "film", coating: "none", tier: "premium", aggression: 4, sponsor_safe: false, best_with: ["none", "carbon_fiber"] },

    // === WEATHERED BASES ===
    acid_etch:     { family: "weathered", substrate: "paint", coating: "none", tier: "standard", aggression: 4, sponsor_safe: false, best_with: ["acid_wash", "fracture"] },
    battle_patina: { family: "weathered", substrate: "metal", coating: "none", tier: "standard", aggression: 4, sponsor_safe: false, best_with: ["battle_worn", "rust_bloom"] },
    sun_fade:      { family: "weathered", substrate: "paint", coating: "none", tier: "standard", aggression: 2, sponsor_safe: true, best_with: ["none", "acid_wash"] },
    oxidized:      { family: "weathered", substrate: "metal", coating: "oxide", tier: "standard", aggression: 3, sponsor_safe: true, best_with: ["none", "rust_bloom"] },

    // === EXOTIC BASES ===
    spectraflame:  { family: "candy", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 4, sponsor_safe: false, best_with: ["holographic_flake", "stardust"] },
    volcanic:      { family: "exotic", substrate: "metal", coating: "none", tier: "premium", aggression: 5, sponsor_safe: false, best_with: ["fracture", "lightning", "plasma"] },
    iridescent:    { family: "exotic", substrate: "film", coating: "clearcoat", tier: "premium", aggression: 3, sponsor_safe: false, best_with: ["interference", "holographic_flake"] },
    electric_ice:  { family: "chrome", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 4, sponsor_safe: false, best_with: ["lightning", "cracked_ice", "stardust"] },
    diamond_coat:  { family: "exotic", substrate: "metal", coating: "clearcoat", tier: "premium", aggression: 4, sponsor_safe: false, best_with: ["stardust", "holographic_flake"] },
};

// =============================================================================
// BASE FAMILY MAP — Every base classified into 18 material families
// Used for family-based browsing, filtering, and smart recommendations
// =============================================================================
const BASE_FAMILY_MAP = {
    chrome: ["alubeam","black_chrome","blue_chrome","bullseye_chrome","candy_chrome","cc_ghost_silver","champagne_flake","checkered_chrome","chrome","chrome_wrap","dark_chrome","electric_ice","electroplated_gold","enh_chrome","f_chrome","f_electroplate","f_vapor_deposit","hydrographic","liquid_obsidian","liquid_titanium","mercury","mirror_gold","neon_blacklight","neon_cyber_yellow","neon_dual_glow","neon_electric_blue","neon_ice_white","neon_orange_hazard","neon_pink_blaze","neon_rainbow_tube","neon_red_alert","neon_toxic_green","p_erised","p_geomagnetic","p_mercury","platinum","rose_gold","spectraflame","surgical_steel","terrain_chrome","tungsten","vintage_chrome"],
    satin_chrome: ["enh_satin_chrome","f_satin_chrome","original_metal_flake","p_schrodinger","satin_chrome","shokk_spectrum"],
    brushed: ["brushed_aluminum","brushed_titanium","brushed_wrap","enh_brushed","f_brushed","satin_metal"],
    metallic: ["anime_gradient_hair","anime_mecha_plate","anime_sakura_scatter","anime_speed_lines","anodized_exotic","beetle_stag","burnt_headers","cc_bronze_heat","cc_inferno","cc_royal_purple","cc_toxic","copper","cx_arctic","cx_aurora_borealis","cx_blood_mercury","cx_frozen_nebula","cx_phantom","cx_prism_shatter","cx_venom","drag_strip_gloss","dragonfly_wing","enh_anodized","enh_metallic","f_metallic","factory_basecoat","ferrari_rosso","fine_silver_flake","firefly_glow","gunmetal","infinite_finish","metallic","ms_feral_grin","ms_frozen_fury","ms_royal_edge","ms_shape_shift","ms_thunder_lord","opal","organic_metal","p_coronal","p_non_euclidean","pagani_tricolore","porsche_pts","satin_gold","shokk_aurora","shokk_catalyst","shokk_dual","shokk_fusion_base","shokk_inferno","shokk_phase","shokk_reactor","shokk_rift","shokk_tesseract_v2","shokk_wraith","xirallic"],
    heavy_metallic: ["anime_cel_shade_chrome","anime_crystal_facet","anime_energy_aura","anime_neon_outline","anime_sparkle_burst","antique_chrome","beetle_jewel","beetle_rainbow","bentley_silver","blue_ice_flake","bugatti_blue","butterfly_morpho","cc_arctic_freeze","cc_electric_cyan","cc_solar_gold","champagne","cobalt_metal","cx_inferno","cx_royal_spectrum","cx_solar","diamond_coat","f_pvd_coating","graphene","green_flake","gunmetal_flake","holographic_base","maybach_two_tone","metal_flake_base","ms_chrome_cage","p_time_reversed","plasma_core","plasma_metal","prismatic","raw_aluminum","red_chrome","scarab_gold","shokk_apex","shokk_blood","shokk_cipher","shokk_flux","shokk_helix","shokk_mirage","shokk_polarity","shokk_prism","shokk_pulse","shokk_static","shokk_surge","shokk_vortex","victory_lane"],
    pearl: ["dealer_pearl","deep_pearl","enh_pearl","f_pearl","jelly_pearl","midnight_pearl","pace_car_pearl","pearl","pearlescent_white","tri_coat_pearl"],
    candy: ["candy","candy_apple","candy_burgundy","candy_cobalt","candy_emerald","f_candy"],
    ceramic: ["ceramic","ceramic_matte","enamel","enh_baked_enamel","enh_ceramic_glaze","enh_gel_coat","f_baked_enamel","f_gel_coat","stock_car_enamel","tempered_glass"],
    gloss: ["ambulance_white","bioluminescent","cc_midnight","crystal_clear","enh_eggshell","enh_gloss","enh_piano_black","enh_semi_gloss","enh_silk","enh_soft_gloss","enh_wet_look","f_soft_gloss","fire_engine","fleet_white","gloss","lamborghini_verde","mclaren_orange","nebula","obsidian","p_phantom","p_superfluid","piano_black","police_black","porcelain","race_day_gloss","school_bus","semi_gloss","shokk_venom","showroom_clear","smoked","solar_panel","taxi_yellow","wet_look"],
    satin: ["battleship_gray","eggshell","enh_clear_satin","enh_satin","enh_warm_white","f_clear_satin","f_pure_white","f_warm_white","rally_mud","satin","sun_baked"],
    matte: ["asphalt_grind","chalky_base","clear_matte","dark_matter","enh_clear_matte","enh_living_matte","enh_matte","enh_neutral_grey","enh_primer","enh_pure_black","enh_soft_matte","f_matte","f_neutral_grey","f_pure_black","f_soft_matte","f_wrinkle_coat","flat_black","gunship_gray","living_matte","matte","mil_spec_od","mil_spec_tan","neutron_star","orange_peel_gloss","p_seismic","primer","quantum_black","satin_candy","scuffed_satin","shokk_void","sub_black","submarine_black","vantablack","velvet_floc"],
    vinyl: ["enh_vinyl_wrap","f_vinyl_wrap","gloss_wrap","liquid_wrap","matte_wrap","satin_wrap","stealth_wrap","textured_wrap"],
    carbon: ["aramid","carbon_base","carbon_ceramic","carbon_weave","enh_carbon_fiber","f_carbon_fiber","fiberglass","forged_carbon_vis","kevlar_base"],
    industrial: ["cerakote","cerakote_gloss","cerakote_pvd","duracoat","endurance_ceramic","enh_powder_coat","f_powder_coat","powder_coat"],
    weathered: ["acid_etch","acid_rain","barn_find","battle_patina","crumbling_clear","cx_acid_rain","desert_worn","destroyed_coat","f_patina","f_weathering_steel","ms_acid_scale","oxidized","oxidized_copper","patina_bronze","patina_coat","salt_corroded","sun_fade","track_worn"],
    optical: ["chameleon","chromaflair","color_flip_wrap","hypershift_spectral","iridescent"],
    exotic: ["anime_comic_halftone","anodized","arctic_ice","armor_plate","blackout","butterfly_monarch","cc_blood_wash","cx_apocalypse","cx_chrome_void","cx_dragon_scale","cx_electric_storm","cx_glacier_fire","cx_hellfire","cx_midnight_chrome","cx_neon_abyss","cx_obsidian_gold","cx_ocean_trench","cx_rose_chrome","cx_supernova","cx_toxic_chrome","cx_white_lightning","enh_frozen","f_anodized","f_bead_blast","f_frozen","f_galvanized","f_hot_dip","f_mill_scale","f_sand_cast","f_shot_peen","f_thermal_spray","forged_composite","frozen","frozen_matte","galvanized","gunmetal_satin","heat_treated","hybrid_weave","koenigsegg_clear","moonstone","moth_luna","ms_dragon_flame","ms_emerald_shadow","ms_ghost_vapor","ms_soul_drain","ms_titan_bronze","ms_venom_strike","ms_void_walker","ms_war_hammer","p_hypercane","p_programmable","p_volcanic","pewter","quantum_foam","rugged","sandblasted","silk","singularity","superconductor","tinted_clear","tinted_lacquer","titanium_raw","volcanic","wasp_warning"],
};

// Helper: get family for a base ID
function getBaseFamily(baseId) {
    for (var fam in BASE_FAMILY_MAP) {
        if (BASE_FAMILY_MAP[fam].indexOf(baseId) >= 0) return fam;
    }
    return "other";
}

// Helper: get all bases in the same family
function getFamilyBases(baseId) {
    var fam = getBaseFamily(baseId);
    return BASE_FAMILY_MAP[fam] || [];
}

// Helper: identify finishes that need the chrome-on-dark-albedo warning.
// Uses structured metadata first, family map second, then a conservative
// id/name/desc fallback for metadata gaps like legacy "worn_chrome".
function isChromeLikeBase(baseId) {
    if (!baseId || typeof baseId !== 'string') return false;
    const meta = getBaseMetadata(baseId);
    if (meta && (meta.family === 'chrome' || meta.family === 'satin_chrome')) return true;
    const fam = getBaseFamily(baseId);
    if (fam === 'chrome' || fam === 'satin_chrome') return true;
    const base = BASES.find(b => b.id === baseId);
    const hay = `${baseId} ${(base && base.name) || ''} ${(base && base.desc) || ''}`.toLowerCase();
    return /\b(chrome|mirror)\b/.test(hay);
}

// Family display names for UI
const FAMILY_DISPLAY_NAMES = {
    chrome: "Mirror Chrome",
    satin_chrome: "Satin Chrome",
    brushed: "Brushed Metal",
    metallic: "Standard Metallic",
    heavy_metallic: "Heavy Metallic / Flake",
    pearl: "Pearl",
    candy: "Candy",
    ceramic: "Ceramic / Glassy",
    gloss: "Gloss Paint",
    satin: "Satin / Eggshell",
    matte: "Matte / Flat",
    vinyl: "Vinyl Wrap",
    carbon: "Carbon / Composite",
    industrial: "Powder Coat / Industrial",
    weathered: "Weathered / Worn",
    optical: "Color-Shift / Optical",
    exotic: "Exotic / Specialty",
};

// =============================================================================
// HERO BASES — 12 maximally distinct starting points for "Quick Start" mode
// Selected via furthest-point sampling in M/R/CC space — each is unmistakably different
// =============================================================================
const HERO_BASES = [
    { id: "chrome",        label: "Mirror Chrome",    hint: "Perfect mirror — the ultimate show car finish" },
    { id: "candy",         label: "Candy",            hint: "Deep transparent color over metallic — hot rod classic" },
    { id: "matte",         label: "Matte",            hint: "Zero shine, dead flat — stealth and military looks" },
    { id: "pearl",         label: "Pearl",            hint: "Soft iridescent shimmer — luxury OEM upgrade" },
    { id: "metallic",      label: "Metallic",         hint: "Classic car metallic — visible metal flake" },
    { id: "gloss",         label: "Gloss Paint",      hint: "Clean smooth gloss — sponsor-safe, professional" },
    { id: "satin",         label: "Satin",            hint: "Between gloss and matte — understated elegance" },
    { id: "satin_chrome",  label: "Satin Chrome",     hint: "Brushed mirror — softer chrome with directional sheen" },
    { id: "frozen",        label: "Frozen",           hint: "Icy matte metallic — cold crystal texture" },
    { id: "cerakote",      label: "Cerakote",         hint: "Mil-spec ceramic coating — tough and flat" },
    { id: "barn_find",     label: "Barn Find",        hint: "Decades of wear — authentic aged patina" },
    { id: "vantablack",    label: "Vantablack",       hint: "Absolute void — absorbs all light" },
    // 2026-04-20 HEENAN HARDMODE-DISCO-1 (Pillman) — two flagship bases
    // were buried at sortPriority 50 while marketed as OEM/concours
    // essentials. Promoting to HERO_BASES so the Quick Start picker for
    // bases shows what painters actually expect to find first. Held to
    // 14 max per test_hero_bases_constant_exists_and_has_curated_count
    // ratchet (carbon_base already hero=true in metadata, sorts high in
    // Materials tab — doesn't need HERO_BASES seat).
    { id: "piano_black",   label: "Piano Black",      hint: "Mirror-deep show car lacquer — Audi/BMW signature depth" },
    { id: "wet_look",      label: "Wet Look",         hint: "Fresh-waxed concours — perpetual just-detailed shine" },
];

// Featured collections for discovery
const FEATURED_COLLECTIONS = {
    "Best Starting Points":     ["chrome", "candy", "matte", "pearl", "metallic", "gloss"],
    "Best for Sponsors":        ["gloss", "satin", "metallic", "pearl", "ceramic", "matte"],
    "Best Chrome Looks":        ["chrome", "dark_chrome", "satin_chrome", "candy_chrome", "blue_chrome"],
    "Best Show Car":            ["candy", "spectraflame", "chrome", "holographic_base", "pearl"],
    "Best Subtle OEM":          ["gloss", "pearl", "satin", "ceramic", "metallic"],
    "Best Dark Liveries":       ["vantablack", "blackout", "flat_black", "matte", "dark_chrome"],
    // 2026-04-20 HEENAN HARDMODE-DISCO-2 (Pillman) — `acid_etch` and
    // `oxidized` were PHANTOM in BASES (only exist as PATTERN/MONOLITHIC).
    // Painter clicked "Best Weathered" and got tiles that resolved to
    // nothing in the BASES picker. Replaced with verified weathered bases.
    "Best Weathered":           ["barn_find", "oxidized_copper", "patina_bronze", "salt_corroded", "sun_fade"],
    "Experimental / Wild":      ["volcanic", "chameleon", "iridescent", "chromaflair", "frozen"],
};

// Helper: get metadata for a base ID (returns empty object if not tagged yet)
function getBaseMetadata(baseId) {
    return BASE_METADATA[baseId] || {};
}

// Helper: get recommended patterns for a base
function getRecommendedPatterns(baseId) {
    const meta = BASE_METADATA[baseId];
    return meta && meta.best_with ? meta.best_with : [];
}

// Helper: check if a base is sponsor-safe
function isBaseSponsorSafe(baseId) {
    const meta = BASE_METADATA[baseId];
    return meta ? meta.sponsor_safe !== false : true;  // Default to safe
}

// =============================================================================
// PATTERNS - Single source of truth for overlay patterns (picker + server)
// =============================================================================
const PATTERNS = [
    { id: "art_deco", name: "Art Deco", desc: "Repeating fan and sunburst arcs in 1920s Deco style — elegant on pearl or gold bases", swatch: "#ccaa55" },
    { id: "aurora_bands", name: "Aurora Bands", desc: "Flowing aurora borealis curtain bands with soft color gradients — stunning on dark bases", swatch: "#44cc99" },
    { id: "aztec", name: "Aztec", desc: "Bold stepped pyramid and angular Aztec/Mayan geometric blocks — tribal on matte or bronze", swatch: "#cc8844" },
    { id: "barbed_wire", name: "Barbed Wire", desc: "Coiled razor wire with barb spikes — aggressive, dangerous, industrial. Great on matte or blackout for prison/military look.", swatch: "#777788" },
    { id: "biomechanical", name: "Biomechanical", desc: "H.R. Giger-style organic-mechanical hybrid surface — alien biotech with woven cables, ribs, and dark organic structure", swatch: "#445544" },
    { id: "camo", name: "Camo", desc: "Digital splinter camo — angular blocks like military digital camouflage. Best on matte, cerakote, or blackout bases.", swatch: "#556644" },
    { id: "carbon_fiber", name: "Carbon Fiber", desc: "Classic 2x2 twill carbon weave — the #1 pattern. Works on any base. Sponsor-safe, professional, always looks right.", swatch: "#334455" },
    { id: "celtic_knot", name: "Celtic Knot", desc: "Flowing interwoven knot bands — old-world craft meets race car. Stunning on copper, bronze, or dark metallic bases.", swatch: "#668855" },
    { id: "chainlink", name: "Chain Link", desc: "Diagonal diamond wire grid like industrial chain-link fencing — gritty on matte or cerakote", swatch: "#999999" },
    { id: "chainmail", name: "Chainmail", desc: "Rows of interlocking metal rings like medieval armor mesh — great on chrome or brushed steel", swatch: "#999999" },
    { id: "chevron", name: "Chevron", desc: "Repeating V-stripe arrows — military warning stripes, aggressive directional energy. Works on any base.", swatch: "#cc8833" },
    { id: "corrugated", name: "Corrugated", desc: "Parallel raised ridges like corrugated sheet metal roofing — industrial on matte or brushed bases", swatch: "#889999" },
    { id: "crocodile", name: "Crocodile", desc: "Deep embossed square scales mimicking crocodile leather hide — luxurious on candy or satin", swatch: "#556644" },
    { id: "crosshatch", name: "Crosshatch", desc: "Fine overlapping diagonal lines — like pencil sketch shading. Subtle, elegant, works on any base. Sponsor-readable.", swatch: "#886644" },
    { id: "data_stream", name: "Data Stream", desc: "Horizontal streams of flowing data packets like a live network feed — sci-fi on dark bases", swatch: "#ff3366" },
    { id: "dazzle", name: "Dazzle", desc: "WWI-style dazzle camouflage — bold black/white Voronoi patches that break up the car's shape. Maximum visual chaos.", swatch: "linear-gradient(135deg, #ffffff 0%, #000000 50%, #ffffff 100%)" },
    { id: "diamond_plate", name: "Diamond Plate", desc: "Industrial tread plate — raised diamond shapes like truck bed liner. Tough, industrial, great on matte or brushed metal.", swatch: "#aaaaaa" },
    { id: "dragon_scale", name: "Dragon Scale", desc: "Overlapping scaled texture — reptile or armor style with depth shading per scale. Mythical creature aesthetic on candy or chrome.", swatch: "#44AA66", swatch_image: "/assets/patterns/artistic_cultural/dragon_scale.jpg" },
    { id: "dragon_scale_alt", name: "Dragon Scale (Alt)", desc: "Vibrant multi-color overlapping scale pattern with iridescent hue shifts per scale — exotic reptilian look", swatch: "#44aa88", swatch_image: "/assets/patterns/artistic_cultural/dragon_scale_alt.jpg" },
    { id: "expanded_metal", name: "Expanded Metal", desc: "Stretched diamond openings like industrial expanded metal sheet — rugged on metallic or matte", swatch: "#667777" },
    { id: "feather", name: "Feather", desc: "Layered overlapping feather barbs like bird plumage — soft organic texture on pearl or satin", swatch: "#667788" },
    { id: "fleur_de_lis", name: "Fleur-de-Lis", desc: "New Orleans royal French lily repeating motif with ornate petal symmetry — classic heraldic elegance", swatch: "#ccaa44", swatch_image: "/assets/patterns/artistic_cultural/fleur_de_lis.jpg" },
    { id: "fleur_de_lis_alt", name: "Fleur-de-Lis (Alt)", desc: "Subtle damask-style repeating French lily in soft relief — refined on satin or pearl bases", swatch: "#bbbbaa", swatch_image: "/assets/patterns/artistic_cultural/fleur_de_lis_alt.jpg" },
    { id: "fractal", name: "Fractal", desc: "Self-similar Mandelbrot/Julia fractal branching with infinite recursive detail — psychedelic on dark bases", swatch: "#6644cc" },
    { id: "giraffe", name: "Giraffe", desc: "Irregular organic polygon patches like giraffe spots — wild on candy, pearl, or warm metallics", swatch: "#cc9944" },
    { id: "glitch_scan", name: "Glitch Scan", desc: "Horizontal glitch scanline displacement bands with pixel offset and color channel separation artifacts", swatch: "#ff3366" },
    { id: "gothic_arch", name: "Gothic Arch", desc: "Ornate pointed arches in a repeating Gothic cathedral window grid — dramatic on dark bases", swatch: "#886644" },
    { id: "gothic_scroll", name: "Gothic Scroll", desc: "Dark flowing ornamental scroll filigree with curling vine tendrils — elegant on chrome or candy", swatch: "#554433" },
    { id: "greek_key", name: "Greek Key", desc: "Continuous right-angle meander border in ancient Greek key style — clean on gloss or metallic", swatch: "#bbaa77" },
    { id: "hailstorm", name: "Hailstorm", desc: "Dense scattered impact dimples like hailstone dents across the surface — raw on matte or satin", swatch: "#99aabb" },
    { id: "hammered", name: "Hammered", desc: "Irregular hand-hammered dimple texture like beaten metalwork — authentic on brushed or copper bases", swatch: "#998877" },
    { id: "hex_mesh", name: "Hex Mesh", desc: "Honeycomb wire mesh — hexagonal cells with glowing edges. Sci-fi, tactical, high-tech. Works on any base.", swatch: "#888899" },
    { id: "interference", name: "Interference", desc: "Rainbow wave interference — flowing color bands like oil on water. The chameleon pattern. Best on pearl or chrome.", swatch: "#ff44ff" },
    { id: "iron_emblem", name: "Iron Emblem", desc: "Bold angular heraldic emblem shapes tiled in a grid — strong on metallic or matte bases", swatch: "#886644" },
    { id: "japanese_wave", name: "Japanese Wave", desc: "Kanagawa-style great wave with curling foam crests — iconic on pearl, chrome, or deep blue bases", swatch: "#4488bb", swatch_image: "/assets/patterns/artistic_cultural/japanese_wave.jpg" },
    { id: "aztec_alt1", name: "Aztec (Alt 1)", desc: "Black and white geometric diamond and zigzag motifs — high-contrast Mesoamerican textile pattern for bold tribal builds", swatch: "#554433", swatch_image: "/assets/patterns/artistic_cultural/aztec_alt1.jpg" },
    { id: "aztec_alt2", name: "Aztec (Alt 2)", desc: "Earthy-toned central diamond and stepped geometric design", swatch: "#886644", swatch_image: "/assets/patterns/artistic_cultural/aztec_alt2.jpg" },
    { id: "kevlar_weave", name: "Kevlar Weave", desc: "Tight golden aramid fiber weave like ballistic Kevlar fabric — tactical on matte or cerakote", swatch: "#998833" },
    { id: "leopard", name: "Leopard", desc: "Organic leopard rosette spots with dark ring outlines — exotic on candy, gold, or warm metallics", swatch: "#ccaa66" },
    { id: "lightning", name: "Lightning", desc: "Forked branching lightning bolts — electric storm over your paint. Dramatic on chrome, candy, or vantablack.", swatch: "#eedd44" },
    { id: "mandala", name: "Mandala", desc: "Radially symmetric mandala flower with layered petal rings — ornate on pearl or chrome bases", swatch: "#cc77aa", swatch_image: "/assets/patterns/artistic_cultural/mandala.jpg" },
    { id: "mandela_ornate", name: "Mandala Ornate", desc: "Rich ornate mandala or paisley swirl in gold and deep tones", swatch: "#884466", swatch_image: "/assets/patterns/artistic_cultural/mandela_ornate.jpg" },
    { id: "matrix_rain", name: "Matrix Rain", desc: "Falling columns of green glowing characters like the Matrix digital rain — cyber on dark bases", swatch: "#22cc44" },
    { id: "metal_flake", name: "Metal Flake", desc: "Coarse visible sparkle flake — like glitter embedded in paint. Maximum sparkle effect. Best on metallic or candy.", swatch: "#aabbcc" },
    { id: "mosaic", name: "Mosaic", desc: "Irregular colored tile fragments like stained-glass mosaic windows — vibrant on any gloss base", swatch: "#aa6688", swatch_image: "/assets/patterns/artistic_cultural/mosaic.jpg" },
    { id: "muertos_dod1", name: "Muertos DOD 1", desc: "Day of the Dead — sugar skulls, maracas, peppers and bones on dark backgrounds. Dia de los Muertos celebration motif.", swatch: "#662244", swatch_image: "/assets/patterns/artistic_cultural/muertos_dod1.jpg" },
    { id: "muertos_dod2", name: "Muertos DOD 2", desc: "Day of the Dead — sugar skulls and flowers on light background. Light-toned variant of the DOD celebration pattern.", swatch: "#DDCCDD", swatch_image: "/assets/patterns/artistic_cultural/muertos_dod2.jpg" },
    { id: "multicam", name: "Multicam", desc: "Five-layer organic Perlin noise camouflage with blended earth-tone blobs — military on matte", swatch: "#778855" },
    { id: "nanoweave", name: "Nanoweave", desc: "Ultra-fine microscopic nano fiber weave barely visible at distance — subtle tech on any base", swatch: "#556688" },
    { id: "rune_symbols", name: "Rune Symbols", desc: "Angular runic glyph symbols in a repeating grid like carved Norse inscription — bold on matte", swatch: "#8877aa", swatch_image: "/assets/patterns/artistic_cultural/norse_rune.jpg" },
    { id: "optical_illusion", name: "Optical Illusion", desc: "Moire interference pattern — overlapping grids create visual depth tricks", swatch: "#4444cc" },
    { id: "five_point_star", name: "Five-Point Star", desc: "Five-pointed stars tiled in a geometric array — bold patriotic or military on any base", swatch: "#993355" },
    { id: "perforated", name: "Perforated", desc: "Evenly spaced punched round holes in a grid like perforated speaker grille — clean on metallic", swatch: "#555566" },
    { id: "pinstripe", name: "Pinstripe", desc: "Thin parallel racing pinstripes running lengthwise — classic hot rod detail on any gloss base", swatch: "#556688" },
    { id: "pixel_grid", name: "Pixel Grid", desc: "Retro 8-bit pixel blocks in a chunky mosaic grid — nostalgic arcade style on matte or gloss", swatch: "#44aa44" },
    { id: "plaid", name: "Plaid", desc: "Overlapping horizontal and vertical tartan plaid bands in classic Scottish weave — bold on satin", swatch: "#cc4444" },
    { id: "plasma", name: "Plasma", desc: "Branching plasma veins — electric energy web across the surface. Sci-fi effect, great on chrome or vantablack.", swatch: "#7744dd" },
    { id: "razor_wire", name: "Razor Wire", desc: "Coiled helical razor wire with sharp barbed loops — menacing industrial on matte or cerakote", swatch: "#777788" },
    { id: "ripple", name: "Ripple", desc: "Concentric expanding rings from water droplet impacts — smooth calming effect on pearl or gloss", swatch: "#4488aa" },
    { id: "sandstorm", name: "Sandstorm", desc: "Dense blowing sand particle streaks like a desert windstorm — gritty weathered on matte or satin", swatch: "#ccaa77" },
    { id: "skull", name: "Skull", desc: "Tiled skull shapes with hollow eyes — aggressive, dark, rebellious. Best on matte, blackout, or chrome bases.", swatch: "#444444" },
    { id: "skull_wings", name: "Skull Wings", desc: "Affliction-style winged skull ornamental spread with feathered bone wings — biker gothic on matte or chrome", swatch: "#444444" },
    { id: "shokk_bitrot", name: "SHOKK Bitrot", desc: "Corrupted binary data blocks with random degradation and glitch artifacts", swatch: "#ff2244" },
    // 2026-04-19 HEENAN HB2 — `shokk_cipher` already exists as a SHOKK Series
    // BASE (L232). Cross-registry id collision → BASES_BY_ID / PATTERNS_BY_ID
    // would silently overwrite. Renamed PATTERN entry to shokk_cipher_pattern
    // to preserve the computer-glitch pattern while letting the BASE keep its
    // canonical id. Bockwinkel SHOKK audit.
    { id: "shokk_cipher_pattern", name: "SHOKK Cipher (Pattern)", desc: "Encrypted data stream with pseudorandom blocks and key boundary markers", swatch: "#33ff88" },
    { id: "shokk_firewall", name: "SHOKK Firewall", desc: "Network defense grid with probe attempts and breach scatter marks", swatch: "#4488ff" },
    { id: "shokk_hex_dump", name: "SHOKK Hex Dump", desc: "Hexadecimal memory dump visualization with address and ASCII columns", swatch: "#88ff33" },
    { id: "shokk_kernel_panic", name: "SHOKK Kernel Panic", desc: "System crash dump with structured header and cascading memory corruption", swatch: "#ff4400" },
    { id: "shokk_overflow", name: "SHOKK Overflow", desc: "Buffer overflow — orderly data cascading into chaos at overflow points", swatch: "#ff8800" },
    { id: "shokk_packet_storm", name: "SHOKK Packet Storm", desc: "Dense data packet headers and payloads as structured blocks", swatch: "#00ccff" },
    { id: "shokk_scan_line", name: "SHOKK Scan Line", desc: "CRT/VHS scan line effect with line dropout and tracking errors", swatch: "#aabb44" },
    { id: "shokk_signal_noise", name: "SHOKK Signal Noise", desc: "Digital signal-to-noise ratio with clean bands interrupted by noise bursts", swatch: "#ff66cc" },
    { id: "shokk_zero_day", name: "SHOKK Zero Day", desc: "Exploit injection — clean data with precisely placed anomalous insertions", swatch: "#cc00ff" },
    { id: "snake_skin", name: "Snake Skin", desc: "Elongated overlapping reptile scales like snake belly skin — exotic on candy, chrome, or satin", swatch: "#668844" },
    { id: "snake_skin_2", name: "Snake Skin 2", desc: "Diamond-shaped python scales with subtle color variation between individual scale faces — exotic reptile", swatch: "#557733" },
    { id: "snake_skin_3", name: "Snake Skin 3", desc: "Hourglass saddle-shaped viper scales like rattlesnake dorsal markings — wild on matte or bronze", swatch: "#887744" },
    { id: "snake_skin_4", name: "Snake Skin 4", desc: "Small cobblestone-like pebble scales mimicking boa constrictor skin — textured on satin or candy", swatch: "#667755" },
    { id: "solar_flare", name: "Solar Flare", desc: "Erupting solar coronal mass ejection tendrils like sun surface plasma arcs — fiery on chrome", swatch: "#ee8833" },
    { id: "sound_wave", name: "Sound Wave", desc: "Audio waveform oscillation bands like an oscilloscope display — tech effect on dark or chrome", swatch: "#4488bb" },
    { id: "spiderweb", name: "Spiderweb", desc: "Radial spokes and concentric rings forming a spiderweb pattern — creepy on matte or vantablack", swatch: "#aaaaaa" },
    { id: "stardust", name: "Stardust", desc: "Scattered bright star sparkles — like a galaxy of glitter points. Stunning on candy, chrome, or vantablack.", swatch: "#ccaa44" },
    { id: "steampunk_gears", name: "Steampunk Gears", desc: "Interlocking clockwork gear wheels in a steampunk mechanical array — great on bronze or copper", swatch: "#bb8844", swatch_image: "/assets/patterns/artistic_cultural/steampunk_gears.jpg" },
    { id: "tessellation", name: "Tessellation", desc: "Interlocking M.C. Escher-style tile shapes that fit together with no gaps — artful on any base", swatch: "#6688aa" },
    { id: "thorn_vine", name: "Thorn Vine", desc: "Twisted thorny vines with sharp barbs in a dark botanical tangle — gothic on matte or black", swatch: "#445533" },
    { id: "tiger_stripe", name: "Tiger Stripe", desc: "Organic broken tiger stripe bands with irregular edges — aggressive on candy or metallic bases", swatch: "#556688" },
    { id: "tornado", name: "Tornado", desc: "Spiraling funnel vortex with rotating debris bands like a tornado — dramatic on dark or chrome", swatch: "#778899" },
    { id: "voronoi_shatter", name: "Voronoi Shatter", desc: "Clean Voronoi cell shatter with sharp cracked edges like broken safety glass — bold on chrome", swatch: "#7799bb" },
    { id: "biomechanical_2", name: "Biomechanical (Alt)", desc: "Abstract organic-mechanical variant — alternate Giger-inspired biotech surface with denser cable structure and rib detail", swatch: "#445544" },
    { id: "fractal_2", name: "Fractal (Variant 2)", desc: "Self-similar branching fractal with alternate coloring and depth — psychedelic on dark bases", swatch: "#6644cc" },
    { id: "fractal_3", name: "Fractal (Variant 3)", desc: "Dense fractal branching variant with tighter recursion and finer detail — trippy on chrome", swatch: "#6644cc" },
    { id: "optical_illusion_2", name: "Optical Illusion (Alt)", desc: "Overlapping grid interference creating visual depth and shimmer — hypnotic on gloss or pearl", swatch: "#4444cc" },
    { id: "stardust_2", name: "Stardust (Alt)", desc: "Alternate starfield sparkle with varied density and brightness — cosmic on vantablack or candy", swatch: "#ccaa44" },
    { id: "Art_Deco", name: "Art Deco Classic", desc: "1920s Art Deco geometric fan and sunburst motif with radiating spokes and gilded symmetry — timeless", swatch: "#ccaa55" },
    { id: "Art_Deco_V2", name: "Art Deco V2", desc: "Art Deco variant with bold radial symmetry and metallic tones — second pass with thicker spokes and warmer palette", swatch: "#BB9944" },
    { id: "Art_Deco_V3", name: "Art Deco V3", desc: "Layered Art Deco fan arcs with nested chevron geometry in gold tones — luxurious on any base", swatch: "#aa8844" },
    { id: "Art_Deco_V4", name: "Art Deco V4", desc: "Refined Art Deco stepped terraces and fan motifs with clean symmetry — elegant on pearl or chrome", swatch: "#ddbb66" },
    { id: "Billabong_Board", name: "Billabong Board", desc: "Billabong surf brand tiled board and wave graphic repeat — beach lifestyle imagery for surf-and-skate themed builds", swatch: "#D4C9A0" },
    { id: "Billabong_Surf_Style", name: "Billabong Surf Style", desc: "Billabong street surf collage with boards, palms, and waves layered together — coastal Australian surf vibe", swatch: "#5588AA" },
    { id: "Blind_Skateboy", name: "Blind Skateboy", desc: "Skate culture graphic with bold typography and street style — Blind Skateboards crew aesthetic for skate-themed liveries", swatch: "#333333" },
    { id: "Bong_Surfer", name: "Bong Surfer", desc: "Surf and chill vibes with wave and rider motif in laid-back coastal palette — beach culture on any base", swatch: "#2266aa" },
    { id: "Hardcore_Punk", name: "Hardcore Punk", desc: "Punk rock aesthetic with aggressive type and attitude — DIY rebellion graphic for hardcore-styled builds on matte bases", swatch: "#CC2222" },
    { id: "Hero_Skate", name: "Hero Skate", desc: "Heroic skate deck style with strong graphic impact — bold central figure on a deck-shaped repeat for street-culture builds", swatch: "#884422" },
    { id: "Hydro_Wave", name: "Hydro Wave", desc: "Fluid water motion surf pattern with cresting wave curls and spray mist — ocean energy on gloss", swatch: "#4488cc" },
    { id: "Punk_Rock_Zine", name: "Punk Rock Zine", desc: "DIY punk rock zine collage with cut-and-paste ransom-note typography and raw xerox textures", swatch: "#222222" },
    { id: "Skate_Deck", name: "Skate Deck", desc: "Skateboard deck graphic style with wood grain and print — bottom-of-board imagery layered for street culture liveries", swatch: "#553322" },
    { id: "Skate_Reaper_Glowing_Eyes", name: "Skate Reaper (Glowing)", desc: "Skate culture reaper figure with eerie glowing green eyes — dark street graphic on matte bases", swatch: "#22aa44" },
    { id: "Skate_Reaper_Tiled", name: "Skate Reaper Tiled", desc: "Tiled repeating skate reaper skulls in a seamless dark graphic pattern — street on matte bases", swatch: "#444444" },
    { id: "Surf_80s", name: "Surf 80s", desc: "Neon 80s surf with checkerboard palms and Memphis splatter — radical retro beach pattern with bright palette", swatch: "#FF33CC" },
    { id: "Surfin_80s", name: "Surfin' 80s", desc: "Retro Ocean Pacific surf icons with warm 80s color palette — vintage California beach culture motifs", swatch: "#CC6633" },
    { id: "Thrash_Metal_Skate_Alt", name: "Thrash Metal Skate (Alt)", desc: "Thrash metal and skate culture crossover graphic with aggressive typography and dark imagery — alternate variant with denser layout", swatch: "#662211" },
    { id: "Thrash_Metal_Skate", name: "Thrash Metal Skate", desc: "Thrash metal and skate culture fusion graphic with aggressive band-style lettering and dark street energy", swatch: "#441111" },
    { id: "Tiki_Surf", name: "Tiki Surf", desc: "Tiki and surf combo with tropical and wave elements — Polynesian beach-bar aesthetic for chill island-themed builds", swatch: "#228855" },
    { id: "wave", name: "Wave", desc: "Smooth flowing sine wave ripples across the surface like gentle water motion — clean on any base", swatch: "#4488bb" },
    { id: "zebra", name: "Zebra", desc: "Bold black and white zebra stripes with organic curved edges — high contrast on any base", swatch: "#cccccc" },
    { id: "basket_weave_alt", name: "Basket Weave (Alt)", desc: "Image-based basket weave carbon fiber with alternating strand blocks — textured composite look", swatch: "#333333" },
    { id: "carbon_alt_1", name: "Carbon Alt 1", desc: "Image-based alternative carbon fiber weave with different thread spacing and reflection angle", swatch: "#2a2a2a" },
    // 2026-04-19 HEENAN H4HR-2 — `carbon_weave` collided with BASES L302
    // (and SPEC_PATTERNS, fixed earlier in HP2). PATTERNS-tier entry
    // renamed; HP-MIGRATE handles backward compat. BASE keeps canonical id.
    { id: "carbon_weave_pattern", name: "Carbon Weave (Pattern)", desc: "Image-based tightly woven carbon fiber with visible twill weave texture and deep black sheen", swatch: "#1a1a1a" },
    { id: "exhaust_wrap_alt", name: "Exhaust Wrap (Alt)", desc: "Image-based woven fiberglass exhaust wrap with tan crosshatch heat-shield textile texture", swatch: "#665544" },
    { id: "geo_weave", name: "Geo Weave", desc: "Image-based geometric weave carbon with angular interlocking fiber bundles — structured look", swatch: "#444444" },
    { id: "hex_carbon", name: "Hex Carbon", desc: "Image-based hexagonal weave carbon fiber with honeycomb-shaped fiber bundle crossings", swatch: "#222222" },
    { id: "multi_directional", name: "Multi-Directional", desc: "Image-based multi-directional carbon fragments with randomized fiber angles — chaotic composite texture", swatch: "#3a3a3a" },
    { id: "wavy_carbon", name: "Wavy Carbon", desc: "Image-based wavy carbon fiber with flowing undulating weave direction — dynamic organic carbon", swatch: "#2c2c2c" },
    { id: "fresnel_ghost", name: "Fresnel Ghost", desc: "Hidden hex pattern - invisible head-on, appears at grazing angles via Fresnel amplification", swatch: "#889999" },
    { id: "caustic", name: "Caustic", desc: "Underwater dancing light - golden-ratio sine wave interference caustic pools", swatch: "#88ccdd" },
    { id: "dimensional", name: "Dimensional", desc: "Newton's rings thin-film interference - rainbow concentric ring iridescence", swatch: "#99aadd" },
    { id: "neural", name: "Neural", desc: "Living neural network - Voronoi cells with connecting axon pathways", swatch: "#77aacc" },
    { id: "p_plasma", name: "Plasma (PARADIGM)", desc: "Plasma ball discharge - electric tendrils from overlapping sine fields", swatch: "#9944dd" },
    { id: "holographic", name: "Holographic (PARADIGM)", desc: "Hologram diffraction grating - multi-angle rainbow interference lines", swatch: "#aa88ff" },
    { id: "p_topographic", name: "Topographic (PARADIGM)", desc: "Contour map elevation lines - terrain-style isolines from noise field", swatch: "#88aa66" },
    { id: "p_tessellation", name: "Tessellation (PARADIGM)", desc: "Geometric Penrose-style tiling - triangular grid interference edges", swatch: "#7788cc" },
    { id: "circuitboard", name: "Circuit Board (PARADIGM)", desc: "PCB trace routing with via pads and copper trace pathways", swatch: "#228844" },
    { id: "soundwave", name: "Sound Wave (PARADIGM)", desc: "Audio frequency waveform with amplitude modulation bands", swatch: "#4466bb" },
    { id: "shimmer_quantum_shard", name: "Shimmer: Quantum Shard", desc: "Faceted shard micro-splits that throw sharp, odd color flips under light.", swatch: "#6f7cd4" },
    { id: "shimmer_prism_frost", name: "Shimmer: Prism Frost", desc: "Crossed crystalline frost lines with cool prism lift and glassy breakup.", swatch: "#9bb7de" },
    { id: "shimmer_velvet_static", name: "Shimmer: Velvet Static", desc: "Matte-leaning ultra-fine grain that shimmers softly without chrome glare.", swatch: "#58606e" },
    { id: "shimmer_chrome_flux", name: "Shimmer: Chrome Flux", desc: "Directional high-energy sheen bands for liquid chrome sweep behavior.", swatch: "#c3cedd" },
    { id: "shimmer_matte_halo", name: "Shimmer: Matte Halo", desc: "Soft concentric micro-halos that deepen matte finishes with subtle sparkle.", swatch: "#7b7f88" },
    { id: "shimmer_oil_tension", name: "Shimmer: Oil Tension", desc: "Thin-film interference waves with unstable rainbow travel and depth.", swatch: "#405068" },
    { id: "shimmer_neon_weft", name: "Shimmer: Neon Weft", desc: "Tight woven micro-filaments that alternate warm/cool electric edges.", swatch: "#5d3e89" },
    { id: "shimmer_void_dust", name: "Shimmer: Void Dust", desc: "Dark-space field peppered with sparse, explosive micro spark points.", swatch: "#1f2534" },
    { id: "shimmer_turbine_sheen", name: "Shimmer: Turbine Sheen", desc: "Curved rotational blade cues for kinetic reflections that feel in motion.", swatch: "#6f8a9f" },
    { id: "shimmer_spectral_mesh", name: "Shimmer: Spectral Mesh", desc: "Hybrid mesh lattice balancing chrome flashes and matte depth pockets.", swatch: "#4d6a7f" },
    { id: "12155818_4903117", name: "Rainbow Halftone Dots", desc: "60s rainbow halftone dots — Lichtenstein-style Ben-Day comic-book printing pattern. Use pattern scale to tile small on canvas.", swatch: "#6688CC" },
    { id: "12267458_4936872", name: "Mod Color Block (Mondrian)", desc: "Image pattern — bold mod color block grid with sharp Mondrian-style geometric divisions", swatch: "#cc2222" },
    { id: "12284536_4958169", name: "Psychedelic Wave", desc: "Image pattern — psychedelic flowing wave with saturated color bands and optical distortion", swatch: "#8844cc" },
    { id: "12428555_4988298", name: "Retro Stripe (70s Warm)", desc: "Image pattern — retro vintage stripes with warm 70s color palette and parallel band rhythm", swatch: "#cc4400" },
    { id: "144644845_10133112", name: "Patchwork Square", desc: "Image pattern — 70s patchwork quilt squares with mixed earth-tone fabric swatches tiled", swatch: "#886644" },
    { id: "248169", name: "Abstract Gradient", desc: "70s abstract color gradient blocks with soft transitions and earthy palette — use pattern scale to tile small on canvas", swatch: "#8899AA" },
    { id: "6868396_23455", name: "Bold Geometric", desc: "70s bold geometric shapes in warm earth tones with strong outline contrast — use pattern scale to tile small on canvas", swatch: "#AA6644" },
    { id: "78534344_9837553_1", name: "Disco Sparkle", desc: "70s disco glitter sparkle with mirror-ball reflection points — use pattern scale to tile small for shimmery surface effect", swatch: "#FFCC00" },
    { id: "Groovy_Swirl", name: "Groovy Swirl", desc: "70s groovy spiral pattern with hippie-era curves and warm psychedelic palette — use pattern scale to tile small", swatch: "#AA6688" },
    { id: "Halftone_Rainbow", name: "Halftone Rainbow", desc: "Image pattern — rainbow halftone dot gradient with shifting color through Ben-Day dot sizes", swatch: "#6688cc" },
    { id: "Plad_Wrapper", name: "Plaid Wrapper", desc: "70s plaid/tartan with classic intersecting bands in earthy mid-tone palette — use pattern scale to tile small on canvas", swatch: "#886644" },
    { id: "decade_50s_diner_checkerboard", name: "Diner Checkerboard", desc: "Classic black and white alternating diner floor tiles in checkerboard grid — retro on any base", swatch: "#222222" },
    { id: "decade_50s_jukebox_arc", name: "Jukebox Arc", desc: "Wurlitzer jukebox concentric rainbow arcs fanning outward — retro 50s on chrome or candy", swatch: "#cc4488" },
    { id: "decade_50s_sputnik_orbit", name: "Sputnik Orbit", desc: "Sputnik satellite orbit trail arcs with radio signal dots — space age on matte or metallic", swatch: "#4488aa" },
    { id: "decade_50s_drivein_marquee", name: "Drive-In Marquee", desc: "Chasing light bulbs in a drive-in movie marquee border — nostalgic warm glow on gloss or chrome", swatch: "#ffaa22" },
    { id: "decade_50s_fallout_shelter", name: "Fallout Shelter", desc: "Cold War radiation trefoil symbol with concentric warning rings — atomic age on matte or yellow", swatch: "#ccaa44" },
    { id: "decade_50s_boomerang_formica", name: "Boomerang Formica", desc: "Retro 50s kitchen boomerang and starburst Formica shapes scattered on mid-century palette", swatch: "#668844" },
    { id: "decade_50s_atomic_reactor", name: "Atomic Reactor Core", desc: "Layered radiation rings, particle trails, and scintillation marks — atomic-age science fair aesthetic on glow-bright bases", swatch: "#CCAA44" },
    { id: "decade_50s_diner_chrome", name: "Chrome Diner Counter", desc: "Warped chrome reflections with Fresnel curves and overhead lamp highlights — vintage 50s diner counter aesthetic", swatch: "#CCDDEE" },
    { id: "decade_50s_crt_phosphor", name: "CRT Phosphor", desc: "RGB phosphor dot triads with horizontal scanlines and bloom glow — retro CRT television look", swatch: "#6688aa" },
    { id: "decade_50s_casino_felt", name: "Casino Felt", desc: "Green gaming felt with soft nap, subtle card suit motifs, and dealer chalk marks — Las Vegas 50s casino floor aesthetic", swatch: "#1A4D1A" },
    { id: "decade_60s_peace_sign", name: "Peace Sign", desc: "Peace symbol with radial energy lines emanating outward — 60s counterculture on bright bases", swatch: "#44aa66" },
    { id: "decade_60s_tie_dye_spiral", name: "Tie-Dye Spiral", desc: "Tie-dye spiral with rainbow bands radiating from center in classic hippie fabric dye technique — groovy", swatch: "#8844cc" },
    { id: "decade_60s_lava_lamp_blob", name: "Lava Lamp Blob", desc: "Floating lava lamp blobs in warm amber glow — groovy 60s psychedelic on candy or gloss bases", swatch: "#cc6622" },
    { id: "decade_60s_opart_illusion", name: "Retro Stripe", desc: "Op-art warped parallel lines creating optical depth illusion — mesmerizing tiled on any base", swatch: "#000000" },
    { id: "decade_60s_pop_art_halftone", name: "Pop Art Halftone", desc: "Lichtenstein-style Ben-Day halftone dots with bold pop art color and comic book print texture — 60s icon", swatch: "#ffff00" },
    { id: "decade_60s_gogo_check", name: "Mod Color Block", desc: "Mondrian-style primary color block grid with bold black borders — mod 60s tiled on gloss", swatch: "#ffffff" },
    { id: "decade_60s_caged_square", name: "Caged Square", desc: "Mod 60s caged square grid with nested geometric frames — clean pop art on gloss or satin bases", swatch: "#2244aa" },
    { id: "decade_60s_peter_max_gradient", name: "Peter Max Gradient", desc: "Bold Peter Max poster-style gradient with saturated pop-art color blends — psychedelic on gloss", swatch: "#ff0088" },
    { id: "decade_60s_peter_max_alt", name: "Peter Max Alt", desc: "Bold Peter Max poster colors in a tiled repeat with vivid contrast and cosmic energy", swatch: "#ff44cc" },
    { id: "decade_70s_earth_tone_geo", name: "Earth Tone Geo", desc: "Harvest gold and avocado green geometric shapes in earthy 70s palette — retro kitchen tile aesthetic", swatch: "#886655" },
    { id: "decade_70s_funk_zigzag", name: "Funk Zigzag", desc: "Bold zigzag stripes in warm earth-funk brown and orange palette — groovy 70s disco energy on any base", swatch: "#ffaa00" },
    { id: "decade_70s_studio54_glitter", name: "Studio 54 Glitter", desc: "Dense disco glitter sparkle with crossing spotlight beams — Studio 54 glamour on chrome or candy", swatch: "#ffcc00" },
    { id: "decade_70s_pong_pixel", name: "Pong Pixel", desc: "Atari Pong court with center line, paddles, and ball — pixel-perfect retro game on dark bases", swatch: "#00ff00" },
    { id: "decade_80s_pacman_maze", name: "Pac-Man Maze", desc: "Classic Pac-Man arcade maze corridors with ghosted character silhouettes — retro 80s on black", swatch: "#ffff00" },
    { id: "decade_80s_neon_grid", name: "Neon Grid", desc: "Tron-style neon glowing perspective grid receding to vanishing point — cyber 80s on dark bases", swatch: "#00ffff" },
    { id: "decade_80s_rubiks_cube", name: "Rubik's Cube", desc: "Rubik's Cube 3x3 face with colored squares in classic scrambled arrangement — 80s pop on gloss", swatch: "#ff0000" },
    { id: "decade_80s_rubiks_cube_2", name: "Rubik's Cube (Variation 2)", desc: "Rubik's Cube alternate face layout with different color scramble pattern — variation 2", swatch: "#00aa00" },
    { id: "decade_80s_rubiks_cube_3", name: "Rubik's Cube (Variation 3)", desc: "Rubik's Cube third face variant with blue-dominant color scramble — cool-toned 80s pop", swatch: "#0066ff" },
    { id: "decade_80s_boombox_speaker", name: "Boombox Speaker", desc: "Boombox speaker cone with circular grille mesh and woofer rings — 80s hip-hop on matte bases", swatch: "#333333" },
    { id: "decade_80s_nintendo_dpad", name: "Nintendo D-Pad", desc: "NES controller D-pad cross and A/B buttons in pixel-perfect detail — 80s gaming on flat bases", swatch: "#cc0000" },
    { id: "decade_80s_breakdance_spin", name: "Breakdance Spin", desc: "Radial motion blur spin lines emanating from center like a breakdancer's headspin — dynamic 80s", swatch: "#ff2288" },
    { id: "decade_80s_laser_tag", name: "Laser Tag", desc: "Crossing neon laser beams cutting through fog haze — 80s arcade atmosphere on dark bases", swatch: "#00ff00" },
    { id: "decade_80s_leg_warmer", name: "Leg Warmer", desc: "Ribbed hot pink knit texture like 80s leg warmers with stretchy vertical rib lines", swatch: "#ff69b4" },
    { id: "decade_90s_grunge_splatter", name: "Grunge Splatter", desc: "Grunge ink splatter and paint drip grime texture — 90s alternative distressed on matte bases", swatch: "#443322" },
    { id: "decade_90s_nirvana_smiley", name: "Nirvana Smiley", desc: "Nirvana-style smiley face with crossed-out eyes and crooked grin — 90s grunge icon on any base", swatch: "#ffff00" },
    { id: "decade_90s_cross_colors", name: "Cross Colors", desc: "Bold asymmetric color blocks in Cross Colours streetwear style — 90s hip-hop on gloss or satin", swatch: "#ff0000" },
    { id: "decade_90s_tamagotchi_egg", name: "Tamagotchi Egg", desc: "Tamagotchi egg shape with tiny pixel LCD screen showing a virtual pet — cute 90s nostalgia", swatch: "#ff88aa" },
    { id: "decade_90s_sega_blast", name: "Sega Blast", desc: "Sonic-style horizontal speed blur with blue motion streaks and ring scatter — 90s gaming energy", swatch: "#0066ff" },
    { id: "decade_90s_fresh_prince", name: "Fresh Prince", desc: "Bold geometric streetwear blocks in Fresh Prince style with bright 90s color clash palette", swatch: "#448844" },
    { id: "decade_90s_floppy_disk", name: "Floppy Disk", desc: "3.5-inch floppy disk with metal slider, label area, and write-protect tab — 90s tech icon", swatch: "#0000ff" },
    { id: "decade_90s_rave_zigzag", name: "Rave Zigzag", desc: "Neon zigzag energy bolts in rave fluorescent colors — 90s dance culture on dark or black bases", swatch: "#00ffff" },
    { id: "decade_90s_y2k_bug", name: "Y2K Bug", desc: "Digital glitch corruption with cascading binary code and millennium bug panic — late 90s tech", swatch: "#ff0000" },
    { id: "decade_90s_tribal_tattoo", name: "Tribal Tattoo", desc: "Flowing tribal tattoo blackwork with sharp curves and pointed tips — 90s ink style on any base", swatch: "#222222" },
    { id: "decade_90s_dialup_static", name: "Dial-Up Static", desc: "Dial-up modem static noise with horizontal loading progress bars — 90s internet on dark bases", swatch: "#448844" },
    { id: "decade_90s_slap_bracelet", name: "Slap Bracelet", desc: "Coiled slap bracelet band with holographic rainbow sheen surface — fun 90s on chrome or pearl", swatch: "#8888cc" },
    { id: "decade_90s_windows95", name: "Windows 95", desc: "Windows 95 teal desktop with gray start bar and window chrome — iconic 90s computing nostalgia", swatch: "#008080" },
    { id: "decade_90s_chrome_bubble", name: "Chrome Bubble", desc: "Inflated 3D chrome bubble letters with shiny reflections — 90s graffiti style on gloss or candy", swatch: "#aaddff" },
    { id: "decade_90s_rugrats_squiggle", name: "Rugrats Squiggle", desc: "Chaotic squiggly cartoon lines in Rugrats animation style — playful 90s kids energy on gloss", swatch: "#ffcc66" },
    { id: "decade_90s_rollerblade_streak", name: "Rollerblade Streak", desc: "Rollerblade speed streaks with wheel spark trails — 90s inline skating energy on any bright base", swatch: "#ffff00" },
    { id: "decade_90s_beanie_tag", name: "Beanie Tag", desc: "TY Beanie Baby heart-shaped hang tag with red heart logo — 90s collectible nostalgia on any base", swatch: "#ff6699" },
    { id: "decade_90s_dot_matrix", name: "Dot Matrix", desc: "Dot matrix printer output with visible pin-strike dots and tractor-feed perforations — retro", swatch: "#333333" },
    { id: "decade_90s_geo_minimal", name: "Geo Minimal", desc: "Minimal geometric primitives — circle, square, and triangle in clean 90s design grid layout", swatch: "#446688" },
    { id: "decade_90s_sbtb_wall", name: "SBTB Wall", desc: "Saved by the Bell angular Memphis-style wall with bright zigzag shapes and bold color blocks", swatch: "#ff4488" },
    // ── TRIBAL & ANCIENT (2026-03-28) ──────────────────────────────────────────
    { id: "spiral_fern", name: "Spiral Fern", desc: "Logarithmic spiral fern frond uncoiling motif with fractal self-similarity — organic botanical elegance", swatch: "#557766" },
    { id: "zigzag_bands", name: "Zigzag Bands", desc: "Alternating zigzag and crosshatch geometric bands in stacked horizontal rows — tribal textile pattern", swatch: "#886644" },
    { id: "radial_calendar", name: "Radial Calendar", desc: "Radial calendar wheel with concentric ring bands and spoke dividers — ancient astronomical instrument look", swatch: "#cc8833" },
    { id: "triple_knot", name: "Triple Knot", desc: "Three interlocked rings at 120° forming triple knot — Celtic triskele symbol with woven over-under depth illusion", swatch: "#558844" },
    { id: "diagonal_interlace", name: "Diagonal Interlace", desc: "Diagonal over-under strand braid in tiled cells with woven depth illusion — Celtic interlace weaving", swatch: "#997744" },
    { id: "diamond_blanket", name: "Diamond Blanket", desc: "Diamond lattice grid with border accent stripes like Native American woven blanket patterns", swatch: "#cc6633" },
    { id: "step_fret", name: "Step Fret", desc: "L-shaped step fret motif with alternating rotation like Mesoamerican temple borders — bold geometric", swatch: "#bb8822" },
    { id: "concentric_dot_rings", name: "Concentric Dot Rings", desc: "Concentric ring dot art — periodic rings radiating from grid centers", swatch: "#994422" },
    { id: "medallion_lattice", name: "Medallion Lattice", desc: "Sinusoidal medallion interlace — crossed wave lattice medallion lines", swatch: "#336688" },
    { id: "eight_point_star", name: "Eight-Point Star", desc: "8-pointed geometric star — four-direction arm tiling with interlace weave", swatch: "#557799" },
    { id: "petal_frieze", name: "Petal Frieze", desc: "Radial petal cluster frieze — teardrop petal clusters with center stalk", swatch: "#aaaa44" },
    { id: "cloud_scroll", name: "Cloud Scroll", desc: "Ruyi cloud scroll — L-inf rectangular scroll rings with corner softening", swatch: "#aa4444" },
    // ── NATURAL TEXTURES (2026-03-28) ──────────────────────────────────────────
    { id: "marble_veining", name: "Marble Veining", desc: "Turbulence-warped sinusoidal marble vein network with secondary veins", swatch: "#ccbbaa" },
    { id: "wood_burl", name: "Wood Burl", desc: "Multi-center swirling concentric ellipse burl figure with noise warp", swatch: "#774422" },
    { id: "seigaiha_scales", name: "Seigaiha Scales", desc: "Japanese seigaiha — overlapping arched scale tiles with shadow edge", swatch: "#336699" },
    { id: "ammonite_chambers", name: "Ammonite Chambers", desc: "Ammonite fossil — log-spiral walls with radial suture line divisions", swatch: "#997755" },
    { id: "peacock_eye", name: "Peacock Eye", desc: "Peacock feather eye — elliptical rings with 20-barb radial overlay", swatch: "#336644" },
    // 2026-04-19 HEENAN H4HR-1 — `dragonfly_wing` collided with BASES L90.
    // PATTERNS-tier entry renamed; HP-MIGRATE handles backward compat for
    // saved configs. BASE keeps the canonical id.
    { id: "dragonfly_wing_pattern", name: "Dragonfly Wing (Pattern)", desc: "Dragonfly wing venation — Voronoi cell network with thin vein walls", swatch: "#aaccee" },
    { id: "insect_compound", name: "Compound Eye", desc: "Insect compound eye — hex close-packed ommatidium ring array", swatch: "#445544" },
    { id: "diatom_radial", name: "Diatom Radial", desc: "Radial diatom microorganism — 16 spokes + concentric rings + dot array", swatch: "#bbddcc" },
    { id: "coral_polyp", name: "Coral Polyp", desc: "Coral polyp tiling — 8-tentacle radial star with concentric oral disk rings", swatch: "#ff8866" },
    { id: "birch_bark", name: "Birch Bark", desc: "Birch bark — noise-warped horizontal lenticel bands with vertical crack lines", swatch: "#eeeedd" },
    { id: "pine_cone_scale", name: "Pine Cone Scale", desc: "Phyllotaxis-inspired scales — dual diagonal sine families forming diamond tiles", swatch: "#886633" },
    { id: "geode_crystal", name: "Geode Crystal", desc: "Geode crystal facets — Voronoi cells with per-facet directional sheen lines", swatch: "#aabbdd" },
    // ── TECH & CIRCUIT (2026-03-28) ──────────────────────────────────────────
    { id: "circuit_traces", name: "Circuit Traces", desc: "PCB circuit board — orthogonal grid traces with via pad rings at intersections", swatch: "#334455" },
    { id: "hex_circuit", name: "Hex Circuit", desc: "Hexagonal circuit grid — three-direction parallel lines forming hex trace network", swatch: "#335544" },
    { id: "biomech_cables", name: "Biomech Cables", desc: "Biomechanical cable bundles — sinusoidal twisted cables with circumferential ribs", swatch: "#443322" },
    { id: "dendrite_web", name: "Dendrite Web", desc: "Dendrite web — multi-scale fractal branching vein network", swatch: "#334433" },
    { id: "crystal_lattice", name: "Crystal Lattice", desc: "Crystal lattice — 45°-rotated diamond rhombus grid with atom nodes at vertices", swatch: "#aabbcc" },
    { id: "chainmail_hex", name: "Chainmail Hex", desc: "Hex chainmail — interlocking circular wire rings in hexagonal close-pack arrangement", swatch: "#778899" },
    { id: "graphene_hex", name: "Graphene Hex", desc: "Graphene lattice — ultra-fine honeycomb bond network with atom nodes at unit cell positions", swatch: "#333344" },
    { id: "gear_mesh", name: "Gear Mesh", desc: "Interlocking gear mesh — toothed circular gear with spokes and hub, tiled pattern", swatch: "#665544" },
    { id: "vinyl_record", name: "Vinyl Record", desc: "Vinyl record — ultra-fine concentric groove rings with label ring and spindle hole", swatch: "#222233" },
    { id: "fiber_optic", name: "Fiber Optic", desc: "Fiber optic bundle cross-section — hexagonally close-packed fiber cores with cladding", swatch: "#ccddee" },
    { id: "sonar_ping", name: "Sonar Ping", desc: "Sonar/radar ping — expanding concentric rings from multiple offset source points", swatch: "#112233" },
    { id: "waveform_stack", name: "Waveform Stack", desc: "Waveform stack — multiple layered oscilloscope sine traces offset vertically across the surface", swatch: "#223344" },
    // ── ART DECO & GEOMETRIC (2026-03-28) ────────────────────────────────────
    { id: "art_deco_fan", name: "Art Deco Fan", desc: "Art Deco fan — tiled semicircular fans with radiating spokes and concentric arc bands", swatch: "#cc9933" },
    { id: "chevron_stack", name: "Chevron Stack", desc: "Chevron stack — stacked V-chevrons via triangular-wave centerline, periodic in y", swatch: "#445566" },
    { id: "quatrefoil", name: "Quatrefoil", desc: "Quatrefoil — four overlapping circle-arc leaves forming a Gothic foil lattice", swatch: "#446644" },
    { id: "herringbone", name: "Herringbone", desc: "Herringbone — alternating-parity diagonal stripe directions in staggered rectangular cells", swatch: "#664433" },
    { id: "basket_weave", name: "Basket Weave", desc: "Basket weave — alternating horizontal and vertical strand blocks in 2×2 parity grid", swatch: "#885522" },
    { id: "houndstooth", name: "Houndstooth", desc: "Houndstooth — combined offset 45°-rotated checkerboards creating 4-pointed star tiles", swatch: "#333333" },
    { id: "argyle", name: "Argyle", desc: "Argyle — L1-norm diamond outline grid with diagonal crosshatch lines in alternate diamonds", swatch: "#336688" },
    { id: "tartan", name: "Tartan Plaid", desc: "Tartan plaid — intersecting stripe families with sett-defined widths forming a plaid grid", swatch: "#883333" },
    { id: "op_art_rings", name: "Op-Art Rings", desc: "Op-art squares — concentric L-inf square rings creating an optical pulsation illusion", swatch: "#222222" },
    { id: "moire_grid", name: "Moiré Grid", desc: "Moiré grid — two slightly angled parallel line families creating interference fringe patterns", swatch: "#334455" },
    { id: "lozenge_tile", name: "Lozenge Tile", desc: "Lozenge tile — offset-row diamond shapes with clean L1-norm border outlines", swatch: "#556677" },
    { id: "ogee_lattice", name: "Ogee Lattice", desc: "Ogee lattice — sinusoidally-warped grid creating S-curve Gothic arch shapes", swatch: "#557744" },
    { id: "reaction_diffusion", name: "Reaction Diffusion", desc: "Gray-Scott Turing activator-inhibitor spot and stripe morphogenesis pattern", swatch: "#336644" },
    { id: "fractal_fern", name: "Fractal Fern", desc: "Barnsley fern IFS attractor — self-similar leaf structure density map", swatch: "#2a5c2a" },
    { id: "hilbert_curve", name: "Hilbert Curve (Maze Walls)", desc: "Hilbert space-filling curve maze — walls between non-adjacent cells", swatch: "#445566" },
    { id: "lorenz_slice", name: "Lorenz Attractor", desc: "Lorenz butterfly chaotic attractor projected onto x/z density plane", swatch: "#554433" },
    { id: "julia_boundary", name: "Julia Set", desc: "Julia set fractal boundary — smooth escape-time bands of z-squared-plus-c", swatch: "#334455" },
    { id: "wave_standing", name: "Standing Wave", desc: "2D Chladni standing wave nodal lines from cosine interference products", swatch: "#446655" },
    { id: "lissajous_web", name: "Lissajous Web", desc: "Lissajous parametric curve web — sin 3:4 ratio implicit zero-contour family", swatch: "#553344" },
    { id: "dragon_curve", name: "Dragon Curve", desc: "Dragon curve fractal — multi-scale rotated right-angle self-similar grid", swatch: "#443355" },
    { id: "diffraction_grating", name: "Diffraction Grating", desc: "Holographic diffraction grating — six sinusoidal gratings at 30-degree intervals", swatch: "#335566" },
    { id: "perlin_terrain", name: "Perlin Terrain", desc: "Topographic terrain — multi-octave noise with ridged erosion scarring", swatch: "#554422" },
    { id: "phyllotaxis", name: "Phyllotaxis", desc: "Fibonacci phyllotaxis spiral — golden-angle seed packing distance field", swatch: "#226644" },
    { id: "truchet_flow", name: "Truchet Flow", desc: "Truchet flow tiles — random quarter-circle arcs forming organic flowing paths", swatch: "#334466" },
    { id: "concentric_op", name: "Concentric Op-Art", desc: "Bridget Riley dual-frequency concentric bands — beats produce optical vibration", swatch: "#445566" },
    { id: "checker_warp", name: "Checker Warp", desc: "Sine-warped checkerboard — sinusoidal displacement creates bulging impossible grid illusion", swatch: "#554433" },
    { id: "barrel_distort", name: "Barrel Distort", desc: "Barrel lens distortion grid — straight lines bow outward from image center", swatch: "#334455" },
    { id: "moire_interference", name: "Moiré Interference", desc: "Two grids at different scale and rotation producing classic moiré beat fringes", swatch: "#443355" },
    { id: "twisted_rings", name: "Twisted Rings", desc: "Concentric rings twisted by radius via Archimedean phase — spring vortex illusion", swatch: "#335566" },
    { id: "spiral_hypnotic", name: "Hypnotic Spiral", desc: "Archimedean spiral banded by phase offset — rotating depth vortex optical illusion", swatch: "#553344" },
    { id: "necker_grid", name: "Necker Grid", desc: "Isometric cube tiling with three shaded faces — Necker cube 3D/2D ambiguity illusion", swatch: "#446655" },
    { id: "radial_pulse", name: "Radial Pulse", desc: "24 radial spokes with radius-modulated width — apparent inward pulse motion illusion", swatch: "#554422" },
    { id: "hex_op", name: "Hex Tunnel", desc: "Nested hexagonal shells receding to vanishing point — 3D optical tunnel illusion", swatch: "#226644" },
    { id: "pinwheel_tiling", name: "Pinwheel Tiling", desc: "7 golden-angle grid overlaps approximate aperiodic pinwheel — no repeating tile direction", swatch: "#334466" },
    { id: "impossible_grid", name: "Impossible Grid", desc: "Phase-inverted alternating cells — interior/exterior swap creates impossible connectivity illusion", swatch: "#443344" },
    { id: "rose_curve", name: "Rose Curve", desc: "Rhodonea k=5 polar rose petal tiled field — five-petal outline with radial gradient fill", swatch: "#556633" },
    { id: "art_deco_sunburst", name: "Art Deco Sunburst", desc: "Chrysler Building iconic sunburst — 36 radial spokes with 5 concentric decorative ring bands", swatch: "#665533" },
    { id: "art_deco_chevron", name: "Art Deco Chevron", desc: "Bold 1920s double-stripe nested V chevrons — wide gaps between paired bands", swatch: "#554422" },
    { id: "greek_meander", name: "Greek Meander", desc: "Greek key right-angle hook spiral — ancient continuous meander motif tiled in alternating rows", swatch: "#556644" },
    { id: "star_tile_mosaic", name: "Star Tile Mosaic", desc: "8-pointed star tile — two overlapping L-inf norms create classic mosaic geometry", swatch: "#445566" },
    { id: "escher_reptile", name: "Escher Reptile", desc: "Escher-style hex reptile tessellation — alternating shaded cells with organic sine-deformed boundary", swatch: "#336644" },
    { id: "constructivist", name: "Constructivist", desc: "Soviet Constructivist geometry — orthogonal grid, 45-degree diagonals, and bold horizontal bands", swatch: "#553322" },
    { id: "bauhaus_system", name: "Bauhaus System", desc: "Bauhaus primary form grid — circle, square, and diamond outlines alternating across cells", swatch: "#446633" },
    { id: "celtic_plait", name: "Celtic Plait", desc: "Celtic plait braid — two diagonal strand families with over-under weave alternation", swatch: "#336655" },
    { id: "cane_weave", name: "Cane Weave", desc: "Cane/rattan weave — paired diagonal strands with gaps and over-under interlacing", swatch: "#554433" },
    { id: "cable_knit", name: "Cable Knit", desc: "Cable knit rope-twist — two crossing strands per column period with subtle rib background", swatch: "#445544" },
    { id: "damask_brocade", name: "Damask Brocade", desc: "Silk damask — four-petal rose with outer ring and diamond accent, figure-vs-ground contrast", swatch: "#664455" },
    { id: "tatami_grid", name: "Tatami Grid", desc: "Japanese tatami mat grid — 2:1 ratio rectangles in staggered alternating row layout", swatch: "#554433" },
    { id: "hypocycloid", name: "Hypocycloid", desc: "Tiled 5-cusped Spirograph hypocycloid — parametric star outline from hypotrochoid curve, k=5", swatch: "#553366" },
    { id: "voronoi_relaxed", name: "Voronoi Relaxed", desc: "Centroidal Voronoi relaxed cells — jitter-grid seeds produce uniform organic cell borders", swatch: "#445566" },
    { id: "wave_ripple_2d", name: "Wave Ripple 2D", desc: "2D circular wave interference from 4 sources — constructive/destructive ring patterns", swatch: "#334466" },
    { id: "sierpinski_tri", name: "Sierpinski (Pascal Mod 2)", desc: "Sierpinski gasket via Pascal triangle mod 2 — bitwise integer test produces deep fractal", swatch: "#335544" },
    // ── RESEARCH SESSION 6: 8 New Special Finishes (2026-03-29) ─────────────
    { id: "iridescent_fog", name: "Iridescent Fog Overlay", desc: "Semi-transparent oil-film haze overlay — warm/cool tone shift over any base without changing base character", swatch: "#aaccdd" },
    { id: "chrome_delete_edge", name: "Chrome Delete Accent Edge", desc: "Mirror-chrome edge line at zone boundaries — simulates production brightwork, A-pillar chrome, door trim strips", swatch: "#e8e8ee" },
    { id: "carbon_clearcoat_lock", name: "Carbon Clearcoat Phase-Lock", desc: "Clearcoat phase-locked to carbon weave pattern — rib tops catch more clearcoat, creating wet 3D depth in carbon panels", swatch: "#1a1a22" },
    { id: "racing_scratch", name: "Racing Scratch / Race Wear", desc: "Directional micro-scratches front-weighted — nose heaviest, tail lightest; simulates post-race directional wear", swatch: "#887766" },
    { id: "pearlescent_flip", name: "Pearlescent Flip Coat", desc: "Additive edge-weighted flop over any finish — gold secondary color hint appears at raking angles on dark base colors", swatch: "#ddeeff" },
    { id: "frost_crystal", name: "Frost / Ice Crystal Overlay", desc: "Voronoi crystal pattern — cell interiors frosted, boundaries near-zero roughness with max clearcoat sparkle", swatch: "#ccddee" },
    { id: "satin_wax", name: "Satin Wax / Concours Polish", desc: "Maximum clearcoat with large-radius buffer swirl marks — hand-waxed show car appearance", swatch: "#dde8ff" },
    { id: "uv_night_accent", name: "UV-Active Night Accent", desc: "High-specular zones barely visible in daylight but reveal as bright reflections under night race low-ambient lighting", swatch: "#442266" },
    // --- Nature-Inspired (6) ---
    { id: "nature_leaf_vein", name: "Leaf Vein", desc: "Delicate leaf venation pattern with hierarchical primary and secondary branching — natural organic texture perfect for botanical-themed liveries on pearl or satin bases", swatch: "#4a6e3a", category: "Nature-Inspired", tags: ["nature", "organic", "botanical"] },
    { id: "nature_bark_rough", name: "Bark Rough", desc: "Rough tree bark texture with deep vertical furrows and cracked ridges — weathered natural wood feel ideal for rustic or earthy builds on matte or satin bases", swatch: "#6b4a2a", category: "Nature-Inspired", tags: ["nature", "wood", "organic", "rustic"] },
    { id: "nature_water_ripple_pat", name: "Water Ripple", desc: "Calm water surface ripples with concentric wave interference and soft highlights — serene aquatic shimmer for pearl, candy, or chrome bases", swatch: "#4488aa", category: "Nature-Inspired", tags: ["nature", "water", "organic", "calm"] },
    { id: "nature_fern_fractal", name: "Fern Fractal", desc: "Self-similar Barnsley fern frond with recursive pinnate leaflet branching — elegant mathematical botanical pattern on dark or metallic bases", swatch: "#3a6e4a", category: "Nature-Inspired", tags: ["nature", "fractal", "botanical", "organic"] },
    { id: "nature_cloud_wisp", name: "Cloud Wisp", desc: "Soft cloud formations with wispy cumulus streaks and feathered edges — dreamy atmospheric texture for pearl, pastel, or sky-themed builds", swatch: "#ccd8e6", category: "Nature-Inspired", tags: ["nature", "sky", "atmospheric", "soft"] },
    { id: "nature_flame_flicker", name: "Flame Flicker", desc: "Stylized flame pattern with licking tongues of fire and ember gradients — classic hot rod flame kit on candy, chrome, or dark bases", swatch: "#e6611a", category: "Nature-Inspired", tags: ["nature", "fire", "organic", "aggressive"] },
    // --- Tribal & Cultural (6) ---
    { id: "tribal_polynesian", name: "Polynesian Tribal", desc: "Polynesian-inspired bold motifs with enata figures, shark teeth, and ocean wave bands — Pacific islander tribal art for bold masculine builds on matte or dark bases", swatch: "#2a2a2a", category: "Tribal & Cultural", tags: ["tribal", "cultural", "polynesian", "bold"] },
    { id: "tribal_norse_runes", name: "Norse Runes", desc: "Stylized Nordic elder futhark rune patterns with angular carved glyphs in repeating bands — viking warrior aesthetic for matte, brushed steel, or weathered bronze bases", swatch: "#8877aa", category: "Tribal & Cultural", tags: ["tribal", "cultural", "norse", "runic"] },
    { id: "tribal_celtic_spiral", name: "Celtic Spiral", desc: "Triple-spiral triskele Celtic pattern with flowing interwoven curved bands — ancient Gaelic heritage motif elegant on copper, bronze, or deep green metallic bases", swatch: "#668855", category: "Tribal & Cultural", tags: ["tribal", "cultural", "celtic", "spiral"] },
    { id: "tribal_aboriginal_dots", name: "Aboriginal Dots", desc: "Australian aboriginal dot painting pattern with concentric rings, dreamtime paths, and stippled clusters — earth-tone indigenous art for candy, bronze, or ochre bases", swatch: "#cc7733", category: "Tribal & Cultural", tags: ["tribal", "cultural", "aboriginal", "dots"] },
    { id: "tribal_african_kente", name: "African Kente", desc: "Geometric kente cloth pattern with bold color-block stripes, diamonds, and symbolic weave motifs — Ghanaian textile heritage stunning on gloss or satin bases", swatch: "#d4a017", category: "Tribal & Cultural", tags: ["tribal", "cultural", "african", "textile"] },
    { id: "tribal_native_diamond", name: "Native Diamond", desc: "Southwestern diamond motif with stepped geometric patterns, arrow points, and Navajo-inspired lattice bands — desert tribal art on matte, bronze, or terracotta bases", swatch: "#b8541c", category: "Tribal & Cultural", tags: ["tribal", "cultural", "native", "geometric"] },
    // --- Advanced Geometric (6) ---
    { id: "geo_penrose_tile", name: "Penrose Tiling", desc: "Non-repeating Penrose tile pattern with kite and dart rhombic shapes in aperiodic five-fold symmetry — mathematical art tiling elegant on pearl, chrome, or metallic bases", swatch: "#7788aa", category: "Advanced Geometric", tags: ["geometric", "mathematical", "aperiodic", "complex"] },
    { id: "geo_truchet_curves", name: "Truchet Curves", desc: "Truchet tile curve patterns with randomly oriented quarter-arc segments forming flowing interconnected paths — generative algorithmic art on gloss or matte bases", swatch: "#446688", category: "Advanced Geometric", tags: ["geometric", "mathematical", "generative", "curves"] },
    { id: "geo_islamic_star", name: "Islamic Star", desc: "Ten-point Islamic geometric star pattern with interlocking polygonal tiles and classical Moorish tessellation — ornate sacred geometry stunning on gold, copper, or deep blue bases", swatch: "#b8923c", category: "Advanced Geometric", tags: ["geometric", "islamic", "cultural", "ornate"] },
    { id: "geo_voronoi_organic", name: "Voronoi Organic", desc: "Organic Voronoi cells with irregular polygonal regions derived from randomized seed point tessellation — cellular biological texture ideal on pearl, candy, or metallic bases", swatch: "#667799", category: "Advanced Geometric", tags: ["geometric", "organic", "cellular", "mathematical"] },
    { id: "geo_fractal_triangle", name: "Sierpinski Triangle", desc: "Sierpinski fractal triangle with recursive self-similar triangular subdivisions revealing infinite nested detail — mathematical fractal art on dark, chrome, or neon bases", swatch: "#cc3355", category: "Advanced Geometric", tags: ["geometric", "fractal", "mathematical", "recursive"] },
    { id: "geo_hilbert_curve", name: "Hilbert Curve", desc: "Space-filling Hilbert curve with continuous fractal path weaving through every grid cell in recursive u-shaped segments — algorithmic elegance on matte, chrome, or dark bases", swatch: "#3388cc", category: "Advanced Geometric", tags: ["geometric", "fractal", "mathematical", "curve"] },
];;

// =============================================================================
// PATTERN METADATA - Structured tags for smart combo recommendations
// style: visual category (geometric, organic, flame, industrial, texture, effect, racing, cultural)
// density: how much of the canvas the pattern fills (sparse, medium, dense, full)
// aggression: visual intensity 1-5
// best_bases: array of base families this pattern works best with
// readability: how well sponsor text reads over this pattern (good, fair, poor)
// =============================================================================
const PATTERN_METADATA = {
    // === GEOMETRIC ===
    carbon_fiber:      { style: "geometric", density: "full", aggression: 2, best_bases: ["chrome", "matte", "candy", "metallic", "satin"], readability: "good" },
    hex_mesh:          { style: "geometric", density: "full", aggression: 3, best_bases: ["chrome", "matte", "cerakote", "blackout"], readability: "fair" },
    diamond_plate:     { style: "geometric", density: "full", aggression: 3, best_bases: ["matte", "metallic", "brushed"], readability: "fair" },
    houndstooth:       { style: "geometric", density: "full", aggression: 2, best_bases: ["gloss", "satin", "pearl"], readability: "good" },
    argyle:            { style: "geometric", density: "full", aggression: 2, best_bases: ["gloss", "satin", "pearl"], readability: "good" },
    plaid:             { style: "geometric", density: "full", aggression: 2, best_bases: ["matte", "satin"], readability: "good" },
    // === EFFECT ===
    holographic_flake: { style: "effect", density: "full", aggression: 4, best_bases: ["candy", "pearl", "metallic", "frozen"], readability: "fair" },
    stardust:          { style: "effect", density: "sparse", aggression: 3, best_bases: ["candy", "chrome", "pearl", "vantablack"], readability: "good" },
    metal_flake:       { style: "effect", density: "full", aggression: 3, best_bases: ["metallic", "candy", "gloss"], readability: "good" },
    interference:      { style: "effect", density: "full", aggression: 3, best_bases: ["pearl", "chameleon", "frozen"], readability: "fair" },
    lightning:         { style: "effect", density: "sparse", aggression: 4, best_bases: ["chrome", "candy", "vantablack", "electric_ice"], readability: "poor" },
    plasma:            { style: "effect", density: "medium", aggression: 4, best_bases: ["chrome", "vantablack", "candy"], readability: "poor" },
    hologram:          { style: "effect", density: "full", aggression: 3, best_bases: ["chrome", "metallic"], readability: "fair" },
    // === FLAME ===
    tribal_flame:      { style: "flame", density: "medium", aggression: 5, best_bases: ["candy", "metallic", "chrome"], readability: "poor" },
    // === INDUSTRIAL ===
    circuit_board:     { style: "industrial", density: "medium", aggression: 2, best_bases: ["metallic", "matte", "cerakote"], readability: "fair" },
    rivet_plate:       { style: "industrial", density: "full", aggression: 3, best_bases: ["metallic", "matte", "brushed"], readability: "fair" },
    gear_mesh:         { style: "industrial", density: "full", aggression: 3, best_bases: ["metallic", "chrome", "matte"], readability: "fair" },
    // === RACING ===
    ekg:               { style: "racing", density: "medium", aggression: 3, best_bases: ["chrome", "candy", "matte", "blackout"], readability: "fair" },
    racing_stripe:     { style: "racing", density: "sparse", aggression: 2, best_bases: ["gloss", "metallic", "matte"], readability: "good" },
    checkered_flag:    { style: "racing", density: "full", aggression: 3, best_bases: ["gloss", "chrome"], readability: "fair" },
    // === TEXTURE ===
    battle_worn:       { style: "texture", density: "full", aggression: 3, best_bases: ["matte", "metallic", "satin"], readability: "fair" },
    acid_wash:         { style: "texture", density: "full", aggression: 3, best_bases: ["matte", "weathered"], readability: "fair" },
    cracked_ice:       { style: "texture", density: "full", aggression: 3, best_bases: ["frozen", "chrome", "pearl"], readability: "fair" },
    rust_bloom:        { style: "texture", density: "full", aggression: 4, best_bases: ["weathered", "matte"], readability: "poor" },
    // === ORGANIC ===
    topographic:       { style: "organic", density: "full", aggression: 2, best_bases: ["matte", "satin", "metallic"], readability: "fair" },
    skull:             { style: "organic", density: "medium", aggression: 4, best_bases: ["matte", "blackout", "chrome"], readability: "poor" },
    celtic_knot:       { style: "cultural", density: "full", aggression: 2, best_bases: ["copper", "metallic", "matte"], readability: "fair" },
};

// Helper: get pattern metadata
function getPatternMetadata(patternId) {
    return PATTERN_METADATA[patternId] || {};
}

// Helper: check if base+pattern is a recommended combo based on metadata
function isRecommendedCombo(baseId, patternId) {
    var baseMeta = (typeof getBaseMetadata === 'function') ? getBaseMetadata(baseId) : {};
    var patMeta = PATTERN_METADATA[patternId] || {};
    // Check if pattern recommends this base family
    if (patMeta.best_bases && baseMeta.family && patMeta.best_bases.indexOf(baseMeta.family) >= 0) return true;
    // Check if base recommends this pattern
    if (baseMeta.best_with && baseMeta.best_with.indexOf(patternId) >= 0) return true;
    return false;
}

// Removed 2026-03: Color Shift Adaptive/Duo/Preset, Luxury & Exotic, Novelty & Fun, Racing Legend, Surreal & Fantasy, Texture & Surface, Vintage & Retro
const REMOVED_SPECIAL_IDS = new Set([
    "cs_chrome_shift", "cs_complementary", "cs_cool", "cs_earth", "cs_extreme", "cs_monochrome", "cs_neon_shift", "cs_ocean_shift", "cs_prism_shift", "cs_rainbow", "cs_split", "cs_subtle", "cs_triadic", "cs_vivid", "cs_warm",
    "cs_black_red", "cs_blue_orange", "cs_bronze_green", "cs_bronze_navy", "cs_copper_teal", "cs_copper_violet", "cs_emerald", "cs_fire_ice", "cs_gold_emerald", "cs_green_gold", "cs_gunmetal_orange", "cs_lime_blue", "cs_magenta_gold", "cs_navy_gold", "cs_navy_silver", "cs_neon_dreams", "cs_pink_purple", "cs_pink_teal", "cs_purple_lime", "cs_red_black", "cs_red_gold", "cs_silver_purple", "cs_sunset_ocean", "cs_teal_pink", "cs_twilight", "cs_violet_teal", "cs_white_blue", "cs_yellow_blue",
    "cs_candy_paint", "cs_dark_flame", "cs_deepocean", "cs_gold_rush", "cs_inferno", "cs_mystichrome", "cs_nebula", "cs_oilslick", "cs_rose_gold_shift", "cs_solarflare", "cs_supernova", "cs_toxic",
    "alexandrite", "black_diamond", "champagne_toast", "galaxy", "liquid_gold", "mother_of_pearl", "ruby", "sapphire", "silk_road", "stained_glass", "velvet_crush", "venetian_glass",
    "aged_leather", "bark", "bone", "brick_wall", "burlap", "cork", "crocodile_leather", "linen", "parchment", "petrified_wood", "stucco", "suede", "terra_cotta",
    "black_flag", "burnout_zone", "chicane_blur", "cool_down", "dawn_patrol", "drafting", "drag_chute", "flag_wave", "green_flag", "grid_walk", "heat_haze", "last_lap", "night_race", "pace_lap", "photo_finish", "pit_stop", "pole_position", "race_worn", "rain_race", "red_mist", "slipstream", "tunnel_run", "under_lights", "victory_burnout", "white_flag",
    "acid_trip", "antimatter", "astral", "crystal_cave", "dark_fairy", "dragon_breath", "dreamscape", "enchanted", "ethereal", "fourth_dimension", "fractal_dimension", "glitch_reality", "hallucination", "levitation", "mirage", "multiverse", "nebula_core", "phantom_zone", "portal", "simulation", "tesseract", "time_warp", "void_walker", "wormhole",
    "acid_etched_glass", "brushed_steel_dark", "cast_iron", "concrete", "etched_metal", "forged_iron", "granite", "hammered_copper", "obsidian_glass", "sandstone", "slate_tile", "volcanic_rock",
    "art_deco_gold", "barn_find", "beat_up_truck", "classic_racing", "daguerreotype", "diner_chrome", "drive_in", "faded_glory", "grindhouse", "hot_rod_flames", "jukebox", "moonshine", "muscle_car_stripe", "nascar_heritage", "nostalgia_drag", "old_school", "patina_truck", "pin_up", "psychedelic", "sepia", "tin_type", "vinyl_record", "woodie", "woodie_wagon", "zeppelin"
]);

// =============================================================================
// SPECIALS / MONOLITHICS - Single source of truth (picker + server)
// Structure: subsection objects merged into SPECIAL_GROUPS; SPECIALS_SECTION_ORDER
// and SPECIALS_SECTIONS give the app logical categories for UI grouping.
// =============================================================================

// =============================================================================
// SHOKKER — Reimagined Monolithic Taxonomy (628 finishes)
// Single source: only backend-registered IDs. No filler. The benchmark.
// =============================================================================

const _SPECIALS_SHOKKER = {
    // 2026-04-19 HEENAN H4HR-3: crystal_lattice MONO renamed → crystal_lattice_mono
    // (PATTERN tier kept the canonical id). gravity_well MONO is unchanged here
    // (SPEC tier is the one getting renamed in H4HR-5 below — see SPEC_PATTERN_GROUPS).
    "PARADIGM": ["blackbody", "ember", "p_aurora", "pulse", "thin_film", "crystal_lattice_mono", "living_chrome", "mercury_pool", "quantum", "singularity", "gravity_well", "phase_shift", "void", "wormhole", "glass_armor", "magnetic", "p_static", "stealth", "p_superfluid", "p_coronal", "p_seismic", "p_hypercane", "p_geomagnetic", "p_non_euclidean", "p_time_reversed", "p_programmable", "p_erised", "p_schrodinger", "p_mercury", "p_phantom", "p_volcanic", "arctic_ice", "nebula", "quantum_foam", "infinite_finish"],
    "★ COLORSHOXX": ["cx_inferno", "cx_arctic", "cx_venom", "cx_solar", "cx_phantom", "cx_chrome_void", "cx_blood_mercury", "cx_neon_abyss", "cx_glacier_fire", "cx_obsidian_gold", "cx_electric_storm", "cx_rose_chrome", "cx_toxic_chrome", "cx_midnight_chrome", "cx_white_lightning", "cx_aurora_borealis", "cx_dragon_scale", "cx_frozen_nebula", "cx_hellfire", "cx_ocean_trench", "cx_supernova", "cx_prism_shatter", "cx_acid_rain", "cx_royal_spectrum", "cx_apocalypse", "cx_gold_green", "cx_gold_purple", "cx_teal_blue", "cx_copper_rose", "cx_gold_olive_emerald", "cx_purple_plum_bronze", "cx_blue_teal_cyan", "cx_burgundy_wine_gold", "cx_sunset_horizon", "cx_northern_lights", "cx_peacock_fan", "cx_rainbow_stealth", "cx_oil_slick", "cx_molten_metal", "cx_red_green_chaos", "cx_orange_blue_electric", "cx_pink_yellow_pop", "cx_purple_gold_majesty", "cx_custom_shift", "cx_pink_to_gold", "cx_blue_to_orange", "cx_purple_to_green", "cx_teal_to_magenta", "cx_red_to_cyan", "cx_sunset_shift", "cx_emerald_ruby", "cx_ice_fire", "cx_hyperflip_red_blue", "cx_hyperflip_pink_black", "cx_hyperflip_orange_cyan", "cx_hyperflip_lime_purple", "cx_hyperflip_purple_gold", "cx_hyperflip_electric_blue_copper", "cx_hyperflip_bronze_teal", "cx_hyperflip_silver_violet", "cx_hyperflip_crimson_prism", "cx_hyperflip_midnight_opal", "cx_cotton_candy", "cx_forest_fire", "cx_deep_sea", "cx_galaxy_dust", "cx_autumn_blaze", "cx_thunderstorm", "cx_tropical_sunset", "cx_black_ice", "cx_cherry_blossom", "cx_volcanic_glass", "cx_neon_dreams", "cx_champagne_toast", "cx_emerald_city", "cx_midnight_aurora", "cx_bronze_age"],
    "★ MORTAL SHOKK": ["ms_frozen_fury", "ms_venom_strike", "ms_thunder_lord", "ms_chrome_cage", "ms_dragon_flame", "ms_royal_edge", "ms_feral_grin", "ms_acid_scale", "ms_soul_drain", "ms_emerald_shadow", "ms_void_walker", "ms_ghost_vapor", "ms_shape_shift", "ms_titan_bronze", "ms_war_hammer"],
    "Shokk Series": ["burnt_headers", "electric_ice", "mercury", "plasma_metal", "shokk_blood", "shokk_pulse", "shokk_static", "shokk_venom", "shokk_void", "volcanic", "shokk_flux", "shokk_phase", "shokk_dual", "shokk_spectrum", "shokk_aurora", "shokk_helix", "shokk_catalyst", "shokk_mirage", "shokk_polarity", "shokk_reactor", "shokk_prism", "shokk_wraith", "shokk_tesseract_v2", "shokk_fusion_base", "shokk_rift", "shokk_vortex", "shokk_surge", "shokk_cipher", "shokk_inferno", "shokk_apex"],
    // 2026-04-23 Codex finish-taxonomy hardening:
    // keep shipping special ids in ONE canonical category only.
    // Angle SHOKK is now reserved for the true angle-read entries instead of
    // duplicating PARADIGM / Shokk Series / Extreme finishes.
    "Angle SHOKK": ["chameleon", "color_flip_wrap", "pagani_tricolore"],
    "Extreme & Experimental": ["bioluminescent", "dark_matter", "holographic_base", "neutron_star", "plasma_core", "quantum_black", "solar_panel", "superconductor", "prismatic", "liquid_obsidian", "vantablack"],
    "★ NEON UNDERGROUND": ["neon_pink_blaze", "neon_toxic_green", "neon_electric_blue", "neon_blacklight", "neon_orange_hazard", "neon_red_alert", "neon_cyber_yellow", "neon_ice_white", "neon_dual_glow", "neon_rainbow_tube"],
};

const _SPECIALS_COLOR_SCIENCE = {
    "Chameleon": ["chameleon_amethyst", "chameleon_arctic", "chameleon_aurora", "chameleon_copper", "chameleon_emerald", "chameleon_fire", "chameleon_frost", "chameleon_galaxy", "chameleon_midnight", "chameleon_neon", "chameleon_obsidian", "chameleon_ocean", "chameleon_phoenix", "chameleon_venom", "mystichrome"],
    "Prizm": ["prizm_adaptive", "prizm_alien_skin", "prizm_arctic", "prizm_aurora_shift", "prizm_black_rainbow", "prizm_blood_moon", "prizm_candy_paint", "prizm_chrome_rose", "prizm_copper_flame", "prizm_cosmos", "prizm_dark_matter", "prizm_deep_space", "prizm_duochrome", "prizm_ember", "prizm_fire_ice", "prizm_galaxy_dust", "prizm_holographic", "prizm_iridescent", "prizm_midnight", "prizm_mystichrome", "prizm_neon", "prizm_oceanic", "prizm_phoenix", "prizm_solar", "prizm_spectrum", "prizm_sunset_strip", "prizm_titanium", "prizm_toxic_waste", "prizm_venom"],
    "Aurora & Chromatic Flow": ["aurora_borealis", "aurora_solar_wind", "aurora_nebula", "aurora_chromatic_surge", "aurora_frozen_flame", "aurora_deep_ocean", "aurora_volcanic", "aurora_ethereal", "aurora_toxic_current", "aurora_midnight_silk", "aurora_electric_candy", "aurora_ocean_phosphor", "aurora_molten_earth", "aurora_arctic_shimmer", "aurora_neon_storm", "aurora_twilight_veil", "aurora_dragon_fire", "aurora_crystal_prism", "aurora_shadow_silk", "aurora_copper_patina", "aurora_poison_ivy", "aurora_champagne_dream", "aurora_thunderhead", "aurora_coral_reef", "aurora_black_rainbow", "aurora_cherry_blossom", "aurora_plasma_reactor", "aurora_autumn_ember", "aurora_ice_crystal", "aurora_supernova"],
    "Color-Shift Adaptive": ["cs_cool", "cs_warm", "cs_complementary", "cs_monochrome", "cs_subtle", "cs_rainbow", "cs_vivid", "cs_extreme", "cs_triadic", "cs_split", "cs_neon_shift", "cs_ocean_shift", "cs_chrome_shift", "cs_earth", "cs_prism_shift"],
    "Color-Shift Presets": ["cs_deepocean", "cs_solarflare", "cs_inferno", "cs_nebula", "cs_mystichrome", "cs_supernova", "cs_emerald", "cs_candypaint", "cs_oilslick", "cs_rose_gold_shift", "cs_goldrush", "cs_toxic", "cs_darkflame", "cs_rosegold", "cs_twilight", "cs_neon_dreams"],
    "Color-Shift Duos": ["cs_amber_indigo", "cs_aqua_maroon", "cs_black_blue", "cs_black_gold", "cs_black_red", "cs_black_silver", "cs_blue_orange", "cs_blush_emerald", "cs_bronze_green", "cs_bronze_navy", "cs_bronze_purple", "cs_bronze_red", "cs_burgundy_gold", "cs_candy_paint", "cs_champagne_cobalt", "cs_charcoal_honey", "cs_chocolate_mint", "cs_copper_blue", "cs_copper_gold", "cs_copper_lime", "cs_copper_teal", "cs_copper_violet", "cs_coral_cobalt", "cs_crimson_jade", "cs_dark_flame", "cs_fire_ice", "cs_gold_emerald", "cs_gold_navy", "cs_gold_rush", "cs_graphite_coral", "cs_green_blue", "cs_green_gold", "cs_gunmetal_gold", "cs_gunmetal_lime", "cs_gunmetal_orange", "cs_honey_plum", "cs_ivory_indigo", "cs_lavender_jade", "cs_lime_blue", "cs_lime_pink", "cs_lime_violet", "cs_magenta_blue", "cs_magenta_gold", "cs_magenta_teal", "cs_mint_maroon", "cs_navy_gold", "cs_navy_orange", "cs_navy_silver", "cs_orange_navy", "cs_orange_purple", "cs_peach_cobalt", "cs_pewter_rose", "cs_pink_gold", "cs_pink_purple", "cs_pink_teal", "cs_purple_gold", "cs_purple_lime", "cs_red_black", "cs_red_gold", "cs_red_purple", "cs_rose_emerald", "cs_sage_crimson", "cs_silver_purple", "cs_silver_red", "cs_silver_teal", "cs_sky_gold", "cs_slate_amber", "cs_sunset_ocean", "cs_teal_orange", "cs_teal_pink", "cs_titanium_crimson", "cs_violet_gold", "cs_violet_teal", "cs_white_blue", "cs_white_green", "cs_white_purple", "cs_white_red", "cs_yellow_blue"],
    "Gradient Directional": ["grad_arctic_dawn", "grad_bruise", "grad_copper_patina", "grad_fire_fade", "grad_fire_fade_diag", "grad_fire_fade_h", "grad_forest_canopy", "grad_golden_hour", "grad_golden_hour_h", "grad_ice_fire", "grad_lava_flow", "grad_midnight_ember", "grad_neon_rush", "grad_neon_rush_h", "grad_ocean_depths", "grad_ocean_depths_diag", "grad_ocean_depths_h", "grad_steel_forge", "grad_sunset", "grad_sunset_diag", "grad_toxic_waste", "grad_twilight", "grad_twilight_diag", "grad_twilight_h"],
    "Gradient Vortex": ["grad_blue_vortex", "grad_copper_vortex", "grad_fire_vortex", "grad_gold_vortex", "grad_green_vortex", "grad_pink_vortex", "grad_shadow_vortex", "grad_teal_vortex", "grad_violet_vortex", "grad_white_vortex"],
    "Chromatic Flake": ["cf_midnight_galaxy", "cf_volcanic_ember", "cf_arctic_aurora", "cf_black_opal", "cf_dragon_scale", "cf_toxic_nebula", "cf_rose_gold_dust", "cf_deep_space", "cf_phoenix_feather", "cf_frozen_mercury", "cf_jungle_venom", "cf_cobalt_storm", "cf_sunset_strip", "cf_absinthe_dreams", "cf_titanium_rain", "cf_blood_moon", "cf_peacock_strut", "cf_champagne_frost", "cf_neon_viper", "cf_obsidian_fire", "cf_mermaid_scale", "cf_carbon_prizm", "cf_molten_copper", "cf_electric_storm", "cf_desert_mirage", "cf_venom_strike", "cf_sapphire_ice", "cf_inferno_chrome", "cf_phantom_violet", "cf_solar_flare"],
    "Color Clash": ["cc_acid_burn", "cc_blood_orange", "cc_bruised_sky", "cc_candy_poison", "cc_chaos_theory", "cc_chemical_spill", "cc_coral_venom", "cc_deep_friction", "cc_digital_rot", "cc_electric_conflict", "cc_fever_dream", "cc_flash_burn", "cc_magma_freeze", "cc_neon_bruise", "cc_neon_war", "cc_nuclear_dawn", "cc_plasma_edge", "cc_punk_static", "cc_radioactive", "cc_rust_vs_ice", "cc_solar_clash", "cc_toxic_sunset", "cc_ultraviolet_burn", "cc_venom_strike", "cc_voltage_split"],
    "Gradient Extended": ["grad_black_gold", "grad_patriot", "grad_frostbite", "grad_neon_violet", "grad_aqua_drift", "grad_iron_blood", "grad_emerald_crown", "grad_candy_cane", "grad_chrome_wave", "grad_copper_flame", "grad_storm_front", "grad_ultraviolet", "grad_antique_gold", "grad_obsidian", "grad_electric_lime", "grad_magma", "grad_sapphire_ice", "grad_rose_gold", "grad_forest_night", "grad_solar_flare", "grad_black_gold_h", "grad_patriot_h", "grad_candy_cane_h", "grad_magma_h", "grad_rose_gold_h", "grad_black_gold_diag", "grad_neon_violet_diag", "grad_storm_front_diag", "grad_emerald_crown_diag", "grad_patriot_vortex", "grad_neon_violet_vortex", "grad_obsidian_vortex", "grad_rose_gold_vortex", "grad_solar_vortex", "grad_wine_silk", "grad_midnight_gold", "grad_coral_sea", "grad_ember_ash", "grad_jade_mist", "grad_plum_dawn", "grad_amber_night", "grad_sage_bronze", "grad_titanium_fire", "grad_ivory_cobalt", "grad_honey_slate", "grad_rose_midnight", "grad_charcoal_gold", "grad_lavender_dusk", "grad_emerald_night", "grad_cream_crimson", "grad_blush_cobalt", "grad_graphite_amber", "grad_mint_purple", "grad_champagne_navy", "grad_pewter_rose", "grad_chocolate_gold", "grad_crimson_vortex", "grad_coral_vortex", "grad_amber_vortex", "grad_honey_vortex", "grad_emerald_vortex", "grad_jade_vortex", "grad_aqua_vortex", "grad_cerulean_vortex", "grad_cobalt_vortex", "grad_indigo_vortex", "grad_lavender_vortex", "grad_plum_vortex", "grad_rose_vortex", "grad_blush_vortex", "grad_maroon_vortex", "grad_burgundy_vortex", "grad_chocolate_vortex", "grad_tan_vortex", "grad_cream_vortex", "grad_ivory_vortex", "grad_slate_vortex", "grad_charcoal_vortex", "grad_graphite_vortex", "grad_pewter_vortex", "grad_champagne_vortex", "grad_titanium_vortex", "grad_mint_vortex", "grad_sage_vortex", "grad_chartreuse_vortex", "grad_peach_vortex", "grad_ruby_vortex", "grad_sapphire_vortex", "grad_topaz_vortex", "grad_amethyst_vortex", "grad_opal_vortex"],
};

const _SPECIALS_MATERIAL_WORLD = {
    "Atelier — Ultra Detail": ["atelier_brushed_titanium", "atelier_carbon_weave_micro", "atelier_cathedral_glass", "atelier_ceramic_glaze", "atelier_damascus_layers", "atelier_engine_turned", "atelier_fluid_metal", "atelier_forged_iron_texture", "atelier_gold_leaf_micro", "atelier_hand_brushed_metal", "atelier_japanese_lacquer", "atelier_marble_vein_fine", "atelier_micro_flake_burst", "atelier_obsidian_glass", "atelier_pearl_depth_layers", "atelier_silk_weave", "atelier_vintage_enamel_crackle"],
    "Metals & Forged": ["forged_iron", "cast_iron", "hammered_copper", "brushed_steel_dark", "etched_metal", "bare_aluminum", "chrome_oxidized", "heat_blued", "oxidized_metal", "mill_scale", "weathered_metal", "carbon_raw", "weathered_paint", "worn_chrome", "phosphate_coat", "raw_weld", "grinding_marks", "forged_titanium", "brushed_gunmetal", "cast_iron_raw", "polished_brass", "annealed_steel", "oxidized_bronze", "damascus_steel"],
    "Glass & Surface": ["obsidian_glass", "stained_glass", "venetian_glass", "acid_etched_glass", "concrete", "granite", "raw_concrete", "sandstone", "slate_tile", "stucco", "terra_cotta", "volcanic_rock", "brick_wall"],
    "Leather & Texture": ["aged_leather", "crocodile_leather", "suede", "velvet", "velvet_crush", "linen", "burlap", "cork", "parchment", "bark", "petrified_wood"],
    "Standalone Effects": ["thermal_titanium", "galaxy_nebula_base", "dark_sigil", "deep_space_void", "polished_obsidian_mono", "patinated_bronze", "reactive_plasma", "molten_metal", "oil_slick_base", "aurora_borealis_mono"],
    "Brushed & Machined": ["brushed_linear", "brushed_diagonal", "brushed_cross", "brushed_radial", "brushed_arc", "brushed_sparkle", "brushed_metal_fine", "hairline_polish", "lathe_concentric", "bead_blast_uniform", "orbital_swirl", "buffer_swirl", "wire_brushed_coarse", "hand_polished", "face_mill_bands", "fly_cut_arcs", "edm_dimple", "jeweling_circles", "knurl_diamond", "knurl_straight", "engraved_crosshatch", "guilloche_barleycorn", "guilloche_hobnail", "guilloche_moire_eng", "guilloche_sunray", "guilloche_waves"],
    "Clearcoat Effects": ["cc_drip_runs", "cc_edge_thin", "cc_fish_eye", "cc_gloss_stripe", "cc_masking_edge", "cc_overspray_halo", "cc_panel_fade", "cc_panel_pool", "cc_spot_polish", "cc_wet_zone"],
    "Ornamental": ["hex_mandala", "lace_filigree", "honeycomb_organic", "baroque_scrollwork", "art_nouveau_vine", "penrose_quasi", "topographic_dense", "interference_rings"],
    // 2026-04-23 Codex painter-truth cleanup:
    // retire Carbon & Weave from the shipping special-monolithic surface.
    // The only visibly reachable monolithics here ("carbon_3k_weave" and
    // "carbon_weave") were explicitly painter-rejected, and the spec_* ids
    // never belonged in this monolithic/base picker path to begin with.
    "Natural & Organic": ["spec_wood_grain_fine", "spec_wood_burl", "spec_stone_granite", "spec_stone_marble", "spec_water_ripple_spec", "spec_coral_reef", "spec_snake_scales", "spec_fish_scales", "spec_leaf_venation", "spec_terrain_erosion", "spec_crystal_growth", "spec_lava_flow", "marble_vein", "cloud_wisps", "sand_dune", "crystal_growth", "reptile_scale", "fungal_network", "neural_dendrite"],
    "Surface Treatment": ["spec_electroplated_chrome", "spec_anodized_texture", "spec_powder_coat_texture", "spec_thermal_spray", "spec_electroformed_texture", "spec_pvd_coating", "spec_shot_peened", "spec_laser_etched", "spec_cast_surface", "spec_oxidized_pitting", "spec_micro_chips", "spec_aged_matte", "spec_patina_verdigris", "spec_rust_bloom", "spec_galvanic_corrosion", "spec_peeling_clear", "spec_worn_edges", "spec_sandblast_strip", "spec_battle_scars", "spec_stress_fractures", "spec_heat_scale"],
    "Geometric & Structural": ["spec_faceted_diamond", "spec_hammered_dimple", "spec_knurled_diamond", "spec_knurled_straight", "spec_architectural_grid", "spec_hexagonal_tiles", "spec_brick_mortar", "spec_corrugated_panel", "spec_riveted_plate", "spec_weld_seam", "spec_stamped_emboss", "panel_zones", "hex_cells", "diamond_lattice", "woven_mesh"],
    "Optical & Light": ["spec_holographic_foil", "spec_oil_film_thick", "spec_magnetic_ferrofluid", "spec_aerogel_surface", "spec_damascus_steel_spec", "spec_liquid_metal", "spec_chameleon_flake", "spec_xirallic_crystal", "spec_iridescent_film", "spec_diffraction_grating", "spec_chromatic_aberration", "spec_fresnel_gradient", "spec_caustic_light", "spec_light_leak", "spec_subsurface_depth", "spec_retroreflective", "spec_velvet_sheen", "spec_bokeh_scatter", "spec_sparkle_flake", "spec_anisotropic_radial", "diffraction_grating", "interference_bands", "heat_distortion", "holographic_flake", "prismatic_dust", "prismatic_shatter"],
    "Particles & Textures": ["crystal_shimmer", "diamond_dust", "flake_scatter", "gold_flake", "metallic_sand", "micro_sparkle", "pearl_micro", "stardust_fine", "crushed_glass"],
    "Patterns & Effects": ["acid_etch", "aniso_grain", "banded_rows", "chevron_bands", "circuit_trace", "concentric_ripple", "crackle_network", "depth_gradient", "diagonal_bands", "electric_branches", "flow_lines", "fractal_discharge", "galaxy_swirl", "gradient_bands", "lava_crack", "magnetic_field", "meteor_impact", "micro_facets", "moire_overlay", "orange_peel_texture", "patina_bloom", "pebble_grain", "plasma_turbulence", "quantum_noise", "radial_sunburst", "rust_bloom", "smoke_tendril", "sonic_boom", "spiral_sweep", "split_bands", "topographic_steps", "voronoi_fracture", "wave_bands", "wave_ripple", "wear_scuff"],
};

const _SPECIALS_FUSION_LAB = {
    "Ghost Geometry": ["ghost_camo", "ghost_circuit", "ghost_diamonds", "ghost_fracture", "ghost_hex", "ghost_panel", "ghost_quilt", "ghost_scales", "ghost_stripes", "ghost_vortex", "ghost_waves"],
    "Surface Accent": ["iridescent_fog", "chrome_delete_edge", "carbon_clearcoat_lock", "racing_scratch", "pearlescent_flip", "frost_crystal", "satin_wax", "uv_night_accent"],
    "Depth Illusion": ["depth_bubble", "depth_canyon", "depth_crack", "depth_erosion", "depth_honeycomb", "depth_map", "depth_pillow", "depth_ripple", "depth_scale", "depth_vortex", "depth_wave"],
    "Material Gradients": ["gradient_anodized_gloss", "gradient_candy_frozen", "gradient_candy_matte", "gradient_carbon_chrome", "gradient_chrome_matte", "gradient_ember_ice", "gradient_metallic_satin", "gradient_obsidian_mirror", "gradient_pearl_chrome", "gradient_spectraflame_void"],
    "Directional Grain": ["aniso_circular_chrome", "aniso_crosshatch_steel", "aniso_diagonal_candy", "aniso_herringbone_gold", "aniso_horizontal_chrome", "aniso_radial_metallic", "aniso_spiral_mercury", "aniso_turbulence_metal", "aniso_vertical_pearl", "aniso_wave_titanium"],
    "Reactive Panels": ["reactive_candy_reveal", "reactive_chrome_fade", "reactive_dual_tone", "reactive_ghost_metal", "reactive_matte_shine", "reactive_mirror_shadow", "reactive_pearl_flash", "reactive_pulse_metal", "reactive_stealth_pop", "reactive_warm_cold"],
    "Sparkle Systems": ["sparkle_champagne", "sparkle_confetti", "sparkle_constellation", "sparkle_diamond_dust", "sparkle_firefly", "sparkle_galaxy", "sparkle_lightning_bug", "sparkle_meteor", "sparkle_snowfall", "sparkle_starfield"],
    "Multi-Scale Texture": ["multiscale_candy_frost", "multiscale_carbon_micro", "multiscale_chrome_grain", "multiscale_chrome_sand", "multiscale_flake_grain", "multiscale_frost_crystal", "multiscale_matte_silk", "multiscale_metal_grit", "multiscale_pearl_texture", "multiscale_satin_weave"],
    "Weather & Age": ["weather_acid_rain", "weather_barn_dust", "weather_desert_blast", "weather_hood_bake", "weather_ice_storm", "weather_ocean_mist", "weather_road_spray", "weather_salt_spray", "weather_sun_fade", "weather_volcanic_ash"],
    "Exotic Physics": ["exotic_anti_metal", "exotic_ceramic_void", "exotic_crystal_clear", "exotic_dark_glass", "exotic_foggy_chrome", "exotic_glass_paint", "exotic_inverted_candy", "exotic_liquid_glass", "exotic_phantom_mirror", "exotic_wet_void"],
    "Tri-Zone Materials": ["trizone_anodized_candy_silk", "trizone_ceramic_flake_satin", "trizone_chrome_candy_matte", "trizone_frozen_ember_chrome", "trizone_glass_metal_matte", "trizone_mercury_obsidian_candy", "trizone_pearl_carbon_gold", "trizone_stealth_spectra_frozen", "trizone_titanium_copper_chrome", "trizone_vanta_chrome_pearl"],
    "Metallic Halos": ["halo_circle_pearl", "halo_crack_chrome", "halo_diamond_chrome", "halo_grid_pearl", "halo_hex_chrome", "halo_ripple_chrome", "halo_scale_gold", "halo_star_metal", "halo_voronoi_metal", "halo_wave_candy"],
    "Light Waves": ["wave_candy_flow", "wave_chrome_tide", "wave_circular_radar", "wave_diagonal_sweep", "wave_dual_frequency", "wave_metallic_pulse", "wave_moire_metal", "wave_pearl_current", "wave_standing_chrome", "wave_turbulent_flow"],
    "Fractal Chaos": ["fractal_candy_chaos", "fractal_chrome_decay", "fractal_cosmic_dust", "fractal_deep_organic", "fractal_dimension", "fractal_electric_noise", "fractal_liquid_fire", "fractal_matte_chrome", "fractal_metallic_storm", "fractal_pearl_cloud", "fractal_warm_cold"],
    "Spectral Reactive": ["spectral_complementary", "spectral_dark_light", "spectral_earth_sky", "spectral_inverse_logic", "spectral_mono_chrome", "spectral_neon_reactive", "spectral_prismatic_flip", "spectral_rainbow_metal", "spectral_sat_metal", "spectral_warm_cool"],
    "Panel Quilting": ["quilt_alternating_duo", "quilt_candy_tiles", "quilt_chrome_mosaic", "quilt_diamond_shimmer", "quilt_gradient_tiles", "quilt_hex_variety", "quilt_metallic_pixels", "quilt_organic_cells", "quilt_pearl_patchwork", "quilt_random_chaos"],
};

// NOTE (2026-04-17): _SPECIALS_RACING_HERITAGE intentionally EMPTY.
// Racing Heritage lives exclusively in BASE_GROUPS.Racing Heritage now; the
// Specials duplicate was scrubbed per user request.
const _SPECIALS_RACING_HERITAGE = {};

const _SPECIALS_ATMOSPHERE = {
    "Atmosphere": ["acid_rain", "black_ice", "blizzard", "desert_mirage", "dew_drop", "dust_storm", "ember_glow", "fog_bank", "frost_bite", "frozen_lake", "hail_damage", "heat_wave", "hurricane", "lightning_strike", "liquid_metal", "magma_flow", "meteor_shower", "monsoon", "ocean_floor", "oil_slick", "permafrost", "solar_wind", "tidal_wave", "tornado_alley", "volcanic_glass"],
};

const _SPECIALS_SIGNAL = {
    "Signal": ["aurora_glow", "bioluminescent_wave", "blacklight_paint", "cyber_punk", "electric_arc", "firefly", "fluorescent", "glow_stick", "laser_grid", "laser_show", "led_matrix", "magnesium_burn", "neon_glow", "neon_sign", "neon_vegas", "phosphorescent", "plasma_globe", "radioactive", "rave", "scorched", "sodium_lamp", "static", "tesla_coil", "tracer_round", "welding_arc"],
};

// NOTE (2026-04-17): _SPECIALS_MULTI_SPECTRUM intentionally EMPTY.
// All 25 Multi-Spectrum finishes (Multi Swirl/Camo/Marble/Splatter) were
// scrubbed from the Specials picker per user request.
const _SPECIALS_MULTI_SPECTRUM = {};

const _SPECIALS_ANIME_INSPIRED = {
    "★ ANIME INSPIRED": ["anime_cel_shade_chrome", "anime_speed_lines", "anime_sparkle_burst", "anime_gradient_hair", "anime_mecha_plate", "anime_sakura_scatter", "anime_energy_aura", "anime_comic_halftone", "anime_neon_outline", "anime_crystal_facet"],
};

const _SPECIALS_IRIDESCENT_INSECTS = {
    "★ IRIDESCENT INSECTS": ["beetle_jewel", "beetle_rainbow", "butterfly_morpho", "butterfly_monarch", "dragonfly_wing", "scarab_gold", "moth_luna", "beetle_stag", "wasp_warning", "firefly_glow"],
};

const _SPECIALS_EFFECTS_VISION = {
    "Effects & Vision": ["acid_trip", "antimatter", "astral", "aurora", "banshee", "black_diamond", "blood_oath", "bone", "catacombs", "cel_shade", "chromatic_aberration", "crt_scanline", "crystal_cave", "cursed", "daguerreotype", "dark_fairy", "dark_ritual", "datamosh", "death_metal", "demon_forge", "double_exposure", "dragon_breath", "dreamscape", "eclipse", "embossed", "enchanted", "ethereal", "film_burn", "fish_eye", "fourth_dimension", "galaxy", "gargoyle", "glitch", "glitch_reality", "graveyard", "grid_walk", "halftone", "hallucination", "haunted", "heat_haze", "hellhound", "holographic_wrap", "infrared", "iron_maiden", "kaleidoscope", "levitation", "lich_king", "long_exposure", "mirage", "multiverse", "nebula_core", "necrotic", "negative", "nightmare", "parallax", "phantom", "phantom_zone", "polarized", "portal", "possessed", "psychedelic", "reaper", "refraction", "rust", "sepia", "shadow_realm", "silk_road", "solarization", "spectral", "tesseract", "thermochromic", "tin_type", "uv_blacklight", "vinyl_record", "void_walker", "voodoo", "wraith", "x_ray"],
};

// Section order and group → section map
// NOTE (2026-04-17): "Racing Heritage" and "Multi-Spectrum" sections removed
// from Specials. Racing Heritage now lives exclusively under BASE_GROUPS; the
// 25 Multi-Spectrum finishes were scrubbed entirely per user request.
const SPECIALS_SECTION_ORDER = ["SHOKKER", "Color Science", "Material World", "Fusion Lab", "Atmosphere", "Signal", "Effects & Vision"];
const SPECIALS_SECTIONS = {
    "SHOKKER": ["PARADIGM", "★ COLORSHOXX", "★ MORTAL SHOKK", "★ NEON UNDERGROUND", "★ ANIME INSPIRED", "★ IRIDESCENT INSECTS", "Shokk Series", "Angle SHOKK", "Extreme & Experimental"],
    "Color Science": ["Chameleon", "Aurora & Chromatic Flow", "Chromatic Flake", "Prizm", "Color-Shift Adaptive", "Color-Shift Presets", "Color-Shift Duos", "Color Clash", "Gradient Directional", "Gradient Vortex", "Gradient Extended"],
    "Material World": ["Atelier — Ultra Detail", "Metals & Forged", "Glass & Surface", "Leather & Texture", "Standalone Effects", "Brushed & Machined", "Clearcoat Effects", "Ornamental", "Natural & Organic", "Surface Treatment", "Geometric & Structural", "Optical & Light", "Particles & Textures", "Patterns & Effects"],
    "Fusion Lab": ["Ghost Geometry", "Depth Illusion", "Material Gradients", "Directional Grain", "Reactive Panels", "Sparkle Systems", "Multi-Scale Texture", "Weather & Age", "Exotic Physics", "Tri-Zone Materials", "Metallic Halos", "Light Waves", "Fractal Chaos", "Spectral Reactive", "Panel Quilting", "Surface Accent"],
    "Atmosphere": ["Atmosphere"],
    "Signal": ["Signal"],
    "Effects & Vision": ["Effects & Vision"],
};

// Merged flat object (all reimagined groups — only backend-registered IDs)
const SPECIAL_GROUPS = Object.assign({},
    _SPECIALS_SHOKKER,
    _SPECIALS_ANIME_INSPIRED,
    _SPECIALS_IRIDESCENT_INSECTS,
    _SPECIALS_COLOR_SCIENCE,
    _SPECIALS_MATERIAL_WORLD,
    _SPECIALS_FUSION_LAB,
    _SPECIALS_RACING_HERITAGE,
    _SPECIALS_ATMOSPHERE,
    _SPECIALS_SIGNAL,
    _SPECIALS_MULTI_SPECTRUM,
    _SPECIALS_EFFECTS_VISION
);

// Keep the shipping Specials picker aligned with the MONOLITHICS filters below.
// Removed ids are intentionally not reachable; leaving them in SPECIAL_GROUPS
// creates blank picker tiles and trips validateFinishData().
Object.keys(SPECIAL_GROUPS).forEach(function (groupName) {
    if (!Array.isArray(SPECIAL_GROUPS[groupName])) return;
    SPECIAL_GROUPS[groupName] = SPECIAL_GROUPS[groupName].filter(function (id) {
        return !REMOVED_SPECIAL_IDS.has(id);
    });
});

const MONOLITHICS = [
    // ★ COLORSHOXX WAVE 3 — Micro-Flake Color Shift (migrated from MICRO-FLAKE COLOR SHIFT)
    // 2-color micro-flake shifts
    { id: "cx_gold_green", name: "CX Gold-Green Flake", desc: "Warm gold with green-gold micro-flakes. Subtle shift — the car breathes between gold and olive.", swatch: "linear-gradient(135deg, #D4A017 0%, #8B9A1E 100%)" },
    { id: "cx_gold_purple", name: "CX Gold-Purple Flake", desc: "Gold base with violet-bronze micro-flakes. Royal warmth that shifts to plum at edges.", swatch: "linear-gradient(135deg, #C9960C 0%, #7B5C8B 100%)" },
    { id: "cx_teal_blue", name: "CX Teal-Blue Flake", desc: "Cool teal metallic with deep blue flakes. Ocean depth that darkens at angle.", swatch: "linear-gradient(135deg, #2CA5A5 0%, #2854A5 100%)" },
    { id: "cx_copper_rose", name: "CX Copper-Rose Flake", desc: "Warm copper with rose-pink micro-flakes. Sunset metal that blushes.", swatch: "linear-gradient(135deg, #C87533 0%, #C26680 100%)" },
    // 3-color micro-flake progressions
    { id: "cx_gold_olive_emerald", name: "CX Gold-Olive-Emerald", desc: "3-shade: warm gold through olive into emerald green. Living forest metal.", swatch: "linear-gradient(135deg, #D4A017 0%, #8B8830 50%, #448844 100%)" },
    { id: "cx_purple_plum_bronze", name: "CX Purple-Plum-Bronze", desc: "3-shade: royal purple through plum into warm bronze. Ancient royalty on metal.", swatch: "linear-gradient(135deg, #6644AA 0%, #884466 50%, #AA8844 100%)" },
    { id: "cx_blue_teal_cyan", name: "CX Blue-Teal-Cyan", desc: "3-shade oceanic: deep blue through teal into bright cyan. Tropical lagoon.", swatch: "linear-gradient(135deg, #334488 0%, #338888 50%, #44BBBB 100%)" },
    { id: "cx_burgundy_wine_gold", name: "CX Burgundy-Wine-Gold", desc: "3-shade luxury: deep burgundy through wine into gold. Vintage Rolls-Royce.", swatch: "linear-gradient(135deg, #661133 0%, #883344 50%, #CCAA22 100%)" },
    // 4+ color micro-flake
    { id: "cx_sunset_horizon", name: "CX Sunset Horizon", desc: "4-shade: gold → amber → coral → rose. Full sunset in metallic flakes.", swatch: "linear-gradient(135deg, #DDAA22 0%, #CC7733 33%, #BB5555 66%, #AA5577 100%)" },
    { id: "cx_northern_lights", name: "CX Northern Lights", desc: "4-shade aurora: green → teal → violet → magenta. Cosmic at flake level.", swatch: "linear-gradient(135deg, #55AA66 0%, #448888 33%, #665588 66%, #885577 100%)" },
    { id: "cx_peacock_fan", name: "CX Peacock Fan", desc: "4-shade: deep blue → teal → emerald → bronze. Iridescent feather.", swatch: "linear-gradient(135deg, #334477 0%, #337766 33%, #448855 66%, #887744 100%)" },
    { id: "cx_rainbow_stealth", name: "CX Rainbow Stealth", desc: "6-shade: full rainbow at barely-visible flake level. Only shows in direct sun.", swatch: "conic-gradient(#AA4444, #AA8833, #66AA44, #4488AA, #6655AA, #AA4466, #AA4444)" },
    { id: "cx_oil_slick", name: "CX Oil Slick", desc: "5-shade: magenta → violet → blue → teal → green. Gasoline on water, metallic.", swatch: "linear-gradient(135deg, #884466 0%, #665588 25%, #445588 50%, #448877 75%, #558855 100%)" },
    { id: "cx_molten_metal", name: "CX Molten Metal", desc: "5-shade: black → red → orange → gold → white. Forge-hot at micro scale.", swatch: "linear-gradient(135deg, #222 0%, #882222 25%, #CC7722 50%, #DDBB22 75%, #EEEEDD 100%)" },
    // Impossible complementary combos
    { id: "cx_red_green_chaos", name: "CX Red-Green Impossible", desc: "Christmas on metal. Red and green micro-flakes that shouldn't work but the subtlety makes it sing.", swatch: "linear-gradient(135deg, #AA3344 0%, #BB6644 33%, #668844 66%, #449955 100%)" },
    { id: "cx_orange_blue_electric", name: "CX Orange-Blue Electric", desc: "Complementary shock. Warm orange and cool blue at pixel level. Electric tension.", swatch: "linear-gradient(135deg, #CC7722 0%, #BB8844 33%, #557788 66%, #445588 100%)" },
    { id: "cx_pink_yellow_pop", name: "CX Pink-Yellow Pop", desc: "Bubblegum meets sunshine. Hot pink and bright yellow at flake scale — surprisingly elegant.", swatch: "linear-gradient(135deg, #CC5588 0%, #DD88AA 33%, #DDCC66 66%, #CCAA33 100%)" },
    { id: "cx_purple_gold_majesty", name: "CX Purple-Gold Majesty", desc: "Deep purple and rich gold in noble opposition. LSU. Lakers. Royalty.", swatch: "linear-gradient(135deg, #553388 0%, #775599 33%, #BBAA44 66%, #DDCC33 100%)" },
    // ★ COLORSHOXX WAVE 3 — Angle-Dependent Shifts (migrated from DUAL COLOR SHIFT)
    { id: "cx_custom_shift", name: "CX Custom Shift — Pick ANY 2 Colors", desc: "Choose any two colors and SPB builds a true angle-shift between them. Use this when the stock duos are close but you want your own face-to-edge flip.", swatch: "conic-gradient(from 0deg, #ff3388, #ffd926, #1a4de6, #1ae64d, #ff3388)" },
    { id: "cx_pink_to_gold", name: "CX Pink → Gold Shift", desc: "Wide candy-to-gold roll with a molten arc profile — hot pink holds face-on, then pours into rich gold across the edges.", swatch: "linear-gradient(135deg, #FF3388 0%, #FFD926 100%)" },
    { id: "cx_blue_to_orange", name: "CX Blue → Orange Shift", desc: "Hard cobalt-to-ember split with a sharper complementary flip than the softer duo shifts. Reads colder face-on and hotter at break angles.", swatch: "linear-gradient(135deg, #1A4DE6 0%, #FF800D 100%)" },
    { id: "cx_purple_to_green", name: "CX Purple → Green Shift", desc: "Faceted Mystichrome-style jewel flip — royal purple on-axis, emerald-green flashes through the breaks and contour lines.", swatch: "linear-gradient(135deg, #991ACC 0%, #1AE64D 100%)" },
    { id: "cx_teal_to_magenta", name: "CX Teal → Magenta Shift", desc: "Curved electric sweep with teal body color and neon-magenta edge ribbons. Louder and more liquid than the straight complementary pairs.", swatch: "linear-gradient(135deg, #00CCB3 0%, #E61A80 100%)" },
    { id: "cx_red_to_cyan", name: "CX Red → Cyan Shift", desc: "High-contrast banded opposition — fire red face-on, ice cyan in crisp cool bands and edge flashes instead of one soft roll.", swatch: "linear-gradient(135deg, #E61A1A 0%, #1AE6E6 100%)" },
    { id: "cx_sunset_shift", name: "CX Sunset Shift", desc: "Broad warm-to-cool sweep tuned like late sun falling into plum shadow. Softer and more atmospheric than the aggressive duo flips.", swatch: "linear-gradient(135deg, #FF4D00 0%, #990066 100%)" },
    { id: "cx_emerald_ruby", name: "CX Emerald → Ruby Shift", desc: "Jewel-tone arc shift with darker mids — emerald face, ruby edge, and a richer luxury transition than the louder complementary duos.", swatch: "linear-gradient(135deg, #00B34D 0%, #CC0D26 100%)" },
    { id: "cx_ice_fire", name: "CX Ice → Fire Shift", desc: "Frosted face with a hard ember break — pale ice-blue on-axis that snaps into orange-red fire across contours and edge turns.", swatch: "linear-gradient(135deg, #B3D9FF 0%, #FF3300 100%)" },
    // ★ COLORSHOXX HYPERFLIP — opponent-pixel perceptual flips
    { id: "cx_hyperflip_red_blue", name: "CX HyperFlip Red/Blue", desc: "Opposing red and blue pixel populations with spec-gated dominance. Matte red reads off-angle; glossy blue detonates when light catches it.", swatch: "linear-gradient(135deg, #FF0504 0%, #0524FF 100%)" },
    { id: "cx_hyperflip_pink_black", name: "CX HyperFlip Pink/Black", desc: "Hot pink diffuse field hiding glossy black micro-slats. Reads candy pink, then snaps into black-glass depth under highlight.", swatch: "linear-gradient(135deg, #FF0A8C 0%, #020204 100%)" },
    { id: "cx_hyperflip_orange_cyan", name: "CX HyperFlip Orange/Cyan", desc: "Complementary opponent-pixel flip: orange body glow against cyan metallic flash, tuned for track-light motion.", swatch: "linear-gradient(135deg, #FF5700 0%, #00E0FF 100%)" },
    { id: "cx_hyperflip_lime_purple", name: "CX HyperFlip Lime/Purple", desc: "Lime diffuse signal and purple glossy signal interleaved at 2048 scale for a loud impossible color snap.", swatch: "linear-gradient(135deg, #59FF05 0%, #8C08FF 100%)" },
    { id: "cx_hyperflip_purple_gold", name: "CX HyperFlip Purple/Gold", desc: "Royal purple base with fine champagne-gold and hot gold flash cells. Complementary enough to shift hard without reading like pepper.", swatch: "linear-gradient(135deg, #4D0DB3 0%, #FFB30D 100%)" },
    { id: "cx_hyperflip_electric_blue_copper", name: "CX HyperFlip Electric Blue/Copper", desc: "Electric blue base carrying copper and amber micro-flake mist. Warm flakes pop only when the light band catches.", swatch: "linear-gradient(135deg, #002EFF 0%, #FF6B0F 100%)" },
    { id: "cx_hyperflip_bronze_teal", name: "CX HyperFlip Bronze/Teal", desc: "Burnished bronze body with teal and aqua-blue flake populations. A safer complementary flip with strong contrast in motion.", swatch: "linear-gradient(135deg, #B85C1F 0%, #00DBC7 100%)" },
    { id: "cx_hyperflip_silver_violet", name: "CX HyperFlip Silver/Violet", desc: "Fine silver face color with violet-blue flake reveal. Built for a cleaner luxury flip instead of blunt rainbow metal.", swatch: "linear-gradient(135deg, #B5B8C2 0%, #A80FFF 100%)" },
    { id: "cx_hyperflip_crimson_prism", name: "CX HyperFlip Crimson Prism", desc: "Crimson primary with three hidden complementary flake colors: cyan, gold, and violet. Four-color logic without a painted rainbow gradient.", swatch: "linear-gradient(135deg, #F2050D 0%, #00DBFF 38%, #FFBD0F 68%, #B80DFF 100%)" },
    { id: "cx_hyperflip_midnight_opal", name: "CX HyperFlip Midnight Opal", desc: "Midnight blue primary with copper, lime, and magenta flake colors. Four-color opal flash over a dark base.", swatch: "linear-gradient(135deg, #04061F 0%, #FF7514 38%, #6BFF0D 68%, #FF0DB8 100%)" },
    // ★ COLORSHOXX WAVE 4 — NEW finishes filling color gaps
    { id: "cx_cotton_candy", name: "CX Cotton Candy", desc: "Soft pink → baby blue → white. Dreamy carnival confection on metal.", swatch: "linear-gradient(135deg, #FFB6C1 0%, #87CEEB 50%, #FFFFFF 100%)" },
    { id: "cx_forest_fire", name: "CX Forest Fire", desc: "Deep emerald green → burnt orange → crimson red. Wildfire consuming the canopy.", swatch: "linear-gradient(135deg, #1B5E20 0%, #E65100 50%, #B71C1C 100%)" },
    { id: "cx_deep_sea", name: "CX Deep Sea", desc: "Navy blue → teal → aqua → pearl white. Descending through ocean layers.", swatch: "linear-gradient(135deg, #0D1B2A 0%, #1B6B63 33%, #48D1CC 66%, #E0F7FA 100%)" },
    { id: "cx_galaxy_dust", name: "CX Galaxy Dust", desc: "Deep purple → cosmic blue → silver → hot pink. Nebula in a paint can.", swatch: "linear-gradient(135deg, #4A148C 0%, #1A237E 33%, #B0BEC5 66%, #EC407A 100%)" },
    { id: "cx_autumn_blaze", name: "CX Autumn Blaze", desc: "Crimson red → burnt orange → gold → chocolate brown. Peak fall foliage.", swatch: "linear-gradient(135deg, #C62828 0%, #E65100 33%, #FFB300 66%, #4E342E 100%)" },
    { id: "cx_thunderstorm", name: "CX Thunderstorm", desc: "Dark charcoal gray → electric blue → white flash. Storm front rolling in.", swatch: "linear-gradient(135deg, #37474F 0%, #1565C0 50%, #E0E0E0 100%)" },
    { id: "cx_tropical_sunset", name: "CX Tropical Sunset", desc: "Living coral → hot magenta → rich gold → burnt orange. Island sky at golden hour.", swatch: "linear-gradient(135deg, #FF7043 0%, #D81B60 33%, #FFD54F 66%, #FF6F00 100%)" },
    { id: "cx_black_ice", name: "CX Black Ice", desc: "Absolute black → gunmetal silver → ice blue. Invisible danger on asphalt.", swatch: "linear-gradient(135deg, #0A0A0A 0%, #78909C 50%, #B3E5FC 100%)" },
    { id: "cx_cherry_blossom", name: "CX Cherry Blossom", desc: "Soft pink → pearl white → sage green. Spring hanami in metallic flake.", swatch: "linear-gradient(135deg, #F48FB1 0%, #FAFAFA 50%, #A5D6A7 100%)" },
    { id: "cx_volcanic_glass", name: "CX Volcanic Glass", desc: "Obsidian black → deep blood red → amber → orange glow. Magma under glass.", swatch: "linear-gradient(135deg, #1A1A1A 0%, #7F0000 33%, #FF8F00 66%, #FF6D00 100%)" },
    { id: "cx_neon_dreams", name: "CX Neon Dreams", desc: "Hot pink → electric blue → lime green → vivid purple. Synthwave on wheels.", swatch: "linear-gradient(135deg, #FF1493 0%, #00BFFF 33%, #76FF03 66%, #7C4DFF 100%)" },
    { id: "cx_champagne_toast", name: "CX Champagne Toast", desc: "Pale gold → silver → blush pink → cream. Celebration in a clearcoat.", swatch: "linear-gradient(135deg, #D4AF37 0%, #C0C0C0 33%, #F8BBD0 66%, #FFF8E1 100%)" },
    { id: "cx_emerald_city", name: "CX Emerald City", desc: "Rich emerald → gold → teal → lime. Oz in metallic flake.", swatch: "linear-gradient(135deg, #00695C 0%, #FFD700 33%, #00897B 66%, #76FF03 100%)" },
    { id: "cx_midnight_aurora", name: "CX Midnight Aurora", desc: "Pure black → aurora green → deep purple → cosmic blue. Northern lights at midnight.", swatch: "linear-gradient(135deg, #0A0A0A 0%, #00E676 33%, #6A1B9A 66%, #1A237E 100%)" },
    { id: "cx_bronze_age", name: "CX Bronze Age", desc: "Warm copper → antique bronze → rich gold → dark brown. Ancient metalwork reborn.", swatch: "linear-gradient(135deg, #BF6B3A 0%, #8D6E63 33%, #FFD54F 66%, #3E2723 100%)" },
    // Atelier — Ultra Detail (Pro Grade)
    // 2026-04-19 HEENAN HSTING5 — Sting copy fix: "pro-grade detail" was filler.
    { id: "atelier_japanese_lacquer", name: "Japanese Lacquer (Atelier)", desc: "Deep maroon-black urushi lacquer with hand-rubbed crackle — Kyoto-master glossy depth that reads as wet enamel from any angle.", swatch: "#220606" },
    { id: "atelier_engine_turned", name: "Engine Turned", desc: "Precision guilloche radial grooves catching light at every angle — machined elegance", swatch: "#a0a0a8" },
    { id: "atelier_damascus_layers", name: "Damascus Layers", desc: "Hand-folded Damascus steel with swirling grain lines revealing hundreds of forged layers", swatch: "#5a5a62" },
    { id: "atelier_cathedral_glass", name: "Cathedral Glass", desc: "Leaded segments with fine refraction and color fringing — gothic stained-glass cathedral aesthetic on candy or pearl bases", swatch: "#3A8099" },
    { id: "atelier_vintage_enamel_crackle", name: "Vintage Enamel Crackle", desc: "Aged enamel surface with fine organic crackle networks and subtle cell-pattern variation", swatch: "#f0ebe0" },
    // 2026-04-19 HEENAN HSTING6 — Sting copy fix: 60-char generic.
    { id: "atelier_carbon_weave_micro", name: "Carbon Weave Micro (Atelier)", desc: "Ultra-fine 1K carbon twill under glass-clear clearcoat — weave only readable up close, deep black sheen at distance.", swatch: "#1a1a1a" },
    { id: "atelier_pearl_depth_layers", name: "Pearl Depth Layers", desc: "Stacked pearl nacre layers creating luminous depth with gentle pastel hue shifts", swatch: "#f2f0ec" },
    { id: "atelier_hand_brushed_metal", name: "Hand Brushed Metal", desc: "Warm bronze-copper with visible directional hand-brush strokes and artisan character", swatch: "#b06a38" },
    { id: "atelier_forged_iron_texture", name: "Forged Iron Texture", desc: "Blacksmith-hammered iron with scale marks, micro pits, and rough forged character", swatch: "#3a3836" },
    { id: "atelier_micro_flake_burst", name: "Micro Flake Burst", desc: "Thousands of micro metallic flakes erupting like stars against an inky dark base", swatch: "#222228" },
    { id: "atelier_marble_vein_fine", name: "Marble Vein Fine", desc: "Delicate marble veining in multiple translucent layers — polished stone luxury", swatch: "#c8c4bc" },
    { id: "atelier_obsidian_glass", name: "Obsidian Glass", desc: "Volcanic obsidian glass with razor-sharp internal fracture lines catching faint light", swatch: "#0c0c12" },
    { id: "atelier_silk_weave", name: "Silk Weave", desc: "Ultra-fine silk textile weave with direction-dependent sheen that shifts as you move", swatch: "#f5f2eb" },
    { id: "atelier_ceramic_glaze", name: "Ceramic Glaze", desc: "Hand-fired ceramic glaze with pooled color depth and delicate surface crazing", swatch: "#2a7080" },
    { id: "atelier_brushed_titanium", name: "Brushed Titanium", desc: "Aerospace-grade brushed titanium with fine directional grain in cool blue-gray tones", swatch: "#7a8088" },
    { id: "atelier_gold_leaf_micro", name: "Gold Leaf Micro", desc: "Gold leaf with fine irregular patches and micro cracks — hand-applied gilding aesthetic for art-car and luxury builds", swatch: "#E0B830" },
    { id: "atelier_fluid_metal", name: "Fluid Metal", desc: "Liquid chrome in motion — turbulent metallic flow captured mid-ripple with mirror depth", swatch: "#a8a8b0" },
    // 2026-04-19 HEENAN HSTING7 — Sting copy fix: bland.
    { id: "fourth_dimension", name: "4th Dimension", desc: "Overlapping cube projections that read as 4D geometry — math-poster aesthetic on metal, dramatic on chrome bases.", swatch: "#4444cc" },
    { id: "acid_etched_glass", name: "Acid Etched Glass", desc: "Frosted decorative glass with acid-etched patterns creating soft diffused translucence", swatch: "#88bbcc" },
    { id: "acid_trip", name: "Acid Trip", desc: "Psychedelic morphing rainbow fractals flowing and breathing with hallucinogenic energy", swatch: "#ee44cc" },
    { id: "alexandrite", name: "Alexandrite", desc: "Rare color-change gemstone shifting from emerald green in daylight to ruby red at night", swatch: "#448844" },
    { id: "antimatter", name: "Antimatter", desc: "Negative image color inversion — inverted tones and hues", swatch: "#ccddee" },
    { id: "aurora", name: "Aurora", desc: "Shimmering northern lights curtains flowing across the surface in soft glowing bands", swatch: "#33ccaa" },
    { id: "barn_find", name: "Barn Find", desc: "Complete barn find — dust, cobwebs, mouse-chewed, faded paint with the full neglect package for authentic wreck aesthetics", swatch: "#887766" },
    { id: "black_diamond", name: "Black Diamond", desc: "Jet-black depth studded with scattered brilliant diamond sparkle points like a night sky", swatch: "#111122" },
    { id: "black_flag", name: "Black Flag", desc: "Ominous penalty shadow creeping inward from every edge — dark authority energy", swatch: "#111111" },
    { id: "cast_iron", name: "Cast Iron", desc: "Heavy rough-poured cast iron with sand texture, scale marks, and industrial weight", swatch: "#445555" },
    { id: "cc_acid_burn", name: "Color Clash: Acid Burn", desc: "Acid yellow center clashing with deep purple edges — flat matte", swatch: "linear-gradient(90deg, #3F0080 0%, #F2F200 50%, #3F0080 100%)" },
    { id: "cc_blood_orange", name: "Color Clash: Blood Orange", desc: "Blood red center clashing with electric blue edges — satin", swatch: "linear-gradient(90deg, #004DF2 0%, #B20D00 50%, #004DF2 100%)" },
    { id: "cc_bruised_sky", name: "Color Clash: Bruised Sky", desc: "Deep purple center fading to sickly yellow edges — satin to matte", swatch: "linear-gradient(90deg, #D9D933 0%, #4D008C 50%, #D9D933 100%)" },
    { id: "cc_candy_poison", name: "Color Clash: Candy Poison", desc: "Candy pink center into poison black-green edges — gloss to matte", swatch: "linear-gradient(90deg, #0D260D 0%, #FF66A6 50%, #0D260D 100%)" },
    { id: "cc_chaos_theory", name: "Color Clash: Chaos Theory", desc: "Shifting rainbow center dissolving into void black edges — mixed everything", swatch: "linear-gradient(90deg, #050505 0%, #FF0000 25%, #00FF00 50%, #0000FF 75%, #050505 100%)" },
    { id: "cc_chemical_spill", name: "Color Clash: Chemical Spill", desc: "Lime green center clashing with chemical orange edges — chrome", swatch: "linear-gradient(90deg, #FF7300 0%, #66F200 50%, #FF7300 100%)" },
    { id: "cc_coral_venom", name: "Color Clash: Coral Venom", desc: "Coral center clashing with viper green edges in a wide-gradient satin sweep — high-tension warm/cool clash", swatch: "linear-gradient(90deg, #009919 0%, #FF664D 50%, #009919 100%)" },
    { id: "cc_deep_friction", name: "Color Clash: Deep Friction", desc: "Deep red center clashing with electric teal edges — rough texture", swatch: "linear-gradient(90deg, #00D9BF 0%, #8C0000 50%, #00D9BF 100%)" },
    { id: "cc_digital_rot", name: "Color Clash: Digital Rot", desc: "Digital cyan center decaying into rot brown edges — satin", swatch: "linear-gradient(90deg, #66330D 0%, #00E6E6 50%, #66330D 100%)" },
    { id: "cc_electric_conflict", name: "Color Clash: Electric Conflict", desc: "Cyan center clashing with magenta edges under high gloss — vivid complementary opposition for show-floor pop", swatch: "linear-gradient(90deg, #E600B3 0%, #00E6F2 50%, #E600B3 100%)" },
    { id: "cc_fever_dream", name: "Color Clash: Fever Dream", desc: "Fever red center into hallucination purple edges — multi-finish 4 zones", swatch: "linear-gradient(90deg, #8000BF 0%, #E61A0D 50%, #8000BF 100%)" },
    { id: "cc_flash_burn", name: "Color Clash: Flash Burn", desc: "Flash white center searing into burn orange-red edges — chrome to rough", swatch: "linear-gradient(90deg, #E64D00 0%, #FFFFF2 50%, #E64D00 100%)" },
    { id: "cc_magma_freeze", name: "Color Clash: Magma Freeze", desc: "Molten red center freezing into arctic white edges — mixed chrome/matte/satin", swatch: "linear-gradient(90deg, #EBF2FF 0%, #E62600 50%, #EBF2FF 100%)" },
    { id: "cc_neon_bruise", name: "Color Clash: Neon Bruise", desc: "Electric purple center clashing with toxic green edges — chrome", swatch: "linear-gradient(90deg, #33F21A 0%, #8C00D9 50%, #33F21A 100%)" },
    { id: "cc_neon_war", name: "Color Clash: Neon War", desc: "Neon orange center battling neon blue edges over chrome metallic — maximum-saturation warring complement clash", swatch: "linear-gradient(90deg, #004DFF 0%, #FF6600 50%, #004DFF 100%)" },
    { id: "cc_nuclear_dawn", name: "Color Clash: Nuclear Dawn", desc: "Nuclear green center against crimson edges — rough matte", swatch: "linear-gradient(90deg, #B2000D 0%, #26F200 50%, #B2000D 100%)" },
    { id: "cc_plasma_edge", name: "Color Clash: Plasma Edge", desc: "White-hot center radiating into plasma blue edges — ultra chrome", swatch: "linear-gradient(90deg, #1A33F2 0%, #FFFAE6 50%, #1A33F2 100%)" },
    { id: "cc_punk_static", name: "Color Clash: Punk Static", desc: "Hot pink center dissolving into black & white static edges — flat matte", swatch: "linear-gradient(90deg, #808080 0%, #FF0D80 50%, #808080 100%)" },
    { id: "cc_radioactive", name: "Color Clash: Radioactive", desc: "Neon green center against deep maroon edges under gloss — toxic-glow vs blood-deep clash for hazmat-themed builds", swatch: "linear-gradient(90deg, #59000D 0%, #1AFF0D 50%, #59000D 100%)" },
    { id: "cc_rust_vs_ice", name: "Color Clash: Rust vs Ice", desc: "Rust orange center clashing with ice blue edges — matte center, chrome edges", swatch: "linear-gradient(90deg, #B3D9F2 0%, #B34D0D 50%, #B3D9F2 100%)" },
    { id: "cc_solar_clash", name: "Color Clash: Solar Clash", desc: "Solar gold center against void black edges — chrome center only", swatch: "linear-gradient(90deg, #050505 0%, #FFCC1A 50%, #050505 100%)" },
    { id: "cc_toxic_sunset", name: "Color Clash: Toxic Sunset", desc: "Hot pink center clashing with acid green edges — chrome fading to matte", swatch: "linear-gradient(90deg, #4DF20D 0%, #FF1A8C 50%, #4DF20D 100%)" },
    { id: "cc_ultraviolet_burn", name: "Color Clash: Ultraviolet Burn", desc: "UV purple center clashing with safety orange edges — semi-gloss", swatch: "linear-gradient(90deg, #FF8000 0%, #6600E6 50%, #FF8000 100%)" },
    { id: "cc_venom_strike", name: "Color Clash: Venom Strike", desc: "Venom green center dissolving into black edges — high gloss", swatch: "linear-gradient(90deg, #050505 0%, #26D900 50%, #050505 100%)" },
    { id: "cc_voltage_split", name: "Color Clash: Voltage Split", desc: "Electric yellow center splitting into deep navy edges — chrome center, matte edges", swatch: "linear-gradient(90deg, #000D4D 0%, #FFF200 50%, #000D4D 100%)" },
    { id: "cel_shade", name: "Cel Shade", desc: "Bold cartoon cel-shading with hard-edged shadow bands and flat color fill zones", swatch: "#44aa44" },
    { id: "chameleon_amethyst", name: "Chameleon Amethyst", desc: "Purple to pink to magenta color-shift like a turning amethyst crystal in sunlight", swatch: "#6633aa" },
    { id: "chameleon_arctic", name: "Chameleon Arctic", desc: "Ice blue shifting to white then silver — frigid arctic tones that shimmer with movement", swatch: "#88ccee" },
    { id: "chameleon_copper", name: "Chameleon Copper", desc: "Warm copper to bronze to gold metal shift like heated precious alloy catching firelight", swatch: "#cc7744" },
    { id: "chameleon_emerald", name: "Chameleon Emerald", desc: "Rich emerald to teal to cyan jewel-tone shift — deep gemstone color-flip brilliance", swatch: "#22aa66" },
    { id: "chameleon_midnight", name: "Chameleon Midnight", desc: "Deep purple to blue to teal midnight shift that hides its colors until the light hits", swatch: "#4422aa" },
    { id: "chameleon_obsidian", name: "Chameleon Obsidian", desc: "Near-black stealth shift revealing deep purple and dark blue only at sharp angles", swatch: "#221144" },
    { id: "chameleon_ocean", name: "Chameleon Ocean", desc: "Teal to sapphire blue to purple deep ocean color-shift like sunlight through water", swatch: "#2266aa" },
    { id: "chameleon_phoenix", name: "Chameleon Phoenix", desc: "Fiery red to orange to gold phoenix shift — a blazing rebirth captured in pigment", swatch: "#ee4422" },
    { id: "chameleon_venom", name: "Chameleon Venom", desc: "Toxic green to yellow to lime venom shift with an aggressive venomous color-flip", swatch: "#44cc22" },
    { id: "chameleon_aurora", name: "Chameleon Aurora", desc: "Green to blue to purple aurora color-flip mimicking the shimmer of northern lights", swatch: "#33cc88" },
    { id: "chameleon_fire", name: "Chameleon Fire", desc: "Red to orange to yellow fire shift — living flame color that dances with every curve", swatch: "#ee4422" },
    { id: "chameleon_frost", name: "Chameleon Frost", desc: "White to ice blue to silver frost shift — cold crystalline color that glitters softly", swatch: "#ccddee" },
    { id: "chameleon_galaxy", name: "Chameleon Galaxy", desc: "Deep purple to blue to star-white galaxy shift with cosmic depth and brilliance", swatch: "#442288" },
    { id: "chameleon_neon", name: "Chameleon Neon", desc: "Electric neon green to yellow to pink shift — vivid sign-glow color that demands attention", swatch: "#44ff44" },
    { id: "mystichrome", name: "Mystichrome", desc: "Iconic purple → green → gold Ford SVT Mystichrome shift — the legendary 2004 Cobra Cobra factory color flop", swatch: "#7744AA" },
    { id: "aurora_borealis", name: "Aurora Borealis", desc: "Northern lights flowing curtains — green → teal → cyan → blue → violet fine bands", swatch: "linear-gradient(135deg, #33cc88 0%, #33bbcc 25%, #3388cc 50%, #6644cc 75%, #33cc88 100%)" },
    { id: "aurora_solar_wind", name: "Aurora Solar Wind", desc: "Electric solar bands — orange → gold → yellow → lime → cyan → blue flowing threads", swatch: "linear-gradient(135deg, #ee8833 0%, #ccaa33 25%, #88cc33 50%, #33cccc 75%, #3388cc 100%)" },
    { id: "aurora_nebula", name: "Aurora Nebula", desc: "Cosmic wisps — deep purple → magenta → pink → rose → coral → amber flowing bands", swatch: "linear-gradient(135deg, #8833cc 0%, #cc3388 25%, #ee6688 50%, #ee8866 75%, #ccaa55 100%)" },
    { id: "aurora_chromatic_surge", name: "Aurora Chromatic Surge", desc: "Full rainbow spectrum in tight concentrated flowing bands", swatch: "linear-gradient(135deg, #ff3333 0%, #ffaa33 17%, #ffff33 33%, #33cc33 50%, #33cccc 67%, #3333cc 83%, #cc33cc 100%)" },
    { id: "aurora_frozen_flame", name: "Aurora Frozen Flame", desc: "Fire meets ice — ice blue → white → gold → red concentrated flow", swatch: "linear-gradient(135deg, #66aaee 0%, #eeeeff 25%, #eebb33 50%, #cc4422 75%, #66aaee 100%)" },
    { id: "aurora_deep_ocean", name: "Aurora Deep Ocean", desc: "Abyssal flowing bands — dark navy → sapphire → teal → aqua → seafoam", swatch: "linear-gradient(135deg, #223366 0%, #334488 25%, #337788 50%, #44aa99 75%, #66ccaa 100%)" },
    { id: "aurora_volcanic", name: "Aurora Volcanic Flow", desc: "Molten magma veins — black → deep red → orange → gold flowing bands", swatch: "linear-gradient(135deg, #221111 0%, #882222 25%, #cc5522 50%, #eeaa33 75%, #221111 100%)" },
    { id: "aurora_ethereal", name: "Aurora Ethereal", desc: "Ultra-fine pastel threads — lavender → mint → peach → sky delicate flowing shimmer", swatch: "linear-gradient(135deg, #ccaaee 0%, #aaeebb 25%, #eeccaa 50%, #aaccee 75%, #ccaaee 100%)" },
    { id: "aurora_toxic_current", name: "Aurora Toxic Current", desc: "Electric poison bands — acid green → neon yellow → electric blue concentrated flow", swatch: "linear-gradient(135deg, #44ee44 0%, #aaee22 25%, #eeff33 50%, #3388ee 75%, #44ee44 100%)" },
    { id: "aurora_midnight_silk", name: "Aurora Midnight Silk", desc: "Dark luxury — barely visible deep blue → purple → teal threads on near-black", swatch: "linear-gradient(135deg, #222244 0%, #332244 25%, #442244 50%, #223344 75%, #222244 100%)" },
    { id: "aurora_electric_candy", name: "Aurora Electric Candy", desc: "WILD — hot pink → electric blue → neon yellow → lime → magenta sharp flowing bands", swatch: "linear-gradient(135deg, #ff2288 0%, #2255ee 25%, #eeff22 50%, #55ee22 75%, #dd22cc 100%)" },
    { id: "aurora_ocean_phosphor", name: "Aurora Ocean Phosphorescence", desc: "Deep navy → bioluminescent blue → cyan glow → dark teal → seafoam gentle bands", swatch: "linear-gradient(135deg, #1a2b55 0%, #224499 25%, #22bbcc 50%, #228877 75%, #44bbaa 100%)" },
    { id: "aurora_molten_earth", name: "Aurora Molten Earth", desc: "Burnt sienna → copper → dark red → amber → charcoal warm earthy flow", swatch: "linear-gradient(135deg, #bb5522 0%, #cc7733 25%, #882211 50%, #ddaa33 75%, #333333 100%)" },
    { id: "aurora_arctic_shimmer", name: "Aurora Arctic Shimmer", desc: "Ice white → pale blue → silver → frost blue → pale lavender cold delicate shimmer", swatch: "linear-gradient(135deg, #eef5ff 0%, #aaccee 25%, #ddeeff 50%, #99bbdd 75%, #ccbbee 100%)" },
    { id: "aurora_neon_storm", name: "Aurora Neon Storm", desc: "ULTRA WILD — neon green → hot pink → electric purple → bright orange → cyan max bands", swatch: "linear-gradient(135deg, #22ff44 0%, #ff2299 25%, #aa22ff 50%, #ff8800 75%, #22eeff 100%)" },
    { id: "aurora_twilight_veil", name: "Aurora Twilight Veil", desc: "Deep purple → rose gold → dusty pink → slate blue → dark magenta elegant dusk flow", swatch: "linear-gradient(135deg, #552288 0%, #cc8866 25%, #cc8899 50%, #556699 75%, #882266 100%)" },
    { id: "aurora_dragon_fire", name: "Aurora Dragon Fire", desc: "WILD — bright orange → deep red → gold → black → surprise electric blue flowing bands", swatch: "linear-gradient(135deg, #ff8822 0%, #881100 25%, #ddaa22 50%, #111111 75%, #2266ee 100%)" },
    { id: "aurora_crystal_prism", name: "Aurora Crystal Prism", desc: "WILD — full rainbow spectrum: red → orange → yellow → green → blue → violet flowing", swatch: "linear-gradient(135deg, #ff2222 0%, #ff8822 17%, #ffff22 33%, #22cc44 50%, #2244ee 67%, #8822dd 83%, #ff2222 100%)" },
    { id: "aurora_shadow_silk", name: "Aurora Shadow Silk", desc: "Dark luxurious flow — black → dark purple → dark teal → charcoal → midnight blue", swatch: "linear-gradient(135deg, #0a0a0a 0%, #221133 25%, #112233 50%, #1a1a1a 75%, #111133 100%)" },
    { id: "aurora_copper_patina", name: "Aurora Copper Patina", desc: "Copper → verdigris green → brown → teal → oxidized orange aged metal flow", swatch: "linear-gradient(135deg, #bb7733 0%, #448866 25%, #774422 50%, #337766 75%, #cc6622 100%)" },
    { id: "aurora_poison_ivy", name: "Aurora Poison Ivy", desc: "ULTRA WILD — toxic green → black → bright lime → dark emerald → acid yellow aggressive", swatch: "linear-gradient(135deg, #33dd22 0%, #111111 25%, #aaff00 50%, #115522 75%, #ddff00 100%)" },
    { id: "aurora_champagne_dream", name: "Aurora Champagne Dream", desc: "Pale gold → cream → blush pink → soft peach → pearl white luxurious soft flow", swatch: "linear-gradient(135deg, #eeddaa 0%, #fffaee 25%, #ffcccc 50%, #ffddbb 75%, #f8f8f5 100%)" },
    { id: "aurora_thunderhead", name: "Aurora Thunderhead", desc: "Steel grey → dark charcoal → silver flash → slate → gunmetal dramatic storm flow", swatch: "linear-gradient(135deg, #8899aa 0%, #333344 25%, #ccddee 50%, #667788 75%, #445566 100%)" },
    { id: "aurora_coral_reef", name: "Aurora Coral Reef", desc: "Coral pink → turquoise → sand gold → seafoam → deep blue tropical underwater flow", swatch: "linear-gradient(135deg, #ff7766 0%, #22bbaa 25%, #ddbb66 50%, #66ccaa 75%, #2255aa 100%)" },
    { id: "aurora_black_rainbow", name: "Aurora Black Rainbow", desc: "WILD — very dark rainbow: dark red → dark orange → dark yellow → dark green → dark blue", swatch: "linear-gradient(135deg, #661111 0%, #884422 17%, #887711 33%, #224411 50%, #112266 67%, #331166 83%, #661111 100%)" },
    { id: "aurora_cherry_blossom", name: "Aurora Cherry Blossom", desc: "Soft pink → white → pale rose → light green → blush delicate spring flow", swatch: "linear-gradient(135deg, #ffaacc 0%, #fff8fa 25%, #ffbbcc 50%, #bbddaa 75%, #ffbbcc 100%)" },
    { id: "aurora_plasma_reactor", name: "Aurora Plasma Reactor", desc: "ULTRA WILD — electric cyan → white-hot → purple → bright blue → magenta high energy", swatch: "linear-gradient(135deg, #22eeff 0%, #eeffff 25%, #8822ff 50%, #2266ff 75%, #ff22cc 100%)" },
    { id: "aurora_autumn_ember", name: "Aurora Autumn Ember", desc: "Burnt orange → dark red → gold → maroon → brown fall foliage flowing bands", swatch: "linear-gradient(135deg, #dd6622 0%, #881100 25%, #ccaa22 50%, #661122 75%, #774422 100%)" },
    { id: "aurora_ice_crystal", name: "Aurora Ice Crystal", desc: "Very pale blue → white → crystal clear → frost → pale cyan nearly-white ice flow", swatch: "linear-gradient(135deg, #ddeeff 0%, #ffffff 25%, #eef8ff 50%, #ccddff 75%, #cceeff 100%)" },
    { id: "aurora_supernova", name: "Aurora Supernova", desc: "ULTRA WILD — white-hot → orange → red → deep purple → black stellar explosion flow", swatch: "linear-gradient(135deg, #ffffee 0%, #ff9933 25%, #dd1100 50%, #551188 75%, #080808 100%)" },
    { id: "champagne_toast", name: "Champagne Toast", desc: "Warm golden effervescence with rising bubble sparkle and soft celebratory shimmer", swatch: "#ccaa77" },
    { id: "concrete", name: "Concrete", desc: "Raw poured concrete with industrial aggregate texture, subtle cracks, and urban weight", swatch: "#999999" },
    { id: "crocodile_leather", name: "Croc Leather", desc: "Full crocodile hide embossed texture with deep glossy lacquer and exotic scale detail", swatch: "#556644" },
    { id: "cs_complementary", name: "CS Complementary", desc: "Shifts the base paint toward its complementary opposite for bold contrasting color harmony", swatch: "#aa55aa" },
    { id: "cs_cool", name: "CS Cool", desc: "Absolute cool shift: blue → violet → deep teal (works on any base)", swatch: "linear-gradient(135deg, #2244bb 0%, #6633cc 50%, #1a8899 100%)" },
    { id: "cs_deepocean", name: "CS Deep Ocean", desc: "Abyssal sweep: deep navy → cerulean → bright teal → violet", swatch: "linear-gradient(135deg, #0a2255 0%, #1155aa 33%, #0088bb 66%, #5533aa 100%)" },
    { id: "cs_extreme", name: "CS Extreme", desc: "Aggressive 90-degree wild color push that slams hues into unexpected territory", swatch: "linear-gradient(135deg, #ee33aa 0%, #aa33ee 100%)" },
    { id: "cs_inferno", name: "CS Inferno (Overlay Shift)", desc: "Volcanic inferno ramp from black base through deep red, orange, and molten gold", swatch: "linear-gradient(135deg, #040000 0%, #880800 33%, #dd4400 66%, #ee8800 100%)" },
    { id: "cs_mystichrome", name: "CS Mystichrome (Purple→Green Overlay)", desc: "Classic Mystichrome purple to green to gold ramp applied as a color-shift overlay", swatch: "linear-gradient(135deg, #5522aa 0%, #22aa44 50%, #ccaa22 100%)" },
    { id: "cs_nebula", name: "CS Nebula", desc: "Space nebula sweep: deep purple → violet → magenta → pink — interstellar gas-cloud color shift for cosmic builds", swatch: "linear-gradient(135deg, #1a0044 0%, #5522aa 33%, #aa2288 66%, #dd5599 100%)" },
    { id: "cs_rainbow", name: "CS Rainbow", desc: "Full rainbow spectrum fanning outward from the base paint color in every direction", swatch: "linear-gradient(135deg, #ee6633 0%, #44ee22 33%, #2244ee 66%, #ee22aa 100%)" },
    { id: "cs_solarflare", name: "CS Solar Flare", desc: "Solar eruption: bright gold-white → orange → deep red → black", swatch: "linear-gradient(135deg, #eeee44 0%, #ee7722 33%, #dd2200 66%, #080400 100%)" },
    { id: "cs_split", name: "CS Split Complement", desc: "Split complementary dual shift creating sophisticated two-tone color harmony", swatch: "linear-gradient(135deg, #cc6688 0%, #6688cc 100%)" },
    { id: "cs_subtle", name: "CS Subtle", desc: "Gentle 15-degree hue nudge that barely whispers a color change from the base tone", swatch: "linear-gradient(135deg, #7799bb 0%, #88aacc 100%)" },
    { id: "cs_supernova", name: "CS Supernova (Overlay Shift)", desc: "Supernova: brilliant white-gold → amber → orange-red → deep red", swatch: "linear-gradient(135deg, #ffeeaa 0%, #ffaa22 33%, #ee4400 66%, #880808 100%)" },
    { id: "cs_toxic", name: "CS Toxic", desc: "Biohazard acid: nuclear yellow-green → chartreuse → lime → teal", swatch: "linear-gradient(135deg, #88ee00 0%, #44ee08 33%, #00ee30 66%, #00bbbb 100%)" },
    { id: "cs_triadic", name: "CS Triadic", desc: "Three-way color triangle shift from base creating balanced triadic color harmony", swatch: "linear-gradient(135deg, #dd7733 0%, #4488ee 50%, #cc44aa 100%)" },
    { id: "cs_candy_paint", name: "CS Candy Paint", desc: "Electric candy sweep: magenta → violet → cobalt → teal → lime", swatch: "linear-gradient(135deg, #ee0066 0%, #6600ee 33%, #0022ee 50%, #00ee88 75%, #aaee00 100%)" },
    { id: "cs_dark_flame", name: "CS Dark Flame", desc: "Volcanic dark fire: near-black → deep crimson → dark orange → charcoal", swatch: "linear-gradient(135deg, #100000 0%, #660000 25%, #aa1100 50%, #cc4400 75%, #1a0b0b 100%)" },
    { id: "cs_gold_rush", name: "CS Gold Rush", desc: "Precious metal spectrum: bright gold → amber → bronze → dark copper", swatch: "linear-gradient(135deg, #eecc00 0%, #dd8800 33%, #aa5500 66%, #662200 100%)" },
    { id: "cs_oilslick", name: "CS Oil Slick (Overlay Shift)", desc: "Petroleum rainbow: red → orange → gold → teal → blue → violet", swatch: "linear-gradient(135deg, #cc1100 0%, #ee7700 20%, #eecc00 40%, #00bb44 55%, #0044cc 75%, #aa00cc 100%)" },
    { id: "cs_rose_gold_shift", name: "CS Rose Gold", desc: "Luxury sweep: champagne → rose gold → copper → dark copper", swatch: "linear-gradient(135deg, #f5e6b8 0%, #ee8877 33%, #cc5544 66%, #882233 100%)" },
    { id: "cs_warm", name: "CS Warm", desc: "Absolute warm shift: gold → amber → sunset red (works on any base)", swatch: "linear-gradient(135deg, #eebb00 0%, #dd6611 50%, #cc2200 100%)" },
    { id: "cs_chrome_shift", name: "CS Chrome Shift", desc: "Metallic chrome angle-dependent color shift that changes hue as viewing angle moves", swatch: "#bbccdd" },
    { id: "cs_earth", name: "CS Earth", desc: "Natural earth tone shift pulling colors toward warm clay, ochre, and organic brown", swatch: "#886644" },
    { id: "cs_monochrome", name: "CS Monochrome", desc: "Single-hue value ramp from deep shadow to bright highlight within one color family", swatch: "#668899" },
    { id: "cs_neon_shift", name: "CS Neon Shift", desc: "Bright neon glow shift that electrifies the base color with fluorescent intensity", swatch: "#44ff88" },
    { id: "cs_ocean_shift", name: "CS Ocean Shift", desc: "Deep ocean color shift pulling tones into moody teal, navy, and abyssal blue-green", swatch: "#226688" },
    { id: "cs_prism_shift", name: "CS Prism Shift", desc: "Rainbow prism dispersion fanning the base color into a spread of spectral neighbors", swatch: "#ee6644" },
    { id: "cs_vivid", name: "CS Vivid", desc: "Maximum saturation vivid color push cranking chroma to eye-searing intensity", swatch: "#ff44cc" },
    { id: "cursed", name: "Cursed", desc: "Cracked ancient dark surface with green poison seep — Lovecraftian artifact aesthetic for horror-themed builds", swatch: "#332244" },
    { id: "cyber_punk", name: "Cyberpunk", desc: "Rain-slicked neon pink and blue cyberpunk glow on dark surfaces with wet reflections", swatch: "#ff44ff" },
    { id: "brushed_steel_dark", name: "Dark Brushed Steel", desc: "Dark steel with heavy directional brush grain and moody gunmetal industrial character", swatch: "#888899" },
    { id: "dawn_patrol", name: "Dawn Patrol", desc: "Early morning golden-hour warmth with soft sunrise gradient and peaceful amber glow", swatch: "#886644" },
    { id: "depth_map", name: "Depth Map", desc: "3D depth perception rendered as grayscale elevation mapping — closer surfaces go brighter", swatch: "#446688" },
    { id: "desert_mirage", name: "Desert Mirage", desc: "Wavering heat shimmer distortion over sun-baked sand — the road ahead seems to melt", swatch: "#ccaa77" },
    { id: "double_exposure", name: "Double Exposure", desc: "Ghostly photography double-exposure overlay blending two images into one surreal frame", swatch: "#887766" },
    { id: "drafting", name: "Drafting", desc: "Aerodynamic draft pressure zones visualized with flowing air-stream color mapping", swatch: "#886644" },
    { id: "dreamscape", name: "Dreamscape", desc: "Surreal soft-focus landscape of floating color clouds and gentle luminous haze", swatch: "#7788cc" },
    { id: "drive_in", name: "Drive-In", desc: "1950s neon drive-in diner glow with chrome reflection — Americana sock-hop aesthetic for vintage cruise builds", swatch: "#CC6688" },
    { id: "eclipse", name: "Eclipse", desc: "Solar eclipse corona ring of blazing light surrounding an absolute black central void", swatch: "#111122" },
    { id: "ember_glow", name: "Ember Glow", desc: "Smoldering ember surface with bright orange-red cracks glowing through charred black", swatch: "#ee4422" },
    { id: "etched_metal", name: "Etched Metal", desc: "Chemically etched artistic metal with raised and recessed relief pattern detail", swatch: "#aabbcc" },
    { id: "firefly", name: "Firefly", desc: "Scattered bioluminescent glow points drifting across the surface like summer fireflies", swatch: "#ccaa44" },
    { id: "forged_iron", name: "Forged Iron", desc: "Blacksmith hammer-forged iron with glowing heat marks and rough worked-metal texture", swatch: "#556666" },
    { id: "frost_bite", name: "Frost Bite", desc: "Icy crystalline frost coating with sharp frozen crystal patterns and a cold bitter edge", swatch: "#88ccee" },
    { id: "frozen_lake", name: "Frozen Lake", desc: "Thick clear ice layer with trapped air bubbles, deep cracks, and frozen-in-time depth", swatch: "#aaddee" },
    { id: "galaxy", name: "Galaxy", desc: "Deep space nebula swirling with cosmic dust clouds and a brilliant distant star field", swatch: "#221144" },
    { id: "glitch", name: "Glitch", desc: "Digital corruption with RGB channel displacement, scan lines, and pixel scatter noise", swatch: "#ee44aa" },
    { id: "glitch_reality", name: "Glitch Reality", desc: "Heavy pixel scatter and noise displacement — digital corruption look as if reality itself is buffering and tearing", swatch: "#AA44EE" },
    { id: "green_flag", name: "Green Flag", desc: "Electric green start-race energy radiating outward — pure acceleration confidence", swatch: "#22aa33" },
    { id: "hammered_copper", name: "Hammered Copper", desc: "Hand-hammered warm copper with dimpled bowl texture and rich oxidation tones", swatch: "#cc7744" },
    { id: "heat_haze", name: "Heat Haze", desc: "Intense radiating heat distortion rising from hot metal — the air itself is shimmering", swatch: "#cc8844" },
    { id: "holographic_wrap", name: "Holographic Wrap", desc: "Full holographic rainbow surface wrap with prismatic color that shifts at every angle", swatch: "#aaccee" },
    { id: "hot_rod_flames", name: "Hot Rod Flames", desc: "Traditional hot rod flowing flame paint job effect — classic 1950s flame licks down the body for nostalgic kustom builds", swatch: "#EE4422" },
    { id: "infrared", name: "Infrared", desc: "Thermal camera heat-map visualization with hot red zones fading to cool blue regions", swatch: "#cc2233" },
    { id: "laser_grid", name: "Laser Grid", desc: "Bright neon laser beam grid projected across the surface in precise geometric lines", swatch: "#ff2222" },
    { id: "last_lap", name: "Last Lap", desc: "Desperate intensity — heightened contrast plus aggression for the do-or-die final stint of an endurance race", swatch: "#CC2222" },
    { id: "led_matrix", name: "LED Matrix", desc: "Dense RGB LED pixel grid surface glowing with individual addressable light dots", swatch: "#44ccee" },
    { id: "liquid_gold", name: "Liquid Gold", desc: "Flowing molten gold pooling across the surface with thick luxurious metallic viscosity", swatch: "#ccaa44" },
    { id: "liquid_metal", name: "Liquid Metal", desc: "T-1000 mercury liquid metal flowing and pooling with mirror-perfect chrome reflections", swatch: "#bbccdd" },
    { id: "meteor_shower", name: "Meteor Shower", desc: "Streaking bright meteor trails across dark surface — perseid-night cosmic aesthetic for sci-fi and space-themed builds", swatch: "#FFAA33" },
    { id: "mirage", name: "Mirage", desc: "Desert heat shimmer making the surface waver and ripple like a distant highway horizon", swatch: "#ccaa88" },
    { id: "mother_of_pearl", name: "Mother of Pearl", desc: "Iridescent nacre shell layers with gentle rainbow shimmer and organic pearlescent depth", swatch: "#ddeeff" },
    { id: "muscle_car_stripe", name: "Muscle Car Stripe", desc: "Classic 1970s GTO/Chevelle bold racing hood stripes — pure American muscle authority", swatch: "#dd2222" },
    // 2026-04-19 HEENAN HP4 — duplicate `mystichrome` id within MONOLITHICS
    // (sister entry at L1233 with different swatch + desc). MONOLITHICS_BY_ID
    // would silently overwrite. Renamed this one to mystichrome_classic
    // (matches its desc "the original chameleon paint").
    { id: "mystichrome_classic", name: "Mystichrome (Original)", desc: "Ford SVT Cobra legendary purple-green-gold color-shift — the original chameleon paint", swatch: "#6644aa" },
    { id: "neon_glow", name: "Neon Glow", desc: "Bright neon tube edge-glow effect casting vivid colored light against the surface", swatch: "#44ee88" },
    { id: "neon_vegas", name: "Neon Vegas", desc: "Las Vegas strip multi-color neon sign glow with buzzing electric casino energy", swatch: "#22ff88" },
    { id: "nightmare", name: "Nightmare", desc: "Distorted dark tones — shifted hues with hard shadows for fever-dream horror aesthetic on Halloween and themed builds", swatch: "#220022" },
    { id: "ocean_floor", name: "Ocean Floor", desc: "Deep ocean floor with bioluminescent glow scattered across an abyssal dark surface", swatch: "#224488" },
    { id: "oil_slick", name: "Oil Slick", desc: "Thin-film rainbow oil-on-water iridescence with full spectrum color interference", swatch: "#224466" },
    { id: "oil_slick_base", name: "Oil Slick", desc: "Thin-film rainbow over deep dark base — full spectrum petrol-film interference", swatch: "#1a3344" },
    { id: "thermal_titanium", name: "Thermal Titanium", desc: "Full titanium heat-color finish: silver to straw to purple to deep blue", swatch: "#7799bb" },
    { id: "galaxy_nebula_base", name: "Galaxy Nebula", desc: "Deep space nebula: multi-region color clouds with star field point sources", swatch: "#221144" },
    { id: "pace_lap", name: "Pace Lap", desc: "Yellow caution flag warm glow blending outward — the calm before green-flag intensity", swatch: "#44aa88" },
    { id: "patina_truck", name: "Patina Truck", desc: "Classic pickup patina — sun fade with surface rust and character that earned itself over decades of farm work", swatch: "#778866" },
    { id: "petrified_wood", name: "Petrified Wood", desc: "Ancient fossilized wood turned to stone with preserved grain and mineral color bands", swatch: "#887766" },
    { id: "phantom", name: "Phantom", desc: "Semi-transparent ghostly fade revealing depth beneath — a spectral see-through presence", swatch: "#aabbcc" },
    { id: "phantom_zone", name: "Phantom Zone", desc: "Cold crystalline prison look — angular facets in muted blue-gray, like Krypton's banishment cube from Superman lore", swatch: "#556688" },
    { id: "photo_finish", name: "Photo Finish", desc: "Finish-line camera motion blur with speed streaks frozen in the decisive moment", swatch: "#aabbcc" },
    { id: "pin_up", name: "Pin-Up Nose Art", desc: "WWII bomber nose art style hand-painted over military primer — vintage aviation charm", swatch: "#cc8877" },
    { id: "plasma_globe", name: "Plasma Globe", desc: "Electric plasma tendrils branching and reaching from bright center discharge points", swatch: "#8844ff" },
    { id: "polarized", name: "Polarized", desc: "Polarized lens stress pattern bands revealing hidden rainbow interference fringes", swatch: "#5588bb" },
    { id: "pole_position", name: "Pole Position", desc: "Front-row qualifier energy — electric confident metallic radiating first-place authority", swatch: "#886644" },
    { id: "portal", name: "Portal", desc: "Swirling vortex pattern — concentric energy rings in deep purple opening into another dimension across each panel", swatch: "#6633CC" },
    { id: "possessed", name: "Possessed", desc: "Demonic red-black inner glow pulsing beneath the surface like something alive inside", swatch: "#cc2222" },
    { id: "prizm_adaptive", name: "Prizm Adaptive", desc: "Panel-mapped adaptive color shift that reads base paint and shifts each panel uniquely", swatch: "#7799bb" },
    { id: "prizm_black_rainbow", name: "Prizm Black Rainbow", desc: "Near-black surface with a hidden full-spectrum rainbow revealed only at steep angles", swatch: "#222222" },
    { id: "prizm_blood_moon", name: "Prizm Blood Moon", desc: "Dark crimson to black to blood-red panel shift evoking a lunar eclipse in deep red", swatch: "#ff66aa" },
    { id: "prizm_duochrome", name: "Prizm Duochrome", desc: "Two-color flip panel shift where each body panel snaps between two distinct hues", swatch: "#aa44cc" },
    { id: "prizm_holographic", name: "Prizm Holographic", desc: "Full spectrum rainbow holographic panel shift scattering prismatic light across panels", swatch: "#cc88ee" },
    { id: "prizm_iridescent", name: "Prizm Iridescent", desc: "Oil-slick iridescent panel mapping with full spectrum color shift across every surface", swatch: "#aaccee" },
    { id: "prizm_mystichrome", name: "Prizm Mystichrome", desc: "Purple to green to gold Mystichrome color-flip mapped uniquely across each body panel", swatch: "#8844cc" },
    { id: "prizm_neon", name: "Prizm Neon", desc: "Electric neon color panel mapping assigning vivid fluorescent hues to each surface", swatch: "#ff66aa" },
    { id: "prizm_phoenix", name: "Prizm Phoenix", desc: "Red to orange to gold fire-phoenix panel mapping with blazing warm color-flip per panel", swatch: "#ee4422" },
    { id: "prizm_solar", name: "Prizm Solar", desc: "Gold to white to platinum solar panel mapping radiating bright celestial warmth", swatch: "#eecc22" },
    { id: "prizm_venom", name: "Prizm Venom", desc: "Toxic green to lime to yellow venom panel mapping with aggressive poisonous energy", swatch: "#44dd22" },
    { id: "prizm_cosmos", name: "Prizm Cosmos", desc: "Deep purple to blue to black cosmos panel shift evoking vast interstellar darkness", swatch: "#442288" },
    { id: "prizm_dark_matter", name: "Prizm Dark Matter", desc: "Black to purple to navy dark-matter panel shift — barely visible color in deep shadow", swatch: "#221144" },
    { id: "prizm_fire_ice", name: "Prizm Fire & Ice", desc: "Red to white to blue panel contrast — fire and ice battling across every body surface", swatch: "#cc2244" },
    { id: "prizm_spectrum", name: "Prizm Spectrum", desc: "Full rainbow spectrum mapped across panels creating a complete color-wheel car wrap", swatch: "#ee5533" },
    { id: "prizm_galaxy_dust", name: "Prizm Galaxy Dust", desc: "Purple to pink to white to teal angular sweep like cosmic dust across a galaxy arm", swatch: "linear-gradient(135deg, #7733cc 0%, #cc44aa 35%, #eeeeee 65%, #33bbaa 100%)" },
    { id: "prizm_sunset_strip", name: "Prizm Sunset Strip", desc: "Warm sunset angular sweep fading from orange through magenta and violet into deep navy", swatch: "linear-gradient(135deg, #ee8822 0%, #cc3366 35%, #7733aa 65%, #223388 100%)" },
    { id: "prizm_toxic_waste", name: "Prizm Toxic Waste", desc: "Acid green → black → neon yellow → purple faceted shift", swatch: "linear-gradient(135deg, #44ee22 0%, #111111 30%, #eeff22 65%, #6622aa 100%)" },
    { id: "prizm_chrome_rose", name: "Prizm Chrome Rose", desc: "Soft feminine faceted shift from chrome silver through rose pink to warm platinum", swatch: "linear-gradient(135deg, #cccccc 0%, #cc7788 35%, #ddaaaa 65%, #dddddd 100%)" },
    { id: "prizm_deep_space", name: "Prizm Deep Space", desc: "Dramatic angular shift from void black through deep blue and purple to blinding white", swatch: "linear-gradient(135deg, #111111 0%, #2233aa 35%, #7733bb 65%, #eeeeee 100%)" },
    { id: "prizm_copper_flame", name: "Prizm Copper Flame", desc: "Molten metal flow from warm copper through flame orange and dark red into antique bronze", swatch: "linear-gradient(135deg, #bb7744 0%, #ee6622 35%, #881122 65%, #886633 100%)" },
    { id: "prizm_alien_skin", name: "Prizm Alien Skin", desc: "Otherworldly faceted shift from lime through teal and forest green to burnished gold", swatch: "linear-gradient(135deg, #66cc22 0%, #22aa88 35%, #225522 65%, #ccaa22 100%)" },
    { id: "prizm_titanium", name: "Prizm Titanium", desc: "Blue-grey → purple-grey → gold-grey → steel flowing — subtle aerospace metal sheen with quiet color motion", swatch: "linear-gradient(135deg, #778899 0%, #887799 35%, #998877 65%, #889999 100%)" },
    { id: "prizm_aurora_shift", name: "Prizm Aurora Shift", desc: "Northern lights palette mapped into angular prizm facets with green-to-violet sweep", swatch: "linear-gradient(135deg, #33cc77 0%, #33aacc 30%, #4466cc 60%, #7733aa 80%, #cc44aa 100%)" },
    { id: "prizm_candy_paint", name: "Prizm Candy Paint", desc: "Bold candy-tone faceted shift from hot pink through deep purple and blue to rich teal", swatch: "linear-gradient(135deg, #ee3388 0%, #7733aa 35%, #3366cc 65%, #33aaaa 100%)" },
    { id: "race_worn", name: "Race Worn", desc: "500-mile race wear - rubber marks, stone chips, brake dust", swatch: "#776655" },
    { id: "radioactive", name: "Radioactive", desc: "Toxic nuclear green glow with hazmat intensity — bright reactor-core radiation on dark base", swatch: "#44ee22" },
    { id: "rain_race", name: "Rain Race", desc: "Wet surface with visible water droplets and splash — soaked rain-tire racing aesthetic for wet-weather endurance builds", swatch: "#886644" },
    { id: "reaper", name: "Reaper", desc: "Death-black gradient with cold scythe-edge gleam along highlight lines — grim and menacing", swatch: "#222222" },
    { id: "ruby", name: "Ruby", desc: "Deep blood-red gemstone with pigeon-blood core depth and brilliant internal fire refraction", swatch: "#cc1122" },
    { id: "rust", name: "Rust", desc: "Heavy orange-brown iron oxidation with flaking corrosion texture and rough pitted surface", swatch: "#aa5533" },
    { id: "sandstone", name: "Sandstone", desc: "Natural sandstone with visible mineral grain and warm sedimentary layers — desert rock feel", swatch: "#ccbb99" },
    { id: "sapphire", name: "Sapphire", desc: "Deep royal blue gemstone with brilliant internal fire sparkle and crystalline depth", swatch: "#2244aa" },
    { id: "scorched", name: "Scorched", desc: "Charred blackened surface with glowing hot-spot embers — post-fire scorched metal look", swatch: "#553322" },
    { id: "silk_road", name: "Silk Road", desc: "Flowing silk fabric drape with fine metallic thread shimmer — luxurious textile surface", swatch: "#886644" },
    { id: "stained_glass", name: "Stained Glass", desc: "Cathedral stained-glass window with vivid colored light zones and dark lead borders", swatch: "#aa4466" },
    { id: "static", name: "Static", desc: "Electric static discharge with bright sparking arcs crawling across a charged surface", swatch: "#88aadd" },
    { id: "thermochromic", name: "Thermochromic", desc: "Heat-sensitive color-change surface shifting hue based on temperature zones across panels", swatch: "#cc4466" },
    { id: "time_warp", name: "Time Warp", desc: "Temporal distortion effect with melting clock faces and spiral warp — surreal Dali look", swatch: "#4466aa" },
    { id: "tornado_alley", name: "Tornado Alley", desc: "Rotating debris-filled violent storm with dark funnel cloud and scattered impact marks", swatch: "#889999" },
    { id: "tunnel_run", name: "Tunnel Run", desc: "Le Mans tunnel transition from bright sunlight into deep shadow and back to daylight", swatch: "#886644" },
    { id: "under_lights", name: "Under Lights", desc: "Night race finish under artificial floodlights with harsh sodium glow and deep shadows", swatch: "#ffcc22" },
    { id: "uv_blacklight", name: "UV Blacklight", desc: "Blacklight-reactive neon glow — hidden fluorescent patterns emerge under UV light", swatch: "#7722ee" },
    { id: "velvet_crush", name: "Velvet Crush", desc: "Deep crushed velvet texture with pile direction shift — luxury fabric aesthetic with light/dark zones based on viewing angle", swatch: "#662244" },
    { id: "venetian_glass", name: "Venetian Glass", desc: "Hand-blown Murano glass with multi-color translucent layers and trapped air bubbles", swatch: "#44aaaa" },
    { id: "victory_burnout", name: "Victory Burnout", desc: "Tire smoke, confetti, and champagne splash celebration — full post-race podium party aesthetic for winner livery overlays", swatch: "#DDBB55" },
    { id: "vinyl_record", name: "Vinyl Record", desc: "Concentric vinyl groove spiral with reflective rainbow edge and retro center label zone", swatch: "#222222" },
    { id: "volcanic_glass", name: "Volcanic Glass", desc: "Black obsidian volcanic glass with razor-sharp edges and glowing magma vein fractures", swatch: "#553322" },
    { id: "dark_sigil", name: "Dark Sigil", desc: "Dark mystical sigil pattern with faint arcane glow lines on near-black ritual surface", swatch: "#442244" },
    { id: "weathered_paint", name: "Weathered Paint", desc: "Sun-damaged old paint with peeling flakes and cracking clearcoat over faded original color", swatch: "#887766" },
    { id: "white_flag", name: "White Flag", desc: "Final-lap bright white intensity flash — pure blinding white with maximum reflectivity", swatch: "#dddddd" },
    { id: "woodie_wagon", name: "Woodie Wagon", desc: "1940s wood-panel station wagon sides with honey-toned grain and chrome strip borders", swatch: "#886644" },
    { id: "worn_chrome", name: "Worn Chrome", desc: "Aged pitted chrome with rust spots bleeding through — decades of neglect on mirror finish", swatch: "#aabbbb" },
    { id: "forged_titanium", name: "Forged Titanium", desc: "Heat-treated titanium with blue-gold oxidation bands — exhaust-pipe temper colors on aerospace-grade metal for race builds", swatch: "#5577AA" },
    { id: "brushed_gunmetal", name: "Brushed Gunmetal", desc: "Directional brushed dark gunmetal with fine grain lines and cool blue-grey undertone", swatch: "#444450" },
    { id: "cast_iron_raw", name: "Raw Cast Iron", desc: "Rough sand-cast iron with visible porous surface texture and raw foundry scale marks", swatch: "#3a3a3a" },
    { id: "polished_brass", name: "Polished Brass", desc: "Mirror-polished brass with warm golden reflection and rich amber depth in shadows", swatch: "#ccaa44" },
    { id: "annealed_steel", name: "Annealed Steel", desc: "Heat-annealed steel showing rainbow temper colors from straw gold through blue to violet", swatch: "#6688aa" },
    { id: "oxidized_bronze", name: "Oxidized Bronze", desc: "Ancient bronze with verdigris green patina overlay — museum statue aesthetic with centuries of weathering for art-car builds", swatch: "#448855" },
    { id: "damascus_steel", name: "Damascus Steel", desc: "Folded steel pattern with visible layer striations — knife-grade pattern-welded steel for luxury and historical builds", swatch: "#556677" },
    { id: "wraith", name: "Wraith", desc: "Ghostly transparent dark smoke wisps drifting across a cold near-black spectral surface", swatch: "#334455" },
    { id: "x_ray", name: "X-Ray", desc: "Translucent X-ray negative effect revealing ghostly skeletal structure beneath the paint", swatch: "#33aacc" },
    { id: "astral", name: "Astral", desc: "Astral plane ethereal projection glow with soft luminous aura bleeding into deep indigo", swatch: "#7788cc" },
    { id: "crystal_cave", name: "Crystal Cave", desc: "Underground crystal cave with gemstone reflections and prismatic light scatter on facets", swatch: "#88aaee" },
    { id: "dark_fairy", name: "Dark Fairy", desc: "Dark fae enchantment with twisted magical glow — corrupted fairy dust on shadow base", swatch: "#664488" },
    { id: "dragon_breath", name: "Dragon Breath", desc: "Molten dragon fire exhale with bright orange heat core fading to scorched dark edges", swatch: "#ee6622" },
    { id: "enchanted", name: "Enchanted", desc: "Enchanted forest magical sparkle with soft green fairy-dust shimmer on woodland tones", swatch: "#44aa66" },
    { id: "ethereal", name: "Ethereal", desc: "Soft diffused glow — gentle light bloom with pale washed-out tones for dreamy heaven-touched appearance", swatch: "#AABBDD" },
    { id: "fractal_dimension", name: "Fractal Dimension", desc: "Deep fractal recursive pattern — multi-scale self-similar geometry that pulls the eye into infinite mathematical depth", swatch: "#6644CC" },
    { id: "hallucination", name: "Hallucination", desc: "Warped color morph — shifting hues with organic distortion for a fever-dream psychedelic surface effect", swatch: "#EE44AA" },
    { id: "levitation", name: "Levitation", desc: "Anti-gravity energy lift aura with bright levitation glow ring and distorted air beneath", swatch: "#8899cc" },
    { id: "multiverse", name: "Multiverse", desc: "Parallel universe overlap with dimensional bleed-through zones and reality-shift edges", swatch: "#774488" },
    { id: "nebula_core", name: "Nebula Core", desc: "Dense star-nursery nebula core with bright pink-violet gas glow and newborn star points", swatch: "#cc44aa" },
    { id: "simulation", name: "Simulation", desc: "Matrix-style green code rain cascading over dark base — digital simulation overlay", swatch: "#22cc44" },
    { id: "tesseract", name: "Tesseract", desc: "4D hypercube geometric projection with impossible perspective and folded spatial edges", swatch: "#5555cc" },
    { id: "void_walker", name: "Void Walker", desc: "Ultra-dark void with faint structural hints — deep black with subtle edges that hint at form without showing detail", swatch: "#221133" },
    { id: "voodoo", name: "Voodoo", desc: "Dark ritual scratched hex-symbol effect with smoky halos and disturbed static energy between spellcraft runes", swatch: "#5a2e3b" },
    { id: "art_deco_gold", name: "Art Deco Gold", desc: "1920s Art Deco geometric gold motif with sunburst rays and stepped symmetrical framing", swatch: "#ccaa44" },
    { id: "beat_up_truck", name: "Beat Up Truck", desc: "Well-used farm truck character wear with dents, scratches, and sun-faded workday patina", swatch: "#887766" },
    { id: "classic_racing", name: "Classic Racing", desc: "1960s Le Mans classic racing heritage with period-correct colors and vintage roundels", swatch: "#cc4422" },
    { id: "daguerreotype", name: "Daguerreotype", desc: "Early photography silver-plate image with mirror-like surface and ghostly exposure look", swatch: "#aabbcc" },
    { id: "diner_chrome", name: "Diner Chrome", desc: "1950s chrome diner counter polish with warm reflections and retro Americana nostalgia", swatch: "#ccddee" },
    { id: "faded_glory", name: "Faded Glory", desc: "Sun-bleached patriotic paint with faded stars-and-stripes tones — worn American pride", swatch: "#998877" },
    { id: "grindhouse", name: "Grindhouse", desc: "70s exploitation film grain damage with scratches, color shift, and missing-frame look", swatch: "#886644" },
    { id: "jukebox", name: "Jukebox", desc: "Chrome jukebox with neon bubble tubes and warm backlit glow — 1950s rock-and-roll vibe", swatch: "#ee88aa" },
    { id: "moonshine", name: "Moonshine", desc: "Prohibition-era copper still patina with hammered texture and dark tarnish character", swatch: "#cc9966" },
    { id: "nascar_heritage", name: "NASCAR Heritage", desc: "Classic NASCAR stock car heritage paint with bold primary colors and vintage sponsor feel", swatch: "#cc2222" },
    { id: "nostalgia_drag", name: "Nostalgia Drag", desc: "1960s nostalgia dragster hand-lettered paint with pinstripe flames and garage charm", swatch: "#dd6622" },
    { id: "old_school", name: "Old School", desc: "Old school custom car candy paint with deep transparent color and hot rod attitude", swatch: "#cc4488" },
    { id: "psychedelic", name: "Psychedelic", desc: "1960s psychedelic poster color explosion with swirling saturated hues and trippy warping", swatch: "#ee44cc" },
    { id: "sepia", name: "Sepia", desc: "Aged sepia photograph warm tone with soft brown-yellow cast and antique faded edges", swatch: "#aa8855" },
    { id: "tin_type", name: "Tin Type", desc: "Civil War era tintype photograph surface with dark grey-blue metallic and ghostly look", swatch: "#778888" },
    { id: "woodie", name: "Woodie", desc: "1940s woodie station wagon panel grain with warm honey oak and dark mahogany trim strips", swatch: "#886644" },
    { id: "zeppelin", name: "Zeppelin", desc: "1930s zeppelin duralumin riveted hull with brushed aluminum panels and exposed rivet rows", swatch: "#aabbcc" },
    { id: "aged_leather", name: "Aged Leather", desc: "Worn aged leather with deep patina grain, crease marks, and rich saddle-brown character", swatch: "#886644" },
    { id: "bark", name: "Bark", desc: "Tree bark rough organic texture with deep fissures and layered natural growth patterns", swatch: "#665544" },
    { id: "bone", name: "Bone", desc: "Bleached bone smooth organic surface with subtle porosity and warm ivory undertone", swatch: "#eeddcc" },
    { id: "brick_wall", name: "Brick Wall", desc: "Red clay brick masonry wall with aged mortar joints and irregular hand-fired surface", swatch: "#994433" },
    { id: "cork", name: "Cork", desc: "Natural cork with soft porous surface and warm tan tone — wine-barrel organic texture", swatch: "#bb9966" },
    { id: "granite", name: "Granite", desc: "Polished granite with dense speckled mineral crystals and deep stone-slab reflectivity", swatch: "#888899" },
    { id: "linen", name: "Linen", desc: "Fine linen woven fabric texture with visible thread crosshatch and soft natural drape", swatch: "#ddddcc" },
    { id: "obsidian_glass", name: "Obsidian Glass", desc: "Volcanic obsidian glass with razor-smooth dark surface and deep reflective black mirror", swatch: "#111122" },
    { id: "parchment", name: "Parchment", desc: "Ancient parchment scroll with aged yellowed paper, ink stains, and crinkled edges", swatch: "#ddcc99" },
    { id: "slate_tile", name: "Slate Tile", desc: "Natural slate tile with layered stone grain, cool blue-grey tone, and rough split face", swatch: "#556677" },
    { id: "stucco", name: "Stucco", desc: "Mediterranean stucco with rough hand-troweled plaster texture and sun-warmed surface", swatch: "#ccbb99" },
    { id: "suede", name: "Suede", desc: "Soft suede with napped leather surface that shifts shade with touch — velvety feel", swatch: "#998877" },
    { id: "terra_cotta", name: "Terra Cotta", desc: "Fired terra cotta clay with warm earthy orange-red surface and handmade kiln character", swatch: "#cc7744" },
    { id: "volcanic_rock", name: "Volcanic Rock", desc: "Rough volcanic pumice stone with dark porous surface and sharp vesicular bubble texture", swatch: "#444444" },
    { id: "aurora_glow", name: "Aurora Glow", desc: "Northern lights pulsing glow bands with green-to-violet curtain shimmer on dark sky base", swatch: "#33cc88" },
    { id: "blacklight_paint", name: "Blacklight Paint", desc: "UV-reactive blacklight paint that glows vivid neon under ultraviolet — invisible by day", swatch: "#aa44ff" },
    { id: "bioluminescent_wave", name: "Bioluminescent Wave", desc: "Ocean bioluminescence with electric blue wave glow — deep-sea plankton light-up effect", swatch: "#2288cc" },
    { id: "electric_arc", name: "Electric Arc", desc: "Visible electrical arc discharge with bright plasma bridge and ionized air glow path", swatch: "#44aaff" },
    { id: "fluorescent", name: "Fluorescent", desc: "Fluorescent tube harsh bright glow with cool blue-white cast and flat shadowless wash", swatch: "#88ff44" },
    { id: "glow_stick", name: "Glow Stick", desc: "Chemical glow stick snap with vivid green chemiluminescent liquid light effect", swatch: "#44ff88" },
    { id: "laser_show", name: "Laser Show", desc: "Multi-beam laser show projection with sharp colored lines cutting through fog and haze", swatch: "#ff22ff" },
    { id: "magnesium_burn", name: "Magnesium Burn", desc: "Intense white magnesium flare burn with blinding brightness and hot-metal sparkle shower", swatch: "#ffffff" },
    { id: "neon_sign", name: "Neon Sign", desc: "Glass tube neon sign with bright electric buzz glow and warm gas-discharge color tone", swatch: "#ff4488" },
    { id: "phosphorescent", name: "Phosphorescent", desc: "Afterglow phosphorescent charge-release that stores light and slowly emits green glow", swatch: "#88ff88" },
    { id: "rave", name: "Rave", desc: "Multi-color rave strobe pulse effect with rapid cycling neon flashes on deep black base", swatch: "#ee22ff" },
    { id: "sodium_lamp", name: "Sodium Lamp", desc: "Sodium street lamp amber monochrome glow with warm orange cast and flat nighttime wash", swatch: "#ffaa22" },
    { id: "tesla_coil", name: "Tesla Coil", desc: "Tesla coil discharge with branching violet-white arcs and crackling plasma tendrils", swatch: "#8844ff" },
    { id: "tracer_round", name: "Tracer Round", desc: "Military tracer bullet bright streak with hot phosphorus trail and ballistic light path", swatch: "#ff8822" },
    { id: "welding_arc", name: "Welding Arc", desc: "Intense arc welding bright blue-white flash with spatter sparks and UV-hot glow zone", swatch: "#44ccff" },
    { id: "banshee", name: "Banshee", desc: "Wailing banshee spectral scream with ghostly pale-blue trails and cold dread atmosphere", swatch: "#556677" },
    { id: "blood_oath", name: "Blood Oath", desc: "Dark blood pact ritual with deep crimson seal marks and ancient dried-blood surface tone", swatch: "#881122" },
    { id: "catacombs", name: "Catacombs", desc: "Ancient underground burial chamber stone with bone-dust residue and cold damp texture", swatch: "#554433" },
    { id: "dark_ritual", name: "Dark Ritual", desc: "Occult ritual circle with dark ceremonial markings and faint eldritch glow from symbols", swatch: "#332244" },
    { id: "death_metal", name: "Death Metal", desc: "Heavy metal aggressive dark surface with sharp angular typography and blackened steel look", swatch: "#222222" },
    { id: "demon_forge", name: "Demon Forge", desc: "Hellfire forge with hammered demon-metal texture — dark iron glowing from infernal heat", swatch: "#882211" },
    { id: "gargoyle", name: "Gargoyle", desc: "Gothic cathedral gargoyle stone surface with weathered grey limestone and carved detail", swatch: "#667766" },
    { id: "graveyard", name: "Graveyard", desc: "Misty graveyard with moonlit stone surface — cold fog over lichen-covered granite markers", swatch: "#445544" },
    { id: "haunted", name: "Haunted", desc: "Haunted house flickering spectral presence with cold spots and ghostly translucent patches", swatch: "#334455" },
    { id: "hellhound", name: "Hellhound", desc: "Burning hell beast with deep claw-mark gouges and ember-orange glow from beneath surface", swatch: "#cc3311" },
    { id: "iron_maiden", name: "Iron Maiden", desc: "Medieval iron torture device texture with pitted blackened steel and cold forged rivets", swatch: "#556655" },
    { id: "lich_king", name: "Lich King", desc: "Undead lich frost crown ice aura with pale blue necromantic glow over frozen dark metal", swatch: "#88aacc" },
    { id: "necrotic", name: "Necrotic", desc: "Decaying necrotic tissue with dark corruption spreading outward from blackened dead zones", swatch: "#443322" },
    { id: "shadow_realm", name: "Shadow Realm", desc: "Near-total black — deep shadow with minimal surface detail", swatch: "#111122" },
    { id: "spectral", name: "Spectral", desc: "Ghost spectral translucent phase-shift with see-through shimmer and fading edge presence", swatch: "#7788aa" },
    // 2026-04-19 HEENAN HP1 — id `acid_rain` already exists in BASES (L26).
    // Same id in two registries → BASES_BY_ID / MONOLITHICS_BY_ID lookup
    // returned whichever ran last; painter saw the wrong tile / wrong swatch.
    // Pillman cross-registry audit. Renamed MONOLITHICS entry to acid_rain_drip
    // (matches its desc "drip pattern") so both tiles can coexist honestly.
    { id: "acid_rain_drip", name: "Acid Rain Drip", desc: "Corrosive acid rain streaks dissolving through paint layers — chemical damage drip pattern", swatch: "#88aa44" },
    { id: "black_ice", name: "Black Ice", desc: "Invisible ice sheet dark glaze with treacherous transparent frost over near-black surface", swatch: "#334455" },
    { id: "blizzard", name: "Blizzard", desc: "Whiteout snow blizzard with heavily obscured surface and ice crystal buildup on edges", swatch: "#ddeeff" },
    { id: "dew_drop", name: "Dew Drop", desc: "Morning dew droplet fresh surface with hundreds of tiny water beads on cool metal base", swatch: "#88ccaa" },
    { id: "dust_storm", name: "Dust Storm", desc: "Desert dust storm with sandy brown obscuring haze and wind-blasted grit accumulation", swatch: "#ccaa77" },
    { id: "fog_bank", name: "Fog Bank", desc: "Dense fog bank with soft gradient fade obscuring all detail into milky white distance", swatch: "#aabbcc" },
    { id: "hail_damage", name: "Hail Damage", desc: "Golf-ball hail dent damage with pockmarked surface and fractured clearcoat craters", swatch: "#99aabb" },
    { id: "heat_wave", name: "Heat Wave", desc: "Extreme heat shimmer with wavering visual distortion — mirage effect over hot surface", swatch: "#cc9944" },
    { id: "hurricane", name: "Hurricane", desc: "Spiral hurricane eye-wall force with violent rotating cloud bands and dark storm center", swatch: "#446688" },
    { id: "lightning_strike", name: "Lightning Strike", desc: "Direct bolt lightning strike with branching Lichtenberg burn scars across the surface", swatch: "#ddee44" },
    { id: "magma_flow", name: "Magma Flow", desc: "Flowing volcanic magma with bright orange-red hot cracks glowing through cooled dark crust", swatch: "#ee4411" },
    { id: "monsoon", name: "Monsoon", desc: "Heavy monsoon rain sheet cascade with dense water curtain and flooded surface reflections", swatch: "#335577" },
    { id: "permafrost", name: "Permafrost", desc: "Permanently frozen deep ice with ancient trapped bubbles and pale blue crystalline surface", swatch: "#aaccdd" },
    { id: "solar_wind", name: "Solar Wind", desc: "Charged particle solar wind aurora stream with bright plasma bands on dark space base", swatch: "#eecc44" },
    { id: "tidal_wave", name: "Tidal Wave", desc: "Massive ocean wave crash force with towering wall of dark water and white foam spray", swatch: "#3366aa" },
    { id: "burnout_zone", name: "Burnout Zone", desc: "Post-victory burnout with thick rubber smoke, spinning tire marks, and celebration chaos", swatch: "#554433" },
    { id: "chicane_blur", name: "Chicane Blur", desc: "Quick chicane direction-change motion blur with sharp lateral smear and speed distortion", swatch: "#556688" },
    { id: "cool_down", name: "Cool Down", desc: "Post-race cool-down lap calm fade with engine-off serenity and sunset track atmosphere", swatch: "#668899" },
    { id: "drag_chute", name: "Drag Chute", desc: "Parachute deployment deceleration force with billowing canopy drag and speed-scrub look", swatch: "#887766" },
    { id: "flag_wave", name: "Flag Wave", desc: "Victory flag waving celebration ripple with checkered cloth motion and wind-snap energy", swatch: "#ccaa44" },
    { id: "grid_walk", name: "Grid Walk", desc: "Pre-race starting grid anticipation with clean fresh paint under bright pit-lane lighting", swatch: "#778899" },
    { id: "night_race", name: "Night Race", desc: "Under-lights night racing atmosphere with artificial floodlight glow and deep track shadows", swatch: "#223344" },
    { id: "pit_stop", name: "Pit Stop", desc: "High-speed pit stop blur urgency with rapid crew motion and tire-smoke in the pit box", swatch: "#888866" },
    { id: "red_mist", name: "Red Mist", desc: "Racing red-mist rage intensity — deep crimson tunnel-vision haze of full-attack driving", swatch: "#cc2233" },
    { id: "slipstream", name: "Slipstream", desc: "Aerodynamic draft tunnel effect with low-pressure wake shimmer trailing behind lead car", swatch: "#667788" },
    { id: "chromatic_aberration", name: "Chromatic Aberration", desc: "RGB color-channel edge separation with prismatic fringe shift — broken lens distortion", swatch: "#ee4488" },
    { id: "crt_scanline", name: "CRT Scanline", desc: "Retro CRT monitor scanline display with visible horizontal line gaps and phosphor glow", swatch: "#44cc88" },
    { id: "datamosh", name: "Datamosh", desc: "Corrupted video compression artifact with pixel-smear glitch blocks and broken frame data", swatch: "#cc44ee" },
    { id: "embossed", name: "Embossed", desc: "Raised surface emboss relief effect with sculpted depth illusion and soft highlight edges", swatch: "#aabbcc" },
    { id: "film_burn", name: "Film Burn", desc: "Overexposed film edge burn effect with hot orange-white light leak bleeding into frame", swatch: "#eedd44" },
    { id: "fish_eye", name: "Fish Eye", desc: "Wide-angle barrel distortion with extreme lens curvature warping edges outward from center", swatch: "#6688aa" },
    { id: "halftone", name: "Halftone", desc: "Print halftone dot pattern with variable-size Ben-Day dots creating tonal gradient zones", swatch: "#886644" },
    { id: "kaleidoscope", name: "Kaleidoscope", desc: "Symmetric kaleidoscope mirror pattern with repeated triangular slices and color symmetry", swatch: "#ee66aa" },
    { id: "long_exposure", name: "Long Exposure", desc: "Motion trail long-exposure light effect with streaked headlight paths and blurred movement", swatch: "#445588" },
    { id: "negative", name: "Negative", desc: "Photographic negative inversion with reversed tones — light becomes dark, colors flip hue", swatch: "#88ccdd" },
    { id: "parallax", name: "Parallax", desc: "Depth parallax layer-shifting effect with foreground and background at different rates", swatch: "#667799" },
    { id: "refraction", name: "Refraction", desc: "Light bending through thick glass refraction with displaced image and prismatic color edges", swatch: "#99bbdd" },
    { id: "solarization", name: "Solarization", desc: "Sabattier solarization tone reversal with partially inverted midtones and surreal contrast", swatch: "#cc8844" },
    { id: "void", name: "Void", desc: "Material with apparent holes - zero-specular patches surrounded by mirror chrome", swatch: "#020202" },
    { id: "living_chrome", name: "Living Chrome", desc: "Breathing chrome - full metallic with slow roughness oscillation creating undulation illusion", swatch: "#ccddee" },
    { id: "quantum", name: "Quantum", desc: "Every material simultaneously - coherent noise blocks with random metallic and roughness", swatch: "#8899aa" },
    { id: "p_aurora", name: "Aurora (PARADIGM)", desc: "Northern lights shimmer - horizontal curtain waves with angle-dependent highlights", swatch: "#33ddaa" },
    { id: "magnetic", name: "Magnetic", desc: "Iron filing magnetic field lines - pole-based vector field with metallic stripes", swatch: "#556688" },
    { id: "ember", name: "Ember", desc: "Glowing hot metal cooling - heat-mapped noise with orange-red glow zones", swatch: "#cc3300" },
    { id: "stealth", name: "Stealth", desc: "Radar-absorbing angular facets - Voronoi flat panels with ultra-high roughness", swatch: "#181818" },
    { id: "glass_armor", name: "Glass Armor", desc: "Transparent armor plating - rectangular glass panels with metallic frame edges", swatch: "#aaccdd" },
    { id: "p_static", name: "Static (PARADIGM)", desc: "TV static signal noise - scan lines with random metallic/roughness per pixel block", swatch: "#999999" },
    { id: "mercury_pool", name: "Mercury Pool", desc: "Liquid mercury pooling - smooth flowing metallic pools with mirror centers", swatch: "#b8c0cc" },
    { id: "phase_shift", name: "Phase Shift", desc: "Conductor/dielectric micro-stripes — alternating reflection models create strong angle-dependent shimmer", swatch: "#9088aa" },
    { id: "gravity_well", name: "Gravity Well", desc: "Radial Fresnel gradient traps - depth illusion where chrome centers fade to matte edges", swatch: "#2a2a3a" },
    { id: "thin_film", name: "Thin Film", desc: "Physically-linked color + reflectivity - oil-on-water rainbow where hue and spec change together", swatch: "#88aacc" },
    { id: "blackbody", name: "Blackbody", desc: "Continuous temperature emission - smooth black→red→orange→yellow→white thermal gradient", swatch: "#cc4400" },
    { id: "wormhole", name: "Wormhole", desc: "Connected void portal pairs — dark holes ringed with bright chrome edges", swatch: "#0a0a1a" },
    // 2026-04-19 HEENAN H4HR-3 — `crystal_lattice` collided with PATTERNS L832.
    // MONOLITHIC entry renamed; HP-MIGRATE handles backward compat. PATTERN
    // keeps the canonical id (it's the older established entry).
    { id: "crystal_lattice_mono", name: "Crystal Lattice (Mono)", desc: "Multi-scale hex grid interference — 3 overlapping crystalline layers create convincing depth", swatch: "#aabbdd" },
    { id: "pulse", name: "Pulse", desc: "Radial energy wavefronts - concentric metallic rings oscillate between chrome mirror and matte void", swatch: "#6688bb" },
    // ===== FUSIONS - 150 Paradigm Shift Hybrid Materials =====
    // P1: Material Gradients
    { id: "gradient_chrome_matte", name: "Gradient Chrome→Matte", desc: "Chrome mirror fading to dead-flat matte in a smooth vertical gradient — polish to stealth", swatch: "#ccddee" },
    { id: "gradient_candy_frozen", name: "Gradient Candy→Frozen", desc: "Deep candy color dissolving into frozen ice-pearl — warm wet depth meets cold crystal", swatch: "#cc88aa" },
    { id: "gradient_pearl_chrome", name: "Gradient Pearl→Chrome", desc: "Soft pearl shimmer sweeping diagonally into hard mirror chrome — subtle into bold", swatch: "#aabbcc" },
    { id: "gradient_metallic_satin", name: "Gradient Metallic→Satin", desc: "Metallic flake blending horizontally into smooth satin — sparkle fading to soft sheen", swatch: "#99aabc" },
    { id: "gradient_obsidian_mirror", name: "Gradient Obsidian→Mirror", desc: "Light-absorbing obsidian bursting radially into brilliant mirror chrome from center out", swatch: "#334455" },
    { id: "gradient_candy_matte", name: "Gradient Candy→Matte", desc: "Wet candy transparency warped by noise into dead-flat matte zones — organic blend edge", swatch: "#bb7799" },
    { id: "gradient_anodized_gloss", name: "Gradient Anodized→Gloss", desc: "Gritty anodized oxide sweeping diagonally into deep wet gloss — tech meets show car", swatch: "#8899aa" },
    { id: "gradient_ember_ice", name: "Gradient Ember→Ice", desc: "Glowing hot ember at bottom cooling upward into frozen ice-blue crystal at the top", swatch: "#cc6644" },
    { id: "gradient_carbon_chrome", name: "Gradient Carbon→Chrome", desc: "Raw carbon fiber weave warping into liquid mirror chrome — race tech meets luxury", swatch: "#556677" },
    { id: "gradient_spectraflame_void", name: "Gradient Spectra→Void", desc: "Vivid spectraflame color fading radially into total vantablack void — light to nothing", swatch: "#aa44cc" },
    // P2: Ghost Geometry
    { id: "ghost_hex", name: "Ghost Hex Grid", desc: "Hexagonal grid visible only in the clearcoat layer — hidden geometry revealed at angle", swatch: "#445566" },
    { id: "ghost_stripes", name: "Ghost Stripes", desc: "Racing stripe pattern embedded in clearcoat only — invisible head-on, revealed at angle", swatch: "#3a4a5a" },
    { id: "ghost_diamonds", name: "Ghost Diamonds", desc: "Diamond plate tread pattern in clearcoat — subtle geometric texture seen in reflections", swatch: "#4a5a6a" },
    { id: "ghost_waves", name: "Ghost Waves", desc: "Wave interference pattern in clearcoat layer — rippling geometry only visible at angle", swatch: "#3a5a6a" },
    { id: "ghost_camo", name: "Ghost Camo", desc: "Digital camouflage in clearcoat only — stealth geometry hidden in the transparent layer", swatch: "#4a5a5a" },
    { id: "ghost_scales", name: "Ghost Scales", desc: "Dragon scale pattern embedded in clearcoat — reptilian texture revealed in angled light", swatch: "#3a4a4a" },
    { id: "ghost_circuit", name: "Ghost Circuit", desc: "Circuit board traces in clearcoat — hidden tech lines revealed under angled light", swatch: "#3a5a5a" },
    { id: "ghost_vortex", name: "Ghost Vortex", desc: "Spiral vortex embedded in clearcoat — swirling geometry visible only in reflections", swatch: "#4a4a5a" },
    { id: "ghost_fracture", name: "Ghost Fracture", desc: "Shattered crack network in clearcoat only — fractured glass geometry revealed at angle", swatch: "#3a3a4a" },
    { id: "ghost_quilt", name: "Ghost Quilt", desc: "Micro-panel quilt pattern in clearcoat — subtle stitched grid visible under direct light", swatch: "#4a5a6b" },
    // P3: Directional Grain
    { id: "aniso_horizontal_chrome", name: "Aniso Horizontal Chrome", desc: "Horizontal brushed chrome grain with fine directional scratches — lathe-turned mirror metal", swatch: "#bbccdd" },
    { id: "aniso_vertical_pearl", name: "Aniso Vertical Pearl", desc: "Vertical polished pearl grain with top-to-bottom directional shimmer — tall elegant sweep", swatch: "#aabbcc" },
    { id: "aniso_diagonal_candy", name: "Aniso Diagonal Candy", desc: "45-degree diagonal candy shimmer with angled grain catching light at oblique angles", swatch: "#cc8899" },
    { id: "aniso_radial_metallic", name: "Aniso Radial Metallic", desc: "Radial metallic grain spreading outward from center — spun-metal centrifuge polish effect", swatch: "#99aabb" },
    { id: "aniso_circular_chrome", name: "Aniso Circular Chrome", desc: "Concentric circle chrome grain like a vinyl record — circular polish rings catching light", swatch: "#aabbdd" },
    { id: "aniso_crosshatch_steel", name: "Aniso Crosshatch Steel", desc: "Crossed 45-degree brushed steel grain creating fine crosshatch diamond interference pattern", swatch: "#8899aa" },
    { id: "aniso_spiral_mercury", name: "Aniso Spiral Mercury", desc: "Spiral outward mercury grain with liquid-metal shimmer following a logarithmic curve path", swatch: "#99aacc" },
    { id: "aniso_wave_titanium", name: "Aniso Wave Titanium", desc: "Wave-warped titanium grain with flowing sinusoidal brush direction and warm metal tone", swatch: "#7788aa" },
    { id: "aniso_herringbone_gold", name: "Aniso Herringbone Gold", desc: "Herringbone gold directional grain with alternating chevron-angled polish — woven metal", swatch: "#ccaa66" },
    { id: "aniso_turbulence_metal", name: "Aniso Turbulence Metal", desc: "Turbulent flow metallic grain with chaotic swirling brush direction — wind-tunnel metal", swatch: "#8899bb" },
    // P4: Reactive Panels
    { id: "reactive_stealth_pop", name: "Reactive Stealth Pop", desc: "Matte stealth zones that pop to bright metallic in noise-driven regions — surprise flash", swatch: "#334455" },
    { id: "reactive_pearl_flash", name: "Reactive Pearl Flash", desc: "Soft pearl zones that flash to full mirror-metallic in reactive activation regions", swatch: "#8899aa" },
    { id: "reactive_candy_reveal", name: "Reactive Candy Reveal", desc: "Deep candy zones that reveal hidden chrome underneath in noise-triggered reveal areas", swatch: "#cc7799" },
    { id: "reactive_chrome_fade", name: "Reactive Chrome Fade", desc: "Bright chrome fading to soft satin in per-panel zones — mirror dissolving into matte", swatch: "#aabbcc" },
    { id: "reactive_matte_shine", name: "Reactive Matte Shine", desc: "Dead-flat matte base with bright metallic zones appearing in noise-driven hot spots", swatch: "#556677" },
    { id: "reactive_dual_tone", name: "Reactive Dual Tone", desc: "Two different metallic states alternating per-pixel — dual-personality reflective surface", swatch: "#778899" },
    { id: "reactive_ghost_metal", name: "Reactive Ghost Metal", desc: "Ghost metallic zones that appear and disappear in noise-driven activation regions", swatch: "#445566" },
    { id: "reactive_mirror_shadow", name: "Reactive Mirror Shadow", desc: "Mirror chrome zones with deep shadow regions creating dramatic light-trap contrast", swatch: "#667788" },
    { id: "reactive_warm_cold", name: "Reactive Warm Cold", desc: "Warm golden metallic vs cold blue-grey matte zones — temperature-coded material contrast", swatch: "#998877" },
    { id: "reactive_pulse_metal", name: "Reactive Pulse Metal", desc: "Pulsing metallic zone activation with rhythmic bright-to-dark metallic wave pattern", swatch: "#5566aa" },
    // P5: Sparkle Systems
    { id: "sparkle_diamond_dust", name: "Sparkle Diamond Dust", desc: "Ultra-fine diamond dust sparkle with thousands of micro-crystal points across the surface", swatch: "#ddeeff" },
    { id: "sparkle_starfield", name: "Sparkle Starfield", desc: "Sparse bright star-point sparkles on deep dark base — night sky with scattered pinpricks", swatch: "#112233" },
    { id: "sparkle_galaxy", name: "Sparkle Galaxy", desc: "Dense galaxy-cluster sparkle distribution with concentrated bright zones and dark voids", swatch: "#223344" },
    { id: "sparkle_firefly", name: "Sparkle Firefly", desc: "Rare ultra-bright sparkle flashes on dark green base — summer firefly field at dusk", swatch: "#445533" },
    { id: "sparkle_snowfall", name: "Sparkle Snowfall", desc: "Dense cold crystal sparkle field with icy white points on pale frozen base — fresh snow", swatch: "#ccddee" },
    { id: "sparkle_champagne", name: "Sparkle Champagne", desc: "Fine bubbly champagne sparkle with warm golden micro-points rising through pale base", swatch: "#ddcc99" },
    { id: "sparkle_meteor", name: "Sparkle Meteor", desc: "Directional meteor trail sparkle with streaked bright points all moving in one direction", swatch: "#cc8844" },
    { id: "sparkle_constellation", name: "Sparkle Constellation", desc: "Arranged sparkle star clusters forming bright groups with dark space between formations", swatch: "#334466" },
    { id: "sparkle_confetti", name: "Sparkle Confetti", desc: "Variable-size confetti sparkle with multi-colored bright points scattered in celebration", swatch: "#ee88cc" },
    { id: "sparkle_lightning_bug", name: "Sparkle Lightning Bug", desc: "Green-tinted bioluminescent glow points on dark base — warm summer lightning bug flicker", swatch: "#88cc44" },
    // P6: Multi-Scale Texture
    { id: "multiscale_chrome_grain", name: "Multi Chrome Grain", desc: "Chrome with layered macro and micro grain — two scales of brushing on mirror metal", swatch: "#ccddee" },
    { id: "multiscale_candy_frost", name: "Multi Candy Frost", desc: "Candy color with frost crystal overlay — deep wet candy under icy micro-detail texture", swatch: "#cc88aa" },
    { id: "multiscale_metal_grit", name: "Multi Metal Grit", desc: "Metal with layered coarse and fine grit — dual-scale abrasive texture on reflective base", swatch: "#889999" },
    { id: "multiscale_pearl_texture", name: "Multi Pearl Texture", desc: "Pearl shimmer with multi-scale surface texture — fine and coarse detail on iridescence", swatch: "#aabbcc" },
    { id: "multiscale_satin_weave", name: "Multi Satin Weave", desc: "Satin with woven fabric texture grain — soft sheen with visible thread micro-detail", swatch: "#99aabb" },
    { id: "multiscale_chrome_sand", name: "Multi Chrome Sand", desc: "Chrome with sand-blown texture overlay — mirror metal roughened by fine wind-blasted grit", swatch: "#bbccdd" },
    { id: "multiscale_matte_silk", name: "Multi Matte Silk", desc: "Dead-flat matte with silk micro-texture — ultra-smooth fabric feel on zero-gloss base", swatch: "#556666" },
    { id: "multiscale_flake_grain", name: "Multi Flake Grain", desc: "Metallic flake with directional grain — sparkle particles aligned in brush groove lines", swatch: "#aabb99" },
    { id: "multiscale_carbon_micro", name: "Multi Carbon Micro", desc: "Carbon fiber weave with micro-texture detail — visible tow structure plus surface grain", swatch: "#445555" },
    { id: "multiscale_frost_crystal", name: "Multi Frost Crystal", desc: "Frost surface with crystal micro-texture — ice formation with sharp geometric micro-facets", swatch: "#bbccdd" },
    // P7: Weather & Age
    { id: "weather_sun_fade", name: "Weather Sun Fade", desc: "UV sun fade gradient from bleached roof down to preserved lower panels — top-down damage", swatch: "#ccaa77" },
    { id: "weather_salt_spray", name: "Weather Salt Spray", desc: "Salt corrosion climbing from rocker panels upward — coastal rust and mineral deposits", swatch: "#889988" },
    { id: "weather_acid_rain", name: "Weather Acid Rain", desc: "Acid rain spot damage with circular etch marks and clearcoat failure dots across panels", swatch: "#88aa66" },
    { id: "weather_desert_blast", name: "Weather Desert Blast", desc: "Sand-pitting wear gradient with windward side showing heavy abrasion and surface erosion", swatch: "#ccbb88" },
    { id: "weather_ice_storm", name: "Weather Ice Storm", desc: "Ice crystal buildup from bottom with thick frozen accretion and cracked frost layers", swatch: "#aaccdd" },
    { id: "weather_road_spray", name: "Weather Road Spray", desc: "Dirty road spray wear from bottom up — stone chips, tar spots, and grime accumulation", swatch: "#776655" },
    { id: "weather_hood_bake", name: "Weather Hood Bake", desc: "Hood UV-baked damage gradient with severe clearcoat failure and chalking on flat areas", swatch: "#cc9966" },
    { id: "weather_barn_dust", name: "Weather Barn Dust", desc: "Dusty barn-stored haze coating with thick settled grime and protected areas underneath", swatch: "#998877" },
    { id: "weather_ocean_mist", name: "Weather Ocean Mist", desc: "Salt mist corrosion gradient with pitted metal and white mineral deposits on lower body", swatch: "#88aacc" },
    { id: "weather_volcanic_ash", name: "Weather Volcanic Ash", desc: "Volcanic ash fallout deposit with fine grey powder coating and abrasive grit accumulation", swatch: "#666655" },
    // P8: Exotic Physics
    { id: "exotic_glass_paint", name: "Exotic Glass Paint", desc: "FUSION — Caustic glass network with thin-film color shift creating jewel-like refractive depth across the panel surface", swatch: "#88AACC" },
    { id: "exotic_foggy_chrome", name: "Exotic Foggy Chrome", desc: "FUSION — Multi-scale condensation droplets over chrome with cold-mirror frost effect for moody atmospheric builds", swatch: "#CCDDEE" },
    { id: "exotic_inverted_candy", name: "Exotic Inverted Candy", desc: "FUSION — Deep candy coat with reversed highlight behavior; bright zones go dark and shadows pop with color", swatch: "#CC88DD" },
    { id: "exotic_liquid_glass", name: "Exotic Liquid Glass", desc: "FUSION — Ultra-smooth glass-like dielectric surface that pools like a fresh ceramic coat with deep optical clarity", swatch: "#AACCDD" },
    { id: "exotic_phantom_mirror", name: "Exotic Phantom Mirror", desc: "FUSION — Near-zero reflection with ghost interference pattern that hints at chrome without committing to a hard mirror", swatch: "#222233" },
    { id: "exotic_ceramic_void", name: "Exotic Ceramic Void", desc: "FUSION — Ultra-smooth ceramic with light-absorbing zones; the reflective surface contains pockets of pure void", swatch: "#334455" },
    { id: "exotic_anti_metal", name: "Exotic Anti Metal", desc: "FUSION — Dielectric surface with metallic interference bands; non-metal that flashes metallic at certain angles", swatch: "#AABBEE" },
    { id: "exotic_crystal_clear", name: "Exotic Crystal Clear", desc: "FUSION — Crystal-clear surface with prismatic refraction that splits white light into rainbow fringes at edges", swatch: "#BBCCDD" },
    { id: "exotic_dark_glass", name: "Exotic Dark Glass", desc: "FUSION — Dark tinted glass with deep metallic undertone for stealth-luxury builds with hidden reflective depth", swatch: "#334455" },
    { id: "exotic_wet_void", name: "Exotic Wet Void", desc: "FUSION — Wet-look surface with light-trapping depth that pulls reflections inward like a black-hole event horizon", swatch: "#223344" },
    // P9: Tri-Zone Materials
    { id: "trizone_chrome_candy_matte", name: "TriZone Chrome/Candy/Matte", desc: "Three materials in noise zones — mirror chrome, deep candy, and flat matte compete for space", swatch: "#aabbcc" },
    { id: "trizone_pearl_carbon_gold", name: "TriZone Pearl/Carbon/Gold", desc: "Pearl shimmer, carbon fiber, and gold metallic in noise-driven zones across the surface", swatch: "#99aa88" },
    { id: "trizone_frozen_ember_chrome", name: "TriZone Frozen/Ember/Chrome", desc: "Frozen ice, hot ember glow, and mirror chrome competing in noise-separated surface zones", swatch: "#88aacc" },
    { id: "trizone_anodized_candy_silk", name: "TriZone Anodized/Candy/Silk", desc: "Anodized oxide, candy transparency, and silk satin in three noise-driven material zones", swatch: "#8899aa" },
    { id: "trizone_vanta_chrome_pearl", name: "TriZone Vanta/Chrome/Pearl", desc: "Vantablack, mirror chrome, and soft pearl in dramatic three-zone high-contrast material", swatch: "#334466" },
    { id: "trizone_glass_metal_matte", name: "TriZone Glass/Metal/Matte", desc: "Transparent glass, reflective metal, and flat matte in noise-driven dominance zones", swatch: "#778899" },
    { id: "trizone_mercury_obsidian_candy", name: "TriZone Mercury/Obsidian/Candy", desc: "Liquid mercury, dark obsidian, and candy color in three flowing noise-driven zones", swatch: "#889999" },
    { id: "trizone_titanium_copper_chrome", name: "TriZone Titanium/Copper/Chrome", desc: "Warm titanium, rich copper, and mirror chrome in three noise-separated metallic zones", swatch: "#aa9988" },
    { id: "trizone_ceramic_flake_satin", name: "TriZone Ceramic/Flake/Satin", desc: "Smooth ceramic, metallic flake sparkle, and soft satin in three noise-driven zones", swatch: "#7788aa" },
    { id: "trizone_stealth_spectra_frozen", name: "TriZone Stealth/Spectra/Frozen", desc: "Stealth matte, vivid spectraflame, and frozen crystal in three dramatic material zones", swatch: "#556688" },
    // P10: Depth Illusion
    { id: "depth_canyon", name: "Depth Canyon", desc: "Deep canyon crevice depth illusion with dark valley shadows and bright ridge highlights", swatch: "#667788" },
    { id: "depth_bubble", name: "Depth Bubble", desc: "Spherical bubble depth illusion with raised dome highlights and curved shadow falloff", swatch: "#88aacc" },
    { id: "depth_ripple", name: "Depth Ripple", desc: "Water ripple ring depth effect with concentric wave shadows radiating from impact point", swatch: "#7799bb" },
    { id: "depth_scale", name: "Depth Scale", desc: "Fish scale depth illusion with overlapping curved plates and crescent shadow underneath", swatch: "#889999" },
    { id: "depth_honeycomb", name: "Depth Honeycomb", desc: "Hexagonal honeycomb hole depth effect with dark recessed cells and bright flat rims", swatch: "#99aa88" },
    { id: "depth_crack", name: "Depth Crack", desc: "Earthquake crack depth illusion with dark fissures cutting deep into the surface plane", swatch: "#556666" },
    { id: "depth_wave", name: "Depth Wave", desc: "Ocean wave undulation depth with rolling peaks and deep trough shadows across surface", swatch: "#6688aa" },
    { id: "depth_pillow", name: "Depth Pillow", desc: "Pillow quilt puffiness depth with soft rounded mounds and stitched-valley shadow lines", swatch: "#8899aa" },
    { id: "depth_vortex", name: "Depth Vortex", desc: "Spiral vortex drain depth with twisting funnel pulling the surface into a dark center", swatch: "#556688" },
    { id: "depth_erosion", name: "Depth Erosion", desc: "Erosion channel depth illusion with water-carved groove shadows and worn ridge highlights", swatch: "#778888" },
    // P11: Metallic Halos
    { id: "halo_hex_chrome", name: "Halo Hex Chrome", desc: "Hex grid with bright chrome halo rims surrounding each dark cell — honeycomb metal glow", swatch: "#aabbdd" },
    { id: "halo_scale_gold", name: "Halo Scale Gold", desc: "Scale pattern with warm gold halos rimming each overlapping plate — gilded dragon armor", swatch: "#ccaa66" },
    { id: "halo_circle_pearl", name: "Halo Circle Pearl", desc: "Circle pattern with soft pearl halos ringing each dot — luminous bubble array on surface", swatch: "#aabbcc" },
    { id: "halo_diamond_chrome", name: "Halo Diamond Chrome", desc: "Diamond pattern with chrome halos framing each facet — gemstone grid mirror reflection", swatch: "#bbccdd" },
    { id: "halo_voronoi_metal", name: "Halo Voronoi Metal", desc: "Voronoi cells with metallic halo rims — organic cell boundaries glowing with bright metal", swatch: "#8899bb" },
    { id: "halo_wave_candy", name: "Halo Wave Candy", desc: "Wave crests with candy-colored halos — warm transparent glow rimming each wave peak", swatch: "#cc88aa" },
    { id: "halo_crack_chrome", name: "Halo Crack Chrome", desc: "Crack network with chrome halos along fracture lines — bright metal in shattered seams", swatch: "#aabbcc" },
    { id: "halo_star_metal", name: "Halo Star Metal", desc: "Star points with metallic halos radiating from each tip — bright metal starburst pattern", swatch: "#99aacc" },
    { id: "halo_grid_pearl", name: "Halo Grid Pearl", desc: "Grid pattern with soft pearl halos at every intersection — luminous lattice on dark base", swatch: "#aabbbb" },
    { id: "halo_ripple_chrome", name: "Halo Ripple Chrome", desc: "Ripple rings with chrome halos on each wave crest — concentric mirror circles on surface", swatch: "#bbccdd" },
    // P12: Light Waves
    { id: "wave_chrome_tide", name: "Wave Chrome Tide", desc: "Low-frequency chrome wave with broad rolling metallic tide bands sweeping across surface", swatch: "#ccddee" },
    { id: "wave_candy_flow", name: "Wave Candy Flow", desc: "Medium-frequency candy flow bands with warm transparent color undulating across panels", swatch: "#cc88aa" },
    { id: "wave_pearl_current", name: "Wave Pearl Current", desc: "Low-frequency pearl current waves with slow iridescent shimmer bands rolling across body", swatch: "#aabbcc" },
    { id: "wave_metallic_pulse", name: "Wave Metallic Pulse", desc: "High-frequency metallic pulse with tight rapid reflective oscillation across the surface", swatch: "#99aabb" },
    { id: "wave_dual_frequency", name: "Wave Dual Frequency", desc: "Low and high frequency combined wave creating complex metallic interference beat pattern", swatch: "#8899aa" },
    { id: "wave_diagonal_sweep", name: "Wave Diagonal Sweep", desc: "Diagonal wave sweep with angled metallic bands flowing corner to corner across the body", swatch: "#aabbcc" },
    { id: "wave_circular_radar", name: "Wave Circular Radar", desc: "Radial radar-scan wave with rotating metallic sweep ring expanding outward from center", swatch: "#7799bb" },
    { id: "wave_turbulent_flow", name: "Wave Turbulent Flow", desc: "Chaotic turbulent wave with unpredictable metallic flow and swirling current zones", swatch: "#8899bb" },
    { id: "wave_standing_chrome", name: "Wave Standing Chrome", desc: "Standing-wave chrome interference with fixed bright nodes and dark antinodes on surface", swatch: "#bbccdd" },
    { id: "wave_moire_metal", name: "Wave Moiré Metal", desc: "Moire interference metal bands with overlapping wave grids creating shifting beat pattern", swatch: "#99aabb" },
    // P13: Fractal Chaos
    { id: "fractal_chrome_decay", name: "Fractal Chrome Decay", desc: "Four-octave fractal noise driving chrome-to-matte decay — organic erosion of mirror finish", swatch: "#aabbcc" },
    { id: "fractal_candy_chaos", name: "Fractal Candy Chaos", desc: "Three-octave fractal noise mixing candy transparency zones — chaotic depth variation", swatch: "#cc88aa" },
    { id: "fractal_pearl_cloud", name: "Fractal Pearl Cloud", desc: "Four-octave fractal pearl cloud formation with soft iridescent zones in organic shapes", swatch: "#aabbcc" },
    { id: "fractal_metallic_storm", name: "Fractal Metallic Storm", desc: "Five-octave metallic storm chaos with extreme multi-scale turbulent reflective variation", swatch: "#8899bb" },
    { id: "fractal_matte_chrome", name: "Fractal Matte Chrome", desc: "Four-octave fractal spanning full matte-to-chrome range — maximum material contrast", swatch: "#99aabb" },
    { id: "fractal_warm_cold", name: "Fractal Warm Cold", desc: "Three-octave warm-cold material fractal — gold metallic vs blue matte in organic zones", swatch: "#aa8877" },
    { id: "fractal_deep_organic", name: "Fractal Deep Organic", desc: "Four-octave deep organic texture fractal with natural growth-pattern material variation", swatch: "#667766" },
    { id: "fractal_electric_noise", name: "Fractal Electric Noise", desc: "Five-octave electric noise chaos with intense high-frequency metallic sparkle turbulence", swatch: "#6688cc" },
    { id: "fractal_cosmic_dust", name: "Fractal Cosmic Dust", desc: "Four-octave cosmic dust distribution with nebula-like metallic particle cloud formation", swatch: "#556688" },
    { id: "fractal_liquid_fire", name: "Fractal Liquid Fire", desc: "Three-octave liquid fire fractal with flowing molten zones and cooled dark crust edges", swatch: "#cc6633" },
    // P14: Spectral Reactive
    { id: "spectral_rainbow_metal", name: "Spectral Rainbow Metal", desc: "Full HSV rainbow cycle mapped to metallic — every hue gets its own unique reflectivity", swatch: "#ee88cc" },
    { id: "spectral_warm_cool", name: "Spectral Warm Cool", desc: "Binary warm-cool material zones — warm tones get bright metallic, cool tones stay matte", swatch: "#aa7788" },
    { id: "spectral_dark_light", name: "Spectral Dark Light", desc: "Value-reactive material mapping where dark areas go matte and light areas go chrome", swatch: "#889999" },
    { id: "spectral_sat_metal", name: "Spectral Sat Metal", desc: "Saturation-reactive metallic where vivid colors go mirror-bright and muted areas go flat", swatch: "#99aaaa" },
    { id: "spectral_complementary", name: "Spectral Complementary", desc: "Hue-pair complementary system where opposing colors get contrasting material properties", swatch: "#88aa88" },
    { id: "spectral_neon_reactive", name: "Spectral Neon Reactive", desc: "Brightness-reactive neon specular where bright zones get intense metallic pop and glow", swatch: "#44cc88" },
    { id: "spectral_earth_sky", name: "Spectral Earth Sky", desc: "Earth-sky temperature mapping — warm earth tones vs cool sky tones drive material zones", swatch: "#88aa77" },
    { id: "spectral_mono_chrome", name: "Spectral Mono Chrome", desc: "Value-to-metallic monochrome where brightness controls reflectivity — greyscale metal", swatch: "#aabbcc" },
    { id: "spectral_prismatic_flip", name: "Spectral Prismatic Flip", desc: "Tri-spectral zone prism flip with three color bands each driving different material state", swatch: "#cc88ee" },
    { id: "spectral_inverse_logic", name: "Spectral Inverse Logic", desc: "Inverted spectral logic where expected material assignments are deliberately reversed", swatch: "#7799aa" },
    // P15: Panel Quilting
    { id: "quilt_chrome_mosaic", name: "Quilt Chrome Mosaic", desc: "Small chrome mosaic tiles in a tight grid — each tile a separate mirror fragment on base", swatch: "#bbccdd" },
    { id: "quilt_candy_tiles", name: "Quilt Candy Tiles", desc: "Candy-colored material tile grid with each square showing different transparent depth", swatch: "#cc88aa" },
    { id: "quilt_pearl_patchwork", name: "Quilt Pearl Patchwork", desc: "Pearl material patchwork quilt with each small patch showing unique iridescent shimmer", swatch: "#aabbcc" },
    { id: "quilt_metallic_pixels", name: "Quilt Metallic Pixels", desc: "Tiny metallic pixel mosaic with each micro-tile showing different reflective intensity", swatch: "#99aabb" },
    { id: "quilt_hex_variety", name: "Quilt Hex Variety", desc: "Hexagonal tile material variety with each hex cell assigned different metallic property", swatch: "#8899aa" },
    { id: "quilt_diamond_shimmer", name: "Quilt Diamond Shimmer", desc: "Diamond-shaped shimmer tiles with alternating bright and subtle metallic facets in grid", swatch: "#aabbcc" },
    { id: "quilt_random_chaos", name: "Quilt Random Chaos", desc: "Tiny fully random material chaos tiles — each micro-square gets unpredictable finish", swatch: "#889999" },
    { id: "quilt_gradient_tiles", name: "Quilt Gradient Tiles", desc: "Large gradient material tiles where each square fades between two different finish types", swatch: "#99aabb" },
    { id: "quilt_alternating_duo", name: "Quilt Alternating Duo", desc: "Alternating duo-material checkerboard with two contrasting finishes in neat tile pattern", swatch: "#8899bb" },
    { id: "quilt_organic_cells", name: "Quilt Organic Cells", desc: "Voronoi organic cell materials with irregular natural shapes each holding unique finish", swatch: "#7799aa" },
    // Chromatic Flake Collection — multi-color micro-flake shimmer (30 palettes)
    { id: "cf_midnight_galaxy", name: "CF: Midnight Galaxy", desc: "Deep navy, electric purple, teal, silver, dark magenta micro-flake shimmer", swatch: "#1a1a44" },
    { id: "cf_volcanic_ember", name: "CF: Volcanic Ember", desc: "Deep red, burnt orange, gold, charcoal, crimson multi-flake fire shimmer", swatch: "#8b2500" },
    { id: "cf_arctic_aurora", name: "CF: Arctic Aurora", desc: "Ice blue, mint green, lavender, white, pale cyan crystalline flake", swatch: "#c8e8ff" },
    { id: "cf_black_opal", name: "CF: Black Opal", desc: "Black, deep green, deep blue, purple flash, copper — precious stone flake", swatch: "#0a0a12" },
    { id: "cf_dragon_scale", name: "CF: Dragon Scale", desc: "Emerald, gold, dark red, bronze, olive — ancient reptilian flake", swatch: "#2a6030" },
    { id: "cf_toxic_nebula", name: "CF: Toxic Nebula", desc: "Neon green, black, electric purple, acid yellow, dark teal biohazard flake", swatch: "#22cc44" },
    { id: "cf_rose_gold_dust", name: "CF: Rose Gold Dust", desc: "Rose pink, gold, copper, cream, blush — luxury micro-flake dust", swatch: "#e8a0a0" },
    { id: "cf_deep_space", name: "CF: Deep Space", desc: "Black, deep blue, purple, silver sparkle, dark teal — cosmic void flake", swatch: "#0a0a1a" },
    { id: "cf_phoenix_feather", name: "CF: Phoenix Feather", desc: "Orange, red, gold, amber, dark scarlet — burning plumage flake", swatch: "#ee6622" },
    { id: "cf_frozen_mercury", name: "CF: Frozen Mercury", desc: "Silver, ice blue, platinum, pearl white, steel grey — liquid metal flake", swatch: "#c8ccd0" },
    { id: "cf_jungle_venom", name: "CF: Jungle Venom", desc: "Dark green, lime, black, gold, toxic yellow — serpent scale flake", swatch: "#1a4020" },
    { id: "cf_cobalt_storm", name: "CF: Cobalt Storm", desc: "Deep blue, electric blue, slate, silver, navy — thunderstorm flake", swatch: "#1a2266" },
    { id: "cf_sunset_strip", name: "CF: Sunset Strip", desc: "Coral, magenta, gold, peach, deep orange — Hollywood boulevard flake", swatch: "#ee6655" },
    { id: "cf_absinthe_dreams", name: "CF: Absinthe Dreams", desc: "Chartreuse, dark green, gold, emerald, black — green fairy flake", swatch: "#88aa20" },
    { id: "cf_titanium_rain", name: "CF: Titanium Rain", desc: "Gunmetal, silver, dark grey, blue-grey, platinum — industrial metal flake", swatch: "#707880" },
    { id: "cf_blood_moon", name: "CF: Blood Moon", desc: "Dark crimson, orange, black, deep red, rust — lunar eclipse flake", swatch: "#550808" },
    { id: "cf_peacock_strut", name: "CF: Peacock Strut", desc: "Teal, royal blue, emerald, gold, deep purple — iridescent feather flake", swatch: "#1a8888" },
    { id: "cf_champagne_frost", name: "CF: Champagne Frost", desc: "Pale gold, cream, silver, champagne, pearl — elegant celebration flake", swatch: "#e8dcc0" },
    { id: "cf_neon_viper", name: "CF: Neon Viper", desc: "Hot pink, electric blue, neon green, black, purple — aggressive neon flake", swatch: "#ee22aa" },
    { id: "cf_obsidian_fire", name: "CF: Obsidian Fire", desc: "Black, dark red, orange glow, charcoal, ember — volcanic glass flake", swatch: "#1a0808" },
    { id: "cf_mermaid_scale", name: "CF: Mermaid Scale", desc: "Aqua, purple, teal, silver, seafoam — underwater shimmer flake", swatch: "#44ccbb" },
    { id: "cf_carbon_prizm", name: "CF: Carbon Prizm", desc: "Charcoal base with subtle rainbow color-shift micro-flake", swatch: "#333340" },
    { id: "cf_molten_copper", name: "CF: Molten Copper", desc: "Copper, bronze, gold, burnt orange, dark brown — liquid forge flake", swatch: "#cc7744" },
    { id: "cf_electric_storm", name: "CF: Electric Storm", desc: "Purple, electric blue, white flash, dark grey, violet — lightning flake", swatch: "#6644cc" },
    { id: "cf_desert_mirage", name: "CF: Desert Mirage", desc: "Sand gold, terracotta, dusty rose, sage, camel — arid shimmer flake", swatch: "#ccaa77" },
    { id: "cf_venom_strike", name: "CF: Venom Strike", desc: "Acid green, black, neon yellow, dark emerald, lime — toxic attack flake", swatch: "#44ee22" },
    { id: "cf_sapphire_ice", name: "CF: Sapphire Ice", desc: "Deep sapphire, ice blue, white, crystal blue, navy — frozen gem flake", swatch: "#2244aa" },
    { id: "cf_inferno_chrome", name: "CF: Inferno Chrome", desc: "Chrome silver, fire red, orange, gold, dark steel — blazing metal flake", swatch: "#cc4422" },
    { id: "cf_phantom_violet", name: "CF: Phantom Violet", desc: "Deep violet, silver, black, lavender, dark purple — spectral flake", swatch: "#3a1870" },
    { id: "cf_solar_flare", name: "CF: Solar Flare", desc: "Bright gold, white-hot, amber, orange, deep yellow — stellar eruption flake", swatch: "#eeaa22" },
    // ===== Research Session 6: 6 New Monolithic Finishes =====
    { id: "aurora_borealis_mono", name: "Aurora Borealis Curtains", desc: "Flowing curtains of green, teal, and purple northern-lights light play — near-black base with sinusoidal band variation, R=230–255, G=30–80 smooth curtain structure", swatch: "#0d2018" },
    { id: "deep_space_void", name: "Deep Space Void", desc: "Absolute black base with ultra-sparse mirror-bright star points — near-total void with occasional blinding metallic highlights, maximum void/contrast", swatch: "#050508" },
    { id: "polished_obsidian_mono", name: "Polished Obsidian", desc: "Volcanic glass — pure black, zero metallic, maximum clearcoat gloss — the anti-chrome: dark environment reflections in a deep black mirror surface", swatch: "#08080a" },
    { id: "patinated_bronze", name: "Patinated Bronze", desc: "Ancient bronze with verdigris oxidation — warm dark metallic bronze base with turquoise-green patina zones in surface recesses, two-zone color/spec generation", swatch: "#5a3a1a" },
    { id: "reactive_plasma", name: "Reactive Plasma", desc: "High-energy plasma discharge — electric-blue and violet lightning tendrils against near-black base; tendril zones R=240–255 G=0–10 mirror-chrome, background near-black non-metallic", swatch: "#0a0514" },
    { id: "molten_metal", name: "Molten Metal", desc: "Just-solidified forge metal — bright orange-gold at hot rear/edges (R=230–255, G=20–40), cooling to dark bronze-grey toward front; heat-state color and spec from same gradient", swatch: "#cc5511" },
    // ── INTRICATE & ORNATE — Batch 1 (moved from SPEC_PATTERNS where they were misplaced)
    { id: "hex_mandala", name: "Hex Mandala", desc: "Hex interference — three 120°-offset cosine waves produce concentric hexagonal ring mandalas", swatch: "#ccaa55" },
    { id: "lace_filigree", name: "Lace Filigree", desc: "Delicate interlaced openwork — orthogonal and 45° sinusoidal grids combine for intricate lacework threads", swatch: "#ddccbb" },
    { id: "brushed_metal_fine", name: "Brushed Metal Fine", desc: "Three-frequency directional micro-scratch brushing — very fine anisotropic grain lines like bead-blasted aluminum", swatch: "#aabbcc" },
    { id: "carbon_3k_weave", name: "Carbon 3K Weave", desc: "3K satin-braid diagonal carbon — two interleaved 45° diagonal tow directions vs the standard 2×2 twill", swatch: "#223344" },
    { id: "honeycomb_organic", name: "Honeycomb Organic", desc: "Warped organic honeycomb — 3-wave hex pattern distorted by noise warp for irregular natural cell shapes", swatch: "#ddaa44" },
    { id: "baroque_scrollwork", name: "Baroque Scrollwork", desc: "Ornate spiral scrollwork — Archimedean scrolls and sinusoidal flourishes layered for classical baroque decoration", swatch: "#aa8833" },
    { id: "art_nouveau_vine", name: "Art Nouveau Vine", desc: "Flowing vine tendrils — sinuous stems with branching tendrils in Art Nouveau organic plant style", swatch: "#557744" },
    { id: "penrose_quasi", name: "Penrose Quasicrystal", desc: "5-fold quasicrystal tiling — five cosine projections at 72° spacing approximate aperiodic Penrose geometry", swatch: "#6655aa" },
    { id: "topographic_dense", name: "Topographic Dense", desc: "Dense contour lines — 35 contour bands over a multi-scale noise height field, very fine map-like striping", swatch: "#448866" },
    { id: "interference_rings", name: "Interference Rings", desc: "Newton's ring multi-source interference — four offset radial sources create moiré-like concentric ring beating", swatch: "#66aacc" }
].filter(m => !REMOVED_SPECIAL_IDS.has(m.id));

// ============================================================
// SPEC PATTERNS — stackable spec map overlays
// ============================================================
const SPEC_PATTERNS = [
    { id: "banded_rows", name: "Banded Rows", desc: "Adds horizontal metallic/roughness bands with soft feathered transitions between value zones", category: "Structure", defaults: { num_bands: 50, palette_size: 10 } },
    { id: "flake_scatter", name: "Flake Scatter", desc: "Scatters sparse metallic flake particles across the surface for random point-sparkle highlights", category: "Metallic", defaults: { density: 0.02, flake_radius: 2 } },
    { id: "depth_gradient", name: "Depth Gradient", desc: "Creates coating thickness variation from gravity pooling — thicker at bottom affects roughness and gloss", category: "Coating", defaults: { direction: "vertical" } },
    { id: "orange_peel_texture", name: "Orange Peel", desc: "Adds spray-coat orange peel micro-bump roughness texture simulating real automotive paint surface", category: "Texture", defaults: { cell_size: 6 } },
    { id: "wear_scuff", name: "Wear & Scuff", desc: "Applies localized roughness patches and directional scuff streaks that break up clearcoat smoothness", category: "Weathering", defaults: { wear_density: 0.3 } },
    { id: "aniso_grain", name: "Aniso Grain", desc: "Creates directional brushing and grinding lines that affect roughness in one orientation — anisotropic", category: "Texture", defaults: { direction: "horizontal" } },
    { id: "interference_bands", name: "Interference Bands", desc: "Adds thin-film iridescent metallic banding that shifts reflectivity in periodic color-like waves", category: "Optical", defaults: { frequency: 8.0 } },
    { id: "concentric_ripple", name: "Concentric Ripple", desc: "Generates expanding roughness rings from random center points — water droplet impact interference", category: "Structure", defaults: { num_centers: 3, ring_freq: 15.0 } },
    { id: "hex_cells", name: "Hex Cells", desc: "Applies honeycomb hexagonal cell grid with per-cell metallic and roughness variation for tiled texture", category: "Structure", defaults: { cell_size: 20 } },
    { id: "marble_vein", name: "Marble Vein", desc: "Creates organic roughness veining like natural stone — smooth face with rough vein channel grooves", category: "Organic", defaults: { vein_freq: 6.0, turbulence: 3 } },
    { id: "cloud_wisps", name: "Cloud Wisps", desc: "Adds fractal cloud formation noise that modulates roughness in soft organic billowing shapes", category: "Organic", defaults: { num_octaves: 5 } },
    { id: "micro_sparkle", name: "Micro Sparkle", desc: "Applies ultra-fine dense metallic pigment grain that adds overall sparkle to the metallic channel", category: "Metallic", defaults: { density: 0.15 } },
    { id: "panel_zones", name: "Panel Zones", desc: "Defines large irregular zones with different metallic and roughness values — panel color variation", category: "Structure", defaults: { num_zones: 25 } },
    { id: "spiral_sweep", name: "Spiral Sweep", desc: "Creates logarithmic spiral arms from center that modulate metallic reflection in rotational sweep", category: "Optical", defaults: { num_arms: 4 } },
    // 2026-04-19 HEENAN HP2 — id `carbon_weave` was a TRIPLE collision:
    // BASES (L291), PATTERNS (L695), and SPEC_PATTERNS (here). Spec-pattern
    // siblings already use the `spec_*` namespace (spec_kevlar_weave,
    // spec_wood_burl, spec_carbon_2x2_twill, etc.). Renamed to spec_carbon_weave
    // to match that convention; updated SPEC_PATTERN_GROUPS["Misc"] reference.
    { id: "spec_carbon_weave", name: "Carbon Weave (Spec)", desc: "Adds woven fiber crosshatch roughness pattern simulating carbon fiber surface texture on spec maps", category: "Texture", defaults: { weave_size: 12 } },
    { id: "crackle_network", name: "Crackle Network", desc: "Creates crack and craze roughness network like dried clay — sharp channels cut through smooth surface", category: "Weathering", defaults: { cell_count: 25 } },
    { id: "flow_lines", name: "Flow Lines", desc: "Adds fluid paint flow stream roughness — directional drip lines that affect clearcoat thickness", category: "Coating", defaults: { num_streams: 40 } },
    { id: "micro_facets", name: "Micro Facets", desc: "Creates tiny angled facets like crushed crystal that scatter metallic reflection at random micro-angles", category: "Texture", defaults: { facet_size: 8 } },
    { id: "moire_overlay", name: "Moire Overlay", desc: "Overlaps two metallic grids at slight angle offset creating moire interference fringe modulation", category: "Optical", defaults: { grid1_freq: 60 } },
    { id: "pebble_grain", name: "Pebble Grain", desc: "Adds large rounded roughness bumps like leather pebble grain — dimpled surface texture variation", category: "Texture", defaults: { pebble_size: 5 } },
    { id: "radial_sunburst", name: "Radial Sunburst", desc: "Creates metallic rays emanating from center point outward — radial reflection gradient like sunburst", category: "Structure", defaults: { num_rays: 12 } },
    { id: "topographic_steps", name: "Topo Steps", desc: "Applies contour-line stepped roughness levels creating terraced elevation bands across the surface", category: "Structure", defaults: { num_levels: 8 } },
    { id: "wave_ripple", name: "Wave Ripple", desc: "Adds directional water surface interference waves that modulate roughness in flowing ripple bands", category: "Optical", defaults: { num_waves: 5 } },
    { id: "patina_bloom", name: "Patina Bloom", desc: "Creates circular roughness bloom spots from simulated chemical oxidation reaction on the surface", category: "Weathering", defaults: { num_blooms: 80 } },
    { id: "electric_branches", name: "Electric Branches", desc: "Generates branching tree and lightning roughness patterns — fractal discharge paths across clearcoat", category: "Organic", defaults: { num_trees: 10, branch_depth: 12 } },
    // --- NEW PATTERNS (26-50) ---
    { id: "voronoi_fracture", name: "Voronoi Fracture", desc: "Shattered glass cell boundaries with dark fracture lines", category: "Crystalline", defaults: { num_cells: 200, edge_width: 1.0 } },
    { id: "plasma_turbulence", name: "Plasma Turbulence", desc: "Hot plasma energy field with chaotic swirling metallic turbulence — intense sci-fi surface modulation", category: "Optical", defaults: { octaves: 6, freq_base: 3.0 } },
    { id: "diamond_lattice", name: "Diamond Lattice", desc: "Geometric diamond grid with per-cell depth modulation — engraved facet array that catches highlights at panel-rotation angles", category: "Crystalline", defaults: { cell_size: 24, depth_variation: 0.4 } },
    { id: "acid_etch", name: "Acid Etch", desc: "Chemical dissolution eating through coating layers — pitted clearcoat damage from acid rain or industrial fallout exposure", category: "Weathering", defaults: { intensity: 0.6, blob_count: 150 } },
    { id: "galaxy_swirl", name: "Galaxy Swirl", desc: "Creates spiral galaxy arm metallic patterns with scattered star cluster highlight points throughout", category: "Optical", defaults: { num_arms: 4, twist: 3.0 } },
    { id: "reptile_scale", name: "Reptile Scale", desc: "Overlapping biological scales with angle-based specularity", category: "Organic", defaults: { scale_size: 18, overlap: 0.3 } },
    { id: "magnetic_field", name: "Magnetic Field", desc: "Generates iron filing roughness lines curving between magnetic pole points — electromagnetic texture", category: "Kinetic", defaults: { num_poles: 8, line_density: 60.0 } },
    { id: "prismatic_shatter", name: "Prismatic Shatter", desc: "Shattered prism fragments reflecting at different angles", category: "Crystalline", defaults: { num_shards: 300 } },
    { id: "neural_dendrite", name: "Neural Dendrite", desc: "Creates branching neural network metallic patterns with synaptic fire nodes — organic tech overlay", category: "Organic", defaults: { num_neurons: 5, branch_depth: 7 } },
    { id: "heat_distortion", name: "Heat Distortion", desc: "Adds rising convection shimmer waves that modulate roughness like heat distortion over hot asphalt", category: "Kinetic", defaults: { wave_count: 40, turbulence: 8.0 } },
    { id: "rust_bloom", name: "Rust Bloom (Spots)", desc: "Expanding oxidation circles with jagged corrosion fronts", category: "Weathering", defaults: { num_spots: 25, max_radius: 50 } },
    { id: "quantum_noise", name: "Quantum Noise", desc: "Standing wave interference — probability density clouds", category: "Optical", defaults: { num_waves: 120 } },
    { id: "woven_mesh", name: "Woven Mesh", desc: "Interlocking thread mesh with over/under spec variation — fabric-grade weave that adds tactile texture detail to clearcoat", category: "Texture", defaults: { thread_spacing: 10, thread_width: 3 } },
    { id: "lava_crack", name: "Lava Crack", desc: "Cooling lava plates with bright glowing fissures between", category: "Organic", defaults: { num_plates: 35, glow_width: 4.0 } },
    // 2026-04-19 HEENAN HP3 — id `diffraction_grating` collided with PATTERNS
    // (L845). Renamed SPEC_PATTERNS entry to spec_diffraction_grating_cd
    // (sister to spec_diffraction_grating which already exists in Optical).
    // TF13 had already disambiguated the display name; this completes the fix
    // at the id level. SPEC_PATTERN_GROUPS["Optical"] updated accordingly.
    { id: "spec_diffraction_grating_cd", name: "Diffraction Grating (CD)", desc: "Fine parallel ruling lines — CD surface rainbow diffraction", category: "Optical", defaults: { line_freq: 80.0, num_orders: 5 } },
    { id: "sand_dune", name: "Sand Dune", desc: "Creates wind-sculpted asymmetric roughness ripples with steep slip faces — desert dune surface texture", category: "Texture", defaults: { dune_freq: 15.0, wind_angle: 0.3 } },
    { id: "circuit_trace", name: "Circuit Trace", desc: "Adds PCB Manhattan-routed metallic traces with solder pad nodes — circuit board reflection pattern", category: "Structure", defaults: { trace_count: 200 } },
    // 2026-04-19 HEENAN H4HR-4 — `oil_slick` collided with MONOLITHICS L1354.
    // SPEC entry namespaced; HP-MIGRATE handles backward compat. MONO keeps id.
    { id: "spec_oil_slick", name: "Oil Slick (Spec)", desc: "Thin-film oil interference with organic flowing pools — rainbow surface fringe like gasoline on a wet parking lot", category: "Coating", defaults: { num_pools: 8, freq: 6.0 } },
    { id: "meteor_impact", name: "Meteor Impact", desc: "Radial crater with ejecta rays and concentric shockwaves", category: "Kinetic", defaults: { num_craters: 12 } },
    { id: "fungal_network", name: "Fungal Network", desc: "Mycelium threads — delicate interconnected branching web", category: "Organic", defaults: { num_hyphae: 60 } },
    // 2026-04-19 HEENAN H4HR-5 — `gravity_well` collided with MONOLITHICS L1562.
    { id: "spec_gravity_well", name: "Gravity Well (Spec)", desc: "Spacetime warping around singularity — lensing distortion", category: "Optical", defaults: { num_wells: 6 } },
    { id: "sonic_boom", name: "Sonic Boom", desc: "Generates Mach cone shockwave roughness interference patterns radiating from supersonic source points", category: "Kinetic", defaults: { num_sources: 8 } },
    { id: "crystal_growth", name: "Crystal Growth (Frost)", desc: "Dendritic frost crystallization — 6-fold branching symmetry", category: "Crystalline", defaults: { num_seeds_pts: 4, growth_steps: 200 } },
    { id: "smoke_tendril", name: "Smoke Tendril", desc: "Rising smoke plumes with turbulent billowing expansion — atmospheric haze overlay for moody fog-on-paint effects", category: "Coating", defaults: { num_plumes: 20 } },
    { id: "fractal_discharge", name: "Fractal Discharge", desc: "Recursive branching electrical discharge — dense energy web", category: "Optical", defaults: { num_bolts: 15, depth: 14 } },
    // --- NEW PATTERNS (51-65) ---
    // Sparkle / Flake variants
    { id: "diamond_dust", name: "Diamond Dust", desc: "Thousands of tiny bright points on a dark field — crushed diamond ultra-fine sparkle", category: "Sparkle", defaults: { density: 0.025 } },
    { id: "metallic_sand", name: "Metallic Sand", desc: "Fine 2px block-quantized metallic sand particles — slightly larger than diamond dust", category: "Sparkle", defaults: { block_size: 2 } },
    { id: "holographic_flake", name: "Holographic Flake", desc: "Iridescent flakes with position-modulated brightness — rainbow prismatic scatter", category: "Sparkle", defaults: { density: 0.02, freq_x: 35.0, freq_y: 28.0 } },
    { id: "crystal_shimmer", name: "Crystal Shimmer", desc: "Small Voronoi facets with edge darkening — angular crystal reflections", category: "Sparkle", defaults: { cell_size: 10, edge_width: 0.25 } },
    { id: "stardust_fine", name: "Stardust Fine", desc: "Extremely fine high-density sparkle — like a star-filled night sky", category: "Sparkle", defaults: { density: 0.05 } },
    { id: "pearl_micro", name: "Pearl Micro", desc: "Soft pearlescent micro-texture — smooth undulating mother-of-pearl iridescence", category: "Sparkle", defaults: { octaves: 4 } },
    { id: "gold_flake", name: "Gold Flake", desc: "Large sparse irregular gold-leaf style flakes — bright fragments on a dark field", category: "Sparkle", defaults: { density1: 0.6, density2: 0.5 } },
    { id: "brushed_sparkle", name: "Brushed Sparkle", desc: "Directional anisotropic brushed grain with embedded random sparkle points", category: "Sparkle", defaults: { sparkle_density: 0.002 } },
    { id: "crushed_glass", name: "Crushed Glass", desc: "Jagged angular bright fragments — sharp high-frequency thresholding, not smooth", category: "Sparkle", defaults: { threshold_hi: 0.55 } },
    { id: "sparkle_rain", name: "Sparkle Rain", desc: "Vertical falling metallic rain streaks with bright heads and fading tails", category: "Sparkle", defaults: { density: 0.008, streak_len: 12 } },
    // 2026-04-19 HEENAN H4HR-6 — `sparkle_constellation` collided with MONOLITHICS L1621.
    { id: "spec_sparkle_constellation", name: "Sparkle Constellation (Spec)", desc: "Clustered star groups — Gaussian clusters with bright cores", category: "Sparkle", defaults: { n_clusters: 8, stars_per: 40 } },
    { id: "sparkle_nebula", name: "Sparkle Nebula", desc: "FBM cloud-shaped sparkle regions — dense in clouds, sparse in voids", category: "Sparkle", defaults: { density: 0.006 } },
    // 2026-04-19 HEENAN H4HR-7 — `sparkle_firefly` collided with MONOLITHICS L1617.
    { id: "spec_sparkle_firefly", name: "Sparkle Firefly (Spec)", desc: "Soft glowing points with warm Gaussian halos — like fireflies at dusk", category: "Sparkle", defaults: { n_flies: 200, glow_radius: 8 } },
    { id: "sparkle_shattered", name: "Sparkle Shattered", desc: "Angular shard fragments — random bright polygonal pieces like broken glass", category: "Sparkle", defaults: { n_shards: 500 } },
    // 2026-04-19 HEENAN H4HR-8 — `sparkle_champagne` collided with MONOLITHICS L1619.
    { id: "spec_sparkle_champagne", name: "Sparkle Champagne (Spec)", desc: "Rising round bubble sparkle dots — clustered vertically like champagne fizz", category: "Sparkle", defaults: { density: 0.02, bubble_max: 4 } },
    { id: "sparkle_comet", name: "Sparkle Comet", desc: "Bright heads with fading directional tail streaks — shooting stars", category: "Sparkle", defaults: { n_comets: 80, tail_len: 30 } },
    { id: "sparkle_galaxy_swirl", name: "Sparkle Galaxy Swirl", desc: "Logarithmic spiral arms dense with star points — spiral galaxy structure", category: "Sparkle", defaults: { n_arms: 3, density: 0.008 } },
    { id: "sparkle_electric_field", name: "Sparkle Electric Field", desc: "Sparkle density follows electric field lines between random charges", category: "Sparkle", defaults: { density: 0.01 } },
    { id: "prismatic_dust", name: "Prismatic Dust", desc: "Multi-frequency scatter overlaid with sin(dist) interference rings — prismatic halo effect", category: "Sparkle", defaults: { scatter_density: 0.005, ring_freq: 18.0 } },
    // Banded row variants
    { id: "chevron_bands", name: "Chevron Bands", desc: "V-shaped chevron bands — arrowhead striping using y + abs(x-center) coordinate", category: "Structure", defaults: { num_bands: 40, v_angle: 0.6 } },
    { id: "wave_bands", name: "Wave Bands", desc: "Sinusoidal wavy bands — undulating stripes using y + sin(x * freq) coordinate", category: "Structure", defaults: { num_bands: 36, wave_freq: 6.0, wave_amp: 0.12 } },
    { id: "gradient_bands", name: "Gradient Bands", desc: "Bands that fade bright-to-dark internally — fmod banding with within-band gradient", category: "Structure", defaults: { num_bands: 35 } },
    { id: "split_bands", name: "Split Bands", desc: "Alternating thick bright and thin dark bands — two-weight stripe pattern", category: "Structure", defaults: { thick_count: 20, thin_count: 25 } },
    { id: "diagonal_bands", name: "Diagonal Bands", desc: "45-degree angled bands — diagonal projection coordinate for true angular stripes", category: "Structure", defaults: { num_bands: 45, angle_deg: 45.0 } },
    // NOTE: Intricate & Ornate patterns MOVED to PATTERNS array (were mistakenly in SPEC_PATTERNS)
    // --- PRIORITY 2 BATCH A: 🪛 Directional Brushed (66–77) — G=Roughness channel ---
    { id: "brushed_linear", name: "Brushed Linear", desc: "Pure parallel horizontal lines — sin(y×freq) zero x-modulation, G=Roughness — definitive brushed aluminum", category: "Brushed", defaults: { frequency: 80.0 } },
    { id: "brushed_diagonal", name: "Brushed Diagonal", desc: "45° diagonal brushed lines via rotated projection — chevron-style panel polish, G=Roughness", category: "Brushed", defaults: { frequency: 70.0, angle_deg: 45.0 } },
    { id: "brushed_cross", name: "Brushed Cross", desc: "Bidirectional H+V cross-brushed strokes — scotch-brite stainless cross-finish, G=Roughness", category: "Brushed", defaults: { frequency: 60.0 } },
    { id: "brushed_radial", name: "Brushed Radial", desc: "Radial lines from center — machined disc or spinner radial polish, G=Roughness", category: "Brushed", defaults: { num_lines: 120 } },
    { id: "brushed_arc", name: "Brushed Arc", desc: "Concentric arc sweeps from off-canvas center — belt-sanded panel with slight bow, G=Roughness", category: "Brushed", defaults: { frequency: 50.0 } },
    { id: "hairline_polish", name: "Hairline Polish", desc: "Ultra-fine high-frequency parallel hairlines — premium stainless steel hairline texture, G=Roughness", category: "Brushed", defaults: { frequency: 200.0 } },
    { id: "lathe_concentric", name: "Lathe Concentric", desc: "Lathe-turned concentric rings with spiral drift — machined billet part face, G=Roughness", category: "Brushed", defaults: { frequency: 60.0 } },
    { id: "bead_blast_uniform", name: "Bead Blast", desc: "Isotropic fine pit texture — glass bead blasting, uniform no-directionality grain, G=Roughness", category: "Brushed", defaults: { grain_size: 3.0 } },
    { id: "orbital_swirl", name: "Orbital Swirl", desc: "DA orbital sander arc passes — overlapping curved brushed regions, G=Roughness", category: "Brushed", defaults: { num_passes: 8 } },
    { id: "buffer_swirl", name: "Buffer Swirl", desc: "Random circular buffer marks — car-wash or compound-polish swirl arc artifacts, G=Roughness", category: "Brushed", defaults: { num_centers: 20 } },
    { id: "wire_brushed_coarse", name: "Wire Brushed", desc: "Low-frequency wide directional grain — stiff wire brush coarse scratches with wandering waviness, G=Roughness", category: "Brushed", defaults: { frequency: 25.0 } },
    { id: "hand_polished", name: "Hand Polished", desc: "Multi-region hand polishing — inconsistent short directional strokes per zone, like wax-on/wax-off, G=Roughness", category: "Brushed", defaults: { num_regions: 12 } },
    // === Guilloché & Machined ===
    { id: "guilloche_barleycorn", name: "Guilloché Barleycorn", desc: "Classic barleycorn — lobed concentric rings via polar amplitude modulation, interlocking oval cells, R=Metallic", category: "Guilloché", defaults: { frequency: 40.0, n_lobes: 8, amplitude: 0.3 } },
    { id: "guilloche_hobnail", name: "Guilloché Hobnail", desc: "Square-grid hemispherical dome protrusions — hobnail stud array, R=Metallic", category: "Guilloché", defaults: { spacing: 16, dome_radius_frac: 0.45 } },
    { id: "guilloche_waves", name: "Guilloché Waves", desc: "Phase-modulated engine-turned wave sheets — classic pocket-watch sweep lines undulating, R=Metallic", category: "Guilloché", defaults: { x_freq: 60.0, y_mod_freq: 8.0, amplitude: 0.15 } },
    { id: "guilloche_sunray", name: "Guilloché Sunray", desc: "Engine-turned sunray — radial lines + concentric rings polar cross-hatch, pocket-watch dial character, R=Metallic", category: "Guilloché", defaults: { n_rays: 72, ring_freq: 20.0, ray_fade: 0.6 } },
    { id: "guilloche_moire_eng", name: "Guilloché Moiré", desc: "Two offset concentric ring systems beating into flowing moiré ellipses, R=Metallic", category: "Guilloché", defaults: { freq: 30.0, offset_frac: 0.15 } },
    { id: "jeweling_circles", name: "Jeweling Circles", desc: "Spotfacing jeweling — hex-packed overlapping circles, scalloped at intersections, R=Metallic", category: "Guilloché", defaults: { spacing: 14, circle_radius_frac: 0.55 } },
    { id: "knurl_diamond", name: "Knurl Diamond", desc: "Diamond knurl — crossed diagonal sin lines, raised diamond peaks at both-high intersections, G=Roughness + R=Metallic", category: "Guilloché", defaults: { frequency: 30.0, angle_deg: 45.0 } },
    { id: "knurl_straight", name: "Knurl Straight", desc: "Straight knurl — sharpened horizontal ridges from sine to discrete stepped form, G=Roughness", category: "Guilloché", defaults: { frequency: 40.0, sharpness: 3.0 } },
    { id: "face_mill_bands", name: "Face Mill Bands", desc: "Face milling — parallel circular arc scallops from sequential cutter passes, G=Roughness", category: "Guilloché", defaults: { pass_width: 60, freq: 20.0 } },
    { id: "fly_cut_arcs", name: "Fly Cut Arcs", desc: "Fly cutting — overlapping large-radius scalloped arcs from single-point cutter passes, G=Roughness", category: "Guilloché", defaults: { cutter_radius_frac: 1.2, pass_pitch: 40 } },
    { id: "engraved_crosshatch", name: "Engraved Crosshatch", desc: "Precision engraved crosshatch — additive fine parallel lines at ±angle, uniform weight at all grid points, G=Roughness", category: "Guilloché", defaults: { frequency: 50.0, angle_deg: 30.0 } },
    { id: "edm_dimple", name: "EDM Dimple", desc: "EDM dimple texture — hex-packed spherical craters, bright rim, dark pit — electrical discharge machining, G=Roughness + R=Metallic", category: "Guilloché", defaults: { spacing: 12, dimple_radius_frac: 0.4 } },
    // --- PRIORITY 2 BATCH D: Carbon Fiber & Industrial Weave (102-113) ---
    { id: "spec_carbon_2x2_twill", name: "Carbon 2×2 Twill", desc: "Standard 2×2 twill carbon fiber — diagonal ±45° tow families, over-2/under-2 interlace, sharp metallic peaks at tow crowns", category: "Carbon & Weave" },
    { id: "spec_carbon_plain_weave", name: "Carbon Plain Weave", desc: "Plain weave 1×1 carbon fiber — orthogonal over/under checkerboard interlace, symmetric grid-like metallic variation", category: "Carbon & Weave" },
    { id: "spec_carbon_3k_fine", name: "Carbon 3K Fine", desc: "Fine 3K carbon (3000 filament tow) — high-frequency ±45° twill with narrow Gaussian tow crowns, aerospace small-weave look", category: "Carbon & Weave" },
    { id: "spec_carbon_forged", name: "Carbon Forged", desc: "Forged carbon (random short-fiber SMC) — random overlapping strand segments at all angles, marbled metallic pattern, NOT a regular weave", category: "Carbon & Weave" },
    { id: "spec_carbon_wet_layup", name: "Carbon Wet Layup", desc: "Wet layup carbon — fiber weave shows through thick resin layer, Gaussian-blurred soft metallic peaks, resin-rich gloss", category: "Carbon & Weave" },
    { id: "spec_kevlar_weave", name: "Kevlar Weave", desc: "Kevlar/aramid fiber weave — plain-weave geometry with matte satin sheen, silky micro-texture, moderate interlace roughness", category: "Carbon & Weave" },
    { id: "spec_fiberglass_chopped", name: "Fiberglass Chopped", desc: "Chopped strand fiberglass mat — random clustered glass strands, orientation-weighted specular (vertical fibers most specular), non-woven", category: "Carbon & Weave" },
    { id: "spec_woven_dyneema", name: "Woven Dyneema", desc: "Woven Dyneema/UHMWPE — extremely tight near-invisible weave, subtle grid R variation (160–200 range), the almost-metallic look of UHMWPE sheets", category: "Carbon & Weave" },
    { id: "spec_mesh_perforated", name: "Mesh Perforated", desc: "Perforated metal mesh — regular circular holes with smooth radial transition, high metallic between perforations, R=0 at hole centers", category: "Carbon & Weave" },
    { id: "spec_expanded_metal", name: "Expanded Metal", desc: "Expanded metal mesh — rotated diamond-pattern openings from slitting/stretching sheet, high metallic wire edges, open diamond interior", category: "Carbon & Weave" },
    { id: "spec_chainlink_fence", name: "Chainlink Fence", desc: "Chain-link fence — two families of diagonal crossing wires, double-thickness metallic at intersections, distinct from stamped expanded metal", category: "Carbon & Weave" },
    { id: "spec_ballistic_weave", name: "Ballistic Weave", desc: "Ballistic nylon/Cordura weave — dense tight plain weave, moderate R (synthetic fiber), subtle interlace roughness, utilitarian tactical texture", category: "Carbon & Weave" },
    // --- PRIORITY 2 BATCH E: 🔵 Clearcoat Behavior (114–123) ---
    { id: "cc_panel_pool", name: "CC Panel Pool", desc: "Clearcoat pooling — gravity-settled extra-clear in panel low spots, scattered Gaussian gloss pools, B=Clearcoat", category: "Clearcoat", defaults: { num_pools: 12, pool_spread: 0.18 } },
    { id: "cc_drip_runs", name: "CC Drip Runs", desc: "Clearcoat drip runs — vertical streaks of excess clear running down panel, thin elongated gloss streaks, B=Clearcoat", category: "Clearcoat", defaults: { num_drips: 8, drip_length: 0.25 } },
    { id: "cc_fish_eye", name: "CC Fish Eye", desc: "Fish-eye defects — silicone contamination repels clearcoat, circular bare craters with bright matte edge rings, B=Clearcoat", category: "Clearcoat", defaults: { num_craters: 20, crater_radius: 0.04 } },
    { id: "cc_overspray_halo", name: "CC Overspray Halo", desc: "Overspray halo — spray gun edge mist, ring of thin/rough clearcoat at spray boundary, B=Clearcoat", category: "Clearcoat", defaults: { num_halos: 6, halo_radius: 0.22 } },
    { id: "cc_edge_thin", name: "CC Edge Thin", desc: "Panel edge thinning — clearcoat sags/thins at corners, edges rough (bright), center gloss (dark), B=Clearcoat", category: "Clearcoat", defaults: { edge_width: 0.12, noise_scale: 0.04 } },
    { id: "cc_masking_edge", name: "CC Masking Edge", desc: "Masking tape boundary — hard clearcoat step where tape lifted, abrupt bright-to-dark line at angle, B=Clearcoat", category: "Clearcoat", defaults: { num_edges: 4, edge_softness: 0.03 } },
    { id: "cc_spot_polish", name: "CC Spot Polish", desc: "Spot polish — localized re-buffed gloss spots against normal texture, random dark smooth circles, B=Clearcoat", category: "Clearcoat", defaults: { num_spots: 15, spot_radius: 0.08 } },
    { id: "cc_gloss_stripe", name: "CC Gloss Stripe", desc: "Gloss stripes — parallel extra-glossy bands from spray gun double-pass, dark stripes vs normal surface, B=Clearcoat", category: "Clearcoat", defaults: { num_stripes: 6, stripe_width: 0.06, angle_deg: 0.0 } },
    { id: "cc_wet_zone", name: "CC Wet Zone", desc: "Wet zones — unleveled clearcoat blob patches at higher gloss, organic FBM-thresholded dark areas, B=Clearcoat", category: "Clearcoat", defaults: { num_zones: 5 } },
    { id: "cc_panel_fade", name: "CC Panel Fade", desc: "Panel fade — clearcoat thickness gradient across panel from spray angle, one side gloss one side dull, B=Clearcoat", category: "Clearcoat", defaults: { fade_direction: 0.0, noise_warp: 0.06 } },
    // --- PRIORITY 2 BATCH C: Worn, Patina & Weathering (90-101) ---
    { id: "spec_rust_bloom", name: "Rust Bloom", desc: "Worley-noise rust blooms spreading from surface defects — metallic drops to zero in corroded zones", category: "Weathering" },
    { id: "spec_patina_verdigris", name: "Patina Verdigris", desc: "FBM-inverted oxidized copper patina — verdigris pools in recesses, bronze glints on high points", category: "Weathering" },
    { id: "spec_oxidized_pitting", name: "Oxidized Pitting", desc: "Gaussian oxidation pits — dark metallic centers with bright metallic rings at each pit edge", category: "Weathering" },
    { id: "spec_heat_scale", name: "Heat Scale", desc: "Sinusoidal heat-gradient bands like titanium exhaust pipes — oxide thickness gradient creates spectral zones", category: "Weathering" },
    { id: "spec_galvanic_corrosion", name: "Galvanic Corrosion", desc: "Voronoi two-metal partition — roughness spikes and metallic drops at dissimilar metal contact seams", category: "Weathering" },
    { id: "spec_stress_fractures", name: "Stress Fractures", desc: "Metal fatigue crack tree grown along FBM gradients — crack pixels near-zero metallic, max roughness", category: "Weathering" },
    { id: "spec_battle_scars", name: "Battle Scars", desc: "Race-impact linear scratch gouges — fresh metal streak flanked by rough paint pile-up edges", category: "Weathering" },
    { id: "spec_worn_edges", name: "Worn Edges", desc: "Contour-line edge wear — high metallic at simulated panel edges, normal painted spec at center", category: "Weathering" },
    { id: "spec_peeling_clear", name: "Peeling Clear", desc: "Voronoi clearcoat peel — bonded cells glossy, lifted cells dull, peel boundary adds micro-roughness", category: "Weathering" },
    { id: "spec_sandblast_strip", name: "Sandblast Strip", desc: "FBM blob-shaped sandblasted zones — bare metal roughness adjacent to unblasted painted surfaces", category: "Weathering" },
    { id: "spec_micro_chips", name: "Micro Chips", desc: "Stone chip damage field — 3-octave clustered point-process chips expose bare metal on leading surfaces", category: "Weathering" },
    { id: "spec_aged_matte", name: "Aged Matte", desc: "Long-term matte oxidation — tangent-warped FBM makes some areas deader matte with ghost metallic", category: "Weathering" },
    // --- PRIORITY 2 BATCH E: Geometric & Architectural (124–135) ---
    { id: "spec_faceted_diamond", name: "Faceted Diamond", desc: "Gem-cut Voronoi facets — each cell one facet, linear metallic gradient rotates per cell to simulate different facet orientations, multi-directional gem glitter, R=Metallic", category: "Geometric", defaults: { num_cells: 120 } },
    { id: "spec_hammered_dimple", name: "Hammered Dimple", desc: "Hex-grid hemispherical hammer dimples — cos(r/radius×π/2) profile peaks at rim edge (angled surface), low at dome center, R=Metallic", category: "Geometric", defaults: { dimple_spacing: 18.0 } },
    { id: "spec_knurled_diamond", name: "Knurled Diamond", desc: "Precision diamond knurl — two diagonal ridge families at ±60° multiply at crossing peaks, cut-into-solid geometry distinct from wire mesh, R=Metallic + G=Roughness", category: "Geometric", defaults: { frequency: 28.0, angle_deg: 60.0 } },
    { id: "spec_knurled_straight", name: "Knurled Straight", desc: "Axial straight knurl — single horizontal ridge family with sharpened cosine profile, crisp machined-tooth bright ridge / dark valley bands, G=Roughness", category: "Geometric", defaults: { frequency: 36.0, sharpness: 4.0 } },
    { id: "spec_architectural_grid", name: "Architectural Grid", desc: "Curtain wall grid — polished aluminum frame (high metallic) surrounding low-metallic glass panels, min(fmod) frame-proximity approach, 10% frame width, R=Metallic", category: "Geometric", defaults: { cell_size: 40.0, frame_frac: 0.10 } },
    { id: "spec_hexagonal_tiles", name: "Hexagonal Tiles", desc: "Hex mosaic tiles — smooth ceramic interior (low metallic) with mineral grout lines (higher metallic, higher roughness), hex distance function tile/grout split, R=Metallic + G=Roughness", category: "Geometric", defaults: { tile_size: 22.0, grout_frac: 0.12 } },
    { id: "spec_brick_mortar", name: "Brick Mortar", desc: "Running-bond brickwork — near-zero metallic clay brick faces with moderate metallic cement mortar joints, 0.5-offset stagger per course, R=Metallic + G=Roughness", category: "Geometric", defaults: { brick_h: 16.0, brick_w: 36.0, mortar_frac: 0.08 } },
    { id: "spec_corrugated_panel", name: "Corrugated Panel", desc: "Industrial corrugated metal — sin cross-section, metallic = cos²(surface_normal_angle), wave tops maximum specular, valleys minimum, strong directional sheen, R=Metallic", category: "Geometric", defaults: { frequency: 12.0, amplitude: 0.4 } },
    { id: "spec_riveted_plate", name: "Riveted Plate", desc: "Aircraft riveted sheet — flat polished plate + Gaussian dome metallic peaks at rivet heads, edge roughness spike at rivet rim, installation smear halo, R=Metallic + G=Roughness", category: "Geometric", defaults: { rivet_spacing: 24.0, rivet_radius_frac: 0.28 } },
    { id: "spec_weld_seam", name: "Weld Seam", desc: "Linear weld bead — oxidized weld crown + heat-affected zone (scale reduces metallic) + clean base metal, sinusoidal ripple pattern from multi-pass puddle solidification, R=Metallic + G=Roughness", category: "Geometric", defaults: { num_passes: 3, pass_spacing: 8.0 } },
    { id: "spec_stamped_emboss", name: "Stamped Emboss", desc: "Embossed sheet metal panel — circle-in-square repeating motif, raised areas high metallic (light catch), recessed shadowed, abs(combined sine waves) for sharp emboss peaks, R=Metallic", category: "Geometric", defaults: { cell_size: 28.0 } },
    { id: "spec_cast_surface", name: "Cast Surface", desc: "Sand-cast raw metal — Gaussian roughness + low-freq sand cluster bumps + sparse gas pore pits, matte-metallic look of unfinished cast iron/aluminum, R=Metallic", category: "Geometric", defaults: { bump_scale: 0.15, grain_scale: 0.05 } },
    // --- PRIORITY 2 BATCH F: Natural & Organic ---
    { id: "spec_wood_grain_fine", name: "Wood Grain Fine", desc: "Fine maple/birch wood grain — parallel growth rings with FBM warp perturbation, earlywood (ring peak) high metallic, latewood (valley) low metallic + high roughness, R=Metallic + G=Roughness", category: "Natural", defaults: { ring_freq: 0.55, ring_warp: 6.0 } },
    { id: "spec_wood_burl", name: "Wood Burl", desc: "Burl wood swirling grain — multiple burl eye seed points each with own rotation direction, ring function uses distance_to_nearest_eye for complex burl veneer swirls, R=Metallic", category: "Natural", defaults: { num_eyes: 8, eye_influence: 0.55 } },
    { id: "spec_stone_granite", name: "Stone Granite", desc: "Granite crystalline texture — multi-scale Voronoi per crystal type: quartz (high metallic), feldspar (medium), mica (very high metallic flash), boundary roughness spike, R=Metallic + G=Roughness", category: "Natural", defaults: { num_crystals: 600 } },
    { id: "spec_stone_marble", name: "Stone Marble", desc: "Marble vein pattern — vein = sin(x*freq + fbm*warp), vein areas high roughness (micro-fracture) + moderate metallic, marble body low roughness + low metallic (polished stone), R=Metallic + G=Roughness", category: "Natural", defaults: { vein_freq: 0.08, vein_warp: 7.0 } },
    { id: "spec_water_ripple_spec", name: "Water Ripple", desc: "Water ripple surface — concentric circular waves from multiple random drop points, wave crest higher metallic (facet angle), trough lower metallic, overlapping systems create interference, max gloss throughout, R=Metallic", category: "Natural", defaults: { num_drops: 6 } },
    { id: "spec_coral_reef", name: "Coral Reef", desc: "Coral reef branching texture — domain-warped multi-scale FBM creates cellular/branching coral structure, branch surfaces moderate metallic (calcium carbonate shimmer), tips highest metallic, void areas zero metallic, R=Metallic", category: "Natural", defaults: { branch_octaves: 6 } },
    { id: "spec_snake_scales", name: "Snake Scales", desc: "Reptile scale array — elongated oval scales in offset rows, specular peak near scale center-top (convex surface), lower metallic at scale edges, overlap regions roughness spike, elliptical distance function, R=Metallic + G=Roughness", category: "Natural", defaults: { scale_w: 20.0, scale_h: 14.0 } },
    { id: "spec_fish_scales", name: "Fish Scales", desc: "Fish scale array — circular overlapping scales, INVERTED radial metallic gradient vs snake scales: higher metallic at scale rim + lower at center (iridescent armored look), radial shimmer rings, R=Metallic", category: "Natural", defaults: { scale_r: 16.0 } },
    { id: "spec_leaf_venation", name: "Leaf Venation", desc: "Leaf vein network — hierarchical: main mid-rib (thickest, highest metallic), secondary veins at angles, tertiary fine FBM network, vein channels high metallic (hydrated tissue), inter-vein leaf tissue lower metallic, R=Metallic + G=Roughness", category: "Natural", defaults: { num_secondary: 8 } },
    { id: "spec_terrain_erosion", name: "Terrain Erosion", desc: "Eroded terrain topology — multi-octave domain-warped FBM, ridgetops lower roughness (wind-polished rock), valley floors higher roughness (sediment), cliff faces high metallic (fresh exposed rock), gradient magnitude as roughness proxy, R=Metallic + G=Roughness", category: "Natural", defaults: { octaves: 7 } },
    { id: "spec_crystal_growth", name: "Crystal Growth", desc: "Geode crystal growth — Voronoi facets radiate from center, each crystal face at different angle (metallic varies with face orientation), dense packing creates angular metallic peaks, boundary glint at crystal edges, R=Metallic", category: "Natural", defaults: { num_crystals: 80 } },
    { id: "spec_lava_flow", name: "Lava Flow", desc: "Solidified lava flow — pahoehoe ropy lines (sinusoidal flow lines, moderate metallic, low roughness) vs aa lava zones (FBM high-roughness, low metallic), flow direction follows perturbed gradient field, R=Metallic + G=Roughness", category: "Natural", defaults: { flow_freq: 0.035 } },
    // --- PRIORITY 2 BATCH G: Lighting & Optical Effects (136-147) ---
    { id: "spec_fresnel_gradient", name: "Fresnel Gradient", desc: "Fresnel reflectivity gradient — Schlick approximation drives edge-brightening (glancing angle = max metallic), center near-normal incidence = moderate metallic, FBM perturbs edge boundary, R=Metallic + G=Roughness", category: "Optical", defaults: { edge_metallic: 0.92, center_metallic: 0.38 } },
    { id: "spec_caustic_light", name: "Caustic Light", desc: "Caustic light patterns — folded-wavefront FBM simulation, histogram density of fold landing positions creates bright branching caustic lines like light through water, R=Metallic", category: "Optical", defaults: { caustic_sharpness: 8.0, num_octaves: 4 } },
    { id: "spec_diffraction_grating", name: "Diffraction Grating", desc: "Physical diffraction grating — sin²(x×freq) ruling lines with position-dependent phase modulation for constructive interference zones, secondary cross-diffraction perpendicular grating, R=Metallic", category: "Optical", defaults: { fine_freq: 120.0, secondary_strength: 0.25 } },
    { id: "spec_retroreflective", name: "Retroreflective", desc: "Retroreflective surface (road signs/safety vest) — staggered Gaussian corner-cube grid with microsphere fill between, FBM bead-coat variation, characteristic sparkly grid of retroreflective materials, R=Metallic", category: "Optical", defaults: { grid_spacing: 22.0, microsphere_fill: 0.55 } },
    { id: "spec_velvet_sheen", name: "Velvet Sheen", desc: "Velvet sheen — directional gradient field magnitude as grazing-angle proxy, edge zones high metallic (fiber tips catch light), center zones low metallic + high roughness (fiber base absorption), R=Metallic + G=Roughness", category: "Optical", defaults: { edge_width: 0.22, fiber_scatter: 0.12 } },
    { id: "spec_sparkle_flake", name: "Sparkle Flake", desc: "Metal flake sparkle field — three size-tier circular flakes with Gaussian mirror-face peak + edge shadow ring, FBM density clustering, R=Metallic", category: "Optical", defaults: { density_base: 0.018 } },
    { id: "spec_iridescent_film", name: "Iridescent Film", desc: "Thin-film iridescence — FBM-driven film thickness with sin²(thickness × band_freq × π) interference banding, smooth film surface near-zero roughness throughout, oily shimmer pattern, R=Metallic", category: "Optical", defaults: { film_octaves: 5, band_freq: 12.0 } },
    { id: "spec_anisotropic_radial", name: "Anisotropic Radial", desc: "Radial anisotropic star pattern — sin(atan2 × N/2)^p formula creates sharp angular metallic bands from disc center, FBM run-out perturbation, distinct from brushed_radial smooth gradient, R=Metallic", category: "Optical", defaults: { num_segments: 24, star_power: 2.0 } },
    { id: "spec_bokeh_scatter", name: "Bokeh Scatter", desc: "Bokeh aperture circles — hexagonally-packed overlapping circles ±20% size variation, Gaussian interior fill + metallic edge ring at aperture blade radius, R=Metallic + B=Clearcoat", category: "Optical", defaults: { num_circles: 60, hex_jitter: 0.15 } },
    { id: "spec_light_leak", name: "Light Leak", desc: "Lens flare light leak — anamorphic horizontal streak + primary halo ring + ghost aperture circles at intervals along streak axis, retro/aesthetic photographic artifact look, R=Metallic", category: "Optical", defaults: { streak_width: 0.035, num_ghosts: 5 } },
    { id: "spec_subsurface_depth", name: "Subsurface Depth", desc: "Subsurface scattering depth — blurred FBM gradient magnitude as SSS proxy, high curvature = low metallic (light scatters in), smooth areas = high metallic (surface reflection), depth glow look of skin/marble/wax, R=Metallic + G=Roughness", category: "Optical", defaults: { sss_depth: 0.65, scatter_radius: 8.0 } },
    { id: "spec_chromatic_aberration", name: "Chromatic Aberration", desc: "Lens chromatic aberration — inner zone uniform spec, outer zones alternating metallic fringes at multi-frequency period growing with radius (CA magnitude grows outward), FBM field-curvature distortion, R=Metallic", category: "Optical", defaults: { inner_radius: 0.30, fringe_period: 0.04 } },
    // --- PRIORITY 2 BATCH H: Surface Treatments (148-155) ---
    { id: "spec_electroplated_chrome", name: "Electroplated Chrome", desc: "Electroplated chrome micro-crystalline surface — fine isotropic Voronoi (55+ cells/unit) per-crystal metallic variation ±15 around base 230, no directionality, near-zero clearcoat variation (16-18), R=Metallic + B=Clearcoat", category: "Surface Treatment", defaults: { cell_density: 55.0, metallic_base: 230 } },
    { id: "spec_anodized_texture", name: "Anodized Texture", desc: "Anodized aluminum nanoporous oxide layer — hexagonal three-cosine pore grid (100+ pores/unit), high metallic oxide inter-pore matrix, low metallic pore centers, moderate roughness (G: 30-60), glossy clearcoat (B: 20-40), R=Metallic + G=Roughness", category: "Surface Treatment", defaults: { pore_density: 105.0, metallic_base: 170 } },
    { id: "spec_powder_coat_texture", name: "Powder Coat Texture", desc: "Powder coat orange-peel surface — low-frequency FBM bumps (wavelength 20-30px), non-metallic (R: 0-20), semi-glossy (B: 50-100), G=Roughness 100-160, softer and lower-frequency than spray orange peel, G=Roughness dominant", category: "Surface Treatment", defaults: { cell_size: 22.0 } },
    { id: "spec_thermal_spray", name: "Thermal Spray", desc: "Plasma spray / HVOF splat texture — Poisson-disc overlapping circular splats, each with raised metallic center, rough impact-crater rim, oxidized splat top, characteristic metallic sheen with rough orange-peel character, R=Metallic + G=Roughness", category: "Surface Treatment", defaults: { splat_density: 0.018 } },
    { id: "spec_electroformed_texture", name: "Electroformed Texture", desc: "Electroformed metal columnar grain — anisotropic Voronoi cells taller than wide (aspect ~2.8:1) oriented vertically, column tip (top) = higher metallic, column base = lower metallic, grain boundary roughness spikes, directional columnar structure, R=Metallic + G=Roughness", category: "Surface Treatment", defaults: { col_aspect: 2.8 } },
    { id: "spec_pvd_coating", name: "PVD Coating", desc: "Physical Vapor Deposition nodule texture — ultra-fine Voronoi (80+ cells/unit) nucleation sites, very high metallic 180-240/255 throughout, near-zero roughness G: 10-30/255, minimal grain boundary dip, TiN/TiAlN characteristic smooth highly-reflective surface, R=Metallic + G=Roughness", category: "Surface Treatment", defaults: { cell_density: 80.0 } },
    { id: "spec_shot_peened", name: "Shot Peened", desc: "Shot peening overlapping impact dimples — dense Gaussian depression field (100% coverage), dimple center = roughness peak, rim = metallic flash from compressive work hardening, G: 140-200 roughness, R: 80-140 metallic, B: 120-180 (lost gloss), G=Roughness + R=Metallic", category: "Surface Treatment", defaults: { dimple_density: 0.022, dimple_radius: 6.0 } },
    { id: "spec_laser_etched", name: "Laser Etched", desc: "Laser-etched pattern on polished surface — sharp step-function boundary (FBM-wobbled edge) between etched border strips (G=200+ rough, R=40 oxidized) and polished tile centers (G=10, R=200 mirror), no gradual transition, R=Metallic + G=Roughness", category: "Surface Treatment", defaults: { tile_size: 32.0, border_frac: 0.18 } },
    // --- PRIORITY 2 BATCH I: Specialty & Exotic (156-163) ---
    { id: "spec_liquid_metal", name: "Liquid Metal", desc: "Mercury / liquid metal surface — near-perfect reflectivity (R: 240-255, G: 2-8, B: 16-18) with two-frequency gravity wave interference pattern, standing wave beating creates subtle metallic modulation, very low amplitude (0.04), distinguishes from flat chrome, R=Metallic dominant", category: "Exotic", defaults: { wave1_freq: 0.8, wave2_freq: 1.3, amplitude: 0.04 } },
    { id: "spec_chameleon_flake", name: "Chameleon Flake", desc: "ChromaFlair / chameleon flake spec — medium-scale Voronoi (20-40/unit), each flake random metallic value (160-220/255) by hash, random-metallic mosaic pattern, inter-flake boundary roughness spike, genuine ChromaFlair spec signature, R=Metallic + G=Roughness", category: "Exotic", defaults: { cell_density: 28.0, metallic_base: 190 } },
    { id: "spec_xirallic_crystal", name: "Xirallic Crystal", desc: "Xirallic alumina crystal flake — large sparse Voronoi (10-20/unit), steep radial metallic gradient per flake (200-255 at crystal face center, drops to 60-80 at flake edge), low-density deep sparkle character, inter-flake R=80 G=80, distinct depth-sparkle vs standard metallic, R=Metallic + G=Roughness", category: "Exotic", defaults: { cell_density: 14.0 } },
    { id: "spec_holographic_foil", name: "Holographic Foil", desc: "Holographic foil dual perpendicular gratings — grating 1 (horizontal lines, freq1) × grating 2 (vertical lines, freq2) beat product, cross-term diagonal interference, constructive metallic peaks at 2D grating node intersections, fundamentally different from single-family diffraction grating and moire_overlay, R=Metallic", category: "Exotic", defaults: { grating1_freq: 55.0, grating2_freq: 48.0 } },
    { id: "spec_oil_film_thick", name: "Oil Film Thick", desc: "Thick oil film pooling — FBM + Gaussian pool centers define thickness distribution, thick pools G=5-15 (smooth level surface), thin film edges G=80-120 (substrate roughness bleeds through), spatial gradient from pool center to edge, different from thin-film oil_slick (this is about surface leveling), G=Roughness + R=Metallic", category: "Exotic", defaults: { num_pools: 6 } },
    { id: "spec_magnetic_ferrofluid", name: "Magnetic Ferrofluid", desc: "Ferrofluid Rosensweig instability spike array — regular hexagonal array via three-cosine hex field, each spike Gaussian profile (exp(-r²/σ²)), tip metallic 240+ (apex direct reflection), valley metallic 50-80, hex-grid spike distribution, striking sci-fi textured surface, R=Metallic dominant", category: "Exotic", defaults: { hex_spacing: 30.0, spike_sigma: 0.35 } },
    { id: "spec_aerogel_surface", name: "Aerogel Surface", desc: "Aerogel nanofoam pore network — multi-scale FBM threshold masking creates interconnected strut/pore topology, strut R=40/255 (glass silica), pore R=20/255 (air), strut G=15 (smooth glass), pore G=183 (rough walls), very unusual all-low-metallic signature with glass-smooth struts, R=Metallic + G=Roughness", category: "Exotic", defaults: { octaves: 4, threshold: 0.52 } },
    { id: "spec_damascus_steel_spec", name: "Damascus Steel Spec", desc: "Damascus steel surface micro-topography spec — flow-field distorted layer bands, high-carbon bands (R=190/255 metallic, G=20/255 smooth, polishes bright), low-carbon bands (R=120/255, G=60/255 slightly rougher, chemical etch reveals), sinuous watered-silk FBM warp, different from paint damascus_steel, R=Metallic + G=Roughness", category: "Exotic", defaults: { num_layers: 18, warp_strength: 4.5 } },
    // --- RACING & AUTOMOTIVE (v6.2) ---
    { id: "tire_rubber_transfer", name: "Tire Rubber Transfer", desc: "Dark rubber marks from tire contact — parallel arc streaks with rubber particulate roughness embedded in deposit zones, realistic tire-scuff spec overlay for racing scenes", category: "Racing", defaults: { streak_count: 40, arc_strength: 0.3 } },
    { id: "vinyl_wrap_texture", name: "Vinyl Wrap Texture", desc: "Subtle vinyl wrap film surface texture — air-release channel micro-grooves, fine vinyl surface noise, and tiny trapped air bubble imperfections visible under specular lighting", category: "Racing", defaults: { channel_spacing: 80, bubble_density: 0.001 } },
    { id: "paint_drip_edge", name: "Paint Drip Edge", desc: "Thick clearcoat sag at panel bottom edges — gravity-pooled curtain ridges with horizontal drip lines, heavy clearcoat buildup zone different from cc_drip_runs vertical streaks", category: "Racing", defaults: { edge_fraction: 0.25, drip_count: 30 } },
    { id: "racing_tape_residue", name: "Racing Tape Residue", desc: "Adhesive residue from removed sponsor tape — rectangular boundaries with slightly rough sticky film inside and clean paint outside, raised tape edges", category: "Racing", defaults: { num_strips: 6, strip_width_frac: 0.04 } },
    { id: "sponsor_deboss", name: "Sponsor Deboss", desc: "Pressed-in logo emboss/deboss effect — subtle roughness change from stamped impression in clearcoat surface, catches light at pressed boundary edges", category: "Racing", defaults: { num_logos: 4, depth: 0.3 } },
    { id: "heat_discoloration", name: "Heat Discoloration", desc: "Heat-treated metal color zones — concentric temperature gradient bands like exhaust manifold bluing or weld heat-affected zones with oxide micro-texture", category: "Racing", defaults: { num_zones: 5, max_radius: 0.2 } },
    { id: "salt_spray_corrosion", name: "Salt Spray Corrosion", desc: "Fine salt-air corrosion pitting — coastal marine environment surface degradation with clustered micro-pits, halo staining, and salt-exposure base roughness", category: "Racing", defaults: { pit_density: 0.015, cluster_count: 15 } },
    { id: "track_grime", name: "Track Grime", desc: "Real racing dirt/rubber/oil buildup — concentrated at lower panel areas with splatter spray, embedded rubber particulate, and gravity-biased grime accumulation", category: "Racing", defaults: { splatter_density: 0.005, buildup_zones: 8 } },
    // --- v6.2.x SPONSOR & VINYL ---
    { id: "vinyl_seam", name: "Vinyl Seam", desc: "Long bright ridge lines where two vinyl sheets meet — sharp specular crests with soft heat-gun halo on each side, G=Roughness", category: "Sponsor & Vinyl", defaults: { num_seams: 5, seam_width_frac: 0.0025 } },
    { id: "decal_lift_edge", name: "Decal Lift Edge", desc: "Sponsor decals starting to lift at the edges — bright rim around rectangular sticker boundaries with subtle interior shading and adhesive grit, G=Roughness", category: "Sponsor & Vinyl", defaults: { num_decals: 4, lift_strength: 0.55 } },
    { id: "sponsor_emboss_v2", name: "Sponsor Emboss V2", desc: "V2 sponsor stamp — mixed circle + rounded-rect logo footprints with SDF-based clean rim relief and subtle interior face dimming, G=Roughness + B=Clearcoat", category: "Sponsor & Vinyl", defaults: { num_logos: 6, base_size: 0.10 } },
    { id: "sticker_bubble_film", name: "Sticker Bubble Film", desc: "Trapped air bubbles under vinyl film — soft circular dimples with tiny bright glints and Gaussian halos over a subtle film texture, G=Roughness", category: "Sponsor & Vinyl", defaults: { bubble_density: 0.0009, max_radius: 10 } },
    { id: "vinyl_stretched", name: "Vinyl Stretched", desc: "Vinyl wrap stretched over a curve — directional micro-streaks along the stretch axis with periodic ridges where film thinned and thickened, G=Roughness", category: "Sponsor & Vinyl", defaults: { stretch_freq: 18.0, stretch_amp: 0.30 } },
    // --- v6.2.x RACE WEAR ---
    { id: "tire_smoke_residue", name: "Tire Smoke Residue", desc: "Hazy directional smudges left after burnouts and hard brake events — multi-pass overlapping ribbons with embedded carbon flecks, biased lower panel, G=Roughness", category: "Race Wear", defaults: { num_passes: 5, smoke_strength: 0.45 } },
    { id: "brake_dust_buildup", name: "Brake Dust Buildup", desc: "Brake dust accumulation — fine particulate concentrated near lower panels and wheel arches with sparse darker pools, G=Roughness + B=Clearcoat", category: "Race Wear", defaults: { vertical_bias: 0.85, cluster_count: 20 } },
    { id: "oil_streak_panel", name: "Oil Streak Panel", desc: "Oil and fluid streaks running down a panel — dark vertical wet streaks with bright sheen centerlines and occasional horizontal drip pools, B=Clearcoat + G=Roughness", category: "Race Wear", defaults: { num_streaks: 14, streak_len: 0.45 } },
    { id: "gravel_chip_field", name: "Gravel Chip Field", desc: "Stone-chip damage — many small irregular bright chips clustered toward leading edges, each with a darker disturbed-clearcoat halo, R=Metallic + G=Roughness", category: "Race Wear", defaults: { chip_density: 0.0008, bias_dir: "leading" } },
    { id: "wax_streak_polish", name: "Wax Streak Polish", desc: "Hand-polished wax swipes — irregular curved arc gloss lifts left by a buffing cloth with light pre-polish dust underneath, B=Clearcoat + G=Roughness", category: "Race Wear", defaults: { n_strokes: 18, stroke_width: 0.012 } },
    // --- v6.2.x PREMIUM FINISHES ---
    { id: "mother_of_pearl_inlay", name: "Mother of Pearl Inlay", desc: "Nacre inlay shards — Voronoi cells each with their own iridescence phase and band-axis direction so adjacent shards shimmer at different angles, R=Metallic", category: "Premium", defaults: { num_shards: 140, shimmer_freq: 14.0 } },
    { id: "anodized_rainbow", name: "Anodized Rainbow", desc: "Anodized titanium / niobium oxide rainbow bands — smooth low-roughness surface with FBM-warped interference banding from oxide thickness gradient, R=Metallic", category: "Premium", defaults: { band_freq: 10.0, axis_jitter: 0.10 } },
    { id: "frosted_glass_etch", name: "Frosted Glass Etch", desc: "Sandblasted glass — dense fine random etch points forming a diffuse haze with gentle low-frequency variation between heavier/lighter zones, G=Roughness", category: "Premium", defaults: { etch_density: 2200, etch_radius: 2.2 } },
    { id: "gold_leaf_torn", name: "Gold Leaf Torn", desc: "Torn gold leaf application — discrete sheets with rough warped torn edges, interior wrinkle veins, and exposed dull substrate between sheets, R=Metallic", category: "Premium", defaults: { n_sheets: 10, tear_jitter: 0.08 } },
    { id: "copper_patina_drip", name: "Copper Patina Drip", desc: "Copper with verdigris patina blooms and vertical green-runoff drip channels where moisture pulled patina downward, R=Metallic + G=Roughness", category: "Premium", defaults: { num_drips: 10, drip_len: 0.55 } },
    // --- v6.2.x COLOR-SHIFT VARIANTS ---
    { id: "brushed_linear_warm", name: "Brushed Linear (Warm)", desc: "Warm-toned brushed_linear — softer denser grain pulled toward smoother side, suits copper/brass/gold finishes, G=Roughness", category: "Brushed", defaults: { frequency: 72.0 } },
    { id: "brushed_linear_cool", name: "Brushed Linear (Cool)", desc: "Cool-toned brushed_linear — crisper higher-frequency grain with boosted contrast, suits steel/titanium/chrome finishes, G=Roughness", category: "Brushed", defaults: { frequency: 92.0 } },
    { id: "micro_sparkle_warm", name: "Micro Sparkle (Warm)", desc: "Warm-tinted micro_sparkle — fewer softer sparkles over a lifted dark floor, reads like champagne or gold pearl, R=Metallic", category: "Sparkle", defaults: { density: 0.13 } },
    { id: "micro_sparkle_cool", name: "Micro Sparkle (Cool)", desc: "Cool-tinted micro_sparkle — denser sharper points over a deep crushed field, reads like diamond ice or silver flake, R=Metallic", category: "Sparkle", defaults: { density: 0.18 } },
    { id: "cloud_wisps_warm", name: "Cloud Wisps (Warm)", desc: "Warm-toned cloud_wisps — boosted persistence + bias toward higher mids gives a softer hazier pearl roll for sunset/bronze pearls", category: "Organic", defaults: { num_octaves: 5 } },
    { id: "cloud_wisps_cool", name: "Cloud Wisps (Cool)", desc: "Cool-toned cloud_wisps — extra octave + lower persistence gives a colder sharper cloud for silver/blue/teal pearls", category: "Organic", defaults: { num_octaves: 6 } },
    { id: "aniso_grain_deep", name: "Aniso Grain (Deep)", desc: "Deep / high-contrast aniso_grain — boosted grain depth and outward histogram push for dramatic anodized or deep brushed looks, G=Roughness", category: "Texture", defaults: {} },
    // --- v6.2.y RACE HERITAGE ---
    { id: "checker_flag_subtle", name: "Checker Flag Subtle", desc: "Faint warped checkered-flag specular ghost — soft-edged alternating cells with a gentle FBM wobble so the grid never sits perfectly straight, R=Metallic", category: "Race Heritage", defaults: { squares: 18, warp: 0.006 } },
    { id: "drag_strip_burnout", name: "Drag Strip Burnout", desc: "Two dark rubber lanes down the panel with heat-smoke haloes and embedded carbon grit — long straight burnout deposit, G=Roughness + R=Metallic", category: "Race Heritage", defaults: { num_strips: 2, strip_width: 0.18 } },
    { id: "pit_lane_stripes", name: "Pit Lane Stripes", desc: "Parallel bright speed stripes with thin dark feathered rims — pit-lane tape lane livery effect, R=Metallic", category: "Race Heritage", defaults: { num_stripes: 6, stripe_width: 0.012, gap: 0.06 } },
    { id: "victory_lap_confetti", name: "Victory Lap Confetti", desc: "Mixed-size scattered confetti highlights with soft motion-shadow cool rims — paper bits caught on clearcoat, R=Metallic", category: "Race Heritage", defaults: { density: 0.0009, min_r: 1.5, max_r: 4.5 } },
    { id: "sponsor_tape_vinyl", name: "Sponsor Tape Vinyl", desc: "Angled rectangular faux-vinyl tape strips with bright hardcut rims and matte interior sheen — sponsor tape seam look, G=Roughness + B=Clearcoat", category: "Race Heritage", defaults: { num_tapes: 3, tape_length: 0.55, tape_width: 0.06 } },
    { id: "race_number_ghost", name: "Race Number Ghost", desc: "Big circular badge ghost with bright rim and faint crossed numeral strokes — residual competition roundel, B=Clearcoat + G=Roughness", category: "Race Heritage", defaults: {} },
    // --- v6.2.y MECHANICAL ---
    { id: "exhaust_pipe_scorch", name: "Exhaust Pipe Scorch", desc: "Concentric heat-gradient oxide bands around exhaust tips with soft soot halos — straw/blue/purple bluing rings, R=Metallic + G=Roughness", category: "Mechanical", defaults: { num_vents: 2, heat_radius: 0.18 } },
    { id: "radiator_grille_mesh", name: "Radiator Grille Mesh", desc: "Dense fine perforated grille — bright rims around each dark hole with every-few-cell cross-brace shadow, R=Metallic + G=Roughness", category: "Mechanical", defaults: { cell: 8, hole_frac: 0.55 } },
    { id: "engine_bay_grime", name: "Engine Bay Grime", desc: "Concentrated lower-panel oily dust with dark pools and oily speckle — engine-bay accumulation, G=Roughness + B=Clearcoat", category: "Mechanical", defaults: { buildup: 0.55 } },
    { id: "tire_smoke_streaks", name: "Tire Smoke Streaks", desc: "Long thin sinuous horizontal smoke ribbons that fade at both tips — elongated motion trails distinct from smudge-style residue, G=Roughness", category: "Mechanical", defaults: { num_streaks: 14, taper: 0.35 } },
    { id: "undercarriage_spray", name: "Undercarriage Spray", desc: "Bottom-up road-spray speck fan thinning with height — gravity-biased tire-kicked mote field, G=Roughness", category: "Mechanical", defaults: { spray_density: 0.0025, fan_height: 0.55 } },
    { id: "suspension_rust_ring", name: "Suspension Rust Ring", desc: "Concentric rust rings around bolt/bushing fixture centres with FBM micro-corrosion flavour, G=Roughness + R=Metallic", category: "Mechanical", defaults: { num_rings: 5, ring_spread: 0.18 } },
    // --- v6.2.y WEATHER & TRACK ---
    { id: "rain_droplet_beads", name: "Rain Droplet Beads", desc: "Discrete round wet beads with bright glints and dark gravity-sag crescents — individual raindrop pearls, B=Clearcoat + G=Roughness", category: "Weather & Track", defaults: { density: 0.0015, min_r: 2.5, max_r: 6.5 } },
    { id: "mud_splatter_random", name: "Mud Splatter Random", desc: "Organic dark blobs with FBM-warped edges and radiating thin drip-trail spokes — thrown mud impact splat, G=Roughness + B=Clearcoat", category: "Weather & Track", defaults: { num_splats: 60, splat_size: 0.04 } },
    { id: "wet_track_gloss", name: "Wet Track Gloss", desc: "Macro glossy water pools with FBM-perturbed boundaries and subtle film-reflection bands, B=Clearcoat", category: "Weather & Track", defaults: { pool_scale: 0.38, num_pools: 8 } },
    { id: "dry_dust_film", name: "Dry Dust Film", desc: "Whole-panel low-frequency haze with fine embedded grain — uniform dry dust coating, G=Roughness + B=Clearcoat", category: "Weather & Track", defaults: { film_strength: 0.22, grain_scale: 2.0 } },
    { id: "morning_dew_fog", name: "Morning Dew Fog", desc: "Soft top-biased misted haze with very fine dewlet micro-bumps — cold-morning damp layer, B=Clearcoat", category: "Weather & Track", defaults: { fog_density: 0.55 } },
    { id: "tarmac_grit_embed", name: "Tarmac Grit Embed", desc: "Tiny dark-cored bright-rim asphalt specks pressed into clearcoat with a low-freq dark wash, R=Metallic + G=Roughness", category: "Weather & Track", defaults: { grit_density: 0.005 } },
    // --- v6.2.y ARTISTIC ---
    { id: "brushstroke_bold", name: "Brushstroke Bold", desc: "Painterly elongated curved brush streaks with directional bristle grain and dark trailing rim, R=Metallic", category: "Artistic", defaults: { n_strokes: 14, stroke_width: 0.022 } },
    { id: "crayon_wax_resist", name: "Crayon Wax Resist", desc: "Short parallel wax-rub streaks layered inside low-freq heavy/light macro zones — wax crayon rubbing texture, G=Roughness", category: "Artistic", defaults: { rub_density: 0.35, streak_len: 0.12 } },
    { id: "airbrush_gradient_bloom", name: "Airbrush Gradient Bloom", desc: "Soft radial gradient blooms overlapped with global blur — feather-soft airbrush highlights, R=Metallic", category: "Artistic", defaults: { num_blooms: 5, bloom_radius: 0.30 } },
    { id: "spray_paint_drip", name: "Spray Paint Drip", desc: "Tagger spray drips — bright speckled head with thinning tapered drool running down and a wet centreline, B=Clearcoat + G=Roughness", category: "Artistic", defaults: { num_drips: 9, drip_len: 0.40 } },
    { id: "stippled_dots_fine", name: "Stippled Dots Fine", desc: "Dense fine uniform bright stipple dots over subtle dark wash — pointillism-style texture, R=Metallic", category: "Artistic", defaults: { dot_density: 0.04, dot_radius: 1.2 } },
    { id: "halftone_print", name: "Halftone Print", desc: "Regular halftone grid with per-cell radius modulated by FBM tonal map — pop-art / comic halftone dots, R=Metallic", category: "Artistic", defaults: { cell: 12, dot_max: 0.45 } },
    // --- ABSTRACT ART (17 patterns) — art-history-inspired spec overlays ---
    { id: "abstract_expressionist_splatter", name: "Expressionist Splatter", desc: "Pollock-style paint drips and scattered splatter droplets with occasional downward drip trails — gestural abstract expressionism, R=Metallic", category: "Abstract Art", defaults: { n_splats: 28, drip_chance: 0.6 } },
    { id: "abstract_cubist_facets", name: "Cubist Facets", desc: "Faceted geometric planes partitioning the surface into Voronoi cells with bimodal tonal contrast — analytic cubism, R=Metallic", category: "Abstract Art", defaults: { num_facets: 28 } },
    { id: "abstract_rothko_field", name: "Rothko Field", desc: "Soft color-field rectangles stacked with feathered edges and subtle horizontal brush texture — abstract sublime, B=Clearcoat", category: "Abstract Art", defaults: { num_fields: 3, feather: 0.08 } },
    { id: "abstract_kandinsky_shapes", name: "Kandinsky Shapes", desc: "Scattered circles, lines, and triangles arranged in Kandinsky-style compositional counterpoint, R=Metallic", category: "Abstract Art", defaults: { n_circles: 12, n_lines: 10, n_triangles: 6 } },
    { id: "abstract_mondrian_grid", name: "Mondrian Grid", desc: "Recursive axis-aligned rectangular grid with thick black grid lines and primary-contrast cell tones — De Stijl neoplasticism", category: "Abstract Art", defaults: { min_splits: 3, max_splits: 6 } },
    { id: "abstract_op_art_circles", name: "Op Art Circles", desc: "Concentric high-frequency ring illusion from an off-center origin — Bridget Riley illusory motion, R=Metallic", category: "Abstract Art", defaults: { ring_freq: 40.0 } },
    { id: "abstract_op_art_waves", name: "Op Art Waves", desc: "Tight parallel stripes warped by a slow sinusoidal wave — op-art illusory-motion grid, G=Roughness", category: "Abstract Art", defaults: { freq: 30.0, wave_amp: 0.08, wave_freq: 3.0 } },
    { id: "abstract_suprematism", name: "Suprematism", desc: "Malevich-style asymmetric hard-edged rectangles of varying rotation — clean geometric suprematist forms, R=Metallic", category: "Abstract Art", defaults: { n_forms: 7 } },
    { id: "abstract_futurist_motion", name: "Futurist Motion", desc: "Speed-blur streaks fanned along a directional axis — Balla / Boccioni dynamism captured as spec motion, G=Roughness", category: "Abstract Art", defaults: { n_lines: 90, blur_sigma: 1.5 } },
    { id: "abstract_minimalist_stripe", name: "Minimalist Stripe", desc: "Large flat horizontal bands with subtle hand-painted wash — Agnes Martin / Donald Judd minimalism, B=Clearcoat", category: "Abstract Art", defaults: { n_bands: 6 } },
    { id: "abstract_hard_edge_field", name: "Hard Edge Field", desc: "Ellsworth Kelly / Frank Stella flat color blocks with razor-sharp half-plane boundaries, R=Metallic", category: "Abstract Art", defaults: { n_blocks: 14 } },
    { id: "abstract_color_field_bleed", name: "Color Field Bleed", desc: "Frankenthaler soak-stain — large blurred color regions with irregular bleeding edges, B=Clearcoat", category: "Abstract Art", defaults: { num_fields: 4, bleed: 0.06 } },
    { id: "abstract_fluid_acrylic_pour", name: "Fluid Acrylic Pour", desc: "Swirling marbled fluid-acrylic pour cells from domain-warped turbulence — gravity-pour cell structure, R=Metallic", category: "Abstract Art", defaults: { swirl_freq: 6.0, turb_scale: 40.0 } },
    { id: "abstract_ink_wash_gradient", name: "Ink Wash Gradient", desc: "Sumi-e ink wash with irregular bleed boundary and small dropped ink blots in the darker end, G=Roughness", category: "Abstract Art", defaults: { edge_bleeds: 12 } },
    { id: "abstract_neon_glitch", name: "Neon Glitch", desc: "Digital glitch artifacts — horizontal slice offsets, scanline banding, and datamosh rectangular blocks, R=Metallic", category: "Abstract Art", defaults: { n_slices: 30, bar_density: 0.08 } },
    { id: "abstract_retro_wave", name: "Retro Wave", desc: "Synthwave perspective floor grid with soft sun gradient above a horizon — 80s vapourwave aesthetic, R=Metallic", category: "Abstract Art", defaults: { horizon_frac: 0.55, grid_freq_x: 28.0, grid_freq_y: 18.0 } },
    { id: "abstract_bauhaus_forms", name: "Bauhaus Forms", desc: "Circle, square, and triangle primary forms arranged with Bauhaus hierarchical balance, R=Metallic", category: "Abstract Art", defaults: { n_primitives: 9 } },
];

// =============================================================================
// v6.2.z MONOLITHIC WAVE — Catalog-only entries.
// These are full color-finish / monolithic entries and must never live in the
// SPEC_PATTERNS catalog, which is spec-only.
// =============================================================================
const MONOLITHIC_WAVE = [
    // --- Racing Livery Styles ---
    { id: "rl_nascar_classic", name: "NASCAR Classic", desc: "Throwback stock car paint — high-gloss clearcoat with subtle chrome accents, perfect for late-model stock car liveries and retro oval tributes", swatch: "#1a1a2e", category: "Racing Livery Styles", tags: ["racing", "classic", "stock-car", "oval"], colorSafe: true },
    { id: "rl_f1_carbon_wing", name: "F1 Carbon Wing", desc: "Exposed carbon-fiber aero weave with satin clear — modern Formula 1 wing and chassis panel look for open-wheel prototype builds", swatch: "#141418", category: "Racing Livery Styles", tags: ["racing", "f1", "carbon", "aero"], colorSafe: false },
    { id: "rl_gt3_pearl", name: "GT3 Pearl", desc: "Modern GT3 customer-car pearl base with sponsor-ready flat panels and deep pearlescent shift — production-racing clean", swatch: "#e8ecef", category: "Racing Livery Styles", tags: ["racing", "gt3", "pearl", "sponsor"], colorSafe: true },
    { id: "rl_lmp_silver_arrow", name: "LMP Silver Arrow", desc: "Brushed-aluminum prototype look recalling the unpainted Mercedes Silver Arrows — ultra-low-drag bare-metal Le Mans prototype aesthetic", swatch: "#b8bcc2", category: "Racing Livery Styles", tags: ["racing", "lmp", "silver", "le-mans"], colorSafe: false },
    { id: "rl_rally_mud_splat", name: "Rally Mud Splat", desc: "Realistic rally-car mud and gravel damage — flung slurry, rock chips, and drying dirt fans over a hard-charging WRC livery base", swatch: "#5a4632", category: "Racing Livery Styles", tags: ["racing", "rally", "weathered", "dirty"], colorSafe: true },
    { id: "rl_drift_wrap", name: "Drift Wrap", desc: "Vinyl-wrap drift-car look with satin seams, edge lift, and loud sponsor-block composition — Formula D / D1GP street-racer aesthetic", swatch: "#e84a5f", category: "Racing Livery Styles", tags: ["racing", "drift", "vinyl", "street"], colorSafe: true },
    // --- Vintage Styles ---
    { id: "v_70s_stripes", name: "70s Stripes", desc: "Bold horizontal stripe era — wide earth-tone bands, orange-to-brown fades, and the unmistakable wedge-shape 70s graphic confidence", swatch: "#c06a2a", category: "Vintage Styles", tags: ["vintage", "70s", "stripes", "retro"], colorSafe: true },
    { id: "v_80s_neon_wedge", name: "80s Neon Wedge", desc: "Miami-Vice pastel neon on a wedge-era body — hot pink, teal, and chrome-letter sponsor text evoking arcade cabinets and Testarossas", swatch: "#ff4fb3", category: "Vintage Styles", tags: ["vintage", "80s", "neon", "miami"], colorSafe: true },
    { id: "v_90s_racing_decal", name: "90s Racing Decal", desc: "Early sponsor-decal era with die-cut logos, bold primary blocks, and glossy touring-car clearcoat — peak ITC/BTCC livery energy", swatch: "#1e6edb", category: "Vintage Styles", tags: ["vintage", "90s", "decal", "touring"], colorSafe: true },
    { id: "v_classic_hot_rod", name: "Classic Hot Rod", desc: "Metalflake candy base with layered traditional flame jobs licking up the cowl — hand-painted Kustom Kulture hot-rod heritage", swatch: "#8a0d1a", category: "Vintage Styles", tags: ["vintage", "hot-rod", "flames", "flake"], colorSafe: true },
    { id: "v_muscle_car_stripe", name: "Muscle Car Stripe", desc: "American-muscle dual racing stripes over a deep solid body — classic Shelby/Camaro/Challenger stripe package in flat or gloss", swatch: "#0a2d5c", category: "Vintage Styles", tags: ["vintage", "muscle", "stripes", "american"], colorSafe: true },
    { id: "v_touring_car_livery", name: "Touring Car Classic", desc: "60s GT and touring-car livery — ivory body, single contrasting nose band, and small roundel-style race numerals for Goodwood grids", swatch: "#f2ead6", category: "Vintage Styles", tags: ["vintage", "gt", "60s", "goodwood"], colorSafe: true },
    // --- Fantasy / Sci-Fi ---
    { id: "sf_hologram_shift", name: "Hologram Shift", desc: "Full rainbow hologram finish cycling through the spectrum at every angle — maximum prismatic interference for show-car and concept builds", swatch: "linear-gradient(135deg, #ff00aa 0%, #00ffd9 50%, #ffd900 100%)", category: "Fantasy / Sci-Fi", tags: ["sci-fi", "hologram", "rainbow", "prismatic"], colorSafe: false },
    { id: "sf_energy_core", name: "Energy Core", desc: "Glowing reactor-core look with pulsing inner luminescence and dark armored outer shell — powered-up exotic sci-fi vehicle energy", swatch: "#1affd9", category: "Fantasy / Sci-Fi", tags: ["sci-fi", "glow", "reactor", "energy"], colorSafe: true },
    { id: "sf_stealth_matte", name: "Stealth Matte", desc: "Radar-absorbing ultra-matte black with micro-faceted surface and zero reflection — F-117/B-2-inspired low-observable coating", swatch: "#0c0c10", category: "Fantasy / Sci-Fi", tags: ["sci-fi", "stealth", "matte", "military"], colorSafe: false },
    { id: "sf_plasma_flame", name: "Plasma Flame", desc: "Plasma-blue fire effect with core-to-edge temperature gradient and ionized halo — electric arc flames dancing across the body", swatch: "#1e90ff", category: "Fantasy / Sci-Fi", tags: ["sci-fi", "plasma", "fire", "electric"], colorSafe: false },
    { id: "sf_cyber_circuit", name: "Cyber Circuit", desc: "Neon circuit-board overlay with glowing PCB trace network and soldered-node highlights — Tron-grid cyberpunk tech aesthetic", swatch: "#00ff88", category: "Fantasy / Sci-Fi", tags: ["sci-fi", "cyberpunk", "circuit", "tron"], colorSafe: false },
    { id: "sf_void_crystal", name: "Void Crystal", desc: "Dark crystal-facet monolith with internal refraction catching faint violet light — obsidian alien-gemstone sci-fi show finish", swatch: "#1a0833", category: "Fantasy / Sci-Fi", tags: ["sci-fi", "crystal", "void", "dark"], colorSafe: false },
    // --- Weathered ---
    { id: "w_barn_find", name: "Barn Find", desc: "Decades-of-neglect patina — dust layer, cobwebs, bird droppings, and faded pigment revealing primer — authentic abandoned-in-garage storytelling", swatch: "#8a7a5c", category: "Weathered", tags: ["weathered", "barn-find", "dust", "patina"], colorSafe: true },
    { id: "w_rust_belt", name: "Rust Belt", desc: "Aggressive rust weathering with flaking paint, deep oxide scale, and sheet-metal perforation — Midwest-winter salt-damage level oxidation", swatch: "#8a3a12", category: "Weathered", tags: ["weathered", "rust", "oxidation", "industrial"], colorSafe: true },
    { id: "w_sun_faded", name: "Sun Faded", desc: "UV-faded factory paint with horizontal-surface bleaching, chalked clearcoat, and washed-out pigment — Arizona parking-lot decade-of-sun", swatch: "#b8a890", category: "Weathered", tags: ["weathered", "faded", "uv", "sun"], colorSafe: true },
    { id: "w_salt_corrosion", name: "Salt Corrosion", desc: "Coastal salt-spray damage with white crystalline deposits, pitted chrome, and galvanic corrosion around fasteners — beach-town daily-driver", swatch: "#a8b0a4", category: "Weathered", tags: ["weathered", "salt", "corrosion", "coastal"], colorSafe: true },
    { id: "w_burn_marks", name: "Burn Marks", desc: "Fire-scorched metal with heat-bluing oxide bands, soot deposits, and charred paint blisters — post-engine-bay-fire or arson aftermath look", swatch: "#2a1a14", category: "Weathered", tags: ["weathered", "burn", "fire", "scorched"], colorSafe: true },
    { id: "w_acid_wash", name: "Acid Wash", desc: "Chemical etching texture with eaten-through clearcoat, exposed primer patches, and irregular bright-rimmed corrosion blooms — industrial spill damage", swatch: "#5c6a62", category: "Weathered", tags: ["weathered", "acid", "chemical", "etched"], colorSafe: true },
    // --- Special Effects ---
    { id: "fx_color_shift_ultra", name: "Color Shift Ultra", desc: "Extreme 4-color angle-dependent shift cycling through pink, gold, teal, and violet — maximum-interference pigment custom-paint hero finish", swatch: "linear-gradient(135deg, #ff3388 0%, #ffd926 33%, #1ae6d9 66%, #991acc 100%)", category: "Special Effects", tags: ["fx", "color-shift", "chameleon", "4-color"], colorSafe: false },
    { id: "fx_glitter_storm", name: "Glitter Storm", desc: "Dense multi-size glitter flakes in a deep glass clearcoat — from fine pearl dust to jumbo holographic confetti particles all at once", swatch: "#f8d850", category: "Special Effects", tags: ["fx", "glitter", "flake", "sparkle"], colorSafe: true },
    { id: "fx_wet_look_mirror", name: "Wet Look Mirror", desc: "Hyper-glossy wet-mirror surface with liquid clearcoat depth and razor-sharp reflections — showroom-floor photoshoot-grade gloss", swatch: "#f5f7fa", category: "Special Effects", tags: ["fx", "wet", "mirror", "gloss"], colorSafe: true },
    { id: "fx_liquid_metal", name: "Liquid Metal (T-1000)", desc: "Fluid metal surface captured mid-ripple with mercury-like flow turbulence and chromatic interference — T-1000 terminator aesthetic", swatch: "#b8bcc4", category: "Special Effects", tags: ["fx", "liquid", "metal", "chrome"], colorSafe: false },
    { id: "fx_aurora_wave", name: "Aurora Wave", desc: "Northern-lights shifting curtains flowing across the body with green-to-violet plasma bands and soft stellar backdrop haze", swatch: "linear-gradient(135deg, #00e676 0%, #1a237e 50%, #6a1b9a 100%)", category: "Special Effects", tags: ["fx", "aurora", "northern-lights", "glow"], colorSafe: false },
    { id: "fx_galaxy_dust", name: "Galaxy Dust", desc: "Deep-space starfield embedded in a rich cosmic-color base — distant galaxies, nebulae haze, and pinpoint micro-flake stars at every angle", swatch: "#1a0833", category: "Special Effects", tags: ["fx", "galaxy", "stars", "space"], colorSafe: false },
].filter(m => !REMOVED_SPECIAL_IDS.has(m.id));

MONOLITHICS.push(...MONOLITHIC_WAVE);

// =============================================================================
// MONOLITHIC_GROUPS — sub-tab navigation buckets for the MONOLITHICS picker.
// Mirrors SPEC_PATTERN_GROUPS pattern: category label -> array of monolithic ids.
// Only the new v6.2.z themed waves are grouped here; legacy monolithics remain
// discoverable via the default "All" picker view.
// =============================================================================
const MONOLITHIC_GROUPS = {
    "Racing Livery Styles": [
        "rl_nascar_classic", "rl_f1_carbon_wing", "rl_gt3_pearl",
        "rl_lmp_silver_arrow", "rl_rally_mud_splat", "rl_drift_wrap"
    ],
    "Vintage Styles": [
        "v_70s_stripes", "v_80s_neon_wedge", "v_90s_racing_decal",
        "v_classic_hot_rod", "v_muscle_car_stripe", "v_touring_car_livery"
    ],
    "Fantasy / Sci-Fi": [
        "sf_hologram_shift", "sf_energy_core", "sf_stealth_matte",
        "sf_plasma_flame", "sf_cyber_circuit", "sf_void_crystal"
    ],
    "Weathered": [
        "w_barn_find", "w_rust_belt", "w_sun_faded",
        "w_salt_corrosion", "w_burn_marks", "w_acid_wash"
    ],
    "Special Effects": [
        "fx_color_shift_ultra", "fx_glitter_storm", "fx_wet_look_mirror",
        "fx_liquid_metal", "fx_aurora_wave", "fx_galaxy_dust"
    ],
};

// =============================================================================
// SPEC PATTERN GROUPS — sub-tab navigation for SPEC_PATTERNS picker
// =============================================================================
const SPEC_PATTERN_GROUPS = {
    "Structure":   ["banded_rows", "concentric_ripple", "hex_cells", "chevron_bands", "wave_bands", "gradient_bands", "split_bands", "diagonal_bands"],
    "Metallic":    ["flake_scatter", "diamond_dust", "metallic_sand", "holographic_flake", "crystal_shimmer", "stardust_fine", "pearl_micro", "gold_flake", "brushed_sparkle", "crushed_glass", "prismatic_dust"],
    "Coating":     ["depth_gradient"],
    "Texture":     ["orange_peel_texture", "aniso_grain", "aniso_grain_deep"],
    // 2026-04-19 HEENAN H2: 15 SPEC_PATTERNS were ungrouped — silent-Misc-tab
    // bug. Each was already accessible via SPECIAL_GROUPS (Material World ▸
    // Patterns & Effects, etc.) but missing from the spec-pattern picker.
    // Added each to its category-correct group below — `acid_etch`,
    // `rust_bloom`, `lava_crack` to Weathering; `plasma_turbulence`,
    // `magnetic_field`, `prismatic_shatter`, `heat_distortion`,
    // `diffraction_grating`, `quantum_noise` to Optical; `galaxy_swirl`,
    // `reptile_scale`, `neural_dendrite` to Natural; `voronoi_fracture`,
    // `diamond_lattice` to Geometric; `woven_mesh` to Carbon & Weave.
    "Weathering":  ["wear_scuff", "spec_rust_bloom", "spec_patina_verdigris", "spec_oxidized_pitting", "spec_heat_scale", "spec_galvanic_corrosion", "spec_stress_fractures", "spec_battle_scars", "spec_worn_edges", "spec_peeling_clear", "spec_sandblast_strip", "spec_micro_chips", "spec_aged_matte", "acid_etch", "rust_bloom", "lava_crack"],
    // 2026-04-19 HEENAN HP3 — `diffraction_grating` was renamed to
    // `spec_diffraction_grating_cd` (cross-registry collision fix).
    // 2026-04-19 HEENAN H4HR-5: `gravity_well` SPEC renamed → `spec_gravity_well`.
    "Optical":     ["interference_bands", "spec_fresnel_gradient", "spec_caustic_light", "spec_diffraction_grating", "spec_retroreflective", "spec_velvet_sheen", "spec_sparkle_flake", "spec_iridescent_film", "spec_anisotropic_radial", "spec_bokeh_scatter", "spec_light_leak", "spec_subsurface_depth", "spec_chromatic_aberration", "plasma_turbulence", "magnetic_field", "prismatic_shatter", "heat_distortion", "spec_diffraction_grating_cd", "quantum_noise", "spec_gravity_well", "sonic_boom"],
    "Organic":     ["marble_vein", "cloud_wisps", "cloud_wisps_warm", "cloud_wisps_cool"],
    // 2026-04-19 HEENAN H4HR-6/7/8: 3 sparkle SPEC entries renamed → spec_sparkle_*
    // (cross-registry collision fix vs MONOLITHIC sparkle_* siblings).
    "Sparkle":     ["micro_sparkle", "micro_sparkle_warm", "micro_sparkle_cool", "sparkle_rain", "spec_sparkle_constellation", "sparkle_nebula", "spec_sparkle_firefly", "sparkle_shattered", "spec_sparkle_champagne", "sparkle_comet", "sparkle_galaxy_swirl", "sparkle_electric_field"],
    // 2026-04-19 HEENAN HP2 + H4HR-4 — `carbon_weave` → `spec_carbon_weave`,
    // `oil_slick` → `spec_oil_slick` (both cross-registry collision fixes).
    "Misc":        ["panel_zones", "spiral_sweep", "spec_carbon_weave", "crackle_network", "flow_lines", "micro_facets", "moire_overlay", "pebble_grain", "radial_sunburst", "topographic_steps", "wave_ripple", "patina_bloom", "electric_branches", "circuit_trace", "spec_oil_slick", "meteor_impact", "fractal_discharge"],
    "Brushed":     ["brushed_linear", "brushed_linear_warm", "brushed_linear_cool", "brushed_diagonal", "brushed_cross", "brushed_radial", "brushed_arc", "hairline_polish", "lathe_concentric", "bead_blast_uniform", "orbital_swirl", "buffer_swirl", "wire_brushed_coarse", "hand_polished"],
    "Guilloché":   ["guilloche_barleycorn", "guilloche_hobnail", "guilloche_waves", "guilloche_sunray", "guilloche_moire_eng", "jeweling_circles", "knurl_diamond", "knurl_straight", "face_mill_bands", "fly_cut_arcs", "engraved_crosshatch", "edm_dimple"],
    "Carbon & Weave": ["spec_carbon_2x2_twill", "spec_carbon_plain_weave", "spec_carbon_3k_fine", "spec_carbon_forged", "spec_carbon_wet_layup", "spec_kevlar_weave", "spec_fiberglass_chopped", "spec_woven_dyneema", "spec_mesh_perforated", "spec_expanded_metal", "spec_chainlink_fence", "spec_ballistic_weave", "woven_mesh"],
    "Clearcoat":   ["cc_panel_pool", "cc_drip_runs", "cc_fish_eye", "cc_overspray_halo", "cc_edge_thin", "cc_masking_edge", "cc_spot_polish", "cc_gloss_stripe", "cc_wet_zone", "cc_panel_fade"],
    "Geometric":   ["spec_faceted_diamond", "spec_hammered_dimple", "spec_knurled_diamond", "spec_knurled_straight", "spec_architectural_grid", "spec_hexagonal_tiles", "spec_brick_mortar", "spec_corrugated_panel", "spec_riveted_plate", "spec_weld_seam", "spec_stamped_emboss", "spec_cast_surface", "voronoi_fracture", "diamond_lattice"],
    // 2026-04-19 HEENAN H2 (extended): added remaining Natural / Optical /
    // Sparkle / Weathering / Carbon un-prefixed siblings so
    // the spec-pattern picker sees them. Each was already accessible via
    // SPECIAL_GROUPS but missing from SPEC_PATTERN_GROUPS.
    "Natural":     ["spec_wood_grain_fine", "spec_wood_burl", "spec_stone_granite", "spec_stone_marble", "spec_water_ripple_spec", "spec_coral_reef", "spec_snake_scales", "spec_fish_scales", "spec_leaf_venation", "spec_terrain_erosion", "spec_crystal_growth", "spec_lava_flow", "galaxy_swirl", "reptile_scale", "neural_dendrite", "sand_dune", "fungal_network", "smoke_tendril", "crystal_growth"],
    "Surface Treatment": ["spec_electroplated_chrome", "spec_anodized_texture", "spec_powder_coat_texture", "spec_thermal_spray", "spec_electroformed_texture", "spec_pvd_coating", "spec_shot_peened", "spec_laser_etched"],
    "Exotic":      ["spec_liquid_metal", "spec_chameleon_flake", "spec_xirallic_crystal", "spec_holographic_foil", "spec_oil_film_thick", "spec_magnetic_ferrofluid", "spec_aerogel_surface", "spec_damascus_steel_spec"],
    "Racing":      ["tire_rubber_transfer", "vinyl_wrap_texture", "paint_drip_edge", "racing_tape_residue", "sponsor_deboss", "heat_discoloration", "salt_spray_corrosion", "track_grime"],
    "Sponsor & Vinyl": ["vinyl_seam", "decal_lift_edge", "sponsor_emboss_v2", "sticker_bubble_film", "vinyl_stretched"],
    "Race Wear":   ["tire_smoke_residue", "brake_dust_buildup", "oil_streak_panel", "gravel_chip_field", "wax_streak_polish"],
    "Premium":     ["mother_of_pearl_inlay", "anodized_rainbow", "frosted_glass_etch", "gold_leaf_torn", "copper_patina_drip"],
    "Race Heritage": ["checker_flag_subtle", "drag_strip_burnout", "pit_lane_stripes", "victory_lap_confetti", "sponsor_tape_vinyl", "race_number_ghost"],
    "Mechanical":    ["exhaust_pipe_scorch", "radiator_grille_mesh", "engine_bay_grime", "tire_smoke_streaks", "undercarriage_spray", "suspension_rust_ring"],
    "Weather & Track": ["rain_droplet_beads", "mud_splatter_random", "wet_track_gloss", "dry_dust_film", "morning_dew_fog", "tarmac_grit_embed"],
    "Artistic":      ["brushstroke_bold", "crayon_wax_resist", "airbrush_gradient_bloom", "spray_paint_drip", "stippled_dots_fine", "halftone_print"],
    "Abstract Art":  ["abstract_expressionist_splatter", "abstract_cubist_facets", "abstract_rothko_field", "abstract_kandinsky_shapes", "abstract_mondrian_grid", "abstract_op_art_circles", "abstract_op_art_waves", "abstract_suprematism", "abstract_futurist_motion", "abstract_minimalist_stripe", "abstract_hard_edge_field", "abstract_color_field_bleed", "abstract_fluid_acrylic_pour", "abstract_ink_wash_gradient", "abstract_neon_glitch", "abstract_retro_wave", "abstract_bauhaus_forms"],
};

// =============================================================================
// GROUP MAPS — Bases and patterns (sub-tab navigation); SPECIAL_GROUPS is above.
//
// Conventions:
//  - Each group key becomes a tab/section heading in the picker UI.
//  - Use a leading "★" to flag premium/curated tiers (Enhanced Foundation,
//    SHOKK Series, COLORSHOXX, MORTAL SHOKK, NEON UNDERGROUND, Anime Inspired).
//  - Every base ID listed here MUST exist in the BASES array above; the
//    validateFinishData() helper at the end of the file will warn on orphans.
//  - Bases not in any group ARE still rendered through the engine — they're just
//    hidden from the picker. Use that intentionally for legacy/internal IDs.
// =============================================================================
const BASE_GROUPS = {
    "Foundation": ["gloss", "matte", "satin", "semi_gloss", "eggshell", "silk", "wet_look", "clear_matte", "primer", "flat_black", "f_metallic", "f_pearl", "f_chrome", "f_satin_chrome", "f_anodized", "f_brushed", "f_powder_coat", "f_carbon_fiber", "f_frozen", "scuffed_satin", "chalky_base", "living_matte", "ceramic", "piano_black", "f_gel_coat", "f_baked_enamel", "f_vinyl_wrap", "f_pure_white", "f_pure_black", "f_neutral_grey", "f_soft_gloss", "f_soft_matte", "f_clear_satin", "f_warm_white"],
    "★ Enhanced Foundation": ["enh_gloss", "enh_matte", "enh_satin", "enh_metallic", "enh_pearl", "enh_chrome", "enh_satin_chrome", "enh_anodized", "enh_baked_enamel", "enh_brushed", "enh_carbon_fiber", "enh_frozen", "enh_gel_coat", "enh_powder_coat", "enh_vinyl_wrap", "enh_soft_gloss", "enh_soft_matte", "enh_warm_white", "enh_ceramic_glaze", "enh_silk", "enh_eggshell", "enh_primer", "enh_clear_matte", "enh_semi_gloss", "enh_wet_look", "enh_piano_black", "enh_living_matte", "enh_neutral_grey", "enh_clear_satin", "enh_pure_black"],
    // 2026-04-19 TRUE FIVE-HOUR (TF12) — registry truth.
    // validateFinishData runtime exercise surfaced 9 phantom BASE_GROUPS
    // entries: ids referenced by groups but with no entry in BASES. Painter
    // sees a tile in the picker with no display name and clicking it returns
    // nothing. Removed: hydrographic, tinted_lacquer (Candy & Pearl);
    // terrain_chrome (Chrome & Mirror); cerakote_gloss, sub_black (Industrial
    // & Tactical); acid_etch, battle_patina, oxidized, patina_coat (Weathered
    // & Aged). All 9 still render via the engine; if any should ship as a
    // base, add a proper BASES entry — phantoms in BASE_GROUPS are a UX lie.
    "Candy & Pearl": ["candy_burgundy", "candy_cobalt", "candy_emerald", "chameleon", "iridescent", "moonstone", "opal", "spectraflame", "tinted_clear", "tri_coat_pearl", "jelly_pearl", "orange_peel_gloss", "satin_candy", "deep_pearl", "hypershift_spectral"],
    "Carbon & Composite": ["aramid", "carbon_base", "carbon_ceramic", "fiberglass", "forged_composite", "graphene", "hybrid_weave", "kevlar_base", "carbon_weave", "forged_carbon_vis"],
    "Ceramic & Glass": ["ceramic", "ceramic_matte", "crystal_clear", "enamel", "obsidian", "piano_black", "porcelain", "tempered_glass"],
    "Chrome & Mirror": ["antique_chrome", "black_chrome", "blue_chrome", "candy_chrome", "chrome", "dark_chrome", "mirror_gold", "red_chrome", "satin_chrome", "surgical_steel", "electroplated_gold"],
    "Exotic Metal": ["anodized", "brushed_aluminum", "brushed_titanium", "cobalt_metal", "diamond_coat", "frozen", "liquid_titanium", "platinum", "raw_aluminum", "rose_gold", "titanium_raw", "tungsten", "organic_metal", "anodized_exotic", "xirallic", "chromaflair"],
    "Industrial & Tactical": ["armor_plate", "battleship_gray", "blackout", "cerakote", "duracoat", "gunship_gray", "mil_spec_od", "mil_spec_tan", "powder_coat", "sandblasted", "submarine_black", "velvet_floc", "cerakote_pvd"],
    "Metallic Standard": ["candy", "candy_apple", "champagne", "copper", "gunmetal", "gunmetal_satin", "metal_flake_base", "original_metal_flake", "champagne_flake", "fine_silver_flake", "blue_ice_flake", "bronze_flake", "gunmetal_flake", "green_flake", "fire_flake", "metallic", "midnight_pearl", "pearl", "pearlescent_white", "pewter", "satin_metal", "alubeam"],
    "OEM Automotive": ["ambulance_white", "dealer_pearl", "factory_basecoat", "fire_engine", "fleet_white", "police_black", "school_bus", "showroom_clear", "smoked", "taxi_yellow"],
    "Premium Luxury": ["bentley_silver", "bugatti_blue", "ferrari_rosso", "koenigsegg_clear", "lamborghini_verde", "maybach_two_tone", "mclaren_orange", "pagani_tricolore", "porsche_pts", "satin_gold"],
    "Racing Heritage": ["asphalt_grind", "barn_find", "bullseye_chrome", "checkered_chrome", "drag_strip_gloss", "endurance_ceramic", "pace_car_pearl", "race_day_gloss", "rally_mud", "stock_car_enamel", "victory_lane"],
    "Satin & Wrap": ["brushed_wrap", "chrome_wrap", "color_flip_wrap", "frozen_matte", "gloss_wrap", "liquid_wrap", "matte_wrap", "satin_wrap", "stealth_wrap", "textured_wrap"],
    "Weathered & Aged": ["acid_rain", "desert_worn", "galvanized", "heat_treated", "oxidized_copper", "patina_bronze", "rugged", "salt_corroded", "sun_baked", "vintage_chrome", "sun_fade", "crumbling_clear", "destroyed_coat"],
    // NOTE (2026-04-17): "★ SHOKK Series", "★ COLORSHOXX", "★ MORTAL SHOKK",
    // "★ NEON UNDERGROUND", "★ Anime Inspired" were removed from BASE_GROUPS.
    // They are "Specials"-only categories and now live exclusively in
    // SPECIAL_GROUPS via _SPECIALS_SHOKKER / _SPECIALS_ANIME_INSPIRED.
    "Iridescent Insects": ["beetle_jewel", "beetle_rainbow", "beetle_stag", "butterfly_monarch", "butterfly_morpho", "dragonfly_wing", "firefly_glow", "moth_luna", "scarab_gold", "wasp_warning"],
    "Extreme & Experimental": ["bioluminescent", "dark_matter", "electric_ice", "holographic_base", "liquid_obsidian", "mercury", "neutron_star", "plasma_core", "plasma_metal", "prismatic", "quantum_black", "singularity", "solar_panel", "superconductor", "vantablack", "volcanic", "burnt_headers"],
    "Textile-Inspired": ["textile_denim_weave", "textile_canvas_rough", "textile_silk_sheen", "textile_velvet_crush", "textile_burlap_coarse", "textile_suede_soft"],
    "Stone & Mineral": ["stone_slate_matte", "stone_marble_polished", "stone_granite_speckled", "stone_sandstone_warm", "stone_obsidian_mirror", "stone_travertine_cream"],
    "Paint Technique": ["paint_drip_gravity", "paint_splatter_loose", "paint_sponge_stipple", "paint_roller_streak", "paint_spray_fade", "paint_brush_stroke"],
};

const PATTERN_GROUPS = {
    "Abstract & Experimental": ["biomechanical", "biomechanical_2", "fractal", "fractal_2", "fractal_3", "interference", "optical_illusion", "optical_illusion_2", "sound_wave", "stardust", "stardust_2", "voronoi_shatter", "Art_Deco", "Art_Deco_V2", "Art_Deco_V3", "Art_Deco_V4"],
    "Animal & Wildlife": ["camo", "crocodile", "dazzle", "feather", "giraffe", "leopard", "multicam", "snake_skin", "snake_skin_2", "snake_skin_3", "snake_skin_4", "tiger_stripe", "zebra"],
    "Artistic & Cultural": ["aztec", "aztec_alt1", "aztec_alt2", "dragon_scale", "dragon_scale_alt", "fleur_de_lis", "fleur_de_lis_alt", "japanese_wave", "mandala", "mandela_ornate", "mosaic", "muertos_dod1", "muertos_dod2", "rune_symbols", "steampunk_gears", "tribal_norse_runes", "tribal_celtic_spiral"],
    // 2026-04-19 HEENAN H4HR-2: carbon_weave PATTERN renamed → carbon_weave_pattern (cross-registry collision fix).
    "Carbon & Weave": ["carbon_fiber", "kevlar_weave", "nanoweave", "basket_weave_alt", "carbon_alt_1", "carbon_weave_pattern", "exhaust_wrap_alt", "geo_weave", "hex_carbon", "multi_directional", "wavy_carbon"],
    "Decades - 50s": ["decade_50s_diner_checkerboard", "decade_50s_jukebox_arc", "decade_50s_sputnik_orbit", "decade_50s_drivein_marquee", "decade_50s_fallout_shelter", "decade_50s_boomerang_formica", "decade_50s_atomic_reactor", "decade_50s_diner_chrome", "decade_50s_crt_phosphor", "decade_50s_casino_felt"],
    "Decades - 60s": ["decade_60s_peace_sign", "decade_60s_tie_dye_spiral", "decade_60s_lava_lamp_blob", "decade_60s_opart_illusion", "decade_60s_pop_art_halftone", "decade_60s_gogo_check", "decade_60s_caged_square", "decade_60s_peter_max_gradient", "decade_60s_peter_max_alt", "Halftone_Rainbow", "12155818_4903117", "12267458_4936872", "12284536_4958169", "12428555_4988298"],
    "Decades - 70s": ["144644845_10133112", "decade_70s_earth_tone_geo", "248169", "6868396_23455", "78534344_9837553_1", "decade_70s_funk_zigzag", "Groovy_Swirl", "Plad_Wrapper", "decade_70s_studio54_glitter", "decade_70s_pong_pixel"],
    "Decades - 80s": ["decade_80s_pacman_maze", "decade_80s_neon_grid", "decade_80s_rubiks_cube", "decade_80s_rubiks_cube_2", "decade_80s_rubiks_cube_3", "decade_80s_boombox_speaker", "decade_80s_nintendo_dpad", "decade_80s_breakdance_spin", "decade_80s_laser_tag", "decade_80s_leg_warmer"],
    "Decades - 90s": ["decade_90s_grunge_splatter", "decade_90s_nirvana_smiley", "decade_90s_cross_colors", "decade_90s_tamagotchi_egg", "decade_90s_sega_blast", "decade_90s_fresh_prince", "decade_90s_floppy_disk", "decade_90s_rave_zigzag", "decade_90s_y2k_bug", "decade_90s_tribal_tattoo", "decade_90s_dialup_static", "decade_90s_slap_bracelet", "decade_90s_windows95", "decade_90s_chrome_bubble", "decade_90s_rugrats_squiggle", "decade_90s_rollerblade_streak", "decade_90s_beanie_tag", "decade_90s_dot_matrix", "decade_90s_geo_minimal", "decade_90s_sbtb_wall"],
    "Geometric": ["art_deco", "celtic_knot", "chevron", "crosshatch", "greek_key", "pinstripe", "plaid", "tessellation"],
    "Gothic & Dark": ["barbed_wire", "gothic_arch", "gothic_scroll", "iron_emblem", "five_point_star", "razor_wire", "skull", "skull_wings", "spiderweb", "thorn_vine"],
    "Metal & Industrial": ["chainlink", "chainmail", "corrugated", "diamond_plate", "expanded_metal", "hammered", "hex_mesh", "metal_flake", "perforated"],
    "PARADIGM": ["circuitboard", "holographic", "p_tessellation", "p_topographic", "soundwave", "caustic", "dimensional", "fresnel_ghost", "neural", "p_plasma"],
    // 2026-04-19 HEENAN HB2 — `shokk_cipher` pattern was renamed to
    // `shokk_cipher_pattern` to resolve cross-registry id collision.
    "SHOKK PATTERNS": ["data_stream", "glitch_scan", "matrix_rain", "pixel_grid", "shokk_bitrot", "shokk_cipher_pattern", "shokk_firewall", "shokk_hex_dump", "shokk_kernel_panic", "shokk_overflow", "shokk_packet_storm", "shokk_scan_line", "shokk_signal_noise", "shokk_zero_day"],
    "Skate & Surf": ["Billabong_Board", "Billabong_Surf_Style", "Blind_Skateboy", "Bong_Surfer", "Hardcore_Punk", "Hero_Skate", "Hydro_Wave", "Punk_Rock_Zine", "Skate_Deck", "Skate_Reaper_Glowing_Eyes", "Skate_Reaper_Tiled", "Surf_80s", "Surfin_80s", "Thrash_Metal_Skate_Alt", "Thrash_Metal_Skate", "Tiki_Surf"],
    "Weather & Elements": ["aurora_bands", "hailstorm", "lightning", "plasma", "ripple", "sandstorm", "solar_flare", "tornado", "wave"],
    "\u2728 Reactive Shimmer": ["shimmer_quantum_shard", "shimmer_prism_frost", "shimmer_velvet_static", "shimmer_chrome_flux", "shimmer_matte_halo", "shimmer_oil_tension", "shimmer_neon_weft", "shimmer_void_dust", "shimmer_turbine_sheen", "shimmer_spectral_mesh"],
    // FIVE-HOUR SHIFT Win B1 (TWENTY WINS leftover): the "★ Intricate & Ornate"
    // group used to live here with 12 ids that ALL exist in MONOLITHICS, not
    // in PATTERNS. The pattern picker only resolves group ids against PATTERNS,
    // so this group rendered as an empty tab (zero tiles) — silent UX dead end.
    // All 12 ids still ship through the monolithics picker via their canonical
    // groups (e.g. damascus_steel lives in MONOLITHIC_GROUPS["Metals & Forged"],
    // baroque_scrollwork in "Ornate & Decorative", etc.). Removing the dead
    // pattern-picker entry stops the validator from screaming `cross_registry_pattern_group`
    // and stops painters from clicking a tab that contains nothing.
    "\u2728 World Geometry": ["spiral_fern", "zigzag_bands", "radial_calendar", "triple_knot", "diagonal_interlace", "diamond_blanket", "step_fret", "concentric_dot_rings", "medallion_lattice", "eight_point_star", "petal_frieze", "cloud_scroll"],
    // 2026-04-19 HEENAN H4HR-1: dragonfly_wing PATTERN renamed → dragonfly_wing_pattern (cross-registry collision fix).
    "\ud83c\udf3f Natural Textures": ["marble_veining", "wood_burl", "seigaiha_scales", "ammonite_chambers", "peacock_eye", "dragonfly_wing_pattern", "insect_compound", "diatom_radial", "coral_polyp", "birch_bark", "pine_cone_scale", "geode_crystal", "nature_bark_rough", "nature_water_ripple_pat"],
    "\u2699\ufe0f Tech & Circuit": ["circuit_traces", "hex_circuit", "biomech_cables", "dendrite_web", "crystal_lattice", "chainmail_hex", "graphene_hex", "gear_mesh", "vinyl_record", "fiber_optic", "sonar_ping", "waveform_stack"],
    "\ud83c\udfa8 Art Deco & Geometric": ["art_deco_fan", "chevron_stack", "quatrefoil", "herringbone", "basket_weave", "houndstooth", "argyle", "tartan", "op_art_rings", "moire_grid", "lozenge_tile", "ogee_lattice"],
    "\ud83c\udf00 Mathematical & Fractal": ["reaction_diffusion", "fractal_fern", "hilbert_curve", "lorenz_slice", "julia_boundary", "wave_standing", "lissajous_web", "dragon_curve", "diffraction_grating", "perlin_terrain", "phyllotaxis", "truchet_flow", "hypocycloid", "voronoi_relaxed", "wave_ripple_2d", "sierpinski_tri", "geo_fractal_triangle", "geo_hilbert_curve"],
    "\ud83d\udd2e Op-Art & Visual Illusions": ["concentric_op", "checker_warp", "barrel_distort", "moire_interference", "twisted_rings", "spiral_hypnotic", "necker_grid", "radial_pulse", "hex_op", "pinwheel_tiling", "impossible_grid", "rose_curve"],
    "\ud83c\udfd7\ufe0f Art Deco & Textile": ["art_deco_sunburst", "art_deco_chevron", "greek_meander", "star_tile_mosaic", "escher_reptile", "constructivist", "bauhaus_system", "celtic_plait", "cane_weave", "cable_knit", "damask_brocade", "tatami_grid"],
    "\u2728 Surface Accent": ["iridescent_fog", "chrome_delete_edge", "carbon_clearcoat_lock", "racing_scratch", "pearlescent_flip", "frost_crystal", "satin_wax", "uv_night_accent"],
    // 2026-04-25 CODEX 55: taxonomy cleanup for Alpha. Removed tiny junk-drawer
    // categories: Final Collection, Nature-Inspired, Tribal & Cultural, and
    // Advanced Geometric. Their renderable ids now live in the stronger parent
    // families above; unrenderable legacy ids remain metadata-only for old saves.
};

// Alpha UX curation:
// Keep ONLY patterns explicitly mapped into PATTERN_GROUPS.
// This removes unmapped "Other" patterns from the picker/library UI.
{
    const _groupedPatternIds = new Set(Object.values(PATTERN_GROUPS).flat());
    for (let i = PATTERNS.length - 1; i >= 0; i--) {
        if (!_groupedPatternIds.has(PATTERNS[i].id)) PATTERNS.splice(i, 1);
    }
}

// SPECIAL_GROUPS is defined above (structured sections before MONOLITHICS); merged from _SPECIALS_*.

// ================================================================
// COLOR MONOLITHICS - Generated dynamically (260+ entries)
// These monolithics REPLACE paint color, not just light behavior.
// ================================================================
const CLR_PALETTE = {
    racing_red: [217, 20, 20], fire_orange: [242, 115, 13], sunburst_yellow: [242, 217, 26],
    lime_green: [115, 230, 38], forest_green: [26, 115, 38], teal: [13, 166, 166],
    sky_blue: [77, 166, 242], royal_blue: [38, 64, 217], navy: [20, 20, 89],
    purple: [128, 31, 179], violet: [166, 51, 217], hot_pink: [242, 38, 140],
    magenta: [217, 13, 166], white: [242, 242, 242], black: [13, 13, 13],
    gunmetal: [71, 77, 82], silver: [199, 199, 204], gold: [217, 179, 64],
    bronze: [179, 115, 46], copper: [191, 107, 71]
    ,
    crimson: [180, 20, 40],
    coral: [255, 127, 80],
    peach: [255, 180, 130],
    amber: [255, 191, 0],
    honey: [235, 190, 85],
    chartreuse: [127, 255, 0],
    mint: [152, 255, 152],
    sage: [130, 176, 130],
    emerald: [0, 155, 80],
    jade: [0, 168, 120],
    aqua: [0, 200, 200],
    cerulean: [0, 123, 167],
    cobalt: [0, 71, 171],
    indigo: [63, 0, 150],
    lavender: [180, 130, 230],
    plum: [142, 69, 133],
    rose: [255, 80, 120],
    blush: [240, 160, 170],
    maroon: [128, 0, 0],
    burgundy: [128, 0, 32],
    chocolate: [123, 63, 0],
    tan: [210, 180, 140],
    cream: [255, 253, 208],
    ivory: [255, 255, 240],
    slate: [112, 128, 144],
    charcoal: [54, 69, 79],
    graphite: [65, 65, 65],
    pewter: [150, 150, 165],
    champagne: [247, 231, 206],
    titanium: [135, 145, 155]
};
const CLR_MATERIALS = {
    gloss: "Gloss", matte: "Matte", satin: "Satin", metallic: "Metallic",
    pearl: "Pearl", candy: "Candy", chrome: "Chrome", flat: "Flat"
};
const CLR_COLOR_NAMES = {
    racing_red: "Racing Red", fire_orange: "Fire Orange", sunburst_yellow: "Sunburst Yellow",
    lime_green: "Lime Green", forest_green: "Forest Green", teal: "Teal",
    sky_blue: "Sky Blue", royal_blue: "Royal Blue", navy: "Navy",
    purple: "Purple", violet: "Violet", hot_pink: "Hot Pink",
    magenta: "Magenta", white: "White", black: "Black",
    gunmetal: "Gunmetal", silver: "Silver", gold: "Gold", bronze: "Bronze", copper: "Copper"
    ,
    crimson: "Crimson",
    coral: "Coral",
    peach: "Peach",
    amber: "Amber",
    honey: "Honey",
    chartreuse: "Chartreuse",
    mint: "Mint",
    sage: "Sage",
    emerald: "Emerald",
    jade: "Jade",
    aqua: "Aqua",
    cerulean: "Cerulean",
    cobalt: "Cobalt",
    indigo: "Indigo",
    lavender: "Lavender",
    plum: "Plum",
    rose: "Rose",
    blush: "Blush",
    maroon: "Maroon",
    burgundy: "Burgundy",
    chocolate: "Chocolate",
    tan: "Tan",
    cream: "Cream",
    ivory: "Ivory",
    slate: "Slate",
    charcoal: "Charcoal",
    graphite: "Graphite",
    pewter: "Pewter",
    champagne: "Champagne",
    titanium: "Titanium"
};

// Color monolithics: gradient, ghost, multi-color only (no solid — use zone Base + Base Color Mode instead)
const COLOR_MONOLITHICS = [];
const COLOR_MONO_GROUPS = {};
// Solid color + material entries removed: apply solid color via Base Color Mode on any base.

// Gradient entries
const GRADIENT_DEFS = [
    ["grad_fire_fade", "Fire Fade", "racing_red", "fire_orange"],
    ["grad_sunset", "Sunset", "fire_orange", "sunburst_yellow"],
    ["grad_ocean_depths", "Ocean Depths", "sky_blue", "navy"],
    ["grad_forest_canopy", "Forest Canopy", "lime_green", "forest_green"],
    ["grad_twilight", "Twilight", "purple", "navy"],
    ["grad_lava_flow", "Lava Flow", "racing_red", "sunburst_yellow"],
    ["grad_arctic_dawn", "Arctic Dawn", "white", "sky_blue"],
    ["grad_midnight_ember", "Midnight Ember", "black", "racing_red"],
    ["grad_golden_hour", "Golden Hour", "gold", "fire_orange"],
    ["grad_steel_forge", "Steel Forge", "silver", "gunmetal"],
    ["grad_copper_patina", "Copper Patina", "copper", "teal"],
    ["grad_neon_rush", "Neon Rush", "hot_pink", "lime_green"],
    ["grad_bruise", "Bruise", "purple", "black"],
    ["grad_ice_fire", "Ice & Fire", "sky_blue", "racing_red"],
    ["grad_toxic_waste", "Toxic Waste", "lime_green", "sunburst_yellow"],
    ["grad_fire_fade_h", "Fire Fade H", "racing_red", "fire_orange"],
    ["grad_ocean_depths_h", "Ocean Depths H", "sky_blue", "navy"],
    ["grad_twilight_h", "Twilight H", "purple", "navy"],
    ["grad_golden_hour_h", "Golden Hour H", "gold", "fire_orange"],
    ["grad_neon_rush_h", "Neon Rush H", "hot_pink", "lime_green"],
    ["grad_fire_fade_diag", "Fire Fade Diag", "racing_red", "fire_orange"],
    ["grad_ocean_depths_diag", "Ocean Depths Diag", "sky_blue", "navy"],
    ["grad_sunset_diag", "Sunset Diag", "fire_orange", "sunburst_yellow"],
    ["grad_twilight_diag", "Twilight Diag", "purple", "navy"],
    ["grad_fire_vortex", "Fire Vortex", "racing_red", "sunburst_yellow"],
    ["grad_blue_vortex", "Blue Vortex", "sky_blue", "navy"],
    ["grad_gold_vortex", "Gold Vortex", "gold", "black"],
    ["grad_green_vortex", "Green Vortex", "lime_green", "forest_green"],
    ["grad_pink_vortex", "Pink Vortex", "hot_pink", "purple"],
    ["grad_white_vortex", "White Vortex", "white", "gunmetal"],
    ["grad_shadow_vortex", "Shadow Vortex", "gunmetal", "black"],
    ["grad_copper_vortex", "Copper Vortex", "copper", "bronze"],
    ["grad_violet_vortex", "Violet Vortex", "violet", "navy"],
    ["grad_teal_vortex", "Teal Vortex", "teal", "forest_green"],
    // === NEW 2-color combos (vertical default) ===
    ["grad_black_gold", "Black Gold", "black", "gold"],
    ["grad_patriot", "Patriot", "navy", "racing_red"],
    ["grad_frostbite", "Frostbite", "royal_blue", "white"],
    ["grad_neon_violet", "Neon Violet", "hot_pink", "purple"],
    ["grad_aqua_drift", "Aqua Drift", "teal", "sky_blue"],
    ["grad_iron_blood", "Iron Blood", "gunmetal", "racing_red"],
    ["grad_emerald_crown", "Emerald Crown", "forest_green", "gold"],
    ["grad_candy_cane", "Candy Cane", "white", "racing_red"],
    ["grad_chrome_wave", "Chrome Wave", "silver", "royal_blue"],
    ["grad_copper_flame", "Copper Flame", "copper", "racing_red"],
    ["grad_storm_front", "Storm Front", "gunmetal", "sky_blue"],
    ["grad_ultraviolet", "Ultraviolet", "violet", "hot_pink"],
    ["grad_antique_gold", "Antique Gold", "bronze", "gold"],
    ["grad_obsidian", "Obsidian", "black", "gunmetal"],
    ["grad_electric_lime", "Electric Lime", "lime_green", "sunburst_yellow"],
    ["grad_magma", "Magma", "racing_red", "black"],
    ["grad_sapphire_ice", "Sapphire Ice", "royal_blue", "sky_blue"],
    ["grad_rose_gold", "Rose Gold", "hot_pink", "gold"],
    ["grad_forest_night", "Forest Night", "forest_green", "black"],
    ["grad_solar_flare", "Solar Flare", "sunburst_yellow", "racing_red"],
    // === Horizontal variants of new combos ===
    ["grad_black_gold_h", "Black Gold H", "black", "gold"],
    ["grad_patriot_h", "Patriot H", "navy", "racing_red"],
    ["grad_candy_cane_h", "Candy Cane H", "white", "racing_red"],
    ["grad_magma_h", "Magma H", "racing_red", "black"],
    ["grad_rose_gold_h", "Rose Gold H", "hot_pink", "gold"],
    // === Diagonal variants ===
    ["grad_black_gold_diag", "Black Gold Diag", "black", "gold"],
    ["grad_neon_violet_diag", "Neon Violet Diag", "hot_pink", "purple"],
    ["grad_storm_front_diag", "Storm Front Diag", "gunmetal", "sky_blue"],
    ["grad_emerald_crown_diag", "Emerald Crown Diag", "forest_green", "gold"],
    // === Vortex/radial variants ===
    ["grad_patriot_vortex", "Patriot Vortex", "navy", "racing_red"],
    ["grad_neon_violet_vortex", "Neon Violet Vortex", "hot_pink", "purple"],
    ["grad_obsidian_vortex", "Obsidian Vortex", "black", "gunmetal"],
    ["grad_rose_gold_vortex", "Rose Gold Vortex", "hot_pink", "gold"],
    ["grad_solar_vortex", "Solar Vortex", "sunburst_yellow", "racing_red"],
    // === EXPANSION: 22 new 2-color gradients ===
    ["grad_wine_silk", "Wine Silk", "burgundy", "cream"],
    ["grad_midnight_gold", "Midnight Gold", "navy", "gold"],
    ["grad_coral_sea", "Coral Sea", "coral", "cerulean"],
    ["grad_ember_ash", "Ember Ash", "crimson", "charcoal"],
    ["grad_jade_mist", "Jade Mist", "jade", "mint"],
    ["grad_plum_dawn", "Plum Dawn", "plum", "peach"],
    ["grad_amber_night", "Amber Night", "amber", "indigo"],
    ["grad_sage_bronze", "Sage Bronze", "sage", "bronze"],
    ["grad_titanium_fire", "Titanium Fire", "titanium", "crimson"],
    ["grad_ivory_cobalt", "Ivory Cobalt", "ivory", "cobalt"],
    ["grad_honey_slate", "Honey Slate", "honey", "slate"],
    ["grad_rose_midnight", "Rose Midnight", "rose", "navy"],
    ["grad_charcoal_gold", "Charcoal Gold", "charcoal", "gold"],
    ["grad_lavender_dusk", "Lavender Dusk", "lavender", "maroon"],
    ["grad_emerald_night", "Emerald Night", "emerald", "black"],
    ["grad_cream_crimson", "Cream Crimson", "cream", "crimson"],
    ["grad_blush_cobalt", "Blush Cobalt", "blush", "cobalt"],
    ["grad_graphite_amber", "Graphite Amber", "graphite", "amber"],
    ["grad_mint_purple", "Mint Purple", "mint", "purple"],
    ["grad_champagne_navy", "Champagne Navy", "champagne", "navy"],
    ["grad_pewter_rose", "Pewter Rose", "pewter", "rose"],
    ["grad_chocolate_gold", "Chocolate Gold", "chocolate", "gold"],
    // === EXPANSION: 35 new radial/vortex gradients ===
    ["grad_crimson_vortex", "Crimson Vortex", "crimson", "black"],
    ["grad_coral_vortex", "Coral Vortex", "coral", "navy"],
    ["grad_amber_vortex", "Amber Vortex", "amber", "charcoal"],
    ["grad_honey_vortex", "Honey Vortex", "honey", "chocolate"],
    ["grad_emerald_vortex", "Emerald Vortex", "emerald", "black"],
    ["grad_jade_vortex", "Jade Vortex", "jade", "navy"],
    ["grad_aqua_vortex", "Aqua Vortex", "aqua", "indigo"],
    ["grad_cerulean_vortex", "Cerulean Vortex", "cerulean", "black"],
    ["grad_cobalt_vortex", "Cobalt Vortex", "cobalt", "silver"],
    ["grad_indigo_vortex", "Indigo Vortex", "indigo", "gold"],
    ["grad_lavender_vortex", "Lavender Vortex", "lavender", "charcoal"],
    ["grad_plum_vortex", "Plum Vortex", "plum", "gold"],
    ["grad_rose_vortex", "Rose Vortex", "rose", "black"],
    ["grad_blush_vortex", "Blush Vortex", "blush", "navy"],
    ["grad_maroon_vortex", "Maroon Vortex", "maroon", "gold"],
    ["grad_burgundy_vortex", "Burgundy Vortex", "burgundy", "silver"],
    ["grad_chocolate_vortex", "Chocolate Vortex", "chocolate", "gold"],
    ["grad_tan_vortex", "Tan Vortex", "tan", "charcoal"],
    ["grad_cream_vortex", "Cream Vortex", "cream", "cobalt"],
    ["grad_ivory_vortex", "Ivory Vortex", "ivory", "indigo"],
    ["grad_slate_vortex", "Slate Vortex", "slate", "gold"],
    ["grad_charcoal_vortex", "Charcoal Vortex", "charcoal", "crimson"],
    ["grad_graphite_vortex", "Graphite Vortex", "graphite", "amber"],
    ["grad_pewter_vortex", "Pewter Vortex", "pewter", "crimson"],
    ["grad_champagne_vortex", "Champagne Vortex", "champagne", "indigo"],
    ["grad_titanium_vortex", "Titanium Vortex", "titanium", "crimson"],
    ["grad_mint_vortex", "Mint Vortex", "mint", "purple"],
    ["grad_sage_vortex", "Sage Vortex", "sage", "crimson"],
    ["grad_chartreuse_vortex", "Chartreuse Vortex", "chartreuse", "black"],
    ["grad_peach_vortex", "Peach Vortex", "peach", "indigo"],
    ["grad_ruby_vortex", "Ruby Vortex", "crimson", "maroon"],
    ["grad_sapphire_vortex", "Sapphire Vortex", "cobalt", "navy"],
    ["grad_topaz_vortex", "Topaz Vortex", "amber", "chocolate"],
    ["grad_amethyst_vortex", "Amethyst Vortex", "lavender", "indigo"],
    ["grad_opal_vortex", "Opal Vortex", "ivory", "aqua"],
];

// REMOVED: Mirror gradients (all gradm_ entries deleted)

// REMOVED: 3-Color gradients (all grad3_ entries deleted)
// REMOVED: 3-Color gradients (all grad3_ entries deleted)
const GRADIENT_3C_DEFS = [];

COLOR_MONO_GROUPS["Gradient"] = [];
COLOR_MONO_GROUPS["Gradient Radial"] = [];
// REMOVED: Gradient Mirror category
// REMOVED: Gradient 3-Color category
GRADIENT_DEFS.forEach(([id, name, c1, c2]) => {
    const rgb1 = CLR_PALETTE[c1], rgb2 = CLR_PALETTE[c2];
    const hex1 = '#' + rgb1.map(v => v.toString(16).padStart(2, '0')).join('');
    const hex2 = '#' + rgb2.map(v => v.toString(16).padStart(2, '0')).join('');
    const isRadial = id.includes('vortex');
    const cat = isRadial ? "Gradient Radial" : "Gradient";
    COLOR_MONOLITHICS.push({ id, name, desc: `${name} gradient blend`, swatch: hex1, swatch2: hex2, clrCat: cat });
    COLOR_MONO_GROUPS[cat].push(id);
});
// REMOVED: mirror gradient forEach
// REMOVED: 3-color gradient forEach

// Color-Shift Duo entries
// REMOVED: Color Shift Duo (all CS Duo removed) - was CS_DUO_DEFS + forEach
const _CS_DUO_DEFS_REMOVED = [
    ["cs_fire_ice", "Fire & Ice", "racing_red", "sky_blue"],
    ["cs_sunset_ocean", "Sunset Ocean", "fire_orange", "royal_blue"],
    ["cs_gold_emerald", "Gold Emerald", "gold", "forest_green"],
    ["cs_copper_teal", "Copper Teal", "copper", "teal"],
    ["cs_pink_purple", "Pink Purple", "hot_pink", "purple"],
    ["cs_lime_blue", "Lime Blue", "lime_green", "royal_blue"],
    ["cs_red_gold", "Red Gold", "racing_red", "gold"],
    ["cs_navy_silver", "Navy Silver", "navy", "silver"],
    ["cs_violet_teal", "Violet Teal", "violet", "teal"],
    ["cs_bronze_green", "Bronze Green", "bronze", "forest_green"],
    ["cs_black_red", "Black Red", "black", "racing_red"],
    ["cs_white_blue", "White Blue", "white", "royal_blue"],
    ["cs_magenta_gold", "Magenta Gold", "magenta", "gold"],
    ["cs_gunmetal_orange", "Gunmetal Orange", "gunmetal", "fire_orange"],
    ["cs_purple_lime", "Purple Lime", "purple", "lime_green"],
    ["cs_navy_gold", "Navy Gold", "navy", "gold"],
    ["cs_teal_pink", "Teal Pink", "teal", "hot_pink"],
    ["cs_red_black", "Red Black", "racing_red", "black"],
    ["cs_blue_orange", "Blue Orange", "royal_blue", "fire_orange"],
    ["cs_silver_purple", "Silver Purple", "silver", "purple"],
    ["cs_green_gold", "Green Gold", "forest_green", "gold"],
    ["cs_bronze_navy", "Bronze Navy", "bronze", "navy"],
    ["cs_copper_violet", "Copper Violet", "copper", "violet"],
    ["cs_yellow_blue", "Yellow Blue", "sunburst_yellow", "royal_blue"],
    ["cs_pink_teal", "Pink Teal", "hot_pink", "teal"],
    // === NEW Color Shift Duos ===
    ["cs_orange_purple", "Orange Purple", "fire_orange", "purple"],
    ["cs_gold_navy", "Gold Navy", "gold", "navy"],
    ["cs_lime_pink", "Lime Pink", "lime_green", "hot_pink"],
    ["cs_copper_blue", "Copper Blue", "copper", "royal_blue"],
    ["cs_white_red", "White Red", "white", "racing_red"],
    ["cs_black_gold", "Black Gold", "black", "gold"],
    ["cs_silver_red", "Silver Red", "silver", "racing_red"],
    ["cs_teal_orange", "Teal Orange", "teal", "fire_orange"],
    ["cs_purple_gold", "Purple Gold", "purple", "gold"],
    ["cs_navy_orange", "Navy Orange", "navy", "fire_orange"],
    ["cs_green_blue", "Green Blue", "forest_green", "royal_blue"],
    ["cs_bronze_red", "Bronze Red", "bronze", "racing_red"],
    ["cs_violet_gold", "Violet Gold", "violet", "gold"],
    ["cs_magenta_teal", "Magenta Teal", "magenta", "teal"],
    ["cs_gunmetal_lime", "Gunmetal Lime", "gunmetal", "lime_green"],
    ["cs_black_blue", "Black Blue", "black", "royal_blue"],
    ["cs_white_green", "White Green", "white", "forest_green"],
    ["cs_copper_gold", "Copper Gold", "copper", "gold"],
    ["cs_red_purple", "Red Purple", "racing_red", "purple"],
    ["cs_sky_gold", "Sky Gold", "sky_blue", "gold"],
    ["cs_orange_navy", "Orange Navy", "fire_orange", "navy"],
    ["cs_lime_violet", "Lime Violet", "lime_green", "violet"],
    ["cs_silver_teal", "Silver Teal", "silver", "teal"],
    ["cs_bronze_purple", "Bronze Purple", "bronze", "purple"],
    ["cs_pink_gold", "Pink Gold", "hot_pink", "gold"],
    ["cs_black_silver", "Black Silver", "black", "silver"],
    ["cs_white_purple", "White Purple", "white", "purple"],
    ["cs_copper_lime", "Copper Lime", "copper", "lime_green"],
    ["cs_magenta_blue", "Magenta Blue", "magenta", "royal_blue"],
    ["cs_gunmetal_gold", "Gunmetal Gold", "gunmetal", "gold"],
    // === EXPANSION: 20 new CS Duo entries ===
    ["cs_crimson_jade", "Crimson Jade", "crimson", "jade"],
    ["cs_coral_cobalt", "Coral Cobalt", "coral", "cobalt"],
    ["cs_amber_indigo", "Amber Indigo", "amber", "indigo"],
    ["cs_honey_plum", "Honey Plum", "honey", "plum"],
    ["cs_mint_maroon", "Mint Maroon", "mint", "maroon"],
    ["cs_rose_emerald", "Rose Emerald", "rose", "emerald"],
    ["cs_slate_amber", "Slate Amber", "slate", "amber"],
    ["cs_champagne_cobalt", "Champagne Cobalt", "champagne", "cobalt"],
    ["cs_titanium_crimson", "Titanium Crimson", "titanium", "crimson"],
    ["cs_lavender_jade", "Lavender Jade", "lavender", "jade"],
    ["cs_charcoal_honey", "Charcoal Honey", "charcoal", "honey"],
    ["cs_ivory_indigo", "Ivory Indigo", "ivory", "indigo"],
    ["cs_peach_cobalt", "Peach Cobalt", "peach", "cobalt"],
    ["cs_sage_crimson", "Sage Crimson", "sage", "crimson"],
    ["cs_blush_emerald", "Blush Emerald", "blush", "emerald"],
    ["cs_burgundy_gold", "Burgundy Gold", "burgundy", "gold"],
    ["cs_chocolate_mint", "Chocolate Mint", "chocolate", "mint"],
    ["cs_pewter_rose", "Pewter Rose", "pewter", "rose"],
    ["cs_graphite_coral", "Graphite Coral", "graphite", "coral"],
    ["cs_aqua_maroon", "Aqua Maroon", "aqua", "maroon"],
];

// Ghost Gradient entries - gradient base + ghosted pattern overlay [id, name, c1, c2, ghostPattern]
// REMOVED: Ghost gradients (all ghostg_ entries deleted)
const GHOST_GRADIENT_DEFS = [];
// REMOVED: Ghost gradient forEach + category

// Multi-Color Pattern entries - now with real 3-color palettes [id, name, [c1,c2,c3], ptype]
const MC_DEFS = [
    ["mc_usa_flag", "All-American", ["racing_red", "white", "royal_blue"], "swirl"],
    ["mc_rasta", "Rasta", ["racing_red", "sunburst_yellow", "forest_green"], "swirl"],
    ["mc_halloween", "Halloween", ["fire_orange", "black", "purple"], "swirl"],
    ["mc_christmas", "Christmas", ["racing_red", "forest_green", "white"], "swirl"],
    ["mc_miami_vice", "Miami Vice", ["hot_pink", "teal", "white"], "swirl"],
    ["mc_fire_storm", "Fire Storm", ["racing_red", "fire_orange", "sunburst_yellow"], "swirl"],
    ["mc_deep_space", "Deep Space", ["navy", "purple", "white"], "swirl"],
    ["mc_tropical", "Tropical", ["lime_green", "sunburst_yellow", "teal"], "swirl"],
    ["mc_vaporwave", "Vaporwave", ["hot_pink", "purple", "teal"], "swirl"],
    ["mc_earth_tone", "Earth Tone", ["bronze", "forest_green", "sunburst_yellow"], "swirl"],
    ["mc_woodland_camo", "Woodland Camo", ["forest_green", "bronze", "black"], "camo"],
    ["mc_desert_camo", "Desert Camo", ["bronze", "sunburst_yellow", "gunmetal"], "camo"],
    ["mc_urban_camo", "Urban Camo", ["gunmetal", "silver", "black"], "camo"],
    ["mc_snow_camo", "Snow Camo", ["white", "silver", "sky_blue"], "camo"],
    ["mc_neon_camo", "Neon Camo", ["lime_green", "hot_pink", "sunburst_yellow"], "camo"],
    ["mc_blue_camo", "Blue Camo", ["royal_blue", "navy", "sky_blue"], "camo"],
    ["mc_white_marble", "White Marble", ["white", "silver", "gunmetal"], "marble"],
    ["mc_black_marble", "Black Marble", ["black", "gunmetal", "white"], "marble"],
    ["mc_green_marble", "Green Marble", ["forest_green", "lime_green", "white"], "marble"],
    ["mc_red_marble", "Red Marble", ["racing_red", "black", "white"], "marble"],
    ["mc_gold_marble", "Gold Marble", ["gold", "bronze", "black"], "marble"],
    ["mc_paint_splat", "Paint Splatter", ["racing_red", "sunburst_yellow", "royal_blue"], "splatter"],
    ["mc_ink_splat", "Ink Splatter", ["black", "gunmetal", "white"], "splatter"],
    ["mc_neon_splat", "Neon Splatter", ["hot_pink", "lime_green", "sunburst_yellow"], "splatter"],
    ["mc_blood_splat", "Blood Splatter", ["racing_red", "black", "gunmetal"], "splatter"],
];
const MC_CATS = { swirl: "Multi Swirl", camo: "Multi Camo", marble: "Multi Marble", splatter: "Multi Splatter" };
Object.values(MC_CATS).forEach(c => COLOR_MONO_GROUPS[c] = []);
MC_DEFS.forEach(([id, name, colors, ptype]) => {
    const hexes = colors.map(c => '#' + CLR_PALETTE[c].map(v => v.toString(16).padStart(2, '0')).join(''));
    const cat = MC_CATS[ptype];
    COLOR_MONOLITHICS.push({ id, name, desc: `${name} multi-color`, swatch: hexes[0], swatch2: hexes[1], swatch3: hexes[2], mcColors: colors, clrCat: cat });
    COLOR_MONO_GROUPS[cat].push(id);
});

// Merge into MONOLITHICS array
MONOLITHICS.push(...COLOR_MONOLITHICS);

// Final painter-facing guard: SPECIAL_GROUPS drives clickable Specials tiles,
// so keep only ids that resolve through the JS catalog. Python-only or retired
// ids may still exist in backend registries, but they must not create blank UI
// tiles here.
(function pruneUnresolvedSpecialGroups() {
    var liveSpecialIds = new Set();
    if (typeof BASES !== 'undefined') {
        BASES.forEach(function (b) { if (b && b.id) liveSpecialIds.add(b.id); });
    }
    MONOLITHICS.forEach(function (m) { if (m && m.id) liveSpecialIds.add(m.id); });
    Object.keys(SPECIAL_GROUPS).forEach(function (groupName) {
        if (!Array.isArray(SPECIAL_GROUPS[groupName])) return;
        SPECIAL_GROUPS[groupName] = SPECIAL_GROUPS[groupName].filter(function (id) {
            return liveSpecialIds.has(id);
        });
    });
})();

// SPECIAL_GROUPS is already complete (reimagined taxonomy, JS-resolvable IDs only). Do not merge COLOR_MONO_GROUPS.

// Helper: get finish_colors { c1, c2, c3, ghost } for a gradient/mirror/3c/ghost id when MONOLITHICS lookup misses (ensures render always gets colors)
function getFinishColorsForId(id) {
    if (!id || typeof id !== 'string') return null;
    const toHex = (rgb) => '#' + rgb.map(v => v.toString(16).padStart(2, '0')).join('');
    const g = GRADIENT_DEFS.find(([fid]) => fid === id);
    if (g) {
        const [, , c1, c2] = g;
        const rgb1 = CLR_PALETTE[c1], rgb2 = CLR_PALETTE[c2];
        if (!rgb1 || !rgb2) return null;
        return { c1: toHex(rgb1), c2: toHex(rgb2), c3: null, ghost: null };
    }
    const m = GRADIENT_MIRROR_DEFS.find(([fid]) => fid === id);
    if (m) {
        const [, , c1, c2] = m;
        const rgb1 = CLR_PALETTE[c1], rgb2 = CLR_PALETTE[c2];
        if (!rgb1 || !rgb2) return null;
        return { c1: toHex(rgb1), c2: toHex(rgb2), c3: null, ghost: null };
    }
    const t = GRADIENT_3C_DEFS.find(([fid]) => fid === id);
    if (t) {
        const [, , c1, c2, c3] = t;
        const rgb1 = CLR_PALETTE[c1], rgb2 = CLR_PALETTE[c2], rgb3 = CLR_PALETTE[c3];
        if (!rgb1 || !rgb2 || !rgb3) return null;
        return { c1: toHex(rgb1), c2: toHex(rgb2), c3: toHex(rgb3), ghost: null };
    }
    const gh = GHOST_GRADIENT_DEFS.find(([fid]) => fid === id);
    if (gh) {
        const [, , c1, c2, ghostPat] = gh;
        const rgb1 = CLR_PALETTE[c1], rgb2 = CLR_PALETTE[c2];
        if (!rgb1 || !rgb2) return null;
        return { c1: toHex(rgb1), c2: toHex(rgb2), c3: null, ghost: ghostPat || null };
    }
    const mc = MC_DEFS.find(([fid]) => fid === id);
    if (mc) {
        const [, , colors] = mc;
        const rgb1 = CLR_PALETTE[colors[0]], rgb2 = CLR_PALETTE[colors[1]], rgb3 = CLR_PALETTE[colors[2]];
        if (!rgb1 || !rgb2 || !rgb3) return null;
        return { c1: toHex(rgb1), c2: toHex(rgb2), c3: toHex(rgb3), ghost: null };
    }
    return null;
}
if (typeof window !== 'undefined') window.getFinishColorsForId = getFinishColorsForId;

console.log(`[Color Monolithics UI] Added ${COLOR_MONOLITHICS.length} color finishes`);

// Legacy compat: flat array of all finishes (used for old scripts)
const FINISHES = [
    ...BASES.map(b => ({ ...b, cat: "Base" })),
    ...PATTERNS.filter(p => p.id !== "none").map(p => ({ ...p, cat: "Pattern" })),
    ...MONOLITHICS.map(m => ({ ...m, cat: "Special" })),
];

const CATEGORIES = ["Base", "Pattern", "Special"];

// ── Server merge is called from paint-booth-1-data.js (after function is defined) ──

// QUICK_COLORS — perceptually distinct palette for the zone color picker.
// Each color has a contrasting hue from its neighbors so the picker reads cleanly.
const QUICK_COLORS = [
    { label: "Red",    value: "red",    bg: "#CC2222", desc: "Vivid red — racing red, fire engines, classic roadsters" },
    { label: "Orange", value: "orange", bg: "#CC6600", desc: "Warm orange — McLaren papaya, hunter blaze, sunset hues" },
    { label: "Yellow", value: "yellow", bg: "#CCAA00", desc: "Bright yellow — taxi, school bus, hi-vis safety yellow" },
    { label: "Gold",   value: "gold",   bg: "#AA8800", desc: "Warm gold — luxury accents, championship trim, bronze tone" },
    { label: "Green",  value: "green",  bg: "#22AA22", desc: "Pure green — British racing, jungle, Lambo verde" },
    { label: "Blue",   value: "blue",   bg: "#2255CC", desc: "Royal blue — Bugatti, traditional rally, deep ocean" },
    { label: "Purple", value: "purple", bg: "#7733AA", desc: "Royal purple — Plum Crazy, Shokk signature, mystic violet" },
    { label: "Pink",   value: "pink",   bg: "#CC4488", desc: "Hot pink — Petty Pink, magenta, Shokk Pulse rose" },
    { label: "White",  value: "white",  bg: "#DDDDDD", desc: "Bright white — sponsor copy, Stormtrooper, fleet white" },
    { label: "Dark",   value: "dark",   bg: "#222222", desc: "Catches dark/black-ish areas without locking on pure black" },
    { label: "Black",  value: "black",  bg: "#080808", desc: "Pure black — vantablack zones, shadow areas, blackout" },
    { label: "Gray",   value: "gray",   bg: "#777777", desc: "Mid-grey neutral — primer panels, Le Mans gray, gunmetal" },
];

// SPECIAL_COLORS — symbolic targets that aren't a literal hex, used to catch
// pixels that don't match any other zone (the safety-net fill at the bottom of a stack).
const SPECIAL_COLORS = [
    { label: "Remaining", value: "remaining", desc: "Catches every pixel not already assigned to another zone — the safety-net fill" },
];

const INTENSITY_OPTIONS = [
    { id: "10", name: "10%" },
    { id: "20", name: "20%" },
    { id: "30", name: "30%" },
    { id: "40", name: "40%" },
    { id: "50", name: "50%" },
    { id: "60", name: "60%" },
    { id: "70", name: "70%" },
    { id: "80", name: "80%" },
    { id: "90", name: "90%" },
    { id: "100", name: "100%" },
];
const INTENSITY_VALUES = {
    "10": { spec: 0.10, paint: 0.10, bright: 0.10 },
    "20": { spec: 0.20, paint: 0.20, bright: 0.20 },
    "30": { spec: 0.30, paint: 0.30, bright: 0.30 },
    "40": { spec: 0.40, paint: 0.40, bright: 0.40 },
    "50": { spec: 0.50, paint: 0.50, bright: 0.50 },
    "60": { spec: 0.60, paint: 0.60, bright: 0.60 },
    "70": { spec: 0.70, paint: 0.70, bright: 0.70 },
    "80": { spec: 0.80, paint: 0.80, bright: 0.80 },
    "90": { spec: 0.90, paint: 0.90, bright: 0.90 },
    "100": { spec: 1.00, paint: 1.00, bright: 1.00 },
};

// PRESETS — curated multi-zone scaffolds the "New Project" picker exposes.
// Each preset is a complete starting state: zones array (in stack order),
// a friendly name/desc/category for the picker tile, and intensity defaults.
// New presets should default to intensity 100 unless they're a sponsor/decal
// "support" zone, in which case 60–80 keeps them readable under everything else.
const PRESETS = {
    multi_color_show: {
        name: "Multi-Color Show Car",
        desc: "Up to 4 body colors + number + sponsors + dark",
        category: "Show Car",
        zones: [
            { name: "Body Color 1", color: null, base: "metallic", pattern: "holographic_flake", intensity: "100", hint: "Click your PRIMARY body color (e.g. the blue)" },
            { name: "Body Color 2", color: null, base: "chrome", pattern: "hex_mesh", intensity: "100", hint: "Click your SECOND body color (e.g. the yellow)" },
            { name: "Body Color 3", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Third body color (delete if not needed)" },
            { name: "Body Color 4", color: null, base: "pearl", pattern: "stardust", intensity: "80", hint: "Fourth body color (delete if not needed)" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Sponsors / Logos", color: "white", base: "metallic", pattern: "none", intensity: "80", hint: "Most sponsor text is white-ish" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "none", intensity: "80", hint: "Auto-catches dark/black areas without forcing carbon weave" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50", hint: "Catches unclaimed pixels" },
        ]
    },
    single_color_show: {
        name: "Single-Color Show Car",
        desc: "One body color + chrome number + sponsor pop",
        category: "Show Car",
        zones: [
            { name: "Body Color", color: null, base: "candy", pattern: "holographic_flake", intensity: "100", hint: "Click the main body color on your paint" },
            { name: "Car Number", color: null, base: "chrome", pattern: "lightning", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Sponsors / Logos", color: "white", base: "chrome", pattern: "none", intensity: "80", hint: "Click a sponsor or use 'white'" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "none", intensity: "80", hint: "Auto-catches dark areas without forcing carbon weave" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50", hint: "Catches unclaimed pixels" },
        ]
    },
    number_pop: {
        name: "Number Pop",
        desc: "Chrome number steals the show",
        category: "Clean",
        zones: [
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Body Color 1", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Click your primary body color" },
            { name: "Body Color 2", color: null, base: "frozen", pattern: "none", intensity: "80", hint: "Second body color (delete if single-color car)" },
            { name: "Sponsors / Logos", color: "white", base: "metallic", pattern: "none", intensity: "80", hint: "Sponsor areas" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50", hint: "Catches everything else" },
        ]
    },
    sponsor_showcase: {
        name: "Sponsor Showcase",
        desc: "Metallic sponsors pop against matte body",
        category: "Clean",
        zones: [
            { name: "Sponsors / Logos", color: "white", base: "chrome", pattern: "none", intensity: "100", hint: "Click a sponsor area or use 'white'" },
            { name: "Car Number", color: null, base: "metallic", pattern: "metal_flake", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Body Color 1", color: null, base: "matte", pattern: "none", intensity: "80", hint: "Click primary body color" },
            { name: "Body Color 2", color: null, base: "satin", pattern: "none", intensity: "80", hint: "Second body color (delete if not needed)" },
            { name: "Dark / Carbon Areas", color: "dark", base: "blackout", pattern: "carbon_fiber", intensity: "100", hint: "Auto-catches dark areas" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50", hint: "Catches unclaimed pixels" },
        ]
    },
    full_chrome: {
        name: "Full Send Chrome",
        desc: "Mirror chrome on everything",
        category: "Aggressive",
        zones: [
            { name: "All Surfaces", color: "everything", base: "chrome", pattern: "none", intensity: "100", hint: "Covers the entire car" },
        ]
    },
    street_racer: {
        name: "Street Racer",
        desc: "Candy body + chrome carbon number + carbon dark",
        category: "Aggressive",
        zones: [
            { name: "Body Color 1", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Click your primary body color" },
            { name: "Body Color 2", color: null, base: "pearl", pattern: "ripple", intensity: "100", hint: "Second body color (delete if not needed)" },
            { name: "Car Number", color: null, base: "chrome", pattern: "stardust", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "none", intensity: "100", hint: "Auto-catches dark areas without forcing carbon weave" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "80", hint: "Catches unclaimed pixels" },
        ]
    },
    // ===== v4.2 THEME PRESETS =====
    stealth_mode: {
        name: "Stealth Mode",
        desc: "Murdered-out vantablack body + cerakote accents",
        category: "Aggressive",
        zones: [
            { name: "Body", color: null, base: "vantablack", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "cerakote", pattern: "none", intensity: "100", hint: "Click accent/trim areas" },
            { name: "Car Number", color: null, base: "matte", pattern: "none", intensity: "80", hint: "Grab each number color" },
            { name: "Everything Else", color: "remaining", base: "blackout", pattern: "carbon_fiber", intensity: "80" },
        ]
    },
    chameleon_dream: {
        name: "Chameleon Dream",
        desc: "Color-shift body + chrome number + matte sponsors",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, finish: "chameleon_midnight", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "matte", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    carbon_warrior: {
        name: "Carbon Warrior",
        desc: "Chrome carbon fiber body + matte accents",
        category: "Aggressive",
        zones: [
            { name: "Body", color: null, base: "chrome", pattern: "carbon_fiber", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "matte", pattern: "none", intensity: "80", hint: "Click accent areas" },
            { name: "Car Number", color: null, base: "metallic", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "hex_mesh", intensity: "100" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    ice_king: {
        name: "Ice King",
        desc: "Frozen matte body + cracked ice + holographic number",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, base: "frozen_matte", pattern: "cracked_ice", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "holographic_flake", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "frozen_matte", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50" },
        ]
    },
    hot_wheels: {
        name: "Hot Wheels",
        desc: "Spectraflame body + chrome diamond plate accents",
        category: "Show Car",
        zones: [
            { name: "Body", color: null, base: "spectraflame", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "chrome", pattern: "diamond_plate", intensity: "100", hint: "Click accent/trim areas" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "metallic", pattern: "metal_flake", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50" },
        ]
    },
    military_spec: {
        name: "Military Spec",
        desc: "Cerakote multicam body + tactical flat accents",
        category: "Themed",
        zones: [
            { name: "Body", color: null, base: "cerakote", pattern: "multicam", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "duracoat", pattern: "none", intensity: "80", hint: "Click accent/trim areas" },
            { name: "Car Number", color: null, base: "cerakote", pattern: "none", intensity: "80", hint: "Grab number colors" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "none", intensity: "100" },
            { name: "Everything Else", color: "remaining", base: "cerakote", pattern: "none", intensity: "50" },
        ]
    },
    neon_runner: {
        name: "Neon Runner",
        desc: "Blackout body with tron grid + neon glow number",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, base: "blackout", pattern: "tron", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, finish: "neon_glow", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "matte", pattern: "none", intensity: "50" },
            { name: "Everything Else", color: "remaining", base: "blackout", pattern: "none", intensity: "80" },
        ]
    },
    luxury: {
        name: "Luxury",
        desc: "Rose gold body + satin chrome number + pearl sponsors",
        category: "Show Car",
        zones: [
            { name: "Body", color: null, base: "rose_gold", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "satin_chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "pearl", pattern: "none", intensity: "80" },
            { name: "Dark Areas", color: "dark", base: "surgical_steel", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    retro_racer: {
        name: "Retro Racer",
        desc: "Candy body + pinstripe + chrome stardust number",
        category: "Themed",
        zones: [
            { name: "Body", color: null, base: "candy", pattern: "pinstripe", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "stardust", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "metallic", pattern: "none", intensity: "80" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50" },
        ]
    },
    track_veteran: {
        name: "Track Veteran",
        desc: "Metallic battle-worn body + worn chrome number",
        category: "Themed",
        zones: [
            { name: "Body", color: null, base: "metallic", pattern: "battle_worn", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, finish: "worn_chrome", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "satin", pattern: "none", intensity: "80" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "acid_wash", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    // ===== v7.1 RACING PRESETS =====
    dual_shift_demo: {
        name: "COLORSHOXX: Pink to Gold",
        desc: "30-second color shift demo — car shifts from pink to gold with viewing angle",
        category: "Special Effect",
        zones: [
            { name: "Body (Color Shift)", color: null, finish: "cx_pink_to_gold", intensity: "100", hint: "Click ANY body color — COLORSHOXX replaces it with pink-to-gold shift" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "none", intensity: "100" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    dual_shift_blue_orange: {
        name: "COLORSHOXX: Blue to Orange",
        desc: "Complementary color flip — deep blue face-on, vivid orange at edges",
        category: "Special Effect",
        zones: [
            { name: "Body (Color Shift)", color: null, finish: "cx_blue_to_orange", intensity: "100", hint: "Click ANY body color — blue-to-orange color shift" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "metallic", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    shokker_ekg: {
        name: "SHOKKER EKG",
        desc: "Signature Shokker look - EKG heartbeat pattern on chrome body",
        category: "Aggressive",
        zones: [
            { name: "Body Color", color: null, base: "chrome", pattern: "ekg", intensity: "100", hint: "Click your primary body color — chrome + EKG is the Shokker signature" },
            { name: "Car Number", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Sponsors / Logos", color: "white", base: "metallic", pattern: "stardust", intensity: "80", hint: "Click a sponsor or use 'white'" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "hex_mesh", intensity: "100", hint: "Auto-catches dark/black areas" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "60", hint: "Catches unclaimed pixels" },
        ]
    },
    endurance_racer: {
        name: "Endurance Racer",
        desc: "Night racing - high visibility sponsors, glow accents",
        category: "Themed",
        zones: [
            { name: "Body Color", color: null, base: "pearl", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Body Color 2", color: null, base: "metallic", pattern: "none", intensity: "100", hint: "Second body panel color" },
            { name: "Number / Livery", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number/livery colors" },
            { name: "Sponsor Panels", color: "white", base: "chrome", pattern: "holographic_flake", intensity: "100", hint: "Click white/light sponsor areas" },
            { name: "Dark / Carbon", color: "dark", base: "blackout", pattern: "carbon_fiber", intensity: "100", hint: "Auto-catches dark areas" },
            { name: "Accent Trim", color: null, base: "candy", pattern: "lightning", intensity: "80", hint: "Pick any accent color areas" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    drift_machine: {
        name: "Drift Machine",
        desc: "Aggressive tribal flames + worn carbon + chrome numbers",
        category: "Aggressive",
        zones: [
            { name: "Body Color", color: null, base: "candy", pattern: "tribal_flame", intensity: "100", hint: "Click your primary body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "none", intensity: "100" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "drift_marks", intensity: "60" },
        ]
    },
    vintage_racer: {
        name: "Vintage Racer",
        desc: "Classic racing stripes + brushed aluminum + matte body",
        category: "Themed",
        zones: [
            { name: "Body Color", color: null, base: "matte", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Racing Stripes", color: null, base: "gloss", pattern: "racing_stripe", intensity: "100", hint: "Click the stripe color" },
            { name: "Car Number", color: null, base: "metallic", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Metal Panels", color: null, base: "brushed_aluminum", pattern: "none", intensity: "80", hint: "Pick metal/silver areas" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    neon_nights: {
        name: "Neon Nights",
        desc: "Dark body + neon holographic accents + chrome numbers",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, base: "vantablack", pattern: "none", intensity: "100", hint: "Click the main dark body color" },
            { name: "Neon Accents", color: null, base: "candy", pattern: "holographic_flake", intensity: "100", hint: "Click bright accent areas" },
            { name: "Car Number", color: null, base: "chrome", pattern: "plasma", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "chrome", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "blackout", pattern: "none", intensity: "60" },
        ]
    },
};

// =============================================================================
// CUSTOM DUAL COLOR SHIFT — User picks any 2 colors, gets real PBR color shift
// =============================================================================
var _dualShiftTargetZone = -1;

function openDualShiftModal(zoneIndex) {
    _dualShiftTargetZone = (zoneIndex !== undefined) ? zoneIndex : (typeof selectedZoneIndex !== 'undefined' ? selectedZoneIndex : 0);
    var overlay = document.getElementById('dualShiftOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        updateDualShiftPreview();
    }
}

function closeDualShiftModal() {
    var overlay = document.getElementById('dualShiftOverlay');
    if (overlay) overlay.style.display = 'none';
}

function updateDualShiftPreview() {
    var ca = document.getElementById('dualShiftColorA');
    var cb = document.getElementById('dualShiftColorB');
    var hexA = document.getElementById('dualShiftHexA');
    var hexB = document.getElementById('dualShiftHexB');
    var box = document.getElementById('dualShiftPreviewBox');
    if (ca && hexA) hexA.value = ca.value;
    if (cb && hexB) hexB.value = cb.value;
    if (box && ca && cb) {
        box.style.background = 'linear-gradient(135deg, ' + ca.value + ' 0%, ' + cb.value + ' 100%)';
    }
}

// Attach change listeners after DOM ready
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function () {
        var ca = document.getElementById('dualShiftColorA');
        var cb = document.getElementById('dualShiftColorB');
        if (ca) ca.addEventListener('input', updateDualShiftPreview);
        if (cb) cb.addEventListener('input', updateDualShiftPreview);
    });
}

function applyCustomDualShift() {
    var ca = document.getElementById('dualShiftColorA').value;
    var cb = document.getElementById('dualShiftColorB').value;
    var intensity = parseInt(document.getElementById('dualShiftIntensity').value) / 100;

    // Convert hex to 0-255 RGB.
    // 2026-04-18 MARATHON bug #53 (Luger, HIGH): pre-fix, this assumed a
    // 6-char hex and silently produced [nnn, 0, NaN] for a 3-char shorthand
    // like '#f60'. The NaN propagated into the dual_shift register payload,
    // and the painter's shift looked identical to the previous color with
    // no toast. Now expands 3-char CSS shorthand and validates, falling
    // back to white if the painter somehow typed garbage.
    function hexToRgb(hex) {
        hex = (hex || '').toString().replace('#', '').trim();
        // Expand 3-char shorthand ("f60" -> "ff6600") matching CSS rules.
        if (/^[0-9a-fA-F]{3}$/.test(hex)) {
            hex = hex.split('').map(c => c + c).join('');
        }
        if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
            // Fallback to white + surface a console warning so the painter
            // can see why the shift didn't look right (toast added by callers).
            try { console.warn('[SPB] invalid hex color', hex); } catch (_) {}
            return [255, 255, 255];
        }
        return [parseInt(hex.substring(0, 2), 16), parseInt(hex.substring(2, 4), 16), parseInt(hex.substring(4, 6), 16)];
    }

    var rgbA = hexToRgb(ca);
    var rgbB = hexToRgb(cb);

    // Register custom shift on server, then apply as zone finish
    fetch('/api/dual-shift-register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            color_a: rgbA,
            color_b: rgbB,
            shift_intensity: intensity,
            name: ca.toUpperCase() + ' → ' + cb.toUpperCase()
        })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success && data.finish_id) {
            // Apply to the target zone as a monolithic finish
            if (typeof zones !== 'undefined' && _dualShiftTargetZone >= 0 && _dualShiftTargetZone < zones.length) {
                var z = zones[_dualShiftTargetZone];
                z.finish = data.finish_id;
                z.base = null;
                z.pattern = 'none';
                z.finishName = 'Custom Shift: ' + ca.toUpperCase() + ' → ' + cb.toUpperCase();
                // Store custom shift metadata for preset save/restore
                z._customDualShift = { colorA: ca, colorB: cb, intensity: intensity };
                if (typeof renderZones === 'function') renderZones();
                if (typeof renderZoneDetail === 'function') renderZoneDetail(_dualShiftTargetZone);
                if (typeof triggerPreview === 'function') triggerPreview();
            }
            closeDualShiftModal();
            if (typeof showToast === 'function') {
                showToast('Custom Dual Shift applied! Rendering...', 'success');
            }
        } else {
            alert('Failed to register custom shift: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(function (err) {
        console.error('Custom dual shift registration failed:', err);
        alert('Server error: ' + err.message);
    });
}

// =============================================================================
// QUALITY-OF-LIFE CONSTANTS, INDEXED LOOKUPS, AND HELPERS
// Added by the Finish Data Quality pass — non-breaking additions only.
// All previously exported names still resolve identically; these new constants
// give the rest of the app fast lookups, validation, and richer UI metadata.
// =============================================================================

// Default fallback values used by zone scaffolding and preset builders when a
// zone is constructed without explicit overrides. Centralizing them here keeps
// the various callers in sync if we ever want to shift the baseline.
const DEFAULT_BASE_COLOR = "#9999A0";    // neutral mid-grey, neither warm nor cool
const DEFAULT_INTENSITY  = "100";         // full strength — matches preset zones
const DEFAULT_BASE_ID    = "gloss";      // safest non-metallic, sponsor-friendly
const DEFAULT_PATTERN_ID = "none";       // explicit "no pattern" sentinel

// Category visual coding — emoji per category (reused by the picker tabs) plus
// a hex color for any chip/swatch UI that wants to color-code by category.
const CATEGORY_ICONS = {
    "Base":    "🎨",
    "Pattern": "🧩",
    "Special": "✨",
};
const CATEGORY_COLORS = {
    "Base":    "#4488CC",  // blue — solid foundation
    "Pattern": "#AA66DD",  // violet — overlay layer
    "Special": "#DDAA22",  // gold — premium effect
};
const CATEGORY_DESCRIPTIONS = {
    "Base":    "Material foundations — the underlying paint, metal, or wrap that defines how the surface behaves under light.",
    "Pattern": "Overlay graphics — repeating motifs, weaves, and decorative artwork that sit on top of a base finish.",
    "Special": "Monolithic effects — fully self-contained finishes that replace base+pattern with a single curated look.",
};

// Default starter zones used when a fresh project has no preset chosen — gives
// new users a sensible 3-zone scaffold instead of an empty workspace.
const DEFAULT_ZONES = [
    { name: "Body",          color: null,        base: "metallic", pattern: "none",         intensity: "100", hint: "Click your main body color in the picker" },
    { name: "Numbers",       color: null,        base: "chrome",   pattern: "none",         intensity: "100", hint: "Tap each number-panel color" },
    { name: "Everything Else", color: "remaining", base: "gloss",  pattern: "none",         intensity: "60",  hint: "Catches anything not yet claimed" },
];

// =============================================================================
// INDEXED LOOKUPS — O(1) access for what was previously O(n) array scanning.
// =============================================================================
const FINISH_BY_NAME = {};   // lowercased-name -> finish object (BASES + PATTERNS + MONOLITHICS)
const BASES_BY_ID    = {};
const PATTERNS_BY_ID = {};
const SPEC_PATTERNS_BY_ID = {};
const MONOLITHICS_BY_ID   = {};

(function _buildIndexes() {
    try {
        if (typeof BASES !== 'undefined' && Array.isArray(BASES)) {
            for (var i = 0; i < BASES.length; i++) {
                var b = BASES[i];
                if (b && b.id)   BASES_BY_ID[b.id] = b;
                if (b && b.name) FINISH_BY_NAME[String(b.name).toLowerCase()] = b;
            }
        }
        if (typeof PATTERNS !== 'undefined' && Array.isArray(PATTERNS)) {
            for (var j = 0; j < PATTERNS.length; j++) {
                var p = PATTERNS[j];
                if (p && p.id)   PATTERNS_BY_ID[p.id] = p;
                if (p && p.name) FINISH_BY_NAME[String(p.name).toLowerCase()] = p;
            }
        }
        if (typeof SPEC_PATTERNS !== 'undefined' && Array.isArray(SPEC_PATTERNS)) {
            for (var k = 0; k < SPEC_PATTERNS.length; k++) {
                var s = SPEC_PATTERNS[k];
                if (s && s.id)   SPEC_PATTERNS_BY_ID[s.id] = s;
                if (s && s.name) FINISH_BY_NAME[String(s.name).toLowerCase()] = s;
            }
        }
        if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) {
            for (var m = 0; m < MONOLITHICS.length; m++) {
                var mo = MONOLITHICS[m];
                if (mo && mo.id)   MONOLITHICS_BY_ID[mo.id] = mo;
                if (mo && mo.name) FINISH_BY_NAME[String(mo.name).toLowerCase()] = mo;
            }
        }
    } catch (e) {
        // Fail soft — indexes are an accelerator, not a correctness requirement.
        if (typeof console !== 'undefined') console.warn('[finish-data] index build failed', e);
    }
})();

// Common search aliases — synonyms users actually type that don't match the
// canonical name. Resolved by getFinishMetadata before any other lookup.
const FINISH_ALIASES = {
    "matte black":   "flat_black",
    "satin black":   "satin",
    "cf":            "carbon_base",
    "carbon":        "carbon_base",
    "carbon fiber":  "carbon_base",
    "carbon fibre":  "carbon_base",
    "kevlar":        "kevlar_base",
    "vanta":         "vantablack",
    "blackout black": "blackout",
    "stealth":       "stealth_wrap",
    "od green":      "mil_spec_od",
    "rosegold":      "rose_gold",
    "rose":          "rose_gold",
    "raw alu":       "raw_aluminum",
    "alu":           "brushed_aluminum",
    "ti":            "titanium_raw",
    "gunmetal grey": "gunmetal",
    "gunmetal gray": "gunmetal",
};

// Pre-computed counts so a stats bar / dashboard never has to recount on render.
const FINISH_COUNT_BY_CATEGORY = (function () {
    var counts = { Base: 0, Pattern: 0, Special: 0, SpecPattern: 0 };
    try {
        counts.Base        = (typeof BASES        !== 'undefined' ? BASES.length        : 0);
        counts.Pattern     = (typeof PATTERNS     !== 'undefined' ? PATTERNS.length     : 0);
        counts.Special     = (typeof MONOLITHICS  !== 'undefined' ? MONOLITHICS.length  : 0);
        counts.SpecPattern = (typeof SPEC_PATTERNS!== 'undefined' ? SPEC_PATTERNS.length: 0);
    } catch (e) { /* swallow */ }
    return counts;
})();

// =============================================================================
// PUBLIC HELPERS
// =============================================================================

// Look up any finish (base / pattern / spec pattern / monolithic / alias) by id
// or by free-text name. Returns the matched record or null.
function getFinishMetadata(idOrName) {
    if (!idOrName) return null;
    var key = String(idOrName);

    // Direct id matches first — cheapest path.
    if (BASES_BY_ID[key])         return BASES_BY_ID[key];
    if (PATTERNS_BY_ID[key])      return PATTERNS_BY_ID[key];
    if (SPEC_PATTERNS_BY_ID[key]) return SPEC_PATTERNS_BY_ID[key];
    if (MONOLITHICS_BY_ID[key])   return MONOLITHICS_BY_ID[key];

    // Alias resolution then re-attempt the id lookup.
    var lower = key.toLowerCase();
    if (FINISH_ALIASES[lower]) {
        var aliasId = FINISH_ALIASES[lower];
        if (BASES_BY_ID[aliasId])         return BASES_BY_ID[aliasId];
        if (PATTERNS_BY_ID[aliasId])      return PATTERNS_BY_ID[aliasId];
        if (SPEC_PATTERNS_BY_ID[aliasId]) return SPEC_PATTERNS_BY_ID[aliasId];
        if (MONOLITHICS_BY_ID[aliasId])   return MONOLITHICS_BY_ID[aliasId];
    }

    // Fallback — case-insensitive name match across the indexed map.
    return FINISH_BY_NAME[lower] || null;
}

// Validate every BASE/PATTERN appears in its respective *_GROUPS map. Logs
// warnings to the console but never throws — purely an authoring aid.
function validateFinishData() {
    // WIN #18 (Windham, TWENTY WINS shift): extended to also check PHANTOM group
    // entries (group references an id that doesn't exist in the registry — picker
    // tile renders blank, painter clicks it and gets nothing) AND SPEC_PATTERNS
    // ungrouped/duplicate detection. Categorised counts so the painter can see
    // drift at a glance instead of scrolling 100+ "Ungrouped X:" lines.
    var problems = [];
    var counts = {
        ungrouped_base: 0, ungrouped_pattern: 0, ungrouped_spec: 0,
        phantom_base_group: 0, phantom_pattern_group: 0, phantom_spec_group: 0, phantom_special_group: 0,
        cross_registry_pattern_group: 0,
        duplicate_pattern_name: 0, duplicate_spec_name: 0, duplicate_special_group: 0,
        missing_desc: 0, missing_swatch: 0,
    };
    try {
        var hexRe = /^#[0-9A-Fa-f]{6}$/;

        // Build id sets up-front so phantom checks are O(1).
        var baseIds = new Set();
        if (typeof BASES !== 'undefined') BASES.forEach(function (b) { if (b && b.id) baseIds.add(b.id); });
        var patternIds = new Set();
        if (typeof PATTERNS !== 'undefined') PATTERNS.forEach(function (p) { if (p && p.id) patternIds.add(p.id); });
        var monolithicIds = new Set();
        if (typeof MONOLITHICS !== 'undefined') MONOLITHICS.forEach(function (m) { if (m && m.id) monolithicIds.add(m.id); });
        var specIds = new Set();
        if (typeof SPEC_PATTERNS !== 'undefined') SPEC_PATTERNS.forEach(function (s) { if (s && s.id) specIds.add(s.id); });

        // Base group orphan check + PHANTOM check.
        // 2026-04-19 HEENAN H1: BASES that live in the "specials" picker
        // (★ COLORSHOXX, ★ MORTAL SHOKK, ★ NEON UNDERGROUND, ★ ANIME INSPIRED,
        //  Shokk Series, etc.) are intentionally absent from BASE_GROUPS
        // because they're surfaced via SPECIAL_GROUPS instead. Pre-fix the
        // validator was reporting all 85 of them as "Ungrouped BASE", which
        // drowned out the real signal. We now consider a base "grouped" if it
        // appears in EITHER BASE_GROUPS or SPECIAL_GROUPS.
        if (typeof BASES !== 'undefined' && typeof BASE_GROUPS !== 'undefined') {
            var groupedBase = new Set();
            for (var g in BASE_GROUPS) {
                if (!Array.isArray(BASE_GROUPS[g])) continue;
                BASE_GROUPS[g].forEach(function (id) {
                    groupedBase.add(id);
                    if (!baseIds.has(id)) {
                        problems.push('Phantom BASE_GROUPS["' + g + '"] entry: ' + id + ' (id not in BASES)');
                        counts.phantom_base_group++;
                    }
                });
            }
            // HEENAN H1: also count specials as "grouped" for ungrouped detection.
            // (We don't phantom-check SPECIAL_GROUPS here — many specials reference
            //  ids that live in MONOLITHICS rather than BASES. That's a separate
            //  concern handled by the monolithic registry.)
            if (typeof SPECIAL_GROUPS !== 'undefined') {
                var specialOwners = Object.create(null);
                for (var sgKey in SPECIAL_GROUPS) {
                    if (!Array.isArray(SPECIAL_GROUPS[sgKey])) continue;
                    SPECIAL_GROUPS[sgKey].forEach(function (id) {
                        if (!baseIds.has(id) && !monolithicIds.has(id)) {
                            problems.push('Phantom SPECIAL_GROUPS["' + sgKey + '"] entry: ' + id + ' (id not in BASES or MONOLITHICS)');
                            counts.phantom_special_group++;
                        }
                        if (specialOwners[id]) {
                            problems.push('Duplicate SPECIAL_GROUPS entry: ' + id + ' appears in "' + specialOwners[id] + '" and "' + sgKey + '"');
                            counts.duplicate_special_group++;
                        } else {
                            specialOwners[id] = sgKey;
                        }
                        if (baseIds.has(id)) groupedBase.add(id);
                    });
                }
            }
            for (var i = 0; i < BASES.length; i++) {
                var b = BASES[i];
                if (!b || !b.id) continue;
                if (!groupedBase.has(b.id)) { problems.push('Ungrouped BASE: ' + b.id); counts.ungrouped_base++; }
                if (!b.desc || String(b.desc).length < 20) { problems.push('Short/missing desc on BASE: ' + b.id); counts.missing_desc++; }
                if (!b.swatch) { problems.push('Missing swatch on BASE: ' + b.id); counts.missing_swatch++; }
                else if (!hexRe.test(b.swatch) && String(b.swatch).indexOf('linear-gradient') < 0) {
                    problems.push('Non-standard swatch on BASE: ' + b.id + ' (' + b.swatch + ')');
                }
            }
        }

        // Pattern group orphan check + PHANTOM check + cross-registry check.
        // Pattern picker only resolves group ids against PATTERNS, so a group
        // entry pointing at a MONOLITHIC id renders blank in the pattern picker.
        // Flag that as cross_registry (different fix path: move group → SPECIAL_GROUPS).
        if (typeof PATTERNS !== 'undefined' && typeof PATTERN_GROUPS !== 'undefined') {
            var groupedPat = new Set();
            for (var pg in PATTERN_GROUPS) {
                if (!Array.isArray(PATTERN_GROUPS[pg])) continue;
                PATTERN_GROUPS[pg].forEach(function (id) {
                    groupedPat.add(id);
                    if (!patternIds.has(id)) {
                        if (monolithicIds.has(id)) {
                            problems.push('Cross-registry PATTERN_GROUPS["' + pg + '"] entry: ' + id + ' (lives in MONOLITHICS, not PATTERNS — pattern picker tile will render blank; move group to SPECIAL_GROUPS)');
                            counts.cross_registry_pattern_group++;
                        } else {
                            problems.push('Phantom PATTERN_GROUPS["' + pg + '"] entry: ' + id + ' (id not in PATTERNS or MONOLITHICS)');
                            counts.phantom_pattern_group++;
                        }
                    }
                });
            }
            for (var p = 0; p < PATTERNS.length; p++) {
                var pat = PATTERNS[p];
                if (!pat || !pat.id) continue;
                if (!groupedPat.has(pat.id)) { problems.push('Ungrouped PATTERN: ' + pat.id); counts.ungrouped_pattern++; }
                if (!pat.desc || String(pat.desc).length < 20) { problems.push('Short/missing desc on PATTERN: ' + pat.id); counts.missing_desc++; }
            }

            // Duplicate display-name detection in PATTERNS.
            var patternNames = {};
            PATTERNS.forEach(function (pat) {
                if (!pat || !pat.name) return;
                if (patternNames[pat.name]) {
                    problems.push('Duplicate PATTERN name "' + pat.name + '" — ids: ' + patternNames[pat.name] + ', ' + pat.id);
                    counts.duplicate_pattern_name++;
                } else {
                    patternNames[pat.name] = pat.id;
                }
            });
        }

        // SPEC_PATTERNS ungrouped + phantom + duplicate (NEW in Win #18).
        if (typeof SPEC_PATTERNS !== 'undefined' && typeof SPEC_PATTERN_GROUPS !== 'undefined') {
            var groupedSpec = new Set();
            for (var sg in SPEC_PATTERN_GROUPS) {
                if (!Array.isArray(SPEC_PATTERN_GROUPS[sg])) continue;
                SPEC_PATTERN_GROUPS[sg].forEach(function (id) {
                    groupedSpec.add(id);
                    if (!specIds.has(id)) {
                        problems.push('Phantom SPEC_PATTERN_GROUPS["' + sg + '"] entry: ' + id + ' (id not in SPEC_PATTERNS)');
                        counts.phantom_spec_group++;
                    }
                });
            }
            for (var s = 0; s < SPEC_PATTERNS.length; s++) {
                var sp = SPEC_PATTERNS[s];
                if (!sp || !sp.id) continue;
                if (!groupedSpec.has(sp.id)) {
                    problems.push('Ungrouped SPEC_PATTERN: ' + sp.id + ' (lands in Misc tab)');
                    counts.ungrouped_spec++;
                }
            }

            // Duplicate spec display-names.
            var specNames = {};
            SPEC_PATTERNS.forEach(function (sp) {
                if (!sp || !sp.name) return;
                if (specNames[sp.name]) {
                    problems.push('Duplicate SPEC_PATTERN name "' + sp.name + '" — ids: ' + specNames[sp.name] + ', ' + sp.id);
                    counts.duplicate_spec_name++;
                } else {
                    specNames[sp.name] = sp.id;
                }
            });
        }

        if (typeof console !== 'undefined') {
            if (problems.length === 0) {
                console.log('[finish-data] validateFinishData: clean — no issues detected.');
            } else {
                console.warn('[finish-data] validateFinishData: ' + problems.length + ' issue(s). Counts:', counts);
                problems.slice(0, 25).forEach(function (msg) { console.warn('  - ' + msg); });
                if (problems.length > 25) console.warn('  …and ' + (problems.length - 25) + ' more.');
            }
        }
    } catch (e) {
        if (typeof console !== 'undefined') console.warn('[finish-data] validateFinishData crashed', e);
    }
    // Return shape: keep `.length` working for legacy callers but also expose counts.
    var result = problems;
    result.counts = counts;
    return result;
}

// Expose helpers on window for browser usage (no-ops in Node script linting).
if (typeof window !== 'undefined') {
    window.getFinishMetadata    = getFinishMetadata;
    window.validateFinishData   = validateFinishData;
    window.BASES_BY_ID          = BASES_BY_ID;
    window.PATTERNS_BY_ID       = PATTERNS_BY_ID;
    window.SPEC_PATTERNS_BY_ID  = SPEC_PATTERNS_BY_ID;
    window.MONOLITHICS_BY_ID    = MONOLITHICS_BY_ID;
    window.FINISH_BY_NAME       = FINISH_BY_NAME;
    window.FINISH_ALIASES       = FINISH_ALIASES;
    window.FINISH_COUNT_BY_CATEGORY = FINISH_COUNT_BY_CATEGORY;
    window.DEFAULT_ZONES        = DEFAULT_ZONES;
    window.DEFAULT_BASE_COLOR   = DEFAULT_BASE_COLOR;
    window.DEFAULT_INTENSITY    = DEFAULT_INTENSITY;
    window.CATEGORY_ICONS       = CATEGORY_ICONS;
    window.CATEGORY_COLORS      = CATEGORY_COLORS;
    window.CATEGORY_DESCRIPTIONS = CATEGORY_DESCRIPTIONS;

    // WIN #18: auto-run finish-data drift validation once on boot. Output goes
    // to console.log/warn — painters never see it unless they open devtools.
    // Devs can suppress via `window._SPB_SKIP_FINISH_VALIDATE = true` set BEFORE
    // this file loads (e.g. in production builds with confirmed-clean catalogs).
    try {
        if (!window._SPB_SKIP_FINISH_VALIDATE) {
            // Defer to next tick so all data arrays are fully assembled.
            setTimeout(function () { try { validateFinishData(); } catch (_) {} }, 0);
        }
    } catch (_) {}
}
