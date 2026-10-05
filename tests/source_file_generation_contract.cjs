'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const names = ['browsePaintFile', 'loadPaintImage', 'loadPaintImageFromFile', 'loadPaintImageFromFileAsync', 'loadPaintImageFromPath'];
const generation = source.slice(source.indexOf('var _spbSourceLoadGeneration = 0;'), source.indexOf('async function _spbFingerprintBytes('));
function harness() {
    const readers = [], images = [], commits = [], toasts = [], fetches = [];
    const element = { style: {}, value: '' };
    const context = {
        window: {}, document: { getElementById() { return element; } },
        console: { error() {} },
        validatePaintPath() {}, setupCanvasHandlers() {}, canvasZoom() {}, setTimeout() {}, splitViewActive: true,
        showToast(message) { toasts.push(message); }, markFlatPaintLiveSource() {}, clearFlatPaintLiveSource() {},
        _spbCommitSourceFile(w, h, draw) { draw({ drawImage(image) { commits.push(image.tag); } }); },
        loadDecodedImageToCanvas(w, h, rgba) { commits.push(rgba); },
        decodeTGA(bytes) { return { width: 4, height: 4, rgba: bytes.tag }; },
        FileReader: class {
            readAsDataURL(file) { this.file = file; readers.push(this); }
            readAsArrayBuffer(file) { this.file = file; readers.push(this); }
        },
        Image: class { constructor() { this.width = 4; this.height = 4; } set src(tag) { this.tag = tag; images.push(this); } },
        File: class { constructor(parts, name) { this.name = name; } },
        fetch() { return new Promise(resolve => fetches.push(resolve)); }
    };
    vm.createContext(context);
    vm.runInContext(generation + names.map(name => {
        const a = source.indexOf('        function ' + name + '(');
        return source.slice(a, source.indexOf('\n        function ', a + 20));
    }).join('\n'), context);
    function read(reader) {
        reader.onload({ target: { result: reader.file.name.endsWith('.tga') ? { tag: reader.file.name } : reader.file.name } });
    }
    function start(name, fileName) {
        const file = { name: fileName };
        const arg = ['browsePaintFile', 'loadPaintImage'].includes(name) ? { files: [file] } : file;
        return Promise.resolve(context[name](arg)).then(() => ({ ok: true }), error => ({ ok: false, error }));
    }
    return { context, readers, images, commits, toasts, fetches, read, start };
}
async function main() {
    let cases = 0;
    for (const name of names.slice(0, 4)) {
        for (const extension of ['png', 'tga']) {
            const h = harness();
            const older = h.start(name, 'older.' + extension), oldReader = h.readers[0];
            const newer = h.start(name, 'newer.' + extension), newReader = h.readers[1];
            h.read(newReader);
            if (extension === 'png') h.images.at(-1).onload();
            assert((await newer).ok);
            h.read(oldReader);
            const oldResult = await older;
            if (name.endsWith('Async')) assert.match(oldResult.error.message, /superseded/);
            assert.deepEqual(h.commits, ['newer.' + extension]);
            cases++;
        }
        for (const failure of [false, true]) {
            const h = harness(), old = h.start(name, 'older.png');
            h.read(h.readers[0]);
            // Newer normal/PSD loads use this exact shared authority.
            h.context._spbBeginSourceLoad('newer.psd', 'layered');
            h.toasts.length = 0;
            if (failure && h.images[0].onerror) h.images[0].onerror();
            else h.images[0].onload();
            await old;
            assert.deepEqual(h.commits, []);
            assert.deepEqual(h.toasts, []);
            cases++;
        }
        const h = harness();
        const previous = h.context._spbBeginSourceLoad('older.psd', 'layered');
        const latest = h.start(name, 'newer.tga');
        assert(!h.context._spbIsCurrentSourceLoad(previous));
        h.read(h.readers[0]);
        await latest;
        assert.deepEqual(h.commits, ['newer.tga']);
        cases++;
    }
    const h = harness();
    const urlResult = h.context.loadPaintImageFromPath('/old/paint.png').then(() => null, e => e);
    const latest = h.start('loadPaintImageFromFileAsync', 'newer.tga');
    h.read(h.readers[0]); await latest;
    h.toasts.length = 0;
    h.fetches[0]({ ok: true, blob: async () => ({ type: 'image/png' }) });
    assert.match((await urlResult).message, /superseded/);
    assert.equal(h.readers.length, 1, 'stale URL cannot start another file generation');
    assert.deepEqual(h.commits, ['newer.tga']);
    assert.deepEqual(h.toasts, []);
    const valid = harness();
    const oldFile = valid.start('loadPaintImageFromFileAsync', 'older.tga');
    const newUrl = valid.context.loadPaintImageFromPath('/new/paint.tga');
    valid.read(valid.readers[0]);
    assert.match((await oldFile).error.message, /superseded/);
    valid.fetches[0]({ ok: true, blob: async () => ({ type: 'image/tga' }) });
    for (let tick = 0; tick < 8 && valid.readers.length < 2; tick++) await Promise.resolve();
    assert.equal(valid.readers.length, 2);
    valid.read(valid.readers[1]);
    assert.equal((await newUrl).width, 4);
    assert.deepEqual(valid.commits, ['paint.tga']);
    assert(valid.context._spbIsCurrentSourceLoad({ generation: 2 }), 'URL passes its original generation through file decode');
    console.log(`Source generations: ${cases + 2} delayed-reader/image, late-error, cross-format and URL handoff cases preserve the newer source.`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
