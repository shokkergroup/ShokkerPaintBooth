'use strict';

(function () {
  const SCALE_STEP = 0.05;
  const SCALE_BASE_MIN = 0.05;
  const SCALE_BASE_MAX = 10.0;

  function clampPct(val, fallback) {
    const pct = !Number.isNaN(parseInt(val, 10)) ? parseInt(val, 10) : fallback;
    return Math.max(0, Math.min(2, pct / 100));
  }

  function roundToStep(val, step) {
    return Math.round(val / step) * step;
  }

  function preview() {
    if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
  }

  function render() {
    if (typeof window.renderZones === 'function') window.renderZones();
  }

  function syncRange(fnName, index, value) {
    document.querySelectorAll(`input[type="range"][oninput*="${fnName}(${index},"]`).forEach(sl => { sl.value = value; });
  }

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;

    window.setZoneBaseStrength = function setZoneBaseStrength(index, val) {
      pushZoneUndo('Set base strength', true);
      const zone = getZones()[index];
      zone.baseStrength = clampPct(val, 100);
      const pct = Math.round(zone.baseStrength * 100);
      const label = document.getElementById('detBaseStrVal' + index);
      if (label) label.textContent = pct + '%';
      preview();
    };

    window.stepZoneBaseStrength = function stepZoneBaseStrength(index, delta) {
      const cur = Math.round((getZones()[index].baseStrength ?? 1) * 100);
      window.setZoneBaseStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
    };

    window.setZoneBaseSpecStrength = function setZoneBaseSpecStrength(index, val) {
      pushZoneUndo('Set base spec strength', true);
      const zone = getZones()[index];
      zone.baseSpecStrength = clampPct(val, 100);
      const label = document.getElementById('detBaseSpecStrVal' + index);
      if (label) label.textContent = Math.round(zone.baseSpecStrength * 100) + '%';
      preview();
    };

    window.stepZoneBaseSpecStrength = function stepZoneBaseSpecStrength(index, delta) {
      const cur = Math.round((getZones()[index].baseSpecStrength ?? 1) * 100);
      window.setZoneBaseSpecStrength(index, Math.max(0, Math.min(200, cur + delta * 5)));
    };

    window.setZoneBaseSpecBlendMode = function setZoneBaseSpecBlendMode(index, val) {
      pushZoneUndo('Set spec blend mode');
      getZones()[index].baseSpecBlendMode = val || 'normal';
      preview();
    };

    window.setZoneBaseRotation = function setZoneBaseRotation(index, val) {
      pushZoneUndo('Set base rotation', true);
      const v = Math.round(((Number(val) || 0) % 360 + 360) % 360 / 5) * 5;
      getZones()[index].baseRotation = v;
      ['detBaseRotVal', 'baseRotVal'].forEach(prefix => {
        const el = document.getElementById(prefix + index);
        if (!el) return;
        if (el.tagName === 'INPUT') el.value = v;
        else el.textContent = v + 'deg';
      });
      const posLabel = document.getElementById('detBasePosRotVal' + index);
      if (posLabel) posLabel.textContent = v + 'deg';
      syncRange('setZoneBaseRotation', index, v);
      preview();
    };

    window.stepZoneBaseRotation = function stepZoneBaseRotation(index, delta) {
      const cur = getZones()[index].baseRotation ?? 0;
      window.setZoneBaseRotation(index, cur + delta * 5);
    };

    window.resetZoneBaseRotation = function resetZoneBaseRotation(index) {
      window.setZoneBaseRotation(index, 0);
    };

    window.setZoneBaseOffsetX = function setZoneBaseOffsetX(index, val) {
      pushZoneUndo('Set base offset X', true);
      const v = Math.max(0, Math.min(1, Number(val) / 100));
      getZones()[index].baseOffsetX = v;
      const label = document.getElementById('detBasePosXVal' + index);
      if (label) label.textContent = Math.round(v * 100) + '%';
      preview();
    };

    window.setZoneBaseOffsetY = function setZoneBaseOffsetY(index, val) {
      pushZoneUndo('Set base offset Y', true);
      const v = Math.max(0, Math.min(1, Number(val) / 100));
      getZones()[index].baseOffsetY = v;
      const label = document.getElementById('detBasePosYVal' + index);
      if (label) label.textContent = Math.round(v * 100) + '%';
      preview();
    };

    window.setZoneBaseFlipH = function setZoneBaseFlipH(index, val) {
      pushZoneUndo('Set base flip H', true);
      getZones()[index].baseFlipH = !!val;
      preview();
    };

    window.setZoneBaseFlipV = function setZoneBaseFlipV(index, val) {
      pushZoneUndo('Set base flip V', true);
      getZones()[index].baseFlipV = !!val;
      preview();
    };

    window.setZoneBaseScale = function setZoneBaseScale(index, val) {
      pushZoneUndo('Set base scale', true);
      const zone = getZones()[index];
      let v = parseFloat(val) || 1.0;
      v = roundToStep(v, SCALE_STEP);
      v = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));
      if (window.SPBBaseSpecScaleLink) window.SPBBaseSpecScaleLink.applyBaseScale(zone, v);
      else {
        zone.baseScale = v;
        if (zone.specScaleMode !== 'independent') {
          zone.specScaleMode = 'match';
          zone.specScale = v;
        }
      }
      const label = document.getElementById('detBaseScaleVal' + index);
      if (label) label.textContent = zone.baseScale.toFixed(2) + 'x';
      syncRange('setZoneBaseScale', index, Math.round(zone.baseScale * 100));
      preview();
    };

    window.stepZoneBaseScale = function stepZoneBaseScale(index, delta) {
      const cur = getZones()[index].baseScale || 1.0;
      window.setZoneBaseScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
    };

    window.resetZoneBaseScale = function resetZoneBaseScale(index) {
      pushZoneUndo('Reset base scale');
      const zone = getZones()[index];
      if (window.SPBBaseSpecScaleLink) window.SPBBaseSpecScaleLink.applyBaseScale(zone, 1.0);
      else zone.baseScale = 1.0;
      render();
      preview();
    };

    window.setZoneBaseColorScale = function setZoneBaseColorScale(index, val) {
      pushZoneUndo('Set base color scale', true);
      const zone = getZones()[index];
      let v = parseFloat(val) || 1.0;
      v = roundToStep(v, SCALE_STEP);
      zone.baseColorScale = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));
      const label = document.getElementById('detBaseColorScaleVal' + index);
      if (label) label.textContent = zone.baseColorScale.toFixed(2) + 'x';
      syncRange('setZoneBaseColorScale', index, Math.round(zone.baseColorScale * 100));
      preview();
    };

    window.stepZoneBaseColorScale = function stepZoneBaseColorScale(index, delta) {
      const cur = getZones()[index].baseColorScale || 1.0;
      window.setZoneBaseColorScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
    };

    window.resetZoneBaseColorScale = function resetZoneBaseColorScale(index) {
      pushZoneUndo('Reset base color scale');
      getZones()[index].baseColorScale = 1.0;
      render();
      preview();
    };

    window.setZoneBaseColorRotation = function setZoneBaseColorRotation(index, val) {
      pushZoneUndo('Set base color rotation', true);
      const v = Math.round(Math.max(0, Math.min(359, parseInt(val, 10) || 0)) / 5) * 5;
      getZones()[index].baseColorRotation = v;
      const input = document.getElementById('detBaseColorRotVal' + index);
      if (input) input.value = v;
      syncRange('setZoneBaseColorRotation', index, v);
      preview();
    };

    window.stepZoneBaseColorRotation = function stepZoneBaseColorRotation(index, delta) {
      const cur = getZones()[index].baseColorRotation ?? 0;
      window.setZoneBaseColorRotation(index, cur + delta * 5);
    };

    window.resetZoneBaseColorRotation = function resetZoneBaseColorRotation(index) {
      pushZoneUndo('Reset base color rotation');
      getZones()[index].baseColorRotation = 0;
      render();
      preview();
    };

    window.setZoneSpecRotation = function setZoneSpecRotation(index, val) {
      pushZoneUndo('Set spec rotation', true);
      const v = Math.round(Math.max(0, Math.min(359, parseInt(val, 10) || 0)) / 5) * 5;
      getZones()[index].specRotation = v;
      const input = document.getElementById('detSpecRotVal' + index);
      if (input) input.value = v;
      syncRange('setZoneSpecRotation', index, v);
      preview();
    };

    window.stepZoneSpecRotation = function stepZoneSpecRotation(index, delta) {
      const cur = getZones()[index].specRotation ?? 0;
      window.setZoneSpecRotation(index, cur + delta * 5);
    };

    window.resetZoneSpecRotation = function resetZoneSpecRotation(index) {
      window.setZoneSpecRotation(index, 0);
    };

    window.setZoneSpecScale = function setZoneSpecScale(index, val) {
      pushZoneUndo('Set spec scale', true);
      const zone = getZones()[index];
      let v = parseFloat(val) || 1.0;
      v = roundToStep(v, SCALE_STEP);
      if (window.SPBBaseSpecScaleLink) window.SPBBaseSpecScaleLink.applySpecScale(zone, v);
      else {
        zone.specScale = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));
        zone.specScaleMode = 'independent';
      }
      const label = document.getElementById('detSpecScaleVal' + index);
      if (label) label.textContent = zone.specScale.toFixed(2) + 'x';
      syncRange('setZoneSpecScale', index, Math.round(zone.specScale * 100));
      preview();
    };

    window.stepZoneSpecScale = function stepZoneSpecScale(index, delta) {
      const zone = getZones()[index];
      const cur = window.SPBBaseSpecScaleLink
        ? window.SPBBaseSpecScaleLink.resolve(zone)
        : (zone.specScale || 1.0);
      window.setZoneSpecScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
    };

    window.resetZoneSpecScale = function resetZoneSpecScale(index) {
      pushZoneUndo('Reset spec scale');
      const zone = getZones()[index];
      if (window.SPBBaseSpecScaleLink) window.SPBBaseSpecScaleLink.setIndependent(zone, false);
      else {
        zone.specScaleMode = 'match';
        zone.specScale = zone.baseScale ?? 1.0;
      }
      render();
      preview();
    };

    window.matchZoneSpecToBase = function matchZoneSpecToBase(index) {
      pushZoneUndo('Align spec with base');
      const zone = getZones()[index];
      zone.specRotation = zone.baseRotation ?? 0;
      zone.specScale = zone.baseScale ?? 1.0;
      zone.specScaleMode = 'match';
      render();
      preview();
    };

    window.matchZoneColorToBase = function matchZoneColorToBase(index) {
      pushZoneUndo('Align color with base');
      const zone = getZones()[index];
      zone.baseColorRotation = zone.baseRotation ?? 0;
      zone.baseColorScale = zone.baseScale ?? 1.0;
      render();
      preview();
    };

    window.matchZoneAllTransformsToBase = function matchZoneAllTransformsToBase(index) {
      pushZoneUndo('Align color and spec with base');
      const zone = getZones()[index];
      zone.baseColorRotation = zone.baseRotation ?? 0;
      zone.baseColorScale = zone.baseScale ?? 1.0;
      zone.specRotation = zone.baseRotation ?? 0;
      zone.specScale = zone.baseScale ?? 1.0;
      zone.specScaleMode = 'match';
      render();
      preview();
    };

    window.matchZoneSpecToColor = function matchZoneSpecToColor(index) {
      pushZoneUndo('Align spec with color');
      const zone = getZones()[index];
      zone.specRotation = zone.baseColorRotation ?? 0;
      zone.specScale = zone.baseColorScale ?? 1.0;
      zone.specScaleMode = 'independent';
      render();
      preview();
    };
  }

  window.SPBZoneBaseMaterialControls = { install };
})();
