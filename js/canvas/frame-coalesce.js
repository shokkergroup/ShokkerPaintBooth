/* ============================================================================
 * SPB FRAME COALESCE — do drag work once per FRAME, not once per EVENT
 *                                                        2026-07-30, Claude
 *
 * WHY
 *   A mouse reports 125-1000 positions a second. A screen draws 60. Every drag
 *   handler in the app is wired straight to `mousemove`, so on a gaming mouse
 *   the app can do 8x the work it can possibly display — and each extra call is
 *   a full re-render of the decal overlay plus, for scale/rotate, a rebuild of
 *   the decal list DOM. Measured: zero rAF throttling on updateDecalDrag,
 *   updateDecalScaleFromMouse or updateDecalRotateFromMouse.
 *
 *   The work that gets thrown away is not free — it is what makes a drag feel
 *   heavy, because the extra calls run BETWEEN frames and delay the frame that
 *   the user is actually waiting to see.
 *
 * THE ONE RULE THAT MATTERS
 *   The LAST event must never be dropped. If a drag ends on a coalesced move
 *   that never ran, the decal lands a few pixels away from where the painter
 *   released it — a subtle, maddening bug. `wrap()` therefore exposes flush(),
 *   and the caller MUST flush on mouseup. That is why this is a named helper
 *   rather than three copies of a rAF guard: the flush is easy to forget.
 *
 * USAGE
 *   const move = SPBFrameCoalesce.wrap(updateDecalDrag);
 *   document.addEventListener('mousemove', e => move(x, y));
 *   document.addEventListener('mouseup', () => { move.flush(); ... });
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBFrameCoalesce = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    const raf = (typeof requestAnimationFrame === 'function')
        ? requestAnimationFrame
        : function (cb) { return setTimeout(function () { cb(Date.now()); }, 16); };
    const caf = (typeof cancelAnimationFrame === 'function')
        ? cancelAnimationFrame
        : clearTimeout;

    let coalesced = 0, executed = 0;

    /**
     * @param  {Function} fn      the expensive work
     * @param  {Object}   [opts]  {thisArg}
     * @return {Function}         call it as often as you like; it runs once per
     *                            frame with the most recent arguments.
     *                            .flush()  — run any pending call NOW (use on mouseup)
     *                            .cancel() — drop any pending call (use on abort/escape)
     */
    function wrap(fn, opts) {
        const thisArg = (opts && opts.thisArg) || null;
        let pendingArgs = null;
        let handle = 0;

        const run = function () {
            handle = 0;
            if (!pendingArgs) return;
            const args = pendingArgs;
            pendingArgs = null;
            executed++;
            fn.apply(thisArg, args);
        };

        const scheduled = function () {
            if (pendingArgs) coalesced++;      // a previous position never drew
            pendingArgs = arguments;
            if (!handle) handle = raf(run);
        };

        scheduled.flush = function () {
            if (handle) { caf(handle); handle = 0; }
            run();
        };
        scheduled.cancel = function () {
            if (handle) { caf(handle); handle = 0; }
            pendingArgs = null;
        };
        return scheduled;
    }

    /** Diagnostic: how many redundant updates were skipped. */
    function debugStats() {
        return { executed: executed, coalescedAway: coalesced,
                 savedPct: (executed + coalesced) ? +(100 * coalesced / (executed + coalesced)).toFixed(1) : 0 };
    }

    return { wrap: wrap, debugStats: debugStats };
});
