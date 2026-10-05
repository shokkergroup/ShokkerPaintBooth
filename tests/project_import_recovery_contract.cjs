'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const start = source.indexOf('// [SPB review remediation 2026-08-22] Layer recovery');
const end = source.indexOf('// [SPB-HEADER-SLIM', start);
assert.ok(start > 0 && end > start);
const recovery = source.slice(start, end);
function run(options, accept) {
    const events = [];
    const saved = { sourcePaintFile: 'C:/audit.psd', savedAt: Date.now(), layers: [{}], schemaVersion: 2, cleanClose: false, sourceFingerprint: 'same' };
    vm.runInNewContext(recovery, {
        importOptions: options, normalizedPath: 'C:/audit.psd', SPB_LAYER_AUTOSAVE_KEY: 'key', SPB_LAYER_AUTOSAVE_SCHEMA: 2,
        localStorage: { getItem() { events.push('read'); return JSON.stringify(saved); }, setItem() { events.push('decline'); }, removeItem() { events.push('clear'); } },
        window: { confirm() { events.push('prompt'); return accept; } },
        _spbLayerSourceFingerprint: () => 'same', _pushLayerStackUndo: () => events.push('undo'),
        _spbApplyLayerStateLite: () => { events.push('restore'); return 1; },
        recompositeFromLayers: () => events.push('composite'), renderLayerPanel() {}, showToast() {},
    });
    return events;
}
assert.deepEqual(run({ restoreProject: true }, true), []);
assert.deepEqual(run(undefined, false), ['read', 'prompt', 'decline']);
assert.deepEqual(run({}, true), ['read', 'prompt', 'undo', 'restore', 'composite', 'clear']);
console.log('Actual import recovery: explicit Project skips recovery; ordinary import retains confirm, decline and undoable restore.');
