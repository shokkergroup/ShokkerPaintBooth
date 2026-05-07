import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-3-canvas.js'), 'utf8');

function extractFunction(name) {
    const needle = '\nfunction ' + name + '(';
    const start = SRC.indexOf(needle) + 1;
    if (start === 0) throw new Error('Could not locate function ' + name);
    let i = SRC.indexOf('{', start);
    let depth = 0;
    for (; i < SRC.length; i++) {
        const ch = SRC[i];
        if (ch === '{') depth++;
        else if (ch === '}') {
            depth--;
            if (depth === 0) break;
        }
    }
    return SRC.slice(start, i + 1);
}

function buildContext(target) {
    const W = 2048;
    const H = 2048;
    const calls = {
        pushZoneUndo: [],
        renderZones: 0,
        triggerPreviewRender: 0,
        renderContextActionBar: 0,
        drawTransformHandles: 0,
        showToast: [],
    };
    const zone = {
        base: 'gradient_test',
        pattern: 'pattern_test',
        baseOffsetX: 0.5,
        baseOffsetY: 0.5,
        baseScale: 1,
        baseRotation: 0,
        patternOffsetX: 0.5,
        patternOffsetY: 0.5,
        scale: 1,
        rotation: 0,
        secondBase: 'overlay_test',
        secondBasePatternOffsetX: 0.5,
        secondBasePatternOffsetY: 0.5,
        secondBasePatternScale: 1,
        secondBasePatternRotation: 0,
        specPatternStack: [{
            id: 'sparkle_test',
            offsetX: 0.5,
            offsetY: 0.5,
            scale: 1,
            rotation: 0,
        }],
    };
    const paintCanvas = { width: W, height: H, style: { width: '512px', height: '512px' } };
    const transformCanvas = { width: 0, height: 0, style: {} };
    const ctx = {
        window: {},
        zones: [zone],
        selectedZoneIndex: 0,
        selectedDecalIndex: -1,
        decalLayers: [],
        placementLayer: target,
        freeTransformState: null,
        _selectedLayerId: null,
        _psdLayersLoaded: false,
        document: {
            getElementById(id) {
                if (id === 'paintCanvas') return paintCanvas;
                if (id === 'transformCanvas') return transformCanvas;
                return null;
            },
        },
        showToast(msg, type) { calls.showToast.push([msg, type]); },
        pushZoneUndo(label) { calls.pushZoneUndo.push(label); },
        renderZones() { calls.renderZones++; },
        triggerPreviewRender() { calls.triggerPreviewRender++; },
        renderContextActionBar() { calls.renderContextActionBar++; },
        drawTransformHandles() { calls.drawTransformHandles++; },
        _hideLayerTransformQuickbar() {},
        _hideTransformCanvas() {},
        _getActiveSelectionInfo() { return null; },
        getSelectedEditableLayer() { return null; },
        activateLayerTransform() { throw new Error('layer transform should not run'); },
        transformSelectedLayerRegion() { throw new Error('selection transform should not run'); },
        commitLayerTransform() { throw new Error('layer commit should not run'); },
        cancelLayerTransform() { throw new Error('layer cancel should not run'); },
        console,
        _calls: calls,
        _zone: zone,
    };
    ctx.window = ctx;
    return ctx;
}

const script = [
    'var freeTransformState = null;',
    extractFunction('_isZoneFreeTransformTarget'),
    extractFunction('_getZoneFreeTransformTargetState'),
    extractFunction('_setZoneFreeTransformTargetState'),
    extractFunction('_zoneTransformTargetLabel'),
    extractFunction('activateFreeTransform'),
    extractFunction('deactivateFreeTransform'),
    extractFunction('requestContextTransform'),
].join('\n');

function readTarget(zone, target) {
    if (target === 'base') {
        return {
            offsetX: zone.baseOffsetX,
            offsetY: zone.baseOffsetY,
            scale: zone.baseScale,
            rotation: zone.baseRotation,
        };
    }
    if (target === 'pattern') {
        return {
            offsetX: zone.patternOffsetX,
            offsetY: zone.patternOffsetY,
            scale: zone.scale,
            rotation: zone.rotation,
        };
    }
    if (target === 'second_base') {
        return {
            offsetX: zone.secondBasePatternOffsetX,
            offsetY: zone.secondBasePatternOffsetY,
            scale: zone.secondBasePatternScale,
            rotation: zone.secondBasePatternRotation,
        };
    }
    if (target === 'spec_pattern_0') {
        return {
            offsetX: zone.specPatternStack[0].offsetX,
            offsetY: zone.specPatternStack[0].offsetY,
            scale: zone.specPatternStack[0].scale,
            rotation: zone.specPatternStack[0].rotation,
        };
    }
    throw new Error('Unknown target ' + target);
}

function exercise(target) {
    const ctx = buildContext(target);
    vm.createContext(ctx);
    vm.runInContext(script, ctx, { filename: 'zone_transform_targets.runtime.js', timeout: 2000 });
    const activated = vm.runInContext("requestContextTransform('auto')", ctx, { timeout: 2000 });
    if (!activated) throw new Error('Failed to activate ' + target);
    vm.runInContext(`
        freeTransformState.centerX = 512;
        freeTransformState.centerY = 1536;
        freeTransformState.boxW = 860;
        freeTransformState.rotation = 90;
        deactivateFreeTransform(true);
    `, ctx, { timeout: 2000 });
    return {
        target,
        state: readTarget(ctx._zone, target),
        undo: ctx._calls.pushZoneUndo.length,
        renderZones: ctx._calls.renderZones,
        preview: ctx._calls.triggerPreviewRender,
        drawTransformHandles: ctx._calls.drawTransformHandles,
    };
}

const results = {};
for (const target of ['base', 'pattern', 'second_base', 'spec_pattern_0']) {
    results[target] = exercise(target);
}
console.log(JSON.stringify(results, null, 2));
