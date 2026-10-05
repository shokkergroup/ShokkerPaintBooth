/* ============================================================================
   SPB EASY MODE — paint-by-numbers guided flow (v3, 2026-07-16)
   ----------------------------------------------------------------------------
   OWNER SPEC (2026-07-16, third iteration — this is the system):
   "ALL of the finishes should be available in the EASY MODE. Even the
   Fractured One's etc. We need to figure out a system that's almost paint by
   numbers. First question - WHOLE CAR or BY COLOR?"

   FORK → two modes:
   · WHOLE CAR — pick one material and finish, or blend up to four from the
     complete base + monolithic catalog. A typed ``materialStack`` sends only
     authored SPEC data through a paint-aware livery trace; the user's diffuse
     paint/colors remain byte-for-byte untouched. Per-material shares total
     100%, with independent master strength and linked fine-detail scale.
   · BY COLOR — paint by numbers: click a color on the car (sampled from
     window.paintImageData — the source paint pixels, no Pro canvas needed) →
     tolerance with plain-English teaching ("exact red? slide down. every
     shade of red? slide up") → pick a finish for that color → "want the car
     color to change?" NO = keep colors / YES = solid color or borrow another
     finish's colors (baseColorMode 'special', baseColorSource 'mono:<id>')
     + hue/sat/bright sliders → repeat per color → save.
     All of it drives the REAL hard-mode zone fields (color {color_rgb,
     tolerance}, colorMode 'picker', pickerTolerance — server-side mask in
     _build_plain_rgb_color_mask_fast, tol 0=exact..100=loose).

   REAL THUMBNAILS (owner: "we also need the REAL thumbnail previews"):
   /api/swatch/<base|monolithic>/<id>?color=<hex6>&size=48&mode=split&
   prefer=live — the engine-rendered paint|spec split tile the hard-mode
   library shows; pre-baked at boot for the ENTIRE catalog, immutable-cached.
   48 is the native snapshot size — anything larger is a soft upscale.
   Geometry-lazy-loaded only for visible/open rows (≈2,400 total looks).

   Kept from v1/v2 (live-verified): opaque cover body.spb-easy-on z20000;
   preview mirror of #livePreviewImg; safeDoRender save flow + progress
   mirror + suppressed Pro results modal; pushZoneUndo before every mutation;
   capture-phase hotkey filter; spb_view_mode unset→PRO (2026-07-23 owner: Pro is the
   default front door; Easy is opt-IN via the header button — only a saved 'easy' auto-enters);
   [hidden] CSS guards (LOAD-BEARING).
   Standing traps: never touch retired body.easy-mode / shokker_ui_mode;
   BASES/MONOLITHICS/BASE_GROUPS/SPECIAL_GROUPS/HERO_BASES are global LEXICAL
   consts (bare access only, not window.*).
   ============================================================================ */
(function () {
    'use strict';

    // ---------------------------------------------------------------- config
    var LS_MODE = 'spb_view_mode';
    // [2026-08-08 E11/E12/E17] Repeat-buyer memory: hearts, recent looks, and
    // reusable saved plans. All three were completely absent — a buyer who
    // nailed a look could not shortlist it, could not find it again next
    // session, and could not put it on a second car without redoing it.
    var LS_FAVS = 'spb_easy_favs_v1';
    var LS_RECENT = 'spb_easy_recent_looks_v1';
    var LS_PLANS = 'spb_easy_plans_v1';
    var RECENT_MAX = 12;
    var PLANS_MAX = 24;
    var LS_STATE = 'spb_easy_state';
    var LS_SPECPEEK = 'spb_easy_specpeek_v1';
    var BOOT_DELAY_MS = 450;
    var PAINT_POLL_MS = 800;
    var PROGRESS_POLL_MS = 300;
    var SAVE_WATCHDOG_MS = 9000;
    var TOP_SHELF_SIZE = 50;
    var TOL_DEFAULT = 40;
    var PREVIEW_DEBOUNCE_MS = 350;

    // ------------------------------------------------------------------ state
    // view: 'fork' | 'sculpt' | 'whole' | 'bycolor'
    // wholeStack: one-to-four typed material/spec finishes; source paint stays.
    // bycolor phase: 'pick' | 'color' | 'finish' | 'options'
    // Whole Car is deliberately material/spec-only. Typed keys keep the one
    // base/monolithic ID collision (and any future collisions) honest.
    // [SPB-EASY-2026-08-19] Owner-approved flow flip: FINISH FIRST, fork after.
    // The old landing asked "WHOLE CAR or BY COLOR or SPEC SCULPT?" - a question
    // about our architecture - BEFORE the buyer had seen a single finish. It was
    // the hardest question in the flow and it was question one. Easy now opens
    // straight onto the catalog with the car above it; BY COLOR and SPEC SCULPT
    // survive as side doors in the browse bar, offered AFTER they have something
    // they like. 'fork' is still a valid view (restoreState and the ?easy deep
    // link still reach it) - it is just no longer a gate.
    var state = { view: 'whole', wholeStack: [], wholeAmount: 1.0, wholeScale: 1.0, light: 'studio' };
    // [2026-08-08 E10] The material preview was ONE fixed neutral light, which
    // under-sells exactly the finishes people buy: flake and clearcoat only
    // show their character when the light changes. These are not fake beams -
    // each mode re-weights how the REAL rendered M/R/Cc channels respond, so
    // "what does this look like at a night race" has an honest answer.
    var LIGHT_MODES = {
        studio: { label: 'GARAGE', hint: 'Even shop light - the neutral read',
                  m: 0.38, r: 0.34, c: 0.18, shade: 0.72, hi: 52, hiPow: 1.0, hiCut: 0.00, amb: 1.00, alb: 0.00 },
        sun:    { label: 'SUNLIGHT', hint: 'Hard midday key - flake and gloss pop',
                  m: 0.55, r: 0.50, c: 0.22, shade: 0.95, hi: 118, hiPow: 1.5, hiCut: 0.06, amb: 1.05, alb: 0.30 },
        night:  { label: 'NIGHT RACE', hint: 'Low ambient - only metal and clearcoat catch light',
                  m: 0.62, r: 0.60, c: 0.30, shade: 0.55, hi: 210, hiPow: 1.35, hiCut: 0.20, amb: 0.34, alb: 0.85 }
    };
    var bc = { phase: 'pick', zoneIdx: -1, pickerFor: 'finish', recolorOpen: false }; // pickerFor: 'finish' | 'borrow'
    var els = {};
    var _active = false;
    var _built = false;
    var _savedDisplayMode = null;
    var _paintPollTimer = null;
    var _progressTimer = null;
    var _watchdogTimer = null;
    var _watchdogSawProgress = false;
    var _saving = false;
    var _wrapsInstalled = false;
    var _keyFilterInstalled = false;
    var _lastPaintLoaded = null;
    var _lastDestReady = null;   // [GAUNTLET B3] see startPaintPoll
    var _enteredAt = 0;          // [GAUNTLET B3] when Easy Mode last opened
    var _catalogMode = false;
    var _proAccessibilityState = [];
    var _searchText = '';
    // [2026-08-08 E13] Easy had text search and category rows only. Pro's atlas
    // has #tags; a buyer does not think in tags, they think "something shiny"
    // or "something dark". These read the catalog's own name/desc/swatch, so
    // there is no second source of truth to maintain.
    var _filterTag = '';
    function _lumOf(hex) {
        if (!/^#[0-9a-fA-F]{6}$/.test(hex || '')) return null;
        var r = parseInt(hex.slice(1, 3), 16) / 255,
            g = parseInt(hex.slice(3, 5), 16) / 255,
            b = parseInt(hex.slice(5, 7), 16) / 255;
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    var FILTER_TAGS = [
        { key: 'shiny',   label: 'SHINY',    test: function (t) { return /gloss|mirror|chrome|wet|polish|glass|shine|lacquer|clearcoat/.test(t.s); } },
        { key: 'matte',   label: 'MATTE',    test: function (t) { return /matte|flat|satin|stealth|chalk|suede|velvet/.test(t.s); } },
        { key: 'metal',   label: 'METALLIC', test: function (t) { return /metal|flake|chrome|alloy|steel|gold|silver|copper|brass|titanium|anodiz/.test(t.s); } },
        { key: 'candy',   label: 'CANDY & PEARL', test: function (t) { return /candy|pearl|iridescen|shift|chameleon|prism|opal/.test(t.s); } },
        { key: 'pattern', label: 'PATTERNED', test: function (t) { return /pattern|camo|weave|carbon|check|stripe|geometric|hex|grid|marble|tie-dye|swirl|scale|mesh|fract|flame/.test(t.s); } },
        { key: 'dark',    label: 'DARK',     test: function (t) { return t.lum != null && t.lum < 0.30; } },
        { key: 'bright',  label: 'BRIGHT',   test: function (t) { return t.lum != null && t.lum > 0.62; } }
    ];
    function _tagSubject(key) {
        var f = finishInfo(key);
        if (!f) return null;
        // Only the SELF-description counts. Trailing clauses talk about other
        // materials ("Matte ... Great under carbon fiber") and were pulling
        // finishes into the wrong filter (measured: Matte showed under
        // PATTERNED). Take the name plus the first clause of the description.
        var desc = String(f.desc || '');
        var selfPart = desc.split(/[—.·]/)[0] || '';
        return { s: ((f.name || '') + ' ' + selfPart).toLowerCase(), lum: _lumOf(f.swatch) };
    }
    function matchesTag(key) {
        if (!_filterTag) return true;
        var def = FILTER_TAGS.filter(function (t) { return t.key === _filterTag; })[0];
        if (!def) return true;
        var subj = _tagSubject(key);
        return !!(subj && def.test(subj));
    }
    // [2026-08-08 E14] "More like this". A buyer who likes one look had no way
    // to see its neighbours in a 2,782-item catalog. Similarity is computed from
    // what the catalog already knows: shared words in the name + self-
    // description, membership of the same browse family, and swatch hue.
    var _likeKey = '';
    var _sectionOfId = null;
    var LIKE_STOP = { with: 1, that: 1, this: 1, from: 1, your: 1, over: 1, under: 1,
                      the: 1, and: 1, for: 1, into: 1, like: 1, real: 1, very: 1,
                      base: 1, paint: 1, finish: 1, look: 1, looks: 1, color: 1, color: 1,
                      // family words in NAMES inflate every sibling equally
                      // (measured: "Carbon Fiber (Foundation)" pulled Vinyl
                      // Wrap / Pearl / Chrome purely on the word "foundation")
                      foundation: 1, enhanced: 1, exotic: 1, series: 1, special: 1, edition: 1 };
    function _sectionMap() {
        if (_sectionOfId) return _sectionOfId;
        _sectionOfId = {};
        try {
            buildCatalogSections().forEach(function (sec) {
                (sec.ids || []).forEach(function (id) { if (!(id in _sectionOfId)) _sectionOfId[id] = sec.title; });
            });
        } catch (e) {}
        return _sectionOfId;
    }
    function _likeTokens(key) {
        var f = finishInfo(key);
        if (!f) return null;
        var selfPart = String(f.desc || '').split(/[\u2014.\u00b7]/)[0] || '';
        var words = ((f.name || '') + ' ' + selfPart).toLowerCase().match(/[a-z]{4,}/g) || [];
        var set = {};
        words.forEach(function (w) { if (!LIKE_STOP[w]) set[w] = 1; });
        return { set: set, lum: _lumOf(f.swatch), hue: _hueOf(f.swatch), sec: _sectionMap()[f.id] || '' };
    }
    function _hueOf(hex) {
        if (!/^#[0-9a-fA-F]{6}$/.test(hex || '')) return null;
        var r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
        if (d < 0.02) return null;                       // grayscale has no hue
        var h = mx === r ? ((g - b) / d) % 6 : (mx === g ? (b - r) / d + 2 : (r - g) / d + 4);
        h *= 60; if (h < 0) h += 360;
        return h;
    }
    function likeScore(refT, key) {
        var t = _likeTokens(key);
        if (!t || !refT) return -1;
        var shared = 0;
        for (var w in t.set) { if (refT.set[w]) shared++; }
        var score = shared * 3;
        if (t.sec && refT.sec && t.sec === refT.sec) score += 2;   // family is a hint, not the answer
        if (t.hue != null && refT.hue != null) {
            var dh = Math.abs(t.hue - refT.hue); if (dh > 180) dh = 360 - dh;
            if (dh < 25) score += 2; else if (dh < 55) score += 1;
        }
        if (t.lum != null && refT.lum != null && Math.abs(t.lum - refT.lum) < 0.15) score += 1;
        return score;
    }
    function currentLookKey() {
        try {
            if (state.view === 'whole') {
                var st = normalizeWholeShares(state.wholeStack);
                return st.length ? st[st.length - 1].key : '';
            }
            var z = zones[bc.zoneIdx];
            if (!z) return '';
            return z.finish ? finishKey('monolithic', z.finish) : (z.base ? finishKey('base', z.base) : '');
        } catch (e) { return ''; }
    }
    function likeListIds(refKey, limit) {
        var refT = _likeTokens(refKey);
        if (!refT) return [];
        var seen = {}, scored = [];
        buildCatalogSections().forEach(function (sec) {
            (sec.ids || []).forEach(function (id) {
                if (seen[id] || id === refKey) return;
                seen[id] = 1;
                var sc = likeScore(refT, id);
                if (sc > 3) scored.push({ id: id, sc: sc });
            });
        });
        scored.sort(function (a, b2) { return b2.sc - a.sc; });
        return scored.slice(0, limit || 60).map(function (r) { return r.id; });
    }

    // [2026-08-08 E16] BY COLOR showed the same fixed 50 to everybody. Spec
    // Sculpt has "FOR THIS PAINT 12"; the by-color step knew the exact color
    // the buyer clicked and ignored it. Rank the catalog against that color:
    // same-family hues read as intentional, neutrals (chrome/matte/carbon) work
    // on anything, and a deliberate complement is a real design choice.
    function _rgbHue(rgb) {
        if (!rgb) return null;
        var r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
        if (d < 0.02) return null;
        var h = mx === r ? ((g - b) / d) % 6 : (mx === g ? (b - r) / d + 2 : (r - g) / d + 4);
        h *= 60; if (h < 0) h += 360;
        return h;
    }
    function _rgbLum(rgb) {
        if (!rgb) return null;
        return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
    }
    function forColorIds(rgb, limit) {
        var refHue = _rgbHue(rgb), refLum = _rgbLum(rgb);
        if (refLum == null) return [];
        var seen = {}, scored = [];
        buildCatalogSections().forEach(function (sec) {
            (sec.ids || []).forEach(function (id) {
                if (seen[id]) return;
                seen[id] = 1;
                var f = finishInfo(id);
                if (!f) return;
                var hue = _hueOf(f.swatch), lum = _lumOf(f.swatch);
                var sc = 0;
                if (hue == null) sc += 3;                       // neutral: safe on any color
                else if (refHue != null) {
                    var dh = Math.abs(hue - refHue); if (dh > 180) dh = 360 - dh;
                    if (dh < 20) sc += 5;                        // same family
                    else if (dh < 45) sc += 3;
                    else if (dh > 150) sc += 4;                  // deliberate complement
                }
                if (lum != null && Math.abs(lum - refLum) > 0.25) sc += 1;   // reads against the paint
                if (sc > 0) scored.push({ id: id, sc: sc });
            });
        });
        scored.sort(function (a, b2) { return b2.sc - a.sc; });
        return scored.slice(0, limit || 12).map(function (r) { return r.id; });
    }
    function currentPickedRgb() {
        try {
            if (state.view !== 'bycolor') return null;
            var z = zones[bc.zoneIdx];
            return (z && z.color && z.color.color_rgb) ? z.color.color_rgb : null;
        } catch (e) { return null; }
    }

    function filterChipsHtml() {
        var cur = currentLookKey();
        var curInfo = cur ? finishInfo(cur) : null;
        return '<div class="spb-easy-tagbar" id="spbEasyTagBar">' +
            (curInfo
                ? '<button type="button" class="spb-easy-tag spb-easy-tag-like' + (_likeKey ? ' on' : '') +
                  '" data-like="' + esc(curInfo.key) + '" title="Show looks that are close to ' + esc(curInfo.name) + '">' +
                  '\u2726 MORE LIKE ' + esc((curInfo.name || '').toUpperCase().slice(0, 16)) + '</button>'
                : '') +
            FILTER_TAGS.map(function (t) {
                return '<button type="button" class="spb-easy-tag' + (_filterTag === t.key ? ' on' : '') +
                    '" data-tag="' + t.key + '">' + esc(t.label) + '</button>';
            }).join('') +
            (_filterTag ? '<button type="button" class="spb-easy-tag spb-easy-tag-clear" data-tag="">\u2715 CLEAR</button>' : '') +
            '</div>';
    }
    var _topShelf = null;
    var _catalogSections = null;
    var _kickTimer = null;
    var _iracingCars = [];
    var _carsLoading = false;
    var _carFilterQuery = '';
    var _saveExpected = null;
    // [2026-08-08 E18] One plan, several cars. The dropdown only ever set the
    // destination of THE current save, so running the same look on a second car
    // meant redoing everything. The finished job is copied to each extra folder
    // through /deploy-to-iracing (the same verified copy Pro's deploy uses) -
    // no second render, and each target is confirmed before it is called done.
    var _alsoCars = [];
    var _lastJobId = '';

    // ---------------------------------------------------------------- helpers
    function $(id) { return document.getElementById(id); }
    function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
    function lsJson(k, fallback) {
        try { var v = JSON.parse(lsGet(k) || 'null'); return v == null ? fallback : v; }
        catch (e) { return fallback; }
    }
    function favList() { var a = lsJson(LS_FAVS, []); return Array.isArray(a) ? a : []; }
    function isFav(key) { return favList().indexOf(key) !== -1; }
    function toggleFav(key) {
        var a = favList(), i = a.indexOf(key);
        if (i === -1) a.unshift(key); else a.splice(i, 1);
        lsSet(LS_FAVS, JSON.stringify(a.slice(0, 300)));
        return i === -1;
    }
    function recentList() { var a = lsJson(LS_RECENT, []); return Array.isArray(a) ? a : []; }
    function noteRecentLook(key) {
        if (!key) return;
        var a = recentList().filter(function (k) { return k !== key; });
        a.unshift(key);
        lsSet(LS_RECENT, JSON.stringify(a.slice(0, RECENT_MAX)));
    }
    function planList() { var a = lsJson(LS_PLANS, []); return Array.isArray(a) ? a : []; }
    // A plan is Easy's OWN decisions — not a zone dump. Rebuildable on any car,
    // any paint, so "put my look on the next car" is one click.
    function capturePlan(name) {
        var plan = { name: String(name || 'My look').slice(0, 40), ts: Date.now(), view: state.view };
        if (state.view === 'whole') {
            plan.whole = {
                rows: normalizeWholeShares(state.wholeStack).map(function (r) {
                    return { key: r.key, weight: r.weight };
                }),
                amount: wholeEffectAmount(), scale: state.wholeScale
            };
        } else {
            plan.colors = easyColorZones().map(function (p) {
                var z = p.z;
                return {
                    rgb: (z.color && z.color.color_rgb) ? z.color.color_rgb.slice() : null,
                    tol: z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT,
                    hex: z.pickerColor || null,
                    finishKey: z.finish ? finishKey('monolithic', z.finish) : (z.base ? finishKey('base', z.base) : null),
                    colorMode: z.baseColorMode || null,
                    baseColor: z.baseColor || null,
                    baseColorSource: z.baseColorSource || null,
                    hue: z.baseHueOffset || 0, sat: z.baseSaturationAdjust || 0, brt: z.baseBrightnessAdjust || 0
                };
            });
        }
        return plan;
    }
    // [2026-08-08 E19] Sharing. A buyer who builds something good had no way to
    // hand it to a team-mate, and no way to receive one. The plan is already a
    // small, car-independent object (E17), so it travels as one paste-able code
    // that survives Discord/forum line-wrapping.
    var SHARE_PREFIX = 'SPB1:';
    function encodePlan(plan) {
        try {
            var json = JSON.stringify(plan);
            return SHARE_PREFIX + btoa(unescape(encodeURIComponent(json)));
        } catch (e) { return ''; }
    }
    function decodePlan(code) {
        try {
            var raw = String(code || '').trim().replace(/\s+/g, '');
            var i = raw.indexOf(SHARE_PREFIX);
            if (i === -1) return null;
            raw = raw.slice(i + SHARE_PREFIX.length);
            var json = decodeURIComponent(escape(atob(raw)));
            var plan = JSON.parse(json);
            if (!plan || typeof plan !== 'object') return null;
            if (!plan.whole && !plan.colors) return null;
            return plan;
        } catch (e) { return null; }
    }
    function openShare() {
        var back = $('spbEasyShareBackdrop');
        if (!back) return;
        var plan = capturePlan((state.view === 'whole') ? 'Shared whole-car look' : 'Shared color plan');
        var hasWork = (plan.whole && plan.whole.rows.length) || (plan.colors && plan.colors.length);
        var out = $('spbEasyShareOut');
        var code = hasWork ? encodePlan(plan) : '';
        if (out) {
            out.value = code || 'Pick a finish first — then this box will hold a code you can send.';
            out.readOnly = true;
        }
        var copyBtn = $('spbEasyShareCopy');
        if (copyBtn) copyBtn.disabled = !code;
        var inp = $('spbEasyShareIn');
        if (inp) inp.value = '';
        var msg = $('spbEasyShareMsg');
        if (msg) msg.textContent = '';
        back.hidden = false;
        if (out && code) { try { out.focus(); out.select(); } catch (e) {} }
    }
    function closeShare() { var b2 = $('spbEasyShareBackdrop'); if (b2) b2.hidden = true; }
    function wireShare() {
        var back = $('spbEasyShareBackdrop');
        if (!back) return;
        back.addEventListener('click', function (e) { if (e.target === back) closeShare(); });
        var cl = $('spbEasyShareClose'); if (cl) cl.addEventListener('click', closeShare);
        var copyBtn = $('spbEasyShareCopy');
        if (copyBtn) copyBtn.addEventListener('click', function () {
            var out = $('spbEasyShareOut');
            if (!out || !out.value) return;
            try { out.select(); } catch (e) {}
            var done = false;
            try { done = document.execCommand('copy'); } catch (e) { done = false; }
            if (!done && navigator.clipboard) {
                navigator.clipboard.writeText(out.value).then(function () {
                    var m = $('spbEasyShareMsg'); if (m) m.textContent = 'Copied \u2014 paste it to your team-mate.';
                });
                return;
            }
            var m2 = $('spbEasyShareMsg');
            if (m2) m2.textContent = done ? 'Copied \u2014 paste it to your team-mate.' : 'Press Ctrl+C to copy the highlighted code.';
        });
        var loadBtn = $('spbEasyShareLoad');
        if (loadBtn) loadBtn.addEventListener('click', function () {
            var inp = $('spbEasyShareIn');
            var msg = $('spbEasyShareMsg');
            var plan = decodePlan(inp ? inp.value : '');
            if (!plan) { if (msg) msg.textContent = 'That does not look like a Shokker look code.'; return; }
            closeShare();
            applyPlan(plan);
            var all = planList().filter(function (p2) { return p2 && p2.name !== plan.name; });
            all.unshift(plan);
            lsSet(LS_PLANS, JSON.stringify(all.slice(0, PLANS_MAX)));
            renderMyLooks();
        });
    }

    function savePlan(name) {
        var plan = capturePlan(name);
        var hasWork = (plan.whole && plan.whole.rows.length) || (plan.colors && plan.colors.length);
        if (!hasWork) { try { if (window.showToast) window.showToast('Pick a finish first, then save the look', 'info'); } catch (e) {} return null; }
        var all = planList().filter(function (p) { return p && p.name !== plan.name; });
        all.unshift(plan);
        lsSet(LS_PLANS, JSON.stringify(all.slice(0, PLANS_MAX)));
        return plan;
    }
    function deletePlan(name) {
        lsSet(LS_PLANS, JSON.stringify(planList().filter(function (p) { return p && p.name !== name; })));
    }
    function applyPlan(plan) {
        if (!plan) return false;
        undoPush('Easy Mode: load look "' + (plan.name || '') + '"');
        try {
            if (plan.view === 'whole' && plan.whole) {
                state.view = 'whole';
                state.wholeStack = (plan.whole.rows || []).map(function (r) {
                    var f = finishInfo(r.key);
                    return f ? { key: f.key, id: f.id, registryType: f.type, weight: r.weight } : null;
                }).filter(Boolean);
                state.wholeAmount = plan.whole.amount != null ? plan.whole.amount : 1;
                state.wholeScale = plan.whole.scale != null ? plan.whole.scale : 1;
                applyWholeStack(false, false, false);   // [2026-08-08] must repaint: USE THIS is a visible choice
            } else {
                state.view = 'bycolor';
                for (var i = zones.length - 1; i >= 0; i--) { if (isEasyColorZone(zones[i])) zones.splice(i, 1); }
                (plan.colors || []).forEach(function (c, n) {
                    if (!c || !c.rgb) return;
                    var z = {
                        id: (typeof _newZoneId === 'function') ? _newZoneId() : ('easyc_' + (n + 1)),
                        name: 'Color ' + (n + 1),
                        color: { color_rgb: c.rgb.slice(), tolerance: c.tol != null ? c.tol : TOL_DEFAULT },
                        colorMode: 'picker', pickerColor: c.hex || '#888888',
                        pickerTolerance: c.tol != null ? c.tol : TOL_DEFAULT,
                        base: null, pattern: 'none', finish: null, intensity: '100',
                        customSpec: null, customPaint: null, customBright: null,
                        colors: [], regionMask: null, patternStack: []
                    };
                    if (c.colorMode) { z.baseColorMode = c.colorMode; z.baseColor = c.baseColor || null; z.baseColorSource = c.baseColorSource || null; }
                    z.baseHueOffset = c.hue || 0; z.baseSaturationAdjust = c.sat || 0; z.baseBrightnessAdjust = c.brt || 0;
                    zones.push(z);
                    var f = c.finishKey ? finishInfo(c.finishKey) : null;
                    if (f) { if (f.type === 'monolithic') { zones[zones.length - 1].finish = f.id; } else { zones[zones.length - 1].base = f.id; } }
                });
                if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'easy-mode plan load');
                bc.zoneIdx = zones.length - 1;
                bc.phase = easyColorZones().length ? 'options' : 'pick';
            }
        } catch (e) {
            try { console.error('[spbEasy] applyPlan failed:', e); } catch (e2) {}
            return false;
        }
        persistState();
        refreshZonesUI();
        renderRail();
        kickPreview();
        try { if (window.showToast) window.showToast('Loaded "' + (plan.name || 'look') + '"', 'success'); } catch (e) {}
        return true;
    }
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function serverBase() {
        try { if (typeof getServerBase === 'function') return getServerBase() || ''; } catch (e) {}
        return '';
    }
    function finishKey(type, id) {
        return (type === 'monolithic' ? 'monolithic' : 'base') + '::' + String(id || '');
    }
    function parseFinishKey(value, forcedType) {
        var raw = String(value || '');
        var match = /^(base|monolithic)::(.+)$/.exec(raw);
        return match ? { type: match[1], id: match[2] }
            : { type: forcedType === 'monolithic' ? 'monolithic' : (forcedType === 'base' ? 'base' : ''), id: raw };
    }
    function finishInfo(value, forcedType) {
        var parsed = parseFinishKey(value, forcedType);
        var id = parsed.id;
        if (parsed.type === 'monolithic') {
            try {
                if (typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID[id]) {
                    var typedM = MONOLITHICS_BY_ID[id];
                    return { key: finishKey('monolithic', id), id: id, name: typedM.name || id, desc: typedM.desc || '', swatch: typedM.swatch || '', type: 'monolithic' };
                }
            } catch (typedMonoError) {}
            return null;
        }
        if (parsed.type === 'base') {
            try {
                if (typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID[id]) {
                    var typedB = BASES_BY_ID[id];
                    return { key: finishKey('base', id), id: id, name: typedB.name || id, desc: typedB.desc || '', swatch: typedB.swatch || '', type: 'base' };
                }
            } catch (typedBaseError) {}
            return null;
        }
        // → {id, name, desc, swatch, type:'base'|'monolithic'} or null
        try {
            if (typeof BASES_BY_ID !== 'undefined' && BASES_BY_ID[id]) {
                var b = BASES_BY_ID[id];
                return { key: finishKey('base', id), id: id, name: b.name || id, desc: b.desc || '', swatch: b.swatch || '', type: 'base' };
            }
        } catch (e) {}
        try {
            if (typeof MONOLITHICS_BY_ID !== 'undefined' && MONOLITHICS_BY_ID[id]) {
                var m = MONOLITHICS_BY_ID[id];
                return { key: finishKey('monolithic', id), id: id, name: m.name || id, desc: m.desc || '', swatch: m.swatch || '', type: 'monolithic' };
            }
        } catch (e) {}
        return null;
    }
    function easyFeaturedQualityEligible(value) {
        var info = finishInfo(value);
        if (!info) return false;
        try {
            if (typeof CATALOG_SCORECARD_METRICS === 'undefined') return false;
            var row = CATALOG_SCORECARD_METRICS[info.type + ':' + info.id];
            if (!row || row.status !== 'OK' || row.priority === 'FIX') return false;
            return Number(row.overallQuality || 0) >= 85;
        } catch (e) { return false; }
    }
    // Real engine-rendered paint|spec split tile — the same image the
    // hard-mode Finish Library shows. Reuse its canonical URL builder so
    // Easy Mode gets the identical authored asset and cache fingerprint.
    // Never manufacture a color swatch here.
    function thumbUrl(info) {
        try {
            if (typeof window.getSwatchUrl === 'function') {
                var canonical = window.getSwatchUrl(info.id, info.swatch || '888888', true, 48);
                if (canonical && canonical.indexOf('/api/swatch/' + info.type + '/') !== -1) return canonical;
            }
        } catch (e) {}
        var tint = /^#[0-9a-fA-F]{6}$/.test(info.swatch || '') ? info.swatch.slice(1) : '888888';
        var fp = window._SHOKKER_SWATCH_FP || {};
        var version = fp[info.type + ':' + info.id] || window._SHOKKER_SWATCH_V || 'easy-real-split';
        return serverBase() + '/api/swatch/' + info.type + '/' + encodeURIComponent(info.id) +
            '?color=' + tint.toLowerCase() + '&size=48&mode=split&prefer=live&v=' + encodeURIComponent(version);
    }
    function paintLoaded() {
        try {
            var pf = $('paintFile');
            if (pf && String(pf.value || '').trim()) return true;
            if (typeof window._spbFlatPaintLiveSource !== 'undefined' && window._spbFlatPaintLiveSource) return true;
        } catch (e) {}
        return false;
    }
    function idIsValid(v) { return /^\d{4,7}$/.test(String(v || '').trim()); }
    function normalizedWholeStack(raw) {
        if (!Array.isArray(raw)) return [];
        return raw.slice(0, 4).map(function (entry) {
            var info = finishInfo(entry && (entry.key || entry.id), entry && (entry.registryType || entry.registry_type || entry.type));
            var weight = Number(entry && entry.weight);
            if (!info || !Number.isFinite(weight) || weight <= 0) return null;
            return { key: info.key, id: info.id, registryType: info.type, weight: Math.max(1, Math.min(100, Math.round(weight))) };
        }).filter(Boolean);
    }
    function allocateWholeShares(rows, budget) {
        rows = normalizedWholeStack(rows);
        budget = Math.max(rows.length, Math.round(Number(budget) || 0));
        if (!rows.length) return [];
        if (rows.length === 1) { rows[0].weight = budget; return rows; }
        var adjustable = Math.max(0, budget - rows.length);
        var bases = rows.map(function (row) { return Math.max(0, row.weight - 1); });
        var baseTotal = bases.reduce(function (sum, value) { return sum + value; }, 0);
        if (baseTotal <= 0) { bases = rows.map(function () { return 1; }); baseTotal = rows.length; }
        var fractions = [], used = 0;
        rows.forEach(function (row, index) {
            var exact = adjustable * bases[index] / baseTotal;
            var whole = Math.floor(exact);
            row.weight = 1 + whole;
            used += whole;
            fractions.push({ index: index, fraction: exact - whole });
        });
        fractions.sort(function (a, b) { return b.fraction - a.fraction || a.index - b.index; });
        var left = adjustable - used;
        for (var i = 0; i < left; i++) rows[fractions[i % fractions.length].index].weight++;
        return rows;
    }
    function normalizeWholeShares(rows) { return allocateWholeShares(rows, 100); }
    function rebalanceWholeShare(rows, changedIndex, requested) {
        rows = normalizeWholeShares(rows);
        if (!rows[changedIndex] || rows.length === 1) return rows;
        var max = 100 - (rows.length - 1);
        var target = Math.max(1, Math.min(max, Math.round(Number(requested) || rows[changedIndex].weight)));
        var changed = rows[changedIndex];
        var others = rows.filter(function (_row, index) { return index !== changedIndex; });
        others = allocateWholeShares(others, 100 - target);
        var oi = 0;
        return rows.map(function (_row, index) {
            if (index === changedIndex) { changed.weight = target; return changed; }
            return others[oi++];
        });
    }
    function wholeEffectAmount() {
        var value = Number(state.wholeAmount);
        return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 1));
    }
    function persistState() {
        lsSet(LS_STATE, JSON.stringify({ view: state.view, wholeStack: normalizeWholeShares(state.wholeStack), wholeAmount: wholeEffectAmount(), wholeScale: state.wholeScale, light: state.light, protect: protectSpots(), protectFor: state.protectFor || '' }));
    }
    function restoreState() {
        try {
            var p = JSON.parse(lsGet(LS_STATE) || 'null');
            if (p && typeof p === 'object') {
                if (p.view === 'whole' || p.view === 'bycolor' || p.view === 'fork' || p.view === 'auto') state.view = p.view;
                state.wholeStack = normalizedWholeStack(p.wholeStack);
                if (!state.wholeStack.length && typeof p.wholeId === 'string') {
                    var legacy = finishInfo(p.wholeId);
                    if (legacy) state.wholeStack = [{ key: legacy.key, id: legacy.id, registryType: legacy.type, weight: 100 }];
                }
                state.wholeStack = normalizeWholeShares(state.wholeStack);
                var restoredAmount = Number(p.wholeAmount);
                state.wholeAmount = Number.isFinite(restoredAmount) ? Math.max(0, Math.min(1, restoredAmount)) : 1.0;
                var restoredScale = Number(p.wholeScale);
                state.wholeScale = Number.isFinite(restoredScale) ? Math.max(0.25, Math.min(1, restoredScale)) : 1.0;
                if (p.light && LIGHT_MODES[p.light]) state.light = p.light;   // [E10]
                if (Array.isArray(p.protect)) { state.protect = p.protect.slice(0, 12); state.protectFor = String(p.protectFor || ''); }
            }
        } catch (e) {}
    }
    // [2026-08-08 E40] Sometimes you just want to LOOK at the car. The rail
    // folds away and the button stays on the same edge, so the way back is
    // exactly where the way out was. Persisted, because a buyer who wants the
    // big picture usually wants it for more than one look.
    var LS_RAIL = 'spb_easy_rail_hidden';
    function railHidden() { return lsGet(LS_RAIL) === '1'; }
    function syncRailToggle() {
        var hidden = railHidden();
        document.body.classList.toggle('spb-easy-rail-hidden', !!(hidden && _active));
        var btn = $('spbEasyRailToggle');
        if (btn) {
            btn.textContent = hidden ? '\u25b6 SHOW CONTROLS' : '\u25c0 BIGGER PICTURE';
            btn.setAttribute('aria-expanded', hidden ? 'false' : 'true');
            btn.title = hidden ? 'Bring the controls back'
                               : 'Fold the controls away and give the car the whole window';
        }
    }
    // [2026-08-09 S37] Delegated so the tab survives whichever subsystem is
    // rendering the rail - Easy Mode's own view, or Spec Sculpt's.
    var railToggleWired = false;
    function wireRailToggleOnce() {
        if (railToggleWired) return;
        railToggleWired = true;
        document.addEventListener('click', function (event) {
            var btn = event.target && event.target.closest
                ? event.target.closest('#spbEasyRailToggle') : null;
            if (!btn) return;
            event.preventDefault();
            toggleRail();
        });
    }

    function toggleRail() {
        lsSet(LS_RAIL, railHidden() ? '0' : '1');
        syncRailToggle();
        try { if (typeof syncPreviewNow === 'function') syncPreviewNow(); } catch (e) {}
    }

    function kickPreview() {
        // An immediate decision (notably choosing the finish after moving the
        // color picker) supersedes any queued color-preview kick. Otherwise the
        // stale timer can abort/restart the authoritative finish render.
        if (_kickTimer) { clearTimeout(_kickTimer); _kickTimer = null; }
        syncProtectZones();   // [E25] zones are rebuilt constantly; re-attach the shield
        try { if (typeof window.spbKickLivePreview === 'function') window.spbKickLivePreview(); } catch (e) {}
    }
    function kickPreviewDebounced() {
        if (_kickTimer) clearTimeout(_kickTimer);
        _kickTimer = setTimeout(function () { _kickTimer = null; kickPreview(); }, PREVIEW_DEBOUNCE_MS);
    }
    function undoPush(label) {
        try { if (typeof pushZoneUndo === 'function') pushZoneUndo(label); } catch (e) {}
    }
    function refreshZonesUI() {
        try { if (_built && _active) syncHistoryUI(); } catch (e) {}
        try { if (typeof renderZones === 'function') renderZones(); } catch (e) {}
    }
    function friendlyCarName(value) {
        try {
            if (window.spbEasySculpt && typeof window.spbEasySculpt.friendlyCarName === 'function') return window.spbEasySculpt.friendlyCarName(value);
        } catch (e) {}
        var raw = String(value || '').trim();
        if (!raw) return '';
        return raw.replace(/([a-z])([0-9])/g, '$1 $2').replace(/([0-9])([a-z])/g, '$1 $2')
            .replace(/\b(gtp|gt3|gt4|gte|arca|bmw|ump)\b/gi, function (m) { return m.toUpperCase(); })
            .replace(/(^|\s)([a-z])/g, function (_m, a, b) { return a + b.toUpperCase(); });
    }
    function normalizePath(value) { return String(value || '').replace(/\//g, '\\').replace(/\\+$/, '').toLowerCase(); }
    function currentOutputDir() { var el = $('outputDir'); return el ? String(el.value || '').trim() : ''; }
    function currentCarRecord() {
        var path = normalizePath(currentOutputDir());
        return _iracingCars.filter(function (car) { return normalizePath(car.path) === path; })[0] || null;
    }
    function customNumberIsOn() {
        var el = $('useCustomNumberCheckbox');
        return !el || !!el.checked;
    }
    function expectedOutputNames() {
        var idEl = $('iracingId');
        var id = idEl ? String(idEl.value || '').trim() : '';
        return [(customNumberIsOn() ? 'car_num_' : 'car_') + id + '.tga', 'car_spec_' + id + '.tga'];
    }
    // [2026-08-08 E30] Most buyers paint the same two or three cars over and
    // over, and every single save made them find them again in a 179-entry
    // dropdown. The cars they actually use are now one click, newest first.
    var LS_TOUR = 'spb_easy_tour_seen';
    var LS_CARS = 'spb_easy_recent_cars';
    var RECENT_CARS_MAX = 4;
    function recentCars() {
        try {
            var list = JSON.parse(lsGet(LS_CARS) || '[]');
            return Array.isArray(list) ? list.filter(function (c) { return c && c.path; }) : [];
        } catch (e) { return []; }
    }
    function noteRecentCar(path, name) {
        if (!path) return;
        var key = normalizePath(path);
        var list = recentCars().filter(function (c) { return normalizePath(c.path) !== key; });
        list.unshift({ path: path, name: name || '' });
        lsSet(LS_CARS, JSON.stringify(list.slice(0, RECENT_CARS_MAX)));
    }
    function recentCarsHtml() {
        var list = recentCars();
        if (!list.length) return '';
        var current = normalizePath(currentOutputDir());
        return '<div class="spb-easy-recent-cars"><span>YOUR CARS</span>' +
            list.map(function (c) {
                var on = normalizePath(c.path) === current ? ' class="on"' : '';
                return '<button type="button" data-recent-car="' + esc(c.path) + '"' + on +
                    ' title="' + esc(c.name || c.path) + '">' +
                    esc(friendlyCarName(c.name || '') || c.name || 'Car') + '</button>';
            }).join('') + '</div>';
    }
    function chooseCar(path) {
        var select = $('spbEasyCarSelect');
        if (!select) return false;
        var found = false;
        Array.prototype.forEach.call(select.options, function (option) {
            if (normalizePath(option.value) === normalizePath(path)) { select.value = option.value; found = true; }
        });
        if (!found) return false;
        try { select.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
        return true;
    }

    // [2026-08-08 E33] The two number buttons said "CUSTOM NUMBER car_num" and
    // "SIM-STAMPED car" — the internal iRacing filename prefixes. A buyer had
    // no way to tell which one their league wants, and picking wrong means
    // either two numbers on the car or none. Say what each one DOES.
    var SEARCH_TIP = 'Type what you want and Shokker searches every look by name and ' +
        'description \u2014 try chrome, matte, carbon, candy, or a color.';
    var CAT_TIP = 'Switch between the hand-picked starter shelf and every look in the ' +
        'catalogue. The shelf is a short list that always works; the full catalogue is everything.';

    // [GAUNTLET B1 2026-08-20] Once the buyer picks a side themselves, we never
    // silently move it again - detection is a helpful default, not a correction.
    var _numberModeTouched = false;

    // Returns true (paint carries the number), false (iRacing adds it), or null
    // (the filename is not a conventional iRacing name, so we genuinely do not
    // know and must keep asking). Same rule Spec Sculpt has used since 2026-07.
    function detectNumberModeFromPaint() {
        var path = '';
        try {
            path = (typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || '';
        } catch (e) { return null; }
        if (!path) return null;
        var parts = String(path).replace(/\\/g, '/').split('/').filter(Boolean);
        var filename = parts[parts.length - 1] || '';
        var m = filename.match(/^car_(num_)?(\d{4,7})(?:\.[^.]+)?$/i);
        if (!m) return null;
        return !!m[1];
    }

    // Apply the detected default, unless the buyer has already chosen.
    function applyDetectedNumberMode() {
        if (_numberModeTouched) return null;
        var detected = detectNumberModeFromPaint();
        if (detected === null) return null;
        if (customNumberIsOn() === detected) return detected;
        try {
            var c = $('useCustomNumberCheckbox'), sm = $('useSimStampedCheckbox');
            if (c) c.checked = !!detected;
            if (sm) sm.checked = !detected;
            if (typeof toggleCustomNumber === 'function') toggleCustomNumber(!!detected);
        } catch (e) {}
        return detected;
    }

    function numberModeCopy(custom) {
        return custom
            ? 'The number is part of your paint. iRacing will not add one on top — pick this if ' +
              'your design already has your number on it, or your league runs fixed numbers.'
            : 'iRacing stamps your number onto the car for you, in the series font. Pick this if ' +
              'your paint has NO number on it.';
    }
    function numberModeHtml(custom) {
        return '<div class="spb-easy-number-why" id="spbEasyNumberWhy">' +
            '<b>' + (custom ? 'YOUR PAINT CARRIES THE NUMBER' : 'iRACING ADDS THE NUMBER') + '</b>' +
            '<span>' + esc(numberModeCopy(custom)) + '</span>' +
            '<em>Not sure? Look at your paint above: if you can see your number on it, pick ' +
            '“MY PAINT HAS THE NUMBER”. If you cannot, let iRacing add it.</em></div>';
    }

    function carOptionsHtml() {
        var current = normalizePath(currentOutputDir());
        var html = '<option value="">Choose the iRacing car...</option>';
        _iracingCars.forEach(function (car) {
            html += '<option value="' + esc(car.path) + '"' + (normalizePath(car.path) === current ? ' selected' : '') + '>' +
                esc(friendlyCarName(car.name)) + ' — folder: ' + esc(car.name) + '</option>';
        });
        return html;
    }
    function populateCarSelect() {
        var select = $('spbEasyCarSelect');
        if (!select) return;
        select.innerHTML = carOptionsHtml();
        filterEasyCarOptions();
        refreshSaveEls();
    }
    function filterEasyCarOptions() {
        var search = $('spbEasyCarSearch');
        var select = $('spbEasyCarSelect');
        if (!select) return;
        var query = String(search && search.value || _carFilterQuery || '').trim().toLowerCase();
        Array.prototype.forEach.call(select.options, function (option, index) {
            option.hidden = !!query && index > 0 && !option.selected && option.textContent.toLowerCase().indexOf(query) === -1;
        });
    }
    function ensureIracingCars() {
        if (_carsLoading || _iracingCars.length) return;
        _carsLoading = true;
        fetch(serverBase() + '/api/iracing-paint-cars', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : {}; })
            .then(function (data) {
                _iracingCars = (data && Array.isArray(data.cars) ? data.cars : []).filter(function (car) { return car && car.name && car.path && !/^(cars|helmets|suits|pitcrew)$/i.test(car.name); });
                _carsLoading = false;
                populateCarSelect();
            }).catch(function () { _carsLoading = false; });
    }
    // [GAUNTLET A2 2026-08-20] Every family now says what it IS, in one line of
    // buyer language. Before this, THREE families shared "Clean painted surfaces
    // and dependable real-car materials." and five more fell through to the
    // placeholder "Click to browse every authored look in this family." - so a
    // buyer scanning 62 rows learned nothing the family name had not already
    // told them. Keyed on a normalized title (emoji, stars and middots stripped)
    // so renaming a family's decoration cannot silently drop its description.
    var CATEGORY_DESCS = {
        'foundation': 'The everyday paints - gloss, matte, satin, primer. Start here for a clean color.',
        'enhanced foundation': 'The same everyday paints rebuilt with real grit, flake and coverage variation.',
        'efx enhanced foundation exotic': 'Everyday paint pushed somewhere strange - familiar surfaces, exotic twist.',
        'candy & pearl': 'Deep transparent color over metal, and pearls that shift as the car turns.',
        'carbon & composite': 'Woven carbon, kevlar and technical composites with a real weave.',
        'ceramic & glass': 'Glazed, fired and glassy surfaces - hard, smooth and deep.',
        'chrome & mirror': 'Full mirror finishes. The car reflects the track instead of showing paint.',
        'exotic metal': 'Machined, brushed, forged and anodized metal - titanium to hammered copper.',
        'tactical & cyberpunk': 'Military coatings, stealth surfaces and hard-edged near-future tech.',
        'metallic standard': 'Classic automotive metallic flake. The safe, sponsor-friendly race base.',
        'flames': 'Fire in every style, from traditional hot-rod licks to plasma.',
        'marble & onyx': 'Veined stone - marble, onyx and polished mineral surfaces.',
        'sock hop': '1950s diner chrome, pastels and candy. Jukebox era.',
        'groovy vibes': '1970s swirls, earth tones and psychedelic curves.',
        'iridescent insects': 'Beetle-shell iridescence - color that comes from structure, not pigment.',
        'extreme & experimental': 'The physically impossible ones. Bring these out to be noticed.',
        'prism forge': 'Light split into spectra - prisms, refraction and rainbow edges.',
        'optic lab': 'Lenses, moire, diffraction and optical illusions.',
        'more bases': 'The long tail of the base library - everything outside a themed family.',
        'fractured flames ignite': 'Fire caught at the moment it takes hold, broken into fine shards.',
        'fractured flames topo': 'Flame drawn as contour lines - heat mapped like terrain.',
        'fractured flames dance': 'Flame in motion, shifting as the light angle changes.',
        'gradients': 'Clean color fades across the whole body.',
        'fractured minds': 'Dense neural, circuit and thought-pattern fields. The fine-detail benchmark.',
        'fractured souls': 'Ghostly, bone and spectral surfaces with a haunted edge.',
        'fractured forge': 'Molten metal, quench patterns and forge-marked steel.',
        'fractured opalfire': 'Black opal - a dark ground with fire flashing through it.',
        'paradigm': 'Physically impossible finishes. The showpieces.',
        'colorshoxx': 'Loud, saturated color statements built to grab attention.',
        'neon underground': 'Night-street neon, wet asphalt and glow.',
        'anime inspired': 'Cel-shaded, high-contrast anime styling.',
        'rising sun': 'Japanese motifs - rays, waves, lacquer and sakura.',
        'viva mexico': 'Mexican folk art, talavera tile and papel picado color.',
        'union jacked': 'British racing heritage, flags and mod-era graphics.',
        'forbidden dragon': 'Scales, lacquer and dragon-skin detail.',
        'let freedom ring': 'Stars, stripes and American racing patriotism.',
        'fable': 'Storybook surfaces - soft, magical and illustrated.',
        'chameleon': 'Color that flips completely as your viewing angle changes.',
        'prizm': 'Faceted, crystalline surfaces that catch light in planes.',
        'aurora & chromatic flow': 'Northern-lights curtains and slow-flowing color.',
        'gradient directional': 'Fades with a deliberate direction - nose to tail, roof to sill.',
        'gradient vortex': 'Color spiraling into a center.',
        'chromatic flake': 'Big multi-color flake that sparkles a different color as you move.',
        'color clash': 'Two fighting colors forced together on one body.',
        'gradient extended': 'The full gradient library - every ramp, blend and multi-stop fade.',
        'source pattern plates': 'Hand-authored pattern plates used as raw material.',
        'grunge & fun': 'Beaten up, sprayed, stickered and deliberately rough.',
        'atelier ultra detail': 'Showroom-grade detail that holds up in close-up screenshots.',
        'glass & surface': 'Transparent, frosted and etched glass surfaces.',
        'natural & organic': 'Wood, stone and living material.',
        'spectrum shift': 'Full-spectrum color travel across the body.',
        'light & optics': 'How light behaves - caustics, bloom and refraction.',
        'surface & grain': 'Texture you can almost feel - grain, tooth and micro-relief.',
        'depth & geometry': 'Layered depth and geometric structure under clearcoat.',
        'materials & physics': 'Real material behavior, taken seriously.',
        'atmosphere': 'Fog, haze, cloud and air made visible.',
        'signal': 'Broadcast, glitch and data-transmission artefacts.',
        'fractured wilds': 'Overgrowth, bark, moss and wild botanical structure.',
        'fractured elements': 'Water, ice, earth and air, fractured into fine detail.',
        'fractured cosmos': 'Nebulae, starfields and deep space.',
        'fractured relics': 'Ancient, excavated and weathered artefact surfaces.',
        'wave & flow': 'Liquid motion frozen mid-flow.'
    };
    function _normCategoryKey(title) {
        return String(title || '')
            .toLowerCase()
            .replace(/[^a-z0-9&]+/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }
    function categoryDescription(title) {
        var key = _normCategoryKey(title);
        if (CATEGORY_DESCS[key]) return CATEGORY_DESCS[key];
        // Fall back to the old shape-based guesses for anything added later, so a
        // new family is never blank - but it should get a real line here.
        var s = key;
        if (/foundation/.test(s)) return 'Clean painted surfaces and dependable real-car materials.';
        if (/candy|pearl/.test(s)) return 'Deep color, pearl shift and layered show-car paint.';
        if (/chrome|mirror/.test(s)) return 'Reflective metals, polished surfaces and bright highlights.';
        if (/fract|crack|shatter/.test(s)) return 'Fine broken-surface detail with dramatic spec contrast.';
        if (/carbon|fiber|weave/.test(s)) return 'Fine woven and technical composite materials.';
        if (/weather|rust|dirt|aged/.test(s)) return 'Wear, patina and race-used material character.';
        if (/metal|steel|aluminum|alloy/.test(s)) return 'Machined, brushed and forged metal surfaces.';
        if (/gradient|fade/.test(s)) return 'Color fades and blends across the body.';
        return 'Browse every authored look in this family.';
    }
    function baseCatalogTotal() {
        // bases + specials — the borrow library offers both (iter9)
        var n = 0;
        try { if (typeof BASES !== 'undefined') n += BASES.length; } catch (e) {}
        try { if (typeof MONOLITHICS !== 'undefined') n += MONOLITHICS.length; } catch (e) {}
        return n;
    }
    function selectedBaseColorInfo(source) {
        var raw = String(source || '');
        if (raw.indexOf('base:') === 0) {
            var bInfo = finishInfo(raw.slice(5), 'base');
            return bInfo && bInfo.type === 'base' ? bInfo : null;
        }
        if (raw.indexOf('mono:') === 0) {
            // specials are borrowable now (iter9) — NEXT must recognize them
            var mInfo = finishInfo(raw.slice(5), 'monolithic');
            return mInfo && mInfo.type === 'monolithic' ? mInfo : null;
        }
        return null;
    }
    // [SPB-EASY-SHINE 2026-08-26] The tile PNG is paint(left)|raw-spec(right); the raw spec is
    // owner-mandated DATA for the Pro picker (SPB-SWATCH-TRUTH 2026-08-06) but reads as static
    // to a buyer. Relight the right half in the buyer's browser: paint x spec under a sweeping
    // light (the same composite the audit pages use), so SHINE shows what the finish actually
    // does on a lit panel. ~2.3k px per 48px tile. Never touches the server, caches, or Pro.
    function relightEasyTile(img) {
        try {
            if (!img || img.dataset.spbLit === '1') return;
            var w = img.naturalWidth, h = img.naturalHeight;
            if (!w || !h || w < 8) return;
            var half = Math.floor(w / 2);
            var cv = document.createElement('canvas');
            cv.width = w; cv.height = h;
            var ctx = cv.getContext('2d', { willReadFrequently: true });
            ctx.drawImage(img, 0, 0);
            var paint = ctx.getImageData(0, 0, half, h);
            var spec = ctx.getImageData(half, 0, w - half, h);
            var out = ctx.createImageData(half, h);
            var pd = paint.data, sd = spec.data, od = out.data;
            var skyR = 0.85, skyG = 0.90, skyB = 1.0;
            for (var y = 0; y < h; y++) {
                for (var x = 0; x < half; x++) {
                    var px = Math.min(x, half - 2);          // left half's last col is the seam
                    var sx = Math.max(x, 1);                 // right half's first col is the seam
                    var pi = (y * half + px) * 4;
                    var si = (y * (w - half) + sx) * 4;
                    var oi = (y * half + x) * 4;
                    var m = sd[si] / 255, r = sd[si + 1] / 255, cc = sd[si + 2] / 255;
                    var L = (x / (half - 1)) * 0.6 + (y / (h - 1)) * 0.4;
                    var band = 1 - Math.abs(L - 0.52) * 2; if (band < 0) band = 0;
                    var hi = Math.pow(band, 6 + (1 - r) * 200);
                    var srefl = (0.18 + 0.85 * m + 0.40 * cc) * hi;
                    var basev = 0.55 + 0.18 * (1 - r);
                    var aR = pd[pi] / 255, aG = pd[pi + 1] / 255, aB = pd[pi + 2] / 255;
                    var vR = aR * basev + (0.55 * aR + 0.45 * skyR) * srefl;
                    var vG = aG * basev + (0.55 * aG + 0.45 * skyG) * srefl;
                    var vB = aB * basev + (0.55 * aB + 0.45 * skyB) * srefl;
                    od[oi] = vR > 1 ? 255 : (vR * 255) | 0;
                    od[oi + 1] = vG > 1 ? 255 : (vG * 255) | 0;
                    od[oi + 2] = vB > 1 ? 255 : (vB * 255) | 0;
                    od[oi + 3] = 255;
                }
            }
            ctx.putImageData(out, half, 0);
            img.dataset.spbLit = '1';
            img.src = cv.toDataURL('image/png');
            img.setAttribute('data-swatch-contract', 'paint-left-shine-right');
        } catch (e) { /* tainted canvas / decode issue: raw tile stays, still real data */ }
    }

    function splitThumbHtml(info, extraClass) {
        if (!info) return '';
        // [GAUNTLET C1 2026-08-20] Was 'COLOR REF' / 'SPEC USED' (whole) and
        // 'PAINT' / 'SPEC' (by color). "Spec" is the single most-repeated piece
        // of jargon in Easy Mode and it means nothing to a first-time buyer.
        // [SPB-EASY-SHINE 2026-08-26] one honest buyer-English pair everywhere:
        // PAINT = the finish's own color sample; SHINE = how it behaves under light.
        var leftLabel = 'PAINT';
        var rightLabel = 'SHINE';
        return '<span class="spb-easy-finish-chip ' + esc(extraClass || '') + '" data-swatch-contract="paint-left-spec-right">' +
            '<img alt="' + esc(info.name) + ' real Paint Booth preview: paint on the left, how it shines on the right" loading="lazy" decoding="async" data-src="' + esc(thumbUrl(info)) + '">' +
            '<span class="spb-easy-swatch-labels" aria-hidden="true"><i>' + leftLabel + '</i><i>' + rightLabel + '</i></span>' +
            '<span class="spb-easy-thumb-unavailable" hidden aria-hidden="true">PREVIEW UNAVAILABLE</span></span>';
    }
    function baseColorChoiceHtml(source) {
        var info = selectedBaseColorInfo(source);
        if (!info) {
            return '<button type="button" class="spb-easy-base-choice empty" id="spbEasyChooseBaseColor">' +
                '<b>CHOOSE A PAINT BOOTH BASE COLOR</b><small>Open ' + baseCatalogTotal() + ' real paint + spec thumbnails</small></button>';
        }
        return '<button type="button" class="spb-easy-base-choice" id="spbEasyChooseBaseColor" aria-label="Change Paint Booth base color. Current choice: ' + esc(info.name) + '">' +
            splitThumbHtml(info, 'spb-easy-base-choice-thumb') +
            '<span><b>' + esc(info.name) + '</b><small>REAL PAINT + SPEC THUMBNAIL · CLICK TO CHANGE</small></span></button>';
    }

    // ------------------------------------------------------- curated Top 50
    function buildTopShelf() {
        if (_topShelf) return _topShelf;
        var out = [], seen = {}, seenName = {};
        function add(id, type) {
            var info = finishInfo(id, type);
            if (!info || seen[info.key] || out.length >= TOP_SHELF_SIZE) return;
            // [SPB-EASY-PBN 2026-09-22] one look, one tile: the Foundation cells (f_pearl, f_candy, f_metallic,
            // f_frozen) carry the same names as the classic bases — Top picks showed Candy / Pearl / Metallic /
            // Frozen twice (owner: "that repeating pattern bug is back somehow in EASY MODE").
            var nm = String(info.name || '').trim().toLowerCase();
            if (nm && seenName[nm]) return;
            seen[info.key] = true; if (nm) seenName[nm] = true; out.push(info.key);
        }
        try { if (typeof HERO_BASES !== 'undefined') HERO_BASES.forEach(function (h) { add(h && h.id, 'base'); }); } catch (e) {}
        try {
            if (typeof FEATURED_COLLECTIONS !== 'undefined') {
                ['Best Starting Points', 'Best Show Car', 'Best Chrome Looks', 'Best for Sponsors',
                 'Best Subtle OEM', 'Best Dark Liveries', 'Best Weathered', 'Experimental / Wild']
                    .forEach(function (n) { (FEATURED_COLLECTIONS[n] || []).forEach(add); });
            }
        } catch (e) {}
        try {
            if (typeof BASE_METADATA !== 'undefined') {
                ['premium', 'hero'].forEach(function (tier) {
                    Object.keys(BASE_METADATA).forEach(function (id) {
                        if (BASE_METADATA[id] && BASE_METADATA[id].tier === tier) add(id, 'base');
                    });
                });
            }
        } catch (e) {}
        try {
            if (typeof BASE_GROUPS !== 'undefined') {
                ['Foundation', 'Foundation EFX', 'Candy & Pearl', 'Chrome & Mirror']
                    .forEach(function (g) { (BASE_GROUPS[g] || []).forEach(function (id) { add(id, 'base'); }); });
            }
        } catch (e) {}
        _topShelf = out;
        return out;
    }

    // Full catalog: ALL bases (BASE_GROUPS order) THEN ALL monolithics
    // (SPECIAL_GROUPS order — 59 authored families incl. every FRACTURED
    // group), with catch-all sections so nothing is unreachable.
    function buildCatalogSections() {
        if (_catalogSections) return _catalogSections;
        var sections = [], grouped = {};
        function pushGroupMap(groupsConst, registryType) {
            try {
                if (typeof groupsConst === 'undefined' || !groupsConst) return;
                Object.keys(groupsConst).forEach(function (title) {
                    var keys = (groupsConst[title] || []).map(function (id) { return finishKey(registryType, id); })
                        .filter(function (key) { return !!finishInfo(key); });
                    keys.forEach(function (key) { grouped[key] = true; });
                    if (keys.length) sections.push({ title: title, ids: keys });
                });
            } catch (e) {}
        }
        try { pushGroupMap(typeof BASE_GROUPS !== 'undefined' ? BASE_GROUPS : null, 'base'); } catch (e) {}
        try {
            if (typeof BASES !== 'undefined') {
                var restB = BASES.filter(function (b) { return b && b.id && !grouped[finishKey('base', b.id)]; })
                    .map(function (b) { return finishKey('base', b.id); });
                if (restB.length) sections.push({ title: 'More Bases', ids: restB });
            }
        } catch (e) {}
        try { pushGroupMap(typeof SPECIAL_GROUPS !== 'undefined' ? SPECIAL_GROUPS : null, 'monolithic'); } catch (e) {}
        try {
            if (typeof MONOLITHICS !== 'undefined') {
                var restM = MONOLITHICS.filter(function (m) { return m && m.id && !grouped[finishKey('monolithic', m.id)]; })
                    .map(function (m) { return finishKey('monolithic', m.id); });
                if (restM.length) sections.push({ title: 'More Specials', ids: restM });
            }
        } catch (e) {}
        _catalogSections = sections;
        return sections;
    }
    // [SPB-EASY-2026-08-19] "2834" reads as a part number; "2,834" reads as a
    // catalog. Used anywhere a buyer sees the catalog size.
    function nfmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
    function catalogTotal() {
        var n = 0;
        try { if (typeof BASES !== 'undefined') n += BASES.length; } catch (e) {}
        try { if (typeof MONOLITHICS !== 'undefined') n += MONOLITHICS.length; } catch (e) {}
        return n;
    }

    // ------------------------------------------------------------- DOM build
    function buildRoot() {
        if (_built) return;
        var root = document.createElement('div');
        root.id = 'spbEasyRoot';
        root.innerHTML = '' +
            '<div class="spb-easy-topbar">' +
            '  <div class="spb-easy-brand">SHOKKER PAINT BOOTH <b>· EASY MODE</b></div>' +
            '  <div class="spb-easy-tagline">Same paint shop as Pro — it just walks you through it.</div>' +
            '  <div class="spb-easy-history">' +
            '    <button type="button" id="spbEasyUndo" class="spb-easy-histbtn" disabled title="Undo (Ctrl+Z)">↶ UNDO<small id="spbEasyUndoWhat"></small></button>' +
            '    <button type="button" id="spbEasyRedo" class="spb-easy-histbtn" disabled title="Redo (Ctrl+Y)">↷ REDO</button>' +
            '    <button type="button" id="spbEasyStartOver" class="spb-easy-histbtn spb-easy-startover" title="Clear every finish and color you have picked for this car">✕ START OVER</button>' +
            '    <span class="spb-easy-saved" id="spbEasySavedTag" hidden>✓ Saved</span>' +
            '  </div>' +
            '  <button type="button" class="spb-easy-probtn" id="spbEasyProBtn" title="Open the full Paint Booth editor — this paint stays open">PRO MODE →</button>' +
            '</div>' +
            '<div class="spb-easy-main">' +
            '  <div class="spb-easy-stage" id="spbEasyStage">' +
            '    <div class="spb-easy-painting-badge"><span class="spb-easy-painting-dot"></span> Updating live proof…</div>' +
            '    <div class="spb-easy-proof" id="spbEasyProof">' +
            '      <div class="spb-easy-stage-side" id="spbEasyStageSide">' +
            '        <b>ON THE BENCH</b>' +
            '        <div class="spb-easy-side-row"><i>PAINT</i><span id="spbEasySideFile">\u2014</span></div>' +
            '        <div class="spb-easy-side-row"><i>CAR</i><span id="spbEasySideCar">pick below</span></div>' +
            '        <div class="spb-easy-side-row"><i>SHEET</i><span id="spbEasySideSheet">2048 \u00d7 2048</span></div>' +
            '        <small class="spb-easy-side-tip">\u2315 INSPECT on either view zooms the real pixels \u2014 scroll to zoom, drag to pan.</small>' +
            '        <small class="spb-easy-side-tip">The 4 small squares on the right are the shine data iRacing reads \u2014 metal \u00b7 roughness \u00b7 clearcoat.</small>' +
            '      </div>' +
            '      <div class="spb-easy-proof-main">' +
            '        <div class="spb-easy-proof-card spb-easy-source-card"><b>SOURCE</b><span>Your untouched paint</span><button type="button" class="spb-easy-inspect-btn" data-inspect="source" title="Zoom in on the real pixels (scroll to zoom, drag to pan)">⌕ INSPECT</button><div class="spb-easy-proof-media"><canvas id="spbEasySourceCanvas"></canvas><canvas id="spbEasyPickCanvas" tabindex="-1" role="button" aria-label="Choose a color on the source paint. Click a point, or press Enter to sample the center." hidden></canvas><canvas id="spbEasyPickFlash" aria-hidden="true" style="position:absolute; inset:0; width:100%; height:100%; pointer-events:none; opacity:0; transition:opacity 0.45s;" hidden></canvas><img id="spbEasyMapOverlay" alt="Where each material lands" style="position:absolute; inset:0; width:100%; height:100%; pointer-events:none;" hidden></div></div>' +
            '        <div class="spb-easy-proof-card spb-easy-live-card"><b id="spbEasyLiveTitle">LIVE PREVIEW</b><span id="spbEasyLiveSubtitle">What your paint becomes</span><button type="button" class="spb-easy-inspect-btn" data-inspect="live" title="Zoom in and wipe between before and after">⌕ INSPECT</button><div class="spb-easy-proof-media"><canvas id="spbEasyLiveCanvas"></canvas><img id="spbEasyPreviewImg" alt="Live material preview" hidden><em class="spb-easy-material-sim-note" id="spbEasyMaterialSimNote" hidden>REAL MATERIAL · NEUTRAL LIGHT</em></div></div>' +
            '      </div>' +
            '      <button type="button" class="spb-easy-specpeek" id="spbEasySpecPeek" aria-expanded="false" aria-controls="spbEasyChannelStrip" title="Show the four live spec-map channels iRacing actually reads. Nothing on your car changes - this is a look under the hood.">🔬 SHOW ME THE SPEC MAP</button>' +
            '      <div class="spb-easy-channel-strip" id="spbEasyChannelStrip" aria-label="Live iRacing spec map channels" hidden>' +
            '        <div class="spb-easy-channel"><b>COMBINED SPEC</b><i>everything iRacing reads</i><canvas id="spbEasySpecAll" width="256" height="256"></canvas></div>' +
            '        <div class="spb-easy-channel"><b>RED · METAL</b><i>how metallic · brighter = more</i><canvas id="spbEasySpecR" width="256" height="256"></canvas></div>' +
            '        <div class="spb-easy-channel"><b>GREEN · ROUGH</b><i>how sharp the shine · darker = mirror</i><canvas id="spbEasySpecG" width="256" height="256"></canvas></div>' +
            '        <div class="spb-easy-channel"><b>BLUE · COAT</b><i>clearcoat depth · darker = glassier</i><canvas id="spbEasySpecB" width="256" height="256"></canvas></div>' +
            '      </div>' +
            '    </div>' +
            '    <div class="spb-easy-loupe" id="spbEasyLoupe" hidden><canvas class="spb-easy-loupe-zoom" id="spbEasyLoupeZoom" width="132" height="132"></canvas><span class="spb-easy-loupe-dot" id="spbEasyLoupeDot"></span><span id="spbEasyLoupeHex"></span></div>' +
            '    <div class="spb-easy-pick-banner" id="spbEasyPickBanner" hidden>🎯 Click the color on EITHER picture</div>' +
            '    <div class="spb-easy-empty" id="spbEasyEmpty" hidden>' +
            '      <div class="spb-easy-empty-icon">🏎️</div>' +
            '      <div class="spb-easy-empty-title">STEP 1 · Load your car</div>' +
            '      <div class="spb-easy-empty-sub">Open the paint file for your iRacing car — or start on a blank canvas just to play.</div>' +
            '      <div class="spb-easy-empty-actions">' +
            '        <button type="button" class="spb-easy-open-paint" id="spbEasyOpenPaint">📂 Open your car’s paint file</button>' +
            '        <button type="button" class="spb-easy-blank-canvas" id="spbEasyBlankCanvas">🎨 Start with a blank canvas</button>' +
            '      </div>' +
            '    </div>' +
            '    <div class="spb-easy-stage-hint" id="spbEasyStageHint" hidden></div>' +
            '  </div>' +
            '  <div class="spb-easy-rail" id="spbEasyRail"></div>' +
            '  <button type="button" class="spb-easy-railtoggle" id="spbEasyRailToggle" title="Fold the controls away and give the car the whole window">\u25c0 BIGGER PICTURE</button>' +
            '</div>' +
            '<div class="spb-easy-gloss-backdrop" id="spbEasyGlossBackdrop" hidden>' +
            '  <div class="spb-easy-gloss">' +
            '    <div class="spb-easy-gloss-head"><b>WHAT THE WORDS MEAN</b>' +
            '      <button type="button" id="spbEasyGlossClose">\u2715 CLOSE</button></div>' +
            '    <dl class="spb-easy-gloss-body" id="spbEasyGlossBody"></dl>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-tour-backdrop" id="spbEasyTourBackdrop" hidden>' +
            '  <div class="spb-easy-tour-spot" id="spbEasyTourSpot"></div>' +
            '  <div class="spb-easy-tour-card" id="spbEasyTourCard">' +
            '    <div class="spb-easy-tour-head"><span id="spbEasyTourNum"></span>' +
            '      <button type="button" id="spbEasyTourClose" aria-label="Close the tour">\u2715</button></div>' +
            '    <b id="spbEasyTourTitle"></b>' +
            '    <p id="spbEasyTourBody"></p>' +
            '    <div class="spb-easy-tour-actions">' +
            '      <button type="button" id="spbEasyTourPrev">\u2190 BACK</button>' +
            '      <button type="button" id="spbEasyTourPro" hidden>OPEN PRO MODE</button>' +
            '      <button type="button" id="spbEasyTourNext">NEXT \u2192</button>' +
            '    </div>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-ask-backdrop" id="spbEasyAskBackdrop" hidden>' +
            '  <div class="spb-easy-ask">' +
            '    <div class="spb-easy-ask-title" id="spbEasyAskTitle"></div>' +
            '    <div class="spb-easy-ask-body" id="spbEasyAskBody"></div>' +
            '    <input type="text" class="spb-easy-ask-input" id="spbEasyAskInput" hidden autocomplete="off" spellcheck="false">' +
            '    <div class="spb-easy-ask-actions">' +
            '      <button type="button" id="spbEasyAskNo">CANCEL</button>' +
            '      <button type="button" id="spbEasyAskYes">OK</button>' +
            '    </div>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-ow-backdrop" id="spbEasyOverwriteBackdrop" hidden>' +
            '  <div class="spb-easy-ow">' +
            '    <div class="spb-easy-ow-head"><b>\u26a0 THIS CAR ALREADY HAS A PAINT</b></div>' +
            '    <div class="spb-easy-ow-body" id="spbEasyOverwriteBody"></div>' +
            '    <div class="spb-easy-ow-actions">' +
            '      <button type="button" id="spbEasyOverwriteCancel">KEEP WHAT I HAVE</button>' +
            '      <button type="button" id="spbEasyOverwriteGo">REPLACE IT \u2192</button>' +
            '    </div>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-share-backdrop" id="spbEasyShareBackdrop" hidden>' +
            '  <div class="spb-easy-share">' +
            '    <div class="spb-easy-share-head"><b>SHARE THIS LOOK</b>' +
            '      <button type="button" id="spbEasyShareClose">\u2715 CLOSE</button></div>' +
            '    <label>SEND THIS CODE<textarea id="spbEasyShareOut" rows="4" spellcheck="false"></textarea></label>' +
            '    <button type="button" id="spbEasyShareCopy">\u29c9 COPY THE CODE</button>' +
            '    <label>GOT A CODE FROM SOMEONE?<textarea id="spbEasyShareIn" rows="3" spellcheck="false" placeholder="Paste a SPB1:... code here"></textarea></label>' +
            '    <button type="button" id="spbEasyShareLoad">\u2193 PUT IT ON MY CAR</button>' +
            '    <div class="spb-easy-share-msg" id="spbEasyShareMsg" aria-live="polite"></div>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-compare-backdrop" id="spbEasyCompareBackdrop" hidden>' +
            '  <div class="spb-easy-compare">' +
            '    <div class="spb-easy-compare-head">' +
            '      <b>COMPARE YOUR LOOKS</b>' +
            '      <span>Real renders, side by side. Pick the one you want and it goes straight back on the car.</span>' +
            '      <span class="spb-easy-compare-spacer"></span>' +
            '      <button type="button" id="spbEasyCompareClear">CLEAR ALL</button>' +
            '      <button type="button" id="spbEasyCompareClose">\u2715 CLOSE</button>' +
            '    </div>' +
            '    <div class="spb-easy-compare-grid" id="spbEasyCompareGrid"></div>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-inspect-backdrop" id="spbEasyInspectBackdrop" hidden>' +
            '  <div class="spb-easy-inspect">' +
            '    <div class="spb-easy-inspect-head">' +
            '      <b id="spbEasyInspectTitle">INSPECT</b>' +
            '      <span id="spbEasyInspectHint">Scroll = zoom · drag = pan · hold B = before</span>' +
            '      <span class="spb-easy-inspect-spacer"></span>' +
            '      <button type="button" id="spbEasyInspectFit">FIT</button>' +
            '      <button type="button" id="spbEasyInspect1x">1:1</button>' +
            '      <button type="button" id="spbEasyInspectClose">✕ CLOSE</button>' +
            '    </div>' +
            '    <div class="spb-easy-inspect-stage" id="spbEasyInspectStage">' +
            '      <canvas id="spbEasyInspectCanvas"></canvas>' +
            '      <div class="spb-easy-inspect-zoom" id="spbEasyInspectZoom">100%</div>' +
            '    </div>' +
            '    <div class="spb-easy-inspect-foot" id="spbEasyInspectFoot">' +
            '      <label>BEFORE <input type="range" id="spbEasyWipe" min="0" max="100" value="100"> AFTER</label>' +
            '      <button type="button" id="spbEasyWipeSwap">SHOW BEFORE ONLY</button>' +
            '    </div>' +
            '  </div>' +
            '</div>' +
            '<div class="spb-easy-result-backdrop" id="spbEasyResultBackdrop" hidden>' +
            '  <div class="spb-easy-result" id="spbEasyResult">' +
            '    <div class="spb-easy-result-icon" id="spbEasyResultIcon">🏁</div>' +
            '    <div class="spb-easy-result-title" id="spbEasyResultTitle"></div>' +
            '    <div class="spb-easy-result-body" id="spbEasyResultBody"></div>' +
            '    <div class="spb-easy-result-actions">' +
            '      <button type="button" class="spb-easy-result-retry" id="spbEasyResultRetry" hidden>↺ TRY THE SAVE AGAIN</button>' +
            '      <button type="button" class="spb-easy-result-folder" id="spbEasyResultFolder" hidden>\u{1F4C2} OPEN THE FOLDER</button>' +
            '      <button type="button" class="spb-easy-result-secondary" id="spbEasyResultSecondary">Open Pro Mode</button>' +
            '      <button type="button" class="spb-easy-result-done" id="spbEasyResultDone">🎨 Keep painting</button>' +
            '    </div>' +
            '  </div>' +
            '</div>';
        document.body.appendChild(root);
        root.setAttribute('role', 'region');
        root.setAttribute('aria-label', 'Shokker Paint Booth Easy Mode');
        root.tabIndex = -1;

        els.root = root;
        els.stage = $('spbEasyStage');
        els.previewImg = $('spbEasyPreviewImg');
        els.sourceCanvas = $('spbEasySourceCanvas');
        els.liveCanvas = $('spbEasyLiveCanvas');
        els.pickCanvas = $('spbEasyPickCanvas');
        els.pickFlash = $('spbEasyPickFlash');
        els.channelStrip = $('spbEasyChannelStrip');
        // [SPB-EASY-2026-08-19] The four raw spec channels (COMBINED / RED-METAL /
        // GREEN-ROUGH / BLUE-COAT) were a PERMANENT readout of iRacing internals
        // for a buyer who does not yet know what a spec map is - and in the browse
        // layout they also ate the car preview. Demoted to a one-click reveal,
        // remembered per buyer. NOT removed: it is one of the best things this app
        // can show off, so it gets a button that sells it.
        (function wireSpecPeek() {
            var btn = $('spbEasySpecPeek'), strip = els.channelStrip;
            if (!btn || !strip || btn._spbWired) return;
            btn._spbWired = true;
            function apply(on) {
                strip.hidden = !on;
                btn.setAttribute('aria-expanded', on ? 'true' : 'false');
                btn.classList.toggle('on', !!on);
                btn.textContent = on ? '🔬 HIDE THE SPEC MAP' : '🔬 SHOW ME THE SPEC MAP';
            }
            // [SPB-EASY-STAGE 2026-08-26] owner: channels visible AT ALL TIMES by default
            // (the 2x2 side grid no longer eats the car panes). Hiding is still remembered.
            apply(lsGet(LS_SPECPEEK) !== '0');
            btn.addEventListener('click', function () {
                var turningOn = strip.hidden;
                lsSet(LS_SPECPEEK, turningOn ? '1' : '0');
                apply(turningOn);
            });
        })();
        els.pickBanner = $('spbEasyPickBanner');
        els.empty = $('spbEasyEmpty');
        els.stageHint = $('spbEasyStageHint');
        els.rail = $('spbEasyRail');
        els.resultBackdrop = $('spbEasyResultBackdrop');
        els.result = $('spbEasyResult');
        els.resultIcon = $('spbEasyResultIcon');
        els.resultTitle = $('spbEasyResultTitle');
        els.resultBody = $('spbEasyResultBody');

        $('spbEasyProBtn').addEventListener('click', function () { exit(); });
        $('spbEasyOpenPaint').addEventListener('click', openPaint);
        $('spbEasyBlankCanvas').addEventListener('click', startBlankCanvas);
        // [2026-08-08 E1/E2/E3] Safety controls. Undo/redo drive Pro's zone
        // history (the same stack undoPush already writes to) and then force
        // Easy to re-read the world: zone list, rail, preview.
        var _undoBtn = $('spbEasyUndo');
        if (_undoBtn) _undoBtn.addEventListener('click', function () { easyUndo(); });
        var _redoBtn = $('spbEasyRedo');
        if (_redoBtn) _redoBtn.addEventListener('click', function () { easyRedo(); });
        var _startOver = $('spbEasyStartOver');
        if (_startOver) _startOver.addEventListener('click', easyStartOver);
        var _retry = $('spbEasyResultRetry');
        if (_retry) _retry.addEventListener('click', function () { hideResult(); onSaveClick(); });
        wireInspector();
        wireCompare();
        wireShare();
        wireOverwrite();
        wireTour();
        wireGlossary();
        $('spbEasyResultDone').addEventListener('click', hideResult);
        $('spbEasyResultSecondary').addEventListener('click', function () {
            hideResult(); exit();
            // Training Wheels bridge (2026-07-18): a completed whole-car save lands
            // the user in the editor with quest q-render armed (js/spb-quests.js).
            if (window.spbQuests && typeof window.spbQuests.notifyFirstWin === 'function') window.spbQuests.notifyFirstWin();
        });
        els.pickCanvas.addEventListener('click', onPickCanvasClick);
        els.pickCanvas.addEventListener('keydown', function (event) {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            var rect = els.pickCanvas.getBoundingClientRect();
            onPickCanvasClick({ clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 });
        });
        // Color loupe: shows the color under the cursor while picking, so the
        // user knows exactly what they're about to grab.
        els.loupe = $('spbEasyLoupe');
        els.loupeDot = $('spbEasyLoupeDot');
        els.loupeHex = $('spbEasyLoupeHex');
        els.loupeZoom = $('spbEasyLoupeZoom');
        els.pickCanvas.addEventListener('mousemove', onPickCanvasMove);
        els.pickCanvas.addEventListener('mouseleave', function () { if (els.loupe) els.loupe.hidden = true; });

        installPreviewMirror();
        ensureIracingCars();
        _built = true;
    }

    function isolateProAccessibility() {
        if (_proAccessibilityState.length || !els.root) return;
        Array.prototype.forEach.call(document.body.children, function (element) {
            if (element === els.root || /^(SCRIPT|STYLE|LINK)$/.test(element.tagName) || element.id === 'ariaLiveAnnouncer' || element.id === 'ariaAlertAnnouncer') return;
            // Keep modal/file-picker siblings available: Easy Mode deliberately
            // opens some of them. Only isolate the permanent Pro workspace.
            if (!element.matches('.skip-link, #spbUpdateBanner, nav.header, #spbTopToolbar, main.main-container')) return;
            _proAccessibilityState.push({
                element: element,
                ariaHidden: element.getAttribute('aria-hidden'),
                hadInert: element.hasAttribute('inert'),
                inertValue: !!element.inert
            });
            element.setAttribute('aria-hidden', 'true');
            element.setAttribute('inert', '');
            try { element.inert = true; } catch (e) {}
        });
    }

    function restoreProAccessibility() {
        _proAccessibilityState.forEach(function (saved) {
            var element = saved.element;
            if (!element || !element.isConnected) return;
            if (saved.ariaHidden == null) element.removeAttribute('aria-hidden');
            else element.setAttribute('aria-hidden', saved.ariaHidden);
            if (saved.hadInert) element.setAttribute('inert', '');
            else element.removeAttribute('inert');
            try { element.inert = saved.inertValue; } catch (e) {}
        });
        _proAccessibilityState = [];
    }

    // Geometry-based lazy thumbnail loader. Deliberately NOT an
    // IntersectionObserver: IO callbacks depend on the rendering lifecycle
    // and never fire in occluded/embedded webviews (verified live 2026-07-16
    // — 2,187 observed imgs, zero callbacks). getBoundingClientRect math
    // works everywhere. Rows are in DOM order, so we stop early past the
    // bottom edge; each pass only touches still-pending imgs.
    var _lazyTimer = null;
    var _lazyContainers = [];
    function lazyThumbPass(onlyContainer) {
        _lazyContainers = _lazyContainers.filter(function (c) { return c && c.isConnected; });
        var containers = onlyContainer ? [onlyContainer] : _lazyContainers.slice();
        containers.forEach(function (c) {
            if (!c || !c.isConnected) return;
            var crect = c.getBoundingClientRect();
            var topEdge = crect.top - 600, bottomEdge = crect.bottom + 900;
            var pending = c.querySelectorAll('img[data-src]:not([src]):not([data-thumb-failed])');
            for (var i = 0; i < pending.length; i++) {
                var img = pending[i];
                // Collapsed <details> children report a 0,0,0,0 rectangle.
                // Treating that as visible launched ~2,400 hidden real-swatch
                // requests and starved the category the painter actually opened.
                var ownerDetails = img.closest ? img.closest('details') : null;
                // [GAUNTLET A1 2026-08-20] ...except the summary's own preview
                // chips, which are visible precisely BECAUSE the family is closed.
                if (ownerDetails && !ownerDetails.open && img.getAttribute('data-peek') !== '1') continue;
                var r = img.getBoundingClientRect();
                if (!r.width || !r.height) continue;
                if (r.top > bottomEdge) break;          // DOM order — rest are lower
                if (r.bottom < topEdge) continue;
                if (!img._spbEasyThumbErrorWired) {
                    img._spbEasyThumbErrorWired = true;
                    img.addEventListener('load', function () {
                        this.removeAttribute('data-thumb-failed');
                        this.removeAttribute('data-thumb-retry');
                        var loadedChip = this.closest ? this.closest('.spb-easy-finish-chip') : null;
                        var loadedUnavailable = loadedChip ? loadedChip.querySelector('.spb-easy-thumb-unavailable') : null;
                        if (loadedUnavailable) loadedUnavailable.hidden = true;
                        relightEasyTile(this);   // [SPB-EASY-SHINE] buyer sees the finish LIT, not raw spec data
                    });
                    img.addEventListener('error', function () {
                        var failedImage = this;
                        var retry = parseInt(failedImage.getAttribute('data-thumb-retry') || '0', 10) || 0;
                        // Full material rendering and a cold swatch can overlap.
                        // Retry the exact real Paint Booth thumbnail; never swap
                        // in a synthetic approximation just to fill the tile.
                        if (retry < 2 && failedImage.isConnected) {
                            retry += 1;
                            failedImage.setAttribute('data-thumb-retry', String(retry));
                            failedImage.removeAttribute('src');
                            setTimeout(function () {
                                if (!failedImage.isConnected) return;
                                var source = failedImage.getAttribute('data-src') || '';
                                failedImage.src = source + (source.indexOf('?') >= 0 ? '&' : '?') + 'real_retry=' + retry;
                            }, 450 * retry);
                            return;
                        }
                        this.setAttribute('data-thumb-failed', '1');
                        this.removeAttribute('src');
                        var chip = this.closest ? this.closest('.spb-easy-finish-chip') : null;
                        var unavailable = chip ? chip.querySelector('.spb-easy-thumb-unavailable') : null;
                        if (unavailable) unavailable.hidden = false;
                    });
                }
                img.src = img.getAttribute('data-src');
            }
        });
    }
    var _lazyWindowWired = false;
    function lazyThumbPassSoon() {
        if (_lazyTimer) return;
        _lazyTimer = setTimeout(function () { _lazyTimer = null; lazyThumbPass(); }, 120);
    }
    function armLazyThumbs(container) {
        if (!container) return;
        if (_lazyContainers.indexOf(container) === -1) _lazyContainers.push(container);
        if (!container._spbLazyWired) {
            container._spbLazyWired = true;
            container.addEventListener('scroll', lazyThumbPassSoon, { passive: true });
        }
        // Collapsed visual families have zero geometry, so opening one must
        // explicitly wake the loader. Waiting for a scroll left a freshly
        // opened PAINT | SPEC family blank in embedded browsers.
        Array.prototype.forEach.call(container.querySelectorAll('details'), function (details) {
            if (details._spbLazyToggleWired) return;
            details._spbLazyToggleWired = true;
            details.addEventListener('toggle', function () {
                if (details.open) {
                    // A cold render may have failed while the category was
                    // previously visible. Reopening is an explicit retry of
                    // the same real Paint Booth assets, never a fake fallback.
                    Array.prototype.forEach.call(details.querySelectorAll('img[data-thumb-failed]'), function (img) {
                        img.removeAttribute('data-thumb-failed');
                        img.removeAttribute('data-thumb-retry');
                    });
                    lazyThumbPassSoon();
                }
            });
        });
        // [SPB-EASY-2026-08-19] MEASURED after the browse layout landed: 50 tiles
        // on screen, 13 with a src, 37 blank, 0 HTTP errors, swatches serving in
        // 4ms. The loader was never broken - it just only ever ran ONCE, before
        // the grid had its final size, so `if (r.top > bottomEdge) break;` cut
        // the pass short; and because the catalog no longer needs scrolling to
        // see 27 finishes, the scroll handler that used to rescue this never
        // fired again. Two fixes, both about WHEN the pass runs:
        //   1. a ResizeObserver, so the pass re-runs the moment the container
        //      settles into its real size (layout switch, window resize, the
        //      mix panel opening and shrinking the catalog);
        //   2. a few delayed passes, because a container that never changes size
        //      and never scrolls would otherwise get exactly one shot at it.
        if (!container._spbLazyResizeWired && typeof ResizeObserver === 'function') {
            container._spbLazyResizeWired = true;
            try {
                new ResizeObserver(function () { lazyThumbPassSoon(); }).observe(container);
            } catch (e) { /* older shells fall back to the timed passes below */ }
        }
        if (!_lazyWindowWired) {
            _lazyWindowWired = true;
            window.addEventListener('resize', lazyThumbPassSoon, { passive: true });
        }
        lazyThumbPass(container);
        [60, 250, 700, 1600].forEach(function (ms) {
            setTimeout(function () { if (container.isConnected) lazyThumbPass(container); }, ms);
        });
    }

    // ------------------------------------------------------------ rail views
    function renderRail() {
        if (!_built) return;
        // Owner 2026-07-18: Sculpt My Paint is the automatic brain of Easy Mode.
        // Whole Car and By Color remain; the preserved control room is not linked here.
        if (state.view === 'sculpt' && window.spbEasySculpt && typeof window.spbEasySculpt.mount === 'function') {
            window.spbEasySculpt.mount({
                back: function () { state.view = 'whole'; renderRail(); },
                exit: exit
            });
        } else {
            if (window.spbEasySculpt && typeof window.spbEasySculpt.unmount === 'function') window.spbEasySculpt.unmount();
            if (state.view === 'auto' && window.spbEasyAuto) window.spbEasyAuto.renderRail();   // [SPB-EASY-AUTO 2026-09-19] your car, built for you
            else if (state.view === 'fork') renderForkRail();
            else if (state.view === 'whole') renderWholeRail();
            else renderByColorRail();
        }
        // [SPB-EASY-2026-08-19] The browse layout is a LAYOUT, not a new view: in
        // the catalog view the window restacks to car-on-top / catalog-below at
        // full width, so the finish list gets the whole screen instead of a 367px
        // porthole inside a 470px rail. MEASURED before: 2 of 2,834 finishes
        // visible at 1920x1080. BY COLOR keeps the side rail - it needs the car
        // big enough to click colors on.
        try { document.body.classList.toggle('spb-easy-browse', _active && state.view === 'whole'); } catch (e) {}
        persistState();
        syncStage();
    }

    function railHeader(title, sub, showBack) {
        return '' +
            '<div class="spb-easy-rail-head">' +
            (showBack ? '<button type="button" class="spb-easy-back" id="spbEasyBackBtn" aria-label="Back to Easy Mode choices" title="Back to Easy Mode choices">←</button>' : '') +
            '<div class="spb-easy-step-label spb-easy-head-label">' + title +
            (sub ? '<small>' + sub + '</small>' : '') + '</div>' +
            '</div>';
    }

    // [SPB-EASY-READY 2026-08-26] Everything SAVE needs, as visible rows. The blocked button
    // names ONE problem; this names them ALL, and every unmet row is a button that opens its fix.
    function saveReadinessRows() {
        var rows = [];
        var pl = paintLoaded();
        var pName = '';
        try { pName = String((typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || '').replace(/\\/g, '/').split('/').pop(); } catch (e) {}
        rows.push({ ok: !!pl, act: 'paint', label: 'Your paint',
            detail: pl ? (pName || 'loaded') : 'Load your TGA / PNG / PSD' });
        var idEl = $('iracingId');
        var idVal = idEl ? String(idEl.value || '').trim() : '';
        rows.push({ ok: idIsValid(idVal), act: 'id', label: 'Your customer ID',
            detail: idIsValid(idVal) ? idVal : 'The number iRacing knows you by' });
        var car = currentCarRecord();
        rows.push({ ok: !!car, act: 'car', label: 'Your iRacing car',
            detail: car ? car.name : 'Pick which car this goes on' });
        if (state.view === 'bycolor') {
            var pairs = easyColorZones();
            var unfinished = pairs.filter(function (p2) { return !(p2.z.base || p2.z.finish); }).length;
            rows.push({ ok: pairs.length > 0 && unfinished === 0, act: 'finish', label: 'Every color has a finish',
                detail: pairs.length === 0 ? 'Click a color on your car above' :
                        (unfinished ? unfinished + ' still need one' : pairs.length + ' colors done') });
        } else {
            var has = false;
            try { has = !!detectWholeApplied(); } catch (e) {}
            if (!has) { try { has = state.wholeStack && state.wholeStack.length > 0; } catch (e) {} }
            rows.push({ ok: has, act: 'finish', label: 'A finish is picked',
                detail: has ? 'on your car' : 'Tap any card below' });
        }
        return rows;
    }
    function syncReadinessChecklist(blocked) {
        var box = $('spbEasyReadiness');
        if (!box) return;
        if (!blocked) { box.hidden = true; return; }
        var rows = saveReadinessRows();
        box.hidden = false;
        box.innerHTML = '<div class="spb-easy-ready-head">READY TO RACE?</div>' + rows.map(function (r) {
            return '<button type="button" class="spb-easy-ready-row' + (r.ok ? ' ok' : '') + '" data-ready-act="' + r.act + '"' +
                (r.ok ? ' tabindex="-1"' : '') + '>' +
                '<i>' + (r.ok ? '\u2713' : '\u2192') + '</i><b>' + esc(r.label) + '</b><small>' + esc(r.detail) + '</small></button>';
        }).join('');
        if (!box._spbWired) {
            box._spbWired = true;
            // destination can change outside Easy's own handlers (Pro-side input, tools):
            // keep the checklist truthful either way
            var od = $('outputDir');
            if (od && !od._spbReadyWired) {
                od._spbReadyWired = true;
                od.addEventListener('change', function () { try { refreshSaveEls(); } catch (e) {} });
            }
            box.addEventListener('click', function (ev) {
                var btn = ev.target && ev.target.closest ? ev.target.closest('[data-ready-act]') : null;
                if (!btn || btn.classList.contains('ok')) return;
                var act = btn.getAttribute('data-ready-act');
                var drawer = $('spbEasySendDrawer');
                if (act === 'paint') {
                    if (typeof window.openFilePicker === 'function') {
                        window.openFilePicker({
                            title: 'Select Your Car Paint (TGA / PNG / JPEG / PSD)', mode: 'file',
                            onSelect: function (path) { if (typeof window.loadPaintByPath === 'function') window.loadPaintByPath(path); }
                        });
                    }
                } else if (act === 'id') {
                    if (drawer) drawer.open = true;
                    var ii = $('spbEasyIdInput');
                    if (ii) { ii.focus(); try { ii.select(); } catch (e) {} }
                } else if (act === 'car') {
                    if (drawer) drawer.open = true;
                    var cs = $('spbEasyCarSearch');
                    if (cs) cs.focus();
                    else { var sel = $('spbEasyCarSelect'); if (sel) sel.focus(); }
                } else if (act === 'finish') {
                    var se = $('spbEasySearch');
                    if (se) { se.focus(); se.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
                }
            });
        }
    }

    function saveBlockReason() {
        if (!paintLoaded()) return 'LOAD A PAINT FIRST';
        var idEl = $('iracingId');
        if (!idIsValid(idEl ? idEl.value : '')) return 'ENTER YOUR CUSTOMER ID';
        if (!currentCarRecord()) return 'CHOOSE AN iRACING CAR';
        if (state.view === 'bycolor') {
            // [2026-08-06 easy-loop] was 'FINISH OR REMOVE THE UNFINISHED COLOR'
            // — buyers read that as a riddle. Say the actual next action.
            // [GAUNTLET E2 2026-08-20] ...and say HOW MANY. After FIND MY COLORS
            // FOR ME there can be five, and "your picked color" (singular) hides
            // that the shortcut just took on five obligations.
            var unfinished = easyColorZones().filter(function (p) { return !(p.z.base || p.z.finish); }).length;
            if (unfinished === 1) return 'CHOOSE A FINISH FOR YOUR PICKED COLOR \u2191';
            if (unfinished > 1) return unfinished + ' COLORS STILL NEED A FINISH \u2191';
        }
        var hasWork = detectWholeApplied() ||
            easyColorZones().some(function (p) { return p.z.base || p.z.finish; }) ||
            (Array.isArray(zones) && zones.some(function (z) { return z && (z.base || z.finish || (z.pattern && z.pattern !== 'none')); }));
        return hasWork ? '' : 'PICK A FINISH FIRST';
    }

    // [SPB-EASY-2026-08-19] The collapsed destination drawer has to state the
    // answer it is hiding, or collapsing it just hides a decision the buyer never
    // made. Re-stamped on every car / number change.
    function syncDestSummary() {
        var el = $('spbEasyDestSummary');
        if (!el) return;
        var car = currentCarRecord();
        el.textContent = (car ? friendlyCarName(car.name) : 'Choose your car') + ' · ' +
            (customNumberIsOn() ? 'your number' : 'iRacing’s number');
    }

    function saveBlockHtml(diceTitle) {
        var car = currentCarRecord();
        // [GAUNTLET B1 2026-08-20] Apply the detection BEFORE reading the mode.
        // Caught by testing both filenames: the explanatory note was rendered
        // from detectNumberModeFromPaint() while the buttons were rendered from
        // customNumberIsOn(), and the two disagreed for `car_<id>.tga` - the note
        // said "iRacing will add one" over a button set to "my paint has it".
        // A wrong default that explains itself confidently is worse than none.
        try { applyDetectedNumberMode(); } catch (e) {}
        var custom = customNumberIsOn();
        // [SPB-EASY-2026-08-19] MEASURED before this change: the destination config
        // (car search + a 179-entry dropdown + recent cars + ALSO SAVE TO + the
        // car_num/car question + its 115-word explainer + the ID row) sat
        // permanently on screen WHILE the buyer was still shopping for a finish -
        // 8 of the ~25 controls competing with the one job of that screen.
        // Demoted, NOT removed (owner: "we can't just remove all the cool
        // features"): one drawer, labelled with the answer it already has, so the
        // buyer sees where it is going without being asked to decide. SAVE,
        // progress, My Looks and the dice stay OUTSIDE it - the way to finish must
        // never be behind a disclosure.
        // [GAUNTLET C8 2026-08-20] The Customer ID row used to render only while
        // the ID was INVALID. But the ID is auto-detected by scanning iRacing
        // folders, so a wrong-but-VALID number (shared PC, a friend's install, a
        // stale folder) hid the field permanently and every save went to someone
        // else's number - silently, because the save still succeeds. It lives
        // inside the collapsed WHERE IT GOES drawer, so always rendering it costs
        // the buyer nothing and closes the trap.
        // [SPB-EASY-2026-08-19, screenshot pass] This used to render OPEN whenever
        // the customer ID looked missing - but the ID (and the car list) arrive
        // from /config AFTER the rail renders, so on a real boot the drawer was
        // ALWAYS open on first paint and the whole point was lost. It now renders
        // closed and refreshSaveEls() opens it only if a destination problem is
        // still blocking the save once the real values have landed.
        var drawerOpen = false;
        return '' +
            '<div class="spb-easy-controls">' +
            '  <details class="spb-easy-drawer spb-easy-senddrawer" id="spbEasySendDrawer"' + (drawerOpen ? ' open' : '') + '>' +
            '  <summary><span class="spb-easy-drawer-title">WHERE IT GOES</span>' +
            '    <span class="spb-easy-drawer-value" id="spbEasyDestSummary">' +
            (car ? esc(friendlyCarName(car.name)) : 'Choose your car') + ' · ' + (custom ? 'your number' : 'iRacing’s number') +
            '</span><span class="spb-easy-drawer-caret" aria-hidden="true">▾</span></summary>' +
            '  <div class="spb-easy-step-label spb-easy-step-tight">SAVE TO iRACING<small id="spbEasySaveHint">Choose the exact car. Shokker verifies both paint files before saying DONE.</small></div>' +
            '  <div class="spb-easy-destination">' +
            '    <label>FIND YOUR CAR FAST<input type="search" id="spbEasyCarSearch" maxlength="60" autocomplete="off" value="' + esc(_carFilterQuery) + '" placeholder="Type dirt late, Ferrari, ARCA..." title="Narrows the car list below. This picks the iRacing FOLDER your paint is saved into - it does not change the design."></label>' +
            '    <label>WHICH CAR?<select id="spbEasyCarSelect">' + carOptionsHtml() + '</select></label>' +
            recentCarsHtml() +
            '    <div class="spb-easy-alsocars" id="spbEasyAlsoCars"></div>' +
            '    <small id="spbEasyRouteSummary">' + (car ? ('Folder ' + esc(car.name)) : 'Choose the iRacing car folder') + '</small>' +
            '    <div class="spb-easy-number-choice" role="group" aria-label="iRacing number type">' +
            '      <button type="button" id="spbEasyCustomNumber" class="' + (custom ? 'on' : '') + '" title="' + esc(numberModeCopy(true)) + '">MY PAINT HAS THE NUMBER <small>car_num</small></button>' +
            '      <button type="button" id="spbEasySimNumber" class="' + (!custom ? 'on' : '') + '" title="' + esc(numberModeCopy(false)) + '">LET iRACING ADD IT <small>car</small></button>' +
            '    </div>' +
            numberModeHtml(custom) +
            (function () {
                // Say WHY it is set this way, and name the evidence. A default a
                // buyer cannot see the reasoning for is just a mystery setting.
                if (_numberModeTouched) return '';
                var d = detectNumberModeFromPaint();
                if (d === null) return '';
                return '<div class="spb-easy-number-auto">\u2713 Set from your file name \u2014 ' +
                    esc(String((function () {
                        try {
                            var p2 = (typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || '';
                            return String(p2).replace(/\\/g, '/').split('/').pop();
                        } catch (e) { return 'your paint'; }
                    })())) +
                    (d ? ' already carries your number.' : ' has no number, so iRacing will add one.') +
                    ' Change it above if that is wrong.</div>';
            })() +
            '  </div>' +
            '  <div class="spb-easy-id-row" id="spbEasyIdRow">' +
            '    <label for="spbEasyIdInput">YOUR iRACING NUMBER</label>' +
            '    <input type="text" id="spbEasyIdInput" inputmode="numeric" placeholder="e.g. 23371" maxlength="7" autocomplete="off" spellcheck="false" title="Your iRacing customer number. It is part of the file names Shokker writes, and iRacing only shows a paint whose file name matches YOUR number.">' +
            '    <small>Found by looking at your iRacing folders. It is the number in the file names below \u2014 if that is not you, change it here.</small>' +
            '  </div>' +
            '  <div class="spb-easy-file-proof" id="spbEasyFileProof">Will verify <b>' + esc(expectedOutputNames()[0]) + '</b> + <b>' + esc(expectedOutputNames()[1]) + '</b></div>' +
            '  </details>' +
            '  <div class="spb-easy-progress" id="spbEasyProgress">' +
            '    <div class="spb-easy-progress-track"><div class="spb-easy-progress-fill" id="spbEasyProgressFill"></div></div>' +
            '    <div class="spb-easy-progress-text" id="spbEasyProgressText">Painting…</div>' +
            '  </div>' +
            '  <div class="spb-easy-myloooks" id="spbEasyMyLooks"></div>' +
            '  <div class="spb-easy-readiness" id="spbEasyReadiness" hidden></div>' +
            '  <div class="spb-easy-actions">' +
            (diceTitle ? '  <button type="button" class="spb-easy-dice" id="spbEasyDice" title="' + esc(diceTitle) + '">🎲</button>' : '') +
            '    <button type="button" class="spb-easy-save" id="spbEasySave" title="Renders your car at full size and writes both files into the iRacing folder above, then checks they really landed before saying DONE.">SAVE TO iRACING</button>' +
            '  </div>' +
            '  <button type="button" class="spb-easy-dropunfinished" id="spbEasyDropUnfinished" hidden title="Removes the colors you have not given a finish to. Those parts of the car simply stay as you painted them.">\u2715 DROP THE COLORS I DID NOT FINISH</button>' +
            '  <button type="button" class="spb-easy-teach" id="spbEasyTeach" title="A four-step walk through this screen. Pro Mode is offered at the end, not instead.">🎓 Show me around Easy Mode</button>' +
            '  <button type="button" class="spb-easy-gloss-link" id="spbEasyGlossOpen" title="Plain-language meanings for the paint words this screen uses">\u2753 What do words like SPEC, CANDY and MATTE mean?</button>' +
            '</div>';
    }
    // [2026-08-08 E17] "My looks": save the current plan by name and drop it on
    // any other car in one click. Easy had no reuse at all - every car started
    // from zero even if the buyer had just perfected a look.
    function planListHtml() {
        var pairs = easyColorZones();
        if (!pairs.length) return '';
        var rows = pairs.map(function (p, n) {
            var z = p.z;
            var f = z.finish ? finishInfo(finishKey('monolithic', z.finish))
                  : (z.base ? finishInfo(finishKey('base', z.base)) : null);
            var pct = coveragePct(z.color && z.color.color_rgb, z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT);
            var swatch = z.baseColor && /^#[0-9a-fA-F]{6}$/.test(z.baseColor) ? z.baseColor : (z.pickerColor || '#888888');
            var strength = Math.round(Number(z.intensity != null ? z.intensity : 100));
            return '<button type="button" class="spb-easy-planrow' + (p.i === bc.zoneIdx ? ' current' : '') + '" data-plan-zone="' + p.i + '">' +
                '<i style="--plan-color:' + esc(swatch) + '"></i>' +
                '<span class="spb-easy-planrow-main"><b>' + esc(f ? f.name : 'Needs a finish') + '</b>' +
                '<small>' + esc(z.pickerColor || '') + (pct != null ? (pct <= 6
                    ? (' \u00b7 <b class="spb-easy-planrow-tiny">\u26a0 only ~' + pct + '% of the car</b>')
                    : (' \u00b7 ~' + pct + '% of the car')) : '') +
                (strength !== 100 ? (' \u00b7 ' + strength + '% strength') : '') + '</small></span>' +
                '<em>' + (f ? 'EDIT' : 'PICK') + '</em>' +
                '</button>';
        }).join('');
        return '<div class="spb-easy-step-label spb-easy-step-tight">YOUR PLAN<small>' + pairs.length +
            ' color' + (pairs.length === 1 ? '' : 's') + ' \u00b7 click one to change it</small></div>' +
            '<div class="spb-easy-planlist">' + rows + '</div>';
    }
    function wirePlanList() {
        var host = $('spbEasyPlanList');
        if (!host) return;
        host.addEventListener('click', function (e) {
            var row = e.target && e.target.closest ? e.target.closest('[data-plan-zone]') : null;
            if (!row) return;
            var zi = parseInt(row.getAttribute('data-plan-zone'), 10);
            if (isNaN(zi) || !zones[zi]) return;
            bc.zoneIdx = zi;
            bc.phase = (zones[zi].base || zones[zi].finish) ? 'options' : 'finish';
            bc.recolorOpen = false;
            _searchText = ''; _catalogMode = false;
            renderRail();
        });
    }

    function renderMyLooks() {
        var host = $('spbEasyMyLooks');
        if (!host) return;
        var plans = planList();
        var opts = plans.map(function (p) {
            return '<option value="' + esc(p.name) + '">' + esc(p.name) + '</option>';
        }).join('');
        host.innerHTML =
            '<div class="spb-easy-mylooks-bar">' +
            '  <button type="button" id="spbEasyCompareAdd" title="Snapshot how the car looks right now so you can weigh it against another look">\u229e COMPARE</button>' +
            '  <button type="button" id="spbEasyCompareOpen" hidden></button>' +
            '  <button type="button" id="spbEasySaveLook" title="Save the colors and finishes you picked as a reusable look, for any car">\u2605 SAVE LOOK</button>' +
            '  <button type="button" id="spbEasyShareBtn" title="Send this look to someone, or paste in a code they sent you">\u21ea SHARE</button>' +
            '  <button type="button" id="spbEasyProtectBtn" title="Keep your numbers, logos or decals exactly as they are - no finish touches them">' +
            (_protectMode ? '\u2713 DONE PROTECTING' : '\u{1F6E1} KEEP PARTS UNPAINTED') + '</button>' +
            (plans.length
                ? '  <select id="spbEasyLoadLook" title="Load one of your saved looks onto this car"><option value="">Load a look...</option>' + opts + '</select>' +
                  '  <button type="button" id="spbEasyDeleteLook" title="Delete the selected saved look">\u{1F5D1}</button>'
                : '') +
            '</div>' + protectChipsHtml();
        var shareBtn = $('spbEasyShareBtn');
        if (shareBtn) shareBtn.addEventListener('click', openShare);
        var protectBtn = $('spbEasyProtectBtn');
        if (protectBtn) {
            if (_protectMode) protectBtn.classList.add('on');
            protectBtn.addEventListener('click', function () { setProtectMode(!_protectMode); });
        }
        var chipHost = $('spbEasyProtectChips');
        if (chipHost) chipHost.addEventListener('click', function (ev) {
            var btn = ev.target.closest ? ev.target.closest('[data-unprotect]') : null;
            if (!btn) return;
            unprotect(parseInt(btn.getAttribute('data-unprotect'), 10));
        });
        var cmpAdd = $('spbEasyCompareAdd');
        if (cmpAdd) cmpAdd.addEventListener('click', captureCompare);
        var cmpOpen = $('spbEasyCompareOpen');
        if (cmpOpen) cmpOpen.addEventListener('click', openCompare);
        renderCompareBar();
        var saveBtn = $('spbEasySaveLook');
        if (saveBtn) saveBtn.addEventListener('click', function () {
            var suggested = (state.view === 'whole' ? 'Whole car look' : 'My color plan');
            easyAsk({
                title: 'Name this look',
                body: 'So you can find it again and drop it onto another car.',
                input: suggested, yes: 'SAVE LOOK'
            }).then(function (name) {
                if (name == null || !name) return;
                if (savePlan(name)) {
                    renderMyLooks();
                    try { if (window.showToast) window.showToast('Saved "' + name + '" - reuse it on any car', 'success'); } catch (e) {}
                }
            });
        });
        var loadSel = $('spbEasyLoadLook');
        if (loadSel) loadSel.addEventListener('change', function () {
            var name = loadSel.value;
            if (!name) return;
            var plan = planList().filter(function (p) { return p && p.name === name; })[0];
            if (plan) applyPlan(plan);
        });
        var delBtn = $('spbEasyDeleteLook');
        if (delBtn) delBtn.addEventListener('click', function () {
            var sel = $('spbEasyLoadLook');
            var name = sel && sel.value;
            if (!name) { try { if (window.showToast) window.showToast('Pick a saved look to delete first', 'info'); } catch (e) {} return; }
            easyAsk({
                title: 'Delete this saved look?',
                body: '\u201c' + name + '\u201d goes out of My Looks. Cars you already painted with ' +
                      'it are not affected.',
                yes: 'DELETE', no: 'KEEP IT', danger: true
            }).then(function (ok) {
                if (!ok) return;
                deletePlan(name); renderMyLooks();
            });
        });
    }

    function renderAlsoCars() {
        var host = $('spbEasyAlsoCars');
        if (!host) return;
        var cur = currentCarRecord();
        var opts = _iracingCars
            .filter(function (c) { return !cur || c.name !== cur.name; })
            .filter(function (c) { return _alsoCars.indexOf(c.name) === -1; })
            .map(function (c) {
                return '<option value="' + esc(c.name) + '">' + esc(friendlyCarName(c.name)) + '</option>';
            }).join('');
        host.innerHTML =
            '<div class="spb-easy-alsocars-row">' +
            '  <label for="spbEasyAlsoPick">ALSO SAVE TO</label>' +
            '  <select id="spbEasyAlsoPick" title="Send this same look to another car folder as well"><option value="">Add another car\u2026</option>' + opts + '</select>' +
            '</div>' +
            (_alsoCars.length
                ? '<div class="spb-easy-alsocars-chips">' + _alsoCars.map(function (n) {
                      return '<span class="spb-easy-alsocar">' + esc(friendlyCarName(n)) +
                             '<button type="button" data-also-drop="' + esc(n) + '" title="Remove this car">\u2715</button></span>';
                  }).join('') + '</div>'
                : '');
        var pick = $('spbEasyAlsoPick');
        if (pick) pick.addEventListener('change', function () {
            var v = pick.value;
            if (!v) return;
            if (_alsoCars.indexOf(v) === -1) _alsoCars.push(v);
            renderAlsoCars();
            refreshSaveEls();
        });
        host.addEventListener('click', function (e) {
            var drop = e.target && e.target.closest ? e.target.closest('[data-also-drop]') : null;
            if (!drop) return;
            e.preventDefault(); e.stopPropagation();
            var n = drop.getAttribute('data-also-drop');
            _alsoCars = _alsoCars.filter(function (x) { return x !== n; });
            renderAlsoCars();
        });
    }

    function deployToExtraCars(jobId, cb) {
        var idEl = $('iracingId');
        var idVal = idEl ? String(idEl.value || '').trim() : '';
        var queue = _alsoCars.slice();
        var done = [], failed = [];
        function next() {
            if (!queue.length) { cb(done, failed); return; }
            var car = queue.shift();
            fetch(serverBase() + '/deploy-to-iracing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id: jobId, car_folder: car, iracing_id: idVal })
            }).then(function (r) { return r.json(); })
              .then(function (j) {
                  if (j && j.success && j.verified !== false) done.push(car); else failed.push(car);
              })
              .catch(function () { failed.push(car); })
              .then(next);
        }
        next();
    }

    function wireSaveBlock() {
        // [GAUNTLET E2 2026-08-20] MUST be wired here, not in the once-only
        // buildRoot section: saveBlockHtml() re-creates this button on every rail
        // render, so a listener attached once lands on an element that is thrown
        // away moments later. MEASURED: the drop button looked correct, had the
        // right label, and did nothing at all.
        var _dropUnfin = $('spbEasyDropUnfinished');
        if (_dropUnfin) _dropUnfin.addEventListener('click', function () {
            var pend = easyColorZones().filter(function (p) { return !(p.z.base || p.z.finish); });
            if (!pend.length) return;
            undoPush('Easy Mode: drop unfinished colors');
            // Splice high-to-low so earlier indices stay valid.
            pend.map(function (p) { return p.i; }).sort(function (a, b) { return b - a; })
                .forEach(function (i) { try { zones.splice(i, 1); } catch (e) {} });
            bc = { phase: 'pick', zoneIdx: -1, pickerFor: 'finish', recolorOpen: false };
            var left = easyColorZones();
            if (left.length) { bc.phase = 'options'; bc.zoneIdx = left[left.length - 1].i; }
            refreshZonesUI();
            renderRail();
            kickPreview();
            try { if (window.showToast) window.showToast('Those colors stay as you painted them', 'info'); } catch (e) {}
        });

        renderAlsoCars();
        renderMyLooks();
        var save = $('spbEasySave'); if (save) save.addEventListener('click', onSaveClick);
        // [2026-08-09 S37] The rail toggle is NOT wired here any more. This
        // function only runs on Easy Mode's own save-block render, so while
        // Spec Sculpt owned the rail the button sat there inert - measured
        // dead to both a real pointer click and a direct .click(). It is now
        // handled by the delegated listener in wireRailToggleOnce(), which
        // works whoever rendered the shell. Do not re-add a direct binding
        // here: two handlers on one button toggle twice per click, which looks
        // exactly like nothing happening.
        var folderBtn = $('spbEasyResultFolder');
        if (folderBtn) folderBtn.addEventListener('click', openSavedFolder);
        var dice = $('spbEasyDice'); if (dice) dice.addEventListener('click', surprise);
        var teach = $('spbEasyTeach'); if (teach) teach.addEventListener('click', teachMe);
        var gloss = $('spbEasyGlossOpen'); if (gloss) gloss.addEventListener('click', openGlossary);
        var recentHost = els.root ? els.root.querySelector('.spb-easy-recent-cars') : null;
        if (recentHost) recentHost.addEventListener('click', function (e) {
            var btn = e.target && e.target.closest ? e.target.closest('[data-recent-car]') : null;
            if (!btn) return;
            if (!chooseCar(btn.getAttribute('data-recent-car'))) {
                try { if (window.showToast) window.showToast('That car folder is not in this iRacing install any more', 'info'); } catch (err) {}
            }
        });
        var carSearch = $('spbEasyCarSearch');
        if (carSearch) carSearch.addEventListener('input', function () {
            _carFilterQuery = carSearch.value.slice(0, 60);
            filterEasyCarOptions();
        });
        filterEasyCarOptions();
        var select = $('spbEasyCarSelect');
        if (select) select.addEventListener('change', function () {
            _carFilterQuery = '';
            if (carSearch) carSearch.value = '';
            filterEasyCarOptions();
            var out = $('outputDir');
            if (out) {
                out.value = select.value;
                try { out.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
                try { if (typeof updateOutputPath === 'function') updateOutputPath(); } catch (e2) {}
            }
            var car = currentCarRecord();
            var summary = $('spbEasyRouteSummary');
            if (summary) summary.textContent = car ? ('Folder ' + car.name) : 'Choose the iRacing car folder';
            syncDestSummary();
            if (car) { noteRecentCar(car.path, car.name); renderRail(); }
            refreshSaveEls();
        });
        function setNumberMode(custom) {
            var c = $('useCustomNumberCheckbox'), s = $('useSimStampedCheckbox');
            if (c) c.checked = !!custom;
            if (s) s.checked = !custom;
            try { if (typeof toggleCustomNumber === 'function') toggleCustomNumber(!!custom); } catch (e) {}
            syncFileProof();
            var cb = $('spbEasyCustomNumber'), sb = $('spbEasySimNumber');
            if (cb) cb.classList.toggle('on', !!custom);
            if (sb) sb.classList.toggle('on', !custom);
            var why = $('spbEasyNumberWhy');
            if (why) {
                var head = why.querySelector('b'), text = why.querySelector('span');
                if (head) head.textContent = custom ? 'YOUR PAINT CARRIES THE NUMBER' : 'iRACING ADDS THE NUMBER';
                if (text) text.textContent = numberModeCopy(!!custom);
            }
            syncDestSummary();
        }
        var customBtn = $('spbEasyCustomNumber'); if (customBtn) customBtn.addEventListener('click', function () { _numberModeTouched = true; setNumberMode(true); renderRail(); });
        var simBtn = $('spbEasySimNumber'); if (simBtn) simBtn.addEventListener('click', function () { _numberModeTouched = true; setNumberMode(false); renderRail(); });
        var inp = $('spbEasyIdInput');
        var mainId = $('iracingId');
        if (inp && mainId) inp.value = mainId.value || '';
        if (inp) inp.addEventListener('input', function () {
            var idEl = $('iracingId');
            if (idEl && idEl.value !== inp.value) {
                idEl.value = inp.value;
                try { idEl.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
            }
            syncFileProof();
            refreshSaveEls();
        });
        refreshSaveEls();
        syncIdRow();
        ensureIracingCars();
    }    function refreshSaveEls() {
        // [SPB-EASY-2026-08-19] The drawer renders before /iracing-cars resolves,
        // so its collapsed summary would sit on "Choose your car" forever even
        // though a car WAS detected. populateCarSelect() calls this.
        syncDestSummary();
        els.save = $('spbEasySave');
        els.idRow = $('spbEasyIdRow');
        els.idInput = $('spbEasyIdInput');
        els.progress = $('spbEasyProgress');
        els.progressFill = $('spbEasyProgressFill');
        els.progressText = $('spbEasyProgressText');
        if (els.save && !_saving) {
            var reason = saveBlockReason();
            els.save.disabled = !!reason;
            els.save.textContent = reason || 'SAVE TO iRACING';
            syncReadinessChecklist(!!reason);   // [SPB-EASY-READY] all blockers visible + clickable
            // The SAVE button names the blocker, but the control that fixes it
            // lives inside the collapsed drawer - so open the drawer for exactly
            // those two reasons, and never for "pick a finish first".
            // [GAUNTLET E1 2026-08-20] MEASURED walking By Color: at the "click a
            // color on your car" step the buyer faced 11 buttons, of which TWO
            // did anything. Four of the rest are the extras bar — COMPARE,
            // SAVE LOOK, SHARE, KEEP PARTS UNPAINTED — and every one of them is
            // meaningless before a finish exists: nothing to compare, nothing to
            // save, nothing to share, no finish to keep parts out of. They now
            // appear when they can actually do something.
            // By Color has its own "not done yet" blocker; a picked colour with no
            // finish on it is still nothing to compare, save or share.
            var noWorkYet = (reason === 'PICK A FINISH FIRST' || reason === 'LOAD A PAINT FIRST' ||
                             reason.indexOf('CHOOSE A FINISH') === 0 || /^\d+ COLORS STILL NEED/.test(reason));
            var extras = els.save && els.save.closest ? els.save.closest('.spb-easy-controls') : null;
            extras = extras ? extras.querySelector('.spb-easy-myloooks') : null;
            if (extras) extras.hidden = noWorkYet;
            // [GAUNTLET E2] The way out of "N colors still need a finish" when
            // the buyer only ever wanted one of them.
            var drop = $('spbEasyDropUnfinished');
            if (drop) {
                var pend = (state.view === 'bycolor')
                    ? easyColorZones().filter(function (p) { return !(p.z.base || p.z.finish); }).length : 0;
                var done = (state.view === 'bycolor')
                    ? easyColorZones().filter(function (p) { return !!(p.z.base || p.z.finish); }).length : 0;
                // Only useful if dropping them would actually unblock a real save.
                drop.hidden = !(pend > 0 && done > 0);
                drop.textContent = '\u2715 DROP THE ' + pend + ' COLOR' + (pend === 1 ? '' : 'S') + ' I DID NOT FINISH';
            }
            var destBlocked = reason === 'ENTER YOUR CUSTOMER ID' || reason === 'CHOOSE AN iRACING CAR';
            // [GAUNTLET B3 2026-08-20] ...but not during the first few seconds,
            // when "missing" only means /config has not answered yet. Opening on
            // that transient made the drawer flap open then shut on every boot.
            var settled = !_enteredAt || (Date.now() - _enteredAt) > 3500;
            var drawer = $('spbEasySendDrawer');
            if (drawer) {
                // [GAUNTLET E1 2026-08-20] This used to only ever OPEN. One
                // transient blocker — /config not answered yet, a car record
                // briefly null after START OVER — latched the drawer open for the
                // rest of the session, which is how the car_num question ended up
                // on screen during "click a color on your car". Auto-open is now
                // reversible, and a manual toggle opts out of the automation
                // entirely so we never fight the buyer.
                if (!drawer._spbToggleWired) {
                    drawer._spbToggleWired = true;
                    drawer.addEventListener('toggle', function () {
                        if (drawer._spbSelfToggle) return;
                        drawer._spbManual = true;
                    });
                }
                if (!drawer._spbManual) {
                    var want = destBlocked && settled;
                    if (want !== drawer.open) {
                        drawer._spbSelfToggle = true;
                        drawer.open = want;
                        drawer._spbSelfToggle = false;
                    }
                }
            }
        }
    }

    // --- FORK ---------------------------------------------------------------
    function renderForkRail() {
        var sculptPlan = null;
        try {
            var sculptState = window.spbEasySculpt && window.spbEasySculpt.getState && window.spbEasySculpt.getState();
            if (sculptState && sculptState.selectedLook && sculptState.sourceUrl && sculptState.specUrl && sculptState.phase !== 'drop') {
                var colorCount = Array.isArray(sculptState.colorTargets) ? sculptState.colorTargets.length : 0;
                var carName = sculptState.car && window.spbEasySculpt.friendlyCarName
                    ? window.spbEasySculpt.friendlyCarName(sculptState.car) : '';
                sculptPlan = {
                    badge: 'CURRENT MATERIAL PLAN READY',
                    title: 'CONTINUE SPEC SCULPT',
                    description: 'Your ' + (colorCount ? (colorCount + '-color ') : '') + 'material plan' +
                        (carName ? (' and ' + carName + ' destination') : '') +
                        ' are still here. Return without rebuilding anything.'
                };
            }
        } catch (e) { sculptPlan = null; }
        // [2026-08-06 easy-loop #4] The fork opened on "STEP 2" with the demo car
        // loaded and NO way to load YOUR paint from Easy Mode — a buyer's first
        // question. STEP 1 card: shows what's loaded, one big button into the
        // thumbnail file picker (loadPaintByPath handles the rest app-wide).
        var _step1File = '';
        try { _step1File = (typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || ''; } catch (e) {}
        var _step1Name = _step1File ? String(_step1File).split(/[\\/]/).pop() : '';
        els.rail.innerHTML = '' +
            '<div class="spb-easy-step1-card">' +
            '  <div class="spb-easy-step1-info"><b>STEP 1 · YOUR CAR</b>' +
            '  <small id="spbEasyStep1File">' + (_step1Name ? ('Loaded: ' + esc(_step1Name)) : 'No paint loaded yet') + '</small></div>' +
            '  <button type="button" id="spbEasyLoadPaint">&#128194; LOAD YOUR PAINT<small>TGA &middot; PNG &middot; JPEG &middot; PSD</small></button>' +
            '</div>' +
            railHeader('STEP 2 · WHAT SHOULD SHOKKER DO?', 'Let Shokker sculpt it automatically, or choose the materials yourself.', false) +
            '<div class="spb-easy-fork">' +
            '  <button type="button" class="spb-easy-fork-card spb-easy-fork-sculpt" id="spbEasyForkSculpt">' +
            '    <span class="spb-easy-fork-badge">' + (sculptPlan ? esc(sculptPlan.badge) : 'FULL LOOK LIBRARY &middot; 2 MINUTES') + '</span>' +
            '    <span class="spb-easy-fork-icon">&#10024;</span>' +
            '    <span class="spb-easy-fork-title">' + (sculptPlan ? esc(sculptPlan.title) : 'SPEC SCULPT') + '</span>' +
            '    <span class="spb-easy-fork-desc">' + (sculptPlan ? esc(sculptPlan.description) : 'Load a finished 2048 paint, browse every Spec Sculpt and Paint Booth look, preview it, and put it in iRacing.') + '</span>' +
            '  </button>' +
            '  <button type="button" class="spb-easy-fork-card" id="spbEasyForkWhole">' +
            '    <span class="spb-easy-fork-icon">🚗</span>' +
            '    <span class="spb-easy-fork-title">WHOLE CAR</span>' +
            '    <span class="spb-easy-fork-desc">Choose one finish—or blend up to four. Shokker follows the livery automatically while your colors, numbers and decals stay untouched. Every finish in the catalog is available.</span>' +
            '  </button>' +
            '  <button type="button" class="spb-easy-fork-card" id="spbEasyForkByColor">' +
            '    <span class="spb-easy-fork-icon">🎯</span>' +
            '    <span class="spb-easy-fork-title">BY COLOR</span>' +
            '    <span class="spb-easy-fork-desc">Paint by numbers. Click a color on your car, choose what finish that color becomes — and optionally change the color itself. Repeat for every color you want.</span>' +
            '  </button>' +
            '  <button type="button" class="spb-easy-demo" id="spbEasyShowExample" title="Builds a finished two-material car so you can see what this does before choosing anything">\u{1F440} NOT SURE? SHOW ME AN EXAMPLE</button>' +
            '  <button type="button" class="spb-easy-original-sculpt" id="spbEasyForkOriginalSculpt">' +
            '    <span>ORIGINAL / ADVANCED</span><b>OPEN ORIGINAL SPEC SCULPT</b>' +
            '    <small>SHOKK THE WORLD &middot; Auto-Sculpt &middot; stacks &middot; masks &middot; every deep control</small>' +
            '  </button>' +
            '  <button type="button" class="spb-easy-teach" id="spbEasyTeachFork" title="A short walk through this screen, without leaving Easy Mode. Pro Mode is offered at the end.">🎓 New here? Show me around →</button>' +
            '</div>';
        var _loadBtn = $('spbEasyLoadPaint');
        if (_loadBtn) _loadBtn.addEventListener('click', function () {
            if (typeof window.openFilePicker !== 'function') return;
            window.openFilePicker({
                title: 'Select Your Car Paint (TGA / PNG / JPEG / PSD)',
                mode: 'file',
                onSelect: function (path) {
                    if (typeof window.loadPaintByPath === 'function') window.loadPaintByPath(path);
                    // the load pipeline refreshes previews app-wide; re-render the
                    // rail once it has had a beat so STEP 1 shows the new name
                    setTimeout(function () { if (_active && state.view === 'fork') renderRail(); }, 2500);
                }
            });
        });
        $('spbEasyForkSculpt').addEventListener('click', function () { state.view = 'sculpt'; renderRail(); });
        $('spbEasyForkWhole').addEventListener('click', function () { _carFilterQuery = ''; state.view = 'whole'; renderRail(); });
        $('spbEasyForkByColor').addEventListener('click', function () { enterByColor(); });
        $('spbEasyTeachFork').addEventListener('click', teachMe);
        var demoBtn = $('spbEasyShowExample');
        if (demoBtn) demoBtn.addEventListener('click', function () { showExample(); });
        $('spbEasyForkOriginalSculpt').addEventListener('click', function () {
            if (window.spbEasySculpt && typeof window.spbEasySculpt.openOriginal === 'function') {
                window.spbEasySculpt.openOriginal();
                return;
            }
            var child = window.open('/spec-sculpt.html', 'shokkerSpecSculptLab');
            if (!child) window.location.href = '/spec-sculpt.html';
        });
    }

    // --- WHOLE CAR ------------------------------------------------------------
    function renderWholeRail() {
        var activePlan = readWholeMaterialPlan() || readLegacyWholeMaterialPlan();
        if (activePlan) hydrateWholeState(activePlan);
        else {
            // Opening a mode is navigation, not an edit. Never repaint the car
            // with a stale localStorage mix merely because WHOLE CAR was opened.
            state.wholeStack = [];
            state.wholeAmount = 1.0;
            state.wholeScale = 1.0;
        }
        // [SPB-EASY-2026-08-19] BROWSE IS THE LANDING. Order rewritten so the one
        // job of this screen comes first: search, then the catalog. Lighting and
        // the "your paint stays your paint" explainer moved BELOW the shelves into
        // a TUNE IT drawer - kept in full, just not competing with the catalog for
        // a first-time buyer's attention. The back-to-fork arrow is gone (this IS
        // the first screen now); BY COLOR / SPEC SCULPT / SHOW ME AN EXAMPLE
        // survive as side doors, offered AFTER they have a look they like instead
        // of before they have seen anything.
        els.rail.innerHTML = '' +
            railHeader('PICK A FINISH', 'Tap one — it goes straight on your car. Your colors, numbers and decals stay exactly as you painted them.', false) +
            '<div class="spb-easy-finder">' +
            '  <input type="text" id="spbEasySearch" value="' + esc(_searchText) + '" placeholder="' + (state.wholeStack.length ? 'Add another finish…' : 'Search ' + nfmt(catalogTotal()) + ' finishes…') + ' chrome, candy, carbon…" autocomplete="off" spellcheck="false" title="' + esc(SEARCH_TIP) + '">' +
            '  <button type="button" class="spb-easy-search-clear" id="spbEasySearchClear" aria-label="Clear the search" title="Clear the search"' +
            (_searchText ? '' : ' hidden') + '>\u2715</button>' +
            '  <button type="button" id="spbEasyCatalogToggle" title="' + esc(CAT_TIP) + '"></button>' +
            '</div>' +
            '<div class="spb-easy-finishes" id="spbEasyFinishes"></div>' +
            // [SPB-EASY-2026-08-19] One wrapper for everything that is NOT the
            // catalog. In the wide browse layout it becomes the right-hand
            // column, which lets the catalog own the full height of the left
            // column instead of being squeezed between blocks above and below
            // it. In the narrow/stacked layout it is an inert div and the
            // children lay out exactly as before.
            '<div class="spb-easy-browse-side" id="spbEasyBrowseSide">' +
            '<div class="spb-easy-whole-stack" id="spbEasyWholeStack">' + wholeStackHtml() + '</div>' +
            '<div class="spb-easy-mix-notice" id="spbEasyMixNotice" aria-live="polite"></div>' +
            '<div class="spb-easy-sidedoors">' +
            '  <button type="button" id="spbEasySideByColor" title="Give ONE color on your car its own finish, instead of one finish over the whole car.">🎯 ONE COLOR AT A TIME</button>' +
            '  <button type="button" id="spbEasySideSculpt" title="Load a finished 2048 paint and let Shokker sculpt a starting point, then browse every look.">✨ SPEC SCULPT</button>' +
            '  <button type="button" id="spbEasySideExample" title="Builds a finished two-material car so you can see what this does before choosing anything.">👀 SHOW ME AN EXAMPLE</button>' +
            '</div>' +
            carPartsDrawerHtml() +
            '<details class="spb-easy-drawer spb-easy-tunedrawer" id="spbEasyTuneDrawer">' +
            '  <summary><span class="spb-easy-drawer-title">TUNE IT</span>' +
            '    <span class="spb-easy-drawer-value">lighting · how it works</span>' +
            '    <span class="spb-easy-drawer-caret" aria-hidden="true">▾</span></summary>' +
            '  <div class="spb-easy-lights" id="spbEasyLights" role="group" aria-label="Preview lighting">' +
            Object.keys(LIGHT_MODES).map(function (k) {
                var L2 = LIGHT_MODES[k];
                return '<button type="button" class="spb-easy-light' + (state.light === k ? ' on' : '') +
                    '" data-light="' + k + '" title="' + esc(L2.hint) + '">' + esc(L2.label) + '</button>';
            }).join('') +
            '  </div>' +
            '  <div class="spb-easy-whole-promise"><b>✓ YOUR PAINT STAYS YOUR PAINT</b><span>Shokker reads the livery\'s colors and detail, then maps your chosen finishes where they fit best.</span><small>Each card shows PAINT | SHINE. A whole-car finish uses the shine behavior only — never the card\'s own colors.</small></div>' +
            '</details>' +
            saveBlockHtml('Replace the mix with one surprise finish') +
            '</div>';
        $('spbEasySideByColor').addEventListener('click', function () { enterByColor(); });
        $('spbEasySideSculpt').addEventListener('click', function () { state.view = 'sculpt'; renderRail(); });
        $('spbEasySideExample').addEventListener('click', function () { showExample(); });
        els.search = $('spbEasySearch');
        els.catalogToggle = $('spbEasyCatalogToggle');
        els.finishes = $('spbEasyFinishes');
        els.catalogToggle.addEventListener('click', function () {
            if (_catalogMode || _searchText) {
                _catalogMode = false;
                _searchText = '';
                if (els.search) els.search.value = '';
            } else _catalogMode = true;
            renderFinishList();
        });
        els.search.addEventListener('input', function () {
            _searchText = String(els.search.value || '').trim().toLowerCase();
            // [GAUNTLET A6 2026-08-20] The × only exists while there is something
            // to clear, so it never sits there as dead chrome.
            var clr = $('spbEasySearchClear');
            if (clr) clr.hidden = !els.search.value;
            searchSoon();
        });
        var searchClear = $('spbEasySearchClear');
        if (searchClear) searchClear.addEventListener('click', function () {
            els.search.value = '';
            _searchText = '';
            searchClear.hidden = true;
            renderFinishList();
            try { els.search.focus(); } catch (e) {}
        });
        attachFinishListHandlers(els.finishes);
        // [GAUNTLET A6] Delegated so it survives every re-render of the list.
        if (els.finishes && !els.finishes._spbIdeaWired) {
            els.finishes._spbIdeaWired = true;
            els.finishes.addEventListener('click', function (ev) {
                var t = ev.target && ev.target.closest ? ev.target.closest('[data-try]') : null;
                if (!t) return;
                ev.preventDefault();
                var word = t.getAttribute('data-try') || '';
                if (els.search) els.search.value = word;
                _searchText = word.toLowerCase();
                var clr2 = $('spbEasySearchClear');
                if (clr2) clr2.hidden = false;
                renderFinishList();
            });
        }
        wireCarParts();
        wireSaveBlock();
        wireLights();
        wireWholeStack();
        renderFinishList();
    }

    // [2026-08-08 E27] The blend shares were drag-only. A buyer who wants a
    // straight 50/50 had to nudge a slider until the label happened to read 50,
    // and "mostly carbon with a bit of candy" had no way to be said at all.
    // Two fixes, both in the buyer's own language: named splits that show their
    // real numbers, and a box you can type an exact percent into. Both land on
    // the same rebalance the slider uses, so the mix always still sums to 100.
    var MIX_PRESETS = {
        2: [[50, 50], [70, 30], [85, 15]],
        3: [[34, 33, 33], [60, 20, 20], [50, 30, 20]],
        4: [[25, 25, 25, 25], [55, 15, 15, 15], [40, 30, 20, 10]]
    };
    function mixPresetsHtml(rows) {
        var list = MIX_PRESETS[rows.length];
        if (!list) return '';
        var current = rows.map(function (r) { return r.weight; }).join('/');
        return '<div class="spb-easy-mix-presets"><span>QUICK SPLIT</span>' +
            list.map(function (arr, i) {
                var label = arr.join('/');
                var even = arr.every(function (v) { return Math.abs(v - arr[0]) <= 1; });
                var on = (label === current) ? ' class="on"' : '';
                return '<button type="button" data-mix-preset="' + i + '"' + on +
                    ' title="Give material 1 ' + arr[0] + '% of the mix' +
                    (arr.length > 1 ? ', material 2 ' + arr[1] + '%' : '') + '">' +
                    (even ? 'EVEN ' : '') + label + '</button>';
            }).join('') + '</div>';
    }
    function applyMixPreset(i) {
        var rows = normalizedWholeStack(state.wholeStack);
        var preset = (MIX_PRESETS[rows.length] || [])[i];
        if (!preset) return false;
        undoPush('Easy Mode: quick split ' + preset.join('/'));
        rows.forEach(function (row, k) { row.weight = preset[k]; });
        state.wholeStack = normalizeWholeShares(rows);
        applyWholeStack(false, false);
        renderRail();
        return true;
    }

    // [2026-08-08 E28] "Shokker maps the rest" was the whole explanation the
    // buyer got for where their materials land. The routing is real math on
    // their own paint (authored M/R/Cc statistics x per-pixel luminance /
    // saturation / detail, calibrated to the shares they set) and cannot be
    // approximated here honestly, so SHOW ME WHERE asks the engine for the
    // actual shares (/api/material-map) and paints them over the SOURCE card.
    var _mapState = { on: false, busy: false, png: '', rows: [], key: '' };
    function mapKeyForStack(rows) {
        return rows.map(function (r) { return r.registryType + ':' + r.id + ':' + r.weight; }).join('|') +
            '@' + (currentPaintPath() || '');
    }
    function mapOverlayEl() {
        return els.root ? els.root.querySelector('#spbEasyMapOverlay') : null;
    }
    function paintMapOverlay() {
        var img = mapOverlayEl();
        if (!img) return;
        if (!_mapState.on || !_mapState.png) { img.hidden = true; img.removeAttribute('src'); return; }
        img.src = _mapState.png;
        img.hidden = false;
    }
    function fetchMaterialMap() {
        var rows = normalizedWholeStack(state.wholeStack);
        if (rows.length < 2) return;
        var key = mapKeyForStack(rows);
        if (_mapState.png && _mapState.key === key) { paintMapOverlay(); renderRail(); return; }
        _mapState.busy = true;
        renderRail();
        var body = {
            paint_file: currentPaintPath(),
            materials: rows.map(function (r) {
                return { id: r.id, registry_type: r.registryType, weight: r.weight };
            })
        };
        var base = '';
        try { base = (window.ShokkerAPI && window.ShokkerAPI.baseUrl) || ''; } catch (e) {}
        // [2026-08-09 S49] On a fresh boot #paintFile is
        // "...Starting Example PSD.tga" and only the .PSD exists on disk, so
        // this - the one caller that reads the paint FROM DISK - 404s with
        // "That paint file is not on disk." while renders keep working (they
        // upload pixels). Measured: .tga -> 404, .psd -> 200, and with a real
        // on-disk paint the whole feature works in 202ms. So retry once with
        // the sibling source before giving up. One extra POST, failures only.
        function postMaterialMap(pathToTry) {
            body.paint_file = pathToTry;
            return fetch(base + '/api/material-map', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            }).then(function (r) { return r.json(); });
        }
        function siblingSourcePath(pth) {
            if (/\.tga$/i.test(pth || '')) return pth.replace(/\.tga$/i, '.psd');
            if (/\.psd$/i.test(pth || '')) return pth.replace(/\.psd$/i, '.tga');
            return '';
        }
        function missingOnDisk(out) {
            return !!(out && !out.ok && /not on disk/i.test(String(out.error || '')));
        }
        postMaterialMap(body.paint_file).then(function (out) {
            if (!missingOnDisk(out)) return out;
            var sib = siblingSourcePath(currentPaintPath());
            if (!sib) return out;
            return postMaterialMap(sib).then(function (retry) {
                return missingOnDisk(retry) ? out : retry;
            }, function () { return out; });
        }).then(function (out) {
            _mapState.busy = false;
            if (!out || !out.ok) {
                _mapState.on = false;
                try {
                    // "That paint file is not on disk" is true but unactionable.
                    // Tell the buyer what to DO about it.
                    if (window.showToast) window.showToast(missingOnDisk(out)
                        ? 'Shokker needs the paint saved as a file to map it. Open your ' +
                          '.tga or .psd with CHOOSE PAINT, then press SHOW ME WHERE again.'
                        : ('Could not map the materials: ' +
                           ((out && out.error) || 'no answer from Shokker')), 'info');
                } catch (e) {}
                renderRail();
                return;
            }
            _mapState.png = out.png;
            _mapState.rows = out.materials || [];
            _mapState.key = key;
            paintMapOverlay();
            renderRail();
        }).catch(function (err) {
            _mapState.busy = false;
            _mapState.on = false;
            try { if (window.showToast) window.showToast('Could not map the materials', 'info'); } catch (e) {}
            renderRail();
        });
    }
    function toggleMaterialMap() {
        var rows = normalizedWholeStack(state.wholeStack);
        if (rows.length < 2) return;
        _mapState.on = !_mapState.on;
        if (!_mapState.on) { paintMapOverlay(); renderRail(); return; }
        if (_mapState.png && _mapState.key === mapKeyForStack(rows)) { paintMapOverlay(); renderRail(); return; }
        fetchMaterialMap();
    }
    function materialMapHtml(rows) {
        if (rows.length < 2) return '';
        var btn = '<button type="button" id="spbEasyShowMap"' + (_mapState.on ? ' class="on"' : '') +
            ' title="See which material Shokker puts where on YOUR paint">' +
            (_mapState.busy ? 'WORKING\u2026' : (_mapState.on ? '\u2713 SHOWING WHERE' : '\u25c9 SHOW ME WHERE')) + '</button>';
        var legend = '';
        if (_mapState.on && _mapState.rows.length) {
            legend = _mapState.rows.map(function (m, i) {
                var info = finishInfo(rows[i] ? rows[i].key : '', rows[i] ? rows[i].registryType : '');
                return '<span class="spb-easy-map-key"><i style="background:' + esc(m.color) + '"></i>' +
                    esc(info ? info.name : m.id) + ' <b>leads ' + m.leads_pct + '%</b></span>';
            }).join('');
        }
        return '<div class="spb-easy-map-row">' + btn + legend + '</div>';
    }

    function wholeStackHtml() {
        var rows = normalizedWholeStack(state.wholeStack);
        if (!rows.length) {
            return '<div class="spb-easy-mix-empty"><b>1. PICK A MATERIAL BELOW</b><span>That is enough to make a complete car. Add more only when you want a custom blend.</span></div>';
        }
        var html = demoNoteHtml() + '<div class="spb-easy-mix-head"><span><b>ON YOUR CAR</b><small>' + rows.length + ' OF 4 · ADDS UP TO 100%</small></span><em>Each % is how much of the car gets that finish. Shokker decides where each one fits.</em></div>' + materialMapHtml(rows) + mixPresetsHtml(rows);
        rows.forEach(function (entry, index) {
            var info = finishInfo(entry.key, entry.registryType);
            if (!info) return;
            html += '<div class="spb-easy-mix-row" data-mix-key="' + esc(entry.key) + '">' +
                splitThumbHtml(info, 'spb-easy-mix-thumb') +
                '<span class="spb-easy-mix-copy"><b>' + (index + 1) + '. ' + esc(info.name) + '</b><small>' +
                '<input type="number" class="spb-easy-mix-num" data-mix-value="' + index + '" data-mix-num="' + index + '" min="1" max="' + (100 - (rows.length - 1)) + '" step="1" value="' + entry.weight + '" aria-label="' + esc(info.name) + ' share of the car, percent" title="Type the exact share you want"' + (rows.length === 1 ? ' disabled' : '') + '>% OF THE CAR</small></span>' +
                '<input type="range" data-mix-weight="' + index + '" min="1" max="' + (100 - (rows.length - 1)) + '" step="1" value="' + entry.weight + '" aria-label="' + esc(info.name) + ' share of the material mix"' + (rows.length === 1 ? ' disabled' : '') + '>' +
                '<button type="button" data-mix-remove="' + index + '" title="Remove ' + esc(info.name) + '" aria-label="Remove ' + esc(info.name) + '">×</button>' +
                '</div>';
        });
        html += '<div class="spb-easy-mix-scale spb-easy-mix-strength"><label>HOW STRONG <b id="spbEasyWholeAmountValue">' + Math.round(wholeEffectAmount() * 100) + '%</b><small>Turn the whole look up or down. 100% is full strength.</small></label>' +
            '<input type="range" id="spbEasyWholeAmount" min="0" max="100" step="5" value="' + Math.round(wholeEffectAmount() * 100) + '"></div>' +
            '<div class="spb-easy-mix-scale"><label>HOW FINE <b id="spbEasyWholeScaleValue">' + Math.round(state.wholeScale * 100) + '%</b><small>Lower makes the pattern smaller and tighter on the car.</small></label>' +
            '<input type="range" id="spbEasyWholeScale" min="25" max="100" step="5" value="' + Math.round(state.wholeScale * 100) + '"></div>';
        return html;
    }

    function setWholeWeight(index, nextWeight) {
        var rows = normalizedWholeStack(state.wholeStack);
        if (!rows[index]) return rows;
        return rebalanceWholeShare(rows, index, nextWeight);
    }

    function syncWholeZoneFromState() {
        if (!hasWholeMaterialZone()) return false;
        var z = zones[0];
        var names = state.wholeStack.map(function (row) {
            var info = finishInfo(row.key, row.registryType);
            return info ? info.name : row.id;
        });
        z.name = 'Whole Car · ' + names.join(' + ');
        z.materialStack = state.wholeStack.map(function (row) {
            return { id: row.id, registryType: row.registryType, weight: row.weight };
        });
        z.materialStackMode = 'auto_trace';
        z.materialStackAmount = wholeEffectAmount();
        z.materialScale = state.wholeScale;
        return true;
    }

    function previewWholeState(debounced) {
        persistState();
        // A retired one-finish Whole Car zone remains untouched merely by
        // opening this screen. The first intentional slider move upgrades it
        // to the typed stack contract, preserving the same look and zone id.
        if (!syncWholeZoneFromState()) {
            applyWholeStack(false, !!debounced);
            return;
        }
        if (debounced) kickPreviewDebounced();
        else kickPreview();
    }

    function wireLights() {
        var host = $('spbEasyLights');
        if (!host) return;
        host.addEventListener('click', function (e) {
            var btn = e.target && e.target.closest ? e.target.closest('[data-light]') : null;
            if (!btn) return;
            var mode = btn.getAttribute('data-light');
            if (!LIGHT_MODES[mode] || mode === state.light) return;
            state.light = mode;
            persistState();
            Array.prototype.forEach.call(host.querySelectorAll('[data-light]'), function (b2) {
                b2.classList.toggle('on', b2.getAttribute('data-light') === mode);
            });
            renderWholeMaterialPreview();
        });
    }

    function wireWholeStack() {
        var host = $('spbEasyWholeStack');
        if (!host) return;
        host.addEventListener('pointerdown', function (e) {
            var input = e.target;
            if (!input || input.type !== 'range' || input._spbEasyUndoArmed) return;
            undoPush('Easy Mode: adjust Whole Car material mix');
            input._spbEasyUndoArmed = true;
        });
        host.addEventListener('keydown', function (e) {
            var input = e.target;
            if (!input || input.type !== 'range' || !/^(Arrow(Up|Down|Left|Right)|Home|End|PageUp|PageDown)$/.test(e.key)) return;
            if (input._spbEasyUndoArmed) return;
            undoPush('Easy Mode: adjust Whole Car material mix');
            input._spbEasyUndoArmed = true;
        });
        host.addEventListener('input', function (e) {
            var input = e.target;
            if (input && input.hasAttribute('data-mix-weight')) {
                var index = Number(input.getAttribute('data-mix-weight'));
                state.wholeStack = setWholeWeight(index, input.value);
                state.wholeStack.forEach(function (row, i) {
                    var slider = host.querySelector('[data-mix-weight="' + i + '"]');
                    var value = host.querySelector('[data-mix-value="' + i + '"]');
                    if (slider) slider.value = row.weight;
                    if (value) {
                        if (value.tagName === 'INPUT') { if (value !== input) value.value = row.weight; }
                        else value.textContent = row.weight + '%';
                    }
                });
                previewWholeState(true);
            } else if (input && input.id === 'spbEasyWholeAmount') {
                state.wholeAmount = Math.max(0, Math.min(1, Number(input.value) / 100));
                var amountEl = $('spbEasyWholeAmountValue');
                if (amountEl) amountEl.textContent = Math.round(wholeEffectAmount() * 100) + '%';
                previewWholeState(true);
            } else if (input && input.id === 'spbEasyWholeScale') {
                state.wholeScale = Math.max(0.25, Math.min(1, Number(input.value) / 100));
                var valueEl = $('spbEasyWholeScaleValue');
                if (valueEl) valueEl.textContent = Math.round(state.wholeScale * 100) + '%';
                previewWholeState(true);
            }
        });
        host.addEventListener('change', function (e) {
            var input = e.target;
            if (input && input.hasAttribute('data-mix-num')) {
                // Committed on change (blur / Enter / spinner), never per
                // keystroke: rebalancing on the "5" of "50" fights the typist.
                var idx = Number(input.getAttribute('data-mix-num'));
                var want = Math.round(Number(input.value));
                if (!isFinite(want)) { input.value = (state.wholeStack[idx] || {}).weight || 1; return; }
                undoPush('Easy Mode: set share to ' + want + '%');
                state.wholeStack = setWholeWeight(idx, want);
                state.wholeStack.forEach(function (row, i) {
                    var sl = host.querySelector('[data-mix-weight="' + i + '"]');
                    var nb = host.querySelector('[data-mix-value="' + i + '"]');
                    if (sl) sl.value = row.weight;
                    if (nb && nb.tagName === 'INPUT') nb.value = row.weight;
                });
                previewWholeState(true);
                refreshZonesUI();
                return;
            }
            if (!input || input.type !== 'range') return;
            input._spbEasyUndoArmed = false;
            refreshZonesUI();
        });
        host.addEventListener('click', function (e) {
            if (e.target && e.target.closest && e.target.closest('#spbEasyDemoDismiss')) {
                _demoNote = '';
                renderRail();
                return;
            }
            if (e.target && e.target.closest && e.target.closest('#spbEasyShowMap')) {
                toggleMaterialMap();
                return;
            }
            var preset = e.target && e.target.closest ? e.target.closest('[data-mix-preset]') : null;
            if (preset) { applyMixPreset(Number(preset.getAttribute('data-mix-preset'))); return; }
            var button = e.target && e.target.closest ? e.target.closest('[data-mix-remove]') : null;
            if (!button) return;
            var index = Number(button.getAttribute('data-mix-remove'));
            var removed = state.wholeStack[index];
            if (!removed) return;
            var info = finishInfo(removed.key, removed.registryType);
            undoPush('Easy Mode: remove ' + (info ? info.name : 'material'));
            state.wholeStack.splice(index, 1);
            state.wholeStack = normalizeWholeShares(state.wholeStack);
            if (state.wholeStack.length) applyWholeStack(false, false);
            else clearWholeMaterialZone();
            renderRail();
        });
        armLazyThumbs(host);
    }

    // Rebuilding a 2,187-row list on every keystroke janks — debounce it.
    var _searchTimer = null;
    function searchSoon() {
        if (_searchTimer) clearTimeout(_searchTimer);
        _searchTimer = setTimeout(function () { _searchTimer = null; renderFinishList(); }, 150);
    }

    // [2026-08-08 E42] The looks were loose buttons in a plain div, so a screen
    // reader announced each one as an isolated button with no idea how many
    // there were or where in the run you had got to. Wrapping each run in a
    // real list gives "list, 50 items" and "3 of 50" for free, computed by the
    // AT rather than hand-maintained. The wrapper is display:contents so the
    // rows remain the flex items they already were and nothing moves.
    function rowsListHtml(ids, label, selectedId) {
        var rows = ids.map(function (id) { return rowHtml(id, selectedId); }).join('');
        if (!rows) return '';
        return '<div class="spb-easy-rowlist" role="list"' +
            (label ? ' aria-label="' + esc(label) + '"' : '') + '>' + rows + '</div>';
    }

    function rowHtml(key, selectedKeys) {
        var f = finishInfo(key);
        if (!f) return '';
        var selected = Array.isArray(selectedKeys) ? selectedKeys : [selectedKeys];
        var applied = selected.indexOf(f.key) !== -1;
        var appliedCopy = state.view === 'whole' ? '✓ IN YOUR MIX' : '✓ ON YOUR COLOR';
        var typeTag = f.type === 'monolithic' ? '<i>SPECIAL</i>' : '';
        return '<span class="spb-easy-rowli" role="listitem">' +
            // [GAUNTLET A5 2026-08-20] The tile clamps its description to 2-3
            // lines, so the back half of a good description was unreachable
            // without applying the finish. A native title gives the full text on
            // hover AND on keyboard focus, costs no layout, and cannot reflow the
            // grid the way an expanding hover card would.
            '<button type="button" tabindex="-1" class="spb-easy-finish' + (applied ? ' selected' : '') + '" data-fkey="' + esc(f.key) + '" data-fid="' + esc(f.id) + '" data-ftype="' + f.type + '" title="' + esc(f.name + (f.desc ? ' — ' + f.desc : '')) + '" aria-pressed="' + (applied ? 'true' : 'false') + '">' +
            '<span class="spb-easy-fav' + (isFav(f.key) ? ' on' : '') + '" data-fav="' + esc(f.key) + '" role="button" tabindex="-1" title="' + (isFav(f.key) ? 'Remove from your favourites' : 'Save to your favourites') + '">' + (isFav(f.key) ? '\u2665' : '\u2661') + '</span>' +
            splitThumbHtml(f, '') +
            '  <span class="spb-easy-finish-text">' +
            '    <span class="spb-easy-finish-name">' + esc(f.name) + ' ' + typeTag + (applied ? ' <em>' + appliedCopy + '</em>' : '') + '</span>' +
            '    <span class="spb-easy-finish-desc">' + esc(f.desc) + '</span>' +
            '  </span>' +
            '</button></span>';
    }
    function matchesSearchAndTag(key) { return matchesTag(key) && matchesSearch(key); }

    // [GAUNTLET A3 2026-08-20] Buyers do not search our vocabulary, they search
    // theirs: "shiny", "flat", "rust", "stealth", "sparkle", "blacked out". The
    // old matcher was a single raw substring test over name+desc+id, so all of
    // those returned an empty catalog out of 2,834 finishes. This maps their
    // words onto ours. Every entry is one-directional and additive - a synonym
    // only ever WIDENS a result set, so nothing that used to be findable stops
    // being findable.
    var SEARCH_SYNONYMS = {
        shiny: ['gloss', 'mirror', 'chrome', 'wet', 'polish', 'lacquer', 'shine', 'reflect'],
        glossy: ['gloss', 'lacquer', 'wet', 'shine'],
        flat: ['matte', 'flat', 'satin', 'chalk', 'suede', 'primer'],
        matt: ['matte'],
        dull: ['matte', 'flat', 'primer', 'chalk'],
        stealth: ['matte', 'black', 'tactical', 'stealth', 'vanta', 'blackout'],
        blacked: ['black', 'blackout', 'vanta', 'piano'],
        murdered: ['black', 'blackout', 'vanta'],
        sparkle: ['flake', 'metallic', 'glitter', 'sparkle', 'chromatic'],
        sparkly: ['flake', 'metallic', 'glitter'],
        glitter: ['flake', 'glitter', 'sparkle', 'sequin'],
        rust: ['rust', 'patina', 'corrod', 'weather', 'oxidi', 'barn'],
        rusty: ['rust', 'patina', 'corrod', 'oxidi'],
        old: ['patina', 'weather', 'barn', 'aged', 'relic', 'grunge'],
        dirty: ['grunge', 'dirt', 'weather', 'patina', 'mud'],
        clean: ['gloss', 'foundation', 'satin', 'pure'],
        gold: ['gold', 'brass', 'bronze', 'gilt', 'amber'],
        silver: ['silver', 'chrome', 'alloy', 'steel', 'aluminium', 'aluminum', 'titanium'],
        copper: ['copper', 'bronze', 'rose'],
        metal: ['metal', 'alloy', 'steel', 'chrome', 'titanium', 'forge'],
        rainbow: ['prism', 'spectrum', 'iridesc', 'chameleon', 'holograph', 'opal', 'aurora'],
        oilslick: ['iridesc', 'opal', 'prism', 'chameleon'],
        colorshift: ['chameleon', 'shift', 'iridesc', 'prism', 'spectrum'],
        colorshift: ['chameleon', 'shift', 'iridesc', 'prism', 'spectrum'],
        glow: ['neon', 'glow', 'lumin', 'signal', 'aurora'],
        neon: ['neon', 'glow', 'signal', 'cyber'],
        camo: ['camo', 'camouflage', 'tactical', 'military'],
        military: ['tactical', 'camo', 'cerakote', 'military'],
        wood: ['wood', 'timber', 'oak', 'grain', 'natural'],
        stone: ['marble', 'onyx', 'stone', 'mineral', 'granite'],
        water: ['water', 'wave', 'flow', 'liquid', 'aqua', 'ocean'],
        fire: ['flame', 'fire', 'ember', 'ignite', 'molten', 'plasma'],
        space: ['cosmos', 'nebula', 'star', 'galax', 'astro'],
        ice: ['ice', 'frozen', 'frost', 'crystal', 'glacier'],
        carbon: ['carbon', 'weave', 'fiber', 'fibre', 'composite'],
        wrap: ['wrap', 'vinyl', 'satin', 'matte'],
        pearl: ['pearl', 'iridesc', 'shift', 'opal'],
        candy: ['candy', 'transparent', 'deep'],
        dark: ['black', 'dark', 'shadow', 'night', 'vanta'],
        bright: ['bright', 'white', 'neon', 'vivid'],
        pastel: ['pastel', 'soft', 'powder'],
        cheap: ['primer', 'flat', 'foundation'],
        expensive: ['chrome', 'candy', 'pearl', 'atelier', 'exotic'],
        fast: ['metallic', 'gloss', 'racing'],
        classic: ['gloss', 'metallic', 'foundation', 'sock', 'groovy'],
        retro: ['sock', 'groovy', 'vintage', 'classic', 'hop'],
        anime: ['anime', 'cel', 'manga'],
        japan: ['rising', 'sun', 'sakura', 'lacquer', 'dragon'],
        japanese: ['rising', 'sun', 'sakura', 'lacquer'],
        mexico: ['viva', 'mexico', 'talavera'],
        british: ['union', 'jack', 'british'],
        american: ['freedom', 'stars', 'stripes', 'usa'],
        usa: ['freedom', 'stars', 'stripes', 'american']
    };

    // One character deleted, inserted or swapped. Cheap enough to run over the
    // query's own words (never over the catalog) and it turns "chrom", "cadny"
    // and "metalic" from an empty catalog into the obvious answer.
    function _fuzzyVariants(word) {
        var out = [];
        if (word.length < 5) return out;
        for (var i = 0; i < word.length; i++) out.push(word.slice(0, i) + word.slice(i + 1));
        for (var j = 0; j < word.length - 1; j++) {
            out.push(word.slice(0, j) + word[j + 1] + word[j] + word.slice(j + 2));
        }
        // Missed double letter - by far the most common real typo in this
        // catalog's vocabulary ("metalic", "brilliant", "iridescent"). Deletion
        // and transposition cannot reach it; doubling each character can, for
        // only len(word) extra variants. MEASURED: "metalic" 0 -> 300+ hits.
        for (var k = 0; k < word.length; k++) {
            out.push(word.slice(0, k) + word[k] + word.slice(k));
        }
        return out;
    }

    var _searchTermsCache = { q: null, terms: null };
    function _searchTerms() {
        if (_searchTermsCache.q === _searchText) return _searchTermsCache.terms;
        var words = String(_searchText || '').split(/[^a-z0-9]+/).filter(Boolean);
        var terms = words.map(function (w) {
            var alts = [w];
            if (SEARCH_SYNONYMS[w]) alts = alts.concat(SEARCH_SYNONYMS[w]);
            // Trailing plural: "flakes" should find "flake".
            if (w.length > 3 && w.charAt(w.length - 1) === 's') alts.push(w.slice(0, -1));
            alts = alts.concat(_fuzzyVariants(w));
            return alts;
        });
        _searchTermsCache = { q: _searchText, terms: terms };
        return terms;
    }

    // [GAUNTLET A3d 2026-08-20] Relevance. A name hit is worth far more than a
    // description hit, an exact word is worth more than a synonym, and the whole
    // phrase landing in the name wins outright. Returns 0 for "does not match"
    // so the caller can use it as both filter and sort key.
    function searchScore(key) {
        if (!_searchText) return 1;
        var f = finishInfo(key);
        if (!f) return 0;
        var name = String(f.name || '').toLowerCase();
        var desc = String(f.desc || '').toLowerCase();
        var id = String(f.id || '').toLowerCase();
        var score = 0;
        // The name is the buyer's strongest signal. A phrase buried in prose is
        // the weakest - "matte black" appearing inside a Seismic Faultline
        // description must never outrank a finish actually CALLED Flat Black.
        if (name.indexOf(_searchText) !== -1) score += 1000;
        else if (desc.indexOf(_searchText) !== -1) score += 60;
        var terms = _searchTerms();
        var allInName = terms.length > 0;
        for (var i = 0; i < terms.length; i++) {
            var alts = terms[i], best = 0, inName = false;
            for (var j = 0; j < alts.length; j++) {
                var a = alts[j];
                if (!a) continue;
                var exact = (j === 0);   // alts[0] is the buyer's own word
                var nAt = name.indexOf(a);
                if (nAt !== -1) {
                    // Whole-word hits beat letters buried inside another word:
                    // "rust" should mean Rust, not Ember Crust / Frustule.
                    var whole = _wordBoundaryHit(name, a, nAt);
                    best = Math.max(best, (exact ? 120 : 60) + (whole ? 60 : 0));
                    inName = true;
                    continue;
                }
                if (desc.indexOf(a) !== -1) { best = Math.max(best, exact ? 25 : 8); continue; }
                if (id.indexOf(a) !== -1) { best = Math.max(best, exact ? 12 : 4); }
            }
            if (!best) return 0;      // every word still has to land somewhere
            if (!inName) allInName = false;
            score += best;
        }
        // Every word landed in the name: this is what the buyer meant.
        if (allInName) score += 400;
        return score || 1;
    }

    // True when `needle` sits at a word boundary inside `hay` at index `at`.
    function _wordBoundaryHit(hay, needle, at) {
        var before = at === 0 ? ' ' : hay.charAt(at - 1);
        var afterIdx = at + needle.length;
        var after = afterIdx >= hay.length ? ' ' : hay.charAt(afterIdx);
        return !/[a-z0-9]/.test(before) && !/[a-z0-9]/.test(after);
    }
    function matchesSearch(key) {
        if (!_searchText) return true;
        var f = finishInfo(key);
        if (!f) return false;
        var hay = (f.name + ' ' + f.desc + ' ' + f.id).toLowerCase();
        // Whole-phrase hit first: preserves the old behavior exactly, and keeps
        // "piano black" cheap when it really is a literal substring.
        if (hay.indexOf(_searchText) !== -1) return true;
        var terms = _searchTerms();
        if (!terms.length) return true;
        for (var i = 0; i < terms.length; i++) {
            var alts = terms[i], hit = false;
            for (var j = 0; j < alts.length; j++) {
                if (alts[j] && hay.indexOf(alts[j]) !== -1) { hit = true; break; }
            }
            if (!hit) return false;   // every word must land somewhere
        }
        return true;
    }
    function isBaseColorPicker() {
        return state.view === 'bycolor' && bc.pickerFor === 'borrow';
    }
    // [2026-08-08 E41] The look list had no keyboard story. Rows are <button>,
    // so Tab reached them and Enter applied them - but Tab reached EVERY one of
    // them, one at a time, plus a second stop for each row's favourite heart.
    // That is not navigation, it is a hostage situation.
    //
    // Roving focus: the list is ONE tab stop, arrows move inside it, Home/End
    // jump the ends. Enter/Space still apply (native button behavior).
    //
    // The heart also gets fixed here: it is a role="button" span with
    // tabindex="0" and a CLICK handler only, so it was focusable but NOT
    // operable - Enter on a focused heart did nothing at all.
    function visibleRows(host) {
        return Array.prototype.filter.call(
            host.querySelectorAll('.spb-easy-finish'),
            function (el) {
                // [GAUNTLET F3 2026-08-20] offsetParent stays non-null for
                // content inside a closed <details> (Chrome hides it with
                // content-visibility, not display:none), so collapsed families
                // were counted as navigable and arrow keys walked into tiles the
                // buyer could not see.
                try {
                    return el.checkVisibility({ checkVisibilityCSS: true, contentVisibilityAuto: true });
                } catch (e) { return el.offsetParent !== null; }
            });
    }

    // How many tiles sit on one visual row. In the browse grid this is however
    // many fit across; in the narrow single-column list it is 1, which makes the
    // grid maths collapse back to the old list behaviour for free.
    function _rowStride(rows) {
        if (rows.length < 2) return 1;
        var top0 = Math.round(rows[0].getBoundingClientRect().top);
        var count = 1;
        for (var i = 1; i < rows.length; i++) {
            if (Math.abs(Math.round(rows[i].getBoundingClientRect().top) - top0) > 4) break;
            count++;
        }
        return Math.max(1, count);
    }
    function focusRow(row, rows) {
        if (!row) return;
        (rows || []).forEach(function (r) { r.tabIndex = -1; });
        row.tabIndex = 0;
        try { row.focus({ preventScroll: true }); } catch (e) { try { row.focus(); } catch (e2) {} }
        try { row.scrollIntoView({ block: 'nearest' }); } catch (e) {}
    }
    function syncRovingFocus() {
        var host = els.finishes;
        if (!host) return;
        var rows = visibleRows(host);
        if (!rows.length) return;
        var current = host.querySelector('.spb-easy-finish.selected') || rows[0];
        rows.forEach(function (r) { r.tabIndex = (r === current) ? 0 : -1; });
    }

    function attachFinishListHandlers(host) {
        if (!host || host._spbEasyListWired) return;
        host._spbEasyListWired = true;
        host.addEventListener('keydown', function (e) {
            var target = e.target;
            if (!target || !target.closest) return;
            // Enter/Space on the favourite heart. It is a span, so the browser
            // does not do this for us the way it would for a real button.
            var fav = target.closest('[data-fav]');
            if (fav && (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar')) {
                e.preventDefault();
                e.stopPropagation();
                fav.click();
                return;
            }
            var row = target.closest('.spb-easy-finish');
            if (!row) return;
            var keys = { ArrowDown: 1, ArrowUp: 1, ArrowLeft: 1, ArrowRight: 1,
                         Home: 1, End: 1, PageDown: 1, PageUp: 1 };
            if (!keys[e.key]) return;
            e.preventDefault();
            e.stopPropagation();
            var rows = visibleRows(host);
            var i = rows.indexOf(row);
            if (i === -1) return;
            var next = i;
            var stride = _rowStride(rows);
            if (e.key === 'ArrowRight') next = Math.min(rows.length - 1, i + 1);
            else if (e.key === 'ArrowLeft') next = Math.max(0, i - 1);
            else if (e.key === 'ArrowDown') next = Math.min(rows.length - 1, i + stride);
            else if (e.key === 'ArrowUp') next = Math.max(0, i - stride);
            // PageUp/PageDown move a screenful, which in a grid is a few rows
            // rather than a fixed 8 tiles.
            else if (e.key === 'PageDown') next = Math.min(rows.length - 1, i + stride * 3);
            else if (e.key === 'PageUp') next = Math.max(0, i - stride * 3);
            else if (e.key === 'Home') next = 0;
            else if (e.key === 'End') next = rows.length - 1;
            focusRow(rows[next], rows);
        });
        host.addEventListener('click', function (e) {
            var like = e.target && e.target.closest ? e.target.closest('[data-like]') : null;
            if (like) {
                e.preventDefault(); e.stopPropagation();
                _likeKey = _likeKey ? '' : like.getAttribute('data-like');
                _filterTag = '';
                // [2026-08-08] "more like this" replaces the current query — a
                // leftover search term intersected the similar set to nothing
                // (measured: 0 results while a 'carbon' search was still live).
                _searchText = '';
                if (els.search) els.search.value = '';
                renderFinishList();
                return;
            }
            var tag = e.target && e.target.closest ? e.target.closest('[data-tag]') : null;
            if (tag) {
                e.preventDefault(); e.stopPropagation();
                var t = tag.getAttribute('data-tag');
                _filterTag = (t && t === _filterTag) ? '' : (t || '');
                _likeKey = '';
                renderFinishList();
                return;
            }
            var heart = e.target && e.target.closest ? e.target.closest('[data-fav]') : null;
            if (heart) {
                e.preventDefault(); e.stopPropagation();
                var on = toggleFav(heart.getAttribute('data-fav'));
                heart.classList.toggle('on', on);
                heart.textContent = on ? '\u2665' : '\u2661';
                heart.title = on ? 'Remove from your favourites' : 'Save to your favourites';
                return;
            }
            var row = e.target && e.target.closest ? e.target.closest('.spb-easy-finish') : null;
            if (row) onPickerRowClick(row.getAttribute('data-fkey'));
        });
    }

    // [2026-08-08 E38] The full catalogue put 2,252 rows / 2,252 <img> /
    // 26,812 nodes into a list box 340px tall - document nodes went 3,706 ->
    // 29,958, so the look list alone was 8x the entire rest of the app. The
    // sections are <details> and nearly all of them are CLOSED, so the browser
    // was building, laying out and keeping thousands of rows nobody could see.
    //
    // Rows are now built when a section is actually opened, and long sections
    // arrive a chunk at a time. Filtering and counting still run over the WHOLE
    // catalogue - only the DOM is windowed, so search results and the "N
    // MATCHES" figure are unchanged.
    var CATALOG_CHUNK = 100;
    var _secIds = {};          // section key -> the ids that passed the filter
    var _secLabels = {};       // section key -> its title, for the list label
    var _secShown = {};        // section key -> how many are currently in the DOM
    var _lastSelectedId = null;

    function sectionRowsHtml(key, upto) {
        var ids = _secIds[key] || [];
        var n = Math.min(upto, ids.length);
        var html = rowsListHtml(ids.slice(0, n), _secLabels[key] || 'Looks', _lastSelectedId);
        _secShown[key] = n;
        if (n < ids.length) {
            html += '<button type="button" class="spb-easy-more-rows" data-more="' + esc(key) + '">' +
                'SHOW ' + Math.min(CATALOG_CHUNK, ids.length - n) + ' MORE \u00b7 ' +
                (ids.length - n) + ' left</button>';
        }
        return html;
    }
    function fillSection(key) {
        var host = els.finishes ? els.finishes.querySelector('[data-rows="' + key + '"]') : null;
        if (!host || host.getAttribute('data-filled') === '1') return;
        host.setAttribute('data-filled', '1');
        host.innerHTML = sectionRowsHtml(key, CATALOG_CHUNK);
        armLazyThumbs(host);
        syncRovingFocus();
    }
    function growSection(key) {
        var host = els.finishes ? els.finishes.querySelector('[data-rows="' + key + '"]') : null;
        if (!host) return;
        host.innerHTML = sectionRowsHtml(key, (_secShown[key] || 0) + CATALOG_CHUNK);
        armLazyThumbs(host);
        syncRovingFocus();
    }
    function wireSectionLazyFill() {
        if (!els.finishes || els.finishes._spbSecWired) return;
        els.finishes._spbSecWired = true;
        // 'toggle' does not bubble, so listen in the CAPTURE phase - a capturing
        // listener on the ancestor still sees it on the way down.
        els.finishes.addEventListener('toggle', function (e) {
            var d = e.target;
            if (!d || d.tagName !== 'DETAILS' || !d.open) return;
            var key = d.getAttribute('data-sec');
            if (key) fillSection(key);
        }, true);
        els.finishes.addEventListener('click', function (e) {
            var more = e.target && e.target.closest ? e.target.closest('[data-more]') : null;
            if (!more) return;
            e.preventDefault();
            e.stopPropagation();
            growSection(more.getAttribute('data-more'));
        });
    }

    function renderFinishList() {
        if (!els.finishes) return;
        var basePicker = isBaseColorPicker();
        var zone = (bc.zoneIdx >= 0 && zones[bc.zoneIdx]) ? zones[bc.zoneIdx] : null;
        var selectedBase = basePicker && zone ? selectedBaseColorInfo(zone.baseColorSource) : null;
        var selectedId = basePicker ? (selectedBase && selectedBase.key)
            : (state.view === 'whole') ? state.wholeStack.map(function (row) { return row.key; })
            : zone ? (zone.finish ? finishKey('monolithic', zone.finish) : (zone.base ? finishKey('base', zone.base) : null)) : null;
        var html = '', shown = 0;
        if (!basePicker && _likeKey) {
            var refInfo = finishInfo(_likeKey);
            var likeIds = likeListIds(_likeKey, 60);
            shown = likeIds.length;
            html = '<div class="spb-easy-finish-group">\u2726 CLOSE TO ' +
                esc((refInfo ? refInfo.name : '').toUpperCase()) + ' <span>' + shown + ' similar</span></div>' +
                rowsListHtml(likeIds, 'Looks like the one you picked', selectedId);
            if (!shown) html = '<div class="spb-easy-finish-none">Nothing else in the catalog is close to that one.</div>';
        } else if (!basePicker && !_catalogMode && !_searchText && !_filterTag) {
            var ids = buildTopShelf();
            shown = ids.length;
            // [E11/E12] your hearts first, then what you used recently, then the shelf
            var favIds = favList().filter(function (k) { return !!finishInfo(k); });
            var recIds = recentList().filter(function (k) { return !!finishInfo(k) && favIds.indexOf(k) === -1; });
            html = '';
            if (favIds.length) {
                html += '<div class="spb-easy-finish-group">\u2665 YOUR FAVOURITES <span>' + favIds.length + ' saved</span></div>' +
                    rowsListHtml(favIds, 'Your favourites', selectedId);
                shown += favIds.length;
            }
            if (recIds.length) {
                html += '<div class="spb-easy-finish-group">\u23f1 RECENTLY USED <span>' + recIds.length + '</span></div>' +
                    rowsListHtml(recIds, 'Recently used', selectedId);
                shown += recIds.length;
            }
            var pickedRgb = currentPickedRgb();
            if (pickedRgb) {
                var fitIds = forColorIds(pickedRgb, 12).filter(function (id) {
                    return favIds.indexOf(id) === -1 && recIds.indexOf(id) === -1;
                });
                if (fitIds.length) {
                    var hex = (zones[bc.zoneIdx] && zones[bc.zoneIdx].pickerColor) || '';
                    html += '<div class="spb-easy-finish-group">\u2605 FOR THIS COLOR ' +
                        (hex ? '<i class="spb-easy-fitchip" style="--fit-color:' + esc(hex) + '"></i>' : '') +
                        ' <span>' + fitIds.length + ' picks that suit it</span></div>' +
                        rowsListHtml(fitIds, 'Picks that suit the color you chose', selectedId);
                    shown += fitIds.length;
                }
            }
            // [SPB-105 review remediation 2026-08-22] "Featured" now means
            // scorecard-cleared (>= owner ship bar, not FIX), and collections
            // lead the generic shelf so they reduce rather than add decisions.
            (function () {
                var seen = {};
                favIds.concat(recIds).forEach(function (k) { seen[k] = 1; });
                var featuredSeen = {};
                var sections = buildCatalogSections();
                [
                    { tag: 'candy',   title: '◆ CANDY & PEARL PICKS', sub: 'deep color that shifts as the car turns' },
                    { tag: 'pattern', title: '◆ PATTERNED PICKS',     sub: 'art baked right into the paint' },
                    { tag: 'dark',    title: '◆ STEALTH PICKS',       sub: 'murdered-out dark looks' },
                ].forEach(function (coll) {
                    var def = FILTER_TAGS.filter(function (t) { return t.key === coll.tag; })[0];
                    if (!def) return;
                    var collIds = [];
                    sections.some(function (sec) {
                        sec.ids.some(function (id) {
                            if (seen[id] || !easyFeaturedQualityEligible(id)) return false;
                            var subj = _tagSubject(id);
                            if (!(subj && def.test(subj))) return false;
                            seen[id] = 1;
                            featuredSeen[id] = 1;
                            collIds.push(id);
                            return collIds.length >= 8;
                        });
                        return collIds.length >= 8;
                    });
                    if (collIds.length < 4) return;
                    html += '<div class="spb-easy-finish-group">' + coll.title +
                        ' <span>' + esc(coll.sub) + '</span>' +
                        '<button type="button" data-tag="' + coll.tag + '" ' +
                        'style="float:right;margin-left:auto;background:transparent;border:1px solid rgba(0,229,255,0.35);border-radius:6px;color:#7fdfff;font-size:10px;padding:2px 9px;cursor:pointer;letter-spacing:0.05em;" ' +
                        'title="Show every ' + esc(coll.title.replace(/^◆ /, '').toLowerCase()) + ' look in the catalog">SEE ALL →</button></div>' +
                        rowsListHtml(collIds, coll.title, selectedId);
                    shown += collIds.length;
                });
                var starterIds = ids.filter(function (id) {
                    return !featuredSeen[id] && favIds.indexOf(id) === -1 && recIds.indexOf(id) === -1;
                });
                if (starterIds.length) {
                    html += '<div class="spb-easy-finish-group">STARTER SHELF <span>' + starterIds.length + ' hand-picked</span></div>' +
                        rowsListHtml(starterIds, 'Starter shelf', selectedId);
                    shown += starterIds.length;
                }
            })();
        } else if (!basePicker && (_searchText || _filterTag)) {
            // [GAUNTLET A3c 2026-08-20] FILTERING, not browsing: one flat grid.
            // The family accordions are the right shape for exploring the
            // catalog and the wrong shape for looking something up - 79 matches
            // spread over 20 families is 20 headers, 20 descriptions and a lot
            // of empty row. Flattened and de-duplicated (a look can be
            // cross-listed in two families), capped so a two-letter query cannot
            // build a 2,000-tile DOM.
            var FLAT_CAP = 200;
            var flatSeen = {}, flatIds = [];
            buildCatalogSections().forEach(function (sec) {
                sec.ids.forEach(function (id) {
                    if (flatSeen[id]) return;
                    var info = finishInfo(id);
                    if (!info) return;
                    if (!matchesSearchAndTag(id)) return;
                    flatSeen[id] = 1;
                    flatIds.push(id);
                });
            });
            shown = flatIds.length;
            if (_searchText) {
                // Stable decorate-sort-undecorate: equal scores keep catalog
                // order, so the shelf's own curation still shows through.
                flatIds = flatIds.map(function (id, i) { return { id: id, s: searchScore(id), i: i }; })
                    .sort(function (a, b) { return (b.s - a.s) || (a.i - b.i); })
                    .map(function (r) { return r.id; });
            }
            var capped = flatIds.slice(0, FLAT_CAP);
            var lbl2 = _filterTag ? (FILTER_TAGS.filter(function (t) { return t.key === _filterTag; })[0] || {}).label : '';
            if (shown) {
                html = '<div class="spb-easy-finish-group">\u2315 ' + shown + ' MATCH' + (shown === 1 ? '' : 'ES') +
                    ' <span>' + (_searchText ? ('for \u201c' + esc(_searchText) + '\u201d') : '') +
                    (_searchText && lbl2 ? ' + ' : '') + (lbl2 ? esc(lbl2) : '') +
                    (shown > FLAT_CAP ? (' \u00b7 showing the first ' + FLAT_CAP) : '') +
                    '</span></div>' + rowsListHtml(capped, 'Search results', selectedId);
            } else {
                // [GAUNTLET A6 2026-08-20] A dead end needs a door. Offer real,
                // clickable starting points instead of one gray apology - these
                // are the words the synonym table is strongest on, so every one
                // of them lands on a full grid.
                var ideas = ['chrome', 'matte black', 'candy', 'carbon', 'gold', 'rust', 'stealth', 'rainbow'];
                html = '<div class="spb-easy-finish-none"><b>Nothing matches ' +
                    (_searchText ? ('\u201c' + esc(_searchText) + '\u201d') : 'that filter') + '</b>' +
                    (_filterTag ? '<span>Tap the filter chip again to clear it.</span>' : '<span>Try one of these instead:</span>') +
                    '<span class="spb-easy-none-ideas">' +
                    ideas.map(function (w) {
                        return '<button type="button" class="spb-easy-none-idea" data-try="' + esc(w) + '">' + esc(w) + '</button>';
                    }).join('') +
                    '</span></div>';
            }
        } else {
            var parts = [], searchSeen = {};
            _secIds = {}; _secShown = {}; _secLabels = {};
            _lastSelectedId = selectedId;
            buildCatalogSections().forEach(function (sec) {
                var ids = sec.ids.filter(function (id) {
                    var info = finishInfo(id);
                    // [2026-08-08 E38] An id with no info renders as an empty
                    // string (rowHtml bails), so counting it inflates the
                    // section header and the match total. MEASURED: a section
                    // advertising "593 looks" could only produce 44 rows out of
                    // its first 100 ids. The old code only applied this test in
                    // the base picker, so every other list has been counting
                    // looks it cannot show.
                    if (!info) return false;
                    return (!basePicker || info.type === 'base' || info.type === 'monolithic') &&
                        matchesSearchAndTag(id);
                }).filter(function (id) {
                    // Cross-listing a look in two browse families is useful,
                    // but showing the identical button twice in one search
                    // result looks broken and makes keyboard choice ambiguous.
                    if (!_searchText) return true;
                    if (searchSeen[id]) return false;
                    searchSeen[id] = true;
                    return true;
                });
                if (!ids.length) return;
                shown += ids.length;
                var selectedList = Array.isArray(selectedId) ? selectedId : [selectedId];
                var open = !!_searchText || ids.some(function (key) { return selectedList.indexOf(key) !== -1; });
                var secKey = 'sec' + parts.length;
                _secIds[secKey] = ids;
                _secLabels[secKey] = sec.title;
                _secShown[secKey] = 0;
                // [GAUNTLET A1 2026-08-20] A collapsed family used to be a line of
                // text. Five real paint|spec chips make the row scannable, so the
                // FULL CATALOG reads like shelves instead of a table of contents.
                // data-peek marks them for the lazy loader (see lazyThumbPass) -
                // a closed family's ROWS are invisible, but its preview is not.
                var peek = ids.slice(0, 5).map(function (pid) {
                    var pinfo = finishInfo(pid);
                    if (!pinfo) return '';
                    return '<span class="spb-easy-secchip"><img alt="" loading="lazy" decoding="async" data-peek="1" data-src="' +
                        esc(thumbUrl(pinfo)) + '"></span>';
                }).join('');
                parts.push('<details class="spb-easy-finish-section" data-sec="' + secKey + '"' + (open ? ' open' : '') + '>' +
                    '<summary><span><b>' + esc(sec.title) + '</b><small>' + esc(categoryDescription(sec.title)) + '</small></span>' +
                    '<span class="spb-easy-secpreview" aria-hidden="true">' + peek + '</span>' +
                    '<em>' + ids.length + ' looks</em></summary>' +
                    '<div class="spb-easy-finish-section-rows" data-rows="' + secKey + '">' +
                    (open ? sectionRowsHtml(secKey, CATALOG_CHUNK) : '') + '</div></details>');
            });
            html = parts.join('');
            // [E15] a search that returns 600 rows should say so
            if (shown && (_searchText || _filterTag)) {
                var lbl = _filterTag ? (FILTER_TAGS.filter(function (t) { return t.key === _filterTag; })[0] || {}).label : '';
                html = '<div class="spb-easy-finish-group">\u2315 ' + shown + ' MATCH' + (shown === 1 ? '' : 'ES') +
                    ' <span>' + (_searchText ? ('for “' + esc(_searchText) + '”') : '') +
                    (_searchText && lbl ? ' + ' : '') + (lbl ? esc(lbl) : '') + '</span></div>' + html;
            }
            if (!shown) html = '<div class="spb-easy-finish-none">Nothing matches ' +
                (_searchText ? ('“' + esc(_searchText) + '”') : 'that filter') +
                (_filterTag ? ' with this filter on. Tap the filter again to clear it.' : '. Try a color name, candy, metal, chrome, or pearl.') + '</div>';
        }
        els.finishes.innerHTML = (basePicker ? '' : filterChipsHtml()) + html;
        Array.prototype.forEach.call(
            els.finishes.querySelectorAll('details[open] > [data-rows]'),
            function (node) { node.setAttribute('data-filled', '1'); });
        wireSectionLazyFill();
        syncRovingFocus();
        els.finishes.scrollTop = 0;
        if (els.catalogToggle) {
            if (basePicker) {
                els.catalogToggle.textContent = 'ALL ' + baseCatalogTotal() + ' COLORS';
                els.catalogToggle.disabled = true;
            } else {
                els.catalogToggle.disabled = false;
                els.catalogToggle.textContent = (_catalogMode || _searchText)
                    ? '← STARTER SHELF'
                    : 'FULL CATALOG (' + nfmt(catalogTotal()) + ')';
            }
        }
        armLazyThumbs(els.finishes);
        // [GAUNTLET A6 2026-08-20] The clear-× is positioned to the left of the
        // catalog toggle, whose width changes with its own label ("FULL CATALOG
        // (2,834)" vs "← STARTER SHELF"). A hard-coded offset would drift
        // every time that label flips, so publish the real measured width.
        try {
            var tgl = els.catalogToggle, fnd = tgl && tgl.parentNode;
            if (tgl && fnd && fnd.style) {
                fnd.style.setProperty('--spb-cat-toggle-w', Math.round(tgl.getBoundingClientRect().width) + 'px');
            }
        } catch (e) {}
    }
    function updateSelectionUI() {
        if (!els.finishes) return;
        var zone = (bc.zoneIdx >= 0 && zones[bc.zoneIdx]) ? zones[bc.zoneIdx] : null;
        var baseInfo = isBaseColorPicker() && zone ? selectedBaseColorInfo(zone.baseColorSource) : null;
        var selectedId = baseInfo ? [baseInfo.key] : (state.view === 'whole')
            ? state.wholeStack.map(function (row) { return row.key; })
            : zone ? [zone.finish ? finishKey('monolithic', zone.finish) : (zone.base ? finishKey('base', zone.base) : '')] : [];
        Array.prototype.forEach.call(els.finishes.querySelectorAll('.spb-easy-finish'), function (row) {
            var is = selectedId.indexOf(row.getAttribute('data-fkey')) !== -1;
            row.classList.toggle('selected', is);
            row.setAttribute('aria-pressed', is ? 'true' : 'false');
            var name = row.querySelector('.spb-easy-finish-name');
            if (name) {
                var em = name.querySelector('em');
                if (is && !em) name.insertAdjacentHTML('beforeend', ' <em>' + (state.view === 'whole' ? '✓ IN YOUR MIX' : '✓ ON YOUR COLOR') + '</em>');
                else if (!is && em) em.remove();
            }
        });
    }

    function onPickerRowClick(key) {
        // [GAUNTLET F1 2026-08-20] With no paint loaded the catalog stayed fully
        // interactive: 50 tappable finishes that could not go anywhere. Browsing
        // before you load a car is genuinely useful (window shopping 2,834
        // finishes), so this does NOT block the catalog — it just stops the tap
        // being a silent no-op and hands the buyer the one control they need.
        if (!paintLoaded()) {
            var info = finishInfo(key);
            try {
                if (window.showToast) {
                    window.showToast('Load your car first, then ' +
                        (info ? '“' + info.name + '”' : 'that finish') + ' goes straight on it', 'info');
                }
            } catch (e) {}
            var openBtn = $('spbEasyOpenPaint');
            if (openBtn) { try { openBtn.focus({ preventScroll: false }); } catch (e) { try { openBtn.focus(); } catch (e2) {} } }
            return;
        }
        noteRecentLook(key);
        if (state.view === 'whole') { addWholeMaterial(key); return; }
        if (state.view === 'bycolor') {
            if (bc.pickerFor === 'borrow') setZoneBorrowedColors(bc.zoneIdx, key);
            else setZoneFinish(bc.zoneIdx, key);
        }
    }

    function readWholeMaterialPlan() {
        try {
            if (!Array.isArray(zones) || zones.length !== 1) return null;
            var z = zones[0];
            if (!z || z.color !== 'everything') return null;
            var stack = Array.isArray(z.materialStack) ? z.materialStack : (Array.isArray(z.material_stack) ? z.material_stack : []);
            if (!stack.length) return null;
            var rows = normalizeWholeShares(stack.map(function (entry) {
                var type = entry && (entry.registryType || entry.registry_type || entry.type);
                return {
                    key: finishKey(type, entry && entry.id),
                    id: entry && entry.id,
                    registryType: type,
                    weight: entry && entry.weight,
                };
            }));
            if (!rows.length) return null;
            var amount = Number(z.materialStackAmount ?? z.material_stack_amount ?? 1);
            var scale = Number(z.materialScale ?? z.material_scale ?? 1);
            return {
                rows: rows,
                amount: Number.isFinite(amount) ? Math.max(0, Math.min(1, amount)) : 1,
                scale: Number.isFinite(scale) ? Math.max(0.25, Math.min(1, scale)) : 1,
            };
        } catch (e) { return null; }
    }

    function readLegacyWholeMaterialPlan() {
        try {
            if (!Array.isArray(zones) || zones.length !== 1) return null;
            var z = zones[0];
            if (!z || z.color !== 'everything') return null;
            var stack = Array.isArray(z.materialStack) ? z.materialStack : z.material_stack;
            if (Array.isArray(stack) && stack.length) return null;
            if ((z.pattern || 'none') !== 'none') return null;
            var key = z.finish ? finishKey('monolithic', z.finish) : (z.base ? finishKey('base', z.base) : '');
            var info = key ? finishInfo(key) : null;
            if (!info) return null;
            return {
                rows: [{ key: info.key, id: info.id, registryType: info.type, weight: 100 }],
                amount: 1,
                scale: Math.max(0.25, Math.min(1, Number(z.materialScale ?? z.material_scale ?? 1) || 1)),
                legacy: true,
            };
        } catch (e) { return null; }
    }

    function hydrateWholeState(plan) {
        if (!plan || !Array.isArray(plan.rows) || !plan.rows.length) return false;
        state.wholeStack = normalizeWholeShares(plan.rows);
        state.wholeAmount = Math.max(0, Math.min(1, Number(plan.amount) || 0));
        state.wholeScale = Math.max(0.25, Math.min(1, Number(plan.scale) || 1));
        return true;
    }

    function detectWholeApplied() {
        try {
            var plan = readWholeMaterialPlan() || readLegacyWholeMaterialPlan();
            if (plan && plan.rows.length) return plan.rows[0].key;
            return null;
        } catch (e) { return null; }
    }

    function hasWholeMaterialZone() {
        return !!readWholeMaterialPlan();
    }

    function addWholeMaterial(key) {
        var info = finishInfo(key);
        if (!info) return;
        var existing = state.wholeStack.findIndex(function (row) { return row.key === info.key; });
        if (existing !== -1) {
            var existingRow = $('spbEasyWholeStack') && $('spbEasyWholeStack').querySelector('[data-mix-key="' + info.key + '"]');
            if (existingRow) {
                existingRow.classList.remove('pulse');
                void existingRow.offsetWidth;
                existingRow.classList.add('pulse');
                try { existingRow.scrollIntoView({ block: 'nearest' }); } catch (e) {}
            }
            var already = $('spbEasyMixNotice');
            if (already) already.textContent = info.name + ' is already in your mix. Use its slider above.';
            return;
        }
        if (state.wholeStack.length >= 4) {
            var full = $('spbEasyMixNotice');
            if (full) full.textContent = 'Your four material slots are full. Remove one above before adding another.';
            return;
        }
        undoPush('Easy Mode: add ' + info.name + ' to Whole Car mix');
        var old = normalizeWholeShares(state.wholeStack);
        if (!old.length) {
            old = [{ key: info.key, id: info.id, registryType: info.type, weight: 100 }];
        } else {
            // Give the new material a fair share while preserving the user's
            // existing recipe ratio. The complete blend always remains 100%.
            var newShare = Math.round(100 / (old.length + 1));
            old = allocateWholeShares(old, 100 - newShare);
            old.push({ key: info.key, id: info.id, registryType: info.type, weight: newShare });
        }
        state.wholeStack = normalizeWholeShares(old);
        applyWholeStack(false, false);
        renderRail();
    }

    function clearWholeMaterialZone() {
        try {
            zones = [{
                id: (typeof _newZoneId === 'function') ? _newZoneId() : 'easy_whole_empty',
                name: 'Original Paint (no Whole Car material yet)',
                color: null, colorMode: 'none', base: null, finish: null, pattern: 'none',
                intensity: '100', colors: [], regionMask: null, patternStack: []
            }];
            selectedZoneIndex = 0;
        } catch (e) {}
        persistState();
        refreshZonesUI();
        kickPreview();
        syncStage();
    }

    // SPB-EASY-WHOLE-MIX-20260721 — owner asked for one-to-four Whole Car
    // finishes with individual sliders and automatic placement. This is a
    // first-class, typed Spec Sculpt catalog stack. The engine's fast trace
    // analyzes the livery, returns SPEC ONLY, and the standard preview/save
    // path therefore preserves source paint byte-for-byte.
    function applyWholeStack(recordUndo, debounced, skipPreview) {
        state.wholeStack = normalizeWholeShares(state.wholeStack);
        // A map of the OLD mix over the new one would be a lie; drop it and let
        // the buyer ask again (the answer is one click and ~1s away).
        if (_mapState.key && _mapState.key !== mapKeyForStack(normalizedWholeStack(state.wholeStack))) {
            _mapState.png = ''; _mapState.rows = []; _mapState.key = '';
            paintMapOverlay();
        }
        if (!state.wholeStack.length) { clearWholeMaterialZone(); return; }
        var names = state.wholeStack.map(function (row) {
            var info = finishInfo(row.key, row.registryType);
            return info ? info.name : row.id;
        });
        if (recordUndo) undoPush('Easy Mode Whole Car: ' + names.join(' + '));
        var z = {
            id: (hasWholeMaterialZone() || readLegacyWholeMaterialPlan()) ? zones[0].id : ((typeof _newZoneId === 'function') ? _newZoneId() : 'easy_whole_material_mix'),
            name: 'Whole Car · ' + names.join(' + '),
            color: 'everything',
            colorMode: 'special',
            base: null,
            pattern: 'none',
            finish: null,
            intensity: '100',
            customSpec: null, customPaint: null, customBright: null,
            pickerColor: '#3366ff', pickerTolerance: TOL_DEFAULT,
            colors: [], regionMask: null,
            lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
            patternStack: [],
            materialStack: state.wholeStack.map(function (row) {
                return { id: row.id, registryType: row.registryType, weight: row.weight };
            }),
            materialStackMode: 'auto_trace',
            materialStackAmount: wholeEffectAmount(),
            materialScale: state.wholeScale,
            hardEdge: true,
        };
        try {
            zones = [z];
            selectedZoneIndex = 0;
            if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'easy-mode whole-car material stack');
        } catch (e) {
            try { console.error('[spbEasy] applyWholeStack failed:', e); } catch (e2) {}
            return;
        }
        persistState();
        refreshZonesUI();
        if (!skipPreview) {
            if (debounced) kickPreviewDebounced();
            else kickPreview();
        }
        updateSelectionUI();
        syncStage();
        refreshSaveEls();
    }

    // [2026-08-08 E36] A buyer who has never seen the app has to make a choice
    // before they can see ANY result, which is the wrong order: they do not yet
    // know what the choices mean. One click now builds a finished, deliberately
    // good two-material car and then says what it did and how to change it.
    // Not SURPRISE ME (that is one random material) - this is a worked example.
    var _demoNote = '';
    function demoPair() {
        var ids = buildTopShelf();
        if (!ids.length) return null;
        var infos = ids.map(function (k) { return finishInfo(k); }).filter(Boolean);
        if (infos.length < 2) return null;
        function firstMatching(re, skipKey) {
            for (var i = 0; i < infos.length; i++) {
                if (skipKey && infos[i].key === skipKey) continue;
                if (re.test(infos[i].name || '')) return infos[i];
            }
            return null;
        }
        // A blend only reads as a blend if the two materials disagree: something
        // bright and reflective against something flat and textured.
        var shiny = firstMatching(/chrome|mirror|candy|pearl|gloss|metal/i) || infos[0];
        var flat = firstMatching(/carbon|matte|satin|weave|forge|stone|brush/i, shiny.key) ||
                   infos.find(function (i2) { return i2.key !== shiny.key; });
        if (!flat) return null;
        return { shiny: shiny, flat: flat };
    }
    function showExample() {
        var pair = demoPair();
        if (!pair) {
            try { if (window.showToast) window.showToast('The look library is still loading — try again in a second', 'info'); } catch (e) {}
            return false;
        }
        undoPush('Easy Mode: show me an example');
        state.view = 'whole';
        state.wholeStack = [
            { key: pair.shiny.key, id: pair.shiny.id, registryType: pair.shiny.type, weight: 70 },
            { key: pair.flat.key, id: pair.flat.id, registryType: pair.flat.type, weight: 30 }
        ];
        state.wholeAmount = 1.0;
        _demoNote = '70% ' + pair.shiny.name + ' + 30% ' + pair.flat.name;
        applyWholeStack(false, false);
        renderRail();
        return true;
    }
    function demoNoteHtml() {
        if (!_demoNote) return '';
        return '<div class="spb-easy-demo-note" id="spbEasyDemoNote">' +
            '<b>\u{1F440} THIS IS AN EXAMPLE</b>' +
            '<span>Shokker built you a <b>' + esc(_demoNote) + '</b> blend so you can see what a ' +
            'finished car looks like. Nothing is locked: drag the shares, swap either material, ' +
            'or hit START OVER and build your own.</span>' +
            '<button type="button" id="spbEasyDemoDismiss" aria-label="Hide this note">\u2715</button>' +
            '</div>';
    }

    function surprise() {
        if (state.view !== 'whole') { state.view = 'whole'; renderRail(); }
        var ids = buildTopShelf();
        if (!ids.length) return;
        var current = state.wholeStack.length === 1 ? state.wholeStack[0].key : '';
        var pick = current;
        for (var t = 0; t < 8 && pick === current; t++) pick = ids[Math.floor(Math.random() * ids.length)];
        var info = finishInfo(pick);
        if (!info) return;
        undoPush('Easy Mode: surprise Whole Car material');
        state.wholeStack = [{ key: info.key, id: info.id, registryType: info.type, weight: 100 }];
        state.wholeAmount = 1.0;
        applyWholeStack(false, false);
        renderRail();
        var row = els.finishes ? els.finishes.querySelector('.spb-easy-finish[data-fkey="' + pick + '"]') : null;
        if (row && row.scrollIntoView) { try { row.scrollIntoView({ block: 'nearest' }); } catch (e) {} }
    }

    // --- BY COLOR -------------------------------------------------------------
    function isEasyColorZone(z) {
        return !!(z && z.colorMode === 'picker' && /^Color \d+$/.test(z.name || ''));
    }
    function easyColorZones() {
        try { return zones.map(function (z, i) { return { z: z, i: i }; }).filter(function (p) { return isEasyColorZone(p.z); }); }
        catch (e) { return []; }
    }

    function enterByColor() {
        _carFilterQuery = '';
        state.view = 'bycolor';
        // Starting a by-numbers session over a non-by-numbers design would be
        // confusing — reset to a clean sheet (undo-able) unless we're resuming
        // an existing by-color session. NOTE: zones can never go fully empty —
        // renderZones() auto-restores the last saved design when length===0
        // (verified live 2026-07-16) — so the clean sheet is ONE inert
        // placeholder zone (color:null renders nothing; buildServerZones
        // filters it out).
        if (!easyColorZones().length) {
            undoPush('Easy Mode: start By Color');
            try {
                zones = [{
                    id: (typeof _newZoneId === 'function') ? _newZoneId() : 'easy_untouched',
                    name: 'Original Paint (untouched)',
                    color: null, colorMode: 'none',
                    base: null, pattern: 'none', finish: null,
                    intensity: '100',
                    customSpec: null, customPaint: null, customBright: null,
                    pickerColor: '#3366ff', pickerTolerance: TOL_DEFAULT,
                    colors: [], regionMask: null,
                    lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
                    patternStack: [],
                }];
                selectedZoneIndex = 0;
            } catch (e) {}
            refreshZonesUI();
            kickPreview();
        }
        bc = { phase: 'pick', zoneIdx: -1, pickerFor: 'finish', recolorOpen: false };
        renderRail();
    }

    function renderByColorRail() {
        var zlist = easyColorZones();
        var chips = zlist.map(function (p) {
            var f = (p.z.finish || p.z.base) ? finishInfo(p.z.finish || p.z.base) : null;
            return '<div class="spb-easy-zchip' + (p.i === bc.zoneIdx ? ' current' : '') + '" data-zi="' + p.i + '">' +
                '<span class="spb-easy-zchip-swatch" style="background:' + esc(p.z.pickerColor || '#888') + '"></span>' +
                '<span class="spb-easy-zchip-text">' + esc(f ? f.name : 'NEEDS A FINISH') + '</span>' +
                '<button type="button" class="spb-easy-zchip-x" data-zx="' + p.i + '" aria-label="Remove ' + esc(f ? f.name : 'unfinished color') + '" title="Remove this color">×</button></div>';
        }).join('');
        var stepHtml = '';
        if (bc.phase === 'pick') {
            stepHtml = '<div class="spb-easy-bc-card"><div class="spb-easy-bc-title">🎯 Click one color on SOURCE</div>' +
                '<div class="spb-easy-bc-copy">Pick the painted color you want to work on. SOURCE stays untouched; LIVE PREVIEW and the four spec channels show every decision.</div>' +
                '<button type="button" class="spb-easy-bc-primary" id="spbEasyAutoFind" title="Let Shokker read the paint and add its main colors for you">\u2728 FIND MY COLORS FOR ME</button>' +
                (zlist.length ? '<button type="button" class="spb-easy-bc-secondary" id="spbEasyBcCancelPick">Never mind — back to my colors</button>' : '') + '</div>';
        } else if (bc.phase === 'color') {
            var z = zones[bc.zoneIdx] || {};
            var recolor = !!bc.recolorOpen || z.baseColorMode === 'solid' || z.baseColorMode === 'special';
            var baseMode = z.baseColorMode === 'special';
            stepHtml = '<div class="spb-easy-bc-card">' +
                '<div class="spb-easy-bc-eyebrow">FIRST QUESTION</div>' +
                '<div class="spb-easy-bc-title"><span class="spb-easy-zchip-swatch" style="background:' + esc(z.pickerColor || '#888') + '"></span> Keep this color or change it?</div>' +
                // [GAUNTLET E3 2026-08-20] A click that lands on a stripe or a
                // logo edge can select 2-4% of the car. The buyer then applies a
                // finish, sees almost nothing change, and concludes the app is
                // broken. Say it plainly at the moment it happens, and name the
                // control that fixes it — Color reach is right below this card.
                (function () {
                    var cov = coveragePct(z.color && z.color.color_rgb,
                                          z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT);
                    if (cov == null || cov > 6) return '';
                    return '<div class="spb-easy-bc-tiny">⚠ That is only about <b>' + cov +
                        '% of the car</b> — you may barely see it. Slide <b>Color reach</b> up to catch ' +
                        'more shades of it, or click a bigger area on your paint.</div>';
                })() +
                '<div class="spb-easy-bc-choice spb-easy-bc-big-choice">' +
                '<button type="button" class="spb-easy-bc-secondary' + (!recolor ? ' on' : '') + '" id="spbEasyKeepColor">KEEP MY COLOR<small>material only</small></button>' +
                '<button type="button" class="spb-easy-bc-secondary' + (recolor ? ' on' : '') + '" id="spbEasyRecolor">CHANGE THE COLOR<small>then add a material</small></button></div>' +
                '<div class="spb-easy-recolor" id="spbEasyRecolorPanel"' + (recolor ? '' : ' hidden') + '>' +
                '<div class="spb-easy-bc-choice"><button type="button" id="spbEasySolidMode" class="spb-easy-bc-secondary' + (!baseMode ? ' on' : '') + '">SOLID COLOR</button>' +
                '<button type="button" id="spbEasyBaseMode" class="spb-easy-bc-secondary' + (baseMode ? ' on' : '') + '">COLOR BY BASE TYPE</button></div>' +
                '<div class="spb-easy-color-source" id="spbEasySolidPanel"' + (baseMode ? ' hidden' : '') + '><label>New solid color<input type="color" id="spbEasyRecolorHex" value="' + esc(/^#[0-9a-fA-F]{6}$/.test(z.baseColor || '') ? z.baseColor : (z.pickerColor || '#2255cc')) + '"></label></div>' +
                '<div class="spb-easy-color-source" id="spbEasyBasePanel"' + (!baseMode ? ' hidden' : '') + '>' + baseColorChoiceHtml(z.baseColorSource) + '</div>' +
                '<div class="spb-easy-tol-row"><label>Hue <b id="spbEasyHueVal">' + esc(z.baseHueOffset || 0) + '</b></label><input type="range" id="spbEasyHue" min="-180" max="180" value="' + esc(z.baseHueOffset || 0) + '"></div>' +
                '<div class="spb-easy-tol-row"><label>Saturation <b id="spbEasySatVal">' + esc(z.baseSaturationAdjust || 0) + '</b></label><input type="range" id="spbEasySat" min="-100" max="100" value="' + esc(z.baseSaturationAdjust || 0) + '"></div>' +
                '<div class="spb-easy-tol-row"><label>Brightness <b id="spbEasyBrtVal">' + esc(z.baseBrightnessAdjust || 0) + '</b></label><input type="range" id="spbEasyBrt" min="-100" max="200" value="' + esc(z.baseBrightnessAdjust || 0) + '"></div>' +
                '<div class="spb-easy-tol-row"><label>Color scale <b id="spbEasyColorScaleVal">' + esc((z.baseColorScale || 1).toFixed ? (z.baseColorScale || 1).toFixed(2) : '1.00') + '×</b></label><input type="range" id="spbEasyColorScale" min="0.25" max="4" step="0.05" value="' + esc(z.baseColorScale || 1) + '"></div>' +
                '<div class="spb-easy-bc-copy">Color scale changes the size of authored base-color texture. Hue, saturation and brightness tune either color choice live.</div>' +
                '<button type="button" class="spb-easy-bc-primary" id="spbEasyColorNext">NEXT: PICK ITS FINISH →</button></div>' +
                '<div class="spb-easy-tol-row"><label>Color reach <b id="spbEasyTolVal">' + esc(z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT) + '</b></label><input type="range" id="spbEasyTolSlider" min="0" max="100" value="' + esc(z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT) + '"></div>' +
                '<div class="spb-easy-bc-copy">Lower = only the exact shade. Higher = more nearby shades of this color.</div></div>';
        } else if (bc.phase === 'finish') {
            var z2 = zones[bc.zoneIdx] || {};
            if (bc.pickerFor === 'borrow') {
                stepHtml = '<div class="spb-easy-bc-card"><div class="spb-easy-bc-eyebrow">COLOR BY BASE TYPE</div>' +
                    '<div class="spb-easy-bc-title">Pick the Paint Booth color you can actually see</div>' +
                    '<div class="spb-easy-bc-copy">Every card below is the real authored thumbnail already used by Paint Booth: <b>paint on the left, iRacing spec on the right.</b> Open a family or search, then click the look you want.</div>' +
                    '<button type="button" class="spb-easy-bc-secondary" id="spbEasyBasePickerBack">← BACK TO COLOR CHOICE</button></div>' +
                    '<div class="spb-easy-finder"><input type="text" id="spbEasySearch" value="' + esc(_searchText) + '" placeholder="Search all ' + baseCatalogTotal() + ' colors…" autocomplete="off" spellcheck="false" title="' + esc(SEARCH_TIP) + '"><button type="button" id="spbEasyCatalogToggle" title="' + esc(CAT_TIP) + '"></button></div>' +
                    '<div class="spb-easy-finishes spb-easy-base-finishes" id="spbEasyFinishes" aria-label="Paint Booth base color thumbnail library"></div>';
            } else {
                stepHtml = '<div class="spb-easy-bc-card"><div class="spb-easy-bc-eyebrow">SECOND QUESTION</div>' +
                    '<div class="spb-easy-bc-title"><span class="spb-easy-zchip-swatch" style="background:' + esc(z2.pickerColor || '#888') + '"></span> Pick a finish for this color</div>' +
                    '<div class="spb-easy-bc-copy">Every card is a real render, not a color dot — the left half is the finish in its own color, the right half is what lands on your car. Start with the 50 hand-picked looks, search, or open the FULL CATALOG.</div></div>' +
                    '<div class="spb-easy-finder"><input type="text" id="spbEasySearch" value="' + esc(_searchText) + '" placeholder="Search all ' + catalogTotal() + ' looks…" autocomplete="off" spellcheck="false" title="' + esc(SEARCH_TIP) + '"><button type="button" id="spbEasyCatalogToggle" title="' + esc(CAT_TIP) + '"></button></div>' +
                    '<div class="spb-easy-finishes" id="spbEasyFinishes" aria-label="Spec finish thumbnail library"></div>';
            }
        } else if (bc.phase === 'options') {
            var z3 = zones[bc.zoneIdx] || {};
            var f3 = (z3.finish || z3.base) ? finishInfo(z3.finish || z3.base) : null;
            var colorText = z3.baseColorMode === 'solid' ? 'new solid color' : (z3.baseColorMode === 'special' ? 'Paint Booth base color' : 'original paint color');
            stepHtml = '<div class="spb-easy-bc-card"><div class="spb-easy-bc-eyebrow">THIS COLOR IS READY</div>' +
                '<div class="spb-easy-bc-title"><span class="spb-easy-zchip-swatch" style="background:' + esc(z3.pickerColor || '#888') + '"></span>' + esc(f3 ? f3.name : 'Choose a finish') + '</div>' +
                '<div class="spb-easy-bc-copy">Using <b>' + esc(colorText) + '</b>. Check LIVE PREVIEW and the spec channels, or change either decision below.</div>' +
                '<div class="spb-easy-tol-row"><label>Color reach <b id="spbEasyTolVal">' + esc(z3.pickerTolerance != null ? z3.pickerTolerance : TOL_DEFAULT) + '</b></label><input type="range" id="spbEasyTolSlider" min="0" max="100" value="' + esc(z3.pickerTolerance != null ? z3.pickerTolerance : TOL_DEFAULT) + '"></div>' +
                '<div class="spb-easy-tol-row"><label>How strong <b id="spbEasyStrengthVal">' + Math.round(Number(z3.intensity != null ? z3.intensity : 100)) + '%</b></label><input type="range" id="spbEasyStrength" min="5" max="100" step="5" value="' + Math.round(Number(z3.intensity != null ? z3.intensity : 100)) + '" title="Lower = a hint of the finish, more of your own paint shows through"></div>' +
                (easyColorZones().length > 1 ? '<div class="spb-easy-copyrow"><label for="spbEasyCopyTo">USE THIS SETUP ON</label><select id="spbEasyCopyTo" title="Give another picked color the same finish, strength and color treatment"><option value="">Another color\u2026</option>' + easyColorZones().filter(function (q) { return q.i !== bc.zoneIdx; }).map(function (q) {   var qf = q.z.finish ? finishInfo(finishKey('monolithic', q.z.finish)) : (q.z.base ? finishInfo(finishKey('base', q.z.base)) : null);   return '<option value="' + q.i + '">' + esc(q.z.name || ('Color ' + (q.i + 1))) +     (qf ? (' \u2014 now ' + esc(qf.name)) : ' \u2014 unfinished') + '</option>'; }).join('') + '<option value="__all">Every other color</option></select></div>' : '') +
                '<div class="spb-easy-bc-choice"><button type="button" class="spb-easy-bc-secondary" id="spbEasyEditColor">← EDIT COLOR</button><button type="button" class="spb-easy-bc-secondary" id="spbEasyChangeFinish">DIFFERENT FINISH</button></div>' +
                '<button type="button" class="spb-easy-bc-primary" id="spbEasyAnotherColor">＋ ADD ANOTHER COLOR</button></div>';
        }
        els.rail.innerHTML = railHeader('BY COLOR · PAINT BY NUMBERS', 'SOURCE → color choice → finish choice → verified iRacing save.', true) +
            (chips ? '<div class="spb-easy-zchips" id="spbEasyZchips">' + chips + '</div>' : '') +
            '<div id="spbEasyPlanList">' + planListHtml() + '</div>' +
            stepHtml + saveBlockHtml(null);
        $('spbEasyBackBtn').addEventListener('click', function () { setPickMode(false); state.view = 'whole'; renderRail(); });
        wirePlanList();
        var zc = $('spbEasyZchips');
        if (zc) zc.addEventListener('click', function (e) {
            // SPB Easy beta hardening 2026-07-21: normalize the click target.
            // The chip's × is a bare text node in some embedded-browser click
            // paths; relying on e.target.getAttribute/closest made REMOVE look
            // clickable while doing nothing. Resolve through its parent and
            // the actual [data-zx] button so mouse, touch and automation agree.
            var target = e.target && e.target.nodeType === 3 ? e.target.parentElement : e.target;
            var removeBtn = target && target.closest ? target.closest('[data-zx]') : null;
            var x = removeBtn ? removeBtn.getAttribute('data-zx') : null;
            if (x != null) {
                e.preventDefault();
                e.stopPropagation();
                removeColorZone(parseInt(x, 10));
                return;
            }
            var chip = target && target.closest ? target.closest('.spb-easy-zchip') : null;
            if (chip) {
                bc.zoneIdx = parseInt(chip.getAttribute('data-zi'), 10);
                var chosen = zones[bc.zoneIdx] || {};
                bc.phase = (chosen.base || chosen.finish) ? 'options' : 'color';
                bc.recolorOpen = chosen.baseColorMode === 'solid' || chosen.baseColorMode === 'special';
                bc.pickerFor = 'finish'; setPickMode(false); renderRail();
            }
        });
        if (bc.phase === 'pick') {
            setPickMode(true);
            var auto = $('spbEasyAutoFind');
            if (auto) auto.addEventListener('click', function () { autoFindColors(); });
            var cancel = $('spbEasyBcCancelPick');
            if (cancel) cancel.addEventListener('click', function () {
                setPickMode(false);
                var existing = easyColorZones();
                bc.zoneIdx = existing.length ? existing[existing.length - 1].i : -1;
                var chosen = bc.zoneIdx >= 0 ? (zones[bc.zoneIdx] || {}) : {};
                bc.phase = bc.zoneIdx < 0 ? 'pick' : ((chosen.base || chosen.finish) ? 'options' : 'color');
                bc.recolorOpen = chosen.baseColorMode === 'solid' || chosen.baseColorMode === 'special';
                renderRail();
            });
        } else if (bc.phase === 'color') {
            setPickMode(false); wireColorPhase();
        } else if (bc.phase === 'finish') {
            setPickMode(false);
            els.search = $('spbEasySearch'); els.catalogToggle = $('spbEasyCatalogToggle'); els.finishes = $('spbEasyFinishes');
            if (els.catalogToggle && bc.pickerFor !== 'borrow') els.catalogToggle.addEventListener('click', function () {
                if (_catalogMode || _searchText) {
                    _catalogMode = false;
                    _searchText = '';
                    if (els.search) els.search.value = '';
                } else _catalogMode = true;
                renderFinishList();
            });
            els.search.addEventListener('input', function () { _searchText = String(els.search.value || '').trim().toLowerCase(); searchSoon(); });
            attachFinishListHandlers(els.finishes);
            var baseBack = $('spbEasyBasePickerBack');
            if (baseBack) baseBack.addEventListener('click', function () { bc.phase = 'color'; bc.pickerFor = 'finish'; _searchText = ''; renderRail(); });
            renderFinishList();
        } else if (bc.phase === 'options') {
            setPickMode(false); wireOptionsPhase();
        }
        wireCarParts();
        wireSaveBlock();
    }

    function wireColorPhase() {
        wireTolSlider();
        var z = zones[bc.zoneIdx]; if (!z) return;
        function openBaseColorLibrary() {
            bc.recolorOpen = true;
            z.baseColorMode = 'special';
            z.baseColor = null;
            bc.phase = 'finish';
            bc.pickerFor = 'borrow';
            _searchText = '';
            _catalogMode = true;
            renderRail();
        }
        var keep = $('spbEasyKeepColor'), rec = $('spbEasyRecolor');
        if (keep) keep.addEventListener('click', function () { bc.recolorOpen = false; setZoneRecolor(bc.zoneIdx, null); bc.phase = 'finish'; _catalogMode = false; _searchText = ''; renderRail(); clearRecolorOverlay(); });
        // 2026-07-22 owner beta blocker: opening CHANGE THE COLOR is navigation,
        // not a hidden paint edit. The first real color input below starts the
        // temporary neutral preview anchor. Workflow-only; finish metrics N/A.
        if (rec) rec.addEventListener('click', function () { bc.recolorOpen = true; renderRail(); });
        var solid = $('spbEasySolidMode'); if (solid) solid.addEventListener('click', function () { bc.recolorOpen = true; setZoneRecolor(bc.zoneIdx, z.baseColor || z.pickerColor || '#2255cc'); renderRail(); updateRecolorOverlay(); });
        var base = $('spbEasyBaseMode'); if (base) base.addEventListener('click', openBaseColorLibrary);
        var hex = $('spbEasyRecolorHex'); if (hex) hex.addEventListener('input', function () { bc.recolorOpen = true; setZoneRecolor(bc.zoneIdx, hex.value); updateRecolorOverlay(); });
        var chooseBase = $('spbEasyChooseBaseColor'); if (chooseBase) chooseBase.addEventListener('click', openBaseColorLibrary);
        armLazyThumbs($('spbEasyBasePanel'));
        function slider(id, valId, field, floating, suffix) {
            var el = $(id); if (!el) return;
            el.addEventListener('input', function () {
                var value = floating ? parseFloat(el.value) : (parseInt(el.value, 10) || 0);
                z[field] = value;
                $(valId).textContent = (floating ? value.toFixed(2) : value) + (suffix || '');
                // With SOLID COLOR visibly selected, the first H/S/B move is
                // itself an explicit color decision even if the wheel has not
                // moved yet. Activate the same truthful live-render path.
                if (!z.baseColorMode && field !== 'baseColorScale') setZoneRecolor(bc.zoneIdx, z.pickerColor || '#2255cc');
                else kickPreviewDebounced();
                if (field !== 'baseColorScale') {
                    if (_hsbOverlayTimer) clearTimeout(_hsbOverlayTimer);
                    _hsbOverlayTimer = setTimeout(function () { _hsbOverlayTimer = null; updateRecolorOverlay(); }, 260);
                }
            });
        }
        slider('spbEasyHue', 'spbEasyHueVal', 'baseHueOffset');
        slider('spbEasySat', 'spbEasySatVal', 'baseSaturationAdjust');
        slider('spbEasyBrt', 'spbEasyBrtVal', 'baseBrightnessAdjust');
        slider('spbEasyColorScale', 'spbEasyColorScaleVal', 'baseColorScale', true, '×');
        var next = $('spbEasyColorNext'); if (next) next.addEventListener('click', function () { if (z.baseColorMode === 'special' && !selectedBaseColorInfo(z.baseColorSource)) { openBaseColorLibrary(); return; } bc.phase = 'finish'; bc.pickerFor = 'finish'; _searchText = ''; _catalogMode = false; renderRail(); });
    }
    var _tolFlashTimer = null;
    var _hsbOverlayTimer = null;
    function wireTolSlider() {
        var tol = $('spbEasyTolSlider');
        if (!tol) return;
        tol.addEventListener('input', function () {
            setZoneTolerance(bc.zoneIdx, parseInt(tol.value, 10));
            var v = $('spbEasyTolVal');
            if (v) v.textContent = tol.value;
            // [2026-08-06 easy-loop #6] reach changes coverage — RE-FLASH the
            // selection so the buyer sees the new spread. Debounced: the flash
            // scans the full source once, not per input tick.
            if (_tolFlashTimer) clearTimeout(_tolFlashTimer);
            _tolFlashTimer = setTimeout(function () {
                _tolFlashTimer = null;
                var z = zones[bc.zoneIdx];
                var rgb = z && z.color && z.color.color_rgb;
                if (rgb) flashColorReach(rgb, parseInt(tol.value, 10) || 0);
            }, 260);
        });
    }

    // [2026-08-08 E20] A multi-color plan often wants the SAME treatment on
    // two colors (both stripes chrome, body matte). There was no way to say
    // that except redoing the whole finish + strength + recolor dance by hand.
    // The color selection itself (which pixels) is deliberately NOT copied.
    function copySetupTo(targetIdx) {
        var src = zones[bc.zoneIdx];
        if (!src) return 0;
        var targets = [];
        if (targetIdx === '__all') {
            targets = easyColorZones().filter(function (q) { return q.i !== bc.zoneIdx; }).map(function (q) { return q.i; });
        } else {
            var n = parseInt(targetIdx, 10);
            if (!isNaN(n) && zones[n] && n !== bc.zoneIdx) targets = [n];
        }
        if (!targets.length) return 0;
        undoPush('Easy Mode: copy setup to ' + targets.length + ' color' + (targets.length === 1 ? '' : 's'));
        targets.forEach(function (i) {
            var z = zones[i];
            if (!z) return;
            z.base = src.base || null;
            z.finish = src.finish || null;
            z.pattern = src.pattern || 'none';
            z.intensity = src.intensity != null ? src.intensity : '100';
            z.baseColorMode = src.baseColorMode || null;
            z.baseColor = src.baseColor || null;
            z.baseColorSource = src.baseColorSource || null;
            z.baseHueOffset = src.baseHueOffset || 0;
            z.baseSaturationAdjust = src.baseSaturationAdjust || 0;
            z.baseBrightnessAdjust = src.baseBrightnessAdjust || 0;
            if (z.base || z.finish) delete z._easyPendingColorPreview;
        });
        refreshZonesUI();
        renderRail();
        kickPreview();
        try {
            if (window.showToast) window.showToast('Same setup applied to ' + targets.length + ' more color' + (targets.length === 1 ? '' : 's'), 'success');
        } catch (e) {}
        return targets.length;
    }

    function wireOptionsPhase() {
        wireTolSlider();
        var copyTo = $('spbEasyCopyTo');
        if (copyTo) copyTo.addEventListener('change', function () {
            var v = copyTo.value;
            copyTo.value = '';
            if (v) copySetupTo(v);
        });
        // [2026-08-08 E26] Per-color strength. Pro exposes intensity; Easy hid
        // it entirely, so "just a hint of candy" was impossible for a buyer.
        var st = $('spbEasyStrength');
        if (st) {
            var stVal = $('spbEasyStrengthVal');
            st.addEventListener('input', function () {
                var z = zones[bc.zoneIdx]; if (!z) return;
                var v = Math.max(5, Math.min(100, parseInt(st.value, 10) || 100));
                z.intensity = String(v);
                if (stVal) stVal.textContent = v + '%';
                kickPreviewDebounced();
            });
        }
        var edit = $('spbEasyEditColor');
        if (edit) edit.addEventListener('click', function () { bc.phase = 'color'; renderRail(); });
        var chg = $('spbEasyChangeFinish');
        if (chg) chg.addEventListener('click', function () { bc.phase = 'finish'; bc.pickerFor = 'finish'; _searchText = ''; _catalogMode = false; renderRail(); });
        var another = $('spbEasyAnotherColor');
        if (another) another.addEventListener('click', function () { bc.phase = 'pick'; bc.pickerFor = 'finish'; bc.recolorOpen = false; renderRail(); });
    }
    // Source-pixel picking. Tier 1 (universal, sync): copy Pro's own source
    // canvas #paintCanvas — it holds the truth for EVERY source kind (disk
    // TGA, imported PSD composite, blank canvas). Tier 2 (fallback):
    // /preview-tga fetch by path. Verified 2026-07-16: window.paintImageData
    // and _spbFlatPaintLiveSource are both undefined in normal flows, and a
    // PSD-sourced session's #paintFile can point at a TGA that doesn't exist
    // on disk (/preview-tga 404s) while #paintCanvas is fully painted.
    var _srcPath = null;
    var _srcReady = false;
    var _srcLoading = false;
    function currentPaintPath() {
        var pf = $('paintFile');
        return pf ? String(pf.value || '').trim() : '';
    }
    function drawSourceCanvases(image) {
        if (!image || !els.pickCanvas || !els.sourceCanvas) return false;
        var w = image.width || image.naturalWidth, h = image.height || image.naturalHeight;
        if (!w || !h) return false;
        [els.pickCanvas, els.sourceCanvas, els.liveCanvas].forEach(function (canvas) {
            if (!canvas) return;
            canvas.width = w; canvas.height = h;
            canvas.getContext('2d', { willReadFrequently: canvas === els.pickCanvas }).drawImage(image, 0, 0, w, h);
        });
        _covBuf = null;
        return true;
    }
    function syncSpecProof() {
        if (!_built) return;
        var spec = $('livePreviewSpecImg');
        if (!spec || !spec.getAttribute('src') || !spec.complete || !spec.naturalWidth) return;
        // Same renderer as the Pro dock: Combined plus literal Photoshop-style
        // red/green/blue material lanes. One implementation means no Easy drift.
        if (typeof window.spbRenderSpecProofSet === 'function') {
            window.spbRenderSpecProofSet(spec, {
                all: $('spbEasySpecAll'),
                r: $('spbEasySpecR'),
                g: $('spbEasySpecG'),
                b: $('spbEasySpecB')
            }, 256);
        }
        renderWholeMaterialPreview(spec);
    }

    // Whole Car intentionally returns the source diffuse paint byte-for-byte;
    // a normal paint preview would therefore look unchanged and make a real
    // spec edit appear broken. This neutral-light simulator uses the ACTUAL
    // rendered M/R/Cc pixels to reveal material response without adding a fake
    // spotlight or rewriting the paint that will be saved.
    function renderWholeMaterialPreview(specImage) {
        if (!_active || state.view !== 'whole' || !detectWholeApplied()) return;
        specImage = specImage || $('livePreviewSpecImg');
        if (!specImage || !specImage.complete || !specImage.naturalWidth || !els.liveCanvas || !els.sourceCanvas) return;
        ensureSourceCanvas(function (ready) {
            if (!ready || state.view !== 'whole') return;
            try {
                var maxEdge = 1024;
                var ratio = Math.min(1, maxEdge / Math.max(specImage.naturalWidth, specImage.naturalHeight));
                var w = Math.max(1, Math.round(specImage.naturalWidth * ratio));
                var h = Math.max(1, Math.round(specImage.naturalHeight * ratio));
                var out = els.liveCanvas;
                out.width = w; out.height = h;
                var outCtx = out.getContext('2d', { willReadFrequently: true });
                outCtx.clearRect(0, 0, w, h);
                outCtx.drawImage(els.sourceCanvas, 0, 0, w, h);
                var paintPixels = outCtx.getImageData(0, 0, w, h);
                var specCanvas = document.createElement('canvas');
                specCanvas.width = w; specCanvas.height = h;
                var specCtx = specCanvas.getContext('2d', { willReadFrequently: true });
                specCtx.drawImage(specImage, 0, 0, w, h);
                var specPixels = specCtx.getImageData(0, 0, w, h).data;
                var pixels = paintPixels.data;
                var L = LIGHT_MODES[state.light] || LIGHT_MODES.studio;
                for (var i = 0; i < pixels.length; i += 4) {
                    var metal = specPixels[i] / 255;
                    var rough = specPixels[i + 1] / 255;
                    var coat = specPixels[i + 2] / 255;
                    // Match the quiet material used by the engine at 0%
                    // strength: M=0, R=160, Cc=255 must look exactly like the
                    // source here too. The preview then shows only departures
                    // caused by the actual rendered spec, never a fake beam.
                    var response = metal * L.m + ((160 / 255) - rough) * L.r + (coat - 1) * L.c;
                    // ambient dims the BODY; the specular is gated by hiCut so a
                    // night scene stays dark except where the material really
                    // reflects (measured: night mean must sit below garage)
                    var shade = (1 + response * L.shade) * L.amb;
                    // A mirror reflects its SURROUNDINGS, and at night the
                    // surroundings are dark. Without an environment map the
                    // honest stand-in is the paint's own brightness: dark
                    // panels stay dark, bright graphics catch the track lights.
                    // (Measured need: a chrome whole-car is uniformly reflective,
                    // so an unweighted specular made NIGHT brighter than GARAGE.)
                    var lum = (pixels[i] + pixels[i + 1] + pixels[i + 2]) / 765;
                    var albW = 1 - L.alb + L.alb * lum;
                    var highlight = Math.pow(Math.max(0, response - L.hiCut), L.hiPow) * L.hi * albW;
                    pixels[i] = Math.max(0, Math.min(255, pixels[i] * shade + highlight));
                    pixels[i + 1] = Math.max(0, Math.min(255, pixels[i + 1] * shade + highlight));
                    pixels[i + 2] = Math.max(0, Math.min(255, pixels[i + 2] * shade + highlight));
                }
                outCtx.putImageData(paintPixels, 0, 0);
                out.hidden = false;
                var simNote = $('spbEasyMaterialSimNote');
                if (simNote) simNote.textContent = 'REAL MATERIAL \u00b7 ' + (LIGHT_MODES[state.light] || LIGHT_MODES.studio).label + ' LIGHT';
                if (els.previewImg) els.previewImg.hidden = true;
            } catch (e) {
                // The four literal spec channels remain the authoritative proof
                // even if an old embedded browser cannot read canvas pixels.
            }
        });
    }
    function ensureSourceCanvas(cb) {
        // Tier 1: mirror Pro's source canvas (refresh every entry into pick
        // mode — cheap drawImage; keeps up with any Pro-side edits).
        // ≥512 guard: before the source image loads, #paintCanvas sits at the
        // 300x150 element default — copying that latches an EMPTY mirror
        // (found live 2026-07-16: first pick returned rgb 0,0,0 off blank).
        try {
            var pro = $('paintCanvas');
            if (pro && pro.width >= 512 && pro.height >= 512) {
                drawSourceCanvases(pro);
                _srcReady = true;
                cb(true);
                return;
            }
        } catch (e) {}
        // Tier 1b: Spec Sculpt has already validated and decoded this source.
        // Reuse its proof image instead of asking /preview-tga for the
        // temporary *.tga path produced by a layered PSD import (that path is
        // intentionally virtual and returned 404 before the Pro canvas was
        // ready). This makes the handoff immediate and keeps diagnostics clean.
        try {
            var sculptState = window.spbEasySculpt && typeof window.spbEasySculpt.getState === 'function'
                ? window.spbEasySculpt.getState() : null;
            var sculptUrl = sculptState && sculptState.sourceUrl ? String(sculptState.sourceUrl) : '';
            if (sculptUrl) {
                var sculptKey = 'sculpt:' + String(sculptState.filename || '') + ':' + sculptUrl.length;
                if (_srcReady && _srcPath === sculptKey) { cb(true); return; }
                if (_srcLoading) { cb(null); return; }
                _srcLoading = true;
                var sculptImage = new Image();
                sculptImage.onload = function () {
                    drawSourceCanvases(sculptImage);
                    _srcPath = sculptKey;
                    _srcReady = true;
                    _srcLoading = false;
                    cb(true);
                };
                sculptImage.onerror = function () {
                    _srcLoading = false;
                    _srcReady = false;
                    cb(false);
                };
                sculptImage.src = sculptUrl;
                return;
            }
        } catch (e) {}
        // Tier 2: fetch the TGA preview by path.
        var path = currentPaintPath();
        if (!path) { cb(false); return; }
        if (_srcReady && _srcPath === path) { cb(true); return; }
        if (_srcLoading) { cb(null); return; }   // already inbound — poll will retry
        _srcLoading = true;
        fetch(serverBase() + '/preview-tga', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path }),
        }).then(function (resp) {
            if (!resp.ok) throw new Error('preview-tga ' + resp.status);
            return resp.blob();
        }).then(function (blob) {
            return new Promise(function (resolve, reject) {
                var image = new Image(), url = URL.createObjectURL(blob);
                image.onload = function () { URL.revokeObjectURL(url); resolve(image); };
                image.onerror = function () { URL.revokeObjectURL(url); reject(new Error('source preview image decode failed')); };
                image.src = url;
            });
        }).then(function (sourceImage) {
            drawSourceCanvases(sourceImage);
            _srcPath = path;
            _srcReady = true;
            _srcLoading = false;
            cb(true);
        }).catch(function (err) {
            _srcLoading = false;
            _srcReady = false;
            try { console.warn('[spbEasy] source fetch failed:', err); } catch (e) {}
            cb(false);
        });
    }

    function setPickMode(on) {
        if (!_built) return;
        if (_protectMode) return;   // [E25] protect owns the pick canvas while on
        setLivePickMode(!!on && paintLoaded());
        if (!on) {
            els.pickCanvas.hidden = true;
            els.pickCanvas.tabIndex = -1;
            els.pickBanner.hidden = true;
            if (els.loupe) els.loupe.hidden = true;
            els.pickBanner.textContent = '🎯 Click the color on EITHER picture';
            syncPreviewNow();
            if (paintLoaded() && els.previewImg.getAttribute('src')) els.previewImg.hidden = false;
            return;
        }
        if (!paintLoaded()) {
            els.pickCanvas.hidden = true;
            els.pickBanner.hidden = false;
            els.pickBanner.textContent = 'Load your car first (STEP 1) — then we can pick colors off it.';
            return;
        }
        els.pickBanner.hidden = false;
        els.pickBanner.textContent = 'Loading your paint…';
        var pickWasHidden = els.pickCanvas.hidden;
        ensureSourceCanvas(function (ok) {
            if (!_active || state.view !== 'bycolor' || bc.phase !== 'pick') return;
            if (ok) {
                els.pickBanner.textContent = '🎯 Click the color on EITHER picture';
                els.pickCanvas.hidden = false;
                els.pickCanvas.tabIndex = 0;
                if (els.previewImg.getAttribute('src')) els.previewImg.hidden = false;
                if (pickWasHidden) window.requestAnimationFrame(function () {
                    try { els.pickCanvas.focus({ preventScroll: true }); } catch (e) { try { els.pickCanvas.focus(); } catch (e2) {} }
                });
            } else if (ok === false) {
                els.pickBanner.textContent = 'Couldn’t load your paint for picking — try Pro Mode’s eyedropper.';
            }
            // ok === null → fetch already inbound; the paint poll retries us.
        });
    }

    // [2026-08-08 E24] Buyers kept clicking the LIVE PREVIEW to choose a color
    // - it is the same car at the same UV, so the click is perfectly meaningful.
    // Sampling always reads the SOURCE (the zone matches original pixels, not
    // rendered ones); only the rectangle used to map the click changes.
    function samplePickCanvas(e, fromEl) {
        if (!_srcReady) return null;
        var cw = els.pickCanvas.width, ch = els.pickCanvas.height;
        var rect = (fromEl || els.pickCanvas).getBoundingClientRect();
        if (!rect.width || !rect.height) return null;
        var x = Math.max(0, Math.min(cw - 1, Math.round((e.clientX - rect.left) * (cw / rect.width))));
        var y = Math.max(0, Math.min(ch - 1, Math.round((e.clientY - rect.top) * (ch / rect.height))));
        var d;
        try { d = els.pickCanvas.getContext('2d').getImageData(x, y, 1, 1).data; } catch (e2) { return null; }
        if (d[3] === 0) return null;
        return { rgb: [d[0], d[1], d[2]], x: x, y: y, hex: '#' + [d[0], d[1], d[2]].map(function (v) { return ('0' + v.toString(16)).slice(-2); }).join('') };
    }

    // [2026-08-08 E23] The loupe showed a color chip and a hex string but not
    // the PIXELS, so picking a pinstripe or a small logo was aim-and-hope. Now
    // it magnifies a 15x15 window of the real source at ~9x with a crosshair on
    // the exact pixel that will be sampled.
    function drawLoupeZoom(e, fromEl) {
        var cv = els.loupeZoom;
        if (!cv || !_srcReady) return;
        var src = els.pickCanvas;
        var cw = src.width, ch = src.height;
        var rect = (fromEl || src).getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        var x = Math.max(0, Math.min(cw - 1, Math.round((e.clientX - rect.left) * (cw / rect.width))));
        var y = Math.max(0, Math.min(ch - 1, Math.round((e.clientY - rect.top) * (ch / rect.height))));
        var win = 15, half = (win - 1) / 2;
        var ctx = cv.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, cv.width, cv.height);
        ctx.fillStyle = '#05070d';
        ctx.fillRect(0, 0, cv.width, cv.height);
        try {
            ctx.drawImage(src, x - half, y - half, win, win, 0, 0, cv.width, cv.height);
        } catch (err) { return; }
        var cell = cv.width / win;
        var cx = Math.floor(win / 2) * cell;
        ctx.strokeStyle = 'rgba(0,0,0,0.9)';
        ctx.lineWidth = 3;
        ctx.strokeRect(cx + 0.5, cx + 0.5, cell - 1, cell - 1);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(cx + 0.5, cx + 0.5, cell - 1, cell - 1);
    }

    function onPickCanvasMove(e) {
        if (!els.loupe || els.pickCanvas.hidden) return;
        var s = samplePickCanvas(e);
        if (!s) { els.loupe.hidden = true; return; }
        els.loupeDot.style.background = s.hex;
        els.loupeHex.textContent = s.hex;
        drawLoupeZoom(e);
        var stageRect = els.stage.getBoundingClientRect();
        els.loupe.style.left = (e.clientX - stageRect.left + 18) + 'px';
        els.loupe.style.top = (e.clientY - stageRect.top - 14) + 'px';
        els.loupe.hidden = false;
    }

    function onPickCanvasClick(e) {
        var s = samplePickCanvas(e);
        if (!s) return;   // empty/transparent pixel — not a real color
        if (els.loupe) els.loupe.hidden = true;
        if (_protectMode) { protectAt(s.x, s.y); return; }   // [E25]
        addColorZone(s.rgb, s.hex);
    }

    // [2026-08-06 easy-loop] "Paint by numbers" needs the numbers to light up:
    // the instant a buyer picks a color, FLASH exactly which pixels that pick
    // covers (match metric mirrors the zone: max channel diff <= tolerance)
    // and say how much of the paint it is. Fades out on its own; overlay is
    // pointer-transparent and lives only in the SOURCE card.
    var _pickFlashTimer = null;
    var _covLast = null;
    var _covBuf = null;          // {w,h,data} downscaled copy of the source
    // ==================================================================== E25
    // [2026-08-08 E25] PROTECT / "everything except the numbers". Pro can brush
    // an exclude region; Easy had no way to shield anything, so a buyer who
    // wanted a chrome car lost their race numbers, sponsor logos and
    // contingency decals under the finish. One click now grabs the whole
    // CONNECTED object under the cursor (glyph + outline + shadow, via a small
    // dilation) and marks those pixels spatial-mask 2. The engine already
    // honours exactly that -- mask = np.where(spatial == 2, 0.0, mask), and
    // with no include (1) pixels present nothing else is restricted
    // (shokker_engine_v2.py ~17790). Protection is deliberately NOT part of the
    // portable plan (E17/E19): it is pixel coordinates on THIS car's paint.
    var _protectMode = false;
    var _protectMask = null;        // Uint8Array(w*h); 2 = leave this pixel alone
    var _protectPct = 0;
    var _srcOpaque = 0;             // opaque pixel count, cached per source
    var _srcOpaqueFor = '';
    var PROTECT_TOL_LADDER = [48, 24, 12];
    var PROTECT_LEAK_PCT = 25;      // a grab past this is a bleed, not an object

    function protectSpots() {
        if (!Array.isArray(state.protect)) state.protect = [];
        return state.protect;
    }

    // Span-based flood fill. Marks the connected run of similar pixels from the
    // seed into `seen` and returns its bounding box, or null for a dead pixel.
    function floodGrab(data, w, h, sx, sy, tol, seen) {
        var p0 = (sy * w + sx) * 4;
        if (data[p0 + 3] === 0) return null;
        var r0 = data[p0], g0 = data[p0 + 1], b0 = data[p0 + 2];
        function ok(x, y) {
            var i = y * w + x;
            if (seen[i]) return false;
            var p = i * 4;
            if (data[p + 3] === 0) return false;
            return Math.abs(data[p] - r0) <= tol &&
                   Math.abs(data[p + 1] - g0) <= tol &&
                   Math.abs(data[p + 2] - b0) <= tol;
        }
        var stack = [sx, sy], count = 0;
        var minx = sx, maxx = sx, miny = sy, maxy = sy;
        while (stack.length) {
            var y = stack.pop(), x = stack.pop();
            if (!ok(x, y)) continue;
            var xl = x; while (xl > 0 && ok(xl - 1, y)) xl--;
            var xr = x; while (xr < w - 1 && ok(xr + 1, y)) xr++;
            for (var i2 = xl; i2 <= xr; i2++) { seen[y * w + i2] = 1; count++; }
            if (xl < minx) minx = xl;
            if (xr > maxx) maxx = xr;
            if (y < miny) miny = y;
            if (y > maxy) maxy = y;
            for (var d = -1; d <= 1; d += 2) {
                var ny = y + d;
                if (ny < 0 || ny >= h) continue;
                var inRun = false;                    // push one seed per run
                for (var xx = xl; xx <= xr; xx++) {
                    if (ok(xx, ny)) { if (!inRun) { stack.push(xx, ny); inRun = true; } }
                    else inRun = false;
                }
            }
        }
        return count ? { count: count, x0: minx, y0: miny, x1: maxx, y1: maxy } : null;
    }

    // Separable max-filter: grows the grabbed object by R px so its outline,
    // drop shadow and anti-aliased fringe come along -- a bare color fill stops
    // at the glyph edge and leaves a painted halo around every number.
    function dilateInto(seen, w, h, bb, R, out) {
        var x0 = Math.max(0, bb.x0 - R), x1 = Math.min(w - 1, bb.x1 + R);
        var y0 = Math.max(0, bb.y0 - R), y1 = Math.min(h - 1, bb.y1 + R);
        var bw = x1 - x0 + 1;
        var tmp = new Uint8Array(bw * (y1 - y0 + 1));
        var x, y, k, row, srow, a, b;
        for (y = y0; y <= y1; y++) {
            srow = y * w; row = (y - y0) * bw;
            for (x = x0; x <= x1; x++) {
                if (!seen[srow + x]) continue;
                a = Math.max(x0, x - R); b = Math.min(x1, x + R);
                for (k = a; k <= b; k++) tmp[row + (k - x0)] = 1;
            }
        }
        for (y = y0; y <= y1; y++) {
            row = (y - y0) * bw;
            for (x = 0; x < bw; x++) {
                if (!tmp[row + x]) continue;
                a = Math.max(y0, y - R); b = Math.min(y1, y + R);
                for (k = a; k <= b; k++) out[k * w + (x + x0)] = 2;
            }
        }
    }

    function _sourcePixels() {
        var src = els.pickCanvas;
        if (!_srcReady || !src || !src.width) return null;
        var w = src.width, h = src.height, data;
        try { data = src.getContext('2d').getImageData(0, 0, w, h).data; } catch (e) { return null; }
        if (_srcOpaqueFor !== _srcPath) {
            var n = 0;
            for (var i = 3; i < data.length; i += 4) if (data[i] !== 0) n++;
            _srcOpaque = n || (w * h);
            _srcOpaqueFor = _srcPath;
        }
        return { data: data, w: w, h: h, opaque: _srcOpaque };
    }

    function rebuildProtectMask() {
        _protectMask = null;
        _protectPct = 0;
        var spots = protectSpots();
        if (!spots.length) return 0;
        if (state.protectFor && state.protectFor !== _srcPath) {   // different car
            state.protect = []; state.protectFor = '';
            return 0;
        }
        var px = _sourcePixels();
        if (!px) return 0;                                          // retry once ready
        var w = px.w, h = px.h;
        var mask = new Uint8Array(w * h);
        var R = Math.max(2, Math.round(w / 512));
        var any = false;
        spots.forEach(function (sp) {
            if (sp.x < 0 || sp.y < 0 || sp.x >= w || sp.y >= h) return;
            var seen = new Uint8Array(w * h);
            var bb = floodGrab(px.data, w, h, sp.x, sp.y, sp.tol || 48, seen);
            if (!bb) return;
            dilateInto(seen, w, h, bb, R, mask);
            any = true;
        });
        if (!any) return 0;
        var held = 0;
        for (var i = 0; i < mask.length; i++) if (mask[i] === 2) held++;
        _protectMask = mask;
        _protectPct = px.opaque ? Math.round(held / px.opaque * 100) : 0;
        return _protectPct;
    }

    // Shield ONLY the zones that actually put something on the car. A zone with
    // no material paints nothing, so excluding pixels from it cannot change a
    // rendered pixel -- it just hands the payload builder another full-size
    // mask to RLE-encode on every render, and makes "how many zones are
    // shielded" mean nothing. (Measured 2026-08-08: scoping this changed the
    // shielded-zone count 2 -> 1 with the rendered result bit-identical, which
    // is exactly the claim.)
    function _zoneTakesShield(z) {
        if (!z) return false;
        if (z.base || z.finish) return true;
        if (z.materialStack && z.materialStack.length) return true;
        if (z.patternStack && z.patternStack.length) return true;
        if (z.pattern && z.pattern !== 'none') return true;
        if (z._easyPendingColorPreview) return true;
        if (z.baseColorMode && String(z.baseColorMode) !== 'source') return true;
        return false;
    }

    // Every shielded zone shares one mask object. We only ever clear masks we
    // set ourselves, so a spatial mask brushed in Pro Mode survives a trip here.
    function syncProtectZones() {
        try {
            if (!Array.isArray(zones)) return;
            if (_protectMask === null && protectSpots().length && _srcReady) rebuildProtectMask();
            zones.forEach(function (z) {
                if (!z) return;
                if (_protectMask && _zoneTakesShield(z)) {
                    if (!z.spatialMask || z._spbEasyProtected) {
                        z.spatialMask = _protectMask;
                        z._spbEasyProtected = true;
                    }
                } else if (z._spbEasyProtected) {
                    z.spatialMask = null;
                    z._spbEasyProtected = false;
                }
            });
        } catch (e) {}
    }

    function paintProtectOverlay() {
        var fl = els.pickFlash, src = els.pickCanvas;
        if (!fl || !src || !_srcReady) return;
        if (_pickFlashTimer) { clearTimeout(_pickFlashTimer); _pickFlashTimer = null; }
        if (!_protectMask) { fl.style.opacity = '0'; fl.hidden = true; return; }
        var w = src.width, h = src.height;
        fl.width = w; fl.height = h;
        var ctx = fl.getContext('2d');
        var out = ctx.createImageData(w, h);
        var o = out.data;
        for (var i = 0, p = 0; i < _protectMask.length; i++, p += 4) {
            if (_protectMask[i] === 2) { o[p] = 255; o[p + 1] = 64; o[p + 2] = 96; o[p + 3] = 150; }
        }
        ctx.putImageData(out, 0, 0);
        var cap = 'PROTECTED \u2014 ' + _protectPct + '% OF YOUR PAINT STAYS AS IT IS';
        ctx.font = 'bold ' + Math.round(h * 0.045) + 'px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.lineWidth = Math.max(4, h * 0.008);
        ctx.strokeStyle = 'rgba(0,0,0,0.85)';
        ctx.strokeText(cap, w / 2, h * 0.94);
        ctx.fillStyle = '#ffd27a';
        ctx.fillText(cap, w / 2, h * 0.94);
        fl.hidden = false;
        fl.style.opacity = '1';
    }
    function fadeProtectOverlay() {
        var fl = els.pickFlash;
        if (!fl) return;
        fl.style.opacity = '0';
        if (_pickFlashTimer) clearTimeout(_pickFlashTimer);
        _pickFlashTimer = setTimeout(function () { fl.hidden = true; _pickFlashTimer = null; }, 500);
    }

    function afterProtectChange() {
        rebuildProtectMask();
        syncProtectZones();
        persistState();
        renderMyLooks();
        paintProtectOverlay();
        kickPreview();
    }

    function protectAt(sx, sy) {
        var px = _sourcePixels();
        if (!px) return false;
        var chosen = null, tolUsed = 0;
        for (var t = 0; t < PROTECT_TOL_LADDER.length; t++) {
            var tol = PROTECT_TOL_LADDER[t];
            var seen = new Uint8Array(px.w * px.h);
            var bb = floodGrab(px.data, px.w, px.h, sx, sy, tol, seen);
            if (!bb) continue;
            if (bb.count / px.opaque * 100 <= PROTECT_LEAK_PCT) { chosen = bb; tolUsed = tol; break; }
        }
        if (!chosen) {
            // No silent truncation: a half-protected number is worse than none.
            try {
                if (window.showToast) window.showToast('That spot runs into most of the car \u2014 click right on the number or logo itself', 'info');
            } catch (e) {}
            return false;
        }
        var p0 = (sy * px.w + sx) * 4;
        var hex = '#' + [px.data[p0], px.data[p0 + 1], px.data[p0 + 2]].map(function (v) {
            return ('0' + v.toString(16)).slice(-2);
        }).join('');
        protectSpots().push({ x: sx, y: sy, tol: tolUsed, hex: hex });
        state.protectFor = _srcPath;
        afterProtectChange();
        try {
            if (window.showToast) window.showToast('Protected \u2014 that stays exactly as it is (' + _protectPct + '% of your paint)', 'success');
        } catch (e) {}
        return true;
    }

    function unprotect(idx) {
        var spots = protectSpots();
        if (idx < 0 || idx >= spots.length) return;
        spots.splice(idx, 1);
        if (!spots.length) state.protectFor = '';
        afterProtectChange();
    }

    function protectChipsHtml() {
        var spots = protectSpots();
        if (!spots.length && !_protectMode) return '';
        var chips = spots.map(function (sp, i) {
            return '<span class="spb-easy-protect-chip" title="Protected from every finish. Click \u2715 to let paint back onto it.">' +
                '<i style="background:' + esc(sp.hex || '#888') + '"></i>' +
                'KEPT' +
                '<button type="button" data-unprotect="' + i + '" aria-label="Stop protecting this spot">\u2715</button>' +
                '</span>';
        }).join('');
        var head = spots.length
            ? '<b>\u{1F6E1} ' + spots.length + ' KEPT UNPAINTED \u00b7 ' + _protectPct + '% OF YOUR PAINT</b>'
            : '<b>\u{1F6E1} CLICK WHAT TO KEEP</b>';
        return '<div class="spb-easy-protect-chips" id="spbEasyProtectChips">' + head + chips + '</div>';
    }

    function setProtectMode(on) {
        on = !!on;
        if (on && !paintLoaded()) {
            try { if (window.showToast) window.showToast('Load your car first (STEP 1)', 'info'); } catch (e) {}
            return;
        }
        _protectMode = on;
        if (on) {
            ensureSourceCanvas(function (ok) {
                if (!_protectMode) return;
                if (!ok) {
                    els.pickBanner.hidden = false;
                    els.pickBanner.textContent = 'Couldn\u2019t load your paint \u2014 try Pro Mode\u2019s exclude brush.';
                    return;
                }
                els.pickCanvas.hidden = false;
                els.pickCanvas.tabIndex = 0;
                els.pickBanner.hidden = false;
                els.pickBanner.textContent = '\u{1F6E1} Click your numbers, logos or decals \u2014 whatever you click stays exactly as it is.';
                setLivePickMode(true);
                if (els.previewImg.getAttribute('src')) els.previewImg.hidden = false;
                rebuildProtectMask();
                paintProtectOverlay();
                renderMyLooks();
            });
            renderMyLooks();
            return;
        }
        fadeProtectOverlay();
        var backToPicking = (state.view === 'bycolor' && bc.phase === 'pick');
        setLivePickMode(backToPicking);
        setPickMode(backToPicking);
        renderMyLooks();
    }

    function _coverageBuffer() {
        var src = els.pickCanvas;
        if (!src || !src.width || !_srcReady) return null;
        if (_covBuf && _covBuf.srcW === src.width && _covBuf.srcH === src.height) return _covBuf;
        try {
            var W = 256, H = Math.max(1, Math.round(src.height * (256 / src.width)));
            var c = document.createElement('canvas');
            c.width = W; c.height = H;
            var cx = c.getContext('2d', { willReadFrequently: true });
            cx.drawImage(src, 0, 0, W, H);
            _covBuf = { w: W, h: H, srcW: src.width, srcH: src.height, data: cx.getImageData(0, 0, W, H).data };
        } catch (e) { _covBuf = null; }
        return _covBuf;
    }
    function coveragePct(rgb, tolerance) {
        var buf = _coverageBuffer();
        if (!buf || !rgb) return null;
        var d = buf.data, tol = Math.max(0, Number(tolerance) || 0);
        var r0 = rgb[0], g0 = rgb[1], b0 = rgb[2], hit = 0, seen = 0;
        for (var i = 0; i < d.length; i += 4) {
            if (d[i + 3] === 0) continue;
            seen++;
            if (Math.abs(d[i] - r0) <= tol && Math.abs(d[i + 1] - g0) <= tol && Math.abs(d[i + 2] - b0) <= tol) hit++;
        }
        return seen ? Math.round(hit / seen * 100) : null;
    }
    // [2026-08-08 E39] The reach overlay repainted at the full 2048x2048 source
    // on every tick - pick flash, recolor, and every HSB slider step. MEASURED
    // on this machine: 23.9 ms per repaint at 2048, 4.6 ms at 640, and the
    // percentage it reports is IDENTICAL at both (6%) because it is an area
    // ratio. The card it lands in is 560x560, so 640 is still above display
    // resolution - this is pure waste removed, not quality traded away.
    var OVERLAY_PX = 640;
    var _ovBuf = null;
    function _overlayBuffer() {
        var src = els.pickCanvas;
        if (!src || !src.width || !_srcReady) return null;
        if (_ovBuf && _ovBuf.srcW === src.width && _ovBuf.srcH === src.height) return _ovBuf;
        try {
            var W = Math.min(OVERLAY_PX, src.width);
            var H = Math.max(1, Math.round(src.height * (W / src.width)));
            var c = document.createElement('canvas');
            c.width = W; c.height = H;
            c.getContext('2d', { willReadFrequently: true }).drawImage(src, 0, 0, W, H);
            _ovBuf = { w: W, h: H, srcW: src.width, srcH: src.height,
                       data: c.getContext('2d').getImageData(0, 0, W, H).data };
        } catch (e) { _ovBuf = null; }
        return _ovBuf;
    }

    function _paintReachOverlay(rgb, tolerance, tint, caption) {
        var fl = els.pickFlash;
        var buf = _overlayBuffer();
        if (!buf || !fl) return false;
        var w = buf.w, h = buf.h;
        var data = buf.data;                  // cached; never written to
        fl.width = w; fl.height = h;
        var out = fl.getContext('2d').createImageData(w, h);
        var o = out.data;
        var matched = 0, opaque = 0;
        var r0 = rgb[0], g0 = rgb[1], b0 = rgb[2], tol = Math.max(0, Number(tolerance) || 0);
        for (var i = 0; i < data.length; i += 4) {
            if (data[i + 3] === 0) continue;
            opaque++;
            var dr = Math.abs(data[i] - r0), dg = Math.abs(data[i + 1] - g0), db = Math.abs(data[i + 2] - b0);
            if (dr <= tol && dg <= tol && db <= tol) {
                matched++;
                o[i] = tint[0]; o[i + 1] = tint[1]; o[i + 2] = tint[2]; o[i + 3] = tint[3];
            } else {
                o[i + 3] = 0;
            }
        }
        var fctx = fl.getContext('2d');
        fctx.putImageData(out, 0, 0);
        var pct = opaque ? Math.round(matched / opaque * 100) : 0;
        _covLast = pct;
        var cap = caption.replace('{pct}', String(pct));
        fctx.font = 'bold ' + Math.round(h * 0.045) + 'px system-ui, sans-serif';
        fctx.textAlign = 'center';
        fctx.lineWidth = Math.max(4, h * 0.008);
        fctx.strokeStyle = 'rgba(0,0,0,0.85)';
        fctx.strokeText(cap, w / 2, h * 0.94);
        fctx.fillStyle = '#ffd27a';
        fctx.fillText(cap, w / 2, h * 0.94);
        fl.hidden = false;
        fl.style.opacity = '1';
        return true;
    }
    function flashColorReach(rgb, tolerance) {
        try {
            if (!_paintReachOverlay(rgb, tolerance, [255, 150, 30, 195], 'THIS PICK COVERS ~{pct}% OF YOUR PAINT')) return;
            var fl = els.pickFlash;
            if (_pickFlashTimer) clearTimeout(_pickFlashTimer);
            _pickFlashTimer = setTimeout(function () {
                fl.style.opacity = '0';
                _pickFlashTimer = setTimeout(function () { fl.hidden = true; _pickFlashTimer = null; }, 500);
            }, 2800);   // [iter10] 1.9s was too quick to read the coverage caption first time
        } catch (e) { /* the flash is a hint — never let it break the pick */ }
    }
    // [2026-08-08 easy-loop iter7] CHANGE THE COLOR could not preview: a
    // recolor-only zone has no base/finish, the render predicate skips it and
    // the ENGINE ignores it (verified: center pixel unchanged) — so a buyer
    // picked red and NOTHING moved until the finish step. This paints the
    // chosen color onto the matched pixels client-side, PERSISTENT while the
    // recolor panel is open, so the decision is visible the moment it lands.
    function _shiftHsb(rgb, hueDeg, satAdj, brtAdj) {
        var r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
        var h = 0;
        if (d > 0) {
            if (mx === r) h = ((g - b) / d) % 6;
            else if (mx === g) h = (b - r) / d + 2;
            else h = (r - g) / d + 4;
            h *= 60; if (h < 0) h += 360;
        }
        var sv = mx === 0 ? 0 : d / mx;
        var v = mx;
        h = (h + (hueDeg || 0) + 360) % 360;
        sv = Math.max(0, Math.min(1, sv + (satAdj || 0) / 100));
        v = Math.max(0, Math.min(1, v * (1 + (brtAdj || 0) / 100)));
        var c = v * sv, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c;
        var rr = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x]
               : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
        return [Math.round((rr[0] + m) * 255), Math.round((rr[1] + m) * 255), Math.round((rr[2] + m) * 255)];
    }
    function updateRecolorOverlay() {
        try {
            var z = zones[bc.zoneIdx];
            if (!z || !z.color || !z.color.color_rgb) return;
            var hex = /^#[0-9a-fA-F]{6}$/.test(z.baseColor || '') ? z.baseColor : null;
            if (!hex) return;
            if (_pickFlashTimer) { clearTimeout(_pickFlashTimer); _pickFlashTimer = null; }
            var rgb0 = [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
            // [2026-08-08 iter8] the H/S/B sliders are part of the color
            // decision — shift the overlay tint the same direction so the
            // preview tracks every control on this panel, not just the wheel.
            var shifted = _shiftHsb(rgb0, Number(z.baseHueOffset) || 0,
                Number(z.baseSaturationAdjust) || 0, Number(z.baseBrightnessAdjust) || 0);
            var tint = [shifted[0], shifted[1], shifted[2], 230];
            _paintReachOverlay(z.color.color_rgb, z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT,
                tint, 'NEW COLOR PREVIEW — PICK ITS FINISH NEXT (~{pct}% of your paint)');
        } catch (e) { /* preview hint only */ }
    }
    function clearRecolorOverlay() {
        try {
            if (_pickFlashTimer) return;   // an amber flash owns the canvas right now
            var fl = els.pickFlash;
            if (fl && !fl.hidden) { fl.hidden = true; fl.style.opacity = '0'; }
        } catch (e) {}
    }

    // [2026-08-08 E22] Spec Sculpt can auto-find colors; BY COLOR made the
    // buyer hunt every one by eye. Cluster the paint's dominant colors from
    // the same 256px buffer the coverage figures use, then create one color
    // per cluster so the buyer goes straight to choosing materials.
    function findDominantColors(maxN) {
        var buf = _coverageBuffer();
        if (!buf) return [];
        var d = buf.data, bins = {};
        for (var i = 0; i < d.length; i += 4) {
            if (d[i + 3] < 8) continue;
            var key = ((d[i] >> 5) << 10) | ((d[i + 1] >> 5) << 5) | (d[i + 2] >> 5);
            var e = bins[key];
            if (e) { e.n++; e.r += d[i]; e.g += d[i + 1]; e.b += d[i + 2]; }
            else bins[key] = { n: 1, r: d[i], g: d[i + 1], b: d[i + 2] };
        }
        var total = 0, list = [];
        for (var k in bins) {
            var v = bins[k];
            total += v.n;
            list.push({ n: v.n, rgb: [Math.round(v.r / v.n), Math.round(v.g / v.n), Math.round(v.b / v.n)] });
        }
        if (!total) return [];
        list.sort(function (a, b2) { return b2.n - a.n; });
        var out = [];
        for (var j = 0; j < list.length && out.length < (maxN || 5); j++) {
            var c = list[j];
            var pct = c.n / total * 100;
            if (pct < 2) break;                       // ignore specks and anti-alias fringes
            var tooClose = out.some(function (o) {
                var dr = o.rgb[0] - c.rgb[0], dg = o.rgb[1] - c.rgb[1], db = o.rgb[2] - c.rgb[2];
                return Math.sqrt(dr * dr + dg * dg + db * db) < 48;
            });
            if (tooClose) continue;
            out.push({ rgb: c.rgb, pct: Math.round(pct) });
        }
        return out;
    }
    function autoFindColors() {
        if (!paintLoaded()) return 0;
        var found = findDominantColors(5);
        if (!found.length) {
            try { if (window.showToast) window.showToast('Could not read colors from this paint yet \u2014 try again in a moment', 'info'); } catch (e) {}
            return 0;
        }
        undoPush('Easy Mode: find my colors');
        var made = 0;
        found.forEach(function (c) {
            var hex = '#' + c.rgb.map(function (v) { return ('0' + v.toString(16)).slice(-2); }).join('');
            var dup = easyColorZones().some(function (p2) {
                var q = p2.z.color && p2.z.color.color_rgb;
                if (!q) return false;
                var dr = q[0] - c.rgb[0], dg = q[1] - c.rgb[1], db = q[2] - c.rgb[2];
                return Math.sqrt(dr * dr + dg * dg + db * db) < 48;
            });
            if (dup) return;
            var n = easyColorZones().length + 1;
            zones.push({
                id: (typeof _newZoneId === 'function') ? _newZoneId() : ('easyc_' + n),
                name: 'Color ' + n,
                color: { color_rgb: c.rgb.slice(), tolerance: TOL_DEFAULT },
                colorMode: 'picker', pickerColor: hex, pickerTolerance: TOL_DEFAULT,
                base: null, pattern: 'none', finish: null, intensity: '100',
                customSpec: null, customPaint: null, customBright: null,
                colors: [], regionMask: null, patternStack: []
            });
            made++;
        });
        if (!made) {
            try { if (window.showToast) window.showToast('Those colors are already in your plan', 'info'); } catch (e) {}
            return 0;
        }
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'easy-mode auto colors'); } catch (e) {}
        var pairs = easyColorZones();
        bc.zoneIdx = pairs.length ? pairs[pairs.length - made].i : -1;
        bc.phase = 'finish';
        bc.pickerFor = 'finish';
        bc.recolorOpen = false;
        _searchText = ''; _catalogMode = false; _filterTag = ''; _likeKey = '';
        setPickMode(false);
        refreshZonesUI();
        renderRail();
        kickPreview();
        try {
            if (window.showToast) window.showToast('Found ' + made + ' color' + (made === 1 ? '' : 's') + ' \u2014 now pick a material for each', 'success');
        } catch (e) {}
        return made;
    }

    var _liveePickWired = false;
    function liveMediaEl() {
        var card = els.root ? els.root.querySelector('.spb-easy-live-card .spb-easy-proof-media') : null;
        return card || null;
    }
    function setLivePickMode(on) {
        var media = liveMediaEl();
        if (!media) return;
        media.classList.toggle('spb-easy-live-pickable', !!on);
        if (on && !_liveePickWired) {
            _liveePickWired = true;
            media.addEventListener('mousemove', function (e) {
                if (!media.classList.contains('spb-easy-live-pickable')) return;
                if (!els.loupe) return;
                var s2 = samplePickCanvas(e, media);
                if (!s2) { els.loupe.hidden = true; return; }
                els.loupeDot.style.background = s2.hex;
                els.loupeHex.textContent = s2.hex;
                drawLoupeZoom(e, media);
                var stageRect = els.stage.getBoundingClientRect();
                els.loupe.style.left = (e.clientX - stageRect.left + 18) + 'px';
                els.loupe.style.top = (e.clientY - stageRect.top - 14) + 'px';
                els.loupe.hidden = false;
            });
            media.addEventListener('mouseleave', function () { if (els.loupe) els.loupe.hidden = true; });
            media.addEventListener('click', function (e) {
                if (!media.classList.contains('spb-easy-live-pickable')) return;
                var s2 = samplePickCanvas(e, media);
                if (!s2) return;
                if (els.loupe) els.loupe.hidden = true;
                if (_protectMode) { protectAt(s2.x, s2.y); return; }   // [E25]
                addColorZone(s2.rgb, s2.hex);
            });
        }
    }

    function addColorZone(rgb, hex) {
        undoPush('Easy Mode: pick color ' + hex);
        var n = easyColorZones().length + 1;
        var z = {
            id: (typeof _newZoneId === 'function') ? _newZoneId() : ('easyc_' + n),
            name: 'Color ' + n,
            color: { color_rgb: rgb.slice(), tolerance: TOL_DEFAULT },
            colorMode: 'picker',
            pickerColor: hex,
            pickerTolerance: TOL_DEFAULT,
            base: null, pattern: 'none', finish: null,
            intensity: '100',
            customSpec: null, customPaint: null, customBright: null,
            colors: [], regionMask: null,
            lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
            patternStack: [],
        };
        try {
            zones.push(z);
            selectedZoneIndex = zones.length - 1;
            if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'easy-mode by-color');
        } catch (e) {
            try { console.error('[spbEasy] addColorZone failed:', e); } catch (e2) {}
            return;
        }
        bc.zoneIdx = zones.length - 1;
        bc.phase = 'color';
        bc.pickerFor = 'finish';
        bc.recolorOpen = false;
        _searchText = '';
        // [2026-08-06 easy-loop #5] was _catalogMode = true — BY COLOR skipped
        // the visual STARTER SHELF straight into collapsed text-only sections,
        // so the most visual decision in the app started with zero pictures.
        // Land on the 50 hand-picked visual looks; FULL CATALOG stays 1 click.
        _catalogMode = false;
        refreshZonesUI();
        renderRail();
        flashColorReach(rgb, TOL_DEFAULT);
        window.requestAnimationFrame(function () {
            var keepColor = $('spbEasyKeepColor');
            if (keepColor) keepColor.focus();
        });
    }

    function removeColorZone(zi) {
        var z = zones[zi];
        if (!z) return;
        undoPush('Easy Mode: remove ' + (z.name || 'color'));
        try {
            zones.splice(zi, 1);
            selectedZoneIndex = Math.max(0, Math.min(selectedZoneIndex, zones.length - 1));
        } catch (e) { return; }
        if (bc.zoneIdx === zi) { bc.zoneIdx = -1; bc.phase = easyColorZones().length ? 'options' : 'pick'; bc.recolorOpen = false; }
        else if (bc.zoneIdx > zi) bc.zoneIdx--;
        if (bc.phase === 'options' && bc.zoneIdx < 0) {
            var rest = easyColorZones();
            bc.zoneIdx = rest.length ? rest[rest.length - 1].i : -1;
            if (bc.zoneIdx < 0) bc.phase = 'pick';
        }
        refreshZonesUI();
        kickPreview();
        renderRail();
    }

    function setZoneFinish(zi, key) {
        var z = zones[zi], f = finishInfo(key);
        if (!z || !f) return;
        undoPush('Easy Mode: ' + (z.name || 'color') + ' → ' + f.name);
        if (f.type === 'monolithic') { z.finish = f.id; z.base = null; }
        else { z.base = f.id; z.finish = null; }
        delete z._easyPendingColorPreview;
        z.pattern = 'none';
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(zones, 'easy-mode by-color finish'); } catch (e) {}
        refreshZonesUI();
        kickPreview();
        bc.phase = 'options';
        renderRail();
    }

    function setZoneBorrowedColors(zi, key) {
        var z = zones[zi], f = finishInfo(key);
        // [2026-08-08 iter9] was type!=='base' only — the borrow library now
        // offers SPECIALS as well (owner 2026-08-06 precedent on the sculpt
        // browser: "ANY Base or Special should be in there"); the engine's
        // color-source transform takes base: and mono: alike.
        if (!z || !f || (f.type !== 'base' && f.type !== 'monolithic')) return;
        undoPush('Easy Mode: base color → ' + f.name);
        z.baseColorMode = 'special';
        z.baseColor = null;
        z.baseColorSource = (f.type === 'monolithic' ? 'mono:' : 'base:') + f.id;
        if (!z.base && !z.finish) z._easyPendingColorPreview = true;
        else delete z._easyPendingColorPreview;
        if (z.baseColorStrength == null) z.baseColorStrength = 1;
        refreshZonesUI();
        kickPreview();
        bc.phase = 'color';
        bc.pickerFor = 'finish';
        renderRail();
        // instant feedback: tint the matched pixels with the borrowed look's
        // catalog color while the real render is out of reach (no finish yet)
        try {
            if (/^#[0-9a-fA-F]{6}$/.test(f.swatch || '')) {
                var tint = [parseInt(f.swatch.slice(1, 3), 16), parseInt(f.swatch.slice(3, 5), 16), parseInt(f.swatch.slice(5, 7), 16), 230];
                _paintReachOverlay(z.color && z.color.color_rgb, z.pickerTolerance != null ? z.pickerTolerance : TOL_DEFAULT,
                    tint, (f.name || 'BORROWED COLOR').toUpperCase().slice(0, 26) + ' PREVIEW (~{pct}% of your paint)');
            }
        } catch (e) {}
    }

    function setZoneRecolor(zi, hexOrNull) {
        var z = zones[zi];
        if (!z) return;
        if (hexOrNull) {
            z.baseColorMode = 'solid';
            z.baseColor = hexOrNull;
            z.baseColorSource = null;
            if (!z.base && !z.finish) z._easyPendingColorPreview = true;
            else delete z._easyPendingColorPreview;
            if (z.baseColorStrength == null) z.baseColorStrength = 1;
        } else {
            z.baseColorMode = null;   // absent → 'source' (keep the car's color)
            z.baseColor = null;
            z.baseColorSource = null;
            delete z._easyPendingColorPreview;
        }
        kickPreviewDebounced();
    }

    function setZoneTolerance(zi, tol) {
        var z = zones[zi];
        if (!z) return;
        tol = Math.max(0, Math.min(100, tol | 0));
        z.pickerTolerance = tol;
        if (z.color && typeof z.color === 'object' && z.color.color_rgb) z.color.tolerance = tol;
        kickPreviewDebounced();
    }

    // [SPB-EASY-STAGE2 2026-08-27] the pane cards must HUG their square art. With flex-basis
    // auto the 2048-buffer canvases inflate each card's intrinsic width ~130px past the square
    // (dark slab margins — the owner's "wasted space"). Measure the real square (card height
    // minus header chrome) and publish it as --spb-pane; the browse CSS pins the media width to
    // it, which collapses each card to art + padding.
    function sizeBrowsePanes() {
        var proof = $('spbEasyProof');
        if (!proof) return;
        if (!document.body.classList.contains('spb-easy-browse')) { proof.style.removeProperty('--spb-pane'); return; }
        var card = proof.querySelector('.spb-easy-source-card');
        var media = card ? card.querySelector('.spb-easy-proof-media') : null;
        if (!card || !media || !card.offsetParent) return;
        var cr = card.getBoundingClientRect();
        var mr = media.getBoundingClientRect();
        if (!cr.height) return;
        var chrome = Math.max(24, Math.min(120, (mr.top - cr.top) + 10)); // header stack + card bottom padding
        var pane = Math.floor(Math.min(cr.height - chrome, window.innerWidth * 0.40));
        if (pane < 100) return;
        proof.style.setProperty('--spb-pane', pane + 'px');
    }
    var _paneResizeWired = false;
    function wirePaneResize() {
        if (_paneResizeWired) return;
        _paneResizeWired = true;
        var raf = 0;
        window.addEventListener('resize', function () {
            if (raf) return;
            raf = requestAnimationFrame(function () { raf = 0; sizeBrowsePanes(); });
        });
    }

    // ---------------------------------------------------------- stage / empty
    function syncStage() {
        if (!_built) return;
        if (state.view === 'sculpt') return; // dedicated module owns the hero stage
        var byColor = _active && (state.view === 'bycolor' || state.view === 'auto') && paintLoaded();   // [SPB-EASY-AUTO 2026-09-19] auto = by-color stage, no picking
        var wholeProof = _active && state.view === 'whole' && paintLoaded() && !!detectWholeApplied();
        var sourceOnly = _active && paintLoaded() && (state.view === 'fork' || (state.view === 'whole' && !wholeProof));
        var proofMode = byColor || wholeProof;
        var picking = byColor && state.view === 'bycolor' && bc.phase === 'pick';
        els.stage.classList.toggle('spb-easy-proof-on', proofMode);
        // [SPB-EASY-STAGE 2026-08-26] channels visible whenever a paint is loaded (owner:
        // 'seeing them good at all times'), not only once a finish is applied
        els.stage.classList.toggle('spb-easy-haspaint', !!paintLoaded());
        if (paintLoaded()) {
            ensureSourceCanvas(function (ready) {
                // Source decoding can finish after the current spec image has
                // already fired its load event. Retry the material proof from
                // this callback so the first Whole Car visit cannot get stuck
                // showing an untouched source canvas.
                if (ready && _active && state.view === 'whole') renderWholeMaterialPreview();
                if (ready) {
                    var benchC = $('spbEasySourceCanvas'), benchS = $('spbEasySideSheet');
                    if (benchC && benchS && benchC.width > 300) benchS.textContent = benchC.width + ' × ' + benchC.height;
                }
            });
        }
        // A deliberate color choice is a real live-preview edit before the user
        // chooses its final material. Save/completion still requires base/finish.
        var byColorHasMaterial = byColor && easyColorZones().some(function (p) { return !!(p.z.base || p.z.finish || p.z._easyPendingColorPreview); });
        var liveTitle = $('spbEasyLiveTitle');
        var liveSubtitle = $('spbEasyLiveSubtitle');
        var simNote = $('spbEasyMaterialSimNote');
        // [SPB-EASY-STAGE2 2026-08-27] in browse the SOURCE pane is visible pre-finish too, so
        // the live pane keeps its real name and points at the catalog instead of duplicating YOUR PAINT
        var browseSourceOnly = sourceOnly && state.view === 'whole';
        if (liveTitle) liveTitle.textContent = wholeProof ? 'MATERIAL PREVIEW' : (browseSourceOnly ? 'LIVE PREVIEW' : (sourceOnly ? 'YOUR PAINT' : 'LIVE PREVIEW'));
        if (liveSubtitle) liveSubtitle.textContent = wholeProof ? 'How it will really look · your painted colors stay exactly as they are' : (browseSourceOnly ? 'Pick a finish below — updates here, live' : (sourceOnly ? 'Ready for your finish' : 'What your paint becomes'));
        var sideFile = $('spbEasySideFile'), sideCar = $('spbEasySideCar'), sideSheet = $('spbEasySideSheet');
        if (sideFile) {
            var sidePn = '';
            try { sidePn = String((typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || '').replace(/\\/g, '/').split('/').pop(); } catch (e) {}
            sideFile.textContent = sidePn || (paintLoaded() ? 'loaded' : 'not loaded yet');
            if (sidePn) sideFile.title = sidePn;
        }
        if (sideCar) {
            var sideCarRec = null;
            try { sideCarRec = currentCarRecord(); } catch (e) {}
            sideCar.textContent = sideCarRec ? sideCarRec.name : 'pick below';
        }
        if (sideSheet) {
            var sideSrcC = $('spbEasySourceCanvas');
            sideSheet.textContent = (sideSrcC && sideSrcC.width > 300) ? (sideSrcC.width + ' × ' + sideSrcC.height) : '2048 × 2048';
        }
        if (simNote) simNote.hidden = !wholeProof;
        if (els.liveCanvas) els.liveCanvas.hidden = !(wholeProof || sourceOnly || (byColor && !byColorHasMaterial));
        if (els.previewImg) els.previewImg.hidden = wholeProof || sourceOnly || !byColorHasMaterial;
        if (proofMode || paintLoaded()) syncSpecProof();
        if (!picking && !els.pickCanvas.hidden) setPickMode(false);
        var hints = {
            fork: 'Live preview — pick a path on the right',
            whole: wholeProof ? 'Material lighting proof — no spotlight, no recolor; the real spec channels drive this simulation' : 'Tap any finish below — your paint colors stay untouched',
            bycolor: 'Live preview — colors you haven’t touched stay exactly as painted',
        };
        els.stageHint.textContent = hints[state.view] || '';
        wirePaneResize();
        sizeBrowsePanes();
    }

    function openPaint() {
        try { if (typeof openPaintFilePicker === 'function') { openPaintFilePicker(); return; } } catch (e) {}
        try { console.warn('[spbEasy] openPaintFilePicker unavailable'); } catch (e) {}
    }
    function startBlankCanvas() {
        var btn = $('spbEasyBlankCanvas');
        if (btn) { btn.disabled = true; btn.textContent = 'Setting up your canvas…'; }
        try {
            if (typeof loadBlankCanvas === 'function') {
                Promise.resolve(loadBlankCanvas()).catch(function () {}).then(function () {
                    if (btn) { btn.disabled = false; btn.textContent = '🎨 Start with a blank canvas'; }
                });
            }
        } catch (e) {
            if (btn) { btn.disabled = false; btn.textContent = '🎨 Start with a blank canvas'; }
        }
    }
    function syncEmptyState() {
        if (!_built) return;
        if (state.view === 'sculpt') return; // accepts its own PSD/TGA/PNG/JPG source
        var loaded = paintLoaded();
        // [GAUNTLET F4 2026-08-20] This tracked only the BOOLEAN "is a paint
        // loaded", so swapping one paint for another (true -> true) returned
        // early and nothing re-ran. MEASURED by loading a real
        // car_num_23371.tga over the bundled example: the number-mode detection
        // never fired and its explanatory note never appeared — the mode only
        // looked right because the config default happened to match. Track the
        // PATH, so a different paint is treated as the new evidence it is.
        var pathNow = '';
        try {
            pathNow = (typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || '';
        } catch (e) {}
        var key = (loaded ? '1' : '0') + '|' + pathNow;
        if (key === _lastPaintLoaded) return;
        var hadPaintBefore = typeof _lastPaintLoaded === 'string' && _lastPaintLoaded.charAt(0) === '1';
        _lastPaintLoaded = key;
        // [GAUNTLET B1] A new paint is new evidence: re-run the number detection
        // (still a no-op once the buyer has chosen for themselves).
        try { applyDetectedNumberMode(); } catch (e) {}
        // A different paint under a live session means the rail's own rendered
        // state (the number note, the file proof) is stale.
        if (loaded && hadPaintBefore && _active) {
            try { renderRail(); } catch (e) {}
        }
        els.empty.hidden = loaded;
        els.previewImg.hidden = !loaded || state.view === 'whole' || state.view === 'fork' || !els.previewImg.getAttribute('src');
        els.stageHint.hidden = !loaded;
        refreshSaveEls();
        if (loaded) {
            kickPreview();
            if (state.view === 'bycolor' && bc.phase === 'pick') setPickMode(true);
            syncStage();
        }
    }
    // [GAUNTLET C8 2026-08-20] The file-name proof is rendered ONCE, from an ID
    // that /config has not delivered yet - MEASURED at rest on a real boot it read
    // "Will verify car_num_.tga + car_spec_.tga" and stayed that way until the
    // buyer typed in the ID field. The one line whose entire job is to be
    // trustworthy was showing an impossible filename. Now it re-renders whenever
    // the answer changes.
    function syncFileProof() {
        var proof = $('spbEasyFileProof');
        if (!proof) return;
        var names = expectedOutputNames();
        var html = 'Will verify <b>' + esc(names[0]) + '</b> + <b>' + esc(names[1]) + '</b>';
        if (proof.innerHTML !== html) proof.innerHTML = html;
    }

    function syncIdRow() {
        // [GAUNTLET C8 2026-08-20] Always visible (see the render comment). This
        // now only mirrors the live value and flags an unusable one, instead of
        // hiding the only way to fix it.
        if (!_built || !els.idRow) return;
        var idEl = $('iracingId');
        var val = idEl ? String(idEl.value || '').trim() : '';
        els.idRow.hidden = false;
        els.idRow.classList.toggle('spb-easy-id-row-bad', !idIsValid(val));
        if (els.idInput && document.activeElement !== els.idInput && els.idInput.value !== val) {
            els.idInput.value = val;
        }
        syncFileProof();
    }

    // -------------------------------------------------------- preview mirror
    function installPreviewMirror() {
        var src = $('livePreviewImg');
        if (src) {
            new MutationObserver(function () { syncPreviewNow(); })
                .observe(src, { attributes: true, attributeFilter: ['src'] });
        }
        var spec = $('livePreviewSpecImg');
        if (spec) {
            spec.addEventListener('load', syncSpecProof);
            new MutationObserver(function () { if (spec.complete) syncSpecProof(); })
                .observe(spec, { attributes: true, attributeFilter: ['src'] });
        }
        var spinner = $('previewSpinner');
        if (spinner) {
            new MutationObserver(function () {
                if (!_active) return;
                els.stage.classList.toggle('spb-easy-painting', spinner.style.display !== 'none');
            }).observe(spinner, { attributes: true, attributeFilter: ['style'] });
        }
    }
    function syncPreviewNow() {
        if (!_built) return;
        var src = $('livePreviewImg');
        var url = src ? src.getAttribute('src') : null;
        if (url) {
            if (els.previewImg.getAttribute('src') !== url) els.previewImg.src = url;
            if (_active && paintLoaded()) {
                if (state.view === 'whole') {
                    els.previewImg.hidden = true;
                    renderWholeMaterialPreview();
                } else if (state.view === 'fork') {
                    // The fork promises YOUR PAINT, not the last rendered
                    // recipe that happens to remain in Pro's preview image.
                    els.previewImg.hidden = true;
                } else if (state.view === 'bycolor') {
                    var hasByColorDecision = easyColorZones().some(function (p) { return p.z.base || p.z.finish || p.z._easyPendingColorPreview; });
                    els.previewImg.hidden = !hasByColorDecision;
                    els.liveCanvas.hidden = hasByColorDecision;
                } else {
                    els.previewImg.hidden = false;
                }
            }
            syncSpecProof();
        } else {
            els.previewImg.removeAttribute('src');
            els.previewImg.hidden = true;
        }
    }

    // ------------------------------------------------------------- save flow
    // [2026-08-08 E31] Saving REPLACES whatever paint that car folder already
    // has. The server does keep a copy as ORIGINAL_<name> (first save only),
    // but the buyer was never told any of it: not that something was about to
    // be overwritten, not that a copy was kept, not how to put it back. A
    // measured test save wrote 14 files including 7 ORIGINAL_* without a word.
    // One preflight, once per destination, in plain language.
    var _overwriteOk = {};          // "path|names" the buyer has already agreed to
    var _pendingSave = null;

    function checkFileOnDisk(path) {
        var base = '';
        try { base = (window.ShokkerAPI && window.ShokkerAPI.baseUrl) || ''; } catch (e) {}
        return fetch(base + '/check-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        }).then(function (r) { return r.json(); }).catch(function () { return null; });
    }
    function joinPath(dir, name) {
        return String(dir || '').replace(/[\\/]+$/, '') + '\\' + name;
    }
    function overwriteKey(route, names) { return normalizePath(route.path) + '|' + names.join(','); }

    // Resolves to null when nothing would be replaced, or a description of
    // exactly what is there. Never blocks the save on a failed lookup: if we
    // cannot read the folder we must not invent a warning about it.
    function preflightOverwrite(route, names) {
        var wanted = names.map(function (n) { return { name: n, path: joinPath(route.path, n) }; });
        var originals = names.map(function (n) { return { name: 'ORIGINAL_' + n, path: joinPath(route.path, 'ORIGINAL_' + n) }; });
        return Promise.all(wanted.concat(originals).map(function (f) {
            return checkFileOnDisk(f.path).then(function (r) {
                return { name: f.name, exists: !!(r && r.exists && r.is_file), size: (r && r.size_human) || '' };
            });
        })).then(function (rows) {
            var current = rows.slice(0, names.length).filter(function (r) { return r.exists; });
            var kept = rows.slice(names.length).filter(function (r) { return r.exists; });
            if (!current.length) return null;                 // nothing to replace
            return { current: current, kept: kept, route: route, names: names };
        });
    }

    function openOverwriteDialog(info) {
        var back = $('spbEasyOverwriteBackdrop');
        if (!back) return false;
        var body = $('spbEasyOverwriteBody');
        if (body) {
            // [GAUNTLET B9 2026-08-20] Reassurance FIRST. The buyer's actual
            // question at this modal is "am I about to destroy something?", and
            // the answer is no - so answer it before listing anything.
            var files = info.current.map(function (f) {
                return '<li><b>' + esc(f.name) + '</b>' + (f.size ? ' <span>' + esc(f.size) + '</span>' : '') + '</li>';
            }).join('');
            var keptName = info.kept.length ? info.kept[0].name : ('ORIGINAL_' + info.names[0]);
            var safety = info.kept.length
                ? 'Your original paint for this car is already saved as <b>' + esc(keptName) +
                  '</b>. This will not touch it.'
                : 'Shokker will save what is on the car now as <b>' + esc(keptName) +
                  '</b> first, so you can always get it back.';
            body.innerHTML =
                '<p class="spb-easy-ow-good"><b>\u2713 Your old paint is safe.</b><br>' + safety + '</p>' +
                '<p><b>' + esc(friendlyCarName(info.route.name) || info.route.name) +
                '</b> already has a paint on it. Saving puts your new one on instead:</p>' +
                '<ul class="spb-easy-ow-files">' + files + '</ul>' +
                '<details class="spb-easy-ow-how"><summary>How do I put the old one back?</summary>' +
                '<div>Open the folder below, delete the new <b>' + esc(info.names[0]) +
                '</b>, then rename <b>' + esc(keptName) + '</b> back to <b>' + esc(info.names[0]) + '</b>.</div>' +
                '</details>' +
                '<p class="spb-easy-ow-where">' + esc(info.route.path) + '</p>';
        }
        back.hidden = false;
        var go = $('spbEasyOverwriteGo');
        if (go) { try { go.focus(); } catch (e) {} }
        return true;
    }
    function closeOverwriteDialog() {
        var back = $('spbEasyOverwriteBackdrop');
        if (back) back.hidden = true;
        _pendingSave = null;
    }
    function wireOverwrite() {
        var back = $('spbEasyOverwriteBackdrop');
        if (!back) return;
        back.addEventListener('click', function (e) { if (e.target === back) closeOverwriteDialog(); });
        var no = $('spbEasyOverwriteCancel');
        if (no) no.addEventListener('click', closeOverwriteDialog);
        var go = $('spbEasyOverwriteGo');
        if (go) go.addEventListener('click', function () {
            var pending = _pendingSave;
            closeOverwriteDialog();
            if (!pending) return;
            _overwriteOk[pending.key] = true;
            onSaveClick();
        });
    }

    function onSaveClick() {
        if (_saving || !els.save) return;
        if (!paintLoaded()) { syncEmptyState(); return; }
        syncProtectZones();   // [E25] the saved TGA must respect the shield too
        var idEl = $('iracingId');
        var idVal = idEl ? String(idEl.value || '').trim() : '';
        if (!idIsValid(idVal)) {
            if (els.idRow) els.idRow.hidden = false;
            try { els.idInput.focus(); } catch (e) {}
            return;
        }
        var route = currentCarRecord();
        if (!route) {
            var carSelect = $('spbEasyCarSelect');
            var routeHint = $('spbEasySaveHint');
            if (routeHint) routeHint.textContent = 'Choose the exact iRacing car first — no guessing.';
            try { if (carSelect) carSelect.focus(); } catch (e) {}
            return;
        }
        var incomplete = state.view === 'bycolor' && easyColorZones().some(function (p) { return !(p.z.base || p.z.finish); });
        if (incomplete) {
            var incompleteHint = $('spbEasySaveHint');
            if (incompleteHint) incompleteHint.textContent = 'Finish or remove the color marked NEEDS A FINISH first.';
            return;
        }
        var hasWork = detectWholeApplied() ||
            easyColorZones().some(function (p) { return p.z.base || p.z.finish; }) ||
            (Array.isArray(zones) && zones.some(function (z) { return z && (z.base || z.finish || (z.pattern && z.pattern !== 'none')); }));
        if (!hasWork) {
            var hint = $('spbEasySaveHint');
            if (hint) hint.textContent = 'Pick a finish first ↑ then save.';
            return;
        }
        // A design saved by the retired single-finish Whole flow may still
        // carry a legacy base/finish zone that can repaint diffuse color. The
        // new Whole Car promise is spec-only, so an explicit SAVE upgrades
        // that one row synchronously before the render payload is built. Just
        // opening the screen still remains a zero-mutation navigation action.
        var legacyWhole = state.view === 'whole' ? readLegacyWholeMaterialPlan() : null;
        if (legacyWhole) {
            hydrateWholeState(legacyWhole);
            applyWholeStack(true, false, true);
        }
        // [E31] Ask before replacing, once per destination. The lookup is
        // async, so the first click arms it and the dialog's own button
        // re-enters here with permission recorded.
        var _names = expectedOutputNames();
        var _owKey = overwriteKey(route, _names);
        if (!_overwriteOk[_owKey] && !_pendingSave) {
            _pendingSave = { key: _owKey };
            var hintEl = $('spbEasySaveHint');
            if (hintEl) hintEl.textContent = 'Checking that car folder…';
            preflightOverwrite(route, _names).then(function (info) {
                if (hintEl) hintEl.textContent = '';
                if (!info) {                       // nothing there — just save
                    _overwriteOk[_owKey] = true;
                    _pendingSave = null;
                    onSaveClick();
                    return;
                }
                if (!openOverwriteDialog(info)) {   // no dialog? never block the save
                    _overwriteOk[_owKey] = true;
                    _pendingSave = null;
                    onSaveClick();
                }
            }).catch(function () {                  // unreadable folder is not a warning
                if (hintEl) hintEl.textContent = '';
                _overwriteOk[_owKey] = true;
                _pendingSave = null;
                onSaveClick();
            });
            return;
        }

        _saveExpected = { path: route.path, car: route.name, names: _names };
        _saving = true;
        _watchdogSawProgress = false;
        els.save.disabled = true;
        els.save.textContent = 'PAINTING…';
        els.progress.classList.add('active');
        els.progressFill.style.width = '2%';
        els.progressText.textContent = 'Sending your car to the paint shop…';
        startProgressMirror();
        _watchdogTimer = setTimeout(function () {
            if (_saving && !_watchdogSawProgress) {
                finishSave(false, { message: 'The render never started. The paint engine may still be warming up — give it a few seconds and hit SAVE again.' });
            }
        }, SAVE_WATCHDOG_MS);
        try {
            if (typeof safeDoRender === 'function') safeDoRender();
            else finishSave(false, { message: 'The render engine isn’t loaded yet. Try again in a moment.' });
        } catch (e) {
            finishSave(false, { message: 'Something went wrong starting the render.' });
        }
    }
    function startProgressMirror() {
        stopProgressMirror();
        _progressTimer = setInterval(function () {
            if (!_saving || !els.progressFill) return;
            var bar = $('renderProgressBar');
            var pct = parseFloat(bar && bar.style ? String(bar.style.width || '') : '');
            if (isFinite(pct) && pct > 0) {
                _watchdogSawProgress = true;
                els.progressFill.style.width = Math.max(2, Math.min(99, pct)) + '%';
                els.progressText.textContent = pct >= 99 ? 'Almost done…' : ('Painting your car… ' + Math.round(pct) + '%');
            }
        }, PROGRESS_POLL_MS);
    }
    function stopProgressMirror() {
        if (_progressTimer) { clearInterval(_progressTimer); _progressTimer = null; }
        if (_watchdogTimer) { clearTimeout(_watchdogTimer); _watchdogTimer = null; }
    }
    function finishSave(success, opts) {
        if (!_saving) return;
        _saving = false;
        stopProgressMirror();
        if (els.progress) els.progress.classList.remove('active');
        if (els.save) els.save.textContent = 'SAVE TO iRACING';
        refreshSaveEls();
        showResult(success, opts || {});
    }
    // [2026-08-08 E32] The DONE panel printed the destination as text and left
    // the buyer to go find it themselves. The server already has a verified
    // opener (/api/spec-sculpt/open-folder — validates the path and opens the
    // parent of a file); it just had no caller. It needs the X-Shokker-Internal
    // marker header, without which it answers 403.
    var _lastSavedFolder = '';
    function openSavedFolder() {
        if (!_lastSavedFolder) return;
        var btn = $('spbEasyResultFolder');
        var base = '';
        try { base = (window.ShokkerAPI && window.ShokkerAPI.baseUrl) || ''; } catch (e) {}
        if (btn) { btn.disabled = true; btn.textContent = 'OPENING\u2026'; }
        fetch(base + '/api/spec-sculpt/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' },
            body: JSON.stringify({ path: _lastSavedFolder })
        }).then(function (r) { return r.json(); }).then(function (out) {
            if (btn) { btn.disabled = false; btn.textContent = '\u{1F4C2} OPEN THE FOLDER'; }
            if (!out || !out.success) {
                try {
                    if (window.showToast) window.showToast('Could not open that folder: ' +
                        ((out && out.error) || 'unknown'), 'info');
                } catch (e) {}
            }
        }).catch(function () {
            if (btn) { btn.disabled = false; btn.textContent = '\u{1F4C2} OPEN THE FOLDER'; }
            try { if (window.showToast) window.showToast('Could not open that folder', 'info'); } catch (e) {}
        });
    }

    function showResult(success, opts) {
        if (!_built || !_active) return;
        els.result.classList.toggle('success', !!success);
        els.result.classList.toggle('failure', !success);
        els.resultIcon.textContent = success ? '🏁' : '😅';
        var _retryHide = $('spbEasyResultRetry');
        if (_retryHide) _retryHide.hidden = true;
        _lastSavedFolder = (success && opts && opts.path) ? String(opts.path) : '';
        var _folderBtn = $('spbEasyResultFolder');
        if (_folderBtn) _folderBtn.hidden = !_lastSavedFolder;
        if (success) {
            var idEl = $('iracingId');
            var idVal = idEl ? String(idEl.value || '').trim() : '';
            // [GAUNTLET B2 2026-08-20] Lead with the ONE thing they must do next.
            // The filenames, the folder and the elapsed time are proof the save
            // really landed - worth keeping, worth verifying, not worth being the
            // first thing a buyer reads at the finish line.
            els.resultTitle.textContent = 'Your car is painted.';
            var extraLine = '';
            if (opts.extraDone && opts.extraDone.length) {
                extraLine += '<div class="spb-easy-result-extra">Also copied to <b>' +
                    esc(opts.extraDone.map(function (c) { return friendlyCarName(c); }).join(', ')) + '</b></div>';
            }
            if (opts.extraFailed && opts.extraFailed.length) {
                extraLine += '<div class="spb-easy-result-extra spb-easy-warn">Could not copy to ' +
                    esc(opts.extraFailed.map(function (c) { return friendlyCarName(c); }).join(', ')) + '</div>';
            }
            els.resultBody.innerHTML =
                '<div class="spb-easy-result-next"><b>Press Ctrl+R in iRacing</b>' +
                '<span>That reloads your paint so you can see it on the car.</span></div>' +
                '<div class="spb-easy-result-where">It is on <b>' + esc(opts.car ? friendlyCarName(opts.car) : 'your selected car') + '</b>' +
                (idVal ? (' as car <b>' + esc(idVal) + '</b>') : '') + '.</div>' +
                extraLine +
                '<details class="spb-easy-result-proof"><summary>What Shokker just wrote</summary>' +
                '<div>' + esc((opts.names && opts.names[0]) || ('car_num_' + idVal + '.tga')) + '<br>' +
                esc((opts.names && opts.names[1]) || ('car_spec_' + idVal + '.tga')) + '<br>' +
                'in ' + esc(opts.path || 'your iRacing paint folder') +
                (opts.elapsed ? ('<br>verified in ' + esc(Number(opts.elapsed).toFixed(1)) + 's') : '') +
                '</div></details>';
        } else {
            var _retryBtn = $('spbEasyResultRetry');
            if (_retryBtn) _retryBtn.hidden = false;
            els.resultTitle.textContent = 'That didn’t work';
            els.resultBody.textContent = (opts && opts.message) || 'The render didn’t finish. Try again — or open Pro Mode to see the details.';
        }
        els.resultBackdrop.hidden = false;
    }
    // ===================================================== SAFETY (2026-08-08)
    // [E1] Easy Mode had NO undo: no button, and Ctrl+Z did nothing because
    // installKeyFilter swallows keys outside the Easy root. Every mis-click was
    // permanent. undoPush() was already recording to Pro's zoneUndoStack the
    // whole time — nothing ever popped it. These reach that stack and then make
    // Easy re-read the world (zones can appear/disappear, so bc.zoneIdx and the
    // by-color phase are reconciled before the rail re-renders).
    function _historyDepth(which) {
        try {
            var st = which === 'redo' ? zoneRedoStack : zoneUndoStack;   // global lexical
            return Array.isArray(st) ? st.length : 0;
        } catch (e) { return 0; }
    }
    function _historyLabel() {
        try {
            var st = zoneUndoStack;
            var top = st && st.length ? st[st.length - 1] : null;
            var raw = top && top.label ? String(top.label) : '';
            return raw.replace(/^Easy Mode:\s*/i, '').slice(0, 30);
        } catch (e) { return ''; }
    }
    function syncHistoryUI() {
        var u = $('spbEasyUndo'), r = $('spbEasyRedo'), w = $('spbEasyUndoWhat');
        if (u) u.disabled = _historyDepth('undo') === 0;
        if (r) r.disabled = _historyDepth('redo') === 0;
        if (w) w.textContent = _historyDepth('undo') ? _historyLabel() : '';
        var tag = $('spbEasySavedTag');
        if (tag) tag.hidden = !(paintLoaded() && (_historyDepth('undo') > 0));
    }
    function _reconcileAfterHistory() {
        try {
            var pairs = easyColorZones();
            if (state.view === 'bycolor') {
                var stillThere = pairs.some(function (p) { return p.i === bc.zoneIdx; });
                if (!stillThere) {
                    bc.zoneIdx = pairs.length ? pairs[pairs.length - 1].i : -1;
                    bc.phase = pairs.length ? 'options' : 'pick';
                    bc.recolorOpen = false;
                }
            }
            var plan = readWholeMaterialPlan() || readLegacyWholeMaterialPlan();
            if (state.view === 'whole') {
                if (plan) hydrateWholeState(plan);
                else { state.wholeStack = []; }
            }
        } catch (e) {}
        if (state.view === 'auto' && window.spbEasyAuto && typeof window.spbEasyAuto.resync === 'function') { try { window.spbEasyAuto.resync(); } catch (e) {} }   // [SPB-EASY-R7] picks / layers / reach / owner map follow the history
        refreshZonesUI();
        renderRail();
        kickPreview();
        syncHistoryUI();
    }
    function easyUndo() {
        if (_historyDepth('undo') === 0) return false;
        var label = _historyLabel();
        var ok = false;
        try { ok = (typeof undoZoneChange === 'function') ? undoZoneChange() !== false : false; } catch (e) { ok = false; }
        if (!ok) return false;
        clearRecolorOverlay();
        _reconcileAfterHistory();
        try { if (typeof window.showToast === 'function') window.showToast('Undone' + (label ? (': ' + label) : ''), 'info'); } catch (e) {}
        return true;
    }
    function easyRedo() {
        if (_historyDepth('redo') === 0) return false;
        var ok = false;
        try { ok = (typeof redoZoneChange === 'function') ? redoZoneChange() !== false : false; } catch (e) { ok = false; }
        if (!ok) return false;
        _reconcileAfterHistory();
        return true;
    }
    // [E3] A buyer four colors deep who hates the result had to delete each chip
    // one at a time. One button, one confirm, fully undoable (snapshot first).
    function easyStartOver() {
        var pairs = easyColorZones();
        var hasWork = pairs.length || detectWholeApplied() ||
            (Array.isArray(zones) && zones.some(function (z) { return z && (z.base || z.finish); }));
        if (!hasWork) { try { if (window.showToast) window.showToast('Nothing to clear yet', 'info'); } catch (e) {} return; }
        easyAsk({
            title: 'Start this car over?',
            body: 'This clears every color and finish you have picked. Your paint file is not ' +
                  'touched, and UNDO can bring it all back.',
            yes: 'START OVER', no: 'KEEP WHAT I HAVE', danger: true
        }).then(function (ok) { if (ok) _easyStartOverConfirmed(); });
    }
    function _easyStartOverConfirmed() {
        undoPush('Easy Mode: start over');
        try {
            for (var i = zones.length - 1; i >= 0; i--) {
                var z = zones[i];
                if (!z) continue;
                if (isEasyColorZone(z)) { zones.splice(i, 1); continue; }
                z.base = null; z.finish = null; z.pattern = 'none';
                z.materialStack = []; z.material_stack = [];
                z.baseColorMode = null; z.baseColor = null; z.baseColorSource = null;
                delete z._easyPendingColorPreview;
            }
            if (typeof selectedZoneIndex !== 'undefined') selectedZoneIndex = Math.max(0, Math.min(selectedZoneIndex, zones.length - 1));
        } catch (e) {}
        if (state.view === 'auto' && window.spbEasyAuto && typeof window.spbEasyAuto.startOver === 'function') {
            // [SPB-EASY-PBN 2026-09-22] Built-for-you: multi-colour parts and picks are not "Easy colour zones" to the
            // loop above, so they survived half-cleared. Start over = every auto part gone + a fresh build.
            try { window.spbEasyAuto.startOver(); } catch (e) {}
            persistState();
            return;
        }
        state.wholeStack = [];
        bc.zoneIdx = -1; bc.phase = 'pick'; bc.recolorOpen = false;
        clearRecolorOverlay();
        persistState();
        _reconcileAfterHistory();
    }
    // ================================================== INSPECT (2026-08-08)
    // [E6] Easy Mode had NO zoom anywhere: buyers judged 2048px of fine detail
    // in a half-width panel. [E7] and no way to A/B the same frame — only two
    // small panels side by side. One surface solves both: a full-screen canvas
    // that draws SOURCE and LIVE at true pixels with scroll-zoom / drag-pan and
    // a wipe between them (hold B = before). Draws straight from the existing
    // canvases/img — no data URLs, no extra fetch.
    var _insp = { open: false, mode: 'live', zoom: 1, x: 0, y: 0, wipe: 100,
                  drag: null, beforeOnly: false, raf: 0 };
    function _inspSources() {
        var src = els.sourceCanvas && els.sourceCanvas.width ? els.sourceCanvas : null;
        var after = null;
        if (els.previewImg && !els.previewImg.hidden && els.previewImg.naturalWidth) after = els.previewImg;
        else if (els.liveCanvas && els.liveCanvas.width) after = els.liveCanvas;
        return { src: src, after: after };
    }
    function _inspNatural() {
        var s2 = _inspSources();
        var n = s2.src || s2.after;
        if (!n) return { w: 0, h: 0 };
        return { w: n.naturalWidth || n.width, h: n.naturalHeight || n.height };
    }
    function inspectDraw() {
        if (!_insp.open) return;
        var cv = $('spbEasyInspectCanvas'), stage = $('spbEasyInspectStage');
        if (!cv || !stage) return;
        var rect = stage.getBoundingClientRect();
        var dpr = Math.min(2, window.devicePixelRatio || 1);
        if (cv.width !== Math.round(rect.width * dpr) || cv.height !== Math.round(rect.height * dpr)) {
            cv.width = Math.round(rect.width * dpr); cv.height = Math.round(rect.height * dpr);
            cv.style.width = rect.width + 'px'; cv.style.height = rect.height + 'px';
        }
        var ctx = cv.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, rect.width, rect.height);
        ctx.fillStyle = '#07070f';
        ctx.fillRect(0, 0, rect.width, rect.height);
        var nat = _inspNatural();
        if (!nat.w) return;
        var s2 = _inspSources();
        var w = nat.w * _insp.zoom, h = nat.h * _insp.zoom;
        var ox = (rect.width - w) / 2 + _insp.x, oy = (rect.height - h) / 2 + _insp.y;
        ctx.imageSmoothingEnabled = _insp.zoom < 2;   // crisp pixels when zoomed in
        var base = (_insp.mode === 'source') ? s2.src : (s2.src || s2.after);
        if (base) { try { ctx.drawImage(base, ox, oy, w, h); } catch (e) {} }
        var top = (_insp.mode === 'source') ? null : s2.after;
        if (top && !_insp.beforeOnly && top !== base) {
            var cut = rect.width * (_insp.wipe / 100);
            ctx.save();
            ctx.beginPath(); ctx.rect(0, 0, cut, rect.height); ctx.clip();
            try { ctx.drawImage(top, ox, oy, w, h); } catch (e) {}
            ctx.restore();
            if (_insp.wipe > 0 && _insp.wipe < 100) {
                ctx.fillStyle = 'rgba(255,255,255,0.85)';
                ctx.fillRect(cut - 1, 0, 2, rect.height);
            }
        } else if (top && !_insp.beforeOnly && top === base) {
            // live-only source (no separate before) — nothing extra to draw
        }
        var zl = $('spbEasyInspectZoom');
        if (zl) zl.textContent = Math.round(_insp.zoom * 100) + '%';
    }
    function inspectDrawSoon() {
        if (_insp.raf) return;
        _insp.raf = window.requestAnimationFrame(function () { _insp.raf = 0; inspectDraw(); });
    }
    function inspectFit() {
        var stage = $('spbEasyInspectStage'); var nat = _inspNatural();
        if (!stage || !nat.w) return;
        var r = stage.getBoundingClientRect();
        _insp.zoom = Math.min(r.width / nat.w, r.height / nat.h) * 0.98;
        _insp.x = 0; _insp.y = 0; inspectDraw();
    }
    function openInspector(mode) {
        var back = $('spbEasyInspectBackdrop');
        if (!back) return;
        var s2 = _inspSources();
        if (!s2.src && !s2.after) { try { if (window.showToast) window.showToast('Load a paint first', 'info'); } catch (e) {} return; }
        _insp.open = true; _insp.mode = mode || 'live'; _insp.beforeOnly = false; _insp.wipe = 100;
        var t = $('spbEasyInspectTitle');
        if (t) t.textContent = (_insp.mode === 'source') ? 'INSPECT · YOUR SOURCE PAINT' : 'INSPECT · BEFORE / AFTER';
        var foot = $('spbEasyInspectFoot');
        if (foot) foot.hidden = (_insp.mode === 'source') || !s2.after || !s2.src;
        var wipe = $('spbEasyWipe'); if (wipe) wipe.value = 100;
        var swap = $('spbEasyWipeSwap'); if (swap) swap.textContent = 'SHOW BEFORE ONLY';
        back.hidden = false;
        window.requestAnimationFrame(function () { inspectFit(); });
    }
    function closeInspector() {
        _insp.open = false;
        var back = $('spbEasyInspectBackdrop');
        if (back) back.hidden = true;
    }
    function wireInspector() {
        var back = $('spbEasyInspectBackdrop');
        var stage = $('spbEasyInspectStage');
        if (!back || !stage) return;
        back.addEventListener('click', function (e) { if (e.target === back) closeInspector(); });
        var closeBtn = $('spbEasyInspectClose');
        if (closeBtn) closeBtn.addEventListener('click', closeInspector);
        var fit = $('spbEasyInspectFit'); if (fit) fit.addEventListener('click', inspectFit);
        var one = $('spbEasyInspect1x');
        if (one) one.addEventListener('click', function () { _insp.zoom = 1; _insp.x = 0; _insp.y = 0; inspectDraw(); });
        stage.addEventListener('wheel', function (e) {
            if (!_insp.open) return;
            e.preventDefault();
            var factor = e.deltaY < 0 ? 1.16 : 1 / 1.16;
            var next = Math.max(0.05, Math.min(16, _insp.zoom * factor));
            _insp.zoom = next;
            inspectDrawSoon();
        }, { passive: false });
        stage.addEventListener('pointerdown', function (e) {
            if (!_insp.open) return;
            _insp.drag = { x: e.clientX, y: e.clientY, ox: _insp.x, oy: _insp.y };
            try { stage.setPointerCapture(e.pointerId); } catch (err) {}
            stage.classList.add('is-panning');
        });
        stage.addEventListener('pointermove', function (e) {
            if (!_insp.drag) return;
            _insp.x = _insp.drag.ox + (e.clientX - _insp.drag.x);
            _insp.y = _insp.drag.oy + (e.clientY - _insp.drag.y);
            inspectDrawSoon();
        });
        var endDrag = function () { _insp.drag = null; stage.classList.remove('is-panning'); };
        stage.addEventListener('pointerup', endDrag);
        stage.addEventListener('pointercancel', endDrag);
        stage.addEventListener('pointerleave', endDrag);
        var wipe = $('spbEasyWipe');
        if (wipe) wipe.addEventListener('input', function () {
            _insp.wipe = parseInt(wipe.value, 10) || 0; _insp.beforeOnly = false; inspectDrawSoon();
        });
        var swap = $('spbEasyWipeSwap');
        if (swap) swap.addEventListener('click', function () {
            _insp.beforeOnly = !_insp.beforeOnly;
            swap.textContent = _insp.beforeOnly ? 'SHOW THE RESULT' : 'SHOW BEFORE ONLY';
            inspectDraw();
        });
        // hold B for before (photographer's flip)
        document.addEventListener('keydown', function (e) {
            if (!_insp.open) return;
            if (e.key === 'Escape') { e.stopPropagation(); closeInspector(); return; }
            if ((e.key === 'b' || e.key === 'B') && !_insp.beforeOnly) { _insp.beforeOnly = true; inspectDraw(); }
        }, true);
        document.addEventListener('keyup', function (e) {
            if (!_insp.open) return;
            if ((e.key === 'b' || e.key === 'B') && _insp.beforeOnly) {
                var sw = $('spbEasyWipeSwap');
                if (!sw || sw.textContent.indexOf('RESULT') === -1) { _insp.beforeOnly = false; inspectDraw(); }
            }
        }, true);
        window.addEventListener('resize', function () { if (_insp.open) inspectDrawSoon(); });
        // the two INSPECT buttons on the proof cards
        var root = els.root || document;
        root.addEventListener('click', function (e) {
            var btn = e.target && e.target.closest ? e.target.closest('[data-inspect]') : null;
            if (!btn) return;
            e.preventDefault(); e.stopPropagation();
            openInspector(btn.getAttribute('data-inspect'));
        });
    }
    // ================================================== COMPARE (2026-08-08)
    // [E8] Browsing 2,782 looks with no way to hold two of them side by side is
    // the core "which one do I actually want" problem. A snapshot captures the
    // REAL rendered preview plus the plan that produced it (same plan format as
    // MY LOOKS), so choosing a card puts that exact look back on the car.
    var _cmp = [];
    var CMP_MAX = 4;
    function _cmpSourceNode() {
        if (els.previewImg && !els.previewImg.hidden && els.previewImg.naturalWidth) return els.previewImg;
        if (els.liveCanvas && els.liveCanvas.width) return els.liveCanvas;
        return null;
    }
    function _cmpLabel() {
        if (state.view === 'whole') {
            var names = normalizedWholeStack(state.wholeStack).map(function (r) {
                var f = finishInfo(r.key); return f ? f.name : '';
            }).filter(Boolean);
            return names.length ? names.join(' + ') : 'Whole car';
        }
        var pairs = easyColorZones().filter(function (p) { return p.z.base || p.z.finish; });
        if (!pairs.length) return 'Unfinished plan';
        var first = pairs[0].z;
        var f2 = finishInfo(first.finish ? finishKey('monolithic', first.finish) : finishKey('base', first.base));
        return (f2 ? f2.name : 'Look') + (pairs.length > 1 ? (' +' + (pairs.length - 1) + ' more') : '');
    }
    function captureCompare() {
        var node = _cmpSourceNode();
        if (!node) { try { if (window.showToast) window.showToast('Pick a finish first, then add it to compare', 'info'); } catch (e) {} return; }
        var url = '';
        try {
            var W = 560;
            var nw = node.naturalWidth || node.width, nh = node.naturalHeight || node.height;
            var c = document.createElement('canvas');
            c.width = W; c.height = Math.max(1, Math.round(nh * (W / nw)));
            c.getContext('2d').drawImage(node, 0, 0, c.width, c.height);
            url = c.toDataURL('image/jpeg', 0.85);
        } catch (e) { return; }
        _cmp.unshift({ label: _cmpLabel(), url: url, plan: capturePlan(_cmpLabel()) });
        if (_cmp.length > CMP_MAX) _cmp.length = CMP_MAX;
        renderCompareBar();
        try { if (window.showToast) window.showToast('Added to compare (' + _cmp.length + ' of ' + CMP_MAX + ')', 'success'); } catch (e) {}
    }
    function renderCompareBar() {
        var add = $('spbEasyCompareAdd'), open = $('spbEasyCompareOpen');
        if (add) add.textContent = '\u229e COMPARE' + (_cmp.length ? (' ' + _cmp.length + '/' + CMP_MAX) : '');
        if (open) { open.hidden = _cmp.length < 2; open.textContent = 'SEE ' + _cmp.length + ' SIDE BY SIDE'; }
    }
    function renderCompareGrid() {
        var grid = $('spbEasyCompareGrid');
        if (!grid) return;
        grid.innerHTML = _cmp.map(function (sn, i) {
            return '<figure class="spb-easy-compare-card">' +
                '<img src="' + sn.url + '" alt="' + esc(sn.label) + '">' +
                '<figcaption><b>' + esc(sn.label) + '</b>' +
                '<span><button type="button" data-cmp-use="' + i + '">USE THIS</button>' +
                '<button type="button" data-cmp-drop="' + i + '" title="Remove from compare">\u2715</button></span>' +
                '</figcaption></figure>';
        }).join('');
    }
    function openCompare() {
        if (_cmp.length < 2) { try { if (window.showToast) window.showToast('Add at least two looks to compare', 'info'); } catch (e) {} return; }
        renderCompareGrid();
        var back = $('spbEasyCompareBackdrop');
        if (back) back.hidden = false;
    }
    function closeCompare() { var b2 = $('spbEasyCompareBackdrop'); if (b2) b2.hidden = true; }
    function wireCompare() {
        var back = $('spbEasyCompareBackdrop');
        if (!back) return;
        back.addEventListener('click', function (e) { if (e.target === back) closeCompare(); });
        var cl = $('spbEasyCompareClose'); if (cl) cl.addEventListener('click', closeCompare);
        var clr = $('spbEasyCompareClear');
        if (clr) clr.addEventListener('click', function () { _cmp = []; renderCompareBar(); closeCompare(); });
        var grid = $('spbEasyCompareGrid');
        if (grid) grid.addEventListener('click', function (e) {
            var use = e.target && e.target.closest ? e.target.closest('[data-cmp-use]') : null;
            var drop = e.target && e.target.closest ? e.target.closest('[data-cmp-drop]') : null;
            if (use) {
                var i = parseInt(use.getAttribute('data-cmp-use'), 10);
                var snap = _cmp[i];
                closeCompare();
                if (snap && snap.plan) applyPlan(snap.plan);
                return;
            }
            if (drop) {
                var j = parseInt(drop.getAttribute('data-cmp-drop'), 10);
                _cmp.splice(j, 1);
                renderCompareBar();
                if (_cmp.length < 2) closeCompare(); else renderCompareGrid();
            }
        });
        document.addEventListener('keydown', function (e) {
            var b3 = $('spbEasyCompareBackdrop');
            if (!b3 || b3.hidden) return;
            if (e.key === 'Escape') { e.stopPropagation(); closeCompare(); }
        }, true);
    }
    function hideResult() {
        if (els.resultBackdrop) els.resultBackdrop.hidden = true;
    }
    function installRenderWraps() {
        if (_wrapsInstalled) return;
        _wrapsInstalled = true;
        if (typeof window.showRenderResults === 'function') {
            var origShow = window.showRenderResults;
            window.showRenderResults = function (result) {
                var ret, easySaveInFlight = _active && _saving;
                try { ret = origShow.apply(this, arguments); } catch (e) { throw e; }
                // SPB-EASY-DIRECT-RESULT-20260721 — owner: successful Easy
                // renders "should NOT go to the blurry screen" first. Pro's
                // showRenderResults still runs so history/preview state stays
                // truthful, then its recipe modal is closed synchronously
                // before the browser can paint it. Easy's verified result is
                // the one and only completion screen for Whole + By Color.
                if (easySaveInFlight) {
                    try {
                        if (typeof window.closeRenderResults === 'function') window.closeRenderResults();
                        else {
                            var proPanel = $('renderResultsPanel');
                            var proBackdrop = $('renderResultsBackdrop');
                            if (proPanel) proPanel.style.display = 'none';
                            if (proBackdrop) proBackdrop.style.display = 'none';
                        }
                    } catch (e2) {}
                }
                finallyEasySuccess(result);
                return ret;
            };
        }
        if (typeof window.RenderNotify !== 'undefined' && window.RenderNotify &&
            typeof window.RenderNotify.onRenderComplete === 'function') {
            var origNotify = window.RenderNotify.onRenderComplete.bind(window.RenderNotify);
            window.RenderNotify.onRenderComplete = function (success, elapsed, zoneCount) {
                try { origNotify(success, elapsed, zoneCount); } catch (e) {}
                if (_active && _saving && success === false) finishSave(false, {});
            };
        }
    }
    function finallyEasySuccess(result) {
        if (!_active || !_saving) return;
        try { _lastJobId = (result && result.job_id) || _lastJobId; } catch (e) {}
        var expected = _saveExpected;
        var out = result && result.output_dir;
        var files = out && Array.isArray(out.pushed_files) ? out.pushed_files.map(function (f) { return String(f || '').replace(/\\/g, '/').split('/').pop().toLowerCase(); }) : [];
        var correctPath = !!(expected && out && normalizePath(out.path) === normalizePath(expected.path));
        var correctFiles = !!(expected && expected.names.every(function (name) { return files.indexOf(name.toLowerCase()) !== -1; }));
        var verified = !!(result && result.success && out && out.success === true && out.verified === true && correctPath && correctFiles);
        if (!verified) {
            var reason = out && out.error ? out.error : (!correctPath ? 'The render did not confirm the selected car folder.' : (!correctFiles ? 'The render did not confirm both iRacing paint files.' : 'iRacing installation was not verified.'));
            finishSave(false, { message: reason + ' Easy Mode will not call this DONE until the exact folder and both filenames are verified.' });
            return;
        }
        var baseOpts = {
            pushed: true,
            elapsed: result && result.elapsed_seconds,
            path: out.path,
            car: expected.car,
            names: expected.names
        };
        if (_alsoCars.length && _lastJobId) {
            if (els.progressText) els.progressText.textContent = 'Copying to ' + _alsoCars.length + ' more car' + (_alsoCars.length === 1 ? '' : 's') + '\u2026';
            deployToExtraCars(_lastJobId, function (okCars, badCars) {
                baseOpts.extraDone = okCars;
                baseOpts.extraFailed = badCars;
                finishSave(true, baseOpts);
            });
            return;
        }
        finishSave(true, baseOpts);
    }
    // -------------------------------------------------------- input isolation
    function installKeyFilter() {
        if (_keyFilterInstalled) return;
        _keyFilterInstalled = true;
        // [2026-08-08 E1] Undo/redo hotkeys INSIDE Easy. Must run before the
        // isolation filter below (which stops every key that is not aimed at the
        // Easy root — that is exactly why Ctrl+Z did nothing before).
        document.addEventListener('keydown', function (e) {
            if (!_active) return;
            var typing = e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName || '');
            // [2026-08-08 E27] A share box is a control bound to the car, not
            // free text, so the browser's own field-level undo is wrong there:
            // MEASURED, it rewound the text 40 -> 70 while the car stayed at 40,
            // and the buyer was left reading a number the car did not have.
            // Search boxes and name fields keep native undo.
            var boundToCar = !!(e.target && e.target.hasAttribute && e.target.hasAttribute('data-mix-num'));
            if (typing && e.target.type !== 'range' && !boundToCar) return;
            if (!(e.ctrlKey || e.metaKey)) return;
            var k = (e.key || '').toLowerCase();
            if (k === 'z' && !e.shiftKey) { e.preventDefault(); e.stopPropagation(); easyUndo(); }
            else if ((k === 'z' && e.shiftKey) || k === 'y') { e.preventDefault(); e.stopPropagation(); easyRedo(); }
        }, true);
        document.addEventListener('keydown', function (e) {
            if (!_active) return;
            if (els.root && e.target instanceof Node && els.root.contains(e.target)) return;
            e.stopPropagation();
        }, true);
    }

    // -------------------------------------------------------------- mode I/O
    function readDisplayMode() {
        try {
            if ($('btnCanvasViewRendered') && $('btnCanvasViewRendered').getAttribute('aria-pressed') === 'true') return 'rendered';
            if ($('btnSplitView') && $('btnSplitView').getAttribute('aria-pressed') === 'true') return 'split';
        } catch (e) {}
        return 'source';
    }
    function startPaintPoll() {
        stopPaintPoll();
        _paintPollTimer = setInterval(function () {
            if (!_active) return;
            syncEmptyState();
            syncIdRow();
            // [SPB-LAYER-GAUNTLET C6b 2026-08-21] the CAR PARTS drawer renders '' when
            // the rail paints before the PSD finishes rasterizing - inject it once the
            // layers land instead of leaving the drawer missing for the session.
            try {
                if ((state.view === 'whole' || state.view === 'browse') && !$('spbEasyCarParts')
                    && typeof _psdLayers !== 'undefined' && window._psdLayersLoaded && _psdLayers.length) {
                    var _cpHtml = carPartsDrawerHtml();
                    var _tuneD = $('spbEasyTuneDrawer');
                    if (_cpHtml && _tuneD) {
                        _tuneD.insertAdjacentHTML('beforebegin', _cpHtml);
                        wireCarParts();
                    }
                }
            } catch (e) {}
            // [GAUNTLET B3 2026-08-20] The customer ID and the car list arrive
            // from /config AFTER the rail first renders. MEASURED 2.5s into a
            // fresh boot: SAVE read "ENTER YOUR CUSTOMER ID" and the WHERE IT
            // GOES drawer force-opened itself - then both silently corrected a
            // moment later. A blocker that is really just "not loaded yet" reads
            // as a real problem and makes the drawer flap open on every boot.
            // Re-evaluate when the answer actually changes, not on a timer alone.
            var idNow = idIsValid(($('iracingId') || {}).value) && !!currentCarRecord();
            if (idNow !== _lastDestReady) {
                _lastDestReady = idNow;
                refreshSaveEls();
            }
            // Pick mode retries until the source image lands — and re-mirrors
            // if Pro's canvas has since loaded at a different (real) size.
            if (state.view === 'bycolor' && bc.phase === 'pick' && paintLoaded()) {
                var pro = $('paintCanvas');
                var stale = pro && pro.width >= 512 && pro.width !== els.pickCanvas.width;
                if (els.pickCanvas.hidden || stale) setPickMode(true);
            }
        }, PAINT_POLL_MS);
    }
    function stopPaintPoll() {
        if (_paintPollTimer) { clearInterval(_paintPollTimer); _paintPollTimer = null; }
    }

    // [SPB-EASY-2026-08-19] Owner: "we could make Easy Mode easier to see maybe?"
    // The switch is now a segmented PRO | EASY control in the app-chrome header
    // (#spbModePill in paint-booth-v2.html), not a 40px button wedged between
    // Lasso and Magic Wand in the DRAWING TOOL row. Keep it truthful about which
    // view is live - a mode switch that does not show the current mode is just a
    // button. Safe to call before the markup exists (older shells).
    function syncModePill() {
        try {
            var pro = $('spbModeProBtn'), easy = $('spbModeEasyBtn');
            if (!pro || !easy) return;
            pro.classList.toggle('on', !_active);
            easy.classList.toggle('on', !!_active);
            pro.setAttribute('aria-pressed', _active ? 'false' : 'true');
            easy.setAttribute('aria-pressed', _active ? 'true' : 'false');
        } catch (e) {}
    }

    function enter() {
        if (_active) return;
        // [SPB-EASY-ISOLATION 2026-08-26] Easy is ITS OWN THING: park the Pro project
        // (full zone snapshot) and load Easy's own zone state BEFORE anything below
        // inspects or mutates zones. Owner: switching modes must never touch Pro work.
        try { if (window.spbEasyIsolation) window.spbEasyIsolation.enterEasy(); } catch (e) {}
        buildRoot();
        installRenderWraps();
        installKeyFilter();
        wireRailToggleOnce();   // [S37] survives whoever re-renders the rail
        _active = true;
        _savedDisplayMode = readDisplayMode();
        if (_savedDisplayMode === 'source') {
            try { if (typeof window.setCanvasDisplayMode === 'function') window.setCanvasDisplayMode('rendered'); } catch (e) {}
        }
        document.body.classList.add('spb-easy-on');
        syncRailToggle();   // [E40] a folded rail is remembered between visits
        // Move focus out of Pro before its permanent workspace becomes
        // aria-hidden/inert; Chromium otherwise rejects the ownership change
        // when the Easy Mode toolbar button still has focus.
        try { els.root.focus({ preventScroll: true }); } catch (e) { try { els.root.focus(); } catch (e2) {} }
        isolateProAccessibility();
        lsSet(LS_MODE, 'easy');
        hideResult();
        _lastPaintLoaded = null;
        _lastDestReady = null;
        _enteredAt = Date.now();
        _catalogMode = false;
        _searchText = '';
        // Resume where the design actually is (highlights never lie):
        // [SPB-EASY-AUTO ROUND 4 2026-09-19] Built-for-you IS Easy Mode: always land there (it builds the parts
        // itself, and shows the open-your-paint card before a paint is loaded). The whole-car / by-colour
        // stages stay in source but are no longer a destination.
        if (window.spbEasyAuto) { state.view = 'auto'; bc.phase = 'options'; }
        else if (easyColorZones().length) { state.view = 'bycolor'; bc = { phase: 'options', zoneIdx: easyColorZones()[0].i, pickerFor: 'finish' }; }
        else if (detectWholeApplied()) state.view = 'whole';
        renderRail();
        syncEmptyState();
        syncPreviewNow();
        startPaintPoll();
        syncModePill();
    }
    function exit() {
        if (!_active) return;
        _active = false;
        stopPaintPoll();
        hideResult();
        setPickMode(false);
        if (window.spbEasySculpt && typeof window.spbEasySculpt.unmount === 'function') window.spbEasySculpt.unmount();
        restoreProAccessibility();
        document.body.classList.remove('spb-easy-on');
        // [E40] never let a folded Easy rail follow the buyer into Pro Mode
        document.body.classList.remove('spb-easy-rail-hidden');
        document.body.classList.remove('spb-easy-browse');
        lsSet(LS_MODE, 'pro');
        try {
            var panel = $('renderResultsPanel');
            if (panel && panel.style && panel.style.display && panel.style.display !== 'none' && !_saving) {
                panel.style.display = 'none';
            }
        } catch (e) {}
        if (_savedDisplayMode === 'source') {
            try { if (typeof window.setCanvasDisplayMode === 'function') window.setCanvasDisplayMode('source'); } catch (e) {}
        }
        _savedDisplayMode = null;
        // [SPB-EASY-ISOLATION 2026-08-26] park Easy's zones in their own slot and put the
        // Pro project back byte-for-byte (masks included). Runs last so Easy teardown
        // above never sees the swapped state.
        try { if (window.spbEasyIsolation) window.spbEasyIsolation.exitEasy(); } catch (e) {}
        syncModePill();
    }
    function toggle() { if (_active) exit(); else enter(); }
    // [2026-08-08 E35] "Teach me the full app" used to call exit() and switch on
    // Pro's Training Wheels: the ONE buyer who admitted they needed help was the
    // one thrown into the deep end, losing the mode they were learning. A tour
    // that stays inside Easy teaches the thing they are actually using; Pro is
    // still one click away, but at the END, as a choice.
    var _tour = { on: false, step: 0, steps: [] };
    // [GAUNTLET D1 2026-08-20] Rewritten for the finish-first landing. The old
    // step 3 described the WHOLE CAR / BY COLOR / SPEC SCULPT fork, which stopped
    // being the first screen. Note startTour() filters to steps whose target is
    // actually on screen - on the old fork there was no SOURCE card and no SAVE
    // button, so a "4-step" tour silently showed 2. All five targets below exist
    // on the browse landing.
    var TOUR_STEPS = [
        {
            sel: '.spb-easy-source-card',
            title: 'THIS IS YOUR CAR, UNROLLED',
            body: 'A car paint is a flat sheet that gets wrapped onto the 3D car. This side is ' +
                  'exactly what you loaded — Shokker never changes it.'
        },
        {
            sel: '.spb-easy-live-card',
            title: 'THIS IS WHAT IT BECOMES',
            body: 'Every choice you make shows up here first. If you can see it here, that is ' +
                  'what iRacing will show.'
        },
        {
            sel: '.spb-easy-finishes',
            title: 'TAP ANY FINISH',
            body: 'One tap puts it on the whole car — that alone is a finished paint. Your ' +
                  'colors, numbers and decals stay exactly as you painted them. Want just one ' +
                  'color changed instead? Use ONE COLOR AT A TIME underneath.'
        },
        {
            sel: '.spb-easy-finder',
            title: 'OR JUST SAY WHAT YOU WANT',
            body: 'Type it in your own words — shiny, matte black, rust, gold, carbon. ' +
                  'FULL CATALOG opens all of them, grouped into families.'
        },
        {
            sel: '#spbEasySave',
            title: 'THEN SEND IT TO iRACING',
            body: 'Shokker writes both files, checks they really landed, and tells you to press ' +
                  'Ctrl+R. Nothing already in that folder is replaced without asking you first.'
        }
    ];

    function tourTargetRect(sel) {
        var el = document.querySelector(sel);
        if (!el) return null;
        var r = el.getBoundingClientRect();
        if (!r.width || !r.height) return null;
        return { el: el, r: r };
    }
    function drawTour() {
        var back = $('spbEasyTourBackdrop');
        if (!back) return;
        if (!_tour.on) { back.hidden = true; return; }
        var step = _tour.steps[_tour.step];
        var hit = step ? tourTargetRect(step.sel) : null;
        if (!hit) { nextTourStep(); return; }          // never stall on a missing target
        back.hidden = false;
        var pad = 6;
        var spot = $('spbEasyTourSpot');
        if (spot) {
            spot.style.left = (hit.r.left - pad) + 'px';
            spot.style.top = (hit.r.top - pad) + 'px';
            spot.style.width = (hit.r.width + pad * 2) + 'px';
            spot.style.height = (hit.r.height + pad * 2) + 'px';
        }
        var card = $('spbEasyTourCard');
        if (card) {
            var t = $('spbEasyTourTitle'), b2 = $('spbEasyTourBody'), n = $('spbEasyTourNum');
            if (t) t.textContent = step.title;
            if (b2) b2.textContent = step.body;
            if (n) n.textContent = (_tour.step + 1) + ' of ' + _tour.steps.length;
            var prev = $('spbEasyTourPrev'), next = $('spbEasyTourNext'), pro = $('spbEasyTourPro');
            if (prev) prev.disabled = _tour.step === 0;
            if (next) next.textContent = (_tour.step === _tour.steps.length - 1) ? 'GOT IT' : 'NEXT \u2192';
            if (pro) pro.hidden = _tour.step !== _tour.steps.length - 1;
            // Place the card beside the spotlight, flipping to whichever side
            // has room so it never covers the thing it is describing.
            var cw = 320, ch = card.offsetHeight || 190, gap = 14;
            var left = hit.r.left - cw - gap;
            if (left < 12) left = hit.r.right + gap;
            if (left + cw > window.innerWidth - 12) left = Math.max(12, window.innerWidth - cw - 12);
            var top = hit.r.top + Math.min(40, hit.r.height / 2);
            if (top + ch > window.innerHeight - 12) top = Math.max(12, window.innerHeight - ch - 12);
            card.style.left = Math.round(left) + 'px';
            card.style.top = Math.round(top) + 'px';
        }
    }
    function startTour() {
        if (!_built) return;
        // Only tour what is actually on screen. MEASURED: in WHOLE CAR before a
        // material is picked the SOURCE card is 0x0 with a null offsetParent, so
        // a fixed four-step list would have skipped a step and still counted to
        // four - telling the buyer they missed something they were never shown.
        _tour.steps = TOUR_STEPS.filter(function (st) { return !!tourTargetRect(st.sel); });
        if (!_tour.steps.length) return;
        _tour.on = true;
        _tour.step = 0;
        drawTour();
    }
    function endTour() {
        _tour.on = false;
        var back = $('spbEasyTourBackdrop');
        if (back) back.hidden = true;
        try { lsSet(LS_TOUR, '1'); } catch (e) {}
    }
    function nextTourStep() {
        if (_tour.step >= _tour.steps.length - 1) { endTour(); return; }
        _tour.step++;
        drawTour();
    }
    function prevTourStep() {
        if (_tour.step <= 0) return;
        _tour.step--;
        drawTour();
    }
    function wireTour() {
        var back = $('spbEasyTourBackdrop');
        if (!back) return;
        back.addEventListener('click', function (e) { if (e.target === back) endTour(); });
        var x = $('spbEasyTourClose'); if (x) x.addEventListener('click', endTour);
        var n = $('spbEasyTourNext'); if (n) n.addEventListener('click', nextTourStep);
        var p2 = $('spbEasyTourPrev'); if (p2) p2.addEventListener('click', prevTourStep);
        var pro = $('spbEasyTourPro');
        if (pro) pro.addEventListener('click', function () {
            endTour();
            exit();
            setTimeout(function () {
                try { if (window.spbGuide && typeof window.spbGuide.on === 'function') window.spbGuide.on(); } catch (e) {}
            }, 150);
        });
        window.addEventListener('resize', function () { if (_tour.on) drawTour(); });
        document.addEventListener('keydown', function (e) {
            if (!_tour.on) return;
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); endTour(); }
            else if (e.key === 'ArrowRight' || e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); nextTourStep(); }
            else if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopPropagation(); prevTourStep(); }
        }, true);
    }

    // [2026-08-08 E37] Easy Mode avoids jargon where it can, but some words are
    // unavoidable because iRacing and the paint world use them: the channel
    // strips under the car say METAL / ROUGH / COAT, the filter chips say
    // CANDY & PEARL, and every finish name assumes you know what satin is.
    // These are the words the app actually puts on screen - nothing else.
    var GLOSSARY = [
        ['SPEC MAP', 'The second file Shokker saves next to your paint. Your paint file says what ' +
                     'COLOR the car is; the spec map says how LIGHT behaves on it - what is shiny, ' +
                     'what is flat, what looks like metal. iRacing needs both.'],
        ['METAL (the red channel)', 'How much a spot behaves like bare metal rather than painted ' +
                     'plastic. Brighter red = more metal. Chrome is all the way up.'],
        ['ROUGH (the green channel)', 'How sharp the reflection is. Dark green = mirror-sharp, ' +
                     'bright green = blurred and soft. Matte is all the way up.'],
        ['COAT (the blue channel)', 'The clear layer over the paint, like lacquer on a show car. ' +
                     'Darker = deeper and glassier.'],
        ['CHROME', 'A mirror. It reflects the world around the car instead of having a color of ' +
                   'its own.'],
        ['CANDY', 'A see-through color sprayed over a metallic base. Light goes through the color, ' +
                  'bounces off the metal underneath and comes back - that is the wet, deep look.'],
        ['PEARL', 'Fine flakes that shift color as the car turns. Subtler than candy.'],
        ['METALLIC / FLAKE', 'Tiny reflective specks in the paint. They sparkle in direct light and ' +
                   'go quiet in shade.'],
        ['MATTE', 'No reflection at all. Flat, stealthy, absorbs light.'],
        ['SATIN', 'Between gloss and matte - a soft sheen with no harsh highlight.'],
        ['CARBON FIBER', 'The woven composite look. Fine dark weave with a sheen that moves across ' +
                   'the weave.'],
        ['PAINT | SHINE', 'The two halves of every card in the picker. PAINT is that finish ' +
                   'shown in its own color, just so you can recognize it. SHINE is how it behaves under light, the part that ' +
                   'actually goes on your car. Your own colors are never replaced by the sample.'],
        ['BASE vs FINISH', 'Shokker uses them interchangeably in Easy Mode: both mean "the material ' +
                   'this part of the car is made of".'],
        ['THE MIX / SHARE', 'When you use more than one material, the share is how much of the car ' +
                   'leans toward that material. Shokker decides WHERE each one lands from your own ' +
                   'paint - press SHOW ME WHERE to see it.']
    ];
    function glossaryHtml() {
        return GLOSSARY.map(function (row) {
            return '<dt>' + esc(row[0]) + '</dt><dd>' + esc(row[1]) + '</dd>';
        }).join('');
    }
    // [GAUNTLET E0 2026-08-20] Easy Mode's own confirm/prompt, in the app's own
    // skin. Returns a Promise: null = cancelled, true = confirmed, or the typed
    // string when `input` is supplied. Falls back to the native dialog only if
    // the markup is missing, so an older shell still gets the action.
    function easyAsk(opts) {
        return new Promise(function (resolve) {
            var back = $('spbEasyAskBackdrop');
            if (!back) {
                if (opts.input != null) return resolve(window.prompt(opts.title, opts.input));
                return resolve(window.confirm(opts.title) ? true : null);
            }
            var title = $('spbEasyAskTitle'), body = $('spbEasyAskBody'), inp = $('spbEasyAskInput');
            var yes = $('spbEasyAskYes'), no = $('spbEasyAskNo');
            title.textContent = opts.title || '';
            body.textContent = opts.body || '';
            body.hidden = !opts.body;
            inp.hidden = (opts.input == null);
            if (opts.input != null) inp.value = String(opts.input);
            yes.textContent = opts.yes || 'OK';
            no.textContent = opts.no || 'CANCEL';
            yes.classList.toggle('danger', !!opts.danger);
            back.hidden = false;

            function done(result) {
                back.hidden = true;
                yes.removeEventListener('click', onYes);
                no.removeEventListener('click', onNo);
                back.removeEventListener('click', onBack);
                document.removeEventListener('keydown', onKey, true);
                resolve(result);
            }
            function onYes() { done(opts.input != null ? String(inp.value || '').trim() : true); }
            function onNo() { done(null); }
            function onBack(e) { if (e.target === back) done(null); }
            function onKey(e) {
                if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(null); }
                else if (e.key === 'Enter' && opts.input != null) { e.preventDefault(); e.stopPropagation(); onYes(); }
            }
            yes.addEventListener('click', onYes);
            no.addEventListener('click', onNo);
            back.addEventListener('click', onBack);
            document.addEventListener('keydown', onKey, true);
            try { (opts.input != null ? inp : yes).focus(); } catch (e) {}
        });
    }

    function openGlossary() {
        var back = $('spbEasyGlossBackdrop');
        if (!back) return;
        var body = $('spbEasyGlossBody');
        if (body && !body.innerHTML) body.innerHTML = glossaryHtml();
        back.hidden = false;
        var cl = $('spbEasyGlossClose');
        if (cl) { try { cl.focus(); } catch (e) {} }
    }
    function closeGlossary() {
        var back = $('spbEasyGlossBackdrop');
        if (back) back.hidden = true;
    }
    function wireGlossary() {
        var back = $('spbEasyGlossBackdrop');
        if (!back) return;
        back.addEventListener('click', function (e) { if (e.target === back) closeGlossary(); });
        var cl = $('spbEasyGlossClose');
        if (cl) cl.addEventListener('click', closeGlossary);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && back && !back.hidden) {
                e.preventDefault(); e.stopPropagation(); closeGlossary();
            }
        }, true);
    }

    function teachMe() {
        startTour();
    }

    // ------------------------------------------------------------------ boot
    // [SPB-EASY-2026-08-19] Owner: "an option when they first install if they'd
    // like to begin in Pro Mode or Easy Mode? I'm afraid if it JUST boots into
    // Easy Mode people are going to also be totally missing out on the GOOD
    // things the app has going for it."
    //
    // So: Pro is still the front door (SPB-FIX-2026-07-23 stands) and is the
    // PRE-HIGHLIGHTED, Enter-default choice here. This card exists only so a buyer
    // LEARNS on day one that Easy Mode exists. Shown exactly once - any explicit
    // answer writes LS_MODE, and boot() only calls this when LS_MODE has never
    // been set. Deliberately NOT a skill-level quiz: both doors reach the same
    // catalog and the same engine, and the card says so, because the measured
    // failure was buyers assuming Easy = a cut-down product.
    function showFirstRunChooser() {
        if ($('spbFirstRun')) return;
        var host = document.createElement('div');
        host.id = 'spbFirstRun';
        host.setAttribute('role', 'dialog');
        host.setAttribute('aria-modal', 'true');
        host.setAttribute('aria-labelledby', 'spbFrTitle');
        var total = nfmt(catalogTotal());
        host.innerHTML = '' +
            '<div class="spb-fr-card">' +
            '  <div class="spb-fr-brand">SHOKKER <b>PAINT BOOTH</b></div>' +
            '  <h2 class="spb-fr-title" id="spbFrTitle">Two ways in. Same paint shop.</h2>' +
            '  <p class="spb-fr-sub">Both doors open the exact same engine and the exact same ' + total +
            ' finishes — nothing is locked away in either one. You can switch any time with the ' +
            '<b>PRO&nbsp;|&nbsp;EASY</b> button up top — each mode keeps its own project safe, so switching never touches the other one.</p>' +
            '  <div class="spb-fr-doors">' +
            '    <button type="button" class="spb-fr-door recommended" id="spbFrPro">' +
            '      <span class="spb-fr-badge">THE FULL SHOP · DEFAULT</span>' +
            '      <h3>PRO MODE</h3>' +
            '      <p>Everything the Paint Booth can do, on one screen.</p>' +
            '      <ul>' +
            '        <li>Every tool — brush, wand, lasso, masks, layers</li>' +
            '        <li>Zones, patterns and per-channel spec control</li>' +
            '        <li>Spec Sculpt, Shokk Drop, PSD import</li>' +
            '      </ul>' +
            '    </button>' +
            '    <button type="button" class="spb-fr-door easy" id="spbFrEasy">' +
            '      <span class="spb-fr-badge">BUILT FOR YOU · SWITCH ANY TIME</span>' +
            '      <h3>✨ EASY MODE</h3>' +
            '      <p>Open your paint and the car is built for you — then tap any part to change it.</p>' +
            '      <ul>' +
            '        <li>Every one of the ' + total + ' finishes, seen in the light on your own car</li>' +
            '        <li>Plain English: blend, size, colour — hover anything for a hint</li>' +
            '        <li>Its own project: nothing here touches your Pro work · saves straight into iRacing</li>' +
            '      </ul>' +
            '    </button>' +
            '  </div>' +
            '  <div class="spb-fr-foot">New to painting cars? Start in <b>EASY</b> — it is the fastest way to a ' +
            'finished car, and every finish you find there is waiting for you in Pro. Already know your way ' +
            'around a paint editor? <b>PRO</b> is your room.</div>' +
            '</div>';
        document.body.appendChild(host);
        // [SPB-EASY-2026-08-19, screenshot pass] Caught only by looking at it: the
        // Training Wheels quest panel (11 items, top-right, its own z-index) sits
        // ABOVE the first-run backdrop, so a brand-new buyer met a modal AND an
        // 11-item checklist in the same first second. Suppress it while the card
        // is up; it comes straight back afterwards.
        document.body.classList.add('spb-firstrun-open');

        function choose(mode) {
            lsSet(LS_MODE, mode);
            document.body.classList.remove('spb-firstrun-open');
            try { host.parentNode.removeChild(host); } catch (e) { host.hidden = true; }
            document.removeEventListener('keydown', onKey, true);
            if (mode === 'easy') enter();
            else syncModePill();
        }
        function onKey(ev) {
            // Enter and Escape both land on Pro - the pre-highlighted, owner-chosen
            // default. Never leave LS_MODE unset here, or the card returns on every
            // boot and becomes the nag it was meant to replace.
            if (ev.key === 'Enter' || ev.key === 'Escape') {
                ev.preventDefault(); ev.stopPropagation(); choose('pro');
            }
        }
        $('spbFrPro').addEventListener('click', function () { choose('pro'); });
        $('spbFrEasy').addEventListener('click', function () { choose('easy'); });
        document.addEventListener('keydown', onKey, true);
        try { $('spbFrPro').focus({ preventScroll: true }); } catch (e) {}
    }


    // ============================================ PLAIN-LANGUAGE TOASTS (2026-08-20)
    // A toast census on a real first boot (_easy_gauntlet/shots/toast) caught TEN
    // toasts in the first ~20 seconds, six of them written for a Pro user:
    // "Loading PSD...", "Rasterizing layers", "(2048x2048, TGA decoded)",
    // "PSD ready: 11/11 layers loaded. Toggle eyes to show/hide." - there are no
    // eyes in Easy Mode - and "Press ? or F1 for keyboard shortcuts".
    //
    // Rather than chase every showToast() call site across three Pro modules, Easy
    // Mode wraps showToast once and rewrites the messages it recognises. Rules:
    //   * only while Easy Mode is the active view,
    //   * an explicit table - anything unrecognised passes through untouched,
    //   * NOTHING is silently swallowed. A toast the buyer cannot act on still
    //     gets shown, just in words that mean something to them.
    // [SPB-OVERNIGHT 2026-08-22, R16] filenames leaked Pro jargon straight
    // through this table ("Starting you off with an example paint: SPB Chevy
    // Truck Starting Example PSD.psd") \u2014 buyers get a clean paint NAME, never
    // a file string with format words in it.
    function plainPaintName(f) {
        var n = String(f || '').replace(/\\/g, '/').split('/').pop();
        n = n.replace(/\.(psd|tga|ora|xcf|png|jpe?g)$/i, '');
        n = n.replace(/\b(psd|tga|ora|xcf)\b/ig, ' ').replace(/\s{2,}/g, ' ').trim();
        return n || 'your paint';
    }
    var TOAST_PLAIN = [
        { re: /^Loading PSD\.\.\.$/i, to: 'Opening your paint\u2026' },
        { re: /^First launch\s*[-\u2014]\s*loading default:\s*(.+)$/i,
          to: function (m) { return 'Starting you off with an example paint: ' + plainPaintName(m[1]); } },
        { re: /^Loaded\s+(.+?)\s*\([^)]*\)$/i,
          to: function (m) { return 'Opened ' + plainPaintName(m[1]); } },
        { re: /^Rasterizing layers[^$]*$/i, to: 'Getting your paint ready \u2014 about 10 seconds\u2026' },
        { re: /^(.+?)\s+ready:\s*\d+\/\d+\s+layers\s+loaded\..*$/i, to: 'Your paint is open and ready.' },
        { re: /^(.+?)\s+ready:\s*\d+\/\d+\s+layers\s+decoded;.*$/i, to: 'Your paint is open and ready.' },
        { re: /^(.+?)\s+opened safely from its source composite;.*$/i,
          to: function (m) { return 'Opened ' + plainPaintName(m[1]) + ' \u2014 a few layers could not be separated, so your paint is used exactly as it came.'; } },
        { re: /^Detected your iRacing ID\s+(\d+)\s+from.*$/i,
          to: function (m) { return 'Found your iRacing number: ' + m[1] + ' \u2014 your paint saves under that number.'; } },
        { re: /^Welcome to Shokker Paint Booth!.*shortcuts.*$/i,
          to: 'Welcome \u2014 tell Shokker what you want in the bar above the car, or tap any part.' },
    ];

    /** Easy Mode language applies once Easy is on, or while it is about to open. */
    function easyLanguageActive() {
        try {
            if (document.body && document.body.classList.contains('spb-easy-on')) return true;
            if (lsGet(LS_MODE) === 'easy') return true;
            return new URLSearchParams(window.location.search).get('easy') === 'spec-sculpt';
        } catch (e) { return false; }
    }

    function plainToast(msg) {
        for (var i = 0; i < TOAST_PLAIN.length; i++) {
            var m = TOAST_PLAIN[i].re.exec(msg);
            if (!m) continue;
            var to = TOAST_PLAIN[i].to;
            return (typeof to === 'function') ? to(m) : to;
        }
        return null;
    }

    var _toastWrapped = false;
    function installPlainToasts() {
        if (_toastWrapped || typeof window.showToast !== 'function') return;
        _toastWrapped = true;
        var orig = window.showToast;
        window.showToast = function (msg, kind, details) {
            try {
                if (easyLanguageActive()) {
                    var plain = plainToast(String(msg));
                    if (plain) {
                        return orig.call(this, plain, kind, details);
                    }
                }
            } catch (e) {}
            return orig.apply(this, arguments);
        };
        try { window.spbEasyPlainToast = plainToast; } catch (e) {}
    }


    // [SPB-LAYER-GAUNTLET C6 2026-08-21] CAR PARTS drawer - Easy Mode's window
    // onto a layered paint. Groups by the PSD's own folder names; each row is
    // just a name + show/hide. Uses Pro's toggleLayerVisible so the preview and
    // the real render stay truthful.
    function carPartsDrawerHtml() {
        try {
            if (typeof _psdLayers === 'undefined' || !window._psdLayersLoaded || !_psdLayers.length) return '';
            var groups = {};
            var order = [];
            _psdLayers.forEach(function (l) {
                if (!l || !l.img) return;
                var g = l.groupName || l.name || 'Part';
                if (!groups[g]) { groups[g] = []; order.push(g); }
                groups[g].push(l);
            });
            if (!order.length) return '';
            var rows = order.map(function (g) {
                var members = groups[g];
                var shown = members.filter(function (l) { return l.visible !== false; }).length;
                var allOn = shown === members.length;
                var label = (members.length === 1 && !members[0].groupName) ? members[0].name : g;
                return '<button type="button" class="spb-easy-carpart' + (allOn ? ' on' : (shown ? ' part' : '')) + '"' +
                    ' data-carpart="' + esc(g) + '"' +
                    ' title="' + (allOn ? 'Hide' : 'Show') + ' this part of the paint (' + members.length + ' layer' + (members.length > 1 ? 's' : '') + ')">' +
                    '<span class="spb-easy-carpart-eye">' + (shown ? '\u{1F441}' : '\u2013') + '</span>' +
                    '<span class="spb-easy-carpart-name">' + esc(label) + '</span>' +
                    (members.length > 1 ? '<span class="spb-easy-carpart-count">' + shown + '/' + members.length + '</span>' : '') +
                    '</button>';
            }).join('');
            return '<details class="spb-easy-drawer spb-easy-carparts" id="spbEasyCarParts">' +
                '  <summary><span class="spb-easy-drawer-title">CAR PARTS</span>' +
                '    <span class="spb-easy-drawer-value">show or hide pieces of your paint</span>' +
                '    <span class="spb-easy-drawer-caret" aria-hidden="true">\u25be</span></summary>' +
                '  <div class="spb-easy-carpart-rows" id="spbEasyCarPartRows">' + rows + '</div>' +
                '  <small class="spb-easy-carpart-hint">Hiding a part only hides it \u2014 nothing is deleted. Tap again to bring it back.</small>' +
                '</details>';
        } catch (e) { return ''; }
    }

    function toggleCarPart(groupName) {
        try {
            if (typeof _psdLayers === 'undefined') return;
            var members = _psdLayers.filter(function (l) {
                return l && l.img && ((l.groupName || l.name || 'Part') === groupName);
            });
            if (!members.length) return;
            var anyOn = members.some(function (l) { return l.visible !== false; });
            members.forEach(function (l) {
                if ((l.visible !== false) === anyOn) {
                    if (typeof window.toggleLayerVisible === 'function') window.toggleLayerVisible(l.id);
                    else l.visible = !anyOn;
                }
            });
            var host = $('spbEasyCarParts');
            if (host) {
                var fresh = carPartsDrawerHtml();
                if (fresh) {
                    var tmp = document.createElement('div');
                    tmp.innerHTML = fresh;
                    var next = tmp.firstElementChild;
                    next.open = host.open;
                    host.replaceWith(next);
                    wireCarParts();
                }
            }
        } catch (e) {}
    }

    function wireCarParts() {
        var rows = $('spbEasyCarPartRows');
        if (!rows) return;
        rows.querySelectorAll('[data-carpart]').forEach(function (btn) {
            btn.addEventListener('click', function () { toggleCarPart(btn.getAttribute('data-carpart')); });
        });
    }

    function boot() {
        try {
            restoreState();
            var openGuidedSculpt = false;
            try { openGuidedSculpt = new URLSearchParams(window.location.search).get('easy') === 'spec-sculpt'; } catch (e) {}
            // SPB-FIX-2026-07-23 (owner): boot into PRO by default; Easy Mode is opt-IN via the
            // header "EASY MODE" button. Was `!== 'pro'` which sent EVERY fresh install (unset key)
            // into Easy — the owner wants Pro as the front door with Easy one click away. Now only an
            // explicit saved 'easy' (or the ?easy=spec-sculpt deep link) auto-enters Easy Mode.
            var savedMode = lsGet(LS_MODE);
            // SPB-CHAT-2026-10-01 (owner): "dump the existing EASY MODE for now and hide it" - the chat studio (js/spb-chat-studio.js) replaces it as the easy way in. Easy stays in the code (Spec Sculpt still opens through it);
            // a saved 'easy' heals to 'pro' and nothing auto-enters it any more.
            if (savedMode === 'easy') { try { lsSet(LS_MODE, 'pro'); } catch (e0) {} savedMode = 'pro'; }
            if (openGuidedSculpt) enter();
            if (openGuidedSculpt) {
                state.view = 'sculpt';
                renderRail();
            }
            // [SPB-EASY-2026-08-19] First install (LS_MODE never written) gets the
            // one-time PRO/EASY card. Deep links skip it - someone arriving at
            // ?easy=spec-sculpt has already chosen. Dismissing still lands in Pro,
            // so this cannot regress the owner's Pro-first rule.
            if (!savedMode && !openGuidedSculpt) { try { lsSet(LS_MODE, 'pro'); window.__spbFirstRun = true; window.dispatchEvent(new CustomEvent('spb:first-run')); } catch (e1) {} }
            syncModePill();
        } catch (e) {
            try { console.error('[spbEasy] boot failed:', e); } catch (e2) {}
        }
    }
    window.spbEasy = {
        // [SPB-EASY-AUTO 2026-09-19] live handles for js/spb-easy-auto.js (same project, same picker, same render)
        _internals: function () {
            return {
                state: state, bc: bc, bcRef: function () { return bc; }, els: els,
                zones: function () { return zones; },
                isActive: function () { return _active; },
                finishInfo: finishInfo, finishKey: finishKey, buildTopShelf: buildTopShelf, buildCatalogSections: buildCatalogSections,
                splitThumbHtml: splitThumbHtml, thumbUrl: thumbUrl, armLazyThumbs: armLazyThumbs, lazyThumbPassSoon: lazyThumbPassSoon,
                kickPreview: kickPreview, kickPreviewDebounced: kickPreviewDebounced, undoPush: undoPush, refreshZonesUI: refreshZonesUI,
                renderRail: renderRail, railHeader: railHeader, saveBlockHtml: saveBlockHtml, wireSaveBlock: wireSaveBlock,
                paintLoaded: paintLoaded, detectWholeApplied: detectWholeApplied, isEasyColorZone: isEasyColorZone, easyColorZones: easyColorZones,
                easyUndo: easyUndo, easyRedo: easyRedo, historyTop: function () { try { var st = zoneUndoStack; return (st && st.length) ? st[st.length - 1] : null; } catch (e) { return null; } },   // [SPB-EASY-TELL2] receipts undo only their own step
                syncStage: syncStage, persistState: persistState, esc: esc, TOL_DEFAULT: TOL_DEFAULT, LIGHT_MODES: (typeof LIGHT_MODES !== 'undefined' ? LIGHT_MODES : null), syncPreviewNow: syncPreviewNow
            };
        },
        enter: enter,
        exit: exit,
        toggle: toggle,
        openSculpt: function () { enter(); state.view = 'sculpt'; renderRail(); },
        openWhole: function () { enter(); state.view = 'whole'; renderRail(); }
    };
    // Wrap showToast NOW, not at boot(): the welcome / PSD-load toasts all fire
    // inside the first second, well before BOOT_DELAY_MS elapses.
    installPlainToasts();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, BOOT_DELAY_MS); });
    } else {
        setTimeout(boot, BOOT_DELAY_MS);
    }
})();
