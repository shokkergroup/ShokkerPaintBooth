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
    { id: "carbon_3k_fine", name: "Carbon 3K Fine", desc: "Tight high-frequency 3K ±45° twill — small aerospace weave with crisp fiber striation under gloss clear", swatch: "#2a2a2e" },
    { id: "carbon_satin", name: "Carbon Satin", desc: "Matte-clear 2×2 twill — OEM stealth carbon, woven structure with a dead-flat satin top", swatch: "#232326" },
    { id: "carbon_red", name: "Carbon Red", desc: "Candy-red tinted carbon twill under deep wet clear — colored carbon with full weave detail", swatch: "#5a1212" },
    { id: "carbon_blue", name: "Carbon Blue", desc: "Candy-blue tinted carbon twill under deep wet clear — colored carbon with full weave detail", swatch: "#14224d" },
    { id: "spread_tow", name: "Spread-Tow Carbon", desc: "Wide flat spread-tow ribbons — modern large-format carbon weave, big rectangular lanes", swatch: "#303034" },
    { id: "forged_blue", name: "Forged Blue", desc: "Chopped forged carbon set in blue resin — random marbled strand chunks, wet clearcoat", swatch: "#2a3350" },
    { id: "nomex_honeycomb", name: "Nomex Honeycomb", desc: "Gold aramid honeycomb core — open hex cells with resin-wet walls, exposed composite structure", swatch: "#b88a2a" },
    { id: "kevlar_red", name: "Kevlar Red Hybrid", desc: "Carbon black interwoven with red aramid tracer tows — race hybrid weave", swatch: "#6a1414" },
    { id: "basalt_weave", name: "Basalt Weave", desc: "Bronze-grey volcanic basalt fiber twill — warm metallic mineral weave, distinct from carbon", swatch: "#5a4d3c" },
    { id: "dyneema_white", name: "Dyneema White", desc: "White UHMWPE technical weave — matte high-strength fabric, pale woven structure", swatch: "#cfd0d4" },
    { id: "carbon_ceramic", name: "Carbon Ceramic", desc: "Carbon-ceramic brake disc surface — gray with carbon fiber flecks. Exotic supercar brakes-as-finish aesthetic.", swatch: "#333333", colorSafe: true },
    { id: "cerakote", name: "Cerakote", desc: "Military-spec ceramic polymer coating — tough, dead flat, tactical feel. Like a firearm finish on a race car.", swatch: "#667755" },
    { id: "ceramic", name: "Ceramic", desc: "Ultra-smooth ceramic nano-coating — deep wet shine with glass-like clarity and hydrophobic surface protection", swatch: "#5588bb", colorSafe: true },
    { id: "cathedral_glass", name: "Cathedral Glass", desc: "Stained leaded cathedral glass — deep violet colored panels with faceted depth and leading texture", swatch: "#5a2a8c" },
    { id: "sea_glass", name: "Sea Glass", desc: "Frosted beachy sea glass — soft seafoam tumbled finish, matte-satin with gentle subsurface", swatch: "#8ec9bc" },
    { id: "sapphire_glass", name: "Sapphire Glass", desc: "Deep blue faceted gem glass — sapphire transparency with wet specular depth", swatch: "#1530a0" },
    { id: "ruby_glass", name: "Ruby Glass", desc: "Deep red faceted gem glass — ruby cranberry transparency with wet specular depth", swatch: "#9e1020" },
    { id: "emerald_glass", name: "Emerald Glass", desc: "Deep green faceted gem glass — emerald transparency with wet specular depth", swatch: "#0a7038" },
    { id: "amber_glass", name: "Amber Glass", desc: "Warm honey amber gem glass — golden transparency with wet depth and facets", swatch: "#c8820e" },
    { id: "smoked_glass", name: "Smoked Glass", desc: "Charcoal smoked translucent glass — dark tinted transparency, privacy-glass depth", swatch: "#2a2a30" },
    { id: "milk_glass", name: "Milk Glass", desc: "Opaque milky white glass — soft subsurface glow, vintage pressed-glass look", swatch: "#e6e7ea" },
    { id: "mercury_glass", name: "Mercury Glass", desc: "Antique silvered mercury glass — blotchy mottled silvering with worn metallic patches", swatch: "#8c8d92" },
    { id: "crackle_glaze", name: "Raku Crackle", desc: "Teal celadon raku glaze — fine crazed crack network over wet ceramic glaze", swatch: "#5fa89e" },
    { id: "liquid_glaze", name: "Liquid Glaze", desc: "Cobalt ultra-wet ceramic glaze — maximum gloss depth, pooled liquid-glass surface", swatch: "#15309a" },
    { id: "terracotta_glaze", name: "Terracotta Glaze", desc: "Warm glazed terracotta — earthy orange clay with a soft glaze sheen and fine crazing", swatch: "#c46a40" },
    { id: "ceramic_matte", name: "Ceramic Matte", desc: "Ceramic nano-coat in matte — protected flat finish like PPF/ceramic but zero gloss. Modern stealth with UV protection.", swatch: "#667788", colorSafe: true },
    { id: "chalky_base", name: "Chalky Base", desc: "Chalky oxidised flat — near-maximum degradation, powdery dead surface like neglected fence paint. Apocalypse and abandoned-vehicle builds.", swatch: "#AAAAAA", colorSafe: true },
    { id: "chameleon", name: "Orchid Shift Pearl", desc: "Candy-pearl that shifts candy magenta to candy teal across the surface — fine mica platelets carry the two-tone flip.", swatch: "#b0228c" },
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
    { id: "iridescent", name: "Abalone Nacre", desc: "Abalone-shell pearl — green/blue/violet thin-film nacre flecks over a deep pearl body", swatch: "#1a6e5a" },
    { id: "jelly_pearl", name: "Jelly Pearl", desc: "Translucent jelly-like pearl coating with deep shimmer — semi-transparent gel surface that lets the base color glow through", swatch: "#DDBBEE", colorSafe: true },
    { id: "kevlar_base", name: "Kevlar Base", desc: "Same aramid as bulletproof vests — tough golden fiber weave. Pairs with carbon for hybrid. Tactical/military builds.", swatch: "#998844" },
    { id: "koenigsegg_clear", name: "Koenigsegg Clear", desc: "Clear-coated visible carbon weave Koenigsegg style — exposed fiber under deep glossy resin shell", swatch: "#3d3020" },
    { id: "lamborghini_verde", name: "Lambo Verde", desc: "Lamborghini Verde Mantis electric green — vivid acid-bright hue that screams Italian supercar aggression", swatch: "#33cc55" },
    { id: "liquid_titanium", name: "Liquid Titanium", desc: "Molten titanium pooling mirror — liquid-metal sheen with warm gray tone and flowing reflective highlights", swatch: "#8899aa" },
    { id: "liquid_wrap", name: "Liquid Wrap", desc: "PlastiDip-style removable rubber coat — textured matte you can peel off later. Temporary builds and experiments.", swatch: "#8866aa" },
    // SPB-102 / PRISM FORGE — procedural spectral bases (2026-05-17 UI wire-up)
    { id: "pf_event_horizon_spectra", name: "PF: Event Horizon Spectra", desc: "PRISM FORGE Event Horizon Spectra — v3: ink-quiet diffuse; sub-pixel spec carriers stack spectral flash in sim.", swatch: "#888899" },
    { id: "pf_chromatic_storm", name: "PF: Chromatic Storm", desc: "PRISM FORGE Chromatic Storm — v3: crushed multi-scale hue fog + dense spec interference (no damascus wallpaper).", swatch: "#888899" },
    { id: "pf_neon_nova", name: "PF: Neon Nova", desc: "PRISM FORGE Neon Nova — v3: no radial fan; pocket hue via micro regions + cyber-dense spec lattice.", swatch: "#888899" },
    { id: "pf_molten_aurora", name: "PF: Molten Aurora", desc: "PRISM FORGE Molten Aurora — v3: ember/teal without diagonal macro bands; heat reads from spec beats.", swatch: "#888899" },
    { id: "pf_void_pearl", name: "PF: Void Pearl", desc: "PRISM FORGE Void Pearl — **unchanged v2 path** (artist hold); charcoal opal, spec-led bloom.", swatch: "#888899" },
    { id: "pf_ion_trap", name: "PF: Ion Trap", desc: "PRISM FORGE Ion Trap — v3: electric blue-violet micro grain; no wide ion stripes in diffuse.", swatch: "#888899" },
    { id: "pf_sapphire_blood", name: "PF: Sapphire Blood", desc: "PRISM FORGE Sapphire Blood — v3: jewel hue crushed to fine texture; wine undertow in spec mix.", swatch: "#888899" },
    { id: "pf_emerald_inferno", name: "PF: Emerald Inferno", desc: "PRISM FORGE Emerald Inferno — v3: no pinwheel; acid/ember via micro hue + HF spec shards.", swatch: "#888899" },
    { id: "pf_violet_sunrise", name: "PF: Violet Sunrise", desc: "PRISM FORGE Violet Sunrise — v3: dawn gold/violet as crushed fields; zero candy stripes.", swatch: "#888899" },
    { id: "pf_copper_moon", name: "PF: Copper Moon", desc: "PRISM FORGE Copper Moon — **unchanged v2 path** (artist hold); burnished copper, spec-led story.", swatch: "#888899" },
    { id: "pf_toxic_horizon", name: "PF: Toxic Horizon", desc: "PRISM FORGE Toxic Horizon — v3: chartreuse/purple as micro mosaic; hazard glitter in spec.", swatch: "#888899" },
    { id: "pf_glacial_burn", name: "PF: Glacial Burn", desc: "PRISM FORGE Glacial Burn — v3: cooler, smoother ultra carrier vs Oil Nebula; ice/ember separation.", swatch: "#888899" },
    { id: "pf_oil_nebula", name: "PF: Oil Nebula", desc: "PRISM FORGE Oil Nebula — v3: distinct HF phase set from Glacial; thinner tri power, more warp chaos.", swatch: "#888899" },
    { id: "pf_rose_quantum", name: "PF: Rose Quantum", desc: "PRISM FORGE Rose Quantum — v3: no quantum pinwheel; rose/teal as micro pockets + jewelry spec.", swatch: "#888899" },
    { id: "pf_cobalt_fire", name: "PF: Cobalt Fire", desc: "PRISM FORGE Cobalt Fire — v3: cobalt/lava without candy bands; flash is spec-led.", swatch: "#888899" },
    { id: "pf_midnight_prism", name: "PF: Midnight Prism", desc: "PRISM FORGE Midnight Prism — v3: ink-quiet plane; prismatic lightning almost entirely in spec.", swatch: "#888899" },
    { id: "pf_hyperwave", name: "PF: Hyperwave", desc: "PRISM FORGE Hyperwave — v3: lateral energy without macro sweep stripes; HF spec scan texture.", swatch: "#888899" },
    { id: "pf_crystal_fade", name: "PF: Crystal Fade", desc: "PRISM FORGE Crystal Fade — v3: opal milk micro veins + satin frost spec (tighter than v2 wallpaper).", swatch: "#888899" },
    { id: "pf_dark_matter_halo", name: "PF: Dark Matter Halo", desc: "PRISM FORGE Dark Matter Halo — v3: void base; halo is HF spec ridge energy, not radial pinwheel paint.", swatch: "#888899" },
    { id: "pf_apex_spectrum", name: "PF: Apex Spectrum", desc: "PRISM FORGE Apex Spectrum — v3: max hue walk still **micro** on albedo; bold metallic in spec (no cell wallpaper).", swatch: "#888899" },
    { id: "pf_cluster_tar_eclipse", name: "PF: Cluster Tar Eclipse", desc: "PRISM FORGE Cluster Tar Eclipse — black islands: gold/violet/teal pockets + crushed grain.", swatch: "#888899" },
    { id: "pf_cluster_bitumen_aurora", name: "PF: Cluster Bitumen Aurora", desc: "PRISM FORGE Cluster Bitumen Aurora — tar-black with scattered aurora RGB pockets; unique island layout.", swatch: "#888899" },
    { id: "pf_cluster_obsidian_gild", name: "PF: Cluster Obsidian Gild", desc: "PRISM FORGE Cluster Obsidian Gild — gilded micro-pools on obsidian; purple/teal counter-islands.", swatch: "#888899" },
    { id: "pf_cluster_coal_starfield", name: "PF: Cluster Coal Starfield", desc: "PRISM FORGE Cluster Coal Starfield — coal black with starfield jewel pockets; denser micro sparkle.", swatch: "#888899" },
    { id: "pf_cluster_void_islands", name: "PF: Cluster Void Islands", desc: "PRISM FORGE Cluster Void Islands — void black + isolated hue archipelagos; each island unique weighting.", swatch: "#888899" },
    { id: "pf_bright_solar_daffodil", name: "PF: Bright Solar Daffodil", desc: "PRISM FORGE Bright Solar Daffodil — high-key yellow sun plate; micro hue so sponsors stay clean.", swatch: "#888899" },
    { id: "pf_bright_hyperpink", name: "PF: Bright Hyperpink", desc: "PRISM FORGE Bright Hyperpink — neon magenta/pink pop with crushed micro texture + glass spec.", swatch: "#888899" },
    { id: "pf_bright_seafoam_bolt", name: "PF: Bright Seafoam Bolt", desc: "PRISM FORGE Bright Seafoam Bolt — seafoam/lime voltage on bright shell; undertone through micro hue.", swatch: "#888899" },
    { id: "pf_bright_cerulean_pop", name: "PF: Bright Cerulean Pop", desc: "PRISM FORGE Bright Cerulean Pop — saturated sky blue; sparkle via HF spec, not albedo bands.", swatch: "#888899" },
    { id: "pf_bright_canary_glass", name: "PF: Bright Canary Glass", desc: "PRISM FORGE Bright Canary Glass — lemon-lime glass bright plate; satin-glass spec envelope.", swatch: "#888899" },
    { id: "pf_bright_magenta_arc", name: "PF: Bright Magenta Arc", desc: "PRISM FORGE Bright Magenta Arc — hot magenta/fuchsia with micro hue arc; no macro stripes.", swatch: "#888899" },
    { id: "pf_bright_lime_voltage", name: "PF: Bright Lime Voltage", desc: "PRISM FORGE Bright Lime Voltage — acid lime on bright value; undertone via micro yellow-green walk.", swatch: "#888899" },
    { id: "pf_bright_peach_fizz", name: "PF: Bright Peach Fizz", desc: "PRISM FORGE Bright Peach Fizz — warm peach/coral bright shell; fizz is spec HF, not peach stripes.", swatch: "#888899" },
    { id: "pf_bright_neon_ice_stream", name: "PF: Bright Neon Ice Stream", desc: "PRISM FORGE Bright Neon Ice Stream — electric cyan/ice blue bright plate; arctic undertone.", swatch: "#888899" },
    { id: "pf_bright_orchid_pulse", name: "PF: Bright Orchid Pulse", desc: "PRISM FORGE Bright Orchid Pulse — vivid orchid/violet bright finish; pulse in spec, not candy bands.", swatch: "#888899" },
    { id: "pf_blend_triad_mist", name: "PF: Blend Triad Mist", desc: "PRISM FORGE Blend Triad Mist — three-hue mist (teal/violet/gold) crushed to micro scales.", swatch: "#888899" },
    { id: "pf_blend_quad_weave", name: "PF: Blend Quad Weave", desc: "PRISM FORGE Blend Quad Weave — four-hue weave in micro field; spec carries extra separation.", swatch: "#888899" },
    { id: "pf_spectrum_chaos_crown", name: "PF: Spectrum Chaos Crown", desc: "PRISM FORGE Spectrum Chaos Crown — full-spectrum madness #1: max hue span, still pixel-crushed on albedo.", swatch: "#888899" },
    { id: "pf_prismatic_void_madness", name: "PF: Prismatic Void Madness", desc: "PRISM FORGE Prismatic Void Madness — full-spectrum madness #2 on deep void; rainbow in spec + micro hue.", swatch: "#888899" },
    { id: "pf_white_castle_of_fear", name: "PF: White Castle of Fear", desc: "PRISM FORGE White Castle of Fear — glimmering white show plate; ice-blue undertone via tint + micro hue.", swatch: "#888899" },
    { id: "pf_gradient_venetian_veil", name: "PF: Gradient Venetian Veil", desc: "PRISM FORGE Gradient Venetian Veil — soft multi-octave gradient bias in region scales + micro crush.", swatch: "#888899" },
    { id: "pf_tri_crimson_cyan_mage", name: "PF: Tri Crimson Cyan Mage", desc: "PRISM FORGE Tri Crimson Cyan Mage — crimson/cyan/magenta triad on micro islands; mage undertone in spec.", swatch: "#888899" },
    { id: "pf_quad_jade_violet_gold_slate", name: "PF: Quad Jade Violet Gold Slate", desc: "PRISM FORGE Quad Jade Violet Gold Slate — four-tone luxury blend; all crushed to fine texture.", swatch: "#888899" },
    { id: "pf_fade_copper_teal_sunset", name: "PF: Fade Copper Teal Sunset", desc: "PRISM FORGE Fade Copper Teal Sunset — copper→teal sunset gradient character via **region octaves** + micro.", swatch: "#888899" },
    { id: "pf_blend_ocean_peach_ivory", name: "PF: Blend Ocean Peach Ivory", desc: "PRISM FORGE Blend Ocean Peach Ivory — pastel tri-hue on ivory value; beach luxury micro spec.", swatch: "#888899" },
    { id: "pf_iris_velvet_crossfade", name: "PF: Iris Velvet Crossfade", desc: "PRISM FORGE Iris Velvet Crossfade — iris/violet velvet crossfade; micro cross hue, no macro bands.", swatch: "#888899" },
    { id: "pf_spectral_tidepool_wash", name: "PF: Spectral Tidepool Wash", desc: "PRISM FORGE Spectral Tidepool Wash — teal/green/violet wash; tidepool spectral in HF spec.", swatch: "#888899" },
    { id: "pf_midnight_coral_ember", name: "PF: Midnight Coral Ember", desc: "PRISM FORGE Midnight Coral Ember — deep midnight with coral ember micro pockets + warm spec.", swatch: "#888899" },
    { id: "pf_emerald_orchid_storm", name: "PF: Emerald Orchid Storm", desc: "PRISM FORGE Emerald Orchid Storm — emerald/jade/orchid tri-storm; crushed hue complexity.", swatch: "#888899" },
    { id: "pf_golden_ultraviolet_fog", name: "PF: Golden Ultraviolet Fog", desc: "PRISM FORGE Golden Ultraviolet Fog — full-spectrum madness #3 (warmer): gold fog into UV violet micro travel.", swatch: "#888899" },
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
    { id: "multicam", name: "Multicam", desc: "Multicam/Scorpion fine organic camo — tan/green/brown blended micro-blobs, matte cerakote feel", swatch: "#6a6450" },
    { id: "marpat_woodland", name: "MARPAT Digital", desc: "Pixelated digital woodland camo — fine green/brown/tan/black pixels, flat tactical", swatch: "#3a4030" },
    { id: "tiger_stripe", name: "Tiger Stripe", desc: "Jungle tiger stripe — fine wavy black brush stripes over olive/tan, matte", swatch: "#4a4a2e" },
    { id: "kryptek_typhon", name: "Kryptek Typhon", desc: "Angular reptilian-scale camo — fine black/grey geometric cells, matte", swatch: "#2a2c30" },
    { id: "m81_woodland", name: "M81 Woodland", desc: "Classic 4-color woodland camo — fine brown/green/black organic blobs, matte", swatch: "#3a4228" },
    { id: "desert_dpm", name: "Desert DPM", desc: "Desert disruptive-pattern camo — fine tan/brown blobs, matte", swatch: "#b09060" },
    { id: "urban_digital", name: "Urban Digital", desc: "Urban digital camo — fine grey/white/black pixels, matte", swatch: "#888a8e" },
    { id: "od_drab", name: "OD Green", desc: "Solid olive-drab tactical cerakote — flat mil-spec coating with micro grain", swatch: "#4d5333" },
    { id: "coyote_fde", name: "Coyote FDE", desc: "Solid coyote / flat-dark-earth tan tactical cerakote — flat with micro grain", swatch: "#8c7654" },
    { id: "blackout_ops", name: "Blackout Ops", desc: "Murdered-out tactical black — near-flat with fine chalky micro-pore texture", swatch: "#18181c" },
    { id: "neon_circuit", name: "Neon Circuit", desc: "Cyberpunk PCB — fine routed cyan/magenta circuit traces and nodes on dark board", swatch: "#10b0c0" },
    { id: "tron_grid", name: "Tron Grid", desc: "Glowing fine cyan grid with bright intersection nodes and depth fade on black", swatch: "#10a0d0" },
    { id: "synthwave", name: "Synthwave", desc: "Retro synthwave — magenta→cyan gradient with sun band and a fine glowing grid", swatch: "#c83a8c" },
    { id: "data_rain", name: "Data Rain", desc: "Matrix code-rain — fine green glyph streaks dripping on black", swatch: "#1a8a30" },
    { id: "glitch_rgb", name: "RGB Glitch", desc: "Datamosh glitch — fine chromatic RGB-shifted scanlines and blocks", swatch: "#6040a0" },
    { id: "hex_tech", name: "Hex Tech", desc: "Sci-fi hex panel grid — fine glowing cyan honeycomb edges on dark", swatch: "#14a0b0" },
    { id: "holo_vapor", name: "Holo Vapor", desc: "Holographic vaporwave — fine pastel thin-film iridescent swirl", swatch: "#c8a0e0" },
    { id: "chrome_neon", name: "Chrome Neon", desc: "Polished chrome with fine diagonal magenta/cyan neon pinstripes", swatch: "#b0b4bc" },
    { id: "plasma_pulse", name: "Plasma Pulse", desc: "Electric plasma — fine blue/purple energy filaments and arcs", swatch: "#7a30c0" },
    { id: "cyber_camo", name: "Cyber Camo", desc: "Cyberpunk digital camo — fine neon cyan/magenta/violet pixel blocks on dark", swatch: "#18c0d0" },
    { id: "labradorite", name: "Labradorite", desc: "Gray feldspar that flashes electric blue/gold at angle (labradorescence)", swatch: "#2a3a6a" },
    { id: "spectrolite", name: "Spectrolite", desc: "Full-spectrum labradorite — blue/gold/green/violet flash domains", swatch: "#3a2a6a" },
    { id: "ammolite", name: "Ammolite", desc: "Iridescent fossil-shell — fractured rainbow plates with dark seams", swatch: "#b8407a" },
    { id: "tiger_eye", name: "Tiger's Eye", desc: "Chatoyant golden-brown silk fibre bands with a moving cat's-eye sheen", swatch: "#9a6a1a" },
    { id: "dichroic_glass", name: "Dichroic Glass", desc: "Art-glass dichroic film — flowing two-color iridescent flip", swatch: "#c060a0" },
    { id: "fire_agate", name: "Fire Agate", desc: "Banded agate with fiery iridescent flash pockets", swatch: "#b0600f" },
    { id: "malachite", name: "Malachite", desc: "Concentric green mineral banding (eye rings)", swatch: "#1f6a3a" },
    { id: "azurite", name: "Azurite", desc: "Deep blue wavy mineral bands with crystalline glints", swatch: "#1a3aa0" },
    { id: "black_opal", name: "Black Opal", desc: "Black body with vivid multi-color play-of-color fire", swatch: "#202840" },
    { id: "sunstone", name: "Sunstone", desc: "Warm orange with copper aventurescent schiller glitter", swatch: "#c8600f" },
    { id: "retroreflective_silver", name: "Retro Silver", desc: "Road-sign retroreflective — muted by day, blazes white under lights", swatch: "#9a9ca0" },
    { id: "hi_vis_lime", name: "Hi-Vis Lime", desc: "Safety lime-yellow retroreflective sheeting", swatch: "#b8d020" },
    { id: "cats_eye_beaded", name: "Cat's Eye", desc: "Beaded retroreflective studs on charcoal — sparkles under lights", swatch: "#2a2c30" },
    { id: "diamond_grade", name: "Diamond Grade", desc: "Prismatic micro-cube reflective sheeting", swatch: "#7a8aa0" },
    { id: "ghost_graphic", name: "Ghost Graphic", desc: "Graphic hidden in daylight, blazes under direct light", swatch: "#3a2a18" },
    { id: "amber_hazard", name: "Amber Hazard", desc: "Amber reflective hazard stripes", swatch: "#c8820a" },
    { id: "tribal_blaze", name: "Tribal Blaze", desc: "Reflective tribal linework that ignites at night", swatch: "#303236" },
    { id: "big_kahuna", name: "Big Kahuna", desc: "Sunset-orange surf-tribal over teal, reflective", swatch: "#0a4a4a" },
    { id: "chevron_blaze", name: "Battenburg", desc: "Reflective battenburg emergency checker", swatch: "#4a5a30" },
    { id: "starfield_reflective", name: "Starfield", desc: "Reflective stars — dark by day, starry under lights", swatch: "#1a1f3a" },
    { id: "twoface_blue_copper", name: "Two-Face Blue/Copper", desc: "Bold directional two-color flip — blue to copper", swatch: "#4060c0" },
    { id: "twoface_purple_gold", name: "Two-Face Purple/Gold", desc: "Bold directional two-color flip — purple to gold", swatch: "#8a5ac0" },
    { id: "twoface_green_magenta", name: "Two-Face Green/Magenta", desc: "Bold directional two-color flip — green to magenta", swatch: "#80608a" },
    { id: "twoface_teal_orange", name: "Two-Face Teal/Orange", desc: "Bold directional two-color flip — teal to orange", swatch: "#c08040" },
    { id: "twoface_red_cyan", name: "Two-Face Red/Cyan", desc: "Bold directional two-color flip — red to cyan", swatch: "#a06070" },
    { id: "twoface_silver_void", name: "Two-Face Silver/Void", desc: "Dramatic light/dark directional flip — silver to black", swatch: "#6a6c70" },
    { id: "twoface_pink_teal", name: "Two-Face Pink/Teal", desc: "Bold directional two-color flip — pink to teal", swatch: "#c06080" },
    { id: "twoface_gold_emerald", name: "Two-Face Gold/Emerald", desc: "Bold directional two-color flip — gold to emerald", swatch: "#8a8a40" },
    { id: "twoface_violet_lime", name: "Two-Face Violet/Lime", desc: "Bold directional two-color flip — violet to lime", swatch: "#8aa050" },
    { id: "twoface_crimson_navy", name: "Two-Face Crimson/Navy", desc: "Bold directional two-color flip — crimson to navy", swatch: "#6a3050" },
    { id: "pour_ocean", name: "Ocean Pour", desc: "Acrylic pour cells with silicone lacing — blue/teal/white", swatch: "#2a7a8a" },
    { id: "pour_lava", name: "Lava Pour", desc: "Fluid pour — black/red/orange/gold cells", swatch: "#b04010" },
    { id: "pour_galaxy", name: "Galaxy Pour", desc: "Fluid pour — purple/magenta/white cells", swatch: "#6a3a8a" },
    { id: "pour_gold_marble", name: "Gold Marble Pour", desc: "Luxe fluid pour — black/white/gold", swatch: "#8a7030" },
    { id: "pour_tropical", name: "Tropical Pour", desc: "Fluid pour — teal/lime/yellow", swatch: "#4aa060" },
    { id: "pour_rose", name: "Rose Pour", desc: "Fluid pour — rose/pink/white/gold", swatch: "#c06a7a" },
    { id: "ink_emerald", name: "Emerald Ink", desc: "Alcohol-ink emerald blooms, soft feathered cells", swatch: "#2a8a4a" },
    { id: "ink_copper", name: "Copper Ink", desc: "Alcohol-ink teal/copper patina blooms", swatch: "#5a8a7a" },
    { id: "pour_monochrome", name: "Mono Pour", desc: "Fluid pour — black/white/grey cells", swatch: "#707274" },
    { id: "pour_neon", name: "Neon Pour", desc: "Fluid pour — neon cyan/magenta/lime cells", swatch: "#40c0a0" },
    { id: "sequin_silver", name: "Silver Sequin", desc: "Field of mirror sequins, each catching light at its own flash", swatch: "#aaacb2" },
    { id: "sequin_gold", name: "Gold Sequin", desc: "Gold sequin sparkle field", swatch: "#c8a030" },
    { id: "sequin_rose", name: "Rose Sequin", desc: "Rose-gold sequin sparkle field", swatch: "#d07080" },
    { id: "sequin_emerald", name: "Emerald Sequin", desc: "Emerald sequin sparkle field", swatch: "#30a050" },
    { id: "sequin_copper", name: "Copper Sequin", desc: "Copper sequin sparkle field", swatch: "#c06030" },
    { id: "sequin_ice", name: "Ice Sequin", desc: "Icy blue/white sequin sparkle field", swatch: "#8ab0d0" },
    { id: "sequin_rainbow", name: "Rainbow Sequin", desc: "Multicolor flashing sequins — disco party", swatch: "#a060a0" },
    { id: "sequin_holographic", name: "Holo Sequin", desc: "Holographic iridescent sequins, each a thin-film hue", swatch: "#b090c0" },
    { id: "disco_black_diamond", name: "Disco Black Diamond", desc: "Mirror-ball facets flashing on black", swatch: "#404858" },
    { id: "sequin_mardi_gras", name: "Mardi Gras", desc: "Festive purple/gold/green sequin sparkle", swatch: "#8a6a4a" },
    { id: "flame_hotrod", name: "Hot Rod Flames", desc: "Classic orange/yellow hot-rod flame licks on black", swatch: "#e06010" },
    { id: "flame_true_fire", name: "True Fire", desc: "Photoreal turbulent fire — red/orange/yellow", swatch: "#e85010" },
    { id: "flame_blue", name: "Blue Flame", desc: "Propane-blue flame licks", swatch: "#1060d0" },
    { id: "flame_green", name: "Green Fire", desc: "Toxic green firestorm", swatch: "#20a020" },
    { id: "flame_purple", name: "Purple Flame", desc: "Violet/magenta flame licks", swatch: "#8020c0" },
    { id: "flame_ghost", name: "Ghost Flames", desc: "Subtle tonal black-on-charcoal flame licks", swatch: "#2a2a30" },
    { id: "flame_inferno", name: "Inferno", desc: "Intense red/orange firestorm", swatch: "#e03000" },
    { id: "flame_white_hot", name: "White Hot", desc: "Hottest blue-white fire", swatch: "#80a0f0" },
    { id: "flame_rainbow", name: "Rainbow Fire", desc: "Multicolor spectral flames", swatch: "#a05060" },
    { id: "flame_ember", name: "Ember Coals", desc: "Glowing ember/coal bed", swatch: "#c84810" },
    { id: "flame_candy", name: "Candy Flame", desc: "Candy-red metallic flame licks", swatch: "#c01828" },
    { id: "flame_plasma", name: "Plasma Fire", desc: "Electric blue/purple plasma fire", swatch: "#7040e0" },
    { id: "flame_cold", name: "Cold Fire", desc: "Icy blue-white cold flame licks", swatch: "#50a0e0" },
    { id: "flame_lava", name: "Lava Flame", desc: "Molten lava + flame, orange/black", swatch: "#d05010" },
    { id: "flame_phoenix", name: "Phoenix", desc: "Gold/orange feathery phoenix flames", swatch: "#e0a030" },
    { id: "flame_toxic", name: "Toxic Flame", desc: "Green/yellow toxic fire", swatch: "#a0c020" },
    { id: "flame_pink", name: "Pink Flame", desc: "Hot-pink flame licks", swatch: "#e030a0" },
    { id: "flame_smoke", name: "Smoke & Fire", desc: "Orange fire bleeding into grey smoke", swatch: "#a06030" },
    { id: "flame_tribal", name: "Tribal Flame", desc: "Bold tribal flame tongues", swatch: "#d04810" },
    { id: "flame_dragon", name: "Dragon Breath", desc: "Intense orange/red/yellow dragon breath", swatch: "#e04810" },
    { id: "marble_carrara", name: "Carrara Marble", desc: "White Carrara with soft grey veining", swatch: "#e8e8ea" },
    { id: "marble_calacatta", name: "Calacatta Gold", desc: "White marble with dramatic gold veins", swatch: "#ece2c8" },
    { id: "marble_nero", name: "Nero Marquina", desc: "Black marble with crisp white veins", swatch: "#1a1a1e" },
    { id: "marble_portoro", name: "Portoro", desc: "Black marble with luxe gold veins", swatch: "#14110c" },
    { id: "marble_statuario", name: "Statuario", desc: "Bright white marble, fine grey veining", swatch: "#e6e6ea" },
    { id: "marble_bardiglio", name: "Bardiglio Grey", desc: "Grey marble with white veins", swatch: "#5a5c62" },
    { id: "marble_rose", name: "Rose Marble", desc: "Soft pink marble with mauve veining", swatch: "#d8b0b0" },
    { id: "marble_rosso", name: "Rosso Levanto", desc: "Deep red marble with white veins", swatch: "#6a1414" },
    { id: "marble_verde_alpi", name: "Verde Alpi", desc: "Dark green marble with white veins", swatch: "#1a4a28" },
    { id: "marble_fusion", name: "Fusion Marble", desc: "Multicolor luxe marble with gold/teal veins", swatch: "#6a3a5a" },
    { id: "travertine", name: "Travertine", desc: "Soft beige travertine stone", swatch: "#b8a070" },
    { id: "obsidian_gold", name: "Obsidian Gold", desc: "Black obsidian shot with gold veins", swatch: "#1a1a1e" },
    { id: "onyx_emerald", name: "Emerald Onyx", desc: "Banded green onyx slab", swatch: "#1a5a30" },
    { id: "onyx_honey", name: "Honey Onyx", desc: "Translucent amber banded onyx", swatch: "#c8922a" },
    { id: "onyx_pink", name: "Pink Onyx", desc: "Banded pink onyx slab", swatch: "#d090a0" },
    { id: "onyx_white", name: "White Onyx", desc: "Milky backlit banded onyx", swatch: "#dde0e4" },
    { id: "agate_blue", name: "Blue Agate", desc: "Banded blue agate slab", swatch: "#2a55b0" },
    { id: "lapis_lazuli", name: "Lapis Lazuli", desc: "Deep blue lapis with gold pyrite flecks", swatch: "#1530a0" },
    { id: "amethyst", name: "Amethyst", desc: "Purple amethyst geode banding", swatch: "#6a30a0" },
    { id: "tiger_iron", name: "Tiger Iron", desc: "Red/gold/black banded tiger iron", swatch: "#8a4a18" },
    { id: "diner_checker", name: "Diner Checkerboard", desc: "Classic black/white diner floor checker", swatch: "#888888" },
    { id: "soda_check", name: "Soda Fountain Check", desc: "Pastel mint/pink 50s checker", swatch: "#9ad0c0" },
    { id: "cherry_polka", name: "Cherry Polka", desc: "White polka dots on cherry red", swatch: "#c81824" },
    { id: "lemon_polka", name: "Lemon Polka", desc: "White polka dots on lemon yellow", swatch: "#e8d020" },
    { id: "bubblegum_dot", name: "Bubblegum Dots", desc: "Big retro dots on bubblegum pink", swatch: "#e878a0" },
    { id: "mint_stripe", name: "Mint Candy Stripe", desc: "Mint/cream 50s candy stripes", swatch: "#8ad0b8" },
    { id: "coral_stripe", name: "Coral Stripe", desc: "Coral/cream diagonal stripes", swatch: "#e08070" },
    { id: "gingham_red", name: "Red Gingham", desc: "Red/white picnic gingham", swatch: "#c83030" },
    { id: "atomic_starburst", name: "Atomic Starburst", desc: "Atomic-age starbursts on teal", swatch: "#1a7a7c" },
    { id: "atomic_charcoal", name: "Atomic Charcoal", desc: "Atomic starbursts on charcoal", swatch: "#c85040" },
    { id: "googie_orbit", name: "Googie Orbit", desc: "Mid-century googie orbit ellipses", swatch: "#30a0a8" },
    { id: "vinyl_groove", name: "Vinyl Record", desc: "Concentric record grooves in black", swatch: "#222226" },
    { id: "harlequin", name: "Harlequin", desc: "Retro harlequin diamonds", swatch: "#b04040" },
    { id: "argyle_pastel", name: "Pastel Argyle", desc: "Soft 50s argyle diamonds", swatch: "#7a9098" },
    { id: "terrazzo_cream", name: "Terrazzo", desc: "Confetti terrazzo speckle on cream", swatch: "#c8b8a0" },
    { id: "formica_boomerang", name: "Formica Boomerang", desc: "Boomerang formica-counter speckle", swatch: "#b89878" },
    { id: "jukebox_neon", name: "Jukebox Neon", desc: "Chrome-and-neon jukebox arcs on black", swatch: "#e0306a" },
    { id: "pink_fleck", name: "Pink Metalflake", desc: "50s pink metalflake", swatch: "#d870a0" },
    { id: "turquoise_fleck", name: "Turquoise Metalflake", desc: "50s turquoise metalflake", swatch: "#20a0a0" },
    { id: "chrome_diner", name: "Diner Chrome", desc: "Polished diner chrome", swatch: "#9a9ca0" },
    { id: "tie_dye_spiral", name: "Tie-Dye Spiral", desc: "Classic spiral tie-dye rainbow", swatch: "#c050a0" },
    { id: "tie_dye_crumple", name: "Crumple Tie-Dye", desc: "Crumpled scrunch tie-dye", swatch: "#a060c0" },
    { id: "peace_tie_dye", name: "Peace Tie-Dye", desc: "Mellow blue/purple tie-dye spiral", swatch: "#6050b0" },
    { id: "psychedelic_swirl", name: "Psychedelic Swirl", desc: "Bold psychedelic rainbow swirls", swatch: "#d04090" },
    { id: "acid_swirl", name: "Acid Swirl", desc: "Neon acid rainbow swirl", swatch: "#40d080" },
    { id: "melting_rainbow", name: "Melting Rainbow", desc: "Flowing melting rainbow", swatch: "#e05040" },
    { id: "hippie_rainbow", name: "Hippie Rainbow", desc: "Full flowing rainbow", swatch: "#e08020" },
    { id: "sunburst_60s", name: "60s Sunburst", desc: "Radiating rainbow sunburst rays", swatch: "#d0b020" },
    { id: "groovy_zigzag", name: "Groovy Zigzag", desc: "Rainbow zigzag rays", swatch: "#d05050" },
    { id: "kaleido_rings", name: "Kaleidoscope", desc: "Concentric kaleidoscope rainbow rings", swatch: "#40a0d0" },
    { id: "trippy_concentric", name: "Trippy Rings", desc: "Tight trippy concentric rainbow", swatch: "#b040a0" },
    { id: "warp_op", name: "Warp Op-Art", desc: "Psychedelic warped op-art rings", swatch: "#8060c0" },
    { id: "oil_slick_groove", name: "Oil Slick", desc: "Psychedelic oil-slick flow", swatch: "#6080a0" },
    { id: "groovy_marble", name: "Groovy Marble", desc: "Psychedelic marbled swirl", swatch: "#8050a0" },
    { id: "liquid_light", name: "Liquid Light Show", desc: "60s liquid-light-show blooms", swatch: "#d04080" },
    { id: "flower_power", name: "Flower Power", desc: "Tight flower-power rainbow rosette", swatch: "#d09030" },
    { id: "lava_lamp_purple", name: "Lava Lamp Purple", desc: "Purple/orange lava-lamp blobs", swatch: "#8a2a8a" },
    { id: "lava_lamp_groovy", name: "Lava Lamp Groovy", desc: "Orange/teal/avocado lava-lamp blobs", swatch: "#c86020" },
    { id: "mushroom_fade", name: "Mushroom Fade", desc: "Earthy psychedelic blob fade", swatch: "#8a6a40" },
    { id: "neon_acid_blob", name: "Neon Acid", desc: "Neon acid-blob psychedelia", swatch: "#20c070" },
    { id: "mil_spec_tan", name: "Martian Regolith Dust", desc: "Extremely rusty, iron-rich, harsh and gritty red dirt directly from the surface of Mars", swatch: "#AE684F" },
    { id: "mirror_gold", name: "Mirror Gold", desc: "Pure mirror gold chrome — full 24k gold reflective surface like a Dubai showpiece, maximum opulence on wheels", swatch: "#ddaa33" },
    { id: "moonstone", name: "Moonstone", desc: "Soft translucent milky moonstone shimmer — pale opalescent glow like the real gemstone with internal light play", swatch: "#ccccdd" },
    { id: "moth_luna", name: "Moth Luna", desc: "Pale green Luna moth wing with delicate eye-spot markings — soft pastel insect-inspired organic texture", swatch: "#99cc88" },
    { id: "neutron_star", name: "Accretion Ring", desc: "Void black sink with a sharp micro-spec ring — light grazing the edge explodes into color. Procedural.", swatch: "#0A0A0A" },
    { id: "obsidian", name: "Obsidian", desc: "Volcanic obsidian glass — razor-sharp deep black with mirror sheen like polished igneous rock. Dramatic depth.", swatch: "#0a0a12" },
    { id: "opal", name: "Dragon's Pearl Scale", desc: "Massive multi-colored shifting pearl mimicking the biological armored plate of a dragon", swatch: "#E6E6FA" },
    { id: "orange_peel_gloss", name: "Candy Tangerine", desc: "Bright tangerine candy over gold flake with a subtle orange-peel clearcoat ripple — deep wet citrus", swatch: "#e85a0a", colorSafe: true },
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
    // -- ENHANCED FOUNDATION EXOTIC (EFX): spec-driven recipe bases surfaced in the picker --
    { id: "efx_holographic_drift", name: "EFX Holographic Drift", desc: "Spec-driven diffraction grating with four-band micro sparkle; base paint stays intact.", swatch: "#D8CCFF", colorSafe: true },
    { id: "efx_cathedral_veil", name: "EFX Cathedral Veil", desc: "Spec-driven glass-vein network with cane-like depth and fine interior texture.", swatch: "#B8D6E8", colorSafe: true },
    { id: "efx_frost_fractal", name: "EFX Frost Fractal", desc: "Spec-driven recursive frost ridges with ice crystal sparkle and tight micro detail.", swatch: "#C8F4FF", colorSafe: true },
    { id: "efx_kintsugi_bloom", name: "EFX Kintsugi Bloom", desc: "Spec-driven matte body with sparse gold vein blooms and broken lacquer energy.", swatch: "#D7B04A", colorSafe: true },
    { id: "efx_quicksilver_pool", name: "EFX Quicksilver Pool", desc: "Spec-driven mercury pooling with chrome-rich liquid territories and fast shimmer.", swatch: "#D8DDE2", colorSafe: true },
    { id: "efx_volcanic_obsidian", name: "EFX Volcanic Obsidian", desc: "Spec-driven obsidian fracture wells with knife-edge ridges and dark volcanic depth.", swatch: "#281018", colorSafe: true },
    { id: "efx_aurora_skin", name: "EFX Aurora Skin", desc: "Spec-driven flowing chromatic veils with high-frequency clearcoat oscillation.", swatch: "#66D9C8", colorSafe: true },
    { id: "efx_lace_filament", name: "EFX Lace Filament", desc: "Spec-driven fractal lace filaments over anisotropic body grain and fine shimmer.", swatch: "#D7D0C8", colorSafe: true },
    { id: "efx_tempered_spectrum", name: "EFX Tempered Spectrum", desc: "Spec-driven heat-tint spectrum bands with anisotropic grain and micro sparkle.", swatch: "#B6D4FF", colorSafe: true },
    { id: "efx_damascus_fold", name: "EFX Damascus Fold", desc: "Spec-driven interleaved Damascus fold bands with layered angle changes.", swatch: "#8B8A7A", colorSafe: true },
    { id: "efx_stardust_coat", name: "EFX Stardust Coat", desc: "Spec-driven dark coat with sparse stars, dense micro sparkle, and high contrast flecks.", swatch: "#18243F", colorSafe: true },
    { id: "efx_spectral_edge", name: "EFX Spectral Edge", desc: "Spec-driven sharp light corridors with multi-frequency spectral edge shimmer.", swatch: "#D0F0FF", colorSafe: true },
    { id: "efx_frost_mercury_duo", name: "EFX Frost Mercury Duo", desc: "Spec-driven frost and mercury recipe with cold crystalline shine and liquid metal depth.", swatch: "#C8F5FF", colorSafe: true },
    { id: "efx_aurora_obsidian_veil", name: "EFX Aurora Obsidian Veil", desc: "Spec-driven aurora veil over obsidian energy with dark glassy color movement.", swatch: "#14352F", colorSafe: true },
    { id: "efx_damascus_trinity", name: "EFX Damascus Trinity", desc: "Spec-driven triple Damascus recipe with folded bands, ridges, and layered metallic reads.", swatch: "#91856F", colorSafe: true },
    { id: "efx_cathedral_holographic", name: "EFX Cathedral Holographic", desc: "Spec-driven cathedral glass network fused with holographic micro diffraction.", swatch: "#B6F0FF", colorSafe: true },
    { id: "efx_tempered_quattro", name: "EFX Tempered Quattro", desc: "Spec-driven four-part tempered spectrum recipe with fast heat tint and sparkle variety.", swatch: "#C6DDFF", colorSafe: true },
    { id: "efx_crystalline_triad", name: "EFX Crystalline Triad", desc: "Spec-driven crystalline triad with frost, glass, and spectral shard detail.", swatch: "#D6F7FF", colorSafe: true },
    { id: "efx_volcanic_triad", name: "EFX Volcanic Triad", desc: "Spec-driven volcanic triad with obsidian fractures, hot ridges, and mineral depth.", swatch: "#4B1810", colorSafe: true },
    { id: "efx_aurora_fold", name: "EFX Aurora Fold", desc: "Spec-driven aurora and folded metal recipe with flowing color and layered ridges.", swatch: "#70E0C0", colorSafe: true },
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
    { id: "candy_gold", name: "Candy Gold", desc: "Liquid amber candy over bright gold flake — deep wet gloss with crisp metalflake sparkle", swatch: "#c8920a", colorSafe: true },
    { id: "candy_lime", name: "Candy Lime", desc: "Vivid chartreuse candy over silver-green flake — bright wet candy, fine flake detail", swatch: "#7fbf12", colorSafe: true },
    { id: "candy_aqua", name: "Candy Aqua", desc: "Beachy turquoise candy over silver flake — deep wet aqua depth with crisp sparkle", swatch: "#11a89e", colorSafe: true },
    { id: "copper_pearl", name: "Copper Pearl", desc: "Warm copper/bronze mica pearl — fine platelet shift, rich metal nacre", swatch: "#9c5a2e", colorSafe: true },
    { id: "coral_pearl", name: "Coral Pearl", desc: "Beachy coral/peach mica pearl — soft warm shimmer with fine platelets", swatch: "#c66a60", colorSafe: true },
    { id: "gunmetal_satin", name: "Gunmetal Satin Industrial", desc: "CNC-machined alloy satin — dark metallic without gloss, raw processed metal aesthetic", swatch: "#3a3a44", colorSafe: true },
    { id: "forged_carbon_vis", name: "Forged Carbon Visible", desc: "Lamborghini forged carbon — random-fiber organic weave, non-repeating charcoal with wet clearcoat depth", swatch: "#1a1a1c" },
    { id: "electroplated_gold", name: "Electroplated Gold / Rose Gold", desc: "Warm mirror — near-chrome metallic with warm gold or rose-gold albedo, Rolls-Royce Bespoke reference", swatch: "#c8a028", colorSafe: true },
    { id: "cerakote_pvd", name: "Cerakote / PVD Hard Coat", desc: "TiN/TiAlN thin hard coating — muted deep colors, flat zero-clearcoat surface, firearms/motorsport hardware aesthetic", swatch: "#445544", colorSafe: true },
    { id: "hypershift_spectral", name: "Black Diamond Candy", desc: "Near-black candy over fine diamond flake — a full-spectrum spark stays buried, igniting only at grazing angles", swatch: "#1a1a22", colorSafe: true },
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
    // ★ MORTAL SHOKK V2 — 4K reference-plate-driven married paint+spec finishes
    // 2026-05-22: replaced old 15 algorithmic finishes with 26 V2 plate-driven ids
    // (matches assets/reference_textures/mortal_shokk/manifest.json + cultural_mortal_shokk.py).
    { id: "ms_acid_veil_ambush", name: "MS Acid Veil Ambush", desc: "Acid mist veil hiding chrome strike zones. Toxic ambush vibe.", swatch: "#66BB22" },
    { id: "ms_blood_empress", name: "MS Blood Empress", desc: "Regal deep-crimson with imperial gold edge highlights. Empress aura.", swatch: "#99112A" },
    { id: "ms_bone_sonata", name: "MS Bone Sonata", desc: "Bone-white plate with melodic shadow ribs. Skeletal harmony.", swatch: "#DDD5C0" },
    { id: "ms_chainburst_inferno", name: "MS Chainburst Inferno", desc: "Cascading flame chains burst across dark metal. Chain reaction inferno.", swatch: "#EE4411" },
    { id: "ms_cinder_spiral", name: "MS Cinder Spiral", desc: "Spiraling ember sparks on cooling ash substrate. Cinder vortex.", swatch: "#CC5500" },
    { id: "ms_crimson_dragon", name: "MS Crimson Dragon", desc: "Dragon-scale crimson with shadow-etched scale boundaries. Apex predator.", swatch: "#B01818" },
    { id: "ms_cryo_shard", name: "MS Cryo Shard", desc: "Frozen cyan shards on glacial substrate. Sub-zero kill strike.", swatch: "#88E8F8" },
    { id: "ms_crystal_onslaught", name: "MS Crystal Onslaught", desc: "Faceted crystal assault with prism-edge refraction. Shatter-strike.", swatch: "#C8E0F0" },
    { id: "ms_dragon_ascent", name: "MS Dragon Ascent", desc: "Ascending dragon gold with flame-trail accents. Rising power finish.", swatch: "#DD9911" },
    { id: "ms_dragon_soul", name: "MS Dragon Soul", desc: "Soul-ember dragon jade with inner glow channels. Spiritual depth.", swatch: "#228866" },
    { id: "ms_emerald_scale_mirage", name: "MS Emerald Scale Mirage", desc: "Emerald scale shimmer that shifts at viewing angle. Iridescent mirage.", swatch: "#228855" },
    { id: "ms_fang_cataclysm", name: "MS Fang Cataclysm", desc: "Tooth-shard cataclysm on slate armor. Predator devastation.", swatch: "#444455" },
    { id: "ms_frost_sentinel", name: "MS Frost Sentinel", desc: "Frozen sentinel-blue with vigilant ice crystals. Guardian frost.", swatch: "#6699CC" },
    { id: "ms_frozen_inferno", name: "MS Frozen Inferno", desc: "Paradox blue cold-flame on icefire substrate. Frozen burn.", swatch: "#4477BB" },
    { id: "ms_lotus_ascention", name: "MS Lotus Ascention", desc: "Sacred lotus rising in pink-gold petals. Spiritual ascent finish.", swatch: "#E090B0" },
    { id: "ms_molten_sting", name: "MS Molten Sting", desc: "Molten metal sting with droplet flares. Liquid-flame venom.", swatch: "#DD6611" },
    { id: "ms_porcelain_cipher", name: "MS Porcelain Cipher", desc: "Encoded porcelain glaze with cipher-line crackles. Mystery finish.", swatch: "#E8DDD0" },
    { id: "ms_serpent_haze_strike", name: "MS Serpent Haze Strike", desc: "Toxic serpent haze with venom-strike accents. Coiled deadliness.", swatch: "#88BB22" },
    { id: "ms_shadow_wraith", name: "MS Shadow Wraith", desc: "Spectral wraith-black with faint shadow-duplicate shimmer. Nearly invisible.", swatch: "#221122" },
    { id: "ms_soul_forge", name: "MS Soul Forge", desc: "Forged amber with soul-ember inner glow. Crafted-spirit finish.", swatch: "#CC8833" },
    { id: "ms_tempest_crown", name: "MS Tempest Crown", desc: "Storm-crown tempest blue with lightning crown veins. Sovereign storm.", swatch: "#3344AA" },
    { id: "ms_thunder_mandala", name: "MS Thunder Mandala", desc: "Sacred thunder mandala in electric violet rays. Storm-spiritual finish.", swatch: "#6633CC" },
    { id: "ms_toxic_labyrinth", name: "MS Toxic Labyrinth", desc: "Toxic neon maze on contaminated substrate. Hazmat puzzle aesthetic.", swatch: "#99DD11" },
    { id: "ms_venom_eclipse", name: "MS Venom Eclipse", desc: "Eclipse venom-dark purple with corona shimmer. Total venom blackout.", swatch: "#4D1A66" },
    { id: "ms_venom_veil", name: "MS Venom Veil", desc: "Venomous veil mixing serpent green and amethyst poison.", swatch: "#884499" },
    { id: "ms_zero_hour", name: "MS Zero Hour", desc: "Final-hour steel grey with last-second crisis veins. Apocalypse finish.", swatch: "#555566" },
    // ★ MONEY SHOKK — The Money Shot angle-reveal color change (2026-05-27 breakthrough)
    { id: "msh_canary_coffin", name: "MSH: Canary Coffin", desc: "V2 — electric blue body, lavender/pink coffin-rust reveal; finer spec gates + chroma lift.", swatch: "#3344EE" },
    { id: "msh_magenta_widow", name: "MSH: Magenta Widow", desc: "V2 — deep blue-indigo body, hot pink/crimson web flashes. Neon ice base + widow venom overlay.", swatch: "#2244AA" },
    { id: "msh_cerulean_cobra", name: "MSH: Cerulean Cobra", desc: "V2 — sapphire-indigo body, molten gold scale bloom. Deep blue hue rotation, no white wash.", swatch: "#2233CC" },
    { id: "msh_lime_scorpion", name: "MSH: Lime Scorpion", desc: "Violet-indigo base with ember-hex copper bloom. Densest spec tiling in the set.", swatch: "#5533AA" },
    { id: "msh_hyperpink_torii", name: "MSH: Hyperpink Torii", desc: "V2 — sapphire-teal body, peach-gold torii lattice flare. Magenta arc → deep blue, colored reveal.", swatch: "#2266BB" },
    { id: "msh_seafoam_piranha", name: "MSH: Seafoam Piranha", desc: "V2 — deep blue body, electric aqua/magenta current streaks. Cerulean base replaces dead seafoam green.", swatch: "#2244AA" },
    { id: "msh_orchid_kintsugi", name: "MSH: Orchid Kintsugi", desc: "Teal-green body, champagne-gold crack-line reveal. Orchid pulse + kintsugi rift.", swatch: "#228866" },
    { id: "msh_peach_jellyshock", name: "MSH: Peach Jellyshock", desc: "V2 — ice-blue body, burned hot pink jelly drift. Owner hue-shift proof: blue base + jellyshock overlay.", swatch: "#66BBFF" },
    { id: "msh_daffodil_bayou", name: "MSH: Daffodil Bayou", desc: "V2 — electric indigo body, violet/pink bayou script smoke. Canary→indigo + denser bayou overlay.", swatch: "#4433CC" },
    { id: "msh_neonice_rising", name: "MSH: Neon Ice Rising", desc: "Ice-blue body, sunset orange prismwave crown on roof and quarters.", swatch: "#88DDFF" },

    // ★ MONEY SHOKK CLAUDE — Claude Opus 4.7 bake-off entry (2026-05-27)
    { id: "mshc_tigerblood_voltage", name: "MSHC: Tigerblood Voltage", desc: "Deep indigo body, amber tiger-claw flash on glancing sun. Tiger Fang Fracture overlay.", swatch: "#1a1040" },
    { id: "mshc_oxblood_seigaiha", name: "MSHC: Oxblood Seigaiha", desc: "Magenta → sea-green wave body with chrome crest peaks. Seigaiha Chrome overlay.", swatch: "#cc2288" },
    { id: "mshc_emerald_sharkbite", name: "MSHC: Emerald Sharkbite", desc: "Seafoam → ruby-coral reveal with salt-teeth gates. Sharkbite Riptide overlay.", swatch: "#40e0d0" },
    { id: "mshc_amber_panther", name: "MSHC: Amber Panther", desc: "Peach → deep teal-night body, amber pearl glints catch on curve. Panther Shadow Claw overlay.", swatch: "#ffaa66" },
    { id: "mshc_violet_kyoto", name: "MSHC: Violet Kyoto", desc: "Cerulean → red-violet with gold filigree pins. Kyoto Lantern Filigree overlay.", swatch: "#4b0082" },
    { id: "mshc_acid_hornet", name: "MSHC: Acid Hornet", desc: "Pink → acid yellow-green swarm reveal. Hornet Swarm Static overlay.", swatch: "#ff69b4" },
    { id: "mshc_oni_orchid_glass", name: "MSHC: Oni Orchid Glass", desc: "Orchid → coral-amber demon-mosaic shadows. Oni Veil Mosaic overlay.", swatch: "#da70d6" },
    { id: "mshc_copper_jubilee", name: "MSHC: Copper Jubilee", desc: "Daffodil → indigo-blue with warm copper voodoo-root reveal. Root Doctor Copper overlay.", swatch: "#ffd700" },
    { id: "mshc_canary_widow_redux", name: "MSHC: Canary Widow Redux", desc: "Canary → coral-orange with ruby web flashes. Same base, +63 rotation, Widow Web Venom.", swatch: "#eebb22" },
    { id: "mshc_rosethorn_bonsai", name: "MSHC: Rosethorn Bonsai", desc: "Ice blue → soft violet-rose with leaf-circuit gates. Bonsai Drift Circuit overlay.", swatch: "#afeeee" },

    // ★ MONEY SHOKK ANTIGRAVITY — Antigravity bake-off entry (2026-05-27)
    { id: "msha_canary_gris_gris", name: "MSHA: Canary Gris-Gris", desc: "Electric indigo-blue base with a soft pearlescent amethyst crystal shift. Midnight Gris-Gris overlay.", swatch: "#3f00ff" },
    { id: "msha_emerald_brocade", name: "MSHA: Emerald Brocade", desc: "Bright jade-teal body that flashes coral-gold scales in direct sunlight. Shogun Scale Brocade overlay.", swatch: "#00a86b" },
    { id: "msha_fuji_neon_crest", name: "MSHA: Fuji Neon Crest", desc: "Icy cyan-violet base that blooms with warm bronze-pink frost peaks. Fuji Frost Crest overlay.", swatch: "#00ffff" },
    { id: "msha_volcanic_croc", name: "MSHA: Volcanic Croc", desc: "Deep indigo body shifting to molten lava gold plates under high angles. Croc Delta Armor overlay.", swatch: "#4b0082" },
    { id: "msha_cherry_blossom_flux", name: "MSHA: Cherry Blossom Flux", desc: "Intense sky-teal body blooming cherry-blossom pink under direct solar rays. Sakura Static overlay.", swatch: "#00ced1" },
    { id: "msha_waxen_voodoo", name: "MSHA: Waxen Voodoo", desc: "Cobalt-violet body with shifting pale amber candle-wax veves catching solar glare. Candle Wax Veve overlay.", swatch: "#4b0082" },
    { id: "msha_hyperpink_threads", name: "MSHA: Hyperpink Threads", desc: "Neon violet base with golden micro-thread grid reveals that sparkle under motion. Pins & Thread overlay.", swatch: "#8a2be2" },
    { id: "msha_peach_burlap", name: "MSHA: Peach Burlap", desc: "Mint-teal base with shifting copper-rose hex burlap texture. Bayou Hex Burlap overlay.", swatch: "#98ff98" },
    { id: "msha_seafoam_charm", name: "MSHA: Seafoam Charm", desc: "Royal purple body with shifting emerald-patina charms under grazing sunlight. Swamp Charm Patina overlay.", swatch: "#7b1fa2" },
    { id: "msha_solar_moss", name: "MSHA: Solar Moss", desc: "Electric magenta base that shifts to moss-green sparkles under glanced lighting. Spanish Moss Static overlay.", swatch: "#ff007f" },

    // ★ MONEY SHOKK CODEX — Codex bake-off entry (2026-05-27)
    { id: "mshx_blueprint_jackpot", name: "MSHX: Blueprint Jackpot V2", desc: "Rebuilt after owner 3/REBUILD — tighter coffin gates, stronger blue-indigo landing, brighter lavender/pink flare.", swatch: "#6732e0" },
    { id: "mshx_venom_cashmere", name: "MSHX: Venom Cashmere V2", desc: "Rebuilt after owner 4/REBUILD — neon-ice base, blue/purple body, colored tiger-fang glints instead of white glare.", swatch: "#d617e5" },
    { id: "mshx_glacier_pinkslip", name: "MSHX: Glacier Pinkslip V2", desc: "Rebuilt after owner 3/REBUILD — Prism Tipjar-derived sapphire body with sharkbite pink/ice flare.", swatch: "#1585bd" },
    { id: "mshx_lime_afterburner", name: "MSHX: Lime Afterburner V2", desc: "Rebuilt after owner 5/REBUILD — deeper blue-purple landing with dense copper scorpion ember cells.", swatch: "#b21adb" },
    { id: "mshx_miami_blacklight", name: "MSHX: Miami Blacklight V2", desc: "Rebuilt after owner 3/REBUILD — neon-ice substrate with magenta widow-web flare baked into the reveal.", swatch: "#c719e7" },
    { id: "mshx_royal_sunstroke", name: "MSHX: Royal Sunstroke V2", desc: "Rebuilt after owner 3/REBUILD — canary-to-indigo base with champagne/pink Kyoto pin bloom.", swatch: "#6732e0" },
    { id: "mshx_kintsugi_ransom", name: "MSHX: Kintsugi Ransom", desc: "Teal-night paint with pale-gold fracture flashes that read expensive fast. Orchid + Kintsugi Rift.", swatch: "#127f78" },
    { id: "mshx_coral_sharkskin", name: "MSHX: Coral Sharkskin V2", desc: "Rebuilt after owner 3/REBUILD — owner-proven blue-base direction with hot piranha current scratches.", swatch: "#c719e7" },
    { id: "mshx_dover_jackpot", name: "MSHX: Dover Jackpot V2", desc: "Rebuilt after owner 3/REBUILD — darker indigo Dover body with tighter violet/pink smoke-script payout.", swatch: "#391de0" },
    { id: "mshx_prism_tipjar", name: "MSHX: Prism Tipjar", desc: "Sapphire-teal body tipping warm orange/pink from prismwave micro-crowns in motion. Magenta + Rising Sun Prismwave.", swatch: "#146aa8" },
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
    { id: "neon_rainbow_tube", name: "NU Rainbow Tube", desc: "Full spectrum neon tube with horizontal banding. All wavelengths.", swatch: "#FF4488" }
    // 2026-05-18 (owner mandate): Textile-Inspired (6), Stone & Mineral (6),
    // and Paint Technique (6) base categories TOTALLY REMOVED. Renderers
    // for these ids were previously skipped in the engine ("Missing ids
    // skipped" log line) so the picker tiles were dead weight. Source-of-
    // truth bases removed here; downstream BASE_GROUPS, BASE_METADATA,
    // BASE_FAMILY_MAP, and HERO_BASES entries scrubbed alongside.
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
    barn_find:     { family: "weathered", substrate: "paint", coating: "none", tier: "premium", aggression: 3, sponsor_safe: false, best_with: ["acid_wash", "battle_worn"] },
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
    battle_patina: { family: "weathered", substrate: "metal", coating: "none", tier: "standard", aggression: 4, sponsor_safe: false, best_with: ["battle_worn"] },
    sun_fade:      { family: "weathered", substrate: "paint", coating: "none", tier: "standard", aggression: 2, sponsor_safe: true, best_with: ["none", "acid_wash"] },
    oxidized:      { family: "weathered", substrate: "metal", coating: "oxide", tier: "standard", aggression: 3, sponsor_safe: true, best_with: ["none"] },

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
    metallic: ["anime_gradient_hair","anime_mecha_plate","anime_sakura_scatter","anime_speed_lines","anodized_exotic","beetle_stag","burnt_headers","cc_bronze_heat","cc_inferno","cc_royal_purple","cc_toxic","copper","cx_arctic","cx_aurora_borealis","cx_blood_mercury","cx_frozen_nebula","cx_phantom","cx_prism_shatter","cx_venom","drag_strip_gloss","dragonfly_wing","enh_anodized","enh_metallic","f_metallic","factory_basecoat","ferrari_rosso","fine_silver_flake","firefly_glow","gunmetal","infinite_finish","metallic","ms_blood_empress","ms_crimson_dragon","ms_dragon_ascent","ms_dragon_soul","ms_lotus_ascention","ms_molten_sting","ms_serpent_haze_strike","ms_soul_forge","ms_tempest_crown","ms_thunder_mandala","opal","organic_metal","p_coronal","p_non_euclidean","pagani_tricolore","porsche_pts","satin_gold","shokk_aurora","shokk_catalyst","shokk_dual","shokk_fusion_base","shokk_inferno","shokk_phase","shokk_reactor","shokk_rift","shokk_tesseract_v2","shokk_wraith","xirallic"],
    heavy_metallic: ["anime_cel_shade_chrome","anime_crystal_facet","anime_energy_aura","anime_neon_outline","anime_sparkle_burst","antique_chrome","beetle_jewel","beetle_rainbow","bentley_silver","blue_ice_flake","bugatti_blue","butterfly_morpho","cc_arctic_freeze","cc_electric_cyan","cc_solar_gold","champagne","cobalt_metal","cx_inferno","cx_royal_spectrum","cx_solar","diamond_coat","f_pvd_coating","graphene","green_flake","gunmetal_flake","holographic_base","maybach_two_tone","metal_flake_base","ms_chainburst_inferno","ms_cinder_spiral","ms_crystal_onslaught","ms_emerald_scale_mirage","ms_thunder_mandala","p_time_reversed","plasma_core","plasma_metal","prismatic","raw_aluminum","red_chrome","scarab_gold","shokk_apex","shokk_blood","shokk_cipher","shokk_flux","shokk_helix","shokk_mirage","shokk_polarity","shokk_prism","shokk_pulse","shokk_static","shokk_surge","shokk_vortex","victory_lane"],
    pearl: ["dealer_pearl","deep_pearl","enh_pearl","f_pearl","jelly_pearl","midnight_pearl","pace_car_pearl","pearl","pearlescent_white","tri_coat_pearl"],
    candy: ["candy","candy_apple","candy_burgundy","candy_cobalt","candy_emerald","f_candy"],
    ceramic: ["ceramic","ceramic_matte","enamel","enh_baked_enamel","enh_ceramic_glaze","enh_gel_coat","f_baked_enamel","f_gel_coat","stock_car_enamel","tempered_glass"],
    gloss: ["ambulance_white","bioluminescent","cc_midnight","crystal_clear","enh_eggshell","enh_gloss","enh_piano_black","enh_semi_gloss","enh_silk","enh_soft_gloss","enh_wet_look","f_soft_gloss","fire_engine","fleet_white","gloss","lamborghini_verde","mclaren_orange","nebula","obsidian","p_phantom","p_superfluid","piano_black","police_black","porcelain","race_day_gloss","school_bus","semi_gloss","shokk_venom","showroom_clear","smoked","solar_panel","taxi_yellow","wet_look"],
    satin: ["battleship_gray","eggshell","enh_clear_satin","enh_satin","enh_warm_white","f_clear_satin","f_pure_white","f_warm_white","rally_mud","satin","sun_baked"],
    matte: ["asphalt_grind","chalky_base","clear_matte","dark_matter","enh_clear_matte","enh_living_matte","enh_matte","enh_neutral_grey","enh_primer","enh_pure_black","enh_soft_matte","f_matte","f_neutral_grey","f_pure_black","f_soft_matte","f_wrinkle_coat","flat_black","gunship_gray","living_matte","matte","mil_spec_od","mil_spec_tan","neutron_star","orange_peel_gloss","p_seismic","primer","quantum_black","satin_candy","scuffed_satin","shokk_void","sub_black","submarine_black","vantablack","velvet_floc"],
    vinyl: ["enh_vinyl_wrap","f_vinyl_wrap","gloss_wrap","liquid_wrap","matte_wrap","satin_wrap","stealth_wrap","textured_wrap"],
    carbon: ["aramid","carbon_base","carbon_ceramic","carbon_weave","enh_carbon_fiber","f_carbon_fiber","fiberglass","forged_carbon_vis","kevlar_base"],
    industrial: ["cerakote","cerakote_gloss","cerakote_pvd","duracoat","endurance_ceramic","enh_powder_coat","f_powder_coat","powder_coat"],
    weathered: ["acid_etch","acid_rain","barn_find","battle_patina","crumbling_clear","cx_acid_rain","desert_worn","destroyed_coat","f_patina","f_weathering_steel","ms_toxic_labyrinth","oxidized","oxidized_copper","patina_bronze","patina_coat","salt_corroded","sun_fade","track_worn"],
    optical: ["chameleon","chromaflair","color_flip_wrap","hypershift_spectral","iridescent"],
    exotic: ["anime_comic_halftone","anodized","arctic_ice","armor_plate","blackout","butterfly_monarch","cc_blood_wash","cx_apocalypse","cx_chrome_void","cx_dragon_scale","cx_electric_storm","cx_glacier_fire","cx_hellfire","cx_midnight_chrome","cx_neon_abyss","cx_obsidian_gold","cx_ocean_trench","cx_rose_chrome","cx_supernova","cx_toxic_chrome","cx_white_lightning","enh_frozen","f_anodized","f_bead_blast","f_frozen","f_galvanized","f_hot_dip","f_mill_scale","f_sand_cast","f_shot_peen","f_thermal_spray","forged_composite","frozen","frozen_matte","galvanized","gunmetal_satin","heat_treated","hybrid_weave","koenigsegg_clear","moonstone","moth_luna","ms_acid_veil_ambush","ms_bone_sonata","ms_cryo_shard","ms_fang_cataclysm","ms_frost_sentinel","ms_frozen_inferno","ms_porcelain_cipher","ms_shadow_wraith","ms_venom_eclipse","ms_venom_veil","ms_zero_hour","p_hypercane","p_programmable","p_volcanic","pewter","quantum_foam","rugged","sandblasted","silk","singularity","superconductor","tinted_clear","tinted_lacquer","titanium_raw","volcanic","wasp_warning"],
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
    // === LET FREEDOM RING PATTERNS 2026-06-09 START === (UV-agnostic patriotic drop)
    { id: "lfr_star_lattice", name: "Star Lattice", desc: "Liberty stars scattered at random sizes and rotations — a constellation of five-point stars with faint blue halos, never a grid, never upright", swatch: "linear-gradient(135deg, #1a2a6c 0%, #e8e8f0 55%, #3a4a9c 100%)", category: "Let Freedom Ring", tags: ["patriotic", "stars", "july4", "freedom"] },
    { id: "lfr_stripe_drift", name: "Stripe Drift", desc: "Tapered red-and-white bands drifting at many different angles, widening and pinching — flag-stripe spirit freed from being parallel", swatch: "linear-gradient(115deg, #b02030 0%, #f0f0f4 45%, #c03040 100%)", category: "Let Freedom Ring", tags: ["patriotic", "stripes", "july4", "freedom"] },
    { id: "lfr_bunting_scallop", name: "Bunting Scallop", desc: "Scattered swags of patriotic bunting — nested red/white/blue arc scallops flung at random rotations like festival bunting draped every which way", swatch: "linear-gradient(150deg, #b02030 0%, #f0f0f4 40%, #1a2a6c 100%)", category: "Let Freedom Ring", tags: ["patriotic", "bunting", "july4", "freedom"] },
    { id: "lfr_distressed_flag", name: "Distressed Flag", desc: "All-over weathered patriotic texture — cracked, faded, sun-bleached red/white/blue worn into the surface like a battle-worn vintage flag", swatch: "linear-gradient(125deg, #8a2530 0%, #c8c0b8 50%, #2a3a64 100%)", category: "Let Freedom Ring", tags: ["patriotic", "weathered", "vintage", "july4"] },
    { id: "lfr_eagle_crest", name: "Eagle Crest", desc: "Omnidirectional brocade of abstract eagle crests — swept wing-fan rosettes with bright shield hearts, scattered like heraldic damask", swatch: "linear-gradient(140deg, #1a2a5c 0%, #d8b040 55%, #243468 100%)", category: "Let Freedom Ring", tags: ["patriotic", "eagle", "heraldic", "july4"] },
    { id: "lfr_firework_radial", name: "Firework Radial", desc: "Bursting fireworks scattered across the surface — radial spark-bursts with white-hot cores and sparkle shells detonating from random points", swatch: "linear-gradient(160deg, #101830 0%, #e8c050 50%, #b02030 100%)", category: "Let Freedom Ring", tags: ["patriotic", "fireworks", "july4", "freedom"] },
    { id: "lfr_constellation_field", name: "Constellation Field", desc: "An irregular night-sky field of liberty stars — glowing points of varied brightness with faint connecting constellation lines, nothing aligned to a grid", swatch: "linear-gradient(130deg, #0e1430 0%, #8090d0 60%, #141c3c 100%)", category: "Let Freedom Ring", tags: ["patriotic", "stars", "night", "july4"] },
    { id: "lfr_ribbon_weave", name: "Ribbon Weave", desc: "Omnidirectional over-under weave of red, white and blue ribbons interlacing on two randomly-rotated axes — reads diagonal, never an upright grid", swatch: "linear-gradient(120deg, #b02030 0%, #f0f0f4 35%, #1a2a6c 70%, #b02030 100%)", category: "Let Freedom Ring", tags: ["patriotic", "weave", "ribbon", "july4"] },
    { id: "lfr_stencil_stars", name: "Stencil Stars", desc: "Spray-painted stencil stars at random angles and sizes with soft over-spray bleed and fine paint speckle — worn, tactile, all-over", swatch: "linear-gradient(145deg, #2a3a64 0%, #e8e8f0 55%, #34457c 100%)", category: "Let Freedom Ring", tags: ["patriotic", "stencil", "stars", "july4"] },
    { id: "lfr_liberty_filigree", name: "Liberty Filigree", desc: "Sweeping liberty scrollwork — rose-curve and spiral flourishes radiating from scattered hubs in every direction like engraved coin ornament", swatch: "linear-gradient(135deg, #1c2c5e 0%, #c8ccd8 50%, #28386c 100%)", category: "Let Freedom Ring", tags: ["patriotic", "filigree", "ornate", "july4"] },
    // === LET FREEDOM RING PATTERNS 2026-06-09 END ===
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
    // SPB-107 (2026-05-18): wormhole removed from this purge list. It was
    // accidentally swept in with the old Surreal/Dreamscape group when those
    // ids were dropped. Wormhole IS a shipping PARADIGM finish on paint_v3
    // (see engine/paint_v3/paradigm_v3.py) and must remain selectable in
    // the Specials → PARADIGM lane.
    "acid_trip", "antimatter", "astral", "crystal_cave", "dark_fairy", "dragon_breath", "dreamscape", "enchanted", "ethereal", "fourth_dimension", "fractal_dimension", "glitch_reality", "hallucination", "levitation", "mirage", "multiverse", "nebula_core", "phantom_zone", "portal", "simulation", "tesseract", "time_warp", "void_walker",
    "acid_etched_glass", "brushed_steel_dark", "cast_iron", "concrete", "etched_metal", "forged_iron", "granite", "hammered_copper", "obsidian_glass", "sandstone", "slate_tile", "volcanic_rock",
    "art_deco_gold", "barn_find", "beat_up_truck", "classic_racing", "daguerreotype", "diner_chrome", "drive_in", "faded_glory", "grindhouse", "hot_rod_flames", "jukebox", "moonshine", "muscle_car_stripe", "nascar_heritage", "nostalgia_drag", "old_school", "patina_truck", "pin_up", "psychedelic", "sepia", "tin_type", "vinyl_record", "woodie", "woodie_wagon", "zeppelin",
    // 2026-06-08 audit: hidden — no engine renderer (would crash on click).
    // The v6.2.z MONOLITHIC_WAVE (30 rl_/v_/sf_/w_/fx_ ids) + 2 loose monolithics
    // (acid_rain_drip, carbon_3k_weave) have NO backend renderer → every click
    // raises ValueError 'Unknown base' and the render fails. Stripped here via
    // the existing MONOLITHICS .filter(!REMOVED_SPECIAL_IDS.has(id)) guards; the
    // matching MONOLITHIC_GROUPS sub-tab sections are emptied below.
    "rl_nascar_classic", "rl_f1_carbon_wing", "rl_gt3_pearl", "rl_lmp_silver_arrow", "rl_rally_mud_splat", "rl_drift_wrap",
    "v_70s_stripes", "v_80s_neon_wedge", "v_90s_racing_decal", "v_classic_hot_rod", "v_muscle_car_stripe", "v_touring_car_livery",
    "sf_hologram_shift", "sf_energy_core", "sf_stealth_matte", "sf_plasma_flame", "sf_cyber_circuit", "sf_void_crystal",
    "w_barn_find", "w_rust_belt", "w_sun_faded", "w_salt_corrosion", "w_burn_marks", "w_acid_wash",
    "fx_color_shift_ultra", "fx_glitter_storm", "fx_wet_look_mirror", "fx_liquid_metal", "fx_aurora_wave", "fx_galaxy_dust",
    "acid_rain_drip", "carbon_3k_weave"
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
    "PARADIGM": ["blackbody", "ember", "p_aurora", "pulse", "thin_film", "crystal_lattice_mono", "living_chrome", "mercury_pool", "quantum", "singularity", "phase_shift", "void", "wormhole", "glass_armor", "magnetic", "p_static", "stealth", "p_superfluid", "p_coronal", "p_seismic", "p_hypercane", "p_geomagnetic", "p_non_euclidean", "p_time_reversed", "p_programmable", "p_erised", "p_schrodinger", "p_mercury", "p_phantom", "p_volcanic", "arctic_ice", "nebula", "quantum_foam", "infinite_finish"],
    "★ COLORSHOXX": ["cx_inferno", "cx_arctic", "cx_venom", "cx_solar", "cx_phantom", "cx_chrome_void", "cx_blood_mercury", "cx_neon_abyss", "cx_glacier_fire", "cx_obsidian_gold", "cx_electric_storm", "cx_rose_chrome", "cx_toxic_chrome", "cx_midnight_chrome", "cx_white_lightning", "cx_aurora_borealis", "cx_dragon_scale", "cx_frozen_nebula", "cx_hellfire", "cx_ocean_trench", "cx_supernova", "cx_prism_shatter", "cx_acid_rain", "cx_royal_spectrum", "cx_apocalypse", "cx_gold_green", "cx_gold_purple", "cx_teal_blue", "cx_copper_rose", "cx_gold_olive_emerald", "cx_purple_plum_bronze", "cx_blue_teal_cyan", "cx_burgundy_wine_gold", "cx_sunset_horizon", "cx_northern_lights", "cx_peacock_fan", "cx_rainbow_stealth", "cx_oil_slick", "cx_molten_metal", "cx_red_green_chaos", "cx_orange_blue_electric", "cx_pink_yellow_pop", "cx_purple_gold_majesty", "cx_custom_shift", "cx_pink_to_gold", "cx_blue_to_orange", "cx_purple_to_green", "cx_teal_to_magenta", "cx_red_to_cyan", "cx_sunset_shift", "cx_emerald_ruby", "cx_ice_fire", "cx_hyperflip_red_blue", "cx_hyperflip_pink_black", "cx_hyperflip_orange_cyan", "cx_hyperflip_lime_purple", "cx_hyperflip_purple_gold", "cx_hyperflip_electric_blue_copper", "cx_hyperflip_bronze_teal", "cx_hyperflip_silver_violet", "cx_hyperflip_crimson_prism", "cx_hyperflip_midnight_opal", "cx_cotton_candy", "cx_forest_fire", "cx_deep_sea", "cx_galaxy_dust", "cx_autumn_blaze", "cx_thunderstorm", "cx_tropical_sunset", "cx_black_ice", "cx_cherry_blossom", "cx_volcanic_glass", "cx_neon_dreams", "cx_champagne_toast", "cx_emerald_city", "cx_midnight_aurora", "cx_bronze_age"],
    "★ MORTAL SHOKK": ["ms_acid_veil_ambush", "ms_blood_empress", "ms_bone_sonata", "ms_chainburst_inferno", "ms_cinder_spiral", "ms_crimson_dragon", "ms_cryo_shard", "ms_crystal_onslaught", "ms_dragon_ascent", "ms_dragon_soul", "ms_emerald_scale_mirage", "ms_fang_cataclysm", "ms_frost_sentinel", "ms_frozen_inferno", "ms_lotus_ascention", "ms_molten_sting", "ms_porcelain_cipher", "ms_serpent_haze_strike", "ms_shadow_wraith", "ms_soul_forge", "ms_tempest_crown", "ms_thunder_mandala", "ms_toxic_labyrinth", "ms_venom_eclipse", "ms_venom_veil", "ms_zero_hour"],
    "★ MONEY SHOKK": ["msh_canary_coffin", "msh_magenta_widow", "msh_cerulean_cobra", "msh_lime_scorpion", "msh_hyperpink_torii", "msh_seafoam_piranha", "msh_orchid_kintsugi", "msh_peach_jellyshock", "msh_daffodil_bayou", "msh_neonice_rising", "mshc_tigerblood_voltage", "mshc_oxblood_seigaiha", "mshc_emerald_sharkbite", "mshc_amber_panther", "mshc_violet_kyoto", "mshc_acid_hornet", "mshc_oni_orchid_glass", "mshc_copper_jubilee", "mshc_canary_widow_redux", "mshc_rosethorn_bonsai", "msha_canary_gris_gris", "msha_emerald_brocade", "msha_fuji_neon_crest", "msha_volcanic_croc", "msha_cherry_blossom_flux", "msha_waxen_voodoo", "msha_hyperpink_threads", "msha_peach_burlap", "msha_seafoam_charm", "msha_solar_moss", "mshx_blueprint_jackpot", "mshx_venom_cashmere", "mshx_glacier_pinkslip", "mshx_lime_afterburner", "mshx_miami_blacklight", "mshx_royal_sunstroke", "mshx_kintsugi_ransom", "mshx_coral_sharkskin", "mshx_dover_jackpot", "mshx_prism_tipjar"],
    // SPB-102 — same 50 pf_* ids as BASE_GROUPS["★ PRISM FORGE"]; surfaced here for SHOKKER swatch picker lane
    "★ PRISM FORGE": ["pf_event_horizon_spectra", "pf_chromatic_storm", "pf_neon_nova", "pf_molten_aurora", "pf_void_pearl", "pf_ion_trap", "pf_sapphire_blood", "pf_emerald_inferno", "pf_violet_sunrise", "pf_copper_moon", "pf_toxic_horizon", "pf_glacial_burn", "pf_oil_nebula", "pf_rose_quantum", "pf_cobalt_fire", "pf_midnight_prism", "pf_hyperwave", "pf_crystal_fade", "pf_dark_matter_halo", "pf_apex_spectrum", "pf_cluster_tar_eclipse", "pf_cluster_bitumen_aurora", "pf_cluster_obsidian_gild", "pf_cluster_coal_starfield", "pf_cluster_void_islands", "pf_bright_solar_daffodil", "pf_bright_hyperpink", "pf_bright_seafoam_bolt", "pf_bright_cerulean_pop", "pf_bright_canary_glass", "pf_bright_magenta_arc", "pf_bright_lime_voltage", "pf_bright_peach_fizz", "pf_bright_neon_ice_stream", "pf_bright_orchid_pulse", "pf_blend_triad_mist", "pf_blend_quad_weave", "pf_spectrum_chaos_crown", "pf_prismatic_void_madness", "pf_white_castle_of_fear", "pf_gradient_venetian_veil", "pf_tri_crimson_cyan_mage", "pf_quad_jade_violet_gold_slate", "pf_fade_copper_teal_sunset", "pf_blend_ocean_peach_ivory", "pf_iris_velvet_crossfade", "pf_spectral_tidepool_wash", "pf_midnight_coral_ember", "pf_emerald_orchid_storm", "pf_golden_ultraviolet_fog"],
    "Shokk Series": ["burnt_headers", "electric_ice", "mercury", "plasma_metal", "shokk_blood", "shokk_pulse", "shokk_static", "shokk_venom", "shokk_void", "volcanic", "shokk_flux", "shokk_phase", "shokk_dual", "shokk_spectrum", "shokk_aurora", "shokk_helix", "shokk_catalyst", "shokk_mirage", "shokk_polarity", "shokk_reactor", "shokk_prism", "shokk_wraith", "shokk_tesseract_v2", "shokk_fusion_base", "shokk_rift", "shokk_vortex", "shokk_surge", "shokk_cipher", "shokk_inferno", "shokk_apex", "chameleon", "color_flip_wrap", "pagani_tricolore"],
    // 2026-06-02 (owner): the "Angle SHOKK" special group held only 3 finishes
    // (chameleon, color_flip_wrap, pagani_tricolore) — folded into Shokk Series
    // above and the group removed. The 3 ids stay fully registered (tiles,
    // BASE_GROUPS, engine); only the special-group lane changed.
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
    "SOURCE PATTERN PLATES": ["pp_holographic_oil_circuit", "pp_black_emboss_mandala", "pp_graphite_cross_lattice", "pp_marble_flow_pearl", "pp_acid_carbon_mesh", "pp_noir_houndstooth_star", "pp_hazard_chevron_weave", "pp_burn_hole_mesh", "pp_teal_hex_haze", "pp_shadow_diamond_mesh", "pp_talavera_tile_riot", "pp_green_plasma_vein", "pp_neon_fracture_net", "pp_pink_checker_carbon", "pp_red_herringbone_heat", "pp_chrome_oval_chain", "pp_terracotta_ceramic_grid", "pp_gunmetal_geo_tessellation", "pp_tokyo_script_textile", "pp_lime_pixel_confetti", "pp_psychedelic_floral_spin", "pp_ice_facet_shatter", "pp_ember_circuit_maze", "pp_blue_polygon_shatter"],
    "GRUNGE & FUN": ["gf_x_1024293_6391", "gf_x_1024294_6392", "gf_x_1152842_or6ilf0", "gf_x_1195794_6247", "gf_x_1292", "gf_x_13845", "gf_x_1434947_595", "gf_x_16302407_yellow_hexagon_halftone_pattern_backg", "gf_x_18677", "gf_x_18914258_casino_2021_11", "gf_x_19034947_en9y_pjge_210709", "gf_x_19516529_casino_2021_17", "gf_x_20216645_6276400", "gf_x_20771417_v6t9_6fpy_210512", "gf_x_2149635369", "gf_x_22587040_6656535", "gf_x_22587046_6656517", "gf_x_2311", "gf_x_237560942_1f15d9a7_672f_4b74_9792_9a0daae8fbe2", "gf_x_2425", "gf_x_2474", "gf_x_26323837_blue_hexagon_pattern_background", "gf_x_283511752_c9a714fc_a791_4c92_a2af_e3b8537ecaef", "gf_x_29035", "gf_x_30330639_lightabstrback14gradientd", "gf_x_31587230_7837300", "gf_x_3521", "gf_x_391161788_673b312d_2817_44f1_bfa5_bc51bf8df42d", "gf_x_3946420_524", "gf_x_4004", "gf_x_417665166_62a76dd6_56af_4a68_b801_92f5967beda0", "gf_x_420841114_17c7c800_04f4_4c25_8844_09134f10d3a7", "gf_x_426098859_bfe8ddbc_e982_4a17_b396_d362c3e1e12f", "gf_x_426203826_fc914006_6101_4668_8c1d_3322a73a9319", "gf_x_6090", "gf_x_6113", "gf_x_69", "gf_x_819188_26851_nwdlx0", "gf_x_850287_o4yijt0", "gf_x_850288_o4yijy0", "gf_x_8514125_3910277", "gf_x_9121", "gf_x_9169", "gf_x_9338", "gf_x_946728_oe3t1y0", "gf_x_947419_oe46fw0", "gf_x_9819736_12811_1", "gf_magnific_digital_illustration_a_dark_background_"],
    "Atelier — Ultra Detail": ["atelier_brushed_titanium", "atelier_carbon_weave_micro", "atelier_cathedral_glass", "atelier_ceramic_glaze", "atelier_damascus_layers", "atelier_engine_turned", "atelier_fluid_metal", "atelier_forged_iron_texture", "atelier_gold_leaf_micro", "atelier_hand_brushed_metal", "atelier_japanese_lacquer", "atelier_marble_vein_fine", "atelier_micro_flake_burst", "atelier_obsidian_glass", "atelier_pearl_depth_layers", "atelier_silk_weave", "atelier_vintage_enamel_crackle"],
    // 2026-06-02 (owner): "Metals & Forged" special group REMOVED (weak). Dropping the
    // group key removes all its ids from the picker lane. Shared/core finishes
    // (worn_chrome, weathered_paint, damascus_steel) stay engine-registered for
    // other surfaces; their exclusive metal tiles are removed from MONOLITHICS.
    "Glass & Surface": ["obsidian_glass", "stained_glass", "venetian_glass", "acid_etched_glass", "concrete", "granite", "raw_concrete", "sandstone", "slate_tile", "stucco", "terra_cotta", "volcanic_rock", "brick_wall"],
    "Leather & Texture": ["aged_leather", "crocodile_leather", "suede", "velvet", "velvet_crush", "linen", "burlap", "cork", "parchment", "bark", "petrified_wood"],
    // 2026-06-02 (owner): "Standalone Effects" special group REMOVED (weak). Dropping
    // the group key removes all 10 ids from the picker lane.
    // 2026-05-18 (owner mandate): "Brushed & Machined" (only brushed_metal_fine
    // ever actually surfaced as a visible monolithic) and "Ornamental" (8
    // finishes) groups TOTALLY REMOVED from the Material World section.
    "Clearcoat Effects": ["cc_overspray_halo", "cc_panel_fade", "cc_panel_pool", "cc_wet_zone"],
    // 2026-04-23 Codex painter-truth cleanup:
    // retire Carbon & Weave from the shipping special-monolithic surface.
    // The only visibly reachable monolithics here ("carbon_3k_weave" and
    // "carbon_weave") were explicitly painter-rejected, and the spec_* ids
    // never belonged in this monolithic/base picker path to begin with.
    "Natural & Organic": [ "spec_snake_scales", "spec_fish_scales", "spec_terrain_erosion"],
    "Surface Treatment": ["spec_anodized_texture", "spec_pvd_coating", "spec_laser_etched", "spec_galvanic_corrosion", "spec_sandblast_strip", "spec_stress_fractures"],
    "Geometric & Structural": [ "spec_hammered_dimple", "spec_architectural_grid", "spec_brick_mortar", "panel_zones", "hex_cells", "diamond_lattice"],
    "Optical & Light": [ "spec_damascus_steel_spec", "spec_liquid_metal", "spec_chameleon_flake", "spec_iridescent_film", "spec_chromatic_aberration", "spec_fresnel_gradient", "spec_retroreflective", "spec_anisotropic_radial", "diffraction_grating", "holographic_flake", "prismatic_shatter"],
    "Particles & Textures": [ "gold_flake", "metallic_sand", "stardust_fine"],
    // 2026-06-03 (B7): "pearl_micro" pulled from the clickable pattern group — it has no
    // engine PATTERN_REGISTRY renderer (404s in the picker). Tile def kept below; re-add it
    // here once a pattern renderer is wired.
    "Patterns & Effects": ["acid_etch", "banded_rows", "chevron_bands", "crackle_network", "galaxy_swirl", "gradient_bands", "lava_crack", "pebble_grain", "voronoi_fracture", "wave_bands", "wave_ripple"],
};

// 2026-05-18 (owner mandate): Fusion Lab consolidated from 17 subgroups
// (mostly 10-finishes-each tiny piles) into 5 themed mega-groups so the
// picker shows fewer-but-fuller lanes. Original subgroup names kept inline
// as comments for traceability — every id is preserved, only their group
// assignment changed. "★ Spectrum Shift" stays standalone per its 50-finish
// scale and dedicated swatch lane.
const _SPECIALS_FUSION_LAB = {
    "★ Spectrum Shift": ["spectrum_aberration_glitch", "spectrum_abrasion_halo", "spectrum_anodine_dunes", "spectrum_beetle_elytra", "spectrum_bismuth_garden", "spectrum_black_opal", "spectrum_borealis_ice", "spectrum_boulder_opal", "spectrum_chromatic_orchid", "spectrum_circuit_awakens", "spectrum_clockwork_dial", "spectrum_contact_bloom", "spectrum_data_etch", "spectrum_diamond_fire", "spectrum_event_horizon", "spectrum_flare_spectra", "spectrum_forge_heat", "spectrum_fracture_polarized", "spectrum_ghost_prism", "spectrum_grating_quilt", "spectrum_interference_weave", "spectrum_jewel_box", "spectrum_lathe_burst", "spectrum_liquid_crystal", "spectrum_magnet_flow", "spectrum_mantis_strike", "spectrum_moire_silk", "spectrum_nacre_tide", "spectrum_oilfilm_rain", "spectrum_opal_core", "spectrum_orbital_engrave", "spectrum_peacock_eye", "spectrum_pressure_map", "spectrum_prism_pool", "spectrum_rainbow_river", "spectrum_redshift_drift", "spectrum_shatter_glass", "spectrum_singularity_lens", "spectrum_smectic_fan", "spectrum_smoke_chroma", "spectrum_spill_metropolis", "spectrum_star_temperature", "spectrum_stress_storm", "spectrum_swirl_supernova", "spectrum_tempered_ghost", "spectrum_thermo_touch", "spectrum_topo_rainbow", "spectrum_vhs_phantom", "spectrum_vinyl_groove", "spectrum_xray_bloom"],

    // Light & Optics — merged: Light Waves (10) + Spectral Reactive (10)
    // + Metallic Halos (10) + Sparkle Systems (10) = 40 finishes.
    // Theme: how light interacts with the surface (waves, halos, sparkle, spectral shift).
    "Light & Optics": [
        // Light Waves
        "wave_candy_flow", "wave_chrome_tide", "wave_circular_radar", "wave_diagonal_sweep", "wave_dual_frequency", "wave_metallic_pulse", "wave_moire_metal", "wave_pearl_current", "wave_standing_chrome", "wave_turbulent_flow",
        // Spectral Reactive
        "spectral_complementary", "spectral_dark_light", "spectral_earth_sky", "spectral_inverse_logic", "spectral_mono_chrome", "spectral_neon_reactive", "spectral_prismatic_flip", "spectral_rainbow_metal", "spectral_sat_metal", "spectral_warm_cool",
        // Metallic Halos
        "halo_circle_pearl", "halo_crack_chrome", "halo_diamond_chrome", "halo_grid_pearl", "halo_hex_chrome", "halo_ripple_chrome", "halo_scale_gold", "halo_star_metal", "halo_voronoi_metal", "halo_wave_candy",
        // Sparkle Systems
        "sparkle_champagne", "sparkle_confetti", "sparkle_diamond_dust", "sparkle_galaxy", "sparkle_lightning_bug", "sparkle_meteor", "sparkle_snowfall", "sparkle_starfield"
    ],

    // Surface & Grain — merged: Directional Grain (10) + Multi-Scale Texture (10)
    // + Surface Accent (8) + Reactive Panels (10) = 38 finishes.
    // Theme: surface-level micro-features (grain, texture, accents, reactive panels).
    "Surface & Grain": [
        // Directional Grain
        "aniso_circular_chrome", "aniso_crosshatch_steel", "aniso_diagonal_candy", "aniso_herringbone_gold", "aniso_horizontal_chrome", "aniso_radial_metallic", "aniso_spiral_mercury", "aniso_turbulence_metal", "aniso_vertical_pearl", "aniso_wave_titanium",
        // Multi-Scale Texture
        "multiscale_candy_frost", "multiscale_carbon_micro", "multiscale_chrome_grain", "multiscale_chrome_sand", "multiscale_flake_grain", "multiscale_frost_crystal", "multiscale_matte_silk", "multiscale_metal_grit", "multiscale_pearl_texture", "multiscale_satin_weave",
        // Surface Accent
        "iridescent_fog", "chrome_delete_edge", "carbon_clearcoat_lock", "racing_scratch", "pearlescent_flip", "frost_crystal", "satin_wax", "uv_night_accent",
        // Reactive Panels
        "reactive_candy_reveal", "reactive_chrome_fade", "reactive_dual_tone", "reactive_ghost_metal", "reactive_matte_shine", "reactive_mirror_shadow", "reactive_pearl_flash", "reactive_pulse_metal", "reactive_stealth_pop", "reactive_warm_cold"
    ],

    // Depth & Geometry — merged: Depth Illusion (11) + Ghost Geometry (11)
    // + Panel Quilting (10) + Tri-Zone Materials (10) = 42 finishes.
    // Theme: shape/depth/zone illusion (depth fake-outs, ghost geometry, quilted zones, tri-zone splits).
    "Depth & Geometry": [
        // Depth Illusion
        "depth_bubble", "depth_canyon", "depth_crack", "depth_erosion", "depth_honeycomb", "depth_map", "depth_pillow", "depth_ripple", "depth_scale", "depth_vortex", "depth_wave",
        // Ghost Geometry
        "ghost_camo", "ghost_circuit", "ghost_diamonds", "ghost_fracture", "ghost_hex", "ghost_panel", "ghost_quilt", "ghost_scales", "ghost_stripes", "ghost_vortex", "ghost_waves",
        // Panel Quilting
        "quilt_alternating_duo", "quilt_candy_tiles", "quilt_chrome_mosaic", "quilt_diamond_shimmer", "quilt_gradient_tiles", "quilt_hex_variety", "quilt_metallic_pixels", "quilt_organic_cells", "quilt_pearl_patchwork", "quilt_random_chaos",
        // Tri-Zone Materials
        "trizone_anodized_candy_silk", "trizone_ceramic_flake_satin", "trizone_chrome_candy_matte", "trizone_frozen_ember_chrome", "trizone_glass_metal_matte", "trizone_mercury_obsidian_candy", "trizone_pearl_carbon_gold", "trizone_stealth_spectra_frozen", "trizone_titanium_copper_chrome", "trizone_vanta_chrome_pearl"
    ],

    // Materials & Physics — merged: Material Gradients (10) + Exotic Physics (10)
    // + Weather & Age (10) + Fractal Chaos (11) = 41 finishes.
    // Theme: material-level behavior (gradient blends, exotic surfaces, weathering, fractal noise).
    "Materials & Physics": [
        // Material Gradients
        "gradient_anodized_gloss", "gradient_candy_frozen", "gradient_candy_matte", "gradient_carbon_chrome", "gradient_chrome_matte", "gradient_ember_ice", "gradient_metallic_satin", "gradient_obsidian_mirror", "gradient_pearl_chrome", "gradient_spectraflame_void",
        // Exotic Physics
        "exotic_anti_metal", "exotic_ceramic_void", "exotic_crystal_clear", "exotic_dark_glass", "exotic_foggy_chrome", "exotic_glass_paint", "exotic_inverted_candy", "exotic_liquid_glass", "exotic_phantom_mirror", "exotic_wet_void",
        // Weather & Age
        "weather_acid_rain", "weather_barn_dust", "weather_desert_blast", "weather_hood_bake", "weather_ice_storm", "weather_ocean_mist", "weather_road_spray", "weather_salt_spray", "weather_sun_fade", "weather_volcanic_ash",
        // Fractal Chaos
        "fractal_candy_chaos", "fractal_chrome_decay", "fractal_cosmic_dust", "fractal_deep_organic", "fractal_dimension", "fractal_electric_noise", "fractal_liquid_fire", "fractal_matte_chrome", "fractal_metallic_storm", "fractal_pearl_cloud", "fractal_warm_cold"
    ],
};

// NOTE (2026-04-17): _SPECIALS_RACING_HERITAGE intentionally EMPTY.
// Racing Heritage lives exclusively in BASE_GROUPS.Racing Heritage now; the
// Specials duplicate was scrubbed per user request.
const _SPECIALS_RACING_HERITAGE = {};

const _SPECIALS_ATMOSPHERE = {
    "Atmosphere": ["acid_rain", "black_ice", "blizzard", "desert_mirage", "dew_drop", "dust_storm", "ember_glow", "fog_bank", "frost_bite", "frozen_lake", "hail_damage", "heat_wave", "hurricane", "lightning_strike", "liquid_metal", "magma_flow", "meteor_shower", "monsoon", "ocean_floor", "permafrost", "solar_wind", "tidal_wave", "tornado_alley", "volcanic_glass"],
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


const _SPECIALS_CULTURAL = {
    "RISING SUN": ["rs_rising_sun_flare", "rs_oni_bloodshift", "rs_sakura_storm", "rs_hakuryu_ice", "rs_kuro_dragon", "rs_bamboo_zen", "rs_temple_gold", "rs_geisha_whisper", "rs_thunder_dragon", "rs_koi_ascension", "rs_kyoto_lantern", "rs_shibuya_pulse", "rs_kintsugi_moon", "rs_fuji_dawn", "rs_matcha_ceremony", "rs_kabuki_inferno", "rs_indigo_tsunami", "rs_vermilion_torii", "rs_crane_garden", "rs_sumi_eclipse", "rs_yurei_veil", "rs_kitsune_ember", "rs_oni_nocturne", "rs_gashadokuro_moon", "rs_jorogumo_silk", "rs_tengu_storm", "rs_bakeneko_velvet", "rs_nure_onna_tide", "rs_hyakki_parade", "rs_bell_of_damned", "rs_sakura_cascade", "rs_wisteria_reverie", "rs_lotus_reverie", "rs_peony_festival", "rs_iris_rain", "rs_camellia_glow", "rs_plum_blossom_dawn", "rs_chrysanthemum_sun", "rs_hydrangea_mist", "rs_koi_pond_bloom", "rs_bosozoku_riot", "rs_wangan_midnight_pulse", "rs_touge_apex", "rs_drift_hanami_oversteer", "rs_kaido_chrome_bloom", "rs_dekotora_electric_freight", "rs_time_attack_grid_shock", "rs_akane_flake_fog", "rs_kurogane_rain", "rs_kinpaku_blaze", "rs_ryokucha_scroll", "rs_mikan_pearl"],
    "VIVA MEXICO": ["vm_aztec_sunfire", "vm_talavera_azul", "vm_quetzal_sunset", "vm_sacred_heart_eclipse", "vm_guadalupe_lowrider", "vm_rosa_corazon", "vm_mariachi_verde", "vm_calavera_violeta", "vm_serape_sunburst", "vm_riviera_lowrider", "vm_luchador_plata", "vm_luchador_rayo", "vm_cactus_sunset", "vm_sierra_verde", "vm_cenote_lace", "vm_agave_pearl", "vm_baja_horizon", "vm_pacific_coast_dawn", "vm_copper_canyon", "vm_sierra_niebla", "vm_oaxaca_moonwater", "vm_xolo_candy_desert", "vm_huichol_beadwork", "vm_sonora_blue_calavera", "vm_bajio_gold_calaveras", "vm_lucha_rosa", "vm_desert_marigold", "vm_zapata_jade", "vm_cinco_spark", "vm_mezcal_smoke", "vm_riviera_corazon", "vm_noche_buena", "vm_rosario_gold", "vm_pyramid_shadow", "vm_fiesta_chrome", "vm_maguey_pearl", "vm_cantina_neon", "vm_azulejo_storm", "vm_calavera_royal", "vm_talavera_muertos", "vm_tulum_candelaria", "vm_eclipse_ofrenda", "vm_charro_nocturne", "vm_cempasuchil_noir", "vm_sierra_madre", "vm_mole_negro", "vm_veracruz_carnival", "vm_jalisco_flash", "vm_mosaic_jaguar", "vm_milagro_silver", "vm_sacred_cenote", "vm_playa_dorada", "vm_adobe_sunset", "vm_zapotec_thunder", "vm_nopal_bloom", "vm_mayan_jade", "vm_neon_cantina", "vm_baja_cartografia"],
    "UNION JACKED": ["uj_camden_signal_riot", "uj_thames_after_dark", "uj_chelsea_razor_parade", "uj_kings_cross_mercury", "uj_covent_garden_static", "uj_oxford_circus_chrome", "uj_piccadilly_rain_stance", "uj_brick_lane_voltage", "uj_notting_carnival_glass", "uj_beat_burst", "uj_highland_heather_haze", "uj_portobello_pearl_riot", "uj_liverpool_echo_lace", "uj_manchester_acid_union", "uj_glasgow_granite_soul", "uj_belfast_harp_storm", "uj_edinburgh_castle_frost", "uj_welsh_dragon_lacquer", "uj_cornwall_sea_spark", "uj_dover_white_cliff_pearl", "uj_brighton_pier_neon", "uj_southampton_dock_matte", "uj_silverstone_apex_flare", "uj_goodwood_heritage_flake", "uj_isle_of_man_tt_chrome", "uj_ulster_rally_tartan", "uj_highland_fling_metal", "uj_loch_ness_deep_void", "uj_midnight_hearse_baroque", "uj_tudor_rose_filigree", "uj_windsor_guard_gloss", "uj_shard_glass_rain", "uj_gherkin_twist_metal", "uj_black_cab_nocturne", "uj_red_bus_velocity", "uj_routemaster_candy", "uj_mini_cooper_flip", "uj_aston_strait_silver", "uj_bentley_brooklands_mist", "uj_rolls_phantom_veil", "uj_lotus_elan_streak", "uj_mclaren_papaya_strike", "uj_williams_fw_blueblood", "uj_jaguar_etype_silk", "uj_blueblood_beatline"],
    "FORBIDDEN DRAGON": ["fd_azure_celestial", "fd_vermilion_fire", "fd_abyssal_sea", "fd_imperial_gold", "fd_storm_black", "fd_jade_empress", "fd_frost_emperor", "fd_bronze_relic", "fd_pearl_chaser", "fd_dragon_phoenix", "fd_phoenix_fenghuang", "fd_jade_qilin", "fd_guardian_foo_lion", "fd_vermilion_bird", "fd_black_tortoise", "fd_white_tiger_baihu", "fd_crane_garden", "fd_koi_ascension", "fd_pixiu_fortune", "fd_golden_toad_jinchan"],
    "LET FREEDOM RING": ["lfr_old_glory_flux", "lfr_rockets_red_glare", "lfr_liberty_torch", "lfr_eagle_ascendant", "lfr_we_the_people", "lfr_midnight_militia", "lfr_freedom_forge", "lfr_amber_waves", "lfr_glory_chrome", "lfr_sparkler_dusk"],
};
// 2026-05-18 (owner mandate): "Effects & Vision" section (47 finishes)
// TOTALLY REMOVED. Quality bar of the underlying renderers (acid_trip,
// antimatter, kaleidoscope, glitch, etc.) was too far below the 85%
// composite floor to justify retooling. Section header dropped from
// SPECIALS_SECTION_ORDER and SPECIALS_SECTIONS below.
const _SPECIALS_FABLE = {
    "\u2728 FABLE": ["fable_ember_glass", "fable_glacier_core", "fable_abyss_lantern", "fable_stained_aurora", "fable_prism_veil", "fable_oilforge", "fable_tempered_dawn", "fable_pulse_alloy", "fable_velvet_eclipse", "fable_wovenlight", "fable_sovereign_flip", "fable_static_bloom", "fable_aurora_travel", "fable_saffron_circuit", "fable_quicksilver_garden", "fable_emberline_drift", "fable_duomorph", "fable_nightbloom", "fable_magnetite_flow", "fable_comet_parade"],
};

const _SPECIALS_EFFECTS_VISION = {};

// Section order and group → section map
// NOTE (2026-04-17): "Racing Heritage" and "Multi-Spectrum" sections removed
// from Specials. Racing Heritage now lives exclusively under BASE_GROUPS; the
// 25 Multi-Spectrum finishes were scrubbed entirely per user request.
// 2026-05-18 (owner mandate): SPECIALS sweep —
//   • Removed "Effects & Vision" section entirely (47 weak finishes).
//   • Removed "Brushed & Machined" + "Ornamental" subgroups from Material World.
//   • Fusion Lab consolidated from 17 subgroups → 5 themed mega-groups
//     ("Light & Optics", "Surface & Grain", "Depth & Geometry",
//      "Materials & Physics") plus the standalone "★ Spectrum Shift" lane.
const SPECIALS_SECTION_ORDER = ["FRACTURED", "GHOST LAB", "SHOKKER", "FABLE", "Cultural", "Color Science", "Material World", "Fusion Lab", "Atmosphere", "Signal"];
const SPECIALS_SECTIONS = {
    // 2026-06-11 owner flagship: FRACTURED MINDS at the VERY TOP — color-shift
    // bases built on the owner-discovered Ghost Fracture recipe.
    // 2026-06-12 owner: ONE main category "FRACTURED" with the two
    // sub-lanes as its folders (MINDS = 55, SOULS = the apex drops)
    "FRACTURED": ["\U0001F9E0 FRACTURED MINDS", "💀 FRACTURED SOULS"],
    // 2026-06-12: Ghost Fracture isolation experiments (single-variable variants)
    "GHOST LAB": ["🔬 GHOST LAB"],
    "FABLE": ["\u2728 FABLE"],
    "Cultural": ["RISING SUN", "VIVA MEXICO", "UNION JACKED", "FORBIDDEN DRAGON", "LET FREEDOM RING"],
    "SHOKKER": ["SHOKK DROP", "PARADIGM", "★ PRISM FORGE", "★ COLORSHOXX", "★ MORTAL SHOKK", "★ MONEY SHOKK", "★ NEON UNDERGROUND", "★ ANIME INSPIRED", "★ IRIDESCENT INSECTS", "Shokk Series", "Extreme & Experimental"], // 2026-05-29 owner UI fix (#2): SHOKK DROP user-imports surface at the TOP of SHOKKER (above PARADIGM); empty/absent until imports exist
    "Color Science": ["Chameleon", "Prizm", "Color-Shift Adaptive", "Color-Shift Presets", "Color-Shift Duos", "Color Clash", "Gradient Directional", "Gradient Vortex", "Gradient Extended"],
    // 2026-06-03: "Aurora & Chromatic Flow" (30 aurora_*) + "Chromatic Flake" (30 cf_*) pulled from the
    // picker for Alpha — mid-rebuild, no engine renderer wired yet (would show as broken/404 tiles).
    // Group definitions kept; re-add these two section refs once Codex rewires their renderers.
    "Material World": ["SOURCE PATTERN PLATES", "GRUNGE & FUN", "Glass & Surface", "Leather & Texture", "Clearcoat Effects", "Natural & Organic", "Surface Treatment", "Geometric & Structural", "Optical & Light", "Particles & Textures", "Patterns & Effects"],
    // 2026-06-03: "Atelier — Ultra Detail" (17 atelier_*) pulled from the picker for Alpha — mid-rebuild,
    // no engine renderer wired (broken/404 tiles). Group def kept; re-add the section ref once rewired.
    "Fusion Lab": ["★ Spectrum Shift", "Light & Optics", "Surface & Grain", "Depth & Geometry", "Materials & Physics"],
    "Atmosphere": ["Atmosphere"],
    "Signal": ["Signal"],
};

// Merged flat object (all reimagined groups — only backend-registered IDs)
const _SPECIALS_FRACTURED_MINDS = {
    "\U0001F9E0 FRACTURED MINDS": ["fm_basalt", "fm_basketweave", "fm_cable_knit", "fm_carbon_weave", "fm_chainlink", "fm_chainmail", "fm_checkerflash", "fm_circuit_maze", "fm_code_cascade", "fm_croc_hide", "fm_damascus", "fm_diamond_plate", "fm_diamondback", "fm_dragon_scale", "fm_dragonfly", "fm_ebru_marble", "fm_fiber_optic", "fm_flame_helix", "fm_flame_lick", "fm_flame_wall", "fm_frost_feather", "fm_frost_lace", "fm_geode_slice", "fm_gila_bead", "fm_glacier_core", "fm_graphene", "fm_gyro_cage", "fm_gyroid", "fm_herringbone", "fm_hexcore", "fm_honeycomb_burst", "fm_inferno_veins", "fm_ion_drift", "fm_labyrinth", "fm_lattice", "fm_magma", "fm_mudcrack", "fm_nanoweave", "fm_octo_suckers", "fm_penrose", "fm_petal_storm", "fm_python_skin", "fm_riverine", "fm_rivet_array", "fm_rope_coil", "fm_static_burst", "fm_stingray", "fm_tessellate", "fm_thousand_eyes", "fm_tide_glass", "fm_tiger_slash", "fm_topo_lines", "fm_tortoise", "fm_tsunami", "fm_witchlight"]
};

const _SPECIALS_FRACTURED_SOULS = {
    "💀 FRACTURED SOULS": ["fs_core_violet", "fs_core_abyss", "fs_core_emerald", "fs_core_crimson", "fs_core_aurum", "fs_wraith_veil", "fs_moth_dust", "fs_blood_marble", "fs_night_tide", "fs_static_veins", "fs_shatter_glass", "fs_howl", "fs_phantom_lattice", "fs_ember_drift", "fs_carnival_night", "fs_soul_loom", "fs_widow_braid", "fs_ghost_silk", "fs_shattered_prism", "fs_oil_serpent", "fs_hex_hive", "fs_guilloche_ghost", "fs_petrol_halo", "fs_star_chart", "fs_serpent_scale", "fs_nova_burst", "fs_circuit_soul", "fs_geode_vein", "fs_moire_phantom", "fs_aurora_threads"]
};

const _SPECIALS_GHOST_LAB = {
    "🔬 GHOST LAB": ["gl_control", "gl_metal_low", "gl_metal_mid", "gl_rough_pastel", "gl_rough_mirror", "gl_cc_flat", "gl_cc_shallow", "gl_cc_inverted", "gl_cells_micro", "gl_cells_macro", "gl_pastel_full", "gl_cc_max"]
};

const SPECIAL_GROUPS = Object.assign({},
    _SPECIALS_FRACTURED_MINDS,
    _SPECIALS_FRACTURED_SOULS,
    _SPECIALS_GHOST_LAB,
    _SPECIALS_SHOKKER,
    _SPECIALS_ANIME_INSPIRED,
    _SPECIALS_IRIDESCENT_INSECTS,
    _SPECIALS_CULTURAL,
    _SPECIALS_FABLE,
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
    // Material World / SOURCE PATTERN PLATES - real source plates + paired spec maps
    { id: "pp_holographic_oil_circuit", name: "Holographic Oil Circuit", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#ba9dff" },
    { id: "pp_black_emboss_mandala", name: "Black Emboss Mandala", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#2e2926" },
    { id: "pp_graphite_cross_lattice", name: "Graphite Cross Lattice", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#c7c4bc" },
    { id: "pp_marble_flow_pearl", name: "Marble Flow Pearl", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#d8d2c8" },
    { id: "pp_acid_carbon_mesh", name: "Acid Carbon Mesh", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#c7e23c" },
    { id: "pp_noir_houndstooth_star", name: "Noir Houndstooth Star", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#5a5962" },
    { id: "pp_hazard_chevron_weave", name: "Hazard Chevron Weave", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#e3c817" },
    { id: "pp_burn_hole_mesh", name: "Burn Hole Mesh", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#4d4238" },
    { id: "pp_teal_hex_haze", name: "Teal Hex Haze", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#7ec3bf" },
    { id: "pp_shadow_diamond_mesh", name: "Shadow Diamond Mesh", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#8b8e91" },
    { id: "pp_talavera_tile_riot", name: "Talavera Tile Riot", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#1e8cb6" },
    { id: "pp_green_plasma_vein", name: "Green Plasma Vein", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#64d550" },
    { id: "pp_neon_fracture_net", name: "Neon Fracture Net", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#3aff45" },
    { id: "pp_pink_checker_carbon", name: "Pink Checker Carbon", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#ed4fa4" },
    { id: "pp_red_herringbone_heat", name: "Red Herringbone Heat", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#bd181d" },
    { id: "pp_chrome_oval_chain", name: "Chrome Oval Chain", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#d8dce4" },
    { id: "pp_terracotta_ceramic_grid", name: "Terracotta Ceramic Grid", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#9b5d3e" },
    { id: "pp_gunmetal_geo_tessellation", name: "Gunmetal Geo Tessellation", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#74787b" },
    { id: "pp_tokyo_script_textile", name: "Tokyo Script Textile", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#cf302c" },
    { id: "pp_lime_pixel_confetti", name: "Lime Pixel Confetti", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#90d93b" },
    { id: "pp_psychedelic_floral_spin", name: "Psychedelic Floral Spin", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#d37ad6" },
    { id: "pp_ice_facet_shatter", name: "Ice Facet Shatter", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#8fc8ff" },
    { id: "pp_ember_circuit_maze", name: "Ember Circuit Maze", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#ef4b1e" },
    { id: "pp_blue_polygon_shatter", name: "Blue Polygon Shatter", desc: "Real-source pattern plate cropped to 2048 with paired image-derived dynamic spec channels.", swatch: "#2954c6" },
    // Cultural / RISING SUN — image-authored 2048 paint plates with paired dynamic spec maps
    { id: "rs_rising_sun_flare", name: "Rising Sun Flare", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_oni_bloodshift", name: "Oni Bloodshift", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_sakura_storm", name: "Sakura Storm", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_hakuryu_ice", name: "Hakuryu Ice", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_kuro_dragon", name: "Kuro Dragon", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_bamboo_zen", name: "Bamboo Zen", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_temple_gold", name: "Temple Gold", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_geisha_whisper", name: "Geisha Whisper", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_thunder_dragon", name: "Thunder Dragon", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_koi_ascension", name: "Koi Ascension", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_kyoto_lantern", name: "Kyoto Lantern", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_shibuya_pulse", name: "Shibuya Pulse", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_kintsugi_moon", name: "Kintsugi Moon", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_fuji_dawn", name: "Fuji Dawn", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_matcha_ceremony", name: "Matcha Ceremony", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_kabuki_inferno", name: "Kabuki Inferno", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_indigo_tsunami", name: "Indigo Tsunami", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_vermilion_torii", name: "Vermilion Torii", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_crane_garden", name: "Crane Garden", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_sumi_eclipse", name: "Sumi Eclipse", desc: "Japanese-inspired cultural lacquer texture with paired dynamic spec detail.", swatch: "#57576d" },
    { id: "rs_yurei_veil", name: "Yurei Veil", desc: "Pale ghost-silk moonlit lacquer with drifting spirit veils, dark shrine red, and spectral pearl depth.", swatch: "#57576d" },
    { id: "rs_kitsune_ember", name: "Kitsune Ember", desc: "Red-orange fox-fire metallic with shrine shadow, ember motion, and sly golden spec heat.", swatch: "#57576d" },
    { id: "rs_oni_nocturne", name: "Oni Nocturne", desc: "Black-crimson oni mask finish with lacquer smoke, demon-red relief, and night-market menace.", swatch: "#57576d" },
    { id: "rs_gashadokuro_moon", name: "Gashadokuro Moon", desc: "Cold blue moonbone finish with giant skeleton silhouette, misty shrine detail, and icy spectral texture.", swatch: "#57576d" },
    { id: "rs_jorogumo_silk", name: "Jorogumo Silk", desc: "Black silk spider finish with pale gold webwork, hidden kimono warmth, and venomous gloss shimmer.", swatch: "#57576d" },
    { id: "rs_tengu_storm", name: "Tengu Storm", desc: "Electric blue-violet storm finish with tengu wings, lightning fracture, and charged shrine atmosphere.", swatch: "#57576d" },
    { id: "rs_bakeneko_velvet", name: "Bakeneko Velvet", desc: "Purple-black cat-spirit velvet with moon curls, lantern flecks, and mischievous sakura glow.", swatch: "#57576d" },
    { id: "rs_nure_onna_tide", name: "Nure-Onna Tide", desc: "Deep indigo serpent tide finish with moonlit wave scales, cyan foam, and wet mythic movement.", swatch: "#57576d" },
    { id: "rs_hyakki_parade", name: "Hyakki Parade", desc: "Chaotic yokai parade in toxic green, purple lanterns, and black festival lacquer.", swatch: "#57576d" },
    { id: "rs_bell_of_damned", name: "Bell of the Damned", desc: "Dark temple bell finish with blood moon haze, smoky bronze texture, and haunted red accents.", swatch: "#57576d" },
    { id: "rs_sakura_cascade", name: "Sakura Cascade", desc: "Bright pink sakura river over warm gold haze with temple silhouettes and soft pearl flower detail.", swatch: "#57576d" },
    { id: "rs_wisteria_reverie", name: "Wisteria Reverie", desc: "Lavender-blue moon garden pearl with wisteria mist, bridge depth, and cool flake shimmer.", swatch: "#57576d" },
    { id: "rs_lotus_reverie", name: "Lotus Reverie", desc: "Soft aqua lotus pond pearl with watercolor depth, lily pads, and fine green-blue sparkle.", swatch: "#57576d" },
    { id: "rs_peony_festival", name: "Peony Festival", desc: "Hot coral peony festival metallic with lantern warmth, fan detail, and dense floral gloss.", swatch: "#57576d" },
    { id: "rs_iris_rain", name: "Iris Rain", desc: "Cool blue iris garden pearl with rain-silver highlights, temple depth, and violet petal shimmer.", swatch: "#57576d" },
    { id: "rs_camellia_glow", name: "Camellia Glow", desc: "Deep rose camellia lacquer with lantern gold, crimson petal relief, and lush festival sparkle.", swatch: "#57576d" },
    { id: "rs_plum_blossom_dawn", name: "Plum Blossom Dawn", desc: "Peach-pink dawn pearl with plum branches, distant temple, and soft sunlit blossom haze.", swatch: "#57576d" },
    { id: "rs_chrysanthemum_sun", name: "Chrysanthemum Sun", desc: "Radiant yellow-orange chrysanthemum metallic with sunburst petals and warm temple gold.", swatch: "#57576d" },
    { id: "rs_hydrangea_mist", name: "Hydrangea Mist", desc: "Pale blue-white hydrangea mist pearl with soft bridge depth and airy cold-flower shimmer.", swatch: "#57576d" },
    { id: "rs_koi_pond_bloom", name: "Koi Pond Bloom", desc: "Turquoise koi pond finish with lotus pink, orange koi motion, and garden-water sparkle.", swatch: "#57576d" },
    { id: "rs_bosozoku_riot", name: "Bosozoku Riot", desc: "Red rising-sun street-race chrome with black speed stripes, kanji energy, and aggressive metallic grit.", swatch: "#57576d" },
    { id: "rs_wangan_midnight_pulse", name: "Wangan Midnight Pulse", desc: "Neon purple-blue highway pulse with Japanese street grid, star flake, and high-speed gloss.", swatch: "#57576d" },
    { id: "rs_touge_apex", name: "Touge Apex", desc: "Black graphite touge finish with silver mountain-road linework and stealth carbon sparkle.", swatch: "#57576d" },
    { id: "rs_drift_hanami_oversteer", name: "Drift Hanami Oversteer", desc: "Pink-black drift spiral with sakura petals, smoke curves, and oversteer gloss movement.", swatch: "#57576d" },
    { id: "rs_kaido_chrome_bloom", name: "Kaido Chrome Bloom", desc: "Red-silver kaido racer chrome with rising-sun bloom, sakura lanes, and deep flake paneling.", swatch: "#57576d" },
    { id: "rs_dekotora_electric_freight", name: "Dekotora Electric Freight", desc: "Electric freight-truck neon finish with blue-magenta panels, chrome light bars, and festival glow.", swatch: "#57576d" },
    { id: "rs_time_attack_grid_shock", name: "Time Attack Grid Shock", desc: "Black-red time-attack grid with Fuji strike, speedline texture, and hot digital spec pulses.", swatch: "#57576d" },
    { id: "rs_akane_flake_fog", name: "Akane Flake Fog", desc: "Deep red akane microflake haze with dark lacquer scratches and ember-glow metallic depth.", swatch: "#57576d" },
    { id: "rs_kurogane_rain", name: "Kurogane Rain", desc: "Blackened steel rain texture with blue-red streaks, wet abrasion, and moody lacquer depth.", swatch: "#57576d" },
    { id: "rs_kinpaku_blaze", name: "Kinpaku Blaze", desc: "Gold-leaf blaze field with orange copper grain, hot metallic flecks, and layered foil texture.", swatch: "#57576d" },
    { id: "rs_ryokucha_scroll", name: "Ryokucha Scroll", desc: "Dark green tea-lacquer scrollwork with emerald flake pockets and carved metallic currents.", swatch: "#57576d" },
    { id: "rs_mikan_pearl", name: "Mikan Pearl", desc: "Mikan orange pearl fade with coral-gold shimmer, soft flake texture, and warm candy depth.", swatch: "#57576d" },

    // Cultural / VIVA MEXICO — cleaned image-authored 2048 paint plates with paired dynamic spec maps
    // Cultural / FORBIDDEN DRAGON — dense imperial dragon brocades; spec traced from the art at render time (gold->metal, scales/clouds/flames -> decorrelated M/R/Cc). See engine/paint_v2/cultural_forbidden_dragon.py.
    { id: "fd_azure_celestial", name: "Azure Celestial", desc: "Cobalt-and-silver imperial dragon brocade — sky dragons, clouds and scales in gold linework; spec traced from the art for a shimmering scale-and-cloud reveal.", swatch: "#2a52be" },
    { id: "fd_vermilion_fire", name: "Vermilion Fire", desc: "Crimson-and-gold dragon brocade with curling flame fields; the fire motifs trace into glossy cut-outs that breathe under sun.", swatch: "#e3431f" },
    { id: "fd_abyssal_sea", name: "Abyssal Sea", desc: "Jade-and-aqua sea-dragon brocade with foam crests; wave and scale motifs gate the angle reveal.", swatch: "#1f7a6b" },
    { id: "fd_imperial_gold", name: "Imperial Gold", desc: "Radiant gold-on-lacquer dragon-scale damask; gold linework reads as metal, lacquer cells as glossy clearcoat.", swatch: "#d4af37" },
    { id: "fd_storm_black", name: "Storm Black", desc: "Black-and-silver storm-dragon brocade with lightning forks; moody dark ground laced with electric metal veins.", swatch: "#2c3e50" },
    { id: "fd_jade_empress", name: "Jade Empress", desc: "Carved-jade dragon brocade — translucent greens with white relief and gold; sculpted scale field.", swatch: "#2e8b57" },
    { id: "fd_frost_emperor", name: "Frost Emperor", desc: "Ice-white and glacier-blue dragon brocade with snowflake and frost-fern motifs; crisp cool reveal.", swatch: "#9fd3e0" },
    { id: "fd_bronze_relic", name: "Bronze Relic", desc: "Antique bronze and verdigris dragon-coin brocade; aged-treasure patina with gold-leaf relief.", swatch: "#8c6a3f" },
    { id: "fd_pearl_chaser", name: "Pearl Chaser", desc: "Red-and-gold dragons chasing flaming pearls; the pearls trace into glowing focal gems scattered across the body.", swatch: "#c8102e" },
    { id: "fd_dragon_phoenix", name: "Dragon & Phoenix", desc: "Interlocking dragon-and-phoenix medallion brocade in cobalt, crimson and gold; balanced duo reveal.", swatch: "#b5432f" },
    { id: "fd_phoenix_fenghuang", name: "Phoenix Fenghuang", desc: "Crimson-orange-and-teal phoenix brocade — sweeping eye-spot tail-feathers fanning every direction; gold linework on a dark ground.", swatch: "#d4502a" },
    { id: "fd_jade_qilin", name: "Jade Qilin", desc: "Jade-and-gold qilin brocade — scaled unicorn-beasts and cloud scrolls in all orientations; auspicious omnidirectional weave.", swatch: "#2e8b57" },
    { id: "fd_guardian_foo_lion", name: "Guardian Foo Lion", desc: "Imperial-red-and-gold temple-lion brocade — curly-maned foo dogs with coins and knots; ivory highlights flash as pearl.", swatch: "#b8252b" },
    { id: "fd_vermilion_bird", name: "Vermilion Bird", desc: "Vermilion-and-flame-gold southern-phoenix brocade with ember motifs; fiery birds turning every way under sun.", swatch: "#e0401e" },
    { id: "fd_black_tortoise", name: "Black Tortoise", desc: "Black-jade-and-silver Xuanwu brocade — tortoise shells and serpents with water scrolls; deep moody ground.", swatch: "#20413a" },
    { id: "fd_white_tiger_baihu", name: "White Tiger Baihu", desc: "White-silver-and-gold Bai Hu brocade — black-striped tigers prowling all directions with wind curls and coins.", swatch: "#c9a84a" },
    { id: "fd_crane_garden", name: "Crane Garden", desc: "Pale-jade crane-garden brocade — red-crowned cranes, pine, lotus and peony; light airy ground for a softer reveal.", swatch: "#9cc5a1" },
    { id: "fd_koi_ascension", name: "Koi Ascension", desc: "Cobalt-and-gold koi brocade — orange-and-white carp swimming every way over foam swirls and coins.", swatch: "#1b3fa0" },
    { id: "fd_pixiu_fortune", name: "Pixiu Fortune", desc: "Antique-gold-and-jade Pixiu brocade — winged wealth-beasts amid coin showers; gold reads as metal, jade as gloss.", swatch: "#b8860b" },
    { id: "fd_golden_toad_jinchan", name: "Golden Toad Jinchan", desc: "Gold-on-lucky-red money-toad brocade — three-legged Jin Chan with coin strings and lotus; opulent prosperity weave.", swatch: "#c8881f" },
    // === LET FREEDOM RING FINISHES 2026-06-09 START === (fully procedural — zero image plates)
    { id: "lfr_old_glory_flux", name: "Old Glory Flux", desc: "Deep navy lacquer dusted with red-and-white star-flecks under a multi-directional color-shift sheen that travels red-white-blue as the car turns.", swatch: "#1b2a5e" },
    { id: "lfr_rockets_red_glare", name: "Rockets Red Glare", desc: "Firework bursts of concentric red and gold rings on a near-black night field — the sparks flare mirror-bright only when light rakes the panel.", swatch: "#3a0d18" },
    { id: "lfr_liberty_torch", name: "Liberty Torch", desc: "Omnidirectional licking flame tongues in red, orange and gold over ember-black — wrapped torch heat that glows hotter at the tips in clearcoat.", swatch: "#c2491b" },
    { id: "lfr_eagle_ascendant", name: "Eagle Ascendant", desc: "Dense gold-on-navy brocade of scattered feather and wing motifs at every angle — imperial eagle damask that catches gilt light from any direction.", swatch: "#22305e" },
    { id: "lfr_we_the_people", name: "We The People", desc: "Aged parchment cross-hatched with an engraved banknote guilloche — debossed ink lines in every direction with a low scholarly sheen.", swatch: "#d8c9a3" },
    { id: "lfr_midnight_militia", name: "Midnight Militia", desc: "Tactical matte multicam in muted navy, slate and olive blotches with fine deep grain — dead-flat, light-eating stealth patriot camo.", swatch: "#2c3440" },
    { id: "lfr_freedom_forge", name: "Freedom Forge", desc: "Molten steel mid-pour — glowing orange cracks web across cooling gunmetal cells with white-hot sparks, the cracks blazing in clearcoat.", swatch: "#3a3f46" },
    { id: "lfr_amber_waves", name: "Amber Waves", desc: "Rippling wheat-gold grain bending under crossing winds — soft sheen-corridors roll across the gold like sun on a prairie.", swatch: "#d9a93f" },
    { id: "lfr_glory_chrome", name: "Glory Chrome", desc: "Liquid show-chrome brushed in crossing directions and dusted with red, white and blue mirror flecks — a polished patriot mirror.", swatch: "#c9ced8" },
    { id: "lfr_sparkler_dusk", name: "Sparkler Dusk", desc: "Dusk-purple twilight scattered with comet-spark micro-flake — tapered spark streaks at every angle, each tipped with a twinkling white-hot flake.", swatch: "#3c2a5e" },
    // === LET FREEDOM RING FINISHES 2026-06-09 END ===
    // === FABLE FINISHES 2026-06-09 START === (color-science flagship set — fully procedural)
    { id: "fable_ember_glass", name: "Ember Glass", desc: "Blood-orange candy laid over coarse silver flake, shattered by a crackle relief: the coat burns thin and fiery on every plateau and pools deep crimson-black in the crack valleys. Under track lights the crack web glows wet while flake glints spark across the faces.", swatch: "#b3441a" },
    { id: "fable_glacier_core", name: "Glacier Core", desc: "Crushed-ice facets locked under arctic cyan candy: every angular shard tips its own way, the coat staying thin and bright on the faces while the fissures between shards flood deep sapphire. Edge glints flash along the shard lines like sun on broken ice.", swatch: "#2e8fb8" },
    { id: "fable_abyss_lantern", name: "Abyss Lantern", desc: "A near-black deep-sea teal so thick the metal barely survives the dive - until light rakes across it and hidden lantern cells bloom out of the clearcoat like bioluminescence. Head-on it is abyss; at an angle the car is alive.", swatch: "#06282c" },
    { id: "fable_stained_aurora", name: "Stained Aurora", desc: "A leaded stained-glass window poured over silver leaf: every flow-warped pane is its own jewel - ruby, amber, emerald, sapphire, violet - in deep candy glass that pools darker toward its lead border. Hand-rolled ripple catches the light inside each pane.", swatch: "#7a3fa0" },
    { id: "fable_prism_veil", name: "Prism Veil", desc: "Banded thin-film interference orders drift like a torn veil over a near-black cherry base - amber, magenta and violet plateaus split by prismatic shimmer, with the order edges flaring under direct light.", swatch: "#4a1428" },
    { id: "fable_oilforge", name: "Oilforge", desc: "Oil-slick rings bloom in quantized Newton bands around scattered heat spots on brushed gunmetal - the brush grain changes direction patch to patch, and the ring crests flare while the heat centers pool with wet gloss.", swatch: "#56606c" },
    { id: "fable_tempered_dawn", name: "Tempered Dawn", desc: "Titanium weld-temper: straw, bronze, violet and blue heat bands trace curling weld paths across raw brushed metal, and the bead line itself flares like fresh chrome under direct light.", swatch: "#b08a3c" },
    { id: "fable_pulse_alloy", name: "Pulse Alloy", desc: "Concentric pulses ripple out from scattered impact points, every ring order snapping to a different hue - teal, violet, magenta, gold - before fading into brushed alloy with a soft pooled glow.", swatch: "#8a4a2c" },
    { id: "fable_velvet_eclipse", name: "Velvet Eclipse", desc: "Deep indigo velvet shot through with a molten-gold micro lattice — head-on it reads midnight, raking sun sets the gold pools on fire while eclipse coronas glow in the clearcoat.", swatch: "#1c1c4e" },
    { id: "fable_wovenlight", name: "Wovenlight", desc: "An over/under ribbon weave of emerald satin and royal-violet mirror that flips color as the car turns — dive shadows give the basket real depth and light pools diagonally across the weave.", swatch: "#1e6e4e" },
    { id: "fable_sovereign_flip", name: "Sovereign Flip", desc: "Three paints in one: matte oxblood, mirror champagne and glass-deep emerald candy split the body into fine inked territories — every sun angle shows you a different car.", swatch: "#5e1e26" },
    { id: "fable_static_bloom", name: "Static Bloom", desc: "Electric-cobalt micro-static, magenta filament streaks and amber soft blooms each claim their own territory, their own hue family and their own light behavior — a triple-personality finish.", swatch: "#4e3a8e" },
    { id: "fable_aurora_travel", name: "Aurora Travel", desc: "An aurora curtain that physically travels: glossy corridors cut across the teal-violet-magenta flow, so the live highlight slides through different hues as the car rotates, while curtain-edge filaments flare icy white under direct light.", swatch: "#2a6e8e" },
    { id: "fable_saffron_circuit", name: "Saffron Circuit", desc: "Etched micro-circuitry in saffron, rose and ember: trace density steers the hue, the grooves polish glossy and pool dark candy, and every via dot glows wet under the clear.", swatch: "#d08a2a" },
    { id: "fable_quicksilver_garden", name: "Quicksilver Garden", desc: "Liquid chrome overgrown with a garden of pastel cells — every cell grows its own mini color ramp in its own direction behind a mirror-bright rim, and each cell flares at its own angle as you drive.", swatch: "#c8ccd4" },
    { id: "fable_emberline_drift", name: "Emberline Drift", desc: "Folded dune ridges drift from gold through crimson into smoke; satin sheen lanes cross the dunes at their own angles while embers pool and glow in the clearcoat between the crests.", swatch: "#b86a2a" },
    { id: "fable_duomorph", name: "Duomorph", desc: "Two hidden artworks on one car: orbital glyph rosettes flare in the metallic under direct sun, while sweeping ribbon arcs glow out of the clearcoat at glancing angles — the deep graphite paint only whispers both until the light picks a side.", swatch: "#2c2c34" },
    { id: "fable_nightbloom", name: "Nightbloom", desc: "Dusk indigo melting into plum, seeded from scattered night-sky anchors — and when low sun rakes the clearcoat, luminous petal-fan blooms open across the car that the paint itself only hints at.", swatch: "#2c1e4e" },
    { id: "fable_magnetite_flow", name: "Magnetite Flow", desc: "Ferrofluid spike colonies frozen mid-pulse on wet black: the coat pools deep blue-black between the spikes and thins to bright steel at every crest, and only the spike tips spark when the sun hits them dead-on.", swatch: "#14161c" },
    { id: "fable_comet_parade", name: "Comet Parade", desc: "A deep-space violet-to-teal field crossed by three separate comet swarms — heads spark in direct light, long wakes drag bright and dark gloss lanes across the panels, and bow-shock crescents glow out of the clearcoat at low sun.", swatch: "#241a44" },
    // === FABLE FINISHES 2026-06-09 END ===
    { id: "vm_aztec_sunfire", name: "Aztec Sunfire", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#923514" },
    { id: "vm_talavera_azul", name: "Talavera Azul", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#434e6e" },
    { id: "vm_quetzal_sunset", name: "Quetzal Sunset", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#8a4939" },
    { id: "vm_sacred_heart_eclipse", name: "Sacred Heart Eclipse", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#5a382d" },
    { id: "vm_guadalupe_lowrider", name: "Guadalupe Lowrider", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#51312a" },
    { id: "vm_rosa_corazon", name: "Rosa Corazon", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#742c47" },
    { id: "vm_mariachi_verde", name: "Mariachi Verde", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#5b4d2d" },
    { id: "vm_calavera_violeta", name: "Calavera Violeta", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#4e3c57" },
    { id: "vm_serape_sunburst", name: "Serape Sunburst", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#7c3917" },
    { id: "vm_riviera_lowrider", name: "Riviera Lowrider", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#394f7a" },
    { id: "vm_luchador_plata", name: "Luchador Plata", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#604d45" },
    { id: "vm_luchador_rayo", name: "Luchador Rayo", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#3f4452" },
    { id: "vm_cactus_sunset", name: "Cactus Sunset", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#871511" },
    { id: "vm_sierra_verde", name: "Sierra Verde", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#446c44" },
    { id: "vm_cenote_lace", name: "Cenote Lace", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#337d8b" },
    { id: "vm_agave_pearl", name: "Agave Pearl", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#3f715d" },
    { id: "vm_baja_horizon", name: "Baja Horizon", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#9a5c40" },
    { id: "vm_pacific_coast_dawn", name: "Pacific Coast Dawn", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#947f7c" },
    { id: "vm_copper_canyon", name: "Copper Canyon", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#8c6120" },
    { id: "vm_sierra_niebla", name: "Sierra Niebla", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#909aa6" },
    { id: "vm_oaxaca_moonwater", name: "Oaxaca Moonwater", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#1d2b45" },
    { id: "vm_xolo_candy_desert", name: "Xolo Candy Desert", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#c3714f" },
    { id: "vm_huichol_beadwork", name: "Huichol Beadwork", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#5c443d" },
    { id: "vm_sonora_blue_calavera", name: "Sonora Blue Calavera", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#5c6574" },
    { id: "vm_bajio_gold_calaveras", name: "Bajio Gold Calaveras", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#5d5037" },
    { id: "vm_lucha_rosa", name: "Lucha Rosa", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#78474f" },
    { id: "vm_desert_marigold", name: "Desert Marigold", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#624a30" },
    { id: "vm_zapata_jade", name: "Zapata Jade", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#535b46" },
    { id: "vm_cinco_spark", name: "Cinco Spark", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#585872" },
    { id: "vm_mezcal_smoke", name: "Mezcal Smoke", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#595387" },
    { id: "vm_riviera_corazon", name: "Riviera Corazon", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#614334" },
    { id: "vm_noche_buena", name: "Noche Buena", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#694a3e" },
    { id: "vm_rosario_gold", name: "Rosario Gold", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#7d3d21" },
    { id: "vm_pyramid_shadow", name: "Pyramid Shadow", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#68331a" },
    { id: "vm_fiesta_chrome", name: "Fiesta Chrome", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#602915" },
    { id: "vm_maguey_pearl", name: "Maguey Pearl", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#6d2d18" },
    { id: "vm_cantina_neon", name: "Cantina Neon", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#8b2f28" },
    { id: "vm_azulejo_storm", name: "Azulejo Storm", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#714120" },
    { id: "vm_calavera_royal", name: "Calavera Royal", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#7e3b17" },
    { id: "vm_talavera_muertos", name: "Talavera Muertos", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#7a695a" },
    { id: "vm_tulum_candelaria", name: "Tulum Candelaria", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#80411d" },
    { id: "vm_eclipse_ofrenda", name: "Eclipse Ofrenda", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#673524" },
    { id: "vm_charro_nocturne", name: "Charro Nocturne", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#37535e" },
    { id: "vm_cempasuchil_noir", name: "Cempasuchil Noir", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#453f3a" },
    { id: "vm_sierra_madre", name: "Sierra Madre", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#4b6053" },
    { id: "vm_mole_negro", name: "Mole Negro", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#65483c" },
    { id: "vm_veracruz_carnival", name: "Veracruz Carnival", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#803e23" },
    { id: "vm_jalisco_flash", name: "Jalisco Flash", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#565964" },
    { id: "vm_mosaic_jaguar", name: "Mosaic Jaguar", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#452e1e" },
    { id: "vm_milagro_silver", name: "Milagro Silver", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#532015" },
    { id: "vm_sacred_cenote", name: "Sacred Cenote", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#3e3027" },
    { id: "vm_playa_dorada", name: "Playa Dorada", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#c49a77" },
    { id: "vm_adobe_sunset", name: "Adobe Sunset", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#7a563c" },
    { id: "vm_zapotec_thunder", name: "Zapotec Thunder", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#956b3b" },
    { id: "vm_nopal_bloom", name: "Nopal Bloom", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#ab6832" },
    { id: "vm_mayan_jade", name: "Mayan Jade", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#895c21" },
    { id: "vm_neon_cantina", name: "Neon Cantina", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#5b3b65" },
    { id: "vm_baja_cartografia", name: "Baja Cartografia", desc: "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired high-detail spec map depth.", swatch: "#998260" },

    // Material World / GRUNGE & FUN - image-authored 2048 plates + matched dynamic spec maps
    { id: "gf_x_1024293_6391", name: "Blacktop Neon Rain", desc: "Blacktop Neon Rain is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #neon, #rain, #blacktop, #dots.", swatch: "#38513a" },
    { id: "gf_x_1024294_6392", name: "Electric Green Scanline", desc: "Electric Green Scanline is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #scanline, #green, #glitch, #digital.", swatch: "#455923" },
    { id: "gf_x_1152842_or6ilf0", name: "Midnight Blue Mesh", desc: "Midnight Blue Mesh is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #blue, #mesh, #halftone, #depth.", swatch: "#161e82" },
    { id: "gf_x_1195794_6247", name: "Broken Glass Mosaic", desc: "Broken Glass Mosaic is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #punk-checker, #mosaic, #glass, #black-white, #cells.", swatch: "#797977" },
    { id: "gf_x_1292", name: "Golden Circuit Lace", desc: "Golden Circuit Lace is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #disco-glitter, #gold, #circuit, #lace, #ornate.", swatch: "#edb013" },
    { id: "gf_x_13845", name: "Rainbow Audio Shockwave", desc: "Rainbow Audio Shockwave is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #rainbow, #wave, #audio, #neon.", swatch: "#722b49" },
    { id: "gf_x_1434947_595", name: "Sunburst Polygon Pop", desc: "Sunburst Polygon Pop is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #comic-pop, #yellow, #polygon, #sunburst, #pop.", swatch: "#fed80d" },
    { id: "gf_x_16302407_yellow_hexagon_halftone_pattern_backg", name: "Hazard Honeycomb Glow", desc: "Hazard Honeycomb Glow is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #yellow, #honeycomb, #hex, #halftone.", swatch: "#fec303" },
    { id: "gf_x_18677", name: "Matrix Asphalt Rain", desc: "Matrix Asphalt Rain is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #matrix, #green, #rain, #asphalt.", swatch: "#203724" },
    { id: "gf_x_18914258_casino_2021_11", name: "Lucky Dice Blackout", desc: "Lucky Dice Blackout is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #casino, #dice, #cards, #black.", swatch: "#655d3e" },
    { id: "gf_x_19034947_en9y_pjge_210709", name: "Gilded Mermaid Scales", desc: "Gilded Mermaid Scales is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #metal-flake, #scales, #gold, #white, #mermaid.", swatch: "#e0d4a8" },
    { id: "gf_x_19516529_casino_2021_17", name: "Vegas Chip Nightfall", desc: "Vegas Chip Nightfall is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #casino, #chips, #dots, #night.", swatch: "#5a4b2e" },
    { id: "gf_x_20216645_6276400", name: "Bronze Maze Circuit", desc: "Bronze Maze Circuit is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #metal-flake, #bronze, #maze, #circuit, #geometric.", swatch: "#57462e" },
    { id: "gf_x_20771417_v6t9_6fpy_210512", name: "Blue Koi Scale Pop", desc: "Blue Koi Scale Pop is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #blue, #scales, #koi, #pop.", swatch: "#9fbdcf" },
    { id: "gf_x_2149635369", name: "Molten Mustard Marble", desc: "Molten Mustard Marble is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #worn-rust, #marble, #molten, #red, #yellow.", swatch: "#a75416" },
    { id: "gf_x_22587040_6656535", name: "Monochrome Pixel Snow", desc: "Monochrome Pixel Snow is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #pixel, #snow, #black-white, #static.", swatch: "#858585" },
    { id: "gf_x_22587046_6656517", name: "Silver Pixel Gravel", desc: "Silver Pixel Gravel is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #pixel, #gravel, #silver, #static.", swatch: "#afafaf" },
    { id: "gf_x_2311", name: "Cotton Candy Halftone Fade", desc: "Cotton Candy Halftone Fade is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #gradient, #pastel, #halftone, #fade.", swatch: "#e7b8f2" },
    { id: "gf_x_237560942_1f15d9a7_672f_4b74_9792_9a0daae8fbe2", name: "Red Checker Burnout", desc: "Red Checker Burnout is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #punk-checker, #checker, #red, #burnout, #punk.", swatch: "#7c100a" },
    { id: "gf_x_2425", name: "Purple Reptile Circuit", desc: "Purple Reptile Circuit is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #purple, #scale, #reptile, #circuit.", swatch: "#6e60d3" },
    { id: "gf_x_2474", name: "Lava Honeycomb Split", desc: "Lava Honeycomb Split is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #lava, #honeycomb, #yellow, #red.", swatch: "#c64816" },
    { id: "gf_x_26323837_blue_hexagon_pattern_background", name: "Blue Honeycomb Haze", desc: "Blue Honeycomb Haze is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #blue, #honeycomb, #hex, #soft.", swatch: "#08aef7" },
    { id: "gf_x_283511752_c9a714fc_a791_4c92_a2af_e3b8537ecaef", name: "Deep Blue Dot Fade", desc: "Deep Blue Dot Fade is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #blue, #dots, #halftone, #fade.", swatch: "#003c7c" },
    { id: "gf_x_29035", name: "Torn Poster Static", desc: "Torn Poster Static is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #poster, #torn, #orange, #static.", swatch: "#c8775c" },
    { id: "gf_x_30330639_lightabstrback14gradientd", name: "Rainbow Hex Tunnel", desc: "Rainbow Hex Tunnel is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #rainbow, #hex, #tunnel, #optical.", swatch: "#257324" },
    { id: "gf_x_31587230_7837300", name: "Warped Arcade Checker", desc: "Warped Arcade Checker is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #punk-checker, #checker, #arcade, #warp, #purple.", swatch: "#8e6685" },
    { id: "gf_x_3521", name: "Electric Scribble Storm", desc: "Electric Scribble Storm is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #electric, #scribble, #storm, #neon.", swatch: "#235e9e" },
    { id: "gf_x_391161788_673b312d_2817_44f1_bfa5_bc51bf8df42d", name: "Peach Stone Scuff", desc: "Peach Stone Scuff is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #worn-rust, #peach, #stone, #scuff, #weathered.", swatch: "#fea38d" },
    { id: "gf_x_3946420_524", name: "Python Scale Armor", desc: "Python Scale Armor is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #metal-flake, #python, #scale, #armor, #brown.", swatch: "#9c8970" },
    { id: "gf_x_4004", name: "Solar Mesh Fade", desc: "Solar Mesh Fade is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #solar, #mesh, #gradient, #green.", swatch: "#bcb863" },
    { id: "gf_x_417665166_62a76dd6_56af_4a68_b801_92f5967beda0", name: "Black White Decay Wall", desc: "Black White Decay Wall is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #decay, #wall, #black-white, #scratch.", swatch: "#7a7a7a" },
    { id: "gf_x_420841114_17c7c800_04f4_4c25_8844_09134f10d3a7", name: "Frosted Vertical Smear", desc: "Frosted Vertical Smear is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #frost, #vertical, #smear, #silver.", swatch: "#868e96" },
    { id: "gf_x_426098859_bfe8ddbc_e982_4a17_b396_d362c3e1e12f", name: "Redline Audio Pulse", desc: "Redline Audio Pulse is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #red, #audio, #pulse, #wave.", swatch: "#e41e00" },
    { id: "gf_x_426203826_fc914006_6101_4668_8c1d_3322a73a9319", name: "Rainbow Sonar Sweep", desc: "Rainbow Sonar Sweep is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #casino-neon, #rainbow, #sonar, #wave, #sweep.", swatch: "#af4300" },
    { id: "gf_x_6090", name: "Sunset Mesh Burst", desc: "Sunset Mesh Burst is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #sunset, #mesh, #orange, #red.", swatch: "#b9692b" },
    { id: "gf_x_6113", name: "Toxic Green Mesh Fade", desc: "Toxic Green Mesh Fade is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #green, #toxic, #mesh, #fade.", swatch: "#8c9f4a" },
    { id: "gf_x_69", name: "Blue Digital Drizzle", desc: "Blue Digital Drizzle is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #blue, #digital, #drizzle, #rain.", swatch: "#0f414b" },
    { id: "gf_x_819188_26851_nwdlx0", name: "Champagne Bubble Grid", desc: "Champagne Bubble Grid is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #disco-glitter, #champagne, #bubbles, #grid, #dots.", swatch: "#988650" },
    { id: "gf_x_850287_o4yijt0", name: "Carnival Dot Burst", desc: "Carnival Dot Burst is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #disco-glitter, #carnival, #dots, #burst, #red.", swatch: "#a05457" },
    { id: "gf_x_850288_o4yijy0", name: "Blue Starburst Marquee", desc: "Blue Starburst Marquee is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #disco-glitter, #blue, #starburst, #marquee, #dots.", swatch: "#3ea0b6" },
    { id: "gf_x_8514125_3910277", name: "Magenta Static Weave", desc: "Magenta Static Weave is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #magenta, #static, #weave, #noise.", swatch: "#4f4183" },
    { id: "gf_x_9121", name: "Toxic Diagonal Beam", desc: "Toxic Diagonal Beam is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #toxic, #diagonal, #beam, #green.", swatch: "#94d402" },
    { id: "gf_x_9169", name: "Cherry Sunrise Halftone", desc: "Cherry Sunrise Halftone is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #acid-wash, #cherry, #sunrise, #halftone, #orange.", swatch: "#e43f02" },
    { id: "gf_x_9338", name: "Purple Blue Dot Mesh", desc: "Purple Blue Dot Mesh is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #halftone-hex, #purple, #blue, #dots, #mesh.", swatch: "#6f3aa8" },
    { id: "gf_x_946728_oe3t1y0", name: "Blacklight Wireframe", desc: "Blacklight Wireframe is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #punk-checker, #blacklight, #wireframe, #grid, #neon.", swatch: "#2c282f" },
    { id: "gf_x_947419_oe46fw0", name: "Prism Triangle Confetti", desc: "Prism Triangle Confetti is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #comic-pop, #prism, #triangle, #confetti, #rainbow.", swatch: "#5f8db0" },
    { id: "gf_x_9819736_12811_1", name: "Dry Brush Carbon Scratch", desc: "Dry Brush Carbon Scratch is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #grunge-scratch, #scratch, #carbon, #dry-brush, #black-white.", swatch: "#4d4d4d" },
    { id: "gf_magnific_digital_illustration_a_dark_background_", name: "Radiant Dark Matter Burst", desc: "Radiant Dark Matter Burst is a Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, and gradients. Search tags: #grunge, #fun, #dynamic-spec, #abstract-gradient, #radiant, #dark, #burst, #halftone.", swatch: "#352b24" },

    // Cultural / UNION JACKED — cleaned 2048 plates; procedural relief-rich M/R/Cc spec (see cultural_union_jacked.py); DNA-polished like Viva Mexico.
    { id: "uj_camden_signal_riot", name: "Camden Signal Riot", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#3a2c2d" },
    { id: "uj_thames_after_dark", name: "Thames After Dark", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#14263a" },
    { id: "uj_chelsea_razor_parade", name: "Chelsea Razor Parade", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#392b26" },
    { id: "uj_kings_cross_mercury", name: "King's Cross Mercury", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#1d1818" },
    { id: "uj_covent_garden_static", name: "Covent Garden Static", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#2b241f" },
    { id: "uj_oxford_circus_chrome", name: "Oxford Circus Chrome", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#2f292f" },
    { id: "uj_piccadilly_rain_stance", name: "Piccadilly Rain Stance", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#806661" },
    { id: "uj_brick_lane_voltage", name: "Brick Lane Voltage", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#526877" },
    { id: "uj_notting_carnival_glass", name: "Notting Carnival Glass", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#925d5c" },
    { id: "uj_beat_burst", name: "Beat Burst", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#786f8f" },
    { id: "uj_highland_heather_haze", name: "Highland Heather Haze", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#6e697f" },
    { id: "uj_portobello_pearl_riot", name: "Portobello Pearl Riot", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#a09c6b" },
    { id: "uj_liverpool_echo_lace", name: "Liverpool Echo Lace", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#456d76" },
    { id: "uj_manchester_acid_union", name: "Manchester Acid Union", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#c8ccce" },
    { id: "uj_glasgow_granite_soul", name: "Glasgow Granite Soul", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#a78c74" },
    { id: "uj_belfast_harp_storm", name: "Belfast Harp Storm", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#2a4740" },
    { id: "uj_edinburgh_castle_frost", name: "Edinburgh Castle Frost", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#131520" },
    { id: "uj_welsh_dragon_lacquer", name: "Welsh Dragon Lacquer", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#677d8e" },
    { id: "uj_cornwall_sea_spark", name: "Cornwall Sea Spark", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#302c40" },
    { id: "uj_dover_white_cliff_pearl", name: "Dover White Cliff Pearl", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#758885" },
    { id: "uj_brighton_pier_neon", name: "Brighton Pier Neon", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#6b7687" },
    { id: "uj_southampton_dock_matte", name: "Southampton Dock Matte", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#294645" },
    { id: "uj_silverstone_apex_flare", name: "Silverstone Apex Flare", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#30373d" },
    { id: "uj_goodwood_heritage_flake", name: "Goodwood Heritage Flake", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#30373d" },
    { id: "uj_isle_of_man_tt_chrome", name: "Isle of Man TT Chrome", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#242d34" },
    { id: "uj_ulster_rally_tartan", name: "Ulster Rally Tartan", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#221d17" },
    { id: "uj_highland_fling_metal", name: "Highland Fling Metal", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#4f5b6c" },
    { id: "uj_loch_ness_deep_void", name: "Loch Ness Deep Void", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#24272f" },
    { id: "uj_midnight_hearse_baroque", name: "Midnight Hearse Baroque", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#181718" },
    { id: "uj_tudor_rose_filigree", name: "Tudor Rose Filigree", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#1b203c" },
    { id: "uj_windsor_guard_gloss", name: "Windsor Guard Gloss", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#23396e" },
    { id: "uj_shard_glass_rain", name: "Shard Glass Rain", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#262d28" },
    { id: "uj_gherkin_twist_metal", name: "Gherkin Twist Metal", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#262b33" },
    { id: "uj_black_cab_nocturne", name: "Black Cab Nocturne", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#2b4b62" },
    { id: "uj_red_bus_velocity", name: "Red Bus Velocity", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#322c24" },
    { id: "uj_routemaster_candy", name: "Routemaster Candy", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#352717" },
    { id: "uj_mini_cooper_flip", name: "Mini Cooper Flip", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#2b1813" },
    { id: "uj_aston_strait_silver", name: "Aston Strait Silver", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#5a6877" },
    { id: "uj_bentley_brooklands_mist", name: "Bentley Brooklands Mist", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#576f9e" },
    { id: "uj_rolls_phantom_veil", name: "Rolls Phantom Veil", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#434362" },
    { id: "uj_lotus_elan_streak", name: "Lotus Elan Streak", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#654644" },
    { id: "uj_mclaren_papaya_strike", name: "McLaren Papaya Strike", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#382b2c" },
    { id: "uj_williams_fw_blueblood", name: "Williams FW Blueblood", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#7a606d" },
    { id: "uj_jaguar_etype_silk", name: "Jaguar E-Type Silk", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec.", swatch: "#4c2f32" },
    { id: "uj_blueblood_beatline", name: "Blueblood Beatline", desc: "Union Jacked cultural lacquer — poster artwork with relief-sculpted procedural M/R/Cc spec. Chromatic-shift spec layer for view-dependent colour travel.", swatch: "#6b555a" },

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
    { id: "cx_custom_shift", name: "CX Prism Reactor Shift", desc: "Fixed deep-ink and magenta prism reactor finish. The old pick-any-two-color feature was removed; this is now a curated COLORSHOXX finish.", swatch: "conic-gradient(from 0deg, #10142e, #f214a8, #6447ff, #10142e)" },
    { id: "cx_pink_to_gold", name: "CX Pink Gold Abstract Shift", desc: "Hot pink and rich gold trade dominance through abstract liquid islands across the whole canvas. No stripes, no single candy-band roll.", swatch: "linear-gradient(135deg, #FF3388 0%, #FFD926 100%)" },
    { id: "cx_blue_to_orange", name: "CX Blue Orange Abstract Shift", desc: "Cobalt and ember roll back and forth in broken abstract currents, giving several color-shift reversals instead of one hard split.", swatch: "linear-gradient(135deg, #1A4DE6 0%, #FF800D 100%)" },
    { id: "cx_purple_to_green", name: "CX Purple Green Abstract Shift", desc: "Royal purple and electric green alternate through abstract jewel pools and contour eddies with lively spec-map contrast.", swatch: "linear-gradient(135deg, #991ACC 0%, #1AE64D 100%)" },
    { id: "cx_teal_to_magenta", name: "CX Teal Magenta Abstract Shift", desc: "Teal and magenta pulse through abstract plasma eddies with several back-and-forth reversals across the panel.", swatch: "linear-gradient(135deg, #00CCB3 0%, #E61A80 100%)" },
    { id: "cx_red_to_cyan", name: "CX Red Cyan Abstract Shift", desc: "Fire red and ice cyan snap through abstract cellular wakes instead of stripe rails or candy-cane bands.", swatch: "linear-gradient(135deg, #E61A1A 0%, #1AE6E6 100%)" },
    { id: "cx_sunset_shift", name: "CX Sunset Shift", desc: "Broad warm-to-cool sweep tuned like late sun falling into plum shadow. Softer and more atmospheric than the aggressive duo flips.", swatch: "linear-gradient(135deg, #FF4D00 0%, #990066 100%)" },
    { id: "cx_emerald_ruby", name: "CX Emerald → Ruby Shift", desc: "Jewel-tone arc shift with darker mids — emerald face, ruby edge, and a richer luxury transition than the louder complementary duos.", swatch: "linear-gradient(135deg, #00B34D 0%, #CC0D26 100%)" },
    { id: "cx_ice_fire", name: "CX Ice Fire Abstract Shift", desc: "Frozen blue and ember orange chase each other through abstract thermal islands with lively, varied spec channels.", swatch: "linear-gradient(135deg, #B3D9FF 0%, #FF3300 100%)" },
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
    { id: "cyber_punk", name: "Cyberpunk", desc: "Rain-slicked neon pink and blue cyberpunk glow on dark surfaces with wet reflections", swatch: "#ff44ff" },
    { id: "brushed_steel_dark", name: "Dark Brushed Steel", desc: "Dark steel with heavy directional brush grain and moody gunmetal industrial character", swatch: "#888899" },
    { id: "dawn_patrol", name: "Dawn Patrol", desc: "Early morning golden-hour warmth with soft sunrise gradient and peaceful amber glow", swatch: "#886644" },
    { id: "depth_map", name: "Depth Map", desc: "3D depth perception rendered as grayscale elevation mapping — closer surfaces go brighter", swatch: "#446688" },
    { id: "desert_mirage", name: "Desert Mirage", desc: "Wavering heat shimmer distortion over sun-baked sand — the road ahead seems to melt", swatch: "#ccaa77" },
    { id: "drafting", name: "Drafting", desc: "Aerodynamic draft pressure zones visualized with flowing air-stream color mapping", swatch: "#886644" },
    { id: "dreamscape", name: "Dreamscape", desc: "Surreal soft-focus landscape of floating color clouds and gentle luminous haze", swatch: "#7788cc" },
    { id: "drive_in", name: "Drive-In", desc: "1950s neon drive-in diner glow with chrome reflection — Americana sock-hop aesthetic for vintage cruise builds", swatch: "#CC6688" },
    { id: "ember_glow", name: "Ember Glow", desc: "Smoldering ember surface with bright orange-red cracks glowing through charred black", swatch: "#ee4422" },
    { id: "etched_metal", name: "Etched Metal", desc: "Chemically etched artistic metal with raised and recessed relief pattern detail", swatch: "#aabbcc" },
    { id: "firefly", name: "Firefly", desc: "Scattered bioluminescent glow points drifting across the surface like summer fireflies", swatch: "#ccaa44" },
    { id: "forged_iron", name: "Forged Iron", desc: "Blacksmith hammer-forged iron with glowing heat marks and rough worked-metal texture", swatch: "#556666" },
    { id: "frost_bite", name: "Frost Bite", desc: "Icy crystalline frost coating with sharp frozen crystal patterns and a cold bitter edge", swatch: "#88ccee" },
    { id: "frozen_lake", name: "Frozen Lake", desc: "Thick clear ice layer with trapped air bubbles, deep cracks, and frozen-in-time depth", swatch: "#aaddee" },
    { id: "galaxy", name: "Galaxy", desc: "Deep space nebula swirling with cosmic dust clouds and a brilliant distant star field", swatch: "#221144" },
    { id: "glitch_reality", name: "Glitch Reality", desc: "Heavy pixel scatter and noise displacement — digital corruption look as if reality itself is buffering and tearing", swatch: "#AA44EE" },
    { id: "green_flag", name: "Green Flag", desc: "Electric green start-race energy radiating outward — pure acceleration confidence", swatch: "#22aa33" },
    { id: "hammered_copper", name: "Hammered Copper", desc: "Hand-hammered warm copper with dimpled bowl texture and rich oxidation tones", swatch: "#cc7744" },
    { id: "heat_haze", name: "Heat Haze", desc: "Intense radiating heat distortion rising from hot metal — the air itself is shimmering", swatch: "#cc8844" },
    { id: "hot_rod_flames", name: "Hot Rod Flames", desc: "Traditional hot rod flowing flame paint job effect — classic 1950s flame licks down the body for nostalgic kustom builds", swatch: "#EE4422" },
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
    { id: "neon_glow", name: "Neon Glow", desc: "Bright neon tube edge-glow effect casting vivid colored light against the surface", swatch: "#44ee88" },
    { id: "neon_vegas", name: "Neon Vegas", desc: "Las Vegas strip multi-color neon sign glow with buzzing electric casino energy", swatch: "#22ff88" },
    { id: "ocean_floor", name: "Ocean Floor", desc: "Deep ocean floor with bioluminescent glow scattered across an abyssal dark surface", swatch: "#224488" },
    { id: "pace_lap", name: "Pace Lap", desc: "Yellow caution flag warm glow blending outward — the calm before green-flag intensity", swatch: "#44aa88" },
    { id: "patina_truck", name: "Patina Truck", desc: "Classic pickup patina — sun fade with surface rust and character that earned itself over decades of farm work", swatch: "#778866" },
    { id: "petrified_wood", name: "Petrified Wood", desc: "Ancient fossilized wood turned to stone with preserved grain and mineral color bands", swatch: "#887766" },
    { id: "phantom_zone", name: "Phantom Zone", desc: "Cold crystalline prison look — angular facets in muted blue-gray, like Krypton's banishment cube from Superman lore", swatch: "#556688" },
    { id: "photo_finish", name: "Photo Finish", desc: "Finish-line camera motion blur with speed streaks frozen in the decisive moment", swatch: "#aabbcc" },
    { id: "pin_up", name: "Pin-Up Nose Art", desc: "WWII bomber nose art style hand-painted over military primer — vintage aviation charm", swatch: "#cc8877" },
    { id: "plasma_globe", name: "Plasma Globe", desc: "Electric plasma tendrils branching and reaching from bright center discharge points", swatch: "#8844ff" },
    { id: "pole_position", name: "Pole Position", desc: "Front-row qualifier energy — electric confident metallic radiating first-place authority", swatch: "#886644" },
    { id: "portal", name: "Portal", desc: "Swirling vortex pattern — concentric energy rings in deep purple opening into another dimension across each panel", swatch: "#6633CC" },
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
    { id: "ruby", name: "Ruby", desc: "Deep blood-red gemstone with pigeon-blood core depth and brilliant internal fire refraction", swatch: "#cc1122" },
    { id: "rust", name: "Rust", desc: "Heavy orange-brown iron oxidation with flaking corrosion texture and rough pitted surface", swatch: "#aa5533" },
    { id: "sandstone", name: "Sandstone", desc: "Natural sandstone with visible mineral grain and warm sedimentary layers — desert rock feel", swatch: "#ccbb99" },
    { id: "sapphire", name: "Sapphire", desc: "Deep royal blue gemstone with brilliant internal fire sparkle and crystalline depth", swatch: "#2244aa" },
    { id: "scorched", name: "Scorched", desc: "Charred blackened surface with glowing hot-spot embers — post-fire scorched metal look", swatch: "#553322" },
    { id: "silk_road", name: "Silk Road", desc: "Flowing silk fabric drape with fine metallic thread shimmer — luxurious textile surface", swatch: "#886644" },
    { id: "stained_glass", name: "Stained Glass", desc: "Cathedral stained-glass window with vivid colored light zones and dark lead borders", swatch: "#aa4466" },
    { id: "static", name: "Static", desc: "Electric static discharge with bright sparking arcs crawling across a charged surface", swatch: "#88aadd" },
    { id: "time_warp", name: "Time Warp", desc: "Temporal distortion effect with melting clock faces and spiral warp — surreal Dali look", swatch: "#4466aa" },
    { id: "tornado_alley", name: "Tornado Alley", desc: "Rotating debris-filled violent storm with dark funnel cloud and scattered impact marks", swatch: "#889999" },
    { id: "tunnel_run", name: "Tunnel Run", desc: "Le Mans tunnel transition from bright sunlight into deep shadow and back to daylight", swatch: "#886644" },
    { id: "under_lights", name: "Under Lights", desc: "Night race finish under artificial floodlights with harsh sodium glow and deep shadows", swatch: "#ffcc22" },
    { id: "velvet_crush", name: "Velvet Crush", desc: "Deep crushed velvet texture with pile direction shift — luxury fabric aesthetic with light/dark zones based on viewing angle", swatch: "#662244" },
    { id: "venetian_glass", name: "Venetian Glass", desc: "Hand-blown Murano glass with multi-color translucent layers and trapped air bubbles", swatch: "#44aaaa" },
    { id: "victory_burnout", name: "Victory Burnout", desc: "Tire smoke, confetti, and champagne splash celebration — full post-race podium party aesthetic for winner livery overlays", swatch: "#DDBB55" },
    { id: "vinyl_record", name: "Vinyl Record", desc: "Concentric vinyl groove spiral with reflective rainbow edge and retro center label zone", swatch: "#222222" },
    { id: "volcanic_glass", name: "Volcanic Glass", desc: "Black obsidian volcanic glass with razor-sharp edges and glowing magma vein fractures", swatch: "#553322" },
    { id: "weathered_paint", name: "Weathered Paint", desc: "Sun-damaged old paint with peeling flakes and cracking clearcoat over faded original color", swatch: "#887766" },
    { id: "white_flag", name: "White Flag", desc: "Final-lap bright white intensity flash — pure blinding white with maximum reflectivity", swatch: "#dddddd" },
    { id: "woodie_wagon", name: "Woodie Wagon", desc: "1940s wood-panel station wagon sides with honey-toned grain and chrome strip borders", swatch: "#886644" },
    { id: "worn_chrome", name: "Worn Chrome", desc: "Aged pitted chrome with rust spots bleeding through — decades of neglect on mirror finish", swatch: "#aabbbb" },
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
    // FRACTURED MINDS (2026-06-11) — owner flagship color-shift bases
    { id: "fm_petal_storm", name: "Petal Storm", desc: "Petal Storm — FRACTURED MINDS PASTEL — a storm of drifting flower petals at every angle: light-pink air, light-blue petals, light-purple midribs in the combined spec (the owner-discovered pastel shift recipe). Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#cba8c6" },
    { id: "fm_basketweave", name: "Basketweave", desc: "Basketweave — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#56466a" },
    { id: "fm_cable_knit", name: "Cable Knit", desc: "Cable Knit — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#3f5e58" },
    { id: "fm_carbon_weave", name: "Carbon Weave", desc: "Carbon Weave — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5e4a44" },
    { id: "fm_chainlink", name: "Chainlink", desc: "Chainlink — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#46586a" },
    { id: "fm_chainmail", name: "Chainmail", desc: "Chainmail — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_checkerflash", name: "Checkerflash", desc: "Checkerflash — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#4a5670" },
    { id: "fm_circuit_maze", name: "Circuit Maze", desc: "Circuit Maze — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#56466a" },
    { id: "fm_code_cascade", name: "Code Cascade", desc: "Code Cascade — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#3f5e58" },
    { id: "fm_damascus", name: "Damascus", desc: "Damascus — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5e4a44" },
    { id: "fm_diamond_plate", name: "Diamond Plate", desc: "Diamond Plate — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#46586a" },
    { id: "fm_dragon_scale", name: "Dragon Scale", desc: "Dragon Scale — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_geode_slice", name: "Geode Slice", desc: "Geode Slice — FRACTURED MINDS color-shift base — agate growth bands wobbling around scattered seed cores; pink banded field, every third band and the druzy-crystal cores flood light blue with purple-dot sparks. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#7a5a9a" },
    { id: "fm_glacier_core", name: "Glacier Core", desc: "Glacier Core — FRACTURED MINDS BLUE FLIP — the spec is MOSTLY BLUE: deep-ice mirror field with purple crevasse veins and rare light-pink frost ridges. Crushed dark, the whole surface becomes an env mirror with glinting metal seams. Assign as BASE, crush the brightness, daytime track.", swatch: "#4a6a8a" },
    { id: "fm_frost_lace", name: "Frost Lace", desc: "Frost Lace — FRACTURED MINDS BLUE FLIP — window-frost fern crystals in purple metal lace over a blue mirror pane, lace tips sparking light pink. MOSTLY-blue combined spec. Assign as BASE, crush the brightness, daytime track.", swatch: "#6a7a9a" },
    { id: "fm_ion_drift", name: "Ion Drift", desc: "Ion Drift — FRACTURED MINDS BLUE FLIP — charged plasma streams drifting through a blue mirror field, purple stream cores, light-pink pulse heads, star pinpricks between. MOSTLY-blue combined spec. Assign as BASE, crush the brightness, daytime track.", swatch: "#4a5a9a" },
    { id: "fm_fiber_optic", name: "Fiber Optic", desc: "Fiber Optic — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#56466a" },
    { id: "fm_flame_helix", name: "Flame Helix", desc: "Flame Helix — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#3f5e58" },
    { id: "fm_flame_lick", name: "Flame Lick", desc: "Flame Lick — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5e4a44" },
    { id: "fm_flame_wall", name: "Flame Wall", desc: "Flame Wall — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#46586a" },
    { id: "fm_frost_feather", name: "Frost Feather", desc: "Frost Feather — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_graphene", name: "Graphene", desc: "Graphene — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#4a5670" },
    { id: "fm_gyro_cage", name: "Gyro Cage", desc: "Gyro Cage — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#56466a" },
    { id: "fm_gyroid", name: "Gyroid", desc: "Gyroid — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#3f5e58" },
    { id: "fm_herringbone", name: "Herringbone", desc: "Herringbone — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5e4a44" },
    { id: "fm_hexcore", name: "Hexcore", desc: "Hexcore — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#46586a" },
    { id: "fm_thousand_eyes", name: "Thousand Eyes", desc: "Thousand Eyes — FRACTURED MINDS color-shift base (HORROR) — a field of almond eyes staring out of the paint: bloodshot pink sclera field, glistening blue irises with purple striation dots, dead-void pupils. Crushed dark, the eyes glisten and the pupils stare back black. Assign as BASE, crush the brightness, daytime track.", swatch: "#5a3a4a" },
    { id: "fm_tide_glass", name: "Tide Glass", desc: "Tide Glass — FRACTURED MINDS BLUE FLIP — sunlight caustics on a pool floor: interfering purple-pink light webs over deep blue glass, web nodes sparking light pink. MOSTLY-blue combined spec. Assign as BASE, crush the brightness, daytime track.", swatch: "#3a6a7a" },
    { id: "fm_witchlight", name: "Witchlight", desc: "Witchlight — FRACTURED MINDS BLUE FLIP — drifting ghost-orbs with trailing purple wisps over the deepest blue mirror; orb cores burn light pink inside hard-blue halos. MOSTLY-blue combined spec. Assign as BASE, crush the brightness, daytime track.", swatch: "#5a4a8a" },
    { id: "fm_honeycomb_burst", name: "Honeycomb Burst", desc: "Honeycomb Burst — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#4a5670" },
    { id: "fm_inferno_veins", name: "Inferno Veins", desc: "Inferno Veins — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#56466a" },
    { id: "fm_labyrinth", name: "Labyrinth", desc: "Labyrinth — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#3f5e58" },
    { id: "fm_lattice", name: "Lattice", desc: "Lattice — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5e4a44" },
    { id: "fm_magma", name: "Magma", desc: "Magma — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#46586a" },
    { id: "fm_nanoweave", name: "Nanoweave", desc: "Nanoweave — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_python_skin", name: "Python Skin", desc: "Python Skin — FRACTURED MINDS color-shift base — rosette saddle colonies ringed by pale gold rims over keeled belly-scale micro-shimmer; the saddle hearts pool deep mirror while the rims halo metal. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#6a5a3a" },
    { id: "fm_octo_suckers", name: "Octo Suckers", desc: "Octo Suckers — FRACTURED MINDS color-shift base — curling tapered arms of sucker rings, every cup a wet mirror pool deepening toward its pore, every lip a metal ring. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#6a4256" },
    { id: "fm_stingray", name: "Stingray Shagreen", desc: "Stingray Shagreen — FRACTURED MINDS color-shift base — dense pearl-bead leather with a thin winding eye-stone ridge; bead crowns dome metal, equators ring mirror, the eye-line beads flip to pure-blue dielectric flash. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#4f5866" },
    { id: "fm_gila_bead", name: "Gila Bead", desc: "Gila Bead — FRACTURED MINDS color-shift base — two clans of beaded reticulation (metal-crown beads vs mirror-dome beads) with a live crawling border wire between the clans. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#7a4a26" },
    { id: "fm_riverine", name: "Riverine", desc: "Riverine — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#46586a" },
    { id: "fm_rivet_array", name: "Rivet Array", desc: "Rivet Array — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_rope_coil", name: "Rope Coil", desc: "Rope Coil — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#4a5670" },
    { id: "fm_croc_hide", name: "Croc Hide", desc: "Croc Hide — FRACTURED MINDS color-shift base — rounded osteoderm scutes with keeled metal domes, mirror caps on the crests, wet mirror rivers in the wrinkle channels; scattered scutes flip to blue dielectric. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#4a5a3e" },
    { id: "fm_diamondback", name: "Diamondback", desc: "Diamondback — FRACTURED MINDS color-shift base — a rattler diamond chain winding along its spine with pale keel borders; the chain IGNITES progressively along its length, each diamond a traveling mirror pulse. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#5a4f3a" },
    { id: "fm_dragonfly", name: "Dragonfly Wing", desc: "Dragonfly Wing — FRACTURED MINDS color-shift base — two-tier wing venation; only the BIG membrane panes ignite blue-mirror (size-graded thin film) while primary veins run near-max conduits. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#3e6a7a" },
    { id: "fm_ebru_marble", name: "Ebru Marble", desc: "Ebru Marble — FRACTURED MINDS color-shift base — Turkish paper-marbling ink streams combed into feathered chevrons; three inks carry three spec identities (tinted metal / dielectric blue / textured gold) with live veins on every combed boundary. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#6a3a52" },
    { id: "fm_static_burst", name: "Static Burst", desc: "Static Burst — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_tessellate", name: "Tessellate", desc: "Tessellate — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#4a5670" },
    { id: "fm_tortoise", name: "Tortoise Scute", desc: "Tortoise Scute — FRACTURED MINDS color-shift base — shell plates with interior growth rings that flash SEQUENTIALLY from rim to center, every plate on its own phase; horn seams stay dark. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#7a5c2e" },
    { id: "fm_tiger_slash", name: "Tiger Slash", desc: "Tiger Slash — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#3f5e58" },
    { id: "fm_topo_lines", name: "Topo Lines", desc: "Topo Lines — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5e4a44" },
    // FRACTURED SOULS — apex drag-and-drop color shift (2026-06-12)
    { id: "fs_core_violet", name: "Soul Core Violet — Yellow Gold Flash", desc: "Soul Core Violet — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Pure pre-crushed dark violet — the proven contract, no texture. Drop it on a zone and the color morphs/reveals by sun angle instantly. No sliders needed.", swatch: "#1c0d2e" },
    { id: "fs_core_abyss", name: "Soul Core Abyss — Amber Flash", desc: "Soul Core Abyss — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Pure pre-crushed abyss blue core — instant angle-driven color reveal, no setup.", swatch: "#0a1233" },
    { id: "fs_core_emerald", name: "Soul Core Emerald — Pink Flash", desc: "Soul Core Emerald — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Pure pre-crushed emerald core — instant angle-driven color reveal, no setup.", swatch: "#0a2917" },
    { id: "fs_core_crimson", name: "Soul Core Crimson — Teal Flash", desc: "Soul Core Crimson — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Pure pre-crushed crimson core — instant angle-driven color reveal, no setup.", swatch: "#2e0a10" },
    { id: "fs_core_aurum", name: "Soul Core Aurum — Purple Flash", desc: "Soul Core Aurum — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Pure pre-crushed gold core — instant angle-driven color reveal, no setup.", swatch: "#332608" },
    { id: "fs_wraith_veil", name: "Wraith Veil", desc: "Wraith Veil — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Smoky flowing veils carved into the reveal aperture — violet wraiths sweep across the car as the angle changes.", swatch: "#241238" },
    { id: "fs_moth_dust", name: "Moth Dust", desc: "Moth Dust — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Glitter-pin field: thousands of razor-aperture sparkle points dancing over a gold-dust core.", swatch: "#3a2c08" },
    { id: "fs_blood_marble", name: "Blood Marble", desc: "Blood Marble — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Marbled horror swirls in the aperture channel — crimson veins flash through near-black marble.", swatch: "#330a10" },
    { id: "fs_night_tide", name: "Night Tide", desc: "Night Tide — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Rolling wave-caustic lanes — abyss-blue swells reveal in moving bands.", swatch: "#0a1233" },
    { id: "fs_static_veins", name: "Static Veins", desc: "Static Veins — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Electric filaments with razor-pin cores — emerald lightning crawls through the reveal.", swatch: "#0a2917" },
    { id: "fs_shatter_glass", name: "Shatter Glass", desc: "Shatter Glass — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Angular shard lanes — ice-violet fractures flash plate by plate.", swatch: "#1a1233" },
    { id: "fs_howl", name: "Howl", desc: "Howl — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Radial claw-scratch flares (horror) — ash-violet gashes ignite at angle.", swatch: "#221a26" },
    { id: "fs_phantom_lattice", name: "Phantom Lattice", desc: "Phantom Lattice — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — A faint diamond lattice that only exists at the reveal angle — gunmetal teal.", swatch: "#0d2226" },
    { id: "fs_ember_drift", name: "Ember Drift", desc: "Ember Drift — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Drifting ember streaks with spark pins — burnt orange fire lanes.", swatch: "#331505" },
    { id: "fs_carnival_night", name: "Carnival Night", desc: "Carnival Night — FRACTURED SOULS (drag-and-drop color shift, built on the proven Ghost Fracture four-dial physics) — Confetti pin swarm in three hidden colors over midnight — the glitter light show.", swatch: "#120e26" },
    // FRACTURED SOULS round 3 (2026-06-12) — 15 new on the Blood Marble winner physics (M252/B255-rail/G-lanes)
    { id: "fs_soul_loom", name: "Soul Loom — Emerald × Violet Weave", desc: "Soul Loom — FRACTURED SOULS round 3 — WOVENLIGHT TWIST: warped ribbon weave with over/under dive shadows + thread striations, pre-crushed emerald and violet ribbon families. Each weave direction flashes its own color by sun angle.", swatch: "#13102a" },
    { id: "fs_widow_braid", name: "Widow Braid — Tri-Color Weave", desc: "Widow Braid — FRACTURED SOULS round 3 — WOVENLIGHT TWIST: tri-axial braid, three warped strand families 60° apart cycling on top. Rose / petrol / amber crushed hues = three flash colors from three sun geometries.", swatch: "#1c0f17" },
    { id: "fs_ghost_silk", name: "Ghost Silk — Indigo→Teal Satin", desc: "Ghost Silk — FRACTURED SOULS round 3 — WOVENLIGHT TWIST: micro satin threads in crisp curtain panels; third-angle sheen pools decide where the silk ignites, hue slides indigo→teal along the sheen.", swatch: "#161330" },
    { id: "fs_shattered_prism", name: "Shattered Prism — 47 Colors", desc: "Shattered Prism — FRACTURED SOULS round 3 — the '47 colors' flagship: fine crystal mosaic, EVERY cell its own crushed hue; borders + facet striations carve the aperture so each cell pops its own complement at its own angle.", swatch: "#1a1422" },
    { id: "fs_oil_serpent", name: "Oil Serpent — Flow-Hue Currents", desc: "Oil Serpent — FRACTURED SOULS round 3 — advected serpent currents; strand hue follows the FLOW DIRECTION, so the paint flashes different colors depending on which way the current bends.", swatch: "#0c1c1c" },
    { id: "fs_hex_hive", name: "Hex Hive — Amber/Petrol Comb", desc: "Hex Hive — FRACTURED SOULS round 3 — dead hive: fine rotated honeycomb, three crushed hues cycling cell-by-cell, walls carve the aperture, razor pore pin in every cell.", swatch: "#241a0c" },
    { id: "fs_guilloche_ghost", name: "Guilloché Ghost — Engine Turn", desc: "Guilloché Ghost — FRACTURED SOULS round 3 — banknote engine-turning: overlapping hairline harmonograph rosette nets, champagne + teal over crushed bronze; curve crossings pin razor glints.", swatch: "#241c10" },
    { id: "fs_petrol_halo", name: "Petrol Halo — Newton Rings", desc: "Petrol Halo — FRACTURED SOULS round 3 — Newton-ring packets: scattered interference halos of fine concentric rings whose hue cycles with ring index. Oil-on-water, crushed.", swatch: "#0e1822" },
    { id: "fs_star_chart", name: "Star Chart — Constellation Pins", desc: "Star Chart — FRACTURED SOULS round 3 — grave-sky cartography: razor star pins, hairline constellation chords, three faint nebula washes under crushed indigo.", swatch: "#100d28" },
    { id: "fs_serpent_scale", name: "Serpent Scale — Emerald/Abyss Rows", desc: "Serpent Scale — FRACTURED SOULS round 3 — imbricated scale rows: fine crescent rims + keeled centers, alternating crushed emerald/abyss rows that flash row-by-row.", swatch: "#0e1f16" },
    { id: "fs_nova_burst", name: "Nova Burst — Six-Color Detonations", desc: "Nova Burst — FRACTURED SOULS round 3 — scattered micro star-detonations, each with its own crushed hue halo: a six-color nova field on near-black violet.", swatch: "#170f24" },
    { id: "fs_circuit_soul", name: "Circuit Soul — Copper/Teal Traces", desc: "Circuit Soul — FRACTURED SOULS round 3 — haunted circuitry: hairline traces walking a seed-rotated grid, via-dots pinned razor; copper vs teal trace families flash separately.", swatch: "#101813" },
    { id: "fs_geode_vein", name: "Geode Vein — Five-Hue Agate", desc: "Geode Vein — FRACTURED SOULS round 3 — agate banding: warped contour bands cycling five crushed hues (violet/teal/gold/rose/ice), druzy pin pockets every few bands.", swatch: "#1c1326" },
    { id: "fs_moire_phantom", name: "Moiré Phantom — Interference Curves", desc: "Moiré Phantom — FRACTURED SOULS round 3 — circular moiré: two families of fine concentric rings interfere into wandering phantom curves; the beat decides which hue shows (steel-teal vs rose).", swatch: "#191420" },
    { id: "fs_aurora_threads", name: "Aurora Threads — Green→Violet Curtains", desc: "Aurora Threads — FRACTURED SOULS round 3 — curtain filaments: micro threads gated into crisp aurora curtains, hue sweeping green→teal→violet across the car. Many colors in the paint at once.", swatch: "#0c2017" },
    // GHOST LAB single-variable experiments (2026-06-12)
    { id: "gl_control", name: "GL 00 Control (Ghost Fracture)", desc: "GL 00 Control (Ghost Fracture) — GHOST LAB experiment — Byte-identical Ghost Fracture. Your reference — everything else changes ONE thing vs this. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_metal_low", name: "GL 01 Metal LOW (~150)", desc: "GL 01 Metal LOW (~150) — GHOST LAB experiment — PILLAR 1 TEST: metal dropped to the level our newer finishes use. If the purple stops jumping through, near-max metal is the body-color engine. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_metal_mid", name: "GL 02 Metal MID (~185)", desc: "GL 02 Metal MID (~185) — GHOST LAB experiment — Pillar 1 dose-response: halfway. Tells us the metal threshold where color-jump starts dying. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_rough_pastel", name: "GL 03 Rough PASTEL (150-200)", desc: "GL 03 Rough PASTEL (150-200) — GHOST LAB experiment — PILLAR 2 TEST + the pastel doctrine on-track: roughness raised to the light-pastel band. If flashes go soft/hazy, low roughness is what makes them EXPLODE. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_rough_mirror", name: "GL 04 Rough MIRROR (30-60)", desc: "GL 04 Rough MIRROR (30-60) — GHOST LAB experiment — Pillar 2 the other direction: glossier than GF. Do flashes get even sharper/harder? Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_cc_flat", name: "GL 05 Clearcoat FLAT (no cells)", desc: "GL 05 Clearcoat FLAT (no cells) — GHOST LAB experiment — PILLAR 3 TEST: same metal+gloss but the carve is GONE (CC uniform 212). If gold still flashes but with no cell pattern, the carve is only the SHAPE; if gold dies, the carve is the engine. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_cc_shallow", name: "GL 06 Clearcoat SHALLOW carve", desc: "GL 06 Clearcoat SHALLOW carve — GHOST LAB experiment — Pillar 3 dose-response: carve amplitude halved. How much swing does the two-color travel need? Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_cc_inverted", name: "GL 07 Clearcoat INVERTED", desc: "GL 07 Clearcoat INVERTED — GHOST LAB experiment — Cells swap polarity (carved becomes flooded). Should swap WHERE gold vs teal appears — confirms the cells choose which env color shows. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_cells_micro", name: "GL 08 Cells MICRO (3x smaller)", desc: "GL 08 Cells MICRO (3x smaller) — GHOST LAB experiment — Structure scale: same recipe, 3x finer cells. Does fine structure shimmer instead of detonate? Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_cells_macro", name: "GL 09 Cells MACRO (3x bigger)", desc: "GL 09 Cells MACRO (3x bigger) — GHOST LAB experiment — Structure scale: 3x bigger cells. Do big panels flash harder but read blocky? Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_pastel_full", name: "GL 10 Full PASTEL recipe", desc: "GL 10 Full PASTEL recipe — GHOST LAB experiment — The round-5 pastel doctrine applied to GF geometry (rough 150-170, compressed carve 191-240). Head-to-head vs GL 00 settles whether pastel beats the original on track. Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "gl_cc_max", name: "GL 11 Clearcoat MAX carve", desc: "GL 11 Clearcoat MAX carve — GHOST LAB experiment — Carve amplitude pushed to the rails (cells swing 40<->250). Is more swing more magic, or does it clip into noise? Ritual: assign as BASE, set the SAME purple, CRUSH brightness, same daytime track, compare to GL 00.", swatch: "#3a3a4a" },
    { id: "fm_basalt", name: "Basalt Columns", desc: "Basalt Columns — FRACTURED MINDS color-shift base — Giant's Causeway columns end-on: hot and cold column clans, chipped sparkling rims, and onion-fracture rings giving every column its own radial flash signature. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#4a4d55" },
    { id: "fm_tsunami", name: "Tsunami", desc: "Tsunami — FRACTURED MINDS color-shift base — assign as BASE, pick a color, CRUSH the brightness near black, daytime track: the carved cells flash sky-teal and sun-gold by angle while flakes and slashes fire from inside the pattern.", swatch: "#5a5246" },
    { id: "fm_mudcrack", name: "Mudcrack Curl", desc: "Mudcrack Curl — FRACTURED MINDS color-shift base — dried-lakebed plates whose crack canyons run deep mirror while the curled lips ridge metal; plate cores crossfade on a slow macro gradient. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#6a523e" },
    { id: "fm_penrose", name: "Penrose Quasi", desc: "Penrose Quasi — FRACTURED MINDS color-shift base — five-fold quasicrystal interference that NEVER repeats anywhere on the car: gold star suns, cyan anti-star wells, and an aperiodic mirror flood across the low field. Assign as BASE, pick a color, CRUSH the brightness near black, daytime track.", swatch: "#463e6a" },
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
    { id: "sparkle_snowfall", name: "Sparkle Snowfall", desc: "Dense cold crystal sparkle field with icy white points on pale frozen base — fresh snow", swatch: "#ccddee" },
    // R6 RACING-PIVOT V3 (2026-05-26): sparkle_champagne ALIASED to tiger_stripe_field.
    // Sparkle-cluster diversification — predator-skin replacement for sparkle clone.
    { id: "sparkle_champagne", name: "Tiger Stripe Field", desc: "Tiger fur — warm orange-tan base with 18-30 bold black irregular stripes 4-8 px wide running mostly vertical with diagonal jitter + 80-150 short stub stripes + 6-10 hero extra-bold stripes with bright orange edge halo", swatch: "#c66a1f" },
    { id: "sparkle_meteor", name: "Sparkle Meteor", desc: "Directional meteor trail sparkle with streaked bright points all moving in one direction", swatch: "#cc8844" },
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
    // SPB-102 ★ Spectrum Shift — 50 procedural iridescent fusions (2026-05-17 UI wire-up)
    // SPECTRUM SHIFT 2026 (2026-06-11) — 50 bespoke optical-physics finishes
    // (engine/expansions/spectrum_shift_2026.py); replaced the 10x5 palette clones.
    { id: "spectrum_aberration_glitch", name: "Aberration Glitch", desc: "★ Spectrum Shift — Aberration Glitch: A crisp mono mosaic shot through a broken lens: R and B sheared opposite ways so EVERY edge grows prism fringes.", swatch: "#565452" },
    { id: "spectrum_abrasion_halo", name: "Abrasion Halo", desc: "★ Spectrum Shift — Abrasion Halo: Scratch holography on polished steel: thousands of micro arcs whose spectral glints CRAWL along the scratches as the view tilts.", swatch: "#5e6270" },
    { id: "spectrum_anodine_dunes", name: "Anodine Dunes", desc: "★ Spectrum Shift — Anodine Dunes: Wind-rippled dunes anodized by slope aspect: straw-violet-cobalt riding the slip faces, grating-fine ripples everywhere.", swatch: "#695461" },
    { id: "spectrum_beetle_elytra", name: "Beetle Elytra", desc: "★ Spectrum Shift — Beetle Elytra: Jewel-scarab shell: hexagonal micro-dimple lattice with metallic green-gold bands sweeping across the carapace.", swatch: "#40570e" },
    { id: "spectrum_bismuth_garden", name: "Bismuth Garden", desc: "★ Spectrum Shift — Bismuth Garden: Bismuth hopper crystals: stepped square-spiral terraces in anodize rainbow by depth — the staircase geode.", swatch: "#2b4157" },
    { id: "spectrum_black_opal", name: "Black Opal", desc: "★ Spectrum Shift — Black Opal: Lightning Ridge black opal: sleeping color domains in near-black potch that DETONATE in spectral fire at the gate angle.", swatch: "#5a4843" },
    { id: "spectrum_borealis_ice", name: "Borealis Ice", desc: "★ Spectrum Shift — Borealis Ice: Aurora curtains REFRACTED through pack ice: every shard displaces and recolors the light passing through it.", swatch: "#505a57" },
    { id: "spectrum_boulder_opal", name: "Boulder Opal", desc: "★ Spectrum Shift — Boulder Opal: Boulder opal: rainbow fire running only in the veins through dark ironstone — the matrix stays stone, the seams burn.", swatch: "#483121" },
    { id: "spectrum_chromatic_orchid", name: "Chromatic Orchid", desc: "★ Spectrum Shift — Chromatic Orchid: Orchid fields with spectral nectar-guide veins — the ultraviolet runway insects see, made visible.", swatch: "#5a3956" },
    { id: "spectrum_circuit_awakens", name: "Circuit Awakens", desc: "★ Spectrum Shift — Circuit Awakens: Dormant circuitry: Manhattan traces and solder vias that power ON in spectral sequence as the view sweeps.", swatch: "#2c5a39" },
    { id: "spectrum_clockwork_dial", name: "Clockwork Dial", desc: "★ Spectrum Shift — Clockwork Dial: Watch-dial guilloche: jittered gold rosettes over spectral lathe rings on near-black — horology under a prism.", swatch: "#719046" },
    { id: "spectrum_contact_bloom", name: "Contact Bloom", desc: "★ Spectrum Shift — Contact Bloom: Newton-ring blossoms: thin-film interference rings with true Airy crowding around every contact point, overlapping into gardens.", swatch: "#8d8981" },
    { id: "spectrum_data_etch", name: "Data Etch", desc: "★ Spectrum Shift — Data Etch: Optical-disc data sectors: wedge fields of micro-tracks, every sector refracting its own order rainbow off the etched blocks.", swatch: "#9280af" },
    { id: "spectrum_diamond_fire", name: "Diamond Fire", desc: "★ Spectrum Shift — Diamond Fire: Brilliant-cut scintillation: kite-facet fans with internal dispersion and white scintillation pins — ice with fire in it.", swatch: "#d7e2e0" },
    { id: "spectrum_event_horizon", name: "Event Horizon", desc: "★ Spectrum Shift — Event Horizon: An accretion disk doppler-beamed for real: the approaching side burns blue-white, the receding side dims red, around lensed black cores.", swatch: "#5a4f54" },
    { id: "spectrum_flare_spectra", name: "Flare Spectra", desc: "★ Spectrum Shift — Flare Spectra: Spectroheliograph corona: thin emission-line arcs in pure spectral colors leaping across near-black.", swatch: "#5a5656" },
    { id: "spectrum_forge_heat", name: "Forge Heat", desc: "★ Spectrum Shift — Forge Heat: True Planck incandescence: hammered steel glowing through cherry-orange-white by actual blackbody color, slag flecks quenching dark.", swatch: "#c4894a" },
    { id: "spectrum_fracture_polarized", name: "Fracture Polarized", desc: "★ Spectrum Shift — Fracture Polarized: Cracked stressed glass: fringe rainbows CROWD at every crack tip (true stress concentration), the fractures glassy black.", swatch: "#594341" },
    { id: "spectrum_ghost_prism", name: "Ghost Prism", desc: "★ Spectrum Shift — Ghost Prism: Double-exposure spectroscopy: an attractor motif and its R/G/B ghosts offset in three directions — spectral echo art.", swatch: "#4d525a" },
    { id: "spectrum_grating_quilt", name: "Grating Quilt", desc: "★ Spectrum Shift — Grating Quilt: Holo-foil patchwork: stitched tiles of hairline diffraction gratings at scattered angles — every patch fires its own color at its own angle.", swatch: "#64395c" },
    { id: "spectrum_interference_weave", name: "Interference Weave", desc: "★ Spectrum Shift — Interference Weave: Over-under thread weave where the moire beat phase decides every crossing's hue — textile interference.", swatch: "#896d63" },
    { id: "spectrum_jewel_box", name: "Jewel Box", desc: "★ Spectrum Shift — Jewel Box: Stained-glass shard mosaic with dispersed caustics caged INSIDE each facet — light trapped in a jewel case.", swatch: "#5a4740" },
    { id: "spectrum_lathe_burst", name: "Lathe Burst", desc: "★ Spectrum Shift — Lathe Burst: Overlapping spin-cut systems; hue follows the cut angle like light raking spun metal — holographic engine-turning.", swatch: "#2c668a" },
    { id: "spectrum_liquid_crystal", name: "Liquid Crystal", desc: "★ Spectrum Shift — Liquid Crystal: Cholesteric liquid crystal under the microscope: fingerprint pitch bands cycling the wheel, dark disclination defects threading through.", swatch: "#414655" },
    { id: "spectrum_magnet_flow", name: "Magnet Flow", desc: "★ Spectrum Shift — Magnet Flow: Iron filings in spectral ink: hue advected along true dipole field lines arcing pole to pole.", swatch: "#3c5a38" },
    { id: "spectrum_mantis_strike", name: "Mantis Strike", desc: "★ Spectrum Shift — Mantis Strike: Mantis-shrimp carapace: segmented armor plates each cycling its own spectral band, raptorial strike streaks in ember.", swatch: "#a76f2f" },
    { id: "spectrum_moire_silk", name: "Moire Silk", desc: "★ Spectrum Shift — Moire Silk: Two silk-fine line lattices a hair off angle: giant slow rainbow interference beats rolling over visible micro-threads.", swatch: "#895a59" },
    { id: "spectrum_nacre_tide", name: "Nacre Tide", desc: "★ Spectrum Shift — Nacre Tide: Abalone growth terraces: wavy stacked layer-lines, mother-of-pearl travel by layer count, dark conchiolin seams.", swatch: "#895553" },
    { id: "spectrum_oilfilm_rain", name: "Oilfilm Rain", desc: "★ Spectrum Shift — Oilfilm Rain: Gasoline rainbow after rain: drain-streaked oil film, rain-impact ring sets, wet aggregate poking through the slick.", swatch: "#4a3321" },
    { id: "spectrum_opal_core", name: "Opal Core", desc: "★ Spectrum Shift — Opal Core: Full crystal opal: wall-to-wall play-of-color domains over milk glass, every domain flashing on its own schedule.", swatch: "#a99393" },
    { id: "spectrum_orbital_engrave", name: "Orbital Engrave", desc: "★ Spectrum Shift — Orbital Engrave: Interlocking orbital ring systems cut into black chrome, each system flashing its glint at a different clock position — sequential fire.", swatch: "#45465a" },
    { id: "spectrum_peacock_eye", name: "Peacock Eye", desc: "★ Spectrum Shift — Peacock Eye: Peacock train: dense structural-color eyespots (cobalt heart, teal iris, bronze halo) over fine radiating barbs.", swatch: "#155a37" },
    { id: "spectrum_pressure_map", name: "Pressure Map", desc: "★ Spectrum Shift — Pressure Map: Meteorology in paint: cyclone isobar spirals cycling hue, wind-streak barbs combing between the cells.", swatch: "#3c683d" },
    { id: "spectrum_prism_pool", name: "Prism Pool", desc: "★ Spectrum Shift — Prism Pool: Dispersed caustics in a midnight pool: every dancing light filament is itself a tiny spectrum, red bending wider than blue.", swatch: "#38495a" },
    { id: "spectrum_rainbow_river", name: "Rainbow River", desc: "★ Spectrum Shift — Rainbow River: Spectrum as a fluid: hue advected along real currents — rainbow streams, eddies trapping whirlpools of trapped color.", swatch: "#376c3f" },
    { id: "spectrum_redshift_drift", name: "Redshift Drift", desc: "★ Spectrum Shift — Redshift Drift: Receding galaxies: streaks red-shifted trailing, blue-shifted leading, smeared along the expansion flow.", swatch: "#53565a" },
    { id: "spectrum_shatter_glass", name: "Shatter Glass", desc: "★ Spectrum Shift — Shatter Glass: Tempered glass exploded: shard mosaic, each fragment refracting its own dispersion gradient, prism fringes at every fracture line.", swatch: "#4b535f" },
    { id: "spectrum_singularity_lens", name: "Singularity Lens", desc: "★ Spectrum Shift — Singularity Lens: A deep-field sky gravitationally smeared into Einstein arcs and rings around invisible dark masses, violet rim-light on the voids.", swatch: "#2a3d5a" },
    { id: "spectrum_smectic_fan", name: "Smectic Fan", desc: "★ Spectrum Shift — Smectic Fan: Smectic focal-conic fans: packed ribbed fan domains, each refracting its own slice of the wheel — polarized-microscope money shot.", swatch: "#563a43" },
    { id: "spectrum_smoke_chroma", name: "Smoke Chroma", desc: "★ Spectrum Shift — Smoke Chroma: Laminar smoke going turbulent, every filament carrying its slice of spectrum through the curl.", swatch: "#455a4c" },
    { id: "spectrum_spill_metropolis", name: "Spill Metropolis", desc: "★ Spectrum Shift — Spill Metropolis: Gasoline rainbow on wet night asphalt: micro-aggregate, drain swirls, neon signs bleeding into the slick.", swatch: "#5a2a3e" },
    { id: "spectrum_star_temperature", name: "Star Temperature", desc: "★ Spectrum Shift — Star Temperature: The HR diagram as a sky: thousands of stars each colored by its real temperature class — red dwarfs to blue giants.", swatch: "#3a335a" },
    { id: "spectrum_stress_storm", name: "Stress Storm", desc: "★ Spectrum Shift — Stress Storm: A polariscope hurricane: dozens of colliding photoelastic stress fringes — real fringe-order physics, rainbow contours storming across dark glass.", swatch: "#6e576a" },
    { id: "spectrum_swirl_supernova", name: "Swirl Supernova", desc: "★ Spectrum Shift — Swirl Supernova: The detailer's swirl-mark nightmare made cosmic: micro arc-galaxies on deep violet, dispersive star glints riding every arc.", swatch: "#3e215a" },
    { id: "spectrum_tempered_ghost", name: "Tempered Ghost", desc: "★ Spectrum Shift — Tempered Ghost: The polarized-sunglasses car-window secret: a drifting lattice of quench-spot stress rosettes in rose and iris over smoked glass.", swatch: "#4a455a" },
    { id: "spectrum_thermo_touch", name: "Thermo Touch", desc: "★ Spectrum Shift — Thermo Touch: Thermochromic skin: heat blooms crawl through the LC spectrum (bronze-green-blue) over visible fingerprint texture — a touch-reactive heat map.", swatch: "#0d5743" },
    { id: "spectrum_topo_rainbow", name: "Topo Rainbow", desc: "★ Spectrum Shift — Topo Rainbow: Survey-fine elevation isolines cycling the wheel over shaded relief — cartography as iridescence.", swatch: "#43585a" },
    { id: "spectrum_vhs_phantom", name: "Vhs Phantom", desc: "★ Spectrum Shift — Vhs Phantom: Analog video breakdown: scanline micro, tracking-error rainbow tears, chromatic ghost offsets — the haunted tape.", swatch: "#578976" },
    { id: "spectrum_vinyl_groove", name: "Vinyl Groove", desc: "★ Spectrum Shift — Vinyl Groove: Record grooves at hairline pitch sweeping in from off-canvas spindles, tone-arm rainbows raking across the tracks, anti-static dust glints.", swatch: "#963ab4" },
    { id: "spectrum_xray_bloom", name: "Xray Bloom", desc: "★ Spectrum Shift — Xray Bloom: A garden in body color whose vein SKELETONS detonate spectral at the flash angle — the flowers x-ray themselves.", swatch: "#5a2750" },
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
    // 2026-06-02 (owner): the 6 "Research Session 6" standalone-effect monolithics
    // (aurora_borealis_mono, deep_space_void, polished_obsidian_mono, patinated_bronze,
    // reactive_plasma, molten_metal) + 4 more (thermal_titanium, galaxy_nebula_base,
    // dark_sigil, oil_slick_base) were removed with the "Standalone Effects" group.
    // ── INTRICATE & ORNATE — Batch 1 (moved from SPEC_PATTERNS where they were misplaced)
    { id: "carbon_3k_weave", name: "Carbon 3K Weave", desc: "3K satin-braid diagonal carbon — two interleaved 45° diagonal tow directions vs the standard 2×2 twill", swatch: "#223344" },
].filter(m => !REMOVED_SPECIAL_IDS.has(m.id));

// ============================================================
// SPEC PATTERNS — stackable spec map overlays
// ============================================================
const SPEC_PATTERNS = [
    // Reference Pattern Plates - real source plates converted to SPEC overlays
    { id: "spec_holographic_oil_circuit", name: "SPEC Holographic Oil Circuit", desc: "Rainbow oil-film highlights, polished low-roughness arcs, and prismatic clearcoat response.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_black_emboss_mandala", name: "SPEC Black Emboss Mandala", desc: "Dark raised relief, satin valleys, and glossy mandala edge catches.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_graphite_cross_lattice", name: "SPEC Graphite Cross Lattice", desc: "Graphite lattice ribs with crisp bright intersections and controlled satin gaps.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_marble_flow_pearl", name: "SPEC Marble Flow Pearl", desc: "Pearl marble veins with soft clearcoat rivers and polished vein ridges.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_acid_carbon_mesh", name: "SPEC Acid Carbon Mesh", desc: "Acid-tinted mesh/carbon contrast with tight gloss cells and matte under-weave.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_noir_houndstooth_star", name: "SPEC Noir Houndstooth Star", desc: "Noir textile stars and houndstooth checks with thread-level roughness shifts.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_hazard_chevron_weave", name: "SPEC Hazard Chevron Weave", desc: "Hazard chevrons with bright cut edges, dark rubber troughs, and woven directionality.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_burn_hole_mesh", name: "SPEC Burn Hole Mesh", desc: "Burned mesh crater texture with scorched rough pits and polished raised rim detail.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_teal_hex_haze", name: "SPEC Teal Hex Haze", desc: "Teal hex haze with pearly bokeh cells and restrained translucent clearcoat.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_shadow_diamond_mesh", name: "SPEC Shadow Diamond Mesh", desc: "Shadow diamond mesh with repeating raised ridges and satin recessed panels.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_talavera_tile_riot", name: "SPEC Talavera Tile Riot", desc: "Talavera ceramic tile gloss with enamel ridges and deep grout contrast.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_green_plasma_vein", name: "SPEC Green Plasma Vein", desc: "Green plasma veins with electrical gloss streaks and smoky rough shadows.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_neon_fracture_net", name: "SPEC Neon Fracture Net", desc: "Neon fracture net with hot crack clearcoat and black low-sheen islands.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_pink_checker_carbon", name: "SPEC Pink Checker Carbon", desc: "Pink checker carbon geometry with glossy colored cells and dark woven breaks.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_red_herringbone_heat", name: "SPEC Red Herringbone Heat", desc: "Red herringbone heat weave with diagonal satin grain and hot edge flashes.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_chrome_oval_chain", name: "Pop Top", desc: "Stamped aluminium can top — pull-tab ring, rivet, and rolled rim.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_terracotta_ceramic_grid", name: "SPEC Terracotta Ceramic Grid", desc: "Terracotta ceramic grid with glazed stone islands and gritty grout channels.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_gunmetal_geo_tessellation", name: "SPEC Gunmetal Geo Tessellation", desc: "Gunmetal micro tessellation with precise satin/metal facet shifts.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_tokyo_script_textile", name: "SPEC Tokyo Script Textile", desc: "Tokyo script textile with inked cloth valleys and glossy red-white calligraphy strokes.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lime_pixel_confetti", name: "SPEC Lime Pixel Confetti", desc: "Lime pixel confetti with small hard gloss pops across a matte field.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_psychedelic_floral_spin", name: "SPEC Psychedelic Floral Spin", desc: "Psychedelic guilloche floral rings with shifting satin petals and chrome thread lines.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_ice_facet_shatter", name: "SPEC Ice Facet Shatter", desc: "Ice crystal shards with cold clearcoat facets and bright frozen cuts.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_ember_circuit_maze", name: "SPEC Ember Circuit Maze", desc: "Ember circuit maze with heated copper lines and dark insulated cells.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_blue_polygon_shatter", name: "SPEC Blue Polygon Shatter", desc: "Blue polygon shatter with angular clearcoat facets and graphite separators.", category: "Source Pattern Plates", defaults: {}, defaultChannels: "MRC" },
    { id: "banded_rows", name: "Banded Rows", desc: "Adds horizontal metallic/roughness bands with soft feathered transitions between value zones", category: "Structure & Geometry", defaults: { num_bands: 50, palette_size: 10 } },
    // R6 RACING-PIVOT V3 (2026-05-26): aniso_grain ALIASED to chainmail_armor.
    // Owner: "Boring / no character". Replaced with interlocking 6-10 px metal rings.
    { id: "hex_cells", name: "Hex Cells", desc: "Applies honeycomb hexagonal cell grid with per-cell metallic and roughness variation for tiled texture", category: "Structure & Geometry", defaults: { cell_size: 20 } },
    { id: "panel_zones", name: "Panel Zones", desc: "Defines large irregular zones with different metallic and roughness values — panel color variation", category: "Structure & Geometry", defaults: { num_zones: 25 } },
    // 2026-04-19 HEENAN HP2 — id `carbon_weave` was a TRIPLE collision:
    // BASES (L291), PATTERNS (L695), and SPEC_PATTERNS (here). Spec-pattern
    // siblings already use the `spec_*` namespace (spec_kevlar_weave,
    // spec_wood_burl, spec_carbon_2x2_twill, etc.). Renamed to spec_carbon_weave
    // to match that convention; updated SPEC_PATTERN_GROUPS["Misc"] reference.
    { id: "spec_carbon_weave", name: "Carbon Weave (Spec)", desc: "Adds woven fiber crosshatch roughness pattern simulating carbon fiber surface texture on spec maps", category: "Surface & Spray Texture", defaults: { weave_size: 12 } },
    { id: "crackle_network", name: "Crackle Network", desc: "Creates crack and craze roughness network like dried clay — sharp channels cut through smooth surface", category: "Weather, Wear & Track", defaults: { cell_count: 25 } },
    { id: "pebble_grain", name: "Pebble Grain", desc: "Adds large rounded roughness bumps like leather pebble grain — dimpled surface texture variation", category: "Surface & Spray Texture", defaults: { pebble_size: 5 } },
    { id: "wave_ripple", name: "Wave Ripple", desc: "Adds directional water surface interference waves that modulate roughness in flowing ripple bands", category: "Optical & Interference", defaults: { num_waves: 5 } },
    // --- NEW PATTERNS (26-50) ---
    { id: "voronoi_fracture", name: "Voronoi Fracture", desc: "Shattered glass cell boundaries with dark fracture lines", category: "Sparkle & Micro-Metal", defaults: { num_cells: 200, edge_width: 1.0 } },
    { id: "diamond_lattice", name: "Diamond Lattice", desc: "R6 owner rebuild — CLEAN sharp rhombus lattice grid with crisp 1px polyline outlines, uniform per-cell fill from a tight polished-steel palette + every 7th cell as a brighter hero gem with sharp top-edge highlight (no noise, no grain, no FBM)", category: "Geometric & Structural", defaults: { cell_size: 24, depth_variation: 0.4 } },
    { id: "galaxy_swirl", name: "Galaxy Swirl", desc: "Creates spiral galaxy arm metallic patterns with scattered star cluster highlight points throughout", category: "Optical & Interference", defaults: { num_arms: 4, twist: 3.0 } },
    { id: "prismatic_shatter", name: "Prismatic Shatter", desc: "Shattered prism fragments reflecting at different angles", category: "Sparkle & Micro-Metal", defaults: { num_shards: 300 } },
    { id: "lava_crack", name: "Lava Crack", desc: "Cooling lava plates with bright glowing fissures between", category: "Organic & Natural", defaults: { num_plates: 35, glow_width: 4.0 } },
    // 2026-04-19 HEENAN HP3 — id `diffraction_grating` collided with PATTERNS
    // (L845). Renamed SPEC_PATTERNS entry to spec_diffraction_grating_cd
    // (sister to spec_diffraction_grating which already exists in Optical).
    // TF13 had already disambiguated the display name; this completes the fix
    // at the id level. SPEC_PATTERN_GROUPS["Optical"] updated accordingly.
    { id: "spec_diffraction_grating_cd", name: "Diffraction Grating (CD)", desc: "Fine parallel ruling lines — CD surface rainbow diffraction", category: "Optical & Interference", defaults: { line_freq: 80.0, num_orders: 5 } },
    // 2026-04-19 HEENAN H4HR-4 — `oil_slick` collided with MONOLITHICS L1354.
    // SPEC entry namespaced; HP-MIGRATE handles backward compat. MONO keeps id.
    // 2026-04-19 HEENAN H4HR-5 — `gravity_well` collided with MONOLITHICS L1562.
    // --- NEW PATTERNS (51-65) ---
    // Sparkle / Flake variants
    { id: "metallic_sand", name: "Metallic Sand", desc: "Fine 2px block-quantized metallic sand particles — slightly larger than diamond dust", category: "Sparkle & Micro-Metal", defaults: { block_size: 2 } },
    { id: "holographic_flake", name: "Holographic Flake", desc: "Iridescent flakes with position-modulated brightness — rainbow prismatic scatter", category: "Sparkle & Micro-Metal", defaults: { density: 0.02, freq_x: 35.0, freq_y: 28.0 } },
    { id: "stardust_fine", name: "Stardust Fine", desc: "Extremely fine high-density sparkle — like a star-filled night sky", category: "Sparkle & Micro-Metal", defaults: { density: 0.05 } },
    { id: "pearl_micro", name: "Pearl Micro", desc: "Soft pearlescent micro-texture — smooth undulating mother-of-pearl iridescence", category: "Sparkle & Micro-Metal", defaults: { octaves: 4 } },
    { id: "gold_flake", name: "Gold Flake", desc: "Large sparse irregular gold-leaf style flakes — bright fragments on a dark field", category: "Sparkle & Micro-Metal", defaults: { density1: 0.6, density2: 0.5 } },
    // R6 RACING-PIVOT V3 (2026-05-26): brushed_sparkle ALIASED to nordic_rune_field.
    // Sparkle-cluster diversification — replaces a near-duplicate sparkle pattern.
    { id: "brushed_sparkle", name: "Nordic Rune Field", desc: "Carved Viking runes on dark stone — angular Algiz/Tiwaz/Othala/Eihwaz line geometries 12-22 px Poisson-scattered + 8-14 hero 24-32 px halo-glowing runes + 3-5 red blood-magic runes, M=Metallic + G=Roughness + B=Clearcoat", category: "Gothic & Horror", defaults: {}, defaultChannels: "MRC" },
    // 2026-04-19 HEENAN H4HR-6 — `sparkle_constellation` collided with MONOLITHICS L1621.
    // 2026-04-19 HEENAN H4HR-7 — `sparkle_firefly` collided with MONOLITHICS L1617.
    // R6 RACING-PIVOT V3 (2026-05-26): sparkle_shattered ALIASED to razor_wire_coil.
    // Sparkle-cluster diversification — replaces a near-duplicate sparkle pattern.
    { id: "sparkle_shattered", name: "Razor Wire Coil", desc: "Coiled concertina razor wire — 6-12 helical bands sweeping diagonal sine curves, 4-7 px thick with sharp triangular razor blades 6-10 px embedded every 8-12 px + 4-8 hero barbed bundle crossings + 6-12 broken sheared wire ends, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    // 2026-04-19 HEENAN H4HR-8 — `sparkle_champagne` collided with MONOLITHICS L1619.
    // Banded row variants
    { id: "chevron_bands", name: "Chevron Bands", desc: "V-shaped chevron bands — arrowhead striping using y + abs(x-center) coordinate", category: "Structure & Geometry", defaults: { num_bands: 40, v_angle: 0.6 } },
    { id: "wave_bands", name: "Wave Bands", desc: "Sinusoidal wavy bands — undulating stripes using y + sin(x * freq) coordinate", category: "Structure & Geometry", defaults: { num_bands: 36, wave_freq: 6.0, wave_amp: 0.12 } },
    { id: "gradient_bands", name: "Gradient Bands", desc: "Bands that fade bright-to-dark internally — fmod banding with within-band gradient", category: "Structure & Geometry", defaults: { num_bands: 35 } },
    // NOTE: Intricate & Ornate patterns MOVED to PATTERNS array (were mistakenly in SPEC_PATTERNS)
    // --- PRIORITY 2 BATCH A: 🪛 Directional Brushed (66–77) — G=Roughness channel ---
    { id: "brushed_diagonal", name: "Brushed Diagonal", desc: "45° diagonal brushed lines via rotated projection — chevron-style panel polish, G=Roughness", category: "Directional Metal & Brush", defaults: { frequency: 70.0, angle_deg: 45.0 } },
    { id: "brushed_cross", name: "Brushed Cross", desc: "R6 rebuild: bidirectional H+V cross-brushed scotch-brite strata + 100-200 explicit '+' cross marks 8-16 px scattered as HERO motif (no more engine-turn circles) + 14-22 larger crosses with bright halo, G=Roughness", category: "Directional Metal & Brush", defaults: { frequency: 60.0 } },
    // === Guilloché & Machined ===
    { id: "guilloche_waves", name: "Guilloché Waves", desc: "Phase-modulated engine-turned wave sheets — classic pocket-watch sweep lines undulating, R=Metallic", category: "Precision & Guilloché", defaults: { x_freq: 60.0, y_mod_freq: 8.0, amplitude: 0.15 } },
    { id: "guilloche_sunray", name: "Guilloché Sunray", desc: "Engine-turned sunray — radial lines + concentric rings polar cross-hatch, pocket-watch dial character, R=Metallic", category: "Precision & Guilloché", defaults: { n_rays: 72, ring_freq: 20.0, ray_fade: 0.6 } },
    { id: "guilloche_moire_eng", name: "Guilloché Moiré", desc: "Two offset concentric ring systems beating into flowing moiré ellipses, R=Metallic", category: "Precision & Guilloché", defaults: { freq: 30.0, offset_frac: 0.15 } },
    { id: "knurl_diamond", name: "Knurl Diamond", desc: "Diamond knurl — crossed diagonal sin lines, raised diamond peaks at both-high intersections, G=Roughness + R=Metallic", category: "Precision & Guilloché", defaults: { frequency: 30.0, angle_deg: 45.0 } },
    { id: "edm_dimple", name: "EDM Dimple", desc: "EDM dimple texture — hex-packed spherical craters, bright rim, dark pit — electrical discharge machining, G=Roughness + R=Metallic", category: "Precision & Guilloché", defaults: { spacing: 12, dimple_radius_frac: 0.4 } },
    // --- PRIORITY 2 BATCH D: Carbon Fiber & Industrial Weave (102-113) ---
    { id: "spec_carbon_2x2_twill", name: "Carbon 2×2 Twill", desc: "Standard 2×2 twill carbon fiber — diagonal ±45° tow families, over-2/under-2 interlace, sharp metallic peaks at tow crowns", category: "Carbon & Composite Weave" },
    { id: "spec_carbon_3k_fine", name: "Carbon 3K Fine", desc: "Fine 3K carbon (3000 filament tow) — high-frequency ±45° twill with narrow Gaussian tow crowns, aerospace small-weave look", category: "Carbon & Composite Weave" },
    { id: "spec_carbon_forged", name: "Carbon Forged", desc: "Forged carbon (random short-fiber SMC) — random overlapping strand segments at all angles, marbled metallic pattern, NOT a regular weave", category: "Carbon & Composite Weave" },
    { id: "spec_carbon_wet_layup", name: "Carbon Wet Layup", desc: "Wet layup carbon — fiber weave shows through thick resin layer, Gaussian-blurred soft metallic peaks, resin-rich gloss", category: "Carbon & Composite Weave" },
    { id: "spec_kevlar_weave", name: "Kevlar Weave", desc: "Kevlar/aramid fiber weave — plain-weave geometry with matte satin sheen, silky micro-texture, moderate interlace roughness", category: "Carbon & Composite Weave" },
    { id: "spec_fiberglass_chopped", name: "Fiberglass Chopped", desc: "Chopped strand fiberglass mat — random clustered glass strands, orientation-weighted specular (vertical fibers most specular), non-woven", category: "Carbon & Composite Weave" },
    { id: "spec_mesh_perforated", name: "Mesh Perforated", desc: "Perforated metal mesh — regular circular holes with smooth radial transition, high metallic between perforations, R=0 at hole centers", category: "Carbon & Composite Weave" },
    { id: "spec_expanded_metal", name: "Expanded Metal", desc: "Expanded metal mesh — rotated diamond-pattern openings from slitting/stretching sheet, high metallic wire edges, open diamond interior", category: "Carbon & Composite Weave" },
    // --- PRIORITY 2 BATCH E: 🔵 Clearcoat Behavior (114–123) ---
    { id: "cc_panel_pool", name: "CC Panel Pool", desc: "Clearcoat pooling — gravity-settled extra-clear in panel low spots, scattered Gaussian gloss pools, B=Clearcoat", category: "Clearcoat & Coating", defaults: { num_pools: 12, pool_spread: 0.18 } },
    { id: "cc_overspray_halo", name: "CC Overspray Halo", desc: "Overspray halo — spray gun edge mist, ring of thin/rough clearcoat at spray boundary, B=Clearcoat", category: "Clearcoat & Coating", defaults: { num_halos: 6, halo_radius: 0.22 } },
    { id: "cc_wet_zone", name: "CC Wet Zone", desc: "Wet zones — unleveled clearcoat blob patches at higher gloss, organic FBM-thresholded dark areas, B=Clearcoat", category: "Clearcoat & Coating", defaults: { num_zones: 5 } },
    { id: "cc_panel_fade", name: "CC Panel Fade", desc: "Panel fade — clearcoat thickness gradient across panel from spray angle, one side gloss one side dull, B=Clearcoat", category: "Clearcoat & Coating", defaults: { fade_direction: 0.0, noise_warp: 0.06 } },
    // --- PRIORITY 2 BATCH C: Worn, Patina & Weathering (90-101) ---
    { id: "spec_galvanic_corrosion", name: "Galvanic Corrosion", desc: "Voronoi two-metal partition — roughness spikes and metallic drops at dissimilar metal contact seams", category: "Weather, Wear & Track" },
    { id: "spec_stress_fractures", name: "Stress Fractures", desc: "Metal fatigue crack tree grown along FBM gradients — crack pixels near-zero metallic, max roughness", category: "Weather, Wear & Track" },
    { id: "spec_sandblast_strip", name: "Sandblast Strip", desc: "FBM blob-shaped sandblasted zones — bare metal roughness adjacent to unblasted painted surfaces", category: "Weather, Wear & Track" },
    // --- PRIORITY 2 BATCH E: Geometric & Architectural (124–135) ---
    { id: "spec_hammered_dimple", name: "Hammered Dimple", desc: "Hex-grid hemispherical hammer dimples — cos(r/radius×π/2) profile peaks at rim edge (angled surface), low at dome center, R=Metallic", category: "Structure & Geometry", defaults: { dimple_spacing: 18.0 } },
    { id: "spec_architectural_grid", name: "Architectural Grid", desc: "Curtain wall grid — polished aluminum frame (high metallic) surrounding low-metallic glass panels, min(fmod) frame-proximity approach, 10% frame width, R=Metallic", category: "Structure & Geometry", defaults: { cell_size: 40.0, frame_frac: 0.10 } },
    { id: "spec_brick_mortar", name: "Brick Mortar", desc: "Running-bond brickwork — near-zero metallic clay brick faces with moderate metallic cement mortar joints, 0.5-offset stagger per course, R=Metallic + G=Roughness", category: "Structure & Geometry", defaults: { brick_h: 16.0, brick_w: 36.0, mortar_frac: 0.08 } },
    // --- PRIORITY 2 BATCH F: Natural & Organic ---
    { id: "spec_snake_scales", name: "Snake Scales", desc: "Reptile scale array — elongated oval scales in offset rows, specular peak near scale center-top (convex surface), lower metallic at scale edges, overlap regions roughness spike, elliptical distance function, R=Metallic + G=Roughness", category: "Organic & Natural", defaults: { scale_w: 20.0, scale_h: 14.0 } },
    { id: "spec_fish_scales", name: "Fish Scales", desc: "Fish scale array — circular overlapping scales, INVERTED radial metallic gradient vs snake scales: higher metallic at scale rim + lower at center (iridescent armored look), radial shimmer rings, R=Metallic", category: "Organic & Natural", defaults: { scale_r: 16.0 } },
    { id: "spec_terrain_erosion", name: "Terrain Erosion", desc: "Eroded terrain topology — multi-octave domain-warped FBM, ridgetops lower roughness (wind-polished rock), valley floors higher roughness (sediment), cliff faces high metallic (fresh exposed rock), gradient magnitude as roughness proxy, R=Metallic + G=Roughness", category: "Organic & Natural", defaults: { octaves: 7 } },
    // --- PRIORITY 2 BATCH G: Lighting & Optical Effects (136-147) ---
    { id: "spec_fresnel_gradient", name: "Fresnel Gradient", desc: "Fresnel reflectivity gradient — Schlick approximation drives edge-brightening (glancing angle = max metallic), center near-normal incidence = moderate metallic, FBM perturbs edge boundary, R=Metallic + G=Roughness", category: "Optical & Interference", defaults: { edge_metallic: 0.92, center_metallic: 0.38 } },
    { id: "holo_prism_shift", name: "Holo Prism Shift", desc: "Holographic prism flecks 4-10 px with per-fleck rainbow CC sweep + 6-12 angular facet cluster zones 16-22 px for view-angle shift, M=Metallic + G=Roughness + B=Clearcoat", category: "Holographic & Color-Shift", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_retroreflective", name: "Retroreflective", desc: "Retroreflective surface (road signs/safety vest) — staggered Gaussian corner-cube grid with microsphere fill between, FBM bead-coat variation, characteristic sparkly grid of retroreflective materials, R=Metallic", category: "Optical & Interference", defaults: { grid_spacing: 22.0, microsphere_fill: 0.55 } },
    { id: "snake_scale_diamond", name: "Snake Scale Diamond", desc: "Diamond-tessellated 10-16 px snake scales staggered with crown highlight + dark base + iridescent CC centerline + 4-8 enlarged king-scale zones 16-22 px with dramatic chroma split, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_iridescent_film", name: "Iridescent Film", desc: "Thin-film iridescence — FBM-driven film thickness with sin²(thickness × band_freq × π) interference banding, smooth film surface near-zero roughness throughout, oily shimmer pattern, R=Metallic", category: "Optical & Interference", defaults: { film_octaves: 5, band_freq: 12.0 } },
    { id: "spec_anisotropic_radial", name: "Anisotropic Radial", desc: "Radial anisotropic star pattern — sin(atan2 × N/2)^p formula creates sharp angular metallic bands from disc center, FBM run-out perturbation, distinct from brushed_radial smooth gradient, R=Metallic", category: "Optical & Interference", defaults: { num_segments: 24, star_power: 2.0 } },
    { id: "spec_chromatic_aberration", name: "Chromatic Aberration", desc: "Lens chromatic aberration — inner zone uniform spec, outer zones alternating metallic fringes at multi-frequency period growing with radius (CA magnitude grows outward), FBM field-curvature distortion, R=Metallic", category: "Optical & Interference", defaults: { inner_radius: 0.30, fringe_period: 0.04 } },
    // --- PRIORITY 2 BATCH H: Surface Treatments (148-155) ---
    { id: "spec_anodized_texture", name: "Anodized Texture", desc: "Anodized aluminum nanoporous oxide layer — hexagonal three-cosine pore grid (100+ pores/unit), high metallic oxide inter-pore matrix, low metallic pore centers, moderate roughness (G: 30-60), glossy clearcoat (B: 20-40), R=Metallic + G=Roughness", category: "Surface & Spray Texture", defaults: { pore_density: 105.0, metallic_base: 170 } },
    { id: "spec_pvd_coating", name: "PVD Coating", desc: "Physical Vapor Deposition nodule texture — ultra-fine Voronoi (80+ cells/unit) nucleation sites, very high metallic 180-240/255 throughout, near-zero roughness G: 10-30/255, minimal grain boundary dip, TiN/TiAlN characteristic smooth highly-reflective surface, R=Metallic + G=Roughness", category: "Surface & Spray Texture", defaults: { cell_density: 80.0 } },
    { id: "spec_laser_etched", name: "Laser Etched", desc: "Laser-etched pattern on polished surface — sharp step-function boundary (FBM-wobbled edge) between etched border strips (G=200+ rough, R=40 oxidized) and polished tile centers (G=10, R=200 mirror), no gradual transition, R=Metallic + G=Roughness", category: "Surface & Spray Texture", defaults: { tile_size: 32.0, border_frac: 0.18 } },
    // --- PRIORITY 2 BATCH I: Specialty & Exotic (156-163) ---
    { id: "spec_liquid_metal", name: "Liquid Metal", desc: "Mercury / liquid metal surface — near-perfect reflectivity (R: 240-255, G: 2-8, B: 16-18) with two-frequency gravity wave interference pattern, standing wave beating creates subtle metallic modulation, very low amplitude (0.04), distinguishes from flat chrome, R=Metallic dominant", category: "Exotic & Kinetic", defaults: { wave1_freq: 0.8, wave2_freq: 1.3, amplitude: 0.04 } },
    { id: "spec_chameleon_flake", name: "Chameleon Flake", desc: "ChromaFlair / chameleon flake spec — medium-scale Voronoi (20-40/unit), each flake random metallic value (160-220/255) by hash, random-metallic mosaic pattern, inter-flake boundary roughness spike, genuine ChromaFlair spec signature, R=Metallic + G=Roughness", category: "Exotic & Kinetic", defaults: { cell_density: 28.0, metallic_base: 190 } },
    { id: "spec_damascus_steel_spec", name: "Damascus Steel Spec", desc: "Damascus steel surface micro-topography spec — flow-field distorted layer bands, high-carbon bands (R=190/255 metallic, G=20/255 smooth, polishes bright), low-carbon bands (R=120/255, G=60/255 slightly rougher, chemical etch reveals), sinuous watered-silk FBM warp, different from paint damascus_steel, R=Metallic + G=Roughness", category: "Exotic & Kinetic", defaults: { num_layers: 18, warp_strength: 4.5 } },
    // --- RACING & AUTOMOTIVE (v6.2) ---
    { id: "heat_discoloration", name: "Heat Discoloration", desc: "Heat-treated metal color zones — concentric temperature gradient bands like exhaust manifold bluing or weld heat-affected zones with oxide micro-texture", category: "Racing & Livery Story", defaults: { num_zones: 5, max_radius: 0.2 } },
    { id: "salt_spray_corrosion", name: "Salt Spray Corrosion", desc: "Fine salt-air corrosion pitting — coastal marine environment surface degradation with clustered micro-pits, halo staining, and salt-exposure base roughness", category: "Racing & Livery Story", defaults: { pit_density: 0.015, cluster_count: 15 } },
    // --- v6.2.x SPONSOR & VINYL ---
    { id: "vinyl_stretched", name: "Vinyl Stretched", desc: "Vinyl wrap stretched over a curve — directional micro-streaks along the stretch axis with periodic ridges where film thinned and thickened, G=Roughness", category: "Racing & Livery Story", defaults: { stretch_freq: 18.0, stretch_amp: 0.30 } },
    // --- v6.2.x RACE WEAR ---
    // --- v6.2.x PREMIUM FINISHES ---
    { id: "mother_of_pearl_inlay", name: "Mother of Pearl Inlay", desc: "Nacre inlay shards — Voronoi cells each with their own iridescence phase and band-axis direction so adjacent shards shimmer at different angles, R=Metallic", category: "Sparkle & Micro-Metal", defaults: { num_shards: 140, shimmer_freq: 14.0 } },
    { id: "anodized_rainbow", name: "Anodized Rainbow", desc: "Anodized titanium / niobium oxide rainbow bands — smooth low-roughness surface with FBM-warped interference banding from oxide thickness gradient, R=Metallic", category: "Sparkle & Micro-Metal", defaults: { band_freq: 10.0, axis_jitter: 0.10 } },
    // --- v6.2.x COLOR-SHIFT VARIANTS ---
    { id: "crypt_brick", name: "Crypt Brick", desc: "Heavy stone-block masonry — cold-grey blocks 18-30 px wide x 10-16 px tall in staggered courses with deep dark mortar seams + 6-10 hero cracked/chipped blocks showing bare stone + subtle moss-green CC accent at base, M=Metallic + G=Roughness + B=Clearcoat", category: "Gothic & Horror", defaults: {}, defaultChannels: "MRC" },
    { id: "brushed_linear_cool", name: "Brushed Linear (Cool)", desc: "Cool-toned brushed_linear — crisper higher-frequency grain with boosted contrast, suits steel/titanium/chrome finishes, G=Roughness", category: "Directional Metal & Brush", defaults: { frequency: 92.0 } },
    // --- v6.2.y RACE HERITAGE ---
    { id: "checker_flag_subtle", name: "Checker Flag Subtle", desc: "Faint warped checkered-flag specular ghost — soft-edged alternating cells with a gentle FBM wobble so the grid never sits perfectly straight, R=Metallic", category: "Racing & Livery Story", defaults: { squares: 18, warp: 0.006 } },
    // --- v6.2.y MECHANICAL ---
    // --- v6.2.y WEATHER & TRACK ---
    { id: "morning_dew_fog", name: "Morning Dew Fog", desc: "Soft top-biased misted haze with very fine dewlet micro-bumps — cold-morning damp layer, B=Clearcoat", category: "Weather, Wear & Track", defaults: { fog_density: 0.55 } },
    // --- v6.2.y ARTISTIC ---
    // R6 RACING-PIVOT V3 (2026-05-26): airbrush_gradient_bloom ALIASED to engine_turn_starburst.
    // Owner: "Just don't like it. Turn this into an ENGINE TURN type finish of some sort".
    { id: "airbrush_gradient_bloom", name: "Engine-Turn Starburst", desc: "Explosive radial-arc cluster — 30-50 radiation points each emitting 8-14 fly-cut arcs fanning 12-22 px with bright leading-edge crescents on polished billet steel + 6-10 hero oversized 24-32 px starburst clusters, M=Metallic + G=Roughness + B=Clearcoat", category: "Engine-Turn & Machined", defaults: {}, defaultChannels: "MRC" },
    { id: "halftone_print", name: "Halftone Print", desc: "Regular halftone grid with per-cell radius modulated by FBM tonal map — pop-art / comic halftone dots, R=Metallic", category: "Artistic & Abstract", defaults: { cell: 12, dot_max: 0.45 } },
    // --- ABSTRACT ART (17 patterns) — art-history-inspired spec overlays ---
    { id: "ember_field", name: "Ember Field", desc: "200-400 glowing embers 3-8 px with hot bright CC cores + cooling outer halos, vertical heat-rise smear, + 8-14 burning coal hot-spots 10-18 px with extra-bright cores, M=Metallic + G=Roughness + B=Clearcoat", category: "Fire & Heat", defaults: {}, defaultChannels: "MRC" },
    { id: "pangolin_armor", name: "Pangolin Armor", desc: "Heavy overlapping pangolin armor scales — bronze/copper spearhead plates 14-22 px wide x 10-16 px tall packed in directional pinecone rows + sharp keel ridge per plate + 8-14 hero 22-30 px lead scales with extra-bright keels, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "viper_pit_hex", name: "Viper Pit Hex", desc: "Pit-viper hex-diamond pattern — angular 10-16 px hex shapes with sharp corners packed dense on cold dark-olive viper-venom substrate + 6-10 hero 18-24 px fang hexes with bright fang-yellow vertical keel ridges, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "samhain_ritual", name: "Samhain Ritual", desc: "Reference-backed occult fire ritual overlay - candle arcs, ceremonial geometry, ember leafwork, bone-gold filigree and hot ash ridges remapped into distinct M/R/CC spec response", category: "Gothic & Horror", defaults: {}, defaultChannels: "MRC" },
    { id: "ouija_mystic", name: "Ouija Mystic", desc: "Reference-backed spirit-board glamour overlay - planchette shields, moon phases, compass eyes, purple filigree and antique-gold linework remapped into dynamic M/R/CC spec response", category: "Gothic & Horror", defaults: {}, defaultChannels: "MRC" },
    { id: "king_cobra_coil", name: "King Cobra Coil", desc: "Reference-backed dangerous animal overlay - gilded cobra scales, fangs, eyes, and black-green armor linework remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "widow_web_venom", name: "Widow Web Venom", desc: "Reference-backed dangerous animal overlay - red-black widow web panels, silk radial geometry, glass venom beads, and chromium fang accents remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "tiger_fang_fracture", name: "Tiger Fang Fracture", desc: "Reference-backed dangerous animal overlay - tiger-stripe fracture shards, claw flashes, amber predator eyes, and torn black enamel remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "scorpion_ember_hex", name: "Scorpion Ember Hex", desc: "Reference-backed dangerous animal overlay - scorched scorpion hooks, ember hex armor, molten cracks, and segmented sting plates remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "hornet_swarm_static", name: "Hornet Swarm Static", desc: "Reference-backed dangerous animal overlay - hornet bodies, wing facets, yellow-black warning geometry, and blue static arcs remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "croc_delta_armor", name: "Croc Delta Armor", desc: "Reference-backed dangerous animal overlay - swamp crocodile armor plates, bone teeth, dark water gloss, and river-patina scale texture remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "panther_shadow_claw", name: "Panther Shadow Claw", desc: "Reference-backed dangerous animal overlay - midnight panther fur, purple claw blades, leopard ghost spots, and cyan eye glints remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "piranha_frenzy_current", name: "Piranha Frenzy Current", desc: "Reference-backed dangerous animal overlay - crimson piranha eyes, tooth rows, scale flashes, and turbulent teal current streaks remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "jellyshock_drift", name: "Jellyshock Drift", desc: "Reference-backed dangerous animal overlay - neon jellyfish bells, electrical tendrils, translucent ocean mesh, and pink-blue bio-glow remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "sharkbite_riptide", name: "Sharkbite Riptide", desc: "Reference-backed dangerous animal overlay - shark teeth, riptide foam, steel-blue fin blades, and saltwater scale plates remapped into dynamic M/R/CC spec response", category: "Dangerous Animals", defaults: {}, defaultChannels: "MRC" },
    { id: "bayou_hex_burlap", name: "Bayou Hex Burlap", desc: "Reference-backed voodoo overlay - moss-dark burlap hex weave, stitched bone knots, root bindings, and swamp grit remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "candle_wax_veve", name: "Candle Wax Veve", desc: "Reference-backed voodoo overlay - raised candle-wax veve lines, amber drips, bead nodes, and scratched altar stone remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "pins_and_thread", name: "Pins & Thread", desc: "Reference-backed voodoo overlay - black cloth patches, red and gold stitch glyphs, pins, pearls, and stitched charm grids remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "swamp_charm_patina", name: "Swamp Charm Patina", desc: "Reference-backed voodoo overlay - oxidized charms, shells, bones, skulls, shields, and green patina relics remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "mojo_bag_grain", name: "Mojo Bag Grain", desc: "Reference-backed voodoo overlay - leather mojo-bag quilting, tied pouches, ritual knots, scratched symbols, and bronze dust remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "midnight_gris_gris", name: "Midnight Gris-Gris", desc: "Reference-backed voodoo overlay - midnight gris-gris scatter, purple crystals, bones, handprints, relic beads, and occult debris remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "bayou_smoke_script", name: "Bayou Smoke Script", desc: "Reference-backed voodoo overlay - blue-purple bayou smoke columns, gold spirit-script circles, skull marks, and glass bubbles remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "coffin_nail_rust", name: "Coffin Nail Rust", desc: "Reference-backed voodoo overlay - blackened coffin nails, X-stamped rivets, rust pits, tiny skull talismans, and dirty bronze scars remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "root_doctor_copper", name: "Root Doctor Copper", desc: "Reference-backed voodoo overlay - copper root tendrils, masks, bottles, bone charms, patina enamel, and dense ritual icons remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "spanish_moss_static", name: "Spanish Moss Static", desc: "Reference-backed voodoo overlay - hanging Spanish moss, pale thread filigree, dew pearls, fog wisps, and swamp-lace sigils remapped into dynamic M/R/CC spec response", category: "Voodoo Inspired", defaults: {}, defaultChannels: "MRC" },
    { id: "seigaiha_chrome", name: "Seigaiha Chrome", desc: "Reference-backed Rising Sun Spec overlay - polished blue seigaiha wave geometry, chrome arcs, floral caps, and bead highlights remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "sakura_static", name: "Sakura Static", desc: "Reference-backed Rising Sun Spec overlay - sakura blossoms, pink gloss petals, gold linework, and soft star-grid texture remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "kintsugi_rift", name: "Kintsugi Rift", desc: "Reference-backed Rising Sun Spec overlay - navy ceramic shards, ivory panels, repaired gold fractures, and fine floral inlay remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "oni_veil_mosaic", name: "Oni Veil Mosaic", desc: "Reference-backed Rising Sun Spec overlay - dark oni masks, purple-teal veil shapes, red eye glints, and shadow floral mosaics remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "shogun_scale_brocade", name: "Shogun Scale Brocade", desc: "Reference-backed Rising Sun Spec overlay - shogun armor plates, red cord brocade, gold crests, and layered scale panels remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "kyoto_lantern_filigree", name: "Kyoto Lantern Filigree", desc: "Reference-backed Rising Sun Spec overlay - Kyoto lanterns, tassels, floral filigree, teal lacquer, and warm gold scrollwork remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "bonsai_drift_circuit", name: "Bonsai Drift Circuit", desc: "Reference-backed Rising Sun Spec overlay - bonsai branch flow, nature circuit linework, moss greens, copper traces, and circular brush currents remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "fuji_frost_crest", name: "Fuji Frost Crest", desc: "Reference-backed Rising Sun Spec overlay - icy Fuji mountain crests, snowflake geometry, silver-blue peaks, and frosted cloud scrolls remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "rising_sun_prismwave", name: "Rising Sun Prismwave", desc: "Reference-backed Rising Sun Spec overlay - red-gold sunburst fans, prism waves, blue accent arcs, and dense gold pattern sparkle remapped into dynamic M/R/CC spec response", category: "Rising Sun Spec", defaults: {}, defaultChannels: "MRC" },
    { id: "shark_denticle", name: "Shark Denticle", desc: "Drag-reducing shark-skin denticle pattern — hundreds of small tooth-shaped 8-14 px scales all oriented in the same flow direction with bright keel ridge highlights + 12-20 hero 16-22 px lead denticles with extra-bright keels, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "jaguar_rosette", name: "Jaguar Rosette", desc: "Jaguar coat rosette markings — 90-200 ring clusters of 3-5 dark spots around a darker center spot on warm tan-gold base + 8-12 hero 22-28 px rosettes with bright tan rim and dramatic dark spots, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "alligator_hide", name: "Alligator Hide", desc: "Fine 8-14 px rectangular leathery plates packed dense, deep dark M=low fissure cracks between plates, per-plate independent M/R/CC, sub-plate 2-3 px micro-pitting, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "dragon_scale_macro", name: "Dragon Scale Macro", desc: "Armored overlapping 14-26 px pentagon/hex hybrid dragon plates with M=high spine ridge + dark crevice + CC iridescent edge highlight + 12-20 hero spike-crest plates with extra-bright cresting, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    { id: "raptor_feather", name: "Raptor Feather", desc: "Overlapping raptor flight feathers — vertical quill segments 6-14 px tall x 3-6 px wide with bright central shaft + barb spread + cohesive raven-black/warm-brown/bronze racing palette + 8-15 hero primary feathers 18-24 px, M=Metallic + G=Roughness + B=Clearcoat", category: "Predator Skins", defaults: {}, defaultChannels: "MRC" },
    // === SPB DEFINITIVE SPEC OVERLAY REPLACEMENTS 2026-05-29 START ===
    { id: "spec_weld_stack_rainbow", name: "Weld Stack Rainbow", desc: "TIG bead stacks with blue-straw heat tint and crisp bead rims.", category: "Machined & Race Hardware", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_titanium_heat_fishscale", name: "Titanium Heat Fishscale", desc: "Overlapping titanium heat scales with blue, violet, and gold oxide shifts.", category: "Fire, Heat & Exhaust", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_ceramic_brake_sinter", name: "Ceramic Brake Sinter", desc: "Carbon-ceramic rotor pores, swept brake arcs, and hot dust glazing.", category: "Machined & Race Hardware", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_beadlock_bolt_circle", name: "Beadlock Bolt Circle", desc: "Dense beadlock bolt heads, washer rings, and indexed circular rows.", category: "Machined & Race Hardware", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_knurled_socket_grip", name: "Knurled Socket Grip", desc: "Socket-tool diamond knurl and polished peak flecks.", category: "Machined & Race Hardware", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_louvered_aluminum_slot", name: "Louvered Aluminum Slot", desc: "Stamped aluminum louvers with dark slots and bright leading lips.", category: "Machined & Race Hardware", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_carbon_tow_spread", name: "Carbon Tow Spread", desc: "Spread-tow carbon ribbons with rectangular fiber lanes.", category: "Carbon & Composite", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_kevlar_blue_hybrid", name: "Kevlar Blue Hybrid", desc: "Aramid-carbon hybrid weave with satin yellow and blue-black tow crossings.", category: "Carbon & Composite", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_nomex_honeycomb_core", name: "Nomex Honeycomb Core", desc: "Open honeycomb composite core with resin-wet cell edges.", category: "Carbon & Composite", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_prepreg_resin_bleed", name: "Prepreg Resin Bleed", desc: "Prepreg pinholes, resin bleed lines, and glossy trapped clear.", category: "Carbon & Composite", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_braided_hose_sleeve", name: "Braided Hose Sleeve", desc: "Braided stainless and aramid sleeve strands in diagonal over-under rows.", category: "Race Track Materials", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_rubber_tire_cord", name: "Rubber Tire Cord", desc: "Exposed tire cord ribs, rubber scuffs, and satin black worn streaks.", category: "Race Track Materials", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_tar_snake_sealant", name: "Tar Snake Sealant", desc: "Track tar-seal strips with glossy raised asphalt snakes.", category: "Race Track Materials", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_rain_bead_aero", name: "Rain Bead Aero", desc: "Wind-sheared rain beads and short aero trails under clearcoat.", category: "Race Track Materials", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_sharkskin_riblet", name: "Sharkskin Riblet", desc: "Directional shark denticle riblets with tiny keel highlights.", category: "Predator & Animal Armor", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_alligator_scute_plate", name: "Alligator Scute Plate", desc: "Alligator scute armor plates, dark seams, and worn glossy crowns.", category: "Predator & Animal Armor", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_mantis_shrimp_shell", name: "Mantis Shrimp Shell", desc: "Segmented iridescent shell armor with micro ridges.", category: "Predator & Animal Armor", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_armadillo_band_armor", name: "Armadillo Band Armor", desc: "Layered armadillo armor bands with hard ridges and dusty valleys.", category: "Predator & Animal Armor", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_abalone_crack_inlay", name: "Abalone Crack Inlay", desc: "Abalone shard inlay with pearly islands and dark grout.", category: "Cultural & Inlay", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_guilloche_watch_dial", name: "Guilloche Watch Dial", desc: "Fine watch-dial guilloche waves and jeweled engraved cuts.", category: "Engine Turn & Optical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_laser_etched_microbar", name: "Laser Etched Microbar", desc: "Laser-etched micro bars, registration ticks, and satin burn marks.", category: "Engine Turn & Optical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_circuit_solder_mask", name: "Circuit Solder Mask", desc: "PCB traces, solder pads, via rings, and gloss mask islands.", category: "Engine Turn & Optical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_exhaust_soot_gradient", name: "Exhaust Soot Gradient", desc: "Layered exhaust soot, oxide specks, and brushed heat flow.", category: "Fire, Heat & Exhaust", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_flame_lapped_clearcoat", name: "Flame Lapped Clearcoat", desc: "Kustom flame-lap clearcoat edges with glossy hotrod overlap ridges.", category: "Fire, Heat & Exhaust", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_burnt_clutch_dust", name: "Burnt Clutch Dust", desc: "Copper clutch dust, hot spots, and scorched friction streaks.", category: "Fire, Heat & Exhaust", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_ice_frost_feather", name: "Ice Frost Feather", desc: "Frost fern crystals with sharp clearcoat feather branches.", category: "Weathered Physical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_mud_crackle_dried", name: "Dried Mud Crackle", desc: "Dried mud plates with clean cracks and dusty high shelves.", category: "Weathered Physical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_red_clay_roost", name: "Red Clay Roost", desc: "Red-clay roost flecks and angled dirt sling streaks.", category: "Weathered Physical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_fuel_stain_evap_ring", name: "Fuel Stain Evap Ring", desc: "Fuel evaporated rings, ghost halos, and clean solvent edge marks.", category: "Liquid & Clearcoat", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_polished_swirl_compound", name: "Hay Straw", desc: "Dry woven straw and hay-fiber strands with a matte, fibrous sheen.", category: "Liquid & Clearcoat", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_sandblasted_mask_edge", name: "Sandblasted Mask Edge", desc: "Masked blast transitions, satin eroded grain, and sharp tape borders.", category: "Weathered Physical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_anodized_hex_fade", name: "Anodized Hex Fade", desc: "Anodized hex panels with electric fade and polished cell lips.", category: "Engine Turn & Optical", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_waterjet_cut_edge", name: "Waterjet Cut Edge", desc: "Waterjet kerf striations, garnet scoring, and cut-edge shimmer.", category: "Machined & Race Hardware", defaults: {}, defaultChannels: "MRC" },
    // === SPB DEFINITIVE SPEC OVERLAY REPLACEMENTS 2026-05-29 END ===
    // === LET FREEDOM RING SPEC OVERLAYS 2026-06-09 START === (UV-agnostic patriotic drop)
    { id: "spec_lfr_starfield_scatter", name: "Liberty Starfield Scatter", desc: "Omnidirectional 5-point star scatter — bright glint cores, signed twinkle halos, and a faint constellation web.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_corridor_sheen", name: "Stripe Corridor Sheen", desc: "Multi-angle anisotropic sheen corridors — stripe feel at every rotation with cross-lane brush grain.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_firework_radial", name: "Firework Burst Radial", desc: "Scattered radial firework bursts — bright spokes, expanding shock rings, and ember-trail glow coronas.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_brocade_relief", name: "Eagle Brocade Relief", desc: "Interlocking feather-scale brocade at varying angles with barb grain and a damask diamond overlay.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_liberty_colorflip", name: "Liberty Color-Flip", desc: "Angle-reactive tricolor flip — three offset interference phase fields flash red-to-white-to-blue as light sweeps.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_anisotropic_drift", name: "Brushed Steel Drift", desc: "Curling multi-directional brushed metal — flowing highlights, perpendicular micro-scratches, satin sheen pools.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_sparkler_embers", name: "Sparkler Ember Dust", desc: "Dense hot micro-sparks with radiating jets, drifting soot streaks, and warm glow blooms.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_torch_flicker", name: "Liberty Torch Flicker", desc: "Living flame-tongue flicker — bright cores, heat-shimmer roughness warp, ember glow pooling at lobe bases.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_capitol_veins", name: "Capitol Marble Veins", desc: "Branching polished marble veins with micro-fracture grain and translucent calcite depth.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    { id: "spec_lfr_canyon_bevel", name: "Canyon Relief Bevel", desc: "Faceted canyon relief — per-facet bevel highlights, valley-edge roughness, and ambient depth pools.", category: "Let Freedom Ring", defaults: {}, defaultChannels: "MRC" },
    // === LET FREEDOM RING SPEC OVERLAYS 2026-06-09 END ===
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
// 2026-06-08 audit: hidden — no engine renderer (would crash on click).
// The 5 v6.2.z MONOLITHIC_WAVE sub-tab sections ("Racing Livery Styles",
// "Vintage Styles", "Fantasy / Sci-Fi", "Weathered", "Special Effects") held
// exactly the 30 dead wave ids that have no backend renderer (ValueError
// 'Unknown base' on click). Sections removed so the empty sub-tabs disappear;
// the ids are also stripped via REMOVED_SPECIAL_IDS above. This object stays a
// valid (empty) map — user-imports.js / guest-designers.js add keys at runtime.
const MONOLITHIC_GROUPS = {};

// =============================================================================
// SPEC PATTERN GROUPS — sub-tab navigation for SPEC_PATTERNS picker
// 2026-05-17: Consolidated 27+ legacy tabs -> 14 review lanes (SPB_SPEC_PATTERNS_ATLAS).
// =============================================================================
const SPEC_PATTERN_GROUPS = {
    "Sparkle & Micro-Metal": [
        "pearl_micro",
        "gold_flake",
        "holographic_flake",
        "metallic_sand",
        "mother_of_pearl_inlay",
        "prismatic_shatter",
        "stardust_fine",
        "galaxy_swirl",
    ],
    "Optical & Interference": [
        "spec_chromatic_aberration",
        "spec_diffraction_grating_cd",
        "spec_fresnel_gradient",
        "spec_iridescent_film",
        "spec_retroreflective",
        "wave_ripple",
        "anodized_rainbow",
    ],
    "Directional Metal & Brush": [
        "brushed_cross",
        "brushed_diagonal",
        "brushed_linear_cool",
        "spec_anisotropic_radial",
    ],
    "Carbon & Composite Weave": [
        "spec_carbon_2x2_twill",
        "spec_carbon_3k_fine",
        "spec_carbon_forged",
        "spec_carbon_wet_layup",
        "spec_expanded_metal",
        "spec_fiberglass_chopped",
        "spec_kevlar_weave",
        "spec_mesh_perforated",
        "spec_carbon_weave",
    ],
    "Clearcoat & Coating": [
        "cc_overspray_halo",
        "cc_panel_fade",
        "cc_panel_pool",
        "cc_wet_zone",
    ],
    "Structure & Geometry": [
        "banded_rows",
        "chevron_bands",
        "gradient_bands",
        "hex_cells",
        "panel_zones",
        "spec_architectural_grid",
        "spec_brick_mortar",
        "spec_hammered_dimple",
        "wave_bands",
        "voronoi_fracture",
    ],
    "Surface & Spray Texture": [
        "pebble_grain",
        "spec_anodized_texture",
        "spec_laser_etched",
        "spec_pvd_coating",
    ],
    "Organic & Natural": [
        "lava_crack",
        "spec_fish_scales",
        "spec_snake_scales",
        "spec_terrain_erosion",
    ],
    "Weather, Wear & Track": [
        "crackle_network",
        "morning_dew_fog",
        "spec_galvanic_corrosion",
        "spec_sandblast_strip",
        "spec_stress_fractures",
        "salt_spray_corrosion",
    ],
    "Racing & Livery Story": [
        "checker_flag_subtle",
        "heat_discoloration",
        "vinyl_stretched",
    ],
    "Mechanical & Industrial": [
        "sparkle_shattered",
    ],
    "Exotic & Kinetic": [
        "spec_chameleon_flake",
        "spec_damascus_steel_spec",
        "spec_liquid_metal",
    ],
    "Precision & Guilloché": [
        "edm_dimple",
        "guilloche_moire_eng",
        "guilloche_sunray",
        "guilloche_waves",
        "knurl_diamond",
        "diamond_lattice",
    ],
    "Artistic & Abstract": [
        "halftone_print",
    ],
    "Predator Skins": [
        "alligator_hide",
        "dragon_scale_macro",
        "jaguar_rosette",
        "pangolin_armor",
        "raptor_feather",
        "shark_denticle",
        "snake_scale_diamond",
        "viper_pit_hex",
    ],
    "Dangerous Animals": [
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
    ],
    "Gothic & Horror": [
        "brushed_sparkle",
        "crypt_brick",
        "ouija_mystic",
        "samhain_ritual",
    ],
    "Voodoo Inspired": [
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
    ],
    "Rising Sun Spec": [
        "seigaiha_chrome",
        "sakura_static",
        "kintsugi_rift",
        "oni_veil_mosaic",
        "shogun_scale_brocade",
        "kyoto_lantern_filigree",
        "bonsai_drift_circuit",
        "fuji_frost_crest",
        "rising_sun_prismwave",
    ],
    "Engine-Turn & Machined": [
        "airbrush_gradient_bloom",
    ],
    "Fire & Heat": [
        "ember_field",
    ],
    "Holographic & Color-Shift": [
        "holo_prism_shift",
    ],
    "Source Pattern Plates": [
        "spec_holographic_oil_circuit", "spec_black_emboss_mandala", "spec_graphite_cross_lattice", "spec_marble_flow_pearl",
        "spec_acid_carbon_mesh", "spec_noir_houndstooth_star", "spec_hazard_chevron_weave", "spec_burn_hole_mesh",
        "spec_teal_hex_haze", "spec_shadow_diamond_mesh", "spec_talavera_tile_riot", "spec_green_plasma_vein",
        "spec_neon_fracture_net", "spec_pink_checker_carbon", "spec_red_herringbone_heat", "spec_chrome_oval_chain",
        "spec_terracotta_ceramic_grid", "spec_gunmetal_geo_tessellation", "spec_tokyo_script_textile", "spec_lime_pixel_confetti",
        "spec_psychedelic_floral_spin", "spec_ice_facet_shatter", "spec_ember_circuit_maze", "spec_blue_polygon_shatter",
    ],
    "Definitive Spec Replacements": [
        "spec_weld_stack_rainbow", "spec_titanium_heat_fishscale", "spec_ceramic_brake_sinter", "spec_beadlock_bolt_circle", "spec_knurled_socket_grip",
        "spec_louvered_aluminum_slot", "spec_carbon_tow_spread", "spec_kevlar_blue_hybrid",
        "spec_nomex_honeycomb_core", "spec_prepreg_resin_bleed", "spec_braided_hose_sleeve",
        "spec_rubber_tire_cord", "spec_tar_snake_sealant", "spec_rain_bead_aero",
        "spec_sharkskin_riblet", "spec_alligator_scute_plate", "spec_mantis_shrimp_shell",
        "spec_armadillo_band_armor", "spec_abalone_crack_inlay",
        "spec_guilloche_watch_dial", "spec_laser_etched_microbar", "spec_circuit_solder_mask", "spec_exhaust_soot_gradient", "spec_flame_lapped_clearcoat", "spec_burnt_clutch_dust",
        "spec_ice_frost_feather", "spec_mud_crackle_dried", "spec_red_clay_roost", "spec_fuel_stain_evap_ring", "spec_polished_swirl_compound",
        "spec_sandblasted_mask_edge", "spec_anodized_hex_fade", "spec_waterjet_cut_edge",
    ],
    "Let Freedom Ring": [
        "spec_lfr_starfield_scatter", "spec_lfr_corridor_sheen", "spec_lfr_firework_radial",
        "spec_lfr_brocade_relief", "spec_lfr_liberty_colorflip", "spec_lfr_anisotropic_drift",
        "spec_lfr_sparkler_embers", "spec_lfr_torch_flicker", "spec_lfr_capitol_veins",
        "spec_lfr_canyon_bevel",
    ],
};

// Explicit picker tab order (Object.keys order is reliable in modern engines; this documents intent).
const SPEC_PATTERN_GROUP_ORDER = ["Sparkle & Micro-Metal", "Optical & Interference", "Directional Metal & Brush", "Carbon & Composite Weave", "Clearcoat & Coating", "Structure & Geometry", "Surface & Spray Texture", "Organic & Natural", "Weather, Wear & Track", "Racing & Livery Story", "Mechanical & Industrial", "Exotic & Kinetic", "Precision & Guilloché", "Artistic & Abstract", "Predator Skins", "Dangerous Animals", "Gothic & Horror", "Voodoo Inspired", "Rising Sun Spec", "Engine-Turn & Machined", "Fire & Heat", "Holographic & Color-Shift", "Source Pattern Plates"];
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
    "EFX Enhanced Foundation Exotic": ["efx_holographic_drift", "efx_cathedral_veil", "efx_frost_fractal", "efx_kintsugi_bloom", "efx_quicksilver_pool", "efx_volcanic_obsidian", "efx_aurora_skin", "efx_lace_filament", "efx_tempered_spectrum", "efx_damascus_fold", "efx_stardust_coat", "efx_spectral_edge", "efx_frost_mercury_duo", "efx_aurora_obsidian_veil", "efx_damascus_trinity", "efx_cathedral_holographic", "efx_tempered_quattro", "efx_crystalline_triad", "efx_volcanic_triad", "efx_aurora_fold"],
    // 2026-04-19 TRUE FIVE-HOUR (TF12) — registry truth.
    // validateFinishData runtime exercise surfaced 9 phantom BASE_GROUPS
    // entries: ids referenced by groups but with no entry in BASES. Painter
    // sees a tile in the picker with no display name and clicking it returns
    // nothing. Removed: hydrographic, tinted_lacquer (Candy & Pearl);
    // terrain_chrome (Chrome & Mirror); cerakote_gloss, sub_black (Industrial
    // & Tactical); acid_etch, battle_patina, oxidized, patina_coat (Weathered
    // & Aged). All 9 still render via the engine; if any should ship as a
    // base, add a proper BASES entry — phantoms in BASE_GROUPS are a UX lie.
    "Candy & Pearl": ["candy_burgundy", "candy_cobalt", "candy_emerald", "chameleon", "iridescent", "moonstone", "opal", "spectraflame", "tinted_clear", "tri_coat_pearl", "jelly_pearl", "orange_peel_gloss", "satin_candy", "deep_pearl", "hypershift_spectral", "candy_gold", "candy_lime", "candy_aqua", "copper_pearl", "coral_pearl"],
    "Carbon & Composite": ["aramid", "carbon_base", "carbon_ceramic", "fiberglass", "forged_composite", "graphene", "hybrid_weave", "kevlar_base", "carbon_weave", "forged_carbon_vis", "carbon_3k_fine", "carbon_satin", "carbon_red", "carbon_blue", "spread_tow", "forged_blue", "nomex_honeycomb", "kevlar_red", "basalt_weave", "dyneema_white"],
    "Ceramic & Glass": ["ceramic", "ceramic_matte", "crystal_clear", "enamel", "obsidian", "piano_black", "porcelain", "tempered_glass", "cathedral_glass", "sea_glass", "sapphire_glass", "ruby_glass", "emerald_glass", "amber_glass", "smoked_glass", "milk_glass", "mercury_glass", "crackle_glaze", "liquid_glaze", "terracotta_glaze"],
    "Chrome & Mirror": ["antique_chrome", "black_chrome", "blue_chrome", "candy_chrome", "chrome", "dark_chrome", "mirror_gold", "red_chrome", "satin_chrome", "surgical_steel", "electroplated_gold"],
    "Exotic Metal": ["anodized", "brushed_aluminum", "brushed_titanium", "cobalt_metal", "diamond_coat", "frozen", "liquid_titanium", "platinum", "raw_aluminum", "rose_gold", "titanium_raw", "tungsten", "organic_metal", "anodized_exotic", "xirallic", "chromaflair"],
    "Tactical & Cyberpunk": ["multicam", "marpat_woodland", "tiger_stripe", "kryptek_typhon", "m81_woodland", "desert_dpm", "urban_digital", "od_drab", "coyote_fde", "blackout_ops", "neon_circuit", "tron_grid", "synthwave", "data_rain", "glitch_rgb", "hex_tech", "holo_vapor", "chrome_neon", "plasma_pulse", "cyber_camo"],
    "★ OPTIC LAB · Flash Stone": ["labradorite", "spectrolite", "ammolite", "tiger_eye", "dichroic_glass", "fire_agate", "malachite", "azurite", "black_opal", "sunstone"],
    "★ OPTIC LAB · Night Bloom": ["retroreflective_silver", "hi_vis_lime", "cats_eye_beaded", "diamond_grade", "ghost_graphic", "amber_hazard", "tribal_blaze", "big_kahuna", "chevron_blaze", "starfield_reflective"],
    "★ OPTIC LAB · Two-Face": ["twoface_blue_copper", "twoface_purple_gold", "twoface_green_magenta", "twoface_teal_orange", "twoface_red_cyan", "twoface_silver_void", "twoface_pink_teal", "twoface_gold_emerald", "twoface_violet_lime", "twoface_crimson_navy"],
    "★ OPTIC LAB · Fluid Pour": ["pour_ocean", "pour_lava", "pour_galaxy", "pour_gold_marble", "pour_tropical", "pour_rose", "ink_emerald", "ink_copper", "pour_monochrome", "pour_neon"],
    "★ OPTIC LAB · Sequin Disco": ["sequin_silver", "sequin_gold", "sequin_rose", "sequin_emerald", "sequin_copper", "sequin_ice", "sequin_rainbow", "sequin_holographic", "disco_black_diamond", "sequin_mardi_gras"],
    "Metallic Standard": ["candy", "candy_apple", "champagne", "copper", "gunmetal", "gunmetal_satin", "metal_flake_base", "original_metal_flake", "champagne_flake", "fine_silver_flake", "blue_ice_flake", "bronze_flake", "gunmetal_flake", "green_flake", "fire_flake", "metallic", "midnight_pearl", "pearl", "pearlescent_white", "pewter", "satin_metal", "alubeam"],
    "Flames": ["flame_hotrod", "flame_true_fire", "flame_inferno", "flame_dragon", "flame_lava", "flame_ember", "flame_candy", "flame_phoenix", "flame_tribal", "flame_smoke", "flame_blue", "flame_cold", "flame_plasma", "flame_white_hot", "flame_purple", "flame_pink", "flame_green", "flame_toxic", "flame_rainbow", "flame_ghost"],
    "Marble & Onyx": ["marble_carrara", "marble_calacatta", "marble_nero", "marble_portoro", "marble_statuario", "marble_bardiglio", "marble_rose", "marble_rosso", "marble_verde_alpi", "marble_fusion", "travertine", "obsidian_gold", "onyx_emerald", "onyx_honey", "onyx_pink", "onyx_white", "agate_blue", "lapis_lazuli", "amethyst", "tiger_iron"],
    // 2026-05-18 (owner mandate): "Racing Heritage" base group REMOVED.
    // The 11 underlying ids (asphalt_grind, barn_find, etc.) remain in
    // BASES because they're cross-referenced by other family/group lists
    // (weathered, chrome) and HERO_BASES; only the picker grouping is gone.
    "Sock Hop": ["diner_checker", "soda_check", "cherry_polka", "lemon_polka", "bubblegum_dot", "mint_stripe", "coral_stripe", "gingham_red", "atomic_starburst", "atomic_charcoal", "googie_orbit", "vinyl_groove", "harlequin", "argyle_pastel", "terrazzo_cream", "formica_boomerang", "jukebox_neon", "pink_fleck", "turquoise_fleck", "chrome_diner"],
    "Groovy Vibes": ["tie_dye_spiral", "tie_dye_crumple", "peace_tie_dye", "psychedelic_swirl", "acid_swirl", "melting_rainbow", "hippie_rainbow", "sunburst_60s", "groovy_zigzag", "kaleido_rings", "trippy_concentric", "warp_op", "oil_slick_groove", "groovy_marble", "liquid_light", "flower_power", "lava_lamp_purple", "lava_lamp_groovy", "mushroom_fade", "neon_acid_blob"],
    // NOTE (2026-04-17): "★ SHOKK Series", "★ COLORSHOXX", "★ MORTAL SHOKK",
    // "★ NEON UNDERGROUND", "★ Anime Inspired" were removed from BASE_GROUPS.
    // They are "Specials"-only categories and now live exclusively in
    // SPECIAL_GROUPS via _SPECIALS_SHOKKER / _SPECIALS_ANIME_INSPIRED.
    "Iridescent Insects": ["beetle_jewel", "beetle_rainbow", "beetle_stag", "butterfly_monarch", "butterfly_morpho", "dragonfly_wing", "firefly_glow", "moth_luna", "scarab_gold", "wasp_warning"],
    "Extreme & Experimental": ["bioluminescent", "dark_matter", "electric_ice", "holographic_base", "liquid_obsidian", "mercury", "neutron_star", "plasma_core", "plasma_metal", "prismatic", "quantum_black", "singularity", "solar_panel", "superconductor", "vantablack", "volcanic", "burnt_headers"],
    // 2026-05-18 (owner mandate): "Textile-Inspired", "Stone & Mineral",
    // and "Paint Technique" base groups REMOVED along with their 18
    // underlying base entries. Renderers were never registered (engine
    // logged "Missing ids skipped" for all 18).
    "★ PRISM FORGE": ["pf_event_horizon_spectra", "pf_chromatic_storm", "pf_neon_nova", "pf_molten_aurora", "pf_void_pearl", "pf_ion_trap", "pf_sapphire_blood", "pf_emerald_inferno", "pf_violet_sunrise", "pf_copper_moon", "pf_toxic_horizon", "pf_glacial_burn", "pf_oil_nebula", "pf_rose_quantum", "pf_cobalt_fire", "pf_midnight_prism", "pf_hyperwave", "pf_crystal_fade", "pf_dark_matter_halo", "pf_apex_spectrum", "pf_cluster_tar_eclipse", "pf_cluster_bitumen_aurora", "pf_cluster_obsidian_gild", "pf_cluster_coal_starfield", "pf_cluster_void_islands", "pf_bright_solar_daffodil", "pf_bright_hyperpink", "pf_bright_seafoam_bolt", "pf_bright_cerulean_pop", "pf_bright_canary_glass", "pf_bright_magenta_arc", "pf_bright_lime_voltage", "pf_bright_peach_fizz", "pf_bright_neon_ice_stream", "pf_bright_orchid_pulse", "pf_blend_triad_mist", "pf_blend_quad_weave", "pf_spectrum_chaos_crown", "pf_prismatic_void_madness", "pf_white_castle_of_fear", "pf_gradient_venetian_veil", "pf_tri_crimson_cyan_mage", "pf_quad_jade_violet_gold_slate", "pf_fade_copper_teal_sunset", "pf_blend_ocean_peach_ivory", "pf_iris_velvet_crossfade", "pf_spectral_tidepool_wash", "pf_midnight_coral_ember", "pf_emerald_orchid_storm", "pf_golden_ultraviolet_fog"],
};

const PATTERN_GROUPS = {
    // 2026-05-23 regular-pattern audit loop: collapse 25 small picker groups into 8 owner-reviewable groups, all <= 50 finishes.
    "\u2726 Abstract, Fractal & Paradigm": ["biomechanical", "biomechanical_2", "fractal", "fractal_2", "fractal_3", "interference", "optical_illusion", "optical_illusion_2", "sound_wave", "stardust", "stardust_2", "voronoi_shatter", "Art_Deco", "Art_Deco_V2", "Art_Deco_V3", "Art_Deco_V4", "circuitboard", "holographic", "p_tessellation", "p_topographic", "soundwave", "caustic", "dimensional", "fresnel_ghost", "neural", "p_plasma", "reaction_diffusion", "fractal_fern", "hilbert_curve", "lorenz_slice", "julia_boundary", "wave_standing", "lissajous_web", "dragon_curve", "diffraction_grating", "perlin_terrain", "phyllotaxis", "truchet_flow", "hypocycloid", "voronoi_relaxed", "wave_ripple_2d", "sierpinski_tri", "geo_fractal_triangle", "geo_hilbert_curve"],
    "\u2699 Tech, Carbon & Industrial": ["carbon_fiber", "kevlar_weave", "nanoweave", "basket_weave_alt", "carbon_alt_1", "carbon_weave_pattern", "exhaust_wrap_alt", "geo_weave", "hex_carbon", "multi_directional", "wavy_carbon", "chainlink", "chainmail", "corrugated", "diamond_plate", "expanded_metal", "hammered", "hex_mesh", "metal_flake", "perforated", "data_stream", "glitch_scan", "matrix_rain", "pixel_grid", "shokk_bitrot", "shokk_cipher_pattern", "shokk_firewall", "shokk_hex_dump", "shokk_kernel_panic", "shokk_overflow", "shokk_packet_storm", "shokk_scan_line", "shokk_signal_noise", "shokk_zero_day", "circuit_traces", "hex_circuit", "biomech_cables", "dendrite_web", "crystal_lattice", "chainmail_hex", "graphene_hex", "gear_mesh", "vinyl_record", "fiber_optic", "sonar_ping", "waveform_stack"],
    "\u25c6 Geometry, Deco & Op-Art": ["art_deco", "celtic_knot", "chevron", "crosshatch", "greek_key", "pinstripe", "plaid", "tessellation", "art_deco_fan", "chevron_stack", "quatrefoil", "herringbone", "basket_weave", "houndstooth", "argyle", "tartan", "op_art_rings", "moire_grid", "lozenge_tile", "ogee_lattice", "concentric_op", "checker_warp", "barrel_distort", "moire_interference", "twisted_rings", "spiral_hypnotic", "necker_grid", "radial_pulse", "hex_op", "pinwheel_tiling", "impossible_grid", "rose_curve", "art_deco_sunburst", "art_deco_chevron", "greek_meander", "star_tile_mosaic", "escher_reptile", "constructivist", "bauhaus_system", "celtic_plait", "cane_weave", "cable_knit", "damask_brocade", "tatami_grid"],
    "\ud83c\udf3f Nature, Animals & Weather": ["camo", "crocodile", "dazzle", "feather", "giraffe", "leopard", "multicam", "snake_skin", "snake_skin_2", "snake_skin_3", "snake_skin_4", "tiger_stripe", "zebra", "aurora_bands", "hailstorm", "lightning", "plasma", "ripple", "sandstorm", "solar_flare", "tornado", "wave", "marble_veining", "wood_burl", "seigaiha_scales", "ammonite_chambers", "peacock_eye", "dragonfly_wing_pattern", "insect_compound", "diatom_radial", "coral_polyp", "birch_bark", "pine_cone_scale", "geode_crystal", "nature_bark_rough", "nature_water_ripple_pat"],
    "\ud83c\udf0e Cultural, World & Dark": ["aztec", "aztec_alt1", "aztec_alt2", "dragon_scale", "dragon_scale_alt", "fleur_de_lis", "fleur_de_lis_alt", "japanese_wave", "mandala", "mandela_ornate", "mosaic", "muertos_dod1", "muertos_dod2", "rune_symbols", "steampunk_gears", "tribal_norse_runes", "tribal_celtic_spiral", "barbed_wire", "gothic_arch", "gothic_scroll", "iron_emblem", "five_point_star", "razor_wire", "skull", "skull_wings", "spiderweb", "thorn_vine", "spiral_fern", "zigzag_bands", "radial_calendar", "triple_knot", "diagonal_interlace", "diamond_blanket", "step_fret", "concentric_dot_rings", "medallion_lattice", "eight_point_star", "petal_frieze", "cloud_scroll"],
    "\ud83c\udf9e Decades 50s-80s": ["decade_50s_diner_checkerboard", "decade_50s_jukebox_arc", "decade_50s_sputnik_orbit", "decade_50s_drivein_marquee", "decade_50s_fallout_shelter", "decade_50s_boomerang_formica", "decade_50s_atomic_reactor", "decade_50s_diner_chrome", "decade_50s_crt_phosphor", "decade_50s_casino_felt", "decade_60s_peace_sign", "decade_60s_tie_dye_spiral", "decade_60s_lava_lamp_blob", "decade_60s_opart_illusion", "decade_60s_pop_art_halftone", "decade_60s_gogo_check", "decade_60s_caged_square", "decade_60s_peter_max_gradient", "decade_60s_peter_max_alt", "Halftone_Rainbow", "12155818_4903117", "12267458_4936872", "12284536_4958169", "12428555_4988298", "144644845_10133112", "decade_70s_earth_tone_geo", "248169", "6868396_23455", "78534344_9837553_1", "decade_70s_funk_zigzag", "Groovy_Swirl", "Plad_Wrapper", "decade_70s_studio54_glitter", "decade_70s_pong_pixel", "decade_80s_pacman_maze", "decade_80s_neon_grid", "decade_80s_rubiks_cube", "decade_80s_rubiks_cube_2", "decade_80s_rubiks_cube_3", "decade_80s_boombox_speaker", "decade_80s_nintendo_dpad", "decade_80s_breakdance_spin", "decade_80s_laser_tag", "decade_80s_leg_warmer"],
    "\ud83d\udcbf 90s, Skate & Surf": ["decade_90s_grunge_splatter", "decade_90s_nirvana_smiley", "decade_90s_cross_colors", "decade_90s_tamagotchi_egg", "decade_90s_sega_blast", "decade_90s_fresh_prince", "decade_90s_floppy_disk", "decade_90s_rave_zigzag", "decade_90s_y2k_bug", "decade_90s_tribal_tattoo", "decade_90s_dialup_static", "decade_90s_slap_bracelet", "decade_90s_windows95", "decade_90s_chrome_bubble", "decade_90s_rugrats_squiggle", "decade_90s_rollerblade_streak", "decade_90s_beanie_tag", "decade_90s_dot_matrix", "decade_90s_geo_minimal", "decade_90s_sbtb_wall", "Billabong_Board", "Billabong_Surf_Style", "Blind_Skateboy", "Bong_Surfer", "Hardcore_Punk", "Hero_Skate", "Hydro_Wave", "Punk_Rock_Zine", "Skate_Deck", "Skate_Reaper_Glowing_Eyes", "Skate_Reaper_Tiled", "Surf_80s", "Surfin_80s", "Thrash_Metal_Skate_Alt", "Thrash_Metal_Skate", "Tiki_Surf"],
    "\u2728 Reactive & Surface Accents": ["shimmer_quantum_shard", "shimmer_prism_frost", "shimmer_velvet_static", "shimmer_chrome_flux", "shimmer_matte_halo", "shimmer_oil_tension", "shimmer_neon_weft", "shimmer_void_dust", "shimmer_turbine_sheen", "shimmer_spectral_mesh", "iridescent_fog", "chrome_delete_edge", "carbon_clearcoat_lock", "racing_scratch", "pearlescent_flip", "frost_crystal", "satin_wax", "uv_night_accent"],
    "\ud83c\udf86 Let Freedom Ring": ["lfr_star_lattice", "lfr_stripe_drift", "lfr_bunting_scallop", "lfr_distressed_flag", "lfr_eagle_crest", "lfr_firework_radial", "lfr_constellation_field", "lfr_ribbon_weave", "lfr_stencil_stars", "lfr_liberty_filigree"],
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
// 2026-06-03: MC_DEFS emptied (25 dynamic mc_* tiles scrubbed — orphan, zero live picker refs).
// MUST stay an EMPTY array, not deleted: the forEach below + the .find in getFinishColorsForId
// reference it, so removing the literal threw a top-level ReferenceError that bricked the whole
// finish-data module (catalog failed to populate). Empty = harmless no-ops, no mc_* tiles.
const MC_DEFS = [];
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

    // Register legacy ad-hoc shift on server, then apply as zone finish
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
                z.finishName = 'Legacy Dual Shift: ' + ca.toUpperCase() + ' → ' + cb.toUpperCase();
                // Store legacy ad-hoc shift metadata for preset save/restore
                z._customDualShift = { colorA: ca, colorB: cb, intensity: intensity };
                if (typeof renderZones === 'function') renderZones();
                if (typeof renderZoneDetail === 'function') renderZoneDetail(_dualShiftTargetZone);
                if (typeof triggerPreview === 'function') triggerPreview();
            }
            closeDualShiftModal();
            if (typeof showToast === 'function') {
                showToast('Legacy dual shift applied! Rendering...', 'success');
            }
        } else {
            alert('Failed to register legacy dual shift: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(function (err) {
        console.error('Legacy dual shift registration failed:', err);
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
            // 2026-06-01: these 11 bases are INTENTIONALLY ungrouped. The "Racing Heritage" picker
            // group was removed by owner mandate 2026-05-18 (see BASE_GROUPS comment ~L2965) but the
            // BASES entries stay because other family lists + HERO_BASES cross-reference them. They are
            // deliberately out of the picker — don't report them as a data defect.
            var INTENTIONAL_UNGROUPED_BASES = new Set(['asphalt_grind', 'barn_find', 'checkered_chrome', 'drag_strip_gloss', 'endurance_ceramic', 'pace_car_pearl', 'race_day_gloss', 'rally_mud', 'bullseye_chrome', 'stock_car_enamel', 'victory_lane']);
            for (var i = 0; i < BASES.length; i++) {
                var b = BASES[i];
                if (!b || !b.id) continue;
                if (!groupedBase.has(b.id) && !INTENTIONAL_UNGROUPED_BASES.has(b.id)) { problems.push('Ungrouped BASE: ' + b.id); counts.ungrouped_base++; }
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
