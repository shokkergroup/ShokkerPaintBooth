// SPB-93 tools 2026-09-07: share thumbnail rendering between full panel updates
// and paint commits. A stroke changes pixels, not the layer-control DOM.
(function (root) {
    'use strict';
    root.SPBLayerThumbnail = {
        draw(layer, thumb, cache, size, key) {
            if (!thumb || !layer?.img) return false;
            const hit = cache.get(layer.id);
            if (hit && hit.img === layer.img && hit.key === key) {
                thumb.getContext('2d').drawImage(hit.canvas, 0, 0);
                return true;
            }
            const off = document.createElement('canvas');
            off.width = size; off.height = size;
            const ctx = off.getContext('2d');
            ctx.fillStyle = '#222'; ctx.fillRect(0, 0, size, size);
            ctx.fillStyle = '#333';
            for (let y = 0; y < size; y += 4) for (let x = (y % 8 === 0 ? 0 : 4); x < size; x += 8) ctx.fillRect(x, y, 4, 4);
            const [x1, y1, x2, y2] = layer.bbox || [0, 0, layer.img.width || size, layer.img.height || size];
            const width = (x2 - x1) || layer.img.width || size, height = (y2 - y1) || layer.img.height || size;
            const scale = Math.min(size / width, size / height), dw = width * scale, dh = height * scale;
            try {
                const filter = root.SPBLayerClippingMask?.adjustFilterFor?.(layer);
                if (filter) ctx.filter = filter;
                ctx.drawImage(layer.img, 0, 0, layer.img.width || width, layer.img.height || height, (size - dw) / 2, (size - dh) / 2, dw, dh);
            } catch (_) { /* Preserve the checkerboard if the image is not drawable. */ }
            ctx.filter = 'none';
            cache.set(layer.id, { img: layer.img, key, canvas: off });
            thumb.getContext('2d').drawImage(off, 0, 0);
            return true;
        }
    };
})(window);
