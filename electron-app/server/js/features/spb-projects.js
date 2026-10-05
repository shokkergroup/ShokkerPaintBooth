/* [SPB-PROJECTS v2 2026-08-22] Lossless, fail-closed Layered Workflow projects.
 *
 * A v2 project embeds the current raster for every available Layer, including
 * Layers that came from a PSD and were edited in SPB. Restore is staged: saved
 * pixels decode first, the server confirms the source content fingerprint, the
 * source loader must commit the exact requested path, and layer/config mutation
 * happens only after every saved binding resolves. Version 1 JSON projects stay
 * readable, but are identified honestly as lacking a saved source fingerprint.
 */
(function () {
    'use strict';

    var API = '/api/projects';
    var SCHEMA_VERSION = 2;
    var INLINE_SAVE_BYTES = 8 * 1024 * 1024;
    var DEFAULT_CHUNK_BYTES = 4 * 1024 * 1024;
    var RESTART_MSG = 'Projects needs one app restart to activate the current server routes. Close and reopen Shokker Paint Booth, then try again.';

    function _apiMissing(res, out) {
        return (res && res.status === 404) || (out && out.error === 'not_found');
    }

    function _toast(msg, warn) {
        try {
            if (typeof window.showToast === 'function') window.showToast(msg, warn);
        } catch (e) {}
    }

    function _clone(value) {
        return value == null ? value : JSON.parse(JSON.stringify(value));
    }

    function _layers() {
        try {
            return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers))
                ? _psdLayers
                : (window._psdLayers || []);
        } catch (e) {
            return window._psdLayers || [];
        }
    }

    function _paintData() {
        try {
            return (typeof paintImageData !== 'undefined') ? paintImageData : window.paintImageData;
        } catch (e) {
            return window.paintImageData || null;
        }
    }

    function _currentSource() {
        try {
            return (typeof window.getCurrentSourcePaintFile === 'function')
                ? String(window.getCurrentSourcePaintFile() || '').trim()
                : '';
        } catch (e) {
            return '';
        }
    }

    function _normalizePath(path) {
        return String(path || '').trim().replace(/\//g, '\\').replace(/\\+/g, '\\').toLowerCase();
    }

    function _samePath(left, right) {
        return !!left && !!right && _normalizePath(left) === _normalizePath(right);
    }

    function _waitFor(cond, timeoutMs, everyMs) {
        return new Promise(function (resolve) {
            var t0 = Date.now();
            (function tick() {
                var ok = false;
                try { ok = !!cond(); } catch (e) {}
                if (ok) return resolve(true);
                if (Date.now() - t0 > (timeoutMs || 30000)) return resolve(false);
                setTimeout(tick, everyMs || 100);
            })();
        });
    }

    async function _fetchJson(url, options) {
        var res = await fetch(url, options || {});
        var text = await res.text();
        var out = null;
        try { out = text ? JSON.parse(text) : {}; }
        catch (e) { out = { error: text || ('HTTP ' + res.status) }; }
        return { res: res, out: out };
    }

    function _jsonHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-Shokker-Internal': '1',
        };
    }

    // ------------------------------------------------------------------ save
    function _layerRasterDataUrl(layer) {
        if (!layer || !layer.img) return null;
        if (typeof layer.img.toDataURL === 'function') {
            var direct = layer.img.toDataURL('image/png');
            if (direct && direct.indexOf('data:image/png;base64,') === 0) return direct;
        }
        var source = layer.img;
        var width = Number(source.naturalWidth || source.videoWidth || source.width || 0);
        var height = Number(source.naturalHeight || source.videoHeight || source.height || 0);
        if (!width || !height) throw new Error('Layer pixels have no dimensions');
        var canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        // SPB-93: use CPU-backed publication precision for persisted Layer pixels.
        var context = canvas.getContext('2d', { willReadFrequently: true });
        if (!context) throw new Error('Canvas is unavailable');
        context.drawImage(source, 0, 0);
        var encoded = canvas.toDataURL('image/png');
        if (!encoded || encoded.indexOf('data:image/png;base64,') !== 0) {
            throw new Error('Layer PNG encoding failed');
        }
        return encoded;
    }

    function _serializeLayerState() {
        var layers = _layers();
        if (!layers.length) return { layers: [], errors: [] };
        var errors = [];
        var records = layers.map(function (layer, index) {
            var record;
            try {
                record = {
                    idx: index,
                    id: String(layer.id || ('layer_' + index)),
                    path: layer.path || null,
                    pathParts: Array.isArray(layer.pathParts) ? layer.pathParts.slice() : null,
                    rasterKey: layer.rasterKey != null ? String(layer.rasterKey) : null,
                    name: layer.name || ('Layer ' + index),
                    groupName: layer.groupName || '',
                    groupChain: Array.isArray(layer.groupChain) ? _clone(layer.groupChain) : [],
                    parentGroupKey: layer.parentGroupKey != null ? String(layer.parentGroupKey) : null,
                    visible: layer.visible !== false,
                    importVisible: layer.importVisible !== false,
                    ownVisible: layer.ownVisible !== false,
                    opacity: (layer.opacity != null ? layer.opacity : 255),
                    blendMode: layer.blendMode || 'source-over',
                    locked: !!layer.locked,
                    alphaLock: !!layer.alphaLock,
                    clippingMask: !!layer.clippingMask,
                    effects: layer.effects ? _clone(layer.effects) : null,
                    elementLinkGroups: _clone(layer.elementLinkGroups || []),
                    elementInstances: _clone(layer.elementInstances || []),
                    adjHue: Number(layer.adjHue) || 0,
                    adjSat: Number(layer.adjSat) || 0,
                    adjBri: Number(layer.adjBri) || 0,
                    bbox: Array.isArray(layer.bbox) ? layer.bbox.slice(0, 4) : null,
                    pixelState: layer.img ? 'embedded' : 'source',
                };
            } catch (error) {
                errors.push((layer && (layer.name || layer.id) || ('Layer ' + index)) +
                    ' state could not be captured: ' + error.message);
                return { idx: index, id: String(layer && layer.id || ('layer_' + index)) };
            }
            if (layer.img) {
                try {
                    // Always capture the live pixels. A PSD path identifies the
                    // original source, not whether this Layer has been edited.
                    record.imgData = _layerRasterDataUrl(layer);
                } catch (error) {
                    errors.push((record.name || record.id) + ': ' + error.message);
                }
            }
            return record;
        });
        return { layers: records, errors: errors };
    }

    function _newProjectId() {
        try {
            if (window.crypto && typeof window.crypto.randomUUID === 'function') {
                return window.crypto.randomUUID();
            }
        } catch (e) {}
        return 'spbproj_' + Date.now() + '_' + Math.random().toString(36).slice(2);
    }

    function buildProjectPayload(name) {
        try {
            if (typeof window._settleActiveLayerStrokeBeforeTargetChange === 'function') {
                window._settleActiveLayerStrokeBeforeTargetChange();
            }
        } catch (e) {}

        var config = null;
        try { config = (typeof window.getConfig === 'function') ? window.getConfig() : null; }
        catch (error) {
            _toast('Cannot save project — config capture failed: ' + error.message, true);
            return null;
        }
        if (!config) {
            _toast('Cannot save project — config is unavailable', true);
            return null;
        }
        var source = _currentSource() || config.sourcePaintFile || config.paintFile || '';
        if (!source) {
            _toast('Cannot save project — open a source paint first', true);
            return null;
        }
        var serialized = _serializeLayerState();
        if (serialized.errors.length) {
            _toast('Project was not saved because Layer pixels could not be captured: ' +
                serialized.errors.slice(0, 3).join('; '), true);
            return null;
        }
        var savedLayerIds = new Set(serialized.layers.map(function (record) { return String(record.id); }));
        var selectedLayerId = window._selectedLayerId && savedLayerIds.has(String(window._selectedLayerId))
            ? String(window._selectedLayerId)
            : null;
        var canvas = document.getElementById('paintCanvas');
        return {
            _spb_project: true,
            version: '2.0',
            schemaVersion: SCHEMA_VERSION,
            projectId: _newProjectId(),
            name: name,
            sourcePaintFile: source,
            canvas: canvas ? { width: canvas.width, height: canvas.height } : null,
            config: config,
            layers: serialized.layers,
            selectedLayerId: selectedLayerId,
            selectedLayerIds: (window._selectedLayerIds && typeof window._selectedLayerIds.forEach === 'function')
                ? Array.from(window._selectedLayerIds).map(String).filter(function (id) { return savedLayerIds.has(id); })
                : null,
            appBuild: window.SPB_BUILD_HASH || window.SPB_VERSION || null,
            savedAt: new Date().toISOString(),
        };
    }

    async function _saveProjectEnvelope(name, payload) {
        var body = JSON.stringify({ name: name, project: payload });
        var blob = new Blob([body], { type: 'application/json' });
        if (blob.size <= INLINE_SAVE_BYTES) {
            return _fetchJson(API + '/save', {
                method: 'POST', headers: _jsonHeaders(), body: body,
            });
        }

        var started = await _fetchJson(API + '/save/start', {
            method: 'POST', headers: _jsonHeaders(),
            body: JSON.stringify({ name: name, totalBytes: blob.size }),
        });
        if (!started.out || !started.out.ok) return started;

        var uploadId = started.out.uploadId;
        var chunkBytes = Number(started.out.chunkBytes) || DEFAULT_CHUNK_BYTES;
        var index = 0;
        try {
            _toast('Saving large project safely (0%)…');
            for (var offset = 0; offset < blob.size; offset += chunkBytes) {
                var part = blob.slice(offset, Math.min(blob.size, offset + chunkBytes));
                var chunk = await _fetchJson(API + '/save/chunk/' + encodeURIComponent(uploadId), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/octet-stream',
                        'X-Shokker-Internal': '1',
                        'X-SPB-Chunk-Index': String(index),
                    },
                    body: part,
                });
                if (!chunk.out || !chunk.out.ok) return chunk;
                index++;
            }
            return _fetchJson(API + '/save/commit/' + encodeURIComponent(uploadId), {
                method: 'POST', headers: { 'X-Shokker-Internal': '1' },
            });
        } finally {
            // Commit removes successful uploads. Abort is deliberately safe and
            // idempotent, so it also cleans failed/abandoned chunk sessions.
            try {
                await fetch(API + '/save/abort/' + encodeURIComponent(uploadId), {
                    method: 'POST', headers: { 'X-Shokker-Internal': '1' },
                });
            } catch (e) {}
        }
    }

    async function saveSpbProject() {
        var defaultName = '';
        try {
            var source = _currentSource();
            defaultName = source
                ? source.replace(/\\/g, '/').split('/').pop().replace(/\.[^.]+$/, '')
                : 'My Project';
        } catch (e) {
            defaultName = 'My Project';
        }
        if (!window.SPBProjectNameDialog) {
            _toast('Reload Paint Booth to enable project saving.', true);
            return false;
        }
        var name = await window.SPBProjectNameDialog.open(defaultName);
        if (!name) return false;
        var payload = buildProjectPayload(name);
        if (!payload) return false;
        try {
            var result = await _saveProjectEnvelope(name, payload);
            var res = result.res;
            var out = result.out;
            if (out && out.ok) {
                _toast('Project saved: ' + out.file + ' (' +
                    Math.round((out.bytes || 0) / 1024) + ' KB) — all live Layer pixels included');
                return true;
            }
            if (_apiMissing(res, out)) _toast(RESTART_MSG, true);
            else _toast('Project save failed: ' + ((out && out.error) || res.status), true);
        } catch (error) {
            _toast('Project save failed: ' + error.message, true);
        }
        return false;
    }

    // ------------------------------------------------------------------ load
    function _dataUrlToCanvas(dataUrl, fallbackWidth, fallbackHeight) {
        return new Promise(function (resolve) {
            var image = new Image();
            image.onload = function () {
                try {
                    var canvas = document.createElement('canvas');
                    canvas.width = image.naturalWidth || image.width || fallbackWidth || 2048;
                    canvas.height = image.naturalHeight || image.height || fallbackHeight || 2048;
                    canvas.getContext('2d', { willReadFrequently: true }).drawImage(image, 0, 0);
                    resolve(canvas);
                } catch (error) {
                    resolve(null);
                }
            };
            image.onerror = function () { resolve(null); };
            image.src = dataUrl;
        });
    }

    async function _stageLayerAssets(records) {
        var decoded = new Array((records || []).length);
        var errors = [];
        for (var index = 0; index < (records || []).length; index++) {
            var record = records[index] || {};
            if (!record.imgData) continue;
            var bbox = record.bbox || [];
            var canvas = await _dataUrlToCanvas(record.imgData, bbox[2], bbox[3]);
            if (!canvas) errors.push((record.name || record.id || ('Layer ' + index)) + ' pixels are corrupt');
            decoded[index] = canvas;
        }
        return { decoded: decoded, errors: errors };
    }

    function _sourceGate(project, sourceStatus, source) {
        if (!sourceStatus) {
            return { ok: false, message: RESTART_MSG };
        }
        if (!_samePath(sourceStatus.requestedPath, source)) {
            return { ok: false, message: 'Project source identity was inconsistent; nothing was applied.' };
        }
        if (!sourceStatus.exists) {
            return {
                ok: false,
                message: 'Project source is missing or unavailable: ' + source + '. Nothing was applied.',
            };
        }
        if (sourceStatus.matchesSavedFingerprint === false) {
            return {
                ok: false,
                message: 'Project source changed since this workflow was saved. Restore was stopped before applying Layers or zones: ' + source,
            };
        }
        return {
            ok: true,
            legacyUnverified: !!sourceStatus.legacyUnverified || Number(project.schemaVersion || 1) < 2,
        };
    }

    function _sourceTransactionApi() {
        var api = window.SPBSourceLoadTransaction;
        return api && typeof api.captureDocumentState === 'function' &&
            typeof api.restoreDocumentState === 'function'
            ? api
            : null;
    }

    function _confirmStructuredLoad(result, source) {
        if (!result || typeof result !== 'object') {
            return { ok: false, error: 'Source loader returned no transactional result' };
        }
        if (result.ok !== true) {
            return { ok: false, error: String(result.error || 'Source loader did not commit') };
        }
        if (!_samePath(result.requestedPath, source)) {
            return { ok: false, error: 'Source loader confirmed a different requested path' };
        }
        if (!_samePath(result.committedPath, source)) {
            return { ok: false, error: 'Source loader committed a different document' };
        }
        if (!Number.isFinite(Number(result.generation)) || Number(result.generation) < 1) {
            return { ok: false, error: 'Source loader returned an invalid commit generation' };
        }
        if (!String(result.fingerprint || '').trim()) {
            return { ok: false, error: 'Source loader did not fingerprint the committed document' };
        }

        var transaction = _sourceTransactionApi();
        if (!transaction) {
            return { ok: false, error: 'Transactional source restore is unavailable' };
        }
        try {
            if (typeof transaction.getGeneration === 'function' &&
                    Number(transaction.getGeneration()) !== Number(result.generation)) {
                return { ok: false, error: 'Source load was superseded before Project restore' };
            }
            if (typeof transaction.getCommittedPath === 'function' &&
                    !_samePath(transaction.getCommittedPath(), source)) {
                return { ok: false, error: 'Committed source identity did not match the Project source' };
            }
            if (typeof transaction.getCommittedFingerprint === 'function') {
                var committedFingerprint = String(transaction.getCommittedFingerprint() || '');
                if (!committedFingerprint || committedFingerprint !== String(result.fingerprint)) {
                    return { ok: false, error: 'Committed source fingerprint did not match the loader result' };
                }
            }
        } catch (error) {
            return { ok: false, error: 'Source transaction confirmation failed: ' + error.message };
        }
        if (!_samePath(_currentSource(), source)) {
            return { ok: false, error: 'Current source identity did not match the loader commit' };
        }
        return { ok: true, result: result };
    }

    function _captureProjectOpenState() {
        var transaction = _sourceTransactionApi();
        if (!transaction) {
            return { ok: false, error: 'Transactional source restore is unavailable' };
        }
        var config = null;
        try {
            if (typeof window.getConfig !== 'function') throw new Error('config capture is unavailable');
            config = _clone(window.getConfig());
            if (!config) throw new Error('config capture returned no state');
            return {
                ok: true,
                transaction: transaction,
                sourceState: transaction.captureDocumentState(),
                config: config,
                sourcePath: _currentSource(),
            };
        } catch (error) {
            return { ok: false, error: error.message };
        }
    }

    function _restoreProjectOpenState(snapshot) {
        if (!snapshot || !snapshot.ok) {
            return { ok: false, error: 'pre-open document snapshot was unavailable' };
        }
        var errors = [];
        try {
            snapshot.transaction.restoreDocumentState(snapshot.sourceState);
        } catch (error) {
            errors.push('source rollback failed: ' + error.message);
        }
        try {
            if (typeof window.loadConfigFromObj !== 'function') {
                throw new Error('config loader is unavailable');
            }
            window.loadConfigFromObj(_clone(snapshot.config));
        } catch (error) {
            errors.push('config rollback failed: ' + error.message);
        }
        // Config restoration legitimately touches paintFile and replaces the
        // zone array. Re-publish the exact captured canvases, source identity,
        // original zone objects, selections, and Layer/history references last.
        try {
            snapshot.transaction.restoreDocumentState(snapshot.sourceState);
        } catch (error) {
            errors.push('final document rollback failed: ' + error.message);
        }
        var currentPath = _currentSource();
        if ((snapshot.sourcePath || currentPath) && !_samePath(currentPath, snapshot.sourcePath)) {
            errors.push('restored source identity did not match the pre-open document');
        }
        return {
            ok: errors.length === 0,
            error: errors.join('; '),
        };
    }

    async function _loadAndConfirmSource(source, layered) {
        if (layered) {
            if (typeof window.importPSDFromPath !== 'function') {
                return { ok: false, error: 'Layered-file importer is unavailable' };
            }
            var previousData = window._psdData;
            var layeredResult;
            try { layeredResult = await window.importPSDFromPath(source, { restoreProject: true }); }
            catch (error) { return { ok: false, error: error.message }; }
            var layeredConfirmation = _confirmStructuredLoad(layeredResult, source);
            if (!layeredConfirmation.ok) return layeredConfirmation;
            var layersReady = window._psdLayersLoaded === true && _layers().length > 0;
            var freshImport = window._psdData && window._psdData.success && window._psdData !== previousData;
            if (!layersReady || !freshImport || !_samePath(_currentSource(), source)) {
                return { ok: false, error: 'The layered source did not finish importing as the requested document' };
            }
            return layeredConfirmation;
        }

        var beforePixels = _paintData();
        var flatResult;
        try {
            if (typeof window.loadPaintPreviewFromServer === 'function') {
                flatResult = await window.loadPaintPreviewFromServer(source);
            } else if (typeof window.loadPaintByPath === 'function') {
                flatResult = await window.loadPaintByPath(source);
            } else {
                return { ok: false, error: 'Flat-paint loader is unavailable' };
            }
        } catch (error) {
            return { ok: false, error: error.message };
        }
        var flatConfirmation = _confirmStructuredLoad(flatResult, source);
        if (!flatConfirmation.ok) return flatConfirmation;
        if (!_paintData() || _paintData() === beforePixels) {
            return { ok: false, error: 'The flat source reported success without committing new pixels' };
        }
        return flatConfirmation;
    }

    async function _reverifySourceAfterLoad(file, project, source) {
        try {
            var result = await _fetchJson(API + '/verify-source', {
                method: 'POST', headers: _jsonHeaders(),
                body: JSON.stringify({ file: file }),
            });
            if (!result.out || !result.out.ok) {
                return {
                    ok: false,
                    message: 'Source verification failed after loading: ' +
                        ((result.out && result.out.error) || result.res.status),
                };
            }
            return _sourceGate(project, result.out.sourceStatus, source);
        } catch (error) {
            return { ok: false, message: 'Source verification failed after loading: ' + error.message };
        }
    }

    function _uniqueLayerId(preferred, occupied, fallbackIndex) {
        var base = String(preferred || ('project_layer_' + fallbackIndex));
        if (!occupied.has(base)) {
            occupied.add(base);
            return base;
        }
        var suffix = 2;
        while (occupied.has(base + '_' + suffix)) suffix++;
        var result = base + '_' + suffix;
        occupied.add(result);
        return result;
    }

    function _prepareLayerRestore(records, staged, schemaVersion) {
        var current = _layers();
        var used = new Set();
        var occupiedIds = new Set(current.map(function (layer) { return String(layer.id); }));
        var idMap = {};
        var descriptors = [];
        var errors = [];

        current.forEach(function (layer) { idMap[String(layer.id)] = String(layer.id); });

        function claim(layer) {
            if (layer) used.add(layer);
            return layer;
        }

        function available(predicate) {
            return current.find(function (layer) { return !used.has(layer) && predicate(layer); }) || null;
        }

        (records || []).forEach(function (record, index) {
            record = record || {};
            var layer = null;
            if (record.rasterKey != null) {
                layer = available(function (candidate) {
                    return candidate.rasterKey != null && String(candidate.rasterKey) === String(record.rasterKey);
                });
            }
            if (!layer && record.path) {
                layer = available(function (candidate) { return candidate.path === record.path; });
            }
            if (!layer && record.id) {
                layer = available(function (candidate) { return String(candidate.id) === String(record.id); });
            }
            if (!layer) {
                layer = available(function (candidate) {
                    return candidate.name === record.name &&
                        (candidate.groupName || '') === (record.groupName || '');
                });
            }
            if (!layer) {
                layer = available(function (candidate) { return candidate.name === record.name; });
            }
            if (layer) claim(layer);

            var pixels = staged.decoded[index] || null;
            if (!layer && pixels) {
                layer = {
                    id: _uniqueLayerId(record.id, occupiedIds, index),
                    name: record.name || ('Layer ' + index),
                    path: null,
                    img: pixels,
                    bbox: record.bbox || [0, 0, pixels.width, pixels.height],
                    groupName: record.groupName || '',
                    groupChain: Array.isArray(record.groupChain) ? _clone(record.groupChain) : [],
                    parentGroupKey: record.parentGroupKey != null ? String(record.parentGroupKey) : null,
                };
            }
            if (!layer) {
                errors.push('Saved Layer could not be resolved: ' +
                    (record.name || record.path || record.id || ('Layer ' + index)));
                return;
            }
            if (record.id) idMap[String(record.id)] = String(layer.id);
            descriptors.push({ record: record, layer: layer, pixels: pixels });
        });

        var sourceExtras = current.filter(function (layer) { return !used.has(layer); });
        // In v2, the saved stack is authoritative. A deleted or merged source
        // Layer must stay deleted after reopen, so source-only extras are
        // intentionally dropped. Version 1 keeps its historical behavior
        // because its incomplete pixel snapshots were not an exact stack.
        var extras = Number(schemaVersion || 1) >= 2 ? [] : sourceExtras;

        return {
            descriptors: descriptors,
            extras: extras,
            droppedSourceExtras: Number(schemaVersion || 1) >= 2 ? sourceExtras : [],
            idMap: idMap,
            errors: errors,
        };
    }

    function _remapProjectConfig(config, idMap, availableIds) {
        var remapped = _clone(config || {});
        var missing = [];
        (remapped.zones || []).forEach(function (zone) {
            if (!zone) return;
            var sourceIds = Array.isArray(zone.sourceLayers) && zone.sourceLayers.length
                ? zone.sourceLayers.slice()
                : (zone.sourceLayer ? [zone.sourceLayer] : []);
            var next = [];
            sourceIds.forEach(function (oldId) {
                var mapped = idMap[String(oldId)] ||
                    (availableIds.has(String(oldId)) ? String(oldId) : null);
                if (!mapped) {
                    missing.push((zone.name || zone.id || 'Zone') + ' → ' + oldId);
                } else if (next.indexOf(mapped) === -1) {
                    next.push(mapped);
                }
            });
            zone.sourceLayers = next;
            zone.sourceLayer = next[0] || null;
        });
        return { config: remapped, missing: missing };
    }

    function _commitLayerRestore(plan) {
        var ordered = [];
        plan.descriptors.forEach(function (descriptor) {
            var record = descriptor.record;
            var layer = descriptor.layer;
            layer.name = record.name || layer.name;
            layer.visible = record.visible !== false;
            layer.importVisible = record.importVisible !== false;
            layer.ownVisible = record.ownVisible !== false;
            layer.opacity = (record.opacity != null ? record.opacity : 255);
            layer.blendMode = record.blendMode || 'source-over';
            layer.locked = !!record.locked;
            layer.alphaLock = !!record.alphaLock;
            layer.clippingMask = !!record.clippingMask;
            // New Project records own the group topology. Legacy records did
            // not carry it, so preserve the freshly imported source topology
            // instead of silently flattening an older .spbproj on open.
            if (Array.isArray(record.groupChain)) {
                layer.groupChain = _clone(record.groupChain);
                layer.parentGroupKey = record.parentGroupKey != null
                    ? String(record.parentGroupKey)
                    : (layer.groupChain.length ? String(layer.groupChain[layer.groupChain.length - 1].key) : null);
            } else if (record.parentGroupKey != null) {
                layer.parentGroupKey = String(record.parentGroupKey);
            }
            layer.effects = record.effects ? _clone(record.effects) : null;
            layer.elementLinkGroups = Array.isArray(record.elementLinkGroups) ? _clone(record.elementLinkGroups) : [];
            layer.elementInstances = Array.isArray(record.elementInstances) ? _clone(record.elementInstances) : [];
            layer.adjHue = Number(record.adjHue) || 0;
            layer.adjSat = Number(record.adjSat) || 0;
            layer.adjBri = Number(record.adjBri) || 0;
            if (Array.isArray(record.bbox)) layer.bbox = record.bbox.slice(0, 4);
            if (Array.isArray(record.pathParts)) layer.pathParts = record.pathParts.slice();
            if (record.rasterKey != null) layer.rasterKey = String(record.rasterKey);
            if (descriptor.pixels) layer.img = descriptor.pixels;
            ordered.push(layer);
        });

        var next = ordered.concat(plan.extras);
        var target = _layers();
        target.length = 0;
        Array.prototype.push.apply(target, next);
        try {
            if (typeof window._publishPSDDocumentState === 'function') window._publishPSDDocumentState();
        } catch (e) {}
        return next;
    }

    function _snapshotLoadedLayers() {
        var order = _layers().slice();
        return {
            order: order,
            selectedLayerId: window._selectedLayerId || null,
            states: order.map(function (layer) {
                return {
                    layer: layer,
                    name: layer.name,
                    visible: layer.visible,
                    importVisible: layer.importVisible,
                    ownVisible: layer.ownVisible,
                    opacity: layer.opacity,
                    blendMode: layer.blendMode,
                    locked: layer.locked,
                    alphaLock: layer.alphaLock,
                    clippingMask: layer.clippingMask,
                    groupChain: layer.groupChain,
                    parentGroupKey: layer.parentGroupKey,
                    effects: layer.effects,
                    elementLinkGroups: layer.elementLinkGroups,
                    elementInstances: layer.elementInstances,
                    adjHue: layer.adjHue,
                    adjSat: layer.adjSat,
                    adjBri: layer.adjBri,
                    bbox: layer.bbox,
                    pathParts: layer.pathParts,
                    rasterKey: layer.rasterKey,
                    img: layer.img,
                };
            }),
        };
    }

    function _restoreLoadedLayers(snapshot) {
        if (!snapshot) return;
        snapshot.states.forEach(function (state) {
            var layer = state.layer;
            Object.keys(state).forEach(function (key) {
                if (key !== 'layer') layer[key] = state[key];
            });
        });
        var target = _layers();
        target.length = 0;
        Array.prototype.push.apply(target, snapshot.order);
        try {
            if (typeof window._publishPSDDocumentState === 'function') window._publishPSDDocumentState();
            if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
            if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
            if (snapshot.selectedLayerId && typeof window.selectPSDLayer === 'function') {
                window.selectPSDLayer(snapshot.selectedLayerId);
            }
        } catch (e) {}
    }

    async function loadSpbProject(file) {
        var result;
        try {
            result = await _fetchJson(API + '/open', {
                method: 'POST', headers: _jsonHeaders(),
                body: JSON.stringify({ file: file }),
            });
        } catch (error) {
            _toast('Project open failed: ' + error.message, true);
            return false;
        }
        var res = result.res;
        var out = result.out;
        if (!out || !out.ok || !out.project) {
            if (_apiMissing(res, out)) _toast(RESTART_MSG, true);
            else _toast('Project open failed: ' + ((out && out.error) || res.status), true);
            return false;
        }

        var project = out.project;
        if (!project.config || !Array.isArray(project.layers || [])) {
            _toast('Project is incomplete or corrupt; nothing was applied', true);
            return false;
        }
        var source = project.sourcePaintFile || project.config.sourcePaintFile || project.config.paintFile || '';
        if (!source) {
            _toast('Project has no source paint path; nothing was applied', true);
            return false;
        }
        var gate = _sourceGate(project, out.sourceStatus, source);
        if (!gate.ok) {
            _toast(gate.message, true);
            return false;
        }

        // Decode all embedded pixels before changing the current document.
        var staged = await _stageLayerAssets(project.layers || []);
        if (staged.errors.length) {
            _toast('Project pixels are damaged; restore stopped before changing the document: ' +
                staged.errors.slice(0, 3).join('; '), true);
            return false;
        }

        // The transaction begins before source B is requested. Every failure
        // below—including a successful B load followed by a late validation or
        // commit fault—must restore this exact document-A snapshot.
        var preOpen = _captureProjectOpenState();
        if (!preOpen.ok) {
            _toast('Project restore stopped before changing the document: ' + preOpen.error, true);
            return false;
        }
        function stopAndRestore(message) {
            var rollback = _restoreProjectOpenState(preOpen);
            var suffix = rollback.ok
                ? ' The previous document was restored.'
                : ' CRITICAL: the previous document could not be restored exactly: ' + rollback.error;
            _toast(message + suffix, true);
            return false;
        }

        closeSpbProjectsModal();
        _toast('Opening project "' + (project.name || file) + '" — verifying source and Layers…');
        var layered = /\.(psd|xcf|ora)$/i.test(source.split(/[?#]/, 1)[0]);
        var loaded;
        try {
            loaded = await _loadAndConfirmSource(source, layered);
        } catch (error) {
            return stopAndRestore('Project restore stopped during source confirmation: ' + error.message + '.');
        }
        if (!loaded.ok) {
            return stopAndRestore('Project restore stopped: ' + loaded.error +
                '. Layer settings and zones were not applied.');
        }
        var verifiedAfterLoad = await _reverifySourceAfterLoad(file, project, source);
        if (!verifiedAfterLoad.ok) {
            return stopAndRestore('Project restore stopped after source load: ' + verifiedAfterLoad.message +
                '. No saved Layer state or zones were applied.');
        }
        gate.legacyUnverified = gate.legacyUnverified || verifiedAfterLoad.legacyUnverified;

        var plan = { descriptors: [], extras: [], idMap: {}, errors: [] };
        if (layered || (project.layers && project.layers.length)) {
            try {
                plan = _prepareLayerRestore(project.layers || [], staged, project.schemaVersion || 1);
            } catch (error) {
                return stopAndRestore('Project restore stopped while resolving the saved Layer map: ' + error.message + '.');
            }
            if (plan.errors.length) {
                return stopAndRestore('Project restore stopped after source verification because the Layer map was not exact: ' +
                    plan.errors.slice(0, 3).join('; ') + '. Zones were not applied.');
            }
        }

        var futureIds = new Set(plan.descriptors.map(function (descriptor) {
            return String(descriptor.layer.id);
        }).concat(plan.extras.map(function (layer) { return String(layer.id); })));
        var remapped;
        try {
            remapped = _remapProjectConfig(project.config, plan.idMap, futureIds);
        } catch (error) {
            return stopAndRestore('Project restore stopped while remapping zone-to-Layer bindings: ' + error.message + '.');
        }
        if (remapped.missing.length) {
            return stopAndRestore('Project restore stopped because zone-to-Layer bindings are missing: ' +
                remapped.missing.slice(0, 4).join('; ') +
                '. No saved Layer state or zones were applied.');
        }

        var selected = project.selectedLayerId
            ? (plan.idMap[String(project.selectedLayerId)] ||
                (futureIds.has(String(project.selectedLayerId)) ? String(project.selectedLayerId) : null))
            : null;
        if (project.selectedLayerId && !selected) {
            return stopAndRestore('Project restore stopped because the saved active Layer no longer exists. ' +
                'No saved Layer state or zones were applied.');
        }

        try {
            if (plan.descriptors.length || plan.extras.length) {
                _commitLayerRestore(plan);
                if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers();
                if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel();
            }
            if (typeof window.loadConfigFromObj !== 'function') {
                throw new Error('zone configuration loader is unavailable');
            }
            window.loadConfigFromObj(remapped.config);
            if (selected && typeof window.selectPSDLayer === 'function') window.selectPSDLayer(selected);
            if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
        } catch (error) {
            return stopAndRestore('Project source loaded, but workflow commit failed: ' + error.message +
                '. Saved Layer/config changes were not kept.');
        }

        var zoneCount = ((remapped.config || {}).zones || []).length;
        var layerCount = plan.descriptors.length;
        var suffix = gate.legacyUnverified
            ? ' Warning: this legacy v1 project had no saved source fingerprint; save it again to upgrade.'
            : '';
        _toast('Project "' + (project.name || file) + '" restored — ' + zoneCount +
            ' zone(s), ' + layerCount + ' Layer state(s), source verified.' + suffix,
            gate.legacyUnverified);
        return true;
    }

    // ----------------------------------------------------------------- modal
    function closeSpbProjectsModal() {
        var modal = document.getElementById('spbProjectsModal');
        if (modal) modal.remove();
    }

    function _element(tag, style, text) {
        var element = document.createElement(tag);
        if (style) element.style.cssText = style;
        if (text != null) element.textContent = String(text);
        return element;
    }

    function _button(label, title, handler, extraStyle) {
        var button = _element('button', 'padding:4px 10px;font-weight:700;' + (extraStyle || ''), label);
        button.className = 'btn btn-sm';
        if (title) button.title = title;
        button.type = 'button';
        button.addEventListener('click', handler);
        return button;
    }

    function _projectRow(project) {
        var row = _element('div', 'display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--border,#1a1a3a);border-radius:8px;margin-bottom:6px;background:rgba(255,255,255,0.02);');
        var info = _element('div', 'flex:1;min-width:0;');
        var title = _element('div', 'font-weight:700;color:var(--text-bright,#f0f0ff);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;',
            (project.name || project.file || 'Untitled Project') + (project.corrupt ? ' ⚠' : ''));
        var when = project.modified ? new Date(project.modified * 1000).toLocaleString() : '';
        var sourceName = String(project.sourcePaintFile || '').replace(/\\/g, '/').split('/').pop();
        var details = [when];
        if (sourceName) details.push(sourceName);
        if (project.zoneCount != null) details.push(project.zoneCount + ' zones');
        if (project.layerCount != null) details.push(project.layerCount + ' Layers');
        if (project.sourceAvailable === false) details.push('SOURCE MISSING');
        var meta = _element('div', 'font-size:10px;color:' +
            (project.sourceAvailable === false ? '#ff9966' : 'var(--text-dim,#8a96b3)') + ';', details.filter(Boolean).join(' · '));
        info.appendChild(title);
        info.appendChild(meta);
        row.appendChild(info);
        var open = _button('OPEN', 'Open this project', function () {
            loadSpbProject(String(project.file || ''));
        }, 'padding:4px 12px;');
        open.disabled = !!project.corrupt;
        row.appendChild(open);
        row.appendChild(_button('✕', 'Delete this project', function () {
            deleteSpbProject(String(project.file || ''));
        }, 'padding:4px 8px;color:#ff6666;'));
        return row;
    }

    async function openSpbProjects() {
        closeSpbProjectsModal();
        var list = [];
        var directory = '';
        var needsRestart = false;
        try {
            var result = await _fetchJson(API + '/list', {
                headers: { 'X-Shokker-Internal': '1' },
            });
            if (result.out && result.out.ok) {
                list = result.out.projects || [];
                directory = result.out.dir || '';
            } else if (_apiMissing(result.res, result.out)) {
                needsRestart = true;
            } else {
                _toast('Could not list projects: ' + ((result.out && result.out.error) || result.res.status), true);
            }
        } catch (error) {
            _toast('Could not list projects: ' + error.message, true);
        }

        var modal = _element('div', 'position:fixed;inset:0;z-index:100090;background:rgba(3,4,10,0.88);display:flex;align-items:center;justify-content:center;');
        modal.id = 'spbProjectsModal';
        var card = _element('div', 'width:min(560px,92vw);max-height:80vh;display:flex;flex-direction:column;background:var(--bg-card,#0e0e22);border:1px solid var(--border,#2a2a4a);border-radius:12px;padding:14px 16px;');
        var header = _element('div', 'display:flex;align-items:center;margin-bottom:10px;');
        header.appendChild(_element('b', 'font-size:14px;color:var(--text-bright,#f0f0ff);letter-spacing:0.04em;', 'SPB PROJECTS'));
        header.appendChild(_element('span', 'font-size:9px;color:var(--text-dim,#8a96b3);margin-left:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;', directory));
        header.appendChild(_button('💾 SAVE CURRENT', 'Save this exact workflow', async function () {
            if (await saveSpbProject()) openSpbProjects();
        }, 'padding:2px 10px;'));
        header.appendChild(_button('✕ CLOSE', 'Close Projects', closeSpbProjectsModal, 'padding:2px 8px;margin-left:6px;'));
        card.appendChild(header);

        var body = _element('div', 'overflow-y:auto;min-height:60px;');
        if (needsRestart) {
            body.appendChild(_element('div', 'color:#ffcc66;font-size:12px;padding:12px 4px;line-height:1.5;', '⟳ One restart needed. ' + RESTART_MSG));
        } else if (!list.length) {
            body.appendChild(_element('div', 'color:var(--text-dim,#8a96b3);font-size:12px;padding:12px 4px;',
                'No projects yet. SAVE CURRENT captures the open source, every zone, Layer setting, and live Layer pixels.'));
        } else {
            list.forEach(function (project) { body.appendChild(_projectRow(project)); });
        }
        card.appendChild(body);
        modal.appendChild(card);
        modal.addEventListener('click', function (event) {
            if (event.target === modal) closeSpbProjectsModal();
        });
        document.body.appendChild(modal);
    }

    async function deleteSpbProject(file) {
        if (!window.confirm('Delete project "' + file + '"? This cannot be undone.')) return false;
        try {
            var result = await _fetchJson(API + '/delete', {
                method: 'POST', headers: _jsonHeaders(),
                body: JSON.stringify({ file: file }),
            });
            if (result.out && result.out.ok) {
                _toast('Project deleted');
                openSpbProjects();
                return true;
            }
            _toast('Delete failed: ' + ((result.out && result.out.error) || result.res.status), true);
        } catch (error) {
            _toast('Delete failed: ' + error.message, true);
        }
        return false;
    }

    window.saveSpbProject = saveSpbProject;
    window.loadSpbProject = loadSpbProject;
    window.openSpbProjects = openSpbProjects;
    window.deleteSpbProject = deleteSpbProject;
    window.closeSpbProjectsModal = closeSpbProjectsModal;
    window.SPBProjects = Object.freeze({
        schemaVersion: SCHEMA_VERSION,
        buildProjectPayload: buildProjectPayload,
        samePath: _samePath,
        remapProjectConfig: _remapProjectConfig,
    });
})();
