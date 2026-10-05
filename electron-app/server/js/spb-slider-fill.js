/* ===========================================================================
   SPB — SLIDER FILL runtime                                       2026-07-25
   ---------------------------------------------------------------------------
   Sole job: keep `--_pct` current on every <input type=range> so the orange
   fill in css/spb-slider-polish.css reaches the thumb. CSS alone cannot
   express "percent of the way between min and max", and
   ::-webkit-slider-runnable-track has no progress pseudo-element the way Gecko
   does — so the value has to be written from JS.

   (Promoted out of the discarded Aftershock skin, which the owner asked to
   drop apart from the sliders. Formerly js/spb-aftershock-skin.js.)

   Why this is safe:
     - It only ever WRITES A CSS CUSTOM PROPERTY. No value, no class, no
       attribute, no layout, no handler on any app control is touched.
     - `--_pct` is read by nothing except spb-slider-polish.css.
     - Listeners are passive + capture, so they can never swallow or reorder an
       event the app depends on.
     - If this file fails to load, the CSS falls back to --_pct:50% and sliders
       render styled-but-unfilled. Degraded, never broken.
   =========================================================================== */
(function () {
    'use strict';

    function pct(el) {
        var min = parseFloat(el.min); if (!isFinite(min)) min = 0;
        var max = parseFloat(el.max); if (!isFinite(max)) max = 100;
        var val = parseFloat(el.value); if (!isFinite(val)) val = min;
        var span = max - min;
        if (!(span > 0)) return 0;
        var p = ((val - min) / span) * 100;
        return p < 0 ? 0 : (p > 100 ? 100 : p);
    }

    function paint(el) {
        if (!el || el.type !== 'range') return;
        try { el.style.setProperty('--_pct', pct(el).toFixed(2) + '%'); } catch (e) {}
    }

    function refreshAll() {
        var list;
        try { list = document.querySelectorAll('input[type="range"]'); } catch (e) { return; }
        for (var i = 0; i < list.length; i++) paint(list[i]);
    }

    // The app builds sliders on demand (zone cards, adjust panel, finish picker
    // ratings), so a one-shot pass at boot is not enough. Delegated + capture so
    // it sees the event no matter how the app wires its own handlers.
    document.addEventListener('input',  function (e) { paint(e.target); }, { capture: true, passive: true });
    document.addEventListener('change', function (e) { paint(e.target); }, { capture: true, passive: true });

    // Sliders whose value is set programmatically (preset load, autosave restore,
    // zone switch) fire no event. Watch for DOM churn and re-paint, debounced so a
    // busy repaint of the zone list costs one pass, not one per node.
    var pending = 0;
    function scheduleRefresh() {
        if (pending) return;
        pending = setTimeout(function () { pending = 0; refreshAll(); }, 120);
    }

    function start() {
        refreshAll();
        var host = document.querySelector('.main-container') || document.body;
        if (host && window.MutationObserver) {
            try {
                new MutationObserver(scheduleRefresh)
                    .observe(host, { childList: true, subtree: true });
            } catch (e) { /* observer is an optimisation, not a requirement */ }
        }
    }

    // Exposed so any module can force a repaint after bulk-setting slider values.
    window.spbRefreshSliderFills = refreshAll;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start, { once: true });
    } else {
        start();
    }
})();
