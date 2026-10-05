'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const stage = require('../js/canvas/zone/source-mask-transition.js').stage;
const geometry = require('../js/canvas/zone/canvas-mask-geometry.js');
const codec = {
    encode(mask, width, height) {
        const runs = [];
        for (const value of mask) {
            if (runs.length && runs.at(-1)[0] === value) runs.at(-1)[1]++;
            else runs.push([value, 1]);
        }
        return { width, height, runs };
    },
    decode(rle) {
        const mask = new Uint8Array(rle.width * rle.height);
        let index = 0;
        for (const [value, count] of rle.runs) { mask.fill(value, index, index + count); index += count; }
        assert.equal(index, mask.length);
        return mask;
    }
};
let seed = 73917;
function random(n) { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed % n; }
function reference(mask, ow, oh, w, h) {
    return Uint8Array.from({ length: w * h }, (_, i) => {
        const x = Math.floor(((i % w) + 0.5) * ow / w);
        const y = Math.floor((Math.floor(i / w) + 0.5) * oh / h);
        return mask[y * ow + x];
    });
}
for (let trial = 0; trial < 500; trial++) {
    const ow = 1 + random(35), oh = 1 + random(31), w = 1 + random(33), h = 1 + random(37);
    const mask = Uint8Array.from({ length: ow * oh }, () => random(256));
    const spatial = Uint8Array.from(mask, value => value % 3);
    const original = mask.slice(), originalSpatial = spatial.slice();
    const compressed = codec.encode(mask, ow, oh);
    const state = {
        zones: [{ id: 'a', base: 'chrome', useRegion: true, regionMask: mask, spatialMask: spatial }, { id: 'b' }],
        undo: [{ zoneIndex: 0, prevMask: mask }, { _rle: true, prevMask: null, prevMaskRLE: compressed },
            { batchMasks: [{ zoneId: 'a', prevMask: mask }] }],
        redo: [{ prevSpatial: spatial }],
        configUndo: [{ label: 'Base scale', snapshot: [{ id: 'a', baseScale: 1, spatialMask: spatial }] }],
        configRedo: [{ label: 'Base scale', snapshot: [{ id: 'a', baseScale: 2, spatialMask: spatial }] }]
    };
    const before = JSON.stringify(state);
    const next = stage(state, ow, oh, w, h, geometry, codec);
    const expected = reference(mask, ow, oh, w, h);
    assert.deepEqual(next.zones[0].regionMask, expected);
    assert.deepEqual(next.zones[0].spatialMask, reference(spatial, ow, oh, w, h));
    assert.deepEqual(next.undo[0].prevMask, expected);
    assert.deepEqual(codec.decode(next.undo[1].prevMaskRLE), expected);
    assert.equal(next.undo[1]._rle, true);
    assert.equal(next.undo[1].prevMask, null);
    assert.deepEqual(next.undo[2].batchMasks[0].prevMask, expected);
    assert.deepEqual(next.redo[0].prevSpatial, next.zones[0].spatialMask);
    assert.deepEqual(next.configUndo[0].snapshot[0].spatialMask, reference(spatial, ow, oh, w, h));
    assert.deepEqual(next.configRedo[0].snapshot[0].spatialMask, reference(spatial, ow, oh, w, h));
    assert.equal(next.configUndo[0].snapshot[0].baseScale, 1);
    assert.equal(next.configRedo[0].snapshot[0].baseScale, 2);
    assert.equal(next.configUndo[0].label, 'Base scale');
    assert.equal(next.zones[0].base, 'chrome');
    assert.equal(next.zones[0].useRegion, true);
    assert.strictEqual(next.zones[1], state.zones[1]);
    assert.deepEqual(mask, original);
    assert.deepEqual(spatial, originalSpatial);
    assert.equal(JSON.stringify(state), before, 'staging must never mutate rollback objects');
}
const saved = { zones: [{ regionMask: Uint8Array.from([0, 64, 128, 255]) }], undo: [], redo: [] };
assert.deepEqual(stage(saved, 300, 150, 4, 4, geometry, codec).zones[0].regionMask,
    reference(saved.zones[0].regionMask, 2, 2, 4, 4));
const malformed = { zones: [{ regionMask: new Uint8Array(7) }], undo: [], redo: [] };
assert.throws(() => stage(malformed, 3, 2, 4, 4, geometry, codec), /determine/);
assert.equal(malformed.zones[0].regionMask.length, 7);

// Execute the actual integration bridge: arrays keep identity and old entries
// remain usable for exact transaction rollback after a publication failure.
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const bridge = source.slice(source.indexOf('function _spbTransitionSourceMasks('), source.indexOf('function _spbCaptureSourceDocumentState()'));
const context = { window: { SPBSourceMaskTransition: { stage }, SPBCanvasMaskGeometry: geometry, decodeRegionMaskRLE: codec.decode },
    zones: saved.zones, undoStack: [{ prevMask: saved.zones[0].regionMask }], redoStack: [], encodeRegionMaskRLE: codec.encode };
vm.createContext(context);
vm.runInContext(bridge, context);
const oldZones = context.zones, oldUndo = context.undoStack.slice(), stackRef = context.undoStack;
context._spbTransitionSourceMasks(2, 2, 4, 4);
assert.strictEqual(context.undoStack, stackRef);
assert.equal(context.undoStack[0].prevMask.length, 16);
context.zones = oldZones;
context.undoStack.splice(0, context.undoStack.length, ...oldUndo);
assert.strictEqual(context.zones, saved.zones);
assert.equal(context.undoStack[0].prevMask.length, 4);
for (const [begin, end] of [['async function loadPaintPreviewFromServer(', 'window.loadPaintPreviewFromServer ='],
    ['async function _doPSDImport(', 'function countLayers(']]) {
    const body = source.slice(source.indexOf(begin), source.indexOf(end, source.indexOf(begin)));
    assert(body.indexOf('_spbCaptureSourceDocumentState()') < body.indexOf('_spbTransitionSourceMasks('));
    assert(body.includes('_spbRestoreSourceDocumentState(previous)'));
}
console.log('Source mask transition: 500 non-square soft/discrete mask and raw/compressed/batch Undo/Redo cases; immutable staging, startup recovery, invalid-shape rejection and actual transaction bridge pass.');

// Actual Zone-config Undo/Redo restores the new-grid spatial mask and retains
// the live region by id, even though each stack owns separate recipe snapshots.
const zoneSource = fs.readFileSync('paint-booth-2-state-zones.js', 'utf8');
const zoneUndo = zoneSource.slice(zoneSource.indexOf('function undoZoneChange()'), zoneSource.indexOf('function jumpToUndoState('));
const spatial = Uint8Array.from([0, 1, 2, 1]);
context.zoneUndoStack = [{ label: 'Scale', snapshot: [{ id: 'a', baseScale: 1, spatialMask: spatial }] }];
context.zoneRedoStack = [{ label: 'Later', snapshot: [{ id: 'a', baseScale: 3, spatialMask: spatial }] }];
context.zones = [{ id: 'a', baseScale: 2, spatialMask: spatial, regionMask: saved.zones[0].regionMask }];
const configAlias = context.zoneUndoStack;
context._spbTransitionSourceMasks(2, 2, 4, 4);
assert.strictEqual(context.zoneUndoStack, configAlias);
assert.equal(context.zoneRedoStack[0].snapshot[0].spatialMask.length, 16);
Object.assign(context, {selectedZoneIndex:0, undoHistoryPointer:1, showToast(){}, renderZones(){}, _requestZoneLivePreview(){}, renderUndoHistoryPanel(){},
    _cloneUint8ArrayLike: mask => mask?.slice() || null,
    _cloneZoneState: zone => ({...zone, spatialMask:zone.spatialMask?.slice(), regionMask:null}),
    _ensureZoneShape: zone => ({...zone, spatialMask:zone.spatialMask?.slice()})});
vm.runInContext(zoneUndo, context);
assert.equal(context.undoZoneChange(), true);
assert.equal(context.zones[0].baseScale, 1);
assert.deepEqual(context.zones[0].spatialMask, reference(spatial, 2, 2, 4, 4));
assert.deepEqual(context.zones[0].regionMask, reference(saved.zones[0].regionMask, 2, 2, 4, 4));
assert.equal(context.redoZoneChange(), true);
assert.equal(context.zones[0].baseScale, 2);
assert.deepEqual(context.zones[0].spatialMask, reference(spatial, 2, 2, 4, 4));
console.log('Zone-config source transition: 500 snapshot grids and actual recipe Undo/Redo retain spatial values and region identity.');
