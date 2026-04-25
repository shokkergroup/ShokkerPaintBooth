import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const STATE_SRC = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

function sliceBetween(src, startMarker, endMarker) {
    const s = src.indexOf(startMarker);
    if (s === -1) throw new Error('start marker not found: ' + startMarker);
    const e = src.indexOf(endMarker, s);
    if (e === -1) throw new Error('end marker not found: ' + endMarker);
    return src.slice(s, e);
}

const guardBlock = sliceBetween(
    STATE_SRC,
    'function _hasAnyMaskPixels',
    'let undoActiveDragTimer'
);

const warnings = [];
const ctx = {
    console: { warn: (...args) => warnings.push(args.join(' ')) },
    window: {},
    Uint8Array,
    Array,
    RegExp,
    String,
};
vm.createContext(ctx);
vm.runInContext(guardBlock, ctx, { filename: 'zone9_guard.runtime.js' });

function filler(n) {
    return Array.from({ length: n }, (_, i) => ({
        name: `Zone ${i + 1}`,
        base: null,
        pattern: 'none',
        finish: null,
        color: null,
        colorMode: 'none',
    }));
}

const results = {};

const zombieZones = filler(8).concat([{
    name: 'Open Zone 9',
    color: 'dark',
    colorMode: 'quick',
    base: 'matte',
    pattern: 'carbon_fiber',
    finish: null,
    regionMask: null,
    spatialMask: null,
    patternStack: [],
    specPatternStack: [],
}]);
results.zombie_fixed_count = ctx._sanitizeZonesInPlace(zombieZones, 'harness');
results.zombie_after = {
    base: zombieZones[8].base,
    pattern: zombieZones[8].pattern,
    finish: zombieZones[8].finish,
    color: zombieZones[8].color,
    colorMode: zombieZones[8].colorMode,
};

const maskedZones = filler(8).concat([{
    name: 'Open Zone 9',
    color: 'dark',
    colorMode: 'quick',
    base: 'matte',
    pattern: 'carbon_fiber',
    finish: null,
    regionMask: new Uint8Array([0, 1, 0]),
    spatialMask: null,
}]);
results.authored_mask_fixed_count = ctx._sanitizeZonesInPlace(maskedZones, 'harness');
results.authored_mask_after = {
    base: maskedZones[8].base,
    pattern: maskedZones[8].pattern,
};

const layerScopedZones = filler(8).concat([{
    name: 'Open Zone 9',
    color: 'white',
    colorMode: 'quick',
    base: 'matte',
    pattern: 'carbon_fiber',
    finish: null,
    sourceLayer: 'White Base',
    regionMask: null,
    spatialMask: null,
}]);
results.authored_source_layer_fixed_count = ctx._sanitizeZonesInPlace(layerScopedZones, 'harness');
results.authored_source_layer_after = {
    base: layerScopedZones[8].base,
    pattern: layerScopedZones[8].pattern,
    sourceLayer: layerScopedZones[8].sourceLayer,
};

const nonZone9 = [{
    name: 'Carbon Accent',
    color: 'dark',
    colorMode: 'quick',
    base: 'matte',
    pattern: 'carbon_fiber',
    finish: null,
}];
results.non_zone9_fixed_count = ctx._sanitizeZonesInPlace(nonZone9, 'harness');
results.non_zone9_after = {
    base: nonZone9[0].base,
    pattern: nonZone9[0].pattern,
};

results.warning_count = warnings.length;

console.log(JSON.stringify(results, null, 2));
