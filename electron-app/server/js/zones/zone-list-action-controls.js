(function (global) {
    'use strict';

    function install(deps) {
        deps = deps || {};

        var documentRef = deps.document || (global && global.document);
        var confirmDialog = deps.confirm || function () { return true; };
        var requestAnimationFrameFn = deps.requestAnimationFrame || function (fn) { return setTimeout(fn, 0); };
        var setTimeoutFn = deps.setTimeout || function (fn, ms) { return setTimeout(fn, ms); };
        var getZones = deps.getZones || function () { return []; };
        var setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
        var getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return -1; };
        var setLastRenderedZoneDetailIndex = deps.setLastRenderedZoneDetailIndex || function () {};
        var getPlacementLayer = deps.getPlacementLayer || function () { return 'none'; };
        var setPlacementLayer = deps.setPlacementLayer || function () {};
        var getCanvasMode = deps.getCanvasMode || function () { return 'zone'; };
        var deactivateManualPlacement = deps.deactivateManualPlacement || function () {};
        var updatePlacementBanner = deps.updatePlacementBanner || function () {};
        var setToolbarEditMode = deps.setToolbarEditMode || function () {};
        var renderZones = deps.renderZones || function () {};
        var renderZoneDetail = deps.renderZoneDetail || function () {};
        var updateDrawZoneIndicator = deps.updateDrawZoneIndicator || function () {};
        var syncEyedropperPanel = deps.syncEyedropperPanel || function () {};
        var updateRegionStatus = deps.updateRegionStatus || function () {};
        var renderRegionOverlay = deps.renderRegionOverlay || function () {};
        var refreshActiveToolLabel = deps.refreshActiveToolLabel || function () {};
        var pushZoneUndo = deps.pushZoneUndo || function () {};
        var triggerPreviewRender = deps.triggerPreviewRender || function () {};
        var autoSave = deps.autoSave || function () {};
        var showToast = deps.showToast || function () {};

        var zoneDragIndex = -1;

        function zoneList() {
            return getZones() || [];
        }

        function placementLayerAllowedForZone(layer, zone) {
            if (!layer || layer === 'none' || !zone) return true;
            return (layer === 'pattern' && zone.pattern && zone.pattern !== 'none') ||
                (layer === 'second_base' && zone.secondBase && zone.secondBasePattern) ||
                (layer === 'third_base' && zone.thirdBase && zone.thirdBasePattern) ||
                (layer === 'fourth_base' && zone.fourthBase && zone.fourthBasePattern) ||
                (layer === 'fifth_base' && zone.fifthBase && zone.fifthBasePattern) ||
                (layer === 'base' && (zone.base || zone.finish)) ||
                (typeof layer === 'string' && layer.indexOf('spec_pattern') === 0);
        }

        function collapseZoneDetail() {
            setLastRenderedZoneDetailIndex(-1);
            var fallbackPanel = documentRef ? documentRef.getElementById('zoneDetailPanel') : null;
            if (fallbackPanel) fallbackPanel.innerHTML = '';
            var floatPanel = documentRef ? documentRef.getElementById('zoneEditorFloat') : null;
            if (floatPanel) {
                floatPanel.innerHTML = '';
                floatPanel.classList.remove('active', 'collapsed');
                floatPanel.style.display = '';
                floatPanel.style.visibility = '';
            }
            var tab = documentRef ? documentRef.getElementById('zoneFloatExpandTab') : null;
            if (tab) tab.classList.remove('visible');
            updateBottomBarShift();
        }

        function toggleZoneFloat() {
            var floatPanel = documentRef ? documentRef.getElementById('zoneEditorFloat') : null;
            var tab = documentRef ? documentRef.getElementById('zoneFloatExpandTab') : null;
            if (!floatPanel || !floatPanel.classList.contains('active')) return;
            if (floatPanel.classList.contains('collapsed')) {
                floatPanel.classList.remove('collapsed');
                if (tab) {
                    tab.classList.remove('visible');
                    tab.innerHTML = '&#9664;';
                }
            } else {
                floatPanel.classList.add('collapsed');
                if (tab) {
                    tab.classList.add('visible');
                    tab.innerHTML = '&#9654;';
                }
            }
            updateBottomBarShift();
        }

        function updateBottomBarShift() {
            var floatPanel = documentRef ? documentRef.getElementById('zoneEditorFloat') : null;
            var isOpen = floatPanel && floatPanel.classList.contains('active') && !floatPanel.classList.contains('collapsed');
            var centerPanel = documentRef ? documentRef.getElementById('centerPanel') : null;
            if (centerPanel) centerPanel.style.paddingLeft = isOpen ? '425px' : '0';
        }

        function selectZone(index) {
            var zones = zoneList();
            if (index < 0 || index >= zones.length) return;

            var placementLayer = getPlacementLayer();
            if (index !== getSelectedZoneIndex() && placementLayer !== 'none' && !placementLayerAllowedForZone(placementLayer, zones[index])) {
                setPlacementLayer('none');
                deactivateManualPlacement();
                updatePlacementBanner();
            }

            setSelectedZoneIndex(index);
            if (getCanvasMode() === 'eyedropper' && global._spbPickFromCarZone) {
                global._spbPickFromCarZone.zone = index;
            }
            setToolbarEditMode('zone', { silent: true });
            renderZones();
            if (index >= 0 && index < zones.length) renderZoneDetail(index);
            updateDrawZoneIndicator();
            syncEyedropperPanel();
            updateRegionStatus();
            renderRegionOverlay();
            refreshActiveToolLabel();
        }

        function updateZoneName(index, name) {
            var zones = zoneList();
            if (index < 0 || index >= zones.length) return;
            zones[index].name = (typeof name === 'string' ? name : '').substring(0, 100);
        }

        function deleteZone(index) {
            var zones = zoneList();
            if (index < 0 || index >= zones.length) return;
            if (zones.length <= 1) {
                showToast('Cannot delete the last zone -- at least one zone is required', true);
                return;
            }

            var zone = zones[index];
            if (!zone) return;
            var hasFinish = zone.base || zone.finish;
            var hasColor = zone.color !== null || zone.colorMode === 'multi';
            var hasRegion = zone.regionMask && zone.regionMask.some(function (value) { return value > 0; });
            if (hasFinish || hasColor || hasRegion) {
                var details = [];
                if (hasFinish) details.push('finish assigned');
                if (hasColor) details.push('color set');
                if (hasRegion) details.push('region drawn');
                if (!confirmDialog('Delete "' + zone.name + '"? This zone has ' + details.join(', ') + '.')) return;
            }

            pushZoneUndo('Delete zone "' + zone.name + '"');
            var card = documentRef ? documentRef.getElementById('zone-card-' + index) : null;
            if (card) {
                card.style.transition = 'all 0.18s ease';
                card.style.opacity = '0';
                card.style.transform = 'translateX(12px) scale(0.96)';
            }
            setTimeoutFn(function () {
                var selectedIndex = getSelectedZoneIndex();
                zones.splice(index, 1);
                if (index < selectedIndex) selectedIndex = Math.max(0, selectedIndex - 1);
                else if (selectedIndex >= zones.length) selectedIndex = zones.length - 1;
                setSelectedZoneIndex(selectedIndex);
                renderZones();
                triggerPreviewRender();
                autoSave();
                showToast('Deleted zone "' + zone.name + '" -- Ctrl+Z to undo');
            }, card ? 160 : 0);
        }

        function moveZoneUp(index) {
            var zones = zoneList();
            if (index <= 0 || index >= zones.length) return;
            pushZoneUndo('Move zone up');
            var previous = zones[index - 1];
            zones[index - 1] = zones[index];
            zones[index] = previous;
            var selectedIndex = getSelectedZoneIndex();
            if (selectedIndex === index) setSelectedZoneIndex(index - 1);
            else if (selectedIndex === index - 1) setSelectedZoneIndex(index);
            renderZones();
            triggerPreviewRender();
        }

        function moveZoneDown(index) {
            var zones = zoneList();
            if (index < 0 || index >= zones.length - 1) return;
            pushZoneUndo('Move zone down');
            var next = zones[index + 1];
            zones[index + 1] = zones[index];
            zones[index] = next;
            var selectedIndex = getSelectedZoneIndex();
            if (selectedIndex === index) setSelectedZoneIndex(index + 1);
            else if (selectedIndex === index + 1) setSelectedZoneIndex(index);
            renderZones();
            triggerPreviewRender();
        }

        function zoneDragStart(event, index) {
            zoneDragIndex = index;
            if (event && event.dataTransfer) {
                event.dataTransfer.effectAllowed = 'move';
                event.dataTransfer.setData('text/plain', String(index));
                var dragImage = documentRef ? documentRef.getElementById('zone-card-' + index) : null;
                if (dragImage) event.dataTransfer.setDragImage(dragImage, 20, 20);
            }
            requestAnimationFrameFn(function () {
                var card = documentRef ? documentRef.getElementById('zone-card-' + index) : null;
                if (card) card.classList.add('dragging');
            });
        }

        function zoneDragOver(event) {
            if (event && event.preventDefault) event.preventDefault();
            if (event && event.dataTransfer) event.dataTransfer.dropEffect = 'move';
        }

        function zoneDragEnter(event, index) {
            if (event && event.preventDefault) event.preventDefault();
            if (documentRef) {
                documentRef.querySelectorAll('.zone-card.drag-over').forEach(function (card) {
                    card.classList.remove('drag-over');
                });
            }
            if (zoneDragIndex === index) return;
            var card = documentRef ? documentRef.getElementById('zone-card-' + index) : null;
            if (card) card.classList.add('drag-over');
        }

        function zoneDragLeave(event) {
            var card = event && event.target && event.target.closest ? event.target.closest('.zone-card') : null;
            var relatedTarget = event && event.relatedTarget;
            if (card && !card.contains(relatedTarget)) card.classList.remove('drag-over');
        }

        function zoneDrop(event, dropIndex) {
            if (event && event.preventDefault) event.preventDefault();
            if (documentRef) {
                documentRef.querySelectorAll('.zone-card.drag-over, .zone-card.dragging').forEach(function (card) {
                    card.classList.remove('drag-over', 'dragging');
                });
            }
            var zones = zoneList();
            var fromIndex = zoneDragIndex;
            if (fromIndex < 0 || fromIndex === dropIndex || fromIndex >= zones.length) return;
            pushZoneUndo('Reorder zones');
            var zone = zones.splice(fromIndex, 1)[0];
            zones.splice(dropIndex, 0, zone);
            var selectedIndex = getSelectedZoneIndex();
            if (selectedIndex === fromIndex) selectedIndex = dropIndex;
            else if (fromIndex < selectedIndex && dropIndex >= selectedIndex) selectedIndex--;
            else if (fromIndex > selectedIndex && dropIndex <= selectedIndex) selectedIndex++;
            zoneDragIndex = -1;
            setSelectedZoneIndex(selectedIndex);
            renderZones();
            triggerPreviewRender();
            autoSave();
        }

        function zoneDragEnd() {
            zoneDragIndex = -1;
            if (!documentRef) return;
            documentRef.querySelectorAll('.zone-card.drag-over, .zone-card.dragging').forEach(function (card) {
                card.classList.remove('drag-over', 'dragging');
            });
        }

        function toggleZoneMute(index) {
            var zones = zoneList();
            if (index < 0 || index >= zones.length) return;
            pushZoneUndo(zones[index].muted ? 'Unmute zone' : 'Mute zone');
            zones[index].muted = !zones[index].muted;
            renderZones();
            triggerPreviewRender();
            autoSave();
            showToast(zones[index].muted ?
                zones[index].name + ' muted (excluded from render)' :
                zones[index].name + ' unmuted');
        }

        global.collapseZoneDetail = collapseZoneDetail;
        global.toggleZoneFloat = toggleZoneFloat;
        global.updateBottomBarShift = updateBottomBarShift;
        global.selectZone = selectZone;
        global.updateZoneName = updateZoneName;
        global.deleteZone = deleteZone;
        global.moveZoneUp = moveZoneUp;
        global.moveZoneDown = moveZoneDown;
        global.zoneDragStart = zoneDragStart;
        global.zoneDragOver = zoneDragOver;
        global.zoneDragEnter = zoneDragEnter;
        global.zoneDragLeave = zoneDragLeave;
        global.zoneDrop = zoneDrop;
        global.zoneDragEnd = zoneDragEnd;
        global.toggleZoneMute = toggleZoneMute;
    }

    global.SPBZoneListActionControls = {
        install: install
    };
})(typeof window !== 'undefined' ? window : globalThis);
