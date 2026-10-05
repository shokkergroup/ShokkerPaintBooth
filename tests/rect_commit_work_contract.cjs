const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const rect = require('../js/canvas/zone/rect-marquee.js');
let seed = 930907;
const random = n => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed % n; };
for (let trial = 0; trial < 300; trial++) {
    const width = 2 + random(37), height = 2 + random(31);
    const before = Uint8Array.from({ length: width * height }, () => [0, 0, 1, 80, 254, 255][random(6)]);
    const copy = before.slice();
    const x1 = random(width), x2 = x1 + random(width - x1);
    const y1 = random(height), y2 = y1 + random(height - y1);
    for (const mode of ['add', 'subtract', 'replace']) {
        const actual = rect.composeMask(before, width, height, { x1, x2, y1, y2 }, mode);
        let differences = 0;
        const expected = Uint8Array.from(before, (value, i) => {
            const x = i % width, y = Math.floor(i / width);
            const inside = x >= x1 && x <= x2 && y >= y1 && y <= y2;
            const next = inside ? (mode === 'subtract' ? 0 : 255) : (mode === 'replace' ? 0 : value);
            if (value !== next) differences++;
            return next;
        });
        assert.deepEqual(actual.nextMask, expected);
        assert.equal(actual.changedPixels, differences);
        assert.equal(actual.enclosedPixels, (x2 - x1 + 1) * (y2 - y1 + 1));
        assert.deepEqual(before, copy, 'candidate creation must not mutate the history source');
    }
}

// Execute the production commit boundary, including feathering and a no-op.
const source = fs.readFileSync(require.resolve('../paint-booth-3-canvas.js'), 'utf8');
const commit = source.slice(source.indexOf('function commitRectSelection('), source.indexOf('function _completeRectGesture('));
for (const feather of [0, 2]) {
    const original = new Uint8Array(64), zone = { regionMask: original };
    let scans = 0, history = 0;
    const env = {
        Uint8Array, rectStart: { x: 1, y: 1 }, selectedZoneIndex: 0,
        _rectGestureState: null, _rectZoneCache: null, zones: [zone],
        document: { getElementById: id => id === 'paintCanvas' ? { width: 8, height: 8 } : { value: id === 'selectionMode' ? 'add' : String(feather) } },
        window: { SPBRectMarquee: { ...rect, countDifferences: (a, b) => { scans++; return rect.countDifferences(a, b); } },
            SPBPenPath: { featherMask: mask => { const result = mask.slice(); result[0] = 80; return result; } } },
        pushUndo: i => { assert.equal(i, 0); assert.equal(zone.regionMask, original); history++; },
        hideRectPreview() {}, renderRegionOverlay() {}, triggerPreviewRender() {}, showToast() {},
    };
    vm.createContext(env); vm.runInContext(commit, env);
    const event = { gesture: { x1: 1, y1: 1, x2: 4, y2: 4, width: 3, height: 3 } };
    assert.equal(env.commitRectSelection({ x: 4, y: 4 }, event), true);
    assert.equal(history, 1);
    assert.equal(scans, feather ? 1 : 0, 'only a modified feather candidate needs a second scan');
    assert.equal(zone.regionMask[0], feather ? 80 : 0);
    env.rectStart = { x: 1, y: 1 };
    assert.equal(env.commitRectSelection({ x: 4, y: 4 }, event), false);
    assert.equal(history, 1, 'repeating the same selection must not add history');
}
console.log('Rectangle work:900 soft-mask candidates match reference; input immutable; native commit preserves feather/no-op/history and skips redundant scans.');

const applySource = fs.readFileSync(require.resolve('../js/zones/source-color-apply-controls.js'), 'utf8');
for (const selected of [false, true]) {
    const mask = new Uint8Array(100); if (selected) mask[99] = 80;
    mask.some = () => { throw Error('must reuse shared count instead of callback scan'); };
    const zone = { regionMask: mask, useRegion: false, fitIntoApplyArea: true, name: 'Test' };
    let counts = 0, refreshes = 0;
    const env = { window: { document: {}, SPBMaskStats: { count: m => { counts++; let n=0; for(const v of m) if(v)n++; return n; } } } };
    vm.createContext(env); vm.runInContext(applySource, env);
    env.window.SPBZoneSourceColorApplyControls.install({ getZones: () => [zone], renderZones: () => refreshes++, updateRegionStatus: () => refreshes++ });
    assert.equal(env.window.autoActivateZoneApplyArea(0, 'rect'), selected);
    assert.equal(zone.useRegion, selected);
    assert.equal(counts, 1); assert.equal(refreshes, selected ? 2 : 0);
    if(selected) assert.equal(zone.patternPlacement, 'fit');
}
console.log('Apply-area activation: soft selection and empty mask retain activation/fit/refresh behavior with one shared count.');
