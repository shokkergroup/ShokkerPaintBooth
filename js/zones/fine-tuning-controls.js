(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var getZones = typeof deps.getZones === 'function' ? deps.getZones : function() { return []; };
        var getSelectedZoneIndex = typeof deps.getSelectedZoneIndex === 'function' ? deps.getSelectedZoneIndex : function() { return -1; };
        var getOverlayBaseDisplay = typeof deps.getOverlayBaseDisplay === 'function' ? deps.getOverlayBaseDisplay : function() { return null; };

        global._fineTuningOpen = false;
        global._fineTuningZone = -1;
        if (typeof global._ftAccordionMode === 'undefined') global._ftAccordionMode = true;

        function zoneAt(zoneIndex) {
            var zones = getZones();
            return zones && zones[zoneIndex] ? zones[zoneIndex] : null;
        }

        function overlayBaseName(zone, key) {
            var value = zone[key + 'Base'] || zone[key + 'BaseColorSource'];
            if (!value) return 'None';
            var display = getOverlayBaseDisplay(value);
            return (display && display.name) || value || 'Set';
        }

        function setFineTuningTitle(zoneIndex) {
            var titleEl = global.document && global.document.getElementById('fineTuningTitle');
            if (titleEl) titleEl.textContent = 'FINE TUNING \u2014 Zone ' + (zoneIndex + 1);
        }

        global.openFineTuning = function openFineTuning(zoneIndex) {
            var zones = getZones();
            if (zoneIndex < 0 || zoneIndex >= zones.length) return;
            global._fineTuningOpen = true;
            global._fineTuningZone = zoneIndex;

            var libHeader = document.querySelector('.right-panel > .section-header');
            var libSearch = document.querySelector('.right-panel > .finish-search-bar');
            var libPanel = document.getElementById('finishLibrary');
            var ftPanel = document.getElementById('fineTuningPanel');
            if (libHeader) libHeader.style.display = 'none';
            if (libSearch) libSearch.style.display = 'none';
            if (libPanel) libPanel.style.display = 'none';
            if (ftPanel) ftPanel.style.display = 'flex';

            setFineTuningTitle(zoneIndex);
            global._buildFineTuningContent(zoneIndex);
        };

        global.closeFineTuning = function closeFineTuning() {
            global._fineTuningOpen = false;
            global._fineTuningZone = -1;

            var libHeader = document.querySelector('.right-panel > .section-header');
            var libSearch = document.querySelector('.right-panel > .finish-search-bar');
            var libPanel = document.getElementById('finishLibrary');
            var ftPanel = document.getElementById('fineTuningPanel');
            if (libHeader) libHeader.style.display = '';
            if (libSearch) libSearch.style.display = '';
            if (libPanel) libPanel.style.display = '';
            if (ftPanel) ftPanel.style.display = 'none';
        };

        global.toggleFineTuningSection = function toggleFineTuningSection(n) {
            var section = document.getElementById('ftSection' + n);
            if (!section) return;
            var isCollapsed = section.classList.contains('ft-collapsed');

            if (global._ftAccordionMode && isCollapsed) {
                document.querySelectorAll('#fineTuningBody .ft-section').forEach(function(s) {
                    s.classList.add('ft-collapsed');
                });
            }

            if (isCollapsed) {
                section.classList.remove('ft-collapsed');
            } else {
                section.classList.add('ft-collapsed');
            }
        };

        global._retargetFineTuningCloneIds = function _retargetFineTuningCloneIds(root) {
            if (!root) return;
            var idMap = {};
            root.querySelectorAll('[id]').forEach(function(node) {
                var oldId = node.id;
                if (!oldId) return;
                var newId = oldId + '_ft';
                idMap[oldId] = newId;
                node.id = newId;
            });

            var oldIds = Object.keys(idMap);
            if (!oldIds.length) return;
            var attrs = ['for', 'aria-controls', 'aria-labelledby', 'name', 'onclick', 'oninput', 'onchange', 'onpointerdown', 'onmousedown'];
            root.querySelectorAll('*').forEach(function(node) {
                attrs.forEach(function(attr) {
                    var current = node.getAttribute(attr);
                    if (!current) return;
                    var next = current;
                    oldIds.forEach(function(oldId) {
                        next = next.split(oldId).join(idMap[oldId]);
                    });
                    if (next !== current) node.setAttribute(attr, next);
                });
            });
        };

        global._buildFineTuningContent = function _buildFineTuningContent(zoneIndex) {
            var body = document.getElementById('fineTuningBody');
            if (!body) return;
            body.innerHTML = '';

            var zone = zoneAt(zoneIndex);
            if (!zone) { body.innerHTML = '<div style="padding:16px;color:var(--text-dim);">No zone selected.</div>'; return; }
            var materialStack = Array.isArray(zone.materialStack) ? zone.materialStack : (Array.isArray(zone.material_stack) ? zone.material_stack : []);
            if (materialStack.length) {
                body.innerHTML = '<div style="padding:16px;color:var(--text-dim);line-height:1.5;">This is a <b style="color:var(--accent-cyan);">Whole Car material mix</b> with ' + materialStack.length + ' finish' + (materialStack.length === 1 ? '' : 'es') + '.<br>Edit its blend, strength, and detail size in Easy Mode → Whole Car.<br><button type="button" class="btn" style="margin-top:10px;" onclick="window.spbEasy && window.spbEasy.openWhole && window.spbEasy.openWhole()">OPEN WHOLE CAR MIX</button></div>';
                return;
            }
            if (!zone.base && !zone.finish) { body.innerHTML = '<div style="padding:16px;color:var(--text-dim);">Select a base finish first to enable overlays.</div>'; return; }

            var layers = [
                { n: 2, key: 'second', label: '2nd Base', cssClass: 'ft-2nd', hasBase: !!(zone.secondBase || zone.secondBaseColorSource), baseName: overlayBaseName(zone, 'second') },
                { n: 3, key: 'third', label: '3rd Base', cssClass: 'ft-3rd', hasBase: !!(zone.thirdBase || zone.thirdBaseColorSource), baseName: overlayBaseName(zone, 'third') },
                { n: 4, key: 'fourth', label: '4th Base', cssClass: 'ft-4th', hasBase: !!(zone.fourthBase || zone.fourthBaseColorSource), baseName: overlayBaseName(zone, 'fourth') },
                { n: 5, key: 'fifth', label: '5th Base', cssClass: 'ft-5th', hasBase: !!(zone.fifthBase || zone.fifthBaseColorSource), baseName: overlayBaseName(zone, 'fifth') }
            ];

            var overlayContainer = document.getElementById('sectionOverlays' + zoneIndex);
            var overlaySections = [];
            if (overlayContainer) {
                overlaySections = Array.from(overlayContainer.querySelectorAll('.overlay-section'));
            }

            layers.forEach(function(layer, idx) {
                var sectionDiv = document.createElement('div');
                sectionDiv.className = 'ft-section ' + layer.cssClass + (idx > 0 ? ' ft-collapsed' : '');
                sectionDiv.id = 'ftSection' + layer.n;

                var header = document.createElement('div');
                header.className = 'ft-section-header';
                header.onclick = function() { global.toggleFineTuningSection(layer.n); };
                header.innerHTML = '<span>' + layer.label + ' <span style="font-size:9px;color:var(--text-dim);">' +
                    layer.baseName + '</span>' +
                    '<span class="ft-status-dot ' + (layer.hasBase ? 'active' : 'inactive') + '"></span></span>' +
                    '<span class="ft-section-arrow">&#9660;</span>';
                sectionDiv.appendChild(header);

                var bodyDiv = document.createElement('div');
                bodyDiv.className = 'ft-section-body';

                if (overlaySections[idx]) {
                    var clone = overlaySections[idx].cloneNode(true);
                    global._retargetFineTuningCloneIds(clone);
                    bodyDiv.appendChild(clone);
                } else {
                    bodyDiv.innerHTML = '<div style="padding:8px;color:var(--text-dim);font-size:10px;">Overlay controls not available. Open the zone detail panel first.</div>';
                }

                sectionDiv.appendChild(bodyDiv);
                body.appendChild(sectionDiv);
            });
        };

        global._refreshFineTuningIfOpen = function _refreshFineTuningIfOpen() {
            if (!global._fineTuningOpen) return;
            var zones = getZones();
            var zi = getSelectedZoneIndex();
            if (zi < 0) zi = global._fineTuningZone;
            if (zi >= 0 && zi < zones.length) {
                global._fineTuningZone = zi;
                setFineTuningTitle(zi);
                global._buildFineTuningContent(zi);
            }
        };
    }

    global.SPBZoneFineTuningControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
