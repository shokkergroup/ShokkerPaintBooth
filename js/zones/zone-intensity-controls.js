(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getDocument = deps.getDocument || function () { return global.document; };
    var getZones = deps.getZones || function () { return []; };
    var getIntensityValues = deps.getIntensityValues || function () { return {}; };
    var propagateToLinkedZones = deps.propagateToLinkedZones || function () {};
    var pushZoneUndo = deps.pushZoneUndo || function () {};
    var pushZoneUndoCoalesced = deps.pushZoneUndoCoalesced || function () {};
    var renderZones = deps.renderZones || function () {};
    var triggerPreviewRender = deps.triggerPreviewRender || function () {};
    var autoSave = deps.autoSave || function () {};

    function doc() {
      return getDocument() || {};
    }

    function zones() {
      return getZones() || [];
    }

    function intensityValues() {
      return getIntensityValues() || {};
    }

    function validZone(index, caller) {
      if (typeof index !== 'number' || index < 0 || index >= zones().length) {
        if (global.console && console.warn) console.warn('[SPB] ' + caller + ': invalid zone index', index);
        return null;
      }
      return zones()[index];
    }

    function setZoneFinish(index, finishId) {
      var zone = validZone(index, 'setZoneFinish');
      if (!zone) return;
      zone.finish = finishId || null;
      zone.base = null;
      zone.pattern = null;
      zone._autoBaseColorFill = false;
      zone._scopedBrushAutoBaseColor = false;
      renderZones();
      triggerPreviewRender();
      autoSave();
    }

    function setZoneIntensity(index, intensity, fromSlider) {
      var zone = validZone(index, 'setZoneIntensity');
      if (!zone) return;
      var values = intensityValues();
      if (intensity === 'custom') {
        pushZoneUndo('Switch to custom intensity');
        if (zone.customSpec == null) {
          var current = values[zone.intensity] || values['100'] || { spec: 1, paint: 1, bright: 1 };
          zone.customSpec = current.spec;
          zone.customPaint = current.paint;
          zone.customBright = current.bright;
        }
        renderZones();
        triggerPreviewRender();
        return;
      }

      var numVal = Math.max(0, Math.min(100, parseInt(intensity, 10) || 100));
      zone.intensity = String(numVal);
      zone.customSpec = null;
      zone.customPaint = null;
      zone.customBright = null;
      propagateToLinkedZones(index, ['intensity', 'customSpec', 'customPaint', 'customBright']);

      if (!fromSlider) {
        pushZoneUndo('Set intensity ' + numVal + '%');
        renderZones();
      } else {
        syncIntensityInputs(index, numVal);
      }
      triggerPreviewRender();
    }

    function syncIntensityInputs(index, numVal) {
      var d = doc();
      var card = d.getElementById && d.getElementById('zone-card-' + index);
      if (card && card.querySelectorAll) {
        card.querySelectorAll('.intensity-control-group input[type="number"]').forEach(function (el) {
          if (el !== d.activeElement) el.value = numVal;
        });
      }
      var detailPanel = d.getElementById && (d.getElementById('zoneDetailPanel') || d.getElementById('zoneEditorFloat'));
      if (detailPanel && detailPanel.querySelectorAll) {
        detailPanel.querySelectorAll('.intensity-control-group input[type="number"], .intensity-control-group input[type="range"]').forEach(function (el) {
          if (el !== d.activeElement) el.value = numVal;
        });
      }
    }

    function tickZoneIntensity(index, delta) {
      var zone = zones()[index];
      if (!zone) return;
      var current = parseInt(zone.intensity, 10) || 100;
      setZoneIntensity(index, String(Math.max(0, Math.min(100, current + delta))));
    }

    function setZonePatternIntensity(index, value) {
      var zone = zones()[index];
      if (!zone) return;
      var numVal = Math.max(0, Math.min(100, parseInt(value, 10) || 100));
      zone.patternIntensity = String(numVal);
      propagateToLinkedZones(index, ['patternIntensity']);
      pushZoneUndoCoalesced('Set pattern intensity');
      syncPatternIntensityInputs(index, numVal);
      triggerPreviewRender();
    }

    function syncPatternIntensityInputs(index, numVal) {
      var d = doc();
      ['zone-card-' + index, 'zoneEditorFloat'].forEach(function (id) {
        var panel = d.getElementById && d.getElementById(id);
        if (!panel || !panel.querySelectorAll) return;
        var groups = panel.querySelectorAll('.intensity-rows-wrap .intensity-control-group');
        if (!groups[1]) return;
        var range = groups[1].querySelector('input[type="range"]');
        var number = groups[1].querySelector('input[type="number"]');
        if (range && range !== d.activeElement) range.value = numVal;
        if (number && number !== d.activeElement) number.value = numVal;
      });
    }

    function getIntensityMultiplier(zone) {
      if (zone && zone.customSpec != null) {
        return { spec: zone.customSpec, paint: zone.customPaint, bright: zone.customBright };
      }
      var values = intensityValues();
      var preset = zone ? values[zone.intensity] : null;
      if (preset) return preset;
      var pct = (parseInt(zone && zone.intensity, 10) || 100) / 100;
      return { spec: pct, paint: pct, bright: pct };
    }

    function setCustomIntensity(index, param, value) {
      var zone = zones()[index];
      if (!zone) return;
      pushZoneUndo('Set intensity', true);
      var values = intensityValues();
      var numeric = parseFloat(value);
      if (!Number.isFinite(numeric)) numeric = 1;
      if (zone.customSpec == null) {
        var current = values[zone.intensity] || values['100'] || { spec: 1, paint: 1, bright: 1 };
        zone.customSpec = current.spec;
        zone.customPaint = current.paint;
        zone.customBright = current.bright;
      }
      if (param === 'spec') zone.customSpec = numeric;
      else if (param === 'paint') zone.customPaint = numeric;
      else if (param === 'bright') zone.customBright = numeric;
      syncCustomIntensityLabels(index, zone);
      triggerPreviewRender();
    }

    function syncCustomIntensityLabels(index, zone) {
      var d = doc();
      [
        ['detIntSpecVal', 'intSpecVal', zone.customSpec, 2],
        ['detIntPaintVal', 'intPaintVal', zone.customPaint, 2],
        ['detIntBrightVal', 'intBrightVal', zone.customBright, 3]
      ].forEach(function (item) {
        var el = d.getElementById && (d.getElementById(item[0] + index) || d.getElementById(item[1] + index));
        if (el) el.textContent = Number(item[2]).toFixed(item[3]);
      });
    }

    function toggleIntensitySliders(index) {
      var d = doc();
      var panel = d.getElementById && (d.getElementById('detIntSliders' + index) || d.getElementById('intSliders' + index));
      var arrow = d.getElementById && (d.getElementById('detIntArrow' + index) || d.getElementById('intArrow' + index));
      if (panel && panel.classList) panel.classList.toggle('open');
      if (arrow && arrow.classList) arrow.classList.toggle('open');
    }

    global.setZoneFinish = setZoneFinish;
    global.setZoneIntensity = setZoneIntensity;
    global.tickZoneIntensity = tickZoneIntensity;
    global.setZonePatternIntensity = setZonePatternIntensity;
    global.getIntensityMultiplier = getIntensityMultiplier;
    global.setCustomIntensity = setCustomIntensity;
    global.toggleIntensitySliders = toggleIntensitySliders;
  }

  global.SPBZoneIntensityControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
