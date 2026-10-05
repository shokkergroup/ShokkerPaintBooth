/* ============================================================================
   SPB EASY TELL — language engine v2  (SPB-EASY-TELL2 2026-09-30)
   "Tell Shokker what you want" — the brain. Pure logic: no DOM, no network, no LLM,
   no globals other than window.SpbTellNLU (or module.exports under Node, where
   _easy_claude_work/tell_tests/run.js exercises it against the real catalog).

   parse(text, world) -> plan
     world = { parts:[{idx,name,label,kind,tone,hex,share,finish,layerId,pick}],
               layers:[{id,name}], ctx:{selected,last:{targets}}, index: buildIndex(...) }
     plan  = { text, cmds:[cmd], notes:[str], leftover:[str], fixes:[[typed,read]] }
     cmd   = { type:'style'|'adjust'|'undo'|'redo'|'startover'|'another'|'help'|'surprise'|'more'|'less',
               targets:[{kind:'part',idx}|{kind:'layer',layerId,name}|{kind:'whole'}|{kind:'colors'}],
               exclude:[target], needsTarget:bool, color:{mode,hex,word,fromIdx,fromName}|null,
               finish:{key,name,via,family,alts:[key]}|null, how:'all'|'blend'|'shine'|null, amount:0..1|null,
               adjusts:[{op,dir,mag}], recipe:id|null, said:'the words this command came from' }

   ES5 only (old Electron): var/function, no arrows, no template literals.
   ========================================================================== */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.SpbTellNLU = api;
})(typeof window !== 'undefined' ? window : this, function () {
    'use strict';

    // ---------------------------------------------------------------- text utils
    function norm(s) {
        return String(s == null ? '' : s).toLowerCase()
            .replace(/[‘’]/g, "'")
            .replace(/\bcolou?r(s|ed|ing)?\b/g, function (m) { return m.replace('colour', 'color'); })
            .replace(/\bgrey\b/g, 'gray').replace(/\bgreys\b/g, 'grays')
            .replace(/\blet's\b/g, 'lets').replace(/\bdon't\b/g, 'dont').replace(/\bdoesn't\b/g, 'doesnt').replace(/\bcan't\b/g, 'cant').replace(/\bi'd\b/g, 'id').replace(/\bthat's\b/g, 'thats').replace(/\bit's\b/g, 'its').replace(/\bwhat's\b/g, 'whats')
            .replace(/([a-z])'s\b/g, '$1s')
            .replace(/([,;])/g, ' $1 ').replace(/[.!?]+(\s|$)/g, ' ; ')
            .replace(/(\d)\s*(%|percent|pct)\b/g, '$1%')
            .replace(/[^a-z0-9#%,;]+/g, ' ').replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
    }
    function stem(w) {
        if (w.length > 4 && /ies$/.test(w)) return w.slice(0, -3) + 'y';
        if (w.length > 3 && /s$/.test(w) && !/(ss|us|is)$/.test(w)) return w.slice(0, -1);
        return w;
    }
    function toks(s) { var n = norm(s); return n ? n.split(' ') : []; }
    function isHex(s) { return /^#[0-9a-f]{6}$/i.test(String(s || '')); }
    function uniq(a) { var seen = {}, out = []; for (var i = 0; i < a.length; i++) { if (!seen[a[i]]) { seen[a[i]] = 1; out.push(a[i]); } } return out; }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
    function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

    // Damerau-Levenshtein, bounded (for typo repair on short vocab words)
    function editDistance(a, b, max) {
        if (a === b) return 0;
        var la = a.length, lb = b.length;
        if (Math.abs(la - lb) > max) return max + 1;
        var prev2 = null, prev = [], cur = [], i, j;
        for (j = 0; j <= lb; j++) prev.push(j);
        for (i = 1; i <= la; i++) {
            cur = [i]; var best = i;
            for (j = 1; j <= lb; j++) {
                var cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
                var v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
                if (prev2 && i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1)) v = Math.min(v, prev2[j - 2] + 1);
                cur.push(v); if (v < best) best = v;
            }
            if (best > max) return max + 1;
            prev2 = prev; prev = cur;
        }
        return prev[lb];
    }

    // ---------------------------------------------------------------- colours
    // One line per name: "name hex". Multi-word names are matched longest-first. Values are the plain,
    // representative colour of that word (what "make it X" should put on the car).
    var COLOR_LINES = [
        'red d81e1e', 'crimson b0122a', 'scarlet e0281b', 'maroon 7a1226', 'burgundy 6d1230', 'cherry c2182f', 'ruby a1142b', 'wine 722f37', 'brick a03a2c', 'coral ff6f61', 'salmon fa8072', 'rose e0507a', 'candy apple red b1121b', 'fire engine red d0101a', 'racing red d81e1e', 'blood red 8a0303',
        'orange ff7a18', 'tangerine ff8c1a', 'amber ffb000', 'burnt orange cc5500', 'pumpkin ff7518', 'peach ffb38a', 'apricot fbb26a', 'sunset orange ff6a2a', 'safety orange ff6700',
        'yellow f5d016', 'lemon f7e01d', 'canary ffe135', 'mustard d1a300', 'banana ffe57a', 'sunshine ffd200', 'school bus yellow ffd800', 'hi vis yellow e6ff00', 'high vis yellow e6ff00',
        'lime 9be21b', 'chartreuse 9de600', 'neon green 39ff14', 'lime green 9be21b', 'bright green 2bd94a', 'acid green b0ff00', 'toxic green 6bff00',
        'green 1f9d3a', 'forest green 1d5c2e', 'dark green 14532d', 'olive 6b7a1f', 'emerald 0f9d58', 'mint 8de3b5', 'sage 87a78a', 'army green 4b5320', 'british racing green 004225', 'kelly green 2ca02c', 'hunter green 2f5233', 'seafoam 7fe0c0', 'jade 00a86b',
        'teal 12907c', 'turquoise 1fc4b6', 'aqua 33d6d0', 'dark teal 0b5d55',
        'cyan 1fc4e8', 'ice blue a8e6ff', 'light blue 6fb7ff', 'baby blue 9fd0ff', 'sky blue 4fb0ff', 'powder blue b0d4f1', 'electric blue 0a7bff', 'cyan blue 1fa9e8',
        'blue 1e56d8', 'royal blue 2b4fd8', 'cobalt 0047ab', 'sapphire 0f3fa6', 'denim 3a5f9a', 'azure 0a84ff', 'cornflower 6495ed', 'ocean blue 0f5fa8',
        'navy 14245f', 'navy blue 14245f', 'midnight blue 0a1a4a', 'dark blue 0c2a78', 'midnight 0a1a4a', 'indigo 3b1f8f',
        'purple 6a2fc9', 'violet 8a2be2', 'lavender b79cf2', 'lilac c8a2f0', 'plum 6b2a6b', 'grape 5a2a8a', 'amethyst 9966cc', 'dark purple 3b1470', 'eggplant 3d1a47', 'royal purple 5a2ca0', 'deep purple 3b1470',
        'magenta d21ec0', 'fuchsia e0219a', 'hot pink ff2d95', 'raspberry c2185b', 'orchid c86bd6',
        'pink ff5fa8', 'baby pink ffc0d9', 'light pink ffb6cf', 'bubblegum ff8acb', 'blush f3b7c2', 'pastel pink ffc4d8', 'neon pink ff2fb0',
        'brown 6b3f1d', 'chocolate 4a2a14', 'coffee 4b2e1e', 'espresso 3a2216', 'chestnut 8a4b2a', 'caramel b8763a', 'mocha 5c3a28', 'walnut 5a3a24', 'mahogany 4e1f12', 'sienna 8a4a2a',
        'tan c9a77a', 'beige d8c3a0', 'khaki b5a26a', 'sand d9c49a', 'desert sand d8b98a', 'taupe 9a8a7a', 'camel c19a6b', 'cream f3ecd0', 'ivory f5f0e0', 'champagne f1dfb0',
        'gold c9a227', 'golden c9a227', 'bronze 9c6b30', 'brass b5a642', 'copper b87333', 'rose gold b76e79', 'old gold a88a2a',
        'silver b9bec7', 'platinum d5d7dc', 'titanium 878681', 'steel 8a94a3', 'gunmetal 43484f', 'gun metal 43484f', 'chrome silver c8ccd2', 'aluminum a9b0b8', 'pewter 8f979a', 'nickel a7acb1',
        'gray 6b6f78', 'charcoal 33363b', 'slate 5b6470', 'ash 9aa0a6', 'graphite 3a3d42', 'smoke 7a8088', 'light gray b8bcc4', 'dark gray 3a3e45', 'battleship gray 7d8590', 'concrete 8d8f8f', 'cement 8d8f8f',
        'black 111111', 'jet black 060606', 'midnight black 0a0a0c', 'onyx 0d0d10', 'ebony 0a0a0a', 'obsidian 0b0b12', 'coal 1a1a1a',
        'white f2f2f2', 'snow ffffff', 'pearl white f4f1ea', 'off white ece8dd', 'bone e6e0cc', 'chalk ececea', 'arctic white f6fbff', 'ghost white f4f5f8'
    ];
    // words that are colours only in combination (modifier + base colour)
    var COLOR_MODS = {
        dark: { l: -0.16, s: 0.0 }, deep: { l: -0.12, s: 0.10 }, light: { l: 0.16, s: -0.05 }, bright: { l: 0.06, s: 0.25 }, vivid: { l: 0.0, s: 0.3 }, pale: { l: 0.24, s: -0.25 },
        pastel: { l: 0.28, s: -0.15 }, neon: { l: 0.10, s: 0.55 }, hot: { l: 0.04, s: 0.35 }, electric: { l: 0.04, s: 0.4 }, muted: { l: 0.0, s: -0.3 }, dusty: { l: 0.06, s: -0.32 }, burnt: { l: -0.12, s: 0.0 }
    };
    var BASE19 = ['red', 'orange', 'yellow', 'lime', 'green', 'teal', 'cyan', 'blue', 'navy', 'purple', 'magenta', 'pink', 'brown', 'tan', 'gold', 'silver', 'gray', 'black', 'white'];
    var COLORS = {};                     // name -> '#rrggbb'
    var COLOR_MAXLEN = 1;
    (function () {
        for (var i = 0; i < COLOR_LINES.length; i++) {
            var line = COLOR_LINES[i], sp = line.lastIndexOf(' '), name = line.slice(0, sp), hex = '#' + line.slice(sp + 1);
            COLORS[name] = hex; var n = name.split(' ').length; if (n > COLOR_MAXLEN) COLOR_MAXLEN = n;
        }
    })();
    var METAL_WORDS = { gold: 1, golden: 1, silver: 1, copper: 1, bronze: 1, brass: 1, platinum: 1, titanium: 1, gunmetal: 1, 'gun metal': 1, steel: 1, aluminum: 1, 'rose gold': 1, 'old gold': 1, pewter: 1, nickel: 1, champagne: 1 };

    function hexToHsl(hex) {
        if (!isHex(hex)) return null;
        var r = parseInt(hex.substr(1, 2), 16) / 255, g = parseInt(hex.substr(3, 2), 16) / 255, b = parseInt(hex.substr(5, 2), 16) / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn, h = 0, s = 0;
        if (d > 0) {
            s = d / (1 - Math.abs(2 * l - 1));
            if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4;
            h *= 60; if (h < 0) h += 360;
        }
        return { h: h, s: s, l: l };
    }
    function hslToHex(h, s, l) {
        h = ((h % 360) + 360) % 360; s = clamp(s, 0, 1); l = clamp(l, 0, 1);
        var c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2, r, g, b;
        if (h < 60) { r = c; g = x; b = 0; } else if (h < 120) { r = x; g = c; b = 0; } else if (h < 180) { r = 0; g = c; b = x; } else if (h < 240) { r = 0; g = x; b = c; } else if (h < 300) { r = x; g = 0; b = c; } else { r = c; g = 0; b = x; }
        function hx(v) { var n = Math.round((v + m) * 255); return ('0' + n.toString(16)).slice(-2); }
        return '#' + hx(r) + hx(g) + hx(b);
    }
    // hue / saturation / lightness -> one of the 19 plain words (documented, deterministic; same rules as Easy v1)
    function colorWord(hex) {
        var c = hexToHsl(hex); if (!c) return null;
        var h = c.h, s = c.s, l = c.l;
        if (l < 0.12) return 'black';
        if (s < 0.14) { if (l > 0.86) return 'white'; if (l > 0.58) return 'silver'; return 'gray'; }
        if (l > 0.93 && s < 0.5) return 'white';
        if (h >= 12 && h < 48 && l < 0.36 && s < 0.85) return 'brown';
        if (h >= 20 && h < 48 && l > 0.55 && s < 0.5) return 'tan';
        if (h >= 38 && h < 56 && s >= 0.35 && l >= 0.30 && l <= 0.62 && (l < 0.50 || s < 0.75)) return 'gold';
        if (h >= 205 && h < 255 && l < 0.24) return 'navy';
        if ((h >= 330 || h < 12) && l > 0.68) return 'pink';
        if (h < 15 || h >= 345) return 'red';
        if (h < 42) return 'orange';
        if (h < 66) return 'yellow';
        if (h < 96) return 'lime';
        if (h < 165) return 'green';
        if (h < 188) return 'teal';
        if (h < 205) return 'cyan';
        if (h < 255) return 'blue';
        if (h < 290) return 'purple';
        if (h < 332) return 'magenta';
        return 'pink';
    }
    // words people type for a colour part label / colour that collapse to one of the 19 (matching parts by colour word)
    var WORD_TO_BASE = {
        golden: 'gold', violet: 'purple', lavender: 'purple', turquoise: 'teal', aqua: 'cyan', amber: 'orange', charcoal: 'gray', maroon: 'red', crimson: 'red', scarlet: 'red', lemon: 'yellow', beige: 'tan', cream: 'white', ivory: 'white',
        chocolate: 'brown', bronze: 'brown', slate: 'gray', taupe: 'tan', mint: 'green', olive: 'green', plum: 'purple', graphite: 'gray', platinum: 'silver', indigo: 'purple', fuchsia: 'magenta', coral: 'orange', khaki: 'tan', burgundy: 'red', cobalt: 'blue', copper: 'brown', 'sky blue': 'blue', 'light blue': 'cyan', 'ice blue': 'cyan', 'navy blue': 'navy', 'dark blue': 'navy', 'hot pink': 'pink', 'lime green': 'lime'
    };
    function lookupColor(phrase) {          // exact table lookup ("navy blue", "burnt orange") + "<modifier> <base>" derivation
        var p = phrase;
        if (COLORS[p]) return { hex: COLORS[p], word: baseWordOf(p, COLORS[p]) };
        var parts = p.split(' ');
        if (parts.length === 2 && COLOR_MODS[parts[0]] && COLORS[parts[1]]) {
            var c = hexToHsl(COLORS[parts[1]]), m = COLOR_MODS[parts[0]];
            var hex = hslToHex(c.h, c.s + m.s, c.l + m.l);
            return { hex: hex, word: baseWordOf(p, hex), mod: parts[0] };
        }
        return null;
    }
    function baseWordOf(name, hex) {
        if (COLORS[name] && BASE19.indexOf(name) !== -1) return name;
        if (WORD_TO_BASE[name]) return WORD_TO_BASE[name];
        var last = name.split(' ').pop();
        if (BASE19.indexOf(last) !== -1) return last;
        return colorWord(hex) || name;
    }
    function isColorPhrase(p) { return !!lookupColor(p); }

    // ---------------------------------------------------------------- finish families / vibes
    // Each family: the words people say (syn) and the catalog words used to rank (q). colorMode = what colour the
    // finish wears when the sentence names none: 'mine' keeps the part's own colour (candy/pearl/flake/matte/… are coatings
    // over YOUR colour); 'finish' uses the finish's own look (chrome, carbon, holographic are materials with an identity).
    var FAMILIES = [
        { id: 'chrome', label: 'chrome', syn: ['chrome', 'chromed', 'chromy', 'mirror', 'mirrored', 'polished', 'liquid metal', 'mirror finish'], q: ['chrome', 'mirror'], colorMode: 'finish', canon: ['chrome'] },
        { id: 'candy', label: 'candy', syn: ['candy', 'candied', 'kandy', 'candy coat', 'candy paint', 'tinted', 'translucent'], q: ['candy'], colorMode: 'mine', canon: ['candy'] },
        { id: 'pearl', label: 'pearl', syn: ['pearl', 'pearlescent', 'pearly', 'nacre', 'mother of pearl', 'tri coat', 'tricoat'], q: ['pearl'], colorMode: 'mine', canon: ['pearl'] },
        { id: 'flake', label: 'flake / glitter', syn: ['flake', 'flakes', 'flaked', 'metal flake', 'metalflake', 'glitter', 'glittery', 'glitzy', 'sparkle', 'sparkly', 'sparkles', 'sparkling', 'shimmer', 'shimmery', 'shimmering', 'twinkle', 'bling', 'sequin', 'sequins', 'diamond dust'], q: ['flake', 'glitter', 'sparkle', 'sequin'], colorMode: 'mine', canon: ['metal flake', 'micro glitter', 'supernova flake'] },
        { id: 'matte', label: 'matte', syn: ['matte', 'matt', 'flat', 'dull', 'no shine', 'non reflective', 'not shiny', 'not shiny at all', 'no shine at all', 'dead flat', 'much less shiny', 'zero shine'], q: ['matte', 'flat'], colorMode: 'mine', canon: ['matte'] },
        { id: 'satin', label: 'satin', syn: ['satin', 'silky', 'semi matte', 'semi flat', 'eggshell', 'too shiny', 'less shiny', 'too glossy', 'less glossy', 'less shine', 'not so shiny', 'not that shiny', 'a bit less shiny', 'tone down the shine', 'less gloss', 'too much shine', 'too much gloss'], q: ['satin'], colorMode: 'mine', canon: ['satin'] },
        { id: 'gloss', label: 'gloss', syn: ['gloss', 'glossy', 'shiny', 'high gloss', 'showroom', 'wet look', 'wet', 'glass smooth', 'lacquer', 'lacquered', 'shinier', 'glossier', 'more shiny', 'more glossy', 'more shine', 'more gloss', 'a bit shinier', 'a little shinier'], q: ['gloss', 'wet look'], colorMode: 'mine', canon: ['gloss'] },
        { id: 'metallic', label: 'metallic', syn: ['metallic', 'metal', 'metals', 'metalic'], q: ['metallic'], colorMode: 'mine', canon: ['metallic'] },
        { id: 'carbon', label: 'carbon fiber', syn: ['carbon', 'carbon fiber', 'carbon fibre', 'carbonfiber', 'kevlar', 'twill weave', 'weave'], q: ['carbon'], colorMode: 'finish', canon: ['carbon fiber'] },
        { id: 'holo', label: 'holographic', syn: ['holographic', 'holo', 'hologram', 'holograms', 'prism', 'prismatic', 'rainbow', 'oil slick', 'iridescent', 'chameleon', 'color shift', 'color shifting', 'colorshift', 'color flip', 'duochrome', 'shifting', 'color changing'], q: ['holographic', 'holo', 'iridescent', 'chameleon', 'prism'], colorMode: 'finish', canon: ['holographic base'] },
        { id: 'brushed', label: 'brushed metal', syn: ['brushed', 'brushed metal', 'brushed aluminum', 'anodized', 'machined', 'bare metal'], q: ['brushed', 'anodized'], colorMode: 'finish', canon: ['brushed aluminum'] },
        { id: 'rust', label: 'rusty / weathered', syn: ['rust', 'rusty', 'rusted', 'corroded', 'weathered', 'distressed', 'barn find', 'patina', 'patinaed', 'oxidized', 'aged', 'worn', 'beat up', 'battle worn'], q: ['rust', 'patina', 'barn', 'corroded', 'oxidized', 'weathered'], colorMode: 'finish', canon: ['barn find'] },
        { id: 'camo', label: 'camo', syn: ['camo', 'camouflage', 'military', 'tactical'], q: ['camo'], colorMode: 'finish', canon: [] },
        { id: 'flame', label: 'flames', syn: ['flame', 'flames', 'flaming', 'on fire', 'hot rod flames', 'fire', 'blaze', 'fire theme', 'flame job'], q: ['flame', 'fire'], colorMode: 'finish', canon: ['hot rod flames', 'true fire', 'flame job'] },
        { id: 'ice', label: 'ice / frost', syn: ['ice', 'icy', 'frost', 'frosty', 'frozen', 'arctic', 'snow', 'snowy', 'winter'], q: ['ice', 'frost', 'frozen', 'arctic'], colorMode: 'finish', canon: ['frozen'] },
        { id: 'neon', label: 'neon / glow', syn: ['neon', 'glow', 'glowing', 'fluorescent', 'blacklight', 'tron', 'glow in the dark', 'radioactive'], q: ['neon', 'glow'], colorMode: 'finish', canon: ['neon pour', 'neon underglow'] },
        { id: 'marble', label: 'marble / stone', syn: ['marble', 'granite', 'stone', 'concrete', 'terrazzo'], q: ['marble', 'granite', 'stone', 'concrete'], colorMode: 'finish', canon: [] },
        { id: 'leather', label: 'leather / velvet', syn: ['leather', 'velvet', 'suede', 'fabric', 'cloth', 'canvas', 'denim'], q: ['leather', 'velvet', 'suede', 'fabric'], colorMode: 'finish', canon: ['leather grain', 'velvet floc'] },
        { id: 'galaxy', label: 'galaxy / space', syn: ['galaxy', 'cosmic', 'space', 'nebula', 'stars', 'starry', 'constellation', 'astral'], q: ['galaxy', 'cosmic', 'nebula', 'star'], colorMode: 'finish', canon: ['galaxy pour', 'spiral galaxy'] },
        { id: 'lava', label: 'lava / magma', syn: ['lava', 'magma', 'molten', 'volcanic', 'ember', 'embers'], q: ['lava', 'magma', 'molten', 'volcanic', 'ember'], colorMode: 'finish', canon: ['lava pour', 'lava flow'] },
        { id: 'snake', label: 'snakeskin', syn: ['snake', 'snakeskin', 'snake skin', 'reptile', 'scales', 'scaly', 'lizard', 'croc', 'crocodile'], q: ['snake', 'reptile'], colorMode: 'finish', canon: [] },
        { id: 'wood', label: 'wood', syn: ['wood', 'woodgrain', 'wood grain', 'wooden'], q: ['wood'], colorMode: 'finish', canon: [] }
    ];
    // Words that name a whole SHELF of the catalog (a "world"). Resolved against the real section titles.
    var VIBE_SECTIONS = [
        { words: ['cyberpunk', 'cyber', 'sci fi', 'scifi', 'futuristic', 'dystopian', 'blade runner'], section: 'CYBERPUNK' },
        { words: ['dark city', 'gotham', 'noir'], section: 'DARK CITY' },
        { words: ['tactical', 'field', 'hunting'], section: 'TACTICAL' },
        { words: ['groovy', 'psychedelic', 'hippie', 'hippy', '70s', 'seventies', 'tie dye'], section: 'Groovy' },
        { words: ['sock hop', '50s', 'fifties', 'diner', 'rockabilly', 'jukebox'], section: 'Sock Hop' },
        { words: ['disco', 'shag', 'van', 'boogie', 'far out'], section: 'FAR OUT' },
        { words: ['radical', 'arcade', '80s', 'eighties', 'memphis', 'vaporwave', 'retro wave', 'synthwave'], section: 'BAD & RAD' },
        { words: ['lightning', 'electric', 'thunder', 'storm', 'spark'], section: 'LIGHTNING' },
        { words: ['snakes', 'serpent'], section: 'SLITHERIN' },
        { words: ['wrap', 'wraps', 'vinyl'], section: 'WRAP SHOP' },
        { words: ['bug', 'bugs', 'beetle', 'insect', 'insects', 'scarab', 'dragonfly', 'butterfly'], section: 'Iridescent' },
        { words: ['anime', 'manga', 'kawaii', 'neo tokyo'], section: 'ANIME' },
        { words: ['cd', 'cdrom', 'y2k', '90s', 'nineties'], section: 'ALL THAT' },
        { words: ['western', 'cowboy', 'outlaw', 'boot'], section: 'FAR OUT' },
        { words: ['mexico', 'mexican', 'viva', 'talavera', 'dia de muertos'], section: 'VIVA MEXICO' },
        { words: ['japan', 'japanese', 'rising sun', 'samurai'], section: 'RISING SUN' },
        { words: ['union jack', 'british', 'uk', 'england', 'britain'], section: 'UNION JACKED' },
        { words: ['dragon', 'oriental', 'chinese'], section: 'FORBIDDEN DRAGON' },
        { words: ['patriotic', 'usa', 'american', 'america', 'freedom', 'stars and stripes'], section: 'LET FREEDOM RING' },
        { words: ['money', 'cash', 'luxury bank', 'dollar'], section: 'MONEY SHOKK' },
        { words: ['gradient', 'gradients', 'fade', 'ombre', 'faded'], section: 'GRADIENTS' },
        { words: ['grunge', 'punk', 'fun'], section: 'GRUNGE' },
        { words: ['nature', 'jungle', 'forest', 'wilds', 'plants', 'leaf', 'leaves'], section: 'WILDS' },
        { words: ['ancient', 'relic', 'relics', 'egyptian', 'gothic'], section: 'RELICS' },
        { words: ['prizm', 'prism forge'], section: 'PRISM' }
    ];

    var FILLER = ' the a an please pls plz can could would will you your yours i im ill ive id me my mine we lets let us want wanna need needs like to be it its this that these those them there here some any just really very so then now also again too for on in at of and or with without into onto over as by from is are was am have has had do does get got go going let one ones thing things stuff part parts area areas bit bits section sections looking look looks want kinda sorta maybe actually basically ok okay hey hi hello thanks thank ' +
        'all add adding include including theme vibe style kind type sort something whats what how about if would im thats there their they them then than that this now should shall must will be being been gets get alone untouched intact totally quite fairly make makes making made paint painting turn turning change changing set give giving put putting dress wrap wrapping coat coating use using try trying switch convert swap replace redo recolor repaint finish finishes color colors ';

    // ---------------------------------------------------------------- finish index
    var DEAD = { the: 1, of: 1, and: 1, a: 1, an: 1, in: 1, on: 1, to: 1, for: 1, with: 1, base: 1, finish: 1, finishes: 1, paint: 1, coat: 1, look: 1, is: 1, at: 1, by: 1, it: 1, its: 1, from: 1, as: 1, or: 1, no: 1 };
    var SECTION_PRIOR = { 'foundation': 6, 'foundation efx': 5, 'more bases': 4, 'wrap shop': 3, 'astra': 5, 'more specials': 0 };
    function secPrior(title) {
        var t = norm(String(title || '').replace(/[^\x00-\x7f]+/g, ' '));
        if (SECTION_PRIOR[t] != null) return SECTION_PRIOR[t];
        return 2;
    }
    function tokSet(list) { var o = {}; for (var i = 0; i < list.length; i++) o[list[i]] = 1; return o; }

    // cat: { finishes:[{key,id,type,name,desc}], sections:[{title,keys}], top:[key] }
    function buildIndex(cat) {
        var docs = [], df = {}, byKey = {}, secOf = {}, topRank = {}, i, j;
        var top = cat.top || [], secs = cat.sections || [];
        for (i = 0; i < top.length; i++) topRank[top[i]] = i + 1;
        for (i = 0; i < secs.length; i++) for (j = 0; j < secs[i].keys.length; j++) { var k = secs[i].keys[j]; (secOf[k] = secOf[k] || []).push(secs[i].title); }
        var seenName = {};
        var list = (cat.finishes || []).slice();
        // prefer the copy that is on the top shelf / in a better section when one name exists several times
        list.sort(function (a, b) { return bestPrior(b) - bestPrior(a); });
        function bestPrior(f) { var p = topRank[f.key] ? 100 - topRank[f.key] * 0.5 : 0, s = secOf[f.key] || []; var m = 0; for (var q = 0; q < s.length; q++) m = Math.max(m, secPrior(s[q])); return p + m; }
        for (i = 0; i < list.length; i++) {
            var f = list[i], nn = norm(f.name);
            if (!nn || seenName[nn]) continue; seenName[nn] = 1;
            var nameT = toks(f.name).map(stem), descT = toks(f.desc || '').map(stem), idT = String(f.id || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).map(stem);
            var secT = []; (secOf[f.key] || []).forEach(function (t) { secT = secT.concat(toks(String(t).replace(/[^\x00-\x7f]+/g, ' ')).map(stem)); });
            var d = { key: f.key, id: f.id, type: f.type, name: f.name, nameNorm: nn, nameToks: nameT, nameSet: tokSet(nameT), descSet: tokSet(descT), secSet: tokSet(secT), idSet: tokSet(idT),
                top: topRank[f.key] || 0, sec: (secOf[f.key] || [])[0] || '', desc: String(f.desc || '').replace(/\s+/g, ' ').slice(0, 110), prior: bestPrior(f), prefixed: /^[a-z0-9 ]{1,12}:/i.test(f.name) };
            docs.push(d); byKey[f.key] = d;
            var all = {}; for (j = 0; j < nameT.length; j++) all[nameT[j]] = 1; for (var t in d.descSet) all[t] = 1; for (t in d.idSet) all[t] = 1; for (t in d.secSet) all[t] = 1;
            for (t in all) df[t] = (df[t] || 0) + 1;
        }
        var nameTokDf = {};                                   // tokens that appear in NAMES (vocabulary for finish words + typo repair)
        for (i = 0; i < docs.length; i++) for (j = 0; j < docs[i].nameToks.length; j++) nameTokDf[docs[i].nameToks[j]] = (nameTokDf[docs[i].nameToks[j]] || 0) + 1;
        var byName = {}; for (i = 0; i < docs.length; i++) byName[docs[i].nameNorm] = docs[i];
        // stemmed-name lookup for the tagger (exact catalog names typed in a sentence); "Camo: Flecktarn" is also reachable as "flecktarn"
        var byStem = {};
        for (i = 0; i < docs.length; i++) byStem[docs[i].nameToks.join(' ')] = docs[i];
        for (i = 0; i < docs.length; i++) { var bare = String(docs[i].name).replace(/\s*\(.*\)\s*$/, '').replace(/\s+\u2014.*$/, ''); if (bare !== docs[i].name) { var bk = toks(bare).map(stem).join(' '); if (bk && !byStem[bk]) byStem[bk] = docs[i]; } }
        for (i = 0; i < docs.length; i++) { var mm = /^[^:]{1,14}:\s*(.+)$/.exec(docs[i].name); if (mm) { var rest = toks(mm[1]).map(stem).join(' '); if (rest && !byStem[rest]) byStem[rest] = docs[i]; } }
        var maxName = 1; for (i = 0; i < docs.length; i++) if (docs[i].nameToks.length > maxName) maxName = docs[i].nameToks.length;
        return { docs: docs, df: df, N: docs.length, byKey: byKey, byName: byName, byStem: byStem, nameTokDf: nameTokDf, maxName: maxName, sections: secs, top: top, secOf: secOf };
    }
    function idf(ix, t) { var d = ix.df[t] || 0; return Math.log((ix.N + 1) / (d + 1)) + 0.3; }

    // concepts: [[{t:'glitter',w:1},{t:'flake',w:.8}], [{t:'chrome',w:1}]] — every concept must be met; alternatives inside one are OR
    function rank(ix, concepts, opts) {
        opts = opts || {};
        var phrase = opts.phrase || '', out = [], i, c, a;
        var ncon = concepts.length; if (!ncon) return out;
        for (i = 0; i < ix.docs.length; i++) {
            var d = ix.docs[i], s = 0, met = 0, nameHits = 0;
            for (c = 0; c < ncon; c++) {
                var best = 0, inName = false;
                for (a = 0; a < concepts[c].length; a++) {
                    var alt = concepts[c][a], t = alt.t, w = idf(ix, t) * alt.w, v = 0;
                    if (d.nameSet[t]) { v = 3 * w; if (alt.w >= 0.99) inName = true; else if (alt.w >= 0.7) inName = inName || false; }
                    else if (d.idSet[t]) v = 1.3 * w;
                    else if (d.secSet[t]) v = 1.5 * w;
                    else if (d.descSet[t]) v = 0.55 * w;
                    if (v > best) best = v;
                    if (d.nameSet[t]) nameHits++;
                }
                if (best > 0) { met++; s += best * (c === ncon - 1 ? 1.15 : 1); }
            }
            if (!met) continue;
            if (met < ncon) s *= Math.pow(met / ncon, 2.2);
            if (phrase) {
                if (d.nameNorm === phrase) s += 60;
                else if (d.nameNorm.indexOf(phrase + ' ') === 0) s += 14;
                else if (d.nameNorm.indexOf(phrase) !== -1) s += 9;
            }
            var extra = d.nameToks.length - ncon; if (extra > 1) s -= 0.5 * (extra - 1);
            if (met === ncon && nameHits >= ncon && d.nameToks.length <= ncon + 1) s += 5;
            if (nameHits > 0) { s += d.top ? 7 + (d.top <= 8 ? 3 : 0) : 0; s += d.prior * 0.35; }     // priors only lift finishes that NAME the thing
            else s *= 0.55;                                                                             // a description that merely mentions it
            if (d.prefixed) s -= 1.2;
            if (opts.boost && opts.boost[d.nameNorm]) s += opts.boost[d.nameNorm];
            out.push({ doc: d, score: s });
        }
        out.sort(function (x, y) { return y.score - x.score; });
        return out;
    }

    // ================================================================ WORLD LEXICON
    var GENERIC_LAYER_TOKENS = tokSet(['color', 'layer', 'area', 'art', 'copy', 'group', 'base', 'new', 'mask', 'the', 'of', 'and', 'a', 'my', 'car', 'main', 'default', 'template', 'guide', 'guides']);
    var LAYER_ALIAS = { numeral: 'number', num: 'number', nr: 'number', sponsors: 'sponsor', sticker: 'decal', decals: 'decal', logos: 'logo', stripes: 'stripe', lettering: 'text', letters: 'text', letter: 'text', windshield: 'banner', windscreen: 'banner', pit: 'pitbox' };
    function canonTok(t) { t = stem(t); return LAYER_ALIAS[t] || t; }
    var KIND_PHRASES = {
        dark: ['dark areas', 'dark area', 'dark parts', 'dark part', 'black areas', 'black parts', 'shadows', 'shadow areas', 'dark bits', 'dark stuff'],
        white: ['white areas', 'white area', 'white parts', 'white part', 'white logos', 'white and logos', 'white bits', 'white lettering', 'white text'],
        remaining: ['everything else', 'the rest', 'rest of it', 'rest of the car', 'the remainder', 'remaining', 'leftover', 'left over', 'leftovers', 'the background', 'background', 'other stuff', 'everything left', 'the other parts', 'other parts', 'the other stuff', 'the leftovers', 'rest']
    };
    var WHOLE_PHRASES = ['whole car', 'the whole car', 'entire car', 'the entire car', 'whole thing', 'the whole thing', 'entire thing', 'all of it', 'all over', 'everything', 'the car', 'my car', 'the whole design', 'the whole paint job', 'whole paint job', 'paint job', 'the paint job', 'my paint job', 'overall', 'car'];
    var COLORS_GROUP_PHRASES = ['all colors', 'all the colors', 'every color', 'each color', 'all my colors', 'all the color parts', 'every color part', 'all color parts', 'the colors', 'all the paint', 'all the body colors', 'body colors'];
    var MAIN_PHRASES = ['main color', 'the main color', 'main paint', 'the main paint', 'base color', 'the base color', 'main body', 'the body', 'body', 'bodywork', 'the bodywork', 'body color', 'the body color', 'body paint', 'biggest color', 'the biggest color', 'largest color', 'the largest color', 'dominant color', 'primary color', 'the primary color', 'base coat', 'the base coat', 'car paint', 'the paint', 'my paint'];
    var LOCATION_WORDS = tokSet(['hood', 'roof', 'bumper', 'door', 'doors', 'trunk', 'spoiler', 'wing', 'sides', 'side', 'fender', 'fenders', 'quarter', 'splitter', 'mirror', 'mirrors', 'nose', 'tail', 'rear', 'front', 'back', 'wheel', 'wheels', 'rim', 'rims', 'window', 'windows', 'grille', 'skirt', 'skirts', 'diffuser', 'panel', 'panels', 'top', 'bottom', 'left', 'right']);

    function partWordOf(p) {
        if (!p) return '';
        if (p.label && p.kind === 'color') {
            var full = String(p.label).replace(/\s*·\s*your pick$/i, '').replace(/\s\d+$/, '').replace(/\s*→.*$/, '').replace(/\sfade$/i, '').trim().toLowerCase();
            if (WORD_TO_BASE[full]) return WORD_TO_BASE[full];
            var w = full.split(' '), last = w[w.length - 1];
            return WORD_TO_BASE[last] || last;
        }
        return p.hex ? (colorWord(p.hex) || '') : '';
    }
    function isBodyColor(p) { return p && p.kind === 'color' && !p.tone && !p.pick; }
    function partDisplay(p) { return p ? (p.whole ? 'the whole car' : (p.label || p.name)) : ''; }

    // phrase -> [{target, w, group}] ; plus per-colour-word part groups
    function buildLexicon(world) {
        var lex = { phrases: {}, maxN: 1, colorParts: {}, labels: {}, layers: [], sortedParts: [] };
        var parts = world.parts || [], layers = world.layers || [];
        function add(phrase, entry) {
            var p = norm(phrase); if (!p) return;
            var k = p.split(' ').map(stem).join(' ');
            (lex.phrases[k] = lex.phrases[k] || []).push(entry);
            var n = k.split(' ').length; if (n > lex.maxN) lex.maxN = n;
        }
        parts.forEach(function (p) {
            if (p.kind === 'layer' || p.layerId != null) return;              // layers handled below (they may not be parts yet)
            var tgt = { kind: 'part', idx: p.idx, label: partDisplay(p) };
            if (p.kind === 'remaining') { KIND_PHRASES.remaining.forEach(function (ph) { add(ph, { target: tgt, w: 3 }); }); return; }
            if (p.tone === 'dark' || p.kind === 'dark') KIND_PHRASES.dark.forEach(function (ph) { add(ph, { target: tgt, w: 3 }); });
            if (p.tone === 'white' || p.kind === 'white') KIND_PHRASES.white.forEach(function (ph) { add(ph, { target: tgt, w: 3 }); });
            var lab = norm(p.label || p.name);
            if (lab) {
                if (/\d/.test(lab)) add(lab, { target: tgt, w: 4 });             // "cyan 2": one specific part
                else { lex.labels[lab] = lex.labels[lab] || []; lex.labels[lab].push(tgt); }
            }
            var wd = partWordOf(p);
            if (wd && p.hex) { (lex.colorParts[wd] = lex.colorParts[wd] || []).push(tgt); }
        });
        // ---- layers: full name (w3), unique distinctive token (w2), shared token (w1, ambiguous)
        var seenLayer = {}, list = [];
        layers.forEach(function (l) { if (seenLayer[l.id] == null) { seenLayer[l.id] = 1; list.push({ id: l.id, name: l.name }); } });
        parts.forEach(function (p) { if ((p.kind === 'layer' || p.layerId != null) && p.layerId != null && seenLayer[p.layerId] == null) { seenLayer[p.layerId] = 1; list.push({ id: p.layerId, name: p.name || p.label }); } });
        var tokCount = {};
        list.forEach(function (l) { l._toks = uniq(toks(l.name).map(canonTok).filter(function (t) { return !GENERIC_LAYER_TOKENS[t] && t.length > 1; })); l._toks.forEach(function (t) { tokCount[t] = (tokCount[t] || 0) + 1; }); });
        list.forEach(function (l) {
            var tgt = { kind: 'layer', layerId: l.id, name: l.name };
            add(l.name, { target: tgt, w: 3, layer: true });
            l._toks.forEach(function (t) { add(t, { target: tgt, w: tokCount[t] === 1 ? 2 : 1, layer: true, ambiguous: tokCount[t] > 1 }); });
        });
        lex.layers = list;
        Object.keys(LAYER_ALIAS).forEach(function (a) { var c = LAYER_ALIAS[a]; var k = stem(a); if (lex.phrases[c] && !lex.phrases[k]) lex.phrases[k] = lex.phrases[c]; });
        lex.sortedParts = parts.filter(isBodyColor).slice().sort(function (a, b) { return (b.share || 0) - (a.share || 0); });
        if (!lex.sortedParts.length) lex.sortedParts = parts.filter(function (p) { return p.kind !== 'layer' && p.layerId == null && p.kind !== 'remaining' && !p.pick; }).slice().sort(function (a, b) { return (b.share || 0) - (a.share || 0); });   // a flat white/black car has only tone parts
        return lex;
    }

    // ================================================================ VERB / HOW / ADJUST PHRASES
    var VERB_PHRASES = [
        ['undo', ['undo', 'undo that', 'undo it', 'take that back', 'take it back', 'go back', 'step back', 'revert', 'revert that', 'cancel that', 'oops', 'never mind', 'nevermind', 'scratch that', 'that was wrong', 'i hate it', 'i dont like it', 'i dont like that', 'thats worse', 'worse', 'nope', 'no']],
        ['save', ['save', 'save it', 'save this', 'save my paint', 'save the paint', 'save my car', 'save the car', 'save to iracing', 'export', 'export it', 'export my paint', 'send it to iracing', 'put it in iracing', 'im done', 'i am done', 'all done', 'finished', 'im finished']],
        ['redo', ['redo', 'redo that', 'put it back', 'bring it back', 'bring that back']],
        ['startover', ['start over', 'start again', 'start fresh', 'from scratch', 'reset everything', 'wipe everything', 'clear everything', 'begin again', 'reset all', 'reset it all']],
        ['another', ['another', 'another one', 'try another', 'try another one', 'something else', 'something different', 'different one', 'a different one', 'different', 'next one', 'next', 'reroll', 're roll', 'shuffle', 'switch it up', 'mix it up', 'again', 'once more', 'one more', 'other one', 'the other one', 'not that one', 'not that', 'not this one']],
        ['surprise', ['something cool', 'something nice', 'something good', 'something awesome', 'something sick', 'something epic', 'something amazing', 'something great', 'something pretty', 'something beautiful', 'make it cool', 'make it look cool', 'make it awesome', 'make it look awesome', 'make it look good', 'make it look great', 'make it look nice', 'make it pretty', 'make it beautiful', 'make it look beautiful', 'make it better', 'make it look better', 'improve it', 'improve the design', 'make it sick', 'make it epic', 'cool design', 'cool paint job', 'awesome design', 'make it look sick', 'make it look epic', 'surprise me', 'surprise', 'impress me', 'wow me', 'your choice', 'you choose', 'you pick', 'anything', 'dealers choice', 'go wild', 'go crazy', 'pick for me', 'choose for me', 'random', 'randomize', 'randomise', 'i dont care', 'i dont know', 'no idea', 'dunno', 'inspire me']],
        ['help', ['help', 'help me', 'what can you do', 'what can i say', 'what can i ask', 'examples', 'example', 'how does this work', 'how do i use this', 'commands', 'ideas', 'i need ideas', 'give me ideas', 'suggestions', 'options']]
    ];
    var HOW_PHRASES = [
        ['shine', ['just the shine', 'only the shine', 'shine only', 'just shine', 'only shine', 'keep my paint', 'keep the paint', 'keep my paint job', 'leave my paint', 'just the finish', 'only the finish', 'just the spec', 'only the spec', 'just the shininess', 'keep paint as is', 'without changing the colors', 'without changing colors', 'without changing my colors', 'dont change the colors', 'dont change my colors', 'keep all my colors', 'keep all colors', 'materials only', 'just the material', 'just the materials', 'only the materials']],
        ['blend', ['blend it', 'blend', 'blended', 'mix it', 'mixed', 'mix', 'half way', 'halfway', 'half', 'a bit', 'a little', 'a touch', 'a hint', 'a hint of', 'hint of', 'touch of', 'slightly', 'slight', 'subtle', 'subtly', 'lightly', 'light touch', 'faint', 'faintly', 'partly', 'partially', 'gentle', 'gently', 'soft touch', 'sprinkle of', 'dusting of', 'medium', 'moderately', 'mostly', 'mainly', 'strongly', 'strong', 'heavy', 'heavily', 'thick']],
        ['all', ['all the way', 'fully', 'full on', 'completely', 'totally', 'solid', 'full strength', 'entirely', 'full blast', 'max', 'maximum', 'at full strength', 'over the top', 'full']]
    ];
    var AMOUNT_WORDS = { 'a bit': 0.3, 'a little': 0.3, 'a touch': 0.3, 'a hint': 0.25, 'a hint of': 0.25, 'hint of': 0.25, 'touch of': 0.3, slightly: 0.3, slight: 0.3, subtle: 0.3, subtly: 0.3, lightly: 0.3, 'light touch': 0.3, faint: 0.25, faintly: 0.25, gentle: 0.3, gently: 0.3, 'soft touch': 0.3, 'sprinkle of': 0.25, 'dusting of': 0.25, partly: 0.5, partially: 0.5, half: 0.5, 'half way': 0.5, halfway: 0.5, medium: 0.5, moderately: 0.5, mostly: 0.75, mainly: 0.75, strongly: 0.85, strong: 0.85, heavy: 0.85, heavily: 0.85, thick: 0.85, 'blend it': 0.5, blend: 0.5, blended: 0.5, 'mix it': 0.5, mixed: 0.5, mix: 0.5 };
    // adjust phrases -> {op, dir}. op: size | blend | hue | sat | bri | intensity ; dir +1/-1
    var ADJ_PHRASES = [
        ['size', 1, ['bigger', 'larger', 'coarser', 'chunkier', 'bigger pattern', 'larger pattern', 'bigger flakes', 'larger flakes', 'bigger flake', 'larger flake', 'big flakes', 'chunky', 'huge', 'enlarge', 'zoom in', 'scale up']],
        ['size', -1, ['smaller', 'finer', 'tighter', 'tiny', 'micro', 'smaller pattern', 'finer pattern', 'smaller flakes', 'finer flakes', 'smaller flake', 'finer flake', 'fine flakes', 'zoom out', 'shrink', 'scale down', 'more detailed', 'busier']],
        ['bri', 1, ['brighter', 'lighter', 'lighten', 'brighten', 'light up', 'less dark', 'paler', 'more bright', 'lighter shade', 'light', 'bright']],
        ['bri', -1, ['darker', 'deeper', 'darken', 'dim', 'dimmer', 'richer', 'moodier', 'less bright', 'not so bright', 'too bright', 'darker shade', 'dark']],
        ['sat', 1, ['more vivid', 'vivid', 'more saturated', 'saturated', 'punchier', 'punchy', 'more color', 'colorful', 'more colorful', 'pop', 'make it pop', 'pop more', 'more pop', 'louder', 'bolder', 'vibrant', 'more vibrant', 'more intense color']],
        ['sat', -1, ['muted', 'more muted', 'desaturated', 'less saturated', 'less color', 'calmer', 'toned down', 'tone it down', 'quieter', 'softer', 'less vivid']],
        ['hue', 1, ['shift hue', 'shift the hue', 'change the hue', 'rotate hue', 'warmer', 'more warm', 'warm it up', 'shift the color', 'shift color', 'hue shift']],
        ['hue', -1, ['cooler', 'more cool', 'cool it down', 'cool it off']],
        ['blend', 1, ['more blend', 'more of the finish', 'stronger finish', 'more finish', 'more of it', 'stronger', 'more effect', 'increase blend', 'crank it', 'crank it up', 'turn it up', 'turn up', 'amp it up', 'more of that']],
        ['blend', -1, ['less blend', 'less of the finish', 'weaker finish', 'less finish', 'less of it', 'weaker', 'less effect', 'reduce blend', 'turn it down', 'tone down', 'back off', 'dial it back', 'ease off', 'not so strong', 'less of that']],
        ['intensity', 1, ['more', 'a bit more', 'a little more', 'even more', 'much more', 'way more', 'lots more', 'bit more', 'little more']],
        ['intensity', -1, ['less', 'a bit less', 'a little less', 'even less', 'much less', 'way less', 'lots less', 'bit less', 'little less', 'not as much', 'not so much', 'too much', 'too strong', 'too intense', 'too loud', 'too busy']]
    ];

    function buildPhraseMap(defs) {
        var map = {}, maxN = 1;
        defs.forEach(function (d) {
            d.phrases.forEach(function (ph) {
                var k = norm(ph).split(' ').map(stem).join(' '); if (!k) return;
                map[k] = d.payload; var n = k.split(' ').length; if (n > maxN) maxN = n;
            });
        });
        return { map: map, maxN: maxN };
    }
    var VERB_MAP = buildPhraseMap(VERB_PHRASES.map(function (v) { return { payload: { type: 'verb', kind: v[0] }, phrases: v[1] }; }));
    var HOW_MAP = buildPhraseMap(HOW_PHRASES.map(function (h) { return { payload: { type: 'how', kind: h[0] }, phrases: h[1] }; }));
    var ADJ_MAP = buildPhraseMap(ADJ_PHRASES.map(function (a) { return { payload: { type: 'adj', op: a[0], dir: a[1] }, phrases: a[2] }; }));
    var FAMILY_MAP = buildPhraseMap(FAMILIES.map(function (f) { return { payload: { type: 'fam', id: f.id }, phrases: f.syn }; }));
    var VIBE_MAP = buildPhraseMap(VIBE_SECTIONS.map(function (v) { return { payload: { type: 'vibe', section: v.section }, phrases: v.words }; }));
    var WHOLE_MAP = buildPhraseMap([{ payload: { type: 'whole' }, phrases: WHOLE_PHRASES }]);
    var GROUP_MAP = buildPhraseMap([{ payload: { type: 'colorsgroup' }, phrases: COLORS_GROUP_PHRASES }]);
    var LAYERS_PHRASES = ['all layers', 'all the layers', 'all my layers', 'every layer', 'each layer', 'every single layer', 'the layers', 'my layers', 'all of the layers', 'every one of the layers'];
    var LAYERS_MAP = buildPhraseMap([{ payload: { type: 'layersgroup' }, phrases: LAYERS_PHRASES }]);
    // the LAYERS panel lists the base paint first and the art stacked above it, so first/bottom = first row, last/top = last row
    var ORDINALS = { first: 0, bottom: 0, second: 1, third: 2, fourth: 3, fifth: 4, sixth: 5, last: -1, top: -1, topmost: -1, final: -1 };
    var MAIN_MAP = buildPhraseMap([{ payload: { type: 'main' }, phrases: MAIN_PHRASES }]);
    function familyById(id) { for (var i = 0; i < FAMILIES.length; i++) if (FAMILIES[i].id === id) return FAMILIES[i]; return null; }

    // ================================================================ RECIPES ("vibes")
    // Role-based looks. Roles: main (largest colour part), second (other body colours), dark, white, rest, layer:<word>.
    // Each slot: {fam|key, color:'#hex'|'keep'|'finish'}. A recipe never touches a role the car does not have.
    var RECIPES = [
        { id: 'stealth', label: 'Stealth', words: ['stealth', 'stealthy', 'blacked out', 'blackout', 'murdered out', 'murder out', 'all black', 'ninja', 'sinister', 'menacing', 'covert', 'batmobile'],
          blurb: 'Everything dark and quiet — matte black bodywork, satin accents.',
          roles: { main: { fam: 'matte', color: '#111111' }, second: { fam: 'matte', color: '#1a1b1e' }, dark: { fam: 'satin', color: 'keep' }, white: { fam: 'satin', color: '#3a3d42' }, rest: { fam: 'matte', color: 'keep' }, 'layer:number': { fam: 'satin', color: '#3a3d42' } } },
        { id: 'expensive', label: 'Luxury', words: ['expensive', 'luxury', 'luxurious', 'classy', 'elegant', 'premium', 'high end', 'upscale', 'rich', 'fancy', 'posh', 'refined', 'sophisticated', 'boutique', 'bespoke', 'bentley', 'rolls royce', 'sleek'],
          blurb: 'Deeper, richer colours in pearl, piano-black accents, champagne whites, gold numbers.',
          roles: { main: { fam: 'pearl', color: 'keep', adj: { dSat: 6, dBri: -24 } }, second: { fam: 'pearl', color: 'keep', adj: { dSat: 6, dBri: -24 } }, dark: { key: 'piano_black', color: 'keep' }, white: { fam: 'pearl', color: '#f3ecd0' }, rest: { fam: 'gloss', color: 'keep' }, 'layer:number': { fam: 'metallic', color: '#c9a227' } } },
        { id: 'showcar', label: 'Show car', words: ['show car', 'showcar', 'show stopper', 'showstopper', 'head turner', 'turn heads', 'trophy', 'concours', 'cruise night', 'car show', 'wow'],
          blurb: 'Chrome on the main colour, candy and pearl on the rest.', look: 'show' },
        { id: 'candyshop', label: 'Candy shop', words: ['candy shop', 'sweet', 'sweets', 'lollipop', 'juicy', 'wet and glossy', 'candy land', 'candyland'], blurb: 'Deep candy on every colour — wet, glossy, loud.', look: 'candy' },
        { id: 'oem', label: 'Factory', words: ['factory', 'oem', 'stock', 'dealership', 'dealer', 'clean', 'simple', 'plain', 'minimal', 'minimalist', 'understated', 'normal', 'realistic', 'believable', 'daily driver', 'sensible'], blurb: 'Factory metallic and clean gloss — believable.', look: 'oem' },
        { id: 'matteandchrome', label: 'Matte & chrome', words: ['matte and chrome', 'modern', 'contrast', 'modern wrap', 'contemporary'], blurb: 'Matte everywhere, chrome on the white and logos.', look: 'matte' },
        { id: 'raceday', label: 'Race day', words: ['race day', 'raceday', 'racecar', 'race car', 'racing', 'race ready', 'track day', 'competition', 'motorsport', 'livery', 'gulf', 'martini'],
          blurb: 'Vivid gloss body, chrome-white accents, satin darks — a crisp racing livery.',
          roles: { main: { fam: 'gloss', color: 'keep', adj: { dSat: 14 } }, second: { fam: 'gloss', color: 'keep', adj: { dSat: 14 } }, dark: { fam: 'satin', color: 'keep' }, white: { fam: 'chrome', color: 'finish' }, rest: { fam: 'gloss', color: 'keep' }, 'layer:number': { fam: 'gloss', color: '#f2f2f2' } } },
        { id: 'neonnight', label: 'Neon night', words: ['night', 'night race', 'nighttime', 'after dark', 'midnight', 'underglow', 'tokyo drift', 'street racer', 'street race', 'nightclub', 'club'],
          blurb: 'Near-black bodywork lit by hot neon accents.',
          roles: { main: { fam: 'matte', color: '#0b0d14' }, second: { fam: 'gloss', colors: ['#39ff14', '#ff2fb0', '#1fe0ff', '#ffe600'] }, dark: { fam: 'gloss', color: 'keep' }, white: { fam: 'gloss', color: '#1fe0ff' }, rest: { fam: 'satin', color: 'keep' }, 'layer:number': { fam: 'gloss', color: '#ffe600' } } },
        { id: 'retro', label: 'Retro', words: ['retro', 'vintage', 'old school', 'oldschool', 'classic', 'nostalgic', 'throwback', 'antique', 'heritage', 'muscle car', 'sixties', '60s', 'timeless'],
          blurb: 'Faded, soft satin colours and warm off-whites — period-correct.',
          roles: { main: { fam: 'satin', color: 'keep', adj: { dSat: -38, dBri: 4 } }, second: { fam: 'satin', color: 'keep', adj: { dSat: -38, dBri: 4 } }, dark: { fam: 'matte', color: 'keep' }, white: { fam: 'satin', color: '#ece8dd' }, rest: { fam: 'satin', color: 'keep' }, 'layer:number': { fam: 'satin', color: '#ece8dd' } } },
        { id: 'wild', label: 'Wild', words: ['wild', 'crazy', 'insane', 'flashy', 'over the top', 'extra', 'psychedelic', 'trippy', 'rave', 'circus', 'party', 'festival', 'playful', 'bonkers'],
          blurb: 'Hot-pink candy body with a different loud colour on every accent — maximum colour.',
          roles: { main: { fam: 'candy', color: '#ff2d95' }, second: { fam: 'candy', colors: ['#00d3f3', '#ffe600', '#7a2ff0', '#39ff14', '#ff7a18'] }, dark: { fam: 'chrome', color: 'finish' }, white: { fam: 'gloss', color: '#ffffff' }, rest: { fam: 'pearl', color: '#ff9ad0' }, 'layer:number': { fam: 'metallic', color: '#ffe600' } } },
        { id: 'raw', label: 'Raw metal', words: ['raw', 'industrial', 'raw metal', 'bare metal', 'unpainted', 'machine', 'mechanical', 'workshop', 'rat rod', 'ratrod', 'gritty'],
          blurb: 'Gunmetal and steel with copper accents and matte blacks.',
          roles: { main: { fam: 'metallic', color: '#5a6068' }, second: { fam: 'metallic', colors: ['#b87333', '#8a8d92', '#43484f'] }, dark: { fam: 'matte', color: 'keep' }, white: { fam: 'satin', color: '#c9ccd1' }, rest: { fam: 'matte', color: 'keep' }, 'layer:number': { fam: 'metallic', color: '#b87333' } } },
        { id: 'icy', label: 'Ice', words: ['icy', 'frozen look', 'polar', 'glacier', 'chilly', 'freezing'],
          blurb: 'Pearl in pale ice blues, navy darks, frosted white.',
          roles: { main: { fam: 'pearl', color: '#bfe3ff' }, second: { fam: 'pearl', colors: ['#8fb8e8', '#dff3ff', '#5f8fd0'] }, dark: { fam: 'satin', color: '#16233d' }, white: { fam: 'pearl', color: '#f6fbff' }, rest: { fam: 'gloss', color: '#dff3ff' }, 'layer:number': { fam: 'chrome', color: 'finish' } } },
        { id: 'fire', label: 'Fire', words: ['fiery', 'blazing', 'inferno', 'burning', 'scorching', 'hellfire', 'demon', 'devil'],
          blurb: 'Orange candy body, red and amber accents, soot-black darks.',
          roles: { main: { fam: 'candy', color: '#ff5a00' }, second: { fam: 'candy', colors: ['#e02010', '#ffb000', '#ff3d00'] }, dark: { fam: 'gloss', color: '#140806' }, white: { fam: 'candy', color: '#ffd200' }, rest: { fam: 'gloss', color: '#b01800' }, 'layer:number': { fam: 'metallic', color: '#ffd200' } } }
    ];
    var RECIPE_MAP = buildPhraseMap(RECIPES.map(function (r) { return { payload: { type: 'recipe', id: r.id }, phrases: r.words }; }));
    function recipeById(id) { for (var i = 0; i < RECIPES.length; i++) if (RECIPES[i].id === id) return RECIPES[i]; return null; }

    // ================================================================ FINISH RESOLUTION
    function famConcept(f) {
        var c = [];
        for (var i = 0; i < f.q.length; i++) c.push({ t: stem(f.q[i]), w: i === 0 ? 1 : 0.8 });
        return c;
    }
    function boostFor(fams) {
        var b = {};
        fams.forEach(function (f) { (f.canon || []).forEach(function (n, i) { b[norm(n)] = Math.max(b[norm(n)] || 0, 30 - i * 4); }); });
        return b;
    }
    function altKeys(ranked, skipKey, n) {
        var out = [];
        for (var i = 0; i < ranked.length && out.length < n; i++) if (ranked[i].doc.key !== skipKey) out.push(ranked[i].doc.key);
        return out;
    }
    // Resolve a finish from what the command said. said = {names:[doc], fams:[family], fws:[word], vibes:[section]}
    function resolveFinish(ix, said) {
        if (!ix) return null;
        var i, ranked, concepts = [], fams = said.fams || [];
        if (said.names && said.names.length) {
            var d = said.names[said.names.length - 1];
            ranked = rank(ix, d.nameToks.map(function (t) { return [{ t: t, w: 1 }]; }), { phrase: d.nameNorm });
            return { key: d.key, name: d.name, via: 'name', family: null, alts: altKeys(ranked, d.key, 10) };
        }
        var vibeKeys = null;
        if (said.vibes && said.vibes.length) {
            var title = said.vibes[said.vibes.length - 1];
            for (i = 0; i < ix.sections.length; i++) if (ix.sections[i].title.toLowerCase().indexOf(title.toLowerCase()) !== -1) { vibeKeys = ix.sections[i].keys; break; }
        }
        fams.forEach(function (f) { concepts.push(famConcept(f)); });
        (said.fws || []).forEach(function (w) { concepts.push([{ t: stem(w), w: 1 }]); });
        if (!concepts.length && !vibeKeys) return null;
        var phrase = (fams.length === 0 && said.fws && said.fws.length) ? said.fws.join(' ') : '';
        if (fams.length === 1 && !(said.fws && said.fws.length)) phrase = fams[0].q[0];
        ranked = concepts.length ? rank(ix, concepts, { phrase: norm(phrase), boost: boostFor(fams) }) : [];
        if (vibeKeys) {
            var inSec = {}; vibeKeys.forEach(function (k) { inSec[k] = 1; });
            if (ranked.length) { var pri = ranked.filter(function (r) { return inSec[r.doc.key]; }); if (pri.length) ranked = pri.concat(ranked.filter(function (r) { return !inSec[r.doc.key]; })); }
            else ranked = vibeKeys.map(function (k) { return ix.byKey[k]; }).filter(Boolean).map(function (dd, n) { return { doc: dd, score: 100 - n }; });
        }
        if (!ranked.length) return { key: null, name: '', via: 'none', family: fams.length ? fams[fams.length - 1].id : null, alts: [], missing: (said.fws || []).concat(fams.map(function (f) { return f.label; })).join(' ') };
        var top = ranked[0].doc;
        return { key: top.key, name: top.name, via: fams.length && !vibeKeys ? 'family' : (vibeKeys ? 'vibe' : 'word'), family: fams.length ? fams[fams.length - 1].id : null, alts: altKeys(ranked, top.key, 10) };
    }
    function resolveFamilyKey(ix, famId) {
        var f = familyById(famId); if (!f || !ix) return null;
        var r = rank(ix, [famConcept(f)], { phrase: norm(f.q[0]), boost: boostFor([f]) });
        return r.length ? r[0].doc.key : null;
    }

    // ================================================================ TAGGER
    var COMMON_WORDS = tokSet(('thing things something anything everything nothing cool warm cold hot bright dark light deep pale soft hard last first next previous session design theme vibe style kind sort type way lot lots little bit good bad best better worse nice pretty great awesome amazing sick epic dope fresh clean simple plain normal real true new old big small huge tiny long short high low fast slow more most less least much many very quite really just only even still also always never sometimes about around back front side top bottom left right up down out off over under again ever wanted looks looked looking want wants ' +
        'true false hello please thanks color colors shade shades tone tones tint mode mood feel feeling energy power speed race racing car cars paint painted').split(' '));
    var SEP_WORDS = tokSet(['then', 'also', 'plus', 'afterwards', 'later', 'next,']);
    var EXCEPT_PHRASES = ['except for', 'except', 'excluding', 'besides', 'apart from', 'other than', 'but not', 'but leave', 'but keep', 'leave', 'keep', 'skip', 'ignore', 'not including', 'sparing', 'aside from', 'without touching', 'dont touch', 'do not touch'];
    var EXCEPT_MAP = buildPhraseMap([{ payload: { type: 'except' }, phrases: EXCEPT_PHRASES }]);
    var KEEPCOLOR_MAP = buildPhraseMap([{ payload: { type: 'colorkeep' }, phrases: ['its own color', 'own color', 'my own color', 'own colors', 'the same color', 'same color', 'same colors', 'original color', 'original colors', 'current color', 'current colors', 'existing color', 'existing colors', 'my colors', 'my color', 'keep the color', 'keep the colors', 'keep its color', 'keep their color', 'keep color', 'keep colors', 'the color it has', 'the same colors', 'as is color', 'unchanged color', 'no color change', 'dont change the color', 'leave the color', 'leave the colors'] }]);
    var SRC_MAP = buildPhraseMap([{ payload: { type: 'srcmark' }, phrases: ['same as', 'same color as', 'same colors as', 'match', 'matching', 'matches', 'copy the color of', 'the color of', 'color of', 'color from', 'the color from', 'colors from', 'just like', 'look like the', 'looks like the', 'looking like the', 'same as the'] }]);
    var PARTNOUN = tokSet(['part', 'parts', 'area', 'areas', 'bit', 'bits', 'one', 'ones', 'stuff', 'section', 'sections', 'spots', 'spot', 'panels', 'paint', 'color', 'colors']);
    var DET = tokSet(['the', 'my', 'all', 'every', 'each', 'that', 'this', 'those', 'these', 'both', 'our']);
    var PREP = tokSet(['on', 'for', 'to', 'onto', 'over', 'across', 'in', 'of', 'at']);

    function matchAt(map, S, i) {                       // longest phrase from a phrase map starting at token i
        var maxN = Math.min(map.maxN, S.length - i);
        for (var n = maxN; n >= 1; n--) {
            var k = S.slice(i, i + n).join(' ');
            if (map.map[k]) return { payload: map.map[k], len: n, key: k };
        }
        return null;
    }
    function colorAt(T, i) {                            // colour phrase (table or modifier+base), hex literal
        if (/^#[0-9a-f]{6}$/.test(T[i])) return { hex: T[i], word: colorWord(T[i]), name: T[i], len: 1, custom: true };
        var maxN = Math.min(COLOR_MAXLEN, T.length - i);
        for (var n = maxN; n >= 1; n--) {
            var ph = T.slice(i, i + n).join(' '), r = lookupColor(ph);
            if (r) return { hex: r.hex, word: r.word, name: ph, len: n, mod: r.mod || null };
            if (n === 1 && T[i].length > 3 && /s$/.test(T[i])) { r = lookupColor(T[i].slice(0, -1)); if (r) return { hex: r.hex, word: r.word, name: T[i].slice(0, -1), len: 1 }; }
        }
        return null;
    }
    // vocabulary for typo repair
    function buildFuzzyVocab(world, lex) {
        var v = {}, add = function (w, kind) { if (w && w.length >= 4 && !v[w]) v[w] = kind; };
        Object.keys(COLORS).forEach(function (n) { if (n.indexOf(' ') === -1) add(n, 'color'); });
        [FAMILY_MAP, HOW_MAP, ADJ_MAP, VERB_MAP, WHOLE_MAP].forEach(function (m) { Object.keys(m.map).forEach(function (k) { if (k.indexOf(' ') === -1) add(k, 'word'); }); });
        FAMILIES.forEach(function (f) { var k = stem(norm(f.syn[0])); if (k.indexOf(' ') === -1 && k.length >= 4) v[k] = 'core'; });   // the family's own name beats its variants (chrom -> chrome, not chromy)
        Object.keys(lex.phrases).forEach(function (k) { if (k.indexOf(' ') === -1) add(k, 'part'); });
        Object.keys(lex.labels).forEach(function (k) { if (k.indexOf(' ') === -1) add(k, 'part'); });
        if (world.index) { var nd = world.index.nameTokDf; Object.keys(nd).forEach(function (t) { if (t.length >= 5 && nd[t] >= 2) add(t, 'fin'); }); }
        return v;
    }
    var VOCAB_PRI = { word: 3, color: 2, part: 4, fin: 1, core: 3.6 };
    function repairWord(w, vocab) {
        if (w.length < 4 || /\d/.test(w)) return null;
        var max = w.length >= 8 ? 2 : 1, best = null, bestD = 99, bestScore = -99;
        for (var k in vocab) {
            if (Math.abs(k.length - w.length) > max) continue;
            if (vocab[k] === 'fin' && w.length < 7) continue;                  // gibberish like "flarn" must not become the finish "Flare"
            if (w.length <= 5 && k.charAt(0) !== w.charAt(0)) continue;         // short words: first letter must survive
            var d = editDistance(w, k, max);
            if (d > max) continue;
            var score = -d * 10 - Math.abs(k.length - w.length) * 0.3 + (VOCAB_PRI[vocab[k]] || 0) * 0.8 + (k.charAt(0) === w.charAt(0) ? 0.5 : 0) + (k.indexOf(w) === 0 ? 1.6 : 0) - k.length * 0.01;   // "chrom" -> chrome (a word typed short)
            if (score > bestScore + 1e-9) { bestScore = score; best = k; bestD = d; }
            else if (Math.abs(score - bestScore) < 1e-9 && k !== best) best = null, bestScore = score - 0.0;   // genuine tie
        }
        return best;
    }
    function repairAny(w, vocab) { return repairWord(w, vocab) || repairWord(stem(w), vocab); }

    function candidatesAt(T, S, i, lex, ix, world) {
        var t = T[i], st = S[i], m, c, cands = [];
            m = matchAt(VERB_MAP, S, i); if (m) cands.push({ len: m.len, pri: 9, ent: { type: 'verb', kind: m.payload.kind } });
            m = matchAt(EXCEPT_MAP, S, i); if (m) cands.push({ len: m.len, pri: 8, ent: { type: 'except' } });
            m = matchAt(KEEPCOLOR_MAP, S, i); if (m) cands.push({ len: m.len, pri: 8, ent: { type: 'colorkeep' } });
            m = matchAt(SRC_MAP, S, i); if (m) cands.push({ len: m.len, pri: 6, ent: { type: 'srcmark' } });
            // parts (layers, numbered labels, kind phrases)
            var pl = null, maxP = Math.min(lex.maxN, T.length - i);
            for (var n = maxP; n >= 1 && !pl; n--) {
                var ent = lex.phrases[S.slice(i, i + n).join(' ')];
                if (ent) { if (n === 1 && ent.every(function (e) { return e.layer; }) && (FILLER.indexOf(' ' + t + ' ') !== -1)) continue; pl = { len: n, entries: ent }; }
            }
            if (pl) cands.push({ len: pl.len, pri: 10, ent: { type: 'part', entries: pl.entries } });
            m = matchAt(WHOLE_MAP, S, i); if (m) cands.push({ len: m.len, pri: 5, ent: { type: 'whole' } });
            m = matchAt(GROUP_MAP, S, i); if (m) cands.push({ len: m.len, pri: 7, ent: { type: 'colorsgroup' } });
            m = matchAt(LAYERS_MAP, S, i); if (m) cands.push({ len: m.len, pri: 9, ent: { type: 'layersgroup' } });
            if (ORDINALS.hasOwnProperty(t) && S[i + 1] === 'layer' && lex.layers.length) { var oi = ORDINALS[t], lyr = lex.layers[oi < 0 ? lex.layers.length + oi : oi]; if (lyr) cands.push({ len: 2, pri: 11, ent: { type: 'part', entries: [{ target: { kind: 'layer', layerId: lyr.id, name: lyr.name }, w: 4, layer: true }] } }); }
            if (/^(make|makes|paint|turn|change|set|give|put|dress|wrap|coat|apply|use|switch|convert|swap|replace|recolor|repaint|do|try)$/.test(t)) cands.push({ len: 1, pri: 0.5, ent: { type: 'mk' } });
            m = matchAt(MAIN_MAP, S, i); if (m) cands.push({ len: m.len, pri: 7, ent: { type: 'main' } });
            // exact finish names (>=2 tokens, or a distinctive single token)
            if (ix) {
                var maxF = Math.min(ix.maxName, T.length - i);
                for (var nf = maxF; nf >= 1; nf--) {
                    var key = S.slice(i, i + nf).join(' '), doc = ix.byStem[key];
                    if (doc) {
                        if (nf === 1 && (FAMILY_MAP.map[key] || COLORS[t] || FILLER.indexOf(' ' + t + ' ') !== -1 || t.length < 5 || VERB_MAP.map[key] || HOW_MAP.map[key] || ADJ_MAP.map[key])) continue;
                        if (nf === 1 && RECIPE_MAP.map[key] && !world._partAnywhere) continue;          // a bare "stealth" is the look, not the finish
                        cands.push({ len: nf, pri: nf >= 2 ? 6.5 : 3, ent: { type: 'fname', doc: doc } }); break;
                    }
                }
            }
            m = matchAt(HOW_MAP, S, i); if (m) cands.push({ len: m.len, pri: 4, ent: { type: 'how', kind: m.payload.kind, phrase: m.key } });
            m = matchAt(ADJ_MAP, S, i); if (m && !(m.payload.op === 'intensity' && colorAt(T, i + m.len))) cands.push({ len: m.len, pri: 4.5, ent: { type: 'adj', op: m.payload.op, dir: m.payload.dir, phrase: m.key } });
            m = matchAt(FAMILY_MAP, S, i); if (m) cands.push({ len: m.len, pri: 4.2, ent: { type: 'fam', id: m.payload.id, phrase: m.key } });
            m = matchAt(VIBE_MAP, S, i); if (m) cands.push({ len: m.len, pri: 3.5, ent: { type: 'vibe', section: m.payload.section, phrase: m.key } });
            m = matchAt(RECIPE_MAP, S, i); if (m) cands.push({ len: m.len, pri: world._partAnywhere ? 3 : 4.6, ent: { type: 'recipe', id: m.payload.id, phrase: m.key } });
            c = colorAt(T, i); if (c) cands.push({ len: c.len, pri: 2, ent: { type: 'color', hex: c.hex, word: c.word, name: c.name, custom: !!c.custom, mod: c.mod } });
            var pct = /^(\d{1,3})%$/.exec(t); if (pct) cands.push({ len: 1, pri: 6, ent: { type: 'pct', v: Math.min(100, Number(pct[1])) / 100 } });
        return cands;
    }

    function tag(text, world, lex) {
        var raw = norm(text), T = raw ? raw.split(' ') : [], S, ents = [], fixes = [], i = 0, guard = 0;
        S = T.map(stem);
        var ix = world.index, vocab = null;
        world._partAnywhere = false;
        for (var q = 0; q < T.length; q++) { for (var qn = Math.min(lex.maxN, T.length - q); qn >= 1; qn--) { var qe = lex.phrases[S.slice(q, q + qn).join(' ')]; if (qe && !(qn === 1 && qe.every(function (e) { return e.layer; }) && FILLER.indexOf(' ' + T[q] + ' ') !== -1)) { world._partAnywhere = true; break; } } if (world._partAnywhere) break; }
        while (i < T.length && guard++ < 400) {
            var t = T[i], st = S[i], m, best = null, c;
            if (t === ',' || t === ';') { ents.push({ type: 'sep', s: i, e: i + 1, w: t }); i++; continue; }
            if (SEP_WORDS[t]) { ents.push({ type: 'sep', s: i, e: i + 1, w: t }); i++; continue; }
            if (t === 'and' && T[i + 1] === 'then') { ents.push({ type: 'sep', s: i, e: i + 2, w: 'and then' }); i += 2; continue; }
            if (t === 'but' && !(T[i + 1] === 'not' || T[i + 1] === 'leave')) { ents.push({ type: 'but', s: i, e: i + 1, w: t }); i++; continue; }
            var cands = candidatesAt(T, S, i, lex, ix, world);
            cands = cands.filter(function (cc) {
                if (cc.ent.type === 'colorkeep' && T[i + cc.len] === 'as') return false;                     // "same color as the cyan" is a colour SOURCE
                if (cc.ent.type === 'fname' && cc.len === 2 && DET[T[i - 1]] && lex.colorParts[cc.ent.doc.nameToks[0]] && FAMILY_MAP.map[cc.ent.doc.nameToks[1]]) return false;   // "the black chrome" = the black PART in chrome
                return true;
            });
            if (cands.length) {
                cands.sort(function (a, b) { return (b.len - a.len) || (b.pri - a.pri); });
                best = cands[0];
                if (DET[t] && (best.ent.type === 'whole' || best.ent.type === 'main' || best.ent.type === 'colorsgroup')) {      // "the car paint": let the longer phrase after "the" win
                    var c2 = candidatesAt(T, S, i + 1, lex, ix, world).sort(function (a, b) { return (b.len - a.len) || (b.pri - a.pri); })[0];
                    if (c2 && (i + 1 + c2.len) > (i + best.len)) { i++; continue; }
                }
                best.ent.s = i; best.ent.e = i + best.len; best.ent.w = T.slice(i, i + best.len).join(' ');
                ents.push(best.ent); i += best.len; continue;
            }
            if (t === 'layer' && /^\d{1,2}$/.test(T[i + 1] || '')) {             // "layer 3"
                var li = Number(T[i + 1]) - 1, L = lex.layers[li];
                if (L) { ents.push({ type: 'part', entries: [{ target: { kind: 'layer', layerId: L.id, name: L.name }, w: 4, layer: true }], s: i, e: i + 2, w: t + ' ' + T[i + 1] }); i += 2; continue; }
            }
            if (/^\d+$/.test(t)) { ents.push({ type: 'num', s: i, e: i + 1, w: t }); i++; continue; }
            if (FILLER.indexOf(' ' + t + ' ') !== -1 || DEAD[t] || ((t === 'more' || t === 'less') && colorAt(T, i + 1)) || (COLOR_MODS[t] && colorAt(T, i + 1)) || /^(very|really|super|extra|ultra|so|too|pretty|nice|bit)$/.test(t)) { i++; continue; }
            // typo repair (once per token), then finish-vocabulary words
            if (!vocab) vocab = buildFuzzyVocab(world, lex);
            if (!vocab[t] && !(ix && ix.nameTokDf[st])) {
                var fixed = repairAny(t, vocab);
                if (fixed) { fixes.push([t, fixed]); T[i] = fixed; S[i] = stem(fixed); continue; }
            }
            if (ix && ix.nameTokDf[st] && t.length >= 4 && ix.nameTokDf[st] <= 80 && !COMMON_WORDS[t] && !COMMON_WORDS[st] && !LOCATION_WORDS[t]) { ents.push({ type: 'fw', s: i, e: i + 1, w: t, st: st }); i++; continue; }
            ents.push({ type: 'unk', s: i, e: i + 1, w: t }); i++;
        }
        return { ents: ents, T: T, S: S, fixes: fixes };
    }

    // ================================================================ GROUPING
    function newCmd() { return { targets: [], excl: [], colors: [], fams: [], names: [], fws: [], vibes: [], recipes: [], hows: [], adjs: [], pcts: [], verbs: [], unk: [], unkDet: [], keepColor: false, srcFrom: null, first: null, closed: false, styleAfterTarget: false, span: [], prepTarget: false }; }
    function cmdHasStyle(c) { return c.colors.length || c.fams.length || c.names.length || c.fws.length || c.vibes.length || c.hows.length || c.adjs.length || c.pcts.length || c.keepColor || c.recipes.length; }
    function targetKey(t) { return t.kind + ':' + (t.idx != null ? t.idx : (t.layerId != null ? t.layerId : '')); }
    function addTarget(c, t) { for (var i = 0; i < c.targets.length; i++) if (targetKey(c.targets[i]) === targetKey(t)) return; c.targets.push(t); }

    function resolvePartEntry(ent, lex) {
        // choose the best-weight entries; several equal entries = ambiguous group
        var es = ent.entries, bw = 0, i;
        for (i = 0; i < es.length; i++) if (es[i].w > bw) bw = es[i].w;
        var chosen = es.filter(function (e) { return e.w === bw; }), out = [], seen = {};
        chosen.forEach(function (e) { var k = targetKey(e.target); if (!seen[k]) { seen[k] = 1; out.push(e.target); } });
        return { targets: out, ambiguous: out.length > 1 && chosen.every(function (e) { return e.ambiguous; }) };
    }
    function mainTargets(lex) {
        var paintLayer = null;
        lex.layers.forEach(function (l) { var tk = toks(l.name).map(canonTok); if (!paintLayer && tk.indexOf('paint') !== -1 && tk.every(function (x) { return x === 'paint' || GENERIC_LAYER_TOKENS[x] || x === 'body' || x === 'car'; })) paintLayer = l; });
        if (paintLayer) return [{ kind: 'layer', layerId: paintLayer.id, name: paintLayer.name }];
        var p = lex.sortedParts[0]; return p ? [{ kind: 'part', idx: p.idx, label: partDisplay(p) }] : [];
    }
    function partHex(world, target) {
        var ps = world.parts || [];
        for (var i = 0; i < ps.length; i++) if (target.kind === 'part' && ps[i].idx === target.idx) return ps[i].hex || null;
        return null;
    }
    function unionTargets(a, b) { var out = [], seen = {}; (a || []).concat(b || []).forEach(function (t) { var k = targetKey(t); if (!seen[k]) { seen[k] = 1; out.push(t); } }); return out; }
    function groupCommands(tg, world, lex) {
        var ents = tg.ents, T = tg.T, cmds = [], cur = newCmd(), pendingExcl = [], exceptMode = false, srcPending = false, notes = [], k;
        function close() { if (cur.span.length || cur.targets.length || cmdHasStyle(cur) || cur.verbs.length) cmds.push(cur); cur = newCmd(); exceptMode = false; srcPending = false; }
        function prevTok(e) { return e.s > 0 ? T[e.s - 1] : ''; }
        function prev2(e) { return e.s > 1 ? T[e.s - 2] + ' ' + T[e.s - 1] : ''; }
        function nextTok(e) { return T[e.e] || ''; }
        function prepBefore(e) { var a = T[e.s - 1] || '', b2 = T[e.s - 2] || ''; return !!(PREP[a] || (DET[a] && PREP[b2])); }
        function conflicts(kind) {
            if (kind === 'color' || kind === 'colorkeep') return !!(cur.colors.length || cur.keepColor);
            if (kind === 'fam' || kind === 'fname' || kind === 'fw' || kind === 'vibe') return !!(cur.fams.length || cur.names.length || cur.fws.length || cur.vibes.length);
            if (kind === 'how') return cur.hows.length > 0;
            return false;
        }
        function attachTarget(targets, ent) {
            if (exceptMode) { targets.forEach(function (t) { pendingExcl.push(t); }); return; }
            var prepOk = prepBefore(ent);
            // target-first phrasing ("numbers white chrome sponsors matte"): a new target after style starts the next command
            if (cur.targets.length && cmdHasStyle(cur) && cur.first === 'target' && cur.styleAfterTarget && !prepOk) close();
            if (cur.first == null) cur.first = cmdHasStyle(cur) ? 'style' : 'target';
            targets.forEach(function (t) { addTarget(cur, t); });
            if (prepOk) cur.prepTarget = true;
            if (cur.first === 'style') cur.closed = true;                 // style-first phrasing ("gold chrome numbers"): the target completes the command
            cur.styleAfterTarget = false;
        }
        function styleEntity(kind) {
            exceptMode = false;
            if (cur.closed && conflicts(kind)) { close(); cur.soft = true; }   // this style belongs to the NEXT command (it repeats what this one already says)
            else if (cur.closed) cur.closed = false;                       // "keep my colors but make everything glossy": still one command
            else if (cur.first === 'target' && cur.targets.length && conflicts(kind)) { close(); cur.soft = true; }   // "whole car midnight blue with silver numbers": the 2nd colour starts the next command
            if (cur.first == null) cur.first = 'style';
            if (cur.first === 'target' && cur.targets.length) cur.styleAfterTarget = true;
        }
        for (k = 0; k < ents.length; k++) {
            var e = ents[k], nx = ents[k + 1];
            switch (e.type) {
                case 'sep': close(); break;
                case 'but': exceptMode = false; break;
                case 'mk': exceptMode = false; break;
                case 'except': exceptMode = true; break;
                case 'srcmark': srcPending = true; break;
                case 'colorkeep': styleEntity('colorkeep'); cur.keepColor = true; cur.span.push(e.w); break;
                case 'verb': cur.verbs.push(e.kind); cur.span.push(e.w); if (cur.first == null) cur.first = 'style'; break;
                case 'part': {
                    var r = resolvePartEntry(e, lex);
                    cur.span.push(e.w);
                    if (srcPending) {                                      // "same as the numbers": a colour SOURCE, not the target
                        srcPending = false; var pt = r.targets[0], hx = pt ? partHex(world, pt) : null;
                        styleEntity('color');
                        if (hx) cur.colors.push({ mode: 'part', hex: hx, word: colorWord(hx), name: pt.label || pt.name, fromIdx: pt.idx, from: pt.label || pt.name });
                        else notes.push('I can only copy a colour from one of the car\'s colour parts (“' + e.w + '” has none).');
                        break;
                    }
                    if (r.ambiguous) { cur.ambiguous = (cur.ambiguous || []).concat([{ word: e.w, targets: r.targets }]); }
                    attachTarget(r.targets, e); break;
                }
                case 'whole': cur.span.push(e.w); attachTarget([{ kind: 'whole' }], e); break;
                case 'colorsgroup': cur.span.push(e.w); attachTarget([{ kind: 'colors' }], e); break;
                case 'layersgroup': cur.span.push(e.w); attachTarget([{ kind: 'layers' }], e); break;
                case 'main': cur.span.push(e.w); attachTarget(mainTargets(lex), e); break;
                case 'color': {
                    var w = e.word, exist = unionTargets(lex.colorParts[w], lex.labels[e.name]); if (!exist.length) exist = null;
                    var det = !!DET[prevTok(e)];
                    var followedNoun = PARTNOUN[nextTok(e)];
                    var nextIsColor = nx && nx.type === 'color' && (nx.s === e.e || ((T[e.e] === 'to' || T[e.e] === 'into') && nx.s === e.e + 1));
                    var hasTarget = cur.targets.length > 0;
                    var asPart = false;
                    var startsNew = hasTarget && cmdHasStyle(cur) && cur.first === 'target' && exist && !srcPending && (det || nextIsColor);   // "cyan candy and THE yellow chrome" / "cyan chrome and yellow gold"
                    var andBefore = T[e.s - 1] === 'and' || (DET[T[e.s - 1]] && T[e.s - 2] === 'and');
                    var listJoin = hasTarget && !cmdHasStyle(cur) && exist && andBefore;                                    // "the cyan and the yellow chrome"
                    var lookAndColor = !hasTarget && exist && T[e.e] === 'and' && nx && nx.type === 'color' && (lex.colorParts[nx.word] || lex.labels[nx.name]);   // "make cyan and yellow chrome"
                    if (exceptMode && exist) asPart = true;
                    else if (startsNew || listJoin || lookAndColor) asPart = true;
                    else if (!hasTarget && exist) {
                        if (followedNoun || det || nextIsColor) asPart = true;
                    }
                    if (srcPending) {                                      // "the same as the blue" -> car colour
                        srcPending = false; styleEntity('color');
                        var g = exist && exist[0] ? partHex(world, exist[0]) : null;
                        cur.colors.push(g ? { mode: 'part', hex: g, word: w, name: e.name, fromIdx: exist[0].idx, from: exist[0].label } : { mode: 'palette', hex: e.hex, word: w, name: e.name });
                        cur.span.push(e.w); break;
                    }
                    cur.span.push(e.w);
                    if (e.name === 'candy apple red' && !asPart) { cur.fams.push(familyById('candy')); }
                    if (asPart) {
                        var tg2 = exist.slice();
                        var uniqT = []; var seenT = {}; tg2.forEach(function (t) { if (!seenT[targetKey(t)]) { seenT[targetKey(t)] = 1; uniqT.push(t); } });
                        attachTarget(uniqT, e);
                        if (followedNoun) { /* consumed below by the leftover pass */ }
                    } else {
                        // a colour word after "the/my" with a matching part on the car, in a command that already has a target = the car's OWN colour
                        var fromCar = det && exist && exist.length && hasTarget;
                        styleEntity('color');
                        if (fromCar) { var hx2 = partHex(world, exist[0]); cur.colors.push(hx2 ? { mode: 'part', hex: hx2, word: w, name: e.name, fromIdx: exist[0].idx, from: exist[0].label } : { mode: 'palette', hex: e.hex, word: w, name: e.name }); }
                        else cur.colors.push({ mode: e.custom ? 'custom' : 'palette', hex: e.hex, word: w, name: e.name, metal: !!METAL_WORDS[e.name] });
                    }
                    break;
                }
                case 'fam': styleEntity('fam'); cur.fams.push(familyById(e.id)); cur.span.push(e.w); break;
                case 'fname': styleEntity('fname'); cur.names.push(e.doc); cur.span.push(e.w); break;
                case 'fw': styleEntity('fw'); cur.fws.push(e.w); cur.span.push(e.w); break;
                case 'vibe': styleEntity('vibe'); cur.vibes.push(e.section); cur.span.push(e.w); break;
                case 'recipe': styleEntity('recipe'); cur.recipes.push(e.id); cur.span.push(e.w); break;
                case 'how': styleEntity('how'); cur.hows.push({ kind: e.kind, phrase: e.phrase }); cur.span.push(e.w); break;
                case 'adj': styleEntity('adj'); cur.adjs.push({ op: e.op, dir: e.dir, phrase: e.phrase }); cur.span.push(e.w); break;
                case 'pct': styleEntity('pct'); cur.pcts.push(e.v); cur.span.push(e.w); break;
                case 'num': break;
                case 'unk': cur.unk.push(e.w); if (DET[prevTok(e)] && !LOCATION_WORDS[e.w] && !exceptMode) { cur.unkDet.push(e.w); attachTarget([{ kind: 'unresolved', word: e.w }], e); } break;   // "the widgets": a noun we do not know is still a TARGET boundary
                default: break;
            }
        }
        close();
        // a "next command" that never got a target of its own is a continuation ("white numbers with a black outline"), not a new command
        for (k = cmds.length - 1; k > 0; k--) {
            var sc = cmds[k], pv = cmds[k - 1];
            if (sc.soft && !sc.targets.length && !sc.verbs.length) {
                ['colors', 'fams', 'names', 'fws', 'vibes', 'recipes', 'hows', 'adjs', 'pcts', 'unk', 'span'].forEach(function (f) { pv[f] = pv[f].concat(sc[f]); });
                if (sc.keepColor) pv.keepColor = true;
                pv.softMerged = true; cmds.splice(k, 1);
            }
        }
        return { cmds: cmds, pendingExcl: pendingExcl, notes: notes };
    }

    // ================================================================ FINALIZE (groups -> commands)
    function famColorMode(fams, via) {
        if (via === 'name') return 'finish';
        if (!fams || !fams.length) return 'finish';
        return fams[fams.length - 1].colorMode || 'mine';          // the head noun decides ("glitter chrome" -> chrome)
    }
    function adjustsFrom(rc) {
        return rc.adjs.map(function (a) {
            var mag = 1, p = a.phrase || '';
            if (/(^| )(a bit|a little|bit|little)( |$)/.test(p)) mag = 0.5; else if (/(^| )(way|much|lots)( |$)/.test(p)) mag = 2;
            return { op: a.op, dir: a.dir, mag: mag };
        });
    }
    function whoText(cmd, world) {
        var ps = world.parts || [], names = [];
        (cmd.targets || []).forEach(function (t) {
            if (!t) return;
            if (t.kind === 'whole') names.push('the whole car');
            else if (t.kind === 'layers') names.push('every layer');
            else if (t.kind === 'colors') names.push('every colour');
            else if (t.kind === 'layer') names.push(t.name);
            else { var p = null; for (var i = 0; i < ps.length; i++) if (ps[i].idx === t.idx) p = ps[i]; names.push(p ? partDisplay(p) : (t.label || 'that part')); }
        });
        var s;
        if (names.length <= 1) s = names[0] || '';
        else s = names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
        if (cmd.exclude && cmd.exclude.length) s += ' (except ' + cmd.exclude.map(function (t) { return t.kind === 'layer' ? t.name : (t.label || 'that part'); }).join(', ') + ')';
        return s;
    }
    function colorTextOf(color) {
        if (!color) return '';
        if (color.mode === 'keep') return 'its own colour';
        if (color.mode === 'asis') return 'the colour it has now';
        if (color.mode === 'finish') return 'the finish’s own colour';
        if (color.mode === 'part') return 'the ' + (color.word || 'colour') + ' from ' + (color.from || 'another part');
        return color.name && color.name !== color.hex ? color.name : (color.word || color.hex);
    }
    function howTextOf(cmd) {
        if (cmd.how === 'shine') return 'just the shine';
        if (cmd.how === 'blend') return Math.round((cmd.amount == null ? 0.5 : cmd.amount) * 100) + '% blended with your paint';
        return '';
    }
    function pickRandom(list, rand) { return list.length ? list[Math.min(list.length - 1, Math.floor(rand() * list.length))] : null; }

    function expandRecipe(recipe, world, lex, opts) {
        var ix = world.index, cmds = [], notes = [];
        if (recipe.look) return { cmds: [{ type: 'look', id: recipe.look, label: recipe.label, blurb: recipe.blurb, targets: [{ kind: 'whole' }], recipe: recipe.id, said: recipe.label }], notes: notes };
        var parts = world.parts || [];
        var roles = { main: [], second: [], dark: [], white: [], rest: [] };
        lex.sortedParts.forEach(function (p, i) { (i === 0 ? roles.main : roles.second).push({ kind: 'part', idx: p.idx, label: partDisplay(p) }); });
        parts.forEach(function (p) {
            if (p.pick) return;
            if (p.kind === 'remaining') roles.rest.push({ kind: 'part', idx: p.idx, label: partDisplay(p) });
            else if (p.tone === 'dark') roles.dark.push({ kind: 'part', idx: p.idx, label: partDisplay(p) });
            else if (p.tone === 'white') roles.white.push({ kind: 'part', idx: p.idx, label: partDisplay(p) });
        });
        Object.keys(recipe.roles).forEach(function (role) {
            var slot = recipe.roles[role], targets = [];
            if (role.indexOf('layer:') === 0) {
                var want = canonTok(role.slice(6));
                lex.layers.forEach(function (l) { if (toks(l.name).map(canonTok).indexOf(want) !== -1) targets.push({ kind: 'layer', layerId: l.id, name: l.name }); });
            } else targets = roles[role] || [];
            if (!targets.length) return;
            var key = slot.key ? (ix && ix.byKey['base::' + slot.key] ? 'base::' + slot.key : (ix && ix.byKey['monolithic::' + slot.key] ? 'monolithic::' + slot.key : null)) : resolveFamilyKey(ix, slot.fam);
            var doc = key && ix ? ix.byKey[key] : null;
            function colorOf(c) { return c === 'keep' ? { mode: 'keep' } : (c === 'finish' ? { mode: 'finish' } : { mode: 'palette', hex: c, word: colorWord(c), name: colorWord(c) }); }
            var adjs = []; if (slot.adj) { if (slot.adj.dSat) adjs.push({ op: 'dSat', value: slot.adj.dSat }); if (slot.adj.dBri) adjs.push({ op: 'dBri', value: slot.adj.dBri }); if (slot.adj.dHue) adjs.push({ op: 'dHue', value: slot.adj.dHue }); }
            function emit(tg, col) { cmds.push({ type: 'style', targets: tg, exclude: [], needsTarget: false, color: colorOf(col), finish: doc ? { key: doc.key, name: doc.name, via: 'recipe', family: slot.fam || null, alts: [] } : null,
                how: 'all', amount: null, adjusts: adjs, recipe: recipe.id, said: recipe.label, role: role }); }
            if (slot.colors && slot.colors.length) targets.forEach(function (t, n) { emit([t], slot.colors[n % slot.colors.length]); }); else emit(targets, slot.color);
        });
        if (!cmds.length) notes.push('That look needs parts this car doesn’t have.');
        return { cmds: cmds, notes: notes };
    }

    function finalize(g, tg, world, lex, opts) {
        var out = [], notes = g.notes.slice(), ix = world.index, ctx = world.ctx || {}, rand = (opts && opts.rand) || Math.random;
        var prevTargets = null, leftover = [], usedLocation = false;
        var i, n;
        for (n = 0; n < g.cmds.length; n++) {
            var rc = g.cmds[n], cmd = { type: null, targets: rc.targets.slice(), exclude: [], needsTarget: false, color: null, finish: null, how: null, amount: null, adjusts: [], recipe: null, said: rc.span.join(' '), unk: rc.unk };
            var bare = !cmdHasStyle(rc);
            var verb = rc.verbs.length ? rc.verbs[0] : null;
            // -------- verbs
            if (verb && bare) {
                if (verb === 'undo' || verb === 'redo' || verb === 'startover' || verb === 'help' || verb === 'save') { cmd.type = verb; cmd.targets = []; out.push(cmd); continue; }
                if (verb === 'surprise') { cmd.type = 'surprise'; }
                if (verb === 'another') { cmd.type = 'another'; }
            } else if (verb === 'surprise') cmd.type = 'surprise';
            // -------- recipes / surprise
            if (rc.recipes.length && !cmd.type) {
                var rec = recipeById(rc.recipes[rc.recipes.length - 1]);
                var ex = expandRecipe(rec, world, lex, opts); notes = notes.concat(ex.notes);
                if (rc.targets.length && rec.roles && (rec.roles.main || rec.roles.second)) {            // "make the numbers something crazy": that look's main material on just those targets
                    var slot = rec.roles.main || rec.roles.second, rkey = slot.key ? 'base::' + slot.key : resolveFamilyKey(ix, slot.fam), rdoc = rkey && ix ? ix.byKey[rkey] : null;
                    if (rdoc) { out.push({ type: 'style', targets: rc.targets.slice(), exclude: [], needsTarget: false, color: slot.color === 'keep' ? { mode: 'keep' } : (slot.color === 'finish' ? { mode: 'finish' } : { mode: 'palette', hex: slot.color, word: colorWord(slot.color), name: colorWord(slot.color) }), finish: { key: rdoc.key, name: rdoc.name, via: 'recipe', family: slot.fam || null, alts: [] }, how: 'all', amount: null, adjusts: [], recipe: rec.id, said: rc.span.join(' '), unk: [] }); continue; }
                }
                if (rc.targets.length) notes.push('A look like “' + rec.label + '” covers the whole car — name a part and a finish to change just that.');
                ex.cmds.forEach(function (c) { c.said = rc.span.join(' '); out.push(c); });
                if (!ex.cmds.length) { /* notes carry the reason */ }
                continue;
            }
            if (cmd.type === 'surprise') {
                var pool = RECIPES.filter(function (r) { return r.id !== ctx.lastRecipe; });
                var pick = pickRandom(pool, rand), ex2 = expandRecipe(pick, world, lex, opts);
                ex2.cmds.forEach(function (c) { c.surprise = true; c.said = 'surprise me'; c.recipeLabel = pick.label; c.blurb = pick.blurb; out.push(c); });
                if (!ex2.cmds.length) notes.push('Nothing to surprise — this car has no parts I can restyle.');
                continue;
            }
            // -------- what kind of command
            var said = { names: rc.names, fams: rc.fams, fws: rc.fws, vibes: rc.vibes };
            var wantsFinish = rc.names.length || rc.fams.length || rc.fws.length || rc.vibes.length;
            var hasColor = rc.colors.length || rc.keepColor;
            var shine = rc.hows.some(function (h) { return h.kind === 'shine'; });
            var blendWord = rc.hows.filter(function (h) { return h.kind === 'blend'; });
            var allWord = rc.hows.some(function (h) { return h.kind === 'all'; });
            var amount = null;
            if (rc.pcts.length) amount = rc.pcts[rc.pcts.length - 1];
            else if (blendWord.length) { var bp = blendWord[blendWord.length - 1].phrase; amount = AMOUNT_WORDS[bp] != null ? AMOUNT_WORDS[bp] : 0.5; }
            if (cmd.type === 'another') { /* keep */ }
            else if (wantsFinish || hasColor || shine) cmd.type = 'style';
            else if (rc.adjs.length) cmd.type = 'adjust';
            else if (amount != null) cmd.type = 'adjust';
            else if (rc.targets.length) cmd.type = 'select';
            else { if (rc.unk.length) leftover = leftover.concat(rc.unk); continue; }
            // -------- style resolution
            if (cmd.type === 'style') {
                var fin = wantsFinish ? resolveFinish(ix, said) : null;
                var colorEnt = rc.keepColor ? { mode: 'keep' } : (rc.colors.length ? rc.colors[rc.softMerged ? 0 : rc.colors.length - 1] : null);
                if (rc.colors.length > 1 && rc.colors[0].hex !== rc.colors[rc.colors.length - 1].hex) notes.push('You named two colours for one part — I used ' + (colorEnt.name || colorEnt.word) + '.');
                if (colorEnt && colorEnt.metal && !fin) {                      // "make the numbers gold" -> gold, metallic
                    var mk = resolveFamilyKey(ix, 'metallic'), md = mk && ix ? ix.byKey[mk] : null;
                    if (md) fin = { key: md.key, name: md.name, via: 'family', family: 'metallic', alts: [] };
                }
                if (fin && fin.key == null) { notes.push('I couldn’t find a “' + (fin.missing || rc.span.join(' ')) + '” finish — tap FINISH to browse.'); fin = null; if (!hasColor && !shine) { cmd.type = rc.targets.length ? 'select' : 'none'; } }
                cmd.finish = fin;
                if (colorEnt) cmd.color = colorEnt;
                else if (fin) cmd.color = { mode: famColorMode(rc.fams.length ? rc.fams : null, fin.via) === 'mine' ? 'keep' : 'finish', implied: true };
                if (shine) { cmd.how = 'shine'; if (fin) cmd.color = { mode: 'keep', implied: true }; }
                else if (amount != null && (fin || blendWord.length)) { cmd.how = amount >= 0.995 ? 'all' : 'blend'; cmd.amount = amount; }
                else if (allWord) cmd.how = 'all';
                if (cmd.type === 'style' && !cmd.finish && !cmd.color && !cmd.how) cmd.type = rc.adjs.length ? 'adjust' : (rc.targets.length ? 'select' : 'none');
                cmd.adjusts = adjustsFrom(rc);
            } else if (cmd.type === 'adjust') {
                cmd.adjusts = adjustsFrom(rc);
                if (amount != null) cmd.adjusts.push({ op: 'blendTo', value: amount });
            }
            // -------- targets
            if (cmd.type === 'style' || cmd.type === 'adjust' || cmd.type === 'another' || cmd.type === 'select') {
                var unresolved = cmd.targets.filter(function (t) { return t.kind === 'unresolved'; });
                if (unresolved.length) {                                               // "the widgets": never quietly reuse another part for a noun we do not know
                    cmd.targets = cmd.targets.filter(function (t) { return t.kind !== 'unresolved'; });
                    if (!cmd.targets.length) { cmd.needsTarget = true; cmd.unknownNoun = unresolved[0].word; cmd.question = 'I don’t see “' + unresolved[0].word + '” on this car — which part did you mean?'; }
                }
                var explicit = cmd.targets.length > 0 || !!cmd.needsTarget;
                if (cmd.how === 'shine') { cmd.targets = [{ kind: 'whole' }]; if (explicit && rc.targets.some(function (t) { return t.kind !== 'whole'; })) notes.push('“Just the shine” always covers the whole car — your colours stay as they are.'); }
                else if (rc.ambiguous && rc.ambiguous.length && explicit && cmd.targets.length === rc.ambiguous[0].targets.length) {
                    cmd.options = rc.ambiguous[0].targets.slice(); cmd.needsTarget = true; cmd.targets = []; cmd.question = 'Which “' + rc.ambiguous[0].word + '”?';
                } else if (!explicit) {
                    if (prevTargets && n > 0) { cmd.targets = prevTargets.slice(); cmd.inherited = true; }
                    else if (ctx.selected != null && ctx.selected >= 0) { cmd.targets = [{ kind: 'part', idx: ctx.selected }]; cmd.fromContext = 'selected'; }
                    else if (ctx.last && ctx.last.targets && ctx.last.targets.length) { cmd.targets = ctx.last.targets.slice(); cmd.fromContext = 'last'; }
                    else { cmd.needsTarget = true; cmd.question = 'Which part should I change?'; }
                }
                if (cmd.targets.length) prevTargets = cmd.targets;
                else if (cmd.options || cmd.needsTarget) prevTargets = null;
            }
            if (cmd.type === 'none') { if (rc.unk.length) leftover = leftover.concat(rc.unk); continue; }
            // "make the numbers red, then chrome": the second step keeps the colour the first one just set
            if (cmd.type === 'style' && cmd.inherited && cmd.color && cmd.color.implied && out.length) {
                var pc = out[out.length - 1];
                if (pc && pc.type === 'style' && pc.color && (pc.color.mode === 'palette' || pc.color.mode === 'custom' || pc.color.mode === 'part')) cmd.color = { mode: 'asis', implied: true };
            }
            out.push(cmd);
        }
        // -------- a clause that only says HOW ("just the shine, make it chrome") belongs to the neighbouring finish command
        for (i = out.length - 1; i >= 0; i--) {
            var oc = out[i];
            if (oc.type === 'style' && !oc.finish && !oc.color && oc.how) {
                var nb = null;
                if (out[i + 1] && out[i + 1].type === 'style' && out[i + 1].finish) nb = out[i + 1]; else if (out[i - 1] && out[i - 1].type === 'style' && out[i - 1].finish) nb = out[i - 1];
                if (nb && !nb.how) { nb.how = oc.how; nb.amount = oc.amount; if (oc.how === 'shine') { nb.targets = [{ kind: 'whole' }]; nb.needsTarget = false; nb.color = { mode: 'keep', implied: true }; } out.splice(i, 1); }
            }
        }
        // -------- exclusions ("everything matte except the numbers")
        if (g.pendingExcl.length) {
            var hit = false;
            var remIdx = {}; (world.parts || []).forEach(function (p) { if (p.kind === 'remaining') remIdx[p.idx] = 1; });
            out.forEach(function (c) {                                   // "keep the sponsors, make everything else matte": everything else = the rest of the car
                if ((c.type === 'style' || c.type === 'adjust') && c.targets.length === 1 && c.targets[0].kind === 'part' && remIdx[c.targets[0].idx]) c.targets = [{ kind: 'whole' }];
                else if ((c.type === 'style' || c.type === 'adjust') && !c.targets.length && !c.options) { c.targets = [{ kind: 'whole' }]; c.needsTarget = false; c.question = null; }
            });
            out.forEach(function (c) { if ((c.type === 'style' || c.type === 'adjust') && c.targets.some(function (t) { return t.kind === 'whole' || t.kind === 'colors' || t.kind === 'layers'; })) { c.exclude = g.pendingExcl.slice(); hit = true; } });
            if (!hit) notes.push('Nothing to leave out yet — say what to change first, e.g. “everything matte except the numbers”.');
        }
        // -------- words we could not use
        tg.ents.forEach(function (e) { if (e.type === 'unk' && leftover.indexOf(e.w) === -1) leftover.push(e.w); });
        // location words with no way to resolve them
        var anyTarget = out.some(function (c) { return (c.targets && c.targets.length && !c.inherited && !c.fromContext) || c.type === 'undo' || c.type === 'redo' || c.type === 'startover' || c.type === 'help' || c.type === 'another'; });
        if (!anyTarget) {
            for (i = 0; i < tg.T.length && !usedLocation; i++) if (LOCATION_WORDS[tg.T[i]] && !(world.locationOk)) {
                if (/^(top|bottom|left|right|front|back|side|sides|rear|panel|panels)$/.test(tg.T[i]) && out.length && out[0].targets && out[0].targets.length) continue;
                notes.push('I can’t tell where the “' + tg.T[i] + '” is on a flat paint template. Tap it on the car, then tell me what to do — or name a colour part or layer.'); usedLocation = true;
            }
        }
        // a word already understood is not "left over" (unk list also holds words repaired later)
        leftover = leftover.filter(function (w) { return !LOCATION_WORDS[w] || !usedLocation; });
        return { cmds: out, notes: notes, leftover: leftover };
    }

    // ================================================================ PUBLIC: parse / describe / suggest
    function parse(text, world, opts) {
        world = world || {};
        var lex = buildLexicon(world), tg = tag(text, world, lex), g = groupCommands(tg, world, lex), f = finalize(g, tg, world, lex, opts || {});
        var plan = { text: String(text == null ? '' : text), cmds: f.cmds, notes: f.notes, leftover: f.leftover, fixes: tg.fixes, empty: !norm(text) };
        plan.understood = f.cmds.length > 0;
        return plan;
    }
    function describe(cmd, world) {
        var d = { who: whoText(cmd, world), color: colorTextOf(cmd.color), finish: cmd.finish ? cmd.finish.name : '', how: howTextOf(cmd), sentence: '' };
        var bits = [];
        if (cmd.type === 'style') {
            if (cmd.finish) bits.push(cmd.finish.name);
            if (cmd.color && !cmd.color.implied && cmd.color.mode !== 'keep') bits.push('in ' + d.color);
            else if (cmd.color && cmd.color.mode === 'keep' && !cmd.color.implied) bits.push('keeping its colour');
            if (d.how) bits.push(d.how);
            d.sentence = (d.who || 'It') + ' → ' + (bits.join(' ') || 'no change');
        } else if (cmd.type === 'adjust') {
            d.sentence = (d.who || 'It') + ' → ' + cmd.adjusts.map(adjustWords).join(', ');
        } else if (cmd.type === 'look') d.sentence = 'The “' + cmd.label + '” look on the whole car';
        else if (cmd.type === 'select') d.sentence = 'Show ' + d.who;
        else d.sentence = cmd.type;
        return d;
    }
    function adjustWords(a) {
        var d = a.dir > 0 ? '+' : '−';
        switch (a.op) {
            case 'size': return a.dir > 0 ? 'bigger pattern' : 'finer pattern';
            case 'bri': return a.dir > 0 ? 'brighter' : 'darker';
            case 'sat': return a.dir > 0 ? 'more vivid' : 'more muted';
            case 'hue': return a.dir > 0 ? 'warmer hue' : 'cooler hue';
            case 'blend': return a.dir > 0 ? 'more of the finish' : 'less of the finish';
            case 'intensity': return a.dir > 0 ? 'more' : 'less';
            case 'blendTo': return Math.round(a.value * 100) + '% of the finish';
            case 'dSat': return a.value > 0 ? 'more vivid' : 'more muted';
            case 'dBri': return a.value > 0 ? 'brighter' : 'darker';
            case 'dHue': return 'hue shift';
            default: return d + a.op;
        }
    }
    function bodyParts(world) {
        var ps = (world.parts || []).filter(isBodyColor).sort(function (a, b) { return (b.share || 0) - (a.share || 0); });
        if (!ps.length) ps = (world.parts || []).filter(function (p) { return p.kind !== 'layer' && p.layerId == null && p.kind !== 'remaining' && !p.pick; }).sort(function (a, b) { return (b.share || 0) - (a.share || 0); });
        return ps;
    }
    // Phrase ideas built from THIS car's real parts and layers. Every phrase is one the parser understands (tested).
    function suggest(world, opts) {
        var out = [], parts = bodyParts(world), layers = world.layers || [], ix = world.index;
        var famCycle = ['candy', 'chrome', 'pearl', 'carbon', 'flake', 'matte'], fi = (opts && opts.seed) || 0;
        function fam() { var f = famCycle[fi % famCycle.length]; fi++; return f; }
        parts.slice(0, 2).forEach(function (p) {
            var l = String(partDisplay(p)).replace(/\s+\d+$/, '').toLowerCase();
            out.push({ kind: 'part', label: 'The ' + l + ' → ' + fam(), phrase: 'make the ' + l + ' ' + famCycle[(fi - 1) % famCycle.length], hex: p.hex });
        });
        var byName = function (re) { for (var i = 0; i < layers.length; i++) if (re.test(layers[i].name.toLowerCase())) return layers[i]; return null; };
        var num = byName(/number/), spon = byName(/sponsor/), tape = byName(/tape|stripe/), paint = byName(/paint|body/);
        if (num) out.push({ kind: 'layer', label: 'Numbers → gold chrome', phrase: 'make the numbers gold chrome' });
        if (spon) out.push({ kind: 'layer', label: 'Sponsors → keep, rest matte', phrase: 'everything matte except the sponsors' });
        if (tape) out.push({ kind: 'layer', label: 'Tape → pearl white', phrase: 'make the ' + toks(tape.name).filter(function (t) { return !GENERIC_LAYER_TOKENS[stem(t)]; })[0] + ' pearl white' });
        if (paint && !parts.length) out.push({ kind: 'layer', label: 'Car paint → candy', phrase: 'make the car paint candy' });
        out.push({ kind: 'whole', label: 'Everything matte black', phrase: 'everything matte black' });
        out.push({ kind: 'vibe', label: 'Make it look expensive', phrase: 'make it look expensive' });
        out.push({ kind: 'vibe', label: 'Stealth', phrase: 'stealth' });
        out.push({ kind: 'vibe', label: 'Race day', phrase: 'race day' });
        out.push({ kind: 'vibe', label: 'Surprise me', phrase: 'surprise me' });
        return out;
    }


    // ================================================================ AUTOCOMPLETE (the word being typed)
    // Returns [{text, kind}] — completions for the LAST word (or last two words) of `text`, from this car's own parts and layers first,
    // then colours, finish families, top-shelf finish names, looks and commands. The UI inserts `text` in place of the typed tail.
    var COMPLETE_FAMILIES = ['chrome', 'candy', 'pearl', 'matte', 'satin', 'gloss', 'metallic', 'carbon fiber', 'holographic', 'glitter', 'flake', 'brushed metal', 'rusty', 'camo', 'flames', 'frozen', 'neon', 'marble', 'leather', 'galaxy', 'lava', 'snakeskin', 'wood grain', 'sparkly', 'wet look'];
    var COMPLETE_COMMANDS = ['undo', 'redo', 'another one', 'surprise me', 'start over', 'darker', 'brighter', 'bigger', 'finer', 'more vivid', 'just the shine', 'everything except'];
    function complete(text, world, max) {
        var raw = String(text == null ? '' : text);
        if (!raw || /\s$/.test(raw)) return [];
        var low = norm(raw), words = low.split(' ');
        var w1 = words[words.length - 1] || '', w2 = words.length > 1 ? words[words.length - 2] + ' ' + w1 : '';
        if (w1.length < 2 || w1.charAt(0) === '#' || /\d/.test(w1)) return [];
        var out = [], seen = {}, world0 = world || {};
        function add(cand, kind) {
            var c = norm(cand); if (!c || seen[c] || c === w1 || c === w2) return;
            var hit = null;
            if (c.indexOf(w1) === 0) hit = { text: cand.toLowerCase(), replace: w1 };
            else if (w2 && c.indexOf(w2) === 0) hit = { text: cand.toLowerCase(), replace: w2 };
            if (!hit) return; seen[c] = 1; hit.kind = kind; out.push(hit);
        }
        (world0.parts || []).forEach(function (p) { if (p.kind !== 'layer' && p.layerId == null) add(String(p.label || p.name || '').replace(/\s+\d+$/, ''), 'part'); });
        (world0.layers || []).forEach(function (l) { add(String(l.name).replace(/_/g, ' '), 'layer'); toks(l.name).forEach(function (t) { if (t.length > 3 && !GENERIC_LAYER_TOKENS[stem(t)]) add(t, 'layer'); }); });
        Object.keys(COLORS).forEach(function (n) { add(n, 'color'); });
        COMPLETE_FAMILIES.forEach(function (f) { add(f, 'finish'); });
        RECIPES.forEach(function (r) { add(r.label, 'look'); r.words.slice(0, 3).forEach(function (w) { add(w, 'look'); }); });
        COMPLETE_COMMANDS.forEach(function (c) { add(c, 'command'); });
        var ix = world0.index;
        if (ix) ix.top.slice(0, 50).forEach(function (k) { var d = ix.byKey[k]; if (d) add(d.name, 'finish'); });
        var order = { part: 0, layer: 0, color: 1, finish: 2, look: 3, command: 4 };
        out.sort(function (a, b) { return (order[a.kind] - order[b.kind]) || (a.text.length - b.text.length); });
        return out.slice(0, max || 6);
    }

    // Finish search for the AI copilot (and anyone else): words -> ranked finishes, using the same synonyms as the parser.
    function searchFinishes(ix, query, limit) {
        if (!ix) return [];
        var ts = toks(query).filter(function (t) { return FILLER.indexOf(' ' + t + ' ') === -1 && !DEAD[t] && t.length > 1; }), concepts = [], seen = {};
        ts.forEach(function (t) {
            var st = stem(t), fm = FAMILY_MAP.map[st]; if (fm && !seen[fm.id]) { seen[fm.id] = 1; concepts.push(famConcept(familyById(fm.id))); }
            else if (!fm) concepts.push([{ t: st, w: 1 }]);
        });
        if (!concepts.length) return [];
        var fams = Object.keys(seen).map(familyById), r = rank(ix, concepts, { phrase: norm(ts.join(' ')), boost: boostFor(fams) });
        return r.slice(0, limit || 8).map(function (x) { return { key: x.doc.key, name: x.doc.name, section: String(x.doc.sec || '').replace(/[^ -~]+/g, '').trim(), about: x.doc.desc }; });
    }
    function lookCmds(id, world) { var r = recipeById(id); if (!r) return []; return expandRecipe(r, world, buildLexicon(world), {}).cmds; }

    var PUBLIC = { _debugTag: function (text, world) { var lex = buildLexicon(world), tg = tag(text, world, lex); return tg.ents.map(function (e) { var o = {}; for (var k in e) if (k !== 'entries' && k !== 'doc') o[k] = e[k]; if (e.entries) o.entries = e.entries.map(function (x) { return x.target.label || x.target.name || x.target.kind; }); if (e.doc) o.doc = e.doc.name; return o; }); }, norm: norm, stem: stem, toks: toks, buildIndex: buildIndex, rank: rank, colorWord: colorWord, hexToHsl: hexToHsl, hslToHex: hslToHex, lookupColor: lookupColor, COLORS: COLORS, FAMILIES: FAMILIES, RECIPES: RECIPES,
        VIBE_SECTIONS: VIBE_SECTIONS, editDistance: editDistance, parse: parse, describe: describe, suggest: suggest, resolveFamilyKey: resolveFamilyKey, resolveFinish: resolveFinish, adjustWords: adjustWords, familyById: familyById, recipeById: recipeById, whoText: whoText, colorTextOf: colorTextOf, howTextOf: howTextOf, isBodyColor: isBodyColor, partWordOf: partWordOf, complete: complete, searchFinishes: searchFinishes, lookCmds: lookCmds };

    return PUBLIC;
});
