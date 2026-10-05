(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const getZones = deps.getZones || function() { return global.zones || []; };
        const getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return 0; };
        const allocateLinkGroupId = deps.allocateLinkGroupId || function() { return 'link_' + Date.now(); };
        const pushZoneUndo = deps.pushZoneUndo || function() {};
        const renderZones = deps.renderZones || function() {};
        const showToast = deps.showToast || function() {};
        const triggerPreviewRender = deps.triggerPreviewRender || function() {};
        const promptUser = deps.promptUser || function(message) {
            return global.prompt ? global.prompt(message) : null;
        };

        const LINK_FINISH_PROPS = ['base', 'pattern', 'finish', 'intensity', 'scale', 'rotation',
            'patternOpacity', 'customSpec', 'customPaint', 'customBright', 'patternStack', 'wear',
            'baseColorMode', 'baseColor', 'baseColorSource', 'baseColorStrength', 'baseColorScale', 'baseColorRotation',
            'gradientStops', 'gradientDirection', '_autoBaseColorFill'];

        function linkZones(indices) {
            const zones = getZones();
            if (!indices || indices.length < 2) return;
            pushZoneUndo('Link ' + indices.length + ' zones');
            const groupId = allocateLinkGroupId();
            indices.forEach(function(i) { if (zones[i]) zones[i].linkGroup = groupId; });
            renderZones();
            showToast('Linked ' + indices.length + ' zones (Group ' + groupId.replace('link_', '') + ')');
        }

        function unlinkZone(index) {
            const zones = getZones();
            if (!zones[index] || !zones[index].linkGroup) return;
            pushZoneUndo('Unlink zone "' + zones[index].name + '"');
            const group = zones[index].linkGroup;
            zones[index].linkGroup = null;
            const remaining = zones.filter(function(z) { return z.linkGroup === group; });
            if (remaining.length === 1) remaining[0].linkGroup = null;
            renderZones();
            showToast('Zone unlinked');
        }

        function linkSelectedToZone(targetIndex) {
            const zones = getZones();
            const srcIdx = getSelectedZoneIndex();
            if (srcIdx < 0 || srcIdx === targetIndex || !zones[srcIdx] || !zones[targetIndex]) return;
            pushZoneUndo('Link zone ' + (srcIdx + 1) + ' <-> ' + (targetIndex + 1));
            if (zones[targetIndex].linkGroup) {
                zones[srcIdx].linkGroup = zones[targetIndex].linkGroup;
            } else {
                const groupId = allocateLinkGroupId();
                zones[srcIdx].linkGroup = groupId;
                zones[targetIndex].linkGroup = groupId;
            }
            renderZones();
            showToast('Zones linked together');
        }

        function propagateToLinkedZones(sourceIndex, props) {
            const zones = getZones();
            const zone = zones[sourceIndex];
            if (!zone || !zone.linkGroup) return;
            zones.forEach(function(z, i) {
                if (i === sourceIndex || z.linkGroup !== zone.linkGroup) return;
                props.forEach(function(p) { z[p] = zone[p]; });
            });
        }

        function promptLinkZone(index) {
            const zones = getZones();
            if (!zones[index]) return;
            if (zones[index].linkGroup) {
                unlinkZone(index);
                return;
            }
            const options = zones.map(function(z, i) { return i === index ? null : (i + 1) + '. ' + z.name; }).filter(Boolean);
            const choice = promptUser('Link "' + zones[index].name + '" with which zone?\n\n' + options.join('\n') + '\n\nEnter zone number:');
            if (!choice) return;
            const targetIdx = parseInt(choice, 10) - 1;
            if (isNaN(targetIdx) || targetIdx < 0 || targetIdx >= zones.length || targetIdx === index) {
                showToast('Invalid zone number');
                return;
            }
            pushZoneUndo('Link "' + zones[index].name + '" + "' + zones[targetIdx].name + '"');
            if (zones[targetIdx].linkGroup) {
                zones[index].linkGroup = zones[targetIdx].linkGroup;
            } else {
                const groupId = allocateLinkGroupId();
                zones[index].linkGroup = groupId;
                zones[targetIdx].linkGroup = groupId;
            }
            LINK_FINISH_PROPS.forEach(function(p) { zones[index][p] = zones[targetIdx][p]; });
            renderZones();
            triggerPreviewRender();
            showToast('Linked: ' + zones[index].name + ' + ' + zones[targetIdx].name);
        }

        Object.assign(global, {
            LINK_FINISH_PROPS: LINK_FINISH_PROPS,
            linkZones: linkZones,
            unlinkZone: unlinkZone,
            linkSelectedToZone: linkSelectedToZone,
            propagateToLinkedZones: propagateToLinkedZones,
            promptLinkZone: promptLinkZone
        });
    }

    global.SPBZoneLinkControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
