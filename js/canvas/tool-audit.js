/* SPB-93 2026-09-07: opt-in, localhost-only pixel and interaction evidence.
   No paint/history mutations, network requests, or arbitrary execution hooks.
   Open the app with ?spb-tool-audit=1. Normal sessions install no listeners. */
(function (root) {
    'use strict';
    function difference(before, after) {
        if (!before || before.width !== after.width || before.height !== after.height) return { dimensionsChanged: true };
        let changedPixels = 0, alphaChanged = 0, maxDelta = 0;
        let left = after.width, top = after.height, right = -1, bottom = -1;
        for (let i = 0; i < after.data.length; i += 4) {
            let changed = false;
            for (let c = 0; c < 4; c++) {
                const d = Math.abs(before.data[i + c] - after.data[i + c]);
                if (d) changed = true;
                if (d > maxDelta) maxDelta = d;
            }
            if (before.data[i + 3] !== after.data[i + 3]) alphaChanged++;
            if (changed) {
                changedPixels++;
                const x = (i / 4) % after.width, y = Math.floor(i / 4 / after.width);
                left = Math.min(left, x); right = Math.max(right, x);
                top = Math.min(top, y); bottom = Math.max(bottom, y);
            }
        }
        return { changedPixels, alphaChanged, maxDelta, bounds: changedPixels ? [left, top, right, bottom] : null };
    }
    function maskDifference(before, after, width, height) {
        let changedPixels = 0, selectedPixels = 0, minValue = Infinity, maxValue = 0;
        let left = width, top = height, right = -1, bottom = -1;
        const values = new Set();
        for (let i = 0; i < width * height; i++) {
            const a = before?.[i] || 0, b = after?.[i] || 0;
            if (a !== b) changedPixels++;
            if (!b) continue;
            selectedPixels++; values.add(b); minValue = Math.min(minValue, b); maxValue = Math.max(maxValue, b);
            const x = i % width, y = Math.floor(i / width);
            left = Math.min(left, x); right = Math.max(right, x);
            top = Math.min(top, y); bottom = Math.max(bottom, y);
        }
        return { changedPixels, selectedPixels, minValue: selectedPixels ? minValue : 0, maxValue,
            distinctNonzeroValues: values.size, bounds: selectedPixels ? [left, top, right, bottom] : null };
    }
    if (typeof module === 'object' && module.exports) module.exports = { difference, maskDifference };
    if (!root.document || !['localhost', '127.0.0.1', '[::1]'].includes(root.location.hostname)
        || new URLSearchParams(root.location.search).get('spb-tool-audit') !== '1') return;

    function mount() {
        const panel = document.createElement('details');
        panel.id = 'spbToolAudit';
        panel.style.cssText = 'position:fixed;left:8px;bottom:8px;width:350px;max-height:38vh;overflow:auto;z-index:60000;background:#101923;color:#edf5ff;border:1px solid #54829c;border-radius:8px;padding:8px;font:12px system-ui';
        panel.innerHTML = '<summary>Local tool audit</summary><p>Read-only pixel comparisons. Baseline and comparison are outside gesture timing.</p>' +
            '<button id="spbAuditBaseline">Set baseline</button> <button id="spbAuditCompare">Compare pixels</button> ' +
            '<button id="spbAuditTiming">Show timing</button> <button id="spbAuditPng">Check PNG encoding</button> <button id="spbAuditBrushPreview">Check brush preview</button><pre id="spbAuditResult" style="white-space:pre-wrap">Ready</pre>';
        document.body.appendChild(panel);
        const result = document.getElementById('spbAuditResult');
        const parityButton = document.createElement('button');
        parityButton.textContent = 'Check source parity';
        panel.insertBefore(parityButton, result);
        const pickButton = document.createElement('button');
        pickButton.textContent = 'Inspect last object hit';
        panel.insertBefore(pickButton, result);
        pickButton.onclick = () => {
            const g = gesture, c = g?.canvasAtDown;
            if (!c) { result.textContent = 'Click Source first.'; return; }
            const x = Math.floor((g.down[0] - c.x) * c.pixels[0] / c.width);
            const y = Math.floor((g.down[1] - c.y) * c.pixels[1] / c.height);
            result.textContent = JSON.stringify({point:[x,y],layers:_psdLayers.map(layer => {
                const data = _getLayerAlphaImageData(layer), origin = getLayerCanvasOrigin(layer);
                const lx=x-origin.x, ly=y-origin.y;
                return {id:layer.id,name:layer.name,bbox:layer.bbox,visible:layer.visible,
                    opacity:layer.opacity,locked:layer.locked,baseLike:_isBaseLikeLayer(layer),
                    alpha:data?.data[(ly*data.width+lx)*4+3]??null};
            })},null,2);
        };
        parityButton.onclick = () => {
            try {
                const source = document.getElementById('paintCanvas'), ctx = source.getContext('2d');
                const exported = root.buildLivePaintCompositeCanvas();
                const read = c => c.getContext('2d').getImageData(0, 0, c.width, c.height);
                const sourceData = read(source), exportData = read(exported);
                const cases = [];
                for (const attributes of [{ willReadFrequently: true }, ctx.getContextAttributes()]) {
                    const scratch = document.createElement('canvas');
                    scratch.width = source.width; scratch.height = source.height;
                    const target = scratch.getContext('2d', attributes);
                    const composed = root._spbCompositeLayerStack(target, root._psdLayers);
                    const pixels = read(scratch);
                    cases.push({ attributes: target.getContextAttributes(), composed,
                        source: difference(sourceData, pixels), export: difference(exportData, pixels) });
                }
                result.textContent = JSON.stringify({ sourceParity: {
                    sourceToExport: difference(sourceData, exportData),
                    state: { alpha: ctx.globalAlpha, blend: ctx.globalCompositeOperation, filter: ctx.filter,
                        smoothing: ctx.imageSmoothingEnabled, quality: ctx.imageSmoothingQuality,
                        transform: Array.from(ctx.getTransform().toFloat64Array()) }, cases
                } }, null, 2);
            } catch (error) { result.textContent = String(error); }
        };
        // SPB-93: compare the production async encoder with the same immutable
        // full-resolution canvas and the old PNG path; never mutate live paint.
        document.getElementById('spbAuditPng').onclick = async () => {
            result.textContent = 'Checking full-resolution PNG pixels…';
            try {
                const source = root.buildLivePaintCompositeCanvas?.() || document.getElementById('paintCanvas');
                const snapshot = document.createElement('canvas');
                snapshot.width = source.width; snapshot.height = source.height;
                const context = snapshot.getContext('2d', { willReadFrequently: true });
                context.drawImage(source, 0, 0);
                const original = context.getImageData(0, 0, snapshot.width, snapshot.height);
                const decode = url => new Promise((resolve, reject) => {
                    const img = new Image();
                    img.onerror = reject;
                    img.onload = () => {
                        const canvas = document.createElement('canvas');
                        canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
                        const ctx = canvas.getContext('2d', { willReadFrequently: true });
                        ctx.drawImage(img, 0, 0);
                        resolve(ctx.getImageData(0, 0, canvas.width, canvas.height));
                    };
                    img.src = url;
                });
                const start = performance.now();
                const encoded = await root.SPBPreviewPngEncoder.encode(snapshot, {
                    memo: {}, revision: () => 'audit', current: () => true,
                    now: () => performance.now(), stamp: () => Date.now(),
                    signature: () => 'audit', encode: canvas => root.canvasToBase64Async(canvas, 'image/png')
                });
                const asyncWallMs = performance.now() - start;
                const syncStart = performance.now(), syncUrl = snapshot.toDataURL('image/png');
                const syncBlockingMs = performance.now() - syncStart;
                const [asyncPixels, syncPixels] = await Promise.all([decode(encoded.url), decode(syncUrl)]);
                result.textContent = JSON.stringify({ pngEncoding: {
                    dimensions: [snapshot.width, snapshot.height], asyncWallMs, syncBlockingMs,
                    sourceToAsync: difference(original, asyncPixels), syncToAsync: difference(syncPixels, asyncPixels)
                } }, null, 2);
            } catch (error) { result.textContent = 'PNG audit failed: ' + String(error); }
        };
        document.getElementById('spbAuditBrushPreview').onclick = () => {
            stopTiming();
            try {
                const selected = getSelectedLayer(), pc = document.getElementById('paintCanvas');
                if (!selected?.img || typeof _psdLayers === 'undefined') throw new Error('Select a loaded Layer first');
                const rect = { x: Math.floor(pc.width / 3), y: Math.floor(pc.height / 3), width: 203, height: 183 };
                const cases = [];
                for (const blendMode of ['source-over', 'multiply', 'screen']) {
                    const canvases = [];
                    const make = () => {
                        const c = document.createElement('canvas'); c.width = pc.width; c.height = pc.height;
                        canvases.push(c); return c;
                    };
                    const source = make(), local = make(), reference = make();
                    const ctx = c => c.getContext('2d', { willReadFrequently: true });
                    ctx(source).drawImage(selected.img, selected.bbox?.[0] || 0, selected.bbox?.[1] || 0);
                    const layers = _psdLayers.map(layer => layer.id === selected.id ? { ...layer, blendMode } : layer);
                    const draw = target => root._spbCompositeLayerStack(target, layers, {
                        sourceOverrideFor: layer => layer.id === selected.id ? source : null
                    });
                    root.SPBPaintPreviewRegion.paint(ctx(local), null, () => draw(ctx(local)));
                    ctx(source).clearRect(rect.x, rect.y, rect.width, rect.height);
                    ctx(source).fillStyle = 'rgba(83,197,121,0.5)';
                    ctx(source).fillRect(rect.x, rect.y, rect.width, rect.height);
                    const localStart = performance.now();
                    const localResult = root.SPBPaintPreviewRegion.paint(ctx(local), rect, () => draw(ctx(local)));
                    const clippedMs = performance.now() - localStart;
                    const fullStart = performance.now();
                    const fullResult = root.SPBPaintPreviewRegion.paint(ctx(reference), null, () => draw(ctx(reference)));
                    const fullMs = performance.now() - fullStart;
                    cases.push({ blendMode, clippedMs, fullMs, ok: localResult.ok && fullResult.ok,
                        pixels: difference(ctx(local).getImageData(0, 0, pc.width, pc.height),
                            ctx(reference).getImageData(0, 0, pc.width, pc.height)) });
                    for (const canvas of canvases) { canvas.width = 0; canvas.height = 0; }
                }
                result.textContent = JSON.stringify({ brushPreview: { dimensions: [pc.width, pc.height], rect, cases } }, null, 2);
            } catch (error) { result.textContent = 'Brush preview audit failed: ' + String(error); }
        };
        let baseline = null, gesture = null, frame = 0;
        const canvasGeometry = () => {
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return null;
            const r = canvas.getBoundingClientRect();
            return { x: r.x, y: r.y, width: r.width, height: r.height, pixels: [canvas.width, canvas.height] };
        };
        // Fixed instrumentation list; all durations are inclusive. Wrappers
        // preserve arguments/results and are installed only in this audit UI.
        const measured = [];
        const targets = ['_initLayerPaintCanvas', '_commitLayerPaint', '_pushLayerUndo',
            'recompositeFromLayers', '_spbCompositeLayerStack', 'renderLayerPanel', 'triggerPreviewRender',
            'commitRectSelection', 'autoActivateZoneApplyArea', 'updateRegionStatus',
            'renderZones', 'renderZoneDetail', 'renderContextActionBar',
            'renderZoneQuickView', 'getZoneStatus', 'getZoneDiagnostic', '_sanitizeZonesInPlace',
            'autoSave', 'getConfig', 'updateOnboardingHints', 'updateAutoSaveBadge',
            'buildServerZonesForRender', 'encodeRegionMaskRLE', 'buildLivePaintCompositeCanvas', '_paintDodgeBurn',
            '_paintOnLayerAt', '_beginLayerDabSelectionPatch', '_finishLayerDabSelectionPatch',
            '_refreshActiveLayerCompositePreviewNow', '_drawLayerSpecialStamp'].map(name => ({ owner: root, key: name, name }));
        if (root.SPBMaskStats) for (const key of ['count', 'any', 'bounds', 'fingerprint', 'sum']) {
            targets.push({ owner: root.SPBMaskStats, key, name: 'mask.' + key });
        }
        for (const { owner, key, name } of targets) {
            const original = owner[key];
            if (typeof original !== 'function') continue;
            measured.push(name);
            owner[key] = function () {
                if (!gesture || gesture.stopped) return original.apply(this, arguments);
                const current = gesture, start = performance.now();
                // SPB-93: bounded actual dab coordinates distinguish native input,
                // smoothing and painted footprint from canvas/CUA assumptions.
                if (name === '_paintDodgeBurn') {
                    current.retouchDabs ||= [];
                    if (current.retouchDabs.length < 256) current.retouchDabs.push([arguments[0], arguments[1], arguments[2]]);
                    else current.retouchDabsTruncated = true;
                }
                try { return original.apply(this, arguments); }
                finally {
                    const elapsed = performance.now() - start;
                    const record = current.calls[name] || (current.calls[name] = { count: 0, totalMs: 0, maxMs: 0 });
                    record.count++; record.totalMs += elapsed; record.maxMs = Math.max(record.maxMs, elapsed);
                    if (record.firstStartMs === undefined) record.firstStartMs = start - current.start;
                    record.lastStartMs = start - current.start;
                    record.beforeReleaseCount = (record.beforeReleaseCount || 0) + (!current.release ? 1 : 0);
                }
            };
        }
        // A fixed private callback reports timing through this read-only bridge.
        root.spbAuditRecordOverlayDuration = function (elapsed) {
            if (!gesture || gesture.stopped) return;
            const record = gesture.calls._doRenderRegionOverlay || (gesture.calls._doRenderRegionOverlay = { count: 0, totalMs: 0, maxMs: 0 });
            record.count++; record.totalMs += elapsed; record.maxMs = Math.max(record.maxMs, elapsed);
        };
        root.spbAuditRecordRectStage = function (stage, elapsed) {
            if (!gesture || gesture.stopped || !['compose', 'history', 'activate'].includes(stage)) return;
            const key = 'rect.' + stage;
            const record = gesture.calls[key] || (gesture.calls[key] = { count: 0, totalMs: 0, maxMs: 0 });
            record.count++; record.totalMs += elapsed; record.maxMs = Math.max(record.maxMs, elapsed);
        };
        const publish = value => { result.textContent = JSON.stringify(value, null, 2); };
        root.spbAuditStartPaintCommit = () => {
            if (!gesture || gesture.stopped) return null;
            const current = gesture;
            let start = performance.now();
            return stage => {
                const end = performance.now();
                if (['active-read', 'original-read', 'analyze'].includes(stage)) {
                    const key = 'commit.' + stage;
                    const record = current.calls[key] || (current.calls[key] = { count: 0, totalMs: 0, maxMs: 0 });
                    const elapsed = end - start;
                    record.count++; record.totalMs += elapsed; record.maxMs = Math.max(record.maxMs, elapsed);
                }
                start = end;
            };
        };
        const capture = () => {
            const paint = document.getElementById('paintCanvas');
            const exported = typeof root.buildLivePaintCompositeCanvas === 'function' ? root.buildLivePaintCompositeCanvas() : paint;
            if (!paint?.width || !exported?.width) throw new Error('Load a document first.');
            const read = c => c.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, c.width, c.height);
            const zoneIndex = typeof selectedZoneIndex === 'number' ? selectedZoneIndex : -1;
            const zone = typeof zones !== 'undefined' ? zones[zoneIndex] : null;
            const material = Object.fromEntries(['sourceLayer', 'sourceLayers', 'base', 'baseStrength', 'baseSpecStrength', 'baseColorMode',
                'pattern', 'finish', 'useRegion', 'specMaterialOverride', 'specMaterialRemap', 'specLightingMask',
                'baseOffsetX', 'baseOffsetY', 'baseScale', 'baseRotation',
                'patternOffsetX', 'patternOffsetY', 'scale', 'rotation']
                .map(key => [key, zone?.[key] ?? null]));
            const layer = typeof getSelectedLayer === 'function' ? getSelectedLayer() : null;
            const layerLinks = layer ? { layerId: layer.id, groups: layer.elementLinkGroups || [] } : null;
            const transformPreview = root.SPBLayerTransformPreview?.peek(typeof freeTransformState !== 'undefined' ? freeTransformState : null);
            const layerState = (typeof _psdLayers === 'undefined' ? [] : _psdLayers).map(l => {
                const p=_getLayerAlphaImageData(l); let hash=2166136261;
                if(p) for(let i=0;i<p.data.length;i++) hash=Math.imul(hash^p.data[i],16777619);
                return {id:l.id,name:l.name,image:l.img,pixelHash:hash>>>0,
                    properties:JSON.stringify(Object.fromEntries(
                    Object.entries(l).filter(([key,value]) => key !== 'img' && typeof value !== 'function')))};
            });
            return { paint: read(paint), exported: read(exported), zoneIndex, layerState,
                transformPreview: transformPreview ? read(transformPreview) : null,
                layerLinks: JSON.parse(JSON.stringify(layerLinks)),
                region: zone?.regionMask?.slice() || null, spatial: zone?.spatialMask?.slice() || null,
                material: JSON.parse(JSON.stringify(material)), paintContext: paint.getContext('2d').getContextAttributes?.() || null };
        };
        const stopTiming = () => { if (gesture) gesture.stopped = true; cancelAnimationFrame(frame); };
        document.getElementById('spbAuditBaseline').onclick = () => {
            stopTiming();
            try { baseline = capture(); publish({ baseline: [baseline.paint.width, baseline.paint.height], paintContext: baseline.paintContext,
                sourceExportParity: difference(baseline.paint, baseline.exported), hasTransformPreview: !!baseline.transformPreview }); }
            catch (error) { publish({ error: error.message }); }
        };
        document.getElementById('spbAuditCompare').onclick = () => {
            stopTiming();
            try {
                if (!baseline) throw new Error('Set a baseline first.');
                const current = capture();
                publish({ source: difference(baseline.paint, current.paint), export: difference(baseline.exported, current.exported),
                    changedLayers: current.layerState.filter(l => {
                        const previous=baseline.layerState.find(p=>p.id===l.id);
                        return !previous || previous.image!==l.image || previous.pixelHash!==l.pixelHash || previous.properties!==l.properties;
                    }).map(l=>({id:l.id,name:l.name,imageChanged:baseline.layerState.find(p=>p.id===l.id)?.image!==l.image,
                        pixelsChanged:baseline.layerState.find(p=>p.id===l.id)?.pixelHash!==l.pixelHash})),
                    previewToExport: baseline.transformPreview ? difference(baseline.transformPreview, current.exported) : null,
                    zoneIndex: current.zoneIndex, zoneChanged: baseline.zoneIndex !== current.zoneIndex,
                    layerLinks: { changed: JSON.stringify(baseline.layerLinks) !== JSON.stringify(current.layerLinks), values: current.layerLinks },
                    material: { changed: Object.keys(current.material).filter(key =>
                        JSON.stringify(baseline.material[key]) !== JSON.stringify(current.material[key])), values: current.material },
                    region: maskDifference(baseline.region, current.region, current.paint.width, current.paint.height),
                    spatial: maskDifference(baseline.spatial, current.spatial, current.paint.width, current.paint.height) });
            } catch (error) { publish({ error: error.message }); }
        };
        document.getElementById('spbAuditTiming').onclick = () => {
            stopTiming();
            if (!gesture) { publish({ timing: 'Drag a canvas tool or adjustment slider first.' }); return; }
            const gaps = gesture.gaps.slice().sort((a, b) => a - b);
            publish({ target: gesture.target, events: gesture.moves,
                inputDelayMs: Math.round(gesture.inputDelay),
                firstFrameMs: Math.max(0, Math.round(gesture.firstFrame || 0)),
                maxFrameGapMs: Math.round(gaps.at(-1) || 0),
                p95FrameGapMs: Math.round(gaps[Math.max(0, Math.ceil(gaps.length * .95) - 1)] || 0),
                dragMaxFrameGapMs: Math.round(Math.max(0, ...gesture.dragGaps)),
                settleMaxFrameGapMs: Math.round(Math.max(0, ...gesture.settleGaps)),
                pointerHeldMs: gesture.release ? Math.round(gesture.release - gesture.start) : null,
                frames: gaps.length, longTasks: gesture.longTasks,
                longTaskSpans: gesture.longTaskSpans.map(entry => ({
                    startMs: Math.round(entry.start - gesture.start), durationMs: Math.round(entry.duration),
                    afterReleaseMs: gesture.release ? Math.round(entry.start - gesture.release) : null })),
                retouchDabs: gesture.retouchDabs || [], retouchDabsTruncated: !!gesture.retouchDabsTruncated,
                down: gesture.down, up: gesture.up, canvasAtDown: gesture.canvasAtDown, canvasAtUp: gesture.canvasAtUp,
                inclusiveCalls: Object.fromEntries(Object.entries(gesture.calls).map(([name, entry]) => [name,
                    { count: entry.count, totalMs: Math.round(entry.totalMs), maxMs: Math.round(entry.maxMs),
                        beforeReleaseCount: entry.beforeReleaseCount ?? null,
                        firstStartMs: entry.firstStartMs === undefined ? null : Math.round(entry.firstStartMs),
                        lastStartMs: entry.lastStartMs === undefined ? null : Math.round(entry.lastStartMs) }])), measured });
        };
        function tick(now) {
            if (!gesture || gesture.stopped) return;
            if (!gesture.firstFrame) gesture.firstFrame = now - gesture.start;
            if (gesture.previousFrame) {
                const gap = now - gesture.previousFrame;
                gesture.gaps.push(gap);
                const phase = gesture.release && now >= gesture.release ? gesture.settleGaps : gesture.dragGaps;
                phase.push(gap);
                if (phase.length > 600) phase.shift();
            }
            gesture.previousFrame = now;
            if (gesture.gaps.length > 600) gesture.gaps.shift();
            if (gesture.release && now - gesture.release > 250) { gesture.stopped = true; return; }
            frame = requestAnimationFrame(tick);
        }
        document.addEventListener('pointerdown', event => {
            if (panel.contains(event.target) || !event.target.closest('#canvasViewport, input[type="range"]')) return;
            cancelAnimationFrame(frame);
            const now = performance.now();
            gesture = { target: event.target.id || event.target.tagName, start: now,
                inputDelay: Math.max(0, now - event.timeStamp), moves: 0, gaps: [], dragGaps: [], settleGaps: [], longTasks: [], longTaskSpans: [], calls: {},
                down: [event.clientX, event.clientY], canvasAtDown: canvasGeometry() };
            frame = requestAnimationFrame(tick);
        }, { capture: true, passive: true });
        document.addEventListener('pointermove', () => { if (gesture && !gesture.stopped) gesture.moves++; }, { capture: true, passive: true });
        for (const name of ['pointerup', 'pointercancel']) document.addEventListener(name, event => {
            if (gesture && !gesture.stopped) {
                gesture.release = performance.now(); gesture.up = [event.clientX, event.clientY]; gesture.canvasAtUp = canvasGeometry();
            }
        }, { capture: true, passive: true });
        if (typeof PerformanceObserver === 'function' && PerformanceObserver.supportedEntryTypes.includes('longtask')) {
            new PerformanceObserver(list => {
                for (const entry of list.getEntries()) if (gesture && entry.startTime >= gesture.start
                    && (!gesture.release || entry.startTime <= gesture.release + 250)) {
                    gesture.longTasks.push(Math.round(entry.duration));
                    gesture.longTaskSpans.push({ start: entry.startTime, duration: entry.duration });
                    if (gesture.longTaskSpans.length > 30) gesture.longTaskSpans.shift();
                    if (gesture.longTasks.length > 30) gesture.longTasks.shift();
                }
            }).observe({ type: 'longtask' });
        }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
    else mount();
})(typeof window === 'object' ? window : globalThis);
