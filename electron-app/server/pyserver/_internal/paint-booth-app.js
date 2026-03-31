// ============================================================
// SHOKKER PAINT BOOTH - Base + Pattern Compositing
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
    const advBar1 = document.getElementById('advancedToolbar'); if (advBar1) advBar1.style.display = 'flex';
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

// ===== FINISH DATA =====
// ===== 24K ARSENAL: 155 Bases × 155 Patterns + 155 Specials =====
// 155 bases × 155 patterns = 24025 base+pattern combos + 155 specials = 24,180 total

// ── Pain Point #2 Fix ─────────────────────────────────────────────────
// /api/finish-data serves the live Python registry as JSON.
// On load we merge any IDs missing from the static arrays below so that
// new Python finishes automatically appear in the UI with zero HTML edits.
// The static arrays remain as offline fallback if the server is down.
// ─────────────────────────────────────────────────────────────────────
async function _mergeFinishDataFromServer() {
    try {
        const res = await fetch('/api/finish-data', { cache: 'no-store' });
        if (!res.ok) return;
        const data = await res.json();
        if (data.status !== 'ok') return;

        function _merge(staticArr, serverArr) {
            if (!serverArr || !serverArr.length) return;
            const existing = new Set(staticArr.map(f => f.id));
            let added = 0;
            for (const item of serverArr) {
                if (!existing.has(item.id)) {
                    staticArr.push({
                        id: item.id,
                        name: item.name,
                        desc: item.category || '',
                        swatch: item.swatch || '#888888'
                    });
                    added++;
                }
            }
            if (added > 0) console.log(`[FinishData] Merged ${added} new entries from server`);
        }

        _merge(BASES, data.bases);
        _merge(PATTERNS, data.patterns);
        _merge(MONOLITHICS, data.specials);

        // Re-render finish library so new entries appear
        if (typeof renderFinishLibrary === 'function') renderFinishLibrary();
        if (typeof buildFinishBrowser === 'function') buildFinishBrowser();
        if (typeof populateBaseDropdown === 'function') populateBaseDropdown();

    } catch (e) {
        console.warn('[FinishData] Server merge skipped (offline?):', e.message);
    }
}
// Run after arrays are defined - see _mergeFinishDataFromServer() call at bottom of FINISH DATA block

// =============================================================================
// FINISH DATA: Single source is paint-booth-1-data.js - load it BEFORE this script.
// BASES, PATTERNS, MONOLITHICS, PATTERN_GROUPS, SPECIAL_GROUPS are defined there.
// This file no longer duplicates them. If this bundle runs standalone, load 1-data first.
// =============================================================================
if (typeof BASES === 'undefined' || typeof PATTERN_GROUPS === 'undefined' || typeof SPECIAL_GROUPS === 'undefined') {
    console.warn('[paint-booth-app] Finish data missing - load paint-booth-1-data.js first.');
}


// Legacy compat: flat array of all finishes (used for old scripts)
const FINISHES = [
    ...BASES.map(b => ({ ...b, cat: "Base" })),
    ...PATTERNS.filter(p => p.id !== "none").map(p => ({ ...p, cat: "Pattern" })),
    ...MONOLITHICS.map(m => ({ ...m, cat: "Special" })),
];

const CATEGORIES = ["Base", "Pattern", "Special"];

// ── Fire the server merge now that all static arrays are ready ─────────
// After merge, FINISHES is rebuilt to include newly added entries.
_mergeFinishDataFromServer().then(() => {
    // Rebuild flat FINISHES so search / compare / browser see new entries
    FINISHES.length = 0;
    FINISHES.push(
        ...BASES.map(b => ({ ...b, cat: "Base" })),
        ...PATTERNS.filter(p => p.id !== "none").map(p => ({ ...p, cat: "Pattern" })),
        ...MONOLITHICS.map(m => ({ ...m, cat: "Special" })),
    );
});
// ──────────────────────────────────────────────────────────────────────

const QUICK_COLORS = [
    { label: "Red", value: "red", bg: "#cc2222" },
    { label: "Orange", value: "orange", bg: "#cc6600" },
    { label: "Yellow", value: "yellow", bg: "#ccaa00" },
    { label: "Gold", value: "gold", bg: "#aa8800" },
    { label: "Green", value: "green", bg: "#22aa22" },
    { label: "Blue", value: "blue", bg: "#2255cc" },
    { label: "Purple", value: "purple", bg: "#7733aa" },
    { label: "Pink", value: "pink", bg: "#cc4488" },
    { label: "White", value: "white", bg: "#dddddd" },
    { label: "Dark", value: "dark", bg: "#222222" },
    { label: "Black", value: "black", bg: "#080808" },
    { label: "Gray", value: "gray", bg: "#777777" },
];

const SPECIAL_COLORS = [
    { label: "Remaining", value: "remaining" },
];

const INTENSITY_OPTIONS = [
    { id: "10", name: "10%" },
    { id: "20", name: "20%" },
    { id: "30", name: "30%" },
    { id: "40", name: "40%" },
    { id: "50", name: "50%" },
    { id: "60", name: "60%" },
    { id: "70", name: "70%" },
    { id: "80", name: "80%" },
    { id: "90", name: "90%" },
    { id: "100", name: "100%" },
];
const INTENSITY_VALUES = {
    "10": { spec: 0.10, paint: 0.10, bright: 0.10 },
    "20": { spec: 0.20, paint: 0.20, bright: 0.20 },
    "30": { spec: 0.30, paint: 0.30, bright: 0.30 },
    "40": { spec: 0.40, paint: 0.40, bright: 0.40 },
    "50": { spec: 0.50, paint: 0.50, bright: 0.50 },
    "60": { spec: 0.60, paint: 0.60, bright: 0.60 },
    "70": { spec: 0.70, paint: 0.70, bright: 0.70 },
    "80": { spec: 0.80, paint: 0.80, bright: 0.80 },
    "90": { spec: 0.90, paint: 0.90, bright: 0.90 },
    "100": { spec: 1.00, paint: 1.00, bright: 1.00 },
};

const PRESETS = {
    multi_color_show: {
        name: "Multi-Color Show Car",
        desc: "Up to 4 body colors + number + sponsors + dark",
        category: "Show Car",
        zones: [
            { name: "Body Color 1", color: null, base: "metallic", pattern: "holographic_flake", intensity: "100", hint: "Click your PRIMARY body color (e.g. the blue)" },
            { name: "Body Color 2", color: null, base: "chrome", pattern: "hex_mesh", intensity: "100", hint: "Click your SECOND body color (e.g. the yellow)" },
            { name: "Body Color 3", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Third body color (delete if not needed)" },
            { name: "Body Color 4", color: null, base: "pearl", pattern: "stardust", intensity: "80", hint: "Fourth body color (delete if not needed)" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Sponsors / Logos", color: "white", base: "metallic", pattern: "none", intensity: "80", hint: "Most sponsor text is white-ish" },
            { name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", intensity: "80", hint: "Auto-catches dark/black areas" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50", hint: "Catches unclaimed pixels" },
        ]
    },
    single_color_show: {
        name: "Single-Color Show Car",
        desc: "One body color + chrome number + sponsor pop",
        category: "Show Car",
        zones: [
            { name: "Body Color", color: null, base: "candy", pattern: "holographic_flake", intensity: "100", hint: "Click the main body color on your paint" },
            { name: "Car Number", color: null, base: "chrome", pattern: "lightning", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Sponsors / Logos", color: "white", base: "chrome", pattern: "none", intensity: "80", hint: "Click a sponsor or use 'white'" },
            { name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", intensity: "80", hint: "Auto-catches dark areas" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50", hint: "Catches unclaimed pixels" },
        ]
    },
    number_pop: {
        name: "Number Pop",
        desc: "Chrome number steals the show",
        category: "Clean",
        zones: [
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Body Color 1", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Click your primary body color" },
            { name: "Body Color 2", color: null, base: "frozen", pattern: "none", intensity: "80", hint: "Second body color (delete if single-color car)" },
            { name: "Sponsors / Logos", color: "white", base: "metallic", pattern: "none", intensity: "80", hint: "Sponsor areas" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50", hint: "Catches everything else" },
        ]
    },
    sponsor_showcase: {
        name: "Sponsor Showcase",
        desc: "Metallic sponsors pop against matte body",
        category: "Clean",
        zones: [
            { name: "Sponsors / Logos", color: "white", base: "chrome", pattern: "none", intensity: "100", hint: "Click a sponsor area or use 'white'" },
            { name: "Car Number", color: null, base: "metallic", pattern: "metal_flake", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Body Color 1", color: null, base: "matte", pattern: "none", intensity: "80", hint: "Click primary body color" },
            { name: "Body Color 2", color: null, base: "satin", pattern: "none", intensity: "80", hint: "Second body color (delete if not needed)" },
            { name: "Dark / Carbon Areas", color: "dark", base: "blackout", pattern: "carbon_fiber", intensity: "100", hint: "Auto-catches dark areas" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50", hint: "Catches unclaimed pixels" },
        ]
    },
    full_chrome: {
        name: "Full Send Chrome",
        desc: "Mirror chrome on everything",
        category: "Aggressive",
        zones: [
            { name: "All Surfaces", color: "everything", base: "chrome", pattern: "none", intensity: "100", hint: "Covers the entire car" },
        ]
    },
    street_racer: {
        name: "Street Racer",
        desc: "Candy body + chrome carbon number + carbon dark",
        category: "Aggressive",
        zones: [
            { name: "Body Color 1", color: null, base: "candy", pattern: "none", intensity: "100", hint: "Click your primary body color" },
            { name: "Body Color 2", color: null, base: "pearl", pattern: "ripple", intensity: "100", hint: "Second body color (delete if not needed)" },
            { name: "Car Number", color: null, base: "chrome", pattern: "stardust", intensity: "100", hint: "Grab each number color with '+ Add to Zone'" },
            { name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", intensity: "100", hint: "Auto-catches dark areas" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "80", hint: "Catches unclaimed pixels" },
        ]
    },
    // ===== v4.2 THEME PRESETS =====
    stealth_mode: {
        name: "Stealth Mode",
        desc: "Murdered-out vantablack body + cerakote accents",
        category: "Aggressive",
        zones: [
            { name: "Body", color: null, base: "vantablack", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "cerakote", pattern: "none", intensity: "100", hint: "Click accent/trim areas" },
            { name: "Car Number", color: null, base: "matte", pattern: "none", intensity: "80", hint: "Grab each number color" },
            { name: "Everything Else", color: "remaining", base: "blackout", pattern: "carbon_fiber", intensity: "80" },
        ]
    },
    chameleon_dream: {
        name: "Chameleon Dream",
        desc: "Color-shift body + chrome number + matte sponsors",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, finish: "chameleon_midnight", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "matte", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    carbon_warrior: {
        name: "Carbon Warrior",
        desc: "Chrome carbon fiber body + matte accents",
        category: "Aggressive",
        zones: [
            { name: "Body", color: null, base: "chrome", pattern: "carbon_fiber", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "matte", pattern: "none", intensity: "80", hint: "Click accent areas" },
            { name: "Car Number", color: null, base: "metallic", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Dark Areas", color: "dark", base: "blackout", pattern: "hex_mesh", intensity: "100" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    ice_king: {
        name: "Ice King",
        desc: "Frozen matte body + cracked ice + holographic number",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, base: "frozen_matte", pattern: "cracked_ice", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "holographic_flake", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "frozen_matte", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50" },
        ]
    },
    hot_wheels: {
        name: "Hot Wheels",
        desc: "Spectraflame body + chrome diamond plate accents",
        category: "Show Car",
        zones: [
            { name: "Body", color: null, base: "spectraflame", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "chrome", pattern: "diamond_plate", intensity: "100", hint: "Click accent/trim areas" },
            { name: "Car Number", color: null, base: "chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "metallic", pattern: "metal_flake", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50" },
        ]
    },
    military_spec: {
        name: "Military Spec",
        desc: "Cerakote multicam body + tactical flat accents",
        category: "Themed",
        zones: [
            { name: "Body", color: null, base: "cerakote", pattern: "multicam", intensity: "100", hint: "Click the main body color" },
            { name: "Accents", color: null, base: "duracoat", pattern: "none", intensity: "80", hint: "Click accent/trim areas" },
            { name: "Car Number", color: null, base: "cerakote", pattern: "none", intensity: "80", hint: "Grab number colors" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "none", intensity: "100" },
            { name: "Everything Else", color: "remaining", base: "cerakote", pattern: "none", intensity: "50" },
        ]
    },
    neon_runner: {
        name: "Neon Runner",
        desc: "Blackout body with tron grid + neon glow number",
        category: "Special Effect",
        zones: [
            { name: "Body", color: null, base: "blackout", pattern: "tron", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, finish: "neon_glow", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "matte", pattern: "none", intensity: "50" },
            { name: "Everything Else", color: "remaining", base: "blackout", pattern: "none", intensity: "80" },
        ]
    },
    luxury: {
        name: "Luxury",
        desc: "Rose gold body + satin chrome number + pearl sponsors",
        category: "Show Car",
        zones: [
            { name: "Body", color: null, base: "rose_gold", pattern: "none", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "satin_chrome", pattern: "none", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "pearl", pattern: "none", intensity: "80" },
            { name: "Dark Areas", color: "dark", base: "surgical_steel", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
    retro_racer: {
        name: "Retro Racer",
        desc: "Candy body + pinstripe + chrome stardust number",
        category: "Themed",
        zones: [
            { name: "Body", color: null, base: "candy", pattern: "pinstripe", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, base: "chrome", pattern: "stardust", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "metallic", pattern: "none", intensity: "80" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "none", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", intensity: "50" },
        ]
    },
    track_veteran: {
        name: "Track Veteran",
        desc: "Metallic battle-worn body + worn chrome number",
        category: "Themed",
        zones: [
            { name: "Body", color: null, base: "metallic", pattern: "battle_worn", intensity: "100", hint: "Click the main body color" },
            { name: "Car Number", color: null, finish: "worn_chrome", intensity: "100", hint: "Grab number colors" },
            { name: "Sponsors", color: "white", base: "satin", pattern: "none", intensity: "80" },
            { name: "Dark Areas", color: "dark", base: "matte", pattern: "acid_wash", intensity: "80" },
            { name: "Everything Else", color: "remaining", base: "satin", pattern: "none", intensity: "50" },
        ]
    },
};

// ===== STATE =====
let zones = [];
let selectedZoneIndex = 0;
let categoryCollapsed = {};
let importedSpecMapPath = null;  // Path to imported spec map TGA (merge mode)

// Render History
const renderHistory = [];
const MAX_RENDER_HISTORY = 20;

// Multi-color per zone: each zone can have a `colors` array
// of {color_rgb: [R,G,B], tolerance: N, hex: "#RRGGBB"} objects
// This allows zones like "Car Number" to capture gold + blue + red
// All matched pixels get the SAME finish applied uniformly

// Spatial regions: each zone can have a `regionMask` (Uint8Array)
// that marks which pixels belong to this zone by position (not color).
// Great for numbers, sponsors, artwork where colors overlap body paint.
// regionMask is canvas-resolution: 1 = pixel belongs, 0 = doesn't

let canvasMode = 'eyedropper'; // 'eyedropper' | 'brush' | 'rect' | 'erase' | 'wand' | 'spatial-include' | 'spatial-exclude'
let spatialBrushRadius = 15; // Radius for spatial include/exclude brush
let isDrawing = false;
let rectStart = null; // {x, y} for rectangle start point
let paintImageData = null;
let lastEyedropperColor = null;

// Undo stack for draw region strokes
// Each entry: { zoneIndex, prevMask (Uint8Array snapshot or null) }
const undoStack = [];
const MAX_UNDO = 30;

// Zone undo/redo for property changes (base, pattern, intensity, add/delete, etc.)
const zoneUndoStack = [];   // Each entry: { label, timestamp, snapshot }
const zoneRedoStack = [];   // Each entry: { label, timestamp, snapshot }
const MAX_ZONE_UNDO = 50;
let undoHistoryPointer = -1; // Current position in history for visual highlighting

let undoActiveDragTimer = null;
function pushZoneUndo(label, isDrag = false) {
    if (isDrag && undoActiveDragTimer) {
        // Extend the timer and skip pushing a new state
        clearTimeout(undoActiveDragTimer);
        undoActiveDragTimer = setTimeout(() => { undoActiveDragTimer = null; }, 500);
        return;
    }
    zoneRedoStack.length = 0; // Clear redo on new action
    const snapshot = JSON.parse(JSON.stringify(
        zones.map(z => ({ ...z, regionMask: null })) // Exclude large masks from undo
    ));
    zoneUndoStack.push({
        label: label || 'Change',
        timestamp: Date.now(),
        snapshot: snapshot,
    });
    if (zoneUndoStack.length > MAX_ZONE_UNDO) zoneUndoStack.shift();
    undoHistoryPointer = zoneUndoStack.length; // Points past top = current state
    renderUndoHistoryPanel();

    if (isDrag) {
        undoActiveDragTimer = setTimeout(() => { undoActiveDragTimer = null; }, 500);
    }
}

function undoZoneChange() {
    if (zoneUndoStack.length === 0) { showToast('Nothing to undo'); return; }
    const currentSnapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null }))));
    const entry = zoneUndoStack.pop();
    zoneRedoStack.push({
        label: entry.label,
        timestamp: Date.now(),
        snapshot: currentSnapshot,
    });
    // Restore zone properties while preserving regionMask
    const masks = zones.map(z => z.regionMask);
    zones.length = 0;
    entry.snapshot.forEach((z, i) => { z.regionMask = masks[i] || null; zones.push(z); });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = zoneUndoStack.length;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Undo: ' + entry.label);
}

function redoZoneChange() {
    if (zoneRedoStack.length === 0) { showToast('Nothing to redo'); return; }
    const currentSnapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null }))));
    const entry = zoneRedoStack.pop();
    zoneUndoStack.push({
        label: entry.label,
        timestamp: Date.now(),
        snapshot: currentSnapshot,
    });
    const masks = zones.map(z => z.regionMask);
    zones.length = 0;
    entry.snapshot.forEach((z, i) => { z.regionMask = masks[i] || null; zones.push(z); });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = zoneUndoStack.length;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Redo: ' + entry.label);
}

function jumpToUndoState(index) {
    // Jump to a specific point in the undo stack
    // index 0 = oldest state, zoneUndoStack.length = current (no undo applied)
    if (index < 0 || index >= zoneUndoStack.length) return;
    const entry = zoneUndoStack[index];
    // Save current state to redo
    const currentSnapshot = JSON.parse(JSON.stringify(zones.map(z => ({ ...z, regionMask: null }))));
    zoneRedoStack.push({ label: 'Jump', timestamp: Date.now(), snapshot: currentSnapshot });
    // Restore
    const masks = zones.map(z => z.regionMask);
    zones.length = 0;
    entry.snapshot.forEach((z, i) => { z.regionMask = masks[i] || null; zones.push(z); });
    selectedZoneIndex = Math.min(selectedZoneIndex, zones.length - 1);
    undoHistoryPointer = index;
    renderZones();
    renderUndoHistoryPanel();
    showToast('Jumped to: ' + entry.label);
}

function renderUndoHistoryPanel() {
    const list = document.getElementById('undoHistoryList');
    if (!list) return;
    const count = document.getElementById('undoHistoryCount');
    if (count) count.textContent = zoneUndoStack.length + ' actions';

    let html = '';
    if (zoneUndoStack.length === 0) {
        html = '<div style="color:var(--text-dim); font-size:10px; padding:8px; text-align:center;">No history yet. Make changes to see them here.</div>';
    } else {
        // Show newest first
        for (let i = zoneUndoStack.length - 1; i >= 0; i--) {
            const e = zoneUndoStack[i];
            const isActive = (i === undoHistoryPointer);
            const isCurrent = (i === zoneUndoStack.length - 1 && undoHistoryPointer >= zoneUndoStack.length);
            const dimmed = (i > undoHistoryPointer && undoHistoryPointer < zoneUndoStack.length);
            const timeAgo = formatTimeAgo(e.timestamp);
            html += `<div class="undo-history-item${isActive ? ' active' : ''}${dimmed ? ' dimmed' : ''}" onclick="jumpToUndoState(${i})" title="Click to restore this state">
                <span class="undo-history-label">${escapeHtml(e.label)}</span>
                <span class="undo-history-time">${timeAgo}</span>
            </div>`;
        }
        // Current state marker
        if (undoHistoryPointer >= zoneUndoStack.length) {
            html = `<div class="undo-history-item active" style="cursor:default;">
                <span class="undo-history-label" style="color:var(--accent-green);">Current State</span>
                <span class="undo-history-time">now</span>
            </div>` + html;
        }
    }
    list.innerHTML = html;
}

function formatTimeAgo(ts) {
    const diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 5) return 'just now';
    if (diff < 60) return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return Math.floor(diff / 3600) + 'h ago';
}

function toggleUndoHistoryPanel() {
    const panel = document.getElementById('undoHistoryPanel');
    if (!panel) return;
    const isOpen = panel.classList.contains('open');
    if (isOpen) {
        panel.classList.remove('open');
    } else {
        panel.classList.add('open');
        renderUndoHistoryPanel();
    }
}

function clearUndoHistory() {
    if (!confirm('Clear all undo history?')) return;
    zoneUndoStack.length = 0;
    zoneRedoStack.length = 0;
    undoHistoryPointer = -1;
    renderUndoHistoryPanel();
    showToast('Undo history cleared');
}

// Keyboard shortcuts: Ctrl+Z = undo, Ctrl+Y / Ctrl+Shift+Z = redo
// UNIFIED: prefers draw/mask undo (undoStack) over zone history undo (zoneUndoStack)
document.addEventListener('keydown', function (e) {
    // Skip if focused on input/textarea/select
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        // If there are draw/mask actions to undo, do those first; else undo zone config change
        if (typeof undoStack !== 'undefined' && undoStack.length > 0) {
            undoDrawStroke();
        } else {
            undoZoneChange();
        }
    } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        redoZoneChange();
    }
});

// Zone colors for region overlay visualization
const ZONE_OVERLAY_COLORS = [
    [255, 50, 50, 200],    // Red
    [50, 255, 50, 200],    // Green
    [50, 100, 255, 200],   // Blue
    [255, 255, 50, 200],   // Yellow
    [255, 50, 255, 200],   // Magenta
    [50, 255, 255, 200],   // Cyan
    [255, 150, 50, 200],   // Orange
    [150, 50, 255, 200],   // Purple
    [255, 100, 100, 200],  // Salmon
    [100, 255, 200, 200],  // Mint
    [200, 150, 255, 200],  // Lavender
    [255, 200, 100, 200],  // Peach
];

// ===== INITIALIZATION =====
function init() {
    // Start with 4 body color slots + number + sponsors + dark + remainder
    // User deletes body color slots they don't need
    zones = [
        {
            name: "Body Color 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#3366ff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Pick Color mode - click your PRIMARY body color on the paint"
        },
        {
            name: "Body Color 2", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffcc00", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Click your SECOND body color (delete this zone if single-color car)"
        },
        {
            name: "Body Color 3", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#cc2222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Third body color if needed (delete if not)"
        },
        {
            name: "Body Color 4", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#22cc22", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Fourth body color if needed (delete if not)"
        },
        {
            name: "Car Number", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffaa00", pickerTolerance: 35, colors: [], regionMask: null,
            hint: "Magic Wand each number color, or Draw Region/Rectangle manually."
        },
        {
            name: "Custom Art 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ff3366", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Magic Wand to click artwork or Draw Region manually. Delete if not needed."
        },
        {
            name: "Custom Art 2", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#33ccff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Another art element - Magic Wand + Shift+click. Delete if not needed."
        },
        {
            name: "Sponsors / Logos", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#ffffff", pickerTolerance: 30, colors: [], regionMask: null,
            hint: "Draw regions over sponsor areas, or pick a color if sponsors share one color"
        },
        {
            name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", finish: null, intensity: "80", colorMode: "quick", pickerColor: "#222222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Auto-catches dark/black areas - matte carbon fiber by default"
        },
        {
            name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", finish: null, intensity: "50", colorMode: "special", pickerColor: "#888888", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Safety net - catches any pixels not claimed by zones above"
        },
    ];
    selectedZoneIndex = 0;
    CATEGORIES.forEach(c => categoryCollapsed[c] = false);
    renderZones();
    renderFinishLibrary();
    updateOutputPath();
    refreshTemplateDropdown();
    refreshComboDropdown();
}

// ===== ZONE RENDERING =====
function renderZones() {
    closeSwatchPicker(); // Close any open swatch popup before re-rendering
    if (typeof autoSave === 'function') autoSave(); // Auto-save on every zone change
    const container = document.getElementById('zoneList');
    document.getElementById('zoneCount').textContent = `(${zones.length})`;
    let html = '';
    zones.forEach((zone, i) => {
        const isSelected = i === selectedZoneIndex;
        const accordionClass = ' zone-card-collapsed' + (isSelected ? ' selected' : '');
        const stackCount = (zone.patternStack || []).filter(l => l.id && l.id !== 'none').length;
        const finishName = zone.finish
            ? (MONOLITHICS.find(m => m.id === zone.finish)?.name || zone.finish) +
            (zone.pattern && zone.pattern !== 'none' ? ' + ' + (PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern) : '')
            : zone.base
                ? (BASES.find(b => b.id === zone.base)?.name || zone.base) +
                (zone.pattern && zone.pattern !== 'none' ? ' + ' + (PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern) : '') +
                (stackCount > 0 ? ` +${stackCount}` : '')
                : '(not set)';
        const intensityName = zone.customSpec != null ? 'Custom' : (INTENSITY_OPTIONS.find(o => o.id === zone.intensity)?.name || zone.intensity || '');
        const summaryHtml = `<span class="zone-summary">${escapeHtml(finishName)}${intensityName ? ` <span class="finish-badge">${escapeHtml(intensityName)}</span>` : ''}</span>`;
        const colorStatus = getColorStatusText(zone);

        const zoneHint = zone.hint || '';

        // Determine zone dot color: use picked color if available, fall back to overlay color
        let dotColor;
        let dotTitle;
        if (zone.colorMode === 'picker' && zone.pickerColor) {
            dotColor = zone.pickerColor;
            dotTitle = `Zone color: ${zone.pickerColor}`;
        } else if (zone.colorMode === 'quick' && zone.color) {
            const qc = QUICK_COLORS.find(c => c.value === zone.color);
            dotColor = qc ? qc.bg : '#888';
            dotTitle = `Zone color: ${zone.color}`;
        } else if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
            const [r, g, b] = zone.colors[0].color_rgb || [128, 128, 128];
            dotColor = `rgb(${r},${g},${b})`;
            dotTitle = `Zone color: ${zone.colors.length} color(s)`;
        } else if (zone.colorMode === 'text' && zone.color) {
            // Try matching text color to a quick color, or use CSS color name
            const qc = QUICK_COLORS.find(c => String(zone.color).toLowerCase().includes(c.value));
            dotColor = qc ? qc.bg : '#888';
            dotTitle = `Zone color: "${zone.color}"`;
        } else if (zone.colorMode === 'special' && zone.color === 'remaining') {
            dotColor = '#555';
            dotTitle = 'Remainder (unclaimed pixels)';
        } else if (zone.colorMode === 'special' && zone.color === 'everything') {
            dotColor = 'linear-gradient(135deg, #888, #ccc)';
            dotTitle = 'Everything (all pixels)';
        } else if (zone.regionMask && zone.regionMask.some(v => v > 0)) {
            // Zone has a drawn region but no color - that's valid, region replaces color detection
            dotColor = '#cc88ff';
            dotTitle = 'Region-based zone (lasso/brush drawn)';
        } else {
            dotColor = 'NOCOLOR';
            dotTitle = 'No color selected \u2014 pick a color first';
        }

        // Region badge: show a purple indicator when zone has a drawn region
        const hasRegion = zone.regionMask && zone.regionMask.some(v => v > 0);
        const regionBadge = hasRegion
            ? `<span style="font-size:8px; color:#cc88ff; margin-left:2px; white-space:nowrap;" title="Region drawn (${zone.regionMask.reduce((s, v) => s + (v > 0 ? 1 : 0), 0).toLocaleString()} pixels)">🎯</span>`
            : '';

        const mutedClass = zone.muted ? ' zone-muted' : '';
        html += `<div class="zone-card${accordionClass}${mutedClass}" onclick="selectZone(${i})" id="zone-card-${i}"
            ondragover="zoneDragOver(event,${i})" ondragenter="zoneDragEnter(event,${i})" ondragleave="zoneDragLeave(event)" ondrop="zoneDrop(event,${i})" ondragend="zoneDragEnd(event)">
            <div class="zone-card-header">
                <span class="zone-drag-handle" draggable="true" ondragstart="zoneDragStart(event,${i})" title="Drag to reorder">&#x2630;</span>
                <span class="zone-number">${i + 1}</span>
                <span class="zone-overlay-dot${dotColor === 'NOCOLOR' ? ' no-color' : ''}" style="${dotColor !== 'NOCOLOR' ? 'background:' + dotColor + ';' : ''}" title="${dotTitle}">${dotColor === 'NOCOLOR' ? '\u26A0' : ''}</span>
                <input class="zone-name-input" type="text" value="${escapeHtml(zone.name)}"
                    onclick="event.stopPropagation()"
                    onchange="updateZoneName(${i}, this.value)">
                ${summaryHtml}${regionBadge}
                <button class="zone-mute-btn${zone.muted ? ' muted' : ''}" onclick="event.stopPropagation(); toggleZoneMute(${i})" title="${zone.muted ? 'Unmute zone (include in render)' : 'Mute zone (exclude from render)'}">${zone.muted ? '&#x1F6AB;' : '&#x1F441;'}</button>
                <button class="zone-move-btn" onclick="event.stopPropagation(); duplicateZone(${i})" title="Duplicate this zone" style="font-size:12px; padding:1px 5px;">&#x29C9;</button>
                <div class="zone-reorder-group">
                    <button class="zone-move-btn" onclick="event.stopPropagation(); moveZoneUp(${i})" title="Move zone up (higher priority)"${i === 0 ? ' disabled' : ''}>&#9650;</button>
                    <button class="zone-move-btn" onclick="event.stopPropagation(); moveZoneDown(${i})" title="Move zone down (lower priority)"${i === zones.length - 1 ? ' disabled' : ''}>&#9660;</button>
                </div>
                <button class="zone-move-btn" onclick="event.stopPropagation(); promptLinkZone(${i})" title="${zone.linkGroup ? 'Linked (click to unlink)' : 'Link this zone to another'}" style="font-size:11px; padding:1px 4px;${zone.linkGroup ? ' color:var(--accent-gold); border-color:var(--accent-gold);' : ''}">${zone.linkGroup ? '&#128279;' : '&#9741;'}</button>
                <button class="zone-delete-btn" onclick="event.stopPropagation(); deleteZone(${i})" title="Delete zone">&times;</button>
            </div>
            ${zone.linkGroup ? `<div style="font-size:8px; color:var(--accent-gold); padding:0 8px 2px; letter-spacing:0.5px;">&#128279; LINKED: ${zones.filter(z => z.linkGroup === zone.linkGroup).map(z => z.name).join(' + ')}</div>` : ''}
            ${zoneHint ? `<div class="zone-hint">${escapeHtml(zoneHint)}</div>` : ''}
            <div class="color-selector" onclick="event.stopPropagation()">
                <div class="color-selector-label">What pixels does this zone cover?</div>
                <div class="color-selector-help">Pick a color below, type a color name, enter a hex code, or use the eyedropper on your paint</div>
                <div class="quick-colors">
                    ${QUICK_COLORS.map(c =>
            `<button class="quick-color-btn${zone.colorMode === 'quick' && zone.color === c.value ? ' active' : ''}"
                            style="border-left: 3px solid ${c.bg};"
                            onclick="setQuickColor(${i}, '${c.value}')"
                            title="Selects all ${c.label.toLowerCase()}-ish pixels">${c.label}</button>`
        ).join('')}
                    ${SPECIAL_COLORS.map(c =>
            `<button class="quick-color-btn special${zone.colorMode === 'special' && zone.color === c.value ? ' active' : ''}"
                            onclick="setSpecialColor(${i}, '${c.value}')"
                            title="${c.value === 'everything' ? 'Selects ALL pixels on the car' : 'Catches any pixels not claimed by higher-priority zones'}">${c.label}</button>`
        ).join('')}
                </div>
                <div class="color-text-row">
                    <input class="color-text-input" type="text" placeholder="Type a color: &quot;dark blue&quot;, &quot;bright red&quot;, &quot;navy&quot;..."
                        value="${zone.colorMode === 'text' ? escapeHtml(String(zone.color)) : ''}"
                        onchange="setTextColor(${i}, this.value)"
                        onfocus="this.select()">
                </div>
                <div class="color-hex-row">
                    <span class="hex-label">HEX / Eyedropper:</span>
                    <input class="hex-code-input" type="text" placeholder="#FF3366"
                        value="${zone.colorMode === 'picker' && !zone.colors?.length ? (zone.pickerColor || '') : ''}"
                        onchange="setHexColor(${i}, this.value)"
                        onfocus="this.select()"
                        maxlength="7">
                    <input class="color-picker-input" type="color" value="${zone.pickerColor || '#3366ff'}"
                        onchange="setPickerColor(${i}, this.value)"
                        title="Color picker">
                </div>
                <div class="color-tol-row">
                    <span class="tol-label">TOL:</span>
                    <input class="tolerance-slider" type="range" min="5" max="100" value="${zone.pickerTolerance || 40}"
                        onchange="setPickerTolerance(${i}, this.value)"
                        title="How close a pixel must be to this color (lower = more exact, higher = more forgiving)">
                    <span class="tolerance-val">±${zone.pickerTolerance || 40}</span>
                </div>
                ${renderMultiColorChips(zone, i)}
                <div class="color-status">${colorStatus}</div>
                ${i === selectedZoneIndex ? renderHarmonyPanel(zone, i) : ''}
            </div>
            <div class="zone-finish-row">
                <label>Base</label>
                <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'base', ${i})" title="${zone.finish ? (MONOLITHICS.find(m => m.id === zone.finish) || {}).desc || '' : zone.base ? (BASES.find(b => b.id === zone.base) || {}).desc || '' : 'Click to select a base finish'}">
                    ${zone.finish ? renderSwatchDot(zone.finish, getSwatchColor(zone), getZoneColorHex(zone)) : zone.base ? renderSwatchDot(zone.base, getSwatchColor(zone), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                    <span class="swatch-name">${getBaseName(zone)}</span>
                    <span class="swatch-arrow">&#9662;</span>
                </div>
                <span class="lock-toggle${zone.lockBase ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockBase')" title="Lock base during randomize">${zone.lockBase ? '&#128274;' : '&#128275;'}</span>
                <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishBrowser(${i})" title="Browse all finishes visually" style="padding:1px 4px; font-size:9px; margin-left:2px;">🎨</button>
                <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishCompare(${i})" title="Compare finishes side-by-side" style="padding:1px 4px; font-size:9px;">🔍</button>
            </div>
            ${(zone.base || zone.finish) ? `<div class="zone-finish-row zone-base-rotate-row" onclick="event.stopPropagation()" style="padding-left:24px;">
                <div class="stack-control-group" style="flex:1;">
                    <span class="stack-label-mini">Base Rotate</span>
                    <input type="range" min="0" max="359" step="1" value="${zone.baseRotation || 0}"
                        oninput="setZoneBaseRotation(${i}, this.value)"
                        class="stack-slider" title="Rotate base material (degrees)">
                    <input type="number" min="0" max="359" step="1" value="${zone.baseRotation || 0}"
                        onchange="setZoneBaseRotation(${i}, this.value)"
                        oninput="setZoneBaseRotation(${i}, this.value)"
                        id="baseRotVal${i}"
                        style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text-main,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;" title="Type exact degrees">
                    <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneBaseRotation(${i})" title="Reset to 0°" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                </div>
            </div>` : ''}
            ${(zone.base || zone.finish) ? `<div class="pattern-stack-section" onclick="event.stopPropagation()">
                <div class="pattern-stack-header">${zone.finish ? 'Pattern Overlay' : `Pattern Layers (${1 + (zone.patternStack || []).length})`}
                    ${zone.finish ? '<span style="font-size:9px;color:var(--text-dim);margin-left:4px;">(optional - adds texture over special finish)</span>' : ''}
                    <span class="lock-toggle${zone.lockPattern ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockPattern')" title="Lock pattern during randomize" style="margin-left:auto;float:right;">${zone.lockPattern ? '&#128274;' : '&#128275;'}</span>
                </div>
                <div class="pattern-layer-card">
                    <div class="pattern-layer-card-header">
                        <span class="pattern-layer-num">L1</span>
                        <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'pattern', ${i})">
                            ${(zone.pattern && zone.pattern !== 'none') ? renderSwatchDot(zone.pattern, getPatternSwatchColor(zone.pattern), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                            <span class="swatch-name">${getPatternName(zone.pattern)}</span>
                            <span class="swatch-arrow">&#9662;</span>
                        </div>
                    </div>
                    ${(zone.pattern && zone.pattern !== 'none') ? `
                    <div class="pattern-layer-card-controls">
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Opacity</span>
                            <input type="range" min="0" max="100" step="5" value="${zone.patternOpacity ?? 100}"
                                oninput="setZonePatternOpacity(${i}, this.value)" onclick="event.stopPropagation()"
                                class="stack-slider" title="Opacity">
                            <span class="stack-val" id="patOpVal${i}">${zone.patternOpacity ?? 100}%</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Scale</span>
                            <input type="range" min="0.10" max="4.0" step="0.05" value="${zone.scale || 1.0}"
                                oninput="setZoneScale(${i}, this.value)" onclick="event.stopPropagation()"
                                class="stack-slider" title="Scale">
                            <span class="stack-val" id="scaleVal${i}">${(zone.scale || 1.0).toFixed(2)}x</span>
                            <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneScale(${i})" title="Reset to 1.0x" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Rotate</span>
                            <input type="range" min="0" max="359" step="1" value="${zone.rotation || 0}"
                                oninput="setZoneRotation(${i}, this.value)" onclick="event.stopPropagation()"
                                class="stack-slider" title="Rotation (degrees)">
                            <input type="number" min="0" max="359" step="1" value="${zone.rotation || 0}"
                                onchange="setZoneRotation(${i}, this.value)"
                                oninput="setZoneRotation(${i}, this.value)"
                                id="rotVal${i}"
                                style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text-main,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;" title="Type exact degrees">
                            <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                            <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneRotation(${i})" title="Reset to 0°" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                        </div>
                    </div>` : ''}
                </div>
                ${!zone.finish ? (zone.patternStack || []).map((layer, li) => `
                <div class="pattern-layer-card">
                    <div class="pattern-layer-card-header">
                        <span class="pattern-layer-num">L${li + 2}</span>
                        <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'stackPattern', ${i}, ${li})">
                            ${(layer.id && layer.id !== 'none') ? renderSwatchDot(layer.id, getPatternSwatchColor(layer.id)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                            <span class="swatch-name">${getPatternName(layer.id)}</span>
                            <span class="swatch-arrow">&#9662;</span>
                        </div>
                        <button class="stack-remove-btn" onclick="removePatternLayer(${i}, ${li})" title="Remove layer">&times;</button>
                    </div>
                    <div class="pattern-layer-card-controls">
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Opacity</span>
                            <input type="range" min="0" max="100" step="5" value="${layer.opacity ?? 100}"
                                oninput="setPatternLayerOpacity(${i}, ${li}, this.value)"
                                class="stack-slider" title="Opacity">
                            <span class="stack-val">${layer.opacity ?? 100}%</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Scale</span>
                            <input type="range" min="0.10" max="4.0" step="0.05" value="${layer.scale || 1.0}"
                                oninput="setPatternLayerScale(${i}, ${li}, this.value)"
                                class="stack-slider" title="Scale">
                            <span class="stack-val">${(layer.scale || 1.0).toFixed(2)}x</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Rotate</span>
                            <input type="range" min="0" max="359" step="1" value="${layer.rotation || 0}"
                                oninput="setPatternLayerRotation(${i}, ${li}, this.value)"
                                class="stack-slider" title="Rotation">
                            <input type="number" min="0" max="359" step="1" value="${layer.rotation || 0}"
                                onchange="setPatternLayerRotation(${i}, ${li}, this.value)"
                                oninput="setPatternLayerRotation(${i}, ${li}, this.value)"
                                class="stack-val-input"
                                style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;">
                            <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Blend</span>
                            <select onchange="setPatternLayerBlend(${i}, ${li}, this.value)"
                                style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                <option value="normal"${(layer.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                <option value="multiply"${layer.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                <option value="screen"${layer.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                <option value="overlay"${layer.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                            </select>
                        </div>
                    </div>
                </div>`).join('') : ''}
                ${!zone.finish && (zone.patternStack || []).length < 5 ? `<button class="btn btn-sm stack-add-btn" onclick="addPatternLayer(${i})" title="Add a pattern layer (max 5)">+ Add Layer</button>` : ''}
            </div>` : `<div class="zone-finish-row" style="display:none;"></div>`}
            <div class="zone-finish-row zone-wear-row"${(zone.base || zone.finish) ? '' : ' style="display:none;"'}>
                <label>Wear</label>
                <input type="range" min="0" max="100" step="5" value="${zone.wear || 0}"
                    oninput="setZoneWear(${i}, this.value)" onclick="event.stopPropagation()"
                    style="flex:1; min-width:60px;">
                <span class="slider-val" id="wearVal${i}" style="min-width:30px; text-align:center;">${zone.wear || 0}%</span>
            </div>
            <div class="zone-finish-row intensity-row-stacked">
                <div class="intensity-header" onclick="event.stopPropagation(); toggleIntensitySliders(${i})">
                    <span class="intensity-toggle-arrow${zone.customSpec != null ? ' open' : ''}" id="intArrow${i}">&#9654;</span>
                    <label>Intensity</label>
                </div>
                <div class="intensity-rows-wrap" style="display:flex; flex-direction:column; width:100%; gap:4px;">
                    <div class="intensity-control-group" onclick="event.stopPropagation()" style="display:flex; align-items:center; gap:2px;">
                        <span style="font-size:8px; color:var(--text-dim); min-width:28px;">Base</span>
                        <button class="btn btn-xs intensity-tick" onclick="tickZoneIntensity(${i},-1)" title="Decrease base intensity" style="padding:0 3px; font-size:9px; line-height:16px;">◀</button>
                        <input type="range" min="0" max="100" step="1" value="${parseInt(zone.intensity) || 100}" 
                            oninput="setZoneIntensity(${i}, this.value, true); this.nextElementSibling.value=this.value" 
                            style="width:55px; flex-shrink:0;" title="Base intensity 0-100%">
                        <input type="number" min="0" max="100" step="1" value="${parseInt(zone.intensity) || 100}" 
                            onchange="setZoneIntensity(${i}, this.value, false); this.previousElementSibling.value=this.value" 
                            onclick="event.stopPropagation(); this.select()" 
                            style="width:36px; text-align:center; font-size:9px; padding:1px 2px; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:3px;" 
                            title="Base intensity %">
                        <span style="font-size:8px; color:var(--text-dim);">%</span>
                        <button class="btn btn-xs intensity-tick" onclick="tickZoneIntensity(${i},+1)" title="Increase base intensity" style="padding:0 3px; font-size:9px; line-height:16px;">▶</button>
                    </div>
                    ${(zone.base && zone.pattern && zone.pattern !== 'none') || (zone.finish && zone.pattern && zone.pattern !== 'none') ? `
                    <div class="intensity-control-group" onclick="event.stopPropagation()" style="display:flex; align-items:center; gap:2px;">
                        <span style="font-size:8px; color:var(--text-dim); min-width:28px;">Pattern</span>
                        <input type="range" min="0" max="100" step="1" value="${zone.patternIntensity != null && zone.patternIntensity !== '' ? (parseInt(zone.patternIntensity) || 0) : (parseInt(zone.intensity) || 100)}" 
                            oninput="setZonePatternIntensity(${i}, this.value); this.nextElementSibling.value=this.value" 
                            style="width:55px; flex-shrink:0;" title="Pattern intensity - independent of base">
                        <input type="number" min="0" max="100" step="1" value="${zone.patternIntensity != null && zone.patternIntensity !== '' ? (parseInt(zone.patternIntensity) || 0) : (parseInt(zone.intensity) || 100)}" 
                            onchange="setZonePatternIntensity(${i}, this.value); this.previousElementSibling.value=this.value" 
                            onclick="event.stopPropagation(); this.select()" 
                            style="width:36px; text-align:center; font-size:9px; padding:1px 2px; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:3px;" 
                            title="Pattern intensity %">
                        <span style="font-size:8px; color:var(--text-dim);">%</span>
                    </div>` : ''}
                </div>
                ${zone.customSpec != null ? '<span class="intensity-custom-badge">CUSTOM</span>' : ''}
                <span class="lock-toggle${zone.lockIntensity ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockIntensity')" title="Lock intensity during randomize">${zone.lockIntensity ? '&#128274;' : '&#128275;'}</span>
            </div>
            <div class="intensity-sliders${zone.customSpec != null ? ' open' : ''}" id="intSliders${i}">
                <div class="intensity-slider-row">
                    <label>Spec</label>
                    <input type="range" min="0" max="1.00" step="0.05" value="${zone.customSpec != null ? zone.customSpec : INTENSITY_VALUES[zone.intensity]?.spec || 1.0}" oninput="setCustomIntensity(${i},'spec',this.value)" onclick="event.stopPropagation()" onpointerdown="event.stopPropagation()">
                    <span class="slider-val" id="intSpecVal${i}">${(zone.customSpec != null ? zone.customSpec : INTENSITY_VALUES[zone.intensity]?.spec || 1.0).toFixed(2)}</span>
                </div>
                <div class="intensity-slider-row">
                    <label>Paint</label>
                    <input type="range" min="0" max="1.00" step="0.05" value="${zone.customPaint != null ? zone.customPaint : INTENSITY_VALUES[zone.intensity]?.paint || 1.0}" oninput="setCustomIntensity(${i},'paint',this.value)" onclick="event.stopPropagation()" onpointerdown="event.stopPropagation()">
                    <span class="slider-val" id="intPaintVal${i}">${(zone.customPaint != null ? zone.customPaint : INTENSITY_VALUES[zone.intensity]?.paint || 1.0).toFixed(2)}</span>
                </div>
                <div class="intensity-slider-row">
                    <label>Bright</label>
                    <input type="range" min="0" max="1.00" step="0.05" value="${zone.customBright != null ? zone.customBright : INTENSITY_VALUES[zone.intensity]?.bright || 1.0}" oninput="setCustomIntensity(${i},'bright',this.value)" onclick="event.stopPropagation()" onpointerdown="event.stopPropagation()">
                    <span class="slider-val" id="intBrightVal${i}">${(zone.customBright != null ? zone.customBright : INTENSITY_VALUES[zone.intensity]?.bright || 1.0).toFixed(2)}</span>
                </div>
            </div>
            ${i === 0 ? '<div class="zone-priority-note">First zone = highest priority</div>' : ''}
        </div>`;
    });
    container.innerHTML = html;
    // Render the detail panel for selected zone
    renderZoneDetail(selectedZoneIndex);
    // Auto-save after any zone change
    if (typeof autoSave === 'function') autoSave();
    // Update onboarding hints
    if (typeof updateOnboardingHints === 'function') updateOnboardingHints();
}

function getColorStatusText(zone) {
    // Check for drawn region first
    const hasRegion = zone.regionMask && zone.regionMask.some(v => v > 0);
    const regionPixels = hasRegion ? zone.regionMask.reduce((sum, v) => sum + v, 0) : 0;
    const regionNote = hasRegion ? `<br><span style="color: var(--accent-blue);">&#9998; Drawn region: <strong>${regionPixels.toLocaleString()} pixels</strong> marked</span>` : '';

    if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
        return `&#10004; Multi-color zone: <strong>${zone.colors.length} colors stacked</strong> - all pixels get the same finish${regionNote}`;
    }
    if (hasRegion && (zone.colorMode === 'none' || zone.color === null)) {
        return `<span style="color: var(--accent-blue);">&#9998; Spatial region drawn: <strong>${regionPixels.toLocaleString()} pixels</strong> marked - no color matching needed</span>`;
    }
    if (zone.colorMode === 'none' || zone.color === null) return '<span style="color: #ff6644;">&#9888; No color or region set - use Pick Color, Draw Region, or buttons</span>';
    if (zone.colorMode === 'quick') return `&#10004; Matching all <strong>${zone.color}</strong> pixels`;
    if (zone.colorMode === 'special') {
        if (zone.color === 'everything') return '&#10004; Covers <strong>ALL</strong> pixels on the car';
        if (zone.color === 'remaining') return '&#10004; Catches anything <strong>not claimed</strong> by zones above';
        return `&#10004; Special: <strong>${zone.color}</strong>`;
    }
    if (zone.colorMode === 'picker') {
        const c = zone.color;
        const hex = zone.pickerColor || '#???';
        return `&#10004; Matching pixels near <strong>${hex.toUpperCase()}</strong> (tolerance: ${c.tolerance})`;
    }
    if (zone.colorMode === 'text') return `&#10004; Matching: <strong>${escapeHtml(String(zone.color))}</strong>`;
    return '';
}

function renderMultiColorChips(zone, zoneIndex) {
    const colors = zone.colors || [];
    if (colors.length === 0 && zone.colorMode !== 'multi') return '';

    let chips = colors.map((c, ci) => {
        const hex = c.hex || '#???';
        return `<span style="display: inline-flex; align-items: center; gap: 3px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; font-size: 10px;">
            <span style="width: 14px; height: 14px; border-radius: 3px; background: ${hex}; border: 1px solid var(--border); display: inline-block;"></span>
            <span style="font-family: 'Consolas', monospace; color: var(--accent-green);">${hex.toUpperCase()}</span>
            <span style="color: var(--text-dim); font-size: 9px;">±${c.tolerance}</span>
            <button onclick="event.stopPropagation(); removeColorFromZone(${zoneIndex}, ${ci})" style="background:none; border:none; color:#ff4444; cursor:pointer; font-size:12px; padding:0 2px; line-height:1;" title="Remove this color">&times;</button>
        </span>`;
    }).join('');

    return `<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; align-items: center;">
        ${chips}
        <button onclick="event.stopPropagation(); addColorToZoneFromPicker(${zoneIndex})" class="quick-color-btn" style="font-size: 9px; padding: 2px 6px; border-color: var(--accent-green); color: var(--accent-green);" title="Add another color to this zone (use hex input or eyedropper first)">+ Add Color</button>
        ${colors.length > 0 ? `<button onclick="event.stopPropagation(); clearZoneColors(${zoneIndex})" class="quick-color-btn" style="font-size: 9px; padding: 2px 6px; border-color: #ff4444; color: #ff4444;" title="Clear all stacked colors">Clear All</button>` : ''}
    </div>`;
}

function addColorToZoneFromPicker(zoneIndex) {
    // Grab current hex input value or picker color and ADD it to the zone's colors array
    const zone = zones[zoneIndex];
    const hex = zone.pickerColor || '#3366ff';
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    const tol = zone.pickerTolerance || 40;

    // Check for duplicate
    if (zone.colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
        showToast('That color is already added to this zone', true);
        return;
    }

    zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
    zone.colorMode = 'multi';
    zone.color = zone.colors; // color becomes the array
    renderZones();
    showToast(`Added ${hex.toUpperCase()} to ${zone.name} (${zone.colors.length} colors stacked)`);
}

function removeColorFromZone(zoneIndex, colorIndex) {
    const zone = zones[zoneIndex];
    zone.colors.splice(colorIndex, 1);
    if (zone.colors.length === 0) {
        zone.colorMode = 'none';
        zone.color = null;
    } else {
        zone.color = zone.colors;
    }
    renderZones();
}

function clearZoneColors(zoneIndex) {
    zones[zoneIndex].colors = [];
    zones[zoneIndex].colorMode = 'none';
    zones[zoneIndex].color = null;
    renderZones();
    triggerPreviewRender();
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ===== ZONE DETAIL PANEL (Floating Side Panel) =====
function renderZoneDetail(index) {
    // Render into floating panel between left panel and canvas
    const panel = document.getElementById('zoneEditorFloat');
    const oldPanel = document.getElementById('zoneDetailPanel');
    if (oldPanel) oldPanel.innerHTML = ''; // Clear old bottom drawer
    if (!panel) return;
    if (index < 0 || index >= zones.length) {
        panel.innerHTML = '';
        panel.classList.remove('active');
        updateBottomBarShift();
        return;
    }
    panel.classList.add('active');
    panel.classList.remove('collapsed'); // Ensure expanded when opening
    updateBottomBarShift();
    const zone = zones[index];
    const i = index;

    // Build the detail panel HTML with all zone controls
    let html = '';

    // Header bar
    html += `<div class="zone-detail-header">
        <span class="zone-number">${i + 1}</span>
        <span class="zone-detail-title">${escapeHtml(zone.name)}</span>
        <button class="zone-detail-close" onclick="event.stopPropagation(); toggleZoneFloat()" title="Collapse panel (E)" style="font-size:13px;">&#9664;</button>
        <button class="zone-detail-close" onclick="event.stopPropagation(); collapseZoneDetail()" title="Close detail panel">&times;</button>
    </div>`;

    // Body
    html += `<div class="zone-detail-body" onclick="event.stopPropagation()">`;

    // Hint
    if (zone.hint) {
        html += `<div class="zone-hint">${escapeHtml(zone.hint)}</div>`;
    }

    // Color selector
    const colorStatus = getColorStatusText(zone);
    html += `<div class="color-selector">
        <div class="color-selector-label">What pixels does this zone cover?</div>
        <div class="color-selector-help">Pick a color below, type a color name, enter a hex code, or use the eyedropper on your paint</div>
        <div class="quick-colors">
            ${QUICK_COLORS.map(c =>
        `<button class="quick-color-btn${zone.colorMode === 'quick' && zone.color === c.value ? ' active' : ''}"
                    style="border-left: 3px solid ${c.bg};"
                    onclick="setQuickColor(${i}, '${c.value}')"
                    title="Selects all ${c.label.toLowerCase()}-ish pixels">${c.label}</button>`
    ).join('')}
            ${SPECIAL_COLORS.map(c =>
        `<button class="quick-color-btn special${zone.colorMode === 'special' && zone.color === c.value ? ' active' : ''}"
                    onclick="setSpecialColor(${i}, '${c.value}')"
                    title="${c.value === 'everything' ? 'Selects ALL pixels on the car' : 'Catches any pixels not claimed by higher-priority zones'}">${c.label}</button>`
    ).join('')}
        </div>
        <div class="color-text-row">
            <input class="color-text-input" type="text" placeholder="Type a color: &quot;dark blue&quot;, &quot;bright red&quot;, &quot;navy&quot;..."
                value="${zone.colorMode === 'text' ? escapeHtml(String(zone.color)) : ''}"
                onchange="setTextColor(${i}, this.value)"
                onfocus="this.select()">
        </div>
        <div class="color-hex-row">
            <span class="hex-label">HEX / Eyedropper:</span>
            <input class="hex-code-input" type="text" placeholder="#FF3366"
                value="${zone.colorMode === 'picker' && !zone.colors?.length ? (zone.pickerColor || '') : ''}"
                onchange="setHexColor(${i}, this.value)"
                onfocus="this.select()"
                maxlength="7">
            <input class="color-picker-input" type="color" value="${zone.pickerColor || '#3366ff'}"
                onchange="setPickerColor(${i}, this.value)"
                title="Color picker">
        </div>
        <div class="color-tol-row">
            <span class="tol-label">TOL:</span>
            <input class="tolerance-slider" type="range" min="5" max="100" value="${zone.pickerTolerance || 40}"
                onchange="setPickerTolerance(${i}, this.value)"
                title="How close a pixel must be to this color (lower = more exact, higher = more forgiving)">
            <span class="tolerance-val">&plusmn;${zone.pickerTolerance || 40}</span>
        </div>
        ${renderMultiColorChips(zone, i)}
        <div class="color-status">${colorStatus}</div>
        ${renderHarmonyPanel(zone, i)}
    </div>`;

    // Base/Finish row
    html += `<div class="zone-finish-row">
        <label>Base</label>
        <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'base', ${i})" title="${zone.finish ? (MONOLITHICS.find(m => m.id === zone.finish) || {}).desc || '' : zone.base ? (BASES.find(b => b.id === zone.base) || {}).desc || '' : 'Click to select a base finish'}">
            ${zone.finish ? renderSwatchDot(zone.finish, getSwatchColor(zone), getZoneColorHex(zone)) : zone.base ? renderSwatchDot(zone.base, getSwatchColor(zone), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
            <span class="swatch-name">${getBaseName(zone)}</span>
            <span class="swatch-arrow">&#9662;</span>
        </div>
        <span class="lock-toggle${zone.lockBase ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockBase')" title="Lock base during randomize">${zone.lockBase ? '&#128274;' : '&#128275;'}</span>
        <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishBrowser(${i})" title="Browse all finishes visually" style="padding:1px 4px; font-size:9px; margin-left:2px;">🎨</button>
        <button class="btn btn-sm" onclick="event.stopPropagation(); openFinishCompare(${i})" title="Compare finishes side-by-side" style="padding:1px 4px; font-size:9px;">🔍</button>
    </div>`;

    // Base rotation control
    if (zone.base || zone.finish) {
        html += `<div class="zone-finish-row zone-base-rotate-row" style="padding-left:24px;">
            <div class="stack-control-group" style="flex:1;">
                <span class="stack-label-mini">Base Rotate</span>
                <input type="range" min="0" max="359" step="1" value="${zone.baseRotation || 0}"
                    oninput="setZoneBaseRotation(${i}, this.value)"
                    class="stack-slider" title="Rotate base material (degrees)">
                <input type="number" min="0" max="359" step="1" value="${zone.baseRotation || 0}"
                    onchange="setZoneBaseRotation(${i}, this.value)"
                    oninput="setZoneBaseRotation(${i}, this.value)"
                    id="detBaseRotVal${i}"
                    style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text-main,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;" title="Type exact degrees">
                <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneBaseRotation(${i})" title="Reset to 0°" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
            </div>
            <div class="stack-control-group" style="flex:1; margin-top:4px;">
                <span class="stack-label-mini">Base Scale</span>
                <input type="range" min="1.0" max="10.0" step="0.5" value="${zone.baseScale || 1.0}"
                    oninput="setZoneBaseScale(${i}, this.value)"
                    class="stack-slider" title="Scale/tile base material (1=normal, higher=more repetitions)">
                <span class="stack-val" id="detBaseScaleVal${i}">${(zone.baseScale || 1.0).toFixed(1)}x</span>
                <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneBaseScale(${i})" title="Reset to 1.0x" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
            </div>
        </div>`;
    }

    // ===== ⚗️ BASE OVERLAY LAYER (Dual Material Blend) =====
    if (zone.base) {
        html += `<div class="pattern-stack-section" style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;">
            <div class="pattern-stack-header" style="color:#c084fc;font-size:10px;">
                ⚗️ Base Overlay Layer
                <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">blend a 2nd material into this zone</span>
                ${zone.secondBase ? `<span style="font-size:9px;margin-left:auto;color:#a78bfa;">● ACTIVE</span>` : ''}
            </div>
            <div style="padding:4px 8px;">
                <div class="stack-control-group">
                    <span class="stack-label-mini">2nd Base</span>
                    <select id="detSecondBase${i}" onchange="setZoneSecondBase(${i}, this.value)"
                        style="font-size:10px;padding:1px 4px;background:var(--bg-input,#1a1a2e);color:var(--text);border:1px solid var(--border);border-radius:3px;max-width:160px;"
                        title="Second base material to blend into this zone">
                        <option value="">- None -</option>
                        ${BASES.map(b => `<option value="${b.id}"${zone.secondBase === b.id ? ' selected' : ''}>${b.name}</option>`).join('')}
                    </select>
                    ${zone.secondBase ? `<button class="btn btn-sm" onclick="event.stopPropagation(); setZoneSecondBase(${i}, '')" title="Remove overlay" style="padding:0px 5px;font-size:9px;line-height:1.2;margin-left:4px;">✕</button>` : ''}
                </div>
                ${zone.secondBase ? `
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Overlay Color</span>
                    <input type="color" value="${zone.secondBaseColor || '#ffffff'}"
                        onchange="setZoneSecondBaseColor(${i}, this.value)"
                        title="Paint color for the overlay base material"
                        style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                    <span style="font-size:9px;color:var(--text-dim);margin-left:6px;">${zone.secondBaseColor || '#ffffff'}</span>
                </div>
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Strength</span>
                    <input type="range" min="0" max="100" step="5" value="${Math.round((zone.secondBaseStrength || 0) * 100)}"
                        oninput="setZoneSecondBaseStrength(${i}, this.value)"
                        class="stack-slider" title="0%=primary only, 100%=overlay only, 50%=equal blend">
                    <span class="stack-val" id="detSBStrVal${i}">${Math.round((zone.secondBaseStrength || 0) * 100)}%</span>
                </div>
                <div class="stack-control-group" style="margin-top:4px;align-items:flex-start;">
                    <span class="stack-label-mini" style="padding-top:2px;">Blend Mode</span>
                    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="sbBlendMode${i}" value="noise" ${(zone.secondBaseBlendMode || 'noise') === 'noise' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'noise')">
                            <span>🌊 Organic Noise</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="sbBlendMode${i}" value="uniform" ${zone.secondBaseBlendMode === 'uniform' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'uniform')">
                            <span>⬜ Uniform</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                            <input type="radio" name="sbBlendMode${i}" value="pattern" ${zone.secondBaseBlendMode === 'pattern' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern')">
                            <span>🔷 Pattern-Reactive</span></label>
                        <label style="display:flex;align-items:center;gap:4px;cursor:pointer;" title="Same as Pattern-Reactive but the overlay color always shows at FULL saturation where the pattern hits - strength controls coverage area, not color intensity">
                            <input type="radio" name="sbBlendMode${i}" value="pattern-vivid" ${zone.secondBaseBlendMode === 'pattern-vivid' ? 'checked' : ''}
                                onchange="setZoneSecondBaseBlendMode(${i}, 'pattern-vivid')">
                            <span>💥 Pattern-Pop <span style="font-size:8px;color:var(--text-dim);">full color</span></span></label>
                    </div>
                </div>
                ${(zone.secondBaseBlendMode || 'noise') === 'noise' ? `
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Noise Scale</span>
                    <input type="range" min="4" max="128" step="4" value="${zone.secondBaseNoiseScale || 24}"
                        oninput="setZoneSecondBaseNoiseScale(${i}, this.value)"
                        class="stack-slider" title="Fine (small) ↔ Coarse (large) noise scale">
                    <span class="stack-val" id="detSBNSVal${i}">${zone.secondBaseNoiseScale || 24}px</span>
                </div>` : ''}
                ` : ''}
                <div class="stack-control-group" style="margin-top:4px;">
                    <span class="stack-label-mini">Paint Color</span>
                    <input type="color" value="${zone.paintReactiveColor || '#000000'}"
                        onchange="setZonePaintReactiveColor(${i}, this.value)"
                        title="Paint color for paint-reactive spec (spec adapts to underlying paint)"
                        style="width:24px;height:18px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
                    <label style="font-size:9px;color:var(--text-dim);margin-left:4px;">
                        <input type="checkbox" ${zone.usePaintReactive ? 'checked' : ''}
                            onchange="setZoneUsePaintReactive(${i}, this.checked)"
                            style="margin-right:2px;">
                        Enable paint-reactive spec
                    </label>
                </div>
            </div>
        </div>`;
    }

    // Pattern stack section
    if (zone.base || zone.finish) {
        const stackCount = (zone.patternStack || []).filter(l => l.id && l.id !== 'none').length;
        html += `<div class="pattern-stack-section">
            <div class="pattern-stack-header">${zone.finish ? 'Pattern Overlay' : `Pattern Layers (${1 + stackCount})`}
                ${zone.finish ? '<span style="font-size:9px;color:var(--text-dim);margin-left:4px;">(optional - adds texture over special finish)</span>' : ''}
                <span class="lock-toggle${zone.lockPattern ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockPattern')" title="Lock pattern during randomize" style="margin-left:auto;float:right;">${zone.lockPattern ? '&#128274;' : '&#128275;'}</span>
            </div>
            <div class="pattern-layer-card">
                <div class="pattern-layer-card-header">
                    <span class="pattern-layer-num">L1</span>
                    <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'pattern', ${i})">
                        ${(zone.pattern && zone.pattern !== 'none') ? renderSwatchDot(zone.pattern, getPatternSwatchColor(zone.pattern), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                        <span class="swatch-name">${getPatternName(zone.pattern)}</span>
                        <span class="swatch-arrow">&#9662;</span>
                    </div>
                </div>
                ${(zone.pattern && zone.pattern !== 'none') ? `
                <div class="pattern-layer-card-controls">
                    <div class="stack-control-group">
                        <span class="stack-label-mini">Opacity</span>
                        <input type="range" min="0" max="100" step="5" value="${zone.patternOpacity ?? 100}"
                            oninput="setZonePatternOpacity(${i}, this.value)"
                            class="stack-slider" title="Opacity">
                        <span class="stack-val" id="detPatOpVal${i}">${zone.patternOpacity ?? 100}%</span>
                    </div>
                    <div class="stack-control-group">
                        <span class="stack-label-mini">Scale</span>
                        <input type="range" min="0.10" max="4.0" step="0.05" value="${zone.scale || 1.0}"
                            oninput="setZoneScale(${i}, this.value)"
                            class="stack-slider" title="Scale">
                        <span class="stack-val" id="detScaleVal${i}">${(zone.scale || 1.0).toFixed(2)}x</span>
                        <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneScale(${i})" title="Reset to 1.0x" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                    </div>
                    <div class="stack-control-group">
                        <span class="stack-label-mini">Rotate</span>
                        <input type="range" min="0" max="359" step="1" value="${zone.rotation || 0}"
                            oninput="setZoneRotation(${i}, this.value)"
                            class="stack-slider" title="Rotation (degrees)">
                        <input type="number" min="0" max="359" step="1" value="${zone.rotation || 0}"
                            onchange="setZoneRotation(${i}, this.value)"
                            oninput="setZoneRotation(${i}, this.value)"
                            id="detRotVal${i}"
                            style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text-main,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;" title="Type exact degrees">
                        <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                        <button class="btn btn-sm" onclick="event.stopPropagation(); resetZoneRotation(${i})" title="Reset to 0°" style="padding:0px 4px; font-size:9px; line-height:1.2;">↺</button>
                    </div>
                </div>` : ''}
            </div>`;

        // Extra pattern stack layers (only for non-monolithic)
        if (!zone.finish) {
            (zone.patternStack || []).forEach((layer, li) => {
                html += `<div class="pattern-layer-card">
                    <div class="pattern-layer-card-header">
                        <span class="pattern-layer-num">L${li + 2}</span>
                        <div class="swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, 'stackPattern', ${i}, ${li})">
                            ${(layer.id && layer.id !== 'none') ? renderSwatchDot(layer.id, getPatternSwatchColor(layer.id), getZoneColorHex(zone)) : '<div class="swatch-dot" style="background:#333;border-style:dashed;"></div>'}
                            <span class="swatch-name">${getPatternName(layer.id)}</span>
                            <span class="swatch-arrow">&#9662;</span>
                        </div>
                        <button class="stack-remove-btn" onclick="removePatternLayer(${i}, ${li})" title="Remove layer">&times;</button>
                    </div>
                    <div class="pattern-layer-card-controls">
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Opacity</span>
                            <input type="range" min="0" max="100" step="5" value="${layer.opacity ?? 100}"
                                oninput="setPatternLayerOpacity(${i}, ${li}, this.value)"
                                class="stack-slider" title="Opacity">
                            <span class="stack-val">${layer.opacity ?? 100}%</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Scale</span>
                            <input type="range" min="0.10" max="4.0" step="0.05" value="${layer.scale || 1.0}"
                                oninput="setPatternLayerScale(${i}, ${li}, this.value)"
                                class="stack-slider" title="Scale">
                            <span class="stack-val">${(layer.scale || 1.0).toFixed(2)}x</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Rotate</span>
                            <input type="range" min="0" max="359" step="1" value="${layer.rotation || 0}"
                                oninput="setPatternLayerRotation(${i}, ${li}, this.value)"
                                class="stack-slider" title="Rotation">
                            <input type="number" min="0" max="359" step="1" value="${layer.rotation || 0}"
                                onchange="setPatternLayerRotation(${i}, ${li}, this.value)"
                                oninput="setPatternLayerRotation(${i}, ${li}, this.value)"
                                class="stack-val-input"
                                style="width:42px; font-size:10px; text-align:center; padding:1px 2px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px;">
                            <span style="font-size:10px; color:var(--text-dim,#888);">°</span>
                        </div>
                        <div class="stack-control-group">
                            <span class="stack-label-mini">Blend</span>
                            <select onchange="setPatternLayerBlend(${i}, ${li}, this.value)"
                                style="font-size:9px; padding:1px 3px; background:var(--bg-input,#1a1a2e); color:var(--text,#e0e0e0); border:1px solid var(--border,#333); border-radius:3px; min-width:60px;">
                                <option value="normal"${(layer.blendMode || 'normal') === 'normal' ? ' selected' : ''}>Normal</option>
                                <option value="multiply"${layer.blendMode === 'multiply' ? ' selected' : ''}>Multiply</option>
                                <option value="screen"${layer.blendMode === 'screen' ? ' selected' : ''}>Screen</option>
                                <option value="overlay"${layer.blendMode === 'overlay' ? ' selected' : ''}>Overlay</option>
                            </select>
                        </div>
                    </div>
                </div>`;
            });
            if ((zone.patternStack || []).length < 5) {
                html += `<button class="btn btn-sm stack-add-btn" onclick="addPatternLayer(${i})" title="Add a pattern layer (max 5)">+ Add Layer</button>`;
            }
        }
        html += `</div>`;
    }

    // Wear row
    if (zone.base || zone.finish) {
        html += `<div class="zone-finish-row zone-wear-row">
            <label>Wear</label>
            <input type="range" min="0" max="100" step="5" value="${zone.wear || 0}"
                oninput="setZoneWear(${i}, this.value)"
                style="flex:1; min-width:60px;">
            <span class="slider-val" id="detWearVal${i}" style="min-width:30px; text-align:center;">${zone.wear || 0}%</span>
        </div>`;
    }

    // Intensity row - Base and Pattern stack vertically so Pattern is not cut off
    html += `<div class="zone-finish-row" style="flex-wrap:wrap;">
        <div class="intensity-header" onclick="event.stopPropagation(); toggleIntensitySliders(${i})">
            <span class="intensity-toggle-arrow${zone.customSpec != null ? ' open' : ''}" id="detIntArrow${i}">&#9654;</span>
            <label>Intensity</label>
        </div>
        <div style="display:flex; flex-direction:column; width:100%; gap:4px; min-width:0;">
            <div class="intensity-control-group" onclick="event.stopPropagation()" style="display:flex; align-items:center; gap:2px;">
                <span style="font-size:8px; color:var(--text-dim); min-width:28px;">Base</span>
                <button class="btn btn-xs intensity-tick" onclick="tickZoneIntensity(${i},-1)" title="Decrease base intensity" style="padding:0 3px; font-size:9px; line-height:16px;">◀</button>
                <input type="range" min="0" max="100" step="1" value="${parseInt(zone.intensity) || 100}" 
                    oninput="setZoneIntensity(${i}, this.value, true); this.nextElementSibling.value=this.value" 
                    style="width:55px; flex-shrink:0;" title="Base intensity 0-100%">
                <input type="number" min="0" max="100" step="1" value="${parseInt(zone.intensity) || 100}" 
                    onchange="setZoneIntensity(${i}, this.value, false); this.previousElementSibling.value=this.value" 
                    onclick="event.stopPropagation(); this.select()" 
                    style="width:36px; text-align:center; font-size:9px; padding:1px 2px; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:3px;" 
                    title="Base intensity %">
                <span style="font-size:8px; color:var(--text-dim);">%</span>
                <button class="btn btn-xs intensity-tick" onclick="tickZoneIntensity(${i},+1)" title="Increase base intensity" style="padding:0 3px; font-size:9px; line-height:16px;">▶</button>
            </div>
            ${(zone.base && zone.pattern && zone.pattern !== 'none') || (zone.finish && zone.pattern && zone.pattern !== 'none') ? `
            <div class="intensity-control-group" onclick="event.stopPropagation()" style="display:flex; align-items:center; gap:2px;">
                <span style="font-size:8px; color:var(--text-dim); min-width:28px;">Pattern</span>
                <input type="range" min="0" max="100" step="1" value="${zone.patternIntensity != null && zone.patternIntensity !== '' ? (parseInt(zone.patternIntensity) || 0) : (parseInt(zone.intensity) || 100)}" 
                    oninput="setZonePatternIntensity(${i}, this.value); this.nextElementSibling.value=this.value" 
                    style="flex:1; min-width:60px;" title="Pattern intensity - independent of base">
                <input type="number" min="0" max="100" step="1" value="${zone.patternIntensity != null && zone.patternIntensity !== '' ? (parseInt(zone.patternIntensity) || 0) : (parseInt(zone.intensity) || 100)}" 
                    onchange="setZonePatternIntensity(${i}, this.value); this.previousElementSibling.value=this.value" 
                    onclick="event.stopPropagation(); this.select()" 
                    style="width:36px; text-align:center; font-size:9px; padding:1px 2px; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:3px;" 
                    title="Pattern intensity %">
                <span style="font-size:8px; color:var(--text-dim);">%</span>
            </div>` : ''}
        </div>
        ${zone.customSpec != null ? '<span class="intensity-custom-badge">CUSTOM</span>' : ''}
        <span class="lock-toggle${zone.lockIntensity ? ' locked' : ''}" onclick="event.stopPropagation(); toggleLock(${i},'lockIntensity')" title="Lock intensity during randomize">${zone.lockIntensity ? '&#128274;' : '&#128275;'}</span>
    </div>`;

    // Intensity sliders
    html += `<div class="intensity-sliders${zone.customSpec != null ? ' open' : ''}" id="detIntSliders${i}">
        <div class="intensity-slider-row">
            <label>Spec</label>
            <input type="range" min="0" max="1.00" step="0.05" value="${zone.customSpec != null ? zone.customSpec : INTENSITY_VALUES[zone.intensity]?.spec || 1.0}" oninput="setCustomIntensity(${i},'spec',this.value)" onpointerdown="event.stopPropagation()">
            <span class="slider-val" id="detIntSpecVal${i}">${(zone.customSpec != null ? zone.customSpec : INTENSITY_VALUES[zone.intensity]?.spec || 1.0).toFixed(2)}</span>
        </div>
        <div class="intensity-slider-row">
            <label>Paint</label>
            <input type="range" min="0" max="1.00" step="0.05" value="${zone.customPaint != null ? zone.customPaint : INTENSITY_VALUES[zone.intensity]?.paint || 1.0}" oninput="setCustomIntensity(${i},'paint',this.value)" onpointerdown="event.stopPropagation()">
            <span class="slider-val" id="detIntPaintVal${i}">${(zone.customPaint != null ? zone.customPaint : INTENSITY_VALUES[zone.intensity]?.paint || 1.0).toFixed(2)}</span>
        </div>
        <div class="intensity-slider-row">
            <label>Bright</label>
            <input type="range" min="0" max="1.00" step="0.05" value="${zone.customBright != null ? zone.customBright : INTENSITY_VALUES[zone.intensity]?.bright || 1.0}" oninput="setCustomIntensity(${i},'bright',this.value)" onpointerdown="event.stopPropagation()">
            <span class="slider-val" id="detIntBrightVal${i}">${(zone.customBright != null ? zone.customBright : INTENSITY_VALUES[zone.intensity]?.bright || 1.0).toFixed(2)}</span>
        </div>
    </div>`;

    if (i === 0) {
        html += '<div class="zone-priority-note">First zone = highest priority</div>';
    }

    // ===== SPATIAL SELECTION - Include/Exclude refinement =====
    if (zone.base || zone.finish) {
        const hasSpatial = hasSpatialMask(zone);
        const isSpatialActive = canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude';
        html += `<div class="pattern-stack-section" style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;">
            <div class="pattern-stack-header" style="color:var(--accent-green);font-size:10px;">
                🎯 Spatial Selection
                <span style="font-size:9px;color:var(--text-dim);margin-left:4px;">Refine color match with include/exclude regions</span>
                ${hasSpatial ? '<span style="font-size:8px;color:var(--accent-green);margin-left:auto;float:right;">ACTIVE</span>' : ''}
            </div>
            <div style="padding:4px 8px;">
                <div style="font-size:9px;color:var(--text-dim);margin-bottom:6px;">
                    Paint on the preview to include (green) or exclude (red) areas from this zone's color selection.
                </div>
                <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;">
                    <button class="btn btn-sm${canvasMode === 'spatial-include' ? ' active' : ''}" 
                        onclick="event.stopPropagation(); toggleSpatialMode('include')" 
                        style="padding:3px 8px;font-size:10px;${canvasMode === 'spatial-include' ? 'background:rgba(0,200,100,0.3);border-color:var(--accent-green);color:var(--accent-green);' : ''}"
                        title="Include brush: paint areas to KEEP in this zone">
                        🟢 Include
                    </button>
                    <button class="btn btn-sm${canvasMode === 'spatial-exclude' ? ' active' : ''}" 
                        onclick="event.stopPropagation(); toggleSpatialMode('exclude')" 
                        style="padding:3px 8px;font-size:10px;${canvasMode === 'spatial-exclude' ? 'background:rgba(220,50,50,0.3);border-color:#ff4444;color:#ff4444;' : ''}"
                        title="Exclude brush: paint areas to REMOVE from this zone">
                        🔴 Exclude
                    </button>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); clearSpatialMask(${i})" 
                        style="padding:3px 8px;font-size:10px;" title="Clear all include/exclude marks">
                        🗑️ Clear
                    </button>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); undoSpatialStroke()" 
                        style="padding:3px 8px;font-size:10px;" title="Undo last spatial stroke">
                        ↩ Undo
                    </button>
                    ${isSpatialActive ? '<button class="btn btn-sm" onclick="event.stopPropagation(); toggleSpatialMode(\'off\')" style="padding:3px 8px;font-size:10px;color:var(--accent-orange);border-color:var(--accent-orange);">✋ Stop Drawing</button>' : ''}
                </div>
                ${isSpatialActive ? `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-size:9px;color:var(--text-dim);min-width:60px;">Brush Size</span>
                    <input type="range" min="3" max="80" value="${spatialBrushRadius}" 
                        oninput="spatialBrushRadius = parseInt(this.value); document.getElementById('spatialBrushVal').textContent = this.value + 'px'"
                        style="flex:1;">
                    <span id="spatialBrushVal" style="font-size:10px;color:var(--text-dim);min-width:30px;">${spatialBrushRadius}px</span>
                </div>` : ''}
            </div>
        </div>`;
    }

    html += `</div>`; // close zone-detail-body

    // Apply/Confirm footer
    html += `<div class="zone-detail-footer">
        <button class="btn-cancel" onclick="collapseZoneDetail()">Cancel</button>
        <button class="btn-apply" onclick="collapseZoneDetail()">&#10003; Apply</button>
    </div>`;

    panel.innerHTML = html;

    // Scroll panel into view
    panel.scrollTop = 0;
}

function collapseZoneDetail() {
    const panel = document.getElementById('zoneDetailPanel');
    if (panel) panel.innerHTML = '';
    // Close floating side panel
    const floatPanel = document.getElementById('zoneEditorFloat');
    if (floatPanel) { floatPanel.innerHTML = ''; floatPanel.classList.remove('active', 'collapsed'); }
    // Hide expand tab
    const tab = document.getElementById('zoneFloatExpandTab');
    if (tab) tab.classList.remove('visible');
    updateBottomBarShift();
}

// Toggle floating panel collapsed/expanded (hides panel, shows expand tab)
function toggleZoneFloat() {
    const floatPanel = document.getElementById('zoneEditorFloat');
    const tab = document.getElementById('zoneFloatExpandTab');
    if (!floatPanel || !floatPanel.classList.contains('active')) return;

    if (floatPanel.classList.contains('collapsed')) {
        // Expand - show panel, hide tab
        floatPanel.classList.remove('collapsed');
        if (tab) { tab.classList.remove('visible'); tab.innerHTML = '&#9664;'; }
    } else {
        // Collapse - hide panel, show tab
        floatPanel.classList.add('collapsed');
        if (tab) { tab.classList.add('visible'); tab.innerHTML = '&#9654;'; }
    }
    updateBottomBarShift();
}

// Shift the entire center panel right when the floating zone panel is visible (not collapsed)
function updateBottomBarShift() {
    const floatPanel = document.getElementById('zoneEditorFloat');
    const isOpen = floatPanel && floatPanel.classList.contains('active') && !floatPanel.classList.contains('collapsed');
    const shiftPx = isOpen ? '370px' : '0';
    // Shift entire center panel content
    const centerPanel = document.getElementById('centerPanel');
    if (centerPanel) centerPanel.style.paddingLeft = shiftPx;
}

// ===== ZONE ACTIONS =====
function selectZone(index) {
    selectedZoneIndex = index;
    renderZones();
    // Update draw zone indicator if in drawing mode
    if (canvasMode !== 'eyedropper') {
        updateDrawZoneIndicator();
    }
    // Sync the right-side eyedropper panel to match the selected zone
    syncEyedropperPanel();
    // Update region status indicator in bottom bar
    if (typeof updateRegionStatus === 'function') updateRegionStatus();
    // Refresh overlay to show only the selected zone's masks
    if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
}

function updateZoneName(index, name) {
    zones[index].name = name;
}

function deleteZone(index) {
    if (zones.length <= 1) { showToast('Need at least one zone', true); return; }
    const z = zones[index];
    const hasFinish = z.base || z.finish;
    const hasColor = z.color !== null || z.colorMode === 'multi';
    // Only confirm if zone has meaningful config (finish + color assigned)
    if (hasFinish && hasColor) {
        if (!confirm(`Delete "${z.name}"? This zone has a finish and color assigned.`)) return;
    }
    pushZoneUndo('Delete zone "' + z.name + '"');
    zones.splice(index, 1);
    if (selectedZoneIndex >= zones.length) selectedZoneIndex = zones.length - 1;
    renderZones();
    triggerPreviewRender();
    autoSave();
}

function moveZoneUp(index) {
    if (index <= 0) return;
    pushZoneUndo('Move zone up');
    [zones[index - 1], zones[index]] = [zones[index], zones[index - 1]];
    if (selectedZoneIndex === index) selectedZoneIndex = index - 1;
    else if (selectedZoneIndex === index - 1) selectedZoneIndex = index;
    renderZones();
}

function moveZoneDown(index) {
    if (index >= zones.length - 1) return;
    pushZoneUndo('Move zone down');
    [zones[index], zones[index + 1]] = [zones[index + 1], zones[index]];
    if (selectedZoneIndex === index) selectedZoneIndex = index + 1;
    else if (selectedZoneIndex === index + 1) selectedZoneIndex = index;
    renderZones();
}

// ===== ZONE DRAG & DROP REORDER =====
let zoneDragIndex = -1;

function zoneDragStart(e, index) {
    // Drag is now ONLY on the handle (☰), so no need to check for controls.
    // The handle has draggable="true"; the card div does NOT.
    // This prevents slider/input interactions from triggering drag ghosts.
    zoneDragIndex = index;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
    // Use the whole card as drag image for visual feedback
    const card = document.getElementById('zone-card-' + index);
    if (card) {
        e.dataTransfer.setDragImage(card, 20, 20);
    }
    // Slight delay so the dragging class doesn't affect the drag image
    requestAnimationFrame(() => {
        if (card) card.classList.add('dragging');
    });
}

function zoneDragOver(e, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function zoneDragEnter(e, index) {
    e.preventDefault();
    // Clear all drag-over classes first
    document.querySelectorAll('.zone-card.drag-over').forEach(el => el.classList.remove('drag-over'));
    if (index !== zoneDragIndex) {
        const card = document.getElementById('zone-card-' + index);
        if (card) card.classList.add('drag-over');
    }
}

function zoneDragLeave(e) {
    // Only remove if actually leaving the card (not entering a child)
    const card = e.target.closest?.('.zone-card');
    if (card && !card.contains(e.relatedTarget)) {
        card.classList.remove('drag-over');
    }
}

function zoneDrop(e, targetIndex) {
    e.preventDefault();
    document.querySelectorAll('.zone-card.drag-over, .zone-card.dragging').forEach(el => {
        el.classList.remove('drag-over', 'dragging');
    });
    if (zoneDragIndex < 0 || zoneDragIndex === targetIndex) return;
    pushZoneUndo('Reorder zones');
    const [moved] = zones.splice(zoneDragIndex, 1);
    zones.splice(targetIndex, 0, moved);
    // Update selected index to follow the moved zone
    if (selectedZoneIndex === zoneDragIndex) {
        selectedZoneIndex = targetIndex;
    } else if (zoneDragIndex < selectedZoneIndex && targetIndex >= selectedZoneIndex) {
        selectedZoneIndex--;
    } else if (zoneDragIndex > selectedZoneIndex && targetIndex <= selectedZoneIndex) {
        selectedZoneIndex++;
    }
    zoneDragIndex = -1;
    renderZones();
    triggerPreviewRender();
    autoSave();
}

function zoneDragEnd(e) {
    zoneDragIndex = -1;
    document.querySelectorAll('.zone-card.drag-over, .zone-card.dragging').forEach(el => {
        el.classList.remove('drag-over', 'dragging');
    });
}

// ===== ZONE MUTE (SOLO/DISABLE) =====
function toggleZoneMute(index) {
    zones[index].muted = !zones[index].muted;
    renderZones();
    triggerPreviewRender();
    autoSave();
    showToast(zones[index].muted
        ? `${zones[index].name} muted (excluded from render)`
        : `${zones[index].name} unmuted`);
}

// ===== RECENT PAINT PATHS =====
const RECENT_PATHS_KEY = 'shokker_recent_paths';
const MAX_RECENT_PATHS = 8;

function getRecentPaths() {
    try {
        return JSON.parse(localStorage.getItem(RECENT_PATHS_KEY) || '[]');
    } catch { return []; }
}

function addRecentPath(path) {
    if (!path) return;
    let paths = getRecentPaths();
    // Remove if already exists (will re-add at top)
    paths = paths.filter(p => p.toLowerCase() !== path.toLowerCase());
    paths.unshift(path);
    if (paths.length > MAX_RECENT_PATHS) paths = paths.slice(0, MAX_RECENT_PATHS);
    localStorage.setItem(RECENT_PATHS_KEY, JSON.stringify(paths));
}

function showRecentPaths() {
    const paths = getRecentPaths();
    const dropdown = document.getElementById('recentPathsDropdown');
    const currentVal = document.getElementById('paintFile').value.trim();
    if (!dropdown || paths.length === 0) { if (dropdown) dropdown.style.display = 'none'; return; }
    // Filter out current value
    const filtered = paths.filter(p => p.toLowerCase() !== currentVal.toLowerCase());
    if (filtered.length === 0) { dropdown.style.display = 'none'; return; }
    dropdown.innerHTML = filtered.map(p => {
        const shortName = p.split(/[/\\]/).pop();
        const folder = p.split(/[/\\]/).slice(-2, -1)[0] || '';
        return `<div class="recent-path-item" onmousedown="selectRecentPath('${p.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')" title="${p}">${folder ? folder + '/' : ''}${shortName}</div>`;
    }).join('');
    dropdown.style.display = '';
}

function hideRecentPaths() {
    const dropdown = document.getElementById('recentPathsDropdown');
    if (dropdown) dropdown.style.display = 'none';
}

function selectRecentPath(path) {
    document.getElementById('paintFile').value = path;
    hideRecentPaths();
    validatePaintPath();
}

// ===== LIVE PREVIEW (PAINT + SPEC INSET) =====
// Paint fills the preview pane. Spec map shows as a clickable inset thumbnail.
// Click the spec inset to expand it full-size (hides paint). Click again to shrink back.
let specExpanded = false;
function toggleSpecInset() {
    const specPane = document.getElementById('previewSpecPane');
    const paintPane = document.getElementById('previewPaintPane');
    specExpanded = !specExpanded;
    specPane.classList.toggle('spec-expanded', specExpanded);
    paintPane.style.display = specExpanded ? 'none' : '';
}

// ===== SPEC MAP CHANNEL VISUALIZER =====
let activeSpecChannel = 'all';  // 'all', 'r', 'g', 'b', 'a'

function setSpecChannel(ch) {
    activeSpecChannel = ch;
    // Update button states
    document.querySelectorAll('.spec-channel-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.ch === ch);
    });
    // Update label
    const labels = { all: 'SPEC MAP', r: 'METALLIC (R)', g: 'ROUGHNESS (G)', b: 'CLEARCOAT (B)', a: 'SPEC MASK (A)' };
    const label = document.querySelector('#previewSpecPane .preview-dual-label');
    if (label) label.textContent = labels[ch] || 'SPEC MAP';
    // Render channel
    renderSpecChannel();
}

function renderSpecChannel() {
    const img = document.getElementById('livePreviewSpecImg');
    const canvas = document.getElementById('specChannelCanvas');
    if (!img || !canvas || !img.src || !img.naturalWidth) return;

    if (activeSpecChannel === 'all') {
        // Show original image, hide canvas
        img.style.display = '';
        canvas.style.display = 'none';
        return;
    }

    // Draw spec image to canvas and extract channel
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, w, h);
    const imageData = ctx.getImageData(0, 0, w, h);
    const d = imageData.data;

    const chIndex = { r: 0, g: 1, b: 2, a: 3 }[activeSpecChannel];
    const chColors = {
        r: [1.0, 0.3, 0.3],   // reddish tint for metallic
        g: [0.3, 1.0, 0.3],   // greenish tint for roughness
        b: [0.3, 0.5, 1.0],   // bluish tint for clearcoat
        a: [1.0, 0.7, 0.3],   // orange tint for spec mask
    };
    const tint = chColors[activeSpecChannel] || [1, 1, 1];

    for (let i = 0; i < d.length; i += 4) {
        const val = d[i + chIndex];
        d[i] = Math.min(255, Math.round(val * tint[0]));  // R
        d[i + 1] = Math.min(255, Math.round(val * tint[1]));  // G
        d[i + 2] = Math.min(255, Math.round(val * tint[2]));  // B
        d[i + 3] = 255;  // Full opacity
    }

    ctx.putImageData(imageData, 0, 0);

    // Show canvas, hide original img
    img.style.display = 'none';
    canvas.style.display = '';
}

// Re-apply channel filter whenever spec preview updates
const _origSpecImgOnload = null;
function hookSpecImageLoad() {
    const img = document.getElementById('livePreviewSpecImg');
    if (!img) return;
    img.addEventListener('load', () => {
        if (activeSpecChannel !== 'all') {
            renderSpecChannel();
        }
    });
}
// Hook after DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hookSpecImageLoad);
} else {
    hookSpecImageLoad();
}

// ===== BEFORE/AFTER COMPARISON =====
let beforeAfterActive = false;
let beforeImageCaptured = false;

function captureBeforeImage() {
    // Capture the current paint canvas as the "before" image
    const paintCanvas = document.getElementById('paintCanvas');
    if (!paintCanvas || paintCanvas.width === 0) return;
    const beforeImg = document.getElementById('beforePreviewImg');
    if (!beforeImg) return;
    beforeImg.src = paintCanvas.toDataURL('image/png');
    beforeImageCaptured = true;
    // Show the B/A button
    const btn = document.getElementById('btnBeforeAfter');
    if (btn) btn.style.display = '';
}

function toggleBeforeAfter() {
    if (!beforeImageCaptured) {
        showToast('No paint loaded yet - load a paint file first');
        return;
    }
    beforeAfterActive = !beforeAfterActive;
    const beforePane = document.getElementById('previewBeforePane');
    const btn = document.getElementById('btnBeforeAfter');
    if (beforeAfterActive) {
        beforePane.style.display = '';
        if (btn) { btn.style.borderColor = 'var(--accent-gold)'; btn.style.background = 'rgba(255,170,0,0.15)'; }
    } else {
        beforePane.style.display = 'none';
        if (btn) { btn.style.borderColor = 'var(--accent-gold)'; btn.style.background = ''; }
    }
}

// Keyboard shortcut: hold B to show before, release to show after
document.addEventListener('keydown', (e) => {
    if (e.key === 'b' && !e.ctrlKey && !e.altKey && !e.metaKey && !e.repeat) {
        const tag = e.target.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (beforeImageCaptured && !beforeAfterActive) {
            toggleBeforeAfter();
        }
    }
});
document.addEventListener('keyup', (e) => {
    if (e.key === 'b') {
        if (beforeAfterActive) toggleBeforeAfter();
    }
});

function clearAllZones() {
    if (!confirm('Reset ALL zones to defaults? This cannot be undone.')) return;
    pushZoneUndo('Clear all zones');
    init();
    showToast('All zones cleared and reset to defaults');
}

function restoreAllZones() {
    // Restore all 10 default zones without losing existing finishes on matching zones
    pushZoneUndo('Restore all zones');
    const defaults = [
        {
            name: "Body Color 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#3366ff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Pick Color mode - click your PRIMARY body color on the paint"
        },
        {
            name: "Body Color 2", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffcc00", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Click your SECOND body color (delete this zone if single-color car)"
        },
        {
            name: "Body Color 3", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#cc2222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Third body color if needed (delete if not)"
        },
        {
            name: "Body Color 4", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#22cc22", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Fourth body color if needed (delete if not)"
        },
        {
            name: "Car Number", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ffaa00", pickerTolerance: 35, colors: [], regionMask: null,
            hint: "Magic Wand each number color, or Draw Region/Rectangle manually."
        },
        {
            name: "Custom Art 1", color: null, base: null, pattern: "none", finish: null, intensity: "100", colorMode: "none", pickerColor: "#ff3366", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Use Magic Wand to click artwork or Draw Region manually. Delete if not needed."
        },
        {
            name: "Custom Art 2", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#33ccff", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Another art element - Magic Wand + Shift+click. Delete if not needed."
        },
        {
            name: "Sponsors / Logos", color: null, base: null, pattern: "none", finish: null, intensity: "80", colorMode: "none", pickerColor: "#ffffff", pickerTolerance: 30, colors: [], regionMask: null,
            hint: "Draw regions over sponsor areas, or pick a color if sponsors share one color"
        },
        {
            name: "Dark / Carbon Areas", color: "dark", base: "matte", pattern: "carbon_fiber", finish: null, intensity: "80", colorMode: "quick", pickerColor: "#222222", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Auto-catches dark/black areas - matte carbon fiber by default"
        },
        {
            name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", finish: null, intensity: "50", colorMode: "special", pickerColor: "#888888", pickerTolerance: 40, colors: [], regionMask: null,
            hint: "Safety net - catches any pixels not claimed by zones above"
        },
    ];
    zones = defaults;
    selectedZoneIndex = 0;
    renderZones();
    autoSave();
    showToast('All 10 default zones restored');
}

function addZone(skipUndo) {
    if (!skipUndo) pushZoneUndo('Add zone');
    zones.push({
        name: `Zone ${zones.length + 1}`,
        color: null,
        base: null,
        pattern: "none",
        finish: null,
        intensity: "100",
        customSpec: null, customPaint: null, customBright: null,
        colorMode: "none",
        pickerColor: "#3366ff",
        pickerTolerance: 40,
        colors: [],
        regionMask: null,
        spatialMask: null, // Uint8Array: 0=unset, 1=include(green), 2=exclude(red)
        hint: "Pick a base material + pattern, then set the color",
        lockBase: false,
        lockPattern: false,
        lockIntensity: false,
        lockColor: false,
        scale: 1.0,
        patternStack: [],
        wear: 0,
        muted: false,
    });
    selectedZoneIndex = zones.length - 1;
    renderZones();
    document.getElementById('zoneList').scrollTop = document.getElementById('zoneList').scrollHeight;
}

function duplicateZone(index) {
    pushZoneUndo('Duplicate zone');
    const src = zones[index];
    const clone = JSON.parse(JSON.stringify(src));
    clone.name = src.name + ' (copy)';
    clone.regionMask = src.regionMask ? [...src.regionMask] : null;
    zones.splice(index + 1, 0, clone);
    selectedZoneIndex = index + 1;
    renderZones();
    showToast(`Duplicated "${src.name}"`);
}

function applyFinishToAllZones() {
    const src = zones[selectedZoneIndex];
    if (!src.base && !src.finish) { showToast('Selected zone has no finish to apply', true); return; }
    if (!confirm(`Apply "${src.base || src.finish}" to ALL ${zones.length} zones?`)) return;
    pushZoneUndo('Apply finish to all zones');
    zones.forEach((z, i) => {
        if (i === selectedZoneIndex) return;
        z.base = src.base;
        z.pattern = src.pattern;
        z.finish = src.finish;
        z.intensity = src.intensity;
        z.patternIntensity = src.patternIntensity;
        z.scale = src.scale;
        z.patternStack = JSON.parse(JSON.stringify(src.patternStack || []));
    });
    renderZones();
    showToast(`Applied finish to all ${zones.length} zones`);
}

// ===== COLOR SELECTORS =====
function setQuickColor(index, value) {
    pushZoneUndo('Set color');
    zones[index].color = value;
    zones[index].colorMode = 'quick';
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setSpecialColor(index, value) {
    pushZoneUndo();
    zones[index].color = value;
    zones[index].colorMode = 'special';
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setTextColor(index, value) {
    pushZoneUndo();
    if (!value.trim()) {
        zones[index].color = null;
        zones[index].colorMode = 'none';
    } else {
        zones[index].color = value.trim();
        zones[index].colorMode = 'text';
    }
    zones[index].colors = []; // Clear multi-color stack
    renderZones();
    triggerPreviewRender();
}

function setPickerColor(index, hexValue) {
    const r = parseInt(hexValue.substr(1, 2), 16);
    const g = parseInt(hexValue.substr(3, 2), 16);
    const b = parseInt(hexValue.substr(5, 2), 16);
    zones[index].pickerColor = hexValue;
    zones[index].color = { color_rgb: [r, g, b], tolerance: zones[index].pickerTolerance || 40 };
    zones[index].colorMode = 'picker';
    zones[index].colors = []; // Clear multi-color stack when setting single color via picker
    renderZones();
    triggerPreviewRender();
}

function setPickerTolerance(index, value) {
    zones[index].pickerTolerance = parseInt(value);
    if (zones[index].colorMode === 'picker' && typeof zones[index].color === 'object' && zones[index].color !== null) {
        zones[index].color.tolerance = parseInt(value);
    }
    renderZones();
    triggerPreviewRender();
}

// ===== HEX CODE COLOR =====
function setHexColor(index, hex) {
    hex = hex.trim();
    if (!hex) {
        // Only clear if NOT in multi-color mode (don't wipe the stack)
        if (zones[index].colorMode !== 'multi') {
            zones[index].color = null;
            zones[index].colorMode = 'none';
        }
        renderZones();
        triggerPreviewRender();
        return;
    }
    // Normalize: add # if missing
    if (!hex.startsWith('#')) hex = '#' + hex;
    // Validate hex
    if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) {
        showToast('Enter a valid hex code like #FF3366', true);
        return;
    }
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    const tol = zones[index].pickerTolerance || 40;
    zones[index].pickerColor = hex;

    // If zone is already in multi-color mode, add to the stack
    if (zones[index].colorMode === 'multi' && zones[index].colors.length > 0) {
        if (zones[index].colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
            showToast('That color is already in this zone', true);
            return;
        }
        zones[index].colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
        zones[index].color = zones[index].colors;
        renderZones();
        triggerPreviewRender();
        showToast(`Added ${hex.toUpperCase()} to ${zones[index].name} (${zones[index].colors.length} colors stacked)`);
    } else {
        // Single color mode
        zones[index].color = { color_rgb: [r, g, b], tolerance: tol };
        zones[index].colorMode = 'picker';
        renderZones();
        triggerPreviewRender();
        showToast(`Zone ${index + 1}: color set to ${hex.toUpperCase()}`);
    }
}

// ===== SWATCH PICKER POPUP =====
let swatchPopupState = { open: false, type: null, zoneIndex: -1, layerIndex: -1 };

// Determine finish type for a given ID (needed to pick the right /api/swatch path)
function getFinishType(id) {
    if (!id || id === 'none') return null;
    // Check the smaller sets first - anything not in BASES or PATTERNS is a monolithic/special
    if (typeof BASES !== 'undefined' && BASES.find(b => b.id === id)) return 'base';
    if (typeof PATTERNS !== 'undefined' && PATTERNS.find(p => p.id === id)) return 'pattern';
    return 'monolithic';  // default: all 1100+ specials land here
}

// Build the /api/swatch URL for a given finish + optional hint color
// Returns null if ShokkerAPI is not yet online (fallback to color dot)
// Patterns get ?mode=split → 2x-wide image: left=pattern texture, right=with user color
function getSwatchUrl(finishId, colorHex, forceSplit) {
    const type = getFinishType(finishId);
    if (!type) return null;
    const col = (colorHex || '888888').replace('#', '');
    const base = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl)
        ? ShokkerAPI.baseUrl
        : `http://localhost:${window._SHOKKER_PORT || 59876}`;
    // Patterns: split view unless explicitly disabled
    const splitMode = (forceSplit !== false && type === 'pattern') ? '&mode=split' : '';
    return `${base}/api/swatch/${type}/${finishId}?color=${col}&size=48${splitMode}`;
}

function renderSwatchSquare(finishId, fallbackColor, title, colorHex) {
    if (!finishId || finishId === 'none') {
        return `<div class="swatch-square" style="background:${fallbackColor || '#444'};" title="${title || ''}"></div>`;
    }
    const type = getFinishType(finishId);
    const isPattern = (type === 'pattern');
    const url = getSwatchUrl(finishId, colorHex);  // patterns auto-get mode=split
    if (url) {
        // Patterns: wider 72x36 split image (left=spec structure, right=color applied)
        // Bases/monolithics: standard 36x36
        const w = isPattern ? 72 : 36;
        const h = 36;
        const titleSafe = (title || '').replace(/"/g, '&quot;');
        const fallback = fallbackColor || '#444';
        return `<img class="swatch-square${isPattern ? ' swatch-split' : ''}" src="${url}" title="${title || ''}"
                    loading="lazy"
                    style="width:${w}px;height:${h}px;border-radius:4px;border:1px solid rgba(255,255,255,0.12);object-fit:cover;"
                    onerror="this.outerHTML='<div class=&quot;swatch-square&quot; title=&quot;${titleSafe}&quot; style=&quot;width:36px;height:36px;background:${fallback};&quot;></div>'">`;
    }
    return `<div class="swatch-square" style="background:${fallbackColor || '#444'};" title="${title || ''}"></div>`;
}

function renderSwatchDot(finishId, fallbackColor, colorHex) {
    // Small inline dot for trigger buttons / zone cards - always single swatch, no split
    if (!finishId || finishId === 'none') {
        return `<div class="swatch-dot" style="background:${fallbackColor || '#444'};"></div>`;
    }
    const url = getSwatchUrl(finishId, colorHex, false);  // false = no split mode for dots
    if (url) {
        return `<img class="swatch-dot" src="${url}" loading="lazy"
                    style="width:14px;height:14px;border-radius:3px;border:1px solid rgba(255,255,255,0.15);flex-shrink:0;object-fit:cover;"
                    onerror="this.outerHTML='<div class=&quot;swatch-dot&quot; style=&quot;background:${fallbackColor || '#444'};&quot;></div>'">`;
    }
    return `<div class="swatch-dot" style="background:${fallbackColor || '#444'};"></div>`;
}

function getSwatchColor(zone) {
    if (zone.finish) {
        const m = MONOLITHICS.find(x => x.id === zone.finish);
        return m ? m.swatch : '#444';
    }
    if (zone.base) {
        const b = BASES.find(x => x.id === zone.base);
        return b ? b.swatch : '#444';
    }
    return '#333';
}

function getPatternSwatchColor(patternId) {
    if (!patternId || patternId === 'none') return 'transparent';
    const p = PATTERNS.find(x => x.id === patternId);
    return p ? p.swatch : '#444';
}

// Extract zone's paint color as a 6-char hex string (no #) for /api/swatch tinting
function getZoneColorHex(zone) {
    let rgb = null;
    if (zone.color) {
        if (Array.isArray(zone.color) && zone.color.length > 0) {
            // Multi-color stack - use first color
            const first = zone.color[0];
            rgb = first.color_rgb || null;
        } else if (zone.color.color_rgb) {
            rgb = zone.color.color_rgb;
        }
    }
    if (!rgb || !Array.isArray(rgb) || rgb.length < 3) return '888888';
    const toHex = v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0');
    return toHex(rgb[0]) + toHex(rgb[1]) + toHex(rgb[2]);
}

function getBaseName(zone) {
    if (zone.finish) {
        const m = MONOLITHICS.find(x => x.id === zone.finish);
        return m ? m.name : '(not set)';
    }
    if (zone.base) {
        const b = BASES.find(x => x.id === zone.base);
        return b ? b.name : '(not set)';
    }
    return '(not set)';
}

function getPatternName(patternId) {
    if (!patternId || patternId === 'none') return 'None (Base Only)';
    const p = PATTERNS.find(x => x.id === patternId);
    return p ? p.name : patternId;
}

function openSwatchPicker(triggerEl, type, zoneIndex, layerIndex) {
    const popup = document.getElementById('swatchPopup');
    const grid = document.getElementById('swatchPopupGrid');
    const searchInput = document.getElementById('swatchSearchInput');

    // Close if same trigger clicked again
    if (swatchPopupState.open && swatchPopupState.type === type &&
        swatchPopupState.zoneIndex === zoneIndex && swatchPopupState.layerIndex === (layerIndex ?? -1)) {
        closeSwatchPicker();
        return;
    }

    swatchPopupState = { open: true, type, zoneIndex, layerIndex: layerIndex ?? -1 };

    // Determine current selection
    const zone = zones[zoneIndex];
    let currentId = '';
    if (type === 'base') {
        currentId = zone.finish ? ('mono:' + zone.finish) : (zone.base || '');
    } else if (type === 'pattern') {
        currentId = zone.pattern || 'none';
    } else if (type === 'stackPattern') {
        currentId = (zone.patternStack && zone.patternStack[layerIndex]) ? zone.patternStack[layerIndex].id : 'none';
    }

    // Build grid HTML with canvas-rendered previews
    let html = '';
    if (type === 'base') {
        // Bases section - grouped by BASE_GROUPS with collapsible sections
        html += `<div class="swatch-item${currentId === '' ? ' selected' : ''}" data-name="not set none clear" onclick="selectSwatchItem('')" style="margin-bottom:4px;">
            <div class="swatch-square" style="background:#333;display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:10px;">&#8709;</div>
            <div class="swatch-label">(not set)</div></div>`;
        const baseGroupedIds = new Set();
        Object.keys(BASE_GROUPS).sort((a, b) => a === 'Foundation' ? -1 : b === 'Foundation' ? 1 : a.localeCompare(b)).forEach(groupName => {
            const ids = BASE_GROUPS[groupName];
            if (!ids || ids.length === 0) return;
            const groupBases = ids.map(id => BASES.find(b => b.id === id)).filter(Boolean);
            if (groupBases.length === 0) return;
            groupBases.forEach(b => baseGroupedIds.add(b.id));
            const hasSelected = groupBases.some(b => b.id === currentId);
            const collapsed = !hasSelected;
            html += `<div class="swatch-group${collapsed ? ' collapsed' : ''}">`;
            html += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupBases.length})</span></div>`;
            html += `<div class="swatch-grid-row">`;
            groupBases.forEach(b => {
                html += `<div class="swatch-item${currentId === b.id ? ' selected' : ''}" data-name="${b.name.toLowerCase()}" data-finish-id="${b.id}" data-desc="${(b.desc || b.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${b.id}')">
                    ${renderSwatchSquare(b.id, b.swatch, b.desc)}
                    <div class="swatch-label">${b.name}</div></div>`;
            });
            html += `</div></div>`;
        });
        // Ungrouped bases (safety net)
        const ungroupedBases = BASES.filter(b => !baseGroupedIds.has(b.id));
        if (ungroupedBases.length > 0) {
            html += `<div class="swatch-group"><div class="swatch-group-label">Other Bases <span class="swatch-group-count">(${ungroupedBases.length})</span></div><div class="swatch-grid-row">`;
            ungroupedBases.forEach(b => {
                html += `<div class="swatch-item${currentId === b.id ? ' selected' : ''}" data-name="${b.name.toLowerCase()}" data-finish-id="${b.id}" data-desc="${(b.desc || b.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${b.id}')">
                    ${renderSwatchSquare(b.id, b.swatch, b.desc)}
                    <div class="swatch-label">${b.name}</div></div>`;
            });
            html += '</div></div>';
        }
        // Monolithics - grouped by SPECIAL_GROUPS, separated into Color-Changing vs Effect sections
        const groupedIds = new Set();
        const COLOR_CHANGING_GROUPS = new Set(["Chameleon Classic", "Prizm Series"]);
        const allGroupNames = Object.keys(SPECIAL_GROUPS).sort();
        const colorChangingGroups = allGroupNames.filter(g => COLOR_CHANGING_GROUPS.has(g));
        const effectGroups = allGroupNames.filter(g => !COLOR_CHANGING_GROUPS.has(g));

        function renderGroupSection(groups, sectionLabel, sectionIcon) {
            let s = `<div class="swatch-section-divider" style="margin:10px 0 6px; padding:6px 8px; background:var(--bg-dark); border:1px solid var(--border); border-radius:6px; display:flex; align-items:center; gap:6px;">
                <span style="font-size:12px;">${sectionIcon}</span>
                <span style="font-size:11px; font-weight:700; color:var(--accent-green); text-transform:uppercase; letter-spacing:1px;">${sectionLabel}</span>
                <span style="font-size:9px; color:var(--text-dim); margin-left:auto;">${groups.reduce((n, g) => n + (SPECIAL_GROUPS[g] || []).length, 0)} finishes</span>
            </div>`;
            groups.forEach(groupName => {
                const ids = SPECIAL_GROUPS[groupName];
                if (!ids) return;
                const groupMonos = ids.map(id => MONOLITHICS.find(m => m.id === id)).filter(Boolean);
                if (groupMonos.length === 0) return;
                groupMonos.forEach(m => groupedIds.add(m.id));
                const hasSelected = groupMonos.some(m => 'mono:' + m.id === currentId);
                const isColorGroup = groupName.startsWith('Solid') || groupName.startsWith('Gradient') || groupName.startsWith('Multi');
                const collapsed = isColorGroup && !hasSelected;
                s += `<div class="swatch-group${collapsed ? ' collapsed' : ''}">`;
                s += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupMonos.length})</span></div>`;
                s += `<div class="swatch-grid-row">`;
                groupMonos.forEach(m => {
                    s += `<div class="swatch-item${currentId === 'mono:' + m.id ? ' selected' : ''}" data-name="${m.name.toLowerCase()}" data-finish-id="${m.id}" data-desc="${(m.desc || m.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('mono:${m.id}')">
                        ${renderSwatchSquare(m.id, m.swatch, m.desc)}
                        <div class="swatch-label">${m.name}</div></div>`;
                });
                s += `</div></div>`;
            });
            return s;
        }
        html += renderGroupSection(colorChangingGroups, 'Color-Changing Finishes', '🎨');
        html += renderGroupSection(effectGroups, 'Effect Finishes (keeps paint color)', '✨');
        // Ungrouped monolithics (safety net)
        const ungrouped = MONOLITHICS.filter(m => !groupedIds.has(m.id));
        if (ungrouped.length > 0) {
            html += '<div class="swatch-group"><div class="swatch-group-label">Other</div><div class="swatch-grid-row">';
            ungrouped.forEach(m => {
                html += `<div class="swatch-item${currentId === 'mono:' + m.id ? ' selected' : ''}" data-name="${m.name.toLowerCase()}" data-finish-id="${m.id}" data-desc="${(m.desc || m.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('mono:${m.id}')">
                    ${renderSwatchSquare(m.id, m.swatch, m.desc)}
                    <div class="swatch-label">${m.name}</div></div>`;
            });
            html += '</div></div>';
        }
    } else {
        // Pattern / stackPattern - grouped by PATTERN_GROUPS with collapsible sections
        html += `<div class="swatch-item${currentId === 'none' ? ' selected' : ''}" data-name="none not set clear" onclick="selectSwatchItem('none')" style="margin-bottom:4px;">
            <div class="swatch-square" style="background:#333;display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:10px;">&#8709;</div>
            <div class="swatch-label">None</div></div>`;
        const patGroupedIds = new Set();
        Object.keys(PATTERN_GROUPS).sort().forEach(groupName => {
            const ids = PATTERN_GROUPS[groupName];
            if (!ids || ids.length === 0) return;
            const groupPats = ids.map(id => PATTERNS.find(p => p.id === id)).filter(Boolean);
            if (groupPats.length === 0) return;
            groupPats.forEach(p => patGroupedIds.add(p.id));
            const hasSelected = groupPats.some(p => p.id === currentId);
            const collapsed = !hasSelected;
            html += `<div class="swatch-group${collapsed ? ' collapsed' : ''}">`;
            html += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupPats.length})</span></div>`;
            html += `<div class="swatch-grid-row">`;
            groupPats.forEach(p => {
                html += `<div class="swatch-item${currentId === p.id ? ' selected' : ''}" data-name="${p.name.toLowerCase()}" data-finish-id="${p.id}" data-desc="${(p.desc || p.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${p.id}')">
                    ${renderSwatchSquare(p.id, p.swatch, p.desc)}
                    <div class="swatch-label">${p.name}</div></div>`;
            });
            html += `</div></div>`;
        });
        // Ungrouped patterns (safety net)
        const ungroupedPats = PATTERNS.filter(p => p.id !== 'none' && !patGroupedIds.has(p.id));
        if (ungroupedPats.length > 0) {
            html += `<div class="swatch-group"><div class="swatch-group-label">Other <span class="swatch-group-count">(${ungroupedPats.length})</span></div><div class="swatch-grid-row">`;
            ungroupedPats.forEach(p => {
                html += `<div class="swatch-item${currentId === p.id ? ' selected' : ''}" data-name="${p.name.toLowerCase()}" data-finish-id="${p.id}" data-desc="${(p.desc || p.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${p.id}')">
                    ${renderSwatchSquare(p.id, p.swatch, p.desc)}
                    <div class="swatch-label">${p.name}</div></div>`;
            });
            html += '</div></div>';
        }
    }

    grid.innerHTML = html;

    // Position popup near trigger
    const rect = triggerEl.getBoundingClientRect();
    const popupW = 340;
    const popupH = Math.min(400, window.innerHeight - 40);

    let left = rect.right + 8;
    if (left + popupW > window.innerWidth - 10) left = rect.left - popupW - 8;
    if (left < 10) left = 10;

    let top = rect.top;
    if (top + popupH > window.innerHeight - 10) top = window.innerHeight - popupH - 10;
    if (top < 10) top = 10;

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.classList.add('active');

    searchInput.value = '';
    setTimeout(() => searchInput.focus(), 50);
}

function closeSwatchPicker() {
    const popup = document.getElementById('swatchPopup');
    if (popup) popup.classList.remove('active');
    swatchPopupState = { open: false, type: null, zoneIndex: -1, layerIndex: -1 };
}

function filterSwatchPopup(query) {
    const grid = document.getElementById('swatchPopupGrid');
    const items = grid.querySelectorAll('.swatch-item');
    const q = query.toLowerCase().trim();
    items.forEach(item => {
        const name = item.getAttribute('data-name') || '';
        const desc = (item.getAttribute('data-desc') || '').toLowerCase();
        item.style.display = (!q || name.includes(q) || desc.includes(q)) ? '' : 'none';
    });
    // Show/hide groups based on visible items; expand all when searching
    const groups = grid.querySelectorAll('.swatch-group');
    groups.forEach(grp => {
        const visibleItems = grp.querySelectorAll('.swatch-item:not([style*="display: none"])');
        grp.style.display = (q && visibleItems.length === 0) ? 'none' : '';
        if (q) grp.classList.remove('collapsed');
        else if (visibleItems.length > 0 && !grp.querySelector('.swatch-item.selected')) grp.classList.add('collapsed');
    });
}

function selectSwatchItem(id) {
    const { type, zoneIndex, layerIndex } = swatchPopupState;
    if (type === 'base') {
        setZoneBase(zoneIndex, id);
    } else if (type === 'pattern') {
        setZonePattern(zoneIndex, id);
    } else if (type === 'stackPattern') {
        setPatternLayerId(zoneIndex, layerIndex, id);
    }
    closeSwatchPicker();
}

// Close swatch picker on click outside
document.addEventListener('mousedown', function (e) {
    if (!swatchPopupState.open) return;
    const popup = document.getElementById('swatchPopup');
    if (!popup.contains(e.target) && !e.target.closest('.swatch-trigger')) {
        closeSwatchPicker();
    }
});
// Close swatch picker on Escape
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && swatchPopupState.open) {
        closeSwatchPicker();
        e.stopPropagation();
    }
});

// ===== FINISH SELECTORS =====
// ===== ZONE LINKING / GROUPS =====
let nextLinkGroupId = 1;

function linkZones(indices) {
    if (!indices || indices.length < 2) return;
    pushZoneUndo();
    const groupId = 'link_' + (nextLinkGroupId++);
    indices.forEach(i => { if (zones[i]) zones[i].linkGroup = groupId; });
    renderZones();
    showToast(`Linked ${indices.length} zones (Group ${groupId.replace('link_', '')})`);
}

function unlinkZone(index) {
    if (!zones[index] || !zones[index].linkGroup) return;
    pushZoneUndo();
    const group = zones[index].linkGroup;
    zones[index].linkGroup = null;
    // If only 1 zone left in group, auto-unlink it too
    const remaining = zones.filter(z => z.linkGroup === group);
    if (remaining.length === 1) remaining[0].linkGroup = null;
    renderZones();
    showToast('Zone unlinked');
}

function linkSelectedToZone(targetIndex) {
    // Link the currently selected zone to the target zone's group (or create new group)
    const srcIdx = selectedZoneIndex;
    if (srcIdx < 0 || srcIdx === targetIndex) return;
    pushZoneUndo();
    if (zones[targetIndex].linkGroup) {
        zones[srcIdx].linkGroup = zones[targetIndex].linkGroup;
    } else {
        const groupId = 'link_' + (nextLinkGroupId++);
        zones[srcIdx].linkGroup = groupId;
        zones[targetIndex].linkGroup = groupId;
    }
    renderZones();
    showToast(`Zones linked together`);
}

function propagateToLinkedZones(sourceIndex, props) {
    // Copy finish properties from source zone to all zones in the same link group
    const zone = zones[sourceIndex];
    if (!zone || !zone.linkGroup) return;
    zones.forEach((z, i) => {
        if (i === sourceIndex || z.linkGroup !== zone.linkGroup) return;
        props.forEach(p => { z[p] = zone[p]; });
    });
}

const LINK_FINISH_PROPS = ['base', 'pattern', 'finish', 'intensity', 'scale', 'rotation',
    'patternOpacity', 'customSpec', 'customPaint', 'customBright', 'patternStack', 'wear'];

function promptLinkZone(index) {
    if (zones[index].linkGroup) {
        // Already linked - offer to unlink
        unlinkZone(index);
        return;
    }
    // Show a simple picker: which zone to link with?
    const options = zones.map((z, i) => i === index ? null : `${i + 1}. ${z.name}`).filter(Boolean);
    const choice = prompt(`Link "${zones[index].name}" with which zone?\n\n${options.join('\n')}\n\nEnter zone number:`);
    if (!choice) return;
    const targetIdx = parseInt(choice) - 1;
    if (isNaN(targetIdx) || targetIdx < 0 || targetIdx >= zones.length || targetIdx === index) {
        showToast('Invalid zone number');
        return;
    }
    pushZoneUndo();
    if (zones[targetIdx].linkGroup) {
        zones[index].linkGroup = zones[targetIdx].linkGroup;
    } else {
        const groupId = 'link_' + (nextLinkGroupId++);
        zones[index].linkGroup = groupId;
        zones[targetIdx].linkGroup = groupId;
    }
    // Copy finish from target to source so they match
    LINK_FINISH_PROPS.forEach(p => { zones[index][p] = zones[targetIdx][p]; });
    renderZones();
    triggerPreviewRender();
    showToast(`Linked: ${zones[index].name} + ${zones[targetIdx].name}`);
}

function setZoneBase(index, value) {
    pushZoneUndo('Set base: ' + (value || 'none'));
    if (value && value.startsWith('mono:')) {
        // Monolithic finish selected
        const monoId = value.replace('mono:', '');
        zones[index].finish = monoId;
        zones[index].base = null;
        zones[index].pattern = null;
        zones[index].patternStack = [];
    } else {
        zones[index].base = value || null;
        zones[index].finish = null; // Clear monolithic
        if (!zones[index].pattern) zones[index].pattern = 'none';
    }
    propagateToLinkedZones(index, LINK_FINISH_PROPS);
    renderZones();
    triggerPreviewRender();
}

function setZonePattern(index, patternId) {
    pushZoneUndo('Set pattern: ' + (patternId || 'none'));
    zones[index].pattern = patternId || 'none';
    propagateToLinkedZones(index, ['pattern']);
    renderZones();  // Re-render to show/hide scale slider
    triggerPreviewRender();
}

function setZonePatternOpacity(index, val) {
    zones[index].patternOpacity = parseInt(val) || 100;
    const label = document.getElementById('detPatOpVal' + index) || document.getElementById('patOpVal' + index);
    if (label) label.textContent = val + '%';
    triggerPreviewRender();
}

function setZoneScale(index, val) {
    pushZoneUndo('Set scale', true);
    zones[index].scale = parseFloat(val) || 1.0;
    const label = document.getElementById('detScaleVal' + index) || document.getElementById('scaleVal' + index);
    if (label) label.textContent = zones[index].scale.toFixed(2) + 'x';
    triggerPreviewRender();
}

function resetZoneScale(index) {
    pushZoneUndo('Reset scale');
    zones[index].scale = 1.0;
    renderZones();
    triggerPreviewRender();
}

function setZoneBaseScale(index, val) {
    pushZoneUndo('Set base scale', true);
    zones[index].baseScale = parseFloat(val) || 1.0;
    const label = document.getElementById('detBaseScaleVal' + index);
    if (label) label.textContent = zones[index].baseScale.toFixed(1) + 'x';
    triggerPreviewRender();
}

function resetZoneBaseScale(index) {
    pushZoneUndo('Reset base scale');
    zones[index].baseScale = 1.0;
    renderZones();
    triggerPreviewRender();
}

function setZoneRotation(index, val) {
    pushZoneUndo('Set rotation', true);
    const v = Math.max(0, Math.min(359, parseInt(val) || 0));
    zones[index].rotation = v;
    // Sync both number inputs and sliders
    ['detRotVal', 'rotVal'].forEach(prefix => {
        const el = document.getElementById(prefix + index);
        if (el) el.value = v;
    });
    document.querySelectorAll(`input[type="range"][oninput*="setZoneRotation(${index},"]`).forEach(sl => { sl.value = v; });
    triggerPreviewRender();
}

function resetZoneRotation(index) {
    pushZoneUndo();
    zones[index].rotation = 0;
    renderZones();
    triggerPreviewRender();
}

function setZoneBaseRotation(index, val) {
    pushZoneUndo('Set base rotation', true);
    const v = Math.max(0, Math.min(359, parseInt(val) || 0));
    zones[index].baseRotation = v;
    // Sync both number inputs and sliders
    ['detBaseRotVal', 'baseRotVal'].forEach(prefix => {
        const el = document.getElementById(prefix + index);
        if (el) el.value = v;
    });
    // Sync range sliders too (they won't have these IDs, find via parent)
    document.querySelectorAll(`input[type="range"][oninput*="setZoneBaseRotation(${index},"]`).forEach(sl => { sl.value = v; });
    triggerPreviewRender();
}

function resetZoneBaseRotation(index) {
    pushZoneUndo('Reset base rotation');
    zones[index].baseRotation = 0;
    renderZones();
    triggerPreviewRender();
}

// ===== DUAL LAYER BASE OVERLAY SETTERS =====
function setZoneSecondBase(index, val) {
    pushZoneUndo('Set overlay base');
    zones[index].secondBase = val || '';
    if (!val) { zones[index].secondBaseStrength = 0; }
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBaseColor(index, val) {
    pushZoneUndo('Set overlay color', true);
    zones[index].secondBaseColor = val || '#ffffff';
    triggerPreviewRender();
}
function setZoneSecondBaseStrength(index, val) {
    pushZoneUndo('Set overlay strength', true);
    zones[index].secondBaseStrength = (parseInt(val) || 0) / 100;
    const label = document.getElementById('detSBStrVal' + index);
    if (label) label.textContent = (parseInt(val) || 0) + '%';
    triggerPreviewRender();
}
function setZoneSecondBaseBlendMode(index, val) {
    pushZoneUndo('Set overlay blend mode');
    zones[index].secondBaseBlendMode = val || 'noise';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneSecondBaseNoiseScale(index, val) {
    pushZoneUndo('Set overlay noise scale', true);
    zones[index].secondBaseNoiseScale = parseInt(val) || 24;
    const label = document.getElementById('detSBNSVal' + index);
    if (label) label.textContent = (parseInt(val) || 24) + 'px';
    triggerPreviewRender();
}

// ===== LEGACY v6 SETTERS (kept for backward compat) =====
function setZoneCCQuality(index, val) {
    pushZoneUndo('Set CC quality', true);
    zones[index].ccQuality = parseInt(val) || 100;
    const label = document.getElementById('detCCQVal' + index);
    if (label) label.textContent = zones[index].ccQuality + '%';
    triggerPreviewRender();
}
function resetZoneCCQuality(index) {
    pushZoneUndo('Reset CC quality');
    zones[index].ccQuality = 100;
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBlendBase(index, val) {
    pushZoneUndo('Set blend base');
    zones[index].blendBase = val || '';
    renderZoneDetail(index);
    triggerPreviewRender();
}
function setZoneBlendDir(index, val) {
    pushZoneUndo('Set blend direction');
    zones[index].blendDir = val || 'horizontal';
    triggerPreviewRender();
}
function setZoneBlendAmount(index, val) {
    pushZoneUndo('Set blend amount');
    zones[index].blendAmount = parseInt(val) || 50;
    const label = document.getElementById('detBlendAmtVal' + index);
    if (label) label.textContent = zones[index].blendAmount + '%';
    triggerPreviewRender();
}
function setZonePaintReactiveColor(index, val) {
    pushZoneUndo('Set paint-reactive color');
    zones[index].paintReactiveColor = val || '#000000';
    triggerPreviewRender();
}
function setZoneUsePaintReactive(index, checked) {
    pushZoneUndo('Toggle paint-reactive');
    zones[index].usePaintReactive = !!checked;
    triggerPreviewRender();
}

function setPatternLayerRotation(zoneIdx, layerIdx, val) {
    pushZoneUndo();
    const intVal = parseInt(val) || 0;
    if (zones[zoneIdx].patternStack && zones[zoneIdx].patternStack[layerIdx]) {
        zones[zoneIdx].patternStack[layerIdx].rotation = intVal;
    }
    // Live update both slider and number input in the layer row
    const detRow = document.querySelectorAll(`#zoneDetailPanel .pattern-stack-layer`)[layerIdx];
    const cardRow = document.querySelectorAll(`#zone-card-${zoneIdx} .pattern-stack-layer`)[layerIdx];
    [detRow, cardRow].forEach(row => {
        if (!row) return;
        const groups = row.querySelectorAll('.stack-control-group');
        const rotGroup = groups[2]; // 0=opacity, 1=scale, 2=rotate
        if (!rotGroup) return;
        const slider = rotGroup.querySelector('input[type="range"]');
        const numInput = rotGroup.querySelector('input[type="number"]');
        if (slider && slider !== document.activeElement) slider.value = intVal;
        if (numInput && numInput !== document.activeElement) numInput.value = intVal;
    });
    triggerPreviewRender();
}

// ===== IMPORT SPEC MAP (MERGE MODE) =====
function importSpecMapFromFile() {
    // Use the existing browse filesystem to pick a TGA
    let startPath = '';
    const currentPaint = document.getElementById('paintFile').value.trim();
    if (currentPaint) startPath = currentPaint.replace(/[/\\][^/\\]+$/, '');
    openFilePicker({
        title: 'Select Spec Map TGA to Import',
        filter: '.tga',
        mode: 'file',
        startPath: startPath,
        onSelect: function (filePath) {
            if (!filePath) return;
            fetch('/upload-spec-map', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ spec_path: filePath })
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        importedSpecMapPath = data.temp_path;
                        const status = document.getElementById('importSpecMapStatus');
                        if (status) {
                            const fname = filePath.split('/').pop().split('\\').pop();
                            status.innerHTML = `<span style="color: var(--accent-green);">&#10003;</span> <strong>${fname}</strong> (${data.resolution[0]}x${data.resolution[1]})`;
                        }
                        document.getElementById('btnClearSpecMap').disabled = false;
                        showToast('Spec map imported - zones will merge on top');
                        triggerPreviewRender();
                    } else {
                        showToast('Failed to import spec map: ' + (data.error || 'unknown'), true);
                    }
                })
                .catch(err => showToast('Spec map import error: ' + err, true));
        }
    });
}

function importSpecMapFromDrop(file) {
    // Handle drag-drop or file input of a TGA/PNG spec map
    const reader = new FileReader();
    reader.onload = function (e) {
        fetch('/upload-spec-map', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spec_data: e.target.result })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    importedSpecMapPath = data.temp_path;
                    const status = document.getElementById('importSpecMapStatus');
                    if (status) {
                        status.innerHTML = `<span style="color: var(--accent-green);">&#10003;</span> <strong>${file.name}</strong> (${data.resolution[0]}x${data.resolution[1]})`;
                    }
                    document.getElementById('btnClearSpecMap').disabled = false;
                    showToast('Spec map imported - zones will merge on top');
                    triggerPreviewRender();
                } else {
                    showToast('Failed to import spec map: ' + (data.error || 'unknown'), true);
                }
            })
            .catch(err => showToast('Spec map import error: ' + err, true));
    };
    reader.readAsDataURL(file);
}

function clearImportedSpecMap() {
    importedSpecMapPath = null;
    const status = document.getElementById('importSpecMapStatus');
    if (status) status.textContent = 'No spec map imported - zones render on default base';
    document.getElementById('btnClearSpecMap').disabled = true;
    showToast('Imported spec map cleared');
    triggerPreviewRender();
}

// ===== PATTERN STACK CONTROLS =====
function addPatternLayer(zoneIdx) {
    pushZoneUndo();
    if (!zones[zoneIdx].patternStack) zones[zoneIdx].patternStack = [];
    if (zones[zoneIdx].patternStack.length >= 5) { showToast('Max 5 stacked layers!', true); return; }
    zones[zoneIdx].patternStack.push({ id: 'none', opacity: 100, scale: 1.0, rotation: 0, blendMode: 'normal' });
    renderZones();
    triggerPreviewRender();
}

function removePatternLayer(zoneIdx, layerIdx) {
    pushZoneUndo();
    zones[zoneIdx].patternStack.splice(layerIdx, 1);
    renderZones();
    triggerPreviewRender();
}

function setPatternLayerId(zoneIdx, layerIdx, val) {
    pushZoneUndo();
    zones[zoneIdx].patternStack[layerIdx].id = val;
    renderZones();
    triggerPreviewRender();
}

function setPatternLayerOpacity(zoneIdx, layerIdx, val) {
    zones[zoneIdx].patternStack[layerIdx].opacity = parseInt(val) || 100;
    // Live update the value label without full re-render - check detail panel first, then card
    const detRow = document.querySelectorAll(`#zoneDetailPanel .pattern-stack-layer`)[layerIdx];
    const cardRow = document.querySelectorAll(`#zone-card-${zoneIdx} .pattern-stack-layer`)[layerIdx];
    const row = detRow || cardRow;
    if (row) {
        const vals = row.querySelectorAll('.stack-val');
        if (vals[0]) vals[0].textContent = val + '%';
    }
    triggerPreviewRender();
}

function setPatternLayerScale(zoneIdx, layerIdx, val) {
    zones[zoneIdx].patternStack[layerIdx].scale = parseFloat(val) || 1.0;
    // Check detail panel first, then card
    const detRow = document.querySelectorAll(`#zoneDetailPanel .pattern-stack-layer`)[layerIdx];
    const cardRow = document.querySelectorAll(`#zone-card-${zoneIdx} .pattern-stack-layer`)[layerIdx];
    const row = detRow || cardRow;
    if (row) {
        const vals = row.querySelectorAll('.stack-val');
        if (vals[1]) vals[1].textContent = parseFloat(val).toFixed(2) + 'x';
    }
    triggerPreviewRender();
}

function setPatternLayerBlend(zoneIdx, layerIdx, val) {
    zones[zoneIdx].patternStack[layerIdx].blendMode = val;
    triggerPreviewRender();
}

function setZoneWear(index, val) {
    pushZoneUndo();
    zones[index].wear = parseInt(val) || 0;
    const label = document.getElementById('detWearVal' + index) || document.getElementById('wearVal' + index);
    if (label) label.textContent = zones[index].wear + '%';
    triggerPreviewRender();
}

function setZoneFinish(index, finishId) {
    // Legacy compat
    zones[index].finish = finishId || null;
    zones[index].base = null;
    zones[index].pattern = null;
}

function setZoneIntensity(index, intensity, fromSlider) {
    if (intensity === 'custom') {
        // Switching to custom - keep current slider values or init from current preset
        pushZoneUndo();
        const z = zones[index];
        if (z.customSpec == null) {
            const vals = INTENSITY_VALUES[z.intensity] || INTENSITY_VALUES["100"];
            z.customSpec = vals.spec;
            z.customPaint = vals.paint;
            z.customBright = vals.bright;
        }
        renderZones();
        triggerPreviewRender();
        return;
    }
    // Clamp to 0-100
    const numVal = Math.max(0, Math.min(100, parseInt(intensity) || 100));
    // Store as string for backward compat with existing presets
    zones[index].intensity = String(numVal);
    zones[index].customSpec = null;
    zones[index].customPaint = null;
    zones[index].customBright = null;
    propagateToLinkedZones(index, ['intensity', 'customSpec', 'customPaint', 'customBright']);
    // CRITICAL: Do NOT call renderZones() when called from a slider drag event -
    // doing so rebuilds the DOM and repositions the slider back to stored value (jump bug).
    // Instead, just sync sibling inputs and labels without touching the slider itself.
    if (!fromSlider) {
        pushZoneUndo();
        renderZones();
    } else {
        // Sync only the number input and summary text in the card without rebuilding DOM
        // Find sibling number input: the range and number input are siblings in the row
        const card = document.getElementById('zone-card-' + index);
        if (card) {
            // Sync number inputs that share value with this slider
            card.querySelectorAll('.intensity-control-group input[type="number"]').forEach(el => {
                if (el !== document.activeElement) el.value = numVal;
            });
            // Also sync the detail panel if open
            const detPanel = document.getElementById('zoneDetailPanel');
            if (detPanel) {
                detPanel.querySelectorAll('.intensity-control-group input[type="number"]').forEach(el => {
                    if (el !== document.activeElement) el.value = numVal;
                });
                detPanel.querySelectorAll('.intensity-control-group input[type="range"]').forEach(el => {
                    if (el !== document.activeElement) el.value = numVal;
                });
            }
        }
    }
    triggerPreviewRender();
}

// Tick intensity up or down by delta (usually ±1)
function tickZoneIntensity(index, delta) {
    const current = parseInt(zones[index].intensity) || 100;
    const next = Math.max(0, Math.min(100, current + delta));
    setZoneIntensity(index, String(next));
}

function setZonePatternIntensity(index, value) {
    const numVal = Math.max(0, Math.min(100, parseInt(value) || 100));
    zones[index].patternIntensity = String(numVal);
    propagateToLinkedZones(index, ['patternIntensity']);
    pushZoneUndo();
    renderZones();
    triggerPreviewRender();
}

// Helper: get intensity multiplier for any 0-100 value
// Falls back to INTENSITY_VALUES for exact presets, otherwise linearly maps
function getIntensityMultiplier(zone) {
    if (zone.customSpec != null) {
        return { spec: zone.customSpec, paint: zone.customPaint, bright: zone.customBright };
    }
    const preset = INTENSITY_VALUES[zone.intensity];
    if (preset) return preset;
    // Fallback: linear 0-100 → 0.0-1.0
    const pct = (parseInt(zone.intensity) || 100) / 100;
    return { spec: pct, paint: pct, bright: pct };
}

function setCustomIntensity(index, param, value) {
    pushZoneUndo('Set intensity', true);
    const z = zones[index];
    const v = parseFloat(value);
    // Ensure we're in custom mode
    if (z.customSpec == null) {
        const vals = INTENSITY_VALUES[z.intensity] || INTENSITY_VALUES["100"];
        z.customSpec = vals.spec;
        z.customPaint = vals.paint;
        z.customBright = vals.bright;
    }
    if (param === 'spec') z.customSpec = v;
    else if (param === 'paint') z.customPaint = v;
    else if (param === 'bright') z.customBright = v;
    // Update value display (check detail panel first, then card)
    const el = document.getElementById(`detIntSpecVal${index}`) || document.getElementById(`intSpecVal${index}`);
    if (el) el.textContent = z.customSpec.toFixed(2);
    const el2 = document.getElementById(`detIntPaintVal${index}`) || document.getElementById(`intPaintVal${index}`);
    if (el2) el2.textContent = z.customPaint.toFixed(2);
    const el3 = document.getElementById(`detIntBrightVal${index}`) || document.getElementById(`intBrightVal${index}`);
    if (el3) el3.textContent = z.customBright.toFixed(3);
    triggerPreviewRender();
}

function toggleIntensitySliders(index) {
    // Check detail panel first, then card
    const panel = document.getElementById(`detIntSliders${index}`) || document.getElementById(`intSliders${index}`);
    const arrow = document.getElementById(`detIntArrow${index}`) || document.getElementById(`intArrow${index}`);
    if (panel) {
        panel.classList.toggle('open');
        if (arrow) arrow.classList.toggle('open');
    }
}

function assignFinishToSelected(finishId) {
    if (selectedZoneIndex >= 0 && selectedZoneIndex < zones.length) {
        pushZoneUndo('Assign finish: ' + finishId);
        const zone = zones[selectedZoneIndex];
        console.log(`[assignFinish] Zone ${selectedZoneIndex} (${zone.name}): assigning ${finishId}, was base=${zone.base} finish=${zone.finish}`);
        // Check if it's a base, pattern, or monolithic
        const base = BASES.find(b => b.id === finishId);
        const pattern = PATTERNS.find(p => p.id === finishId);
        const mono = MONOLITHICS.find(m => m.id === finishId);

        if (base) {
            zone.base = finishId;
            zone.finish = null;
            if (!zone.pattern) zone.pattern = 'none';
            console.log(`[assignFinish] Set base=${zone.base}, finish=${zone.finish}`);
            renderZones();
            triggerPreviewRender();
            showToast(`Base: ${base.name} => ${zone.name}`);
        } else if (pattern) {
            // If a monolithic is already set, ADD the pattern on top (don't clear the monolithic)
            if (zone.finish) {
                zone.pattern = finishId;
                // Keep zone.finish intact - pattern overlays on monolithic
                renderZones();
                triggerPreviewRender();
                const monoName = MONOLITHICS.find(m => m.id === zone.finish)?.name || zone.finish;
                showToast(`Pattern: ${pattern.name} over ${monoName} => ${zone.name}`);
            } else {
                if (!zone.base) zone.base = 'gloss'; // Default base if none set
                zone.pattern = finishId;
                renderZones();
                triggerPreviewRender();
                showToast(`Pattern: ${pattern.name} => ${zone.name}`);
            }
        } else if (mono) {
            zone.finish = finishId;
            zone.base = null;
            // Keep existing pattern if one is set (pattern can overlay on monolithic)
            // zone.pattern is preserved - user can keep or remove it
            console.log(`[assignFinish] Set mono finish=${zone.finish}, base=${zone.base}`);
            renderZones();
            triggerPreviewRender();
            const patLabel = (zone.pattern && zone.pattern !== 'none') ? ` (keeping ${PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern} overlay)` : '';
            showToast(`Special: ${mono.name}${patLabel} => ${zone.name}`);
        } else {
            // Legacy fallback
            zone.finish = finishId;
            zone.base = null;
            zone.pattern = null;
            console.log(`[assignFinish] Legacy fallback: finish=${zone.finish}`);
            renderZones();
            triggerPreviewRender();
            showToast(`Assigned ${finishId} to ${zone.name}`);
        }
        console.log(`[assignFinish] AFTER: zone ${selectedZoneIndex} base=${zones[selectedZoneIndex].base} finish=${zones[selectedZoneIndex].finish}`);
    }
}


// ===== FINISH FAVORITES (localStorage) =====
let _favoriteFinishes = new Set(JSON.parse(localStorage.getItem('shokker_favorites') || '[]'));
let _showFavoritesOnly = false;

function toggleFavorite(finishId, event) {
    if (event) { event.stopPropagation(); event.preventDefault(); }
    if (_favoriteFinishes.has(finishId)) {
        _favoriteFinishes.delete(finishId);
    } else {
        _favoriteFinishes.add(finishId);
    }
    localStorage.setItem('shokker_favorites', JSON.stringify([..._favoriteFinishes]));
    renderFinishLibrary();
}

function isFavorite(finishId) {
    return _favoriteFinishes.has(finishId);
}

function toggleFavoritesOnly() {
    _showFavoritesOnly = !_showFavoritesOnly;
    const btn = document.getElementById('btnFavoritesOnly');
    if (btn) {
        btn.textContent = _showFavoritesOnly ? '★' : '☆';
        btn.style.color = _showFavoritesOnly ? '#ffaa00' : '';
        btn.style.borderColor = _showFavoritesOnly ? '#ffaa00' : '';
    }
    renderFinishLibrary();
}

// ===== FINISH LIBRARY RENDERING (v3.0 tabbed) =====
let activeLibraryTab = 'bases'; // 'bases' | 'patterns' | 'specials'

let activeLibraryGroup = null; // legacy compat
const _expandedGroups = new Set(); // tracks which accordion groups are open

function toggleLibraryGroup(groupName) {
    if (_expandedGroups.has(groupName)) {
        _expandedGroups.delete(groupName);
    } else {
        _expandedGroups.add(groupName);
    }
    renderFinishLibrary();
}

function expandAllLibraryGroups() {
    const GROUP_MAPS = { bases: BASE_GROUPS, patterns: PATTERN_GROUPS, specials: SPECIAL_GROUPS };
    const groupMap = GROUP_MAPS[activeLibraryTab] || {};
    Object.keys(groupMap).forEach(gn => _expandedGroups.add(gn));
    renderFinishLibrary();
}

function collapseAllLibraryGroups() {
    _expandedGroups.clear();
    renderFinishLibrary();
}

function _renderFinishItem(item, type) {
    const isFav = isFavorite(item.id);
    const starIcon = isFav ? '★' : '☆';
    const starColor = isFav ? 'color:#ffaa00;' : 'color:var(--text-dim);';
    const swatchUrl = getSwatchUrl(item.id, '888888');
    const swatchHtml = swatchUrl
        ? `<img class="finish-swatch-canvas" src="${swatchUrl}" loading="lazy"
                       style="width:40px;height:40px;border-radius:4px;object-fit:cover;flex-shrink:0;"
                       onerror="this.style.background='${item.swatch || '#444'}';this.removeAttribute('src')">`
        : `<div class="finish-swatch-canvas" style="width:40px;height:40px;border-radius:4px;background:${item.swatch || '#444'};flex-shrink:0;"></div>`;
    return `
        <div class="finish-item" onclick="assignFinishToSelected('${item.id}')"
             onmouseenter="showFinishPopup(event, '${item.id}')"
             onmouseleave="hideFinishPopup()"
             data-name="${escapeHtml(item.name).toLowerCase()}"
             data-desc="${escapeHtml(item.desc).toLowerCase()}"
             data-id="${item.id}">
            ${swatchHtml}
            <div class="finish-item-info">
                <div class="finish-item-name">${item.name}</div>
                <div class="finish-item-desc">${item.desc}</div>
            </div>
            <span onclick="toggleFavorite('${item.id}', event)" title="${isFav ? 'Remove from favorites' : 'Add to favorites'}" style="cursor:pointer; font-size:14px; ${starColor} padding:0 4px; flex-shrink:0; transition:color 0.15s;">${starIcon}</span>
            <span class="finish-item-assign">${type === 'base' ? 'Set Base' : type === 'pattern' ? 'Set Pattern' : 'Assign'}</span>
        </div>`;
}

function renderFinishLibrary() {
    const container = document.getElementById('finishLibrary');
    const GROUP_MAPS = { bases: BASE_GROUPS, patterns: PATTERN_GROUPS, specials: SPECIAL_GROUPS };
    const tabs = [
        { id: 'bases', label: `Bases (${BASES.length})`, items: BASES, type: 'base' },
        { id: 'patterns', label: `Patterns (${PATTERNS.length})`, items: PATTERNS, type: 'pattern' },
        { id: 'specials', label: `Specials (${MONOLITHICS.length})`, items: MONOLITHICS, type: 'mono' },
    ];

    // Main category tabs
    let html = `<div style="display:flex; gap:2px; margin-bottom:4px;">
        ${tabs.map(t => `<button class="btn btn-sm${activeLibraryTab === t.id ? ' active' : ''}"
            onclick="activeLibraryTab='${t.id}'; renderFinishLibrary();"
            style="flex:1; font-size:10px; padding:4px 2px; ${activeLibraryTab === t.id ? 'background:var(--accent); color:#000; border-color:var(--accent);' : ''}"
        >${t.label}</button>`).join('')}
    </div>`;

    // Combo count
    html += `<div style="text-align:center; font-size:9px; color:var(--text-dim); margin-bottom:3px;">
        ${BASES.length} bases x ${PATTERNS.length} patterns + ${MONOLITHICS.length} specials = <strong style="color:var(--accent);">${(BASES.length * PATTERNS.length + MONOLITHICS.length).toLocaleString()} finishes</strong>
    </div>`;

    const activeTab = tabs.find(t => t.id === activeLibraryTab);
    if (!activeTab) { container.innerHTML = html; return; }

    // Group accordion
    const groupMap = GROUP_MAPS[activeLibraryTab] || {};
    const groupNames = Object.keys(groupMap);

    // === FAVORITES GROUP (always at top if any exist for this tab) ===
    const allTabIds = new Set(activeTab.items.map(it => it.id));
    const favItems = activeTab.items.filter(it => _favoriteFinishes.has(it.id));
    if (favItems.length > 0 && !_showFavoritesOnly) {
        html += `<div class="finish-group-accordion" style="margin-bottom:4px;">
                <div style="display:flex; align-items:center; gap:6px; padding:5px 8px; border-radius:4px; border-left:3px solid #ffaa00; background:rgba(255,170,0,0.06);">
                    <span style="font-size:14px; color:#ffaa00;">★</span>
                    <span style="font-size:10px; font-weight:700; color:#ffaa00; flex:1;">Favorites</span>
                    <span style="font-size:9px; color:var(--text-dim);">${favItems.length}</span>
                </div>
                <div style="padding:2px 0 4px 0;">`;
        favItems.forEach(item => { html += _renderFinishItem(item, activeTab.type); });
        html += `</div></div>`;
    }

    // If favorites-only mode, skip groups
    if (_showFavoritesOnly) {
        if (favItems.length === 0) {
            html += `<div style="text-align:center; padding:30px 10px; color:var(--text-dim); font-size:11px;">No favorites in this tab yet. Click the ☆ star on any finish to add it.</div>`;
        } else {
            favItems.forEach(item => { html += _renderFinishItem(item, activeTab.type); });
        }
        container.innerHTML = html;
        return;
    }

    if (groupNames.length > 0) {
        // Expand/Collapse All controls
        html += `<div style="display:flex; justify-content:flex-end; gap:6px; margin-bottom:4px; padding:0 2px;">
            <span onclick="expandAllLibraryGroups()" style="font-size:9px; color:var(--accent); cursor:pointer; text-decoration:underline;">Expand All</span>
            <span onclick="collapseAllLibraryGroups()" style="font-size:9px; color:var(--text-dim); cursor:pointer; text-decoration:underline;">Collapse All</span>
        </div>`;

        // Section dividers for specials
        const _effSet = new Set(["Effect & Visual", "Weather & Element", "Dark & Gothic", "Neon & Glow"]);
        let _prevWasEffect = false;
        let _addedColorLabel = false;

        groupNames.forEach(gn => {
            const isEffect = _effSet.has(gn);
            const isParadigm = gn.startsWith('PARADIGM');

            // Section divider labels for specials tab
            if (activeLibraryTab === 'specials' && !_addedColorLabel && !isEffect && !isParadigm) {
                html += `<div style="width:100%; font-size:8px; color:var(--accent-green); font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:3px 2px 1px; margin-top:2px;">Color-Changing</div>`;
                _addedColorLabel = true;
            }
            if (activeLibraryTab === 'specials' && isEffect && !_prevWasEffect) {
                html += `<div style="width:100%; font-size:8px; color:var(--accent-gold); font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:3px 2px 1px; margin-top:4px; border-top:1px solid var(--border);">Effect (keeps paint color)</div>`;
            }
            _prevWasEffect = isEffect;

            const isOpen = _expandedGroups.has(gn);
            const groupIds = new Set(groupMap[gn]);
            const groupItems = activeTab.items.filter(it => groupIds.has(it.id));
            const chevron = isOpen ? '▾' : '▸';

            // Accent color for PARADIGM groups
            const headerBorder = isParadigm ? 'border-left:3px solid var(--accent);' : isEffect ? 'border-left:3px solid var(--accent-gold);' : 'border-left:3px solid var(--accent-green);';
            const headerBg = isOpen ? 'background:var(--surface-hover);' : '';

            html += `<div class="finish-group-accordion" style="margin-bottom:2px;">
                <div onclick="toggleLibraryGroup('${gn.replace(/'/g, "\\'")}')"
                     style="display:flex; align-items:center; gap:6px; padding:5px 8px; cursor:pointer; border-radius:4px; ${headerBorder} ${headerBg} transition:background 0.15s;"
                     onmouseenter="this.style.background='var(--surface-hover)'" onmouseleave="this.style.background='${isOpen ? 'var(--surface-hover)' : ''}'">
                    <span style="font-size:11px; color:var(--accent); width:12px;">${chevron}</span>
                    <span style="font-size:10px; font-weight:600; color:${isParadigm ? 'var(--accent)' : 'var(--text)'}; flex:1;">${gn}</span>
                    <span style="font-size:9px; color:var(--text-dim);">${groupItems.length}</span>
                </div>`;

            if (isOpen) {
                html += `<div style="padding:2px 0 4px 0;">`;
                groupItems.forEach(item => {
                    html += _renderFinishItem(item, activeTab.type);
                });
                html += `</div>`;
            }
            html += `</div>`;
        });

        // Ungrouped items (items not in any group)
        const allGroupedIds = new Set();
        groupNames.forEach(gn => groupMap[gn].forEach(id => allGroupedIds.add(id)));
        const ungrouped = activeTab.items.filter(it => !allGroupedIds.has(it.id));
        if (ungrouped.length > 0) {
            const uIsOpen = _expandedGroups.has('__ungrouped__');
            const uChevron = uIsOpen ? '▾' : '▸';
            html += `<div class="finish-group-accordion" style="margin-bottom:2px; margin-top:4px;">
                <div onclick="toggleLibraryGroup('__ungrouped__')"
                     style="display:flex; align-items:center; gap:6px; padding:5px 8px; cursor:pointer; border-radius:4px; border-left:3px solid var(--border); transition:background 0.15s;"
                     onmouseenter="this.style.background='var(--surface-hover)'" onmouseleave="this.style.background=''">
                    <span style="font-size:11px; color:var(--text-dim); width:12px;">${uChevron}</span>
                    <span style="font-size:10px; font-weight:600; color:var(--text-dim); flex:1;">Other</span>
                    <span style="font-size:9px; color:var(--text-dim);">${ungrouped.length}</span>
                </div>`;
            if (uIsOpen) {
                html += `<div style="padding:2px 0 4px 0;">`;
                ungrouped.forEach(item => {
                    html += _renderFinishItem(item, activeTab.type);
                });
                html += `</div>`;
            }
            html += `</div>`;
        }
    } else {
        // No groups - render all items flat
        activeTab.items.forEach(item => {
            html += _renderFinishItem(item, activeTab.type);
        });
    }

    container.innerHTML = html;
    // No deferred canvas rendering needed - swatches are server-rendered <img> tags
}

function filterFinishes(query) {
    const q = query.toLowerCase().trim();
    const items = document.querySelectorAll('#finishLibrary .finish-item');
    let visibleCount = 0;
    items.forEach(item => {
        const name = item.getAttribute('data-name') || '';
        const desc = item.getAttribute('data-desc') || '';
        const matches = !q || name.includes(q) || desc.includes(q);
        item.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });
    // Show/hide "no results" message
    let noResults = document.getElementById('finishNoResults');
    if (visibleCount === 0 && q) {
        if (!noResults) {
            noResults = document.createElement('div');
            noResults.id = 'finishNoResults';
            noResults.style.cssText = 'text-align:center; padding:20px; color:var(--text-dim); font-size:11px;';
            document.getElementById('finishLibrary').appendChild(noResults);
        }
        noResults.textContent = `No finishes matching "${query}"`;
        noResults.style.display = '';
    } else if (noResults) {
        noResults.style.display = 'none';
    }
}

function toggleCategory(cat) {
    categoryCollapsed[cat] = !categoryCollapsed[cat];
    renderFinishLibrary();
}

// ===== SECTION TOGGLE =====
function toggleSection(id) {
    const body = document.getElementById(id + '-body');
    const toggle = document.getElementById(id + '-toggle');
    const header = toggle.closest('.section-header');
    if (body.classList.contains('collapsed')) {
        body.classList.remove('collapsed');
        header.classList.remove('collapsed');
    } else {
        body.classList.add('collapsed');
        header.classList.add('collapsed');
    }
}


// ===== PRESETS =====
function applyPreset(presetId) {
    if (!presetId || !PRESETS[presetId]) return;
    const preset = PRESETS[presetId];
    zones = preset.zones.map(z => ({
        name: z.name,
        color: z.color,
        base: z.base || null,
        pattern: z.pattern || 'none',
        finish: z.finish || null,
        intensity: z.intensity,
        customSpec: null, customPaint: null, customBright: null,
        hint: z.hint || '',
        colorMode: z.color === null ? 'none' :
            SPECIAL_COLORS.some(sc => sc.value === z.color) ? 'special' :
                QUICK_COLORS.some(qc => qc.value === z.color) ? 'quick' : 'text',
        pickerColor: '#3366ff',
        pickerTolerance: 40,
        colors: [],
        regionMask: null,
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        patternStack: [],
    }));
    selectedZoneIndex = 0;
    renderZones();
    showToast(`Loaded preset: ${preset.name} -- set colors using the eyedropper!`);
}

// ===== TOAST =====
function showToast(msg, isError) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast show' + (isError ? ' error' : '');
    setTimeout(() => toast.className = 'toast', 2500);
}

// ===== RENDER NOTIFICATION SYSTEM =====
const RenderNotify = {
    _originalTitle: document.title,
    _flashTimer: null,

    // Play a short success/error tone using Web Audio API (no external files needed)
    playSound(success) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            if (success) {
                // Two-tone success chime
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.frequency.setValueAtTime(1175, ctx.currentTime + 0.12);
                gain.gain.setValueAtTime(0.15, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.35);
            } else {
                // Low buzz for error
                osc.type = 'square';
                osc.frequency.setValueAtTime(220, ctx.currentTime);
                gain.gain.setValueAtTime(0.1, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.3);
            }
        } catch (e) { /* Audio not available */ }
    },

    // Flash the tab title to get attention when tabbed away
    flashTitle(msg) {
        if (this._flashTimer) clearInterval(this._flashTimer);
        let on = true;
        this._flashTimer = setInterval(() => {
            document.title = on ? msg : this._originalTitle;
            on = !on;
        }, 800);
        // Stop flashing when window gets focus
        const stop = () => {
            clearInterval(this._flashTimer);
            this._flashTimer = null;
            document.title = this._originalTitle;
            window.removeEventListener('focus', stop);
        };
        window.addEventListener('focus', stop);
        // Auto-stop after 30 seconds
        setTimeout(stop, 30000);
    },

    // Browser notification (only if page is not focused)
    browserNotify(title, body) {
        if (document.hasFocus()) return;
        if (Notification.permission === 'granted') {
            new Notification(title, { body, icon: '🎨' });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    },

    // Call this when render completes
    onRenderComplete(success, elapsed, zoneCount) {
        this.playSound(success);
        if (!document.hasFocus()) {
            if (success) {
                this.flashTitle(`✅ Render done! (${elapsed}s)`);
                this.browserNotify('Shokker Render Complete', `${zoneCount} zones rendered in ${elapsed}s`);
            } else {
                this.flashTitle('❌ Render failed!');
                this.browserNotify('Shokker Render Failed', 'Check the Paint Booth for details');
            }
        }
    }
};

// Request notification permission early (on user interaction)
document.addEventListener('click', () => {
    if (window.Notification && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}, { once: true });

// ===== RENDER ELAPSED TIMER =====
let renderStartTime = null;
let renderElapsedTimer = null;
function startRenderTimer() {
    renderStartTime = Date.now();
    const btn = document.getElementById('btnRender');
    renderElapsedTimer = setInterval(() => {
        const elapsed = ((Date.now() - renderStartTime) / 1000).toFixed(0);
        btn.textContent = `RENDERING... ${elapsed}s`;
    }, 500);
}
function stopRenderTimer() {
    if (renderElapsedTimer) { clearInterval(renderElapsedTimer); renderElapsedTimer = null; }
    renderStartTime = null;
}

// ===== OUTPUT PATH AUTO-FILL =====
const BASE_DRIVER_PATH = "";  // Set via config or leave blank - output path is user-defined

function updateOutputPath() {
    const iracingId = document.getElementById('iracingId').value.trim();

    // Update filename preview if element exists (moved to header, may not have preview span)
    const preview = document.getElementById('outputFilenamePreview');
    if (preview) preview.textContent = `car_num_${iracingId}.tga + car_spec_${iracingId}.tga`;
}

// ===== CONFIG SAVE / LOAD =====
function getConfig() {
    return {
        version: "3.0",
        driverName: document.getElementById('driverName').value,
        carName: document.getElementById('carName').value,
        iracingId: document.getElementById('iracingId').value,
        paintFile: document.getElementById('paintFile').value,
        outputDir: document.getElementById('outputDir').value,
        helmetFile: document.getElementById('helmetFile')?.value || '',
        suitFile: document.getElementById('suitFile')?.value || '',
        wearLevel: parseInt(document.getElementById('wearSlider')?.value || '0', 10),
        exportZip: document.getElementById('exportZipCheckbox')?.checked || false,
        dualSpec: document.getElementById('dualSpecCheckbox')?.checked || false,
        nightBoost: parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7'),
        zones: zones.map(z => ({
            name: z.name,
            color: z.color,
            base: z.base,
            pattern: z.pattern,
            finish: z.finish,
            intensity: z.intensity,
            customSpec: z.customSpec != null ? z.customSpec : undefined,
            customPaint: z.customPaint != null ? z.customPaint : undefined,
            customBright: z.customBright != null ? z.customBright : undefined,
            colorMode: z.colorMode,
            pickerColor: z.pickerColor,
            pickerTolerance: z.pickerTolerance,
            colors: z.colors || [],
            scale: z.scale || 1.0,
            rotation: z.rotation || 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternStack: z.patternStack || [],
            wear: z.wear || 0,
            muted: z.muted || false,
            linkGroup: z.linkGroup || null,
        })),
        // Decals disabled - future feature
        importedSpecMapPath: importedSpecMapPath || null,
        activeSpecChannel: activeSpecChannel || 'all',
    };
}

function loadConfigFromObj(cfg) {
    if (cfg.driverName !== undefined) document.getElementById('driverName').value = cfg.driverName;
    if (cfg.carName !== undefined) document.getElementById('carName').value = cfg.carName;
    if (cfg.iracingId !== undefined) document.getElementById('iracingId').value = cfg.iracingId;
    if (cfg.paintFile !== undefined) document.getElementById('paintFile').value = cfg.paintFile;
    if (cfg.outputDir !== undefined) document.getElementById('outputDir').value = cfg.outputDir;
    // Extras
    if (cfg.helmetFile !== undefined && document.getElementById('helmetFile')) document.getElementById('helmetFile').value = cfg.helmetFile;
    if (cfg.suitFile !== undefined && document.getElementById('suitFile')) document.getElementById('suitFile').value = cfg.suitFile;
    if (cfg.wearLevel !== undefined && document.getElementById('wearSlider')) {
        document.getElementById('wearSlider').value = cfg.wearLevel;
        updateWearDisplay(cfg.wearLevel);
    }
    if (cfg.exportZip !== undefined && document.getElementById('exportZipCheckbox')) document.getElementById('exportZipCheckbox').checked = cfg.exportZip;
    if (cfg.dualSpec !== undefined && document.getElementById('dualSpecCheckbox')) { document.getElementById('dualSpecCheckbox').checked = cfg.dualSpec; toggleNightBoostSlider(); }
    if (cfg.nightBoost !== undefined && document.getElementById('nightBoostSlider')) { document.getElementById('nightBoostSlider').value = cfg.nightBoost; document.getElementById('nightBoostVal').textContent = parseFloat(cfg.nightBoost).toFixed(2); }
    updateOutputPath();
    if (cfg.zones) {
        zones = cfg.zones.map(z => ({
            name: z.name || 'Zone',
            color: z.color,
            base: z.base || null,
            pattern: z.pattern || 'none',
            finish: z.finish || null,
            intensity: z.intensity || '100',
            customSpec: z.customSpec != null ? z.customSpec : null,
            customPaint: z.customPaint != null ? z.customPaint : null,
            customBright: z.customBright != null ? z.customBright : null,
            colorMode: z.colorMode || 'none',
            pickerColor: z.pickerColor || '#3366ff',
            pickerTolerance: z.pickerTolerance || 40,
            colors: z.colors || [],
            regionMask: null,
            lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
            scale: z.scale || 1.0,
            rotation: z.rotation || 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternStack: z.patternStack || [],
            wear: z.wear || 0,
            muted: z.muted || false,
            linkGroup: z.linkGroup || null,
        }));
        selectedZoneIndex = 0;
        // Restore nextLinkGroupId to avoid collisions
        const maxLinkId = zones.reduce((max, z) => {
            if (z.linkGroup) {
                const n = parseInt(z.linkGroup.replace('link_', '')) || 0;
                return Math.max(max, n);
            }
            return max;
        }, 0);
        if (maxLinkId >= nextLinkGroupId) nextLinkGroupId = maxLinkId + 1;
        renderZones();
    }
    // Decal restore disabled - future feature
    // Restore imported spec map (merge mode)
    if (cfg.importedSpecMapPath) {
        importedSpecMapPath = cfg.importedSpecMapPath;
        const status = document.getElementById('importSpecMapStatus');
        if (status) {
            const fname = cfg.importedSpecMapPath.split('/').pop().split('\\').pop();
            status.innerHTML = `<span style="color: var(--accent-green);">&#10003;</span> <strong>${fname}</strong> (loaded from config)`;
        }
        const btn = document.getElementById('btnClearSpecMap');
        if (btn) btn.disabled = false;
    }
    // Restore spec channel visualizer state
    if (cfg.activeSpecChannel && cfg.activeSpecChannel !== 'all') {
        setSpecChannel(cfg.activeSpecChannel);
    }
}

function saveConfig() {
    const cfg = getConfig();
    const json = JSON.stringify(cfg, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_paintbooth_config_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast('Config saved!');
}

// ===== SHAREABLE PAINT PRESETS (.shokker files) =====
function exportPreset() {
    const driverName = document.getElementById('driverName').value.trim() || 'Unknown';
    const carName = document.getElementById('carName').value.trim() || 'Unknown Car';
    const presetName = prompt('Preset name:', `${driverName} - ${carName}`);
    if (!presetName) return;

    const preset = {
        _shokker_preset: true,
        version: "1.0",
        name: presetName,
        author: driverName,
        car: carName,
        created: new Date().toISOString(),
        description: buildPresetDescription(),
        zones: zones.map(z => ({
            name: z.name,
            base: z.base,
            pattern: z.pattern,
            finish: z.finish,
            intensity: z.intensity,
            customSpec: z.customSpec != null ? z.customSpec : undefined,
            customPaint: z.customPaint != null ? z.customPaint : undefined,
            customBright: z.customBright != null ? z.customBright : undefined,
            color: z.color,
            colorMode: z.colorMode,
            pickerColor: z.pickerColor,
            pickerTolerance: z.pickerTolerance,
            colors: z.colors || [],
            scale: z.scale || 1.0,
            rotation: z.rotation || 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternStack: z.patternStack || [],
            wear: z.wear || 0,
            muted: z.muted || false,
            // Region masks are intentionally excluded - they're car-specific
        })),
        settings: {
            wearLevel: parseInt(document.getElementById('wearSlider')?.value || '0', 10),
            dualSpec: document.getElementById('dualSpecCheckbox')?.checked || false,
            nightBoost: parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7'),
        },
        finishCount: zones.filter(z => z.base || z.finish).length,
        colorCount: zones.filter(z => z.color !== null || z.colorMode === 'multi').length,
    };

    const json = JSON.stringify(preset, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const safeName = presetName.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_');
    a.download = `${safeName}.shokker`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast(`Preset exported: ${presetName}`);
}

function buildPresetDescription() {
    return zones.map(z => {
        let finish = '';
        if (z.finish) {
            const mono = MONOLITHICS.find(m => m.id === z.finish);
            finish = mono ? mono.name : z.finish;
        } else if (z.base) {
            const b = BASES.find(b => b.id === z.base);
            const p = z.pattern && z.pattern !== 'none' ? PATTERNS.find(p => p.id === z.pattern) : null;
            finish = b ? b.name : z.base;
            if (p) finish += ' + ' + p.name;
        }
        return `${z.name}: ${finish || 'No finish'}`;
    }).join(' | ');
}

function importPreset() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.shokker,.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                if (data._shokker_preset) {
                    applyPreset(data);
                } else if (data.zones) {
                    // Fallback: it's a regular config file
                    loadConfigFromObj(data);
                    showToast('Loaded as config (not a preset file)');
                } else {
                    throw new Error('Not a valid .shokker preset');
                }
            } catch (err) {
                showToast('Invalid preset file: ' + err.message, true);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

function applyPreset(preset) {
    // Show preset info before applying
    const info = `"${preset.name}"${preset.author ? ' by ' + preset.author : ''}\n${preset.zones.length} zones | ${preset.finishCount || '?'} finishes\n\nApply this preset? (Your current zones will be replaced)`;
    if (!confirm(info)) return;

    // Apply zones
    zones = preset.zones.map(z => ({
        name: z.name || 'Zone',
        color: z.color,
        base: z.base || null,
        pattern: z.pattern || 'none',
        finish: z.finish || null,
        intensity: z.intensity || '100',
        customSpec: z.customSpec != null ? z.customSpec : null,
        customPaint: z.customPaint != null ? z.customPaint : null,
        customBright: z.customBright != null ? z.customBright : null,
        colorMode: z.colorMode || 'none',
        pickerColor: z.pickerColor || '#3366ff',
        pickerTolerance: z.pickerTolerance || 40,
        colors: z.colors || [],
        regionMask: null, // Regions are car-specific, not imported
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        scale: z.scale || 1.0,
        patternOpacity: z.patternOpacity ?? 100,
        patternStack: z.patternStack || [],
        wear: z.wear || 0,
        muted: z.muted || false,
    }));
    selectedZoneIndex = 0;

    // Apply settings if present
    if (preset.settings) {
        if (preset.settings.wearLevel !== undefined && document.getElementById('wearSlider')) {
            document.getElementById('wearSlider').value = preset.settings.wearLevel;
            updateWearDisplay(preset.settings.wearLevel);
        }
        if (preset.settings.dualSpec !== undefined && document.getElementById('dualSpecCheckbox')) {
            document.getElementById('dualSpecCheckbox').checked = preset.settings.dualSpec;
            toggleNightBoostSlider();
        }
        if (preset.settings.nightBoost !== undefined && document.getElementById('nightBoostSlider')) {
            document.getElementById('nightBoostSlider').value = preset.settings.nightBoost;
            document.getElementById('nightBoostVal').textContent = parseFloat(preset.settings.nightBoost).toFixed(2);
        }
    }

    renderZones();
    triggerPreviewRender();
    autoSave();
    showToast(`Preset loaded: "${preset.name}" - ${preset.zones.length} zones`);
}

function loadConfig() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const cfg = JSON.parse(ev.target.result);
                loadConfigFromObj(cfg);
                showToast('Config loaded!');
            } catch (err) {
                showToast('Invalid config file', true);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

// ===== AUTO-SAVE / AUTO-RESTORE =====
const AUTOSAVE_KEY = 'shokker_autosave';
let autosaveTimer = null;

function autoSave() {
    // Debounce: wait 500ms after last change before saving
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
        try {
            const cfg = getConfig();
            cfg._autosave_time = Date.now();
            localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(cfg));
            const badge = document.getElementById('autosaveBadge');
            if (badge) {
                badge.textContent = 'Auto-saved';
                badge.style.opacity = '1';
                setTimeout(() => { badge.style.opacity = '0.4'; }, 1500);
            }
        } catch (e) {
            // localStorage full or unavailable - silently ignore
        }
    }, 500);
}

function autoRestore() {
    try {
        const raw = localStorage.getItem(AUTOSAVE_KEY);
        if (!raw) return false;
        const cfg = JSON.parse(raw);
        if (!cfg || !cfg.zones || cfg.zones.length === 0) return false;
        loadConfigFromObj(cfg);
        const age = cfg._autosave_time ? Math.round((Date.now() - cfg._autosave_time) / 1000) : 0;
        let ageStr;
        if (age < 60) ageStr = `${age}s ago`;
        else if (age < 3600) ageStr = `${Math.round(age / 60)}m ago`;
        else ageStr = `${Math.round(age / 3600)}h ago`;
        showToast(`Session restored (saved ${ageStr}) - ${cfg.zones.length} zones, ${cfg.driverName || 'no driver'}`);
        // Validate restored paint path after a short delay (server needs to be up)
        setTimeout(() => { if (typeof validatePaintPath === 'function') validatePaintPath(); }, 800);
        return true;
    } catch (e) {
        return false;
    }
}

function exportJSON() {
    const zoneData = zones.map(z => {
        const entry = { name: z.name, finish: z.finish, intensity: z.intensity };
        if (z.customSpec != null) entry.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
        if (z.color !== null) entry.color = z.color;
        return entry;
    });
    const json = JSON.stringify(zoneData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_zones_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast('Zone JSON exported!');
}

// ===== MODAL =====
function openModal() {
    document.getElementById('scriptModal').classList.add('active');
}

function closeModal() {
    document.getElementById('scriptModal').classList.remove('active');
}

function copyScript() {
    const text = document.getElementById('scriptOutput').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const fb = document.getElementById('copyFeedback');
        fb.classList.add('show');
        setTimeout(() => fb.classList.remove('show'), 2000);
    });
}

function saveScriptFile() {
    const text = document.getElementById('scriptOutput').textContent;
    if (!text) { showToast('No script generated yet!', true); return; }

    let filename = document.getElementById('scriptFilename').value.trim();
    if (!filename) filename = 'shokker_multizone.py';
    if (!filename.endsWith('.py')) filename += '.py';

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Saved ${filename}`);
}

function saveBatLauncher() {
    // Generate a .bat file that launches the .py script
    // Uses RUN_ prefix so it won't get confused with browser-renamed .py files
    let pyFilename = document.getElementById('scriptFilename').value.trim();
    if (!pyFilename) pyFilename = 'shokker_multizone.py';
    if (!pyFilename.endsWith('.py')) pyFilename += '.py';

    const driverName = document.getElementById('driverName')?.value.trim() || 'Paint';
    // Use RUN_ prefix so the bat has a distinct name from the .py
    const baseName = pyFilename.replace(/\.py$/, '');
    const batName = `RUN_${baseName}.bat`;

    // ROBUST bat launcher:
    // 1. Auto-unblocks all .py files (fixes Windows Zone.Identifier blocking)
    // 2. Tries exact filename first
    // 3. Falls back to PowerShell to find the NEWEST .py file matching the base name
    //    (handles browser renaming: script.py -> script (1).py, script (2).py, etc.)
    // 4. Last resort: runs the newest .py file in the folder
    const batContent = `@echo off\r
REM Auto-unblock .py files in this folder (browser downloads get Zone.Identifier)\r
powershell -ExecutionPolicy Bypass -Command "Get-ChildItem '%~dp0*.py' | Unblock-File" >nul 2>&1\r
\r
echo ============================================================\r
echo   SHOKKER PAINT BOOTH - ${driverName} Build\r
echo ============================================================\r
echo.\r
\r
REM Try the exact script name first\r
if exist "%~dp0${pyFilename}" (\r
    echo   Running: ${pyFilename}\r
    python "%~dp0${pyFilename}"\r
    goto :done\r
)\r
\r
REM Browser renamed the file - use PowerShell to find newest matching .py\r
echo   ${pyFilename} not found, searching for latest version...\r
for /f "usebackq delims=" %%f in (\`powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Filter '${baseName}*.py' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"\`) do (\r
    echo   Found: %%f\r
    python "%~dp0%%f"\r
    goto :done\r
)\r
\r
REM Last resort: find ANY .py file (newest first, skip RUN_ bat scripts)\r
for /f "usebackq delims=" %%f in (\`powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Filter '*.py' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"\`) do (\r
    echo   Using newest script found: %%f\r
    python "%~dp0%%f"\r
    goto :done\r
)\r
\r
echo   ERROR: No .py scripts found in this folder!\r
echo   Make sure the .py file is in the same folder as this .bat file.\r
echo   Current folder: %~dp0\r
\r
:done\r
echo.\r
echo ============================================================\r
echo   DONE! Check the output files above.\r
echo ============================================================\r
echo.\r
pause\r\n`;

    const blob = new Blob([batContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = batName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Saved ${batName} - double-click to run!`);
}

function getAutoScriptName() {
    const driver = document.getElementById('driverName')?.value.trim() || '';
    const car = document.getElementById('carName')?.value.trim() || '';
    // Use underscores instead of spaces to prevent Windows batch issues
    // and reduce browser rename collisions (script.py -> script (1).py)
    if (driver && car) {
        return `${driver}_${car}.py`.replace(/[<>:"/\\|?*\s]+/g, '_');
    }
    if (driver) return `${driver}.py`.replace(/[<>:"/\\|?*\s]+/g, '_');
    return 'shokker_multizone.py';
}

// ===== ADDITIONAL KEYBOARD SHORTCUTS (tools & view) =====
document.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && canvasMode === 'lasso' && lassoActive && lassoPoints.length > 0) {
        e.preventDefault();
        lassoPoints.pop();
        drawLassoPreview();
        updateDrawZoneIndicator(); // Update point count in hint
        showToast(`Removed last vertex (${lassoPoints.length} points remaining)`);
        return;
    }
    if (e.key === 'Escape') {
        // Cancel active lasso first
        if (canvasMode === 'lasso' && lassoActive && lassoPoints.length > 0) {
            lassoActive = false; lassoPoints = []; hideLassoPreview();
            showToast('Lasso cancelled');
            return;
        }
        if (typeof compareMode !== 'undefined' && compareMode) { toggleCompareMode(); return; }
        if (document.getElementById('finishCompareOverlay')?.classList.contains('active')) { closeFinishCompare(); return; }
        if (document.getElementById('finishBrowserOverlay')?.classList.contains('active')) { closeFinishBrowser(); return; }
        if (document.getElementById('presetGalleryOverlay')?.classList.contains('active')) { closePresetGallery(); return; }
        closeModal();
    }
});

// ===== REGION MASK ENCODING =====
function encodeRegionMaskRLE(mask, width, height) {
    // Run-length encode a binary mask: [[value, count], [value, count], ...]
    // For sparse masks (few drawn areas on big canvas), this compresses massively
    if (!mask) return null;
    const runs = [];
    let currentVal = mask[0];
    let count = 1;
    for (let i = 1; i < mask.length; i++) {
        if (mask[i] === currentVal) {
            count++;
        } else {
            runs.push([currentVal, count]);
            currentVal = mask[i];
            count = 1;
        }
    }
    runs.push([currentVal, count]);
    return { width, height, runs };
}

function hasAnyRegionMasks() {
    return zones.some(z => z.regionMask && z.regionMask.some(v => v > 0));
}

// ===== SCRIPT GENERATION =====
function formatColorForPython(color, zone) {
    // Multi-color zone: output a list of selectors
    if (zone && zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
        const selectors = zone.colors.map(c =>
            `{"color_rgb": [${c.color_rgb[0]}, ${c.color_rgb[1]}, ${c.color_rgb[2]}], "tolerance": ${c.tolerance || 40}}`
        );
        return `[${selectors.join(', ')}]`;
    }
    // If zone has a spatial region but no color, use "everything" as fallback
    // (the region mask will override color detection in the engine)
    if (color === null) {
        if (zone && zone.regionMask && zone.regionMask.some(v => v > 0)) return '"everything"';
        return '"everything"';
    }
    if (typeof color === 'string') return `"${color}"`;
    if (typeof color === 'object' && !Array.isArray(color) && color.color_rgb) {
        return `{"color_rgb": [${color.color_rgb[0]}, ${color.color_rgb[1]}, ${color.color_rgb[2]}], "tolerance": ${color.tolerance || 40}}`;
    }
    if (Array.isArray(color)) {
        // Already an array of selectors
        const selectors = color.map(c =>
            `{"color_rgb": [${c.color_rgb[0]}, ${c.color_rgb[1]}, ${c.color_rgb[2]}], "tolerance": ${c.tolerance || 40}}`
        );
        return `[${selectors.join(', ')}]`;
    }
    return '"everything"';
}

function generateScript() {
    // Validate
    const paintFile = document.getElementById('paintFile').value.trim();
    const outputDir = document.getElementById('outputDir').value.trim();
    const iracingId = document.getElementById('iracingId').value.trim();

    if (!paintFile) { showToast('Set the Source Paint path in the header bar!', true); return; }
    if (!outputDir) { showToast('Set the iRacing Paint Folder path in Car Info!', true); return; }

    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    if (validZones.length === 0) { showToast('At least one zone needs a base/finish AND a color or drawn region!', true); return; }

    // Build zones python array, including region mask references
    const canvas = document.getElementById('paintCanvas');
    const canvasW = canvas?.width || 2048;
    const canvasH = canvas?.height || 2048;

    // Encode any region masks
    const regionMasks = {};
    validZones.forEach((z, i) => {
        if (z.regionMask && z.regionMask.some(v => v > 0)) {
            const rle = encodeRegionMaskRLE(z.regionMask, canvasW, canvasH);
            regionMasks[z.name] = rle;
        }
    });

    const zonesStr = validZones.map(z => {
        const colorPy = formatColorForPython(z.color, z);
        const hasRegion = regionMasks[z.name] ? 'True' : 'False';
        let finishPart;
        if (z.base) {
            finishPart = `"base": "${z.base}", "pattern": "${z.pattern || 'none'}"`;
            if (z.scale && z.scale !== 1.0) finishPart += `, "scale": ${z.scale}`;
            // Pattern stack
            if (z.patternStack && z.patternStack.length > 0) {
                const stack = z.patternStack.filter(l => l.id && l.id !== 'none');
                if (stack.length > 0) {
                    const stackPy = stack.map(l => `{"id": "${l.id}", "opacity": ${((l.opacity ?? 100) / 100).toFixed(2)}, "scale": ${(l.scale || 1.0).toFixed(2)}}`).join(', ');
                    finishPart += `, "pattern_stack": [${stackPy}]`;
                }
            }
        } else {
            finishPart = `"finish": "${z.finish}"`;
        }
        const customInt = z.customSpec != null ? `, "custom_intensity": {"spec": ${z.customSpec}, "paint": ${z.customPaint}, "bright": ${z.customBright}}` : '';
        return `    {"name": "${z.name.replace(/"/g, '\\"')}", "color": ${colorPy}, ${finishPart}, "intensity": "${z.intensity}"${customInt}, "has_region": ${hasRegion}}`;
    }).join(',\n');

    // SAFETY: Always point PAINT_FILE at the .tga, never a .png/.jpg preview image
    let paintFileSafe = paintFile;
    const previewExts = /\.(png|jpg|jpeg|bmp)$/i;
    if (previewExts.test(paintFileSafe)) {
        const carMatch = paintFileSafe.match(/^(.*[/\\])(car_num_\d+)[\w-]*\.\w+$/i);
        if (carMatch) {
            paintFileSafe = carMatch[1] + carMatch[2] + '.tga';
        } else {
            paintFileSafe = paintFileSafe.replace(previewExts, '.tga');
        }
        showToast(`Script targets TGA: ${paintFileSafe.split(/[/\\]/).pop()}`, false);
    }
    const paintFilePy = paintFileSafe.replace(/\\/g, '/');
    const outputDirPy = outputDir.replace(/\\/g, '/');

    // Gather extras for script generation
    const scriptExtras = {};
    const helmetFile = document.getElementById('helmetFile')?.value.trim();
    const suitFile = document.getElementById('suitFile')?.value.trim();
    const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
    const exportZip = document.getElementById('exportZipCheckbox')?.checked || false;
    if (helmetFile) scriptExtras.helmetFile = helmetFile.replace(/\\/g, '/');
    if (suitFile) scriptExtras.suitFile = suitFile.replace(/\\/g, '/');
    if (wearLevel > 0) scriptExtras.wearLevel = wearLevel;
    if (exportZip) scriptExtras.exportZip = true;
    const dualSpec = document.getElementById('dualSpecCheckbox')?.checked || false;
    if (dualSpec) {
        scriptExtras.dualSpec = true;
        scriptExtras.nightBoost = parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7');
    }

    const script = generateFullPythonScript(paintFilePy, outputDirPy, iracingId, zonesStr, regionMasks, scriptExtras);

    document.getElementById('scriptOutput').textContent = script;
    document.getElementById('scriptFilename').value = getAutoScriptName();
    openModal();
}

function generateFullPythonScript(paintFile, outputDir, iracingId, zonesStr, regionMasks, extras) {
    // Generate a clean build script that imports from shokker_engine_v2.py
    // The engine file contains ALL proven, tested code

    // Build region mask data block if any regions were drawn
    let regionDataBlock = '';
    const maskNames = Object.keys(regionMasks || {});
    if (maskNames.length > 0) {
        regionDataBlock = `
# ==============================================================================
# SPATIAL REGION MASKS (drawn in Paint Booth)
# RLE encoded: [[value, count], ...] - decode with decode_region_mask()
# ==============================================================================
REGION_MASKS = {
`;
        for (const name of maskNames) {
            const rle = regionMasks[name];
            // Compact the runs array for readability
            const runsStr = rle.runs.map(r => `[${r[0]},${r[1]}]`).join(',');
            regionDataBlock += `    "${name.replace(/"/g, '\\"')}": {"width": ${rle.width}, "height": ${rle.height}, "runs": [${runsStr}]},\n`;
        }
        regionDataBlock += `}

def decode_region_mask(rle_data, target_h, target_w):
    """Decode RLE region mask and resize to target paint dimensions."""
    import numpy as np
    from PIL import Image
    w, h = rle_data["width"], rle_data["height"]
    mask = np.zeros(w * h, dtype=np.uint8)
    pos = 0
    for val, count in rle_data["runs"]:
        mask[pos:pos+count] = val
        pos += count
    mask = mask.reshape((h, w))
    # Resize to match paint resolution if different
    if h != target_h or w != target_w:
        mask_img = Image.fromarray(mask * 255)
        mask_img = mask_img.resize((target_w, target_h), Image.NEAREST)
        mask = (np.array(mask_img) > 127).astype(np.float32)
    else:
        mask = mask.astype(np.float32)
    return mask
`;
    }

    return `"""
SHOKKER PAINT BOOTH - Base + Pattern Compositing Build Script
Generated: ${new Date().toLocaleString()}

HOW TO RUN:
  1. Double-click the .bat file that came with this script
  2. Or run: python "your_script_name.py"
  3. Or paste this into Claude Code and say "run this"

REQUIRES: numpy, Pillow (pip install numpy Pillow)
NOTE: Do NOT add a shebang line - it breaks Windows py.exe launcher
"""
import sys
import os

# Add the ShokkerEngine folder to Python path so we can import the engine
ENGINE_PATHS = [
    os.path.dirname(os.path.abspath(__file__)),
    r"E:/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/ShokkerEngine",
]
for p in ENGINE_PATHS:
    if p not in sys.path:
        sys.path.insert(0, p)

# ==============================================================================
# CONFIG
# ==============================================================================
PAINT_FILE = r"${paintFile}"
OUTPUT_DIR = r"${outputDir}"
IRACING_ID = "${iracingId}"
SEED = 51
${extras?.helmetFile ? `HELMET_PAINT = r"${extras.helmetFile}"` : '# HELMET_PAINT = None  # Set path to helmet paint TGA for matching spec'}
${extras?.suitFile ? `SUIT_PAINT = r"${extras.suitFile}"` : '# SUIT_PAINT = None  # Set path to suit paint TGA for matching spec'}
WEAR_LEVEL = ${extras?.wearLevel || 0}  # 0=factory new, 100=destroyed
EXPORT_ZIP = ${extras?.exportZip ? 'True' : 'False'}
DUAL_SPEC = ${extras?.dualSpec ? 'True' : 'False'}  # Generate day + night spec maps
NIGHT_BOOST = ${extras?.nightBoost || 0.7}  # 0.0-1.0 night enhancement strength

# ==============================================================================
# ZONES - Color-based zone definitions
# First zone = highest priority. Use "remaining" for catch-all.
# Color can be: "blue", "dark", "gold", "red", "white", "remaining", etc.
# Or a dict: {"color_rgb": [R,G,B], "tolerance": 40}
# Or a LIST of dicts for multi-color zones (all get same finish):
#   [{"color_rgb": [255,170,0], "tolerance": 40}, {"color_rgb": [51,102,255], "tolerance": 40}]
# ==============================================================================
ZONES = [
${zonesStr}
]
${regionDataBlock}
# ==============================================================================
# IMPORT ENGINE & RUN
# ==============================================================================
try:
    from shokker_engine_v2 import build_multi_zone, full_render_pipeline
    print("  Engine loaded from shokker_engine_v2.py")
except ImportError:
    print("  ERROR: Could not find shokker_engine_v2.py!")
    print("  Make sure the file is in one of these locations:")
    for p in ENGINE_PATHS:
        print(f"    - {p}")
    print("\\n  You can get it from: E:/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/ShokkerEngine/")
    sys.exit(1)

if __name__ == '__main__':
    try:
        # Inject spatial region masks into zones if any were drawn
        region_masks = globals().get('REGION_MASKS', {})
        if region_masks:
            from PIL import Image
            import numpy as np
            paint_img = Image.open(PAINT_FILE)
            paint_h, paint_w = paint_img.size[1], paint_img.size[0]
            paint_img.close()
            for zone in ZONES:
                name = zone.get("name", "")
                if name in region_masks:
                    mask = decode_region_mask(region_masks[name], paint_h, paint_w)
                    zone["region_mask"] = mask
                    print(f"  Loaded spatial mask for: {name} ({int(mask.sum())} pixels)")

        # Resolve optional helmet/suit paths
        helmet_file = globals().get('HELMET_PAINT', None)
        if isinstance(helmet_file, str) and helmet_file.startswith('#'):
            helmet_file = None
        suit_file = globals().get('SUIT_PAINT', None)
        if isinstance(suit_file, str) and suit_file.startswith('#'):
            suit_file = None

        # Use full pipeline if extras are configured, otherwise basic build
        if helmet_file or suit_file or WEAR_LEVEL > 0 or EXPORT_ZIP or DUAL_SPEC:
            results = full_render_pipeline(
                car_paint_file=PAINT_FILE,
                output_dir=OUTPUT_DIR,
                zones=ZONES,
                iracing_id=IRACING_ID,
                seed=SEED,
                helmet_paint_file=helmet_file,
                suit_paint_file=suit_file,
                wear_level=WEAR_LEVEL,
                export_zip=EXPORT_ZIP,
                dual_spec=DUAL_SPEC,
                night_boost=NIGHT_BOOST,
            )
            print(f"  Full pipeline complete!")
            if helmet_file:
                print(f"  Helmet spec generated")
            if suit_file:
                print(f"  Suit spec generated")
            if WEAR_LEVEL > 0:
                print(f"  Wear applied: {WEAR_LEVEL}%")
            if EXPORT_ZIP and "export_zip" in results:
                print(f"  ZIP exported: {results['export_zip']}")
        else:
            build_multi_zone(PAINT_FILE, OUTPUT_DIR, ZONES, IRACING_ID, SEED)
    except Exception as e:
        print(f"\\n  ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    input("  Press Enter to close this window...")
`;
}

// ===== SOURCE PAINT FILE BROWSER =====
// ===== PAINT PATH VALIDATION =====
let _validateTimer = null;
function debouncedValidatePaintPath() {
    clearTimeout(_validateTimer);
    _validateTimer = setTimeout(validatePaintPath, 600);
}

async function validatePaintPath() {
    const input = document.getElementById('paintFile');
    const status = document.getElementById('paintPathStatus');
    const hint = document.getElementById('paintPathHint'); // may not exist in compact header layout
    const path = input.value.trim();

    if (!path) {
        input.classList.remove('path-valid', 'path-invalid');
        status.textContent = '';
        status.className = 'header-path-status';
        if (hint) hint.textContent = 'Paste the FULL Windows path to the paint TGA the engine should read';
        return;
    }

    if (!ShokkerAPI.online) {
        status.textContent = '(server offline)';
        status.className = 'path-status checking';
        return;
    }

    status.textContent = 'checking...';
    status.className = 'path-status checking';

    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/check-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path }),
        });
        const data = await res.json();

        if (data.is_file) {
            input.classList.add('path-valid');
            input.classList.remove('path-invalid');
            status.textContent = `\u2713 ${data.size_human}`;
            status.className = 'header-path-status valid';
            if (hint) { hint.textContent = `File found! (${data.size_human})`; hint.style.color = 'var(--accent-green)'; }
            addRecentPath(path);
        } else if (data.exists) {
            input.classList.remove('path-valid');
            input.classList.add('path-invalid');
            status.textContent = '\u2717 directory';
            status.className = 'header-path-status invalid';
            if (hint) { hint.textContent = 'That path is a directory, not a file.'; hint.style.color = '#ff4444'; }
        } else {
            input.classList.remove('path-valid');
            input.classList.add('path-invalid');
            status.textContent = '\u2717 not found';
            status.className = 'header-path-status invalid';
            if (hint) { hint.textContent = 'File not found!'; hint.style.color = '#ff4444'; }
        }
    } catch (e) {
        status.textContent = '(error)';
        status.className = 'header-path-status';
    }
}

function browsePaintFile(input) {
    const file = input.files[0];
    if (!file) return;

    // For browser security, we can't get the real path, but we CAN show the filename
    // and auto-load it as the paint preview too
    let fileName = file.name;

    // AUTO-FIX: If user uploaded a PNG/JPG (because browser can't display TGA),
    // convert the path to point to the actual .tga file for the engine.
    // The preview image can still be PNG - only the PAINT_FILE path matters.
    const iracingId = document.getElementById('iracingId').value.trim();
    let tgaFileName = fileName;
    const imgExts = /\.(png|jpg|jpeg|bmp)$/i;
    if (imgExts.test(fileName)) {
        // Check if this looks like a car_num file (with any suffix before extension)
        const carNumMatch = fileName.match(/^(car_num_\d+)[\w-]*\.\w+$/i);
        if (carNumMatch) {
            // Point to the actual TGA: car_num_XXXXX.tga
            tgaFileName = carNumMatch[1] + '.tga';
            showToast(`Preview: ${fileName} | Script will use: ${tgaFileName}`, false);
        } else {
            // Generic image file - try swapping extension to .tga
            tgaFileName = fileName.replace(imgExts, '.tga');
            showToast(`Note: Script will target ${tgaFileName} (TGA). Preview uses ${fileName}`, false);
        }
    }

    // Build a likely path based on driver name - BUT only if paintFile is empty
    // If user already has a path set, don't overwrite it - just update the filename part
    const currentPath = document.getElementById('paintFile').value.trim();
    const driverName = document.getElementById('driverName').value.trim();

    if (currentPath) {
        // User already has a path - replace just the filename, keep the directory
        const dir = currentPath.replace(/[/\\][^/\\]+$/, '');
        const newPath = dir + '/' + tgaFileName;
        document.getElementById('paintFile').value = newPath;
        showToast(`Updated filename in existing path: ${tgaFileName}`, false);
    } else if (driverName) {
        const guessedPath = BASE_DRIVER_PATH + "/" + driverName + "/" + tgaFileName;
        document.getElementById('paintFile').value = guessedPath;
    } else {
        // Just show the filename - user can adjust the full path
        document.getElementById('paintFile').value = tgaFileName;
        showToast('Paste the FULL path to the paint TGA - browser can\'t detect it automatically', true);
    }

    // Validate the path against the server
    validatePaintPath();

    // Load the file as paint preview
    if (fileName.toLowerCase().endsWith('.tga')) {
        // TGA: decode with our custom decoder
        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                const tga = decodeTGA(e.target.result);
                loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);
            } catch (err) {
                showToast(`TGA decode error: ${err.message}`, true);
            }
        };
        reader.readAsArrayBuffer(file);
    } else {
        // PNG/JPG/BMP: browser-native decode
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = new Image();
            img.onload = function () {
                const canvas = document.getElementById('paintCanvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                // Also size region canvas
                const regionCanvas = document.getElementById('regionCanvas');
                regionCanvas.width = img.width;
                regionCanvas.height = img.height;

                // Show/hide elements for 3-column layout
                const emptyBig = document.getElementById('paintPreviewEmptyBig');
                if (emptyBig) emptyBig.style.display = 'none';
                const empty2 = document.getElementById('paintPreviewEmpty2');
                if (empty2) empty2.style.display = 'none';
                document.getElementById('paintPreviewLoaded').style.display = 'flex';
                const advBar2 = document.getElementById('advancedToolbar'); if (advBar2) advBar2.style.display = 'flex';
                const edInfo2 = document.getElementById('eyedropperInfo'); if (edInfo2) edInfo2.style.display = 'block';
                document.getElementById('paintDimensions').textContent = `${img.width}x${img.height}`;
                document.getElementById('paintPreviewStatus').textContent = `(${img.width}x${img.height})`;
                const canvasInner = document.getElementById('canvasInner');
                if (canvasInner) canvasInner.style.display = 'block';
                const zoomCtrl = document.getElementById('zoomControls');
                if (zoomCtrl) zoomCtrl.style.display = 'flex';

                setupCanvasHandlers(canvas);
                canvasZoom('fit');
                showToast(`Loaded ${fileName} as source paint + preview!`);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

function browseOutputFolder(input) {
    // Browser folder picker - extract the folder path from the first file
    const files = input.files;
    if (!files || files.length === 0) return;
    // webkitRelativePath gives us "folderName/filename" - we just need the folder
    const relPath = files[0].webkitRelativePath || '';
    const folderName = relPath.split('/')[0] || '';
    if (folderName) {
        // We can't get the real absolute path from a browser picker, so show a hint
        document.getElementById('outputDir').value = folderName;
        showToast(`Folder selected: "${folderName}" - paste the FULL path (e.g. C:\\Users\\...\\iRacing\\paint\\${folderName})`, true);
    }
}

// ===== SERVER-POWERED FILE PICKER =====
let _filePickerCallback = null;
let _filePickerFilter = '';
let _filePickerMode = 'file'; // 'file' or 'folder'
let _filePickerSelectedPath = '';

function openFilePicker(options) {
    // options: { title, filter, mode, startPath, onSelect }
    const overlay = document.getElementById('filePickerOverlay');
    document.getElementById('filePickerTitle').textContent = options.title || 'Select File';
    _filePickerCallback = options.onSelect || null;
    _filePickerFilter = options.filter || '';
    _filePickerMode = options.mode || 'file';
    _filePickerSelectedPath = '';
    document.getElementById('filePickerPath').value = '';
    document.getElementById('filePickerSelectBtn').disabled = true;
    overlay.classList.add('active');

    // Set up event delegation for file list clicks (avoids inline onclick escaping issues)
    const _fpList = document.getElementById('filePickerList');
    if (!_fpList._delegated) {
        _fpList._delegated = true;
        _fpList.addEventListener('click', function (e) {
            const item = e.target.closest('[data-fp-action]');
            if (!item) return;
            e.stopPropagation();
            const action = item.dataset.fpAction;
            const fpPath = item.dataset.fpPath || '';
            if (action === 'navigate') filePickerNavigate(fpPath);
            else if (action === 'select') filePickerSelectItem(item, fpPath);
        });
        _fpList.addEventListener('dblclick', function (e) {
            const item = e.target.closest('[data-fp-action="select"]');
            if (!item) return;
            filePickerDblSelect(item.dataset.fpPath || '');
        });
    }

    // If we have a start path, navigate there; otherwise show root
    const startPath = options.startPath || '';
    filePickerNavigate(startPath);
}

function closeFilePicker() {
    document.getElementById('filePickerOverlay').classList.remove('active');
    _filePickerCallback = null;
}

function filePickerSelect() {
    const path = _filePickerSelectedPath || document.getElementById('filePickerPath').value;
    if (path && _filePickerCallback) {
        _filePickerCallback(path);
    }
    closeFilePicker();
}

async function filePickerNavigate(dirPath) {
    const listEl = document.getElementById('filePickerList');
    const breadcrumbEl = document.getElementById('filePickerBreadcrumb');
    const quickNavEl = document.getElementById('filePickerQuickNav');

    listEl.innerHTML = '<div class="file-picker-loading with-spinner">Scanning folder...</div>';
    _filePickerSelectedPath = '';
    document.getElementById('filePickerPath').value = '';
    document.getElementById('filePickerSelectBtn').disabled = (_filePickerMode === 'file');

    // If mode=folder and we have a dirPath, allow selecting the current folder
    if (_filePickerMode === 'folder' && dirPath) {
        _filePickerSelectedPath = dirPath;
        document.getElementById('filePickerPath').value = dirPath;
        document.getElementById('filePickerSelectBtn').disabled = false;
    }

    try {
        console.log('[FilePicker] navigating to:', dirPath);
        document.title = 'ShokkerPaintBooth - Loading...';
        // Yield to UI thread so spinner paints before we do anything else
        await new Promise(r => setTimeout(r, 0));
        const _t0 = performance.now();
        let data;

        // --- PRIMARY: Electron IPC (direct Node.js fs, no server, no HTTP) ---
        if (window.electronAPI) {
            console.log('[FilePicker] Using Electron IPC for directory listing');
            if (!dirPath) {
                // Root view: get drives + quick navs
                const navs = await window.electronAPI.getQuickNavs();
                data = { path: '', drives: navs.drives, quick_navs: navs.quick_navs, items: [] };
            } else {
                data = await window.electronAPI.listDir(dirPath, _filePickerFilter);
            }
        } else {
            // --- FALLBACK: server fetch (for dev mode without Electron) ---
            console.log('[FilePicker] Using server fetch (no electronAPI)');
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 15000);
            const res = await fetch(ShokkerAPI.baseUrl + '/browse-files', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: dirPath, filter: _filePickerFilter }),
                signal: controller.signal,
            });
            clearTimeout(timeout);
            data = await res.json();
        }
        console.log('[FilePicker] data ready in', (performance.now() - _t0).toFixed(0), 'ms, items:', data?.items?.length);

        if (data.error) {
            listEl.innerHTML = `<div class="file-picker-loading" style="color:#ff4444;">${data.error}</div>`;
            return;
        }

        // Build breadcrumb
        if (data.path) {
            const parts = data.path.split('/').filter(Boolean);
            let crumbs = '<span onclick="filePickerNavigate(\'\')" title="Root / Drives">&#128187;</span>';
            let accumulated = '';
            for (let i = 0; i < parts.length; i++) {
                accumulated += parts[i] + '/';
                const escapedPath = accumulated.replace(/'/g, "\\'");
                crumbs += `<span class="sep">/</span><span onclick="filePickerNavigate('${escapedPath}')">${parts[i]}</span>`;
            }
            breadcrumbEl.innerHTML = crumbs;
            breadcrumbEl.style.display = 'flex';
        } else {
            breadcrumbEl.innerHTML = '<span style="color:var(--text-dim);">Select a drive or shortcut to start</span>';
            breadcrumbEl.style.display = 'flex';
        }

        // Build quick nav buttons (only shown at root)
        if (data.drives || data.quick_navs) {
            let qhtml = '';
            if (data.quick_navs) {
                data.quick_navs.forEach(q => {
                    const ep = q.path.replace(/'/g, "\\'");
                    qhtml += `<button onclick="filePickerNavigate('${ep}')" title="${q.path}">&#9889; ${q.name}</button>`;
                });
            }
            if (data.drives) {
                data.drives.forEach(d => {
                    const ep = d.path.replace(/'/g, "\\'");
                    qhtml += `<button onclick="filePickerNavigate('${ep}')" title="${d.path}">&#128190; ${d.name}</button>`;
                });
            }
            quickNavEl.innerHTML = qhtml;
            quickNavEl.style.display = 'flex';
        } else {
            quickNavEl.style.display = 'none';
        }

        // Build file list
        let html = '';

        // Parent directory link
        if (data.parent) {
            html += `<div class="file-picker-item folder" data-fp-action="navigate" data-fp-path="${data.parent.replace(/"/g, '&quot;')}">
                <span class="fp-icon">&#128281;</span>
                <span class="fp-name">..</span>
            </div>`;
        }

        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                const safeP = item.path.replace(/"/g, '&quot;');
                if (item.type === 'folder' || item.type === 'drive') {
                    html += `<div class="file-picker-item ${item.type}" data-fp-action="navigate" data-fp-path="${safeP}">
                        <span class="fp-icon">${item.type === 'drive' ? '&#128190;' : '&#128193;'}</span>
                        <span class="fp-name">${item.name}</span>
                    </div>`;
                } else {
                    html += `<div class="file-picker-item file" data-fp-action="select" data-fp-path="${safeP}">
                        <span class="fp-icon">${item.name.toLowerCase().endsWith('.tga') ? '&#127912;' : '&#128196;'}</span>
                        <span class="fp-name">${item.name}</span>
                        <span class="fp-size">${item.size_human || ''}</span>
                    </div>`;
                }
            });
        } else if (!data.drives) {
            html += '<div class="file-picker-loading" style="color:var(--text-dim);">No matching files in this folder</div>';
        }

        // Show overflow warning if server truncated or skipped files
        if (data.large_dir) {
            html += `<div style="padding:8px 12px;color:#ffaa00;font-size:12px;border-top:1px solid #333;margin-top:4px;">&#128193; Large folder (${data.entry_count?.toLocaleString() || 'many'} entries) - showing folders only. Click a car folder to see paint files.</div>`;
        } else if (data.hidden_files && data.hidden_files > 0) {
            html += `<div style="padding:8px 12px;color:#ffaa00;font-size:12px;border-top:1px solid #333;margin-top:4px;">&#9888; ${data.hidden_files.toLocaleString()} files not shown (${data.total_files.toLocaleString()} total). Navigate into a car folder to find your paint file.</div>`;
        }

        // Use rAF to render so the browser can paint between fetch and DOM update
        requestAnimationFrame(() => {
            listEl.innerHTML = html;
            document.title = 'Shokker Paint Booth';
        });

    } catch (e) {
        console.error('[FilePicker] ERROR:', e.name, e.message);
        document.title = 'Shokker Paint Booth';
        const msg = e.name === 'AbortError'
            ? 'This folder took too long to load. Try using the Go button to paste a path directly.'
            : `Server error: ${e.message}`;
        listEl.innerHTML = `<div class="file-picker-loading" style="color:#ff4444;">${msg}</div>`;
    }
}

function filePickerSelectItem(el, path) {
    // Deselect previous
    document.querySelectorAll('.file-picker-item.selected').forEach(e => e.classList.remove('selected'));
    el.classList.add('selected');
    _filePickerSelectedPath = path;
    document.getElementById('filePickerPath').value = path;
    document.getElementById('filePickerSelectBtn').disabled = false;
}

function filePickerDblSelect(path) {
    _filePickerSelectedPath = path;
    document.getElementById('filePickerPath').value = path;
    filePickerSelect();
}

// Convenience wrappers for the Browse buttons
async function resetSourceBackup() {
    const paintFile = document.getElementById('paintFile').value.trim();
    const iracingId = document.getElementById('iracingId').value.trim();
    if (!paintFile) { showToast('Set the Source Paint path first', true); return; }
    if (!confirm('Reset source backup? This forces the next render to re-read the current source file as the clean original. Use this if renders seem stuck or unchanged.')) return;
    try {
        const result = await ShokkerAPI.resetBackup(paintFile, iracingId);
        if (result.success) {
            showToast(result.message);
        } else {
            showToast('Reset failed: ' + (result.error || 'unknown'), true);
        }
    } catch (e) {
        showToast('Reset error: ' + e.message, true);
    }
}

function openPaintFilePicker() {
    // Try to start from the current path's directory
    let startPath = '';
    const currentPath = document.getElementById('paintFile').value.trim();
    if (currentPath) {
        const dir = currentPath.replace(/[/\\][^/\\]+$/, '');
        startPath = dir;
    }
    openFilePicker({
        title: 'Select Source Paint TGA',
        filter: '.tga',
        mode: 'file',
        startPath: startPath,
        onSelect: function (path) {
            document.getElementById('paintFile').value = path;
            validatePaintPath();
            // Auto-load the TGA as preview via server conversion
            loadPaintPreviewFromServer(path);
            showToast('Source Paint set + loading preview...');
        }
    });
}

async function loadPaintPreviewFromServer(tgaPath) {
    /**Load a TGA file from the server as a PNG preview into the canvas.
     * This also sets the preview so the user can eyedrop colors from it.
     */
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/preview-tga', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: tgaPath }),
        });
        if (!res.ok) {
            showToast('Could not load preview: ' + res.statusText, true);
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = function () {
            const canvas = document.getElementById('paintCanvas');
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            paintImageData = ctx.getImageData(0, 0, img.width, img.height);
            // Also size region canvas
            const regionCanvas = document.getElementById('regionCanvas');
            regionCanvas.width = img.width;
            regionCanvas.height = img.height;

            // Show/hide elements
            const emptyBig = document.getElementById('paintPreviewEmptyBig');
            if (emptyBig) emptyBig.style.display = 'none';
            const empty2 = document.getElementById('paintPreviewEmpty2');
            if (empty2) empty2.style.display = 'none';
            document.getElementById('paintPreviewLoaded').style.display = 'flex';
            const advBar3 = document.getElementById('advancedToolbar'); if (advBar3) advBar3.style.display = 'flex';
            const edInfo3 = document.getElementById('eyedropperInfo'); if (edInfo3) edInfo3.style.display = 'block';
            document.getElementById('paintDimensions').textContent = `${img.width}x${img.height}`;
            document.getElementById('paintPreviewStatus').textContent = `(${img.width}x${img.height})`;
            const canvasInner = document.getElementById('canvasInner');
            if (canvasInner) canvasInner.style.display = 'block';
            const zoomCtrl = document.getElementById('zoomControls');
            if (zoomCtrl) zoomCtrl.style.display = 'flex';

            setupCanvasHandlers(canvas);
            canvasZoom('fit');
            showToast(`Preview loaded: ${img.width}x${img.height}`);
            URL.revokeObjectURL(url);
        };
        img.onerror = function () {
            showToast('Failed to decode preview image', true);
            URL.revokeObjectURL(url);
        };
        img.src = url;
    } catch (e) {
        showToast('Preview load error: ' + e.message, true);
    }
}

function openOutputFolderPicker() {
    let startPath = '';
    const currentPath = document.getElementById('outputDir').value.trim();
    if (currentPath) startPath = currentPath;
    openFilePicker({
        title: 'Select iRacing Paint Folder',
        filter: '',
        mode: 'folder',
        startPath: startPath,
        onSelect: function (path) {
            document.getElementById('outputDir').value = path;
            updateOutputPath();
            showToast('iRacing folder set!');
        }
    });
}

function openHelmetFilePicker() {
    openFilePicker({
        title: 'Select Helmet Paint TGA',
        filter: '.tga',
        mode: 'file',
        startPath: '',
        onSelect: function (path) {
            document.getElementById('helmetFile').value = path;
            showToast('Helmet paint path set!');
        }
    });
}

function openSuitFilePicker() {
    openFilePicker({
        title: 'Select Suit Paint TGA',
        filter: '.tga',
        mode: 'file',
        startPath: '',
        onSelect: function (path) {
            document.getElementById('suitFile').value = path;
            showToast('Suit paint path set!');
        }
    });
}

// ===== PAINT PREVIEW & EYEDROPPER =====

// Shared: set up hover + click + draw handlers on the canvas
function setupCanvasHandlers(canvas) {
    function getPixelAt(e) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = Math.floor((e.clientX - rect.left) * scaleX);
        const y = Math.floor((e.clientY - rect.top) * scaleY);
        if (x < 0 || x >= canvas.width || y < 0 || y >= canvas.height) return null;
        return { x, y };
    }

    // Like getPixelAt but clamps to canvas edges instead of returning null.
    // Used by rect/gradient drag so the preview stays active when the mouse
    // leaves the canvas - the selection just pins to the nearest edge.
    function getPixelAtClamped(e) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const x = Math.max(0, Math.min(canvas.width - 1, Math.floor((e.clientX - rect.left) * scaleX)));
        const y = Math.max(0, Math.min(canvas.height - 1, Math.floor((e.clientY - rect.top) * scaleY)));
        return { x, y };
    }

    function getColorAt(x, y) {
        const idx = (y * canvas.width + x) * 4;
        return {
            r: paintImageData.data[idx],
            g: paintImageData.data[idx + 1],
            b: paintImageData.data[idx + 2]
        };
    }

    function toHex(r, g, b) {
        return '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
    }


    function getBrushSize() {
        return parseInt(document.getElementById('brushSize')?.value || 20);
    }

    // ── FAST OVERLAY ARC ──────────────────────────────────────────────────────
    // During active brush/erase strokes, drawing a full 2048×2048 ImageData on
    // every mousemove is catastrophically slow (~16 MB alloc + 2 full-canvas
    // scans per frame).  Instead, we paint directly onto regionCanvas with a
    // GPU-accelerated arc() call - O(1) vs O(W×H).  A full renderRegionOverlay()
    // syncs everything correctly once at stroke-start (mousedown) and stroke-end
    // (mouseup), so edges and multi-zone overlaps are always accurate at rest.
    // _rectZoneCache declared at outer scope (before drawRectPreview) so both
    // setupCanvasHandlers internals and drawRectPreview can access it.

    function _fastOverlayArc(cx, cy, radius, value) {
        const paintCanvas = document.getElementById('paintCanvas');
        const regionCanvas = document.getElementById('regionCanvas');
        if (!regionCanvas || !paintCanvas) return;
        // Sync dims here - RAF-throttled renderRegionOverlay() may not have fired yet
        // on first mousemove after mousedown, leaving regionCanvas at default 300×150
        if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
            regionCanvas.width = paintCanvas.width;
            regionCanvas.height = paintCanvas.height;
            regionCanvas.style.width = paintCanvas.style.width;
            regionCanvas.style.height = paintCanvas.style.height;
        }
        const ctx = regionCanvas.getContext('2d');
        if (value === 0) {
            // Erase: punch a hole through the overlay
            ctx.globalCompositeOperation = 'destination-out';
            ctx.fillStyle = 'rgba(0,0,0,1)';
        } else {
            // Paint: draw the zone colour circle
            ctx.globalCompositeOperation = 'source-over';
            const color = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
            ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${(color[3] / 255).toFixed(3)})`;
        }
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalCompositeOperation = 'source-over';
    }

    function paintRegionCircle(x, y, radius, value) {
        // Paint into the current zone's regionMask
        const zone = zones[selectedZoneIndex];
        if (!zone) return;
        if (!zone.regionMask) {
            zone.regionMask = new Uint8Array(canvas.width * canvas.height);
        }
        const r2 = radius * radius;
        for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
                if (dx * dx + dy * dy > r2) continue;
                const px = x + dx, py = y + dy;
                if (px < 0 || px >= canvas.width || py < 0 || py >= canvas.height) continue;
                zone.regionMask[py * canvas.width + px] = value;
            }
        }
    }

    // Constrain rect end point so rect becomes a square (Shift held = PS behavior)
    function constrainRectToSquare(start, end) {
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const size = Math.max(Math.abs(dx), Math.abs(dy));
        return { x: start.x + size * Math.sign(dx || 1), y: start.y + size * Math.sign(dy || 1) };
    }

    function paintRegionRect(x1, y1, x2, y2, value) {
        const zone = zones[selectedZoneIndex];
        if (!zone) return;
        if (!zone.regionMask) {
            zone.regionMask = new Uint8Array(canvas.width * canvas.height);
        }
        const w = canvas.width;
        const minX = Math.max(0, Math.min(x1, x2));
        const maxX = Math.min(w - 1, Math.max(x1, x2));
        const minY = Math.max(0, Math.min(y1, y2));
        const maxY = Math.min(canvas.height - 1, Math.max(y1, y2));

        // Color-aware rectangle: if eyedropper color is set and paint image is loaded,
        // only fill pixels within the rect that match the eyedropper color (within tolerance).
        // This lets you: eyedrop blue → draw rect → only the blue pixels inside the rect get masked.
        const useColorFilter = (value === 1) && lastEyedropperColor && paintImageData;

        if (useColorFilter) {
            const data = paintImageData.data;
            const seedR = lastEyedropperColor.r;
            const seedG = lastEyedropperColor.g;
            const seedB = lastEyedropperColor.b;
            const tolerance = parseInt(document.getElementById('wandTolerance')?.value) || 32;
            const tolSq = tolerance * tolerance * 3; // Euclidean RGB squared (same as wand/selectAll)
            let filled = 0;

            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    const pi = (y * w + x) * 4;
                    const dr = data[pi] - seedR;
                    const dg = data[pi + 1] - seedG;
                    const db = data[pi + 2] - seedB;
                    if ((dr * dr + dg * dg + db * db) <= tolSq) {
                        zone.regionMask[y * w + x] = 1;
                        filled++;
                    }
                }
            }
            showToast(`Rect + Color: ${filled.toLocaleString()} matching pixels selected`);
        } else {
            // No eyedropper color - fill entire rectangle (legacy behavior)
            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    zone.regionMask[y * w + x] = value;
                }
            }
        }
    }

    canvas.onmousemove = function (e) {
        // Pan mode - don't draw while panning
        if (isPanning || spaceHeld) return;

        // Compare mode intercept
        if (compareMode && compareDragging) { onCompareMouseMove(e); return; }

        const pos = getPixelAt(e);
        if (!pos) return;

        if (canvasMode === 'eyedropper') {
            const px = getColorAt(pos.x, pos.y);
            const hex = toHex(px.r, px.g, px.b);
            document.getElementById('hoverInfo').style.display = 'block';
            document.getElementById('hoverSwatch').style.background = hex;
            document.getElementById('hoverHex').textContent = hex.toUpperCase();
            document.getElementById('hoverRGB').textContent = `RGB(${px.r}, ${px.g}, ${px.b})`;
        } else if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {
            const radius = getBrushSize();
            const val = canvasMode === 'brush' ? 1 : 0;
            paintRegionCircle(pos.x, pos.y, radius, val);
            _fastOverlayArc(pos.x, pos.y, radius, val); // fast GPU draw - no full ImageData rebuild
        } else if ((canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude') && isDrawing) {
            const val = canvasMode === 'spatial-include' ? 1 : 2;
            paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);
            renderRegionOverlay();
        } else if (canvasMode === 'rect' && isDrawing && rectStart) {
            // Use clamped coords so drag pins to canvas edge instead of dying
            let cpos = getPixelAtClamped(e);
            if (e.shiftKey) cpos = constrainRectToSquare(rectStart, cpos);
            drawRectPreview(rectStart, cpos);
        }
    };

    canvas.onmouseleave = function () {
        document.getElementById('hoverInfo').style.display = 'none';
        if (canvasMode !== 'rect') isDrawing = false;
    };

    canvas.onmousedown = function (e) {
        // Pan mode intercept - space+drag, middle-click, right-click, or active pan
        if (spaceHeld || e.button === 1 || e.button === 2 || isPanning) return;

        // Compare mode intercept
        if (compareMode) { onCompareMouseDown(e); return; }

        // Prevent native canvas image drag for draw tools - without this,
        // the browser can start a drag-and-drop operation that steals mousemove events
        if (['brush', 'rect', 'erase', 'spatial-include', 'spatial-exclude', 'lasso'].includes(canvasMode)) {
            e.preventDefault();
        }

        const pos = getPixelAt(e);
        if (!pos) return;

        if (canvasMode === 'eyedropper') {
            const px = getColorAt(pos.x, pos.y);
            lastEyedropperColor = px;
            const hex = toHex(px.r, px.g, px.b);
            document.getElementById('eyedropperSwatch').style.background = hex;
            document.getElementById('eyedropperRGB').textContent = `RGB: (${px.r}, ${px.g}, ${px.b})`;
            document.getElementById('eyedropperHex').textContent = hex.toUpperCase();
            document.getElementById('hoverInfo').style.display = 'none';
            document.getElementById('eyedropperInfo').style.display = 'block';
            updateEyedropperZoneSelect();
        } else if (canvasMode === 'brush' || canvasMode === 'erase') {
            pushUndo(selectedZoneIndex); // Save state before stroke begins
            isDrawing = true;
            const radius = getBrushSize();
            paintRegionCircle(pos.x, pos.y, radius, canvasMode === 'brush' ? 1 : 0);
            // SYNC render - must complete before first mousemove fires _fastOverlayArc()
            // (RAF-wrapped renderRegionOverlay() is async and may not run in time,
            //  leaving regionCanvas at default 300×150 → tiny dots bug)
            _doRenderRegionOverlay();
        } else if (canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude') {
            pushSpatialUndo(selectedZoneIndex);
            isDrawing = true;
            const val = canvasMode === 'spatial-include' ? 1 : 2;
            paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);
            _doRenderRegionOverlay();
        } else if (canvasMode === 'lasso') {
            // Right-click undoes last lasso point
            if (e.button === 2) { undoLassoPoint(); return; }
            addLassoPoint(pos.x, pos.y);
            // Double-click closes the lasso
            if (e.detail >= 2 && lassoPoints.length >= 3) {
                closeLasso();
            }
        } else if (canvasMode === 'rect') {
            pushUndo(selectedZoneIndex); // Save state before rect draw
            isDrawing = true;
            rectStart = pos;
            _rectZoneCache = null;
            // Eagerly build zone overlay cache synchronously so drawRectPreview()
            // never needs to call the expensive renderRegionOverlayData() during drag
            _doRenderRegionOverlay();
            const _rcPre = document.getElementById('regionCanvas');
            if (_rcPre && _rcPre.width > 0 && _rcPre.height > 0) {
                _rectZoneCache = _rcPre.getContext('2d').getImageData(0, 0, _rcPre.width, _rcPre.height);
            }
        } else if (canvasMode === 'wand' || canvasMode === 'selectall') {
            pushUndo(selectedZoneIndex); // Save state before wand fill
            const tolerance = parseInt(document.getElementById('wandTolerance').value) || 32;
            const selMode = document.getElementById('selectionMode')?.value || 'add';
            let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
            let subtractMode = selMode === 'subtract' || e.altKey;
            let addToExisting = (selMode === 'add') || e.shiftKey;
            if (replaceMode) addToExisting = false;
            if (subtractMode) addToExisting = false;

            const contiguous = document.getElementById('wandContiguous')?.checked ?? (canvasMode === 'wand');
            if (subtractMode) {
                subtractWandSelection(pos.x, pos.y, tolerance, contiguous);
            } else if (contiguous) {
                magicWandFill(pos.x, pos.y, tolerance, addToExisting);
            } else {
                selectAllColor(pos.x, pos.y, tolerance, addToExisting);
            }
            renderRegionOverlay();
        } else if (canvasMode === 'edge') {
            pushUndo(selectedZoneIndex);
            const tolerance = parseInt(document.getElementById('wandTolerance').value) || 32;
            const selMode = document.getElementById('selectionMode')?.value || 'add';
            let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
            let subtractMode = selMode === 'subtract' || e.altKey;
            let addToExisting = (selMode === 'add') || e.shiftKey;
            if (replaceMode) addToExisting = false;
            if (subtractMode) addToExisting = false;

            edgeDetectFill(pos.x, pos.y, tolerance, addToExisting, subtractMode);
            renderRegionOverlay();
        }
    };

    canvas.onmouseup = function (e) {
        if (canvasMode === 'rect' && isDrawing && rectStart) {
            let pos = getPixelAtClamped(e);
            if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);

            const selMode = document.getElementById('selectionMode')?.value || 'add';
            let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
            let subtractMode = selMode === 'subtract' || e.altKey;

            if (replaceMode && zones[selectedZoneIndex]) {
                const zone = zones[selectedZoneIndex];
                const canvas = document.getElementById('paintCanvas');
                if (canvas && zone.regionMask) {
                    zone.regionMask = new Uint8Array(canvas.width * canvas.height);
                }
            }

            const fillVal = subtractMode ? 0 : 1;
            paintRegionRect(rectStart.x, rectStart.y, pos.x, pos.y, fillVal);
            rectStart = null;
            _rectZoneCache = null;
            hideRectPreview();
            renderRegionOverlay();
        }
        // Brush/erase: full re-render once at stroke end so edges and multi-zone
        // overlaps are drawn correctly (fast arc path skips those)
        if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {
            renderRegionOverlay();
        }
        if ((canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude') && isDrawing) {
            _doRenderRegionOverlay();
        }
        isDrawing = false;
    };

    // Remove old onclick (now handled by onmousedown)
    canvas.onclick = null;

    // Block native canvas image drag - browsers treat <canvas> as a draggable image,
    // which steals mousemove events during drag-to-draw operations
    canvas.addEventListener('dragstart', (e) => e.preventDefault());

    // Document-level mousemove for rect/gradient preview during drag.
    // canvas.onmousemove can miss events if the cursor briefly leaves the canvas
    // element during fast drags, or if the browser's hit-testing is off due to
    // CSS transforms (zoom). This listener ensures preview always updates.
    document.addEventListener('mousemove', function _rectGradDocMove(e) {
        if (isPanning || spaceHeld) return;
        if (canvasMode === 'rect' && isDrawing && rectStart) {
            // Clamped so drag-to-edge pins to canvas boundary instead of stopping
            let pos = getPixelAtClamped(e);
            if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);
            drawRectPreview(rectStart, pos);
        }
    });

    // Document-level mouseup - commits rect even when mouse is
    // released outside the canvas (edge drag scenario).
    document.addEventListener('mouseup', function _rectDocUp(e) {
        if (canvasMode === 'rect' && isDrawing && rectStart) {
            let pos = getPixelAtClamped(e);
            if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);
            paintRegionRect(rectStart.x, rectStart.y, pos.x, pos.y, 1);
            rectStart = null;
            _rectZoneCache = null;
            hideRectPreview();
            renderRegionOverlay();
            isDrawing = false;
        }
    });
}

function setCanvasMode(mode) {
    canvasMode = mode;
    const canvas = document.getElementById('paintCanvas');

    // Update toolbar button active states
    document.querySelectorAll('.draw-tool-btn').forEach(btn => btn.classList.remove('active'));
    const btnId = {
        eyedropper: 'modeEyedropper', brush: 'modeBrush', rect: 'modeRect',
        erase: 'modeErase', wand: 'modeWand', selectall: 'modeSelectAll',
        edge: 'modeEdge', 'spatial-include': 'modeSpatialInclude',
        'spatial-exclude': 'modeSpatialExclude', lasso: 'modeLasso'
    }[mode];
    document.getElementById(btnId)?.classList.add('active');
    // Reset lasso state when switching away
    if (mode !== 'lasso' && lassoActive) { lassoActive = false; lassoPoints = []; hideLassoPreview(); }

    // Toggle tool-specific controls
    const showBrush = (mode === 'brush' || mode === 'erase');
    const showWand = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect');
    const showSpatial = (mode === 'spatial-include' || mode === 'spatial-exclude');
    document.getElementById('brushSizeLabel').style.display = showBrush ? '' : 'none';
    document.getElementById('brushSize').style.display = showBrush ? '' : 'none';
    document.getElementById('brushSizeVal').style.display = showBrush ? '' : 'none';
    document.getElementById('wandToleranceLabel').style.display = showWand ? '' : 'none';
    document.getElementById('wandTolerance').style.display = showWand ? '' : 'none';
    document.getElementById('wandTolVal').style.display = showWand ? '' : 'none';
    // Show selection mode for selection tools
    const showSelMode = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect' || mode === 'lasso');
    const selModeEl = document.getElementById('selectionMode');
    if (selModeEl) selModeEl.style.display = showSelMode ? '' : 'none';
    // Contiguous checkbox only for wand/selectall, not edge/rect
    const showContiguous = (mode === 'wand' || mode === 'selectall');
    document.getElementById('wandContiguousLabel').style.display = showContiguous ? '' : 'none';
    const wandHint = document.getElementById('wandSubtractHint');
    if (wandHint) wandHint.style.display = 'none';
    // When switching to selectall, uncheck contiguous; when switching to wand, check it
    if (mode === 'selectall') document.getElementById('wandContiguous').checked = false;
    else if (mode === 'wand') document.getElementById('wandContiguous').checked = true;
    document.getElementById('spatialSizeLabel').style.display = showSpatial ? '' : 'none';
    document.getElementById('spatialBrushSize').style.display = showSpatial ? '' : 'none';
    document.getElementById('spatialSizeVal').style.display = showSpatial ? '' : 'none';

    // Edge preview button: only visible in edge mode
    const edgeBtn = document.getElementById('edgePreviewBtn');
    if (edgeBtn) {
        edgeBtn.style.display = (mode === 'edge') ? '' : 'none';
        if (mode !== 'edge') { clearEdgePreviewOverlay(); edgePreviewActive = false; edgeBtn.style.background = ''; }
    }

    // Update cursor
    const viewport = document.getElementById('canvasViewport');
    if (mode === 'eyedropper') {
        canvas.style.cursor = 'crosshair';
        if (viewport) viewport.style.cursor = '';
        document.getElementById('drawZoneIndicator').style.display = 'none';
        document.getElementById('regionCanvas').style.pointerEvents = 'none';
    } else if (showSpatial) {
        canvas.style.cursor = 'none'; // Hide native cursor, use brush circle
        if (viewport) viewport.style.cursor = '';
        document.getElementById('drawZoneIndicator').style.display = 'flex';
        updateDrawZoneIndicator();
        document.getElementById('regionCanvas').style.pointerEvents = 'none';
    } else if (showBrush) {
        canvas.style.cursor = 'none'; // Hide native cursor, use brush circle
        if (viewport) viewport.style.cursor = '';
        document.getElementById('drawZoneIndicator').style.display = 'flex';
        updateDrawZoneIndicator();
        document.getElementById('regionCanvas').style.pointerEvents = 'none';
    } else if (mode === 'lasso') {
        canvas.style.cursor = 'crosshair';
        if (viewport) viewport.style.cursor = '';
        document.getElementById('drawZoneIndicator').style.display = 'flex';
        updateDrawZoneIndicator();
        document.getElementById('regionCanvas').style.pointerEvents = 'none';
        startLasso();
    } else {
        canvas.style.cursor = (mode === 'wand' || mode === 'selectall' || mode === 'edge') ? 'crosshair' : 'cell';
        if (viewport) viewport.style.cursor = '';
        document.getElementById('drawZoneIndicator').style.display = 'flex';
        updateDrawZoneIndicator();
        document.getElementById('regionCanvas').style.pointerEvents = 'none';
    }

    // Show/hide brush cursor circle
    updateBrushCursorVisibility();
}

function updateDrawZoneIndicator() {
    const zoneColor = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
    document.getElementById('drawZoneName').textContent = `Zone ${selectedZoneIndex + 1}: ${zones[selectedZoneIndex]?.name || '?'}`;
    document.getElementById('drawZoneColorDot').style.background = `rgba(${zoneColor[0]},${zoneColor[1]},${zoneColor[2]},0.8)`;

    // Update label and hint based on mode
    const label = document.getElementById('drawZoneLabel');
    const hint = document.getElementById('drawZoneHint');
    if (canvasMode === 'wand') {
        label.textContent = 'Wand select for:';
        hint.textContent = '(click a number/logo/shape - Shift+click to add more areas)';
    } else if (canvasMode === 'erase') {
        label.textContent = 'Erasing from:';
        hint.textContent = '(paint over drawn areas to remove them)';
    } else if (canvasMode === 'spatial-include') {
        label.textContent = '✅ Including for:';
        label.style.color = 'var(--accent-green)';
        hint.textContent = '(paint green areas to KEEP in this zone\'s color match)';
    } else if (canvasMode === 'spatial-exclude') {
        label.textContent = '❌ Excluding from:';
        label.style.color = '#ff4444';
        hint.textContent = '(paint red areas to REMOVE from this zone\'s color match)';
    } else if (canvasMode === 'lasso') {
        label.textContent = '⬡ Lasso for:';
        label.style.color = 'var(--accent-gold)';
        hint.textContent = `(click to place vertices, double-click to fill - ${lassoPoints.length} points)`;
    } else {
        label.textContent = 'Drawing for:';
        label.style.color = '';
        hint.textContent = '(select a different zone on the left to switch)';
    }
}

// ===== BRUSH CURSOR CIRCLE - visible radius indicator =====
function updateBrushCursorVisibility() {
    const circle = document.getElementById('brushCursorCircle');
    if (!circle) return;
    const showCircle = ['brush', 'erase', 'spatial-include', 'spatial-exclude'].includes(canvasMode);
    circle.style.display = showCircle ? 'block' : 'none';
    if (showCircle) {
        // Color the circle based on mode
        if (canvasMode === 'spatial-include') {
            circle.style.borderColor = 'rgba(0,200,100,0.8)';
        } else if (canvasMode === 'spatial-exclude') {
            circle.style.borderColor = 'rgba(220,50,50,0.8)';
        } else if (canvasMode === 'erase') {
            circle.style.borderColor = 'rgba(255,255,255,0.5)';
        } else {
            circle.style.borderColor = 'rgba(255,255,255,0.7)';
        }
    }
}

function updateBrushCursorPosition(e) {
    const circle = document.getElementById('brushCursorCircle');
    if (!circle || circle.style.display === 'none') return;
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;

    // Get the brush radius in canvas pixels
    let radius;
    if (canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude') {
        radius = spatialBrushRadius;
    } else {
        radius = parseInt(document.getElementById('brushSize')?.value || 20);
    }

    // Convert canvas pixels to screen pixels using current zoom
    const rect = canvas.getBoundingClientRect();
    const scaleX = rect.width / canvas.width;
    const screenRadius = radius * scaleX;
    const diameter = screenRadius * 2;

    circle.style.width = diameter + 'px';
    circle.style.height = diameter + 'px';
    circle.style.left = (e.clientX - screenRadius) + 'px';
    circle.style.top = (e.clientY - screenRadius) + 'px';
}

// Attach global mousemove for brush cursor tracking
document.addEventListener('mousemove', function (e) {
    if (['brush', 'erase', 'spatial-include', 'spatial-exclude'].includes(canvasMode)) {
        updateBrushCursorPosition(e);
    }
});


// Cached ImageData of zone overlay for rect preview drag (outer scope so both
// setupCanvasHandlers internals and drawRectPreview can access it)
let _rectZoneCache = null;

// Draw rubber-band rectangle during drag.
// Uses a plain CSS DIV (rectSelectionBox) for the marching-ants border.
// CSS borders are always in screen pixels - no canvas scaling issues.
// Zone-colored fill still drawn on regionCanvas.
function drawRectPreview(start, end) {
    const paintCanvas = document.getElementById("paintCanvas");
    const regionCanvas = document.getElementById("regionCanvas");
    const selBox = document.getElementById("rectSelectionBox");
    if (!paintCanvas || !regionCanvas || !selBox) return;

    // Ensure regionCanvas matches paintCanvas full resolution
    if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
        regionCanvas.width = paintCanvas.width;
        regionCanvas.height = paintCanvas.height;
        regionCanvas.style.width = paintCanvas.style.width;
        regionCanvas.style.height = paintCanvas.style.height;
        _rectZoneCache = null;
    }

    // Restore zone overlay on regionCanvas (cached for perf)
    const rctx = regionCanvas.getContext("2d");
    if (!_rectZoneCache) {
        const tmpC = document.createElement('canvas');
        tmpC.width = paintCanvas.width;
        tmpC.height = paintCanvas.height;
        renderRegionOverlayData(tmpC.getContext('2d'), paintCanvas);
        _rectZoneCache = tmpC.getContext('2d').getImageData(0, 0, paintCanvas.width, paintCanvas.height);
    }
    rctx.clearRect(0, 0, regionCanvas.width, regionCanvas.height);
    rctx.putImageData(_rectZoneCache, 0, 0);

    // Draw zone-colored fill on regionCanvas (large solid area, visible at any zoom)
    const rx = Math.min(start.x, end.x);
    const ry = Math.min(start.y, end.y);
    const rw = Math.abs(end.x - start.x);
    const rh = Math.abs(end.y - start.y);
    const color = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
    rctx.fillStyle = "rgba(" + color[0] + "," + color[1] + "," + color[2] + ",0.5)";
    rctx.fillRect(rx, ry, rw, rh);

    // Position the CSS selection box in screen-pixel coordinates
    const zoom = currentZoom || 1;
    selBox.style.left = Math.round(rx * zoom) + 'px';
    selBox.style.top = Math.round(ry * zoom) + 'px';
    selBox.style.width = Math.max(1, Math.round(rw * zoom)) + 'px';
    selBox.style.height = Math.max(1, Math.round(rh * zoom)) + 'px';
    selBox.style.display = 'block';
}

// Hide the rect selection box (call on mouseup / mode change)
function hideRectPreview() {
    const selBox = document.getElementById("rectSelectionBox");
    if (selBox) selBox.style.display = 'none';
}

// Helper: render region mask overlay pixels onto context (selected zone only)
function renderRegionOverlayData(ctx, paintCanvas) {
    const imgData = ctx.createImageData(paintCanvas.width, paintCanvas.height);
    const data = imgData.data;
    const zi = selectedZoneIndex;
    const zone = zones[zi];
    if (zone && zone.regionMask) {
        const color = ZONE_OVERLAY_COLORS[zi % ZONE_OVERLAY_COLORS.length];
        for (let i = 0; i < zone.regionMask.length; i++) {
            if (zone.regionMask[i] > 0) {
                const pi = i * 4;
                data[pi] = color[0]; data[pi + 1] = color[1];
                data[pi + 2] = color[2]; data[pi + 3] = color[3];
            }
        }
    }
    ctx.putImageData(imgData, 0, 0);
}

let _overlayRafPending = false;
function renderRegionOverlay() {
    // RAF-throttle: coalesce multiple sync calls within the same frame into one
    if (_overlayRafPending) return;
    _overlayRafPending = true;
    requestAnimationFrame(() => {
        _overlayRafPending = false;
        _doRenderRegionOverlay();
    });
}
function _doRenderRegionOverlay() {
    const paintCanvas = document.getElementById('paintCanvas');
    const regionCanvas = document.getElementById('regionCanvas');
    if (!paintCanvas || !regionCanvas) return;

    // Only reset canvas dimensions when they actually changed.
    // Setting .width/.height clears the bitmap AND triggers a DOM reflow - very expensive.
    if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
        regionCanvas.width = paintCanvas.width;
        regionCanvas.height = paintCanvas.height;
    }
    if (regionCanvas.style.width !== paintCanvas.style.width) {
        regionCanvas.style.width = paintCanvas.style.width;
        regionCanvas.style.height = paintCanvas.style.height;
    }
    const ctx = regionCanvas.getContext('2d');
    ctx.clearRect(0, 0, regionCanvas.width, regionCanvas.height);
    const imgData = ctx.createImageData(paintCanvas.width, paintCanvas.height);
    const data = imgData.data;

    // Draw ONLY the selected zone's region overlay (other zones' overlays are hidden)
    {
        const zi = selectedZoneIndex;
        const zone = zones[zi];
        if (zone && zone.regionMask) {
            const color = ZONE_OVERLAY_COLORS[zi % ZONE_OVERLAY_COLORS.length];
            for (let i = 0; i < zone.regionMask.length; i++) {
                if (zone.regionMask[i] > 0) {
                    const pi = i * 4;
                    data[pi] = color[0];
                    data[pi + 1] = color[1];
                    data[pi + 2] = color[2];
                    data[pi + 3] = Math.min(255, Math.round(color[3] * overlayOpacityMultiplier));
                }
            }
        }
    }

    // ---- SPATIAL MASK OVERLAY: green=include, red=exclude (selected zone only) ----
    {
        const zi = selectedZoneIndex;
        const zone = zones[zi];
        if (zone && zone.spatialMask) {
            const cw = paintCanvas.width, ch = paintCanvas.height;
            for (let i = 0; i < zone.spatialMask.length && i < cw * ch; i++) {
                const v = zone.spatialMask[i];
                if (v === 0) continue;
                const pi = i * 4;
                if (v === 1) {
                    // Include = green overlay
                    data[pi] = 0; data[pi + 1] = 200; data[pi + 2] = 100; data[pi + 3] = 128;
                } else if (v === 2) {
                    // Exclude = red overlay
                    data[pi] = 220; data[pi + 1] = 50; data[pi + 2] = 50; data[pi + 3] = 128;
                }
            }
        }
    }


    // Draw bright edge outlines for the selected zone only
    {
        const zi = selectedZoneIndex;
        const zone = zones[zi];
        if (zone && zone.regionMask) {
            const color = ZONE_OVERLAY_COLORS[zi % ZONE_OVERLAY_COLORS.length];
            const cw = paintCanvas.width, ch = paintCanvas.height;
            for (let y = 0; y < ch; y++) {
                for (let x = 0; x < cw; x++) {
                    const idx = y * cw + x;
                    if (zone.regionMask[idx] > 0) {
                        const isEdge = (
                            x === 0 || x === cw - 1 || y === 0 || y === ch - 1 ||
                            zone.regionMask[idx - 1] === 0 || zone.regionMask[idx + 1] === 0 ||
                            zone.regionMask[idx - cw] === 0 || zone.regionMask[idx + cw] === 0
                        );
                        if (isEdge) {
                            const pi = idx * 4;
                            imgData.data[pi] = 255; imgData.data[pi + 1] = 255;
                            imgData.data[pi + 2] = 255; imgData.data[pi + 3] = 255;
                        }
                    }
                }
            }
        }
    }
    ctx.putImageData(imgData, 0, 0);

    // Decal overlay disabled - future feature
}

// ===== UNDO SYSTEM =====
function pushUndo(zoneIndex) {
    const zone = zones[zoneIndex];
    if (!zone) return;
    // Save a copy of the current masks (or null if no mask yet)
    const prevMask = zone.regionMask ? new Uint8Array(zone.regionMask) : null;
    const prevSpatial = zone.spatialMask ? new Uint8Array(zone.spatialMask) : null;
    undoStack.push({ zoneIndex, prevMask, prevSpatial });
    // Trim stack if too large
    if (undoStack.length > MAX_UNDO) undoStack.shift();
}

function undoDrawStroke() {
    if (undoStack.length === 0) {
        showToast('Nothing to undo');
        return;
    }
    const entry = undoStack.pop();
    const zone = zones[entry.zoneIndex];
    if (!zone) return;
    zone.regionMask = entry.prevMask;
    zone.spatialMask = entry.prevSpatial;
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Undo: reverted Zone ${entry.zoneIndex + 1} actions`);
}

// ===== MAGIC WAND / FLOOD FILL =====
function magicWandFill(startX, startY, tolerance, addToExisting) {
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    if (!paintImageData) {
        showToast('Load a paint image first!');
        return;
    }

    const canvas = document.getElementById('paintCanvas');
    const w = canvas.width;
    const h = canvas.height;
    const data = paintImageData.data; // RGBA pixel data

    // Initialize zone mask if needed
    if (!zone.regionMask) {
        zone.regionMask = new Uint8Array(w * h);
    } else if (!addToExisting) {
        // If not shift+click, replace existing mask
        zone.regionMask = new Uint8Array(w * h);
    }

    // Get seed color
    const seedIdx = (startY * w + startX) * 4;
    const seedR = data[seedIdx];
    const seedG = data[seedIdx + 1];
    const seedB = data[seedIdx + 2];

    // Visited array to avoid revisiting
    const visited = new Uint8Array(w * h);

    // Color distance function (Photoshop Chebyshev Distance)
    function colorMatch(idx) {
        const pi = idx * 4;
        const rDiff = Math.abs(data[pi] - seedR);
        const gDiff = Math.abs(data[pi + 1] - seedG);
        const bDiff = Math.abs(data[pi + 2] - seedB);

        // Chebyshev distance matches exactly how Photoshop's tolerance slider works
        return Math.max(rDiff, gDiff, bDiff) <= tolerance;
    }

    // Stack-based flood fill using 8-connectivity (cardinal + diagonal)
    // 8-connectivity prevents leaking through 1px diagonal gaps (PS behavior)
    let filled = 0;
    const seedPos = startY * w + startX;
    if (!colorMatch(seedPos)) {
        showToast('Clicked pixel doesn\'t match - try a different spot or increase tolerance');
        return;
    }

    const stack = [seedPos];
    visited[seedPos] = 1;

    while (stack.length > 0) {
        const pos = stack.pop();
        zone.regionMask[pos] = 1;
        filled++;

        const px = pos % w;
        const py = (pos - px) / w;

        // 8 neighbors: cardinal + diagonal
        const neighbors = [];
        if (px > 0) neighbors.push(pos - 1);                         // Left
        if (px < w - 1) neighbors.push(pos + 1);                     // Right
        if (py > 0) neighbors.push(pos - w);                         // Up
        if (py < h - 1) neighbors.push(pos + w);                     // Down
        if (px > 0 && py > 0) neighbors.push(pos - w - 1);           // Top-Left
        if (px < w - 1 && py > 0) neighbors.push(pos - w + 1);       // Top-Right
        if (px > 0 && py < h - 1) neighbors.push(pos + w - 1);       // Bottom-Left
        if (px < w - 1 && py < h - 1) neighbors.push(pos + w + 1);   // Bottom-Right

        for (const npos of neighbors) {
            if (!visited[npos] && colorMatch(npos)) {
                visited[npos] = 1;
                stack.push(npos);
            }
        }
    }

    // Post-fill constrained 1px dilation - captures anti-aliased edge pixels that
    // are blended between the target color and surrounding outlines, but STOPS at
    // dramatically different colors (white, black, blue). Only expands into pixels
    // whose max per-channel diff from the seed is within 5x the tolerance.
    const dilThreshold = tolerance * 5; // generous enough to catch blended anti-aliased edges
    const dilated = new Uint8Array(zone.regionMask);

    function dilatePixel(npos) {
        if (dilated[npos]) return; // already selected
        const pi = npos * 4;
        const rDiff = Math.abs(data[pi] - seedR);
        const gDiff = Math.abs(data[pi + 1] - seedG);
        const bDiff = Math.abs(data[pi + 2] - seedB);
        if (Math.max(rDiff, gDiff, bDiff) <= dilThreshold) {
            dilated[npos] = 1;
            filled++;
        }
    }

    for (let pos = 0; pos < w * h; pos++) {
        if (zone.regionMask[pos] !== 1) continue;
        const px = pos % w;
        const py = (pos - px) / w;
        if (px > 0) dilatePixel(pos - 1);
        if (px < w - 1) dilatePixel(pos + 1);
        if (py > 0) dilatePixel(pos - w);
        if (py < h - 1) dilatePixel(pos + w);
        if (px > 0 && py > 0) dilatePixel(pos - w - 1);
        if (px < w - 1 && py > 0) dilatePixel(pos - w + 1);
        if (px > 0 && py < h - 1) dilatePixel(pos + w - 1);
        if (px < w - 1 && py < h - 1) dilatePixel(pos + w + 1);
    }
    zone.regionMask = dilated;

    showToast(`Magic Wand: selected ${filled.toLocaleString()} pixels (Shift=add, Alt=subtract)`);
}

// ===== SUBTRACT WAND SELECTION - Alt+click removes matching pixels =====
function subtractWandSelection(startX, startY, tolerance, contiguous) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !paintImageData) { showToast('Load a paint image first!'); return; }
    if (!zone.regionMask) { showToast('No selection to subtract from'); return; }
    const canvas = document.getElementById('paintCanvas');
    const w = canvas.width, h = canvas.height;
    const data = paintImageData.data;

    const seedIdx = (startY * w + startX) * 4;
    const seedR = data[seedIdx], seedG = data[seedIdx + 1], seedB = data[seedIdx + 2];
    let removed = 0;

    function colorMatch(idx) {
        const pi = idx * 4;
        const rDiff = Math.abs(data[pi] - seedR);
        const gDiff = Math.abs(data[pi + 1] - seedG);
        const bDiff = Math.abs(data[pi + 2] - seedB);
        return Math.max(rDiff, gDiff, bDiff) <= tolerance;
    }

    if (contiguous) {
        // Flood fill subtract - only remove connected matching pixels
        const visited = new Uint8Array(w * h);
        const seedPos = startY * w + startX;
        if (!colorMatch(seedPos)) { showToast('Clicked pixel doesn\'t match'); return; }
        const stack = [seedPos];
        visited[seedPos] = 1;
        while (stack.length > 0) {
            const pos = stack.pop();
            if (zone.regionMask[pos] > 0) { zone.regionMask[pos] = 0; removed++; }
            const px = pos % w, py = (pos - px) / w;
            const neighbors = [];
            if (px > 0) neighbors.push(pos - 1);
            if (px < w - 1) neighbors.push(pos + 1);
            if (py > 0) neighbors.push(pos - w);
            if (py < h - 1) neighbors.push(pos + w);
            if (px > 0 && py > 0) neighbors.push(pos - w - 1);
            if (px < w - 1 && py > 0) neighbors.push(pos - w + 1);
            if (px > 0 && py < h - 1) neighbors.push(pos + w - 1);
            if (px < w - 1 && py < h - 1) neighbors.push(pos + w + 1);
            for (const npos of neighbors) {
                if (!visited[npos] && colorMatch(npos)) { visited[npos] = 1; stack.push(npos); }
            }
        }
    } else {
        // Global subtract - remove ALL matching pixels
        for (let i = 0; i < w * h; i++) {
            if (zone.regionMask[i] > 0 && colorMatch(i)) { zone.regionMask[i] = 0; removed++; }
        }
    }
    showToast(`Subtracted ${removed.toLocaleString()} pixels from selection`);
}

// Select ALL pixels of clicked color everywhere (not just connected)
function selectAllColor(startX, startY, tolerance, addToExisting) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !paintImageData) { showToast('Load a paint image first!'); return; }
    const canvas = document.getElementById('paintCanvas');
    const w = canvas.width, h = canvas.height;
    const data = paintImageData.data;

    if (!zone.regionMask || !addToExisting) zone.regionMask = new Uint8Array(w * h);

    const seedIdx = (startY * w + startX) * 4;
    const seedR = data[seedIdx], seedG = data[seedIdx + 1], seedB = data[seedIdx + 2];
    let filled = 0;

    for (let i = 0; i < w * h; i++) {
        const pi = i * 4;
        const rDiff = Math.abs(data[pi] - seedR);
        const gDiff = Math.abs(data[pi + 1] - seedG);
        const bDiff = Math.abs(data[pi + 2] - seedB);

        if (Math.max(rDiff, gDiff, bDiff) <= tolerance) {
            zone.regionMask[i] = 1;
            filled++;
        }
    }
    showToast(`Select All Color: ${filled.toLocaleString()} pixels (Shift+click to add more)`);
}

// Edge-aware flood fill - stops at hard color boundaries
function edgeDetectFill(startX, startY, tolerance, addToExisting) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !paintImageData) { showToast('Load a paint image first!'); return; }
    const canvas = document.getElementById('paintCanvas');
    const w = canvas.width, h = canvas.height;
    const data = paintImageData.data;

    if (!zone.regionMask || !addToExisting) zone.regionMask = new Uint8Array(w * h);

    // Build edge map using Sobel-like gradient magnitude
    // Precompute gradient magnitude for every pixel
    const edgeThreshold = tolerance * 1.5; // Edge detection uses tolerance as sensitivity
    const visited = new Uint8Array(w * h);
    let filled = 0;

    function getGray(x, y) {
        if (x < 0 || x >= w || y < 0 || y >= h) return 0;
        const pi = (y * w + x) * 4;
        return data[pi] * 0.299 + data[pi + 1] * 0.587 + data[pi + 2] * 0.114;
    }

    function isEdge(x, y) {
        // Sobel gradient magnitude
        const gx = -getGray(x - 1, y - 1) - 2 * getGray(x - 1, y) - getGray(x - 1, y + 1)
            + getGray(x + 1, y - 1) + 2 * getGray(x + 1, y) + getGray(x + 1, y + 1);
        const gy = -getGray(x - 1, y - 1) - 2 * getGray(x, y - 1) - getGray(x + 1, y - 1)
            + getGray(x - 1, y + 1) + 2 * getGray(x, y + 1) + getGray(x + 1, y + 1);
        return Math.sqrt(gx * gx + gy * gy) > edgeThreshold;
    }

    // Flood fill stopping at edges
    const seedPos = startY * w + startX;
    if (isEdge(startX, startY)) {
        showToast('Clicked on an edge - try clicking inside a region');
        return;
    }

    const stack = [seedPos];
    visited[seedPos] = 1;

    while (stack.length > 0) {
        const pos = stack.pop();
        zone.regionMask[pos] = 1;
        filled++;

        const px = pos % w;
        const py = (pos - px) / w;

        const neighbors = [];
        if (px > 0) neighbors.push(pos - 1);
        if (px < w - 1) neighbors.push(pos + 1);
        if (py > 0) neighbors.push(pos - w);
        if (py < h - 1) neighbors.push(pos + w);

        for (const npos of neighbors) {
            if (visited[npos]) continue;
            visited[npos] = 1;
            const nx = npos % w;
            const ny = (npos - nx) / w;
            if (!isEdge(nx, ny)) {
                stack.push(npos);
            }
        }
    }
    showToast(`Edge Fill: ${filled.toLocaleString()} pixels (bounded by edges, Shift+click to add)`);
}

// ===== EDGE DETECTION PREVIEW OVERLAY =====
let edgePreviewActive = false;
let edgePreviewImageData = null;  // cached edge map ImageData for overlay

function toggleEdgePreview() {
    edgePreviewActive = !edgePreviewActive;
    const btn = document.getElementById('edgePreviewBtn');
    if (edgePreviewActive) {
        btn.style.background = 'var(--accent-gold)';
        btn.style.color = '#111';
        computeEdgePreview();
    } else {
        btn.style.background = '';
        btn.style.color = 'var(--accent-gold)';
        clearEdgePreviewOverlay();
    }
}

function computeEdgePreview() {
    if (!paintImageData) return;
    const canvas = document.getElementById('paintCanvas');
    const w = canvas.width, h = canvas.height;
    const data = paintImageData.data;
    const tolerance = parseInt(document.getElementById('wandTolerance').value) || 32;
    const edgeThreshold = tolerance * 1.5;

    // Compute Sobel edge map
    function getGray(x, y) {
        if (x < 0 || x >= w || y < 0 || y >= h) return 0;
        const pi = (y * w + x) * 4;
        return data[pi] * 0.299 + data[pi + 1] * 0.587 + data[pi + 2] * 0.114;
    }

    // Create overlay ImageData (RGBA)
    const overlay = new ImageData(w, h);
    const od = overlay.data;

    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            const gx = -getGray(x - 1, y - 1) - 2 * getGray(x - 1, y) - getGray(x - 1, y + 1)
                + getGray(x + 1, y - 1) + 2 * getGray(x + 1, y) + getGray(x + 1, y + 1);
            const gy = -getGray(x - 1, y - 1) - 2 * getGray(x, y - 1) - getGray(x + 1, y - 1)
                + getGray(x - 1, y + 1) + 2 * getGray(x, y + 1) + getGray(x + 1, y + 1);
            const mag = Math.sqrt(gx * gx + gy * gy);

            if (mag > edgeThreshold) {
                const pi = (y * w + x) * 4;
                // Red with intensity based on edge strength (brighter = stronger edge)
                const intensity = Math.min(255, Math.floor(mag * 2));
                od[pi] = 255;         // R
                od[pi + 1] = 40;      // G (slight warmth)
                od[pi + 2] = 40;      // B
                od[pi + 3] = Math.min(200, intensity);  // A
            }
        }
    }
    edgePreviewImageData = overlay;
    renderEdgePreviewOverlay();
}

function renderEdgePreviewOverlay() {
    if (!edgePreviewImageData) return;
    // Use a dedicated canvas layer for edge preview
    let edgeCanvas = document.getElementById('edgePreviewCanvas');
    if (!edgeCanvas) {
        edgeCanvas = document.createElement('canvas');
        edgeCanvas.id = 'edgePreviewCanvas';
        edgeCanvas.style.cssText = 'position:absolute; top:0; left:0; pointer-events:none; z-index:15; image-rendering:pixelated;';
        const viewport = document.getElementById('canvasViewport');
        if (viewport) viewport.appendChild(edgeCanvas);
    }
    const paintCanvas = document.getElementById('paintCanvas');
    edgeCanvas.width = paintCanvas.width;
    edgeCanvas.height = paintCanvas.height;
    edgeCanvas.style.width = paintCanvas.style.width;
    edgeCanvas.style.height = paintCanvas.style.height;
    edgeCanvas.style.transform = paintCanvas.style.transform || '';
    // Match paint canvas position
    edgeCanvas.style.transformOrigin = paintCanvas.style.transformOrigin || '';

    const ctx = edgeCanvas.getContext('2d');
    ctx.clearRect(0, 0, edgeCanvas.width, edgeCanvas.height);
    ctx.putImageData(edgePreviewImageData, 0, 0);
}

function clearEdgePreviewOverlay() {
    edgePreviewImageData = null;
    const edgeCanvas = document.getElementById('edgePreviewCanvas');
    if (edgeCanvas) {
        const ctx = edgeCanvas.getContext('2d');
        ctx.clearRect(0, 0, edgeCanvas.width, edgeCanvas.height);
    }
}

// Hook into tolerance slider to update edge preview live
(function () {
    const tolSlider = document.getElementById('wandTolerance');
    if (tolSlider) {
        const origOninput = tolSlider.oninput;
        tolSlider.addEventListener('input', function () {
            if (edgePreviewActive) {
                // Debounce: delay recompute slightly
                clearTimeout(tolSlider._edgePreviewTimer);
                tolSlider._edgePreviewTimer = setTimeout(computeEdgePreview, 80);
            }
        });
    }
})();

function clearZoneRegions(zoneIndex) {
    if (zones[zoneIndex]) {
        pushUndo(zoneIndex); // Save state before clearing
        zones[zoneIndex].regionMask = null;
        renderRegionOverlay();
        triggerPreviewRender();
        showToast(`Cleared drawn regions for ${zones[zoneIndex].name}`);
    }
}

function clearAllRegions() {
    zones.forEach(z => z.regionMask = null);
    renderRegionOverlay();
    showToast('Cleared all drawn regions');
}

// ===== SPATIAL MASK - Include/Exclude refinement for color-based zones =====
// spatialMask is a Uint8Array: 0=unset, 1=include(green), 2=exclude(red)
// Unlike regionMask which REPLACES color detection, spatialMask REFINES it.

function pushSpatialUndo(zoneIndex) {
    pushUndo(zoneIndex); // Forward to unified undo
}

function undoSpatialStroke() {
    undoDrawStroke(); // Forward to unified undo
}

function paintSpatialCircle(cx, cy, radius, value) {
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;

    // Initialize mask if needed
    if (!zone.spatialMask) {
        zone.spatialMask = new Uint8Array(w * h);
    }

    // Paint circle
    const r2 = radius * radius;
    const x0 = Math.max(0, Math.floor(cx - radius));
    const x1 = Math.min(w - 1, Math.ceil(cx + radius));
    const y0 = Math.max(0, Math.floor(cy - radius));
    const y1 = Math.min(h - 1, Math.ceil(cy + radius));
    for (let y = y0; y <= y1; y++) {
        for (let x = x0; x <= x1; x++) {
            if ((x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2) {
                zone.spatialMask[y * w + x] = value;
            }
        }
    }
}

function clearSpatialMask(zoneIndex) {
    const zone = zones[zoneIndex];
    if (!zone) return;
    pushSpatialUndo(zoneIndex);
    zone.spatialMask = null;
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Cleared spatial mask for ${zone.name}`);
}

function eraseSpatialCircle(cx, cy, radius) {
    // Erase = set to 0 (unset)
    paintSpatialCircle(cx, cy, radius, 0);
}

function toggleSpatialMode(mode) {
    // mode: 'include', 'exclude', 'erase-spatial', 'off'
    const cvs = document.getElementById('paintCanvas');
    if (mode === 'include') {
        canvasMode = 'spatial-include';
        if (cvs) cvs.style.cursor = 'crosshair';
        showToast('Spatial Include: paint areas to KEEP in this zone (green)');
    } else if (mode === 'exclude') {
        canvasMode = 'spatial-exclude';
        if (cvs) cvs.style.cursor = 'crosshair';
        showToast('Spatial Exclude: paint areas to REMOVE from this zone (red)');
    } else if (mode === 'erase-spatial') {
        canvasMode = 'spatial-include'; // reuse include but with value=0
        // We'll handle erase by checking dedicated button state
        if (cvs) cvs.style.cursor = 'crosshair';
        showToast('Spatial Eraser: clear include/exclude marks');
    } else {
        canvasMode = 'eyedropper';
        if (cvs) cvs.style.cursor = 'crosshair';
    }
    renderZoneDetail(selectedZoneIndex);
}

function hasSpatialMask(zone) {
    return zone && zone.spatialMask && zone.spatialMask.some(v => v > 0);
}

// ===== ADVANCED MASK OPERATIONS =====

// --- INVERT SELECTION --- flip 0↔1 in regionMask
function invertRegionMask() {
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;
    pushUndo(selectedZoneIndex);
    if (!zone.regionMask) {
        // Invert empty → fill everything
        zone.regionMask = new Uint8Array(w * h).fill(1);
    } else {
        for (let i = 0; i < zone.regionMask.length; i++) {
            zone.regionMask[i] = zone.regionMask[i] > 0 ? 0 : 1;
        }
    }
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Inverted selection for Zone ${selectedZoneIndex + 1}`);
}

// --- GROW SELECTION --- fast BFS morphological dilation
// Instead of checking every pixel against every neighbor, we do N iterations
// of single-pixel dilation from the boundary - O(boundary × n) vs O(w×h×n²)
function growRegionMask(px) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region to grow - draw one first'); return; }
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;
    const n = px || 2;
    pushUndo(selectedZoneIndex);
    const mask = zone.regionMask;

    for (let iter = 0; iter < n; iter++) {
        // Collect current boundary pixels (filled pixels adjacent to empty)
        const boundary = [];
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const idx = y * w + x;
                if (mask[idx] > 0) continue; // already filled
                // Check 8 neighbors for any filled pixel
                let adj = false;
                if (x > 0 && mask[idx - 1] > 0) adj = true;
                else if (x < w - 1 && mask[idx + 1] > 0) adj = true;
                else if (y > 0 && mask[idx - w] > 0) adj = true;
                else if (y < h - 1 && mask[idx + w] > 0) adj = true;
                else if (x > 0 && y > 0 && mask[idx - w - 1] > 0) adj = true;
                else if (x < w - 1 && y > 0 && mask[idx - w + 1] > 0) adj = true;
                else if (x > 0 && y < h - 1 && mask[idx + w - 1] > 0) adj = true;
                else if (x < w - 1 && y < h - 1 && mask[idx + w + 1] > 0) adj = true;
                if (adj) boundary.push(idx);
            }
        }
        // Expand: fill all boundary pixels
        for (const idx of boundary) mask[idx] = 1;
        if (boundary.length === 0) break; // nothing left to grow
    }
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Grew selection by ${n}px`);
}

// --- SHRINK SELECTION --- fast BFS morphological erosion
// N iterations of single-pixel erosion from the boundary
function shrinkRegionMask(px) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region to shrink'); return; }
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;
    const n = px || 2;
    pushUndo(selectedZoneIndex);
    const mask = zone.regionMask;

    for (let iter = 0; iter < n; iter++) {
        // Collect edge pixels (filled pixels adjacent to empty or image border)
        const edgePixels = [];
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const idx = y * w + x;
                if (mask[idx] === 0) continue; // already empty
                // Check if on image border or adjacent to empty pixel
                let onEdge = (x === 0 || x === w - 1 || y === 0 || y === h - 1);
                if (!onEdge) {
                    if (mask[idx - 1] === 0 || mask[idx + 1] === 0 ||
                        mask[idx - w] === 0 || mask[idx + w] === 0 ||
                        mask[idx - w - 1] === 0 || mask[idx - w + 1] === 0 ||
                        mask[idx + w - 1] === 0 || mask[idx + w + 1] === 0) {
                        onEdge = true;
                    }
                }
                if (onEdge) edgePixels.push(idx);
            }
        }
        // Erode: clear all edge pixels
        for (const idx of edgePixels) mask[idx] = 0;
        if (edgePixels.length === 0) break; // nothing left to shrink
    }
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Shrunk selection by ${n}px`);
}

// --- FILL HOLES --- flood fill from edges to find enclosed gaps
function fillRegionHoles() {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region to fill holes in'); return; }
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;
    pushUndo(selectedZoneIndex);

    // Flood fill from all edge-touching empty pixels
    const visited = new Uint8Array(w * h);
    const stack = [];
    // Seed from all 4 edges
    for (let x = 0; x < w; x++) {
        if (zone.regionMask[x] === 0 && !visited[x]) { stack.push(x); visited[x] = 1; }
        const bot = (h - 1) * w + x;
        if (zone.regionMask[bot] === 0 && !visited[bot]) { stack.push(bot); visited[bot] = 1; }
    }
    for (let y = 0; y < h; y++) {
        const left = y * w;
        if (zone.regionMask[left] === 0 && !visited[left]) { stack.push(left); visited[left] = 1; }
        const right = y * w + w - 1;
        if (zone.regionMask[right] === 0 && !visited[right]) { stack.push(right); visited[right] = 1; }
    }
    // BFS flood
    while (stack.length > 0) {
        const pos = stack.pop();
        const px = pos % w, py = Math.floor(pos / w);
        const neighbors = [];
        if (px > 0) neighbors.push(pos - 1);
        if (px < w - 1) neighbors.push(pos + 1);
        if (py > 0) neighbors.push(pos - w);
        if (py < h - 1) neighbors.push(pos + w);
        for (const nb of neighbors) {
            if (!visited[nb] && zone.regionMask[nb] === 0) {
                visited[nb] = 1;
                stack.push(nb);
            }
        }
    }
    // Any unvisited empty pixel is an enclosed hole → fill it
    let filled = 0;
    for (let i = 0; i < w * h; i++) {
        if (zone.regionMask[i] === 0 && !visited[i]) {
            zone.regionMask[i] = 1;
            filled++;
        }
    }
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Filled ${filled.toLocaleString()} hole pixels`);
}

// --- COPY MASK BETWEEN ZONES ---
function toggleCopyMaskDropdown(e) {
    if (e) e.stopPropagation();
    const dd = document.getElementById('copyMaskDropdown');
    if (!dd) return;
    if (dd.style.display !== 'none') { dd.style.display = 'none'; return; }
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region mask to copy'); return; }
    // Build dropdown items
    let html = '';
    zones.forEach((z, i) => {
        if (i === selectedZoneIndex) return;
        const color = ZONE_OVERLAY_COLORS[i % ZONE_OVERLAY_COLORS.length];
        const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:rgb(${color[0]},${color[1]},${color[2]});margin-right:5px;vertical-align:middle;"></span>`;
        html += `<div onclick="copyMaskToZone(${i}); document.getElementById('copyMaskDropdown').style.display='none';" 
                    style="padding:4px 10px; cursor:pointer; font-size:10px; color:var(--text); white-space:nowrap; transition:background 0.15s;"
                    onmouseenter="this.style.background='var(--accent-blue-dim)'" 
                    onmouseleave="this.style.background='transparent'">
                    ${dot}Zone ${i + 1}: ${z.name}
                </div>`;
    });
    if (!html) html = '<div style="padding:6px 10px; font-size:10px; color:var(--text-dim);">No other zones</div>';
    dd.innerHTML = html;
    dd.style.display = 'block';
    // Close on outside click
    setTimeout(() => {
        function closeDd(ev) { if (!dd.contains(ev.target)) { dd.style.display = 'none'; document.removeEventListener('mousedown', closeDd); } }
        document.addEventListener('mousedown', closeDd);
    }, 10);
}

function copyMaskToZone(targetIndex) {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region mask to copy'); return; }
    if (targetIndex == null || targetIndex < 0 || targetIndex >= zones.length || targetIndex === selectedZoneIndex) {
        showToast('Invalid zone number'); return;
    }
    pushUndo(targetIndex);
    zones[targetIndex].regionMask = new Uint8Array(zone.regionMask);
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Copied mask from Zone ${selectedZoneIndex + 1} → Zone ${targetIndex + 1}`);
}

// --- MIRROR/FLIP MASK --- horizontal flip
function mirrorRegionMask() {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region to mirror'); return; }
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;
    pushUndo(selectedZoneIndex);
    for (let y = 0; y < h; y++) {
        const row = y * w;
        for (let x = 0; x < Math.floor(w / 2); x++) {
            const left = row + x;
            const right = row + w - 1 - x;
            const tmp = zone.regionMask[left];
            zone.regionMask[left] = zone.regionMask[right];
            zone.regionMask[right] = tmp;
        }
    }
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Mirrored region mask horizontally for Zone ${selectedZoneIndex + 1}`);
}

// --- OVERLAY OPACITY --- adjustable zone overlay transparency
let overlayOpacityMultiplier = 1.0; // 0.0 - 2.0 range, 1.0 = default

function setOverlayOpacity(val) {
    overlayOpacityMultiplier = parseFloat(val);
    _doRenderRegionOverlay();
    document.getElementById('overlayOpacityVal').textContent = Math.round(val * 50) + '%';
}

// --- ZOOM TO SELECTION --- auto-zoom to fit mask bounding box
function zoomToSelection() {
    const zone = zones[selectedZoneIndex];
    if (!zone || !zone.regionMask) { showToast('No region to zoom to'); return; }
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;

    // Find bounding box
    let minX = w, maxX = 0, minY = h, maxY = 0;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            if (zone.regionMask[y * w + x] > 0) {
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }
    }
    if (maxX < minX) { showToast('Selection is empty'); return; }

    // Calculate required zoom to fit bounding box in viewport
    const viewport = document.getElementById('canvasViewport');
    if (!viewport) return;
    const vpW = viewport.clientWidth - 40;
    const vpH = viewport.clientHeight - 40;
    const selW = maxX - minX + 1;
    const selH = maxY - minY + 1;
    const zoomX = vpW / selW;
    const zoomY = vpH / selH;
    const targetZoom = Math.min(zoomX, zoomY, 8.0); // Cap at 8x

    // Apply zoom
    currentZoom = Math.max(0.1, targetZoom);
    applyZoom();

    // Scroll to center of selection
    setTimeout(() => {
        const sc = getScrollContainer();
        if (!sc) return;
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        sc.scrollLeft = centerX * currentZoom - vpW / 2;
        sc.scrollTop = centerY * currentZoom - vpH / 2;
    }, 50);

    showToast(`Zoomed to selection (${selW}×${selH}px)`);
}

// --- LASSO / POLYGON SELECT --- click vertices, fill inside on close
let lassoPoints = [];
let lassoActive = false;

function startLasso() {
    lassoPoints = [];
    lassoActive = true;
}

function addLassoPoint(x, y) {
    lassoPoints.push({ x, y });
    drawLassoPreview();
}

function closeLasso(e) {
    if (lassoPoints.length < 3) {
        showToast('Need at least 3 points for polygon selection');
        lassoActive = false;
        lassoPoints = [];
        return;
    }
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const w = canvas.width, h = canvas.height;
    pushUndo(selectedZoneIndex);

    const selMode = document.getElementById('selectionMode')?.value || 'add';
    const eShift = e?.shiftKey || false;
    const eAlt = e?.altKey || false;
    let replaceMode = selMode === 'replace' && !eShift && !eAlt;
    let subtractMode = selMode === 'subtract' || eAlt;

    if (!zone.regionMask || replaceMode) {
        zone.regionMask = new Uint8Array(w * h);
    }

    const fillVal = subtractMode ? 0 : 1;

    // Fill polygon using scanline approach
    // Find bounding box
    let minX = w, maxX = 0, minY = h, maxY = 0;
    for (const p of lassoPoints) {
        if (p.x < minX) minX = Math.floor(p.x);
        if (p.x > maxX) maxX = Math.ceil(p.x);
        if (p.y < minY) minY = Math.floor(p.y);
        if (p.y > maxY) maxY = Math.ceil(p.y);
    }
    minX = Math.max(0, minX); maxX = Math.min(w - 1, maxX);
    minY = Math.max(0, minY); maxY = Math.min(h - 1, maxY);

    // Point-in-polygon test (ray casting)
    const pts = lassoPoints;
    const n = pts.length;
    let filled = 0;
    for (let y = minY; y <= maxY; y++) {
        for (let x = minX; x <= maxX; x++) {
            let inside = false;
            for (let i = 0, j = n - 1; i < n; j = i++) {
                const xi = pts[i].x, yi = pts[i].y;
                const xj = pts[j].x, yj = pts[j].y;
                if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
                    inside = !inside;
                }
            }
            if (inside) {
                zone.regionMask[y * w + x] = fillVal;
                filled++;
            }
        }
    }

    lassoActive = false;
    lassoPoints = [];
    hideLassoPreview();
    renderRegionOverlay();
    triggerPreviewRender();
    showToast(`Lasso: filled ${filled.toLocaleString()} pixels`);
}

function drawLassoPreview() {
    const canvas = document.getElementById('paintCanvas');
    const regionCanvas = document.getElementById('regionCanvas');
    if (!canvas || !regionCanvas) return;
    // Draw lasso preview lines on region canvas overlay
    _doRenderRegionOverlay(); // Full redraw since we overlay on top
    if (lassoPoints.length < 2) return;
    const ctx = regionCanvas.getContext('2d');
    ctx.save();
    ctx.strokeStyle = 'rgba(255,255,0,0.9)';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(lassoPoints[0].x, lassoPoints[0].y);
    for (let i = 1; i < lassoPoints.length; i++) {
        ctx.lineTo(lassoPoints[i].x, lassoPoints[i].y);
    }
    ctx.stroke();
    // Draw vertices
    ctx.fillStyle = 'rgba(255,255,0,1)';
    for (const p of lassoPoints) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.fill();
    }
    // Draw closing line (dashed) from last point to first
    if (lassoPoints.length >= 3) {
        ctx.strokeStyle = 'rgba(255,255,0,0.4)';
        ctx.beginPath();
        ctx.moveTo(lassoPoints[lassoPoints.length - 1].x, lassoPoints[lassoPoints.length - 1].y);
        ctx.lineTo(lassoPoints[0].x, lassoPoints[0].y);
        ctx.stroke();
    }
    ctx.restore();
}

function hideLassoPreview() {
    _doRenderRegionOverlay();
}

function undoLassoPoint() {
    if (lassoPoints.length > 0) {
        lassoPoints.pop();
        drawLassoPreview();
        showToast(`Lasso: ${lassoPoints.length} points (right-click to undo last)`);
    }
}

function loadPaintImage(input) {
    const file = input.files[0];
    if (!file) return;
    const fileName = file.name;

    if (fileName.toLowerCase().endsWith('.tga')) {
        // TGA: decode with our custom decoder
        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                const tga = decodeTGA(e.target.result);
                loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);
            } catch (err) {
                showToast(`TGA decode error: ${err.message}`, true);
            }
        };
        reader.readAsArrayBuffer(file);
    } else {
        // PNG/JPG/BMP: browser-native decode
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = new Image();
            img.onload = function () {
                const canvas = document.getElementById('paintCanvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                // Also size region canvas
                const regionCanvas = document.getElementById('regionCanvas');
                regionCanvas.width = img.width;
                regionCanvas.height = img.height;

                // Show/hide elements for new 3-column layout
                const emptyBig = document.getElementById('paintPreviewEmptyBig');
                if (emptyBig) emptyBig.style.display = 'none';
                const empty2 = document.getElementById('paintPreviewEmpty2');
                if (empty2) empty2.style.display = 'none';
                document.getElementById('paintPreviewLoaded').style.display = 'flex';
                const advBar4 = document.getElementById('advancedToolbar'); if (advBar4) advBar4.style.display = 'flex';
                const edInfo4 = document.getElementById('eyedropperInfo'); if (edInfo4) edInfo4.style.display = 'block';
                document.getElementById('paintDimensions').textContent = `${img.width}x${img.height}`;
                document.getElementById('paintPreviewStatus').textContent = `(${img.width}x${img.height})`;
                const canvasInner = document.getElementById('canvasInner');
                if (canvasInner) canvasInner.style.display = 'block';
                const zoomCtrl = document.getElementById('zoomControls');
                if (zoomCtrl) zoomCtrl.style.display = 'flex';

                setupCanvasHandlers(canvas);
                canvasZoom('fit');
                showToast('Paint loaded! Hover to see colors, click to grab one.');
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

function updateEyedropperZoneSelect() {
    const sel = document.getElementById('eyedropperZoneSelect');
    if (!sel) return;
    sel.innerHTML = zones.map((z, i) =>
        `<option value="${i}"${i === selectedZoneIndex ? ' selected' : ''}>Zone ${i + 1}: ${escapeHtml(z.name)}</option>`
    ).join('');

    // Populate base + pattern dropdowns if not yet done
    const baseSel = document.getElementById('eyedropperBaseSelect');
    if (baseSel && baseSel.options.length <= 1) {
        let html = '<option value="">- Base -</option>';
        BASES.forEach(b => { html += `<option value="${b.id}">${b.name}</option>`; });
        html += '<optgroup label="Special">';
        MONOLITHICS.forEach(m => { html += `<option value="mono:${m.id}">${m.name}</option>`; });
        html += '</optgroup>';
        baseSel.innerHTML = html;
    }
    const patSel = document.getElementById('eyedropperPatternSelect');
    if (patSel && patSel.options.length <= 1) {
        let html = '';
        PATTERNS.forEach(p => { html += `<option value="${p.id}">${p.name}</option>`; });
        patSel.innerHTML = html;
    }

    // ALWAYS sync dropdowns with the selected zone's current values
    syncEyedropperPanel();
}

function syncEyedropperPanel() {
    // Sync the bottom-bar dropdowns with the currently selected zone
    const sel = document.getElementById('eyedropperZoneSelect');
    const baseSel = document.getElementById('eyedropperBaseSelect');
    const patSel = document.getElementById('eyedropperPatternSelect');
    const intSel = document.getElementById('eyedropperIntensitySelect');

    if (sel) sel.value = String(selectedZoneIndex);

    const zone = zones[selectedZoneIndex];
    if (!zone) return;

    // Sync base dropdown (monolithics get "mono:" prefix)
    if (baseSel) {
        if (zone.finish && MONOLITHICS.find(m => m.id === zone.finish)) {
            baseSel.value = 'mono:' + zone.finish;
        } else {
            baseSel.value = zone.base || '';
        }
    }

    // Sync pattern dropdown (now works for BOTH bases AND monolithics - patterns overlay on top!)
    if (patSel) {
        patSel.value = zone.pattern || 'none';
        patSel.disabled = false;  // Patterns can now overlay on monolithics too
    }

    // Sync intensity dropdown
    if (intSel) intSel.value = zone.intensity || '100';
}

function onEyedropperZoneChange(val) {
    // When user picks a different zone in the RIGHT panel dropdown
    const newIndex = parseInt(val);
    if (newIndex >= 0 && newIndex < zones.length) {
        selectedZoneIndex = newIndex;
        renderZones();
        syncEyedropperPanel();
        if (canvasMode !== 'eyedropper') {
            updateDrawZoneIndicator();
        }
    }
}

function onEyedropperBaseChange(val) {
    // When user picks a base (or monolithic) in the bottom bar → apply to selected zone
    const zone = zones[selectedZoneIndex];
    if (!zone || !val) return;
    pushZoneUndo();
    if (val.startsWith('mono:')) {
        const monoId = val.replace('mono:', '');
        zone.finish = monoId;
        zone.base = null;
        zone.pattern = null;
        showToast(`${zone.name}: ${MONOLITHICS.find(m => m.id === monoId)?.name || monoId}`);
    } else {
        zone.base = val;
        zone.finish = null;
        if (!zone.pattern) zone.pattern = 'none';
        showToast(`${zone.name}: base set to ${BASES.find(b => b.id === val)?.name || val}`);
    }
    renderZones();
    syncEyedropperPanel();
}

function onEyedropperPatternChange(val) {
    const zone = zones[selectedZoneIndex];
    if (!zone) return;
    pushZoneUndo();
    zone.pattern = val || 'none';
    if (!zone.base) zone.base = 'gloss'; // Need a base for pattern to work
    zone.finish = null;
    renderZones();
    syncEyedropperPanel();
    const patName = PATTERNS.find(p => p.id === val)?.name || val;
    showToast(`${zone.name}: pattern set to ${patName}`);
}

function onEyedropperIntensityChange(val) {
    // When user picks intensity in the RIGHT panel → immediately apply to selected zone on LEFT
    const zone = zones[selectedZoneIndex];
    if (zone && val) {
        pushZoneUndo();
        zone.intensity = val;
        renderZones();
        showToast(`${zone.name}: intensity set to ${val}`);
    }
}

function quickAssignAll() {
    // Assign color + finish + intensity to the selected zone all at once from the right panel
    pushZoneUndo();
    const sel = document.getElementById('eyedropperZoneSelect');
    const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;
    if (targetIndex < 0 || targetIndex >= zones.length) return;

    const zone = zones[targetIndex];
    const finishSel = document.getElementById('eyedropperFinishSelect');
    const intSel = document.getElementById('eyedropperIntensitySelect');

    // Set color if eyedropper has one
    if (lastEyedropperColor) {
        const { r, g, b } = lastEyedropperColor;
        const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
        const tol = zone.pickerTolerance || 40;
        zone.color = { color_rgb: [r, g, b], tolerance: tol };
        zone.colorMode = 'picker';
        zone.pickerColor = hex;
        zone.colors = [];
    }

    // Set base + pattern from bottom bar dropdowns
    const baseSel = document.getElementById('eyedropperBaseSelect');
    const patSel = document.getElementById('eyedropperPatternSelect');
    if (baseSel && baseSel.value) {
        if (baseSel.value.startsWith('mono:')) {
            zone.finish = baseSel.value.replace('mono:', '');
            zone.base = null;
            zone.pattern = null;
        } else {
            zone.base = baseSel.value;
            zone.finish = null;
            zone.pattern = (patSel && patSel.value) ? patSel.value : 'none';
        }
    }

    // Set intensity
    if (intSel && intSel.value) {
        zone.intensity = intSel.value;
    }

    selectedZoneIndex = targetIndex;
    renderZones();

    const parts = [];
    if (lastEyedropperColor) parts.push(zone.pickerColor?.toUpperCase());
    if (zone.base) {
        parts.push(BASES.find(b => b.id === zone.base)?.name || zone.base);
        if (zone.pattern && zone.pattern !== 'none') parts.push(PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern);
    } else if (zone.finish) {
        parts.push(MONOLITHICS.find(m => m.id === zone.finish)?.name || FINISHES.find(f => f.id === zone.finish)?.name || zone.finish);
    }
    if (zone.intensity) parts.push(zone.intensity);
    showToast(`${zone.name}: ${parts.join(' + ')}`);
}

function useEyedropperColor() {
    // "Set as Only" - replaces the zone with a single color (clears multi-color stack)
    if (!lastEyedropperColor) return;
    pushZoneUndo();
    const { r, g, b } = lastEyedropperColor;

    const sel = document.getElementById('eyedropperZoneSelect');
    const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;

    if (targetIndex >= 0 && targetIndex < zones.length) {
        const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
        const tol = zones[targetIndex].pickerTolerance || 40;
        zones[targetIndex].color = { color_rgb: [r, g, b], tolerance: tol };
        zones[targetIndex].colorMode = 'picker';
        zones[targetIndex].pickerColor = hex;
        zones[targetIndex].colors = []; // Clear multi-color stack
        selectedZoneIndex = targetIndex;
        renderZones();
        triggerPreviewRender();
        showToast(`Zone ${targetIndex + 1} (${zones[targetIndex].name}): set to ${hex.toUpperCase()} (single color)`);
    }
}

function addEyedropperColorToZone() {
    // "+ Add to Zone" - stacks this color into the zone's multi-color array
    if (!lastEyedropperColor) { showToast('Click a color on the paint first!', true); return; }
    pushZoneUndo();
    const { r, g, b } = lastEyedropperColor;

    const sel = document.getElementById('eyedropperZoneSelect');
    const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;

    if (targetIndex >= 0 && targetIndex < zones.length) {
        const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
        const tol = zones[targetIndex].pickerTolerance || 40;
        const zone = zones[targetIndex];

        // If zone was in single-color picker mode, migrate that color to the stack first
        if (zone.colorMode === 'picker' && zone.colors.length === 0 && zone.pickerColor) {
            const existR = parseInt(zone.pickerColor.substr(1, 2), 16);
            const existG = parseInt(zone.pickerColor.substr(3, 2), 16);
            const existB = parseInt(zone.pickerColor.substr(5, 2), 16);
            zone.colors.push({ color_rgb: [existR, existG, existB], tolerance: zone.pickerTolerance || 40, hex: zone.pickerColor });
        }

        // Check for duplicate
        if (zone.colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
            showToast('That color is already in this zone', true);
            return;
        }

        zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
        zone.colorMode = 'multi';
        zone.color = zone.colors;
        zone.pickerColor = hex; // Update picker display to last-added
        selectedZoneIndex = targetIndex;
        renderZones();
        triggerPreviewRender();
        showToast(`Added ${hex.toUpperCase()} to ${zone.name} (${zone.colors.length} colors stacked)`);
    }
}

// ===== USE REGION - commit lasso/brush drawn region to zone (no color needed) =====
function useRegionForZone() {
    const sel = document.getElementById('eyedropperZoneSelect');
    const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;
    if (targetIndex < 0 || targetIndex >= zones.length) {
        showToast('Select a zone first!', true);
        return;
    }
    const zone = zones[targetIndex];
    if (!zone.regionMask || !zone.regionMask.some(v => v > 0)) {
        showToast('Draw a region first! Use Lasso, Brush, Rect, or Wand tool to select an area.', true);
        return;
    }
    pushZoneUndo();
    // Count pixels in the region
    const pixelCount = zone.regionMask.reduce((sum, v) => sum + (v > 0 ? 1 : 0), 0);
    const canvas = document.getElementById('paintCanvas');
    const totalPixels = canvas ? canvas.width * canvas.height : 1;
    const pct = ((pixelCount / totalPixels) * 100).toFixed(1);
    // If zone has no color set, that's fine - region_mask bypasses color detection in the engine
    // Set a marker so the UI knows this zone uses region mode
    zone.useRegion = true;
    selectedZoneIndex = targetIndex;
    renderZones();
    triggerPreviewRender();
    updateRegionStatus();
    showToast(`🎯 Region applied to ${zone.name}: ${pixelCount.toLocaleString()} pixels (${pct}%) - assign a base/finish and hit Render!`);
}

// Update the region status indicator in the bottom bar
function updateRegionStatus() {
    const statusEl = document.getElementById('regionStatus');
    if (!statusEl) return;
    const zone = zones[selectedZoneIndex];
    if (zone && zone.regionMask && zone.regionMask.some(v => v > 0)) {
        const pixelCount = zone.regionMask.reduce((sum, v) => sum + (v > 0 ? 1 : 0), 0);
        statusEl.textContent = `Region: ${pixelCount.toLocaleString()}px ✓`;
        statusEl.style.color = '#cc88ff';
    } else {
        statusEl.textContent = '';
    }
}

// ===== LIVE PREVIEW SPLIT VIEW =====
let splitViewActive = false;
let previewDebounceTimer = null;
let previewAbortController = null;
let previewVersion = 0;           // Monotonic counter for staleness detection
let previewIsRendering = false;
let lastPreviewZoneHash = '';

function toggleSplitView() {
    splitViewActive = !splitViewActive;
    const splitBtn = document.getElementById('btnSplitView');
    const previewPane = document.getElementById('splitPreview');
    const sourceLabel = document.getElementById('sourcePaneLabel');

    if (splitBtn) splitBtn.classList.toggle('split-active', splitViewActive);
    if (previewPane) previewPane.style.display = splitViewActive ? 'flex' : 'none';
    if (sourceLabel) sourceLabel.style.display = splitViewActive ? '' : 'none';

    // Re-fit source canvas to the new (narrower or wider) space
    setTimeout(() => canvasZoom('fit'), 50);

    // Trigger initial preview if zones are configured
    if (splitViewActive) {
        triggerPreviewRender();
    }
}

function getZoneConfigHash() {
    // Hash all rendering-relevant zone fields to detect actual changes
    // Include mute states so muting/unmuting triggers hash change
    const muteKey = zones.map(z => z.muted ? '1' : '0').join('');
    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    if (validZones.length === 0) return muteKey || '';
    const hashData = validZones.map(z => ({
        base: z.base, pattern: z.pattern, finish: z.finish,
        scale: z.scale, rotation: z.rotation, baseRotation: z.baseRotation, baseScale: z.baseScale,
        patternOpacity: z.patternOpacity,
        patternStack: z.patternStack,
        intensity: z.intensity, patternIntensity: z.patternIntensity,
        customSpec: z.customSpec, customPaint: z.customPaint, customBright: z.customBright,
        color: z.color, colorMode: z.colorMode, colors: z.colors,
        pickerColor: z.pickerColor, pickerTolerance: z.pickerTolerance,
        wear: z.wear,
        ccQuality: z.ccQuality, blendBase: z.blendBase, blendDir: z.blendDir, blendAmount: z.blendAmount,
        usePaintReactive: z.usePaintReactive, paintReactiveColor: z.paintReactiveColor,
        secondBase: z.secondBase, secondBaseStrength: z.secondBaseStrength,
        secondBaseBlendMode: z.secondBaseBlendMode, secondBaseNoiseScale: z.secondBaseNoiseScale,
        secondBaseColor: z.secondBaseColor,
        // Region mask: just track length + sum for change detection (not full data)
        rmLen: z.regionMask ? z.regionMask.length : 0,
        rmSum: z.regionMask ? z.regionMask.reduce((a, b) => a + b, 0) : 0,
    }));
    return muteKey + JSON.stringify(hashData);
}

function triggerPreviewRender() {
    if (!splitViewActive) return;

    const hash = getZoneConfigHash();
    if (hash === lastPreviewZoneHash) return;  // Nothing actually changed
    if (hash === '') {
        // No valid zones - show empty state
        updatePreviewStatus('', '');
        document.getElementById('previewPaintPane').style.display = 'none';
        document.getElementById('previewSpecPane').style.display = 'none';
        document.getElementById('previewSpecPane').classList.remove('spec-expanded');
        specExpanded = false;
        document.getElementById('previewSpinner').style.display = 'none';
        document.getElementById('previewEmpty').style.display = '';
        return;
    }

    // Mark as stale
    updatePreviewStatus('stale', 'Changed');

    // Debounce: clear previous timer, set new 600ms timer
    if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
    previewDebounceTimer = setTimeout(() => {
        doPreviewRender(hash);
    }, 600);
}

async function doPreviewRender(zoneHash) {
    const paintFile = document.getElementById('paintFile').value.trim();
    if (!paintFile) return;
    if (!ShokkerAPI.online) return;

    // Abort any in-flight request
    if (previewAbortController) {
        previewAbortController.abort();
    }
    previewAbortController = new AbortController();

    // Increment version to detect stale responses
    previewVersion++;
    const thisVersion = previewVersion;

    // Show spinner
    previewIsRendering = true;
    updatePreviewStatus('rendering', 'Rendering...');
    document.getElementById('previewEmpty').style.display = 'none';
    document.getElementById('previewSpinner').style.display = 'flex';

    // Build server zones (same logic as doRender)
    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    const serverZones = validZones.map(z => {
        const zoneObj = {
            name: z.name,
            color: formatColorForServer(z.color, z),
            intensity: z.intensity,
        };
        if (z.customSpec != null) {
            zoneObj.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
        }
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) {
            zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        }
        if (z.base) {
            zoneObj.base = z.base;
            zoneObj.pattern = z.pattern || 'none';
            if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
            if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation;
            if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
            if (z.patternStack && z.patternStack.length > 0) {
                const stack = z.patternStack.filter(l => l.id && l.id !== 'none');
                if (stack.length > 0) {
                    zoneObj.pattern_stack = stack.map(l => ({
                        id: l.id,
                        opacity: (l.opacity != null ? l.opacity : 100) / 100,
                        scale: l.scale || 1.0,
                        rotation: l.rotation || 0,
                    }));
                }
            }
        } else if (z.finish) {
            zoneObj.finish = z.finish;
            // Send rotation for the finish itself (gradient direction, etc.)
            // baseRotation is the visible "Base Rotate" slider for finishes; rotation is pattern-only
            const _finishRot = z.baseRotation || z.rotation || 0;
            if (_finishRot && _finishRot !== 0) zoneObj.rotation = _finishRot;
            // Send color data for server-side fallback rendering
            const _fMono = MONOLITHICS.find(m => m.id === z.finish);
            if (_fMono) {
                zoneObj.finish_colors = {
                    c1: _fMono.swatch || null,
                    c2: _fMono.swatch2 || null,
                    c3: _fMono.swatch3 || null,
                    ghost: _fMono.ghostPattern || null,
                };
            }
            // Pattern overlay on monolithic - send pattern data if set
            if (z.pattern && z.pattern !== 'none') {
                zoneObj.pattern = z.pattern;
                if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
                if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
            }
        }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase) { zoneObj.blend_base = z.blendBase; zoneObj.blend_dir = z.blendDir || 'horizontal'; zoneObj.blend_amount = (z.blendAmount ?? 50) / 100; console.log(`[v6.1 BLEND] Zone "${z.name}" sending blend_base=${z.blendBase}, dir=${zoneObj.blend_dir}, amount=${zoneObj.blend_amount}`); }
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // Dual Layer Base Overlay
        if (z.secondBase && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = z.secondBaseNoiseScale || 24;
        }
        // Region mask RLE
        if (z.regionMask && z.regionMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc) {
                zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height);
            }
        }
        // Spatial mask RLE (include/exclude refinement)
        if (z.spatialMask && z.spatialMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc) {
                zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
            }
        }
        return zoneObj;
    });

    // Build request body
    const body = {
        paint_file: paintFile,
        zones: serverZones,
        seed: 51,
        preview_scale: 0.25,
    };

    // Include imported spec map if active (merge mode)
    if (importedSpecMapPath) {
        body.import_spec_map = importedSpecMapPath;
    }

    try {
        const resp = await fetch(ShokkerAPI.baseUrl + '/preview-render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: previewAbortController.signal,
        });

        // Check if this response is still current (not superseded)
        if (thisVersion !== previewVersion) return;

        const data = await resp.json();
        if (!data.success) {
            updatePreviewStatus('error', data.error || 'Failed');
            document.getElementById('previewSpinner').style.display = 'none';
            previewIsRendering = false;
            return;
        }

        // Update preview images (show both paint + spec simultaneously)
        const paintImg = document.getElementById('livePreviewImg');
        const specImg = document.getElementById('livePreviewSpecImg');
        paintImg.src = data.paint_preview;
        if (specImg) specImg.src = data.spec_preview;
        // Show both panes (paint full, spec inset) - reset expanded state
        document.getElementById('previewPaintPane').style.display = '';
        document.getElementById('previewSpecPane').style.display = '';
        document.getElementById('previewSpecPane').classList.remove('spec-expanded');
        specExpanded = false;
        document.getElementById('previewEmpty').style.display = 'none';
        document.getElementById('previewSpinner').style.display = 'none';

        // Update hash and status
        lastPreviewZoneHash = zoneHash;
        previewIsRendering = false;
        updatePreviewStatus('current', `${data.elapsed_ms}ms`);

        // Show/hide pattern indicator badge
        const patBadge = document.getElementById('patternActiveBadge');
        if (patBadge) {
            const hasPattern = zones.some(z => z.pattern && z.pattern !== 'none');
            patBadge.style.display = hasPattern ? '' : 'none';
        }

    } catch (err) {
        if (err.name === 'AbortError') return;  // Expected when superseded
        if (thisVersion !== previewVersion) return;
        previewIsRendering = false;
        updatePreviewStatus('error', 'Error');
        document.getElementById('previewSpinner').style.display = 'none';
        console.warn('[preview] render failed:', err);
    }
}

function updatePreviewStatus(state, text) {
    const badge = document.getElementById('previewStatus');
    if (!badge) return;
    badge.className = 'preview-status' + (state ? ' ' + state : '');
    badge.textContent = text || '';
}

function forcePreviewRefresh() {
    if (!splitViewActive) return;
    // Clear the hash so it re-renders even if nothing changed
    lastPreviewZoneHash = '';
    triggerPreviewRender();
    showToast('Refreshing preview...');
}

// ===== CANVAS ZOOM CONTROLS =====
let currentZoom = 1;
const ZOOM_STEPS = [0.1, 0.15, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];

function canvasZoom(action) {
    const canvas = document.getElementById('paintCanvas');
    const inner = document.getElementById('canvasInner');
    const viewport = document.getElementById('canvasViewport');
    if (!canvas || !inner || !viewport || !canvas.width) return;

    if (action === 'fit') {
        // When split view is active, fit within the source pane (half width)
        const fitContainer = splitViewActive ? document.getElementById('splitSource') : viewport;
        const vw = (fitContainer || viewport).clientWidth - 20;
        const vh = (fitContainer || viewport).clientHeight - 20;
        const fitZoom = Math.min(vw / canvas.width, vh / canvas.height);
        currentZoom = Math.min(fitZoom, 1); // Don't upscale past 100%
    } else if (action === '100') {
        currentZoom = 1;
    } else if (action === 'in') {
        const curIdx = ZOOM_STEPS.findIndex(s => s >= currentZoom - 0.01);
        const nextIdx = Math.min(curIdx + 1, ZOOM_STEPS.length - 1);
        currentZoom = ZOOM_STEPS[nextIdx];
    } else if (action === 'out') {
        const curIdx = ZOOM_STEPS.findIndex(s => s >= currentZoom - 0.01);
        const nextIdx = Math.max((curIdx >= 0 ? curIdx : 0) - 1, 0);
        currentZoom = ZOOM_STEPS[nextIdx];
    }

    applyZoom();
}

function applyZoom() {
    const canvas = document.getElementById('paintCanvas');
    const regionCanvas = document.getElementById('regionCanvas');
    const inner = document.getElementById('canvasInner');
    const viewport = document.getElementById('canvasViewport');
    if (!canvas || !inner) return;

    const w = Math.round(canvas.width * currentZoom);
    const h = Math.round(canvas.height * currentZoom);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    if (regionCanvas) {
        regionCanvas.style.width = w + 'px';
        regionCanvas.style.height = h + 'px';
    }
    // rectSelectionBox is a CSS div - no resize needed, it positions itself via drawRectPreview()
    inner.style.width = w + 'px';
    inner.style.height = h + 'px';

    // Centering: when canvas is smaller than scroll container, center via margin
    const sc = typeof getScrollContainer === 'function' ? getScrollContainer() : viewport;
    if (sc) {
        if (h < sc.clientHeight) {
            inner.style.marginTop = Math.max(0, Math.floor((sc.clientHeight - h) / 2)) + 'px';
        } else {
            inner.style.marginTop = '0';
        }
        // Horizontal centering - use JS margin instead of CSS auto
        // (margin:auto + overflow:auto = left side unreachable when content overflows)
        if (w < sc.clientWidth) {
            inner.style.marginLeft = Math.max(0, Math.floor((sc.clientWidth - w) / 2)) + 'px';
        } else {
            inner.style.marginLeft = '0';
        }
    }

    document.getElementById('zoomLevel').textContent = Math.round(currentZoom * 100) + '%';

    // Refresh cursor after zoom level changes
    if (viewport && !spaceHeld && !isPanning) {
        viewport.style.cursor = '';
        // Re-apply the mode cursor since zoom level may affect it
        const cvs = document.getElementById('paintCanvas');
        if (cvs && canvasMode === 'eyedropper') {
            cvs.style.cursor = 'crosshair';
        }
    }
}

// ===== CANVAS PAN & ZOOM =====
let isPanning = false;
let panStartX = 0, panStartY = 0;
let panScrollStartX = 0, panScrollStartY = 0;
let spaceHeld = false;

document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !e.repeat && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
        spaceHeld = true;
        const viewport = document.getElementById('canvasViewport');
        if (viewport) viewport.style.cursor = 'grab';
        e.preventDefault();
    }
});
document.addEventListener('keyup', (e) => {
    if (e.code === 'Space') {
        spaceHeld = false;
        if (!isPanning) {
            const viewport = document.getElementById('canvasViewport');
            if (viewport) viewport.style.cursor = '';
        }
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const viewport = document.getElementById('canvasViewport');
    if (!viewport) return;

    // Drag-and-drop paint file loading
    const centerPanel = viewport.closest('.center-panel') || viewport;
    ['dragenter', 'dragover'].forEach(evt => {
        centerPanel.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            centerPanel.style.outline = '2px dashed var(--accent)';
            centerPanel.style.outlineOffset = '-4px';
        });
    });
    ['dragleave', 'drop'].forEach(evt => {
        centerPanel.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            centerPanel.style.outline = '';
            centerPanel.style.outlineOffset = '';
        });
    });
    centerPanel.addEventListener('drop', (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (!file) return;
        const name = file.name.toLowerCase();
        if (name.endsWith('.tga') || name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.bmp')) {
            // Simulate the browsePaintFile flow by creating a synthetic input
            const dt = new DataTransfer();
            dt.items.add(file);
            const fakeInput = document.createElement('input');
            fakeInput.type = 'file';
            fakeInput.files = dt.files;
            browsePaintFile(fakeInput);
            showToast(`Dropped: ${file.name}`);
        } else {
            showToast('Drop a paint file (.tga, .png, .jpg)', true);
        }
    });

    // Mouse wheel = ALWAYS zoom (scroll up = zoom in, scroll down = zoom out)
    // Zooms toward the mouse cursor position for intuitive navigation
    viewport.addEventListener('wheel', (e) => {
        if (!document.getElementById('paintCanvas')?.width) return;
        e.preventDefault();

        const oldZoom = currentZoom;
        if (e.deltaY < 0) canvasZoom('in');
        else canvasZoom('out');
        const newZoom = currentZoom;

        // Zoom toward cursor: adjust scroll so the point under the cursor stays fixed
        if (oldZoom !== newZoom) {
            const sc = getScrollContainer();
            const rect = sc.getBoundingClientRect();
            // Mouse position relative to scroll container top-left
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            // Point in content that's under the cursor (in un-zoomed coords)
            const contentX = (sc.scrollLeft + mx) / oldZoom;
            const contentY = (sc.scrollTop + my) / oldZoom;
            // After zoom, that same content point should still be under the cursor
            sc.scrollLeft = contentX * newZoom - mx;
            sc.scrollTop = contentY * newZoom - my;
        }
    }, { passive: false });

    // ===== PAN SYSTEM =====
    // When zoomed in: left-click DRAG = pan, left-click (no drag) = tool action (eyedropper etc.)
    // Middle-click drag = pan (always)
    // Right-click drag = pan (always when zoomed)
    // Space + left-click = pan (always)
    //
    // The key insight: we intercept mousedown on the VIEWPORT (parent of canvas),
    // and decide whether it's a pan or a tool action based on whether the user drags.
    let pendingPan = false;
    let pendingPanEvent = null;
    let panConsumed = false;  // True if this mousedown became a pan (suppress canvas tool action)

    // Disable right-click context menu on canvas for right-drag panning
    viewport.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });

    viewport.addEventListener('mousedown', (e) => {
        panConsumed = false;

        // Middle button (button 1) always pans immediately
        if (e.button === 1) {
            e.preventDefault();
            startPan(e, viewport);
            panConsumed = true;
            return;
        }
        // Right button (button 2) pans when zoomed
        if (e.button === 2 && canvasOverflows()) {
            e.preventDefault();
            startPan(e, viewport);
            panConsumed = true;
            return;
        }
        // Space + left-click pans immediately
        if (spaceHeld && e.button === 0) {
            e.preventDefault();
            startPan(e, viewport);
            panConsumed = true;
            return;
        }
        // Left-click when zoomed in: DEFER - could be pan (drag) or tool action (click)
        // Short click = tool action (eyedropper, brush dot, etc.)
        // Drag past threshold = pan the view
        // BUT: if user is in a drag-based drawing tool, DON'T hijack for pan -
        // they need left-drag for rect, gradient, brush, erase strokes.
        // Pan is still available via space+drag, middle-click, or right-click.
        const drawToolActive = ['brush', 'rect', 'erase', 'spatial-include', 'spatial-exclude', 'lasso'].includes(canvasMode);
        if (e.button === 0 && canvasOverflows() && !drawToolActive) {
            pendingPan = true;
            pendingPanEvent = e;
            return;
        }
    });

    document.addEventListener('mousemove', (e) => {
        // Check if pending left-click should become a pan (drag threshold = 5px)
        if (pendingPan && pendingPanEvent) {
            const dx = e.clientX - pendingPanEvent.clientX;
            const dy = e.clientY - pendingPanEvent.clientY;
            if (dx * dx + dy * dy > 25) {  // 5px threshold
                startPan(pendingPanEvent, viewport);
                panConsumed = true;
                pendingPan = false;
                pendingPanEvent = null;
                // Cancel any active drawing operation so pan takes over cleanly
                isDrawing = false;
                rectStart = null;
            }
        }
        if (!isPanning) return;
        const sc = getScrollContainer();
        if (!sc) return;
        sc.scrollLeft = panScrollStartX - (e.clientX - panStartX);
        sc.scrollTop = panScrollStartY - (e.clientY - panStartY);
    });

    document.addEventListener('mouseup', (e) => {
        // If pending pan never started (quick click), just clean up - tool action already happened
        if (pendingPan) {
            pendingPan = false;
            pendingPanEvent = null;
        }
        if (isPanning) {
            isPanning = false;
            panConsumed = true;  // Keep flag until next mousedown
            const vp = document.getElementById('canvasViewport');
            const cvs = document.getElementById('paintCanvas');
            if (vp) {
                if (spaceHeld) {
                    vp.style.cursor = 'grab';
                    if (cvs) cvs.style.cursor = 'grab';
                } else {
                    vp.style.cursor = '';
                    // Restore canvas cursor based on current mode
                    if (cvs) {
                        if (canvasMode === 'eyedropper') cvs.style.cursor = 'crosshair';
                        else if (canvasMode === 'wand' || canvasMode === 'selectall' || canvasMode === 'edge') cvs.style.cursor = 'crosshair';
                        else if (['brush', 'erase', 'spatial-include', 'spatial-exclude'].includes(canvasMode)) cvs.style.cursor = 'none';
                        else cvs.style.cursor = 'cell';
                    }
                }
            }
        }
    });
});

// Returns the element that actually scrolls when the canvas is zoomed.
// This is the split-source pane (closest scrollable ancestor of canvasInner).
function getScrollContainer() {
    return document.getElementById('splitSource') || document.getElementById('canvasViewport');
}

function startPan(e, viewport) {
    const sc = getScrollContainer();
    isPanning = true;
    panStartX = e.clientX;
    panStartY = e.clientY;
    panScrollStartX = sc.scrollLeft;
    panScrollStartY = sc.scrollTop;
    viewport.style.cursor = 'grabbing';
    // Also set canvas cursor so it overrides the tool-specific cursor during pan
    const canvas = document.getElementById('paintCanvas');
    if (canvas) canvas.style.cursor = 'grabbing';
    console.log('[PAN] Started pan - scrollStart:', panScrollStartX, panScrollStartY,
        'scrollMax:', sc.scrollWidth - sc.clientWidth, sc.scrollHeight - sc.clientHeight,
        'containerSize:', sc.clientWidth, 'x', sc.clientHeight,
        'scrollSize:', sc.scrollWidth, 'x', sc.scrollHeight,
        'container:', sc.id);
}

// Returns true if the zoomed canvas is bigger than the scroll container (scroll needed)
function canvasOverflows() {
    const sc = getScrollContainer();
    const canvas = document.getElementById('paintCanvas');
    if (!sc || !canvas || !canvas.width) return false;
    const w = Math.round(canvas.width * currentZoom);
    const h = Math.round(canvas.height * currentZoom);
    return w > sc.clientWidth || h > sc.clientHeight;
}

// ===== FINISH PATTERN PREVIEW RENDERER (Client-side) =====
// Renders miniature versions of each texture/base to canvas for visual preview
const _previewCache = {}; // Cache rendered previews: finishId → ImageData

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
        dragon_scale: (ctx, w, h) => {
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
        tire_tread: (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const vp = ((px + py * 0.5) % 20);
                    const depth = Math.abs(vp - 10) / 10;
                    const v = Math.floor(30 + depth * 50);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = v; id.data[idx + 1] = v; id.data[idx + 2] = v; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
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
        mosaic: (ctx, w, h) => {
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
            const cs = 6;
            for (let py = 0; py < h; py += cs) {
                for (let px = 0; px < w; px += cs) {
                    ctx.fillStyle = ((Math.floor(px / cs) + Math.floor(py / cs)) % 2) ? '#222' : '#eee';
                    ctx.fillRect(px, py, cs, cs);
                }
            }
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
            ctx.fillStyle = '#1a0a2a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4200);
            for (let y = 0; y < h; y += 2) {
                const offset = Math.floor((rng() - 0.5) * 8);
                const bright = rng() > 0.7;
                const r = bright ? 200 + rng() * 55 : 40 + rng() * 30;
                const g = bright ? 50 + rng() * 40 : 20 + rng() * 20;
                const b = bright ? 80 + rng() * 60 : 60 + rng() * 40;
                ctx.fillStyle = `rgb(${Math.floor(r)},${Math.floor(g)},${Math.floor(b)})`;
                ctx.fillRect(offset, y, w, 2);
            }
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
        steampunk_gears: (ctx, w, h) => {
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
        mandala: (ctx, w, h) => {
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
        fleur_de_lis: (ctx, w, h) => {
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
            ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#4444cc'; ctx.lineWidth = 1.5;
            const cx = w / 2, cy = h / 2;
            for (let r = 5; r < Math.max(w, h) * 0.8; r += 6) {
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
            ctx.strokeStyle = '#cc4444'; ctx.lineWidth = 1;
            for (let r = 8; r < Math.max(w, h) * 0.8; r += 6) {
                ctx.beginPath(); ctx.arc(cx + 4, cy + 3, r, 0, Math.PI * 2); ctx.stroke();
            }
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
        norse_rune: (ctx, w, h) => {
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
            ctx.fillStyle = '#667766'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(5600);
            for (let i = 0; i < 8; i++) {
                const bx = rng() * w, by = rng() * h, br = 2 + rng() * 3;
                ctx.fillStyle = '#222'; ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();
                ctx.strokeStyle = '#556655'; ctx.lineWidth = 0.8;
                for (let c = 0; c < 4; c++) {
                    const ca = rng() * Math.PI * 2, cl = br + 2 + rng() * 6;
                    ctx.beginPath(); ctx.moveTo(bx + Math.cos(ca) * br, by + Math.sin(ca) * br);
                    ctx.lineTo(bx + Math.cos(ca) * cl, by + Math.sin(ca) * cl); ctx.stroke();
                }
            }
        },
        brake_dust: (ctx, w, h) => {
            ctx.fillStyle = '#2a2018'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(3300);
            for (let i = 0; i < 80; i++) {
                const x = rng() * w, y = rng() * h, sz = 0.5 + rng() * 2;
                ctx.fillStyle = `rgba(${120 + rng() * 60},${60 + rng() * 30},${20 + rng() * 20},${0.4 + rng() * 0.6})`;
                ctx.fillRect(x, y, sz, sz);
            }
        },
        road_rash: (ctx, w, h) => {
            ctx.fillStyle = '#555544'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(4400);
            ctx.strokeStyle = 'rgba(100,90,80,0.7)'; ctx.lineWidth = 1.5;
            for (let i = 0; i < 12; i++) {
                const y = rng() * h;
                ctx.beginPath(); ctx.moveTo(0, y);
                for (let x = 0; x < w; x += 4) { ctx.lineTo(x, y + rng() * 4 - 2); } ctx.stroke();
            }
        },
        skid_marks: (ctx, w, h) => {
            ctx.fillStyle = '#666'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = 'rgba(20,20,20,0.7)';
            for (let i = 0; i < 3; i++) {
                const y = h * 0.2 + i * h * 0.25, tw = 3 + i * 2;
                ctx.fillRect(0, y, w, tw); ctx.fillRect(0, y + tw + 4, w, tw - 1);
            }
        },
        tire_smoke: (ctx, w, h) => {
            ctx.fillStyle = '#333'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8800);
            for (let i = 0; i < 20; i++) {
                const x = rng() * w, y = rng() * h, r = 8 + rng() * 15;
                const g = ctx.createRadialGradient(x, y, 0, x, y, r);
                g.addColorStop(0, `rgba(${140 + rng() * 40},${140 + rng() * 40},${140 + rng() * 40},0.3)`);
                g.addColorStop(1, 'rgba(60,60,60,0)');
                ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
            }
        },
        rpm_gauge: (ctx, w, h) => {
            ctx.fillStyle = '#111'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h * 0.6, r = Math.min(w, h) * 0.42;
            ctx.strokeStyle = '#444'; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 0); ctx.stroke();
            for (let i = 0; i <= 8; i++) {
                const a = Math.PI + i * Math.PI / 8;
                const c = i >= 6 ? '#dd3333' : '#33dd44'; ctx.strokeStyle = c; ctx.lineWidth = 3;
                ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * r * 0.75, cy + Math.sin(a) * r * 0.75);
                ctx.lineTo(cx + Math.cos(a) * r * 0.95, cy + Math.sin(a) * r * 0.95); ctx.stroke();
            }
            ctx.strokeStyle = '#ff4444'; ctx.lineWidth = 2; const na = Math.PI + Math.PI * 0.82;
            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(na) * r * 0.7, cy + Math.sin(na) * r * 0.7); ctx.stroke();
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
            ctx.fillStyle = '#2a3a2a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#557755'; ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(w * 0.2, h * 0.8);
            ctx.quadraticCurveTo(w * 0.1, h * 0.3, w * 0.3, h * 0.2);
            ctx.quadraticCurveTo(w * 0.6, h * 0.1, w * 0.8, h * 0.3);
            ctx.quadraticCurveTo(w * 0.9, h * 0.6, w * 0.6, h * 0.7);
            ctx.quadraticCurveTo(w * 0.4, h * 0.8, w * 0.3, h * 0.9);
            ctx.quadraticCurveTo(w * 0.15, h * 0.95, w * 0.2, h * 0.8);
            ctx.stroke();
            ctx.fillStyle = '#dd2222'; ctx.fillRect(w * 0.18, h * 0.78, 6, 3);
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
            ctx.fillStyle = '#0a1a2a'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.3, cy = h * 0.5;
            const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, w * 0.7);
            g.addColorStop(0, 'rgba(100,220,255,0.8)'); g.addColorStop(0.3, 'rgba(40,150,255,0.4)'); g.addColorStop(1, 'rgba(0,30,60,0)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(200,240,255,0.5)'; ctx.lineWidth = 1;
            const rng = _seededRng(7700);
            for (let i = 0; i < 10; i++) {
                const a = -0.6 + rng() * 1.2, r = w * 0.2 + rng() * w * 0.5;
                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.stroke();
            }
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
            ctx.fillStyle = '#445566'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#6688aa'; ctx.lineWidth = 1;
            const s = 12; const h2 = s * Math.sin(Math.PI / 3);
            for (let row = 0; row < Math.ceil(h / h2) + 1; row++) {
                for (let col = 0; col < Math.ceil(w / s) + 1; col++) {
                    const cx = col * s + (row % 2 ? s / 2 : 0), cy = row * h2;
                    ctx.beginPath();
                    for (let i = 0; i < 6; i++) {
                        const a = i * Math.PI / 3;
                        const px = cx + Math.cos(a) * s * 0.55, py = cy + Math.sin(a) * s * 0.55;
                        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                    } ctx.closePath(); ctx.stroke();
                }
            }
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
            ctx.fillStyle = '#0a0a1a'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#6644cc'; ctx.lineWidth = 1;
            const drawBranch = (x, y, len, angle, depth) => {
                if (depth <= 0 || len < 2) return;
                const ex = x + Math.cos(angle) * len, ey = y + Math.sin(angle) * len;
                ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(ex, ey); ctx.stroke();
                drawBranch(ex, ey, len * 0.65, angle - 0.5, depth - 1);
                drawBranch(ex, ey, len * 0.65, angle + 0.5, depth - 1);
            };
            drawBranch(w * 0.5, h * 0.9, h * 0.3, -Math.PI / 2, 6);
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
            ctx.fillStyle = '#2a2a44'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            for (let r = 3; r < Math.max(w, h) * 0.6; r += 4) {
                const hue = (r * 5) % 360;
                ctx.strokeStyle = `hsla(${hue},60%,60%,${0.15 + Math.sin(r * 0.1) * 0.1})`;
                ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        neural: (ctx, w, h) => {
            ctx.fillStyle = '#0a1520'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(6600);
            const cells = []; for (let i = 0; i < 10; i++) { cells.push([rng() * w, rng() * h]); }
            ctx.strokeStyle = 'rgba(100,160,200,0.3)'; ctx.lineWidth = 1;
            for (let y = 0; y < h; y += 2) {
                for (let x = 0; x < w; x += 2) {
                    let minD = 999, minI = 0;
                    for (let i = 0; i < cells.length; i++) { const d = Math.hypot(x - cells[i][0], y - cells[i][1]); if (d < minD) { minD = d; minI = i; } }
                    let secD = 999;
                    for (let i = 0; i < cells.length; i++) { if (i !== minI) { const d = Math.hypot(x - cells[i][0], y - cells[i][1]); if (d < secD) secD = d; } }
                    if (Math.abs(minD - secD) < 3) { ctx.fillStyle = 'rgba(100,170,220,0.5)'; ctx.fillRect(x, y, 2, 2); }
                }
            }
            ctx.fillStyle = 'rgba(120,200,255,0.6)';
            for (const c of cells) { ctx.beginPath(); ctx.arc(c[0], c[1], 2, 0, Math.PI * 2); ctx.fill(); }
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
            // Random material blocks - chaotic patchwork
            const rng = _seededRng(8802); const bs = 6;
            const id = ctx.createImageData(w, h);
            for (let by = 0; by < h; by += bs) {
                for (let bx = 0; bx < w; bx += bs) {
                    const r = Math.floor(rng() * 200 + 40), g = Math.floor(rng() * 200 + 40), b = Math.floor(rng() * 200 + 40);
                    for (let py = by; py < Math.min(by + bs, h); py++) {
                        for (let px = bx; px < Math.min(bx + bs, w); px++) {
                            const idx = (py * w + px) * 4;
                            id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                        }
                    }
                }
            }
            ctx.putImageData(id, 0, 0);
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
            // Conductor/dielectric micro-stripes - alternating shimmer
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const idx = (py * w + px) * 4;
                    const stripe = Math.floor((px + py * 0.5) / 3) % 2;
                    if (stripe) {
                        id.data[idx] = 160; id.data[idx + 1] = 150; id.data[idx + 2] = 180;
                    } else {
                        id.data[idx] = 100; id.data[idx + 1] = 90; id.data[idx + 2] = 120;
                    }
                    id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        gravity_well: (ctx, w, h) => {
            // Radial chrome-to-matte gradient traps
            ctx.fillStyle = '#2a2a3a'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(8811);
            for (let i = 0; i < 4; i++) {
                const cx = rng() * w, cy = rng() * h, r = 8 + rng() * 15;
                const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
                g.addColorStop(0, 'rgba(200,210,230,0.6)');
                g.addColorStop(0.5, 'rgba(100,110,130,0.3)');
                g.addColorStop(1, 'rgba(42,42,58,0)');
                ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            }
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
            // Void portals with chrome event horizon rims
            ctx.fillStyle = '#060610'; ctx.fillRect(0, 0, w, h);
            const cx1 = w * 0.3, cy1 = h * 0.45, cx2 = w * 0.7, cy2 = h * 0.55;
            [{ x: cx1, y: cy1 }, { x: cx2, y: cy2 }].forEach(p => {
                const r = Math.min(w, h) * 0.18;
                // Chrome rim
                const rim = ctx.createRadialGradient(p.x, p.y, r * 0.6, p.x, p.y, r);
                rim.addColorStop(0, 'rgba(0,0,0,0)');
                rim.addColorStop(0.7, 'rgba(180,200,240,0.5)');
                rim.addColorStop(0.85, 'rgba(220,230,255,0.7)');
                rim.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = rim; ctx.fillRect(0, 0, w, h);
                // Void center
                const vc = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 0.65);
                vc.addColorStop(0, '#000008'); vc.addColorStop(1, 'rgba(6,6,16,0)');
                ctx.fillStyle = vc; ctx.fillRect(0, 0, w, h);
            });
        },
        crystal_lattice: (ctx, w, h) => {
            // Overlapping hex grid - crystalline interference
            ctx.fillStyle = '#1a2038'; ctx.fillRect(0, 0, w, h);
            const layers = [
                { s: 12, c: 'rgba(140,160,220,0.2)' },
                { s: 8, c: 'rgba(100,130,200,0.15)' },
                { s: 18, c: 'rgba(170,180,230,0.1)' },
            ];
            layers.forEach(l => {
                ctx.strokeStyle = l.c; ctx.lineWidth = 1;
                const s = l.s, hr = s * 0.866;
                for (let row = -1; row < h / hr + 1; row++) {
                    for (let col = -1; col < w / s + 1; col++) {
                        const cx = col * s * 1.5 + (row % 2) * s * 0.75;
                        const cy = row * hr;
                        ctx.beginPath();
                        for (let i = 0; i < 6; i++) {
                            const a = Math.PI / 3 * i - Math.PI / 6;
                            const px = cx + Math.cos(a) * s * 0.5, py = cy + Math.sin(a) * s * 0.5;
                            i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                        }
                        ctx.closePath(); ctx.stroke();
                    }
                }
            });
        },
        pulse: (ctx, w, h) => {
            // Concentric metallic ring wavefronts
            ctx.fillStyle = '#141828'; ctx.fillRect(0, 0, w, h);
            const cx = w * 0.5, cy = h * 0.5;
            const maxR = Math.max(w, h) * 0.6;
            for (let r = 4; r < maxR; r += 6) {
                const t = (r / maxR);
                const bright = Math.floor(80 + Math.sin(r * 0.3) * 60);
                ctx.strokeStyle = 'rgba(' + bright + ',' + (bright + 20) + ',' + (bright + 50) + ',' + (0.3 - t * 0.2) + ')';
                ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        // === FLAMES (12) ===
        classic_hotrod: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a1a'; ctx.fillRect(0, 0, w, h);
            const g = ctx.createLinearGradient(0, h, w * 0.3, 0);
            g.addColorStop(0, '#ff4400'); g.addColorStop(0.4, '#ff8800'); g.addColorStop(0.7, '#ffcc00'); g.addColorStop(1, 'rgba(255,200,0,0)');
            ctx.fillStyle = g;
            for (let i = 0; i < 4; i++) {
                ctx.beginPath(); ctx.moveTo(0, h - i * 8);
                ctx.quadraticCurveTo(w * 0.3, h * 0.3 - i * 6, w * 0.7, h * 0.5 - i * 4);
                ctx.quadraticCurveTo(w * 0.9, h * 0.2 - i * 3, w, h * 0.1);
                ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.fill();
            }
        },
        ghost_flames: (ctx, w, h) => {
            ctx.fillStyle = '#2a2a3a'; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.15;
            for (let i = 0; i < 5; i++) {
                ctx.strokeStyle = '#aabbcc'; ctx.lineWidth = 3 - i * 0.4;
                ctx.beginPath(); ctx.moveTo(0, h - i * 7);
                ctx.bezierCurveTo(w * 0.2, h * 0.4 - i * 5, w * 0.5, h * 0.6 - i * 3, w, h * 0.2 - i * 2);
                ctx.stroke();
            }
            ctx.globalAlpha = 1;
        },
        pinstripe_flames: (ctx, w, h) => {
            ctx.fillStyle = '#1a1a22'; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#ff6600'; ctx.lineWidth = 1;
            for (let i = 0; i < 6; i++) {
                ctx.beginPath(); ctx.moveTo(0, h - i * 6);
                ctx.bezierCurveTo(w * 0.25, h * 0.3 - i * 4, w * 0.6, h * 0.5 - i * 3, w, h * 0.15 - i * 2);
                ctx.stroke();
            }
        },
        fire_lick: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a00'; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(601);
            for (let i = 0; i < 8; i++) {
                const x = rng() * w, bw = 4 + rng() * 8;
                const g = ctx.createLinearGradient(x, h, x, h * 0.2);
                g.addColorStop(0, '#ff4400'); g.addColorStop(0.5, '#ff8800'); g.addColorStop(1, 'rgba(255,200,0,0)');
                ctx.fillStyle = g;
                ctx.beginPath(); ctx.moveTo(x - bw / 2, h);
                ctx.quadraticCurveTo(x - bw / 4, h * 0.4 + rng() * 10, x, h * 0.1 + rng() * 10);
                ctx.quadraticCurveTo(x + bw / 4, h * 0.4 + rng() * 10, x + bw / 2, h);
                ctx.fill();
            }
        },
        inferno: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(602);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = 1 - py / h; const n = rng() * 0.3;
                    const heat = Math.max(0, Math.min(1, t * 1.5 + n - 0.2));
                    const r = Math.floor(heat > 0.5 ? 255 : heat * 2 * 255);
                    const g = Math.floor(heat > 0.7 ? (heat - 0.7) * 3 * 255 : 0);
                    const b = Math.floor(heat > 0.9 ? (heat - 0.9) * 10 * 100 : 0);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        fireball: (ctx, w, h) => {
            const cx = w / 2, cy = h / 2, maxR = w * 0.45;
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const d = Math.sqrt((px - cx) ** 2 + (py - cy) ** 2) / maxR;
                    const heat = Math.max(0, 1 - d);
                    const r = Math.floor(Math.min(255, heat * 350));
                    const g = Math.floor(Math.min(255, heat * heat * 300));
                    const b = Math.floor(heat > 0.8 ? (heat - 0.8) * 5 * 255 : 0);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        hellfire: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(604);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = 1 - py / h; const n = (rng() - 0.5) * 0.3;
                    const heat = Math.max(0, Math.min(1, t * 1.2 + n));
                    const r = Math.floor(heat * 200); const g = Math.floor(heat * heat * 80);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = 0; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        wildfire: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(605);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = 1 - py / h; const n = (rng() - 0.5) * 0.5;
                    const heat = Math.max(0, Math.min(1, t + n * 0.8));
                    const r = Math.floor(Math.min(255, heat * 300));
                    const g = Math.floor(Math.min(255, heat * heat * 200));
                    const b = Math.floor(heat > 0.7 ? 20 : 0);
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        flame_fade: (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, h, 0, 0);
            g.addColorStop(0, '#ff4400'); g.addColorStop(0.3, '#ff8800');
            g.addColorStop(0.6, '#cc7744'); g.addColorStop(0.8, '#666');
            g.addColorStop(1, '#333');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            const rng = _seededRng(606); const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < id.data.length; i += 4) { const n = (rng() - 0.5) * 20; id.data[i] += n; id.data[i + 1] += n; id.data[i + 2] += n; }
            ctx.putImageData(id, 0, 0);
        },
        blue_flame: (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const rng = _seededRng(607);
            for (let py = 0; py < h; py++) {
                for (let px = 0; px < w; px++) {
                    const t = 1 - py / h; const n = rng() * 0.3;
                    const heat = Math.max(0, Math.min(1, t * 1.4 + n - 0.2));
                    const r = Math.floor(heat > 0.8 ? (heat - 0.8) * 5 * 200 : 0);
                    const g = Math.floor(heat > 0.5 ? (heat - 0.5) * 2 * 200 : 0);
                    const b = Math.floor(Math.min(255, heat * 300));
                    const idx = (py * w + px) * 4;
                    id.data[idx] = r; id.data[idx + 1] = g; id.data[idx + 2] = b; id.data[idx + 3] = 255;
                }
            }
            ctx.putImageData(id, 0, 0);
        },
        torch_burn: (ctx, w, h) => {
            ctx.fillStyle = '#1a1008'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h * 0.7;
            const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, w * 0.6);
            g.addColorStop(0, '#ffcc44'); g.addColorStop(0.3, '#ff6600');
            g.addColorStop(0.6, '#aa3300'); g.addColorStop(1, 'rgba(20,10,0,0)');
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        },
        ember_scatter: (ctx, w, h) => {
            ctx.fillStyle = '#1a0a00'; ctx.fillRect(0, 0, w, h);
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
            ctx.fillStyle = '#ffcc00'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ee3333';
            const cx = w / 2, cy = h / 2;
            ctx.beginPath();
            for (let i = 0; i < 16; i++) {
                const a = i * Math.PI / 8;
                const r = i % 2 ? w * 0.45 : w * 0.2;
                const method = i === 0 ? 'moveTo' : 'lineTo';
                ctx[method](cx + Math.cos(a) * r, cy + Math.sin(a) * r);
            }
            ctx.closePath(); ctx.fill();
        },
        web_pattern: (ctx, w, h) => {
            ctx.fillStyle = '#222244'; ctx.fillRect(0, 0, w, h);
            const cx = w / 2, cy = h / 2;
            ctx.strokeStyle = '#aaaacc'; ctx.lineWidth = 0.5;
            // Radials
            for (let i = 0; i < 8; i++) {
                const a = i * Math.PI / 4;
                ctx.beginPath(); ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(a) * w, cy + Math.sin(a) * h);
                ctx.stroke();
            }
            // Rings
            for (let r = 5; r < w; r += 6) {
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
            }
        },
        dark_knight_scales: (ctx, w, h) => {
            ctx.fillStyle = '#1a2233'; ctx.fillRect(0, 0, w, h);
            const ss = 8;
            for (let row = 0; row < Math.ceil(h / ss) + 1; row++) {
                const off = (row % 2) * ss / 2;
                for (let col = -1; col < Math.ceil(w / ss) + 1; col++) {
                    const cx = col * ss + off, cy = row * ss;
                    ctx.fillStyle = `rgb(${30 + row * 3},${35 + row * 3},${50 + row * 3})`;
                    ctx.beginPath();
                    ctx.arc(cx, cy, ss * 0.55, 0, Math.PI); ctx.fill();
                }
            }
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
            ctx.fillStyle = '#ffcc00'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ff4400';
            const cx = w / 2, cy = h / 2;
            ctx.beginPath();
            for (let i = 0; i < 20; i++) {
                const a = i * Math.PI / 10;
                const r = i % 2 ? w * 0.45 : w * 0.15;
                i === 0 ? ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r) : ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
            }
            ctx.closePath(); ctx.fill();
            ctx.fillStyle = '#ffffff'; ctx.font = 'bold 10px sans-serif'; ctx.textAlign = 'center';
            ctx.fillText('POW', cx, cy + 4);
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
            ctx.fillStyle = '#112244'; ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = '#ffee33';
            ctx.beginPath();
            ctx.moveTo(w * 0.55, 0); ctx.lineTo(w * 0.3, h * 0.45);
            ctx.lineTo(w * 0.5, h * 0.45); ctx.lineTo(w * 0.35, h);
            ctx.lineTo(w * 0.7, h * 0.5); ctx.lineTo(w * 0.5, h * 0.5);
            ctx.lineTo(w * 0.55, 0);
            ctx.fill();
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
            const sp = 8;
            for (let i = -h; i < w + h; i += sp) {
                ctx.fillStyle = (Math.floor(i / sp) % 2) ? '#663399' : '#331166';
                ctx.beginPath();
                ctx.moveTo(i, 0); ctx.lineTo(i + sp / 2, 0);
                ctx.lineTo(i + sp / 2 + h, h); ctx.lineTo(i + h, h);
                ctx.closePath(); ctx.fill();
            }
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
            // Magenta left / cyan right split with glitch lines
            for (let x = 0; x < w; x++) {
                const t = x / w;
                if (t < 0.5) {
                    ctx.fillStyle = `rgba(${Math.floor(120 + (0.5 - t) * 200)},20,${Math.floor(80 + (0.5 - t) * 140)},1)`;
                } else {
                    ctx.fillStyle = `rgba(20,${Math.floor(80 + (t - 0.5) * 200)},${Math.floor(120 + (t - 0.5) * 200)},1)`;
                }
                ctx.fillRect(x, 0, 1, h);
            }
            // Glitch lines
            const rng = _seededRng(790);
            for (let i = 0; i < 4; i++) {
                const y = Math.floor(rng() * h);
                const gh = 1 + Math.floor(rng() * 2);
                ctx.fillStyle = 'rgba(255,255,255,0.3)';
                ctx.fillRect(0, y, w, gh);
            }
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

    };

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
                            case 'dragon_scale': { const sx2 = (px + (Math.floor(py / 7) % 2) * 5) % 10, sy2 = py % 7; return (sx2 * sx2 / 25 + sy2 * sy2 / 12 < 1) ? 0.07 : -0.03; }
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

// Render a swatch canvas for the finish library list item
function renderFinishSwatch(canvas, finishId) {
    const cacheKey = finishId + '_swatch';
    if (_previewCache[cacheKey]) {
        canvas.getContext('2d').putImageData(_previewCache[cacheKey], 0, 0);
        return;
    }
    const ctx = canvas.getContext('2d');
    renderPatternPreview(ctx, canvas.width, canvas.height, finishId);
    _previewCache[cacheKey] = ctx.getImageData(0, 0, canvas.width, canvas.height);
}

// ===== FINISH HOVER POPUP =====
let finishPopupTimeout = null;

function showFinishPopup(e, finishId) {
    const finish = BASES.find(f => f.id === finishId) || PATTERNS.find(f => f.id === finishId) || MONOLITHICS.find(f => f.id === finishId) || FINISHES.find(f => f.id === finishId);
    if (!finish) return;

    clearTimeout(finishPopupTimeout);
    const popup = document.getElementById('finishPopup');
    const previewCanvas = document.getElementById('finishPopupPreview');
    const nameEl = document.getElementById('finishPopupName');
    const descEl = document.getElementById('finishPopupDesc');
    const catEl = document.getElementById('finishPopupCat');
    const chanEl = document.getElementById('finishPopupChannels');

    // Use server-rendered swatch (240x160) instead of JS canvas
    const swatchUrl = getSwatchUrl(finishId, '888888');
    if (swatchUrl) {
        const swatchW = previewCanvas.width, swatchH = previewCanvas.height;
        const pctx = previewCanvas.getContext('2d');
        pctx.fillStyle = '#1a1a1a';
        pctx.fillRect(0, 0, swatchW, swatchH);
        const img = new Image();
        img.onload = () => {
            pctx.clearRect(0, 0, swatchW, swatchH);
            pctx.drawImage(img, 0, 0, swatchW, swatchH);
        };
        img.src = swatchUrl.replace('size=48', `size=${swatchW}`);
    } else {
        const pctx = previewCanvas.getContext('2d');
        const cacheKey = finishId + '_popup';
        if (_previewCache[cacheKey]) {
            pctx.putImageData(_previewCache[cacheKey], 0, 0);
        } else {
            renderPatternPreview(pctx, previewCanvas.width, previewCanvas.height, finishId);
            _previewCache[cacheKey] = pctx.getImageData(0, 0, previewCanvas.width, previewCanvas.height);
        }
    }

    nameEl.textContent = finish.name;
    descEl.textContent = finish.desc;
    catEl.textContent = finish.cat || (BASES.find(f => f.id === finishId) ? 'Base Material' : PATTERNS.find(f => f.id === finishId) ? 'Pattern' : 'Special');

    // Show spec channel hints based on finish type
    const channelHints = {
        'gloss': 'M:0 R:20 CC:16 - smooth mirror clearcoat',
        'matte': 'M:0 R:215 CC:0 - zero metallic, max rough',
        'satin': 'M:0 R:100 CC:10 - mid sheen partial clearcoat',
        'metallic': 'M:200 R:50 CC:16 - visible flake sparkle',
        'pearl': 'M:100 R:40 CC:16 - pearlescent shimmer',
        'chrome': 'M:255 R:2 CC:0 - perfect mirror reflection',
        'candy': 'M:130 R:15 CC:16 - deep wet tinted glass',
        'satin_metal': 'M:235 R:65 CC:16 - subtle brushed metallic',
        'brushed_titanium': 'M:180 R:70 CC:0 - heavy directional grain',
        'anodized': 'M:170 R:80 CC:0 - gritty matte aluminum',
        'frozen': 'M:225 R:140 CC:0 - frozen icy matte metal',
        'blackout': 'M:30 R:220 CC:0 - stealth murdered out',
        'carbon_fiber': 'Pattern: tight 2x2 twill weave, R modulation ±50',
        'forged_carbon': 'Pattern: chopped chunks, M±40 R±50',
        'diamond_plate': 'Pattern: raised diamond tread, R-132 M+60',
        'dragon_scale': 'Pattern: hex scales, center=shiny edge=rough',
        'hex_mesh': 'Pattern: honeycomb wire grid, R-155 M+155',
        'ripple': 'Pattern: concentric ring waves, R-85 M+100',
        'hammered': 'Pattern: hand-hammered dimples, R-112 M+95',
        'lightning': 'Pattern: forked bolt paths, R-177 M+175',
        'plasma': 'Pattern: branching electric veins, R-118 M+95',
        'hologram': 'Pattern: 6px scanlines, R-75 only',
        'interference': 'Pattern: rainbow wave bands, R+100 only',
        'battle_worn': 'Pattern: scratch damage + variable clearcoat',
        'acid_wash': 'Pattern: acid etch + variable clearcoat',
        'cracked_ice': 'Pattern: frozen crack network, R+115',
        'metal_flake': 'Pattern: coarse sparkle, M+50 + R noise',
        'holographic_flake': 'Pattern: prismatic micro-grid, R+40',
        'stardust': 'Pattern: sparse star pinpoints, R-52 M+95',
        'phantom': 'Special: paint vanishes into mirror',
        'ember_glow': 'Special: hot metal glowing from within',
        'liquid_metal': 'Special: flowing mercury T-1000 pools',
        'frost_bite': 'Special: coarse ice crystal texture',
        'worn_chrome': 'Special: patchy chrome with patina wear',
        // --- Expansion Pack Bases ---
        'ceramic': 'M:60 R:8 CC:16 - ultra-smooth ceramic coating',
        'satin_wrap': 'M:0 R:130 CC:0 - vinyl wrap satin sheen',
        'primer': 'M:0 R:200 CC:0 - raw flat primer gray',
        'gunmetal': 'M:220 R:40 CC:16 - dark blue-gray metallic',
        'copper': 'M:190 R:55 CC:16 - warm oxidized copper',
        'chameleon': 'M:160 R:25 CC:16 - dual-tone color-shift',
        // --- Expansion Pack Patterns ---
        'pinstripe': 'Pattern: thin parallel stripes, R-60 M+40',
        'camo': 'Pattern: digital splinter blocks, R+60 M-30',
        'wood_grain': 'Pattern: flowing grain lines, R+80 M-50',
        'snake_skin': 'Pattern: elongated scales, R-100 M+80',
        'tire_tread': 'Pattern: V-groove rubber, R+80 M-40',
        'circuit_board': 'Pattern: PCB traces + pads, R-120 M+140',
        'mosaic': 'Pattern: Voronoi glass tiles, R-90 M+80',
        'lava_flow': 'Pattern: molten cracks + variable CC',
        'rain_drop': 'Pattern: water beading, R-80 M+60',
        'barbed_wire': 'Pattern: twisted wire + barbs, R-100 M+130',
        'chainmail': 'Pattern: interlocking rings, R-90 M+100',
        'brick': 'Pattern: offset blocks + mortar, R+60 M-40',
        'leopard': 'Pattern: organic rosette spots, R+50 M-60',
        'razor': 'Pattern: diagonal slash marks, R-80 M+120',
        // --- Expansion Pack Specials ---
        'oil_slick': 'Special: rainbow oil pools + variable roughness',
        'galaxy': 'Special: deep space nebula + star clusters',
        'rust': 'Special: progressive oxidation + no clearcoat',
        'neon_glow': 'Special: UV reactive fluorescent glow',
        'weathered_paint': 'Special: faded peeling layers to primer',
    };
    chanEl.textContent = channelHints[finishId] || '';

    // Position popup to the left of the finish list item
    const rect = e.currentTarget.getBoundingClientRect();
    popup.style.left = Math.max(10, rect.left - 270) + 'px';
    popup.style.top = Math.max(10, Math.min(rect.top - 30, window.innerHeight - 300)) + 'px';
    popup.classList.add('visible');
}

function hideFinishPopup() {
    finishPopupTimeout = setTimeout(() => {
        document.getElementById('finishPopup').classList.remove('visible');
    }, 100);
}

// ===== SWATCH HOVER POPUP (for swatch picker grid) =====
let _shpTimeout = null;
const _shpPreviewCache = {}; // Separate cache for 140x140 popup previews

function showSwatchHoverPopup(el) {
    clearTimeout(_shpTimeout);
    const finishId = el.getAttribute('data-finish-id');
    if (!finishId) return;

    const popup = document.getElementById('swatchHoverPopup');
    const canvas = document.getElementById('shpCanvas');
    const nameEl = document.getElementById('shpName');
    const descEl = document.getElementById('shpDesc');
    const catEl = document.getElementById('shpCat');

    // Render 140x140 preview via server swatch (async, instant update)
    const pctx = canvas.getContext('2d');
    const swatchUrl = getSwatchUrl(finishId, '888888');
    if (swatchUrl) {
        pctx.fillStyle = '#1a1a1a';
        pctx.fillRect(0, 0, 140, 140);
        const cacheKey = finishId + '_shp';
        if (_shpPreviewCache[cacheKey]) {
            pctx.drawImage(_shpPreviewCache[cacheKey], 0, 0, 140, 140);
        } else {
            const img = new Image();
            img.onload = () => {
                pctx.clearRect(0, 0, 140, 140);
                pctx.drawImage(img, 0, 0, 140, 140);
                _shpPreviewCache[cacheKey] = img;
            };
            img.src = swatchUrl.replace('size=48', 'size=140');
        }
    } else {
        const cacheKey = finishId + '_shp';
        if (_shpPreviewCache[cacheKey]) {
            pctx.putImageData(_shpPreviewCache[cacheKey], 0, 0);
        } else {
            renderPatternPreview(pctx, 140, 140, finishId);
            _shpPreviewCache[cacheKey] = pctx.getImageData(0, 0, 140, 140);
        }
    }

    // Lookup finish info
    const finish = BASES.find(f => f.id === finishId)
        || PATTERNS.find(f => f.id === finishId)
        || MONOLITHICS.find(f => f.id === finishId);

    nameEl.textContent = finish ? finish.name : finishId;
    descEl.textContent = el.getAttribute('data-desc') || (finish ? finish.desc : '');

    // Category label
    if (BASES.some(f => f.id === finishId)) catEl.textContent = 'Base Material';
    else if (PATTERNS.some(f => f.id === finishId)) catEl.textContent = 'Pattern';
    else if (finishId.startsWith('clr_')) catEl.textContent = 'Solid Color';
    else if (finishId.startsWith('grad_') || finishId.startsWith('gradm_') || finishId.startsWith('grad3_')) catEl.textContent = 'Gradient';
    else if (finishId.startsWith('ghostg_')) catEl.textContent = 'Ghost Gradient';
    else if (finishId.startsWith('cs_')) catEl.textContent = 'Color Shift';
    else if (finishId.startsWith('mc_')) catEl.textContent = 'Multi-Color';
    else catEl.textContent = 'Special';

    // Position popup near the swatch
    const rect = el.getBoundingClientRect();
    let left = rect.right + 10;
    if (left + 230 > window.innerWidth) left = rect.left - 230;
    if (left < 5) left = 5;
    let top = rect.top - 40;
    if (top + 240 > window.innerHeight) top = window.innerHeight - 245;
    if (top < 5) top = 5;

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.style.display = 'block';
}

function hideSwatchHoverPopup() {
    _shpTimeout = setTimeout(() => {
        document.getElementById('swatchHoverPopup').style.display = 'none';
    }, 120);
}

// Delegate hover events on swatch picker grid (uses event delegation)
document.addEventListener('mouseenter', function (e) {
    if (!e.target || typeof e.target.closest !== 'function') return;
    const item = e.target.closest('.swatch-item[data-finish-id]');
    if (item && item.closest('#swatchPopupGrid')) {
        showSwatchHoverPopup(item);
    }
}, true);

document.addEventListener('mouseleave', function (e) {
    if (!e.target || typeof e.target.closest !== 'function') return;
    const item = e.target.closest('.swatch-item[data-finish-id]');
    if (item && item.closest('#swatchPopupGrid')) {
        hideSwatchHoverPopup();
    }
}, true);

// ===== SHOKKER API - Server Connectivity (v4.0 - Build 19: Origin-Based) =====
const ShokkerAPI = {
    // Build 19 FIX: Use the page's own origin instead of scanning ports.
    // The page is served BY the Flask server, so window.location.origin IS the server.
    // Port scanning caused a critical bug: if an old server process was still alive on a
    // lower port, ALL API calls would go to the stale server instead of the current one.
    baseUrl: window.location.origin || 'http://localhost:5001',
    online: false,
    config: null,
    _renderAbort: null,
    _portDiscovered: !!(window.location.origin && window.location.protocol === 'http:'),

    async discoverPort() {
        // Build 19: If loaded from HTTP (Electron app), the origin IS the server - no scanning needed
        if (window.location.protocol === 'http:') {
            this.baseUrl = window.location.origin;
            this._portDiscovered = true;
            console.log(`[ShokkerAPI] Using page origin: ${this.baseUrl} (no port scan needed)`);
            try {
                const res = await fetch(this.baseUrl + '/status', { signal: AbortSignal.timeout(2000) });
                return await res.json();
            } catch {
                return null;
            }
        }
        // Fallback: file:// or dev mode - scan ports
        for (let p = 5000; p <= 5010; p++) {
            try {
                const url = `http://localhost:${p}/status`;
                const res = await fetch(url, { signal: AbortSignal.timeout(800) });
                const data = await res.json();
                if (data.status === 'online') {
                    this.baseUrl = `http://localhost:${p}`;
                    this._portDiscovered = true;
                    console.log(`[ShokkerAPI] Server found on port ${p} (scan fallback)`);
                    return data;
                }
            } catch { /* try next port */ }
        }
        return null;
    },

    async checkStatus() {
        try {
            // First call: discover which port the server is on
            if (!this._portDiscovered) {
                const discovered = await this.discoverPort();
                if (discovered) {
                    this.online = true;
                    this.config = discovered.config || null;
                    this._lastStatusData = discovered;
                    if (discovered.license) {
                        licenseActive = discovered.license.active;
                        if (typeof updateLicenseUI === 'function') updateLicenseUI(discovered.license);
                    }
                    this.updateUI();
                    return discovered;
                }
                this.online = false;
                this.config = null;
                this.updateUI();
                return null;
            }
            const res = await fetch(this.baseUrl + '/status', { signal: AbortSignal.timeout(2000) });
            const data = await res.json();
            this.online = data.status === 'online';
            this.config = data.config || null;
            this._lastStatusData = data;
            // Sync license state from server status
            if (data.license) {
                licenseActive = data.license.active;
                if (typeof updateLicenseUI === 'function') updateLicenseUI(data.license);
            }
            this.updateUI();
            return data;
        } catch {
            this.online = false;
            this.config = null;
            this._portDiscovered = false; // Re-discover on next check
            this.updateUI();
            return null;
        }
    },

    cancelRender() {
        if (this._renderAbort) {
            this._renderAbort.abort();
            this._renderAbort = null;
            console.log('[ShokkerAPI] Render cancelled by user');
        }
    },

    async render(paintFile, zones, iracingId, seed, liveLink, extras) {
        // Create AbortController for this render
        this._renderAbort = new AbortController();
        const useCustomNumber = document.getElementById('useCustomNumberCheckbox')?.checked ?? true;
        const body = {
            paint_file: paintFile,
            zones: zones,
            iracing_id: iracingId,
            seed: seed || 51,
            live_link: liveLink || false,
            use_custom_number: useCustomNumber,
        };
        // Optional extras: helmet, suit, wear, export, output_dir
        if (extras) {
            if (extras.helmet_paint_file) body.helmet_paint_file = extras.helmet_paint_file;
            if (extras.suit_paint_file) body.suit_paint_file = extras.suit_paint_file;
            if (extras.wear_level !== undefined) body.wear_level = extras.wear_level;
            if (extras.export_zip) body.export_zip = true;
            if (extras.dual_spec) { body.dual_spec = true; body.night_boost = extras.night_boost || 0.7; }
            if (extras.output_dir) body.output_dir = extras.output_dir;
            if (extras.import_spec_map) body.import_spec_map = extras.import_spec_map;
        }
        const res = await fetch(this.baseUrl + '/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: this._renderAbort ? this._renderAbort.signal : undefined,
        });
        const data = await res.json();
        if (!res.ok && !data.error) data.error = `Server returned ${res.status}`;
        return data;
    },

    async resetBackup(paintFile, iracingId) {
        const res = await fetch(this.baseUrl + '/reset-backup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paint_file: paintFile, iracing_id: iracingId })
        });
        return await res.json();
    },

    async saveConfig(cfg) {
        const res = await fetch(this.baseUrl + '/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cfg),
        });
        return await res.json();
    },

    updateUI() {
        const dot = document.getElementById('serverStatus');
        const btn = document.getElementById('btnRender');
        const llRow = document.getElementById('liveLinkRow');
        if (dot) {
            dot.className = 'server-status ' + (this.online ? 'online' : 'offline');
            dot.title = this.online ? 'Server online' : 'Server offline - start server.py';
        }
        if (btn) {
            btn.textContent = this.online ? 'RENDER' : 'RENDER (Offline)';
            btn.style.opacity = this.online ? '1' : '0.5';
        }
        // Update combo count in header from server capabilities
        const comboEl = document.getElementById('comboCount');
        if (comboEl && this.online && this._lastStatusData) {
            const caps = this._lastStatusData.capabilities;
            if (caps) {
                const total = (caps.combination_count || 0) + (caps.monolithic_count || Object.keys(caps.monolithics || {}).length || 0);
                comboEl.textContent = total.toLocaleString() + '+ Combinations';
            }
        }
        if (llRow && this.config) {
            llRow.style.display = 'flex';
            const cb = document.getElementById('liveLinkCheckbox');
            const badge = document.getElementById('liveLinkBadge');
            if (cb) cb.checked = this.config.live_link_enabled || false;
            if (badge) badge.style.display = this.config.live_link_enabled ? 'inline' : 'none';
        }
        // Sync car file naming checkbox from saved config
        if (this.config) {
            const cnCb = document.getElementById('useCustomNumberCheckbox');
            if (cnCb) cnCb.checked = this.config.use_custom_number !== false;
        }
    },

    startPolling() {
        this.checkStatus();
        setInterval(() => this.checkStatus(), 10000);
    }
};

// ===== DISK CLEANUP =====
async function cleanupOldRenders() {
    if (!ShokkerAPI.online) { showToast('Server is offline!', true); return; }
    if (!confirm('Delete ALL old render job folders from output/? This frees disk space but removes cached render results.')) return;
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/cleanup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Cleaned ${data.deleted} render jobs, freed ${data.freed_mb}MB`);
        } else {
            showToast('Cleanup failed: ' + (data.error || 'unknown'), true);
        }
    } catch (e) {
        showToast('Cleanup error: ' + e.message, true);
    }
}

// ===== HELMET / SUIT BROWSE =====
function browseHelmetFile(input) {
    if (input.files && input.files[0]) {
        // For local file browsing, extract the path
        const fileName = input.files[0].name;
        // Try to build a path from the paint file's directory
        const paintFile = document.getElementById('paintFile').value.trim();
        if (paintFile) {
            const dir = paintFile.replace(/[/\\][^/\\]+$/, '');
            document.getElementById('helmetFile').value = dir + '/' + fileName;
        } else {
            document.getElementById('helmetFile').value = fileName;
        }
        showToast(`Helmet paint: ${fileName}`);
    }
}

function browseSuitFile(input) {
    if (input.files && input.files[0]) {
        const fileName = input.files[0].name;
        const paintFile = document.getElementById('paintFile').value.trim();
        if (paintFile) {
            const dir = paintFile.replace(/[/\\][^/\\]+$/, '');
            document.getElementById('suitFile').value = dir + '/' + fileName;
        } else {
            document.getElementById('suitFile').value = fileName;
        }
        showToast(`Suit paint: ${fileName}`);
    }
}

// ===== WEAR SLIDER =====
function updateWearDisplay(val) {
    const v = parseInt(val, 10);
    const valueEl = document.getElementById('wearValue');
    const descEl = document.getElementById('wearDesc');
    if (valueEl) valueEl.textContent = v;
    if (descEl) {
        if (v === 0) descEl.textContent = 'Fresh / Factory New';
        else if (v <= 10) descEl.textContent = 'Light use - micro-scratches only';
        else if (v <= 20) descEl.textContent = 'Weekend warrior - clearcoat fading';
        else if (v <= 40) descEl.textContent = 'Season worn - paint chips starting';
        else if (v <= 60) descEl.textContent = 'Battle scarred - visible edge wear';
        else if (v <= 80) descEl.textContent = 'Heavily worn - significant damage';
        else descEl.textContent = 'Destroyed - maximum wear & tear';
    }
}

function toggleNightBoostSlider() {
    const checked = document.getElementById('dualSpecCheckbox')?.checked;
    const row = document.getElementById('nightBoostRow');
    if (row) row.style.display = checked ? 'block' : 'none';
}

// ===== PBR MATERIAL VISUALIZER =====
function togglePbrVisualizer() {
    const sec = document.getElementById('pbrVisualizerSection');
    if (!sec) return;
    const show = sec.style.display === 'none';
    sec.style.display = show ? 'block' : 'none';
    if (show) updatePbrBall();
}

function setPbrPreset(m, r, c) {
    document.getElementById('pbrMetallic').value = m;
    document.getElementById('pbrRoughness').value = r;
    document.getElementById('pbrClearcoat').value = c;
    updatePbrBall();
}

function updatePbrBall() {
    const canvas = document.getElementById('pbrBallCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h / 2, radius = w / 2 - 4;

    const metallic = parseInt(document.getElementById('pbrMetallic').value);
    const roughness = parseInt(document.getElementById('pbrRoughness').value);
    const clearcoat = parseInt(document.getElementById('pbrClearcoat').value);

    document.getElementById('pbrMetallicVal').textContent = metallic;
    document.getElementById('pbrRoughnessVal').textContent = roughness;
    document.getElementById('pbrClearcoatVal').textContent = clearcoat;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // PBR ball simulation
    const mf = metallic / 255;   // 0-1
    const rf = roughness / 255;   // 0-1
    // iRacing clearcoat: 16=max shine, higher=duller
    const ccf = clearcoat <= 16 ? (1 - clearcoat / 16) : Math.max(0, 1 - (clearcoat - 16) / 239);

    const imgData = ctx.createImageData(w, h);
    const data = imgData.data;

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const dx = (x - cx) / radius;
            const dy = (y - cy) / radius;
            const dist2 = dx * dx + dy * dy;
            if (dist2 > 1) continue;

            const nz = Math.sqrt(1 - dist2);
            const nx = dx, ny = dy;

            // Light direction (upper-left)
            const lx = -0.4, ly = -0.6, lz = 0.7;
            const llen = Math.sqrt(lx * lx + ly * ly + lz * lz);
            const ndotl = Math.max(0, (nx * lx + ny * ly + nz * lz) / llen);

            // Specular (Blinn-Phong approximation)
            const hx = lx, hy = ly, hz = lz + 1;
            const hlen = Math.sqrt(hx * hx + hy * hy + hz * hz);
            const ndoth = Math.max(0, (nx * hx + ny * hy + nz * hz) / hlen);
            const specPower = Math.max(4, 200 * (1 - rf));
            const spec = Math.pow(ndoth, specPower);

            // Fresnel effect (metallic surfaces reflect more at glancing angles)
            const fresnel = Math.pow(1 - nz, 3) * mf;

            // Base color (use neutral gray as paint proxy)
            const baseColor = 0.45;
            // Metallic dims diffuse, boosts reflection
            const diffuse = baseColor * ndotl * (1 - mf * 0.6);
            const reflection = (spec * (0.3 + mf * 0.7) + fresnel * 0.4) * (1 - rf * 0.8);

            // Clearcoat adds a secondary specular highlight
            const ccSpec = ccf > 0 ? Math.pow(ndoth, 300) * ccf * 0.8 : 0;

            let r = Math.min(1, diffuse + reflection + ccSpec);
            let g = Math.min(1, diffuse + reflection + ccSpec);
            let b = Math.min(1, diffuse + reflection * 1.05 + ccSpec * 1.1);

            // Metallic tint - shift toward blue-ish for high metallic
            if (mf > 0.5) {
                const tint = (mf - 0.5) * 0.15;
                r -= tint * 0.3;
                b += tint * 0.2;
            }

            // Edge darkening (ambient occlusion approximation)
            const ao = 0.3 + 0.7 * nz;
            r *= ao; g *= ao; b *= ao;

            const idx = (y * w + x) * 4;
            data[idx] = Math.min(255, Math.max(0, r * 255)) | 0;
            data[idx + 1] = Math.min(255, Math.max(0, g * 255)) | 0;
            data[idx + 2] = Math.min(255, Math.max(0, b * 255)) | 0;
            data[idx + 3] = 255;
        }
    }
    ctx.putImageData(imgData, 0, 0);

    // Draw border circle
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.stroke();
}

// ===== FLEET MODE =====
let fleetCars = [];
let fleetModeActive = false;

function toggleFleetMode() {
    fleetModeActive = !fleetModeActive;
    const panel = document.getElementById('fleetPanel');
    const btn = document.getElementById('btnFleetToggle');
    if (panel) panel.style.display = fleetModeActive ? 'block' : 'none';
    if (btn) {
        btn.style.background = fleetModeActive ? 'rgba(255,170,0,0.15)' : 'transparent';
        btn.textContent = fleetModeActive ? 'Fleet Mode ON' : 'Fleet Mode';
    }
    if (fleetModeActive && fleetCars.length === 0) {
        addFleetCar();
    }
}

function addFleetCar() {
    const paintFile = document.getElementById('paintFile')?.value || '';
    const id = document.getElementById('iracingId')?.value || '';
    fleetCars.push({ name: `Car ${fleetCars.length + 1}`, paintFile: paintFile, iracingId: id });
    renderFleetList();
}

function removeFleetCar(idx) {
    fleetCars.splice(idx, 1);
    renderFleetList();
}

function renderFleetList() {
    const container = document.getElementById('fleetList');
    const count = document.getElementById('fleetCount');
    if (count) count.textContent = `(${fleetCars.length} cars)`;
    if (!container) return;
    container.innerHTML = fleetCars.map((car, i) => `
        <div class="batch-entry">
            <span style="color: var(--accent-gold); font-weight: 600; min-width: 14px;">${i + 1}</span>
            <input type="text" value="${car.name}" onchange="fleetCars[${i}].name=this.value" placeholder="Car name" style="max-width: 80px;">
            <input type="text" value="${car.paintFile}" onchange="fleetCars[${i}].paintFile=this.value" placeholder="Paint TGA path" title="Full path to paint TGA">
            <input type="text" value="${car.iracingId}" onchange="fleetCars[${i}].iracingId=this.value" placeholder="ID" style="max-width: 45px;" title="iRacing ID">
            <span class="batch-remove" onclick="removeFleetCar(${i})" title="Remove car">&times;</span>
        </div>
    `).join('');
}

async function doFleetRender() {
    if (!ShokkerAPI.online) { showToast('Server offline!', true); return; }
    if (fleetCars.length === 0) { showToast('Add at least one car to the fleet!', true); return; }

    const btn = document.getElementById('btnFleetRender');
    const progress = document.getElementById('fleetProgress');
    const results = document.getElementById('fleetResults');
    btn.disabled = true;
    progress.style.display = 'block';
    results.innerHTML = '';

    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    if (validZones.length === 0) { showToast('Set up zones first!', true); btn.disabled = false; progress.style.display = 'none'; return; }

    const serverZones = validZones.map(z => {
        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
        if (z.customSpec != null) zoneObj.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; if (z.patternStack?.length) { const st = z.patternStack.filter(l => l.id && l.id !== 'none'); if (st.length) zoneObj.pattern_stack = st.map(l => ({ id: l.id, opacity: (l.opacity ?? 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0, blend_mode: l.blendMode || 'normal' })); } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fm = MONOLITHICS.find(m => m.id === z.finish); if (_fm) { zoneObj.finish_colors = { c1: _fm.swatch || null, c2: _fm.swatch2 || null, c3: _fm.swatch3 || null, ghost: _fm.ghostPattern || null }; } if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase) { zoneObj.blend_base = z.blendBase; zoneObj.blend_dir = z.blendDir || 'horizontal'; zoneObj.blend_amount = (z.blendAmount ?? 50) / 100; }
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // Dual Layer Base Overlay
        if (z.secondBase && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = z.secondBaseNoiseScale || 24;
        }
        return zoneObj;
    });

    const extras = {};
    const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
    if (wearLevel > 0) extras.wear_level = wearLevel;
    if (importedSpecMapPath) extras.import_spec_map = importedSpecMapPath;

    for (let i = 0; i < fleetCars.length; i++) {
        const car = fleetCars[i];
        progress.textContent = `Rendering car ${i + 1}/${fleetCars.length}: ${car.name}...`;

        try {
            const result = await ShokkerAPI.render(car.paintFile, serverZones, car.iracingId, 51, false, extras);
            const urls = result.preview_urls || {};
            const paintUrl = Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet'));
            results.innerHTML += `
                <div class="batch-result-card">
                    ${paintUrl ? `<img src="${ShokkerAPI.baseUrl + paintUrl[1]}" alt="${car.name}">` : '<div style="height: 60px; background: #111; border-radius: 3px;"></div>'}
                    <div class="batch-result-name">${car.name}</div>
                </div>`;
        } catch (err) {
            results.innerHTML += `<div class="batch-result-card"><div class="batch-result-name" style="color: #ff4444;">FAILED: ${car.name}</div></div>`;
        }
    }

    progress.textContent = `Fleet render complete! ${fleetCars.length} cars rendered.`;
    btn.disabled = false;
}

// ===== SEASON MODE =====
let seasonJobs = [];
let seasonModeActive = false;

function toggleSeasonMode() {
    seasonModeActive = !seasonModeActive;
    const panel = document.getElementById('seasonPanel');
    const btn = document.getElementById('btnSeasonToggle');
    if (panel) panel.style.display = seasonModeActive ? 'block' : 'none';
    if (btn) {
        btn.style.background = seasonModeActive ? 'rgba(51,102,255,0.15)' : 'transparent';
        btn.textContent = seasonModeActive ? 'Season Mode ON' : 'Season Mode';
    }
    if (seasonModeActive && seasonJobs.length === 0) {
        addSeasonRace();
    }
}

function addSeasonRace() {
    seasonJobs.push({ name: `Race ${seasonJobs.length + 1}`, wearLevel: 0 });
    renderSeasonList();
}

function removeSeasonRace(idx) {
    seasonJobs.splice(idx, 1);
    renderSeasonList();
}

function renderSeasonList() {
    const container = document.getElementById('seasonList');
    const count = document.getElementById('seasonCount');
    if (count) count.textContent = `(${seasonJobs.length} races)`;
    if (!container) return;
    container.innerHTML = seasonJobs.map((job, i) => `
        <div class="batch-entry">
            <span style="color: var(--accent-blue); font-weight: 600; min-width: 14px;">${i + 1}</span>
            <input type="text" value="${job.name}" onchange="seasonJobs[${i}].name=this.value" placeholder="Race name" style="max-width: 100px;">
            <label style="font-size: 9px; color: var(--text-dim); min-width: 32px;">Wear:</label>
            <input type="range" min="0" max="100" value="${job.wearLevel}" oninput="seasonJobs[${i}].wearLevel=parseInt(this.value); this.nextElementSibling.textContent=this.value+'%'" style="width: 60px;">
            <span style="font-size: 9px; color: var(--accent-orange); min-width: 28px;">${job.wearLevel}%</span>
            <span class="batch-remove" onclick="removeSeasonRace(${i})" title="Remove race">&times;</span>
        </div>
    `).join('');
}

function quickFillSeasonWear() {
    if (seasonJobs.length < 2) { showToast('Add at least 2 races for wear progression!', true); return; }
    for (let i = 0; i < seasonJobs.length; i++) {
        seasonJobs[i].wearLevel = Math.round((i / (seasonJobs.length - 1)) * 100);
    }
    renderSeasonList();
    showToast(`Wear ramp: 0% to 100% across ${seasonJobs.length} races`);
}

async function doSeasonRender() {
    if (!ShokkerAPI.online) { showToast('Server offline!', true); return; }
    if (seasonJobs.length === 0) { showToast('Add at least one race!', true); return; }

    const paintFile = document.getElementById('paintFile')?.value.trim();
    const iracingId = document.getElementById('iracingId')?.value.trim();
    if (!paintFile) { showToast('Set paint file in Car Info!', true); return; }

    const btn = document.getElementById('btnSeasonRender');
    const progress = document.getElementById('seasonProgress');
    const results = document.getElementById('seasonResults');
    btn.disabled = true;
    progress.style.display = 'block';
    results.innerHTML = '';

    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    if (validZones.length === 0) { showToast('Set up zones first!', true); btn.disabled = false; progress.style.display = 'none'; return; }

    const serverZones = validZones.map(z => {
        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
        if (z.customSpec != null) zoneObj.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; if (z.patternStack?.length) { const st = z.patternStack.filter(l => l.id && l.id !== 'none'); if (st.length) zoneObj.pattern_stack = st.map(l => ({ id: l.id, opacity: (l.opacity ?? 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0, blend_mode: l.blendMode || 'normal' })); } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fm = MONOLITHICS.find(m => m.id === z.finish); if (_fm) { zoneObj.finish_colors = { c1: _fm.swatch || null, c2: _fm.swatch2 || null, c3: _fm.swatch3 || null, ghost: _fm.ghostPattern || null }; } if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase) { zoneObj.blend_base = z.blendBase; zoneObj.blend_dir = z.blendDir || 'horizontal'; zoneObj.blend_amount = (z.blendAmount ?? 50) / 100; }
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // Dual Layer Base Overlay
        if (z.secondBase && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = z.secondBaseNoiseScale || 24;
        }
        return zoneObj;
    });

    for (let i = 0; i < seasonJobs.length; i++) {
        const job = seasonJobs[i];
        progress.textContent = `Rendering race ${i + 1}/${seasonJobs.length}: ${job.name} (wear ${job.wearLevel}%)...`;

        const extras = {};
        if (job.wearLevel > 0) extras.wear_level = job.wearLevel;

        try {
            const result = await ShokkerAPI.render(paintFile, serverZones, iracingId, 51, false, extras);
            const urls = result.preview_urls || {};
            const paintUrl = Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet'));
            results.innerHTML += `
                <div class="batch-result-card">
                    ${paintUrl ? `<img src="${ShokkerAPI.baseUrl + paintUrl[1]}" alt="${job.name}">` : '<div style="height: 60px; background: #111; border-radius: 3px;"></div>'}
                    <div class="batch-result-name">${job.name}</div>
                    ${job.wearLevel > 0 ? `<span class="batch-wear-badge">WEAR ${job.wearLevel}%</span>` : ''}
                </div>`;
        } catch (err) {
            results.innerHTML += `<div class="batch-result-card"><div class="batch-result-name" style="color: #ff4444;">FAILED: ${job.name}</div></div>`;
        }
    }

    progress.textContent = `Season render complete! ${seasonJobs.length} races rendered.`;
    btn.disabled = false;
}

// ===== iRACING FOLDER HELPER =====
async function setOutputToIracingFolder() {
    // Auto-fill Save To with the iRacing paint folder from server config
    if (!ShokkerAPI.online) {
        showToast('Server offline - start server.py to use iRacing folder lookup', true);
        return;
    }
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/config');
        const cfg = await res.json();
        const activeCar = cfg.active_car;
        const carPath = cfg.car_paths?.[activeCar];
        if (carPath) {
            document.getElementById('outputDir').value = carPath;
            showToast(`Save To set to: ${activeCar} (${carPath})`);
        } else {
            showToast('No active car configured on server. Check shokker_config.json', true);
        }
    } catch (e) {
        showToast('Could not fetch config: ' + e.message, true);
    }
}

// ===== RENDER =====
function safeDoRender() {
    try {
        const btn = document.getElementById('btnRender');
        if (btn && btn.classList.contains('terminate-mode')) {
            // Button is in terminate mode - clicking it should cancel, not start new render
            ShokkerAPI.cancelRender();
            return;
        }
        if (btn && btn.textContent.includes('RENDERING')) {
            showToast('Already rendering - please wait...', true);
            return;
        }
        if (!ShokkerAPI.online) {
            showToast('Server appears offline - rechecking...', true);
            // Force recheck, then try render if now online
            ShokkerAPI.checkStatus().then(() => {
                if (ShokkerAPI.online) {
                    showToast('Server is back! Starting render...');
                    doRender();
                } else {
                    showToast('Server is offline. Start server.py first!', true);
                }
            });
            return;
        }
        doRender();
    } catch (e) {
        console.error('[safeDoRender] Error:', e);
        showToast('Error starting render: ' + e.message, true);
    }
}

async function doRender() {
    console.log('[doRender] Starting render... baseUrl=' + ShokkerAPI.baseUrl + ' origin=' + window.location.origin + ' online=' + ShokkerAPI.online);
    if (!ShokkerAPI.online) { showToast('Server is offline! Start server.py first.', true); return; }

    // License gate - disabled for Alpha testing
    // if (!licenseActive) {
    //     showToast('License required for full renders. Enter your key in Settings.', true);
    //     const settingsPanel = document.getElementById('settingsPanel');
    //     if (settingsPanel) settingsPanel.style.display = '';
    //     const licenseInput = document.getElementById('licenseKeyInput');
    //     if (licenseInput) { licenseInput.focus(); licenseInput.scrollIntoView({behavior:'smooth', block:'center'}); }
    //     return;
    // }

    const paintFile = document.getElementById('paintFile').value.trim();
    const iracingId = document.getElementById('iracingId').value.trim();
    if (!paintFile) { showToast('Set the Source Paint path in the header bar!', true); return; }
    // Quick check: warn if path looks like just a filename (no directory)
    if (!paintFile.includes('/') && !paintFile.includes('\\')) {
        showToast('Source Paint needs a FULL path (e.g. C:\\Users\\You\\Documents\\iRacing\\paint\\carname\\car_num_12345.tga), not just a filename!', true);
        return;
    }

    // Build zone configs for the server
    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    console.log('[doRender] Valid zones:', validZones.length, '/', zones.length, 'total');
    if (validZones.length === 0) {
        // Debug: show why zones were invalid
        const debugInfo = zones.map((z, i) => `Zone${i + 1}[${z.name}]: base=${z.base} finish=${z.finish} color=${z.color} colorMode=${z.colorMode}`).join('\n');
        console.warn('[doRender] No valid zones! Zone details:\n' + debugInfo);
        showToast('At least one zone needs a finish AND a color! Check that each zone has both set.', true);
        return;
    }

    const serverZones = validZones.map(z => {
        const zoneObj = {
            name: z.name,
            color: formatColorForServer(z.color, z),
            intensity: z.intensity,
        };
        // Custom intensity curve overrides
        if (z.customSpec != null) {
            zoneObj.custom_intensity = {
                spec: z.customSpec,
                paint: z.customPaint,
                bright: z.customBright,
            };
        }
        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) {
            zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
        }
        if (z.base) {
            zoneObj.base = z.base;
            zoneObj.pattern = z.pattern || 'none';
            if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
            if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation;
            if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
            // Pattern stack: convert opacity 0-100 to 0.0-1.0
            if (z.patternStack && z.patternStack.length > 0) {
                const stack = z.patternStack.filter(l => l.id && l.id !== 'none');
                if (stack.length > 0) {
                    zoneObj.pattern_stack = stack.map(l => ({
                        id: l.id,
                        opacity: (l.opacity != null ? l.opacity : 100) / 100,
                        scale: l.scale || 1.0,
                        rotation: l.rotation || 0,
                    }));
                }
            }
        } else if (z.finish) {
            zoneObj.finish = z.finish;
            // Send rotation for the finish itself (gradient direction, etc.)
            // baseRotation is the visible "Base Rotate" slider for finishes; rotation is pattern-only
            const _finishRot = z.baseRotation || z.rotation || 0;
            if (_finishRot && _finishRot !== 0) zoneObj.rotation = _finishRot;
            // Send color data for server-side fallback rendering
            const _fMono = MONOLITHICS.find(m => m.id === z.finish);
            if (_fMono) {
                zoneObj.finish_colors = {
                    c1: _fMono.swatch || null,
                    c2: _fMono.swatch2 || null,
                    c3: _fMono.swatch3 || null,
                    ghost: _fMono.ghostPattern || null,
                };
            }
            // Pattern overlay on monolithic - send pattern data if set
            if (z.pattern && z.pattern !== 'none') {
                zoneObj.pattern = z.pattern;
                if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
                if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
            }
        }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase) { zoneObj.blend_base = z.blendBase; zoneObj.blend_dir = z.blendDir || 'horizontal'; zoneObj.blend_amount = (z.blendAmount ?? 50) / 100; console.log(`[doRender v6.1 BLEND] Zone "${z.name}" => blend_base=${z.blendBase}, dir=${zoneObj.blend_dir}, amount=${zoneObj.blend_amount}`); } else { console.log(`[doRender v6.1 BLEND] Zone "${z.name}" => NO blendBase (value: "${z.blendBase}")`); }
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // Dual Layer Base Overlay
        if (z.secondBase && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = z.secondBaseNoiseScale || 24;
        }
        // Region mask RLE
        if (z.regionMask && z.regionMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc) { zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height); }
        }
        // Spatial mask RLE (include/exclude refinement)
        if (z.spatialMask && z.spatialMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc) { zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height); }
        }
        return zoneObj;
    });

    const liveLink = document.getElementById('liveLinkCheckbox')?.checked || false;

    // Gather extras (helmet, suit, wear, export, output folder)
    const extras = {};
    const outputDir = document.getElementById('outputDir').value.trim();
    const helmetFile = document.getElementById('helmetFile')?.value.trim();
    const suitFile = document.getElementById('suitFile')?.value.trim();
    const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
    const exportZip = document.getElementById('exportZipCheckbox')?.checked || false;
    if (outputDir) extras.output_dir = outputDir;
    if (helmetFile) extras.helmet_paint_file = helmetFile;
    if (suitFile) extras.suit_paint_file = suitFile;
    if (wearLevel > 0) extras.wear_level = wearLevel;
    if (exportZip) extras.export_zip = true;
    const dualSpec = document.getElementById('dualSpecCheckbox')?.checked || false;
    if (dualSpec) {
        extras.dual_spec = true;
        extras.night_boost = parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7');
    }

    // Import spec map (merge mode)
    if (importedSpecMapPath) extras.import_spec_map = importedSpecMapPath;

    // Show progress
    const btn = document.getElementById('btnRender');
    const bar = document.getElementById('renderProgress');
    const barInner = document.getElementById('renderProgressBar');
    const zoneCount = serverZones.length;
    btn.textContent = `RENDERING ${zoneCount} ZONE${zoneCount > 1 ? 'S' : ''}...`;
    btn.style.opacity = '0.5';
    btn.style.pointerEvents = 'none';
    bar.classList.add('active');
    barInner.style.width = '10%';
    startRenderTimer();
    // After 3 seconds, enable TERMINATE mode on the button
    const _terminateTimeout = setTimeout(() => {
        btn.classList.add('terminate-mode');
        btn.textContent = 'TERMINATE RENDER';
        btn.onclick = function () {
            ShokkerAPI.cancelRender();
            btn.textContent = 'CANCELLING...';
            btn.classList.remove('terminate-mode');
            btn.style.opacity = '0.5';
            btn.style.pointerEvents = 'none';
        };
    }, 3000);
    // Simulate progress stepping (visual feedback while server works)
    let _progStep = 10;
    const _progInterval = setInterval(() => {
        _progStep = Math.min(_progStep + Math.random() * 8, 85);
        barInner.style.width = _progStep + '%';
    }, 400);

    try {
        const result = await ShokkerAPI.render(paintFile, serverZones, iracingId, 51, liveLink, extras);
        clearInterval(_progInterval);
        stopRenderTimer();
        barInner.style.width = '100%';

        if (result.success) {
            let msg = `Rendered ${result.zone_count} zones in ${result.elapsed_seconds}s`;
            if (result.includes?.helmet) msg += ' + helmet';
            if (result.includes?.suit) msg += ' + suit';
            if (result.includes?.wear) msg += ` (wear ${result.wear_level})`;
            if (result.output_dir?.success) {
                msg += ` | Saved to ${result.output_dir.pushed_files?.length || 0} files!`;
            } else if (result.output_dir?.error) {
                msg += ' | OUTPUT FOLDER ERROR: ' + result.output_dir.error;
            }
            if (result.live_link?.success) {
                msg += ' | Live Link active!';
            }
            showToast(msg);
            RenderNotify.onRenderComplete(true, result.elapsed_seconds, result.zone_count);

            // Show both previews in the results panel (NOT on the source canvas)
            showRenderResults(result);
        } else if (result.license_required) {
            showToast('License required for full renders. Open Settings to enter your key.', true);
            licenseActive = false;
            RenderNotify.onRenderComplete(false, 0, 0);
        } else {
            showToast('Render failed: ' + (result.error || 'unknown'), true);
            RenderNotify.onRenderComplete(false, 0, 0);
        }
    } catch (e) {
        clearInterval(_progInterval);
        stopRenderTimer();
        if (e.name === 'AbortError') {
            showToast('Render terminated by user.', false);
        } else {
            showToast('Render error: ' + e.message, true);
        }
        RenderNotify.onRenderComplete(false, 0, 0);
    } finally {
        clearTimeout(_terminateTimeout);
        ShokkerAPI._renderAbort = null;
        setTimeout(() => {
            btn.textContent = 'RENDER';
            btn.classList.remove('terminate-mode');
            btn.style.opacity = '1';
            btn.style.pointerEvents = '';
            btn.onclick = function () { safeDoRender(); };
            bar.classList.remove('active');
            barInner.style.width = '0%';
        }, 1500);
    }
}

function formatColorForServer(color, zone) {
    if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
        return zone.colors.map(c => ({ color_rgb: c.color_rgb, tolerance: c.tolerance || 40 }));
    }
    if (zone.colorMode === 'picker' && zone.pickerColor) {
        const hex = zone.pickerColor;
        const r = parseInt(hex.substr(1, 2), 16);
        const g = parseInt(hex.substr(3, 2), 16);
        const b = parseInt(hex.substr(5, 2), 16);
        return { color_rgb: [r, g, b], tolerance: zone.pickerTolerance || 40 };
    }
    if (typeof color === 'string') return color;
    if (color && typeof color === 'object' && !Array.isArray(color)) return color;
    return 'everything';
}

function showRenderResults(result) {
    // Stop render pulse after first successful render
    hasRenderedOnce = true;
    const renderBtn = document.getElementById('btnRender');
    if (renderBtn) renderBtn.classList.remove('pulse');

    // Track job ID for one-click deploy
    lastRenderedJobId = result.job_id || null;
    // Show deploy row and load car list
    // Deploy row removed - render button handles everything
    // const deployRow = document.getElementById('renderDeployRow');
    // if (deployRow && lastRenderedJobId) {
    //     deployRow.style.display = 'block';
    //     document.getElementById('deployStatus').textContent = '';
    //     loadIracingCars();
    // }

    // Show paint + spec previews in the results panel WITHOUT touching the source canvas
    const panel = document.getElementById('renderResultsPanel');
    const paintImg = document.getElementById('renderPaintPreview');
    const specImg = document.getElementById('renderSpecPreview');
    const elapsed = document.getElementById('renderElapsed');
    const llMsg = document.getElementById('renderLiveLinkMsg');

    if (!panel) return;

    // Find preview URLs from the result
    const urls = result.preview_urls || {};
    const paintUrl = Object.entries(urls).find(([k]) => k.includes('paint') && !k.includes('helmet') && !k.includes('suit'));
    const specUrl = Object.entries(urls).find(([k]) => k.includes('spec') && !k.includes('helmet') && !k.includes('suit'));

    const cacheBust = '?v=' + (window.APP_SESSION_ID || Date.now());
    if (paintImg && paintUrl) paintImg.src = ShokkerAPI.baseUrl + paintUrl[1] + cacheBust;
    if (specImg && specUrl) specImg.src = ShokkerAPI.baseUrl + specUrl[1] + cacheBust;

    // Load rendered paint for Before/After compare mode
    if (paintUrl) {
        loadRenderedImageForCompare(ShokkerAPI.baseUrl + paintUrl[1] + cacheBust);
    }

    // Elapsed + zone info
    let elapsedText = `${result.elapsed_seconds}s | ${result.zone_count} zones`;
    if (elapsed) elapsed.textContent = elapsedText;

    // Wear badge
    const wearBadge = document.getElementById('renderWearBadge');
    if (wearBadge) {
        if (result.includes?.wear && result.wear_level > 0) {
            wearBadge.textContent = `WEAR: ${result.wear_level}%`;
            wearBadge.style.display = 'inline-block';
        } else {
            wearBadge.style.display = 'none';
        }
    }

    // Helmet + Suit previews
    const helmetSuitRow = document.getElementById('renderHelmetSuitRow');
    const helmetCol = document.getElementById('renderHelmetCol');
    const suitCol = document.getElementById('renderSuitCol');
    const helmetImg = document.getElementById('renderHelmetPreview');
    const suitImg = document.getElementById('renderSuitPreview');

    let showExtras = false;
    if (helmetCol && helmetImg) {
        const helmetUrl = Object.entries(urls).find(([k]) => k.includes('helmet'));
        if (result.includes?.helmet && helmetUrl) {
            helmetImg.src = ShokkerAPI.baseUrl + helmetUrl[1] + cacheBust;
            helmetCol.style.display = 'block';
            showExtras = true;
        } else {
            helmetCol.style.display = 'none';
        }
    }
    if (suitCol && suitImg) {
        const suitUrl = Object.entries(urls).find(([k]) => k.includes('suit'));
        if (result.includes?.suit && suitUrl) {
            suitImg.src = ShokkerAPI.baseUrl + suitUrl[1] + cacheBust;
            suitCol.style.display = 'block';
            showExtras = true;
        } else {
            suitCol.style.display = 'none';
        }
    }
    if (helmetSuitRow) helmetSuitRow.style.display = showExtras ? 'flex' : 'none';

    // Night spec preview
    const nightRow = document.getElementById('renderNightRow');
    const nightImg = document.getElementById('renderNightPreview');
    if (nightRow && nightImg) {
        const nightUrl = Object.entries(urls).find(([k]) => k.includes('spec_night') && !k.includes('helmet') && !k.includes('suit'));
        if (nightUrl) {
            nightImg.src = ShokkerAPI.baseUrl + nightUrl[1] + cacheBust;
            nightRow.style.display = 'flex';
        } else {
            nightRow.style.display = 'none';
        }
    }

    // Export ZIP link
    const zipRow = document.getElementById('renderZipRow');
    const zipLink = document.getElementById('renderZipLink');
    if (zipRow && zipLink) {
        if (result.export_zip_url) {
            zipLink.href = ShokkerAPI.baseUrl + result.export_zip_url;
            zipRow.style.display = 'block';
        } else {
            zipRow.style.display = 'none';
        }
    }

    // Output directory status
    if (llMsg) {
        let msgParts = [];
        // Show output_dir status (primary output)
        if (result.output_dir?.success) {
            msgParts.push(`<span style="color:var(--accent-green)"><strong>&#10003; Saved ${result.output_dir.pushed_files?.length || 0} files</strong> to <code>${result.output_dir.path}</code></span>`);
        } else if (result.output_dir?.error) {
            msgParts.push(`<span style="color:#ff4444"><strong>&#10007; Output Error:</strong> ${result.output_dir.error}</span>`);
        }
        // Show live link status
        if (result.live_link?.success) {
            // Show the actual output path instead of config car name
            const llPath = result.live_link.path || result.live_link.car || '';
            const llFolder = llPath.replace(/\\/g, '/').split('/').pop() || result.live_link.car;
            msgParts.push(`<span style="color:var(--accent-blue)"><strong>Live Link:</strong> Pushed to <code>${llFolder}</code> - Alt+Tab + Ctrl+R!</span>`);
        } else if (result.live_link?.error && !result.output_dir?.success) {
            // Only show live link error if output_dir didn't succeed either
            msgParts.push(`<span style="color:var(--text-dim)">Live Link: ${result.live_link.error}</span>`);
        }
        if (msgParts.length > 0) {
            llMsg.style.display = 'block';
            llMsg.style.borderColor = result.output_dir?.success ? 'var(--accent-green)' : 'var(--accent)';
            llMsg.innerHTML = msgParts.join('<br>');
        } else {
            // No output_dir and no live_link - warn user
            llMsg.style.display = 'block';
            llMsg.style.borderColor = 'var(--accent-gold)';
            llMsg.style.color = 'var(--accent-gold)';
            llMsg.innerHTML = '<strong>&#9888; No output folder set!</strong> Set the "iRacing Folder" path in Car Info to save files. Previews are still available below.';
        }
    }

    panel.style.display = 'block';

    // Push to render history
    try {
        const paintUrlFull = paintUrl ? (ShokkerAPI.baseUrl + paintUrl[1]) : '';
        const specUrlFull = specUrl ? (ShokkerAPI.baseUrl + specUrl[1]) : '';
        const summary = zones.map(z => {
            if (z.finish) return `${z.name}: ${z.finish}`;
            if (z.base) return `${z.name}: ${z.base}${z.pattern && z.pattern !== 'none' ? '+' + z.pattern : ''}`;
            return z.name;
        }).join(' | ');
        renderHistory.unshift({
            job_id: result.job_id || '',
            timestamp: Date.now(),
            elapsed_seconds: result.elapsed_seconds || 0,
            zone_count: result.zone_count || zones.length,
            paint_url: paintUrlFull,
            spec_url: specUrlFull,
            zones_summary: summary,
            zoneSnapshot: JSON.parse(JSON.stringify(zones.map(z => ({
                name: z.name, base: z.base, pattern: z.pattern, finish: z.finish,
                intensity: z.intensity, customSpec: z.customSpec, customPaint: z.customPaint,
                customBright: z.customBright, color: z.color, colorMode: z.colorMode,
                pickerColor: z.pickerColor, pickerTolerance: z.pickerTolerance,
                colors: z.colors, scale: z.scale, patternOpacity: z.patternOpacity,
                patternStack: z.patternStack, wear: z.wear, muted: z.muted,
                ccQuality: z.ccQuality, blendBase: z.blendBase, blendDir: z.blendDir,
                blendAmount: z.blendAmount, usePaintReactive: z.usePaintReactive, paintReactiveColor: z.paintReactiveColor,
            }))))
        });
        if (renderHistory.length > MAX_RENDER_HISTORY) renderHistory.pop();
        updateHistoryStrip();
    } catch (e) { console.warn('History push failed:', e); }
}

function closeRenderResults() {
    const panel = document.getElementById('renderResultsPanel');
    if (panel) panel.style.display = 'none';
}

// ===== ONE-CLICK DEPLOY TO iRACING =====
let lastRenderedJobId = null;

async function loadIracingCars() {
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/iracing-cars');
        const data = await res.json();
        const sel = document.getElementById('deployCarSelect');
        if (!sel || !data.cars) return;
        let html = '<option value="">Select car folder...</option>';
        data.cars.forEach(c => {
            html += `<option value="${c.name}" title="${c.path}">${c.name} (${c.tga_count} files)</option>`;
        });
        sel.innerHTML = html;
        // Try to auto-select based on current paint file path
        const paintPath = document.getElementById('paintFile')?.value || '';
        if (paintPath) {
            const parts = paintPath.replace(/\\/g, '/').split('/');
            // Look for car folder name in the path
            for (const car of data.cars) {
                if (parts.includes(car.name)) {
                    sel.value = car.name;
                    break;
                }
            }
        }
    } catch (e) {
        console.warn('Could not load iRacing cars:', e);
    }
}

async function deployToIracing() {
    const sel = document.getElementById('deployCarSelect');
    const status = document.getElementById('deployStatus');
    const carFolder = sel?.value;
    if (!carFolder) {
        showToast('Select a car folder first', true);
        return;
    }
    if (!lastRenderedJobId) {
        showToast('No render available to deploy', true);
        return;
    }
    const iracingId = document.getElementById('iracingId')?.value?.trim() || '00000';
    status.textContent = 'Deploying...';
    status.style.color = 'var(--accent-blue)';
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/deploy-to-iracing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: lastRenderedJobId, car_folder: carFolder, iracing_id: iracingId })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = `Deployed ${data.deployed.length} files to ${carFolder}. Alt+Tab to iRacing, press Ctrl+R!`;
            status.style.color = 'var(--success)';
            showToast(`Deployed to iRacing! ${data.deployed.length} files → ${carFolder}`);
        } else {
            status.textContent = data.error || 'Deploy failed';
            status.style.color = 'var(--error)';
            showToast('Deploy failed: ' + (data.error || 'Unknown error'), true);
        }
    } catch (e) {
        status.textContent = 'Server offline';
        status.style.color = 'var(--error)';
        showToast('Deploy failed - server offline', true);
    }
}

function copyTPDescription() {
    const lines = ['═══ Made with Shokker Paint Booth ═══', ''];
    const wearSlider = document.getElementById('wearSlider');
    const globalWear = wearSlider ? parseInt(wearSlider.value) : 0;

    for (const z of zones) {
        let finishName = '';
        if (z.finish) {
            const mono = MONOLITHICS.find(m => m.id === z.finish);
            finishName = mono ? mono.name + ' (Monolithic)' : z.finish;
        } else if (z.base) {
            const baseObj = BASES.find(b => b.id === z.base);
            const patObj = z.pattern && z.pattern !== 'none' ? PATTERNS.find(p => p.id === z.pattern) : null;
            finishName = baseObj ? baseObj.name : z.base;
            if (patObj) finishName += ' + ' + patObj.name;
        }
        if (!finishName) finishName = 'No finish';

        let line = `▸ ${z.name}: ${finishName}`;
        if (z.intensity && z.intensity !== '100') line += ` [${z.intensity}%]`;
        if (z.scale && z.scale !== 1.0) line += ` (scale ${z.scale}x)`;
        const zoneWear = z.wear || 0;
        if (zoneWear > 0) line += ` | Wear: ${zoneWear}%`;
        lines.push(line);
    }

    if (globalWear > 0) {
        lines.push('');
        lines.push(`Global Wear: ${globalWear}%`);
    }

    lines.push('');
    lines.push('───────────────────────');
    lines.push('2,525 finishes | shokkerpaints.com');

    const text = lines.join('\n');

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Trading Paints description copied!');
        }).catch(() => {
            fallbackCopyTP(text);
        });
    } else {
        fallbackCopyTP(text);
    }
}

function fallbackCopyTP(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
        document.execCommand('copy');
        showToast('Trading Paints description copied!');
    } catch (e) {
        showToast('Could not copy - check browser permissions', true);
    }
    document.body.removeChild(ta);
}

// ===== RENDER HISTORY =====
function updateHistoryStrip() {
    const strip = document.getElementById('renderHistoryStrip');
    const container = document.getElementById('renderHistoryThumbs');
    if (!strip || !container) return;

    if (renderHistory.length === 0) {
        strip.style.display = 'none';
        return;
    }
    strip.style.display = 'block';

    let html = '';
    renderHistory.forEach((entry, idx) => {
        const age = Math.round((Date.now() - entry.timestamp) / 1000);
        const ageLabel = age < 60 ? `${age}s ago` : age < 3600 ? `${Math.round(age / 60)}m ago` : `${Math.round(age / 3600)}h ago`;
        const border = idx === 0 ? 'var(--success)' : 'var(--border)';
        html += `<div onclick="showHistoryItem(${idx})" ondblclick="restoreHistoryItem(${idx})" title="${entry.zones_summary}\n${ageLabel} | ${entry.elapsed_seconds}s | ${entry.zone_count} zones\nDouble-click to restore zone config"
            style="cursor:pointer; position:relative; border:1px solid ${border}; border-radius:3px; overflow:hidden; flex-shrink:0; width:48px; height:48px; transition:border-color 0.15s;">
            <img src="${entry.paint_url}" style="width:100%; height:100%; object-fit:cover;" loading="lazy" onerror="this.style.display='none'">
            <div style="position:absolute; bottom:0; left:0; right:0; background:rgba(0,0,0,0.7); font-size:7px; color:#aaa; text-align:center; padding:1px;">${ageLabel}</div>
        </div>`;
    });
    container.innerHTML = html;
}

function showHistoryItem(index) {
    const entry = renderHistory[index];
    if (!entry) return;

    const paintImg = document.getElementById('renderPaintPreview');
    const specImg = document.getElementById('renderSpecPreview');
    const elapsed = document.getElementById('renderElapsed');
    const panel = document.getElementById('renderResultsPanel');

    if (paintImg && entry.paint_url) paintImg.src = entry.paint_url;
    if (specImg && entry.spec_url) specImg.src = entry.spec_url;
    if (elapsed) elapsed.textContent = `${entry.elapsed_seconds}s | ${entry.zone_count} zones (history #${index + 1})`;
    if (panel) panel.style.display = 'block';

    // Load for compare mode too
    if (entry.paint_url) loadRenderedImageForCompare(entry.paint_url);

    showToast(`Loaded render #${index + 1} from history`);
}

function toggleLiveLink(enabled) {
    ShokkerAPI.saveConfig({ live_link_enabled: enabled }).then(res => {
        if (res.success) {
            const badge = document.getElementById('liveLinkBadge');
            if (badge) badge.style.display = enabled ? 'inline' : 'none';
            showToast(enabled ? 'iRacing Live Link enabled!' : 'Live Link disabled');
        }
    }).catch(() => showToast('Could not save config', true));
}

function toggleCustomNumber(enabled) {
    ShokkerAPI.saveConfig({ use_custom_number: enabled }).then(res => {
        if (res.success) {
            showToast(enabled ? 'Car files: car_num_XXXXX.tga (custom numbers)' : 'Car files: car_XXXXX.tga (no custom numbers)');
        }
    }).catch(() => showToast('Could not save config', true));
}

// ===== RENDER HISTORY GALLERY WITH COMPARE =====
let historyCompareA = -1;
let historyCompareB = -1;

function openHistoryGallery() {
    if (renderHistory.length === 0) { showToast('No render history yet', true); return; }

    historyCompareA = -1;
    historyCompareB = -1;

    let overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.id = 'historyGalleryOverlay';
    overlay.className = 'history-gallery-overlay';
    overlay.innerHTML = buildGalleryHTML();
    document.body.appendChild(overlay);
}

function buildGalleryHTML() {
    let cards = '';
    renderHistory.forEach((entry, idx) => {
        const age = Math.round((Date.now() - entry.timestamp) / 1000);
        const ageLabel = age < 60 ? `${age}s ago` : age < 3600 ? `${Math.round(age / 60)}m ago` : `${Math.round(age / 3600)}h ago`;
        const selA = idx === historyCompareA ? ' compare-selected' : '';
        const selB = idx === historyCompareB ? ' compare-selected' : '';
        const badge = idx === 0 ? '<span class="history-card-badge" style="background:rgba(0,255,136,0.2);color:var(--success);">LATEST</span>' : '';
        cards += `<div class="history-card${selA}${selB}" onclick="gallerySelectItem(${idx})" ondblclick="restoreHistoryItem(${idx})">
            ${badge}
            <img src="${entry.paint_url}" alt="Render #${idx + 1}" onerror="this.style.background='#222'">
            <div class="history-card-info">
                <div class="hc-time">${ageLabel} &middot; ${entry.elapsed_seconds}s &middot; ${entry.zone_count} zones</div>
                <div class="hc-summary" title="${entry.zones_summary}">${entry.zones_summary}</div>
            </div>
        </div>`;
    });

    const compareBar = (historyCompareA >= 0 && historyCompareB >= 0)
        ? `<div class="history-compare-bar">
            <span>Comparing #${historyCompareA + 1} vs #${historyCompareB + 1}</span>
            <button class="btn btn-sm" onclick="clearHistoryCompare()" style="font-size:9px;">Clear</button>
           </div>
           <div class="history-compare-view">
            <div class="history-compare-pane">
                <div class="compare-label">Render #${historyCompareA + 1}</div>
                <img src="${renderHistory[historyCompareA]?.paint_url}" alt="A">
                <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">${renderHistory[historyCompareA]?.zones_summary || ''}</div>
            </div>
            <div class="history-compare-pane">
                <div class="compare-label">Render #${historyCompareB + 1}</div>
                <img src="${renderHistory[historyCompareB]?.paint_url}" alt="B">
                <div style="font-size:9px;color:var(--text-dim);margin-top:4px;">${renderHistory[historyCompareB]?.zones_summary || ''}</div>
            </div>
           </div>`
        : '';

    const hint = historyCompareA < 0 ? 'Click to select for compare. Double-click to restore zone config.'
        : historyCompareB < 0 ? 'Click another render to compare. Double-click to restore.'
            : 'Comparing two renders. Double-click to restore zone config.';

    return `<div class="history-gallery-header">
        <h3>RENDER HISTORY GALLERY (${renderHistory.length})</h3>
        <span style="font-size:10px; color:var(--text-dim);">${hint}</span>
        <button class="btn btn-sm" onclick="closeHistoryGallery()" style="font-size:11px;">&times; Close</button>
    </div>
    <div class="history-gallery-body">${cards}</div>
    ${compareBar}`;
}

function gallerySelectItem(idx) {
    if (historyCompareA < 0) {
        historyCompareA = idx;
    } else if (historyCompareB < 0 && idx !== historyCompareA) {
        historyCompareB = idx;
    } else {
        // Reset and start new selection
        historyCompareA = idx;
        historyCompareB = -1;
    }
    // Re-render gallery
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}

function clearHistoryCompare() {
    historyCompareA = -1;
    historyCompareB = -1;
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.innerHTML = buildGalleryHTML();
}

function restoreHistoryItem(idx) {
    const entry = renderHistory[idx];
    if (!entry || !entry.zoneSnapshot) {
        showToast('No zone snapshot for this render', true);
        return;
    }
    if (!confirm(`Restore zone config from render #${idx + 1}? Your current zones will be replaced.`)) return;

    zones = entry.zoneSnapshot.map(z => ({
        name: z.name || 'Zone',
        color: z.color, base: z.base || null, pattern: z.pattern || 'none',
        finish: z.finish || null, intensity: z.intensity || '100',
        customSpec: z.customSpec != null ? z.customSpec : null,
        customPaint: z.customPaint != null ? z.customPaint : null,
        customBright: z.customBright != null ? z.customBright : null,
        colorMode: z.colorMode || 'none',
        pickerColor: z.pickerColor || '#3366ff',
        pickerTolerance: z.pickerTolerance || 40,
        colors: z.colors || [],
        regionMask: null,
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        scale: z.scale || 1.0, patternOpacity: z.patternOpacity ?? 100,
        patternStack: z.patternStack || [],
        wear: z.wear || 0, muted: z.muted || false,
    }));
    selectedZoneIndex = 0;
    renderZones();
    triggerPreviewRender();
    autoSave();
    closeHistoryGallery();
    showToast(`Restored zone config from render #${idx + 1}`);
}

function closeHistoryGallery() {
    const overlay = document.getElementById('historyGalleryOverlay');
    if (overlay) overlay.remove();
}

// ===== COMBINATION HINTS =====
const COMBO_HINTS = {
    "chrome+carbon_fiber": "Premium supercar look - mirror carbon weave",
    "chrome+diamond_plate": "Industrial chrome tread - tough and shiny",
    "matte+carbon_fiber": "Stealth carbon - the classic DTM look",
    "matte+hex_mesh": "Tactical honeycomb - military spec",
    "candy+holographic_flake": "Candy flake - classic hot rod show car",
    "candy+stardust": "Galaxy candy - deep space effect",
    "metallic+metal_flake": "Double metallic - maximum sparkle",
    "pearl+interference": "Chameleon pearl - color shifts everywhere",
    "chrome+lightning": "Thunder chrome - electric mirror",
    "blackout+carbon_fiber": "Full stealth carbon - invisible",
    "frozen+cracked_ice": "Arctic frozen - cracked ice crystal",
    "chrome+hologram": "Sci-fi chrome - futuristic scanlines",
};

function getComboHint(base, pattern) {
    if (!base || !pattern || pattern === 'none') return '';
    return COMBO_HINTS[base + '+' + pattern] || '';
}

// ===== DECAL & NUMBER OVERLAY SYSTEM =====
let decalLayers = []; // [{name, img: Image, canvas: offscreen, x, y, scale, rotation, opacity, visible}]
let draggingDecal = -1;
let decalDragOffset = { x: 0, y: 0 };

function importDecal() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/png,image/jpeg,image/webp,image/gif';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const img = new Image();
        img.onload = () => {
            decalLayers.push({
                name: file.name.replace(/\.[^.]+$/, ''),
                img: img,
                x: 100, y: 100,
                scale: 0.5,
                rotation: 0,
                opacity: 100,
                visible: true,
            });
            renderDecalList();
            renderDecalOverlay();
            showToast(`Decal added: ${file.name} (${img.width}x${img.height})`);
        };
        img.src = URL.createObjectURL(file);
    };
    input.click();
}

function removeDecal(idx) {
    decalLayers.splice(idx, 1);
    renderDecalList();
    renderDecalOverlay();
}

function setDecalScale(idx, val) {
    decalLayers[idx].scale = parseFloat(val);
    renderDecalOverlay();
}

function setDecalOpacity(idx, val) {
    decalLayers[idx].opacity = parseInt(val);
    renderDecalOverlay();
}

function setDecalRotation(idx, val) {
    decalLayers[idx].rotation = parseInt(val);
    renderDecalOverlay();
}

function toggleDecalVisibility(idx) {
    decalLayers[idx].visible = !decalLayers[idx].visible;
    renderDecalList();
    renderDecalOverlay();
}

function renderDecalList() {
    const list = document.getElementById('decalLayerList');
    const count = document.getElementById('decalCount');
    if (!list) return;
    if (count) count.textContent = `(${decalLayers.length} layer${decalLayers.length !== 1 ? 's' : ''})`;

    if (decalLayers.length === 0) {
        list.innerHTML = '<div style="font-size:9px; color:var(--text-dim); text-align:center; padding:4px;">No decals added</div>';
        return;
    }

    let html = '';
    decalLayers.forEach((d, idx) => {
        html += `<div class="decal-layer-row">
            <img class="decal-thumb" src="${d.img.src}" alt="${d.name}">
            <span class="decal-name" title="${d.name}">${d.name}</span>
            <div class="decal-controls">
                <span>Sc</span>
                <input type="range" min="0.05" max="2.0" step="0.05" value="${d.scale}" oninput="setDecalScale(${idx}, this.value)" title="Scale">
                <span>Op</span>
                <input type="range" min="0" max="100" value="${d.opacity}" oninput="setDecalOpacity(${idx}, this.value)" title="Opacity">
                <span>Rot</span>
                <input type="range" min="0" max="360" value="${d.rotation}" oninput="setDecalRotation(${idx}, this.value)" title="Rotation" style="width:35px;">
                <button onclick="toggleDecalVisibility(${idx})" title="Toggle visibility">${d.visible ? '&#x1F441;' : '&#x1F6AB;'}</button>
                <button onclick="removeDecal(${idx})" title="Remove">&times;</button>
            </div>
        </div>`;
    });
    list.innerHTML = html;
}

function renderDecalOverlay() {
    const regionCanvas = document.getElementById('regionCanvas');
    if (!regionCanvas) return;
    // We draw decals on the region canvas context as a visual overlay
    // The actual compositing happens in compositeDecalsForRender()
    // Just trigger a re-render of the region overlay which will include decals
    renderRegionOverlay();
}

function drawDecalsOnContext(ctx, w, h) {
    // Called from renderRegionOverlay to draw decal previews
    for (const d of decalLayers) {
        if (!d.visible || d.opacity <= 0) continue;
        ctx.save();
        ctx.globalAlpha = d.opacity / 100;
        const dw = d.img.width * d.scale;
        const dh = d.img.height * d.scale;
        ctx.translate(d.x + dw / 2, d.y + dh / 2);
        ctx.rotate(d.rotation * Math.PI / 180);
        ctx.drawImage(d.img, -dw / 2, -dh / 2, dw, dh);
        ctx.restore();
    }
}

function compositeDecalsForRender() {
    // Returns a canvas with decals composited onto the paint
    // Called before render to produce a modified paint TGA
    const paintCanvas = document.getElementById('paintCanvas');
    if (!paintCanvas || decalLayers.length === 0) return null;

    const c = document.createElement('canvas');
    c.width = paintCanvas.width;
    c.height = paintCanvas.height;
    const ctx = c.getContext('2d');
    ctx.drawImage(paintCanvas, 0, 0);
    drawDecalsOnContext(ctx, c.width, c.height);
    return c;
}

// Number generator
function openNumberGenerator() {
    const sec = document.getElementById('numberGenSection');
    if (sec) sec.style.display = sec.style.display === 'none' ? 'block' : 'none';
    updateNumberPreview();
}

function updateNumberPreview() {
    const text = document.getElementById('numberGenText')?.value || '23';
    const color = document.getElementById('numberGenColor')?.value || '#ffffff';
    const outline = document.getElementById('numberGenOutline')?.value || '#000000';
    const size = document.getElementById('numberGenSize')?.value || '120';
    const preview = document.getElementById('numberPreview');
    const sizeVal = document.getElementById('numberGenSizeVal');

    if (preview) {
        preview.textContent = text;
        preview.style.color = color;
        preview.style.textShadow = `2px 2px 0 ${outline}, -2px -2px 0 ${outline}, 2px -2px 0 ${outline}, -2px 2px 0 ${outline}`;
        preview.style.fontSize = Math.min(60, parseInt(size) / 2) + 'px';
    }
    if (sizeVal) sizeVal.textContent = size;
}

function addNumberDecal() {
    const text = document.getElementById('numberGenText')?.value || '23';
    const color = document.getElementById('numberGenColor')?.value || '#ffffff';
    const outline = document.getElementById('numberGenOutline')?.value || '#000000';
    const font = document.getElementById('numberGenFont')?.value || 'Helvetica';
    const size = parseInt(document.getElementById('numberGenSize')?.value || '120');

    // Render number to an offscreen canvas
    const c = document.createElement('canvas');
    const padding = size * 0.2;
    c.width = size * text.length * 0.7 + padding * 2;
    c.height = size + padding * 2;
    const ctx = c.getContext('2d');

    ctx.font = `900 ${size}px "${font}"`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Draw outline
    ctx.lineWidth = size * 0.06;
    ctx.strokeStyle = outline;
    ctx.strokeText(text, c.width / 2, c.height / 2);

    // Draw fill
    ctx.fillStyle = color;
    ctx.fillText(text, c.width / 2, c.height / 2);

    // Convert to image
    const img = new Image();
    img.onload = () => {
        decalLayers.push({
            name: `#${text}`,
            img: img,
            x: 200, y: 200,
            scale: 1.0,
            rotation: 0,
            opacity: 100,
            visible: true,
        });
        renderDecalList();
        renderDecalOverlay();
        showToast(`Number decal "${text}" added`);
    };
    img.src = c.toDataURL('image/png');
}

// Decal dragging on canvas (uses mousedown on paint canvas)
function checkDecalDrag(x, y) {
    for (let i = decalLayers.length - 1; i >= 0; i--) {
        const d = decalLayers[i];
        if (!d.visible) continue;
        const dw = d.img.width * d.scale;
        const dh = d.img.height * d.scale;
        if (x >= d.x && x <= d.x + dw && y >= d.y && y <= d.y + dh) {
            draggingDecal = i;
            decalDragOffset = { x: x - d.x, y: y - d.y };
            return true;
        }
    }
    return false;
}

function updateDecalDrag(x, y) {
    if (draggingDecal < 0) return;
    decalLayers[draggingDecal].x = x - decalDragOffset.x;
    decalLayers[draggingDecal].y = y - decalDragOffset.y;
    renderDecalOverlay();
}

function endDecalDrag() {
    draggingDecal = -1;
}

// ===== TEMPLATE LIBRARY (Pre-built Livery Layouts) =====
const LIVERY_TEMPLATES = [
    {
        name: "Racing Stripe",
        category: "Classic",
        desc: "Classic dual racing stripes. Body as Zone 1, stripes as Zone 2 with a bold pattern.",
        zones: [
            { name: "Body", base: "gloss", pattern: "none", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Racing Stripes", base: "metallic", pattern: "pinstripe", finish: null, intensity: "100", color: null, colorMode: "none", scale: 2.0 }
        ]
    },
    {
        name: "Two-Tone Split",
        category: "Classic",
        desc: "Upper/lower two-tone. Assign complementary colors to each zone for a clean split.",
        zones: [
            { name: "Upper Body", base: "gloss", pattern: "none", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Lower Body", base: "metallic", pattern: "none", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Accent Trim", base: "chrome", pattern: "none", finish: null, intensity: "50", color: null, colorMode: "none" }
        ]
    },
    {
        name: "GT3 Livery",
        category: "Motorsport",
        desc: "Classic GT3 race car layout with body, front/rear panels, and sponsor areas.",
        zones: [
            { name: "Main Body", base: "gloss", pattern: "none", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Hood/Roof", base: "matte", pattern: "carbon_fiber", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Side Panels", base: "metallic", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" },
            { name: "Accents", base: "chrome", pattern: "none", finish: null, intensity: "50", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Full Carbon",
        category: "Performance",
        desc: "Exposed carbon fiber everywhere with clear-coated accent areas.",
        zones: [
            { name: "Carbon Body", base: "matte", pattern: "carbon_fiber", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Gloss Panels", base: "gloss", pattern: "carbon_fiber", finish: null, intensity: "80", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Stealth Blackout",
        category: "Performance",
        desc: "Murdered-out matte black with subtle pattern texture. Dark and menacing.",
        zones: [
            { name: "Matte Body", finish: "blackout", intensity: "100", color: "everything", colorMode: "special" },
            { name: "Trim", base: "matte", pattern: "hex_mesh", finish: null, intensity: "50", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Chrome Show Car",
        category: "Show",
        desc: "Mirror chrome body with candy-colored accent panels.",
        zones: [
            { name: "Chrome Body", base: "chrome", pattern: "none", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Candy Accents", base: "candy", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Rally Livery",
        category: "Motorsport",
        desc: "Bold rally car look with large color blocks and sponsor-ready panels.",
        zones: [
            { name: "Primary Color", base: "gloss", pattern: "none", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Secondary Color", base: "gloss", pattern: "none", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Hood/Roof Accent", base: "matte", pattern: "forged_carbon", finish: null, intensity: "80", color: null, colorMode: "none" },
            { name: "Number Panels", base: "gloss", pattern: "none", finish: null, intensity: "50", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Gradient Fade",
        category: "Modern",
        desc: "Modern gradient look using multiple zones with transitioning finishes.",
        zones: [
            { name: "Front (Bright)", base: "metallic", pattern: "none", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Middle", base: "pearl", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" },
            { name: "Rear (Dark)", base: "matte", pattern: "none", finish: null, intensity: "50", color: null, colorMode: "none" }
        ]
    },
    {
        name: "NASCAR Cup",
        category: "Motorsport",
        desc: "Traditional oval stock car layout - large body panels with contrasting roof and bumpers.",
        zones: [
            { name: "Main Body", base: "metallic", pattern: "metal_flake", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Roof/Hood", base: "gloss", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" },
            { name: "Bumpers/Trim", base: "chrome", pattern: "none", finish: null, intensity: "50", color: null, colorMode: "none" },
            { name: "Number Area", base: "gloss", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Chameleon Exotic",
        category: "Show",
        desc: "Color-shifting chameleon body with brushed metal accents.",
        zones: [
            { name: "Chameleon Body", finish: "chameleon_emerald", intensity: "100", color: "everything", colorMode: "special" },
            { name: "Brushed Accents", base: "brushed_titanium", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Military Tactical",
        category: "Themed",
        desc: "Tactical military look with camo pattern and cerakote finish.",
        zones: [
            { name: "Camo Body", base: "cerakote", pattern: "multicam", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Tactical Panels", base: "cerakote", pattern: "hex_mesh", finish: null, intensity: "80", color: null, colorMode: "none" }
        ]
    },
    {
        name: "Tron / Sci-Fi",
        category: "Themed",
        desc: "Futuristic neon-grid look with dark base and glowing circuit patterns.",
        zones: [
            { name: "Dark Base", base: "matte", pattern: "none", finish: null, intensity: "100", color: "everything", colorMode: "special" },
            { name: "Neon Circuits", base: "gloss", pattern: "tron", finish: null, intensity: "100", color: null, colorMode: "none" },
            { name: "Glow Accents", base: "chrome", pattern: "circuit_board", finish: null, intensity: "80", color: null, colorMode: "none" }
        ]
    },
];

function openTemplateLibrary() {
    let overlay = document.getElementById('templateLibraryOverlay');
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.id = 'templateLibraryOverlay';
    overlay.className = 'template-library-overlay';

    const categories = [...new Set(LIVERY_TEMPLATES.map(t => t.category))];

    let cards = '';
    LIVERY_TEMPLATES.forEach((tmpl, idx) => {
        const zoneChips = tmpl.zones.map(z => {
            const finish = z.finish || (z.base ? z.base + (z.pattern && z.pattern !== 'none' ? '+' + z.pattern : '') : 'No finish');
            return `<span class="template-zone-chip">${z.name}: ${finish}</span>`;
        }).join('');
        cards += `<div class="template-card" onclick="applyLiveryTemplate(${idx})">
            <span class="template-card-badge">${tmpl.category}</span>
            <div class="template-card-title">${tmpl.name}</div>
            <div class="template-card-desc">${tmpl.desc}</div>
            <div class="template-card-zones">${zoneChips}</div>
        </div>`;
    });

    overlay.innerHTML = `
        <div class="template-library-header">
            <h3>LIVERY TEMPLATE LIBRARY (${LIVERY_TEMPLATES.length})</h3>
            <span style="font-size:10px;color:var(--text-dim);">Click a template to apply. Paint region masks with the brush tool after loading.</span>
            <button class="btn btn-sm" onclick="closeTemplateLibrary()" style="font-size:11px;">&times; Close</button>
        </div>
        <div class="template-library-body">${cards}</div>`;

    document.body.appendChild(overlay);
}

function applyLiveryTemplate(idx) {
    const tmpl = LIVERY_TEMPLATES[idx];
    if (!tmpl) return;
    if (zones.some(z => z.base || z.finish || z.color !== null)) {
        if (!confirm(`Apply "${tmpl.name}" template? Your current zones will be replaced.`)) return;
    }

    pushZoneUndo();
    zones = tmpl.zones.map(z => ({
        name: z.name || 'Zone',
        color: z.color || null,
        base: z.base || null,
        pattern: z.pattern || 'none',
        finish: z.finish || null,
        intensity: z.intensity || '100',
        customSpec: null, customPaint: null, customBright: null,
        colorMode: z.colorMode || 'none',
        pickerColor: z.pickerColor || '#3366ff',
        pickerTolerance: z.pickerTolerance || 40,
        colors: [],
        regionMask: null,
        lockBase: false, lockPattern: false, lockIntensity: false, lockColor: false,
        scale: z.scale || 1.0,
        patternOpacity: z.patternOpacity ?? 100,
        patternStack: z.patternStack || [],
        wear: z.wear || 0,
        muted: false,
    }));
    selectedZoneIndex = 0;
    renderZones();
    triggerPreviewRender();
    autoSave();
    closeTemplateLibrary();
    showToast(`Template loaded: "${tmpl.name}" - ${tmpl.zones.length} zones. Now assign colors with eyedropper or brush!`);
}

function closeTemplateLibrary() {
    const overlay = document.getElementById('templateLibraryOverlay');
    if (overlay) overlay.remove();
}

// ===== BEFORE/AFTER COMPARE MODE =====
let compareMode = false;
let compareDividerX = 0.5; // 0-1 fraction
let renderedImage = null;  // Image element of rendered paint
let compareDragging = false;

function toggleCompareMode() {
    if (!renderedImage) {
        showToast('Render first to use compare mode!', true);
        return;
    }
    compareMode = !compareMode;
    const btn = document.getElementById('btnCompare');
    if (btn) btn.classList.toggle('active', compareMode);

    if (compareMode) {
        compareDividerX = 0.5;
        drawCompareView();
        showToast('Compare mode: drag the divider to compare');
    } else {
        // Restore original canvas
        const canvas = document.getElementById('paintCanvas');
        if (canvas && paintImageData) {
            const ctx = canvas.getContext('2d');
            ctx.putImageData(paintImageData, 0, 0);
        }
    }
}

function drawCompareView() {
    const canvas = document.getElementById('paintCanvas');
    if (!canvas || !paintImageData || !renderedImage) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const divX = Math.round(compareDividerX * w);

    // Draw original on left
    ctx.putImageData(paintImageData, 0, 0);

    // Draw rendered on right
    ctx.save();
    ctx.beginPath();
    ctx.rect(divX, 0, w - divX, h);
    ctx.clip();
    ctx.drawImage(renderedImage, 0, 0, w, h);
    ctx.restore();

    // Divider line
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    ctx.shadowColor = 'rgba(0,0,0,0.5)';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    ctx.moveTo(divX, 0);
    ctx.lineTo(divX, h);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Handle circle
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(divX, h / 2, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Arrows on handle
    ctx.fillStyle = '#333';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('\u25C0\u25B6', divX, h / 2);

    // Labels
    ctx.font = 'bold 11px sans-serif';
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(8, 6, 68, 18);
    ctx.fillRect(divX + 8, 6, 72, 18);
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'left';
    ctx.fillText('ORIGINAL', 12, 17);
    ctx.fillText('RENDERED', divX + 12, 17);
}

function onCompareMouseDown(e) {
    if (!compareMode || !renderedImage) return;
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const x = (e.clientX - rect.left) * scaleX;
    const divX = compareDividerX * canvas.width;
    if (Math.abs(x - divX) < 20 * scaleX) {
        compareDragging = true;
        e.preventDefault();
    }
}

function onCompareMouseMove(e) {
    if (!compareDragging || !compareMode) return;
    const canvas = document.getElementById('paintCanvas');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    compareDividerX = Math.max(0.02, Math.min(0.98, x));
    drawCompareView();
}

function onCompareMouseUp() {
    compareDragging = false;
}

// Hook into canvas mouse events (added to existing canvas listeners)
document.addEventListener('mouseup', onCompareMouseUp);

function loadRenderedImageForCompare(url) {
    renderedImage = new Image();
    renderedImage.crossOrigin = 'anonymous';
    renderedImage.onload = () => {
        const btn = document.getElementById('btnCompare');
        if (btn) btn.style.display = 'inline-block';
    };
    renderedImage.src = url;
}

// ===== PRESET GALLERY =====
function openPresetGallery() {
    renderPresetGalleryCards();
    document.getElementById('presetGalleryOverlay').classList.add('active');
}

function closePresetGallery() {
    document.getElementById('presetGalleryOverlay').classList.remove('active');
}

function renderPresetGalleryCards() {
    const grid = document.getElementById('presetGalleryGrid');
    if (!grid) return;

    // Group presets by category
    const categoryOrder = ['Show Car', 'Clean', 'Aggressive', 'Special Effect', 'Themed'];
    const grouped = {};
    for (const [id, preset] of Object.entries(PRESETS)) {
        const cat = preset.category || 'Other';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push({ id, preset });
    }

    let html = '';
    const categoryIcons = {
        'Show Car': '🏆', 'Clean': '✨', 'Aggressive': '🔥',
        'Special Effect': '🌈', 'Themed': '🎯', 'Other': '🎨'
    };

    // Render in category order, then any remaining
    const allCats = [...categoryOrder, ...Object.keys(grouped).filter(c => !categoryOrder.includes(c))];
    for (const cat of allCats) {
        if (!grouped[cat] || grouped[cat].length === 0) continue;
        html += `<div style="grid-column:1/-1; padding:8px 4px 4px; margin-top:8px; border-bottom:1px solid var(--border); font-size:11px; font-weight:700; letter-spacing:1.5px; color:var(--accent); text-transform:uppercase;">
            ${categoryIcons[cat] || '🎨'} ${cat} <span style="font-weight:400; color:var(--text-dim); font-size:9px;">(${grouped[cat].length})</span>
        </div>`;

        for (const { id, preset } of grouped[cat]) {
            const swatches = preset.zones.map(z => {
                const baseSwatch = BASES.find(b => b.id === z.base)?.swatch || '#555';
                const patSwatch = z.pattern && z.pattern !== 'none' ? (PATTERNS.find(p => p.id === z.pattern)?.swatch || '') : '';
                return `<div class="preset-swatch" style="background:${baseSwatch};" title="${z.name}: ${z.base || '?'}${z.pattern && z.pattern !== 'none' ? ' + ' + z.pattern : ''}">
                    ${patSwatch ? `<div class="preset-swatch-stripe" style="background:${patSwatch};"></div>` : ''}
                </div>`;
            }).join('');

            html += `<div class="preset-card" onclick="applyPreset('${id}'); closePresetGallery();">
                <div class="preset-card-name">${preset.name}</div>
                <div class="preset-card-desc">${preset.desc}</div>
                <div class="preset-card-swatches">${swatches}</div>
                <div class="preset-card-zones">${preset.zones.length} zones</div>
            </div>`;
        }
    }
    grid.innerHTML = html;
}

// ===== FINISH BROWSER =====
let finishBrowserTargetZone = 0;

function openFinishBrowser(zoneIndex) {
    finishBrowserTargetZone = zoneIndex;
    // Populate filter dropdowns
    const baseSelect = document.getElementById('fbFilterBase');
    const patSelect = document.getElementById('fbFilterPattern');
    if (baseSelect && baseSelect.options.length <= 1) {
        BASES.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id; opt.textContent = b.name;
            baseSelect.appendChild(opt);
        });
    }
    if (patSelect && patSelect.options.length <= 1) {
        PATTERNS.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id; opt.textContent = p.name;
            patSelect.appendChild(opt);
        });
    }
    // Reset filters
    document.getElementById('fbFilterType').value = 'all';
    document.getElementById('fbFilterBase').value = 'all';
    document.getElementById('fbFilterPattern').value = 'all';
    document.getElementById('fbSearch').value = '';
    if (document.getElementById('fbSort')) document.getElementById('fbSort').value = 'default';
    finishBrowserFavOnly = false;
    const favBtn = document.getElementById('fbFavToggle');
    if (favBtn) favBtn.classList.remove('active');
    // Restore view toggle state
    const viewBtn = document.getElementById('fbViewToggle');
    if (viewBtn) viewBtn.innerHTML = finishBrowserCatalogView ? '⊞ Grid' : '☰ List';
    filterFinishBrowser();
    document.getElementById('finishBrowserOverlay').classList.add('active');
}

function closeFinishBrowser() {
    document.getElementById('finishBrowserOverlay').classList.remove('active');
    hideFinishTooltip();
}

// Track recently applied finishes for "Recent" sort
const RECENT_FINISHES_KEY = 'shokker_recent_finishes';
function getRecentFinishes() { try { return JSON.parse(localStorage.getItem(RECENT_FINISHES_KEY) || '[]'); } catch { return []; } }
function addRecentFinish(key) {
    let recent = getRecentFinishes();
    recent = recent.filter(k => k !== key);
    recent.unshift(key);
    if (recent.length > 50) recent = recent.slice(0, 50);
    localStorage.setItem(RECENT_FINISHES_KEY, JSON.stringify(recent));
}

// ===== OFFLINE FINISH CATALOG =====
// Favorites system (localStorage)
const FINISH_FAVORITES_KEY = 'shokker_finish_favorites';
let finishBrowserCatalogView = false;
let finishBrowserFavOnly = false;

function getFinishFavorites() { try { return JSON.parse(localStorage.getItem(FINISH_FAVORITES_KEY) || '[]'); } catch { return []; } }
function setFinishFavorites(favs) { localStorage.setItem(FINISH_FAVORITES_KEY, JSON.stringify(favs)); }
function toggleFinishFavorite(key) {
    let favs = getFinishFavorites();
    const idx = favs.indexOf(key);
    if (idx >= 0) favs.splice(idx, 1); else favs.push(key);
    setFinishFavorites(favs);
    filterFinishBrowser();
}
function isFinishFavorite(key) { return getFinishFavorites().includes(key); }

// Generate CSS swatch for a base+pattern combo (no server needed)
function makeSwatchCSS(baseId, patId) {
    const base = BASES.find(b => b.id === baseId);
    const pat = PATTERNS.find(p => p.id === patId);
    const baseColor = base?.swatch || '#555';
    if (!pat || patId === 'none') {
        return `background:${baseColor};`;
    }
    // Use actual rendered pattern texture thumbnail overlaid on base color
    const cacheBust = window.APP_SESSION_ID || Date.now();
    return `background: url('/swatch/pattern/${patId}?v=${cacheBust}') center/cover, ${baseColor}; background-blend-mode: overlay;`;
}

function makeMonoSwatchCSS(monoId) {
    const mono = MONOLITHICS.find(m => m.id === monoId);
    if (!mono) return 'background: #666;';
    const color = mono.swatch || '#666';
    // Dual-color entries (gradients, color-shifts) show both colors
    if (mono.swatch2) {
        return `background: linear-gradient(135deg, ${color} 50%, ${mono.swatch2} 50%);`;
    }
    // Monolithics get a radial gradient to distinguish from combos
    return `background: radial-gradient(circle at 30% 30%, ${color}, ${adjustBrightness(color, -40)});`;
}

function adjustBrightness(hex, amount) {
    const num = parseInt(hex.replace('#', ''), 16);
    let r = Math.min(255, Math.max(0, ((num >> 16) & 0xFF) + amount));
    let g = Math.min(255, Math.max(0, ((num >> 8) & 0xFF) + amount));
    let b = Math.min(255, Math.max(0, (num & 0xFF) + amount));
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

function getFinishDesc(item) {
    if (item.type === 'mono') {
        return MONOLITHICS.find(m => m.id === item.monoId)?.desc || '';
    }
    const baseDesc = BASES.find(b => b.id === item.baseId)?.desc || '';
    const patDesc = PATTERNS.find(p => p.id === item.patId)?.desc || '';
    if (!item.patId || item.patId === 'none') return baseDesc;
    return baseDesc + ' / ' + patDesc;
}

// View toggle
function toggleFinishBrowserView() {
    finishBrowserCatalogView = !finishBrowserCatalogView;
    const btn = document.getElementById('fbViewToggle');
    if (btn) btn.innerHTML = finishBrowserCatalogView ? '⊞ Grid' : '☰ List';
    const grid = document.getElementById('finishBrowserGrid');
    if (grid) grid.classList.toggle('catalog-view', finishBrowserCatalogView);
    filterFinishBrowser();
}

// Favorites filter toggle
function toggleFavoritesFilter() {
    finishBrowserFavOnly = !finishBrowserFavOnly;
    const btn = document.getElementById('fbFavToggle');
    if (btn) btn.classList.toggle('active', finishBrowserFavOnly);
    filterFinishBrowser();
}

// Finish detail tooltip
let finishTooltipEl = null;
function showFinishTooltip(e, item) {
    if (!finishTooltipEl) {
        finishTooltipEl = document.createElement('div');
        finishTooltipEl.className = 'finish-tooltip';
        document.body.appendChild(finishTooltipEl);
    }
    const desc = getFinishDesc(item);
    const isMono = item.type === 'mono';
    const swatchStyle = isMono ? makeMonoSwatchCSS(item.monoId) : makeSwatchCSS(item.baseId, item.patId);
    const typeLabel = isMono ? 'Monolithic' : 'Base + Pattern';
    const isFav = isFinishFavorite(item.key);

    finishTooltipEl.innerHTML = `
        <div class="ftt-name">${item.label} ${isFav ? '★' : ''}</div>
        <div class="ftt-type">${typeLabel}</div>
        <div class="ftt-swatch" style="${swatchStyle}"></div>
        <div class="ftt-desc">${desc}</div>
        <div class="ftt-meta">${isMono ? 'ID: ' + item.monoId : 'Base: ' + item.baseId + (item.patId !== 'none' ? ' | Pattern: ' + item.patId : '')}</div>
    `;
    finishTooltipEl.style.display = 'block';
    positionFinishTooltip(e);
}
function positionFinishTooltip(e) {
    if (!finishTooltipEl) return;
    let x = e.clientX + 12, y = e.clientY + 12;
    if (x + 260 > window.innerWidth) x = e.clientX - 260;
    if (y + 200 > window.innerHeight) y = e.clientY - 200;
    finishTooltipEl.style.left = x + 'px';
    finishTooltipEl.style.top = y + 'px';
}
function hideFinishTooltip() {
    if (finishTooltipEl) finishTooltipEl.style.display = 'none';
}

function filterFinishBrowser() {
    const type = document.getElementById('fbFilterType').value;
    const baseFilter = document.getElementById('fbFilterBase').value;
    const patFilter = document.getElementById('fbFilterPattern').value;
    const search = (document.getElementById('fbSearch').value || '').toLowerCase();
    const sortMode = document.getElementById('fbSort')?.value || 'default';
    const grid = document.getElementById('finishBrowserGrid');
    if (!grid) return;

    const favs = getFinishFavorites();
    const isCatalog = finishBrowserCatalogView;
    grid.classList.toggle('catalog-view', isCatalog);

    // Build items array
    let items = [];

    // Combos (base + pattern)
    if (type === 'all' || type === 'combo') {
        const bases = baseFilter === 'all' ? BASES : BASES.filter(b => b.id === baseFilter);
        const pats = patFilter === 'all' ? PATTERNS : PATTERNS.filter(p => p.id === patFilter);
        for (const b of bases) {
            for (const p of pats) {
                const label = p.id === 'none' ? b.name : `${b.name} + ${p.name}`;
                const key = `${b.id}:${p.id}`;
                if (search && !label.toLowerCase().includes(search) && !b.id.includes(search) && !p.id.includes(search) &&
                    !(b.desc && b.desc.toLowerCase().includes(search)) && !(p.desc && p.desc.toLowerCase().includes(search))) continue;
                if (finishBrowserFavOnly && !favs.includes(key)) continue;
                items.push({ type: 'combo', label, baseId: b.id, patId: p.id, key });
            }
        }
    }

    // Monolithics
    if (type === 'all' || type === 'mono') {
        for (const m of MONOLITHICS) {
            const key = `mono:${m.id}`;
            if (search && !m.name.toLowerCase().includes(search) && !m.id.includes(search) &&
                !(m.desc && m.desc.toLowerCase().includes(search))) continue;
            if (baseFilter !== 'all' || patFilter !== 'all') continue;
            if (finishBrowserFavOnly && !favs.includes(key)) continue;
            items.push({ type: 'mono', label: m.name, monoId: m.id, key });
        }
    }

    // Apply sorting
    if (sortMode === 'az') {
        items.sort((a, b) => a.label.localeCompare(b.label));
    } else if (sortMode === 'za') {
        items.sort((a, b) => b.label.localeCompare(a.label));
    } else if (sortMode === 'recent') {
        const recent = getRecentFinishes();
        items.sort((a, b) => {
            const ai = recent.indexOf(a.key);
            const bi = recent.indexOf(b.key);
            if (ai === -1 && bi === -1) return 0;
            if (ai === -1) return 1;
            if (bi === -1) return -1;
            return ai - bi;
        });
    } else if (sortMode === 'favorites') {
        items.sort((a, b) => {
            const af = favs.includes(a.key) ? 0 : 1;
            const bf = favs.includes(b.key) ? 0 : 1;
            if (af !== bf) return af - bf;
            return a.label.localeCompare(b.label);
        });
    }

    // Cap at 500 for performance (24K+ combos would kill the DOM)
    const maxItems = 500;
    const totalFound = items.length;
    const capped = items.length > maxItems;
    if (capped) items = items.slice(0, maxItems);

    // Render - using client-side CSS swatches (offline-ready, no server images)
    let html = '';
    for (const item of items) {
        const isMono = item.type === 'mono';
        const swatchStyle = isMono ? makeMonoSwatchCSS(item.monoId) : makeSwatchCSS(item.baseId, item.patId);
        const isFav = favs.includes(item.key);
        const dataAttr = `data-item='${JSON.stringify(item).replace(/'/g, "&#39;")}'`;

        if (isCatalog) {
            // Catalog (list) view with descriptions and favorites
            const desc = getFinishDesc(item);
            const onclick = isMono
                ? `applyFinishFromBrowser(null,null,'${item.monoId}')`
                : `applyFinishFromBrowser('${item.baseId}','${item.patId}')`;
            html += `<div class="finish-swatch-cell" onclick="${onclick}" ${dataAttr}
                onmouseenter="showFinishTooltip(event,${isMono ? `{type:'mono',label:'${item.label.replace(/'/g, "\\'")}',monoId:'${item.monoId}',key:'${item.key}'}` : `{type:'combo',label:'${item.label.replace(/'/g, "\\'")}',baseId:'${item.baseId}',patId:'${item.patId}',key:'${item.key}'}`})"
                onmousemove="positionFinishTooltip(event)" onmouseleave="hideFinishTooltip()"
                ${isMono ? 'style="border-color:var(--accent-gold);"' : ''}>
                <div class="fs-swatch-block" style="${swatchStyle}"></div>
                <div class="fs-info">
                    <div class="fs-label" ${isMono ? 'style="color:var(--accent-gold);"' : ''}>${item.label}</div>
                    <div class="fs-desc">${desc}</div>
                </div>
                <span class="fs-fav ${isFav ? 'favorited' : ''}" onclick="event.stopPropagation(); toggleFinishFavorite('${item.key}')">★</span>
            </div>`;
        } else {
            // Grid view - compact CSS swatches
            const onclick = isMono
                ? `applyFinishFromBrowser(null,null,'${item.monoId}')`
                : `applyFinishFromBrowser('${item.baseId}','${item.patId}')`;
            html += `<div class="finish-swatch-cell" onclick="${onclick}" title="${item.label}${isMono ? ' (Monolithic)' : ''}"
                onmouseenter="showFinishTooltip(event,${isMono ? `{type:'mono',label:'${item.label.replace(/'/g, "\\'")}',monoId:'${item.monoId}',key:'${item.key}'}` : `{type:'combo',label:'${item.label.replace(/'/g, "\\'")}',baseId:'${item.baseId}',patId:'${item.patId}',key:'${item.key}'}`})"
                onmousemove="positionFinishTooltip(event)" onmouseleave="hideFinishTooltip()"
                ${isMono ? 'style="border-color:var(--accent-gold);"' : ''}>
                <div class="fs-swatch-block" style="${swatchStyle}">${isFav ? '<span style="position:absolute;top:1px;right:2px;font-size:10px;color:var(--accent-gold);">★</span>' : ''}</div>
                <div class="fs-label" ${isMono ? 'style="color:var(--accent-gold);"' : ''}>${item.label}</div>
            </div>`;
        }
    }

    if (!html) {
        html = '<div style="grid-column:1/-1; text-align:center; color:var(--text-dim); padding:20px;">No finishes match your filters.' +
            (finishBrowserFavOnly ? '<br><span style="font-size:10px;">Try disabling the ★ Favorites filter.</span>' : '') + '</div>';
    }

    grid.innerHTML = html;
    const countText = capped ? `Showing ${maxItems} of ${totalFound} finishes (filter to see more)` : `Showing ${totalFound} finishes`;
    const favCount = favs.length;
    document.getElementById('fbCount').textContent = countText + (favCount > 0 ? ` | ${favCount} favorites` : '');
}

function applyFinishFromBrowser(baseId, patternId, monoId) {
    pushZoneUndo('Apply finish from catalog');
    const z = zones[finishBrowserTargetZone];
    if (monoId) {
        z.finish = monoId;
        z.base = null;
        z.pattern = null;
        addRecentFinish(`mono:${monoId}`);
    } else {
        z.finish = null;
        z.base = baseId;
        z.pattern = patternId || 'none';
        addRecentFinish(`${baseId}:${patternId || 'none'}`);
    }
    renderZones();
    closeFinishBrowser();
    hideFinishTooltip();
    const name = monoId || (baseId + (patternId && patternId !== 'none' ? ' + ' + patternId : ''));
    showToast(`Applied ${name} to ${z.name}`);
}

// ===== FINISH COMPARISON =====
let compareTargetZone = 0;
let compareColumns = [];

function openFinishCompare(zoneIndex) {
    compareTargetZone = zoneIndex;
    const z = zones[zoneIndex];
    // Pre-populate first column with current zone's finish
    compareColumns = [
        { base: z.base || 'chrome', pattern: z.pattern || 'none', mono: z.finish || null },
        { base: 'metallic', pattern: 'carbon_fiber', mono: null }
    ];
    renderCompareColumns();
    document.getElementById('finishCompareOverlay').classList.add('active');
}

function closeFinishCompare() {
    document.getElementById('finishCompareOverlay').classList.remove('active');
}

function renderCompareColumns() {
    const container = document.getElementById('compareColumnsContainer');
    if (!container) return;

    let html = '';
    compareColumns.forEach((col, ci) => {
        const isMono = !!col.mono;
        const swatchStyle = isMono
            ? makeMonoSwatchCSS(col.mono)
            : makeSwatchCSS(col.base, col.pattern);
        const label = isMono
            ? (MONOLITHICS.find(m => m.id === col.mono)?.name || col.mono)
            : (BASES.find(b => b.id === col.base)?.name || col.base) +
            (col.pattern !== 'none' ? ' + ' + (PATTERNS.find(p => p.id === col.pattern)?.name || col.pattern) : '');

        html += `<div class="compare-col">
            <div style="${swatchStyle} width:100%; height:80px; border-radius:6px;"></div>
            <div style="font-size:10px; font-weight:700; color:var(--text-bright); margin:4px 0 2px;">${label}</div>
            <select onchange="updateCompareCol(${ci},'base',this.value)">
                ${BASES.map(b => `<option value="${b.id}"${!isMono && col.base === b.id ? ' selected' : ''}>${b.name}</option>`).join('')}
                <optgroup label="Monolithic">
                    ${MONOLITHICS.map(m => `<option value="mono:${m.id}"${col.mono === m.id ? ' selected' : ''}>${m.name}</option>`).join('')}
                </optgroup>
            </select>
            <select onchange="updateCompareCol(${ci},'pattern',this.value)"${isMono ? ' disabled style="opacity:0.3;"' : ''}>
                ${PATTERNS.map(p => `<option value="${p.id}"${!isMono && col.pattern === p.id ? ' selected' : ''}>${p.name}</option>`).join('')}
            </select>
            <div style="display:flex; gap:4px; margin-top:6px; justify-content:center;">
                <button class="btn btn-sm" onclick="applyCompareCol(${ci})" style="font-size:9px; padding:2px 8px; background:var(--accent); color:#000;">Apply</button>
                ${compareColumns.length > 2 ? `<button class="btn btn-sm" onclick="removeCompareCol(${ci})" style="font-size:9px; padding:2px 6px; color:#ff4444;">✕</button>` : ''}
            </div>
        </div>`;
    });
    container.innerHTML = html;
}

function updateCompareCol(ci, field, value) {
    const col = compareColumns[ci];
    if (field === 'base') {
        if (value.startsWith('mono:')) {
            col.mono = value.replace('mono:', '');
            col.base = null;
            col.pattern = 'none';
        } else {
            col.mono = null;
            col.base = value;
        }
    } else if (field === 'pattern') {
        col.pattern = value;
    }
    renderCompareColumns();
}

function applyCompareCol(ci) {
    pushZoneUndo('Apply finish from compare');
    const col = compareColumns[ci];
    const z = zones[compareTargetZone];
    if (col.mono) {
        z.finish = col.mono;
        z.base = null;
        z.pattern = null;
    } else {
        z.finish = null;
        z.base = col.base;
        z.pattern = col.pattern || 'none';
    }
    renderZones();
    closeFinishCompare();
    const name = col.mono || (col.base + (col.pattern !== 'none' ? ' + ' + col.pattern : ''));
    showToast(`Applied ${name} to ${z.name}`);
}

function addCompareColumn() {
    if (compareColumns.length >= 4) { showToast('Max 4 columns'); return; }
    compareColumns.push({ base: 'pearl', pattern: 'none', mono: null });
    renderCompareColumns();
}

function removeCompareCol(ci) {
    if (compareColumns.length <= 2) return;
    compareColumns.splice(ci, 1);
    renderCompareColumns();
}

// ===== RANDOMIZE WITH STYLE LOCK =====
const GOOD_COMBOS = [
    "chrome+carbon_fiber", "chrome+diamond_plate", "chrome+hex_mesh", "chrome+lightning",
    "chrome+hologram", "chrome+stardust", "chrome+none",
    "matte+carbon_fiber", "matte+hex_mesh", "matte+battle_worn",
    "candy+holographic_flake", "candy+stardust", "candy+metal_flake", "candy+none",
    "metallic+metal_flake", "metallic+holographic_flake", "metallic+carbon_fiber",
    "pearl+interference", "pearl+stardust", "pearl+holographic_flake", "pearl+ripple",
    "satin_metal+carbon_fiber", "satin_metal+diamond_plate",
    "brushed_titanium+carbon_fiber", "brushed_titanium+diamond_plate", "brushed_titanium+hex_mesh",
    "frozen+cracked_ice", "frozen+holographic_flake", "frozen+stardust",
    "blackout+carbon_fiber", "blackout+hex_mesh", "blackout+lightning",
    "anodized+diamond_plate", "anodized+hex_mesh",
    "gloss+none", "gloss+carbon_fiber", "gloss+metal_flake",
    "satin+carbon_fiber", "satin+none",
];

const BAD_COMBOS = new Set([
    "blackout+stardust", "blackout+holographic_flake", "blackout+interference",
    "matte+holographic_flake", "matte+metal_flake", "matte+interference",
    "chrome+battle_worn", "chrome+acid_wash",
]);

function toggleLock(index, prop) {
    zones[index][prop] = !zones[index][prop];
    renderZones();
}

function randomizeZone(index) {
    if (index < 0 || index >= zones.length) return;
    pushZoneUndo('Randomize zone');
    const zone = zones[index];
    const smart = document.getElementById('smartRandomize')?.checked;

    if (smart && !zone.lockBase && !zone.lockPattern) {
        // Smart mode: pick from curated combos
        if (Math.random() < 0.8 && GOOD_COMBOS.length > 0) {
            const combo = GOOD_COMBOS[Math.floor(Math.random() * GOOD_COMBOS.length)];
            const [b, p] = combo.split('+');
            zone.base = b;
            zone.pattern = p;
        } else {
            // Random but avoid bad combos
            let attempts = 0;
            do {
                zone.base = BASES[Math.floor(Math.random() * BASES.length)].id;
                zone.pattern = PATTERNS[Math.floor(Math.random() * PATTERNS.length)].id;
                attempts++;
            } while (BAD_COMBOS.has(zone.base + '+' + zone.pattern) && attempts < 20);
        }
    } else {
        if (!zone.lockBase) zone.base = BASES[Math.floor(Math.random() * BASES.length)].id;
        if (!zone.lockPattern) zone.pattern = PATTERNS[Math.floor(Math.random() * PATTERNS.length)].id;
    }

    zone.finish = null;
    zone.patternStack = [];  // Clear stacked layers on randomize
    if (!zone.lockIntensity) {
        const intensities = INTENSITY_OPTIONS.map(o => o.id);
        zone.intensity = intensities[Math.floor(Math.random() * intensities.length)];
    }
    renderZones();
    const hint = getComboHint(zone.base, zone.pattern);
    showToast(`Randomized: ${BASES.find(b => b.id === zone.base)?.name} + ${PATTERNS.find(p => p.id === zone.pattern)?.name}${hint ? ' -- ' + hint : ''}`);
}

function randomizeAllZones() {
    pushZoneUndo();
    zones.forEach((z, i) => {
        const smart = document.getElementById('smartRandomize')?.checked;
        if (smart && !z.lockBase && !z.lockPattern) {
            if (Math.random() < 0.8 && GOOD_COMBOS.length > 0) {
                const combo = GOOD_COMBOS[Math.floor(Math.random() * GOOD_COMBOS.length)];
                const [b, p] = combo.split('+');
                z.base = b;
                z.pattern = p;
            } else {
                let attempts = 0;
                do {
                    z.base = BASES[Math.floor(Math.random() * BASES.length)].id;
                    z.pattern = PATTERNS[Math.floor(Math.random() * PATTERNS.length)].id;
                    attempts++;
                } while (BAD_COMBOS.has(z.base + '+' + z.pattern) && attempts < 20);
            }
        } else {
            if (!z.lockBase) z.base = BASES[Math.floor(Math.random() * BASES.length)].id;
            if (!z.lockPattern) z.pattern = PATTERNS[Math.floor(Math.random() * PATTERNS.length)].id;
        }
        z.finish = null;
        if (!z.lockIntensity) {
            const intensities = INTENSITY_OPTIONS.map(o => o.id);
            z.intensity = intensities[Math.floor(Math.random() * intensities.length)];
        }
    });
    renderZones();
    showToast(`Randomized all ${zones.length} zones!`);
}

// ===== ZONE TEMPLATES (Save/Load) =====
function getTemplateStore() {
    try { return JSON.parse(localStorage.getItem('shokker_zone_templates') || '{}'); }
    catch { return {}; }
}

function saveZoneTemplate() {
    const overlay = document.getElementById('tmplNameOverlay');
    const input = document.getElementById('tmplNameInput');
    input.value = '';
    overlay.classList.add('active');
    setTimeout(() => input.focus(), 50);
    input.onkeydown = (e) => {
        if (e.key === 'Enter') confirmSaveTemplate();
        if (e.key === 'Escape') closeTmplNameModal();
    };
}
function closeTmplNameModal() {
    document.getElementById('tmplNameOverlay').classList.remove('active');
}
function confirmSaveTemplate() {
    const input = document.getElementById('tmplNameInput');
    const name = (input.value || '').trim();
    if (!name) { input.style.borderColor = 'var(--accent)'; input.focus(); return; }
    closeTmplNameModal();
    const templates = getTemplateStore();
    templates[name] = zones.map(z => ({
        name: z.name,
        color: z.color,
        colorMode: z.colorMode,
        pickerColor: z.pickerColor,
        pickerTolerance: z.pickerTolerance,
        colors: z.colors || [],
        base: z.base, pattern: z.pattern, finish: z.finish,
        intensity: z.intensity, scale: z.scale || 1.0,
        customSpec: z.customSpec, customPaint: z.customPaint, customBright: z.customBright,
        lockBase: z.lockBase, lockPattern: z.lockPattern,
        lockIntensity: z.lockIntensity, lockColor: z.lockColor,
        patternStack: z.patternStack || [],
    }));
    localStorage.setItem('shokker_zone_templates', JSON.stringify(templates));
    refreshTemplateDropdown();
    showToast(`Template saved: "${name}" (${zones.length} zones)`);
}

function loadZoneTemplate(name) {
    if (!name) return;
    const templates = getTemplateStore();
    const data = templates[name];
    if (!data) { showToast('Template not found!', true); return; }
    pushZoneUndo();

    zones = data.map(t => ({
        name: t.name || 'Zone',
        color: t.color,
        colorMode: t.colorMode || 'none',
        pickerColor: t.pickerColor || '#3366ff',
        pickerTolerance: t.pickerTolerance || 40,
        colors: t.colors || [],
        base: t.base || null, pattern: t.pattern || 'none',
        finish: t.finish || null, intensity: t.intensity || '100',
        scale: t.scale || 1.0,
        customSpec: t.customSpec ?? null, customPaint: t.customPaint ?? null,
        customBright: t.customBright ?? null,
        hint: '',
        regionMask: null,
        lockBase: t.lockBase || false, lockPattern: t.lockPattern || false,
        lockIntensity: t.lockIntensity || false, lockColor: t.lockColor || false,
        patternStack: t.patternStack || [],
    }));
    selectedZoneIndex = 0;
    renderZones();
    const sel = document.getElementById('templateSelect');
    if (sel) sel.value = '';
    const hasFinishes = zones.some(z => z.base || z.finish);
    showToast(`Template loaded: "${name}" (${zones.length} zones)${hasFinishes ? '' : ' -- now assign finishes!'}`);
}

function deleteZoneTemplate(name) {
    const templates = getTemplateStore();
    delete templates[name];
    localStorage.setItem('shokker_zone_templates', JSON.stringify(templates));
    refreshTemplateDropdown();
    showToast(`Template deleted: "${name}"`);
}

function refreshTemplateDropdown() {
    const sel = document.getElementById('templateSelect');
    if (!sel) return;
    const templates = getTemplateStore();
    const names = Object.keys(templates);
    let html = '<option value="">Load Tmpl...</option>';
    names.forEach(n => {
        const count = templates[n].length;
        html += `<option value="${escapeHtml(n)}">${escapeHtml(n)} (${count}z)</option>`;
    });
    if (names.length > 0) {
        html += '<optgroup label="Delete">';
        names.forEach(n => html += `<option value="__delete__:${escapeHtml(n)}">Delete: ${escapeHtml(n)}</option>`);
        html += '</optgroup>';
    }
    sel.innerHTML = html;
    // Override the onchange to handle delete
    sel.onchange = function () {
        const v = this.value;
        if (v.startsWith('__delete__:')) {
            const delName = v.substring(11);
            if (confirm(`Delete template "${delName}"?`)) deleteZoneTemplate(delName);
            this.value = '';
        } else {
            loadZoneTemplate(v);
        }
    };
}

// ===== TEMPLATE EXPORT/IMPORT =====
function exportTemplate(name) {
    const templates = getTemplateStore();
    const data = templates[name];
    if (!data) { showToast('Select a template to export', true); return; }
    const blob = new Blob([JSON.stringify({ type: 'shokker_template', name, zones: data }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_template_${name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast(`Exported template: "${name}"`);
}

function importTemplate() {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                if (!data.name || !data.zones || !Array.isArray(data.zones))
                    throw new Error('Invalid template format');
                const templates = getTemplateStore();
                templates[data.name] = data.zones;
                localStorage.setItem('shokker_zone_templates', JSON.stringify(templates));
                refreshTemplateDropdown();
                showToast(`Imported template: "${data.name}" (${data.zones.length} zones)`);
            } catch (err) { showToast('Invalid template file: ' + err.message, true); }
        };
        reader.readAsText(file);
    };
    input.click();
}

// ===== FINISH COMBO LIBRARY =====
function getComboStore() {
    return JSON.parse(localStorage.getItem('shokker_finish_combos') || '{}');
}

function saveCombo() {
    const z = zones[selectedZoneIndex];
    if (!z) return;
    if (!z.base && !z.finish) { showToast('Zone has no finish to save as combo', true); return; }
    const name = prompt('Name this finish combo:');
    if (!name || !name.trim()) return;
    const combos = getComboStore();
    combos[name.trim()] = {
        name: name.trim(),
        base: z.base, pattern: z.pattern, finish: z.finish,
        intensity: z.intensity, scale: z.scale || 1.0,
        author: '', description: '', tags: [],
        created: new Date().toISOString()
    };
    localStorage.setItem('shokker_finish_combos', JSON.stringify(combos));
    refreshComboDropdown();
    showToast(`Saved combo: "${name.trim()}"`);
}

function applyCombo(name) {
    if (!name) return;
    const combos = getComboStore();
    const c = combos[name];
    if (!c) return;
    pushZoneUndo();
    const z = zones[selectedZoneIndex];
    if (c.finish) {
        z.finish = c.finish; z.base = null; z.pattern = null;
    } else {
        z.base = c.base; z.pattern = c.pattern; z.finish = null;
    }
    z.intensity = c.intensity || '100';
    z.scale = c.scale || 1.0;
    renderZones();
    showToast(`Applied combo: "${name}"`);
}

function deleteCombo() {
    const sel = document.getElementById('comboDropdown');
    const name = sel ? sel.value : '';
    if (!name) { showToast('Select a combo first', true); return; }
    if (!confirm(`Delete combo "${name}"?`)) return;
    const combos = getComboStore();
    delete combos[name];
    localStorage.setItem('shokker_finish_combos', JSON.stringify(combos));
    refreshComboDropdown();
    showToast(`Deleted combo: "${name}"`);
}

function exportCombo(name) {
    if (!name) { showToast('Select a combo to export', true); return; }
    const combos = getComboStore();
    const c = combos[name];
    if (!c) return;
    const blob = new Blob([JSON.stringify({ type: 'shokker_combo', ...c }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_combo_${name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast(`Exported combo: "${name}"`);
}

function exportAllCombos() {
    const combos = getComboStore();
    const arr = Object.values(combos);
    if (arr.length === 0) { showToast('No combos saved', true); return; }
    const blob = new Blob([JSON.stringify({ type: 'shokker_combo_pack', combos: arr }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `shokker_combo_pack_${arr.length}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast(`Exported ${arr.length} combos as pack`);
}

function importCombo() {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                const combos = getComboStore();
                // Detect combo pack format
                if (data.type === 'shokker_combo_pack' && Array.isArray(data.combos)) {
                    let count = 0;
                    data.combos.forEach(c => {
                        if (c.name && (c.base || c.finish)) {
                            combos[c.name] = c;
                            count++;
                        }
                    });
                    localStorage.setItem('shokker_finish_combos', JSON.stringify(combos));
                    refreshComboDropdown();
                    showToast(`Imported combo pack: ${count} combos`);
                } else if (data.name && (data.base || data.finish)) {
                    // Single combo
                    combos[data.name] = data;
                    localStorage.setItem('shokker_finish_combos', JSON.stringify(combos));
                    refreshComboDropdown();
                    showToast(`Imported combo: "${data.name}"${data.author ? ' by ' + data.author : ''}`);
                } else {
                    throw new Error('Invalid combo format');
                }
            } catch (err) { showToast('Invalid combo file: ' + err.message, true); }
        };
        reader.readAsText(file);
    };
    input.click();
}

function refreshComboDropdown() {
    const sel = document.getElementById('comboDropdown');
    if (!sel) return;
    const combos = getComboStore();
    const names = Object.keys(combos);
    let html = '<option value="">-- Saved Combos --</option>';
    names.forEach(n => {
        const c = combos[n];
        const desc = c.finish
            ? (MONOLITHICS.find(m => m.id === c.finish)?.name || c.finish)
            : [BASES.find(b => b.id === c.base)?.name || c.base, PATTERNS.find(p => p.id === c.pattern)?.name || ''].filter(Boolean).join(' + ');
        html += `<option value="${escapeHtml(n)}">${escapeHtml(n)} (${desc})</option>`;
    });
    sel.innerHTML = html;
}

// ===== NLP CHAT BAR - NATURAL LANGUAGE ZONE CONFIGURATION =====

// Synonym dictionary for fuzzy matching
const CHAT_SYNONYMS = {
    // Base synonyms
    'mirror': 'chrome', 'reflective': 'chrome', 'shiny': 'gloss', 'glossy': 'gloss',
    'flat': 'matte', 'murdered': 'blackout', 'blacked': 'blackout', 'murdered out': 'blackout',
    'brushed': 'brushed_titanium', 'titanium': 'brushed_titanium',
    'candy apple': 'candy', 'pearlescent': 'pearl',
    'ice': 'frozen_matte', 'icy': 'frozen_matte',
    'tactical': 'cerakote', 'military': 'cerakote', 'void': 'vantablack',
    'pink gold': 'rose_gold', 'rosegold': 'rose_gold',
    'satin chrome': 'satin_chrome', 'silk chrome': 'satin_chrome',
    'hot wheels': 'spectraflame', 'spectra': 'spectraflame',
    // Pattern synonyms
    'cf': 'carbon_fiber', 'fiber': 'carbon_fiber', 'carbon': 'carbon_fiber',
    'weave': 'carbon_fiber', 'forged': 'forged_carbon', 'chopped': 'forged_carbon',
    'hex': 'hex_mesh', 'honeycomb': 'hex_mesh', 'diamond': 'diamond_plate',
    'scales': 'dragon_scale', 'dragon': 'dragon_scale',
    'holo': 'holographic_flake', 'holographic': 'holographic_flake',
    'sparkle': 'metal_flake', 'glitter': 'mega_flake', 'flake': 'metal_flake',
    'stripes': 'pinstripe', 'racing stripes': 'pinstripe',
    'camo': 'camo', 'camouflage': 'multicam',
    'circuit': 'circuit_board', 'pcb': 'circuit_board', 'tron': 'tron', 'grid': 'tron',
    'neon grid': 'tron', 'lava': 'magma_crack', 'magma': 'magma_crack',
    'snake': 'snake_skin', 'leopard': 'leopard', 'brick': 'brick',
    'wire': 'barbed_wire', 'chainmail': 'chainmail', 'chain': 'chainmail',
    'marble': 'marble', 'stone': 'marble', 'rain': 'rain_drop',
    'wood': 'wood_grain', 'tire': 'tire_tread', 'tread': 'tire_tread',
    'dazzle': 'dazzle', 'mosaic': 'mosaic', 'stained glass': 'mosaic',
    'razor': 'razor', 'slash': 'razor',
    // Monolithic synonyms
    'color shift': 'cs_warm', 'colour shift': 'cs_warm',
    'color shift pro': 'cs_emerald', 'cs pro': 'cs_emerald',
    'adaptive': 'cs_warm', 'adaptive shift': 'cs_warm',
    'warm shift': 'cs_warm', 'cool shift': 'cs_cool',
    'rainbow shift': 'cs_rainbow', 'subtle shift': 'cs_subtle',
    'extreme shift': 'cs_extreme',
    'emerald': 'cs_emerald', 'chromaflair': 'cs_emerald',
    'inferno': 'cs_inferno', 'nebula': 'cs_nebula',
    'deep ocean': 'cs_deepocean', 'ocean shift': 'cs_deepocean',
    'supernova': 'cs_supernova', 'full spectrum': 'cs_supernova',
    'solar flare': 'cs_solarflare', 'sunset metal': 'cs_solarflare',
    'mystichrome pro': 'cs_mystichrome',
    'chameleon': 'chameleon_midnight', 'mystichrome': 'mystichrome',
    'glitch': 'glitch', 'digital': 'glitch', 'corrupted': 'glitch',
    'toon': 'cel_shade', 'cel': 'cel_shade', 'anime': 'cel_shade', 'cartoon': 'cel_shade',
    'heat': 'thermochromic', 'thermal': 'thermochromic', 'temperature': 'thermochromic',
    'aurora': 'aurora', 'northern lights': 'aurora', 'borealis': 'aurora',
    'phantom': 'phantom', 'ghost': 'phantom',
    'ember': 'ember_glow', 'liquid': 'liquid_metal', 'mercury': 'liquid_metal',
    'frost': 'frost_bite', 'oil': 'oil_slick', 'rainbow': 'oil_slick',
    'galaxy': 'galaxy', 'nebula': 'galaxy', 'space': 'galaxy',
    'rust': 'rust', 'rusty': 'rust', 'neon': 'neon_glow',
    'weathered': 'weathered_paint', 'worn': 'worn_chrome',
    // Prizm v4 Panel-Aware Color Shift
    'prizm': 'prizm_holographic', 'prizm paint': 'prizm_holographic',
    'prizm holographic': 'prizm_holographic', 'holographic prizm': 'prizm_holographic',
    'prizm midnight': 'prizm_midnight', 'prizm purple': 'prizm_midnight',
    'prizm phoenix': 'prizm_phoenix', 'prizm fire': 'prizm_phoenix',
    'prizm oceanic': 'prizm_oceanic', 'prizm ocean': 'prizm_oceanic', 'prizm sea': 'prizm_oceanic',
    'prizm ember': 'prizm_ember', 'prizm copper': 'prizm_ember', 'prizm molten': 'prizm_ember',
    'prizm arctic': 'prizm_arctic', 'prizm ice': 'prizm_arctic', 'prizm frozen': 'prizm_arctic',
    'prizm solar': 'prizm_solar', 'prizm sunset': 'prizm_solar', 'prizm gold': 'prizm_solar',
    'prizm venom': 'prizm_venom', 'prizm toxic': 'prizm_venom', 'prizm green': 'prizm_venom',
    'prizm mystichrome': 'prizm_mystichrome', 'prizm svt': 'prizm_mystichrome',
    'prizm black rainbow': 'prizm_black_rainbow', 'black rainbow': 'prizm_black_rainbow',
    'prizm duochrome': 'prizm_duochrome', 'prizm duo': 'prizm_duochrome',
    'prizm iridescent': 'prizm_iridescent', 'prizm pearl': 'prizm_iridescent',
    'prizm adaptive': 'prizm_adaptive', 'panel shift': 'prizm_adaptive',
    'neonizm': 'prizm_holographic', 'color shift v4': 'prizm_holographic',
    // Intensity synonyms
    'light': 'subtle', 'soft': 'subtle', 'mild': 'subtle',
    'med': 'medium', 'moderate': 'medium',
    'heavy': 'extreme', 'max': 'extreme', 'brutal': 'extreme',
    // Color synonyms
    'rest': 'remaining', 'everything else': 'remaining',
};

// Color name-to-value map from QUICK_COLORS
const CHAT_COLOR_MAP = {};
QUICK_COLORS.forEach(c => { CHAT_COLOR_MAP[c.label.toLowerCase()] = c.value; });
CHAT_COLOR_MAP['remaining'] = 'remaining';
CHAT_COLOR_MAP['rest'] = 'remaining';
CHAT_COLOR_MAP['everything else'] = 'remaining';
CHAT_COLOR_MAP['remainder'] = 'remaining';
CHAT_COLOR_MAP['sponsors'] = 'remaining'; // common user term
CHAT_COLOR_MAP['other'] = 'remaining';

// --- Helper Functions ---

function chatHexToRgb(hex) {
    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    return [r, g, b];
}

function findBestMatch(text, array, type) {
    // First check exact ID match
    for (const item of array) {
        if (item.id === 'none') continue;
        if (text.includes(item.id.replace(/_/g, ' '))) return item.id;
        if (text.includes(item.id.replace(/_/g, ''))) return item.id;
    }
    // Check name match
    for (const item of array) {
        if (item.id === 'none') continue;
        if (text.includes(item.name.toLowerCase())) return item.id;
    }
    // Check synonyms
    const synonymEntries = Object.entries(CHAT_SYNONYMS);
    // Sort by length descending so multi-word synonyms match first
    synonymEntries.sort((a, b) => b[0].length - a[0].length);
    for (const [syn, target] of synonymEntries) {
        if (!text.includes(syn)) continue;
        // Verify the target belongs to the right category
        if (type === 'base' && BASES.find(b => b.id === target)) return target;
        if (type === 'pattern' && PATTERNS.find(p => p.id === target && p.id !== 'none')) return target;
        if (type === 'mono' && MONOLITHICS.find(m => m.id === target)) return target;
    }
    return null;
}

function findColorMatch(text) {
    // Check hex pattern
    const hexMatch = text.match(/#([0-9a-f]{6})\b/i);
    if (hexMatch) return '#' + hexMatch[1].toLowerCase();
    // Check named colors (sort by length to match "everything else" before "red" etc.)
    const colorEntries = Object.entries(CHAT_COLOR_MAP);
    colorEntries.sort((a, b) => b[0].length - a[0].length);
    for (const [name, value] of colorEntries) {
        if (text.includes(name)) return value;
    }
    return null;
}

function findIntensityMatch(text) {
    const intensities = ['subtle', 'medium', 'aggressive', 'extreme'];
    for (const i of intensities) {
        if (text.includes(i)) return i;
    }
    // Check synonyms
    for (const [syn, target] of Object.entries(CHAT_SYNONYMS)) {
        if (intensities.includes(target) || ['subtle', 'medium', 'aggressive', 'extreme'].includes(target)) {
            if (text.includes(syn)) return target;
        }
    }
    return null;
}

function inferZoneName(segment, zone) {
    // Strip @mentions and known keywords to extract a human-readable name
    let name = segment.replace(/@\w+/g, '').trim();
    // Remove color keywords, finish keywords, intensity keywords
    const remove = ['subtle', 'medium', 'aggressive', 'extreme', 'body', 'number', 'sponsors', 'accents',
        'remaining', 'rest', 'everything else'];
    // Also remove quick color names
    QUICK_COLORS.forEach(c => remove.push(c.label.toLowerCase()));
    for (const r of remove) {
        name = name.replace(new RegExp('\\b' + r.replace(/\s+/g, '\\s+') + '\\b', 'gi'), '');
    }
    name = name.replace(/[,;]/g, '').trim();
    // If the segment mentions things like "body", "number", "sponsors", "accents" - use as zone name
    const labels = ['body', 'number', 'numbers', 'sponsors', 'sponsor', 'accents', 'accent', 'trim',
        'hood', 'roof', 'bumper', 'fender', 'door', 'wing', 'splitter', 'diffuser',
        'stripe', 'stripes', 'livery', 'base coat', 'highlights'];
    for (const l of labels) {
        if (segment.toLowerCase().includes(l)) {
            return l.charAt(0).toUpperCase() + l.slice(1);
        }
    }
    return name.length > 1 ? name : null;
}

// --- Core Parser ---
function parseNaturalCommand(text) {
    const segments = text.split(/[,;]+/).map(s => s.trim()).filter(Boolean);
    const results = [];

    for (const segment of segments) {
        const lower = segment.toLowerCase();
        const zone = {
            name: null, color: null, base: null, pattern: null,
            finish: null, intensity: null, scale: null
        };

        // PHASE 1: Extract @mentions (exact IDs)
        const mentions = [...segment.matchAll(/@(\w+)/g)].map(m => m[1].toLowerCase());
        for (const m of mentions) {
            if (MONOLITHICS.find(x => x.id === m)) zone.finish = m;
            else if (BASES.find(b => b.id === m) && !zone.base) zone.base = m;
            else if (PATTERNS.find(p => p.id === m && p.id !== 'none') && !zone.pattern) zone.pattern = m;
            else if (INTENSITY_OPTIONS.find(o => o.id === m)) zone.intensity = m;
        }

        // PHASE 2: If no @mentions matched finish/base/pattern, fall back to synonym/keyword matching
        if (!zone.finish && !zone.base && !zone.pattern) {
            const monoMatch = findBestMatch(lower, MONOLITHICS, 'mono');
            if (monoMatch) zone.finish = monoMatch;
            if (!zone.finish) zone.base = findBestMatch(lower, BASES, 'base');
            if (!zone.finish) zone.pattern = findBestMatch(lower, PATTERNS, 'pattern');
        }

        // PHASE 3: Color, intensity (if not from @), scale, zone name
        zone.color = findColorMatch(lower);
        if (!zone.intensity) zone.intensity = findIntensityMatch(lower);
        const scaleMatch = lower.match(/(\d+\.?\d*)x\b|scale\s+(\d+\.?\d*)/);
        if (scaleMatch) zone.scale = parseFloat(scaleMatch[1] || scaleMatch[2]);
        zone.name = inferZoneName(segment, zone);

        if (zone.base || zone.finish || zone.color) results.push(zone);
    }
    return results;
}

// --- Apply Function ---
function applyChatZones(configs) {
    pushZoneUndo();

    for (const cfg of configs) {
        let targetIndex = -1;

        // Try to find existing zone by color match
        if (cfg.color) {
            targetIndex = zones.findIndex(z =>
                z.color === cfg.color || z.colorMode === cfg.color ||
                (z.pickerColor && z.pickerColor.toLowerCase() === cfg.color)
            );
        }

        if (targetIndex < 0) {
            // Create new zone (skip undo since already pushed)
            addZone(true);
            targetIndex = zones.length - 1;
        }

        const zone = zones[targetIndex];
        if (cfg.name) zone.name = cfg.name;
        if (cfg.color) {
            if (QUICK_COLORS.find(q => q.value === cfg.color)) {
                zone.color = cfg.color; zone.colorMode = 'quick';
            } else if (cfg.color === 'remaining') {
                zone.color = 'remaining'; zone.colorMode = 'special';
            } else if (cfg.color.startsWith('#')) {
                zone.pickerColor = cfg.color; zone.colorMode = 'picker';
                zone.color = { color_rgb: chatHexToRgb(cfg.color), tolerance: 40 };
            }
        }
        if (cfg.finish) {
            zone.finish = cfg.finish; zone.base = null; zone.pattern = null;
        } else {
            if (cfg.base) { zone.base = cfg.base; zone.finish = null; }
            if (cfg.pattern) zone.pattern = cfg.pattern;
            if (!zone.base && cfg.pattern) zone.base = 'gloss'; // Need a base for pattern
        }
        if (cfg.intensity) zone.intensity = cfg.intensity;
        if (cfg.scale) zone.scale = cfg.scale;
    }
    renderZones();
}

// --- Chat Submit ---
function handleChatSubmit() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;

    closeChatDropdown();
    const configs = parseNaturalCommand(text);
    const feedback = document.getElementById('chatFeedback');

    if (configs.length === 0) {
        feedback.style.display = 'block';
        feedback.className = 'chat-feedback error';
        feedback.textContent = 'Could not understand. Try: "white chrome carbon fiber, blue metallic hex"';
        return;
    }

    applyChatZones(configs);

    const summary = configs.map(c => {
        const parts = [];
        if (c.color) parts.push(c.color);
        if (c.base) parts.push(BASES.find(b => b.id === c.base)?.name || c.base);
        if (c.pattern) parts.push(PATTERNS.find(p => p.id === c.pattern)?.name || c.pattern);
        if (c.finish) parts.push(MONOLITHICS.find(m => m.id === c.finish)?.name || c.finish);
        if (c.intensity) parts.push(c.intensity);
        return parts.join(' + ');
    }).join(' | ');
    feedback.style.display = 'block';
    feedback.className = 'chat-feedback';
    feedback.textContent = `Applied ${configs.length} zone(s): ${summary}`;

    input.select();
}

function clearChatInput() {
    document.getElementById('chatInput').value = '';
    document.getElementById('chatFeedback').style.display = 'none';
    closeChatDropdown();
}

// --- @ Autocomplete Engine ---
let chatDropdownIndex = -1;
let chatDropdownItems = [];

function getChatSegmentContext(segmentText) {
    const mentions = [...segmentText.matchAll(/@(\w+)/g)].map(m => m[1].toLowerCase());
    let hasBase = false, hasPattern = false, hasMono = false, hasIntensity = false;
    for (const m of mentions) {
        if (BASES.find(b => b.id === m)) hasBase = true;
        if (PATTERNS.find(p => p.id === m && p.id !== 'none')) hasPattern = true;
        if (MONOLITHICS.find(x => x.id === m)) hasMono = true;
        if (INTENSITY_OPTIONS.find(o => o.id === m)) hasIntensity = true;
    }
    return { hasBase, hasPattern, hasMono, hasIntensity };
}

function getNextCategory(ctx) {
    if (ctx.hasMono) return ctx.hasIntensity ? null : 'intensity';
    if (!ctx.hasBase) return 'base_or_mono';
    if (!ctx.hasPattern) return 'pattern';
    if (!ctx.hasIntensity) return 'intensity';
    return null;
}

function buildDropdownItems(category, filter) {
    const items = [];
    filter = (filter || '').toLowerCase();

    if (category === 'base_or_mono') {
        // Bases
        BASES.forEach(b => {
            if (filter && !b.id.includes(filter) && !b.name.toLowerCase().includes(filter)) return;
            items.push({ id: b.id, name: b.name, desc: b.desc || '', swatch: b.swatch || '', group: 'BASES' });
        });
        // Monolithics
        MONOLITHICS.forEach(m => {
            if (filter && !m.id.includes(filter) && !m.name.toLowerCase().includes(filter)) return;
            items.push({ id: m.id, name: m.name, desc: m.desc || '', swatch: m.swatch || '', group: 'MONOLITHICS' });
        });
    } else if (category === 'pattern') {
        PATTERNS.forEach(p => {
            if (p.id === 'none') return;
            if (filter && !p.id.includes(filter) && !p.name.toLowerCase().includes(filter)) return;
            items.push({ id: p.id, name: p.name, desc: p.desc || '', swatch: '', group: 'PATTERNS' });
        });
    } else if (category === 'intensity') {
        const intensities = [
            { id: 'subtle', name: 'Subtle', desc: 'Light effect' },
            { id: 'medium', name: 'Medium', desc: 'Balanced' },
            { id: 'aggressive', name: 'Aggressive', desc: 'Strong effect' },
            { id: 'extreme', name: 'Extreme', desc: 'Maximum intensity' },
        ];
        intensities.forEach(i => {
            if (filter && !i.id.includes(filter) && !i.name.toLowerCase().includes(filter)) return;
            items.push({ id: i.id, name: i.name, desc: i.desc, swatch: '', group: 'INTENSITY' });
        });
    }
    return items;
}

function showChatDropdown(items, category) {
    const dropdown = document.getElementById('chatDropdown');
    if (!items || items.length === 0) { closeChatDropdown(); return; }

    chatDropdownItems = items;
    chatDropdownIndex = -1;

    let currentGroup = '';
    let html = '';
    const headerLabels = {
        'base_or_mono': 'SELECT BASE OR MONOLITHIC',
        'pattern': 'SELECT PATTERN',
        'intensity': 'SELECT INTENSITY'
    };

    // Add category header
    html += `<div class="chat-dropdown-header">${headerLabels[category] || category.toUpperCase()}</div>`;

    items.forEach((item, idx) => {
        // Group separator for base_or_mono
        if (category === 'base_or_mono' && item.group !== currentGroup) {
            currentGroup = item.group;
            html += `<div class="chat-dropdown-header" style="font-size:8px;padding:2px 8px;">${currentGroup}</div>`;
        }
        const swatchHtml = item.swatch ? `<span class="swatch" style="background:${item.swatch}"></span>` : '';
        html += `<div class="chat-dropdown-item" data-idx="${idx}" onclick="selectChatOption(${idx})" onmouseenter="chatDropdownIndex=${idx};highlightChatItem()">
            ${swatchHtml}<span>${escapeHtml(item.name)}</span><span class="desc">${escapeHtml(item.desc)}</span>
        </div>`;
    });

    dropdown.innerHTML = html;
    dropdown.style.display = 'block';
}

function closeChatDropdown() {
    const dropdown = document.getElementById('chatDropdown');
    if (dropdown) dropdown.style.display = 'none';
    chatDropdownItems = [];
    chatDropdownIndex = -1;
}

function highlightChatItem() {
    const dropdown = document.getElementById('chatDropdown');
    if (!dropdown) return;
    const items = dropdown.querySelectorAll('.chat-dropdown-item');
    items.forEach((el, i) => {
        el.classList.toggle('active', i === chatDropdownIndex);
    });
    // Scroll into view
    if (chatDropdownIndex >= 0 && items[chatDropdownIndex]) {
        items[chatDropdownIndex].scrollIntoView({ block: 'nearest' });
    }
}

function selectChatOption(idx) {
    const item = chatDropdownItems[idx];
    if (!item) return;

    const input = document.getElementById('chatInput');
    const text = input.value;
    const cursorPos = input.selectionStart;
    const beforeCursor = text.substring(0, cursorPos);
    const afterCursor = text.substring(cursorPos);

    // Find the last @... token before cursor and replace it
    const atMatch = beforeCursor.match(/@(\w*)$/);
    if (atMatch) {
        const start = beforeCursor.length - atMatch[0].length;
        const replacement = '@' + item.id + ' ';
        input.value = beforeCursor.substring(0, start) + replacement + afterCursor;
        const newPos = start + replacement.length;
        input.setSelectionRange(newPos, newPos);
    } else {
        // Fallback: just insert
        const replacement = '@' + item.id + ' ';
        input.value = beforeCursor + replacement + afterCursor;
        const newPos = beforeCursor.length + replacement.length;
        input.setSelectionRange(newPos, newPos);
    }

    closeChatDropdown();
    input.focus();
    // Trigger input event to re-check for new @
    onChatInput();
}

function onChatInput() {
    const input = document.getElementById('chatInput');
    const text = input.value;
    const cursorPos = input.selectionStart;
    const beforeCursor = text.substring(0, cursorPos);

    // Find current segment (text after last comma)
    const lastCommaIdx = beforeCursor.lastIndexOf(',');
    const currentSegment = lastCommaIdx >= 0 ? beforeCursor.substring(lastCommaIdx + 1) : beforeCursor;

    // Check if cursor is right after @...
    const atMatch = currentSegment.match(/@(\w*)$/);
    if (!atMatch) {
        closeChatDropdown();
        return;
    }

    const partial = atMatch[1].toLowerCase(); // text typed after @
    const ctx = getChatSegmentContext(currentSegment.substring(0, currentSegment.length - atMatch[0].length));
    const category = getNextCategory(ctx);

    if (!category) {
        closeChatDropdown();
        return;
    }

    const items = buildDropdownItems(category, partial);
    showChatDropdown(items, category);
}

function onChatKeyDown(e) {
    const dropdown = document.getElementById('chatDropdown');
    const isOpen = dropdown && dropdown.style.display !== 'none' && chatDropdownItems.length > 0;

    if (isOpen) {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            chatDropdownIndex = Math.min(chatDropdownIndex + 1, chatDropdownItems.length - 1);
            highlightChatItem();
            return;
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            chatDropdownIndex = Math.max(chatDropdownIndex - 1, 0);
            highlightChatItem();
            return;
        }
        if (e.key === 'Tab' || (e.key === 'Enter' && chatDropdownIndex >= 0)) {
            e.preventDefault();
            if (chatDropdownIndex >= 0) {
                selectChatOption(chatDropdownIndex);
            } else if (chatDropdownItems.length > 0) {
                selectChatOption(0);
            }
            return;
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            closeChatDropdown();
            return;
        }
    }

    // Enter without dropdown selection → submit
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleChatSubmit();
        return;
    }

    // Escape while no dropdown → blur input
    if (e.key === 'Escape') {
        document.getElementById('chatInput').blur();
    }
}

// ===== COLOR HARMONY =====
function hexToHSL(hex) {
    if (!hex || hex.length < 7) return { h: 0, s: 0, l: 0.5 };
    let r = parseInt(hex.substr(1, 2), 16) / 255;
    let g = parseInt(hex.substr(3, 2), 16) / 255;
    let b = parseInt(hex.substr(5, 2), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h = 0, s = 0, l = (max + min) / 2;
    if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        else if (max === g) h = ((b - r) / d + 2) / 6;
        else h = ((r - g) / d + 4) / 6;
    }
    return { h: h * 360, s, l };
}

function hslToHex(h, s, l) {
    h = ((h % 360) + 360) % 360;
    const a = s * Math.min(l, 1 - l);
    const f = n => {
        const k = (n + h / 30) % 12;
        const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
        return Math.round(255 * Math.max(0, Math.min(1, color))).toString(16).padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
}

function getHarmonies(hex) {
    const { h, s, l } = hexToHSL(hex);
    return {
        complementary: [hslToHex(h + 180, s, l)],
        analogous: [hslToHex(h + 30, s, l), hslToHex(h - 30, s, l)],
        triadic: [hslToHex(h + 120, s, l), hslToHex(h + 240, s, l)],
        split: [hslToHex(h + 150, s, l), hslToHex(h + 210, s, l)],
    };
}

function renderHarmonyPanel(zone, zoneIndex) {
    // Get the zone's current color as hex
    let hex = null;
    if (zone.colorMode === 'picker' && zone.pickerColor) hex = zone.pickerColor;
    else if (zone.colorMode === 'multi' && zone.colors?.length > 0) {
        const c = zone.colors[0].color_rgb;
        hex = '#' + c.map(v => v.toString(16).padStart(2, '0')).join('');
    }
    if (!hex || hex.length < 7) return '';

    const harmonies = getHarmonies(hex);
    const { h } = hexToHSL(hex);

    // Build mini color wheel with dots
    const wheelR = 20; // radius for dot placement
    const cx = 25, cy = 25;
    function dotAt(hue, color) {
        const rad = (hue - 90) * Math.PI / 180;
        const x = cx + wheelR * Math.cos(rad);
        const y = cy + wheelR * Math.sin(rad);
        return `<div class="harmony-wheel-dot" style="left:${x}px;top:${y}px;background:${color};"></div>`;
    }

    let wheelDots = dotAt(h, hex); // current color
    harmonies.complementary.forEach(c => { wheelDots += dotAt(hexToHSL(c).h, c); });
    harmonies.triadic.forEach(c => { wheelDots += dotAt(hexToHSL(c).h, c); });

    function chipRow(label, colors) {
        const chips = colors.map(c =>
            `<div class="harmony-chip" style="background:${c};"
                 onclick="event.stopPropagation(); applyHarmonyColor(${zoneIndex}, '${c}')"
                 title="Click to apply ${c} to another zone"></div>`
        ).join('');
        return `<div class="harmony-row"><span class="harmony-type">${label}</span>${chips}</div>`;
    }

    return `<div class="harmony-panel" onclick="event.stopPropagation()">
        <div class="harmony-label">Color Harmony</div>
        <div style="display:flex;gap:10px;align-items:flex-start;">
            <div class="harmony-wheel">${wheelDots}</div>
            <div style="flex:1;">
                ${chipRow('Complement', harmonies.complementary)}
                ${chipRow('Analogous', harmonies.analogous)}
                ${chipRow('Triadic', harmonies.triadic)}
                ${chipRow('Split', harmonies.split)}
            </div>
        </div>
    </div>`;
}

function applyHarmonyColor(fromZoneIndex, hex) {
    // Apply to the NEXT zone that doesn't have a color yet, or prompt
    let targetIdx = -1;
    for (let i = 0; i < zones.length; i++) {
        if (i !== fromZoneIndex && (zones[i].colorMode === 'none' || zones[i].color === null)) {
            targetIdx = i;
            break;
        }
    }
    if (targetIdx === -1) {
        // All zones have colors, apply to next zone after current
        targetIdx = (fromZoneIndex + 1) % zones.length;
        if (targetIdx === fromZoneIndex) return;
    }

    const r = parseInt(hex.substr(1, 2), 16);
    const g = parseInt(hex.substr(3, 2), 16);
    const b = parseInt(hex.substr(5, 2), 16);
    zones[targetIdx].pickerColor = hex;
    zones[targetIdx].color = { color_rgb: [r, g, b], tolerance: zones[targetIdx].pickerTolerance || 40 };
    zones[targetIdx].colorMode = 'picker';
    zones[targetIdx].colors = [];
    selectedZoneIndex = targetIdx;
    renderZones();
    showToast(`Applied ${hex} to Zone ${targetIdx + 1}: ${zones[targetIdx].name}`);
}

// ===== SHORTCUT LEGEND =====
function showShortcutLegend() {
    let overlay = document.getElementById('shortcutLegendOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'shortcutLegendOverlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:10000;display:flex;align-items:center;justify-content:center;';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.style.display = 'none'; };
        overlay.innerHTML = `<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:24px 32px;max-width:520px;width:90%;max-height:80vh;overflow-y:auto;">
            <h3 style="margin:0 0 16px;color:var(--accent-gold);font-size:16px;">Keyboard Shortcuts</h3>
            <div style="display:grid;grid-template-columns:120px 1fr;gap:6px 16px;font-size:12px;">
                <span style="color:var(--accent);font-weight:700;">ZONES</span><span></span>
                <kbd style="color:var(--text-bright);">1-9</kbd><span style="color:var(--text-dim);">Select zone by number</span>
                <kbd style="color:var(--text-bright);">&#8593; / &#8595;</kbd><span style="color:var(--text-dim);">Navigate between zones</span>
                <kbd style="color:var(--text-bright);">Ctrl+&#8593; / &#8595;</kbd><span style="color:var(--text-dim);">Move zone up/down (reorder priority)</span>
                <kbd style="color:var(--text-bright);">N</kbd><span style="color:var(--text-dim);">Add new zone</span>
                <kbd style="color:var(--text-bright);">D</kbd><span style="color:var(--text-dim);">Duplicate selected zone</span>
                <kbd style="color:var(--text-bright);">Delete</kbd><span style="color:var(--text-dim);">Delete selected zone</span>
                <kbd style="color:var(--text-bright);">R</kbd><span style="color:var(--text-dim);">Randomize selected zone</span>
                <span style="color:var(--accent);font-weight:700;margin-top:8px;">ACTIONS</span><span></span>
                <kbd style="color:var(--text-bright);">Ctrl+R</kbd><span style="color:var(--text-dim);">Render</span>
                <kbd style="color:var(--text-bright);">Ctrl+G</kbd><span style="color:var(--text-dim);">Generate script</span>
                <kbd style="color:var(--text-bright);">Ctrl+S</kbd><span style="color:var(--text-dim);">Save config</span>
                <kbd style="color:var(--text-bright);">Ctrl+Z</kbd><span style="color:var(--text-dim);">Undo</span>
                <kbd style="color:var(--text-bright);">Ctrl+Shift+Z</kbd><span style="color:var(--text-dim);">Redo</span>
                <span style="color:var(--accent);font-weight:700;margin-top:8px;">CANVAS</span><span></span>
                <kbd style="color:var(--text-bright);">Space+Drag</kbd><span style="color:var(--text-dim);">Pan canvas</span>
                <kbd style="color:var(--text-bright);">Scroll</kbd><span style="color:var(--text-dim);">Zoom in/out</span>
                <kbd style="color:var(--text-bright);">/</kbd><span style="color:var(--text-dim);">Focus NLP chat input</span>
                <kbd style="color:var(--text-bright);">Escape</kbd><span style="color:var(--text-dim);">Close modal / exit compare</span>
                <span style="color:var(--accent);font-weight:700;margin-top:8px;">VIEW</span><span></span>
                <kbd style="color:var(--text-bright);">V</kbd><span style="color:var(--text-dim);">Toggle split view (live preview)</span>
                <kbd style="color:var(--text-bright);">H</kbd><span style="color:var(--text-dim);">History gallery</span>
                <kbd style="color:var(--text-bright);">T</kbd><span style="color:var(--text-dim);">Template library</span>
                <kbd style="color:var(--text-bright);">?</kbd><span style="color:var(--text-dim);">Show this legend</span>
            </div>
            <div style="margin-top:16px;text-align:center;"><button class="btn btn-sm" onclick="this.closest('#shortcutLegendOverlay').style.display='none'" style="padding:4px 20px;">Close</button></div>
        </div>`;
        document.body.appendChild(overlay);
    }
    overlay.style.display = 'flex';
}

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', (e) => {
    // Don't trigger when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

    // Ctrl+R: Render (if server online)
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        safeDoRender();
        return;
    }
    // Ctrl+G: Generate Script
    if (e.ctrlKey && e.key === 'g') {
        e.preventDefault();
        generateScript();
        return;
    }
    // 1-9: Select zone
    if (e.key >= '1' && e.key <= '9') {
        const idx = parseInt(e.key) - 1;
        if (idx < zones.length) {
            selectZone(idx);
        }
        return;
    }
    // R key (no ctrl): Randomize selected zone
    if (e.key === 'r' && !e.ctrlKey && !e.altKey) {
        randomizeZone(selectedZoneIndex);
        return;
    }
    // E key: Toggle zone editor panel collapse/expand
    if (e.key === 'e' && !e.ctrlKey && !e.altKey) {
        const floatPanel = document.getElementById('zoneEditorFloat');
        if (floatPanel && floatPanel.classList.contains('active')) {
            toggleZoneFloat();
            return;
        }
    }
    // / key: Focus chat input (NLP bar)
    if (e.key === '/') {
        e.preventDefault();
        document.getElementById('chatInput')?.focus();
        return;
    }
    // Arrow Up/Down: Navigate between zones
    if (e.key === 'ArrowUp' && !e.ctrlKey) {
        e.preventDefault();
        if (selectedZoneIndex > 0) selectZone(selectedZoneIndex - 1);
        return;
    }
    if (e.key === 'ArrowDown' && !e.ctrlKey) {
        e.preventDefault();
        if (selectedZoneIndex < zones.length - 1) selectZone(selectedZoneIndex + 1);
        return;
    }
    // Ctrl+Arrow: Move zone up/down in priority
    if (e.key === 'ArrowUp' && e.ctrlKey) {
        e.preventDefault();
        moveZoneUp(selectedZoneIndex);
        return;
    }
    if (e.key === 'ArrowDown' && e.ctrlKey) {
        e.preventDefault();
        moveZoneDown(selectedZoneIndex);
        return;
    }
    // D key: Duplicate selected zone
    if (e.key === 'd' && !e.ctrlKey && !e.altKey) {
        duplicateZone(selectedZoneIndex);
        return;
    }
    // Delete/Backspace: Delete selected zone
    if (e.key === 'Delete' || e.key === 'Backspace') {
        deleteZone(selectedZoneIndex);
        return;
    }
    // N key: Add new zone
    if (e.key === 'n' && !e.ctrlKey && !e.altKey) {
        addZone();
        return;
    }
    // V key: Toggle split view
    if (e.key === 'v' && !e.ctrlKey && !e.altKey) {
        toggleSplitView();
        return;
    }
    // ? key: Show keyboard shortcuts
    if (e.key === '?') {
        showShortcutLegend();
        return;
    }
    // H key: Open history gallery
    if (e.key === 'h' && !e.ctrlKey && !e.altKey) {
        openHistoryGallery();
        return;
    }
    // T key: Open template library
    if (e.key === 't' && !e.ctrlKey && !e.altKey) {
        openTemplateLibrary();
        return;
    }
    // Escape: exit compare mode / close gallery / close modal / close undo panel
    if (e.key === 'Escape') {
        if (document.getElementById('undoHistoryPanel')?.classList.contains('open')) { toggleUndoHistoryPanel(); return; }
        if (document.getElementById('historyGalleryOverlay')) { closeHistoryGallery(); return; }
        if (document.getElementById('templateLibraryOverlay')) { closeTemplateLibrary(); return; }
        if (document.getElementById('shortcutLegendOverlay')?.style.display === 'flex') {
            document.getElementById('shortcutLegendOverlay').style.display = 'none'; return;
        }
        if (typeof compareMode !== 'undefined' && compareMode) { toggleCompareMode(); return; }
        if (document.getElementById('finishCompareOverlay')?.classList.contains('active')) { closeFinishCompare(); return; }
        if (document.getElementById('finishBrowserOverlay')?.classList.contains('active')) { closeFinishBrowser(); return; }
        if (document.getElementById('presetGalleryOverlay')?.classList.contains('active')) { closePresetGallery(); return; }
        return;
    }
});

// ===== INIT ON LOAD =====
init();

// Auto-restore previous session BEFORE polling starts
const didRestore = autoRestore();

// Auto-save: listen for changes on ALL inputs in the sidebar
document.querySelectorAll('#car-info-body input, #car-info-body select').forEach(el => {
    el.addEventListener('change', autoSave);
    el.addEventListener('input', autoSave);
});

ShokkerAPI.startPolling();

// BUILD 25: Server build check (zombie process fix applied in Electron)
setTimeout(async () => {
    const el = document.getElementById('b21check');
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/build-check', { signal: AbortSignal.timeout(5000) });
        const rawText = await res.text();
        console.log('[BUILD-CHECK] status=' + res.status + ' raw=' + rawText.substring(0, 200));
        try {
            const d = JSON.parse(rawText);
            if (el) el.textContent = `[Server B${d.build} | PID:${d.pid} | port:${d.shokker_port_env}]`;
            document.title = `SPB v6.0 B28 - Server B${d.build} OK`;
        } catch (jsonErr) {
            if (el) el.textContent = `[HTTP ${res.status} NOT JSON: "${rawText.substring(0, 60)}..."]`;
            document.title = `SPB v6.0 B28 - NOT JSON (HTTP ${res.status})`;
        }
    } catch (e) {
        console.error('[BUILD-CHECK] FAILED:', e);
        if (el) el.textContent = `[BUILD-CHECK FAILED: ${e.message}]`;
        document.title = 'SPB v6.0 B28 - SERVER UNREACHABLE';
    }
}, 3000);
