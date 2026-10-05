(function(global) {
  'use strict';

  const OVERLAY_BASE_HSB_FIELDS = {
    second: { hue: 'secondBaseHueShift', sat: 'secondBaseSaturation', brt: 'secondBaseBrightness' },
    third: { hue: 'thirdBaseHueShift', sat: 'thirdBaseSaturation', brt: 'thirdBaseBrightness' },
    fourth: { hue: 'fourthBaseHueShift', sat: 'fourthBaseSaturation', brt: 'fourthBaseBrightness' },
    fifth: { hue: 'fifthBaseHueShift', sat: 'fifthBaseSaturation', brt: 'fifthBaseBrightness' }
  };
  const OVERLAY_PATTERN_HSB_FIELDS = {
    second: { hue: 'secondBasePatternHueShift', sat: 'secondBasePatternSaturation', brt: 'secondBasePatternBrightness' }
  };

  function installZoneBaseOverlayHsbControls(deps) {
    deps = deps || {};
    const getZones = deps.getZones || function() { return []; };
    const pushZoneUndo = deps.pushZoneUndo || function() {};
    const renderZones = deps.renderZones || function() {};
    const triggerPreviewRender = deps.triggerPreviewRender || function() {};

    function _formatOverlayBaseHsbValue(kind, val) {
      return kind === 'hue' ? val + String.fromCharCode(176) : String(val);
    }

    function _overlayBaseHsbClamp(kind, val) {
      const n = parseInt(val, 10) || 0;
      if (kind === 'hue') return Math.max(-180, Math.min(180, n));
      // Brightness gets extra headroom (+200) to lift very dark finishes; saturation stays +/-100.
      if (kind === 'brt') return Math.max(-100, Math.min(200, n));
      return Math.max(-100, Math.min(100, n));
    }

    function _updateOverlayBaseHsbLabel(ev, kind, val) {
      const row = ev && (ev.currentTarget || ev.target) ? (ev.currentTarget || ev.target).parentElement : null;
      if (!row) return;
      const lbl = row.querySelector('.stack-val');
      if (lbl) lbl.textContent = _formatOverlayBaseHsbValue(kind, val);
    }

    function setZoneOverlayBaseHsb(index, layer, kind, val, ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
      const zones = getZones();
      if (index < 0 || index >= zones.length) return;
      const fields = OVERLAY_BASE_HSB_FIELDS[layer];
      const field = fields && fields[kind];
      if (!field) return;
      pushZoneUndo('', true);
      const n = _overlayBaseHsbClamp(kind, val);
      zones[index][field] = n;
      _updateOverlayBaseHsbLabel(ev, kind, n);
      triggerPreviewRender();
    }

    function stepZoneOverlayBaseHsb(index, layer, kind, direction, ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
      const zones = getZones();
      if (index < 0 || index >= zones.length) return;
      const fields = OVERLAY_BASE_HSB_FIELDS[layer];
      const field = fields && fields[kind];
      if (!field) return;
      const micro = !!(ev && (ev.shiftKey || ev.altKey || ev.ctrlKey || ev.metaKey));
      const step = micro ? 1 : 5;
      const cur = parseInt(zones[index][field], 10) || 0;
      setZoneOverlayBaseHsb(index, layer, kind, cur + (direction * step), ev);
      renderZones();
    }

    function commitZoneOverlayBaseHsb(index, ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
      renderZones();
      triggerPreviewRender();
    }

    function stopOverlayBaseHsbPointer(ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
    }

    function setZoneOverlayPatternHsb(index, layer, kind, val, ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
      const zones = getZones();
      if (index < 0 || index >= zones.length) return;
      const fields = OVERLAY_PATTERN_HSB_FIELDS[layer];
      const field = fields && fields[kind];
      if (!field) return;
      pushZoneUndo('', true);
      const n = _overlayBaseHsbClamp(kind, val);
      zones[index][field] = n;
      _updateOverlayBaseHsbLabel(ev, kind, n);
      triggerPreviewRender();
    }

    function stepZoneOverlayPatternHsb(index, layer, kind, direction, ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
      const zones = getZones();
      if (index < 0 || index >= zones.length) return;
      const fields = OVERLAY_PATTERN_HSB_FIELDS[layer];
      const field = fields && fields[kind];
      if (!field) return;
      const micro = !!(ev && (ev.shiftKey || ev.altKey || ev.ctrlKey || ev.metaKey));
      const step = micro ? 1 : 5;
      const cur = parseInt(zones[index][field], 10) || 0;
      setZoneOverlayPatternHsb(index, layer, kind, cur + (direction * step), ev);
      renderZones();
    }

    function commitZoneOverlayPatternHsb(index, ev) {
      if (ev && typeof ev.stopPropagation === 'function') ev.stopPropagation();
      renderZones();
      triggerPreviewRender();
    }

    global.setZoneOverlayBaseHsb = setZoneOverlayBaseHsb;
    global.stepZoneOverlayBaseHsb = stepZoneOverlayBaseHsb;
    global.commitZoneOverlayBaseHsb = commitZoneOverlayBaseHsb;
    global.stopOverlayBaseHsbPointer = stopOverlayBaseHsbPointer;
    global.setZoneOverlayPatternHsb = setZoneOverlayPatternHsb;
    global.stepZoneOverlayPatternHsb = stepZoneOverlayPatternHsb;
    global.commitZoneOverlayPatternHsb = commitZoneOverlayPatternHsb;
  }

  global.SPBZoneBaseOverlayHsbControls = {
    install: installZoneBaseOverlayHsbControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
