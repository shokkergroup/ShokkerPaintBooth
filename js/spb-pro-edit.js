/* ============================================================================
   SPB PRO EDIT - "change what is ALREADY on the car"   (owner 2026-10-02)
   Most buyers do not paint a car from nothing: they load a livery and say
       "make the black matte" / "make the numbers purple and metallic" / "the yellow, powder coat looking"
   This module is the brain for that: it READS the colours the paint really has (families: black / yellow / navy ...), understands the spoken look
   (powder coat, plasti dip, cerakote, wet look, chrome, pearl ... -> real Foundation finishes), splits a sentence into targets x actions
   and COMPILES them to zone specs: a colour target selects those pixels (region.colors), a look with no new colour changes ONLY the spec
   (Foundation finish + color "source": the paint stays identical), a new colour repaints exactly those pixels.
   The same structured request ({target, look, colour, relative}) is what the online AI sends through the `refinish` tool (compileRequest),
   so the offline parser and the AI share ONE deterministic executor.
   No catalogue, no network.  ES5 only.
   window.SpbProEdit = { plan, compileRequest, resolveColour, familyOf, describe, suggestions, LOOKS, lookFor, fixText }
   ========================================================================== */
(function () {
    'use strict';
    function Dz() { return window.SpbProDesign || {}; }
    function norm(s) { return String(s || '').toLowerCase().replace(/['’`]/g, '').replace(/[^a-z0-9#]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    function cap(s) { s = String(s || ''); return s.charAt(0).toUpperCase() + s.slice(1); }
    function hexRgb(h) { h = String(h || '').replace('#', ''); return [parseInt(h.substr(0, 2), 16) || 0, parseInt(h.substr(2, 2), 16) || 0, parseInt(h.substr(4, 2), 16) || 0]; }
    function rgbHex(c) { function p(n) { n = Math.max(0, Math.min(255, Math.round(n))); return (n < 16 ? '0' : '') + n.toString(16); } return '#' + p(c[0]) + p(c[1]) + p(c[2]); }
    function hsl(hex) {
        var c = hexRgb(hex), r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn, h = 0, s = 0;
        if (d > 0) { s = d / (1 - Math.abs(2 * l - 1)); if (mx === r) h = (g - b) / d + (g < b ? 6 : 0); else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; }
        return { h: h, s: s, l: l, c: d };
    }
    function otherFamilies(cols) {
        cols = cols || []; if (cols.length < 2) return 0; var f = hsl(cols[0]), n = 0;
        for (var i = 1; i < cols.length; i++) { var q = hsl(cols[i]), dh = Math.abs(q.h - f.h); if (dh > 180) dh = 360 - dh; if (!(f.s > 0.45 && q.s > 0.45 && dh <= 18)) n++; }
        return n;
    }
    function fromHsl(h, s, l) {
        h = ((h % 360) + 360) % 360; s = Math.max(0, Math.min(1, s)); l = Math.max(0, Math.min(1, l));
        var c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2, r = 0, g = 0, b = 0;
        if (h < 60) { r = c; g = x; } else if (h < 120) { r = x; g = c; } else if (h < 180) { g = c; b = x; } else if (h < 240) { g = x; b = c; } else if (h < 300) { r = x; b = c; } else { r = c; b = x; }
        return rgbHex([(r + m) * 255, (g + m) * 255, (b + m) * 255]);
    }

    // ------------------------------------------------------------------ colour FAMILIES: the words a person uses for the colours on a livery ("the black", "the yellow", "the navy")
    function familyOf(hex) {
        var q = hsl(hex), h = q.h, s = q.s, l = q.l, ch = q.c;          // chroma (max-min), not HSL saturation: saturation is meaningless at the extremes (#fffefe is "100% saturated")
        if (l < 0.09) return 'black';                         // true black; #252525 and the like are CHARCOAL (a livery often has both)
        if (l > 0.88 && ch < 0.14) return 'white';
        if (ch < 0.07) return l < 0.32 ? 'charcoal' : (l > 0.9 ? 'white' : (l > 0.72 ? 'silver' : 'grey'));
        if (l > 0.8 && ch < 0.2) return 'white';
        if (h < 14 || h >= 346) return l > 0.74 ? 'pink' : 'red';
        if (h < 46 && l < 0.36) return 'brown';
        if (h < 50 && s < 0.5 && l > 0.5) return 'tan';
        if (h < 38) return 'orange';
        if (h < 70) return 'yellow';
        if (h < 165) return 'green';
        if (h < 200) return 'teal';
        if (h < 258) return 'blue';
        if (h < 300) return 'purple';
        return 'pink';
    }
    var PLAIN = { red: 1, orange: 1, yellow: 1, green: 1, blue: 1, purple: 1, pink: 1, black: 1, white: 1, grey: 1, gray: 1, silver: 1, brown: 1, teal: 1, gold: 1, tan: 1, cyan: 1, aqua: 1, turquoise: 1, magenta: 1, violet: 1, beige: 1, bronze: 1, copper: 1, 'hot pink': 1, 'neon green': 1, 'neon yellow': 1, 'neon orange': 1, 'neon pink': 1, 'neon blue': 1, lime: 1, 'lime green': 1, cream: 1, 'off white': 1, platinum: 1, champagne: 1, 'electric blue': 1, 'royal blue': 1, cobalt: 1, 'pepsi blue': 1, 'steel blue': 1, emerald: 1, jade: 1, ruby: 1, scarlet: 1, crimson: 1, lemon: 1, mustard: 1, amber: 1, coral: 1, salmon: 1, peach: 1, rose: 1 };
    var NEAR = { black: ['charcoal'], charcoal: ['black', 'grey'], grey: ['charcoal', 'silver'], silver: ['grey'] };                                   // used without asking (one grey is another grey)
    var NEAR_ASK = { white: ['silver'], red: ['pink', 'orange'], orange: ['yellow', 'red', 'brown'], yellow: ['orange', 'tan'], tan: ['yellow', 'brown'], brown: ['orange', 'tan'], green: ['teal'], teal: ['green', 'blue'], blue: ['teal', 'purple'], purple: ['blue', 'pink'], pink: ['purple', 'red'], silver: ['white'] };      // a different colour: ask first
    // a spoken colour word -> what to look for on the car
    function wantFor(word, hex, qual) {
        var q = hsl(hex), fam = familyOf(hex), band = null;
        if (word === 'gray') fam = 'grey';
        if (['navy', 'midnight blue', 'maroon', 'burgundy', 'wine', 'forest green', 'dark green', 'dark blue', 'dark red', 'dark purple', 'chocolate', 'army green', 'olive', 'indigo', 'plum'].indexOf(word) !== -1) band = 'dark';
        else if (['sky blue', 'baby blue', 'light blue', 'powder blue', 'baby pink', 'light pink', 'light green', 'mint', 'mint green', 'seafoam', 'lavender', 'lilac', 'pastel'].indexOf(word) !== -1) band = 'light';
        else if (!PLAIN[word] && q.l < 0.3 && fam !== 'black') band = 'dark';
        if (qual === 'dark' || qual === 'deep') band = 'dark'; else if (qual === 'light' || qual === 'pale') band = 'light';
        if (word === 'charcoal' || word === 'gunmetal' || word === 'dark grey' || word === 'dark gray') { fam = 'charcoal'; band = null; }
        if (word === 'light grey' || word === 'light gray') { fam = 'silver'; band = null; }
        if (word === 'gold' || word === 'mustard' || word === 'amber' || word === 'lemon') fam = 'yellow';
        if (word === 'bronze' || word === 'copper') fam = 'orange';
        if (word === 'beige' || word === 'sand' || word === 'khaki' || word === 'cream' || word === 'ivory') fam = (word === 'cream' || word === 'ivory') ? 'white' : 'tan';
        return { fam: fam, band: band, hex: hex, word: word };
    }
    function prepPalette(pal) {
        return (pal || []).map(function (c) { var q = hsl(c.hex); return { hex: c.hex, share: Number(c.share_pct != null ? c.share_pct : c.share) || 0, shown: c.shown_pct != null ? Number(c.shown_pct) : null, hidden: (c.hidden_by && c.hidden_by.length) ? c.hidden_by : null, bshare: c.body_share_pct != null ? Number(c.body_share_pct) : null, bshown: c.body_shown_pct != null ? Number(c.body_shown_pct) : null, where: c.where || '', cells: c.cells || [], fam: familyOf(c.hex), l: q.l, s: q.s, h: q.h, name: (Dz().nameColour ? Dz().nameColour(c.hex) : familyOf(c.hex)) }; });
    }
    function bandOk(e, band) { return !band || (band === 'dark' ? e.l < 0.4 : e.l > 0.58); }
    // which of the car's real colours does "the black" / "the navy" / "the yellow" mean?  -> { entries, via, share, label }
    function resolveColour(want, pal) {
        var out = { entries: [], via: 'none', share: 0, label: want.word };
        var keep = pal.filter(function (e) { return e.share >= 0.4; });
        var ex = keep.filter(function (e) { return e.name === want.word || (e.fam === want.fam && bandOk(e, want.band)); });          // the name the helper itself reports ("charcoal", "neon orange") always resolves
        if (!ex.length && want.band) ex = keep.filter(function (e) { return e.fam === want.fam; });            // "the dark blue" on a car whose only blue is a mid blue: that is it
        if (ex.length) out.via = 'exact';
        else {
            var nb = NEAR[want.fam] || [], i;
            for (i = 0; i < nb.length && !ex.length; i++) ex = keep.filter(function (e) { return e.fam === nb[i] && bandOk(e, want.band); });
            if (ex.length) out.via = 'near';
        }
        if (!ex.length) { var na = NEAR_ASK[want.fam] || [], j; for (j = 0; j < na.length && !out.near; j++) { var cand = keep.filter(function (e) { return e.fam === na[j] && bandOk(e, want.band); }); if (cand.length) out.near = cand; } }
        // the colour NAME on the car (navy, gold, burnt orange ...) is how people talk about it, so say that, not the word they typed
        if (ex.length) {
            out.entries = ex; out.share = ex.reduce(function (a, e) { return a + e.share; }, 0);
            out.label = out.via === 'exact' ? want.word : ex[0].name;
            if (out.via === 'exact' && PLAIN[want.word] && ex.length === 1 && ex[0].name !== want.word && familyOf(COLOURS_HEX(ex[0].name)) === want.fam) out.label = want.word;
        }
        return out;
    }
    function COLOURS_HEX(name) { var C = Dz().COLOURS || {}; return C[name] || '#808080'; }

    // ------------------------------------------------------------------ LOOKS: how a surface looks, in the words people use -> a real FOUNDATION finish (spec only; the paint stays) + a plain-words description
    var LOOKS = [
        { id: 'powder coat', label: 'powder coat', words: ['powder coat', 'powdercoat'], found: 'base::f_powder_coat', about: 'a thick, slightly rough powder-coated surface with no gloss' },
        { id: 'wrinkle coat', label: 'wrinkle coat', words: ['wrinkle coat', 'wrinkle finish', 'wrinkle', 'crinkle'], found: 'base::f_powder_coat', shift: { rough: 35, clearcoat: 10 }, about: 'a rougher, wrinkle-textured powder coat' },
        { id: 'plasti dip', label: 'plasti dip', words: ['plasti dip', 'plastidip', 'rubberized', 'rubber coat', 'rubber coated', 'rubber paint', 'rubber', 'dipped'], found: 'base::f_soft_matte', shift: { rough: 30, clearcoat: 40 }, about: 'a dead-flat, rubbery matte with no reflection' },
        { id: 'stealth', label: 'stealth matte', words: ['stealth matte', 'stealth', 'ultra matte', 'super matte', 'dead flat', 'flat black finish', 'no reflection', 'non reflective'], found: 'base::f_soft_matte', shift: { rough: 25, clearcoat: 30 }, about: 'dead-flat matte: nothing reflects' },
        { id: 'cerakote', label: 'cerakote', words: ['cerakote', 'gunkote', 'duracoat', 'gun coat', 'gun finish'], found: 'base::f_soft_matte', about: 'a thin, hard-wearing matte coating' },
        { id: 'matte', label: 'matte', words: ['matte', 'flat', 'chalky', 'chalk', 'velvet', 'suede', 'no shine', 'no gloss', 'not shiny', 'non shiny', 'not glossy', 'low gloss', 'flatten'], found: 'base::f_soft_matte', about: 'no shine: rough surface, dull clearcoat' },
        { id: 'satin', label: 'satin', words: ['satin', 'eggshell', 'semi gloss', 'semi matte', 'low sheen', 'silky', 'soft sheen'], found: 'base::f_clear_satin', about: 'a soft sheen between gloss and matte' },
        { id: 'gloss', label: 'gloss', words: ['gloss', 'glossy', 'shiny', 'high gloss', 'show car', 'showroom', 'clearcoat', 'clear coat', 'clear coated', 'factory paint', 'factory finish'], found: 'base::f_soft_gloss', about: 'a deep, wet-looking gloss' },
        { id: 'wet look', label: 'wet look', words: ['wet look', 'wet paint', 'wet', 'ceramic coating', 'ceramic coated', 'ceramic', 'glassy', 'glass like', 'liquid look', 'mirror gloss', 'dripping wet'], found: 'base::f_gel_coat', about: 'a glass-smooth, wet-looking gloss' },
        { id: 'satin chrome', label: 'satin chrome', words: ['satin chrome', 'brushed chrome', 'soft chrome'], found: 'base::f_satin_chrome', about: 'chrome with a soft satin sheen' },
        { id: 'dark chrome', label: 'dark chrome', words: ['dark chrome', 'smoked chrome', 'gunmetal chrome', 'tinted chrome'], found: 'base::f_dark_chrome', about: 'smoked mirror metal' },
        { id: 'chrome', label: 'chrome', words: ['chrome', 'mirror', 'mirror chrome', 'mirror finish', 'mirrored'], found: 'base::f_chrome', about: 'full metal, perfectly smooth: a mirror' },
        { id: 'plated', label: 'plated metal', words: ['electroplated', 'electroplate', 'plated', 'pvd'], found: 'base::f_chrome', about: 'bright plated metal' },
        { id: 'matte metallic', label: 'matte metallic', words: ['matte metallic', 'satin metallic', 'frosted metal'], found: 'base::f_matte_metallic', about: 'metal with a flat, hazed finish' },
        { id: 'metallic', label: 'metallic', words: ['metallic', 'metal flake', 'metalflake', 'flake', 'sparkle', 'sparkly', 'glitter', 'shimmer', 'shimmery', 'metal', 'reflective', 'light reflecting'], found: 'base::f_metallic', about: 'bright metal under clearcoat' },          // FIRSTTEST 2026-10-04: "reflective" = a bright metallic under clearcoat ("non reflective" stays stealth matte: longest match wins)
        { id: 'satin pearl', label: 'satin pearl', words: ['satin pearl'], found: 'base::f_satin_pearl', about: 'soft pearl with a satin highlight' },
        { id: 'pearl', label: 'pearl', words: ['pearl', 'pearlescent', 'pearly', 'mica'], found: 'base::f_pearl', about: 'a soft pearl sheen under deep clearcoat' },
        { id: 'candy', label: 'candy', words: ['candy', 'candy apple', 'candy paint', 'tinted gloss'], found: 'base::f_candy', about: 'a strong metal glow under deep clearcoat' },
        { id: 'brushed', label: 'brushed metal', words: ['brushed', 'brushed metal', 'brushed aluminum', 'brushed aluminium', 'brushed steel', 'machined', 'bare metal', 'raw aluminum'], found: 'base::f_brushed', about: 'metal with a brushed, rougher surface' },
        { id: 'anodized', label: 'anodized', words: ['anodized', 'anodised', 'anodize'], found: 'base::f_anodized', about: 'an anodized metal oxide finish' },
        { id: 'frosted', label: 'frosted', words: ['frosted', 'frozen', 'icy', 'frost', 'frosty'], found: 'base::f_frozen', about: 'frosted, icy matte metal' },
        { id: 'bead blasted', label: 'bead blasted', words: ['bead blasted', 'bead blast', 'sand blasted', 'sandblasted', 'grit blasted', 'blasted'], found: 'base::f_bead_blast', about: 'an evenly rough bead-blasted metal' },
        { id: 'hammered', label: 'hammered metal', words: ['hammered', 'hammertone', 'hammer tone', 'peened', 'shot peen', 'dimpled'], found: 'base::f_bead_blast', shift: { rough: 12 }, about: 'rough, hammered metal' },
        { id: 'vinyl', label: 'vinyl wrap', words: ['vinyl wrap', 'vinyl', 'wrapped', 'wrap'], found: 'base::f_vinyl_wrap', about: 'a soft satin-matte vinyl wrap' },
        { id: 'enamel', label: 'baked enamel', words: ['baked enamel', 'enamel'], found: 'base::f_baked_enamel', about: 'hard, glossy baked enamel' },
        { id: 'patina', label: 'patina', words: ['patina', 'rusty', 'weathered', 'aged', 'worn', 'oxidized', 'oxidised'], found: 'base::f_matte_metallic', shift: { metal: -60, clearcoat: 40 }, about: 'aged, oxidised metal' },
        { id: 'galvanized', label: 'galvanized', words: ['galvanized', 'galvanised'], found: 'base::f_matte_metallic', shift: { rough: -25 }, about: 'galvanised zinc metal' },
        { id: 'primer', label: 'primer', words: ['primer'], found: 'base::f_soft_matte', about: 'flat primer-style matte' }
    ];
    var LEGACY_LOOKS = { matte: 1, satin: 1, gloss: 1, chrome: 1, 'satin chrome': 1, 'dark chrome': 1, metallic: 1, pearl: 1, candy: 1, brushed: 1, frosted: 1, 'matte metallic': 1 };
    var LOOK_BY_ID = {}; LOOKS.forEach(function (l) { LOOK_BY_ID[l.id] = l; });
    var LOOK_INDEX = []; LOOKS.forEach(function (l) { l.words.forEach(function (w) { LOOK_INDEX.push({ w: w, look: l }); }); }); LOOK_INDEX.sort(function (a, b) { return b.w.length - a.w.length; });
    // a look from a word / phrase ("powder coat", "plasti-dip", "ceramic") - also used by the online refinish tool
    function lookFor(q) {
        var t = ' ' + fixText(q) + ' ', best = null, bl = 0;
        LOOK_INDEX.forEach(function (e) { var w = ' ' + e.w + ' '; if (t.indexOf(w) !== -1 && w.length > bl) { bl = w.length; best = e.look; } });
        return best;
    }

    // ------------------------------------------------------------------ typos + colloquial spellings -> the words above
    // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- part typos + everyday part words ("rooof" / "top of the car" / "bumprs" fell to a whole-car change)
    var PART_TYPOS = [
        [/\br[o0]{3,}fs?\b|\brof\b|\bruf\b|\brooff\b/g, 'roof'], [/\bh[o0]{3,}d\b|\bhod\b/g, 'hood'], [/\btruk\b|\btrnk\b|\btrunck\b|\btrunkk\b/g, 'trunk'], [/\bspoi?l[ie]?e?r\b|\bspolier\b|\bspoilor\b/g, 'spoiler'],
        [/\bbump[ae]?rs\b|\bbumber(s)?\b|\bbumpr(s)?\b|\bbummpers?\b/g, function (m) { return /s$/.test(m) ? 'bumpers' : 'bumper'; }], [/\b(?:the |my )?(?:very )?top of (?:the |my |this )?(?:car|body|vehicle)\b|\bcar ?top\b/g, 'the roof'], [/\b(?:the |my )?(?:back|rear) end\b/g, 'the rear bumper'], [/\b(?:the |my )?front end\b/g, 'the front bumper']
    ];
    function fixParts(text) { var t = String(text || ''); PART_TYPOS.forEach(function (p) { t = t.replace(p[0], p[1]); }); return t; }
    var TYPOS = PART_TYPOS.concat([
        [/\bpowder ?coat(ed|ing)?\b/g, 'powder coat'], [/\bpowder ?coating\b/g, 'powder coat'], [/\bplasti ?-?dip(ped|ping)?\b/g, 'plasti dip'], [/\bplastic dip(ped)?\b/g, 'plasti dip'], [/\bplasty dip\b/g, 'plasti dip'],
        [/\bmatt(e|ed|es)?\b/g, 'matte'], [/\bmate\b/g, 'matte'], [/\bmeta?l+i+c\b|\bmetalic\b|\bmettalic\b|\bmetalick\b/g, 'metallic'], [/\bglos+e?y\b|\bglosy\b/g, 'glossy'], [/\bglos+\b/g, 'gloss'], [/\bglossier\b/g, 'glossier'],
        [/\bchrom(e|ed|y|ey)\b|\bcrome\b|\bchromed\b/g, 'chrome'], [/\bsat+[ie]n(ed)?\b|\bsatan\b/g, 'satin'], [/\bpearl(escent|ish|y)?\b|\bperal\b/g, 'pearl'], [/\bcarbon fib(er|re)\b|\bcarbonfiber\b/g, 'carbon fiber'],
        [/\bcera ?kot(e|ed)\b/g, 'cerakote'], [/\bcerakoted\b/g, 'cerakote'], [/\bwrinkled\b/g, 'wrinkle'], [/\bcandied\b|\bcandy ?paint\b/g, 'candy'], [/\bflakes\b|\bflaked\b/g, 'flake'], [/\bbrush(ed)?\b/g, 'brushed'],
        [/\banodi[sz]ed\b|\banodi[sz]e\b/g, 'anodized'], [/\bplated\b/g, 'plated'], [/\bcolor(s|ed)?\b/g, 'colour'], [/\bcolour(s|ed)?\b/g, 'colour'], [/\bgrey\b/g, 'grey'], [/\bnumbers?'?s?\b/g, 'numbers'], [/\bsponsors?\b/g, 'sponsors'],
        [/\bgloss y\b/g, 'glossy'], [/\bshine y\b/g, 'shiny'], [/\bmatte ?finish\b/g, 'matte'], [/\blooking\b/g, 'look'], [/\blooks like\b/g, 'look like'], [/\bkinda\b|\bkind of\b|\bsort of\b|\bsorta\b/g, ' '], [/\bda\b|\bteh\b|\btha\b/g, 'the'], [/\bwanna\b/g, 'want to'], [/\bplz\b|\bpls\b/g, 'please']
    ]);
    var WORD_TYPOS = { blak: 'black', blck: 'black', blac: 'black', blacl: 'black', wite: 'white', whte: 'white', whit: 'white', yelow: 'yellow', yello: 'yellow', yellw: 'yellow', yelloe: 'yellow', bleu: 'blue', blu: 'blue', gren: 'green', grean: 'green', purpel: 'purple', purle: 'purple', orang: 'orange', ornge: 'orange', pnk: 'pink', gry: 'grey', gray: 'grey', silvr: 'silver', sliver: 'silver', slver: 'silver', redd: 'red', navey: 'navy', nvy: 'navy', mat: 'matte', matt: 'matte', flatt: 'flat', glos: 'gloss', shinny: 'shiny', shiney: 'shiny', metalic: 'metallic', metallics: 'metallic', crome: 'chrome', chrom: 'chrome', satn: 'satin', satan: 'satin', perl: 'pearl', pearls: 'pearl', canday: 'candy', candi: 'candy', chrme: 'chrome', chorme: 'chrome', chromee: 'chrome', chrmoe: 'chrome', numbrs: 'numbers', numbes: 'numbers', nubers: 'numbers', numers: 'numbers', numebrs: 'numbers', nmbers: 'numbers', nunbers: 'numbers', sponsers: 'sponsors', sponcers: 'sponsors', sponsrs: 'sponsors', stipes: 'stripes', stripse: 'stripes', striipes: 'stripes', whtie: 'white', wihte: 'white', whiet: 'white', blakc: 'black', balck: 'black', blck: 'black', yelllow: 'yellow', yeloow: 'yellow', oragne: 'orange', pruple: 'purple', purpul: 'purple', pupple: 'purple', gren: 'green', grene: 'green', golld: 'gold', gld: 'gold', satiin: 'satin', glossey: 'glossy', glosssy: 'glossy', shinney: 'shiny', dulll: 'dull', canndy: 'candy', pearll: 'pearl', pearal: 'pearl' };
    var VOCAB = null, SAFE_WORDS = ' make paint color colour parts panels stripes pinstripes numbers sponsors decals lettering bumper hood spoiler wheels windows mirrors something nothing anything everything colors cannot should please thanks little really actually already another because between around against without within before after beyond better darker lighter brighter bigger smaller shiny metal glossier duller ';
    function dl1(a, b) {                      // Damerau-Levenshtein distance <= 1 ?
        if (a === b) return true; var la = a.length, lb = b.length; if (Math.abs(la - lb) > 1) return false;
        var i = 0; while (i < la && i < lb && a.charAt(i) === b.charAt(i)) i++;
        if (la === lb) { if (a.slice(i + 1) === b.slice(i + 1)) return true; return a.charAt(i) === b.charAt(i + 1) && a.charAt(i + 1) === b.charAt(i) && a.slice(i + 2) === b.slice(i + 2); }
        return la > lb ? a.slice(i + 1) === b.slice(i) : b.slice(i + 1) === a.slice(i);
    }
    function vocab() {
        if (VOCAB) return VOCAB; VOCAB = [];
        var C = Dz().COLOURS || {}; Object.keys(C).forEach(function (k) { if (k.indexOf(' ') === -1 && k.length >= 6) VOCAB.push(k); });
        LOOKS.forEach(function (l) { l.words.forEach(function (w) { if (w.indexOf(' ') === -1 && w.length >= 6) VOCAB.push(w); }); }); ['sponsors', 'numbers', 'stripes', 'powder', 'plasti', 'chrome', 'satin', 'cerakote'].forEach(function (w) { if (w.length >= 6) VOCAB.push(w); });
        return VOCAB;
    }
    function fuzz(t) {
        return t.split(' ').map(function (w) {
            if (WORD_TYPOS[w]) return WORD_TYPOS[w];
            if (w.length < 6 || SAFE_WORDS.indexOf(' ' + w + ' ') !== -1) return w;
            var v = vocab(), hit = null, n = 0, i; for (i = 0; i < v.length; i++) { if (v[i] === w) return w; if (dl1(w, v[i])) { hit = v[i]; n++; } }
            return n === 1 ? hit : w;
        }).join(' ');
    }
    function fixText(text) { var t = norm(text); TYPOS.forEach(function (p) { t = t.replace(p[0], p[1]); }); t = fuzz(t); return t.replace(/\s+/g, ' ').trim(); }

    // ------------------------------------------------------------------ the sentence: clauses, targets, actions
    var PART_WORDS = [['hood', /\b(hood|bonnet)\b/], ['roof', /\broof\b/], ['trunk', /\b(trunk|deck ?lid|rear deck)\b/], ['bed', /\b(truck bed|pickup bed|cargo bed)\b/], ['front bumper', /\b(front bumper|nose)\b/], ['rear bumper', /\b(rear bumper|back bumper|tail)\b/], ['spoiler', /\b(spoiler|wing)\b/], ['left side', /\b(left|driver)s? (side|door|flank)\b/], ['right side', /\b(right|passenger)s? (side|door|flank)\b/]];
    // ROUTER-FIX 2026-10-04 (owner T1: "the black near the rear of the car and back bumper" painted the WHOLE taught areas pink and covered white stripes): a PLACE after a colour
    // ("the black near the rear of the car", "the white on the back of each side") is a SCOPE of that colour, never a target of its own. "part@portion" = a portion of a part (carmap portionBox).
    var PLACES = [
        [/\b(?:back|rear|backs|rears)(?: half| end| part)? (?:of|on) (?:each|both|the|my) sides?\b|\bback of the doors?\b/, ['left side@rear half', 'right side@rear half']],
        [/\bfront(?: half| end| part)? (?:of|on) (?:each|both|the|my) sides?\b/, ['left side@front half', 'right side@front half']],
        [/\b(?:rear|back|tail)(?: half| end| part)? of (?:the |my )?(?:car|truck|vehicle)\b|\b(?:near|at|towards?|around|by|on) the (?:rear|back)(?! (?:bumper|window|glass|wing|spoiler|deck))\b|\b(?:rear|back) end\b/, ['trunk', 'rear bumper', 'left side@rear third', 'right side@rear third']],
        [/\bfront(?: half| end| part)? of (?:the |my )?(?:car|truck|vehicle)\b|\b(?:near|at|towards?|around|by) the front(?! (?:bumper|window|glass))\b|\bfront end\b/, ['hood', 'front bumper', 'left side@front third', 'right side@front third']]
    ];
    var SCOPE_PREP = /^ (?:(?:parts?|areas?|stuff|bits?|stripes?|blocks?|squares?|sections?|pieces?|spots?|ones?) )?(?:(?:that is|thats|that are|which is|which are|that s) )?(?:on|in|of|across|along|from|over|down|near|around|at|by|towards?|inside|within)(?= )/;
    var OBJ_STOP = /^(to|into|and|or|but|then|with|as|is|are|was|were|be|so|because|please|that|which|where|should|you|i|it|on|in|of|near|at|for|from|by|when|if|while|now|also|too|make|give|turn|paint|set|change|have|put|look|looks|looking|same|well)$/;
    function placeIn(s) { s = String(s || ''); for (var i = 0; i < PLACES.length; i++) { var m = PLACES[i][0].exec(s); if (m) return { parts: PLACES[i][1].slice(), at: m.index, len: m[0].length }; } return null; }
    // a place / part phrase -> part list (online refinish `part`, complaint places): "rear of the car" -> trunk, rear bumper, rear thirds of the sides; "hood" -> hood
    function placeParts(s) { var t = ' ' + norm(String(s || '')) + ' ', pl = placeIn(t), out = pl ? pl.parts.slice() : []; PART_WORDS.forEach(function (pw) { if (pw[1].test(t) && out.indexOf(pw[0]) === -1 && !out.some(function (x) { return x.split('@')[0] === pw[0]; })) out.push(pw[0]); }); if (!out.length && /\b(sides?|doors?)\b/.test(t)) out = ['left side', 'right side']; if (!out.length && /\bbumpers?\b/.test(t)) out = ['front bumper', 'rear bumper']; return out; }
    var NUMBERS_RE = /\b(numbers?|digits?|number panels?|car number|the \d{1,3}s?)\b/, SPONSORS_RE = /\b(sponsors?|sponsor (panels?|logos?)|logos?|decals?|lettering|branding|adverts?|advertising|ads)\b/;
    var ACCENT_RE = /\b(stripes?|pinstripes?|accents?|trim|graphics?|lines?|highlights?|outlines?|details?|detailing)\b/, BODY_RE = /\b(body|bodywork|the paint|paintwork|base colou?r|main colou?r|primary colou?r|the base|whole car|entire car|the car|the truck|my car|my truck|everything|all of it|the whole thing|vehicle)\b/;
    var DET = '(?:(?:everything|anything|stuff|parts?|areas?|bits?|things?) (?:that is|that are|thats|which is|which are|that s)|the|all of the|all the|all|any|every|each|those|these|that|my|where the|wherever the|anywhere the)';
    var COLOUR_NOUN = '(?:parts?|areas?|bits?|stuff|sections?|panels?|paint|colou?rs?|stripes?|pinstripes?|trim|accents?|graphics?|lines?|bands?|portions?|regions?|spots?|bodywork|things?|pieces?|squares?|blocks?|letters?|lettering)';
    var QUESTION_RE = /^(what|which|how|why|where|when|who|is|are|does|do you|can i|could i|should|would|will|help|any (idea|advice|suggest)|recommend|suggest|tell me|explain|show me|list|describe)\b|\?\s*$/;
    var REL_UP = /\b(glossier|shinier|(?:shine|gloss|glossy|reflect|shimmer) (?:a )?(?:bit |little )?more|more (gloss|glossy|shine|shiny|reflective|wet)|extra (gloss|shine)|brighter shine|high(er)? gloss|polished up|wetter)\b/, REL_DOWN = /\b(duller|dull(ed)? down|flatter|more (?:dull|matte|flat|muted|subtle|satin)|less (shiny|glossy|shine|gloss|reflective|glare)|tone(d)? down the (shine|gloss)|not (so |as |too )?(shiny|glossy)|less sheen|more subtle|take the shine off|knock the shine off)\b/;
    var SHADE_RE = /\b(darker|lighter|brighter|bolder|deeper|richer|more saturated|less saturated|more vivid|washed out|faded|paler|subdued|muted|neon(?! (?:orange|green|yellow|pink|blue))|fluorescent|fluoro|day glo|electric(?! blue))\b/;
    var SOFT_RE = /\b(a little|a bit|slightly|somewhat|just a bit|a touch|little bit)\b/, STRONG_RE = /\b(much|way|a lot|super|really|very|extremely|mirror|max(imum)?|as .{0,10} as possible)\b/;
    var KEEP_RE = /\b(keep (the )?(colou?rs?|paint)|same colou?rs?|leave the colou?rs?|without changing the colou?rs?|colou?rs? stay|colou?rs? the same|only the (shine|finish|spec|look)|just the (shine|finish|spec)|spec only|don't change the colou?r|not change the colou?r)\b/;
    var POP_RE = /\b(pop|pops|popping|stand out|stands out|accentuate|emphasi[sz]e|more contrast|contrast|punch up|punch it up|jazz up|jazz it up|spice up|liven up|make it zing|zing)\b/;
    var DESCRIBE_RE = /\b(what colou?rs? (do i|are|does|is)|which colou?rs?|what('s| is) (on|in) (my|the) (car|paint|livery|design)|what do i have|list (my|the) colou?rs?|describe (my|the) (car|paint|livery|design)|what am i working with|what('s| is) the (base|main) colou?r|read (my|the) (paint|car|colou?rs?))\b/;

    // "make the black matte but leave the numbers alone" / "everything except the sponsors": what must NOT change (stripped from the sentence before targets are read)
    var EXCEPT_RE = /\b(?:(?:except|excluding|apart from|other than|(?<=\b(?:everything|all|all of it|the car|whole car) )but|without touching|not including|but not|but not touching|but don t touch|but dont touch|and don t touch|and dont touch|do not touch|dont touch|don t touch)(?: for)?|(?:but |and )?(?:leave|keep))\s+(?:all |both )?(?:the |my )?(numbers?|sponsors?|logos?|decals?|stripes?|pinstripes?)(?:\s+(?:and|&)\s+(?:the |my )?(numbers?|sponsors?|logos?|decals?|stripes?|pinstripes?))?(?:\s+(?:alone|as (?:they are|is|it is)|untouched|the same|unchanged|out of (?:it|this|that|the (?:job|edit|change))|where (?:they|it) (?:are|is)|(?:white|black|red|blue|green|yellow|gold|silver|orange|purple|pink|grey)))?(?=$|\s)/g;
    var STAYS_RE = /(?:^|[,;]\s*|\s)(?:and |but )?(?:leave |keep )?(?:the |my )?(?:rest|body|everything else|everything|the car|the rest of (?:it|the car|the paint))(?: (?:colou?rs? )?(?:stays?|remains?|is fine|are fine|as is|the same|untouched|unchanged|alone|stay the same|stays the same|as they are|as it is))(?=$|[,;.!?\s])(?!\s+(?:[a-z]+\s+)?(?:as|colou?r|shade|hue)\b)/gi;          // ROUTER-FIX: "...of the car the same pink as the numbers" is not "the car stays the same"
    function exceptKind(w) { return /number/.test(w) ? 'numbers' : (/stripe/.test(w) ? 'stripes' : 'sponsors'); }
    function extractExcept(text) {
        var ex = [], t = fixText(text);
        t = t.replace(EXCEPT_RE, function (m, w, w2, off, whole) { var strong = /^(?:but |and )?(?:leave|keep)/.test(m.trim()); var tail = whole.slice(off + m.length); var closing = /^\s*(?:$|,|;|\.|please\b|thanks?\b|and\b|then\b)/.test(tail); if (strong && !/(alone|as they are|as is|as it is|untouched|the same|unchanged|where|out of (?:it|this|that|the))/.test(m) && !(/^(?:but|and) /.test(m.trim()) && closing)) return m; [w, w2].forEach(function (x) { if (!x) return; var k = exceptKind(x); if (ex.indexOf(k) === -1) ex.push(k); }); return ' '; });
        return { text: t.replace(/\s+/g, ' ').trim(), list: ex };
    }
    // ZoneKit's exclusion contract only supports element layers (numbers, sponsors, stripes).
    // A named-panel exclusion cannot safely be approximated by an all-car or colour region.
    function preservedParts(text) {
        var possessiveParts = /\b(hood|bonnet|roof|trunk|deck|lid|bed|bumper|nose|tail|spoiler|wing|side|door|flank|driver|passenger)['’]s\b/gi;
        var t = norm(String(text || '').replace(possessiveParts, '$1')), found = [];
        var protectWords = '(?:except(?: for)?|excluding|apart from|other than|not including|without touching|without changing|but not|do not touch|dont touch|do not change|dont change|do not alter|dont alter|do not modify|dont modify|leav(?:e|ing)|keep(?:ing)?|preserv(?:e|ing)|retain(?:ing)?|maintain(?:ing)?)';
        var marker = new RegExp(protectWords + '\\s+(?:(?:all|both|the|my|current|existing|original|entire)\\s+){0,3}$');
        PART_WORDS.forEach(function (pw) {
            var re = new RegExp(pw[1].source, 'g'), m;
            while ((m = re.exec(t))) {
                var before = t.slice(Math.max(0, m.index - 90), m.index), after = t.slice(m.index + m[0].length, m.index + m[0].length + 65);
                // "don't leave/keep it" cancels a preservation request; "don't change it" preserves it.
                if (/\b(?:do not|dont|never)\s+(?:leave|keep|preserve|retain|maintain)\s+(?:(?:all|both|the|my|current|existing|original|entire)\s+){0,3}$/.test(before)) continue;
                var coordinated = new RegExp('\\b' + protectWords + '\\b(.+)$').exec(before);
                var sharesMarker = coordinated && /\b(?:and|or)\b/.test(coordinated[1]) && !/\b(?:make|paint|turn|change|recolou?r|add|apply|set|should be|to be)\b/.test(coordinated[1]);
                var stays = /^\s+(?:(?:should|must)\s+)?(?:stay|stays|remain|remains|be left|be kept|is left|is kept)\b/.test(after);
                if ((marker.test(before) || sharesMarker || stays) && found.indexOf(pw[0]) === -1) found.push(pw[0]);
            }
        });
        // Generic plural references are safe to block too, while singular left/right wording stays exact.
        if (new RegExp('\\b' + protectWords + '\\s+(?:(?:all|both|the|my|current|existing|original|entire)\\s+){0,3}sides?\\b').test(t)) {
            ['left side', 'right side'].forEach(function (p) { if (found.indexOf(p) === -1) found.push(p); });
        }
        return found;
    }
    function preservedPartAsk(parts, text) {
        var named = norm(text), requested = PART_WORDS.filter(function (pw) { return parts.indexOf(pw[0]) === -1 && pw[1].test(named); }).map(function (pw) { return pw[0]; });
        var subject = requested.length ? 'the requested ' + requested.join(' and ') + ' change' : 'this combined request';
        return { kind: 'ask', protected_parts: parts.slice(), requested_parts: requested, text: 'Nothing was changed. I can’t yet guarantee ' + subject + ' leaves ' + parts.map(function (p) { return 'the ' + p; }).join(' and ') + ' unchanged. Send the change as a separate panel-only request, or clarify the scope before I apply anything.', chips: [] };
    }
    var VARIANTS_RE = /\b(options?|variations?|variants?|alternatives?|choices|(a few|some|several|different|other|more) (looks?|finishes|ideas)|what (could|would|might) .{0,30}look like|try (a few|some|different|several) (looks?|finishes)|show me (some |a few )?(looks?|finishes))\b/;
    var SAME_RE = /\b(same|likewise|do that|do it|too|also|as well)\b/, WHOLE_RE = /\b(car|truck|vehicle|body|everything|whole|entire|all of it|everywhere)\b/;
    var REVERT_RE = /\b(put|set|change|turn|take|bring|restore|go|get)\b.{0,24}\b(back|to normal|to how it was|to what it was|to the original|as it was)\b|\b(undo|revert|reset|remove|cancel|forget|get rid of)\b (?:that |the |my |all the |all )?(?!last\b|that\b|everything\b|all\b|change|changes\b)/;
    var REVERT_WORDS_RE = /\b(put|take|bring|restore|go|get|set|back|to normal|to how it was|to what it was|to the original|as it was|undo|revert|reset|remove|cancel|forget|get rid of)\b/g;
    var MORE_RE = /^(?:(?:just )?(?:a (?:little|bit|touch|tad|smidge)(?: bit)?|bit|tad) |even |much |slightly |a lot |way )?(?:more|stronger|again|further|go further|push it|push it more|take it further|crank it|crank it up|turn it up)(?: of that| still| please| than that)?$/, LESS_RE = /^(?:(?:a (?:little|bit|touch|tad|smidge)(?: bit)?|bit|tad) |slightly |much |way |just )?(?:less|weaker|softer|gentler|tone it down|ease off|back off|dial it back|dial it down|not (?:that|so|quite so|this) much|too much|that is too much|thats too much|that s too much|a bit much|a little much|bit much|less than that)(?: please| a bit| a little)?$/;
    var GHOST_RE = /\b(ghost(?:ed|ing)?|tone on tone|tonal)\b/, BLACKOUT_RE = /\b(black ?out|blacked out|murdered out)\b/, SUB_RE = /\b(outlines?|borders?|edges?|shadows?|fill|inside|inner|outer)\b/;
    var SHEEN = ['plasti dip', 'matte', 'satin', 'gloss', 'wet look'], METAL = ['pearl', 'metallic', 'satin chrome', 'chrome'];
    var VARIANT_SETS = { black: ['matte', 'satin', 'powder coat', 'wet look'], charcoal: ['matte', 'satin', 'powder coat', 'dark chrome'], grey: ['satin chrome', 'brushed', 'matte metallic', 'chrome'], silver: ['chrome', 'brushed', 'satin chrome', 'matte metallic'], white: ['pearl', 'satin pearl', 'matte', 'wet look'], red: ['candy', 'wet look', 'matte', 'pearl'], orange: ['satin', 'candy', 'powder coat', 'metallic'], yellow: ['powder coat', 'pearl', 'metallic', 'matte'], green: ['candy', 'pearl', 'matte', 'metallic'], teal: ['metallic', 'pearl', 'candy', 'satin'], blue: ['metallic', 'candy', 'satin', 'pearl'], purple: ['candy', 'pearl', 'metallic', 'matte'], pink: ['pearl', 'candy', 'satin', 'metallic'], brown: ['satin', 'matte', 'metallic', 'powder coat'], tan: ['matte', 'satin', 'powder coat', 'metallic'], numbers: ['chrome', 'metallic', 'matte', 'pearl'], sponsors: ['matte', 'satin', 'chrome', 'wet look'], accents: ['chrome', 'metallic', 'matte', 'pearl'], part: ['matte', 'satin', 'chrome', 'powder coat'], main: ['matte', 'satin', 'pearl', 'metallic'] };
    function lookById(id) { return LOOK_BY_ID[id] || null; }
    function stepLook(id, dir) {          // dir +1 = shinier / more metal, -1 = flatter / less metal; null when the look is not on a ladder or already at the end
        var lad = SHEEN.indexOf(id) !== -1 ? SHEEN : (METAL.indexOf(id) !== -1 ? METAL : null); if (!lad) return null;
        var i = lad.indexOf(id) + dir; if (i < 0 || i >= lad.length) return null; return lookById(lad[i]);
    }

    // named things that are LAYERS in many templates (rollbar colour, cockpit colour, pit box, window blackout) or are not on the paint sheet at all (wheels, tyres)
    var LAYERWORDS = [['rollbar', /\b(roll ?bars?|roll ?cage)\b/], ['cockpit', /\b(cockpit|interior|seats?|dash(board)?)\b/], ['pit box', /\b(pit ?box(es)?|pit ?board)\b/], ['windows', /\b(windows?|glass|windshield|windscreen)\b/], ['wheels', /\b(wheels?|rims?|tires?|tyres?)\b/]];
    var UNSUPPORTED_TEXT = { wheels: 'Wheels, rims and tyres are not on the car paint sheet: iRacing paints them from a separate wheel texture, so I cannot change them here.', windows: 'The windows are not part of the paint on most iRacing cars (the sim draws the glass), and I cannot find a window layer in this file.', cockpit: 'I cannot find a cockpit / interior layer in this file, and the inside of the car is not on the paint sheet of most cars.', rollbar: 'I cannot find a roll-bar layer in this file.', 'pit box': 'I cannot find a pit box layer in this file.' };
    var UNKNOWN_PART_RE = /\b(head ?lights?|tail ?lights?|lights?|grille?s?|mirrors?|splitter|diffuser|scoops?|vents?|nerf bars?|licen[cs]e plates?|plates?|antenna|wipers?|handles?|fenders?|quarter panels?)\b/;
    function layerNamesFor(layers, re) { return layers.filter(function (l) { var n = String(l.name || '').toLowerCase(); return !l.hidden && re.test(n) && !/mask|wire|mandatory|licen[cs]e|guide/.test(n); }).map(function (l) { return l.name; }); }
    var SHADE_PARAMS = [[/darker|deeper|richer/, { brightness: -35 }, 'darker'], [/lighter|paler/, { brightness: 35, saturation: -10 }, 'lighter'], [/brighter|bolder|more vivid|more saturated/, { saturation: 45, brightness: 8 }, 'brighter'], [/washed out|faded|muted|subdued|less saturated/, { saturation: -55 }, 'faded'], [/neon|fluorescent|fluoro|day glo|electric/, { saturation: 100, brightness: 10 }, 'neon']];
    function shadeParams(word) { for (var i = 0; i < SHADE_PARAMS.length; i++) if (SHADE_PARAMS[i][0].test(word)) return { adj: JSON.parse(JSON.stringify(SHADE_PARAMS[i][1])), label: SHADE_PARAMS[i][2] }; return { adj: { saturation: -30 }, label: word }; }

    function lookScan(t) {          // find looks (longest first, no overlaps) -> { looks:[{look, at}], rest }
        var padded = ' ' + t + ' ', taken = [], found = [];
        LOOK_INDEX.forEach(function (e) {
            var w = ' ' + e.w + ' ', from = 0, at;
            while ((at = padded.indexOf(w, from)) !== -1) {
                var st = at + 1, en = at + w.length - 1; from = at + 1;
                if (taken.some(function (r) { return st < r[1] && en > r[0]; })) continue;
                taken.push([st, en]); found.push({ look: e.look, at: st });
            }
        });
        found.sort(function (a, b) { return a.at - b.at; });
        var rest = padded.split(''); taken.forEach(function (r) { for (var i = r[0]; i < r[1]; i++) rest[i] = ' '; });
        return { looks: found, rest: rest.join('').replace(/\s+/g, ' ').trim() };
    }
    function splitClauses(t) {
        var s = ' ' + t + ' ';
        s = s.replace(/ (and|then|also|plus|but|while|with|as well as|and then|after that|next) (make|turn|set|paint|give|put|change|have|i want|i need|let s|let's) /g, ' | $2 ');
        // FIRSTTEST2 2026-10-04 owner: 'I told it to change the yellow TO pink' ("the yellow on the base paint and on the spray paint can to pink"): "and on / in the X" is MORE SCOPE
        // for the same clause, never a new job; "after that" is a step separator like "then".
        s = s.replace(/ (after that|and|then|plus|also|but|while|as well as) (?=((?:on|in|inside|across|along) (?:the |my |that |this )?)?(\S*))/g, function (m, w, prep, nx) { return (prep && !(Dz().parseColours && Dz().parseColours(nx || '').length)) ? m : ' | '; });          // "...and on the black near the rear" (a colour) is still a new target
        return s.split('|').map(function (x) { return x.replace(/\s+/g, ' ').trim(); }).filter(function (x) { return x.length; });
    }
    function clauseList(text) {
        var out = []; String(text || '').split(/[,;]+|\.\s+|\s&\s|\s-\s/).forEach(function (piece) { var ft = fixText(piece); if (ft) splitClauses(ft).forEach(function (c) { out.push(c); }); });
        return out;
    }
    function qualBefore(t, at) { var m = /\b(dark|deep|light|pale|bright|neon)\s$/.exec(t.slice(Math.max(0, at - 8), at)); return m ? m[1] : null; }

    var CTX = { pal: [], prevColour: false };
    function onCar(word, hex) { try { return resolveColour(wantFor(word, hex, null), CTX.pal).entries.length > 0; } catch (e) { return false; } }
    // FIRSTTEST 2026-10-04 (owner's first test: "I want to make the yellow on the car purple and give it some type of reflective snakeskin pattern" -> every built-in brain declined:
    // "reflective snakeskin pattern" was ONE unknown look and the catalogue has no finish named like that; "purple metallic snake scales" silently dropped the scales).
    // A TEXTURE named with an edit is part of the SAME job: a SHINE texture (spec pattern) or a PAINT pattern on exactly that target, in the same zone (one Undo).
    // Shine words ("reflective", "shine", "chrome", "metallic" ...) make it a spec texture; "print" / a bare "pattern" a paint pattern; the other version is offered as a chip.
    var TEXTURES = [
        { id: 'snake', label: 'snakeskin', re: /\b(?:rattle ?snake|snake ?skin|snake ?scales?|snakes?|python|cobra|viper|serpent|reptile|reptilian|lizard)(?: (?:skin|scales?|hide|print|leather))?\b/, spec: 'snake_scale_diamond', specName: 'Snake Scale Diamond', specAlt: 'spec_snake_scales', pattern: 'snake_skin', patternName: 'Snake Skin' },
        { id: 'croc', label: 'crocodile skin', re: /\b(?:croc|crocodile|alligator|gator)(?: (?:skin|scales?|hide|print|leather))?\b/, spec: 'croc_delta_armor', specName: 'Croc Delta Armor', pattern: 'crocodile', patternName: 'Crocodile' },
        { id: 'dragon', label: 'dragon scales', re: /\bdragon ?(?:scales?|skin|hide)\b/, spec: 'dragon_scale_macro', specName: 'Dragon Scale Macro', pattern: 'dragon_scale', patternName: 'Dragon Scale' },
        { id: 'scales', label: 'fish scales', re: /\b(?:fish ?scales?|mermaid ?scales?|scaly|scales)\b/, spec: 'spec_fish_scales', specName: 'Fish Scales', pattern: 'seigaiha_scales', patternName: 'Seigaiha Scales' }
    ];
    var TEX_SHINE_RE = /\b(?:reflective|reflecting|reflection|reflect|shine|shiny|shimmer\w*|sheen|glossy|gloss|chrome|mirror\w*|metallic|metal|spec|specular|clear ?coat|sparkl\w*|glint\w*|holo\w*|iridescent)\b/;
    var TEX_PAINT_RE = /\b(?:print|printed|graphic|drawn|in the paint|colou?red lines)\b/;
    function textureScan(t) {
        var hit = null; TEXTURES.forEach(function (tx) { var m = tx.re.exec(t); if (m && (!hit || m.index < hit.m.index)) hit = { tx: tx, m: m }; });
        if (!hit) return null;
        var shine = TEX_SHINE_RE.test(t), mode = TEX_PAINT_RE.test(t) ? 'pattern' : (shine ? 'spec' : (/\bpatterns?\b/.test(t) ? 'pattern' : 'spec')), tx = hit.tx;
        var rest = (t.slice(0, hit.m.index) + ' ' + t.slice(hit.m.index + hit.m[0].length)).replace(/\b(?:patterns?|prints?|printed|textured|textures?|sheen|specular|spec|shine|feel|overlay)\b/g, ' ').replace(/\s+/g, ' ').trim();
        return { tex: { id: tx.id, label: tx.label, mode: mode, word: hit.m[0], spec: tx.spec, specName: tx.specName, specAlt: tx.specAlt || null, pattern: tx.pattern, patternName: tx.patternName }, rest: rest };
    }
    function textureFor(word, mode) {          // the online refinish `texture` field: a concept word ("snakeskin") or a catalogue id
        var t = norm(String(word || '')), sc = textureScan(t + (mode === 'pattern' ? ' print' : (mode === 'shine' || mode === 'spec' ? ' shine' : '')));
        if (sc) return sc.tex;
        if (/^[a-z0-9_]{3,60}$/.test(t)) return { id: 'id', label: t.replace(/_/g, ' '), mode: mode === 'pattern' ? 'pattern' : 'spec', word: t, spec: t, specName: t.replace(/_/g, ' '), pattern: t, patternName: t.replace(/_/g, ' ') };
        return null;
    }
    // FIRSTTEST2 2026-10-04 owner: 'I told it to change the yellow TO pink' ("holographic reflective snakeskin pattern on that pink"): "holographic" with a colour the buyer just chose or
    // with a texture must KEEP that colour. The catalogue's colour-keeping holographic is the Foundation EFX keeper "Holographic Drift" (base::efx_holographic_drift, paint passthrough,
    // spec-driven diffraction; owner-LOCKED look). A bare "make the black holographic" still goes to the catalogue's own rainbow holographic (LOOK_CURATED), unchanged.
    var HOLO_RE = /\b(?:holo\w*|hologram\w*|prismatic|prism|iridescen\w*|chameleon|colou?r ?shift\w*|rainbow)\b/, HOLO_RE_G = new RegExp(HOLO_RE.source, 'g');
    var HOLO_LOOK = { id: 'holographic', label: 'holographic', words: [], found: 'base::efx_holographic_drift', about: 'a holographic diffraction shimmer in the shine (spec); the paint colour stays' };
    var HOLO_GENERIC = { metallic: 1, gloss: 1, 'wet look': 1, pearl: 1 };          // plain shine words a holographic shine already covers ("holographic reflective")
    LOOK_BY_ID.holographic = HOLO_LOOK;
    function parseClause(raw) {
        var t = fixText(raw), res = { raw: t, targets: [], looks: [], colours: [], rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, inherits: false, alt: [], hasVerb: false };
        res.hasVerb = /\b(make|turn|set|paint|give|put|change|have|want|need|should be|needs to be|color|colour|switch|swap|replace|convert|do)\b/.test(t);
        var txs = textureScan(t); if (txs) { res.texture = txs.tex; t = txs.rest; }          // FIRSTTEST
        // alternatives: "matte or powder coat" -> take the first, offer the rest
        var orSplit = t.split(/ or /);
        if (orSplit.length > 1 && lookScan(orSplit[1]).looks.length && lookScan(orSplit[0]).looks.length) { var alts = []; orSplit.slice(1).forEach(function (a) { var ls = lookScan(a).looks; if (ls.length) alts.push(ls[0].look); }); res.alt = alts; t = orSplit[0]; }
        res.keep = KEEP_RE.test(t); if (res.keep) t = t.replace(KEEP_RE, ' ');
        res.soft = SOFT_RE.test(t); res.strong = STRONG_RE.test(t);
        if (REL_UP.test(t)) { res.rel = 'up'; t = t.replace(REL_UP, ' '); } else if (REL_DOWN.test(t)) { res.rel = 'down'; t = t.replace(REL_DOWN, ' '); }
        var sh = SHADE_RE.exec(t); if (sh) { res.shade = sh[1]; t = t.replace(SHADE_RE, ' '); }
        if (POP_RE.test(t)) { res.pop = true; t = t.replace(POP_RE, ' '); }
        if (GHOST_RE.test(t)) { res.recipe = 'ghost'; t = t.replace(GHOST_RE, ' '); } else if (BLACKOUT_RE.test(t)) { res.recipe = 'blackout'; t = t.replace(BLACKOUT_RE, ' '); }
        var ls = lookScan(t); ls.looks.forEach(function (l) { res.looks.push(l.look); });
        var rest = ' ' + ls.rest + ' ';
        var hm = HOLO_RE.exec(rest);          // FIRSTTEST2: "holographic reflective snakeskin" = a colour-keeping holographic shine + the snakeskin texture (never a dropped word)
        if (hm) { res.holo = hm[0]; if (res.texture) { res.looks = res.looks.filter(function (l) { return !HOLO_GENERIC[l.id]; }); res.looks.push(HOLO_LOOK); rest = rest.replace(HOLO_RE_G, ' '); } }          // only with a texture: "matte white with holographic flakes" stays the designer's layer stack
        var subm = SUB_RE.exec(rest); res.sub = subm ? (/outline|border|edge|outer/.test(subm[1]) ? 'outline' : (/shadow/.test(subm[1]) ? 'shadow' : 'fill')) : null;
        // layers + parts first (an explicit element beats a colour word: "the black numbers" = the numbers)
        var cols = (Dz().parseColours ? Dz().parseColours(rest) : []).slice(), consumed = [], hx, hre = /(^| )(#[0-9a-f]{6})(?= |$)/g;
        while ((hx = hre.exec(rest))) cols.push({ name: hx[2], hex: hx[2], at: hx.index + hx[1].length });
        cols.sort(function (a, b) { return a.at - b.at; });
        function elementAfter(c) { var after = rest.slice(c.at + c.name.length, c.at + c.name.length + 18); return /^ (numbers|sponsors|logos?|decals?|hood|roof|trunk|bonnet|doors?|sides?|bumpers?|spoiler|wing|stripes?|pinstripes?|trim|accents?|lines?|bands?)\b/.test(after); }
        var explicit = false;
        LAYERWORDS.forEach(function (lw) { var m = lw[1].exec(rest); if (m) { res.targets.push({ kind: 'layerword', word: lw[0], at: m.index }); explicit = true; } });
        // ROUTER-FIX 2026-10-04: "the same pink as the numbers" / "the pink you use on the numbers": the numbers are a REFERENCE for the colour there, not a target
        var refEl = /\b(?:same\b[^.,;]{0,30}?\bas|like|(?:you|i) (?:use|used|put|have|had) (?:on|for)|that (?:is|s) on|matching|to match) (?:the |my )?(?:numbers?|sponsors?|logos?|decals?)\b/.exec(rest);
        if (refEl) { var refFrom = refEl.index, refTo = refEl.index + refEl[0].length; rest = rest.slice(0, refFrom) + rest.slice(refFrom, refTo).replace(/\b(numbers?|sponsors?|logos?|decals?)\b/g, function (w) { return new Array(w.length + 1).join('_'); }) + rest.slice(refTo); }
        if (NUMBERS_RE.test(rest)) { res.targets.push({ kind: 'numbers', at: rest.search(NUMBERS_RE) }); explicit = true; }
        if (SPONSORS_RE.test(rest)) { res.targets.push({ kind: 'sponsors', at: rest.search(SPONSORS_RE) }); explicit = true; }
        var partsHit = [];
        PART_WORDS.forEach(function (pw) { var m = pw[1].exec(rest); if (m) partsHit.push({ kind: 'part', part: pw[0], at: m.index }); });
        if (/\b(sides?|doors?)\b/.test(rest) && !partsHit.some(function (h) { return /side/.test(h.part); })) { var ms = /\b(sides?|doors?)\b/.exec(rest); partsHit.push({ kind: 'part', part: 'left side', at: ms.index }, { kind: 'part', part: 'right side', at: ms.index }); }
        if (/\bbumpers?\b/.test(rest) && !partsHit.some(function (h) { return /bumper/.test(h.part); })) { var mb = /\bbumpers?\b/.exec(rest); partsHit.push({ kind: 'part', part: 'front bumper', at: mb.index }, { kind: 'part', part: 'rear bumper', at: mb.index }); }
        // "the black ON THE HOOD": a colour target limited to a part - the part is a scope, not the target
        var scoped = null;
        cols.forEach(function (c) {
            if (scoped) return;
            var after = rest.slice(c.at + c.name.length, c.at + c.name.length + 70), m = SCOPE_PREP.exec(after);
            if (!m) return;
            var pl = placeIn(after);          // ROUTER-FIX 2026-10-04: "the black near the rear of the car", "the white on the back of each side"
            if (pl && pl.at <= m[0].length + 6) { var cutEnd = c.at + c.name.length + pl.at + pl.len; scoped = { colourAt: c.at, parts: pl.parts.concat(partsHit.filter(function (x) { return x.at >= cutEnd; }).map(function (x) { return x.part; })), place: true, cut: [c.at + c.name.length, cutEnd] }; return; }
            var tail = after.slice(m[0].length).replace(/^ (?:the |my |each |both )?/, '');
            partsHit.forEach(function (h) { var pw = PART_WORDS.filter(function (x) { return x[0] === h.part; })[0]; if (pw && pw[1].test(tail.slice(0, 22)) && !scoped) scoped = { colourAt: c.at, parts: partsHit.filter(function (x) { return x.at >= c.at; }).map(function (x) { return x.part; }) }; });
        });
        if (scoped) partsHit = [];
        // WP7 2026-10-03: "the number on the door" / "the logos on the hood": the part says WHERE the element is, it is not a second job (it used to chrome the whole door)
        var onEl = /\b(?:numbers?|digits?|sponsors?|logos?|decals?|stripes?|pinstripes?)(?: \w+)? (?:on|in|across|along|down|over|of) (?:the |my )?/.exec(rest);
        if (onEl) { var onAt = onEl.index + onEl[0].length; partsHit = partsHit.filter(function (h) { return h.at < onAt - 12; }); }
        partsHit.forEach(function (h) { res.targets.push(h); explicit = true; });
        var accent = ACCENT_RE.exec(rest), bodyHit = BODY_RE.exec(rest);
        // colour roles
        var tgtCols = [], actCols = [];
        cols.forEach(function (c, i) {
            var before = rest.slice(Math.max(0, c.at - 24), c.at), after = rest.slice(c.at + c.name.length, c.at + c.name.length + 24), q = qualBefore(rest, c.at);
            var det = new RegExp(DET + ' (?:(?:dark|deep|light|pale|bright|neon) )?$').test(before), noun = new RegExp('^ ' + COLOUR_NOUN + '\\b').test(after);
            var elem = elementAfter(c) && !/^ (stripes?|pinstripes?|trim|accents?|lines?|bands?)\b/.test(after);
            var fromTo = /\b(from|turn|change|swap|switch|replace|convert|recolou?r|colou?r)\s+(the\s+|all\s+the\s+|all\s+)?(?:(?:dark|deep|light|pale|bright|neon) )?$/.test(before) && /^ (to|into|with|for)\b/.test(after) && cols[i + 1];
            var c2 = { name: c.name, hex: c.hex, at: c.at, qual: q, exact: /^#/.test(c.name) };
            // WP7 2026-10-03: "purple numbers" / "gold stripes" (one colour, no "the", no look): the buyer states the colour they WANT on the element
            if ((elem || /^ (stripes?|pinstripes?|trim|accents?|lines?|bands?)\b/.test(after)) && !det && cols.length === 1 && !ls.looks.length && !res.rel && !res.shade && !res.pop && (NUMBERS_RE.test(rest) || SPONSORS_RE.test(rest) || ACCENT_RE.test(rest))) { actCols.push(c2); return; }
            if (elem) return;                                                                       // "the black numbers": the colour only describes the element
            if (scoped && c.at === scoped.colourAt) { tgtCols.push(c2); return; }
            // Owner AI/offline sprint 2026-10-03: in "roof from blue to red", blue describes
            // the named target's previous colour; it must not create an extra all-blue edit.
            if (fromTo && explicit) { res.sourceColour = true; return; }
            if (fromTo || ((det || noun) && !(explicit && !noun && !det))) { tgtCols.push(c2); return; }
            if (!explicit && cols.length === 1 && (res.shade || res.rel)) { tgtCols.push(c2); return; }                             // "make the yellow neon", "darker red", "the white glossier"
            if (!explicit && CTX.prevColour && (ls.looks.length || res.rel) && onCar(c.name, c.hex)) { tgtCols.push(c2); return; }       // "make the black matte and white gloss": white is another colour ON the car
            if (!explicit && i === 0 && cols.length > 1 && (/^ (to|into|for|with)\b/.test(after) || (!actCols.length && res.hasVerb))) { tgtCols.push(c2); return; }       // "make the red blue", "turn red into blue"
            actCols.push(c2);
        });
        if (cols.length === 2 && !explicit && tgtCols.length === 2) { actCols.push(tgtCols.pop()); }              // "turn the yellow into the purple"
        tgtCols.forEach(function (c) { var tgc = { kind: 'colour', word: c.name, hex: c.hex, qual: c.qual, at: c.at, parts: scoped ? scoped.parts : null }; if (scoped && scoped.place) tgc.place = true; res.targets.push(tgc); });
        res.colours = actCols;
        if (!res.targets.length) {
            if (res.pop && !accent && /\b(colou?rs?|paint|livery|design)\b/.test(rest)) res.targets.push({ kind: 'allpop', at: 0 });          // "make the colours pop": ours; a vague "make it pop" is the ideas helper's (it offers directions)
            else if (accent) res.targets.push({ kind: 'accents', word: accent[1], at: accent.index });
            else if (bodyHit && /\b(base colou?r|main colou?r|primary colou?r|the base)\b/.test(bodyHit[0])) res.targets.push({ kind: 'main', at: bodyHit.index });
            else if (bodyHit) res.targets.push({ kind: 'body', at: bodyHit.index });
        }
        // anything left over that is not a known word: an unknown look word ("carbon fiber", "camo", "galaxy") or noise
        var cw = {}; cols.forEach(function (c) { c.name.split(' ').forEach(function (w) { cw[w] = 1; }); });
        var STOP = ' now well again next make give put paint turn set add apply want wanted wants like love need please can could would you me my i it its that this the a an of on in with to for from only just also too some more really very change use do have get be is are as car cars truck whole entire all everything finish finishes look looks effect effects texture type kind style stuff parts part areas area bits sections panels paint painted colour colours colour like having has looking go going it s them they those these there here and or but then plus not no so thing things coating coated coat spec shine shiny up down off out dark deep light pale bright neon on top hey hi hello thanks thank please ok okay yes yeah just still will would should lets let into little bit touch way much lot bigger actually already switch swap replace recolor recolour convert pls plz wanna gonna gotta da border edge shadow fill inside inner outer same likewise again further ';
        var restL = rest; if (scoped && scoped.cut) restL = rest.slice(0, scoped.cut[0]) + ' ' + rest.slice(scoped.cut[1]);          // ROUTER-FIX: the place words are a scope, not an unknown look
        PART_WORDS.forEach(function (pw) { restL = restL.replace(new RegExp(pw[1].source, 'g'), ' '); });          // "rear bumper" / "back bumper": "rear" / "back" were left over as an unknown LOOK ("I do not know a look called rear")
        if (scoped) restL = restL.replace(/\b(?:near|around|towards?|within|each|both)\b/g, ' ');
        restL = restL.replace(/_+/g, ' ');          // a reference element ("as the numbers") is masked with underscores above
        var left = restL.split(' ').filter(function (w) { return w.length > 2 && !cw[w] && !/^[0-9#]+$/.test(w) && !/^#[0-9a-f]{6}$/.test(w) && STOP.indexOf(' ' + w + ' ') === -1 && !NUMBERS_RE.test(w) && !SPONSORS_RE.test(w) && !ACCENT_RE.test(w) && !BODY_RE.test(w) && !PART_WORDS.some(function (pw) { return pw[1].test(w); }) && !/^(sides?|doors?|bumpers?|fenders?|windows?|wheels?|rims?|tires?|tyres?|mirrors?|grille?s?|lights?|headlights?|taillights?|splitter|diffuser|scoops?|vents?|plates?|handles?|wipers?|antenna|cockpit|interior|seats?|dash|dashboard|rollbar|rollbars|cage|glass|windshield|pitbox|pitboard)$/.test(w); });
        // The direction word belongs to a parsed left/right side alias (it is not an unknown look).
        if (res.targets.some(function (x) { return x.kind === 'part' && /side/.test(x.part); })) left = left.filter(function (w) { return !/^(left|right|drivers?|passengers?)$/.test(w); });
        // ROUTER-FIX 2026-10-04 (owner T1: "the yellow on the spray can" was refused, "the black base hexagon" became the LOOK "base hexagon"): words naming a THING after a colour
        // target are an object the app must locate (layers that hold that colour / a box the buyer draws), never an unknown look. With no preposition they count only when the clause
        // also says what to do ("make the black base hexagon pink"), so "make the black carbon fiber" stays a catalogue look.
        // FIRSTTEST2 2026-10-04 owner: 'I told it to change the yellow TO pink' ("change the yellow on the base paint and on the spray paint can to pink"): a LIST of places after a
        // colour target. "the base paint" / "the body" = the body-paint layers; any other named thing (not a car part: "the spray paint can", "the energy drink", "the bottle") with the
        // body named too = the buyer asked to include the ARTWORK that holds that colour (tg.artObjects; the app adds the art layers that hold it and says which). Words used up here are
        // never an unknown look ("spray" used to become a look).
        res.targets.forEach(function (tg) {
            if (tg.kind !== 'colour' || tg.parts || tg.object) return;
            var from = tg.at + String(tg.word).length, seg = rest.slice(from, from + 120), cut = /\s(?:to|into)\s/.exec(seg); if (cut) seg = seg.slice(0, cut.index);
            if (!/^ (?:on|in|inside) /.test(seg)) return;
            var phrases = [], cur = null, toks = seg.trim().split(' ');
            for (var q = 0; q < toks.length; q++) {
                var tk = toks[q];
                if (/^(?:on|in|inside)$/.test(tk)) { if (cur && cur.length) phrases.push(cur.join(' ')); cur = []; continue; }
                if (cur === null) break;
                if (tk === 'and' || tk === 'plus' || tk === 'also') { if (cur.length) phrases.push(cur.join(' ')); cur = []; continue; }
                if (!cur.length && /^(?:the|my|that|this|its|both|each|those|these)$/.test(tk)) continue;
                if (/^(?:to|into|with|then|so|please|make|give|turn|set|change|put|but|or|as|is|are|it|of|at|for|from|by|where|which)$/.test(tk) || lookScan(tk).looks.length || cw[tk]) break;
                cur.push(tk);
            }
            if (cur && cur.length) phrases.push(cur.join(' '));
            if (!phrases.length) return;
            var BODY_PH = /^(?:(?:base|body|main|whole|entire)(?: (?:car|truck|paint|paintwork|colou?r|layers?|coat))?|car|truck|vehicle|paint|paintwork|bodywork|the car)$/;
            var bodyPh = phrases.filter(function (p) { return BODY_PH.test(p); }), partPh = phrases.filter(function (p) { return !BODY_PH.test(p) && PART_WORDS.some(function (pw) { return pw[1].test(' ' + p + ' '); }); });
            var objPh = phrases.filter(function (p) { return !BODY_PH.test(p) && partPh.indexOf(p) === -1 && !NUMBERS_RE.test(p) && !SPONSORS_RE.test(p); });
            if (!bodyPh.length || partPh.length) return;          // object only ("the yellow on the spray can"): the ROUTER-FIX object flow (layers + a box) below stays
            tg.bodyNamed = true; if (objPh.length) tg.artObjects = objPh;
            var used = {}; phrases.forEach(function (p) { p.split(' ').forEach(function (w) { used[w] = 1; }); });
            left = left.filter(function (w) { return !used[w]; });
        });
        var leftSet = {}; left.forEach(function (w) { leftSet[w] = 1; });
        res.targets.forEach(function (tg) {
            if (tg.kind !== 'colour' || tg.parts || tg.object || tg.bodyNamed) return;
            var after = rest.slice(tg.at + String(tg.word).length, tg.at + String(tg.word).length + 60), m = SCOPE_PREP.exec(after);
            var tail = (m ? after.slice(m[0].length) : after).replace(/^ (?:the|my|that|this|each|both|those|these) /, ' '), words = tail.trim().split(' '), obj = [];
            for (var k = 0; k < words.length && obj.length < 3; k++) {
                var wd = words[k];
                if (!wd || OBJ_STOP.test(wd) || lookScan(wd).looks.length || (Dz().parseColours && Dz().parseColours(wd).length) || cw[wd]) break;
                obj.push(wd);
            }
            if (!obj.some(function (w) { return leftSet[w]; })) return;
            if (!m && !(res.looks.length || actCols.length || res.rel || res.shade || res.pop || SAME_RE.test(t))) return;
            tg.object = obj.join(' ');
            left = left.filter(function (w) { return obj.indexOf(w) === -1; });
        });
        res.leftover = left; res.ext = (!res.looks.length && left.length && left.length <= 3) ? left.join(' ') : null;
        res.inherits = !res.targets.length && /\b(it|them|that|those|these|this|same|one)\b/.test(t) || (!res.targets.length && (res.looks.length || res.colours.length || res.rel || res.shade) && !res.hasVerb) || (!res.targets.length && /\b(make|give|have|put)\b/.test(t) && /\b(it|them|that)\b/.test(t));
        return res;
    }

    // ------------------------------------------------------------------ chips: complete sentences a buyer can tap
    var STARTER_LOOK = { black: 'matte', charcoal: 'satin', grey: 'satin chrome', silver: 'chrome', white: 'pearl', red: 'candy', orange: 'satin', yellow: 'powder coat', green: 'pearl', teal: 'metallic', blue: 'metallic', purple: 'candy', pink: 'pearl', brown: 'satin', tan: 'matte' };
    function chipFor(name, lookLabel) { return 'Make the ' + name + ' ' + lookLabel; }
    // VISIBLE_COLOUR 2026-10-04 (owner law: "a colour on the car" = the colour the buyer SEES): a paint colour that a zone repaints is listed by what still SHOWS of it
    function visOf(e) { return e.shown != null ? e.shown : e.share; }
    function topNames(pal, n) { return pal.filter(function (e) { return visOf(e) >= 1.5; }).sort(function (a, b) { return visOf(b) - visOf(a); }).slice(0, n || 4); }
    function zoneLine(zcols) {          // VISIBLE_COLOUR: the colours the ZONES paint, grouped by colour name, biggest first: "pink (“GTA Pink”, “Number Fill” +2, 22%)"
        var by = {}, items = [];
        (zcols || []).slice().sort(function (a, b) { return (Number(b.share) || 0) - (Number(a.share) || 0); }).forEach(function (z) { if (z.share != null && z.share < 0.3) return; var g = by[z.name]; if (!g) { g = by[z.name] = { name: z.name, fam: z.fam, hex: z.hex, share: 0, zones: [] }; items.push(g); } g.share += Number(z.share) || 0; g.zones.push(z.zone); });
        items.sort(function (a, b) { return b.share - a.share; });
        return { items: items, text: items.slice(0, 5).map(function (g) { return g.name + ' (' + g.zones.slice(0, 2).map(function (nm) { return '“' + nm + '”'; }).join(', ') + (g.zones.length > 2 ? ' +' + (g.zones.length - 2) : '') + (g.share ? ', ' + (g.share < 1 ? 'under 1' : Math.round(g.share)) + '%' : '') + ')'; }).join(', ') };
    }
    function paletteLine(pal) { return topNames(pal, 6).map(function (e) { return e.name + ' (' + Math.round(visOf(e)) + '%)'; }).join(', '); }
    function suggestions(pal, layers) {
        var out = [], used = {};
        topNames(pal, 3).forEach(function (e) { var k = e.name; if (used[k]) return; used[k] = 1; var lk = STARTER_LOOK[e.fam] || 'satin'; out.push(chipFor(e.name, lk)); });
        var hasNum = (layers || []).some(function (l) { return l.role === 'numbers' && !l.hidden; });
        if (hasNum) out.push('Make the numbers metallic');
        out.push('Make the colours pop');
        return out.slice(0, 5);
    }
    function describe(pal, layers, zcols) {
        var top = topNames(pal, 6), zl = zoneLine(zcols), first = top[0] || zl.items[0], hid = pal.filter(function (e) { return e.hidden && e.hidden.length && e.share - visOf(e) >= 1.5 && visOf(e) < e.share * 0.5; });          // VISIBLE_COLOUR: zones' colours + the paint that still shows
        if (!first) return { text: 'I cannot read the paint yet: wait for the car to show in the preview, then ask again.', chips: [] };
        var nums = (layers || []).filter(function (l) { return l.role === 'numbers' && !l.hidden; }).length, sp = (layers || []).filter(function (l) { return l.role === 'sponsors' && !l.hidden; }).length;
        var t = 'Here is what I can see on your car: ' + (zl.items.length ? zl.text + (top.length ? '; from the paint itself: ' + paletteLine(pal) : '') : paletteLine(pal)) + '.' + (hid.length ? ' Under your zones (not showing now): ' + hid.slice(0, 3).map(function (e) { return (visOf(e) >= 0.5 ? 'most of the ' : 'the ') + e.name + ' (under “' + e.hidden[0].zone + '”)'; }).join(', ') + '.' : '') + (nums || sp ? ' It also has ' + [nums ? 'a numbers layer' : null, sp ? 'sponsor / logo layers' : null].filter(Boolean).join(' and ') + '.' : '') + ' Tell me what to do with any of them, for example “' + chipFor(first.name, STARTER_LOOK[first.fam] || 'satin').toLowerCase().replace(/^make/, 'make') + '”.';
        return { text: t, chips: suggestions(pal, layers) };
    }
    var BIG_LOOKS = ['matte', 'satin', 'gloss', 'powder coat', 'chrome', 'metallic', 'pearl'];
    function askWhat(prefixTarget, pal) { return BIG_LOOKS.slice(0, 5).map(function (l) { return chipFor(prefixTarget, l); }); }

    // ------------------------------------------------------------------ shade words (darker / lighter / brighter ...) -> a new hex from the colour that is there
    function shadeHex(hex, word) {
        var q = hsl(hex);
        if (/neon|fluorescent|fluoro|day glo|electric/.test(word)) return fromHsl(q.h, 1, 0.5);
        if (/darker|deeper|richer/.test(word)) return fromHsl(q.h, Math.min(1, q.s * 1.05), q.l * 0.68);
        if (/lighter|paler/.test(word)) return fromHsl(q.h, q.s * 0.9, Math.min(0.92, q.l + (1 - q.l) * 0.38));
        if (/brighter|bolder|more vivid|more saturated/.test(word)) return fromHsl(q.h, Math.min(1, q.s * 1.2 + 0.05), Math.min(0.68, q.l + 0.1));
        return fromHsl(q.h, q.s * 0.55, q.l);                          // washed out / faded / muted / subdued / less saturated
    }
    function applyQual(hex, qual) { if (!qual) return hex; var q = hsl(hex); if (qual === 'dark' || qual === 'deep') return fromHsl(q.h, q.s, Math.min(q.l, 0.3)); if (qual === 'light' || qual === 'pale') return fromHsl(q.h, q.s * 0.8, Math.max(q.l, 0.72)); if (qual === 'bright' || qual === 'neon') return fromHsl(q.h, Math.min(1, q.s * 1.2 + 0.1), 0.5); return hex; }

    // ------------------------------------------------------------------ PLAN: sentence -> ops (null = not an edit-of-what-is-there sentence: the older handlers get it)
    // WP7 2026-10-03: "rgb(255, 0, 128)" / "rgb 10 200 30" -> #hex (the colour reader only knows names and #hex)
    function rgbToHex(text) { return String(text).replace(/\brgb\s*\(?\s*(\d{1,3})\s*[ ,]\s*(\d{1,3})\s*[ ,]\s*(\d{1,3})\s*\)?/gi, function (m, r, g, b) { function h(v) { v = Math.min(255, +v); return (v < 16 ? '0' : '') + v.toString(16); } return '#' + h(r) + h(g) + h(b); }); }
    // W7 2026-10-03: normalize a direct "put/paint/apply <known look or colour> on <one named part" order
    // into the target-first grammar. Keep this strict: extra clauses stay with the stack/help owners.
    function partFirstAssignment(text) {
        var m = /^\s*(?:(?:please|hey|ok|okay|now)\s+)*(?:(?:can|could|would) you\s+|i want you to\s+)?(?:please\s+)?(?:put|paint|apply|place)\s+(?:(?:only|just)\s+)?(.+?)\s+(?:on|onto)\s+(.+?)\s*(?:,\s*please)?[.!?]*\s*$/i.exec(String(text || ''));
        if (!m) return text;
        var tail = m[2].replace(/\bplease\b\s*[.!?]*$/i, '').replace(/[.!?,]+$/g, '').trim(), parsed = parseClause(tail);
        if (!parsed || parsed.targets.length !== 1 || parsed.targets[0].kind !== 'part' || parsed.leftover.length || parsed.colours.length || parsed.looks.length || parsed.rel || parsed.shade || parsed.pop || parsed.recipe || parsed.ext) return text;
        return 'make the ' + parsed.targets[0].part + ' ' + m[1].trim();
    }
    // COPILOT-FIX 2026-10-04: colour words the colour list does not know that only tint the colour after them ("tangerine orange" read "tangerine" as an unknown LOOK and sent the request to the AI)
    var TINT_COLOURS = { tangerine: '#f28500', mandarin: '#f37a48', pumpkin: '#ff7518', papaya: '#ff9a3c', persimmon: '#ec5800', apricot: '#fbb46e', bubblegum: '#ff7eb6', flamingo: '#fc8eac', fuchsia: '#e0218a', mint: '#98ff98' };
    function tintName(hex, semantic) { var h = String(hex || '').toLowerCase(), k; for (k in TINT_COLOURS) if (TINT_COLOURS[k] === h) return k; if (semantic) return familyOf(hex); return Dz().nameColour ? Dz().nameColour(hex) : h; }
    function tintColours(text) { var C = Dz().COLOURS || {}; return String(text).replace(/\b(tangerine|mandarin|pumpkin|papaya|persimmon|apricot|bubblegum|flamingo|fuchsia|mint)(\s+(?:orange|pink|green))?\b/gi, function (m, w) { w = w.toLowerCase(); return C[w] || C[m.toLowerCase()] ? m : TINT_COLOURS[w]; }); }
    // COPILOT-FIX 2026-10-04: a LAYER named in the sentence ("in the Numbers layer, all the pink to metallic silver", "make the Numbers layer gold") is a scope / a target,
    // never the look "Layered Cut Foil". Returns { layers:[real layer name], rest } or { ask } or null.
    var LAYER_ROLE_WORDS = { numbers: /^numbers?$/, sponsors: /^(sponsors?|logos?|decals?)$/, stripes: /^(stripes?|tape)$/, body: /^(body|base|paint|body paint)$/ };
    function layerScope(text, layers) {
        var raw = String(text || ''), lm = /\blayer\b\s*[,:]?/i.exec(raw); if (!lm) return null;
        var pre = raw.slice(0, lm.index).replace(/\s+$/, ''), words = pre.split(/\s+/), ls = (layers || []).filter(function (l) { return l && l.name; }), hit = [], k, used = 0;
        function find(nn) {
            var h = ls.filter(function (l) { return norm(l.name) === nn; });
            if (!h.length) h = ls.filter(function (l) { var ln = norm(l.name); return ln.indexOf(nn + ' ') === 0 || (nn.length >= 4 && ln.indexOf(nn) !== -1); });
            if (!h.length) Object.keys(LAYER_ROLE_WORDS).forEach(function (rk) { if (h.length || !LAYER_ROLE_WORDS[rk].test(nn)) return; h = ls.filter(function (l) { var r = String(l.role || '').toLowerCase(); return rk === 'numbers' ? r === 'numbers' : (rk === 'sponsors' ? /logo|sponsor|decal/.test(r) : (rk === 'stripes' ? /tape|stripe/.test(r) : /body/.test(r))); }); });
            return h;
        }
        for (k = Math.min(4, words.length); k >= 2 && !hit.length; k--) { var cx = norm(words.slice(words.length - k).join(' ')), hx = ls.filter(function (l) { return norm(l.name) === cx; }); if (hx.length) { hit = hx; used = k; } }          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a: the LONGEST exact layer name wins ("Black Base layer" is the Black Base layer, never "base" = the first *Base layer)
        for (k = 1; k <= Math.min(4, words.length) && !hit.length; k++) { var cand = norm(words.slice(words.length - k).join(' ')); if (!cand || /^(the|my|a|an|that|this|all)$/.test(cand)) continue; hit = find(cand); if (hit.length) used = k; }
        var nameWords = words.slice(words.length - (used || 1)), name = nameWords.join(' ');
        if (/^(a|an|one|new|another|top|bottom|clear|that|this|the|my)$/i.test(name)) return null;
        if (!hit.length) return { ask: { kind: 'ask', text: 'I cannot find a layer called “' + name + '” in this file.' + (ls.length ? ' Your layers: ' + ls.slice(0, 12).map(function (l) { return l.name; }).join(', ') + '.' : ' This paint has no layers.'), chips: [] } };
        var head = words.slice(0, words.length - used).join(' ').replace(/(?:^|\s+)(?:(?:in|on|of|inside|within|for)\s+)?(?:the|my|that)$/i, '').replace(/(?:^|\s+)(?:in|on|of|inside|within|for)$/i, '');
        var rest = (head + ' ' + raw.slice(lm.index + lm[0].length)).replace(/\s+/g, ' ').replace(/^\s*[,;:]\s*/, '').trim();
        return { layers: [hit[0].name], word: hit[0].name, rest: rest };
    }
    // ROUTER-FIX 2026-10-04 (owner T2 "You covered up some of the white stripes near the back. That should stay white", T5 "You changed the white base to pink and should not
    // have touched that or the white blocks on the back of each side" -> "I do not know a look called 'changed base'"): a COMPLAINT about the last change is a CORRECTION of it,
    // never a new request ("you made the white pink" is a complaint, "make the white pink" a request). Returns { kind:'complaint', colours, result, names, elements, places, soft } or null.
    // soft = "put the white back" / "undo that on the white": the caller may fall back to the older revert of the helper's own zone when the last change did not touch it.
    var CMP_STRONG = [/\byou (?:have |just |also |then |even )?(?:changed|made|turned|painted|covered|recolou?red|messed|ruined|broke|touched|removed|lost|wiped|replaced|repainted|took|killed|overwrote|went over|swapped|switched|did that|did this|did it)\b/,
        /\b(?:should(?:n t| not| nt)(?: have)?|was(?:n t| not) (?:supposed|meant)|did(?:n t| not) (?:ask|want|tell|say)|never (?:asked|said|wanted|told))\b/,
        /\b(?:should|needs? to|has to|must|is (?:supposed|meant) to|was (?:supposed|meant) to|ought to) (?:stay|remain|be left|be kept|still be|have stayed|have stay)\b/,
        /^(?:no )?(?:that|this|it)(?: is| s| was) (?:wrong|not right|bad|incorrect|a mistake|not what i (?:wanted|asked for|asked|meant))\b/,
        /^(?:no )?(?:please )?(?:don t|do not|dont|never) (?:touch|change|paint over|cover) (?:the|my|that|those|any)\b/,
        /\b(?:got|is|are|was|were|has been|have been) (?:covered|painted over|gone|lost|ruined|wiped out)\b|\b(?:disappeared|vanished)\b/];
    var CMP_SOFT = [/^(?:please )?put (?:the |my |all the |all of the )?(?:\w+ ){0,3}back\b(?!.*\b(?:make|paint|turn)\b)/, /^(?:please )?undo (?:that |it |this |the last(?: change| one)? )?(?:on|for|from|in|to) (?:the |my )/, /^(?:please )?(?:bring|get) (?:the |my )(?:\w+ ){0,3}back\b/];
    function complaint(text, env) {
        var raw = String(text || ''), t = norm(raw.replace(/[‘’']/g, ' ')).replace(/\s+/g, ' ').trim(); if (!t || t.length > 400) return null;
        if (/^(?:why|what|how|can|could|would|will|is it|are you|do you|does)\b/.test(t) && /\?\s*$/.test(raw)) return null;          // a question about it: the help brain answers
        var strong = CMP_STRONG.some(function (re) { return re.test(t); }), soft = !strong && CMP_SOFT.some(function (re) { return re.test(t); });
        if (!strong && !soft) return null;
        if (!/^(?:no |ok |okay |hey |but |um |so )?you\b/.test(t) && /^(?:please )?(?:make|paint|turn|set|give|add|apply|recolou?r|swap|switch|change)\b/.test(t) && !/\b(?:back|undo|you (?:changed|made|turned|painted|covered))\b/.test(t)) return null;          // "make the black matte, the white should stay white" is a request with a constraint
        var tt = ' ' + t + ' ', cols = (Dz().parseColours ? Dz().parseColours(t) : []).slice().sort(function (a, b) { return a.at - b.at; }), colours = [], result = null, colWord = {};          // parseColours positions are into ' ' + text
        cols.forEach(function (c) { colWord[c.name] = 1; });
        cols.forEach(function (c, i) {
            var before = tt.slice(Math.max(0, c.at - 16), c.at), prev = cols[i - 1], between = prev ? tt.slice(prev.at + prev.name.length, c.at) : null;
            if (i > 0 && /\b(?:to|into)\s+(?:the\s+|a\s+|that\s+|this\s+)?(?:same\s+)?(?:\w+\s+)?$/.test(before)) { if (!result) result = { word: c.name, hex: c.hex }; return; }          // "changed the white base to pink"
            if (prev && between !== null && /^\s*$/.test(between)) { if (!result) result = { word: c.name, hex: c.hex }; return; }          // "you made the white pink": pink is what it became
            if (/\byou (?:\w+ ){0,2}(?:painted|made|turned|changed) (?:it|them|that|those|everything|the \w+|my \w+) $/.test(tt.slice(0, c.at))) { if (!result) result = { word: c.name, hex: c.hex }; return; }          // "you turned the roof pink"
            if (!colours.some(function (x) { return x.word === c.name; })) colours.push({ word: c.name, hex: c.hex });
        });
        var names = [], m, NP = /\b(?:the|my|those|these|that|all the)\s+((?:[a-z]+\s+){0,2}[a-z]+)/g, NSTOP = /^(?:back|rear|front|same|way|car|truck|whole|rest|last|one|ones|thing|things|change|changes|part|parts|bit|bits|side|sides|left|right|top|bottom|middle|stuff|colou?rs?|paint)$/;
        while ((m = NP.exec(t))) {
            var words = m[1].split(' '), keep = [];
            for (var k = 0; k < words.length; k++) { if (/^(?:to|on|in|of|at|near|and|or|but|should|that|is|was|were|are|be|stay|you|it|i|s|t|got|back|not|what|have|has|had|did|do|does|been|now|again|too|also|any|some|alone|untouched)$/.test(words[k]) || (k > 0 && colWord[words[k]])) break; keep.push(words[k]); }
            if (!keep.length || (keep.length === 1 && NSTOP.test(keep[0]))) continue;
            if (keep.length === 1 && cols.some(function (c) { return c.name === keep[0]; })) continue;          // "the white" alone is a colour, not a name
            if (placeParts(keep.join(' ')).length || /^(?:back|rear|front)\b/.test(keep[0])) continue;          // "on the left side" / "the back of each side" is a PLACE (cp.places), never a zone name
            var ph = keep.join(' '); if (names.indexOf(ph) === -1) names.push(ph);
        }
        var elements = []; if (NUMBERS_RE.test(t)) elements.push('numbers'); if (SPONSORS_RE.test(t)) elements.push('sponsors'); if (/\b(?:stripes?|pinstripes?|tape)\b/.test(t)) elements.push('stripes');
        var places = placeParts(t);
        if (/\b(?:each|both) sides?\b/.test(t) && !places.length) places = ['left side', 'right side'];
        return { kind: 'complaint', colours: colours, result: result, names: names, elements: elements, places: places, soft: soft, whole: !colours.length && !names.length && !elements.length && !places.length, text: t };
    }
    function plan(text, env) {
        env = env || {}; var raw0 = String(text || ''), force = /\banyway\b/i.test(raw0);
        text = tintColours(raw0.replace(/\s*\banyway\b\s*/ig, ' ').trim()).replace(/\s*(?:->|=>|\u2192|\u21d2)\s*/g, ' to ');          // FIRSTTEST: "yellow -> purple chrome" = from yellow to purple
        var cmp0 = complaint(raw0, env); if (cmp0 && !cmp0.soft) return cmp0;          // ROUTER-FIX: a complaint is never a look name ("changed base")
        var sc = /\blayer\b/i.test(text) ? layerScope(text, env.layers) : null;
        if (sc && sc.ask) return sc.ask;
        var pl = planCore(sc ? sc.rest : text, sc ? Object.assign({}, env, { _layerScope: sc.layers }) : env);
        if (pl && pl.kind === 'ops') {
            if (sc) pl.ops.forEach(function (op) {
                var tg = op.target; if (!tg) return;
                if (tg.kind === 'colour') { op.target = Object.assign({}, tg, { layers: sc.layers.slice() }); }
                else if (tg.kind === 'body' || tg.kind === 'main' || (tg.kind === 'numbers' && /number/i.test(sc.word)) || (tg.kind === 'sponsors' && /logo|sponsor|decal/i.test(sc.word))) op.target = { kind: 'layer', layers: sc.layers.slice(), word: sc.word };
            });
            if (sc) pl.layerScope = sc.layers.slice();
            if (force) pl.force = true;
            pl.raw = raw0;
            // ROUTER2 2026-10-04 (owner T1 "... to the same color pink you use on the numbers and on the black near the rear of the car and back bumper"): a trailing
            // "and on the <colour> near / on the <place>" is one more TARGET of that colour (it was read as part of the colour phrase and silently dropped)
            try {
                var lm = /\b(?:and|also)\s+(?:on\s+|to\s+)?(?:all\s+)?the\s+(black|white|yellow|red|blue|green|orange|purple|pink|gr[ae]y|silver|gold)\s+((?:near|on|at|around|by|towards|in)\s+the\s+[a-z ]+?)\s*(?:[.!?]|$)/i.exec(raw0), lastC = null;
                pl.ops.forEach(function (op) { if (op.colour) lastC = op.colour; });
                if (lm && lastC && !pl.ops.some(function (op) { return op.target && op.target.kind === 'colour' && op.target.word === lm[1].toLowerCase() && !op.target.object; })) {
                    var subP = planCore(tintColours('make the ' + lm[1] + ' ' + lm[2] + ' ' + (lastC.name || 'pink')), env);
                    if (subP && subP.kind === 'ops') subP.ops.forEach(function (op) { if (op.target && op.target.kind === 'colour' && op.target.parts && op.target.parts.length) { op.colour = lastC; pl.ops.push(op); } });
                }
            } catch (eLo) {}
        }
        return pl;
    }
    function stripSamePartFinishPreservation(raw) {
        var src = String(raw || ''), split = /^(.*?)(?:\s+(?:and|while)\s+|\s*[,;]\s*|\.\s+)(.+?)[.!?]*$/i.exec(src);
        if (!split) return null;
        var prefix = split[1].trim(), tail = split[2].trim();
        var partNames = PART_WORDS.map(function (x) { return x[0]; });
        var colourWords = '(?:red|blue|green|yellow|orange|purple|pink|black|white|gray|grey|silver|gold|brown|teal|cyan|magenta|maroon|navy|lime|olive|bronze|copper)';
        var ref = '(?:(?:its|their)\\s+|the\\s+(?:hood|bonnet|roof|trunk|deck ?lid|rear deck|truck bed|pickup bed|cargo bed|front bumper|nose|rear bumper|tail|spoiler|wing|left side|left door|driver side|driver door|right side|right door|passenger side|passenger door)(?:\\x27s)?\\s+)?';
        var preserveColor = new RegExp('^(?:' +
            '(?:keep(?:ing)?|retain(?:ing)?|preserv(?:e|ing)|leav(?:e|ing))\\s+' + ref +
            '(?:the\\s+)?(?:(?:current|existing|original)\\s+)?(?:(?:' + colourWords + ')\\s+)?(?:paint(?:\\s+colou?r)?|colou?r)(?:\\s+(?:alone|as\\s+is|unchanged|intact))?' +
            '|(?:do\\s+not|don\\x27t|dont)\\s+(?:change|alter|modify)\\s+' + ref +
            '(?:(?:current|existing|original)\\s+)?(?:(?:' + colourWords + ')\\s+)?(?:paint\\s+)?colou?r(?:\\s+as\\s+is)?' +
            '|(?:do\\s+not|don\\x27t|dont)\\s+(?:recolou?r)\\s+(?:(?:its|it)\\b)' +
            '|' + ref + 'paint\\s+should\\s+stay\\s+' + colourWords +
            '|(?:keep|leave)\\s+the\\s+(?:hood|bonnet|roof|trunk|deck ?lid|rear deck|truck bed|pickup bed|cargo bed|front bumper|nose|rear bumper|tail|spoiler|wing|left side|left door|driver side|driver door|right side|right door|passenger side|passenger door)\\s+' + colourWords +
            ')(?:(?:,?\\s+(?:and|while)\\s+|,\\s*)(?:(?:leave|keep|retain|preserve)\\s+)?' + ref + '(?:region(?:\\s+mask)?|mask)(?:\\s+(?:alone|unchanged|intact))?)?$', 'i');
        if (!preserveColor.test(tail) || /\\b(?:whole|entire|everything|body|car|truck|vehicle|all|every)\\b/i.test(tail)) return null;
        var p = parseClause(prefix), target = p && p.targets.length === 1 && p.targets[0];
        if (!target || target.kind !== 'part' || partNames.indexOf(target.part) < 0 || p.looks.length !== 1 || p.colours.length || p.rel || p.shade || p.pop || p.keep || p.ext || p.recipe || p.sub || p.leftover.length) return null;
        var mentioned = [];
        PART_WORDS.forEach(function (pw) { if (pw[1].test(tail)) mentioned.push(pw[0]); });
        if (mentioned.some(function (part) { return part !== target.part; }) || new Set(mentioned).size > 1) return null;
        return { prefix: prefix, target: target.part, tail: tail };
    }
    function planCore(text, env) {
        env = env || {}; text = rgbToHex(text); var assignedExcept = false;
        // A tightly bounded preservation clause may follow one complete, known
        // part-finish command. Strip only the verified tail; never discard a
        // second action, a different part, or an unrecognized constraint.
        var preservedFinish = stripSamePartFinishPreservation(text);
        if (preservedFinish) text = preservedFinish.prefix;
        // AI/offline sprint W7: preserve explicit prohibitions before the
        // normalizer can discard "do" and expose a positive make/paint command.
        var prohibition = String(text || '').replace(/[\u2018\u2019]/g, "'");
        if (/\b(?:do\s+not|don't|dont|never)\s+(?:(?:ever|please)\s+)?(?:make|paint|repaint|change|recolou?r|set|turn|apply|add|remove|give|put)\s+(?!(?:the\s+)?(?:rest|other|remaining|every\s+other)\b)/i.test(prohibition)) {
            var locked = preservedParts(prohibition);
            if (locked.length) return preservedPartAsk(locked, text);
            return { kind: 'ask', prohibited_edit: true, text: 'Nothing was changed. I treated the negative instruction as a request to leave the paint alone. Send any separate change as its own request.', chips: [] };
        }
        text = String(text || '').replace(/(?:,\s*)?\s+please\s*[.!?]*\s*$/i, '').trim();
        // W12 2026-10-04: a narrowly scoped condition such as "keep its current
        // chrome finish" does not ask E to change the finish. Accept it only
        // when the entire preceding request already parses as one complete,
        // colour-only assignment to one known part, and the tail names a
        // recognized finish without adding any other instruction.
        var currentFinishTail = /^(.*?)\s+(?:(?:and\s+)?(?:keep|retain|leave)\s+its\s+(?:current|existing|original)\s+(?:matte|satin|glossy?|wet\s+look|chrome|metallic|pearl|candy|powder\s+coat|brushed|frosted)\s+finish(?:\s+as\s+is)?(?:\s*[,;]\s*the\s+rest\s+of\s+the\s+car\s+is\s+already\s+right)?|(?:and\s+)?leave\s+all\s+other\s+parts\s+alone|the\s+rest\s+of\s+the\s+car\s+is\s+already\s+right)[.!?]*$/i.exec(String(text));
        if (currentFinishTail) {
            var finishBase = currentFinishTail[1].trim(), finishClause = parseClause(finishBase);
            var finishTarget = finishClause && finishClause.targets.length === 1 && finishClause.targets[0];
            if (finishTarget && finishTarget.kind === 'part' && PART_WORDS.some(function (pw) { return pw[0] === finishTarget.part; }) &&
                finishClause.colours.length === 1 && !finishClause.looks.length && !finishClause.rel && !finishClause.shade && !finishClause.pop &&
                !finishClause.keep && !finishClause.ext && !finishClause.recipe && !finishClause.sub && !finishClause.leftover.length) {
                text = finishBase;
            }
        }
        // WP7: "make the whole car matte except the roof should be glossy" = two jobs (the car matte, the roof gloss), not an exclusion
        text = String(text).replace(/^(.*?)\s+except\s+(?:for\s+)?((?:the\s+)?(?:roof|hood|trunk|bonnet|spoiler|wing|bumpers?|(?:left|right|driver|passenger)s?\s+(?:side|door)|sides?|doors?|numbers?|sponsors?|stripes?))\s+(?:should be|should look|to be|is|are|being|which should be|that should be|can be)\s+(.+)$/i, function (m, head, target, action) { assignedExcept = true; return head + ', and ' + target + ' ' + action; });
        // A positive except-clause overrides a whole-body assignment with its own
        // named-panel job. Both assignments must compile before either is applied.
        var assigned = /^(.*?)\s*,?\s+except(?: for)?\s+((?:make|paint|turn|set|recolou?r|apply)\s+.+)$/i.exec(String(text));
        if (assigned && /\b(?:whole|entire|all)\b/.test(norm(assigned[1])) && /\b(?:body|bodywork|car|truck|vehicle|paint|everything)\b/.test(norm(assigned[1])) && PART_WORDS.some(function (pw) { return pw[1].test(norm(assigned[2])); })) {
            assignedExcept = true; text = assigned[1] + ', and ' + assigned[2];
        }
        text = String(text).replace(/\brepaint\b/gi, 'paint');
        var t = fixText(text); if (!t) return null;
        var protectedPanels = preservedParts(text); if (protectedPanels.length) return preservedPartAsk(protectedPanels, text);
        text = partFirstAssignment(text); t = fixText(text); if (!t) return null;
        var pal = prepPalette(env.palette), layers = env.layers || [], last = env.last || null;
        CTX.pal = pal; CTX.prevColour = false;
        text = String(text).replace(STAYS_RE, function (m) { return /^[,;]/.test(m) ? ', ' : ' '; }).trim(); t = fixText(text); if (!t) return null;
        var xcp = extractExcept(text), exclude = xcp.list; if (exclude.length) { text = xcp.text; t = fixText(text); }
        // WP7 2026-10-03: "add a big number 7 on the roof" / "put a dragon on the hood": drawing something NEW is not an edit of what is there (a look word keeps it ours: "add a pearl finish to the white")
        if (/^(?:(?:please|hey|ok|okay)\s+)?(?:(?:can|could|would) you\s+)?(?:i want you to\s+)?(?:add|draw|put|place|create|insert|write|stick|paint on)\s+(?:a|an|some|new|another|my name|the word|the text)\b/.test(t) && !/\b(finish|look|effect|coat|coating|sheen|shine|gloss|glossy|matte|metallic|chrome|pearl|candy|satin|powder|wet|brushed|frosted)\b/.test(t)) return null;
        if (DESCRIBE_RE.test(t)) { var d = describe(pal, layers, prepZoneColours(env.zoneColours)); return { kind: 'describe', text: d.text, chips: d.chips }; }
        // "show me options for the yellow": a gallery of looks on ONE target (the app tries each and shows thumbnails)
        if (VARIANTS_RE.test(t) && !/\b(liver(y|ies)|scheme|theme|design|whole car)\b/.test(t)) {
            var vc = parseClause(t), vt = vc.targets.filter(function (x) { return x.kind !== 'body' && x.kind !== 'allpop'; })[0];
            if (!vt && last && last.targets && last.targets.length && !WHOLE_RE.test(t)) vt = last.targets[0];
            if (vt) return { kind: 'variants', target: vt, looks: variantLooks(vt, pal), text: t };
        }
        // "swap the black and the yellow": each takes the other's colour exactly (the selection is made on the ORIGINAL paint, so both can move at once)
        if (/\b(swap|switch|flip|trade|exchange)\b/.test(t) && !/ for /.test(t)) {
            var sc = (Dz().parseColours ? Dz().parseColours(t) : []);
            if (sc.length >= 2) {
                var ea = resolveColour(wantFor(sc[0].name, sc[0].hex, null), pal), eb = resolveColour(wantFor(sc[1].name, sc[1].hex, null), pal);
                if (ea.entries.length && eb.entries.length && ea.entries[0].hex !== eb.entries[0].hex) {
                    var A = ea.entries[0], B = eb.entries[0], blank = { look: null, rel: null, soft: false, strong: false, shade: null, keep: false, pop: false, recipe: null, sub: null, ext: null };
                    return { kind: 'ops', ops: [Object.assign({ target: { kind: 'colour', word: sc[0].name, hex: sc[0].hex }, colour: { name: B.name, hex: B.hex, exact: true } }, blank), Object.assign({ target: { kind: 'colour', word: sc[1].name, hex: sc[1].hex }, colour: { name: A.name, hex: A.hex, exact: true } }, blank)], alt: [], unknown: [], text: t, swap: true };
                }
            }
        }
        // "put the yellow back", "undo the numbers": take back what THIS helper did to that target
        if (/^(?:please )?(?:undo|revert|cancel)(?: (?:that|it|this|the last(?: one| change| edit| thing)?|last(?: one| change)?))?(?: please)?$/.test(t)) return null;          // WP7: a bare undo is the regular Undo, never a question
        if (REVERT_RE.test(t)) {
            var rc = parseClause(t.replace(REVERT_WORDS_RE, ' ')), rts = rc.targets.filter(function (x) { return x.kind !== 'body' && x.kind !== 'allpop'; });
            if (!rts.length && last && last.targets && (/\b(it|them|that|those)\b/.test(t) || /^(?:please )?(?:go back|step back|back)(?: a step)?(?: please)?$/.test(t)) && !/\b(last|everything|all)\b/.test(t)) rts = last.targets.slice();
            if (rts.length && !(rc.looks.length || rc.colours.length || rc.rel || rc.shade)) return { kind: 'revert', targets: rts, text: t };
        }
        // "a bit more" / "less": move the last look one step along its ladder (matte - satin - gloss - wet look, pearl - metallic - chrome)
        if (last && last.act && (MORE_RE.test(t) || LESS_RE.test(t))) {
            var mo = MORE_RE.test(t), la = last.act, nop = null;
            if (la.shade) nop = { shade: mo ? la.shade : (/darker|deeper|richer/.test(la.shade) ? 'lighter' : (/lighter|paler/.test(la.shade) ? 'darker' : 'faded')) };
            else if (la.look) {
                var lid = la.look, lk0 = lookById(lid), dirn = la.dir != null ? la.dir : (SHEEN.indexOf(lid) !== -1 ? (SHEEN.indexOf(lid) <= 1 ? -1 : 1) : 1), nl = stepLook(lid, mo ? dirn : -dirn);
                if (nl) nop = { look: nl }; else return { kind: 'ask', text: 'That is already as ' + (mo ? 'far' : 'gentle') + ' as the ' + (lk0 ? lk0.label : lid) + ' look goes. Want a different look?', chips: askWhat(last.label || 'car', pal) };
            }
            if (nop) { var mops = last.targets.map(function (tg) { return { target: tg, look: nop.look || null, colour: null, rel: nop.rel || null, soft: !!nop.soft, strong: !!nop.strong, shade: nop.shade || null, keep: false, pop: false, ext: null }; }); return { kind: 'ops', ops: mops, alt: [], unknown: [], text: t, usedLast: true }; }
        }
        if (QUESTION_RE.test(norm(text)) && !/\b(make|turn|change|set|paint|give)\b/.test(t)) return null;
        // WP7 2026-10-03 (red team: "What's the difference between metallic and pearl for sponsor logos", "Should the number be metallic silver or pearl white", "If I use a gradient ... will that affect", "Remember last week ... that matte green test?" all EDITED the car):
        // a question word that opens the sentence (or 'should the' / 'difference between' ...) makes it a question unless it opens with an imperative / polite request; a trailing '?' alone does NOT ("... keep the roof matte, yes?" is still an edit)
        var nQ = norm(text), POLITE_RE = /^(?:(?:please|hey|ok|okay|so|now|if possible|if you can)\s+)*(?:(?:can|could|would|will) you\s+|(?:is it possible to|would it be possible to|are you able to|is there a way to|any way to)\s+|i want you to\s+|i d like you to\s+|lets?\s+)?(?:please\s+)?(?:make|turn|change|set|paint|give|put|do|add|swap|switch|recolou?r|ghost|blackout|powder|chrome|matte|satin|gloss)\b/;
        var QWORD_RE = /^(?:whats?|what s|which|how|hows|why|where|when|who|is|are|does|do you|if|remember|recall|should|tell me|explain|any (?:idea|advice|suggest\w*)|recommend|suggest|wondering|i was wondering)\b|\b(?:should the|should i|should we|difference between|wondering if|will that|will it|does that|would it|is it better|which one (?:is|reads|looks))\b/;
        if (QWORD_RE.test(nQ) && !POLITE_RE.test(nQ)) return null;
        if (/\b(liver(y|ies)|scheme|retro|old school|throwback|theme|two tone|pinstripes? (and|with)|stripes (and|with)|surprise)\b/.test(t) && !/\b(the|all)\s+(black|white|red|blue|yellow|green|orange|purple|pink|grey|silver)\b/.test(t)) return null;
        var clauses = [], ops = [], pending = [], prev = null, alt = [], usedLast = false, usedSame = false;
        clauseList(text).forEach(function (raw) { var cc = parseClause(raw); clauses.push(cc); CTX.prevColour = cc.targets.some(function (x) { return x.kind === 'colour'; }); });
        function lastLook(c) { return c.looks.length ? c.looks[c.looks.length - 1] : null; }
        // FIRSTTEST2 2026-10-04 owner: 'I told it to change the yellow TO pink': a later clause's job lands on the SAME op (same zone, same pixels) as an earlier one
        function mergeClause(op, c) {
            var ll = lastLook(c); if (ll) op.look = (!op.look || ll.id === 'holographic') ? ll : (lookFor(op.look.id + ' ' + ll.id) || ll);
            if (c.ext && !op.look && !op.ext) op.ext = c.ext; if (c.colours.length && !op.colour) op.colour = c.colours[0]; if (c.rel && !op.rel) { op.rel = c.rel; op.soft = c.soft; op.strong = c.strong; }
            if (c.keep) op.keep = true; if (c.shade && !op.shade) op.shade = c.shade; if (c.pop) op.pop = true; if (c.recipe) op.recipe = c.recipe; if (c.sub && !op.sub) op.sub = c.sub; if (c.texture) op.texture = c.texture;
        }
        // ANAPHORA: "...the yellow to pink. Then a snakeskin on THAT PINK" / "give the new blue a flake" / "chrome the green" (green = what clause 1 makes, not on the car): the colour an
        // EARLIER clause of this message CREATES is not selectable on the source paint (zones select the SOURCE pixels), so the job binds to that earlier op. A colour already on the car binds
        // only with a reference word (that / the new / those ...): "make the yellow pink and make the black matte" keeps the black its own job.
        function bindToMade(c) {
            var bound = [];
            c.targets = c.targets.filter(function (tg) {
                if (tg.kind !== 'colour' || tg.parts || tg.object || tg.layers) return true;
                var wd = String(tg.word || '').replace(/[^a-z0-9 ]/g, ''), refd = !!wd && new RegExp('\\b(?:that|this|those|these|the new|new|same|said|resulting)\\s+(?:(?:dark|deep|light|pale|bright|neon|hot)\\s+)?' + wd + '\\b').test(c.raw);
                var onc = !refd && onCar(tg.word, tg.hex);
                var dest = ops.filter(function (op) { return op.colour && !op.keep && op.target && op.target.kind !== 'body' && (op.colour.name === tg.word || (op.colour.hex && tg.hex && familyOf(op.colour.hex) === familyOf(tg.hex))); });
                if (!dest.length) return true;
                dest.forEach(function (op) { if (bound.indexOf(op) === -1) bound.push(op); });
                return onc;          // "yellow -> green, then chrome the green" on a car that already has some green: ALL the green (the new + the old) gets it; "that green" = only the new
            });
            bound.forEach(function (op) { mergeClause(op, c); });
            return bound;
        }
        // WP7 2026-10-03: "matte, the black" / "chrome, the numbers please": the look comes first, the target second - hand the look to the target-only clause that follows
        if (clauses.length >= 2) { var c0 = clauses[0], c1 = clauses[1];
            if (!c0.targets.length && (c0.looks.length || c0.colours.length || c0.rel || c0.shade || c0.pop) && c1.targets.length && !(c1.looks.length || c1.colours.length || c1.rel || c1.shade || c1.pop || c1.ext) && !WHOLE_RE.test(c0.raw)) {
                ['looks', 'colours', 'rel', 'soft', 'strong', 'shade', 'keep', 'pop', 'recipe', 'sub'].forEach(function (k) { c1[k] = c0[k]; }); clauses.shift(); } }
        var leadAdd = /^\s*(?:(?:ok|okay|alright)\s+)?(?:now|and|also|then|next|plus|and now)\b/.test(t), firstClause = true;     // WP7: "now the sponsors" / "and the yellow" = the last job, on this target
        clauses.forEach(function (c) {
            var isFirst = firstClause; firstClause = false;
            if (c.alt && c.alt.length) alt = alt.concat(c.alt);
            var acts = !!(c.looks.length || c.colours.length || c.rel || c.shade || c.pop || c.keep || c.ext || c.recipe || c.texture);
            if (acts && c.targets.length && ops.length) { var bnd = bindToMade(c); if (bnd.length && !c.targets.length) { prev = { targets: bnd.map(function (op) { return op.target; }), ops: bnd }; pending = []; return; } }          // FIRSTTEST2
            if (!c.targets.length) {
                if (!acts) return;
                var targets = pending.length ? pending : (prev ? prev.targets : []);
                if (!targets.length && last && last.targets && last.targets.length && !WHOLE_RE.test(c.raw)) { targets = last.targets.slice(); usedLast = true; }          // "make it glossier" right after "make the black matte": it = the black
                if (!targets.length) { var bop = { target: { kind: 'body' }, look: lastLook(c), colour: c.colours[0] || null, rel: c.rel, soft: c.soft, strong: c.strong, shade: c.shade, keep: c.keep, pop: c.pop, recipe: c.recipe || null, sub: c.sub || null, ext: c.ext, texture: c.texture || null }; ops.push(bop); prev = { targets: [bop.target], ops: [bop] }; return; }
                if (!pending.length && prev && prev.ops.length) {          // "...purple and metallic": the second clause finishes the SAME job on the same target
                    prev.ops.forEach(function (op) { if (c.looks.length) op.look = op.look ? (lookFor(op.look.id + ' ' + lastLook(c).id) || lastLook(c)) : lastLook(c); if (c.ext && !op.look && !op.ext) op.ext = c.ext; if (c.colours.length && !op.colour) op.colour = c.colours[0]; if (c.rel && !op.rel) { op.rel = c.rel; op.soft = c.soft; op.strong = c.strong; } if (c.keep) op.keep = true; if (c.shade && !op.shade) op.shade = c.shade; if (c.pop) op.pop = true; if (c.recipe) op.recipe = c.recipe; if (c.sub && !op.sub) op.sub = c.sub; if (c.texture && !op.texture) op.texture = c.texture; });
                    return;
                }
                var made = []; targets.forEach(function (tg) { var op = { target: tg, look: lastLook(c), colour: c.colours[0] || null, rel: c.rel, soft: c.soft, strong: c.strong, shade: c.shade, keep: c.keep, pop: c.pop, recipe: c.recipe || null, sub: c.sub || null, ext: c.looks.length ? null : c.ext, texture: c.texture || null }; ops.push(op); made.push(op); });
                prev = { targets: targets, ops: made }; pending = []; return;
            }
            // ROUTER-FIX 2026-10-04: "the black near the rear of the car and back bumper": a clause that is ONLY a place continues the previous colour's scope (never a whole-part job)
            if (!acts && c.targets.length && c.targets.every(function (x) { return x.kind === 'part'; })) {
                var scopedPrev = (prev && prev.ops.length && prev.ops.every(function (op) { return op.target && op.target.kind === 'colour' && op.target.parts; })) ? prev.ops.map(function (op) { return op.target; }) : ((pending.length && pending.every(function (x) { return x.kind === 'colour' && x.parts; })) ? pending : null);
                if (scopedPrev) { scopedPrev.forEach(function (tg) { c.targets.forEach(function (x) { if (tg.parts.indexOf(x.part) === -1) tg.parts.push(x.part); }); }); return; }
            }
            // "make the numbers pink as well as the black base hexagon": "as well" / "too" inside ONE sentence = the earlier clause's action on this target
            if (!acts && SAME_RE.test(c.raw) && prev && prev.ops.length && !pending.length && c.targets.length) {
                var pa = prev.ops[0], mo = []; c.targets.forEach(function (tg) { var sop2 = { target: tg, look: pa.look, colour: pa.colour, rel: pa.rel, soft: pa.soft, strong: pa.strong, shade: pa.shade, keep: pa.keep, pop: pa.pop, recipe: null, sub: null, ext: null, texture: pa.texture || null }; ops.push(sop2); mo.push(sop2); }); prev = { targets: c.targets, ops: mo }; return;
            }
            if (!acts && (SAME_RE.test(c.raw) || (leadAdd && isFirst)) && last && last.act && !pending.length) {          // "do the same for the roof": the last action, on this target
                var sa = last.act; c.targets.forEach(function (tg) { var sop = { target: tg, look: sa.look ? lookById(sa.look) : null, colour: sa.colour || null, rel: null, soft: !!sa.soft, strong: !!sa.strong, shade: sa.shade || null, keep: !!sa.keep, pop: !!sa.pop, ext: null }; ops.push(sop); }); usedSame = true; prev = null; return;
            }
            if (!acts) { pending = pending.concat(c.targets); prev = null; return; }          // "make the hood ..." (the action comes with the next clause)
            if (pending.length && c.targets.length && pending.every(function (x) { return x.kind === 'colour' && x.parts; }) && c.targets.every(function (x) { return x.kind === 'part'; })) { pending.forEach(function (tg) { c.targets.forEach(function (x) { if (tg.parts.indexOf(x.part) === -1) tg.parts.push(x.part); }); }); c.targets = []; }          // ROUTER-FIX: "the black on the trunk and rear bumper satin": the bumper is more of the black's place
            var all = pending.concat(c.targets); pending = []; var madeOps = [];
            all.forEach(function (tg) { var op = { target: tg, look: lastLook(c), colour: c.colours[0] || null, rel: c.rel, soft: c.soft, strong: c.strong, shade: c.shade, keep: c.keep, pop: c.pop, recipe: c.recipe || null, sub: c.sub || null, ext: c.looks.length ? null : c.ext, texture: c.texture || null }; ops.push(op); madeOps.push(op); });
            prev = { targets: all, ops: madeOps };
        });
        var umm = UNKNOWN_PART_RE.exec(t); if (umm && /^lights?$/.test(umm[1]) && /^lights? (?:red|orange|yellow|gold|lime|green|teal|cyan|blue|navy|purple|violet|pink|magenta|white|silver|gr[ae]y|black|brown|maroon|bronze|copper|cream|tan|beige|aqua|turquoise|mint|lavender|lilac|coral|peach|olive|khaki)\b/.test(t.slice(umm.index))) umm = null;          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a: "make it light blue" is a colour, never "the light" (an unknown part)
        if (umm && !clauses.some(function (c) { return c.targets.length; }) && clauses.some(function (c) { return c.looks.length || c.colours.length || c.rel || c.shade || c.pop || c.recipe; })) return { kind: 'ask', text: 'I cannot tell where the ' + umm[1] + ' ' + (/s$/.test(umm[1]) ? 'are' : 'is') + ' on your paint (that is drawn art, not a named part). Tell me its colour instead (“the yellow ones”), or say “let me show you the parts of my car”.', chips: topNames(pal, 3).map(function (e) { return 'Make the ' + e.name + ' matte'; }) };
        if (!ops.length && pending.length && pending[0].kind !== 'body' && pending[0].kind !== 'main') {                 // a target and nothing to do with it: "the black" / "the numbers"
            var tg0 = pending[0];
            return { kind: 'ask', text: 'What should I do with ' + targetPhrase(tg0, pal) + '? Pick a look, or tell me a colour.', chips: askWhat(targetChipName(tg0, pal), pal) };
        }
        if (!ops.length) return null;
        // painter shorthand: ghost the stripes (same colour as the body, a different sheen), blackout the X (near-black satin)
        var main = topNames(pal, 1)[0] || null, ghostAsk = false;
        ops = ops.filter(function (op) {
            if (!op.recipe) return true;
            if (op.recipe === 'ghost') { if (!op.target || op.target.kind === 'body') op.target = { kind: 'accents', word: 'stripes' }; if (!main || main.share < 30) { ghostAsk = true; return false; } op.colour = { name: main.name, hex: main.hex }; op.look = op.look || lookById('matte'); op.pop = false; return true; }
            if (op.recipe === 'blackout') { if (!op.target || op.target.kind === 'body') return false; op.colour = { name: 'black', hex: '#0d0d0f' }; op.look = op.look || lookById('satin'); return true; }
            return true;
        });
        if (!ops.length && ghostAsk) return { kind: 'ask', text: 'A ghost graphic is the SAME colour as the body with a different sheen, and this paint has no single body colour (the biggest is ' + (main ? main.name + ' at ' + Math.round(main.share) + '%' : 'unclear') + '). Which colour should the stripes match?', chips: topNames(pal, 3).map(function (e) { return 'Make the stripes ' + e.name + ' matte'; }) };
        if (!ops.length) return null;
        // not ours: nothing here is about what is already on the car (a plain "make the roof matte black" is the older, simpler handler's job)
        var ours = ops.some(function (op) {
            var tg = op.target; if (!tg) return false;
            if (op.recipe) return true;
            if (tg.kind === 'layerword') return true;
            if (tg.kind === 'allpop' || tg.kind === 'colour' || tg.kind === 'accents' || tg.kind === 'numbers' || tg.kind === 'sponsors' || tg.kind === 'main') return true;
            if (tg.kind === 'body') return !!(op.keep || (op.look && !LEGACY_LOOKS[op.look.id]));          // whole-car matte / gloss / glossier / pop: the older handlers
            if (op.rel || op.shade || op.pop || op.keep) return true;
            if (op.look && !LEGACY_LOOKS[op.look.id]) return true;
            if (op.look && op.colour && tg.kind === 'body') return false;
            return false;
        });
        if (usedLast || usedSame || assignedExcept || (env._layerScope && env._layerScope.length) || clauses.some(function (c) { return c.sourceColour; })) ours = true; // explicit source-to-destination corrections stay in this scoped compiler
        // A single imperative with one exact named-part target is complete enough for E to own.
        // Never use this marker for body requests, multi-job text, unknown extras, or layered recipes.
        var exactPart = false;
        if (ops.length === 1 && clauses.length === 1 && !assignedExcept && !exclude.length && !usedLast && !usedSame && !WHOLE_RE.test(t) && (POLITE_RE.test(nQ) || clauses[0].sourceColour)) {
            var onlyOp = ops[0], onlyTarget = onlyOp && onlyOp.target;
            var oneKnownPart = onlyTarget && onlyTarget.kind === 'part' && PART_WORDS.some(function (pw) { return pw[0] === onlyTarget.part; });
            var completeAction = !!(onlyOp && (onlyOp.colour || onlyOp.look || onlyOp.rel || onlyOp.shade || onlyOp.pop)) && !onlyOp.ext && !onlyOp.recipe && !onlyOp.sub;
            var cleanClause = clauses[0].targets.length === 1 && clauses[0].targets[0].kind === 'part' && !clauses[0].leftover.length && !clauses[0].ext && !clauses[0].recipe;
            if (oneKnownPart && completeAction && cleanClause) { exactPart = true; ours = true; }
        }
        if (exclude.length) {                                           // "...but leave the numbers alone": only this helper can express it
            ops.forEach(function (op) { if (op.target && ['colour', 'main', 'body', 'part', 'accents', 'allpop', 'layerword'].indexOf(op.target.kind) !== -1) { var ex2 = exclude.filter(function (k) { return !(op.target.kind === 'numbers' && k === 'numbers') && !(op.target.kind === 'sponsors' && k === 'sponsors'); }); if (ex2.length) { op.exclude = ex2; ours = true; } } });
        }
        var targetless = ops.filter(function (op) { return !op.target; });
        if (targetless.length && !ours) return null;
        if (!ours) return null;
        // unknown words: an unknown look ("carbon fiber", "camo", "galaxy") is the catalogue's job (the caller resolves it), nothing else is guessed
        var unknown = [];
        ops.forEach(function (op) { if (op.ext && !op.look && HOLO_RE.test(op.ext) && (op.colour || op.texture)) { op.look = HOLO_LOOK; op.ext = null; } });          // FIRSTTEST2: "...to pink and make it holographic": the pink stays
        ops.forEach(function (op) { if (op.ext && !op.look) unknown.push(op.ext); });
        var planned = { kind: 'ops', ops: ops, alt: alt, unknown: unknown.slice(0, 2), text: t, usedLast: usedLast, usedSame: usedSame, exclude: exclude, atomicScope: assignedExcept };
        if (exactPart) planned.exactPart = true;
        return planned;
    }
    function variantLooks(tg, pal) {
        var key = tg.kind;
        if (tg.kind === 'colour') { var r = resolveColour(wantFor(tg.word, tg.hex, tg.qual), pal); key = r.entries.length ? r.entries[0].fam : familyOf(tg.hex); }
        if (tg.kind === 'main') { var top = topNames(pal, 1)[0]; key = top ? top.fam : 'main'; }
        return (VARIANT_SETS[key] || VARIANT_SETS.part).slice(0, 4);
    }
    // the context the NEXT sentence can lean on ("make it glossier", "a bit more", "do the same for the roof", "put it back")
    function ctxOf(planned) {
        if (!planned || planned.kind !== 'ops' || !planned.ops || !planned.ops.length) return null;
        var op = planned.ops[0], seen = {}, tgs = [];
        planned.ops.forEach(function (o) { if (!o.target) return; var k = JSON.stringify([o.target.kind, o.target.word || o.target.part || '', o.target.hex || '']); if (!seen[k]) { seen[k] = 1; tgs.push(o.target); } });
        var lid = op.look && op.look.id !== 'ext' ? op.look.id : null, dir = null;
        if (!lid && op.rel) { lid = op.rel === 'up' ? (op.strong ? 'wet look' : 'gloss') : (op.soft ? 'satin' : 'matte'); dir = op.rel === 'up' ? 1 : -1; }         // "glossier" produced the gloss look: "a bit more" climbs from there
        return { targets: tgs, act: { look: lid, dir: dir, colour: op.colour || null, soft: !!op.soft, strong: !!op.strong, shade: op.shade || null, keep: !!op.keep, pop: !!op.pop, lookObj: op.look ? JSON.parse(JSON.stringify(op.look)) : null, strength: op.strengthMul || null, texture: op.texture ? JSON.parse(JSON.stringify(op.texture)) : null, scale: op.scaleMul || null, shadeDir: op.shadeDir || 0 }, label: tgs.length ? targetChipName(tgs[0], []) : '' };          // HELPER_V2 fix pass 4: "on the roof too" / "smaller" need the exact look, texture and size
    }
    function targetChipName(tg, pal) {
        if (tg.kind === 'colour') { var w = wantFor(tg.word, tg.hex, tg.qual), r = resolveColour(w, pal); return r.entries.length ? r.label : tg.word; }
        if (tg.kind === 'numbers') return 'numbers'; if (tg.kind === 'sponsors') return 'sponsors'; if (tg.kind === 'part') return tg.part; if (tg.kind === 'accents' || tg.kind === 'layerword') return tg.word;
        if (tg.kind === 'main') return topNames(pal, 1).length ? topNames(pal, 1)[0].name : 'main colour';
        return 'car';
    }
    function targetPhrase(tg, pal) {
        if (tg.kind === 'colour') { var w = wantFor(tg.word, tg.hex, tg.qual), r = resolveColour(w, pal); return 'the ' + (r.entries.length ? r.label + ' (' + Math.round(r.share) + '% of the car)' : tg.word); }
        if (tg.kind === 'numbers') return 'the numbers'; if (tg.kind === 'sponsors') return 'the sponsors'; if (tg.kind === 'part') return 'the ' + tg.part; if (tg.kind === 'accents' || tg.kind === 'layerword') return 'the ' + tg.word; if (tg.kind === 'main') return 'the main colour';
        return 'the whole car';
    }

    // ------------------------------------------------------------------ COMPILE: ops + the car's real colours / layers -> zone specs (add_zone arguments) and an honest list of what each one does
    var TOL_SPEC = 30, TOL_PAINT = 38;          // the FLOORS (and the fallback when the paint cannot be measured, e.g. node tests)
    // WP6 2026-10-03 edge quality: measure the paint instead of a fixed tolerance (SpbProZone.edgeFit): per-colour tolerance up to half the distance to the nearest
    // other colour, same-hue shades of a shaded fill, and safe extra spheres over the anti-alias ramp (no halo of the old colour on thin glyphs / stripes).
    function edgeFitFor(colors, paint, family, siblings) {          // MCPSCEN 2026-10-05: siblings = a named colour / main colour target (RAM2 flat lighter-pink hood)
        var Zk = (typeof window !== 'undefined' && window.SpbProZone) || null; if (!Zk || typeof Zk.edgeFit !== 'function') return null;
        try { var opts = { floor: paint ? TOL_PAINT : TOL_SPEC }; if (family) opts.family = family; if (siblings) opts.siblings = true; var f = Zk.edgeFit(colors, opts); return (f && f.colors && f.colors.length) ? f : null; } catch (e) { return null; }
    }
    function relFinish(op) { if (op.rel === 'up') return op.strong ? { found: 'base::f_gel_coat', label: 'much glossier' } : { found: 'base::f_soft_gloss', label: 'glossier' }; return op.soft ? { found: 'base::f_clear_satin', label: 'a little duller' } : { found: 'base::f_soft_matte', label: 'duller (matte)' }; }
    function accentsOf(pal) { var real = pal.filter(function (e) { return e.share >= 1.5; }); return real.slice(1); }          // colours that are not the body: everything after the biggest real colour
    function actionText(op) { if (op.look) return op.look.label; if (op.colour) return op.colour.name; if (op.rel) return op.rel === 'up' ? 'glossier' : 'duller'; if (op.pop) return 'pop'; if (op.shade) return op.shade; return 'satin'; }
    function chipsLike(op, pal, n) { var al = actionText(op); return topNames(pal, n || 3).map(function (e) { return 'Make the ' + e.name + ' ' + al; }); }
    function extend(a, b) { for (var k in b) if (Object.prototype.hasOwnProperty.call(b, k)) a[k] = b[k]; return a; }
    function chDelta(h1, h2) { var a = hexRgb(h1), b = hexRgb(h2); return Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]), Math.abs(a[2] - b[2])); }
    function popAll(pal, zones, notes) {
        var real = pal.filter(function (e) { return e.share >= 1.5; });
        if (real.length < 2) { notes.push('This paint has one main colour, so there is nothing to contrast: say what you want it to look like instead.'); return; }
        function hexesOf(e) { var r = resolveColour(wantFor(e.name, e.hex, null), pal); return (r.entries.length ? r.entries : [e]).map(function (x) { return x.hex; }); }
        var used = {};
        real.slice(0, 4).forEach(function (e, i) {
            if (used[e.fam]) return; used[e.fam] = 1;
            zones.push({ name: i === 0 ? cap(e.name) + ' flat (so the other colours pop)' : cap(e.name) + ' metallic (pops against the flat body)', finish: i === 0 ? 'base::f_soft_matte' : 'base::f_metallic', color: 'source', region: { colors: hexesOf(e), tolerance: TOL_SPEC }, _meta: { label: e.name, what: [i === 0 ? 'flat matte' : 'metallic'], share: e.share, specOnly: true, kind: 'colour', about: '' } });
        });
    }
    // COPILOT-FIX 2026-10-04: the colours the ZONES paint (from the app: zone base colours with what they cover) -> family-tagged entries like prepPalette's
    function prepZoneColours(zc) {
        return (zc || []).filter(function (z) { return z && /^#[0-9a-f]{6}$/i.test(String(z.hex || '')); }).map(function (z) { var q = hsl(z.hex); return { hex: String(z.hex).toLowerCase(), zone: z.zone, zone_id: z.zone_id, index: z.index, share: z.share_pct != null ? Number(z.share_pct) : null, layers: z.layers || [], fam: familyOf(z.hex), l: q.l, s: q.s, h: q.h, name: (Dz().nameColour ? Dz().nameColour(z.hex) : familyOf(z.hex)) }; });
    }
    function zoneHits(want, zcols, scope) {
        if (!zcols || !zcols.length) return [];
        var sc = (scope || []).map(norm), inScope = function (z) { return !sc.length || z.layers.some(function (l) { return sc.indexOf(norm(l)) !== -1; }); };
        var hit = zcols.filter(function (e) { return inScope(e) && (e.name === want.word || (e.fam === want.fam && bandOk(e, want.band))); });
        if (!hit.length && want.band) hit = zcols.filter(function (e) { return inScope(e) && e.fam === want.fam; });
        if (!hit.length) { var nb = NEAR[want.fam] || []; nb.forEach(function (f) { if (!hit.length) hit = zcols.filter(function (e) { return inScope(e) && e.fam === f; }); }); }
        return hit;
    }
    function shadeHex(hex, word) { var q = hsl(hex); if (/darker|deeper|richer/.test(word)) return fromHsl(q.h, q.s, q.l * 0.65); if (/lighter|paler/.test(word)) return fromHsl(q.h, q.s * 0.9, q.l + (1 - q.l) * 0.4); if (/faded|washed|subdued|muted|less saturated/.test(word)) return fromHsl(q.h, q.s * 0.55, q.l); return fromHsl(q.h, Math.min(1, q.s * 1.25 + 0.05), Math.min(0.62, Math.max(0.42, q.l))); }
    // ENC_READER_FIX 2026-10-05: 'is now Flat Black, in black' -> 'is now Flat Black' (the look's name already says the colour)
    function saysColour(label, name) { var l = ' ' + String(label || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ') + ' ', n = String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); return !!n && l.indexOf(' ' + n + ' ') >= 0; }
    // one edit per zone that paints the colour: its colour (new / shaded) and / or its finish (a look). The zones keep their own selection: nothing new covers the car.
    function zoneColourOps(op, tg, zh, zones, notes, pal, semanticLabels) {
        var c = op.look, finish = null, shift = null, what = [], newHex = op.colour && !op.keep ? applyQual(op.colour.hex, op.colour.qual) : null;
        if (op.ext && !c) return { ask: { text: 'I do not know a look called “' + op.ext + '”. Here is what I can do to the ' + tg.word + ':', chips: askWhat('the ' + tg.word, pal) }, why: 'look' };
        if (c) { what.push(c.label); finish = c.found || (c.zone && c.zone.finish) || null; if (c.shift) shift = JSON.parse(JSON.stringify(c.shift)); if (!newHex && c.zone && c.zoneColor && /^#/.test(c.zoneColor)) newHex = c.zoneColor; }
        else if (op.rel) { var rf = relFinish(op); finish = rf.found; what.push(rf.label); }
        else if (op.pop) { finish = 'base::f_metallic'; what.push('metallic, so it stands out'); }
        if (!finish && !newHex && !op.shade && !op.texture) return { ask: { text: 'What should I do with the ' + tg.word + ' (painted by ' + zh.map(function (z) { return '“' + z.zone + '”'; }).join(', ') + ')? Pick a look, or tell me a colour.', chips: askWhat('the ' + tg.word, pal) }, why: 'action' };
        if (newHex) { var cn0 = (op.colour && op.colour.name && !/^#/.test(op.colour.name) ? op.colour.name : tintName(newHex, semanticLabels)); if (!(c && saysColour(c.label, cn0))) what.push((c ? 'in ' : 'recoloured ') + cn0); }
        else if (op.shade) what.push(op.shade);
        zh.forEach(function (z) {
            var hx = newHex || (op.shade ? shadeHex(z.hex, op.shade) : null), e = { name: z.zone, finish: finish || undefined, color: hx || 'source' };
            if (shift) e.spec_shift = shift;
            if (op.texture) { if (op.texture.mode === 'pattern') e.pattern = { id: op.texture.pattern, opacity: 60, scale: 1 }; else e.spec_patterns_add = [{ id: op.texture.spec, opacity: 85, scale: 1 }]; }          // FIRSTTEST: added ON TOP of the zone's own spec layers (ai.js merges)
            e._meta = { label: tg.word + (tg.layers ? ' in the ' + tg.layers[0] + ' layer' : ''), what: what.slice(), share: z.share, element: false, specOnly: !hx, finishExplicit: !!finish, look: c ? c.id : null, parts: [], kind: 'zonecolour', about: c ? c.about : '', zoneEdit: { zone_id: z.zone_id, zone: z.zone, hex: z.hex } };
            zones.push(e);
        });
        return { ok: true };
    }
    // VISIBLE_COLOUR 2026-10-04 (owner: on the 8-zone seafoam design "make the yellow purple" found the SOURCE yellow under the Seafoam zone and turned the body purple):
    // how much of a resolved paint colour the buyer still SEES. editEnv measures it per colour: shown_pct (whole car), hidden_by (the zones that repaint it: top zone wins, lower
    // index = higher priority), body_shown_pct (on the body-paint layers, which is what "the yellow" means on a layered file unless numbers / logos are named).
    function visibleOf(entries, env, tg) {
        var body = !!(env && env.bodyLayers && env.bodyLayers.length && !env.decalsNamed && !(tg && tg.layers && tg.layers.length));
        var q = { hidden: 0, shown: 0, inScope: 0, outside: 0, zones: [], body: body }, byId = {};
        entries.forEach(function (e) {
            var sh = visOf(e); q.shown += sh; q.inScope += (body && e.bshown != null) ? e.bshown : sh;
            if (!e.hidden || !e.hidden.length) return;
            q.hidden += Math.max(0, e.share - sh);
            e.hidden.forEach(function (h) { var k = String(h.zone_id || h.zone); if (!byId[k]) { byId[k] = { id: String(h.zone_id || ''), zone: String(h.zone || ''), shows: h.shows || null, index: h.index, pct: 0 }; q.zones.push(byId[k]); } byId[k].pct += (Number(h.pct) || 0) * e.share / 100; });
        });
        q.zones.sort(function (a, b) { return b.pct - a.pct; });
        q.outside = body ? Math.max(0, q.shown - q.inScope) : 0;
        return q;
    }
    // the colour shows nowhere (in scope): nothing changes; say so, say what covers it, offer the hidden one (chip, re-run by the app) + the colour the buyer sees there instead
    function hiddenAsk(op, tg, q) {
        var w = tg.word, act = [op.colour && !op.keep ? op.colour.name : null, op.look ? op.look.label : null].filter(Boolean).join(' ') || actionText(op), z0 = q.zones[0] || { zone: 'one of your zones' }, many = q.zones.length > 1, shows = z0.shows ? (Dz().nameColour ? Dz().nameColour(z0.shows) : familyOf(z0.shows)) : null;
        var zn = q.zones.slice(0, 2).map(function (z) { return '“' + z.zone + '”'; }).join(' and ');
        var t = 'I do not see any ' + w + ' on ' + (q.body && q.outside >= 0.5 ? 'the body of the car' : 'the car') + ' now: your zone' + (many ? 's ' : ' ') + zn + ' paint' + (many ? '' : 's') + ' over it' + (shows ? ', so that part of the car shows ' + shows : '') + '.';
        if (q.outside >= 0.5) t += ' The only ' + w + ' you can still see is in the logos / decals (about ' + (q.outside < 1 ? 'under 1' : Math.round(q.outside)) + '% of the car), and I leave those alone unless you name them.';
        t += ' There is ' + w + ' in the original paint under ' + (many ? 'those zones' : 'your ' + z0.zone + ' zone') + ' (about ' + (q.hidden < 1 ? 'under 1' : Math.round(q.hidden)) + '% of the car): change that?';
        var chip = 'Change the hidden ' + w + ' under “' + z0.zone + '”'; if (chip.length > 58) chip = 'Change the hidden ' + w + ' under that zone';
        var chips = [chip];
        var texT = op.texture ? ' with a ' + op.texture.label + (op.texture.mode === 'pattern' ? ' print' : ' shine') : '';
        if (shows && (op.colour || op.look || op.shade || op.rel || op.pop)) { var c2 = 'Make the ' + shows + ' ' + act; if ((c2 + texT).length < 60) c2 += texT; if (c2.length < 60) chips.push(c2); }
        if (q.outside >= 0.5) { var c3 = 'Make all the ' + w + ' ' + act + ', including the logos'; if (c3.length < 60) chips.push(c3); }
        var ask = { text: t, chips: chips };
        return { ask: ask, info: { word: w, chip: chip, ask: ask, zones: q.zones.map(function (z) { return z.zone; }), hidden: Math.round(q.hidden * 10) / 10, outside: Math.round(q.outside * 10) / 10, shows: shows } };
    }
    // HELPER FIX PASS 7 2026-10-05: the gradient for a fade on ONE part. axis 'length' runs front->rear, 'height' runs roof-line->rocker; start = the end the FIRST colour sits at
    // (front | rear | top | bottom). The car map gives each part's front and roof-line side on the sheet (js/spb-pro-carmap.js island.front / island.up); zone-kit fits the stops to the zone box.
    function partGradient(part, g) {
        var Wn = typeof window !== 'undefined' ? window : null, isl = null; try { isl = Wn && Wn.SpbProCar && Wn.SpbProCar.findIsland ? Wn.SpbProCar.findIsland(part) : null; } catch (e) { isl = null; }
        var side = g.axis === 'height' ? ((isl && isl.up) || 'top') : ((isl && isl.front) || 'left'), dir = (side === 'left' || side === 'right') ? 'horizontal' : 'vertical', lowFirst = (side === 'left' || side === 'top');
        var firstAtSide = g.axis === 'height' ? g.start !== 'bottom' : g.start !== 'rear', a = String(g.from).toLowerCase(), b = String(g.to).toLowerCase(), aLow = firstAtSide === lowFirst;
        return { stops: [{ pos: 0, color: aLow ? a : b }, { pos: 100, color: aLow ? b : a }], direction: dir, fit: true };
    }
    function compile(planned, env) {
        var pal = prepPalette(env.palette), layers = env.layers || [], zones = [], notes = [], missing = [], ask = null, zcols = prepZoneColours(env.zoneColours), objects = [], noops = [], lastCol = null;
        function layerNames(role) {         // the app's layer roles: 'numbers', 'decals / logos', 'tape / stripes', 'body paint', 'other art'
            var want = role === 'sponsors' ? { sponsors: 1, 'decals / logos': 1, 'decals/logos': 1, logos: 1 } : (role === 'stripes' ? { 'tape / stripes': 1, 'tape/stripes': 1, stripes: 1, tape: 1 } : { numbers: 1 });
            return layers.filter(function (l) { return want[String(l.role || '').toLowerCase()] && !l.hidden && !(role === 'numbers' && /sponsor|logo|decal|contingenc/i.test(String(l.name || ''))); }).map(function (l) { return l.name; });          // MCPSCEN 2026-10-05: a numbers layer that also holds the sponsors (DLM "SPONSORS NUMBERS") is shared: numbers are boxed instead
        }
        // FIRSTTEST2 2026-10-04 owner: 'I told it to change the yellow TO pink': one unresolvable job never wipes the jobs that resolved. Every op is compiled; the FIRST question is
        // kept in `ask` (+ all of them in `asks`); the caller does what resolved and asks about only the rest (atomicScope still wipes everything below).
        var asks = [], hiddenOut = null;          // VISIBLE_COLOUR: the "that colour shows nowhere" answer (chip + the zones covering it)
        planned.ops.forEach(function (op0) { var keepAsk = ask; ask = null; if (keepAsk && planned.atomicScope) { ask = keepAsk; return; } compileOp(op0); if (ask) asks.push({ ask: ask, op: op0 }); ask = keepAsk || ask; });
        function compileOp(op) {
            var tg = op.target, c = op.look, region = null, label = '', share = null, parts = null, below = null;
            // ROUTER2 2026-10-04 (owner T1 "make the numbers pink as well as where the black base hexagon is"): a named thing with no colour / look of its own takes the one said before it
            if (tg && tg.object && !op.colour && !op.look && !op.rel && !op.pop && !op.shade && lastCol) op = extend(extend({}, op), { colour: lastCol.colour, look: lastCol.look });
            if (op.colour || op.look) lastCol = op;
            if (!tg) return;
            if (tg.kind === 'allpop') { popAll(pal, zones, notes); return; }
            if (tg.kind === 'colour') {
                var w = wantFor(tg.word, tg.hex, tg.qual), r = resolveColour(w, pal), zh = zoneHits(w, zcols, tg.layers), shownPix = r.entries.reduce(function (a, e) { return a + (e.shown != null ? e.shown : e.share); }, 0);
                // ROUTER-FIX 2026-10-04 (owner: "the yellow on the spray can" -> "that yellow is a logo ... Show me the can"): the buyer NAMED a thing; the app offers the layers that hold
                // that colour (+ a box to draw) and the other jobs in the sentence still run. Nothing is guessed here.
                if (tg.object && op.colour && !op.colour.exact && /\bsame\b/.test(String(planned.raw || planned.text || '')) && zcols.length) { var sameO = zcols.filter(function (zc) { return zc.fam === familyOf(op.colour.hex); })[0]; if (sameO) op = extend(extend({}, op), { colour: { name: op.colour.name, hex: sameO.hex, exact: true } }); }          // ROUTER2: "the same color pink you use on the numbers" = that zone's exact hex for a named thing too
                if (tg.object) { objects.push({ object: tg.object, word: tg.word, hexes: r.entries.map(function (e) { return e.hex; }).concat(zh.map(function (z) { return z.hex; })), layers: tg.layers || null, action: actionText(op), colour: op.colour ? { name: op.colour.name, hex: applyQual(op.colour.hex, op.colour.qual) } : null, look: op.look ? op.look.id : null }); return; }
                // a colour IN A PLACE that only a zone paints: that zone covers more than the place, so editing it would change the colour everywhere
                if (zh.length && tg.parts && tg.parts.length && !r.entries.length) { missing.push({ why: 'zonescope', word: tg.word }); ask = { text: 'The ' + tg.word + ' there is painted by your zone' + (zh.length > 1 ? 's ' : ' ') + zh.slice(0, 3).map(function (z) { return '“' + z.zone + '”'; }).join(', ') + ', which also covers other places, so I did not change it. Say “make all the ' + tg.word + ' ' + actionText(op) + '” to change it everywhere.', chips: ['Make all the ' + tg.word + ' ' + actionText(op)] }; return; }
                // COPILOT-FIX 2026-10-04: the colour is painted by ZONES -> edit those zones (plus the paint's own pixels of that colour only when they clearly show: >= 2%)
                if (zh.length && !(tg.parts && tg.parts.length)) {
                    var zdone = zoneColourOps(op, tg, zh, zones, notes, pal, !!(env && env.mcpSemanticHexLabels));
                    if (zdone && zdone.ask) { ask = zdone.ask; missing.push({ why: zdone.why || 'action', label: tg.word }); return; }
                    if (!(r.entries.length && shownPix >= 2 && !tg.layers)) return;
                    notes.push('(The paint itself also has ' + r.label + ' (' + Math.round(shownPix) + '% of the car): I changed that too.)');
                }
                // VISIBLE_COLOUR 2026-10-04 (owner law: a colour on the car = the colour the buyer SEES): paint pixels that a zone above repaints are not that colour any more (the
                // yellow under a seafoam zone shows seafoam). Visible nowhere (on the body paint when the request keeps to it) -> nothing changes, the reply says so + offers the hidden
                // one; partly hidden -> the new zone goes BELOW the zones that hide it, so only the colour the buyer can see changes. "anyway" / the chip (env.hiddenOk) lift both.
                var visQ = (r.entries.length && !zh.length) ? visibleOf(r.entries, env, tg) : null;
                if (visQ && visQ.hidden >= 1 && visQ.inScope < ((tg.parts && tg.parts.length) ? 0.05 : 0.3) && !planned.force && !env.hiddenOk) { var hq = hiddenAsk(op, tg, visQ); missing.push({ why: 'hidden', word: tg.word }); ask = hq.ask; hiddenOut = hq.info; return; }
                if (visQ && visQ.hidden >= 0.3 && visQ.zones.length && !planned.force && !env.hiddenOk) { below = { ids: visQ.zones.map(function (z) { return z.id; }).filter(Boolean), names: visQ.zones.map(function (z) { return z.zone; }) }; below.note = '(Only the ' + tg.word + ' you can see changed: the ' + tg.word + ' under ' + below.names.slice(0, 2).map(function (nm) { return '“' + nm + '”'; }).join(' and ') + ' stays covered by ' + (below.names.length > 1 ? 'those zones' : 'that zone') + '.)'; }
                if (!r.entries.length && zcols.length && !zh.length) {
                    missing.push({ why: 'colour', word: tg.word });
                    ask = { text: 'I do not see any ' + tg.word + (tg.layers ? ' in the ' + tg.layers[0] + ' layer' : '') + ' on this car. Colours on it: ' + paletteLine(pal) + (zcols.length ? '; painted by your zones: ' + zcols.slice(0, 5).map(function (z) { return z.name + ' (' + z.zone + ')'; }).join(', ') : '') + '. Which one do you mean?', chips: chipsLike(op, pal, 2).concat(zcols.slice(0, 2).map(function (z) { return 'Make the ' + z.name + ' ' + actionText(op); })) };
                    return;
                }
                // HELPER FIX PASS 7 2026-10-05 (blind5 b5-042/044: 2% red was reported as a car-wide change): under 2% shown -> nothing changes, ask (as before); 2-3% shown -> the change is made but the reply SAYS it is small and names the main colour (edit_corpus keeps its 2% synthetic accents as real edits)
                if (r.entries.length && !zh.length && !tg.layers && shownPix >= 2 && shownPix < 3 && !planned.force) { var mainC = topNames(pal, 1)[0]; notes.push('(Only about ' + Math.round(shownPix) + '% of the paint is ' + r.label + ', so this is a small change' + (mainC && mainC.name && mainC.name !== r.label ? '. If you meant the main colour, say “' + actionText(op).replace(/^/, 'make the ' + mainC.name + ' ') + '”' : '') + '.)'); }
                if (r.entries.length && !zh.length && !tg.layers && shownPix < 2 && !planned.force) {
                    missing.push({ why: 'small', word: tg.word });
                    ask = { text: 'Nothing was changed: I only see a little ' + r.label + ' on this car (about ' + (shownPix < 1 ? 'under 1' : Math.round(shownPix)) + '% of the paint)' + (zcols.length ? ' and none of your zones paints ' + tg.word : '') + '. Should I change just those few spots? Otherwise tell me which colour you mean: ' + paletteLine(pal) + '.', chips: [String(planned.raw || planned.text || ('make the ' + tg.word + ' ' + actionText(op))).replace(/[.!?]+$/, '') + ' anyway'].concat(chipsLike(op, pal, 2)) };
                    return;
                }
                if (!r.entries.length) {
                    missing.push({ why: 'colour', word: tg.word });
                    if (r.near) ask = { text: 'I do not see any ' + tg.word + ' on this car, but I do see ' + r.near[0].name + ' (' + Math.round(r.near[0].share) + '% of the car). Is that the one? Otherwise tell me which: ' + paletteLine(pal) + '.', chips: ['Make the ' + r.near[0].name + ' ' + actionText(op)].concat(chipsLike(op, pal, 3).filter(function (x) { return x !== 'Make the ' + r.near[0].name + ' ' + actionText(op); })).slice(0, 4) };
                    else ask = { text: 'I do not see any ' + tg.word + ' on this car. What I can see: ' + paletteLine(pal) + '. Which one do you mean?', chips: chipsLike(op, pal, 4) };
                    return;
                }
                region = { colors: r.entries.map(function (e) { return e.hex; }) }; if (tg.layers) region.layers = tg.layers.slice(); if (!tg.layers && !(tg.parts && tg.parts.length) && env && env.paintableFlat) region.paintable = true; try { var bigC = (w && w.fam === 'black' && !tg.layers) ? pal.filter(function (e) { return e.fam === 'charcoal' && visOf(e) >= 10 && visOf(e) > (r.share || 0) && r.entries.every(function (x) { return x.hex !== e.hex; }); })[0] : null; if (bigC) notes.push('The car\'s biggest dark colour is charcoal (' + bigC.hex + ', ' + Math.round(visOf(bigC)) + '% of the car), not black: it was NOT changed. If the buyer means that dark body too, call again with target "charcoal".'); } catch (eC) {}          /* MCPSCEN 2026-10-05 (F150: "black matte" mattes the black logo art, the #252525 body stays glossy and nothing said so) */          /* MCPSCEN 2026-10-05 (SS: the template backdrop brown matched the dark-olive shade of the yellow, so "main colour matte" also took the dead space): on a flat paint a colour target stays inside the car's paintable area */ label = r.label + (tg.layers ? ' in the ' + tg.layers[0] + ' layer' : ''); share = (tg.layers || (tg.parts && tg.parts.length)) ? null : ((visQ && visQ.hidden > 0) ? Math.round((visQ.body ? visQ.inScope : visQ.shown) * 10) / 10 : r.share);          /* VISIBLE_COLOUR: "the yellow (38% of the car)" = what shows */ /* ROUTER-FIX: a scoped colour is not "x% of the car"; neutral neighbours (black / charcoal / grey / silver) are used without a fuss: the reply names the colour it really found */
                if (tg.parts && tg.parts.length) parts = tg.parts.slice();
            } else if (tg.kind === 'main') {
                var top = topNames(pal, 1)[0]; if (!top) { missing.push({ why: 'colour', word: 'main colour' }); ask = { text: 'I cannot read the paint yet: wait for the car to show in the preview and ask again.', chips: [] }; return; }
                var rm = resolveColour(wantFor(top.name, top.hex, null), pal); region = { colors: (rm.entries.length ? rm.entries : [top]).map(function (e) { return e.hex; }) }; if (env && env.paintableFlat) region.paintable = true; label = 'main colour (' + top.name + ')'; share = top.share; if (top.share < 25 && op.colour && env && env.mcpSemanticHexLabels != null) notes.push('The body is many colours (the biggest, ' + top.name + ', is only ' + Math.round(top.share) + '% of the car): this changes the ' + top.name + ' family only, so the other body colours stay as shapes around it. ' + 'For ONE colour over the whole body use spb_apply_scheme preset "solid" (numbers / sponsors stay).');          /* MCPSCEN 2026-10-05 (RAM2 Monster High camo: main colour (pink 16%) matte black left blue / teal / purple shards on the sides, and nothing said why) */
            } else if (tg.kind === 'numbers' || tg.kind === 'sponsors') {
                var names = layerNames(tg.kind);
                if (!names.length && env.elements && env.elements[tg.kind] && env.elements[tg.kind].found) { var esub = tg.sub || ((tg.kind === 'numbers' && op.colour && !op.keep) ? 'fill' : ''); region = { element: tg.kind + (esub ? ':' + esub : '') }; label = tg.kind + (esub ? ' ' + esub : ''); share = env.elements[tg.kind].share || null; if (esub === 'fill' && !tg.sub && otherFamilies(env.elements.numbers.colours) > 0) notes.push('(I changed the number fill and kept its outline: say “the number outline too” for that.)'); }
                else if (!names.length) { missing.push({ why: 'layer', kind: tg.kind }); ask = { text: 'I cannot find a ' + tg.kind + ' layer in this file (it is a flat picture, not a layered template). Which colour are the ' + tg.kind + '? I can see ' + paletteLine(pal) + '.', chips: chipsLike(op, pal, 4) }; return; }
                else {
                    // ROUTER2 2026-10-04 (owner T1, replay: "Numbers recoloured hot pink" flattened the numbers, black drop shadow gone): a numbers RECOLOUR changes the FILL colour only;
                    // the shadow / outline keep their colours. And numbers a zone ALREADY paints that colour = no change (said, not done twice).
                    var nfam = (tg.kind === 'numbers' && op.colour && !op.keep && !op.look && !tg.sub) ? familyOf(applyQual(op.colour.hex, op.colour.qual)) : null;
                    var nAlready = nfam ? zcols.filter(function (zc) { return zc.fam === nfam && zc.layers.some(function (ln) { return names.indexOf(ln) !== -1; }); })[0] : null;
                    if (nAlready) { var nmsg = 'The numbers are already ' + (op.colour.name || nfam) + ' (“' + nAlready.zone + '”), so I left them as they are.'; noops.push(nmsg); notes.push(nmsg); return; }
                    region = { layers: names }; label = tg.kind;
                    var nf = env.numbers || null;
                    // MCPSCEN 2026-10-05 (ARCA layered numbers: "number outline white" flattened the whole Numbers layer white, the new blue fill gone): outline / shadow / fill named = that colour of the layer only
                    if (tg.kind === 'numbers' && tg.sub && nf && nf.fill) { var sc = tg.sub === 'fill' ? nf.fill : (tg.sub === 'outline' ? (nf.outline || (nf.others || [])[0]) : (nf.shadow || (nf.others || [])[1] || (nf.others || [])[0])); if (sc) { region.colors = [sc]; region.tolerance = nf.tol || 16; region._fixTol = 1; label = 'number ' + tg.sub; } }
                    else if (tg.kind === 'numbers' && op.colour && !op.keep && !tg.sub && nf && nf.fill && (nf.others || []).length) { region.colors = [nf.fill]; region.tolerance = nf.tol || 16; region._fixTol = 1; label = 'number fill'; notes.push('(I changed the number fill and kept the shadow and outline: say “the number outline too” for those.)'); }
                }
            } else if (tg.kind === 'part') { region = { part: tg.part }; label = tg.part; }
            else if (tg.kind === 'layer') { region = { layers: tg.layers.slice() }; label = tg.word + ' layer'; }          // COPILOT-FIX: "make the Numbers layer gold"
            else if (tg.kind === 'layerword') {
                var lwr = LAYERWORDS.filter(function (x) { return x[0] === tg.word; })[0], lns = lwr ? layerNamesFor(layers, lwr[1]) : [];
                if (!lns.length) { missing.push({ why: 'layerword', word: tg.word }); ask = { text: (UNSUPPORTED_TEXT[tg.word] || ('I cannot find a ' + tg.word + ' layer in this file.')) + ' I can change the body colours, the numbers, the sponsors, the stripes and the named panels.', chips: chipsLike(op, pal, 3) }; return; }
                region = { layers: lns }; label = tg.word;
            }
            else if (tg.kind === 'accents' && layerNames('stripes').length) { region = { layers: layerNames('stripes') }; label = tg.word; }
            else if (tg.kind === 'accents' && env.elements && env.elements.stripes && env.elements.stripes.found && /^(stripes?|pinstripes?|tape)$/.test(String(tg.word))) { region = { element: 'stripes' }; label = tg.word; share = env.elements.stripes.share || null; }       // a tape / stripes layer is exactly "the stripes"
            else if (tg.kind === 'accents') {
                var acc = accentsOf(pal);
                if (acc.length === 1) { var ra = resolveColour(wantFor(acc[0].name, acc[0].hex, null), pal); region = { colors: (ra.entries.length ? ra.entries : acc).map(function (e) { return e.hex; }) }; label = acc[0].name + ' ' + tg.word; share = acc[0].share; }
                else { missing.push({ why: 'accents' }); ask = { text: 'Which colour are the ' + tg.word + '? I can see ' + paletteLine(pal) + '.', chips: topNames(pal, 4).map(function (e) { return 'Make the ' + e.name + ' ' + tg.word + ' ' + actionText(op); }) }; return; }
            } else { region = (env && env.bodyLayers && env.bodyLayers.length) ? { everything: true } : { everything: true, paintable: true }; label = 'whole car'; }          // HELPER_V2 fix pass 4b 2026-10-04 owner: keep improving the Offline Helper -- body layers already keep decals out; the template-Mask 'paintable' grid left holes in the body
            // what does the buyer want it to BECOME
            if (op.ext && !c) { missing.push({ why: 'look', query: op.ext }); ask = { text: 'I do not know a look called “' + op.ext + '”. Here is what I can do to ' + targetPhrase(tg, pal) + ':', chips: askWhat(targetChipName(tg, pal), pal) }; return; }
            var newHex = op.colour ? applyQual(op.colour.hex, op.colour.qual) : null, finish = null, color = 'source', what = [], zoneExtra = null, adj = null;
            // ROUTER-FIX 2026-10-04 (owner: "the same color pink you use on the numbers"): "the same <colour>" = the exact hex a zone already paints in that colour family
            if (newHex && op.colour && !op.colour.exact && /\bsame\b/.test(String(planned.raw || planned.text || '')) && zcols.length) { var sameZ = zcols.filter(function (zc) { return zc.fam === familyOf(newHex); })[0]; if (sameZ) { newHex = sameZ.hex; op.colour = { name: op.colour.name, hex: sameZ.hex, exact: true }; } }
            if (op.keep) newHex = null;
            // a colour on a colour: ROTATE the hue of the original pixels (their shading / gradient survives); a flat hex only when either side is neutral or the buyer gave an exact colour
            if (newHex && (tg.kind === 'colour' || tg.kind === 'main') && region.colors && !(op.colour && op.colour.exact)) {          // MCPSCEN 2026-10-05: "main colour" shifts the hue too (SSL: main colour teal metallic laid a flat hex; the spray-can art lost its shading)
                var sh0 = hsl(region.colors[0]), dh0 = hsl(newHex);
                if (sh0.s > 0.22 && dh0.s > 0.22 && sh0.l > 0.1 && sh0.l < 0.92) {
                    adj = { hue: Math.round(((dh0.h - sh0.h + 540) % 360) - 180) };
                    if (op.colour && (op.colour.qual === 'dark' || op.colour.qual === 'deep')) adj.brightness = -30; else if (op.colour && (op.colour.qual === 'light' || op.colour.qual === 'pale')) adj.brightness = 30;
                    else { var hv = function (h) { var m = /^#?([0-9a-f]{6})$/i.exec(String(h || '')); if (!m) return 0; var n = parseInt(m[1], 16); return Math.max(n >> 16, (n >> 8) & 255, n & 255) / 255; }, vS = hv(region.colors[0]), vT = hv(newHex), bA = vS > 0.05 ? Math.round((vT / vS - 1) * 100) : 0;          // MCPSCEN 2026-10-05 (SSL: yellow -> "teal" came out bright CYAN: the shift kept yellow's brightness): the engine's brightness is v * (1 + b/100), so match the asked colour's value
                        if (Math.abs(bA) >= 8) adj.brightness = Math.max(-70, Math.min(60, bA)); }
                    what.push('shifted to ' + ((op.colour && op.colour.name && !/^#/.test(op.colour.name) && !op.colour.qual) ? op.colour.name : tintName(newHex, !!(env && env.mcpSemanticHexLabels))) + ', keeping the shading'); newHex = null;          // FIRSTTEST2: the buyer's own colour word ("pink", not "bubblegum")
                }
            }
            if (op.shade && region.colors) { var shp = shadeParams(op.shade); adj = extend(adj || {}, shp.adj); what.push(shp.label + ' (keeps the shading)'); newHex = null; }
            if (c) {
                what.push(c.label);
                if (c.zone) { zoneExtra = JSON.parse(JSON.stringify(c.zone)); finish = zoneExtra.finish || 'base::gloss'; delete zoneExtra.finish; delete zoneExtra.color; color = newHex || (c.colourFrom === 'own' ? 'finish' : (adj ? 'source' : (c.zoneColor || c.defaultColour || 'source')));          /* FIRSTTEST2: "yellow to purple, then carbon fiber on the purple": the hue-shifted paint IS the colour (the look's dark default would paint over it) */ if (color !== 'source' && color !== 'finish' && !newHex) newHex = color; }
                else { finish = c.found; if (c.shift) zoneExtra = { spec_shift: JSON.parse(JSON.stringify(c.shift)) }; }
            } else if (op.rel) { var rf = relFinish(op); finish = rf.found; what.push(rf.label); }
            else if (op.pop) { var shiny = (tg.kind === 'colour' || tg.kind === 'numbers' || tg.kind === 'sponsors' || tg.kind === 'accents'); finish = shiny ? 'base::f_metallic' : 'base::f_soft_matte'; what.push(shiny ? 'metallic, so it stands out' : 'flat matte, so the rest stands out'); }
            if (adj && !c && !finish) finish = 'base::gloss';
            if (newHex && !c) { what.push('recoloured ' + tintName(newHex, !!(env && env.mcpSemanticHexLabels))); if (!finish) finish = 'base::gloss'; color = newHex; }
            else if (newHex && c) { color = newHex; var cn1 = tintName(newHex, !!(env && env.mcpSemanticHexLabels)); if (!saysColour(c.label, cn1)) what.push('in ' + cn1); }
            var tex = op.texture || null;          // FIRSTTEST 2026-10-04: the texture rides in the SAME zone as the colour / finish (two zones on the same pixels: only the top one shows)
            if (tex) { if (!finish) finish = 'base::f_soft_gloss'; what.push(tex.mode === 'pattern' ? tex.label + ' pattern (' + tex.patternName + ')' : tex.label + ' shine texture (' + tex.specName + ', in the spec)'); }
            if (!finish) { missing.push({ why: 'action', label: label }); ask = { text: 'What should I do with ' + targetPhrase(tg, pal) + '? Pick a look, or tell me a colour.', chips: askWhat(targetChipName(tg, pal), pal) }; return; }
            if (op.exclude && op.exclude.length) { region = JSON.parse(JSON.stringify(region)); region.exclude = op.exclude.slice(); }
            if (op.strengthMul > 0) what.push((op.strengthMul < 1 ? 'toned down' : 'stronger') + ' (strength ' + Math.round(Math.min(1, op.strengthMul) * 100) + '%)');          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper: "less rainbow" = the same look, weaker
            if (op.scaleMul > 0 && finish) what.push((op.scaleMul < 1 ? 'smaller' : 'bigger') + ' (size ' + Math.round(op.scaleMul * 100) + '%)');          // HELPER_V2 fix pass 4: say the size change
            (parts || [null]).forEach(function (pt) {
                var ptn = pt ? String(pt).split('@') : null;          // ROUTER-FIX: "left side@rear third" = that portion of the part
                var rg = JSON.parse(JSON.stringify(region)), fixTol = !!rg._fixTol; delete rg._fixTol; if (rg.colors && !fixTol) { var paintMode = !!(newHex || adj || color !== 'source'), strictFamily = env && env.mcpSemanticColorFamily && tg.kind === 'colour' ? env.mcpSemanticColorFamily : null; if (strictFamily) { var familyColors = rg.colors.filter(function (h) { try { return familyOf(h) === strictFamily; } catch (e) { return false; } }); /* SPB-MCP 2026-10-05: accept an unambiguous exact label reported by this palette even at a display-name/family boundary; preserve all offline routing. */ if (!familyColors.length && r && r.entries) { var exactNamed = r.entries.filter(function (e) { return e.name === tg.word && rg.colors.indexOf(e.hex) !== -1; }), exactFamilies = []; exactNamed.forEach(function (e) { var f = familyOf(e.hex); if (exactFamilies.indexOf(f) === -1) exactFamilies.push(f); }); if (exactNamed.length && exactFamilies.length === 1) { strictFamily = exactFamilies[0]; familyColors = exactNamed.map(function (e) { return e.hex; }); } } rg.colors = familyColors; rg.mcpFamily = strictFamily; if (!rg.colors.length) { missing.push({ why: 'color-family', label: label }); ask = { text: 'I could not safely isolate only the ' + strictFamily + ' paint here, so I changed nothing.' }; return; } } var ef = edgeFitFor(rg.colors, paintMode, strictFamily, tg.kind === 'colour' || tg.kind === 'main'); rg.tolerance = paintMode ? TOL_PAINT : TOL_SPEC; if (ef) { rg.colors = ef.colors; rg.tols = ef.tols; rg.tolerance = ef.tolerance; } }
                if (ptn && (rg.colors || rg.layers)) { rg.part = ptn[0]; if (ptn[1]) rg.portion = ptn[1]; }
                var z = extend(zoneExtra ? JSON.parse(JSON.stringify(zoneExtra)) : {}, { name: cap(label) + (pt ? ' (' + String(pt).replace('@', ', ') + ')' : '') + ' ' + (what.join(', ') || 'edit'), finish: finish, color: color, region: rg });
                if (adj) extend(z, adj);
                if (tex) { if (tex.mode === 'pattern') { z.pattern = { id: tex.pattern, opacity: 60, scale: 1 }; z.spec_patterns = []; } else { z.spec_patterns = [{ id: tex.spec, opacity: 85, scale: 1 }]; z.pattern = { id: 'none' }; } }          // FIRSTTEST: the other version is one chip away (it replaces this one)
                if (op.scaleMul > 0) { z.scale = Math.round(op.scaleMul * 100) / 100; if (z.pattern && z.pattern.id && z.pattern.id !== 'none') z.pattern.scale = z.scale; if (z.spec_patterns && z.spec_patterns.length) z.spec_patterns.forEach(function (sp) { sp.scale = z.scale; }); }          // HELPER_V2 fix pass 4: "smaller" on the pattern just made = its scale
                if (op.strengthMul > 0) { if (String(color) === 'source' && finish) { z.spec_strength = Math.max(15, Math.min(200, Math.round(100 * op.strengthMul))); } else z.intensity = Math.max(15, Math.min(100, Math.round(100 * op.strengthMul))); }          // in-app gate b4-155 (fix pass 5): "less rainbow" on a finish-only zone (paint kept) set intensity, which measured 0 changed pixels; spec_strength moves the spec (1,813 cells on the hood)          // HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper
                if (op.exclude && op.exclude.length) z.name = z.name + ' (not the ' + op.exclude.join(' / ') + ')';
                if (op.recipe === 'ghost') { z.name = cap(label) + ' ghosted'; what = ['ghosted: the body colour with a different sheen']; }
                if (op.recipe === 'blackout') { z.name = cap(label) + ' blacked out'; what = ['blacked out (near-black ' + ((c && c.label) || 'satin') + ')']; }
                // HELPER FIX PASS 7 2026-10-05 (blind5 b5-047: "a thin red line around the roof" made the WHOLE CAR red): an outline is a real line along the part's edge (js/spb-pro-graphics.js kind "outline"), never a fill
                if (op.outline && tg.kind === 'part' && !pt && newHex) { var ow = Number(op.outline.w) || 0.02; z.region = { graphic: { kind: 'outline', part: tg.part, colour: String(newHex).toLowerCase(), w: ow } }; if (rg.exclude) z.region.exclude = rg.exclude.slice(); what = [(ow < 0.015 ? 'a thin ' : (ow > 0.03 ? 'a thick ' : 'a ')) + tintName(newHex, false) + ' outline along its edge']; z.name = cap(label) + ' outline ' + tintName(newHex, false); }
                // HELPER FIX PASS 7 2026-10-05 (blind5 b5-057: a door gradient became a solid whole-car blue): a fade on a part is a gradient zone fitted to THAT part, oriented by the car map (front->rear or roof-line->rocker)
                if (op.gradient && tg.kind === 'part' && op.gradient.from && op.gradient.to) { var gsp = partGradient(tg.part, op.gradient); z.gradient = gsp; z.color = String(op.gradient.from).toLowerCase(); var gnm = op.gradient.names || [tintName(op.gradient.from, false), tintName(op.gradient.to, false)]; what = ['a fade from ' + gnm[0] + ' to ' + gnm[1]]; z.name = cap(label) + ' fade ' + gnm[0] + ' to ' + gnm[1]; }
                z._meta = { label: label, what: what, share: share, element: !!rg.element, specOnly: color === 'source' && !adj, finishExplicit: !!(c || op.rel || op.pop), look: c ? c.id : null, parts: pt ? [ptn[0]] : (tg.kind === 'part' ? [tg.part] : []), kind: tg.kind, about: c ? c.about : '' };
                if (tex) { z._meta.texture = { mode: tex.mode, label: tex.label, id: tex.mode === 'pattern' ? tex.pattern : tex.spec, name: tex.mode === 'pattern' ? tex.patternName : tex.specName }; if (tex.mode === 'pattern') z._meta.specOnly = false; }
                if (below && below.ids.length) { z._meta.below = below.ids.slice(); z._meta.belowNames = below.names.slice(); z._meta.belowNote = below.note; }          // VISIBLE_COLOUR: the app places this zone under those
                if (tg.kind === 'colour') z._meta.visForce = !!(planned.force || env.hiddenOk);          // VISIBLE_COLOUR: "anyway" / the buyer's yes = the hidden colour too (zone on top)
                if (pt && tg.place) z._meta.placePart = true;          // ROUTER-FIX: one of several parts a PLACE stands for ("the rear of the car"): skipped when the car does not know it
                if (pt && tg.kind === 'colour') z._meta.label = label + ' on the ' + (ptn[1] ? ptn[1] + ' of the ' + ptn[0] : ptn[0]);          // "the black on the rear third of the left side", not four times "the black"
                if (tg.bodyNamed) z._meta.bodyNamed = true; if (tg.artObjects) z._meta.artObjects = tg.artObjects.slice();          // FIRSTTEST2: "on the base paint and on the spray paint can" -> the app adds the art layers that hold the colour
                zones.push(z);
            });
        }
        if (planned.atomicScope && (ask || missing.length)) {
            zones = [];
            if (ask) ask.text = 'Nothing was changed: I need to resolve both the body and the panel assignments first. ' + ask.text;
        }
        var outC = { zones: zones, missing: missing, ask: ask, notes: notes, pal: pal }; if (objects.length) outC.objects = objects; if (hiddenOut) outC.hiddenAsk = hiddenOut; if (noops.length) outC.noops = noops;
        if (asks.length && !planned.atomicScope) { outC.asks = asks.map(function (a) { return a.ask; }); outC.partial = !!(zones.length || objects.length); }          // FIRSTTEST2: done what resolved, ask only about the rest
        return outC;
    }
    // the online `refinish` tool and the offline parser meet here: { target:{colour|element|part}, look, colour, relative, keep_colours } -> same ops
    function compileRequest(req, env) {
        req = req || {}; var tg = null, tword = norm(req.target || req.colour_on_car || ''), looks = null;
        var cw = Dz().parseColours ? Dz().parseColours(tword) : [];
        if (/\bnumbers?\b/.test(tword)) tg = { kind: 'numbers' }; else if (SPONSORS_RE.test(tword)) tg = { kind: 'sponsors' };
        // MCPSCEN 2026-10-05 (MCP refinish target "number outline" recoloured the number FILL: the typed sentence reads outline / shadow / fill, the tool target did not)
        if (tg && tg.kind === 'numbers') { var nsm = SUB_RE.exec(tword) || SUB_RE.exec(norm(req.sub || '')); if (nsm) tg.sub = /outline|border|edge|outer/.test(nsm[1]) ? 'outline' : (/shadow/.test(nsm[1]) ? 'shadow' : 'fill'); }
        else if (cw.length) tg = { kind: 'colour', word: cw[0].name, hex: cw[0].hex, qual: qualBefore(' ' + tword, tword.indexOf(cw[0].name)) };
        else if (/\b(main|base|body)\b/.test(tword)) tg = { kind: 'main' };
        else if (ACCENT_RE.test(tword)) tg = { kind: 'accents', word: (ACCENT_RE.exec(tword) || [])[1] || 'accents' };
        else { var ph = null; PART_WORDS.forEach(function (pw) { if (pw[1].test(tword)) ph = pw[0]; }); if (ph) tg = { kind: 'part', part: ph }; else if (/\b(car|whole|everything|all)\b/.test(tword)) tg = { kind: 'body' }; }
        if (tg && req.layer) { var lsr = layerScope(String(req.layer).replace(/\s*layer\s*$/i, '') + ' layer', env && env.layers); if (lsr && lsr.ask) return { error: lsr.ask.text }; if (lsr && lsr.layers) { if (tg.kind === 'colour') tg.layers = lsr.layers; else if (tg.kind === 'body' || tg.kind === 'main' || tg.kind === 'numbers' || tg.kind === 'sponsors') tg = { kind: 'layer', layers: lsr.layers, word: lsr.word }; } }          // COPILOT-FIX
        // ROUTER-FIX 2026-10-04 (owner T1): a colour IN A PLACE (target "black" + part "rear bumper" / "rear of the car", or a target written "black near the rear of the car") selects that
        // colour INSIDE the place, never the whole place; a named object (object "spray can", or "yellow on the spray can") -> the app offers the layers that hold it / a box to draw
        if (tg && tg.kind === 'colour') {
            var pcl = null; try { CTX.pal = prepPalette((env || {}).palette); CTX.prevColour = false; pcl = parseClause('make the ' + tword + ' matte'); } catch (epc) {}          // "matte" = any action (so a bare object after the colour counts); the real action comes from the request fields
            var ptg = pcl ? pcl.targets.filter(function (x) { return x.kind === 'colour' && x.word === tg.word; })[0] : null;
            if (ptg && ptg.parts) { tg.parts = ptg.parts.slice(); if (ptg.place) tg.place = true; }
            if (ptg && ptg.object) tg.object = ptg.object;
            var pp = [].concat(req.part || req.parts || req.place || []).map(String).filter(Boolean), plist = tg.parts ? tg.parts.slice() : [];
            pp.forEach(function (p) { var pl2 = placeParts(p); if (!pl2.length) pl2 = [norm(p)]; pl2.forEach(function (x) { if (plist.indexOf(x) === -1) plist.push(x); }); if (placeIn(' ' + norm(p) + ' ')) tg.place = true; });
            if (plist.length) tg.parts = plist;
            if (req.object) tg.object = norm(req.object);
        }
        if (!tg) return { error: 'target must be a colour that is ON the car ("black", "dark blue"), "numbers", "sponsors", "main colour", "accents" or a part name; call describe_paint to see the car\'s real colours' };
        // MCPSCEN 2026-10-05 (RAM: refinish {target:"main colour", colour:"candy red"} gave a plain GLOSS red): a look word inside the colour ("candy red", "matte black", "pearl white") is the look when the rest is a colour and no look was given.
        if (!req.look && req.colour && !/^#/.test(String(req.colour))) { var cw0 = ' ' + norm(String(req.colour)) + ' ', lb = null; LOOKS.forEach(function (l) { (l.words || []).forEach(function (w) { if ((!lb || w.length > lb.length) && cw0.indexOf(' ' + w + ' ') !== -1 && w !== 'icy') lb = w; }); }); if (lb) { var rest0 = cw0.replace(' ' + lb + ' ', ' ').trim(), pcr0 = (rest0 && Dz().parseColours) ? Dz().parseColours(rest0) : []; if (pcr0.length && lookFor(lb)) req = Object.assign({}, req, { look: lb, colour: rest0 }); } }
        if (req.look) { looks = lookFor(req.look); if (!looks) return { error: 'unknown look "' + req.look + '"; use one of: ' + LOOKS.map(function (l) { return l.id; }).join(', ') + ' (or use add_zone / find_finishes for catalogue looks)' }; }
        var colour = null; if (req.colour) { req = Object.assign({}, req, { colour: /^#/.test(String(req.colour)) ? req.colour : tintColours(String(req.colour)) }); var pc = Dz().parseColours ? Dz().parseColours(norm(req.colour)) : []; if (pc.length) colour = { name: pc[0].name, hex: pc[0].hex, qual: qualBefore(' ' + norm(req.colour), norm(req.colour).indexOf(pc[0].name)) }; else if (/^#[0-9a-f]{6}$/i.test(String(req.colour))) colour = { name: req.colour, hex: String(req.colour).toLowerCase(), exact: true }; else return { error: 'colour not understood: ' + req.colour }; }
        var rel = req.relative === 'glossier' ? 'up' : (req.relative === 'duller' ? 'down' : null);
        var texture = req.texture ? textureFor(req.texture, req.texture_mode) : null; if (req.texture && !texture) return { error: 'texture not understood: ' + req.texture + ' (a concept like "snakeskin", "crocodile", "dragon scales", "fish scales", or a spec pattern id from find_spec_patterns)' };          // FIRSTTEST: the colour + finish + texture of ONE target in ONE zone
        if (!looks && !colour && !rel && !texture) return { error: 'say what it should become: look ("matte", "powder coat" ...), colour, or relative ("glossier" / "duller")' };
        var op = { texture: texture, target: tg, look: looks, colour: colour, rel: rel, soft: !!req.slightly, strong: false, shade: null, keep: !!req.keep_colours, pop: false };
        var exl = []; [].concat(req.exclude || []).forEach(function (w) { var k = /number/i.test(w) ? 'numbers' : (/stripe|tape/i.test(w) ? 'stripes' : (/sponsor|logo|decal/i.test(w) ? 'sponsors' : '')); if (k && exl.indexOf(k) === -1) exl.push(k); });
        if (exl.length && ['colour', 'main', 'body', 'part', 'accents'].indexOf(tg.kind) !== -1) op.exclude = exl;
        return compile({ ops: [op], text: '', raw: 'make the ' + tword + ' ' + (req.look || req.colour || ''), force: !!req.anyway }, env);
    }

    // the region a target resolves to (used to take a change back): compile with a dummy look and read the zone
    function regionFor(tg, env) { var c = compile({ ops: [{ target: tg, look: lookById('matte') }], text: '' }, env); return c.zones.length ? { region: c.zones[0].region, label: c.zones[0]._meta.label } : null; }
    // "what would look good on the black?": the colour ON the car the sentence is about (the advisor then ranks finishes for exactly those pixels)
    function colourTargetOf(text, env) {
        var pal = prepPalette((env || {}).palette); CTX.pal = pal; CTX.prevColour = false;
        var cl = clauseList(text), i, j;
        for (i = 0; i < cl.length; i++) { var pc = parseClause(cl[i]); for (j = 0; j < pc.targets.length; j++) { var tg = pc.targets[j]; if (tg.kind === 'colour') { var rf = regionFor(tg, env || {}); if (rf && rf.region && rf.region.colors) { var r = resolveColour(wantFor(tg.word, tg.hex, tg.qual), pal); return { label: rf.label, region: rf.region, hex: rf.region.colors[0], share: r.share }; } } } }
        return null;
    }
    window.SpbProEdit = { fixParts: fixParts, complaint: complaint, placeParts: placeParts, prepZoneColours: prepZoneColours, layerScope: layerScope, colourTargetOf: colourTargetOf, ctxOf: ctxOf, regionFor: regionFor, variantLooks: variantLooks, lookById: lookById, stepLook: stepLook, plan: plan, compile: compile, compileRequest: compileRequest, resolveColour: resolveColour, wantFor: wantFor, familyOf: familyOf, describe: describe, suggestions: suggestions, askWhat: askWhat, LOOKS: LOOKS, lookFor: lookFor, fixText: fixText, prepPalette: prepPalette, targetPhrase: targetPhrase, targetChipName: targetChipName, paletteLine: paletteLine, parseClause: parseClause, splitClauses: splitClauses, STARTER_LOOK: STARTER_LOOK };
})();
