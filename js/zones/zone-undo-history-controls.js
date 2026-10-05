(function(global) {
  'use strict';

  // SPB-93 T32, owner verdict: every editing tool must work like one coherent
  // Photoshop/GIMP document. Live PSD QA proved the extracted controller was
  // loaded but its unified renderer was replaced by the legacy Zone-only view.
  // Keep panel rendering here as the one runtime owner for every document kind.
  function renderPanel(options) {
    options = options || {};
    var doc = options.document || global.document;
    var list = doc && doc.getElementById('undoHistoryList');
    if (!list) return false;
    var count = doc.getElementById('undoHistoryCount');
    var escapeHtml = options.escapeHtml || function(value) { return String(value == null ? '' : value); };
    var formatTimeAgo = options.formatTimeAgo || function() { return ''; };
    var zoneUndoStack = options.zoneUndoStack || [];
    var pointer = Number.isFinite(options.undoHistoryPointer) ? options.undoHistoryPointer : -1;
    var unified = typeof global.getUnifiedUndoHistoryEntries === 'function'
      ? global.getUnifiedUndoHistoryEntries(50)
      : null;

    if (Array.isArray(unified) && unified.length > 0) {
      if (count) count.textContent = unified.length + (unified.length === 1 ? ' action' : ' actions');
      var unifiedHtml = '<div class="undo-history-item active" style="cursor:default;"><span class="undo-history-label" style="color:var(--accent-green);">Current State</span><span class="undo-history-time">now</span></div>';
      unified.forEach(function(entry) {
        var kindLabel = entry.kind === 'layer' ? 'Layer' : entry.kind === 'pixel' ? 'Pixels' : entry.kind === 'zone-mask' ? 'Zone mask' : entry.kind === 'zone-config' ? 'Zone' : 'Decal';
        var time = entry.timestamp ? formatTimeAgo(entry.timestamp) : '';
        unifiedHtml += '<div class="undo-history-item" style="cursor:default;" title="Use Undo to step back through actions in exact order">'
          + '<span class="undo-history-label">' + escapeHtml(kindLabel) + ' &middot; ' + escapeHtml(entry.label) + '</span>'
          + '<span class="undo-history-time">' + escapeHtml(time) + '</span></div>';
      });
      list.innerHTML = unifiedHtml;
      return true;
    }

    if (count) count.textContent = zoneUndoStack.length + ' actions';
    var html = '';
    if (zoneUndoStack.length === 0) {
      html = '<div style="color:var(--text-dim); font-size:10px; padding:8px; text-align:center;">No history yet. Make changes to see them here.</div>';
    } else {
      for (var i = zoneUndoStack.length - 1; i >= 0; i -= 1) {
        var entry = zoneUndoStack[i];
        var isActive = i === pointer;
        var dimmed = i > pointer && pointer < zoneUndoStack.length;
        var ctxInfo = entry.context ? ' (Z' + (entry.context.zoneIndex + 1) + ': ' + escapeHtml(entry.context.zoneName) + ')' : '';
        html += '<div class="undo-history-item' + (isActive ? ' active' : '') + (dimmed ? ' dimmed' : '') + '" onclick="jumpToUndoState(' + i + ')" title="Click to restore this state' + (entry.context ? ' | Zone: ' + escapeHtml(entry.context.zoneName) : '') + '">'
          + '<span class="undo-history-label">' + escapeHtml(entry.label) + ctxInfo + '</span>'
          + '<span class="undo-history-time">' + formatTimeAgo(entry.timestamp) + '</span></div>';
      }
      if (pointer >= zoneUndoStack.length) {
        html = '<div class="undo-history-item active" style="cursor:default;"><span class="undo-history-label" style="color:var(--accent-green);">Current State</span><span class="undo-history-time">now</span></div>' + html;
      }
    }
    list.innerHTML = html;
    return true;
  }

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var getZones = deps.getZones || function() { return global.zones || []; };
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return 0; };
    var setSelectedZoneIndex = deps.setSelectedZoneIndex || function() {};
    var getUndoHistoryPointer = deps.getUndoHistoryPointer || function() { return -1; };
    var setUndoHistoryPointer = deps.setUndoHistoryPointer || function() {};
    var zoneUndoStack = deps.zoneUndoStack || [];
    var zoneRedoStack = deps.zoneRedoStack || [];
    var maxZoneUndo = deps.maxZoneUndo || 50;
    var cloneZoneState = deps.cloneZoneState || function(z) { return JSON.parse(JSON.stringify(z || {})); };
    var ensureZoneShape = deps.ensureZoneShape || cloneZoneState;
    var cloneUint8ArrayLike = deps.cloneUint8ArrayLike || function(value) { return value ? new Uint8Array(value) : null; };
    var renderZones = deps.renderZones || function() {};
    var showToast = deps.showToast || function() {};
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };
    var confirmUser = deps.confirmUser || function(message) { return global.confirm ? global.confirm(message) : false; };
    var clearAllRedos = deps.clearAllRedos || function() {};
    var recordUndoAction = deps.recordUndoAction || function() {};
    var getDrawUndoStack = deps.getDrawUndoStack || function() { return null; };
    var getDrawRedoStack = deps.getDrawRedoStack || function() { return null; };
    var undoActiveDragTimer = null;

    function zoneSnapshot() {
      return getZones().map(function(z) {
        return cloneZoneState(z, {
          preserveId: true,
          includeRegionMask: false,
          includeSpatialMask: true,
          includePatternStrengthMap: true
        });
      });
    }

    function restoreSnapshot(snapshot) {
      var zones = getZones();
      var masksById = new Map();
      for (var i = 0; i < zones.length; i += 1) {
        if (zones[i] && zones[i].id != null) masksById.set(zones[i].id, zones[i].regionMask);
      }
      zones.length = 0;
      snapshot.forEach(function(z) {
        var restored = ensureZoneShape(z, { includeRegionMask: false, includeSpatialMask: true });
        restored.regionMask = (restored && restored.id != null && masksById.has(restored.id))
          ? cloneUint8ArrayLike(masksById.get(restored.id))
          : null;
        zones.push(restored);
      });
      setSelectedZoneIndex(Math.min(getSelectedZoneIndex(), zones.length - 1));
    }

    function pushZoneUndo(label, isDrag) {
      if (isDrag && undoActiveDragTimer) {
        clearTimeout(undoActiveDragTimer);
        undoActiveDragTimer = setTimeout(function() { undoActiveDragTimer = null; }, 500);
        return;
      }
      clearAllRedos();
      zoneRedoStack.length = 0;
      var zones = getZones();
      var selectedZoneIndex = getSelectedZoneIndex();
      zoneUndoStack.push({
        label: label || 'Change',
        timestamp: Date.now(),
        snapshot: zoneSnapshot(),
        context: {
          zoneIndex: selectedZoneIndex,
          zoneName: (zones[selectedZoneIndex] && zones[selectedZoneIndex].name) || 'Unknown',
          zoneCount: zones.length
        }
      });
      if (zoneUndoStack.length > maxZoneUndo) zoneUndoStack.shift();
      setUndoHistoryPointer(zoneUndoStack.length);
      renderUndoHistoryPanel();
      recordUndoAction('zone-config');
      if (isDrag) undoActiveDragTimer = setTimeout(function() { undoActiveDragTimer = null; }, 500);
    }

    function undoZoneChange() {
      if (zoneUndoStack.length === 0) {
        showToast('Nothing to undo - no zone changes recorded yet');
        return false;
      }
      var entry = zoneUndoStack.pop();
      zoneRedoStack.push({ label: entry.label, timestamp: Date.now(), snapshot: zoneSnapshot() });
      restoreSnapshot(entry.snapshot);
      setUndoHistoryPointer(zoneUndoStack.length);
      renderZones();
      renderUndoHistoryPanel();
      showToast('Undo: ' + entry.label);
      return true;
    }

    function redoZoneChange() {
      if (zoneRedoStack.length === 0) {
        showToast('Nothing to redo - make a change and undo it first');
        return false;
      }
      var entry = zoneRedoStack.pop();
      zoneUndoStack.push({ label: entry.label, timestamp: Date.now(), snapshot: zoneSnapshot() });
      restoreSnapshot(entry.snapshot);
      setUndoHistoryPointer(zoneUndoStack.length);
      renderZones();
      renderUndoHistoryPanel();
      showToast('Redo: ' + entry.label);
      return true;
    }

    function jumpToUndoState(index) {
      if (index < 0 || index >= zoneUndoStack.length) return;
      var entry = zoneUndoStack[index];
      zoneRedoStack.push({ label: 'Jump', timestamp: Date.now(), snapshot: zoneSnapshot() });
      restoreSnapshot(entry.snapshot);
      setUndoHistoryPointer(index);
      renderZones();
      renderUndoHistoryPanel();
      showToast('Jumped to: ' + entry.label);
    }

    function renderUndoHistoryPanel() {
      return renderPanel({
        document: doc,
        zoneUndoStack: zoneUndoStack,
        undoHistoryPointer: getUndoHistoryPointer(),
        formatTimeAgo: formatTimeAgo,
        escapeHtml: escapeHtml
      });
    }

    function formatTimeAgo(ts) {
      var diff = Math.floor((Date.now() - ts) / 1000);
      if (diff < 5) return 'just now';
      if (diff < 60) return diff + 's ago';
      if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
      return Math.floor(diff / 3600) + 'h ago';
    }

    function toggleUndoHistoryPanel() {
      var panel = doc && doc.getElementById('undoHistoryPanel');
      if (!panel) return;
      if (panel.classList.contains('open')) panel.classList.remove('open');
      else {
        panel.classList.add('open');
        renderUndoHistoryPanel();
      }
    }

    function clearUndoHistory() {
      if (!confirmUser('Clear ALL undo history (zone, region, pixel, and layer stacks)? This cannot be undone.')) return;
      zoneUndoStack.length = 0;
      zoneRedoStack.length = 0;
      var drawUndoStack = getDrawUndoStack();
      var drawRedoStack = getDrawRedoStack();
      if (drawUndoStack) drawUndoStack.length = 0;
      if (drawRedoStack) drawRedoStack.length = 0;
      ['_pixelUndoStack', '_pixelRedoStack', '_layerUndoStack', '_layerRedoStack', 'redoStack'].forEach(function(name) {
        try { if (global[name]) global[name].length = 0; } catch (_) {}
      });
      clearAllRedos();
      if (typeof global._clearUnifiedUndoActionTrails === 'function') global._clearUnifiedUndoActionTrails();
      setUndoHistoryPointer(-1);
      renderUndoHistoryPanel();
      showToast('Cleared all undo history (zone + region + pixel + layer stacks)');
    }

    function isTextEntryTargetForGlobalUndo(target) {
      if (!target) return false;
      if (target.isContentEditable) return true;
      var tag = String(target.tagName || '').toLowerCase();
      if (tag === 'textarea') return true;
      if (tag !== 'input') return false;
      var type = String(target.type || '').toLowerCase();
      return !type || ['text', 'search', 'email', 'url', 'tel', 'password', 'number', 'date', 'datetime-local', 'month', 'time', 'week'].includes(type);
    }

    Object.assign(global, {
      pushZoneUndo: pushZoneUndo,
      undoZoneChange: undoZoneChange,
      redoZoneChange: redoZoneChange,
      jumpToUndoState: jumpToUndoState,
      renderUndoHistoryPanel: renderUndoHistoryPanel,
      formatTimeAgo: formatTimeAgo,
      toggleUndoHistoryPanel: toggleUndoHistoryPanel,
      clearUndoHistory: clearUndoHistory,
      _isTextEntryTargetForGlobalUndo: isTextEntryTargetForGlobalUndo
    });
  }

  global.SPBZoneUndoHistoryControls = { install: install, renderPanel: renderPanel };
})(typeof window !== 'undefined' ? window : globalThis);
