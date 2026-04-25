// Runtime harness for doExportToPhotoshop's PSD-layer composite-fallback
// block (prior-shift W14, reopened this shift for runtime proof).
//
// What W14 fixed: when a painter has PSD layers loaded but no decals, the
// PS-export endpoint was being called with NO paint_image_base64. The
// server-side then synthesized a default paint, silently dropping every
// pixel the painter had painted onto their layers.
//
// Runtime check: extract the doExportToPhotoshop function body, execute it
// with stubbed PSD state in three scenarios:
//   A) PSD layers loaded, no decals     ⇒ paint_image_base64 MUST be set
//                                          (else painter loses their work)
//   B) No PSD layers, decals present    ⇒ paint_image_base64 set by decal block
//                                          (existing behavior, unchanged)
//   C) No PSD layers, no decals         ⇒ paint_image_base64 NOT set (composite
//                                          flows through server default — fine)
//
// We capture the `extras` object that gets sent to the server and assert.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-5-api-render.js'), 'utf8');

function extractAsyncFunction(name) {
    const needle = '\nasync function ' + name + '(';
    const start = SRC.indexOf(needle) + 1;
    if (start === 0) throw new Error('Could not locate async function ' + name);
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') { depth--; if (depth === 0) break; }
    }
    return SRC.slice(start, i + 1);
}

function makeContext({ psdLayersLoaded, psdLayerCount, decalCount }) {
    const captured = {
        sentExtras: null,
    };

    return {
        // global objects the function reaches for
        ShokkerAPI: {
            online: true,
            exportToPhotoshop: async function (carFileName, exchangeFolder, paintFile, zones, extras) {
                captured.sentExtras = JSON.parse(JSON.stringify(extras));
                return { exchange_dir: '/tmp/exchange/test' };
            },
        },
        document: {
            getElementById: function (id) {
                if (id === 'paintCanvas') {
                    return { width: 2048, height: 2048,
                             getContext: () => ({ getImageData: () => ({ data: new Uint8ClampedArray(16) }) }) };
                }
                if (id === 'psExportCarFileName') return { value: 'TEST-CAR-001' };
                if (id === 'psExportExchangeFolder') return { value: '/tmp/exchange' };
                if (id === 'paintFile') return { value: '/tmp/source.png' };
                if (id === 'btnDoExportToPs') return { disabled: false, textContent: '' };
                return null;
            },
        },
        showToast: function () {},
        closeExportToPhotoshopModal: function () {},
        buildServerZonesForRender: function () { return []; },
        canvasToBase64Async: async function (canvas) { return 'data:image/png;base64,FAKE'; },
        compositeDecalsForRender: decalCount > 0
            ? function () { return { width: 2048, height: 2048 }; } : undefined,
        compositeDecalMaskForRender: function () { return null; },
        compositeStampsForRender: undefined,
        decalLayers: Array.from({ length: decalCount }, (_, i) => ({ visible: true, specFinish: 'gloss' })),

        // PSD-layer state — the W14 block keys on these
        _psdLayersLoaded: psdLayersLoaded,
        _psdLayers: Array.from({ length: psdLayerCount }, (_, i) => ({ id: 'L' + i, name: 'Layer ' + i })),
        importedSpecMapPath: null,
        zones: [],
        window: {},
        localStorage: { getItem: () => null, setItem: () => {} },
        PS_EXPORT_FOLDER_KEY: 'spb.exportFolder',
        console: { log: () => {} },

        _captured: captured,
    };
}

async function runOne(label, opts) {
    const ctx = makeContext(opts);
    vm.createContext(ctx);
    const body = extractAsyncFunction('doExportToPhotoshop');
    const wrapper = `(async () => { ${body} ; await doExportToPhotoshop(); })()`;
    let error = null;
    try {
        await vm.runInContext(wrapper, ctx, { filename: 'doExportToPhotoshop.runtime.js', timeout: 5000 });
    } catch (e) {
        error = { message: e.message, stack: e.stack };
    }
    return {
        label,
        ok: error === null,
        error,
        extras_sent: ctx._captured.sentExtras,
        had_paint_image_base64: !!(ctx._captured.sentExtras && ctx._captured.sentExtras.paint_image_base64),
    };
}

const a = await runOne('psd_layers_no_decals', { psdLayersLoaded: true, psdLayerCount: 5, decalCount: 0 });
const b = await runOne('decals_no_psd_layers', { psdLayersLoaded: false, psdLayerCount: 0, decalCount: 2 });
const c = await runOne('no_psd_no_decals', { psdLayersLoaded: false, psdLayerCount: 0, decalCount: 0 });
const d = await runOne('psd_layers_with_decals', { psdLayersLoaded: true, psdLayerCount: 3, decalCount: 1 });

console.log(JSON.stringify({
    psd_layers_no_decals: a,
    decals_no_psd_layers: b,
    no_psd_no_decals: c,
    psd_layers_with_decals: d,
}, null, 2));
