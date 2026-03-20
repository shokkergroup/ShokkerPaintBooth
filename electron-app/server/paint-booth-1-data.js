// ============================================================
// PAINT-BOOTH-1-DATA.JS - UI logic, TGA decoder, server merge
// ============================================================
// Purpose: Settings dropdown, onboarding hints, TGA decoder,
//          loadDecodedImageToCanvas, server finish-data merge.
// Deps:    paint-booth-0-finish-data.js (BASES, PATTERNS, MONOLITHICS
//          must be defined before this file runs).
// Edit:    TGA decode bugs → decodeTGA. Server merge → _mergeFinishDataFromServer.
//          DO NOT put finish arrays here - they go in 0-finish-data.js.
// See:     PROJECT_STRUCTURE.md in this folder.
// ============================================================

// ===== SETTINGS DROPDOWN =====
function toggleSettingsDropdown() {
    const dd = document.getElementById('settingsDropdown');
    const btn = document.getElementById('settingsGearBtn');
    dd.classList.toggle('open');
    if (btn) btn.classList.toggle('active');
}
// Close settings dropdown when clicking outside
document.addEventListener('click', function (e) {
    const dd = document.getElementById('settingsDropdown');
    const btn = document.getElementById('settingsGearBtn');
    if (dd && dd.classList.contains('open') && !dd.contains(e.target) && btn && !btn.contains(e.target)) {
        dd.classList.remove('open');
        btn.classList.remove('active');
    }
});

// ===== ONBOARDING HINTS =====
let hasRenderedOnce = false;
function updateOnboardingHints() {
    const canvasHint = document.getElementById('canvasHint');
    const renderBtn = document.getElementById('btnRender');
    const canvasInner = document.getElementById('canvasInner');
    const paintLoaded = canvasInner && canvasInner.style.display !== 'none';

    // Canvas hint: show after paint loaded, hide once a zone has a color
    if (canvasHint) {
        const anyZoneHasColor = zones && zones.some(z => z.color !== null || (z.regionMask && z.regionMask.some(v => v > 0)));
        canvasHint.style.display = (paintLoaded && !anyZoneHasColor) ? '' : 'none';
    }

    // Render pulse: show when zones have finishes but haven't rendered yet
    if (renderBtn && !hasRenderedOnce) {
        const anyZoneHasFinish = zones && zones.some(z => z.base || z.finish);
        if (paintLoaded && anyZoneHasFinish) {
            renderBtn.classList.add('pulse');
        } else {
            renderBtn.classList.remove('pulse');
        }
    }
}

// ===== TGA DECODER (browsers can't natively display TGA) =====
function decodeTGA(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    const idLength = view.getUint8(0);
    const colorMapType = view.getUint8(1);
    const imageType = view.getUint8(2);     // 2 = uncompressed RGB, 10 = RLE
    const width = view.getUint16(12, true);  // little-endian
    const height = view.getUint16(14, true);
    const bpp = view.getUint8(16);           // 24 or 32
    const descriptor = view.getUint8(17);
    const topOrigin = (descriptor & 0x20) !== 0; // bit 5 = top-to-bottom

    if (imageType !== 2 && imageType !== 10) {
        throw new Error(`Unsupported TGA type ${imageType}. Only uncompressed (2) and RLE (10) supported.`);
    }
    if (bpp !== 24 && bpp !== 32) {
        throw new Error(`Unsupported TGA depth ${bpp}bpp. Only 24-bit and 32-bit supported.`);
    }

    const bytesPerPixel = bpp / 8;
    const pixelDataOffset = 18 + idLength + (colorMapType ? view.getUint16(5, true) * Math.ceil(view.getUint8(7) / 8) : 0);
    const pixelCount = width * height;

    // Create RGBA output (canvas always wants RGBA)
    const rgba = new Uint8ClampedArray(pixelCount * 4);

    if (imageType === 2) {
        // Uncompressed
        for (let i = 0; i < pixelCount; i++) {
            const srcOff = pixelDataOffset + i * bytesPerPixel;
            const b = view.getUint8(srcOff);
            const g = view.getUint8(srcOff + 1);
            const r = view.getUint8(srcOff + 2);
            const a = bytesPerPixel === 4 ? view.getUint8(srcOff + 3) : 255;
            const dstOff = i * 4;
            rgba[dstOff] = r; rgba[dstOff + 1] = g; rgba[dstOff + 2] = b; rgba[dstOff + 3] = a;
        }
    } else if (imageType === 10) {
        // RLE compressed
        let srcOff = pixelDataOffset;
        let pixelIdx = 0;
        while (pixelIdx < pixelCount) {
            const header = view.getUint8(srcOff++);
            const count = (header & 0x7F) + 1;
            if (header & 0x80) {
                // RLE packet: one pixel repeated
                const b = view.getUint8(srcOff);
                const g = view.getUint8(srcOff + 1);
                const r = view.getUint8(srcOff + 2);
                const a = bytesPerPixel === 4 ? view.getUint8(srcOff + 3) : 255;
                srcOff += bytesPerPixel;
                for (let j = 0; j < count && pixelIdx < pixelCount; j++, pixelIdx++) {
                    const d = pixelIdx * 4;
                    rgba[d] = r; rgba[d + 1] = g; rgba[d + 2] = b; rgba[d + 3] = a;
                }
            } else {
                // Raw packet: N individual pixels
                for (let j = 0; j < count && pixelIdx < pixelCount; j++, pixelIdx++) {
                    const b = view.getUint8(srcOff);
                    const g = view.getUint8(srcOff + 1);
                    const r = view.getUint8(srcOff + 2);
                    const a = bytesPerPixel === 4 ? view.getUint8(srcOff + 3) : 255;
                    srcOff += bytesPerPixel;
                    const d = pixelIdx * 4;
                    rgba[d] = r; rgba[d + 1] = g; rgba[d + 2] = b; rgba[d + 3] = a;
                }
            }
        }
    }

    // If bottom-origin (default TGA), flip vertically
    if (!topOrigin) {
        const rowBytes = width * 4;
        const temp = new Uint8ClampedArray(rowBytes);
        for (let y = 0; y < Math.floor(height / 2); y++) {
            const topRow = y * rowBytes;
            const botRow = (height - 1 - y) * rowBytes;
            temp.set(rgba.subarray(topRow, topRow + rowBytes));
            rgba.copyWithin(topRow, botRow, botRow + rowBytes);
            rgba.set(temp, botRow);
        }
    }

    return { width, height, bpp, rgba };
}

// Load decoded TGA (or any image) data into the paint preview canvas
function loadDecodedImageToCanvas(width, height, rgbaData, fileName) {
    const canvas = document.getElementById('paintCanvas');
    const ctx = canvas.getContext('2d');
    canvas.width = width;
    canvas.height = height;
    const imgData = new ImageData(rgbaData, width, height);
    ctx.putImageData(imgData, 0, 0);
    paintImageData = ctx.getImageData(0, 0, width, height);
    // Also size region canvas
    const regionCanvas = document.getElementById('regionCanvas');
    regionCanvas.width = width;
    regionCanvas.height = height;

    // Show/hide elements for new 3-column layout
    const emptyBig = document.getElementById('paintPreviewEmptyBig');
    if (emptyBig) emptyBig.style.display = 'none';
    const empty2 = document.getElementById('paintPreviewEmpty2');
    if (empty2) empty2.style.display = 'none';
    document.getElementById('paintPreviewLoaded').style.display = 'flex';
    /* advancedToolbar moved to vertical toolbar */
    const edInfo1 = document.getElementById('eyedropperInfo'); if (edInfo1) edInfo1.style.display = 'block';
    document.getElementById('paintPreviewStatus').textContent = `(${width}x${height})`;
    document.getElementById('paintDimensions').textContent = `${width}x${height}`;
    const canvasInner = document.getElementById('canvasInner');
    if (canvasInner) canvasInner.style.display = 'block';
    const zoomCtrl = document.getElementById('zoomControls');
    if (zoomCtrl) zoomCtrl.style.display = 'flex';

    setupCanvasHandlers(canvas);
    canvasZoom('fit');
    // Capture before image for Before/After comparison
    if (typeof captureBeforeImage === 'function') captureBeforeImage();
    showToast(`Loaded ${fileName} (${width}x${height}, TGA decoded)`);
}

// =============================================================================
// FINISH DATA - paint-booth-1-data.js is the single source of truth
// =============================================================================
// This file defines BASES, PATTERNS, MONOLITHICS, BASE_GROUPS, PATTERN_GROUPS,
// SPECIAL_GROUPS, and all supporting data.
//
// ➤ TO ADD A NEW FINISH: edit HERE, then run copy-server.
// ➤ See SHOKKER_BIBLE.md + FINISH_WIRING_CHECKLIST.md for the full ID contract.
// =============================================================================

async function _mergeFinishDataFromServer() {
    try {
        // Populate from static arrays first (offline / before server responds)
        FINISH_TYPE_BY_ID = {};
        BASES.forEach(b => { FINISH_TYPE_BY_ID[b.id] = 'base'; });
        PATTERNS.forEach(p => { FINISH_TYPE_BY_ID[p.id] = 'pattern'; });
        MONOLITHICS.forEach(m => { FINISH_TYPE_BY_ID[m.id] = 'monolithic'; });

        const res = await fetch('/api/finish-data?v=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) return;
        const data = await res.json();
        // Server may send { bases, patterns, specials } (no status) or { status: 'ok', ... }
        if (data.status !== undefined && data.status !== 'ok') return;

        function _normalize(item, defaultType) {
            if (typeof item === 'string') {
                const id = item;
                const name = id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                return { id, name, type: defaultType, category: '', swatch: '#888888' };
            }
            return { id: item.id, name: item.name, type: item.type || defaultType, category: item.category || '', swatch: item.swatch || '#888888' };
        }
        function _merge(staticArr, serverArr, defaultType, allowAdd) {
            if (!serverArr || !serverArr.length) return;
            const existing = new Set(staticArr.map(f => f.id));
            let added = 0;
            for (const item of serverArr) {
                const o = _normalize(item, defaultType);
                FINISH_TYPE_BY_ID[o.id] = o.type;
                if (allowAdd && !existing.has(o.id)) {
                    staticArr.push({ id: o.id, name: o.name, desc: o.category, swatch: o.swatch });
                    existing.add(o.id);
                    added++;
                }
            }
            if (added > 0) console.log(`[FinishData] Merged ${added} new entries from server`);
        }

        // Alpha UX: keep curated local finish lists stable; do not auto-inject extra server-only IDs.
        _merge(BASES, data.bases, 'base', false);
        _merge(PATTERNS, data.patterns, 'pattern', false);
        _merge(MONOLITHICS, data.specials || data.monolithics, 'monolithic', false);

        // Re-render finish library so new entries appear
        if (typeof renderFinishLibrary === 'function') renderFinishLibrary();
        if (typeof buildFinishBrowser === 'function') buildFinishBrowser();
        if (typeof populateBaseDropdown === 'function') populateBaseDropdown();

    } catch (e) {
        console.warn('[FinishData] Server merge skipped (offline?):', e.message);
    }
}

// ── Fire the server merge now that all arrays (from 0-finish-data.js) AND
//    this function are both defined. Rebuild FINISHES after merge. ──────
_mergeFinishDataFromServer().then(() => {
    // Rebuild flat FINISHES so search / compare / browser see new entries
    FINISHES.length = 0;
    FINISHES.push(
        ...BASES.map(b => ({ ...b, cat: "Base" })),
        ...PATTERNS.filter(p => p.id !== "none").map(p => ({ ...p, cat: "Pattern" })),
        ...MONOLITHICS.map(m => ({ ...m, cat: "Special" })),
    );
});
