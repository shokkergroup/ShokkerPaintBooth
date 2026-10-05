'use strict';
const assert = require('assert');
const api = require('../js/canvas/layer/paint-commit-bounds.js');
function reference(active, original, ox, oy, alpha) {
    let changed = !original, minX = active.width, minY = active.height, maxX = 0, maxY = 0;
    for (let y = 0; y < active.height; y++) for (let x = 0; x < active.width; x++) {
        const i = (y * active.width + x) * 4;
        if (alpha) active.data[i + 3] = alpha[y * active.width + x];
        if (active.data[i + 3]) { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); }
        if (original) for (let c = 0; c < 4; c++) {
            const sx = x - ox, sy = y - oy;
            const expected = sx >= 0 && sy >= 0 && sx < original.width && sy < original.height
                ? original.data[(sy * original.width + sx) * 4 + c] : 0;
            if (active.data[i + c] !== expected) changed = true;
        }
    }
    return { pixelsChanged: changed, minX, minY, maxX, maxY };
}
let seed = 17429;
function random(n) { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed % n; }
function image(w, h, offset = 0) { return { width: w, height: h, data: new Uint8ClampedArray(new ArrayBuffer(w * h * 4 + offset), offset, w * h * 4) }; }
for (let n = 0; n < 1500; n++) {
    const active = image(1 + random(35), 1 + random(37), n % 3);
    const original = n % 19 ? image(1 + random(40), 1 + random(42), (n + 1) % 3) : null;
    const ox = random(70) - 35, oy = random(70) - 35;
    if (original) {
        for (let i = 0; i < original.data.length; i++) original.data[i] = random(256);
        for (let y = 0; y < active.height; y++) for (let x = 0; x < active.width; x++) {
            const sx = x - ox, sy = y - oy;
            if (sx >= 0 && sy >= 0 && sx < original.width && sy < original.height) {
                for (let c = 0; c < 4; c++) active.data[(y * active.width + x) * 4 + c] = original.data[(sy * original.width + sx) * 4 + c];
            }
        }
    }
    if (n % 2) for (let i = 0; i < 8; i++) active.data[random(active.data.length)] = random(256);
    const alpha = n % 4 === 0 ? Uint8Array.from({ length: active.width * active.height }, () => random(256)) : null;
    const clone = { ...active, data: active.data.slice() };
    const oldOriginal = original && original.data.slice();
    const expected = reference(clone, original, ox, oy, alpha);
    assert.deepEqual(api.analyze(active, original, ox, oy, alpha), expected, 'case ' + n);
    assert.deepEqual(active.data, clone.data, 'alpha restoration ' + n);
    if (original) assert.deepEqual(original.data, oldOriginal, 'immutable original ' + n);
}
// Transparent hidden RGB still makes an edit; alpha bounds stay empty.
const empty = image(4, 4), hidden = image(4, 4); hidden.data[4] = 1;
assert.equal(api.analyze(hidden, empty, 0, 0, null).pixelsChanged, true);
assert.equal(api.analyze(empty, empty, 0, 0, null).pixelsChanged, false);
// Long transparent runs (including nonzero hidden RGB), eight-word tails,
// sparse alpha islands and a final-word edit exercise the block fast paths.
for (const width of [8, 9, 15, 16, 17, 129]) {
    const original = image(width, 67);
    for (let i=0;i<original.data.length;i+=4) original.data[i]=77;
    original.data[(30*width+Math.floor(width/2))*4+3]=1;
    const active={...original,data:original.data.slice()};
    assert.deepEqual(api.analyze(active,original,0,0,null),reference(active,original,0,0,null));
    active.data[active.data.length-2]=99;
    assert.deepEqual(api.analyze(active,original,0,0,null),reference(active,original,0,0,null));
}
console.log('Layer commit scan: 1500 offset/unaligned/soft-alpha/no-op cases match per-pixel reference; hidden RGB and immutable originals preserved.');
