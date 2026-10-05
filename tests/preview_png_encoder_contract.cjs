'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const encoder = require('../js/canvas/preview-png-encoder.js');
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
async function main() {
    const canvas = { width: 2048, height: 2048 };
    let revision = '1:2048x2048', current = true, now = 100, sig = 'pixels', calls = 0;
    let job = deferred();
    const memo = {};
    const options = { memo, revision: () => revision, current: () => current, now: () => now, stamp: () => 7,
        signature: () => sig, encode: () => { calls++; return job.promise; } };
    const pending = encoder.encode(canvas, options);
    assert.equal(calls, 1); assert.deepEqual(memo, {}, 'no early memo publication');
    job.resolve('png-original');
    const first = await pending;
    assert.equal(first.url, 'png-original'); assert.equal(first.sig, 'rev:1:2048x2048:7');
    assert.equal(memo.rev, revision);
    assert.deepEqual(await encoder.encode(canvas, options), first);
    assert.equal(calls, 1, 'unchanged source reuses exact encoded bytes');
    now = 30200; sig = memo.sig;
    assert.deepEqual(await encoder.encode(canvas, options), first);
    assert.equal(calls, 1, 'expired unchanged content re-verifies without encoding');
    now = 61000; sig = 'different'; job = deferred();
    const changed = encoder.encode(canvas, options); job.resolve('png-different');
    assert.deepEqual(await changed, { url: 'png-different', sig: 'different' });
    for (const stale of ['revision', 'request']) {
        const before = { ...memo }; revision += '+next'; job = deferred();
        const late = encoder.encode(canvas, options);
        if (stale === 'revision') revision += '+newer'; else current = false;
        job.resolve('stale-png');
        assert.equal(await late, null); assert.deepEqual(memo, before);
        current = true;
    }
    job = deferred(); const before = { ...memo };
    const failed = encoder.encode(canvas, options); job.reject(Error('codec failure'));
    await assert.rejects(failed, /codec failure/); assert.deepEqual(memo, before);
    assert.equal(await encoder.encode({ width: 0, height: 2048 }, options), null);
    current = false; assert.equal(await encoder.encode(canvas, options), null); current = true;
    // A later request completing first must retain its cache when the old one resolves.
    job = deferred(); const oldJob = job; const old = encoder.encode(canvas, options);
    revision += '+latest'; job = deferred(); const latest = encoder.encode(canvas, options);
    job.resolve('newest-png'); await latest;
    oldJob.resolve('older-png'); assert.equal(await old, null); assert.equal(memo.url, 'newest-png');

    // Actual source attachment uses the supplied immutable PNG/signature even
    // when a different operation has replaced the shared synchronous memo.
    const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
    const a = source.indexOf('        function _attachEncodedPaintSource(');
    const b = source.indexOf('        window._spbAttachEncodedPaintSource', a);
    const context = { _pngMemo: { sig: 'different-shared-memo' }, _previewPaintSourceMemo: { sig: first.sig, token: 'cached-token' },
        _encodedPngForCanvas() { throw Error('synchronous encoder must not run'); } };
    vm.createContext(context); vm.runInContext(source.slice(a, b), context);
    const body = { paint_image_base64: 'old' };
    context._attachEncodedPaintSource(body, canvas, first);
    assert.equal(body.paint_source_token, 'cached-token'); assert.equal(body.paint_source_sig, first.sig);
    assert(!('paint_image_base64' in body));
    context._attachEncodedPaintSource(body, canvas, { url: 'new-png', sig: 'new-sig' });
    assert.equal(body.paint_image_base64, 'new-png'); assert.equal(body.paint_source_sig, 'new-sig');
    assert(!('paint_source_token' in body));
    const preview = source.slice(source.indexOf('        async function doPreviewRender('), source.indexOf("                const previewSignal =", source.indexOf('        async function doPreviewRender(')));
    assert(preview.includes('await window.SPBPreviewPngEncoder.encode('));
    assert(preview.includes('paintRevision === (window._spbLayerRev | 0)'));
    assert(preview.includes('sourceGeneration === _spbSourceLoadGeneration'));
    assert(!preview.includes('_attachLivePaintCanvasToPreviewBody(body, paintFile)'));
    assert(!preview.includes('_attachEncodedPaintSource(body, compositeCanvas)'));
    console.log('Async PNG: exact memo/token reuse, expiry verification, delayed completion, source/request races, failures, immutable attachment and async preview wiring pass.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
