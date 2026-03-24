// ============================================================
// PAINT-BOOTH-5-API-RENDER.JS - API, render, history gallery
// ============================================================
// Purpose: Finish hover popup, swatch hover popup, ShokkerAPI (server calls),
//          render pipeline (doRender, preview), render history gallery.
// Deps:    paint-booth-1-data.js, paint-booth-2-state-zones.js (zones, build payload).
// Edit:    Server API → ShokkerAPI, baseUrl. Render → doRender, safeDoRender.
//          History → openHistoryGallery, render history state.
// See:     PROJECT_STRUCTURE.md in this folder.
// ============================================================

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
        'dragon_scale': 'Pattern: image-based scales (Artistic & Cultural)',
        'dragon_scale_alt': 'Pattern: image-based vibrant scales',
        'aztec_alt1': 'Pattern: image-based geometric Aztec alt 1',
        'aztec_alt2': 'Pattern: image-based geometric Aztec alt 2',
        'fleur_de_lis': 'Pattern: image-based French lily motif',
        'fleur_de_lis_alt': 'Pattern: image-based damask lily',
        'japanese_wave': 'Pattern: image-based Kanagawa wave',
        'mandala': 'Pattern: image-based mandala',
        'mandela_ornate': 'Pattern: image-based ornate mandala',
        'mosaic': 'Pattern: image-based mosaic tiles',
        'muertos_dod1': 'Pattern: image-based Day of the Dead (dark)',
        'muertos_dod2': 'Pattern: image-based Day of the Dead (light)',
        'norse_rune': 'Pattern: image-based rune grid',
        'steampunk_gears': 'Pattern: image-based clockwork gears',
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
        'lava_flow': 'Pattern: molten cracks + variable CC',
        'rain_drop': 'Pattern: water beading, R-80 M+60',
        'barbed_wire': 'Pattern: twisted wire + barbs, R-100 M+130',
        'chainmail': 'Pattern: interlocking rings, R-90 M+100',
        // brick removed - Artistic & Cultural image-based
        'leopard': 'Pattern: organic rosette spots, R+50 M-60',
        'crocodile': 'Pattern: rectangular interlocking scales, R-80 M+70',
        'feather': 'Pattern: layered barbs from rachis shaft, R+40 M-20',
        'giraffe': 'Pattern: Voronoi polygon patches, R+30 M-40',
        'tiger_stripe': 'Pattern: noise-warped diagonal stripes, R-60 M+50',
        'zebra': 'Pattern: bold B/W organic stripes, R-40 M+30',
        'snake_skin_2': 'Pattern: diamond python scales, R-90 M+75',
        'snake_skin_3': 'Pattern: hourglass viper scales, R-85 M+70',
        'snake_skin_4': 'Pattern: cobblestone boa scales, R-70 M+60',
        'razor': 'Pattern: diagonal slash marks, R-80 M+120',
        // --- Expansion Pack Specials ---
        'oil_slick': 'Special: rainbow oil pools + variable roughness',
        'galaxy': 'Special: deep space nebula + star clusters',
        'rust': 'Special: progressive oxidation + no clearcoat',
        'neon_glow': 'Special: UV reactive fluorescent glow',
        'weathered_paint': 'Special: faded peeling layers to primer',
        // Your image patterns (patternexamples folder)
        '12155818_4903117': 'Pattern: image from file (tiled)',
        '12267458_4936872': 'Pattern: image from file (tiled)',
        '12284536_4958169': 'Pattern: image from file (tiled)',
        '12428555_4988298': 'Pattern: image from file (tiled)',
        '144644845_10133112': 'Pattern: image from file (tiled)',
        '17852162_5911715': 'Pattern: image from file (tiled)',
        '248169': 'Pattern: image from file (tiled)',
        '6868396_23455': 'Pattern: image from file (tiled)',
        '78534344_9837553_1': 'Pattern: image from file (tiled)',
        '8488198_3924387': 'Pattern: image from file (tiled)',
        'Groovy_Swirl': 'Pattern: image from file (60s/70s style)',
        'Halftone_Rainbow': 'Pattern: image from file (tiled)',
        'Plad_Wrapper': 'Pattern: image from file (tiled)',
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
            if (extras.paint_image_base64) body.paint_image_base64 = extras.paint_image_base64;
            if (extras.decal_mask_base64) body.decal_mask_base64 = extras.decal_mask_base64;
            if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;
        }
        this.resetStatusInterval(); // Reset polling backoff on every render
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

    async exportToPhotoshop(carFileName, exchangeFolder, paintFile, zones, extras) {
        const useCustomNumber = document.getElementById('useCustomNumberCheckbox')?.checked ?? true;
        const body = {
            paint_file: paintFile,
            zones: zones,
            seed: 51,
            car_file_name: carFileName,
            use_custom_number: useCustomNumber,
        };
        if (exchangeFolder && exchangeFolder.trim()) body.exchange_folder = exchangeFolder.trim();
        if (extras) {
            if (extras.import_spec_map) body.import_spec_map = extras.import_spec_map;
            if (extras.paint_image_base64) body.paint_image_base64 = extras.paint_image_base64;
            if (extras.decal_mask_base64) body.decal_mask_base64 = extras.decal_mask_base64;
            if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;
        }
        const res = await fetch(this.baseUrl + '/api/export-to-photoshop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        if (!res.ok && !data.error) data.error = `Server returned ${res.status}`;
        return data;
    },

    async getPhotoshopExchangeRoot() {
        const res = await fetch(this.baseUrl + '/api/photoshop-exchange-root');
        const data = await res.json();
        return data.path || '';
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
        // Combo count available internally but not displayed in header
        // const comboEl = document.getElementById('comboCount');
        if (llRow && this.config) {
            llRow.style.display = 'flex';
            const badge = document.getElementById('liveLinkBadge');
            if (!this._liveLinkSynced) {
                const cb = document.getElementById('liveLinkCheckbox');
                if (cb) { cb.checked = this.config.live_link_enabled || false; this._liveLinkSynced = true; }
            }
            if (badge) badge.style.display = this.config.live_link_enabled ? 'inline' : 'none';
        }
        // Sync car file naming checkbox from saved config (only on first load, not every poll)
        if (this.config && !this._customNumberSynced) {
            const cnCb = document.getElementById('useCustomNumberCheckbox');
            if (cnCb) { cnCb.checked = this.config.use_custom_number !== false; this._customNumberSynced = true; }
        }
    },

    startPolling() {
        this._statusInterval = 10000;
        this.checkStatus();
        const statusPoll = () => {
            this.checkStatus().then(() => {
                // Slow down polling when idle (no recent renders)
                this._statusInterval = Math.min(this._statusInterval * 1.5, 120000); // max 2 minutes
                setTimeout(statusPoll, this._statusInterval);
            }).catch(() => {
                setTimeout(statusPoll, this._statusInterval);
            });
        };
        setTimeout(statusPoll, this._statusInterval);
    },

    resetStatusInterval() {
        this._statusInterval = 10000;
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
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; if (z.patternStack?.length) { const st = z.patternStack.filter(l => l.id && l.id !== 'none'); if (st.length) zoneObj.pattern_stack = st.map(l => ({ id: l.id, opacity: (l.opacity ?? 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0, blend_mode: l.blendMode || 'normal' })); } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fm = MONOLITHICS.find(m => m.id === z.finish); let _fc = _fm ? { c1: _fm.swatch || null, c2: _fm.swatch2 || null, c3: _fm.swatch3 || null, ghost: _fm.ghostPattern || null } : null; if (!_fc && /^(grad_|gradm_|grad3_|ghostg_|mc_)/.test(z.finish) && typeof getFinishColorsForId === 'function') _fc = getFinishColorsForId(z.finish); if (_fc) zoneObj.finish_colors = _fc; if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } if (z.patternStack?.length) { const st = z.patternStack.filter(l => l.id && l.id !== 'none'); if (st.length) zoneObj.pattern_stack = st.map(l => ({ id: l.id, opacity: (l.opacity ?? 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0, blend_mode: l.blendMode || 'normal' })); } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        if (z.base || z.finish) {
            const _bMode = (z.baseColorMode || 'source');
            zoneObj.base_color_mode = _bMode;
            zoneObj.base_color_strength = Math.max(0, Math.min(1, Number(z.baseColorStrength ?? 1)));
            if (z.baseHueOffset) zoneObj.base_hue_offset = Number(z.baseHueOffset);
            if (z.baseSaturationAdjust) zoneObj.base_saturation_adjust = Number(z.baseSaturationAdjust);
            if (z.baseBrightnessAdjust) zoneObj.base_brightness_adjust = Number(z.baseBrightnessAdjust);
            if (_bMode === 'solid') {
                const _bHex = (z.baseColor || '#ffffff').toString();
                const hex = _bHex.length >= 7 ? _bHex : '#ffffff';
                zoneObj.base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            } else if (_bMode === 'special' && z.baseColorSource && z.baseColorSource !== 'undefined') {
                zoneObj.base_color_source = z.baseColorSource;
            }
        }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) { zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5))); zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5))); zoneObj.pattern_flip_h = !!z.patternFlipH; zoneObj.pattern_flip_v = !!z.patternFlipV; }
        if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge) zoneObj.hard_edge = true;
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) { zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5))); zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5))); zoneObj.base_rotation = Number(z.baseRotation ?? 0); zoneObj.base_flip_h = !!z.baseFlipH; zoneObj.base_flip_v = !!z.baseFlipV; }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // Spec pattern overlays
        if (z.specPatternStack && z.specPatternStack.length > 0) {
            zoneObj.spec_pattern_stack = z.specPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.overlaySpecPatternStack && z.overlaySpecPatternStack.length > 0) {
            zoneObj.overlay_spec_pattern_stack = z.overlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.thirdOverlaySpecPatternStack && z.thirdOverlaySpecPatternStack.length > 0) {
            zoneObj.third_overlay_spec_pattern_stack = z.thirdOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.fourthOverlaySpecPatternStack && z.fourthOverlaySpecPatternStack.length > 0) {
            zoneObj.fourth_overlay_spec_pattern_stack = z.fourthOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.fifthOverlaySpecPatternStack && z.fifthOverlaySpecPatternStack.length > 0) {
            zoneObj.fifth_overlay_spec_pattern_stack = z.fifthOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase && z.blendBase !== 'undefined' && z.blendBase !== 'none' && z.blendBase !== 'null') { zoneObj.blend_base = z.blendBase; zoneObj.blend_dir = z.blendDir || 'horizontal'; zoneObj.blend_amount = (z.blendAmount ?? 50) / 100; }
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // Dual Layer Base Overlay
        if ((z.secondBase || z.secondBaseColorSource) && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            if (z.secondBase && z.secondBase !== 'undefined') zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_spec_strength = z.secondBaseSpecStrength ?? 1;
            if (z.secondBaseColorSource && z.secondBaseColorSource !== 'undefined') zoneObj.second_base_color_source = z.secondBaseColorSource;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = Number(z.secondBaseNoiseScale ?? z.secondBaseFractalScale ?? 24);
            zoneObj.second_base_scale = Math.max(0.01, Math.min(5, Number(z.secondBaseScale) || 1));
            if (z.secondBasePattern) zoneObj.second_base_pattern = z.secondBasePattern;
            zoneObj.second_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.secondBasePatternOpacity ?? 100) / 100)));
            zoneObj.second_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.secondBasePatternScale ?? 1)));
            zoneObj.second_base_pattern_rotation = Number(z.secondBasePatternRotation ?? 0);
            zoneObj.second_base_pattern_strength = Math.max(0, Math.min(2, Number(z.secondBasePatternStrength ?? 1)));
            if (z.secondBasePatternInvert != null) zoneObj.second_base_pattern_invert = !!z.secondBasePatternInvert;
            if (z.secondBasePatternHarden != null) zoneObj.second_base_pattern_harden = !!z.secondBasePatternHarden;
            zoneObj.second_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetX ?? 0.5)));
            zoneObj.second_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetY ?? 0.5)));
            if (z.secondBaseFitZone) zoneObj.second_base_fit_zone = true;
        }
        if ((z.thirdBase || z.thirdBaseColorSource) && (z.thirdBaseStrength || 0) > 0) {
            const _tbColor = (z.thirdBaseColor || '#ffffff').toString();
            const hex = _tbColor.length >= 7 ? _tbColor : '#ffffff';
            if (z.thirdBase && z.thirdBase !== 'undefined') zoneObj.third_base = z.thirdBase;
            zoneObj.third_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.third_base_strength = z.thirdBaseStrength || 0;
            zoneObj.third_base_spec_strength = z.thirdBaseSpecStrength ?? 1;
            if (z.thirdBaseColorSource && z.thirdBaseColorSource !== 'undefined') zoneObj.third_base_color_source = z.thirdBaseColorSource;
            zoneObj.third_base_blend_mode = z.thirdBaseBlendMode || 'noise';
            zoneObj.third_base_noise_scale = Number(z.thirdBaseNoiseScale ?? z.thirdBaseFractalScale ?? 24);
            zoneObj.third_base_scale = Math.max(0.01, Math.min(5, Number(z.thirdBaseScale) || 1));
            if (z.thirdBasePattern) zoneObj.third_base_pattern = z.thirdBasePattern;
            zoneObj.third_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.thirdBasePatternOpacity ?? 100) / 100)));
            zoneObj.third_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.thirdBasePatternScale ?? 1)));
            zoneObj.third_base_pattern_rotation = Number(z.thirdBasePatternRotation ?? 0);
            zoneObj.third_base_pattern_strength = Math.max(0, Math.min(2, Number(z.thirdBasePatternStrength ?? 1)));
            if (z.thirdBasePatternInvert != null) zoneObj.third_base_pattern_invert = !!z.thirdBasePatternInvert;
            if (z.thirdBasePatternHarden != null) zoneObj.third_base_pattern_harden = !!z.thirdBasePatternHarden;
            zoneObj.third_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetX ?? 0.5)));
            zoneObj.third_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetY ?? 0.5)));
            if (z.thirdBaseFitZone) zoneObj.third_base_fit_zone = true;
        }
        if ((z.fourthBase || z.fourthBaseColorSource) && (z.fourthBaseStrength || 0) > 0) {
            const _fbColor = (z.fourthBaseColor || '#ffffff').toString();
            const hex = _fbColor.length >= 7 ? _fbColor : '#ffffff';
            if (z.fourthBase && z.fourthBase !== 'undefined') zoneObj.fourth_base = z.fourthBase;
            zoneObj.fourth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.fourth_base_strength = z.fourthBaseStrength || 0;
            zoneObj.fourth_base_spec_strength = z.fourthBaseSpecStrength ?? 1;
            if (z.fourthBaseColorSource && z.fourthBaseColorSource !== 'undefined') zoneObj.fourth_base_color_source = z.fourthBaseColorSource;
            zoneObj.fourth_base_blend_mode = z.fourthBaseBlendMode || 'noise';
            zoneObj.fourth_base_noise_scale = Number(z.fourthBaseNoiseScale ?? z.fourthBaseFractalScale ?? 24);
            zoneObj.fourth_base_scale = Math.max(0.01, Math.min(5, Number(z.fourthBaseScale) || 1));
            if (z.fourthBasePattern) zoneObj.fourth_base_pattern = z.fourthBasePattern;
            zoneObj.fourth_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.fourthBasePatternOpacity ?? 100) / 100)));
            zoneObj.fourth_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.fourthBasePatternScale ?? 1)));
            zoneObj.fourth_base_pattern_rotation = Number(z.fourthBasePatternRotation ?? 0);
            zoneObj.fourth_base_pattern_strength = Math.max(0, Math.min(2, Number(z.fourthBasePatternStrength ?? 1)));
            zoneObj.fourth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetX ?? 0.5)));
            zoneObj.fourth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetY ?? 0.5)));
            if (z.fourthBaseFitZone) zoneObj.fourth_base_fit_zone = true;
        }
        if ((z.fifthBase || z.fifthBaseColorSource) && (z.fifthBaseStrength || 0) > 0) {
            const _fifColor = (z.fifthBaseColor || '#ffffff').toString();
            const hex = _fifColor.length >= 7 ? _fifColor : '#ffffff';
            if (z.fifthBase && z.fifthBase !== 'undefined') zoneObj.fifth_base = z.fifthBase;
            zoneObj.fifth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.fifth_base_strength = z.fifthBaseStrength || 0;
            zoneObj.fifth_base_spec_strength = z.fifthBaseSpecStrength ?? 1;
            if (z.fifthBaseColorSource && z.fifthBaseColorSource !== 'undefined') zoneObj.fifth_base_color_source = z.fifthBaseColorSource;
            zoneObj.fifth_base_blend_mode = z.fifthBaseBlendMode || 'noise';
            zoneObj.fifth_base_noise_scale = Number(z.fifthBaseNoiseScale ?? z.fifthBaseFractalScale ?? 24);
            zoneObj.fifth_base_scale = Math.max(0.01, Math.min(5, Number(z.fifthBaseScale) || 1));
            if (z.fifthBasePattern) zoneObj.fifth_base_pattern = z.fifthBasePattern;
            zoneObj.fifth_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.fifthBasePatternOpacity ?? 100) / 100)));
            zoneObj.fifth_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.fifthBasePatternScale ?? 1)));
            zoneObj.fifth_base_pattern_rotation = Number(z.fifthBasePatternRotation ?? 0);
            zoneObj.fifth_base_pattern_strength = Math.max(0, Math.min(2, Number(z.fifthBasePatternStrength ?? 1)));
            zoneObj.fifth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetX ?? 0.5)));
            zoneObj.fifth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetY ?? 0.5)));
            if (z.fifthBaseFitZone) zoneObj.fifth_base_fit_zone = true;
        }
        return zoneObj;
    });

    const extras = {};
    const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
    if (wearLevel > 0) extras.wear_level = wearLevel;
    const fleetSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
    if (fleetSpecPath) extras.import_spec_map = fleetSpecPath;

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
        if (z.base) { zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none'; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation; if (z.baseRotation && z.baseRotation !== 0) zoneObj.base_rotation = z.baseRotation; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; if (z.patternStack?.length) { const st = z.patternStack.filter(l => l.id && l.id !== 'none'); if (st.length) zoneObj.pattern_stack = st.map(l => ({ id: l.id, opacity: (l.opacity ?? 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0, blend_mode: l.blendMode || 'normal' })); } } else if (z.finish) { zoneObj.finish = z.finish; const _fr = z.baseRotation || z.rotation || 0; if (_fr && _fr !== 0) zoneObj.rotation = _fr; const _fm = MONOLITHICS.find(m => m.id === z.finish); let _fc = _fm ? { c1: _fm.swatch || null, c2: _fm.swatch2 || null, c3: _fm.swatch3 || null, ghost: _fm.ghostPattern || null } : null; if (!_fc && /^(grad_|gradm_|grad3_|ghostg_|mc_)/.test(z.finish) && typeof getFinishColorsForId === 'function') _fc = getFinishColorsForId(z.finish); if (_fc) zoneObj.finish_colors = _fc; if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; } if (z.patternStack?.length) { const st = z.patternStack.filter(l => l.id && l.id !== 'none'); if (st.length) zoneObj.pattern_stack = st.map(l => ({ id: l.id, opacity: (l.opacity ?? 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0, blend_mode: l.blendMode || 'normal' })); } }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        if (z.base || z.finish) {
            const _bMode = (z.baseColorMode || 'source');
            zoneObj.base_color_mode = _bMode;
            zoneObj.base_color_strength = Math.max(0, Math.min(1, Number(z.baseColorStrength ?? 1)));
            if (z.baseHueOffset) zoneObj.base_hue_offset = Number(z.baseHueOffset);
            if (z.baseSaturationAdjust) zoneObj.base_saturation_adjust = Number(z.baseSaturationAdjust);
            if (z.baseBrightnessAdjust) zoneObj.base_brightness_adjust = Number(z.baseBrightnessAdjust);
            if (_bMode === 'solid') {
                const _bHex = (z.baseColor || '#ffffff').toString();
                const hex = _bHex.length >= 7 ? _bHex : '#ffffff';
                zoneObj.base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            } else if (_bMode === 'special' && z.baseColorSource && z.baseColorSource !== 'undefined') {
                zoneObj.base_color_source = z.baseColorSource;
            }
        }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) { zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5))); zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5))); zoneObj.pattern_flip_h = !!z.patternFlipH; zoneObj.pattern_flip_v = !!z.patternFlipV; }
        if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge) zoneObj.hard_edge = true;
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) { zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5))); zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5))); zoneObj.base_rotation = Number(z.baseRotation ?? 0); zoneObj.base_flip_h = !!z.baseFlipH; zoneObj.base_flip_v = !!z.baseFlipV; }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // Spec pattern overlays
        if (z.specPatternStack && z.specPatternStack.length > 0) {
            zoneObj.spec_pattern_stack = z.specPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.overlaySpecPatternStack && z.overlaySpecPatternStack.length > 0) {
            zoneObj.overlay_spec_pattern_stack = z.overlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.thirdOverlaySpecPatternStack && z.thirdOverlaySpecPatternStack.length > 0) {
            zoneObj.third_overlay_spec_pattern_stack = z.thirdOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.fourthOverlaySpecPatternStack && z.fourthOverlaySpecPatternStack.length > 0) {
            zoneObj.fourth_overlay_spec_pattern_stack = z.fourthOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.fifthOverlaySpecPatternStack && z.fifthOverlaySpecPatternStack.length > 0) {
            zoneObj.fifth_overlay_spec_pattern_stack = z.fifthOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        // v6.0 advanced finish params
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase && z.blendBase !== 'undefined' && z.blendBase !== 'none' && z.blendBase !== 'null') { zoneObj.blend_base = z.blendBase; zoneObj.blend_dir = z.blendDir || 'horizontal'; zoneObj.blend_amount = (z.blendAmount ?? 50) / 100; }
        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
        // Dual Layer Base Overlay
        if ((z.secondBase || z.secondBaseColorSource) && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            if (z.secondBase && z.secondBase !== 'undefined') zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_spec_strength = z.secondBaseSpecStrength ?? 1;
            if (z.secondBaseColorSource && z.secondBaseColorSource !== 'undefined') zoneObj.second_base_color_source = z.secondBaseColorSource;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = Number(z.secondBaseNoiseScale ?? z.secondBaseFractalScale ?? 24);
            zoneObj.second_base_scale = Math.max(0.01, Math.min(5, Number(z.secondBaseScale) || 1));
            if (z.secondBasePattern) zoneObj.second_base_pattern = z.secondBasePattern;
            zoneObj.second_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.secondBasePatternOpacity ?? 100) / 100)));
            zoneObj.second_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.secondBasePatternScale ?? 1)));
            zoneObj.second_base_pattern_rotation = Number(z.secondBasePatternRotation ?? 0);
            zoneObj.second_base_pattern_strength = Math.max(0, Math.min(2, Number(z.secondBasePatternStrength ?? 1)));
            if (z.secondBasePatternInvert != null) zoneObj.second_base_pattern_invert = !!z.secondBasePatternInvert;
            if (z.secondBasePatternHarden != null) zoneObj.second_base_pattern_harden = !!z.secondBasePatternHarden;
            zoneObj.second_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetX ?? 0.5)));
            zoneObj.second_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetY ?? 0.5)));
            if (z.secondBaseFitZone) zoneObj.second_base_fit_zone = true;
        }
        if ((z.thirdBase || z.thirdBaseColorSource) && (z.thirdBaseStrength || 0) > 0) {
            const _tbColor = (z.thirdBaseColor || '#ffffff').toString();
            const hex = _tbColor.length >= 7 ? _tbColor : '#ffffff';
            if (z.thirdBase && z.thirdBase !== 'undefined') zoneObj.third_base = z.thirdBase;
            zoneObj.third_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.third_base_strength = z.thirdBaseStrength || 0;
            zoneObj.third_base_spec_strength = z.thirdBaseSpecStrength ?? 1;
            if (z.thirdBaseColorSource && z.thirdBaseColorSource !== 'undefined') zoneObj.third_base_color_source = z.thirdBaseColorSource;
            zoneObj.third_base_blend_mode = z.thirdBaseBlendMode || 'noise';
            zoneObj.third_base_noise_scale = Number(z.thirdBaseNoiseScale ?? z.thirdBaseFractalScale ?? 24);
            zoneObj.third_base_scale = Math.max(0.01, Math.min(5, Number(z.thirdBaseScale) || 1));
            if (z.thirdBasePattern) zoneObj.third_base_pattern = z.thirdBasePattern;
            zoneObj.third_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.thirdBasePatternOpacity ?? 100) / 100)));
            zoneObj.third_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.thirdBasePatternScale ?? 1)));
            zoneObj.third_base_pattern_rotation = Number(z.thirdBasePatternRotation ?? 0);
            zoneObj.third_base_pattern_strength = Math.max(0, Math.min(2, Number(z.thirdBasePatternStrength ?? 1)));
            if (z.thirdBasePatternInvert != null) zoneObj.third_base_pattern_invert = !!z.thirdBasePatternInvert;
            if (z.thirdBasePatternHarden != null) zoneObj.third_base_pattern_harden = !!z.thirdBasePatternHarden;
            zoneObj.third_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetX ?? 0.5)));
            zoneObj.third_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetY ?? 0.5)));
            if (z.thirdBaseFitZone) zoneObj.third_base_fit_zone = true;
        }
        if ((z.fourthBase || z.fourthBaseColorSource) && (z.fourthBaseStrength || 0) > 0) {
            const _fbColor = (z.fourthBaseColor || '#ffffff').toString();
            const hex = _fbColor.length >= 7 ? _fbColor : '#ffffff';
            if (z.fourthBase && z.fourthBase !== 'undefined') zoneObj.fourth_base = z.fourthBase;
            zoneObj.fourth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.fourth_base_strength = z.fourthBaseStrength || 0;
            zoneObj.fourth_base_spec_strength = z.fourthBaseSpecStrength ?? 1;
            if (z.fourthBaseColorSource && z.fourthBaseColorSource !== 'undefined') zoneObj.fourth_base_color_source = z.fourthBaseColorSource;
            zoneObj.fourth_base_blend_mode = z.fourthBaseBlendMode || 'noise';
            zoneObj.fourth_base_noise_scale = Number(z.fourthBaseNoiseScale ?? z.fourthBaseFractalScale ?? 24);
            zoneObj.fourth_base_scale = Math.max(0.01, Math.min(5, Number(z.fourthBaseScale) || 1));
            if (z.fourthBasePattern) zoneObj.fourth_base_pattern = z.fourthBasePattern;
            zoneObj.fourth_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.fourthBasePatternOpacity ?? 100) / 100)));
            zoneObj.fourth_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.fourthBasePatternScale ?? 1)));
            zoneObj.fourth_base_pattern_rotation = Number(z.fourthBasePatternRotation ?? 0);
            zoneObj.fourth_base_pattern_strength = Math.max(0, Math.min(2, Number(z.fourthBasePatternStrength ?? 1)));
            zoneObj.fourth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetX ?? 0.5)));
            zoneObj.fourth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetY ?? 0.5)));
            if (z.fourthBaseFitZone) zoneObj.fourth_base_fit_zone = true;
        }
        if ((z.fifthBase || z.fifthBaseColorSource) && (z.fifthBaseStrength || 0) > 0) {
            const _fifColor = (z.fifthBaseColor || '#ffffff').toString();
            const hex = _fifColor.length >= 7 ? _fifColor : '#ffffff';
            if (z.fifthBase && z.fifthBase !== 'undefined') zoneObj.fifth_base = z.fifthBase;
            zoneObj.fifth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.fifth_base_strength = z.fifthBaseStrength || 0;
            zoneObj.fifth_base_spec_strength = z.fifthBaseSpecStrength ?? 1;
            if (z.fifthBaseColorSource && z.fifthBaseColorSource !== 'undefined') zoneObj.fifth_base_color_source = z.fifthBaseColorSource;
            zoneObj.fifth_base_blend_mode = z.fifthBaseBlendMode || 'noise';
            zoneObj.fifth_base_noise_scale = Number(z.fifthBaseNoiseScale ?? z.fifthBaseFractalScale ?? 24);
            zoneObj.fifth_base_scale = Math.max(0.01, Math.min(5, Number(z.fifthBaseScale) || 1));
            if (z.fifthBasePattern) zoneObj.fifth_base_pattern = z.fifthBasePattern;
            zoneObj.fifth_base_pattern_opacity = Math.max(0, Math.min(1, Number((z.fifthBasePatternOpacity ?? 100) / 100)));
            zoneObj.fifth_base_pattern_scale = Math.max(0.1, Math.min(4, Number(z.fifthBasePatternScale ?? 1)));
            zoneObj.fifth_base_pattern_rotation = Number(z.fifthBasePatternRotation ?? 0);
            zoneObj.fifth_base_pattern_strength = Math.max(0, Math.min(2, Number(z.fifthBasePatternStrength ?? 1)));
            zoneObj.fifth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetX ?? 0.5)));
            zoneObj.fifth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetY ?? 0.5)));
            if (z.fifthBaseFitZone) zoneObj.fifth_base_fit_zone = true;
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

/** Build server zone payload (same for preview and full render so paint file matches live preview). */
function buildServerZonesForRender(zones) {
    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
    return validZones.map(z => {
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
            zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
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
            const _finishRot = z.baseRotation || z.rotation || 0;
            if (_finishRot && _finishRot !== 0) zoneObj.rotation = _finishRot;
            const _fMono = typeof MONOLITHICS !== 'undefined' && MONOLITHICS.find(m => m.id === z.finish);
            let fc = _fMono ? { c1: _fMono.swatch || null, c2: _fMono.swatch2 || null, c3: _fMono.swatch3 || null, ghost: _fMono.ghostPattern || null } : null;
            if (!fc && typeof getFinishColorsForId === 'function' && /^(grad_|gradm_|grad3_|ghostg_)/.test(z.finish)) fc = getFinishColorsForId(z.finish);
            if (fc) zoneObj.finish_colors = fc;
            if (z.pattern && z.pattern !== 'none') {
                zoneObj.pattern = z.pattern;
                if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
                zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
            }
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
        }
        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
        if (z.baseSpecBlendMode && z.baseSpecBlendMode !== 'normal') zoneObj.base_spec_blend_mode = z.baseSpecBlendMode;
        if (z.base || z.finish) {
            const _bMode = (z.baseColorMode || 'source');
            zoneObj.base_color_mode = _bMode;
            zoneObj.base_color_strength = Math.max(0, Math.min(1, Number(z.baseColorStrength ?? 1)));
            if (z.baseHueOffset) zoneObj.base_hue_offset = Number(z.baseHueOffset);
            if (z.baseSaturationAdjust) zoneObj.base_saturation_adjust = Number(z.baseSaturationAdjust);
            if (z.baseBrightnessAdjust) zoneObj.base_brightness_adjust = Number(z.baseBrightnessAdjust);
            if (_bMode === 'solid') {
                const _bHex = (z.baseColor || '#ffffff').toString();
                const hex = _bHex.length >= 7 ? _bHex : '#ffffff';
                zoneObj.base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            } else if (_bMode === 'special' && z.baseColorSource && z.baseColorSource !== 'undefined') {
                zoneObj.base_color_source = z.baseColorSource;
            }
        }
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) {
            zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5)));
            zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5)));
            zoneObj.pattern_flip_h = !!z.patternFlipH;
            zoneObj.pattern_flip_v = !!z.patternFlipV;
        }
        if (z.patternPlacement === 'fit' || z.patternFitZone) zoneObj.pattern_fit_zone = true;
        if (z.hardEdge) zoneObj.hard_edge = true;
        if (z.patternPlacement === 'manual') zoneObj.pattern_manual = true;
        if (z.base || z.finish) {
            zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5)));
            zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5)));
            zoneObj.base_rotation = Number(z.baseRotation ?? 0);
            zoneObj.base_flip_h = !!z.baseFlipH;
            zoneObj.base_flip_v = !!z.baseFlipV;
        }
        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
        // Spec pattern overlays
        if (z.specPatternStack && z.specPatternStack.length > 0) {
            zoneObj.spec_pattern_stack = z.specPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.overlaySpecPatternStack && z.overlaySpecPatternStack.length > 0) {
            zoneObj.overlay_spec_pattern_stack = z.overlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.thirdOverlaySpecPatternStack && z.thirdOverlaySpecPatternStack.length > 0) {
            zoneObj.third_overlay_spec_pattern_stack = z.thirdOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.fourthOverlaySpecPatternStack && z.fourthOverlaySpecPatternStack.length > 0) {
            zoneObj.fourth_overlay_spec_pattern_stack = z.fourthOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if (z.fifthOverlaySpecPatternStack && z.fifthOverlaySpecPatternStack.length > 0) {
            zoneObj.fifth_overlay_spec_pattern_stack = z.fifthOverlaySpecPatternStack.map(sp => ({
                pattern: sp.pattern,
                opacity: (sp.opacity ?? 50) / 100,
                blend_mode: sp.blendMode || 'normal',
                channels: sp.channels || 'MR',
                range: sp.range || 40,
                params: sp.params || {},
                offset_x: sp.offsetX || 0.5,
                offset_y: sp.offsetY || 0.5,
                scale: sp.scale || 1.0,
                rotation: sp.rotation || 0
            }));
        }
        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
        if (z.blendBase && z.blendBase !== 'undefined' && z.blendBase !== 'none' && z.blendBase !== 'null') {
            zoneObj.blend_base = z.blendBase;
            zoneObj.blend_dir = z.blendDir || 'horizontal';
            zoneObj.blend_amount = (z.blendAmount ?? 50) / 100;
        }
        if (z.usePaintReactive && z.paintReactiveColor) {
            const _pc = z.paintReactiveColor;
            zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255];
        }
        // 2nd–5th base overlays (same as doRender)
        if ((z.secondBase || z.secondBaseColorSource) && (z.secondBaseStrength || 0) > 0) {
            const _sbColor = z.secondBaseColor || '#ffffff';
            if (z.secondBase && z.secondBase !== 'undefined') zoneObj.second_base = z.secondBase;
            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
            zoneObj.second_base_strength = z.secondBaseStrength || 0;
            zoneObj.second_base_spec_strength = z.secondBaseSpecStrength ?? 1;
            if (z.secondBaseColorSource && z.secondBaseColorSource !== 'undefined') zoneObj.second_base_color_source = z.secondBaseColorSource;
            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
            zoneObj.second_base_noise_scale = Number(z.secondBaseNoiseScale ?? z.secondBaseFractalScale ?? 24);
            zoneObj.second_base_scale = Math.max(0.01, Math.min(5, Number(z.secondBaseScale) || 1));
            if (z.secondBasePattern) zoneObj.second_base_pattern = z.secondBasePattern;
            if (z.secondBasePatternOpacity != null) zoneObj.second_base_pattern_opacity = (z.secondBasePatternOpacity ?? 100) / 100;
            if (z.secondBasePatternScale != null) zoneObj.second_base_pattern_scale = Number(z.secondBasePatternScale) || 1;
            if (z.secondBasePatternRotation != null) zoneObj.second_base_pattern_rotation = Number(z.secondBasePatternRotation) || 0;
            if (z.secondBasePatternStrength != null) zoneObj.second_base_pattern_strength = Number(z.secondBasePatternStrength) ?? 1;
            if (z.secondBasePatternInvert != null) zoneObj.second_base_pattern_invert = !!z.secondBasePatternInvert;
            if (z.secondBasePatternHarden != null) zoneObj.second_base_pattern_harden = !!z.secondBasePatternHarden;
            zoneObj.second_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetX ?? 0.5)));
            zoneObj.second_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetY ?? 0.5)));
            if (z.secondBaseFitZone) zoneObj.second_base_fit_zone = true;
        }
        if ((z.thirdBase || z.thirdBaseColorSource) && (z.thirdBaseStrength || 0) > 0) {
            const _tbColor = (z.thirdBaseColor || '#ffffff').toString();
            const hex = _tbColor.length >= 7 ? _tbColor : '#ffffff';
            if (z.thirdBase && z.thirdBase !== 'undefined') zoneObj.third_base = z.thirdBase;
            zoneObj.third_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.third_base_strength = z.thirdBaseStrength || 0;
            zoneObj.third_base_spec_strength = z.thirdBaseSpecStrength ?? 1;
            if (z.thirdBaseColorSource && z.thirdBaseColorSource !== 'undefined') zoneObj.third_base_color_source = z.thirdBaseColorSource;
            zoneObj.third_base_blend_mode = z.thirdBaseBlendMode || 'noise';
            zoneObj.third_base_noise_scale = Number(z.thirdBaseNoiseScale ?? z.thirdBaseFractalScale ?? 24);
            zoneObj.third_base_scale = Math.max(0.01, Math.min(5, Number(z.thirdBaseScale) || 1));
            if (z.thirdBasePattern) zoneObj.third_base_pattern = z.thirdBasePattern;
            if (z.thirdBasePatternOpacity != null) zoneObj.third_base_pattern_opacity = (z.thirdBasePatternOpacity ?? 100) / 100;
            if (z.thirdBasePatternScale != null) zoneObj.third_base_pattern_scale = Number(z.thirdBasePatternScale) || 1;
            if (z.thirdBasePatternRotation != null) zoneObj.third_base_pattern_rotation = Number(z.thirdBasePatternRotation) || 0;
            if (z.thirdBasePatternStrength != null) zoneObj.third_base_pattern_strength = Number(z.thirdBasePatternStrength) ?? 1;
            if (z.thirdBasePatternInvert != null) zoneObj.third_base_pattern_invert = !!z.thirdBasePatternInvert;
            if (z.thirdBasePatternHarden != null) zoneObj.third_base_pattern_harden = !!z.thirdBasePatternHarden;
            zoneObj.third_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetX ?? 0.5)));
            zoneObj.third_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetY ?? 0.5)));
            if (z.thirdBaseFitZone) zoneObj.third_base_fit_zone = true;
        }
        if ((z.fourthBase || z.fourthBaseColorSource) && (z.fourthBaseStrength || 0) > 0) {
            const _fbColor = (z.fourthBaseColor || '#ffffff').toString();
            const hex = _fbColor.length >= 7 ? _fbColor : '#ffffff';
            if (z.fourthBase && z.fourthBase !== 'undefined') zoneObj.fourth_base = z.fourthBase;
            zoneObj.fourth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.fourth_base_strength = z.fourthBaseStrength || 0;
            zoneObj.fourth_base_spec_strength = z.fourthBaseSpecStrength ?? 1;
            if (z.fourthBaseColorSource && z.fourthBaseColorSource !== 'undefined') zoneObj.fourth_base_color_source = z.fourthBaseColorSource;
            zoneObj.fourth_base_blend_mode = z.fourthBaseBlendMode || 'noise';
            zoneObj.fourth_base_noise_scale = Number(z.fourthBaseNoiseScale ?? z.fourthBaseFractalScale ?? 24);
            zoneObj.fourth_base_scale = Math.max(0.01, Math.min(5, Number(z.fourthBaseScale) || 1));
            if (z.fourthBasePattern) zoneObj.fourth_base_pattern = z.fourthBasePattern;
            if (z.fourthBasePatternOpacity != null) zoneObj.fourth_base_pattern_opacity = (z.fourthBasePatternOpacity ?? 100) / 100;
            if (z.fourthBasePatternScale != null) zoneObj.fourth_base_pattern_scale = Number(z.fourthBasePatternScale) || 1;
            if (z.fourthBasePatternRotation != null) zoneObj.fourth_base_pattern_rotation = Number(z.fourthBasePatternRotation) || 0;
            if (z.fourthBasePatternStrength != null) zoneObj.fourth_base_pattern_strength = Number(z.fourthBasePatternStrength) ?? 1;
            if (z.fourthBasePatternInvert != null) zoneObj.fourth_base_pattern_invert = !!z.fourthBasePatternInvert;
            if (z.fourthBasePatternHarden != null) zoneObj.fourth_base_pattern_harden = !!z.fourthBasePatternHarden;
            zoneObj.fourth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetX ?? 0.5)));
            zoneObj.fourth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetY ?? 0.5)));
            if (z.fourthBaseFitZone) zoneObj.fourth_base_fit_zone = true;
        }
        if ((z.fifthBase || z.fifthBaseColorSource) && (z.fifthBaseStrength || 0) > 0) {
            const _fifColor = (z.fifthBaseColor || '#ffffff').toString();
            const hex = _fifColor.length >= 7 ? _fifColor : '#ffffff';
            if (z.fifthBase && z.fifthBase !== 'undefined') zoneObj.fifth_base = z.fifthBase;
            zoneObj.fifth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
            zoneObj.fifth_base_strength = z.fifthBaseStrength || 0;
            zoneObj.fifth_base_spec_strength = z.fifthBaseSpecStrength ?? 1;
            if (z.fifthBaseColorSource && z.fifthBaseColorSource !== 'undefined') zoneObj.fifth_base_color_source = z.fifthBaseColorSource;
            zoneObj.fifth_base_blend_mode = z.fifthBaseBlendMode || 'noise';
            zoneObj.fifth_base_noise_scale = Number(z.fifthBaseNoiseScale ?? z.fifthBaseFractalScale ?? 24);
            zoneObj.fifth_base_scale = Math.max(0.01, Math.min(5, Number(z.fifthBaseScale) || 1));
            if (z.fifthBasePattern) zoneObj.fifth_base_pattern = z.fifthBasePattern;
            if (z.fifthBasePatternOpacity != null) zoneObj.fifth_base_pattern_opacity = (z.fifthBasePatternOpacity ?? 100) / 100;
            if (z.fifthBasePatternScale != null) zoneObj.fifth_base_pattern_scale = Number(z.fifthBasePatternScale) || 1;
            if (z.fifthBasePatternRotation != null) zoneObj.fifth_base_pattern_rotation = Number(z.fifthBasePatternRotation) || 0;
            if (z.fifthBasePatternStrength != null) zoneObj.fifth_base_pattern_strength = Number(z.fifthBasePatternStrength) ?? 1;
            if (z.fifthBasePatternInvert != null) zoneObj.fifth_base_pattern_invert = !!z.fifthBasePatternInvert;
            if (z.fifthBasePatternHarden != null) zoneObj.fifth_base_pattern_harden = !!z.fifthBasePatternHarden;
            zoneObj.fifth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetX ?? 0.5)));
            zoneObj.fifth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetY ?? 0.5)));
            if (z.fifthBaseFitZone) zoneObj.fifth_base_fit_zone = true;
        }
        const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);
        if (!hasSpatialRefinement && z.regionMask && z.regionMask.some(v => v > 0)) {
            const pc = document.getElementById('paintCanvas');
            if (pc) zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height);
        }
        if (hasSpatialRefinement) {
            const pc = document.getElementById('paintCanvas');
            if (pc) zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height);
        }
        return zoneObj;
    });
}
if (typeof window !== 'undefined') window.buildServerZonesForRender = buildServerZonesForRender;

// --- Photoshop round-trip: Export modal + Import ---
const PS_EXPORT_FOLDER_KEY = 'shokker_ps_export_folder';

function openExportToPhotoshopModal() {
    const modal = document.getElementById('exportToPhotoshopModal');
    const exchangeInput = document.getElementById('psExportExchangeFolder');
    if (modal) modal.classList.add('active');
    // Pre-fill export folder: saved preference first, then server default
    if (exchangeInput) {
        const saved = (typeof localStorage !== 'undefined' && localStorage.getItem(PS_EXPORT_FOLDER_KEY)) || '';
        if (saved) {
            exchangeInput.value = saved;
        } else if (ShokkerAPI.online) {
            ShokkerAPI.getPhotoshopExchangeRoot().then(function (path) {
                if (path) exchangeInput.value = path;
            }).catch(function () {});
        }
    }
}

function closeExportToPhotoshopModal() {
    const modal = document.getElementById('exportToPhotoshopModal');
    if (modal) modal.classList.remove('active');
}

async function doExportToPhotoshop() {
    if (!ShokkerAPI.online) { showToast('Server is offline. Start server.py first.', true); return; }
    const carFileName = (document.getElementById('psExportCarFileName') || {}).value.trim();
    if (!carFileName) { showToast('Enter a car file name (e.g. DLM438-base-001).', true); return; }
    const exchangeFolder = (document.getElementById('psExportExchangeFolder') || {}).value.trim();
    const paintFile = (document.getElementById('paintFile') || {}).value.trim();
    if (!paintFile) { showToast('Set the Source Paint path in the header bar first.', true); return; }

    const serverZones = buildServerZonesForRender(typeof zones !== 'undefined' ? zones : []);
    const extras = {};
    const exportSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
    if (exportSpecPath) extras.import_spec_map = exportSpecPath;
    if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
        const compositeCanvas = compositeDecalsForRender();
        if (compositeCanvas) extras.paint_image_base64 = compositeCanvas.toDataURL('image/png');
        // Also send the decal-only alpha mask for correct spec stamping
        if (typeof compositeDecalMaskForRender === 'function') {
            const maskDataUrl = compositeDecalMaskForRender();
            if (maskDataUrl) extras.decal_mask_base64 = maskDataUrl;
        }
    }
    // Spec Stamps for PS export
    if (typeof compositeStampsForRender === 'function' && typeof window.stampLayers !== 'undefined' && window.stampLayers.length > 0) {
        const stampCanvas = compositeStampsForRender();
        if (stampCanvas) {
            extras.stamp_image_base64 = stampCanvas.toDataURL('image/png');
            extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';
        }
    }

    const btn = document.getElementById('btnDoExportToPs');
    if (btn) { btn.disabled = true; btn.textContent = 'Exporting...'; }
    try {
        const result = await ShokkerAPI.exportToPhotoshop(carFileName, exchangeFolder || undefined, paintFile, serverZones, extras);
        if (result.error) { showToast('Export failed: ' + result.error, true); return; }
        // Remember the folder we used (exchange root) for next time
        if (result.exchange_dir && typeof localStorage !== 'undefined') {
            const root = result.exchange_dir.replace(/[/\\][^/\\]+$/, '');
            if (root) localStorage.setItem(PS_EXPORT_FOLDER_KEY, root);
        } else if (exchangeFolder && typeof localStorage !== 'undefined') {
            localStorage.setItem(PS_EXPORT_FOLDER_KEY, exchangeFolder);
        }
        showToast('Exported to Photoshop: ' + (result.exchange_dir || carFileName));
        closeExportToPhotoshopModal();
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Export'; }
    }
}

// One-click: import spec map from last PS export
async function importSpecFromLastExport() {
    if (!ShokkerAPI.online) { showToast('Server is offline. Start server.py first.', true); return; }
    var folder = (typeof localStorage !== 'undefined' && localStorage.getItem(PS_EXPORT_FOLDER_KEY)) || '';
    showToast('Loading spec from last PS export...');
    try {
        var res = await fetch(ShokkerAPI.baseUrl + '/api/photoshop-import-spec-from-last-export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exchange_folder: folder || undefined }),
        });
        var data;
        try { data = await res.json(); } catch (e) {
            showToast('Server returned invalid response. Restart the server after code changes.', true);
            return;
        }
        if (data.error) {
            if (data.error === 'not_found') showToast('Server needs to be restarted to load the new import endpoint.', true);
            else showToast(data.error, true);
            return;
        }
        if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = data.temp_path;
        var status = document.getElementById('importSpecMapStatus');
        var label = data.source_file || 'spec from PS export';
        if (status && data.resolution) status.innerHTML = '<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active · Layer 0</span> — ' + label + ' (' + data.resolution[0] + '×' + data.resolution[1] + ')';
        var clearBtn = document.getElementById('btnClearSpecMap');
        if (clearBtn) clearBtn.disabled = false;
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        showToast('Spec loaded: ' + label);
    } catch (err) {
        showToast('Failed to import spec: ' + (err.message || 'unknown error'), true);
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

    // Build zone configs for the server (same builder used by live preview so paint file matches)
    const serverZones = buildServerZonesForRender(zones);
    console.log('[doRender] Valid zones:', serverZones.length, '/', zones.length, 'total');
    if (serverZones.length === 0 && !importedSpecMapPath) {
        const debugInfo = zones.map((z, i) => `Zone${i + 1}[${z.name}]: base=${z.base} finish=${z.finish} color=${z.color} colorMode=${z.colorMode}`).join('\n');
        console.warn('[doRender] No valid zones! Zone details:\n' + debugInfo);
        showToast('To render: pick a color on the paint (Pick + Add), then assign a Finish from the library to each zone. Both are required.', true);
        return;
    }
    if (serverZones.length > 0 && serverZones.length < zones.length) {
        const skipped = zones.length - serverZones.length;
        showToast(`Rendering ${serverZones.length} zones. ${skipped} skipped — assign a Finish + color to include them.`, false);
    }
    if (serverZones.length === 0 && importedSpecMapPath) {
        console.log('[doRender] No user zones, but imported spec canvas exists - rendering with spec canvas only');
        showToast('Rendering with Spec Canvas only (no zone overrides)...');
    }

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

    // Import spec map (merge mode) — from SHOKK or manual import; use window fallback so SHOKK-loaded spec is never missed
    const activeSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath) ? importedSpecMapPath : (window.importedSpecMapPath || null);
    if (activeSpecPath) {
        extras.import_spec_map = activeSpecPath;
        console.log('[doRender] Merge mode: imported spec map =', activeSpecPath);
    }

    // Decals: composite paint + decals and send as image so render includes them
    if (typeof compositeDecalsForRender === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
        const compositeCanvas = compositeDecalsForRender();
        if (compositeCanvas) {
            const dataUrl = compositeCanvas.toDataURL('image/png');
            extras.paint_image_base64 = dataUrl;
        }
        // Send separate decal-only alpha mask so the engine can correctly identify
        // decal pixels without relying on the composite image alpha (which is 255 everywhere)
        if (typeof compositeDecalMaskForRender === 'function') {
            const maskDataUrl = compositeDecalMaskForRender();
            if (maskDataUrl) extras.decal_mask_base64 = maskDataUrl;
        }
        // Send per-decal spec finish info to server
        const decalSpecs = decalLayers
            .filter(dl => dl.visible && dl.specFinish && dl.specFinish !== 'none')
            .map(dl => ({ specFinish: dl.specFinish }));
        if (decalSpecs.length > 0) {
            extras.decal_spec_finishes = decalSpecs;
        }
    }

    // Spec Stamps: composite stamp images and send to server
    if (typeof compositeStampsForRender === 'function' && typeof window.stampLayers !== 'undefined' && window.stampLayers.length > 0) {
        const stampCanvas = compositeStampsForRender();
        if (stampCanvas) {
            const stampDataUrl = stampCanvas.toDataURL('image/png');
            extras.stamp_image_base64 = stampDataUrl;
            extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';
            console.log('[doRender] Stamp overlay included:', window.stampLayers.filter(function(s) { return s.visible; }).length, 'visible stamps, finish=' + (window.stampSpecFinish || 'gloss'));
        }
    }

    // Show progress
    const btn = document.getElementById('btnRender');
    const bar = document.getElementById('renderProgress');
    const barInner = document.getElementById('renderProgressBar');
    const zoneCount = serverZones.length;
    btn.textContent = `RENDERING ${zoneCount} ZONE${zoneCount > 1 ? 'S' : ''}...`;
    showToast('Rendering... This may take 30–60 seconds for complex finishes.', false);
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
                msg += ' | Files pushed to iRacing!';
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
            const err = result.error || 'unknown';
            const friendly = (err.includes('Paint file not found') || err.includes('not found'))
                ? 'Paint file not found. Check the Source Paint path.'
                : (err.includes('No zones') || err.includes('zones'))
                    ? 'No valid zones. Add a finish and color to at least one zone.'
                    : (err.includes('License') || err.includes('license'))
                        ? 'License required. Open Settings to enter your key.'
                        : err;
            showToast('Render failed: ' + friendly, true);
            RenderNotify.onRenderComplete(false, 0, 0);
        }
    } catch (e) {
        clearInterval(_progInterval);
        stopRenderTimer();
        if (e.name === 'AbortError') {
            showToast('Render cancelled.', false);
        } else if (e.message && e.message.includes('fetch')) {
            showToast('Server unreachable. Is server.py running?', true);
        } else {
            showToast('Render error: ' + (e.message || 'Unknown error'), true);
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

    // Output directory + live link combined status
    if (llMsg) {
        let msgParts = [];
        // Show output_dir status (primary output)
        if (result.output_dir?.success) {
            const fileCount = result.output_dir.pushed_files?.length || 0;
            msgParts.push(`<span style="color:var(--accent-green)"><strong>&#10003; Saved ${fileCount} files</strong> to <code>${result.output_dir.path}</code></span>`);
        } else if (result.output_dir?.error) {
            msgParts.push(`<span style="color:#ff4444"><strong>&#10007; Output Error:</strong> ${result.output_dir.error}</span>`);
        }
        // Show iRacing reload instruction (if live link or output_dir succeeded)
        if (result.live_link?.success || result.output_dir?.success) {
            msgParts.push(`<span style="color:var(--accent-gold); font-size:10px;">💡 <strong>Alt+Tab</strong> to iRacing and press <strong>Ctrl+R</strong> to see your new render!</span>`);
        }
        // Show live link error only if output_dir also failed
        if (result.live_link?.error && !result.live_link?.success && !result.output_dir?.success) {
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
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

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

// ===== SAVE TO SHOKKER PAINT BOOTH FOLDER (keep; not overwritten) =====
async function saveRenderToKeep() {
    const outputDir = document.getElementById('outputDir')?.value?.trim();
    if (!outputDir) {
        showToast('Set the iRacing Folder (output path) first, then render. After render, click Save to keep.', true);
        return;
    }
    const btn = document.getElementById('btnSaveToKeep');
    if (btn) btn.disabled = true;
    try {
        const res = await fetch(ShokkerAPI.baseUrl + '/save-render-to-keep', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                output_dir: outputDir,
                iracing_id: document.getElementById('iracingId')?.value?.trim() || '00000'
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Saved ${data.saved_files?.length || 0} file(s) to Shokker Paint Booth folder. They will not be overwritten.`);
        } else {
            showToast(data.error || 'Save failed', true);
        }
    } catch (e) {
        showToast('Save failed - server offline?', true);
    }
    if (btn) btn.disabled = false;
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

