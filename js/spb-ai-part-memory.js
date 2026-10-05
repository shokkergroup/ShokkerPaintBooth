/* Proposed, uninstalled durable part-memory schema. No app hooks live here. */
(function (root, factory) {
    'use strict';
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SpbAIPartMemory = api;
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : null), function () {
    'use strict';
    var SCHEMA = 'spb-ai-part-memory/1';
    var MASK_KEY = /(mask|vector|pixel|image|bitmap|data)/i;

    function ownKeys(obj) { return Object.keys(obj || {}); }
    function exactKeys(obj, expected) {
        if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return false;
        var keys = ownKeys(obj);
        if (keys.length !== expected.length) return false;
        for (var i = 0; i < keys.length; i++) if (expected.indexOf(keys[i]) < 0) return false;
        return true;
    }
    function nonempty(value, max) { return typeof value === 'string' && value.trim().length > 0 && value.length <= max; }
    function positiveInt(value) { return typeof value === 'number' && isFinite(value) && value > 0 && Math.floor(value) === value; }
    function runtimeSource(source, proof) {
        if (!source || source.committed !== true || !nonempty(source.path, 1024) || !nonempty(source.fingerprint, 256) ||
            !positiveInt(source.width) || !positiveInt(source.height) || !positiveInt(source.generation) ||
            !proof || typeof proof.isCommittedSource !== 'function') return false;
        try { return proof.isCommittedSource(source) === true; } catch (e) { return false; }
    }
    function copySelector(value, depth) {
        if (depth > 5) return null;
        if (value === null || typeof value === 'boolean') return value;
        if (typeof value === 'string') return value.length <= 256 ? value : null;
        if (typeof value === 'number') return isFinite(value) ? value : null;
        if (!value || typeof value !== 'object') return null;
        if (Array.isArray(value)) {
            if (value.length > 64) return null;
            var arr = [];
            for (var i = 0; i < value.length; i++) {
                var item = copySelector(value[i], depth + 1);
                if (item === null && value[i] !== null) return null;
                arr.push(item);
            }
            return arr;
        }
        // Typed arrays, DOM objects, and class instances are not JSON selectors.
        if (typeof value.length === 'number' || Object.prototype.toString.call(value) !== '[object Object]') return null;
        var keys = ownKeys(value), out = {};
        if (keys.length > 32) return null;
        for (var k = 0; k < keys.length; k++) {
            var key = keys[k];
            if (MASK_KEY.test(key) || key === '__proto__' || key === 'constructor') return null;
            var next = copySelector(value[key], depth + 1);
            if (next === null && value[key] !== null) return null;
            out[key] = next;
        }
        return out;
    }
    function selectorFromLive(p) {
        if (!p || !nonempty(p.r, 8192)) return null;
        var parsed;
        try { parsed = JSON.parse(p.r); } catch (e) { return null; }
        var region = copySelector(parsed, 0);
        if (!region || (!nonempty(region.part, 128) && !nonempty(region.island, 128))) return null;
        var json;
        try { json = JSON.stringify(region); } catch (e2) { return null; }
        return json && json.length <= 8192 ? { object: region, json: json } : null;
    }
    function validLiveProvenance(p) {
        return !!selectorFromLive(p) && nonempty(p.z, 80) && /^\d+:[0-9a-z]+$/i.test(p.z) &&
            nonempty(p.p, 80) && /^\d+:[0-9a-z]+$/i.test(p.p) && nonempty(p.l, 512) &&
            typeof p.e === 'string' && p.e.length <= 512;
    }
    function currentProof(zone, source, proof, key) {
        if (!proof || typeof proof.partOwnerCurrent !== 'function' || typeof proof.partMaskCurrent !== 'function' || typeof proof.countOwners !== 'function') return false;
        try { return proof.partOwnerCurrent(zone, zone._aiPartProv, key, source) === true &&
            proof.partMaskCurrent(zone, zone._aiPartProv, key, source) === true && proof.countOwners(key, zone.id) === 1; }
        catch (e) { return false; }
    }
    function recordShape(record) {
        if (!exactKeys(record, ['schema', 'source', 'owner', 'provenance']) || record.schema !== SCHEMA) return null;
        if (!exactKeys(record.source, ['path', 'fingerprint', 'width', 'height']) ||
            !nonempty(record.source.path, 1024) || !nonempty(record.source.fingerprint, 256) ||
            !positiveInt(record.source.width) || !positiveInt(record.source.height)) return null;
        if (!exactKeys(record.owner, ['zoneId', 'name', 'key']) || !nonempty(record.owner.zoneId, 128) ||
            !nonempty(record.owner.name, 160) || !nonempty(record.owner.key, 2048)) return null;
        if (!exactKeys(record.provenance, ['r', 'z', 'p', 'l', 'e']) || !validLiveProvenance(record.provenance)) return null;
        var selector = selectorFromLive(record.provenance);
        return {
            schema: SCHEMA,
            source: { path: record.source.path, fingerprint: record.source.fingerprint, width: record.source.width, height: record.source.height },
            owner: { zoneId: record.owner.zoneId, name: record.owner.name, key: record.owner.key },
            provenance: { r: selector.json, z: record.provenance.z, p: record.provenance.p, l: record.provenance.l, e: record.provenance.e }
        };
    }
    function saveRecord(zone, source, proof) {
        if (!runtimeSource(source, proof) || !zone || zone.muted || zone.useRegion !== true || !zone.regionMask ||
            !nonempty(zone.id == null ? '' : String(zone.id), 128) || !nonempty(zone.name, 160)) return null;
        var selector = selectorFromLive(zone._aiPartProv);
        if (!selector || !validLiveProvenance(zone._aiPartProv) || !proof || typeof proof.editKey !== 'function') return null;
        var key;
        try { key = proof.editKey(selector.object); } catch (e) { return null; }
        if (!nonempty(key, 2048) || !currentProof(zone, source, proof, key)) return null;
        return {
            schema: SCHEMA,
            source: { path: source.path, fingerprint: source.fingerprint, width: source.width, height: source.height },
            owner: { zoneId: String(zone.id), name: String(zone.name), key: key },
            provenance: { r: selector.json, z: zone._aiPartProv.z, p: zone._aiPartProv.p, l: zone._aiPartProv.l, e: zone._aiPartProv.e }
        };
    }
    function prepareRestore(saved, current, zone, proof) {
        var record = recordShape(saved);
        if (!record || !runtimeSource(current, proof) || !zone || zone.muted || zone.useRegion !== true || !zone.regionMask) return null;
        if (!proof || typeof proof.sameSourcePath !== 'function' || typeof proof.editKey !== 'function' ||
            typeof proof.partOwnerCurrent !== 'function' || typeof proof.partMaskCurrent !== 'function' || typeof proof.countOwners !== 'function') return null;
        var samePath = false, key;
        try { samePath = proof.sameSourcePath(record.source.path, current.path) === true; key = proof.editKey(JSON.parse(record.provenance.r)); } catch (e) { return null; }
        if (!samePath || record.source.fingerprint !== current.fingerprint || record.source.width !== current.width ||
            record.source.height !== current.height || record.owner.zoneId !== String(zone.id) || record.owner.name !== String(zone.name) ||
            record.owner.key !== key) return null;
        var prov = { r: record.provenance.r, z: record.provenance.z, p: record.provenance.p, l: record.provenance.l, e: record.provenance.e };
        var live = false, partMask = false, owners = 0;
        try {
            live = proof.partOwnerCurrent(zone, prov, key, current) === true;
            partMask = proof.partMaskCurrent(zone, prov, key, current) === true;
            owners = proof.countOwners(key, zone.id, prov);
        } catch (e2) { return null; }
        if (!live || !partMask || owners !== 1) return null;
        return {
            ok: true, authorizedByCurrentOwnerProof: true,
            zoneId: record.owner.zoneId, ownerName: record.owner.name, ownerKey: key,
            provenance: prov,
            runtimeBinding: { sourcePath: current.path, fingerprint: current.fingerprint, generation: current.generation }
        };
    }
    return Object.freeze({ schema: SCHEMA, saveRecord: saveRecord, sanitizeRecord: recordShape, prepareRestore: prepareRestore });
}));
