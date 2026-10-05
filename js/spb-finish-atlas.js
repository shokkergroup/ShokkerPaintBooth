/* ===========================================================================
   SPB — FINISH ATLAS                                              2026-07-31
   ---------------------------------------------------------------------------
   Owner directive (10-hour lane): 1,826 finishes (2,000 soon) bury people.
   "We need people to go 'holy shit look at all I have to play with' — but not
   paralysis."

   This file is the WHOLE feature. It deliberately edits NOTHING in
   paint-booth-2-state-zones.js — it wraps openSwatchPicker/filterSwatchPopup
   at runtime and reorganizes the rendered DOM. Two reasons:
     1. Kimi K3 is actively adding ~10 new FRACTURED categories to
        paint-booth-0-finish-data.js right now. Touching the data file or the
        render function invites a merge collision mid-flight. This file derives
        sections from whatever groups EXIST at open time, so Kimi's new
        categories flow into the FRACTURED section automatically, zero edits.
     2. Rollback = delete two include lines in paint-booth-v2.html.

   What it does:
     - Sections + 4-across category-card grid (owner's exact order):
         FOUNDATIONS (3 across, fixed order, EFX renamed)
         THE CORE COLLECTION (rest of base groups, A-Z, 4 across)
         FRACTURED (all /fractured/i groups, A-Z, 4 across — Kimi-proof)
         SHOKKER (catch-all: Shokk families + FABLE + Pattern Plates +
                  Grunge & Fun + Atmosphere + Signal + anything new, A-Z)
         CULTURAL (5 across — owner: "only 5 so put them 5 across")
         COLOR SCIENCE (A-Z)  ·  FUSION LAB (A-Z)
     - Rich per-category descriptions (tagline on the card, full text expanded)
     - Alphabetical finishes inside every category (Grouped view)
     - Rescues 3 groups that were IN NO SECTION and never rendered:
         Aurora & Chromatic Flow [30] + Chromatic Flake [30] -> Color Science
         Atelier — Ultra Detail [17] -> Shokker            (77 finishes!)
     - Live hashtag bar: real counts, toggle filtering, full tag drawer
     - Explored tracking (✓ badge, per-category meter, global progress)
     - 🎲 SURPRISE ME (biased to unexplored) + TODAY'S 5 date-seeded shelf
   =========================================================================== */
(function () {
    'use strict';

    var A = window.SPB_ATLAS = {};

    /* ---------------- section model (owner's order) ---------------- */
    A.SECTIONS = [
        { id: 'spec_overlays', label: 'SPEC OVERLAYS', icon: '◈', cols: 4,
          intro: 'Fine material constructions for your existing paint. Explore a family, inspect the surface, then stack its metallic, roughness and clearcoat detail.' },
        { id: 'foundations', label: 'FOUNDATIONS', icon: '🏁', cols: 3,
          intro: 'Start here. Clean, dependable paint that looks right on every car — the base coats everything else builds on.' },
        { id: 'core', label: 'THE CORE COLLECTION', icon: '💎', cols: 4,
          intro: 'The material library — real-world surfaces from candy lacquer to raw carbon, plus the Optic Lab effect series. If you can park it in a showroom, it lives here.' },
        { id: 'fractured', label: 'FRACTURED', icon: '⚡', cols: 4,
          intro: 'Its own universe. Generative finishes that shatter, flow, burn and bloom — no two panels repeat, and new Fractured families land here constantly. This is where the wild ones live.' },
        { id: 'shokker', label: 'SHOKKER', icon: '🔥', cols: 4,
          intro: 'The house collection — everything born in the Shokker lab. Signature series, guest slots, imports from Shokk Drop, atmosphere and signal experiments. The deepest bench in the booth.' },
        { id: 'cultural', label: 'CULTURAL', icon: '🌍', cols: 5,
          intro: 'Hand-built tribute collections — full liveries of layered, hand-authored art. The most detailed finishes in the entire catalog.' },
        { id: 'colorsci', label: 'COLOR SCIENCE', icon: '🧪', cols: 4,
          intro: 'Finishes about COLOR itself — chameleon flips, prism splits, gradients and clash sets. Pick these when the color story is the whole point.' },
        { id: 'fusion', label: 'FUSION LAB', icon: '◈', cols: 4,
          intro: 'Physics experiments: light, grain, depth and material math fused into finishes that behave like nothing on a real shelf.' }
    ];

    var CULTURAL = { 'RISING SUN': 1, 'VIVA MEXICO': 1, 'UNION JACKED': 1, 'FORBIDDEN DRAGON': 1, 'LET FREEDOM RING': 1 };
    var COLORSCI = { 'Chameleon': 1, 'Prizm': 1, 'Aurora & Chromatic Flow': 1, 'Chromatic Flake': 1, 'Color Clash': 1,
                     'Color-Shift Adaptive': 1, 'Color-Shift Presets': 1, 'Color-Shift Duos': 1,
                     'Gradient Directional': 1, 'Gradient Vortex': 1, 'Gradient Extended': 1 };
    var FUSION = { '🌈 GRADIENTS': 1, '★ Spectrum Shift': 1, 'Light & Optics': 1, 'Surface & Grain': 1,
                   'Depth & Geometry': 1, 'Materials & Physics': 1 };
    // FOUNDATION ONE (owner 2026-09-03): one category, two shelves — flat BASES + paint/spec EFX.
    var FOUNDATIONS_ORDER = ['Foundation', 'Foundation EFX'];

    A.classify = function (groupName, pickerTypes) {
        if (pickerTypes === 'spec_overlay') return 'spec_overlays';
        if (pickerTypes === 'base') {
            return FOUNDATIONS_ORDER.indexOf(groupName) >= 0 ? 'foundations' : 'core';
        }
        if (/fractured/i.test(groupName)) return 'fractured';
        if (CULTURAL[groupName]) return 'cultural';
        if (COLORSCI[groupName]) return 'colorsci';
        if (FUSION[groupName]) return 'fusion';
        return 'shokker';   // catch-all BY DESIGN — new unclassified groups surface here
    };

    /* Owner: "RENAME FROM EFX ENHANCED FOUNDATION EXOTIC". Display-level only —
       the data key stays stable so BASE_GROUPS refs / engine metadata never break. */
    A.displayName = function (g) {
        if (g === 'Foundation') return 'Foundation Bases';
        if (g === 'Foundation EFX') return 'Foundation EFX';
        return g;
    };

    A.sortKey = function (g) {
        // Alphabetize ignoring emoji/star/decoration prefixes.
        return String(g).replace(/[^A-Za-z0-9&]/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    };

    /* ---------------- detailed category descriptions ----------------
       Owner: "the description of the category should be MUCH more detailed for
       EACH CATEGORY." Tagline = first sentence (collapsed card); full text
       shows when the category is expanded. */
    var D = A.DESC = {
    'SHOKK WORKS': 'Eighty-nine rebuilt finishes in five workshops: Discharge, Living Armor, Optical Deception, Paint Alchemy and Filmcraft. Explore fine conductor forests, iridescent scales, impossible prints, paint processes and layered films. Each surface has its own construction and feature-owned metal, roughness and clearcoat. Quiet coatings and matte covers keep their restraint. Use finish colour for the complete design, or source paint to apply its material response to your own livery.',
    'Foundation': 'Twenty flat base sheens with no colour of their own — wet look, gloss, semi-gloss, satin, eggshell, matte, primer and flat black on the paint side; pearl, satin pearl, metallic, matte metallic, candy, brushed, frozen, bead blast, chrome, dark chrome and satin chrome on the metal side. Every one is a different cell of the material cube, so no two look alike. Pick a colour, pick a sheen, done.',
    'Foundation EFX': 'Foundations with texture — holographic foil, frost, mercury, kintsugi, obsidian, damascus and stardust that carry their own paint and spec. Still a base coat: use source paint or a solid colour over the top, or let the finish own the whole car.',
    'Candy & Pearl': 'Deep candy lacquers and pearl coats — color with dimension. Candies glow from inside like hard sugar over metal; pearls flip soft secondary tones as the car turns. The classic show-car look: rich at a distance, alive up close.',
    'Carbon & Composite': 'Woven carbon fiber, kevlar, forged composite and technical weaves. Reads as raw material, not paint — the motorsport look. Run it whole-car for a prototype feel or zone it into hoods and splitters to break up a bright livery.',
    'Ceramic & Glass': 'Nano-ceramic smoothness, frosted glass, porcelain and vitreous shine. These finishes feel ENGINEERED — ultra-clean surfaces with cold, precise light response. The choice when you want laboratory-clean rather than hot-rod loud.',
    'Chrome & Mirror': 'Full mirror chrome and its family — polished, brushed, smoked and tinted reflection. The loudest material in the booth: it does not have a color so much as it steals everyone else\'s. Small doses electrify a livery; whole-car chrome is a statement you cannot take back.',
    'Exotic Metal': 'Metals you cannot buy at a parts counter — anodized titanium, heat-blued steel, raw magnesium, acid-etched alloys. Industrial, expensive-looking surfaces with real grain and temper marks. For cars that should look machined, not painted.',
    'Tactical & Cyberpunk': 'Stealth coatings, night-ops matte, hex-plate armor and neon-edged tech surfaces. Low-vis military on one end, Night City on the other. These finishes make a car look ARMED.',
    'Metallic Standard': 'The complete standard metallic range — fine flake through coarse sparkle in every practical tone. The workhorse family: brighter than Foundation, calmer than the exotics, correct on basically any panel of any car.',
    'Flames': 'Painted fire — traditional hot-rod licks, airbrushed realism and stylized burn patterns. These carry their own artwork, so they zone beautifully: run flames on the nose and let a foundation carry the tail.',
    'Marble & Onyx': 'Polished stone — white Carrara veining, black onyx depth, travertine and slate. Unexpected on a race car, which is exactly the appeal: it reads as sculpture at speed.',
    'Sock Hop': 'Fifties diner-era Americana — cream-and-chrome two-tones, jukebox sparkle, milkshake pastels and checkerboard trim. Nostalgia with a fresh coat: retro that photographs like candy.',
    'Groovy Vibes': 'The sixties and seventies in paint — lava-lamp swirls, sunburst fades, shag-carpet texture and psychedelic bloom. Loud, warm and unmistakably fun. Nothing else in the booth smiles like this family.',
    '★ OPTIC LAB · Flash Stone': 'Optic Lab series — mineral surfaces that FLASH. Ammolite, spectrolite and fire-agate looks where the stone lights up from angle to angle. Interference physics tuned so the sparkle survives at racing distance.',
    '★ OPTIC LAB · Night Bloom': 'Optic Lab series — dark-field finishes that bloom with hidden color. Deep near-black surfaces until light hits, then amber, violet or lime fire opens up. The "wait, what was THAT" family.',
    '★ OPTIC LAB · Two-Face': 'Optic Lab series — hard two-tone splits in one finish. Violet/lime, cyan/magenta, gold/graphite: each panel decides its side based on angle. A two-color livery without painting two colors.',
    '★ OPTIC LAB · Fluid Pour': 'Optic Lab series — liquid art, frozen. Acrylic pour swirls, molten marble and lava flows locked mid-motion. Every zone placement crops the pour differently, so the same finish never looks the same twice.',
    '★ OPTIC LAB · Sequin Disco': 'Optic Lab series — mirror-ball surfaces built from thousands of micro-facets. Holo sequin, rainbow glitter and dance-floor chrome. Maximum sparkle per square inch of anything in the catalog.',
    'Iridescent Insects': 'Beetle-shell and butterfly-wing iridescence — nature\'s original color-shift. Oily greens, purples and bronzes that crawl across the body as the angle changes.',
    'Extreme & Experimental': 'The proving ground — finishes that push the engine until it creaks. Reality-bending effects, prototype math, ideas too strange for any other family. Some are gorgeous, some are unhinged, all are worth one render.',
    'X LAB': 'Codex’s no-brief material laboratory: thirty brand-new optical skins, engineered liquids, impossible ceramics and living-light experiments. Every card is a separate swing, never a colorway.',
    '★ PRISM FORGE': 'Fifty exotic-engine builds around split light — prismatic edges, forged spectral gradients and hard color refraction. One of the deepest single collections in the booth, and every entry is a keeper-tier render.',

    /* ---- FRACTURED universe ---- */
    '🔥 FRACTURED FLAMES · Ignite': 'Fractured fire, first form: IGNITE. Generative flame fronts that spark, catch and race across the body — every panel burns its own way. The aggressive end of the Fractured Flames trilogy.',
    '🔥 FRACTURED FLAMES · Dance': 'Fractured fire, second form: DANCE. Slower, more liquid flame — ribbons of heat that curl around curves like they are reading the bodywork. The elegant burn.',
    '🔥 FRACTURED FLAMES · Topo': 'Fractured fire, third form: TOPO. Flame rendered as terrain — contour lines of heat, elevation maps of burn. Fire for people who love data as much as danger.',
    '🧠 FRACTURED MINDS': 'Fifty-five generative psyches — neural tangles, thought-storms and pattern logic that feels one step from alive. The flagship Fractured family and the deepest: you can get lost in here, pleasantly.',
    '💀 FRACTURED SOULS': 'The dark mirror of Minds — spectral drifts, afterimage trails and finishes that look haunted in the best way. Runs deep blacks and pale fire; incredible under night-race lighting.',
    '⚛ FRACTURED FORGE': 'Seventy-eight builds of raw generative metalwork — split alloys, energy welds, particle seams. The industrial heart of the Fractured universe and its single biggest collection.',
    '🌊 FRACTURED DEEP': 'Ocean-floor generative — pressure waves, bioluminescent drift, current-carved surfaces. Cool, dark and fluid; the calmest branch of Fractured.',
    '👣 FRACTURED CRYPTID': 'Track-of-the-unknown — fine fur, scale, membrane and hide signatures from creatures that do not exist. Their fractured material bands trade opposing hues as the viewing angle changes.',
    '🛸 FRACTURED UFO': 'Recovered-craft surfaces — impossible alloys, scorch signatures, hull plating with geometry that should not tile but does. Area 51 for your quarter panels.',
    '🌈 FRACTURED RAINBOW': 'The full spectrum, shattered — prismatic shards and split-light ribbons rearranged by the generator. Loud, joyful chaos.',
    '🔮 FRACTURED OCCULT': 'Sigils, ritual geometry and candle-lit gradients — the mystic branch. Runs gold-on-black and violet like nothing else in the booth.',
    '🦋 FRACTURED MORPHO': 'Fifty fine-scale studies of wing, shell, nacre, film and mineral structural color. Each keeps its own physical micro-signature while opposing hue populations flip with the viewing angle.',
    '🌸 FRACTURED BLOOM': 'Twenty botanical micro-worlds built from distinct petals, pollen, stamens, veins, whorls and mosaics. Fine flower structures hold the identity while angle-driven material bands exchange color.',
    '🧫 FRACTURED PETRI': 'Twenty microscopic cultures built from distinct colonies, membranes, diatoms, hyphae, chains and radiolaria. Their biological topology stays fixed while fractured opposing hues flip with the viewing angle.',
    '🌋 FRACTURED MOLTEN': 'Live volcano surfaces — crust, crack and glow. Black stone skin over molten light that traces every panel line. Heat you can almost feel.',

    /* ---- SHOKKER catch-all ---- */
    'SHOKK DROP': 'Your imports live here. Anything you build in Shokk Drop — from any image, any art — lands in this shelf ready to paint. This category is yours to fill.',
    'PARADIGM': 'The signature Shokker design system — thirty-four builds of structured, engineered pattern with the orange thread running through. House style, house pride.',
    '★ COLORSHOXX': 'Seventy-seven electric color studies — thunderstorm teals, volcanic glass, galaxy dust. The biggest pure-color collection in the booth and the fastest way to find "that color I can\'t name."',
    '★ MORTAL SHOKK': 'The tournament roster — twenty-six finisher-grade builds with fight-poster drama. Dark themes, blood accents, arcade energy. Pick your fighter.',
    '★ MONEY SHOKK': 'Forty themed exotic engines about wealth in every form — mint foil, vault steel, counterfeit gold, burn-a-stack green. Flexes harder than chrome.',
    '★ NEON UNDERGROUND': 'Twenty-five charged automotive materials — phosphor, microprism, fluorescent glass, conductive film, optical clear, mica, foil, ceramic, and flock.',
    '★ ANIME INSPIRED': 'Cel-shade energy, speed-line shimmer and hero-machine gloss — eight builds straight off the storyboard.',
    '★ IRIDESCENT INSECTS': 'The beetle-shell family surfaced in the Shokker wing — jewel-carapace color-shift curated to the ten best shells.',
    'Shokk Series': 'The original house line — thirty-three builds that defined the Shokker look before the labs split off. Still carries some of the hardest-hitting finishes in the catalog.',
    'Atelier — Ultra Detail': 'The fine-brush room — seventeen ultra-detail builds where the interest lives at millimeter scale. Made to be zoomed into; unreal in close-up shots.',
    'SOURCE PATTERN PLATES': 'Twenty-four source plates — the raw pattern stock the design lab builds from, exposed as paintable finishes. Industrial honesty: what patterns look like before styling.',
    'GRUNGE & FUN': 'Forty-eight builds of beautiful mess — sticker-bomb, spray-tag, scuff, splatter and shop-floor character. The anti-showroom: cars that look LIVED.',
    'Glass & Surface': 'Glass, stone, masonry and wet-clearcoat studies on one substantial shelf — transparent depth, etched faces, mineral grain and liquid gloss without a one-off effects drawer.',
    'Atmosphere': 'Weather as paint — fog banks, storm fronts, golden-hour haze and pressure light. Soft, cinematic surfaces that make a car look like it drove out of a film still.',
    'Signal': 'Broadcast interference as a finish — scan lines, static bursts, test-pattern color and transmission ghosts. The glitch family: analog TV meets asphalt.',

    /* ---- CULTURAL ---- */
    'RISING SUN': 'The Japan collection — fifty-two hand-layered builds of sun rays, indigo waves, koi and lacquer red. One of the three gold-standard hand-authored collections and a masterclass in restraint.',
    'VIVA MEXICO': 'Fifty-eight builds of Mexican folk-art fire — papel picado lattice, talavera tile, marigold and serape stripe. The single most detailed collection in the booth; the reference standard every procedural family is measured against.',
    'UNION JACKED': 'The British invasion — forty-five builds of flag geometry, mod target rings and racing-green heritage with punk edges. Sharp, graphic and instantly readable at speed.',
    'FORBIDDEN DRAGON': 'Twenty builds of temple-dragon art — scale-work, cloud-scroll and gold-on-black mythology. Hand-plate detail with serious presence on a hood.',
    'LET FREEDOM RING': 'Ten stars-and-stripes builds that go beyond flag-on-car — weathered banners, fireworks burst, parade chrome. American thunder, painted properly.',

    /* ---- COLOR SCIENCE ---- */
    'Chameleon': 'True color-flip paint — fifteen builds that travel green-to-purple, gold-to-teal, whole families of hue in one finish. The angle decides; the car never wears just one color.',
    'Prizm': 'The complete split-light lab — hard prism bands, angle-driven chameleon travel and flowing aurora color share one deep shelf. Ordered refraction, whole-body hue flips and soft chromatic current without three undersized drawers.',
    'Aurora & Chromatic Flow': 'Thirty builds of northern-lights motion — soft chromatic currents that drift across panels rather than flipping. The gentlest color-shift in the booth, and one of the prettiest.',
    'Chromatic Flake': 'Color-shift carried entirely in the FLAKE — thirty builds where the sparkle itself changes hue while the base holds steady. Subtle at rest, wild in sunlight.',
    'Color-Shift Duos': 'The full two-color travel library — complementary, warm/cool, subtle and extreme shifts collected together so every angle-driven pairing is in one place.',
    'Color Clash': 'Twenty-five deliberate collisions — complementary pairs slammed together at full saturation. Uncomfortable on a swatch, spectacular on a car.',
    'Gradient Directional': 'Engineered fades with nose-to-tail, roof-to-rocker, diagonal and vortex travel. The clean way to move two colors across a body without a hard line.',
    'Gradient Vortex': 'Ten gradients that ROTATE — color spiraling around a center instead of fading across. Hypnotic on wheels-turning footage.',
    'Gradient Extended': 'The big multi-stop gradient library, covering practically every color pairing worth running. If a fade exists, it is in here.',

    /* ---- FUSION LAB ---- */
    '🌈 GRADIENTS': 'The Fusion Lab gradient engine — eleven flagship fades built with the structure-times-color math that won the 2026 gradient rebuild. Small set, reference quality.',
    '★ Spectrum Shift': 'Fifty builds where the entire spectrum slides across the car as one continuous motion — the halo family of the color-shift program.',
    'Light & Optics': 'Twenty-nine experiments in pure light behavior — caustics, lens flare, refraction patterns baked into paint.',
    'Surface & Grain': 'The tactile library — leather and cloth, organic growth, weathering, particles, micro-grain, brushed direction and tooling marks. Finishes you can almost feel through the screen.',
    'Depth & Geometry': 'Structured finishes that fake dimension — architectural grids, lattices, parallax layers, carved relief and impossible depth on a flat panel.',
    '🌿 FRACTURED WILDS': 'The living branch of Fractured — 110 distinct fine-scale cryptid, structural-color, botanical and microscopic finishes. Every design keeps a recognizable natural signature and true angle-driven opposing-color flip: if it grows, it fractures here.',
    '🌊 FRACTURED ELEMENTS': 'Weather and water as generative math — ocean-floor pressure, storm tempests and hoarfrost merged into the elemental family. Deep currents, lightning energy and ice crystallography on one shelf.',
    '🌌 FRACTURED COSMOS': 'Everything off-planet — saucer alloys and alien glyphs, nebula gas fields, and prismatic split-light ribbons merged into the space family. The UFO landed in a nebula and left a rainbow.',
    '🏺 FRACTURED RELICS': 'The crafted-and-ancient family — occult ritual geometry, kintsugi gold-seam ceramics, cathedral stained glass, excavated artifacts and clockwork guilloche in one reliquary. Made by hands, broken by time, repaired in gold.',
    '★ OPTIC LAB': 'The full Optic Lab — fifty light-bending effect finishes in one wing. Mineral flash (labradorite, ammolite, black opal), retroreflective night-bloom sheeting that ignites under headlights, hard two-tone Two-Face splits, frozen acrylic fluid pours and mirror-ball sequin fields. If it plays tricks with light, it lives here.',
    'Materials & Physics': 'Material behavior and surface treatment in one lab — ferrofluid spikes, crystal growth, magnetic fields, anodizing, etching, corrosion and fracture. The maddest science in the booth.'
    };

    A.DESC = D;   // exposed so sibling catalog injectors (nightshift lab) can add entries
    A.desc = function (g) {
        var overlayFamily = window.SPB_SPEC_OVERLAY_V2 && window.SPB_SPEC_OVERLAY_V2.families.find(function (family) { return family.name === g; });
        if (overlayFamily) return overlayFamily.desc;
        if (D[g]) return D[g];
        // fall back to the app's short blurb, then to a generic line
        try { if (typeof _spbGroupBlurb === 'function') { var b = _spbGroupBlurb(g); if (b) return b; } } catch (e) {}
        return 'A curated Shokker finish family.';
    };
    A.tagline = function (g) {
        var d = A.desc(g);
        var i = d.indexOf('—') > 20 ? -1 : d.indexOf('. ');
        if (i < 0) i = d.indexOf('. ');
        return i > 0 ? d.slice(0, i + 1) : d;
    };

    /* ---------------- explored tracking ---------------- */
    var TRIED_KEY = 'spb_tried_finishes_v1';
    var _tried = null;
    function tried() {
        if (_tried) return _tried;
        try { _tried = new Set(JSON.parse(localStorage.getItem(TRIED_KEY) || '[]')); }
        catch (e) { _tried = new Set(); }
        return _tried;
    }
    A.isTried = function (id) { return tried().has(String(id)); };
    A.markTried = function (id) {
        id = String(id || '').replace(/^mono:/, '');
        if (!id || id === 'none') return;
        var t = tried();
        if (t.has(id)) return;
        t.add(id);
        try { localStorage.setItem(TRIED_KEY, JSON.stringify(Array.from(t))); } catch (e) {}
        // live-update badges + meters without a rerender
        try {
            document.querySelectorAll('.swatch-item[data-finish-id="' + id + '"]').forEach(function (c) {
                c.classList.add('atlas-tried');
            });
            A.refreshMeters();
        } catch (e) {}
    };

    /* ---------------- tag bar ---------------- */
    A.TAGS = ['#carbon', '#chrome', '#metallic', '#candy', '#pearl', '#chameleon', '#fire', '#ice', '#galaxy',
              '#matte', '#gold', '#neon', '#glass', '#crystal', '#copper', '#grunge', '#scales', '#luxury',
              '#tactical', '#racing', '#toxic', '#fractured', '#gradient', '#stone', '#retro', '#glitch',
              '#dark', '#rainbow', '#usa', '#japan'];
    A.activeTag = '';

    function _norm(s) {
        try { if (typeof _normSearch === 'function') return _normSearch(s); } catch (e) {}
        return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    }
    function _tagCounts(grid) {
        var cards = grid.querySelectorAll('.swatch-item[data-finish-id]');
        var hays = [];
        cards.forEach(function (c) {
            hays.push(_norm((c.getAttribute('data-name') || '') + ' ' + (c.getAttribute('data-search') || '') + ' '
                + (c.getAttribute('data-desc') || '') + ' ' + (c.getAttribute('data-finish-id') || '') + ' '
                + (c.getAttribute('data-tags') || '')));
        });
        var out = {};
        A.TAGS.forEach(function (t) {
            var syn = null;
            try { syn = (typeof _SPB_SEARCH_SYNONYMS !== 'undefined') ? _SPB_SEARCH_SYNONYMS[t.slice(1)] : null; } catch (e) {}
            var needles = [ _norm(t.slice(1)) ];
            if (syn && syn.length) needles = syn.map(_norm).filter(Boolean);
            var n = 0;
            for (var i = 0; i < hays.length; i++) {
                for (var j = 0; j < needles.length; j++) { if (hays[i].indexOf(needles[j]) >= 0) { n++; break; } }
            }
            out[t] = n;
        });
        return out;
    }

    A.renderTagBar = function () {
        var grid = document.getElementById('swatchPopupGrid');
        // the static "Try" row: parent of any setSwatchSmartSearch button
        var probe = document.querySelector('#swatchPopup [onclick*="setSwatchSmartSearch"]');
        var host = probe ? probe.parentElement : null;
        if (!grid || !host) return;
        var counts = _tagCounts(grid);
        var order = A.TAGS.slice().sort(function (a, b) { return (counts[b] || 0) - (counts[a] || 0); });
        var top = order.slice(0, 14).filter(function (t) { return counts[t] > 0; });
        var rest = order.slice(14).filter(function (t) { return counts[t] > 0; });
        var h = '<span class="atlas-tag-lead">Dig in:</span>';
        top.forEach(function (t) {
            h += '<button type="button" class="atlas-tag' + (A.activeTag === t ? ' active' : '') + '" data-tag="' + t + '">'
               + t + '<span class="atlas-tag-n">' + counts[t] + '</span></button>';
        });
        if (rest.length) {
            h += '<button type="button" class="atlas-tag atlas-tag-more" data-more="1">+' + rest.length + ' more</button>';
            h += '<span class="atlas-tag-drawer" style="display:none;">';
            rest.forEach(function (t) {
                h += '<button type="button" class="atlas-tag' + (A.activeTag === t ? ' active' : '') + '" data-tag="' + t + '">'
                   + t + '<span class="atlas-tag-n">' + counts[t] + '</span></button>';
            });
            h += '</span>';
        }
        h += '<button type="button" class="atlas-tag atlas-tag-lucky" data-lucky="1" title="Jump to one random finish you haven\'t tried yet">🎲 SURPRISE ME</button>';
        host.classList.add('atlas-tag-bar');
        host.innerHTML = h;
        host.onclick = function (ev) {
            var b = ev.target.closest('button'); if (!b) return;
            if (b.dataset.more) {
                var d = host.querySelector('.atlas-tag-drawer');
                if (d) d.style.display = d.style.display === 'none' ? 'inline' : 'none';
                b.textContent = d && d.style.display !== 'none' ? '− less' : '+' + rest.length + ' more';
                return;
            }
            if (b.dataset.lucky) { A.surprise(); return; }
            var t = b.dataset.tag; if (!t) return;
            A.activeTag = (A.activeTag === t) ? '' : t;
            host.querySelectorAll('.atlas-tag').forEach(function (x) {
                x.classList.toggle('active', x.dataset.tag === A.activeTag);
            });
            if (typeof setSwatchSmartSearch === 'function') setSwatchSmartSearch(A.activeTag ? A.activeTag.slice(1) : '');
        };
    };

    /* ---------------- surprise + daily picks ---------------- */
    function _allCards() {
        var grid = document.getElementById('swatchPopupGrid');
        return grid ? Array.prototype.slice.call(grid.querySelectorAll('.swatch-item[data-finish-id]')) : [];
    }
    A.surprise = function () {
        var cards = _allCards();
        if (!cards.length) return;
        var untried = cards.filter(function (c) { return !A.isTried(c.getAttribute('data-finish-id')); });
        var pool = (untried.length && Math.random() < 0.85) ? untried : cards;
        var pick = pool[Math.floor(Math.random() * pool.length)];
        A.jumpTo(pick);
    };
    A.jumpTo = function (card) {
        if (!card) return;
        var grp = card.closest('.swatch-group');
        if (grp && grp.closest('.atlas-section')) A.zoomInto(grp);
        else if (grp) grp.classList.remove('collapsed');
        try { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) { card.scrollIntoView(); }
        card.classList.remove('atlas-flash');           // restart animation
        void card.offsetWidth;
        card.classList.add('atlas-flash');
        setTimeout(function () { card.classList.remove('atlas-flash'); }, 2600);
    };
    function _daySeed() {
        var d = new Date();
        var s = d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
        return function () { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    }
    A.renderDailyPicks = function () {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid || grid.querySelector('.atlas-daily')) return;
        var cards = _allCards();
        if (cards.length < 20) return;
        var rnd = _daySeed(), used = {}, picks = [];
        var guard = 0;
        while (picks.length < 5 && guard++ < 200) {
            var c = cards[Math.floor(rnd() * cards.length)];
            var id = c.getAttribute('data-finish-id');
            if (!used[id]) { used[id] = 1; picks.push(c); }
        }
        var h = '<div class="atlas-daily"><span class="atlas-daily-lead">🗓 TODAY\'S 5 <em>— fresh picks every day</em></span>';
        picks.forEach(function (c, i) {
            var name = (c.getAttribute('data-sort-name') || c.getAttribute('data-name') || '').split(' ').slice(0, 4).join(' ');
            var sq = c.querySelector('.swatch-square, .swatch-split');
            var thumb = sq ? sq.outerHTML : '';
            h += '<button type="button" class="atlas-daily-card" data-idx="' + i + '" title="Jump to this finish">'
               + '<span class="atlas-daily-thumb">' + thumb + '</span><span class="atlas-daily-name">' + name + '</span></button>';
        });
        h += '</div>';
        grid.insertAdjacentHTML('afterbegin', h);
        var bar = grid.querySelector('.atlas-daily');
        bar.onclick = function (ev) {
            var b = ev.target.closest('.atlas-daily-card'); if (!b) return;
            A.jumpTo(picks[Number(b.dataset.idx)]);
        };
    };

    /* ---------------- meters ---------------- */
    A.refreshMeters = function () {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid) return;
        var total = 0, done = 0;
        grid.querySelectorAll('.atlas-section .swatch-group').forEach(function (grp) {
            var cards = grp.querySelectorAll('.swatch-item[data-finish-id]');
            var t = 0;
            cards.forEach(function (c) { if (A.isTried(c.getAttribute('data-finish-id'))) t++; });
            total += cards.length; done += t;
            var m = grp.querySelector('.atlas-grp-meter');
            if (m) {
                m.querySelector('.atlas-grp-meter-fill').style.width = cards.length ? Math.round(100 * t / cards.length) + '%' : '0%';
                m.querySelector('.atlas-grp-meter-txt').textContent = t + '/' + cards.length;
                m.title = 'You have tried ' + t + ' of the ' + cards.length + ' finishes in this category';
            }
        });
        var head = document.querySelector('.atlas-progress');
        if (!head) {
            var count = document.getElementById('swatchPopupResultCount');
            if (count && count.parentElement) {
                count.insertAdjacentHTML('beforebegin',
                    '<span class="atlas-progress" title="Every finish you apply gets checked off — explore the whole catalog!">' +
                    '<span class="atlas-progress-bar"><span class="atlas-progress-fill"></span></span>' +
                    '<span class="atlas-progress-txt"></span></span>');
                head = document.querySelector('.atlas-progress');
            }
        }
        if (head) {
            head.querySelector('.atlas-progress-fill').style.width = total ? Math.max(1, Math.round(100 * done / total)) + '%' : '0%';
            head.querySelector('.atlas-progress-txt').textContent = 'Explored ' + done + ' of ' + total;
        }
    };

    /* ---------------- ZOOM navigation (v2, 2026-08-01) ----------------
       Owner rejected the v1 in-place accordion: cards got stuck open (the
       stock label toggle + the card's expand-only listener double-fired) and
       mixed-height expanded groups made the grid ragged. v2 model:
         LEVEL 1  uniform collapsed category cards — click anywhere = zoom in
         LEVEL 2  the grid shows ONLY that category + a sticky back bar
       One capture-phase router owns all atlas clicks; the stock inline
       label onclick never fires inside atlas sections. */
    A.zoomInto = function (grp) {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid || !grp) return;
        A.zoomOut(true);                                    // clear any prior zoom
        var sec = grp.closest('.atlas-section');
        if (!sec) return;
        var scroller = A._scroller();
        A._scrollBack = scroller ? scroller.scrollTop : 0;
        grp.classList.remove('collapsed');
        grp.classList.add('atlas-zoom-target');
        sec.classList.add('atlas-zoom-host');
        grid.classList.add('atlas-zoomed');
        if (typeof window._installSwatchPopupLazyLoader === 'function') window._installSwatchPopupLazyLoader();
        var name = grp.getAttribute('data-picker-category') || '';
        var n = grp.querySelectorAll('.swatch-item[data-finish-id]').length;
        var bar = document.createElement('div');
        bar.className = 'atlas-zoom-bar';
        bar.innerHTML = '<button type="button" class="atlas-zoom-back">&larr; ALL CATEGORIES</button>'
            + '<span class="atlas-zoom-name">' + A.displayName(name).replace(/</g, '&lt;') + '</span>'
            + '<span class="atlas-zoom-count">' + n + ' finishes</span>'
            + '<div class="atlas-zoom-desc">' + A.desc(name).replace(/</g, '&lt;') + '</div>';
        grid.insertBefore(bar, grid.firstChild);
        var chapters = grp.querySelectorAll('.spb-finish-subsection');
        if (chapters.length) {
            var nav = document.createElement('div'); nav.className = 'atlas-subsection-nav';
            var all = document.createElement('button'); all.type='button'; all.dataset.atlasSubsection=''; all.textContent='All '+n; all.setAttribute('aria-pressed','true'); nav.appendChild(all);
            chapters.forEach(function(chapter) {
                var b=document.createElement('button'); b.type='button'; b.dataset.atlasSubsection=chapter.dataset.finishSubsection;
                b.textContent=chapter.dataset.finishSubsection+' '+chapter.querySelectorAll('.swatch-item[data-finish-id]').length;
                b.setAttribute('aria-pressed','false'); nav.appendChild(b);
            });
            bar.appendChild(nav);
        }
        if (scroller) scroller.scrollTop = 0;
    };
    A.showSubsection = function (grp, name) {
        if (!grp) return;
        grp.querySelectorAll('.spb-finish-subsection').forEach(function(chapter) {
            chapter.classList.toggle('atlas-subsection-hidden', !!name && chapter.dataset.finishSubsection !== name);
        });
        var grid=document.getElementById('swatchPopupGrid');
        if (grid) grid.querySelectorAll('[data-atlas-subsection]').forEach(function(b) { b.setAttribute('aria-pressed',String(b.dataset.atlasSubsection===name)); });
        if (typeof window._installSwatchPopupLazyLoader === 'function') window._installSwatchPopupLazyLoader();
    };
    A.zoomOut = function (silent) {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid) return;
        var bar = grid.querySelector('.atlas-zoom-bar');
        if (bar) bar.remove();
        var t = grid.querySelector('.atlas-zoom-target');
        if (t) { A.showSubsection(t,''); t.classList.add('collapsed'); t.classList.remove('atlas-zoom-target'); }
        var h = grid.querySelector('.atlas-zoom-host');
        if (h) h.classList.remove('atlas-zoom-host');
        var was = grid.classList.contains('atlas-zoomed');
        grid.classList.remove('atlas-zoomed');
        if (!silent && was) {
            var scroller = A._scroller();
            if (scroller) scroller.scrollTop = A._scrollBack || 0;
        }
    };
    /* ---------------- land in the category you were already in ----------------
       SPB-UIUX-2026-08-30 (owner): "when you click the dropdown box to CHANGE a
       BASE MATERIAL it automatically opens up the category it was in before ...
       Always to the last category."

       In atlas terms "opens the category" means ZOOM INTO it (Level 2) — merely
       un-collapsing the card is undone by organize()'s uniform-card pass and by
       afterFilter(). Called by the openSwatchPicker wrapper AFTER organize(), so
       it is the last word on the picker's landing state. */
    A.openCurrentCategory = function (type) {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid || grid.classList.contains('atlas-searching')) return;
        // 1. the lane holding the finish this zone is wearing right now
        var sel = grid.querySelector('.swatch-item.selected');
        var grp = (sel && sel.closest) ? sel.closest('.swatch-group') : null;
        // 2. nothing set -> the lane the last pick came from
        if (!grp && typeof window._spbGetLastPickerCategory === 'function') {
            var last = window._spbGetLastPickerCategory(type);
            if (last) {
                grp = grid.querySelector('.atlas-section .swatch-group[data-picker-category="'
                                         + String(last).replace(/"/g, '\\"') + '"]');
            }
        }
        // A category card only zooms from inside a section (pattern pickers keep
        // the stock layout — organize() returns early for them).
        if (!grp || !grp.closest('.atlas-section')) return;
        A.zoomInto(grp);
    };

    /* the popup's actual scroll container (grid itself or nearest scrolling ancestor) */
    A._scroller = function () {
        var grid = document.getElementById('swatchPopupGrid');
        var el = grid;
        while (el && el !== document.body) {
            if (el.scrollHeight > el.clientHeight + 4) {
                var o = getComputedStyle(el).overflowY;
                if (o === 'auto' || o === 'scroll') return el;
            }
            el = el.parentElement;
        }
        return grid;
    };
    A._router = function (grid) {
        if (grid._atlasRouter) return;
        grid._atlasRouter = true;
        grid.addEventListener('click', function (ev) {
            var chapterButton=ev.target.closest('[data-atlas-subsection]');
            if (chapterButton) {
                ev.stopPropagation(); ev.preventDefault();
                A.showSubsection(grid.querySelector('.atlas-zoom-target'),chapterButton.dataset.atlasSubsection || '');
                var chapterScroll=A._scroller(); if (chapterScroll) chapterScroll.scrollTop=0;
                return;
            }
            if (ev.target.closest('.atlas-zoom-back')) {
                ev.stopPropagation(); ev.preventDefault();
                A.zoomOut();
                return;
            }
            if (!grid.classList.contains('atlas-zoomed')) {
                if (grid.classList.contains('atlas-searching')) return;  // flat results keep stock behavior
                var card = ev.target.closest('.atlas-grid > .swatch-group.collapsed');
                if (card && !ev.target.closest('.swatch-item, .swatch-fav-btn, input, button')) {
                    ev.stopPropagation(); ev.preventDefault();
                    A.zoomInto(card);
                }
            } else if (ev.target.closest('.swatch-group-label')) {
                // inside the zoom view the stock collapse toggle must never fire
                ev.stopPropagation(); ev.preventDefault();
            }
        }, true);
    };

    /* ---------------- live subsection adapter ----------------
       SPB-105 / CORE-WORKS 2026-09-30: the production legacy picker still
       builds its grid directly; extracted grid-builder modules are dormant.
       Move the actual cards into chapter rows before sorting/Atlas grouping.
       Keep their selection/favorite handlers, preview nodes and stable IDs. */
    A.ensureSubsections = function (grp) {
        var name = grp.getAttribute('data-picker-category') || '';
        var chapters = (window.BASE_GROUP_SUBSECTIONS || {})[name];
        if (!chapters || !chapters.length || grp.querySelector('.spb-finish-subsection')) return;
        var cards = Array.prototype.slice.call(grp.querySelectorAll('.swatch-item[data-finish-id]'));
        var oldRows = Array.prototype.slice.call(grp.querySelectorAll('.swatch-grid-row'));
        var bases = typeof BASES !== 'undefined' ? BASES : (window.BASES || []);
        chapters.forEach(function (chapter) {
            var members = cards.filter(function (card) { return chapter.ids.indexOf(card.getAttribute('data-finish-id')) >= 0; });
            if (!members.length) return;
            var section = document.createElement('section'); section.className = 'spb-finish-subsection';
            section.dataset.finishSubsection = chapter.name;
            var label = document.createElement('div'); label.className = 'spb-finish-subsection-label'; label.textContent = chapter.name + ' ';
            var count = document.createElement('span'); count.textContent = members.length + ' finishes'; label.appendChild(count);
            var desc = document.createElement('p'); desc.className = 'spb-finish-subsection-desc'; desc.textContent = chapter.description;
            var row = document.createElement('div'); row.className = 'swatch-grid-row';
            members.forEach(function (card) {
                var item = bases.find(function (b) { return b.id === card.getAttribute('data-finish-id'); });
                card.dataset.search = ((card.dataset.search || card.dataset.name || '') + ' ' + chapter.name + ' ' + (item && item.sourceShelf || '')).toLowerCase();
                row.appendChild(card);
            });
            section.appendChild(label); section.appendChild(desc); section.appendChild(row); grp.appendChild(section);
        });
        oldRows.forEach(function (row) { if (!row.querySelector('.swatch-item')) row.remove(); });
    };

    /* ---------------- the organizer ---------------- */
    A.organize = function () {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid) return;
        var groups = Array.prototype.slice.call(grid.querySelectorAll('.swatch-group'));
        if (!groups.length) return;
        groups.forEach(A.ensureSubsections);
        // fresh open: the grid element persists across opens, its innerHTML doesn't —
        // clear any zoom/search classes left from the previous session
        grid.classList.remove('atlas-zoomed', 'atlas-searching');
        // pattern pickers keep their existing layout
        var kinds = {};
        groups.forEach(function (g) { kinds[g.getAttribute('data-picker-types') || ''] = 1; });
        if (kinds['pattern'] && !kinds['base'] && !kinds['monolithic']) return;

        // 1. drop the old full-width section divider bars
        grid.querySelectorAll('.swatch-section-divider').forEach(function (d) { d.remove(); });

        // 2. bucket groups into sections (favorites group stays out, on top)
        var buckets = {}; A.SECTIONS.forEach(function (s) { buckets[s.id] = []; });
        groups.forEach(function (g) {
            var label = g.querySelector('.swatch-group-label');
            if (!label || g.querySelector('.swatch-favorites-label')) return;   // favorites shelf stays put
            var name = g.getAttribute('data-picker-category') || '';
            if (!name) return;
            var sec = A.classify(name, g.getAttribute('data-picker-types') || '');
            (buckets[sec] || buckets.shokker).push({ name: name, el: g });
        });

        // 3. order within sections
        buckets.foundations.sort(function (a, b) {
            return FOUNDATIONS_ORDER.indexOf(a.name) - FOUNDATIONS_ORDER.indexOf(b.name);
        });
        A.SECTIONS.forEach(function (s) {
            if (s.id === 'foundations') return;
            buckets[s.id].sort(function (a, b) { return A.sortKey(a.name).localeCompare(A.sortKey(b.name)); });
        });

        // 4. build section shells and move the group cards in.
        // BUG FIXED 2026-07-31 (self-inflicted, cost a debugging hour): the anchor
        // must be a node that STAYS in the grid. Using the first .swatch-group as
        // the anchor failed silently — by insert time that group had been MOVED
        // into the fragment, so insertBefore threw NotFoundError, the wrapper's
        // try/catch swallowed it, and every group vanished inside the detached
        // fragment leaving a 338-byte grid. A dedicated placeholder cannot move.
        var anchor = document.createElement('div');
        anchor.className = 'atlas-anchor';
        var firstGroup = grid.querySelector('.swatch-group');
        grid.insertBefore(anchor, firstGroup);
        var frag = document.createDocumentFragment();
        A.SECTIONS.forEach(function (s) {
            var list = buckets[s.id];
            if (!list || !list.length) return;
            var nFin = list.reduce(function (n, g) { return n + g.el.querySelectorAll('.swatch-item[data-finish-id]').length; }, 0);
            var sec = document.createElement('div');
            sec.className = 'atlas-section';
            sec.setAttribute('data-atlas-section', s.id);
            sec.innerHTML = '<div class="atlas-section-head">'
                + '<span class="atlas-section-icon">' + s.icon + '</span>'
                + '<span class="atlas-section-name">' + s.label + '</span>'
                + '<span class="atlas-section-count">' + list.length + ' categories · ' + nFin + ' finishes</span>'
                + '<div class="atlas-section-intro">' + s.intro + '</div></div>'
                + '<div class="atlas-grid" style="--atlas-cols:' + s.cols + ';"></div>';
            var g4 = sec.querySelector('.atlas-grid');
            list.forEach(function (item) {
                A.dressGroup(item.el, item.name);
                g4.appendChild(item.el);
            });
            frag.appendChild(sec);
        });
        grid.insertBefore(frag, anchor);
        anchor.remove();

        // 5. alphabetical finishes inside every category (Grouped default view):
        //    resort + RENUMBER data-original-index so _applySwatchPopupSort's
        //    "default" mode (which sorts by originalIndex) now means A-Z.
        var idx = 0;
        grid.querySelectorAll('.swatch-grid-row').forEach(function (row) {
            var cards = Array.prototype.slice.call(row.querySelectorAll('.swatch-item'));
            cards.sort(function (a, b) {
                return String(a.dataset.sortName || '').localeCompare(String(b.dataset.sortName || ''));
            });
            cards.forEach(function (c) { c.dataset.originalIndex = String(idx++); row.appendChild(c); });
        });

        // 6. tried badges
        grid.querySelectorAll('.swatch-item[data-finish-id]').forEach(function (c) {
            c.classList.toggle('atlas-tried', A.isTried(c.getAttribute('data-finish-id')));
        });

        // 7. v2 uniform card home: EVERY category starts as a closed card
        //    (stock render leaves Foundation expanded), and the router owns clicks
        grid.querySelectorAll('.atlas-section .swatch-group').forEach(function (g) { g.classList.add('collapsed'); });
        A._router(grid);

        A.renderTagBar();
        A.renderDailyPicks();
        A.refreshMeters();
    };

    /* Card dressing: tagline + full description + explored meter on each group. */
    A.dressGroup = function (g, name) {
        if (g.getAttribute('data-atlas-dressed')) return;
        g.setAttribute('data-atlas-dressed', '1');
        var label = g.querySelector('.swatch-group-label');
        // display rename (EFX) — replace only the leading text node
        if (label && A.displayName(name) !== name) {
            var tn = label.firstChild;
            if (tn && tn.nodeType === 3) tn.nodeValue = A.displayName(name) + ' ';
        }
        // rich description: replace/augment the stock one-liner
        var desc = g.querySelector('.swatch-group-desc');
        if (!desc) {
            desc = document.createElement('div');
            desc.className = 'swatch-group-desc';
            g.insertBefore(desc, label ? label.nextSibling : g.firstChild);
        }
        desc.textContent = (g.getAttribute('data-picker-types') === 'spec_overlay')
            ? (window.SPB_SPEC_OVERLAY_V2?.families.find(f => f.name === name)?.desc || 'Legacy spec overlays retained for existing recipes and familiar constructions.')
            : A.desc(name);
        // v2: no per-card listener. The capture-phase router (A._router) owns
        // ALL atlas clicks. v1's card listener only ever REMOVED .collapsed, so
        // the label's stock toggle got instantly reverted by the bubbling click
        // and cards were stuck open — the owner's "they won't collapse" bug.
        // per-category explored meter, lives in the label row
        if (label && !label.querySelector('.atlas-grp-meter')) {
            var m = document.createElement('span');
            m.className = 'atlas-grp-meter';
            m.innerHTML = '<span class="atlas-grp-meter-bar"><span class="atlas-grp-meter-fill"></span></span><span class="atlas-grp-meter-txt"></span>';
            label.appendChild(m);
        }
    };

    /* Keep sections/meters honest while searching: hide a section when every
       group in it is hidden; also flip the popup into "search mode" so the
       card grid relaxes to full-width rows (all groups auto-expand there). */
    A.afterFilter = function () {
        var grid = document.getElementById('swatchPopupGrid');
        if (!grid) return;
        var searching = false;
        try {
            var inp = document.getElementById('swatchSearchInput');
            searching = !!(inp && inp.value.trim()) || (window.swatchPopupState && swatchPopupState.filter && swatchPopupState.filter !== 'all');
        } catch (e) {}
        grid.classList.toggle('atlas-searching', !!searching);
        if (searching) {
            A.zoomOut(true);        // search always shows global flat results
            // Owner 2026-09-15: search and Favorites must expose matching
            // cards for every picker, including the category just zoomed out.
            grid.querySelectorAll('.swatch-group').forEach(function (g) {
                if (g.style.display !== 'none') g.classList.remove('collapsed');
            });
        } else if (!grid.classList.contains('atlas-zoomed')) {
            // search cleared → back to the card home; re-close whatever the
            // stock filter expanded so every category is a uniform card again
            grid.querySelectorAll('.atlas-section .swatch-group').forEach(function (g) { g.classList.add('collapsed'); });
        } else {
            // The stock sort/filter pass can re-collapse the focused category.
            // Preserve the zoom invariant so chapter containers stay visible.
            var focused = grid.querySelector('.atlas-zoom-target');
            if (focused) focused.classList.remove('collapsed');
        }
        grid.querySelectorAll('.atlas-section').forEach(function (sec) {
            var any = false;
            sec.querySelectorAll('.swatch-group').forEach(function (g) {
                if (g.style.display !== 'none') any = true;
            });
            sec.style.display = any ? '' : 'none';
        });
        grid.querySelectorAll('.spb-finish-subsection').forEach(function(chapter) {
            var visible=Array.prototype.some.call(chapter.querySelectorAll('.swatch-item'),function(c) { return c.style.display !== 'none'; });
            chapter.classList.toggle('atlas-subsection-empty',!visible);
        });
    };

    /* ---------------- runtime wiring (no core-file edits) ---------------- */
    /* Three NON-EMPTY groups were in no SPECIALS_SECTIONS entry, so the picker
       never rendered them at all — 77 finishes invisible to every user:
         Aurora & Chromatic Flow [30] · Chromatic Flake [30] · Atelier — Ultra Detail [17]
       organize() can only rehome rendered groups, so they must be injected into
       the section lists BEFORE the builder runs. Runtime-patch, duplicate-safe,
       no data-file edit (Kimi K3 is mid-flight in that file). */
    // [2026-09-05 RETIRED LEDGER] rescueOrphans() is GONE. The three groups it re-injected
    // (Aurora & Chromatic Flow, Chromatic Flake, Atelier - Ultra Detail) were pulled by the
    // owner on 2026-06-03 and are on scripts/retired_catalog.json (owner 2026-09-05: "hide
    // both"; "things that are supposed to be dead and buried stay dead and buried"). A group
    // that is in no section is NOT an orphan to rescue - check the ledger first:
    //     python scripts/spb_retired_gate.py

    function wire() {
        if (typeof window.openSwatchPicker === 'function' && !window.openSwatchPicker._atlas) {
            var _open = window.openSwatchPicker;
            window.openSwatchPicker = function () {
                var r = _open.apply(this, arguments);
                try { A.organize(); } catch (e) { console.warn('[Atlas] organize failed', e); }
                try { A.openCurrentCategory(arguments[1]); } catch (e) {}
                return r;
            };
            window.openSwatchPicker._atlas = true;
        }
        if (typeof window.filterSwatchPopup === 'function' && !window.filterSwatchPopup._atlas) {
            var _filt = window.filterSwatchPopup;
            window.filterSwatchPopup = function (q) {
                var r = _filt.apply(this, arguments);
                try { A.afterFilter(); } catch (e) {}
                return r;
            };
            window.filterSwatchPopup._atlas = true;
        }
        if (typeof window.selectSwatchItem === 'function' && !window.selectSwatchItem._atlas) {
            var _sel = window.selectSwatchItem;
            window.selectSwatchItem = function (id) {
                try { A.markTried(id); } catch (e) {}
                return _sel.apply(this, arguments);
            };
            window.selectSwatchItem._atlas = true;
        }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire, { once: true });
    else wire();
    // Late-loading safety: if the picker functions appear after us, re-wire once.
    setTimeout(wire, 2500);
})();
