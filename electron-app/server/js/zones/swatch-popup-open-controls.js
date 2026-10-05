(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const enhanceSwatchPopupCards = deps.enhanceSwatchPopupCards || function() {};
        const renderSwatchPopupFilterControls = deps.renderSwatchPopupFilterControls || function() {};
        const renderSwatchCurationLanes = deps.renderSwatchCurationLanes || function() {};
        const renderSwatchLowScorePanel = deps.renderSwatchLowScorePanel || function() {};
        const installSwatchPopupLazyLoader = deps.installSwatchPopupLazyLoader || function() {};
        const filterSwatchPopup = deps.filterSwatchPopup || function() {};
        const scrollSwatchPickerToSelection = deps.scrollSwatchPickerToSelection || function() {};
        const getSwatchPopupState = deps.getSwatchPopupState || function() { return { open: false }; };
        const setSwatchPopupState = deps.setSwatchPopupState || function() {};
        const getZones = deps.getZones || function() { return []; };
        const getCurrentSwatchPickerId = deps.getCurrentSwatchPickerId || function() { return ''; };
        const buildSwatchPickerGridHtml = deps.buildSwatchPickerGridHtml || function() { return ''; };
        const closeSwatchPicker = deps.closeSwatchPicker || function() {};

        // [SPB 2026-06-04 owner] Dim backdrop behind the full-screen picker. Created
        // once, lazily, and shown only for the centered finish-grid pickers.
        function ensureSwatchBackdrop() {
            if (document.getElementById('swatchPopupBackdrop')) return;
            const bd = document.createElement('div');
            bd.id = 'swatchPopupBackdrop';
            bd.addEventListener('mousedown', function() {
                if (typeof global.closeSwatchPicker === 'function') global.closeSwatchPicker();
            });
            document.body.appendChild(bd);
        }

        function renderAndShowSwatchPicker(args) {
            args = args || {};
            const popup = args.popup;
            const grid = args.grid;
            const searchInput = args.searchInput;
            const triggerEl = args.triggerEl;
            if (!popup || !grid || !searchInput || !triggerEl) return;

            grid.innerHTML = args.html || '';
            enhanceSwatchPopupCards(args.currentId, args.type);
            renderSwatchPopupFilterControls(args.type);
            renderSwatchCurationLanes(args.type);
            renderSwatchLowScorePanel(18);
            installSwatchPopupLazyLoader();

            // [SPB 2026-06-04 owner] The BASE / PATTERN (and multi-color stack base +
            // stack pattern) pickers open CENTERED + near-fullscreen with a dim backdrop
            // — the "fill the screen, more room" layout. Small color-source pickers keep
            // the compact, trigger-anchored placement.
            const FULLSCREEN_TYPES = {
                base: 1, pattern: 1, secondBase: 1, thirdBase: 1,
                fourthBase: 1, fifthBase: 1, stackPattern: 1, specOverlay: 1
            };
            const fullscreen = !!FULLSCREEN_TYPES[args.type];
            ensureSwatchBackdrop();
            const backdrop = document.getElementById('swatchPopupBackdrop');

            if (fullscreen) {
                const popupW = Math.min(1720, Math.max(1040, window.innerWidth - 40));
                const popupH = Math.max(420, window.innerHeight - 40);
                popup.classList.add('swatch-popup--fs');
                popup.style.left = Math.round((window.innerWidth - popupW) / 2) + 'px';
                popup.style.top = '20px';
                popup.style.width = popupW + 'px';
                popup.style.height = popupH + 'px';
                popup.style.maxHeight = popupH + 'px';
                if (backdrop) backdrop.classList.add('active');
            } else {
                popup.classList.remove('swatch-popup--fs');
                popup.style.height = '';
                if (backdrop) backdrop.classList.remove('active');

                const rect = triggerEl.getBoundingClientRect();
                const popupW = Math.min(1500, Math.max(1040, window.innerWidth - 10));
                const popupH = Math.min(1080, Math.max(760, window.innerHeight - 10));
                let left = rect.right + 8;
                if (left + popupW > window.innerWidth - 8) left = Math.max(8, window.innerWidth - popupW - 8);
                if (left < 8) left = 8;
                let top = rect.top;
                if (top + popupH > window.innerHeight - 8) top = Math.max(8, window.innerHeight - popupH - 8);
                if (top < 8) top = 8;

                popup.style.left = left + 'px';
                popup.style.top = top + 'px';
                popup.style.width = popupW + 'px';
                popup.style.maxHeight = popupH + 'px';
            }
            popup.classList.add('active');

            searchInput.placeholder = 'Smart search titles, descriptions, ids, or #tags...';
            searchInput.title = 'Search finish names, descriptions, ids, metadata, aliases, and hashtag-style terms such as #chrome, #weathered, #carbon, #matte, or #spec';
            searchInput.value = '';
            filterSwatchPopup('');
            setTimeout(function() {
                scrollSwatchPickerToSelection();
                searchInput.focus();
            }, 60);
        }

        function openSwatchPicker(triggerEl, type, zoneIndex, layerIndex) {
            const popup = document.getElementById('swatchPopup');
            global.SPBSpecOverlayPicker?.mountToolbar(popup, type);
            const grid = document.getElementById('swatchPopupGrid');
            const searchInput = document.getElementById('swatchSearchInput');
            const normalizedLayerIndex = layerIndex ?? -1;
            const state = getSwatchPopupState();

            if (state.open && state.type === type && state.zoneIndex === zoneIndex && state.layerIndex === normalizedLayerIndex) {
                closeSwatchPicker();
                return;
            }

            setSwatchPopupState({
                open: true,
                type: type,
                zoneIndex: zoneIndex,
                layerIndex: normalizedLayerIndex,
                triggerEl: triggerEl,
                filter: 'all',
                sort: 'default'
            });

            const zone = getZones()[zoneIndex] || {};
            const currentId = getCurrentSwatchPickerId({ zone: zone, type: type, layerIndex: layerIndex });
            const html = buildSwatchPickerGridHtml({ type: type, currentId: currentId });

            renderAndShowSwatchPicker({ popup: popup, grid: grid, searchInput: searchInput, triggerEl: triggerEl, html: html, currentId: currentId, type: type });
        }

        Object.assign(global, {
            renderAndShowSwatchPicker: renderAndShowSwatchPicker,
            openSwatchPicker: openSwatchPicker
        });
    }

    global.SPBSwatchPopupOpenControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
