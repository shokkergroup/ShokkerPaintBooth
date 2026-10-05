/* ============================================================================
   SPB PRO DESIGN — the copilot's built-in design knowledge (SPB-AI 2026-09-30)
   What a good paint scheme is made of, as data + recipes that work on the car's NAMED PARTS (left side, hood, roof ...):
     ELEMENTS  = the building blocks of real liveries (base colour, lower band, pinstripe, twin stripes, centre stripe, bumpers, roof, hood ...), each a recipe that
                 turns {colour, finish} into ready-to-apply zone specs on named parts with exact bands (height = from the ROOF-LINE 0 down to the ROCKER 1)
     PRESETS   = well-proportioned compositions of those elements (retro lower band, classic twin stripes, two-tone, colour block, bookends, stealth)
     PALETTES  = era / brand-style / mood colour families (Pepsi-style, Gulf-style, 70s earth, 80s neon ...) with the roles base / a / b / c / trim
   The model consults this (design_recipes), builds with it (apply_scheme: placement is then guaranteed correct), and with NO AI key at all
   SpbProDesign.offlinePlan(text) still turns "retro red white and blue stripes" into a finished scheme.
   ES5 only.  window.SpbProDesign = { PALETTES, PRESETS, ELEMENTS, nameColour, parseColours, recipes, build, offlinePlan, summarise }
   ========================================================================== */
(function () {
    'use strict';
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9#]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    function hexRgb(h) { h = String(h || '').replace('#', ''); return [parseInt(h.substr(0, 2), 16) || 0, parseInt(h.substr(2, 2), 16) || 0, parseInt(h.substr(4, 2), 16) || 0]; }
    function isHex(s) { return /^#[0-9a-f]{6}$/i.test(String(s || '')); }
    function CAR() { return window.SpbProCar; }
    // MSR-FIX-B 2026-10-03: typos / text-speak ("gimme a matt blak car wit carbn fiber") are cleaned by the shared table in js/spb-ai-cards.js (SpbAICards.normalize, loaded first) before any parser reads the order
    function nz(t) { var C = window.SpbAICards; try { return (C && C.normalize) ? C.normalize(t) : t; } catch (e) { return t; } }

    // ------------------------------------------------------------------ colours
    var COLOURS = {
        'white': '#f4f4f1', 'off white': '#ece8dc', 'cream': '#f1e6c8', 'ivory': '#f2ead3', 'black': '#111113', 'charcoal': '#34363b', 'dark grey': '#45484d', 'grey': '#8a8d92', 'gray': '#8a8d92', 'light grey': '#c4c7cb', 'silver': '#c3c7cc', 'gunmetal': '#4a4f57',
        'red': '#c8102e', 'crimson': '#a3123a', 'maroon': '#6d0f1f', 'burgundy': '#6d0f1f', 'scarlet': '#e0251b', 'orange': '#f26b21', 'burnt orange': '#c55a11', 'amber': '#ffa000', 'gold': '#d7a72b', 'yellow': '#ffd200', 'lemon': '#fff04a', 'lime': '#9bd52b', 'lime green': '#9bd52b', 'neon green': '#39ff14',
        'green': '#1f8a3b', 'forest green': '#14532d', 'dark green': '#14532d', 'olive': '#6b7a2a', 'teal': '#0f9aa0', 'turquoise': '#10b5b0', 'cyan': '#00c2e0', 'aqua': '#3fd6d0', 'sky blue': '#3aa0e0', 'baby blue': '#8ec6ee', 'powder blue': '#6fb7e9', 'light blue': '#7cbcec',
        'blue': '#1450b4', 'royal blue': '#0b3fa8', 'navy': '#0b2350', 'pepsi blue': '#0b2f8f', 'cobalt': '#0047ab', 'purple': '#6a1b9a', 'violet': '#7a3fc4', 'lavender': '#b79ae0', 'magenta': '#d6247d', 'hot pink': '#ff2f92', 'pink': '#ff7eb6', 'rose': '#e8587f',
        'brown': '#6b3a1e', 'tan': '#c9a57a', 'bronze': '#9b6a2f', 'copper': '#b4602c', 'chocolate': '#43260f',
        'mint': '#98e0b3', 'mint green': '#98e0b3', 'seafoam': '#7fd6b8', 'peach': '#ffb38a', 'coral': '#ff6f61', 'salmon': '#fa8072', 'beige': '#d9c9a8', 'khaki': '#bdb36b', 'mustard': '#d4a017', 'indigo': '#3f2a8c', 'sapphire': '#0f3b9c', 'emerald': '#0f9d58', 'ruby': '#9b111e',
        'platinum': '#d5d8dc', 'champagne': '#e9d8b4', 'sand': '#d8c08a', 'rust': '#a4451f', 'plum': '#6a2c5c', 'wine': '#5e1224', 'lilac': '#c8a2c8', 'peacock': '#00798c', 'jade': '#00a86b', 'electric blue': '#0a84ff', 'neon pink': '#ff2fd0', 'neon blue': '#1f51ff',
        'neon orange': '#ff6a00', 'neon yellow': '#e6ff00', 'midnight blue': '#101a4a', 'steel blue': '#4682b4', 'army green': '#4b5320', 'sage': '#9caf88', 'baby pink': '#f4b6c2', 'light pink': '#f4b6c2', 'dark blue': '#0b2350', 'light green': '#8fd18f', 'dark red': '#7a0f1f', 'dark purple': '#3b1a5a',
        // MSR-FIX-B 2026-10-03 (mad scientist run): painter / racing colour names
        'midnight purple': '#2e1a47', 'rose gold': '#b76e79', 'toxic green': '#5fd21e', 'bubblegum pink': '#ff7fbf', 'bubblegum': '#ff7fbf', 'gunmetal grey': '#4a4f57', 'nardo grey': '#7d7f7d', 'chalk grey': '#c9c7bd', 'grabber blue': '#1f6fc5', 'olive drab': '#6b6b3a'
    };
    var NAMEABLE = ['white', 'off white', 'cream', 'black', 'charcoal', 'grey', 'light grey', 'silver', 'red', 'crimson', 'maroon', 'orange', 'burnt orange', 'amber', 'gold', 'yellow', 'lime', 'green', 'forest green', 'olive', 'teal', 'turquoise', 'cyan', 'sky blue', 'powder blue', 'blue', 'royal blue', 'navy', 'purple', 'violet', 'lavender', 'magenta', 'hot pink', 'pink', 'brown', 'tan', 'bronze', 'copper', 'mint green', 'coral', 'peach', 'mustard', 'indigo', 'emerald', 'ruby', 'sand', 'rust', 'plum', 'wine', 'jade', 'electric blue', 'neon pink', 'neon orange', 'neon green', 'neon yellow', 'midnight blue', 'beige', 'platinum', 'champagne', 'lilac'];
    // MCPSCEN 2026-10-05 (MCP Bookends scheme: #ef233c was announced as a "Magenta front bumper"; #e63946, the classic racing red, too): the luminance-weighted RGB distance
    // lets green dominate, so a bright red sat closer to magenta than to the darker "red" entry. A saturated colour now picks among the names within 18 degrees of its hue
    // first (checked on 44 common livery colours: only clearer names changed - reds -> red, #1d3557 navy, #06d6a0 turquoise).
    function hsvOf(c) { var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0; if (d) { h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h *= 60; if (h < 0) h += 360; } return [h, mx ? d / mx : 0, mx]; }
    function nameColour(hex) {
        var c = hexRgb(hex), hc = hsvOf(c), best = 'grey', bd = 1e9, pool = NAMEABLE.filter(function (n) { return COLOURS[n]; });
        if (hc[1] < 0.12) { var greys = pool.filter(function (n) { return hsvOf(hexRgb(COLOURS[n]))[1] < 0.15; }); if (greys.length) pool = greys; }          /* MCPSCEN 2026-10-05: #5a5a5a was named olive */
        if (hc[1] > 0.4 && hc[2] > 0.3) { var near = pool.filter(function (n) { var ht = hsvOf(hexRgb(COLOURS[n])), dh = Math.abs(hc[0] - ht[0]); if (dh > 180) dh = 360 - dh; return ht[1] > 0.3 && ht[2] > 0.2 && dh <= 18; }); if (near.length) pool = near; }
        // MCPSCEN 2026-10-05 (G6 scheme: base #9fd3f0, a light sky blue, was announced as "Mint green"; #ffd1dc pastel pink as "champagne"): pastels keep their hue family too.
        else if (hc[1] > 0.15 && hc[2] > 0.7) { var nearP = pool.filter(function (n) { var ht = hsvOf(hexRgb(COLOURS[n])), dh = Math.abs(hc[0] - ht[0]); if (dh > 180) dh = 360 - dh; return ht[1] > 0.12 && dh <= 25; }); if (nearP.length) pool = nearP; }
        pool.forEach(function (n) { var t = hexRgb(COLOURS[n]), dr = c[0] - t[0], dg = c[1] - t[1], db = c[2] - t[2], d = dr * dr * 0.3 + dg * dg * 0.59 + db * db * 0.11; if (d < bd) { bd = d; best = n; } });
        return best;
    }
    // colours mentioned in a sentence, in order of appearance: [{name, hex, at}]
    function parseColours(text) {
        var t = ' ' + norm(text) + ' ', hits = [], taken = [];
        Object.keys(COLOURS).sort(function (a, b) { return b.length - a.length; }).forEach(function (n) {
            var re = new RegExp('(^| )' + n + '( |$)', 'g'), m;
            while ((m = re.exec(t))) {
                var st = m.index + (m[1] ? 1 : 0), en = st + n.length; re.lastIndex = en - 1;
                var pre = t.slice(Math.max(0, st - 40), st), NGC = '\\b(?:no|not|without|except|instead of|nothing|aint|never)\\s*(?:any |the )?';      // MSR-FIX-B: negated lists
                if (new RegExp(NGC + '(?:(?:[a-z]+ ){1,3}(?:or |nor ))?$').test(pre) || (new RegExp(NGC + '(?:[a-z]+ ){1,2}$').test(pre) && /^ (?:or|nor) /.test(t.slice(en)))) continue;
                if (taken.some(function (r) { return st < r[1] && en > r[0]; })) continue;   // inside a longer colour name already matched
                taken.push([st, en]); hits.push({ name: n, hex: COLOURS[n], at: st });
            }
        });
        hits.sort(function (a, b) { return a.at - b.at; });
        var seen = {}, out = []; hits.forEach(function (h) { if (!seen[h.name]) { seen[h.name] = 1; out.push(h); } });
        return out;
    }
    function rgbDist(h1, h2) { var a = hexRgb(h1), b = hexRgb(h2), dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2]; return Math.sqrt(dr * dr * 0.3 + dg * dg * 0.59 + db * db * 0.11); }
    // stripes in the body colour are invisible: if an accent is too close to the body, take the first other accent that stands out
    function ensureContrast(p) {
        var pool = [p.a, p.b, p.c, p.trim, '#f4f4f1', '#111113'];
        ['a', 'b'].forEach(function (k) {
            if (rgbDist(p[k], p.base) >= 30) return;
            for (var i = 0; i < pool.length; i++) { if (rgbDist(pool[i], p.base) >= 70 && (k === 'a' || rgbDist(pool[i], p.a) >= 40)) { p[k] = pool[i]; return; } }
        });
        return p;
    }

    // ------------------------------------------------------------------ palettes: era / style / mood families   (roles: base = body colour, a = main accent, b = second accent, c = third, trim = pinstripe / trim colour)
    var PALETTES = [
        { id: 'pepsi-80s', names: ['pepsi', 'pepsi challenge', 'cola challenge', 'red white and blue', 'red white blue', 'patriotic', 'americana', 'usa', 'fourth of july', '4th of july', 'stars and stripes', 'old glory'], era: '1970s-1980s', about: 'white car, deep blue and bright red; the classic American cola / patriotic livery', base: '#f4f4f1', a: '#0b2f8f', b: '#c8102e', c: '#f4f4f1', trim: '#c8c8cc', presets: ['retro_lower_band', 'classic_stripes', 'two_tone'] },
        { id: 'cola-red', names: ['coke', 'coca cola', 'cola red', 'santa'], era: 'classic', about: 'bright red with white trim, optional black', base: '#d0102a', a: '#f4f4f1', b: '#111113', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'bookends'] },
        { id: 'gulf-style', names: ['gulf', 'powder blue and orange', 'le mans blue orange', 'endurance classic'], era: '1960s-1970s', about: 'powder blue body with an orange centre stripe, the endurance-racing icon', base: '#6fb7e9', a: '#f26b21', b: '#0b2350', c: '#f4f4f1', trim: '#f26b21', presets: ['classic_stripes', 'retro_lower_band'] },
        { id: 'martini-style', names: ['martini', 'martini racing', 'italian stripes', 'blue and red stripes'], era: '1970s-1980s', about: 'white body, three thin stripes (navy, light blue, red) running nose to tail', base: '#f4f4f1', a: '#0b2350', b: '#3aa0e0', c: '#c8102e', trim: '#c8102e', presets: ['classic_stripes', 'retro_lower_band'] },
        { id: 'black-gold', names: ['black and gold', 'jps', 'john player', 'rothmans style', 'luxury', 'royal', 'champagne'], era: '1970s-1980s', about: 'gloss black body, gold pinstripes and trim: rich and formal', base: '#111113', a: '#d7a72b', b: '#f1e6c8', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'bookends', 'retro_lower_band'] },
        { id: 'sunoco-style', names: ['sunoco', 'blue and yellow', 'fuel blue', 'gas station'], era: '1960s-1990s', about: 'royal blue with yellow and red accents', base: '#0b3fa8', a: '#ffd200', b: '#c8102e', c: '#f4f4f1', trim: '#ffd200', presets: ['retro_lower_band', 'classic_stripes'] },
        { id: '70s-earth', names: ['70s', 'seventies', '1970s', 'earth tones', 'harvest', 'disco era', 'brown orange'], era: '1970s', about: 'warm orange, rust brown, mustard and cream stripes', base: '#f1e6c8', a: '#f26b21', b: '#6b3a1e', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band'] },
        { id: '80s-neon', names: ['80s', 'eighties', '1980s', 'neon', 'synthwave', 'outrun', 'miami', 'vaporwave', 'retrowave'], era: '1980s', about: 'hot pink and cyan on black or deep purple, sharp geometric blocks', base: '#15102a', a: '#ff2f92', b: '#00c2e0', c: '#6a1b9a', trim: '#f4f4f1', presets: ['colour_block', 'classic_stripes', 'retro_lower_band'] },
        { id: '90s-teal', names: ['90s', 'nineties', '1990s', 'teal and purple', 'arcade'], era: '1990s', about: 'teal, purple and magenta splashes on white or black', base: '#f4f4f1', a: '#0f9aa0', b: '#6a1b9a', c: '#d6247d', trim: '#111113', presets: ['colour_block', 'two_tone'] },
        { id: 'stealth', names: ['stealth', 'blackout', 'murdered out', 'all black', 'night mode'], era: 'modern', about: 'matte black and charcoal with one quiet accent', base: '#111113', a: '#34363b', b: '#45484d', c: '#c8102e', trim: '#c8102e', presets: ['stealth', 'bookends'] },
        { id: 'fire', names: ['fire', 'flame', 'lava', 'inferno', 'hot rod', 'magma', 'ember'], era: 'any', about: 'black into red, orange and yellow', base: '#111113', a: '#c8102e', b: '#f26b21', c: '#ffd200', trim: '#ffd200', presets: ['colour_block', 'classic_stripes'] },
        { id: 'ice', names: ['ice', 'arctic', 'frost', 'glacier', 'polar', 'winter'], era: 'any', about: 'white, pale blue and deep navy', base: '#f4f4f1', a: '#3aa0e0', b: '#0b2350', c: '#8ec6ee', trim: '#c3c7cc', presets: ['retro_lower_band', 'two_tone'] },
        { id: 'forest', names: ['forest', 'woodland', 'camo green', 'military', 'army', 'hunter', 'jungle'], era: 'any', about: 'olive and forest green with tan and black', base: '#6b7a2a', a: '#14532d', b: '#c9a57a', c: '#111113', trim: '#c9a57a', presets: ['colour_block', 'two_tone'] },
        { id: 'halloween', names: ['halloween', 'spooky', 'pumpkin', 'trick or treat'], era: 'any', about: 'orange and black with a purple accent', base: '#111113', a: '#f26b21', b: '#6a1b9a', c: '#f26b21', trim: '#f26b21', presets: ['colour_block', 'classic_stripes'] },
        { id: 'christmas', names: ['christmas', 'xmas', 'holiday', 'festive'], era: 'any', about: 'red and green on white', base: '#f4f4f1', a: '#c8102e', b: '#1f8a3b', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band'] },
        { id: 'sunset', names: ['sunset', 'sunrise', 'tropical', 'beach', 'summer'], era: 'any', about: 'orange into pink and purple', base: '#ffa000', a: '#ff2f92', b: '#6a1b9a', c: '#f26b21', trim: '#f4f4f1', presets: ['colour_block', 'two_tone'] },
        { id: 'clean-white', names: ['clean', 'minimal', 'minimalist', 'simple', 'sponsor friendly', 'plain'], era: 'modern', about: 'white body, one strong colour used sparingly', base: '#f4f4f1', a: '#c8102e', b: '#111113', c: '#c3c7cc', trim: '#111113', presets: ['retro_lower_band', 'bookends'] },
        { id: 'mexico', names: ['mexico', 'mexican', 'viva mexico', 'mexican flag', 'italy', 'italian flag', 'italian'], era: 'any', about: 'green, white and red: the tricolour', base: '#f4f4f1', a: '#1f8a3b', b: '#c8102e', c: '#f4f4f1', trim: '#c8c8cc', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'germany', names: ['germany', 'german', 'german flag', 'deutschland'], era: 'any', about: 'black, red and gold', base: '#111113', a: '#c8102e', b: '#ffd200', c: '#c8102e', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'france', names: ['france', 'french', 'french flag', 'tricolore', 'bleu blanc rouge'], era: 'any', about: 'blue, white and red', base: '#f4f4f1', a: '#0b3fa8', b: '#c8102e', c: '#f4f4f1', trim: '#c3c7cc', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'brazil', names: ['brazil', 'brazilian', 'brasil'], era: 'any', about: 'green, yellow and blue', base: '#1f8a3b', a: '#ffd200', b: '#0b3fa8', c: '#f4f4f1', trim: '#ffd200', presets: ['retro_lower_band', 'classic_stripes', 'colour_block'] },
        { id: 'union-jack', names: ['union jack', 'uk', 'british', 'britain', 'england', 'english', 'great britain'], era: 'any', about: 'navy, red and white', base: '#0b2350', a: '#c8102e', b: '#f4f4f1', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'canada', names: ['canada', 'canadian', 'maple leaf'], era: 'any', about: 'red and white', base: '#c8102e', a: '#f4f4f1', b: '#111113', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'japan', names: ['japan', 'japanese', 'rising sun', 'tokyo', 'jdm'], era: 'any', about: 'white with red: clean and sharp', base: '#f4f4f1', a: '#c8102e', b: '#111113', c: '#c8102e', trim: '#c3c7cc', presets: ['retro_lower_band', 'two_tone', 'bookends'] },
        { id: 'ireland', names: ['ireland', 'irish', 'st patricks', 'st patrick', 'shamrock'], era: 'any', about: 'green, white and orange', base: '#1f8a3b', a: '#f4f4f1', b: '#f26b21', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'sweden', names: ['sweden', 'swedish', 'ukraine', 'ukrainian'], era: 'any', about: 'blue and yellow', base: '#0b3fa8', a: '#ffd200', b: '#f4f4f1', c: '#ffd200', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'spain', names: ['spain', 'spanish', 'espana', 'matador'], era: 'any', about: 'red and gold', base: '#c8102e', a: '#ffd200', b: '#6d0f1f', c: '#ffd200', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'netherlands', names: ['netherlands', 'dutch', 'holland', 'oranje'], era: 'any', about: 'orange, white and blue', base: '#f26b21', a: '#f4f4f1', b: '#0b3fa8', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'australia', names: ['australia', 'australian', 'aussie', 'v8 supercars'], era: 'any', about: 'green and gold', base: '#14532d', a: '#ffd200', b: '#f4f4f1', c: '#ffd200', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'argentina', names: ['argentina', 'argentine', 'albiceleste'], era: 'any', about: 'sky blue and white', base: '#8ec6ee', a: '#f4f4f1', b: '#ffd200', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'jamaica', names: ['jamaica', 'jamaican', 'rasta', 'reggae'], era: 'any', about: 'green, gold and black', base: '#111113', a: '#1f8a3b', b: '#ffd200', c: '#1f8a3b', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'dodgers', names: ['dodgers', 'dodger blue', 'los angeles blue', 'cubs', 'chicago blue'], era: 'any', about: 'royal blue and white with a touch of red', base: '#0b3fa8', a: '#f4f4f1', b: '#c8102e', c: '#f4f4f1', trim: '#f4f4f1', presets: ['retro_lower_band', 'classic_stripes', 'two_tone'] },
        { id: 'lakers', names: ['lakers', 'purple and gold', 'vikings', 'minnesota', 'la gold'], era: 'any', about: 'purple and gold', base: '#4b1d8f', a: '#ffc72c', b: '#f4f4f1', c: '#ffc72c', trim: '#ffc72c', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'packers', names: ['packers', 'green and gold', 'green bay', 'oregon', 'ducks'], era: 'any', about: 'dark green and gold', base: '#14532d', a: '#ffc72c', b: '#f4f4f1', c: '#ffc72c', trim: '#ffc72c', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'cowboys', names: ['cowboys', 'dallas', 'navy and silver', 'texas'], era: 'any', about: 'navy and silver', base: '#0b2350', a: '#c3c7cc', b: '#f4f4f1', c: '#c3c7cc', trim: '#c3c7cc', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'niners', names: ['49ers', 'niners', 'san francisco', 'chiefs', 'kansas city', 'red and gold'], era: 'any', about: 'scarlet and gold', base: '#c8102e', a: '#d7a72b', b: '#f4f4f1', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'steelers', names: ['steelers', 'pittsburgh', 'bruins', 'boston gold', 'black and yellow', 'bumblebee'], era: 'any', about: 'black and yellow', base: '#111113', a: '#ffd200', b: '#f4f4f1', c: '#ffd200', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'raiders', names: ['raiders', 'silver and black', 'las vegas', 'oakland', 'spurs'], era: 'any', about: 'black and silver', base: '#111113', a: '#c3c7cc', b: '#f4f4f1', c: '#c3c7cc', trim: '#c3c7cc', presets: ['classic_stripes', 'retro_lower_band', 'bookends'] },
        { id: 'patriots', names: ['patriots', 'new england', 'navy red and silver', 'yankees', 'new york'], era: 'any', about: 'navy with red and silver', base: '#0b2350', a: '#c8102e', b: '#c3c7cc', c: '#f4f4f1', trim: '#c3c7cc', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'seahawks', names: ['seahawks', 'seattle', 'navy and green', 'action green'], era: 'any', about: 'navy with action green', base: '#0b2350', a: '#69be28', b: '#c3c7cc', c: '#69be28', trim: '#69be28', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'eagles', names: ['eagles', 'philadelphia', 'midnight green', 'jets', 'green and silver'], era: 'any', about: 'midnight green and silver', base: '#0b4d3f', a: '#c3c7cc', b: '#111113', c: '#c3c7cc', trim: '#c3c7cc', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'broncos', names: ['broncos', 'denver', 'orange and navy', 'bears', 'chicago'], era: 'any', about: 'orange and navy', base: '#f26b21', a: '#0b2350', b: '#f4f4f1', c: '#0b2350', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'dolphins', names: ['dolphins', 'miami aqua', 'aqua and orange', 'teal and orange'], era: 'any', about: 'aqua with orange', base: '#0f9aa0', a: '#f26b21', b: '#f4f4f1', c: '#f26b21', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'rothmans', names: ['rothmans', 'rothmans blue', 'navy white and gold', 'williams'], era: '1980s-1990s', about: 'white with navy and gold bands', base: '#f4f4f1', a: '#0b2350', b: '#d7a72b', c: '#0b2350', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band'] },
        { id: 'marlboro', names: ['marlboro', 'red and white', 'red top white bottom', 'ferrari red and white'], era: '1980s-1990s', about: 'red and white blocks, the big-tobacco look', base: '#c8102e', a: '#f4f4f1', b: '#111113', c: '#f4f4f1', trim: '#f4f4f1', presets: ['retro_lower_band', 'colour_block', 'two_tone'] },
        { id: 'castrol', names: ['castrol', 'green white and red', 'motor oil'], era: '1990s', about: 'green and white with a red accent', base: '#f4f4f1', a: '#1f8a3b', b: '#c8102e', c: '#1f8a3b', trim: '#c8102e', presets: ['classic_stripes', 'retro_lower_band'] },
        { id: 'red-bull', names: ['red bull', 'redbull', 'energy drink', 'navy and red', 'sebastian'], era: 'modern', about: 'matte navy with red and yellow', base: '#0b2350', a: '#c8102e', b: '#ffd200', c: '#c8102e', trim: '#ffd200', presets: ['classic_stripes', 'colour_block', 'retro_lower_band'] },
        { id: 'monster', names: ['monster', 'monster energy', 'toxic green', 'neon green and black', 'radioactive', 'hazard'], era: 'modern', about: 'black with neon green', base: '#111113', a: '#39ff14', b: '#34363b', c: '#39ff14', trim: '#39ff14', presets: ['classic_stripes', 'colour_block', 'stealth'] },
        { id: 'ferrari', names: ['ferrari', 'rosso corsa', 'italian red', 'prancing', 'scuderia'], era: 'any', about: 'rosso red with a yellow shield accent', base: '#c8102e', a: '#ffd200', b: '#111113', c: '#f4f4f1', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'bookends'] },
        { id: 'papaya', names: ['mclaren', 'papaya', 'papaya orange', 'orange and black', 'sunset orange'], era: 'modern', about: 'papaya orange with black', base: '#f26b21', a: '#111113', b: '#f4f4f1', c: '#111113', trim: '#111113', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'brg', names: ['british racing green', 'brg', 'lotus', 'racing green', 'classic green', 'jaguar', 'aston'], era: 'classic', about: 'deep green with a gold stripe', base: '#14532d', a: '#d7a72b', b: '#f4f4f1', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'deere', names: ['john deere', 'tractor', 'farm', 'green and yellow', 'agricultural'], era: 'any', about: 'green with yellow', base: '#1f8a3b', a: '#ffd200', b: '#f4f4f1', c: '#ffd200', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'ups-brown', names: ['ups', 'brown and gold', 'delivery', 'chocolate', 'mocha'], era: 'any', about: 'brown with gold', base: '#43260f', a: '#d7a72b', b: '#f1e6c8', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'fedex', names: ['fedex', 'purple and orange', 'express'], era: 'any', about: 'purple and orange', base: '#4b1d8f', a: '#f26b21', b: '#f4f4f1', c: '#f26b21', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'mtn-dew', names: ['mountain dew', 'dew', 'lime and red', 'citrus', 'lime and black'], era: 'any', about: 'lime green with red and black', base: '#9bd52b', a: '#c8102e', b: '#111113', c: '#c8102e', trim: '#111113', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'valvoline', names: ['valvoline', 'mobil', 'blue white and red', 'oil can', 'motor sport blue'], era: 'any', about: 'royal blue with white and red', base: '#0b3fa8', a: '#f4f4f1', b: '#c8102e', c: '#f4f4f1', trim: '#c8102e', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'pennzoil', names: ['pennzoil', 'yellow and red', 'banana', 'gold rush', 'lemon'], era: 'any', about: 'bright yellow with red and black', base: '#ffd200', a: '#c8102e', b: '#111113', c: '#c8102e', trim: '#111113', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'police', names: ['police', 'cop', 'black and white', 'panda', 'zebra', 'tuxedo'], era: 'any', about: 'black and white', base: '#111113', a: '#f4f4f1', b: '#c8102e', c: '#f4f4f1', trim: '#f4f4f1', presets: ['two_tone', 'classic_stripes', 'retro_lower_band'] },
        { id: 'pastel', names: ['pastel', 'soft', 'baby', 'cotton candy', 'dreamy', 'macaron', 'cute'], era: 'modern', about: 'soft pink, mint and lavender', base: '#f4e1ea', a: '#a8e6cf', b: '#b79ae0', c: '#8ec6ee', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'bubblegum', names: ['bubblegum', 'bubble gum', 'pink and blue', 'barbie', 'candy pink'], era: 'any', about: 'hot pink with baby blue', base: '#ff7eb6', a: '#8ec6ee', b: '#f4f4f1', c: '#ff2f92', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'ocean', names: ['ocean', 'sea', 'deep sea', 'wave', 'waves', 'marine', 'nautical', 'navy and aqua', 'lagoon'], era: 'any', about: 'deep navy into teal and aqua', base: '#0b2350', a: '#0f9aa0', b: '#3fd6d0', c: '#f4f4f1', trim: '#3fd6d0', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'desert', names: ['desert', 'sand', 'sahara', 'dune', 'terracotta', 'southwest', 'canyon', 'rust'], era: 'any', about: 'sand, terracotta and cream', base: '#c9a57a', a: '#b4602c', b: '#f1e6c8', c: '#6b3a1e', trim: '#f1e6c8', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'galaxy', names: ['galaxy', 'space', 'cosmic', 'nebula', 'universe', 'night sky', 'midnight', 'starry'], era: 'any', about: 'deep purple and navy with pink and cyan light', base: '#15102a', a: '#6a1b9a', b: '#00c2e0', c: '#ff2f92', trim: '#f4f4f1', presets: ['classic_stripes', 'colour_block', 'stealth'] },
        { id: 'toxic', names: ['toxic', 'poison', 'venom', 'acid', 'slime', 'zombie', 'radiation'], era: 'any', about: 'black with acid green and purple', base: '#111113', a: '#9bd52b', b: '#6a1b9a', c: '#39ff14', trim: '#9bd52b', presets: ['classic_stripes', 'colour_block', 'retro_lower_band'] },
        { id: 'rose-gold', names: ['rose gold', 'blush', 'champagne pink', 'copper rose', 'bridal'], era: 'modern', about: 'warm rose gold with white and charcoal', base: '#f4e1ea', a: '#d9a299', b: '#34363b', c: '#d7a72b', trim: '#d9a299', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'patina', names: ['patina', 'oxidised', 'oxidized', 'verdigris', 'copper green', 'weathered', 'steampunk', 'antique'], era: 'any', about: 'teal verdigris with copper', base: '#0f9aa0', a: '#b4602c', b: '#f1e6c8', c: '#6b3a1e', trim: '#b4602c', presets: ['classic_stripes', 'retro_lower_band', 'colour_block'] },
        { id: 'carbon', names: ['gunmetal', 'graphite', 'anthracite', 'tech'], era: 'modern', about: 'gunmetal and charcoal with a red accent', base: '#34363b', a: '#111113', b: '#c8102e', c: '#8a8d92', trim: '#c8102e', presets: ['stealth', 'bookends', 'classic_stripes'] },
        { id: 'camo-tan', names: ['tan', 'khaki', 'coyote', 'sand camo', 'safari', 'savannah'], era: 'any', about: 'tan and olive with black', base: '#c9a57a', a: '#6b7a2a', b: '#111113', c: '#43260f', trim: '#111113', presets: ['colour_block', 'two_tone', 'retro_lower_band'] },
        { id: 'hot-rod', names: ['hot rod', 'rat rod', 'kustom', 'kustom kulture', 'cherry red', 'lowrider', 'lowrider candy', 'custom'], era: 'classic', about: 'deep candy red with cream and flame-yellow', base: '#a3123a', a: '#f1e6c8', b: '#ffd200', c: '#f1e6c8', trim: '#ffd200', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'mint-choc', names: ['mint', 'mint and chocolate', 'retro diner', 'diner', '50s', 'fifties', 'sock hop'], era: '1950s', about: 'mint and cream with cherry red', base: '#a8e6cf', a: '#f1e6c8', b: '#c8102e', c: '#f4f4f1', trim: '#c8102e', presets: ['retro_lower_band', 'two_tone', 'classic_stripes'] },
        { id: 'gold-white', names: ['gold and white', 'white and gold', 'ivory and gold', 'pearl and gold', 'bridal gold', 'versace'], era: 'modern', about: 'white with gold', base: '#f4f4f1', a: '#d7a72b', b: '#f1e6c8', c: '#d7a72b', trim: '#d7a72b', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'silver-arrow', names: ['silver arrow', 'silver arrows', 'mercedes', 'ghost', 'chrome look', 'silver and black', 'metallic silver'], era: 'classic', about: 'polished silver with black and a teal accent', base: '#c3c7cc', a: '#111113', b: '#0f9aa0', c: '#8a8d92', trim: '#111113', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'flag-usa', names: ['old school usa', 'american flag', 'merica', 'murica', 'eagle', 'freedom'], era: 'any', about: 'navy, white and red', base: '#0b2350', a: '#c8102e', b: '#f4f4f1', c: '#f4f4f1', trim: '#f4f4f1', presets: ['classic_stripes', 'retro_lower_band', 'two_tone'] },
        { id: 'taxi-bus', names: ['taxi', 'taxi cab', 'cab', 'school bus', 'school bus yellow', 'yellow cab', 'construction', 'caution'], era: 'any', about: 'bright yellow with a black stripe', base: '#ffd200', a: '#111113', b: '#111113', c: '#f4f4f1', trim: '#111113', presets: ['retro_lower_band', 'two_tone', 'classic_stripes'] },
        { id: 'aggressive', names: ['aggressive', 'angry', 'menacing', 'mean', 'predator'], era: 'modern', about: 'black with red, sharp contrast', base: '#111113', a: '#c8102e', b: '#34363b', c: '#f4f4f1', trim: '#c8102e', presets: ['colour_block', 'stealth'] }
    ];

    // ------------------------------------------------------------------ elements: recipes on named parts
    // ctx = { paint: 'base::gloss', trim: 'base::chrome' }.   o = { colour, colour2, from, to, at, width, finish }.  Each returns { zones: [spec], skipped: [reason] }
    var SIDES = ['left side', 'right side'];
    function known(part) { try { if (CAR() && CAR().missing([part]).length === 0) return true; return part === 'trunk' && !!CAR() && CAR().missing(['bed']).length === 0; } catch (e) { return false; } }
    // trucks have a bed where cars have a trunk
    function rp(part) { try { return (part === 'trunk' && CAR() && CAR().missing(['trunk']).length && !CAR().missing(['bed']).length) ? 'bed' : part; } catch (e) { return part; } }
    function sidesKnown() { return known('left side') && known('right side'); }
    function sideOk(reasons) {
        if (!sidesKnown()) { reasons.push('the left / right sides are not known on this car'); return false; }
        try { var a = CAR().findIsland('left side'), b = CAR().findIsland('right side'); if (!(a && a.up && b && b.up)) { reasons.push('which edge of the sides is the roof-line is not known'); return false; } } catch (e) { return false; }
        return true;
    }
    function zone(name, region, colour, finish) { return { name: name, finish: finish, color: colour, region: region }; }
    function cn(c) { return nameColour(c); }
    function capital(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
    function band(from, to) { return { axis: 'height', from: from, to: to }; }
    // ---- drawn graphics (js/spb-pro-graphics.js): one element per kind; the colour list is cycled over the strokes, one zone per colour
    function graphicEl(kind, about) {
        return { about: about, params: 'colour, colour2 (optional second/third via colours:[...]), part (default both sides), + the graphic params (see design_recipes / SpbGraphics.KINDS)',
            build: function (o, ctx) {
                var G = window.SpbGraphics; if (!G) return { zones: [], skipped: ['the graphics library is not loaded'] };
                var item = {}; Object.keys(o).forEach(function (k) { if (k !== 'id' && k !== 'colour' && k !== 'colour2' && k !== 'finish') item[k] = o[k]; });
                item.kind = kind; var cols = []; [o.colour, o.colour2].forEach(function (c) { if (c && cols.indexOf(c) === -1) cols.push(c); }); (o.colours || []).forEach(function (c) { var h = isHex(c) ? c : COLOURS[norm(c)]; if (h && cols.indexOf(h) === -1) cols.push(h); }); item.colours = cols;
                var err = G.check(item); if (err) return { zones: [], skipped: [err] };
                var zs = cols.map(function (c) { return zone(capital(cn(c)) + ' ' + kind.replace('_', ' '), { graphic: { item: item, only: c } }, c, o.finish || ctx.paint); });
                return { zones: zs, skipped: [] };
            } };
    }
    var ELEMENTS = {
        base: { about: 'the main body colour on the body paint layers (everything else in the scheme sits on top of it; add it FIRST)', params: 'colour',
            build: function (o, ctx) { return { zones: [zone(capital(cn(o.colour)) + ' body base', { everything: true, paintable: true }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        lower_band: { about: 'a colour band along the lower body of both sides, from the belt down to the rocker (the classic way to add a second colour); from / to = 0..1 down from the roof-line, default 0.68-1.0', params: 'colour, from, to',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; var f = o.from != null ? o.from : 0.68, t = o.to != null ? o.to : 1; if (ctx.scale !== 1) f = Math.max(0.3, 1 - (1 - f) * ctx.scale); return { zones: [zone(capital(cn(o.colour)) + ' lower band', { part: SIDES, band: band(f, t) }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        upper_band: { about: 'a colour band along the UPPER body of both sides (roof-line side), default 0-0.22', params: 'colour, from, to',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; return { zones: [zone(capital(cn(o.colour)) + ' upper band', { part: SIDES, band: band(o.from != null ? o.from : 0, o.to != null ? o.to : 0.22) }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        pinstripe: { about: 'a thin line along both sides (chrome, gold, white or a colour); at = how far down from the roof-line (0..1, default 0.64), width default 0.03', params: 'colour, at, width',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; var a = o.at != null ? o.at : 0.64, w = (o.width != null ? o.width : 0.03) * ctx.scale; return { zones: [zone(capital(cn(o.colour)) + ' pinstripe', { part: SIDES, band: band(a, a + w) }, o.colour, o.finish || ctx.trim)], skipped: [] }; } },
        belt_stripe: { about: 'a stripe just under the roof-line of both sides (the beltline), default 0.12-0.22', params: 'colour, from, to',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; var bf = o.from != null ? o.from : 0.12, bt = o.to != null ? o.to : 0.22; bt = bf + (bt - bf) * ctx.scale; return { zones: [zone(capital(cn(o.colour)) + ' beltline stripe', { part: SIDES, band: band(bf, bt) }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        twin_stripes: { about: 'two parallel stripes running nose to tail along both sides (colour, colour2), centred at 0.5 of the height, each width 0.07 with a 0.03 gap: the 1970s-80s classic', params: 'colour, colour2, at, width',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; var w = (o.width != null ? o.width : 0.07) * ctx.scale, g = 0.03, at = o.at != null ? o.at : 0.5, c2 = o.colour2 || o.colour;
                var a0 = at - w - g / 2, b0 = at + g / 2; return { zones: [zone(capital(cn(o.colour)) + ' stripe (upper)', { part: SIDES, band: band(a0, a0 + w) }, o.colour, o.finish || ctx.paint), zone(capital(cn(c2)) + ' stripe (lower)', { part: SIDES, band: band(b0, b0 + w) }, c2, o.finish || ctx.paint)], skipped: [] }; } },
        side_stripe: { about: 'one stripe of any position along both sides: from / to = 0..1 down from the roof-line', params: 'colour, from, to',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; if (o.from == null || o.to == null) return { zones: [], skipped: ['side_stripe needs from and to'] }; return { zones: [zone(capital(cn(o.colour)) + ' side stripe', { part: SIDES, band: band(o.from, o.to) }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        rear_quarter: { about: 'the rear quarter (rear 24% of both sides) in a colour: a sweep-back look', params: 'colour',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; try { var a = CAR().findIsland('left side'), b = CAR().findIsland('right side'); if (!(a.front && b.front)) return { zones: [], skipped: ['which end of the sides is the front is not known'] }; } catch (e) { return { zones: [], skipped: ['sides unknown'] }; }
                return { zones: [zone(capital(cn(o.colour)) + ' rear quarter', { part: SIDES, band: { axis: 'length', from: 0.76, to: 1 } }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        front_fender: { about: 'the front fender (front 22% of both sides) in a colour', params: 'colour',
            build: function (o, ctx) { var sk = []; if (!sideOk(sk)) return { zones: [], skipped: sk }; try { var a = CAR().findIsland('left side'), b = CAR().findIsland('right side'); if (!(a.front && b.front)) return { zones: [], skipped: ['which end of the sides is the front is not known'] }; } catch (e) { return { zones: [], skipped: ['sides unknown'] }; }
                return { zones: [zone(capital(cn(o.colour)) + ' front fender', { part: SIDES, band: { axis: 'length', from: 0, to: 0.22 } }, o.colour, o.finish || ctx.paint)], skipped: [] }; } },
        hood: { about: 'the whole hood in a colour', params: 'colour', build: function (o, ctx) { return part1('hood', 'hood', o, ctx); } },
        roof: { about: 'the whole roof in a colour', params: 'colour', build: function (o, ctx) { return part1('roof', 'roof', o, ctx); } },
        trunk: { about: 'the trunk / rear deck lid in a colour', params: 'colour', build: function (o, ctx) { return part1('trunk', 'trunk', o, ctx); } },
        spoiler: { about: 'the rear spoiler in a colour', params: 'colour', build: function (o, ctx) { return part1('spoiler', 'spoiler', o, ctx); } },
        bumpers: { about: 'front AND rear bumper in a colour (whichever the car has a known part for)', params: 'colour',
            build: function (o, ctx) { var z = [], sk = []; ['front bumper', 'rear bumper'].forEach(function (p) { if (known(p)) z.push(zone(capital(cn(o.colour)) + ' ' + p, { part: p }, o.colour, o.finish || ctx.paint)); else sk.push(p + ' is not known on this car'); }); return { zones: z, skipped: sk }; } },          // MCPSCEN 2026-10-05 (F150 bookends: only the front bumper was painted and the missing rear bumper was never mentioned): report each missing end
        centre_stripe: { about: 'a stripe down the middle of the hood, roof and trunk (width 0.14 of their width, default), colour, optional thin trim lines beside it with trim colour', params: 'colour, width, trim',
            build: function (o, ctx) { var z = [], sk = [], w = (o.width != null ? o.width : 0.14) * ctx.scale, c0 = 0.5 - w / 2, c1 = 0.5 + w / 2, parts = (o.only && o.only.length ? o.only : ['hood', 'roof', 'trunk']).filter(function (p) { return known(p); }).map(rp);
                if (!parts.length) return { zones: [], skipped: ['the hood / roof / trunk are not known on this car'] };
                z.push(zone(capital(cn(o.colour)) + ' centre stripe', { part: parts, band: band(c0, c1) }, o.colour, o.finish || ctx.paint));
                if (o.trim && isHex(o.trim)) z.push(zone(capital(cn(o.trim)) + ' centre trim lines', { part: parts, band: band(c0 - 0.035, c0) }, o.trim, ctx.trim), zone(capital(cn(o.trim)) + ' centre trim lines (2)', { part: parts, band: band(c1, c1 + 0.035) }, o.trim, ctx.trim));
                return { zones: z, skipped: sk }; } }
    };
    function part1(part, label, o, ctx) { if (!known(part)) return { zones: [], skipped: [part + ' is not known on this car'] }; return { zones: [zone(capital(cn(o.colour)) + ' ' + label, { part: rp(part) }, o.colour, o.finish || ctx.paint)], skipped: [] }; }

    // ------------------------------------------------------------------ presets (well-proportioned compositions; roles from the palette: base / a / b / c / trim)
    var PRESETS = {
        retro_lower_band: { name: 'Retro lower band', about: 'the classic: body colour on top, a bold colour band along the lower body with a thin trim line above it, matching bumpers and spoiler, a second accent on the beltline', steps: function (p) { return [['base', { colour: p.base }], ['lower_band', { colour: p.a }], ['pinstripe', { colour: p.trim, at: 0.64, width: 0.03 }], ['belt_stripe', { colour: p.b, from: 0.12, to: 0.2 }], ['bumpers', { colour: p.a }], ['spoiler', { colour: p.a }]]; } },
        classic_stripes: { name: 'Classic twin stripes', about: 'two parallel stripes nose to tail on the sides, continuing as a centre stripe over hood, roof and trunk (1970s-80s racing look)', steps: function (p) { return [['base', { colour: p.base }], ['twin_stripes', { colour: p.a, colour2: p.b, at: 0.5 }], ['centre_stripe', { colour: p.a, trim: p.b, width: 0.12 }], ['bumpers', { colour: p.a }]]; } },
        two_tone: { name: 'Two-tone', about: 'body colour above, a second colour from the belt down plus hood and bumpers: strong and simple', steps: function (p) { return [['base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.5, to: 1 }], ['pinstripe', { colour: p.trim, at: 0.47, width: 0.03 }], ['hood', { colour: p.a }], ['bumpers', { colour: p.a }]]; } },
        colour_block: { name: 'Colour block', about: 'big geometric blocks: hood, roof and rear quarters in different colours, bumpers in the accent', steps: function (p) { return [['base', { colour: p.base }], ['hood', { colour: p.a }], ['roof', { colour: p.b }], ['rear_quarter', { colour: p.a }], ['front_fender', { colour: p.b }], ['bumpers', { colour: p.c || p.a }], ['pinstripe', { colour: p.trim, at: 0.5, width: 0.025 }]]; } },
        bookends: { name: 'Bookends', about: 'body colour with contrasting front and rear ends: bumpers and spoiler in the accent, a thin rocker stripe', steps: function (p) { return [['base', { colour: p.base }], ['bumpers', { colour: p.a }], ['spoiler', { colour: p.a }], ['pinstripe', { colour: p.trim, at: 0.9, width: 0.03 }]]; } },
        solid: { name: 'Solid colour', about: 'one colour over the whole body (numbers, sponsors and logos stay): the base for graphics, stripes and finishes added after it', steps: function (p) { return [['base', { colour: p.base }]]; } },          // MCPSCEN 2026-10-05 (NextGen: the MCP model asked for preset "solid" with only a base colour and got a palette error)
        stealth: { name: 'Stealth', about: 'dark on dark: body, slightly different dark roof / hood / bumpers, one thin accent line', steps: function (p) { return [['base', { colour: p.base }], ['roof', { colour: p.a }], ['hood', { colour: p.a }], ['bumpers', { colour: p.b }], ['pinstripe', { colour: p.trim, at: 0.6, width: 0.025 }]]; } }
    };

    // ------------------------------------------------------------------ build + knowledge for the model
    function paletteById(id) { var r = null; PALETTES.forEach(function (p) { if (p.id === id) r = p; }); return r; }
    function findPalette(text) {
        var t = ' ' + norm(text) + ' ', best = null, bl = 0;
        PALETTES.forEach(function (p) { p.names.concat([p.id.replace(/-/g, ' ')]).forEach(function (n) { var nn = ' ' + norm(n) + ' '; if (t.indexOf(nn) !== -1 && nn.length > bl) { bl = nn.length; best = p; } }); });
        return best;
    }
    // elements: [{id, colour|role, colour2, from, to, at, width, trim, finish}], roles resolved against palette {base,a,b,c,trim}
    ['rings', 'speed_lines', 'strokes', 'stripes', 'waves', 'chevrons', 'checker', 'dots', 'rays', 'lightning'].forEach(function (k) {
        var about = { rings: 'GRAPHIC: concentric arcs ("sonic rings") with optional dashes and tails', speed_lines: 'GRAPHIC: tapered speed lines streaming along the car', strokes: 'GRAPHIC: an explicit list of tapered strokes (measured lines)', stripes: 'GRAPHIC: parallel stripes at any angle, optionally curved', waves: 'GRAPHIC: wavy flow bands', chevrons: 'GRAPHIC: repeating V / arrow shapes', checker: 'GRAPHIC: checkered flag field', dots: 'GRAPHIC: halftone dot field', rays: 'GRAPHIC: sunburst rays', lightning: 'GRAPHIC: lightning bolt' }[k];
        if (!ELEMENTS[k + '_graphic']) ELEMENTS[k + '_graphic'] = graphicEl(k, about);
    });
    function build(elements, palette, ctx) {
        ctx = ctx || {}; ctx.paint = ctx.paint || 'base::gloss'; ctx.trim = ctx.trim || 'base::chrome'; ctx.scale = ctx.scale || 1;
        var zones = [], skipped = [];
        (elements || []).forEach(function (e) {
            var el = ELEMENTS[e.id]; if (!el) { skipped.push('unknown element "' + e.id + '"'); return; }
            function res(c) { if (!c) return c; if (isHex(c)) return c; var n = norm(c); if (palette && palette[n]) return palette[n]; if (COLOURS[n]) return COLOURS[n]; return null; }
            var o = {}; Object.keys(e).forEach(function (k) { o[k] = e[k]; });
            o.colour = res(e.colour || e.role); o.colour2 = res(e.colour2); o.trim = res(e.trim);
            if (!o.colour) { skipped.push(e.id + ': needs a colour (a #hex, a colour name, or a palette role base / a / b / c / trim)'); return; }
            var r = el.build(o, ctx); r.zones.forEach(function (z) { zones.push(z); }); r.skipped.forEach(function (s) { skipped.push(e.id + ': ' + s); });
        });
        return { zones: zones, skipped: skipped };
    }
    function presetSteps(id, palette) { var p = PRESETS[id]; if (!p) return null; return p.steps(palette).map(function (s) { var o = { id: s[0] }; Object.keys(s[1]).forEach(function (k) { o[k] = s[1][k]; }); return o; }); }
    function recipes(query) {
        var t = norm(query), pal = findPalette(query), out = {
            how_to_use: 'Pick 1 preset (or compose elements yourself), a palette (base / a / b / c / trim colours) and finishes, then call apply_scheme ONCE: placement on the car\'s named parts is exact. Adjust colours to the buyer\'s words; never invent placement with boxes.',
            presets: Object.keys(PRESETS).map(function (k) { return { id: k, name: PRESETS[k].name, about: PRESETS[k].about }; }),
            elements: Object.keys(ELEMENTS).map(function (k) { return { id: k, about: ELEMENTS[k].about, params: ELEMENTS[k].params }; }),
            proportions: 'Stripe and band positions are fractions DOWN from the ROOF-LINE (0) to the ROCKER (1) of the side panels: beltline 0.10-0.25, door centre 0.35-0.65, lower body 0.68-1.0. Keep the middle of the side (0.3-0.65, where the number sits) calm: busy art there kills readability.',
            spec_looks: Object.keys(SPEC_LOOKS).map(function (k) { return { look: k, foundation_finish: SPEC_LOOKS[k].finish, about: SPEC_LOOKS[k].about }; }),
            spec_only_rule: 'For spec-only changes use the Foundation finish of the look with color "source": it changes the spec map and leaves the paint untouched (measured). Never base::chrome / base::metallic / base::candy for that: they repaint the car.',
            composition: ['one dominant colour (about 60%), one strong accent (about 30%), one trim colour (about 10%)', 'white or black as the quiet colour lets the accent colours sing', 'line the colour blocks up across the car: the band on the sides continues the colour of the bumpers, the centre stripe of the hood continues over the roof and trunk', 'flat (matte) paint with chrome trim lines is the modern retro look; gloss everywhere is the showroom look', 'never cover the numbers or the sponsor panels: the body paint layer only']
        };
        if (pal) out.palette_match = { id: pal.id, about: pal.about, era: pal.era, base: pal.base, a: pal.a, b: pal.b, c: pal.c, trim: pal.trim, suggested_presets: pal.presets };
        else out.palettes = PALETTES.map(function (p) { return { id: p.id, names: p.names.slice(0, 4), about: p.about, colours: { base: p.base, a: p.a, b: p.b, trim: p.trim } }; });
        return out;
    }

    // ------------------------------------------------------------------ spec looks: how a surface reflects, as spec_shift numbers (metal / rough / clearcoat, -127..127; clearcoat 16 = max gloss so NEGATIVE = glossier)
    var SPEC_LOOKS = {
        'mirror chrome': { words: ['mirror chrome', 'mirror', 'chrome'], finish: 'base::f_chrome', about: 'full metal, no roughness, glossy clearcoat: a mirror' },
        'satin chrome': { words: ['satin chrome', 'brushed chrome', 'soft chrome'], finish: 'base::f_satin_chrome', about: 'chrome with a soft satin sheen' },
        'dark chrome': { words: ['dark chrome', 'black chrome', 'smoked chrome'], finish: 'base::f_dark_chrome', about: 'smoked mirror metal' },
        'matte': { words: ['matte', 'matt', 'flat', 'flatter', 'duller', 'dead flat'], finish: 'base::f_soft_matte', about: 'no metal, rough, dull clearcoat' },
        'satin': { words: ['satin', 'eggshell', 'semi gloss'], finish: 'base::f_clear_satin', about: 'soft sheen between gloss and matte' },
        'gloss': { words: ['gloss', 'glossy', 'glossier', 'shiny', 'shinier', 'shine', 'wet look', 'wet paint', 'high gloss'], finish: 'base::f_soft_gloss', about: 'deep wet gloss' },
        'metallic': { words: ['metallic', 'metal flake', 'metalflake', 'polished metal'], finish: 'base::f_metallic', about: 'metallic paint: bright metal under clearcoat' },
        'matte metal': { words: ['matte metal', 'matte metallic'], finish: 'base::f_matte_metallic', about: 'metal with a flat finish' },
        'pearl': { words: ['pearl', 'pearlescent', 'pearly'], finish: 'base::f_pearl', about: 'pearl: soft metal under a deep clearcoat' },
        'candy': { words: ['candy'], finish: 'base::f_candy', about: 'candy: strong metal under deep clearcoat' },
        'brushed metal': { words: ['brushed', 'brushed metal', 'satin metal'], finish: 'base::f_brushed', about: 'metal with a brushed, rougher surface' },
        'frosted': { words: ['frosted', 'frozen', 'icy'], finish: 'base::f_frozen', about: 'frosted metal' }
    };
    var PART_WORDS = [['hood', /\b(hood|bonnet)\b/], ['roof', /\broof\b/], ['trunk', /\b(trunk|deck ?lid|rear deck)\b/], ['bed', /\b(truck bed|pickup bed|cargo bed|bed)\b/], ['front bumper', /\b(front bumper|nose|front end)\b/], ['rear bumper', /\b(rear bumper|rear end|tail)\b/], ['spoiler', /\b(spoiler|wing)\b/], ['left side', /\b(left|driver)('?s)? (side|door|flank)\b/], ['right side', /\b(right|passenger)('?s)? (side|door|flank)\b/]];
    // "make the hood mirror chrome in the spec only" -> zones that change ONLY the spec (colour "source")
    function offlineSpec(text) {
        text = nz(text);
        var t = ' ' + norm(text) + ' ', look = null, lw = 0;
        if (compoundPlan(text) || parseColours(text).length || /\b(overlays?|patterns?|weaves?|textures?|pinstripes?|stripes?|flames?|camo|marble|decals?|repaint|recolou?r)\b/i.test(t)) return null;      // WP16: incomplete spec-only phrases cannot absorb base colours or additional paint/pattern actions
        Object.keys(SPEC_LOOKS).forEach(function (k) { SPEC_LOOKS[k].words.forEach(function (w) { var ww = ' ' + norm(w) + ' '; if (t.indexOf(ww) !== -1 && ww.length > lw) { lw = ww.length; look = k; } }); });
        if (!look) return null;
        var specy = /\b(spec|only the shine|only the finish|keep the (paint|colou?rs?)|paint colou?rs?)\b/.test(t);
        if (!specy && (parseColours(text).length || findPalette(text) || /\b(liver(y|ies)|scheme|stripes?|bands?|retro|old school|throwback|theme|two tone)\b/.test(t))) return null;      // a colour / scheme request is a paint request: not ours
        if (!/\b(make|set|turn|change|give|put|want|apply)\b/.test(t) && t.trim().split(' ').length > 5) return null;
        if (LAYER_WORDS.some(function (lw) { return lw[1].test(t); })) return null;       // numbers / sponsors are PSD layers: the look request handles them
        var parts = []; PART_WORDS.forEach(function (pw) { if (pw[1].test(t.trim())) parts.push(pw[0]); });
        if (/\b(sides?|doors?)\b/.test(t) && parts.indexOf('left side') === -1 && parts.indexOf('right side') === -1) parts.push('left side', 'right side');
        var whole = /\b(whole|entire|all of|everything|the car|body)\b/.test(t) || !parts.length, fin = SPEC_LOOKS[look].finish, nm = capital(look) + ' (spec only)';
        var zones = []; if (whole && !parts.length) zones.push({ name: 'Whole car ' + look + ' (spec only)', finish: fin, color: 'source', region: { everything: true, paintable: true } });
        else parts.forEach(function (pt) { zones.push({ name: capital(pt) + ' ' + look + ' (spec only)', finish: fin, color: 'source', region: { part: pt } }); });
        return { look: look, parts: parts, zones: zones, about: SPEC_LOOKS[look].about };
    }
    // "make the roof matte black" / "left side blue" / "make the car red": a plain colour change on one or more named parts (no AI)
    function distinctCols(cols) { var out = []; cols.forEach(function (c) { if (!out.some(function (o) { return rgbDist(o.hex, c.hex) < 45; })) out.push(c); }); return out; }
    function offlinePart(text) {
        text = nz(text);
        var t = ' ' + norm(text) + ' ', cols = distinctCols(parseColours(text)); if (!cols.length) return null;
        if (compoundPlan(text)) return null;      // WP C: a compound order is a layer stack (offlineElement answers it)
        // a verbless list of parts + colours ("red hood blue roof", "hood red, roof blue and the bed white") is a paint request too, unless it is a question
        if (!/\b(make|paint|set|turn|put|give|want|change|colou?r|do)\b/.test(t) && t.trim().split(' ').length > 5 && !(cols.length > 1 && t.trim().split(' ').length <= 14 && !/\b(what|which|how|should|could|would|can|any|idea|suggest|recommend|best|why|is|are)\b/.test(t))) return null;
        if (/\b(liver(y|ies)|scheme|stripes?|bands?|retro|old school|throwback|theme|two tone|style|pinstripes?|accents?|highlights?)\b/.test(t)) return null;
        if (LAYER_WORDS.some(function (lw) { return lw[1].test(t); })) return null;
        var hits = []; PART_WORDS.forEach(function (pw) { var m = pw[1].exec(t); if (m) hits.push({ part: pw[0], at: m.index }); });
        if (/\b(sides?|doors?)\b/.test(t) && !hits.some(function (h) { return h.part === 'left side' || h.part === 'right side'; })) { var ms = /\b(sides?|doors?)\b/.exec(t); hits.push({ part: 'left side', at: ms.index }, { part: 'right side', at: ms.index }); }
        var whole = /\b(the car|my car|whole car|entire car|body|everything|all of it|it|car|truck|paint job)\b/.test(t) || (t.trim().split(' ').length <= 3 && !hits.length);
        if (!hits.length && !whole) return null;
        if (!hits.length && (cols.length > 1 || findPalette(text))) return null;            // a whole-car request with several colours is a scheme, not a part
        var fin = /\bmatte|flat\b/.test(t) ? 'base::matte' : (/\bsatin\b/.test(t) ? 'base::satin' : (/\bchrome\b/.test(t) ? 'base::chrome' : 'base::gloss')), zones = [], parts = [], used = {};
        // clauses split at "and" / commas / "then" / "but": a part takes the colour spoken in ITS clause ("hood ... red and roof ... blue"); a part with no colour of its own ("the hood and the roof red") takes the next clause's colour, else the previous one
        var cuts = [], cm, cre = /,|;|\band\b|\bthen\b|\bbut\b|\bwhile\b|\bplus\b/g; while ((cm = cre.exec(t))) cuts.push(cm.index);
        function clauseOf(at) { var n = 0; cuts.forEach(function (x) { if (x < at) n++; }); return n; }
        function nearest(list, at) { var best = null, bd = 1e9; list.forEach(function (c) { var d = Math.abs(c.at - at); if (d < bd) { bd = d; best = c; } }); return best; }
        function colourFor(h) {
            var k = clauseOf(h.at), byAt = function (a, b) { return a.at - b.at; };
            var ph = hits.filter(function (x) { return clauseOf(x.at) === k; }).sort(byAt), mine = cols.filter(function (c) { return clauseOf(c.at) === k; }).sort(byAt);
            if (mine.length && mine.length === ph.length) return mine[ph.indexOf(h)];            // "hood red roof blue" / "red hood blue roof": the i-th part gets the i-th colour
            if (mine.length) return nearest(mine, h.at);
            var nx = cols.filter(function (c) { return clauseOf(c.at) > k; }); if (nx.length) return nearest(nx, h.at);
            var pv = cols.filter(function (c) { return clauseOf(c.at) < k; }); return pv.length ? nearest(pv, h.at) : cols[0];
        }
        if (!hits.length) { zones.push({ name: capital(cols[0].name) + ' body', finish: fin, color: cols[0].hex, region: { everything: true } }); }
        else hits.forEach(function (h) { if (used[h.part]) return; used[h.part] = 1; var c = hits.length === 1 || cols.length === 1 ? cols[0] : colourFor(h); parts.push(h.part); zones.push({ name: capital(c.name) + ' ' + h.part, finish: fin, color: c.hex, region: { part: h.part } }); });
        return { parts: parts, zones: zones, colour: distinctCols(zones.map(function (z) { return { name: z.name.split(' ')[0].toLowerCase(), hex: z.color }; })).map(function (c) { return nameColour(c.hex); }).join(' and '), finish: fin.replace('base::', '') };
    }
    // Strict coverage proof for the configured-offline-first gate. This deliberately
    // recognizes only plain part recolours with one uniform supported finish. It
    // returns the actual offlinePart plan only after every meaningful token and
    // every part/colour/finish association is represented by that plan.
    function offlinePartCoverage(text) {
        var raw = String(text || ''), t = ' ' + norm(raw) + ' ';
        if (!raw.trim() || /\b(?:then|before|after|instead|rather than|but|except|unless|without|plus|also|additionally|another|layer|pattern|texture|carbon|snake|hex|weave|stripe|graphic|flame|spec|clearcoat|rotation|rotate|turn around|move|resize|fade|gradient|pinstripe|accent|highlight|sponsor|number|logo|glow|animate|animation)\b/i.test(t)) return null;
        // Only explicitly preservation-only clauses may be discarded. This does
        // not erase a positive instruction to keep a named panel a stated colour.
        var checked = raw.toLowerCase().replace(/’/g, "'"), preserveStarts = /\b(?:leave|leaving|keep|keeping)\s+(?:all|the|every|other|remaining|rest)\b/gi, pm, removals = [];
        while ((pm = preserveStarts.exec(checked))) {
            var tail = checked.slice(pm.index), end = tail.length, punct = /[,;.!?]/.exec(tail), splitJob = /\b(?:and|but|then)\s+(?:make|paint|set|turn|give|put|change|add|apply|recolor|repaint)\b/i.exec(tail);
            if (punct) end = Math.min(end, punct.index);
            if (splitJob) end = Math.min(end, splitJob.index);
            var clause = tail.slice(0, end);
            if (/\b(?:unchanged|alone|as it is|as they are|do not want the rest changed)\b/i.test(clause)) removals.push({ start: pm.index, end: pm.index + end });
        }
        var preservedOnlyTextRemoved = removals.length > 0;
        removals.sort(function (a, b) { return b.start - a.start; }).forEach(function (r) { checked = checked.slice(0, r.start) + ' ' + checked.slice(r.end); });
        var summaryText = checked.replace(/\bi want those (?:two )?named parts changed(?: independently)? and the remaining body (?:colou?r|paint) preserved(?: exactly as it is(?: now)?)?\b[.!?]?/gi, ' ');
        if (summaryText !== checked) preservedOnlyTextRemoved = true;
        checked = ' ' + norm(summaryText) + ' ';
        if (/\b(?:do not|don't|never|not)\b/i.test(checked)) return null;
        var plan = offlinePart(checked);
        if (!plan && preservedOnlyTextRemoved) {
            var cp = compoundPlan(checked);
            if (cp && cp.zones && cp.zones.length && !((cp.skipped || []).length) && (cp.layers || []).length === cp.zones.length && cp.layers.every(function (kind) { return kind === 'part'; }) && cp.zones.every(function (z) { return z.region && z.region.part && !z.region.everything; })) {
                plan = { parts: cp.zones.reduce(function (out, z) { var ps = Array.isArray(z.region.part) ? z.region.part : [z.region.part]; ps.forEach(function (p) { if (out.indexOf(p) < 0) out.push(p); }); return out; }, []), zones: cp.zones };
            }
        }
        if (!plan || !plan.zones || !plan.zones.length || plan.zones.some(function (z) { return !z.region || !z.region.part || z.region.everything; })) return null;

        var partMentions = [];
        PART_WORDS.forEach(function (pw) {
            var re = new RegExp(pw[1].source, 'gi'), m;
            while ((m = re.exec(checked))) partMentions.push({ part: pw[0], surface: m[0], at: m.index });
        });
        if (/\b(?:sides?|doors?)\b/i.test(checked) && !partMentions.some(function (h) { return h.part === 'left side' || h.part === 'right side'; })) {
            var sm = /\b(?:sides?|doors?)\b/i.exec(checked); partMentions.push({ part: 'left side', surface: '', at: sm.index }, { part: 'right side', surface: '', at: sm.index });
        }
        if (!partMentions.length) return null;
        var planned = {};
        plan.zones.forEach(function (z) {
            var p = Array.isArray(z.region.part) ? z.region.part : [z.region.part];
            p.forEach(function (name) { if (planned[name]) planned[name].push(z); else planned[name] = [z]; });
        });
        var namedParts = [];
        partMentions.forEach(function (h) { if (namedParts.indexOf(h.part) < 0) namedParts.push(h.part); });
        if (namedParts.length !== Object.keys(planned).length || namedParts.some(function (p) { return !planned[p] || planned[p].length !== 1; })) return null;

        // A whole-car positive instruction mixed into a part plan is not covered.
        if (/\b(?:whole|entire|all of|everything|the car|my car|body|paint job)\b/i.test(checked)) return null;
        var colours = parseColours(checked), cuts = [], cm, cre = /,|;|\band\b|\bwhile\b|\bplus\b/g;
        while ((cm = cre.exec(checked))) cuts.push(cm.index);
        function clauseOf(at) { var n = 0; cuts.forEach(function (x) { if (x < at) n++; }); return n; }
        function nearest(list, at) { var best = null, bd = 1e9; list.forEach(function (c) { var d = Math.abs(c.at - at); if (d < bd) { bd = d; best = c; } }); return best; }
        function expectedColour(h) {
            var k = clauseOf(h.at), ph = partMentions.filter(function (x) { return clauseOf(x.at) === k; }).sort(function (a, b) { return a.at - b.at; });
            var mine = colours.filter(function (x) { return clauseOf(x.at) === k; }).sort(function (a, b) { return a.at - b.at; });
            if (mine.length && mine.length === ph.length) return mine[ph.indexOf(h)];
            if (mine.length) return nearest(mine, h.at);
            var nx = colours.filter(function (x) { return clauseOf(x.at) > k; }); if (nx.length) return nearest(nx, h.at);
            return nearest(colours.filter(function (x) { return clauseOf(x.at) < k; }), h.at);
        }
        if (!colours.length) return null;
        var pairs = {};
        partMentions.forEach(function (h) { var c = expectedColour(h); if (!c) return; if (pairs[h.part] && pairs[h.part] !== c.hex) pairs[h.part] = 'conflict'; else pairs[h.part] = c.hex; });
        if (Object.keys(pairs).length !== namedParts.length || namedParts.some(function (p) { return pairs[p] === 'conflict' || !pairs[p] || !planned[p].some(function (z) { return String(z.color || '').toLowerCase() === String(pairs[p]).toLowerCase(); }); })) return null;

        // offlinePart supports matte/flat, satin, and its gloss default. Other
        // finish words and texture/material requests must not be claimed here.
        var explicitFinishes = (checked.match(/\b(matte|flat|satin|gloss|glossy|shiny|shine|chrome|pearl|pearlescent|candy|metallic|frosted|frozen|brushed)\b/gi) || []).map(function (x) { return x.toLowerCase(); });
        if (explicitFinishes.some(function (f) { return ['matte', 'flat', 'satin', 'gloss', 'glossy', 'shiny', 'shine', 'chrome'].indexOf(f) < 0; })) return null;
        if (new Set(explicitFinishes).size > 1) return null;
        var expectedFinish = explicitFinishes.length && (explicitFinishes[0] === 'matte' || explicitFinishes[0] === 'flat') ? 'base::matte' :
            explicitFinishes.length && explicitFinishes[0] === 'satin' ? 'base::satin' : explicitFinishes.length && explicitFinishes[0] === 'chrome' ? 'base::chrome' : 'base::gloss';
        if (plan.zones.some(function (z) { return z.finish !== expectedFinish; })) return null;

        var residual = checked.toLowerCase(), coveredWords = [];
        partMentions.forEach(function (h) { if (h.surface) coveredWords.push({ at: h.at, length: h.surface.length }); });
        colours.forEach(function (c) { coveredWords.push({ at: c.at, length: String(c.name || '').length }); });
        coveredWords.sort(function (a, b) { return b.at - a.at; }).forEach(function (w) { residual = residual.slice(0, w.at) + ' ' + residual.slice(w.at + w.length); });
        residual = residual.replace(/\b(?:matte|flat|satin|glossy|gloss|shiny|shine|chrome|make|paint|set|turn|give|put|want|change|colour|color|please|for|my|next|track|day|version|design|clean|new|look|only|just|exclusively|the|a|an|on|to|with|is|are|it|as|exactly|every|other|panel|panels|body|rest|unchanged|alone|because|already|like|current|do|not|would|keep|leave|all|remaining|that|same|and|while|sides?|doors?)\b/g, ' ').replace(/[^a-z0-9#]+/g, ' ').replace(/\s+/g, ' ').trim();
        if (residual) return null;
        var canonicalFinish = explicitFinishes.length ? (expectedFinish === 'base::matte' ? 'matte ' : expectedFinish === 'base::satin' ? 'satin ' : expectedFinish === 'base::chrome' ? 'chrome ' : 'gloss ') : '';
        var canonicalText = plan.zones.map(function (z) { return 'paint the ' + z.region.part + ' ' + canonicalFinish + nameColour(z.color).toLowerCase(); }).join('; ');
        return { kind: 'part-coverage', zones: plan.zones, parts: namedParts, finish: expectedFinish, finishExplicit: explicitFinishes.length > 0, canonicalText: canonicalText, complete: true };
    }
    // ------------------------------------------------------------------ offline follow-ups on the last scheme: "thinner", "make the red orange", "matte", "another take", "no chrome" ...
    function replaceColour(plan, fromName, toCol) {
        var fromHex = COLOURS[fromName], hit = false, p = plan.palette;
        if (!fromHex) return false;
        Object.keys(p).forEach(function (k) { var a = hexRgb(p[k]), b = hexRgb(fromHex), d = Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]); if (nameColour(p[k]) === nameColour(fromHex) || d < 90) { p[k] = toCol.hex; hit = true; } });
        return hit;
    }
    // a request that names a PART ("make the roof matte black") is a part change, not a tweak of the whole scheme
    function mentionsPart(text) { var t = String(text || '').toLowerCase().trim(), hit = false; PART_WORDS.forEach(function (pw) { if (pw[1].test(t)) hit = true; }); return hit || /\b(sides?|doors?)\b/.test(t); }
    function refine(plan, text) {
        if (!plan || !plan.preset) return null;
        if (mentionsPart(text) || LAYER_WORDS.some(function (lw) { return lw[1].test(String(text).toLowerCase()); })) return null;
        var t = ' ' + norm(text) + ' ', np = JSON.parse(JSON.stringify(plan)), did = [], cols = parseColours(text);
        np.ctx = np.ctx || { paint: 'base::gloss', trim: 'base::chrome' }; np.scale = np.scale || 1;
        if (/\b(thinner|thin|slimmer|skinnier|narrower|smaller|subtler|subtle|less bold)\b/.test(t)) { np.scale = Math.max(0.35, np.scale * 0.65); did.push('thinner stripes and bands'); }
        else if (/\b(thicker|wider|bolder|fatter|broader|bigger|heavier|louder)\b/.test(t)) { np.scale = Math.min(2.2, np.scale * 1.5); did.push('thicker stripes and bands'); }
        var fin = /\b(matte|matt|flat)\b/.test(t) ? 'base::matte' : (/\bsatin\b/.test(t) ? 'base::satin' : (/\b(gloss|glossy|shiny)\b/.test(t) ? 'base::gloss' : null));
        if (fin && fin !== np.ctx.paint && /\b(make|set|switch|change|go|use|want|more|less|instead)\b/.test(t)) { np.ctx.paint = fin; did.push(fin.replace('base::', '') + ' finish'); }
        if (/\b(no chrome|without chrome|not chrome|remove the chrome|drop the chrome)\b/.test(t)) { np.ctx.trim = np.ctx.paint; did.push('no chrome trim'); }
        else if (/\b(add|more|give me|with)\b[^.]{0,20}\bchrome\b/.test(t) || /\bchrome (trim|pinstripe|accents?)\b/.test(t)) { if (np.ctx.trim !== 'base::chrome') { np.ctx.trim = 'base::chrome'; did.push('chrome trim'); } }
        np.flags = np.flags || {};
        if (/\b(remove|no|without|drop|lose)\b[^.]{0,14}\b(pinstripes?|pin stripes?|thin lines?)\b/.test(t)) { if (!np.flags.noPin) { np.flags.noPin = true; np.flags.addPin = false; did.push('no pinstripe'); } }
        else if (/\b(add|give me|put|with)\b[^.]{0,16}\b(pinstripes?|pin stripes?)\b/.test(t) && !np.flags.addPin) { np.flags.addPin = true; np.flags.noPin = false; did.push('a pinstripe'); }
        if (/\b(swap|switch|flip|invert|reverse)\b[^.]{0,20}\b(colou?rs?)\b/.test(t) && !cols.length) { var p = np.palette, tmp = p.a; p.a = p.b; p.b = tmp; if (p.a === p.b) { tmp = p.base; p.base = p.a; p.a = tmp; } did.push('swapped the two colours'); }
        else if (!/\bwith\b/.test(t) && (cols.length >= 2 && /\b(to|into|for|instead of)\b/.test(t) || (cols.length === 2 && /\b(make|change|turn)\b/.test(t) && t.split(' ').length <= 8))) {
            var c1 = cols[0], c2 = cols[1], ok = replaceColour(np, c1.name, c2);
            if (!ok && replaceColour(np, c2.name, c1)) { ok = true; c1 = cols[1]; c2 = cols[0]; }
            if (ok) did.push(c1.name + ' became ' + c2.name);
        } else if (cols.length === 1 && /\b(more|add|use|switch to|change (it )?to|make (it|the (stripes?|band|accent)))\b/.test(t) && !fin) {
            var c = cols[0]; if (/\bbase|body|background\b/.test(t)) np.palette.base = c.hex; else { np.palette.a = c.hex; }
            did.push('accent colour is now ' + c.name);
        }
        if (/\b(another|different|again|something else|try again|redo|other style|new look|shuffle)\b/.test(t) && !/\b(ideas|options|surprise me)\b/.test(t) && !did.length) {
            var pal = plan.palette_id ? paletteById(plan.palette_id) : null, ids = pal ? pal.presets : Object.keys(PRESETS), cur = ids.indexOf(plan.preset);
            np.preset = ids[(cur + 1) % ids.length] === plan.preset ? Object.keys(PRESETS)[(Object.keys(PRESETS).indexOf(plan.preset) + 1) % Object.keys(PRESETS).length] : ids[(cur + 1) % ids.length];
            did.push('a different layout (' + PRESETS[np.preset].name + ')');
        }
        if (!did.length) return null;
        np.elements = presetSteps(np.preset, np.palette).filter(function (e) { return !(np.flags.noPin && e.id === 'pinstripe'); });
        if (np.flags.addPin && !np.elements.some(function (e) { return e.id === 'pinstripe'; })) np.elements.push({ id: 'pinstripe', colour: np.palette.trim || '#c3c7cc', at: 0.64, width: 0.03 });
        return { plan: np, did: did };
    }
    // ------------------------------------------------------------------ offline: text -> a finished scheme, no AI at all
    function offlinePlan(text) {
        text = nz(text);
        var t = norm(text); if (!t || t.length < 4) return null;
        if (compoundPlan(text)) return null;      // WP C: a compound order is a layer stack (offlineElement answers it)
        if (/\b(undo|redo|what|how|why|explain|help|export|save|render|delete)\b/.test(t) && !/\b(make|give|put|add|paint|design|want)\b/.test(t)) return null;
        var pal = findPalette(text), cols = parseColours(text);
        if (mentionsPart(text) || LAYER_WORDS.some(function (lw) { return lw[1].test(' ' + t + ' '); })) return null;      // "make the sides red with white stripes" / "red car with white numbers": not a whole-car scheme
        var scheme = null;
        if (/\b(two tone|split|half and half)\b/.test(t)) scheme = 'two_tone';
        else if (/\b(twin|double|racing stripes?|stripes?|pinstripes?)\b/.test(t) && !/\blower|rocker|skirt\b/.test(t)) scheme = 'classic_stripes';
        else if (/\b(lower band|rocker|skirt|band|bottom)\b/.test(t)) scheme = 'retro_lower_band';
        else if (/\b(bumpers?|bookends?|front and rear|accents?|highlights?)\b/.test(t)) scheme = 'bookends';
        else if (/\b(stealth|blackout|murdered out|all black)\b/.test(t)) scheme = 'stealth';
        else if (/\b(block|blocks|geometric|colou?r block)\b/.test(t)) scheme = 'colour_block';
        else if (pal) scheme = pal.presets[0];
        else if (/\b(retro|old school|throwback|vintage|liver(y|ies)|scheme|design)\b/.test(t) && cols.length >= 2) scheme = 'retro_lower_band';
        else if (cols.length >= 2 && !mentionsPart(text) && /\b(car|truck|paint|colou?rs?|with|and)\b/.test(t)) scheme = 'retro_lower_band';
        if (!scheme || (!pal && cols.length < 1 && !/\b(retro|old school|throwback|vintage)\b/.test(t))) return null;
        if (!pal && cols.length < 2 && !/\b(stripes?|pinstripes?|two tone|split|bookends?|lower band|rocker|skirt|band)\b/.test(t)) return null;      // one colour and no layout word: that is a part or a body colour, not a scheme
        var p;
        if (pal) {
            p = { base: pal.base, a: pal.a, b: pal.b, c: pal.c, trim: pal.trim };
            var named = cols.filter(function (c) { return ['white', 'off white', 'cream', 'ivory', 'black', 'charcoal', 'grey', 'gray', 'silver'].indexOf(c.name) === -1; });
            if (named.length && !pal.names.some(function (n) { return t.indexOf(norm(n)) !== -1 && /\b(red|blue|white|gold|orange|pink|green|yellow|purple|teal)\b/.test(norm(n)); })) {
                var rest0 = named.slice();
                if (rgbDist(rest0[0].hex, pal.base) < 60) p.base = rest0.shift().hex;   // "Gulf: powder blue with orange" restates the body colour, the orange is the accent
                if (rest0.length) { p.a = rest0[0].hex; if (rest0[1]) p.b = rest0[1].hex; if (scheme === 'stealth' || scheme === 'bookends') p.trim = rest0[0].hex; }
            }
        } else {
            var neutral = ['white', 'off white', 'cream', 'ivory', 'black', 'charcoal', 'grey', 'gray', 'silver'], base = null, rest = [];
            cols.forEach(function (c) { if (!base && neutral.indexOf(c.name) !== -1 && cols.length >= 2) base = c; else rest.push(c); });
            if (!base) base = rest.shift() || { hex: '#f4f4f1' };
            var partner = { hex: rgbDist(base.hex, '#f4f4f1') > 70 ? '#f4f4f1' : '#111113' };
            var a = rest[0] || partner, b = rest[1] || rest[0] || partner, c2 = rest[2] || a;
            p = { base: base.hex, a: a.hex, b: b.hex, c: c2.hex, trim: '#c3c7cc' };
        }
        ensureContrast(p);
        var paint = /\b(matte|flat)\b/.test(t) ? 'base::matte' : (/\bsatin\b/.test(t) ? 'base::satin' : (/\b(pearl|pearlescent)\b/.test(t) ? 'base::pearl' : (/\bcandy\b/.test(t) ? 'base::candy' : (/\bmetallic\b/.test(t) ? 'base::metallic' : 'base::gloss'))));
        var trim = /\bchrome\b/.test(t) || !/\b(gold|white)\s+(trim|pinstripes?)\b/.test(t) ? 'base::chrome' : paint;
        if (paint !== 'base::gloss' && paint !== 'base::matte' && paint !== 'base::satin') trim = 'base::chrome';
        return { preset: scheme, palette: p, palette_id: pal ? pal.id : null, ctx: { paint: paint, trim: trim }, scale: 1, elements: presetSteps(scheme, p) };
    }
    // "white with royal blue and red, flat paint with chrome trim"
    // ------------------------------------------------------------------ IDEAS (2026-10-01): "surprise me" / "give me ideas" / "ideas in black and gold" -> several complete, different designs to preview and pick from
    var IDEA_SEED = 0;
    var IDEA_RE = /\b(surprise me|surprise us|(give|show) me (some |a few |more |other |different )?(ideas|options|designs|directions|concepts|looks|schemes)|any ideas|(more|other|new|fresh|different) (ideas|options|designs|directions|looks)|ideas|inspire me|inspiration|brainstorm|mix it up|something (cool|different|new|fresh|else|wild|bold)|what would look (good|cool|great|best)|what should i do)\b/;
    var VAGUE_RE = /\b(make it|make the car|make my car|can you make it|i want it to)\b[^.]{0,24}\b(pop|stand out|unique|expensive|premium|luxury|luxurious|classy|fancy|cooler|sick|badass|awesome|amazing|epic|dope|fresh|stunning|beautiful|gorgeous|special|wow|better|faster)\b/;
    var IDEA_FILLER = /\b(surprise|me|us|give|show|some|a|few|more|other|different|new|fresh|ideas?|options?|designs?|directions?|concepts?|looks?|schemes?|any|please|inspire|inspiration|brainstorm|mix|it|up|something|cool|else|wild|bold|what|would|look|good|great|best|should|i|do|for|my|car|in|with|of|and|the|to|try|can|you|i|d|like|want|love|need|four|three|five|4|3|5)\b/g;
    function offlineIdeas(text, peek, forced) {
        var t = norm(text); if (!t || (!forced && !IDEA_RE.test(t) && !VAGUE_RE.test(t))) return null;
        if (/\b(make|paint|turn|change|set|put|add|remove|undo|hood|roof|trunk|bumper|spoiler|sides?|doors?|numbers?)\b/.test(t) && !/\b(surprise me|ideas|options)\b/.test(t) && !VAGUE_RE.test(t)) return null;
        var cols = (forced && forced.length) ? forced.slice(0, 3) : parseColours(text), left = t.replace(IDEA_FILLER, ' ').replace(/\s+/g, ' ').trim(), leftWords = left ? left.split(' ').filter(function (w) { return w.length > 1; }) : [];
        cols.forEach(function (c) { c.name.split(' ').forEach(function (w) { leftWords = leftWords.filter(function (x) { return x !== w; }); }); });
        var generic = leftWords.length <= 1 || !!forced || VAGUE_RE.test(t);
        var seed = peek ? IDEA_SEED : IDEA_SEED++, plans = [], n = 4;
        var PRE = ['classic_stripes', 'retro_lower_band', 'two_tone', 'colour_block', 'bookends', 'stealth'];
        function titleOf(pal) { var w = pal.id.replace(/-/g, ' '); return w.charAt(0).toUpperCase() + w.slice(1); }
        function finish(k, pal) { return pal.id === 'stealth' ? 'base::matte' : (k % 3 === 2 ? 'base::satin' : 'base::gloss'); }
        function push(pl, label) { pl.label = label; pl.why = PRESETS[pl.preset].name + ': ' + describePlan(pl); plans.push(pl); }
        var names = [];
        if (cols.length) {
            // the buyer's own colours, arranged four different ways (body / stripe / second stripe roles move around)
            var X = cols[0], Y = cols[1] || null, NEU = ['white', 'black', 'silver', 'gold', 'cream', 'charcoal'];
            names = [X.name]; if (Y) names.push(Y.name); if (cols[2]) names.push(cols[2].name);
            function H(n) { return COLOURS[n]; }
            function partnerOf(c) { var o = NEU.filter(function (n) { return rgbDist(H(n), c.hex) > 70; }); return o[(seed) % o.length]; }
            var Z3 = cols[2] ? cols[2].hex : null, P = Y ? Y : { name: partnerOf(X), hex: H(partnerOf(X)) }, W = rgbDist('#f4f4f1', X.hex) > 60 && rgbDist('#f4f4f1', P.hex) > 60 ? 'white' : 'black';
            var dark = rgbDist('#111113', X.hex) > 70 && rgbDist('#111113', P.hex) > 70 ? 'black' : 'white';
            var recipes4 = [
                { preset: 'classic_stripes', pal: { base: X.hex, a: P.hex, b: Z3 || H(W), c: Z3 || H(W), trim: Z3 || H(W) }, paint: 'base::gloss', trim: 'base::chrome', tag: 'on ' + X.name },
                { preset: 'retro_lower_band', pal: { base: H(W), a: X.hex, b: Z3 || P.hex, c: P.hex, trim: P.hex }, paint: 'base::gloss', trim: 'base::chrome', tag: 'light body' },
                { preset: 'bookends', pal: { base: H(dark), a: X.hex, b: P.hex, c: Z3 || P.hex, trim: X.hex }, paint: 'base::matte', trim: 'base::chrome', tag: (dark === 'black' ? 'dark' : 'light') + ' and matte' },
                { preset: 'two_tone', pal: { base: P.hex, a: X.hex, b: H(W), c: X.hex, trim: H(W) }, paint: 'base::satin', trim: 'base::satin', tag: 'on ' + P.name },
                { preset: 'colour_block', pal: { base: H(W), a: X.hex, b: P.hex, c: Z3 || X.hex, trim: H(dark) }, paint: 'base::gloss', trim: 'base::gloss', tag: 'blocks' }
            ];
            for (var i = 0; plans.length < n && i < recipes4.length; i++) {
                var rc = recipes4[(i + seed) % recipes4.length], pp = ensureContrast(rc.pal);
                push({ preset: rc.preset, palette: pp, palette_id: null, ctx: { paint: rc.paint, trim: rc.trim }, scale: 1, elements: presetSteps(rc.preset, pp) }, PRESETS[rc.preset].name + ' · ' + rc.tag);
            }
        } else {
            var pool = PALETTES.filter(function (q) { return ['halloween', 'christmas'].indexOf(q.id) === -1; }), chosen = [];
            for (var j = 0; chosen.length < n && j < pool.length * 2; j++) {
                var cand = pool[(seed * 5 + j * 7) % pool.length]; if (chosen.indexOf(cand) !== -1) continue;
                if (chosen.some(function (q) { return rgbDist(q.base, cand.base) < 45 && rgbDist(q.a, cand.a) < 60; })) continue;
                chosen.push(cand);
            }
            var LOOK_IDEAS = [['carbon fiber', 'classic_stripes'], ['galaxy', 'bookends'], ['camo', 'retro_lower_band'], ['holographic', 'bookends'], ['flames', 'bookends'], ['checkered', 'classic_stripes'], ['chameleon', 'bookends']];
            chosen.forEach(function (pal, k) {
                if (k >= n - 2 && LOOK_CURATED) {
                    var li = LOOK_IDEAS[(seed * 2 + k) % LOOK_IDEAS.length], lk = LOOK_CURATED[li[0]];
                    if (lk) {
                        var lp = ensureContrast({ base: lk.dark || '#111113', a: pal.a, b: pal.b, c: pal.c, trim: pal.trim }), bl = { label: lk.label, zone: lk.zone, colour: lk.colour, dark: lk.dark || null, alt: lk.alt || [] };
                        push({ preset: li[1], palette: lp, palette_id: null, ctx: { paint: 'base::gloss', trim: 'base::chrome' }, scale: 1, baseLook: bl, elements: presetSteps(li[1], lp) }, lk.label + ' + ' + nameColour(lp.a));
                        return;
                    }
                }
                var preset = pal.presets[(seed + k) % pal.presets.length], pp = ensureContrast({ base: pal.base, a: pal.a, b: pal.b, c: pal.c, trim: pal.trim }), paint = finish(k, pal);
                push({ preset: preset, palette: pp, palette_id: pal.id, ctx: { paint: paint, trim: k % 2 ? paint : 'base::chrome' }, scale: 1, elements: presetSteps(preset, pp) }, titleOf(pal));
            });
        }
        if (!plans.length) return null;
        return { plans: plans, generic: generic, colours: cols.length, text: (!generic && !cols.length ? 'I cannot design a specific theme without the AI, but ' : '') + (!generic && !cols.length ? 'here are ' : 'Here are ') + plans.length + ' different directions' + (cols.length ? ' in ' + names.join(' and ') : '') + '. Tap the one you like and I will put it on your car.' + '\nNEXT: More ideas | ' + (cols.length ? 'Ideas in black and gold' : 'Ideas in red and white') + ' | Surprise me with something dark' };
    }
    // ------------------------------------------------------------------ LOOK REQUESTS (2026-10-01): "make the hood carbon fiber", "give me a galaxy roof", "make the numbers chrome", "candy red body"
    // Pure parsing (no catalogue here): which targets (named parts / PSD layers like numbers+sponsors / whole body), which colour, which finish word, which free "look" words are left over.
    // the classics, checked by eye on 1:1 contact sheets (_easy_claude_work/eval/looks_sheet.png): word -> { label, zone: { finish, pattern? }, colour: 'own' (brings its colours) | 'zone' (takes the zone colour), dark: default colour, alt: fallback finish keys }
    var LOOK_CURATED = {"carbon fiber":{"label":"Carbon fiber","zone":{"finish":"base::gloss","pattern":{"id":"carbon_fiber","opacity":45,"scale":1.4}},"colour":"zone","dark":"#0e0e12"},"carbon fibre":{"label":"Carbon fiber","zone":{"finish":"base::gloss","pattern":{"id":"carbon_fiber","opacity":45,"scale":1.4}},"colour":"zone","dark":"#0e0e12"},"carbon":{"label":"Carbon fiber","zone":{"finish":"base::gloss","pattern":{"id":"carbon_fiber","opacity":45,"scale":1.4}},"colour":"zone","dark":"#0e0e12"},"carbon weave":{"label":"Carbon fiber","zone":{"finish":"base::gloss","pattern":{"id":"carbon_fiber","opacity":45,"scale":1.4}},"colour":"zone","dark":"#0e0e12"},"camo":{"label":"Camo","zone":{"finish":"base::gloss","pattern":{"id":"camo","opacity":100,"scale":2}},"colour":"zone","dark":"#5a6b2a"},"camouflage":{"label":"Camo","zone":{"finish":"base::gloss","pattern":{"id":"camo","opacity":100,"scale":2}},"colour":"zone","dark":"#5a6b2a"},"digital camo":{"label":"Camo","zone":{"finish":"base::gloss","pattern":{"id":"camo","opacity":100,"scale":2}},"colour":"zone","dark":"#5a6b2a"},"flames":{"label":"Flames","zone":{"finish":"base::flame_phoenix"},"colour":"own","alt":["monolithic::ffl_blowtorch"]},"flame":{"label":"Flames","zone":{"finish":"base::flame_phoenix"},"colour":"own","alt":["monolithic::ffl_blowtorch"]},"phoenix":{"label":"Flames","zone":{"finish":"base::flame_phoenix"},"colour":"own","alt":["monolithic::ffl_blowtorch"]},"fire":{"label":"Fire","zone":{"finish":"monolithic::ffl_blowtorch"},"colour":"own","alt":["base::flame_phoenix"]},"blowtorch":{"label":"Fire","zone":{"finish":"monolithic::ffl_blowtorch"},"colour":"own","alt":["base::flame_phoenix"]},"inferno":{"label":"Fire","zone":{"finish":"monolithic::ffl_blowtorch"},"colour":"own","alt":["base::flame_phoenix"]},"galaxy":{"label":"Galaxy","zone":{"finish":"base::pour_galaxy"},"colour":"own","alt":["monolithic::fnb_violet_galaxy"]},"nebula":{"label":"Galaxy","zone":{"finish":"base::pour_galaxy"},"colour":"own","alt":["monolithic::fnb_violet_galaxy"]},"cosmic":{"label":"Galaxy","zone":{"finish":"base::pour_galaxy"},"colour":"own","alt":["monolithic::fnb_violet_galaxy"]},"space":{"label":"Galaxy","zone":{"finish":"base::pour_galaxy"},"colour":"own","alt":["monolithic::fnb_violet_galaxy"]},"holographic":{"label":"Holographic","zone":{"finish":"base::holographic_base"},"colour":"own","alt":["monolithic::grd_holo_foil"]},"hologram":{"label":"Holographic","zone":{"finish":"base::holographic_base"},"colour":"own","alt":["monolithic::grd_holo_foil"]},"holo":{"label":"Holographic","zone":{"finish":"base::holographic_base"},"colour":"own","alt":["monolithic::grd_holo_foil"]},"holographic foil":{"label":"Holographic","zone":{"finish":"base::holographic_base"},"colour":"own","alt":["monolithic::grd_holo_foil"]},"hex":{"label":"Hex tiles","zone":{"finish":"base::gloss","pattern":{"id":"hex_carbon","opacity":100,"scale":2}},"colour":"zone","dark":"#0e0e12"},"hexagon":{"label":"Hex tiles","zone":{"finish":"base::gloss","pattern":{"id":"hex_carbon","opacity":100,"scale":2}},"colour":"zone","dark":"#0e0e12"},"hexagons":{"label":"Hex tiles","zone":{"finish":"base::gloss","pattern":{"id":"hex_carbon","opacity":100,"scale":2}},"colour":"zone","dark":"#0e0e12"},"honeycomb":{"label":"Hex tiles","zone":{"finish":"base::gloss","pattern":{"id":"hex_carbon","opacity":100,"scale":2}},"colour":"zone","dark":"#0e0e12"},"checkered":{"label":"Checkerboard","zone":{"finish":"base::gloss","pattern":{"id":"decade_50s_diner_checkerboard","opacity":100,"scale":1}},"colour":"zone","dark":"#f4f4f1"},"checker":{"label":"Checkerboard","zone":{"finish":"base::gloss","pattern":{"id":"decade_50s_diner_checkerboard","opacity":100,"scale":1}},"colour":"zone","dark":"#f4f4f1"},"checkerboard":{"label":"Checkerboard","zone":{"finish":"base::gloss","pattern":{"id":"decade_50s_diner_checkerboard","opacity":100,"scale":1}},"colour":"zone","dark":"#f4f4f1"},"diner checkerboard":{"label":"Checkerboard","zone":{"finish":"base::gloss","pattern":{"id":"decade_50s_diner_checkerboard","opacity":100,"scale":1}},"colour":"zone","dark":"#f4f4f1"},"diamond plate":{"label":"Diamond plate","zone":{"finish":"base::chrome","pattern":{"id":"diamond_plate","opacity":100,"scale":1}},"colour":"zone","dark":"#c3c7cc"},"tread plate":{"label":"Diamond plate","zone":{"finish":"base::chrome","pattern":{"id":"diamond_plate","opacity":100,"scale":1}},"colour":"zone","dark":"#c3c7cc"},"treadplate":{"label":"Diamond plate","zone":{"finish":"base::chrome","pattern":{"id":"diamond_plate","opacity":100,"scale":1}},"colour":"zone","dark":"#c3c7cc"},"chameleon":{"label":"Colour-shift","zone":{"finish":"base::chromaflair"},"colour":"own","alt":["monolithic::chameleon_amethyst"]},"colour shift":{"label":"Colour-shift","zone":{"finish":"base::chromaflair"},"colour":"own","alt":["monolithic::chameleon_amethyst"]},"color shift":{"label":"Colour-shift","zone":{"finish":"base::chromaflair"},"colour":"own","alt":["monolithic::chameleon_amethyst"]},"colorshift":{"label":"Colour-shift","zone":{"finish":"base::chromaflair"},"colour":"own","alt":["monolithic::chameleon_amethyst"]},"color flip":{"label":"Colour-shift","zone":{"finish":"base::chromaflair"},"colour":"own","alt":["monolithic::chameleon_amethyst"]},"chromaflair":{"label":"Colour-shift","zone":{"finish":"base::chromaflair"},"colour":"own","alt":["monolithic::chameleon_amethyst"]},"dichroic":{"label":"Dichroic","zone":{"finish":"monolithic::xlab_dichroic_skin"},"colour":"own","alt":["base::holographic_base"]},"prism":{"label":"Dichroic","zone":{"finish":"monolithic::xlab_dichroic_skin"},"colour":"own","alt":["base::holographic_base"]},"prizm":{"label":"Dichroic","zone":{"finish":"monolithic::xlab_dichroic_skin"},"colour":"own","alt":["base::holographic_base"]},"iridescent":{"label":"Dichroic","zone":{"finish":"monolithic::xlab_dichroic_skin"},"colour":"own","alt":["base::holographic_base"]},"candy":{"label":"Candy","zone":{"finish":"base::candy"},"colour":"zone","dark":"#c8102e","alt":[]},"pearl":{"label":"Pearl","zone":{"finish":"base::pearl"},"colour":"zone","dark":"#f4f4f1","alt":[]},"pearlescent":{"label":"Pearl","zone":{"finish":"base::pearl"},"colour":"zone","dark":"#f4f4f1","alt":[]},"metallic":{"label":"Metallic","zone":{"finish":"base::metallic"},"colour":"zone","dark":"#8a8d92","alt":[]},"metal flake":{"label":"Metal flake","zone":{"finish":"base::xirallic"},"colour":"zone","dark":"#1450b4","alt":["base::metallic"]},"metalflake":{"label":"Metal flake","zone":{"finish":"base::xirallic"},"colour":"zone","dark":"#1450b4","alt":["base::metallic"]},"flake":{"label":"Metal flake","zone":{"finish":"base::xirallic"},"colour":"zone","dark":"#1450b4","alt":["base::metallic"]},"glitter":{"label":"Metal flake","zone":{"finish":"base::xirallic"},"colour":"zone","dark":"#1450b4","alt":["base::metallic"]},"sparkle":{"label":"Metal flake","zone":{"finish":"base::xirallic"},"colour":"zone","dark":"#1450b4","alt":["base::metallic"]},"sparkly":{"label":"Metal flake","zone":{"finish":"base::xirallic"},"colour":"zone","dark":"#1450b4","alt":["base::metallic"]},"gunmetal":{"label":"Gunmetal","zone":{"finish":"base::gunmetal"},"colour":"zone","dark":"#4a4f57","alt":[]},"copper":{"label":"Copper","zone":{"finish":"base::copper"},"colour":"own","alt":[]},"brushed aluminum":{"label":"Brushed aluminum","zone":{"finish":"base::brushed_aluminum"},"colour":"zone","dark":"#c3c7cc","alt":[]},"brushed aluminium":{"label":"Brushed aluminum","zone":{"finish":"base::brushed_aluminum"},"colour":"zone","dark":"#c3c7cc","alt":[]},"brushed":{"label":"Brushed aluminum","zone":{"finish":"base::brushed_aluminum"},"colour":"zone","dark":"#c3c7cc","alt":[]},"aluminum":{"label":"Brushed aluminum","zone":{"finish":"base::brushed_aluminum"},"colour":"zone","dark":"#c3c7cc","alt":[]},"aluminium":{"label":"Brushed aluminum","zone":{"finish":"base::brushed_aluminum"},"colour":"zone","dark":"#c3c7cc","alt":[]},"tiger":{"label":"Tiger stripes","zone":{"finish":"base::gloss","pattern":{"id":"tiger_stripe","opacity":100,"scale":1}},"colour":"zone","dark":"#f26b21"},"tiger stripe":{"label":"Tiger stripes","zone":{"finish":"base::gloss","pattern":{"id":"tiger_stripe","opacity":100,"scale":1}},"colour":"zone","dark":"#f26b21"},"tiger stripes":{"label":"Tiger stripes","zone":{"finish":"base::gloss","pattern":{"id":"tiger_stripe","opacity":100,"scale":1}},"colour":"zone","dark":"#f26b21"},"plaid":{"label":"Plaid","zone":{"finish":"base::gloss","pattern":{"id":"plaid","opacity":60,"scale":1}},"colour":"zone","dark":"#a3123a"},"houndstooth":{"label":"Houndstooth","zone":{"finish":"base::gloss","pattern":{"id":"houndstooth","opacity":40,"scale":1}},"colour":"zone","dark":"#0b2350"}};
    var LAYER_WORDS = [['numbers', /\b(numbers?|number panels?)\b/], ['sponsors', /\b(sponsors?|sponsor (panels?|logos?))\b/]];
    var LOOK_STOP = ' make give put paint turn set add apply want wanted wants like love need please can could would you me my i it its that this the a an of on in with and to for from only just also too some more really very change use do have get be is are as car cars body whole entire all everything finish finishes look looks effect effects texture pattern style type kind hood bonnet roof trunk deck lid rear front bumper bumpers nose tail end spoiler wing left right driver drivers passenger passengers side sides door doors flank number numbers sponsor sponsors panel panels logo logos decal decals gloss glossy shiny matte matt flat satin eggshell chrome mirror top bottom lower upper half part parts them these those one both pop amazing awesome cool nice great better good sick insane crazy epic beautiful pretty stunning sharp accent accents highlight highlights detail details dark light bright deep pale shine shinier glossier duller flatter darker lighter brighter deeper paler bolder richer softer bit slightly little much lot kind sort over under above below half fender fenders quarter quarters panel panels should would could might except list explain ';
    function lookRequest(text) {
        text = nz(text);
        var t = norm(text); if (!t) return null;
        if (compoundPlan(text)) return null;      // WP C: a compound order is a layer stack (offlineElement answers it)
        if (!/\b(make|give|put|paint|turn|set|add|apply|want|wanted|like|love|need|change|use|do|have|get)\b/.test(t) && t.split(' ').length > 5) return null;
        if (IDEA_RE.test(t) || VAGUE_RE.test(t)) return null;
        if (/^(how|what|where|why|when|which|who|is|are|does|do|help|hello|hi|hey|thanks|thank you)\b/.test(t) || /[?]/.test(String(text)) || /\b(export|save|render|iracing|template|spec map|clearcoat|layers?|mask|wire|undo)\b/.test(t)) return null;
        var named = false; PART_WORDS.forEach(function (pw) { if (pw[1].test(t)) named = true; }); LAYER_WORDS.forEach(function (lw) { if (lw[1].test(t)) named = true; }); if (/\b(sides?|doors?)\b/.test(t)) named = true;
        if (!named && findPalette(text)) return null;       // a theme word on the whole car is a scheme (palette); on a named part it is a look
        if (/\b(liver(y|ies)|scheme|stripes?|bands?|retro|old school|throwback|theme|two tone|pinstripes?)\b/.test(t) && !/\b(tiger|zebra|leopard|cheetah|checker[a-z]*|plaid|houndstooth|camo[a-z]*|flame[a-z]*)\b/.test(t)) return null;
        var cols = parseColours(text), cw = {}; cols.forEach(function (c) { c.name.split(' ').forEach(function (w) { cw[w] = 1; }); });
        var left = t.split(' ').filter(function (w) { return w.length > 1 && !cw[w] && !/^[0-9]+$/.test(w) && LOOK_STOP.indexOf(' ' + w + ' ') === -1; });
        var parts = [], layers = [];
        PART_WORDS.forEach(function (pw) { if (pw[1].test(t)) parts.push(pw[0]); });
        if (/\b(sides?|doors?)\b/.test(t) && parts.indexOf('left side') === -1 && parts.indexOf('right side') === -1) parts.push('left side', 'right side');
        LAYER_WORDS.forEach(function (lw) { if (lw[1].test(t)) layers.push(lw[0]); });
        if (!left.length && !layers.length) return null;
        if (layers.length && cols.length >= 2) return null;                       // "red car with white numbers" is two jobs: say so instead of guessing
        var fin = /\b(matte|matt|flat)\b/.test(t) ? 'base::matte' : (/\b(satin|eggshell)\b/.test(t) ? 'base::satin' : (/\b(chrome|mirror)\b/.test(t) ? 'base::chrome' : null));
        return { query: left.join(' '), parts: parts, layers: layers, whole: !parts.length && !layers.length, colour: cols[0] || null, finish: fin };
    }
    // "add a white pinstripe along the sides", "add a red racing stripe", "put a gold beltline stripe on it": ONE element on a car with no scheme yet
    function offlineElement(text) {
        text = nz(text);
        var cp = compoundPlan(text); if (cp) return cp;      // WP C: compound order -> the whole layer stack (zones bottom to top; ai.js offlineElementAsk adds them in order)
        var t = ' ' + norm(text) + ' ', cols = distinctCols(parseColours(text));
        if (/\b(liver(y|ies)|scheme|retro|theme|two tone|stripes and|stripes with)\b/.test(t) || findPalette(text) || cols.length > 1) return null;
        if (LAYER_WORDS.some(function (lw) { return lw[1].test(t); })) return null;
        var ctx = { paint: /\bchrome\b/.test(t) ? 'base::chrome' : (/\bmatte|flat\b/.test(t) ? 'base::matte' : 'base::gloss'), trim: 'base::gloss', scale: 1 };
        // "make the bottom half black" / "paint the top half white": a band along the sides
        var half = /\b(top|upper|bottom|lower) half\b/.exec(t);
        if (half && cols.length === 1 && /\b(make|paint|put|give|turn|colou?r|set)\b/.test(t) && !mentionsPart(text)) {
            var low = /bottom|lower/.test(half[1]), hel = low ? { id: 'lower_band', colour: cols[0].hex, from: 0.5, to: 1 } : { id: 'upper_band', colour: cols[0].hex, from: 0, to: 0.5 };
            var bh = build([hel], null, ctx);
            return { kind: 'half', colour: cols[0].name, zones: bh.zones, skipped: bh.skipped, parts: ['left side', 'right side'], label: (low ? 'bottom' : 'top') + ' half of the sides' };
        }
        // "make the front fenders yellow" / "paint the rear quarters red": the front 22% / rear 24% of both sides
        var fq = /\b(front fenders?|rear quarters?|rear quarter panels?|quarter panels?|fenders?)\b/.exec(t);
        if (fq && cols.length === 1 && /\b(make|paint|put|give|turn|colou?r|set)\b/.test(t) && !mentionsPart(text)) {
            var rearQ = /rear|quarter/.test(fq[1]), bq = build([{ id: rearQ ? 'rear_quarter' : 'front_fender', colour: cols[0].hex }], null, ctx);
            return { kind: rearQ ? 'quarter' : 'fender', colour: cols[0].name, zones: bq.zones, skipped: bq.skipped, parts: ['left side', 'right side'], label: rearQ ? 'rear quarters' : 'front fenders' };
        }
        if (!/\b(add|put|give me|give it|draw|paint|with)\b/.test(t)) return null;
        var kind = /\b(pin ?stripes?)\b/.test(t) ? 'pinstripe' : (/\b(centre|center|racing) stripes?\b/.test(t) ? 'centre' : (/\bbelt ?line (stripe|line)s?\b/.test(t) ? 'belt' : (/\b(side |body )?stripes?\b/.test(t) ? 'stripe' : null)));
        if (!kind) return null;
        var named = []; PART_WORDS.forEach(function (pw) { if (['hood', 'roof', 'trunk'].indexOf(pw[0]) !== -1 && pw[1].test(t.trim())) named.push(pw[0]); });
        if (named.length && kind !== 'pinstripe') kind = 'centre';                       // "add a red stripe to the hood" = a stripe down the middle of the hood
        var col = cols[0] || { name: kind === 'pinstripe' ? 'white' : 'red', hex: kind === 'pinstripe' ? COLOURS.white : COLOURS.red };
        var el = kind === 'pinstripe' ? { id: 'pinstripe', colour: col.hex, at: 0.64, width: 0.03 } : (kind === 'centre' ? { id: 'centre_stripe', colour: col.hex, width: 0.14, only: named } : (kind === 'belt' ? { id: 'belt_stripe', colour: col.hex } : { id: 'side_stripe', colour: col.hex, from: 0.70, to: 0.79 }));
        var thin = /\b(thin|thinner|fine|narrow|slim)\b/.test(t), wide = /\b(wide|thick|fat|bold|big)\b/.test(t);
        if (el.width) el.width = el.width * (thin ? 0.6 : (wide ? 1.5 : 1)); if (kind === 'stripe') { el.to = el.from + 0.09 * (thin ? 0.6 : (wide ? 1.6 : 1)); }
        var built = build([el], null, ctx);
        return { kind: kind, colour: col.name, zones: built.zones, skipped: built.skipped, parts: kind === 'centre' ? (named.length ? named : ['hood', 'roof', 'trunk']) : ['left side', 'right side'], label: ({ pinstripe: 'pinstripe', centre: 'centre stripe', belt: 'beltline stripe', stripe: 'side stripe' })[kind] };
    }
    // ------------------------------------------------------------------ COMPOUND ORDERS -> a LAYER STACK (WP C 2026-10-03)
    // "matte black with orange pearl flakes", "pearl then pink pearl", "gloss red with a carbon fiber hood", "white pearl with pink pearl stripes", "a gold sunburst on the hood":
    // before this every entry point returned ONE layer (one finish, one colour, one look query) and the second layer was lost. compoundPlan(text) -> { layers, zones } where the zones are emitted
    // BOTTOM to TOP (add_zone puts each new zone on top, and the LOWER zone index wins overlaps): body base (finish + buyer colour, plus its spec_patterns / coloured coat as second_base),
    // then part-bound layers (region.part), then stripes, then graphics. Zones never blend: a spec layer on the same pixels as a colour layer is merged INTO that zone (spec_patterns / second_base), never
    // stacked as a color "source" zone (that would show the template art, Codex L7 T29). No colour named = the buyer keeps their paint: color "source" with the Foundation finish of the sheen.
    // Unknown look words go to the catalogue (SpbAIAtlas spec / pattern names, every word must match); anything still unknown -> null (the older single-layer path answers it): never guessed.
    var CP_FIN = [['candy apple', 'base::candy', 'candy'], ['mirror chrome', 'base::chrome', 'chrome'], ['pearlescent', 'base::pearl', 'pearl'], ['metallic', 'base::metallic', 'metallic'], ['chrome', 'base::chrome', 'chrome'], ['pearl', 'base::pearl', 'pearl'], ['candy', 'base::candy', 'candy'], ['matte', 'base::matte', 'matte'], ['matt', 'base::matte', 'matte'], ['flat', 'base::matte', 'matte'], ['satin', 'base::satin', 'satin'], ['glossy', 'base::gloss', 'gloss'], ['gloss', 'base::gloss', 'gloss'], ['shiny', 'base::gloss', 'gloss'], ['wet look', 'base::gloss', 'gloss'], ['wet', 'base::gloss', 'gloss'], ['rough', 'base::matte', 'matte']];      // MSR-FIX-B: wet = gloss
    var CP_FOUND = { matte: 'base::f_soft_matte', satin: 'base::f_clear_satin', gloss: 'base::f_soft_gloss', pearl: 'base::f_pearl', candy: 'base::f_candy', metallic: 'base::f_metallic', chrome: 'base::f_chrome' };
    // spec textures: the spec pattern id, the coat finish a COLOURED texture gets ("orange pearl flakes" = an orange pearl coat + the flake spec), the family tag
    var CP_TEX = [[/\bholographic (flakes?|glitter|sparkles?)\b/, 'holographic_flake', 'base::metallic', 'flake'], [/\b(chameleon|colou?r ?shift) (flakes?|pearl)\b/, 'spec_chameleon_flake', 'base::pearl', 'flake'],
        [/\bpearl (flakes?|dust|sparkles?|flecks?|specks?)\b/, 'pearl_micro', 'base::pearl', 'pearl'], [/\b(metal ?flakes?|metalflakes?|flakes?|glitter|sparkles?|sparkly|flecks?)\b/, 'gold_flake', 'base::xirallic', 'flake'],
        [/\bbrushed( metal| aluminum| aluminium| steel)?\b/, 'brushed_linear_cool', 'base::metallic', 'brushed'], [/\b(engine turned|engine turn|guilloche|jeweled|jewelled)\b/, 'guilloche_sunray', 'base::metallic', 'sunray']];
    var CP_GFX = [[/\b(sun ?burst|star ?burst|sun ?rays?|rays)\b/, 'rays'], [/\blightning( bolts?)?\b/, 'lightning'], [/\bchevrons?\b/, 'chevrons'], [/\bspeed lines?\b/, 'speed_lines'], [/\b(halftone|polka dots?|dots)\b/, 'dots'], [/\bwaves\b/, 'waves'], [/\b(sonic )?rings\b/, 'rings']];
    var CP_SEP = /\s*(?:,|\band then\b|\bthen\b|\btopped with\b|\blayered with\b|\bwith\b|\bplus\b|\band\b|\bover\b|\bunder\b)\s*/;
    var CP_FILL = ' a an the that of some my it its me i id like want wanted would love please make give get put use keep paint do can could you also too just only on top base coat coats layer layers controls control overlay body car truck vehicle panel panels every each full whole entire everything all over in to for and change changed set recolor recolour exclusively recolourable recolorable finish nice cool little bit fine big bold thin thick lots lot tiny small subtle effect effects look paint job spec specs shine sheen texture textured wet smooth soft hard rich clean loud quiet sick dope crazy wild mean classy ';
    function cpScopeText(s) {
        return String(s || '').toLowerCase()
            .replace(/\b(?:and\s+)?(?:leave|keep|preserve)\s+(?:(?:all|every|the|remaining|other)\s+)*(?:rest|other panels?|remaining panels?|other paint|every other panel|all other paint)\b[^.;,]*/g, ' ')
            .replace(/\b(?:and\s+)?nothing else\b[^.;,]*/g, ' ')
            .replace(/\b(?:and\s+)?do not touch\b[^.;,]*/g, ' ')
            .replace(/\bkeep that base\b/g, ' ')
            .replace(/\s+/g, ' ').trim();
    }
    function cpWholeBody(s) {
        return /\b(?:body|whole\s+car|entire\s+car|full\s+(?:car|vehicle)|entire\s+vehicle|all\s+over|overall|all\s+body\s+panels?|every\s+panel|every\s+body\s+panel|the\s+car|my\s+car|this\s+car|a\s+\w+\s+car|scheme|livery|paint\s+job)\b/.test(cpScopeText(s));
    }
    function cpCarbonish(id) { return /carbon/.test(id); }
    function cpSeg(s) {
        var o = { text: s, cols: parseColours(s), fin: null, tex: null, look: null, gfx: null, el: null, parts: [], unknown: [] }, rest = ' ' + s + ' ';
        PART_WORDS.forEach(function (pw) { var m = pw[1].exec(rest); if (m) { o.parts.push(pw[0]); rest = rest.replace(m[0], ' '); } });
        var sm = /(?<!left )(?<!right )(?<!driver )(?<!passenger )\b(sides?|doors?)\b/.exec(rest); if (sm) { o.parts.push('left side', 'right side'); rest = rest.replace(sm[0], ' '); }
        CP_GFX.some(function (g) { var m = g[0].exec(rest); if (m) { o.gfx = g[1]; rest = rest.replace(m[0], ' '); return true; } return false; });
        var em = /\b(pin ?stripes?|(racing|centre|center) stripes?|stripes?|lower band|rocker band|beltline stripe)\b/.exec(rest);
        if (em) { o.el = /pin/.test(em[1]) ? 'pinstripe' : (/racing|centre|center/.test(em[1]) ? 'centre_stripe' : (/band/.test(em[1]) ? 'lower_band' : (/belt/.test(em[1]) ? 'belt_stripe' : 'stripes'))); rest = rest.replace(em[0], ' '); }
        CP_TEX.some(function (x) { var m = x[0].exec(rest); if (m) { o.tex = { id: x[1], coat: x[2], fam: x[3], word: m[0].trim() }; rest = rest.replace(m[0], ' '); return true; } return false; });
        var lk = null, lw = 0; Object.keys(LOOK_CURATED).forEach(function (k) { var e = LOOK_CURATED[k]; if (!e.zone.pattern && !/^(fire|flames?|phoenix|blowtorch|inferno|galaxy|nebula|cosmic|space|holographic|hologram|holo|holographic foil|chameleon|colou?r shift|colorshift|color flip|chromaflair|dichroic|prism|prizm|iridescent|diamond plate|tread plate|treadplate)$/.test(k)) return; var re = new RegExp('(^| )' + k + '( |$)'); if (re.test(rest) && k.length > lw) { lw = k.length; lk = k; } });
        if (lk) { o.look = { word: lk, e: LOOK_CURATED[lk] }; rest = rest.replace(new RegExp('(^| )' + lk + '( |$)'), ' '); if (/^(fiber|fibre|weave)$/.test((rest.trim().split(' ')[0] || ''))) rest = rest.replace(/\b(fiber|fibre|weave)\b/, ' '); }
        o.cols.forEach(function (c) { rest = rest.replace(new RegExp('(^| )' + c.name + '( |$)'), ' '); });
        CP_FIN.some(function (f) { var re = new RegExp('(^| )' + f[0] + '( |$)'); if (re.test(rest)) { o.fin = { key: f[1], fam: f[2] }; rest = rest.replace(re, ' '); return true; } return false; });
        if (!o.fin && o.look && /^(pearl|pearlescent|candy|metallic)$/.test(o.look.word)) { o.fin = { key: o.look.e.zone.finish, fam: o.look.word === 'pearlescent' ? 'pearl' : o.look.word }; o.look = null; }
        var cw = {}; o.cols.forEach(function (c) { c.name.split(' ').forEach(function (w) { cw[w] = 1; }); });
        rest.split(' ').forEach(function (w) { if (w.length > 1 && !cw[w] && !/^[0-9]+$/.test(w) && CP_FILL.indexOf(' ' + w + ' ') === -1 && LOOK_STOP.indexOf(' ' + w + ' ') === -1) o.unknown.push(w); });
        return o;
    }
    // a word the curated lists do not know: the catalogue's spec / paint pattern names (every word must be in the name; never a guess)
    function cpCatalogue(words) {
        var AT = window.SpbAIAtlas; if (!AT || !AT.ready || !AT.ready() || !words.length) return null;
        var q = words.join(' '), best = null, bs = -1;
        ['spec', 'pattern'].forEach(function (ty) {
            var rows = []; try { rows = AT.find({ query: q, type: ty, limit: 12 }) || []; } catch (e) { rows = []; }
            rows.forEach(function (r) { var nm = String(r.name || r.n || '').toLowerCase(); if (!words.every(function (w) { return nm.indexOf(w) !== -1; })) return; var sc = 100 - nm.length + (r.quality == null ? 40 : r.quality) * 0.3 + (ty === 'spec' ? 5 : 0) + (ty === 'pattern' && /\b(marble|marbl\w*|splatter|checker\w*|plaid|tartan|paisley|camo\w*|tiger|zebra|leopard|giraffe|flames?|tie dye|swirls?|stars)\b/.test(q) ? 30 : 0);     if (sc > bs) { bs = sc; best = { type: ty, id: String(r.key || r.k || r.id).replace(/^(spec|pattern)::/, ''), name: r.name || r.n }; } });
        });
        return best;
    }
    function compoundPlan(text) {
        text = nz(text);
        var raw = String(text || ''), t = norm(raw), scopeText = cpScopeText(t);
        if (!t || t.length < 4 || /[?]/.test(raw) || /^(what|why|how|which|should|would|could|is|are|does|do you|can you tell|tell me|show me|any|suggest|recommend)\b/.test(t)) return null;
        if (/\bthe (one|1|first|second|third|last|other one|same one)\b/.test(t)) return null;
        if (/\b(lower|upper|bottom|top|front|rear|back) (half|third|end|edge|portion|section)\b|\bhalf (and|of) the\b|\bfade[sd]? (in|out|to|into)\b|\bfading\b/.test(t)) return null;      // MSR-FIX-B cp: no named part / gradient for it      // MSR-FIX-B cp: "i want the one with the sparkle" points at a shown suggestion (advisor follow-up), not a new stack
        if (IDEA_RE.test(t) || VAGUE_RE.test(t) || LAYER_WORDS.some(function (lw) { return lw[1].test(' ' + t + ' '); }) || /\b(liver(y|ies)|scheme|retro|old school|throwback|theme|two tone|instead|remove|undo)\b/.test(t)) return null;
        // "make the black matte and the yellow chrome", "i want the black to be flat": a colour that is already ON the car is the TARGET (SpbProEdit's job), not a new base
        if (parseColours(raw).some(function (c) { return new RegExp('\\b(the|all|my|that|this)( (the|my))? ' + c.name + '( (parts?|areas?|bits?|paint|colou?r))?( (to|and|is|are|should|matte|matt|flat|satin|gloss|glossy|shiny|chrome|pearl|pearlescent|candy|metallic|look|be|into|,)\\b|$)').test(t); })) return null;
        var scopedPartAsk = (/\b(?:only|just|exclusively)\b/.test(t) || scopeText !== t) && PART_WORDS.some(function (pw) { return pw[1].test(t); }) && (parseColours(raw).length > 0 || CP_FIN.some(function (f) { return new RegExp('\\b' + f[0] + '\\b').test(t); }) || Object.keys(LOOK_CURATED).some(function (k) { return new RegExp('(^| )' + k + '( |$)').test(t); }));
        if (!/\b(with|then|plus|topped|layered|over|under|and)\b|\bon (a|an |the |my )?([a-z]+ ){1,3}(car|truck|body|vehicle)\b/.test(t) && !CP_GFX.some(function (g) { return g[0].test(t); }) && !scopedPartAsk) return null;
        // "a brushed silver hood on a black car": the car colour is the base
        var pre = cpScopeText(String(raw).toLowerCase()).replace(/[^a-z0-9#,]+/g, ' ').replace(/\s*,\s*/g, ' , ').replace(/\s+/g, ' ').trim(), onCar = /\bon (?:a |an |the |my )?((?:[a-z]+ ){0,3})(car|truck|body|vehicle)\b/.exec(pre), segs = [];
        if (onCar && onCar[1].trim()) { segs.push(onCar[1].trim()); pre = pre.replace(onCar[0], ' '); }
        else { var onCol = /\bon (?:a |an )?((?:matte |matt |satin |gloss |glossy |metallic |pearl |candy |chrome )?([a-z]+(?: [a-z]+)?))(?= with | and | , |$)/.exec(pre); if (onCol && parseColours(onCol[2]).length && parseColours(onCol[2])[0].name === onCol[2]) { segs.push(onCol[1].trim()); pre = pre.slice(0, onCol.index) + ' , ' + pre.slice(onCol.index + onCol[0].length); } }      // MSR-FIX-B cp
        pre.split(CP_SEP).forEach(function (s) { s = s.trim(); if (s) segs.push(s); });
        segs = segs.filter(function (sg) { return !/^(no|not|without|nothing|never|minus)\b/.test(sg); });      // MSR-FIX-B cp: a negation is a constraint, never a layer
        var P = segs.map(cpSeg), layers = [], base = null, bare = 0, unknown = [];
        P.forEach(function (s) { if (s.unknown.length) { var hit = cpCatalogue(s.unknown); if (hit) { if (hit.type === 'spec') s.tex = { id: hit.id, coat: 'base::metallic', fam: 'catalogue', word: hit.name }; else s.look = { word: hit.name, e: { label: hit.name, zone: { finish: 'base::gloss', pattern: { id: hit.id, opacity: 80, scale: 1 } }, colour: 'zone' } }; s.unknown = []; } else unknown = unknown.concat(s.unknown); } });
        if (unknown.length) return null;
        // A material named on a part owns the following texture too: "matte black on the roof only with fine hex" is one roof stack.
        var partBase = P[0], partTexture = P.slice(1).filter(function (s) { return s.tex || s.look; })[0];
        if (partBase && partBase.parts.length && (partBase.cols.length || partBase.fin || partBase.look) && partTexture) {
            var scopedBase = { kind: 'base', colour: partBase.cols[0] || null, fin: partBase.fin, look: partTexture.look || partBase.look, specs: [], coat: null, parts: partBase.parts.slice() };
            if (partTexture.tex) scopedBase.specs.push(partTexture.tex);
            var scopedPlan = cpCompile([], scopedBase);
            if (scopedPlan && scopedPlan.zones && scopedPlan.zones.length) {
                var scopedZone = scopedPlan.zones[0]; if (partBase.fin) scopedZone.finish = partBase.fin.key; if (partBase.cols[0]) scopedZone.color = partBase.cols[0].hex;
                scopedZone.name = capital((partBase.fin ? partBase.fin.fam + ' ' : '') + (partBase.cols[0] ? cn(partBase.cols[0].hex) + ' ' : '') + (partTexture.look ? partTexture.look.word : partTexture.tex.word) + ' ' + partBase.parts.join(' + '));
                scopedPlan.layers = ['base']; scopedPlan.parts = partBase.parts.slice(); scopedPlan.label = 'look (base and texture together on ' + partBase.parts.join(' + ') + ')'; scopedPlan.desc = [scopedZone.name.toLowerCase()];
                return scopedPlan;
            }
        }
        P.forEach(function (s) { if (s.cols.length && !s.fin && !s.tex && !s.look && !s.gfx && !s.el && !s.parts.length) bare++; });
        if (bare >= 2 || (findPalette(raw) && !P.some(function (s) { return s.tex || s.gfx || s.look; }))) return null;      // "red white and blue", "black and gold": a colour scheme, not a stack
        var last = null, lost = false;
        P.forEach(function (s, i) {
            var col = s.cols[0] || null;
            if (s.gfx) { last = { kind: 'graphic', gfx: s.gfx, colour: col, fin: s.fin, parts: s.parts.slice() }; layers.push(last); return; }
            if (s.el) { last = { kind: 'element', el: s.el, colour: col, colour2: s.cols[1] || null, fin: s.fin, tex: s.tex, parts: s.parts.slice() }; layers.push(last); return; }
            if (s.parts.length) {
                if (!col && !s.fin && !s.tex && !s.look) {
                    // "pearl white base then pink pearl over it on the hood": the coat just named belongs to that part, not to the whole body
                    if (last === base && base && base.coatSeg) { var cs = base.coatSeg; base.coat = null; base.coatSeg = null; if (cs.tex) base.specs = base.specs.filter(function (x) { return x !== cs.tex; }); last = { kind: 'part', parts: s.parts.slice(), colour: cs.cols[0] || null, fin: cs.fin || (cs.tex ? null : { key: 'base::pearl', fam: 'pearl' }), tex: cs.tex, look: cs.look }; layers.push(last); return; }
                    if (last && last.kind !== 'base') s.parts.forEach(function (p) { if (last.parts.indexOf(p) === -1) last.parts.push(p); }); else lost = true; return;      // MSR-FIX-B cp: else the part was dropped
                }
                last = { kind: 'part', parts: s.parts.slice(), colour: col, fin: s.fin, tex: s.tex, look: s.look }; layers.push(last); return;
            }
            if (!col && !s.fin && !s.tex && !s.look) return;
            if (s.look && !s.tex && !base) { base = { kind: 'base', colour: col, fin: s.fin, look: s.look, specs: [], coat: null, parts: [] }; layers.unshift(base); last = base; return; }
            if (!base) { base = { kind: 'base', colour: null, fin: null, look: null, specs: [], coat: null, parts: [] }; layers.unshift(base); }
            last = base;
            if (s.tex && col && !base.colour && !base.coat && !/\b(over|under)\b/.test(t) && (s.tex.fam === 'brushed' || s.tex.fam === 'sunray' || /hammer|brush|anodi|knurl|machin|forged|billet/i.test(s.tex.word || '') || (i === 0 && s.tex.fam === 'catalogue') || (s.text.indexOf(String(s.tex.word || '').split(' ')[0]) !== -1 && s.text.indexOf(String(s.tex.word || '').split(' ')[0]) < s.text.indexOf(col.name)))) { base.specs.push(s.tex); base.colour = col; if (s.fin && !base.fin) base.fin = s.fin; return; }      // MSR-FIX-B cp: metal colour = base colour
            if (s.tex && s.look) { if (!base.look && s.cols.length <= 1) base.look = s.look; else { lost = true; return; } }      // MSR-FIX-B cp
            if (s.tex) { base.specs.push(s.tex); if (i > 0) base.coatSeg = s; if (col) base.coat = { key: s.tex.coat, colour: col, strength: s.tex.fam === 'pearl' ? 45 : 35, what: s.tex.word, tex: true }; else if (s.fin && !base.fin) base.fin = s.fin; return; }
            if (i > 0 && s.look && col && (base.coat || base.specs.length)) { if (!base.look && cpDark(col.hex)) { base.look = s.look; return; } lost = true; return; }      // MSR-FIX-B cp
            if (i === 0 || (!base.colour && !base.fin)) { if (col && !base.colour) base.colour = col; if (s.fin && !base.fin) base.fin = s.fin; if (s.look) base.look = s.look; return; }
            if (s.look) { if (!base.look && (!col || cpDark(col.hex))) { base.look = s.look; return; } lost = true; return; }      // MSR-FIX-B cp: "pink and black camo", "hot pink with a splatter of black": the pattern used to become a pearl COAT and vanish
            if (col) { base.coat = { key: s.fin ? s.fin.key : 'base::pearl', colour: col, strength: 45, what: (s.fin ? s.fin.fam : 'pearl') }; base.coatSeg = s; } else if (s.fin) base.fin = s.fin;
        });
        if (lost) return null;      // the advisor's stack planner (pattern layer + colour adjust) answers it instead
        var named = layers.length + (base && base.specs.length ? 1 : 0) + (base && base.coat && !base.specs.length ? 1 : 0);
        var exclusivePart = /\b(?:only|just|exclusively)\b/.test(t) || scopeText !== t, explicitWhole = cpWholeBody(scopeText), needsTextureAdvice = /\b(?:pattern|texture|weave|flakes?|glitter|sparkles?|scales?|cells?|spec|shine)\b/.test(t), scopedSingle = exclusivePart && !explicitWhole && !needsTextureAdvice && layers.length === 1 && layers[0].kind === 'part' && P.some(function (s) { return s.parts.length && (s.cols.length || s.fin || s.tex || s.look); });
        if (!explicitWhole && /\b(?:pattern|texture)\b/.test(t) && PART_WORDS.some(function (pw) { return pw[1].test(t); }) && !P.some(function (s) { return s.cols.length && s.fin; })) return null;      // explicit texture advice without a named base stays with the advisor stack path
        if (!layers.length || (named < 2 && !layers.some(function (l) { return l.kind === 'graphic'; }) && !scopedSingle)) return null;      // a directly requested exclusive named-part finish is a valid one-zone composition
        if (layers.length === 1 && layers[0].kind === 'part' && !layers[0].tex && !scopedSingle) return null;
        var compiled = cpCompile(layers, base);
        var sidesAreTheWholeAskedArea = /\b(?:both|two|left and right|right and left)?\s*sides\b/.test(scopeText) && !explicitWhole;
        if (compiled && (exclusivePart || sidesAreTheWholeAskedArea) && !explicitWhole && compiled.zones) {
            var bodyZone = compiled.zones.filter(function (z) { return z.region && (z.region.everything || z.region.paintable); })[0], partZones = compiled.zones.filter(function (z) { return z.region && z.region.part; });
            if (bodyZone && partZones.length) {
                partZones.forEach(function (z) {
                    z.finish = bodyZone.finish; z.color = bodyZone.color;
                    if (!z.second_base && bodyZone.second_base) z.second_base = JSON.parse(JSON.stringify(bodyZone.second_base));
                    if (!z.pattern && bodyZone.pattern) z.pattern = JSON.parse(JSON.stringify(bodyZone.pattern));
                    if (bodyZone.spec_patterns && bodyZone.spec_patterns.length) z.spec_patterns = (bodyZone.spec_patterns || []).concat(z.spec_patterns || []).slice(0, 5);
                });
                compiled.zones = partZones; compiled.parts = partZones.reduce(function (all, z) { var ps = [].concat(z.region.part); ps.forEach(function (p) { if (all.indexOf(p) === -1) all.push(p); }); return all; }, []);
                compiled.layers = ['base']; compiled.label = 'look (all layers only on ' + compiled.parts.join(' + ') + ')'; compiled.desc = partZones.map(function (z) { return String(z.name || '').toLowerCase(); });
            }
        }
        return compiled;
    }
    function cpDark(hex) { var c = hexRgb(hex); return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) < 110; }
    // a coloured FLAKE coat is a uniform blend in the paint (measured in-app 2026-10-03: orange pearl at 45% turned matte black into flat BROWN, no flakes visible); the sparkle lives in the spec pattern,
    // so on a dark base the coat stays a faint cast (15%) and the base still reads black; on mid / light bases 10 points under the coat default
    function cpFlakeStrength(col, dflt) { return /^#[0-9a-f]{6}$/i.test(String(col || '')) && cpDark(col) ? 15 : Math.max(15, dflt - 10); }
    function cpSpec(tex) { return { id: tex.id, opacity: 70, scale: 1 }; }
    function cpCompile(layers, base) {
        var zones = [], skipped = [], parts = [], desc = [];
        function addParts(ps) { ps.forEach(function (p) { if (parts.indexOf(p) === -1) parts.push(p); }); }
        var bCol = base && base.colour ? base.colour.hex : null, bFinFam = base && base.fin ? base.fin.fam : (base && base.look ? null : 'gloss');
        var bFin = base ? (base.look ? base.look.e.zone.finish : (bCol ? (base.fin ? base.fin.key : 'base::gloss') : CP_FOUND[bFinFam] || 'base::f_soft_gloss')) : null;
        if (base) {
            var z = { name: (base.look ? base.look.e.label + ' ' : '') + (base.fin ? capital(base.fin.fam) + ' ' : '') + (bCol ? cn(bCol) + ' ' : '') + (base.parts && base.parts.length ? base.parts.join(' + ') : 'body') + ' base', finish: bFin, color: bCol || (base.look && base.look.e.colour === 'zone' && base.look.e.dark ? base.look.e.dark : 'source'), region: base.parts && base.parts.length ? { part: base.parts.length === 1 ? rp(base.parts[0]) : base.parts.map(rp) } : { everything: true, paintable: true } };
            if (base.look && base.look.e.zone.pattern) z.pattern = JSON.parse(JSON.stringify(base.look.e.zone.pattern));
            if (base.look && cpCarbonish(base.look.word)) z.spec_patterns = [{ id: 'spec_carbon_3k_fine', opacity: 60, scale: 1 }];
            if (base.specs.length) z.spec_patterns = (z.spec_patterns || []).concat(base.specs.map(cpSpec)).slice(0, 5);
            if (base.coat) z.second_base = { id: base.coat.key, color: base.coat.colour.hex, strength: base.coat.tex ? cpFlakeStrength(z.color, base.coat.strength) : base.coat.strength };
            z.name = capital(z.name.trim()) + (base.coat ? ' + ' + cn(base.coat.colour.hex) + ' ' + base.coat.what + ' coat' : '') + (base.specs.length && !base.coat ? ' + ' + base.specs.map(function (x) { return x.word; }).join(' + ') : '');
            zones.push(z); desc.push(z.name.replace(/ body base/, ' base').toLowerCase());
        }
        layers.forEach(function (l) {
            if (l.kind !== 'part') return;
            var lk = l.look ? l.look.e : null, col = l.colour ? l.colour.hex : (lk && lk.colour === 'zone' && lk.dark ? lk.dark : bCol), fin = l.fin ? l.fin.key : (lk ? lk.zone.finish : (base && bCol && base.fin ? base.fin.key : 'base::gloss'));
            if (!col) { col = 'source'; fin = CP_FOUND[l.fin ? l.fin.fam : (bFinFam || 'gloss')] || 'base::f_soft_gloss'; }
            var pz = { name: capital(((l.fin ? l.fin.fam + ' ' : '') + (col !== 'source' && !(lk && lk.colour === 'own') ? cn(col) + ' ' : '') + (lk ? lk.label.toLowerCase() + ' ' : '') + (l.tex ? l.tex.word + ' ' : '')).trim() + ' ' + l.parts.join(' + ')), finish: fin, color: lk && lk.colour === 'own' && !l.colour ? 'finish' : col, region: { part: l.parts.length === 1 ? rp(l.parts[0]) : l.parts.map(rp) } };
            if (lk && lk.zone.pattern) pz.pattern = JSON.parse(JSON.stringify(lk.zone.pattern));
            if (l.look && cpCarbonish(l.look.word)) pz.spec_patterns = [{ id: 'spec_carbon_3k_fine', opacity: 60, scale: 1 }];
            if (l.tex) { pz.spec_patterns = (pz.spec_patterns || []).concat([cpSpec(l.tex)]); if (l.colour && (!base || bCol !== l.colour.hex || l.fin == null)) { pz.color = bCol || 'source'; if (pz.color === 'source') pz.finish = CP_FOUND[bFinFam || 'gloss']; else pz.finish = base && base.fin ? base.fin.key : 'base::gloss'; pz.second_base = { id: l.tex.coat, color: l.colour.hex, strength: cpFlakeStrength(pz.color, l.tex.fam === 'pearl' ? 45 : 35) }; } }
            zones.push(pz); addParts(l.parts); desc.push(pz.name.toLowerCase());
        });
        layers.forEach(function (l) {
            if (l.kind !== 'element') return;
            var dflt = bCol && !cpDark(bCol) ? '#111113' : '#f4f4f1', col = l.colour ? l.colour.hex : (l.fin && l.fin.fam === 'chrome' ? '#c3c7cc' : dflt), fin = l.fin ? l.fin.key : 'base::gloss';
            var tops = l.parts.filter(function (p) { return ['hood', 'roof', 'trunk'].indexOf(p) !== -1; }), el;
            if (l.el === 'centre_stripe' || (l.el === 'stripes' && tops.length)) el = { id: 'centre_stripe', colour: col, width: 0.14, only: tops };
            else if (l.el === 'stripes') el = { id: 'twin_stripes', colour: col, colour2: l.colour2 ? l.colour2.hex : col, at: 0.5 };
            else if (l.el === 'pinstripe') el = { id: 'pinstripe', colour: col, at: 0.64, width: 0.03 };
            else el = { id: l.el, colour: col };
            var b = build([el], null, { paint: fin, trim: fin, scale: 1 });
            b.zones.forEach(function (z) { if (l.tex) z.spec_patterns = [cpSpec(l.tex)]; if (l.fin) z.name = capital(l.fin.fam) + ' ' + z.name.charAt(0).toLowerCase() + z.name.slice(1); zones.push(z); });
            b.skipped.forEach(function (s) { skipped.push(s); });
            addParts(el.id === 'centre_stripe' ? (tops.length ? tops : ['hood', 'roof', 'trunk']) : ['left side', 'right side']); desc.push((l.fin ? l.fin.fam + ' ' : '') + cn(col) + ' ' + ({ centre_stripe: 'centre stripe', twin_stripes: 'stripes', pinstripe: 'pinstripe' }[el.id] || el.id.replace(/_/g, ' ')));
        });
        layers.forEach(function (l) {
            if (l.kind !== 'graphic') return;
            var col = l.colour ? l.colour.hex : (!bCol || cpDark(bCol) ? '#d7a72b' : '#111113'), o = { id: l.gfx + '_graphic', colour: col };
            if (l.parts.length) o.part = l.parts.length === 1 ? rp(l.parts[0]) : l.parts.map(rp);
            if (l.gfx === 'rays') { o.n = 22; o.duty = 0.45; if (!l.parts.length || l.parts.some(function (p) { return /side/.test(p); })) { o.cu = 0.15; o.cv = 0.55; } }
            var b = build([o], null, { paint: l.fin ? l.fin.key : 'base::gloss', trim: 'base::chrome', scale: 1 });
            b.zones.forEach(function (z) { zones.push(z); }); b.skipped.forEach(function (s) { skipped.push(s); });
            addParts(l.parts.length ? l.parts : ['left side', 'right side']); desc.push(cn(col) + ' ' + ({ rays: 'sunburst' }[l.gfx] || l.gfx.replace(/_/g, ' ')) + (l.parts.length ? ' on the ' + l.parts.join(' and ') : ''));
        });
        return { kind: 'compound', layers: layers.map(function (l) { return l.kind; }), zones: zones, skipped: skipped, parts: parts, colour: 'layered', label: 'look (bottom to top: ' + desc.join(', then ') + ')', desc: desc };
    }
    function describePlan(plan) {
        if (!plan || !plan.palette) return '';
        var pal = plan.palette, names = [], seen = {}, bl = plan.baseLook, fin = plan.ctx && plan.ctx.paint ? plan.ctx.paint.replace('base::', '') : 'gloss', trim = plan.ctx && plan.ctx.trim === 'base::chrome';
        (bl ? ['a', 'b'] : ['base', 'a', 'b']).forEach(function (k) { if (!pal[k]) return; var n = nameColour(pal[k]); if (!seen[n]) { seen[n] = 1; names.push(n); } });
        var cs = bl ? (String(bl.label || 'special').toLowerCase() + ' body with ' + (names.join(' and ') || 'matching') + ' accents') : (names.length > 1 ? names[0] + ' with ' + names.slice(1).join(' and ') : (names[0] || 'your colours'));
        var fw = fin === 'matte' ? 'flat paint' : (fin === 'satin' ? 'satin paint' : (fin === 'gloss' ? 'gloss paint' : fin.replace(/_/g, ' ') + ' paint'));
        return cs + (bl ? '' : ', ' + fw) + (trim ? (bl ? ', ' : ' ') + 'with chrome trim' : '');
    }
    // a plain-words list of what the zones do, from the specs (used for honest receipts)
    // MCPSCEN 2026-10-05 (G6 MCP run: the plan said "(f soft matte)" for base::f_soft_matte): the plan names the finish the way the picker does.
    function finLabel(key) {
        var k = String(key || ''), m = /^(base|monolithic|mono)::(.+)$/.exec(k), id = m ? m[2] : k, list = null;
        try { list = (m && m[1] !== 'base') ? (typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : null) : (typeof BASES !== 'undefined' ? BASES : null); var f = (list || []).filter(function (x) { return x.id === id; })[0]; if (f && f.name) return f.name; } catch (e) {}
        return id.replace(/^f_/, '').replace(/_/g, ' ');
    }
    function summarise(specs) {
        var rows = [];
        specs.forEach(function (s) {
            var r = s.region || {}, where = 'everywhere on the body';
            if (r.part || r.island) { var ps = r.part || r.island; where = (Array.isArray(ps) ? ps : [ps]).join(' + '); if (r.band) { var sidey = (Array.isArray(ps) ? ps : [ps]).some(function (q) { return /side/.test(String(q)); }); where += (/len|long|along|front|rear/.test(String(r.band.axis || '')) ? ', ' + Math.round(r.band.from * 100) + '-' + Math.round(r.band.to * 100) + '% from the front' : (sidey ? ', ' + Math.round(r.band.from * 100) + '-' + Math.round(r.band.to * 100) + '% down from the roof-line' : ', a stripe across the middle')); } else if (r.portion) where += ' (' + r.portion + ')'; }
            var col = isHex(s.color) ? nameColour(s.color) : s.color === 'source' ? ((Number(s.hue) || Number(s.saturation) || Number(s.brightness)) ? 'its own colour shifted (' + ['hue', 'saturation', 'brightness'].filter(function (k) { return Number(s[k]); }).map(function (k) { return k + ' ' + (s[k] > 0 ? '+' : '') + s[k]; }).join(', ') + ')' : 'keeps its colour') : s.color === 'finish' ? 'the finish colours' : (s.color || (s.gradient && s.gradient.stops ? 'gradient ' + [].concat(s.gradient.stops).map(function (g) { var c = (g && typeof g === 'object') ? g.color : g; return isHex(c) ? nameColour(c) : String(c || ''); }).join(' → ') : '')),          /* MCPSCEN 2026-10-05: was 'hood - source' */ fin = finLabel(s.finish);
            rows.push((s.name || 'zone') + ': ' + where + ' - ' + col + (fin ? ' (' + fin + ')' : ''));
        });
        return rows;
    }
    window.SpbProDesign = { PALETTES: PALETTES, PRESETS: PRESETS, ELEMENTS: ELEMENTS, COLOURS: COLOURS, nameColour: nameColour, parseColours: parseColours, findPalette: findPalette, recipes: recipes, build: build, presetSteps: presetSteps, offlinePlan: offlinePlan, LOOK_CURATED: LOOK_CURATED, offlineIdeas: offlineIdeas, offlineElement: offlineElement, lookRequest: lookRequest, describePlan: describePlan, offlineSpec: offlineSpec, offlinePart: offlinePart, offlinePartCoverage: offlinePartCoverage, mentionsPart: mentionsPart, refine: refine, presetSteps: presetSteps, SPEC_LOOKS: SPEC_LOOKS, summarise: summarise, compoundPlan: compoundPlan };
})();
