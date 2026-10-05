(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const getSwatchPopupState = deps.getSwatchPopupState || function() { return { open: false }; };
        const resetSwatchPopupState = deps.resetSwatchPopupState || function() {};
        const toggleSwatchLowScorePanel = deps.toggleSwatchLowScorePanel || function() {};
        const disconnectSwatchPopupLazyLoader = deps.disconnectSwatchPopupLazyLoader || function() {};
        const setPickerActiveLaneContext = deps.setPickerActiveLaneContext || function() {};
        const filterSwatchPopup = deps.filterSwatchPopup || function() {};

        function closeSwatchPicker() {
            const popup = document.getElementById('swatchPopup');
            if (popup) {
                popup.classList.remove('active');
                popup.classList.remove('swatch-popup--fs');
                popup.style.height = '';
                popup.dataset.activeLane = 'all';
            }
            const swatchBackdrop = document.getElementById('swatchPopupBackdrop');
            if (swatchBackdrop) swatchBackdrop.classList.remove('active');
            const laneStatus = document.getElementById('swatchActiveLaneStatus');
            if (laneStatus) {
                laneStatus.hidden = true;
                laneStatus.innerHTML = '';
            }
            toggleSwatchLowScorePanel(false);
            disconnectSwatchPopupLazyLoader();
            setPickerActiveLaneContext('main', null, null);
            // SPB live-picker: tear down the on-car Stage session (cancels any in-flight
            // preview, clears the snapshot). Safe no-op in classic mode.
            if (typeof global.resetSwatchStage === 'function') {
                try { global.resetSwatchStage(); } catch (e) {}
            }
            resetSwatchPopupState();
        }

        function wireSwatchPopupLifecycleEvents() {
            if (global.__spbSwatchPopupLifecycleEventsWired) return;
            global.__spbSwatchPopupLifecycleEventsWired = true;

            document.addEventListener('mousedown', function(e) {
                if (!getSwatchPopupState().open) return;
                const popup = document.getElementById('swatchPopup');
                if (popup && !popup.contains(e.target) && !e.target.closest('.swatch-trigger')) {
                    closeSwatchPicker();
                }
            });

            document.addEventListener('keydown', function(e) {
                if (e.defaultPrevented) return;
                if (e.key === 'Escape' && getSwatchPopupState().open) {
                    closeSwatchPicker();
                    e.stopPropagation();
                }
                if (!getSwatchPopupState().open) return;
                const searchInput = document.getElementById('swatchSearchInput');
                if (!searchInput || document.activeElement === searchInput) return;
                const activeTag = (document.activeElement && document.activeElement.tagName || '').toLowerCase();
                if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' || (document.activeElement && document.activeElement.isContentEditable)) return;
                if (e.ctrlKey || e.metaKey || e.altKey || e.key.length !== 1) return;
                if (!/[a-z0-9#._ -]/i.test(e.key)) return;
                e.preventDefault();
                searchInput.focus();
                searchInput.value = (searchInput.value || '') + e.key;
                filterSwatchPopup(searchInput.value);
            });
        }

        Object.assign(global, { closeSwatchPicker: closeSwatchPicker });
        wireSwatchPopupLifecycleEvents();
    }

    global.SPBSwatchPopupLifecycleControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
