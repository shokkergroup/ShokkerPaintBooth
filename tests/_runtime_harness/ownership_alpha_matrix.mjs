import fs from 'node:fs';
import vm from 'node:vm';


const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const start = source.indexOf('function getLayerVisibleContributionMask(');
const end = source.indexOf(
    "if (typeof window !== 'undefined') window.getLayerVisibleContributionMask",
    start,
);
if (start < 0 || end < 0) {
    throw new Error('Could not extract getLayerVisibleContributionMask from the live canvas source');
}
const ownershipFunction = source.slice(start, end);

const context = vm.createContext({ console });
vm.runInContext(`
class AlphaCanvas {
    constructor() { this.width = 0; this.height = 0; this._ctx = null; }
    getContext() {
        if (!this._ctx) this._ctx = new AlphaContext(this);
        return this._ctx;
    }
}

class AlphaContext {
    constructor(canvas) {
        this.canvas = canvas;
        this.alpha = new Float64Array(canvas.width * canvas.height);
        this.globalAlpha = 1;
        this.globalCompositeOperation = 'source-over';
    }
    sourceOver(sourceAlpha) {
        for (let i = 0; i < this.alpha.length; i++) {
            const src = Math.max(0, Math.min(1, Number(sourceAlpha[i]) || 0));
            this.alpha[i] = src + this.alpha[i] * (1 - src);
        }
    }
    getImageData() {
        const data = new Uint8ClampedArray(this.alpha.length * 4);
        for (let i = 0; i < this.alpha.length; i++) {
            data[i * 4 + 3] = Math.round(this.alpha[i] * 255);
        }
        return { data };
    }
}

const document = { createElement: () => new AlphaCanvas() };
let _psdLayers = [];
let _psdLayersLoaded = true;
let _layerVisibleContributionCache = new Map();
let _layerCompositeRevision = 1;
const _layerAtIndexCanComposite = () => true;
const renderLayerEffects = () => {};
const _spbReportGroupFidelityFailure = () => {};
const _drawLayerPixelContent = function (ctx, layers, layerIndex) {
    const layer = layers[layerIndex];
    const opacity = Math.max(0, Math.min(1, Number(layer.opacity == null ? 255 : layer.opacity) / 255));
    ctx.sourceOver(layer.img.alpha.map(value => (Number(value) / 255) * opacity));
    return true;
};
const _spbCompositeLayerStack = function (ctx, layers, options = {}) {
    let drawn = 0;
    for (let index = 0; index < layers.length; index++) {
        const item = layers[index];
        if (!item || item.visible === false || !item.img) continue;
        if (options.includeLayer && !options.includeLayer(item, index)) continue;
        if (!_layerAtIndexCanComposite(layers, index)) continue;
        if ((options.drawLayer || _drawLayerPixelContent)(ctx, item, index)) drawn += 1;
    }
    return { ok: true, drawn };
};

${ownershipFunction}

function layer(id, alpha, opacity = 255) {
    return { id, name: id, visible: true, opacity, img: { alpha } };
}

function masksFor(layers) {
    _psdLayers = layers;
    _layerCompositeRevision += 1;
    _layerVisibleContributionCache.clear();
    return Object.fromEntries(layers.map(item => [
        item.id,
        Array.from(getLayerVisibleContributionMask(item, item.img.alpha.length, 1)),
    ]));
}

globalThis.result = {
    alphaBoundary: masksFor([layer('boundary', [127, 128])]),
    grillMesh: masksFor([layer('mesh', [153, 51])]),
    stackedThirty: masksFor([
        layer('base', [255]),
        layer('lower30', [255], 77),
        layer('top30', [255], 77),
    ]),
};
`, context, { filename: 'ownership_alpha_matrix.runtime.js', timeout: 2000 });

process.stdout.write(JSON.stringify(context.result));
