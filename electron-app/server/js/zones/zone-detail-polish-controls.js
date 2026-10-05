(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var documentRef = deps.document || global.document;
        var getZones = deps.getZones || function() { return global.zones || []; };
        var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return -1; };
        var getFinishType = deps.getFinishType || function() { return null; };
        var getMetadata = deps.getMetadata || function() { return null; };

        function centerPanel() {
            return documentRef ? documentRef.getElementById('centerPanel') : null;
        }

        function pulsePreviewFrame(state, duration) {
            var panel = centerPanel();
            if (!panel) return;
            var cls = state === 'render' ? 'preview-rendering' : 'preview-active';
            panel.classList.add(cls);
            setTimeout(function() { panel.classList.remove(cls); }, duration || 1400);
        }

        function groupAdvancedOverlays(container) {
            if (!container) return;
            var overlayControls = container.querySelectorAll('[id^="sectionOverlay"], .overlay-toggle, [data-overlay]');
            if (overlayControls.length < 2) return;

            var studio = container.querySelector('.overlay-studio');
            if (studio) return;

            studio = documentRef.createElement('div');
            studio.className = 'overlay-studio';

            var header = documentRef.createElement('div');
            header.className = 'overlay-studio-header';
            header.innerHTML = '<span class="ekg-dot"></span><span>ADDITIONAL OVERLAYS</span><span style="margin-left:auto; font-size:9px; color:#8a96b3;">&#9662;</span>';

            var body = documentRef.createElement('div');
            body.className = 'overlay-studio-body collapsed';
            overlayControls.forEach(function(ctrl) { body.appendChild(ctrl); });

            studio.appendChild(header);
            studio.appendChild(body);

            var specSection = container.querySelector('[id^="sectionSpec"]') || container.lastElementChild;
            if (specSection && specSection.parentNode) {
                specSection.parentNode.insertBefore(studio, specSection.nextSibling);
            } else {
                container.appendChild(studio);
            }

            header.addEventListener('click', function() {
                body.classList.toggle('collapsed');
                var arrow = header.querySelector('span:last-child');
                if (arrow) arrow.textContent = body.classList.contains('collapsed') ? '\u25b8' : '\u25be';
            });
        }

        function celebrateZoneFinishChoice(zoneIndex) {
            if (!documentRef) return;
            var zoneCard = documentRef.querySelector('.zone-card[data-index="' + zoneIndex + '"]') ||
                documentRef.querySelectorAll('.zone-card')[zoneIndex];
            if (!zoneCard) return;

            zoneCard.classList.add('choice-celebrated');
            var originalBorder = zoneCard.style.borderColor;
            zoneCard.style.transition = 'border-color 0.1s, box-shadow 0.1s';
            zoneCard.style.borderColor = '#ffd166';
            zoneCard.style.boxShadow = '0 0 0 3px rgba(255,209,102,0.35), 0 12px 30px rgba(0,0,0,0.4)';

            var num = zoneCard.querySelector('.zone-number');
            if (num) {
                num.style.transition = 'box-shadow 0.1s';
                num.style.boxShadow = '0 0 0 3px rgba(255,209,102,0.6), 0 0 14px rgba(255,209,102,0.4)';
            }

            var center = centerPanel();
            if (center) {
                center.classList.add('preview-choice-celebrated');
                pulsePreviewFrame('render', 1600);

                var previewContent = center.querySelector('img, canvas');
                if (previewContent) {
                    previewContent.classList.add('choice-landed');
                    setTimeout(function() { previewContent.classList.remove('choice-landed'); }, 1400);
                }

                center.classList.add('preview-content-celebration');
                setTimeout(function() { center.classList.remove('preview-content-celebration'); }, 1600);
            }

            var detailRoot = documentRef.getElementById('zoneEditorFloat') || documentRef.getElementById('zoneDetailPanel');
            if (detailRoot) {
                var activeRow = detailRoot.querySelector('.zone-finish-row:focus-within') ||
                    detailRoot.querySelector('.zone-finish-row.active-choice');
                if (activeRow) {
                    activeRow.classList.add('choice-landed-row');
                    setTimeout(function() { activeRow.classList.remove('choice-landed-row'); }, 1100);
                }
            }

            setTimeout(function() {
                zoneCard.classList.remove('choice-celebrated');
                zoneCard.style.borderColor = originalBorder || '';
                zoneCard.style.boxShadow = '';
                if (num) num.style.boxShadow = '';
                if (center) center.classList.remove('preview-choice-celebrated');
            }, 1350);
        }

        function enhanceFinishChoiceRows(container) {
            if (!container || !documentRef) return;
            container.querySelectorAll('.zone-finish-row').forEach(function(row) {
                if (row.querySelector('.finish-category-badge')) return;
                var select = row.querySelector('select');
                if (!select || !select.value || select.value === 'none') return;

                var currentValue = select.value;
                var type = getFinishType(currentValue);
                var meta = getMetadata(currentValue);
                var nameEl = row.querySelector('.zone-finish-name, .finish-name');
                if (!nameEl) return;

                var category = type || (currentValue.indexOf('mono:') === 0 ? 'monolithic' : 'base');
                var badge = documentRef.createElement('span');
                badge.className = 'finish-category-badge';
                badge.textContent = category.charAt(0).toUpperCase() + category.slice(1);
                badge.dataset.category = category;

                var metaWrap = documentRef.createElement('div');
                metaWrap.className = 'finish-meta';
                metaWrap.appendChild(badge);

                if (meta && meta.family) {
                    var pers = documentRef.createElement('span');
                    pers.className = 'finish-personality';
                    pers.textContent = meta.family;
                    metaWrap.appendChild(pers);
                }

                var swatch = row.querySelector('img, .swatch-square');
                if (swatch && swatch.nextSibling) {
                    swatch.parentNode.insertBefore(metaWrap, swatch.nextSibling);
                } else if (nameEl.parentNode) {
                    nameEl.parentNode.insertBefore(metaWrap, nameEl);
                }
            });
        }

        function elevateChoiceSurfaces(container) {
            if (!container || !documentRef) return;
            var selectedZoneIndex = getSelectedZoneIndex();
            var baseSection = container.querySelector('#sectionBase' + (selectedZoneIndex || 0)) || container.querySelector('[id^="sectionBase"]');
            var patternSection = container.querySelector('[id^="sectionPattern"]');

            [baseSection, patternSection].forEach(function(section, idx) {
                if (!section) return;
                var surfaceType = idx === 0 ? 'base' : 'pattern';
                var labelText = idx === 0 ? 'BASE MATERIAL' : 'PATTERN / OVERLAY';
                if (section.querySelector('.choice-surface-header')) return;

                var header = documentRef.createElement('div');
                header.className = 'choice-surface-header';
                header.innerHTML = '<span class="surface-label">' + labelText + '</span><div class="surface-ekg" style="color: ' + (surfaceType === 'base' ? '#ffd166' : '#b76cff') + ';"></div>';

                var body = section.querySelector('.section-body') || section;
                if (body.firstChild) body.insertBefore(header, body.firstChild);
                else body.appendChild(header);

                section.classList.add('choice-surface');
                section.dataset.surface = surfaceType;

                section.addEventListener('mouseenter', function() {
                    pulsePreviewFrame('previewing-choice', 900);
                    var center = centerPanel();
                    if (center) center.classList.add('previewing-choice');
                }, { once: false });

                section.addEventListener('mouseleave', function() {
                    var center = centerPanel();
                    if (center) center.classList.remove('previewing-choice');
                });

                section.addEventListener('input', function() {
                    pulsePreviewFrame('active', 650);
                }, true);
            });
        }

        function injectZoneHeartbeat(container, zoneIndex) {
            if (!container || !documentRef) return;
            var floatPanel = documentRef.getElementById('zoneEditorFloat');
            if (!floatPanel) return;
            var existing = floatPanel.querySelector('.zone-heartbeat-bar');
            if (existing) existing.remove();

            var zone = getZones()[zoneIndex];
            if (!zone) return;
            var overlayCount = (zone.patternStack || []).length;
            var energy = overlayCount * 1.8;
            if (zone.patternIntensity) energy += zone.patternIntensity * 2;
            if (zone.intensity) energy += zone.intensity * 1.5;

            var energyClass = 'low-energy';
            var energyLabel = 'Calm';
            if (energy > 6) {
                energyClass = 'high-energy';
                energyLabel = 'Intense';
            } else if (energy > 3) {
                energyClass = 'medium-energy';
                energyLabel = 'Active';
            }

            var bar = documentRef.createElement('div');
            bar.className = 'zone-heartbeat-bar ' + energyClass;
            bar.innerHTML = '<span class="hb-label">ZONE HEARTBEAT</span><div class="hb-ekg"><svg viewBox="0 0 120 14" preserveAspectRatio="none"><polyline points="0,7 6,7 9,3 12,11 15,7 21,7 24,2 27,12 30,7 36,7 39,4 42,10 45,7 51,7 54,1 57,13 60,7 66,7 69,3 72,11 75,7 81,7 84,2 87,12 90,7 96,7 99,4 102,10 105,7 111,7 114,1 117,13 120,7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></div><span class="hb-energy">' + energyLabel + ' &middot; ' + overlayCount + ' layers</span>';

            var body = floatPanel.querySelector('.zone-detail-body');
            if (body) {
                body.insertBefore(bar, body.firstChild);
                return;
            }
            var header = floatPanel.querySelector('.zone-detail-header');
            if (header && header.nextSibling) header.parentNode.insertBefore(bar, header.nextSibling);
            else if (header) header.parentNode.appendChild(bar);
            else floatPanel.insertBefore(bar, floatPanel.firstChild);
        }

        Object.assign(global, {
            groupAdvancedOverlays: groupAdvancedOverlays,
            celebrateZoneFinishChoice: celebrateZoneFinishChoice,
            enhanceFinishChoiceRows: enhanceFinishChoiceRows,
            elevateChoiceSurfaces: elevateChoiceSurfaces,
            injectZoneHeartbeat: injectZoneHeartbeat,
            pulsePreviewFrame: pulsePreviewFrame
        });
    }

    global.SPBZoneDetailPolishControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
