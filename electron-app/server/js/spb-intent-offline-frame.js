/* ============================================================================
   HELPER V4 lane V4-F 2026-10-07: FRAME-FIRST OFFLINE reader.  window.SpbIntentOfflineFrame
   The offline helper produces an IntentFrame DIRECTLY (as the online model does), so offline and online share ONE path:
   frame -> SpbIntentPlan -> apply -> S3 measured report. Every planner fix lifts both.
     frameOf(text, prevTurns, env, opt) -> { frame, want, confidence, source }
       skeleton   = the kNN neighbours (js/spb-intent-knn.js read(): want + shape "verb:kind[:spec][:ref]")
       slots      = the current utterance through the SpbIntentFrame lexers (read / partsOf: parts, keep clauses, layers, elements, whole-car words)
                    and the kNN normaliser's typed slots (COL / FIN / PAT / REL / OBJ / NUMS / SPON / LAYER / N, in sentence order), after a
                    conservative typo pass on colour / finish / part words (this file)
       references = the last change from the env: SpbConvo's editCtx {targets} (the offline helper's env.last) or the planner's own last
                    {target, op, look} (env.planLast = SpbIntentPlan.live().last); the planner resolves every ref itself
       validated  = SpbIntentFrame.validate(frame, env); an invalid frame is never returned
     regexStrong(r, text, regexFrame, env) -> true = keep the regex reader's result (the "mix" policy)
     decide(text, env, r, opt) -> { frame, source, confidence } | null : the one call the route() hook makes (mix policy)
   ES5. Needs SpbIntentKnn + SpbIntentFrame; either missing = null (the regex reader stays in charge).
   Kill switch: window.SPB_OFFLINE_FRAME = '0' or localStorage SPB_OFFLINE_FRAME = '0'.
   ============================================================================ */
(function (root, factory) {
    var W = root || {};
    var api = factory(W);
    W.SpbIntentOfflineFrame = api;
    if (typeof module === 'object' && module && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function (W) {
    'use strict';
    var VERSION = '2026-10-07-v4g7';
    function flag(name, dflt) {
        try { if (W[name] != null) return String(W[name]); } catch (e) {}
        try { if (W.localStorage) { var v = W.localStorage.getItem(name); if (v != null) return String(v); } } catch (e2) {}
        return dflt;
    }
    function on() { return flag('SPB_OFFLINE_FRAME', '1') !== '0'; }
    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    var TH = { use: 0.0 };

    // ------------------------------------------------------------------ colours: canonical word -> hex (rule 8: neutral words = neutral hexes)
    var HEX = { red: '#d01818', maroon: '#800000', orange: '#ff7a00', yellow: '#ffd400', gold: '#d4af37', green: '#1fa83a', lime: '#7fff00', teal: '#008080', cyan: '#00e5ff',
        blue: '#1f4dff', navy: '#0b1f4d', purple: '#7a2bd6', violet: '#8f00ff', magenta: '#ff00ff', pink: '#ff3fa4', white: '#ffffff', cream: '#fffdd0', silver: '#c0c0c0',
        grey: '#808080', black: '#0a0a0a', brown: '#6b4423', tan: '#d2b48c', beige: '#e8d8b0', bronze: '#a8702a', copper: '#b87333' };
    var SHADE = { 'dark red': '#8b0000', 'dark orange': '#c04a00', 'light orange': '#ffb27a', 'dark yellow': '#c9a400', 'dark green': '#0b5d1e', 'light green': '#7ee08a', 'light blue': '#5fb4ff',
        'dark blue': '#0b2a6b', 'light purple': '#c3a3f0', 'dark purple': '#3d1166', 'dark grey': '#3a3a3a', 'light grey': '#c8c8c8', 'bright red': '#ff1a1a', 'bright blue': '#1e90ff',
        'bright green': '#39ff14', 'bright yellow': '#fff200', 'bright orange': '#ff6a00', 'bright pink': '#ff1493', 'light pink': '#ffb6c1', 'dark pink': '#c2185b', 'light yellow': '#fff59d' };
    function hexOfWord(w) {
        w = String(w || '').toLowerCase().trim(); if (/^#[0-9a-f]{6}$/.test(w)) return w;
        if (SHADE[w]) return SHADE[w]; if (HEX[w]) return HEX[w];
        var p = w.split(' '), h = HEX[p[p.length - 1]]; if (!h) return null;
        if (/^(dark|deep)$/.test(p[0])) return mix(h, '#000000', 0.45); if (/^(light|pale)$/.test(p[0])) return mix(h, '#ffffff', 0.45);
        return h;
    }
    function mix(a, b, t) { var o = '#'; for (var i = 1; i < 7; i += 2) { var x = Math.round(parseInt(a.substr(i, 2), 16) * (1 - t) + parseInt(b.substr(i, 2), 16) * t); o += (x < 16 ? '0' : '') + x.toString(16); } return o; }
    var RAINBOW = ['#ff0000', '#ff7a00', '#ffe100', '#00c853', '#0091ea', '#7b1fa2'];

    // ------------------------------------------------------------------ conservative typo pass (colour / finish / part words only; never a common English word)
    var VOCAB = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'white', 'black', 'silver', 'grey', 'gold', 'brown', 'maroon', 'navy', 'teal', 'cyan', 'magenta', 'violet', 'bronze', 'copper', 'beige', 'cream',
        'chrome', 'matte', 'satin', 'gloss', 'glossy', 'candy', 'pearl', 'metallic', 'brushed', 'carbon', 'camo', 'flames', 'checker', 'shiny', 'shine', 'shinier',
        'hood', 'roof', 'trunk', 'spoiler', 'bumper', 'bumpers', 'side', 'sides', 'door', 'doors', 'left', 'right', 'front', 'rear',
        'light', 'dark', 'bright', 'shiny', 'glitter', 'sparkle', 'reflective',
        'stripe', 'stripes', 'darker', 'lighter', 'smaller', 'bigger', 'thinner', 'thicker', 'instead', 'except', 'everything', 'numbers', 'sponsors', 'outline', 'gradient', 'rainbow', 'splitter', 'diffuser'];
    var STOP = {}; ('purpose purposes purple point points reason meant mean means used uses steps step reverse reversed works working selected chosen picked mock ' + 'read real bred bled ride wide hide tide site size sire sine aside good food mood wood hook hold hoot hoof look book took room root rood roam proof mate matter latte glass class grass gross glow blur blew blow glue clue true pick pine punk pint link while write whit greet green block blank slack back bleak silk old bold cold fold golf goad grew greg prey pray tell team tear teak real near fear gear hear wear dear bear year sear rare roar rest lift loft lest font frost dour stain satan chore chose flakes frames truck drunk strip strike stride wavy nave left right sides rider bumped bumps candle sandy handy pearly early peal peak blue pink rink sink pinky goals gods gild gale gray shin shone shiner since shire chose those these there their where were hard bard card leftover lefty frontal').split(' ').forEach(function (x) { STOP[x] = 1; });
    function dl(a, b, cap) {
        var n = a.length, m = b.length, i, j; if (Math.abs(n - m) > cap) return cap + 1; var d = [];
        for (i = 0; i <= n; i++) d[i] = [i]; for (j = 0; j <= m; j++) d[0][j] = j;
        for (i = 1; i <= n; i++) for (j = 1; j <= m; j++) { d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)); if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1); }
        return d[n][m];
    }
    var FIXC = {};
    function fixTok(w) {
        if (w.length < 4 || /[^a-z]/.test(w) || STOP[w] || VOCAB.indexOf(w) !== -1) return w;
        if (FIXC[w] != null) return FIXC[w];
        var x = w.replace(/([a-z])\1{2,}/g, '$1$1'), best = w, bd = 9; if (x !== w && VOCAB.indexOf(x) !== -1) return (FIXC[w] = x);
        var y = x.replace(/([a-z])\1/g, '$1'); if (y !== x && VOCAB.indexOf(y) !== -1) return (FIXC[w] = y);
        var cap = x.length >= 7 ? 2 : 1;
        VOCAB.forEach(function (v) { if (v.length < 4 || Math.abs(v.length - x.length) > cap) return; if (v[0] !== x[0] && !(v[0] === x[1] && v[1] === x[0])) return; var d = dl(x, v, cap); if (d <= cap && d < bd) { bd = d; best = v; } });
        return (FIXC[w] = best);
    }
    // part words the normaliser does not know (UK / slang / paraphrase): applied after prep, before norm
    var ALIAS = [[/\b(?:front lid|bonnet|engine cover|engine lid|front hood)\b/g, 'hood'], [/\b(?:top panel|roof panel|lid on top|the top(?! of| coat|coat| half| part| edge| stripe| side)|white top|black top|red top|blue top)\b/g, function (m) { return /^(white|black|red|blue) top$/.test(m) ? m.replace('top', 'roof') : 'the roof'; }],
        [/\b(?:rear lid|boot lid|boot|deck lid|decklid|trunk lid|back lid)\b/g, 'trunk'], [/\b(?:side mirrors?|wing mirrors?|door mirrors?)\b/g, 'mirrors'], [/\b(?:rear wing|back wing)\b/g, 'spoiler'],
        [/\b(?:front fascia|front valance)\b/g, 'front bumper'], [/\b(?:rear fascia|rear valance)\b/g, 'rear bumper']];
    // W3-SCOPE 2026-10-09 (lane W3-SCOPE; kill SPB_OF_CFG.noW3S): buyer synonyms the part / element lexicon does not know. nums / digits / numerals = the numbers layer ("nums black pls" painted the BODY black);
    // top part / top of the car / up top / lid = the roof; flank(s) = side(s); rear end = rear bumper. Probes (own wordings, w3scope/probes_norm.jsonl): see _easy_claude_work/eval/w3scope/REPORT.md.
    var ALIAS_W3S = [[/\b(?:nums?|numerals?|digits?)\b/g, 'numbers'],
        [/\b(?:on|up) top of (?:the |my |our |this )?(?:car|vehicle|truck|body|ride|machine)\b|\bup top\b/g, 'on the roof'],
        [/\b(?:top part|top of (?:the |my |our |this )?(?:car|vehicle|truck|body|ride|machine)|top section|upper part|car top(?! (?:wing|coat|half|stripe|edge|speed))|(?:the )?(?<!boot |deck |trunk |rear |back |engine |front |hood |gas |fuel )lid(?!\s+(?:on|of|for|over|at)\s+(?:the |my |our )?(?:trunk|boot|hood|bonnet|deck|rear|back|engine|front)))\b/g, 'the roof'],
        [/(^|\b(?:and|also|then|now|next|but|plus) |, ?)(?:the )?(left|right)(?: one| hand| hand side)?\b(?! (?:side|door|fender|mirror|panel|quarter|flank|half|colou?r|shade|finish|amount|way|now|away|there|here|spot|place|size|look|bumper|rear|front|\w+ing\b))/g, '$1$2 side'],          // W3-SCOPE: 'right blu' after a left-side edit = the right SIDE
[/[,;]?\s*((?:the |my )?(?:roof|hood|bonnet|trunk|spoiler|(?:front |rear )?bumpers?|(?:left |right )?sides?|doors?|numbers|sponsors|logos))\s+(?:no change|unchanged|stays?(?: the same| as is)?|as is|untouched|not touched|no touch(?:ing)?|does ?n'?t change|do ?n'?t change|remains?(?: the same)?)\b/g, function (m0, p1, off, str) { return /\b(?:all|every|each|entire|whole|everything|bodywork|body work|all over|the car|full car|rest)\b/.test(String(str).slice(0, off)) ? ' except ' + p1 : m0; }],          // W3-SCOPE class 8: 'pearl white on all bodywork, roof no change' = except the roof
                [/,? ?(?:including|incl\.?|and also|even|along with|plus) (?:the |all |my |its )?(?:stripes?|accents?|trim|details?|pinstripes?|decorations?)\b/g, ''],          // W3-SCOPE class 9: 'left side blue including the stripes' = the part's colour, accents included (it added a stripe)
        [/\b((?:left|right|front|rear) (?:side|bumper)|hood|roof|trunk|spoiler)((?: [a-z]+)?) (?:everything|all of it|all over)\b/g, '$1$2'],          // 'left side red everything' = that part, all of it
        [/\bflanks\b/g, 'sides'], [/\bflank\b/g, 'side']];
    var W3S_EXC_AT = 0; ALIAS_W3S.forEach(function (q, i) { if (typeof q[1] === 'function') W3S_EXC_AT = i; });
    function alias(s) { ALIAS.forEach(function (a) { s = s.replace(a[0], a[1]); }); if (!OF_CFG('noW3S') && !OF_CFG('noW3Sa')) ALIAS_W3S.forEach(function (a, i) { if (!OF_CFG('noW3Sa' + i)) s = s.replace(a[0], a[1]); }); return s; }
    function fixText(s) { return alias(String(s || '').replace(/[A-Za-z]+/g, function (w) { var l = w.toLowerCase(), f = fixTok(l); return f === l ? w : f; })); }

    // ------------------------------------------------------------------ cues
    var UNDO_RE = /\b(?:undo|go back|revert|take (?:it|that) back|put (?:it|that|them) back|scratch that|cancel that|reverse that|back to (?:how|what|the way|before|the old|the original)|bring (?:it )?back)\b/;
    // V4-G round 4 (regression.jsonl ff vs '0'): + 'blend the hood from green to gold' (a fade); J4a-J4t / G33 below, see docs/handoff_reports/HELPER_V3_STAGES.md (V4-G round 4)
    var GRAD_RE = /\b(?:fade|fades|faded|fading|gradient|ombre|blend(?:s|ing)? (?:from|into|to)|blend(?:s|ing)? (?:the |my )?\w+(?: \w+)? from (?=\w+ (?:to|into) )|transition(?:s|ing)? (?:from|into|to)|melt(?:s|ing)? into)\b/;
    var PIN_RE = /\bpin ?(?:stripes?|lines?)\b|\bpinstrip\w*\b|\b(?:line|stripe)(?: \(?#?[0-9a-z]+\)?)? (?:between|where|along the (?:seam|join|edge))\b|\b\d+ ?px (?:line|stripe|pinline)\b/;          // V4-G: 'a 4px line (FFC72C) where body meets top'
    var STRIPE_RE = /\b(?:stripes?|striped|bands?|racing stripes?|rally stripes?|lines? (?:\w+ )?(?:down|along))\b/;
    var OUTL_RE = /\boutlin\w*\b|\bborder\b|\bstroke\b|\b(?:line|ring|edge) (?:around|round)\b|\baround the edges?\b/;
    var OPP_RE = /\b(?:other side|opposite side|mirror (?:it|that)|same (?:thing )?on the (?:right|left|other)|(?:right|left) side (?:too|as well|same|also))\b/;
    var TOO_RE = /\b(?:too|as well|also)\b|^\s*(?:and|also|plus)\b|\bsame (?:on|for) (?:the )?\w/;
    var INSTEAD_RE = /\binstead\b|^\s*(?:no+|nah|nope|actually|wait|hmm+|ugh|not)\b|\bi (?:said|meant|mean|wanted)\b|\bwrong (?:part|side|one)\b/;
    var HIDE_RE = /\b(?:hide|turn off|switch off|toggle off)\b/, SHOW_RE = /\b(?:show|unhide|turn on|switch on)\b/;
    var BODY_W = /\b(?:(?:all|every|each)(?: of)?(?: the)? (?:parts?|panels?|areas?|sections?|pieces)|whole car|entire car|whole thing|the whole|everything|everywhere|all over|the car|the body|body|my car|full car|base colou?r|body colou?r|car body|paint job|all of it|overall|main colou?r|livery|the truck|my truck|the rest)\b/;
    var EXC_RE = /\b(?:except(?: for)?|apart from|other than|besides|but not|without|excluding|minus|save for|leave|leaving|but leave|but keep|keep)\b/;
    var STROKE_W = [[/\bhairline\b/, 'hairline'], [/\b(?:thin|fine|skinny|narrow|slim|pin)\b/, 'thin'], [/\b(?:thick|wide|fat|bold|broad|big)\b/, 'thick'], [/\bmedium\b/, 'medium']];
    var AXIS = [[/\b(?:at|on|along) the (?:very )?(?:bottom|rockers?|sills?)\b[^.;]{0,60}\b(?:at|to(?:wards?)?|on|near) the (?:very )?(?:top|roof)\b/, 'bottom_to_top'], [/\b(?:at|on|along) the (?:very )?(?:top|roof)\b[^.;]{0,60}\b(?:at|to(?:wards?)?|on|near) the (?:very )?(?:bottom|rockers?|sills?)\b/, 'top_to_bottom'], [/\bfrom the (?:bottom|rocker)|\bup from|\bfading up|\bfade up|\bupward/, 'bottom_to_top'], [/\bfrom the (?:top|roof)|\bdown(?:ward)?\b/, 'top_to_bottom'], [/\bfrom the (?:rear|back)\b/, 'rear_to_front'], [/\bfrom the (?:front|nose)\b|\bfront to (?:back|rear)\b/, 'front_to_rear']];          // V4-G round 4 J4x: 'at the bottom ... at the top' (the normaliser turns top into roof) sets the fade axis
    var OBJ_PART = [[/^(?:splitter|front lip|air dam|chin|nose|front end|grill|grille)/, ['front bumper']], [/^(?:diffuser|rear end|back end|tail(?!\s*(?:lights?|lamps?|lens)))/, ['rear bumper']], [/^(?:fenders?|quarter|rockers?|skirts?|doors?)/, ['left side', 'right side']], [/^(?:wing|top wing)/, ['spoiler']]];
    var UNPAINT_RE = /^(?:wheels?|rims?|tyres?|tires?|windows?|windshield|wind ?screen|glass|headlights?|tail ?lights?|lights?|exhaust|interior|seats?|helmet|roll ?cage|cage)$/;
    var FIN_EXTRA = [[/\bpearl(?:escent|y)?\b/, 'pearl'], [/\bcandy\b|\bkandy\b/, 'candy'], [/\bchrome\b/, 'chrome'], [/\bmatte?\b|\bflat\b(?! (?:paint|out|colou?r))/, 'matte'], [/\bsatin\w*\b/, 'satin'], [/\bmetal(?:lic|ic)?\b|\bmetal ?flake\b/, 'metallic'], [/\bglossy?\b|\bhigh gloss\b|\bwet(?: look\w*)?\b|\bceramic\w*\b|\bshiny\b|\bshinier\b(?= but| and keep| keep)/, 'gloss'], [/\bbrushed\b/, 'brushed'], [/\bsparkl\w*\b|\bglitter\w*\b/, 'metallic'], [/\bprimer\b/, 'matte'], [/\bstealth\b/, 'matte']];          // V4-G J4s: 'stealth black' = matte black
    // R8-FIN 2026-10-08: buyer FINISH PHRASES the single-word finish slots drop or mis-pick ("rainbow chrome" = plain chrome, "glitter" = metallic, "color shift purple green" = holographic green,
    // "galaxy paint" = a cipher pattern, "starry night" = an answer, "rusty" = patina matte). Each row: re = the phrase (typo-tolerant), label = the buyer's words, key = the closest catalogue finish
    // (checked in the atlas; the label shows the pick), alts = 1-2 other catalogue picks named after the change, q = atlas query when a colour pair picks (colour shift), colour / family = a plain
    // colour + Foundation finish instead of a catalogue key, dropCols = the colours named belong to the finish (they are not a recolour). Kill: SPB_OF_CFG.noR8f (all), noR8g (alternatives text).
    var R8_FIN = [
        { id: 'rainbowflake', re: /\b(?:rainbow|holo\w*|hologra\w*|prism\w*|spectrum|iridescent)\s+(?:flake\w*|fleck\w*|glitter\w*|sparkl\w*|metal ?flake)\b/, label: 'rainbow flake', key: 'base::efx_holo_flake', alts: ['base::sequin_rainbow', 'base::at_disc_rainbow'] },
        { id: 'rainbowchrome', re: /\b(?:rainbo\w*|prism\w*|spectrum|spectral|holo\w*|hologra\w*|iridescent|opal\w*)\s+(?:chrom\w*|mirror)\b|\bchrom\w*\s+(?:rainbow|holo\w*|prism\w*)\b/, label: 'rainbow chrome', key: 'base::at_disc_rainbow', alts: ['base::efx_holographic_drift', 'base::f_chrome'] },
        { id: 'colourshift', re: /\bcolou?r ?(?:shift\w*|flip\w*|chang\w*)\b|\bchameleon\b|\bchrom[ae]? ?flair\b|\bflip ?(?:flop|paint)\b|\bmulti ?chrome\b/, label: 'colour shift', key: 'base::chromaflair', q: 'chameleon', alts: ['base::chameleon', 'monolithic::chameleon_aurora'], dropCols: true, onlyShift: true },
        { id: 'glitter', re: /\bglitter\w*\b|\bsparkl\w*\b|\bglitz\w*\b|\bsequin\w*\b/, label: 'glitter', key: 'base::efx_micro_glitter', alts: ['monolithic::sparkle_diamond_dust', 'base::metal_flake_base'] },
        { id: 'metalflake', re: /\bmetal ?fl[ae]ke\w*\b|\bfleck\w*\b/, label: 'metalflake', key: 'base::metal_flake_base', alts: ['base::efx_chunky_flake', 'base::efx_micro_glitter'], needCols: true },
        { id: 'liquidmetal', re: /\bliquid (?:metal|chrome|mercury|silver)\b|\bmercury\b/, label: 'liquid metal', key: 'monolithic::liquid_metal', alts: ['base::alubeam', 'base::f_chrome'] },
        { id: 'liquidgold', re: /\bliquid gold\b|\bmolten gold\b/, label: 'liquid gold', colour: { word: 'liquid gold', hex: '#d4af37' }, family: 'chrome', alts: ['base::f_chrome', 'monolithic::liquid_metal'] },
        { id: 'pewter', re: /\bpewter\b/, label: 'pewter', colour: { word: 'pewter', hex: '#8e9094' }, family: 'metallic', alts: [] },
        { id: 'hammered', re: /\bhammer(?:ed)?\b/, label: 'hammered metal', key: 'base::efx_hammered', alts: ['monolithic::hammered_copper', 'base::efx_sandblasted'] },
        { id: 'rust', re: /\brust(?:y|ed)?\b/, label: 'rust', key: 'base::efx_rust_through', alts: ['base::cbp_scav_rust', 'base::efx_verdigris'] },
        { id: 'patina', re: /\bpatina\w*\b|\bverdigris\b|\bweather(?:ed)?\b/, label: 'patina', key: 'base::efx_verdigris', alts: ['monolithic::grad_copper_patina', 'base::efx_rust_through'] },
        { id: 'psychedelic', re: /\bpsychedel\w*\b|\btie ?dye\b|\bhippie\b|\btrippy\b/, label: 'psychedelic', key: 'base::psychedelic_swirl', alts: ['monolithic::psychedelic', 'base::hippie_rainbow'] },
        { id: 'galaxy', re: /\bgalax\w*\b|\bnebula\w*\b|\bcosmic\b|\bstarry\b|\bstar ?(?:field|dust)\b|\bnight sky\b|\bouter space\b/, label: 'galaxy', key: 'base::pour_galaxy', alts: ['monolithic::sparkle_galaxy', 'monolithic::cf_midnight_galaxy'] },
        { id: 'primer', re: /\bprimer\b/, label: 'primer', key: 'base::primer', alts: ['base::f_soft_matte', 'base::flat_black'], dropCols: true },
        { id: 'bare', re: /\b(?:bare|raw|unpainted|naked)\s+(?:steel|metal|aluminium|aluminum|iron)\b/, label: 'bare metal', key: 'monolithic::bare_aluminum', alts: ['base::raw_aluminum', 'base::titanium_raw'], dropCols: true },
        { id: 'brushedal', re: /\bbrushed\s+(?:aluminium|aluminum|alloy)\b/, label: 'brushed aluminium', key: 'base::brushed_aluminum', alts: ['base::f_brushed', 'monolithic::brushed_steel_dark'], dropCols: true },
        { id: 'rosegold', re: /\brose ?gold\b/, label: 'rose gold', colour: { word: 'rose gold', hex: '#b76e79' }, family: 'metallic', alts: ['base::electroplated_gold', 'monolithic::cf_rose_gold_dust'] },
        { id: 'gunmetal', re: /\bgun ?metal\b/, label: 'gunmetal', colour: { word: 'gunmetal', hex: '#4a4f57' }, family: 'metallic', alts: ['base::gunmetal', 'monolithic::brushed_gunmetal'] },
        { id: 'piano', re: /\bpiano black\b|\bpiano gloss\b/, label: 'piano black', colour: { word: 'piano black', hex: '#0a0a0a' }, family: 'gloss', alts: ['base::piano_black', 'base::f_soft_gloss'] },
        { id: 'shimmer', re: /\bshimmer\w*\b|\bpearly\b/, label: 'shimmer', family: 'pearl', keepCols: true }
    ];
    function r8Any(t) { if (OF_CFG('noR8f')) return false; for (var i = 0; i < R8_FIN.length; i++) { var e = R8_FIN[i]; if (e.id === 'shimmer' || !e.re.test(t)) continue; if (e.onlyShift && !/\bcolou?r ?(?:shift|flip)|\bchrom[ae]? ?flair\b|\bmulti ?chrome\b|\bflip ?(?:flop|paint)\b/.test(t)) continue; return true; } return false; }
    function r8Name(k) { try { var A = W.SpbAIAtlas, it = A && A.lookup ? A.lookup(k) : null; if (it && it.n) return String(it.n); } catch (e) {} return null; }
    function r8Has(k) { return !!r8Name(k) || /^base::f_/.test(k); }
    // returns { fin: {family, key?, keep_colour:false, r8:{...}}, colour?, dropCols } or null
    function r8Phrase(f, owns, cols) {
        if (OF_CFG('noR8f')) return null;
        for (var i = 0; i < R8_FIN.length; i++) {
            var e = R8_FIN[i]; if (!e.re.test(f) || !owns(e.re)) continue;
            if (e.onlyShift && !/\bcolou?r ?(?:shift|flip)|\bchrom[ae]? ?flair\b|\bmulti ?chrome\b|\bflip ?(?:flop|paint)\b/.test(f) && !/\b(?:red|orange|yellow|green|blue|purple|violet|pink|teal|cyan|gold|silver|black|white|bronze|copper|brown|magenta|turquoise)\b/.test(f)) continue;          // a bare "chameleon" keeps the encyclopedia path (it already picks Chameleon Aurora)
            if (e.needCols && !(cols && cols.length)) continue;          // metal flake with no colour keeps the paint colour (the Foundation metallic), as before
            var out = { id: e.id, label: e.label, dropCols: !!e.dropCols, keepCols: !!e.keepCols };
            if (e.colour) { out.colour = e.colour; out.fin = { family: e.family, keep_colour: false }; return out; }
            if (e.family && !e.key) { out.fin = { family: e.family, keep_colour: !(cols && cols.length) }; return out; }
            var key = e.key, nm = null, alts = (e.alts || []).slice();
            if (e.q && cols && cols.length) {          // a colour pair picks the catalogue's own shift ("purple green" = CX Purple Green Abstract Shift)
                var cw = (f.match(/\b(?:red|orange|yellow|green|blue|purple|violet|pink|teal|cyan|gold|silver|black|white|bronze|copper|brown|magenta|turquoise)\b/g) || []).filter(function (w, i, a) { return a.indexOf(w) === i; }), qq = e.q + ' ' + (cw.length ? cw : cols.map(function (c) { return c.word || c.v || ''; })).join(' '), hits = [];
                try { hits = (W.SpbAIAtlas && W.SpbAIAtlas.find({ query: qq, type: 'finish', limit: 4 })) || []; } catch (eF) { hits = []; }
                if (hits.length) { key = hits[0].key || hits[0].id; nm = hits[0].name || hits[0].n; alts = hits.slice(1, 3).map(function (h) { return h.key || h.id; }); }
            }
            if (!r8Has(key)) { var alt0 = alts.filter(r8Has)[0]; if (!alt0) return null; key = alt0; alts = alts.filter(function (a) { return a !== alt0; }); }
            nm = nm || r8Name(key) || e.label;
            out.fin = { family: e.label + ' (' + nm + ')', key: key, keep_colour: false, r8: { label: e.label, pick: nm, alts: alts.filter(r8Has).filter(function (a) { return a !== key; }).slice(0, 2).map(function (a) { return { key: a, name: r8Name(a) || a.replace(/^[a-z]+::(?:f_)?/, '').replace(/_/g, ' ') }; }) } };
            return out;
        }
        return null;
    }
    // R8-FIN 2026-10-08 (owner: "all black, no wait blue", "red - actually make it blue", "hood green... scratch that, gold"): a correction inside ONE message = act on the LAST choice only.
    // The text before the cue loses its look words (colour / finish); a new target after the cue wins when it is the same part (or the car); a different part after the cue is an addition, left alone.
    // Kill: SPB_OF_CFG.noR8c.
    var R8_CORR = /(?:^|[\s,.;:!?-])(?:no+[,.]?\s+wait|wait[,.]?\s+no+|no+[,.]?\s+no+|no+[,.]?\s+(?:make that|scratch that|i mean|sorry|actually)|actually[,.]?(?:\s+no+)?|scratch (?:that|it|those)|forget (?:that|it)|never ?mind(?: that)?|i mean|or rather|make that|change (?:that|it) to|on second thought|hold on|hang on|cancel that|ignore (?:that|me)|my bad|oops|sorry|wait)(?=[\s,.;:!?-]|$)[\s,.;:!?-]*/i;
    var R8_LOOKW = /#[0-9a-f]{3,6}\b|\b(?:red|orange|yellow|green|blue|purple|violet|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|lime|cyan|magenta|brown|bronze|copper|tan|cream|beige|turquoise|mint|olive|burgundy|crimson|charcoal|gunmetal|ivory|lavender|lilac|peach|coral|salmon|rose)\b|\b(?:chrome|chromy|matte|matt|flat|satin|gloss\w*|shiny|metallic|metal|pearl\w*|candy|carbon|holo\w*|brushed|glitter\w*|metal ?flake|primer|frozen|rainbow|chameleon|camo\w*|flames?)\b/gi;
    var R8_PARTW = /\b(?:hood|bonnet|roof|trunk|boot|deck|spoiler|wing|bumpers?|sides?|doors?|fenders?|quarters?|panels?|nose|splitter|mirrors?|car|body|everything|whole|truck|all)\b/gi;
    function r8Parts(t) { var m = String(t || '').toLowerCase().match(R8_PARTW) || [], o = {}; m.forEach(function (w) { w = w.replace(/s$/, ''); if (/^(?:car|body|everything|whole|truck|all)$/.test(w)) w = 'car'; if (/^(?:hood|bonnet)$/.test(w)) w = 'hood'; if (/^(?:trunk|boot|deck)$/.test(w)) w = 'trunk'; if (/^(?:spoiler|wing)$/.test(w)) w = 'spoiler'; if (/^(?:side|door|fender|quarter|panel)$/.test(w)) w = 'side'; o[w] = 1; }); return Object.keys(o); }
    // W1-PARSE 2026-10-08: 'everything black even the spoiler' / 'all red including the hood and roof' = the WHOLE car (the even-clause says the part is NOT left out); the reader painted only the named parts.
    // The include-clause is dropped when a whole-car word comes before it and no look word follows it. Kill: SPB_OF_CFG.noW1i.
    var W1_WHOLE = /\b(?:everything|every ?thing|all|whole|entire|every part|all parts|all panels|all of it|the (?:car|truck|body))\b/i;
    var W1_INCL = /\s*,?\s*\b(?:and \s*)?(?:even|including|incl|as well as|along with)\s+(?:the |my )?(?:(?:front |rear |back |left |right )?(?:hood|bonnet|roof|trunk|boot|spoiler|wing|bumpers?|doors?|sides?|mirrors?|fenders?|splitter|diffuser)(?:\s*(?:,|and|&)\s*(?:the |my )?)?)+/i;
    function w1Incl(t) {
        if (OF_CFG('noW1i')) return t; t = String(t).replace(/\b(?:all|every|each)(?: of)?(?: the)? (?:parts?|panels?|areas?|sections?|pieces)\b(?! of)/gi, 'everything');          // 'all parts blue without the spoiler' = everything (the guard rules asked back on 'parts')
        var m = W1_INCL.exec(t); if (!m) return t; var before = t.slice(0, m.index), after = t.slice(m.index + m[0].length);
        if (!W1_WHOLE.test(before)) return t;
        R8_LOOKW.lastIndex = 0; var al = /^\s*(?:in |to |with |as |is |are |a |an )?(?:\w+ )?/.exec(after); var nxt = after.slice(0, 18); var hasL = R8_LOOKW.test(nxt); R8_LOOKW.lastIndex = 0;
        if (hasL && !/^\s*[.!,;]/.test(after) && !/[,;]\s*$/.test(m[0])) return t;          // 'even the roof blue' = a second job, not an include
        return (before.replace(/\s+$/, '') + (after && !/^\s*[.!?;,]/.test(after) ? ' ' : '') + after.replace(/^\s+/, '')).replace(/\s{2,}/g, ' ').replace(/\s+([.!,;])/g, '$1');
    }
    // W1-PARSE 2026-10-08 (lane W1-PARSE; owner failure "who made the roof yellow?? make it white again" painted the roof YELLOW): a COMPLAINT clause names the look the buyer
    // does NOT want ("who made X yellow", "why is X blue", "it's orange now"), the next clause is the correction ("make it white again", "I want red", "change it back to white").
    // The complaint's look words are dropped and its part is carried into the correction ("make it white" -> "make the roof white"). Kill: SPB_OF_CFG.noW1c.
    var W1_CUE = /\b(?:who|what|why|how come)\s+(?:made|painted|turned|changed|did|is|are|was|were|has|have|does|do|the (?:hell|heck))\b|\b(?:it'?s|its|it is|they'?re|they are|that'?s|thats|is|are|was|were|keeps?|came out|turned out|went|got|became|still|looks?|looking)\b[^,.;!?]{0,28}\b(?:now|again|still|instead|too)\b|\b(?:it'?s|its|it is|they'?re|they are|that'?s|thats|is|are|was|were|went|turned|got|looks?|still)\s+(?:still |so |too |really |very |now |all )?(?:bright |dark |light |ugly |wrong )?(?:red|orange|yellow|green|blue|purple|violet|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|lime|cyan|magenta|brown|bronze|copper|tan|cream|beige|turquoise|mint|olive|burgundy|crimson|charcoal|gunmetal|ivory|lavender|lilac|peach|coral|salmon|rose|chrome|matte|matt|flat|satin|glossy|shiny|metallic|pearl\w*|candy|carbon|holo\w*)\b/i;
    var W1_FIX = /^\s*(?:(?:ok|okay|so|and|but|now|just|please|pls|plz)[\s,]+)*(?:(?:i|we)\s+(?:want|need|wanted|needed|would like|d like|'d like|like)|(?:it|they|that|this)\s+(?:should|needs? to|has to|must|ought to)\s+be|(?:it|they)\s+(?:was|were)\s+supposed to be|make|set|put|turn|paint|change|switch|swap|go|take|bring|give|let'?s|lets|redo|fix|restore|revert|return|undo|back)\b/i;
    function w1Corr(s) {
        if (OF_CFG('noW1c')) return null; if (!s || s.length > 220) return null;
        var cl = s.split(/\s*[?!.;]+\s+|\s*[?!.;]+$|\s*,\s*|\s+-+\s+|\s+(?:but|so|and)\s+(?=(?:i|we|make|set|put|turn|paint|change|switch|go|take|bring|give|redo|fix|restore|revert|return|undo|back)\b)/i).filter(function (x) { return x && x.replace(/\W+/g, ''); });
        if (cl.length < 2) return null;
        for (var i = 1; i < cl.length; i++) {
            var before = cl.slice(0, i).join(', '), after = cl.slice(i).join(', ');
            R8_LOOKW.lastIndex = 0; var bl = before.match(R8_LOOKW); R8_LOOKW.lastIndex = 0; var al = after.match(R8_LOOKW); R8_LOOKW.lastIndex = 0;
            if (!bl || !bl.length || !al || !al.length) continue;
            if (!W1_FIX.test(after)) continue;
            {          // a STATE clause about one part ('the hood is red, make the roof blue'): the part it describes is not a target
                var apS = (after.toLowerCase().match(R8_PARTW) || []), bpS = (before.toLowerCase().match(R8_PARTW) || []);
                if (apS.length && bpS.length && !/\b(?:make|paint|turn|change|set|put|swap|switch|want|need|keep|leave|dont|don't|and|also|too|both|same|like|match|copy)\b/i.test(before) && /\b(?:is|are|was|were|'s)\s+(?:(?:now|still|all|just|so|too)\s+)?\w*\s*(?:\w+\s+)?(?:red|orange|yellow|green|blue|purple|violet|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|brown|bronze|chrome|matte|satin|glossy|shiny|carbon)\b/i.test(before) && !apS.some(function (x) { return /^(?:car|body|everything|whole|truck|all)$/.test(x) || bpS.indexOf(x) !== -1; })) return after.replace(/^[\s,.;:!?-]+/, '');
            }
            if (!W1_CUE.test(before)) continue;
            if (/\b(?:numbers?|logos?|sponsors?|decals?|stickers?|stripes?|letters?|keep|leave|dont|don't|do not|without|except|and also|also|too|both|rest)\b/i.test(after)) continue;
            var bset = bl.map(function (x) { return x.toLowerCase(); }), aset = al.map(function (x) { return x.toLowerCase(); });
            if (aset.every(function (x) { return bset.indexOf(x) !== -1; })) continue;          // the same look both times = nothing was corrected
            var bpr = (before.toLowerCase().match(R8_PARTW) || []).filter(function (w) { return !/^(?:car|body|everything|whole|truck|all)$/.test(w); }), apr = (after.toLowerCase().match(R8_PARTW) || []);
            if (apr.length) { if (!bpr.length) return after.replace(/^[\s,.;:!?-]+/, ''); var same = apr.some(function (x) { return bpr.indexOf(x) !== -1 || /^(?:car|body|everything|whole|truck|all)$/.test(x); }); if (!same) continue; return after.replace(/^[\s,.;:!?-]+/, ''); }
            R8_LOOKW.lastIndex = 0; var lookTxt = after.match(R8_LOOKW).join(' '); R8_LOOKW.lastIndex = 0;
            var seen = {}, pw = bpr.filter(function (w) { var k = w.replace(/s$/, ''); if (seen[k]) return false; seen[k] = 1; return true; });
            return 'make the ' + (pw.length ? pw.join(' and the ') : 'car') + ' ' + lookTxt;
        }
        return null;
    }
    function r8Corr(t) {
        if (OF_CFG('noR8c')) return t; var s = String(t || ''); var w1 = w1Corr(s); if (w1) return w1; var m = R8_CORR.exec(s); if (!m) return t;
        var before = s.slice(0, m.index), after = s.slice(m.index + m[0].length);
        if (!before.replace(/[\s,.;:!?-]+/g, '') || !after.replace(/[\s,.;:!?-]+/g, '')) return t;
        R8_LOOKW.lastIndex = 0; var bl = before.match(R8_LOOKW); R8_LOOKW.lastIndex = 0; var al = after.match(R8_LOOKW); R8_LOOKW.lastIndex = 0;
        if (!bl || !bl.length || !al || !al.length) return t;          // only a look before AND after the cue is a changed mind
        if (/\b(?:and|also|plus|too|as well)\b/i.test(after.slice(0, 12)) && !/\b(?:instead|no wait|scratch|forget)\b/i.test(s)) return t;
        if (/\b(?:numbers?|logos?|sponsors?|decals?|stickers?|stripes?|letters?|text|keep|leave|dont|don't|do not|without|except|but not|only|also|too|both|rest)\b/i.test(after)) return t;          // a second instruction about something else, not a changed mind
        var bp = r8Parts(before), ap = r8Parts(after);
        if (!ap.length && after.trim().split(/\s+/).length > 7) return t;
        if (ap.length && bp.length && !ap.some(function (x) { return bp.indexOf(x) !== -1 || x === 'car'; }) ) return t;          // a different part after the cue = an addition ("hood red, actually the roof blue too")
        if (ap.length) return after.replace(/^[\s,.;:!?-]+/, '');          // the part is named again: the later sentence stands alone
        return (before.replace(R8_LOOKW, ' ').replace(/\s{2,}/g, ' ').replace(/[\s,.;:!?-]+$/, '') + ' ' + after).replace(/\s{2,}/g, ' ').trim();          // "all black, no wait blue" = "all blue"
    }
    var Q_START = /^(?:(?:wait|so|and|ok|okay|hmm+|also|but|um+|hey|quick question|question)[, ]+)?(?:how|what|whats|what's|why|which|where|when|who|does|do (?:i|you|we|u)|did|is|are|was|were|should|would it|will it|could i|can i (?!get|have|haz|please)|show me .*\b(?:vs|versus|or|compare(?:d)?)\b|tell me|explain)\b/i;
    var ACK_RE = /^(?:fine|ok(?:ay)?|cool|nice|great|perfect|thanks|thank you|ty|good|sweet|awesome|love it|looks good|alright)\b/i, ACK_STATE = /\b(?:they're|theyre|it's|its|that's|thats|they are|it is|looks?|now|is (?:readable|fine|good|better|ok|okay|perfect|great))\b/, IMPER = /\b(?:make|paint|turn|change|add|put|do|go|try|give|swap|use|switch|set)\b/;
    var TRUCK_RE = /\b(?:bed|cab|tailgate|tonneau)\b/;
    var TRIM_RE = /\b(?:trim|accents?|details?|badges?|emblems?|lettering|edges|bits|stuff on)\b/;          // owner: "silver accent / trim" = ask every time
    var OBJ_RAW = /\b(?:wings?|mirrors?|splitter|diffuser|fenders?|skirts?|canards?|vents?|scoops?|intakes?|grill|grille|lip)\b/;
    var INTERJ = /^\s*(?:no+|nah|nope|no wait|nope wait)\s*(?:[,.!-]|\s+(?:wait|i |make|do |the |just|actually|go |hood|roof|numbers?|nums?|digits?|sponsors?|logos?|decals?|left|right|front|rear|everything|whole|trunk|spoiler|bumper|side|doors?|[a-z]+ (?:too|instead)))/;
    var INTERJ_STRIP = /^\s*(?:no+|nah|nope)(?:\s+wait)?\s*[,.!-]?\s*/i;
    var TWO_TOO = /\b(hood|roof|trunk|spoiler|bumper|bumpers|side|sides|rear|front|left|right|doors?) 2$/;
    var PAT_RAW = /\b(animal ?print|mud(?:dy)?|dirt(?:y)?|grime|grimy|mud splatter|snake ?skin|leopard|zebra|tiger stripes?|cheetah|giraffe|dalmatian|forged(?: carbon)?|hex(?:agon)? carbon|honeycomb|houndstooth|plaid|tartan|marble|wood ?grain|damascus|tribal|polka dots?|spots)\b/;
    var THEMES = [[/\bgulf\b/, [['light blue', '#6fb7e3']], [['orange', '#ff7a00']]], [/\bmartini\b/, [['white', '#f0f0f0']], [['light blue', '#5fb4ff'], ['dark blue', '#0b2a6b'], ['red', '#d01818']]],
        [/\b(?:american|usa|us|stars and stripes) flag\b|\bamerican flag\b|\bred white (?:and|n) blue\b/, [['white', '#ffffff']], [['red', '#d01818'], ['blue', '#1f4dff']]], [/\bjohn player|\bjps\b/, [['black', '#0a0a0a']], [['gold', '#d4af37']]],
        [/\brothmans\b/, [['white', '#ffffff']], [['dark blue', '#0b2a6b'], ['red', '#d01818']]], [/\bbumblebee\b/, [['yellow', '#ffd400']], [['black', '#0a0a0a']]],
        [/\bmarlboro\b/, [['white', '#f0f0f0']], [['red', '#d01818']]], [/\bcastrol\b/, [['white', '#f0f0f0']], [['green', '#1fa83a'], ['red', '#d01818']]], [/\bjagermeister|\bjager\b/, [['orange', '#ff7a00']], [['green', '#1fa83a']]], [/\brepsol\b/, [['orange', '#ff7a00']], [['red', '#d01818'], ['white', '#ffffff']]]];          // C-OFFVAGUE 2026-10-08: more named classic liveries paint at once (closest match)
    var KEEPCOL_RE = /\b(?:keep (?:the |my |all (?:the )?|every )?colou?rs?|same colou?rs?|keep (?:every|each) colou?r|colou?rs? (?:the same|as is|stay))\b/;
    var QUESTION_ANY = /\b(?:is it possible|any ?way to|wondering|would it look|do you think|is there (?:a|any)|what happens|what would|should i|would (?:a|it|that|this|the) \w+ ?look|could it|can it be|i wonder|is it ok|is it okay|does it matter|which one|which is)\b/;
    var TROUBLE_RE = /\b(?:keeps?|won'?t|doesn'?t|isn'?t (?:showing|working)|not (?:showing|working|loading|saving|appearing)|disappear\w*|vanish\w*|missing|broken|bug\w*|glitch\w*|after (?:i|the) (?:render|save|export|load)\w*|in (?:the )?(?:sim|iracing|game)|crash\w*|error)\b/;
    var COMPARE_RE = /\bchoices\b|\b(?:display|render|preview|show)(?: me)? (?:both|each|them both|the two|each one)\b|\bmock ?ups?\b|\bmock (?:it |them )?up\b|\bboth ways\b|\btwo (?:hoods?|roofs?|bonnets?|ways|cars|takes|variants?|choices)\b|\bone (?:in |with |as )?[a-z]+ and (?:the other|one)\b|\bshow me\b.*\bas\b.*\b(?:and|or)\b|\b(?:two versions|both versions|versions of|two looks|both looks|before (?:i )?decid\w*|to decide|see both|show (?:me )?both|let me see both|alongside|as well so i|show both|both options|two options|i will pick|i'll pick|i will choose|compare|comparing|side by side|next to|beside|so i can (?:choose|pick|compare|see|decide)|which (?:is|looks|one is) (?:better|nicer)|nicer|vs|versus|both options)\b/;
    var HOWTO_ANY = /[-,:;]\s*how\s*\??\s*$|\b(?:how(?:'s| is| are| was) (?:that|it|this|those|these) (?:done|made|achieved)|steps (?:for|to|needed)|what are the steps|how'?s it done|teach me|show me how|explain how|explain|how (?:can|do|would|should|to|could) (?:i|we|u|you|one)?|steps to|method|tutorial|walk me through|brainstorm|ideas? for|even though|why (?:is|does|did|do|are)|best way|tips|advice)\b/;
    var ACK_END = /\b(?:fine|good|ok|okay|perfect|readable|works|better|great|nice)\s*$/;
    var VIBE_RE = /\b(?:look(?:s|ing)? (?:aggressive|mean|cool|fast|sick|angry|tough|evil|clean|nice)|styled?|palette|vibes?|schemes? for|choose the colou?rs|pick (?:the |some )?colou?rs|something like|my own version|inspired|like a \w+$)\b/;
    var BARE_RE = /\b(?:the|my) (?:rear|back|front|bottom|lower|upper)\b(?! (?:bumper|side|wing|end|of|half|lid))/;
    var FIN_TGT = /\b(?:all (?:the|of the|my)|any|remove (?:the |all (?:the )?)?|take (?:the |all (?:the )?)?)\s*(?:chrome|candy|matte|metallic|pearl|gloss|flake|carbon)\b|\b(?:chrome|candy|metallic|pearl|carbon)\b[^.]{0,20}\b(?:off|anywhere|removed|gone)\b/;
    var CAP_RE = /\b(?:not|no) (?:any )?more \w+ than (?:that|this|now|it is)\b|\b(?:not|no|dont|don't|do not|never)\s+(?:go\s+|get\s+|make it\s+|any\s+)?\w+er\s+than\s+(?:that|this|now|it is)\b|\bmax(?:imum)? (?:shine|gloss|shiny|glossy)\b|\bthat'?s? (?:the )?(?:max|limit|most)\b/;          // V4-G: 'no shinier than that', 'max shine'
    var PROTECT_RE = /^\s*(?:make sure|ensure|dont let|don't let|be sure|double check|check that|check)\b.*\b(?:dont|don't|do not|not|never|stays?|keep|untouched|safe|no)\b/;
    var WHOLE_CUE = /\b(?:all|whole|entire|full|base|overall|everything|car|livery|paint ?job|scheme|truck|everywhere)\b/;
    var LIKE_RE = /\b(?:looks? like|look of|like (?:a|an|my|the|it|those|that)|style|inspired|themed?|vibe|feel)\b/;
    var UNPAINT_TXT = /\b(?:lights?|lenses|lens|headlights?|tail ?lights?|windows?|wheels?|rims?|tires?|tyres?|glass|windshield|wind ?screen|mirrors?|exhaust|interior|seats?)\b/;

    // V4-G 2026-10-07 harm classes (unit cases in _easy_claude_work/eval/v4f/test_offline_frame.js 'V4-G'):
    // H1 a state report / tag question is not an order ("the roof is #FFFFFF right now, right?", "chrome came out flat", "the doors look dull")
    var STATE_RE = /\b(?:all|everything|it|car|whole thing) (?:is |went |turned )?(?:grey|gray)\b[^?!]{0,30}\b(?:selected|picked|chose|chosen|set)\b|\b(?:selected|picked|chose|chosen)\b[^?!]{0,30}\b(?:grey|gray)\b|\b(?:works?|working|fine|ok|good|right|correct)\s+on\s+(?:the\s+)?\w+[^.?!]{0,30}\b(?:but|other|rest|everywhere else)\b|\b(?:came out|comes out|turned out|turned|went|ended up|end up|shows? up|showing(?: up)?|shows|reads?|looks?|looking|seems?|appears?|stays?|staying|remains?|is|are)\s+(?:all |kind of |kinda |really |very |so |just |still |now |totally )?(?:grey|gray|dull|flat|boring|wrong|weird|off|bad|washed out|muddy|mirrored|backwards|backward|flipped|reversed|upside down|blurry|pixelated|missing|gone|invisible|ugly|plain|lifeless|broken|transparent|see through|fine|great|good|right|ok|okay)\b/;
    var WANT_RE = /\b(?:should|needs?|has to|have to|must|want|wanna|would like|id like|i'd like|lets|let's|please|pls|too|enough|more|less|instead|make|paint|turn it|give|put|apply|use|add|swap|change|set|try|go with|i'll|ill take|why not|fix|redo|i said|i asked|wrong|but make)\b/;
    var MIDQ_RE = /[,.;]\s*(?:and |but |so )?(?:does|do|did|is|are|was|were|has|have)\s+(?:the|it|my|this|that|they|its|everything|he|she|there)\b|[,.;]\s*(?:and |but |so )?(?:does|do|did|is|are|was|were|has|have)\s+[^.!?]*\?\s*$|\b(?:right|correct|yeah|no)\s*\?\s*$|\b(?:isn'?t it|is it|doesn'?t it|does it|or not|aren'?t they)\s*\?\s*$/;
    var TECH_RE = /\b(?:gradient|fade|ombre|blend|zones?|layers?|mask|masking|template|decals?|spec ?map|import|export|upload|psd|tga)\b/;          // H2: a how-to about a technique
    // H2 a how-to thread: its follow-ups stay answers until the user hands the job over
    var HOWTO_PREV = /\bhow (?:do|can|would|should|to|could|does|did)\b|\bsteps (?:to|for)\b|\bwhat(?:'s|s| is) the (?:method|way|process|trick)\b|\bis there a way\b|\bwalk me through\b|\btutorial\b|\bhow\b[^.]*\?\s*$|^\s*(?:can|could) i\b(?! (?:get|have))/i;
    var HANDOVER_RE = /\b(?:for me|you do it|do it for|just do it|go ahead|can you (?:do|make|paint|put|set|apply)|could you (?:do|make|paint|put|set|apply)|apply it|paint it for|do that for)\b/;
    // H4 an option pick ("the second one", "option 2", "number two please") is an ordinal, never the numbers layer
    var PICK_RE = /^\s*(?:(?:ok|okay|yes|yeah|yep|um+|hmm+|i'?ll take|ill take|i'?ll go with|go with|use|lets go with|let'?s go with|let'?s do|lets do|i like|i want|gimme|give me|try|do|then|and|so)[\s,]+)*(?:the\s+)?(?:(?:option|number|no\.?|#|choice|idea|pick|scheme|version)\s*(?:one|two|three|four|five|six|[1-6])|(?:first|second|third|fourth|fifth|sixth|last|1st|2nd|3rd|4th|5th|6th|other|that|this|top|bottom)\s*(?:one|option|choice|idea|scheme|version|pick)?)(?:\s+(?:one|please|pls|then|option|looks? (?:best|good|great|nicer|better)|is (?:best|better|nicer|good)))*\s*[.!]*$/i;
    // H5 the numbers / logos named as kept ("NOT the numbers", "the numbers excluded", "leave the numbers be")
    var W3S_BE_OK = /\b(?:numbers?|logos?|sponsors?)\s+(?:should|must|need to|needs to|has to|have to|can|could|would|will|gonna|gotta|to)\s+be\s+(?:the |a |an )?(?:#[0-9a-f]{3,6}|red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|chrome|matte|gloss|[a-z]+ (?:red|blue|green|gold|black|white|orange|yellow))\b/;
    var NO_NUMS = /\b(?:spare|sparing|exception of|excepting|off ?limits|not touching|protect|protecting|preserve|preserving)\b[^.;]{0,22}\bnumbers?\b|\bnumbers?\b\s*(?:\w+\s+){0,2}(?:excepted|spared|off ?limits|protected|preserved)\b|\bnumbers?\s*[,:]?\s*(?:no|nope|not|none)\s*[.!]?\s*$|\b(?:not|no|never|skip|ignore|without|except|excluding|minus|leave|leaving|dont|don't|do not|hands off|other than|apart from|but not)\b[^.;]{0,22}\bnumbers?\b|\bnumbers?\b\s*(?:\w+\s+){0,2}(?:alone|untouched|excluded|unchanged|stays?|stay put|as is|as they are|out of (?:it|this)|intact|the same|be\b|left out|not included|skip(?:ped)?|ignored|remain)/;
    var NO_LOGOS = /\b(?:not|no|never|skip|ignore|without|except|excluding|minus|leave|leaving|dont|don't|do not|hands off|other than|apart from|but not)\b[^.;]{0,22}\b(?:logos?|sponsors?|decals?|stickers?)\b|\b(?:logos?|sponsors?|decals?|stickers?)\b\s*(?:\w+\s+){0,2}(?:alone|untouched|excluded|unchanged|stays?|stay put|as is|as they are|out of (?:it|this)|intact|the same|be\b|left out|not included|skip(?:ped)?|ignored|remain)/;
    // H6 a colour (or a finish) as the TARGET; when the frame could not build that target it asks, it never paints the whole body
    var CT_CUE = /\b(?:the|all the|all of the)\s+(?:red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon)\s+(?:(?:a (?:bit|little|touch)|slightly|much|way)\s+)?(?:redder|oranger|yellower|greener|bluer|darker|lighter|brighter|deeper|richer|warmer|cooler|more \w+|less \w+)\b|\b(?:the|all(?: of)?(?: the)?|every|any)\s+(?:#?[0-9a-f]{6}|red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon)\s+(?:should|to|into|toward|towards|becomes?|goes?|turns?|gets?|more|=|->)\b|\b(?:shift|move|push|nudge)\s+(?:the\s+)?(?:red|orange|yellow|green|blue|purple|pink)\s+(?:to|toward|towards|into)\b|\b(?:areas?|parts?|bits?|regions?|zones?|spots?|sections?|places?|pixels?|everything|anything|wherever|anywhere|whatever)\s+(?:that(?:'s| is| are|s)?|which (?:is|are)|currently|now|is|are)\s+(?:currently |now |still )?(?:#?[0-9a-f]{6}\b|red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon)|\b(?:currently|right now)\s+#?[0-9a-f]{6}\b|\b(?:the|all|every|any|only)\s+(?:the\s+)?(?:#?[0-9a-f]{6}|red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon)\s+(?:areas?|parts?|bits?|regions?|zones?|spots?|sections?|places?|stuff|paint)\b|\b(?:areas?|parts?|bits?|regions?|zones?)\s+(?:currently\s+)?(?:red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|#?[0-9a-f]{6})\b|\b(?:all|every|any) (?:the )?(?:reds|blues|greens|yellows|whites|blacks|oranges)\b/;
    var FIN_SWAP = /\b(chrome|candy|matte|metallic|pearl|gloss|glossy|satin|carbon|flake)\b[^.;]{0,14}\b(?:to|into|becomes?|->|for|with)\s+(?:a |an |the )?((?:satin |matte |gloss |brushed |dark |black |flat )?(?:chrome|candy|matte|metallic|pearl|gloss|satin|carbon|flake))\b/;
    // ------------------------------------------------------------------ the last change (references): two shapes are read
    function lastInfo(env) {
        var L = env && (env.planLast || env.last); if (!L) return null;
        var parts = [], kind = null, look = null;
        if (L.target) { kind = L.target.kind; parts = (L.target.parts || []).slice(); look = L.look || (L.op && L.op.look) || null; }
        else if (L.targets) { (L.targets || []).forEach(function (t) { if (t && t.kind === 'part' && t.part) parts.push(String(t.part).split('@')[0]); if (t && !kind) kind = t.kind; }); look = L.colour ? { colour: L.colour } : null; }
        return { parts: uniq(parts), kind: kind, look: look };
    }
    function hasLook(L) { return !!(L && (L.colour || L.colours || L.gradient || L.finish || L.pattern || L.scale != null || L.stroke || L.spec)); }

    // ------------------------------------------------------------------ lexing: slots in order + per-slot flags (negated, in an except tail, after "than")
    var SEP_RE = /\s(?:and|with|plus|then|but|also|while|so)\s/g;
    function lex(text, env) {
        var KN = W.SpbIntentKnn, raw0 = String(text || '').toLowerCase(), t1 = String(text || '');
        if (INTERJ.test(raw0)) t1 = t1.replace(INTERJ_STRIP, '');          // 'no, pearl' / 'nah spoiler' / 'no wait blue': an interjection, not a negation
        if (!OF_CFG('noHex')) t1 = t1.replace(/(^|[^#\w])([0-9a-fA-F]{6})\b/g, function (m0, a, h) { return /\d/.test(h) || /^([a-fA-F])\1{5}$/.test(h) ? a + '#' + h : m0; });          // V4-G: a bare hex ('roof FFFFFF', 'bonnet 0B3D91') is a colour
        var fx = fixText(KN.prep(w1Incl(t1))).replace(TWO_TOO, '$1 too'), nm = KN.norm(fx, env), f = nm.fixed, slots = (nm.slots || []).map(function (s) { return clone(s); });
        // finishes the colour pairs swallow ("pearl white", "gold chrome") and finish words the normaliser left as plain words
        FIN_EXTRA.forEach(function (fe) { var re = new RegExp(fe[0].source, 'g'), m; while ((m = re.exec(f))) { var at = m.index; if (!slots.some(function (s) { return s.t === 'FIN' && s.at <= at && s.end > at; }) && !slots.some(function (s) { return s.t === 'PAT' && s.at <= at && s.end > at; })) slots.push({ t: 'FIN', s: m[0], v: fe[1], cls: fe[1], at: at, end: at + m[0].length, extra: true }); } });
        if (!OF_CFG('noJ4f')) slots.slice().forEach(function (c) { if (c.t !== 'COL' || !c.s || c.s === c.v) return; FIN_EXTRA.some(function (fe) { if (!fe[0].test(String(c.s).toLowerCase()) || slots.some(function (q) { return q.t === 'FIN' && q.at < c.end && q.end > c.at; })) return false; slots.push({ t: 'FIN', s: c.s, v: fe[1], cls: fe[1], at: c.at, end: c.end, extra: true }); return true; }); });          // V4-G J4f: 'pearl white' keeps the pearl
        if (!OF_CFG('noJ4t') && GRAD_RE.test(f) && /\b(?:at|to|towards?|near|from|on) the (?:very )?top\b/.test(raw0) && !/\broof\b/.test(raw0)) slots = slots.filter(function (q) { return !(q.t === 'PART' && q.v === 'roof' || q.t === 'PART' && /^roof$/.test(String(q.s || ''))); });          // V4-G J4t: 'fading to nothing at the top' is the fade's direction
        if (/\bgold (?:chrome|leaf|flake|metal)/.test(f) && !slots.some(function (s) { return s.t === 'COL' && s.v === 'gold'; })) { var gi = f.indexOf('gold '); slots.push({ t: 'COL', s: 'gold', v: 'gold', fam: 'gold', at: gi, end: gi + 4 }); }
        // whole-car words as a pseudo target slot
        var bre = w9BodyRe(), bm; while ((bm = bre.exec(f))) { var b0 = bm.index; if (!slots.some(function (s) { return s.at <= b0 && s.end > b0; })) slots.push({ t: 'BODY', s: bm[0], at: b0, end: b0 + bm[0].length }); }
        var bc = /\b(?:car|truck|base)\b/g, bcm; while ((bcm = bc.exec(f))) { var c0 = bcm.index; if (slots.some(function (s) { return s.at <= c0 && s.end > c0; })) continue; if (slots.some(function (s) { return s.t === 'COL' && s.end <= c0 && c0 - s.end <= 2 && !slots.some(function (p) { return p.t === 'COL' && p !== s && p.end <= s.at && s.at - p.end <= 6; }); })) slots.push({ t: 'BODY', s: bcm[0], at: c0, end: c0 + bcm[0].length }); }          // V4-G: "white car, red nose" = the body is white
        if (env && w26TruckOn(env)) slots = w26BedSlots(f, slots);          // W26U 2026-10-10 (class 2): bed / tailgate / bed liner on a car map that has a bed
        slots.sort(function (a, b) { return a.at - b.at; });
        // dedupe overlapping (the normaliser's own slot wins)
        var out = []; slots.forEach(function (s) { if (out.some(function (o) { return s.at < o.end && s.end > o.at && !(o.t === 'FIN' && s.t === 'COL') && !(o.t === 'COL' && s.t === 'FIN'); })) return; out.push(s); });
        if (!OF_CFG('noJ3')) for (var oi = out.length - 2; oi >= 0; oi--) { var a1 = out[oi], b1 = out[oi + 1]; if (a1.t === 'COL' && !a1.hex && b1.t === 'COL' && b1.hex && b1.at - a1.end <= 3 && /^[\s(:=\-]*$/.test(f.slice(a1.end, b1.at))) { if (!b1.fam) b1.fam = a1.fam; out.splice(oi, 1); } }          // V4-G J3: 'charcoal #333333' = #333333
        // "tone the shine down", "dial the gloss back", "less glossy", "more metallic": a relative change, not a new finish
        var tre = /\b(?:tone|turn|knock|dial|bring|take)\s+(?:the\s+)?(shine|gloss|glossiness|metal\w*|flake|sparkle|colou?r|saturation|brightness)\s+(down|back|up)\b|\b(?:tone|turn|dial|knock) (down|up) the (shine|gloss|metal\w*|flake|sparkle)\b/g, tm;
        while ((tm = tre.exec(f))) { var tAt = tm.index; out = out.filter(function (s) { return !(s.at >= tAt && s.at < tAt + tm[0].length); }); out.push({ t: 'REL', v: ((tm[2] || tm[3]) === 'up' ? 'more ' : 'less ') + (tm[1] || tm[4]), at: tAt, end: tAt + tm[0].length }); }
        // "too bright", "too much, half", "nope too dark": the opposite tweak of the last change
        var TOO_MAP = [[/^(?:bright|light|pale|white|loud|neon)/, 'darker'], [/^(?:dark|deep|black)/, 'lighter'],             [/^(?:big|large|huge|chunky|coarse)/, 'smaller'], [/^(?:small|tiny|fine|busy)/, 'bigger'], [/^(?:thick|wide|fat)/, 'thinner'], [/^(?:thin|skinny|narrow)/, 'thicker'], [/^(?:much|strong|intense|heavy|crazy|sparkly|metallic|glittery)/, 'less']];
        var too2 = /\b(?:too|so|way too|kinda too|a bit too|bit too)\s+(\w+)/g, t2m;
        while ((t2m = too2.exec(f))) { var wd = t2m[1], hit2 = null; TOO_MAP.forEach(function (x) { if (!hit2 && x[0].test(wd)) hit2 = x[1]; }); if (!hit2 || !/\btoo\b/.test(t2m[0])) continue; var a2 = t2m.index; out = out.filter(function (s) { return !(s.at >= a2 && s.at < a2 + t2m[0].length); }); out.push({ t: 'REL', v: hit2 + (/\bhalf\b/.test(f) ? ' a little' : ''), at: a2, end: a2 + t2m[0].length, too: true }); }
        out.forEach(function (s) { if ((s.t === 'FIN' || s.t === 'COL') && /\b(less|more)\s+$/.test(f.slice(Math.max(0, s.at - 6), s.at))) { s.t = 'REL'; s.v = RegExp.$1 + ' ' + s.v; s.neg = null; } });
        out.sort(function (a, b) { return a.at - b.at; });
        if (!OF_CFG('noJ4g')) { var swm = /\b(?:reduce|less|lower|tone down|dial back|dial down|cut|drop)\s+(?:the\s+)?(chrome|gloss|candy|pearl|metallic|matte|satin)\b[^.;]{0,24}?\bmore\s+(chrome|metallic|pearl|candy|matte|satin|gloss)\b/.exec(f);          // V4-G J4g: 'reduce the chrome, more metallic' = metallic
            if (swm && swm[1] !== swm[2]) { var sw0 = swm.index, sw1 = swm.index + swm[0].length; out = out.filter(function (q) { return !((q.t === 'REL' || q.t === 'FIN') && q.at >= sw0 && q.at < sw1); }); out.push({ t: 'FIN', s: swm[2], v: swm[2], cls: swm[2], at: sw1 - swm[2].length, end: sw1, extra: true }); out.sort(function (x, y) { return x.at - y.at; }); } }
        var exc = EXC_RE.exec(f), excAt = exc ? exc.index : -1, excEnd = 1e9;
        if (exc && /^(?:keep|leave|leaving)$/.test(exc[0]) && !/\b(?:as (?:is|it is|they are)|alone|untouched|unchanged|the same|be)\b/.test(f.slice(excAt)) && !out.some(function (s) { return s.at < excAt && /^(COL|FIN|PAT|BODY)$/.test(s.t); })) { exc = null; excAt = -1; }          // 'keep the roof carbon' = a request, not an except
        if (exc) { var em = /\b(?:just|but (?:make|paint|do)|then|and make|make|paint|turn|go)\b/.exec(f.slice(excAt + exc[0].length)); if (em) excEnd = excAt + exc[0].length + em.index; }
        out.forEach(function (s) {
            var pre = f.slice(Math.max(0, s.at - 16), s.at);
            if (s.t === 'REL') return;
            if (/\b(?:not|no|never|less|without|instead of|rather than|than|from|isnt|is not|was)\s+(?:the |a |so |that |my |too )?(?:\w+ )?$/.test(pre) && !/\bnot (?:just|only)\s+(?:the )?$/.test(pre)) s.neg = /\b(?:than|from|was|is not|isnt)\s+(?:the |a |my )?(?:\w+ )?$/.test(pre) ? 'ref' : 'neg';
            if (s.neg === 'ref' && s.t === 'COL' && !OF_CFG('noJ4a') && GRAD_RE.test(f) && /\bfrom\s+(?:the |a |my )?(?:\w+ )?$/.test(pre) && /^\s*(?:\w+\s+)?(?:to|into|->)\s/.test(f.slice(s.end, s.end + 14))) delete s.neg;          // V4-G J4a: 'fade from black to red' = black is a stop
            if (excAt >= 0 && s.at > excAt && s.at < excEnd) s.exc = true;
            if (/\bstays?\s*$|\bwhich stays?\s+(?:our |the )?$|\bremains?\s+$|\b(?:stay|stick|keep going|stay put) with\s+(?:the )?$/.test(pre)) s.stays = true;
            if (/^(COL|FIN)$/.test(s.t) && /\b(?:wrong|not that|not this|not the|too|way too|so)\s+$/.test(pre)) s.neg = 'neg';          // "wrong blue", "TOO SHINY"          // "wrong blue, not that one"
            if (/^(PART|NUMS|SPON|LAYER|OBJ)$/.test(s.t) && /^\s*(?:not included|excluded|stay(?:s)? (?:as is|the same|untouched)|untouched|left alone|alone|as they are|as is|stays?(?: put)?\s*(?:as it is|as is|the same|untouched|alone)?\s*[.!]?\s*$|remains?\b|as it is|unchanged|intact|no\s*[.!]?\s*$)\b/.test(f.slice(s.end, s.end + 24))) s.exc = true;          // "numbers not included"
            if (/^(COL|FIN)$/.test(s.t) && !s.neg && /\b(?:is|are|still|looks?|was|were|its|it's)\s+(?:still |so |too |really |very |kinda |a bit )?$/.test(pre) && !/\b(?:it|this|that)\s+(?:is|looks)\s+$/.test(pre) && /\b(?:make|paint|turn|go|fix|change|want|use|do)\b/.test(f)) s.neg = 'ref';          // "the hood is still shiny" = the state now, not the ask
        });
        // a colour as the TARGET: "make the yellow purple", "the white in the Logos layer black", "swap the red to #E4002B", "every region currently #FF0000"
        var looks = out.filter(function (s) { return (s.t === 'COL' || s.t === 'FIN') && !s.neg; });
        out.forEach(function (s) {
            if (s.t !== 'COL' || s.neg || s.exc) return;
            var pre = f.slice(Math.max(0, s.at - 18), s.at), post = f.slice(s.end, s.end + 22);
            if (!/\b(?:the|all(?: the)?|every|any|those|currently|swap(?: the)?|replace(?: the)?|all of the)\s+$/.test(pre) || /\b(?:paint|make|turn|go|to|into|with)\s+(?:the |it )?$/.test(pre)) return;
            var nxt = out[out.indexOf(s) + 1], adj = nxt && (nxt.t === 'COL' || nxt.t === 'FIN') && nxt.at - s.end <= 2;
            if (!/^\s*(?:in|on|of|areas?|parts?|bits?|regions?|to|into|for|everywhere|stuff|sections?|bits?|panels?|paint)\b/.test(post) && !adj && !/\b(?:currently|that are|that is|which are|which is)\s+$/.test(pre)) return;
            if (!looks.some(function (o) { return o !== s; }) || GRAD_RE.test(f) || STRIPE_RE.test(f) || PIN_RE.test(f) || OUTL_RE.test(f)) return;
            if (/^\s*(?:hood|roof|trunk|spoiler|bumper|side|door|stripe|car|body|numbers?|logo)/.test(post)) return;          // "the red hood"
            if (/(?:^|[^a-z])all\s+$/.test(pre) && adj && nxt.t === 'FIN' && looks.filter(function (o) { return o.t === 'COL'; }).length === 1 && !out.some(function (o) { return /^(?:PART|NUMS|SPON|LAYER|OBJ)$/.test(o.t); })) return;          // IA1 2026-10-07 (train A-0227): "all black flat" = the whole car black + flat, not "make the black flat"
            s.ctarget = true;
        });
        // a layer named only as a SOURCE when a part is the target: "pull the blue from the Logos layer for the hood"
        var hasPart = out.some(function (s) { return s.t === 'PART'; });
        out.forEach(function (s, i) { if (s.t === 'LAYER' && hasPart && (/\b(?:from|see|sample|pull|match|like|as|copy|of our|use|grab|take)\b[^.]{0,14}$/.test(f.slice(Math.max(0, s.at - 22), s.at)) || (out[i + 1] && out[i + 1].t === 'COL' && out[i + 1].at - s.end <= 8))) s.src = true; });
        var seps = [], sm; SEP_RE.lastIndex = 0; while ((sm = SEP_RE.exec(f))) seps.push({ at: sm.index, w: sm[0].trim() });
        out.forEach(function (s) { s.chunk = seps.filter(function (x) { return x.at < s.at; }).length; });
        return { fixed: f, slots: out, seps: seps, fx: fx };
    }

    // ------------------------------------------------------------------ slots -> clause groups (one op each)
    function hasT(g) { return g.parts.length || g.layers.length || g.els.length || g.objs.length || g.body || g.ctarget; }
    function hasL(g) { return g.cols.length || g.fin || g.pat; }
    function usable(s) { return !(s.neg === 'neg' && s.t !== 'PART') && s.neg !== 'ref' && !s.stays && !s.src && !s.exc; }
    function isTs(s) { return s.ctarget || /^(PART|LAYER|NUMS|SPON|OBJ|BODY)$/.test(s.t); }
    function isLs(s) { return !s.ctarget && /^(COL|FIN|PAT)$/.test(s.t); }
    function groupsOf(L, keepParts, keepEls) {
        var G = [], cur = null, U = L.slots.filter(usable);
        function fresh(ch) { cur = { parts: [], cols: [], fins: [], fin: null, pat: null, layers: [], els: [], objs: [], rel: null, relAt: -1, body: false, ctarget: null, chunk: ch, at: 1e9, idx: G.length }; G.push(cur); }
        fresh(0);
        // the sentence's own order decides: TARGET-first ("hood red, roof white") starts a clause at each target after a look;
        // LOOK-first ("chrome spoiler and gold mirrors", "white body, black numbers") starts a clause at each look after a target
        var first = U.filter(function (s) { return isTs(s) || isLs(s); })[0], mode = first && isTs(first) ? 'TL' : 'LT';
        U.forEach(function (s) {
            var newChunk = s.chunk !== cur.chunk, isT = isTs(s), isL = isLs(s), sep = L.seps[s.chunk - 1];
            if (mode === 'TL') { if (isT && hasL(cur) && hasT(cur)) fresh(s.chunk); else if (isL && hasL(cur) && hasT(cur) && newChunk) fresh(s.chunk); }
            else { if (isL && hasT(cur) && hasL(cur)) fresh(s.chunk); }
            if (isL && newChunk && hasL(cur) && sep && sep.w === 'with') { fresh(s.chunk); cur.withOf = true; }
            cur.chunk = s.chunk; cur.at = Math.min(cur.at, s.at);
            if (s.ctarget) { if (!cur.ctarget) cur.ctarget = { word: s.v, hex: s.hex || hexOfWord(s.v) }; return; }
            if (s.t === 'PART') {
                var ps = (s.parts || []).filter(function (p) { return keepParts.indexOf(p) === -1; }); if (!ps.length) return;
                if (s.neg === 'neg') { cur.notParts = (cur.notParts || []).concat(ps); return; }
                ps.forEach(function (p) { if (cur.parts.indexOf(p) === -1) cur.parts.push(p); });
            } else if (s.t === 'BODY') cur.body = true;
            else if (s.t === 'COL') cur.cols.push({ word: s.v, hex: s.hex || hexOfWord(s.v), fam: s.fam, at: s.at });
            else if (s.t === 'FIN') { cur.fins.push(s); cur.fin = cur.fin || s; }
            else if (s.t === 'PAT') cur.pat = cur.pat || s;
            else if (s.t === 'LAYER') cur.layers.push(s.v);
            else if (s.t === 'NUMS' || s.t === 'SPON') { var e = s.t === 'NUMS' ? 'numbers' : 'sponsors'; if (keepEls.indexOf(e) === -1) cur.els.push(e); }
            else if (s.t === 'OBJ') cur.objs.push(s.v);
            else if (s.t === 'REL') { cur.rel = (cur.rel ? cur.rel + ' ' : '') + s.v; cur.relAt = s.end; }
        });
        // a target-only clause takes the look of the next clause ("hood and roof red"), else joins the clause before it ("camo on the trunk and the roof")
        for (var i = G.length - 2; i >= 0; i--) { var g = G[i], n = G[i + 1]; if (hasT(g) && !hasL(g) && !g.rel && (hasL(n) || n.rel) && !g.body) { merge(n, g); G.splice(i, 1); } }
        for (var j = 1; j < G.length; j++) { var a = G[j - 1], b = G[j]; if (hasT(b) && !hasL(b) && !b.rel && hasT(a) && (hasL(a) || a.rel)) { merge(a, b); G.splice(j, 1); j--; } }
        // a look-only clause after a clause with a target: the same target ("hood red, and matte" / "roof white and make it gloss")
        for (var k = 1; k < G.length; k++) { var c = G[k - 1], d = G[k]; if (!hasT(d) && (hasL(d) || d.rel) && hasT(c)) { if (!d.cols.length && !d.pat && d.fin && !c.fin) { c.fin = d.fin; c.fins = c.fins.concat(d.fins); G.splice(k, 1); k--; continue; } if (!d.cols.length && !d.fin && !d.pat && d.rel && !c.rel) { c.rel = d.rel; c.relAt = d.relAt; G.splice(k, 1); k--; continue; } } }
        // a look-only clause still without a target borrows the clause before it ("hood red with a black stripe", "spoiler white. white.")
        for (var q = 1; q < G.length; q++) { var pq = G[q - 1], gq = G[q]; if (!hasT(gq) && (hasL(gq) || gq.rel) && hasT(pq)) { ['parts', 'layers', 'els', 'objs'].forEach(function (kk) { gq[kk] = pq[kk].slice(); }); gq.body = pq.body; gq.ctarget = pq.ctarget; gq.borrowed = true; } }
        return G.filter(function (g) { return hasT(g) || hasL(g) || g.rel; });
    }
    function merge(into, g) { ['parts', 'layers', 'els', 'objs'].forEach(function (k) { into[k] = uniq(g[k].concat(into[k])); }); into.body = into.body || g.body; into.at = Math.min(into.at, g.at); }
    function relOf(rel, after, text) {
        var r = String(rel || ''), nx = String(after || '').slice(0, 24);
        var prop = /dark|light|bright|pale|deep|dull/.test(r) ? 'lightness' : /thin|thick|wid|narrow|skinn|fat/.test(r) ? 'width' : /fine|tight|coarse|loose|big|small|large/.test(r) ? 'scale' : /shin|gloss|flat|matt/.test(r) ? 'gloss' : /redder|bluer|greener|warm|cool/.test(r) ? 'hue' : /rich|vivid|satur|subtl|soft/.test(r) ? 'saturation' : null;
        var dir = /\b(?:less|lower|reduce|down)\b/.test(r) ? -1 : /dark|deep|thick|wid|fat|big|large|coarse|loose|shin|gloss|more|strong|bold|rich|redder|bluer|greener|warm/.test(r) ? 1 : -1;
        if (prop === 'gloss' && !OF_CFG('noW1m') && /\b(?:matt|matte|flat|flatter|dull|duller|satin)\w*/.test(r) && !/\b(?:gloss\w*|shin\w*)/.test(r)) dir = (/\b(?:less|lower|reduce|down)\b/.test(r) ? 1 : -1);          // W1-PARSE 2026-10-08: 'make the roof more matte' = LESS gloss (was +1 = shine:gloss, the opposite). Kill: SPB_OF_CFG.noW1m
        if (!prop) {          // "more shine", "less dark", "more red", "less metallic"
            if (/^\s*(?:shin|gloss|reflect|clear ?coat|wet)/.test(nx)) prop = 'gloss'; else if (/^\s*(?:metal|chrome|flake)/.test(nx)) prop = 'metal';
            else if (/^\s*(?:dark|black)/.test(nx)) { prop = 'lightness'; dir = -dir; } else if (/^\s*(?:light|bright|white)/.test(nx)) prop = 'lightness';
            else if (/^\s*(?:red|blue|green|yellow|orange|pink|purple|colou?r)/.test(nx)) prop = 'stops';
            else if (/^\s*(?:matte?|flat|dull)/.test(nx)) { prop = 'gloss'; dir = -dir; } else prop = 'strength';
        }
        if (prop === 'lightness' && /dull/.test(r) && !/dark|light|bright|pale|deep/.test(r) && !W.SPB_OF_NODULLGLOSS && !/\b(?:colou?rs?|shades?|tones?|hues?|tint|red|blue|green|yellow|orange|pink|purple|white|black|grey|gray|silver|gold)\b/.test(nx + ' ' + String(text || ''))) { prop = 'gloss'; dir = -1; }          // lane R3-EDIT-2 2026-10-07 item 3: 'make the wing duller' = less shine, not a darker colour (MCP probe i3 x08 brightness -15)
        if (prop === 'lightness' && /dark|deep/.test(r)) dir = -1; if (prop === 'lightness' && /light|bright|pale/.test(r)) dir = 1;
        var o = { prop: prop, dir: dir }; if (/\b(?:a (?:bit|little|touch|tad)|slightly|little|lil)\b/.test(r + ' ' + text)) o.amount = 'little'; if (/\b(?:a lot|way|much|super|lot)\b/.test(r)) o.amount = 'lot';
        return o;
    }

    function changeFrame(text, L, shape, env, F, prevF) {
        var IF = W.SpbIntentFrame, lo = String(text || '').toLowerCase(), f = L.fixed, sp = String(shape || ''), spv = sp.split(':')[0], spk = sp.split(':')[1] || '';
        var rd = null; try { rd = IF.read(L.fx, env); } catch (e) { rd = null; }
        var correction = INSTEAD_RE.test(f) || /\bnot (?:on )?the\b/.test(f);
        var keepParts = rd ? rd.keep.parts.slice() : [], keepEls = rd ? rd.keep.elements.slice() : [];
        if (correction && /\bnot (?:on )?the\b/.test(f)) keepParts = [];          // "the trunk not the hood" = a correction (retarget), not a keep
        var LI = lastInfo(env), hasLast = !!LI, too = TOO_RE.test(f);
        // "everything X except Y" = ONE op on the body with Y excepted (rule 20)
        var exM = /\b(everything|all over|whole car|entire car|the car|the body|body|whole thing|all)\b.*?\b(?:except(?: for)?|apart from|other than|besides|but not|without|excluding|minus|save for|but leave|but keep)\b(.*)$/.exec(f), exParts = [], exEls = [];
        if (exM) { exParts = IF.partsOf(exM[2]) || []; if (/\bnumbers?\b/.test(exM[2])) exEls.push('numbers'); if (/\b(?:sponsors?|logos?|decals?|stickers?)\b/.test(exM[2])) exEls.push('sponsors'); keepParts = uniq(keepParts.concat(exParts)); keepEls = uniq(keepEls.concat(exEls)); }
        var G = groupsOf(L, keepParts, keepEls), ops = [], rawPm = PAT_RAW.exec(lo), rawPat = rawPm ? rawPm[1] : null;
        if (rawPat && /^(?:mud|dirt|grim)/.test(rawPat) && (/\b(?:is|are|was|looks?|got|gets|getting|seems?)\s+(?:so |too |really |very |all |kinda )?(?:dirty|muddy|grimy)\b|\b(?:clean|remove|get rid of|wash|suggest\w*|ideas?|should i|what|how|which)\b|\bdirt (?:oval|track|car|racing|late|modified|series|bike)|\?\s*$/.test(lo) || !/\b(?:on|add|put|want|give|make|wanna|some|with|splatter)\b/.test(lo))) rawPat = null;          // V4-G G18: "the car is dirty" is no mud request
        // a bare side / end word after a change: "the right also", "rear too", "copy it to the right" (hood <-> trunk, front <-> rear bumper)
        if (hasLast && !G.some(hasT)) {
            var dm = /\b(right|left|rear|back|front)\b(?! (?:side|bumper|wing|end|of))/.exec(f);
            if (dm && dm[1] === 'back' && !OF_CFG('noJ0n') && /\b(?:pull|take|bring|go|put|dial|tone|roll|turn|scale|change|set|switch|knock|bring)(?:ing|s|ed)?\s+(?:it|that|them|this|things|everything)?\s*back\b/.test(f)) dm = null;          // V4-G J0n: "pull it back" is no side
            if (dm && /^(?:right|left)$/.test(dm[1]) && !OF_CFG('noJ0n') && new RegExp('\\b(?:not |the |a )' + dm[1] + ' (?!side|door|hand|half|panel|quarter|fender)(?:\\w+ )?(?:colou?r|shade|tone|one|green|red|blue|yellow|orange|purple|pink|white|black|grey|gray|silver|gold|brown|teal|way|choice|thing|size|amount)\\b').test(f)) dm = null;          // "not the right green" is no side
            var lp0 = (LI && LI.parts) || [], dw0 = dm && dm[1], Pn = !dm ? null : dw0 === 'right' ? 'right side' : dw0 === 'left' ? 'left side' : (dw0 === 'rear' || dw0 === 'back') ? 'rear bumper' : 'front bumper';
            if (dm && (/\b(?:too|also|as well|same|copy|put|do|now|and|then)\b/.test(f) || (!OF_CFG('noJ0n') && /\b(?:only|just)\b|\b(?:front|rear|back|left|right) one\b/.test(f) && lp0.length > 1 && lp0.indexOf(Pn) !== -1))) {          // V4-G J0n: "front only is carbon" after both bumpers = the front bumper
                var lp = LI.parts || [], dw = dm[1], P = /\b(?:only|just)\b|\b(?:front|rear|back|left|right) one\b/.test(f) && lp.indexOf(Pn) !== -1 ? [Pn] : dw === 'right' ? ['right side'] : dw === 'left' ? ['left side'] : (dw === 'rear' || dw === 'back') ? (lp.indexOf('hood') !== -1 ? ['trunk'] : ['rear bumper']) : (lp.indexOf('trunk') !== -1 ? ['hood'] : ['front bumper']);
                if (!G.length) G.push({ parts: [], cols: [], fins: [], fin: null, pat: null, layers: [], els: [], objs: [], rel: null, relAt: -1, body: false, ctarget: null, chunk: 0, at: 0 });
                G[0].parts = P;
            }
        }
        G.forEach(function (g) {
            var look = {}, T = null, verb = null, op = {}, parts = g.parts.filter(function (p) { return (g.notParts || []).indexOf(p) === -1; });
            if (/\btrunk lid\b|\bdeck lid\b/.test(f)) parts = parts.filter(function (p) { return p !== 'roof'; });
            if (!OF_CFG('noJ0n') && parts.length === 2 && parts.indexOf('front bumper') !== -1 && parts.indexOf('rear bumper') !== -1 && /\bbumper\b/.test(f) && !/\b(?:front|rear|back|both|bumpers|nose|tail)\b/.test(f) && LI && LI.parts.length) { if (LI.parts.some(function (p) { return /trunk|rear|spoiler/.test(p); })) parts = ['rear bumper']; else if (LI.parts.some(function (p) { return /hood|front/.test(p); })) parts = ['front bumper']; }          // V4-G J0n: "the bumper at the bottom" after the trunk = the rear one
            // objects that ARE parts (rule 3) / are not on the paint sheet
            var objs = []; g.objs.forEach(function (o) { var hit = null; OBJ_PART.forEach(function (x) { if (!hit && x[0].test(o)) hit = x[1]; }); if (hit) hit.forEach(function (p) { if (parts.indexOf(p) === -1) parts.push(p); }); else if (!UNPAINT_RE.test(o)) objs.push(o.replace(/s$/, '')); else g.unpaint = o; });
            if (g.layers.length) T = { kind: 'layer', layers: uniq(g.layers) };
            else if (parts.length) T = { kind: 'part', parts: parts };
            else if (g.els.length) T = { kind: 'element', element: g.els[0] };
            else if (objs.length) T = { kind: 'object', object: objs[0] };
            else if (g.body) T = { kind: 'body' };
            if (T && T.kind === 'object' && parts.length) T.parts = parts;
            var cols = g.cols.slice();
            if (g.ctarget) { T = { kind: 'colour', colour: { word: g.ctarget.word, hex: g.ctarget.hex } }; if (g.layers.length) T.layers = uniq(g.layers); }
            var cols = g.cols.slice(), nC = cols.length;
            // verb: the sentence's cues first (a stroke cue belongs to the clause it sits in), then the neighbours' skeleton
            var gi = G.indexOf(g), gEnd = gi < G.length - 1 ? G[gi + 1].at : 1e9, gBeg = gi > 0 ? g.at : -1;
            function owns(re) { var m = re.exec(f); if (!m) return false; if (G.length < 2) return true; return (m.index >= gBeg && m.index < gEnd) || (gi === G.length - 1 && m.index >= g.at); }
            function owns8(re) { var m = re.exec(lo); if (!m) return false; if (G.length < 2) return true; var pos = m.index / Math.max(1, lo.length) * f.length; return (pos >= gBeg && pos < gEnd) || (gi === G.length - 1 && pos >= g.at); }
            var r8 = null; try { r8 = r8Phrase(lo, owns8, cols); } catch (eR8) { r8 = null; }          // R8-FIN 2026-10-08: a finish PHRASE (rainbow chrome, glitter, colour shift ...) = one catalogue pick, every word kept
            if (r8) { if (r8.colour) { cols = [{ word: r8.colour.word, hex: r8.colour.hex, v: r8.colour.word }]; nC = 1; } else if (r8.dropCols) { cols = []; nC = 0; } if (r8.fin && r8.fin.key && g.pat && !/\b(?:pattern|print|camo|stripe)/.test(lo)) g.pat = null; }
            if (owns(GRAD_RE) && !g.rel) verb = 'gradient';
            else if (owns(PIN_RE) && !g.rel) verb = 'pinline';
            else if (owns(OUTL_RE) && !g.rel) verb = 'outline';
            else if (owns(STRIPE_RE) && !g.pat && !g.rel && (nC || !hasLast || !T)) verb = 'stripe';
            else if (T && T.kind === 'layer' && HIDE_RE.test(f) && !nC && !g.fin && !g.pat) verb = 'hide';
            else if (T && T.kind === 'layer' && SHOW_RE.test(f) && !nC && !g.fin && !g.pat) verb = 'show';
            else if (g.rel && !nC && !g.fin) verb = 'adjust';
            else if (nC) verb = 'recolour'; else if (g.pat) verb = 'pattern'; else if (g.fin || (r8 && r8.fin)) verb = 'refinish';
            else verb = /^(recolour|refinish|pattern|adjust|retarget|copy_look|restyle)$/.test(spv) ? spv : 'adjust';
            if (g.borrowed && (verb === 'stripe' || verb === 'pinline' || verb === 'outline') && T && T.kind === 'body') T = null;
            if (g.fins.length > 1 && /\b(?:for|to|into|instead|with)\b/.test(f)) g.fin = g.fins[g.fins.length - 1];          // "swap the candy for pearl"
            // look
            if (verb === 'gradient') { var stops = cols.map(function (c) { return c.hex || c.word; }); if (/\brainbow\b/.test(f)) stops = RAINBOW.slice(); if (!stops.length && /\bdark|black|shadow/.test(f)) stops = ['#0a0a0a']; if (stops.length === 1 || /\bclear\b|\binto the (?:paint|base|car)\b/.test(f)) stops.push('clear'); if (stops.length >= 2) { look.gradient = { stops: stops }; if (!OF_CFG('noJ4b') && cols.length && !/\brainbow\b/.test(f)) look.gradient.names = cols.map(function (c) { return c.word || c.v || c.hex; }); }          /* V4-G J4b: the fade's colour words */ AXIS.some(function (a) { if (a[0].test(f)) { look.gradient && (look.gradient.axis = a[1]); return true; } return false; }); }
            else if (nC > 1 && (verb === 'stripe' || verb === 'pinline' || verb === 'outline')) look.colours = cols.map(function (c) { return { word: c.word, hex: c.hex }; });
            else if (nC) look.colour = { word: cols[nC - 1 > 0 && /\b(?:instead|to|into|for)\b/.test(f) ? nC - 1 : 0].word, hex: cols[nC - 1 > 0 && /\b(?:instead|to|into|for)\b/.test(f) ? nC - 1 : 0].hex };
            if (r8 && r8.fin) { look.finish = clone(r8.fin); if (look.finish.key == null && look.finish.keep_colour !== false) look.finish.keep_colour = !nC && !g.pat; } else if (g.fin) look.finish = { family: g.fin.v, keep_colour: !nC && !g.pat };
            if (g.pat) { look.pattern = { concept: g.pat.cls === 'carbon' ? 'carbon fiber' : g.pat.v }; }
            if (rawPat && (g.pat || (G.length === 1 && !nC && !g.fin))) { look.pattern = /^forged/.test(rawPat) ? { concept: 'carbon fiber', style: 'forged' } : { concept: rawPat.replace(/ /g, '') === 'snakeskin' ? 'snakeskin' : /^animal/.test(rawPat) ? 'leopard' : /^(?:mud|dirt|grim)/.test(rawPat) ? 'mud' : rawPat }; /* V4-G G18: 'animal print' = Leopard; mud / dirt = Grunge Splatter (the model's resolveLooks alias) */ if (verb === 'adjust' && !g.rel) verb = 'pattern'; }
            if (verb === 'stripe' || verb === 'pinline' || verb === 'outline') { var st = {}; STROKE_W.some(function (x) { if (x[0].test(f)) { st.width = x[1]; return true; } return false; }); if (verb === 'pinline' && !st.width) st.width = 'thin'; var px = /\b(\d{1,2}) ?(?:px|pixels?)\b/.exec(lo); if (px) st.px = +px[1];
                var nn = /\b(two|twin|double|dual|2|three|triple|3)\s+(?:\w+\s+)?(?:stripes?|lines?|pin ?stripes?)\b/.exec(f); if (nn) st.n = /three|triple|3/.test(nn[1]) ? 3 : 2; var at = /\b(belt ?line|middle|cent(?:er|re)|bottom|rocker)\b/.exec(f); if (at) st.at = /belt/.test(at[1]) ? 'beltline' : at[1];
                if (Object.keys(st).length) look.stroke = st; }
            if (g.pat && /\bscale|crush|tight|small|big|\d+ ?%|\d ?x\b/.test(f)) { var pc = /\b(\d{2,3}) ?%/.exec(f), xm = /\b(\d(?:\.\d)?) ?x\b/.exec(f); if (pc) look.scale = +pc[1] / 100; else if (xm && /tight|small|crush|fine/.test(f)) look.scale = +(1 / +xm[1]).toFixed(3); else if (xm) look.scale = +xm[1]; else if (/crush/.test(f)) look.scale = 0.3; }
            op.verb = verb; op.look = look;
            if (g.rel && verb === 'adjust') op.relative = relOf(g.rel, f.slice(g.relAt), f);
            if (g.rel && g.pat && verb === 'adjust') op.relative.prop = 'scale';
            // IA1 2026-10-07 (train A-0105 'slap carbon on the hood, crushed small, like 3x tighter than default' = "Which texture should be finer?"): a NAMED pattern with its own size and no
            // pattern down from the last change = put that pattern down at that size (the 'tighter' is the size of the new pattern, not a tweak of an old one)
            if (!OF_CFG('noIA1') && verb === 'adjust' && op.relative && op.relative.prop === 'scale' && look.pattern && isFinite(look.scale) && !(hasLast && LI && LI.look && LI.look.pattern)) { verb = 'pattern'; op.verb = 'pattern'; delete op.relative; }
            if (g.rel && !nC && !T && /\bstripes?\b/.test(f) && /thin|thick|wid|narrow|slim|skinn|fat|big|small|bold/.test(g.rel)) { verb = 'adjust'; op.verb = 'adjust'; op.relative = { prop: 'width', dir: /thin|narrow|slim|skinn|small/.test(g.rel) ? -1 : 1 }; T = { kind: 'element', element: 'stripes' }; }
            if (!hasLast && op.verb === 'adjust' && op.relative && op.relative.prop === 'gloss' && op.relative.dir > 0) { op.verb = 'refinish'; op.look = look = { finish: { family: 'gloss', keep_colour: true } }; delete op.relative; }
            // target: named > whole-car > the last change (follow-up) > the skeleton
            if (!T) {
                if ((verb === 'stripe' || verb === 'pinline') && /\b(?:bottom|rocker|along the sides?|down the sides?)\b/.test(f)) T = { kind: 'part', parts: ['left side', 'right side'] };
                else if (TRIM_RE.test(f) || OBJ_RAW.test(f)) { /* an unknown / object noun is the target: leave it missing (the planner asks) */ }
                else if (gi === 0 && verb !== 'stripe' && verb !== 'pinline' && /\b(?:it all|all of it|all over|everything|whole thing|entire thing|all (?=black|white|red|blue|green|yellow|orange|purple|pink|grey|silver|gold|matte|chrome|gloss))\b/.test(f) && (nC || g.fin || g.pat)) T = { kind: 'body' };          // "make it all black w gold stripes"
                else if (!OF_CFG('noG25') && verb === 'pinline' && hasLast && /\bbetween\b/.test(f) && LI && LI.parts.length >= 2) T = { kind: 'graphic', between: [{ kind: 'part', parts: [LI.parts[0]] }, { kind: 'part', parts: [LI.parts[1]] }] };          // V4-G G25: "a thin pinline between them" = the seam of the last two parts
                else if (hasLast && !((verb === 'stripe' || verb === 'pinline') && LI && /^(element|layer|colour)$/.test(LI.kind || '') && !OF_CFG('noH12')) && !(!OF_CFG('noG25') && (verb === 'stripe' || verb === 'pinline') && !(LI && LI.kind === 'part'))) op.ref = { to: 'last_change' };          // v8: a look / tweak with no target after a change = the last change (online rule 15); V4-G H12: a NEW stripe after a numbers / logo change goes on the body, not on the numbers
                else if (verb === 'stripe' || verb === 'pinline') T = { kind: 'part', parts: ['hood', 'roof', 'trunk'] };          // rule 20e: stripes in a whole-car look run down the centre line
                else if (!hasLast && (!prevF || !(prevF.ops || []).some(function (o) { return o.target || hasLook(o.look); })) && (nC || g.pat || g.fin) && (!/\b(?:it|that|this|them|those|these)\b/.test(f) || /\b(?:it all|all of it|all over|everything|whole|entire)\b/.test(f) || KEEPCOL_RE.test(f)) && (WHOLE_CUE.test(f) || KEEPCOL_RE.test(f) || /\b(?:but keep|keep the|except)\b/.test(f) || nC + (g.fin ? 1 : 0) + (g.pat ? 1 : 0) >= 2 || spk === 'body') && !/\b(?:make|paint|do|turn|colou?r)\s+(?:the|my|our|his|a)\s+(?!car|truck|whole|entire|body|livery|paint)\w+/.test(f)) { T = { kind: 'body' }; op.defBody = true; }          // "all black, flat" with nothing before = the whole car; "make it chrome" with nothing before = ask
            }
            if (T && T.kind === 'body' && (verb === 'stripe' || verb === 'pinline')) T = { kind: 'part', parts: /\b(?:low|bottom|rocker|along the (?:body|sides?|car)|down the sides?)\b/.test(f) ? ['left side', 'right side'] : ['hood', 'roof', 'trunk'] };
            if (T) op.target = T;
            if (!OF_CFG('noG25') && op.ref && !T && op.relative && !Array.isArray(op.relative) && op.relative.prop === 'scale' && look.pattern && LI && !(LI.look && LI.look.pattern)) delete op.ref;          // V4-G G25: "carbon scale bigger" when the last change put no pattern down: the target is unknown (ask), never the last (body) change
            if (g.unpaint && !T && !hasLook(look)) op.unpaint = g.unpaint;
            // follow-ups on a named part: "and the roof", "roof same", "no, the trunk not the hood"
            if (T && (T.kind === 'part' || (!OF_CFG('noG13') && /^(?:element|object)$/.test(T.kind) && f.split(' ').length <= 6 && !/\b(?:is|are|was|were|did|does|do|check|chan+ged?|got|went|looks?|again|still|why|what|how|wtf|omg|my|stays?|untouched|alone|fine|keep|leave|unchanged|intact|remains?|safe)\b|[!?]|\bas (?:is|it is|they are)\b/.test(text.toLowerCase()))) && hasLast && !hasLook(look) && !g.rel) /* V4-G G13: also "now the sponsors" / "and the mirrors" / "the whole thing" */ { op.verb = (correction || spv === 'retarget') && !too ? 'retarget' : 'adjust'; op.ref = { to: 'last_change' }; }
            if (hasLast && OPP_RE.test(f) && !hasLook(look) && !g.rel) { delete op.target; op.ref = { to: 'opposite_side' }; op.verb = 'adjust'; }
            if (op.target && op.target.kind === 'body' && keepParts.length) op.except = [{ kind: 'part', parts: keepParts.slice() }];
            if (op.target && op.target.kind === 'body' && exM && exParts.length) op.except = [{ kind: 'part', parts: exParts.slice() }];
            ops.push(op);
        });
        var themeHit = null; THEMES.forEach(function (th) { if (!themeHit && (th[0].test(f) || (!w23Off('livery') && th[0].test(lo)))) themeHit = th; });          // W23U 2026-10-10: f is the LEXED text ('gulf' already read as 'light blue'), lo the buyer's own words
        var anyT = ops.some(function (o) { return (o.target && !o.defBody && o.target.kind !== 'body') || o.ref; }), cAll = []; G.forEach(function (g) { cAll = cAll.concat(g.cols); });
        if (themeHit && !anyT && (!cAll.length || w23ThemeOnly(lo, themeHit))) ops = [{ verb: 'recolour', target: { kind: 'body' }, look: { colour: { word: themeHit[1][0][0], hex: themeHit[1][0][1] } } }, { verb: 'stripe', target: { kind: 'part', parts: ['hood', 'roof', 'trunk'] }, look: themeHit[2].length > 1 ? { colours: themeHit[2].map(function (c) { return { word: c[0], hex: c[1] }; }) } : { colour: { word: themeHit[2][0][0], hex: themeHit[2][0][1] } } }];
        else if (!hasLast && !anyT && G.length === 1 && cAll.length === 2 && cAll[0].word !== cAll[1].word && !GRAD_RE.test(f) && !STRIPE_RE.test(f) && !PIN_RE.test(f) && !OUTL_RE.test(f) && !G[0].fin && !G[0].pat && !/\b(?:to|into|instead|from|swap|switch)\b/.test(f))          // 'yellow and black' = a body colour + stripes (online rule 20)
            ops = [{ verb: 'recolour', target: { kind: 'body' }, look: { colour: { word: cAll[0].word, hex: cAll[0].hex } } }, { verb: 'stripe', target: { kind: 'part', parts: ['hood', 'roof', 'trunk'] }, look: { colour: { word: cAll[1].word, hex: cAll[1].hex } } }];
        // copy / match: "right side should match the left", "put the checker from the roof on the trunk"
        var cm = /\b(?:match(?:es|ing)?|same (?:\w+ )?as|cop(?:y|ies|ying|ied)|mirror(?:s|ing)?|like|from)\s+(?:the |my |that on the )?((?:left|right|front|rear|back)(?: side| bumper)?|hood|roof|trunk|spoiler|sides?|bumpers?)\b/.exec(f);
        var cmE = /\b(?:match(?:es|ing)?|same (?:\w+ )?as|copy|look like|like|to)\s+(?:the |my |our )?(numbers?|logos?|sponsors?)(?: (?:colou?r|do|does|look))?\b/.exec(f);
        if (cmE && !cm && !ops.some(function (o) { return o.look && (o.look.colour || o.look.gradient || o.look.pattern || o.look.finish); })) { var tgt0 = null; ops.forEach(function (o) { if (!tgt0 && o.target && o.target.kind !== 'element') tgt0 = o.target; }); if (tgt0) ops = [{ verb: 'copy_look', target: tgt0, source: { kind: 'element', element: /^num/.test(cmE[1]) ? 'numbers' : 'sponsors' }, copy: ['colour', 'finish', 'spec'], look: {} }]; }
        if (cm && !ops.some(function (o) { return o.look && (o.look.colour || o.look.gradient); })) {
            var srcW = /^(left|right)$/.test(cm[1]) ? cm[1] + ' side' : cm[1], srcP = IF.partsOf(srcW) || []; var allP = []; G.forEach(function (g) { allP = allP.concat(g.parts); });
            var tgtP = allP.filter(function (p) { return srcP.indexOf(p) === -1; });
            if (srcP.length && tgtP.length) { var pat0 = null; ops.forEach(function (o) { if (o.look && o.look.pattern) pat0 = o.look.pattern; }); ops = [{ verb: 'copy_look', target: { kind: 'part', parts: uniq(tgtP) }, source: { kind: 'part', parts: srcP.slice(0, 1) }, copy: pat0 ? ['pattern', 'colour', 'finish', 'scale'] : ['colour', 'finish', 'pattern'], look: {} }]; }
        }
        // the same target twice: one op, the later look wins ("Hood is red. Make it yellow instead." / "the hood orange. ONLY the hood")
        var merged = [];
        ops.forEach(function (o) { var k = JSON.stringify(o.target || o.ref || null), prev = merged.filter(function (m) { return JSON.stringify(m.target || m.ref || null) === k && !o.source && !m.source; })[0];
            if (prev && (o.target || o.ref)) { Object.keys(o.look || {}).forEach(function (kk) { prev.look[kk] = o.look[kk]; }); if (prev.look.colour && /^(refinish)$/.test(prev.verb)) prev.verb = 'recolour'; if (o.relative) { prev.relative = o.relative; } if (o.verb !== 'adjust' && hasLook(o.look)) prev.verb = o.verb; if (prev.look.finish && prev.look.colour) prev.look.finish.keep_colour = false; } else merged.push(o); });
        ops = merged;
        // whole-car look + numbers / logos in the same breath = keep them (rule 20c); a logo as the only target = ask (never repaint sponsors on a guess)
        if (ops.some(function (o) { return o.target && (o.target.kind === 'body' || o.target.kind === 'part'); })) ops = ops.filter(function (o) { if (o.target && o.target.kind === 'element') { if (keepEls.indexOf(o.target.element) === -1) keepEls.push(o.target.element); return false; } return true; });
        var logoAsk = ops.some(function (o) { return o.target && o.target.kind === 'element' && o.target.element === 'sponsors' && hasLook(o.look) && (OF_CFG('noW15F_logo') || !(o.look && (o.look.colour || /\b(?:chrome|gloss(?:y)?|matte|satin|metallic|pearl|candy|carbon|mirror)\b/i.test(text))) || !/\b(?:sponsors?|logos?|decals?|brand(?:s|ings?)?)\b/i.test(text) || /\b(?:behind|backing|around|under|beneath|outline|glow|border|shadow|halo|panel|box|frame|background|pop|stand out|readable|legible|visible|rest of|part of|(?:in|inside|within|of)\s+(?:the|my|our)\s+(?:logos?|sponsors?|decals?))\b/i.test(text)); });          // W15F: sponsors / logos / decals + an explicit colour is an order (like numbers); only a look with no colour still asks
        // nothing typed: a pure follow-up ("do it", "the other side") or the turn before carries what is missing (an answer to an ask)
        if (!ops.length && hasLast) ops.push(OPP_RE.test(f) ? { verb: 'adjust', ref: { to: 'opposite_side' }, look: {} } : { verb: spv === 'retarget' ? 'retarget' : 'adjust', ref: { to: 'last_change' }, look: {} });
        if (prevF && prevF.act === 'change' && !hasLast) {
            var p0 = (prevF.ops || [])[0];
            if (!OF_CFG('noW15F_stripefu') && p0 && /^(?:stripe|pinline|outline)$/.test(p0.verb || '') && ops.length === 1 && !ops[0].target && !ops[0].ref && ops[0].verb === 'recolour' && ops[0].look && ops[0].look.colour) { var o2w = clone(p0); o2w.look = o2w.look || {}; delete o2w.look.colours; o2w.look.colour = ops[0].look.colour; ops[0] = o2w; F._usedPrev = true; }          // W15F: a bare colour right after a stripe / line / outline order is THAT graphic's colour (last-discussed element wins), never a recolour of the body parts it sat on
            else if (p0 && ops.length === 1 && !ops[0].target && !ops[0].ref && p0.target) { ops[0].target = clone(p0.target); F._usedPrev = true; }
            else if (p0 && ops.length === 1 && ops[0].target && !(ops[0].target.kind === 'element' && !OF_CFG('noH13')) && !hasLook(ops[0].look) && !ops[0].relative && hasLook(p0.look)) { ops[0].look = clone(p0.look); ops[0].verb = p0.verb; F._usedPrev = true; }
            else if (!OF_CFG('noG13') && p0 && ops.length === 1 && ops[0].target && ops[0].target.kind !== 'element' && !hasLook(ops[0].look) && !ops[0].relative && p0.relative && (!p0.target || p0.target.kind === 'body')) { ops[0].relative = clone(p0.relative); if (hasLook(p0.look)) ops[0].look = clone(p0.look); ops[0].verb = p0.verb; F._usedPrev = true; }          // V4-G G13: "make it more metallic" > "just the hood"
            else if (p0 && !ops.length && /^\s*(?:yes|yeah|yep|yup|ok|okay|sure|do it|go ahead|please|pls|go for it|that one)\b/.test(f) && f.split(' ').length <= 4) { ops = clone(prevF.ops); F._usedPrev = true; }
        }
        F.act = 'change'; F.ops = ops;
        if (themeHit && !w23Off('livery')) { var lv23 = w23LiveryTag(lo, themeHit, anyT); if (lv23) F.livery = lv23; }          // W23U 2026-10-10: a named classic livery is its own intent, the recipe executor reads F.livery
        F.keep = keepParts.map(function (p) { return { kind: 'part', parts: [p] }; }).concat(keepEls.map(function (e) { return { kind: 'element', element: e }; }));
        F.decals = rd ? rd.decals : 'protect';
        if (hasLast && correction && !too && ops.some(function (o) { return hasLook(o.look) && (o.ref || o.target); }) && !ops.some(function (o) { return o.verb === 'retarget'; })) F.replace_last = true;
        if (!F.replace_last && !OF_CFG('noJ7n') && !W.SPB_OF_NOJ7N && hasLast && LI && LI.kind === 'body' && !too && /\b(?:only|just)\b|\bnot (?:all|everything|the whole|the (?:whole |entire )?car|all over)\b/.test(f) && (correction || INSTEAD_RE.test(lo) || /\bnot (?:all|everything|the whole)\b/.test(f)) && ops.length && ops.every(function (o) { return o.target && o.target.kind === 'part' && (hasLook(o.look) || (o.ref && o.ref.to === 'last_change')); })) { F.replace_last = true; ops.forEach(function (o) { if (o.verb === 'retarget') o.verb = 'adjust'; }); }          // IA1 J7n 2026-10-07: 'no, not all, only the sides' after a whole-car change = undo it, paint the parts
        F.missing = [];
        if (!ops.length) F.missing = ['what'];
        ops.forEach(function (o) {
            if (!o.target && !o.ref) F.missing.push('target');
            if (!hasLook(o.look) && !o.relative && !o.ref && !/^(hide|show|copy_look|retarget)$/.test(o.verb)) F.missing.push('what');
        });
        if (logoAsk) { F.act = 'ask_back'; F.ops = []; F.missing = ['target']; }
        F.missing = uniq(F.missing);
        return F;
    }

    // ------------------------------------------------------------------ frameOf
    function nOfUndo(lo) { if (/\b(?:everything|all (?:of )?(?:it|them|that|the changes)|start over|from scratch|all the way)\b/.test(lo)) return 99; var m = /\b(twice|two|2|three|thrice|3|four|4|five|5)\b/.exec(lo); if (!m) return 1; return /twice|two|2/.test(m[1]) ? 2 : /three|thrice|3/.test(m[1]) ? 3 : /four|4/.test(m[1]) ? 4 : 5; }
    var PREV_CACHE = {};
    // V4-G 2026-10-07: experiment switches (SPB_OF_CFG = { noH1: 1, ... } on window; harness --cfg '{"of":{...}}'); all rules ON by default
    function OF_CFG(k) { var c = W.SPB_OF_CFG; return !!(c && c[k]); }
    var COLW_RE = /\b(red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|lime|cyan|magenta|brown|bronze|copper)s?\b/;
    var HEX6_RE = /#[0-9a-f]{6}\b|\b(?=[0-9a-f]*\d)[0-9a-f]{6}\b/;
    function colOf(txt) {          // the first hex / colour word in a piece of text -> {word, hex}
        var h = HEX6_RE.exec(txt), w = COLW_RE.exec(txt);
        if (h && (!w || h.index <= w.index)) { var hx = '#' + h[0].replace('#', ''); return { word: hx, hex: hx, at: h.index }; }
        if (w) { var wd = w[1] === 'gray' ? 'grey' : w[1]; return { word: wd, hex: hexOfWord(wd), at: w.index }; }
        return null;
    }
    // V4-G H5 / H6: the last checks on a change frame (harm nets: they only remove or narrow, never add a whole-car paint)
    function postNets(F, f, s, L, hasLastE) {
        var lo = String(s || '').toLowerCase();
        function bodyOp0() { return F.ops.some(function (o) { return o.target && o.target.kind === 'body'; }); }
        // V4-G G16: layer properties the planner already speaks (look.layer blend / opacity, relative hue / saturation / brightness):
        // "swap the blend on Car_Decal to screen", "set it to multiply" (after a layer change), "Base Color layer: hue -15"
        if (!OF_CFG('noG16') && (F.act === 'change' || F.act === 'ask_back')) {
            var lays = uniq(L.slots.filter(function (x) { return x.t === 'LAYER' && !x.neg && !x.exc && !x.src; }).map(function (x) { return x.v; }));
            var bm = /\b(multiply|screen|overlay|soft ?light|hard ?light|darken|lighten|difference|normal)\b/.exec(f), lb = /\bblend(?:ing)?\b|\bmode\b|\bset (?:it|that|them) to\b/.test(f) || (bm && lays.length);
            var om = /\bopacity\b[^.;\d]{0,12}(\d{1,3})\s*%?|(\d{1,3})\s*%?\s*(?:percent\s*)?opacity\b/.exec(f);
            var hm = /\b(hue|saturation|sat|brightness|lightness)\b\s*(?:by |to |of )?([+-]?\s?\d{1,3})\b/.exec(f);
            var lo2 = {}, rel = null;
            if (bm && lb && !(bm[1] === 'normal' && !/\bblend|mode\b/.test(f))) lo2.blend = bm[1].replace(/^(soft|hard) ?light$/, '$1-light');
            if (om) lo2.opacity = Math.max(0, Math.min(100, +(om[1] || om[2])));
            if (hm && (lays.length || hasLastE)) { var hv = +hm[2].replace(/\s/g, ''); rel = { prop: /^sat/.test(hm[1]) ? 'saturation' : hm[1] === 'hue' ? 'hue' : 'lightness', dir: hv < 0 ? -1 : 1, amount: Math.abs(hv) }; }
            if (!rel && /\b(?:drop|lower|less|reduce|cut|kill|remove|take down)\b[^.;]{0,14}\brough(?:ness)?\b|\bsmoother\b/.test(f)) rel = { prop: 'gloss', dir: 1 };
            else if (!rel && /\b(?:more|add|raise|increase|up)\b[^.;]{0,10}\brough(?:ness)?\b|\brougher\b/.test(f)) rel = { prop: 'gloss', dir: -1 };
            if ((lo2.blend || lo2.opacity != null || rel) && (lays.length || hasLastE)) {
                var op16 = { verb: 'adjust', look: {} }; if (lo2.blend || lo2.opacity != null) op16.look.layer = lo2; if (rel) op16.relative = rel;
                if (lays.length) op16.target = { kind: 'layer', layers: lays }; else op16.ref = { to: 'last_change' };
                F.act = 'change'; F.ops = [op16]; F.missing = []; return;
            }
        }
        // V4-G G17: part swaps: "swap the roof n hood colours", "change places the colour of the left door and the right door" = each part takes the other's look
        if (!OF_CFG('noG17') && F.act !== 'answer' && /\b(?:swap|switch|trade|exchange|change places|swop|flip)\b/.test(f) && !L.slots.some(function (x) { return x.t === 'COL' || x.t === 'FIN' || x.t === 'PAT' || x.t === 'LAYER' || x.t === 'NUMS' || x.t === 'SPON'; })) {
            var sp = []; L.slots.forEach(function (x) { if (x.t === 'PART' && !x.neg && !x.exc) (x.parts || []).forEach(function (p) { if (sp.indexOf(p) === -1) sp.push(p); }); });
            var lrOnly = sp.length === 2 && sp.indexOf('left side') !== -1 && sp.indexOf('right side') !== -1 && !/\b(?:left|right|driver|passenger)\b/.test(f);          // V4-G G28: "swap top and sides" = 'sides' is ONE word (no left/right swap)
            if (sp.length === 2 && !(lrOnly && !OF_CFG('noG28'))) { F.act = 'change'; F.missing = []; F.ops = [{ verb: 'copy_look', target: { kind: 'part', parts: [sp[0]] }, source: { kind: 'part', parts: [sp[1]] }, copy: ['colour', 'finish', 'pattern'] }, { verb: 'copy_look', target: { kind: 'part', parts: [sp[1]] }, source: { kind: 'part', parts: [sp[0]] }, copy: ['colour', 'finish', 'pattern'] }]; return; }
            if (lrOnly && !OF_CFG('noG28')) { F.act = 'ask_back'; F.ops = []; F.missing = ['what']; F.question = 'Swap which two parts? For example “swap the roof and the sides”.'; return; }
        }
        // V4-G G28 (real-grader traces, own wording): "scale up the roof only" = a size change; "match both doors to the bonnet" = the doors take the bonnet's look;
        // "wing sides orange" (sprint car) = the wing's side panels, never the car's sides
        if (!OF_CFG('noG28') && F.act === 'change') {
            var scm = /\b(?:scale|size)\s+(?:it\s+|that\s+|them\s+|this\s+)?(up|down)\b/.exec(f);
            if (scm) F.ops.forEach(function (o) { if (!o.relative && !(o.look && (o.look.colour || o.look.finish || o.look.gradient)) && o.verb !== 'copy_look') { o.relative = { prop: 'scale', dir: scm[1] === 'up' ? 1 : -1 }; o.verb = 'adjust'; } });
            var IFm = W.SpbIntentFrame, mt = /\bmatch(?:es|ing)?\s+(.{2,48}?)\s+(?:to|with)\s+(?:the\s+|my\s+)?(hood|roof|trunk|spoiler|front bumper|rear bumper|left side|right side)\b/.exec(f), mtT = mt && IFm && IFm.partsOf ? (IFm.partsOf(mt[1]) || []) : [];
            if (mt && mtT.length && mtT.indexOf(mt[2]) === -1 && !/\b(?:numbers?|logos?|sponsors?)\b/.test(mt[1])) { F.ops = [{ verb: 'copy_look', target: { kind: 'part', parts: mtT }, source: { kind: 'part', parts: [mt[2]] }, copy: ['colour', 'finish', 'pattern'], look: {} }]; F.missing = []; }
            var bo29 = F.ops.filter(function (o) { return o.target && o.target.kind === 'body' && o.look && (o.look.colour || o.look.finish || o.look.pattern); });          // V4-G G29: "whole car orange, the nose stays yellow" = the body op leaves out every part that gets its own look
            if (bo29.length === 1 && !OF_CFG('noG29')) { var own29 = []; F.ops.forEach(function (o) { if (o !== bo29[0] && o.target && o.target.kind === 'part' && o.look && (o.look.colour || o.look.finish || o.look.pattern)) (o.target.parts || []).forEach(function (p) { if (own29.indexOf(p) === -1) own29.push(p); }); });
                if (own29.length) { var ex29 = bo29[0].except || (bo29[0].except = []), pe = ex29.filter(function (x) { return x.kind === 'part'; })[0]; if (!pe) ex29.unshift(pe = { kind: 'part', parts: [] }); own29.forEach(function (p) { if (pe.parts.indexOf(p) === -1) pe.parts.push(p); }); } }
            var lsP = []; L.slots.forEach(function (x) { if (x.t === 'PART' && !x.neg && !x.exc) (x.parts || []).forEach(function (p) { if (lsP.indexOf(p) === -1) lsP.push(p); }); });
            if (lsP.length && /\b(?:from|found in|in|of|out of|off)\s+(?:my |the |our )?(?:\w+\s+)?(?:logos?|sponsors?|decals?)\b/.test(lo) && /\b(?:for|on|onto|to)\s+(?:the |my )?(?:\w+\s+)?(?:hood|bonnet|roof|top|trunk|boot|spoiler|wing|bumpers?|sides?|doors?)\b/.test(lo)) F.ops.forEach(function (o) { if (o.target && o.target.kind === 'layer' && o.look && o.look.colour) o.target = { kind: 'part', parts: lsP.slice() }; });          // "the blue in my logo (Logos layer) for the bonnet" = the bonnet, the logo is the colour's source
            if (/\b(?:wing|spoiler)\s+(?:sides?|side ?panels?|end ?plates?|left side and right side|left side)\b|\bsides? (?:of|on) (?:the |my )?(?:wing|spoiler)\b/.test(f + ' ' + lo)) F.ops.forEach(function (o) { var T = o.target; if (T && T.kind === 'part' && (T.parts || []).indexOf('spoiler') !== -1) T.parts = T.parts.filter(function (p) { return p !== 'left side' && p !== 'right side'; }); });
        }
        // V4-G G27 (dev class 3): a split livery "split the car in half, left #FFFFFF and right #0B3D91" = left side colour 1 + right side colour 2, or ask; never one colour on the whole body
        if (!OF_CFG('noG27') && F.act === 'change') {
            var spl = /\bhalf\b.*\bhalf\b|\b(?:split|in half|halves|half and half|two[- ]?tone|50 ?\/ ?50|each side|either side)\b/.test(f);
            var lm = /\b(?:left|driver'?s?)(?: side| half| hand side)?\b([^,;]*?)(?=,|;|\band\b|\bright\b|\bpassenger|$)/.exec(f), rm = /\b(?:right|passenger'?s?)(?: side| half| hand side)?\b([^,;]*?)(?=,|;|\band\b|\bleft\b|\bdriver|$)/.exec(f);
            var c1 = lm && colOf(lm[1]), c2 = rm && colOf(rm[1]);
            var sidesDone = F.ops.some(function (o) { return o.target && o.target.kind === 'part' && (o.target.parts || []).indexOf('left side') !== -1; }) && F.ops.some(function (o) { return o.target && o.target.kind === 'part' && (o.target.parts || []).indexOf('right side') !== -1; });
            if ((spl || (c1 && c2)) && !sidesDone && (bodyOp0() || spl)) {
                if (c1 && c2 && c1.hex !== c2.hex) { F.ops = [{ verb: 'recolour', target: { kind: 'part', parts: ['left side'] }, look: { colour: { word: c1.word, hex: c1.hex } } }, { verb: 'recolour', target: { kind: 'part', parts: ['right side'] }, look: { colour: { word: c2.word, hex: c2.hex } } }]; F.missing = []; return; }
                if (bodyOp0()) { F.act = 'ask_back'; F.ops = []; F.missing = ['what']; F._g = 1; return; }
            }
        }
        // V4-G G18: mud "near / on the bottom of the car" names no part: ask which parts (never the whole car)
        if (!OF_CFG('noG18') && F.act === 'change' && /\b(?:bottom|lower|low|below|under|underside|near)\b/.test(f) && F.ops.some(function (o) { return o.target && o.target.kind === 'body' && o.look && o.look.pattern && o.look.pattern.concept === 'mud'; })) { F.act = 'ask_back'; F.ops = []; F.missing = ['target']; F._g = 1; return; }
        // H5: the numbers / logos named as kept never become a target; they go on the keep list
        var w3sBe = !OF_CFG('noW3S') && !OF_CFG('noW3Sb') && W3S_BE_OK.test(f);          // W3-SCOPE 2026-10-09: 'the numbers should be green' is an order for the numbers, not 'numbers ... be left alone'
        var noN = !OF_CFG('noH5') && ((NO_NUMS.test(f) && !w3sBe) || DK4.n), noL = !OF_CFG('noH5') && ((NO_LOGOS.test(f) && !w3sBe) || DK4.l);
        if (noN || noL) {
            var hit = function (o) { var t = o.target; if (!t) return false; if (t.kind === 'element') return (noN && t.element === 'numbers') || (noL && t.element === 'sponsors'); if (t.kind === 'layer') return (t.layers || []).some(function (l) { return (noN && /number/i.test(l)) || (noL && /logo|sponsor|decal/i.test(l)); }); return false; };
            var named = F.ops.filter(hit).length, others = F.ops.filter(function (o) { return !hit(o); });
            if (named && others.length) F.ops = others;
            else if (named && noN !== noL) { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['target']; }
            var addK = function (el) { if (!(F.keep || []).some(function (k) { return k.kind === 'element' && k.element === el; })) F.keep.push({ kind: 'element', element: el }); };
            if (F.act === 'change') { if (noN && !F.ops.some(function (o) { return o.target && o.target.kind === 'element' && o.target.element === 'numbers'; })) addK('numbers'); if (noL && !F.ops.some(function (o) { return o.target && o.target.kind === 'element' && o.target.element === 'sponsors'; })) addK('sponsors'); }
        }
        // H5b: a colour on the numbers / logos while other colours in the sentence found no place (a scheme the frame only half read) = ask, never the decals alone
        if (F.act === 'change' && !OF_CFG('noH5')) {
            var used = JSON.stringify(F.ops.map(function (o) { return o.look || {}; })).toLowerCase(), unusedC = uniq(L.slots.filter(function (x) { return x.t === 'COL' && !x.neg && !x.exc && !x.src; }).map(function (x) { return String(x.v || '').toLowerCase(); })).filter(function (c) { return c && used.indexOf(c) === -1; });
            if (unusedC.length && F.ops.some(function (o) { return o.target && o.target.kind === 'element' && /^(numbers|sponsors)$/.test(o.target.element); })) { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['target']; return; }
        }
        // H5c: "remove / knock out the white" names the colour to take AWAY: painting that colour on is the opposite of the request: ask
        var rmv = /\b(?:remove|knock(?:ing)? (?:out|off)?|knock|delete|erase|get rid of|take out|take away|clear out|strip)\b[^.;]{0,20}?\b(red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold)\b/.exec(f);
        if (rmv && !OF_CFG('noH5') && F.ops.some(function (o) { return o.look && o.look.colour && o.look.colour.word === rmv[1] && !(o.target && o.target.kind === 'colour'); })) { F.act = 'ask_back'; F.ops = []; F.missing = ['what']; F._g = 1; return; }
        if (F.act !== 'change' || OF_CFG('noH6')) return;
        var bodyOp = F.ops.some(function (o) { return o.target && o.target.kind === 'body'; }), colT = F.ops.some(function (o) { return o.target && o.target.kind === 'colour'; });
        // H6: "every bit that is red now should go #E31837", "#FFD100 on the yellow areas only": a colour target, else ask; never the whole body
        var m = CT_CUE.exec(lo) || CT_CUE.exec(f), src = m && (m.input === lo ? lo : f);
        if (m && !colT && (bodyOp || F.ops.some(function (o) { return !o.target; }) || F.ops.some(function (o) { return o.verb === 'stripe'; }))) {
            var tc = colOf(m[0]), rest = src.slice(0, m.index) + ' ' + src.slice(m.index + m[0].length), nc = colOf(rest);
            if (nc && tc && nc.hex !== tc.hex && !/\b(?:to|into|become|becomes|go|turn|as|with|should be)\s+$/.test(src.slice(Math.max(0, m.index - 14), m.index) + (tc.at === 0 ? '' : ''))) {
                F.ops = [{ verb: 'recolour', target: { kind: 'colour', colour: { word: tc.word, hex: tc.hex } }, look: { colour: { word: nc.word, hex: nc.hex } } }]; F.missing = []; F.replace_last = false; delete F.replace_last;
            } else { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['what']; }
            return;
        }
        // H6b: "all chrome to satin chrome" (a finish as the target) with no part / last change: ask; the planner has no finish target
        var fs2 = FIN_SWAP.exec(f) || (OF_CFG('noG24') ? null : /\b(?:every|all|any)\b[^.;]{0,16}?\b(chrome|candy|matte|metallic|pearl|gloss|satin|carbon|flake)\b\s+(?:\w+\s+)?((?:satin|matte|gloss|brushed|dark|black|flat) (?:chrome|candy|metallic|pearl|carbon|flake))\b/.exec(f));          // V4-G G24: 'turn every bit of chrome satin chrome'
        if (fs2 && fs2[1].replace(/y$/, '') !== fs2[2] && bodyOp && !hasLastE && !L.slots.some(function (x) { return x.t === 'PART' || x.t === 'LAYER' || (x.t === 'BODY' && (OF_CFG('noG24') || !/\b(?:every\w*|all|any)\b/.test(f))); })) { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['what']; }
    }
    // V4-G round 3 J1 (2026-10-07; sealed harm classes, described by the coordinator; OWN paraphrase cases only): a text pre-pass that turns three shapes into the canonical
    // "paint the whole car <look> except the <parts>" / plain clauses BEFORE the clause reader (the clause reader read the negated list as the target):
    //   J1a inverted except: "don't touch the bonnet, the top or the numbers; paint all the rest charcoal" (a leading keep list + everything else / the rest / the remainder)
    //   J1b "paint everything except the hood and roof dark blue" (the look after the except list was lost)
    //   J1c typo'd leave-it clause in a multi-clause order: "hood candy blue. roof satin white. trunk laeve it" (leav / laeve / alon / dont tuch / as is) = a keep, never a target
    //   J1d boundary words are an extent, not a part: "black at the bottom to clear at the roofline" / "up to the beltline" never paints the roof
    // Returns null or { text, kind: 'invert' | 'leave' | 'extent', keep: [part words] }. Kill: SPB_OF_CFG.noJ1 (all), noJ1a / noJ1b / noJ1c / noJ1d.
    var P4W = '(?:hood|roof|trunk|deck ?lid|boot|spoiler|wing|front bumper|rear bumper|bumpers?|nose|tail|left side|right side|driver(?:\'?s)? side|passenger side|sides?|doors?|mirrors?|numbers?|sponsors?|logos?|decals?)';
    var P4G_RE = new RegExp('\\b' + P4W + '\\b', 'g');
    var REST4_RE = /\b(?:every ?thing else|everywhere else|all (?:of )?the rest(?: of (?:the car|it|the body|the truck))?|(?:the )?rest of (?:the car|it|the body|the truck)|the rest|the remainder(?: of (?:the car|it|the body))?|all else|anything else)\b/;
    var NEG4_RE = /\b(?:no (?:changes?|paint|work)|don'?t|dont|do not|never|leave|leaving|keep|keeping|not|without|except|apart from|other than|besides|but not|stays?|staying|alone|untouched|unchanged|as (?:is|it is|they are))\b/;
    var LOOK4_RE = /\b(?:chrome|matte|matt|satin|gloss|glossy|pearl|candy|metallic|carbon|flake|flat|brushed|charcoal|gunmetal|camo|gradient|fade)\b/;
    var KT4 = '(?:(?:l[ae]{1,2}a?ve?|leeve|leav)(?:\\s+(?:it|that|them|this|her))?(?:\\s+(?:alone|alon|alnoe|be|as\\s+is))?|(?:dont|don\'?t|do not|dnt|no)\\s+(?:touch|tuch|touc|tocuh|tuoch|change|paint)(?:\\s+(?:it|that|them))?|as\\s+(?:is|it is|they are)|stays?(?:\\s+(?:the same|as is|as it is))?|untouched|unchanged|alone|alon|no change|skip(?:\\s+it)?)';
    var KEEPC1_RE = new RegExp('^(?:and\\s+|but\\s+)?(?:the\\s+|my\\s+)?(' + P4W + ')\\s*[:=-]?\\s*' + KT4 + '$'), KEEPC2_RE = new RegExp('^(?:and\\s+|but\\s+)?(?:(?:l[ae]{1,2}a?ve?|leeve|leav)|(?:dont|don\'?t|do not|dnt)\\s+(?:touch|tuch|touc|tocuh|tuoch|change|paint))\\s+(?:the\\s+|my\\s+)?(' + P4W + ')(?:\\s+(?:alone|alon|alnoe|be|as\\s+is))?$');
    var COMPL4_RE = /\b(?:hard|tough|difficult|impossible|can'?t|cannot|cant|unable)\s+(?:to\s+)?(?:see|read|make out|spot|tell)\b|\blooks?\s+(?:a bit\s+|kinda\s+|really\s+|so\s+)?(?:off|wrong|weird|odd|bad|funny|strange|washed(?: out)?|muddy|awful|terrible|lost)\b|\bdoesn'?t look right\b|\b(?:went|turned|gone|came out|ended up)\s+\w+/;
    var BODYSTR4_RE = new RegExp('\\b(?:all|whole \\w+|entire \\w+|everything|body|car|it)\\s+(?:\\w+\\s+)?' + COLW_RE.source + '[^.;]*\\b(?:w|with|and|plus)\\b[^.;]*\\bstripes?');          // G32: 'make it all black w gold stripes' = body + stripes (owner rule 20), not a vague stripe
    function isLook4(t) { return COLW_RE.test(t) || HEX6_RE.test(t) || LOOK4_RE.test(t); }
    var DEC4_RE = /^(?:numbers?|sponsors?|logos?|decals?)$/;
    function list4(ps) { ps = ps.filter(function (p) { return !DEC4_RE.test(p); }); if (!ps.length) return ''; var u = []; ps.forEach(function (p) { if (u.indexOf(p) < 0) u.push(p); }); return u.length === 1 ? 'the ' + u[0] : u.slice(0, -1).map(function (p) { return 'the ' + p; }).join(', ') + ' and the ' + u[u.length - 1]; }
    // R4-READ 2026-10-08 R4d: a state clause naming the CURRENT colour before the order ("hood red now, i want yellow", "bonnet currently red, i want a switch to yellow", "the stripe is currently yellow, could it go white instead")
    // was read as the order (red, or both). Remove the state colour when a second colour follows an order marker. Kill: SPB_OF_CFG.noR4d.
    var COL_ALT = '(?:#[0-9a-f]{6}|red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|brown|maroon|navy|teal|cyan|magenta|violet|bronze|copper|beige|cream)';
    var ST_ORDER = /\b(?:i\s+want|i'?d\s+like|id\s+like|i\s+would\s+like|i\s+need|make\s+(?:it|that|them)|switch|change|turn|go|could\s+it|can\s+it|should\s+be|needs?\s+to\s+be|swap|instead|rather)\b/i;
    var ST_RE1 = new RegExp('(\\b(?:is\\s+)?(?:currently|right\\s+now|at\\s+the\\s+moment|at\\s+present|now)\\s+)(' + COL_ALT + ')\\b', 'i');
    var ST_RE2 = new RegExp('\\b(' + COL_ALT + ')(\\s+(?:right\\s+)?(?:now|currently|at\\s+the\\s+moment))\\b', 'i');
    var ST_COLTEST = new RegExp('\\b' + COL_ALT + '\\b', 'i');
    function stripStateColour(s) {
        var m = ST_RE1.exec(s), at = -1, len = 0;
        if (m) { at = m.index; len = m[0].length; } else if ((m = ST_RE2.exec(s))) { at = m.index; len = m[0].length; }
        if (at < 0) return s;
        var after = s.slice(at + len), before = s.slice(0, at);
        if (!ST_ORDER.test(after) || !ST_COLTEST.test(after)) return s;
        if (ST_COLTEST.test(before.replace(/^.*[.;!?]\s*/, ''))) return s;          // another colour before the state: not this shape
        return (before + ' ' + after).replace(/\s{2,}/g, ' ').replace(/\s+,/g, ',').trim();
    }
    // R4-READ 2026-10-08 R4a: a TRAILING keep clause about the numbers / logos ("... but my number has to stay white", "the number and the logos not change", "sponsor logos and the number boxes are not to be touched",
    // "numbers and sponsors need to stay readable", "decals and numbers exactly as they are") was read as a recolour OF those elements and then dropped by H5 = the whole sentence asked / painted the numbers.
    // Strip the clause, remember which elements are kept. Kill: SPB_OF_CFG.noR4a.
    var DK4 = { n: false, l: false };
    var DECAL_NP = '(?:(?:the|my|our|all|all the|all of the|every|all my)\\s+)*(?:(?:race|car|team|sponsor|driver)\\s+)?(?:numbers?(?:\\s+(?:boxes|box|panels?))?|logos?|sponsors?(?:\\s+logos?)?|decals?|stickers?)';
    var DK_RE = new RegExp('(?:^|[,;]\\s*|\\s+)(?:(?:but|and|while|though|also|plus|however|just|only|oh and|and also)\\s+)?((?:(?:white|black|red|blue|yellow|orange|green|silver|grey|gray|gold|pink|purple)\\s+)?' + DECAL_NP + '(?:\\s*(?:,|and|&|or|\\+)\\s*' + DECAL_NP + ')*)\\b([^.;!?]*)', 'gi');
    var DK_TAIL = /^\s*(?:(?:has|have|had|need|needs|must|should|gotta|got|will|shall)\s+(?:to\s+)?|are\s+(?:to\s+|not\s+to\s+be\s+)?|is\s+(?:to\s+|not\s+to\s+be\s+)?|can\s*not\s+|cannot\s+|can'?t\s+|do(?:es)?\s*n'?o?t\s+|dont\s+|not\s+to\s+be\s+)?(?:not\s+(?:to\s+)?(?:be\s+)?(?:change[ds]?|touch(?:ed)?|alter(?:ed)?|paint(?:ed)?|recolou?r(?:ed)?)|(?:stay|stays|remain|remains|staying)\b|(?:be\s+)?(?:left\s+alone|untouched|unchanged|kept|intact|protected|safe|excluded|exempt)|exactly\s+as\s+(?:they|it)\s+(?:are|is)|as\s+(?:they\s+are|is|it\s+is)\b|(?:change|chang|touch|alter)\w*\s*(?:,|im|i'?m|then|and)?\s*(?:im\s+done|i'?m\s+done)|stay\w*)/i;
    function stripDecalKeep(s) {
        if (!/\b(?:numbers?|logos?|sponsors?|decals?|stickers?)\b/i.test(s)) return null;
        var n = false, l = false, out = s, cut = false;
        out = s.replace(DK_RE, function (m0, np, tail) {
            if (!DK_TAIL.test(tail)) return m0;
            var low = String(np).toLowerCase(); if (/\bnumbers?\b/.test(low)) n = true; if (/\b(?:logos?|sponsors?|decals?|stickers?)\b/.test(low)) l = true; cut = true; return '';
        });
        if (!cut) return null;
        out = out.replace(/\s{2,}/g, ' ').replace(/[\s,;]+$/, '').trim();
        if (out.split(/\s+/).length < 2) return null;          // nothing left to read: leave the sentence alone
        return { text: out, n: n, l: l };
    }
    function pre4g(text) {
        if (OF_CFG('noJ1')) return null;
        var raw = String(text || ''), a = alias(raw.toLowerCase()).replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim(), m, out = null;
        // J1a
        if (!OF_CFG('noJ1a') && (m = REST4_RE.exec(a))) {
            var head = a.slice(0, m.index), tail = a.slice(m.index + m[0].length), hp = head.match(P4G_RE) || [];
            if (hp.length && NEG4_RE.test(head)) {
                var look = tail.replace(/^[\s,:=\-–]*(?:(?:in|to|as|with|gets?|goes|go|becomes?|is|are|=|:|-)\s+)?/, '').replace(/[.!]+\s*$/, '').replace(/\b(?:please|pls|thanks|thx)\b/g, '').trim();
                if (!look) { var hc = head.split(/[;,.:–]|\s-\s|\band\b/).pop(); look = hc.replace(/\b(?:paint|make|do|turn|colou?r|spray|wrap|go|on|for|to|in|the|then|but|please|pls)\b/g, ' ').replace(/\s+/g, ' ').trim(); }
                if (look && look.split(/\s+/).length <= 7 && isLook4(look) && !(look.match(P4G_RE) || []).length) out = { text: 'paint the whole car ' + look + (list4(hp) ? ' except ' + list4(hp) : ''), kind: 'invert', keep: hp };
            }
        }
        // J1b
        if (!out && !OF_CFG('noJ1b')) {
            var LB = new RegExp('^(?:(?:pls|please|can you|could you|now|ok|okay)\\s+)?(?:paint|make|do|colou?r|spray|turn|change|wrap)?\\s*(?:every ?thing|the whole (?:car|body|truck)|whole (?:car|body|truck)|all of it|the (?:car|body|truck)|all)\\s+(?:except(?: for)?|but|apart from|other than|besides|bar|minus|excluding)\\s+((?:(?:the|my)\\s+)?' + P4W + '(?:\\s*(?:,|and|or|&|\\+)\\s*(?:(?:the|my)\\s+)?' + P4W + ')*)\\s+(?:in\\s+|to\\s+)?(.+?)[.!]*$');
            if ((m = LB.exec(a)) && isLook4(m[2]) && !(m[2].match(P4G_RE) || []).length) { var bp = m[1].match(P4G_RE) || []; out = { text: 'paint the whole car ' + m[2].trim() + (list4(bp) ? ' except ' + list4(bp) : ''), kind: 'invert', keep: bp }; }
        }
        // J1c
        if (!out && !OF_CFG('noJ1c')) {
            var cls = a.split(/\s*[.;,!]+\s*/).filter(function (c) { return c.trim(); });
            if (cls.length >= 2) {
                var kp = [], rest = [];
                cls.forEach(function (c) { var k1 = KEEPC1_RE.exec(c.trim()) || KEEPC2_RE.exec(c.trim()); if (k1) kp.push(k1[1]); else rest.push(c.trim()); });
                if (kp.length && rest.length && rest.some(isLook4)) {
                    var bw = rest.some(function (c) { return /\b(?:whole car|whole body|the car|the body|everything|all of it|rest)\b/.test(c); });
                    out = { text: rest.join('. ') + (bw && list4(kp) ? ' except ' + list4(kp) : ''), kind: 'leave', keep: kp };
                }
            }
        }
        // J1e a complaint clause followed by an explicit fix ("the numbers are hard to read on black, make them white"): only the fix is the order (the complaint's colour is not a look)
        if (!out && !OF_CFG('noJ1e')) {
            var cs = a.split(/\s*(?:[.!?;]+|,)\s*(?=(?:so\s+|please\s+|pls\s+|just\s+|then\s+|can you\s+|could you\s+)?(?:make|paint|turn|change|set|put|give|go)\b)/);
            if (cs.length >= 2 && COMPL4_RE.test(cs[0]) && isLook4(cs.slice(1).join(' '))) {
                var sp = cs[0].match(P4G_RE) || [], fx = cs.slice(1).join('. ');
                if (sp.length && /\b(?:them|it|those|they)\b/.test(fx) && !(fx.match(P4G_RE) || []).length) fx = fx.replace(/\b(?:them|it|those|they)\b/, 'the ' + sp[0]);
                out = { text: fx, kind: 'fix', keep: [] };
            }
        }
        // J4e "put red on the hood and undo the roof": the undo / revert clause is not a paint target
        if (!out && !OF_CFG('noJ4e')) { var um = /\s*(?:,|\.|\band\b|\bthen\b)\s*(?:also\s+|then\s+)?(?:undo|revert|reset|take back|put back|change back)\s+(?:the\s+|my\s+)?([a-z' ]{3,24}?)(?:\s+(?:one|part|change|colou?r|back))?\s*[.!]?$/.exec(a); var uh = um ? a.slice(0, um.index).trim() : '';
            if (um && (um[1].match(P4G_RE) || []).length && uh && isLook4(uh) && (uh.match(P4G_RE) || []).length) out = { text: uh, kind: 'fix', keep: [] }; }
        // J1d (also on top of J1a-c); J1f "cab sides" / "sides of the cab" = the sides (the cab alone = roof + sides)
        if (!OF_CFG('noJ1d')) {
            var t0 = out ? out.text : raw, BND = /\s*\b(?:at|to|up to|until|till|right up to|all the way (?:up )?to|as far as|from|below|under|beneath)\s+(?:the\s+)?(?:roof ?line|belt ?line|window ?line|waist ?line|shoulder ?line|glass ?line|door ?line|character line|rocker(?: panels?)?|sills?)\b/gi;
            if (/\bcab (?:sides?|doors?)\b|\bsides? of (?:the |my )?cab\b/i.test(t0) && new RegExp(BND.source, 'i').test(t0)) { t0 = t0.replace(/\bcab (sides?|doors?)\b/gi, '$1').replace(/\b(sides?) of (?:the |my )?cab\b/gi, '$1'); out = { text: t0, kind: out ? out.kind : 'extent', keep: out ? out.keep : [] }; }
            if (BND.test(t0)) { BND.lastIndex = 0; var t1 = t0.replace(BND, '').replace(/\s+/g, ' ').trim(); if (t1 !== t0) out = { text: t1, kind: out ? out.kind : 'extent', keep: out ? out.keep : [] }; }
        }
        // W1-PARSE 2026-10-08: a colour WORD in front of its own hex ('our brand blue #0B3D91', 'blue #0B3D91') is the hex: the regex reader took the word for a colour to hunt on the car / painted the family blue instead of the exact hex. Kill: SPB_OF_CFG.noW1h.
        if (!OF_CFG('noW1h')) { var tw = out ? out.text : raw, tw2 = tw.replace(/\b(?:(?:our|the|my|a)\s+)?(?:(?:brand|team|primary|secondary|sponsor|company|main|official)\s+)?(?:colou?r\s+)?(?:red|orange|yellow|green|blue|purple|violet|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|lime|cyan|magenta|brown|bronze|copper|tan|cream|beige|turquoise|mint|olive|burgundy|crimson|charcoal|gunmetal|ivory|lavender)\s+(?=#[0-9a-f]{6}\b)/gi, ''); if (tw2 !== tw) out = { text: tw2, kind: out ? out.kind : 'fix', keep: out ? out.keep : [] }; }
        return out;
    }
    // W21H-BEGIN 2026-10-09 (lane W21-HOOKS; report: _easy_claude_work/eval/w21hooks/PROGRESS.md). HOOK_PROPOSAL hooks that live in the frame, in value order. ONE kill switch:
    // window.SPB_W21H_OFF = true (node: env SPB_W21H_OFF=1 where `process` exists), SPB_OF_CFG.noW21H, localStorage SPB_W21H_OFF = '1'; one hook off: SPB_OF_CFG.noW21H_<key>.
    function w21Off(sub) {
        var ls = false, pe = false;
        try { ls = typeof localStorage !== 'undefined' && localStorage.getItem('SPB_W21H_OFF') === '1'; } catch (e) { ls = false; }
        try { pe = typeof process !== 'undefined' && !!(process && process.env && process.env.SPB_W21H_OFF && process.env.SPB_W21H_OFF !== '0'); } catch (e2) { pe = false; }
        return !!(W.SPB_W21H_OFF || pe || OF_CFG('noW21H') || ls || (sub && OF_CFG('noW21H_' + sub)));
    }
    // ---- F_reply (hook 1; hold probe harm 33 -> see PROGRESS): a reply to the helper's own question about an UNFINISHED graphic order carries that order.
    //   "stripe would be nice" (helper asks where) > "deck lid, pink" = a pink stripe on the trunk, never a pink trunk;  "hood fade vibes" (helper asks which colours) > "blue to burnt orange" =
    //   a hood fade, never a body recolour + stripes. The reply is rewritten into the explicit order ("add a stripe. deck lid, pink") BEFORE the neighbours read it, so every later rule sees a
    //   complete order. Only when the turn before is an unfinished stripe (no place named) or fade (fewer than 2 colours), and the reply names a part (stripe) / 2+ colours (fade) and no graphic word.
    // the planner passes the convo store's turns; when the text it hands the frame was normalised (thx -> thanks, blu -> blue) its own raw turn is NOT popped, so prevTurns ends with the CURRENT turn: skip trailing turns that are the current one
    function w21Toks(t) { return String(t == null ? '' : t).toLowerCase().replace(/[^a-z0-9#' ]+/g, ' ').split(/\s+/).filter(Boolean); }
    function w21Same(a, b) { var A = w21Toks(a), B = w21Toks(b); if (!A.length || !B.length) return false; var seen = {}, i, n = 0; for (i = 0; i < B.length; i++) seen[B[i]] = 1; for (i = 0; i < A.length; i++) if (seen[A[i]]) n++; return n / Math.max(A.length, B.length) >= 0.5; }
    function w21IsSelf(raw, cur) { return w21Same(raw, cur) || w21Same(w21Pre(raw), cur); }
    function w21DropSelf(prevs, cur) {
        var out = prevs.slice(), self = null;
        try { var CVx = W.SpbConvo, tt = CVx && typeof CVx.turns === 'function' ? CVx.turns() : null; if (tt && tt.length) self = String((tt[tt.length - 1] && tt[tt.length - 1].said) || ''); } catch (e) { self = null; }
        while (out.length && self && out[out.length - 1] === self && out[out.length - 1] !== cur && w21IsSelf(out[out.length - 1], cur)) out.pop();
        return out;
    }
    function w21Prev(prevs, cur) { var i = prevs.length - 1; while (i >= 0 && w21IsSelf(prevs[i], cur)) i--; return i >= 0 ? prevs[i] : null; }
    var W21_GFX = /\b(pin ?stripes?|pinlines?|racing stripes?|rally stripes?|stripes?|bands?)\b/i, W21_FADE = /\b(?:fade[sd]?|fading|gradient|ombre)\b/i;
    var W21_NOREPLY = /\b(?:instead|actually|forget|never ?mind|scratch that|cancel|undo|revert|nah|nope|not|don'?t|dont|no)\b/i;
    var W21_PLACEW = /\b(?:middle|cent(?:re|er)|down the|along (?:the|each|both|its)|across|over the top|between|sides?|bottom|rockers?|belt ?line|nose to tail|front to back)\b/i;
    var W21_WHOLE = /\b(?:whole|entire|everything|all over|all of it|all of the car|every ?where)\b/i;
    var W21_UNHAPPY = /\b(?:not (?:a fan|happy|satisfied|pleased|thrilled|keen|crazy|loving|into|sold)|(?:don'?t|do not|dont) (?:really |quite )?(?:love|like|care for|enjoy)|hate|dislike|terrible|awful|horrible|ugly|lame|stale|blah|underwhelming|unhappy|off|meh|boring|plain|bland|dull|flat|ugly|bad|wrong|weird|odd|tired|dated|drab|lacking|not (?:quite |so |really |very )?(?:right|nice|great|good|working|feeling|me)|(?:doesn'?t|does not|don'?t|do not) (?:quite |really )?(?:feel|look|work|suit)|needs? (?:something|work|a change|help|love|colou?r)|something (?:different|else|new)|could use|time for)\b/i;
    var W21_LOOKLESS = /\b(?:paint|recolou?r|re-?colou?r|colou?r|change|redo|repaint|respray|switch|update|restyle|fix|refresh)\b/i;
    function w21Pre(t) {          // the same spelling / abbreviation pre-pass the current turn got (mk, frnt bmpr, blu, pnk)
        var x = String(t == null ? '' : t);
        try { x = w9Abbr(x); var SM = W.SpbIntentModel; if (SM && typeof SM.clean === 'function' && W.SPB_OF_CLEAN !== '0') { var cl = SM.clean(x); if (cl && cl.text && (cl.fixes || []).length && cl.fixes.every(function (fx) { return !STOP[String(fx[0]).toLowerCase()]; })) x = cl.text; } } catch (e) { /* raw */ }
        return x;
    }
    function w21Reply(s, prev, env) {
        if (w21Off('reply') || !prev || typeof s !== 'string') return null;
        var IF = W.SpbIntentFrame; if (!IF) return null;
        var pv = w21Words(w21Pre(prev)).replace(/\bback\s+(bumpers?)\b/gi, 'rear $1'), cur = String(s);
        if (cur.length > 400 || pv.length > 700 || /\?/.test(cur) || W21_NOREPLY.test(cur) || Q_START.test(cur.trim()) || W21_GFX.test(cur)) return null;
        if (Q_START.test(pv.trim()) || /\b(?:how|tutorial|explain|steps?)\b/i.test(pv)) return null;          // a question about the app is not an unfinished order
        var fadeP = W21_FADE.test(pv), gm = fadeP ? null : W21_GFX.exec(pv);
        if (!fadeP && W21_FADE.test(cur)) return null;          // a stripe pending but the reply talks about a fade: not this reply
        var pParts = []; try { pParts = IF.partsOf(pv) || []; } catch (e) { pParts = []; }
        var Lc, Lp; try { Lc = lex(cur, env); Lp = lex(pv, env); } catch (e2) { return null; }
        var cs = Lc.slots.filter(function (x) { return !x.neg && !x.exc; }), ps = Lp.slots.filter(function (x) { return !x.neg && !x.exc; });
        var pPartS = ps.filter(function (x) { return x.t === 'PART' && x.s; }).map(function (x) { var sv = String(x.s).toLowerCase(), o; for (var oi = 0; oi < OBJ_PART.length; oi++) { o = OBJ_PART[oi]; if (o[0].test(sv) && o[1].length === 1) return o[1][0]; } return sv; });          // nose > front bumper (the planner's own word map)
        var cCols = cs.filter(function (x) { return x.t === 'COL'; }).length, pCols = ps.filter(function (x) { return x.t === 'COL'; }).length, cPart = cs.some(function (x) { return x.t === 'PART'; });
        if (fadeP) {
            if (pCols >= 2 || cCols < 2) return null;          // the fade already has its colours / the reply gives none
            var place = cPart ? '' : (pParts.length ? ' on the ' + pParts.join(' and the ') : (pPartS.length && pPartS.length <= 2 ? ' on the ' + pPartS.join(' and the ') : ''));
            return 'add a fade' + place + ': ' + cur;
        }
        if (!gm) {          // (c) no graphic: a part complaint / a 'paint the roof' with no look, then the colour / finish alone: "back bumper feels meh" > "royal blue, yep" = paint the rear bumper royal blue (F_reply, hold 0133 / 0109 / 0067 / 0016)
            if (w21Off('replypart') || !pParts.length || pParts.length > 2 || ps.some(function (x) { return /^(COL|FIN|PAT)$/.test(x.t); }) || !cs.some(function (x) { return /^(COL|FIN|PAT)$/.test(x.t); }) || cPart || W21_WHOLE.test(cur)) return null;
            if (!(W21_UNHAPPY.test(pv) || W21_LOOKLESS.test(pv))) return null;
            return 'paint the ' + pParts.join(' and the ') + ': ' + cur;
        }
        if (pParts.length || pPartS.length || W21_PLACEW.test(pv) || !cPart) return null;          // the stripe order already has a place (the old bare-colour follow-up handles it) / the reply names no place
        var noun = String(gm[1]).toLowerCase().replace(/^bands?$/, 'stripe').replace(/s$/, '');
        return 'add a ' + noun + '. ' + cur;
    }
    // ---- SA_polite (hook 2; hold SA_polite 196 turns 91.8% -> see PROGRESS; kill SPB_OF_CFG.noW21H_polite): a polite or tagged ORDER is an order. "trunk holo, ok?" / "Hood holo, any chance?" / "You make wing teal, is ok?" (tag question after a complete order),
    //   "Would you mind painting the rear wing navy, is that ok?", "Is okay if we make roof panel blue?", "Would it be okay if roof made holographic?", "so I was wondering if you could make the back bumper holo" (a polite lead anywhere in the message).
    //   The tag / lead is cut and the plain imperative goes on to the readers. Fires only when what is left is a paint order with something concrete in it and nothing of a real question (how / why / what / which / should / can I / does it look).
    var W21_TAGQ = /(?:[\s,;.!-]+(?:(?:is|was|would|will|that|it)(?:'?s)?\s+(?:that\s+|it\s+|this\s+)?(?:be\s+)?(?:ok|okay|alright|all right|fine|cool|possible)|ok|okay|alright|all right|cool|(?:any|got a|is there (?:any|a)) chance|yeah|yep|right|eh|deal|(?:can|could|will|would) (?:you|u)|you can|possible)\s*\?+)+(?:[\s,.!-]*(?:thanks|thank you|thx|cheers|ta|pls|please)(?:\s+(?:so much|a lot|very much|in advance|mate|man))?)*[\s.!?]*$/i;
    var W21_PLEADS = [
        /(?:^|[.!;,]\s*|\bso\s+)(?:(?:hi|hey|hello|ok|okay|so|well|and|now)\b[\s,!.:;-]*)*(?:would|do|did)\s+(?:you|u)\s+mind\s+(?:if\s+(?:we|i|you)\s+)?/i,
        /(?:^|[.!;,]\s*|\bso\s+)(?:(?:hi|hey|hello|ok|okay|so|well|and|now)\b[\s,!.:;-]*)*(?:would|will|could|can)\s+(?:it|that)\s+be\s+(?:ok|okay|alright|fine|possible|cool)\s+(?:if|to|that|for)\s+(?:(?:we|you|i|u)\s+)?/i,
        /(?:^|[.!;,]\s*|\bso\s+)(?:(?:hi|hey|hello|ok|okay|so|well|and|now)\b[\s,!.:;-]*)*(?:is|was)\s+(?:it\s+|that\s+)?(?:(?:ok|okay|alright|fine|cool)\s+(?:if|to|that|for)|possible\s+(?:if|that|for))\s+(?:(?:we|you|i|u)\s+)?/i,
        /(?:^|[.!;,]\s*|\bso\s+)(?:(?:hi|hey|hello|ok|okay|so|well|and|now)\b[\s,!.:;-]*)*(?:is|would be)\s+(?:it\s+)?(?:ok|okay|possible|alright|fine)\s+(?:if\s+|that\s+)?(?:you|we|u)\s+/i,
        /(?:^|[.!;,]\s*|\bso\s+)(?:i\s+(?:was\s+)?(?:wondering|hoping|thinking)\s+(?:if\s+)?(?:you\s+)?(?:could|can|would)\s+(?:you\s+)?)/i
    ];
    var W21_QWORD = /\b(?:how|why|what|which|whether|should i|can i|could i|may i|do you think|would (?:it|that|this) look|does (?:it|that|this)|is it (?:ok|okay|possible)|looks?|better|nicer|suits?|works?|good idea)\b/i;
    var W21_CFIXV = /(?:^|[,;.!?:-]\s*|\b(?:lol|lmao|haha|af|and|so|then|just|you|u)\s+)(?:(?:you|u|just|please|pls)\s+)*(?:make|mk|fix|sort|repair|redo|paint|turn|change|set|switch|recolou?r|put|give)\s+(?:it|this|that|them|em|the\s+\w+(?:\s+\w+)?)\b/;
    var W21_EXPL = /\b(?:semi[- ]?gloss\w*|satin|matte?|chrome|carbon|candy|pearl\w*|metallic|holo\w*|brushed|camo\w*|mirror|red|orange|yellow|gold|green|lime|teal|cyan|blue|navy|cobalt|purple|violet|lilac|indigo|pink|magenta|white|silver|gr[ae]y|black|brown|maroon|burgundy|crimson|scarlet|bronze|copper|cream|beige|charcoal|turquoise|mustard)\b|#[0-9a-f]{3,6}\b/i;
    function w21ExplicitTail(m) {          // the order half of "<part> too dull, <verb> ... <look>" names a colour / a finish that is not just "more gloss"
        if (w21Off('complaint')) return false;
        var o = /\b(?:bump|crank|push|dial|turn|bring|take|make|boost|give|add|get|fix|sort|raise|lift|increase|up)\b([\s\S]*)$/i.exec(String(m || ''));
        return !!(o && W21_EXPL.test(o[1]));
    }
    // ---- W21H SA_polite R2 2026-10-09 (hidden-set over-firing, kill noW21H_polite): a tag question ("right?", "ok?", "yeah?") turned a how-to question into an order ("gotta put a number on it, right?" > "put a number on it").
    //   A tag makes an order ONLY when the rest is a concrete order: a named part / element AND a paint value (a colour, finish, pattern or effect word, or the lexer's COL / FIN / PAT slot, which tolerates typos). "a number thing", "some digits", "a logo" have no value: the question path keeps them.
    var W21_TGT = /\b(?:hood|bonnet|roof|trunk|boot|deck ?lid|doors?|fenders?|wings?|bumpers?|spoilers?|mirrors?|sides?|quarters?|splitter|lip|diffuser|skirts?|rockers?|panels?|numbers?|nums?|digits?|sponsors?|logos?|decals?|body|car|tail|nose)\b/i;
    var W21_VAL = /#[0-9a-f]{3,8}\b|\b(?:gloss\w*|matte?|satin|chrome|candy|pearl\w*|metallic|holo\w*|carbon|camo\w*|brushed|flat|shiny|shinier|glitter\w*|sparkl\w*|neon|glow\w*|fade|gradient|ombre|stripes?|flames?|checker\w*|plaid|tribal|dark(?:er)?|light(?:er)?|bright(?:er)?|bigger|smaller|larger|thicker|thinner|wider|rough\w*|opacity)\b/i;
    function w21Concrete(x) {
        if (!(W21_TGT.test(x) || w21Parts(x).length)) return false;
        if (W21_VAL.test(x) || W21_EXPL.test(x)) return true;
        try { return lex(x, {}).slots.some(function (s) { return !s.neg && !s.exc && /^(COL|FIN|PAT)$/.test(s.t); }); } catch (e) { return false; }
    }
    function w21Polite(t) {
        if (w21Off('polite') || typeof t !== 'string' || t.length > 420 || !/\?|\b(?:mind|wondering|hoping|thinking|okay|ok|possible|alright)\b/i.test(t)) return t;
        var x = t, tagged = false, lead = false, tm = W21_TAGQ.exec(x);
        if (tm) { x = x.slice(0, tm.index); tagged = true; }
        var i, best = null; for (i = 0; i < W21_PLEADS.length; i++) { var m = W21_PLEADS[i].exec(x); if (m && (!best || m.index + m[0].length > best.end)) best = { end: m.index + m[0].length, len: m[0].length }; }
        if (best) { x = x.slice(best.end); lead = true; var f1 = /^[^.!?]*/.exec(x); x = f1 ? f1[0] : x; }          // a polite lead: the order is the rest of ITS sentence ("... made the roof holographic? I think it would look fun" > "made the roof holographic")
        x = x.replace(/[\s,;.!?-]+$/, '').replace(/^\s+/, '');
        if (!tagged && !lead) return t;
        if (tagged && !lead) {          // a tag after "Could you make the trunk holographic for me, ok?": cut the pleasantry sentences before it and the bare "could you / can you" lead
            var sents = x.match(/[^.!?]+[.!?]*/g) || [x];
            while (sents.length > 1 && !W9_CONCRETE.test(sents[0])) sents.shift();
            x = sents.join(' ').replace(/[\s,;.!?-]+$/, '').replace(/^\s+/, '');
            x = x.replace(/^(?:(?:hi|hey|hello|ok|okay|so|well|and|now)\b[\s,!.:;-]*)*(?:(?:could|can|would|will)\s+(?:you|u)\s+(?:please\s+|pls\s+|just\s+|maybe\s+|kindly\s+)*)/i, '');
        }
        if (lead && /^(\w+ing)\b/i.test(x)) { var gm = /^(\w+ing)\b/i.exec(x); if (W9_GER[gm[1].toLowerCase()]) x = W9_GER[gm[1].toLowerCase()] + x.slice(gm[1].length); }
        x = x.replace(/^(?:you|u)\s+(?=(?:make|paint|change|turn|put|give|set|do|use|switch|colou?r|recolou?r|wrap|spray|coat|fill)\b)/i, '').replace(/^(made|painted|changed|turned|switched|colou?red|recolou?red|sprayed|wrapped)\b/i, function (w) { return ({ made: 'make', painted: 'paint', changed: 'change', turned: 'turn', switched: 'switch', coloured: 'colour', colored: 'color', recoloured: 'recolour', recolored: 'recolor', sprayed: 'spray', wrapped: 'wrap' })[w.toLowerCase()] || w; });
        if (lead && !new RegExp('^' + W9_IMP + '\\b', 'i').test(x)) { var pm = /^(.{3,40}?)\s+(?:made|painted|done|changed|turned)\s+(.+)$/i.exec(x); if (!pm || !W9_CONCRETE.test(x)) return t; x = 'make ' + pm[1] + ' ' + pm[2]; }          // "if roof made holographic" > "make roof holographic"
        x = x.replace(W9_TAIL, '').replace(/\s+(?:for me|for us|real quick|right now)\s*$/i, '').replace(/[\s,;.!?-]+$/, '').replace(/\s+/g, ' ').trim();
        if (x.length < 6 || /\?/.test(x) || !W9_CONCRETE.test(x) || W21_QWORD.test(x) || Q_START.test(x)) return t;
        if (tagged && !w21Concrete(x)) return t;          // W21H R2: a tag alone does not make an order out of "gotta put a number on it, right?" 
        if (!lead && !new RegExp('^' + W9_IMP + '\\b', 'i').test(x) && !/^[a-z' -]{2,40}$/i.test(x.replace(/#[0-9a-f]{3,8}/ig, 'hex'))) return t;          // a tag after a bare order ("trunk holo, ok?") or an imperative ("make wing teal, is ok?"); anything longer stays as it was
        return x;
    }
    // ---- T06_spec (hook 4; hold T06_spec 116 turns 68.1%, kill noW21H_spec): spec orders said in words the readers do not know. The same order the readers DO act on is composed from the part and the numbers:
    //   "tail spec to R 128 G 0 B 100" (the bare 'tail' + no verb read '?!'; the same with 'rear bumper' works), "hood less rough, keep colour", "nose roughness make low, colour stay same", "Lower the roughness on the hood spec, keep the base colour as is",
    //   "change only the finish on hood, colour stays" / "tail shine only, keep colour" (a finish change with no direction: shinier, colour kept). Only when the text names ONE part and no colour / pattern / finish VALUE
    //   (so 'make the hood red and less rough' and 'roof chrome, spec only' are never touched); a question is never rewritten.
    var W21_KEEPC = /\b(?:keep(?:ing)?|leave|leaving|don'?t change|do not change|dont change|no change|not change|never change|without changing|unchanged|same)\b[^.;,]{0,28}\bcolou?r\w*\b[^.;,]*|\bcolou?r\w*\s+(?:stays?|staying|same|keep|kept|no change|unchanged|is perfect|is fine|is great|is good|as is|as it is)\b[^.;,]*/gi;
    var W21_ROUGHDN = /\b(?:less|lower|reduce|reducing|decrease|drop|dropping|bring|take)\b[^.;,]{0,25}\brough(?:ness)?\b|\brough(?:ness)?\b[^.;,]{0,22}\b(?:low|lower|down|less|zero|min|minimum|smaller)\b|\bsmoother\b/i;
    var W21_RGB = /\bR\s*(\d{1,3})\s*,?\s*G\s*(\d{1,3})\s*,?\s*B\s*(\d{1,3})\b/i;
    var W21_FINONLY = /(?:\b(?:change|adjust|touch|alter|tweak|edit|do|chng|chnge)\b[^.;]{0,24}\b(?:the\s+)?(?:finish|finsh|shine|spec)\b|\b(?:finish|finsh|shine|spec)\b(?:\s*\/\s*\w+)*\s+(?:only|change)\b|\bonly\s+(?:the\s+|on\s+the\s+)?(?:finish|finsh|shine|spec)\b)/i;
    var W21_FINVAL = /\b(?:gloss\w*|matte?|chrome|candy|pearl\w*|metal\w*|satin|holo\w*|carbon|mirror|brushed|flat|semi|shin(?:y|ier)|dull\w*|rougher|smoother|more|less|lower|higher|low|high|max|min|up|down|bigger|smaller|stronger|softer|clearcoat|\d+)\b/i;
    function w21Parts(txt) {
        var IF = W.SpbIntentFrame, parts = [], ab = w9Abbr(txt);
        try { parts = (IF && IF.partsOf(ab)) || []; } catch (e) { parts = []; }
        if (!parts.length) { var Ls; try { Ls = lex(ab, {}); } catch (e2) { return []; } Ls.slots.forEach(function (x) { if (x.t !== 'PART' || x.neg || x.exc || !x.s) return; var sv = String(x.s).toLowerCase(), hit = null; for (var oi = 0; oi < OBJ_PART.length; oi++) if (OBJ_PART[oi][0].test(sv) && OBJ_PART[oi][1].length === 1) hit = OBJ_PART[oi][1][0]; parts.push(hit || sv); }); }
        return parts;
    }
    function w21Spec(t0) {          // the pleasantry clauses ("the car is looking great") are not part of the order: only the clauses about a part / the spec / the colour go to the rewrite; unchanged = the original text back
        if (w21Off('spec') || typeof t0 !== 'string' || t0.length > 320) return t0;
        var core = t0.split(/\s*[,;.!]+\s*/).filter(function (c) { return c && (/\b(?:rough(?:ness)?|smoother|spec(?:ular)?|shine|finish|finsh|colou?r\w*)\b|\bR\s*\d+\s*,?\s*G\s*\d+/i.test(c) || w21Parts(c).length); });
        if (!core.length) return t0;
        var tc = core.join(', '), r = w21SpecCore(tc);
        return r !== tc ? r : t0;
    }
    function w21SpecCore(t) {
        if (w21Off('spec') || typeof t !== 'string' || t.length > 320) return t;
        var low = t.toLowerCase();
        if (!/\b(?:rough(?:ness)?|smoother|spec(?:ular)?|shine|finish|finsh)\b/.test(low) || /\?/.test(t) || /\b(?:how|why|what|which|should|can i|could i)\b/.test(low)) return t;
        var keep = W21_KEEPC.test(low); W21_KEEPC.lastIndex = 0;
        var stripped = low.replace(W21_KEEPC, ' '); W21_KEEPC.lastIndex = 0;
        var rgb = W21_RGB.exec(t), rough = W21_ROUGHDN.test(stripped), fin = !rgb && !rough && W21_FINONLY.test(stripped) && !W21_FINVAL.test(stripped.replace(/\b(?:spec|shine|finish|finsh|roughness)\b/g, ' ').replace(/\bspec or shine or roughness\b/g, ' '));
        if (!rgb && !rough && !fin) return t;
        var Lc; try { Lc = lex(stripped, {}); } catch (e3) { return t; }
        if (Lc.slots.some(function (x) { return !x.neg && !x.exc && (x.t === 'COL' || x.t === 'PAT'); }) && !rgb) return t;          // a colour / pattern is asked for too: not a spec-only order
        if (Lc.slots.some(function (x) { return !x.neg && !x.exc && (x.t === 'BODY' || x.t === 'NUMS' || x.t === 'SPON' || x.t === 'LAYER'); })) return t;
        var parts = w21Parts(stripped); if (parts.length !== 1) return t;
        var p = parts[0], tail = keep ? ', keep colour' : '';
        if (rgb) { if (!/\bspec(?:ular)?\b/.test(low)) return t; return p + ' spec R ' + rgb[1] + ' G ' + rgb[2] + ' B ' + rgb[3] + tail; }
        if (rough) return p + ' roughness low' + tail;
        return 'make the ' + p + ' shinier' + (keep ? ', keep colour' : ', keep colour');
    }
    // ---- F_pick (hook 6; hold F_pick 302 turns 63%, kill noW21H_pick): "1st one" / "the last one, please" / "I think I'll go with the second one" after the helper listed options FOR A PART ("show rear bumper options"). The planner's list-pick reads the ordinal
    //   but asks "where?" because the part sat in the buyer's request, not in the pick. The pick is composed with the part of the options request: "the first one on the rear bumper". Only a bare pick (no part / colour / finish / pattern of its own, no
    //   question) right after an options request that names exactly ONE part. The convo store is the one the planner keeps (SpbConvo.turns); the current turn is skipped.
    var W21_ORDMAP = { '1st': 'first', first: 'first', one: 'first', '1': 'first', '2nd': 'second', second: 'second', two: 'second', '2': 'second', '3rd': 'third', third: 'third', three: 'third', '3': 'third', '4th': 'fourth', fourth: 'fourth', four: 'fourth', '4': 'fourth', last: 'last', final: 'last' };
    var W21_PICKRE = /\b(?:the\s+)?(1st|2nd|3rd|4th|first|second|third|fourth|last|final)\s+(?:one|option|choice|look|finish|spec|idea|suggestion)\b|\b(?:option|number|no\.?|nmbr|opt|choice|#)\s*(1|2|3|4|one|two|three|four)\b|^\s*(?:the\s+)?(1st|2nd|3rd|4th|first|second|third|fourth|last|final)[\s,.!]*$|\b(?:i\s+)?(?:take|pick|choose|go\s+(?:with|for))\s+(?:the\s+)?(first|second|third|fourth|last)\b/i;
    var W21_OPTSREQ = /\b(?:options?|choices?|ideas?|suggest\w*|recommend\w*|few|some|several|what (?:finishes|looks|colou?rs|patterns)|which (?:finish|look|colou?r)|show me|give me|list|possible|possibilities)\b/i;
    function w21CvPrev(cur) {
        try { var CV = W.SpbConvo, tt = CV && typeof CV.turns === 'function' ? CV.turns() : null; if (!tt || !tt.length) return null; var arr = tt.map(function (x) { return String((x && x.said) || ''); }).filter(Boolean), i = arr.length - 1; while (i >= 0 && w21IsSelf(arr[i], cur)) i--; return i >= 0 ? arr[i] : null; } catch (e) { return null; }
    }
    function w21Pick(t) {
        if (w21Off('pick') || typeof t !== 'string' || t.length > 260 || /\?/.test(t)) return t;
        var m = W21_PICKRE.exec(t); if (!m) return t;
        var ordw = (m[1] || m[2] || m[3] || m[4] || '').toLowerCase(), ord = W21_ORDMAP[ordw]; if (!ord) return t;
        var prev = w21CvPrev(t); if (!prev || prev.length > 400 || !W21_OPTSREQ.test(prev) || /\b(?:how|why|explain)\b/i.test(prev)) return t;
        var Lc; try { Lc = lex(t.replace(m[0], ' '), {}); } catch (e) { return t; }          // the ordinal phrase itself ('number two' reads as the numbers element) is not a target
        if (Lc.slots.some(function (x) { return !x.neg && !x.exc && /^(PART|COL|FIN|PAT|BODY|NUMS|SPON|LAYER)$/.test(x.t); })) return t;          // the pick names its own target / look: not a bare pick
        var parts = w21Parts(w21Pre(prev)); if (parts.length !== 1) return t;
        return 'the ' + ord + ' one on the ' + parts[0];
    }
    // ---- SA_complaint_fix (hook 3; hold SA_complaint_fix 131 turns 55%, kill noW21H_complaint): a complaint WITH a fix verb is an order. "spoiler looks awful lol make it burnt orange pls", "the boot is boring af sort it out green pls", "I hate the hood, you fix it and make violet color",
    //   "front bmpr way too dull, make it chrome" (the complaint word 'dull' used to win over the finish she NAMED: gloss instead of chrome). The part comes from the complaint, the look from the order clause: "make the <part> <look>".
    //   A complaint with no fix verb ("numbers are hard to read", "looks plastic") is untouched (the reader answers it), and so is a question (why / how / ?).
    var W21_CMPL = /\b(?:awful|terrible|hideous|horrible|garbage|trash|crap|lame|cheap|tacky|cheesy|ugly|boring|meh|dull|flat|plain|bland|bad|off|wrong|weird|drab|dated|tired|hate|hated|can'?t stand|sucks?)\b(?:\s+(?:af|lol|lmao|honestly|to me|for me|right now|now|so far))*/i;
    var W21_ORDV = /(?:^|[\s,;.!-])((?:(?:you|u)\s+)?(?:just\s+)?(?:fix|sort|repair|redo|make|mk|paint|turn|change|set|switch|put|give|recolou?r)\b[\s\S]*)$/i;
    function w21Complaint(t, env) {
        if (w21Off('complaint') || typeof t !== 'string' || t.length > 260 || /\?/.test(t) || Q_START.test(t.trim()) || /\b(?:how|why|what|which|should|can i|could i)\b/i.test(t)) return t;
        var mc = W21_CMPL.exec(t); if (!mc) return t;
        var seg = t.slice(0, mc.index + mc[0].length), after = t.slice(mc.index + mc[0].length), mo = W21_ORDV.exec(after); if (!mo) return t;
        var ord = mo[1].replace(/^(?:you|u)\s+/i, ''), cut = /^[^,;.!]*/.exec(ord), mid = after.slice(0, mo.index).replace(/^[\s,;.!-]+|[\s,;.!-]+$/g, '');
        if (cut && cut[0].length >= 6) ord = cut[0];          // "... please make it matte, would really suit the car, cheers": the order is the first clause
        var IF = W.SpbIntentFrame; if (!IF) return t;
        var Lo; try { Lo = lex(ord, env); } catch (e) { return t; }
        var os = Lo.slots.filter(function (x) { return !x.neg && !x.exc; });
        if (!os.some(function (x) { return /^(COL|FIN|PAT)$/.test(x.t); })) {          // the order names no look: a look said BEFORE the fix verb is its look ("wing looks awful. burnt orange, fix it.")
            var Lm = null; try { Lm = mid && mid.split(/\s+/).length <= 5 ? lex(mid, env) : null; } catch (e4) { Lm = null; }
            if (!Lm || !Lm.slots.some(function (x) { return /^(COL|FIN|PAT)$/.test(x.t) && !x.neg && !x.exc; }) || Lm.slots.some(function (x) { return x.t === 'PART' || x.t === 'BODY'; })) return t;
            ord = (/\b(?:fix|sort|repair|redo)\b/i.test(ord) ? 'make it ' : ord + ' ') + mid; Lo = lex(ord, env); os = Lo.slots.filter(function (x) { return !x.neg && !x.exc; });
        }
        if (os.some(function (x) { return x.t === 'PART' || x.t === 'LAYER' || x.t === 'SPON' || x.t === 'NUMS' || x.t === 'BODY'; })) return ord.replace(/[\s,;.!]+$/, '');          // the order names its own target: the complaint word must not colour it
        var parts = []; try { parts = IF.partsOf(w9Abbr(seg)) || []; } catch (e2) { parts = []; }
        if (!parts.length) { var Ls; try { Ls = lex(w9Abbr(seg), env); } catch (e3) { return t; } Ls.slots.forEach(function (x) { if (x.t !== 'PART' || x.neg || x.exc || !x.s) return; var sv = String(x.s).toLowerCase(), hit = null; for (var oi = 0; oi < OBJ_PART.length; oi++) if (OBJ_PART[oi][0].test(sv) && OBJ_PART[oi][1].length === 1) hit = OBJ_PART[oi][1][0]; parts.push(hit || sv); }); }
        if (!parts.length || parts.length > 2) return t;
        var look = ord.replace(/[\s,;.!]+$/, '');
        look = look.replace(/^(?:just\s+)?(?:fix|sort|repair|redo|change|update|improve)\s+(?:it|this|that|them|em)(?:\s+out)?(?:\s+up)?(?:\s+(?:with|using|to|in|into|by making it|by using))?\s*/i, '');
        look = look.replace(/^(?:(?:and|then|just)\s+)*(?:make|mk|turn|paint|colou?r|recolou?r|do|set|switch|put|give)\s+(?:it|them|this|that|em)\s*(?:to|into|in|with)?\s*/i, '');
        look = look.replace(/^(?:(?:and|then|just)\s+)*(?:make|mk|paint|turn|set|switch)\s+(?=\S)/i, '');
        look = look.replace(/[\s,;.!]*(?:when you (?:get|have) (?:a )?(?:chance|sec|second|moment|minute)|thanks?(?: so much| a lot| a ton)?|thank you|thx|cheers|pls|plz|please|lol|lmao|for me)[\s,;.!]*$/i, '').replace(/^\s+|\s+$/g, '');
        if (!look || look.split(/\s+/).length > 6 || /\b(?:and|but|then|because|so)\b/i.test(look)) return t;
        return 'make the ' + parts.join(' and the ') + ' ' + look;
    }
    // W21H-END
    // W23U-BEGIN 2026-10-09 (lane W23-UNDERACT; report: _easy_claude_work/eval/w23underact/PROGRESS.md). UNDER-ACTING hooks: a clear order got a question or an article back. Every hook is a TEXT REWRITE to a canonical sentence the planner already acts on. ONE kill switch:
    // window.SPB_W23U_OFF = true (node: env SPB_W23U_OFF=1 where `process` exists), SPB_OF_CFG.noW23U, localStorage SPB_W23U_OFF = '1'; one hook off: SPB_OF_CFG.noW23U_<undo|restore|stripe|spec|tail|qo|pal|chip|whole|feel|remove|size|other|livery|sugg>.
    function w23Off(sub) {
        var ls = false, pe = false;
        try { ls = typeof localStorage !== 'undefined' && localStorage.getItem('SPB_W23U_OFF') === '1'; } catch (e) { ls = false; }
        try { pe = typeof process !== 'undefined' && !!(process && process.env && process.env.SPB_W23U_OFF && process.env.SPB_W23U_OFF !== '0'); } catch (e2) { pe = false; }
        return !!(W.SPB_W23U_OFF || pe || OF_CFG('noW23U') || ls || (sub && OF_CFG('noW23U_' + sub)));
    }
    function w23Sl(t) { try { return lex(String(t), {}).slots.filter(function (x) { return !x.neg && !x.exc; }); } catch (e) { return null; } }
    function w23Any(sl, re) { return !!sl && sl.some(function (x) { return re.test(x.t); }); }
    function w23HasEdit() {          // an edit of this chat exists (the same store the planner's 'it / that' follow-ups read)
        try { var CVh = W.SpbConvo; if (!CVh || typeof CVh.lastEditCtx !== 'function') return false; var c = CVh.lastEditCtx({ skipTalk: true }); return !!(c && c.targets && c.targets.length); } catch (e) { return false; }
    }
    var W23_HOWQ = /\b(?:how\s+(?:do|can|to|would|should|does|did|could|might|may)\b|(?:any|a|the|best|easiest|quickest|simplest|simple)\s+way\s+to\b|is\s+it\s+possible\b|possible\s+to\b|(?:any|some)(?:one|body)\s+know|do\s+(?:you|u)\s+know\s+how|any\s+idea\s+how|wondering\s+(?:how|if|whether)|tell\s+me\s+how|show\s+me\s+how|teach\s+me|walk\s+me\s+through|where\s+(?:is|do|can|are)\b|what\s+(?:is|does|are|do|exactly)\b|what'?s\s+(?:the|an?)\b|is\s+there\s+(?:an?\s+)?(?:undo|way|button|shortcut)|can\s+i\b|could\s+i\b|should\s+i\b|shortcuts?|hotkeys?|ctrl|control\s*\+?\s*z|undo\s+(?:button|key|menu|option|feature|history)|does\s+(?:the\s+)?(?:undo|app|it\s+save)|keyboard|tutorial|explain|why\s+(?:does|do|is|are|can'?t)\b|h(?:ow|w|ou|wo)\s+(?:u\s+|you\s+|i\s+|we\s+|ya\s+|2\s+)?(?:un[\s-]?d(?:o+|ue?)\w*|unod|revert\w*|reverse|restore|recover\w*|roll\s*back|go\s+back|get\s+(?:it|that|this|them)\s+back|take\s+(?:it|that|this)\s+back)\b|h(?:ow|w|ou|wo)\s+(?:2|do|can|to|would|should|does|did|could)\b|ways?\s+(?:to|2)\s+(?:un[\s-]?d|revert|restore|recover|reverse|roll|go\s+back|get\s+(?:it|that|this|them)\s+back))/i;          // round 3 (hidden check of REPORT 2): "..., how undo" / "how u undo" / "hw undo" / "how 2 undo" / "way to undo" with no 'do i' and often no question mark is the same how-to family
    var W23_IMPV = /^(?:and\s+|then\s+|also\s+|just\s+|please\s+|pls\s+|now\s+|so\s+|instead\s+|rather\s+|only\s+|but\s+|actually\s+|ok(?:ay)?\s+|well\s+)*(?:make|paint|turn|change|set|switch|give|add|use|do|colou?r|recolou?r|apply|keep|leave|fix|swap|try|put|bump|raise|lower|increase|decrease|shift|remove|delete|show|let'?s|go\s+with|spray|wrap|stick|throw)\b/;
    // ---- U1 (cause 1, kill noW23U_undo): a complaint with a revert / undo verb is an UNDO ORDER. "can you please change it back to the way it was before", "not feeling it. rewind one step pls", "i dont like that, restore the old look", "wrong part! put it back", "hang on, scrap that, back to the previous look"
    //   (live: an article / 'what should I change?' / a NEW recolour). The revert phrases are cut; what is left must be chatter or a complaint about the thing (a clause with a part / colour / finish in it that has no imperative verb): any order clause left = not a pure undo (bail, the planner handles it).
    //   The canonical form is 'undo that' (answer.js turns the frame's undo act into the app's undo only when the text has an undo word); 'undo twice' when two steps are asked. The weak forms (take that off / get rid of it / the original was better) need an edit in this chat.
    var W23_RVT = '(?:\\s+(?:to\\s+)?(?:how\\s+(?:it|they|we)\\s+(?:was|were|had\\s+it)|the\\s+way\\s+(?:it|they)\\s+(?:was|were)|before|normal|square\\s+one|what\\s+(?:it|we|i)\\s+(?:was|had|started\\s+with)|(?:the\\s+)?(?:old|original|previous|earlier|last|prior|former|first)\\b(?:\\s+(?:look|version|one|state|paint|colou?rs?|setup|scheme|livery|design|finish))?))?';
    var W23_RV = [
        { re: /\b(?:undo|revert|rewind|roll\s?back)\b(?!\s+(?:the\s+)?(?:direction|angle|gradient|order|orientation|flow|slant|tilt|fade|rotation|flip))(?:\s+(?:it|that|this|the\s+(?:last|previous|latest)(?:\s+(?:change|edit|one|thing|step|move))?|(?:one|1|a)\s+(?:step|change|edit|move)|(?:two|2)\s+(?:steps|changes|edits|moves)|(?:the\s+)?(?:last|previous)\s+(?:two|2)(?:\s+(?:steps|changes|edits))?|once|twice|please|pls))*/gi, weak: false },
        { re: /\breverse\s+(?:that|what\s+(?:you|we|i)\s+(?:just\s+)?did|the\s+(?:last|previous|latest)\s+(?:change|edit|step|move))\b/gi, weak: false },          // 'reverse the direction' (a gradient / stripe flip) is NOT an undo (train gate A-0142)
        { re: new RegExp('\\b(?:put|set|change|turn|switch|send|get|bring|take|move|make|flip|roll)\\s+(?:it|that|this|them|everything|all\\s+of\\s+it|(?:that|the|this|my)\\s+(?:last\\s+|latest\\s+|previous\\s+|recent\\s+)?(?:change|edit|step|move))\\s+back\\b' + W23_RVT, 'gi'), weak: false, bare: true },          // held-out probe 2026-10-09: "let us roll that change back" (bare = no 'how it was / before / the old one' qualifier: the rest of the sentence must be empty or a complaint, negative probe: 'move it back a bit', 'set it back to 40 percent')
        { re: new RegExp('\\b(?:go|going|step|stepping|move|moving)\\s+back\\b(?:\\s+(?:one|1|a|two|2)\\s+steps?|\\s+once|\\s+a\\s+step)?' + W23_RVT, 'gi'), weak: false, bare: true },
        { re: /\bback\s+to\s+(?:how\s+(?:it|they|we)\s+(?:was|were|had\s+it)|the\s+way\s+(?:it|they)\s+(?:was|were)|before|normal|square\s+one|what\s+(?:it|we|i)\s+(?:was|had)|(?:the\s+)?(?:old|original|previous|earlier|last|prior|former|first)\b(?:\s+(?:look|version|one|state|paint|colou?rs?|setup|scheme|livery|design|finish))?)/gi, weak: false },
        { re: /\b(?:restore|bring\s+back|return\s+to|get\s+back|recover)\s+(?:the\s+)?(?:old|original|previous|earlier|last|prior|former)\b(?:\s+(?:look|version|one|state|paint|colou?rs?|setup|scheme|livery|design|finish))?/gi, weak: false },
        { re: /\b(?:return|revert|restore|reset|switch|change|set|put|take|send|bring|get|go)\s+(?:it|that|this|them)\s+(?:back\s+)?to\s+(?:the\s+|my\s+|our\s+)?(?:old|original|previous|earlier|last|prior|former)\b(?:\s+(?:look|version|one|state|paint|colou?rs?|setup|scheme|livery|design|finish))?/gi, weak: false },          // "return it to the old colours" (the object is named, so it is an order on the last change, not a new colour)
        { re: /\b(?:scrap|scratch|cancel|ditch|nix|forget|reject|bin|kill|drop)\s+(?:that|it|this)(?:\s+(?:change|edit|one|last\s+(?:change|edit|one)))?/gi, weak: false },
        { re: /\b(?:take|peel|strip|wipe|remove|get\s+rid\s+of|clear|delete|lose)\s+(?:that|it|this)(?:\s+(?:off|away|out))?(?:\s+again)?/gi, weak: true },
        { re: /\b(?:the\s+)?(?:original|old|previous|earlier|before)(?:\s+(?:one|look|version|colou?r|paint))?\s+(?:was|looked|looks)\s+(?:better|nicer|best|cooler)\b/gi, weak: true },
        { re: /\b(?:i\s+)?(?:liked|preferred|miss(?:ed)?)\s+(?:it|the\s+(?:old|original|previous|earlier)(?:\s+(?:one|look|version|colou?rs?))?)\s*(?:better\s*)?(?:before|earlier)?/gi, weak: true },
        { re: /\b(?:want|need|prefer)\s+(?:it|(?:the|my|our)\s+(?:old|original|previous|earlier)(?:\s+(?:one|look|version|colou?rs?))?)\s+back\b/gi, weak: false }
    ];
    var W23_FILL = /\b(?:please|pls|plz|hey|ok|okay|oops|oof|yikes|hang\s+on|wait|nope|nah|no|ugh|hmm|actually|just|thanks|thank\s+you|thx|lol|can\s+you|could\s+you|would\s+you|will\s+you|i\s+want\s+you\s+to|i\s+think|we\s+should|let'?s|lets|let\s+us|now|again|for\s+me|real\s+quick|quickly|asap|sorry|cheers|honestly|seriously|man|dude|bro|mate|buddy|sir|and|so|then|like|really|very|also|too)\b/g;
    var W23_CMPL = /\b(?:why|did|didn'?t|didnt|went|turned|turn(?:s|ed)?|got|gets|made|makes|was|were|is|are|looks?|looked|looking|came|ended|ruined|messed|broke|broken|wrong|bad|ugly|awful|terrible|hate|hated|don'?t|dont|do\s+not|not|too|way|suddenly|already|still|nope|what\s+happened|how\s+come|wtf|what\s+the)\b/;
    var W23_CMPL2 = new RegExp(W23_CMPL.source.replace('|was|were|is|are|', '|'));
    // ---- round 2 (orchestrator hidden set 2026-10-10, kill noW23U_undo): a revert / restore word whose OBJECT is a FILE-ish thing (save, file, folder, project, render, export, tga ...) is a support question, never an undo of the last PAINT change
    //   ("i saved over my old project by mistake, how can i undo that?", "rendered to the wrong car folder, how do i undo it", "any way to undo a render", "my save is gone, bring it back"). Bare 'undo that' / 'take it back' keep no file noun and stay undo orders.
    var W23_FILEOBJ = '(?:save[ds]?|saving|files?|folders?|director(?:y|ies)|projects?|renders?|rendering|rendered|exports?|exported|exporting|imports?|imported|importing|downloads?|downloaded|uploads?|uploaded|tga|tgas|psd|backups?|autosaves?|documents?|workspace|install(?:ed|ation)?)';
    var W23_FILE_OBJ_RE = new RegExp('\\b(?:undo|undoing|revert|reverting|restore|restoring|recover|recovering|bring(?:ing)?\\s+back|get(?:ting)?\\s+back|go(?:ing)?\\s+back\\s+to|take\\s+back|roll(?:ing)?\\s+back|rewind)\\s+(?:to\\s+)?(?:(?:the|my|a|an|that|this|our|last|previous|old|original|wrong|bad|\\w+)\\s+){0,3}' + W23_FILEOBJ + '\\b', 'i');
    var W23_FILEDET = '(?:my|the|that|this|our|old|previous|last|wrong)'+'\\s+(?:\\w+\\s+)?' + W23_FILEOBJ;
    var W23_FILE_LOST_RE = new RegExp('\\b' + W23_FILEDET + '\\b[^.!?]{0,40}\\b(?:gone|lost|missing|overwr\\w+|deleted|corrupt\\w*|wiped|replaced|erased|disappear\\w*|vanish\\w*)\\b|\\b(?:gone|lost|missing|overwr\\w+|deleted|corrupt\\w*|wiped|replaced|erased)\\b[^.!?]{0,40}\\b' + W23_FILEDET + '\\b', 'i');
    var W23_FILE_OVER_RE = new RegExp('\\b(?:saved|wrote|written)\\s+over\\b|\\boverwr(?:ote|itten|ite)\\b', 'i');
    function w23FileTalk(low) { return W23_FILE_OBJ_RE.test(low) || W23_FILE_LOST_RE.test(low) || (W23_FILE_OVER_RE.test(low) && new RegExp('\\b' + W23_FILEOBJ + '\\b', 'i').test(low)); }
    // ---- round 3 (hidden check of REPORT 2, kill noW23U_undo): "rendered with the wrong car folder and it overwrote my other car's paint, how undo" / "saved over my good file by mistake - way to undo" / "hw u undo" / "how 2 undo": a file / render / folder / save / export / overwrite mishap + a bare 'how undo' (no 'do i', often no question mark, misspelt)
    //   is a support question. The bare how-phrase becomes the plain "how do i undo" (rest of the sentence kept, so the answer still finds the car folder / render output article); live read "... - way to undo" after a paint edit as an undo order. Bare 'undo that' / 'take it back' have no how-phrase and stay undo orders.
    var W23_HOWUNDO_BARE = /(?:\bh(?:ow|w|ou|wo)\s+(?:u\s+|you\s+|i\s+|we\s+|ya\s+|2\s+)?|\b(?:a\s+|the\s+|any\s+)?ways?\s+(?:to|2)\s+)(un[\s-]?d(?:o+|ue?)\w*|unod|revert\w*|reverse|restore|recover\w*)\b/i;
    var W23_FILE_TERM = new RegExp('\\b' + W23_FILEOBJ + '\\b|' + W23_FILE_OVER_RE.source, 'i');
    function w23HowUndo(t) {
        if (w23Off('undo') || typeof t !== 'string' || !t || t.length > 220) return t;
        var m = W23_HOWUNDO_BARE.exec(t); if (!m || !W23_FILE_TERM.test(t)) return t;
        return t.replace(W23_HOWUNDO_BARE, 'how do i $1');
    }
// Proposed pure question/command distinction. No state reads or mutations.
function historyExplanation(text) {
    var t = String(text || '').trim().replace(/[‘’]/g, "'");
    t = t.replace(/^(?:(?:hey|ok|okay|please|pls)[,\s]+)*(?:quick\s+question|question)\s*[:,.!?-]?\s*/i, '');
    if (!/\b(?:undo|redo|revert|history|go back|take it back|take that back)\b/i.test(t)) return false;
    if (/\b(?:do not|don't|dont|never|not to)\s+(?:undo|redo|revert)\b/i.test(t)) return true;
    // Polite action requests retain their action semantics, including '?'.
    // 'Can you explain Undo?' is deliberately not this exception.
    if (/^(?:(?:ok|okay|hey|please|pls|just|now)[,\s]+)*(?:can|could|would|will)\s+(?:you|u)\s+(?:(?:please|pls|just)\s+)*(?:undo|redo|revert|go back|take (?:it|that) back|put (?:it|that) back)\b/i.test(t)) return false;
    return /^(?:(?:ok|okay|hey|quick|please|pls)[,\s]+)*(?:does|do|did|is|are|was|were|will|would|should|can|could|what|how|why|where|when|explain|tell me|show me)\b/i.test(t);
}

    function w23Undo(t) {
        if (historyExplanation(t)) return t; // Preserve explanatory/negative wording before Undo normalization.
        if (w23Off('undo') || typeof t !== 'string' || t.length > 220 || !t) return t;
        var low = t.toLowerCase();
        if (W23_HOWQ.test(low) || /\b(?:everything|all\s+(?:of\s+)?(?:it|the\s+changes)|start\s+over|from\s+scratch|all\s+the\s+way)\b/.test(low)) return t;          // how-to questions and the 'undo everything' reader stay as they are
        if (w23FileTalk(low)) return t;          // round 2: a file / save / render / export / project is not the paint
        if (W23_ELEM.test(low) && W23_LOST.test(low) && !w23HasEdit()) return t;          // "my number is gone, can you bring it back" with nothing edited in this chat: the support answer (how to get it back) is the useful reply, not 'nothing to undo'
        var rem = low, hit = false, weak = false, bare = false, i;
        for (i = 0; i < W23_RV.length; i++) { var before = rem, rv = W23_RV[i]; rem = rem.replace(rv.re, function (mm) { if (rv.bare && !/\b(?:how|the\s+way|before|normal|square|what|old|original|previous|earlier|last|prior|former|first|once|twice|steps?|two|2|one|1)\b/.test(mm)) bare = true; return ' | '; }); if (rem !== before) { hit = true; if (rv.weak) weak = true; } }
        if (!hit) return t;
        if (weak && !w23HasEdit()) return t;
        var cl = rem.split(/\s*(?:[,;.!?|]+|\bbut\b|\bthen\b)\s*/);
        for (i = 0; i < cl.length; i++) {
            var c = cl[i].replace(W23_FILL, ' ').replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
            if (!c) continue;
            if (bare && !W23_CMPL.test(cl[i])) return t;          // 'move it back a bit' / 'set it back to 40 percent' / 'go back to the paint tab': an unqualified 'back' with words left over is not a pure undo
            if (W23_IMPV.test(cl[i].replace(/^\s+/, ''))) return t;          // an order clause is left: not a pure undo
            if (/^\s*(?:instead|rather|but\s+instead|and\s+instead)\b/.test(cl[i]) && c.replace(/\b(?:instead|rather|only|but|and|actually)\b/g, ' ').replace(/\s+/g, '').length) return t;          // cycle 3 (aug A-0049-p1 "scrap that, instead only raise glossiness of that layer"; W21 rewrites 'raise' to 'more' on the first pass): 'instead <anything>' after a revert phrase is a REPLACEMENT order, never a pure undo
            var sl = w23Sl(c);
            if (sl && sl.some(function (x) { return /^(?:COL|FIN|PAT|PART|BODY|NUMS|SPON|LAYER)$/.test(x.t); }) && !W23_CMPL2.test(cl[i])) return t;          // cycle 3 (aug A-0541 "forget it, chrome it is"): a bare copula (is / was) is not a complaint word
        }
        return /\b(?:twice|two\s+(?:steps|changes|edits|moves)|2\s+(?:steps|changes|edits|moves)|last\s+(?:two|2)|both\s+(?:changes|edits|steps))\b|\b(?:that|it)\s+and\s+the\s+(?:one|change|edit|step)\s+before\b/.test(low) ? 'undo twice' : 'undo that';
    }
    // ---- E6 (cause 6, kill noW23U_restore): "my number disappeared, can you bring it back" / "the decals got covered, show them again" / "number's missing now, undo whatever hid it": an element WAS there and a change of this chat covered it; the order is to make it visible again = undo that change.
    //   Needs an edit in this chat (nothing to undo = leave the support article); no colour / finish named (that is a different order).
    var W23_ELEM = /\b(?:numbers?|nums?|number\s*(?:plate|panel|box)|sponsors?|sponsor\s*logos?|logos?|decals?|lettering|text|names?|graphics?|stickers?|badges?)\b/i;
    var W23_LOST = /\b(?:disappear\w*|dissapear\w*|vanish\w*|gone|missing|lost|lose|hidden|hid|cover(?:ed)?(?:\s+up)?|not\s+(?:showing|visible|there|show)|no\s+longer\s+(?:showing|visible|there)|can'?t\s+see|cant\s+see|cannot\s+see|don'?t\s+see|dont\s+see|wiped|painted\s+(?:over|out)|buried|swallowed|erased|invisible|went\s+away|isn'?t\s+(?:there|showing|visible)|aren'?t\s+(?:there|showing|visible)|(?:any\s*more|anymore)|where(?:'?d|\s+did|\s+has|\s+have)\b[^?.!]{0,40}?\b(?:go|gone|went|disappear\w*))\b/i;
    var W23_REST = /\b(?:bring|put|get|show|restore|fix|undo|recover|reveal|unhide|reinstate|re-?add|redo|display|visible|appear|back|again|return|reappear|uncover)\b/i;
    function w23Restore(t) {
        if (w23Off('restore') || typeof t !== 'string' || t.length > 200) return t;
        var low = t.toLowerCase();
        if (!W23_ELEM.test(low) || !W23_LOST.test(low) || !W23_REST.test(low) || W23_HOWQ.test(low) || w23FileTalk(low)) return t;
        var sl = w23Sl(low); if (sl && sl.some(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); })) return t;
        if (!w23HasEdit()) return t;
        return 'undo that';
    }
    // ---- S2 (cause 2, kill noW23U_stripe): a stripe asked in other words ("a thin yellow line down the center", "centreline in gold", "a purple streak up the middle", "twin orange bars down the centre", "pink ribbon down the middle of the hood, roof and trunk", "red band from nose to tail") got an
    //   ask / an article / a recoloured part. The planner makes stripe geometry for the word 'stripe': the noun is swapped when a colour AND a length cue sit in the order ('line' / 'band' / 'belt' alone are other things: pinline, belt line, a band round the numbers).
    var W23_GEO = /\b(?:(?:down|up|along|across|over|through)\s+(?:the\s+)?(?:centre|center|middle|spine|length|top|roof|hood|bonnet|trunk|boot|car|body)|(?:nose|front|bumper|hood|bonnet)\s+(?:to|2|till|until)\s+(?:the\s+)?(?:tail|back|rear|boot|trunk|bumper)|length\s*-?\s*ways?|end\s+to\s+end|(?:centre|center)\s*-?\s*(?:line|strip|band|belt|bar|ribbon|streak|stripe)|centerline|centreline|dead\s+(?:centre|center|middle))\b/i;
    var W23_SNOUN = /\b(?:lines?|strips?|belts?|ribbons?|streaks?|bars?|bands?|seams?|swathes?|swaths?)\b/gi;
    function w23Stripe(t) {
        if (w23Off('stripe') || typeof t !== 'string' || t.length > 200 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        if (!W23_GEO.test(t)) return t;
        var sl = w23Sl(t); if (!sl || !sl.some(function (x) { return x.t === 'COL'; })) return t;
        if (/\b(?:pin\s*-?\s*(?:stripe|line)s?|outline|border|edge|around|behind|beside)\b/i.test(t) || w23Any(sl, /^(?:NUMS|SPON)$/)) return t;
        var s = t, hadN = false, hadS = /\bstripes?\b/i.test(s), LEN = /\b(?:from\s+)?(?:the\s+)?(?:(?:nose|front|bumper|hood|bonnet)\s+(?:to|2|till|until)\s+(?:the\s+)?(?:tail|back|rear|boot|trunk|bumper)|length\s*-?\s*ways?|end\s+to\s+end)\b/gi;
        s = s.replace(/\b(?:running|going|travelling|traveling|extending|stretching|that\s+(?:runs|goes|stretches)|which\s+(?:runs|goes))\s+(?=(?:down|up|along|across|through|over)\b)/gi, '');          // "a strip running down the middle"
        s = s.replace(/\b(?:(?:centre|center)\s*-?\s*(?:line|strip|band|belt|bar|ribbon|streak)|centreline|centerline)\b/gi, function () { hadN = true; return 'centre stripe'; });
        s = s.replace(/\b(?:twin|double|dual|two|2|a\s+pair\s+of|pair\s+of|couple\s+of)\s+((?:[a-z#0-9]+\s+){0,2}?)(?:stripes?|lines?|strips?|belts?|ribbons?|streaks?|bars?|bands?)\b/gi, function (m, a2) { hadN = true; return (/^[aeiou]/i.test(a2 || 'x') ? 'an ' : 'a ') + a2 + 'stripe'; });
        s = s.replace(W23_SNOUN, function (m, off, str) {
            var pre = str.slice(Math.max(0, off - 12), off).toLowerCase();
            if (/(?:roof|side|door|body|belt|waist|char|shoulder|hood|window|panel|pin|shut|crease|dash|finish|start|bar)\s*-?\s*$/.test(pre) || /(?:^|\s)(?:pin|waist|roof|belt)$/.test(pre)) return m;
            hadN = true; return 'stripe';
        });
        if (hadS || hadN) s = s.replace(/\b(a\s+|an\s+|the\s+)?((?:[a-z#0-9]+\s+){0,2}?)stripes\b(?=\s+(?:down|up|along|across|over|through|from|nose|front|bumper|hood|bonnet|lengthwise|end))/gi, function (m, art, a3) { hadN = true; return (art || 'a ') + a3 + 'stripe'; });
        s = s.replace(/\bstripe\s+of\s+([a-z]+)\b/gi, function (m, w) { var q = w23Sl(w); return q && q.some(function (x) { return x.t === 'COL'; }) ? w + ' stripe' : m; });          // "line of gold" = a gold stripe
        if (!hadN) return t;
        var hasMid = /\b(?:down|up|along|across|through)\s+the\s+(?:middle|centre|center|spine)\b/i.test(s);
        if (LEN.test(s)) {
            LEN.lastIndex = 0;
            s = s.replace(/[,;]?\s*\b(?:over\s+the\s+top|on\s+top)\b/gi, '');
            s = hasMid ? s.replace(LEN, '') : s.replace(LEN, 'down the middle');          // the planner's own stripe words use 'middle' ('centre' next to a graphic reads as a MOVE request)
            s = s.replace(/\s*,\s*(?=[,.;!]|$)/g, '').replace(/\s{2,}/g, ' ');
        }
        s = s.replace(/(stripe)\s*,\s*(?=down the middle)/gi, '$1 ').replace(/\b(down|up|along|across|through)\s+(?:the\s+)?(?:centre|center)\b/gi, '$1 the middle').replace(/\b(on|at|in)\s+the\s+(?:centre|center)\b/gi, '$1 the middle').replace(/\bright\s+(?=(?:up|down|along|across|through)\s+the)/gi, '');
        s = s.replace(/\b(?:over|on|across|along|down)\s+the\s+(roof|hood|bonnet|trunk|boot)\s+(?:centre|center|middle)\b/gi, 'on the $1');
        return s === t ? t : s;
    }
    // ---- P4 (cause 4, kill noW23U_spec): spec shorthand. "rough -> 90", "metal=200", "gloss to max", "rough 0 on the hood", "cc 16 on the trunk", "metalness 0 on the rear bumper", "max gloss on the front bumper, keep the colour" (live: 'which part?' / 'say a bit more' / an article).
    //   Rewritten to the form the planner reads: '<part> roughness N' / '<part> metallic N' / '<part> clearcoat N|max' / '<part> spec R m G r B c' (two or more channels); no part named = the partless form (the last edit's part), only when this chat has an edit.
    var W23_SPK = '(rough(?:ness)?|rgh|metal(?:ness|lic|ic)?|cc|clear\\s*-?\\s*coat)';
    var W23_SPV = '(\\d{1,3}(?:\\.\\d+)?\\s*%?|zero|none|max(?:imum)?|min(?:imum)?|full|highest|lowest)';
    var W23_SPRE = new RegExp('\\b' + W23_SPK + '\\s*(?:\u2192|->|=>|=|:|@|to|at|of|is|up\\s+to|down\\s+to|set\\s+to|goes?\\s+to)?\\s*' + W23_SPV + '(?![a-z0-9])', 'gi');
    function w23SpecVal(ch, v) {
        v = String(v).toLowerCase().replace(/\s+/g, '');
        if (/^(?:zero|none|min|minimum|lowest)$/.test(v)) return '0';
        if (/^(?:max|maximum|full|highest)$/.test(v)) return ch === 'B' ? 'max' : '255';
        var pc = /%$/.test(v), n = parseFloat(v); if (isNaN(n)) return null;
        if (pc) n = Math.round(n * 2.55);
        return String(Math.max(0, Math.min(255, Math.round(n))));
    }
    function w23Spec(t) {
        if (w23Off('spec') || typeof t !== 'string' || t.length > 200 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var low = t.toLowerCase().replace(/[\u2192\u21d2\u27f6]/g, '->'), ch = {}, n = 0, rest = low, m;
        W23_SPRE.lastIndex = 0;
        rest = low.replace(W23_SPRE, function (m0, k, v) { var c = /^rough|^rgh/.test(k) ? 'G' : /^metal/.test(k) ? 'R' : 'B', val = w23SpecVal(c, v); if (val == null) return m0; if (ch[c] == null) n++; ch[c] = val; return ' '; });
        var gm = /\b(?:max(?:imum)?|full|highest)\s+gloss\b|\bgloss\s+(?:to\s+|at\s+|up\s+to\s+)?(?:max(?:imum)?|full|100\s*%)\b/i;
        if (!n && gm.test(low)) { ch.B = 'max'; n = 1; rest = low.replace(gm, ' '); }
        else if (n && gm.test(rest)) { rest = rest.replace(gm, ' '); if (ch.B == null) { ch.B = 'max'; n++; } }
        if (!n) return t;
        var sl = w23Sl(rest); if (sl && sl.some(function (x) { return /^(?:COL|PAT|BODY|NUMS|SPON|LAYER)$/.test(x.t); })) return t;          // a colour / pattern / element in the same order: not a spec-only order
        var parts = []; try { parts = w21Parts(rest) || []; } catch (e) { parts = []; }
        if (parts.length > 2) return t;
        if (!parts.length && !w23HasEdit()) return t;
        var spec;
        if (n >= 2) spec = 'spec' + (ch.R != null ? ' R ' + ch.R : '') + (ch.G != null ? ' G ' + ch.G : '') + (ch.B != null ? ' B ' + (ch.B === 'max' ? '16' : ch.B) : '');
        else spec = ch.G != null ? 'roughness ' + ch.G : ch.R != null ? 'metallic ' + ch.R : 'clearcoat ' + ch.B;
        var tail = /\bkeep\s+(?:the\s+)?(?:colou?r|paint)s?\b|\b(?:same|current)\s+colou?r\b/.test(rest) ? ', keep the colour' : '';
        var left = rest.replace(/\b(?:keep|the|same|current|colou?r|paint|colours?)\b/g, ' ').replace(W23_FILL, ' ');
        try { parts.forEach(function (p) { left = left.replace(new RegExp('\\b' + String(p).replace(/\s+/g, '\\s+') + 's?\\b', 'g'), ' '); }); } catch (e3) { /* keep */ }
        try { (sl || []).forEach(function (x) { if (x.t === 'PART' && x.s) left = left.replace(new RegExp('\\b' + String(x.s).toLowerCase().replace(/^\s*(?:the|both|all)\s+/, '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+') + '\\b', 'g'), ' '); }); } catch (e4) { /* keep */ }          // held-out probe: "metalness 255 on the doors" (the part's own words, "doors", are not its canonical name, "sides")
        left = left.replace(/\b(?:set|make|put|give|change|bump|drop|turn|on|of|for|to|at|in|with|a|an|it|its|this|that|both|all|spec|specs|channel|value|level|settings?|setting)\b/g, ' ').replace(/[^a-z0-9]+/g, ' ').replace(/^\s+|\s+$/g, '');
        if (left) return t;          // the order says more than the spec: leave it to the planner
        return (parts.length ? parts.join(' and ') + ' ' : '') + spec + tail;
    }
    // ---- T8 (cause 8, kill noW23U_tail): a caution tail on a subtle tweak ("a touch brighter on the doors, dont go overboard", "roof just slightly lighter, nothing wild") made the planner ask: the tail is cut, the subtle tweak ("doors a touch brighter") is an order the planner already runs.
    var W23_TAIL = [
        /[,;.\-]?\s*(?:but\s+)?(?:please\s+)?(?:don'?t|dont|do\s+not|not\s+to|no\s+need\s+to)\s+(?:go\s+|get\s+|be\s+|make\s+it\s+)?(?:over\s*board|overdo(?:\s+it)?|too\s+far|crazy|wild|nuts|mad|extreme|carried\s+away|(?:too\s+)?(?:much|bright|dark|bold|loud|dramatic|big|crazy|wild))\b[^,;.!?]*/gi,
        /[,;.\-]?\s*(?:but\s+)?nothing\s+(?:too\s+)?(?:crazy|wild|extreme|drastic|dramatic|major|big|huge|radical|loud|silly|over\s+the\s+top|ott|too\s+much|fancy|intense|mad)\b/gi,
        /[,;.\-]?\s*(?:but\s+)?not\s+too\s+(?:much|crazy|wild|extreme|bold|loud|bright|dark|dramatic|drastic|obvious)\b/gi,
        /[,;.\-]?\s*(?:but\s+)?(?:keep\s+it|keeping\s+it|go)\s+(?:subtle|tasteful|mild|gentle|light|modest|low\s*key|understated|small|easy|gently|softly)\b/gi,
        /[,;.\-]?\s*(?:but\s+)?(?:go\s+easy|easy\s+(?:does\s+it|now|there)|gently|softly|carefully)\s*(?:please|pls)?\s*$/gi,
        /[,;.\-]?\s*(?:without|w\/o)\s+going\s+(?:overboard|too\s+far|crazy|wild)\b/gi
    ];
    function w23Tail(t) {
        if (w23Off('tail') || typeof t !== 'string' || t.length > 200 || /\?/.test(t)) return t;
        var s = t, i, hit = false;
        for (i = 0; i < W23_TAIL.length; i++) { var b = s; s = s.replace(W23_TAIL[i], ''); if (s !== b) hit = true; }
        if (!hit) return t;
        s = s.replace(/\s+/g, ' ').replace(/^[\s,;.\-]+|[\s,;.\-]+$/g, '');
        if (s.split(/\s+/).length < 2) return t;
        var sl = w23Sl(s); if (!sl || !sl.some(function (x) { return /^(?:PART|BODY|COL|FIN|PAT|NUMS|SPON|LAYER)$/.test(x.t); }) && !/\b(?:more|less|bit|touch|tad|little|slightly|lighter|darker|brighter|bigger|smaller)\b/i.test(s)) return t;
        return s;
    }
    // ---- Q9 (cause 9, kill noW23U_qo): a QUESTION and an ORDER in one turn: the order wins. "which of your finishes is the glossiest? put it on the roof", "do you have holo? trunk please", "tell me your best satin, then put it on the roof", "how shiny can the wing go? max it".
    //   The closest catalogue match is picked from the question (the look it names; 'X or Y' = the first, or the subtler / bolder one when the question says so; a superlative = a plain family) and the order becomes 'make the <parts> <look>' (the reading line tells the buyer what was chosen).
    //   An order with its own part AND look after the question is simply that order. No look to pick (a taste question: "what's a good colour for a trunk? make it that") = untouched: the helper asks.
    var W23_QSTART = /^(?:(?:hey|hi|ok|okay|so|and|um|hmm|quick\s+one|one\s+thing)[\s,]+)*(?:tell\s+me|show\s+me|what(?:'?s|\s+is|\s+are|s)?\b|which\b|do\s+(?:you|u)\b|have\s+(?:you|u)\b|got\s+any|is\s+there|are\s+there|how\s+(?:shiny|glossy|matte|dark|bright|light|reflective|flat|metallic|sparkly)|can\s+(?:you|u)\s+do\b|does\s+it|d'?you\b)/i;
    var W23_ORDST = /^(?:(?:ok|okay|so|then|and|please|pls|just|now|go\s+ahead\s+and|if\s+so|if\s+you\s+do|if\s+yes|if\s+they\s+do|if\s+it\s+does|whichever|either|any|whatever|you\s+pick|your\s+pick)[,\s]+)*(?:(?:put|use|do|try|apply|give|stick|throw|slap|set|go\s+with|paint|add)\b(?=.*\b(?:it|that|this|those|them|one)\b)|(?:max|maximi[sz]e|push|crank)\s+(?:it|that)\b)/i;
    var W23_SHINE = { matte: 1, flat: 1, stealth: 1, satin: 2, eggshell: 2, semi: 2, gloss: 3, glossy: 3, wet: 3, chrome: 4, mirror: 4, metallic: 3, candy: 3, pearl: 3 };
    function w23Look(q) {
        var sl = w23Sl(q); if (!sl) return null;
        var looks = sl.filter(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); });
        if (looks.length) {
            var fins = looks.filter(function (x) { return x.t === 'FIN'; });
            if (/\bor\b/i.test(q) && fins.length >= 2) {
                var pick = fins[0], r = function (x) { return W23_SHINE[String(x.s || x.v).toLowerCase().split(/\s+/)[0]] || 0; };
                if (/\b(?:subtl\w*|quiet\w*|understated|low[- ]?key|less\s+shin\w*|duller|calmer|softer|safer|tamer)\b/i.test(q)) fins.forEach(function (x) { if (r(x) && (!r(pick) || r(x) < r(pick))) pick = x; });
                else if (/\b(?:bold\w*|loud\w*|flash\w*|shinier|brighter|more\s+shin\w*|eye[- ]?catching|bling\w*)\b/i.test(q)) fins.forEach(function (x) { if (r(x) > r(pick)) pick = x; });
                return String(pick.s || pick.v);
            }
            var first = looks[0], out = [String(first.s || first.v)];
            if (/\bor\b/i.test(q)) { var oi = q.toLowerCase().indexOf(' or '); if (oi > 0) { var left = looks.filter(function (x) { return (x.i == null) || x.i < oi; }); if (left.length) out = left.map(function (x) { return String(x.s || x.v); }); } }
            else out = looks.map(function (x) { return String(x.s || x.v); });
            return out.join(' ');
        }
        var ql = q.toLowerCase();
        if (/\b(?:glossi(?:est)?|shini(?:est)?|most\s+(?:glossy|shiny|reflective)|highest\s+(?:gloss|shine)|mirror[- ]?like)\b/.test(ql)) return 'gloss';
        if (/\b(?:most\s+(?:matte|flat|dull|muted|subtle)|mattest|flattest|dullest|least\s+(?:shiny|glossy))\b/.test(ql)) return 'matte';
        if (/\b(?:coolest|sickest|wildest|craziest|most\s+(?:unique|eye[- ]?catching|extreme|futuristic)|flashiest)\b/.test(ql)) return 'holographic';
        if (/\b(?:best|nicest|prettiest|classiest|most\s+(?:elegant|popular|classic|beautiful)|favou?rite|finest)\s+(?:finish|look|one|paint)\b|\byour\s+(?:best|favou?rite)\b/.test(ql)) return 'pearl';
        return null;
    }
    function w23QO(t) {
        if (w23Off('qo') || typeof t !== 'string' || t.length > 260) return t;
        var qi = t.indexOf('?'), Q, O;
        if (qi > 0 && qi < t.length - 3) { Q = t.slice(0, qi + 1); O = t.slice(qi + 1); }
        else {
            var bm = /^(.{8,}?)(?:[;.]\s+|,\s*(?:then|and|so)\s+|\s+then\s+|,\s+)(?=(?:(?:ok|okay|so|then|and|please|pls|just|now|if\s+so|whichever|either)[,\s]+)*(?:put|use|do|try|apply|give|stick|throw|slap|set|go\s+with|paint|add|max|maximi[sz]e|push|crank)\b)/i.exec(t);
            if (!bm) return t;
            Q = bm[1]; O = t.slice(bm[0].length);
            if (!W23_QSTART.test(Q.trim())) return t;
        }
        O = O.replace(/^[\s,;.!?]+/, '').replace(/[\s.!]+$/, '');
        if (!O || O.split(/\s+/).length > 14 || /\?/.test(O) || /\b(?:don'?t|dont|not|never|without|except|no\b)/i.test(O) || /\b(?:how|why|what|which|where|when)\b/i.test(O)) return t;
        Q = Q.trim();
        if (!W23_QSTART.test(Q) || /\b(?:how\s+(?:do|can|to|would|should)\s+(?:i|we|you)|where\s+(?:is|do|can)|why)\b/i.test(Q) || (W23_IMPV.test(Q.toLowerCase()) && !/^(?:(?:hey|hi|ok|okay|so|and)[\s,]+)*do\s+(?:you|u)\b/i.test(Q))) return t;
        var oSl = w23Sl(O), oParts = []; try { oParts = w21Parts(O) || []; } catch (e) { oParts = []; }
        var oLook = w23Any(oSl, /^(?:COL|FIN|PAT)$/), oTgt = w23Any(oSl, /^(?:PART|BODY|NUMS|SPON|LAYER)$/);
        if (oLook && (oTgt || oParts.length)) return O;          // a complete order after the question: the order wins
        if (oLook) return t;
        var ana = W23_ORDST.test(O) || (oParts.length && !oLook && O.replace(/\b(?:please|pls|plz|in\s+that|with\s+that|then|too|the|a|my|and|n)\b/gi, ' ').replace(/\s+/g, ' ').split(/\s+/).filter(Boolean).length <= 5) || /^(?:whichever|either|any(?:thing)?|you\s+pick|your\s+pick)[,\s]+(?:do|put|use)\b/i.test(O);
        if (!ana) return t;
        var parts = oParts.length ? oParts : (function () { try { return w21Parts(Q) || []; } catch (e2) { return []; } })();
        if (!parts.length || parts.length > 3) return t;
        var look = w23Look(Q);
        if (!look && /^(?:max|maximi[sz]e|push|crank)\b/i.test(O)) { var ql = Q.toLowerCase(); look = /\b(?:shin\w*|gloss\w*|reflect\w*)\b/.test(ql) ? 'gloss' : /\b(?:matte|flat|dull)\b/.test(ql) ? 'matte' : null; }
        if (!look) return t;
        return 'make the ' + parts.join(' and the ') + ' ' + look;
    }
    // ---- H7 (cause 7, kill noW23U_pal): a brand palette with hex codes in the same message ("main colour #1A7F3C, accent #222222, do the body in the main one", "brand: #6A0DAD (main), #FFB81C (accent). roof in the accent", "team palette #FF6600 / #1B365D, do the car body in the orange one",
    //   "primary #FF6600, secondary #111111; front bumper in the dark one"). W15F_roles reads 'primary / secondary / main colour / accent colour is #hex'; this reads the other spellings (main shade, hex (role), a palette list, trim / base / brand roles) AND the other references (the second one,
    //   the dark one, the orange one). Definitions are cut, references become the hex; no reference to resolve = the text is untouched ('paint the trim #003DA5' is an order, not a palette).
    var W23_ROLEW = '(?:main|primary|secondary|second|tertiary|third|accent|trim|base|brand|house|team|club|first|highlight|contrast|background|detail|alt(?:ernate)?|dominant|lead|supporting|1st|2nd|3rd)';
    var W23_ROLEGRP = [['main', 'primary', 'first', '1st', 'brand', 'house', 'team', 'club', 'dominant', 'lead'], ['secondary', 'second', '2nd', 'alt', 'alternate', 'supporting'], ['tertiary', 'third', '3rd'], ['accent', 'highlight', 'contrast', 'detail'], ['trim'], ['base', 'background']];
    var W23_HEXRE = '(#[0-9a-f]{6}\\b|#[0-9a-f]{3}\\b)';
    function w23Rgb(h) { h = String(h).replace('#', ''); if (h.length === 3) h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2); var n = parseInt(h, 16); return isNaN(n) ? null : [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
    function w23Hsl(h) {
        var c = w23Rgb(h); if (!c) return null;
        var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn, hu = 0, sat = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
        if (d > 0) { if (mx === r) hu = ((g - b) / d) % 6; else if (mx === g) hu = (b - r) / d + 2; else hu = (r - g) / d + 4; hu *= 60; if (hu < 0) hu += 360; }
        return { h: hu, s: sat, l: l };
    }
    function w23HexNames(h) {
        var f = w23Hsl(h); if (!f) return [];
        if (f.l < 0.17) return ['black'];
        if (f.l > 0.88 && f.s < 0.4) return ['white'];
        if (f.s < 0.16) return f.l > 0.8 ? ['white'] : ['grey', 'gray', 'silver'];
        var hu = f.h, o = [];
        if (hu < 14 || hu >= 346) o.push(f.l > 0.72 ? 'pink' : 'red');
        else if (hu < 40) { o.push(f.l < 0.34 ? 'brown' : 'orange'); }
        else if (hu < 52) o.push('gold', 'yellow');
        else if (hu < 70) o.push('yellow');
        else if (hu < 165) o.push('green');
        else if (hu < 200) o.push('teal', 'cyan');
        else if (hu < 255) { o.push('blue'); if (f.l < 0.3) o.push('navy'); }
        else if (hu < 292) o.push('purple', 'violet');
        else o.push('pink', 'magenta');
        return o;
    }
    function w23Pal(s) {
        if (w23Off('pal') || typeof s !== 'string' || s.length > 420 || !/#[0-9a-f]{3}/i.test(s) || /\?/.test(s)) return s;
        var map = {}, order = [], t = s;
        function addHex(hx) { hx = hx.toLowerCase(); if (order.indexOf(hx) < 0) order.push(hx); }
        t = t.replace(new RegExp(W23_HEXRE + '\\s*\\(\\s*(?:the\\s+)?(' + W23_ROLEW + ')(?:\\s+(?:colou?r|shade|one))?\\s*\\)', 'gi'), function (m0, hx, role) { map[role.toLowerCase()] = hx.toLowerCase(); addHex(hx); return ' '; });
        t = t.replace(new RegExp(W23_HEXRE + '\\s*(?:\\bas\\b|\\bfor\\b|=|:|-)\\s*(?:the\\s+)?(' + W23_ROLEW + ')(?:\\s+(?:colou?r|shade|one))?\\b(?!\\s+(?:of|on|for))', 'gi'), function (m0, hx, role) { map[role.toLowerCase()] = hx.toLowerCase(); addHex(hx); return ' '; });
        t = t.replace(new RegExp('\\b(' + W23_ROLEW + ')(?:\\s+(?:colou?r|shade|tone|hue|one))?\\s*(?:is|=|:|->|=>|-|will\\s+be|should\\s+be)?\\s*' + W23_HEXRE, 'gi'), function (m0, role, hx) { map[role.toLowerCase()] = hx.toLowerCase(); addHex(hx); return ' '; });
        t = t.replace(new RegExp('(?:\\b(?:team|brand|livery|club|house|our|my|the|new)\\s+)*\\b(?:palette|colou?rs?|scheme|theme|brand|branding)\\s*(?:is|are|:|-)?\\s*' + W23_HEXRE + '(?:\\s*(?:\\/|,|&|\\band\\b|\\+|\\|)\\s*' + W23_HEXRE + ')+', 'gi'), function (m0) { (m0.match(/#[0-9a-f]{6}\b|#[0-9a-f]{3}\b/gi) || []).forEach(addHex); return ' '; });
        if (!order.length) return s;
        function byGroup(role) {
            role = role.toLowerCase(); if (map[role]) return map[role];
            for (var gi = 0; gi < W23_ROLEGRP.length; gi++) { if (W23_ROLEGRP[gi].indexOf(role) >= 0) { for (var k = 0; k < W23_ROLEGRP[gi].length; k++) if (map[W23_ROLEGRP[gi][k]]) return map[W23_ROLEGRP[gi][k]]; } }
            return null;
        }
        var used = false;
        t = t.replace(new RegExp('\\b(?:the\\s+)?(' + W23_ROLEW + ')(?:\\s+(colou?r|shade|tone|hue|one))?\\b(?!\\s*[:=])', 'gi'), function (m0, role, noun) { if (!noun && /^(?:brand|team|house|club|lead|dominant|supporting)$/i.test(role)) return m0; var hx = byGroup(role); if (!hx) return m0; used = true; return hx; });
        t = t.replace(/\b(?:the\s+)?(first|1st|second|2nd|third|3rd|last)\s+(?:one|colou?r|shade|hue|tone)\b/gi, function (m0, o) { o = o.toLowerCase(); var ix = /^(?:first|1st)$/.test(o) ? 0 : /^(?:second|2nd)$/.test(o) ? 1 : /^(?:third|3rd)$/.test(o) ? 2 : order.length - 1; if (order.length < 2 || ix >= order.length) return m0; used = true; return order[ix]; });
        t = t.replace(/\b(?:the\s+)?(dark(?:er|est)?|light(?:er|est)?|pale(?:r|st)?|bright(?:er|est)?)\s+(?:one|colou?r|shade|hue|tone)\b/gi, function (m0, w) {
            if (order.length < 2) return m0; var dk = /^dark/i.test(w), best = null, bl = null;
            order.forEach(function (hx) { var f = w23Hsl(hx); if (!f) return; if (best == null || (dk ? f.l < bl : f.l > bl)) { best = hx; bl = f.l; } });
            if (!best) return m0; used = true; return best;
        });
        t = t.replace(/\b(?:the\s+)?(red|orange|yellow|gold|green|teal|cyan|blue|navy|purple|violet|pink|magenta|black|white|grey|gray|silver|brown)(?:ish)?\s+(?:one|colou?r|shade|hue)\b/gi, function (m0, w) {
            if (order.length < 2) return m0; w = w.toLowerCase(); var hits = order.filter(function (hx) { return w23HexNames(hx).indexOf(w) >= 0; });
            if (hits.length !== 1) return m0; used = true; return hits[0];
        });
        if (!used) return s;
        var cls = t.split(/\s*[.;!\n]+\s*/).map(function (c) { return c.replace(/^[\s,:\-]+|[\s,:\-]+$/g, '').replace(/\s*,\s*,+/g, ',').replace(/\s{2,}/g, ' '); }).filter(function (c) { return c && !/^(?:(?:the|our|my|team|brand|livery|club|house|new)\s+)*(?:palette|colou?rs?|scheme|theme|brand|branding|livery|kit)?[\s,:\-&\/]*(?:and\s*)?$/i.test(c); });
        var out = cls.join('. ').replace(/^(?:and|then|so|ok|okay)\s+/i, '').replace(/\s+/g, ' ').trim();
        return out || s;
    }
    // ---- R3 (cause 3, kill noW23U_chip): a SHORT REPLY to the helper's own question. "first one" / "the second option" / "the last one" / "the 3rd one" after the helper offered chips (its last ask: W.__w17().opts.chips), "the whole car" / "hood n roof" / "just the hood" after "which part?".
    //   The picked chip is the helper's own offer: a full order chip ("Make the hood gold") runs as it is; a part chip ("The roof", "On the hood") is put into the buyer's previous order in place of 'it' ("make it darker" > "make the roof darker"); a look chip ("Gold") is added to a part-only order ("paint the car" > "paint the car gold").
    //   Needs a FRESH ask with chips (one turn old); the reply names nothing of its own (an ordinal) or only parts. "first one body, second one trim" = the previous turn's two colours go to the two targets.
    var W23_ORDIX = { first: 0, '1st': 0, second: 1, '2nd': 1, third: 2, '3rd': 2, fourth: 3, '4th': 3, last: -1, final: -1, '1': 0, '2': 1, '3': 2, '4': 3, one: 0, two: 1, three: 2, four: 3 };
    var W23_PICK = /^\s*(?:(?:ok(?:ay)?|yes|yeah|yep|sure|cool|hmm|well|so|and|let'?s|lets|i'?ll|ill|i\s+(?:will|think|guess)|go|going|with|take|pick|choose|do|use|gimme|give\s+me|i\s+want|i'?d\s+(?:like|go\s+with|take)|how\s+about|what\s+about)[\s,]+)*(?:(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|last|final)(?:\s+(?:one|option|choice|pick|suggestion|idea))?|(?:the\s+)?(?:option|choice|number|no\.?|#)\s*(1|2|3|4|one|two|three|four))(?:\s+(?:one|option|choice|pick|please|pls|plz|thanks|then|yeah|ok|there))*[\s.!]*$/i;
    function w23Chips() {
        try {
            var o = W.__w17 && W.__w17(); if (!o || !o.opts || !o.opts.chips || !o.opts.chips.length) return null;
            if (typeof o.n === 'number' && typeof o.opts.n === 'number' && o.n - o.opts.n > 1) return null;
            return o.opts.chips.map(function (c) { return String(typeof c === 'string' ? c : (c && (c.label || c.say || c.text)) || ''); });
        } catch (e) { return null; }
    }
    function w23Fill(prior, chip) {
        var c = String(chip).replace(/^\s+|\s+$/g, ''); if (!c || c.length > 80 || /:|\btake\s+\d|^show\s+me\b|\bmore\b|\bother\b|\bsomething\b/i.test(c)) return null;
        var csl = w23Sl(c); if (!csl) return null;
        var cTgt = w23Any(csl, /^(?:PART|BODY|NUMS|SPON|LAYER)$/), cLook = w23Any(csl, /^(?:COL|FIN|PAT)$/);
        if (cTgt && cLook) return /^only\b/i.test(c) ? 'make ' + c.charAt(0).toLowerCase() + c.slice(1) : c.charAt(0).toLowerCase() + c.slice(1);          // a full order chip
        var psl = w23Sl(prior); if (!psl || !prior || prior.length > 160 || /\?/.test(prior)) return null;
        var pTgt = w23Any(psl, /^(?:PART|BODY|NUMS|SPON|LAYER)$/), pLook = w23Any(psl, /^(?:COL|FIN|PAT)$/);
        if (cTgt && !cLook) {
            if (pTgt) return null;
            var lc = c.charAt(0).toLowerCase() + c.slice(1), pr = /\b(?:on|onto|over|across|along)\s+(?:it|them|this|that)\b/i;
            if (pr.test(prior) && /^(?:on|onto|over|across|along)\b/i.test(lc)) return prior.replace(pr, lc);
            if (pr.test(prior)) return prior.replace(pr, (/^(?:on|onto|over|across|along)\b/i.test(lc) ? '' : 'on ') + (/^the\b/.test(lc) ? lc : 'the ' + lc.replace(/^(?:on|onto|over)\s+/, '')));
            if (/\b(?:it|them|this|that)\b/i.test(prior)) return prior.replace(/\b(?:it|them|this|that)\b/i, /^the\b/.test(lc) ? lc : 'the ' + lc);
            return null;
        }
        if (cLook && !cTgt) { if (!pTgt || pLook) return null; return prior.replace(/[\s.!]+$/, '') + ' ' + c.charAt(0).toLowerCase() + c.slice(1); }
        return null;
    }
    function w23Chip(t) {
        if (w23Off('chip') || typeof t !== 'string' || t.length > 90 || /\?/.test(t)) return t;
        var low = t.toLowerCase(), pm = W23_PICK.exec(low), isWhole = /^\s*(?:(?:ok(?:ay)?|yes|yeah|just|only|the|do|all|go\s+with|let'?s\s+do)[\s,]+)*(?:the\s+)?(?:whole\s+car|entire\s+car|whole\s+thing|everything|all\s+of\s+it|all\s+over|the\s+lot|the\s+car|whole\s+body)(?:\s+(?:please|pls|plz|thanks|yeah|then))?[\s.!]*$/i.test(low);
        var partsOnly = false, sl = w23Sl(low), rp = [];
        if (!pm && !isWhole) {
            if (!sl || !sl.length || sl.some(function (x) { return !/^(?:PART|BODY)$/.test(x.t); })) return w23Chip2(t);
            try { rp = w21Parts(low) || []; } catch (e) { rp = []; }
            if (!rp.length || rp.length > 3 || low.split(/\s+/).length > 7) return t;
            partsOnly = true;
        }
        var chips = w23Chips(); if (!chips) return t;
        var prior = w21CvPrev(t); if (!prior || prior.length > 200) return t;
        if (pm) {
            var w = (pm[1] || pm[2] || '').toLowerCase(), ix = W23_ORDIX[w]; if (ix == null) return t;
            var chip = chips[ix === -1 ? chips.length - 1 : ix]; if (chip == null) return t;
            var out = w23Fill(prior, chip); return out || t;
        }
        if (isWhole && chips.some(function (c) { var cs = w23Sl(c); return cs && cs.some(function (x) { return x.t === 'BODY'; }); })) return t;          // train gate A-0483 2026-10-09 ("yo make it chrome" / "everything?" / "yeah everything"): the ask already OFFERS a whole-car chip and the live chip reader runs it; my rewrite of the prior order lost that and got the confirm ask again
        var tgt = isWhole ? 'the whole car' : 'the ' + rp.join(' and the ');
        var hasChip = chips.some(function (c) { var cs = w23Sl(c); return cs && cs.some(function (x) { return /^(?:PART|BODY)$/.test(x.t); }); });
        if (!hasChip) return t;
        var psl = w23Sl(prior); if (!psl || w23Any(psl, /^(?:PART|BODY|NUMS|SPON|LAYER)$/) || !/\b(?:it|them|this|that)\b/i.test(prior) || /\?/.test(prior)) return t;
        if (!partsOnly && !isWhole) return t;
        return prior.replace(/\b(?:it|them|this|that)\b/i, tgt);
    }
    function w23Chip2(t) {          // "first one body, second one trim": the previous turn's two colours go to the two targets
        var m = /^\s*(?:the\s+)?(first|1st|second|2nd)(?:\s+one)?\s+(?:on\s+|for\s+|is\s+for\s+|goes\s+(?:on|to)\s+)?(?:the\s+)?([a-z ]{2,24}?)\s*(?:[,;&]|\band\b)\s*(?:the\s+)?(first|1st|second|2nd)(?:\s+one)?\s+(?:on\s+|for\s+|is\s+for\s+|goes\s+(?:on|to)\s+)?(?:the\s+)?([a-z ]{2,24}?)[\s.!]*$/i.exec(t);
        if (!m) return t;
        var a = /^(?:first|1st)$/i.test(m[1]) ? 0 : 1, b = /^(?:first|1st)$/i.test(m[3]) ? 0 : 1; if (a === b) return t;
        var prior = w21CvPrev(t); if (!prior || prior.length > 200) return t;
        var psl = w23Sl(prior); if (!psl) return t;
        var cols = psl.filter(function (x) { return x.t === 'COL'; }).map(function (x) { return String(x.s || x.v); }); if (cols.length !== 2) return t;
        function tg(x) { x = x.replace(/^\s+|\s+$/g, ''); return /^(?:body|car|whole car|main)$/i.test(x) ? 'the body' : 'the ' + x; }
        return 'make ' + tg(m[2]) + ' ' + cols[a] + ', and make ' + tg(m[4]) + ' ' + cols[b];
    }
    // ---- W5 (cause 5, kill noW23U_whole): a WHOLE-CAR order with protection / an extra part. "all-over gloss black please, wing included, numbers stay untouched", "make everything stealth black, even the spoiler, just not the sponsors", "whole car matte black and the wing" (live: the wing 'included' made the planner ask which finish,
    //   or paint ONLY the wing and drop the body). Rewritten to two plain clauses the planner runs ("make the whole car <look>, except the numbers, and make the spoiler <look> too"): the protected elements are kept, the extra part is painted too.
    var W23_PROT = /(?:\b(?:leave|keep|don'?t\s+touch|dont\s+touch|do\s+not\s+touch|skip|ignore|spare|protect|preserve)\s+(?:the\s+|my\s+|our\s+)?((?:[a-z]+\s+){0,1}?(?:numbers?|sponsors?|logos?|decals?|lettering|stripes?|windows?|glass|text|badges?))(?:\s+and\s+(?:the\s+)?((?:numbers?|sponsors?|logos?|decals?|lettering|stripes?|windows?|glass|text|badges?)))?(?:\s+(?:alone|as\s+is|untouched|the\s+same|unchanged|intact|how\s+(?:it|they)\s+(?:is|are)))?)|(?:\b(?:the\s+)?((?:numbers?|sponsors?|logos?|decals?|lettering|stripes?|windows?|glass|text|badges?))(?:\s+and\s+(?:the\s+)?((?:numbers?|sponsors?|logos?|decals?|lettering|stripes?|windows?|glass|text|badges?)))?\s+(?:(?:stay|stays|remain|remains)(?:\s+(?:untouched|the\s+same|as\s+(?:is|they\s+are)|unchanged|alone|safe|intact))?|(?:are|is)\s+(?:untouched|the\s+same|as\s+(?:is|they\s+are)|unchanged|alone|safe|intact)))|(?:\b(?:except|excluding|but\s+not|just\s+not|apart\s+from|other\s+than|besides|without\s+touching|not\s+touching)\s+(?:the\s+|my\s+|our\s+)?((?:numbers?|sponsors?|logos?|decals?|lettering|stripes?|windows?|glass|text|badges?))(?:\s+and\s+(?:the\s+)?((?:numbers?|sponsors?|logos?|decals?|lettering|stripes?|windows?|glass|text|badges?)))?)/gi;
    function w23Whole(t) {
        if (w23Off('whole') || typeof t !== 'string' || t.length > 240 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var low = t.toLowerCase(), sl = w23Sl(low); if (!sl || !sl.some(function (x) { return x.t === 'BODY'; })) return t;
        if (!/\b(?:incl\w*|too|as\s+well|also|even|plus|along\s+with|and\s+the|with\s+the|and\s+make)\b/.test(low)) return t;
        if (/\b(?:the\s+)?rest\b|\beverything\s+else\b|\ball\s+(?:the\s+)?(?:else|other)\b|\bremaining\b|\b(?:the\s+)?others?\b|\belse\b/.test(low)) return t;          // b6 gate 2026-10-09 ("roof to team yellow and the rest exactly as it is" painted the whole car): 'the rest / everything else' is the PROTECTED part, never a whole-car order
        if (/\b(?:look\w*\s+(?:\w+\s+){0,3}with|ties?|tied|tying|fits?\s+(?:in\s+)?with|suits?|match(?:es)?|across|throughout)\s+(?:the\s+)?(?:whole|entire|overall|complete|full)\b/.test(low)) return t;          // hold probe 2026-10-09 ('it would look so sharp with the whole scheme', 'tie the whole livery together' are praise, not a whole-car target)
        if (!/\b(?:whole|entire|complete|full)\s+(?:car|body)\b|\ball[\s-]?over\b|\beverything\b|\ball\s+of\s+(?:it|the\s+(?:car|body))\b|\bthe\s+lot\b/.test(low) && !/\b(?:paint|make|do|turn|wrap|colou?r|recolou?r|spray|coat|dip|redo)\s+(?:the\s+|my\s+)?(?:car|body)\b/.test(low)) return t;          // the BODY word must be a real whole-car phrase ('between the body and the roof' is not one: train gate A-0235)
        var prot = [], body = low.replace(W23_PROT, function (m0) { for (var a = 1; a < arguments.length - 2; a++) { var x = arguments[a]; if (typeof x === 'string' && x && prot.indexOf(x) < 0) prot.push(x); } return ' '; });
        var exm = body.search(/\b(?:except|but\s+not|excluding|apart\s+from|other\s+than)\b/); if (exm >= 0) body = body.slice(0, exm);
        if (/\b(?:between|around|outline|border|pin\s*-?\s*(?:line|stripe)s?|pinlines?|pinstripes?|edges?|trim|lines?|stripes?|strips?|bands?|gradient|fade|split|two[\s-]?tone|checker\w*|half)\b/.test(body)) return t;          // a pinline / stripe / split order that mentions the body is not a whole-car order (train gate A-0235)
        var parts = []; try { parts = w21Parts(body) || []; } catch (e) { parts = []; }
        parts = parts.filter(function (p) { return /spoiler|wing|diffuser|splitter|mirror|bumper|roof|hood|trunk|fender|door|side/.test(p); });
        if (!parts.length || parts.length > 3) return t;
        var bsl = w23Sl(body) || [], looks = bsl.filter(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); });
        if (!looks.length || bsl.some(function (x) { return x.t === 'PAT'; }) || bsl.filter(function (x) { return x.t === 'COL'; }).length > 1 || bsl.filter(function (x) { return x.t === 'FIN'; }).length > 2) return t;
        var look = looks.map(function (x) { return String(x.s || x.v).replace(/^\s+|\s+$/g, ''); }).filter(function (x, i, a) { return a.indexOf(x) === i; }).join(' ');          // one slot per source ('pearl white' is both a colour and a finish word)
        var protTxt = prot.length ? ', except the ' + prot.join(' and the ').replace(/\b(number|sponsor|logo|decal|stripe|window|badge)\b/g, '$1s') : '';
        return 'make the whole car ' + look + parts.map(function (p) { return ' and the ' + p + ' ' + look; }).join('') + protTxt;          // shape tested on the planner: "make the whole car L and the spoiler L, except the numbers" runs body + part for every finish; the earlier "..., and make the spoiler L too" dropped the BODY step for 'flat black' (dev gate A-0167)
    }
    // W23U-ADD-BEGIN
    // ---- FEEL (orchestrator 2026-10-10, new-user QA "i hate the yellow"; kill noW23U_feel). A FEELING about the look with no instruction in it ("not feeling the yellow", "the yellow hurts my eyes", "im over the yellow", "can we lose the yellow",
    //   "this yellow is so loud", "i cant stand it") is a COMPLAINT: answer with options, change NOTHING. With a change on the table the live classifier called these 'neutral' ('correction' for a leading "not", 'tweak-complaint' for "too much") and the
    //   frame followed up the LAST change (re-applied it). A positive feeling ("love the yellow", "really like how the hood looks") is thanks. Sits in w15fSpeech right after the 'order' tests, so a fix verb with a look is still an order (cfix / cfix2),
    //   and any order verb, relative word (brighter, bigger, a bit), question mark or second look word bails: that is a tweak or an order for the planner, never a pure feeling.
    var W23_FEEL_NEG = /\b(?:hurts?\s+(?:my\s+)?eyes?|hurting\s+(?:my\s+)?eyes?|burns?\s+(?:my\s+)?eyes?|gives?\s+me\s+(?:a\s+)?(?:headache|migraine|the\s+creeps|vertigo)|makes?\s+me\s+(?:cringe|wince|sick|queasy|dizzy|gag)|(?:not|never|n'?t)\s+(?:really\s+|that\s+|too\s+|very\s+|quite\s+|so\s+|much\s+)*(?:feeling|vibing(?:\s+with)?|loving|liking|like|digging|into|a\s+fan\s+of|keen\s+on|sold\s+on|happy\s+with|crazy\s+(?:about|for)|wild\s+about|buying)|(?:i'?m|im|i\s+am|we'?re|were)\s+(?:so\s+|really\s+|totally\s+|kinda\s+|just\s+|honestly\s+)*(?:over|done\s+with|through\s+with|bored\s+(?:of|with)|tired\s+of|sick\s+of)|can'?t\s+(?:stand|look\s+at|stomach|deal\s+with|bear)|cannot\s+(?:stand|look\s+at)|(?:too|so|way\s+too|really|kinda)\s+(?:loud|harsh|garish|gaudy|obnoxious|obtrusive|aggressive|screaming|clashy|busy|flashy|tacky|cheesy|boring|bland)|(?:can|could)\s+(?:we|you|i)\s+(?:lose|ditch|drop|dump|axe|nix|kill|scrap|bin|toss)\s+(?:all\s+(?:of\s+)?)?(?:the|this|that|these|those|my)\s+\w+)\b/i;
    var W23_FEEL_NEG2 = /\b(?:(?:(?:i'?m|im|i\s+am|we'?re|so|kinda|kind\s+of|really|totally|just|honestly|pretty|quite)\s+)+(?:over|done\s+with|through\s+with|bored\s+(?:of|with)|tired\s+of|sick\s+of|fed\s+up\s+with)|over\s+it|not\s+(?:really\s+|quite\s+|exactly\s+)*(?:my\s+(?:thing|style|vibe|taste|cup\s+of\s+tea)|for\s+me|doing\s+it(?:\s+for\s+me)?|working(?:\s+for\s+me)?|cutting\s+it|clicking|landing|hitting|sitting\s+right)|(?:isn'?t|aren'?t|doesn'?t|don'?t|does\s+not|do\s+not)\s+(?:really\s+|quite\s+)*(?:do\s+it|doing\s+it|work|working|cut\s+it|click|land|hit|sit\s+right))\b/i;
    // cycle 2 (held-out probe, same finding): the experiencer / evaluation CONSTRUCTIONS, not single words: "<it> gives|giving|got me a <bad feeling>", "gone off <it>", "<it> isn't it / isn't me / not it", "i don't think <it> works",
    //   a negative interjection + a determiner ("eh the yellow", "yuck the yellow"), "<it> looks <negative adjective>"; positive: "<it> rocks / is perfect / looks amazing"
    var W23_FEEL_NEG3 = /\b(?:(?:gives?|giving|gave|got|causing|causes?|making|makes?|made)\s+me\s+(?:a\s+|an\s+|the\s+|some\s+)?(?:\w+\s+)?(?:headache|migraine|nausea|creeps|chills|vertigo|eye\s*strain|seasick|sick|dizzy|queasy|anxious|stress\w*|cringe|wince|gag|rash)|(?:gone|went|going)\s+off\s+(?:the|this|that|it|them)|(?:isn'?t|aren'?t|wasn'?t|is\s+not|are\s+not|not)\s+(?:really\s+|quite\s+|exactly\s+)*(?:it|me|the\s+one)|\bi\s+(?:don'?t|dont|do\s+not)\s+(?:really\s+)?(?:think|feel|reckon|believe)\b|(?:^|[\s,.!])(?:eh+|bleh|blah|yikes|oof|ew+|yuck|yucky|bah|pfft|urgh|argh)[\s,.!]+(?:the|this|that|these|those|my)\b|(?:looks?|looking|seems?|feels?|reads?)\s+(?:really\s+|so\s+|pretty\s+|kinda\s+|just\s+|very\s+|way\s+too\s+)*(?:bad|terrible|awful|horrible|tacky|cheap|ugly|gross|nasty|sickly|off|wrong|harsh|garish|gaudy|cringe|dated|tired|meh|rank|vile|hideous|dreadful|naff|trashy|childish|cheesy|weird))\b/i;
    var W23_FEEL_POS2 = /\b(?:the|this|that|it|they)\s+(?:\w+\s+){0,2}(?:rocks?|rules?|slaps?|kills?\s+it|pops?|is\s+(?:perfect|awesome|amazing|great|gorgeous|stunning|beautiful|fire|dope|killer|sweet|lovely|fantastic|brilliant|spot\s+on)|(?:looks?|looking|seems?)\s+(?:so\s+|really\s+|super\s+|pretty\s+|absolutely\s+)*(?:perfect|awesome|amazing|great|gorgeous|stunning|beautiful|fire|dope|killer|sweet|lovely|fantastic|brilliant|incredible|insane|mean|sick))\b/i;
    var W23_FEEL_POS = /\b(?:(?:i\s+|we\s+)?(?:really\s+|totally\s+|absolutely\s+|just\s+|actually\s+)*(?:love|loving|adore|adoring|dig|digging|enjoy|enjoying)\s+(?:the|this|that|these|those|my|our|how|it|them)\b|(?:i\s+|we\s+)(?:really\s+|totally\s+|actually\s+)*like\s+(?:the|this|that|these|those|how|it|them)\b|(?:happy|pleased|stoked|chuffed)\s+with\s+(?:the|this|that|it|how))/i;
    var W23_FEEL_ORD = /\b(?:make|mk|paint|turn|change|set|switch|recolou?r|colou?r|try|use|put|give|swap|replace|redo|add|apply|go\s+(?:with|for|to)|do|fix|lets|let'?s|should\s+be|want|wanna|need|would\s+like|i'?d\s+like|id\s+like|prefer|instead|rather|how\s+about|what\s+about|maybe|please|pls|keep|leave|undo|revert|back|if|but|and\s+then|then)\b/i;
    var W23_REL = /\b(?:bright\w*|dark\w*|light\w*|shin\w*|glossy|gloss|matte|dull\w*|big\w*|small\w*|large|thick\w*|thin(?:ner|nest|ly)?|wide\w*|narrow\w*|strong\w*|saturat\w*|vivid|intense|pale|faded|wash\w*|more|less|bit|little|tad|touch|slightly|lower|higher|subtle|tone|reduce|increase|decrease|metallic|chrome|pearl|candy|flat|satin|glitter|sparkl\w*)\b/i;
    var W23_CORR_LEAD = /^\s*(?:no+|nope|nah|wrong|wait|actually|oops|sorry|not\s+that(?:\s+one)?|not\s+quite)\b[\s,.!:;-]*/i;
    var W23_OPTCUE = /\bbefore\s+(?:i|we)\s+(?:choose|pick|decide|select|commit|go\s+with)\b|\b(?:show|give|offer|suggest|list|get|send|find)\s+(?:me|us)\s+(?:(?:some|a\s+few|a\s+couple(?:\s+of)?|few|any|several|other|better|more|different|nicer|decent|good)\s+)*(?:options?|alternatives?|ideas?|choices?|fixes|suggestions?|variants?|variations?|versions?|looks?|ones|something\s+(?:better|nicer|decent|good))\b|\b(?:suggest|offer|propose)\s+(?:a\s+few|a\s+couple(?:\s+of)?|some|any)\s+(?:\w+\s+)?(?:options?|alternatives?|ideas?|fixes|choices?)\b|\bwhat\s+(?:are\s+)?my\s+options\b/i;
    function w23Strong(x) { return W23_FEEL_NEG.test(x) || W23_FEEL_NEG2.test(x) || W23_FEEL_NEG3.test(x) || F15_HATE.test(x) || F15_NEGLIKE.test(x); }
    // ---- OPTS (round 2, orchestrator hidden set 2026-10-10; kill noW23U_feel): a COMPLAINT plus a request for choices ("this looks cheap, fix it up so its decent before i choose", "that looks awful, show me some options", "i hate the yellow, give me a few alternatives") asks for OPTIONS:
    //   live answered the encyclopedia article ("my car looks like plastic"), re-applied the last colour, or read 'not feeling it' as an undo. The turn becomes the canonical 'show me some other looks' (the planner lists ideas for the last part, or a list of finishes; nothing is changed).
    //   Bails: a real how-to, a correction lead, a feeling + order clause (w23FeelOrder owns it), a sentence that starts with a paint order, a complaint-less 'show me some options' (live already lists).
    function w23Opts(t) {
        if (w23Off('feel') || typeof t !== 'string' || !t || t.length > 120) return t;
        if (!W23_OPTCUE.test(t) || W23_HOWQ.test(t) || W23_CORR_LEAD.test(t)) return t;
        if (/^\s*(?:please\s+|pls\s+)?(?:make|paint|turn|change|set|switch|put|add|remove|delete|undo|revert)\b/i.test(t)) return t;
        if (!(w23Strong(t) || W21_CMPL.test(t))) return t;
        if (w23FeelOrder(t) !== t) return t;
        return 'show me some other looks';
    }
    function w23Feel(t, ctx) {
        if (w23Off('feel') || typeof t !== 'string' || !t || t.length > 90 || /\?/.test(t)) return null;
        t = t.replace(/\bmy\s+(?:bad|mistake|fault|error)\b/gi, ' ');          // cycle 3 (hold F_correct-0137-v2 "roof not tail, my bad"): an apology is not a complaint
        if (W23_OTHER_RE.test(t) && !w23OtherSide()) return { k: 'complaint', why: 'other23' };          // "no, the other side" with no single left / right edit to move: say so, never paint both sides
        if (!w23Off('feel') && w23FeelOrder(t) !== t) return { k: 'order', why: 'feelord23' };          // a feeling clause + an order clause with its own look = the order
        var strong = w23Strong;
        var ld = W23_CORR_LEAD.exec(t);          // cycle 3 (visible gates train A-0084 / aug A-0459 / A-0530): a CORRECTION lead ("no, trunk was wrong. Trunk is blue", "wrong, the wing must be white", "wrong, other way around") is a correction of the last change, never a feeling about a colour: only a strong feeling AFTER the lead counts
        if (ld && !strong(t.slice(ld[0].length))) return null;
        var neg = strong(t) || W21_CMPL.test(t), pos = !neg && (W23_FEEL_POS.test(t) || W23_FEEL_POS2.test(t));
        if (neg && !strong(t) && !ld) { var sl0 = w23Sl(t); if (sl0 && sl0.some(function (x) { return /^(?:PART|BODY)$/.test(x.t); }) && sl0.some(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); })) return null; }          // a mild evaluative word (wrong / bad / off / flat ...) in a sentence that names a part AND a look states that part's look = a correction / instruction, not a feeling
        if (!neg && !pos) return null;
        if (W23_HOWQ.test(t) || W23_FEEL_ORD.test(t) || W23_REL.test(t)) return null;
        var sl = w23Sl(t), seen = {}, n = 0;
        if (sl) sl.forEach(function (x) { if (/^(?:COL|FIN|PAT)$/.test(x.t)) { var k = x.t + ':' + String(x.v && (x.v.word || x.v.name) || x.s); if (!seen[k]) { seen[k] = 1; n++; } } });
        if (n > 1) return null;
        if (neg) return { k: 'complaint', why: 'feel23' };
        if (/\b(?:idea|thinking|think|thought|would|could|might|gonna|going\s+to|imagine|picture|id|i'?d|we'?d|wish|hope|hoping|want\w*|resemble|look\s+like|looks\s+like)\b|\b(?:love|like|prefer|adore)\s+(?:it|this|that|them)\s+(?:to|if|when)\b|\bto\s+(?:be|look|resemble|have|get|see|try|do|make|go)\b/.test(t) || W23_LIVN.test(t)) return null;          // cycle 3 (aug A-0081-p1 "id love it to resemble a Martini Racing livery"): a WISH ("i'd love it to ...", "i love to see ...") or a named livery is an order, never praise
        return (ctx && ctx.pending) ? null : { k: 'thanks', why: 'feel23pos' };
    }
    // ---- FEEL + ORDER (same QA finding, kill noW23U_feel): "i hate the yellow, make it red", "not feeling the yellow, try blue on the hood", "the yellow hurts my eyes, make it blue". The feeling clause names a COLOUR (not a part: W21's cfix owns
    //   "the hood is ugly, make it ..."), the order clause carries its own look, so the order is the sentence. Live re-applied the colour of the feeling clause (yellow) to the last part. Result = the order clause alone (the planner already resolves
    //   "make it red" / "try blue on the hood" / "go blue" against the last change).
    var W23_FO_B = /(?:[,;.!]\s*|\s+(?:so|and|then|but|just|now)\s+)((?:(?:please|pls|just|now|go\s+ahead\s+and|you\s+can|can\s+you|could\s+you)\s+)*(?:make|mk|paint|turn|change|set|switch|recolou?r|colou?r|try|use|put|give|go|swap|replace|redo)\b[^?]*)$/gi;
    var W23_HEADSTOP = /\b(?:i|im|i'm|we|you|me|my|the|this|that|these|those|it|its|it's|is|are|was|a|an|so|really|very|too|way|just|honestly|now|ugh|ew+|eh+|yuck|meh|oh|well|ok|okay|hmm+|and|but|colou?rs?|paint|shade|tone|look|looks|finish|one|all|of|to|on|in|with|at|for|lol|man|dude|bro|tbh|kinda|bit|pretty|quite|here|no|not|nah|yeah|sorry)\b/g;
    function w23HeadPure(head, hs) {
        var h = ' ' + String(head).toLowerCase() + ' ';
        [W23_FEEL_NEG, W23_FEEL_NEG2, W23_FEEL_NEG3, F15_HATE, F15_NEGLIKE, W21_CMPL].forEach(function (re) { h = h.replace(new RegExp(re.source, 'gi'), ' '); });
        (hs || []).forEach(function (x) { if (x && x.s) h = h.split(String(x.s).toLowerCase()).join(' '); });
        h = h.replace(W23_HEADSTOP, ' ').replace(/[^a-z\s]/g, ' ');
        return !/[a-z]{3,}/.test(h);
    }
    function w23FeelOrder(t) {
        if (w23Off('feel') || typeof t !== 'string' || t.length > 160 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var re = new RegExp(W23_FO_B.source, 'gi'), m, low = t.toLowerCase();
        while ((m = re.exec(low))) {
            var head = low.slice(0, m.index), tail = t.slice(m.index + (m[0].length - m[1].length)).replace(/[\s,;.!]*(?:please|pls|plz|thanks|thx|lol|lmao)?[\s.!]*$/i, '').trim();
            re.lastIndex = m.index + 1;
            if (head.split(/\s+/).filter(Boolean).length < 2 || !tail) continue;
            if (!(W23_FEEL_NEG.test(head) || W23_FEEL_NEG2.test(head) || F15_HATE.test(head) || F15_NEGLIKE.test(head) || W21_CMPL.test(head))) continue;
            if (W23_FEEL_ORD.test(head)) continue;
            var hs = w23Sl(head), ts = w23Sl(tail);
            if (!hs || !ts || hs.some(function (x) { return /^(?:PART|BODY|LAYER|NUMS|SPON)$/.test(x.t); })) continue;
            if (!ts.some(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); })) continue;
            if (!w23HeadPure(head, hs)) continue;          // cycle 3 (hold SA_complaint_fix-0088-v0 "front bmpr way too dull, make it chrome pls"): the feeling clause must name NOTHING but the look it dislikes; an unrecognised word (a mistyped part) may be the target, so the order keeps its whole text
            return tail;
        }
        return t;
    }
    // ---- RMV (orchestrator 2026-10-10, new-user QA "remove all the sponsors" painted every decal red; kill noW23U_remove). Remove / hide / delete / take off ON AN ELEMENT (sponsors, logos, decals, numbers) means HIDE it (or say how), never paint it:
    //   the live planner re-applied the colour remembered from the last edit to the layer ("make the hood red" then "remove all the sponsors" = red sponsors, twice). The canonical form is 'get rid of the <element>' (the planner answers with the hide-layer
    //   offer and changes nothing). The same verbs on a COLOUR ("ditch the yellow", "lose the yellow") re-applied the last change as well: 'get rid of the yellow' asks what should change. Exact full-text forms only (a part, a second look, a question = bail).
    var W23_RMV = '(?:remove|delete|erase|hide|take\\s+(?:off|away|out)|strip(?:\\s+(?:off|out|away))?|clear(?:\\s+(?:off|out|away))?|wipe(?:\\s+(?:off|out))?|get\\s+rid\\s+of|lose|ditch|drop|dump|axe|nix|kill|scrap|bin|toss|nuke|zap|cut(?:\\s+out)?|eliminate|do\\s+away\\s+with|knock\\s+off)';
    var W23_RELM = '(sponsors?(?:\\s+logos?)?|logos?|decals?|stickers?|numbers?|number\\s*(?:plate|panel)|lettering|graphics?)';
    var W23_RMV_LEAD = '^(?:(?:ok(?:ay)?|so|and|then|now|please|pls|plz|just|hey|ah|oh|can\\s+you|could\\s+you|will\\s+you|would\\s+you|can\\s+we|could\\s+we|let\\s+us|lets|let\\s*\'s|i\\s+want\\s+(?:you\\s+)?to|i\\s+wanna|i\\s+need\\s+you\\s+to|gotta|we\\s+need\\s+to|you\\s+should)[\\s,]+)*';
    var W23_RMV_TAIL = '(?:[\\s,]+(?:please|pls|plz|now|completely|entirely|altogether|for\\s+me|thanks|thx))*\\s*[.!]*\\s*$';
    var W23_RMV_RE1 = new RegExp(W23_RMV_LEAD + W23_RMV + '\\s+(?:all\\s+(?:of\\s+)?|every\\s+|each\\s+)?(?:the\\s+|my\\s+|our\\s+|these\\s+|those\\s+|that\\s+|this\\s+)?' + W23_RELM + '(?:\\s+(?:off|away|out))?(?:\\s+(?:of\\s+)?(?:the|my|this)\\s+(?:car|livery|paint|design|body|template|thing))?' + W23_RMV_TAIL, 'i');
    var W23_RMV_RE2 = new RegExp(W23_RMV_LEAD + '(?:take|get|pull|peel|rip|wipe|scrub|strip|clear|remove|delete|erase|hide)\\s+(?:all\\s+(?:of\\s+)?)?(?:the\\s+|my\\s+|our\\s+)' + W23_RELM + '\\s+(?:off|away|out)(?:\\s+(?:of\\s+)?(?:the|my|this)\\s+(?:car|livery|paint|design|body|template|thing))?' + W23_RMV_TAIL, 'i');
    var W23_RMV_RE5 = new RegExp(W23_RMV_LEAD + '(?:i\\s+)?(?:want|need|wanna|would\\s+like|\'?d\\s+like)\\s+(?:to\\s+(?:see\\s+)?)?(?:all\\s+(?:of\\s+)?)?(?:the|this|that|these|those|my)\\s+(.{2,24}?)\\s+(?:gone|removed|off|away|out|hidden)' + W23_RMV_TAIL, 'i');          // "i want the yellow gone", "i want the sponsors off"
    var W23_RMV_RE3 = new RegExp(W23_RMV_LEAD + '(?:make|turn|get|have)\\s+(?:all\\s+(?:of\\s+)?)?(?:the\\s+|my\\s+|our\\s+)' + W23_RELM + '\\s+(?:disappear|vanish|invisible|go\\s+away|gone|hidden|vanished)' + W23_RMV_TAIL, 'i');
    var W23_RMV_RE4 = new RegExp(W23_RMV_LEAD + W23_RMV + '\\s+(?:all\\s+(?:of\\s+)?)?(?:the|this|that|these|those|my)\\s+(.{2,24}?)' + W23_RMV_TAIL, 'i');
    function w23RmvWord(w) { w = w.toLowerCase().replace(/\s+/g, ' '); if (/^number/.test(w)) return 'numbers'; if (/^sponsor/.test(w)) return 'sponsors'; if (/^logo/.test(w)) return 'logos'; if (/^decal/.test(w)) return 'decals'; if (/^sticker/.test(w)) return 'stickers'; if (/^letter/.test(w)) return 'lettering'; return 'graphics'; }
    function w23Remove(t) {
        if (w23Off('remove') || typeof t !== 'string' || !t || t.length > 120 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var low = t.toLowerCase().replace(/[\u2018\u2019]/g, "'").replace(/\s+/g, ' ').trim(), m;
        m = W23_RMV_RE1.exec(low) || W23_RMV_RE2.exec(low) || W23_RMV_RE3.exec(low);
        if (!m) {
            var m5 = W23_RMV_RE5.exec(low);
            if (m5) {
                if (W23_ELEM.test(m5[1])) { var me = new RegExp(W23_RELM, 'i').exec(m5[1]); if (me) return 'get rid of the ' + w23RmvWord(me[1]); }
                else { var s5 = w23Sl(m5[1]); if (s5 && s5.length === 1 && s5[0].t === 'COL' && !s5[0].neg) return 'get rid of the ' + m5[1].trim(); }
            }
        }
        if (m) {
            if (/\b(?:how|why|what|where|when|which)\b/.test(low)) return t;
            return 'get rid of the ' + w23RmvWord(m[1]);
        }
        m = W23_RMV_RE4.exec(low);          // a COLOUR ("ditch the yellow"): one colour slot and nothing else
        if (m && !W23_ELEM.test(m[1])) {
            var sl = w23Sl(m[1]);
            if (sl && sl.length === 1 && sl[0].t === 'COL' && !sl[0].neg) return 'get rid of the ' + m[1].trim();
        }
        return t;
    }
    // ---- SIZE (orchestrator 2026-10-10, new-user QA "make the numbers bigger" -> 'Which texture should be bigger?', "make the 32 bigger" -> a stale roof question; kill noW23U_size). Numbers / sponsors / logos + a SIZE word is a RESIZE order on the ELEMENT
    //   (frame op: verb adjust, relative {prop 'scale', dir +-1}, target element); a literal car number ("the 32") is the numbers element. The frame already builds that op for 'make the <element> bigger'; the other wordings ("increase the size of the numbers",
    //   "enlarge the sponsors", "shrink the logo", "blow up the numbers", "scale up the 32", "make the 32 smaller") become that canonical sentence. The executor that grows / shrinks the layer is W20's (relative.prop 'scale' on an element target).
    var W23_SZE = '(numbers?|number\\s*(?:plate|panel)|digits?|sponsors?(?:\\s+logos?)?|logos?|decals?|stickers?)';
    var W23_SZN = '(?:number\\s+)?(\\d{1,3})';
    var W23_SZAMT = '(?:a\\s+(?:bit|little|touch|tad|lot)|slightly|somewhat|much|way|far|loads|massively)';
    var W23_SZUP = '(?:bigger|larger|huge|giant|massive|enormous|big|large)';
    var W23_SZDN = '(?:smaller|tiny|little|small|teeny|minuscule)';
    var W23_SZVU = '(?:enlarge|grow|expand|blow\\s+up|scale\\s+up|size\\s+up|upsize|inflate|beef\\s+up|bump\\s+up|increase)';
    var W23_SZVD = '(?:shrink|reduce|scale\\s+down|size\\s+down|downsize|decrease)';
    function w23SzOut(el, up, amt) { return 'make the ' + el + ' ' + (amt ? (/^(?:a\s|slightly|somewhat)/.test(amt) ? 'a bit ' : 'much ') : '') + (up ? 'bigger' : 'smaller'); }
    function w23Size(t) {
        if (w23Off('size') || typeof t !== 'string' || !t || t.length > 110 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var low = t.toLowerCase().replace(/[\u2018\u2019]/g, "'").replace(/\s+/g, ' ').trim(), m, lead = W23_RMV_LEAD, tail = '(?:[\\s,]+(?:please|pls|plz|now|for\\s+me|thanks|thx|a\\s+bit|a\\s+little|a\\s+touch|slightly|much|a\\s+lot))*\\s*[.!]*\\s*$';
        if (/\b(?:percent|%|px|pixels?|degrees?|times|inches|inch|cm|mm)\b/.test(low) || /\b(?:left|right|hood|roof|trunk|door|doors|side|sides|bumper|spoiler|wing|front|rear|back|stripe|stripes|red|blue|green|yellow|orange|white|black|gold|silver|chrome|matte|gloss|pink|purple)\b/.test(low)) return t;
        var el = null, up = null;
        function amtOf(s) { var a = /\b(?:a\s+(?:bit|little|touch|tad|lot)|slightly|somewhat|much|way|far|loads|massively)\b/.exec(s || ''); return a ? a[0] : null; }
        // 1. "increase the size of the numbers", "decrease the size of the sponsors"
        m = new RegExp(lead + '(increase|raise|boost|grow|enlarge|expand|up|decrease|reduce|lower|cut|shrink|scale\\s+up|scale\\s+down)\\s+the\\s+(?:size|scale)\\s+of\\s+(?:all\\s+(?:of\\s+)?)?(?:the|my|our)\\s+(?:car\\s+)?' + W23_SZE + tail, 'i').exec(low);
        if (m) { up = /^(?:increase|raise|boost|grow|enlarge|expand|up|scale\s+up)$/.test(m[1].trim()); return w23SzOut(w23RmvWord(m[2]), up, amtOf(low)); }
        // 2. "enlarge the sponsors", "shrink the logo", "blow up the numbers a bit", "scale up the 32"
        m = new RegExp(lead + '(' + W23_SZVU.slice(3, -1) + '|' + W23_SZVD.slice(3, -1) + ')\\s+(?:all\\s+(?:of\\s+)?)?(?:the|my|our)\\s+(?:car\\s+)?(?:' + W23_SZE + '|' + W23_SZN + ')(?:\\s+(?:a\\s+(?:bit|little|touch|tad|lot)|slightly|somewhat|much))?' + tail, 'i').exec(low);
        if (m) { up = new RegExp('^' + W23_SZVU + '$').test(m[1].trim()); el = m[2] ? w23RmvWord(m[2]) : 'numbers'; return w23SzOut(el, up, amtOf(low)); }
        // 3. "make the 32 bigger", "get the 32 smaller", "the 32 a bit bigger", "make my number 7 a lot bigger"
        m = new RegExp(lead + '(?:(?:make|get|have|turn)\\s+)?(?:the|my|our)\\s+' + W23_SZN + '\\s+(' + W23_SZAMT + '\\s+)?(' + W23_SZUP + '|' + W23_SZDN + ')' + tail, 'i').exec(low);
        if (m) { up = new RegExp('^' + W23_SZUP + '$').test(m[3]); return w23SzOut('numbers', up, m[2] ? m[2].trim() : amtOf(low)); }
        // 4. "make the numbers huge", "make the logo tiny" (adjective form; 'bigger / smaller' are the frame's own)
        m = new RegExp(lead + '(?:make|get|have|turn)\\s+(?:the|my|our)\\s+(?:car\\s+)?' + W23_SZE + '\\s+(' + W23_SZAMT + '\\s+)?(huge|giant|massive|enormous|tiny|teeny|minuscule)' + tail, 'i').exec(low);
        if (m) { up = /^(?:huge|giant|massive|enormous)$/.test(m[3]); return w23SzOut(w23RmvWord(m[1]), up, up ? 'much' : null); }
        // 5. "bigger numbers", "bigger numbers please", "smaller sponsors" are the frame's own (verified); "numbers bigger" too.
        return t;
    }
    // ---- OTHER (orchestrator 2026-10-10, new-user QA "no, the other side" ADDED a right-side stripe and kept the left one; kill noW23U_other). A correction MOVES the last thing; it does not add another: "no, the other side" after an edit on ONE side
    //   becomes "no, the <opposite> side" (the planner already retargets "no, the right side": the last change is popped first, undoFirst). Only when the last edit's targets name exactly one of left / right side; both / neither = bail (the planner asks).
    //   Without a correction marker ("now the other side") the planner keeps the first and adds the second, as asked.
    var W23_OTHER_RE = /^\s*(?:(?:no|nah|nope|wait|actually|oops|sorry|ugh|hmm+|not\s+that(?:\s+(?:side|one|door|fender|quarter|panel))?|wrong|wrong\s+(?:one|side)|i\s+meant|meant)[\s,.!:;-]+)+(?:(?:put|do|have|make|move|place|stick|go)\s+(?:it|that|them)\s+(?:on|to|onto|over\s+to)\s+|(?:on|to|onto)\s+|i\s+meant\s+)?(?:the\s+)?(?:other|opposite|opp|far|wrong)\s+(?:side|door|fender|quarter|panel)(?:\s+(?:instead|please|pls|though|then|not\s+this\s+one))?\s*[.!]*\s*$|^\s*(?:(?:put|do|have|make|move|place|stick)\s+(?:it|that|them)\s+(?:on|to|onto|over\s+to)\s+)?the\s+(?:other|opposite|far)\s+(?:side|door|fender|quarter|panel)\s+instead\s*[.!]*\s*$/i;
    function w23OtherSide() {
        try {
            var CVo = W.SpbConvo; if (!CVo || typeof CVo.lastEditCtx !== 'function') return null;
            var c = CVo.lastEditCtx({ skipTalk: true }), tg = c && c.targets; if (!tg || !tg.length) return null;
            var L = false, R = false; tg.forEach(function (x) { var p = String(x && x.part || ''); if (/^left/.test(p)) L = true; else if (/^right/.test(p)) R = true; });
            return L && !R ? 'right' : (R && !L ? 'left' : null);
        } catch (e) { return null; }
    }
    function w23OtherGraphic() {          // round 2 (NU2 O-004 lost vs the new live): the last edit was a stripe / graphic. The planner moves THOSE natively for the plain 'no, the other side' ("no, the right side" after a stripe asks 'no earlier change'), so the hook only canonicalises the wording there
        try {
            var CVg = W.SpbConvo, c = CVg && typeof CVg.lastEditCtx === 'function' ? CVg.lastEditCtx({ skipTalk: true }) : null, lo = c && c.act && c.act.lookObj;
            return !!(lo && (/^graphic/.test(String(lo.found || '')) || /^graphic/.test(String(lo.zone && lo.zone.finish || ''))));
        } catch (e) { return false; }
    }
    function w23Other(t) {
        if (w23Off('other') || typeof t !== 'string' || !t || t.length > 90 || /\?/.test(t) || !W23_OTHER_RE.test(t.toLowerCase())) return t;
        var side = w23OtherSide(); if (!side) return t;
        if (w23OtherGraphic()) return 'no, the other side';
        return 'no, the ' + side + ' side';
    }
    // ---- LIVERY (orchestrator 2026-10-10, new-user QA "gulf livery" / "martini racing livery" painted the whole car ONE flat colour; kill noW23U_livery). A named classic livery (Gulf, Martini, JPS, Rothmans, Marlboro, Castrol, Jagermeister, Repsol)
    //   is its OWN intent. (1) Bare phrasings ("gulf", "make it a gulf", "give me a gulf style paint job", "gulf scheme pls") are one canonical sentence, '<name> livery'. (2) The lexer reads 'gulf' as a light-blue COLOUR, which hid the THEMES palette
    //   (body + stripe) so the frame painted the body alone: with only the livery name in the text the THEMES ops now win (w23ThemeOnly). (3) The frame carries F.livery = { key, bare, body, stripes } for the named-livery recipe executor (W24), which
    //   should replace those two ops with the real scheme; until then the car gets body + stripe, never one flat colour.
    var W23_LIVN = /\b(gulf|martini|john\s+player(?:\s+special)?|jps|rothmans|marlboro|castrol|j[a\u00e4]germeister|j[a\u00e4]ger|repsol)\b/i;
    var W23_LIVFILL = /\b(?:please|pls|plz|gimme|give|me|make|it|the|car|a|an|my|our|paint|painting|job|style|styled|scheme|look|livery|liveries|theme|vibes?|colou?rs?|racing|team|in|like|as|i|want|would|love|to|looks?|dressed|dress|do|lets|let'?s|go|with|for|on|some|kind|of|sort|something|that|old|classic|original|famous|iconic|retro|vintage|one|and|just|can|you|could|get|put|wrap|wrapped|inspired|by|from|version|replica|tribute|special|racer|stock|proper|real|authentic|60s|70s|80s|1960s|1970s|sixties|seventies)\b/gi;
    function w23LiveryKey(f) { var m = W23_LIVN.exec(f); if (!m) return null; var k = m[1].toLowerCase().replace(/\s+/g, ' '); if (/^john player/.test(k)) return 'jps'; if (/^j.germeister|^j.ger$/.test(k)) return 'jagermeister'; return k; }
    function w23Livery(t) {
        if (w23Off('livery') || typeof t !== 'string' || !t || t.length > 80 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var low = t.toLowerCase().replace(/[\u2018\u2019]/g, "'"), key = w23LiveryKey(low); if (!key) return t;
        var rest = low.replace(W23_LIVN, ' ').replace(W23_LIVFILL, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
        if (rest) return t;
        var ks = w23Sl(key);          // a name the lexer reads as a COLOUR ('gulf' = light blue) is canonical as the bare name; the others as '<name> livery' (verified: the word 'livery' next to a colour-lexed name sends the rewritten turn to the how-to article)
        return (ks && ks.some(function (x) { return x.t === 'COL'; })) ? key : key + ' livery';
    }
    function w23ThemeOnly(f, th) {          // the only colour in the text is the livery's own name ('gulf' lexes as a light-blue COL)
        if (w23Off('livery') || !th || !W23_LIVN.test(f)) return false;
        var rem = f.replace(new RegExp(th[0].source, 'gi'), ' '), sl = w23Sl(rem);
        if (!sl) return false;
        return !sl.some(function (x) { return /^(?:COL|FIN|PAT|PART|NUMS|SPON|LAYER)$/.test(x.t); });
    }
    function w23LiveryTag(f, th, anyT) {
        var key = w23LiveryKey(f); if (!key || !th) return null;
        return { key: key, bare: !anyT && w23ThemeOnly(f, th), body: { word: th[1][0][0], hex: th[1][0][1] }, stripes: th[2].map(function (c) { return { word: c[0], hex: c[1] }; }) };
    }
    // ---- SUGG (round 2, orchestrator hidden set 2026-10-10; kill noW23U_sugg): "how bout a thin line down the hood?", "hw abt just some dots on the roof?", "how abt stripes?", "hows about a pearl finish", "what about flames on the doors".
    //   A (misspelt) "how about / what about / why not + a THING" is a SUGGESTION = order-ish, never a how-to question (live answered the encyclopedia article for 'how bout' / 'hw abt' and half of 'how about'). The suggestion becomes the plain order
    //   the planner already handles ("add a thin line down the hood" -> asks the stripe colour, "add some dots on the roof" -> acts, "add stripes" -> asks what / where); a part-led thing ("the roof in matte black") becomes "make ...". Bails: a real how-to
    //   (W23_HOWQ), a clause or gerund after the lead ("how about we try ...", "how about making it red"), an order / undo / size verb in the rest, a rest with no pattern / graphic / finish noun (a bare colour or part is a reply to the helper's question,
    //   the live fill handles it), a second question.
    var W23_SUGG_LEAD = /^\s*(?:(?:ok|okay|hey|so|and|well|um+|hmm+|but)[\s,]+)*(?:how(?:'?s)?\s*(?:a\s*)?(?:about|abt|bout|abuot|aboot|abut|abou)|hw\s*(?:a\s*)?(?:about|abt|bout|abuot|aboot|abut)|wh?at\s*(?:a\s*)?(?:about|abt|bout|abuot|aboot)|why\s+not(?:\s+try)?)\b[\s,:;-]*/i;
    var W23_SUGG_THING = /\b(?:stripes?|pinstripes?|lines?|bands?|ribbons?|strips?|dots?|polka|flames?|checker\w*|chequer\w*|camo\w*|gradients?|fades?|swirls?|waves?|chevrons?|stars?|lightning|bolts?|tribal|splatters?|spots?|speckles?|sparkl\w*|glitter\w*|pearl\w*|chrome|matte|gloss\w*|satin|metallic|carbon|candy|holo\w*|textures?|patterns?|decals?|graphics?|sunbursts?|plaid|hex\w*|honeycomb|snakeskin|leopard|zebra|marble|wood\s*grain)\b/i;
    var W23_SUGG_PART = /^(?:the\s+)?(?:hood|bonnet|roof|trunk|boot|spoiler|wing|bumper|sides?|doors?|fenders?|quarter\s+panels?|rear|front|car|body|whole\s+car)\b/i;
    var W23_SUGG_PLACE = /\b(?:hood|bonnet|roof|trunk|boot|spoiler|wing|bumpers?|sides?|doors?|fenders?|quarter\s+panels?|rear|front|mirrors?|pillars?|splitter|diffuser|skirts?|panels?|nose|tail|body|car|everywhere|centre|center|middle)\b|\b(?:on|onto|over|across|along|down|around)\s+(?:the\s+|my\s+|both\s+|each\s+)?\w+/i;
    function w23Osa(a, b) {          // optimal string alignment distance (substitution, insertion, deletion, adjacent swap) for the short lead words
        var i, j, c, d = [];
        for (i = 0; i <= a.length; i++) d[i] = [i];
        for (j = 1; j <= b.length; j++) d[0][j] = j;
        for (i = 1; i <= a.length; i++) for (j = 1; j <= b.length; j++) {
            c = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
            d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
            if (i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1)) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
        }
        return d[a.length][b.length];
    }
    function w23SuggFuzzy(t) {          // any spelling of 'how about' / 'what about' that the exact lead misses ("hwo about", "how aobut", "how 'bout", "wut abt", "whta about"): first word one edit from how / what (and starting h / w), second word within two of 'about'
        var m = /^\s*(?:(?:ok|okay|hey|so|and|well|um+|hmm+|but)[\s,]+)*([a-z]{2,5})(?:'s)?\s+(?:a\s+)?'?([a-z]{3,7})\b[\s,:;-]*/i.exec(t);
        if (!m) return null;
        var w1 = m[1].toLowerCase(), w2 = m[2].toLowerCase();
        var ok1 = (/^h/.test(w1) && (w1 === 'hows' || w23Osa(w1, 'how') <= 1)) || (/^w/.test(w1) && (w1 === 'whats' || w23Osa(w1, 'what') <= 1));
        if (!ok1) return null;
        if (!(w2 === 'abt' || w2 === 'bout' || (w2.length >= 4 && /^[ab]/.test(w2) && w23Osa(w2, 'about') <= 2))) return null;
        return m;
    }
    function w23Sugg(t) {
        if (w23Off('sugg') || typeof t !== 'string' || !t || t.length > 120) return t;
        var m = W23_SUGG_LEAD.exec(t) || w23SuggFuzzy(t); if (!m) return t;
        var rest = t.slice(m[0].length).replace(/[\s?!.]+$/, '').trim();
        if (!rest || rest.length > 80 || /\?/.test(rest) || W23_HOWQ.test(rest)) return t;
        if (/^(?:we|you|i|if|to|it|that|this|using|just\s+(?:doing|using)|maybe\s+(?:we|you|i)|(?:making|adding|painting|putting|giving|having|going|trying|doing|getting|turning|changing|switching|removing|keeping|moving|using|leaving|dropping|losing|swapping|replacing|undoing|reverting|restoring)\b)/i.test(rest)) return t;
        if (/\b(?:make|paint|turn|change|set|switch|remove|delete|undo|revert|restore|bigger|smaller|instead|rather|livery)\b/i.test(rest)) return t;
        if (!W23_SUGG_THING.test(rest)) { var sl = w23Sl(rest); if (!(sl && (sl.some(function (x) { return /^(?:FIN|PAT)$/.test(x.t); }) || (W23_SUGG_PART.test(rest) && sl.some(function (x) { return x.t === 'COL'; }))))) return t; }          // a part-led colour ("the trunk in gold") is a concrete order too; a bare colour or a bare part is a reply to the helper's own question
        rest = rest.replace(/^(?:just|maybe|perhaps|something\s+like|like|simply)\s+/i, '');
        if (W23_SUGG_PART.test(rest)) return 'make ' + rest;
        return 'add ' + rest + (W23_SUGG_PLACE.test(rest) ? '' : ' somewhere');          // no placement: 'somewhere' makes the planner ask where (it would otherwise default to the last part, or paint the whole body for camo / gradients)
    }
    // W23U-ADD-END
    function w23Pre(s) {          // EARLY (start of the w15fNorm chain, before the W15F / W21H rewrites that would otherwise mangle these orders): palette, undo, restore, chip reply, question + order, stripe words
        if (w23Off() || typeof s !== 'string' || !s) return s;
        var o = s, r;
        try {
            s = w23Pal(s);
            if ((r = w23Sugg(s)) !== s) return r;          // round 2: 'how bout / hw abt + a thing' suggestion = order-ish
            if ((r = w23Opts(s)) !== s) return r;          // round 2: a complaint + 'before i choose / show me some options' = options (a list / ask), never an article, an undo or a re-applied colour
            if ((r = w23HowUndo(s)) !== s) return r;          // round 3: a file / render mishap + a bare 'how undo' = the how-to question
            if ((r = w23Undo(s)) !== s) return r;
            if ((r = w23Restore(s)) !== s) return r;
            if ((r = w23FeelOrder(s)) !== s) return r;          // 2026-10-10 coordinator item 1 (feeling clause + order clause: the order wins)
            if ((r = w23Remove(s)) !== s) return r;          // 2026-10-10 coordinator item 2
            if ((r = w23Size(s)) !== s) return r;          // 2026-10-10 coordinator item 3
            if ((r = w23Other(s)) !== s) return r;          // 2026-10-10 coordinator item 4
            if ((r = w23Chip(s)) !== s) return r;
            s = w23Livery(s);          // 2026-10-10 coordinator item 5
            s = w23QO(s);
            s = w23Stripe(s);
        } catch (e) { return o; }
        return s;
    }
    function w23Norm(s) {          // LATE (after the W15F / W21H rewrites): whole-car + protection, spec shorthand, caution tails
        if (w23Off() || typeof s !== 'string' || !s) return s;
        var o = s;
        try {
            s = w23Whole(s);
            s = w23Spec(s);
            s = w23Tail(s);
        } catch (e) { return o; }
        return s;
    }
    var w23dbg = { lex: function (t, e) { return lex(t, e || {}); }, norm: function (t) { return w23Norm(w23Pre(t)); }, pre: function (t) { return w23Pre(t); }, late: function (t) { return w23Norm(t); }, pal: function (t) { return w23Pal(t); }, speech: function (t, c) { return w15fSpeech(t, c || {}); } };
    // W23U-END
    // W26U-BEGIN 2026-10-10 (lane W26-UNDERACT2; report: _easy_claude_work/eval/w26underact/PROGRESS.md). UNDER-ACTING, round 3: a clear order got a question (or an article) back. Every hook is a TEXT REWRITE to a canonical sentence the planner already acts on
    // (one hook, pct, adds a frame op). ONE kill switch: window.SPB_W26_OFF = true (node: env SPB_W26_OFF=1), SPB_OF_CFG.noW26, localStorage SPB_W26_OFF = '1'.
    // One hook off: SPB_OF_CFG.noW26_<self|angry|stripeoff|polite|mod|pct|pal|match|truck>. The hooks run at the head of w15fNorm (so the regex reader gets the same text through OF.syn); self + angry also run before r8Corr in frameOf.
    function w26Off(sub) {
        var ls = false, pe = false;
        try { ls = typeof localStorage !== 'undefined' && localStorage.getItem('SPB_W26_OFF') === '1'; } catch (e) { ls = false; }
        try { pe = typeof process !== 'undefined' && !!(process && process.env && process.env.SPB_W26_OFF && process.env.SPB_W26_OFF !== '0'); } catch (e2) { pe = false; }
        return !!(W.SPB_W26_OFF || pe || OF_CFG('noW26') || ls || (sub && OF_CFG('noW26_' + sub)));
    }
    var W26_ENV = null;
    function w26Said(cur) {          // the buyer's earlier turns of this chat, oldest first (the current turn, if the store already holds it, is dropped)
        try {
            var CV = W.SpbConvo, tt = CV && typeof CV.turns === 'function' ? CV.turns() : null; if (!tt || !tt.length) return [];
            var arr = tt.map(function (x) { return String((x && x.said) || ''); }).filter(Boolean);
            while (arr.length && cur != null && w21IsSelf(arr[arr.length - 1], cur)) arr.pop();
            return arr;
        } catch (e) { return []; }
    }
    function w26Parts(sl) { var out = []; (sl || []).forEach(function (x) { if (x.t !== 'PART') return; (x.parts && x.parts.length ? x.parts : [x.v]).forEach(function (p) { if (p && out.indexOf(p) < 0) out.push(p); }); }); return out; }
    function w26Trim(x) { return String(x || '').replace(/^[\s,.;:!?-]+|[\s,.;:!?-]+$/g, ''); }
    // ---- S1 (class 3, kill noW26_self): a change of mind INSIDE one message: "paint the whole car purple, actually no, just the hood purple", "make all of it gold wait only the doors", "roof green. no sorry, spoiler green", "hood red, no wait, the roof".
    //   Only the FINAL intent acts: the text before the retraction marker is dropped (live: the whole car + the hood were both painted). A final clause with its own look is used as it is; a final clause that only names a part
    //   ("only the doors", "hood only") takes the look of the first clause. A final clause with no part (a colour swap) is left to r8Corr, and so is an additive tail ("... and the roof too").
    var W26_SELFM = /(?:^|[,.;:!—-]\s*|\s+)(?:(?:oh\s+|um+\s+|hmm+\s+|ah\s+)?(?:no|nope|nah)[,.!\s]+(?:(?:actually|wait|sorry|hang\s+on|hold\s+on|hold\s+up|make\s+that|scratch\s+that|forget\s+(?:that|it)|never\s*mind|i\s+mean|just|only)[,.!\s]+)+|(?:actually|wait|hang\s+on|hold\s+on|hold\s+up|scratch\s+that|forget\s+that|never\s*mind(?:\s+that)?|on\s+second\s+thought|i\s+mean|my\s+bad|correction|ignore\s+that|sorry|make\s+that)(?:[,.!\s]+(?:no|nope|nah|wait|actually|scratch\s+that|forget\s+(?:that|it)|sorry|just|only))*[,.!\s]+)/gi;
    var W26_ADD = /\b(?:too|also|as\s+well|both|plus|in\s+addition|along\s+with|on\s+top\s+of)\b/i;
    function w26SelfTry(pre, post) {
        var ps = w23Sl(post), pr = w23Sl(pre); if (!ps || !pr) return null;
        if (ps.some(function (x) { return x.t === 'BODY'; })) return null;
        if (!ps.some(function (x) { return x.t === 'PART'; })) return null;
        var pLook = ps.filter(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); });
        var clean = w26Trim(post).replace(/^(?:just|only|then|so|and|but|make\s+it|make\s+that|do)\s+/i, '');
        if (pLook.length) {          // the correction is a full order
            if (W23_IMPV.test(clean.toLowerCase())) return clean;
            return 'make ' + (/^(?:the|my|our|both)\b/i.test(clean) ? '' : 'the ') + clean;
        }
        var preLook = pr.filter(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); });
        if (!preLook.length || preLook.length > 3) return null;
        var tgt = clean.replace(/\s+(?:only|please|pls|thanks|thank\s+you|instead|then|though|alone)\s*$/i, '').replace(/^(?:the|my|our)\s+/i, '');
        if (!tgt || tgt.split(/\s+/).length > 5) return null;
        var ts = w23Sl(tgt); if (!ts || ts.some(function (x) { return x.t !== 'PART'; })) return null;
        return 'make the ' + tgt + ' ' + preLook.map(function (x) { return String(x.s || x.v); }).join(' ');
    }
    function w26Self(t) {
        if (w26Off('self') || typeof t !== 'string' || t.length < 14 || t.length > 260 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var re = new RegExp(W26_SELFM.source, 'gi'), m, best = null;
        while ((m = re.exec(t))) {
            if (!m[0].length) { re.lastIndex++; continue; }
            var pre = t.slice(0, m.index), post = t.slice(m.index + m[0].length);
            if (pre.replace(/[\s,.;:!-]+/g, '').length < 6 || post.replace(/[\s,.;:!-]+/g, '').length < 3) continue;
            if (/\b(?:and|then|also|plus|but|or|so|because)[\s,]*$/i.test(pre) || W26_ADD.test(post)) continue;
            var cand = w26SelfTry(pre, post); if (cand) best = cand;          // the LAST usable marker wins
        }
        return best || t;
    }
    // ---- S2 (class 4, kill noW26_angry): an angry correction that NAMES the wrong part: "no!! that's the roof, I said the bonnet", "you painted the spoiler, I told you the front bumper", "ugh that is the boot, I said the hood".
    //   The planner already retargets "no, I said the bonnet" (the last change is taken back, then the order is redone on the named part); the wrong-part clause hid it from every reader. Needs an edit in this chat.
    var W26_ANG = /^(.*?)(?:^|[\s,.;!-])(?:that(?:'?s|\s+is|\s+was)|thats|it(?:'?s|\s+is|\s+was)|this\s+is|you\s+(?:just\s+)?(?:painted|did|made|coloured|colored|changed|put\s+it\s+on|did\s+it\s+on)|you(?:'ve|\s+have)\s+(?:just\s+)?(?:painted|done|changed|coloured|colored))\s+(?:it\s+on\s+)?(?:the\s+|my\s+|our\s+)?(.{2,30}?)\s*[,.;!:-]+\s*(?:(?:but|no|and|ugh|argh|dude|man|come\s+on)[\s,]+)*(?:i|we)\s+(?:clearly\s+|just\s+|literally\s+)?(?:said|told\s+you|meant|wanted|asked\s+for|asked|want(?:ed)?|was\s+(?:talking|referring)\s+(?:about|to)|specifically\s+(?:said|asked\s+for))\s+(?:you\s+)?(?:for\s+)?(?:the\s+|my\s+|our\s+)?(.{2,40}?)[\s.!?]*$/i;
    function w26Angry(t) {
        if (w26Off('angry') || typeof t !== 'string' || t.length > 220 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var m = W26_ANG.exec(t); if (!m) return t;
        if (!w23HasEdit()) return t;
        var a = w23Sl(m[2]), b = w23Sl(m[3]); if (!a || !b) return t;
        var ap = w26Parts(a), bp = w26Parts(b);
        if (!bp.length || (ap.length && ap.join() === bp.join()) || b.some(function (x) { return x.t === 'BODY'; })) return t;
        if (!ap.length && m[2].split(/\s+/).length > 3) return t;
        var lp = w26LastParts();          // gate 2026-10-10 (train A-0138 "THATS THE TRUNK. I said ROOF" after "roof chrome": the roof already IS the last change, so there is nothing to move; left to the reader as before)
        if (lp.length && ap.length && !ap.some(function (p) { return lp.indexOf(p) >= 0; }) && bp.every(function (p) { return lp.indexOf(p) >= 0; })) return t;
        return 'no, I said the ' + w26Trim(m[3]).replace(/^(?:the|my|our)\s+/i, '');
    }
    function w26Early(t) { try { if (w26Off()) return t; var r = w26Self(t); if (r !== t) return r; return w26Angry(t); } catch (e) { return t; } }
    // ---- S3 (class 5, kill noW26_stripeoff): take a STRIPE off. "remove the blue stripe", "could you take the stripe off? dont want it", "would you mind removing that stripe" asked what to change / answered with an article; the planner undoes the
    //   last stripe for "get rid of that stripe". Needs the buyer's previous turn to be about a stripe / line / band (nothing else is undone by a word about a stripe).
    var W26_STRIPEOFF = /^\s*(?:(?:and|then|ok(?:ay)?|now|so|please|pls|hey|hi)[\s,]+)*(?:(?:could|can|would|will)\s+(?:you|we|u)\s+(?:please\s+|pls\s+|just\s+|possibly\s+|kindly\s+)*|would\s+you\s+mind\s+|do\s+you\s+mind\s+|any\s+chance\s+you\s+could\s+)?(?:take|taking|get|getting|peel|peeling|rip|ripping|strip|stripping|remove|removing|delete|deleting|erase|erasing|wipe|wiping|scrap|scrapping|ditch|ditching|drop|dropping|kill|killing|lose|losing)\s+(?:off\s+|away\s+|out\s+)?(?:rid\s+of\s+)?(?:all\s+(?:of\s+)?)?(?:the|that|this|my|our|those|these)\s+(?:[a-z]+\s+){0,2}?(?:racing\s+|pin\s*)?(?:stripes?|pinstripes?|pin\s*lines?|lines?|bands?)(?:\s+(?:off|away|out|again|altogether|completely))?\b/i;
    var W26_REASON = /^[\s,;.!?]*(?:(?:i|we)\s+(?:do\s*n'?t|do\s+not|no\s+longer)\s+(?:want|like|need)\s+(?:it|that|them|this)|(?:dont|don't)\s+(?:want|like|need)\s+(?:it|that|them|this)|it'?s\s+(?:ugly|wrong|bad|too\s+\w+|not\s+\w+)|(?:it|that)\s+(?:looks?|is)\s+(?:ugly|wrong|bad|off|awful|terrible)|thanks|thank\s+you|cheers|please|pls|plz|ta|for\s+me|if\s+(?:you\s+can|possible|that'?s\s+ok))?[\s,;.!?]*$/i;
    function w26StripeOff(t) {
        if (w26Off('stripeoff') || typeof t !== 'string' || t.length > 160 || W23_HOWQ.test(t)) return t;
        var m = W26_STRIPEOFF.exec(t); if (!m) return t;
        if (!W26_REASON.test(t.slice(m.index + m[0].length).replace(/^\s*(?:off|away|out)\b/i, ''))) return t;
        if (/\b(?:how|why|what|where|which)\b/i.test(t)) return t;
        var pv = w26Said(t), last = pv.length ? pv[pv.length - 1] : '';
        if (!last || !/\b(?:stripes?|pinstripes?|pin\s*lines?|lines?|bands?)\b/i.test(last)) return t;
        return 'get rid of that stripe';
    }
    // ---- S4 (class 5, kill noW26_polite): a polite removal / restore / undo-all phrased as a question: "can we put the roof back how it was?", "would you mind undoing everything since I started, cheers", "any chance you could take that last change back".
    //   The lead (can / could / would you (mind) / any chance / is it possible to) and the courtesy tail are cut and the bare imperative goes on: the undo / restore readers (W23) and the 'undo everything' reader already act on it.
    //   A how-to (how / in this app / render / file / button) and a first-person "can I" are NOT touched.
    var W26_PLEAD = /^\s*(?:(?:hi|hey|hello|ok(?:ay)?|so|um+|well|please|pls|and|then|now)[\s,!.]+)*(?:would\s+(?:you|u)\s+mind\s+|do\s+(?:you|u)\s+mind\s+|(?:could|can|would|will)\s+(?:you|we|u|ya)\s+(?:please\s+|pls\s+|possibly\s+|maybe\s+|just\s+|kindly\s+|quickly\s+)*(?:be\s+able\s+to\s+)?|would\s+it\s+be\s+possible\s+to\s+|is\s+it\s+possible\s+to\s+(?=(?:take|put|get|remove|swap|change|make|turn|set)\b)|any\s+chance\s+(?:you\s+(?:could|can)\s+|of\s+)|i(?:'d|\s+would)\s+(?:like|love|appreciate)\s+(?:it\s+)?if\s+(?:you|we)\s+(?:could|would|can)\s+)/i;
    var W26_GER = { undoing: 'undo', removing: 'remove', taking: 'take', getting: 'get', deleting: 'delete', putting: 'put', going: 'go', reverting: 'revert', restoring: 'restore', resetting: 'reset', rolling: 'roll', bringing: 'bring', scrapping: 'scrap', dropping: 'drop' };
    var W26_RVV = /^(?:undo|take|get|put|go|revert|restore|reset|roll|bring|scrap|drop|set|change|switch|turn|remove|delete|wipe)\b/i;
    var W26_RESTW = /\b(?:back|undo|revert|restore|reset|roll\s*back|rewind|original|previous|before|as\s+it\s+was|the\s+way\s+it\s+was)\b/i;
    var W26_ALL = /^(?:undo|take\s+back|revert|roll\s*back|reset|scrap|wipe(?:\s+out)?|clear)\s+(?:absolutely\s+)?(?:everything|all(?:\s+(?:of\s+)?(?:it|that|this|my\s+changes|the\s+changes|these\s+changes|our\s+changes))?|every\s+(?:change|edit))(?:\s+(?:since\s+(?:i|we)\s+(?:started|began)|so\s+far|(?:i|we)\s+(?:did|made|have\s+done|started)|from\s+(?:the\s+)?(?:start|beginning)|up\s+to\s+now))*\s*$/i;
    function w26Polite(t) {
        if (w26Off('polite') || typeof t !== 'string' || t.length > 200) return t;
        var m = W26_PLEAD.exec(t); if (!m) return t;
        if (/\b(?:render|export|save|saving|file|files|iracing|trading\s*paints|app|software|button|menu|tab|download|upload|tga|psd|layer\s*panel|slider)\b/i.test(t)) return t;
        var rest = t.slice(m[0].length), gm = /^(\w+ing)\b/i.exec(rest);
        if (gm && W26_GER[gm[1].toLowerCase()]) rest = W26_GER[gm[1].toLowerCase()] + rest.slice(gm[1].length);
        if (!W26_RVV.test(rest) || W23_HOWQ.test(rest)) return t;
        rest = rest.replace(/[\s,;.!?]*(?:(?:thanks|thank\s+you|thx|cheers|ta|much\s+appreciated)(?:\s+(?:so\s+much|a\s+lot|mate|man))?|if\s+(?:that'?s\s+)?(?:ok|okay|possible|you\s+can)|please|pls|plz|for\s+me)[\s,;.!?]*$/i, '').replace(/[\s?]+$/, '');
        rest = rest.replace(/\bhow\s+(?:it|they)\s+(?:was|were|used\s+to\s+be)\b/i, 'the way it was').replace(/\bas\s+(?:it|they)\s+(?:was|were)\b/i, 'the way it was');
        if (!rest || !W26_RESTW.test(rest) || /\b(?:how|why|what|which|where)\b/i.test(rest)) return t;
        if (W26_ALL.test(rest)) return 'undo everything';
        return w26BackPart(rest);
    }
    function w26LastParts() { try { var CV = W.SpbConvo, c = CV && typeof CV.lastEditCtx === 'function' ? CV.lastEditCtx({ skipTalk: true }) : null, out = []; ((c && c.targets) || []).forEach(function (x) { (x.parts || (x.part ? [x.part] : [])).forEach(function (p) { if (out.indexOf(p) < 0) out.push(p); }); }); return out; } catch (e) { return []; } }
    function w26BackPart(rest) {          // "put the roof back the way it was": when the roof IS the last change, that is one undo (the part-restore reader refuses 'how it was'); anything else stays as it was
        var m = /^(?:put|set|bring|get|take|move|change|turn)\s+(?:the\s+|my\s+|our\s+)?(.+?)\s+back(?:\s+(?:to\s+)?(?:the\s+way\s+it\s+was|how\s+it\s+was|as\s+it\s+was|how\s+they\s+were|normal|the\s+original|original|before|as\s+before))?$/i.exec(rest);
        if (!m) return rest;
        var sl = w23Sl(m[1]); if (!sl || sl.some(function (x) { return x.t !== 'PART'; })) return rest;
        var ps = w26Parts(sl), lp = w26LastParts();
        return ps.length && lp.length === ps.length && ps.every(function (p) { return lp.indexOf(p) >= 0; }) ? 'undo that' : rest;
    }
    function w26Back(t) {          // the same without the polite lead ("put the roof back how it was"): only the 'how it was / as it was / as before' wording the part-restore reader refuses
        if (w26Off('polite') || typeof t !== 'string' || t.length > 100 || /\?/.test(t) || !/\b(?:how\s+(?:it|they)\s+(?:was|were)|as\s+(?:it|they)\s+(?:was|were)|as\s+before)\b/i.test(t) || /\b(?:how|why|what|which|where)\s+(?!(?:it|they)\s+(?:was|were))/i.test(t)) return t;
        var r = w26BackPart(w26Trim(t).replace(/\bhow\s+(?:it|they)\s+(?:was|were)\b/i, 'the way it was').replace(/\bas\s+(?:it|they)\s+(?:was|were)\b/i, 'the way it was').replace(/\bas\s+before\b/i, 'before').replace(/^(?:please|pls|ok(?:ay)?|now)\s+/i, ''));
        return r === 'undo that' ? r : t;
    }
    // ---- class 4 (kill noW26_rest), 2026-10-10 in-app K7 ("hood red", "roof blue", "back to the original colour on the hood" = "Undone: roof blue", the LAST change, not the hood): a restore that NAMES a part is that part's own restore, never a generic undo.
    //   "back to the original colour on the hood" / "restore the hood" / "revert the hood" / "reset the hood" / "return the hood to its original look" / "change the hood back to the original colour".
    //   The part IS the last change = 'undo that' (the same one step); any other part = "put the <part> back to the original colour" (the part-restore reader, w17Orig, restores it and nothing else). Needs an edit in this chat.
    var W26_RSLEAD = /^(?:(?:ok(?:ay)?|so|now|and|then|please|pls|just|can\s+you|could\s+you|can\s+we|could\s+we|would\s+you|lets?|let's)[\s,]+)*/i;
    var W26_ORIGW = '(?:the\\s+|its\\s+|their\\s+)?(?:original|old|previous|factory|stock|starting|first|normal|default)(?:\\s+(?:colou?rs?|paint|look|finish|shade|scheme))?';
    var W26_RS1 = new RegExp('^(?:(?:go|get|put|bring|take|switch|change|turn)\\s+)?back\\s+(?:to\\s+)?' + W26_ORIGW + '\\s+(?:on|for|of|in)\\s+(?:the\\s+|my\\s+|our\\s+)?(.{3,40})$', 'i');
    var W26_RS2 = new RegExp('^(?:restore|revert|reset|undo)\\s+(?:the\\s+|my\\s+|our\\s+)?(.{3,40}?)(?:\\s+(?:back\\s+)?(?:to\\s+)?' + W26_ORIGW + ')?$', 'i');
    var W26_RS3 = new RegExp('^(?:return|change|turn|switch|set|put|bring|get)\\s+(?:the\\s+|my\\s+|our\\s+)?(.{3,40}?)\\s+(?:back\\s+)?to\\s+' + W26_ORIGW + '$', 'i');
    function w26Restore(t) {
        if (w26Off('rest') || typeof t !== 'string' || t.length > 100 || /\?/.test(t) || !w23HasEdit()) return t;
        var x = w26Trim(t).replace(W26_RSLEAD, '').replace(/[\s,]+(?:please|pls|thanks|thank\s+you)$/i, ''), m = W26_RS1.exec(x) || W26_RS3.exec(x) || W26_RS2.exec(x);
        if (!m) return t;
        var sl = w23Sl(m[1]); if (!sl || !sl.length || sl.some(function (c) { return c.t !== 'PART' || c.neg || c.exc; })) return t;
        var ps = w26Parts(sl); if (!ps.length) return t;
        var lp = w26LastParts();
        if (ps.length === lp.length && ps.every(function (p) { return lp.indexOf(p) >= 0; })) return 'undo that';
        return 'put the ' + ps.join(' and the ') + ' back to the original colour';
    }
    // ---- S5 (class 1, kill noW26_mod): bare follow-up modifiers on the LAST target. "too much, go matte" / "too bright, make it satin" (the 'too much' complaint hid the finish order), "lighter, like a sky blue" / "darker, like navy"
    //   (= make it sky blue), "less mirror-y" (the word 'mirror' read as the mirrors part: = less shiny). All need an edit in this chat (the 'it' they act on).
    var W26_TOO = /^\s*(?:(?:hmm+|ok(?:ay)?|ah+|oh+|um+|nah|no|ugh|so)[\s,.!]+)*(?:(?:that'?s|it'?s|this\s+is|thats|its)\s+)?(?:(?:a\s+)?(?:bit|little|touch|tad)\s+|way\s+|waay\s+|so\s+|far\s+|just\s+|kinda\s+)*too\s+(?:much|[a-z]+)(?:\s+(?:now|though|for\s+me))?\s*[,.;:!-]+\s*((?:(?:ok(?:ay)?|so|then|just|now|please|pls)\s+)*(?:go|make\s+it|switch(?:\s+it)?\s+to|try|use|change\s+it\s+to|turn\s+it|set\s+it\s+to|how\s+about|what\s+about|let'?s\s+(?:go|try)|lets\s+(?:go|try))\b[\s\S]*)$/i;
    var W26_LIKE = /^\s*(?:(?:hmm+|ok(?:ay)?|and|now|so)[\s,]+)*(?:(?:a\s+)?(?:bit|little|touch)\s+|slightly\s+)?(?:lighter|darker|paler|brighter|deeper|softer|warmer|cooler|bolder)\s*[,;-]?\s*(?:like|more\s+like|maybe|say|something\s+like|as\s+in|such\s+as|kind\s+of|sort\s+of|think)\s+(?:a\s+|an\s+|the\s+)?([a-z #0-9]{3,24}?)[\s.!]*$/i;
    // ---- class 1 (kill noW26_toocol), 2026-10-10 in-app K1 ("hood orange" then "too orange now" = strength 100 -> 75%, nothing visible) + probe ("too dark now" / "too shiny now" / "too big now" = an ARTICLE, "too dull" / "too busy" / "too bold" = "What should change?"):
    //   "too <colour|adjective> (now)" right after a change is an order on the LAST change, in the direction the complaint points. One mapping (also read by answer.js's w4aPre through OF.w26Too):
    //   dark -> lighter, bright / light -> darker, a colour word / vivid / neon / garish -> softer (saturation down), big / huge / coarse -> smaller, small / tiny -> bigger. Shine / gloss / matte / flat / dull / busy / subtle / faint complaints are NOT mapped (the owner's restraint rule: a complaint is answered, fixes offered, wait).
    var W26_TOOHEAD = /^\s*(?:(?:hmm+|ok(?:ay)?|ah+|oh+|um+|nah|no|ugh|so|now|and)[\s,.!]+)*(?:(?:that'?s|it'?s|this\s+is|thats|its|it\s+is|that\s+is|it\s+looks|that\s+looks|now\s+it'?s|now\s+its)\s+)?(?:(?:a\s+)?(?:bit|little|touch|tad)\s+|way\s+|waay\s+|so\s+|far\s+|just\s+|kinda\s+|slightly\s+|really\s+|much\s+)*too\s+/i;
    var W26_TOOTAIL = /^(?:\s+(?:now|already|still|again|though|for\s+me|on\s+there|there|here))*[\s.!]*$/i;
    var W26_TOOCOLW = /^(?:red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|brown|cyan|magenta)$/i;
    var W26_TOOMAP = [[/^(?:dark|dim|murky|deep)$/i, 'a bit lighter'], [/^(?:bright|light|pale-?ish)$/i, 'a bit darker'], [/^(?:vivid|saturated|neon|garish|gaudy|flashy|harsh|punchy)$/i, 'a bit softer'],
        [/^(?:big|large|huge|chunky|coarse|giant|oversized)$/i, 'a bit smaller'], [/^(?:small|tiny|fine|minute)$/i, 'a bit bigger']];
    //   NOT mapped on purpose (train A-0333 / A-0495, owner restraint rule 2 "a complaint is answered, fixes are offered, then wait"): shine / gloss / matte / flat / dull / busy / subtle / faint complaints keep the existing ask that names the options
    function w26Too(t) {
        if (w26Off('toocol') || typeof t !== 'string' || t.length > 70 || /\?/.test(t)) return null;
        var m = W26_TOOHEAD.exec(t); if (!m) return null;
        var rest = t.slice(m[0].length);
        var am =/^([a-z]+(?:\s+out)?)(.*)$/i.exec(rest); if (!am || !W26_TOOTAIL.test(am[2])) return null;
        var w = am[1].toLowerCase(); if (W26_TOOCOLW.test(w)) return 'a bit softer';
        for (var i = 0; i < W26_TOOMAP.length; i++) if (W26_TOOMAP[i][0].test(w)) return W26_TOOMAP[i][1];
        return null;
    }
    // ---- class 1 (kill noW26_numsz), 2026-10-10 coordinator: "make them bigger" / "now bigger" / "even bigger" / "smaller again" right after a change to the NUMBERS (live: asked "Which part should I make bigger?", re-applied the white, or "The numbers has no pattern to resize").
    //   The last change targets only the numbers -> "make the numbers bigger|smaller" (the size reader that already works when the buyer names the numbers: 'numbers>shine:bigger (25% larger)').
    var W26_NUMSZ = /^\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls|hmm+|ah+|just)[\s,]+)*(?:(?:can|could)\s+(?:you|we)\s+)?(?:(?:make|get|have|let'?s\s+make|go)\s+(?:it|them|that|those|the\s+(?:numbers?|digits?))\s+)?(?:(?:a\s+)?(?:bit|little|touch|tad|lot|tiny\s+bit)\s+|slightly\s+|much\s+|way\s+|even\s+|still\s+|that\s+bit\s+|just\s+)*(bigger|larger|smaller)(?:\s+(?:again|still|please|pls|now|then|though|too|yet|more))*\s*[.!]*\s*$/i;
    function w26NumSize(t) {
        if (w26Off('numsz') || typeof t !== 'string' || t.length > 70 || /\?/.test(t)) return null;
        var m = W26_NUMSZ.exec(t); if (!m) return null;
        try { var CV = W.SpbConvo, c = CV && typeof CV.lastEditCtx === 'function' ? CV.lastEditCtx({ skipTalk: true }) : null, tg = c && c.targets; if (!tg || tg.length !== 1 || tg[0].kind !== 'numbers') return null; } catch (e) { return null; }
        return 'make the numbers ' + (/^sm/i.test(m[1]) ? 'smaller' : 'bigger');
    }
    function w26Mod(t) {
        if (w26Off('mod') || typeof t !== 'string' || t.length > 160 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        var m = W26_TOO.exec(t);
        if (m) {
            if (!w23HasEdit()) return t;
            var ord = w26Trim(m[1]), os = w23Sl(ord); if (!os || !os.some(function (x) { return /^(?:COL|FIN|PAT)$/.test(x.t); }) || os.some(function (x) { return x.t === 'PART' || x.t === 'BODY' || x.t === 'LAYER'; })) return t;
            return ord;
        }
        m = W26_LIKE.exec(t);
        if (m) {
            if (!w23HasEdit()) return t;
            var cs = w23Sl(m[1]); if (!cs || cs.length !== 1 || cs[0].t !== 'COL') return t;
            return 'make it ' + w26Trim(m[1]);
        }
        if (/\b(?:less|not\s+as|not\s+so)\s+mirror[\s-]?(?:y|like)\b|\b(?:bit|little|touch)\s+less\s+mirror[\s-]?(?:y|like)\b/i.test(t) && w23HasEdit()) return t.replace(/\bmirror[\s-]?(?:y|like)\b/ig, 'shiny');
        // 2026-10-10 (coordinator classes, in-app): "give it a glow" / "add a neon glow" / "a bit of glow" after a change = "make it glow" (asked "What should change, and where?"); "too orange now" / "way too blue" = less of that colour
        if (W26_GLOW.test(t) && w23HasEdit()) return 'make it glow';
        var tj = w23HasEdit() ? w26Too(t) : null; if (tj) return tj;          // W26U 2026-10-10: "too orange now" / "too dark now" / "too shiny" after a change = the matching relative order (see w26Too)
        return t;
    }
    var W26_GLOW = /^\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls)[\s,]+)*(?:(?:can|could|would)\s+(?:you|we)\s+)?(?:give\s+(?:it|that|this)\s+(?:a\s+|some\s+)?(?:(?:bit|touch|little|hint)\s+of\s+)?(?:(?:soft|subtle|neon|slight|nice|cool)\s+)?glow|add\s+(?:a\s+|some\s+)?(?:(?:bit|touch|little|hint)\s+of\s+)?(?:(?:soft|subtle|neon|slight|nice|cool)\s+)?glow(?:\s+to\s+(?:it|that|this))?|(?:a\s+)?(?:bit|touch|little|hint)\s+of\s+glow|(?:put|throw)\s+(?:a\s+)?glow\s+on\s+(?:it|that|this))(?:\s+(?:please|pls|too|as\s+well|now))*[\s.!]*$/i;
    function w26Obj(F) {          // class 5 (kill noW26_mirror): a mirror asked for on a car map with no mirror part = the object target carries the nearest part (the sides), so the planner says so once and offers "all of the sides" instead of only "draw a box"
        try {
            if (w26Off('mirror') || !F || !F.ops) return;
            var ps = (W26_ENV && Array.isArray(W26_ENV.parts)) ? W26_ENV.parts : [];
            if (ps.some(function (p) { return /mirror/i.test(String(p)); })) return;
            var near = ['left side', 'right side'].filter(function (p) { return !ps.length || ps.indexOf(p) >= 0; });
            if (!near.length) return;
            F.ops.forEach(function (op) { var T = op && op.target; if (T && T.kind === 'object' && /mirror/i.test(String(T.object || '')) && !(T.parts && T.parts.length)) T.parts = near; });
        } catch (e) {}
    }
    // ---- class 1 (kill noW26_mult), 2026-10-10 in-app K3 ("camo on the hood" then "halve the camo size" re-applied the same camo: 'I ran it, but nothing visible changed'): a MULTIPLICATIVE size follow-up on the last change.
    //   "halve it" / "halve the camo size" / "make it half the size" / "half as big" / "cut it in half" / "double the size" / "twice as big" / "make the camo three times bigger" / "make it 30% smaller" / "shrink it by 20%".
    //   Rewritten to "make it smaller|bigger" (or "make the <thing> smaller|bigger"), W26_MULTV carries the factor; the post-frame step w26MultOps puts it on the scale relative (the planner's factor() honours a number).
    //   Needs a last change (w23HasEdit); a bare "double it" / "half the car" are NOT size orders (no size word) and are left alone.
    var W26_MULTV = null, W26_MULTT = 0;          // the factor + when it was read: answer.js re-writes the text between the reader (OF.syn / correct) and the frame (route4f), so the factor outlives the text for ~3 s (one turn)
    function w26Mult(t) {
        if (w26Off('mult') || typeof t !== 'string' || t.length > 90 || /\?/.test(t) || !w23HasEdit()) return t;
        var s = t.replace(/[.!\s]+$/, ''), LEAD = '(?:(?:ok(?:ay)?|so|now|and|then|please|pls|just|maybe|can\\s+you|could\\s+you|can\\s+we|could\\s+we|lets?|let\'s)[\\s,]+)*';
        var f = null, noun = '', m, NUMW = { two: 2, three: 3, four: 4, five: 5, double: 2, twice: 2, triple: 3, treble: 3 };
        function num(w) { w = String(w).toLowerCase(); return NUMW[w] != null ? NUMW[w] : +w; }
        function nounOf(x) { x = String(x || '').replace(/^(?:the|its|their|that|those|this|these|my|our)\s+/i, '').replace(/\s+(?:size|scale)$/i, '').replace(/\s+/g, ' ').trim(); return /^(?:it|them|that|this|those|these|size|scale|one|ones)?$/i.test(x) ? '' : x; }
        if ((m = new RegExp('^' + LEAD + '(?:halve|halved|halving)\\s+(.{0,34})$', 'i').exec(s))) { f = 0.5; noun = nounOf(m[1]); }
        else if ((m = new RegExp('^' + LEAD + '(?:cut|shrink|reduce|scale|bring)\\s+(.{0,34}?)\\s+(?:(?:size|scale)\\s+)?(?:down\\s+)?(?:in|by|to)\\s+half$', 'i').exec(s))) { f = 0.5; noun = nounOf(m[1]); }
        else if ((m = new RegExp('^' + LEAD + '(?:(?:make|get|have|set)\\s+(?:the\\s+|its\\s+|my\\s+|our\\s+)?(.{0,30}?)\\s+)?half\\s+(?:the\\s+size|(?:its\\s+)?(?:current\\s+|original\\s+)?size|as\\s+(?:big|large))$', 'i').exec(s))) { f = 0.5; noun = nounOf(m[1]); }
        else if ((m = new RegExp('^' + LEAD + '(double|twice|triple|treble)\\s+(?:the\\s+|its\\s+|their\\s+)?(?:(.{1,30}?)\\s+)?(?:size|scale)$', 'i').exec(s))) { f = num(m[1]); noun = nounOf(m[2]); }
        else if ((m = new RegExp('^' + LEAD + '(?:(?:make|get|have|set)\\s+(?:the\\s+|its\\s+|my\\s+|our\\s+)?(.{0,30}?)\\s+)?(twice|double|triple|treble|two\\s+times|three\\s+times|four\\s+times|[2-5]\\s*x)\\s+(?:the\\s+size|(?:its\\s+)?(?:current\\s+)?size|as\\s+(?:big|large)|(?:bigger|larger))$', 'i').exec(s))) { f = num(m[2].replace(/\s*(?:times|x)$/i, '')); noun = nounOf(m[1]); }
        else if ((m = new RegExp('^' + LEAD + '(?:(?:make|get|have|set|scale|resize)\\s+(?:the\\s+|its\\s+|my\\s+|our\\s+)?(.{0,30}?)\\s+)?(\\d{1,3})\\s*(?:%|percent|per\\s*cent)\\s+(smaller|bigger|larger)$', 'i').exec(s))) { var p = +m[2]; f = /^s/i.test(m[3]) ? (p > 0 && p < 95 ? 1 - p / 100 : null) : (p > 0 && p <= 400 ? 1 + p / 100 : null); noun = nounOf(m[1]); }
        else if ((m = new RegExp('^' + LEAD + '(shrink|reduce|enlarge|grow|increase|scale\\s+(?:it\\s+)?(?:up|down))\\s+(.{0,30}?)\\s*(?:(?:size|scale)\\s+)?by\\s+(\\d{1,3})\\s*(?:%|percent|per\\s*cent)$', 'i').exec(s))) { var p2 = +m[3], dn = /^(?:shrink|reduce|scale\s+(?:it\s+)?down)/i.test(m[1]); f = dn ? (p2 > 0 && p2 < 95 ? 1 - p2 / 100 : null) : (p2 > 0 && p2 <= 400 ? 1 + p2 / 100 : null); noun = nounOf(m[2]); }
        if (f == null || !isFinite(f) || f <= 0 || f === 1) return t;
        if (/\b(?:opacity|strength|intensity|gloss|shine|shininess|glow|brightness|saturation|speed|rotation|angle|contrast|flake|amount|thickness|width|height|numbers?|text|stripes?|lines?|bands?|bars?|outline|border|spacing|gap)\b/i.test(noun)) return t;          // those are other attributes (the planner has its own words for them), not the size of a pattern / graphic
        W26_MULTV = Math.round(f * 100) / 100; W26_MULTT = Date.now();
        return 'make ' + (noun ? 'the ' + noun : 'it') + (f < 1 ? ' smaller' : ' bigger');
    }
    function w26MultOps(F) {          // post-frame: the factor said ("half", "twice", "30% smaller") on the scale relative the frame emitted
        try {
            if (W26_MULTV == null || Date.now() - W26_MULTT > 3000 || w26Off('mult') || !F || !F.ops) return;
            var hit = false; F.ops.forEach(function (op) { var r = op && op.relative; if (r && r.prop === 'scale' && (r.amount == null || r.amount === 'little' || r.amount === 'lot')) { r.amount = W26_MULTV; r.dir = W26_MULTV < 1 ? -1 : 1; hit = true; } }); if (hit) W26_MULTV = null;          // consumed: one factor, one scale op
        } catch (e) {}
    }
    function w26Pct(F, s, hasLastE) {          // class 1 (kill noW26_pct): a bare percent on the last change ("now try 40%", "make it 40 percent", "now 70%") = the opacity (a pattern) / intensity (a finish) of the last change set to that value.
        if (w26Off('pct') || !hasLastE || typeof s !== 'string' || s.length > 60) return;          // The planner moves it by its default step in the right direction; the absolute value needs the planner patch (relative.to), see PROGRESS.md.
        var m = /^\s*(?:(?:ok(?:ay)?|now|then|and|so|just|maybe|try|hmm+|lets?|let'?s|please|pls)[\s,]+)*(?:(?:make|set|put|bring|take|turn|go)\s+(?:it|that|this|them)?\s*(?:to|at|for)?\s*|(?:to|at)\s+)?(\d{1,3})\s*(?:%|percent|per\s*cent)\s*(?:opacity|strength|intensity|visible|opaque|please|pls)?[\s.!]*$/i.exec(s);
        if (!m) return;
        var n = +m[1]; if (!(n >= 0 && n <= 100)) return; n = Math.max(5, n);
        F.act = 'change'; F.ops = [{ verb: 'adjust', relative: { prop: 'opacity', dir: n < 100 ? -1 : 1, to: n }, ref: { to: 'last_change' } }]; F.missing = []; F.question = undefined; delete F.question;
    }
    // ---- S6 (class 6, kill noW26_pal): "main colour and accent colour" lists. "main colour #1E90FF and accent #222222 please", "base #00A651, accent #FFD100", "gold base, black accent", "green main, white accent" = the two-colour order the helper
    //   already runs ("make it blue and black": the body in the first colour, a stripe in the second). And the reply "base colour first, accent second" / "the first one is the base, the second the accent" to a two-colour turn re-states that order.
    var W26_ROLE_B = /\b(?:main|base|primary|body)(?:\s+colou?rs?)?\b/, W26_ROLE_A = /\b(?:accent|secondary|trim|highlight|contrast|detail)(?:\s+colou?rs?)?\b/;
    function w26PalIn(t) {
        var low = t.toLowerCase(); if (!W26_ROLE_B.test(low) || !W26_ROLE_A.test(low)) return t;
        var L; try { L = lex(low, {}); } catch (e) { return t; }
        var f = L.fixed, cols = L.slots.filter(function (c) { return c.t === 'COL' && !c.neg && !c.exc; });
        if (cols.length !== 2 || L.slots.some(function (c) { return /^(?:PART|BODY|FIN|PAT|LAYER|NUMS|SPON)$/.test(c.t) && !c.neg && !c.exc && !(c.t === 'BODY' && /^(?:main|base|body|primary)(?:\s+colou?rs?)?$/.test(String(c.s || ''))); })) return t;
        var rb = W26_ROLE_B.exec(f), ra = W26_ROLE_A.exec(f); if (!rb || !ra) return t;
        function gap(r, c) { var a = r.index, b = r.index + r[0].length; return c.at >= b ? c.at - b : (a >= c.end ? a - c.end : 0); }
        var pairs = [[gap(rb, cols[0]), 0, 0], [gap(rb, cols[1]), 0, 1], [gap(ra, cols[0]), 1, 0], [gap(ra, cols[1]), 1, 1]].sort(function (x, y) { return x[0] - y[0]; });
        var asg = [null, null]; pairs.forEach(function (p) { if (asg[p[1]] == null && asg.indexOf(p[2]) < 0) asg[p[1]] = p[2]; });
        if (asg[0] == null || asg[1] == null) return t;
        function nm(c) { return String(c.hex || c.s || c.v); }
        return 'make the car ' + nm(cols[asg[0]]) + ' with a ' + nm(cols[asg[1]]) + ' stripe down the middle';          // the explicit form of the two-colour order: 'make it X and Y' after a stripe edit is read as a stripe follow-up
    }
    var W26_ORDREPLY = /^\s*(?:(?:ok(?:ay)?|so|and|then|yes|yeah|yep|um+|well|just)[\s,]+)*(?:(?:the\s+)?(?:base|main|body|primary)(?:\s+colou?r)?\s+(?:first|1st)\s*[,;&]?\s*(?:and\s+)?(?:the\s+)?(?:accent|secondary|trim)(?:\s+colou?r)?\s+(?:second|2nd|next|last)|(?:the\s+)?(?:first|1st)(?:\s+one)?\s+(?:is\s+|for\s+|as\s+)?(?:the\s+)?(?:base|main|body|primary)(?:\s+colou?r)?\s*[,;&]?\s*(?:and\s+)?(?:the\s+)?(?:second|2nd)(?:\s+one)?\s+(?:is\s+|for\s+|as\s+)?(?:the\s+)?(?:accent|secondary|trim)(?:\s+colou?r)?|(?:the\s+)?(?:first|1st)(?:\s+one)?\s+(?:is\s+|for\s+|as\s+)?(?:the\s+)?(?:accent|secondary|trim)(?:\s+colou?r)?\s*[,;&]?\s*(?:and\s+)?(?:the\s+)?(?:second|2nd)(?:\s+one)?\s+(?:is\s+|for\s+|as\s+)?(?:the\s+)?(?:base|main|body|primary)(?:\s+colou?r)?|(?:the\s+)?(?:accent|secondary|trim)(?:\s+colou?r)?\s+(?:first|1st)\s*[,;&]?\s*(?:and\s+)?(?:the\s+)?(?:base|main|body|primary)(?:\s+colou?r)?\s+(?:second|2nd|next|last))[\s.!]*(?:please|pls)?[\s.!]*$/i;
    function w26Pal(t) {
        if (w26Off('pal') || typeof t !== 'string' || t.length > 200 || /\?/.test(t) || W23_HOWQ.test(t)) return t;
        if (W26_ORDREPLY.test(t)) {
            var pv = w26Said(t), prior = pv.length ? pv[pv.length - 1] : null; if (!prior || prior.length > 200) return t;
            var psl = w23Sl(prior); if (!psl) return t;
            var cols = psl.filter(function (x) { return x.t === 'COL'; }); if (cols.length !== 2 || psl.some(function (x) { return x.t === 'PART'; })) return t;
            var rev = /^[^,;&]*?\b(?:accent|secondary|trim)\b[^,;&]*?\b(?:first|1st)\b/i.test(t) || /\b(?:first|1st)(?:\s+one)?\s+(?:is\s+|for\s+|as\s+)?(?:the\s+)?(?:accent|secondary|trim)\b/i.test(t);
            function nm(c) { return String(c.hex || c.s || c.v); }
            return 'make the car ' + nm(cols[rev ? 1 : 0]) + ' with a ' + nm(cols[rev ? 0 : 1]) + ' stripe down the middle';
        }
        return w26PalIn(t);
    }
    // ---- S7 (class 7, kill noW26_match): "make it match" after two named things = the LAST-named thing takes the look of the one before ("hood red", "roof blue", "make it match" = the roof matches the hood).
    var W26_MBARE = /^\s*(?:(?:ok(?:ay)?|so|and|then|now|please|pls|just)[\s,]+)*(?:(?:make|get|have|let'?s\s+make)\s+(?:it|them|those|these|both)\s+(?:all\s+)?(?:match|the\s+same|identical|line\s+up)|match\s+(?:them|those|it)(?:\s+up)?|(?:they|it)\s+should\s+match)(?:\s+(?:exactly|perfectly|please|pls|then|up|together))*[\s.!]*$/i;
    //   S7b (same kill key): a PART told to match the colour of a LAYER / the numbers / the logos: "make the hood match the colour in the Logos layer", "the trunk needs to be the exact colour of the numbers", "match the spoiler to the Numbers layer".
    //   Rewritten to "make the <part> the same colour as the <layer>" (the frame turns that into a copy_look from the layer / element); before, the layer word hijacked the target ("pattern on the Logos layer") or no colour was found and it asked.
    var W26_LX = '(?:(?:the\\s+)?(?:red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|lime|cyan|magenta|brown|bronze|copper)\\s+(?:in|on|of|from)\\s+)?((?:(?:the|our|my)\\s+)?(?:[a-z0-9_-]+\\s+){0,2}?(?:layer|logos?|numbers?|sponsors?|decals?))';
    var W26_LM1 = new RegExp('^\\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls)[\\s,]+)*(?:make|get|have|set)\\s+(?:the\\s+|my\\s+|our\\s+)?([a-z ]{3,24}?)\\s+(?:match|be|look\\s+like)\\s+(?:exactly\\s+)?(?:the\\s+)?(?:(?:exact|same|precise)\\s+)?(?:colou?rs?|paint|look|shade)\\s+(?:in|of|from|on|used\\s+in|used\\s+on|as)\\s+' + W26_LX + '(?:\\s+(?:exactly|precisely|please|pls))*[\\s.!]*$', 'i');
    var W26_LM2 = new RegExp('^\\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls)[\\s,]+)*(?:the\\s+|my\\s+|our\\s+)?([a-z ]{3,24}?)\\s+(?:needs?\\s+to\\s+(?:be|match)|should\\s+(?:be|match)|must\\s+(?:be|match)|has\\s+to\\s+(?:be|match)|have\\s+to\\s+(?:be|match)|ought\\s+to\\s+(?:be|match)|is\\s+(?:meant|supposed)\\s+to\\s+(?:be|match))\\s+(?:exactly\\s+)?(?:the\\s+)?(?:(?:exact|same|precise)\\s+)?(?:(?:colou?rs?|shade|paint)\\s+(?:of|as|in|from)\\s+)?' + W26_LX + '(?:\\s+(?:exactly|precisely|please|pls))*[\\s.!]*$', 'i');
    var W26_LM3 = new RegExp('^\\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls)[\\s,]+)*match\\s+(?:up\\s+)?(?:the\\s+|my\\s+|our\\s+)?([a-z ]{3,24}?)\\s+(?:to|with)\\s+(?:the\\s+)?(?:(?:exact|same|precise)\\s+)?(?:(?:colou?rs?|shade|paint)\\s+(?:of|in|from)\\s+)?' + W26_LX + '(?:\\s+(?:exactly|precisely|please|pls))*[\\s.!]*$', 'i');
    var W26_LM4 = new RegExp('^\\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls)[\\s,]+)*(?:make|get|have|set)\\s+(?:the\\s+|my\\s+|our\\s+)?([a-z ]{3,24}?)\\s+(?:the\\s+)?(?:(?:exact|same|precise)\\s+)+(?:colou?rs?|paint|look|shade)\\s+(?:as|of)\\s+' + W26_LX + '(?:\\s+(?:exactly|precisely|please|pls))*[\\s.!]*$', 'i');          // the normalised form of the match order (make the hood the same colour as the Logos layer): only used by w26IsLayerMatch
    function w26LayerMatch(t) {
        if (W26_INSYN || w26Off('layersame')) return t;
        var m = W26_LM1.exec(t) || W26_LM2.exec(t) || W26_LM3.exec(t); if (!m) return t;
        var sl = w23Sl(m[1]); if (!sl || !sl.length || sl.some(function (x) { return x.t !== 'PART' || x.neg || x.exc; })) return t;
        var tail = m[0].slice(m[0].toLowerCase().indexOf(String(m[1]).toLowerCase()) + String(m[1]).length), cw = /\b(red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|maroon|lime|cyan|magenta|brown|bronze|copper)\b/i.exec(tail);
        if (cw) {          // "the red in our logo layer" (the normaliser leaves "red layer"): that colour family SAMPLED from the layer (the raw text says which layer: logos / sponsors / numbers); anything else keeps the plain colour order
            var raw = String(W26_RAW || '') + ' ' + m[2], src =/\b(?:logos?|sponsors?|decals?)\b/i.test(raw) ? 'logos' : (/\bnumbers?\b/i.test(raw) ? 'numbers' : '');
            if (!src || w26Off('layercol')) return t;
            var hasLy = false; try { hasLy = ((W26_ENV && W26_ENV.layers) || []).some(function (ly) { var nm = String((ly && (ly.name || ly)) || ''); return src === 'numbers' ? /number/i.test(nm) : /logo|sponsor|decal/i.test(nm); }); } catch (eL) {}
            if (!hasLy) return t;          // W26U 2026-10-10 (bank W26_C7-001 regression vs W25): with NO such layer on the paint, 'the red in our logo layer' is just the colour word - keep the plain recolour (the rewrite asked 'Same as what?')
            W26_PEND = { word: cw[1].toLowerCase() };
            return 'make the ' + w26Trim(m[1]).replace(/^(?:the|my|our)\s+/i, '') + ' the same colour as the ' + src;
        }
        if (/\b(?:hood|bonnet|roof|trunk|boot|door|doors|side|sides|fender|fenders|bumper|bumpers|spoiler|wing|mirror|mirrors|skirt|skirts|splitter|roofline)\b/i.test(m[2]) && !/\blayer\b/i.test(m[2])) return t;
        return 'make the ' + w26Trim(m[1]).replace(/^(?:the|my|our)\s+/i, '') + ' the same colour as ' + (/^(?:the|our|my)\s/i.test(m[2]) ? 'the ' + m[2].replace(/^(?:the|our|my)\s+/i, '') : 'the ' + m[2]);
    }
    var W26_PEND = null, W26_RAW = '';
    var W26_INSYN = 0;          // 1 while the answer.js reader calls OF.syn() (outside frameOf: W26_ENV / W26_RAW are the LAST frame's, stale): the layer-match order is rewritten by the frame only
    function w26SynWrap(t) { W26_INSYN = 1; try { return syn(t); } finally { W26_INSYN = 0; } }
    function w26LayerWord(F) {          // after the frame is built: the colour word of a "match the <part> to the <colour> in the <layer>" order rides on the copy_look (the planner picks that colour family from the layer's own pixels)
        try {
            var p = W26_PEND; W26_PEND = null; if (!p || !F || w26Off('layercol')) return;
            var op = (F.ops || [])[0]; if (!op || op.verb !== 'copy_look' || !op.source || (op.source.kind !== 'element' && op.source.kind !== 'layer')) return;
            op.look = op.look || {}; op.look.colour = { word: p.word }; op.copy = ['colour'];
        } catch (e) {}
    }
    function w26IsLayerMatch(t) {          // answer.js (named-layer pass): is this sentence a 'part matches the colour of a LAYER' order? (the frame owns it; the layer pass must not read it as 'Logos layer: make the hood ...')
        try { if (w26Off('match')) return false; var q = String(t || ''); if (q.length > 100 || /\?/.test(q)) return false; var m = W26_LM1.exec(q) || W26_LM2.exec(q) || W26_LM3.exec(q) || W26_LM4.exec(q); if (!m) return false; var sl = w23Sl(m[1]); return !!(sl && sl.length && !sl.some(function (x) { return x.t !== 'PART' || x.neg || x.exc; })); } catch (e) { return false; }
    }
    function w26Match(t) {
        if (w26Off('match') || typeof t !== 'string' || t.length > 100 || /\?/.test(t)) return t;
        if (!W26_MBARE.test(t)) return w26LayerMatch(t);
        var pv = w26Said(t).slice(-3), seq = [];
        pv.forEach(function (turn) { var sl = w23Sl(turn); (sl || []).forEach(function (x) { if (x.t !== 'PART' || x.neg || x.exc) return; var key = (x.parts && x.parts.length ? x.parts : [x.v]).join('+'); for (var i = seq.length - 1; i >= 0; i--) if (seq[i].key === key) seq.splice(i, 1); seq.push({ key: key, label: String(x.s || x.v) }); }); });
        if (seq.length < 2) return t;
        var y = seq[seq.length - 1], x0 = seq[seq.length - 2];
        return 'make the ' + y.label.replace(/^the\s+/i, '') + ' match the ' + x0.label.replace(/^the\s+/i, '');
    }
    // ---- S8 (class 2, kill noW26_truck): TRUCK vocabulary. Only when the car map has a bed (env.parts holds 'bed'): the bed, truck / pickup / cargo bed, bed rails / liner / cover / floor, inside / rear half of the bed, the tailgate and the tonneau cover are the bed part.
    //   (The tailgate sits on the bed part of the Silverado map; a car with no bed keeps the old behaviour: tailgate = trunk, bed = ask.) The sub-region wording (bed liner, only inside) is the same bed part; the reply says which part it used.
    var W26_BED = /\b(?:(?:truck|trunk|pickup|pick-up|cargo|load)\s+bed(?:\s+(?:rails?|liner|cover|floor|walls?))?|bed\s*(?:rails?|liner|cover|floor|walls?|sides?)|bed|tail\s*gate|tonneau(?:\s+cover)?)\b/g;          // 'truck' is spell-fixed to 'trunk' by the normaliser, so 'trunk bed' is the truck bed here
    function w26TruckOn(env) { try { return !w26Off('truck') && !!env && Array.isArray(env.parts) && env.parts.indexOf('bed') >= 0; } catch (e) { return false; } }
    function w26InsideBed(t, um) { try { return !!um && /^inside$/i.test(um[0]) && w26TruckOn(W26_ENV) && /\b(?:bed|liner|cargo|load\s+area|tonneau)\b/i.test(String(t)); } catch (e) { return false; } }          // W26U 2026-10-10 (class 2): "inside the bed" is the bed of a truck car map, not an interior the sheet lacks
    function w26BedSlots(f, slots) {
        var re = new RegExp(W26_BED.source, 'g'), m, add = [];
        while ((m = re.exec(f))) { add.push({ t: 'PART', s: m[0], v: 'bed', parts: ['bed'], at: m.index, end: m.index + m[0].length }); }
        slots.forEach(function (x) { if (x.t === 'PART' && /^(?:tail\s*gate|tonneau)/i.test(String(x.s || ''))) { x.v = 'bed'; x.parts = ['bed']; } });          // 'tailgate' is read as the trunk by the part vocabulary (its text is spell-fixed to 'trunk'): on a car map with a bed it is the bed
        if (!add.length) return slots;
        slots = slots.filter(function (x) { return !add.some(function (a) { return x.at < a.end && x.end > a.at; }); });
        return slots.concat(add);
    }
    // ---- class 6 (kill noW26_colsw), 2026-10-10 coordinator bug 3: "make the white a light grey" / "turn the blue into a light green" = recolour the paint that IS white / blue (live: body white + a light-grey stripe, an article, or a re-applied white).
    //   Rewritten to the form the frame already reads as a colour-target order ("change the white to light grey" -> target colour white). Two different base colours only: "make the red a darker red" keeps the planner's own question (a shade of the same colour has no hex to aim at).
    var W26_COLW = '(?:red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|teal|navy|brown|cyan|magenta|charcoal|maroon|beige|cream|ivory|burgundy|turquoise|lime|violet|lavender|tan|bronze|copper)';
    var W26_COLSW = new RegExp('^\\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls|hey)[\\s,]+)*(?:(?:can|could|would)\\s+(?:you|we)\\s+)?(?:please\\s+)?(?:make|turn|change|switch|swap|recolou?r|colou?r|paint|shift)\\s+(?:all\\s+)?(?:the|my)\\s+(' + W26_COLW + ')(?:\\s+(?:parts?|bits?|areas?|sections?|paint|colou?r|stuff))?\\s+(?:into|to|a|an|be|become)\\s+((?:(?:a|an|the)\\s+)?(?:(?:very|slightly|bit|little|light|lighter|dark|darker|deep|deeper|pale|bright|brighter|dull|soft|warm|warmer|cool|cooler|pastel|neon|hot|rich|muted|vivid)\\s+){0,2}(' + W26_COLW + ')(?:ish)?)\\s*[.!]*\\s*$', 'i');
    function w26ColSwap(t) {
        if (w26Off('colsw') || typeof t !== 'string' || t.length > 90 || /\?/.test(t)) return t;
        var m = W26_COLSW.exec(t); if (!m) return t;
        var a = m[1].toLowerCase().replace(/^gray$/, 'grey'), b = m[3].toLowerCase().replace(/^gray$/, 'grey'); if (a === b) return t;
        return 'change the ' + m[1].toLowerCase() + ' to ' + m[2].replace(/^(?:an?|the)\s+/i, '');
    }
    // ---- class 2 (kill noW26_listpick), 2026-10-10 coordinator bug 2: "the second one but on the hood" / "do the first one but on the roof" right after an ideas list. The frame read the pick as a copy of nothing onto the part and the planner said
    //   "You asked to keep that as it is, so there is nothing left to change". With a list on the table, an ordinal pick plus "but on <part>" is the regex reader's own list pick (p7Pick takes the item and the part): the frame stands aside, as it does for a bare pick.
    var W26_SAMEAS_PRE = /(?:\b(?:the\s+)?same(?:\s+\w+)?\s+as\s+(?:(?:the|my|our)\s+)?(?:[\w#-]+\s+){1,3}?(?:on|of|from|in)\s+(?:(?:the|my|our)\s+)?)$/i;          // bug 4: "same as the red on the left side" - 'the left side' is the reference
    var W26_PICKON = /^\s*(?:(?:ok(?:ay)?|so|now|and|then|please|pls|hmm+)[\s,]+)*(?:(?:do|use|try|go\s+(?:with|for)|pick|take|choose|give\s+me|apply|i'?ll\s+(?:take|have|do|go\s+with)|let'?s\s+(?:do|go\s+with|use|try))\s+)?(?:(?:the\s+)?(?:first|second|third|fourth|fifth|sixth|last|1st|2nd|3rd|4th|5th|6th)(?:\s+(?:one|option|idea|choice|pick|finish|look))?|(?:number|option|choice|pick|no\.?|#)\s*(?:[1-6]|one|two|three|four|five|six))\s*,?\s*(?:(?:but|only|just|though|however)\s+)*(?:on|for|onto|to|over\s+on)\s+(?:the\s+|my\s+)?(?:hood|bonnet|roof|trunk|boot|spoiler|wing|bumpers?|front\s+bumper|rear\s+bumper|(?:left|right)\s+(?:side|door)|sides|doors|body|whole\s+car|car)\b(?:\s+(?:instead|please|pls|though|then))*\s*[.!]*\s*$/i;
    function w26PickBut(t) {          // "the second one BUT on the hood" -> "the second one on the hood": the planner reads 'but <part>' as an exception and the verify pass then refuses the pick ("You asked to keep that as it is")
        if (w26Off('listpick') || typeof t !== 'string' || t.length > 90 || !W26_PICKON.test(t)) return t;
        return t.replace(/\s*,?\s*(?:\b(?:but|only|just|though|however)\b\s+)+(?=(?:on|for|onto|to|over\s+on)\b)/i, ' ');
    }
    // ---- class 2 (kill noW26_listacc), 2026-10-10 coordinator: "go with that" / "do it" / "that one" right after a LIST of ideas names no item (live: an unrelated article "Where the files go", or "I did not catch that"). With a list on the table the helper asks which of ITS OWN items, once,
    //   naming them (the buyer can then say "the second one"); it never picks one for them and never answers with an article. A single-item list / a pending yes-no question keeps the existing accept path.
    var W26_ACCEPT = /^\s*(?:(?:ok(?:ay)?|yes|yeah|yep|sure|alright|so|then|well|hmm+|and)[\s,]+)*(?:go\s+(?:with|for)\s+(?:that|this|it|that\s+one|this\s+one)|(?:do|use|take|pick|choose|apply|try)\s+(?:that|this|it)(?:\s+one)?|(?:that|this)\s+one|(?:let'?s|lets)\s+(?:do|go\s+with|use|try)\s+(?:that|this|it)(?:\s+one)?|go\s+for\s+it|do\s+it|(?:i'?ll|i\s+will|ill)\s+(?:take|have|do|go\s+with)\s+(?:that|this|it)(?:\s+one)?|sounds\s+good|that\s+works|that'?s\s+the\s+one)\s*(?:please|pls|thanks|thx)?\s*[.!]*\s*$/i;
    function w26ListAccept(s, env) {
        try {
            var IF = W.SpbIntentFrame;
            if (w26Off('listacc') || !IF || !env || !env.list || !env.list.items || env.list.items.length < 2 || typeof s !== 'string' || s.length > 60 || /\?/.test(s) || !W26_ACCEPT.test(s)) return null;
            var labs = env.list.items.slice(0, 6).map(function (x, i) { return (i + 1) + '. ' + String((x && x.label) || ''); });
            var F = { v: 1, act: 'ask_back', ops: [], keep: [], decals: 'protect', missing: ['target'], alts: [], said: s.slice(0, 600), producer: 'offline-frame', question: 'Which one do you want: ' + labs.join(', ') + '? Say \u201cthe second one\u201d, or tap one. Nothing changes until you pick.' };
            var v = IF.validate(F, env); if (!v || !v.ok) return null;
            return { frame: F, want: 'ask', confidence: 1, source: 'of:w26listacc', shape: null, said: s, fixes: [], guard: 'listacc' };
        } catch (e) { return null; }
    }
    function w26PickOn(s, env) {
        try { return !w26Off('listpick') && !!(env && env.list && env.list.items && env.list.items.length) && W26_PICKON.test(String(s || '')); } catch (e) { return false; }
    }
    // ---- class 6 (kill noW26_sides), 2026-10-10 coordinator bug 1: "paint the left and right side red" / "make the driver and passenger doors blue" named only the RIGHT side (the lexer reads 'left' alone as no part).
    //   Rewritten to the form that reads both: "both sides" / "both doors" / "both fenders". 'or' is not a pair ("the left or right side" stays a choice).
    var W26_SIDES = /\b(?:the\s+)?(?:left|driver'?s?|port)(?:\s+hand)?\s*(?:,|&|\+|\/|and|plus)\s*(?:the\s+)?(?:right|passenger'?s?|starboard)(?:\s+hand)?\s+(sides?|doors?|fenders?|panels?|quarters?|quarter\s+panels?|flanks?)\b|\b(?:the\s+)?(?:right|passenger'?s?|starboard)(?:\s+hand)?\s*(?:,|&|\+|\/|and|plus)\s*(?:the\s+)?(?:left|driver'?s?|port)(?:\s+hand)?\s+(sides?|doors?|fenders?|panels?|quarters?|quarter\s+panels?|flanks?)\b/gi;
    function w26Sides(t) {
        if (w26Off('sides') || typeof t !== 'string' || !/\b(?:left|driver|port|right|passenger|starboard)/i.test(t)) return t;
        return t.replace(W26_SIDES, function (m, a, b2) { var n = String(a || b2 || '').toLowerCase(); return 'both ' + (/^door/.test(n) ? 'doors' : /^fender/.test(n) ? 'fenders' : 'sides'); });
    }
    function w26Pre(s) {
        if (w26Off() || typeof s !== 'string' || !s) return s;
        var o = s, r;
        try {
            s = w26Sides(s);
            s = w26PickBut(s);
            if ((r = w26Self(s)) !== s) return r;
            if ((r = w26Angry(s)) !== s) return r;
            if ((r = w26StripeOff(s)) !== s) return r;
            if ((r = w26Mult(s)) !== s) return r;
            if ((r = w26Restore(s)) !== s) return r;
            if ((r = w26Polite(s)) !== s) return r;
            if ((r = w26Back(s)) !== s) return r;
            if ((r = w26Mod(s)) !== s) return r;
            if ((r = w26Pal(s)) !== s) return r;
            if ((r = w26Match(s)) !== s) return r;
            if ((r = w26ColSwap(s)) !== s) return r;
        } catch (e) { return o; }
        return s;
    }
    var w26dbg = { listacc: w26ListAccept, sides: w26Sides, colsw: w26ColSwap, pickon: w26PickOn, numsz: w26NumSize, too: w26Too, restore: w26Restore, mult: w26Mult, pre: function (t) { return w26Pre(t); }, self: w26Self, angry: w26Angry, polite: w26Polite, mod: w26Mod, pal: w26Pal, match: w26Match, stripeoff: w26StripeOff };
    // W26U-END
    function frameOf(text, prevTurns, env, opt) {
        opt = opt || {}; env = env || {}; W26_ENV = env; W26_PEND = null; W26_RAW = String(text == null ? '' : text);
        if ('r' in opt) { var vg0 = null; try { vg0 = vagueFrame(text, opt.r, env); } catch (eVg0) { vg0 = null; } if (vg0) return { frame: vg0, want: 'ask', confidence: 1, source: 'of:vague' }; }          // C-OFFVAGUE 2026-10-08 (frame-first policy: the host passes the regex reader's result as opt.r)
        var KN = W.SpbIntentKnn, IF = W.SpbIntentFrame; if (!KN || !IF || !KN.ready()) return null;
        var s = String(text || ''), prevs = (prevTurns || []).map(String), prev;
        // W21H 2026-10-09: the planner pops the current turn from the convo store only when the text it hands us equals the raw turn; a normalised text (thx -> thanks) leaves the buyer's OWN turn as 'the previous turn'. The F_reply compose below skips it (w21Prev);
        // every other reader keeps the list as it was (dropping it for them lost 3 visible items). Planner-side fix for W20: pop the last convo turn when its text is the current turn modulo normalisation.
        prev = prevs.length ? prevs[prevs.length - 1] : null;
        s = w15fNorm(w9Norm(w9Polite(w9Abbr(w1Incl(r8Corr(w26Early(s)))))));          // W26U 2026-10-10: a change of mind / an angry wrong-part correction is rewritten BEFORE r8Corr
        if (typeof W.SPB_W21_LOG === 'function') W.SPB_W21_LOG({ k: 'chain', text: text, s: s });          // W21H 2026-10-09: SA_polite (tag / lead cut) then SA_complaint_fix (complaint + fix verb = order), see the W21H block          // W9ARB polite lead / W1-PARSE 2026-10-08 (include-clause / 'all parts') + R8-FIN 2026-10-08: 'all black, no wait blue' = all blue
        var SM = W.SpbIntentModel, said = s, fixes = [];          // S7c shared spell pre-pass (SpbIntentModel.clean: 'whitte' -> white, 'doirs rd' -> doors red); the said text is kept on the result
        if (SM && typeof SM.clean === 'function' && W.SPB_OF_CLEAN !== '0') { try { var cl = SM.clean(s); if (cl && cl.text && (cl.fixes || []).length) { var okF = cl.fixes.filter(function (fx) { return !STOP[String(fx[0]).toLowerCase()]; }); /* V4-G G23: never 'purpose' -> purple */ if (okF.length === cl.fixes.length) { s = cl.text; fixes = cl.fixes; } else if (okF.length) { okF.forEach(function (fx) { s = s.replace(new RegExp('\\b' + String(fx[0]).replace(/[^a-z0-9]/gi, '') + '\\b', 'i'), fx[1]); }); fixes = okF; } } } catch (e) { /* keep the said text */ } }
        if (prevs.length) { try { var w21p = w21Prev(prevs, s), w21r = w21p ? w21Reply(s, w21p, env) : null; if (typeof W.SPB_W21_LOG === 'function') W.SPB_W21_LOG({ k: 'reply', text: text, prevs: prevs, s: s, prev: w21p, r: w21r }); if (w21r) s = w21r; } catch (eW21) { /* keep the said text */ } }          // W21H F_reply 2026-10-09 (hold probe F_reply harm 33 -> see PROGRESS): a reply to an unfinished stripe / fade question carries that order
        if (!OF_CFG('noJ0t')) s = s.replace(/^(\s*(?:(?:and|now|also|then|ok|okay)[\s,]+)?(?:the\s+|make\s+the\s+)?)top\b(?!\s+(?:of|half|layer|coat|part|section|edge|stripe|bit|end|line|notch|speed|\d))/i, '$1roof');          // V4-G J0t: "top charcoal as well" = the roof
        if (!OF_CFG('noJ4g') && !W.SPB_OF_NOJ4G && /\b(?:fade[sd]?|fading|gradient|ombre|blend(?:ing|ed)?)\b/i.test(s) && /\bfrom\b/i.test(s)) { var axw = []; var s4g = s.replace(/\s+at the (?:very )?(front|nose|back|rear|tail|top|roof|bottom|rockers?|sills?)\b/gi, function (m0, w4) { axw.push(w4.toLowerCase()); return ''; });          // IA1 J4g 2026-10-07: 'from blue at the front to white at the back' = blue -> white, front to back
            if (axw.length >= 1 && s4g !== s) { var a0 = axw[0]; s = s4g.replace(/[\s.!]+$/, '') + (/^(?:front|nose)$/.test(a0) ? ' front to back' : /^(?:back|rear|tail)$/.test(a0) ? ' from the rear' : /^(?:top|roof)$/.test(a0) ? ' fading down' : ' fading up'); } }
        var w26la = w26ListAccept(s, env); if (w26la) return w26la;          // W26U 2026-10-10 (coordinator class 2): "go with that" / "do it" after a list asks which of its own items
        DK4 = { n: false, l: false };          // R4-READ 2026-10-08 R4a/R4b
        if (!OF_CFG('noR4b')) s = s.replace(/\b(?:xcept|exept|excpet|ecxept|exccept|excpt|exepct|exlcude|excpet)\b/gi, 'except');          // typo'd except ("make evrything pink!! xcept my number")
        if (!OF_CFG('noR4c')) s = s.replace(/\b(?:up top|on top)\b(?!\s+of\b)/gi, 'on the roof').replace(/\btail (bumper|bumpers)\b/gi, 'rear $1').replace(/(^|[,;]\s*|\band\s+)top\s+(?=#?[0-9a-f]{6}\b)/gi, '$1roof ');          // R4c: "put glitter up top" = the roof; "tail bumper" = rear bumper; "bonnet 1B365D, top FFFFFF" = roof
        if (!OF_CFG('noW3S') && !OF_CFG('noW3Sx')) s = s.replace(new RegExp(ALIAS_W3S[W3S_EXC_AT][0].source, 'gi'), ALIAS_W3S[W3S_EXC_AT][1]);          // W3-SCOPE class 8: 'roof no change' = except the roof (before the answer cues read 'no change')
        if (!OF_CFG('noR4d')) s = stripStateColour(s);          // R4d: "hood red now, i want yellow": the first colour is the STATE, the second is the order
        if (!OF_CFG('noR4a')) { var dk = stripDecalKeep(s); if (dk) { s = dk.text; DK4 = { n: dk.n, l: dk.l }; } }          // "whole car red but my number has to stay white" / "... the number and the logos not change": the keep clause leaves the sentence, the elements go on the keep list
        var p4g = pre4g(s); if (p4g) s = p4g.text;          // V4-G round 3 J1: inverted except / typo'd leave-it clause / boundary words (see pre4g)
        var rd = KN.read(s, env, { prev: prev, exclude: opt.exclude, convo: !!prev, last: !!(env.planLast || env.last), k: 9, gen: false });
        if (!rd) return null;
        // V4-G: a header before a colon ("need a tidy livery for tomorrow's heat: white car, red nose") is context, not a target: the slots come from after it
        var hm = /^([^:]{3,80}):\s*(\S.{4,})$/.exec(s), sL = s;
        if (hm && !OF_CFG('noHdr') && !/_/.test(hm[1]) && !(env.layers || []).some(function (ly) { var nm = String((ly && (ly.name || ly)) || '').toLowerCase(); return nm.length > 2 && hm[1].toLowerCase().indexOf(nm) >= 0; }) && !COLW_RE.test(hm[1].toLowerCase()) && !HEX6_RE.test(hm[1].toLowerCase()) && !/\b(?:chrome|matte|satin|gloss|pearl|candy|metallic|carbon|flake|hood|bonnet|roof|trunk|spoiler|wing|bumpers?|doors?|sides?|numbers?|layers?|logos?|sponsors?|decals?|only|just)\b/i.test(alias(hm[1].toLowerCase())) && (COLW_RE.test(hm[2].toLowerCase()) || HEX6_RE.test(hm[2].toLowerCase()))) sL = hm[2];
        var L = lex(sL, env), f = L.fixed;
        var want = rd.want || 'nothing', F = { v: 1, act: 'nothing', ops: [], keep: [], decals: 'protect', missing: [], alts: [], said: s.slice(0, 600), producer: 'offline-frame' };
        if (want === 'decline') want = 'answer';
        // V4-G 2026-10-07 H4: an option pick ("the second one", "option 2", "number two please") names a chip / list item the regex reader holds
        // (env.list / env.pending): null = the regex reader picks it; with no list = ask which one. Never the numbers layer.
        if (!OF_CFG('noH4') && PICK_RE.test(s.trim()) && !L.slots.some(function (x) { return /^(COL|FIN|PAT|PART|LAYER|BODY)$/.test(x.t); })) {
            if ((env.list && env.list.parts && env.list.parts.length) || (env.pending && !env.list)) return null;
            F.act = 'ask_back'; F.missing = [env.list ? 'target' : 'what']; var vP = IF.validate(F, env);          // a list made for no part: ask where it goes (the whole car is never a guess)
            return vP.ok ? { frame: F, want: 'ask', confidence: rd.confidence, source: 'of:pick', shape: rd.shape, said: said, fixes: fixes, guard: 'pick', want0: rd.want } : null;
        }
        if (w26PickOn(s.trim(), env)) return null;          // W26U 2026-10-10 (coordinator bug 2): an ordinal pick + 'but on <part>' with a list on the table is p7Pick's (see W26_PICKON)
        // the neighbours' intent is a vote, not a veto: a clear look on a clear target (or on the last change) is a change
        var hasLastE = !!(env.planLast || env.last), sl = L.slots.filter(function (x) { return !x.neg && !x.exc; });
        var hasLk = sl.some(function (x) { return /^(COL|FIN|PAT)$/.test(x.t); }), hasTg = sl.some(function (x) { return /^(PART|LAYER|NUMS|SPON|BODY)$/.test(x.t); });
        if ((want === 'ask' || want === 'nothing') && rd.confidence < 0.9 && hasLk && (hasTg || hasLastE || /\b(?:make|paint|turn|do|go)\b/.test(f) || (!OF_CFG('noG25') && STRIPE_RE.test(f) && /\b(?:middle|centre|center|down the|over the top|along)\b/.test(f) && !/\?/.test(f)))) want = 'change';
        if (want === 'nothing' && hasTg && hasLastE && /\b(?:same|too|also|as well)\b/.test(f)) want = 'change';
        if (want === 'answer' && hasLk && /^(?:ok |okay |now )?show me (?:the |my )?\w+(?: \w+)? (?:in|with)\b/.test(f)) want = 'change';          // "show me hood in candy green" = a preview = a change
        var st = s.trim(), lastSent = st.split(/[.!;]\s+/).pop().trim();
        var imperA = /(?:^|[,.;!?]\s*|\b(?:so|just|then|and|pls|please|now|but|can you|could you|can u|would you)\s+)(?:make|paint|turn|change|put|give|apply|aply|add|swap|set|go|do|use)\b/.test(st.toLowerCase().replace(/^\s*(?:pls|please|just|now|then|and|so|ok|okay)\s+/, ''));
        var themeW = THEMES.some(function (th) { return th[0].test(f); }) || /\b(?:patriotic)\b/.test(f);
        // V4-G G20: a plain look-on-target order with no question in its first clause ("chrome effect for numbers", "roof gradient from 000000 to 333333", "roof: our blue is Pantone ...") is a change even when the kNN reads an answer
        var cl1 = st.toLowerCase().split(/,|\band\b|;/)[0];
        if (want === 'answer' && !OF_CFG('noG20') && hasLk && hasTg && !/\?/.test(st) && !Q_START.test(st) && !HOWTO_ANY.test(f) && !COMPARE_RE.test(f) && !/\b(?:how|why|what|which|should|could|would|can|explain|ideas?|suggest\w*|recommend\w*|best|better|vs|versus|or)\b/.test(cl1) && !/\b(?:whats|wats|disappear\w*|vanish\w*|missing|gone|happen\w*|see|sees|seeing|get|gets|got|getting|shows?|showing|broke\w*|wrong|problem|issue|bug|glitch\w*|why|instead of|plain|identical|still|again|torn|between|prefer\w*|decid\w*|choos\w*|pick|opinion|thoughts?|think|remove|rid|take off|delete|erase|unsure|not sure|either|wonder\w*|curious|lose|clear(?: off| out| away)?|clean\w*|without|no more|stuff|junk|ditch|strip)\b/.test(f) && (!/\b(?:is|are|was|were|looks?|seems?|has|have|had)\b/.test(cl1) || /^[^:]{2,30}:/.test(st))) want = 'change';
        if (want === 'answer' && rd.confidence < 0.8 && (!HOWTO_ANY.test(f) || imperA) && !COMPARE_RE.test(f) && !/\b(?:should i|which|what colou?r|best)\b/.test(f)
            && ((hasLk && hasTg && (imperA || /^\s*what if\b/i.test(st))) || (themeW && (imperA || !Q_START.test(st))))) want = 'change';          // a clear look on a clear target, or a known livery theme
        if ((want === 'nothing' || want === 'ask') && hasLk && prev && /^\s*(?:yes|yeah|yep|yup|ok|okay|sure|go|lets do|let's do)\b/.test(f)) want = 'change';          // "yes yellow" answers the question before it
        if (!OF_CFG('noIA1') && (want === 'nothing' || want === 'ask') && hasLk && /^\s*(?:(?:ok|okay|well|so|then)[, ]+)?(?:i|we)\s+(?:want|need|would\s+like|'?d\s+like|wanna)\s+(?:it|the\s+car|my\s+car|the\s+whole\s+car|the\s+body)\s+(?:to\s+be\s+|in\s+|all\s+)?[a-z#]/.test(f) && !/\?\s*$/.test(st)) want = 'change';          // IA1 2026-10-07 (in-app train A-0229 'hello can you help me psint my car' -> 'i want it red' = "What should change, and where?"): I WANT IT <look> = a change
        var want0 = want, gAsk = 0;          // V4-G: the neighbours' vote before the guard rules (a guard that turns a change into an answer / ask is reported as o.guard)
        if (want !== 'change' && hasTg && !OF_CFG('noR8f') && r8Any(String(s).toLowerCase()) && !/\?\s*$/.test(st) && !Q_START.test(st) && !QUESTION_ANY.test(f) && !HOWTO_ANY.test(f) && !COMPARE_RE.test(f) && !TROUBLE_RE.test(f)) want = 'change';          // R8-FIN 2026-10-08: "starry night roof" / "weathered patina roof" (neighbours voted answer) = a paint order
        var imperClause = /(?:^|[,.;!?]\s*|\b(?:so|just|then|and|pls|please|now|but)\s+)(?:make|paint|turn|change|put|give|apply|aply|add|swap|set|go|do)\b/.test(st.toLowerCase().replace(/^\s*(?:pls|please|just|now|then|and|so|ok|okay)\s+/, ''));
        if (want === 'change' && !imperClause && (Q_START.test(st) || (/\?\s*$/.test(st) && (Q_START.test(lastSent) || st.split(/\s+/).length <= 2)))) want = 'answer';
        // (V4-F v5: a 'looks like X' rule was tried and dropped: theme requests are labelled change)
        if (want === 'change' && (PROTECT_RE.test(f) || CAP_RE.test(f))) want = 'answer';
        // V4-G 2026-10-07 H1: a state report / tag question ("the roof is #FFFFFF right now, right?", "my chrome came out flat") = answer; an imperative still asks for the change
        var stl = st.toLowerCase();
        if (!OF_CFG('noW3S') && !OF_CFG('noW3Sb') && (want === 'answer' || want === 'ask') && hasLk && hasTg && !/\?/.test(st) && !Q_START.test(st) && /^s*(?:(?:ok|and|also|but|now|so|nah|no)[ ,]+)*(?:the |my |our )?[a-z' ]{2,24}?s+(?:should|needs? to|has to|have to|must|ought to|gotta)s+bes+(?:the |a |an )?[a-z# 0-9]{2,30}s*[.!]*s*$/.test(st.toLowerCase())) want = 'change';          // W3-SCOPE 2026-10-09 (kill noW3S): 'the digits need to be orange' = an order, not a how-to (the numbers case asked)
        if (want === 'change' && !imperA && !OF_CFG('noH1') && ((STATE_RE.test(stl) && !WANT_RE.test(f)) || MIDQ_RE.test(stl))) want = 'answer';
        if (want === 'change' && !OF_CFG('noH1b') && /\?\s*$/.test(st) && st.split(/\s+/).length <= 4 && !hasLk) want = 'answer';          // "all of it?", "everything?"
        // V4-G H1c: "confirm the roof is #FFFFFF", "roof = #FFFFFF at the moment?": a check, not an order
        if (want === 'change' && !imperClause && !OF_CFG('noH1') && (/^\s*(?:(?:can you|could you|pls|please|quick)\s+)?(?:confirm|verify|check (?:if|whether|that)|tell me (?:if|whether)|double ?check(?: if| whether| that)?)\b/.test(stl) || /\b(?:at the moment|right now|currently|now|atm)\s*\?\s*$/.test(stl) || (!OF_CFG('noG23') && /\?\s*$/.test(stl) && /\b(?:quick check|check|exactly|precisely|correct|right|did (?:it|the \w+)|is (?:it|the \w+)|come out|came out)\b/.test(stl) && !/\b(?:can|could|would|will) (?:you|u)\b/.test(stl)))) want = 'answer';
        // V4-G H1d: a turn that only names what STAYS ("the hood stays as it is", "sponsors untouched") = an acknowledgement, not a repaint of the last change
        var tsl = L.slots.filter(function (x) { return /^(PART|NUMS|SPON|LAYER|OBJ|BODY)$/.test(x.t); });
        // V4-G G26 (dev class 2, own paraphrases): "sponsors left alone" = a constraint, never a target; "do late models even have a door number?" = a question;
        // "I want flames down the side. how" = how-to; "too much shiny" with nothing before = ask
        if (!OF_CFG('noG26') && (want === 'change' || want === 'ask') && !hasLk && tsl.length && !imperA && /\b(?:left|leave|leaving|keep|kept)\b[^.;]{0,24}\b(?:alone|as (?:is|it is|they are|they were)|untouched|unchanged|the same|be)\b|\b(?:left|kept) (?:alone|untouched|as (?:is|they are))\b/.test(f) && !/\b(?:make|paint|turn|change|colou?r|add|put)\b/.test(f)) want = 'answer';
        if (!OF_CFG('noG26') && want === 'change' && (/^\s*(?:(?:ok|so|but|wait|hey|and)[, ]+)?(?:do|does|did)\s+(?:\w+\s+){0,3}(?:even\s+|really\s+|actually\s+)?(?:have|has|need|get|come|support|work|allow|run|use|got)\b/.test(stl) || (!imperA && /^\s*(?:(?:ok|so|but|wait|hey|and)[, ]+)?(?:is|are|has|have|was|were)\s+(?:\w+\s+){0,3}\w+/.test(stl) && (/\?\s*$/.test(stl) || /\beven\b/.test(stl))))) want = 'answer';
        if (!OF_CFG('noG26') && want === 'change' && /(?:^|[\s.,;:!-])how\s*\??\s*$/.test(stl) && !/\bhow about\b/.test(stl)) want = 'answer';
        if (!OF_CFG('noG28') && want === 'change' && !imperA && /^\s*(?:(?:no|nah|hmm+|but|ugh|wait)[, ]+)?(?:that'?s|thats|it'?s|its|this is|that is|those are|they are|they'?re)\s+(?:still\s+)?not\s+(?:the\s+)?(?:same|right|correct|exact|matching)\b/.test(stl) && !/#[0-9a-f]{3,6}\b/.test(stl)) { want = 'ask'; gAsk = 1; }          // V4-G G28: "thats not the same red" = which one? (never a repaint)
        if (!OF_CFG('noW3S') && !OF_CFG('noW3Sc') && !hasLastE && !hasTg && !imperA && want !== 'ask' && /^\s*(?:(?:it'?s|its|it is|this is|that'?s|thats|looks?|seems?)\s+)?(?:(?:way|waay+|so|too|2|bit|kinda|sorta|really|super|little|a)\s+){1,3}(?:2\s+|too\s+|much\s+)?(?:shiny|shiney|glossy|dull|flat|plain|boring|drab|bright|dark|busy|loud|bland|basic)\b(?:\s+(?:rn|now|tbh|atm|lol|imo|honestly))?\s*[.!?]*\s*$/.test(stl)) { want = 'ask'; gAsk = 1; }          // W3-SCOPE 2026-10-09 (kill noW3S; class 6): 'way 2 shiny rn' is a complaint with no verb = ask, never a repaint
        if (!OF_CFG('noG26') && !hasLastE && !hasTg && /\btoo\s+(?:much\s+)?(?:shiny|shiney|shinny|shine|glossy|gloss|matte|flat|dark|bright)\b/.test(f) && want !== 'ask') { want = 'ask'; gAsk = 1; }
        if (want === 'change' && !OF_CFG('noH1') && !hasLk && !imperA && tsl.length && tsl.every(function (x) { return x.exc || x.stays || x.neg; }) && /\b(?:stays?|remains?|untouched|alone|as is|as it is|as they are|unchanged|intact|excluded|not included)\b/.test(f)) want = 'answer';
        // V4-G H7: trim / accents / details with no place named (or sampled from art): ask every time (owner rule), never paint the part the colour was sampled from
        if (want === 'change' && !OF_CFG('noH7') && TRIM_RE.test(f) && !/\b(?:trim|accents?|details?|badges?|emblems?|lettering)\s+(?:on|to|for|at|along|around)\s+(?:the\s+)?(?:\w+\s+)?(?:hood|roof|trunk|splitter|mirrors?|bumpers?|spoiler|wing|sides?|doors?|lip|skirts?|diffuser|nose|front|rear)\b/.test(f)) { want = 'ask'; gAsk = 1; }
        // V4-G H8: "the back end" / "the rear end" = the rear (owner rule: ask which part), not the rear bumper
        if (want === 'change' && !OF_CFG('noH8') && !hasLastE && /(?:\b(?:the|my) |^\s*(?:(?:make|paint|do|put|give) )?)(?:back|rear) end\b|\b(?:back|rear) of (?:the|my) (?:car|truck|body)\b|\b(?:on|do) the (?:back|rear)\b(?! (?:bumper|spoiler|wing|deck|lid|window|panel|quarter))|^\s*(?:the )?(?:back|rear)\s+(?:red|orange|yellow|green|blue|purple|pink|white|black|silver|grey|gray|gold|chrome|matte|carbon)\b/.test(stl) && !/\b(?:bumper|spoiler|wing|trunk|deck|diffuser)\b/.test(stl)) { want = 'ask'; gAsk = 1; }
        // V4-G H10: "keep green" / "stay with green" right after a change = keep what is there (nothing to paint)
        if (want === 'change' && !OF_CFG('noH10') && hasLastE && /^\s*(?:ok |okay |yeah |fine |then |just )?(?:keep|stay with|stick with|leave(?: it)?)\s+(?:it\s+|the\s+)?[a-z ]{2,24}$/.test(stl) && !hasTg && !/\b(?:but|and|make|paint|with|more|less|darker|lighter|on|instead)\b/.test(stl)) want = 'answer';
        // V4-G H11: a vibe / palette with no part ("look like it came from the future", "yellow green blue like my country") = offer options, never a whole-car guess
        if (want === 'change' && !OF_CFG('noH11') && !hasTg && !hasLastE && (/\b(?:futur\w*|from the future|sci-?fi|space ?age|retro|vintage|old ?school|like my country|my country|national colou?rs|flag colou?rs|but not like)\b/.test(stl) || (L.slots.filter(function (x) { return x.t === 'COL' && !x.neg; }).length >= 3 && LIKE_RE.test(f) && !THEMES.some(function (th) { return th[0].test(f); })))) { want = 'ask'; gAsk = 1; }
        // V4-G H9: 'two versions', 'show me both', 'side by side', 'before i decide': a comparison is an answer even when it is phrased as an order
        if (want === 'change' && !OF_CFG('noH9') && /\b(?:two versions|both versions|two looks|both looks|before (?:i )?decid\w*|see both|show (?:me )?both|let me see both|side by side|alongside|next to (?:it|each other)|so i can (?:compare|pick|choose|decide))\b/.test(stl)) want = 'answer';
        // V4-G H2: a how-to thread (a how-to question earlier, nothing painted since) keeps answering until the job is handed over ("for me", "go ahead", "can you ...")
        //   only a how-to about a TECHNIQUE (gradient, zone, layer ...) and only a follow-up that is not a full request (a look AND a part): "how do i save" > "ok roof red" = change
        if (want === 'change' && !OF_CFG('noH2') && !hasLastE && prevs.some(function (p) { return HOWTO_PREV.test(p) && TECH_RE.test(p.toLowerCase()); }) && !HANDOVER_RE.test(f) && !(hasLk && hasTg)) want = 'answer';
        // V4-G H3: a bare look right after an either/or question ("matte" after "matte or gloss black?") = ask where, never a paint job
        if (want === 'change' && !OF_CFG('noH3') && !hasLastE && prev && /\bor\b/.test(prev) && (Q_START.test(prev) || /\?\s*$/.test(prev)) && !hasTg && !(IF.partsOf(prev) || []).length && st.split(/\s+/).length <= 3) { want = 'ask'; gAsk = 1; }          // "which is better for the roof, chrome or candy" > "candy red" = the roof (a change)
        // V4-G H15: help / purpose / trouble words without an imperative = answer ("need help fading red into black", "what's the Car_Decal layer for", "the doors have no shine")
        if (want === 'change' && !imperA && !OF_CFG('noH15') && (/\b(?:need help|help me(?! (?:to )?(?:paint|make|do|change|colou?r|design|with (?:my|the) (?:car|paint)))|having (?:trouble|issues?|problems?)|(?:a |the )?problem with|(?:an |the )?issue with|struggl\w+|can'?t figure|cannot figure|not sure how|no idea how|(?:i )?do(?:n'?t|nt) know how|confused|purpose|what (?:it|this|that)'?s? for|used for|for what|meaning of|in reverse|reversed|inverted|mirror image|wrong way round|upside down|(?:has|have|got|shows?) no (?:shine|gloss|colou?r|clear ?coat)|lack(?:s|ing)? (?:shine|gloss|colou?r)|(?:isn'?t|aren'?t|not) (?:shiny|glossy|showing|working|right|there))\b/.test(stl))) want = 'answer';
        if (OF_CFG('v15') && want === 'change' && !imperA && (QUESTION_ANY.test(f) || TROUBLE_RE.test(f))) want = 'answer';          // generic question / trouble-report wording without an imperative
        if (want === 'change' && !imperClause && (COMPARE_RE.test(f) || HOWTO_ANY.test(f) || (/\bstill\b/.test(f) && !/\b(?:make|paint|fix|turn|change|sort|redo|again|do it|please|pls)\b/.test(f)))) want = 'answer';          // compare / how-to / "X still Y" complaints
        if (want === 'change' && COMPARE_RE.test(f) && /\b(?:so i can|let me|i can (?:choose|pick|compare))\b/.test(f)) want = 'answer';
        if (want === 'change' && ACK_END.test(f) && ACK_STATE.test(f) && !IMPER.test(f)) want = 'nothing';          // "make sure numbers dont get carbon" = a promise asked for, not a paint job
        if (want === 'change' && ACK_RE.test(st) && ACK_STATE.test(f) && !IMPER.test(f) && !/\b(?:but|now make|can you)\b/.test(f)) want = 'nothing';          // "fine, they're black on white now"
        if (want === 'change' && UNDO_RE.test(f) && !L.slots.some(function (x) { return /^(COL|FIN|PAT)$/.test(x.t); }) && !/\bhow\b/.test(f)) want = 'undo';
        if (want === 'change' && !OF_CFG('noG28') && /\b(?:put|change|set|turn|make|get)\s+(?:it|that|them|this|everything)\s+back\b[^.;]{0,24}\b(?:like|the way|how|as|to what)\s+(?:it|they)\s+(?:was|were|used to be)\b|\b(?:put|change|set|turn)\s+(?:it|that|them)\s+back\s*[.!]*\s*$/.test(stl) && !/#[0-9a-f]{3,6}\b/.test(stl)) want = 'undo';          // V4-G G28: "not the right green, put it back like it was" = undo
        // V4-G round 3 (sealed harm classes in the coordinator's words; OWN paraphrase cases, r3.js): never apply what is a complaint, a vague style, or a stripe with no place
        //   G30 a complaint / observation about the current state ("it went satin?!", "the numbers are hard to read on blue", "looks off") = ask, unless an explicit fix follows ("make them white")
        //   G31 a bare colour answering an idea / suggestion question, or a style "like a famous brand / team look" in "my own colours" with no colour named = ask (list options), never a body paint
        //   G32 a stripe request with no placement ("I want red and blue stripe") = ask where (owner rule for vague stripes), never hood + roof + trunk
        var gQ4 = null;
        if (!OF_CFG('noG30') && (want === 'change' || want === 'nothing') && !imperA && (/\b(?:went|turned|gone|came out|come out|became|ended up)\s+(?:all\s+|really\s+|kinda\s+|too\s+)?[a-z]+(?:\s+[a-z]+)?\s*(?:[?!]+|now|again|instead)?\s*$/.test(stl) || /\b(?:hard|tough|difficult|impossible|can'?t|cannot|cant|unable)\s+(?:to\s+)?(?:see|read|make out|spot|tell)\b/.test(stl) || /\blooks?\s+(?:a bit\s+|kinda\s+|really\s+|so\s+)?(?:off|wrong|weird|odd|bad|funny|strange|washed(?: out)?|muddy|awful|terrible|lost)\b|\bdoesn'?t look right\b/.test(stl))) { want = 'ask'; gAsk = 1; gQ4 = 'That reads like something looks wrong. What should it be instead? For example "make the numbers white" or "put the chrome back".'; }
        if (!OF_CFG('noG31') && want === 'change' && !hasTg && prev && !(IF.partsOf(prev) || []).length && st.split(/\s+/).length <= 3 && hasLk && /\b(?:ideas?|suggest\w*|recommend\w*|inspir\w*|surprise me|options?|something\s+(?:\w+\s+){0,3}(?:for|on)\b|give me something|what would look|what looks|any (?:cool |good |nice )?(?:looks?|designs?|schemes?|liveries|styles?))\b|\b(?:aggressive|fast|mean|cool|sick|clean|wild)\b[^.]*\?/.test(prev.toLowerCase())) { want = 'ask'; gAsk = 1; gQ4 = 'Where should that colour go: the whole body, or as an accent on one of the looks above? Tell me the part, or say "whole car" with the colour.'; }
        if (!OF_CFG('noG31') && want === 'change' && !hasTg && /\b(?:my|our)\s+(?:own\s+)?(?:team\s+)?colou?rs?\b/.test(stl) && !COLW_RE.test(stl) && !HEX6_RE.test(stl)) { want = 'ask'; gAsk = 1; gQ4 = 'Which colours are yours? Name two or three (for example "white, red and black") and I will lay them out.'; }
        if (!OF_CFG('noG31') && want === 'change' && !hasTg && /\b(?:famous|iconic|classic|well[- ]known|legendary)\s+(?:\w+\s+){0,2}(?:brand|team|livery|liveries|look|scheme|sponsor)\b|\b(?:like|similar to|inspired by|in the style of|kind of|sort of)\s+(?:a\s+|an\s+|the\s+)?(?:\w+\s+){0,2}(?:brand|team)\s+(?:look|livery|scheme|style)\b/.test(stl) && !THEMES.some(function (th) { return th[0].test(f); })) { want = 'ask'; gAsk = 1; gQ4 = 'Which look do you mean? Name the team or brand, or pick a style from the list (stripes, two-tone, fade, flames) and give me your colours.'; }
        if (!OF_CFG('noG32') && want === 'change' && STRIPE_RE.test(f) && !BODYSTR4_RE.test(f) && !themeW && !/\b(?:car|it|livery|look|scheme)\s+like\b/.test(f) && !sl.some(function (x) { return /^(PART|LAYER|BODY|NUMS|SPON|OBJ)$/.test(x.t); }) && !/\b(?:down the|along|over the top|over the car|across|middle|cent(?:re|er)|centered|full length|nose to tail|front to back|lengthwise|side|sides|pinstripes?|hood|bonnet|roof|trunk|doors?|bumpers?|spoiler|wing)\b/.test(f) && !/\b(?:the|those|these|that|my|existing)\s+(?:\w+\s+){0,2}stripes?\b/.test(f)) { want = 'ask'; gAsk = 1; gQ4 = 'Where should the stripes go: down the middle (hood, roof and trunk), along the sides, or somewhere else?'; }
        if (!OF_CFG('noG33') && want === 'change' && /\b(?:somewhere|some ?where|someplace|anywhere|some places|a few places)\b/.test(f) && !sl.some(function (x) { return /^(PART|LAYER|BODY|NUMS|SPON|OBJ)$/.test(x.t); })) { want = 'ask'; gAsk = 1; gQ4 = 'Where should it go: the hood, the roof, the sides, or the whole car?'; }          // V4-G round 4 G33: 'put some gloss somewhere' = ask where
        // V4-G experiment switch rxVeto: the regex reader's own reply (opt.regex) was an ANSWER and nothing here is an imperative = answer
        var rxr = opt.regex, rxc = rxr && rxr.cls;
        if (OF_CFG('rxVeto') && want === 'change' && !imperA && rxc === 'ANSWER' && !(rxr.steps || []).length && (OF_CFG('rxVetoAll') || !rxr.local)) want = 'answer';
        if (opt.w9force && want0 === 'change' && want !== 'change') want = 'change';          // W9ARB 2026-10-09: the arbitration re-asks for the change frame with the guard rules bypassed (checked in w9arb)
        if (want === 'answer') { F.act = 'answer'; F.question = { text: s.slice(0, 200) }; }
        else if (want === 'ask') { F.act = 'ask_back'; F.missing = ['what']; if (gQ4) F.question = gQ4; }
        else if (want === 'undo' || want === 'redo') { F.act = want; if (want === 'undo') F.n = nOfUndo(f); }
        else if (want === 'change') {
            var prevF = null;
            if (prev && !(env.planLast || env.last) && !(PICK_RE.test(prev.trim()) && !OF_CFG('noH13'))) { var pk = prev + '\u0001' + JSON.stringify(opt.exclude ? 1 : 0); try { var Lp = lex(prev, env), Fp = { v: 1, act: 'change', ops: [], keep: [], missing: [] }; changeFrame(prev, Lp, null, {}, Fp, null); prevF = Fp; } catch (eP) { prevF = null; } }
            changeFrame(s, L, rd.shape, env, F, prevF);
            var noTgt = F.ops.length && F.ops.every(function (o) { return (!o.target || o.defBody) && !o.ref; });
            var prevQ = prev && /\bhow (?:do|can|would|to|should)\b|\bis there a way\b|^\s*(?:can|could) i\b(?! (?:get|have))/i.test(prev);          // a follow-up to a HOW-TO question is still the how-to
            if (F._usedPrev && prevQ && /^\s*(?:and|then|and then|also|on|after that|next)\b/i.test(s)) { F.act = 'answer'; F.ops = []; F.missing = []; F.question = { text: s.slice(0, 200) }; }
            delete F._usedPrev;
            if (F.act !== 'change') { /* answered above */ }
            else if ((F.ops.length === 1 && F.ops[0].unpaint && !F.ops[0].target) || (noTgt && UNPAINT_TXT.test(f.replace(/\b(?:except|without|apart from|but not|other than|besides|not)\b.*$/, '')))) { F.act = 'answer'; F.ops = []; F.question = { topic: 'unpaintable', text: s.slice(0, 200) }; F.missing = []; }
            else if (TRUCK_RE.test(f) && !w26TruckOn(env)) { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['target']; }          // truck parts on a car with no bed / cab: ask which part
            else if (FIN_TGT.test(f) && /\b(?:off|remove)\b/.test(f) && L.slots.some(function (x) { return x.t === 'PART'; })) { var fps = []; L.slots.forEach(function (x) { if (x.t === 'PART') fps = fps.concat(x.parts || []); }); F.ops = [{ verb: 'refinish', target: { kind: 'part', parts: uniq(fps) }, look: { finish: { family: 'gloss', keep_colour: true } } }]; F.missing = []; }          // "take chrome off the roof"
            else if (FIN_TGT.test(f) || (VIBE_RE.test(f) && !THEMES.some(function (th) { return th[0].test(f); }) && !STRIPE_RE.test(f) && !L.slots.some(function (x) { return x.t === 'PART' || x.t === 'LAYER'; })) || (BARE_RE.test(f) && F.ops.some(function (o) { return o.defBody; }))
                || (!hasLastE && F.ops.some(function (o) { return o.relative && o.target && o.target.kind === 'body' && !hasLook(o.look) && !(!OF_CFG('noW1g') && o.relative.prop === 'gloss'); }))) { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['what']; }          // vague looks / finish-as-target / "the rear" / a tweak with nothing to tweak: ask (W1-PARSE 2026-10-08: a whole-car SHINE tweak, 'make the car less shiny', is a shine-only edit of the paint, not nothing-to-tweak; kill SPB_OF_CFG.noW1g)
            else {          // "switch red and blue (with each other)": two colour-target ops
                var cs = L.slots.filter(function (x) { return x.t === 'COL' && !x.neg; });
                if (cs.length === 2 && cs[0].v !== cs[1].v && /\b(?:switch|swap|flip|invert|reverse|trade)\b/.test(f) && /\b(?:each other|around|vice versa|and \w+ (?:to|into|becomes?) \w+|become)\b/.test(f)) {
                    var h0 = cs[0].hex || hexOfWord(cs[0].v), h1 = cs[1].hex || hexOfWord(cs[1].v);
                    F.ops = [{ verb: 'recolour', target: { kind: 'colour', colour: { word: cs[0].v, hex: h0 } }, look: { colour: { word: cs[1].v, hex: h1 } } }, { verb: 'recolour', target: { kind: 'colour', colour: { word: cs[1].v, hex: h1 } }, look: { colour: { word: cs[0].v, hex: h0 } } }]; F.missing = [];
                }
            }
        }
        if (F.act !== 'answer') w26Pct(F, s, hasLastE);          // W26U 2026-10-10 (class 1: a bare percent on the last change)
        if (F.act === 'change') { w26LayerWord(F); w26Obj(F); w26MultOps(F); }          // W26U 2026-10-10 (class 7: "the red in our logo layer" = that colour family sampled from the layer)
        if (F.act === 'change') postNets(F, f, s, L, hasLastE);          // V4-G 2026-10-07 H5 / H6
        // V4-G H14: a whole-car paint from a look alone (no part, no 'car / all / whole / look / want', no imperative, nothing before) is a guess: ask
        if (F.act === 'change' && !OF_CFG('noH14') && !imperA && !hasTg && !hasLastE && !prev && !(w9on() && W9_LEX && W9_BODYX.test(f)) && F.ops.some(function (o) { return o.target && o.target.kind === 'body'; }) && !WHOLE_CUE.test(f) && !/\b(?:want|wanna|look|theme|themed|livery)\b/.test(f) && !/^\s*(?:(?:light|dark|bright|deep|neon) )?[a-z]+\s+(?:and|n|&|with|w|\/|over|on)\s+(?:(?:light|dark|bright|deep|neon) )?[a-z]+\s*[.!]*$/.test(stl) && !THEMES.some(function (th) { return th[0].test(f); })) { F.act = 'ask_back'; F.ops = []; F._g = 1; F.missing = ['target']; }
        if (!OF_CFG('noIA1')) { var offW = /\b(ivory|off[- ]?white|eggshell|bone white|bone|pearl white|antique white)\b/.exec(String(s).toLowerCase()); if (offW && !/\bcream\b/.test(f)) (F.ops || []).forEach(function (o) { var c = o && o.look && o.look.colour; if (c && c.word === 'white' && String(c.hex || '').toLowerCase() === '#ffffff') { c.word = offW[1] === 'bone' ? 'bone white' : offW[1]; c.hex = /pearl/.test(offW[1]) ? '#f3efe6' : '#efe6cc'; } }); }          // IA1 2026-10-07 (in-app train A-0591 'roof diffreent, white' -> 'roof ivory instead' = "nothing visible changed": ivory was pure white)
        if (!OF_CFG('noIA1') && /\bpowder\s*blue\b/i.test(String(s))) (F.ops || []).forEach(function (o) { var c = o && o.look && o.look.colour; if (c && /^(?:blue|light blue)$/.test(String(c.word || ''))) { c.word = 'powder blue'; c.hex = '#a7cfe8'; } });          // IA1 2026-10-07 (train A-0345 'no not that blue, more powder': powder blue was plain blue #1f4dff = darker)
        if (!OF_CFG('noJ5p') && !W.SPB_OF_NOJ5P) { var pm5 = /\b(lower|upper|bottom|top|front|rear|back)\s+(half|third|quarter)\b/i.exec(String(said || s)); if (pm5) { var pw5 = { bottom: 'lower', top: 'upper', back: 'rear' }[pm5[1].toLowerCase()] || pm5[1].toLowerCase(), pt5 = pw5 + ' ' + pm5[2].toLowerCase();          // IA1 J5p 2026-10-07: 'only the lower half' of a part
            (F.ops || []).forEach(function (o) { if (o && o.target && o.target.kind === 'part' && !o.target.portion) o.target.portion = pt5; }); } }
        var gNet = !!F._g; delete F._g; (F.ops || []).forEach(function (o) { delete o.defBody; delete o.unpaint; });
        if (F.act === 'change' && !OF_CFG('noDoor')) { try { var DRh = W.SpbIntentDoor; if (DRh && DRh.annotate) DRh.annotate(F, s, env); } catch (eDr) {} }          // D-DOOR 2026-10-08 hook: door / fender / quarter / rocker words -> portion of the side panel (or an ask); kill SPB_DOOR_OFF or SPB_OF_CFG.noDoor
        var v = IF.validate(F, env), conf = rd.confidence;
        if (!v.ok) return { frame: null, want: want, confidence: 0, source: 'invalid', errors: v.errors };
        return { frame: F, want: want, confidence: conf, source: 'of:' + want, shape: rd.shape, said: said, fixes: fixes, feat: (imperA ? 'I' : '') + (hasLk ? 'L' : '') + (hasTg ? 'T' : '') + (hasLastE ? 'R' : '') + (prev ? 'P' : '') + ':' + (rd.want || ''),          // V4-G: feat = imperative / look / target / last change / previous turn : the kNN's own want
            guard: want0 === 'change' && (F.act === 'answer' || F.act === 'nothing' || gAsk || gNet) ? 'rule' : null, want0: want0 };          // V4-G: a guard rule (question / trouble / ask-rule / harm net) turned the neighbours' change into an answer or an ask
    }
    function regexStrong(r, text, rxF, env) {
        var KN = W.SpbIntentKnn; if (!r) return false;
        return !!(KN && !KN.weak(r, text, env));
    }
    // the mix policy (the route() hook calls this): the regex reader keeps its confident results; otherwise the frame; but a frame that would only ASK
    // (or do nothing) never overrides a regex result that acts on a named target (the regex reader then answers / acts as before)
    // ------------------------------------------------------------------ C-OFFVAGUE 2026-10-08 (owner restraint rule, offline half of R14-VAGUE): a VAGUE / mood / taste / country-colour / "like the car that won X" ask
    // ("Brazil colours", "a patriotic look", "pastel livery, something kind", "make it pop") changes NOTHING offline too: the reply is an ASK with 2-3 concrete imperative options as chips ("make the body green, the roof yellow ...")
    // PLUS the relevant ideas article (hits / enc) when one exists. A pick (a tapped chip or "the second one") runs the chosen option; "surprise me" is the host's. A named classic livery (Martini, Gulf, JPS ...) is NOT vague: it paints (THEMES).
    // The same classifier + option sets run in-app (js/spb-pro-ai.js SpbR14); this copy feeds the offline route (frame F._vague -> spb-offline-answer.js offlineFrame4f). Kill: SPB_OF_CFG.noVague or SPB_OFFLINE_VAGUE = '0'.
    var V_PART = /\b(hood|bonnet|roof|trunk|boot|doors?|fenders?|wings?|bumpers?|spoilers?|mirrors?|sides?|quarters?|splitter|diffuser|rockers?|skirts?|windshield|windscreen|windows?|stripes?|numbers?|sponsors?|logos?|decals?|layers?|zones?|panels?|pillars?|grille|wheels?|lowers?|uppers?|lip|cab|bed|cowl|nose|tail)\b/i;
    var V_COLOUR = /\b(red|blue|green|yellow|orange|purple|pink|white|black|gr[ae]y|silver|gold|golden|teal|cyan|brown|navy|lime|maroon|burgundy|bronze|copper|violet|magenta|turquoise|tan|beige|cream|lavender|mint|peach|aqua|crimson|scarlet|amber|olive|charcoal|gunmetal|ivory)\b|#[0-9a-f]{3,8}\b/i;
    var V_FINISH = /\b(matte|matt|gloss|glossy|satin|chrome|carbon|candy|metallic|pearl|pearlescent|holo|holographic|flakes?|flames?|camo|camouflage|checker(?:ed)?|checkers|plaid|stripes?|gradient|fade|rust|mud|dirty|dust|tribal|splatter|snake|skull|wrap|brushed|glitter|neon|iridescent|chameleon|color ?shift|colou?rshift|texture|pattern|graphic)\b/i;
    var V_NAMED = /\b(martini|gulf|jps|john player|rothmans|marlboro|castrol|repsol|jagermeister|jager|monster|red bull|redbull|nascar|bud|budweiser|coca|pepsi|ferrari|lamborghini|mclaren|porsche|bmw|mercedes|ford|chevy|dodge)\b/i;
    var V_ASKQ = /^\s*(?:how|what|where|why|when|who|which|is|are|does|do|did|will|would|should|could|can i|can you (?:tell|explain|show me how)|ideas?\b|any ideas|suggest|recommend|explain|tell me)\b/i;
    var V_VAGUE = [
        ['soft', /\b(pastel|kind|gentle|soft|friendly|cute|sweet|nice|warm|calm|peaceful|happy|summer(?:y)?|spring(?:y)?|candy ?floss|dreamy|cheerful|pretty|beautiful|gorgeous|lovely)\b/i],
        ['speed', /\b(fast|speed(?:y)?|quick|aggressive|mean|angry|menacing|scary|tough|fierce|brutal|badass|bad ?ass|savage|wild|crazy|intimidating|dangerous|racy|sporty|powerful|muscle)\b/i],
        ['luxe', /\b(expensive|rich|luxury|luxurious|premium|upscale|elegant|classy|fancy|sleek|sophisticated|high ?end|posh|refined|clean|simple|minimal(?:ist)?|professional)\b/i],
        ['retro', /\b(retro|vintage|old ?school|classic|throwback|80s|70s|60s|90s|nostalgic)\b/i],
        ['moody', /\b(moody|dark vibe|dark and|gothic|sinister|stealthy|stealth|night(?:time)?|mysterious|shadowy|edgy)\b/i],
        ['modern', /\b(modern|futuristic|techy|high ?tech|cyber|space age|sci ?fi)\b/i],
        ['unique', /\b(unique|unusual|different|original|one of a kind|nobody has seen|no ?one has seen|never been seen|never seen|nobody'?s seen|nobody else|stand out from|special|something new)\b/i],
        ['pop', /\b(pop|pops|stand out|eye ?catching|attention|bold|loud|flashy|striking|wow|vibe|vibes|personality|character|flair|swag|cool|cooler|sick|awesome|fresh|better|improve|dope|fire|hot|amazing|epic|insane|nicer|prettier|looks? (?:good|great|nice|amazing|awesome)|good ?looking|beautiful)\b/i]
    ];
    var V_COUNTRY = [
        ['brazil', /\b(brazil(?:ian)?|brasil)\b/i], ['italy', /\b(ital(?:y|ian))\b/i], ['germany', /\b(german(?:y)?)\b/i], ['france', /\b(french|france)\b/i], ['uk', /\b(british|britain|uk|english|england|union jack)\b/i],
        ['usa', /\b(patriotic|american|usa|america|stars and stripes)\b/i], ['mexico', /\b(mexic(?:o|an))\b/i], ['japan', /\b(japan(?:ese)?)\b/i], ['netherlands', /\b(dutch|netherlands|holland)\b/i],
        ['sweden', /\b(swed(?:en|ish))\b/i], ['spain', /\b(spain|spanish)\b/i], ['ireland', /\b(irish|ireland)\b/i], ['australia', /\b(australia(?:n)?|aussie)\b/i], ['canada', /\b(canad(?:a|ian))\b/i], ['argentina', /\b(argentin(?:a|ian))\b/i]
    ];
    var V_SETS = {
        pop: ['black body, neon yellow hood and roof', 'white body, red hood and roof', 'deep blue body, orange roof'],
        speed: ['matte black body, red hood', 'dark grey body, carbon fibre roof and hood', 'black body, red flames on both sides'],
        luxe: ['pearl white body, gold roof', 'gloss black body, silver roof', 'deep burgundy body, gold hood'],
        soft: ['light pink body, white roof', 'baby blue body, white roof', 'mint green body, pale yellow hood'],
        retro: ['orange body, white roof', 'teal body, cream roof', 'yellow body, black hood'],
        moody: ['matte black body, dark purple roof', 'gunmetal grey body, black hood', 'dark green body, black roof'],
        modern: ['satin grey body, black roof and hood', 'white body, black roof, blue hood', 'matte black body, white roof'],
        unique: ['purple body, lime green roof', 'black body, holographic roof', 'black body, gold chrome hood'],
        winner: ['white body, blue roof, red hood', 'red body, white roof', 'yellow body, black roof'],
        brazil: ['green body, yellow roof, blue hood', 'yellow body, green hood and roof'], italy: ['white body, green hood, red roof', 'red body, white roof, green hood'],
        germany: ['black body, red hood, gold roof', 'white body, black roof, red hood'], france: ['blue body, white roof, red hood', 'white body, blue roof, red hood'],
        uk: ['blue body, white roof, red hood', 'british racing green body, yellow roof'], usa: ['blue body, white roof, red hood', 'white body, red hood, blue roof'],
        mexico: ['green body, white roof, red hood', 'white body, green hood, red roof'], japan: ['white body, red roof', 'red body, white roof'],
        netherlands: ['orange body, white roof, blue hood', 'orange body, blue roof'], sweden: ['blue body, yellow roof', 'yellow body, blue hood and roof'],
        spain: ['red body, yellow roof', 'yellow body, red hood and roof'], ireland: ['green body, white roof, orange hood', 'white body, green hood, orange roof'],
        australia: ['green body, gold roof', 'gold body, green hood and roof'], canada: ['red body, white roof', 'white body, red hood and roof'], argentina: ['light blue body, white roof', 'white body, light blue hood and roof']
    };
    function vPhrase(o) {          // "black body, neon yellow hood and roof" -> "make the body black, the hood and roof neon yellow"
        var out = [];
        o.split(', ').forEach(function (g, i) {
            var m;
            if (i === 0 && (m = /^(.*) body$/.exec(g))) { out.push('make the body ' + m[1]); return; }
            if ((m = /^(.*?) flames on both sides$/.exec(g))) { out.push('add ' + m[1] + ' flames on both sides'); return; }
            if ((m = /^(.*?) ((?:hood|roof)(?: and (?:hood|roof))?)$/.exec(g))) { out.push('the ' + m[2] + ' ' + m[1]); return; }
            out.push(g);
        });
        return out.join(', ').replace(/, (add )/, ' and $1');
    }
    var V_ARTICLE = {          // vague set -> the ideas article that backs it (the options reply links it: "best of both")
        pop: ['ideas.make_it_pop', 'Make it pop: contrast of colour AND shine'], speed: ['ideas.aggressive_mean', 'Aggressive and mean: dark, sharp, one hot accent'],
        luxe: ['ideas.look_expensive', 'Make it look expensive'], soft: ['ideas.pastel', 'Pastel: soft mint, peach, baby blue and pink'],
        retro: ['ideas.retro_70s', 'Retro 70s: cream, orange and brown with warm earth tones'], moody: ['ideas.stealth_murdered_out', 'Stealth and murdered-out: black on black'],
        modern: ['ideas.satin_modern_oem', 'Satin and modern OEM: soft sheen, no hard reflections'], usa: ['ideas.patriotic_rwb', 'Patriotic red, white and blue: stars, stripes and fireworks'],
        unique: ['ideas.holographic_iridescent', 'Holographic and iridescent: rainbow shine that moves'], japan: ['ideas.japanese_art', 'Japanese art: waves, cranes, sunbursts and lacquer']
    };
    function vWords(t) { return String(t || '').toLowerCase().replace(/[^a-z0-9#' ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    function vagueSetOf(text) {
        var t = String(text || ''); if (!t || t.length > 120) return null; var w = vWords(t); if (w.split(' ').length > 16) return null;
        if (V_ASKQ.test(t.replace(/^\s*(?:hey|hi|ok|okay|so|please)[ ,]+/i, ''))) return null;
        if (/\b(undo|redo|revert|put it back|go back|render|export|save|download|install|iracing|template|psd|layer|zone|wireframe|spec map|same colou?rs?|keep|shin(?:y|e)|gloss\w*|flag|translate|on each|each driver|ideas?|not|no|nothing|without)\b/i.test(t)) return null;
        if (V_PART.test(t) || V_FINISH.test(t) || V_NAMED.test(t)) return null;
        var i;
        for (i = 0; i < V_COUNTRY.length; i++) if (V_COUNTRY[i][1].test(t) && /\b(colou?rs?|livery|flag|theme|look|scheme|style|vibe|paint|car)\b/i.test(t) && !V_COLOUR.test(t)) return V_COUNTRY[i][0];
        if (V_COLOUR.test(t)) return null;          // a colour the buyer named makes it concrete ("ice cream truck, pastel pink and mint")
        if (/\b(?:like|as|similar to|same as)\b[^.]{0,40}\b(?:won|winner|winning|champion|champ|that raced|that ran|from the|in the)\b/i.test(t) || /\b(?:car|livery|paint|scheme)\b[^.]{0,20}\b(?:that|which) won\b/i.test(t) || /\bthe winner'?s\b/i.test(t)) return 'winner';
        for (i = 0; i < V_VAGUE.length; i++) if (V_VAGUE[i][1].test(t)) return V_VAGUE[i][0];
        return null;
    }
    function vagueGuide(set) { return !/^(winner|brazil|italy|germany|france|uk|usa|mexico|japan|netherlands|sweden|spain|ireland|australia|canada|argentina)$/.test(set); }
    function vagueBuild(set) {
        var o = (V_SETS[set] || V_SETS.pop).map(vPhrase), name = ({ winner: 'I cannot tell which car that was, and I have not changed anything.', brazil: 'Brazil colours can go a few ways, so I have not changed anything yet.' })[set];
        var lines = o.map(function (x, i) { return (i + 1) + ') ' + x; }).join('  ');
        return { set: set, opts: o, text: (name || 'Nothing changed yet, so you are in charge.') + ' Which of these do you want? ' + lines + '. Tap one or say "the second one", or say "surprise me" and I will pick.' };
    }
    function vagueFrame(text, r, env) {
        if (flag('SPB_OFFLINE_VAGUE', '1') === '0' || OF_CFG('noVague')) return null;
        if (env && (env.pending || env.list)) return null;
        if (env && (env.last || env.planLast) && /\b(?:it|that|this|them|down|up|more|less|too|again|still|now|instead)\b/i.test(String(text || ''))) return null;          // answering a question / picking from a list / a change already made this chat ("calm it down" edits it) is not a new vague ask
        if (/\b(?:i|you) mean\b|\b(?:calm|tone|turn|dial)\b[^.]{0,12}\b(?:down|up|back)\b/i.test(String(text || ''))) return null;          // the buyer is answering a question / picking from a list: that is not a new vague ask
        var set = vagueSetOf(text); if (!set) return null;
        var art = null;
        if (r && r.cls === 'ANSWER' && r.answer && !r.local && !/^local\./.test(String(r.answer.id || ''))) {          // a real encyclopedia answer (support.*, recipes.*, a specific ideas.* article) is the better reply: leave it
            var aid = String(r.answer.id || '');
            if (vagueGuide(set) && (!/^ideas\./.test(aid) || /^ideas\.(?:readable_on_tv|stand_out_in_pack|retro_70s|le_mans_endurance|old_school_muscle)$/.test(aid))) return null;
            if (/^ideas\./.test(aid) && vagueGuide(set)) art = [aid, r.answer.title || aid];
        }
        if (!art && V_ARTICLE[set]) art = V_ARTICLE[set];
        art = w14Decade(art, text);          // W14A 2026-10-09: "retro 80s" -> the 80s article
        var b = vagueBuild(set), F = { act: 'ask_back', ops: [], missing: ['what'], question: b.text, chips: b.opts, _vague: set };
        if (art) { F.hits = [{ id: art[0], title: art[1] }]; F.enc = [{ id: art[0], title: art[1] }]; }
        return F;
    }
    var V_SURPRISE = /\b(surprise me|surprise us|just do it|you pick|you choose|you decide|your choice|your pick|up to you|dealer'?s choice|anything( goes| is fine)?|whatever( you like| you want| works)?|go wild|any of them|any one|pick for me|choose for me|decide for me|i don'?t care|dont care|doesn'?t matter|either)\b/i;
    var V_AFFIRM = /^\s*(?:yes|yeah|yep|yup|yea|ok|okay|sure|alright|please|that one|this one|that|do that|do it|go with that|go for it|sounds good|sounds great|perfect|love it|lets do (?:that|it)|let'?s do (?:that|it)|that works|looks good|good|great|nice|yes please|yes that|yes that one|yes do that|yes do it|thats? good|that'?s good|go ahead)\b[\s.!,]*(?:please|one|that|it|thanks|thank you)?[\s.!]*$/i;
    // a pick the host's chip memory cannot read ("yes that", "go with that", "surprise me", "just do it", "the last one"): the host (spb-offline-answer.js route, env.chips) asks here first; only chips THIS module issued count.
    function vaguePick(text, chips) {
        if (flag('SPB_OFFLINE_VAGUE', '1') === '0' || OF_CFG('noVague') || !chips || !chips.length) return null;
        var mine = false; Object.keys(V_SETS).forEach(function (k) { if (!mine && V_SETS[k].map(vPhrase).indexOf(String(chips[0])) !== -1) mine = true; }); if (!mine) return null;
        var t = String(text || ''), w = vWords(t), n = chips.length; if (!w || w.split(' ').length > 9) return null;
        if (V_SURPRISE.test(t)) return String(chips[(w.length + n) % n]);
        if (/\b(?:the )?(?:last|final|other) one\b/.test(w) || /^(?:the )?last\b/.test(w)) return String(chips[n - 1]);
        if (V_AFFIRM.test(t) && !V_COLOUR.test(w)) return String(chips[0]);
        return null;
    }
    /* W14A-BEGIN 2026-10-09 lane W14-APP: the 'retro' vague set always pointed at ideas.retro_70s, so "retro 80s" (and 60s / 90s) showed the 70s article although ideas.retro_80s exists (it was never a content gap). The decade the buyer names now picks its own article. Kill switch window.SPB_W14A_OFF = true. */
    var W14_DEC = [[/\b(?:19)?60'?s\b|\bsixties\b/i, 'ideas.retro_60s', 'Retro 60s: powder blue, mod blocks and sunburst'], [/\b(?:19)?70'?s\b|\bseventies\b/i, 'ideas.retro_70s', 'Retro 70s: cream, orange and brown with warm earth tones'], [/\b(?:19)?80'?s\b|\beighties\b/i, 'ideas.retro_80s', 'Retro 80s: hot pink, cyan and sharp colour blocks'], [/\b(?:19)?90'?s\b|\bnineties\b/i, 'ideas.retro_90s', 'Retro 90s: teal, purple and magenta splashes']];
    function w14Decade(art, text) {          // [id, title] -> the article of the decade named in the sentence, else unchanged
        if (!art || (typeof window !== 'undefined' && window.SPB_W14A_OFF) || !/^ideas\.retro_\d0s$/.test(String(art[0] || ''))) return art;
        var t = String(text || ''), hit = null; W14_DEC.forEach(function (d) { if (!hit && d[0].test(t)) hit = d; });
        return hit ? [hit[1], hit[2]] : art;
    }
    /* W14A-END */
    function vagueArticle(set, text) { return w14Decade(V_ARTICLE[set] || null, text); }
    function asky(F) { return !F || F.act === 'ask_back' || F.act === 'nothing' || (F.act === 'change' && (F.missing || []).length > 0); }
    function acts(F) { return !!(F && F.act === 'change' && (F.ops || []).length && !(F.missing || []).length && F.ops.every(function (o) { return o.target || o.ref; })); }
    function decide(text, prevTurns, env, r, rxF, opt) {
        if (!on()) return null;
        var vgF = null; try { vgF = vagueFrame(text, r, env); } catch (eVg) { vgF = null; }          // C-OFFVAGUE 2026-10-08
        if (vgF) return { frame: vgF, source: 'of:vague', confidence: 1 };
        var o = null; if (opt && opt.pre !== undefined) o = opt.pre; else { try { o = frameOf(text, prevTurns, env, opt); } catch (e) { o = null; } }
        // V4-G 2026-10-07: a frame whose GUARD rule stopped a paint job (a question, a trouble report, an owner ask-rule, a harm net) beats a regex reader that would paint
        if (o && o.frame && rxF && rxF.act === 'change' && !OF_CFG('noGuard') && (o.guard || (OF_CFG('knnVeto') && o.want0 !== 'change' && o.confidence >= 0.85 && o.frame.act !== 'change'))) return { frame: o.frame, source: 'of:guard', confidence: o.confidence, o: o };
        if (o && o.frame && o.frame.act === 'change' && !OF_CFG('noR8c') && r8Corr(String(text || '')) !== String(text || '')) return { frame: o.frame, source: 'of:r8c', confidence: o.confidence, o: o };          // R8-FIN 2026-10-08: a changed mind inside one message: the frame (last choice only) beats a regex reader that painted both or could not read the cue
        if (o && o.frame && o.frame.act === 'change' && o.want0 !== 'change' && r && /^(?:ANSWER|LOCAL|OFFTOPIC)$/.test(r.cls || '') && !(r.steps || []).length && r8Any(String(text || '').toLowerCase())) return { frame: o.frame, source: 'of:r8f', confidence: o.confidence, o: o };          // R8-FIN 2026-10-08: "glow in the dark hood" read as an answer card = a finish phrase + a part
        if (regexStrong(r, text, rxF, env)) {
            // V4-G G19 (job 3, by kind): a complete frame-first paint job beats a regex reader that only asks; (G21, on) a frame-first answer beats a painting regex reader
            if (!OF_CFG('noG19') && o && o.frame && acts(o.frame) && o.confidence >= (OF_CFG('g19c') || 0) && (asky(rxF) || (rxF && rxF.act === 'change' && (rxF.ops || []).some(function (q) { return !hasLook(q.look) && !q.relative && !q.ref && !q.source && !/^(hide|show|copy_look|retarget|undo)$/.test(q.verb || ''); })))) return { frame: o.frame, source: 'of:g19', confidence: o.confidence, o: o };
            // W1-PARSE 2026-10-08: the regex reader PREFILLed a question (an open step: it took the DESTINATION colour for a colour to hunt, 'main body colour to our brand blue #0B3D91') while the frame read a complete
            // body / part paint job with a look = the frame acts. Kill: SPB_OF_CFG.noW1p.
            if (!OF_CFG('noW1p') && o && o.frame && r && r.cls === 'PREFILL' && acts(o.frame) && o.frame.ops.every(function (q) { return q.target && /^(body|part)$/.test(q.target.kind) && hasLook(q.look); })) return { frame: o.frame, source: 'of:w1p', confidence: o.confidence, o: o };
            if (!OF_CFG('noAnsVeto') && o && o.frame && o.frame.act === 'answer' && rxF && rxF.act === 'change') return { frame: o.frame, source: 'of:ansveto', confidence: o.confidence, o: o };
            return { frame: null, source: 'regex-strong', o: o };
        }
        if (!o || !o.frame || o.confidence < TH.use) return { frame: null, source: 'regex-fb', o: o };
        // V4-G G22 (job 3): a first-turn text with no target the frame could read (no part / layer / element, no last change, no earlier turn) keeps the frame's question
        if (!OF_CFG('noG22') && asky(o.frame) && o.frame.act !== 'nothing' && !/[TRP]/.test(String(o.feat || '').split(':')[0]) && acts(rxF)) return { frame: o.frame, source: 'of:g22', confidence: o.confidence, o: o };
        if (asky(o.frame) && (acts(rxF) || (rxF && rxF.act === 'answer' && o.frame.act === 'nothing'))) return { frame: null, source: 'regex-acts', o: o };
        return { frame: o.frame, source: o.source, confidence: o.confidence, o: o };
    }
    // W9ARB-BEGIN 2026-10-09 (lane W9-ARB, kill: window.SPB_W9ARB_OFF or SPB_OF_CFG.noW9Arb). W8-KNN finding: on reworded edits 61% of failing turns had the kNN class RIGHT (change) but the
    // frame-first path answered / asked (a guard rule fired on polite or terse wording; the regex reader's ASK / ANSWER kept). Arbitration (called from spb-offline-answer.js offlineFrame4f, ff policy):
    // when the final frame is NOT a change, the neighbours voted change (o.want0) with confidence >= W9_TH, the change frame rebuilt from the CURRENT utterance (guards bypassed: opt.w9force) is COMPLETE
    // (acts(): every op has a target, nothing missing) and names a concrete part / layer / element (a bare whole-car guess needs explicit whole-car words), and the text carries no question / how-to /
    // complaint / protect cue = the frame acts. Metrics: _easy_claude_work/eval/w9arb/REPORT.md.
    var W9_TH = 0.4, W9_LOGONLY = false, W9_POL = true, W9_LEX = true, W9_ABBR = true, W9_NORM = true;
    function w9Abbr(t) { try { var K = W.SpbIntentKnn; return (w9on() && W9_ABBR && !OF_CFG('noW9Abbr') && K && typeof K.abbr === 'function' && typeof t === 'string') ? K.abbr(t) : t; } catch (e) { return t; } }
    var W9_WHOLE = /\b(?:whole|entire|all of the|all over|overall|everything|full)\b|\b(?:the|my|this|our) (?:car|truck|body|ride|whip)\b|\b(?:car|body|truck) (?:to |in |go |gets? )?(?:red|blue|green|black|white|yellow|orange|purple|pink|silver|gold|grey|gray)\b/i;
    var W9_QCUE = /\?|\b(?:how (?:do|can|to|would|should|could)|what (?:is|does|are|happens)|why|which (?:one|is|colou?r|looks?)|should i|do you think|would (?:it|that|this) look|is it (?:possible|ok|okay)|can i (?:paint|put|have|use|get|make|do)|any (?:ideas?|suggest\w*)|recommend\w*|suggest\w*|explain|tutorial|steps|too (?:much )?(?:shiny|shiney|glossy|dull|flat|dark|bright)|hard to (?:read|see)|looks? (?:off|wrong|bad|plastic|weird))\b/i;
    // W9ARB polite-request normaliser (kill SPB_W9ARB_OFF / SPB_OF_CFG.noW9Arb or noW9Pol): "Hi there! Would it be possible to change just the bumper ...", "Would you mind making the whole car blue ... thanks so much!",
    // "I was hoping you could set the bodywork to #FFF" = the plain imperative ("change just the bumper ...", "make the whole car blue ..."). The Q_START / 'would it' / 'possible' wording made the readers
    // ANSWER a request. Only fires when what follows the polite lead starts with a paint-edit verb (so "would you explain how ..." / "is it possible to ..." stay questions).
    var W9_GER = { making: 'make', changing: 'change', painting: 'paint', giving: 'give', putting: 'put', setting: 'set', turning: 'turn', applying: 'apply', adding: 'add', doing: 'do', using: 'use', swapping: 'swap', switching: 'switch', coating: 'coat', wrapping: 'wrap', spraying: 'spray', colouring: 'colour', coloring: 'color', recolouring: 'recolour', recoloring: 'recolor', filling: 'fill', copying: 'copy', matching: 'match', updating: 'update', dropping: 'drop', going: 'go', taking: 'take', keeping: 'keep', leaving: 'leave' };
    var W9_IMP = '(?:make|paint|change|turn|put|give|apply|add|swap|set|go|do|use|switch|colou?r|recolou?r|shrink|enlarge|scale|bump|increase|decrease|lower|raise|darken|lighten|brighten|soften|remove|copy|duplicate|mirror|match|spray|wrap|coat|fill|restore|update)';
    var W9_CONCRETE = /#[0-9a-f]{3,8}\b|\b(?:hood|bonnet|roof|trunk|boot|doors?|fenders?|wings?|bumpers?|spoilers?|mirrors?|sides?|quarters?|splitter|lip|diffuser|skirts?|rockers?|layers?|numbers?|sponsors?|logos?|decals?|stripes?|panels?|red|blue|green|yellow|orange|purple|pink|white|black|silver|gold|grey|gray|brown|teal|navy|cyan|maroon|crimson|scarlet|lime|chrome|matte|satin|gloss\w*|opacity|saturation|hue|brightness|size|scale)\b/i;
    var W9_GREET = /^\s*(?:(?:hi|hey|hello|hiya|yo|ok|okay|alright|right|so|well|hmm+|um+|oh|then|and|now|next|also|actually)\b(?:\s+there)?[\s,!.:;-]*)*/i;
    var W9_BARE = /^(?:could|can|will)\s+(?:you|u|we)(?:\s+(?:please|kindly|possibly|just|maybe))*[\s,]*(?:please\s+)?$/i;
    var W9_LEAD = /^\s*(?:(?:hi|hey|hello|hiya|yo|ok|okay|alright|right|so|well|hmm+|um+|oh|then|and|now|next|also|actually)\b(?:\s+there)?[\s,!.:;-]*)*(?:(?:would|do)\s+you\s+mind|i\s+(?:was\s+)?(?:hoping|wondering|thinking)\s+(?:if\s+)?(?:you\s+)?(?:could|can|would)|(?:i'?d|i\s+would)\s+(?:like|love|appreciate)\s+(?:it\s+)?(?:if\s+you\s+(?:could|would|can)|you\s+to|for\s+you\s+to)|i\s+(?:need|want)\s+you\s+to|(?:would|could|can|will)\s+(?:you|u|we)(?:\s+(?:please|kindly|possibly|just|maybe))*(?:\s+(?:be\s+able\s+to))?|(?:would|do)\s+you\s+mind|would\s+it\s+be\s+(?:possible|ok|okay|alright|fine)\s+(?:to|if\s+you)|any\s+chance\s+(?:you\s+(?:could|can)|of))[\s,]*(?:please\s+)?/i;
    var W9_TAIL = /[\s,;.!?-]*(?:(?:thanks|thank\s+you|thx|cheers|ta|much\s+appreciated|appreciate\s+it)(?:\s+(?:so\s+much|a\s+lot|very\s+much|a\s+bunch|in\s+advance|mate|man))?|if\s+that'?s\s+(?:ok|okay|alright|fine)|if\s+that\s+works|please|pls|plz)?[\s.!?]*$/i;
    function w9Polite(t) {
        if (!w9on() || !W9_POL || OF_CFG('noW9Pol') || typeof t !== 'string' || t.length > 400) return t;
        var m = W9_LEAD.exec(t); if (m && W9_BARE.test(m[0].replace(W9_GREET, ''))) return t;          // a bare "can/could you" lead was already read right (dev: "can u make my car look like a race car" = ask)
        if (!m || !/(?:would|could|can|will|mind|hoping|wondering|thinking|like|love|appreciate|need|want|possible|ok|okay|alright|fine|chance)/i.test(m[0])) return t;
        var rest = t.slice(m[0].length), gm = /^(\w+ing)\b/i.exec(rest);
        if (/\bmind\b/i.test(m[0]) && gm && W9_GER[gm[1].toLowerCase()]) rest = W9_GER[gm[1].toLowerCase()] + rest.slice(gm[1].length);
        if (!new RegExp('^' + W9_IMP + '\\b', 'i').test(rest)) return t;
        if (/\b(?:how|why|what|which|whether)\b[^.]{0,30}\?/i.test(rest) && !/\bwhat(?:ever)? (?:you|looks)\b/i.test(rest)) return t;
        if (!W9_CONCRETE.test(rest)) return t;          // nothing concrete (no part / layer / element / colour / hex): "put some camouflage on the car" is a vague whole-car ask, not an order
        rest = rest.replace(W9_TAIL, '').replace(/\?+\s*$/, '').replace(/\s+/g, ' ').trim();
        return rest.length >= 6 ? rest : t;
    }
    var W9_BODY_IN = 'bodywork|(?:the |my |our |this |whole |entire |full )vehicle|(?<=\\b(?:make|paint|turn|change|colou?r|recolou?r|do|wrap) )vehicle|main (?:body|panels?|shell|section)|(?:the |my |our |whole |entire |full )ride', W9_BODYX = new RegExp('\\b(?:' + W9_BODY_IN + ')\\b');
    function w9BodyRe() { var src = BODY_W.source; if (w9on() && W9_LEX) src = src.replace('\\b(?:', '\\b(?:' + W9_BODY_IN + '|'); return new RegExp(src, 'g'); }
    // arbitration is narrow on purpose (W9 gates: bypassing the guard rules broadly cost R-003/R-018 asks, comparisons, acks, undo): only a WISH statement ("I need the doors cleaned up", "I'm picturing that woven
    // carbon look", "maybe pearl would look nicer instead", "how about the hood in gold") with a complete concrete frame, and none of the compare / check / undo / keep / ack words.
    var W9_WISH = /\b(?:i(?:'?m| am)?\s+(?:picturing|imagining|thinking|leaning|want|need|wanna|gonna|going to)|i(?:'?d| would)\s+(?:like|love|prefer)|we(?:'?d| would)?\s+(?:need|want|like)|maybe|perhaps|how about|what about|what if|let'?s|i think (?:the|it)|i'?d go with)\b/i;
    var W9_NOARB = /\b(?:vs|versus|than|compar\w*|double[- ]?check|verify|avoid\w*|back|undo|revert|fine|readable|stays?|keep|leave|same as)\b/i;
    // W9ARB wording normaliser (flag n): "the top" (no part word after it) = the roof, "a solid #0B3D91" / "solid black" = the plain colour (the word 'solid' made the regex reader ask for a finish), "wing mirrors" = mirrors.
    var W9_TOP = /(^|[\s,;(])(the|my|our)\s+top\b(?!\s+(?:of|half|layer|coat|part|section|edge|stripes?|bit|end|line|notch|speed|third|portion|row|\d|left|right|corner|wing|spoiler|mirrors?|logos?|numbers?|colou?r|shade|finish|gloss))/gi;
    var W9_SOLID = /\b(?:an? )?solid(?:\s+colou?r)?\s+(?=#[0-9a-f]{3,8}\b|(?:red|blue|green|yellow|orange|purple|pink|white|black|silver|gold|grey|gray|brown|teal|navy|cyan|maroon)\b)/gi;
    function w9Norm(t) {
        if (!w9on() || !W9_NORM || OF_CFG('noW9Norm') || typeof t !== 'string' || t.length > 500) return t;
        if (/\bfrom\b[^.]*\b(?:to|over|across|through|down|up)\b|\b(?:fade|gradient|ombre|stripes?|bands?|path|run(?:ning)?)\b/i.test(t)) return t.replace(W9_SOLID, '').replace(/\b(?:wing|door|side) mirrors?\b/gi, function (m) { return /s$/i.test(m) ? 'mirrors' : 'mirror'; });          // a path / gradient / stripe sentence: "the top" is where it runs, not a part
        return t.replace(W9_TOP, function (m, pre, det, off, str) { var before = str.slice(Math.max(0, off - 16), off + pre.length).toLowerCase(); return /\b(?:at|across|over|from|to|along|up|towards?|near|around|until|through|by|of|reach(?:es|ing)?)\s+$/.test(before) ? m : pre + det + ' roof'; }).replace(W9_SOLID, '').replace(/\b(?:wing|door|side) mirrors?\b/gi, function (m) { return /s$/i.test(m) ? 'mirrors' : 'mirror'; });
    }
    function w9on() { return !(W.SPB_W9ARB_OFF || OF_CFG('noW9Arb')); }
    function w9concrete(F, text) {
        var ops = F.ops || [], body = false, named = false;
        ops.forEach(function (q) { var t = q.target; if (q.ref || q.source) { named = true; return; } if (!t) return; if (t.kind === 'body') body = true; else named = true; });
        if (!ops.length) return false;
        if (body && !named && !W9_WHOLE.test(String(text || ''))) return false;
        return named || body;
    }
    function w9arb(o, d, text, pt, env, r) {
        if (!w9on()) return null;
        var rec = { text: String(text || ''), rcls: r && r.cls, ow0: o && o.want0, oconf: o && o.confidence, oact: o && o.frame && o.frame.act, oguard: o && o.guard, dact: d && d.frame && d.frame.act, why: null };
        var out = null;
        try {
            if (o && o.frame && !(d && d.frame && d.frame.act === 'change') && o.want0 === 'change' && (o.confidence || 0) >= W9_TH && (!r || /^(?:ASK|ANSWER|PREFILL|LOCAL|OFFTOPIC)$/.test(r.cls || '') || !r.cls)) {
                var tx = String(text || ''), c = o.frame.act === 'change' ? o : null;
                if (!c) { c = frameOf(text, pt, env, { r: r || null, w9force: true }); if (c && !(c.frame && c.frame.act === 'change')) c = null; }
                rec.cact = c && c.frame && c.frame.act; rec.ccomplete = !!(c && c.frame && acts(c.frame));
                if (c && c.frame && acts(c.frame)) {
                    if (!W9_WISH.test(tx) || W9_NOARB.test(tx)) rec.why = 'nowish'; else if (W9_QCUE.test(tx)) rec.why = 'qcue'; else if (!w9concrete(c.frame, tx)) rec.why = 'notconcrete'; else { rec.why = 'arb'; out = { frame: c.frame, source: 'of:w9arb', confidence: o.confidence, o: c }; }
                } else rec.why = c ? 'incomplete' : 'noforce';
            }
        } catch (e) { out = null; rec.why = 'err'; }
        try { var lf = W.SPB_W9_LOG; if (typeof lf === 'function') lf(rec); } catch (e2) {}
        return (!W9_LOGONLY && out) ? out : null;
    }
    // W9ARB-END

    // W3-SCOPE 2026-10-09: the synonym pass alone, for the regex reader's route() (patch w3scope/patch_oa_syn.py): returns the text rewritten (lower-cased) or the SAME text when nothing matched. Kill SPB_OF_CFG.noW3S.
    // W3-SCOPE 2026-10-09 (class 5, kill noW3S): 'hood to match the blue in the logo' / 'roof should match the gold on the numbers' name an element only as the colour SOURCE (read-only). The regex reader (COPY4G route) also
    // recoloured that element. dropRef(r, text) removes the steps that paint the referenced element (numbers / sponsors) unless the text also asks to change it ("and the logos black"). Patch: patch_oa_syn.py.
    var REFSRC_RE = /\b(?:match(?:es|ing)?|same(?: \w+)? as|like|matching|to)\b[^.;!?]{0,40}?\b(?:in|on|of|from|as|with)\s+(?:the |my |our |that )?(numbers?|number layer|logos?|sponsors?|decals?)\b/;
    function dropRef(r, text) {
        try { if (OF_CFG('noW3S') || !r || r.cls !== 'DO' || !(r.steps || []).length) return r; var lo = String(text || '').toLowerCase(), m = REFSRC_RE.exec(lo); if (!m) return r;
            var isNum = /^number/.test(m[1]), keep = r.steps.filter(function (st) { var k = st && st.what && st.what.k; return !(isNum ? k === 'numbers' : k === 'sponsors'); });
            if (!keep.length || keep.length === r.steps.length) return r; if (new RegExp('\b(?:and|also|plus|then)\b[^.;!?]{0,25}\b' + (isNum ? 'numbers?' : '(?:logos?|sponsors?|decals?)') + '\b').test(lo.slice(m.index + m[0].length))) return r;
            r.steps = keep; r.w3sRef = true; } catch (e) {} return r;
    }
    // W15F-BEGIN 2026-10-09 (lane W15-FRAME; report: _easy_claude_work/eval/w15frame/PROGRESS.md). General LANGUAGE rules, not item fixes: a speech-act gate (an order needs positive evidence), keep / yardstick parts
    // are never painted, one side named = one side, regions / unpaintable words, vocabulary normaliser. Kill: window.SPB_W15F_OFF = true, SPB_OF_CFG.noW15F, localStorage SPB_W15F_OFF = '1'; one rule off: SPB_OF_CFG.noW15F_<key>.
    // ---- W15F speech act (pure text function; no state). w15fSpeech(text, ctx) -> {k, why}; ctx = { last: a change exists to follow up, pending: an offer / list is open }.
    // k = 'order' (positive evidence the buyer ASKED for a paint) | 'question' | 'wonder' | 'complaint' | 'state' | 'thanks' | 'options' | 'neutral' (no clear evidence: the readers decide as before).
    // A paint job needs positive evidence of an order (imperative, polite request, wish, "should be", an elliptical "hood red", a restated order). A sentence that only complains ("not loving the red"), wonders
    // ("I wonder if blue would suit the roof"), reports ("the roof is blue right now"), thanks ("looks great") or asks is never a paint order however many colours and parts it names.
    var F15_PW = '(?:hood|bonnet|roof|top|trunk|boot|lid|spoiler|wings?|bumpers?|nose|tail|splitter|diffuser|sides?|doors?|fenders?|quarters?|panels?|numbers?|nums?|digits?|sponsors?|logos?|decals?|stripes?|livery|car|body|everything|rest|mirrors?|flanks?|ailerons?|crown)';
    var F15_CW = '(?:red|orange|yellow|gold|green|lime|teal|cyan|blue|navy|cobalt|purple|violet|lilac|indigo|pink|magenta|white|silver|gr[ae]y|black|brown|maroon|burgundy|crimson|scarlet|bronze|copper|cream|beige|tan|charcoal|turquoise|mustard|neon|colou?rs?|shade|hue|tint|#[0-9a-f]{3,6}|reds|blues|greens|whites|blacks|golds|silvers)';
    var F15_FW = '(?:matte|matt|gloss\\w*|satin|chrome|carbon|candy|pearl\\w*|metallic|metal|holo\\w*|brushed|camo\\w*|checker\\w*|flames?|galaxy|glitter|sparkle|flake|mirror|rough\\w*|smooth|shiny|shine|dull|fib(?:er|re)|weave|twill|forged|gradient|fade|stripe|pattern|texture|finish|clearcoat|clear coat|spec)';
    var F15_RW = '(?:darker|lighter|brighter|duller|shinier|glossier|bigger|smaller|larger|thinner|thicker|wider|narrower|softer|harder|bolder|warmer|cooler|deeper|paler|more|less|bit|touch|notch|shades?|tad|slightly|half|double|twice|step|redder|bluer|greener|yellower|pinker|whiter|blacker|purpler|oranger|greyer|browner)';
    var F15_PCF = new RegExp('\\b(?:' + F15_PW + '|' + F15_CW + '|' + F15_FW + ')\\b');
    var F15_V = '(?:make|paint|turn|change|put|give|apply|add|set|switch|swap|go|do|use|colou?r|recolou?r|repaint|respray|spray|wrap|cover|coat|fill|redo|fix|replace|convert|try|show|preview|render|bump|dial|tone|crank|push|pull|lighten|darken|brighten|dim|mute|soften|sharpen|smooth|take|drop|remove|strip|clear|copy|dupe|clone|match|mirror|repeat|extend|stretch|shrink|enlarge|scale|rotate|flip|move|shift|place|stick|slap|throw|drape|dip|stripe|outline|border|finish|polish|gloss|bring|get|hit|ditch|restyle|redesign|customi[sz]e|decorate|design|create|generate|draw|write|print|stamp|sort|clean|tidy|update|adjust|alter|modify|tweak|edit|undo|revert|reset|hide|unhide|display|select|choose|pick|keep|leave|skip|let|reduce|increase|raise|lower|boost|cut|trim|thicken|thin|widen|narrow|invert|reverse|rebuild|refinish|resurface|double|halve|triple|quadruple|fade|blend|tint|scrap|equali[sz]e|blow|crush|squash|compress|tighten|loosen|ease|fatten|slim|lengthen|shorten|flatten|magnify|knock|kill|nix|axe|bin|zap|cull)';
    var F15_LEAD = '(?:(?:please|pls|plz|kindly|just|now|then|also|and|but|so|ok|okay|alright|right|well|hey|hi|hello|yes|yeah|yep|sure|actually|instead|next|first|finally|oh|wait|no|nah|nope|sorry|oops|hmm+|um+|uh+|go ahead and|go ahead|when you get a (?:sec|second|minute|moment|chance)|if you can|if possible|quickly|quick|maybe|perhaps|probably|possibly|even|really|actually|then|cheers)[ ,!.]+)*';
    var F15_COP = '(?:is|are|was|were|am|be|been|being|\'s|\'m|\'re|looks?|looked|looking|seems?|seemed|feels?|felt|came|come|comes|turned|turns|ended|went|goes|gone|got|gets|getting|appears?|reads?|sounds?|has|have|had|do|does|did|can|could|would|should|will|might|may|i|i\'m|im|i\'ve|it|it\'s|its|that|that\'s|this|they|they\'re|we|you|my|our|keeps?|kept|still|isn\'t|aren\'t|wasn\'t|don\'t|didn\'t)';
    var F15_ORD = [
        new RegExp('(?:^|[,;.!?:\\-]\\s*)' + F15_LEAD + '(?:' + F15_V + ')\\b(?!\\s+(?:you|u|ya)\\b)'),
        /\b(?:i need you to|i want you to|i'?d like you to|i would like you to|i'?d appreciate (?:it )?if you|would you mind|do you mind|mind (?:making|painting|changing|putting|doing)|go ahead and|let'?s|lets|let us|if you (?:could|can|would))\b/,
        /\bi (?:said|meant|asked for|told you|wanted|did say|did mean)\b/,
        /\b(?:instead|rather than|something else|something different|another (?:one|look|colou?r|finish|option)|a different (?:one|look|colou?r|finish)|try (?:another|something|a different)|swap (?:it|that|them) for|change (?:it|that|them) to|switch (?:it|that|them) to)\b/,
        /\b(?:goes?|gets?|becomes?|turns?) (?:the |a |an |our |my )?(?:#[0-9a-f]{3,6}|red|blue|green|yellow|orange|purple|pink|white|black|silver|gold|grey|gray|teal|navy|brown|chrome|matte|gloss|satin|candy|pearl|carbon|metallic)/,
        /\b(?:one|two|three|a few|a couple of|2|3|half a) shades? (?:darker|lighter|brighter|duller|deeper|paler)\b/
    ];
    var F15_POLITE = new RegExp('\\b(?:can|could|would|will|may|might|shall)\\s+(?:you|u|ya|someone|somebody|we|i)\\s+(?:please\\s+|pls\\s+|just\\s+|maybe\\s+|possibly\\s+|kindly\\s+|also\\s+|now\\s+|quickly\\s+)*(?:(?:get|have|see|try|make|paint|turn|change|put|give|apply|add|set|switch|swap|do|use|colou?r|recolou?r|repaint|spray|wrap|fix|replace|show|preview|copy|match|mirror|redo|undo|revert|bump|tone|dial|lighten|darken|brighten|dim)\\b)');
    var F15_POLITE_THE = new RegExp('\\b(?:can|could|would|will)\\s+(?:the|my|our|this|that|these|those|both|all|it)\\b[^.?!]{0,50}?\\b(?:be|go|get|become|have|turn|glow|shimmer|run|come|look like|look more|look less)\\b(?!\\s+(?:ok|okay|good|fine|better|nice|too|safe|allowed|possible|legal|a good idea|worth))');
    var F15_POSS = /\bwould it be possible (?:for you )?to\b/;
    var F15_DESIRE = /\b(?:i|we)(?:'d| would|'ll| will)?\s*(?:really |just |kind of |kinda |sort of |also |definitely |probably |now |do )?(?:want|need|wanna|gotta|prefer|wish|love to see|would love|love it if|like it if|like to see|like it|like them|like the|like a|like an|like some|like my|like to have|like)\b(?! to (?:know|learn|understand|ask|find out|figure|check|see how|see what|see if)\b)/;
    var F15_SOFT = /\b(?:how about|what about|why not|what if (?:we|you|i|it|the|my)|how bout|go with|going with|let's go with|lets go with)\b/;
    var F15_MODAL = /\b(?:should|needs? to|has to|have to|must|ought to|gotta|got to)\s+(?:be|go|get|become|look|have|turn|come out|stay)\b/;
    var F15_QSTART = /^\s*(?:(?:ok|okay|so|and|but|hey|hi|hmm+|um+|uh+|wait|also|quick question|question|btw|just curious|curious)[, ]+)*(?:how|what|whats|what's|why|which|where|when|who|whose|whom|is|are|was|were|does|did|has|have|had|am|can i|could i|should i|would i|may i|might i|will i|shall i|can it|could it|would it|will it|should it|can the|could the|does the|do i|do you|do we|do they|did i|any (?:idea|ideas|thoughts|suggestions|tips|advice|recommendations?)|anyone|anybody|is there|are there|tell me|explain|got any|have you got)\b/;
    var F15_WHSTART = /^\s*(?:(?:ok|okay|so|and|but|hey|hi|hmm+|um+|uh+|wait|also|quick question|question|btw|just curious|curious)[, ]+)*(?:how(?! ?(?:bout|about))|what(?! ?(?:about|if))|whats|what's|why(?! not)|which|where|when|who|whose|whom|is there|are there|tell me|explain|any (?:idea|ideas|thoughts|suggestions|tips|advice|recommendations?)|anyone|anybody)\b/;
    var F15_WONDER = /\b(?:i wonder|wondering|wonder if|wonder whether|pondering|debating|thinking (?:about|of|that|maybe)|considering|not sure (?:if|whether|about)|unsure (?:if|whether|about)|do you think|what do you think|you think|your (?:opinion|thoughts)|would it look|will it look|would that look|might look|might suit|would suit|would work|might work|could work|could suit|would look|what would|how would|maybe)\b/;
    var F15_NEGLIKE = /\b(?:not|n't|never|no longer)\s+(?:really\s+|that\s+|too\s+|very\s+|much\s+|quite\s+|so\s+|a\s+|exactly\s+|totally\s+|entirely\s+)*(?:loving|liking|feeling|digging|keen|happy|sold|impressed|satisfied|fan|into|working|great|good|ideal|perfect|what i (?:wanted|asked|meant|expected|had in mind))\b|\b(?:don'?t|do not|didn'?t|doesn'?t|cant|can'?t|cannot|couldn'?t)\s+(?:really\s+|quite\s+|much\s+)?(?:like|love|dig|care for|feel)\b/;
    var F15_HATE = /\b(?:hate|hates|hated|dislike|despise|detest|loathe|annoyed|annoying|frustrat\w+|disappoint\w+|unhappy|upset|bummed|sick of|tired of|fed up|bored (?:of|with)|had enough|regret|ugh+|meh|yuck|eww+|gross|ugly|awful|terrible|horrible|hideous|tacky|cheesy|plasticky|fake|messy|sloppy|drab|bland|lifeless|boring)\b/;
    var F15_TECH = /\b(?:render(?:ing|er|s)?|i-?racing|the sim|in[- ]?game|trading paints|tp|laggy|lagging|lag|crash\w*|freez\w*|bug(?:gy|s)?|glitch\w*|error|won'?t load|not loading|doesn'?t load|doesn'?t show|not showing|black screen|blank|slow|upload\w*|download\w*|export\w*|\.tga|\.mip|\.psd|spec map|file)\b/;
    var F15_NEGADJ = '(?:off|wrong|weird|odd|strange|funny|bad|worse|worst|awful|terrible|horrible|ugly|hideous|tacky|cheap|plasticky|fake|messy|sloppy|blotchy|patchy|streaky|muddy|grainy|noisy|busy|cluttered|washed|faded|dull|flat|boring|plain|bland|drab|lifeless|loud|garish|gaudy|much|heavy|overdone|excessive|glossy|shiny|saturated|pale|thin|crooked|uneven|different|hard to \\w+|too \\w+|so \\w+|way \\w+)';
    var F15_COMPL = [F15_NEGLIKE, F15_HATE,
        new RegExp('\\b(?:is|are|was|were|\'s|looks?|looked|looking|seems?|seemed|feels?|came out|come out|comes out|turned out|ended up|got|gets|getting)(?:\\s+(?:a bit|a little|a tad|kind of|kinda|sort of|sorta|pretty|really|so|too|way too|very|rather|quite|slightly|somewhat|bit|still|already|now|totally|super|fairly|almost))*\\s+' + F15_NEGADJ + '\\b'),
        /\b(?:a bit|a little|kind of|kinda|sort of|sorta|slightly|somewhat|rather|pretty)\s+(?:much|too \w+|off|wrong|dull|flat|bland|plain|busy|loud)\b/,
        /\b(?:has|have) been (?:altered|changed|messed|ruined|broken|moved|touched|reset)\b/];
    var F15_STATE = /\b(?:is|are|\'s|has been|have been)\s+(?:currently|right now|at the moment|atm|still|already|at present)\b|\b(?:right now|at the moment|atm|at present|currently)\b\s*[.!]*\s*$/;
    var F15_PRAISE = /^\s*(?:(?:oh|wow|ok|okay|yes|yeah|and|so|hey|hi|nice|great|cool|perfect|awesome|amazing|sweet|love it|loving it|thanks|thank you|thx|ty|cheers|looks? (?:so |really |pretty |quite |very )?(?:good|great|awesome|amazing|nice|perfect|sweet|fine|sick|clean|cool|better)|that'?s (?:great|good|perfect|awesome|nice|cool|fine|better|it)|good job|well done|nice one|exactly|that works|(?:the |my )?\w+(?: \w+)? (?:look|looks|looking) (?:so |really |pretty |quite |very )?(?:good|great|awesome|amazing|nice|perfect|sweet|fine|sick|clean|cool|better)(?: tbh| now| already| to me| though| honestly)*)[ ,.!]*)+$/;
    var F15_ACK = /^\s*(?:ok|okay|k|kk|alright|sure|fine|cool|yes|yeah|yep|yup|hm+|mm+|uh huh|got it|i see|understood|right|noted|ah|oh)[ .!]*$/;
    var F15_OPTS = /\b(?:show me|give me|offer me|suggest|list|what are)\s+(?:me\s+)?(?:two|three|four|a few|some|several|\d+)\s+(?:options?|ideas?|choices|looks?|examples?|variations?|versions?|alternatives?|suggestions?|designs?)\b|\bi'?ll (?:pick|choose)\b|\bi will (?:pick|choose)\b/;
    var F15_REL1 = new RegExp('\\b' + F15_RW + '\\b');
    function w15fSpeech(t0, ctx) {
        ctx = ctx || {};
        var t = String(t0 == null ? '' : t0).toLowerCase().replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d"]/g, '').replace(/\s+/g, ' ').trim();
        if (!t) return { k: 'neutral', why: 'empty' };
        var hasQ = /\?/.test(t), pcf = F15_PCF.test(t), i;
        var u = t.replace(/^(?:(?:hey|hi|hello|oh|ok|okay|so|well|hmm+|um+|uh+|and|but|also|btw|yo|alright|right|wow|ah|oops|sorry|yes|yeah)[,!. ]+)+/, '');
        if (/^\s*(?:[a-z']+\s+){0,4}?(?:how (?:do|can|could|would|should|to|does|did)|tell me how|show me how|explain how|what'?s the (?:best )?way to)\b/.test(u)) return { k: 'question', why: 'howto' };
        if (!w26Off()) { var w26s = String(t0 == null ? '' : t0).trim(); if (w26Pre(w26s) !== w26s) return { k: 'order', why: 'w26' }; }          // W26U 2026-10-10 (a self-correction / angry wrong-part fix / polite restore / modifier / palette / match order is an ORDER)
        for (i = 0; i < F15_ORD.length; i++) if (F15_ORD[i].test(t)) return { k: 'order', why: 'o' + i };
        if (!w21Off('polite') && /\?|\b(?:mind|wondering|hoping|thinking|okay|ok|possible|alright)\b/.test(t)) { var wpo = w21Polite(String(t0 == null ? '' : t0).trim()); if (wpo && wpo !== String(t0).trim()) return { k: 'order', why: 'polite21' }; }          // W21H SA_polite 2026-10-09
        if (!w23Off('qo')) { var wq23 = w23QO(String(t0 == null ? '' : t0).trim()); if (wq23 && wq23 !== String(t0).trim()) return { k: 'order', why: 'qo23' }; }          // W23U Q9 2026-10-09 (question + order in one turn: the order wins; see w23QO)
        if (!w23Off('sugg')) { var ws23 = w23Sugg(String(t0 == null ? '' : t0).trim()); if (ws23 && ws23 !== String(t0).trim()) return { k: 'order', why: 'sugg23' }; }          // W23U round 2 2026-10-10 (a 'how about / how bout / hw abt + a thing' SUGGESTION is order-ish, never a how-to question; see w23Sugg)
        if (!w23Off('qo')) { var wq23 = w23QO(String(t0 == null ? '' : t0).trim()); if (wq23 && wq23 !== String(t0).trim()) return { k: 'order', why: 'qo23' }; }          // W23U Q9 2026-10-09 (question + order in one turn: the order wins; see w23QO)
        if (!w21Off('complaint') && !hasQ) { var mcm = W21_CMPL.exec(t), mom = mcm ? W21_ORDV.exec(t.slice(mcm.index + mcm[0].length)) : null; if (mom && new RegExp('\\b(?:' + F15_CW + '|' + F15_FW + ')\\b|#[0-9a-f]{3,8}\\b').test(mom[1])) return { k: 'order', why: 'cfix2' }; }          // a complaint word, then a fix verb, then a look
        if (!w21Off('complaint') && !hasQ) { var mcf = W21_CFIXV.exec(t); if (mcf && new RegExp('\\b(?:' + F15_CW + '|' + F15_FW + ')\\b|#[0-9a-f]{3,8}\\b').test(t.slice(mcf.index + mcf[0].length))) return { k: 'order', why: 'cfix' }; }          // W21H SA_complaint_fix 2026-10-09
        if (!w23Off('feel') && !hasQ) { var wf23 = w23Feel(t, ctx); if (wf23) return wf23; }          // W23U 2026-10-10 (a FEELING about the look with no instruction = a complaint / thanks, never a follow-up of the last change; see w23Feel)
        if (/[,;.]\s*(?:so\s+|then\s+|please\s+|pls\s+|just\s+)?(?!(?:i|we|you|it|that|this|they|is|are|was|were|looks?|seems?)\b)[a-z]{3,}\s+(?:it|them|that|those|this|these)\s+(?:down|up|out|back|a bit|a little|some|more|less|to|by|into|over)\b/.test(t)) return { k: 'order', why: 'imp-it' };          // "...is too big, crush it down" = a complaint that ends in an order
        if (F15_POLITE.test(t) && (pcf || /\b(?:it|that|them|this|those|these)\b/.test(t))) return { k: 'order', why: 'polite' };
        if (F15_POLITE_THE.test(t) || (F15_POSS.test(t) && pcf)) return { k: 'order', why: 'polite-the' };
        if (/\b(?:don'?t|do not|stop|quit)\s+(?:go|make|paint|use|put|add|turn|change|do)\b/.test(t)) return { k: 'order', why: 'neg-imp' };
        if (/\b(?:was|am|i'?m|were|we'?re) (?:thinking|picturing|imagining|considering)\s+(?:of\s+)?(?:a|an|some|something|making|doing|painting|putting)\b/.test(t) && pcf) return { k: 'order', why: 'thinking' };
        if (!/\b(?:wonder|wondering|whether|if|think|reckon|suppose|feel|believe|\?)\b|\?/.test(t) && pcf && /\b(?:would|will|could|might) (?:look|be|suit|work|go)\b/.test(t)) return { k: 'order', why: 'would-look' };
        if (/\bi was wondering if (?:you|we|u) (?:could|can|would|might)\b|\b(?:wondering|hoping|wanted to ask) (?:if|whether) (?:you|we|u) (?:could|can|would)\b|\bany chance (?:you|we) (?:could|can)\b/.test(t) && (pcf || /\b(?:it|that|them)\b/.test(t))) return { k: 'order', why: 'wonder-polite' };
        if (/\bcan i (?:get|have)\b/.test(t)) return { k: 'order', why: 'can-i-get' };
        if (F15_DESIRE.test(t) && (pcf || /\b(?:it|that|them|this)\b/.test(t) || F15_REL1.test(t))) return { k: 'order', why: 'desire' };
        if (F15_SOFT.test(t) && (pcf || F15_REL1.test(t))) return { k: 'order', why: 'soft' };
        if (F15_OPTS.test(t)) return { k: 'options', why: 'options' };
        // an elliptical order: the first clause is only part / look / relative words ("hood red", "pearl on the quarter panels, they look flat", "less gloss on the doors pls")
        var c0 = u.split(/\s*[,;.!?]\s*/)[0] || '';
        if (c0 && new RegExp('^(?:(?:the|my|our|a|an|some|that|this)\\s+)?(?:' + F15_PW + '|' + F15_CW + '|' + F15_FW + '|' + F15_RW + ')\\b').test(c0) && !new RegExp('\\b' + F15_COP + '\\b').test(c0) && !/^(?:not|no|never)\b/.test(c0) && !F15_HATE.test(c0) && !F15_NEGLIKE.test(c0) && c0.split(' ').length <= 12) return { k: 'order', why: 'ellipsis' };
        if (F15_ACK.test(t)) return { k: ctx.pending ? 'neutral' : 'thanks', why: 'ack' };
        if (F15_PRAISE.test(t) && !hasQ) return { k: 'thanks', why: 'praise' };
        var cs = t.split(/\s*[.!?;]+\s+|\s*[.!?;]+$/).filter(Boolean);
        var corr = ctx.last && /^(?:no|nah|nope|wait|actually|oops|sorry|ugh|hmm+|not)\b/.test(t);
        if (hasQ && (F15_QSTART.test(t) || cs.some(function (c) { return F15_QSTART.test(c); }))) return { k: 'question', why: 'qform' };
        if (F15_WHSTART.test(t) && !pcf) return { k: 'question', why: 'qlead' };
        if (F15_MODAL.test(t)) return { k: 'order', why: 'modal' };
        if (corr) return { k: 'neutral', why: 'correction' };
        if (ctx.last && /\b(?:was|were) (?:better|right|nicer|fine|good)\b|\b(?:first|og|original|previous|old|earlier|last) (?:one|version|look|colou?r)?\b/.test(t) && /\b(?:better|betta|back|prefer|liked|rather)\b/.test(t)) return { k: 'neutral', why: 'revert' };
        if (F15_TECH.test(t) && !pcf) return { k: 'complaint', why: 'tech' };
        if (!ctx.last && /^\s*(?:i'?m |i am |im )?(?:not|un)\s?sure (?:about|of|on)\b|^\s*(?:i'?m |i am |im )?(?:undecided|torn)\b/.test(u)) return { k: 'complaint', why: 'unsure' };          // "not sure about the green on the hood" = doubt, not an order
        if (hasQ && /^\s*(?:(?:ok(?:ay)?|so|and|but|hmm+)[, ]+)*if (?:i|we)\b[^?]*\b(?:gonna|going to|will|would|do|does|did|can|could)\b[^?]*\b(?:change|happen|look|stay|work|affect|get|go|be|turn|still)\b/.test(u)) return { k: 'question', why: 'cond' };          // "if i go all red, are the sponsors gonna change??" = a what-if question
        if (!/\b(?:you|u|ya) (?:could|can|would|might|please)\b/.test(t) && (/\b(?:do you (?:think|reckon|feel|believe|say)|would you say|in your (?:opinion|view)|your (?:opinion|thoughts)|what do you (?:think|reckon))\b/.test(t) || (/\b(?:i wonder|wondering|wonder (?:if|whether))\b/.test(t) && t.split(' ').length <= 12 && /\b(?:would|will|might|could|did|does|is|are)\b.*\b(?:suit|look|work|fit|match|go with|clash|be (?:good|nice|better|best|ok|okay|fine|cool|great|bad|too))/.test(t)))) return { k: 'question', why: 'opinion' };          // asking for an OPINION ("do you think green works on the roof", "I wonder if blue would suit the roof") is a question, never an order
        if (F15_WONDER.test(t)) return ctx.last && F15_REL1.test(t) && !hasQ ? { k: 'neutral', why: 'tweak-wonder' } : { k: 'wonder', why: 'wonder' };
        for (i = 0; i < F15_COMPL.length; i++) if (F15_COMPL[i].test(t)) {
            if (ctx.last && !F15_HATE.test(t) && !F15_NEGLIKE.test(t) && (!F15_PCF.test(t.replace(/\b(?:that|it|this|these|those)\b/g, '')) || /^(?:that|it|this|these|those|they|them)\b/.test(u) || /\btoo\b/.test(t) && !/\b(?:i think|i feel|looks?|seems?)\b/.test(t))) return { k: 'neutral', why: 'tweak-complaint' };
            return { k: 'complaint', why: 'c' + i };
        }
        if (F15_STATE.test(t)) return { k: 'state', why: 'state' };
        return { k: 'neutral', why: 'none' };
    }
    // ---- W15F language normaliser: buyer synonyms and phrasings the lexicon / readers do not know, rewritten to words they do. Pure text -> text. One rule off: SPB_OF_CFG.noW15F_<key>.
    function w15fOff(sub) { var ls = false; try { ls = typeof localStorage !== 'undefined' && localStorage.getItem('SPB_W15F_OFF') === '1'; } catch (e) { ls = false; } return !!(W.SPB_W15F_OFF || OF_CFG('noW15F') || ls || (sub && OF_CFG('noW15F_' + sub))); }
    var W15F_PP = '(?:front bumper|rear bumper|back bumper|bumpers?|(?:left|right|driver\'?s?|passenger\'?s?|port|starboard)(?: side)?(?: (?:doors?|quarters?|fenders?|panels?))?|sides?|doors?|hood|bonnet|roof|top|trunk|boot|deck ?lid|spoiler|wings?|nose|numbers|sponsors|logos?)';
    var W15F_ELW = /^(?:numbers?|nums?|digits?|sponsors?|logos?|decals?)$/;
    var W15F_GRADW = /\b(?:fade[sd]?|fading|gradient|ombre|blend(?:s|ing|ed)?|transition(?:s|ing)?|melt(?:s|ing)?)\b/i;
    var W15F_NORM = [
        // excepting words the exception vocabulary lacks: "everything gloss black bar the spoiler", "all but the roof", "not counting the numbers", "sans stripes"
        ['exc', /\b(?:bar|barring|sans)(?=\s+(?:the|my|our|any|all|that|those|both|hood|roof|trunk|bumpers?|spoiler|numbers?|sponsors?|logos?|decals?|doors?|sides?)\b)|\b(?:aside from|all but|not counting|not including|not incl\.?|ignoring|omitting|excepting|leaving out|leave out|skipping|sparing|setting aside)\b/gi, 'except'],
        // woven fibre look = carbon fibre
        ['fibre', /\bwoven\s+(?:carbon\s+)?fib(?:er|re)s?\b/gi, 'carbon fiber'], ['fibre2', /\bcarbon\s+fibre\b/gi, 'carbon fiber'],
        // dupe / clone / replicate / duplicate = copy (not the layer commands)
        ['dupe', /\b(?:dupe|dup|clone|replicate|duplicate)\b(?!\s+(?:the |this |that |my |a )?(?:layers?|zones?|groups?|stamps?|logos?|graphics?|decals?|sponsors?|selection|button))/gi, 'copy'],
        // tail / back / front END bumper = one bumper
        ['endbump', /\b(?:tail|back|rear)\s+end\s+bumpers?\b/gi, 'rear bumper'], ['endbump2', /\b(?:front\s+end|nose)\s+bumpers?\b/gi, 'front bumper'],
        // "identical to / equal to" = the same as
        ['ident', /\b(?:identical|equivalent|equal)\s+to\b/gi, 'the same as'],
        ['shine', /\bhigh[- ]shine\b|\bhigh sheen\b/gi, 'high gloss'],
        // vehicle words
        ['veh1', /\b(?:top wing|aileron)s?\b/gi, 'spoiler'], ['veh2', /\b(?:nose wing|front wing|nose piece)\b/gi, 'front bumper'], ['veh3', /\bthe crown\b(?!\s+(?:logo|emblem|royal|jewel|sticker))/gi, 'the roof'],
        // one-side words: L side / lft / rgt; "<side word> flank" is that side; a flank next to a side word is that side
        ['sidel', /\b(?:l|lh|lhs)\.?\s+(?=side\b|door\b|panel\b|fender\b|flank\b|quarter\b)/gi, 'left '], ['sider', /\b(?:r|rh|rhs)\.?\s+(?=side\b|door\b|panel\b|fender\b|flank\b|quarter\b)/gi, 'right '],
        ['port', /\bport(?=\s+(?:side|door|panel|fender|quarter|flank|mirror)s?\b)/gi, 'left'], ['stbd', /\b(?:starboard|stbd)(?=\s+(?:side|door|panel|fender|quarter|flank|mirror)s?\b)/gi, 'right'],
        ['drv', /\bdriver'?s?(?=\s+(?:door|panel|fender|quarter|flank|mirror)s?\b)/gi, 'left'], ['pax', /\bpassenger'?s?(?=\s+(?:door|panel|fender|quarter|flank|mirror)s?\b)/gi, 'right'],
        ['sidedup', /\b(side|door|panel|fender)s? \1s?\b/gi, '$1'],
        ['sidel2', /\blft\b/gi, 'left'], ['sider2', /\b(?:rgt|rght|rht)\b/gi, 'right'],
        ['flank', /\b(left|right|port|starboard|driver'?s?|passenger'?s?)\s+(?:side\s+)?flanks?\b/gi, '$1 side'], ['flank2', /\bflanks?\b(?=[^.;,!?]{0,30}\b(?:driver|passenger|left|right|port|starboard)\b)/gi, ''],
        // spec words as finish words: roughness low = glossy, roughness high = matte, clearcoat max = high gloss
        ['spec1', /\brough(?:ness)?\s*(?:to |at |of |=|:)?\s*(?:very low|low|minimum|min|zero|0)\b/gi, 'high gloss'], ['spec2', /\brough(?:ness)?\s*(?:to |at |of |=|:)?\s*(?:very high|high|maximum|max|full|255)\b/gi, 'matte'],
        ['spec3', /\bclear ?coat\s*(?:to |at |of |=|:)?\s*(?:maximum|max|full|high|on|16)\b/gi, 'high gloss'], ['spec4', /\bclear ?coat\s*(?:to |at |of |=|:)?\s*(?:low|none|off|zero|0|min(?:imum)?)\b/gi, 'matte'],
        ['colword', /\b(red|orange|yellow|green|blue|purple|violet|pink|white|black|gr[ae]y|silver|gold|brown|teal|cyan|magenta|lime|navy|maroon|beige|cream|bronze|copper|turquoise|burgundy)\s+(?:colou?r|shade|tone|hue)s?\b(?!\s+(?:of|from|for|as|to|than|scheme|palette|code))/gi, '$1'],          // "gold colour" / "gold color" = gold (the bare colour follow-up)
        // "the car's top" = the roof; "skip the numbers" = except the numbers
        // an exception that names something the paint sheet does not have (wheels, rims, glass, lights ...) is moot: those are never painted, so drop the clause
        ['unpex', /[,;]?\s*\b(?:except(?:\s+for)?|excluding|excl\.?|without|skipping|skip|sans|ex|not\s+including|not\s+counting|leaving\s+out|leave\s+out|apart\s+from|aside\s+from|bar|barring|but\s+not|besides)\s+(?:the\s+|my\s+|our\s+|all\s+(?:the\s+)?)?(?:wheels?|rims?|tyres?|tires?|windows?|windshield|windscreen|glass|(?:head|tail|brake|fog)\s?(?:lights?|lamps?)|headlamps?|interior|seats?|cockpit|cabin|dash(?:board)?|exhaust|chassis|brakes?|calipers?)\b(?:\s*(?:,|and|or|&)\s*(?:the\s+)?(?:wheels?|rims?|tyres?|tires?|windows?|glass|(?:head|tail|brake)\s?lights?))*/gi, ''],
        ['exabbr', /\b(?:ex|excl)\b(?=\s+(?:the\s+|my\s+|our\s+)?(?:roof|hood|trunk|bonnet|boot|doors?|sides?|spoiler|bumpers?|numbers?|nums?|sponsors?|logos?|decals?|mirrors?|wings?))/gi, 'except'],
        ['abbr2', /\bhd\b(?!\s+(?:quality|resolution|textures?|render\w*|video|screen|display|image))/gi, 'hood'], ['abbr3', /\b(?:bmpr|bmper|bumpr|bumpa)s?\b/gi, 'bumper'],
        ['veh4', /\b(?:rear\s+)?aero\s+(?:blade|wing|foil|element|flap)\b|\b(?:rear|trunk|boot)\s+(?:blade|foil)\b|\bducktail\b|\bgurney(?:\s+flap)?\b/gi, 'spoiler'],
        // "the blue from our logo" / "the red in the sponsors" names a colour, it is not a target: keep just the colour word
        ['colfrom', /\b(?:the\s+|that\s+)?(red|orange|yellow|green|blue|purple|violet|pink|white|black|gr[ae]y|silver|gold|brown|teal|cyan|magenta|lime|navy|maroon|bronze|copper|turquoise|burgundy)\s+(?:from|in|of|used in)\s+(?:the\s+|our\s+|my\s+)(?:logos?|sponsors?|numbers?|decals?|livery|brand(?:ing)?)\b/gi, '$1'],
        // an order that starts with a stripe noun ("stripe down the centre of the hood in black") is "add a stripe ..."
        ['colfrom2', /\b(?:the\s+|that\s+)?(?:our|my|the)\s+(?:logos?|sponsors?|numbers?|decals?)'s?\s+(red|orange|yellow|green|blue|purple|violet|pink|white|black|gr[ae]y|silver|gold|brown|teal|cyan|magenta|lime|navy|maroon|bronze|copper|turquoise|burgundy)\b/gi, '$1'],
        ['stripeinit', /^\s*(?:and\s+|also\s+|then\s+|plus\s+)?(?:a\s+|an\s+|the\s+)?((?:(?:thin|wide|narrow|fat|thick|skinny|big|small|double|twin|single|red|white|black|blue|green|yellow|orange|gold|silver|grey|gray|pink|purple)\s+){0,2}(?:racing\s+)?(?:stripes?|pin ?stripes?|pinlines?|bands?|strips?))\s+(?=(?:down|over|across|along|on|through|around|up|between|at)\b)/i, 'add a $1 '],
        ['cartop', /\b(?:the\s+)?(?:car|vehicle)'?s\s+top\b/gi, 'the roof'], ['skip', /\bskip(?:ping)?(?=\s+(?:the|my|our|all|both|any)\b)/gi, 'except'],
        // a centre seam / centre line / line down the middle = the racing stripe
        ['seam1', /\b(?:a\s+|the\s+)?(?:centre|center|middle)\s+(?:seam|line|stripe|band|strip|pinline)\b/gi, 'a racing stripe down the middle'], ['seam2', /\b(?:a\s+|the\s+)?(?<!racing\s)(?:line|stripe|band|strip|seam)\s+(?:down|along|through|up|across)\s+the\s+(?:middle|centre|center)(?:\s+of\s+(?:the|my|our)\s+car)?\b/gi, 'a racing stripe down the middle'],
        // gfxsize (W15F 2026-10-09, W17D FRAME_PROPOSAL item 2): a size word on a stripe-like graphic is a WIDTH change of the stripes, whatever colour / place word sits in between ("make the red stripe thinner" was read as a recolour to red
        // that a follow-up would then apply to the previous part). Colour adjectives are dropped (the planner cannot resolve "the red one" without a layer list); the noun is the stripes.
        ['gfxsize1', /\b(?:(?:(?:can|could|would|will)\s+(?:you|u|we|i)\s+(?:please\s+)?)?(?:(?:make|get|have|keep|set)\s+)|(?:(?:can|could|would|will)\s+(?=(?:the|my|our|those|these)\b)))?(?:the\s+|my\s+|our\s+|those\s+|these\s+)?(?:(?:red|white|black|blue|green|yellow|orange|gold|silver|grey|gray|pink|purple|thin|thick|wide|narrow|racing|side|hood|roof|main|top|bottom|left|right|centre|center|middle)\s+){0,3}(?:pin ?stripes?|pinlines?|racing stripes?|stripes?|bands?)\b(?:\s+(?:on|along|down|across|over)\s+(?:the\s+|my\s+|our\s+)?(?:side|sides|hood|roof|trunk|doors?|car))?(?:\s+(?:be|is|are|should be|a bit|a little|slightly|much|way|just|kinda|bit|little)){0,3}\s+(thinner|thicker|wider|narrower|fatter|slimmer|skinnier|chunkier|bolder)\b/gi, function (m, w) { return 'make the stripes ' + ({ fatter: 'thicker', chunkier: 'thicker', bolder: 'thicker', slimmer: 'thinner', skinnier: 'thinner' }[String(w).toLowerCase()] || String(w).toLowerCase()); }],
        ['gfxsize2', /\b(?:the\s+|my\s+|our\s+)?(?:(?:red|white|black|blue|green|yellow|orange|gold|silver|grey|gray|pink|purple|racing|side|hood|roof|main)\s+){0,3}(?:pin ?stripes?|pinlines?|racing stripes?|stripes?|bands?)\b\s+(?:look|looks|looked|seem|seems|is|are|came out|feel|feels)?\s*(?:a bit |a little |way |much |kinda |really |so |pretty |just )?too\s+(thick|fat|wide|chunky|bold|thin|narrow|skinny|slim)\b/gi, function (m, w) { return 'make the stripes ' + (/^(?:thick|fat|wide|chunky|bold)$/i.test(w) ? 'thinner' : 'thicker'); }],
        ['gfxsize4', /^\s*(?:(?:ok(?:ay)?|and|also|then|please|pls|hey|so)[,\s]+)*(thinner|thicker|wider|narrower|slimmer|skinnier)\s+(?:the\s+|my\s+|our\s+)?(?:(?:red|white|black|blue|green|yellow|orange|gold|silver|grey|gray|pink|purple|racing|side|hood|roof|main)\s+){0,3}(?:pin ?stripes?|pinlines?|racing stripes?|stripes?|bands?)\b(?!\s+(?:down|across|along|over|on|around|between|at|through|up)\b)/i, function (m, w) { return 'make the stripes ' + String(w).toLowerCase().replace('slimmer', 'thinner').replace('skinnier', 'thinner'); }],
        ['gfxsize3', /\b(thin|slim|narrow|thicken|widen|fatten)(?:\s+(?:down|out|up))?\s+(?:the|my|our|those|these)\s+(?:(?:red|white|black|blue|green|yellow|orange|gold|silver|grey|gray|pink|purple|racing|side|hood|roof|main)\s+){0,3}(?:pin ?stripes?|pinlines?|racing stripes?|stripes?|bands?)\b(?:\s+(?:down|out|up))?/gi, function (m, w) { return 'make the stripes ' + (/^(?:thin|slim|narrow)$/i.test(w) ? 'thinner' : 'thicker'); }],
        ['abbr4', /\b(?:blk|wht|gry|slvr|slv|grn|ylw|orng|pnk|prpl|purp|brn|gld|blu|crm)\b/gi, function (m) { return ({ blk: 'black', wht: 'white', gry: 'grey', slvr: 'silver', slv: 'silver', grn: 'green', ylw: 'yellow', orng: 'orange', pnk: 'pink', prpl: 'purple', purp: 'purple', brn: 'brown', gld: 'gold', blu: 'blue', crm: 'cream' })[m.toLowerCase()]; }],
        ['nand', /(?<=\w)\s+n\s+(?=\w)/gi, ' and '],
        // "the hood is too dull, bump it up" = make it glossier; "the spoiler's too shiny, tone it down" = less glossy
        ['toodull', new RegExp('\\b((?:the |my |our )?' + W15F_PP + ')\\s*(?:\'s|is|are|looks?|seems?|came out|is looking|feels?)?\\s+(?:a bit |a little |kinda |kind of |way |much |far |really |so |pretty |quite )?too\\s+(?:dull|flat|matt?e?|lifeless|boring|muted|drab|lacklustre|lackluster)\\b[^.;!?]*?[,;]?\\s*(?:so\\s+)?(?:please\\s+|pls\\s+)?(?:bump|crank|push|dial|turn|bring|take|make|boost|give|add|get|fix|sort|raise|lift|increase|up)\\b[^.;!?]*', 'gi'), 'make $1 glossier'],
        ['flatgloss', new RegExp('\\b((?:the |my |our )?' + W15F_PP + ')\\s*(?:\'s|is|are|looks?|seems?|came out|is looking|feels?)\\s+(?:a bit |a little |kinda |kind of |pretty |quite |so |really )?(?:dull|flat|lifeless|boring|muted|drab)\\b[^.;!?]*?[,;]\\s*(?:so\\s+)?(?:please\\s+|pls\\s+)?(?:bump|crank|push|dial|turn|bring|boost|give|add|raise|lift|increase|up|make|get)\\b[^.;!?]*\\b(?:gloss\\w*|shin\\w*|pop|life|sheen|up)\\b[^.;!?]*', 'gi'), 'make $1 glossier'],
        ['tooshiny', new RegExp('\\b((?:the |my |our )?' + W15F_PP + ')\\s*(?:\'s|is|are|looks?|seems?|came out|is looking|feels?)?\\s+(?:a bit |a little |kinda |kind of |way |much |far |really |so |pretty |quite )?too\\s+(?:shiny|glossy|glassy|reflective|slick|mirror\\w*)\\b[^.;!?]*?[,;]?\\s*(?:so\\s+)?(?:please\\s+|pls\\s+)?(?:tone|dial|turn|take|bring|knock|pull|back|lower|reduce|ease|calm|cut|drop|cool|make|fix)\\b[^.;!?]*', 'gi'), 'make $1 less glossy'],
        ['spec5', /\bmetallic\s*(?:to |at |of |=|:)?\s*(?:maximum|max|full|high|255)\b/gi, 'metallic'],
        ['spec6', /[,;]?\s*\b(?:spec(?:ular)?|finish) only\b|\bonly (?:the )?(?:spec(?:ular)?|finish)\b/gi, ' keep the colour']
    ];
    // "same colour on the trunk as the hood has", "give the rear bumper whatever the nose has", "rear bumper in the colour of the front bumper" = "make the A match the B"
    var W15F_REF = [
        new RegExp('\\b(?:the\\s+)?same\\s+(?:colou?r|finish|look|paint|shade|thing)\\s+(?:on|for)\\s+(?:the\\s+)?(' + W15F_PP + ')\\s+as\\s+(?:the\\s+)?(' + W15F_PP + ')(?:\\s+(?:has|have|is|got|is wearing))?\\b', 'gi'),
        new RegExp('\\b(?:give|make)\\s+(?:the\\s+)?(' + W15F_PP + ')\\s+(?:whatever|what)\\s+(?:the\\s+)?(' + W15F_PP + ')\\s+(?:has|have|got|is wearing|is)\\b', 'gi'),
        new RegExp('\\b(?:make|paint|colou?r|do|put)\\s+(?:the\\s+)?(' + W15F_PP + ')\\s+(?:in|with|to)\\s+(?:the\\s+)?(?:same\\s+)?(?:colou?r|finish|look|paint|shade)\\s+(?:as|of)\\s+(?:the\\s+)?(' + W15F_PP + ')\\b', 'gi'),
        new RegExp('\\b(' + W15F_PP + ')\\s+(?:in|with)\\s+the\\s+(?:colou?r|finish|look|paint)\\s+of\\s+(?:the\\s+)?(' + W15F_PP + ')\\b', 'gi')
    ];
    // "spoiler same finish as the front bumper", "doors the same colour as the hood", "spoiler same as the bumper" (an elliptical order at the start of a clause) = "make the A match the B"
    var W15F_REF2 = [
        new RegExp('(^|[,;.]\\s*|\\b(?:and|then|also|plus|please|pls)\\s+)(?:the\\s+)?(' + W15F_PP + ')\\s+(?:the\\s+)?same\\s+(?:(?:colou?r|finish|look|paint|shade|style)\\s+)?(?:as|like)\\s+(?:the\\s+)?(' + W15F_PP + ')\\b', 'gi')
    ];
    var W15F_KEEPCL = new RegExp('([^,;.!?]{6,}?)\\s*[,;]\\s*(?:and\\s+|but\\s+|then\\s+)?(?:please\\s+|pls\\s+)?(?:leave|keep|don\'?t touch|do not touch|dont touch)\\s+(?:the\\s+|my\\s+|our\\s+)?(' + W15F_PP + '|decals?|stripes?|lettering|digits|text)\\s+(?:alone|as is|as it is|untouched|the same|unchanged|intact|how it is)\\b', 'gi');
    var W15F_CMP = new RegExp('\\b((?:more [a-z]+|less [a-z]+|(?:a (?:bit|touch|tad|little|shade) |much |slightly |a lot |way )?(?:[a-z]{3,}er)))((?:\\s+(?:blue|red|green|yellow|orange|purple|pink|grey|gray|white|black|gold|silver|teal|brown))?)\\s+than\\s+(?:the\\s+|my\\s+|our\\s+)?' + W15F_PP + '\\b(?:\\s+(?:is|are|has|have|does|do))?', 'gi');
    function w15fFixWord(w) { try { return fixTok(String(w).toLowerCase()); } catch (e) { return w; } }
    // colour roles defined and used in the same message (W17D FRAME_PROPOSAL item 7): "Primary is #00A651, secondary #1D1D1B. Body in primary, roof and spoiler in secondary." -> the role words become their value
    var W15F_ROLE = '(?:primary|secondary|tertiary|main colou?r|accent colou?r|colou?r (?:1|2|3|one|two|three|a|b|c))';
    var W15F_ROLEVAL = '(#[0-9a-f]{6}|#[0-9a-f]{3}|[a-z]{3,12}(?: [a-z]{3,10})?)';
    function w15fRoles(s) {
        var map = {}, n = 0, rd = new RegExp('\\b(' + W15F_ROLE + ')(?:\\s+colou?r)?\\s*(?:is|are|will be|should be|=|:|->|=>|means)?\\s*' + W15F_ROLEVAL + '(?=\\s*(?:[,.;!?]|\\band\\b|$))', 'gi'), t = s;
        t.replace(rd, function (m, r, v) { if (/^(?:is|are|and|the|for|in|on|to|as|with)$/i.test(v)) return m; var key = r.toLowerCase().replace(/\s+colou?r$/, '').replace(/^colou?r\s+/, 'c'); map[key] = v; n++; return m; });
        if (!n) return s;
        // drop the definition clauses, then replace the remaining uses
        var rest = t.replace(rd, function (m, r, v) { return /^(?:is|are|and|the|for|in|on|to|as|with)$/i.test(v) ? m : ''; });
        var used = false;
        rest = rest.replace(new RegExp('\\b(?:the\\s+)?(' + W15F_ROLE + ')(?:\\s+colou?r)?\\b', 'gi'), function (m, r) { var key = r.toLowerCase().replace(/\s+colou?r$/, '').replace(/^colou?r\s+/, 'c'); if (map[key] == null) return m; used = true; return map[key]; });
        if (!used) return s;
        return rest.replace(/^[\s,.;and]+(?=\S)/i, function (m) { return /^\s*(?:and\b)/i.test(m) ? '' : m.replace(/[,.;]/g, ''); }).replace(/\s*[,;]\s*(?=[.,;])/g, '').replace(/\s{2,}/g, ' ').replace(/^\s*[,.;]+\s*/, '').trim();
    }
    function w15fNorm(s) {
        if (w15fOff('norm') || typeof s !== 'string' || !s) return s;
        var o = s;
        try {
            s = w26Pre(s);          // W26U 2026-10-10 (under-acting round 3, see the W26U block)
            s = w23Pre(s);          // W23U 2026-10-09 (EARLY hooks: palette, undo, restore, chip reply, question + order, stripe words; BEFORE the W15F / W21H rewrites, see the W23U block)
            if (!OF_CFG('noW15F_roles')) s = w15fRoles(s);
            s = w21Spec(s);          // W21H T06_spec 2026-10-09 (BEFORE the rules: 'spec6' turns 'finish only' into 'keep the colour')
            W15F_NORM.forEach(function (r) { if (!OF_CFG('noW15F_' + r[0])) s = (r[0] === 'toodull' || r[0] === 'flatgloss') ? s.replace(r[1], function (m, a) { return w21ExplicitTail(m) ? m : 'make ' + a + ' glossier'; }) : s.replace(r[1], r[2]); });
            s = w21PatWords(w21Words(w21StripOther(s)));          // W21H T01_side 2026-10-09
            s = w21Pick(w21Complaint(w21Polite(s), {}));          // W21H SA_polite / SA_complaint_fix 2026-10-09 (here, not in frameOf: the planner hands this text to the regex reader too)
            s = w23Norm(s);          // W23U 2026-10-09 (under-acting hooks, see the W23U block)
            if (!OF_CFG('noW15F_ref')) W15F_REF.forEach(function (re) { s = s.replace(re, 'make the $1 match the $2'); });
            if (!OF_CFG('noW15F_ref2')) W15F_REF2.forEach(function (re) { s = s.replace(re, '$1make the $2 match the $3'); });
            if (!OF_CFG('noW15F_keepcl')) s = s.replace(W15F_KEEPCL, function (m, a, b) { return /\b(?:keep|leave|don'?t|do not|never|except|but not|without)\b/i.test(a) ? m : a + ', except the ' + b; });          // "hood red; leave the roof alone" = "hood red, except the roof"
            if (!OF_CFG('noW15F_than') && !/\b(?:equali[sz]e|even\b|match|balance|sync|same|consistent|uniform|fix)/i.test(s)) { var s2c = s.replace(W15F_CMP, '$1$2'); if (s2c !== s && new RegExp('\\b(?:' + W15F_PP + ')\\b', 'i').test(s2c)) s = s2c; }          // "a darker blue than the doors": the doors are only the yardstick, but only when another part is still named (a bare "paler blue than the doors" has no target left: the planner / W15H guard must see the yardstick)
            // "everything blue but nmbers" = except the numbers (a body word before the "but", an element / part word after it with no look word following)
            if (!OF_CFG('noW15F_but')) s = s.replace(/\b(everything|all(?: of it)?|whole car|entire car|the whole thing|the car|all over|the body|the livery)\b([^.;!?]*?)\bbut\s+(?!not\b)(?:the\s+|my\s+|our\s+)?([a-z]{3,9})\b(?=(?:\s+(?:and|or|&)\s+(?:the\s+|my\s+|our\s+)?[a-z]{3,9})*\s*(?:$|[.,;!?]|\s+(?:please|pls|plz|thanks|ok|though|tho)\b))/gi, function (m, a, b, w) { var f = w15fFixWord(w); return W15F_ELW.test(f) || /^(?:roof|hood|trunk|bonnet|spoiler|bumpers?|doors?|sides?|boot)$/.test(f) ? a + b + 'except ' + w : m; });
            // a fade's direction words are directions, not parts: "from the windscreen to the nose", "from the roofline down", "toward the bottom"
            if (!OF_CFG('noW15F_grad') && W15F_GRADW.test(s)) s = s.replace(/\b(?:the\s+)?(?:nose|front)\s+end\b(?!\s+(?:bumper|of))/gi, 'front').replace(/\b(?:the\s+)?(?:windscreen|windshield|cowl|tail|rear|back)\s+end\b(?!\s+(?:bumper|of))/gi, 'back');          // "nose end orange fading to the windscreen end yellow": ends of a fade are directions
            if (!OF_CFG('noW15F_grad') && W15F_GRADW.test(s)) s = s.replace(/\b(from|to|towards?|toward|at|by|near|into|out to|down to|up to|starting (?:at|from)|ending (?:at|in))\s+(?:the\s+)?(windscreen|windshield|cowl|a-?pillars?|roof ?line|roof edge|top edge|nose|splitter|front end|tail|tail end|rear end|back end|bottom|bottom edge|rockers?|sills?|skirts?|ground|lower edge)\b(?!\s+(?:bumper|panel|side|wing|of the (?:door|hood|roof)))/gi, function (m, p, w) { var d = /^(?:windscreen|windshield|cowl|a-?pillars?)$/i.test(w) ? 'back' : /^(?:roof ?line|roof edge|top edge)$/i.test(w) ? 'top' : /^(?:nose|splitter|front end)$/i.test(w) ? 'front' : /^(?:tail|tail end|rear end|back end)$/i.test(w) ? 'back' : 'bottom'; return p + ' the ' + d; });
        } catch (e) { return o; }
        return s;
    }
    // ---- W15F verdict: a language-level check of a finished paint against what the buyer actually SAID. Pure: (text, painted-summary, ctx) -> null | { act, key, q, chips, strip, excl }.
    //   speech   : no order cue and clear question / complaint / state / thanks / option-request evidence = nothing is painted
    //   keepref  : a part the sentence only keeps ("leave the roof alone", "bar the spoiler") or uses as a yardstick ("than the doors", "like the hood") is never painted
    //   side     : one side named = one side; a bare singular "the side" asks which
    //   region   : "inside / underside / middle of the car", "the bit between the doors", wheels / glass / interior = no part on this sheet
    //   unnamed  : a fresh (not follow-up) order never paints a part the sentence does not name
    var W15F_PARTS = [['hood', /\b(?:hood|bonnet|engine (?:cover|lid)|front lid)\b/], ['roof', /\b(?:roof|top panel|roof panel|crown)\b/], ['trunk', /\b(?:trunk|boot|deck ?lid|rear lid|back lid|tail ?gate)\b/],
        ['front bumper', /\b(?:front (?:bumper|end|lip|fascia|valance|splitter|nose)|splitter|nose|air ?dam|chin|front)\b/], ['rear bumper', /\b(?:(?:rear|back|tail) (?:bumper|end|fascia|valance)|diffuser|rear|back|tail)\b/], ['spoiler', /\b(?:spoiler|wings?|aileron|rear wing)\b/]];
    var W15F_LW = /\b(?:left|lft|driver'?s?|port|lhs|lh)\b/, W15F_RW = /\b(?:right|rgt|rght|passenger'?s?|starboard|rhs|rh)\b/, W15F_SN = /\b(?:sides?|doors?|panels?|fenders?|quarters?|flanks?|rockers?|skirts?)\b/;
    var W15F_BOTH = /\b(?:both|each|either|every|all|two|2|pair|sides|doors|fenders|panels|quarters|flanks|other side|other one|opposite|too|as well|also|again|same|mirror(?:ed)?|and|plus)\b|[+&]/;
    var W15F_BODYW = /\b(?:car|body|bodywork|everything|every ?thing|whole|entire|all|livery|paint ?job|vehicle|ride|truck|machine|overall|base|rest|the lot|all over|the thing|it)\b/;
    var W15F_UNP = /\b(?:wheels?|rims?|tyres?|tires?|windows?|windshield|windscreen|glass|headlights?|head ?lamps?|tail ?lights?|brake ?lights?|(?:fog|running|rear|front|indicator|marker|driving) lights?|exhaust|interior|inside|seats?|cockpit|cabin|dash(?:board)?|steering|engine(?: bay)?|chassis|roll ?cage|cage|helmet|undercarriage|underside|underbody|underneath|belly|brakes?|calipers?)\b/;
    var W15F_REGION = /\b(?:inside|interior|underside|underneath|under ?body|undercarriage|bottom|belly|middle|centre|center|cockpit|cabin|engine bay|lower half|upper half|front end|rear end|back end|nose|tail|front half|back half|rear half)\s+(?:part\s+)?of\s+(?:the\s+|my\s+|our\s+|this\s+)?(?:car|vehicle|truck|body|ride|livery)\b|\b(?:bit|bits|part|parts|area|areas|section|sections|gap|gaps|space|strip|zone|region|spot|spots)\s+(?:between|around|next to|near|beside|behind|in front of|below|above|under|over|inside)\s+(?:the\s+|my\s+)?\w+/;
    var W15F_KEEP_PRE = /(?:\b(?:leav(?:e|ing)|don'?t\s+touch|do\s+not\s+touch|dont\s+touch|not\s+touch(?:ing)?|except(?:ing)?|besides|apart\s+from|other\s+than|without|excluding|minus|save\s+for|but\s+not|skip(?:ping)?|ignor(?:e|ing)|spar(?:e|ing)|hands\s+off|keep(?:ing)?|not|no|never|protect(?:ing)?|exclude|excl)\s+(?:(?:the|my|our|its|any|all|of|on|to)\s+)*(?:[\w']+\s+){0,1})$/i;
    var W15F_KEEP_POST = /^\s*(?:[\w']+\s+){0,2}?(?:remains?|stays?|stay|staying|untouched|unchanged|as\s+is|as\s+it\s+(?:was|is)|as\s+before|alone|intact|not\s+(?:be\s+)?touched|n'?t\s+(?:be\s+)?touched|nt\s+touched|left\s+alone|safe|stays?\s+put|doesn'?t\s+change|not\s+change|no\s+change|excluded|not\s+included)\b/i;
    var W15F_REF_PRE = /(?:\b(?:than|compared\s+(?:to|with)|versus|vs\.?|relative\s+to|(?:the\s+)?same(?:\s+\w+)?\s+as|similar\s+to|(?:look(?:s|ed|ing)?|be|is|are|just|exactly|much|more|kind\s+of|a\s+bit|a\s+lot|sort\s+of)\s+like|match(?:es|ing)?\s+(?:the\s+)?(?:colou?r|finish|look|paint)\s+(?:of|from|on)|(?:colou?r|finish|look|paint)\s+of|whatever|(?:colou?r|finish|look|paint|style|texture|pattern|copy|take|steal|borrow|pull|use|grab)(?:\s+\w+){0,2}\s+from)\s+(?:(?:the|my|our)\s+)?)$/i;
    function w15fPartsOf(seg, onlyDir) {          // canonical part names a text fragment mentions
        var o = [], t = String(seg || '');
        W15F_PARTS.forEach(function (p) { if (p[1].test(t) && o.indexOf(p[0]) < 0) o.push(p[0]); });
        if (/\bbumpers?\b/.test(t) && !/\b(?:front|rear|back|tail|nose)\s+(?:end\s+)?bumper/.test(t)) { if (o.indexOf('front bumper') < 0) o.push('front bumper'); if (o.indexOf('rear bumper') < 0) o.push('rear bumper'); }
        var l = W15F_LW.test(t), r = W15F_RW.test(t), sn = W15F_SN.test(t);
        if (l && (sn || !onlyDir) && o.indexOf('left side') < 0) o.push('left side'); if (r && (sn || !onlyDir) && o.indexOf('right side') < 0) o.push('right side');
        if (sn && !l && !r) { if (o.indexOf('left side') < 0) o.push('left side'); if (o.indexOf('right side') < 0) o.push('right side'); }
        return o;
    }
    function w15fOccs(t) {          // every part / element occurrence with its role: 'target' | 'keep' | 'ref'
        var out = [], re = new RegExp('\\b(?:(?:(?:left|right|driver\'?s?|passenger\'?s?|port|starboard|lft|rgt|rght)\\s+(?:hand\\s+)?)?(?:sides?|doors?|fenders?|quarter panels?|quarters?|flanks?)|' + W15F_PARTS.map(function (p) { return p[1].source.replace(/^\\b\(\?:|\)\\b$/g, ''); }).join('|') + '|bumpers?|numbers?|nums?|digits?|sponsors?|logos?|decals?)\\b', 'gi'), m;
        while ((m = re.exec(t))) {
            var i = m.index, e = i + m[0].length, cs = Math.max(t.lastIndexOf('.', i), t.lastIndexOf(';', i), t.lastIndexOf('!', i), t.lastIndexOf('?', i), t.lastIndexOf(',', i)) + 1, pre = t.slice(cs, i), post = t.slice(e, e + 45).split(/[.;!?,]/)[0];
            var w = m[0].toLowerCase(), el = /^(?:numbers?|nums?|digits?)$/.test(w) ? 'numbers' : /^(?:sponsors?|logos?|decals?)$/.test(w) ? 'sponsors' : null, role = 'target';
            if (W15F_KEEP_PRE.test(pre.slice(-60)) || (W15F_KEEP_POST.test(post) && !/\b(?:make|paint|turn|set|colou?r)\s+(?:the\s+)?$/.test(pre))) role = 'keep';
            else if ((W15F_REF_PRE.test(pre.slice(-60)) || (!w26Off('sameas') && W26_SAMEAS_PRE.test(pre.slice(-60)))) && !/\b(?:i|we)(?:'d| would)?\s+like\s+(?:the\s+)?$/.test(pre.slice(-30)) && !/\b(?:change|alter|switch|set|swap|modify|edit|adjust|update|recolou?r|re-?colou?r|fix|redo)\s+(?:(?:the|my|our)\s+)?(?:colou?r|finish|look|paint)\s+(?:of|on|for)\s+(?:(?:the|my|our)\s+)?$/.test(pre.slice(-60))) role = 'ref';          // "change the colour of the numbers to green" targets the numbers; "the colour of the hood" elsewhere is only a yardstick
            out.push({ w: w, i: i, e: e, el: el, parts: el ? [] : w15fPartsOf(w, false), role: role });
        }
        return out;
    }
    // W21H T01_side 2026-10-09 (hold probe T01_side harm 2; kill SPB_OF_CFG.noW21H_side): ONE side named (left / right / driver / passenger ...) = one side. W15F_BOTH counted ANY 'and' / 'also' / 'too' / 'all' / 'same' as proof that the other side is wanted
    // ("... just that side, thanks a lot and good luck" painted both). Now only a word that is about the OTHER SIDE counts: both / each / the plural (sides, doors) / the other side / opposite / mirror it / copy it over; and a keep cue after
    // 'the other side' ("the other side can stay as it is") means one side.
    var W21_BOTH = /\b(?:both|each|either|every|pair|sides|doors|fenders|panels|quarters|flanks|opposite|other (?:side|door|one|panel|fender|quarter|flank|half)|(?:two|2) (?:sides|doors)|mirror(?:ed|ing)? (?:it|that|them|to|on|over)|copy (?:it |that )?(?:to|over|across)|same (?:on|for|to|at) (?:the )?(?:other|opposite)|flip (?:it|that) (?:to|over|across))\b|[+&]/;
    var W21_KEEPSIDE = /\b(?:other|opposite) (?:side|door|one|panel|fender|quarter|flank|half)\b[^.;!?]{0,34}\b(?:stay|stays|staying|remain|remains|keep|keeps|kept|leave|leaves|left alone|untouched|unchanged|as is|alone|not|n't|no change)\b|\b(?:leave|leaving|keep|keeping|not|don'?t touch|do not touch|except|without|excluding|skip|skipping|ignore|ignoring)\b[^.;!?]{0,24}\b(?:other|opposite) (?:side|door|one|panel|fender|quarter|flank|half)\b/;
    // "make the right door satin, the other side can stay as it is": the keep clause about the OTHER side is not an order (the regex reader read 'other side' + 'the same' as a copy-to-the-opposite-side ask)
    var W21_OTHERSTAY = [
        /[,;.]?\s*(?:and\s+|but\s+)?(?:the\s+)?(?:other|opposite)\s+(?:side|door|panel|one)\s+(?:can\s+|should\s+|will\s+|may\s+|has\s+to\s+|needs?\s+to\s+)?(?:stays?|remains?|be\s+left|stay\s+put)(?:\s+(?:as\s+is|as\s+it\s+is|as\s+they\s+are|alone|untouched|the\s+same|unchanged|how\s+it\s+is))?/gi,
        /[,;.]?\s*(?:and\s+|but\s+)?(?:please\s+)?(?:leave|keep)\s+(?:the\s+)?(?:other|opposite)\s+(?:side|door|panel|one)(?:\s+(?:alone|as\s+is|as\s+it\s+is|untouched|the\s+same|unchanged))?/gi,
        /[,;.]?\s*(?:and\s+|but\s+)?(?:don'?t|do\s+not|dont)\s+(?:touch|change|paint)\s+(?:the\s+)?(?:other|opposite)\s+(?:side|door|panel|one)/gi
    ];
    function w21Words(s) {          // W21H 2026-10-09: "make the back bumper holo" was read as 'put the bumper back to its original colour' (the word BACK): a part word, not a direction
        if (w21Off('words') || typeof s !== 'string') return s;
        return s.replace(/\bpax\b/gi, 'passenger').replace(/\btail\s+(bumpers?)\b/gi, 'rear $1').replace(/\bnose\s+(bumpers?)\b/gi, 'front $1');          // 'tail bumper' / 'nose bumper' = ONE bumper (the planner read 'tail bumper' as both bumpers; own probe OWN_F_reply-015)
    }
    // ---- T05_pattern (hook 7; hold T05_pattern 84 turns 71 ok / 84.5%, 13 fails = 'splatter' x4, 'honeycomb' x8; kill noW21H_pat): a pattern NOUN the lexer does not know ("put honeycomb on the roof", "splatter on the boot", "dazzle on the hood", "chain mail on the doors") made the
    //   graphics planner (gfx8) ask "which pattern?" although the catalogue has the thing under another name (real_names.json patterns: Hex Mesh / Graphene Hex / Hex Carbon, Grunge Splatter, Dazzle, Chainmail Hex, Scale Mail). The noun is mapped to the nearest REAL pattern word the lexer resolves
    //   (hexagons -> pattern:hex, 'grunge splatter' -> Distressed Patina, 'dazzle camo' -> camo). Only inside an ORDER (an order verb or a bare '<noun> on <part>'), never a question / how-to, and only with a part (or the car) named. Words with no real catalogue counterpart (hearts, scribble)
    //   are NOT mapped on purpose: a dots pattern would be painted where the buyer asked for hearts, so the planner's own question stays.
    var W21_PATSYN = [
        [/\b(?:honey ?combs?|bee ?hives?|apiary)(?: pattern| print| look| texture| design)?\b/gi, 'hexagons'],
        [/\b(mud |grunge )?(?:splatter(?:ed|ing|s)?|spatter(?:ed|s)?|splats?)(?: pattern| print| look| texture| design)?\b/gi, function (m, pre) { return pre ? m : 'grunge splatter'; }],
        [/\bdazzle(?: pattern| print| stripes| look| design)?\b(?! camo)/gi, 'dazzle camo'],
        [/\b(?:chain ?mail|ring ?mail)(?: pattern| print| look| texture| design)?\b/gi, 'hex mesh'],
        [/\bscale ?mail\b/gi, 'scales']
    ];
    var W21_PATQ = /^\s*(?:(?:hey|hi|so|ok|okay|um+|and|but|also|wait)[\s,:!]+)*(?:how|why|what|which|whether|does|is|are)\b|\b(?:how (?:do|can|to|would)|what (?:is|are|does|would|if)|why (?:is|does|did)|whether|do you think|should i|can i|could i|may i|is it (?:ok|okay|possible)|would (?:it|that|this) look|does (?:it|that|this)|good idea)\b/i;
    var W21_PATVERB = /\b(?:put|add|give|gimme|apply|paint|use|want|wanna|need|get|do|slap|throw|stick|try|go with|make)\b/i;
    var W21_PATORD = /\b(?:put|add|give|gimme|apply|paint|use|want|wanna|need|get|do|slap|throw|stick|try|go with|make)\b|^\s*(?:the\s+)?[a-z ]{3,22}\s+(?:on|for)\s+(?:the\s+|my\s+)?[a-z ]{3,20}\s*(?:pls|please|asap|thx|thanks)?[.!]*\s*$|,\s*go\s*[.!]*\s*$/i;
    function w21PatWords(t) {
        if (w21Off('pat') || typeof t !== 'string' || t.length > 260 || /\?/.test(t) || W21_PATQ.test(t) || !W21_PATORD.test(t)) return t;
        var hit = false; W21_PATSYN.forEach(function (r) { r[0].lastIndex = 0; if (r[0].test(t)) hit = true; r[0].lastIndex = 0; });
        if (!hit) return t;
        var named; try { named = w21Parts(w21Pre(t)).length || /\b(?:the car|whole car|everything|all over|body)\b/i.test(t); } catch (e) { named = false; }
        if (!named) return t;
        var out = t; W21_PATSYN.forEach(function (r) { out = out.replace(r[0], r[1]); });
        return W21_PATVERB.test(t) || !/\b(?:on|for)\b/i.test(t) ? out : 'put ' + out.replace(/^\s*(?:the\s+)?/i, '');          // 'splatter on boot asap' = 'put splatter on boot asap'
    }
    function w21StripOther(s) {
        if (w21Off('side') || typeof s !== 'string') return s;
        var t = s; W21_OTHERSTAY.forEach(function (re) { t = t.replace(re, ''); });
        return t !== s && (t.match(/[a-z]{3,}/gi) || []).length >= 3 ? t.replace(/\s{2,}/g, ' ').replace(/\s+([,.;!?])/g, '$1').trim() : s;
    }
    function w21Both(t) { var m = W21_BOTH.test(t); if (m && W21_KEEPSIDE.test(t) && !/\b(?:both|each|either|every|pair)\b/.test(t)) return false; return m; }
    // ---- W21H T01_side R2 2026-10-09 (hidden-set over-firing, kill noW21H_side): an order that names BOTH sides in a misspelling the side regexes do not know ("left door n rite door matte black") was read as ONE side and the other side was stripped.
    //   The side words now go through the frame's OWN typo-tolerant matcher first (fixText = VOCAB + dl() edit distance: lfet / leftt / rihgt / rifht > left / right), then the misspellings distance cannot reach (rite, ryt, rgt, rt side, drivr, pasenger, starbord, pax; the long ones
    //   by dl() with a cap), and a structural cue: TWO side nouns, each with its own DIFFERENT qualifier, joined by and / n / & / , ("<x> door n <y> door") = two sides even when <y> is a word nobody knows. Metric: see PROGRESS REPORT 2.
    var W21_LW2 = /\b(?:lef|lfet|lft|lh|lhs|drvr|drivr|drver|prt)\b|\blt\s+(?:sides?|doors?|panels?|fenders?|quarters?|flanks?)\b/;
    var W21_RW2 = /\b(?:rite|ryt|ryte|righ|rigt|riht|rhgt|rgt|rght|rh|rhs|pax|pasngr|psngr|stbd|starbd|starbord)\b|\brt\s+(?:sides?|doors?|panels?|fenders?|quarters?|flanks?)\b/;
    var W21_NOTSIDE = { driven: 1, drives: 1, driving: 1, drivel: 1 };
    var W21_TWO = /\b([a-z']{2,12})\s+(?:doors?|sides?|panels?|fenders?|quarters?|flanks?)\s*(?:,|&|\+|\b(?:and|n|nd|an|plus|then|also|with|or)\b)\s*(?:the\s+|my\s+)?([a-z']{2,12})\s+(?:doors?|sides?|panels?|fenders?|quarters?|flanks?)\b/;
    var W21_NOMOD = /^(?:the|a|an|my|your|our|this|that|both|each|every|all|two|same|other|opposite|front|rear|back|new|old|one|and|or|plus|its|his|her|their|any|some|these|those)$/;
    function w21SideFuzzy(s) {
        var l = false, r = false;
        (s.match(/[a-z]{6,10}/g) || []).forEach(function (w) {
            if (!l && /^dri?v/.test(w) && !W21_NOTSIDE[w] && (dl(w, 'driver', 1) <= 1 || dl(w, 'drivers', 1) <= 1)) l = true;
            if (!r && /^pa?s/.test(w) && (dl(w, 'passenger', 2) <= 2 || dl(w, 'passengers', 2) <= 2)) r = true;
            if (!r && /^st/.test(w) && dl(w, 'starboard', 2) <= 2) r = true;
        });
        return { l: l, r: r };
    }
    function w21SideLR(t) {
        var s = String(fixText(String(t || ''))).toLowerCase(), fz = w21SideFuzzy(s), m = W21_TWO.exec(s);
        return { l: W15F_LW.test(s) || W21_LW2.test(s) || fz.l, r: W15F_RW.test(s) || W21_RW2.test(s) || fz.r,
            two: !!(m && m[1] !== m[2] && !W21_NOMOD.test(m[1]) && !W21_NOMOD.test(m[2]) && !W21_EXPL.test(m[1]) && !W21_EXPL.test(m[2])) };
    }
    function w15fSideVerdict(t, P) {
        var l = W15F_LW.test(t), r = W15F_RW.test(t);
        var hasL = P.parts.indexOf('left side') >= 0, hasR = P.parts.indexOf('right side') >= 0;
        if (!hasL || !hasR) return null;
        if (!w21Off('side')) { var lr = w21SideLR(t); l = lr.l; r = lr.r; if (lr.two) { l = true; r = true; } }          // W21H R2: both sides named (typo-tolerant) = not a one-side order
        if (l !== r) { if (w21Off('side') ? W15F_BOTH.test(t) : w21Both(t)) return null; return { act: 'strip', key: 'side', strip: { parts: [l ? 'right side' : 'left side'] } }; }
        if (OF_CFG('W15F_sideask') && !l && !r && /\b(?:the|a|one|that|this|my|our)\s+(?:side(?: panel)?)\b/.test(t) && !/\b(?:sides|doors|fenders|flanks|both|each|either|every|all|two|2|pair|other|opposite)\b/.test(t))
            return { act: 'ask', key: 'side', q: 'Which side do you mean, the left (driver) side or the right (passenger) side? I have not painted anything yet.', chips: ['Left side', 'Right side', 'Both sides'] };
        return null;
    }
    function w15fVerdict(text, P, ctx) {
        if (w15fOff() || typeof text !== 'string' || !P || !P.n) return null;
        ctx = ctx || {};
        try {
            var tr = String(text).toLowerCase().replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim(), t = alias(String(syn(text)).toLowerCase()).replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim(), r, look =(/\b(?:red|orange|yellow|gold|green|lime|teal|cyan|blue|navy|purple|violet|pink|magenta|white|silver|gr[ae]y|black|brown|maroon|bronze|copper|cream|matte|gloss\w*|satin|chrome|carbon|candy|pearl\w*|metallic)\b/.exec(t) || [''])[0];
            // 1. speech act
            if (!w15fOff('speech')) {
                var sp = w15fSpeech(tr, { last: !!ctx.last, pending: !!ctx.pending });
                if (sp.k === 'thanks') return { act: 'ask', key: 'speech', q: 'Glad it works. I have not changed anything just now. Tell me the part and the look if you want another change, or say undo to go back.', chips: [] };
                if (sp.k === 'options') return { act: 'ask', key: 'speech', q: 'Happy to show options, and I have not changed anything yet. Which part is it for, and which looks would you like to compare? (For example: hood, candy red or matte black.)', chips: ['Make the hood candy red', 'Make the hood matte black', 'Make the hood carbon fiber'] };
                if (sp.k === 'question' || sp.k === 'state') return { act: 'ask', key: 'speech', q: 'That reads as a question, not an order, so I have not changed anything. Tell me what you want painted (the part and the look), or ask it again in other words.', chips: [] };
                if (sp.k === 'complaint') return { act: 'ask', key: 'speech', q: sp.why === 'tech' ? 'That sounds like a render or iRacing display issue rather than a paint change, so I have not touched the paint. Tell me what to change on the car if you want something different.' : 'Sorry it is not right yet. I have not changed anything. Tell me what you want instead (the part and the look), or say undo.', chips: ctx.last ? ['Undo the last change'] : [] };
            }
            // 2. kept / yardstick parts are never painted
            if (!w15fOff('keepref') && !/\b(?:swap|switch|exchange|trade|flip|reverse|interchange)\b|\bchange places\b/.test(t)) {
                // "replicate my logo's red", "use the blue from our sponsors": the element is only the SOURCE of a colour (read on the raw words, the normaliser drops it)
                var cw15 = '(?:red|orange|yellow|green|blue|purple|violet|pink|white|black|gr[ae]y|silver|gold|brown|teal|cyan|magenta|lime|navy|maroon|bronze|copper|turquoise|burgundy)';
                var srcRe = new RegExp('\\b' + cw15 + '\\s+(?:of|in|from|used\\s+in)\\s+(?:the\\s+|our\\s+|my\\s+)(logos?|sponsors?|numbers?|decals?)\\b|\\b(?:our|my|the)\\s+(logos?|sponsors?|numbers?|decals?)\'s?\\s+' + cw15 + '\\b');
                var srcOf = function (x) { var m = srcRe.exec(x); if (!m) return null; var sw = m[1] || m[2], se = /^numbers?$/.test(sw) ? 'numbers' : 'sponsors', nm = (x.match(se === 'numbers' ? /\b(?:numbers?|nums?|digits?)\b/g : /\b(?:sponsors?|logos?|decals?)\b/g) || []).length; return nm === 1 ? se : null; };
                var se15 = srcOf(tr) || (ctx.prevText && !/\b(?:numbers?|nums?|digits?|sponsors?|logos?|decals?)\b/.test(tr) ? srcOf(String(ctx.prevText).toLowerCase()) : null);          // the colour-source element of the turn before is still only a source in the follow-up ("apply #D71920")
                if (se15 && P.elems.indexOf(se15) >= 0) return { act: 'strip', key: 'keepref', strip: { parts: [], elems: [se15] } };
                var occ = w15fOccs(t), by = {}, byEl = {}, rr = {};
                occ.forEach(function (o) { var tg = o.role === 'target'; if (o.el) byEl[o.el] = byEl[o.el] === undefined ? tg : (byEl[o.el] || tg); else o.parts.forEach(function (p) { by[p] = by[p] === undefined ? tg : (by[p] || tg); if (o.role === 'ref') rr[p] = true; }); });
                var kp = [], ke = [];
                Object.keys(by).forEach(function (p) { if (by[p] === false && P.parts.indexOf(p) >= 0) kp.push(p); });
                Object.keys(byEl).forEach(function (e) { if (byEl[e] === false && P.elems.indexOf(e) >= 0) ke.push(e); });
                if (kp.length || ke.length) return { act: 'strip', key: 'keepref', strip: { parts: kp, elems: ke, hasRef: kp.some(function (p) { return rr[p]; }) } };
                // a whole-body paint that leaves a kept real part out of its exclusion list
                if (P.body) { var xs = []; Object.keys(by).forEach(function (p) { if (by[p] === false && P.bodyExcl.indexOf(p) < 0) xs.push(p); }); if (xs.length) return { act: 'excl', key: 'keepref', excl: xs }; }
            }
            // 3. one side named = one side
            if (!w15fOff('side')) { r = w15fSideVerdict(t, P); if (r) return r; }
            // 4. region / unpaintable words
            if (!ctx.last && !w15fOff('region')) {
                var named = w15fPartsOf(t, true), unnamed = P.parts.filter(function (p) { return named.indexOf(p) < 0; });
                if (W15F_REGION.test(t) && (P.body || unnamed.length || P.parts.length)) return { act: 'ask', key: 'region', q: 'The paint sheet has no separate part for that bit of the car, so I have not painted anything. Pick a part I can paint (hood, roof, trunk, sides, bumpers, spoiler) or say the whole car.', chips: ['Make the hood ' + (look || 'red'), 'Make the sides ' + (look || 'red'), 'Make the whole car ' + (look || 'red')] };
                var uo = w15fOccs(t).length, um = W15F_UNP.exec(t);
                if (um && !w26InsideBed(t, um) && (P.body || unnamed.length) && !/\b(?:except|without|leave|leaving|keep|excluding|not|but)\b[^.;]{0,25}$/.test(t.slice(0, um.index))) return { act: 'ask', key: 'unpaint', q: 'The paint sheet has no ' + um[0] + ', so I cannot paint that, and I have not changed anything. I can paint the hood, roof, trunk, sides, bumpers or spoiler, plus the numbers.', chips: [] };
                // 5. a fresh order paints only what it names
                var anaph = /\b(?:it|that|them|this|these|those|same|too|also|again|other|opposite|back|rest|again)\b/.test(t);
                var tFx = t.replace(/[a-z]{4,}/g, w15fFixWord), named2 = tFx === t ? named : w15fPartsOf(tFx, true), unnamed2 = P.parts.filter(function (p) { return named2.indexOf(p) < 0; });          // typos: "doorrs", "sdes", "trunnk" are still named parts
                if (OF_CFG('W15F_unnamed') && !ctx.prev &&!anaph && !P.body && P.parts.length && unnamed2.length && !W15F_BODYW.test(tFx.replace(/\b(?:the|my|our) car\b/g, ''))) return { act: 'ask', key: 'unnamed', q: 'I am not sure which part you mean, so I have not painted anything yet. Which part should it go on?', chips: ['Make the hood ' + (look || 'red'), 'Make the roof ' + (look || 'red'), 'Make the sides ' + (look || 'red')] };
            }
            // 6. someone else's car as the model
            if (!w15fOff('other') && !look && /\b(?:inspir\w+|(?:friend|buddy|mate|brother|dad|cousin|teammate|team ?mate)'?s?|someone else'?s|another driver'?s)\b[^.;!?]{0,20}\b(?:car|livery|paint|design|scheme|ride)\b|\blike (?:my |a )?(?:friend|buddy|mate|brother|dad|cousin|teammate)\b/.test(t)) return { act: 'ask', key: 'other', q: 'I cannot see another car, so I have not changed anything. Tell me the colours and the parts you like from it, and I will build that.', chips: [] };
            // 7. "I want a stripe": a stripe with no place named
            if (!ctx.last && !w15fOff('stripewhere') && /\b(?:stripes?|pin ?stripes?|bands?|outline|border)\b/.test(t) && !/\b(?:numbers?|nums?|digits?|sponsors?|logos?|decals?|lettering|text|names?|like|livery|scheme|theme)\b/.test(t) && !w15fPartsOf(t, true).length && !W15F_BODYW.test(t.replace(/\bit\b/g, '')) && !/\b(?:middle|centre|center|down|across|along|over|around|edge|top|bottom|side|between|racing|rally|front|rear|back|diagonal|left|right|full length|length)\b/.test(t)) return { act: 'ask', key: 'stripewhere', q: 'Where should the stripe go (over the hood and roof, down the sides, around the edge)? I have not added anything yet.', chips: ['Racing stripe down the middle', 'Stripe along the sides', 'Outline around the roof'] };
        } catch (e) { return null; }
        return null;
    }
    function w15fPainted(steps) {
        var P = { parts: [], body: false, bodyExcl: [], elems: [], layers: [], n: 0 };
        (steps || []).forEach(function (s) {
            if (!s) return; P.n++; var w = s.what || {};
            if (w.k === 'part') { var pn = w.part || (w.tg && w.tg.part); if (pn && P.parts.indexOf(pn) < 0) P.parts.push(pn); }
            else if (w.k === 'body') { P.body = true; ((s.extra && s.extra.exclude) || []).forEach(function (e) { var n = String(typeof e === 'string' ? e : (e && e.part) || '').split('@')[0]; if (n && P.bodyExcl.indexOf(n) < 0) P.bodyExcl.push(n); }); }
            else if (w.k === 'numbers' || w.k === 'sponsors') { if (P.elems.indexOf(w.k) < 0) P.elems.push(w.k); }
            else if (w.k === 'layer') P.layers = P.layers.concat(w.layers || []);
        });
        return P;
    }
    // apply a strip / excl verdict to a step list (returns a new list; steps that only refine a removed step go with it)
    function w15fApply(steps, v) {
        var drop = {}, out = [];
        (steps || []).forEach(function (s) {
            var w = (s && s.what) || {}, pn = w.k === 'part' ? (w.part || (w.tg && w.tg.part)) : null, hit = false;
            if (v.strip) hit = (pn && (v.strip.parts || []).indexOf(pn) >= 0) || ((w.k === 'numbers' || w.k === 'sponsors') && (v.strip.elems || []).indexOf(w.k) >= 0) || (w.k === 'step' && drop[w.ref]);
            if (hit) { drop[s.id] = true; return; }
            if (v.excl && w.k === 'body') { s = JSON.parse(JSON.stringify(s)); s.extra = s.extra || {}; s.extra.exclude = (s.extra.exclude || []).concat(v.excl.filter(function (x) { return (s.extra.exclude || []).indexOf(x) < 0; })); }
            out.push(s);
        });
        return out;
    }
    // W15F-END
    function syn(text) { var t = w15fNorm(w9Norm(w9Polite(w9Abbr(String(text == null ? '' : text))))); if (OF_CFG('noW3S') || OF_CFG('noW3Sa')) return t; var s = t.toLowerCase(), o = s; ALIAS_W3S.forEach(function (a, i) { if (!OF_CFG('noW3Sa' + i)) s = s.replace(a[0], a[1]); }); return s === o ? t : s; }
    return { VERSION: VERSION, w23dbg: w23dbg, w26dbg: w26dbg, w26Restore: w26Restore, w26Too: w26Too, w26NumSize: w26NumSize, w26IsLayerMatch: w26IsLayerMatch, w9arb: w9arb, syn: w26SynWrap, dropRef: dropRef, incl: w1Incl, vagueSetOf: vagueSetOf, vaguePick: vaguePick, vagueArticle: vagueArticle, decadeArticle: w14Decade, vagueBuild: vagueBuild, on: on, TH: TH, frameOf: frameOf, correct: r8Corr, pre4g: pre4g, regexStrong: regexStrong, decide: decide, _hex: hexOfWord, _fix: fixText, _lex: lex, w15fNorm: w15fNorm, w15fSpeech: w15fSpeech, w15fVerdict: w15fVerdict, w15fPainted: w15fPainted, w15fApply: w15fApply, w15fOff: w15fOff, w21Off: w21Off, _w21: { reply: w21Reply } };
});
