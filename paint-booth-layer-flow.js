/* ═══════════════════════════════════════════════════════════════════
   SHOKKER PAINT BOOTH — LAYER FLOW MODULE v3
   "Layers must work like a real editor"

   v3 (50+ improvements over v2). Categories:
   - Persistence       (#1, #22, #38)
   - Layer panel UX    (#2-#5, #9-#13, #15-#23, #35, #39)
   - Effect tooling    (#6-#8, #24-#28, #44, #45, #47, #48)
   - Lock-zone work    (#29, #30, #46)
   - Watchdog & perf   (#31, #32, #41, #42)
   - Navigation        (#14, #33, #34, #43)
   - Dock chrome       (#36, #37, #38, #40, #49, #50)
   - Misc safety       (#51, #52, #53, #54)

   PRESERVED:
   - Alpha-based layer mask logic (findTopmostLayerAt uses alpha > 16)
   - Gold "🔒 Lock Active Zone to This Layer" button
   - Dock placement INSIDE .center-panel as a horizontal strip
   ═══════════════════════════════════════════════════════════════════ */

(function() {
    'use strict';

    // ── Tiny safe persistence helpers (improvement category: storage) ─
    var LS_PREFIX = 'spbLayerFlow.';
    function lsGet(key, fallback) {
        try { var v = localStorage.getItem(LS_PREFIX + key); return v == null ? fallback : v; } catch (e) { return fallback; }
    }
    function lsSet(key, value) {
        try { localStorage.setItem(LS_PREFIX + key, value); } catch (e) {}
    }
    function lsGetJSON(key, fallback) {
        try { var v = localStorage.getItem(LS_PREFIX + key); return v == null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
    }
    function lsSetJSON(key, value) {
        try { localStorage.setItem(LS_PREFIX + key, JSON.stringify(value)); } catch (e) {}
    }

    function ready(fn) {
        if (document.readyState !== 'loading') { fn(); }
        else { document.addEventListener('DOMContentLoaded', fn); }
    }

    function safeToast(msg, isError) {
        if (typeof showToast === 'function') {
            try { showToast(msg, !!isError); } catch (e) {}
        }
    }

    // (#11) Auto-name fallback — derive a friendly name from a layer.
    function deriveLayerName(L) {
        if (!L) return 'Layer';
        if (L.name && L.name !== 'Layer') return L.name;
        if (L.text) return ('"' + String(L.text).slice(0, 24) + '"');
        if (L.shape) return ('Shape · ' + L.shape);
        if (L.bbox) {
            var w = (L.bbox[2] - L.bbox[0]) || 0, h = (L.bbox[3] - L.bbox[1]) || 0;
            if (w && h) return ('Layer ' + w + '×' + h);
        }
        return 'Layer';
    }

    // (#28) Effect intensity multiplier (global). Stored in LS, applied lazily.
    var _effectIntensity = parseFloat(lsGet('effectIntensity', '1.0')) || 1.0;
    function getEffectIntensity() { return _effectIntensity; }
    function setEffectIntensity(v) {
        v = Math.max(0, Math.min(2, parseFloat(v) || 1.0));
        _effectIntensity = v;
        lsSet('effectIntensity', String(v));
        var pill = document.getElementById('layerDockFxPill');
        if (pill) pill.textContent = '✨ FX × ' + v.toFixed(2);
    }

    // (#26)(#27) Effect preset library (saved combos).
    function getEffectPresets() { return lsGetJSON('effectPresets', {}); }
    function saveEffectPreset(name, fx) {
        var p = getEffectPresets(); p[name] = fx; lsSetJSON('effectPresets', p);
    }
    function deleteEffectPreset(name) {
        var p = getEffectPresets(); delete p[name]; lsSetJSON('effectPresets', p);
    }

    // (#7) Effect copy-paste clipboard (in-memory, survives layer switches).
    var _fxClipboard = null;
    function copyLayerFx(layerId) {
        if (typeof _psdLayers === 'undefined') return false;
        var L = _psdLayers.find(function(x) { return x.id === layerId; });
        if (!L || !L.effects) return false;
        try { _fxClipboard = JSON.parse(JSON.stringify(L.effects)); return true; }
        catch (e) { _fxClipboard = null; return false; }
    }
    function pasteLayerFx(layerId) {
        if (!_fxClipboard || typeof _psdLayers === 'undefined') return false;
        var L = _psdLayers.find(function(x) { return x.id === layerId; });
        if (!L) return false;
        // 2026-04-19 TRUE FIVE-HOUR (TF18) — was mutating L.effects with no
        // undo entry. Painter pasted effects, could not Ctrl+Z to revert.
        // _pushLayerStackUndo (canvas.js) takes a stack snapshot so the
        // operation undoes cleanly.
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('Paste layer effects');
        try {
            L.effects = JSON.parse(JSON.stringify(_fxClipboard));
            if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            return true;
        } catch (e) { return false; }
    }

    // (#6) Quick effect presets (built-in defaults).
    var QUICK_FX_PRESETS = {
        'Drop Shadow': { dropShadow: { enabled: true, dx: 4, dy: 6, blur: 8, opacity: 0.55, color: '#000000' } },
        'Outer Glow':  { outerGlow:  { enabled: true, blur: 12, opacity: 0.8, color: '#ff7a18' } },
        'Stroke 2px':  { stroke:     { enabled: true, width: 2, color: '#ffffff', position: 'outside' } },
        'Color Overlay': { colorOverlay: { enabled: true, color: '#ff0000', opacity: 0.5 } },
        'Bevel':       { bevel:      { enabled: true, depth: 4, soften: 2, angle: 120 } }
    };
    function applyQuickFx(layerId, presetName) {
        if (typeof _psdLayers === 'undefined') return;
        var L = _psdLayers.find(function(x) { return x.id === layerId; });
        if (!L) return;
        var preset = QUICK_FX_PRESETS[presetName];
        if (!preset) return;
        // 2026-04-19 TRUE FIVE-HOUR (TF19) — sister fix to TF18. Quick-fx
        // preset application merged keys into L.effects with no undo entry.
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('Apply quick FX: ' + presetName);
        L.effects = L.effects || {};
        Object.keys(preset).forEach(function(k) { L.effects[k] = preset[k]; });
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        safeToast('Applied "' + presetName + '" to ' + (L.name || 'layer'));
    }

    // (#9) Color tags. (#10) Comments. (#12) Pin. (#11/#13) Recents.
    function getLayerMeta(layerId) {
        var all = lsGetJSON('layerMeta', {});
        return all[layerId] || {};
    }
    function setLayerMeta(layerId, patch) {
        var all = lsGetJSON('layerMeta', {});
        all[layerId] = Object.assign({}, all[layerId] || {}, patch);
        lsSetJSON('layerMeta', all);
    }

    function pushRecentLayer(layerId) {
        if (!layerId) return;
        var recents = lsGetJSON('recentLayers', []);
        recents = recents.filter(function(x) { return x !== layerId; });
        recents.unshift(layerId);
        if (recents.length > 5) recents = recents.slice(0, 5);
        lsSetJSON('recentLayers', recents);
    }
    function getRecentLayers() { return lsGetJSON('recentLayers', []); }

    // (#22) Collapsed-group memory.
    function getCollapsedGroups() { return lsGetJSON('collapsedGroups', {}); }
    function toggleCollapsedGroup(name) {
        var g = getCollapsedGroups();
        g[name] = !g[name];
        lsSetJSON('collapsedGroups', g);
    }

    // (#4) Thumbnail size preference.
    function getThumbSize() { return lsGet('thumbSize', 'medium'); }
    function setThumbSize(s) { lsSet('thumbSize', s); }

    // (#5) Filter mode for layer panel.
    function getLayerFilter() { return lsGet('layerFilter', 'all'); }
    function setLayerFilter(f) { lsSet('layerFilter', f); }

    // ── Build the DOCKED layer-active toolbar strip ─────────────────
    // Inserts ABOVE the canvas/toolbar area (not on top of the canvas).
    function buildLayerDock() {
        if (document.getElementById('layerActiveDock')) return;

        var dock = document.createElement('div');
        dock.id = 'layerActiveDock';
        dock.style.cssText = [
            'display: none',
            'align-items: center',
            // 2026-04-18 painter-UI fix: allow the dock to wrap onto a second
            // row rather than overflowing horizontally and clipping the
            // rightmost controls (Pan / Fit were being cut off). Also
            // shrinks gap + padding to stay on one row in most cases.
            'flex-wrap: wrap',
            'gap: 6px',
            'row-gap: 4px',
            'padding: 5px 10px',
            'background: linear-gradient(180deg, rgba(255, 122, 24, 0.10) 0%, rgba(15, 20, 28, 0.95) 100%)',
            'border-bottom: 1px solid rgba(255, 122, 24, 0.35)',
            'box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3)',
            'font-family: "Segoe UI", "Inter", sans-serif',
            'flex-shrink: 0',
            'z-index: 50',
            'position: relative',
            // (#36) Smooth show/hide transition
            'transition: opacity 160ms ease, transform 160ms ease',
            'opacity: 0',
            'transform: translateY(-4px)'
        ].join(';');

        dock.innerHTML = '' +
            '<span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(255, 122, 24, 0.16); border: 1px solid rgba(255, 122, 24, 0.40); border-radius: 999px;">' +
                '<span style="font-size: 10px; color: #ff9a4a;">●</span>' +
                '<span style="color: #8899aa; font-size: 10px; text-transform: uppercase; letter-spacing: 0.10em; font-weight: 700;">Editing Layer</span>' +
                '<span id="layerDockName" style="color: #ffffff; font-size: 12px; font-weight: 700; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: text;" title="Double-click to rename">Layer</span>' +
            '</span>' +
            // (#37) Minimize button
            '<button id="layerDockMinimize" title="Minimize dock to compact pill" style="background: transparent; border: 1px solid rgba(148, 163, 184, 0.18); color: #8899aa; padding: 2px 8px; border-radius: 4px; font-size: 11px; cursor: pointer;">_</button>' +
            '<span style="width: 1px; height: 22px; background: rgba(148, 163, 184, 0.18);"></span>' +
            '<button id="layerDockMove" title="Move tool — drag selected layer on canvas (no Ctrl needed)" style="background: rgba(148, 163, 184, 0.06); border: 1px solid rgba(148, 163, 184, 0.20); color: #8899aa; padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 120ms;">↔ Move</button>' +
            '<button id="layerDockTransform" title="Transform Selection / Layer (Ctrl+T) — draw a rectangle or lasso first to transform only that region; otherwise transforms the whole layer." style="background: rgba(148, 163, 184, 0.06); border: 1px solid rgba(148, 163, 184, 0.20); color: #8899aa; padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 120ms;">⊞ Sel/Layer</button>' +
            '<button id="layerDockEffects" title="Layer Effects — Drop Shadow, Outer Glow, Stroke, Color Overlay, Bevel" style="background: rgba(148, 163, 184, 0.06); border: 1px solid rgba(148, 163, 184, 0.20); color: #8899aa; padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 120ms;">✨ Effects ▾</button>' +
            // (#28) FX intensity pill
            '<span id="layerDockFxPill" title="Global effect intensity multiplier — Shift-click to reset" style="font-size: 11px; color: #ff9a4a; background: rgba(255, 122, 24, 0.10); border: 1px solid rgba(255, 122, 24, 0.30); padding: 4px 8px; border-radius: 999px; cursor: pointer;">✨ FX × ' + getEffectIntensity().toFixed(2) + '</span>' +
            '<span style="width: 1px; height: 22px; background: rgba(148, 163, 184, 0.18);"></span>' +
            '<button id="layerDockLockZone" title="Restrict the currently-selected zone\'s finish to ONLY apply to this layer\'s pixels — fixes paint bleeding through other layers (Ctrl+L)" style="background: rgba(255, 215, 0, 0.10); border: 1px solid rgba(255, 215, 0, 0.40); color: #ffd700; padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 700; cursor: pointer; transition: all 120ms;">🔒 Lock Active Zone to This Layer</button>' +
            '<button id="layerDockPick" title="Pick Layer — click on canvas to select the layer at that pixel" style="background: rgba(20, 184, 166, 0.10); border: 1px solid rgba(20, 184, 166, 0.30); color: #5eead4; padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 120ms;">⊕ Pick Different Layer</button>' +
            // (#33)(#34) Pan / fit-to-view buttons
            '<button id="layerDockPan" title="Pan canvas to show this layer\'s bbox" style="background: rgba(148, 163, 184, 0.06); border: 1px solid rgba(148, 163, 184, 0.20); color: #8899aa; padding: 6px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">⌖ Pan</button>' +
            '<button id="layerDockFit" title="Fit canvas zoom to this layer\'s bbox" style="background: rgba(148, 163, 184, 0.06); border: 1px solid rgba(148, 163, 184, 0.20); color: #8899aa; padding: 6px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">⊕ Fit</button>' +
            // 2026-04-18: tip text now wraps onto its own row if the dock is
            // cramped, instead of stealing horizontal space and pushing the
            // Done button off-screen.
            '<span style="flex: 1; min-width: 0;"></span>' +
            '<span id="layerDockZoneStatus" style="font-size: 10px; color: #5a6b7d; white-space: normal;">Tool paints on this layer.</span>' +
            '<button id="layerDockClose" title="Deselect layer — return to normal mode (Esc)" style="background: transparent; border: 1px solid rgba(148, 163, 184, 0.18); color: #8899aa; padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; transition: all 120ms;">× Done</button>';

        // CRITICAL: insert INSIDE the center-panel as the FIRST child so it
        // appears as a horizontal strip ABOVE the canvas, not as a sibling
        // of the panels (which would make it a vertical sidebar in the row flex).
        var center = document.querySelector('.center-panel');
        if (center) {
            // Make sure center-panel is column flex so the dock stacks above the canvas
            if (!center.style.display) center.style.display = 'flex';
            if (!center.style.flexDirection) center.style.flexDirection = 'column';
            center.insertBefore(dock, center.firstChild);
        } else {
            // Fallback: append to body but use position:fixed so it doesn't affect layout
            dock.style.position = 'fixed';
            dock.style.top = '60px';
            dock.style.left = '50%';
            dock.style.transform = 'translateX(-50%)';
            document.body.appendChild(dock);
        }

        // ── Wire up buttons ──
        function setActiveBtn(activeId) {
            ['layerDockMove', 'layerDockTransform'].forEach(function(id) {
                var b = document.getElementById(id);
                if (!b) return;
                if (id === activeId) {
                    b.style.background = 'rgba(255, 122, 24, 0.22)';
                    b.style.borderColor = 'rgba(255, 122, 24, 0.55)';
                    b.style.color = '#ff9a4a';
                } else {
                    b.style.background = 'rgba(148, 163, 184, 0.06)';
                    b.style.borderColor = 'rgba(148, 163, 184, 0.20)';
                    b.style.color = '#8899aa';
                }
            });
        }
        // expose for later use
        dock._setActiveBtn = setActiveBtn;

        document.getElementById('layerDockMove').addEventListener('click', function() {
            if (typeof setCanvasMode === 'function') setCanvasMode('layer-move');
            setActiveBtn('layerDockMove');
            safeToast('Move tool active — drag the layer on the canvas');
        });

        document.getElementById('layerDockTransform').addEventListener('click', function() {
            // 2026-04-18 painter-trust fix: the Transform button should be
            // context-aware. If the painter has a rectangular (or lasso/wand)
            // selection AND a layer selected, they want to transform JUST
            // that sub-region (e.g. "rotate the TRES COMAS logo 180 degrees
            // within the Sponsors layer"). activateContextTransform already
            // knows this workflow — it lifts the selection into a new
            // layer and activates Free Transform on it. Pre-fix, the dock
            // button called activateLayerTransform directly, which ALWAYS
            // transformed the ENTIRE layer — the painter had to press
            // Ctrl+T (a discoverable-only shortcut) to get the lift-and-
            // transform flow. Now one click does the right thing either way.
            if (typeof activateContextTransform === 'function') {
                activateContextTransform();
            } else if (typeof activateLayerTransform === 'function') {
                activateLayerTransform();
            } else if (typeof activateFreeTransform === 'function') {
                activateFreeTransform('layer');
            } else {
                safeToast('Transform unavailable');
                return;
            }
            setActiveBtn('layerDockTransform');
            safeToast('Transform Selection / Layer — draw a rectangle first to transform just that part of the layer. Use 180° in the top strip for instant sponsor flips.');
        });

        // (#6) Effects button now opens a quick-preset menu before falling
        // through to the full editor.
        document.getElementById('layerDockEffects').addEventListener('click', function(ev) {
            var sel = currentSelectedLayerId();
            if (!sel) return;
            showEffectsMenu(ev.currentTarget, sel);
        });

        document.getElementById('layerDockPick').addEventListener('click', function() {
            if (typeof setCanvasMode === 'function') setCanvasMode('layer-pick');
            safeToast('Pick mode — click anywhere on the canvas to select the layer at that pixel');
        });

        document.getElementById('layerDockClose').addEventListener('click', function() {
            deselectActiveLayer();
        });

        // (#37) Minimize toggle
        document.getElementById('layerDockMinimize').addEventListener('click', function() {
            toggleDockMinimized();
        });

        // (#33) Pan to layer bbox
        document.getElementById('layerDockPan').addEventListener('click', function() {
            var sel = currentSelectedLayerId();
            if (sel) panToLayer(sel, false);
        });

        // (#34) Fit zoom to layer bbox
        document.getElementById('layerDockFit').addEventListener('click', function() {
            var sel = currentSelectedLayerId();
            if (sel) panToLayer(sel, true);
        });

        // (#35) Inline rename: double-click the dock layer name.
        document.getElementById('layerDockName').addEventListener('dblclick', function() {
            var sel = currentSelectedLayerId();
            if (!sel || typeof _psdLayers === 'undefined') return;
            var L = _psdLayers.find(function(x) { return x.id === sel; });
            if (!L) return;
            var nu = window.prompt('Rename layer:', L.name || '');
            if (nu == null) return;
            nu = String(nu).trim().slice(0, 80);
            if (nu) {
                L.name = nu;
                showLayerDock(nu);
                if (typeof renderLayerPanel === 'function') renderLayerPanel();
            }
        });

        // (#28) FX intensity pill — click cycles, shift-click resets.
        document.getElementById('layerDockFxPill').addEventListener('click', function(ev) {
            if (ev.shiftKey) { setEffectIntensity(1.0); safeToast('FX intensity reset to 1.00'); return; }
            var cur = getEffectIntensity();
            var next = cur >= 1.5 ? 0.25 : (cur + 0.25);
            setEffectIntensity(next);
            if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        });

        // 🔒 Lock Active Zone to This Layer — solves the "paint bleeds through other layers" problem
        document.getElementById('layerDockLockZone').addEventListener('click', function() {
            lockActiveZoneToSelectedLayer();
        });

        // Hover effects
        ['layerDockMove', 'layerDockTransform', 'layerDockEffects', 'layerDockPick', 'layerDockClose', 'layerDockPan', 'layerDockFit'].forEach(function(id) {
            var b = document.getElementById(id);
            if (!b) return;
            b.addEventListener('mouseenter', function() {
                if (b.style.color === 'rgb(255, 154, 74)') return; // active state — leave alone
                b.style.background = b.style.background.replace(/0\.\d+\)/, function(m) {
                    var v = parseFloat(m); return (Math.min(0.30, v + 0.10) + ')');
                });
                b.style.color = '#ffffff';
            });
            b.addEventListener('mouseleave', function() {
                // restored by setActiveBtn or default
                if (id === 'layerDockMove' || id === 'layerDockTransform') {
                    var canvasModeNow = (typeof canvasMode !== 'undefined') ? canvasMode : '';
                    if (id === 'layerDockMove' && canvasModeNow === 'layer-move') { setActiveBtn('layerDockMove'); return; }
                    b.style.background = 'rgba(148, 163, 184, 0.06)';
                    b.style.color = '#8899aa';
                } else if (id === 'layerDockPick') {
                    b.style.background = 'rgba(20, 184, 166, 0.10)';
                    b.style.color = '#5eead4';
                } else if (id === 'layerDockEffects') {
                    b.style.background = 'rgba(148, 163, 184, 0.06)';
                    b.style.color = '#8899aa';
                } else if (id === 'layerDockClose') {
                    b.style.background = 'transparent';
                    b.style.color = '#8899aa';
                } else if (id === 'layerDockPan' || id === 'layerDockFit') {
                    b.style.background = 'rgba(148, 163, 184, 0.06)';
                    b.style.color = '#8899aa';
                }
            });
        });

        // (#38) Restore minimized state if persisted.
        if (lsGet('dockMinimized', '0') === '1') applyDockMinimizedClass(true);
    }

    // ── Dock minimize support (#37, #38) ────────────────────────────
    var _dockMinimized = false;
    function applyDockMinimizedClass(min) {
        var dock = document.getElementById('layerActiveDock');
        if (!dock) return;
        _dockMinimized = !!min;
        var hideIds = ['layerDockMove', 'layerDockTransform', 'layerDockEffects', 'layerDockFxPill', 'layerDockLockZone', 'layerDockPick', 'layerDockPan', 'layerDockFit', 'layerDockZoneStatus'];
        hideIds.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.style.display = min ? 'none' : '';
        });
        var btn = document.getElementById('layerDockMinimize');
        if (btn) btn.textContent = min ? '□' : '_';
    }
    function toggleDockMinimized() {
        applyDockMinimizedClass(!_dockMinimized);
        lsSet('dockMinimized', _dockMinimized ? '1' : '0');
    }

    // ── Effects quick-preset menu (#6, #7, #26) ─────────────────────
    function showEffectsMenu(anchor, layerId) {
        // Remove any previous menu
        var old = document.getElementById('layerDockFxMenu');
        if (old) { old.remove(); }
        var menu = document.createElement('div');
        menu.id = 'layerDockFxMenu';
        var rect = anchor.getBoundingClientRect();
        menu.style.cssText = [
            'position: fixed',
            'top: ' + (rect.bottom + 4) + 'px',
            'left: ' + rect.left + 'px',
            'min-width: 200px',
            'background: #0f141c',
            'border: 1px solid rgba(255, 122, 24, 0.30)',
            'border-radius: 6px',
            'box-shadow: 0 6px 24px rgba(0,0,0,0.5)',
            'padding: 6px',
            'z-index: 9999',
            'font-family: "Segoe UI", "Inter", sans-serif',
            'font-size: 12px'
        ].join(';');

        function row(label, handler, color) {
            var d = document.createElement('div');
            d.textContent = label;
            d.style.cssText = 'padding: 6px 10px; color: ' + (color || '#cbd5e1') + '; border-radius: 4px; cursor: pointer;';
            d.addEventListener('mouseenter', function() { d.style.background = 'rgba(255,122,24,0.14)'; });
            d.addEventListener('mouseleave', function() { d.style.background = ''; });
            d.addEventListener('click', function() { menu.remove(); handler(); });
            menu.appendChild(d);
        }
        function sep(label) {
            var s = document.createElement('div');
            s.textContent = label;
            s.style.cssText = 'padding: 4px 10px; color: #5a6b7d; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em;';
            menu.appendChild(s);
        }

        sep('Quick Presets');
        Object.keys(QUICK_FX_PRESETS).forEach(function(name) {
            row(name, function() { applyQuickFx(layerId, name); });
        });

        sep('Clipboard');
        row('Copy effects', function() {
            if (copyLayerFx(layerId)) safeToast('Effects copied'); else safeToast('No effects on this layer', true);
        });
        row(_fxClipboard ? 'Paste effects' : 'Paste effects (empty)', function() {
            if (pasteLayerFx(layerId)) safeToast('Effects pasted'); else safeToast('Nothing to paste', true);
        }, _fxClipboard ? '#5eead4' : '#5a6b7d');
        row('Clear effects', function() {
            if (typeof _psdLayers === 'undefined') return;
            var L = _psdLayers.find(function(x) { return x.id === layerId; });
            if (L) { L.effects = {}; if (typeof recompositeFromLayers === 'function') recompositeFromLayers(); if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); safeToast('Effects cleared'); }
        }, '#ff9a4a');

        sep('Library');
        row('Save as preset…', function() {
            if (typeof _psdLayers === 'undefined') return;
            var L = _psdLayers.find(function(x) { return x.id === layerId; });
            if (!L || !L.effects) { safeToast('No effects on this layer', true); return; }
            var name = window.prompt('Preset name:', '');
            if (name) { saveEffectPreset(name, L.effects); safeToast('Saved preset "' + name + '"'); }
        });
        var presets = getEffectPresets();
        Object.keys(presets).forEach(function(pn) {
            row('Apply: ' + pn, function() {
                if (typeof _psdLayers === 'undefined') return;
                var L = _psdLayers.find(function(x) { return x.id === layerId; });
                if (!L) return;
                L.effects = JSON.parse(JSON.stringify(presets[pn]));
                if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                safeToast('Applied preset "' + pn + '"');
            });
        });

        sep('Editor');
        row('Open full Effects editor…', function() {
            if (typeof openLayerEffects === 'function') openLayerEffects(layerId);
        }, '#5eead4');

        // (#27) Export / import effects setup
        sep('Share');
        row('Export effects (clipboard)', function() {
            if (typeof _psdLayers === 'undefined') return;
            var L = _psdLayers.find(function(x) { return x.id === layerId; });
            if (!L || !L.effects) { safeToast('No effects on this layer', true); return; }
            try {
                var s = JSON.stringify(L.effects);
                if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(s);
                else { window.prompt('Copy this JSON:', s); }
                safeToast('Effects JSON copied');
            } catch (e) { safeToast('Export failed', true); }
        });
        row('Import effects (paste JSON)…', function() {
            var s = window.prompt('Paste effects JSON:', '');
            if (!s) return;
            try {
                var fx = JSON.parse(s);
                if (typeof _psdLayers === 'undefined') return;
                var L = _psdLayers.find(function(x) { return x.id === layerId; });
                if (L) { L.effects = fx; if (typeof recompositeFromLayers === 'function') recompositeFromLayers(); if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); safeToast('Effects imported'); }
            } catch (e) { safeToast('Invalid JSON', true); }
        });

        document.body.appendChild(menu);

        // dismiss on outside click
        setTimeout(function() {
            function dismiss(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('mousedown', dismiss, true);
                }
            }
            document.addEventListener('mousedown', dismiss, true);
        }, 0);
    }

    function showLayerDock(layerName) {
        var dock = document.getElementById('layerActiveDock');
        if (!dock) return;
        var nameEl = document.getElementById('layerDockName');
        if (nameEl) nameEl.textContent = layerName || 'Layer';
        dock.style.display = 'flex';
        // (#36) Animate in
        requestAnimationFrame(function() {
            dock.style.opacity = '1';
            dock.style.transform = 'translateY(0)';
        });
    }

    function hideLayerDock() {
        var dock = document.getElementById('layerActiveDock');
        if (!dock) return;
        dock.style.opacity = '0';
        dock.style.transform = 'translateY(-4px)';
        // Hide after fade
        setTimeout(function() {
            // Only hide if still faded (user might have re-selected during animation)
            if (dock.style.opacity === '0') dock.style.display = 'none';
        }, 180);
    }

    function currentSelectedLayerId() {
        return (typeof window._selectedLayerId !== 'undefined') ? window._selectedLayerId :
               (typeof _selectedLayerId !== 'undefined' ? _selectedLayerId : null);
    }

    function deselectActiveLayer() {
        if (typeof window !== 'undefined') window._selectedLayerId = null;
        try { _selectedLayerId = null; } catch (e) {}
        hideLayerDock();
        var dock = document.getElementById('layerActiveDock');
        if (dock && dock._setActiveBtn) dock._setActiveBtn(null);
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
        if (typeof drawLayerBounds === 'function') drawLayerBounds();
    }

    // (#29) Lock active zone to selected layer (extracted so Ctrl+L can call it).
    function lockActiveZoneToSelectedLayer() {
        var sel = currentSelectedLayerId();
        if (!sel) { safeToast('No layer selected', true); return; }
        if (typeof selectedZoneIndex === 'undefined' || selectedZoneIndex < 0 ||
            typeof zones === 'undefined' || selectedZoneIndex >= zones.length) {
            safeToast('Select a zone first (click a zone in the left panel)', true);
            return;
        }
        if (typeof setZoneSourceLayer === 'function') {
            setZoneSourceLayer(selectedZoneIndex, sel);
            var layer = (typeof _psdLayers !== 'undefined') ? _psdLayers.find(function(l) { return l.id === sel; }) : null;
            var statusEl = document.getElementById('layerDockZoneStatus');
            if (statusEl && layer) {
                // FIVE-HOUR SHIFT Win H9 (security): pre-fix this interpolated
                // user-controlled zone.name + layer.name raw into innerHTML.
                // A crafted PSD layer name or zone rename containing
                // `<img src=x onerror=alert(1)>` would execute on every
                // Ctrl+L lock action. Same XSS class as marathon #68/#69
                // and this shift's H8.
                var _esc = function (s) {
                    var div = document.createElement('div');
                    div.textContent = String(s == null ? '' : s);
                    return div.innerHTML;
                };
                var _zname = _esc(zones[selectedZoneIndex].name || ('Zone ' + (selectedZoneIndex + 1)));
                var _lname = _esc(layer.name || '');
                statusEl.innerHTML = '🔒 Zone <strong style="color:#ffd700;">' + _zname + '</strong> now restricted to layer <strong style="color:#ffd700;">' + _lname + '</strong>';
            }
        }
    }

    // ── Watch for layer selection changes ───────────────────────────
    var _lastSeenLayerId = undefined;
    var _lastSeenZoneRestriction = undefined;
    // (#32) Layer-switch debouncer: rapid switches are coalesced.
    var _layerSwitchTimer = null;
    function watchLayerSelection() {
        var sel = currentSelectedLayerId();
        if (sel !== _lastSeenLayerId) {
            _lastSeenLayerId = sel;
            // (#1) Persist selection for restore-on-reload.
            if (sel) lsSet('lastLayerId', String(sel));
            else { try { localStorage.removeItem(LS_PREFIX + 'lastLayerId'); } catch (e) {} }
            // (#13) Track recents.
            if (sel) pushRecentLayer(sel);

            // (#32) Debounce dock UI updates so rapid arrow-key navigation
            // doesn't churn the DOM.
            if (_layerSwitchTimer) clearTimeout(_layerSwitchTimer);
            _layerSwitchTimer = setTimeout(function() {
                _layerSwitchTimer = null;
                if (sel && typeof _psdLayers !== 'undefined') {
                    var layer = _psdLayers.find(function(l) { return l.id === sel; });
                    if (layer) {
                        showLayerDock(deriveLayerName(layer));
                        updateStatusBarLayer(deriveLayerName(layer));
                    } else {
                        hideLayerDock();
                        updateStatusBarLayer(null);
                    }
                } else {
                    hideLayerDock();
                    updateStatusBarLayer(null);
                }
            }, 60);
        }

        // Live-update the dock's zone-restriction status text
        var statusEl = document.getElementById('layerDockZoneStatus');
        if (statusEl && typeof zones !== 'undefined' && typeof selectedZoneIndex !== 'undefined') {
            var z = zones[selectedZoneIndex];
            var zoneRestrictKey = (selectedZoneIndex + ':' + (z && z.sourceLayer || ''));
            if (zoneRestrictKey !== _lastSeenZoneRestriction) {
                _lastSeenZoneRestriction = zoneRestrictKey;
                if (z && z.sourceLayer && typeof _psdLayers !== 'undefined') {
                    var srcLayer = _psdLayers.find(function(l) { return l.id === z.sourceLayer; });
                    var srcName = srcLayer ? srcLayer.name : z.sourceLayer;
                    statusEl.innerHTML = '🔒 Zone <strong style="color:#ffd700;">' + (z.name || ('Zone ' + (selectedZoneIndex + 1))) + '</strong> restricted to layer <strong style="color:#ffd700;">' + srcName + '</strong>';
                } else if (z) {
                    statusEl.innerHTML = '⚠ Zone <strong style="color:#ff9a4a;">' + (z.name || ('Zone ' + (selectedZoneIndex + 1))) + '</strong> applies to ALL pixels — click 🔒 above to restrict to this layer';
                } else {
                    statusEl.innerHTML = 'Tip: any tool on the left toolbar paints on this layer.';
                }
            }
        }
    }

    function updateStatusBarLayer(name) {
        var el = document.getElementById('statusActiveLayer');
        if (!el) return;
        if (name) {
            // (#21) include count badge inside status pill: "Layer · 3/12"
            var visible = 0, total = 0;
            try {
                if (typeof _psdLayers !== 'undefined' && _psdLayers && _psdLayers.length) {
                    total = _psdLayers.length;
                    for (var i = 0; i < _psdLayers.length; i++) if (_psdLayers[i].visible) visible++;
                }
            } catch (e) {}
            var badge = total > 0 ? (' · ' + visible + '/' + total) : '';
            el.textContent = '● Layer: ' + name + badge;
            el.style.display = '';
        } else {
            el.textContent = '';
            el.style.display = 'none';
        }
    }

    function ensureStatusBarSlot() {
        if (document.getElementById('statusActiveLayer')) return;
        var statusBar = document.querySelector('.status-bar') ||
                        document.getElementById('statusBar') ||
                        document.querySelector('.bottom-bar');
        if (!statusBar) return;
        var slot = document.createElement('span');
        slot.id = 'statusActiveLayer';
        slot.style.cssText = 'margin-right: 12px; padding: 2px 10px; border-radius: 999px; background: rgba(255, 122, 24, 0.14); border: 1px solid rgba(255, 122, 24, 0.40); color: #ff9a4a; font-size: 11px; font-weight: 700; display: none; cursor: pointer;';
        slot.title = 'Click to focus the active layer in the panel; double-click to deselect';
        // (#39) Click pill = focus layer in panel
        slot.addEventListener('click', function() {
            var sel = currentSelectedLayerId();
            if (!sel) return;
            focusLayerInPanel(sel);
        });
        slot.addEventListener('dblclick', function() {
            deselectActiveLayer();
        });
        statusBar.insertBefore(slot, statusBar.firstChild);
    }

    function focusLayerInPanel(layerId) {
        // Try common selectors used by the right panel layer rows.
        var sels = [
            '[data-layer-id="' + layerId + '"]',
            '#layer-' + layerId,
            '.layer-row[data-id="' + layerId + '"]'
        ];
        for (var i = 0; i < sels.length; i++) {
            var el = document.querySelector(sels[i]);
            if (el && el.scrollIntoView) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.style.boxShadow = '0 0 0 2px rgba(255, 122, 24, 0.7)';
                setTimeout(function() { el.style.boxShadow = ''; }, 900);
                return true;
            }
        }
        return false;
    }

    // ── Layer-pick mode ─────────────────────────────────────────────
    function findTopmostLayerAt(x, y) {
        if (typeof _psdLayers === 'undefined' || _psdLayers.length === 0) return null;
        for (var i = _psdLayers.length - 1; i >= 0; i--) {
            var L = _psdLayers[i];
            if (!L.visible || !L.img) continue;
            var bbox = L.bbox;
            if (!bbox) continue;
            var bx = bbox[0], by = bbox[1];
            var bw = (bbox[2] - bbox[0]) || L.img.width || L.img.naturalWidth || 0;
            var bh = (bbox[3] - bbox[1]) || L.img.height || L.img.naturalHeight || 0;
            if (x >= bx && x < bx + bw && y >= by && y < by + bh) {
                try {
                    var c = document.createElement('canvas');
                    c.width = bw; c.height = bh;
                    var cx = c.getContext('2d');
                    cx.drawImage(L.img, 0, 0);
                    // PRESERVED critical fix: alpha-based mask logic, threshold > 16.
                    var px = cx.getImageData(x - bx, y - by, 1, 1).data;
                    if (px[3] > 16) return L;
                } catch (e) {
                    return L;
                }
            }
        }
        return null;
    }

    function installCanvasHandlers() {
        var canvas = document.getElementById('paintCanvas');
        if (!canvas || canvas._layerFlowInstalled) return;
        canvas._layerFlowInstalled = true;

        // Layer-pick: click to select
        canvas.addEventListener('click', function(e) {
            if (typeof canvasMode === 'undefined' || canvasMode !== 'layer-pick') return;
            if (typeof getPixelAt !== 'function') return;
            var pos = getPixelAt(e);
            if (!pos) return;
            var L = findTopmostLayerAt(pos.x, pos.y);
            if (L) {
                if (typeof selectPSDLayer === 'function') selectPSDLayer(L.id);
                else { try { _selectedLayerId = L.id; } catch (e2) {} }
                safeToast('Selected layer: ' + (L.name || 'Layer'));
                if (typeof setCanvasMode === 'function') setCanvasMode('eyedropper');
                if (typeof renderLayerPanel === 'function') renderLayerPanel();
                if (typeof drawLayerBounds === 'function') drawLayerBounds();
            } else {
                safeToast('No layer at this point');
            }
        });

        // Layer-move: drag to move selected layer
        var dragging = false;
        canvas.addEventListener('mousedown', function(e) {
            if (typeof canvasMode === 'undefined' || canvasMode !== 'layer-move') return;
            if (e.button !== 0) return;
            var sel = (typeof _selectedLayerId !== 'undefined') ? _selectedLayerId : null;
            if (!sel || typeof _psdLayers === 'undefined') return;
            var layer = _psdLayers.find(function(l) { return l.id === sel; });
            if (!layer) return;
            if (typeof getPixelAt !== 'function') return;
            var pos = getPixelAt(e);
            if (!pos) return;
            dragging = true;
            canvas.style.cursor = 'grabbing';
            if (typeof startLayerDrag === 'function') startLayerDrag(layer, pos.x, pos.y);
            e.preventDefault();
            e.stopPropagation();
        }, true);

        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            if (typeof canvasMode === 'undefined' || canvasMode !== 'layer-move') { dragging = false; return; }
            var c = document.getElementById('paintCanvas');
            if (!c) return;
            var rect = c.getBoundingClientRect();
            var sx = c.width / rect.width, sy = c.height / rect.height;
            var lx = Math.floor((e.clientX - rect.left) * sx);
            var ly = Math.floor((e.clientY - rect.top) * sy);
            if (typeof updateLayerDrag === 'function') updateLayerDrag(lx, ly);
        });

        document.addEventListener('mouseup', function() {
            if (!dragging) return;
            dragging = false;
            var c = document.getElementById('paintCanvas');
            if (c) c.style.cursor = (typeof canvasMode !== 'undefined' && canvasMode === 'layer-move') ? 'grab' : '';
            if (typeof endLayerDrag === 'function') endLayerDrag();
            // Trigger preview render after layer move so the rendered car updates
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
        });
    }

    // ── Trigger preview render after ANY layer modification ────────
    // Hook into _commitLayerPaint and recompositeFromLayers so that
    // erasing/painting/effects on layers immediately update the rendered car.
    function installLayerCommitHook() {
        if (typeof window._commitLayerPaint === 'function' && !window._commitLayerPaint._spbLayerFlowHooked) {
            var orig = window._commitLayerPaint;
            window._commitLayerPaint = function() {
                var r = orig.apply(this, arguments);
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                return r;
            };
            window._commitLayerPaint._spbLayerFlowHooked = true;
        }
    }

    // ── Cursor management for layer modes ───────────────────────────
    function watchCanvasModeForCursor() {
        var canvas = document.getElementById('paintCanvas');
        if (!canvas) return;
        if (typeof canvasMode !== 'undefined') {
            if (canvasMode === 'layer-move') {
                if (canvas.style.cursor !== 'grabbing') canvas.style.cursor = 'grab';
            } else if (canvasMode === 'layer-pick') {
                canvas.style.cursor = 'crosshair';
            }
        }
    }

    // ── Stuck-preview watchdog ──────────────────────────────────────
    // (#31) Improved watchdog: escalating recovery, distinguishes "rendering"
    // from "queued", offers a one-click forceRefresh hook if available.
    var _stuckWatchdogStart = 0;
    var _stuckWatchdogLastStatus = '';
    var _stuckEscalationStage = 0; // 0=none, 1=warned, 2=offered-refresh, 3=auto-recovered
    function watchStuckPreview() {
        var statusEl = document.getElementById('previewStatus');
        var status = statusEl ? (statusEl.textContent || '') : '';
        var isRendering = /render|pending|busy|queued/i.test(status);

        if (isRendering && status === _stuckWatchdogLastStatus) {
            if (_stuckWatchdogStart === 0) { _stuckWatchdogStart = Date.now(); _stuckEscalationStage = 0; }
            var elapsed = Date.now() - _stuckWatchdogStart;

            // Stage 1: 12s — soft warn (color shift only)
            if (elapsed > 12000 && _stuckEscalationStage < 1) {
                _stuckEscalationStage = 1;
                if (statusEl) {
                    statusEl.style.color = '#ffb86b';
                    statusEl.title = 'Render is taking longer than usual…';
                }
            }
            // Stage 2: 22s — clickable recovery hint + toast
            if (elapsed > 22000 && _stuckEscalationStage < 2) {
                _stuckEscalationStage = 2;
                if (statusEl && !statusEl.dataset.stuckNoticed) {
                    statusEl.dataset.stuckNoticed = '1';
                    statusEl.style.cursor = 'pointer';
                    statusEl.style.color = '#ff6666';
                    statusEl.textContent = 'Stuck — click to refresh';
                    if (!statusEl._stuckClickInstalled) {
                        statusEl._stuckClickInstalled = true;
                        statusEl.addEventListener('click', function() {
                            if (typeof forceRenderPreview === 'function') forceRenderPreview();
                            else if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                        });
                    }
                    safeToast('⚠ Preview seems stuck. Click the status text or press F5 to recover.', true);
                }
            }
            // Stage 3: 45s — auto-attempt recovery once
            if (elapsed > 45000 && _stuckEscalationStage < 3) {
                _stuckEscalationStage = 3;
                if (typeof forceRenderPreview === 'function') {
                    safeToast('Auto-recovery: re-issuing render request…', true);
                    try { forceRenderPreview(); } catch (e) {}
                } else if (typeof triggerPreviewRender === 'function') {
                    try { triggerPreviewRender(); } catch (e) {}
                }
            }
        } else {
            // State changed or not rendering — reset watchdog
            _stuckWatchdogStart = 0;
            _stuckEscalationStage = 0;
            if (statusEl && statusEl.dataset.stuckNoticed) {
                delete statusEl.dataset.stuckNoticed;
                statusEl.style.color = '';
                statusEl.title = '';
            }
        }
        _stuckWatchdogLastStatus = status;
    }

    // ── Layer panel enhancements (#2-#5, #14-#23) ───────────────────
    // The layer panel itself lives in another module; we attach behaviours
    // by delegated event listeners on the document so we don't have to
    // touch panel internals.

    // (#2) Hover preview — when hovering a layer row, briefly highlight bbox
    // (#40) ...with a 300ms hover delay so just brushing past doesn't trigger.
    var _hoverDelayTimer = null;
    var _hoverActiveLayerId = null;
    function installLayerPanelHoverPreview() {
        document.addEventListener('mouseover', function(e) {
            var row = e.target.closest && e.target.closest('[data-layer-id]');
            if (!row) return;
            var id = row.getAttribute('data-layer-id');
            if (!id || id === _hoverActiveLayerId) return;
            if (_hoverDelayTimer) clearTimeout(_hoverDelayTimer);
            _hoverDelayTimer = setTimeout(function() {
                _hoverActiveLayerId = id;
                drawLayerHoverBbox(id);
            }, 300);
        });
        document.addEventListener('mouseout', function(e) {
            var row = e.target.closest && e.target.closest('[data-layer-id]');
            if (!row) return;
            if (_hoverDelayTimer) { clearTimeout(_hoverDelayTimer); _hoverDelayTimer = null; }
            if (_hoverActiveLayerId) {
                _hoverActiveLayerId = null;
                clearLayerHoverBbox();
            }
        });
    }
    function drawLayerHoverBbox(layerId) {
        var canvas = document.getElementById('paintCanvas');
        if (!canvas || typeof _psdLayers === 'undefined') return;
        var L = _psdLayers.find(function(x) { return String(x.id) === String(layerId); });
        if (!L || !L.bbox) return;
        // Draw a transient overlay div positioned over the canvas bbox.
        var overlay = document.getElementById('layerHoverOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'layerHoverOverlay';
            overlay.style.cssText = 'position: absolute; pointer-events: none; border: 2px dashed #ffb86b; background: rgba(255, 184, 107, 0.10); z-index: 30; transition: opacity 120ms;';
            // Position relative to the canvas's offsetParent.
            (canvas.offsetParent || document.body).appendChild(overlay);
        }
        var rect = canvas.getBoundingClientRect();
        var pRect = (canvas.offsetParent || document.body).getBoundingClientRect();
        var sx = rect.width / canvas.width, sy = rect.height / canvas.height;
        var bx = L.bbox[0] * sx + (rect.left - pRect.left);
        var by = L.bbox[1] * sy + (rect.top - pRect.top);
        var bw = (L.bbox[2] - L.bbox[0]) * sx;
        var bh = (L.bbox[3] - L.bbox[1]) * sy;
        overlay.style.left = bx + 'px';
        overlay.style.top = by + 'px';
        overlay.style.width = bw + 'px';
        overlay.style.height = bh + 'px';
        overlay.style.opacity = '1';
        overlay.style.display = '';
    }
    function clearLayerHoverBbox() {
        var overlay = document.getElementById('layerHoverOverlay');
        if (overlay) { overlay.style.opacity = '0'; setTimeout(function() { if (overlay.style.opacity === '0') overlay.style.display = 'none'; }, 150); }
    }

    // (#14) Visibility shortcuts: Alt+click eye = solo, Shift+click eye = range toggle
    function installLayerVisibilityShortcuts() {
        document.addEventListener('click', function(e) {
            var eye = e.target.closest && e.target.closest('[data-layer-eye], .layer-eye, .layer-visibility');
            if (!eye) return;
            var row = eye.closest('[data-layer-id]');
            if (!row || typeof _psdLayers === 'undefined') return;
            var id = row.getAttribute('data-layer-id');
            // Alt = solo
            if (e.altKey) {
                e.preventDefault(); e.stopPropagation();
                _psdLayers.forEach(function(L) { L.visible = (String(L.id) === String(id)); });
                if (typeof renderLayerPanel === 'function') renderLayerPanel();
                if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                safeToast('Solo: only this layer is visible');
            }
            // Shift = range toggle (from last clicked to this)
            else if (e.shiftKey && _lastEyeClickedId != null) {
                e.preventDefault(); e.stopPropagation();
                var ids = _psdLayers.map(function(L) { return String(L.id); });
                var a = ids.indexOf(String(_lastEyeClickedId));
                var b = ids.indexOf(String(id));
                if (a >= 0 && b >= 0) {
                    var lo = Math.min(a, b), hi = Math.max(a, b);
                    var target = !_psdLayers[b].visible;
                    for (var i = lo; i <= hi; i++) _psdLayers[i].visible = target;
                    if (typeof renderLayerPanel === 'function') renderLayerPanel();
                    if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                }
            }
            _lastEyeClickedId = id;
        }, true);
    }
    var _lastEyeClickedId = null;

    // (#23) Hide-others helper exposed via spbLayerFlow.
    function hideOthers(layerId) {
        if (typeof _psdLayers === 'undefined') return;
        _psdLayers.forEach(function(L) { L.visible = (String(L.id) === String(layerId)); });
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }
    function showAll() {
        if (typeof _psdLayers === 'undefined') return;
        _psdLayers.forEach(function(L) { L.visible = true; });
        if (typeof renderLayerPanel === 'function') renderLayerPanel();
        if (typeof recompositeFromLayers === 'function') recompositeFromLayers();
        if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
    }

    // (#15) Right-click context menu on layer thumbnails.
    function installLayerContextMenu() {
        document.addEventListener('contextmenu', function(e) {
            var row = e.target.closest && e.target.closest('[data-layer-id]');
            if (!row) return;
            var id = row.getAttribute('data-layer-id');
            if (!id) return;
            e.preventDefault();
            showLayerContextMenu(e.clientX, e.clientY, id);
        });
    }
    function showLayerContextMenu(x, y, layerId) {
        var old = document.getElementById('layerCtxMenu');
        if (old) old.remove();
        var menu = document.createElement('div');
        menu.id = 'layerCtxMenu';
        menu.style.cssText = 'position: fixed; left: ' + x + 'px; top: ' + y + 'px; min-width: 200px; background: #0f141c; border: 1px solid rgba(255, 122, 24, 0.30); border-radius: 6px; box-shadow: 0 6px 24px rgba(0,0,0,0.5); padding: 6px; z-index: 9999; font-family: "Segoe UI", "Inter", sans-serif; font-size: 12px;';
        function row(label, handler, color) {
            var d = document.createElement('div');
            d.textContent = label;
            d.style.cssText = 'padding: 6px 10px; color: ' + (color || '#cbd5e1') + '; border-radius: 4px; cursor: pointer;';
            d.addEventListener('mouseenter', function() { d.style.background = 'rgba(255,122,24,0.14)'; });
            d.addEventListener('mouseleave', function() { d.style.background = ''; });
            d.addEventListener('click', function() { menu.remove(); handler(); });
            menu.appendChild(d);
        }
        row('Select', function() { if (typeof selectPSDLayer === 'function') selectPSDLayer(layerId); });
        row('Rename…', function() {
            if (typeof _psdLayers === 'undefined') return;
            var L = _psdLayers.find(function(x) { return String(x.id) === String(layerId); });
            if (!L) return;
            var nu = window.prompt('Rename layer:', L.name || '');
            if (nu) { L.name = nu.trim().slice(0, 80); if (typeof renderLayerPanel === 'function') renderLayerPanel(); }
        });
        row('Solo (hide others)', function() { hideOthers(layerId); });
        row('Pin to top', function() {
            var meta = getLayerMeta(layerId);
            setLayerMeta(layerId, { pinned: !meta.pinned });
            if (typeof renderLayerPanel === 'function') renderLayerPanel();
        });
        row('Add comment…', function() {
            var c = window.prompt('Comment:', getLayerMeta(layerId).comment || '');
            if (c != null) setLayerMeta(layerId, { comment: c });
        });
        row('Color tag ▸', function() {
            var c = window.prompt('Color tag (red, orange, yellow, green, blue, purple, gray, none):', getLayerMeta(layerId).color || 'none');
            if (c != null) setLayerMeta(layerId, { color: c.trim().toLowerCase() });
        });
        row('Copy effects', function() { if (copyLayerFx(layerId)) safeToast('Effects copied'); });
        row('Paste effects', function() { if (pasteLayerFx(layerId)) safeToast('Effects pasted'); });
        row('Pan to layer', function() { panToLayer(layerId, false); });
        row('Fit to layer', function() { panToLayer(layerId, true); });
        row('Lock active zone to this layer', function() {
            try { _selectedLayerId = layerId; } catch (e) {}
            window._selectedLayerId = layerId;
            lockActiveZoneToSelectedLayer();
        }, '#ffd700');
        document.body.appendChild(menu);
        setTimeout(function() {
            function dismiss(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('mousedown', dismiss, true);
                }
            }
            document.addEventListener('mousedown', dismiss, true);
        }, 0);
    }

    // (#33)(#34) Pan / fit-to-view helpers.
    function panToLayer(layerId, fit) {
        if (typeof _psdLayers === 'undefined') return;
        var L = _psdLayers.find(function(x) { return String(x.id) === String(layerId); });
        if (!L || !L.bbox) return;
        var cx = (L.bbox[0] + L.bbox[2]) / 2;
        var cy = (L.bbox[1] + L.bbox[3]) / 2;
        // Best-effort hooks into known canvas APIs.
        if (fit && typeof zoomToBounds === 'function') { zoomToBounds(L.bbox); return; }
        if (fit && typeof fitCanvasToBbox === 'function') { fitCanvasToBbox(L.bbox); return; }
        if (typeof panCanvasTo === 'function') { panCanvasTo(cx, cy); return; }
        if (typeof centerCanvasOn === 'function') { centerCanvasOn(cx, cy); return; }
        // Fallback: scroll the canvas's parent into view, then mention coords.
        var canvas = document.getElementById('paintCanvas');
        if (canvas && canvas.scrollIntoView) canvas.scrollIntoView({ behavior: 'smooth', block: 'center' });
        safeToast((fit ? 'Fit to' : 'Pan to') + ' bbox ' + Math.round(cx) + ', ' + Math.round(cy));
    }

    // ── Keyboard handling (#3, #14 deps, #18, #29, #43) ─────────────
    // SESSION ROUTER: bail on defaultPrevented so transform/master listeners win first.
    function installKeyboardHandlers() {
        document.addEventListener('keydown', function(e) {
            if (e.defaultPrevented) return;
            // Don't interfere with text inputs
            var t = e.target;
            var isInput = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);

            // (#29) Ctrl+L = Lock active zone to selected layer
            if ((e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L') && !isInput) {
                e.preventDefault();
                lockActiveZoneToSelectedLayer();
                return;
            }

            // (#18) Ctrl+F when focus is in/near layer panel = focus filter input
            if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F') && !isInput) {
                var panel = document.querySelector('#layerPanel, .layer-panel, .layers-panel');
                if (panel && document.activeElement && (panel === document.activeElement || panel.contains(document.activeElement))) {
                    e.preventDefault();
                    var inp = ensureLayerFindBox(panel);
                    if (inp) inp.focus();
                    return;
                }
            }

            // (#3) Up/Down arrow = navigate layers when focus is on layer panel
            if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && !isInput) {
                var panel2 = document.querySelector('#layerPanel, .layer-panel, .layers-panel');
                if (panel2 && document.activeElement && (panel2 === document.activeElement || panel2.contains(document.activeElement))) {
                    if (typeof _psdLayers === 'undefined' || !_psdLayers.length) return;
                    var sel = currentSelectedLayerId();
                    var idx = _psdLayers.findIndex(function(L) { return String(L.id) === String(sel); });
                    if (idx < 0) idx = 0;
                    idx += (e.key === 'ArrowUp' ? -1 : 1);
                    idx = Math.max(0, Math.min(_psdLayers.length - 1, idx));
                    var nextId = _psdLayers[idx].id;
                    if (typeof selectPSDLayer === 'function') selectPSDLayer(nextId);
                    else { try { _selectedLayerId = nextId; } catch (e2) {} window._selectedLayerId = nextId; }
                    if (typeof renderLayerPanel === 'function') renderLayerPanel();
                    e.preventDefault();
                }
            }

            // (#43) Esc deselects layer
            if (e.key === 'Escape' && !isInput) {
                if (currentSelectedLayerId()) {
                    deselectActiveLayer();
                }
            }
        });
    }

    // (#18) Layer find box — injected lazily into the layer panel header.
    function ensureLayerFindBox(panel) {
        if (!panel) panel = document.querySelector('#layerPanel, .layer-panel, .layers-panel');
        if (!panel) return null;
        var inp = panel.querySelector('#layerFindBox');
        if (inp) return inp;
        var wrap = document.createElement('div');
        wrap.style.cssText = 'padding: 4px 6px; display: flex; gap: 4px; align-items: center;';
        inp = document.createElement('input');
        inp.id = 'layerFindBox';
        inp.placeholder = 'Find layer…';
        inp.style.cssText = 'flex: 1; background: #0f141c; border: 1px solid rgba(148,163,184,0.20); color: #cbd5e1; padding: 4px 8px; border-radius: 4px; font-size: 12px;';
        inp.addEventListener('input', function() { applyLayerFindFilter(inp.value); });
        wrap.appendChild(inp);
        panel.insertBefore(wrap, panel.firstChild);
        return inp;
    }
    function applyLayerFindFilter(query) {
        var q = (query || '').toLowerCase().trim();
        var rows = document.querySelectorAll('[data-layer-id]');
        rows.forEach(function(r) {
            var name = (r.textContent || '').toLowerCase();
            r.style.display = (!q || name.indexOf(q) >= 0) ? '' : 'none';
        });
    }

    // ── Restore last-selected layer on boot (#1) ────────────────────
    function restoreLastSelectedLayer() {
        var last = lsGet('lastLayerId', null);
        if (!last) return;
        // Wait until layers are populated, retry up to ~6s.
        var tries = 0;
        var iv = setInterval(function() {
            tries++;
            if (typeof _psdLayers !== 'undefined' && _psdLayers && _psdLayers.length) {
                var L = _psdLayers.find(function(x) { return String(x.id) === String(last); });
                if (L) {
                    if (typeof selectPSDLayer === 'function') selectPSDLayer(L.id);
                    else { try { _selectedLayerId = L.id; } catch (e) {} window._selectedLayerId = L.id; }
                    if (typeof renderLayerPanel === 'function') renderLayerPanel();
                }
                clearInterval(iv);
            } else if (tries > 24) {
                clearInterval(iv);
            }
        }, 250);
    }

    // ── Effect performance hint (#25) ───────────────────────────────
    function checkEffectPerformance() {
        if (typeof _psdLayers === 'undefined') return;
        for (var i = 0; i < _psdLayers.length; i++) {
            var L = _psdLayers[i];
            if (!L.effects) continue;
            var enabled = 0;
            Object.keys(L.effects).forEach(function(k) { if (L.effects[k] && L.effects[k].enabled) enabled++; });
            if (enabled >= 4 && !L._perfWarned) {
                L._perfWarned = true;
                safeToast('Performance hint: layer "' + (L.name || 'Layer') + '" has ' + enabled + ' active effects — render may slow down.', true);
            } else if (enabled < 4 && L._perfWarned) {
                L._perfWarned = false;
            }
        }
    }

    // (#19) Layer reorder animation — add CSS transition on layer rows.
    function installReorderAnimationCSS() {
        if (document.getElementById('spbLayerFlowCSS')) return;
        var style = document.createElement('style');
        style.id = 'spbLayerFlowCSS';
        style.textContent = [
            '[data-layer-id] { transition: transform 180ms ease, background 120ms ease, box-shadow 120ms ease; }',
            '[data-layer-id][data-pinned="1"] { box-shadow: inset 3px 0 0 #ffd700; }',
            '[data-layer-id][data-color-tag="red"] { box-shadow: inset 3px 0 0 #ff5a5a; }',
            '[data-layer-id][data-color-tag="orange"] { box-shadow: inset 3px 0 0 #ff9a4a; }',
            '[data-layer-id][data-color-tag="yellow"] { box-shadow: inset 3px 0 0 #ffd700; }',
            '[data-layer-id][data-color-tag="green"] { box-shadow: inset 3px 0 0 #5eead4; }',
            '[data-layer-id][data-color-tag="blue"] { box-shadow: inset 3px 0 0 #60a5fa; }',
            '[data-layer-id][data-color-tag="purple"] { box-shadow: inset 3px 0 0 #c084fc; }',
            '[data-layer-id][data-color-tag="gray"] { box-shadow: inset 3px 0 0 #94a3b8; }',
            '[data-layer-id][data-locked-zone="1"]::after { content: "🔒"; position: absolute; right: 6px; top: 4px; font-size: 10px; opacity: 0.8; }',
            '[data-layer-id][data-has-effects="1"]::before { content: "✨"; position: absolute; right: 22px; top: 4px; font-size: 10px; opacity: 0.7; }',
            '[data-layer-id] { position: relative; }',
            '#layerActiveDock.minimized > *:not(#layerDockMinimize):not(#layerDockName) { display: none; }'
        ].join('\n');
        document.head.appendChild(style);
    }

    // (#30) Apply layer-panel data attributes (locked zone, effects, color, pin)
    function decorateLayerRows() {
        var rows = document.querySelectorAll('[data-layer-id]');
        if (!rows.length) return;
        var lockedLayerIds = {};
        if (typeof zones !== 'undefined') {
            for (var i = 0; i < zones.length; i++) {
                if (zones[i] && zones[i].sourceLayer) lockedLayerIds[String(zones[i].sourceLayer)] = true;
            }
        }
        rows.forEach(function(r) {
            var id = r.getAttribute('data-layer-id');
            var meta = getLayerMeta(id);
            if (meta.color && meta.color !== 'none') r.setAttribute('data-color-tag', meta.color);
            else r.removeAttribute('data-color-tag');
            if (meta.pinned) r.setAttribute('data-pinned', '1'); else r.removeAttribute('data-pinned');
            if (lockedLayerIds[String(id)]) r.setAttribute('data-locked-zone', '1'); else r.removeAttribute('data-locked-zone');
            if (typeof _psdLayers !== 'undefined') {
                var L = _psdLayers.find(function(x) { return String(x.id) === String(id); });
                if (L && L.effects && Object.keys(L.effects).some(function(k) { return L.effects[k] && L.effects[k].enabled; })) {
                    r.setAttribute('data-has-effects', '1');
                } else {
                    r.removeAttribute('data-has-effects');
                }
                if (meta.comment) r.title = (r.title || '') + '\n💬 ' + meta.comment;
            }
        });
    }

    // ── Boot ────────────────────────────────────────────────────────
    ready(function() {
        setTimeout(function() {
            installReorderAnimationCSS();
            buildLayerDock();
            ensureStatusBarSlot();
            installCanvasHandlers();
            installLayerCommitHook();
            installLayerPanelHoverPreview();
            installLayerVisibilityShortcuts();
            installLayerContextMenu();
            installKeyboardHandlers();
            restoreLastSelectedLayer();

            setInterval(function() {
                watchLayerSelection();
                watchCanvasModeForCursor();
                installLayerCommitHook(); // late-bound retry
                watchStuckPreview();
                decorateLayerRows();
            }, 250);

            // Performance hint check on a slower interval
            setInterval(checkEffectPerformance, 2000);
        }, 800);
    });

    if (typeof window !== 'undefined') {
        window.spbLayerFlow = {
            // Original API (preserved)
            showDock: showLayerDock,
            hideDock: hideLayerDock,
            findLayerAt: findTopmostLayerAt,
            // New API exposed for power users / other modules
            deselectLayer: deselectActiveLayer,
            lockActiveZoneToSelectedLayer: lockActiveZoneToSelectedLayer,
            copyLayerFx: copyLayerFx,
            pasteLayerFx: pasteLayerFx,
            applyQuickFx: applyQuickFx,
            getEffectIntensity: getEffectIntensity,
            setEffectIntensity: setEffectIntensity,
            getEffectPresets: getEffectPresets,
            saveEffectPreset: saveEffectPreset,
            deleteEffectPreset: deleteEffectPreset,
            hideOthers: hideOthers,
            showAll: showAll,
            panToLayer: panToLayer,
            getLayerMeta: getLayerMeta,
            setLayerMeta: setLayerMeta,
            focusLayerInPanel: focusLayerInPanel,
            getRecentLayers: getRecentLayers,
            toggleDockMinimized: toggleDockMinimized,
            setThumbSize: setThumbSize,
            getThumbSize: getThumbSize,
            setLayerFilter: setLayerFilter,
            getLayerFilter: getLayerFilter,
            QUICK_FX_PRESETS: QUICK_FX_PRESETS
        };
    }
})();
