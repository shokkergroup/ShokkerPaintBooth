(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBZoneMaskHistory = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function cloneMask(mask) {
        return mask ? new Uint8Array(mask) : null;
    }

    function masksEqual(left, right) {
        if (left === right) return true;
        if (!left || !right || left.length !== right.length) return false;
        for (let index = 0; index < left.length; index++) {
            if (left[index] !== right[index]) return false;
        }
        return true;
    }

    function horizontalMirrorDiffers(mask, widthValue, heightValue) {
        const width = Math.max(0, Math.floor(Number(widthValue) || 0));
        const height = Math.max(0, Math.floor(Number(heightValue) || 0));
        if (!mask || width * height !== mask.length) return false;
        for (let y = 0; y < height; y++) {
            const row = y * width;
            for (let x = 0; x < Math.floor(width / 2); x++) {
                if (mask[row + x] !== mask[row + width - 1 - x]) return true;
            }
        }
        return false;
    }

    function resolveZone(zones, item) {
        if (!Array.isArray(zones) || !item) return null;
        if (item.zoneId != null) {
            const byId = zones.find(zone => zone && zone.id === item.zoneId);
            if (byId) return byId;
        }
        return Number.isInteger(item.zoneIndex) ? zones[item.zoneIndex] || null : null;
    }

    function capture(zones, zoneIndexes, label) {
        const masks = [];
        const seen = new Set();
        for (const value of zoneIndexes || []) {
            const zoneIndex = Number(value);
            if (!Number.isInteger(zoneIndex) || seen.has(zoneIndex)) continue;
            const zone = Array.isArray(zones) ? zones[zoneIndex] : null;
            if (!zone) continue;
            seen.add(zoneIndex);
            masks.push({
                zoneId: zone.id != null ? zone.id : null,
                zoneIndex,
                prevMask: cloneMask(zone.regionMask),
            });
        }
        return masks.length ? {
            batchMasks: masks,
            label: label || 'Zone mask change',
        } : null;
    }

    function captureReciprocal(zones, entry) {
        if (!entry || !Array.isArray(entry.batchMasks)) return null;
        const masks = [];
        for (const item of entry.batchMasks) {
            const zone = resolveZone(zones, item);
            if (!zone) continue;
            masks.push({
                zoneId: zone.id != null ? zone.id : item.zoneId,
                zoneIndex: Array.isArray(zones) ? zones.indexOf(zone) : item.zoneIndex,
                prevMask: cloneMask(zone.regionMask),
            });
        }
        return masks.length ? {
            batchMasks: masks,
            label: entry.label || 'Zone mask change',
        } : null;
    }

    function restore(zones, entry) {
        if (!entry || !Array.isArray(entry.batchMasks)) return 0;
        let restored = 0;
        for (const item of entry.batchMasks) {
            const zone = resolveZone(zones, item);
            if (!zone) continue;
            zone.regionMask = cloneMask(item.prevMask);
            restored++;
        }
        return restored;
    }

    return {
        capture,
        captureReciprocal,
        restore,
        resolveZone,
        masksEqual,
        horizontalMirrorDiffers,
    };
});
