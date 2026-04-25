// ============================================================
// PAINT-BOOTH-4-PATTERN-RENDERER.JS - Client-side finish preview
// ============================================================
// Purpose: Canvas renderers for every finish (base, pattern, special) used for
//          small preview swatches in the UI. Large file - search by finish id.
// Deps:    paint-booth-1-data.js (finish ids). Called by UI that shows previews.
//          fusion-swatches.js / swatch-upgrades*.js populate
//          window._fusionSwatchRenderers which this file consults first.
// Edit:    Add/change a client preview for a finish -> baseFns, patternFns, or
//          the big specials object; search for finish id or "FINISH PATTERN PREVIEW".
// See:     PROJECT_STRUCTURE.md in this folder.
// Swatch size conventions (kept for visual regression parity):
//   - Detail / hero swatch: 96x96
//   - Picker tile        : 48x48
//   - Zone chip          : 24x24
// Version: 2026-04-17
// ============================================================

// ===== FINISH PATTERN PREVIEW RENDERER (Client-side) =====
// Renders miniature versions of each texture/base to canvas for visual preview.
/** @type {Object.<string, ImageData>} finishId_swatch -> cached ImageData */
const _previewCache = {};
/** @type {Object.<string, HTMLImageElement>} url -> loaded image for image-based swatches */
const _imagePatternCache = {};

/**
 * Standard swatch dimensions used across the UI. Keeping these as constants
 * prevents "every dev picks their own size" drift.
 * @type {{detail: number, picker: number, chip: number}}
 */
const SWATCH_SIZES = Object.freeze({ detail: 96, picker: 48, chip: 24 });

/**
 * Paints an image-based pattern swatch from a URL. Async: if the image isn't
 * cached yet, we draw a dark placeholder and swap in the real image onload.
 * Falls back to an X-cross if the image fails to load.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} w
 * @param {number} h
 * @param {string} imageUrl - relative or absolute URL.
 * @returns {void}
 */
function renderImagePatternSwatch(ctx, w, h, imageUrl) {
    // Dark background so white patterns are visible
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, w, h);
    const base = (typeof window !== 'undefined' && window.location && window.location.origin) ? window.location.origin : '';
    const fullUrl = imageUrl.startsWith('http') ? imageUrl : (base + (imageUrl.startsWith('/') ? '' : '/') + imageUrl);
    const cached = _imagePatternCache[fullUrl];
    if (cached && cached.complete && cached.naturalWidth > 0) {
        ctx.drawImage(cached, 0, 0, w, h);
        return;
    }
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function () {
        _imagePatternCache[fullUrl] = img;
        ctx.drawImage(img, 0, 0, w, h);
    };
    img.onerror = function () {
        ctx.strokeStyle = '#444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, 0); ctx.lineTo(w, h);
        ctx.moveTo(w, 0); ctx.lineTo(0, h);
        ctx.stroke();
    };
    img.src = fullUrl;
}

/**
 * Main entry: paints a finish preview onto an already-sized canvas context.
 * Resolution order:
 *   1. window._fusionSwatchRenderers (populated by fusion-swatches + upgrades)
 *   2. local baseFns / patternFns / specials tables (below)
 *   3. Fallback: a flat neutral fill so something is always shown.
 * Deterministic: same (finishId, w, h) -> same pixels.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} w
 * @param {number} h
 * @param {string} finishId
 * @param {string} [bgColor] - optional CSS color to use as the neutral background.
 * @returns {void}
 */
function renderPatternPreview(ctx, w, h, finishId, bgColor) {
    // Use a neutral-ish background to show the pattern clearly
    const bg = bgColor || '#4a4a5a';
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    // --- BASE MATERIALS ---
    const baseFns = {
        gloss: (ctx, w, h) => {
            // Smooth gradient showing reflective clearcoat
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#6a8a6a'); g.addColorStop(0.3, '#4a6a4a');
            g.addColorStop(0.6, '#8aaa8a'); g.addColorStop(1, '#5a7a5a');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Subtle highlight band
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.6);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.12)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.12)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        matte: (ctx, w, h) => {
            ctx.fillStyle = '#666'; ctx.fillRect(0, 0, w, h);
            // Subtle noise
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = (Math.random() - 0.5) * 15;
                id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
            }
            ctx.putImageData(id, 0, 0);
        },
        satin: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#888'); g.addColorStop(0.5, '#9a9a9a'); g.addColorStop(1, '#7a7a7a');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, h * 0.2, w, h * 0.6);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.06)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.06)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        metallic: (ctx, w, h) => {
            ctx.fillStyle = '#8a9aaa'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const spark = Math.random() > 0.92 ? 40 : (Math.random() - 0.5) * 20;
                id.data[i] += spark; id.data[i + 1] += spark; id.data[i + 2] += spark + 5;
            }
            ctx.putImageData(id, 0, 0);
        },
        pearl: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#d8dce8'); g.addColorStop(0.3, '#e8dce0');
            g.addColorStop(0.6, '#dce8e4'); g.addColorStop(1, '#e0dce8');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.35, 'rgba(255,255,255,0.15)');
            hl.addColorStop(0.55, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#bbb'); g.addColorStop(0.2, '#fff');
            g.addColorStop(0.4, '#999'); g.addColorStop(0.6, '#eee');
            g.addColorStop(0.8, '#aaa'); g.addColorStop(1, '#ddd');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        candy: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#cc2244'); g.addColorStop(0.35, '#aa1a3a');
            g.addColorStop(0.65, '#dd3355'); g.addColorStop(1, '#bb2040');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.35, 'rgba(255,255,255,0.14)');
            hl.addColorStop(0.55, 'rgba(255,255,255,0.14)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        satin_metal: (ctx, w, h) => {
            ctx.fillStyle = '#8899aa'; ctx.fillRect(0, 0, w, h);
            // Horizontal grain lines
            ctx.strokeStyle = 'rgba(180,195,210,0.2)'; ctx.lineWidth = 0.5;
            for (let y = 0; y < h; y += 2) {
                ctx.beginPath(); ctx.moveTo(0, y + (Math.random() - 0.5) * 0.5);
                ctx.lineTo(w, y + (Math.random() - 0.5) * 0.5); ctx.stroke();
            }
        },
        brushed_titanium: (ctx, w, h) => {
            ctx.fillStyle = '#778899'; ctx.fillRect(0, 0, w, h);
            // Heavy directional grain
            for (let y = 0; y < h; y++) {
                const bright = 120 + Math.random() * 60;
                ctx.strokeStyle = `rgba(${bright},${bright + 10},${bright + 20},0.35)`;
                ctx.lineWidth = 0.8;
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }
        },
        anodized: (ctx, w, h) => {
            ctx.fillStyle = '#6688aa'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = (Math.random() - 0.5) * 30;
                id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n + 5;
            }
            ctx.putImageData(id, 0, 0);
        },
        frozen: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#99bbcc'); g.addColorStop(0.5, '#bbddee');
            g.addColorStop(1, '#aaccdd');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = (Math.random() - 0.5) * 25;
                id.data[i] += n; id.data[i + 1] += n + 3; id.data[i + 2] += n + 8;
            }
            ctx.putImageData(id, 0, 0);
        },
        blackout: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = Math.random() * 8;
                id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Expansion Pack Bases ---
        ceramic: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#4477aa'); g.addColorStop(0.3, '#5588bb');
            g.addColorStop(0.6, '#6699cc'); g.addColorStop(1, '#4a88aa');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.35, 'rgba(255,255,255,0.2)');
            hl.addColorStop(0.55, 'rgba(255,255,255,0.2)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        satin_wrap: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#707080'); g.addColorStop(0.5, '#808090'); g.addColorStop(1, '#6a6a7a');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, h * 0.2, w, h * 0.6);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.05)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.05)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        primer: (ctx, w, h) => {
            ctx.fillStyle = '#787878'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = (Math.random() - 0.5) * 12;
                id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
            }
            ctx.putImageData(id, 0, 0);
        },
        gunmetal: (ctx, w, h) => {
            ctx.fillStyle = '#3a4555'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const spark = Math.random() > 0.93 ? 30 : (Math.random() - 0.5) * 15;
                id.data[i] += spark; id.data[i + 1] += spark + 3; id.data[i + 2] += spark + 8;
            }
            ctx.putImageData(id, 0, 0);
        },
        copper: (ctx, w, h) => {
            ctx.fillStyle = '#aa6633'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const spark = Math.random() > 0.9 ? 35 : (Math.random() - 0.5) * 20;
                id.data[i] += spark + 5; id.data[i + 1] += spark - 3; id.data[i + 2] += spark - 10;
            }
            ctx.putImageData(id, 0, 0);
        },
        chameleon: (ctx, w, h) => {
            // Rainbow color bands (high frequency hue rotation)
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const angle = Math.sin(py * 0.5 + px * 0.3) * 0.4 + Math.sin(py * 0.25 - px * 0.4) * 0.3 + Math.sin((py + px) * 0.2) * 0.2;
                    const hue = ((angle + 1) * 0.5) * 360;
                    const [r, g, b] = _hslToRgb(hue % 360, 55, 52);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Candy & Pearl Bases ---
        candy_burgundy: (ctx, w, h) => {
            ctx.fillStyle = '#881133'; ctx.fillRect(0, 0, w, h);
            // Deep candy darkening + sparkle
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, 'rgba(100,10,30,0.4)'); g.addColorStop(0.5, 'rgba(160,20,50,0.3)'); g.addColorStop(1, 'rgba(90,10,25,0.4)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7710); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { if (rng() > 0.90) { id.data[i] += 50; id.data[i + 1] += 30; id.data[i + 2] += 20; } }
            ctx.putImageData(id, 0, 0);
        },
        candy_cobalt: (ctx, w, h) => {
            ctx.fillStyle = '#1a2266'; ctx.fillRect(0, 0, w, h);
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, 'rgba(20,30,120,0.4)'); g.addColorStop(0.5, 'rgba(30,50,180,0.3)'); g.addColorStop(1, 'rgba(15,25,100,0.4)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7711); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { if (rng() > 0.90) { id.data[i] += 20; id.data[i + 1] += 30; id.data[i + 2] += 60; } }
            ctx.putImageData(id, 0, 0);
        },
        candy_emerald: (ctx, w, h) => {
            ctx.fillStyle = '#114422'; ctx.fillRect(0, 0, w, h);
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, 'rgba(10,80,30,0.4)'); g.addColorStop(0.5, 'rgba(20,140,50,0.3)'); g.addColorStop(1, 'rgba(8,70,25,0.4)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7712); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { if (rng() > 0.90) { id.data[i] += 20; id.data[i + 1] += 50; id.data[i + 2] += 20; } }
            ctx.putImageData(id, 0, 0);
        },
        moonstone: (ctx, w, h) => {
            // Milky white with iridescent color pearls
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#d8dce8'); g.addColorStop(0.3, '#e4e0e8'); g.addColorStop(0.6, '#dce8e4'); g.addColorStop(1, '#e4dce8');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7713); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                if (rng() > 0.92) { id.data[i] += 20; id.data[i + 1] += 15; id.data[i + 2] += 25; }
                const n = (rng() - 0.5) * 15; id.data[i] += n; id.data[i + 1] += n + 3; id.data[i + 2] += n + 6;
            }
            ctx.putImageData(id, 0, 0);
        },
        opal: (ctx, w, h) => {
            // Multi-color internal play
            const id = ctx.createImageData(w, h); const rng = _seededRng(7714);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const n = Math.sin(py * 0.2 + px * 0.15) * 0.3 + Math.sin(py * 0.1 - px * 0.2) * 0.2 + 0.5;
                    const r = Math.floor(160 + n * 60 + (rng() > 0.90 ? 40 : 0));
                    const g = Math.floor(180 + (1 - n) * 50 + (rng() > 0.90 ? 35 : 0));
                    const b = Math.floor(200 + Math.sin(n * 4) * 40 + (rng() > 0.90 ? 45 : 0));
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.min(255, r); id.data[idx + 1] = Math.min(255, g); id.data[idx + 2] = Math.min(255, b); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        tri_coat_pearl: (ctx, w, h) => {
            // Pearl white with sparkle + directional sheen
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#dde0ee'); g.addColorStop(0.3, '#eee8f0'); g.addColorStop(0.6, '#e0eaef'); g.addColorStop(1, '#e8e0ee');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Directional sheen band
            const hl = ctx.createLinearGradient(0, h * 0.2, 0, h * 0.5);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.15)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
            // Dense sparkle
            const rng = _seededRng(7715); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                if (rng() > 0.88) { const s = 15 + Math.floor(rng() * 30); id.data[i] += s; id.data[i + 1] += s - 2; id.data[i + 2] += s + 3; }
            }
            ctx.putImageData(id, 0, 0);
        },
        iridescent: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const angle = Math.sin(py * 0.3 + px * 0.2) * 0.4 + Math.sin(py * 0.15 - px * 0.25) * 0.3;
                    const hue = ((angle + 1) * 0.5) * 360;
                    const [r, g, b] = _hslToRgb(hue % 360, 35, 65);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Industrial & Tactical Bases ---
        mil_spec_od: (ctx, w, h) => {
            ctx.fillStyle = '#4a5038'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7900); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 8; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        mil_spec_tan: (ctx, w, h) => {
            ctx.fillStyle = '#b8a080'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7901); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 8; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        armor_plate: (ctx, w, h) => {
            ctx.fillStyle = '#505558'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7902); ctx.strokeStyle = 'rgba(100,105,110,0.15)'; ctx.lineWidth = 0.5;
            for (let y = 0; y < h; y += 3) { const x1 = rng() * 5; ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(w - x1, y); ctx.stroke(); }
        },
        submarine_black: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0c'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(20,20,25,0.4)'; ctx.lineWidth = 0.5;
            for (let x = 0; x < w; x += 6) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = 0; y < h; y += 6) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        gunship_gray: (ctx, w, h) => {
            // Pure draw - no getImageData (would corrupt paint canvas)
            ctx.fillStyle = '#606468'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7903);
            for (let i = 0; i < 40; i++) {
                const v = Math.floor((rng() - 0.5) * 12);
                const c = 96 + v;
                ctx.fillStyle = `rgba(${c},${c},${c + 1},0.25)`;
                ctx.fillRect(rng() * w, rng() * h, 1 + rng(), 1 + rng());
            }
        },
        battleship_gray: (ctx, w, h) => {
            ctx.fillStyle = '#6a7078'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7904);
            for (let i = 0; i < 30; i++) {
                ctx.fillStyle = `rgba(55,60,65,${0.2 + rng() * 0.3})`;
                ctx.fillRect(rng() * w, rng() * h, 1 + rng() * 2, 1 + rng() * 2);
            }
        },
        // --- Metallic Standard Flake Bases (pure canvas drawing - NO getImageData) ---
        // RULE: These renderers are called on the full paint canvas during zone rendering.
        // getImageData reads & corrupts existing paint pixels. Always use drawing primitives.
        original_metal_flake: (ctx, w, h) => {
            // Classic heavy coarse metalflake - warm silver-gray with big bright dot flakes
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#888890'); g.addColorStop(0.5, '#a8a8b0'); g.addColorStop(1, '#888890');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1977);
            const numFlakes = Math.ceil(w * h * 0.18); // 18% coverage - coarse & heavy
            for (let i = 0; i < numFlakes; i++) {
                const bright = 160 + rng() * 90;
                const sz = rng() > 0.7 ? 2 : 1; // larger flakes for coarse look
                ctx.fillStyle = `rgba(${bright},${bright - 4},${bright - 8},${0.5 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        champagne_flake: (ctx, w, h) => {
            // Warm gold-champagne base with coarse warm flakes
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#a88850'); g.addColorStop(0.4, '#c0a060'); g.addColorStop(0.6, '#ccaa68'); g.addColorStop(1, '#a88850');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1978);
            const numFlakes = Math.ceil(w * h * 0.16);
            for (let i = 0; i < numFlakes; i++) {
                const bright = 150 + rng() * 95;
                const sz = rng() > 0.72 ? 2 : 1;
                ctx.fillStyle = `rgba(${bright},${bright - 10},${bright - 30},${0.5 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        fine_silver_flake: (ctx, w, h) => {
            // Dense bright micro-silver - much more coverage, smaller flakes
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#b8bcc4'); g.addColorStop(0.5, '#d0d4dc'); g.addColorStop(1, '#b8bcc4');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1979);
            const numFlakes = Math.ceil(w * h * 0.35); // dense coverage, all 1px
            for (let i = 0; i < numFlakes; i++) {
                const bright = 190 + rng() * 60;
                ctx.fillStyle = `rgba(${bright},${bright},${bright + 3},${0.4 + rng() * 0.6})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), 1, 1);
            }
        },
        blue_ice_flake: (ctx, w, h) => {
            // Cool blue-chrome coarse metalflake
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#5870a0'); g.addColorStop(0.4, '#7090b8'); g.addColorStop(0.6, '#80a0c8'); g.addColorStop(1, '#5870a0');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1980);
            const numFlakes = Math.ceil(w * h * 0.16);
            for (let i = 0; i < numFlakes; i++) {
                const bright = 145 + rng() * 100;
                const sz = rng() > 0.72 ? 2 : 1;
                ctx.fillStyle = `rgba(${bright - 15},${bright - 5},${bright + 10},${0.5 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        bronze_flake: (ctx, w, h) => {
            // Warm copper-bronze heavy metalflake
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#7a5228'); g.addColorStop(0.4, '#986038'); g.addColorStop(0.6, '#a87040'); g.addColorStop(1, '#7a5228');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1981);
            const numFlakes = Math.ceil(w * h * 0.17);
            for (let i = 0; i < numFlakes; i++) {
                const bright = 150 + rng() * 100;
                const sz = rng() > 0.70 ? 2 : 1;
                ctx.fillStyle = `rgba(${bright},${bright - 20},${bright - 50},${0.5 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        gunmetal_flake: (ctx, w, h) => {
            // Dark gunmetal - dark base, rare ultra-bright flakes that pop hard
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#303840'); g.addColorStop(0.5, '#404850'); g.addColorStop(1, '#303840');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1982);
            const numFlakes = Math.ceil(w * h * 0.12); // fewer flakes but very bright
            for (let i = 0; i < numFlakes; i++) {
                const bright = 170 + rng() * 85;
                const sz = rng() > 0.72 ? 2 : 1;
                ctx.fillStyle = `rgba(${bright},${bright + 2},${bright + 5},${0.6 + rng() * 0.4})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        green_flake: (ctx, w, h) => {
            // Classic emerald-green coarse metalflake (70s drag car)
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#285038'); g.addColorStop(0.4, '#386848'); g.addColorStop(0.6, '#487858'); g.addColorStop(1, '#285038');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1983);
            const numFlakes = Math.ceil(w * h * 0.17);
            for (let i = 0; i < numFlakes; i++) {
                const bright = 140 + rng() * 100;
                const sz = rng() > 0.70 ? 2 : 1;
                ctx.fillStyle = `rgba(${bright - 30},${bright},${bright - 20},${0.5 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        fire_flake: (ctx, w, h) => {
            // Orange-red coarse hot-rod metalflake
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#6a200c'); g.addColorStop(0.4, '#882e14'); g.addColorStop(0.6, '#9c3818'); g.addColorStop(1, '#6a200c');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1984);
            const numFlakes = Math.ceil(w * h * 0.17);
            for (let i = 0; i < numFlakes; i++) {
                const bright = 145 + rng() * 100;
                const sz = rng() > 0.70 ? 2 : 1;
                ctx.fillStyle = `rgba(${bright},${bright - 35},${bright - 55},${0.5 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), sz, sz);
            }
        },
        // --- Current Metal Flake base (also pure canvas) ---
        metal_flake_base: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#9a9aa0'); g.addColorStop(0.5, '#ababb2'); g.addColorStop(1, '#9a9aa0');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7905);
            for (let i = 0; i < 60; i++) {
                ctx.fillStyle = `rgba(200,200,210,${0.3 + rng() * 0.5})`;
                ctx.fillRect(Math.floor(rng() * w), Math.floor(rng() * h), 1, 1);
            }
        },
        candy_apple: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#8a0000'); g.addColorStop(0.3, '#cc1010'); g.addColorStop(0.5, '#dd2020'); g.addColorStop(0.7, '#cc1010'); g.addColorStop(1, '#8a0000');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        midnight_pearl: (ctx, w, h) => {
            ctx.fillStyle = '#181820'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7906);
            for (let i = 0; i < 25; i++) {
                ctx.fillStyle = `rgba(60,60,80,${0.2 + rng() * 0.3})`;
                ctx.fillRect(rng() * w, rng() * h, 1, 1);
            }
        },
        // --- Exotic Metal Bases ---
        liquid_titanium: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#b0bcc5'); g.addColorStop(0.3, '#c8d4dd'); g.addColorStop(0.5, '#d8e0e8'); g.addColorStop(0.7, '#c8d4dd'); g.addColorStop(1, '#b0bcc5');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Caustic flow ripples
            for (let y = 0; y < h; y += 3) { const x = Math.sin(y * 0.15) * 8 + w / 2; ctx.strokeStyle = 'rgba(220,230,240,0.15)'; ctx.beginPath(); ctx.moveTo(x - 10, y); ctx.lineTo(x + 10, y); ctx.stroke(); }
        },
        tungsten: (ctx, w, h) => {
            ctx.fillStyle = '#3a3e45'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7840); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 10; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n + 2; }
            ctx.putImageData(id, 0, 0);
        },
        platinum: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#d8d8d5'); g.addColorStop(0.35, '#e8e8e5'); g.addColorStop(0.5, '#f0f0ed'); g.addColorStop(0.65, '#e8e8e5'); g.addColorStop(1, '#d8d8d5');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        cobalt_metal: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.8, h);
            g.addColorStop(0, '#4a5570'); g.addColorStop(0.4, '#5a6888'); g.addColorStop(0.6, '#6878a0'); g.addColorStop(1, '#4a5570');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(w * 0.3, 0, w * 0.7, h * 0.5);
            hl.addColorStop(0, 'rgba(100,130,200,0)'); hl.addColorStop(0.5, 'rgba(100,130,200,0.2)'); hl.addColorStop(1, 'rgba(100,130,200,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        // --- Extreme & Experimental Bases ---
        quantum_black: (ctx, w, h) => {
            ctx.fillStyle = '#020204'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7850);
            for (let i = 0; i < 5; i++) { ctx.fillStyle = `rgba(15,15,20,${0.3 + rng() * 0.3})`; ctx.fillRect(rng() * w, rng() * h, 2, 2); }
        },
        neutron_star: (ctx, w, h) => {
            const g = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.7);
            g.addColorStop(0, '#ffffff'); g.addColorStop(0.3, '#f8f8ff'); g.addColorStop(0.6, '#f0f0f8'); g.addColorStop(1, '#e8e8f0');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        plasma_core: (ctx, w, h) => {
            ctx.fillStyle = '#401060'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7851);
            ctx.lineWidth = 0.8; ctx.strokeStyle = 'rgba(200,80,180,0.4)';
            for (let i = 0; i < 12; i++) {
                let x = rng() * w, y = rng() * h; ctx.beginPath(); ctx.moveTo(x, y);
                for (let j = 0; j < 8; j++) { x += (rng() - 0.5) * 15; y += (rng() - 0.5) * 15; ctx.lineTo(x, y); } ctx.stroke();
            }
        },
        dark_matter: (ctx, w, h) => {
            ctx.fillStyle = '#060608'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 6; i++) {
                const y = h * (i / 6); const a = i % 2 === 0 ? 'rgba(20,10,40,0.4)' : 'rgba(10,25,30,0.4)';
                ctx.fillStyle = a; ctx.fillRect(0, y, w, h / 12);
            }
        },
        superconductor: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#e0e4e8'); g.addColorStop(0.3, '#e8ecf0'); g.addColorStop(0.5, '#f0f4f8'); g.addColorStop(0.7, '#e8ecf0'); g.addColorStop(1, '#e0e4e8');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(100,180,200,0.15)'; ctx.lineWidth = 0.5;
            for (let x = 0; x < w; x += 8) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.bezierCurveTo(x + 4, h * 0.3, x - 4, h * 0.6, x, h); ctx.stroke(); }
        },
        bioluminescent: (ctx, w, h) => {
            ctx.fillStyle = '#0a2020'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7852);
            for (let i = 0; i < 40; i++) {
                const x = rng() * w, y = rng() * h, r = 0.5 + rng() * 2;
                ctx.fillStyle = `rgba(40,${150 + Math.floor(rng() * 80)},${120 + Math.floor(rng() * 60)},${0.3 + rng() * 0.4})`;
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
            }
        },
        solar_panel: (ctx, w, h) => {
            ctx.fillStyle = '#0a1530'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(120,120,140,0.3)'; ctx.lineWidth = 0.5;
            for (let x = 0; x < w; x += 8) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = 0; y < h; y += 8) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        holographic_base: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#ff4488'); g.addColorStop(0.17, '#ffaa22'); g.addColorStop(0.33, '#44ff44');
            g.addColorStop(0.5, '#22ddff'); g.addColorStop(0.67, '#4444ff'); g.addColorStop(0.83, '#aa22ff'); g.addColorStop(1, '#ff4488');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        // --- Chrome & Mirror Bases ---
        black_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#0a0a0e'); g.addColorStop(0.35, '#141418'); g.addColorStop(0.5, '#222228'); g.addColorStop(0.65, '#141418'); g.addColorStop(1, '#0a0a0e');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, h * 0.3, 0, h * 0.5);
            hl.addColorStop(0, 'rgba(60,60,70,0)'); hl.addColorStop(0.5, 'rgba(80,80,95,0.3)'); hl.addColorStop(1, 'rgba(60,60,70,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        blue_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#3050aa'); g.addColorStop(0.3, '#5070cc'); g.addColorStop(0.5, '#7090ee'); g.addColorStop(0.7, '#5070cc'); g.addColorStop(1, '#3050aa');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(w * 0.2, 0, w * 0.6, h * 0.4);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(200,220,255,0.25)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        red_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#882020'); g.addColorStop(0.3, '#bb3030'); g.addColorStop(0.5, '#dd4040'); g.addColorStop(0.7, '#bb3030'); g.addColorStop(1, '#882020');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(w * 0.2, 0, w * 0.6, h * 0.4);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,200,180,0.25)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        antique_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#8a8070'); g.addColorStop(0.4, '#9a9080'); g.addColorStop(0.7, '#8a7e6e'); g.addColorStop(1, '#807060');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7830);
            for (let i = 0; i < 25; i++) {
                const x = rng() * w, y = rng() * h, r = 1 + rng() * 3;
                ctx.fillStyle = `rgba(90,80,60,${0.15 + rng() * 0.2})`;
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
            }
        },
        // --- Ceramic & Glass Bases ---
        porcelain: (ctx, w, h) => {
            // Bright white porcelain with slight cool blue shimmer
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#e8e8f4'); g.addColorStop(0.4, '#f0f0f8'); g.addColorStop(1, '#e5e5f0');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Subtle gloss band
            const gl = ctx.createLinearGradient(0, h * 0.3, 0, h * 0.6);
            gl.addColorStop(0, 'rgba(255,255,255,0)'); gl.addColorStop(0.5, 'rgba(255,255,255,0.15)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = gl; ctx.fillRect(0, 0, w, h);
        },
        obsidian: (ctx, w, h) => {
            // Deep near-black volcanic glass with blue-purple depth
            const g = ctx.createLinearGradient(0, 0, w * 0.6, h);
            g.addColorStop(0, '#0a0a14'); g.addColorStop(0.4, '#12121e'); g.addColorStop(0.7, '#0e0e18'); g.addColorStop(1, '#08080f');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createRadialGradient(w * 0.3, h * 0.35, 0, w * 0.3, h * 0.35, w * 0.5);
            hl.addColorStop(0, 'rgba(30,25,50,0.3)'); hl.addColorStop(1, 'rgba(10,10,20,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        crystal_clear: (ctx, w, h) => {
            // Pale clear with prismatic sparkle dots
            ctx.fillStyle = '#dceef5'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7820);
            for (let i = 0; i < 30; i++) {
                const x = rng() * w, y = rng() * h, r = 0.5 + rng() * 1.5;
                const hue = Math.floor(rng() * 360);
                ctx.fillStyle = `hsla(${hue}, 60%, 80%, ${0.3 + rng() * 0.3})`;
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
            }
        },
        tempered_glass: (ctx, w, h) => {
            // Glass with subtle green tint
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#c0d8d0'); g.addColorStop(0.5, '#c8e0d8'); g.addColorStop(1, '#b8d0c8');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const gl = ctx.createLinearGradient(w * 0.2, 0, w * 0.8, h);
            gl.addColorStop(0, 'rgba(255,255,255,0)'); gl.addColorStop(0.5, 'rgba(255,255,255,0.1)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = gl; ctx.fillRect(0, 0, w, h);
        },
        ceramic_matte: (ctx, w, h) => {
            // Flat matte ceramic - smooth grey-ish desaturated
            ctx.fillStyle = '#8a8a8a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7821); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = (rng() - 0.5) * 8;
                id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
            }
            ctx.putImageData(id, 0, 0);
        },
        enamel: (ctx, w, h) => {
            // Deep glossy enamel - vivid color with wet-look band
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#992222'); g.addColorStop(0.3, '#aa2828'); g.addColorStop(0.7, '#881e1e'); g.addColorStop(1, '#992222');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const gl = ctx.createLinearGradient(0, h * 0.25, 0, h * 0.55);
            gl.addColorStop(0, 'rgba(255,255,255,0)'); gl.addColorStop(0.5, 'rgba(255,255,255,0.12)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = gl; ctx.fillRect(0, 0, w, h);
        },
        // --- Carbon & Composite Bases ---
        carbon_base: (ctx, w, h) => {
            // Dark carbon fiber weave
            ctx.fillStyle = '#222'; ctx.fillRect(0, 0, w, h);
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wx = Math.abs(px % 6 - 3) / 3.0;
                    const wy = Math.abs(py % 6 - 3) / 3.0;
                    const weave = (wx * 0.5 + wy * 0.5);
                    const v = Math.floor(30 + weave * 40 + Math.random() * 10);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v + 3; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        kevlar_base: (ctx, w, h) => {
            // Golden kevlar weave
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wx = Math.abs(px % 8 - 4) / 4.0;
                    const wy = Math.abs(py % 8 - 4) / 4.0;
                    const weave = wx * 0.6 + wy * 0.4;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.floor(130 + weave * 50); id.data[idx + 1] = Math.floor(110 + weave * 40);
                    id.data[idx + 2] = Math.floor(50 + weave * 20); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        fiberglass: (ctx, w, h) => {
            // Raw fiberglass - visible random fiber strands over translucent greenish-white
            ctx.fillStyle = '#d4ddd0'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7800);
            // Random fiber strands
            ctx.lineWidth = 0.4;
            for (let i = 0; i < 80; i++) {
                const x1 = rng() * w, y1 = rng() * h;
                const angle = rng() * Math.PI;
                const len = 8 + rng() * 20;
                ctx.strokeStyle = `rgba(180,200,175,${0.15 + rng() * 0.25})`;
                ctx.beginPath(); ctx.moveTo(x1, y1);
                ctx.lineTo(x1 + Math.cos(angle) * len, y1 + Math.sin(angle) * len);
                ctx.stroke();
            }
            // Slight translucent sheen
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, 'rgba(220,235,225,0.2)'); g.addColorStop(1, 'rgba(200,215,195,0.15)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        carbon_ceramic: (ctx, w, h) => {
            // Dark grey-blue gritty ceramic
            const id = ctx.createImageData(w, h); const rng = _seededRng(7801);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const grit = (rng() - 0.5) * 25;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.floor(55 + grit); id.data[idx + 1] = Math.floor(58 + grit);
                    id.data[idx + 2] = Math.floor(65 + grit); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        aramid: (ctx, w, h) => {
            // Golden-yellow tight weave
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wx = Math.abs(px % 4 - 2) / 2.0;
                    const wy = Math.abs(py % 4 - 2) / 2.0;
                    const weave = wx * 0.5 + wy * 0.5;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.floor(150 + weave * 40); id.data[idx + 1] = Math.floor(125 + weave * 35);
                    id.data[idx + 2] = Math.floor(40 + weave * 15); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        graphene: (ctx, w, h) => {
            // Near-black with subtle green-blue sheen
            ctx.fillStyle = '#111418'; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, h * 0.2, 0, h * 0.6);
            hl.addColorStop(0, 'rgba(20,40,35,0)'); hl.addColorStop(0.4, 'rgba(30,60,50,0.3)');
            hl.addColorStop(0.6, 'rgba(25,50,55,0.3)'); hl.addColorStop(1, 'rgba(20,40,35,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        forged_composite: (ctx, w, h) => {
            // Dark forged carbon - Lamborghini-style random irregular chunks with strong contrast
            ctx.fillStyle = '#1a1a1c'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h); const rng = _seededRng(7802);
            const noise = _simpleNoise2D(w, h, [3, 6, 12], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const n = noise[i];
                let v;
                if (n > 0.3) v = 55 + (rng() - 0.5) * 12;       // light chunks (silver-grey)
                else if (n > -0.1) v = 35 + (rng() - 0.5) * 8;  // mid chunks
                else v = 18 + (rng() - 0.5) * 6;                 // dark gaps (near-black)
                id.data[i * 4] = v; id.data[i * 4 + 1] = v; id.data[i * 4 + 2] = v + 2; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        hybrid_weave: (ctx, w, h) => {
            // Alternating carbon (dark) and kevlar (golden) bands
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                const isKevlar = (Math.floor(py / 6) % 2) === 1;
                for (let px = 0; px < w; px++) {
                    const wx = Math.abs(px % 6 - 3) / 3.0;
                    const wy = Math.abs(py % 6 - 3) / 3.0;
                    const weave = wx * 0.5 + wy * 0.5;
                    const idx = (py * w + px) * 4;
                    if (isKevlar) {
                        id.data[idx] = Math.floor(120 + weave * 40); id.data[idx + 1] = Math.floor(100 + weave * 30);
                        id.data[idx + 2] = Math.floor(45 + weave * 15);
                    } else {
                        const v = Math.floor(30 + weave * 35);
                        id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v + 2;
                    }
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- v4.0 Bases ---
        satin_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#bbb'); g.addColorStop(0.3, '#ddd'); g.addColorStop(0.5, '#aaa'); g.addColorStop(0.7, '#ccc'); g.addColorStop(1, '#bbb');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Soft satin grain
            ctx.strokeStyle = 'rgba(200,200,210,0.08)'; ctx.lineWidth = 0.5;
            for (let y = 0; y < h; y += 1.5) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        spectraflame: (ctx, w, h) => {
            // Candy-over-chrome: deep saturated + dense sparkle
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#771144'); g.addColorStop(0.3, '#cc2266'); g.addColorStop(0.5, '#ee4488'); g.addColorStop(0.7, '#aa1a55'); g.addColorStop(1, '#992255');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Dense chrome sparkle flecks (Hot Wheels look)
            const rng = _seededRng(5001); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                if (rng() > 0.88) { const s = 40 + Math.floor(rng() * 50); id.data[i] += s; id.data[i + 1] += s; id.data[i + 2] += s; }
            }
            ctx.putImageData(id, 0, 0);
        },
        frozen_matte: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#99aabb'); g.addColorStop(0.5, '#aabbcc'); g.addColorStop(1, '#8899aa');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5002); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 20 + (rng() > 0.9 ? 30 : 0); id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n + 3; }
            ctx.putImageData(id, 0, 0);
        },
        cerakote: (ctx, w, h) => {
            ctx.fillStyle = '#5a6644'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5003); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 18; id.data[i] += n; id.data[i + 1] += n + 2; id.data[i + 2] += n - 3; }
            ctx.putImageData(id, 0, 0);
        },
        sandblasted: (ctx, w, h) => {
            ctx.fillStyle = '#8a8a8a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5004); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 40; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        vantablack: (ctx, w, h) => {
            ctx.fillStyle = '#020202'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5005); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = rng() * 4; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        rose_gold: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#bb7766'); g.addColorStop(0.4, '#cc8877'); g.addColorStop(0.6, '#dd9988'); g.addColorStop(1, '#c08070');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5006); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const s = rng() > 0.9 ? 35 : 0; id.data[i] += s; id.data[i + 1] += s - 5; id.data[i + 2] += s - 10; }
            ctx.putImageData(id, 0, 0);
        },
        surgical_steel: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#ccc'); g.addColorStop(0.2, '#eee'); g.addColorStop(0.4, '#bbb'); g.addColorStop(0.6, '#ddd'); g.addColorStop(1, '#ccc');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        duracoat: (ctx, w, h) => {
            ctx.fillStyle = '#4a4a33'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5008); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 15; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n - 3; }
            ctx.putImageData(id, 0, 0);
        },
        powder_coat: (ctx, w, h) => {
            ctx.fillStyle = '#6666aa'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5009); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 10; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n + 3; }
            ctx.putImageData(id, 0, 0);
        },
        // --- v5.0 Bases ---
        wet_look: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#2a5544'); g.addColorStop(0.3, '#3a7755'); g.addColorStop(0.6, '#4a8866'); g.addColorStop(1, '#336655');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.4);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.18)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.18)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        silk: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#9999bb'); g.addColorStop(0.3, '#aaaacc'); g.addColorStop(0.6, '#bbbbdd'); g.addColorStop(1, '#9999bb');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(200,200,230,0.06)'; ctx.lineWidth = 0.5;
            for (let y = 0; y < h; y += 1) { ctx.beginPath(); ctx.moveTo(0, y + (Math.sin(y * 0.3) * 0.5)); ctx.lineTo(w, y + (Math.sin(y * 0.3 + 1) * 0.5)); ctx.stroke(); }
        },
        patina_bronze: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(5102);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const pat = (noise[i] + 1) * 0.5;
                const r = Math.floor(80 + pat * 40); const g = Math.floor(100 + pat * 50); const b = Math.floor(50 + pat * 30);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        iridescent: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.07 + px * 0.05) * 0.3 + Math.sin(py * 0.03 - px * 0.06) * 0.2 + 0.5;
                    const hue = t * 360;
                    const [r, g, b] = _hslToRgb(hue, 60, 60 + t * 15);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        raw_aluminum: (ctx, w, h) => {
            ctx.fillStyle = '#aabbcc'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5104); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 25; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n + 3; }
            ctx.putImageData(id, 0, 0);
        },
        tinted_clear: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#336655'); g.addColorStop(0.4, '#448866'); g.addColorStop(0.7, '#559977'); g.addColorStop(1, '#3a7760');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.1)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.1)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        galvanized: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(5106);
            const noise = _simpleNoise2D(w, h, [8, 16], [0.5, 0.5], rng);
            for (let i = 0; i < w * h; i++) {
                const spangle = Math.floor(((noise[i] + 1) * 0.5) * 4) / 4;
                const v = Math.floor(140 + spangle * 80);
                id.data[i * 4] = v - 5; id.data[i * 4 + 1] = v; id.data[i * 4 + 2] = v - 3; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        heat_treated: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = (Math.sin(py * 0.08 + px * 0.04) * 0.3 + Math.sin(px * 0.06) * 0.2 + 0.5);
                    // Blue-gold heat zones
                    const r = Math.floor(80 + t * 120); const g = Math.floor(80 + t * 80); const b = Math.floor(140 - t * 60);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        smoked: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#2a2a33'); g.addColorStop(0.5, '#333344'); g.addColorStop(1, '#282835');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.06)');
            hl.addColorStop(0.6, 'rgba(255,255,255,0.06)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        diamond_coat: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#ccddee'); g.addColorStop(0.5, '#ddeeff'); g.addColorStop(1, '#bbccdd');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5110); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const s = rng() > 0.88 ? 50 + rng() * 40 : 0; id.data[i] += s; id.data[i + 1] += s; id.data[i + 2] += s; }
            ctx.putImageData(id, 0, 0);
        },
        flat_black: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5111); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = rng() * 5; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        mirror_gold: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#bb8822'); g.addColorStop(0.2, '#eecc44'); g.addColorStop(0.4, '#aa7711');
            g.addColorStop(0.6, '#ddbb33'); g.addColorStop(0.8, '#cc9922'); g.addColorStop(1, '#ddaa44');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        brushed_aluminum: (ctx, w, h) => {
            ctx.fillStyle = '#aabbcc'; ctx.fillRect(0, 0, w, h);
            for (let y = 0; y < h; y++) {
                const bright = 160 + Math.random() * 50;
                ctx.strokeStyle = `rgba(${bright},${bright + 5},${bright + 10},0.3)`;
                ctx.lineWidth = 0.7; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }
        },
        clear_matte: (ctx, w, h) => {
            ctx.fillStyle = '#888'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5114); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 8; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        piano_black: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#050510'); g.addColorStop(0.3, '#101020'); g.addColorStop(0.5, '#181828');
            g.addColorStop(0.7, '#101020'); g.addColorStop(1, '#050510');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, 0, w, h * 0.4);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.35, 'rgba(255,255,255,0.15)');
            hl.addColorStop(0.55, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        satin_gold: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#aa8833'); g.addColorStop(0.5, '#ccaa55'); g.addColorStop(1, '#bb9944');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(200,180,100,0.08)'; ctx.lineWidth = 0.5;
            for (let y = 0; y < h; y += 1.5) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        rugged: (ctx, w, h) => {
            ctx.fillStyle = '#554433'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5118); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 35; id.data[i] += n; id.data[i + 1] += n - 3; id.data[i + 2] += n - 8; }
            ctx.putImageData(id, 0, 0);
        },
        pearlescent_white: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#e8e8ff'); g.addColorStop(0.3, '#eeeeff'); g.addColorStop(0.6, '#e0e0f0'); g.addColorStop(1, '#eae8f8');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5119); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const s = rng() > 0.9 ? 15 : 0; id.data[i] += s; id.data[i + 1] += s; id.data[i + 2] += s; }
            ctx.putImageData(id, 0, 0);
        },
        dark_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#222230'); g.addColorStop(0.2, '#444450'); g.addColorStop(0.4, '#1a1a28');
            g.addColorStop(0.6, '#3a3a48'); g.addColorStop(0.8, '#282838'); g.addColorStop(1, '#333340');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        titanium_raw: (ctx, w, h) => {
            ctx.fillStyle = '#7a8899'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5121); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 30; id.data[i] += n; id.data[i + 1] += n + 2; id.data[i + 2] += n + 5; }
            ctx.putImageData(id, 0, 0);
        },
        candy_chrome: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w * 0.7, h);
            g.addColorStop(0, '#aa2266'); g.addColorStop(0.2, '#dd4488'); g.addColorStop(0.4, '#882255');
            g.addColorStop(0.6, '#cc3377'); g.addColorStop(0.8, '#993366'); g.addColorStop(1, '#bb3380');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        liquid_wrap: (ctx, w, h) => {
            ctx.fillStyle = '#555566'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5123); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 22; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n + 2; }
            ctx.putImageData(id, 0, 0);
        },
        // --- v5.5 Bases ---
        plasma_metal: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.06 + px * 0.04) * 0.3 + Math.sin(py * 0.03 - px * 0.05) * 0.2 + 0.5;
                    const r = Math.floor(80 + t * 80); const g = Math.floor(40 + t * 40); const b = Math.floor(140 + t * 60);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
            const rng = _seededRng(5501); const id2 = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id2.data.length; i += 4) { const s = rng() > 0.9 ? 35 : 0; id2.data[i] += s; id2.data[i + 1] += s * 0.3; id2.data[i + 2] += s; }
            ctx.putImageData(id2, 0, 0);
        },
        burnt_headers: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.05 + px * 0.07) * 0.3 + Math.sin(py * 0.04) * 0.2 + 0.5;
                    // Gold-blue oxide heat zones
                    const r = Math.floor(140 + t * 60); const g = Math.floor(100 + t * 40); const b = Math.floor(50 + t * 80);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        mercury: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(5503);
            const noise = _simpleNoise2D(w, h, [2, 4, 8], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const pool = Math.max(0, Math.min(1, (noise[i] + 1) * 0.5));
                const v = Math.floor(160 + pool * 90);
                id.data[i * 4] = v - 3; id.data[i * 4 + 1] = v - 2; id.data[i * 4 + 2] = v + 3; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        electric_ice: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#2288cc'); g.addColorStop(0.3, '#44aaee'); g.addColorStop(0.6, '#33bbff'); g.addColorStop(1, '#2299dd');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5504); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const s = rng() > 0.9 ? 40 : 0; id.data[i] += s * 0.3; id.data[i + 1] += s * 0.7; id.data[i + 2] += s; }
            ctx.putImageData(id, 0, 0);
        },
        volcanic: (ctx, w, h) => {
            ctx.fillStyle = '#3a3a2a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5505); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 25; id.data[i] += n; id.data[i + 1] += n - 2; id.data[i + 2] += n - 5; }
            ctx.putImageData(id, 0, 0);
        },
        // ===== PARADIGM BASES =====
        singularity: (ctx, w, h) => {
            // Black hole - near-black with accretion ring glow
            ctx.fillStyle = '#020008'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.5, cy = h * 0.5, r = Math.min(w, h) * 0.35;
            for (let ring = 3; ring >= 0; ring--) {
                const rr = r + ring * 3;
                const g = ctx.createRadialGradient(cx, cy, rr * 0.7, cx, cy, rr);
                g.addColorStop(0, 'rgba(0,0,0,0)');
                g.addColorStop(0.6, 'rgba(80,40,120,' + (0.15 + ring * 0.05) + ')');
                g.addColorStop(0.85, 'rgba(255,140,40,' + (0.2 + ring * 0.08) + ')');
                g.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            }
            // Central void
            const v = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 0.4);
            v.addColorStop(0, '#000005'); v.addColorStop(1, 'rgba(0,0,5,0)');
            ctx.fillStyle = v; ctx.fillRect(0, 0, w, h);
        },
        bioluminescent: (ctx, w, h) => {
            // Living glow cells - dark with bright organic spots
            ctx.fillStyle = '#0a1a18'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7700);
            const cells = 12 + Math.floor(rng() * 8);
            for (let i = 0; i < cells; i++) {
                const x = rng() * w, y = rng() * h, r = 4 + rng() * 8;
                const hue = 140 + rng() * 80; // cyan-green range
                const g = ctx.createRadialGradient(x, y, 0, x, y, r);
                g.addColorStop(0, 'hsla(' + hue + ',90%,70%,0.7)');
                g.addColorStop(0.5, 'hsla(' + hue + ',80%,40%,0.3)');
                g.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            }
        },
        liquid_obsidian: (ctx, w, h) => {
            // Flowing glass-metal - deep black with reflective streaks
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#080818'); g.addColorStop(0.25, '#0c0c22');
            g.addColorStop(0.5, '#141428'); g.addColorStop(0.75, '#0a0a1e');
            g.addColorStop(1, '#060614');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Highlight streaks
            ctx.strokeStyle = 'rgba(140,150,200,0.15)'; ctx.lineWidth = 2;
            const rng = _seededRng(7701);
            for (let i = 0; i < 5; i++) {
                ctx.beginPath();
                ctx.moveTo(rng() * w, 0);
                ctx.quadraticCurveTo(rng() * w, h * 0.5, rng() * w, h);
                ctx.stroke();
            }
        },
        prismatic: (ctx, w, h) => {
            // Rainbow diagonal spectral gradient
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#ff3366'); g.addColorStop(0.17, '#ff8833');
            g.addColorStop(0.33, '#ffdd33'); g.addColorStop(0.5, '#33dd66');
            g.addColorStop(0.67, '#3388ff'); g.addColorStop(0.83, '#8833ff');
            g.addColorStop(1, '#ff33aa');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Metallic shimmer overlay
            const s = ctx.createLinearGradient(0, h, w, 0);
            s.addColorStop(0, 'rgba(255,255,255,0)'); s.addColorStop(0.4, 'rgba(255,255,255,0.15)');
            s.addColorStop(0.6, 'rgba(255,255,255,0.15)'); s.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = s; ctx.fillRect(0, 0, w, h);
        },
        p_mercury: (ctx, w, h) => {
            // Liquid silver mercury pooling
            const g = ctx.createRadialGradient(w * 0.4, h * 0.4, 0, w * 0.5, h * 0.5, w * 0.6);
            g.addColorStop(0, '#e8ecf0'); g.addColorStop(0.3, '#c0c8d0');
            g.addColorStop(0.6, '#98a4b0'); g.addColorStop(1, '#788898');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Pooling distortion blobs
            const rng = _seededRng(7702);
            for (let i = 0; i < 6; i++) {
                const x = rng() * w, y = rng() * h, r = 5 + rng() * 10;
                const pg = ctx.createRadialGradient(x, y, 0, x, y, r);
                pg.addColorStop(0, 'rgba(240,244,248,0.5)');
                pg.addColorStop(1, 'rgba(160,170,185,0)');
                ctx.fillStyle = pg; ctx.fillRect(0, 0, w, h);
            }
        },
        p_phantom: (ctx, w, h) => {
            // Ghostly translucent mist - barely visible wisps
            ctx.fillStyle = '#d8dde4'; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.12;
            const rng = _seededRng(7703);
            for (let i = 0; i < 8; i++) {
                ctx.beginPath();
                const x1 = rng() * w, y1 = rng() * h;
                ctx.moveTo(x1, y1);
                ctx.quadraticCurveTo(rng() * w, rng() * h, rng() * w, rng() * h);
                ctx.strokeStyle = 'rgba(200,210,225,0.6)'; ctx.lineWidth = 8 + rng() * 12;
                ctx.stroke();
            }
            ctx.globalAlpha = 1.0;
        },
        p_volcanic: (ctx, w, h) => {
            // Lava cooling - dark rock with orange heat veins
            ctx.fillStyle = '#1a0800'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7704);
            // Heat veins
            ctx.lineWidth = 2;
            for (let i = 0; i < 8; i++) {
                ctx.beginPath();
                let x = rng() * w, y = rng() * h;
                ctx.moveTo(x, y);
                for (let s = 0; s < 5; s++) {
                    x += (rng() - 0.5) * w * 0.3; y += (rng() - 0.5) * h * 0.3;
                    ctx.lineTo(x, y);
                }
                ctx.strokeStyle = 'rgba(255,' + Math.floor(80 + rng() * 80) + ',0,0.5)';
                ctx.lineWidth = 1 + rng() * 3; ctx.stroke();
                // Glow pass
                ctx.strokeStyle = 'rgba(255,120,20,0.15)';
                ctx.lineWidth = 6 + rng() * 4; ctx.stroke();
            }
        },
        arctic_ice: (ctx, w, h) => {
            // Cracked ice - blue-white with fracture lines
            const g = ctx.createLinearGradient(0, 0, w * 0.5, h);
            g.addColorStop(0, '#c8e8ff'); g.addColorStop(0.5, '#e0f0ff');
            g.addColorStop(1, '#a8d0f0');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Crack lines
            const rng = _seededRng(7705);
            ctx.strokeStyle = 'rgba(120,180,220,0.4)'; ctx.lineWidth = 1;
            for (let i = 0; i < 12; i++) {
                ctx.beginPath();
                let x = rng() * w, y = rng() * h;
                ctx.moveTo(x, y);
                for (let s = 0; s < 3; s++) {
                    x += (rng() - 0.5) * w * 0.25; y += (rng() - 0.5) * h * 0.25;
                    ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        },
        carbon_weave: (ctx, w, h) => {
            // Carbon fiber diagonal weave
            ctx.fillStyle = '#1a2030'; ctx.fillRect(0, 0, w, h);
            const ws = 5; // weave size
            const id = ctx.getImageData(0, 0, w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const idx = (py * w + px) * 4;
                    const cell = ((Math.floor(px / ws) + Math.floor(py / ws)) % 2);
                    const bright = cell ? 38 : 28;
                    // Metallic thread highlight on diagonals
                    const diag = ((px + py) % ws === 0) ? 12 : 0;
                    id.data[idx] = bright + diag * 0.3;
                    id.data[idx + 1] = bright + diag * 0.5 + 4;
                    id.data[idx + 2] = bright + diag + 8;
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        nebula: (ctx, w, h) => {
            // Cosmic purple-blue nebula with star sparkles
            ctx.fillStyle = '#0a0820'; ctx.fillRect(0, 0, w, h);
            // Nebula clouds
            const colors = [
                { x: 0.3, y: 0.4, c: 'rgba(80,30,150,0.35)', r: 0.4 },
                { x: 0.6, y: 0.6, c: 'rgba(30,60,180,0.3)', r: 0.35 },
                { x: 0.5, y: 0.3, c: 'rgba(150,40,120,0.2)', r: 0.3 },
            ];
            colors.forEach(cl => {
                const g = ctx.createRadialGradient(cl.x * w, cl.y * h, 0, cl.x * w, cl.y * h, cl.r * Math.max(w, h));
                g.addColorStop(0, cl.c); g.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            });
            // Star sparkles
            const rng = _seededRng(7706);
            for (let i = 0; i < 20; i++) {
                const x = rng() * w, y = rng() * h;
                const b = 150 + rng() * 105;
                ctx.fillStyle = 'rgba(' + b + ',' + b + ',' + (b + 30) + ',' + (0.4 + rng() * 0.5) + ')';
                ctx.fillRect(x, y, 1, 1);
            }
        },
    };

    // --- PATTERN TEXTURES ---
    function _flameGrad(ctx, x0, y0, x1, y1, palette) {
        const g = ctx.createLinearGradient(x0, y0, x1, y1);
        palette.forEach(([stop, color]) => g.addColorStop(stop, color));
        return g;
    }
    function _flameTongue(ctx, baseX, baseY, tipX, tipY, baseW, sway, filled) {
        ctx.beginPath();
        ctx.moveTo(baseX, baseY - baseW);
        ctx.quadraticCurveTo(baseX + (tipX - baseX) * 0.4, baseY - baseW * 0.7 + sway,
            tipX - 5, tipY + 2);
        ctx.lineTo(tipX, tipY);
        ctx.quadraticCurveTo(baseX + (tipX - baseX) * 0.4, baseY + baseW * 0.3 + sway,
            baseX, baseY + baseW);
        ctx.closePath();
        if (filled) ctx.fill(); else ctx.stroke();
    }
    const patternFns = {
        carbon_fiber: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const ws = 6; // Match engine weave_size
            const id = ctx.getImageData(0, 0, w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const tx = (px % (ws * 2)) / (ws * 2);
                    const ty = (py % (ws * 2)) / (ws * 2);
                    const horiz = Math.sin(tx * Math.PI * 2) * 0.5 + 0.5;
                    const vert = Math.sin(ty * Math.PI * 2) * 0.5 + 0.5;
                    const cell = (Math.floor(px / ws) + Math.floor(py / ws)) % 2;
                    let cf = cell ? horiz : vert;
                    cf = Math.max(0, Math.min(1, cf * 1.3 - 0.15));
                    const v = Math.floor(20 + cf * 50);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v + 3; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        forged_carbon: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            // Chunky noise with quantized levels
            const rng = _seededRng(42);
            const chunks = new Float32Array(w * h);
            // Simple multi-scale noise
            for (let s = 0; s < 3; s++) {
                const scale = [12, 6, 3][s];
                const weight = [0.55, 0.35, 0.1][s];
                const sw2 = Math.max(1, Math.ceil(w / scale));
                const sh2 = Math.max(1, Math.ceil(h / scale));
                const raw = new Float32Array(sw2 * sh2);
                for (let i = 0; i < raw.length; i++) raw[i] = rng() * 2 - 1;
                for (let py = 0; py < h; py++) {
                    for (let px = 0; px < w; px++) {
                        const fx = px / w * (sw2 - 1), fy = py / h * (sh2 - 1);
                        const ix = Math.floor(fx), iy = Math.floor(fy);
                        const fx2 = fx - ix, fy2 = fy - iy;
                        const i00 = iy * sw2 + ix, i10 = i00 + (ix < sw2 - 1 ? 1 : 0);
                        const i01 = i00 + (iy < sh2 - 1 ? sw2 : 0), i11 = i01 + (ix < sw2 - 1 ? 1 : 0);
                        const v = (raw[i00] * (1 - fx2) * (1 - fy2) + raw[i10] * fx2 * (1 - fy2) + raw[i01] * (1 - fx2) * fy2 + raw[i11] * fx2 * fy2);
                        chunks[py * w + px] += v * weight;
                    }
                }
            }
            // Quantize
            for (let i = 0; i < chunks.length; i++) {
                chunks[i] = Math.floor((chunks[i] + 1) * 5) / 10;
                chunks[i] = Math.max(0, Math.min(1, chunks[i]));
            }
            for (let i = 0; i < chunks.length; i++) {
                const v = Math.floor(15 + chunks[i] * 55);
                id.data[i * 4] = v; id.data[i * 4 + 1] = v; id.data[i * 4 + 2] = v + 3; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        diamond_plate: (ctx, w, h) => {
            ctx.fillStyle = '#888'; ctx.fillRect(0, 0, w, h);
            const ds = 20;
            const id = ctx.getImageData(0, 0, w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const dx = (px % ds) - ds / 2;
                    const dy = (py % ds) - ds / 2;
                    const isDiamond = (Math.abs(dx) + Math.abs(dy)) < ds * 0.38;
                    const v = isDiamond ? 200 : 130;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        _broken_dragon_scale: (ctx, w, h) => {
            const ss = 24;
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / ss);
                    const col = Math.floor((px + (row % 2) * (ss / 2)) / ss);
                    const cy = (row + 0.5) * ss;
                    const cx = col * ss + (row % 2) * (ss / 2) + ss / 2;
                    const dist = Math.sqrt((py - cy) ** 2 + (px - cx) ** 2) / (ss * 0.55);
                    const d = Math.max(0, Math.min(1, dist));
                    const center = 1 - d;
                    const v = Math.floor(80 + center * 140);
                    const g = Math.floor(60 + center * 100);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = g; id.data[idx + 1] = v; id.data[idx + 2] = g; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        hex_mesh: (ctx, w, h) => {
            const hs = 16;
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = py / (hs * 0.866);
                    const col = px / hs;
                    const colS = col - 0.5 * (Math.floor(row) % 2);
                    const rr = Math.round(row), cr = Math.round(colS);
                    const cy = rr * hs * 0.866;
                    const cx = (cr + 0.5 * (Math.round(row) % 2)) * hs;
                    const dist = Math.sqrt((py - cy) ** 2 + (px - cx) ** 2);
                    const nd = Math.min(1, dist / (hs * 0.45));
                    const isWire = nd > 0.75;
                    const v = isWire ? 100 : 200;
                    const b = isWire ? 110 : 220;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v - 10; id.data[idx + 1] = v; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        ripple: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const origins = [{ x: w * 0.3, y: h * 0.4, sp: 12 }, { x: w * 0.7, y: h * 0.6, sp: 16 }, { x: w * 0.5, y: h * 0.2, sp: 10 }];
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let sum = 0;
                    for (const o of origins) {
                        const dist = Math.sqrt((px - o.x) ** 2 + (py - o.y) ** 2);
                        const fade = Math.max(0, 1 - dist / (Math.max(w, h) * 0.6));
                        sum += Math.sin(dist / o.sp * Math.PI * 2) * fade;
                    }
                    const rv = (sum / 3 + 1) * 0.5;
                    const v = Math.floor(80 + rv * 140);
                    const b = Math.floor(100 + rv * 120);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v - 20; id.data[idx + 1] = v; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        hammered: (ctx, w, h) => {
            ctx.fillStyle = '#8a7a6a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(42);
            for (let i = 0; i < 60; i++) {
                const cx = rng() * w, cy = rng() * h, r = 3 + rng() * 8;
                const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
                g.addColorStop(0, 'rgba(200,190,170,0.7)'); g.addColorStop(1, 'rgba(120,110,90,0.0)');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
            }
        },
        lightning: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(42);
            for (let b = 0; b < 4; b++) {
                ctx.strokeStyle = `rgba(0,200,255,${0.6 + rng() * 0.4})`;
                ctx.lineWidth = 2 + rng() * 2; ctx.beginPath();
                let px = rng() * w, py = 0;
                ctx.moveTo(px, py);
                while (py < h) {
                    py += 1 + rng() * 4;
                    px += (rng() - 0.5) * 12;
                    ctx.lineTo(px, py);
                    if (rng() < 0.04) { // Fork
                        ctx.stroke(); ctx.beginPath(); ctx.moveTo(px, py);
                        ctx.strokeStyle = `rgba(0,180,255,${0.3 + rng() * 0.3})`;
                        ctx.lineWidth = 1;
                        let fpx = px, fpy = py;
                        for (let f = 0; f < 10; f++) {
                            fpy += 1 + rng() * 3;
                            fpx += (rng() - 0.5) * 10;
                            ctx.lineTo(fpx, fpy);
                        }
                        ctx.stroke(); ctx.beginPath(); ctx.moveTo(px, py);
                        ctx.strokeStyle = `rgba(0,200,255,0.7)`; ctx.lineWidth = 2;
                    }
                }
                ctx.stroke();
            }
            // Glow
            ctx.filter = 'blur(2px)'; ctx.globalAlpha = 0.3;
            ctx.drawImage(ctx.canvas, 0, 0);
            ctx.filter = 'none'; ctx.globalAlpha = 1;
        },
        plasma: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise1 = _simpleNoise2D(w, h, [2, 4, 8], [0.25, 0.35, 0.4], rng);
            const noise2 = _simpleNoise2D(w, h, [1, 3, 6], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const n2 = noise1[i] * noise2[i];
                const vein = Math.max(0, Math.min(1, 1 - Math.abs(n2) * 4)) ** 2;
                const r = Math.floor(60 + vein * 120);
                const g = Math.floor(20 + vein * 40);
                const b = Math.floor(100 + vein * 155);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        hologram: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                const bright = (py % 6) < 3;
                for (let px = 0; px < w; px++) {
                    const v = bright ? 200 : 80;
                    const b = bright ? 240 : 100;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v - 40; id.data[idx + 1] = v; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        interference: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wave = Math.sin(py * 0.08 + px * 0.04) * 0.4 + Math.sin(py * 0.04 - px * 0.06) * 0.3 + Math.sin((py + px) * 0.03) * 0.3;
                    const t = (wave + 1) * 0.5;
                    // Rainbow HSL
                    const hue = t * 360;
                    const [r, g, b] = _hslToRgb(hue, 70, 55 + t * 20);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        battle_worn: (ctx, w, h) => {
            ctx.fillStyle = '#6a6a6a'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            const rng = _seededRng(301);
            // Horizontal scratch lines
            for (let py = 0; py < h; py++) {
                const scratchIntensity = rng() * 0.5;
                for (let px = 0; px < w; px++) {
                    const noise = (rng() - 0.5) * 50;
                    const scratch = scratchIntensity * 40;
                    const idx = (py * w + px) * 4;
                    id.data[idx] += noise - scratch; id.data[idx + 1] += noise - scratch; id.data[idx + 2] += noise - scratch;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        acid_wash: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.25, 0.35, 0.4], rng);
            for (let i = 0; i < w * h; i++) {
                const etch = Math.abs(noise[i]) * 2;
                const d = Math.max(0, Math.min(1, etch));
                const r = Math.floor(80 + (1 - d) * 80);
                const g = Math.floor(90 + (1 - d) * 50);
                const b = Math.floor(50 + (1 - d) * 30);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        cracked_ice: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const n1 = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            const n2 = _simpleNoise2D(w, h, [3, 6, 12], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const c1 = Math.exp(-n1[i] * n1[i] * 20);
                const c2 = Math.exp(-n2[i] * n2[i] * 20);
                const crack = Math.min(1, c1 + c2);
                const r = Math.floor(160 + (1 - crack) * 60);
                const g = Math.floor(200 + (1 - crack) * 40);
                const b = Math.floor(220 + (1 - crack) * 30);
                // Crack lines are darker
                const cv = Math.floor(120 * crack);
                id.data[i * 4] = r - cv; id.data[i * 4 + 1] = g - cv * 0.5; id.data[i * 4 + 2] = b - cv * 0.3; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        metal_flake: (ctx, w, h) => {
            ctx.fillStyle = '#aaa088'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            const rng = _seededRng(42);
            for (let i = 0; i < id.data.length; i += 4) {
                const flake = rng() > 0.85 ? 50 + rng() * 60 : (rng() - 0.5) * 25;
                id.data[i] += flake; id.data[i + 1] += flake - 5; id.data[i + 2] += flake - 10;
            }
            ctx.putImageData(id, 0, 0);
        },
        holographic_flake: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const gs = 8;
            const rng = _seededRng(42);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const d1 = Math.sin((px + py) * Math.PI / gs) * 0.5 + 0.5;
                    const d2 = Math.sin((px - py) * Math.PI / (gs * 1.3)) * 0.5 + 0.5;
                    const holo = d1 * 0.6 + d2 * 0.4;
                    const hue = holo * 360;
                    const sparkle = rng() > 0.97;
                    const [r, g, b] = _hslToRgb(hue, sparkle ? 90 : 60, sparkle ? 80 : 50 + holo * 20);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        stardust: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a2a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(42);
            for (let i = 0; i < w * h * 0.02; i++) {
                const sx = rng() * w, sy = rng() * h;
                const bright = 180 + rng() * 75;
                ctx.fillStyle = `rgba(${bright},${bright},${bright + 20},${0.7 + rng() * 0.3})`;
                ctx.fillRect(Math.floor(sx), Math.floor(sy), 1, 1);
            }
        },
        // --- Expansion Pack Patterns ---
        pinstripe: (ctx, w, h) => {
            ctx.fillStyle = '#4a5568'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#7a8598';
            for (let x = 0; x < w; x += 12) { ctx.fillRect(x, 0, 2, h); }
        },
        camo: (ctx, w, h) => {
            const rng = _seededRng(700);
            const colors = ['#3a4a2a', '#556644', '#7a8a5a'];
            const bs = 8;
            for (let py = 0; py < h; py += bs) {
                for (let px = 0; px < w; px += bs) {
                    ctx.fillStyle = colors[Math.floor(rng() * 3)];
                    ctx.fillRect(px, py, bs, bs);
                }
            }
        },
        wood_grain: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(800);
            const rowNoise = new Float32Array(h);
            for (let i = 0; i < h; i++) rowNoise[i] = rng() * 2 - 1;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wave = Math.sin(py * 0.12 + Math.sin(px * 0.04) * 3) * 0.4;
                    const grain = (rowNoise[py] + wave + 1) * 0.35;
                    const v = Math.max(0, Math.min(1, grain));
                    const r = Math.floor(100 + v * 80); const g = Math.floor(60 + v * 50); const b = Math.floor(30 + v * 25);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        snake_skin: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const sw2 = 12, sh2 = 18;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / sh2);
                    const sx = (px + (row % 2) * (sw2 / 2)) % sw2;
                    const sy = py % sh2;
                    const ex = Math.min(sx, sw2 - sx) / (sw2 * 0.5);
                    const ey = Math.min(sy, sh2 - sy) / (sh2 * 0.5);
                    const c = Math.min(1, Math.min(ex, ey) * 2.5);
                    const v = Math.floor(50 + c * 120); const g = Math.floor(70 + c * 90);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v - 10; id.data[idx + 1] = g; id.data[idx + 2] = v - 20; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Animal & Wildlife: Missing Renderers ---
        crocodile: (ctx, w, h) => {
            // Interlocking rectangular croc scales with irregular sizing
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4001);
            const sw2 = 14, sh2 = 10;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / sh2);
                    const ox = (row % 2) * Math.floor(sw2 * 0.6);
                    const sx = ((px + ox) % sw2);
                    const sy = py % sh2;
                    // Distance from scale center (rectangular, not circular)
                    const ex = Math.min(sx, sw2 - sx) / (sw2 * 0.5);
                    const ey = Math.min(sy, sh2 - sy) / (sh2 * 0.5);
                    const edge = Math.min(ex, ey);
                    // Raised center, dark groove border
                    const isGroove = edge < 0.2;
                    const ridge = isGroove ? 0 : Math.min(1, (edge - 0.2) * 2.5);
                    // Subtle per-scale color variation from seeded noise
                    const scaleIdx = row * 20 + Math.floor((px + ox) / sw2);
                    const hueShift = (Math.sin(scaleIdx * 3.7) * 0.5 + 0.5) * 0.15;
                    const base_r = 55 + ridge * 80 + hueShift * 30;
                    const base_g = 65 + ridge * 70 - hueShift * 10;
                    const base_b = 40 + ridge * 40;
                    const bump = (rng() - 0.5) * 12; // micro texture
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.max(0, Math.min(255, Math.floor(base_r + bump)));
                    id.data[idx + 1] = Math.max(0, Math.min(255, Math.floor(base_g + bump)));
                    id.data[idx + 2] = Math.max(0, Math.min(255, Math.floor(base_b + bump * 0.5)));
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        feather: (ctx, w, h) => {
            // Layered feather barbs radiating from a central rachis (shaft)
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4002);
            // Base: warm light color
            for (let i = 0; i < w * h * 4; i += 4) {
                id.data[i] = 180; id.data[i + 1] = 165; id.data[i + 2] = 140; id.data[i + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Draw multiple feather shafts
            const featherCount = 5;
            for (let f = 0; f < featherCount; f++) {
                const startX = (f + 0.5) * (w / featherCount) + (rng() - 0.5) * 10;
                const curve = (rng() - 0.5) * 0.3;
                // Rachis (central shaft)
                ctx.strokeStyle = 'rgba(80,60,30,0.9)';
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(startX, 0);
                for (let y = 0; y < h; y += 2) {
                    ctx.lineTo(startX + Math.sin(y * 0.03 + f) * 8 * curve, y);
                }
                ctx.stroke();
                // Barbs: angled lines emanating from rachis
                ctx.lineWidth = 0.6;
                for (let y = 2; y < h; y += 3) {
                    const shaftX = startX + Math.sin(y * 0.03 + f) * 8 * curve;
                    const barbLen = 12 + rng() * 8;
                    const barbAngle = 0.4 + rng() * 0.2;
                    const alpha = 0.3 + rng() * 0.35;
                    // Left barb
                    ctx.strokeStyle = `rgba(120,100,65,${alpha})`;
                    ctx.beginPath();
                    ctx.moveTo(shaftX, y);
                    ctx.lineTo(shaftX - barbLen * Math.cos(barbAngle), y + barbLen * Math.sin(barbAngle));
                    ctx.stroke();
                    // Right barb
                    ctx.strokeStyle = `rgba(140,115,75,${alpha})`;
                    ctx.beginPath();
                    ctx.moveTo(shaftX, y);
                    ctx.lineTo(shaftX + barbLen * Math.cos(barbAngle), y + barbLen * Math.sin(barbAngle));
                    ctx.stroke();
                }
            }
        },
        giraffe: (ctx, w, h) => {
            // Irregular polygon patches with dark borders (Voronoi-based)
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4003);
            const nc = 25;
            const cx2 = [], cy2 = [], cv = [];
            for (let i = 0; i < nc; i++) {
                cx2.push(rng() * w);
                cy2.push(rng() * h);
                // Warm orange-brown patch colors with variation
                const r = 170 + Math.floor(rng() * 50);
                const g = 110 + Math.floor(rng() * 40);
                const b = 50 + Math.floor(rng() * 25);
                cv.push([r, g, b]);
            }
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let d1 = 1e9, d2 = 1e9, mi = 0;
                    for (let i = 0; i < nc; i++) {
                        const d = (px - cx2[i]) ** 2 + (py - cy2[i]) ** 2;
                        if (d < d1) { d2 = d1; d1 = d; mi = i; }
                        else if (d < d2) { d2 = d; }
                    }
                    const edge = Math.sqrt(d2) - Math.sqrt(d1);
                    const borderWidth = 3.5;
                    const isBorder = edge < borderWidth;
                    const idx = (py * w + px) * 4;
                    if (isBorder) {
                        // Dark brown border lines
                        const t = edge / borderWidth;
                        id.data[idx] = Math.floor(40 + t * 30);
                        id.data[idx + 1] = Math.floor(25 + t * 20);
                        id.data[idx + 2] = Math.floor(10 + t * 15);
                    } else {
                        const c = cv[mi];
                        id.data[idx] = c[0];
                        id.data[idx + 1] = c[1];
                        id.data[idx + 2] = c[2];
                    }
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        tiger_stripe: (ctx, w, h) => {
            // Organic irregular diagonal stripes with noise warping
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4004);
            const n1 = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            const n2 = _simpleNoise2D(w, h, [2, 6], [0.5, 0.5], rng);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const i = py * w + px;
                    // Diagonal stripe base with noise warping
                    const warpedY = py + n1[i] * 25;
                    const warpedX = px + n2[i] * 15;
                    const stripe = Math.sin((warpedY * 0.15) + (warpedX * 0.08)) * 0.5 + 0.5;
                    // Sharp threshold for stripe vs base
                    const isStripe = stripe < 0.38;
                    // Soft edge transition
                    const edgeDist = Math.abs(stripe - 0.38);
                    const softEdge = Math.min(1, edgeDist * 12);
                    if (isStripe) {
                        // Dark stripe (near black)
                        const v = Math.floor(25 + (1 - softEdge) * 30);
                        id.data[i * 4] = v;
                        id.data[i * 4 + 1] = v - 5;
                        id.data[i * 4 + 2] = v - 10;
                    } else {
                        // Orange-tawny base
                        const v = softEdge;
                        id.data[i * 4] = Math.floor(200 + v * 30);
                        id.data[i * 4 + 1] = Math.floor(130 + v * 25);
                        id.data[i * 4 + 2] = Math.floor(40 + v * 15);
                    }
                    id.data[i * 4 + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        zebra: (ctx, w, h) => {
            // Bold black & white organic stripes with noise warping
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4005);
            const n1 = _simpleNoise2D(w, h, [3, 6, 12], [0.3, 0.4, 0.3], rng);
            const n2 = _simpleNoise2D(w, h, [2, 5], [0.5, 0.5], rng);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const i = py * w + px;
                    // Vertical-ish stripes warped by noise
                    const warpedX = px + n1[i] * 20;
                    const warpedY = py + n2[i] * 8;
                    const stripe = Math.sin(warpedX * 0.2 + warpedY * 0.02) * 0.5 + 0.5;
                    // Crisp threshold
                    const isBlack = stripe < 0.45;
                    const edgeDist = Math.abs(stripe - 0.45);
                    const softEdge = Math.min(1, edgeDist * 15);
                    const v = isBlack
                        ? Math.floor(15 + (1 - softEdge) * 25)
                        : Math.floor(210 + softEdge * 35);
                    id.data[i * 4] = v;
                    id.data[i * 4 + 1] = v;
                    id.data[i * 4 + 2] = v + 3;
                    id.data[i * 4 + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Snake Skin Variations ---
        snake_skin_2: (ctx, w, h) => {
            // Diamond-shaped scales (python-like)
            const id = ctx.createImageData(w, h);
            const ds = 16; // diamond size
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / ds);
                    const ox = (row % 2) * Math.floor(ds / 2);
                    const lx = ((px + ox) % ds) - ds / 2;
                    const ly = (py % ds) - ds / 2;
                    // Diamond distance (Manhattan metric)
                    const diamond = (Math.abs(lx) + Math.abs(ly)) / (ds * 0.5);
                    const isEdge = diamond > 0.85;
                    const center = Math.max(0, 1 - diamond);
                    const scaleHash = Math.sin(row * 7.1 + Math.floor((px + ox) / ds) * 13.3) * 0.5 + 0.5;
                    const r = isEdge ? 30 : Math.floor(60 + center * 90 + scaleHash * 40);
                    const g = isEdge ? 35 : Math.floor(80 + center * 80 + scaleHash * 20);
                    const b = isEdge ? 20 : Math.floor(40 + center * 50);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        snake_skin_3: (ctx, w, h) => {
            // Hourglass / saddle pattern (viper-like)
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4013);
            const cw = 20, ch = 14;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / ch);
                    const ox = (row % 2) * Math.floor(cw / 2);
                    const lx = ((px + ox) % cw) / cw;
                    const ly = (py % ch) / ch;
                    // Hourglass shape: narrow at center, wide at top/bottom
                    const pinch = 0.3 + 0.4 * Math.abs(ly - 0.5) * 2;
                    const inHourglass = Math.abs(lx - 0.5) < pinch * 0.5;
                    const dist = Math.abs(lx - 0.5) / (pinch * 0.5);
                    const fade = inHourglass ? Math.max(0, 1 - dist) : 0;
                    const bump = (rng() - 0.5) * 8;
                    if (inHourglass) {
                        const r = Math.floor(50 + fade * 30 + bump);
                        const g = Math.floor(40 + fade * 20 + bump);
                        const b = Math.floor(30 + fade * 15 + bump * 0.5);
                        const idx = (py * w + px) * 4;
                        id.data[idx] = Math.max(0, r); id.data[idx + 1] = Math.max(0, g); id.data[idx + 2] = Math.max(0, b); id.data[idx + 3] = 255;
                    } else {
                        const scaleHash = Math.sin(row * 5.3 + Math.floor((px + ox) / cw) * 11.7) * 0.5 + 0.5;
                        const r = Math.floor(140 + scaleHash * 50 + bump);
                        const g = Math.floor(120 + scaleHash * 30 + bump);
                        const b = Math.floor(70 + scaleHash * 20 + bump * 0.5);
                        const idx = (py * w + px) * 4;
                        id.data[idx] = Math.max(0, Math.min(255, r));
                        id.data[idx + 1] = Math.max(0, Math.min(255, g));
                        id.data[idx + 2] = Math.max(0, Math.min(255, b));
                        id.data[idx + 3] = 255;
                    }
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        snake_skin_4: (ctx, w, h) => {
            // Cobblestone / pebble scales (boa constrictor-like, round irregular)
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(4014);
            const nc = 40;
            const cx2 = [], cy2 = [];
            for (let i = 0; i < nc; i++) { cx2.push(rng() * w); cy2.push(rng() * h); }
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let d1 = 1e9, d2 = 1e9, mi = 0;
                    for (let i = 0; i < nc; i++) {
                        const d = (px - cx2[i]) ** 2 + (py - cy2[i]) ** 2;
                        if (d < d1) { d2 = d1; d1 = d; mi = i; }
                        else if (d < d2) { d2 = d; }
                    }
                    const edge = Math.sqrt(d2) - Math.sqrt(d1);
                    const isGroove = edge < 2;
                    // Center brightness based on distance to cell center
                    const centerDist = Math.sqrt(d1) / 15;
                    const center = Math.max(0, 1 - centerDist * 0.8);
                    const scaleH = Math.sin(mi * 7.7) * 0.5 + 0.5;
                    if (isGroove) {
                        const idx = (py * w + px) * 4;
                        id.data[idx] = 30; id.data[idx + 1] = 35; id.data[idx + 2] = 20; id.data[idx + 3] = 255;
                    } else {
                        const r = Math.floor(70 + center * 80 + scaleH * 35);
                        const g = Math.floor(85 + center * 70 + scaleH * 20);
                        const b = Math.floor(45 + center * 40);
                        const idx = (py * w + px) * 4;
                        id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                    }
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        tire_tread: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2; const step = Math.max(4, h / 12);
            ctx.strokeStyle = '#000000'; ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();
            for (let y = step; y < h; y += step) {
                const wing = Math.min(w * 0.4, (h - y) * 0.5);
                ctx.strokeStyle = '#333333'; ctx.lineWidth = 2;
                ctx.beginPath(); ctx.moveTo(cx, y); ctx.lineTo(cx - wing, y + wing * 0.8); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(cx, y); ctx.lineTo(cx + wing, y + wing * 0.8); ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        circuit_board: (ctx, w, h) => {
            ctx.fillStyle = '#0a3a1a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#2a8a3a'; ctx.lineWidth = 1;
            for (let y = 0; y < h; y += 18) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            for (let x = 0; x < w; x += 24) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            ctx.fillStyle = '#3aaa4a';
            for (let y = 0; y < h; y += 18) {
                for (let x = 0; x < w; x += 24) {
                    ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        _broken_mosaic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(900);
            const nc = 30; const cx2 = [], cy2 = [], cc = [];
            for (let i = 0; i < nc; i++) { cx2.push(rng() * w); cy2.push(rng() * h); cc.push([Math.floor(80 + rng() * 120), Math.floor(50 + rng() * 100), Math.floor(60 + rng() * 120)]); }
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let md = 1e9, md2 = 1e9, mi = 0;
                    for (let i = 0; i < nc; i++) { const d = (px - cx2[i]) ** 2 + (py - cy2[i]) ** 2; if (d < md) { md2 = md; md = d; mi = i; } else if (d < md2) { md2 = d; } }
                    const edge = Math.max(0, 1 - (md2 - md) / 200);
                    const c = cc[mi]; const ev = Math.floor(edge * 80);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = c[0] - ev; id.data[idx + 1] = c[1] - ev; id.data[idx + 2] = c[2] - ev; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        lava_flow: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const n1 = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            const n2 = _simpleNoise2D(w, h, [2, 6, 12], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const crack = Math.exp(-n1[i] * n1[i] * 12);
                const flow = Math.max(0, Math.min(1, (n2[i] + 0.3) * 1.5));
                const lava = Math.min(1, crack * 0.7 + flow * 0.3);
                const r = Math.floor(40 + lava * 215); const g = Math.floor(10 + lava * 100); const b = Math.floor(5 + lava * 20);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        rain_drop: (ctx, w, h) => {
            ctx.fillStyle = '#5577aa'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1100);
            for (let i = 0; i < 40; i++) {
                const dx = rng() * w, dy = rng() * h, dr = 1 + rng() * 4;
                const g = ctx.createRadialGradient(dx, dy, 0, dx, dy, dr);
                g.addColorStop(0, 'rgba(200,220,240,0.7)'); g.addColorStop(1, 'rgba(100,140,180,0)');
                ctx.fillStyle = g; ctx.beginPath(); ctx.arc(dx, dy, dr, 0, Math.PI * 2); ctx.fill();
            }
        },
        barbed_wire: (ctx, w, h) => {
            ctx.fillStyle = '#3a3a3a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#888'; ctx.lineWidth = 1;
            for (let i = -h; i < w + h; i += 24) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + h, h); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(i + 12, 0); ctx.lineTo(i + 12 - h * 0.5, h); ctx.stroke();
            }
            ctx.fillStyle = '#aaa';
            for (let y = 0; y < h; y += 12) {
                for (let x = 0; x < w; x += 12) {
                    ctx.fillRect(x, y, 2, 2);
                }
            }
        },
        chainmail: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rs = 10;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / rs);
                    const cx2 = ((px + (row % 2) * (rs / 2)) % rs - rs / 2);
                    const cy2 = (py % rs - rs / 2);
                    const dist = Math.sqrt(cx2 * cx2 + cy2 * cy2);
                    const ring = Math.abs(dist - rs * 0.35) < 1.5;
                    const v = ring ? 180 : 100;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v + 5; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        brick: (ctx, w, h) => {
            const bh = 12, bw = 24;
            for (let py = 0; py < h; py += bh) {
                const row = py / bh;
                for (let px = 0; px < w; px += bw) {
                    const ox = (row % 2) * (bw / 2);
                    ctx.fillStyle = `rgb(${150 + Math.random() * 30},${70 + Math.random() * 20},${50 + Math.random() * 15})`;
                    ctx.fillRect(px + ox, py, bw - 2, bh - 2);
                }
            }
            ctx.fillStyle = '#555'; // mortar
            for (let y = 0; y < h; y += bh) { ctx.fillRect(0, y, w, 2); }
        },
        leopard: (ctx, w, h) => {
            ctx.fillStyle = '#cc9944'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1200);
            for (let i = 0; i < 30; i++) {
                const sx = rng() * w, sy = rng() * h, sr = 3 + rng() * 5;
                // Filled dark rosette center
                ctx.fillStyle = 'rgba(80,50,20,0.4)';
                ctx.beginPath(); ctx.arc(sx, sy, sr * 0.6, 0, Math.PI * 2); ctx.fill();
                // Dark ring outline
                ctx.strokeStyle = '#3a2a10'; ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.stroke();
            }
        },
        razor: (ctx, w, h) => {
            ctx.fillStyle = '#6a7a8a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(200,210,220,0.6)'; ctx.lineWidth = 1;
            for (let i = -h * 2; i < w + h; i += 20) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + h * 2, h); ctx.stroke();
            }
        },
        // --- v4.0 Patterns ---
        tron: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(0,255,200,0.8)'; ctx.lineWidth = 1.5;
            const gs = 12;
            for (let x = 0; x <= w; x += gs) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = 0; y <= h; y += gs) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            // Glow nodes at intersections
            ctx.fillStyle = 'rgba(0,255,200,0.5)';
            for (let y = 0; y <= h; y += gs) { for (let x = 0; x <= w; x += gs) { ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill(); } }
        },
        dazzle: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(1500);
            const nc = 20; const cx2 = [], cy2 = [], cv = [];
            for (let i = 0; i < nc; i++) { cx2.push(rng() * w); cy2.push(rng() * h); cv.push(rng() > 0.5 ? 220 : 40); }
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let md = 1e9, mi = 0;
                    for (let i = 0; i < nc; i++) { const d = (px - cx2[i]) ** 2 + (py - cy2[i]) ** 2; if (d < md) { md = d; mi = i; } }
                    const v = cv[mi]; const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        marble: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(1600);
            const n1 = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            const n2 = _simpleNoise2D(w, h, [2, 6, 12], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const vein = Math.sin(n1[i] * 6 + n2[i] * 4) * 0.5 + 0.5;
                const r = Math.floor(180 + vein * 55); const g = Math.floor(165 + vein * 55); const b = Math.floor(150 + vein * 55);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        mega_flake: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(1700);
            const hs = 8;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / (hs * 0.866));
                    const col = Math.floor((px + (row % 2) * (hs / 2)) / hs);
                    const hue = (row * 7 + col * 13) % 360;
                    const bright = 160 + rng() * 80;
                    const [r, g, b] = _hslToRgb(hue, 40, Math.floor(bright / 4));
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        multicam: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(1800);
            const colors = [[70, 85, 55], [100, 110, 70], [55, 65, 40], [130, 120, 90], [85, 75, 55]];
            const layers = [];
            for (let l = 0; l < 5; l++) layers.push(_simpleNoise2D(w, h, [4 + l * 2, 8 + l * 3], [0.5, 0.5], rng));
            for (let i = 0; i < w * h; i++) {
                let best = 0, bestV = -999;
                for (let l = 0; l < 5; l++) { if (layers[l][i] > bestV) { bestV = layers[l][i]; best = l; } }
                const c = colors[best];
                id.data[i * 4] = c[0]; id.data[i * 4 + 1] = c[1]; id.data[i * 4 + 2] = c[2]; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        magma_crack: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(1900);
            const nc = 15; const cx2 = [], cy2 = [];
            for (let i = 0; i < nc; i++) { cx2.push(rng() * w); cy2.push(rng() * h); }
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let d1 = 1e9, d2 = 1e9;
                    for (let i = 0; i < nc; i++) { const d = Math.sqrt((px - cx2[i]) ** 2 + (py - cy2[i]) ** 2); if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; } }
                    const edge = d2 - d1;
                    const crack = Math.max(0, 1 - edge / 8);
                    const r = Math.floor(30 + crack * 225); const g = Math.floor(10 + crack * 90); const b = Math.floor(5 + crack * 15);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- v5.0 Patterns ---
        rivet_plate: (ctx, w, h) => {
            ctx.fillStyle = '#556677'; ctx.fillRect(0, 0, w, h);
            // Panel seam lines
            ctx.strokeStyle = 'rgba(30,30,30,0.6)'; ctx.lineWidth = 1;
            const panel = 20;
            for (let y = 0; y < h; y += panel) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            for (let x = 0; x < w; x += panel) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            // Rivet dots at intersections
            ctx.fillStyle = 'rgba(200,210,220,0.9)';
            for (let y = 0; y < h; y += panel) {
                for (let x = 0; x < w; x += panel) {
                    ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        frost_crystal: (ctx, w, h) => {
            ctx.fillStyle = '#88bbdd'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(2100);
            ctx.strokeStyle = 'rgba(220,240,255,0.7)'; ctx.lineWidth = 1;
            for (let b = 0; b < 6; b++) {
                let sx = rng() * w, sy = rng() * h;
                for (let a = 0; a < 6; a++) {
                    const angle = a * Math.PI / 3;
                    ctx.beginPath(); ctx.moveTo(sx, sy);
                    let bx = sx, by = sy;
                    for (let seg = 0; seg < 8; seg++) {
                        bx += Math.cos(angle) * (3 + rng() * 2); by += Math.sin(angle) * (3 + rng() * 2);
                        ctx.lineTo(bx, by);
                        if (rng() < 0.4) {
                            const fork = angle + (rng() > 0.5 ? 0.5 : -0.5);
                            ctx.moveTo(bx, by);
                            ctx.lineTo(bx + Math.cos(fork) * 6, by + Math.sin(fork) * 6);
                            ctx.moveTo(bx, by);
                        }
                    }
                    ctx.stroke();
                }
            }
        },
        wave: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const v1 = Math.sin(py * 0.15 + Math.sin(px * 0.08) * 2) * 0.5 + 0.5;
                    const v2 = Math.sin(px * 0.1 + py * 0.05) * 0.3 + 0.5;
                    const t = (v1 + v2) * 0.5;
                    const r = Math.floor(50 + t * 80); const g = Math.floor(100 + t * 80); const b = Math.floor(140 + t * 70);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        spiderweb: (ctx, w, h) => {
            ctx.fillStyle = '#2a2a3a'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(180,180,200,0.6)'; ctx.lineWidth = 0.8;
            // Radial threads
            for (let a = 0; a < 12; a++) {
                const angle = a * Math.PI / 6;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(angle) * w, cy + Math.sin(angle) * h);
                ctx.stroke();
            }
            // Concentric rings
            for (let r = 6; r < Math.max(w, h); r += 6) {
                ctx.beginPath();
                for (let a = 0; a <= 12; a++) {
                    const angle = a * Math.PI / 6;
                    const wobble = r + Math.sin(a * 1.5) * 2;
                    const x = cx + Math.cos(angle) * wobble;
                    const y = cy + Math.sin(angle) * wobble;
                    a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        },
        topographic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(2400);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const elev = (noise[i] + 1) * 0.5;
                const contour = Math.abs(elev * 10 - Math.round(elev * 10));
                const line = contour < 0.08 ? 1 : 0;
                const bg = Math.floor(60 + elev * 80);
                const r = line ? 100 : bg - 10; const g = line ? 140 : bg + 10; const b = line ? 90 : bg - 5;
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        crosshatch: (ctx, w, h) => {
            ctx.fillStyle = '#5a5a6a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(180,180,200,0.4)'; ctx.lineWidth = 0.8;
            const sp = 6;
            for (let i = -h; i < w + h; i += sp) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + h, h); ctx.stroke(); }
            for (let i = -h; i < w + h; i += sp) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i - h, h); ctx.stroke(); }
            // Second layer rotated slightly
            ctx.strokeStyle = 'rgba(160,160,180,0.25)'; ctx.lineWidth = 0.5;
            for (let i = -h; i < w + h; i += sp * 1.3) { ctx.beginPath(); ctx.moveTo(i + 3, 0); ctx.lineTo(i + h + 3, h); ctx.stroke(); }
        },
        chevron: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const cw = 16, ch = 10;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const cy2 = py % ch; const cx2 = px % cw;
                    const mid = cw / 2;
                    const vShape = Math.abs(cx2 - mid) / mid;
                    const stripe = Math.abs(cy2 - vShape * ch / 2) < 2;
                    const v = stripe ? 180 : 80; const g = stripe ? 200 : 100; const b = stripe ? 140 : 80;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        celtic_knot: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(2700);
            const n1 = _simpleNoise2D(w, h, [4, 8], [0.5, 0.5], rng);
            const n2 = _simpleNoise2D(w, h, [3, 6], [0.5, 0.5], rng);
            for (let i = 0; i < w * h; i++) {
                const band1 = Math.sin(n1[i] * 8) * 0.5 + 0.5;
                const band2 = Math.sin(n2[i] * 8) * 0.5 + 0.5;
                const weave = Math.max(band1, band2);
                const knot = weave > 0.7 ? 1 : 0;
                const r = Math.floor(knot ? 180 : 70); const g = Math.floor(knot ? 150 : 55); const b = Math.floor(knot ? 90 : 40);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        skull: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const ss = 20; const rng = _seededRng(2800);
            for (let sy = 0; sy < h + ss; sy += ss) {
                for (let sx = 0; sx < w + ss; sx += ss) {
                    const cx = sx + ss / 2, cy = sy + ss / 2;
                    // Cranium
                    ctx.fillStyle = 'rgba(180,180,170,0.8)';
                    ctx.beginPath(); ctx.ellipse(cx, cy - 2, ss * 0.25, ss * 0.3, 0, 0, Math.PI * 2); ctx.fill();
                    // Eyes
                    ctx.fillStyle = '#1a1a1a';
                    ctx.beginPath(); ctx.arc(cx - 2.5, cy - 2, 1.5, 0, Math.PI * 2); ctx.fill();
                    ctx.beginPath(); ctx.arc(cx + 2.5, cy - 2, 1.5, 0, Math.PI * 2); ctx.fill();
                    // Jaw
                    ctx.fillStyle = 'rgba(160,160,150,0.6)';
                    ctx.fillRect(cx - 3, cy + 2, 6, 3);
                }
            }
        },
        damascus: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(2900);
            const n1 = _simpleNoise2D(w, h, [2, 4, 8], [0.3, 0.4, 0.3], rng);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const i = py * w + px;
                    const wave = Math.sin(py * 0.15 + n1[i] * 5) * 0.5 + 0.5;
                    const v = Math.floor(100 + wave * 100);
                    id.data[i * 4] = v; id.data[i * 4 + 1] = v + 5; id.data[i * 4 + 2] = v + 10; id.data[i * 4 + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        houndstooth: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const cs = 10;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const cx2 = Math.floor(px / cs) % 4; const cy2 = Math.floor(py / cs) % 4;
                    const lx = px % cs; const ly = py % cs;
                    let dark = false;
                    if ((cx2 + cy2) % 2 === 0) dark = true;
                    if (cx2 % 2 === 0 && ly < lx) dark = !dark;
                    if (cy2 % 2 === 0 && lx < ly) dark = !dark;
                    const v = dark ? 50 : 190;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v + 5; id.data[idx + 2] = v + 10; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        plaid: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const bx = (px % 20) < 10; const by = (py % 20) < 10;
                    const sx = (px % 8) < 4; const sy = (py % 8) < 4;
                    let r = 70, g = 40, b = 40;
                    if (bx !== by) { r = 160; g = 50; b = 50; }
                    if (sx !== sy) { r += 30; g += 20; b += 20; }
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- v5.5 Patterns ---
        fracture: (ctx, w, h) => {
            ctx.fillStyle = '#667788'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(40,40,40,0.8)'; ctx.lineWidth = 1;
            // Impact points with radial cracks
            const impacts = [{ x: w * 0.3, y: h * 0.4 }, { x: w * 0.7, y: h * 0.6 }, { x: w * 0.5, y: h * 0.2 }];
            for (const imp of impacts) {
                const nSpokes = 10;
                for (let s = 0; s < nSpokes; s++) {
                    const angle = s * Math.PI * 2 / nSpokes + (imp.x % 5) * 0.1;
                    const len = Math.max(w, h) * 0.35;
                    ctx.beginPath(); ctx.moveTo(imp.x, imp.y);
                    ctx.lineTo(imp.x + Math.cos(angle) * len, imp.y + Math.sin(angle) * len);
                    ctx.stroke();
                }
                // Stress rings
                for (let r = 10; r < 40; r += 12) {
                    ctx.beginPath(); ctx.arc(imp.x, imp.y, r, 0, Math.PI * 2); ctx.stroke();
                }
            }
        },
        ember_mesh: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a0a'; ctx.fillRect(0, 0, w, h);
            const gs = 10;
            // Hot wire grid
            ctx.strokeStyle = 'rgba(255,100,0,0.6)'; ctx.lineWidth = 1;
            for (let x = 0; x <= w; x += gs) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = 0; y <= h; y += gs) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            // Glowing ember nodes
            ctx.fillStyle = 'rgba(255,200,50,0.9)';
            for (let y = 0; y <= h; y += gs) {
                for (let x = 0; x <= w; x += gs) {
                    ctx.beginPath(); ctx.arc(x, y, 2.5, 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        turbine: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const cx = w / 2, cy = h / 2;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const dx = px - cx, dy = py - cy;
                    const angle = Math.atan2(dy, dx);
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const blade = Math.sin(angle * 6 + dist * 0.3) * 0.5 + 0.5;
                    const fade = Math.min(1, dist / (Math.max(w, h) * 0.5));
                    const v = Math.floor(80 + blade * fade * 120);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v - 5; id.data[idx + 1] = v; id.data[idx + 2] = v + 15; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        static_noise: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(3400);
            const bs = 3;
            for (let py = 0; py < h; py += bs) {
                for (let px = 0; px < w; px += bs) {
                    const v = Math.floor(rng() * 220);
                    for (let dy = 0; dy < bs && py + dy < h; dy++) {
                        for (let dx = 0; dx < bs && px + dx < w; dx++) {
                            const idx = ((py + dy) * w + (px + dx)) * 4;
                            id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v; id.data[idx + 3] = 255;
                        }
                    }
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        razor_wire: (ctx, w, h) => {
            ctx.fillStyle = '#3a3a3a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(180,180,190,0.7)'; ctx.lineWidth = 1.5;
            // Coiled helical wires
            for (let row = 0; row < 3; row++) {
                const cy = h * 0.2 + row * h * 0.3;
                ctx.beginPath();
                for (let px = 0; px < w; px++) {
                    const py = cy + Math.sin(px * 0.3) * 6;
                    px === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                }
                ctx.stroke();
                // Barb spikes
                ctx.strokeStyle = 'rgba(200,200,210,0.8)'; ctx.lineWidth = 1;
                for (let px = 0; px < w; px += 8) {
                    const py = cy + Math.sin(px * 0.3) * 6;
                    ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px + 3, py - 4); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px - 3, py + 4); ctx.stroke();
                }
                ctx.strokeStyle = 'rgba(180,180,190,0.7)'; ctx.lineWidth = 1.5;
            }
        },
        // --- v6.0 Swatch Fixes ---
        ekg: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a0a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(0,220,80,0.9)'; ctx.lineWidth = 1.5;
            // Draw 2 EKG pulse lines
            for (let row = 0; row < 2; row++) {
                const cy = h * 0.3 + row * h * 0.4;
                ctx.beginPath();
                for (let px = 0; px < w; px++) {
                    const t = (px / w) * 4 * Math.PI;
                    const phase = px % Math.floor(w * 0.5);
                    const norm = phase / Math.floor(w * 0.5);
                    let y = cy;
                    if (norm > 0.35 && norm < 0.4) y = cy - h * 0.15;
                    else if (norm > 0.4 && norm < 0.42) y = cy + h * 0.25;
                    else if (norm > 0.42 && norm < 0.48) y = cy - h * 0.35;
                    else if (norm > 0.48 && norm < 0.52) y = cy + h * 0.1;
                    else if (norm > 0.52 && norm < 0.55) y = cy - h * 0.05;
                    px === 0 ? ctx.moveTo(px, y) : ctx.lineTo(px, y);
                }
                ctx.stroke();
            }
            // Subtle grid
            ctx.strokeStyle = 'rgba(0,100,40,0.2)'; ctx.lineWidth = 0.5;
            for (let x = 0; x < w; x += 8) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = 0; y < h; y += 8) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        checkered_flag: (ctx, w, h) => {
            const cols = 4, rows = 4; const cw = w / cols, ch = h / rows;
            for (let row = 0; row < rows; row++) {
                for (let col = 0; col < cols; col++) {
                    const wave = (y) => Math.sin(y / h * 3) * (ch * 0.2);
                    const x0 = col * cw, x1 = (col + 1) * cw;
                    const y0 = row * ch, y1 = (row + 1) * ch;
                    ctx.fillStyle = ((col + row) % 2) ? '#000000' : '#ffffff';
                    ctx.beginPath();
                    ctx.moveTo(x0, y0 + wave(y0));
                    ctx.lineTo(x1, y0 + wave(y0));
                    ctx.lineTo(x1, y1 + wave(y1));
                    ctx.lineTo(x0, y1 + wave(y1));
                    ctx.closePath(); ctx.fill();
                }
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        finish_line: (ctx, w, h) => {
            const cs = 6;
            for (let py = 0; py < h; py += cs) {
                for (let px = 0; px < w; px += cs) {
                    ctx.fillStyle = ((Math.floor(px / cs) + Math.floor(py / cs)) % 2) ? '#222' : '#eee';
                    ctx.fillRect(px, py, cs, cs);
                }
            }
        },
        zebra: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wave = Math.sin(py * 0.25 + Math.sin(px * 0.06) * 1.5);
                    const v = wave > 0 ? 240 : 30;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        matrix_rain: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4100);
            ctx.font = '6px monospace';
            const cols = Math.ceil(w / 6);
            for (let c = 0; c < cols; c++) {
                const colLen = Math.floor(3 + rng() * 8);
                const startY = Math.floor(rng() * h);
                for (let r = 0; r < colLen; r++) {
                    const cy = startY + r * 7;
                    if (cy >= h) break;
                    const bright = r === colLen - 1 ? 255 : 80 + Math.floor(rng() * 100);
                    ctx.fillStyle = `rgba(0,${bright},${Math.floor(bright * 0.3)},${0.6 + rng() * 0.4})`;
                    const ch = String.fromCharCode(0x30A0 + Math.floor(rng() * 96));
                    ctx.fillText(ch, c * 6, cy);
                }
            }
        },
        argyle: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const dw = 16, dh = 20;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const dx = ((px % dw) - dw / 2) / dw * 2;
                    const dy = ((py % dh) - dh / 2) / dh * 2;
                    const diamond1 = (Math.abs(dx) + Math.abs(dy)) < 0.8;
                    const dx2 = (((px + dw / 2) % dw) - dw / 2) / dw * 2;
                    const dy2 = (((py + dh / 2) % dh) - dh / 2) / dh * 2;
                    const diamond2 = (Math.abs(dx2) + Math.abs(dy2)) < 0.8;
                    let r = 60, g = 50, b = 80;
                    if (diamond1) { r = 120; g = 80; b = 120; }
                    if (diamond2) { r = 90; g = 60; b = 100; }
                    // Thin cross lines
                    if (px % dw === 0 || py % dh === 0) { r = 140; g = 120; b = 140; }
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        herringbone: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const bw = 8, bh = 4;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const row = Math.floor(py / bh);
                    const col = Math.floor(px / bw);
                    const lx = px % bw; const ly = py % bh;
                    const up = (row + col) % 2 === 0;
                    const diag = up ? (lx / bw + ly / bh) : (lx / bw + (1 - ly / bh));
                    const stripe = Math.abs(diag - 1) < 0.15;
                    const v = stripe ? 180 : 90;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v + 5; id.data[idx + 2] = v + 15; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        perforated: (ctx, w, h) => {
            ctx.fillStyle = '#555566'; ctx.fillRect(0, 0, w, h);
            const sp = 8, r = 2.5;
            ctx.fillStyle = '#222';
            for (let y = sp / 2; y < h; y += sp) {
                for (let x = sp / 2; x < w; x += sp) {
                    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
                }
            }
            // Highlight ring
            ctx.strokeStyle = 'rgba(180,180,190,0.3)'; ctx.lineWidth = 0.5;
            for (let y = sp / 2; y < h; y += sp) {
                for (let x = sp / 2; x < w; x += sp) {
                    ctx.beginPath(); ctx.arc(x, y, r + 0.5, 0, Math.PI * 2); ctx.stroke();
                }
            }
        },
        fingerprint: (ctx, w, h) => {
            ctx.fillStyle = '#887766'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(60,40,30,0.5)'; ctx.lineWidth = 0.8;
            for (let r = 3; r < Math.max(w, h) * 0.7; r += 2.5) {
                ctx.beginPath();
                for (let a = 0; a <= Math.PI * 2; a += 0.05) {
                    const wobble = Math.sin(a * 8 + r * 0.3) * 1.5 + Math.sin(a * 3 - r * 0.2) * 1;
                    const x = cx + Math.cos(a) * (r + wobble);
                    const y = cy + Math.sin(a) * (r * 0.7 + wobble * 0.7);
                    a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        },
        // --- v6.0 Tier 2 Swatch Fixes ---
        glitch_scan: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff'; ctx.fillRect(0, h * 0.45, w, h * 0.12);
            ctx.fillStyle = '#00ffff'; ctx.fillRect(-3, h * 0.42, w + 6, h * 0.08);
            ctx.fillStyle = '#ff00ff'; ctx.fillRect(3, h * 0.5, w + 6, h * 0.08);
            ctx.strokeStyle = '#000000'; ctx.lineWidth = 1;
            for (let y = 0; y < h; y += 4) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        denim: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const diag = (px + py) % 4;
                    const v = diag < 2 ? 0.7 : 0.5;
                    const r = Math.floor(50 + v * 30); const g = Math.floor(70 + v * 40); const b = Math.floor(130 + v * 40);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        _broken_steampunk_gears: (ctx, w, h) => {
            ctx.fillStyle = '#2a2215'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4300);
            ctx.strokeStyle = 'rgba(180,140,70,0.8)'; ctx.lineWidth = 1;
            for (let i = 0; i < 6; i++) {
                const gx = rng() * w, gy = rng() * h, gr = 6 + rng() * 10;
                const teeth = Math.floor(8 + rng() * 6);
                // Outer teeth
                ctx.beginPath();
                for (let a = 0; a <= Math.PI * 2; a += 0.05) {
                    const tooth = Math.sin(a * teeth) * 0.15;
                    const r2 = gr * (1 + tooth);
                    const x = gx + Math.cos(a) * r2, y = gy + Math.sin(a) * r2;
                    a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.closePath(); ctx.stroke();
                // Center hub
                ctx.beginPath(); ctx.arc(gx, gy, gr * 0.3, 0, Math.PI * 2); ctx.stroke();
                // Spokes
                for (let s = 0; s < 4; s++) {
                    const sa = s * Math.PI / 2 + rng() * 0.3;
                    ctx.beginPath(); ctx.moveTo(gx + Math.cos(sa) * gr * 0.3, gy + Math.sin(sa) * gr * 0.3);
                    ctx.lineTo(gx + Math.cos(sa) * gr * 0.85, gy + Math.sin(sa) * gr * 0.85); ctx.stroke();
                }
            }
        },
        _broken_mandala: (ctx, w, h) => {
            ctx.fillStyle = '#2a1a2a'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(200,120,170,0.7)'; ctx.lineWidth = 0.8;
            for (let ring = 4; ring < Math.max(w, h) * 0.6; ring += 5) {
                const petals = Math.floor(6 + ring / 8);
                ctx.beginPath();
                for (let a = 0; a <= Math.PI * 2; a += 0.03) {
                    const petal = Math.cos(a * petals) * ring * 0.15;
                    const r = ring + petal;
                    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
                    a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.closePath(); ctx.stroke();
            }
        },
        art_deco: (ctx, w, h) => {
            ctx.fillStyle = '#1a1510'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(200,170,80,0.7)'; ctx.lineWidth = 1;
            const cx = w / 2, cy = h;
            // Radiating fan lines
            for (let a = -Math.PI * 0.8; a <= -Math.PI * 0.2; a += Math.PI / 12) {
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(a) * w, cy + Math.sin(a) * h * 1.5);
                ctx.stroke();
            }
            // Concentric arcs
            for (let r = 10; r < Math.max(w, h); r += 12) {
                ctx.beginPath(); ctx.arc(cx, cy, r, -Math.PI * 0.8, -Math.PI * 0.2); ctx.stroke();
            }
        },
        tornado: (ctx, w, h) => {
            ctx.fillStyle = '#556677'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(100,120,140,0.6)'; ctx.lineWidth = 1;
            for (let a = 0; a < Math.PI * 8; a += 0.05) {
                const r = a * 2.5;
                const x = cx + Math.cos(a) * r * 0.3;
                const y = cy + Math.sin(a) * r * 0.3;
                if (a < 0.1) ctx.beginPath();
                ctx.lineTo(x, y);
            }
            ctx.stroke();
            // Inner tight spiral
            ctx.strokeStyle = 'rgba(60,80,100,0.8)'; ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let a = 0; a < Math.PI * 12; a += 0.05) {
                const r = a * 1.2;
                ctx.lineTo(cx + Math.cos(a) * r * 0.2, cy + Math.sin(a) * r * 0.2);
            }
            ctx.stroke();
        },
        atomic_orbital: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a2a'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(255,50,100,0.6)'; ctx.lineWidth = 1;
            // 3 orbital ellipses at different angles
            for (let o = 0; o < 3; o++) {
                const angle = o * Math.PI / 3;
                ctx.beginPath();
                for (let a = 0; a <= Math.PI * 2; a += 0.05) {
                    const rx = w * 0.4, ry = h * 0.12;
                    const px2 = Math.cos(a) * rx;
                    const py2 = Math.sin(a) * ry;
                    const x = cx + px2 * Math.cos(angle) - py2 * Math.sin(angle);
                    const y = cy + px2 * Math.sin(angle) + py2 * Math.cos(angle);
                    a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.closePath(); ctx.stroke();
            }
            // Nucleus
            ctx.fillStyle = 'rgba(255,80,120,0.9)';
            ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill();
        },
        dna_helix: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a2a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(80,140,200,0.8)'; ctx.lineWidth = 1.5;
            const cx = w / 2;
            // Two helical strands
            for (let strand = 0; strand < 2; strand++) {
                ctx.beginPath();
                for (let py = 0; py < h; py++) {
                    const phase = strand * Math.PI;
                    const x = cx + Math.sin(py * 0.15 + phase) * w * 0.3;
                    py === 0 ? ctx.moveTo(x, py) : ctx.lineTo(x, py);
                }
                ctx.stroke();
            }
            // Rungs
            ctx.strokeStyle = 'rgba(60,120,180,0.4)'; ctx.lineWidth = 0.8;
            for (let py = 0; py < h; py += 6) {
                const x1 = cx + Math.sin(py * 0.15) * w * 0.3;
                const x2 = cx + Math.sin(py * 0.15 + Math.PI) * w * 0.3;
                ctx.beginPath(); ctx.moveTo(x1, py); ctx.lineTo(x2, py); ctx.stroke();
            }
        },
        aztec: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const bs = 6;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const bx = Math.floor(px / bs); const by = Math.floor(py / bs);
                    const step = ((bx + by) % 3 === 0 || (bx - by + 100) % 3 === 0) ? 1 : 0;
                    const r = step ? 180 : 80; const g = step ? 120 : 55; const b = step ? 50 : 35;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        grating: (ctx, w, h) => {
            ctx.fillStyle = '#222'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#667777';
            const bw = 4, gap = 3;
            for (let x = 0; x < w; x += bw + gap) { ctx.fillRect(x, 0, bw, h); }
        },
        shokk_fracture: (ctx, w, h) => {
            ctx.fillStyle = '#551515'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(220,60,40,0.8)'; ctx.lineWidth = 1.5;
            // Radial cracks from center impact
            for (let s = 0; s < 10; s++) {
                const angle = s * Math.PI * 2 / 10;
                const len = Math.max(w, h) * 0.5;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(angle) * len, cy + Math.sin(angle) * len);
                ctx.stroke();
            }
            // Stress rings
            ctx.strokeStyle = 'rgba(200,50,30,0.4)'; ctx.lineWidth = 1;
            for (let r = 8; r < 30; r += 8) {
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        shokk_scream: (ctx, w, h) => {
            ctx.fillStyle = '#2a0a1a'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(230,30,80,0.6)'; ctx.lineWidth = 1;
            // Expanding distortion rings
            for (let r = 4; r < Math.max(w, h) * 0.6; r += 4) {
                ctx.beginPath();
                for (let a = 0; a <= Math.PI * 2; a += 0.05) {
                    const wobble = Math.sin(a * 6 + r * 0.3) * r * 0.08;
                    const x = cx + Math.cos(a) * (r + wobble);
                    const y = cy + Math.sin(a) * (r + wobble);
                    a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.closePath(); ctx.stroke();
            }
        },
        shokk_bolt: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a18'; ctx.fillRect(0, 0, w, h);
            // Fractal branching lightning bolts
            ctx.strokeStyle = 'rgba(255,220,60,0.9)'; ctx.lineWidth = 2;
            ctx.shadowColor = '#ffcc22'; ctx.shadowBlur = 6;
            const drawBolt = (x0, y0, x1, y1, w2, depth) => {
                if (depth > 4) return;
                const segs = 4; ctx.beginPath(); ctx.moveTo(x0, y0);
                let px = x0, py = y0;
                for (let i = 1; i <= segs; i++) {
                    const t = i / segs;
                    const jx = (Math.random() - 0.5) * 20 * (1 - depth * 0.2);
                    const mx = x0 + (x1 - x0) * t + jx;
                    const my = y0 + (y1 - y0) * t + (Math.random() - 0.5) * 8;
                    ctx.lineTo(mx, my);
                    if (Math.random() < 0.3 && depth < 3) {
                        drawBolt(mx, my, mx + (Math.random() - 0.5) * 25, my + h * 0.2, w2 * 0.5, depth + 1);
                    }
                    px = mx; py = my;
                }
                ctx.stroke();
            };
            ctx.lineWidth = 2.5; drawBolt(w * 0.3, 0, w * 0.5, h, 2.5, 0);
            ctx.lineWidth = 1.5; drawBolt(w * 0.7, 0, w * 0.4, h, 1.5, 0);
            // Corona glow
            const grad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.6);
            grad.addColorStop(0, 'rgba(255,200,50,0.15)'); grad.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = grad; ctx.fillRect(0, 0, w, h);
            ctx.shadowBlur = 0;
        },
        shokk_pulse_wave: (ctx, w, h) => {
            ctx.fillStyle = '#0a1525'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            // Concentric rings alternating chrome and matte colors
            for (let r = 3; r < Math.max(w, h) * 0.7; r += 4) {
                const phase = r / 4;
                const isChrome = Math.sin(phase * 1.2) > 0;
                ctx.strokeStyle = isChrome ? 'rgba(100,160,220,0.6)' : 'rgba(40,60,80,0.4)';
                ctx.lineWidth = isChrome ? 1.5 : 1;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
            // EKG spike on one radial line
            ctx.strokeStyle = 'rgba(100,200,255,0.8)'; ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.moveTo(cx, cy);
            ctx.lineTo(cx + 10, cy - 8); ctx.lineTo(cx + 14, cy + 12);
            ctx.lineTo(cx + 18, cy - 4); ctx.lineTo(w * 0.85, cy);
            ctx.stroke();
        },
        shokk_singularity: (ctx, w, h) => {
            ctx.fillStyle = '#000008'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            // Accretion disk spiral
            ctx.strokeStyle = 'rgba(120,80,200,0.5)'; ctx.lineWidth = 1;
            for (let a = 0; a < Math.PI * 8; a += 0.05) {
                const r = 5 + a * 3;
                if (r > w * 0.45) break;
                const x = cx + Math.cos(a) * r;
                const y = cy + Math.sin(a) * r * 0.6;
                a < 0.05 ? ctx.beginPath() && ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }
            ctx.stroke();
            // Event horizon glow
            const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 12);
            grad.addColorStop(0, 'rgba(200,150,255,0.8)'); grad.addColorStop(0.5, 'rgba(80,40,160,0.4)');
            grad.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = grad; ctx.fillRect(0, 0, w, h);
            // Gravity well rings (log spacing)
            ctx.strokeStyle = 'rgba(60,40,120,0.4)'; ctx.lineWidth = 0.5;
            for (let i = 1; i < 8; i++) {
                const r = Math.log(i + 1) * 15;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        shokk_nebula: (ctx, w, h) => {
            // Cosmic gas cloud with star knots
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const nx = px / w, ny = py / h;
                    let dust = 0;
                    dust += Math.sin(nx * 12 + ny * 8) * Math.cos(ny * 10 + nx * 6) * 0.4;
                    dust += Math.sin(nx * 20 + 1.5) * Math.cos(ny * 15 + 2.3) * 0.3;
                    dust += Math.sin(nx * 30 + ny * 25) * 0.2;
                    dust = (dust + 0.9) / 1.8;
                    const r = Math.floor(40 + dust * 60);
                    const g = Math.floor(20 + dust * 30);
                    const b = Math.floor(80 + dust * 120);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
            // Star knots
            ctx.shadowColor = '#aaccff'; ctx.shadowBlur = 4;
            [[0.3, 0.3], [0.7, 0.5], [0.5, 0.8], [0.2, 0.7], [0.8, 0.2]].forEach(([sx, sy]) => {
                const sg = ctx.createRadialGradient(sx * w, sy * h, 0, sx * w, sy * h, 5);
                sg.addColorStop(0, 'rgba(200,220,255,0.8)'); sg.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = sg; ctx.fillRect(0, 0, w, h);
            });
            ctx.shadowBlur = 0;
        },
        shokk_predator: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a1a'; ctx.fillRect(0, 0, w, h);
            // Hexagonal camo cells with shimmer
            const hexR = 8;
            const hexH = hexR * Math.sqrt(3);
            ctx.lineWidth = 0.8;
            for (let row = -1; row < h / hexH + 1; row++) {
                for (let col = -1; col < w / (hexR * 1.5) + 1; col++) {
                    const cx2 = col * hexR * 1.5;
                    const cy2 = row * hexH + (col % 2 ? hexH / 2 : 0);
                    // Each cell has unique shimmer brightness
                    const shimmer = Math.abs(Math.sin(col * 3.7 + row * 2.3)) * 0.5 + 0.2;
                    ctx.fillStyle = `rgba(40,${Math.floor(100 + shimmer * 80)},${Math.floor(100 + shimmer * 60)},${shimmer})`;
                    ctx.beginPath();
                    for (let a = 0; a < 6; a++) {
                        const angle = Math.PI / 3 * a + Math.PI / 6;
                        const x = cx2 + hexR * Math.cos(angle);
                        const y = cy2 + hexR * Math.sin(angle);
                        a === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                    }
                    ctx.closePath(); ctx.fill();
                    ctx.strokeStyle = 'rgba(60,180,180,0.3)'; ctx.stroke();
                }
            }
            // Distortion ripple overlay
            ctx.globalAlpha = 0.15;
            const rippleGrad = ctx.createLinearGradient(0, 0, w, h);
            rippleGrad.addColorStop(0, '#448888'); rippleGrad.addColorStop(0.5, 'transparent'); rippleGrad.addColorStop(1, '#448888');
            ctx.fillStyle = rippleGrad; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 1;
        },
        shokk_bioform: (ctx, w, h) => {
            // Organic reaction-diffusion spots
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const nx = px / w, ny = py / h;
                    let v = 0;
                    v += Math.sin(nx * 25 + ny * 15 + 1.2);
                    v += Math.sin(nx * 18 - ny * 22 + 3.7);
                    v += Math.sin(nx * 30 + ny * 10 + 0.5);
                    v += Math.sin(-nx * 12 + ny * 28 + 2.1);
                    v = v / 4;
                    const isSpot = v > 0 ? 1 : 0;
                    const r = isSpot ? Math.floor(30 + Math.abs(v) * 80) : Math.floor(50 + Math.abs(v) * 40);
                    const g = isSpot ? Math.floor(80 + Math.abs(v) * 120) : Math.floor(40 + Math.abs(v) * 30);
                    const b = isSpot ? Math.floor(40 + Math.abs(v) * 60) : Math.floor(60 + Math.abs(v) * 50);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        shokk_tesseract: (ctx, w, h) => {
            ctx.fillStyle = '#0a0820'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            const s1 = w * 0.38, s2 = w * 0.22;
            // Outer cube
            ctx.strokeStyle = 'rgba(140,100,220,0.8)'; ctx.lineWidth = 1.5;
            ctx.strokeRect(cx - s1, cy - s1, s1 * 2, s1 * 2);
            // Inner cube (rotated 45deg = diamond)
            ctx.strokeStyle = 'rgba(100,180,240,0.7)'; ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(cx, cy - s2); ctx.lineTo(cx + s2, cy);
            ctx.lineTo(cx, cy + s2); ctx.lineTo(cx - s2, cy);
            ctx.closePath(); ctx.stroke();
            // Connecting lines (perspective edges)
            ctx.strokeStyle = 'rgba(120,140,200,0.4)'; ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cx - s1, cy - s1); ctx.lineTo(cx, cy - s2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(cx + s1, cy - s1); ctx.lineTo(cx + s2, cy); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(cx + s1, cy + s1); ctx.lineTo(cx, cy + s2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(cx - s1, cy + s1); ctx.lineTo(cx - s2, cy); ctx.stroke();
            // Vertex dots
            ctx.fillStyle = 'rgba(200,180,255,0.8)';
            [[cx - s1, cy - s1], [cx + s1, cy - s1], [cx + s1, cy + s1], [cx - s1, cy + s1],
            [cx, cy - s2], [cx + s2, cy], [cx, cy + s2], [cx - s2, cy]].forEach(([x, y]) => {
                ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
            });
        },
        shokk_plasma_storm: (ctx, w, h) => {
            ctx.fillStyle = '#0a0018'; ctx.fillRect(0, 0, w, h);
            // Multiple plasma epicenters with branching
            const sources = [[w * 0.25, h * 0.3], [w * 0.7, h * 0.6], [w * 0.5, h * 0.15]];
            ctx.shadowColor = '#dd44ff'; ctx.shadowBlur = 4;
            sources.forEach(([sx, sy]) => {
                const arms = 5;
                for (let a = 0; a < arms; a++) {
                    const angle = a * Math.PI * 2 / arms + Math.random() * 0.3;
                    const len = 15 + Math.random() * 15;
                    ctx.strokeStyle = `rgba(220,80,255,${0.5 + Math.random() * 0.3})`;
                    ctx.lineWidth = 1.5;
                    ctx.beginPath(); ctx.moveTo(sx, sy);
                    ctx.lineTo(sx + Math.cos(angle) * len, sy + Math.sin(angle) * len);
                    ctx.stroke();
                }
                // Core glow
                const cg = ctx.createRadialGradient(sx, sy, 0, sx, sy, 8);
                cg.addColorStop(0, 'rgba(255,100,255,0.6)'); cg.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
            });
            ctx.shadowBlur = 0;
        },
        shokk_waveform: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a15'; ctx.fillRect(0, 0, w, h);
            const bands = 12;
            const bandH = h / bands;
            for (let b = 0; b < bands; b++) {
                const y = b * bandH;
                const amp = 0.3 + Math.abs(Math.sin(b * 0.8)) * 0.7;
                // Frequency band bar
                ctx.fillStyle = `rgba(30,${Math.floor(180 + amp * 60)},${Math.floor(140 + amp * 40)},${0.15 + amp * 0.3})`;
                const barW = w * amp * 0.8;
                ctx.fillRect(w * 0.1, y + 1, barW, bandH - 2);
                // Small bars within
                ctx.fillStyle = `rgba(50,${Math.floor(220 * amp)},${Math.floor(170 * amp)},0.6)`;
                for (let bx = 0; bx < barW; bx += 4) {
                    const bh = bandH * amp * Math.abs(Math.sin(bx * 0.5 + b)) * 0.6;
                    ctx.fillRect(w * 0.1 + bx, y + bandH / 2 - bh / 2, 2, bh);
                }
            }
            // Center EKG line
            ctx.strokeStyle = 'rgba(50,255,200,0.7)'; ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.moveTo(0, h / 2);
            ctx.lineTo(w * 0.4, h / 2); ctx.lineTo(w * 0.45, h * 0.3);
            ctx.lineTo(w * 0.5, h * 0.7); ctx.lineTo(w * 0.55, h * 0.4);
            ctx.lineTo(w * 0.6, h / 2); ctx.lineTo(w, h / 2);
            ctx.stroke();
        },
        aurora_bands: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const wave = Math.sin(py * 0.1 + Math.sin(px * 0.05) * 3) * 0.5 + 0.5;
                    const wave2 = Math.sin(py * 0.06 + px * 0.03) * 0.3 + 0.5;
                    const t = (wave + wave2) * 0.5;
                    const r = Math.floor(20 + t * 40); const g = Math.floor(120 + t * 100); const b = Math.floor(80 + t * 80);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        crocodile: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const sw2 = 10, sh2 = 10;
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const sx = px % sw2; const sy = py % sh2;
                    const ex = Math.min(sx, sw2 - sx) / (sw2 * 0.5);
                    const ey = Math.min(sy, sh2 - sy) / (sh2 * 0.5);
                    const c = Math.min(1, Math.min(ex, ey) * 3);
                    const v = Math.floor(40 + c * 60); const g = Math.floor(55 + c * 45);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = g; id.data[idx + 2] = v - 10; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- v6.0 Tier 3a: Iconic & Symbol Patterns ---
        biohazard: (ctx, w, h) => {
            ctx.fillStyle = '#111'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#44cc22'; ctx.lineWidth = 2;
            const cx = w / 2, cy = h / 2, r = Math.min(w, h) * 0.35;
            ctx.beginPath(); ctx.arc(cx, cy, r * 0.25, 0, Math.PI * 2); ctx.stroke();
            for (let i = 0; i < 3; i++) {
                const a = i * Math.PI * 2 / 3 - Math.PI / 2;
                const x1 = cx + Math.cos(a) * r * 0.35, y1 = cy + Math.sin(a) * r * 0.35;
                ctx.beginPath(); ctx.arc(x1, y1, r * 0.45, a - 0.8, a + 0.8); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * r * 0.15, cy + Math.sin(a) * r * 0.15);
                ctx.lineTo(cx + Math.cos(a) * r * 0.85, cy + Math.sin(a) * r * 0.85); ctx.stroke();
            }
        },
        qr_code: (ctx, w, h) => {
            ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4200); const cs = Math.max(3, Math.floor(w / 16));
            ctx.fillStyle = '#111';
            for (let py = 0; py < h; py += cs) { for (let px = 0; px < w; px += cs) { if (rng() > 0.45) ctx.fillRect(px, py, cs, cs); } }
            ctx.fillStyle = '#111';
            const drawFinder = (fx, fy) => { const s = cs * 3; ctx.fillRect(fx, fy, s, s); ctx.fillStyle = '#fff'; ctx.fillRect(fx + cs, fy + cs, cs, cs); ctx.fillStyle = '#111'; };
            drawFinder(1, 1); drawFinder(w - cs * 3 - 1, 1); drawFinder(1, h - cs * 3 - 1);
        },
        skull_wings: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h * 0.45;
            ctx.fillStyle = '#ccc'; ctx.beginPath(); ctx.ellipse(cx, cy, w * 0.12, h * 0.15, 0, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#1a1a1a';
            ctx.beginPath(); ctx.ellipse(cx - w * 0.05, cy - h * 0.02, w * 0.03, h * 0.04, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(cx + w * 0.05, cy - h * 0.02, w * 0.03, h * 0.04, 0, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = '#888'; ctx.lineWidth = 1.5;
            for (let side = -1; side <= 1; side += 2) {
                ctx.beginPath();
                for (let i = 0; i < 5; i++) {
                    const a = -0.3 + i * 0.35; const r = w * 0.2 + i * w * 0.06;
                    ctx.moveTo(cx + side * w * 0.14, cy);
                    ctx.quadraticCurveTo(cx + side * r * 0.7, cy - h * 0.3 - i * 3, cx + side * r, cy - h * 0.1 + i * 4);
                } ctx.stroke();
            }
        },
        tribal_flame: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#dd6622'; ctx.lineWidth = 2.5;
            for (let i = 0; i < 4; i++) {
                const bx = w * 0.15 + i * w * 0.2, by = h * 0.9;
                ctx.beginPath(); ctx.moveTo(bx, by);
                ctx.quadraticCurveTo(bx - w * 0.08, by - h * 0.3, bx + w * 0.05, by - h * 0.5);
                ctx.quadraticCurveTo(bx + w * 0.12, by - h * 0.7, bx - w * 0.02, by - h * 0.85);
                ctx.stroke();
            }
        },
        pentagram: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a1a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#993355'; ctx.lineWidth = 2;
            const cx = w / 2, cy = h / 2, r = Math.min(w, h) * 0.4;
            ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            const pts = []; for (let i = 0; i < 5; i++) { const a = i * Math.PI * 2 / 5 - Math.PI / 2; pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); }
            ctx.beginPath(); for (let i = 0; i < 5; i++) { const t = pts[(i * 2) % 5]; i === 0 ? ctx.moveTo(t[0], t[1]) : ctx.lineTo(t[0], t[1]); } ctx.closePath(); ctx.stroke();
        },
        iron_cross: (ctx, w, h) => {
            ctx.fillStyle = '#222'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#886644';
            const cx = w / 2, cy = h / 2, arm = Math.min(w, h) * 0.38, tw = arm * 0.35;
            ctx.beginPath();
            ctx.moveTo(cx - tw, cy - arm); ctx.lineTo(cx + tw, cy - arm); ctx.lineTo(cx + tw * 0.6, cy - tw);
            ctx.lineTo(cx + arm, cy - tw); ctx.lineTo(cx + arm, cy + tw); ctx.lineTo(cx + tw * 0.6, cy + tw);
            ctx.lineTo(cx + tw, cy + arm); ctx.lineTo(cx - tw, cy + arm); ctx.lineTo(cx - tw * 0.6, cy + tw);
            ctx.lineTo(cx - arm, cy + tw); ctx.lineTo(cx - arm, cy - tw); ctx.lineTo(cx - tw * 0.6, cy - tw);
            ctx.closePath(); ctx.fill();
            ctx.strokeStyle = '#aa8855'; ctx.lineWidth = 1; ctx.stroke();
        },
        _broken_fleur_de_lis: (ctx, w, h) => {
            ctx.fillStyle = '#2a2218'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ccaa44'; ctx.lineWidth = 1.5; ctx.fillStyle = '#ccaa44';
            const cx = w / 2, cy = h / 2;
            ctx.beginPath(); ctx.moveTo(cx, cy - h * 0.35);
            ctx.quadraticCurveTo(cx + w * 0.15, cy - h * 0.15, cx + w * 0.25, cy - h * 0.25);
            ctx.quadraticCurveTo(cx + w * 0.3, cy, cx + w * 0.15, cy + h * 0.15);
            ctx.lineTo(cx, cy + h * 0.05);
            ctx.lineTo(cx - w * 0.15, cy + h * 0.15);
            ctx.quadraticCurveTo(cx - w * 0.3, cy, cx - w * 0.25, cy - h * 0.25);
            ctx.quadraticCurveTo(cx - w * 0.15, cy - h * 0.15, cx, cy - h * 0.35);
            ctx.fill(); ctx.stroke();
            ctx.fillRect(cx - 1, cy + h * 0.05, 2, h * 0.25);
            ctx.fillRect(cx - w * 0.12, cy + h * 0.25, w * 0.24, 2);
        },
        binary_code: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a0a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1010); ctx.font = '8px monospace';
            for (let col = 0; col < Math.ceil(w / 10); col++) {
                ctx.fillStyle = `rgba(${50 + rng() * 80},${180 + rng() * 75},${50 + rng() * 80},${0.5 + rng() * 0.5})`;
                for (let row = 0; row < Math.ceil(h / 10); row++) { ctx.fillText(rng() > 0.5 ? '1' : '0', col * 10 + 1, row * 10 + 8); }
            }
        },
        optical_illusion: (ctx, w, h) => {
            const cx = w / 2, cy = h / 2; const maxR = Math.max(w, h) * 0.48;
            for (let r = 2; r < maxR; r += 4) {
                const even = Math.floor(r / 4) % 2 === 0;
                ctx.fillStyle = even ? '#000000' : '#ffffff'; ctx.strokeStyle = even ? '#000000' : '#ffffff';
                ctx.lineWidth = 2 + (r / maxR) * 6;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        greek_key: (ctx, w, h) => {
            ctx.fillStyle = '#ddd8c8'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#bbaa77'; ctx.lineWidth = 2;
            const s = 16;
            for (let row = 0; row < Math.ceil(h / s); row++) {
                const y = row * s;
                for (let col = 0; col < Math.ceil(w / (s * 2)); col++) {
                    const x = col * s * 2;
                    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + s * 2, y); ctx.lineTo(x + s * 2, y + s);
                    ctx.lineTo(x + s, y + s); ctx.lineTo(x + s, y + s * 0.4); ctx.lineTo(x + s * 1.6, y + s * 0.4); ctx.stroke();
                }
            }
        },
        trophy_laurel: (ctx, w, h) => {
            ctx.fillStyle = '#1a1808'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ddaa44'; ctx.fillStyle = '#ddaa44'; ctx.lineWidth = 1;
            const cx = w / 2, cy = h / 2;
            for (let side = -1; side <= 1; side += 2) {
                for (let i = 0; i < 7; i++) {
                    const a = -1.2 + i * 0.35; const r = Math.min(w, h) * 0.35;
                    const lx = cx + side * Math.cos(a) * r * 0.4, ly = cy + Math.sin(a) * r;
                    ctx.beginPath(); ctx.ellipse(lx, ly, 6, 3, a * side + Math.PI / 2, 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        victory_confetti: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a2a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7777);
            const colors = ['#ee4444', '#44cc44', '#4488ff', '#ffcc22', '#ff66cc', '#44eeff'];
            for (let i = 0; i < 50; i++) {
                ctx.fillStyle = colors[Math.floor(rng() * colors.length)];
                const x = rng() * w, y = rng() * h;
                ctx.save(); ctx.translate(x, y); ctx.rotate(rng() * Math.PI);
                ctx.fillRect(-5, -1.5, 10, 3); ctx.restore();
            }
        },
        gothic_cross: (ctx, w, h) => {
            ctx.fillStyle = '#1a1510'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#886644'; ctx.lineWidth = 2; ctx.fillStyle = '#886644';
            const cx = w / 2, cy = h / 2;
            ctx.fillRect(cx - 3, cy - h * 0.38, 6, h * 0.76);
            ctx.fillRect(cx - w * 0.28, cy - 3, w * 0.56, 6);
            for (let i = 0; i < 4; i++) {
                const a = i * Math.PI / 2; const r = Math.min(w, h) * 0.22;
                ctx.beginPath(); ctx.arc(cx + Math.cos(a) * r * 0.6, cy + Math.sin(a) * r * 0.6, r * 0.35, a - 0.5, a + 0.5); ctx.stroke();
            }
        },
        _broken_norse_rune: (ctx, w, h) => {
            ctx.fillStyle = '#1a1520'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#8877aa'; ctx.lineWidth = 2;
            const rng = _seededRng(2400);
            for (let col = 0; col < 3; col++) {
                for (let row = 0; row < 3; row++) {
                    const cx = w * 0.2 + col * w * 0.3, cy = h * 0.2 + row * h * 0.3, sz = Math.min(w, h) * 0.12;
                    ctx.beginPath(); ctx.moveTo(cx, cy - sz); ctx.lineTo(cx, cy + sz); ctx.stroke();
                    const branches = 1 + Math.floor(rng() * 2);
                    for (let b = 0; b < branches; b++) {
                        const by = cy - sz + rng() * sz * 2; const dir = rng() > 0.5 ? 1 : -1;
                        ctx.beginPath(); ctx.moveTo(cx, by); ctx.lineTo(cx + dir * sz * 0.7, by - sz * 0.4); ctx.stroke();
                    }
                }
            }
        },
        // --- v6.0 Tier 3b: Racing & Automotive Patterns ---
        bullet_holes: (ctx, w, h) => {
            ctx.fillStyle = '#cccccc'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5600);
            const holes = [[0.25, 0.3], [0.6, 0.55], [0.75, 0.25], [0.35, 0.75]];
            for (let i = 0; i < 4; i++) {
                const bx = holes[i][0] * w, by = holes[i][1] * h, br = 2 + rng() * 1.5;
                ctx.fillStyle = '#888888';
                ctx.beginPath();
                for (let k = 0; k < 8; k++) {
                    const a = (k / 8) * Math.PI * 2 + rng() * 0.5;
                    const r = br + 2 + rng() * 3;
                    (k === 0 ? ctx.moveTo : ctx.lineTo).call(ctx, bx + Math.cos(a) * r, by + Math.sin(a) * r);
                }
                ctx.closePath(); ctx.fill();
                ctx.fillStyle = '#000000'; ctx.beginPath(); ctx.arc(bx, by, br * 0.5, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#ffffff'; ctx.beginPath();
                ctx.ellipse(bx - br * 0.3, by - br * 0.3, br * 0.4, br * 0.25, -0.5, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        retro_arcade: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#0055ff'; ctx.lineWidth = 2.5; ctx.shadowBlur = 4; ctx.shadowColor = '#0055ff';
            const m = 4; const bw = w / (m + 2); const bh = h / (m + 2);
            for (let row = 1; row <= m; row++) {
                for (let col = 1; col <= m; col++) {
                    if ((row + col) % 2 === 0) continue;
                    const x = col * bw, y = row * bh;
                    ctx.strokeRect(x, y, bw * 0.9, bh * 0.9);
                }
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        brake_dust: (ctx, w, h) => {
            const g = ctx.createLinearGradient(w, h, 0, 0);
            g.addColorStop(0, '#000000'); g.addColorStop(0.5, '#1a1a1a'); g.addColorStop(1, '#222222');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(3300);
            for (let i = 0; i < 120; i++) {
                const x = rng() * w, y = rng() * h;
                const sz = 0.8 + rng() * 2;
                ctx.fillStyle = rng() > 0.5 ? '#aa5533' : '#999999';
                ctx.globalAlpha = 0.4 + rng() * 0.5;
                ctx.fillRect(x, y, sz, sz);
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        road_rash: (ctx, w, h) => {
            ctx.fillStyle = '#555555'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4400);
            for (let i = 0; i < 8; i++) {
                const x0 = rng() * w, y0 = rng() * h;
                ctx.fillStyle = '#222222'; ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                for (let s = 0; s < 6; s++) {
                    ctx.lineTo(x0 + (s + 1) * 8 + (rng() - 0.5) * 6, y0 + (s + 1) * 6 + (rng() - 0.5) * 4);
                }
                ctx.lineTo(x0 + 50, y0 + 40); ctx.lineTo(x0 + 45, y0 + 42); ctx.closePath();
                ctx.fill(); ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        skid_marks: (ctx, w, h) => {
            ctx.fillStyle = '#bbbbbb'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#111111'; ctx.lineWidth = 4; ctx.lineCap = 'round';
            for (let lane = 0; lane < 2; lane++) {
                const y0 = h * 0.3 + lane * h * 0.35;
                ctx.beginPath(); ctx.moveTo(0, y0);
                for (let x = 2; x <= w; x += 4) {
                    const y = y0 + Math.sin(x * 0.08) * 6 + (x / w) * h * 0.2;
                    ctx.lineTo(x, y);
                }
                ctx.stroke();
                const grad = ctx.createLinearGradient(0, 0, w * 0.3, 0);
                grad.addColorStop(0, 'rgba(17,17,17,0)'); grad.addColorStop(1, 'rgba(17,17,17,1)');
                ctx.strokeStyle = grad; ctx.lineWidth = 4;
                ctx.beginPath(); ctx.moveTo(0, y0); ctx.lineTo(w * 0.25, y0 + h * 0.05); ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        tire_smoke: (ctx, w, h) => {
            ctx.fillStyle = '#2a2a2a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8800);
            ctx.globalAlpha = 0.4; ctx.shadowBlur = 10; ctx.shadowColor = '#ffffff';
            for (let i = 0; i < 25; i++) {
                const x = rng() * w, y = rng() * h, rad = 10 + rng() * 18;
                ctx.fillStyle = rng() > 0.4 ? '#ffffff' : '#cccccc';
                ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fill();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        rpm_gauge: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.35, cy = h * 0.85, r = Math.min(w, h) * 0.5;
            const startAngle = Math.PI * 0.75, endAngle = -Math.PI * 0.25;
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(cx, cy, r, startAngle, endAngle); ctx.stroke();
            for (let i = 0; i <= 10; i++) {
                const t = i / 10; const a = startAngle + t * (endAngle - startAngle);
                ctx.strokeStyle = t >= 0.8 ? '#ff0000' : '#ffffff';
                ctx.beginPath();
                ctx.moveTo(cx + Math.cos(a) * (r - 3), cy + Math.sin(a) * (r - 3));
                ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                ctx.stroke();
            }
            const needleAngle = startAngle + 0.82 * (endAngle - startAngle);
            ctx.strokeStyle = '#ff0000'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(needleAngle) * (r - 2), cy + Math.sin(needleAngle) * (r - 2)); ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        rev_counter: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const bars = 12, bw = Math.floor(w / bars) - 2;
            for (let i = 0; i < bars; i++) {
                const bh = h * 0.3 + i * h * 0.05; const c = i < 7 ? '#33dd44' : i < 10 ? '#ddcc22' : '#dd3333';
                ctx.fillStyle = i < 10 ? c : '#dd3333';
                ctx.fillRect(i * (bw + 2) + 1, h - bh, bw, bh - 2);
            }
        },
        lap_counter: (ctx, w, h) => {
            ctx.fillStyle = '#111'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#cc2222'; ctx.lineWidth = 2.5;
            for (let row = 0; row < 3; row++) {
                for (let g = 0; g < 3; g++) {
                    const bx = g * w * 0.35 + 5, by = row * h * 0.3 + 5;
                    const tally = Math.min(5, row * 3 + g + 1);
                    for (let t = 0; t < tally; t++) {
                        if (t < 4) { ctx.beginPath(); ctx.moveTo(bx + t * 5, by); ctx.lineTo(bx + t * 5, by + h * 0.2); ctx.stroke(); }
                        else { ctx.beginPath(); ctx.moveTo(bx - 2, by + h * 0.15); ctx.lineTo(bx + 18, by + h * 0.03); ctx.stroke(); }
                    }
                }
            }
        },
        track_map: (ctx, w, h) => {
            ctx.fillStyle = '#333333'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(w * 0.2, h * 0.85);
            ctx.quadraticCurveTo(w * 0.08, h * 0.4, w * 0.25, h * 0.15);
            ctx.quadraticCurveTo(w * 0.55, h * 0.05, w * 0.85, h * 0.2);
            ctx.quadraticCurveTo(w * 0.95, h * 0.5, w * 0.7, h * 0.75);
            ctx.quadraticCurveTo(w * 0.45, h * 0.9, w * 0.2, h * 0.85);
            ctx.stroke();
            for (let k = 0; k < 8; k++) {
                ctx.fillStyle = (k % 2) ? '#ff0000' : '#ffffff';
                ctx.fillRect(w * 0.72 + k * 2, h * 0.72, 2, 4);
            }
            for (let k = 0; k < 6; k++) {
                ctx.fillStyle = (k % 2) ? '#ffffff' : '#ff0000';
                ctx.fillRect(w * 0.22 + k * 2, h * 0.18, 2, 3);
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        drift_marks: (ctx, w, h) => {
            ctx.fillStyle = '#555544'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(30,30,25,0.6)'; ctx.lineWidth = 4;
            ctx.beginPath(); ctx.moveTo(0, h * 0.3); ctx.quadraticCurveTo(w * 0.4, h * 0.2, w * 0.7, h * 0.5); ctx.quadraticCurveTo(w * 0.9, h * 0.7, w, h * 0.6); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, h * 0.35); ctx.quadraticCurveTo(w * 0.4, h * 0.25, w * 0.7, h * 0.55); ctx.quadraticCurveTo(w * 0.9, h * 0.75, w, h * 0.65); ctx.stroke();
        },
        g_force: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a0a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#cc4455'; ctx.lineWidth = 1.5;
            for (let i = 0; i < 8; i++) {
                const x = w * 0.1 + i * w * 0.1;
                ctx.beginPath(); ctx.moveTo(x, 0);
                ctx.quadraticCurveTo(x + w * 0.15, h * 0.5, x, h); ctx.stroke();
            }
        },
        roll_cage: (ctx, w, h) => {
            ctx.fillStyle = '#3a3a44'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#99aabb'; ctx.lineWidth = 3; ctx.lineCap = 'round';
            for (let x = w * 0.15; x < w; x += w * 0.35) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = h * 0.15; y < h; y += h * 0.35) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(w * 0.15, 0); ctx.lineTo(w * 0.5, h * 0.5); ctx.lineTo(w * 0.15, h); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(w * 0.85, 0); ctx.lineTo(w * 0.5, h * 0.5); ctx.lineTo(w * 0.85, h); ctx.stroke();
        },
        spark_scatter: (ctx, w, h) => {
            ctx.fillStyle = '#1a1008'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(6600);
            for (let i = 0; i < 35; i++) {
                const sx = rng() * w, sy = rng() * h, sl = 3 + rng() * 8, sa = rng() * Math.PI * 2;
                ctx.strokeStyle = `rgba(${220 + rng() * 35},${150 + rng() * 70},${20 + rng() * 40},${0.6 + rng() * 0.4})`;
                ctx.lineWidth = 0.8 + rng();
                ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(sx + Math.cos(sa) * sl, sy + Math.sin(sa) * sl); ctx.stroke();
            }
        },
        nitro_burst: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const y = h * 0.5;
            ctx.fillStyle = '#444444'; ctx.beginPath(); ctx.arc(w * 0.12, y, 5, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.arc(w * 0.12, y + 14, 5, 0, Math.PI * 2); ctx.fill();
            ctx.shadowBlur = 8; ctx.shadowColor = '#00ffff';
            const g = ctx.createLinearGradient(0, 0, w, 0);
            g.addColorStop(0, '#00ffff'); g.addColorStop(0.5, '#0088ff'); g.addColorStop(1, '#cc00ff');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.moveTo(w * 0.2, y - 4); ctx.lineTo(w * 0.9, y - 2); ctx.lineTo(w * 0.88, y + 2); ctx.lineTo(w * 0.2, y + 4); ctx.closePath(); ctx.fill();
            ctx.beginPath(); ctx.moveTo(w * 0.2, y + 10); ctx.lineTo(w * 0.9, y + 12); ctx.lineTo(w * 0.88, y + 16); ctx.lineTo(w * 0.2, y + 14); ctx.closePath(); ctx.fill();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        rooster_tail: (ctx, w, h) => {
            ctx.fillStyle = '#443322'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(9900);
            ctx.fillStyle = 'rgba(100,70,40,0.6)';
            for (let i = 0; i < 30; i++) {
                const x = w * 0.3 + rng() * w * 0.5, y = rng() * h;
                const sx = 2 + rng() * 6, sy = 1 + rng() * 3;
                ctx.beginPath(); ctx.ellipse(x, y, sx, sy, rng() * 0.5 - 0.25, 0, Math.PI * 2); ctx.fill();
            }
            ctx.strokeStyle = 'rgba(80,55,30,0.5)'; ctx.lineWidth = 1;
            for (let i = 0; i < 8; i++) {
                const a = -0.8 + rng() * 1.6;
                ctx.beginPath(); ctx.moveTo(w * 0.1, h * 0.8); ctx.quadraticCurveTo(w * 0.3, h * 0.3 + rng() * h * 0.3, w * 0.5 + rng() * w * 0.4, rng() * h * 0.4); ctx.stroke();
            }
        },
        // --- v6.0 Tier 3c: Texture, Material & Organic Patterns ---
        leather_grain: (ctx, w, h) => {
            ctx.fillStyle = '#885533'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(2200);
            for (let i = 0; i < 120; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.fillStyle = `rgba(${100 + rng() * 40},${60 + rng() * 30},${30 + rng() * 20},${0.15 + rng() * 0.2})`;
                ctx.beginPath(); ctx.ellipse(x, y, 1 + rng() * 3, 0.5 + rng() * 1.5, rng() * Math.PI, 0, Math.PI * 2); ctx.fill();
            }
        },
        corrugated: (ctx, w, h) => {
            const sp = 6;
            for (let y = 0; y < h; y++) {
                const phase = Math.sin(y / sp * Math.PI) * 0.5 + 0.5;
                const v = Math.floor(120 + phase * 50);
                ctx.fillStyle = `rgb(${v},${v + 5},${v + 5})`; ctx.fillRect(0, y, w, 1);
            }
        },
        expanded_metal: (ctx, w, h) => {
            ctx.fillStyle = '#333'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#778888'; ctx.lineWidth = 1;
            const dx = 10, dy = 6;
            for (let row = 0; row < Math.ceil(h / dy); row++) {
                const off = row % 2 ? dx / 2 : 0;
                for (let col = -1; col < Math.ceil(w / dx) + 1; col++) {
                    const cx = col * dx + off, cy = row * dy;
                    ctx.beginPath(); ctx.moveTo(cx, cy - dy / 2); ctx.lineTo(cx + dx / 2, cy);
                    ctx.lineTo(cx, cy + dy / 2); ctx.lineTo(cx - dx / 2, cy); ctx.closePath(); ctx.stroke();
                }
            }
        },
        chainlink: (ctx, w, h) => {
            ctx.fillStyle = '#444'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#999'; ctx.lineWidth = 1;
            const s = 10;
            for (let row = 0; row < Math.ceil(h / s) + 1; row++) {
                for (let col = 0; col < Math.ceil(w / s) + 1; col++) {
                    const cx = col * s + (row % 2 ? s / 2 : 0), cy = row * s;
                    ctx.beginPath(); ctx.moveTo(cx - s / 2, cy); ctx.lineTo(cx, cy - s / 2); ctx.lineTo(cx + s / 2, cy); ctx.lineTo(cx, cy + s / 2); ctx.closePath(); ctx.stroke();
                }
            }
        },
        giraffe: (ctx, w, h) => {
            ctx.fillStyle = '#cc9944'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(3500);
            ctx.strokeStyle = '#5a3a15'; ctx.lineWidth = 2.5; ctx.fillStyle = '#8a5a20';
            for (let i = 0; i < 12; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.beginPath();
                const pts = 5 + Math.floor(rng() * 3);
                for (let p = 0; p < pts; p++) {
                    const a = p * Math.PI * 2 / pts, r = 6 + rng() * 8;
                    p === 0 ? ctx.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r) : ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
                } ctx.closePath(); ctx.fill(); ctx.stroke();
            }
        },
        feather: (ctx, w, h) => {
            ctx.fillStyle = '#556677'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#778899'; ctx.lineWidth = 0.8;
            for (let row = 0; row < 5; row++) {
                const cy = row * h * 0.22 + 5, cx = w * 0.5;
                ctx.strokeStyle = '#667788'; ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.moveTo(cx - w * 0.3, cy + 5); ctx.quadraticCurveTo(cx, cy - 3, cx + w * 0.3, cy + 5); ctx.stroke();
                ctx.strokeStyle = 'rgba(120,150,170,0.5)'; ctx.lineWidth = 0.5;
                for (let b = 0; b < 12; b++) {
                    const bx = cx - w * 0.25 + b * w * 0.04;
                    ctx.beginPath(); ctx.moveTo(bx, cy + 2); ctx.lineTo(bx + 3, cy - 4); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(bx, cy + 2); ctx.lineTo(bx + 3, cy + 8); ctx.stroke();
                }
            }
        },
        thorn_vine: (ctx, w, h) => {
            ctx.fillStyle = '#1a2210'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#445533'; ctx.lineWidth = 2.5;
            ctx.beginPath(); ctx.moveTo(0, h * 0.3);
            for (let x = 0; x < w; x += 3) { ctx.lineTo(x, h * 0.3 + Math.sin(x * 0.08) * h * 0.15); } ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, h * 0.7);
            for (let x = 0; x < w; x += 3) { ctx.lineTo(x, h * 0.7 + Math.sin(x * 0.06 + 2) * h * 0.12); } ctx.stroke();
            ctx.strokeStyle = '#556644'; ctx.lineWidth = 1;
            const rng = _seededRng(4100);
            for (let i = 0; i < 20; i++) {
                const x = rng() * w, y = h * 0.3 + Math.sin(x * 0.08) * h * 0.15;
                const a = rng() * Math.PI * 2; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(a) * 4, y + Math.sin(a) * 4); ctx.stroke();
            }
        },
        biomechanical: (ctx, w, h) => {
            ctx.fillStyle = '#2a3328'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(6100);
            ctx.strokeStyle = '#556655'; ctx.lineWidth = 1.5;
            for (let i = 0; i < 6; i++) {
                const x = rng() * w, y = rng() * h, r = 5 + rng() * 10;
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
                ctx.beginPath(); ctx.arc(x, y, r * 0.4, 0, Math.PI * 2); ctx.stroke();
                for (let s = 0; s < 3; s++) {
                    const a = rng() * Math.PI * 2;
                    ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
                    ctx.lineTo(x + Math.cos(a) * (r + 8 + rng() * 12), y + Math.sin(a) * (r + 8 + rng() * 12)); ctx.stroke();
                }
            }
            ctx.strokeStyle = '#445544'; ctx.lineWidth = 0.8;
            for (let i = 0; i < 15; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + rng() * 20 - 10, y + rng() * 20 - 10); ctx.stroke();
            }
        },
        hailstorm: (ctx, w, h) => {
            ctx.fillStyle = '#8899aa'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5500);
            for (let i = 0; i < 40; i++) {
                const x = rng() * w, y = rng() * h, r = 1 + rng() * 3;
                ctx.fillStyle = 'rgba(150,170,190,0.5)'; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = 'rgba(200,220,240,0.3)'; ctx.beginPath(); ctx.arc(x - 0.5, y - 0.5, r * 0.5, 0, Math.PI * 2); ctx.fill();
            }
        },
        sandstorm: (ctx, w, h) => {
            ctx.fillStyle = '#bba066'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7700);
            for (let i = 0; i < 100; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.fillStyle = `rgba(${180 + rng() * 50},${150 + rng() * 40},${80 + rng() * 40},${0.2 + rng() * 0.4})`;
                ctx.fillRect(x, y, 1 + rng() * 4, 0.5 + rng());
            }
        },
        peeling_paint: (ctx, w, h) => {
            ctx.fillStyle = '#998866'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(3300);
            for (let i = 0; i < 8; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.fillStyle = `rgba(${140 + rng() * 40},${120 + rng() * 40},${90 + rng() * 30},0.7)`;
                ctx.beginPath();
                const pts = 5 + Math.floor(rng() * 4);
                for (let p = 0; p < pts; p++) {
                    const a = p * Math.PI * 2 / pts, r = 4 + rng() * 8;
                    p === 0 ? ctx.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r) : ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
                } ctx.closePath(); ctx.fill();
                ctx.strokeStyle = 'rgba(80,70,50,0.5)'; ctx.lineWidth = 0.8; ctx.stroke();
            }
        },
        rust_bloom: (ctx, w, h) => {
            ctx.fillStyle = '#665533'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4400);
            for (let i = 0; i < 10; i++) {
                const x = rng() * w, y = rng() * h, r = 4 + rng() * 10;
                const g = ctx.createRadialGradient(x, y, 0, x, y, r);
                g.addColorStop(0, `rgba(${180 + rng() * 40},${80 + rng() * 30},${20 + rng() * 20},0.8)`);
                g.addColorStop(1, 'rgba(100,60,30,0)');
                ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
            }
        },
        shrapnel: (ctx, w, h) => {
            ctx.fillStyle = '#556666'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8800);
            for (let i = 0; i < 15; i++) {
                ctx.fillStyle = `rgba(${60 + rng() * 40},${60 + rng() * 40},${70 + rng() * 40},0.7)`;
                const x = rng() * w, y = rng() * h;
                ctx.beginPath(); const pts = 3 + Math.floor(rng() * 3);
                for (let p = 0; p < pts; p++) {
                    const a = p * Math.PI * 2 / pts, r = 2 + rng() * 5;
                    p === 0 ? ctx.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r) : ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
                } ctx.closePath(); ctx.fill();
            }
        },
        knurled: (ctx, w, h) => {
            ctx.fillStyle = '#778877'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(100,110,100,0.6)'; ctx.lineWidth = 0.8;
            const sp = 5;
            for (let x = -h; x < w + h; x += sp) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + h, h); ctx.stroke(); }
            for (let x = -h; x < w + h; x += sp) { ctx.beginPath(); ctx.moveTo(x + h, 0); ctx.lineTo(x, h); ctx.stroke(); }
        },
        asphalt_texture: (ctx, w, h) => {
            ctx.fillStyle = '#444'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(1100);
            for (let i = 0; i < 200; i++) {
                const v = 40 + Math.floor(rng() * 30);
                ctx.fillStyle = `rgb(${v},${v},${v})`;
                ctx.fillRect(rng() * w, rng() * h, 1 + rng() * 2, 1 + rng() * 2);
            }
        },
        exhaust_wrap: (ctx, w, h) => {
            ctx.fillStyle = '#776655'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(100,85,70,0.5)'; ctx.lineWidth = 1;
            const sp = 6;
            for (let y = 0; y < h; y += sp) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
                ctx.strokeStyle = 'rgba(120,100,80,0.3)';
                for (let x = 0; x < w; x += sp * 2) {
                    const off = Math.floor(y / sp) % 2 ? sp : 0;
                    ctx.beginPath(); ctx.moveTo(x + off, y); ctx.lineTo(x + off, y + sp); ctx.stroke();
                }
                ctx.strokeStyle = 'rgba(100,85,70,0.5)';
            }
        },
        // --- v6.0 Tier 3d: Geometric, Tech & Misc Patterns ---
        molecular: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a1a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(3600);
            const nodes = [];
            for (let i = 0; i < 12; i++) { nodes.push([rng() * w, rng() * h]); }
            ctx.strokeStyle = '#55aa99'; ctx.lineWidth = 1;
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[j][0] - nodes[i][0], dy = nodes[j][1] - nodes[i][1];
                    if (Math.sqrt(dx * dx + dy * dy) < w * 0.45) { ctx.beginPath(); ctx.moveTo(nodes[i][0], nodes[i][1]); ctx.lineTo(nodes[j][0], nodes[j][1]); ctx.stroke(); }
                }
            }
            ctx.fillStyle = '#66ccbb';
            for (const n of nodes) { ctx.beginPath(); ctx.arc(n[0], n[1], 3, 0, Math.PI * 2); ctx.fill(); }
        },
        neuron_network: (ctx, w, h) => {
            ctx.fillStyle = '#111822'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4800);
            const pts = []; for (let i = 0; i < 15; i++) { pts.push([rng() * w, rng() * h]); }
            ctx.strokeStyle = 'rgba(100,140,170,0.4)'; ctx.lineWidth = 0.8;
            for (let i = 0; i < pts.length; i++) {
                const nearest = pts.slice().sort((a, b) => {
                    const da = Math.hypot(a[0] - pts[i][0], a[1] - pts[i][1]);
                    const db = Math.hypot(b[0] - pts[i][0], b[1] - pts[i][1]); return da - db;
                });
                for (let j = 1; j < Math.min(4, nearest.length); j++) {
                    ctx.beginPath(); ctx.moveTo(pts[i][0], pts[i][1]); ctx.lineTo(nearest[j][0], nearest[j][1]); ctx.stroke();
                }
            }
            ctx.fillStyle = '#99bbdd'; for (const p of pts) { ctx.beginPath(); ctx.arc(p[0], p[1], 2, 0, Math.PI * 2); ctx.fill(); }
        },
        data_stream: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5100);
            for (let row = 0; row < Math.ceil(h / 6); row++) {
                const y = row * 6; const speed = rng();
                ctx.fillStyle = `rgba(${200 + rng() * 55},${40 + rng() * 60},${80 + rng() * 80},${0.3 + speed * 0.5})`;
                const startX = rng() * w * 0.5; const len = w * 0.2 + rng() * w * 0.6;
                ctx.fillRect(startX, y, len, 2);
                if (rng() > 0.6) { ctx.fillStyle = 'rgba(255,100,150,0.8)'; ctx.fillRect(startX + len - 3, y, 3, 2); }
            }
        },
        tessellation: (ctx, w, h) => {
            const s = Math.min(w, h) / 5; const r = s * 0.5; const h2 = r * Math.sqrt(3);
            for (let row = -1; row <= Math.ceil(h / h2) + 1; row++) {
                for (let col = -1; col <= Math.ceil(w / (s * 1.5)) + 1; col++) {
                    const cx = col * s * 1.5 + (row % 2 ? s * 0.75 : 0), cy = row * h2;
                    ctx.beginPath();
                    for (let i = 0; i < 6; i++) {
                        const a = (i * Math.PI / 3) - Math.PI / 6;
                        const px = cx + Math.cos(a) * r, py = cy + Math.sin(a) * r;
                        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                    }
                    ctx.closePath();
                    ctx.fillStyle = ((row + col) % 2) ? '#ff6600' : '#333333'; ctx.fill();
                    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1; ctx.stroke();
                }
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        gothic_scroll: (ctx, w, h) => {
            ctx.fillStyle = '#1a1510'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#554433'; ctx.lineWidth = 1.5;
            const rng = _seededRng(2800);
            for (let i = 0; i < 8; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.beginPath();
                ctx.moveTo(x, y); ctx.quadraticCurveTo(x + 15, y - 10, x + 5, y - 20);
                ctx.quadraticCurveTo(x - 10, y - 15, x - 5, y); ctx.stroke();
                ctx.beginPath(); ctx.arc(x + 5, y - 20, 3, 0, Math.PI * 2); ctx.stroke();
            }
        },
        fractal: (ctx, w, h) => {
            ctx.fillStyle = '#220044'; ctx.fillRect(0, 0, w, h);
            const drawBranch = (x, y, len, angle, depth, lw) => {
                if (depth <= 0 || len < 3) return;
                const ex = x + Math.cos(angle) * len, ey = y + Math.sin(angle) * len;
                ctx.strokeStyle = depth % 2 ? '#00ffff' : '#ff00ff'; ctx.lineWidth = lw;
                ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(ex, ey); ctx.stroke();
                drawBranch(ex, ey, len * 0.65, angle - Math.PI / 4, depth - 1, lw * 0.7);
                drawBranch(ex, ey, len * 0.65, angle + Math.PI / 4, depth - 1, lw * 0.7);
            };
            drawBranch(w * 0.5, h * 0.95, h * 0.35, -Math.PI / 2, 4, 3);
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        paisley: (ctx, w, h) => {
            ctx.fillStyle = '#2a1520'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#aa6677'; ctx.lineWidth = 1.5;
            const rng = _seededRng(3900);
            for (let i = 0; i < 6; i++) {
                const cx = rng() * w, cy = rng() * h, sz = 6 + rng() * 8;
                ctx.beginPath(); ctx.moveTo(cx, cy - sz);
                ctx.quadraticCurveTo(cx + sz, cy - sz * 0.3, cx + sz * 0.3, cy + sz * 0.5);
                ctx.quadraticCurveTo(cx - sz * 0.2, cy + sz, cx - sz * 0.5, cy);
                ctx.quadraticCurveTo(cx - sz * 0.6, cy - sz * 0.8, cx, cy - sz); ctx.stroke();
            }
        },
        aero_flow: (ctx, w, h) => {
            ctx.fillStyle = '#1a2233'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(80,150,200,0.5)'; ctx.lineWidth = 1;
            for (let i = 0; i < 10; i++) {
                const y = h * 0.1 + i * h * 0.08;
                ctx.beginPath(); ctx.moveTo(0, y);
                for (let x = 0; x < w; x += 2) { ctx.lineTo(x, y + Math.sin(x * 0.05 + i * 0.8) * 3); } ctx.stroke();
            }
        },
        wind_tunnel: (ctx, w, h) => {
            ctx.fillStyle = '#2a3344'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(6200);
            ctx.strokeStyle = 'rgba(150,170,190,0.3)'; ctx.lineWidth = 0.8;
            for (let i = 0; i < 20; i++) {
                const y = rng() * h, len = w * 0.3 + rng() * w * 0.5, sx = rng() * w * 0.3;
                ctx.beginPath(); ctx.moveTo(sx, y);
                for (let x = sx; x < sx + len; x += 3) { ctx.lineTo(x, y + Math.sin(x * 0.03) * 2); } ctx.stroke();
            }
        },
        sponsor_fade: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, 0);
            g.addColorStop(0, '#667799'); g.addColorStop(0.4, '#8899bb');
            g.addColorStop(0.6, '#8899bb'); g.addColorStop(1, '#556688');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(w * 0.35, 0); ctx.lineTo(w * 0.35, h); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(w * 0.65, 0); ctx.lineTo(w * 0.65, h); ctx.stroke();
        },
        solar_flare: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a00'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.3, cy = h * 0.5;
            const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, w * 0.6);
            g.addColorStop(0, 'rgba(255,200,50,0.9)'); g.addColorStop(0.2, 'rgba(240,130,30,0.6)'); g.addColorStop(0.5, 'rgba(200,60,10,0.3)'); g.addColorStop(1, 'rgba(30,10,0,0)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(255,180,60,0.5)'; ctx.lineWidth = 1.5;
            const rng = _seededRng(7300);
            for (let i = 0; i < 6; i++) {
                const a = rng() * Math.PI * 2, r = w * 0.15 + rng() * w * 0.35;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.quadraticCurveTo(cx + Math.cos(a + 0.3) * r * 0.5, cy + Math.sin(a + 0.3) * r * 0.5, cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.stroke();
            }
        },
        pulse_monitor: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a0a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(0,100,40,0.2)'; ctx.lineWidth = 0.5;
            for (let x = 0; x < w; x += 8) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
            for (let y = 0; y < h; y += 8) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
            const colors = ['rgba(0,220,80,0.9)', 'rgba(220,200,40,0.8)', 'rgba(80,180,220,0.7)'];
            for (let line = 0; line < 3; line++) {
                ctx.strokeStyle = colors[line]; ctx.lineWidth = 1.2;
                const cy = h * 0.2 + line * h * 0.28;
                ctx.beginPath();
                for (let px = 0; px < w; px++) {
                    const phase = px % Math.floor(w * 0.4); const norm = phase / Math.floor(w * 0.4);
                    let y = cy;
                    if (line === 0) { if (norm > 0.4 && norm < 0.5) y = cy - h * 0.12; else if (norm > 0.5 && norm < 0.55) y = cy + h * 0.08; }
                    else { y = cy + Math.sin(px * 0.1 + line * 2) * h * 0.06; }
                    px === 0 ? ctx.moveTo(px, y) : ctx.lineTo(px, y);
                } ctx.stroke();
            }
        },
        rivet_grid: (ctx, w, h) => {
            ctx.fillStyle = '#667777'; ctx.fillRect(0, 0, w, h);
            const sp = 10;
            for (let y = sp / 2; y < h; y += sp) {
                for (let x = sp / 2; x < w; x += sp) {
                    ctx.fillStyle = '#889999'; ctx.beginPath(); ctx.arc(x, y, 2.5, 0, Math.PI * 2); ctx.fill();
                    ctx.fillStyle = 'rgba(255,255,255,0.3)'; ctx.beginPath(); ctx.arc(x - 0.5, y - 0.5, 1, 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        // --- v6.0 Tier 3e: PARADIGM Pattern Renderers ---
        fresnel_ghost: (ctx, w, h) => {
            ctx.fillStyle = '#667777'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(150,170,170,0.25)'; ctx.lineWidth = 1;
            const s = 8; const h2 = s * Math.sin(Math.PI / 3);
            for (let row = 0; row < Math.ceil(h / h2) + 1; row++) {
                for (let col = 0; col < Math.ceil(w / s) + 1; col++) {
                    const cx = col * s + (row % 2 ? s / 2 : 0), cy = row * h2;
                    ctx.beginPath(); for (let i = 0; i < 6; i++) {
                        const a = i * Math.PI / 3;
                        const px = cx + Math.cos(a) * s * 0.5, py = cy + Math.sin(a) * s * 0.5;
                        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                    } ctx.closePath(); ctx.stroke();
                }
            }
        },
        caustic: (ctx, w, h) => {
            ctx.fillStyle = '#1a3344'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5500);
            for (let y = 0; y < h; y += 2) {
                for (let x = 0; x < w; x += 2) {
                    const v = Math.sin(x * 0.15 + rng() * 0.5) * Math.cos(y * 0.12 + rng() * 0.5);
                    const bright = Math.max(0, v) * 180;
                    ctx.fillStyle = `rgba(${100 + bright * 0.5},${180 + bright * 0.4},${200 + bright * 0.3},${0.1 + Math.max(0, v) * 0.4})`;
                    ctx.fillRect(x, y, 2, 2);
                }
            }
        },
        dimensional: (ctx, w, h) => {
            ctx.fillStyle = '#001133'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2, s = Math.min(w, h) * 0.25;
            ctx.strokeStyle = '#00ff00'; ctx.lineWidth = 1.5; ctx.shadowBlur = 5; ctx.shadowColor = '#00ff00';
            const front = [[cx - s, cy + s], [cx + s, cy + s], [cx + s, cy - s], [cx - s, cy - s]];
            const back = [[cx - s * 0.6, cy + s * 0.6], [cx + s * 0.6, cy + s * 0.6], [cx + s * 0.6, cy - s * 0.6], [cx - s * 0.6, cy - s * 0.6]];
            ctx.beginPath(); for (let i = 0; i < 4; i++) ctx.lineTo(front[i][0], front[i][1]); ctx.closePath(); ctx.stroke();
            ctx.beginPath(); for (let i = 0; i < 4; i++) ctx.lineTo(back[i][0], back[i][1]); ctx.closePath(); ctx.stroke();
            for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.moveTo(front[i][0], front[i][1]); ctx.lineTo(back[i][0], back[i][1]); ctx.stroke(); }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        neural: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(6600);
            const pts = []; for (let i = 0; i < 10; i++) pts.push([rng() * w, rng() * h, 2 + rng() * 3]);
            ctx.fillStyle = '#ffffff'; ctx.shadowBlur = 8; ctx.shadowColor = '#ffffff';
            pts.forEach(([x, y, r]) => { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); });
            ctx.shadowBlur = 0; ctx.strokeStyle = '#4488ff'; ctx.lineWidth = 1;
            pts.forEach((p, i) => {
                const dists = pts.map((q, j) => j === i ? Infinity : Math.hypot(p[0] - q[0], p[1] - q[1]));
                const sorted = dists.map((d, j) => [d, j]).sort((a, b) => a[0] - b[0]);
                for (let k = 0; k < 3 && k < sorted.length; k++) {
                    const j = sorted[k][1]; if (j <= i) continue;
                    const q = pts[j]; ctx.beginPath(); ctx.moveTo(p[0], p[1]);
                    const mx = (p[0] + q[0]) / 2 + (rng() - 0.5) * 15, my = (p[1] + q[1]) / 2 + (rng() - 0.5) * 15;
                    ctx.quadraticCurveTo(mx, my, q[0], q[1]); ctx.stroke();
                }
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        p_plasma: (ctx, w, h) => {
            ctx.fillStyle = '#0a0020'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = 'rgba(150,60,220,0.6)'; ctx.lineWidth = 1.5;
            const rng = _seededRng(7700);
            for (let i = 0; i < 8; i++) {
                const a = rng() * Math.PI * 2, r = Math.min(w, h) * 0.4;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                const mx = cx + Math.cos(a + 0.5) * r * 0.4, my = cy + Math.sin(a + 0.5) * r * 0.4;
                ctx.quadraticCurveTo(mx, my, cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.stroke();
            }
            ctx.fillStyle = 'rgba(180,80,255,0.3)'; ctx.beginPath(); ctx.arc(cx, cy, 8, 0, Math.PI * 2); ctx.fill();
        },
        holographic: (ctx, w, h) => {
            for (let y = 0; y < h; y++) {
                const hue = (y * 6) % 360;
                ctx.fillStyle = `hsla(${hue},70%,65%,0.7)`; ctx.fillRect(0, y, w, 1);
            }
            ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 0.5;
            for (let y = 0; y < h; y += 3) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        circuitboard: (ctx, w, h) => {
            ctx.fillStyle = '#0a2a15'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#22aa44'; ctx.lineWidth = 1.5;
            const rng = _seededRng(8800);
            for (let i = 0; i < 10; i++) {
                const sx = rng() * w, sy = rng() * h; let cx = sx, cy = sy;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                for (let s = 0; s < 4; s++) {
                    if (rng() > 0.5) { cx += 10 + rng() * 15; } else { cy += 10 + rng() * 15; }
                    ctx.lineTo(cx, cy);
                } ctx.stroke();
                ctx.fillStyle = '#44cc66'; ctx.beginPath(); ctx.arc(cx, cy, 2, 0, Math.PI * 2); ctx.fill();
                ctx.beginPath(); ctx.arc(sx, sy, 2, 0, Math.PI * 2); ctx.fill();
            }
        },
        p_topographic: (ctx, w, h) => {
            ctx.fillStyle = '#2a3a20'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#88aa66'; ctx.lineWidth = 0.8;
            const cx = w * 0.4, cy = h * 0.45;
            for (let r = 5; r < Math.max(w, h) * 0.7; r += 5) {
                ctx.beginPath();
                for (let a = 0; a < Math.PI * 2; a += 0.1) {
                    const wobble = Math.sin(a * 3 + r * 0.2) * r * 0.08 + Math.cos(a * 5 + r * 0.1) * r * 0.05;
                    const px = cx + Math.cos(a) * (r + wobble), py = cy + Math.sin(a) * (r * 0.7 + wobble);
                    a === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                } ctx.closePath(); ctx.stroke();
            }
        },
        p_tessellation: (ctx, w, h) => {
            ctx.fillStyle = '#2a3044'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#7788cc'; ctx.lineWidth = 1;
            const s = 12;
            for (let row = 0; row < Math.ceil(h / s) + 1; row++) {
                for (let col = 0; col < Math.ceil(w / s) + 1; col++) {
                    const cx = col * s, cy = row * s;
                    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + s, cy); ctx.lineTo(cx + s * 0.5, cy + s); ctx.closePath(); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(cx + s, cy); ctx.lineTo(cx + s * 1.5, cy + s); ctx.lineTo(cx + s * 0.5, cy + s); ctx.closePath(); ctx.stroke();
                }
            }
        },
    };

    // --- MONOLITHIC SPECIALS ---
    const monoFns = {
        phantom: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#2a2a3a'); g.addColorStop(0.3, '#888');
            g.addColorStop(0.5, '#aaa'); g.addColorStop(0.7, '#555');
            g.addColorStop(1, '#333');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const hl = ctx.createLinearGradient(0, h * 0.15, w, h * 0.55);
            hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.35, 'rgba(255,255,255,0.1)');
            hl.addColorStop(0.55, 'rgba(255,255,255,0.1)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        },
        ember_glow: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const glow = Math.max(0, Math.min(1, (noise[i] + 1) * 0.5));
                const r = Math.floor(80 + glow * 175);
                const g = Math.floor(20 + glow * 80);
                const b = Math.floor(5 + glow * 20);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        liquid_metal: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], rng);
            for (let i = 0; i < w * h; i++) {
                const pool = Math.max(0, Math.min(1, (noise[i] + 1) * 0.5));
                const v = Math.floor(140 + pool * 115);
                id.data[i * 4] = v - 5; id.data[i * 4 + 1] = v - 3; id.data[i * 4 + 2] = v + 5; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        frost_bite: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const frost = Math.max(0, Math.min(1, (noise[i] + 1) * 0.5));
                const r = Math.floor(100 + frost * 60);
                const g = Math.floor(140 + frost * 60);
                const b = Math.floor(170 + frost * 70);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        worn_chrome: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [2, 4, 8], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const n = (noise[i] + 1) * 0.5;
                const chrome = n > 0.5;
                const r = chrome ? Math.floor(180 + n * 70) : Math.floor(80 + n * 60);
                const g = chrome ? Math.floor(185 + n * 65) : Math.floor(100 + n * 40);
                const b = chrome ? Math.floor(175 + n * 75) : Math.floor(85 + n * 30);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Expansion Pack Specials ---
        oil_slick: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const n1 = _simpleNoise2D(w, h, [8, 16, 32], [0.3, 0.4, 0.3], rng);
            const n2 = _simpleNoise2D(w, h, [4, 12, 24], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const hue = ((n1[i] + n2[i]) * 0.5 + 1) * 180;
                const [r, g, b] = _hslToRgb(hue, 60, 40);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        galaxy: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [16, 32], [0.5, 0.5], rng);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < w * h; i++) {
                const neb = Math.max(0, (noise[i] + 0.5) * 1.2);
                id.data[i * 4] += Math.floor(neb * 60); id.data[i * 4 + 1] += Math.floor(neb * 20);
                id.data[i * 4 + 2] += Math.floor(neb * 80);
            }
            ctx.putImageData(id, 0, 0);
            // Stars
            for (let i = 0; i < w * h * 0.03; i++) {
                const sx = rng() * w, sy = rng() * h;
                const b = 180 + rng() * 75;
                ctx.fillStyle = `rgba(${b},${b},${b + 20},${0.6 + rng() * 0.4})`;
                ctx.fillRect(Math.floor(sx), Math.floor(sy), 1, 1);
            }
        },
        rust: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], rng);
            for (let i = 0; i < w * h; i++) {
                const r2 = Math.max(0, Math.min(1, (noise[i] + 0.2) * 2));
                const r = Math.floor(80 + r2 * 140); const g = Math.floor(40 + r2 * 50); const b = Math.floor(20 + r2 * 10);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        neon_glow: (ctx, w, h) => {
            // Mask-edge bright green/cyan glow with noise blobs
            ctx.fillStyle = '#1a1a2a'; ctx.fillRect(0, 0, w, h);
            // Edge contour glow
            ctx.strokeStyle = 'rgba(40,255,120,0.5)'; ctx.lineWidth = 3;
            ctx.strokeRect(4, 4, w - 8, h - 8);
            ctx.strokeStyle = 'rgba(40,220,100,0.15)'; ctx.lineWidth = 8;
            ctx.strokeRect(2, 2, w - 4, h - 4);
            // Interior noise glow blobs
            const rng = _seededRng(42);
            for (let i = 0; i < 8; i++) {
                const x = rng() * w, y = rng() * h, r = 5 + rng() * 10;
                const g2 = ctx.createRadialGradient(x, y, 0, x, y, r);
                g2.addColorStop(0, 'rgba(40,255,120,0.25)'); g2.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h);
            }
        },
        weathered_paint: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const rng = _seededRng(42);
            const noise = _simpleNoise2D(w, h, [8, 16, 32], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const peel = Math.max(0, Math.min(1, (noise[i] + 0.1) * 1.5));
                // Intact=paint color, peeled=gray primer
                const r = Math.floor(120 * (1 - peel) + 120 * peel);
                const g = Math.floor(90 * (1 - peel) + 115 * peel);
                const b = Math.floor(70 * (1 - peel) + 110 * peel);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- Chameleon Color-Shift Monolithics ---
        chameleon_midnight: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.06 + px * 0.04) * 0.3 + Math.sin(py * 0.03 - px * 0.05) * 0.2 + 0.5;
                    // Purple → Teal → Gold
                    let r, g, b;
                    if (t < 0.33) { const s = t / 0.33; r = Math.floor(100 - s * 60); g = Math.floor(30 + s * 140); b = Math.floor(170 - s * 80); }
                    else if (t < 0.66) { const s = (t - 0.33) / 0.33; r = Math.floor(40 + s * 180); g = Math.floor(170 - s * 30); b = Math.floor(90 - s * 50); }
                    else { const s = (t - 0.66) / 0.34; r = Math.floor(220 - s * 20); g = Math.floor(140 + s * 60); b = Math.floor(40 + s * 20); }
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        chameleon_phoenix: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.07 + px * 0.03) * 0.3 + Math.sin(py * 0.02 - px * 0.06) * 0.2 + 0.5;
                    // Red → Orange → Gold
                    const r = Math.floor(200 + t * 40); const g = Math.floor(30 + t * 170); const b = Math.floor(10 + t * 30);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        chameleon_ocean: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.05 + px * 0.05) * 0.3 + Math.sin(py * 0.04 - px * 0.03) * 0.2 + 0.5;
                    // Blue → Teal → Emerald
                    const r = Math.floor(20 + t * 40); const g = Math.floor(80 + t * 130); const b = Math.floor(180 - t * 80);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        chameleon_venom: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.06 + px * 0.04) * 0.3 + Math.sin(py * 0.03 - px * 0.05) * 0.2 + 0.5;
                    // Green → Teal → Purple
                    let r, g, b;
                    if (t < 0.5) { const s = t / 0.5; r = Math.floor(20 + s * 30); g = Math.floor(170 - s * 60); b = Math.floor(40 + s * 80); }
                    else { const s = (t - 0.5) / 0.5; r = Math.floor(50 + s * 100); g = Math.floor(110 - s * 60); b = Math.floor(120 + s * 60); }
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        chameleon_copper: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.05 + px * 0.06) * 0.3 + Math.sin(py * 0.04 - px * 0.03) * 0.2 + 0.5;
                    // Copper → Magenta → Violet
                    const r = Math.floor(200 - t * 60); const g = Math.floor(100 - t * 50); const b = Math.floor(50 + t * 150);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        chameleon_arctic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.06 + px * 0.04) * 0.3 + Math.sin(py * 0.03 - px * 0.06) * 0.2 + 0.5;
                    // Teal → Blue → Purple
                    let r, g, b;
                    if (t < 0.5) { const s = t / 0.5; r = Math.floor(30 + s * 30); g = Math.floor(170 - s * 80); b = Math.floor(200 - s * 10); }
                    else { const s = (t - 0.5) / 0.5; r = Math.floor(60 + s * 80); g = Math.floor(90 - s * 40); b = Math.floor(190 + s * 30); }
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        mystichrome: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = Math.sin(py * 0.05 + px * 0.05) * 0.3 + Math.sin(py * 0.04 - px * 0.04) * 0.2 + 0.5;
                    // Green → Blue → Purple (Ford SVT Cobra tribute)
                    let r, g, b;
                    if (t < 0.33) { const s = t / 0.33; r = Math.floor(20 + s * 20); g = Math.floor(140 - s * 60); b = Math.floor(60 + s * 120); }
                    else if (t < 0.66) { const s = (t - 0.33) / 0.33; r = Math.floor(40 + s * 90); g = Math.floor(80 - s * 40); b = Math.floor(180 + s * 30); }
                    else { const s = (t - 0.66) / 0.34; r = Math.floor(130 - s * 20); g = Math.floor(40 + s * 20); b = Math.floor(210 - s * 30); }
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- v4.0 New Monolithics ---
        glitch: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(4100);
            for (let py = 0; py < h; py++) {
                const tearBand = rng() < 0.1;
                const offset = tearBand ? Math.floor(rng() * 10 - 5) : 0;
                for (let px = 0; px < w; px++) {
                    const sx = Math.max(0, Math.min(w - 1, px + offset));
                    const scanline = (py % 4) < 1 ? 0.6 : 1;
                    const noise = rng() * 40;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.floor((150 + noise) * scanline); // R shifted
                    id.data[idx + 1] = Math.floor((50 + noise * 0.5) * scanline); // G
                    id.data[idx + 2] = Math.floor((100 + noise) * scanline); // B shifted
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        cel_shade: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(4200);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const n = (noise[i] + 1) * 0.5;
                // Posterize to 4 levels
                const level = Math.floor(n * 4) / 4;
                const r = Math.floor(200 + level * 40); const g = Math.floor(120 + level * 60); const b = Math.floor(50 + level * 30);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Edge outlines
            ctx.strokeStyle = 'rgba(30,20,10,0.8)'; ctx.lineWidth = 1;
            const rng2 = _seededRng(4201);
            for (let i = 0; i < 15; i++) {
                ctx.beginPath();
                let px = rng2() * w, py = rng2() * h;
                ctx.moveTo(px, py);
                for (let s = 0; s < 6; s++) { px += (rng2() - 0.5) * 15; py += (rng2() - 0.5) * 15; ctx.lineTo(px, py); }
                ctx.stroke();
            }
        },
        thermochromic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(4300);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const heat = (noise[i] + 1) * 0.5;
                // Blue(cold) → Green → Yellow → Red(hot)
                let r, g, b;
                if (heat < 0.25) { const s = heat / 0.25; r = Math.floor(30); g = Math.floor(60 + s * 140); b = Math.floor(200 - s * 80); }
                else if (heat < 0.5) { const s = (heat - 0.25) / 0.25; r = Math.floor(30 + s * 190); g = Math.floor(200 + s * 40); b = Math.floor(120 - s * 100); }
                else if (heat < 0.75) { const s = (heat - 0.5) / 0.25; r = Math.floor(220 + s * 20); g = Math.floor(240 - s * 80); b = Math.floor(20); }
                else { const s = (heat - 0.75) / 0.25; r = Math.floor(240); g = Math.floor(160 - s * 120); b = Math.floor(20); }
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        aurora: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(4400);
            const n1 = _simpleNoise2D(w, h, [8, 16, 32], [0.3, 0.4, 0.3], rng);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const i = py * w + px;
                    const band = Math.sin(py * 0.08 + n1[i] * 3) * 0.5 + 0.5;
                    const curtain = Math.max(0, Math.sin(px * 0.1 + py * 0.02) * 0.5 + 0.3);
                    const glow = band * curtain;
                    // Green/cyan/pink borealis
                    const hue = 120 + glow * 200;
                    const [r, g, b] = _hslToRgb(hue % 360, 70, 15 + glow * 50);
                    id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- v5.0 New Monolithics ---
        static: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(4500);
            for (let i = 0; i < w * h; i++) {
                const v = Math.floor(rng() * 200);
                id.data[i * 4] = v; id.data[i * 4 + 1] = v; id.data[i * 4 + 2] = v; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        scorched: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(4600);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const burn = (noise[i] + 1) * 0.5;
                const r = Math.floor(60 + burn * 80); const g = Math.floor(30 + burn * 40); const b = Math.floor(20 + burn * 20);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        radioactive: (ctx, w, h) => {
            // Toxic green + concentric radiation rings
            ctx.fillStyle = '#001a00'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            // Radiation concentric rings
            for (let r = 3; r < w * 0.6; r += 4) {
                const alpha = 0.7 - r / (w * 0.6) * 0.5;
                ctx.strokeStyle = `rgba(40,220,20,${Math.max(0, alpha)})`;
                ctx.lineWidth = 2;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
            // Green noise overlay
            const rng = _seededRng(4700);
            for (let i = 0; i < 20; i++) {
                const x = rng() * w, y = rng() * h;
                ctx.fillStyle = `rgba(80,255,40,${0.05 + rng() * 0.1})`;
                ctx.fillRect(x - 2, y - 2, 4, 4);
            }
        },
        holographic_wrap: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const angle = Math.sin(py * 0.06 + px * 0.04) * 0.4 + Math.sin(py * 0.03 - px * 0.06) * 0.3 + Math.sin((py + px) * 0.04) * 0.3;
                    const hue = ((angle + 1) * 0.5) * 360;
                    const bright = 70 + Math.sin(px * 0.1) * 15;
                    const [r, g, b] = _hslToRgb(hue % 360, 80, bright);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- PRIZM v4 Swatches (panel-aware color shift previews) ---
        prizm_holographic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const stops = [[0, 350, 75, 82], [0.18, 35, 80, 85], [0.36, 120, 78, 80], [0.54, 190, 82, 78], [0.72, 250, 78, 76], [1, 310, 72, 80]];
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const yn = py / h, xn = px / w;
                    let t = Math.cos(0.8) * yn + Math.sin(0.8) * xn;
                    t = t * 0.6 + Math.sin((yn * 1.2 + xn * 0.7) * Math.PI) * 0.15 + 0.5;
                    t = Math.max(0, Math.min(1, t));
                    let si = 0; for (let i = 0; i < stops.length - 1; i++) { if (t >= stops[i][0] && t <= stops[i + 1][0]) si = i; }
                    const s0 = stops[si], s1 = stops[si + 1]; const lt = (t - s0[0]) / (s1[0] - s0[0] + 1e-6);
                    const hue = s0[1] + (s1[1] - s0[1]) * lt; const sat = s0[2] + (s1[2] - s0[2]) * lt; const bri = s0[3] + (s1[3] - s0[3]) * lt;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, sat, bri / 2 + 25);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_midnight: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(1.2) * py / h + Math.sin(1.2) * px / w) * 0.7 + 0.3; t = Math.max(0, Math.min(1, t));
                    const hue = 275 + (48 - 275) * t; const sat = 82 + (78 - 82) * t; const bri = 34 + t * 10;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, sat, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_phoenix: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (py / h * 0.5 + px / w * 0.5); t = Math.max(0, Math.min(1, t));
                    const hue = 5 + (140 - 5) * t; const sat = 88 - (88 - 75) * t; const bri = 40 + t * 6;
                    const [r, g, b] = _hslToRgb(hue % 360, sat, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_oceanic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.5) * py / h + Math.sin(0.5) * px / w) * 0.8 + 0.2; t = Math.max(0, Math.min(1, t));
                    const hue = 175 + (320 - 175) * t; const sat = 85 - (85 - 75) * t; const bri = 39 + t * 3;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, sat, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_ember: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (py / h * 0.6 + px / w * 0.4); t = Math.max(0, Math.min(1, t));
                    const hue = 25 + (270 - 25) * t; const bri = 41 - t * 6;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, 80, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_arctic: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.3) * py / h + Math.sin(0.3) * px / w) * 0.7 + 0.3; t = Math.max(0, Math.min(1, t));
                    const hue = 210 + (178 - 210) * t; const sat = 18 + (75 - 18) * t; const bri = 44 - t * 4;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, sat, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_solar: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (py / h * 0.4 + px / w * 0.6); t = Math.max(0, Math.min(1, t));
                    const hue = 50 + (340 - 50) * t; const bri = 43 - t * 9;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, 83, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_venom: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(1.0) * py / h + Math.sin(1.0) * px / w) * 0.7 + 0.3; t = Math.max(0, Math.min(1, t));
                    const hue = 130 + (280 - 130) * t; const bri = 39 + t * 2;
                    const [r, g, b] = _hslToRgb(hue % 360, 82, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_mystichrome: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.9) * py / h + Math.sin(0.9) * px / w) * 0.7 + 0.25; t = Math.max(0, Math.min(1, t));
                    const hue = 140 + (290 - 140) * t; const bri = 38 + t * 2;
                    const [r, g, b] = _hslToRgb(hue % 360, 80, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_black_rainbow: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const stops = [[0, 350], [0.16, 30], [0.33, 90], [0.50, 180], [0.66, 240], [0.83, 290], [1, 340]];
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.7) * py / h + Math.sin(0.7) * px / w) * 0.6 + 0.4; t = Math.max(0, Math.min(1, t));
                    let si = 0; for (let i = 0; i < stops.length - 1; i++) { if (t >= stops[i][0] && t <= stops[i + 1][0]) si = i; }
                    const lt = (t - stops[si][0]) / (stops[si + 1][0] - stops[si][0] + 1e-6);
                    const hue = stops[si][1] + (stops[si + 1][1] - stops[si][1]) * lt;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, 78, 32);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_duochrome: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.6) * py / h + Math.sin(0.6) * px / w) * 0.8 + 0.2; t = Math.max(0, Math.min(1, t));
                    const hue = 175 + (280 - 175) * t; const bri = 40 + t * 2;
                    const [r, g, b] = _hslToRgb(hue % 360, 82, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_iridescent: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const stops = [[0, 200], [0.25, 280], [0.5, 340], [0.75, 40], [1, 170]];
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.5) * py / h + Math.sin(0.5) * px / w) * 0.6 + 0.35; t = Math.max(0, Math.min(1, t));
                    let si = 0; for (let i = 0; i < stops.length - 1; i++) { if (t >= stops[i][0] && t <= stops[i + 1][0]) si = i; }
                    const lt = (t - stops[si][0]) / (stops[si + 1][0] - stops[si][0] + 1e-6);
                    const hue = stops[si][1] + (stops[si + 1][1] - stops[si][1]) * lt;
                    const [r, g, b] = _hslToRgb(((hue % 360) + 360) % 360, 32, 44);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        prizm_adaptive: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let t = (Math.cos(0.8) * py / h + Math.sin(0.8) * px / w) * 0.7 + 0.3; t = Math.max(0, Math.min(1, t));
                    const hue = (180 + t * 216) % 360; const bri = 40 + t * 5;
                    const [r, g, b] = _hslToRgb(hue, 75, bri);
                    const idx = (py * w + px) * 4; id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        // --- SHOKK Series Monolithic Swatches ---
        shokk_ekg: (ctx, w, h) => {
            // Dark background with bright green EKG waveform
            ctx.fillStyle = '#0a1a0a'; ctx.fillRect(0, 0, w, h);
            // Faint grid lines
            ctx.strokeStyle = 'rgba(0,180,50,0.08)'; ctx.lineWidth = 0.5;
            for (let gy = 0; gy < h; gy += Math.max(4, h / 10)) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke(); }
            for (let gx = 0; gx < w; gx += Math.max(4, w / 10)) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke(); }
            // EKG waveform
            const cy = h * 0.5; const period = w / 2.5;
            ctx.beginPath(); ctx.moveTo(0, cy);
            for (let px = 0; px < w; px++) {
                const phase = ((px % period) / period);
                let yOff = 0;
                if (phase < 0.08) yOff = -Math.exp(-((phase - 0.06) ** 2) / 0.001) * 0.12 * h; // P-wave
                else if (phase > 0.22 && phase < 0.28) yOff = Math.exp(-((phase - 0.25) ** 2) / 0.0008) * 0.08 * h; // Q-dip
                else if (phase > 0.28 && phase < 0.38) yOff = -Math.exp(-((phase - 0.32) ** 2) / 0.0006) * 0.40 * h; // R-peak
                else if (phase > 0.38 && phase < 0.44) yOff = Math.exp(-((phase - 0.40) ** 2) / 0.0008) * 0.10 * h; // S-dip
                else if (phase > 0.48 && phase < 0.60) yOff = -Math.exp(-((phase - 0.53) ** 2) / 0.003) * 0.10 * h; // T-wave
                ctx.lineTo(px, cy + yOff);
            }
            // Glow pass
            ctx.strokeStyle = 'rgba(0,230,57,0.25)'; ctx.lineWidth = Math.max(6, h * 0.08); ctx.stroke();
            // Core pass
            ctx.strokeStyle = '#00E639'; ctx.lineWidth = Math.max(2, h * 0.025); ctx.stroke();
            // Bright center
            ctx.strokeStyle = 'rgba(180,255,200,0.7)'; ctx.lineWidth = Math.max(1, h * 0.008); ctx.stroke();
        },
        shokk_defib: (ctx, w, h) => {
            // Dark base with electric blue-white burst from two paddle points
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            const cx1 = w * 0.3, cx2 = w * 0.7, cy = h * 0.45;
            // Radial bursts
            for (const cx of [cx1, cx2]) {
                const rg = ctx.createRadialGradient(cx, cy, 0, cx, cy, w * 0.35);
                rg.addColorStop(0, 'rgba(200,240,255,0.6)'); rg.addColorStop(0.3, 'rgba(80,180,255,0.3)');
                rg.addColorStop(0.7, 'rgba(30,80,200,0.1)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = rg; ctx.fillRect(0, 0, w, h);
            }
            // Electric arcs between paddles
            ctx.strokeStyle = 'rgba(140,220,255,0.8)'; ctx.lineWidth = Math.max(2, h * 0.02);
            const rng = _seededRng(7700);
            for (let a = 0; a < 4; a++) {
                ctx.beginPath(); ctx.moveTo(cx1, cy);
                let ax = cx1, ay = cy;
                const segs = 12;
                for (let s = 1; s <= segs; s++) {
                    ax = cx1 + (cx2 - cx1) * s / segs;
                    ay = cy + (rng() - 0.5) * h * 0.3;
                    ctx.lineTo(ax, ay);
                }
                ctx.lineTo(cx2, cy); ctx.stroke();
            }
            // White core arc
            ctx.strokeStyle = 'rgba(220,240,255,0.9)'; ctx.lineWidth = Math.max(1, h * 0.008);
            ctx.beginPath(); ctx.moveTo(cx1, cy);
            ctx.bezierCurveTo(w * 0.4, cy - h * 0.15, w * 0.6, cy + h * 0.15, cx2, cy); ctx.stroke();
        },
        shokk_overload: (ctx, w, h) => {
            // Warm dark base with orange-yellow glitch hot blocks + scan lines
            ctx.fillStyle = '#1a1008'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(7800);
            // Glitch blocks
            for (let i = 0; i < 20; i++) {
                const bx = rng() * w, by = rng() * h;
                const bw = Math.max(3, rng() * w * 0.15), bh = Math.max(2, rng() * h * 0.12);
                const intensity = 0.4 + rng() * 0.6;
                ctx.fillStyle = `rgba(${Math.floor(220 * intensity)},${Math.floor(140 * intensity)},${Math.floor(20 * intensity)},${0.4 + rng() * 0.4})`;
                ctx.fillRect(bx, by, bw, bh);
            }
            // Scan line interference
            ctx.fillStyle = 'rgba(0,0,0,0.15)';
            for (let sy = 0; sy < h; sy += Math.max(3, h / 30)) { ctx.fillRect(0, sy, w, 1); }
            // Warning red zone
            const wg = ctx.createRadialGradient(w * 0.7, h * 0.3, 0, w * 0.7, h * 0.3, w * 0.3);
            wg.addColorStop(0, 'rgba(255,80,0,0.3)'); wg.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = wg; ctx.fillRect(0, 0, w, h);
        },
        shokk_blackout: (ctx, w, h) => {
            // Near-total black with faint red emergency strips
            ctx.fillStyle = '#060608'; ctx.fillRect(0, 0, w, h);
            // Faint emergency red horizontal strips
            const stripH = Math.max(2, h / 8);
            for (let sy = stripH; sy < h; sy += stripH) {
                const eg = ctx.createLinearGradient(0, sy - 1, 0, sy + 1);
                eg.addColorStop(0, 'rgba(0,0,0,0)'); eg.addColorStop(0.5, 'rgba(180,0,0,0.12)'); eg.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = eg; ctx.fillRect(0, sy - 2, w, 4);
            }
            // Faint flicker noise
            const rng = _seededRng(7900);
            for (let i = 0; i < 30; i++) {
                const fx = rng() * w, fy = rng() * h;
                ctx.fillStyle = `rgba(${80 + rng() * 60},0,0,${rng() * 0.06})`;
                ctx.fillRect(fx, fy, rng() * 8 + 1, rng() * 3 + 1);
            }
        },
        shokk_resurrection: (ctx, w, h) => {
            // Very dark base with bright gold crack lines + central light burst
            ctx.fillStyle = '#0a0808'; ctx.fillRect(0, 0, w, h);
            // Central light burst
            const lg = ctx.createRadialGradient(w * 0.5, h * 0.4, 0, w * 0.5, h * 0.4, w * 0.45);
            lg.addColorStop(0, 'rgba(220,180,80,0.35)'); lg.addColorStop(0.3, 'rgba(180,140,50,0.15)');
            lg.addColorStop(0.7, 'rgba(60,40,10,0.05)'); lg.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = lg; ctx.fillRect(0, 0, w, h);
            // Crack network (gold light breaking through)
            ctx.strokeStyle = 'rgba(220,180,60,0.7)'; ctx.lineWidth = Math.max(1, h * 0.012);
            const rng = _seededRng(8000);
            for (let c = 0; c < 8; c++) {
                ctx.beginPath();
                let cx2 = w * 0.5 + (rng() - 0.5) * w * 0.2, cy2 = h * 0.4 + (rng() - 0.5) * h * 0.2;
                ctx.moveTo(cx2, cy2);
                for (let s = 0; s < 6; s++) {
                    cx2 += (rng() - 0.5) * w * 0.2; cy2 += (rng() - 0.5) * h * 0.2;
                    ctx.lineTo(cx2, cy2);
                }
                ctx.stroke();
            }
            // Glow on cracks
            ctx.strokeStyle = 'rgba(255,220,100,0.25)'; ctx.lineWidth = Math.max(4, h * 0.04);
            const rng2 = _seededRng(8000);
            for (let c = 0; c < 8; c++) {
                ctx.beginPath();
                let cx3 = w * 0.5 + (rng2() - 0.5) * w * 0.2, cy3 = h * 0.4 + (rng2() - 0.5) * h * 0.2;
                ctx.moveTo(cx3, cy3);
                for (let s = 0; s < 6; s++) { cx3 += (rng2() - 0.5) * w * 0.2; cy3 += (rng2() - 0.5) * h * 0.2; ctx.lineTo(cx3, cy3); }
                ctx.stroke();
            }
        },
        shokk_voltage: (ctx, w, h) => {
            // Dark base with bright yellow-blue Lichtenberg lightning branches
            ctx.fillStyle = '#0a0a10'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8100);
            // Draw branching lightning paths
            function drawBranch(x, y, angle, len, depth, maxD) {
                if (depth > maxD || len < 2) return;
                const ex = x + Math.cos(angle) * len, ey = y + Math.sin(angle) * len;
                // Glow
                ctx.strokeStyle = `rgba(200,220,50,${0.15 * (1 - depth / maxD)})`; ctx.lineWidth = Math.max(4, h * 0.03 * (1 - depth / maxD));
                ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(ex, ey); ctx.stroke();
                // Core
                ctx.strokeStyle = `rgba(240,240,80,${0.7 * (1 - depth / maxD)})`; ctx.lineWidth = Math.max(1, h * 0.008 * (1 - depth / maxD));
                ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(ex, ey); ctx.stroke();
                // Branch
                const branches = 1 + Math.floor(rng() * 2);
                for (let b = 0; b < branches; b++) {
                    drawBranch(ex, ey, angle + (rng() - 0.5) * 1.2, len * (0.5 + rng() * 0.3), depth + 1, maxD);
                }
            }
            for (let i = 0; i < 3; i++) {
                const sx = rng() * w, sy = rng() * h * 0.3;
                drawBranch(sx, sy, Math.PI * 0.4 + rng() * 0.4, w * 0.15, 0, 5);
            }
        },
        shokk_flatline: (ctx, w, h) => {
            // Very dark dead zone with thin green flatline and one dramatic R-peak spike
            ctx.fillStyle = '#080a08'; ctx.fillRect(0, 0, w, h);
            const cy = h * 0.5;
            // Faint flatline across width
            ctx.strokeStyle = 'rgba(0,180,50,0.15)'; ctx.lineWidth = Math.max(1, h * 0.006);
            ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.stroke();
            // Single dramatic R-peak spike near center
            const spikeX = w * 0.5, spikeW = w * 0.08;
            ctx.beginPath(); ctx.moveTo(spikeX - spikeW, cy);
            ctx.lineTo(spikeX - spikeW * 0.3, cy + h * 0.06); // small Q dip
            ctx.lineTo(spikeX, cy - h * 0.32); // tall R peak
            ctx.lineTo(spikeX + spikeW * 0.3, cy + h * 0.08); // S dip
            ctx.lineTo(spikeX + spikeW, cy);
            // Glow
            ctx.strokeStyle = 'rgba(0,230,60,0.3)'; ctx.lineWidth = Math.max(5, h * 0.06); ctx.stroke();
            // Core
            ctx.strokeStyle = '#00E639'; ctx.lineWidth = Math.max(2, h * 0.02); ctx.stroke();
            // Bright white center of spike
            ctx.strokeStyle = 'rgba(180,255,200,0.8)'; ctx.lineWidth = Math.max(1, h * 0.006); ctx.stroke();
        },
        shokk_adrenaline: (ctx, w, h) => {
            // Deep red-black base with pulsing concentric red rings from center
            ctx.fillStyle = '#1a0808'; ctx.fillRect(0, 0, w, h);
            const cx2 = w * 0.5, cy2 = h * 0.5;
            const maxR = Math.sqrt(cx2 * cx2 + cy2 * cy2);
            const ringSpacing = Math.max(6, maxR * 0.08);
            // Concentric pulse rings
            for (let r = ringSpacing; r < maxR; r += ringSpacing) {
                const fade = Math.max(0, 1 - r / maxR);
                ctx.strokeStyle = `rgba(255,30,30,${0.15 + fade * 0.35})`; ctx.lineWidth = Math.max(2, h * 0.015 * fade);
                ctx.beginPath(); ctx.arc(cx2, cy2, r, 0, Math.PI * 2); ctx.stroke();
            }
            // Hot center glow
            const cg = ctx.createRadialGradient(cx2, cy2, 0, cx2, cy2, maxR * 0.25);
            cg.addColorStop(0, 'rgba(255,60,30,0.5)'); cg.addColorStop(0.5, 'rgba(200,20,10,0.2)'); cg.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
        },
        shokk_aftermath: (ctx, w, h) => {
            // Scorched charred surface with orange ember glow cracks
            const id = ctx.createImageData(w, h); const rng = _seededRng(8400);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const n = (noise[i] + 1) * 0.5;
                // Dark charred base
                let r = Math.floor(30 + n * 25), g = Math.floor(18 + n * 15), b = Math.floor(12 + n * 10);
                // Ember cracks where noise > threshold
                if (n > 0.72) {
                    const ember = (n - 0.72) / 0.28;
                    r = Math.floor(r + ember * 200); g = Math.floor(g + ember * 80); b = Math.floor(b + ember * 10);
                }
                id.data[i * 4] = Math.min(255, r); id.data[i * 4 + 1] = Math.min(255, g); id.data[i * 4 + 2] = Math.min(255, b); id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Ash texture overlay
            ctx.fillStyle = 'rgba(60,50,40,0.08)';
            for (let i = 0; i < 40; i++) { ctx.fillRect(rng() * w, rng() * h, rng() * 6 + 1, rng() * 4 + 1); }
        },
        shokk_unleashed: (ctx, w, h) => {
            // Maximum chaos: multi-color energy + lightning arcs + plasma bursts
            ctx.fillStyle = '#120808'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8500);
            // Chaotic color energy zones
            const id = ctx.createImageData(w, h);
            const nr = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.3, 0.4], rng);
            const ng = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.3, 0.4], _seededRng(8537));
            const nb = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.3, 0.4], _seededRng(8574));
            for (let i = 0; i < w * h; i++) {
                const r2 = Math.floor(18 + Math.max(0, (nr[i] + 0.3)) * 100);
                const g2 = Math.floor(8 + Math.max(0, (ng[i] + 0.3)) * 80);
                const b2 = Math.floor(8 + Math.max(0, (nb[i] + 0.3)) * 90);
                id.data[i * 4] = Math.min(255, r2); id.data[i * 4 + 1] = Math.min(255, g2); id.data[i * 4 + 2] = Math.min(255, b2); id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Lightning arcs
            ctx.lineWidth = Math.max(1, h * 0.012);
            for (let a = 0; a < 5; a++) {
                const colors = ['rgba(255,100,0,0.6)', 'rgba(0,200,255,0.6)', 'rgba(255,255,80,0.6)', 'rgba(200,50,255,0.5)', 'rgba(255,200,100,0.5)'];
                ctx.strokeStyle = colors[a % 5];
                ctx.beginPath(); let ax = rng() * w, ay = rng() * h;
                ctx.moveTo(ax, ay);
                for (let s = 0; s < 8; s++) { ax += (rng() - 0.5) * w * 0.25; ay += (rng() - 0.5) * h * 0.25; ctx.lineTo(ax, ay); }
                ctx.stroke();
            }
            // Plasma bursts
            for (let b = 0; b < 6; b++) {
                const bx = rng() * w, by = rng() * h, br = Math.max(3, Math.min(w, h) * 0.04 * (0.5 + rng()));
                const pg = ctx.createRadialGradient(bx, by, 0, bx, by, br);
                const hue = rng() * 360;
                pg.addColorStop(0, `hsla(${hue},90%,80%,0.5)`); pg.addColorStop(0.5, `hsla(${hue},80%,50%,0.2)`); pg.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = pg; ctx.fillRect(bx - br, by - br, br * 2, br * 2);
            }
        },
        shokk_lafleur: (ctx, w, h) => {
            // Mardi Gras tri-color zones with gold fleur-de-lis motif
            const id = ctx.createImageData(w, h); const rng = _seededRng(8600);
            const noise = _simpleNoise2D(w, h, [16, 32], [0.5, 0.5], rng);
            for (let i = 0; i < w * h; i++) {
                const n = (noise[i] + 1) * 0.5;
                let r, g, b;
                if (n < 0.33) {// Purple zone
                    const s = n / 0.33; r = Math.floor(80 + s * 30); g = Math.floor(20 + s * 15); b = Math.floor(120 + s * 40);
                } else if (n < 0.66) {// Gold zone
                    const s = (n - 0.33) / 0.33; r = Math.floor(180 + s * 40); g = Math.floor(140 + s * 30); b = Math.floor(30 + s * 20);
                } else {// Green zone
                    const s = (n - 0.66) / 0.34; r = Math.floor(20 + s * 20); g = Math.floor(100 + s * 60); b = Math.floor(40 + s * 20);
                }
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Tiled fleur-de-lis in gold
            const tileSize = Math.max(16, Math.min(w, h) * 0.28);
            ctx.fillStyle = 'rgba(210,175,55,0.55)'; ctx.strokeStyle = 'rgba(210,175,55,0.7)'; ctx.lineWidth = Math.max(1, tileSize * 0.02);
            for (let ty = tileSize * 0.5; ty < h + tileSize; ty += tileSize) {
                for (let tx = tileSize * 0.5; tx < w + tileSize; tx += tileSize) {
                    const s = tileSize * 0.35;
                    ctx.beginPath();
                    // Center petal (tall pointed)
                    ctx.moveTo(tx, ty - s * 0.9); ctx.quadraticCurveTo(tx + s * 0.15, ty - s * 0.4, tx + s * 0.08, ty + s * 0.1);
                    ctx.lineTo(tx - s * 0.08, ty + s * 0.1); ctx.quadraticCurveTo(tx - s * 0.15, ty - s * 0.4, tx, ty - s * 0.9);
                    ctx.fill();
                    // Left petal
                    ctx.beginPath(); ctx.moveTo(tx - s * 0.08, ty - s * 0.15);
                    ctx.quadraticCurveTo(tx - s * 0.55, ty - s * 0.6, tx - s * 0.45, ty - s * 0.05);
                    ctx.quadraticCurveTo(tx - s * 0.3, ty + s * 0.1, tx - s * 0.08, ty + s * 0.1);
                    ctx.fill();
                    // Right petal (mirror)
                    ctx.beginPath(); ctx.moveTo(tx + s * 0.08, ty - s * 0.15);
                    ctx.quadraticCurveTo(tx + s * 0.55, ty - s * 0.6, tx + s * 0.45, ty - s * 0.05);
                    ctx.quadraticCurveTo(tx + s * 0.3, ty + s * 0.1, tx + s * 0.08, ty + s * 0.1);
                    ctx.fill();
                    // Stem
                    ctx.fillRect(tx - s * 0.04, ty + s * 0.1, s * 0.08, s * 0.35);
                    // Crossbar
                    ctx.fillRect(tx - s * 0.18, ty + s * 0.12, s * 0.36, s * 0.06);
                }
            }
        },
        // ===== PARADIGM MONOLITHICS =====
        void: (ctx, w, h) => {
            // Zero-specular void patches surrounded by mirror chrome
            ctx.fillStyle = '#ccdde8'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8800);
            for (let i = 0; i < 8; i++) {
                const x = rng() * w, y = rng() * h, r = 3 + rng() * 8;
                const g = ctx.createRadialGradient(x, y, 0, x, y, r);
                g.addColorStop(0, '#020202'); g.addColorStop(0.7, '#050505');
                g.addColorStop(1, 'rgba(200,220,232,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            }
        },
        living_chrome: (ctx, w, h) => {
            // Breathing chrome - undulating metallic surface
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#b8c4d0'); g.addColorStop(0.2, '#dce4ec');
            g.addColorStop(0.4, '#a0b0c0'); g.addColorStop(0.6, '#e8eef4');
            g.addColorStop(0.8, '#98a8b8'); g.addColorStop(1, '#c8d4e0');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Subtle wave ripples
            ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 1;
            for (let i = 0; i < 6; i++) {
                ctx.beginPath();
                for (let x = 0; x < w; x++) {
                    const y = h * 0.2 + i * h * 0.12 + Math.sin(x * 0.08 + i) * 4;
                    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        },
        quantum: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2; const rng = _seededRng(8802);
            for (let i = 0; i < 400; i++) {
                const angle = rng() * Math.PI * 2; const dist = rng() * Math.min(w, h) * 0.45;
                const x = cx + Math.cos(angle) * dist, y = cy + Math.sin(angle) * dist;
                const alpha = 0.15 + (1 - dist / (Math.min(w, h) * 0.45)) * 0.5;
                ctx.fillStyle = rng() > 0.5 ? `rgba(0,255,255,${alpha})` : `rgba(255,0,255,${alpha})`;
                ctx.fillRect(x, y, 1, 1);
            }
            ctx.fillStyle = 'rgba(255,255,255,0.2)'; ctx.shadowBlur = 8; ctx.shadowColor = '#ffffff';
            ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        p_aurora: (ctx, w, h) => {
            // Northern lights - horizontal curtain waves
            ctx.fillStyle = '#040818'; ctx.fillRect(0, 0, w, h);
            const colors = ['rgba(40,220,160,', 'rgba(80,160,255,', 'rgba(120,80,200,', 'rgba(60,255,120,'];
            for (let i = 0; i < colors.length; i++) {
                ctx.beginPath();
                ctx.moveTo(0, h * 0.2 + i * h * 0.15);
                for (let x = 0; x <= w; x += 2) {
                    const y = h * 0.2 + i * h * 0.15 + Math.sin(x * 0.05 + i * 2) * h * 0.08 + Math.sin(x * 0.12 + i) * h * 0.03;
                    ctx.lineTo(x, y);
                }
                ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath();
                const g = ctx.createLinearGradient(0, h * 0.2 + i * h * 0.15, 0, h);
                g.addColorStop(0, colors[i] + '0.35)'); g.addColorStop(0.3, colors[i] + '0.15)');
                g.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g; ctx.fill();
            }
        },
        magnetic: (ctx, w, h) => {
            // Iron filing field lines - radiating from poles
            ctx.fillStyle = '#1a2030'; ctx.fillRect(0, 0, w, h);
            const cx1 = w * 0.25, cy1 = h * 0.5, cx2 = w * 0.75, cy2 = h * 0.5;
            ctx.strokeStyle = 'rgba(100,130,180,0.25)'; ctx.lineWidth = 1;
            for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
                ctx.beginPath();
                ctx.moveTo(cx1 + Math.cos(a) * 5, cy1 + Math.sin(a) * 5);
                const mx = w * 0.5 + Math.sin(a) * h * 0.15, my = h * 0.5 + Math.cos(a) * h * 0.3;
                ctx.quadraticCurveTo(mx, my, cx2 + Math.cos(a + Math.PI) * 5, cy2 + Math.sin(a + Math.PI) * 5);
                ctx.stroke();
            }
            // Pole dots
            ctx.fillStyle = 'rgba(140,160,200,0.5)';
            ctx.beginPath(); ctx.arc(cx1, cy1, 3, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.arc(cx2, cy2, 3, 0, Math.PI * 2); ctx.fill();
        },
        ember: (ctx, w, h) => {
            // Glowing hot metal cooling - heat-mapped noise
            ctx.fillStyle = '#1a0800'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8805);
            const id = ctx.getImageData(0, 0, w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const n = rng();
                    const idx = (py * w + px) * 4;
                    if (n > 0.7) {
                        const t = (n - 0.7) / 0.3;
                        id.data[idx] = Math.floor(40 + t * 200);
                        id.data[idx + 1] = Math.floor(t * 80);
                        id.data[idx + 2] = 0;
                    } else {
                        id.data[idx] = 26; id.data[idx + 1] = 8; id.data[idx + 2] = 0;
                    }
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        stealth: (ctx, w, h) => {
            // Radar-absorbing angular facets - dark Voronoi panels
            ctx.fillStyle = '#181818'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8806);
            ctx.strokeStyle = 'rgba(40,40,48,0.6)'; ctx.lineWidth = 1;
            const pts = []; for (let i = 0; i < 10; i++) pts.push({ x: rng() * w, y: rng() * h });
            // Draw panels as angular shapes
            for (let i = 0; i < pts.length; i++) {
                ctx.beginPath();
                const p = pts[i];
                ctx.moveTo(p.x, p.y);
                for (let j = 0; j < 3; j++) {
                    const np = pts[(i + j + 1) % pts.length];
                    ctx.lineTo(np.x, np.y);
                }
                ctx.closePath();
                ctx.fillStyle = 'rgba(' + (20 + rng() * 12) + ',' + (20 + rng() * 12) + ',' + (22 + rng() * 14) + ',1)';
                ctx.fill(); ctx.stroke();
            }
        },
        glass_armor: (ctx, w, h) => {
            // Transparent armor plating - glass panels with metallic frames
            ctx.fillStyle = '#88aacc'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8807);
            ctx.strokeStyle = 'rgba(180,200,220,0.7)'; ctx.lineWidth = 2;
            // Grid of panels
            const cols = 4, rows = 3;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const px = c * w / cols + 2, py = r * h / rows + 2;
                    const pw = w / cols - 4, ph = h / rows - 4;
                    ctx.fillStyle = 'rgba(160,200,230,' + (0.3 + rng() * 0.2) + ')';
                    ctx.fillRect(px, py, pw, ph);
                    ctx.strokeRect(px, py, pw, ph);
                }
            }
        },
        p_static: (ctx, w, h) => {
            // TV static noise - random gray per pixel block
            const id = ctx.createImageData(w, h); const rng = _seededRng(8808);
            const bs = 2;
            for (let py = 0; py < h; py += bs) {
                for (let px = 0; px < w; px += bs) {
                    const v = Math.floor(rng() * 220 + 20);
                    for (let dy = 0; dy < bs && py + dy < h; dy++) {
                        for (let dx = 0; dx < bs && px + dx < w; dx++) {
                            const idx = ((py + dy) * w + (px + dx)) * 4;
                            id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v; id.data[idx + 3] = 255;
                        }
                    }
                }
            }
            ctx.putImageData(id, 0, 0);
            // Scan lines
            ctx.fillStyle = 'rgba(0,0,0,0.08)';
            for (let y = 0; y < h; y += 3) ctx.fillRect(0, y, w, 1);
        },
        mercury_pool: (ctx, w, h) => {
            // Liquid mercury pools - smooth flowing silver blobs
            ctx.fillStyle = '#8898a8'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8809);
            for (let i = 0; i < 6; i++) {
                const x = rng() * w, y = rng() * h, r = 6 + rng() * 12;
                const g = ctx.createRadialGradient(x - r * 0.2, y - r * 0.2, 0, x, y, r);
                g.addColorStop(0, 'rgba(230,236,242,0.8)');
                g.addColorStop(0.5, 'rgba(190,200,215,0.5)');
                g.addColorStop(1, 'rgba(136,152,168,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            }
        },
        phase_shift: (ctx, w, h) => {
            ctx.fillStyle = '#333333'; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.6;
            for (let wave = 0; wave < 3; wave++) {
                ctx.strokeStyle = wave === 0 ? 'rgba(0,255,255,0.8)' : wave === 1 ? 'rgba(255,0,255,0.8)' : 'rgba(255,255,0,0.8)';
                ctx.lineWidth = 2; ctx.beginPath();
                for (let x = 0; x <= w; x += 2) {
                    const y = h / 2 + Math.sin((x / w) * Math.PI * 4 + wave * 2) * h * 0.35;
                    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        gravity_well: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2; const rng = _seededRng(8811);
            const dots = []; for (let i = 0; i < 120; i++) dots.push([rng() * w, rng() * h]);
            dots.forEach(([x, y]) => {
                const dx = x - cx, dy = y - cy; const dist = Math.hypot(dx, dy) || 0.01;
                const pull = 1 + 80 / (dist + 10); const nx = cx + dx * pull, ny = cy + dy * pull;
                ctx.fillStyle = '#ffffff'; ctx.fillRect(nx, ny, 1, 1);
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        thin_film: (ctx, w, h) => {
            // Oil-on-water rainbow - linked color + reflectivity
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = (Math.sin(px * 0.08 + py * 0.04) * 0.3 + Math.sin(py * 0.06 - px * 0.05) * 0.2 + 0.5);
                    const hue = (t * 360) % 360;
                    const [r, g, b] = _hslToRgb(hue, 55, 50 + t * 15);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        blackbody: (ctx, w, h) => {
            // Temperature gradient - black→red→orange→yellow→white
            const g = ctx.createLinearGradient(0, h, w, 0);
            g.addColorStop(0, '#0a0000'); g.addColorStop(0.25, '#cc2200');
            g.addColorStop(0.5, '#ee8800'); g.addColorStop(0.75, '#ffdd44');
            g.addColorStop(1, '#ffffee');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        wormhole: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2; const baseR = Math.min(w, h) * 0.45;
            for (let i = 12; i >= 0; i--) {
                const t = i / 12; const r = baseR * (1 - t * 0.85); const rot = (12 - i) * (Math.PI / 12);
                ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(1, 0.6);
                const g = ctx.createLinearGradient(-r, 0, r, 0);
                g.addColorStop(0, `rgba(80,40,120,${0.3 + t * 0.5})`);
                g.addColorStop(0.5, `rgba(200,180,255,${0.5 + t * 0.4})`);
                g.addColorStop(1, `rgba(80,40,120,${0.3 + t * 0.5})`);
                ctx.strokeStyle = g; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(0, 0, r, r * 0.8, 0, 0, Math.PI * 2); ctx.stroke();
                ctx.restore();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        crystal_lattice: (ctx, w, h) => {
            ctx.fillStyle = '#000033'; ctx.fillRect(0, 0, w, h);
            const s = Math.min(w, h) / 6; const nodes = [];
            for (let row = -1; row <= 4; row++) {
                for (let col = -1; col <= 4; col++) {
                    const x = w * 0.2 + col * s * 1.2 + (row % 2) * s * 0.6;
                    const y = h * 0.2 + row * s * 0.7;
                    nodes.push([x, y]);
                }
            }
            ctx.strokeStyle = '#888888'; ctx.lineWidth = 2;
            nodes.forEach((a, i) => {
                nodes.forEach((b, j) => {
                    if (j <= i) return;
                    const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
                    if (d > 0 && d < s * 1.8) { ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
                });
            });
            ctx.fillStyle = '#cccccc'; nodes.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill(); });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        pulse: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cy = h / 2; ctx.strokeStyle = '#ff0000'; ctx.lineWidth = 2; ctx.shadowBlur = 6; ctx.shadowColor = '#ff0000';
            ctx.beginPath(); ctx.moveTo(0, cy);
            for (let x = 0; x <= w; x += 3) {
                const spike = (x > w * 0.4 && x < w * 0.6) ? Math.sin((x - w * 0.5) * 20) * h * 0.35 : 0;
                ctx.lineTo(x, cy - spike);
            }
            ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        // === FLAMES (12) - Upgraded: real tongue geometry, staggered heights, core→transparent gradient ===
        classic_hotrod: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const tongues = [[0.02, 0.92, 0.88, 0.08], [0.08, 0.88, 0.92, 0.18], [0.12, 0.95, 0.78, 0.05], [0.05, 0.9, 0.85, 0.12], [0.1, 0.98, 0.95, 0.22]];
            tongues.forEach(([x0r, y0r, x1r, y1r]) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.08;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#ffffff'); g.addColorStop(0.2, '#ffcc00'); g.addColorStop(0.5, '#ff6600'); g.addColorStop(1, '#aa0000');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2 - 2, x1, y1);
                ctx.quadraticCurveTo(x1 + bw * 0.5, y1 + 4, x0 + w * 0.15, y0);
                ctx.closePath(); ctx.fill();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        ghost_flames: (ctx, w, h) => {
            ctx.fillStyle = '#000011'; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.25;
            const tongues = [[0.02, 0.92, 0.88, 0.08], [0.08, 0.88, 0.92, 0.18], [0.12, 0.95, 0.78, 0.05], [0.05, 0.9, 0.85, 0.12], [0.1, 0.98, 0.95, 0.22]];
            tongues.forEach(([x0r, y0r, x1r, y1r]) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.08;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#ffffff'); g.addColorStop(1, '#999999');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2 - 2, x1, y1);
                ctx.quadraticCurveTo(x1 + bw * 0.5, y1 + 4, x0 + w * 0.15, y0);
                ctx.closePath(); ctx.fill();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        pinstripe_flames: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#00ff00'; ctx.lineWidth = 1.5;
            const tongues = [[0.02, 0.92, 0.88, 0.08], [0.08, 0.88, 0.92, 0.18], [0.12, 0.95, 0.78, 0.05], [0.05, 0.9, 0.85, 0.12], [0.1, 0.98, 0.95, 0.22]];
            tongues.forEach(([x0r, y0r, x1r, y1r]) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.08;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2 - 2, x1, y1);
                ctx.quadraticCurveTo(x1 + bw * 0.5, y1 + 4, x0 + w * 0.15, y0);
                ctx.closePath(); ctx.stroke();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        fire_lick: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 8; i++) {
                const baseX = (i / 8) * w * 0.45, tipY = h * (0.35 + (i % 3) * 0.08), bw = w * 0.04;
                const x0 = baseX, y0 = h, x1 = baseX + w * 0.22, y1 = tipY;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#ffffaa'); g.addColorStop(0.3, '#ff6600'); g.addColorStop(0.7, '#cc2200'); g.addColorStop(1, 'rgba(204,34,0,0)');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, y0 - (y0 - y1) * 0.5, x1, y1);
                ctx.quadraticCurveTo(x1 + bw * 0.5, y1 + 4, x0 + w * 0.08, y0);
                ctx.closePath(); ctx.fill();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        inferno: (ctx, w, h) => {
            ctx.fillStyle = '#440000'; ctx.fillRect(0, 0, w, h);
            const tongues = [[0.1, 0.95, 0.5, 0.35], [0.9, 0.9, 0.55, 0.4], [0, 0.7, 0.45, 0.25], [0.95, 0.75, 0.6, 0.3]];
            tongues.forEach(([x0r, y0r, x1r, y1r]) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.06;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#660000'); g.addColorStop(0.5, '#aa2200'); g.addColorStop(1, '#330000');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo((x0 + x1) / 2 + bw, (y0 + y1) / 2, x1, y1);
                ctx.quadraticCurveTo(x1 + 3, y1 + 4, x0 + w * 0.1, y0);
                ctx.closePath(); ctx.fill();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        fireball: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.2, cy = h / 2, maxR = w * 0.28;
            const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR);
            g.addColorStop(0, '#ffffff'); g.addColorStop(0.3, '#ffcc00'); g.addColorStop(0.7, '#ff6600'); g.addColorStop(1, 'rgba(255,102,0,0)');
            ctx.shadowBlur = 12; ctx.shadowColor = '#ffcc00';
            ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, maxR, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = 'rgba(255,150,0,0.5)'; ctx.lineWidth = 1;
            for (let i = 0; i < 6; i++) {
                const x0 = cx + maxR, y0 = cy; const x1 = w * (0.6 + i * 0.06), y1 = cy + (i % 2 ? 4 : -4);
                ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
            }
            ctx.fillStyle = '#ff6600'; for (let i = 0; i < 8; i++) { ctx.beginPath(); ctx.arc(w * (0.75 + (i % 4) * 0.06), cy + (i - 2) * 2, 1, 0, Math.PI * 2); ctx.fill(); }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        hellfire: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const tongues = [[0.15, 0.9, 0.7, 0.2], [0.5, 0.95, 0.85, 0.15], [0.8, 0.88, 0.9, 0.25]];
            tongues.forEach(([x0r, y0r, x1r, y1r]) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.07;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#440088'); g.addColorStop(0.5, '#880000'); g.addColorStop(1, '#000000');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2, x1, y1);
                ctx.quadraticCurveTo(x1 + bw, y1 + 4, x0 + w * 0.18, y0);
                ctx.closePath(); ctx.fill();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        wildfire: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(605);
            for (let row = 0; row < 6; row++) {
                for (let i = 0; i < 4; i++) {
                    const baseX = (i / 4) * w * 0.6 + rng() * 12, tipY = h * (0.05 + row * 0.16 + rng() * 0.1), bw = w * 0.04;
                    const x0 = baseX, y0 = h - row * 3, x1 = baseX + w * (0.25 + rng() * 0.2), y1 = tipY;
                    const g = ctx.createLinearGradient(x0, y0, x1, y1);
                    g.addColorStop(0, '#ffffff'); g.addColorStop(0.3, '#ff6600'); g.addColorStop(1, 'rgba(204,34,0,0)');
                    ctx.fillStyle = g;
                    ctx.beginPath(); ctx.moveTo(x0, y0);
                    ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2 + (rng() - 0.5) * 6, x1, y1);
                    ctx.quadraticCurveTo(x1 + bw, y1 + 4, x0 + w * 0.08, y0);
                    ctx.closePath(); ctx.fill();
                }
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        flame_fade: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const tongues = [[0.02, 0.92, 0.88, 0.08], [0.08, 0.88, 0.92, 0.18], [0.12, 0.95, 0.78, 0.05], [0.05, 0.9, 0.85, 0.12]];
            tongues.forEach(([x0r, y0r, x1r, y1r], i) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.08;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#ffcc00'); g.addColorStop(0.5, '#ff6600'); g.addColorStop(1, '#aa0000');
                ctx.fillStyle = g; ctx.globalAlpha = 1 - (x1 / w) * 0.9;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2 - 2, x1, y1);
                ctx.quadraticCurveTo(x1 + bw * 0.5, y1 + 4, x0 + w * 0.15, y0);
                ctx.closePath(); ctx.fill();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        blue_flame: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const tongues = [[0.02, 0.92, 0.88, 0.08], [0.08, 0.88, 0.92, 0.18], [0.12, 0.95, 0.78, 0.05], [0.05, 0.9, 0.85, 0.12], [0.1, 0.98, 0.95, 0.22]];
            tongues.forEach(([x0r, y0r, x1r, y1r]) => {
                const x0 = x0r * w, y0 = y0r * h, x1 = x1r * w, y1 = y1r * h, bw = w * 0.08;
                const g = ctx.createLinearGradient(x0, y0, x1, y1);
                g.addColorStop(0, '#ffffff'); g.addColorStop(0.25, '#00ffff'); g.addColorStop(1, '#0000bb');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x0, y0);
                ctx.quadraticCurveTo(x0 + bw, (y0 + y1) / 2 - 2, x1, y1);
                ctx.quadraticCurveTo(x1 + bw * 0.5, y1 + 4, x0 + w * 0.15, y0);
                ctx.closePath(); ctx.fill();
            });
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        torch_burn: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h * 0.92;
            const g = ctx.createLinearGradient(cx, cy, cx, 0);
            g.addColorStop(0, '#ffffff'); g.addColorStop(0.2, '#ffcc00'); g.addColorStop(0.5, '#ff6600'); g.addColorStop(0.8, '#aa0000'); g.addColorStop(1, 'rgba(170,0,0,0)');
            ctx.fillStyle = g;
            for (let i = -4; i <= 4; i++) {
                const spread = 0.08; const ax = i * spread;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + w * (ax - 0.02), h * 0.2); ctx.lineTo(cx + w * (ax + 0.02), h * 0.2);
                ctx.closePath(); ctx.fill();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        ember_scatter: (ctx, w, h) => {
            ctx.fillStyle = '#0a0500'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(609);
            for (let i = 0; i < 40; i++) {
                const x = rng() * w, y = rng() * h, r = 0.5 + rng() * 2;
                const bright = Math.floor(150 + rng() * 105);
                ctx.fillStyle = `rgb(${bright},${Math.floor(bright * 0.4)},0)`;
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
            }
        },

        // === SKATE & SURF (12) ===
        wave_curl: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, 0, h);
            g.addColorStop(0, '#0066aa'); g.addColorStop(0.5, '#0088cc'); g.addColorStop(1, '#004477');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(255,255,255,0.4)'; ctx.lineWidth = 2;
            for (let y = 8; y < h; y += 12) {
                ctx.beginPath();
                for (let x = 0; x < w; x++) ctx.lineTo(x, y + Math.sin(x * 0.2 + y * 0.1) * 5);
                ctx.stroke();
            }
        },
        ocean_foam: (ctx, w, h) => {
            ctx.fillStyle = '#2288aa'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(611);
            ctx.fillStyle = 'rgba(255,255,255,0.5)';
            for (let i = 0; i < 60; i++) {
                const x = rng() * w, y = rng() * h, r = 0.5 + rng() * 2.5;
                ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
            }
        },
        palm_frond: (ctx, w, h) => {
            ctx.fillStyle = '#226644'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#44aa66'; ctx.lineWidth = 1.5;
            const cx = w * 0.3, cy = h;
            for (let a = -0.8; a < 0.8; a += 0.15) {
                ctx.beginPath(); ctx.moveTo(cx, cy);
                const ex = cx + Math.cos(a - 1) * w * 0.8, ey = cy + Math.sin(a - 1) * h * 0.9;
                ctx.quadraticCurveTo(cx + Math.cos(a) * w * 0.4, cy - h * 0.5, ex, ey);
                ctx.stroke();
            }
        },
        tiki_totem: (ctx, w, h) => {
            ctx.fillStyle = '#8a6633'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#553311'; ctx.lineWidth = 1.5;
            // Eyes
            ctx.beginPath(); ctx.arc(w * 0.3, h * 0.3, 4, 0, Math.PI * 2); ctx.stroke();
            ctx.beginPath(); ctx.arc(w * 0.7, h * 0.3, 4, 0, Math.PI * 2); ctx.stroke();
            // Mouth
            ctx.beginPath(); ctx.rect(w * 0.25, h * 0.55, w * 0.5, h * 0.15); ctx.stroke();
            // Teeth lines
            for (let x = w * 0.35; x < w * 0.7; x += 5) {
                ctx.beginPath(); ctx.moveTo(x, h * 0.55); ctx.lineTo(x, h * 0.7); ctx.stroke();
            }
        },
        grip_tape: (ctx, w, h) => {
            ctx.fillStyle = '#222'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(614); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) {
                const n = Math.floor(rng() * 50); id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
            }
            ctx.putImageData(id, 0, 0);
        },
        halfpipe: (ctx, w, h) => {
            ctx.fillStyle = '#778899'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#556677'; ctx.lineWidth = 1.5;
            // Curved ramp sides
            ctx.beginPath(); ctx.moveTo(0, h * 0.3);
            ctx.quadraticCurveTo(0, h, w * 0.3, h); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(w, h * 0.3);
            ctx.quadraticCurveTo(w, h, w * 0.7, h); ctx.stroke();
            // Horizontal lines
            for (let y = h * 0.4; y < h; y += 6) {
                ctx.strokeStyle = 'rgba(100,120,140,0.3)';
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }
        },
        bamboo_stalk: (ctx, w, h) => {
            ctx.fillStyle = '#556633'; ctx.fillRect(0, 0, w, h);
            const stalks = [w * 0.2, w * 0.5, w * 0.8];
            stalks.forEach(x => {
                ctx.fillStyle = '#88aa44'; ctx.fillRect(x - 3, 0, 6, h);
                // Joints
                ctx.fillStyle = '#6a8833';
                for (let y = 8; y < h; y += 14) { ctx.fillRect(x - 4, y, 8, 3); }
            });
        },
        surf_stripe: (ctx, w, h) => {
            ctx.fillStyle = '#ddddcc'; ctx.fillRect(0, 0, w, h);
            const colors = ['#22aacc', '#ffffff', '#ee5533'];
            colors.forEach((c, i) => {
                ctx.fillStyle = c;
                ctx.fillRect(0, h * 0.3 + i * 5, w, 4);
            });
        },
        board_wax: (ctx, w, h) => {
            ctx.fillStyle = '#cccc99'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(618);
            ctx.strokeStyle = 'rgba(180,180,140,0.5)'; ctx.lineWidth = 1;
            for (let i = 0; i < 12; i++) {
                const cx = rng() * w, cy = rng() * h, r = 3 + rng() * 8;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        tropical_leaf: (ctx, w, h) => {
            ctx.fillStyle = '#114422'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#33aa66';
            // Large leaf shape
            ctx.beginPath(); ctx.moveTo(w * 0.1, h * 0.9);
            ctx.bezierCurveTo(w * 0.3, h * 0.2, w * 0.7, h * 0.1, w * 0.9, h * 0.5);
            ctx.bezierCurveTo(w * 0.6, h * 0.4, w * 0.4, h * 0.6, w * 0.1, h * 0.9);
            ctx.fill();
            // Center vein
            ctx.strokeStyle = '#228855'; ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(w * 0.1, h * 0.9);
            ctx.quadraticCurveTo(w * 0.5, h * 0.3, w * 0.9, h * 0.5); ctx.stroke();
        },
        rip_tide: (ctx, w, h) => {
            ctx.fillStyle = '#003366'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(100,180,220,0.4)'; ctx.lineWidth = 1.5;
            for (let i = 0; i < 6; i++) {
                ctx.beginPath();
                for (let x = 0; x < w; x++) {
                    const y = h / 2 + Math.sin(x * 0.15 + i * 1.2) * h * 0.3 + Math.sin(x * 0.3) * h * 0.1;
                    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
        },
        hibiscus: (ctx, w, h) => {
            ctx.fillStyle = '#116633'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ee4488';
            const cx = w / 2, cy = h / 2;
            for (let i = 0; i < 5; i++) {
                const a = i * Math.PI * 2 / 5 - Math.PI / 2;
                const px = cx + Math.cos(a) * 10, py = cy + Math.sin(a) * 10;
                ctx.beginPath();
                ctx.ellipse(px, py, 7, 4, a, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.fillStyle = '#ffcc44';
            ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill();
        },

        // === CARTOONS (12) ===
        retro_flower_power: (ctx, w, h) => {
            ctx.fillStyle = '#ffaacc'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(620);
            const colors = ['#ff6699', '#ffcc33', '#66cc66', '#ff9944'];
            for (let i = 0; i < 5; i++) {
                const cx = rng() * w, cy = rng() * h;
                ctx.fillStyle = colors[i % 4];
                for (let p = 0; p < 6; p++) {
                    const a = p * Math.PI / 3;
                    ctx.beginPath();
                    ctx.ellipse(cx + Math.cos(a) * 5, cy + Math.sin(a) * 5, 4, 3, a, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.fillStyle = '#ffee44';
                ctx.beginPath(); ctx.arc(cx, cy, 2.5, 0, Math.PI * 2); ctx.fill();
            }
        },
        prehistoric_spot: (ctx, w, h) => {
            ctx.fillStyle = '#cc8844'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(621);
            ctx.fillStyle = '#553311';
            for (let i = 0; i < 10; i++) {
                const cx = rng() * w, cy = rng() * h;
                ctx.beginPath();
                ctx.ellipse(cx, cy, 3 + rng() * 6, 2 + rng() * 5, rng() * Math.PI, 0, Math.PI * 2);
                ctx.fill();
            }
        },
        toon_stars: (ctx, w, h) => {
            ctx.fillStyle = '#2233aa'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(622);
            ctx.fillStyle = '#ffdd33';
            for (let i = 0; i < 8; i++) {
                const cx = rng() * w, cy = rng() * h, r = 2 + rng() * 5;
                ctx.beginPath();
                for (let p = 0; p < 10; p++) {
                    const a = p * Math.PI / 5 - Math.PI / 2;
                    const pr = p % 2 ? r * 0.4 : r;
                    const method = p === 0 ? 'moveTo' : 'lineTo';
                    ctx[method](cx + Math.cos(a) * pr, cy + Math.sin(a) * pr);
                }
                ctx.closePath(); ctx.fill();
            }
        },
        toon_speed: (ctx, w, h) => {
            ctx.fillStyle = '#ddeeff'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#5588cc'; ctx.lineWidth = 1.5;
            const rng = _seededRng(623);
            for (let i = 0; i < 10; i++) {
                const y = 4 + rng() * (h - 8), x1 = rng() * w * 0.3, x2 = x1 + 10 + rng() * w * 0.5;
                ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
            }
        },
        groovy_swirl: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const dx = px - w / 2, dy = py - h / 2;
                    const angle = Math.atan2(dy, dx) + Math.sqrt(dx * dx + dy * dy) * 0.08;
                    const t = (Math.sin(angle * 3) + 1) / 2;
                    const colors = [[220, 80, 180], [255, 200, 50], [100, 200, 100]];
                    const ci = Math.floor(t * 3) % 3;
                    const idx = (py * w + px) * 4;
                    id.data[idx] = colors[ci][0]; id.data[idx + 1] = colors[ci][1]; id.data[idx + 2] = colors[ci][2]; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        zigzag_stripe: (ctx, w, h) => {
            ctx.fillStyle = '#ee8833'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ffcc44'; ctx.lineWidth = 2;
            for (let y = 4; y < h; y += 8) {
                ctx.beginPath();
                for (let x = 0; x < w; x += 6) {
                    const yy = y + ((x / 6) % 2 ? 3 : -3);
                    x === 0 ? ctx.moveTo(x, yy) : ctx.lineTo(x, yy);
                }
                ctx.stroke();
            }
        },
        toon_cloud: (ctx, w, h) => {
            ctx.fillStyle = '#88ccee'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff';
            const drawCloud = (cx, cy, s) => {
                ctx.beginPath();
                ctx.arc(cx, cy, s * 1.2, 0, Math.PI * 2); ctx.fill();
                ctx.arc(cx - s, cy + s * 0.3, s * 0.8, 0, Math.PI * 2); ctx.fill();
                ctx.arc(cx + s, cy + s * 0.3, s * 0.9, 0, Math.PI * 2); ctx.fill();
            };
            drawCloud(w * 0.3, h * 0.3, 6);
            drawCloud(w * 0.7, h * 0.6, 5);
        },
        retro_atom: (ctx, w, h) => {
            ctx.fillStyle = '#224455'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = '#55bbdd'; ctx.lineWidth = 1;
            for (let i = 0; i < 3; i++) {
                const a = i * Math.PI / 3;
                ctx.beginPath();
                ctx.ellipse(cx, cy, w * 0.4, h * 0.15, a, 0, Math.PI * 2);
                ctx.stroke();
            }
            ctx.fillStyle = '#55ddff';
            ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI * 2); ctx.fill();
        },
        polka_pop: (ctx, w, h) => {
            ctx.fillStyle = '#ee3366'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff';
            const sp = 10;
            for (let y = sp / 2; y < h; y += sp) {
                const off = (Math.floor(y / sp) % 2) * sp / 2;
                for (let x = sp / 2 + off; x < w; x += sp) {
                    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        toon_bones: (ctx, w, h) => {
            ctx.fillStyle = '#222222'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ddddcc'; ctx.lineWidth = 2; ctx.lineCap = 'round';
            // Crossbone
            ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.2); ctx.lineTo(w * 0.8, h * 0.8); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(w * 0.8, h * 0.2); ctx.lineTo(w * 0.2, h * 0.8); ctx.stroke();
            // Bone ends
            const ends = [[w * 0.2, h * 0.2], [w * 0.8, h * 0.2], [w * 0.2, h * 0.8], [w * 0.8, h * 0.8]];
            ends.forEach(([x, y]) => {
                ctx.fillStyle = '#ddddcc';
                ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
            });
        },
        cartoon_plaid: (ctx, w, h) => {
            ctx.fillStyle = '#dd5555'; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.3;
            ctx.fillStyle = '#ffffff';
            for (let x = 0; x < w; x += 10) ctx.fillRect(x, 0, 4, h);
            for (let y = 0; y < h; y += 10) ctx.fillRect(0, y, w, 4);
            ctx.globalAlpha = 0.2;
            ctx.fillStyle = '#000000';
            for (let x = 5; x < w; x += 10) ctx.fillRect(x, 0, 2, h);
            for (let y = 5; y < h; y += 10) ctx.fillRect(0, y, w, 2);
            ctx.globalAlpha = 1;
        },
        toon_lightning: (ctx, w, h) => {
            ctx.fillStyle = '#222244'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffdd22'; ctx.strokeStyle = '#ffee66'; ctx.lineWidth = 2;
            // Jagged bolt
            ctx.beginPath();
            ctx.moveTo(w * 0.4, 0); ctx.lineTo(w * 0.55, h * 0.35);
            ctx.lineTo(w * 0.35, h * 0.4); ctx.lineTo(w * 0.6, h);
            ctx.lineTo(w * 0.5, h * 0.5); ctx.lineTo(w * 0.7, h * 0.45);
            ctx.lineTo(w * 0.4, 0);
            ctx.fill();
        },

        // === COMICS (12) ===
        hero_burst: (ctx, w, h) => {
            ctx.fillStyle = '#0033aa'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            const rays = [0.48, 0.15, 0.42, 0.12, 0.45, 0.18, 0.38, 0.14, 0.5, 0.1, 0.44, 0.2, 0.4, 0.16, 0.46, 0.22];
            ctx.beginPath();
            for (let i = 0; i < 16; i++) {
                const a = (i / 16) * Math.PI * 2 - Math.PI / 2;
                const r = (rays[i % rays.length]) * Math.min(w, h);
                (i === 0 ? ctx.moveTo : ctx.lineTo).call(ctx, cx + Math.cos(a) * r, cy + Math.sin(a) * r);
            }
            ctx.closePath();
            ctx.fillStyle = '#ffcc00'; ctx.fill();
            ctx.strokeStyle = '#cc0000'; ctx.lineWidth = 3; ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        web_pattern: (ctx, w, h) => {
            ctx.fillStyle = '#cc0000'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.5, topY = 0;
            const numSpokes = 10; const numRings = 5;
            ctx.strokeStyle = '#000000'; ctx.lineWidth = 1.5;
            for (let i = 0; i < numSpokes; i++) {
                const a = (i / numSpokes) * Math.PI * 0.85 + Math.PI * 0.075;
                const ex = cx + Math.sin(a) * w * 0.6; const ey = topY + Math.cos(a) * h;
                ctx.beginPath(); ctx.moveTo(cx, topY); ctx.lineTo(ex, ey); ctx.stroke();
            }
            for (let ring = 1; ring <= numRings; ring++) {
                const t = ring / (numRings + 1); const r = Math.min(w, h) * 0.15 * ring;
                ctx.beginPath();
                for (let i = 0; i <= numSpokes; i++) {
                    const a = (i / numSpokes) * Math.PI * 0.85 + Math.PI * 0.075;
                    const dip = Math.sin(i / numSpokes * Math.PI) * r * 0.3;
                    const x = cx + Math.sin(a) * (r + dip); const y = topY + Math.cos(a) * (r * 1.2 + dip);
                    (i === 0 ? ctx.moveTo : ctx.lineTo).call(ctx, x, y);
                }
                ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        dark_knight_scales: (ctx, w, h) => {
            ctx.fillStyle = '#111111'; ctx.fillRect(0, 0, w, h);
            const ss = 7; const r = ss * 0.6;
            for (let row = 0; row < Math.ceil(h / ss) + 2; row++) {
                const off = (row % 2) * (ss / 2);
                for (let col = -1; col < Math.ceil(w / ss) + 2; col++) {
                    const cx = col * ss + off, cy = row * ss;
                    const g = ctx.createLinearGradient(cx, cy - r, cx, cy + r);
                    g.addColorStop(0, '#222222'); g.addColorStop(0.5, '#333333'); g.addColorStop(1, '#2a2a2a');
                    ctx.fillStyle = g; ctx.beginPath();
                    ctx.arc(cx, cy, r, 0, Math.PI); ctx.fill();
                }
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        comic_halftone: (ctx, w, h) => {
            ctx.fillStyle = '#dd6688'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff';
            const sp = 5;
            for (let y = 0; y < h; y += sp) {
                for (let x = 0; x < w; x += sp) {
                    const d = Math.sqrt((x - w) * (x - w) + (y - h) * (y - h)) / (w * 1.4);
                    const r = Math.max(0.3, d * 2.5);
                    ctx.beginPath(); ctx.arc(x, y, Math.min(r, sp * 0.4), 0, Math.PI * 2); ctx.fill();
                }
            }
        },
        pow_burst: (ctx, w, h) => {
            ctx.fillStyle = '#ffee00'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.shadowColor = '#000000'; ctx.shadowBlur = 2;
            ctx.beginPath(); ctx.arc(cx, cy, w * 0.25, 0, Math.PI * 2); ctx.fillStyle = '#ff00aa'; ctx.fill();
            ctx.beginPath(); ctx.moveTo(cx - 8, cy); ctx.lineTo(cx + 12, cy - 10); ctx.lineTo(cx + 6, cy); ctx.lineTo(cx + 14, cy + 8); ctx.closePath(); ctx.fill();
            ctx.beginPath(); ctx.arc(cx + 10, cy - 6, w * 0.12, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = '#000000'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.arc(cx, cy, w * 0.25, 0, Math.PI * 2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(cx - 8, cy); ctx.lineTo(cx + 12, cy - 10); ctx.lineTo(cx + 6, cy); ctx.lineTo(cx + 14, cy + 8); ctx.closePath(); ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        cape_flow: (ctx, w, h) => {
            ctx.fillStyle = '#881133'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(200,50,80,0.5)'; ctx.lineWidth = 2;
            for (let i = 0; i < 8; i++) {
                ctx.beginPath();
                ctx.moveTo(0, i * 6);
                ctx.bezierCurveTo(w * 0.3, i * 6 + 10, w * 0.6, i * 6 - 5, w, i * 6 + 8);
                ctx.stroke();
            }
        },
        power_bolt: (ctx, w, h) => {
            ctx.fillStyle = '#aa0000'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1.5; ctx.globalAlpha = 0.7;
            ctx.beginPath(); ctx.moveTo(w * 0.75, h * 0.15); ctx.lineTo(w * 0.5, h * 0.5); ctx.lineTo(w * 0.8, h * 0.5); ctx.stroke();
            ctx.globalAlpha = 1.0;
            ctx.fillStyle = '#ffcc00'; ctx.strokeStyle = '#ffcc00'; ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(w * 0.2, h * 0.1);
            ctx.lineTo(w * 0.45, h * 0.45);
            ctx.lineTo(w * 0.35, h * 0.45);
            ctx.lineTo(w * 0.6, h * 0.9);
            ctx.lineTo(w * 0.5, h * 0.5);
            ctx.lineTo(w * 0.65, h * 0.5);
            ctx.lineTo(w * 0.2, h * 0.1);
            ctx.fill(); ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        shield_rings: (ctx, w, h) => {
            const cx = w / 2, cy = h / 2;
            const colors = ['#3355cc', '#cc2233', '#ffffff', '#cc2233', '#3355cc'];
            colors.forEach((c, i) => {
                ctx.fillStyle = c;
                ctx.beginPath(); ctx.arc(cx, cy, w * 0.45 - i * 4, 0, Math.PI * 2); ctx.fill();
            });
            // Center star
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            for (let i = 0; i < 10; i++) {
                const a = i * Math.PI / 5 - Math.PI / 2;
                const r = i % 2 ? 3 : 6;
                i === 0 ? ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r) : ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
            }
            ctx.closePath(); ctx.fill();
        },
        comic_panel: (ctx, w, h) => {
            ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#111111'; ctx.lineWidth = 2;
            // Panel borders
            ctx.strokeRect(1, 1, w / 2 - 2, h / 2 - 2);
            ctx.strokeRect(w / 2 + 1, 1, w / 2 - 2, h / 2 - 2);
            ctx.strokeRect(1, h / 2 + 1, w - 2, h / 2 - 2);
            // Inner details
            ctx.fillStyle = '#eee'; ctx.fillRect(3, 3, w / 2 - 6, h / 2 - 6);
            ctx.fillStyle = '#ddd'; ctx.fillRect(w / 2 + 3, 3, w / 2 - 6, h / 2 - 6);
        },
        power_aura: (ctx, w, h) => {
            ctx.fillStyle = '#110033'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            for (let r = w * 0.4; r > 2; r -= 3) {
                const alpha = 0.1 + ((w * 0.4 - r) / (w * 0.4)) * 0.4;
                ctx.strokeStyle = `rgba(136,68,238,${alpha})`;
                ctx.lineWidth = 2;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        villain_stripe: (ctx, w, h) => {
            ctx.fillStyle = '#55ff00'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(666);
            ctx.strokeStyle = '#440066';
            for (let s = 0; s < 12; s++) {
                ctx.lineWidth = rng() > 0.5 ? 2.5 : 1;
                ctx.beginPath();
                let x = rng() * w, y = rng() * h;
                ctx.moveTo(x, y);
                for (let seg = 0; seg < 4; seg++) {
                    x = Math.max(0, Math.min(w, x + (rng() - 0.5) * w * 0.6));
                    y = Math.max(0, Math.min(h, y + (rng() - 0.5) * h * 0.6));
                    ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        // ===== NEON & GLOW PATTERN SWATCHES =====
        aurora_glow: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            for (let y = 0; y < h; y++) {
                const t = y / h;
                const wave = Math.sin(t * Math.PI * 8 + Math.sin(t * 5) * 2) * 0.5 + 0.5;
                const r = Math.floor(20 + (1 - wave) * 100);
                const g = Math.floor(60 + wave * 150);
                const b = Math.floor(40 + (1 - wave) * 120);
                ctx.fillStyle = `rgba(${r},${g},${b},0.6)`;
                ctx.fillRect(0, y, w, 1);
            }
        },
        bioluminescent_wave: (ctx, w, h) => {
            ctx.fillStyle = '#050a14'; ctx.fillRect(0, 0, w, h);
            for (let y = 0; y < h; y++) {
                const t = y / h;
                const wave = Math.sin(t * Math.PI * 6) * 0.5 + 0.5;
                const wave2 = Math.sin(t * Math.PI * 10 - 1.5) * 0.5 + 0.5;
                const glow = (wave * 0.6 + wave2 * 0.4);
                ctx.fillStyle = `rgba(0,${Math.floor(100 + glow * 155)},${Math.floor(80 + glow * 120)},0.5)`;
                ctx.fillRect(0, y, w, 1);
            }
        },
        blacklight_paint: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a2a'; ctx.fillRect(0, 0, w, h);
            // Purple UV wash
            const g = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.6);
            g.addColorStop(0, 'rgba(140,40,255,0.35)'); g.addColorStop(1, 'rgba(80,0,180,0.1)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Hot UV spots
            const rng = _seededRng(700);
            for (let i = 0; i < 15; i++) {
                ctx.fillStyle = `rgba(180,60,255,${0.15 + rng() * 0.2})`;
                ctx.fillRect(rng() * w, rng() * h, 2, 2);
            }
        },
        cyber_punk: (ctx, w, h) => {
            ctx.fillStyle = '#ff007f'; ctx.fillRect(0, 0, w, h);
            const cell = Math.min(w, h) / 6; const rng = _seededRng(790);
            for (let row = 0; row < 6; row++) {
                for (let col = 0; col < 6; col++) {
                    if (rng() < 0.3) continue;
                    ctx.fillStyle = '#ffff00'; ctx.fillRect(col * cell + 1, row * cell + 1, cell - 2, cell - 2);
                }
            }
            ctx.strokeStyle = '#00ffff'; ctx.lineWidth = 1.5;
            let x = 0, y = h * 0.3; ctx.beginPath(); ctx.moveTo(x, y);
            for (let step = 0; step < 8; step++) {
                if (rng() > 0.5) { x += cell; } else { y += (rng() > 0.5 ? 1 : -1) * cell; }
                x = Math.max(0, Math.min(w, x)); y = Math.max(0, Math.min(h, y)); ctx.lineTo(x, y);
            }
            ctx.stroke(); x = w * 0.2; y = h * 0.7; ctx.beginPath(); ctx.moveTo(x, y);
            for (let step = 0; step < 6; step++) {
                if (rng() > 0.5) { x += cell * 0.8; } else { y += (rng() > 0.5 ? 1 : -1) * cell * 0.8; }
                x = Math.max(0, Math.min(w, x)); y = Math.max(0, Math.min(h, y)); ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent'; ctx.globalAlpha = 1.0;
        },
        electric_arc: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a18'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(710);
            // Draw jagged lightning bolts
            for (let bolt = 0; bolt < 3; bolt++) {
                let py = Math.floor(rng() * h), px = 0;
                ctx.beginPath(); ctx.moveTo(px, py);
                for (let s = 0; s < 20; s++) {
                    px += Math.floor(w / 18);
                    py += Math.floor((rng() - 0.5) * h * 0.3);
                    py = Math.max(0, Math.min(h - 1, py));
                    ctx.lineTo(px, py);
                }
                // Glow aura
                ctx.strokeStyle = 'rgba(80,160,255,0.15)'; ctx.lineWidth = 6; ctx.stroke();
                // Core bolt
                ctx.strokeStyle = 'rgba(120,200,255,0.6)'; ctx.lineWidth = 2; ctx.stroke();
            }
        },
        firefly: (ctx, w, h) => {
            ctx.fillStyle = '#0a0f08'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(780);
            for (let i = 0; i < 18; i++) {
                const x = rng() * w, y = rng() * h;
                const r = 3 + rng() * 5;
                const g2 = ctx.createRadialGradient(x, y, 0, x, y, r);
                g2.addColorStop(0, `rgba(200,230,60,${0.4 + rng() * 0.3})`);
                g2.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h);
            }
        },
        fluorescent: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a20'; ctx.fillRect(0, 0, w, h);
            // Greenish-white tube bands
            for (let y = 0; y < h; y++) {
                const band = Math.sin(y * Math.PI / 4) * 0.5 + 0.5;
                const v = Math.floor(140 + band * 80);
                ctx.fillStyle = `rgba(${v - 30},${v},${v - 40},0.5)`;
                ctx.fillRect(0, y, w, 1);
            }
        },
        glow_stick: (ctx, w, h) => {
            ctx.fillStyle = '#0a1a0a'; ctx.fillRect(0, 0, w, h);
            // Bright green edge contour + interior pulse
            ctx.strokeStyle = 'rgba(0,255,50,0.5)'; ctx.lineWidth = 3;
            ctx.strokeRect(3, 3, w - 6, h - 6);
            ctx.strokeStyle = 'rgba(0,200,30,0.12)'; ctx.lineWidth = 8;
            ctx.strokeRect(1, 1, w - 2, h - 2);
            // Green glow fill
            const g = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.5);
            g.addColorStop(0, 'rgba(0,200,30,0.25)'); g.addColorStop(1, 'rgba(0,60,10,0.05)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        laser_grid: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            // Green horizontal + vertical grid lines
            const spacing = Math.max(3, Math.floor(w / 8));
            ctx.strokeStyle = 'rgba(0,220,0,0.5)'; ctx.lineWidth = 1;
            for (let x = spacing; x < w; x += spacing) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
            }
            for (let y = spacing; y < h; y += spacing) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }
            // Bright intersections
            for (let x = spacing; x < w; x += spacing) {
                for (let y = spacing; y < h; y += spacing) {
                    ctx.fillStyle = 'rgba(0,255,0,0.4)'; ctx.fillRect(x - 1, y - 1, 3, 3);
                }
            }
        },
        laser_show: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a14'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            const rng = _seededRng(730);
            for (let i = 0; i < 6; i++) {
                const angle = rng() * Math.PI;
                const endX = cx + Math.cos(angle) * w;
                const endY = cy + Math.sin(angle) * h;
                ctx.beginPath(); ctx.moveTo(cx - Math.cos(angle) * w, cy - Math.sin(angle) * h);
                ctx.lineTo(endX, endY);
                ctx.strokeStyle = 'rgba(200,80,255,0.12)'; ctx.lineWidth = 5; ctx.stroke();
                ctx.strokeStyle = `rgba(${150 + rng() * 100},${80 + rng() * 100},${200 + rng() * 55},0.5)`; ctx.lineWidth = 1.5; ctx.stroke();
            }
        },
        led_matrix: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const dot = Math.max(2, Math.floor(w / 10));
            const rng = _seededRng(800);
            for (let y = dot; y < h; y += dot) {
                for (let x = dot; x < w; x += dot) {
                    const c = Math.floor(rng() * 3);
                    const r = c === 0 ? 200 : c === 1 ? 60 : 60;
                    const g = c === 0 ? 60 : c === 1 ? 200 : 100;
                    const b = c === 0 ? 60 : c === 1 ? 100 : 200;
                    const g2 = ctx.createRadialGradient(x, y, 0, x, y, dot * 0.35);
                    g2.addColorStop(0, `rgba(${r},${g},${b},0.6)`); g2.addColorStop(1, 'rgba(0,0,0,0)');
                    ctx.fillStyle = g2; ctx.fillRect(x - dot / 2, y - dot / 2, dot, dot);
                }
            }
        },
        magnesium_burn: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            // Large centered white bloom
            const g = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.55);
            g.addColorStop(0, 'rgba(255,255,255,0.7)');
            g.addColorStop(0.3, 'rgba(255,250,240,0.4)');
            g.addColorStop(0.7, 'rgba(200,200,220,0.1)');
            g.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        neon_sign: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a18'; ctx.fillRect(0, 0, w, h);
            // Hot pink edge contour glow
            ctx.strokeStyle = 'rgba(255,40,120,0.5)'; ctx.lineWidth = 3;
            ctx.strokeRect(4, 4, w - 8, h - 8);
            ctx.strokeStyle = 'rgba(255,30,100,0.12)'; ctx.lineWidth = 8;
            ctx.strokeRect(2, 2, w - 4, h - 4);
            // Interior pink glow
            const g = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.4);
            g.addColorStop(0, 'rgba(255,40,120,0.15)'); g.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        neon_vegas: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            // Vertical neon color strips
            const stripW = Math.max(2, Math.floor(w / 8));
            const colors = ['#ff1a55', '#00ff44', '#ffee00', '#0088ff', '#cc00ff', '#ff8800'];
            for (let x = 0; x < w; x += stripW) {
                const c = colors[Math.floor(x / stripW) % colors.length];
                ctx.fillStyle = c + '88'; ctx.fillRect(x, 0, stripW - 1, h);
            }
        },
        phosphorescent: (ctx, w, h) => {
            // Dark bg with green glow brighter at edges (shadow-reactive)
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#2a4a2a'); g.addColorStop(0.3, '#0a1a0a');
            g.addColorStop(0.7, '#0a1a0a'); g.addColorStop(1, '#2a4a2a');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Edge glow (brighter in dark)
            ctx.strokeStyle = 'rgba(50,200,80,0.3)'; ctx.lineWidth = 5;
            ctx.strokeRect(2, 2, w - 4, h - 4);
        },
        plasma_globe: (ctx, w, h) => {
            ctx.fillStyle = '#0a0518'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            // Radial tendrils
            for (let i = 0; i < 8; i++) {
                const angle = (i / 8) * Math.PI * 2;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(angle) * w * 0.55, cy + Math.sin(angle) * h * 0.55);
                ctx.strokeStyle = 'rgba(140,40,255,0.12)'; ctx.lineWidth = 6; ctx.stroke();
                ctx.strokeStyle = 'rgba(180,60,255,0.4)'; ctx.lineWidth = 1.5; ctx.stroke();
            }
            // Center glow
            const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 5);
            g.addColorStop(0, 'rgba(220,140,255,0.6)'); g.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        rave: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(750);
            const colors = ['#ff0080', '#00ff00', '#0088ff', '#ffff00', '#cc00ff', '#ff4400', '#00ffff', '#ff00ff'];
            const bs = Math.max(2, Math.floor(w / 12));
            for (let i = 0; i < 40; i++) {
                const x = Math.floor(rng() * (w - bs));
                const y = Math.floor(rng() * (h - bs));
                ctx.fillStyle = colors[Math.floor(rng() * colors.length)] + 'aa';
                ctx.fillRect(x, y, bs, bs);
            }
        },
        scorched: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(810);
            const noise = _simpleNoise2D(w, h, [4, 8, 16], [0.3, 0.4, 0.3], rng);
            for (let i = 0; i < w * h; i++) {
                const burn = Math.max(0, Math.min(1, (noise[i] + 0.3) * 1.2));
                const r = Math.floor(60 + burn * 80); const g = Math.floor(30 + burn * 40); const b = Math.floor(10 + burn * 20);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        sodium_lamp: (ctx, w, h) => {
            // Flat amber monochromatic wash
            const g = ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, '#cc8800'); g.addColorStop(0.5, '#aa6600'); g.addColorStop(1, '#bb7700');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        static: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(820);
            for (let i = 0; i < w * h; i++) {
                const v = Math.floor(rng() * 200);
                id.data[i * 4] = v; id.data[i * 4 + 1] = v; id.data[i * 4 + 2] = v; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        },
        tesla_coil: (ctx, w, h) => {
            ctx.fillStyle = '#08081a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(760);
            // Dense branching arcs from all edges
            for (let bolt = 0; bolt < 5; bolt++) {
                const edge = bolt % 4;
                let py, px;
                if (edge === 0) { py = 0; px = Math.floor(rng() * w); }
                else if (edge === 1) { py = h - 1; px = Math.floor(rng() * w); }
                else if (edge === 2) { py = Math.floor(rng() * h); px = 0; }
                else { py = Math.floor(rng() * h); px = w - 1; }
                ctx.beginPath(); ctx.moveTo(px, py);
                for (let s = 0; s < 15; s++) {
                    px += Math.floor((rng() - 0.5) * w * 0.15 + (w / 2 - px) * 0.08);
                    py += Math.floor((rng() - 0.5) * h * 0.15 + (h / 2 - py) * 0.08);
                    ctx.lineTo(Math.max(0, Math.min(w, px)), Math.max(0, Math.min(h, py)));
                }
                ctx.strokeStyle = 'rgba(60,40,200,0.1)'; ctx.lineWidth = 5; ctx.stroke();
                ctx.strokeStyle = 'rgba(100,60,255,0.45)'; ctx.lineWidth = 1.5; ctx.stroke();
            }
        },
        tracer_round: (ctx, w, h) => {
            ctx.fillStyle = '#1a1208'; ctx.fillRect(0, 0, w, h);
            // Diagonal orange streak lines
            ctx.strokeStyle = 'rgba(255,160,20,0.12)'; ctx.lineWidth = 5;
            for (let i = -2; i < 6; i++) {
                ctx.beginPath();
                ctx.moveTo(i * w / 4, 0); ctx.lineTo(i * w / 4 + w * 0.6, h);
                ctx.stroke();
            }
            ctx.strokeStyle = 'rgba(255,180,40,0.4)'; ctx.lineWidth = 1.5;
            for (let i = -2; i < 6; i++) {
                ctx.beginPath();
                ctx.moveTo(i * w / 4, 0); ctx.lineTo(i * w / 4 + w * 0.6, h);
                ctx.stroke();
            }
        },
        welding_arc: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            // Intense blue-white point blooms
            const rng = _seededRng(770);
            for (let i = 0; i < 3; i++) {
                const x = w * 0.2 + rng() * w * 0.6;
                const y = h * 0.2 + rng() * h * 0.6;
                const g = ctx.createRadialGradient(x, y, 0, x, y, w * 0.25);
                g.addColorStop(0, 'rgba(200,210,255,0.6)');
                g.addColorStop(0.3, 'rgba(120,140,255,0.2)');
                g.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            }
            // Sparks
            for (let i = 0; i < 15; i++) {
                ctx.fillStyle = 'rgba(255,255,255,0.4)';
                ctx.fillRect(rng() * w, rng() * h, 1, 1);
            }
        },
        gamma_pulse: (ctx, w, h) => {
            ctx.fillStyle = '#001a00'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            for (let r = 2; r < w * 0.5; r += 3) {
                const alpha = 0.6 - r / (w * 0.5) * 0.5;
                ctx.strokeStyle = `rgba(51,238,68,${Math.max(0, alpha)})`;
                ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },

        // === EXPANSION PATTERNS (Decades, Flames, Music, Astro, Hero, Sport) ===
        decade_50s_starburst: (ctx, w, h) => {
            const cx = w * 0.5, cy = h * 0.5; ctx.fillStyle = '#ffcc00'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#cc3300'; const rays = 16;
            for (let i = 0; i < rays; i++) {
                const a1 = (i / rays) * Math.PI * 2, a2 = ((i + 0.4) / rays) * Math.PI * 2;
                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, Math.max(w, h), a1, a2); ctx.closePath(); ctx.fill();
            }
        },
        decade_50s_bullet: (ctx, w, h) => {
            ctx.fillStyle = '#111122'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ccaa00';
            for (let i = 0; i < 9; i++) {
                const y = h * (i + 0.5) / 9;
                ctx.fillRect(0, y - 1.5, w, 3);
            }
            const grd = ctx.createRadialGradient(w * 0.22, h * 0.5, 2, w * 0.22, h * 0.5, h * 0.32);
            grd.addColorStop(0, '#ffffff'); grd.addColorStop(1, 'rgba(220,200,100,0)');
            ctx.fillStyle = grd;
            ctx.beginPath();
            ctx.ellipse(w * 0.22, h * 0.5, w * 0.14, h * 0.3, 0, 0, Math.PI * 2);
            ctx.fill();
        },
        decade_50s_tailfin: (ctx, w, h) => {
            ctx.fillStyle = '#22aacc'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#f5e8c0'; ctx.beginPath(); ctx.moveTo(w * 0.2, h); ctx.bezierCurveTo(w * 0.3, h * 0.3, w * 0.7, h * 0.2, w * 0.9, h * 0.6); ctx.lineTo(w * 0.7, h); ctx.closePath(); ctx.fill();
        },
        decade_50s_boomerang: (ctx, w, h) => {
            ctx.fillStyle = '#ee4488'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.7); ctx.quadraticCurveTo(w * 0.5, h * 0.2, w * 0.8, h * 0.7); ctx.quadraticCurveTo(w * 0.5, h * 0.5, w * 0.2, h * 0.7); ctx.stroke();
        },
        decade_50s_diner_curve: (ctx, w, h) => {
            ctx.fillStyle = '#f0e8d8'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ee5577'; ctx.beginPath(); ctx.moveTo(0, h * 0.5); ctx.quadraticCurveTo(w * 0.5, h * 0.2, w, h * 0.5); ctx.quadraticCurveTo(w * 0.5, h * 0.8, 0, h * 0.5); ctx.fill();
        },
        decade_50s_scallop: (ctx, w, h) => {
            ctx.fillStyle = '#0d7a7a'; ctx.fillRect(0, 0, w, h);
            const r = w / 6;
            ctx.fillStyle = '#f0e0c0';
            for (let row = -1; row < Math.ceil(h / r) + 1; row++) {
                for (let col = -1; col < Math.ceil(w / r) + 1; col++) {
                    const ox = (row % 2 === 0) ? 0 : r;
                    const cx = col * r * 2 + ox;
                    const cy = row * r;
                    ctx.beginPath();
                    ctx.arc(cx, cy, r * 0.95, 0, Math.PI);
                    ctx.closePath();
                    ctx.fill();
                }
            }
        },
        decade_50s_rocket: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#334466'; ctx.lineWidth = 1;
            for (let i = 0; i < 8; i++) {
                const y = h * (i + 0.5) / 8;
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w * 0.55, y); ctx.stroke();
            }
            ctx.fillStyle = '#ddaa00';
            ctx.beginPath();
            ctx.ellipse(w * 0.55, h * 0.5, w * 0.28, h * 0.18, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#cc2200';
            ctx.beginPath();
            ctx.moveTo(w * 0.83, h * 0.5);
            ctx.lineTo(w * 0.65, h * 0.34); ctx.lineTo(w * 0.65, h * 0.66);
            ctx.closePath(); ctx.fill();
            ctx.fillStyle = '#cc2200';
            ctx.beginPath();
            ctx.moveTo(w * 0.27, h * 0.5);
            ctx.lineTo(w * 0.15, h * 0.22); ctx.lineTo(w * 0.27, h * 0.36);
            ctx.closePath(); ctx.fill();
            ctx.beginPath();
            ctx.moveTo(w * 0.27, h * 0.5);
            ctx.lineTo(w * 0.15, h * 0.78); ctx.lineTo(w * 0.27, h * 0.64);
            ctx.closePath(); ctx.fill();
        },
        decade_50s_classic_stripe: (ctx, w, h) => {
            ctx.fillStyle = '#f0e8d8'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#cc2200'; ctx.fillRect(0, h * 0.35, w, h * 0.3);
        },
        decade_50s_diamond: (ctx, w, h) => {
            ctx.fillStyle = '#8b1a1a'; ctx.fillRect(0, 0, w, h);
            const dw = w / 4, dh = h / 3;
            const drawDiamond = (cx, cy, rw, rh, color) => {
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.moveTo(cx, cy - rh); ctx.lineTo(cx + rw, cy);
                ctx.lineTo(cx, cy + rh); ctx.lineTo(cx - rw, cy);
                ctx.closePath(); ctx.fill();
            };
            for (let row = -1; row < 5; row++) {
                for (let col = -1; col < 6; col++) {
                    const ox = (row % 2 === 0) ? 0 : dw;
                    drawDiamond(col * dw * 2 + ox, row * dh, dw * 0.9, dh * 0.85,
                        row % 2 === 0 ? '#f0e0b0' : '#cc9900');
                }
            }
            ctx.strokeStyle = '#ccaa00'; ctx.lineWidth = 0.5;
            for (let i = -2; i < 8; i++) {
                ctx.beginPath(); ctx.moveTo(i * dw, 0); ctx.lineTo(i * dw + h, h); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(i * dw, 0); ctx.lineTo(i * dw - h, h); ctx.stroke();
            }
        },
        decade_50s_chrome_line: (ctx, w, h) => {
            ctx.fillStyle = '#8899aa'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ddeeff'; ctx.fillRect(0, h * 0.35, w, 2); ctx.fillRect(0, h * 0.62, w, 2);
        },
        decade_60s_flower: (ctx, w, h) => {
            ctx.fillStyle = '#ff7722'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2; ctx.fillStyle = '#ffee22'; ctx.beginPath(); ctx.arc(cx, cy, w * 0.12, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#ff66aa'; for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2; ctx.beginPath(); ctx.ellipse(cx + Math.cos(a) * w * 0.25, cy + Math.sin(a) * h * 0.2, w * 0.1, h * 0.12, a, 0, Math.PI * 2); ctx.fill(); }
        },
        decade_60s_peace_curve: (ctx, w, h) => {
            ctx.fillStyle = '#88cc00'; ctx.fillRect(0, 0, w, h);
            const drawPeace = (cx, cy, r) => {
                ctx.strokeStyle = '#ffffff'; ctx.lineWidth = r * 0.18;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(cx, cy - r); ctx.lineTo(cx, cy + r); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx - r * Math.sin(Math.PI / 3), cy + r * Math.cos(Math.PI / 3)); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + r * Math.sin(Math.PI / 3), cy + r * Math.cos(Math.PI / 3)); ctx.stroke();
            };
            const cols = 3, rows = 2;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    drawPeace(w * (c + 0.5) / cols, h * (r + 0.5) / rows, Math.min(w / cols, h / rows) * 0.4);
                }
            }
        },
        decade_60s_mod_stripe: (ctx, w, h) => {
            for (let i = 0; i < 5; i++) { ctx.fillStyle = (i % 2) ? '#ffffff' : '#000000'; ctx.fillRect(0, i * (h / 5), w, h / 5 + 1); }
        },
        decade_60s_opart_ray: (ctx, w, h) => {
            const cx = w * 0.5, cy = h * 0.5;
            const maxR = Math.sqrt(cx * cx + cy * cy);
            for (let i = 0; i < 28; i++) {
                ctx.fillStyle = i % 2 === 0 ? '#000000' : '#ffffff';
                ctx.beginPath();
                ctx.arc(cx, cy, maxR * (1 - i / 28), 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.strokeStyle = 'rgba(0,0,0,0.25)'; ctx.lineWidth = 0.5;
            for (let i = 0; i < 36; i++) {
                const a = (i / 36) * Math.PI * 2;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(a) * maxR, cy + Math.sin(a) * maxR); ctx.stroke();
            }
        },
        decade_60s_gogo_check: (ctx, w, h) => {
            const sq = Math.min(w, h) / 5;
            for (let r = 0; r < Math.ceil(h / sq) + 1; r++) {
                for (let c = 0; c < Math.ceil(w / sq) + 1; c++) {
                    ctx.fillStyle = (r + c) % 2 === 0 ? '#000000' : '#ffffff';
                    ctx.fillRect(c * sq, r * sq, sq, sq);
                }
            }
            ctx.strokeStyle = 'rgba(255,255,255,0.45)'; ctx.lineWidth = 3;
            for (let i = -2; i < 8; i++) {
                ctx.beginPath(); ctx.moveTo(i * sq * 2, 0); ctx.lineTo(i * sq * 2 + h, h); ctx.stroke();
            }
            ctx.strokeStyle = 'rgba(0,0,0,0.25)';
            for (let i = -2; i < 8; i++) {
                ctx.beginPath(); ctx.moveTo(i * sq * 2 + h, 0); ctx.lineTo(i * sq * 2, h); ctx.stroke();
            }
        },
        decade_60s_lavalamp: (ctx, w, h) => {
            ctx.fillStyle = '#220033'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ff6600'; ctx.beginPath(); ctx.ellipse(w * 0.25, h * 0.4, w * 0.15, h * 0.2, 0.2, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#ffcc00'; ctx.beginPath(); ctx.ellipse(w * 0.6, h * 0.6, w * 0.12, h * 0.18, -0.1, 0, Math.PI * 2); ctx.fill();
        },
        decade_60s_swirl: (ctx, w, h) => {
            const cx = w * 0.5, cy = h * 0.5;
            const colors = ['#cc00cc', '#ffee00', '#ff6600', '#cc00cc', '#ffee00'];
            const arms = 6;
            for (let i = 0; i < 360; i++) {
                const a = i * Math.PI / 180;
                const r1 = i * 0.28;
                const r2 = r1 + 18;
                const ci = Math.floor((i / 60) % colors.length);
                ctx.fillStyle = colors[ci];
                ctx.beginPath();
                ctx.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
                ctx.lineTo(cx + Math.cos(a + 0.12) * r2, cy + Math.sin(a + 0.12) * r2);
                ctx.lineTo(cx + Math.cos(a + 0.06) * r2, cy + Math.sin(a + 0.06) * r2);
                ctx.fill();
            }
        },
        decade_60s_wide_stripe: (ctx, w, h) => {
            const colors = ['#cc0000', '#ffffff', '#0000cc', '#ffcc00', '#ffffff', '#cc0000'];
            const ratios = [0.18, 0.08, 0.28, 0.12, 0.08, 0.26];
            let y = 0;
            colors.forEach((c, i) => {
                ctx.fillStyle = c;
                const bh = h * ratios[i];
                ctx.fillRect(0, y, w, bh);
                y += bh;
            });
        },
        decade_60s_thin_stripe: (ctx, w, h) => {
            for (let i = 0; i < 12; i++) { ctx.fillStyle = (i % 2) ? '#333333' : '#f0f0f0'; ctx.fillRect(0, i * (h / 12), w, h / 12 + 1); }
        },
        decade_60s_woodstock: (ctx, w, h) => {
            ctx.fillStyle = '#f5e642'; ctx.fillRect(0, 0, w, h);
            const drawBird = (x, y, s) => {
                ctx.fillStyle = '#f59200';
                ctx.beginPath(); ctx.ellipse(x, y, s * 0.55, s * 0.4, 0, 0, Math.PI * 2); ctx.fill();
                ctx.beginPath(); ctx.arc(x + s * 0.45, y - s * 0.28, s * 0.28, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#e05000';
                ctx.beginPath();
                ctx.moveTo(x + s * 0.73, y - s * 0.28);
                ctx.lineTo(x + s * 1.05, y - s * 0.18);
                ctx.lineTo(x + s * 0.73, y - s * 0.12);
                ctx.closePath(); ctx.fill();
                ctx.fillStyle = '#000000';
                ctx.beginPath(); ctx.arc(x + s * 0.52, y - s * 0.34, s * 0.07, 0, Math.PI * 2); ctx.fill();
                ctx.strokeStyle = '#cc6600'; ctx.lineWidth = s * 0.08;
                ctx.beginPath(); ctx.moveTo(x + s * 0.38, y - s * 0.53); ctx.lineTo(x + s * 0.45, y - s * 0.42); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(x + s * 0.48, y - s * 0.56); ctx.lineTo(x + s * 0.52, y - s * 0.44); ctx.stroke();
            };
            const cols = 4, rows = 3;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const bx = w * (c + 0.5) / cols;
                    const by = h * (r + 0.5) / rows;
                    const sz = Math.min(w / cols, h / rows) * 0.38;
                    drawBird(bx - sz * 0.2, by + sz * 0.1, sz);
                }
            }
        },
        decade_70s_disco: (ctx, w, h) => {
            ctx.fillStyle = '#111118'; ctx.fillRect(0, 0, w, h);
            const cell = Math.min(w, h) / 6; for (let row = 0; row < 6; row++) for (let col = 0; col < 6; col++) { ctx.fillStyle = '#aabbcc'; ctx.fillRect(col * cell, row * cell, cell - 1, cell - 1); ctx.fillStyle = '#ffffff'; ctx.fillRect(col * cell, row * cell, 3, 3); }
        },
        decade_70s_sparkle: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const drawSparkle = (cx, cy, r) => {
                ctx.fillStyle = '#ffdd88';
                ctx.shadowBlur = 4; ctx.shadowColor = '#ffffaa';
                for (let i = 0; i < 4; i++) {
                    const a = (i / 4) * Math.PI * 2;
                    ctx.beginPath();
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(cx + Math.cos(a) * r * 0.35, cy + Math.sin(a) * r * 0.35);
                    ctx.lineTo(cx + Math.cos(a + Math.PI / 4) * r * 0.12, cy + Math.sin(a + Math.PI / 4) * r * 0.12);
                    ctx.lineTo(cx + Math.cos(a + Math.PI / 2) * r, cy + Math.sin(a + Math.PI / 2) * r);
                    ctx.lineTo(cx + Math.cos(a + Math.PI * 3 / 4) * r * 0.12, cy + Math.sin(a + Math.PI * 3 / 4) * r * 0.12);
                    ctx.closePath(); ctx.fill();
                }
                ctx.shadowBlur = 0;
            };
            const cols = 5, rows = 4;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const jx = ((r * 7 + c * 13) % 7 - 3) / 3 * w / cols * 0.3;
                    const jy = ((r * 11 + c * 5) % 7 - 3) / 3 * h / rows * 0.3;
                    drawSparkle(w * (c + 0.5) / cols + jx, h * (r + 0.5) / rows + jy, Math.min(w / cols, h / rows) * 0.3);
                }
            }
        },
        decade_70s_funk_zigzag: (ctx, w, h) => {
            ctx.fillStyle = '#7a3b00'; ctx.fillRect(0, 0, w, h);
            const colors = ['#cc5500', '#e8a000', '#6b8e23'];
            const teeth = 6, toothH = h / 4;
            colors.forEach((color, ci) => {
                const offsetY = ci * (h / 3);
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.moveTo(0, offsetY + toothH);
                for (let i = 0; i <= teeth; i++) {
                    const x = (i / teeth) * w;
                    const peak = i % 2 === 0 ? offsetY : offsetY + toothH * 2;
                    ctx.lineTo(x, peak);
                }
                ctx.lineTo(w, offsetY + toothH * 3);
                ctx.lineTo(0, offsetY + toothH * 3);
                ctx.closePath();
                ctx.fill();
            });
        },
        decade_70s_bell_flare: (ctx, w, h) => {
            ctx.fillStyle = '#664422'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#cc9900'; ctx.beginPath(); ctx.moveTo(w * 0.5, 0); ctx.quadraticCurveTo(w * 0.2, h * 0.4, w * 0.35, h); ctx.lineTo(w * 0.65, h); ctx.quadraticCurveTo(w * 0.8, h * 0.4, w * 0.5, 0); ctx.fill();
        },
        decade_70s_shag: (ctx, w, h) => {
            ctx.fillStyle = '#7a5535'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(71); ctx.strokeStyle = '#5a4030'; ctx.lineWidth = 1; for (let i = 0; i < 80; i++) { const x = rng() * w, y = rng() * h; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 8, y + 6); ctx.stroke(); }
        },
        decade_70s_bicentennial: (ctx, w, h) => {
            const stripeH = h * 0.6 / 7;
            const stripeColors = ['#cc0000', '#ffffff', '#cc0000', '#ffffff', '#cc0000', '#ffffff', '#cc0000'];
            stripeColors.forEach((c, i) => {
                ctx.fillStyle = c; ctx.fillRect(0, i * stripeH, w, stripeH);
            });
            ctx.fillStyle = '#002868';
            ctx.fillRect(0, h * 0.6, w * 0.45, h * 0.4);
            ctx.fillStyle = '#ffffff';
            const drawStar = (cx, cy, r) => {
                ctx.beginPath();
                for (let i = 0; i < 5; i++) {
                    const a = (i * 4 * Math.PI / 5) - Math.PI / 2;
                    const ai = ((i * 4 + 2) * Math.PI / 5) - Math.PI / 2;
                    if (i === 0) ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                    else ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                    ctx.lineTo(cx + Math.cos(ai) * r * 0.4, cy + Math.sin(ai) * r * 0.4);
                }
                ctx.closePath(); ctx.fill();
            };
            for (let r = 0; r < 3; r++) {
                for (let c = 0; c < 5; c++) {
                    drawStar(w * 0.45 * (c + 0.5) / 5, h * 0.6 + h * 0.4 * (r + 0.5) / 3, h * 0.055);
                }
            }
            ctx.fillStyle = '#cc0000'; ctx.fillRect(w * 0.45, h * 0.6, w * 0.183, h * 0.4);
            ctx.fillStyle = '#ffffff'; ctx.fillRect(w * 0.633, h * 0.6, w * 0.183, h * 0.4);
            ctx.fillStyle = '#002868'; ctx.fillRect(w * 0.817, h * 0.6, w * 0.183, h * 0.4);
        },
        decade_70s_patchwork: (ctx, w, h) => {
            const colors = ['#cc5500', '#8b4513', '#c8860a', '#6b8e23', '#8b6914', '#a0522d', '#cd853f'];
            const pw = w / 4, ph = h / 3;
            let ci = 0;
            for (let r = 0; r < 3; r++) {
                for (let c = 0; c < 4; c++) {
                    ctx.fillStyle = colors[ci % colors.length];
                    ctx.fillRect(c * pw + 2, r * ph + 2, pw - 4, ph - 4);
                    ctx.strokeStyle = '#ffe4b5'; ctx.lineWidth = 1.5;
                    ctx.strokeRect(c * pw + 5, r * ph + 5, pw - 10, ph - 10);
                    ci++;
                }
            }
            ctx.strokeStyle = '#3b1d08'; ctx.lineWidth = 3;
            for (let i = 1; i < 4; i++) ctx.strokeRect(0, 0, w, h), ctx.beginPath(), ctx.moveTo(i * pw, 0), ctx.lineTo(i * pw, h), ctx.stroke();
            for (let i = 1; i < 3; i++) { ctx.beginPath(); ctx.moveTo(0, i * ph); ctx.lineTo(w, i * ph); ctx.stroke(); }
        },
        decade_70s_earth_geo: (ctx, w, h) => {
            ctx.fillStyle = '#5c3310'; ctx.fillRect(0, 0, w, h);
            const earthColors = ['#8b5e3c', '#c8860a', '#6b4e2e', '#cd853f', '#a0522d'];
            ctx.save();
            for (let i = 0; i < 12; i++) {
                const cx = (Math.sin(i * 2.3) * 0.5 + 0.5) * w;
                const cy = (Math.cos(i * 1.9) * 0.5 + 0.5) * h;
                const s = Math.min(w, h) * (0.12 + (i % 3) * 0.06);
                ctx.fillStyle = earthColors[i % earthColors.length];
                ctx.save();
                ctx.translate(cx, cy); ctx.rotate(Math.PI / 4);
                ctx.globalAlpha = 0.75;
                ctx.fillRect(-s / 2, -s / 2, s, s);
                ctx.restore();
            }
            ctx.restore(); ctx.globalAlpha = 1;
        },
        decade_70s_orange_curve: (ctx, w, h) => {
            ctx.fillStyle = '#c15000'; ctx.fillRect(0, 0, w, h);
            const curveSets = [
                { color: '#e8a000', y: h * 0.3 },
                { color: '#8b3a00', y: h * 0.6 },
                { color: '#ffcc44', y: h * 0.75 },
            ];
            curveSets.forEach(({ color, y }) => {
                ctx.strokeStyle = color; ctx.lineWidth = h * 0.14;
                ctx.lineCap = 'butt';
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.bezierCurveTo(w * 0.25, y - h * 0.22, w * 0.75, y + h * 0.22, w, y);
                ctx.stroke();
            });
        },
        decade_70s_studio54: (ctx, w, h) => {
            ctx.fillStyle = '#05050f'; ctx.fillRect(0, 0, w, h);
            const spots = [w * 0.2, w * 0.5, w * 0.8];
            spots.forEach(sx => {
                const grd = ctx.createRadialGradient(sx, 0, 0, sx, 0, h * 1.1);
                grd.addColorStop(0, 'rgba(255,220,100,0.55)');
                grd.addColorStop(0.4, 'rgba(255,180,50,0.15)');
                grd.addColorStop(1, 'rgba(255,100,0,0)');
                ctx.fillStyle = grd;
                ctx.beginPath();
                ctx.moveTo(sx, 0);
                ctx.lineTo(sx - w * 0.18, h); ctx.lineTo(sx + w * 0.18, h);
                ctx.closePath(); ctx.fill();
            });
            for (let i = 0; i < 5; i++) {
                const y = h * (0.7 + i * 0.07);
                const g2 = ctx.createLinearGradient(0, y, w, y);
                g2.addColorStop(0, 'rgba(255,200,50,0)');
                g2.addColorStop(0.5, 'rgba(255,200,50,0.3)');
                g2.addColorStop(1, 'rgba(255,200,50,0)');
                ctx.fillStyle = g2; ctx.fillRect(0, y, w, 2);
            }
        },
        decade_80s_neon_hex: (ctx, w, h) => {
            ctx.fillStyle = '#0a0015'; ctx.fillRect(0, 0, w, h);
            const s = Math.min(w, h) / 6;
            const hexH = s * Math.sqrt(3);
            ctx.strokeStyle = '#ff00ff'; ctx.lineWidth = 1;
            ctx.shadowBlur = 4; ctx.shadowColor = '#ff00ff';
            const drawHex = (cx, cy) => {
                ctx.beginPath();
                for (let i = 0; i < 6; i++) {
                    const a = (i / 6) * Math.PI * 2 - Math.PI / 6;
                    if (i === 0) ctx.moveTo(cx + Math.cos(a) * s, cy + Math.sin(a) * s);
                    else ctx.lineTo(cx + Math.cos(a) * s, cy + Math.sin(a) * s);
                }
                ctx.closePath(); ctx.stroke();
            };
            for (let row = -1; row < Math.ceil(h / hexH) + 2; row++) {
                for (let col = -1; col < Math.ceil(w / (s * 1.5)) + 2; col++) {
                    const ox = (row % 2) * s * 0.75;
                    drawHex(col * s * 1.5 + ox, row * hexH * 0.5);
                }
            }
            ctx.shadowBlur = 0;
        },
        decade_80s_outrun: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#440066'); g.addColorStop(0.6, '#880088'); g.addColorStop(1, '#220022'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const vx = w / 2, vy = 0; ctx.strokeStyle = '#00ffee'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, h); ctx.lineTo(vx, vy); ctx.moveTo(w, h); ctx.lineTo(vx, vy); ctx.stroke(); for (let y = h * 0.4; y < h; y += 10) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        decade_80s_memphis: (ctx, w, h) => {
            ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#00cccc'; ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.2); ctx.lineTo(w * 0.5, h * 0.5); ctx.lineTo(w * 0.2, h * 0.8); ctx.closePath(); ctx.fill();
            ctx.strokeStyle = '#ee0088'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.6, h * 0.3); ctx.quadraticCurveTo(w * 0.8, h * 0.5, w * 0.6, h * 0.7); ctx.stroke();
            ctx.fillStyle = '#000000'; for (let i = 0; i < 8; i++) ctx.beginPath(), ctx.arc(0.1 * w + (i % 4) * 0.2 * w, 0.2 * h + Math.floor(i / 4) * 0.5 * h, 3, 0, Math.PI * 2), ctx.fill();
        },
        decade_80s_synth_sun: (ctx, w, h) => {
            ctx.fillStyle = '#1a0033'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ff00aa'; ctx.beginPath(); ctx.arc(w / 2, h * 0.8, Math.max(w, h) * 0.6, Math.PI, 0); ctx.fill();
            ctx.strokeStyle = '#000000'; ctx.lineWidth = 2; for (let y = h * 0.2; y < h; y += 8) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
        },
        decade_80s_my_little_friend: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h);
            const tableGrd = ctx.createLinearGradient(0, h * 0.4, 0, h);
            tableGrd.addColorStop(0, '#111111'); tableGrd.addColorStop(1, '#2a2a2a');
            ctx.fillStyle = tableGrd; ctx.fillRect(0, h * 0.4, w, h * 0.6);
            ctx.fillStyle = '#f0f0f0';
            ctx.shadowBlur = 18; ctx.shadowColor = '#ffffff';
            ctx.beginPath();
            ctx.ellipse(w * 0.5, h * 0.58, w * 0.35, h * 0.1, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 3; ctx.shadowColor = '#ffffff';
            ctx.strokeStyle = '#cccccc'; ctx.lineWidth = 1.5;
            for (let i = 0; i < 5; i++) {
                const lx = w * (0.25 + i * 0.11);
                ctx.beginPath(); ctx.moveTo(lx, h * 0.5); ctx.lineTo(lx, h * 0.68); ctx.stroke();
            }
            ctx.fillStyle = '#ffffff'; ctx.shadowBlur = 0;
            for (let i = 0; i < 80; i++) {
                const px = ((i * 137 + 71) % 1000) / 1000 * w;
                const py = h * 0.42 + ((i * 73 + 19) % 1000) / 1000 * h * 0.3;
                const pr = 0.5 + (i % 4) * 0.4;
                ctx.globalAlpha = 0.3 + (i % 3) * 0.2;
                ctx.beginPath(); ctx.arc(px, py, pr, 0, Math.PI * 2); ctx.fill();
            }
            ctx.globalAlpha = 1;
        },
        decade_80s_yo_joe: (ctx, w, h) => {
            const camoColors = ['#4a5240', '#6b5c3a', '#2e3226', '#7a6b4a', '#3c4035'];
            for (let i = 0; i < 20; i++) {
                const cx = ((i * 113) % 1000) / 1000 * w;
                const cy = ((i * 71) % 1000) / 1000 * h;
                const r = Math.min(w, h) * (0.1 + (i % 5) * 0.04);
                ctx.fillStyle = camoColors[i % camoColors.length];
                ctx.beginPath();
                ctx.ellipse(cx, cy, r * (1 + (i % 3) * 0.3), r * (0.6 + (i % 4) * 0.2), (i * 37) % 180 * Math.PI / 180, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.fillStyle = '#ffcc00';
            const drawStar = (cx, cy, r) => {
                ctx.beginPath();
                for (let i = 0; i < 5; i++) {
                    const a = (i * 4 * Math.PI / 5) - Math.PI / 2;
                    const ai = ((i * 4 + 2) * Math.PI / 5) - Math.PI / 2;
                    if (i === 0) ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                    else ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
                    ctx.lineTo(cx + Math.cos(ai) * r * 0.4, cy + Math.sin(ai) * r * 0.4);
                }
                ctx.closePath(); ctx.fill();
            };
            drawStar(w * 0.78, h * 0.22, Math.min(w, h) * 0.14);
            ctx.fillStyle = '#ffcc00';
            ctx.fillRect(0, h * 0.8, w, h * 0.2);
            ctx.fillStyle = '#000000'; ctx.font = `bold ${h * 0.14}px Impact, sans-serif`;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.fillText('YO JOE!', w * 0.5, h * 0.9);
        },
        decade_80s_acid_washed: (ctx, w, h) => {
            ctx.fillStyle = '#3a5888'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(50,80,130,0.6)'; ctx.lineWidth = 1;
            for (let i = -h; i < w + h; i += 4) {
                ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + h, h); ctx.stroke();
            }
            ctx.strokeStyle = 'rgba(70,110,170,0.4)';
            for (let i = -h; i < w + h; i += 4) {
                ctx.beginPath(); ctx.moveTo(i + h, 0); ctx.lineTo(i, h); ctx.stroke();
            }
            for (let i = 0; i < 12; i++) {
                const cx = ((i * 157 + 23) % 1000) / 1000 * w;
                const cy = ((i * 89 + 47) % 1000) / 1000 * h;
                const r = Math.min(w, h) * (0.08 + (i % 4) * 0.05);
                const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
                grd.addColorStop(0, 'rgba(180,210,255,0.65)');
                grd.addColorStop(0.5, 'rgba(160,190,240,0.35)');
                grd.addColorStop(1, 'rgba(100,150,200,0)');
                ctx.fillStyle = grd;
                ctx.beginPath(); ctx.ellipse(cx, cy, r * (1 + (i % 3) * 0.3), r * (0.7 + (i % 4) * 0.15), (i * 41) % 180 * Math.PI / 180, 0, Math.PI * 2);
                ctx.fill();
            }
        },
        decade_80s_pastel_zig: (ctx, w, h) => {
            ctx.fillStyle = '#ffccdd'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ccbbee'; for (let i = -1; i < 8; i++) { ctx.beginPath(); ctx.moveTo(i * w * 0.25, 0); ctx.lineTo((i + 1) * w * 0.25, h); ctx.lineTo((i + 2) * w * 0.25, 0); ctx.closePath(); ctx.fill(); }
            ctx.fillStyle = '#aaddcc'; for (let i = 0; i < 8; i++) { ctx.beginPath(); ctx.moveTo(i * w * 0.25 + w * 0.12, h); ctx.lineTo((i + 1) * w * 0.25 + w * 0.12, 0); ctx.lineTo((i + 2) * w * 0.25 + w * 0.12, h); ctx.closePath(); ctx.fill(); }
        },
        decade_80s_vapor: (ctx, w, h) => {
            const grd = ctx.createLinearGradient(0, 0, 0, h);
            grd.addColorStop(0, '#e8b4f8'); grd.addColorStop(1, '#b4d4f8');
            ctx.fillStyle = grd; ctx.fillRect(0, 0, w, h);
            const bands = [
                { color: 'rgba(200,100,230,0.3)', offset: 0, freq: 1.5 },
                { color: 'rgba(100,180,250,0.3)', offset: 0.3, freq: 2 },
                { color: 'rgba(255,150,200,0.25)', offset: 0.6, freq: 1.2 },
            ];
            bands.forEach(({ color, offset, freq }) => {
                ctx.strokeStyle = color; ctx.lineWidth = h * 0.15;
                ctx.beginPath();
                for (let x = 0; x <= w; x += 2) {
                    const y = h * (offset + 0.2 + 0.15 * Math.sin((x / w) * Math.PI * 2 * freq));
                    if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }
                ctx.stroke();
            });
        },
        decade_80s_pixel: (ctx, w, h) => {
            const cell = Math.min(w, h) / 8; for (let row = 0; row < 8; row++) for (let col = 0; col < 8; col++) { ctx.fillStyle = ((row + col) % 2) ? '#ff00aa' : '#00ffee'; ctx.fillRect(col * cell, row * cell, cell + 1, cell + 1); }
        },
        decade_90s_grunge: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(90); ctx.fillStyle = 'rgba(40,40,40,0.8)'; for (let i = 0; i < 15; i++) ctx.beginPath(), ctx.arc(rng() * w, rng() * h, 8 + rng() * 15, 0, Math.PI * 2), ctx.fill();
            ctx.strokeStyle = 'rgba(80,80,80,0.6)'; ctx.lineWidth = 1; for (let i = 0; i < 20; i++) { const x1 = rng() * w, y1 = rng() * h; ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1 + 20, y1 + 15); ctx.stroke(); }
        },
        decade_90s_trolls: (ctx, w, h) => {
            ctx.fillStyle = '#f5c8a0'; ctx.fillRect(0, 0, w, h);
            const hairColors = ['#ff0066', '#ff6600', '#ffee00', '#00cc66', '#3366ff', '#cc00ff'];
            const spikes = 12;
            for (let i = 0; i < spikes; i++) {
                const baseX = w * (i + 0.5) / spikes;
                const sway = Math.sin(i * 1.3) * w * 0.06;
                const tipH = h * (0.55 + Math.sin(i * 2.1) * 0.25);
                ctx.fillStyle = hairColors[i % hairColors.length];
                ctx.beginPath();
                ctx.moveTo(baseX - w * 0.04, h * 0.38);
                ctx.quadraticCurveTo(baseX + sway, h * 0.38 - tipH, baseX + sway * 1.5, h * 0.38 - tipH * 1.05);
                ctx.quadraticCurveTo(baseX + sway * 0.5, h * 0.38 - tipH * 0.8, baseX + w * 0.04, h * 0.38);
                ctx.closePath(); ctx.fill();
            }
            ctx.fillStyle = '#222222';
            ctx.beginPath(); ctx.arc(w * 0.38, h * 0.52, h * 0.05, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.arc(w * 0.62, h * 0.52, h * 0.05, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#e06060';
            ctx.beginPath(); ctx.arc(w * 0.5, h * 0.62, h * 0.04, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#00ddcc';
            ctx.shadowBlur = 6; ctx.shadowColor = '#00ffee';
            ctx.beginPath();
            ctx.moveTo(w * 0.5, h * 0.77); ctx.lineTo(w * 0.57, h * 0.86); ctx.lineTo(w * 0.5, h * 0.93); ctx.lineTo(w * 0.43, h * 0.86);
            ctx.closePath(); ctx.fill();
            ctx.shadowBlur = 0;
        },
        decade_90s_alt_cross: (ctx, w, h) => {
            ctx.fillStyle = '#222222'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff'; ctx.fillRect(w * 0.35, 0, w * 0.3, h); ctx.fillRect(0, h * 0.35, w, h * 0.3);
        },
        decade_90s_geo_minimal: (ctx, w, h) => {
            ctx.fillStyle = '#cccccc'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = 'rgba(100,120,140,0.5)'; ctx.beginPath(); ctx.arc(w * 0.35, h * 0.4, w * 0.25, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = 'rgba(140,100,120,0.5)'; ctx.beginPath(); ctx.arc(w * 0.65, h * 0.6, w * 0.2, 0, Math.PI * 2); ctx.fill();
        },
        decade_90s_rave_zig: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#44ff00'; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(i * w * 0.25, 0); ctx.lineTo((i + 1) * w * 0.25, h); ctx.lineTo((i + 2) * w * 0.25, 0); ctx.closePath(); ctx.fill(); }
            ctx.fillStyle = '#0044ff'; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(i * w * 0.25 + w * 0.12, h); ctx.lineTo((i + 1) * w * 0.25 + w * 0.12, 0); ctx.lineTo((i + 2) * w * 0.25 + w * 0.12, h); ctx.closePath(); ctx.fill(); }
        },
        decade_90s_chrome_bubble: (ctx, w, h) => {
            ctx.fillStyle = '#99aacc'; ctx.fillRect(0, 0, w, h);
            const drawChromeBall = (cx, cy, r) => {
                const grd = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.05, cx, cy, r);
                grd.addColorStop(0, '#ffffff');
                grd.addColorStop(0.25, '#ddeeff');
                grd.addColorStop(0.65, '#8899bb');
                grd.addColorStop(1, '#223355');
                ctx.fillStyle = grd;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = 'rgba(255,255,255,0.75)';
                ctx.beginPath(); ctx.ellipse(cx - r * 0.28, cy - r * 0.28, r * 0.22, r * 0.14, -Math.PI / 4, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = 'rgba(0,0,30,0.3)';
                ctx.beginPath(); ctx.ellipse(cx, cy + r * 0.85, r * 0.7, r * 0.12, 0, 0, Math.PI * 2); ctx.fill();
            };
            const positions = [[0.25, 0.28, 0.22], [0.7, 0.22, 0.18], [0.5, 0.6, 0.26], [0.15, 0.72, 0.16], [0.78, 0.68, 0.2]];
            positions.forEach(([px, py, pr]) => drawChromeBall(w * px, h * py, Math.min(w, h) * pr));
        },
        decade_90s_y2k: (ctx, w, h) => {
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#00ff88';
            ctx.shadowBlur = 6; ctx.shadowColor = '#00ff88';
            ctx.font = `bold ${h * 0.28}px "Courier New", monospace`;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            const cols = 3, rows = 3;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    ctx.fillText('Y2K', w * (c + 0.5) / cols, h * (r + 0.5) / rows);
                }
            }
            ctx.shadowBlur = 0;
        },
        decade_90s_tama90s: (ctx, w, h) => {
            ctx.fillStyle = '#eecc88'; ctx.fillRect(0, 0, w, h);
            const drawTama = (x, y, s) => {
                ctx.fillStyle = '#ffeeaa';
                ctx.strokeStyle = '#333300'; ctx.lineWidth = s * 0.05;
                ctx.beginPath(); ctx.ellipse(x, y, s * 0.45, s * 0.55, 0, 0, Math.PI * 2);
                ctx.fill(); ctx.stroke();
                ctx.fillStyle = '#88cc44';
                ctx.beginPath(); ctx.roundRect(x - s * 0.28, y - s * 0.28, s * 0.56, s * 0.38, s * 0.05);
                ctx.fill();
                ctx.fillStyle = '#224400';
                [[0, 1], [1, 0], [1, 2], [2, 1], [1, 1]].forEach(([dx, dy]) => {
                    ctx.fillRect(x - s * 0.12 + dx * s * 0.1, y - s * 0.2 + dy * s * 0.1, s * 0.09, s * 0.09);
                });
                [-.18, 0, .18].forEach(bx => {
                    ctx.fillStyle = '#cc4466';
                    ctx.beginPath(); ctx.arc(x + bx * s, y + s * 0.25, s * 0.07, 0, Math.PI * 2); ctx.fill();
                    ctx.strokeStyle = '#330000'; ctx.lineWidth = s * 0.03;
                    ctx.stroke();
                });
                ctx.fillStyle = '#888877';
                ctx.beginPath(); ctx.arc(x, y - s * 0.53, s * 0.06, 0, Math.PI * 2); ctx.fill();
            };
            const cols = 3, rows = 2;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    drawTama(w * (c + 0.5) / cols, h * (r + 0.5) / rows, Math.min(w / cols, h / rows) * 0.85);
                }
            }
        },
        decade_90s_dot_matrix: (ctx, w, h) => {
            ctx.fillStyle = '#f5f0e8'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff'; ctx.strokeStyle = '#ccbbaa'; ctx.lineWidth = 0.5;
            const holeSpacing = h / 8;
            for (let i = 0; i < 9; i++) {
                const hy = i * holeSpacing;
                [w * 0.04, w * 0.96].forEach(hx => {
                    ctx.beginPath(); ctx.arc(hx, hy, w * 0.025, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
                });
            }
            ctx.setLineDash([3, 3]); ctx.strokeStyle = '#bbbbbb'; ctx.lineWidth = 0.5;
            [w * 0.085, w * 0.915].forEach(lx => {
                ctx.beginPath(); ctx.moveTo(lx, 0); ctx.lineTo(lx, h); ctx.stroke();
            });
            ctx.setLineDash([]);
            ctx.fillStyle = '#222222';
            ctx.font = `${h * 0.08}px "Courier New", monospace`;
            ctx.textAlign = 'left';
            const lines = ['PRINTING...', 'ITEM   QTY  AMT', '----   ---  ---', 'PART A  01  $2.50', 'PART B  03  $7.25', 'TOTAL:      $9.75', '', '*** THANK YOU ***'];
            lines.forEach((line, i) => ctx.fillText(line, w * 0.12, h * 0.1 + i * h * 0.104));
        },
        decade_90s_floppy_disk: (ctx, w, h) => {
            ctx.fillStyle = '#221133'; ctx.fillRect(0, 0, w, h);
            const drawFloppy = (x, y, s) => {
                ctx.fillStyle = '#1a1a2a'; ctx.strokeStyle = '#6655aa'; ctx.lineWidth = s * 0.04;
                ctx.beginPath(); ctx.roundRect(x - s * 0.42, y - s * 0.45, s * 0.84, s * 0.9, s * 0.06);
                ctx.fill(); ctx.stroke();
                ctx.fillStyle = '#ddccff';
                ctx.beginPath(); ctx.roundRect(x - s * 0.32, y - s * 0.4, s * 0.64, s * 0.5, s * 0.04);
                ctx.fill();
                ctx.fillStyle = '#330055'; ctx.font = `bold ${s * 0.12}px sans-serif`;
                ctx.textAlign = 'center'; ctx.textBaseline = 'top';
                ctx.fillText('HD  1.44MB', x, y - s * 0.32);
                ctx.fillStyle = '#6655aa';
                ctx.fillRect(x + s * 0.28, y - s * 0.45, s * 0.12, s * 0.14);
                ctx.fillStyle = '#888899';
                ctx.beginPath(); ctx.roundRect(x - s * 0.18, y + s * 0.14, s * 0.36, s * 0.26, s * 0.02);
                ctx.fill();
                ctx.fillStyle = '#1a1a2a';
                ctx.beginPath(); ctx.ellipse(x, y + s * 0.27, s * 0.06, s * 0.06, 0, 0, Math.PI * 2); ctx.fill();
            };
            const cols = 3, rows = 2;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    drawFloppy(w * (c + 0.5) / cols, h * (r + 0.5) / rows, Math.min(w / cols, h / rows) * 0.88);
                }
            }
        },
        music_lightning_bolt: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffdd00';
            ctx.shadowBlur = 8; ctx.shadowColor = '#ff8800';
            ctx.beginPath();
            ctx.moveTo(w * 0.2, h * 0.1);
            ctx.lineTo(w * 0.82, h * 0.1);
            ctx.lineTo(w * 0.82, h * 0.2);
            ctx.lineTo(w * 0.44, h * 0.55);
            ctx.lineTo(w * 0.82, h * 0.55);
            ctx.lineTo(w * 0.82, h * 0.65);
            ctx.lineTo(w * 0.18, h * 0.65);
            ctx.lineTo(w * 0.18, h * 0.55);
            ctx.lineTo(w * 0.56, h * 0.2);
            ctx.lineTo(w * 0.2, h * 0.2);
            ctx.closePath(); ctx.fill();
            ctx.strokeStyle = '#ff4400'; ctx.lineWidth = h * 0.025; ctx.shadowBlur = 6;
            ctx.beginPath(); ctx.moveTo(w * 0.78, h * 0.72); ctx.lineTo(w * 0.65, h * 0.85); ctx.lineTo(w * 0.75, h * 0.85); ctx.lineTo(w * 0.58, h * 0.95); ctx.stroke();
            ctx.shadowBlur = 0;
        },
        music_wing_sweep: (ctx, w, h) => { ctx.fillStyle = '#1a1008'; ctx.fillRect(0, 0, w, h); ctx.fillStyle = '#cc9900'; ctx.beginPath(); ctx.moveTo(w * 0.15, h * 0.5); ctx.quadraticCurveTo(w * 0.4, h * 0.2, w * 0.95, h * 0.35); ctx.quadraticCurveTo(w * 0.6, h * 0.6, w * 0.15, h * 0.5); ctx.fill(); },
        music_script_curve: (ctx, w, h) => { ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#aabbcc'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.3); ctx.bezierCurveTo(w * 0.5, h * 0.1, w * 0.5, h * 0.9, w * 0.8, h * 0.7); ctx.stroke(); },
        music_skull_abstract: (ctx, w, h) => {
            ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff';
            ctx.beginPath(); ctx.ellipse(w * 0.5, h * 0.32, w * 0.32, h * 0.28, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath();
            ctx.moveTo(w * 0.28, h * 0.45); ctx.lineTo(w * 0.72, h * 0.45);
            ctx.lineTo(w * 0.68, h * 0.68); ctx.lineTo(w * 0.32, h * 0.68);
            ctx.closePath(); ctx.fill();
            ctx.fillStyle = '#000000';
            ctx.beginPath(); ctx.ellipse(w * 0.36, h * 0.3, w * 0.1, h * 0.1, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(w * 0.64, h * 0.3, w * 0.1, h * 0.1, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(w * 0.44, h * 0.44, w * 0.055, h * 0.045, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(w * 0.56, h * 0.44, w * 0.055, h * 0.045, 0, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#000000';
            const teethX = [0.3, 0.38, 0.46, 0.54, 0.62];
            teethX.forEach(tx => ctx.fillRect(w * tx, h * 0.52, w * 0.065, h * 0.14));
        },
        music_arrow_bold: (ctx, w, h) => {
            ctx.fillStyle = '#cc0000'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#111111';
            const drawArrow = (x, y, s, angle) => {
                ctx.save(); ctx.translate(x, y); ctx.rotate(angle);
                ctx.beginPath();
                ctx.moveTo(s * 0.5, 0);
                ctx.lineTo(s * 0.1, -s * 0.35);
                ctx.lineTo(s * 0.1, -s * 0.15);
                ctx.lineTo(-s * 0.5, -s * 0.15);
                ctx.lineTo(-s * 0.5, s * 0.15);
                ctx.lineTo(s * 0.1, s * 0.15);
                ctx.lineTo(s * 0.1, s * 0.35);
                ctx.closePath(); ctx.fill();
                ctx.restore();
            };
            drawArrow(w * 0.5, h * 0.3, Math.min(w, h) * 0.52, 0);
            drawArrow(w * 0.5, h * 0.72, Math.min(w, h) * 0.52, 0);
        },
        music_blues: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a2e'; ctx.fillRect(0, 0, w, h);
            const drawNote = (x, y, s) => {
                ctx.fillStyle = '#4488ff';
                ctx.shadowBlur = 4; ctx.shadowColor = '#2255cc';
                ctx.beginPath(); ctx.ellipse(x, y + s * 0.45, s * 0.22, s * 0.17, -0.4, 0, Math.PI * 2); ctx.fill();
                ctx.fillRect(x + s * 0.14, y - s * 0.2, s * 0.07, s * 0.65);
                ctx.beginPath();
                ctx.moveTo(x + s * 0.21, y - s * 0.2);
                ctx.quadraticCurveTo(x + s * 0.55, y, x + s * 0.21, y + s * 0.2);
                ctx.fill();
                ctx.shadowBlur = 0;
            };
            const cols = 3, rows = 4;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const jx = (((r * 7 + c * 13) % 7) - 3) / 3 * w / cols * 0.18;
                    const jy = (((r * 11 + c * 5) % 7) - 3) / 3 * h / rows * 0.18;
                    drawNote(w * (c + 0.5) / cols + jx, h * (r + 0.5) / rows + jy, Math.min(w / cols, h / rows) * 0.7);
                }
            }
        },
        music_strat: (ctx, w, h) => {
            ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
            const stripes = [
                { color: '#000000', x: 0, wf: 0.08 }, { color: '#ff0000', x: 0.09, wf: 0.14 }, { color: '#000000', x: 0.24, wf: 0.06 }, { color: '#ff0000', x: 0.31, wf: 0.04 }, { color: '#000000', x: 0.36, wf: 0.12 }, { color: '#ff0000', x: 0.49, wf: 0.07 }, { color: '#000000', x: 0.57, wf: 0.05 }, { color: '#ff0000', x: 0.63, wf: 0.11 }, { color: '#000000', x: 0.75, wf: 0.08 }, { color: '#ff0000', x: 0.84, wf: 0.05 }, { color: '#000000', x: 0.90, wf: 0.10 },
            ];
            ctx.save();
            ctx.translate(w * 0.5, h * 0.5);
            ctx.rotate(-0.25);
            ctx.translate(-w * 0.5, -h * 0.5);
            stripes.forEach(({ color, x, wf }) => {
                ctx.fillStyle = color;
                ctx.fillRect(x * w - 10, -20, wf * w, h + 40);
            });
            ctx.restore();
        },
        music_the_artist: (ctx, w, h) => {
            ctx.fillStyle = '#1a0033'; ctx.fillRect(0, 0, w, h);
            const drawPrinceSymbol = (cx, cy, s) => {
                ctx.strokeStyle = '#cc8800'; ctx.lineWidth = s * 0.1;
                ctx.fillStyle = '#cc8800';
                ctx.shadowBlur = 5; ctx.shadowColor = '#ffaa00';
                ctx.beginPath(); ctx.arc(cx, cy - s * 0.12, s * 0.3, 0, Math.PI * 2); ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(cx + s * 0.22, cy - s * 0.34);
                ctx.lineTo(cx + s * 0.42, cy - s * 0.52); ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(cx + s * 0.42, cy - s * 0.52);
                ctx.lineTo(cx + s * 0.28, cy - s * 0.5);
                ctx.lineTo(cx + s * 0.4, cy - s * 0.38);
                ctx.closePath(); ctx.fill();
                ctx.beginPath();
                ctx.moveTo(cx, cy + s * 0.18);
                ctx.lineTo(cx, cy + s * 0.58); ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(cx - s * 0.2, cy + s * 0.42);
                ctx.lineTo(cx + s * 0.2, cy + s * 0.42); ctx.stroke();
                ctx.shadowBlur = 0;
            };
            drawPrinceSymbol(w * 0.5, h * 0.5, Math.min(w, h) * 0.7);
        },
        music_smilevana: (ctx, w, h) => {
            ctx.fillStyle = '#ffdd00'; ctx.fillRect(0, 0, w, h);
            const drawSmiley = (cx, cy, r) => {
                ctx.fillStyle = '#ffdd00'; ctx.strokeStyle = '#000000'; ctx.lineWidth = r * 0.1;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
                ctx.strokeStyle = '#000000'; ctx.lineWidth = r * 0.12;
                const eyeOff = r * 0.32, eyeR = r * 0.18;
                [[-eyeOff, 0], [eyeOff, 0]].forEach(([ex, ey]) => {
                    ctx.beginPath(); ctx.moveTo(cx + ex - eyeR, cy - r * 0.08 - eyeR); ctx.lineTo(cx + ex + eyeR, cy - r * 0.08 + eyeR); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(cx + ex + eyeR, cy - r * 0.08 - eyeR); ctx.lineTo(cx + ex - eyeR, cy - r * 0.08 + eyeR); ctx.stroke();
                });
                ctx.beginPath();
                ctx.moveTo(cx - r * 0.42, cy + r * 0.18);
                ctx.bezierCurveTo(cx - r * 0.15, cy + r * 0.6, cx + r * 0.35, cy + r * 0.3, cx + r * 0.45, cy + r * 0.1);
                ctx.stroke();
            };
            const cols = 3, rows = 3;
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    drawSmiley(w * (c + 0.5) / cols, h * (r + 0.5) / rows, Math.min(w / cols, h / rows) * 0.38);
                }
            }
        },
        music_licked: (ctx, w, h) => {
            ctx.fillStyle = '#111111'; ctx.fillRect(0, 0, w, h);
            const drawTongue = (cx, cy, s) => {
                ctx.fillStyle = '#cc0000';
                ctx.beginPath();
                ctx.moveTo(cx - s * 0.5, cy - s * 0.04);
                ctx.bezierCurveTo(cx - s * 0.25, cy - s * 0.28, cx, cy - s * 0.08, cx + s * 0.0, cy - s * 0.04);
                ctx.bezierCurveTo(cx + s * 0.0, cy - s * 0.04, cx + s * 0.25, cy - s * 0.28, cx + s * 0.5, cy - s * 0.04);
                ctx.lineTo(cx + s * 0.5, cy + s * 0.04);
                ctx.bezierCurveTo(cx + s * 0.25, cy + s * 0.1, cx, cy + s * 0.08, cx - s * 0.0, cy + s * 0.04);
                ctx.bezierCurveTo(cx - s * 0.25, cy + s * 0.1, cx - s * 0.5, cy + s * 0.04, cx - s * 0.5, cy - s * 0.04);
                ctx.closePath(); ctx.fill();
                ctx.fillStyle = '#ee1111';
                ctx.beginPath();
                ctx.moveTo(cx - s * 0.22, cy + s * 0.04);
                ctx.bezierCurveTo(cx - s * 0.28, cy + s * 0.55, cx - s * 0.18, cy + s * 0.85, cx, cy + s * 0.9);
                ctx.bezierCurveTo(cx + s * 0.18, cy + s * 0.85, cx + s * 0.28, cy + s * 0.55, cx + s * 0.22, cy + s * 0.04);
                ctx.closePath(); ctx.fill();
                const tGrd = ctx.createLinearGradient(cx - s * 0.2, cy + s * 0.04, cx + s * 0.2, cy + s * 0.04);
                tGrd.addColorStop(0, 'rgba(200,0,0,0.4)');
                tGrd.addColorStop(0.5, 'rgba(255,80,80,0.0)');
                tGrd.addColorStop(1, 'rgba(200,0,0,0.4)');
                ctx.fillStyle = tGrd;
                ctx.beginPath();
                ctx.moveTo(cx - s * 0.22, cy + s * 0.04);
                ctx.bezierCurveTo(cx - s * 0.28, cy + s * 0.55, cx - s * 0.18, cy + s * 0.85, cx, cy + s * 0.9);
                ctx.bezierCurveTo(cx + s * 0.18, cy + s * 0.85, cx + s * 0.28, cy + s * 0.55, cx + s * 0.22, cy + s * 0.04);
                ctx.closePath(); ctx.fill();
            };
            drawTongue(w * 0.5, h * 0.28, Math.min(w * 0.9, h * 0.55));
            [[0.18, 0.82], [0.82, 0.82]].forEach(([px, py]) => drawTongue(w * px, h * py, Math.min(w, h) * 0.2));
        },
        astro_moon_phases: (ctx, w, h) => { ctx.fillStyle = '#040818'; ctx.fillRect(0, 0, w, h); const cy = h / 2, r = w * 0.08; const xs = [w * 0.12, w * 0.32, w * 0.52, w * 0.72]; ctx.fillStyle = '#1a1a30'; ctx.beginPath(); ctx.arc(xs[0], cy, r, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = '#e8e4ff'; ctx.beginPath(); ctx.arc(xs[1], cy, r, 0, Math.PI * 2); ctx.fill(); ctx.globalCompositeOperation = 'destination-out'; ctx.beginPath(); ctx.arc(xs[1] - r * 0.5, cy, r, 0, Math.PI * 2); ctx.fill(); ctx.globalCompositeOperation = 'source-over'; ctx.fillStyle = '#e8e4ff'; ctx.beginPath(); ctx.arc(xs[2], cy, r, Math.PI / 2, Math.PI * 1.5); ctx.lineTo(xs[2], cy); ctx.closePath(); ctx.fill(); ctx.beginPath(); ctx.arc(xs[3], cy, r, 0, Math.PI * 2); ctx.fill(); },
        astro_stars_constellation: (ctx, w, h) => { ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h); const pts = [[0.2, 0.3], [0.35, 0.25], [0.5, 0.4], [0.45, 0.55], [0.6, 0.7], [0.75, 0.5], [0.85, 0.35]]; ctx.fillStyle = '#ffffff'; pts.forEach(([x, y], i) => { ctx.beginPath(); ctx.arc(x * w, y * h, i % 2 ? 2 : 3, 0, Math.PI * 2); ctx.fill(); }); ctx.strokeStyle = 'rgba(255,255,255,0.3)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(pts[0][0] * w, pts[0][1] * h); pts.slice(1).forEach(([x, y]) => ctx.lineTo(x * w, y * h)); ctx.stroke(); },
        astro_sun_rays: (ctx, w, h) => { ctx.fillStyle = '#ff8800'; ctx.fillRect(0, 0, w, h); const cx = w / 2, cy = h / 2; ctx.fillStyle = '#ffdd00'; ctx.beginPath(); ctx.arc(cx, cy, w * 0.12, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = '#ffdd00'; for (let i = 0; i < 16; i++) { const a = (i / 16) * Math.PI * 2; ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * w * 0.15, cy + Math.sin(a) * h * 0.15); ctx.lineTo(cx + Math.cos(a) * w * 0.45, cy + Math.sin(a) * h * 0.45); ctx.lineTo(cx + Math.cos(a + 0.08) * w * 0.4, cy + Math.sin(a + 0.08) * h * 0.4); ctx.closePath(); ctx.fill(); } },
        astro_orbital_rings: (ctx, w, h) => { ctx.fillStyle = '#030810'; ctx.fillRect(0, 0, w, h); const cx = w / 2, cy = h / 2; ctx.strokeStyle = 'rgba(100,180,255,0.8)'; ctx.lineWidth = 1; for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.ellipse(cx, cy, w * (0.15 + i * 0.12), h * (0.12 + i * 0.1), (i * 0.3), 0, Math.PI * 2); ctx.stroke(); } },
        astro_comet_trail: (ctx, w, h) => { ctx.fillStyle = '#0a0a18'; ctx.fillRect(0, 0, w, h); ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.ellipse(w * 0.75, h * 0.35, w * 0.08, h * 0.06, 0, 0, Math.PI * 2); ctx.fill(); for (let i = 1; i < 15; i++) { ctx.fillStyle = `rgba(255,255,255,${0.5 - i / 30})`; ctx.beginPath(); ctx.arc(w * 0.75 - i * 4, h * 0.35 + i * 2, 2, 0, Math.PI * 2); ctx.fill(); } },
        astro_galaxy_swirl: (ctx, w, h) => { ctx.fillStyle = '#020418'; ctx.fillRect(0, 0, w, h); const cx = w / 2, cy = h / 2, rng = _seededRng(98); ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 3; ctx.beginPath(); for (let t = 0; t <= 1; t += 0.02) { const r = w * 0.1 + t * w * 0.35, a = t * Math.PI * 2 * 2; ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r * 0.8); } ctx.stroke(); ctx.beginPath(); for (let t = 0; t <= 1; t += 0.02) { const r = w * 0.1 + t * w * 0.35, a = Math.PI + t * Math.PI * 2 * 2; ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r * 0.8); } ctx.stroke(); ctx.fillStyle = '#ffffff'; for (let i = 0; i < 20; i++) ctx.beginPath(), ctx.arc(cx + (rng() - 0.5) * w * 0.5, cy + (rng() - 0.5) * h * 0.5, 1, 0, Math.PI * 2), ctx.fill(); },
        astro_nebula_drift: (ctx, w, h) => {
            ctx.fillStyle = '#020408'; ctx.fillRect(0, 0, w, h);
            const clouds = [
                { cx: w * 0.3, cy: h * 0.4, r: h * 0.35, color: 'rgba(60,0,120,0.5)' },
                { cx: w * 0.65, cy: h * 0.55, r: h * 0.3, color: 'rgba(0,40,100,0.4)' },
                { cx: w * 0.5, cy: h * 0.3, r: h * 0.25, color: 'rgba(100,0,60,0.35)' },
                { cx: w * 0.15, cy: h * 0.7, r: h * 0.2, color: 'rgba(0,80,80,0.3)' },
            ];
            clouds.forEach(({ cx, cy, r, color }) => {
                const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
                grd.addColorStop(0, color); grd.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = grd;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
            });
            for (let i = 0; i < 80; i++) {
                const sx = ((i * 137) % 1000) / 1000 * w;
                const sy = ((i * 89) % 1000) / 1000 * h;
                const sr = 0.4 + (i % 4) * 0.35;
                ctx.fillStyle = `rgba(255,255,255,${0.3 + (i % 5) * 0.14})`;
                ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.fill();
            }
        },
        astro_zodiac_aries: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; const cx = w / 2, cy = h / 2; ctx.beginPath(); ctx.arc(cx - w * 0.15, cy + h * 0.2, w * 0.12, 0.8 * Math.PI, 2.2 * Math.PI); ctx.arc(cx + w * 0.15, cy + h * 0.2, w * 0.12, 0.8 * Math.PI, 2.2 * Math.PI); ctx.stroke(); },
        astro_zodiac_taurus: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; const cx = w / 2, cy = h / 2; ctx.beginPath(); ctx.arc(cx, cy + h * 0.05, w * 0.25, 0, Math.PI * 2); ctx.stroke(); ctx.beginPath(); ctx.arc(cx - w * 0.2, cy - h * 0.25, w * 0.1, 0, Math.PI * 2); ctx.arc(cx + w * 0.2, cy - h * 0.25, w * 0.1, 0, Math.PI * 2); ctx.stroke(); },
        astro_zodiac_gemini: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.35, h * 0.2); ctx.lineTo(w * 0.35, h * 0.8); ctx.moveTo(w * 0.65, h * 0.2); ctx.lineTo(w * 0.65, h * 0.8); ctx.moveTo(w * 0.25, h * 0.2); ctx.lineTo(w * 0.75, h * 0.2); ctx.moveTo(w * 0.25, h * 0.8); ctx.lineTo(w * 0.75, h * 0.8); ctx.stroke(); },
        astro_zodiac_cancer: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; const cx = w / 2, cy = h / 2; ctx.beginPath(); ctx.arc(cx - w * 0.2, cy - h * 0.15, w * 0.12, 0, Math.PI * 2); ctx.arc(cx + w * 0.2, cy + h * 0.15, w * 0.12, 0, Math.PI * 2); ctx.stroke(); },
        astro_zodiac_leo: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; const cx = w / 2, cy = h / 2; ctx.beginPath(); ctx.arc(cx, cy, w * 0.28, -0.3 * Math.PI, 0.85 * Math.PI); ctx.quadraticCurveTo(cx + w * 0.2, cy + h * 0.35, cx - w * 0.1, cy + h * 0.2); ctx.stroke(); },
        astro_zodiac_virgo: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.3, h * 0.2); ctx.lineTo(w * 0.3, h * 0.8); ctx.moveTo(w * 0.5, h * 0.2); ctx.lineTo(w * 0.5, h * 0.8); ctx.moveTo(w * 0.7, h * 0.2); ctx.lineTo(w * 0.7, h * 0.55); ctx.arc(w * 0.78, h * 0.55, w * 0.08, Math.PI, 0); ctx.stroke(); },
        astro_zodiac_libra: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.6); ctx.lineTo(w * 0.8, h * 0.6); ctx.moveTo(w * 0.5, h * 0.25); ctx.quadraticCurveTo(w * 0.5, h * 0.55, w * 0.5, h * 0.6); ctx.stroke(); },
        astro_zodiac_scorpio: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.3, h * 0.2); ctx.lineTo(w * 0.3, h * 0.7); ctx.moveTo(w * 0.5, h * 0.2); ctx.lineTo(w * 0.5, h * 0.7); ctx.moveTo(w * 0.7, h * 0.2); ctx.lineTo(w * 0.7, h * 0.5); ctx.lineTo(w * 0.85, h * 0.75); ctx.stroke(); },
        astro_zodiac_sagittarius: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.25, h * 0.8); ctx.lineTo(w * 0.75, h * 0.2); ctx.moveTo(w * 0.45, h * 0.45); ctx.lineTo(w * 0.55, h * 0.35); ctx.moveTo(w * 0.5, h * 0.3); ctx.lineTo(w * 0.5, h * 0.55); ctx.stroke(); },
        astro_zodiac_capricorn: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.35, h * 0.2); ctx.lineTo(w * 0.5, h * 0.8); ctx.moveTo(w * 0.65, h * 0.2); ctx.lineTo(w * 0.65, h * 0.6); ctx.quadraticCurveTo(w * 0.75, h * 0.8, w * 0.65, h * 0.75); ctx.stroke(); },
        astro_zodiac_aquarius: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; ctx.beginPath(); for (let x = 0.2; x < 0.9; x += 0.15) ctx.moveTo(x * w, h * 0.35 + Math.sin(x * 8) * 5), ctx.lineTo((x + 0.1) * w, h * 0.35 + Math.sin((x + 0.1) * 8) * 5); for (let x = 0.2; x < 0.9; x += 0.15) ctx.moveTo(x * w, h * 0.65 + Math.sin(x * 7) * 5), ctx.lineTo((x + 0.1) * w, h * 0.65 + Math.sin((x + 0.1) * 7) * 5); ctx.stroke(); },
        astro_zodiac_pisces: (ctx, w, h) => { ctx.fillStyle = '#050a18'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#d4a820'; ctx.lineWidth = 2; const cx = w / 2, cy = h / 2; ctx.beginPath(); ctx.arc(cx - w * 0.15, cy, w * 0.12, 0, Math.PI * 2); ctx.arc(cx + w * 0.15, cy, w * 0.12, 0, Math.PI * 2); ctx.moveTo(cx - w * 0.27, cy); ctx.lineTo(cx + w * 0.27, cy); ctx.stroke(); },
        hero_crest_curve: (ctx, w, h) => { ctx.fillStyle = '#0a1a3a'; ctx.fillRect(0, 0, w, h); ctx.fillStyle = '#ccaa00'; ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.7); ctx.quadraticCurveTo(w * 0.2, h * 0.2, w * 0.5, h * 0.1); ctx.quadraticCurveTo(w * 0.8, h * 0.2, w * 0.8, h * 0.7); ctx.closePath(); ctx.fill(); },
        hero_scallop_edge: (ctx, w, h) => { ctx.fillStyle = '#000000'; ctx.fillRect(0, 0, w, h); ctx.fillStyle = '#ddaa00'; for (let i = 0; i < 7; i++) { const x = w * (0.08 + i * 0.14); ctx.beginPath(); ctx.arc(x, h * 0.75, w * 0.08, 0, Math.PI); ctx.fill(); } },
        hero_pointed_cowl: (ctx, w, h) => { ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#aaaa00'; ctx.fillStyle = '#2a2a2a'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(w * 0.35, h); ctx.lineTo(w * 0.4, h * 0.15); ctx.lineTo(w * 0.5, h * 0.05); ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(w * 0.5, h * 0.05); ctx.lineTo(w * 0.6, h * 0.15); ctx.lineTo(w * 0.65, h); ctx.closePath(); ctx.fill(); ctx.stroke(); },
        sport_stadium_line: (ctx, w, h) => { ctx.fillStyle = '#228b22'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(0, h + i * 15); ctx.lineTo(w, -h * 0.2 + i * 15); ctx.stroke(); } },
        sport_team_stripe: (ctx, w, h) => { ctx.fillStyle = '#002244'; ctx.fillRect(0, 0, w, h); for (let i = 0; i < 4; i++) { ctx.fillStyle = i % 2 ? '#ffffff' : '#002244'; ctx.fillRect(0, i * (h / 4), w, h / 4 + 1); } },
        long_flame_sweep: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const tongues = [
                { by: h * 0.25, tipY: h * 0.08, bw: h * 0.22, reach: w * 0.98, sway: -h * 0.05 },
                { by: h * 0.55, tipY: h * 0.35, bw: h * 0.20, reach: w * 0.95, sway: h * 0.07 },
                { by: h * 0.75, tipY: h * 0.62, bw: h * 0.16, reach: w * 0.92, sway: -h * 0.04 },
                { by: h * 0.42, tipY: h * 0.15, bw: h * 0.14, reach: w * 0.88, sway: h * 0.03 },
                { by: h * 0.68, tipY: h * 0.45, bw: h * 0.12, reach: w * 0.85, sway: -h * 0.06 },
            ];
            tongues.forEach(({ by, tipY, bw, reach, sway }, i) => {
                const g = _flameGrad(ctx, 0, by, reach, tipY,
                    i < 2 ? [[0, 'rgba(180,20,0,0.9)'], [0.5, 'rgba(220,80,0,0.7)'], [1, 'rgba(255,160,0,0)']]
                        : [[0, 'rgba(255,100,0,0.9)'], [0.5, 'rgba(255,200,0,0.6)'], [1, 'rgba(255,255,100,0)']]);
                ctx.fillStyle = g;
                _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            });
        },
        short_flame_lick: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const tData = [
                [h * 0.18, h * 0.04, h * 0.14, w * 0.42, h * 0.03], [h * 0.32, h * 0.12, h * 0.12, w * 0.38, -h * 0.04], [h * 0.48, h * 0.28, h * 0.14, w * 0.45, h * 0.05], [h * 0.62, h * 0.40, h * 0.13, w * 0.40, -h * 0.03], [h * 0.76, h * 0.58, h * 0.12, w * 0.35, h * 0.04], [h * 0.22, h * 0.05, h * 0.10, w * 0.30, h * 0.02], [h * 0.54, h * 0.33, h * 0.11, w * 0.36, -h * 0.05], [h * 0.84, h * 0.68, h * 0.10, w * 0.32, h * 0.03],
            ];
            tData.forEach(([by, tipY, bw, reach, sway], i) => {
                const g = _flameGrad(ctx, 0, by, reach, tipY,
                    [[0, 'rgba(200,30,0,0.95)'], [0.45, 'rgba(255,120,0,0.8)'], [0.8, 'rgba(255,220,50,0.5)'], [1, 'rgba(255,255,150,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            });
        },
        flame_panel_edge: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 10; i++) {
                const by = h * (i + 0.5) / 10;
                const tipY = by - h * (0.07 + (i % 3) * 0.04);
                const bw = h * (0.04 + (i % 4) * 0.01);
                const reach = w * (0.15 + (i % 3) * 0.07);
                const sway = (i % 2 === 0 ? 1 : -1) * h * 0.02;
                const g = _flameGrad(ctx, 0, by, reach, tipY,
                    [[0, 'rgba(220,60,0,0.95)'], [0.6, 'rgba(255,180,0,0.7)'], [1, 'rgba(255,255,100,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            }
        },
        flame_belt_line: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const beltTop = h * 0.3, beltBot = h * 0.7;
            for (let i = 0; i < 6; i++) {
                const by = beltTop + (beltBot - beltTop) * (i + 0.5) / 6;
                const tipY = by - h * (0.1 + (i % 3) * 0.05);
                const bw = (beltBot - beltTop) / 6 * 0.45;
                const reach = w * (0.65 + (i % 3) * 0.12);
                const sway = (i % 2 === 0 ? 1 : -1) * h * 0.03;
                const g = _flameGrad(ctx, 0, by, reach, tipY,
                    [[0, 'rgba(200,20,0,0.9)'], [0.4, 'rgba(255,100,0,0.8)'], [0.8, 'rgba(255,200,30,0.5)'], [1, 'rgba(255,255,100,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            }
        },
        flame_fishtail: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            [[h * 0.35, h * 0.12, h * 0.24, w * 0.65, -h * 0.05], [h * 0.65, h * 0.42, h * 0.22, w * 0.65, h * 0.04]].forEach(([by, tipY, bw, reach, sway], i) => {
                const g = _flameGrad(ctx, 0, by, reach, tipY, [[0, 'rgba(180,20,0,0.9)'], [0.5, 'rgba(255,100,0,0.8)'], [1, 'rgba(255,200,0,0.5)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            });
            [[h * 0.22, h * 0.05, h * 0.12, w, -h * 0.08], [h * 0.78, h * 0.58, h * 0.12, w, h * 0.08]].forEach(([by, tipY, bw, reach, sway]) => {
                const g = _flameGrad(ctx, w * 0.65, by, reach, tipY, [[0, 'rgba(255,120,0,0.8)'], [0.5, 'rgba(255,220,50,0.6)'], [1, 'rgba(255,255,150,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, w * 0.65, by, reach, tipY, bw, sway, true);
            });
        },
        flame_teardrop: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const drops = [[w * 0.18, h * 0.35], [w * 0.4, h * 0.6], [w * 0.6, h * 0.25], [w * 0.78, h * 0.7], [w * 0.3, h * 0.15], [w * 0.65, h * 0.5]];
            drops.forEach(([dx, dy]) => {
                const r = Math.min(w, h) * 0.1;
                const g = ctx.createRadialGradient(dx, dy, 0, dx, dy, r * 1.4);
                g.addColorStop(0, 'rgba(255,255,200,0.95)');
                g.addColorStop(0.3, 'rgba(255,160,0,0.85)');
                g.addColorStop(0.7, 'rgba(220,50,0,0.6)');
                g.addColorStop(1, 'rgba(150,0,0,0)');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.arc(dx, dy, r, 0, Math.PI * 2); ctx.fill();
                ctx.beginPath();
                ctx.moveTo(dx - r * 0.5, dy);
                ctx.quadraticCurveTo(dx - r * 2.5, dy + r * 0.5, dx - r * 3.2, dy - r * 0.5);
                ctx.quadraticCurveTo(dx - r * 2.5, dy - r * 0.8, dx - r * 0.5, dy);
                ctx.closePath(); ctx.fill();
            });
        },
        flame_arrow: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            [[h * 0.5, 0.95], [h * 0.5, 0.75], [h * 0.5, 0.55]].forEach(([by, alpha], i) => {
                const bw = h * (0.38 - i * 0.08);
                const g = _flameGrad(ctx, 0, by, w * 0.9, by,
                    [[0, `rgba(${180 + i * 25},${20 + i * 30},0,${alpha})`], [0.5, `rgba(255,${100 + i * 40},0,${alpha * 0.7})`], [1, 'rgba(255,255,100,0)']]);
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.moveTo(0, by - bw);
                ctx.lineTo(w * 0.6, by - bw * 0.3);
                ctx.lineTo(w * 0.9, by);
                ctx.lineTo(w * 0.6, by + bw * 0.3);
                ctx.lineTo(0, by + bw);
                ctx.closePath(); ctx.fill();
            });
        },
        flame_layered: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const layers = [
                { count: 3, palette: [[0, 'rgba(140,0,0,0.8)'], [0.6, 'rgba(200,40,0,0.5)'], [1, 'rgba(255,80,0,0)']], wMult: 1.4, rMult: 0.95 },
                { count: 4, palette: [[0, 'rgba(220,60,0,0.9)'], [0.5, 'rgba(255,140,0,0.7)'], [1, 'rgba(255,200,0,0)']], wMult: 0.9, rMult: 0.88 },
                { count: 5, palette: [[0, 'rgba(255,180,0,0.95)'], [0.4, 'rgba(255,240,100,0.8)'], [1, 'rgba(255,255,200,0)']], wMult: 0.55, rMult: 0.78 },
            ];
            layers.forEach(({ count, palette, wMult, rMult }) => {
                for (let i = 0; i < count; i++) {
                    const by = h * (i + 0.5) / count + h * 0.05 * ((i * 7) % 3 - 1);
                    const tipY = by - h * (0.12 + (i % 3) * 0.05);
                    const bw = (h / count) * 0.4 * wMult;
                    const reach = w * rMult - h * (i % 3) * 0.03;
                    const sway = (i % 2 === 0 ? 1 : -1) * h * 0.025;
                    const g = _flameGrad(ctx, 0, by, reach, tipY, palette);
                    ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
                }
            });
        },
        flame_ribbon: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const waveH = h * 0.12;
            for (let pass = 2; pass >= 0; pass--) {
                const palette = pass === 0 ? [[0, 'rgba(255,240,150,0.95)'], [1, 'rgba(255,200,50,0.6)']] : pass === 1 ? [[0, 'rgba(255,140,0,0.9)'], [1, 'rgba(220,60,0,0.5)']] : [[0, 'rgba(180,20,0,0.8)'], [1, 'rgba(100,0,0,0.2)']];
                const expand = pass * waveH * 0.5;
                ctx.beginPath();
                ctx.moveTo(0, h * 0.5 + Math.sin(0) * h * 0.28 - waveH - expand);
                for (let x = 0; x <= w; x += 3) { const wavY = h * 0.5 + Math.sin((x / w) * Math.PI * 2.5) * h * 0.28; ctx.lineTo(x, wavY - waveH - expand); }
                for (let x = w; x >= 0; x -= 3) { const wavY = h * 0.5 + Math.sin((x / w) * Math.PI * 2.5) * h * 0.28; ctx.lineTo(x, wavY + waveH + expand); }
                ctx.closePath();
                const g = ctx.createLinearGradient(0, 0, w, 0);
                palette.forEach(([stop, color]) => g.addColorStop(stop, color));
                ctx.fillStyle = g; ctx.fill();
            }
        },
        flame_slash: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 7; i++) {
                const offset = (i / 7) * w * 1.6 - w * 0.3;
                const g = ctx.createLinearGradient(offset, 0, offset - h * 0.6, h);
                g.addColorStop(0, `rgba(${200 + Math.floor(i / 2) * 18},${20 + i * 12},0,0.85)`);
                g.addColorStop(0.5, `rgba(255,${80 + i * 20},0,0.6)`);
                g.addColorStop(1, 'rgba(255,220,50,0)');
                ctx.fillStyle = g;
                const tw = w * 0.08;
                ctx.beginPath();
                ctx.moveTo(offset, 0); ctx.lineTo(offset + tw, 0);
                ctx.lineTo(offset + tw - h * 0.6, h); ctx.lineTo(offset - h * 0.6, h);
                ctx.closePath(); ctx.fill();
            }
        },
        flame_overlay_subtle: (ctx, w, h) => {
            ctx.fillStyle = 'rgba(20,5,0,0.15)'; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.28;
            for (let i = 0; i < 5; i++) {
                const by = h * (i + 0.5) / 5;
                const tipY = by - h * 0.1;
                const bw = h * 0.08;
                const reach = w * (0.7 + (i % 3) * 0.1);
                const sway = (i % 2 === 0 ? 1 : -1) * h * 0.03;
                const g = _flameGrad(ctx, 0, by, reach, tipY, [[0, 'rgba(255,150,0,1)'], [0.6, 'rgba(255,220,100,0.5)'], [1, 'rgba(255,255,200,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            }
            ctx.globalAlpha = 1;
        },
        flame_core_glow: (ctx, w, h) => {
            ctx.fillStyle = '#070200'; ctx.fillRect(0, 0, w, h);
            [[h * 0.4, h * 0.1, h * 0.2, w * 0.9, -h * 0.06], [h * 0.6, h * 0.3, h * 0.18, w * 0.88, h * 0.05], [h * 0.25, h * 0.04, h * 0.14, w * 0.85, h * 0.03], [h * 0.75, h * 0.5, h * 0.14, w * 0.82, -h * 0.04]].forEach(([by, tipY, bw, reach, sway]) => {
                const g = _flameGrad(ctx, 0, by, reach, tipY,
                    [[0, 'rgba(255,255,220,0.98)'], [0.2, 'rgba(255,240,0,0.95)'], [0.5, 'rgba(255,120,0,0.75)'], [0.85, 'rgba(180,20,0,0.4)'], [1, 'rgba(100,0,0,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, sway, true);
            });
            const glow = ctx.createRadialGradient(w * 0.1, h * 0.5, 0, w * 0.1, h * 0.5, h * 0.4);
            glow.addColorStop(0, 'rgba(255,255,255,0.35)');
            glow.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = glow; ctx.fillRect(0, 0, w, h);
        },
        flame_smoke_edge: (ctx, w, h) => {
            ctx.fillStyle = '#111111'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 8; i++) {
                const sx = w * (i + 0.5) / 8 + ((i * 37) % 11 - 5) * w * 0.02;
                const swirl = (i % 2 === 0 ? 1 : -1) * w * 0.06;
                ctx.globalAlpha = 0.18 + (i % 3) * 0.06;
                const g = ctx.createRadialGradient(sx + swirl, h * 0.3, 0, sx + swirl, h * 0.3, h * 0.4);
                g.addColorStop(0, '#888888'); g.addColorStop(1, 'rgba(80,80,80,0)');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.ellipse(sx + swirl, h * 0.35, w * 0.1, h * 0.45, 0, 0, Math.PI * 2); ctx.fill();
            }
            ctx.globalAlpha = 1;
            ctx.fillStyle = '#ff6600';
            for (let i = 0; i < 14; i++) {
                const ex = ((i * 109) % 1000) / 1000 * w;
                const ey = h * 0.6 + ((i * 73) % 1000) / 1000 * h * 0.35;
                ctx.beginPath(); ctx.arc(ex, ey, 1.2, 0, Math.PI * 2); ctx.fill();
            }
        },
        tribal_flame_wide: (ctx, w, h) => {
            ctx.fillStyle = '#080201'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffffff';
            const points = [];
            const steps = 14;
            for (let i = 0; i <= steps; i++) {
                const x = (i / steps) * w;
                const isPeak = i % 2 === 0;
                const peakH = isPeak ? h * (0.1 + (i % 6) * 0.04) : h * (0.35 + (i % 4) * 0.05);
                points.push([x, peakH]);
            }
            ctx.beginPath();
            ctx.moveTo(0, h);
            points.forEach(([x, y]) => ctx.lineTo(x, y));
            ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
        },
        tribal_flame_fine: (ctx, w, h) => {
            ctx.fillStyle = '#080201'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#dddddd';
            const drawTribalShape = (bx, by, tipX, tipY, wid) => {
                ctx.beginPath();
                ctx.moveTo(bx, by - wid);
                const steps = 5;
                for (let i = 1; i <= steps; i++) {
                    const px = bx + (tipX - bx) * i / steps;
                    const py = by - wid * (1 - i / steps) + (by - tipY) * i / steps;
                    const jag = (i % 2 === 0 ? 1 : -1) * wid * 0.15;
                    ctx.lineTo(px, py + jag);
                }
                ctx.lineTo(tipX, tipY);
                for (let i = steps - 1; i >= 1; i--) {
                    const px = bx + (tipX - bx) * i / steps;
                    const py = by + wid * 0.3 * (1 - i / steps) + (by - tipY) * i / steps;
                    const jag = (i % 2 === 0 ? -1 : 1) * wid * 0.12;
                    ctx.lineTo(px, py + jag);
                }
                ctx.lineTo(bx, by + wid * 0.3);
                ctx.closePath(); ctx.fill();
            };
            [[0, h * 0.3, w * 0.9, h * 0.06, h * 0.055], [0, h * 0.55, w * 0.85, h * 0.28, h * 0.042], [0, h * 0.72, w * 0.80, h * 0.48, h * 0.038], [0, h * 0.15, w * 0.75, h * 0.02, h * 0.03], [0, h * 0.45, w * 0.72, h * 0.22, h * 0.035], [0, h * 0.62, w * 0.68, h * 0.38, h * 0.03], [0, h * 0.82, w * 0.65, h * 0.60, h * 0.032]].forEach(t => drawTribalShape(...t));
        },
        flame_flow_organic: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 5; i++) {
                const by = h * (i + 0.5) / 5;
                const curve1 = (i % 3 - 1) * h * 0.12;
                const curve2 = (((i + 1) % 3) - 1) * h * 0.08;
                const g = _flameGrad(ctx, 0, by, w * 0.9, by - h * 0.15,
                    [[0, 'rgba(180,30,0,0.85)'], [0.4, 'rgba(255,100,0,0.7)'], [0.75, 'rgba(255,200,30,0.5)'], [1, 'rgba(255,255,100,0)']]);
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.moveTo(0, by - h * 0.1);
                ctx.bezierCurveTo(w * 0.25, by - h * 0.1 + curve1, w * 0.6, by - h * 0.2 + curve2, w * 0.9, by - h * 0.15);
                ctx.bezierCurveTo(w * 0.6, by - h * 0.1 + curve2, w * 0.25, by + h * 0.05 + curve1, 0, by + h * 0.08);
                ctx.closePath(); ctx.fill();
            }
        },
        flame_flow_geometric: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            const segments = 8;
            for (let i = 0; i < segments; i++) {
                const x1 = (i / segments) * w;
                const x2 = ((i + 0.9) / segments) * w;
                const baseY = h * (0.3 + (i % 3) * 0.22);
                const tipY = baseY - h * (0.15 + (i % 4) * 0.06);
                const g = _flameGrad(ctx, x1, baseY, x2, tipY,
                    [[0, 'rgba(220,50,0,0.9)'], [0.5, 'rgba(255,160,0,0.7)'], [1, 'rgba(255,240,50,0)']]);
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.moveTo(x1, h); ctx.lineTo(x1, baseY); ctx.lineTo((x1 + x2) * 0.5, tipY); ctx.lineTo(x2, baseY); ctx.lineTo(x2, h);
                ctx.closePath(); ctx.fill();
            }
        },
        flame_fade_soft: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 5; i++) {
                const by = h * (i + 0.5) / 5;
                const tipY = by - h * 0.12;
                const bw = h * 0.11;
                const g = _flameGrad(ctx, 0, by, w, tipY,
                    [[0, 'rgba(220,60,0,0.95)'], [0.35, 'rgba(255,160,0,0.7)'], [0.65, 'rgba(255,220,50,0.35)'], [1, 'rgba(255,255,200,0)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, w, tipY, bw, (i % 2 === 0 ? 1 : -1) * h * 0.04, true);
            }
        },
        flame_fade_hard: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 5; i++) {
                const by = h * (i + 0.5) / 5;
                const tipY = by - h * 0.13;
                const reach = w * 0.6;
                const bw = h * 0.11;
                const g = _flameGrad(ctx, 0, by, reach, tipY,
                    [[0, 'rgba(200,30,0,0.95)'], [0.5, 'rgba(255,130,0,0.9)'], [0.85, 'rgba(255,220,50,0.8)'], [1, 'rgba(255,255,100,0.7)']]);
                ctx.fillStyle = g; _flameTongue(ctx, 0, by, reach, tipY, bw, (i % 2 === 0 ? 1 : -1) * h * 0.03, true);
            }
        },
        ember_trail: (ctx, w, h) => {
            ctx.fillStyle = '#060204'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 220; i++) {
                const ex = ((i * 137 + 27) % 1000) / 1000 * w;
                const ey = ((i * 89 + 13) % 1000) / 1000 * h;
                const er = 0.6 + (i % 5) * 0.5;
                const intensity = (i % 4) / 3;
                ctx.fillStyle = intensity > 0.6
                    ? `rgba(255,${200 + Math.floor(intensity * 55)},${Math.floor(intensity * 100)},${0.5 + intensity * 0.5})`
                    : `rgba(${180 + Math.floor(intensity * 75)},${40 + Math.floor(intensity * 80)},0,${0.3 + intensity * 0.5})`;
                ctx.shadowBlur = er * 3; ctx.shadowColor = '#ff8800';
                ctx.beginPath(); ctx.arc(ex, ey, er, 0, Math.PI * 2); ctx.fill();
            }
            ctx.shadowBlur = 0;
        },
        smoke_wisp: (ctx, w, h) => {
            ctx.fillStyle = '#111111'; ctx.fillRect(0, 0, w, h);
            for (let i = 0; i < 6; i++) {
                const bx = w * (i + 0.5) / 6;
                const drift = (i % 3 - 1) * w * 0.08;
                const g = ctx.createLinearGradient(bx, h, bx + drift, 0);
                g.addColorStop(0, 'rgba(100,100,100,0.4)'); g.addColorStop(0.5, 'rgba(130,130,130,0.2)'); g.addColorStop(1, 'rgba(80,80,80,0)');
                ctx.fillStyle = g;
                ctx.globalAlpha = 0.55;
                ctx.beginPath();
                ctx.moveTo(bx - w * 0.04, h);
                ctx.bezierCurveTo(bx - w * 0.02 + drift * 0.3, h * 0.7, bx + drift * 0.6 + w * 0.05, h * 0.4, bx + drift, 0);
                ctx.bezierCurveTo(bx + drift - w * 0.06, h * 0.4, bx - drift * 0.3 - w * 0.04, h * 0.7, bx + w * 0.04, h);
                ctx.closePath(); ctx.fill();
            }
            ctx.globalAlpha = 1;
        },

        // ═══════════════════════════════════════════════════════
        // REACTIVE SHIMMER PATTERNS - Pattern-Pop / Pattern-Reactive masks
        // Each swatch shows the shimmer mask: dark=primary base, bright=secondary base
        // ═══════════════════════════════════════════════════════
        reactive_iridescent_flake: (ctx, w, h) => {
            ctx.fillStyle = '#10101e'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(0xF1A7);
            const tiers = [[4, 18, 1.0], [2, 40, 0.85], [1, 80, 0.7]];
            for (const [radius, count, bright] of tiers) {
                for (let i = 0; i < count; i++) {
                    const fx = rng() * w, fy = rng() * h;
                    const intensity = bright * (0.6 + rng() * 0.4);
                    const r = Math.max(1, radius);
                    const grd = ctx.createRadialGradient(fx, fy, 0, fx, fy, r * 2.5);
                    grd.addColorStop(0, `rgba(${Math.round(200 * intensity)},${Math.round(210 * intensity)},255,${intensity})`);
                    grd.addColorStop(0.5, `rgba(150,160,220,${intensity * 0.4})`);
                    grd.addColorStop(1, 'rgba(0,0,0,0)');
                    ctx.fillStyle = grd;
                    ctx.beginPath(); ctx.arc(fx, fy, r * 2.5, 0, Math.PI * 2); ctx.fill();
                }
            }
            const ag = ctx.createLinearGradient(0, 0, w, h);
            ag.addColorStop(0, 'rgba(160,170,220,0.06)'); ag.addColorStop(0.5, 'rgba(200,210,255,0.10)'); ag.addColorStop(1, 'rgba(160,170,220,0.06)');
            ctx.fillStyle = ag; ctx.fillRect(0, 0, w, h);
        },
        reactive_pearl_shift: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const configs = [[6, 0, 0.28], [9, 90, 0.22], [14, 37, 0.18], [20, 72, 0.14], [4, 18, 0.12], [28, 55, 0.08]];
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const nx = (px / w) * 2 - 1, ny = (py / h) * 2 - 1;
                    let val = 0;
                    for (const [freq, deg, weight] of configs) {
                        const a = deg * Math.PI / 180;
                        val += (Math.sin((nx * Math.cos(a) + ny * Math.sin(a)) * Math.PI * freq) * 0.5 + 0.5) * weight;
                    }
                    val = Math.pow(Math.max(0, Math.min(1, val)), 0.6);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.round(30 + val * 100); id.data[idx + 1] = Math.round(40 + val * 120); id.data[idx + 2] = Math.round(80 + val * 175); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_candy_depth: (ctx, w, h) => {
            const rng = _seededRng(0xCAA7);
            const pts = Array.from({ length: 10 }, () => [rng() * w, rng() * h]);
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let dMin = Infinity;
                    for (const [cx, cy] of pts) dMin = Math.min(dMin, Math.sqrt((px - cx) ** 2 + (py - cy) ** 2));
                    const val = Math.pow(Math.max(0, 1 - dMin / (Math.min(w, h) * 0.32)), 2.2);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.round(20 + val * 180); id.data[idx + 1] = Math.round(5 + val * 30); id.data[idx + 2] = Math.round(30 + val * 80); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_chrome_veil: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                const ny = (py / h) * 2 - 1;
                let val = Math.sin(ny * Math.PI * 11) * 0.55 * 0.5 + 0.55 * 0.5 + Math.sin(ny * Math.PI * 2.5) * 0.30 * 0.5 + 0.30 * 0.5 + Math.sin(ny * Math.PI * 38) * 0.15 * 0.5 + 0.15 * 0.5;
                val = val > 0.5 ? Math.pow((val - 0.5) * 2, 0.7) * 0.5 + 0.5 : 0.5 - Math.pow((0.5 - val) * 2, 0.7) * 0.5;
                val = Math.max(0, Math.min(1, val));
                for (let px = 0; px < w; px++) {
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.round(20 + val * 200); id.data[idx + 1] = Math.round(25 + val * 210); id.data[idx + 2] = Math.round(40 + val * 215); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_spectra_ripple: (ctx, w, h) => {
            const sources = [[w * 0.35, h * 0.4, 16], [w * 0.65, h * 0.6, 12], [w * 0.5, h * 0.5, 8]];
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let sum = 0;
                    for (const [sx, sy, freq] of sources) {
                        const nx = (px - sx) / w * 2, ny = (py - sy) / h * 2;
                        sum += Math.sin(Math.sqrt(nx * nx + ny * ny) * Math.PI * freq) * 0.5 + 0.5;
                    }
                    let val = Math.sin(Math.max(0, Math.min(1, sum / 3)) * Math.PI * 2.5) * 0.5 + 0.5;
                    const [r, g, b] = _hslToRgb(val * 300, 80, 20 + val * 45);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_micro_weave: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                const hT = Math.sin(((py / h) * 2 - 1) * Math.PI * 32) * 0.5 + 0.5;
                for (let px = 0; px < w; px++) {
                    const vT = Math.sin(((px / w) * 2 - 1) * Math.PI * 32) * 0.5 + 0.5;
                    const weave = Math.pow(hT * vT, 0.5);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.round(15 + weave * 160); id.data[idx + 1] = Math.round(12 + weave * 145); id.data[idx + 2] = Math.round(10 + weave * 80); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_depth_cell: (ctx, w, h) => {
            const rng = _seededRng(0xDEF1);
            const pts = Array.from({ length: 7 }, () => [rng() * w, rng() * h]);
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    let d1 = Infinity, d2 = Infinity;
                    for (const [cx, cy] of pts) {
                        const d = Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
                        if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
                    }
                    const val = Math.pow(Math.min(1, (d2 - d1) / (Math.min(w, h) * 0.12)), 3);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.round(8 + val * 80); id.data[idx + 1] = Math.round(10 + val * 150); id.data[idx + 2] = Math.round(20 + val * 220); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_shimmer_mist: (ctx, w, h) => {
            ctx.fillStyle = '#060608'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(0x9A3B);
            const nPts = Math.floor(w * h * 0.0008);
            for (let i = 0; i < nPts; i++) {
                const px = rng() * w, py = rng() * h, r = 1 + rng() * 5, bright = 0.7 + rng() * 0.3;
                const grd = ctx.createRadialGradient(px, py, 0, px, py, r * 2);
                grd.addColorStop(0, `rgba(255,255,255,${bright})`);
                grd.addColorStop(0.4, `rgba(180,190,255,${bright * 0.4})`);
                grd.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = grd;
                ctx.beginPath(); ctx.arc(px, py, r * 2, 0, Math.PI * 2); ctx.fill();
            }
        },
        reactive_oil_slick: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const ny = (py / h) * 2 - 1, nx = (px / w) * 2 - 1;
                    let flow = Math.sin((ny * 3.2 + nx * 1.8) * Math.PI) * 0.35
                        + Math.sin((ny * 1.7 - nx * 2.9) * Math.PI + 1.1) * 0.30
                        + Math.sin((ny * 5.1 + nx * 0.9) * Math.PI + 2.3) * 0.20
                        + Math.sin((ny * 2.3 - nx * 3.7) * Math.PI + 0.7) * 0.15;
                    flow = Math.max(0, Math.min(1, (flow + 1) * 0.5));
                    const banded = Math.sin(flow * Math.PI * 4.5) * 0.4 + flow * 0.6;
                    const val = Math.max(0, Math.min(1, (banded + 0.4) / 1.4));
                    const [r, g, b] = _hslToRgb((val * 360 + 200) % 360, 90, 12 + val * 52);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        reactive_wave_moire: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const a1 = 12 * Math.PI / 180, a2 = 18 * Math.PI / 180;
            for (let py = 0; py < h; py++) {
                const ny = (py / h) * 2 - 1;
                for (let px = 0; px < w; px++) {
                    const nx = (px / w) * 2 - 1;
                    const w1 = Math.sin((nx * Math.cos(a1) + ny * Math.sin(a1)) * Math.PI * 18);
                    const w2 = Math.sin((nx * Math.cos(a2) + ny * Math.sin(a2)) * Math.PI * 19.5);
                    const val = Math.max(0, Math.min(1, w1 * w2 * 0.5 + 0.5));
                    const idx = (py * w + px) * 4;
                    id.data[idx] = Math.round(10 + val * 80); id.data[idx + 1] = Math.round(30 + val * 200); id.data[idx + 2] = Math.round(15 + val * 160); id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
    };


    // Image-based pattern swatch (swatch_image from UI data)
    const finishForImage = [...BASES, ...PATTERNS, ...MONOLITHICS].find(f => f.id === finishId);
    if (finishForImage && finishForImage.swatch_image) {
        renderImagePatternSwatch(ctx, w, h, finishForImage.swatch_image);
        return;
    }

    // Look up render function
    const fn = (window._fusionSwatchRenderers && window._fusionSwatchRenderers[finishId]) || baseFns[finishId] || patternFns[finishId] || monoFns[finishId];
    if (fn) {
        fn(ctx, w, h);
    } else if (finishId === 'none') {
        // Transparent checkerboard
        for (let py = 0; py < h; py += 8) {
            for (let px = 0; px < w; px += 8) {
                ctx.fillStyle = ((px / 8 + py / 8) % 2) ? '#333' : '#222';
                ctx.fillRect(px, py, 8, 8);
            }
        }
        ctx.fillStyle = 'rgba(255,255,255,0.15)'; ctx.font = '10px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText('Base Only', w / 2, h / 2 + 3);

    } else {
        // Smart auto-renderer for finishes without custom renderers
        const finish = [...BASES, ...PATTERNS, ...MONOLITHICS].find(f => f.id === finishId);
        if (finish) {
            // Determine category
            const isBase = BASES.some(f => f.id === finishId);
            const isPattern = PATTERNS.some(f => f.id === finishId);
            const isSpecial = MONOLITHICS.some(f => f.id === finishId);

            // Seeded hash from finishId for consistent variation
            let hash = 0;
            for (let i = 0; i < finishId.length; i++) {
                hash = ((hash << 5) - hash + finishId.charCodeAt(i)) | 0;
            }
            const rng = _seededRng(Math.abs(hash));

            // Parse swatch color
            const sw = finish.swatch || '#888888';
            const cr = parseInt(sw.slice(1, 3), 16) || 128;
            const cg = parseInt(sw.slice(3, 5), 16) || 128;
            const cb = parseInt(sw.slice(5, 7), 16) || 128;

            if (isBase) {
                // Base material preview: gradient + texture based on visual cues from name
                const isDark = (cr + cg + cb) < 200;
                const isBright = (cr + cg + cb) > 500;
                const isMetallic = finishId.includes('metal') || finishId.includes('chrome') || finishId.includes('titanium') ||
                    finishId.includes('steel') || finishId.includes('aluminum') || finishId.includes('gold') ||
                    finishId.includes('copper') || finishId.includes('iron') || finishId.includes('tungsten') ||
                    finishId.includes('platinum') || finishId.includes('cobalt') || finishId.includes('bronze');
                const isRough = finishId.includes('matte') || finishId.includes('flat') || finishId.includes('sandblast') ||
                    finishId.includes('rugged') || finishId.includes('primer') || finishId.includes('concrete') ||
                    finishId.includes('worn') || finishId.includes('grind');
                const isGlossy = finishId.includes('gloss') || finishId.includes('piano') || finishId.includes('wet') ||
                    finishId.includes('ceramic') || finishId.includes('enamel') || finishId.includes('crystal') ||
                    finishId.includes('diamond') || finishId.includes('porcelain');

                // Gradient background
                const g = ctx.createLinearGradient(0, 0, w, h);
                const vary = 15 + Math.floor(rng() * 20);
                g.addColorStop(0, `rgb(${Math.max(0, cr - vary)},${Math.max(0, cg - vary)},${Math.max(0, cb - vary)})`);
                g.addColorStop(0.4, `rgb(${Math.min(255, cr + vary)},${Math.min(255, cg + vary)},${Math.min(255, cb + vary)})`);
                g.addColorStop(0.7, `rgb(${cr},${cg},${cb})`);
                g.addColorStop(1, `rgb(${Math.max(0, cr - vary * 0.7)},${Math.max(0, cg - vary * 0.7)},${Math.max(0, cb - vary * 0.7)})`);
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);

                // Add texture
                const id = ctx.getImageData(0, 0, w, h);
                for (let i = 0; i < id.data.length; i += 4) {
                    if (isMetallic) {
                        // Metallic sparkle
                        const spark = rng() > 0.88 ? 30 + rng() * 40 : (rng() - 0.5) * 20;
                        id.data[i] += spark; id.data[i + 1] += spark; id.data[i + 2] += spark;
                    } else if (isRough) {
                        // Rough noise
                        const n = (rng() - 0.5) * 35;
                        id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
                    } else {
                        // Subtle variation
                        const n = (rng() - 0.5) * 12;
                        id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
                    }
                }
                ctx.putImageData(id, 0, 0);

                // Glossy highlight band
                if (isGlossy || (!isRough && rng() > 0.4)) {
                    const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
                    const hlStr = isGlossy ? 0.18 : 0.08;
                    hl.addColorStop(0, 'rgba(255,255,255,0)');
                    hl.addColorStop(0.35, `rgba(255,255,255,${hlStr})`);
                    hl.addColorStop(0.55, `rgba(255,255,255,${hlStr})`);
                    hl.addColorStop(1, 'rgba(255,255,255,0)');
                    ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
                }

            } else if (isPattern) {
                // Pattern preview: generate a procedural texture hint
                ctx.fillStyle = `rgb(${cr},${cg},${cb})`; ctx.fillRect(0, 0, w, h);

                const pType = Math.floor(rng() * 8);
                const lineColor = `rgba(${Math.min(255, cr + 60)},${Math.min(255, cg + 60)},${Math.min(255, cb + 60)},0.6)`;
                const darkColor = `rgba(${Math.max(0, cr - 40)},${Math.max(0, cg - 40)},${Math.max(0, cb - 40)},0.5)`;
                ctx.strokeStyle = lineColor; ctx.lineWidth = 1;

                if (finishId.includes('stripe') || finishId.includes('line') || finishId.includes('pin')) {
                    // Stripes
                    const spacing = 4 + Math.floor(rng() * 4);
                    for (let x = 0; x < w; x += spacing) {
                        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
                    }
                } else if (finishId.includes('dot') || finishId.includes('halftone') || finishId.includes('flake') || finishId.includes('star')) {
                    // Dots/particles
                    for (let i = 0; i < 30; i++) {
                        const dx = rng() * w, dy = rng() * h, dr = 1 + rng() * 2;
                        ctx.fillStyle = lineColor;
                        ctx.beginPath(); ctx.arc(dx, dy, dr, 0, Math.PI * 2); ctx.fill();
                    }
                } else if (finishId.includes('wave') || finishId.includes('ripple') || finishId.includes('swirl')) {
                    // Waves
                    for (let y = 4; y < h; y += 6) {
                        ctx.beginPath();
                        for (let x = 0; x < w; x++) {
                            ctx.lineTo(x, y + Math.sin(x * 0.3 + y * 0.1) * 3);
                        }
                        ctx.stroke();
                    }
                } else if (finishId.includes('hex') || finishId.includes('scale') || finishId.includes('mesh') || finishId.includes('grid')) {
                    // Grid/hex
                    const sp = 6 + Math.floor(rng() * 4);
                    for (let x = 0; x < w; x += sp) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
                    for (let y = 0; y < h; y += sp) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
                } else if (finishId.includes('crack') || finishId.includes('shatter') || finishId.includes('lightning') || finishId.includes('bolt')) {
                    // Cracks/lightning
                    for (let i = 0; i < 5; i++) {
                        let cx = rng() * w, cy = 0;
                        ctx.beginPath(); ctx.moveTo(cx, cy);
                        while (cy < h) {
                            cx += (rng() - 0.5) * 12; cy += 2 + rng() * 4;
                            ctx.lineTo(cx, cy);
                        }
                        ctx.stroke();
                    }
                } else if (finishId.includes('camo') || finishId.includes('splat')) {
                    // Camo blobs
                    for (let i = 0; i < 12; i++) {
                        const bx = rng() * w, by = rng() * h;
                        ctx.fillStyle = i % 2 ? lineColor : darkColor;
                        ctx.beginPath();
                        ctx.ellipse(bx, by, 3 + rng() * 6, 2 + rng() * 5, rng() * Math.PI, 0, Math.PI * 2);
                        ctx.fill();
                    }
                } else if (finishId.includes('weave') || finishId.includes('fiber') || finishId.includes('kevlar') || finishId.includes('carbon')) {
                    // Weave pattern
                    const sp = 4;
                    ctx.strokeStyle = darkColor;
                    for (let y = 0; y < h; y += sp) {
                        for (let x = 0; x < w; x += sp) {
                            if ((Math.floor(x / sp) + Math.floor(y / sp)) % 2) {
                                ctx.fillStyle = lineColor; ctx.fillRect(x, y, sp - 1, sp - 1);
                            }
                        }
                    }
                } else {
                    // Generic: diagonal lines + noise
                    for (let i = -h; i < w + h; i += 6) {
                        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i + h, h); ctx.stroke();
                    }
                    const id = ctx.getImageData(0, 0, w, h);
                    for (let i = 0; i < id.data.length; i += 4) {
                        const n = (rng() - 0.5) * 20;
                        id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
                    }
                    ctx.putImageData(id, 0, 0);
                }

            } else if (isSpecial) {
                // === COLOR MONOLITHIC RENDERERS (clr_, grad_, cs_, mc_ prefixes) ===
                const isClr = finishId.startsWith('clr_');
                const isGrad = finishId.startsWith('grad_') || finishId.startsWith('gradm_') || finishId.startsWith('grad3_');
                const _csMono = MONOLITHICS.find(m => m.id === finishId);
                const isCS = finishId.startsWith('cs_') && _csMono && _csMono.swatch2;
                const isMC = finishId.startsWith('mc_') && _csMono && _csMono.clrCat;
                const isGhost = finishId.startsWith('ghostg_');

                if (isClr) {
                    // Solid color + material: parse color from CLR_PALETTE, simulate material
                    const parts = finishId.replace('clr_', '').split('_');
                    const matKey = parts.pop(); // last segment is material
                    const clrKey = parts.join('_'); // rest is color key
                    const rgb = CLR_PALETTE[clrKey] || [128, 128, 128];
                    const [rc, gc, bc] = rgb;
                    const id = ctx.createImageData(w, h);

                    // Material-specific rendering
                    const isMetal = matKey === 'metallic' || matKey === 'chrome';
                    const isPearl = matKey === 'pearl' || matKey === 'candy';
                    const isMatte2 = matKey === 'matte' || matKey === 'flat';

                    for (let py = 0; py < h; py++) {
                        for (let px = 0; px < w; px++) {
                            const idx = (py * w + px) * 4;
                            // Car panel curved highlight simulation
                            const nx = px / w - 0.35, ny = py / h - 0.3;
                            const highlight = Math.max(0, 1 - (nx * nx * 3 + ny * ny * 4)) * 0.3;

                            let r = rc, g = gc, b = bc;

                            if (isMetal) {
                                // Metallic sparkle + strong highlight
                                const spark = (rng() > 0.85) ? 25 + rng() * 35 : 0;
                                r = Math.min(255, r + highlight * 120 + spark);
                                g = Math.min(255, g + highlight * 120 + spark);
                                b = Math.min(255, b + highlight * 120 + spark);
                            } else if (isPearl) {
                                // Pearlescent color shift in highlight
                                const shift = highlight * 40;
                                r = Math.min(255, r + shift * 1.2);
                                g = Math.min(255, g + shift * 0.7);
                                b = Math.min(255, b + shift * 1.5);
                            } else if (isMatte2) {
                                // Matte: no highlight, subtle noise
                                const n = (rng() - 0.5) * 12;
                                r += n; g += n; b += n;
                            } else {
                                // Gloss/satin: smooth highlight
                                r = Math.min(255, r + highlight * 80);
                                g = Math.min(255, g + highlight * 80);
                                b = Math.min(255, b + highlight * 80);
                            }

                            id.data[idx] = Math.max(0, Math.min(255, r));
                            id.data[idx + 1] = Math.max(0, Math.min(255, g));
                            id.data[idx + 2] = Math.max(0, Math.min(255, b));
                            id.data[idx + 3] = 255;
                        }
                    }
                    ctx.putImageData(id, 0, 0);

                } else if (isGrad) {
                    // Gradient renderer - supports 2-color, mirror (A→B→A), and 3-color
                    const mono = MONOLITHICS.find(m => m.id === finishId);
                    const _parseHex = s => [parseInt(s.slice(1, 3), 16) || 128, parseInt(s.slice(3, 5), 16) || 128, parseInt(s.slice(5, 7), 16) || 128];
                    const c1 = _parseHex(mono ? mono.swatch : '#888');
                    const c2 = _parseHex(mono && mono.swatch2 ? mono.swatch2 : '#444');
                    const c3 = mono && mono.swatch3 ? _parseHex(mono.swatch3) : null;
                    const isMirror = mono && mono.gradType === 'mirror';
                    const is3Color = mono && mono.gradType === '3color';

                    const isRadial = finishId.endsWith('vortex');
                    const isDiag = finishId.endsWith('_diag');
                    const isHoriz = finishId.endsWith('_h');

                    const id = ctx.createImageData(w, h);
                    for (let py = 0; py < h; py++) {
                        for (let px = 0; px < w; px++) {
                            let t;
                            if (isRadial) {
                                const dx = px / w - 0.5, dy = py / h - 0.5;
                                t = Math.min(1, Math.sqrt(dx * dx + dy * dy) * 2.2);
                            } else if (isDiag) {
                                t = (px / w + py / h) / 2;
                            } else if (isHoriz) {
                                t = px / w;
                            } else {
                                t = py / h;
                            }

                            let r, g, b;
                            if (isMirror) {
                                // A→B→A: remap t so 0→0.5 goes A→B, 0.5→1 goes B→A
                                const mt = t < 0.5 ? t * 2 : (1 - t) * 2;
                                r = c1[0] + (c2[0] - c1[0]) * mt;
                                g = c1[1] + (c2[1] - c1[1]) * mt;
                                b = c1[2] + (c2[2] - c1[2]) * mt;
                            } else if (is3Color && c3) {
                                // 3-color: A→B at t<0.5, B→C at t>=0.5
                                if (t < 0.5) {
                                    const st = t * 2;
                                    r = c1[0] + (c2[0] - c1[0]) * st;
                                    g = c1[1] + (c2[1] - c1[1]) * st;
                                    b = c1[2] + (c2[2] - c1[2]) * st;
                                } else {
                                    const st = (t - 0.5) * 2;
                                    r = c2[0] + (c3[0] - c2[0]) * st;
                                    g = c2[1] + (c3[1] - c2[1]) * st;
                                    b = c2[2] + (c3[2] - c2[2]) * st;
                                }
                            } else {
                                // Standard 2-color
                                r = c1[0] + (c2[0] - c1[0]) * t;
                                g = c1[1] + (c2[1] - c1[1]) * t;
                                b = c1[2] + (c2[2] - c1[2]) * t;
                            }

                            // Car panel highlight overlay
                            const nx = px / w - 0.35, ny = py / h - 0.3;
                            const hl = Math.max(0, 1 - (nx * nx * 3 + ny * ny * 4)) * 0.15;

                            const idx2 = (py * w + px) * 4;
                            id.data[idx2] = Math.min(255, Math.max(0, r + hl * 100));
                            id.data[idx2 + 1] = Math.min(255, Math.max(0, g + hl * 100));
                            id.data[idx2 + 2] = Math.min(255, Math.max(0, b + hl * 100));
                            id.data[idx2 + 3] = 255;
                        }
                    }
                    ctx.putImageData(id, 0, 0);

                } else if (isCS) {
                    // Color-shift duo: two-tone angle-dependent shift
                    const mono = MONOLITHICS.find(m => m.id === finishId);
                    const sw1 = mono ? mono.swatch : '#888';
                    const sw2 = mono && mono.swatch2 ? mono.swatch2 : '#444';
                    const r1 = parseInt(sw1.slice(1, 3), 16) || 128, g1 = parseInt(sw1.slice(3, 5), 16) || 128, b1 = parseInt(sw1.slice(5, 7), 16) || 128;
                    const r2 = parseInt(sw2.slice(1, 3), 16) || 128, g2 = parseInt(sw2.slice(3, 5), 16) || 128, b2 = parseInt(sw2.slice(5, 7), 16) || 128;

                    const id = ctx.createImageData(w, h);
                    const noise = _simpleNoise2D(w, h, [8, 16, 32], [0.5, 0.3, 0.2], rng);
                    for (let py = 0; py < h; py++) {
                        for (let px = 0; px < w; px++) {
                            // Angle-proxy: combine diagonal + noise for color shift
                            const diag = (px / w * 0.6 + py / h * 0.4);
                            const n = noise[py * w + px] * 0.3;
                            let t = Math.max(0, Math.min(1, diag + n));
                            // Smooth cubic
                            t = t * t * (3 - 2 * t);
                            // Car panel highlight
                            const nx = px / w - 0.35, ny = py / h - 0.3;
                            const hl = Math.max(0, 1 - (nx * nx * 3 + ny * ny * 4)) * 0.2;

                            const idx2 = (py * w + px) * 4;
                            id.data[idx2] = Math.min(255, r1 + (r2 - r1) * t + hl * 80);
                            id.data[idx2 + 1] = Math.min(255, g1 + (g2 - g1) * t + hl * 80);
                            id.data[idx2 + 2] = Math.min(255, b1 + (b2 - b1) * t + hl * 80);
                            id.data[idx2 + 3] = 255;
                        }
                    }
                    ctx.putImageData(id, 0, 0);

                } else if (isMC) {
                    // Multi-color pattern: noise-driven splotches with REAL palette colors
                    const mono = MONOLITHICS.find(m => m.id === finishId);
                    const sw1 = mono ? mono.swatch : '#888';
                    const sw2 = mono && mono.swatch2 ? mono.swatch2 : '#666';
                    const sw3 = mono && mono.swatch3 ? mono.swatch3 : '#444';
                    const rc2 = parseInt(sw1.slice(1, 3), 16) || 128, gc2 = parseInt(sw1.slice(3, 5), 16) || 128, bc2 = parseInt(sw1.slice(5, 7), 16) || 128;
                    const r3 = parseInt(sw2.slice(1, 3), 16) || 128, g3 = parseInt(sw2.slice(3, 5), 16) || 128, b3 = parseInt(sw2.slice(5, 7), 16) || 128;
                    const r4 = parseInt(sw3.slice(1, 3), 16) || 128, g4 = parseInt(sw3.slice(3, 5), 16) || 128, b4 = parseInt(sw3.slice(5, 7), 16) || 128;

                    const isCamo = finishId.includes('camo');
                    const isMarble = finishId.includes('marble');
                    const isSplatter = finishId.includes('splatter');

                    const id = ctx.createImageData(w, h);
                    const noise1 = _simpleNoise2D(w, h, [6, 12, 24], [0.5, 0.3, 0.2], rng);
                    const noise2 = _simpleNoise2D(w, h, [8, 16], [0.6, 0.4], rng);

                    for (let py = 0; py < h; py++) {
                        for (let px = 0; px < w; px++) {
                            const n1 = noise1[py * w + px];
                            const n2 = noise2[py * w + px];
                            let r, g, b;

                            if (isCamo) {
                                // Hard-edged color zones
                                if (n1 > 0.2) { r = rc2; g = gc2; b = bc2; }
                                else if (n1 > -0.1) { r = r3; g = g3; b = b3; }
                                else { r = r4; g = g4; b = b4; }
                            } else if (isMarble) {
                                // Smooth veiny blending
                                const t = Math.sin(n1 * 8) * 0.5 + 0.5;
                                r = rc2 + (r3 - rc2) * t; g = gc2 + (g3 - gc2) * t; b = bc2 + (b3 - bc2) * t;
                            } else if (isSplatter) {
                                // Base + splatter spots
                                r = rc2; g = gc2; b = bc2;
                                if (n1 > 0.35) { r = r3; g = g3; b = b3; }
                                if (n2 > 0.4) { r = r4; g = g4; b = b4; }
                            } else {
                                // Swirl: smooth noise blend
                                const t = n1 * 0.5 + 0.5;
                                r = rc2 * (1 - t) + r3 * t; g = gc2 * (1 - t) + g3 * t; b = bc2 * (1 - t) + b3 * t;
                                const t2 = n2 * 0.3;
                                r += t2 * 20; g += t2 * 15; b += t2 * 10;
                            }

                            // Car panel highlight
                            const nx = px / w - 0.35, ny = py / h - 0.3;
                            const hl = Math.max(0, 1 - (nx * nx * 3 + ny * ny * 4)) * 0.12;
                            const idx2 = (py * w + px) * 4;
                            id.data[idx2] = Math.max(0, Math.min(255, r + hl * 80));
                            id.data[idx2 + 1] = Math.max(0, Math.min(255, g + hl * 80));
                            id.data[idx2 + 2] = Math.max(0, Math.min(255, b + hl * 80));
                            id.data[idx2 + 3] = 255;
                        }
                    }
                    ctx.putImageData(id, 0, 0);

                    // === GHOST GRADIENT RENDERER ===
                } else if (isGhost) {
                    // Ghost gradient: base gradient + subtle ghosted pattern overlay
                    const mono = MONOLITHICS.find(m => m.id === finishId);
                    const _parseHex = s => [parseInt(s.slice(1, 3), 16) || 128, parseInt(s.slice(3, 5), 16) || 128, parseInt(s.slice(5, 7), 16) || 128];
                    const c1 = _parseHex(mono ? mono.swatch : '#888');
                    const c2 = _parseHex(mono && mono.swatch2 ? mono.swatch2 : '#444');
                    const ghostPat = mono ? mono.ghostPattern : null;

                    // Inline ghost pattern intensity (returns brightness modifier)
                    function _ghostIntensity(pat, px, py, w2, h2) {
                        switch (pat) {
                            case 'carbon_fiber': { const s = 5; return ((Math.floor(px / s) % 2) !== (Math.floor(py / s) % 2)) ? 0.08 : -0.04; }
                            case 'checkered_flag': { const s = 7; return ((Math.floor(px / s) % 2) !== (Math.floor(py / s) % 2)) ? 0.07 : -0.07; }
                            case 'circuit_board': return (px % 9 === 0 || py % 9 === 0) ? 0.09 : ((px % 9 === 4 && py % 9 < 3) ? 0.05 : -0.02);
                            case 'diamond_plate': { const dx = (px % 10) - 5, dy = (py % 10) - 5; return (Math.abs(dx) + Math.abs(dy) < 4) ? 0.08 : -0.03; }
                            case 'hex_mesh': { const hx = px % 12, hy = py % 7; return (hx < 2 || (hy < 2 && hx > 4 && hx < 8)) ? 0.09 : -0.02; }
                            case 'skull': { const sx = (px % 14) - 7, sy = (py % 14) - 7; return (Math.abs(sx) < 3 && Math.abs(sy) < 5 || Math.abs(sx) < 5 && Math.abs(sy) < 2) ? 0.07 : -0.02; }
                            case 'tribal_flame': { const ty = py + Math.sin(px / 7) * 3.5; return (Math.floor(ty / 5) % 2 === 0) ? 0.06 : -0.04; }
                            case 'lightning': return (Math.abs(px - w2 / 2 - Math.sin(py / 3.5) * 7) < 2) ? 0.11 : -0.02;
                            case 'fractal': { const fx = px * 3.2 / w2 - 1.8, fy = py * 3.2 / h2 - 1.6; let zr = 0, zi = 0, i = 0; while (zr * zr + zi * zi < 4 && i < 10) { const t2 = zr * zr - zi * zi + fx; zi = 2 * zr * zi + fy; zr = t2; i++; } return i < 10 ? 0.07 * (i / 10) : -0.03; }
                            case '_broken_dragon_scale': { const sx2 = (px + (Math.floor(py / 7) % 2) * 5) % 10, sy2 = py % 7; return (sx2 * sx2 / 25 + sy2 * sy2 / 12 < 1) ? 0.07 : -0.03; }
                            case 'racing_stripe': return (px > w2 * 0.33 && px < w2 * 0.67) ? ((px > w2 * 0.38 && px < w2 * 0.62) ? 0.08 : 0.04) : -0.03;
                            case 'tron': return (px % 14 < 1 || py % 14 < 1) ? 0.10 : -0.02;
                            case 'celtic_knot': { const ckx = px % 14, cky = py % 14; return ((ckx > 3 && ckx < 6) || (cky > 3 && cky < 6) || (ckx > 9 && ckx < 12) || (cky > 9 && cky < 12)) ? 0.06 : -0.02; }
                            case 'spiderweb': { const dx2 = px - w2 / 2, dy2 = py - h2 / 2, r = Math.sqrt(dx2 * dx2 + dy2 * dy2); return (r % 7 < 1 || Math.abs(Math.atan2(dy2, dx2) * 6 / Math.PI % 1) < 0.14) ? 0.08 : -0.02; }
                            default: return 0;
                        }
                    }

                    const id = ctx.createImageData(w, h);
                    for (let py = 0; py < h; py++) {
                        for (let px = 0; px < w; px++) {
                            const t = py / h;
                            let r = c1[0] + (c2[0] - c1[0]) * t;
                            let g = c1[1] + (c2[1] - c1[1]) * t;
                            let b = c1[2] + (c2[2] - c1[2]) * t;

                            // Ghost pattern overlay
                            if (ghostPat) {
                                const gm = _ghostIntensity(ghostPat, px, py, w, h) * 110;
                                r += gm; g += gm; b += gm;
                            }

                            // Car panel highlight
                            const nx = px / w - 0.35, ny = py / h - 0.3;
                            const hl = Math.max(0, 1 - (nx * nx * 3 + ny * ny * 4)) * 0.15;
                            const idx2 = (py * w + px) * 4;
                            id.data[idx2] = Math.min(255, Math.max(0, r + hl * 100));
                            id.data[idx2 + 1] = Math.min(255, Math.max(0, g + hl * 100));
                            id.data[idx2 + 2] = Math.min(255, Math.max(0, b + hl * 100));
                            id.data[idx2 + 3] = 255;
                        }
                    }
                    ctx.putImageData(id, 0, 0);

                    // === END COLOR MONOLITHIC RENDERERS ===
                } else {
                    // Original special/monolithic: dramatic effect preview
                    const isShift = finishId.includes('chameleon') || finishId.includes('flip') || finishId.includes('shift') || finishId.includes('prizm');
                    const isGlow = finishId.includes('glow') || finishId.includes('neon') || finishId.includes('ember') || finishId.includes('lava') ||
                        finishId.includes('fire') || finishId.includes('radioactive') || finishId.includes('electric');
                    const isDark2 = finishId.includes('phantom') || finishId.includes('void') || finishId.includes('space') || finishId.includes('singularity') ||
                        finishId.includes('black') || finishId.includes('dark') || finishId.includes('shadow');

                    if (isShift) {
                        // Color shift gradient
                        const id = ctx.createImageData(w, h);
                        const hueBase = (hash % 360 + 360) % 360;
                        for (let py = 0; py < h; py++) {
                            for (let px = 0; px < w; px++) {
                                const t = (Math.sin(py * 0.06 + px * 0.04) * 0.3 + Math.sin(py * 0.03 - px * 0.06) * 0.2 + 0.5);
                                const hue = (hueBase + t * 120) % 360;
                                const [r2, g2, b2] = _hslToRgb(hue, 65, 45 + t * 20);
                                const idx = (py * w + px) * 4;
                                id.data[idx] = r2; id.data[idx + 1] = g2; id.data[idx + 2] = b2; id.data[idx + 3] = 255;
                            }
                        }
                        ctx.putImageData(id, 0, 0);
                    } else if (isGlow) {
                        // Glowing center
                        ctx.fillStyle = `rgb(${Math.max(0, cr - 30)},${Math.max(0, cg - 30)},${Math.max(0, cb - 30)})`;
                        ctx.fillRect(0, 0, w, h);
                        const radG = ctx.createRadialGradient(w * 0.4, h * 0.4, 2, w * 0.5, h * 0.5, w * 0.7);
                        radG.addColorStop(0, `rgba(${Math.min(255, cr + 80)},${Math.min(255, cg + 80)},${Math.min(255, cb + 60)},0.8)`);
                        radG.addColorStop(0.5, `rgba(${cr},${cg},${cb},0.4)`);
                        radG.addColorStop(1, 'rgba(0,0,0,0)');
                        ctx.fillStyle = radG; ctx.fillRect(0, 0, w, h);
                    } else if (isDark2) {
                        // Dark void with subtle gradient
                        const g2 = ctx.createRadialGradient(w * 0.5, h * 0.5, 2, w * 0.5, h * 0.5, w * 0.8);
                        g2.addColorStop(0, `rgb(${Math.min(40, cr + 15)},${Math.min(40, cg + 15)},${Math.min(50, cb + 25)})`);
                        g2.addColorStop(1, `rgb(${Math.min(15, cr)},${Math.min(15, cg)},${Math.min(20, cb)})`);
                        ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h);
                    } else {
                        // Default special: rich gradient + noise
                        const g2 = ctx.createLinearGradient(0, 0, w, h);
                        g2.addColorStop(0, `rgb(${Math.max(0, cr - 20)},${Math.max(0, cg - 20)},${Math.max(0, cb - 20)})`);
                        g2.addColorStop(0.3, `rgb(${Math.min(255, cr + 25)},${Math.min(255, cg + 25)},${Math.min(255, cb + 25)})`);
                        g2.addColorStop(0.6, `rgb(${cr},${cg},${cb})`);
                        g2.addColorStop(1, `rgb(${Math.max(0, cr - 25)},${Math.max(0, cg - 25)},${Math.max(0, cb - 25)})`);
                        ctx.fillStyle = g2; ctx.fillRect(0, 0, w, h);
                        const id = ctx.getImageData(0, 0, w, h);
                        for (let i = 0; i < id.data.length; i += 4) {
                            const n = (rng() - 0.5) * 25;
                            id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n;
                        }
                        ctx.putImageData(id, 0, 0);
                        // Subtle highlight
                        const hl = ctx.createLinearGradient(0, 0, w, h * 0.5);
                        hl.addColorStop(0, 'rgba(255,255,255,0)');
                        hl.addColorStop(0.35, 'rgba(255,255,255,0.1)');
                        hl.addColorStop(0.55, 'rgba(255,255,255,0.1)');
                        hl.addColorStop(1, 'rgba(255,255,255,0)');
                        ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
                    }
                } // closes } else { for original specials branch
            }
        }
    }
}

// Helper: seeded pseudo-RNG (mulberry32)
function _seededRng(seed) {
    let s = seed | 0;
    return function () {
        s = (s + 0x6D2B79F5) | 0;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

// Helper: HSL to RGB
function _hslToRgb(h, s, l) {
    h /= 360; s /= 100; l /= 100;
    let r, g, b;
    if (s === 0) { r = g = b = l; } else {
        const hue2rgb = (p, q, t) => { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1 / 6) return p + (q - p) * 6 * t; if (t < 1 / 2) return q; if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6; return p; };
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3); g = hue2rgb(p, q, h); b = hue2rgb(p, q, h - 1 / 3);
    }
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

// Helper: simple 2D noise (bilinear interpolated multi-scale)
function _simpleNoise2D(w, h, scales, weights, rng) {
    const result = new Float32Array(w * h);
    for (let si = 0; si < scales.length; si++) {
        const s = scales[si], wt = weights[si];
        const sw2 = Math.max(2, Math.ceil(w / s));
        const sh2 = Math.max(2, Math.ceil(h / s));
        const raw = new Float32Array(sw2 * sh2);
        for (let i = 0; i < raw.length; i++) raw[i] = rng() * 2 - 1;
        for (let py = 0; py < h; py++) {
            for (let px = 0; px < w; px++) {
                const fx = px / w * (sw2 - 1), fy = py / h * (sh2 - 1);
                const ix = Math.min(Math.floor(fx), sw2 - 2), iy = Math.min(Math.floor(fy), sh2 - 2);
                const fx2 = fx - ix, fy2 = fy - iy;
                const v = raw[iy * sw2 + ix] * (1 - fx2) * (1 - fy2) + raw[iy * sw2 + ix + 1] * fx2 * (1 - fy2)
                    + raw[(iy + 1) * sw2 + ix] * (1 - fx2) * fy2 + raw[(iy + 1) * sw2 + ix + 1] * fx2 * fy2;
                result[py * w + px] += v * wt;
            }
        }
    }
    return result;
}

/**
 * Renders a full swatch onto a <canvas> for a library-list item.
 * Caches ImageData (by finishId) for non-image swatches so repeated paints
 * are effectively free. Image-backed swatches bypass the cache because their
 * draw is already cheap (blitting an HTMLImageElement).
 * @param {HTMLCanvasElement} canvas
 * @param {string} finishId
 * @returns {void}
 */
function renderFinishSwatch(canvas, finishId) {
    if (!canvas || typeof canvas.getContext !== 'function') {
        console.warn('[SWATCH] renderFinishSwatch: bad canvas for ' + finishId);
        return;
    }
    const finishForCache = [...(typeof BASES !== 'undefined' ? BASES : []), ...(typeof PATTERNS !== 'undefined' ? PATTERNS : []), ...(typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : [])].find(f => f && f.id === finishId);
    const isImageSwatch = finishForCache && finishForCache.swatch_image;
    const cacheKey = finishId + '_swatch';
    if (!isImageSwatch && _previewCache[cacheKey]) {
        canvas.getContext('2d').putImageData(_previewCache[cacheKey], 0, 0);
        return;
    }
    const ctx = canvas.getContext('2d');
    try {
        renderPatternPreview(ctx, canvas.width, canvas.height, finishId);
        if (!isImageSwatch) {
            _previewCache[cacheKey] = ctx.getImageData(0, 0, canvas.width, canvas.height);
        }
    } catch (err) {
        console.warn('[SWATCH] renderFinishSwatch failed for ' + finishId + ': ' + (err && err.message ? err.message : err));
        try { ctx.fillStyle = '#3a3a3a'; ctx.fillRect(0, 0, canvas.width, canvas.height); } catch (_) { /* noop */ }
    }
}

// Expose helpers globally for cross-file use (parity with pre-existing patterns).
if (typeof window !== 'undefined') {
    window.renderFinishSwatch = renderFinishSwatch;
    window.renderPatternPreview = renderPatternPreview;
    window.SWATCH_SIZES = SWATCH_SIZES;
}

