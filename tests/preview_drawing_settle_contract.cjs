'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const start = source.indexOf('        function _schedulePreviewStages()');
const end = source.indexOf('\n        // [SPB-PERF', start);
assert(end > start);
let now = 0, hashCalls = 0, rendered = [], timers = new Map(), timerId = 0;
const context = {
    window: {}, isDrawing: true, performance: { now: () => now },
    previewRetryTimer: null, _previewStage2Timer: null, _previewEnhanceTimer: null, previewDebounceTimer: null,
    PREVIEW_SETTLE_DEBOUNCE_MS: 140, LIVE_PREVIEW_MAX_SCALE: 0.5, lastPreviewZoneHash: 'old', _lastPreviewScale: 0,
    getZoneConfigHash() { hashCalls++; return 'current-' + now; },
    updatePreviewStatus() {}, _previewEmptyState() {},
    doPreviewRender(hash, scale) { rendered.push({ hash, scale }); },
    clearTimeout(id) { timers.delete(id); },
    setTimeout(fn, ms) { timers.set(++timerId, { fn, ms }); return timerId; }
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
function tick() {
    assert.equal(timers.size, 1, 'one pending settle only');
    const [id, timer] = timers.entries().next().value;
    timers.delete(id); now += timer.ms; timer.fn();
}
context._schedulePreviewStages();
for (let i = 0; i < 15; i++) tick(); // A paused held stroke exceeds slider watchdog.
assert.equal(hashCalls, 0);
assert.equal(rendered.length, 0);
context.isDrawing = false;
tick();
assert.equal(hashCalls, 1);
assert.deepEqual(rendered, [{ hash: 'current-' + now, scale: 0.5 }]);
assert.equal(timers.size, 0);

// Existing slider watchdog remains intact; rearming coalesces instead of
// multiplying timers, and the release computes the latest state.
context.window._spbRangeDragActive = true;
context.window.__spbLastInputTs = now;
context._schedulePreviewStages(); context._schedulePreviewStages(); tick();
assert.equal(hashCalls, 1);
context.window._spbRangeDragActive = false; tick();
assert.equal(hashCalls, 2);

// Execute doPreviewRender's actual entry until its first source read. Ordinary
// retries stop before source/body/spinner work; interactive placement proceeds.
const entryStart = source.indexOf('        async function doPreviewRender(');
const cut = source.indexOf("            if (!paintFile) return;", entryStart);
const entry = source.slice(entryStart, cut) + '\n return paintFile;\n}';
let reschedules = 0, reads = 0;
const gate = { isDrawing: true, LIVE_PREVIEW_MAX_SCALE: 0.5,
    window: { SPBRenderReadiness: { reason: () => '' } }, // published source; readiness has its own contract
    _schedulePreviewStages() { reschedules++; },
    document: { getElementById() { reads++; return { value: 'live-source.tga' }; } } };
vm.createContext(gate); vm.runInContext(entry, gate);
(async () => {
    await gate.doPreviewRender('old', 0.5);
    assert.equal(reads, 0); assert.equal(reschedules, 1);
    assert.equal(await gate.doPreviewRender('current', 0.5, { interactive: true }), 'live-source.tga');
    assert.equal(reads, 1); assert.equal(reschedules, 1);
    gate.isDrawing = false;
    await gate.doPreviewRender('current', 0.5);
    assert.equal(reads, 2);
    console.log('Preview settle: held/paused canvas strokes defer all hash/source work; release renders latest state once; slider coalescing and explicit interactive placement preserved.');
})().catch(error => { console.error(error); process.exitCode = 1; });
