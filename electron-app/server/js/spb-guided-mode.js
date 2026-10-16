// ============================================================================
// SPB TUTORIAL — compatibility shim (2026-07-18)
//
// The 2026-07-04 step-by-step coach was absorbed into the Training Wheels
// quest engine (js/spb-quests.js, design: docs/SPB_TRAINING_WHEELS_QUEST_ENGINE.md).
// This file keeps the old surface alive so nothing else had to change:
//   - window.spbGuide API (Easy Mode "Teach me the full app" calls spbGuide)
//   - #spbGuideToggle 🎓 toolbar button (paint-booth-v2.html) + fallback pill
//   - localStorage "spb_guided_mode" resume (a user who left the coach on
//     gets the new quest panel instead of silence)
// The quest engine must load BEFORE this file (script-tag order in
// paint-booth-v2.html). Rollback: restore previous version of this file and
// remove js/spb-quests.js.
// ============================================================================
(function () {
    'use strict';

    var LS_KEY = 'spb_guided_mode';

    function engine() { return window.spbQuests || null; }

    // ---- legacy API → quest engine -------------------------------------------
    window.spbGuide = {
        toggle: function () { var e = engine(); if (e) e.togglePanel(); },
        on: function () {
            var q = engine(); if (q) { q.on(); q.openPanel(); }
        },
        off: function () {
            var q = engine(); if (q) q.closePanel();
        },
        // Old variants (tga/psd) both map onto the Core Loop start quest.
        start: function (/* variant */) { var q = engine(); if (q) q.startQuest('q-load'); },
        show: function () { var q = engine(); if (q) q.showMe(); },
        next: function () { var q = engine(); if (q) q.startQuest('q-load'); },
        back: function () { var q = engine(); if (q) q.backToList(); },
        finish: function () { var q = engine(); if (q) q.closePanel(); }
    };

    // ---- boot ------------------------------------------------------------------
    function init() {
        // The toggle lives in the top toolbar markup (owner 2026-07-04). Only
        // create the fallback pill if the toolbar button is ever removed.
        if (!document.getElementById('spbGuideToggle')) {
            var toggle = document.createElement('button');
            toggle.id = 'spbGuideToggle';
            toggle.type = 'button';
            toggle.className = 'spb-guide-fallback-pill';
            toggle.innerHTML = 'Tutorial';
            toggle.title = 'Training Wheels — step-by-step quests that teach the app while you use it. Toggle any time.';
            toggle.onclick = function () { window.spbGuide.toggle(); };
            document.body.appendChild(toggle);
        }

        // [TW-GONE 2026-10-12 owner: "The TRAINING WHEELS STILL keeps popping up ... Always showing 11/11 complete
        // ... I ALWAYS just have to X out. That is supposed to be gone"] Root cause: this legacy resume read the
        // 2026-07 coach key "spb_guided_mode" === 'on' and called openPanel() on EVERY boot, which switches the
        // wheels back on. The panel's X (spbQuests.closePanel -> off) never cleared that key, so it came back on
        // every launch. Legacy resume removed; the stale key is wiped. Training Wheels now open ONLY from the
        // Tutorial button / Settings checkbox.
        try { localStorage.removeItem(LS_KEY); } catch (e) {}
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 500); });
    } else {
        setTimeout(init, 500);
    }
})();
