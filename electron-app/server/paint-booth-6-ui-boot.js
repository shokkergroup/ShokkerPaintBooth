        // ============================================================
        // PAINT-BOOTH-6-UI-BOOT.JS - Modals, shortcuts, boot
        // ============================================================
        // Purpose: Modals (finish browser, compare, templates, presets), NLP chat bar,
        //          color harmony, keyboard shortcuts, init on load (init(), autoRestore, polling).
        // Deps:    All previous modules (1–5). Runs last.
        // Edit:    Modals → openFinishBrowser, template library, preset gallery.
        //          Shortcuts → keydown listener. Boot → "INIT ON LOAD", init(), ShokkerAPI.startPolling.
        // See:     PROJECT_STRUCTURE.md in this folder.
        // ============================================================

        // ===== COMBINATION HINTS =====
        const COMBO_HINTS = {
            // === CHROME COMBOS ===
            "chrome+carbon_fiber": "Premium supercar look - mirror carbon weave",
            "chrome+diamond_plate": "Industrial chrome tread - tough and shiny",
            "chrome+lightning": "Thunder chrome - electric mirror",
            "chrome+hologram": "Sci-fi chrome - futuristic scanlines",
            "chrome+hex_mesh": "Chrome honeycomb - high-tech racing",
            "chrome+ekg": "SHOKKER signature - chrome heartbeat",
            "chrome+stardust": "Starfield chrome - deep space mirror",
            "dark_chrome+carbon_fiber": "Dark carbon chrome - stealth luxury",
            "dark_chrome+hex_mesh": "Tactical dark chrome mesh",
            "satin_chrome+carbon_fiber": "Satin carbon - understated elegance",
            // === CANDY COMBOS ===
            "candy+holographic_flake": "Candy flake - classic hot rod show car",
            "candy+stardust": "Galaxy candy - deep space effect",
            "candy+tribal_flame": "Candy flames - hot rod tradition",
            "candy+carbon_fiber": "Carbon candy - modern show car",
            "candy+lightning": "Electric candy - high voltage",
            "candy+interference": "Chameleon candy - color-shift depth",
            // === MATTE COMBOS ===
            "matte+matte_grain": "Soft stealth grain - flat, clean, no surprise carbon weave",
            "matte+hex_mesh": "Tactical honeycomb - military spec",
            "matte+diamond_plate": "Industrial matte tread",
            "matte+ekg": "SHOKKER stealth - matte heartbeat",
            "blackout+carbon_fiber": "Full stealth carbon - invisible",
            "blackout+hex_mesh": "Murdered-out mesh - dark ops",
            "blackout+ekg": "SHOKKER blackout - dark pulse",
            "flat_black+carbon_fiber": "Flat carbon - no-frills stealth",
            "vantablack+stardust": "Event horizon - stars in the void",
            "vantablack+lightning": "Dark lightning - electric void",
            "vantablack+plasma": "Void plasma - pure energy",
            // === PEARL COMBOS ===
            "pearl+interference": "Chameleon pearl - color shifts everywhere",
            "pearl+holographic_flake": "Pearl flake - premium sparkle",
            "pearl+stardust": "Cosmic pearl - starfield shimmer",
            // === METALLIC COMBOS ===
            "metallic+metal_flake": "Double metallic - maximum sparkle",
            "metallic+carbon_fiber": "Metallic carbon - motorsport premium",
            "metallic+tribal_flame": "Metallic flames - show car classic",
            "metallic+diamond_plate": "Heavy metal tread",
            // === FROZEN COMBOS ===
            "frozen+cracked_ice": "Arctic frozen - cracked ice crystal",
            "frozen+interference": "Frozen rainbow - ice prism",
            "frozen+stardust": "Frozen galaxy - ice and stars",
            // === SPECIAL COMBOS ===
            "chameleon+none": "Pure chameleon - let the color shift speak",
            "cerakote+carbon_fiber": "Tactical ceramic carbon - mil-spec",
            "cerakote+hex_mesh": "Tactical ceramic mesh",
            "brushed_aluminum+diamond_plate": "Brushed tread - industrial elegance",
            "barn_find+acid_wash": "Barn find patina - authentic aged",
            "copper+celtic_knot": "Celtic copper - old-world metal art",
            "volcanic+fracture": "Volcanic fracture - molten cracks",
            "satin+none": "Clean satin - sponsor-friendly professional",
            "gloss+none": "Clean gloss - OEM showroom finish",
        };

        // ===== UTILITY: DEBOUNCE =====
        // Improvement: debounce utility for rapid-fire event handlers (resize, scroll, input)
        function _spbDebounce(fn, delay) {
            let timer = null;
            return function(...args) {
                clearTimeout(timer);
                timer = setTimeout(() => fn.apply(this, args), delay);
            };
        }

        // ===== UTILITY: BUTTON LOADING STATE =====
        // Sets a button to loading state (disabled + "..." text), returns restore function
        function _spbButtonLoading(btn, loadingText) {
            if (!btn) return () => {};
            const origText = btn.textContent;
            const origDisabled = btn.disabled;
            btn.disabled = true;
            btn.textContent = loadingText || 'Loading...';
            btn.style.opacity = '0.6';
            return function restore(newText) {
                btn.disabled = origDisabled;
                btn.textContent = newText || origText;
                btn.style.opacity = '';
            };
        }

        // Material-aware combo scoring based on BASE_METADATA
        function getComboScore(base, pattern) {
            if (!base || !pattern || pattern === 'none') return 0;
            var meta = (typeof getBaseMetadata === 'function') ? getBaseMetadata(base) : {};
            if (!meta || !meta.best_with) return 50; // Unknown = neutral
            if (meta.best_with.indexOf(pattern) >= 0) return 100; // Recommended pair
            if (meta.best_with.indexOf('none') >= 0 && pattern === 'none') return 80;
            return 50; // No specific recommendation
        }

        function getComboHint(base, pattern) {
            if (!base || !pattern || pattern === 'none') return '';
            var hint = COMBO_HINTS[base + '+' + pattern];
            if (hint) return hint;
            // Auto-generate hint from metadata
            var meta = (typeof getBaseMetadata === 'function') ? getBaseMetadata(base) : {};
            if (meta && meta.best_with && meta.best_with.indexOf(pattern) >= 0) {
                return 'Recommended combo for ' + (meta.family || base);
            }
            return '';
        }

        // ===== DECAL & NUMBER OVERLAY SYSTEM =====
        let decalLayers = []; // [{name, img, x, y, scale, rotation, opacity, visible, flipH, flipV}]
        let draggingDecal = -1;
        let decalDragOffset = { x: 0, y: 0 };
        let selectedDecalIndex = -1;
        let decalScaleStart = null; // { index, scale0, cx, cy, dist0 }
        let decalRotateStart = null; // { index, rotation0, angle0 }

        const DECAL_HANDLE_RADIUS = 8;
        const DECAL_ROTATE_HANDLE_OFFSET = 28;

        function getPaintCanvasSize() {
            const c = document.getElementById('paintCanvas');
            return c ? { w: c.width, h: c.height } : { w: 2048, h: 2048 };
        }

        function _spbBuildLayerBitmap(sourceImg, targetW, targetH, onReady) {
            if (!sourceImg || typeof onReady !== 'function') return;
            const naturalW = sourceImg.naturalWidth || sourceImg.width || 1;
            const naturalH = sourceImg.naturalHeight || sourceImg.height || 1;
            const finalW = Math.max(1, Math.round(targetW || naturalW));
            const finalH = Math.max(1, Math.round(targetH || naturalH));
            if (finalW === naturalW && finalH === naturalH) {
                onReady(sourceImg);
                return;
            }
            const canvas = document.createElement('canvas');
            canvas.width = finalW;
            canvas.height = finalH;
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, finalW, finalH);
            ctx.drawImage(sourceImg, 0, 0, finalW, finalH);
            const scaledImg = new Image();
            scaledImg.onload = () => onReady(scaledImg);
            scaledImg.src = canvas.toDataURL('image/png');
        }

        function addImageToUnifiedLayerStack(options) {
            const opts = options || {};
            const img = opts.img;
            if (!img) return;
            const x = Math.max(0, Math.round(opts.x || 0));
            const y = Math.max(0, Math.round(opts.y || 0));
            const targetW = opts.width || img.naturalWidth || img.width;
            const targetH = opts.height || img.naturalHeight || img.height;
            _spbBuildLayerBitmap(img, targetW, targetH, (layerImg) => {
                const finalW = layerImg.naturalWidth || layerImg.width || Math.max(1, Math.round(targetW));
                const finalH = layerImg.naturalHeight || layerImg.height || Math.max(1, Math.round(targetH));
                if (typeof _psdLayers !== 'undefined') {
                    const newLayer = {
                        id: (opts.idPrefix || 'decal') + '_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
                        name: opts.name || 'Layer',
                        path: opts.path || (opts.groupName || 'Layers') + '/' + (opts.name || 'Layer'),
                        visible: true,
                        opacity: 255,
                        img: layerImg,
                        bbox: [x, y, x + finalW, y + finalH],
                        groupName: opts.groupName || 'Decals',
                        blendMode: 'source-over',
                        locked: false,
                        effects: null,
                    };
                    _psdLayers.push(newLayer);
                    _psdLayersLoaded = true;
                    _selectedLayerId = newLayer.id;
                    if (typeof window !== 'undefined') window._selectedLayerId = _selectedLayerId;
                    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
                    if (typeof renderLayerPanel === 'function') renderLayerPanel();
                    if (typeof drawLayerBounds === 'function') drawLayerBounds();
                    if (typeof switchRightTab === 'function') switchRightTab('layers');
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                } else {
                    decalLayers.push({
                        name: opts.legacyName || opts.name || 'Decal',
                        img: layerImg,
                        x: x,
                        y: y,
                        scale: 1.0,
                        rotation: 0,
                        opacity: 100,
                        visible: true,
                        flipH: false,
                        flipV: false,
                        specFinish: opts.specFinish || 'none',
                    });
                    selectedDecalIndex = decalLayers.length - 1;
                    renderDecalList();
                    renderDecalOverlay();
                }
                if (opts.successToast && typeof showToast === 'function') showToast(opts.successToast);
            });
        }

        function getDecalBounds(d) {
            const dw = d.img.width * d.scale;
            const dh = d.img.height * d.scale;
            const cx = d.x + dw / 2;
            const cy = d.y + dh / 2;
            const rad = (d.rotation || 0) * Math.PI / 180;
            const c = Math.cos(rad), s = Math.sin(rad);
            const corners = [
                { x: cx + (-dw/2)*c - (-dh/2)*s, y: cy + (-dw/2)*s + (-dh/2)*c },
                { x: cx + (dw/2)*c - (-dh/2)*s,  y: cy + (dw/2)*s + (-dh/2)*c },
                { x: cx + (dw/2)*c - (dh/2)*s,   y: cy + (dw/2)*s + (dh/2)*c },
                { x: cx + (-dw/2)*c - (dh/2)*s,  y: cy + (-dw/2)*s + (dh/2)*c },
            ];
            const rotateHandleY = cy - Math.sqrt(dw*dw + dh*dh)/2 - DECAL_ROTATE_HANDLE_OFFSET;
            return { cx, cy, corners, rotateHandleY, w: dw, h: dh };
        }

        function pointInPoly(px, py, corners) {
            let inside = false;
            const n = corners.length;
            for (let i = 0, j = n - 1; i < n; j = i++) {
                const xi = corners[i].x, yi = corners[i].y, xj = corners[j].x, yj = corners[j].y;
                if (((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / (yj - yi) + xi)) inside = !inside;
            }
            return inside;
        }

        function setSelectedDecal(idx) {
            selectedDecalIndex = idx >= 0 && idx < decalLayers.length ? idx : -1;
            renderDecalList();
            renderDecalOverlay();
        }

        function commitDecalSelection() {
            selectedDecalIndex = -1;
            renderDecalList();
            renderDecalOverlay();
            showToast('Decal committed — click decal to edit again');
        }

        function importDecal() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/png,image/jpeg,image/webp,image/gif';
            input.onchange = (e) => {
                const file = e.target.files[0];
                if (!file) return;
                // 2026-04-18 MARATHON bug #59 (Flair, MED-HIGH): pre-fix,
                // every decal import called URL.createObjectURL without a
                // matching revokeObjectURL — each imported decal leaked a
                // blob URL for the lifetime of the tab. Also, the image
                // had NO onerror handler: a corrupt PNG / wrong MIME /
                // someone picking an .svg via "All Files" produced zero
                // painter-visible feedback. Now both cleanup AND error
                // path are covered.
                const img = new Image();
                const blobUrl = URL.createObjectURL(file);
                img.onerror = () => {
                    URL.revokeObjectURL(blobUrl);
                    if (typeof showToast === 'function') {
                        showToast('Could not decode decal "' + file.name + '" — file may be corrupt or an unsupported format.', true);
                    }
                };
                img.onload = () => {
                    // Decode succeeded; free the blob URL now that the
                    // Image element owns the pixel data.
                    URL.revokeObjectURL(blobUrl);
                    const { w: cw, h: ch } = getPaintCanvasSize();
                    // Smart scale: full-size images import at 1.0, oversized get scaled to fit
                    let scale = 1.0;
                    if (img.width > cw * 1.5 || img.height > ch * 1.5) {
                        scale = Math.min(cw / img.width, ch / img.height) * 0.9;
                    }
                    const dw = img.width * scale, dh = img.height * scale;
                    const x = Math.max(0, (cw - dw) / 2);
                    const y = Math.max(0, (ch - dh) / 2);
                    const fileName = file.name.replace(/\.[^.]+$/, '');
                    addImageToUnifiedLayerStack({
                        idPrefix: 'decal',
                        img: img,
                        name: fileName || 'Sponsor',
                        legacyName: fileName || 'Sponsor',
                        path: 'Decals/' + (fileName || 'Sponsor'),
                        groupName: 'Decals',
                        x: x,
                        y: y,
                        width: dw,
                        height: dh,
                        successToast: 'Decal added: ' + file.name + ' - drag to move, use handles to scale/rotate',
                    });
                };
                img.src = blobUrl;
            };
            input.click();
        }

        function removeDecal(idx) {
            // 2026-04-18 MARATHON (Windham bug #23): pre-fix, removeDecal
            // only patched selectedDecalIndex. But draggingDecal /
            // decalScaleStart / decalRotateStart all index into decalLayers
            // — removing a decal BEFORE the in-flight one shifted the
            // remaining decals down but left the drag handles pointing at
            // stale indices. Next mousemove then moved the WRONG decal
            // (or threw on undefined). Full splice-aware fixup here.
            decalLayers.splice(idx, 1);
            if (selectedDecalIndex === idx) selectedDecalIndex = -1;
            else if (selectedDecalIndex > idx) selectedDecalIndex--;
            // Drag handle (mousedown-and-hold drag)
            if (draggingDecal === idx) {
                draggingDecal = -1; // cancel the drag — target is gone
            } else if (draggingDecal > idx) {
                draggingDecal--;
            }
            // Scale gesture state
            if (decalScaleStart) {
                if (decalScaleStart.index === idx) {
                    decalScaleStart = null;
                } else if (decalScaleStart.index > idx) {
                    decalScaleStart.index--;
                }
            }
            // Rotate gesture state
            if (decalRotateStart) {
                if (decalRotateStart.index === idx) {
                    decalRotateStart = null;
                } else if (decalRotateStart.index > idx) {
                    decalRotateStart.index--;
                }
            }
            renderDecalList();
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        // FIVE-HOUR SHIFT Win H6: pre-fix, ALL of these decal mutators only
        // redrew the region-canvas overlay — they did NOT call
        // triggerPreviewRender(). Decals flow into the render via
        // compositeDecalsForRender() → extras.paint_image_base64. Painter
        // flipped/scaled/rotated/toggled a decal, saw the overlay update on
        // the source canvas, but the LIVE PREVIEW pane stayed on the old
        // state until they touched any other control. Same silent-stale
        // class as marathon #15 (zone reorder) and this shift's C1/C2/H1.
        function setDecalFlipH(idx, val) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].flipH = !!val;
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }
        function setDecalFlipV(idx, val) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].flipV = !!val;
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function snapDecalToCanvas(idx) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].x = 0;
            decalLayers[idx].y = 0;
            decalLayers[idx].scale = 1.0;
            decalLayers[idx].rotation = 0;
            decalLayers[idx].flipH = false;
            decalLayers[idx].flipV = false;
            renderDecalList();
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            if (typeof showToast === 'function') showToast('Decal snapped to canvas \u2014 position (0,0), scale 1.0', 'success');
        }

        function setDecalScale(idx, val) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].scale = parseFloat(val);
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function setDecalOpacity(idx, val) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].opacity = parseInt(val);
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function setDecalRotation(idx, val) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].rotation = parseInt(val);
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function toggleDecalVisibility(idx) {
            if (!decalLayers[idx]) return;
            decalLayers[idx].visible = !decalLayers[idx].visible;
            renderDecalList();
            renderDecalOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
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
            if (selectedDecalIndex >= 0) {
                html += `<div class="decal-layer-row" style="border-color:var(--accent-blue); background:rgba(51,102,255,0.1);">
                    <button type="button" class="btn btn-sm" onclick="commitDecalSelection()" title="Commit — hide transform box, click decal again to edit" style="font-size:9px; padding:2px 8px;">✓ Commit</button>
                </div>`;
            }
            decalLayers.forEach((d, idx) => {
                const sel = selectedDecalIndex === idx;
                html += `<div class="decal-layer-row" ${sel ? ' style="border-color:var(--accent-blue);"' : ''}>
            <img class="decal-thumb" src="${d.img.src}" alt="${d.name}">
            <span class="decal-name" title="${d.name}">${d.name}</span>
            <button onclick="setSelectedDecal(${idx})" title="${sel ? 'Selected' : 'Click to select on canvas'}" style="font-size:9px; padding:2px 6px;">${sel ? '●' : '○'}</button>
            <div class="decal-controls">
                <span>Sc</span>
                <input type="range" min="0.05" max="3" step="0.05" value="${d.scale}" oninput="setDecalScale(${idx}, this.value)" title="Scale">
                <span>Op</span>
                <input type="range" min="0" max="100" value="${d.opacity}" oninput="setDecalOpacity(${idx}, this.value)" title="Opacity">
                <span>Rot</span>
                <input type="range" min="0" max="360" value="${d.rotation || 0}" oninput="setDecalRotation(${idx}, this.value)" title="Rotation" style="width:35px;">
                <button onclick="setDecalFlipH(${idx}, !decalLayers[${idx}].flipH)" title="Flip Decal H &#x2014; flip this decal horizontally">&#x2194;</button>
                <button onclick="setDecalFlipV(${idx}, !decalLayers[${idx}].flipV)" title="Flip Decal V &#x2014; flip this decal vertically">&#x2195;</button>
                <button onclick="toggleDecalVisibility(${idx})" title="Toggle visibility">${d.visible ? '&#x1F441;' : '&#x1F6AB;'}</button>
                <button onclick="snapDecalToCanvas(${idx})" title="Snap to Canvas — reset to position (0,0), scale 1.0, no rotation" style="color:#00C8C8;">⊞</button>
                <button onclick="removeDecal(${idx})" title="Remove">&times;</button>
            </div>
            <select onchange="decalLayers[${idx}].specFinish = this.value; renderDecalOverlay();"
                    style="background:#1a1a1a; color:#ccc; border:1px solid #333; padding:2px 4px; font-size:10px; width:100%;"
                    title="Apply a spec finish to just this decal's pixels.">
              <option value="none" ${(!d.specFinish || d.specFinish === 'none') ? 'selected' : ''}>No Spec Finish</option>
              ${(() => {
                // BASE_GROUPS and BASES are top-level const in paint-booth-0-finish-data.js.
                // In non-module scripts they are in global scope but NOT on window — use directly.
                const foundationIds = (typeof BASE_GROUPS !== 'undefined' && BASE_GROUPS['Foundation']) ||
                                     (typeof window.BASE_GROUPS !== 'undefined' && window.BASE_GROUPS['Foundation']) ||
                                     [];
                const referenceFoundationIds = (typeof BASE_GROUPS !== 'undefined' && BASE_GROUPS['Reference Foundations']) ||
                                              (typeof window.BASE_GROUPS !== 'undefined' && window.BASE_GROUPS['Reference Foundations']) ||
                                              [];
                const basesArr = (typeof BASES !== 'undefined' ? BASES : null) ||
                                 (typeof window.BASES !== 'undefined' ? window.BASES : null) ||
                                 [];
                // 2026-04-22 Codex P1 fix: filter the decal specFinish dropdown to
                // only ids that have a working Python decal-spec dispatcher. The
                // 15 classic non-f_ Foundation ids (gloss/matte/satin/semi_gloss/
                // silk/wet_look/clear_matte/primer/flat_black/eggshell/ceramic/
                // piano_black/scuffed_satin/chalky_base/living_matte) route through
                // 5-arg engine.spec_paint handlers that crash at this decal call
                // site (4-arg signature) and get silently swallowed — the painter
                // picks them and gets no spec on their decal. f_* entries route
                // through the flat-spec shim and work correctly. Restrict the
                // dropdown to f_* until the classic backend path is fixed.
                const _decalSpecIsSupported = id => typeof id === 'string' && id.startsWith('f_');
                // Hardcoded fallback in case data hasn't loaded yet
                const fallback = [
                    {id: 'gloss',          name: 'Gloss'},
                    {id: 'matte',          name: 'Matte'},
                    {id: 'satin',          name: 'Satin'},
                    {id: 'semi_gloss',     name: 'Semi Gloss'},
                    {id: 'silk',           name: 'Silk'},
                    {id: 'wet_look',       name: 'Wet Look'},
                    {id: 'clear_matte',    name: 'Clear Matte'},
                    {id: 'flat_black',     name: 'Flat Black'},
                    {id: 'primer',         name: 'Primer'},
                    {id: 'eggshell',       name: 'Eggshell'},
                    {id: 'ceramic',        name: 'Ceramic'},
                    {id: 'piano_black',    name: 'Piano Black'},
                    {id: 'scuffed_satin',  name: 'Scuffed Satin'},
                    {id: 'chalky_base',    name: 'Chalky'},
                    {id: 'living_matte',   name: 'Living Matte'},
                    {id: 'f_chrome',       name: 'Chrome (Foundation)'},
                    {id: 'f_satin_chrome', name: 'Satin Chrome (Foundation)'},
                    {id: 'f_metallic',     name: 'Metallic (Foundation)'},
                    {id: 'f_pearl',        name: 'Pearl (Foundation)'},
                    {id: 'f_carbon_fiber', name: 'Carbon Fiber (Foundation)'},
                    {id: 'f_brushed',      name: 'Brushed (Foundation)'},
                    {id: 'f_frozen',       name: 'Frozen (Foundation)'},
                    {id: 'f_powder_coat',  name: 'Powder Coat (Foundation)'},
                    {id: 'f_anodized',     name: 'Anodized (Foundation)'},
                    {id: 'f_vinyl_wrap',   name: 'Vinyl Wrap (Foundation)'},
                    {id: 'f_gel_coat',     name: 'Gel Coat (Foundation)'},
                    {id: 'f_baked_enamel', name: 'Baked Enamel (Foundation)'},
                    {id: 'f_pure_white',   name: 'Pure White (Foundation)'},
                    {id: 'f_pure_black',   name: 'Pure Black (Foundation)'},
                    {id: 'f_neutral_grey', name: 'Neutral Grey (Foundation)'},
                    {id: 'f_soft_gloss',   name: 'Soft Gloss (Foundation)'},
                    {id: 'f_soft_matte',   name: 'Soft Matte (Foundation)'},
                    {id: 'f_clear_satin',  name: 'Clear Satin (Foundation)'},
                    {id: 'f_warm_white',   name: 'Warm White (Foundation)'},
                ];
                // Loaded-data branch must expose the SAME safe set in the SAME
                // order as the fallback: shipping f_* ids from Foundation only.
                // Reference Foundations was redundant shipping UI and is gone.
                const availableFoundationIds = [];
                for (const id of [...foundationIds, ...referenceFoundationIds]) {
                    if (_decalSpecIsSupported(id) && !availableFoundationIds.includes(id)) {
                        availableFoundationIds.push(id);
                    }
                }
                const preferredFoundationIds = fallback
                    .filter(b => _decalSpecIsSupported(b.id))
                    .map(b => b.id);
                const foundationBases = preferredFoundationIds
                    .filter(id => availableFoundationIds.includes(id))
                    .map(id => basesArr.find(b => b.id === id))
                    .filter(Boolean);
                // Same P1 filter on the hardcoded fallback: only offer ids that
                // actually render on the decal-spec path.
                const options = foundationBases.length > 0
                    ? foundationBases
                    : fallback.filter(b => _decalSpecIsSupported(b.id));
                return options.map(b => `<option value="${b.id}" ${d.specFinish === b.id ? 'selected' : ''}>${b.name}</option>`).join('');
              })()}
            </select>
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
            for (const d of decalLayers) {
                if (!d.visible || d.opacity <= 0) continue;
                ctx.save();
                ctx.globalAlpha = d.opacity / 100;
                const dw = d.img.width * d.scale;
                const dh = d.img.height * d.scale;
                const cx = d.x + dw / 2, cy = d.y + dh / 2;
                ctx.translate(cx, cy);
                ctx.rotate((d.rotation || 0) * Math.PI / 180);
                if (d.flipH || d.flipV) ctx.scale(d.flipH ? -1 : 1, d.flipV ? -1 : 1);
                ctx.drawImage(d.img, -dw / 2, -dh / 2, dw, dh);
                ctx.restore();
            }
        }

        function drawDecalSelectionBox(ctx, w, h) {
            if (selectedDecalIndex < 0 || !decalLayers[selectedDecalIndex]) return;
            const d = decalLayers[selectedDecalIndex];
            if (!d.visible) return;
            const b = getDecalBounds(d);
            ctx.save();
            ctx.strokeStyle = '#00ccff';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(b.corners[0].x, b.corners[0].y);
            for (let i = 1; i < b.corners.length; i++) ctx.lineTo(b.corners[i].x, b.corners[i].y);
            ctx.closePath();
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#00ccff';
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1;
            b.corners.forEach((p, i) => {
                ctx.fillRect(p.x - 4, p.y - 4, 8, 8);
                ctx.strokeRect(p.x - 4, p.y - 4, 8, 8);
            });
            const rhy = b.rotateHandleY;
            ctx.beginPath();
            ctx.arc(b.cx, rhy, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.restore();
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

        function compositeDecalMaskForRender() {
            // Returns a base64 PNG of just the decal alpha mask (grayscale).
            // Drawing only decals onto a transparent canvas, then extracting the alpha channel.
            // This is sent alongside the composite as decal_mask_base64 so the engine
            // can correctly identify which pixels are decals vs. paint background.
            const paintCanvas = document.getElementById('paintCanvas');
            if (!paintCanvas || decalLayers.length === 0) return null;

            // Draw only decals onto a blank (fully transparent) canvas
            const maskCanvas = document.createElement('canvas');
            maskCanvas.width = paintCanvas.width;
            maskCanvas.height = paintCanvas.height;
            const maskCtx = maskCanvas.getContext('2d');
            // Leave background transparent — draw only decals
            drawDecalsOnContext(maskCtx, maskCanvas.width, maskCanvas.height);

            // Extract alpha channel → grayscale PNG
            const imgData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
            const d = imgData.data;
            // Write alpha into R/G/B so the image reads as a proper grayscale mask
            for (let i = 0; i < d.length; i += 4) {
                const a = d[i + 3];
                d[i] = a;
                d[i + 1] = a;
                d[i + 2] = a;
                d[i + 3] = 255;
            }
            maskCtx.putImageData(imgData, 0, 0);
            return maskCanvas.toDataURL('image/png');
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

            // BUG #64: the const img declaration used to live INSIDE this
            // comment (no newline separator), so `const img` never executed
            // and the next line threw ReferenceError. Entire Number Decal
            // feature was silently broken.
            // Convert to image
            const img = new Image();
            img.onerror = function () {
                if (typeof showToast === 'function') showToast('Failed to generate number decal image', true);
            };
            img.onload = () => {
                const { w: cw, h: ch } = getPaintCanvasSize();
                const dw = img.width, dh = img.height;
                const x = Math.max(0, (cw - dw) / 2);
                const y = Math.max(0, (ch - dh) / 2);
                addImageToUnifiedLayerStack({
                    idPrefix: 'number',
                    img: img,
                    name: '#' + text,
                    legacyName: '#' + text,
                    path: 'Numbers/' + text,
                    groupName: 'Numbers',
                    x: x,
                    y: y,
                    width: dw,
                    height: dh,
                    successToast: 'Number decal "' + text + '" added',
                });
            };
            img.src = c.toDataURL('image/png');
        }

        /** Hit-test decals: returns { hit, index, action: 'move'|'scale'|'rotate'|'select', handle?: 'nw'|'ne'|'se'|'sw' } or null */
        function checkDecalHit(x, y) {
            const R = DECAL_HANDLE_RADIUS;
            if (selectedDecalIndex >= 0 && decalLayers[selectedDecalIndex] && decalLayers[selectedDecalIndex].visible) {
                const d = decalLayers[selectedDecalIndex];
                if (d.visible) {
                    const b = getDecalBounds(d);
                    const dx = x - b.cx, dy = y - b.rotateHandleY;
                    if (dx*dx + dy*dy <= (R + 6)*(R + 6)) return { hit: true, index: selectedDecalIndex, action: 'rotate' };
                    const handles = ['nw', 'ne', 'se', 'sw'];
                    for (let i = 0; i < 4; i++) {
                        const px = b.corners[i].x - x, py = b.corners[i].y - y;
                        if (px*px + py*py <= R*R) return { hit: true, index: selectedDecalIndex, action: 'scale', handle: handles[i] };
                    }
                    if (pointInPoly(x, y, b.corners)) return { hit: true, index: selectedDecalIndex, action: 'move' };
                }
            }
            for (let i = decalLayers.length - 1; i >= 0; i--) {
                const d = decalLayers[i];
                if (!d.visible) continue;
                const b = getDecalBounds(d);
                if (pointInPoly(x, y, b.corners)) return { hit: true, index: i, action: 'select' };
            }
            return null;
        }

        function checkDecalDrag(x, y) {
            const h = checkDecalHit(x, y);
            if (!h || !h.hit) {
                if (selectedDecalIndex >= 0) setSelectedDecal(-1);
                return false;
            }
            if (h.action === 'select') { setSelectedDecal(h.index); return false; }
            if (h.action === 'move') {
                const d = decalLayers[h.index];
                draggingDecal = h.index;
                decalDragOffset = { x: x - d.x, y: y - d.y };
                return true;
            }
            if (h.action === 'scale') {
                const d = decalLayers[h.index];
                const b = getDecalBounds(d);
                const dist = Math.hypot(x - b.cx, y - b.cy) || 1;
                decalScaleStart = { index: h.index, scale0: d.scale, cx: b.cx, cy: b.cy, dist0: dist };
                return 'scale';
            }
            if (h.action === 'rotate') {
                const d = decalLayers[h.index];
                const b = getDecalBounds(d);
                const angle0 = Math.atan2(y - b.cy, x - b.cx) * 180 / Math.PI;
                decalRotateStart = { index: h.index, rotation0: d.rotation || 0, angle0 };
                return 'rotate';
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

        function updateDecalScaleFromMouse(x, y) {
            if (!decalScaleStart) return;
            const d = decalLayers[decalScaleStart.index];
            const dist = Math.hypot(x - decalScaleStart.cx, y - decalScaleStart.cy) || 1;
            const s = decalScaleStart.scale0 * (dist / decalScaleStart.dist0);
            d.scale = Math.max(0.05, Math.min(3, s));
            renderDecalList();
            renderDecalOverlay();
        }
        function endDecalScale() { decalScaleStart = null; if (typeof renderDecalList === 'function') renderDecalList(); }

        function updateDecalRotateFromMouse(x, y) {
            if (!decalRotateStart) return;
            const d = decalLayers[decalRotateStart.index];
            const b = getDecalBounds(d);
            const angle = Math.atan2(y - b.cy, x - b.cx) * 180 / Math.PI;
            let delta = angle - decalRotateStart.angle0;
            if (delta > 180) delta -= 360;
            if (delta < -180) delta += 360;
            d.rotation = (decalRotateStart.rotation0 + delta + 360) % 360;
            renderDecalList();
            renderDecalOverlay();
        }
        function endDecalRotate() { decalRotateStart = null; if (typeof renderDecalList === 'function') renderDecalList(); }

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
                    { name: "Hood/Roof", base: "matte", pattern: "none", finish: null, intensity: "100", color: null, colorMode: "none" },
                    { name: "Side Panels", base: "metallic", pattern: "none", finish: null, intensity: "80", color: null, colorMode: "none" },
                    { name: "Accents", base: "chrome", pattern: "none", finish: null, intensity: "50", color: null, colorMode: "none" }
                ]
            },
            {
                name: "Full Carbon",
                category: "Performance",
                desc: "Exposed carbon fiber everywhere with clear-coated accent areas.",
                zones: [
                    { name: "Carbon Body", base: "carbon_base", pattern: "none", finish: null, intensity: "100", color: "everything", colorMode: "special" },
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
            const overlay = document.getElementById('presetGalleryOverlay');
            if (overlay) overlay.classList.add('active');
            else console.warn('[SPB] presetGalleryOverlay element not found');
        }

        function closePresetGallery() {
            const overlay = document.getElementById('presetGalleryOverlay');
            if (overlay) overlay.classList.remove('active');
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
                'Show Car': 'ðŸ†', 'Clean': '✨', 'Aggressive': 'ðŸ”¥',
                'Special Effect': 'ðŸŒˆ', 'Themed': 'ðŸŽ¯', 'Other': 'ðŸŽ¨'
            };

            // Render in category order, then any remaining
            const allCats = [...categoryOrder, ...Object.keys(grouped).filter(c => !categoryOrder.includes(c))];
            for (const cat of allCats) {
                if (!grouped[cat] || grouped[cat].length === 0) continue;
                html += `<div style="grid-column:1/-1; padding:8px 4px 4px; margin-top:8px; border-bottom:1px solid var(--border); font-size:11px; font-weight:700; letter-spacing:1.5px; color:var(--accent); text-transform:uppercase;">
            ${categoryIcons[cat] || 'ðŸŽ¨'} ${cat} <span style="font-weight:400; color:var(--text-dim); font-size:9px;">(${grouped[cat].length})</span>
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
            // Ensure catalog mode (not for-review) when opening
            const backBtn = document.getElementById('fbBackToCatalogBtn');
            const filtersEl = document.getElementById('finishBrowserFilters');
            const countEl = document.getElementById('fbCount');
            const viewBtn = document.getElementById('fbViewToggle');
            const forReviewBtn = document.getElementById('fbForReviewBtn');
            if (backBtn) backBtn.style.display = 'none';
            if (filtersEl) filtersEl.style.display = '';
            if (countEl) countEl.style.display = '';
            if (viewBtn) viewBtn.style.display = '';
            if (forReviewBtn) forReviewBtn.style.display = '';
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
            // Reset filters (null-safe)
            const fbFilterType = document.getElementById('fbFilterType');
            const fbFilterBase2 = document.getElementById('fbFilterBase');
            const fbFilterPattern2 = document.getElementById('fbFilterPattern');
            const fbSearchEl = document.getElementById('fbSearch');
            const fbSortEl = document.getElementById('fbSort');
            if (fbFilterType) fbFilterType.value = 'all';
            if (fbFilterBase2) fbFilterBase2.value = 'all';
            if (fbFilterPattern2) fbFilterPattern2.value = 'all';
            if (fbSearchEl) fbSearchEl.value = '';
            if (fbSortEl) fbSortEl.value = 'default';
            finishBrowserFavOnly = false;
            const favBtn = document.getElementById('fbFavToggle');
            if (favBtn) favBtn.classList.remove('active');
            // Restore view toggle state (viewBtn already declared above)
            if (viewBtn) viewBtn.innerHTML = finishBrowserCatalogView ? '⊞ Grid' : '☰ List';
            filterFinishBrowser();
            const fbOverlay = document.getElementById('finishBrowserOverlay');
            if (fbOverlay) fbOverlay.classList.add('active');
            else console.warn('[SPB] finishBrowserOverlay element not found');
            // Wire up debounced search so it does not re-filter on every keystroke
            const fbSearchInput = document.getElementById('fbSearch');
            if (fbSearchInput && !fbSearchInput._spbDebounced) {
                fbSearchInput._spbDebounced = true;
                fbSearchInput.removeAttribute('oninput');
                fbSearchInput.addEventListener('input', _spbDebounce(filterFinishBrowser, 250));
            }
        }

        function closeFinishBrowser() {
            const overlay = document.getElementById('finishBrowserOverlay');
            if (overlay) overlay.classList.remove('active');
            hideFinishTooltip();
        }

        // ===== PATTERNS FOR REVIEW =====
        // Shows candidate pattern images from assets/patterns/for_review with engine-rendered swatches.
        function openPatternsForReview() {
            const filtersEl = document.getElementById('finishBrowserFilters');
            const countEl = document.getElementById('fbCount');
            const backBtn = document.getElementById('fbBackToCatalogBtn');
            const viewBtn = document.getElementById('fbViewToggle');
            const forReviewBtn = document.getElementById('fbForReviewBtn');
            const grid = document.getElementById('finishBrowserGrid');
            if (filtersEl) filtersEl.style.display = 'none';
            if (countEl) countEl.style.display = 'none';
            if (viewBtn) viewBtn.style.display = 'none';
            if (forReviewBtn) forReviewBtn.style.display = 'none';
            if (backBtn) backBtn.style.display = 'inline-block';
            if (grid) {
                grid.innerHTML = '<div style="padding:12px; color:var(--text-dim);">Loading…</div>';
                grid.classList.remove('catalog-view');
            }
            const baseUrl = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI.baseUrl) ? ShokkerAPI.baseUrl : (window.location.origin || '');
            fetch(baseUrl + '/api/for-review/list', { signal: AbortSignal.timeout(10000) })
                .then(res => {
                    if (!res.ok) throw new Error('Server returned ' + res.status + ' ' + res.statusText);
                    return res.json();
                })
                .then(data => {
                    if (!data || typeof data !== 'object') throw new Error('Invalid response format from server');
                    const items = data.items || [];
                    if (!grid) return;
                    if (items.length === 0) {
                        grid.innerHTML = '<div style="padding:16px; color:var(--text-dim);">No pattern images in For Review folder. Add PNG/JPG files to <code style="font-size:10px;">assets/patterns/for_review/</code> to preview them here as they would render in the app.</div>';
                        return;
                    }
                    let html = '';
                    const size = 80;
                    for (const item of items) {
                        const swatchUrl = baseUrl + '/api/swatch/review?image=' + encodeURIComponent(item.filename) + '&size=' + size + '&color=888888';
                        const label = item.id || item.filename || 'pattern';
                        html += `<div class="finish-swatch-cell" style="flex-direction:column; align-items:center; padding:8px;">
                            <img src="${swatchUrl}" alt="${label}" style="width:${size}px; height:${size}px; object-fit:contain; border-radius:6px; background:#222;" loading="lazy">
                            <div class="fs-label" style="margin-top:4px; font-size:10px; text-align:center;">${label}</div>
                        </div>`;
                    }
                    grid.innerHTML = html;
                })
                .catch(err => {
                    console.warn('[SPB] For Review list fetch failed:', err.message);
                    if (grid) grid.innerHTML = '<div style="padding:12px; color:var(--accent);">Could not load For Review list: ' + (err.message || 'Server unreachable') + '</div>';
                });
        }

        function backToFinishCatalog() {
            const filtersEl = document.getElementById('finishBrowserFilters');
            const countEl = document.getElementById('fbCount');
            const backBtn = document.getElementById('fbBackToCatalogBtn');
            const viewBtn = document.getElementById('fbViewToggle');
            const forReviewBtn = document.getElementById('fbForReviewBtn');
            if (filtersEl) filtersEl.style.display = '';
            if (countEl) countEl.style.display = '';
            if (viewBtn) viewBtn.style.display = '';
            if (forReviewBtn) forReviewBtn.style.display = '';
            if (backBtn) backBtn.style.display = 'none';
            filterFinishBrowser();
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
            if (typeof getSwatchUrl === 'function') {
                const url = getSwatchUrl(monoId, '888888', true, 96);
                if (url) return `background: url("${url}") center/cover, #111827;`;
            }
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
            const typeEl = document.getElementById('fbFilterType');
            const baseEl = document.getElementById('fbFilterBase');
            const patEl = document.getElementById('fbFilterPattern');
            const searchEl = document.getElementById('fbSearch');
            const type = typeEl ? typeEl.value : 'all';
            const baseFilter = baseEl ? baseEl.value : 'all';
            const patFilter = patEl ? patEl.value : 'all';
            const search = (searchEl ? searchEl.value : '').toLowerCase();
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
                const monolithicIdSet = new Set(MONOLITHICS.map(m => m.id));
                const groupedSpecialMonoIds = new Set();
                if (typeof SPECIAL_GROUPS !== 'undefined') {
                    Object.values(SPECIAL_GROUPS).forEach(arr => {
                        if (!Array.isArray(arr)) return;
                        arr.forEach(id => {
                            if (monolithicIdSet.has(id)) groupedSpecialMonoIds.add(id);
                        });
                    });
                }
                for (const m of MONOLITHICS) {
                    if (groupedSpecialMonoIds.size && !groupedSpecialMonoIds.has(m.id)) continue;
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

            // Highlight search matches in label text
            function _highlightMatch(text, query) {
                if (!query) return text;
                const idx = text.toLowerCase().indexOf(query);
                if (idx < 0) return text;
                return text.substring(0, idx) + '<mark style="background:var(--accent-gold);color:#000;padding:0 1px;border-radius:2px;">' + text.substring(idx, idx + query.length) + '</mark>' + text.substring(idx + query.length);
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
                const displayLabel = search ? _highlightMatch(item.label, search) : item.label;

                if (isCatalog) {
                    // Catalog (list) view with descriptions and favorites
                    const desc = search ? _highlightMatch(getFinishDesc(item), search) : getFinishDesc(item);
                    const onclick = isMono
                        ? `applyFinishFromBrowser(null,null,'${item.monoId}')`
                        : `applyFinishFromBrowser('${item.baseId}','${item.patId}')`;
                    html += `<div class="finish-swatch-cell" onclick="${onclick}" ${dataAttr}
                onmouseenter="showFinishTooltip(event,${isMono ? `{type:'mono',label:'${item.label.replace(/'/g, "\\'")}',monoId:'${item.monoId}',key:'${item.key}'}` : `{type:'combo',label:'${item.label.replace(/'/g, "\\'")}',baseId:'${item.baseId}',patId:'${item.patId}',key:'${item.key}'}`})"
                onmousemove="positionFinishTooltip(event)" onmouseleave="hideFinishTooltip()"
                ${isMono ? 'style="border-color:var(--accent-gold);"' : ''}>
                <div class="fs-swatch-block" style="${swatchStyle}"></div>
                <div class="fs-info">
                    <div class="fs-label" ${isMono ? 'style="color:var(--accent-gold);"' : ''}>${displayLabel}</div>
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
                <div class="fs-label" ${isMono ? 'style="color:var(--accent-gold);"' : ''}>${displayLabel}</div>
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
            const fbCountEl = document.getElementById('fbCount');
            if (fbCountEl) fbCountEl.textContent = countText + (favCount > 0 ? ` | ${favCount} favorites` : '');
        }

        function applyFinishFromBrowser(baseId, patternId, monoId) {
            // Intercept: custom color shift opens the modal
            if (monoId === 'dualshift_custom' || monoId === 'cx_custom_shift') {
                closeFinishBrowser();
                if (typeof openDualShiftModal === 'function') openDualShiftModal(finishBrowserTargetZone);
                return;
            }
            pushZoneUndo('Apply finish from catalog');
            const z = zones[finishBrowserTargetZone];
            if (monoId) {
                if (typeof _spbApplyPickedMonolithicToZone === 'function') {
                    _spbApplyPickedMonolithicToZone(z, monoId);
                } else {
                    z.finish = monoId;
                    z.base = null;
                    z.baseColorMode = 'special';
                    z.baseColorSource = 'mono:' + monoId;
                    z._autoBaseColorFill = true;
                }
                z.pattern = null;
                addRecentFinish(`mono:${monoId}`);
            } else {
                if (typeof _spbApplyPickedBaseToZone === 'function') {
                    _spbApplyPickedBaseToZone(z, baseId);
                } else {
                    z.finish = null;
                    z.base = baseId;
                }
                z.pattern = patternId || 'none';
                addRecentFinish(`${baseId}:${patternId || 'none'}`);
            }
            renderZones();
            // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W1): silent-stale.
            // The finish-browser was the canonical "apply this finish" UX, yet
            // it left the rendered car preview frozen on the prior finish until
            // the painter touched something else. Mirror what assignFinishToSelected does.
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
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
            if (!z) { showToast('Invalid zone index for compare', true); return; }
            // Pre-populate first column with current zone's finish
            compareColumns = [
                { base: z.base || 'chrome', pattern: z.pattern || 'none', mono: z.finish || null },
                { base: 'metallic', pattern: 'carbon_fiber', mono: null }
            ];
            renderCompareColumns();
            const overlay = document.getElementById('finishCompareOverlay');
            if (overlay) overlay.classList.add('active');
            else console.warn('[SPB] finishCompareOverlay element not found');
        }

        function closeFinishCompare() {
            const overlay = document.getElementById('finishCompareOverlay');
            if (overlay) overlay.classList.remove('active');
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
            // Chrome family — mirror + structure
            "chrome+carbon_fiber", "chrome+diamond_plate", "chrome+hex_mesh", "chrome+lightning",
            "chrome+hologram", "chrome+stardust", "chrome+none", "chrome+ekg",
            "dark_chrome+carbon_fiber", "dark_chrome+hex_mesh", "dark_chrome+lightning",
            "satin_chrome+carbon_fiber", "satin_chrome+hex_mesh",
            "candy_chrome+holographic_flake", "candy_chrome+stardust",
            // Candy family — depth + sparkle
            "candy+holographic_flake", "candy+stardust", "candy+metal_flake", "candy+none",
            "candy+tribal_flame", "candy+carbon_fiber", "candy+lightning", "candy+interference",
            // Matte family — stealth + texture
            "matte+matte_grain", "matte+hex_mesh", "matte+battle_worn", "matte+diamond_plate",
            "matte+ekg", "matte+topographic",
            "blackout+carbon_fiber", "blackout+hex_mesh", "blackout+lightning", "blackout+ekg",
            "flat_black+carbon_fiber", "flat_black+hex_mesh",
            "vantablack+stardust", "vantablack+lightning", "vantablack+plasma",
            "cerakote+carbon_fiber", "cerakote+hex_mesh", "cerakote+diamond_plate",
            // Pearl family — shimmer + iridescence
            "pearl+interference", "pearl+stardust", "pearl+holographic_flake", "pearl+ripple",
            "pearl+none",
            // Metallic family — sparkle + structure
            "metallic+metal_flake", "metallic+holographic_flake", "metallic+carbon_fiber",
            "metallic+tribal_flame", "metallic+diamond_plate",
            "gunmetal+carbon_fiber", "gunmetal+hex_mesh", "gunmetal+diamond_plate",
            "rose_gold+holographic_flake", "rose_gold+stardust",
            "copper+celtic_knot", "copper+tribal_flame",
            // Brushed family — directional + geometric
            "brushed_aluminum+carbon_fiber", "brushed_aluminum+diamond_plate", "brushed_aluminum+none",
            "brushed_titanium+carbon_fiber", "brushed_titanium+diamond_plate", "brushed_titanium+hex_mesh",
            // Frozen/exotic
            "frozen+cracked_ice", "frozen+holographic_flake", "frozen+stardust", "frozen+interference",
            "electric_ice+lightning", "electric_ice+cracked_ice", "electric_ice+stardust",
            "volcanic+fracture", "volcanic+lightning", "volcanic+plasma",
            "chameleon+none", "chameleon+holographic_flake", "chameleon+interference",
            // Wrap family
            "satin_wrap+none", "satin_wrap+carbon_fiber",
            "chrome_wrap+none", "chrome_wrap+carbon_fiber",
            // Weathered family
            "barn_find+acid_wash", "barn_find+battle_worn", "barn_find+rust_bloom",
            "acid_etch+acid_wash", "acid_etch+fracture",
            "battle_patina+battle_worn", "battle_patina+rust_bloom",
            // Clean/OEM
            "gloss+none", "gloss+carbon_fiber", "gloss+metal_flake",
            "satin+carbon_fiber", "satin+none",
            "ceramic+none", "ceramic+diamond_plate",
            "anodized+diamond_plate", "anodized+hex_mesh",
        ];

        const BAD_COMBOS = new Set([
            // Matte + sparkle = contradicts physics (matte absorbs, sparkle reflects)
            "blackout+stardust", "blackout+holographic_flake", "blackout+interference",
            "matte+holographic_flake", "matte+metal_flake", "matte+interference",
            "flat_black+holographic_flake", "flat_black+metal_flake", "flat_black+stardust",
            "vantablack+holographic_flake", "vantablack+metal_flake",
            "cerakote+holographic_flake", "cerakote+metal_flake", "cerakote+stardust",
            // Chrome + weathering = contradicts material (chrome doesn't rust/fade)
            "chrome+battle_worn", "chrome+acid_wash", "chrome+rust_bloom",
            "dark_chrome+battle_worn", "dark_chrome+acid_wash",
            "candy_chrome+battle_worn", "candy_chrome+acid_wash",
            // Weathered + sparkle = unlikely combo
            "barn_find+holographic_flake", "barn_find+stardust",
            "acid_etch+holographic_flake", "battle_patina+stardust",
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

        // ===== ⚡ SHOKK ME — Total Chaos Randomization =====
        function shokkMe(index) {
            if (index < 0 || index >= zones.length) return;
            pushZoneUndo('SHOKK ME');
            const zone = zones[index];

            // Helper: random int in [min, max]
            const randInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
            // Helper: random float in [min, max], rounded to step
            const randFloat = (min, max, step) => { const v = min + Math.random() * (max - min); return step ? Math.round(v / step) * step : v; };
            // Helper: random hex color
            const randHex = () => '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
            // Helper: pick random item from array
            const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
            // Helper: weighted random — returns index, weights don't need to sum to 1
            const weightedPick = (weights) => { const total = weights.reduce((a, b) => a + b, 0); let r = Math.random() * total; for (let i = 0; i < weights.length; i++) { r -= weights[i]; if (r <= 0) return i; } return weights.length - 1; };

            // Build a flat list of all specials for "From Special" color sources
            const allSpecials = [];
            if (typeof SPECIAL_GROUPS !== 'undefined') {
                Object.values(SPECIAL_GROUPS).forEach(arr => { if (Array.isArray(arr)) arr.forEach(id => allSpecials.push(id)); });
            }
            if (allSpecials.length === 0 && typeof MONOLITHICS !== 'undefined') {
                MONOLITHICS.forEach(m => allSpecials.push(m.id));
            }

            const blendModes = ['noise', 'marble', 'pattern-edges', 'pattern', 'pattern-vivid', 'tint', 'pattern-peaks', 'pattern-contour', 'pattern-screen', 'pattern-threshold'];
            const intensities = (typeof INTENSITY_OPTIONS !== 'undefined') ? INTENSITY_OPTIONS.map(o => o.id) : ['50', '70', '80', '90', '100'];

            // —€—€ 1. BASE FINISH —€—€
            // 85% base from BASES, 15% monolithic from MONOLITHICS
            if (Math.random() < 0.85) {
                zone.base = pick(BASES).id;
                zone.finish = null;
            } else {
                zone.finish = pick(MONOLITHICS).id;
                zone.base = null;
            }

            // —€—€ 2. PATTERN —€—€
            // 75% get a pattern, 25% no pattern
            if (Math.random() < 0.75) {
                zone.pattern = pick(PATTERNS).id;
            } else {
                zone.pattern = 'none';
            }

            // —€—€ 3. INTENSITY —€—€
            zone.intensity = pick(intensities);

            // —€—€ 4. PATTERN SETTINGS —€—€
            zone.scale = randFloat(0.3, 3.0, 0.1);
            zone.rotation = randInt(0, 359);
            zone.patternOffsetX = randFloat(0, 1, 0.05);
            zone.patternOffsetY = randFloat(0, 1, 0.05);
            zone.patternFlipH = Math.random() < 0.2;
            zone.patternFlipV = Math.random() < 0.2;
            zone.patternSpecMult = randFloat(0.3, 2.0, 0.1);

            // —€—€ 5. BASE SETTINGS —€—€
            zone.baseRotation = randInt(0, 359);
            zone.baseScale = randFloat(0.5, 2.5, 0.1);
            zone.baseStrength = randFloat(0.5, 2.0, 0.1);
            zone.baseSpecStrength = randFloat(0.3, 2.0, 0.1);
            zone.baseOffsetX = randFloat(0.2, 0.8, 0.05);
            zone.baseOffsetY = randFloat(0.2, 0.8, 0.05);
            zone.baseFlipH = Math.random() < 0.15;
            zone.baseFlipV = Math.random() < 0.15;

            // —€—€ 6. BASE COLOR MODE —€—€
            // 50% source paint, 25% solid color, 25% from special
            const colorRoll = Math.random();
            if (colorRoll < 0.50) {
                zone.baseColorMode = 'source';
                zone.baseColorSource = null;
                // Still randomize HSB adjustments
                zone.baseHueOffset = randInt(-180, 180);
                zone.baseSaturationAdjust = randInt(-50, 50);
                zone.baseBrightnessAdjust = randInt(-30, 30);
            } else if (colorRoll < 0.75) {
                zone.baseColorMode = 'solid';
                zone.baseColor = randHex();
                zone.baseColorStrength = randFloat(0.4, 1.0, 0.05);
                zone.baseColorSource = null;
                zone.baseHueOffset = randInt(-60, 60);
                zone.baseSaturationAdjust = randInt(-30, 30);
                zone.baseBrightnessAdjust = randInt(-20, 20);
            } else {
                zone.baseColorMode = 'special';
                zone.baseColorSource = allSpecials.length > 0 ? pick(allSpecials) : null;
                zone.baseColorStrength = randFloat(0.5, 1.0, 0.05);
                zone.baseHueOffset = 0;
                zone.baseSaturationAdjust = 0;
                zone.baseBrightnessAdjust = 0;
            }

            // —€—€ 7. PATTERN STACK (extra pattern layers) —€—€
            zone.patternStack = [];
            if (zone.pattern !== 'none' && Math.random() < 0.3) {
                // 30% chance to add 1-2 stacked patterns
                const stackCount = randInt(1, 2);
                for (let s = 0; s < stackCount; s++) {
                    zone.patternStack.push({
                        id: pick(PATTERNS).id,
                        opacity: randInt(30, 100),
                        scale: randFloat(0.3, 3.0, 0.1),
                        rotation: randInt(0, 359),
                        strength: randFloat(0.3, 2.0, 0.1),
                        blendMode: pick(['normal', 'multiply', 'screen', 'overlay']),
                        offsetX: 0.5,
                        offsetY: 0.5,
                        flipH: false,
                        flipV: false,
                    });
                }
            }

            // —€—€ 8. OVERLAY LAYERS (the real magic — 0 to 5 layers) —€—€
            // Weighted: 0 layers=15%, 1=30%, 2=25%, 3=15%, 4=10%, 5=5%
            const overlayCount = weightedPick([15, 30, 25, 15, 10, 5]);
            const layerPrefixes = ['second', 'third', 'fourth', 'fifth'];
            // Map prefix → property names
            const layerKeys = layerPrefixes.map(p => ({
                base: p + 'Base',
                color: p + 'BaseColor',
                strength: p + 'BaseStrength',
                specStrength: p + 'BaseSpecStrength',
                blendMode: p + 'BaseBlendMode',
                fractalScale: p + 'BaseFractalScale',
                scale: p + 'BaseScale',
                pattern: p + 'BasePattern',
                patternOpacity: p + 'BasePatternOpacity',
                patternScale: p + 'BasePatternScale',
                patternRotation: p + 'BasePatternRotation',
                patternStrength: p + 'BasePatternStrength',
                patternInvert: p + 'BasePatternInvert',
                patternHarden: p + 'BasePatternHarden',
                patternOffsetX: p + 'BasePatternOffsetX',
                patternOffsetY: p + 'BasePatternOffsetY',
                colorSource: p + 'BaseColorSource',
            }));

            // Clear all overlay layers first
            layerKeys.forEach(k => {
                zone[k.base] = null;
                zone[k.color] = '#ffffff';
                zone[k.strength] = 0;
                zone[k.specStrength] = 1;
                zone[k.blendMode] = 'noise';
                zone[k.fractalScale] = 24;
                zone[k.scale] = 1.0;
                zone[k.pattern] = null;
                zone[k.patternOpacity] = 100;
                zone[k.patternScale] = 1.0;
                zone[k.patternRotation] = 0;
                zone[k.patternStrength] = 1;
                zone[k.patternInvert] = false;
                zone[k.patternHarden] = false;
                zone[k.patternOffsetX] = 0.5;
                zone[k.patternOffsetY] = 0.5;
                zone[k.colorSource] = null;
            });

            // Now fill the active layers
            // The 2nd base overlay is index 0, up to 5th base overlay at index 3
            // If overlayCount >= 5, we also set the main base as a monolithic and use all 4 overlay slots
            const activeCount = Math.min(overlayCount, 4);
            for (let li = 0; li < activeCount; li++) {
                const k = layerKeys[li];
                // Pick an overlay base
                zone[k.base] = pick(BASES).id;

                // Overlay color: 40% solid, 30% from special, 30% same-as-overlay
                const cRoll = Math.random();
                if (cRoll < 0.40) {
                    zone[k.colorSource] = null;
                    zone[k.color] = randHex();
                } else if (cRoll < 0.70 && allSpecials.length > 0) {
                    zone[k.colorSource] = 'mono:' + pick(allSpecials);
                } else {
                    zone[k.colorSource] = 'overlay';
                    // Sync color to overlay swatch
                    const disp = typeof getOverlayBaseDisplay !== 'undefined' && getOverlayBaseDisplay(zone[k.base]);
                    zone[k.color] = (disp && disp.swatch) ? (disp.swatch.startsWith('#') ? disp.swatch : '#' + disp.swatch) : randHex();
                }

                zone[k.strength] = randFloat(0.2, 1.0, 0.05);
                zone[k.specStrength] = randFloat(0.3, 2.0, 0.1);
                zone[k.blendMode] = pick(blendModes);
                zone[k.fractalScale] = randInt(1, 32) * 4; // 4 to 128, step 4
                zone[k.scale] = randFloat(0.1, 3.0, 0.05);

                // 60% chance to set a react-to pattern
                if (Math.random() < 0.60 && zone.pattern !== 'none') {
                    zone[k.pattern] = zone.pattern; // react to the main pattern
                    zone[k.patternOpacity] = randInt(40, 100);
                    zone[k.patternScale] = randFloat(0.3, 3.0, 0.1);
                    zone[k.patternRotation] = randInt(0, 359);
                    zone[k.patternStrength] = randFloat(0.3, 2.0, 0.1);
                    zone[k.patternInvert] = Math.random() < 0.3;
                    zone[k.patternHarden] = Math.random() < 0.4;
                }
            }

            // —€—€ 9. WEAR —€—€
            zone.wear = Math.random() < 0.15 ? randInt(1, 3) : 0;

            // Refresh UI
            renderZones();
            renderZoneDetail(index);
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();

            // Fun toast with a count of what was randomized
            const overlayMsg = activeCount > 0 ? ` + ${activeCount} overlay${activeCount > 1 ? 's' : ''}` : '';
            const baseName = zone.base ? (BASES.find(b => b.id === zone.base) || {}).name || zone.base : (MONOLITHICS.find(m => m.id === zone.finish) || {}).name || zone.finish;
            const patName = zone.pattern !== 'none' ? (PATTERNS.find(p => p.id === zone.pattern) || {}).name || zone.pattern : 'no pattern';
            // 2026-04-19 TRUE FIVE-HOUR (TF17c) — wrong showToast signature.
            // Pre-fix `, 4000` was treated as truthy isError → the celebratory
            // SHOKK'D toast was styled as an error. showToast has no duration
            // arg; drop it and let the default styling stand.
            showToast(`⚡ SHOKK'D! ${baseName} + ${patName}${overlayMsg}`);
        }
        if (typeof window !== 'undefined') window.shokkMe = shokkMe;

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
            // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W2): silent-stale.
            // applyCombo mutates render-relevant zone state (finish/base/pattern/
            // intensity/scale) but never refreshed the live preview.
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
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
            // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W3): silent-stale.
            // Chat-driven zone application could create/modify many zones at
            // once and still leave the preview frozen on the prior state.
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
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
            harmonies.analogous.forEach(c => { wheelDots += dotAt(hexToHSL(c).h, c); });
            harmonies.triadic.forEach(c => { wheelDots += dotAt(hexToHSL(c).h, c); });
            harmonies.split.forEach(c => { wheelDots += dotAt(hexToHSL(c).h, c); });

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
            // Find first truly empty zone (no color in any mode)
            let targetIdx = -1;
            for (let i = 0; i < zones.length; i++) {
                if (i !== fromZoneIndex &&
                    (zones[i].colorMode === 'none' || (zones[i].color === null && (!zones[i].colors || zones[i].colors.length === 0)))) {
                    targetIdx = i;
                    break;
                }
            }
            if (targetIdx === -1) {
                // All zones have colors — apply to next zone (with confirmation via toast)
                targetIdx = (fromZoneIndex + 1) % zones.length;
                if (targetIdx === fromZoneIndex) {
                    showToast('Only one zone exists — add another zone first', true);
                    return;
                }
                showToast(`Replacing color on Zone ${targetIdx + 1}: ${zones[targetIdx].name} with ${hex}`);
            }

            const r = parseInt(hex.substr(1, 2), 16);
            const g = parseInt(hex.substr(3, 2), 16);
            const b = parseInt(hex.substr(5, 2), 16);
            pushZoneUndo('Harmony color apply');
            zones[targetIdx].pickerColor = hex;
            zones[targetIdx].color = { color_rgb: [r, g, b], tolerance: zones[targetIdx].pickerTolerance || 40 };
            zones[targetIdx].colorMode = 'picker';
            zones[targetIdx].colors = [];
            selectedZoneIndex = targetIdx;
            renderZones();
            // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W4): silent-stale.
            // Harmony palette dropper updated zone color but the rendered car
            // didn't reflect the new color until the painter touched anything
            // else. Sister bug to W1-W3.
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            showToast(`Applied ${hex} to Zone ${targetIdx + 1}: ${zones[targetIdx].name}`);
        }

        // ===== SHORTCUT LEGEND =====
        function showShortcutLegend() {
            // Use the rich HTML-based shortcut overlay (id=shortcutOverlay) in paint-booth-v2.html
            var overlay = document.getElementById('shortcutOverlay');
            if (overlay) {
                overlay.style.display = overlay.style.display === 'none' ? 'block' : 'none';
            }
            // Also hide old dynamic overlay if it exists (backward compat)
            var oldOverlay = document.getElementById('shortcutLegendOverlay');
            if (oldOverlay) oldOverlay.style.display = 'none';
        }

        // ===== KEYBOARD SHORTCUTS =====
        document.addEventListener('keydown', (e) => {
            if (e.defaultPrevented) return;
            // Don't trigger when typing in inputs
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;

            // F5: Force refresh the Live Preview (abort any stuck render, reset pipeline)
            if (e.key === 'F5') {
                e.preventDefault();
                if (typeof forcePreviewRefresh === 'function') forcePreviewRefresh();
                return;
            }
            // Ctrl+R: Render (if server online)
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                safeDoRender();
                return;
            }
            // Ctrl+S: Save config (trigger autosave immediately)
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                if (typeof autoSave === 'function') autoSave();
                if (typeof showToast === 'function') showToast('Config saved');
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
            // Shift+R: Randomize selected zone (bare R = recolor tool)
            if (e.key === 'R' && e.shiftKey && !e.ctrlKey && !e.altKey) {
                randomizeZone(selectedZoneIndex);
                return;
            }
            // Shift+E: Toggle zone editor panel collapse/expand (bare E = edge detect tool)
            if (e.key === 'E' && e.shiftKey && !e.ctrlKey && !e.altKey) {
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
            // Alt+Arrow: Nudge current zone's drawn region (so you can align edges without redrawing)
            if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
                const step = e.shiftKey ? 5 : 1;
                const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
                const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
                if (typeof nudgeRegionSelection === 'function' && nudgeRegionSelection(dx, dy)) {
                    e.preventDefault();
                    showToast(`Nudged selection ${step}px`);
                    return;
                }
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
            // Shift+D: Duplicate selected zone (bare D = dodge tool)
            if (e.key === 'D' && e.shiftKey && !e.ctrlKey && !e.altKey) {
                duplicateZone(selectedZoneIndex);
                return;
            }
            // Delete/Backspace: Delete selected zone
            if (e.key === 'Delete' || e.key === 'Backspace') {
                deleteZone(selectedZoneIndex);
                return;
            }
            // Shift+N: Add new zone (bare N = pen tool)
            if (e.key === 'N' && e.shiftKey && !e.ctrlKey && !e.altKey) {
                addZone();
                return;
            }
            // V key: Toggle split view
            if (e.key === 'v' && !e.ctrlKey && !e.altKey) {
                toggleSplitView();
                return;
            }
            // ? or Ctrl+/: Show keyboard shortcuts
            if (e.key === '?' || (e.ctrlKey && e.key === '/')) {
                e.preventDefault();
                showShortcutLegend();
                return;
            }
            // Shift+H: Open history gallery (bare H = sharpen tool)
            if (e.key === 'H' && e.shiftKey && !e.ctrlKey && !e.altKey) {
                openHistoryGallery();
                return;
            }
            // Shift+T: Open template library (bare T = text tool)
            if (e.key === 'T' && e.shiftKey && !e.ctrlKey && !e.altKey) {
                openTemplateLibrary();
                return;
            }
            // Tool shortcuts (Photoshop/GIMP-like): P=Pick, W=Wand, A=Select All, B=Brush, O=Rect, L=Lasso, X=Erase
            if (!e.ctrlKey && !e.metaKey && !e.altKey) {
                const k = e.key.toLowerCase();
                if (k === 'p') { if (typeof setCanvasMode === 'function') { setCanvasMode('eyedropper'); e.preventDefault(); } return; }
                if (k === 'w') { if (typeof setCanvasMode === 'function') { setCanvasMode('wand'); e.preventDefault(); } return; }
                if (k === 'a') { if (typeof setCanvasMode === 'function') { setCanvasMode('selectall'); e.preventDefault(); } return; }
                if (k === 'b') { if (typeof setCanvasMode === 'function') { setCanvasMode('brush'); e.preventDefault(); } return; }
                if (k === 'o') { if (typeof setCanvasMode === 'function') { setCanvasMode('rect'); e.preventDefault(); } return; }
                if (k === 'l') { if (typeof setCanvasMode === 'function') { setCanvasMode('lasso'); e.preventDefault(); } return; }
                if (k === 'x') { if (typeof setCanvasMode === 'function') { setCanvasMode('erase'); e.preventDefault(); } return; }
            }
            // Escape: cancel lasso/rect first, then exit compare / close gallery / modal / undo panel
            if (e.key === 'Escape') {
                if (typeof cancelCanvasOperation === 'function' && cancelCanvasOperation()) return;
                if (document.getElementById('undoHistoryPanel')?.classList.contains('open')) { toggleUndoHistoryPanel(); return; }
                if (document.getElementById('historyGalleryOverlay')) { closeHistoryGallery(); return; }
                if (document.getElementById('templateLibraryOverlay')) { closeTemplateLibrary(); return; }
                if (document.getElementById('shortcutLegendOverlay')?.style.display === 'flex') {
                    document.getElementById('shortcutLegendOverlay').style.display = 'none'; return;
                }
                if (document.getElementById('shortcutOverlay')?.style.display !== 'none') {
                    document.getElementById('shortcutOverlay').style.display = 'none'; return;
                }
                if (typeof compareMode !== 'undefined' && compareMode) { toggleCompareMode(); return; }
                if (document.getElementById('finishCompareOverlay')?.classList.contains('active')) { closeFinishCompare(); return; }
                if (document.getElementById('finishBrowserOverlay')?.classList.contains('active')) { closeFinishBrowser(); return; }
                if (document.getElementById('presetGalleryOverlay')?.classList.contains('active')) { closePresetGallery(); return; }
                return;
            }
        });

        // ===== THEME TOGGLE =====
        const THEME_KEY = 'shokker_theme';
        function toggleTheme() {
            const body = document.body;
            const btn = document.getElementById('themeToggleBtn');
            const isLight = body.classList.toggle('theme-light');
            localStorage.setItem(THEME_KEY, isLight ? 'light' : 'dark');
            if (btn) btn.textContent = isLight ? 'ðŸŒ™ Dark' : '☀ Light';
        }
        function applySavedTheme() {
            const saved = localStorage.getItem(THEME_KEY);
            const btn = document.getElementById('themeToggleBtn');
            if (saved === 'light') {
                document.body.classList.add('theme-light');
                if (btn) btn.textContent = 'ðŸŒ™ Dark';
            } else if (btn) {
                btn.textContent = '☀ Light';
            }
        }

        // ===== INIT ON LOAD - run after DOM is ready so #zoneList and #zoneEditorFloat exist =====
        // =====================================================
        // SPEC STAMPS - Import sponsor/decal PNGs with alpha
        // =====================================================

        // Global state
        if (typeof window.stampLayers === 'undefined') window.stampLayers = [];
        if (typeof window.stampSpecFinish === 'undefined') window.stampSpecFinish = 'gloss';

        function importStamp() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.png,.tga,.PNG,.TGA';
            input.onchange = async function(e) {
                const file = e.target.files[0];
                if (!file) return;

                const img = new Image();
                const url = URL.createObjectURL(file);
                img.onload = function() {
                    window.stampLayers.push({
                        name: file.name,
                        img: img,
                        width: img.width,
                        height: img.height,
                        opacity: 1.0,
                        visible: true,
                    });
                    renderStampList();
                    showToast('Stamp added: ' + file.name + ' (' + img.width + 'x' + img.height + ')');
                    // FIVE-HOUR SHIFT Win H10: blob URL never revoked.
                    // Marathon #59 fixed this for the decal importer; the
                    // stamp importer was the asymmetric outlier. Without
                    // revocation, every stamp import leaks the blob (small
                    // per stamp but accumulates across a long painting
                    // session). Note: we keep the Image alive in
                    // stampLayers, so we can revoke after onload because
                    // the image's pixel data is already decoded.
                    try { URL.revokeObjectURL(url); } catch (_) {}
                    if (!window._spbStampSessionWarned) {
                        window._spbStampSessionWarned = true;
                        if (typeof showToast === 'function') {
                            showToast('Stamps are session-only \u2014 they are lost on page reload. Export before refreshing.', true);
                        }
                    }
                };
                img.onerror = function() {
                    // TGA files can't be loaded by Image directly
                    try { URL.revokeObjectURL(url); } catch (_) {}
                    showToast('Could not load image. Use PNG format for best results.', true);
                };
                img.src = url;
            };
            input.click();
        }

        // 2026-04-18 MARATHON bug #20: stamp ops didn't fire preview refresh.
        // Painter toggled a stamp visibility, Live Preview kept rendering
        // the old state. Same class as the strength-map silent drop.
        function removeStamp(idx) {
            window.stampLayers.splice(idx, 1);
            renderStampList();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function toggleStampVisibility(idx) {
            if (window.stampLayers[idx]) {
                window.stampLayers[idx].visible = !window.stampLayers[idx].visible;
                renderStampList();
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            }
        }

        function setStampOpacity(idx, val) {
            if (window.stampLayers[idx]) {
                window.stampLayers[idx].opacity = parseFloat(val);
                renderStampList();
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            }
        }

        function updateStampFinish() {
            const sel = document.getElementById('stampSpecFinish');
            if (sel) window.stampSpecFinish = sel.value;
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function clearAllStamps() {
            // 2026-04-19 FIVE-HOUR DEEP SHIFT (Pillman recon W13): destructive without confirm.
            // One misclick wiped every imported stamp with no undo. Sister
            // operations (delete one stamp, clear decals) all confirm — parity fix.
            var n = (window.stampLayers && window.stampLayers.length) || 0;
            if (n === 0) { showToast('No stamps to clear'); return; }
            if (typeof confirm === 'function' &&
                !confirm('Clear all ' + n + ' stamp' + (n === 1 ? '' : 's') + '? This cannot be undone.')) {
                return;
            }
            window.stampLayers = [];
            renderStampList();
            showToast('All stamps cleared');
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        }

        function renderStampList() {
            const container = document.getElementById('stampLayersList');
            const countEl = document.getElementById('stampCount');
            if (!container) return;
            const stamps = window.stampLayers;
            if (countEl) countEl.textContent = '(' + stamps.length + ' layer' + (stamps.length !== 1 ? 's' : '') + ')';

            if (stamps.length === 0) {
                container.innerHTML = '<div style="font-size:9px; color:var(--text-dim); padding:4px;">No stamps imported. Click "Import Stamp" to add sponsor/decal PNGs.</div>';
                return;
            }

            var html = '';
            stamps.forEach(function(s, i) {
                var vis = s.visible ? '\u{1F441}' : '\u{1F6AB}';
                var opacPct = Math.round(s.opacity * 100);
                html += '<div style="display:flex; align-items:center; gap:6px; padding:3px 0; border-bottom:1px solid var(--border);">'
                    + '<button onclick="toggleStampVisibility(' + i + ')" style="font-size:12px; cursor:pointer; background:none; border:none; padding:0;" title="Toggle visibility">' + vis + '</button>'
                    + '<span style="font-size:9px; color:var(--text-main); flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="' + s.name + '">' + s.name + '</span>'
                    + '<span style="font-size:8px; color:var(--text-dim);">' + opacPct + '%</span>'
                    + '<input type="range" min="0" max="100" value="' + opacPct + '" onchange="setStampOpacity(' + i + ', this.value/100)" style="width:50px; height:12px;">'
                    + '<button onclick="removeStamp(' + i + ')" style="font-size:10px; cursor:pointer; background:none; border:none; color:var(--error); padding:0;" title="Remove">\u2715</button>'
                    + '</div>';
            });
            container.innerHTML = html;
        }

        /**
         * Composite all visible stamps into a single RGBA canvas for server rendering.
         * Returns a canvas element with the stamps composited, preserving alpha.
         * Returns null if no visible stamps.
         */
        function compositeStampsForRender() {
            var stamps = window.stampLayers.filter(function(s) { return s.visible && s.img; });
            if (stamps.length === 0) return null;

            // Use 2048x2048 (standard canvas size)
            var w = 2048, h = 2048;
            var canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext('2d');

            // Start with fully transparent
            ctx.clearRect(0, 0, w, h);

            // Draw each stamp (they stack in order)
            stamps.forEach(function(s) {
                ctx.globalAlpha = s.opacity;
                ctx.drawImage(s.img, 0, 0, w, h);
            });
            ctx.globalAlpha = 1.0;

            return canvas;
        }

        // Make stamp functions globally available
        window.importStamp = importStamp;
        window.removeStamp = removeStamp;
        window.toggleStampVisibility = toggleStampVisibility;
        window.setStampOpacity = setStampOpacity;
        window.updateStampFinish = updateStampFinish;
        window.clearAllStamps = clearAllStamps;
        window.renderStampList = renderStampList;
        window.compositeStampsForRender = compositeStampsForRender;

        // ============================================================
        // SPB BOOT/UI POLISH MODULE  (50+ improvements; see report)
        // Single global namespace to avoid leaking into the rest of
        // the file. All hooks are defensive (guarded by typeof / try).
        // ============================================================
        window.SPB = window.SPB || {};
        const SPB = window.SPB;

        // ---------- (1) BOOT TIMING / STAGED INIT ----------
        // Improvement 1: Capture boot start so we can report cold-boot timing in console.
        SPB.bootStartTs = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
        SPB.bootMarks = [];
        SPB.mark = function(label) {
            try {
                const t = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
                SPB.bootMarks.push({ label, t: t - SPB.bootStartTs });
                if (typeof console !== 'undefined') console.log('[SPB-BOOT]', label, '+' + Math.round(t - SPB.bootStartTs) + 'ms');
            } catch (e) {}
        };

        // Improvement 2: Idle scheduler — defer non-critical init until after first paint.
        SPB.idle = function(fn, timeout) {
            if (typeof window.requestIdleCallback === 'function') {
                return window.requestIdleCallback(fn, { timeout: timeout || 2000 });
            }
            return setTimeout(fn, 16);
        };

        // Improvement 3: rAF helper for double-buffered post-paint init (used to push polling start to next frame).
        SPB.afterPaint = function(fn) {
            if (typeof requestAnimationFrame === 'function') {
                requestAnimationFrame(function() { requestAnimationFrame(fn); });
            } else {
                setTimeout(fn, 32);
            }
        };

        // ---------- (4-5) SERVER HEALTH / RECONNECT BANNER ----------
        // Improvement 4: Server health state machine with adaptive backoff.
        SPB.health = {
            online: null,            // null = unknown, true/false otherwise
            lastOk: 0,
            failures: 0,
            interval: null,
            minMs: 5000,
            maxMs: 60000,
            currentMs: 5000,
        };

        // Improvement 5: Reconnect banner element (created lazily so we don't bloat boot).
        SPB.showServerBanner = function(state, msg) {
            try {
                let el = document.getElementById('spbServerBanner');
                if (!el) {
                    el = document.createElement('div');
                    el.id = 'spbServerBanner';
                    el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;padding:6px 12px;font-size:12px;text-align:center;font-family:inherit;letter-spacing:0.04em;display:none;';
                    document.body && document.body.appendChild(el);
                }
                if (state === 'down') {
                    el.style.background = '#7a1d1d';
                    el.style.color = '#fff';
                    el.textContent = msg || 'Render server unreachable — retrying...';
                    el.style.display = 'block';
                } else if (state === 'reconnected') {
                    el.style.background = '#1d6a3a';
                    el.style.color = '#fff';
                    el.textContent = msg || 'Server reconnected';
                    el.style.display = 'block';
                    setTimeout(function() { el.style.display = 'none'; }, 2500);
                } else {
                    el.style.display = 'none';
                }
            } catch (e) {}
        };

        // Improvement 6: Health probe with adaptive polling — back off on failure, fast on success.
        SPB.probeHealth = async function() {
            const h = SPB.health;
            try {
                if (typeof ShokkerAPI === 'undefined' || !ShokkerAPI.baseUrl) return;
                const ctrl = (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) ? { signal: AbortSignal.timeout(4000) } : {};
                const res = await fetch(ShokkerAPI.baseUrl + '/build-check', ctrl);
                if (res && res.ok) {
                    if (h.online === false) SPB.showServerBanner('reconnected');
                    h.online = true;
                    h.lastOk = Date.now();
                    h.failures = 0;
                    h.currentMs = h.minMs;
                } else {
                    throw new Error('status ' + (res && res.status));
                }
            } catch (e) {
                h.failures += 1;
                if (h.online !== false) {
                    SPB.showServerBanner('down', 'Render server unreachable (attempt ' + h.failures + ') — retrying...');
                }
                h.online = false;
                // Improvement 7: Exponential backoff capped at maxMs.
                h.currentMs = Math.min(h.maxMs, Math.max(h.minMs, h.currentMs * 1.6));
            }
            // Improvement 8: Reschedule with current adaptive delay.
            if (h.interval) clearTimeout(h.interval);
            if (!document.hidden) h.interval = setTimeout(SPB.probeHealth, h.currentMs);
        };

        // ---------- (9) BUILD VERSION DISPLAY / UPDATE DETECTION ----------
        // Improvement 9: Persistent build/version cache so we can detect updates between launches.
        SPB.lastKnownBuild = null;
        try { SPB.lastKnownBuild = localStorage.getItem('spb_last_build'); } catch (e) {}

        SPB.applyBuildInfo = function(d) {
            try {
                if (!d) return;
                const v = d.version || '';
                const b = d.build || '';
                // Improvement 10: Title bar always reflects current version + build.
                if (v) document.title = 'Shokker Paint Booth v' + v + (b ? ' • B' + b : '');
                // Improvement 11: Update detection — toast if build number jumped while app was open elsewhere.
                if (b && SPB.lastKnownBuild && String(b) !== String(SPB.lastKnownBuild)) {
                    if (typeof showToast === 'function') {
                        showToast('New build detected (B' + b + '). Press F5 to reload.', false);
                    }
                }
                if (b) {
                    SPB.lastKnownBuild = String(b);
                    try { localStorage.setItem('spb_last_build', String(b)); } catch (e) {}
                }
                // Improvement 12: Stamp version in a status pill if present.
                const pill = document.getElementById('spbVersionPill');
                if (pill) pill.textContent = v ? 'v' + v : '';
            } catch (e) {}
        };

        // ---------- (13-19) MODAL STACK / FOCUS TRAP / KEYBOARD ----------
        // Improvement 13: Centralized modal stack so Esc closes the topmost modal first.
        SPB.modalStack = [];
        SPB.pushModal = function(id, closeFn) {
            if (!id) return;
            // De-dupe — bring to top.
            SPB.modalStack = SPB.modalStack.filter(function(m) { return m.id !== id; });
            SPB.modalStack.push({ id: id, close: closeFn });
        };
        SPB.popModal = function(id) {
            SPB.modalStack = SPB.modalStack.filter(function(m) { return m.id !== id; });
        };
        SPB.closeTopModal = function() {
            const top = SPB.modalStack.pop();
            if (top && typeof top.close === 'function') {
                try { top.close(); return true; } catch (e) {}
            }
            return false;
        };

        // Improvement 14: Tab focus trap — keeps focus inside an open modal.
        SPB.installFocusTrap = function(rootEl) {
            if (!rootEl) return function() {};
            function handler(e) {
                if (e.key !== 'Tab') return;
                const focusables = rootEl.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])');
                if (!focusables.length) return;
                const first = focusables[0];
                const last = focusables[focusables.length - 1];
                if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
                else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
            }
            rootEl.addEventListener('keydown', handler);
            return function uninstall() { rootEl.removeEventListener('keydown', handler); };
        };

        // Improvement 15: Centralized keyboard shortcut registry (used by cheat-sheet generator).
        SPB.shortcuts = SPB.shortcuts || [
            { keys: 'F1 / ?', desc: 'Show this cheat sheet' },
            { keys: 'F5', desc: 'Force preview refresh' },
            { keys: 'Ctrl+R', desc: 'Render' },
            { keys: 'Ctrl+S', desc: 'Save config (autosave)' },
            { keys: 'Ctrl+G', desc: 'Generate script' },
            { keys: '1-9', desc: 'Select zone' },
            { keys: 'Shift+R', desc: 'Randomize selected zone' },
            { keys: 'Shift+E', desc: 'Toggle zone editor panel' },
            { keys: '/', desc: 'Focus chat / finish search' },
            { keys: 'Esc', desc: 'Close top modal / cancel tool / clear search' },
            { keys: 'Alt+Arrows', desc: 'Nudge region selection' },
            { keys: 'Up/Down', desc: 'Cycle zones' },
            { keys: 'Ctrl+Up/Down', desc: 'Reorder zone priority' },
            { keys: 'Shift+D', desc: 'Duplicate zone' },
            { keys: 'Shift+N', desc: 'New zone' },
            { keys: 'Shift+H', desc: 'History gallery' },
            { keys: 'Shift+T', desc: 'Template library' },
            { keys: 'V', desc: 'Toggle split view' },
            { keys: 'P / W / A / B / O / L / X', desc: 'Pick / Wand / All / Brush / Rect / Lasso / Erase' },
            { keys: 'Delete / Backspace', desc: 'Delete selected zone' },
        ];

        // Improvement 16: Detect duplicate shortcut bindings at boot (warn in console only — no UI noise).
        SPB.detectShortcutConflicts = function() {
            try {
                const seen = {};
                const conflicts = [];
                SPB.shortcuts.forEach(function(s) {
                    s.keys.split('/').forEach(function(k) {
                        const key = k.trim().toLowerCase();
                        if (!key) return;
                        if (seen[key]) conflicts.push(key + ' (' + seen[key] + ' vs ' + s.desc + ')');
                        else seen[key] = s.desc;
                    });
                });
                if (conflicts.length) console.warn('[SPB-SHORTCUTS] potential conflicts:', conflicts);
            } catch (e) {}
        };

        // ---------- (20-26) LOCALSTORAGE / SETTINGS PERSISTENCE ----------
        // Improvement 17: Safe localStorage wrappers (handles QuotaExceededError, JSON errors).
        SPB.lsGet = function(key, fallback) {
            try {
                const v = localStorage.getItem(key);
                if (v == null) return fallback;
                return JSON.parse(v);
            } catch (e) { return fallback; }
        };
        SPB.lsSet = function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                if (e && (e.name === 'QuotaExceededError' || (e.code && e.code === 22))) {
                    SPB.warnQuota();
                }
                return false;
            }
        };

        // Improvement 18: localStorage quota check — warn approaching 5MB ceiling.
        SPB.warnQuota = function() {
            try {
                if (SPB._quotaWarned) return;
                SPB._quotaWarned = true;
                if (typeof showToast === 'function') showToast('Browser storage is nearly full — clear old templates/combos to free space.', true);
                console.warn('[SPB-STORAGE] localStorage quota exceeded.');
            } catch (e) {}
        };
        SPB.getStorageUsage = function() {
            try {
                let bytes = 0;
                for (let i = 0; i < localStorage.length; i++) {
                    const k = localStorage.key(i);
                    const v = localStorage.getItem(k) || '';
                    bytes += k.length + v.length;
                }
                return bytes;
            } catch (e) { return 0; }
        };

        // Improvement 19: Schema version + migration scaffold for stored settings.
        SPB.STORAGE_SCHEMA_VERSION = 2;
        SPB.migrateStorage = function() {
            try {
                const current = parseInt(localStorage.getItem('spb_schema_version') || '0', 10) || 0;
                if (current >= SPB.STORAGE_SCHEMA_VERSION) return;
                // v0 → v1: ensure spb_has_launched is normalized to '1'.
                if (current < 1 && localStorage.getItem('spb_has_launched')) {
                    localStorage.setItem('spb_has_launched', '1');
                }
                // v1 → v2: prune legacy keys from very old builds (silent best-effort).
                if (current < 2) {
                    ['shokker_old_palette', 'shokker_v3_state'].forEach(function(k) {
                        try { localStorage.removeItem(k); } catch (e) {}
                    });
                }
                localStorage.setItem('spb_schema_version', String(SPB.STORAGE_SCHEMA_VERSION));
            } catch (e) {}
        };

        // Improvement 20: UI scale (zoom) persistence.
        SPB.applySavedUiScale = function() {
            try {
                const s = parseFloat(localStorage.getItem('spb_ui_scale') || '1');
                if (s && s !== 1 && s >= 0.6 && s <= 1.6) {
                    document.documentElement.style.fontSize = (16 * s) + 'px';
                }
            } catch (e) {}
        };
        SPB.setUiScale = function(s) {
            try {
                if (!s || s < 0.6 || s > 1.6) return;
                localStorage.setItem('spb_ui_scale', String(s));
                document.documentElement.style.fontSize = (16 * s) + 'px';
            } catch (e) {}
        };

        // Improvement 21: Window size restore (Electron + browser).
        SPB.applySavedWindowSize = function() {
            try {
                if (typeof window === 'undefined' || !window.resizeTo) return;
                const w = parseInt(localStorage.getItem('spb_win_w') || '0', 10);
                const h = parseInt(localStorage.getItem('spb_win_h') || '0', 10);
                if (w > 600 && h > 400 && w < screen.width && h < screen.height) {
                    try { window.resizeTo(w, h); } catch (e) {}
                }
            } catch (e) {}
        };
        SPB.captureWindowSize = function() {
            try {
                if (window.outerWidth && window.outerHeight) {
                    localStorage.setItem('spb_win_w', String(window.outerWidth));
                    localStorage.setItem('spb_win_h', String(window.outerHeight));
                }
            } catch (e) {}
        };

        // Improvement 22: Panel collapse-state persistence.
        SPB.PANEL_KEY = 'spb_collapsed_panels';
        SPB.applyCollapsedPanels = function() {
            try {
                const map = SPB.lsGet(SPB.PANEL_KEY, {}) || {};
                Object.keys(map).forEach(function(id) {
                    const el = document.getElementById(id);
                    if (el && map[id]) el.classList.add('collapsed');
                });
            } catch (e) {}
        };
        SPB.persistPanelToggle = function(id, collapsed) {
            try {
                const map = SPB.lsGet(SPB.PANEL_KEY, {}) || {};
                if (collapsed) map[id] = true; else delete map[id];
                SPB.lsSet(SPB.PANEL_KEY, map);
            } catch (e) {}
        };

        // Improvement 23: Right-panel last-used tab persistence.
        SPB.RIGHT_TAB_KEY = 'spb_right_tab';
        SPB.applySavedRightTab = function() {
            try {
                const last = localStorage.getItem(SPB.RIGHT_TAB_KEY);
                if (last && typeof switchRightTab === 'function') {
                    SPB.idle(function() { try { switchRightTab(last); } catch (e) {} }, 500);
                }
            } catch (e) {}
        };
        // Patch switchRightTab to record last-used (safe wrapper, only once).
        if (typeof window.switchRightTab === 'function' && !window.switchRightTab.__spbWrapped) {
            const _origSwitchRightTab = window.switchRightTab;
            window.switchRightTab = function(name) {
                try { localStorage.setItem(SPB.RIGHT_TAB_KEY, name); } catch (e) {}
                return _origSwitchRightTab.apply(this, arguments);
            };
            window.switchRightTab.__spbWrapped = true;
        }

        // ---------- (27-31) RECENT FILES / RELOAD / NETWORK ERRORS ----------
        // Improvement 24: Recent paint files (last 5) for quick reload.
        SPB.RECENT_PAINTS_KEY = 'spb_recent_paints';
        SPB.MAX_RECENT_PAINTS = 5;
        SPB.getRecentPaints = function() { return SPB.lsGet(SPB.RECENT_PAINTS_KEY, []) || []; };
        SPB.addRecentPaint = function(path, meta) {
            if (!path) return;
            try {
                let list = SPB.getRecentPaints();
                list = list.filter(function(p) { return p && p.path !== path; });
                list.unshift({ path: path, meta: meta || {}, ts: Date.now() });
                if (list.length > SPB.MAX_RECENT_PAINTS) list = list.slice(0, SPB.MAX_RECENT_PAINTS);
                SPB.lsSet(SPB.RECENT_PAINTS_KEY, list);
            } catch (e) {}
        };
        SPB.clearRecentPaints = function() { SPB.lsSet(SPB.RECENT_PAINTS_KEY, []); };

        // Improvement 25: Reload last paint helper.
        SPB.reloadLastPaint = function() {
            const list = SPB.getRecentPaints();
            if (!list.length) {
                if (typeof showToast === 'function') showToast('No recent paint files', true);
                return;
            }
            const last = list[0];
            if (typeof window.loadPaintByPath === 'function') {
                try { window.loadPaintByPath(last.path); return; } catch (e) {}
            }
            if (typeof showToast === 'function') showToast('Reload helper not wired — last path: ' + last.path);
        };

        // Improvement 26: Network error wrapper — produces friendly user-facing message.
        SPB.friendlyFetchError = function(err) {
            if (!err) return 'Unknown network error';
            const msg = String(err.message || err);
            if (msg.indexOf('AbortError') >= 0 || msg.indexOf('aborted') >= 0) return 'Request timed out — server may be busy';
            if (msg.indexOf('Failed to fetch') >= 0) return 'Cannot reach render server (is it running?)';
            if (msg.indexOf('NetworkError') >= 0) return 'Network unreachable';
            return msg;
        };

        // Improvement 27: Loading overlay helper (busy indicator) for long fetches.
        SPB.setBusy = function(on, label) {
            try {
                let el = document.getElementById('spbBusyOverlay');
                if (on) {
                    if (!el) {
                        el = document.createElement('div');
                        el.id = 'spbBusyOverlay';
                        el.style.cssText = 'position:fixed;bottom:14px;right:14px;z-index:99998;background:rgba(0,0,0,0.78);color:#ffd84d;font-size:11px;padding:8px 12px;border-radius:6px;font-family:inherit;letter-spacing:0.05em;pointer-events:none;border:1px solid #b58200;box-shadow:0 4px 14px rgba(0,0,0,0.5);';
                        document.body && document.body.appendChild(el);
                    }
                    el.textContent = label || 'Working...';
                    el.style.display = 'block';
                } else if (el) {
                    el.style.display = 'none';
                }
            } catch (e) {}
        };

        // ---------- (32-34) STALE CONFIG / FIRST-RUN / PATH NORMALIZE ----------
        // Improvement 28: Stale-data warning if cached config is older than 24h.
        SPB.STALE_THRESHOLD_MS = 24 * 60 * 60 * 1000;
        SPB.checkStaleConfig = function() {
            try {
                const lastSave = parseInt(localStorage.getItem('spb_last_save_ts') || '0', 10);
                if (!lastSave) return;
                const age = Date.now() - lastSave;
                if (age > SPB.STALE_THRESHOLD_MS) {
                    const days = Math.floor(age / (24 * 60 * 60 * 1000));
                    if (typeof showToast === 'function') {
                        showToast('Restored config is ' + days + 'd old — verify before rendering.', false);
                    }
                }
            } catch (e) {}
        };
        SPB.stampConfigSave = function() {
            try { localStorage.setItem('spb_last_save_ts', String(Date.now())); } catch (e) {}
        };

        // Improvement 29: Sane first-run defaults applier (only once per profile).
        SPB.applyFirstRunDefaults = function() {
            try {
                if (localStorage.getItem('spb_defaults_applied')) return;
                if (!localStorage.getItem(SPB.RIGHT_TAB_KEY)) localStorage.setItem(SPB.RIGHT_TAB_KEY, 'finishes');
                if (!localStorage.getItem('spb_ui_scale')) localStorage.setItem('spb_ui_scale', '1');
                localStorage.setItem('spb_defaults_applied', '1');
            } catch (e) {}
        };

        // Improvement 30: Cross-platform path normalization.
        SPB.normalizePath = function(p) {
            if (!p) return p;
            try {
                let s = String(p).replace(/\\\\/g, '/').replace(/\\/g, '/');
                // Collapse repeats.
                s = s.replace(/\/{2,}/g, '/');
                return s;
            } catch (e) { return p; }
        };

        // Improvement 31: iRacing ID validation feedback (digits 1–9, length 4–9).
        SPB.validateIracingId = function(value) {
            const v = String(value || '').trim();
            if (!v) return { ok: false, reason: 'empty' };
            if (!/^\d+$/.test(v)) return { ok: false, reason: 'non-digit' };
            if (v.length < 4 || v.length > 9) return { ok: false, reason: 'length' };
            return { ok: true };
        };

        // Improvement 32: Output folder validation — flag obviously bad paths client-side.
        SPB.validateOutputFolder = function(value) {
            const v = String(value || '').trim();
            if (!v) return { ok: false, reason: 'empty' };
            // Reject path traversal / suspicious chars.
            if (/<|>|\||\?|\*|"|\u0000/.test(v)) return { ok: false, reason: 'bad-chars' };
            return { ok: true };
        };

        // ---------- (35-40) KEYBOARD / VISIBILITY / AUTOSAVE ----------
        // Improvement 33: Document-wide keydown additions: F1 cheat sheet, '/' search focus, Esc clears search.
        document.addEventListener('keydown', function(e) {
            try {
                if (e.defaultPrevented) return;
                // F1 → shortcut legend (in addition to `?`).
                if (e.key === 'F1') {
                    e.preventDefault();
                    if (typeof showShortcutLegend === 'function') showShortcutLegend();
                    return;
                }
                // Esc on top modal first (before delegating to legacy Esc handler).
                if (e.key === 'Escape' && SPB.modalStack.length) {
                    if (SPB.closeTopModal()) { e.preventDefault(); return; }
                }
                // '/' focuses search field if present (browser elements only).
                if (e.key === '/' && document.activeElement && (document.activeElement.tagName === 'BODY' || document.activeElement === document.documentElement)) {
                    const search = document.getElementById('finishSearchInput') || document.getElementById('chatInput');
                    if (search) { e.preventDefault(); search.focus(); search.select && search.select(); }
                    return;
                }
                // Esc clears search input when focused.
                if (e.key === 'Escape' && document.activeElement && document.activeElement.id === 'finishSearchInput') {
                    document.activeElement.value = '';
                    document.activeElement.dispatchEvent(new Event('input', { bubbles: true }));
                    return;
                }
            } catch (err) {}
        }, true);  // capture so we run before legacy handlers

        // Improvement 34: Visibility change handler — pause polling when tab hidden, resume when visible.
        document.addEventListener('visibilitychange', function() {
            try {
                if (document.hidden) {
                    if (SPB.health.interval) { clearTimeout(SPB.health.interval); SPB.health.interval = null; }
                    if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.pausePolling === 'function') {
                        ShokkerAPI.pausePolling();
                    }
                } else {
                    if (!SPB.health.interval) SPB.probeHealth();
                    if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.resumePolling === 'function') {
                        ShokkerAPI.resumePolling();
                    }
                }
            } catch (e) {}
        });

        // Improvement 35: Save on window blur — reduces data loss on Alt-Tab.
        window.addEventListener('blur', function() {
            try { if (typeof autoSave === 'function') { autoSave(); SPB.stampConfigSave(); } } catch (e) {}
        });

        // Improvement 36: Save on tab change — triggers when switching browser tabs to background.
        document.addEventListener('visibilitychange', function() {
            try {
                if (document.hidden && typeof autoSave === 'function') {
                    autoSave();
                    SPB.stampConfigSave();
                    SPB.captureWindowSize();
                }
            } catch (e) {}
        });

        // Improvement 37: beforeunload safety net — last-chance save and polling cleanup.
        window.addEventListener('beforeunload', function() {
            try {
                // BUG #72 (Owen, HIGH): autoSave() uses a 500ms debounce; the page
                // unloads before the timer fires. Use flushAutoSave() which writes
                // synchronously, then fall back to autoSave() if unavailable.
                if (typeof flushAutoSave === 'function') flushAutoSave();
                else if (typeof autoSave === 'function') autoSave();
                SPB.stampConfigSave();
                SPB.captureWindowSize();
                if (SPB.health.interval) { clearTimeout(SPB.health.interval); SPB.health.interval = null; }
                if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.stopPolling === 'function') {
                    ShokkerAPI.stopPolling();
                }
            } catch (e) {}
        });

        // Improvement 38: pagehide cleanup (Safari/iOS firing path that beforeunload can miss).
        window.addEventListener('pagehide', function() {
            try {
                // BUG #72: pagehide must ALSO flush — on mobile/Safari it's the only
                // reliable save hook (beforeunload is unreliable there).
                if (typeof flushAutoSave === 'function') flushAutoSave();
                if (SPB.health.interval) { clearTimeout(SPB.health.interval); SPB.health.interval = null; }
            } catch (e) {}
        });

        // BUG #72: visibilitychange → hidden is a THIRD save hook that fires
        // reliably when the painter switches apps / minimizes without closing.
        // Flushes opportunistically so 500ms of pending work doesn't sit in
        // the debounce timer while the painter is away.
        document.addEventListener('visibilitychange', function () {
            try {
                if (document.visibilityState === 'hidden' && typeof flushAutoSave === 'function') {
                    flushAutoSave();
                }
            } catch (e) {}
        });

        // ---------- (41-44) GLOBAL ERROR HOOKS ----------
        // Improvement 39: Global error handler — surfaces script errors as toast (rate-limited).
        SPB._lastErrTs = 0;
        window.addEventListener('error', function(ev) {
            try {
                const now = Date.now();
                if (now - SPB._lastErrTs < 2000) return; // throttle
                SPB._lastErrTs = now;
                const msg = (ev && ev.message) ? ev.message : 'Script error';
                console.error('[SPB-ERR]', msg, ev && ev.error);
                if (typeof showToast === 'function') showToast('Script error: ' + msg, true);
            } catch (e) {}
        });

        // Improvement 40: Unhandled promise rejection handler.
        window.addEventListener('unhandledrejection', function(ev) {
            try {
                const reason = ev && ev.reason;
                const msg = reason && reason.message ? reason.message : String(reason || 'unknown');
                console.error('[SPB-ERR-PROMISE]', msg);
                if (typeof showToast === 'function' && Date.now() - SPB._lastErrTs > 2000) {
                    SPB._lastErrTs = Date.now();
                    showToast('Background task failed: ' + SPB.friendlyFetchError(reason), true);
                }
            } catch (e) {}
        });

        // ---------- (45-50) BOOT PROGRESS / RECOVERY / TOUR ----------
        // Improvement 41: Boot progress indicator (only shown on first launch or slow boots).
        SPB._showBootProgress = function() {
            try {
                if (document.getElementById('spbBootProgress')) return;
                const el = document.createElement('div');
                el.id = 'spbBootProgress';
                el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:99999;background:#000;color:#ffd84d;padding:18px 26px;border:1px solid #b58200;border-radius:8px;font-family:inherit;font-size:13px;letter-spacing:0.06em;box-shadow:0 8px 30px rgba(0,0,0,0.7);';
                el.innerHTML = '<div style="margin-bottom:8px;">Initializing Shokker Paint Booth...</div><div id="spbBootStage" style="font-size:10px;color:#999;">Loading modules...</div>';
                document.body && document.body.appendChild(el);
            } catch (e) {}
        };
        SPB._setBootStage = function(label) {
            try {
                const el = document.getElementById('spbBootStage');
                if (el) el.textContent = label;
            } catch (e) {}
        };
        SPB._hideBootProgress = function() {
            try {
                const el = document.getElementById('spbBootProgress');
                if (el) el.parentNode.removeChild(el);
            } catch (e) {}
        };

        // Improvement 42: Boot recovery / retry — if init fails, show error with Retry button.
        SPB.showBootError = function(err) {
            try {
                const wrap = document.createElement('div');
                wrap.id = 'spbBootError';
                wrap.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:99999;background:#1a0e0e;color:#ffb3b3;padding:22px 28px;border:1px solid #7a1d1d;border-radius:8px;font-family:inherit;max-width:560px;font-size:12px;line-height:1.5;box-shadow:0 8px 40px rgba(0,0,0,0.8);';
                wrap.innerHTML = '<div style="font-size:14px;color:#ff6b6b;margin-bottom:8px;">Initialization failed</div>'
                    + '<div style="margin-bottom:14px;font-family:monospace;background:#000;padding:8px;border-radius:4px;">' + (err && err.message ? err.message : String(err || 'unknown')) + '</div>'
                    + '<div style="display:flex;gap:8px;">'
                    + '<button id="spbBootRetry" style="background:#b58200;color:#000;border:none;padding:8px 14px;cursor:pointer;font-weight:bold;border-radius:4px;">Retry</button>'
                    + '<button id="spbBootReload" style="background:#333;color:#ccc;border:none;padding:8px 14px;cursor:pointer;border-radius:4px;">Reload page</button>'
                    + '</div>';
                document.body && document.body.appendChild(wrap);
                const retry = document.getElementById('spbBootRetry');
                if (retry) retry.onclick = function() {
                    try { wrap.parentNode.removeChild(wrap); } catch (e) {}
                    try { runBoot(); } catch (e) { SPB.showBootError(e); }
                };
                const rel = document.getElementById('spbBootReload');
                if (rel) rel.onclick = function() { try { window.location.reload(); } catch (e) {} };
            } catch (e) {}
        };

        // Improvement 43: Tour guide stub — first-launch walkthrough trigger (lightweight, no UI bloat).
        SPB.shouldShowTour = function() {
            try { return !localStorage.getItem('spb_tour_seen'); } catch (e) { return false; }
        };
        SPB.markTourSeen = function() {
            try { localStorage.setItem('spb_tour_seen', '1'); } catch (e) {}
        };

        // Improvement 44: Welcome message gate — only show once per browser session (in addition to first-launch).
        SPB.shouldShowWelcomeThisSession = function() {
            try {
                if (sessionStorage.getItem('spb_welcomed_this_session')) return false;
                sessionStorage.setItem('spb_welcomed_this_session', '1');
                return true;
            } catch (e) { return true; }
        };

        // Improvement 45: Tooltip enhancement — append shortcut hints to elements with data-shortcut.
        SPB.enhanceTooltips = function() {
            try {
                document.querySelectorAll('[data-shortcut]').forEach(function(el) {
                    if (el.__spbTipDone) return;
                    const sc = el.getAttribute('data-shortcut');
                    const t = el.getAttribute('title') || '';
                    el.setAttribute('title', t ? (t + '  (' + sc + ')') : sc);
                    el.__spbTipDone = true;
                });
            } catch (e) {}
        };

        // Improvement 46: Status-bar polish — inject thin separators between status pill children.
        SPB.polishStatusBar = function() {
            try {
                const bar = document.getElementById('statusBar') || document.querySelector('.status-bar');
                if (!bar || bar.__spbPolished) return;
                bar.style.gap = bar.style.gap || '10px';
                Array.prototype.forEach.call(bar.children, function(child, i, arr) {
                    if (i > 0 && i < arr.length) {
                        child.style.borderLeft = child.style.borderLeft || '1px solid rgba(255,255,255,0.08)';
                        child.style.paddingLeft = child.style.paddingLeft || '10px';
                    }
                });
                bar.__spbPolished = true;
            } catch (e) {}
        };

        // Improvement 47: Theme quick-toggle keyboard shortcut (Shift+Ctrl+T).
        // SESSION ROUTER: bail on defaultPrevented.
        document.addEventListener('keydown', function(e) {
            try {
                if (e.defaultPrevented) return;
                if (e.ctrlKey && e.shiftKey && (e.key === 'T' || e.key === 't')) {
                    e.preventDefault();
                    if (typeof toggleTheme === 'function') toggleTheme();
                }
            } catch (err) {}
        });

        // Improvement 48: Settings dropdown organizer — groups settings buttons by data-settings-group attr.
        SPB.organizeSettingsDropdown = function() {
            try {
                const dd = document.getElementById('settingsDropdown');
                if (!dd || dd.__spbOrganized) return;
                const items = Array.prototype.slice.call(dd.querySelectorAll('[data-settings-group]'));
                if (!items.length) return;
                const groups = {};
                items.forEach(function(it) {
                    const g = it.getAttribute('data-settings-group') || 'Other';
                    (groups[g] = groups[g] || []).push(it);
                });
                Object.keys(groups).forEach(function(g) {
                    const header = document.createElement('div');
                    header.textContent = g.toUpperCase();
                    header.style.cssText = 'font-size:9px;color:#888;letter-spacing:0.1em;padding:6px 10px 2px;';
                    if (groups[g][0].parentNode) groups[g][0].parentNode.insertBefore(header, groups[g][0]);
                });
                dd.__spbOrganized = true;
            } catch (e) {}
        };

        // Improvement 49: Render-history polling cleanup helper — exposed for window unload paths.
        SPB.cleanupAllPolling = function() {
            try {
                if (SPB.health.interval) { clearTimeout(SPB.health.interval); SPB.health.interval = null; }
                if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.stopPolling === 'function') {
                    ShokkerAPI.stopPolling();
                }
                (SPB._intervals || []).forEach(function(id) { try { clearInterval(id); } catch (e) {} });
                SPB._intervals = [];
            } catch (e) {}
        };
        SPB._intervals = [];
        SPB.trackInterval = function(id) { SPB._intervals.push(id); return id; };

        // Improvement 50: Boot finalize — runs after DOM settles to apply non-critical polish.
        SPB.finalizeBoot = function() {
            SPB.mark('finalize-start');
            SPB.applySavedUiScale();
            SPB.applyCollapsedPanels();
            SPB.applySavedRightTab();
            SPB.checkStaleConfig();
            SPB.detectShortcutConflicts();
            SPB.enhanceTooltips();
            SPB.polishStatusBar();
            SPB.organizeSettingsDropdown();
            SPB.mark('finalize-end');
        };

        // Improvement 51: Slow-boot detection — show progress only if init takes > 600ms.
        SPB._slowBootTimer = setTimeout(function() {
            if (!SPB._bootDone) SPB._showBootProgress();
        }, 600);

        // Improvement 52: BroadcastChannel cross-tab notify — alert other tabs about updates.
        try {
            if (typeof BroadcastChannel === 'function') {
                SPB._bc = new BroadcastChannel('spb_updates');
                SPB._bc.onmessage = function(ev) {
                    if (!ev || !ev.data) return;
                    if (ev.data.type === 'build' && SPB.lastKnownBuild && String(ev.data.build) !== String(SPB.lastKnownBuild)) {
                        if (typeof showToast === 'function') showToast('Another tab detected a new build (B' + ev.data.build + ')', false);
                    }
                };
            }
        } catch (e) {}

        // Improvement 53: Wrapper that lets the rest of the file kick adaptive health probing.
        SPB.startAdaptiveHealth = function() {
            if (SPB.health.interval) clearTimeout(SPB.health.interval);
            SPB.idle(function() { SPB.probeHealth(); }, 1500);
        };

        // Run lightweight one-shots immediately (safe even before DOMContentLoaded).
        SPB.migrateStorage();
        SPB.applyFirstRunDefaults();

        function runBoot() {
            try {
                SPB.mark('runBoot-start');
                applySavedTheme();
                if (typeof init !== 'function') {
                    // Improvement 54: explicit recoverable failure path.
                    SPB._bootDone = true;
                    if (SPB._slowBootTimer) clearTimeout(SPB._slowBootTimer);
                    SPB._hideBootProgress();
                    SPB.showBootError(new Error('init() function not found — script load order broken'));
                    return;
                }
                SPB._setBootStage('Initializing core...');
                init();
                applySavedTheme();
                SPB._setBootStage('Rendering zones...');
                if (typeof renderZones === 'function') renderZones();
                if (typeof renderZoneDetail === 'function' && typeof zones !== 'undefined' && zones.length > 0) renderZoneDetail(0);
                var didRestore = false;
                SPB._setBootStage('Restoring previous session...');
                if (typeof autoRestore === 'function') didRestore = autoRestore();
                if (typeof zones !== 'undefined' && zones.length === 0) {
                    init();
                    if (typeof renderZones === 'function') renderZones();
                    if (typeof renderZoneDetail === 'function' && zones.length > 0) renderZoneDetail(0);
                }
                SPB._bootDone = true;
                if (SPB._slowBootTimer) clearTimeout(SPB._slowBootTimer);
                SPB._hideBootProgress();
                SPB.mark('runBoot-end');
                // Improvement 55: defer non-critical polish to next idle cycle so first paint is fast.
                SPB.afterPaint(function() {
                    SPB.idle(function() { SPB.finalizeBoot(); }, 1500);
                    SPB.idle(function() { SPB.startAdaptiveHealth(); }, 2000);
                });
            } catch (err) {
                SPB._bootDone = true;
                if (SPB._slowBootTimer) clearTimeout(SPB._slowBootTimer);
                SPB._hideBootProgress();
                SPB.showBootError(err);
                console.error('[SPB-BOOT] runBoot failed:', err);
            }
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', runBoot);
        } else {
            runBoot();
        }

        // First-run welcome message  (Improvement 56: gated to first-launch AND first time this session)
        if (!localStorage.getItem('spb_has_launched')) {
            localStorage.setItem('spb_has_launched', '1');
            setTimeout(function() {
                if (typeof showToast === 'function') {
                    showToast('Welcome to Shokker Paint Booth! Press ? or F1 for keyboard shortcuts.', false);
                }
            }, 2000);
        } else if (SPB.shouldShowWelcomeThisSession && SPB.shouldShowWelcomeThisSession()) {
            // Returning user, new browser session — quieter reminder only on slow boots.
            // Intentionally do nothing here to keep startup quiet for repeat users.
        }

        // Clear iRacing ID highlight once user enters their ID
        const _idInput = document.getElementById('iracingId');
        if (_idInput) {
            const _clearIdHighlight = () => {
                if (_idInput.value.trim()) {
                    _idInput.style.border = '';
                    _idInput.style.background = '';
                    const hint = document.getElementById('iracingIdHint');
                    if (hint) hint.style.display = 'none';
                } else {
                    _idInput.style.border = '2px solid var(--accent-orange)';
                    _idInput.style.background = 'rgba(255,165,0,0.08)';
                    const hint = document.getElementById('iracingIdHint');
                    if (hint) hint.style.display = '';
                }
            };
            _idInput.addEventListener('input', _clearIdHighlight);
            _idInput.addEventListener('change', _clearIdHighlight);
            // Check on load
            setTimeout(_clearIdHighlight, 1000);
        }

        // Prevent page scroll when dragging Base or Pattern intensity sliders (wheel would scroll the page)
        document.addEventListener('wheel', function (e) {
            if (e.target.closest('.intensity-rows-wrap') || e.target.closest('.intensity-control-group')) {
                e.preventDefault();
            }
        }, { passive: false });

        // Auto-save: listen for changes on ALL inputs in the sidebar (debounced to avoid save-per-keystroke)
        // Improvement 59: stamp last-save timestamp so stale-config check works.
        const _debouncedAutoSave = _spbDebounce(function() { try { autoSave(); SPB.stampConfigSave(); } catch (e) {} }, 500);
        const _autoSaveStamped = function() { try { autoSave(); SPB.stampConfigSave(); } catch (e) {} };
        document.querySelectorAll('#car-info-body input, #car-info-body select').forEach(el => {
            el.addEventListener('change', _autoSaveStamped);
            el.addEventListener('input', _debouncedAutoSave);
        });

        // Improvement 60: Live iRacing ID validation feedback (uses SPB.validateIracingId).
        try {
            const _idEl = document.getElementById('iracingId');
            if (_idEl && !_idEl.__spbValidatorBound) {
                const _validate = function() {
                    const r = SPB.validateIracingId(_idEl.value);
                    if (r.ok) {
                        _idEl.style.outline = '';
                        _idEl.title = 'iRacing customer ID';
                    } else if (_idEl.value.trim()) {
                        _idEl.style.outline = '1px solid #ff8c42';
                        _idEl.title = 'iRacing ID should be 4–9 digits (' + r.reason + ')';
                    } else {
                        _idEl.style.outline = '';
                    }
                };
                _idEl.addEventListener('input', _validate);
                _idEl.addEventListener('blur', _validate);
                _idEl.__spbValidatorBound = true;
            }
        } catch (e) {}

        // Improvement 61: Output folder client-side validation.
        try {
            const _outEl = document.getElementById('outputFolder') || document.getElementById('outputPath');
            if (_outEl && !_outEl.__spbValidatorBound) {
                const _validateOut = function() {
                    const r = SPB.validateOutputFolder(_outEl.value);
                    if (r.ok) {
                        _outEl.style.outline = '';
                    } else if (_outEl.value.trim()) {
                        _outEl.style.outline = '1px solid #ff8c42';
                        _outEl.title = 'Invalid output path (' + r.reason + ')';
                    } else {
                        _outEl.style.outline = '';
                    }
                    // Improvement 62: Auto-normalize backslashes on blur for consistency.
                    if (_outEl.value && _outEl.value.indexOf('\\') >= 0) {
                        // do not rewrite during input; only on blur
                    }
                };
                _outEl.addEventListener('input', _validateOut);
                _outEl.addEventListener('blur', function() {
                    _validateOut();
                    try { _outEl.value = SPB.normalizePath(_outEl.value); } catch (e) {}
                });
                _outEl.__spbValidatorBound = true;
            }
        } catch (e) {}

        // Improvement 63: Storage usage logger (one-shot, console only — useful for QA).
        SPB.idle(function() {
            try {
                const used = SPB.getStorageUsage();
                if (used > 0) console.log('[SPB-STORAGE] localStorage usage: ' + Math.round(used / 1024) + 'KB');
                if (used > 4 * 1024 * 1024) SPB.warnQuota();
            } catch (e) {}
        }, 4000);

        // Improvement 64: Recent paints menu renderer (idempotent — safe if no anchor element).
        SPB.renderRecentPaintsMenu = function() {
            try {
                const host = document.getElementById('recentPaintsMenu');
                if (!host) return;
                const list = SPB.getRecentPaints();
                if (!list.length) {
                    host.innerHTML = '<div style="font-size:10px;color:#888;padding:4px;">No recent paints yet</div>';
                    return;
                }
                host.innerHTML = list.map(function(p, i) {
                    const name = (p.path || '').split('/').pop().split('\\').pop();
                    return '<div data-rp-idx="' + i + '" style="cursor:pointer;padding:4px 6px;font-size:11px;border-bottom:1px solid #222;" title="' + (p.path || '') + '">' + (name || '(unnamed)') + '</div>';
                }).join('');
                Array.prototype.forEach.call(host.querySelectorAll('[data-rp-idx]'), function(row) {
                    row.onclick = function() {
                        const idx = parseInt(row.getAttribute('data-rp-idx'), 10);
                        const p = SPB.getRecentPaints()[idx];
                        if (!p) return;
                        if (typeof window.loadPaintByPath === 'function') {
                            try { window.loadPaintByPath(p.path); } catch (e) {}
                        } else if (typeof showToast === 'function') {
                            showToast('Recent: ' + p.path);
                        }
                    };
                });
            } catch (e) {}
        };

        // Improvement 65: Expose recent-paint helpers globally so save/load flows can call them.
        window.spbAddRecentPaint = SPB.addRecentPaint;
        window.spbReloadLastPaint = SPB.reloadLastPaint;
        window.spbRenderRecentPaintsMenu = SPB.renderRecentPaintsMenu;

        // Improvement 66: Ctrl+Shift+R reload-last-paint shortcut (note: differs from Ctrl+R = render).
        // SESSION ROUTER: bail on defaultPrevented.
        document.addEventListener('keydown', function(e) {
            try {
                if (e.defaultPrevented) return;
                if (e.ctrlKey && e.shiftKey && (e.key === 'R' || e.key === 'r')) {
                    e.preventDefault();
                    SPB.reloadLastPaint();
                }
            } catch (err) {}
        });

        // Improvement 67: MutationObserver to enhance tooltips on any newly-added [data-shortcut] elements.
        try {
            if (typeof MutationObserver === 'function') {
                const _spbMO = new MutationObserver(_spbDebounce(function() { SPB.enhanceTooltips(); }, 250));
                _spbMO.observe(document.documentElement, { childList: true, subtree: true });
                SPB._mo = _spbMO;
            }
        } catch (e) {}

        // Improvement 68: Click-delegated panel-collapse persistence — any element with [data-panel-id] persists state.
        document.addEventListener('click', function(e) {
            try {
                const t = e.target.closest && e.target.closest('[data-panel-toggle]');
                if (!t) return;
                const pid = t.getAttribute('data-panel-toggle');
                if (!pid) return;
                const panel = document.getElementById(pid);
                if (!panel) return;
                const collapsed = panel.classList.toggle('collapsed');
                SPB.persistPanelToggle(pid, collapsed);
            } catch (err) {}
        });

        // Improvement 69: Save window-size on resize end (debounced).
        window.addEventListener('resize', _spbDebounce(function() { SPB.captureWindowSize(); }, 500));

        // Improvement 70: Window-focus health probe — quick check on tab regain.
        window.addEventListener('focus', function() {
            try { if (!document.hidden) SPB.idle(function() { SPB.probeHealth(); }, 200); } catch (e) {}
        });

        // Debounced window resize handler -- relayout UI on resize without hammering DOM
        window.addEventListener('resize', _spbDebounce(function() {
            if (typeof renderZoneQuickView === 'function') renderZoneQuickView();
            if (typeof updateBottomBarShift === 'function') updateBottomBarShift();
        }, 200));

        ShokkerAPI.startPolling();

        // Thumbnail status: show banner if pre-rendered thumbnails are missing so user can run rebuild_thumbnails.py
        setTimeout(function () {
            if (typeof checkThumbnailStatus === 'function') checkThumbnailStatus();
        }, 2500);

        // BUILD 25: Server build check (zombie process fix applied in Electron)
        // Improvement 57: integrated with SPB.health (banner + adaptive backoff) and SPB.applyBuildInfo (title + update detect).
        setTimeout(async () => {
            const el = document.getElementById('b21check');
            try {
                if (typeof ShokkerAPI === 'undefined' || !ShokkerAPI.baseUrl) {
                    console.warn('[BUILD-CHECK] ShokkerAPI not available yet');
                    return;
                }
                const res = await fetch(ShokkerAPI.baseUrl + '/build-check', { signal: AbortSignal.timeout(5000) });
                if (!res.ok) console.warn('[BUILD-CHECK] Server returned status ' + res.status);
                const rawText = await res.text();
                console.log('[BUILD-CHECK] status=' + res.status + ' raw=' + rawText.substring(0, 200));
                try {
                    const d = JSON.parse(rawText);
                    console.log(`[BUILD-CHECK] Server B${d.build} | PID:${d.pid} | port:${d.shokker_port_env}`);
                    SPB.applyBuildInfo(d);
                    SPB.health.online = true;
                    SPB.health.lastOk = Date.now();
                    // Improvement 58: notify other tabs about current build via BroadcastChannel.
                    try { if (SPB._bc && d.build) SPB._bc.postMessage({ type: 'build', build: d.build }); } catch (e) {}
                    // GPU status badge
                    if (d.gpu) {
                        var gpuBadge = document.getElementById('gpuStatusBadge');
                        if (gpuBadge) {
                            gpuBadge.textContent = d.gpu.icon + ' ' + (d.gpu.accelerated ? d.gpu.name : 'CPU');
                            gpuBadge.title = d.gpu.accelerated ?
                                'GPU Accelerated: ' + d.gpu.name + ' (' + d.gpu.vram_mb + 'MB VRAM)' :
                                'CPU Mode -- install CuPy for GPU acceleration';
                            gpuBadge.style.color = d.gpu.accelerated ? '#00ff88' : '#888';
                        }
                    }
                } catch (jsonErr) {
                    console.warn(`[BUILD-CHECK] HTTP ${res.status} NOT JSON: "${rawText.substring(0, 60)}..."`);
                    document.title = `Shokker Paint Booth`;
                }
            } catch (e) {
                console.error('[BUILD-CHECK] FAILED:', e);
                console.error(`[BUILD-CHECK] FAILED: ${e.message}`);
                document.title = 'Shokker Paint Booth — Server Unreachable';
                SPB.health.online = false;
                SPB.showServerBanner('down', 'Render server unreachable: ' + SPB.friendlyFetchError(e));
            }
        }, 3000);

