// ============================================================================
// SPB TRAINING WHEELS — QUEST ENGINE (2026-07-18, phase 2)
// Design doc: docs/SPB_TRAINING_WHEELS_QUEST_ENGINE.md
//
// "Training wheels on a bike": same bike (the real app), with support (the
// next-move chip + quest checklist), that comes off gradually (per-skill
// retirement, Core Loop graduation, level-based disclosure). The user learns
// by doing the real UI — the engine never clicks anything for them.
//
// Phase 2 additions:
//   - Event hooks (renderZones / renderZoneDetail / pushUndo / _pushLayerUndo /
//     confirmSaveShokk are wrapped, defensively) — quest sync is instant, and
//     q-touchup / q-recipe auto-complete from real user actions.
//   - Level disclosure: while wheels are ON and level < 2, the zone popout's
//     advanced sections (PATTERN / OVERLAYS / SPEC PATTERNS / SPEC PREVIEW /
//     SPEC SOURCE) start collapsed, with a dismissible 🎓 note. Clicking a
//     section header = peeking; the engine remembers and never re-collapses
//     it. Everything opens for good at level 2 (first render done).
//   - First run: the checklist opens once on a truly fresh profile.
//   - body[data-spb-wheels-level="1|2|3"] is maintained for future CSS.
//   All hooks leave app behavior untouched and are zero-cost when wheels off.
//
// Absorbs js/spb-guided-mode.js (the 2026-07-04 coach): that file is now a
// thin shim keeping window.spbGuide + the 🎓 toolbar button alive.
// Zero changes to paint-booth-*.js app logic — probes read existing globals
// (zones, selectedZoneIndex, _psdLayers, renderHistory, canvasMode) defensively.
// Rollback: remove the script tag + Settings row + css link. Nothing else
// references this file except the spbGuide shim and one Easy Mode hook.
// ============================================================================
(function () {
    'use strict';

    // Double-load guard: a duplicate script tag must not boot twice (panels,
    // hooks, poll interval would all duplicate).
    if (window.spbQuests) return;

    var LS_KEY = 'spb_training_wheels';
    var POLL_MS = 800;
    var SKILL_RETIRE = 3;   // hints for a skill retire after N demonstrated completions

    // ---- state ---------------------------------------------------------------
    var state = {
        wheelsOn: false,         // owner09-08: help starts only after an explicit choice
        choiceMade: false,
        questsDone: {},          // qid -> true
        skillCount: {},          // skill -> demonstrated completions
        activeQuest: null,       // qid shown in the panel detail view
        chipDismissed: false,
        graduated: false,        // user accepted wheels-off after the Core Loop
        gradOfferDismissed: false, // user said "Keep them on" — stop offering, keep questing
        firstWinDone: false,     // Easy Mode → Pro handoff bridge fired
        panelOpen: false,
        panelExpanded: false,   // compact next step by default; full checklist stays available
        specTouched: false,      // user opened the Spec Channels dock/inspector
        userToggledSections: {}, // level-2 popout sections the user peeked into (prefix -> true)
        levelNoteDismissed: false,
        lastProgressAt: 0,       // last quest completion (ms epoch) — for the stuck nudge
        lastNudgeAt: 0,          // last time the chip re-surfaced itself (rate-limited)
        allDoneCelebrated: false // fired the 🏆 all-quests-complete toast
    };
    var _baselineDone = false;   // silent initial sync happened (no toast spam on boot)
    var _bootAt = 0;             // engine init time — nudge fallback for brand-new users
    var _ring = null, _ringTimer = null, _ringCleanup = null;
    var _lastSig = '';

    function lsLoad() {
        try {
            var raw = localStorage.getItem(LS_KEY);
            if (!raw) return;
            var saved = JSON.parse(raw);
            for (var k in state) { if (saved && typeof saved[k] !== 'undefined') state[k] = saved[k]; }
            // Preserve an existing opt-out; ask formerly auto-enabled users once.
            if (!state.choiceMade) {
                state.choiceMade = !!saved && saved.wheelsOn === false;
                state.wheelsOn = false;
                state.panelOpen = false;
            }
            state.panelExpanded = false;
        } catch (e) {}
    }
    function lsSave() {
        try { localStorage.setItem(LS_KEY, JSON.stringify(state)); } catch (e) {}
    }
    function toast(msg, isError) {
        try { if (typeof showToast === 'function') showToast(msg, !!isError); } catch (e) {}
    }

    // ==========================================================================
    // PROBES — the engine's only window into app state. Pure, defensive, return
    // false on any doubt. Field refs verified 2026-07-18 (see design doc §3).
    // ==========================================================================
    function $(id) { return document.getElementById(id); }
    function findByText(selector, text) {
        var els = document.querySelectorAll(selector);
        for (var k = 0; k < els.length; k++) {
            if ((els[k].textContent || '').trim().toLowerCase().indexOf(text.toLowerCase()) !== -1) return els[k];
        }
        return null;
    }
    var probes = {
        paintLoaded: function () {
            // SPB-93 2026-09-07: a restored/typed path is not loaded artwork.
            // This also recognizes a deliberately created blank canvas.
            try {
                var pixels = typeof paintImageData !== 'undefined' ? paintImageData : window.paintImageData;
                return !!(pixels && pixels.width > 0 && pixels.height > 0 && pixels.data &&
                    pixels.data.length >= pixels.width * pixels.height * 4);
            } catch (e) { return false; }
        },
        psdLayerCount: function () {
            try { return (typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded && typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers.filter(function (l) { return l && l.img; }).length : 0; }
            catch (e) { return 0; }
        },
        zone: function () {
            try { return (typeof zones !== 'undefined' && typeof selectedZoneIndex !== 'undefined') ? zones[selectedZoneIndex] : null; }
            catch (e) { return null; }
        },
        anyZone: function () {
            try { return (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : []; }
            catch (e) { return []; }
        },
        regionHasPixels: function (zone) {
            if (!zone || zone.useRegion === false || !zone.regionMask) return false;
            var mask = zone.regionMask;
            if (window.SPBMaskStats && typeof window.SPBMaskStats.any === 'function') return window.SPBMaskStats.any(mask);
            for (var i = 0; i < mask.length; i++) { if (mask[i] > 0) return true; }
            return false;
        },
        zoneClaimed: function (zone) {
            if (!zone) return false;
            // SPB-93 2026-09-07: the live guide stayed on Claim your pixels
            // after a real208,080px selection and finish. Drawing is a valid
            // claim too; a default Everything Else zone or empty mask is not.
            return zone.colorMode === 'picker' || zone.colorMode === 'multi' ||
                (Array.isArray(zone.colors) && zone.colors.length > 0) || probes.regionHasPixels(zone);
        },
        zoneHasColor: function () {
            return probes.anyZone().some(function (zone) { return probes.zoneClaimed(zone); });
        },
        zoneHasFinish: function () {
            return probes.anyZone().some(function (zone) {
                return probes.zoneClaimed(zone) &&
                    ((zone.base && zone.base !== 'none') || (zone.finish && zone.finish !== 'none'));
            });
        },
        zoneHasPattern: function () {
            var zs = probes.anyZone();
            for (var i = 0; i < zs.length; i++) {
                var z = zs[i]; if (!z) continue;
                if (z.pattern && z.pattern !== 'none') return true;
                if (Array.isArray(z.patternStack) && z.patternStack.length) return true;
            }
            return false;
        },
        zoneHasOverlay: function () {
            var zs = probes.anyZone();
            for (var i = 0; i < zs.length; i++) {
                var z = zs[i]; if (!z) continue;
                if (z.secondBase || z.thirdBase || z.fourthBase || z.fifthBase) return true;
            }
            return false;
        },
        zoneHasSpec: function () {
            var zs = probes.anyZone();
            for (var i = 0; i < zs.length; i++) {
                var z = zs[i]; if (!z) continue;
                if (z.zoneSpecMapPath) return true;
                if (z.specPattern && z.specPattern !== 'none') return true;
                if (Array.isArray(z.specPatternStack) && z.specPatternStack.length) return true;
            }
            return false;
        },
        zoneRestricted: function () {
            var zs = probes.anyZone();
            for (var i = 0; i < zs.length; i++) { if (zs[i] && (probes.regionHasPixels(zs[i]) || zs[i].sourceLayer)) return true; }
            return false;
        },
        previewLive: function () {
            var img = $('livePreviewImg');
            return !!(img && img.src && img.src.length > 20);
        },
        hasRendered: function () {
            // renderHistory is a top-level let in paint-booth-5-api-render.js,
            // unshifted on every successful render. Global-lexical, so readable
            // cross-script via typeof (never throws).
            try { return (typeof renderHistory !== 'undefined' && Array.isArray(renderHistory) && renderHistory.length > 0); }
            catch (e) { return false; }
        },
        paintModeActive: function () {
            // A brush-family canvas mode is armed (used with the pushUndo hook).
            try {
                if (typeof canvasMode === 'undefined') return false;
                return /brush|eras|smudge|clone|recolor|dodge|burn|blur|pencil|spray|paint/i.test(String(canvasMode));
            } catch (e) { return false; }
        }
    };

    // ==========================================================================
    // QUESTS — id, title, skill, group ('core' = sequential spine, 'further' =
    // unlocked all at once when core completes), chip hint, instruction body,
    // spotlight target(), auto-done probe done() (null = hook/manual-driven).
    // ==========================================================================
    var QUESTS = [
        {
            id: 'q-load', group: 'core', skill: 'load',
            title: 'Get your car in here',
            chip: 'Everything starts with your car. Load the paint you race with.',
            body: 'At the top, choose <b>PSD/XCF/ORA</b> to open a layered car template, or <b>TGA/PNG/JPEG</b> to open an existing paint image. A layered template keeps numbers, logos and body paint separate for editing. Your paint appears under <b>SOURCE</b> when it loads.',
            target: function () { return $('paintFile'); },
            done: function () { return probes.paintLoaded() || probes.psdLayerCount() > 0; }
        },
        {
            id: 'q-zone', group: 'core', skill: 'zone',
            title: 'Claim your pixels',
            chip: 'Choose where the finish goes. Pick a color on the car, or draw a selection.',
            body: 'A <b>Zone</b> controls where a finish appears. Use <b>&#127919; PICK COLOR FROM CAR</b> in the Zone panel, then click a color on SOURCE. First click sets it; more clicks add colors. To choose an area by hand, use <b>Rectangle</b> or <b>Lasso</b> in Zone mode instead. Either method completes this step.',
            target: function () { return findByText('button', 'PICK COLOR FROM CAR'); },
            done: function () { return probes.zoneHasColor(); }
        },
        {
            id: 'q-finish', group: 'core', skill: 'finish',
            title: 'Drop a finish',
            // SPB-93 2026-09-07: fresh Easy profile exposed2774 choices at
            // its first finish step. Give one concrete route into the full library.
            chip: 'Try Chrome from Foundation Bases, then click Apply.',
            body: 'Click the <b>Base</b> swatch, open <b>FOUNDATIONS → FOUNDATION BASES</b>, and choose <b>Chrome</b> for a first test. Click <b>Apply</b> in its preview card to put it on your Zone. In each split swatch, the left half shows paint and the right half shows its material map. Your finish applies inside the area you claimed; the preview updates automatically. You can return to the full library any time.',
            target: function () { return document.querySelector('.zone-editor-float .swatch-trigger') || document.querySelector('.swatch-trigger'); },
            done: function () { return probes.zoneHasFinish(); }
        },
        {
            id: 'q-setup', group: 'core', skill: 'setup',
            title: 'Point SPB at iRacing',
            chip: 'One-time setup: your iRacing ID and your car\u2019s paint folder.',
            body: 'Top of the window: type your <b>iRacing User ID</b> (4\u20137 digits) and set the <b>iRacing Car Folder</b> — a <b>folder</b>, not a file: <i>Documents\\iRacing\\paint\\&lt;your car&gt;</i>. Your renders land there.',
            target: function () { return $('iracingId'); },
            done: function () {
                try {
                    var id = $('iracingId'), dir = $('outputDir');
                    var idOk = !!(id && /^\d{4,7}$/.test(String(id.value || '').trim()));
                    var dirOk = !!(dir && String(dir.value || '').trim().length > 3);
                    return idOk && dirOk;
                } catch (e) { return false; }
            }
        },
        {
            id: 'q-render', group: 'core', skill: 'render',
            title: 'Send it to the track',
            chip: 'Hit RENDER — paint + spec files land in your iRacing folder.',
            body: 'Hit <b>RENDER</b>. Full-quality paint + spec files are written where iRacing reads them — reload the garage and admire. Turn on <b>Auto-Deploy</b> in Settings and every render lands automatically.',
            target: function () { return $('btnRender'); },
            done: function () { return probes.hasRendered(); }
        },
        {
            id: 'q-pattern', group: 'further', skill: 'pattern',
            title: 'Break up the surface',
            chip: 'Solid finishes are half the catalog. Add a pattern — carbon, sunray, flames.',
            body: 'Open the <b>PATTERN</b> section of a zone and pick one. Scale, rotate and offset it until it sits right — the live preview shows every tweak.',
            target: function () { return findByText('.zone-editor-float .section-header', 'PATTERN'); },
            done: function () { return probes.zoneHasPattern(); }
        },
        {
            id: 'q-spec', group: 'further', skill: 'spec',
            title: 'Feel the material',
            chip: 'Metallic, Roughness, Clearcoat — the three dials that make chrome chrome.',
            body: 'Look at the <b>channel row above the preview</b> — COMBINED, <b>R METAL</b>, <b>G ROUGH</b>, <b>B COAT</b>. M = how metallic, R = how rough, CC = clearcoat depth. Open the <b>Spec Map Inspector</b> for the full view and watch a channel change as you tweak a finish.',
            target: function () { return $('specChannelDock') || $('btnSpecMapInspector'); },
            done: function () { return state.specTouched || probes.zoneHasSpec(); }
        },
        {
            id: 'q-overlay', group: 'further', skill: 'overlay',
            title: 'Stack a second material',
            chip: 'Overlays layer one material over another — pearl over candy, wear over chrome.',
            body: 'Open <b>OVERLAYS</b> in a zone and give <b>layer 2</b> a base. Each overlay is a full material with its own strength and blend mode — up to 5 stacked.',
            target: function () { return findByText('.zone-editor-float .section-header', 'OVERLAY'); },
            done: function () { return probes.zoneHasOverlay(); }
        },
        {
            id: 'q-restrict', group: 'further', skill: 'restrict',
            title: 'Paint inside the lines',
            chip: 'Restrict a zone to a box, a lasso, or one PSD layer. Sponsors stay safe.',
            body: 'Use <b>&#127919; Use Region</b> (the eyedropper strip) to box in exactly where the zone may paint — or <b>RESTRICT TO LAYER</b> in the zone panel so only one PSD layer takes paint.',
            target: function () { return findByText('button', 'Use Region'); },
            done: function () { return probes.zoneRestricted(); }
        },
        {
            id: 'q-touchup', group: 'further', skill: 'brush',
            title: 'Fix it by hand',
            chip: 'One stray pixel? The brush tools work right on the canvas.',
            body: 'Grab the <b>&#128396; Brush</b> from the top toolbar and paint a touch-up right on the canvas. Eraser undoes, Size/Opacity live in the Tool Options bar.',
            target: function () { return document.querySelector('#spbTopToolbar button[title*="Brush" i]') || findByText('#spbTopToolbar button', 'Brush'); },
            done: null // completes via the pushUndo / _pushLayerUndo hooks (questHit)
        },
        {
            id: 'q-recipe', group: 'further', skill: 'recipe',
            title: 'Keep it forever',
            chip: 'Save the whole build — reapply it to next week\u2019s car in one click.',
            body: 'In the zone panel\u2019s <b>⋮ More</b> menu, hit <b>&#128190; SAVE SHOKK</b>. Your whole build — zones, finishes, patterns — is saved and can be reloaded onto any car.',
            target: function () { return findByText('button', 'SAVE SHOKK'); },
            done: null // completes via the confirmSaveShokk hook (questHit)
        }
    ];
    var CORE_IDS = ['q-load', 'q-zone', 'q-finish', 'q-setup', 'q-render'];

    function questById(qid) {
        for (var i = 0; i < QUESTS.length; i++) { if (QUESTS[i].id === qid) return QUESTS[i]; }
        return null;
    }
    function coreComplete() {
        for (var i = 0; i < CORE_IDS.length; i++) { if (!state.questsDone[CORE_IDS[i]]) return false; }
        return true;
    }
    function allComplete() {
        for (var j = 0; j < QUESTS.length; j++) { if (!state.questsDone[QUESTS[j].id]) return false; }
        return true;
    }

    // ---- engine --------------------------------------------------------------
    // The next obvious move: first incomplete core quest, else first incomplete
    // further quest (available once core is done). null when there's nothing to say.
    function pickNextMove() {
        if (!state.wheelsOn || state.graduated) return null;
        for (var i = 0; i < CORE_IDS.length; i++) {
            if (!state.questsDone[CORE_IDS[i]]) return questById(CORE_IDS[i]);
        }
        for (var j = 0; j < QUESTS.length; j++) {
            var q = QUESTS[j];
            if (q.group !== 'further' || state.questsDone[q.id]) continue;
            if (q.skill && (state.skillCount[q.skill] || 0) >= SKILL_RETIRE) continue;
            return q;
        }
        return null;
    }

    function completeQuest(q, silent) {
        if (state.questsDone[q.id]) return false;
        state.questsDone[q.id] = true;
        state.lastProgressAt = Date.now();
        if (q.skill) state.skillCount[q.skill] = (state.skillCount[q.skill] || 0) + 1;
        if (!silent) {
            if (allComplete() && !state.allDoneCelebrated) {
                state.allDoneCelebrated = true;
                toast('🏆 All quests complete — you\u2019re riding on your own now. The 🎓 button is there if you ever want a refresher.');
            } else if (q.id === 'q-render') {
                toast('You just painted a car. 🏁 That\u2019s the whole loop: load → pick pixels → pick a finish → render. New quests unlocked: patterns, spec, overlays.');
            } else {
                toast('✅ ' + q.title + ' — done!');
            }
        }
        lsSave();
        return true;
    }

    // Scan all auto-probed quests; complete any that flipped true. The first
    // pass after boot is silent (baseline sync — an existing project shouldn't
    // trigger a toast parade).
    function syncQuests() {
        var changed = false;
        for (var i = 0; i < QUESTS.length; i++) {
            var q = QUESTS[i];
            if (!q.done || state.questsDone[q.id]) continue;
            var isDone = false;
            try { isDone = !!q.done(); } catch (e) { isDone = false; }
            if (isDone) { completeQuest(q, !_baselineDone); changed = true; }
        }
        _baselineDone = true;
        return changed;
    }

    // ---- spotlight (reuses the coach's .spb-guide-ring styles) ----------------
    function spotlight(el) {
        clearRing();
        if (!el) return;
        try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (e) { try { el.scrollIntoView(); } catch (e2) {} }
        var ring = document.createElement('div');
        ring.className = 'spb-guide-ring';
        ring.setAttribute('aria-hidden', 'true');
        document.body.appendChild(ring);
        _ring = ring;
        var frame = null;
        function position() {
            frame = null;
            if (_ring !== ring) return;
            if (el.isConnected === false) { clearRing(); return; }
            var r = el.getBoundingClientRect();
            ring.style.left = (r.left - 6 + window.scrollX) + 'px';
            ring.style.top = (r.top - 6 + window.scrollY) + 'px';
            ring.style.width = (r.width + 12) + 'px';
            ring.style.height = (r.height + 12) + 'px';
        }
        function schedule() {
            if (frame === null) frame = window.requestAnimationFrame(position);
        }
        // SPB-93 2026-09-07: smooth nested-panel scrolling moved the target
        // after the initial measurement; the ring highlighted Hard Edge instead.
        document.addEventListener('scroll', schedule, true);
        window.addEventListener('resize', schedule);
        _ringCleanup = function () {
            document.removeEventListener('scroll', schedule, true);
            window.removeEventListener('resize', schedule);
            if (frame !== null) window.cancelAnimationFrame(frame);
        };
        position();
        _ringTimer = setTimeout(clearRing, 4500);
        try { if (typeof el.focus === 'function') el.focus({ preventScroll: true }); } catch (e) {}
    }
    function clearRing() {
        if (_ringTimer) { clearTimeout(_ringTimer); _ringTimer = null; }
        if (_ringCleanup) { _ringCleanup(); _ringCleanup = null; }
        if (_ring && _ring.parentNode) _ring.parentNode.removeChild(_ring);
        _ring = null;
    }

    // ==========================================================================
    // LEVEL DISCLOSURE (phase 2) — while wheels are on and level < 2, the zone
    // popout's advanced sections start collapsed. Peeking = clicking a section
    // header; the engine records it (persisted) and never re-collapses it.
    // Implemented entirely here by predictable section ids — no edits to
    // paint-booth-2-state-zones.js.
    // ==========================================================================
    var LEVEL2_SECTIONS = ['sectionPattern', 'sectionOverlays', 'sectionSpecPatterns', 'sectionSpecPreview', 'sectionZoneSpecSource'];

    function applyLevelDisclosure() {
        try {
            if (!document.body) return;
            var lvl = api.level();
            document.body.setAttribute('data-spb-wheels-level', String(lvl));

            // Refresh the 🎓 note at the top of the zone popout. Only shown
            // when there ARE managed sections present (no base = nothing to
            // tuck away), and never churned: create when missing, remove when
            // unwanted, leave alone otherwise (rebuilding it every poll would
            // eat clicks on its "don't show again" link).
            var host = document.querySelector('.zone-editor-float .zone-detail-body');
            var managedCount = 0;
            for (var m = 0; m < LEVEL2_SECTIONS.length; m++) {
                managedCount += document.querySelectorAll('.zone-editor-float .section-collapsible[id^="' + LEVEL2_SECTIONS[m] + '"]').length;
            }
            var wantNote = !!(state.wheelsOn && lvl < 2 && !state.levelNoteDismissed && host && managedCount > 0);
            var old = $('spbLevelNote');
            if (old && !wantNote) old.parentNode.removeChild(old);
            if (wantNote && !old) {
                var note = document.createElement('div');
                note.id = 'spbLevelNote';
                note.innerHTML = '🎓 Advanced sections are tucked away while you learn the loop. Click any section to peek — they open for good after your first render. <a href="#" onclick="event.preventDefault(); spbQuests.dismissLevelNote()">don\u2019t show again</a>';
                host.insertBefore(note, host.firstChild);
            }

            if (!state.wheelsOn || lvl >= 2) return;
            for (var s = 0; s < LEVEL2_SECTIONS.length; s++) {
                var prefix = LEVEL2_SECTIONS[s];
                if (state.userToggledSections[prefix]) continue;
                var els = document.querySelectorAll('.zone-editor-float .section-collapsible[id^="' + prefix + '"]');
                for (var k = 0; k < els.length; k++) els[k].classList.add('collapsed');
            }
        } catch (e) {}
        applyToolbarDisclosure();
    }

    // Top-toolbar disclosure (level 1): the 6 deep <details> menus (History /
    // Select / Retouch / Mask / Transform / Adjust) hide via CSS on
    // body[data-spb-wheels-level="1"]; a 🎓 peek button takes their place.
    // Peeking sets userToggledSections['toolbar'] → body[data-spb-toolbar-peek]
    // → CSS stands down. Fail-open: if any selector misses, nothing hides.
    function applyToolbarDisclosure() {
        try {
            if (!document.body) return;
            var lvl = api.level();
            var peeked = !!state.userToggledSections['toolbar'];
            if (peeked) document.body.setAttribute('data-spb-toolbar-peek', '1');
            else document.body.removeAttribute('data-spb-toolbar-peek');

            var bar = $('spbTopToolbar');
            var btn = $('spbToolbarPeek');
            var want = !!(state.wheelsOn && lvl < 2 && !peeked && bar);
            if (want && !btn) {
                btn = document.createElement('button');
                btn.type = 'button';
                btn.id = 'spbToolbarPeek';
                btn.className = 'spb-tb-summary';
                btn.innerHTML = '🎓 Menus';
                btn.title = 'Tool menus (History / Select / Retouch / Mask / Transform / Adjust) are tucked away while you learn the loop. Click to show them anyway — they appear on their own after your first render.';
                btn.addEventListener('click', function () {
                    state.userToggledSections['toolbar'] = true;
                    lsSave();
                    applyToolbarDisclosure();
                    toast('Tool menus unlocked for this app — they stay put. 🎓');
                });
                bar.appendChild(btn);
            } else if (!want && btn && btn.parentNode) {
                btn.parentNode.removeChild(btn);
            }
        } catch (e) {}
    }

    // Peeking: capture-phase so the header's own stopPropagation can't block it.
    function bindPeekListener() {
        document.addEventListener('click', function (ev) {
            try {
                var h = ev.target && ev.target.closest ? ev.target.closest('.zone-editor-float .section-header') : null;
                if (!h || !h.parentElement || !h.parentElement.id) return;
                var prefix = String(h.parentElement.id).replace(/\d+$/, '');
                if (LEVEL2_SECTIONS.indexOf(prefix) !== -1 && !state.userToggledSections[prefix]) {
                    state.userToggledSections[prefix] = true;
                    lsSave();
                }
            } catch (e) {}
        }, true);
    }

    // ==========================================================================
    // GLOBAL HOOKS (phase 2) — wrap existing app functions for instant sync and
    // for the two hook-driven quests. Every wrap is defensive: if the function
    // is missing or reassigned, nothing breaks; the 800ms poll is the fallback.
    // ==========================================================================
    var _zTimer = null;
    function afterZoneRender() {
        if (_zTimer) return;
        _zTimer = setTimeout(function () {
            _zTimer = null;
            syncQuests();
            applyLevelDisclosure();
            render(false);
        }, 60);
    }
    function wrapGlobal(fnName, after) {
        try {
            var orig = window[fnName];
            if (typeof orig !== 'function' || orig._spbQuestWrapped) return false;
            var wrapped = function () {
                var r = orig.apply(this, arguments);
                try { after(); } catch (e) {}
                return r;
            };
            wrapped._spbQuestWrapped = true;
            window[fnName] = wrapped;
            return true;
        } catch (e) { return false; }
    }
    function wrapAsyncGlobal(fnName, after) {
        try {
            var orig = window[fnName];
            if (typeof orig !== 'function' || orig._spbQuestWrapped) return false;
            var wrapped = function () {
                var p = orig.apply(this, arguments);
                if (p && typeof p.then === 'function') {
                    return p.then(function (r) { try { after(); } catch (e) {} return r; });
                }
                try { after(); } catch (e) {}
                return p;
            };
            wrapped._spbQuestWrapped = true;
            window[fnName] = wrapped;
            return true;
        } catch (e) { return false; }
    }
    function armHooks() {
        // Instant quest sync + disclosure refresh on any zone UI re-render.
        wrapGlobal('renderZones', afterZoneRender);
        wrapGlobal('renderZoneDetail', afterZoneRender);
        // q-touchup: a zone-canvas stroke in a brush-family mode, or any layer
        // pixel-paint op (brush/gradient/fill all go through _pushLayerUndo).
        wrapGlobal('pushUndo', function () { if (probes.paintModeActive()) api.questHit('q-touchup'); });
        wrapGlobal('_pushLayerUndo', function () { api.questHit('q-touchup'); });
        // q-recipe: the SAVE SHOKK dialog's confirm resolves → design is kept.
        wrapAsyncGlobal('confirmSaveShokk', function () { api.questHit('q-recipe'); });
    }
    function armHooksWithRetry() {
        armHooks();
        var tries = 0;
        var t = setInterval(function () {
            tries++;
            armHooks();
            var done = true;
            ['renderZones', 'renderZoneDetail', 'pushUndo', 'confirmSaveShokk'].forEach(function (n) {
                if (typeof window[n] === 'function' && !window[n]._spbQuestWrapped) done = false;
            });
            if (done || tries > 20) clearInterval(t);
        }, 500);
    }

    // ---- UI: next-move chip ----------------------------------------------------
    function questPosition(q) {
        // 1-based position inside its group for the "Next 2/5:" chip label.
        var list = q.group === 'core' ? CORE_IDS : QUESTS.filter(function (x) { return x.group === 'further'; }).map(function (x) { return x.id; });
        for (var i = 0; i < list.length; i++) { if (list[i] === q.id) return { n: i + 1, of: list.length }; }
        return null;
    }
    function renderChip() {
        var chip = $('spbQuestChip');
        if (!chip) return;
        var move = pickNextMove();
        var showGradOffer = state.wheelsOn && !state.graduated && !state.gradOfferDismissed && coreComplete();
        if ((!move && !showGradOffer) || state.chipDismissed || state.panelOpen) {
            chip.style.display = 'none';
            return;
        }
        chip.style.display = 'block';
        if (showGradOffer) {
            chip.innerHTML =
                '<div class="spb-quest-chip-title">🏁 Core Loop complete!</div>' +
                '<div class="spb-quest-chip-hint">You know the loop — load, zone, finish, render. Want the training wheels off?</div>' +
                '<div class="spb-quest-chip-row">' +
                '<button type="button" class="spb-quest-chip-btn primary" onclick="spbQuests.graduate(true)">Wheels off</button>' +
                '<button type="button" class="spb-quest-chip-btn" onclick="spbQuests.graduate(false)">Keep them</button>' +
                '</div>';
            return;
        }
        var pos = questPosition(move);
        var posLabel = pos && move.group === 'core' ? (' ' + pos.n + '/' + pos.of) : '';
        chip.innerHTML =
            '<div class="spb-quest-chip-title">🎓 Next' + posLabel + ': ' + move.title + '</div>' +
            '<div class="spb-quest-chip-hint">' + move.chip + '</div>' +
            '<div class="spb-quest-chip-row">' +
            '<button type="button" class="spb-quest-chip-btn primary" onclick="spbQuests.showMe()">🔍 Show me</button>' +
            '<button type="button" class="spb-quest-chip-btn" onclick="spbQuests.openPanel()">Quests</button>' +
            '<button type="button" class="spb-quest-chip-x" onclick="spbQuests.dismissChip()" title="Hide hints — reopen any time from the 🎓 button">✕</button>' +
            '</div>';
        // Arm the chip's quest only if nothing else is armed (a quest the user
        // picked from the checklist always wins).
        if (!state.activeQuest || state.questsDone[state.activeQuest]) state.activeQuest = move.id;
    }

    // ---- UI: quest checklist panel (owns the coach's #spbGuidePanel shell) -----
    function questRowHtml(q, locked) {
        var done = !!state.questsDone[q.id];
        var icon = done ? '✅' : (locked ? '🔒' : '○');
        var cls = 'spb-quest-row' + (done ? ' done' : '') + (locked ? ' locked' : '');
        return '<button type="button" class="' + cls + '" data-qid="' + q.id + '"' + (locked ? ' disabled' : '') + '>' +
            '<span class="spb-quest-row-icon">' + icon + '</span>' +
            '<span class="spb-quest-row-title">' + q.title + '</span></button>';
    }
    function renderPanel() {
        var panel = $('spbGuidePanel');
        if (!panel) return;
        if (!state.panelOpen) { panel.style.display = 'none'; return; }
        panel.style.display = 'block';

        var doneCount = 0;
        for (var dc = 0; dc < QUESTS.length; dc++) { if (state.questsDone[QUESTS[dc].id]) doneCount++; }
        var head = '<div class="spb-guide-head"><span>&#127891; TRAINING WHEELS · ' + doneCount + '/' + QUESTS.length + '</span>' +
            (state.panelExpanded ? '<button type="button" class="spb-guide-nav" onclick="spbQuests.minimizePanel()" aria-label="Minimize Training Wheels">Minimize</button>' : '<button type="button" class="spb-guide-nav" onclick="spbQuests.openChecklist()" aria-expanded="false">All quests</button>') +
            '<button type="button" class="spb-guide-x" onclick="spbQuests.closePanel()" title="Close Training Wheels" aria-label="Close Training Wheels">×</button></div>' +
            '<div class="spb-quest-progress" aria-hidden="true"><div class="spb-quest-progress-fill" style="width:' + Math.round(doneCount / QUESTS.length * 100) + '%"></div></div>';

        if (!state.wheelsOn) {
            panel.innerHTML = head + '<div class="spb-guide-body">' +
                '<div class="spb-guide-title">Wheels are off. 🚴</div>' +
                '<div class="spb-guide-sub">You\u2019re riding the full app. Any time you want the hints and quests back, flip the switch.</div>' +
                '<div class="spb-guide-row"><button type="button" class="spb-guide-next" onclick="spbQuests.on()">Turn Training Wheels back on</button></div></div>';
            return;
        }

        // Owner09-08: one next action in the corner; full checklist stays available.
        if (!state.panelExpanded) {
            var next = (state.activeQuest && !state.questsDone[state.activeQuest] && questById(state.activeQuest)) || pickNextMove();
            panel.innerHTML = head + '<div class="spb-guide-body spb-guide-compact">' +
                (next ? '<button type="button" class="spb-guide-next" onclick="spbQuests.startQuest(\'' + next.id + '\')">Next: ' + next.title + '</button>' :
                    '<span>All quests complete.</span>') + '</div>';
            return;
        }

        // Detail view for the armed quest
        var q = state.activeQuest ? questById(state.activeQuest) : null;
        if (q && (q.group === 'core' || coreComplete())) {
            var isDone = !!state.questsDone[q.id] || (q.done ? (function () { try { return !!q.done(); } catch (e) { return false; } })() : false);
            panel.innerHTML = head + '<div class="spb-guide-body">' +
                '<div class="spb-guide-title">' + q.title + (isDone ? ' <span class="spb-guide-done">✓ done</span>' : '') + '</div>' +
                '<div class="spb-guide-sub">' + q.body + '</div>' +
                '<div class="spb-guide-row">' +
                '<button type="button" class="spb-guide-show" onclick="spbQuests.showMe()">🔍 Show me where</button>' +
                '<span style="flex:1"></span>' +
                '<button type="button" class="spb-guide-nav" onclick="spbQuests.backToList()">← Quests</button>' +
                (!state.questsDone[q.id] ? '<button type="button" class="spb-guide-next" onclick="spbQuests.markDone(\'' + q.id + '\')">✓ I did it</button>' : '') +
                '</div></div>';
            return;
        }

        // Checklist view
        var html = head + '<div class="spb-guide-body spb-quest-list">';
        html += '<div class="spb-quest-group">THE CORE LOOP</div>';
        for (var i = 0; i < CORE_IDS.length; i++) html += questRowHtml(questById(CORE_IDS[i]), false);
        html += '<div class="spb-quest-group">GO FURTHER' + (coreComplete() ? '' : ' <span class="spb-quest-group-note">— finish the Core Loop first</span>') + '</div>';
        for (var j = 0; j < QUESTS.length; j++) {
            if (QUESTS[j].group === 'further') html += questRowHtml(QUESTS[j], !coreComplete());
        }
        if (allComplete()) {
            html += '<div class="spb-quest-grad"><div class="spb-quest-grad-title">🏆 All quests complete.</div>' +
                '<div class="spb-quest-grad-sub">You\u2019ve done everything the wheels can teach. The full app is yours — the 🎓 button stays if you ever want a refresher.</div></div>';
        } else if (coreComplete() && !state.graduated) {
            html += '<div class="spb-quest-grad"><div class="spb-quest-grad-title">🏁 You know the loop.</div>' +
                '<div class="spb-quest-grad-sub">Wheels off when you\u2019re ready — everything stays reversible.</div>' +
                '<div class="spb-guide-row">' +
                '<button type="button" class="spb-guide-next" onclick="spbQuests.graduate(true)">Turn Training Wheels off</button>' +
                '<button type="button" class="spb-guide-nav" onclick="spbQuests.graduate(false)">Keep them on</button>' +
                '</div></div>';
        }
        html += '<div class="spb-quest-foot"><a href="#" onclick="event.preventDefault(); spbQuests.reset(); spbQuests.openPanel();">↺ start the quests over</a></div>';
        html += '</div>';
        panel.innerHTML = html;

        var rows = panel.querySelectorAll('.spb-quest-row:not(.locked)');
        for (var k = 0; k < rows.length; k++) {
            (function (row) {
                row.addEventListener('click', function () {
                    var qid = row.getAttribute('data-qid');
                    var quest = questById(qid);
                    // SPB-93: completed lessons remain useful reference; do not reset progress.
                    if (quest) { state.activeQuest = qid; lsSave(); render(true); api.showMe(); }
                });
            })(rows[k]);
        }
    }

    // ---- render orchestration (skip no-op re-renders so in-flight clicks live)
    function signature() {
        return JSON.stringify([state.wheelsOn, state.questsDone, state.activeQuest,
            state.chipDismissed, state.graduated, state.gradOfferDismissed, state.panelOpen, state.panelExpanded, state.specTouched,
            state.firstWinDone, state.levelNoteDismissed, coreComplete()]);
    }
    function render(force) {
        var sig = signature();
        if (!force && sig === _lastSig) return;
        _lastSig = sig;
        renderChip();
        renderPanel();
        var t = $('spbGuideToggle');
        if (t) t.classList.toggle('active', !!state.panelOpen);
        var cb = $('trainingWheelsCheckbox');
        if (cb) cb.checked = !!state.wheelsOn;
    }

    function tick() {
        var changed = syncQuests();
        applyLevelDisclosure();
        // Park chip/panel while a full-screen takeover is up (swatch picker,
        // Finish Library, SHOKK Library — they own the screen; both quest UI
        // pieces come back when the takeover closes).
        try {
            var parked = false;
            var overlays = ['swatchPopup', 'finishLibraryBackdrop', 'shokkLibraryModal'];
            for (var oi = 0; oi < overlays.length && !parked; oi++) {
                var ov = $(overlays[oi]);
                if (ov && typeof getComputedStyle === 'function' && getComputedStyle(ov).display !== 'none') parked = true;
            }
            if (document.body) document.body.classList.toggle('spb-picker-open', parked);
        } catch (e) {}
        // Stuck nudge: wheels on, core loop unfinished, chip dismissed, nothing
        // completed for 5 minutes → the chip quietly re-offers the next move.
        // Rate-limited to once per 30 minutes so it can never nag.
        try {
            var now = Date.now();
            if (state.wheelsOn && !state.graduated && state.chipDismissed && !state.panelOpen &&
                !coreComplete() &&
                now - (state.lastProgressAt || _bootAt) > 5 * 60 * 1000 &&
                now - (state.lastNudgeAt || 0) > 30 * 60 * 1000) {
                state.chipDismissed = false;
                state.lastNudgeAt = now;
                lsSave();
                toast('Still here if you want the next step. 🎓');
            }
        } catch (e) {}
        render(changed);
    }

    // ---- public API -------------------------------------------------------------
    var api = {
        // wheels master switch
        on: function () { state.choiceMade = true; state.wheelsOn = true; state.graduated = false; state.chipDismissed = false; state.panelOpen = true; state.panelExpanded = false; lsSave(); applyLevelDisclosure(); render(true); renderChoice(); },
        off: function () { state.choiceMade = true; state.wheelsOn = false; state.panelOpen = false; state.chipDismissed = true; clearRing(); lsSave(); applyLevelDisclosure(); render(true); renderChoice(); },
        toggle: function () { state.wheelsOn ? api.off() : api.on(); },
        isOn: function () { return !!state.wheelsOn; },

        // panel
        openPanel: function () { if (!state.wheelsOn) { api.on(); return; } state.panelOpen = true; lsSave(); render(true); },
        closePanel: function () { api.off(); },
        togglePanel: function () { state.panelOpen ? api.closePanel() : api.openPanel(); },
        backToList: function () { state.activeQuest = null; state.panelExpanded = true; lsSave(); render(true); },
        openChecklist: function () { state.activeQuest = null; state.panelExpanded = true; state.panelOpen = true; lsSave(); render(true); },
        minimizePanel: function () { state.panelExpanded = false; clearRing(); lsSave(); render(true); },

        // quests
        startQuest: function (qid) {
            if (!questById(qid)) return;
            if (!state.wheelsOn) api.on();
            state.activeQuest = qid; state.panelOpen = true; state.panelExpanded = true;
            lsSave(); render(true); api.showMe();
        },
        showMe: function () {
            var q = state.activeQuest ? questById(state.activeQuest) : pickNextMove();
            if (!q) return;
            var el = q.target ? q.target() : null;
            if (el) spotlight(el);
            else toast('That control is not on screen yet — follow the instruction text.');
        },
        markDone: function (qid) {
            var q = questById(qid);
            if (!q) return;
            completeQuest(q, false);
            state.activeQuest = null;
            lsSave(); render(true);
        },
        // Hook-driven completion (pushUndo / _pushLayerUndo / confirmSaveShokk).
        questHit: function (qid) {
            if (!state.wheelsOn) return;
            var q = questById(qid);
            if (q && !state.questsDone[qid]) { completeQuest(q, false); render(true); }
        },

        // chip
        dismissChip: function () { api.off(); },

        // graduation
        graduate: function (wheelsOff) {
            if (wheelsOff) {
                state.graduated = true; state.wheelsOn = false;
                toast('Wheels off. 🚴 The 🎓 button brings them back any time.');
                state.chipDismissed = true;
            } else {
                // "Keep them on": stop offering graduation, but KEEP the chip —
                // the remaining quests (patterns, spec, overlays…) still need it.
                state.gradOfferDismissed = true;
                state.chipDismissed = false;
                toast('Wheels stay on — the next quests are in the chip and the 🎓 list.');
            }
            lsSave(); applyLevelDisclosure(); render(true);
        },

        // level disclosure
        dismissLevelNote: function () { state.levelNoteDismissed = true; lsSave(); applyLevelDisclosure(); render(true); },

        // Easy Mode → Pro bridge: a whole-car save landed the user in the editor.
        notifyFirstWin: function () {
            if (state.firstWinDone) return;
            state.firstWinDone = true;
            ['q-load', 'q-zone', 'q-finish'].forEach(function (qid) {
                var q = questById(qid);
                if (q && !state.questsDone[qid]) completeQuest(q, true);
            });
            state.activeQuest = 'q-render';
            state.chipDismissed = false;
            lsSave();
            toast('That finish you picked lives in a zone. One step left — send it to the track. 🏁');
            render(true);
        },

        // progressive-disclosure hook for CSS / future data-level work
        level: function () {
            if (!state.wheelsOn || state.graduated || allComplete()) return 3;
            return coreComplete() ? 2 : 1;
        },

        reset: function () {
            try { localStorage.removeItem(LS_KEY); } catch (e) {}
            for (var k in state) { if (typeof state[k] === 'boolean') state[k] = false; }
            state.wheelsOn = true; state.choiceMade = true; state.questsDone = {}; state.skillCount = {};
            state.userToggledSections = {};
            state.lastProgressAt = 0; state.lastNudgeAt = 0;
            _baselineDone = false;
            lsSave(); applyLevelDisclosure(); render(true);
        },
        _state: function () { return state; },
        _probes: probes,
        _quests: QUESTS
    };
    window.spbQuests = api;

    // Owner09-08: an optional corner invitation, never a new workspace row.
    function renderChoice() {
        var choice = $('spbTrainingChoice');
        if (!choice && !state.choiceMade) {
            choice = document.createElement('div');
            choice.id = 'spbTrainingChoice';
            choice.setAttribute('role', 'dialog');
            choice.setAttribute('aria-label', 'Training Wheels preference');
            choice.innerHTML = '<button type="button" class="spb-guide-x" onclick="spbQuests.off()" aria-label="Dismiss Training Wheels invitation">×</button>' +
                '<h3>Would you like Training Wheels?</h3><p>Get a small step-by-step guide while you learn. You can close it any time and bring it back with Tutorial.</p>' +
                '<button type="button" class="spb-guide-next" onclick="spbQuests.on()">Turn on</button> ' +
                '<button type="button" class="spb-guide-nav" onclick="spbQuests.off()">No thanks</button>';
            document.body.appendChild(choice);
        }
        if (choice) choice.style.display = state.choiceMade ? 'none' : 'block';
    }

    // ---- boot -------------------------------------------------------------------
    function init() {
        lsLoad();
        _bootAt = Date.now();

        // Chip + panel shells (panel id kept from the coach so its CSS applies).
        if (!$('spbQuestChip')) {
            var chip = document.createElement('div');
            chip.id = 'spbQuestChip';
            chip.style.display = 'none';
            chip.setAttribute('role', 'status');
            chip.setAttribute('aria-live', 'polite');
            document.body.appendChild(chip);
        }
        if (!$('spbGuidePanel')) {
            var panel = document.createElement('div');
            panel.id = 'spbGuidePanel';
            panel.style.display = 'none';
            panel.setAttribute('role', 'region');
            panel.setAttribute('aria-label', 'Training Wheels quest checklist');
            document.body.appendChild(panel);
        }

        // Spec-dock touch flag (quest q-spec): one passive listener each.
        ['specChannelDock', 'btnSpecMapInspector'].forEach(function (id) {
            var el = $(id);
            if (el && !el._spbQuestWired) {
                el._spbQuestWired = true;
                el.addEventListener('click', function () {
                    if (!state.specTouched) { state.specTouched = true; lsSave(); }
                }, { passive: true });
            }
        });

        // Settings → Options checkbox mirrors the wheels switch.
        var cb = $('trainingWheelsCheckbox');
        if (cb && !cb._spbQuestWired) {
            cb._spbQuestWired = true;
            cb.addEventListener('change', function () { cb.checked ? api.on() : api.off(); });
        }

        bindPeekListener();
        armHooksWithRetry();

        // ESC closes the panel and clears the spotlight (keyboard a11y).
        document.addEventListener('keydown', function (ev) {
            try {
                if (ev.key !== 'Escape') return;
                if (state.panelOpen) { api.closePanel(); ev.stopPropagation(); }
                else if (_ring) clearRing();
            } catch (e) {}
        }, true);

        syncQuests();          // silent baseline pass
        renderChoice();
        applyLevelDisclosure();
        render(true);
        setInterval(tick, POLL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 450); });
    } else {
        setTimeout(init, 450);
    }
})();
