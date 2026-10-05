(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBCanvasMaskGeometry = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    function cloneMask(mask) {
        return mask ? new Uint8Array(mask) : null;
    }

    function resolveZone(zones, item) {
        if (!Array.isArray(zones) || !item) return null;
        if (item.zoneId != null) {
            const byId = zones.find(zone => zone && zone.id === item.zoneId);
            if (byId) return byId;
        }
        return Number.isInteger(item.zoneIndex) ? zones[item.zoneIndex] || null : null;
    }

    function captureZoneMasks(zones) {
        const captured = [];
        (zones || []).forEach((zone, zoneIndex) => {
            if (!zone || (!zone.regionMask && !zone.spatialMask)) return;
            captured.push({
                zoneId: zone.id != null ? zone.id : null,
                zoneIndex,
                regionMask: cloneMask(zone.regionMask),
                spatialMask: cloneMask(zone.spatialMask),
            });
        });
        return captured;
    }

    function restoreZoneMasks(zones, captured) {
        let restored = 0;
        for (const item of captured || []) {
            const zone = resolveZone(zones, item);
            if (!zone) continue;
            zone.regionMask = cloneMask(item.regionMask);
            zone.spatialMask = cloneMask(item.spatialMask);
            restored++;
        }
        return restored;
    }

    function validMask(mask, width, height) {
        return !!mask && mask.length === width * height;
    }

    function flipHorizontal(mask, width, height) {
        if (!validMask(mask, width, height)) return cloneMask(mask);
        const output = new Uint8Array(mask.length);
        for (let y = 0; y < height; y++) {
            const row = y * width;
            for (let x = 0; x < width; x++) output[row + width - 1 - x] = mask[row + x];
        }
        return output;
    }

    function flipVertical(mask, width, height) {
        if (!validMask(mask, width, height)) return cloneMask(mask);
        const output = new Uint8Array(mask.length);
        for (let y = 0; y < height; y++) {
            output.set(mask.subarray(y * width, (y + 1) * width), (height - 1 - y) * width);
        }
        return output;
    }

    function rotateClockwise(mask, width, height) {
        if (!validMask(mask, width, height)) return cloneMask(mask);
        const newWidth = height;
        const output = new Uint8Array(mask.length);
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const newX = height - 1 - y;
                const newY = x;
                output[newY * newWidth + newX] = mask[y * width + x];
            }
        }
        return output;
    }

    function resizeNearest(mask, oldWidth, oldHeight, newWidth, newHeight) {
        if (!validMask(mask, oldWidth, oldHeight)) return cloneMask(mask);
        const output = new Uint8Array(newWidth * newHeight);
        for (let y = 0; y < newHeight; y++) {
            const sourceY = Math.min(oldHeight - 1, Math.floor((y + 0.5) * oldHeight / newHeight));
            for (let x = 0; x < newWidth; x++) {
                const sourceX = Math.min(oldWidth - 1, Math.floor((x + 0.5) * oldWidth / newWidth));
                output[y * newWidth + x] = mask[sourceY * oldWidth + sourceX];
            }
        }
        return output;
    }

    function resizeBilinear(mask, oldWidth, oldHeight, newWidth, newHeight) {
        if (!validMask(mask, oldWidth, oldHeight)) return cloneMask(mask);
        const output = new Uint8Array(newWidth * newHeight);
        const scaleX = oldWidth / newWidth;
        const scaleY = oldHeight / newHeight;
        for (let y = 0; y < newHeight; y++) {
            const sy = Math.max(0, Math.min(oldHeight - 1, (y + 0.5) * scaleY - 0.5));
            const y0 = Math.floor(sy), y1 = Math.min(oldHeight - 1, y0 + 1), fy = sy - y0;
            for (let x = 0; x < newWidth; x++) {
                const sx = Math.max(0, Math.min(oldWidth - 1, (x + 0.5) * scaleX - 0.5));
                const x0 = Math.floor(sx), x1 = Math.min(oldWidth - 1, x0 + 1), fx = sx - x0;
                const top = mask[y0 * oldWidth + x0] * (1 - fx) + mask[y0 * oldWidth + x1] * fx;
                const bottom = mask[y1 * oldWidth + x0] * (1 - fx) + mask[y1 * oldWidth + x1] * fx;
                output[y * newWidth + x] = Math.round(top * (1 - fy) + bottom * fy);
            }
        }
        return output;
    }

    function transformZones(zones, operation, oldWidth, oldHeight, newWidth, newHeight) {
        let changed = 0;
        for (const zone of zones || []) {
            if (!zone) continue;
            if (zone.regionMask) {
                if (operation === 'flip-h') zone.regionMask = flipHorizontal(zone.regionMask, oldWidth, oldHeight);
                else if (operation === 'flip-v') zone.regionMask = flipVertical(zone.regionMask, oldWidth, oldHeight);
                else if (operation === 'rotate-cw') zone.regionMask = rotateClockwise(zone.regionMask, oldWidth, oldHeight);
                else if (operation === 'resize') zone.regionMask = resizeBilinear(zone.regionMask, oldWidth, oldHeight, newWidth, newHeight);
                changed++;
            }
            if (zone.spatialMask) {
                if (operation === 'flip-h') zone.spatialMask = flipHorizontal(zone.spatialMask, oldWidth, oldHeight);
                else if (operation === 'flip-v') zone.spatialMask = flipVertical(zone.spatialMask, oldWidth, oldHeight);
                else if (operation === 'rotate-cw') zone.spatialMask = rotateClockwise(zone.spatialMask, oldWidth, oldHeight);
                else if (operation === 'resize') zone.spatialMask = resizeNearest(zone.spatialMask, oldWidth, oldHeight, newWidth, newHeight);
                changed++;
            }
        }
        return changed;
    }

    return {
        captureZoneMasks, restoreZoneMasks, flipHorizontal, flipVertical,
        rotateClockwise, resizeNearest, resizeBilinear, transformZones,
    };
});
