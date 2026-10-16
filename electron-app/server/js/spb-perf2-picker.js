/* [SPB-PERF2 2026-10-10 PERF-2 lane, target 2] FINISH PICKER: keep the built category wall between opens.
 *
 * The owner's complaint: the Base / Pattern finish picker took 3.5-5 s on EVERY open. Measured (CPU profiler, fresh page): ~2.2 s of synchronous JS per open -
 * ~0.35 s building + parsing a 7.7 MB html string for ~2,800 cards, ~0.65 s decorating every card (_enhanceSwatchPopupCards), ~0.55 s re-organising the wall into
 * Atlas sections (A.organize), ~0.25 s for a hidden "review queue" panel nobody sees, ~0.2 s counting hashtags, ~0.2 s in filterSwatchPopup('') ... and
 * closeSwatchPicker() threw the whole wall away (grid.innerHTML = '', SPEED-TUNEUP 2026-08-31) so the next open paid all of it again.
 *
 * What this file does (every part is behind window.SPB_PERF2_OFF === true, or window.SPB_PERF2_PICKER_OFF === true):
 *   1. P.restore()/P.park()  - on close the finished wall (cards, Atlas sections, decorations, already-loaded thumbnails) is PARKED in a detached DocumentFragment
 *                              (detached nodes cost no style recalc / document query time, which is what SPEED-TUNEUP was after). On the next open of the same picker
 *                              type the wall goes straight back in, IF a signature of everything the build reads still matches: the catalog contents (ids, names,
 *                              descs, swatches, groups), the user's ratings, favourites, the day (Atlas "today's 5"), the data tables the card decorator reads and the
 *                              swatch URL base. Anything else -> the normal full build, exactly as before. The selected-card marking (the only per-open input of the html)
 *                              is re-applied with the same rules the html builder uses. The Atlas organise step is replaced by its idempotent tail (A.organize(cache)).
 *   2. P.itemById()          - O(1) lookup behind _getSwatchItemById (was a linear .find over three ~1000-item arrays, once per card per build), guarded by
 *                              array identity / length / first / last and verified on every hit; any doubt falls back to the original linear code.
 * Equivalence is proven by a harness that builds the wall fresh and by restoring it, over many flows, and diffs the popup DOM (_easy_claude_work/perf2/picker_equiv.py).
 */
(function () {
    'use strict';
    var W = window, D = document;
    function off() { return W.SPB_PERF2_OFF === true || W.SPB_PERF2_PICKER_OFF === true; }
    try { if (W.localStorage && W.localStorage.getItem('SPB_PERF2_OFF') === '1') W.SPB_PERF2_OFF = true; } catch (e0) { /* storage blocked */ }

    var P = W.__spbPerf2Picker = { v: '2026-10-10-p2pk2', stats: { hits: 0, misses: 0, parks: 0, parkRefused: 0, restoreMs: 0, parkMs: 0, sigMs: 0, lastMiss: '' } };
    // Picker types whose wall is verified restorable (the html builder's branches for these are covered by the equivalence harness).
    // [SPECIAL-ALL 2026-10-12] layerSpecialPaint (the layer-brush "Choose Special" picker) now builds the SAME wall as the zone Base picker (all BASE groups + all Specials, no "(not set)" card),
    // so it is parked/restored per type too; its signature is keyed by type + the catalog, so a wall built before this change can never be restored (the cache is per page-load anyway).
    var CACHEABLE = { base: 1, pattern: 1, secondBase: 1, thirdBase: 1, fourthBase: 1, fifthBase: 1, stackPattern: 1, layerSpecialPaint: 1 };
    var PATTERNISH = { pattern: 1, stackPattern: 1, secondBasePattern: 1, thirdBasePattern: 1 };
    var MAX_ENTRIES = 3;
    var cache = {};          // type -> { sig, frag, counts, t }
    var pending = null;      // { type, sig } for the open in progress (set by restore(), consumed by built())
    var restored = null;     // { counts, order } when the open in progress re-used a parked wall
    var live = null;         // { type, sig, n, counts, order } describes the wall currently in the grid when it is parkable
    var preOrder = null;     // the grid's top-level children (the "(not set)" card, the groups) in document order BEFORE the Atlas reshuffle - see firstSelected()

    /* ---------- signature ---------- */
    function Hasher() {
        var h = 2166136261 >>> 0;
        return {
            s: function (v) {
                v = (v == null) ? '' : String(v);
                for (var i = 0, n = v.length; i < n; i++) h = Math.imul(h ^ v.charCodeAt(i), 16777619);
                h = Math.imul(h ^ 31, 16777619);
            },
            out: function () { return (h >>> 0).toString(36); }
        };
    }
    function keyCount(o) { try { return o ? Object.keys(o).length : -1; } catch (e) { return -2; } }
    function catalogHash() {
        var H = Hasher(), i, n, a, it, k, ids, g;
        var lists = [typeof BASES !== 'undefined' ? BASES : null, typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : null, typeof PATTERNS !== 'undefined' ? PATTERNS : null];
        for (k = 0; k < lists.length; k++) {
            a = lists[k]; if (!a) { H.s('~'); continue; }
            H.s(a.length);
            for (i = 0, n = a.length; i < n; i++) {
                it = a[i]; if (!it) { H.s('-'); continue; }
                H.s(it.id); H.s(it.name); H.s(it.desc); H.s(it.swatch); H.s(it.swatch2); H.s(it.swatch3); H.s(it.category); H.s(it.colorSafe ? 1 : 0); H.s(it.ghostPattern);
                if (it.tags && it.tags.join) H.s(it.tags.join(','));
            }
        }
        var gs = [typeof BASE_GROUPS !== 'undefined' ? BASE_GROUPS : null, typeof SPECIAL_GROUPS !== 'undefined' ? SPECIAL_GROUPS : null, typeof PATTERN_GROUPS !== 'undefined' ? PATTERN_GROUPS : null];
        for (k = 0; k < gs.length; k++) {
            g = gs[k]; if (!g) { H.s('~'); continue; }
            var names = Object.keys(g);
            H.s(names.length);
            for (i = 0; i < names.length; i++) { H.s(names[i]); ids = g[names[i]]; if (ids && ids.length != null) { H.s(ids.length); for (var j = 0; j < ids.length; j++) H.s(ids[j]); } }
        }
        return H.out();
    }
    function ratingsSig() {
        try {
            var m = (typeof _spbLoadFinishRatings === 'function') ? _spbLoadFinishRatings() : null;
            return m ? JSON.stringify(m) : '';
        } catch (e) { return '!'; }
    }
    function favSig() {
        try { return (typeof _favoriteFinishes !== 'undefined' && _favoriteFinishes) ? Array.from(_favoriteFinishes).join(',') : ''; } catch (e) { return '!'; }
    }
    function tablesSig() {
        var s = [];
        try {
            s.push(keyCount(typeof FINISH_METADATA !== 'undefined' ? FINISH_METADATA : null));
            s.push(keyCount(typeof FINISH_TAGS !== 'undefined' ? FINISH_TAGS : null));
            s.push(keyCount(typeof FINISH_BROWSER_QUALITY_FLAGS !== 'undefined' ? FINISH_BROWSER_QUALITY_FLAGS : null));
            s.push(keyCount(typeof CATALOG_SCORECARD_METRICS !== 'undefined' ? CATALOG_SCORECARD_METRICS : (W.CATALOG_SCORECARD_METRICS || null)));
            s.push(keyCount(typeof PICKER_OWNER_RATINGS !== 'undefined' ? PICKER_OWNER_RATINGS : (W.PICKER_OWNER_RATINGS || null)));
            s.push(keyCount(typeof FINISH_LIBRARY_SEARCH_ALIASES !== 'undefined' ? FINISH_LIBRARY_SEARCH_ALIASES : null));
            s.push(keyCount(typeof FINISH_TYPE_BY_ID !== 'undefined' ? FINISH_TYPE_BY_ID : null));
            s.push(keyCount(W._SHOKKER_SWATCH_FP));
            s.push(W._SHOKKER_SWATCH_V || '');
            s.push((typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : ('p' + (W.spbServerPort ? W.spbServerPort() : W._SHOKKER_PORT)));
            s.push(keyCount(W.BASE_GROUP_SUBSECTIONS));
        } catch (e) { s.push('!'); }
        return s.join('/');
    }
    function sigOf(type) {
        var t0 = performance.now();
        var d = new Date();
        var s = type + '\u0001' + catalogHash() + '\u0001' + ratingsSig() + '\u0001' + favSig() + '\u0001' + tablesSig() + '\u0001' + d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate();
        P.stats.sigMs = performance.now() - t0;
        return s;
    }
    P.sig = sigOf;

    /* ---------- selected-card marking: the same rules openSwatchPicker's html builder (and _renderSwatchPickerCard) apply ---------- */
    var ONCLICK = /^selectSwatchItem\('((?:[^'\\]|\\.)*)'\)$/;
    function unesc(s) { return s.indexOf('\\') < 0 ? s : s.replace(/\\(.)/g, '$1'); }
    function patchSelected(grid, type, cur) {
        var patternish = PATTERNISH[type] === 1, cards = grid.querySelectorAll('.swatch-item'), i, c, fid, m, val, want;
        for (i = 0; i < cards.length; i++) {
            c = cards[i];
            fid = c.getAttribute('data-finish-id');
            m = ONCLICK.exec(c.getAttribute('onclick') || '');
            val = m ? unesc(m[1]) : null;
            if (!fid) {                                   // the "(not set)" / "none" card
                want = patternish ? (cur === 'none' || cur === '') : (cur === '');
            } else if (val === null) {
                want = c.classList.contains('selected');  // unknown card shape: leave it as it was built
            } else if (c.parentNode && c.closest && c.closest('.swatch-favorites-group')) {
                want = (cur === val || cur === fid || cur === ('mono:' + fid));
            } else {
                want = (cur === val);
            }
            if (want !== c.classList.contains('selected')) c.classList.toggle('selected', want);
        }
    }

    /* ---------- restore / built / park ---------- */
    P.restore = function (grid, type, currentId) {
        pending = null; restored = null;
        if (off()) { if (Object.keys(cache).length) cache = {}; live = null; return false; }
        if (!CACHEABLE[type] || !grid) return false;
        var sg;
        try { sg = sigOf(type); } catch (e) { return false; }
        pending = { type: type, sig: sg };
        var ent = cache[type];
        if (!ent) { P.stats.misses++; P.stats.lastMiss = 'none'; return false; }
        if (ent.sig !== sg) { P.stats.misses++; P.stats.lastMiss = 'sig'; delete cache[type]; return false; }
        if (grid.firstChild) { P.stats.misses++; P.stats.lastMiss = 'busy'; return false; }
        var t0 = performance.now();
        try {
            grid.appendChild(ent.frag);
            patchSelected(grid, type, currentId);
        } catch (e) {
            try { grid.innerHTML = ''; } catch (e2) { /* ignore */ }
            delete cache[type]; P.stats.misses++; P.stats.lastMiss = 'throw'; return false;
        }
        delete cache[type];
        restored = { counts: ent.counts, order: ent.order };
        P.stats.hits++; P.stats.restoreMs = performance.now() - t0;
        return true;
    };
    /* called by the Atlas wrapper right after organize()/openCurrentCategory(): the wall in the grid is now final and parkable */
    P.built = function (type) {
        var pnd = pending, rs = restored, po = preOrder; pending = null; restored = null; preOrder = null; live = null;
        if (off() || !pnd || pnd.type !== type) return;
        var grid = D.getElementById('swatchPopupGrid'); if (!grid || !grid.firstChild) return;
        var A = W.SPB_ATLAS, counts = rs ? rs.counts : (A && A._lastCounts ? A._lastCounts : null);
        live = { type: type, sig: pnd.sig, n: grid.querySelectorAll('.swatch-item').length, counts: counts, order: rs ? rs.order : po };
    };
    /* the Atlas wrapper calls this on a FRESH build, right before A.organize() reshuffles the groups */
    P.preOrganize = function () {
        preOrder = null;
        if (off()) return;
        var grid = D.getElementById('swatchPopupGrid'); if (!grid) return;
        preOrder = Array.prototype.slice.call(grid.children);
    };
    /* _spbAutoOpenPickerCategory picks the group of the FIRST selected card in document order. A fresh build asks that BEFORE the Atlas reshuffle (the favourites group, then the
     * catalog groups in build order); a re-used wall is already reshuffled, so ask in the recorded pre-reshuffle order instead -> the same group, the same scroll landing.
     * undefined = "no opinion, use the plain document order" (not a re-used wall, no record, or the record cannot find the card). */
    P.firstSelected = function (grid) {
        var rs = restored; if (!rs || !rs.order || off()) return undefined;
        var o = rs.order, i, u, s;
        for (i = 0; i < o.length; i++) {
            u = o[i]; if (!u || u.nodeType !== 1) continue;
            if (u.classList.contains('swatch-item')) { if (u.classList.contains('selected')) return grid.contains(u) ? u : undefined; continue; }
            s = u.querySelector('.swatch-item.selected');
            if (s) return grid.contains(s) ? s : undefined;
        }
        return grid.querySelector('.swatch-item.selected') ? undefined : null;
    };
    /* the Atlas wrapper asks whether this open re-used a parked wall (-> run only the idempotent tail of organize) */
    P.takeRestored = function () { return restored; };
    P.park = function (grid) {
        var lv = live; live = null;
        if (off() || !lv || !grid || !grid.firstChild) { if (off()) cache = {}; return false; }
        var st = (typeof swatchPopupState !== 'undefined') ? swatchPopupState : null;
        if (!st || st.type !== lv.type) { P.stats.parkRefused++; return false; }
        var t0 = performance.now();
        try {
            if (grid.querySelectorAll('.swatch-item').length !== lv.n) { P.stats.parkRefused++; return false; }   // somebody changed the wall: rebuild next time
            // A thumbnail that failed to load is replaced by a fallback colour for good (its <img> is removed by its own onerror). A fresh open retries every thumbnail, so a wall that
            // holds failures must not be re-used - the next open rebuilds (and retries) exactly as before.
            if (grid.querySelector('.swatch-spec-unavailable')) { P.stats.parkRefused++; P.stats.lastRefuse = 'thumb-failed'; return false; }
            var A = W.SPB_ATLAS; if (A && A.p2Normalize) A.p2Normalize(grid);
            var frag = D.createDocumentFragment();
            while (grid.firstChild) frag.appendChild(grid.firstChild);
            cache[lv.type] = { sig: lv.sig, frag: frag, counts: lv.counts, order: lv.order, t: Date.now() };
            var keys = Object.keys(cache);
            if (keys.length > MAX_ENTRIES) {
                keys.sort(function (a, b) { return cache[a].t - cache[b].t; });
                while (keys.length > MAX_ENTRIES) delete cache[keys.shift()];
            }
            P.stats.parks++; P.stats.parkMs = performance.now() - t0;
            return true;
        } catch (e) { P.stats.parkRefused++; return false; }
    };
    /* filterSwatchPopup('') ends openSwatchPicker and re-sorts every row by rating. On a FRESH build that sort runs before the Atlas reshuffle, which then re-sorts every row A-Z
     * (and renumbers data-original-index), so the final order ignores ratings. A re-used wall is already in that final order (A.p2Normalize restores it on park) - re-sorting it
     * by rating now would change it. Only the sort inside the open of a re-used wall is skipped. */
    P.skipSort = function () {
        if (!restored || off()) return false;
        try { return !((typeof swatchPopupState !== 'undefined' && swatchPopupState && swatchPopupState.sort) && swatchPopupState.sort !== 'default'); } catch (e) { return false; }
    };
    P.drop = function () { cache = {}; live = null; pending = null; restored = null; preOrder = null; };
    P.info = function () { return { entries: Object.keys(cache), hasLive: !!live, stats: P.stats }; };

    /* ---------- O(1) catalog lookup for _getSwatchItemById ---------- */
    var idx = {};
    function indexOf(name, arr) {
        var st = idx[name], n = arr.length;
        if (st && st.arr === arr && st.len === n && st.first === arr[0] && st.last === arr[n - 1]) return st.map;
        var map = new Map(), i, it;
        for (i = 0; i < n; i++) { it = arr[i]; if (it && it.id != null && !map.has(it.id)) map.set(it.id, i); }
        idx[name] = { arr: arr, len: n, first: arr[0], last: arr[n - 1], map: map };
        return map;
    }
    function find(name, arr, id) {
        if (!arr) return null;
        var i = indexOf(name, arr).get(id);
        if (i === undefined) return undefined;                          // not in the index: caller decides (we never trust a miss)
        var it = arr[i];
        return (it && it.id === id) ? it : undefined;
    }
    /* returns the same { item, type, selectValue } _getSwatchItemById would, or undefined = "ask the original code" */
    P.itemById = function (cleanId, typeHint) {
        if (off()) return undefined;
        var bases = typeof BASES !== 'undefined' ? BASES : null, monos = typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : null, pats = typeof PATTERNS !== 'undefined' ? PATTERNS : null;
        var it;
        if (typeHint === 'pattern' && pats) {
            it = find('p', pats, cleanId);
            if (it) return { item: it, type: 'pattern', selectValue: it.id };
        }
        if (bases) { it = find('b', bases, cleanId); if (it) return { item: it, type: 'base', selectValue: it.id }; }
        if (monos) { it = find('m', monos, cleanId); if (it) return { item: it, type: 'monolithic', selectValue: 'mono:' + it.id }; }
        if (pats) { it = find('p', pats, cleanId); if (it) return { item: it, type: 'pattern', selectValue: it.id }; }
        return undefined;                                               // no hit anywhere: let the original linear code give the (null) answer
    };
})();
