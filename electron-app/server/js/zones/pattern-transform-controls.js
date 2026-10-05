'use strict';

(function () {
  const SCALE_STEP = 0.05;
  const SCALE_PATTERN_MIN = 0.10;
  const SCALE_PATTERN_MAX = 4.0;
  const MAX_PATTERN_LAYERS_PER_ZONE = 5;
  const MAX_PATTERN_STACK_LAYERS = MAX_PATTERN_LAYERS_PER_ZONE - 1;
  const MATERIAL_CONTROLS = {
    hue: { zone: 'patternHueShift', layer: 'hueShift', label: 'Hue', min: -180, max: 180, step: 1, unit: '°', tip: 'Shift only the pattern artwork around the color wheel. Overlay mode uses this color; Blend keeps the underlying paint color.' },
    saturation: { zone: 'patternSaturation', layer: 'saturation', label: 'Saturation', min: -100, max: 100, step: 5, unit: '%', tip: 'Change only the pattern artwork color intensity. -100% is grayscale, 0% is its original color, +100% is fully saturated. Applies in Overlay mode.' },
    spec: { zone: 'patternSpecOpacity', layer: 'specOpacity', label: 'Spec amount', min: 0, max: 100, step: 5, unit: '%', tip: 'Starts at 0% to preserve the existing base spec. Increase to reveal this pattern’s spec: 50% mixes both equally; 100% replaces Metallic, Roughness and Clearcoat in this zone. Uses the pattern Scale, Rotate and placement controls. Independent of paint Opacity and Strength.' }
  };

  window.renderPatternMaterialControls = function (index, zone, layerIdx = -1) {
    const target = layerIdx < 0 ? zone : zone.patternStack[layerIdx];
    const blend = zone.patternPaintMode === 'blend';
    const html = Object.entries(MATERIAL_CONTROLS).map(([key, def]) => {
      const value = Number(target[layerIdx < 0 ? def.zone : def.layer] ?? 0);
      const disabled = blend && key !== 'spec' ? 'disabled' : '';
      const address = `${index}:${layerIdx}:${key}`;
      const label = `${layerIdx < 0 ? 'Pattern' : 'Pattern ' + (layerIdx + 2)} ${key === 'spec' ? 'spec amount' : key}`;
      const setter = `setPatternMaterialControl(${index},${layerIdx},'${key}',`;
      return `<div class="stack-control-group" data-pattern-material-control="${address}" title="${def.tip}">
        <span class="stack-label-mini">${def.label}</span>
        <button type="button" class="btn btn-sm stack-step-btn" ${disabled} onclick="event.stopPropagation();stepPatternMaterialControl(${index},${layerIdx},'${key}',-1)" aria-label="Decrease ${label}">−</button>
        <input class="stack-slider" type="range" min="${def.min}" max="${def.max}" step="${def.step}" value="${value}" ${disabled} aria-label="${label}" title="${def.tip}" oninput="${setter}this.value)">
        <button type="button" class="btn btn-sm stack-step-btn" ${disabled} onclick="event.stopPropagation();stepPatternMaterialControl(${index},${layerIdx},'${key}',1)" aria-label="Increase ${label}">+</button>
        <span class="stack-val">${value}${def.unit}</span>
        <button type="button" class="btn btn-sm" ${disabled} onclick="event.stopPropagation();${setter}0)" aria-label="Reset ${label}" title="Reset to 0${def.unit}">↺</button></div>`;
    }).join('');
    return html + `<div style="font-size:10px;line-height:1.5;color:var(--text-dim);padding:2px 6px 7px;">${blend ? 'Blend uses pattern shading and keeps paint color. Hue/Saturation apply in Overlay mode.<br>' : ''}Spec starts at 0% to keep your base material. Pattern and spec share Scale and Rotate.</div>`;
  };

  function roundToStep(val, step) {
    return Math.round(val / step) * step;
  }

  function preview() {
    if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
  }

  function render() {
    if (typeof window.renderZones === 'function') window.renderZones();
  }

  function placement() {
    if (typeof window.applyPlacementPatternTransform === 'function') window.applyPlacementPatternTransform();
  }

  function syncRangeStarts(fnName, index, value) {
    document.querySelectorAll(`input[type="range"][oninput^="${fnName}(${index},"]`).forEach(sl => { sl.value = value; });
  }

  function patternLayer(zone, layerIdx) {
    return zone && zone.patternStack && zone.patternStack[layerIdx];
  }

  function patternLayerRow(zoneIdx, layerIdx) {
    return document.querySelector(`#zoneEditorFloat .pattern-layer-card[data-layer-idx="${layerIdx}"][data-zone-idx="${zoneIdx}"]`)
      || document.querySelector(`#zone-card-${zoneIdx} .pattern-layer-card[data-layer-idx="${layerIdx}"]`);
  }

  function installMaterialControls(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;

    window.setPatternMaterialControl = function (index, layerIdx, key, value) {
      const def = MATERIAL_CONTROLS[key], zone = getZones()[index];
      const target = layerIdx < 0 ? zone : patternLayer(zone, layerIdx);
      if (!def || !target) return;
      const number = Number(value);
      if (!Number.isFinite(number)) return;
      const next = Math.max(def.min, Math.min(def.max, number));
      const property = layerIdx < 0 ? def.zone : def.layer;
      if (Number(target[property] ?? 0) === next) return;
      pushZoneUndo('Pattern ' + def.label.toLowerCase(), true);
      target[property] = next;
      document.querySelectorAll(`[data-pattern-material-control="${index}:${layerIdx}:${key}"]`).forEach(row => {
        row.querySelector('input').value = next;
        row.querySelector('.stack-val').textContent = next + def.unit;
      });
      preview();
    };
    window.stepPatternMaterialControl = function (index, layerIdx, key, direction) {
      const def = MATERIAL_CONTROLS[key], zone = getZones()[index];
      const target = layerIdx < 0 ? zone : patternLayer(zone, layerIdx);
      if (!def || !target) return;
      window.setPatternMaterialControl(index, layerIdx, key,
        Number(target[layerIdx < 0 ? def.zone : def.layer] ?? 0) + def.step * direction);
    };
  }

  function install(deps) {
    installMaterialControls(deps);
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const pushZoneUndoCoalesced = deps.pushZoneUndoCoalesced || pushZoneUndo;
    const showToast = deps.showToast || window.showToast;

    window.setZonePatternSpecMult = function setZonePatternSpecMult(index, val) {
      pushZoneUndo('Set pattern strength', true);
      const zone = getZones()[index];
      zone.patternSpecMult = Math.max(0, Math.min(2, (!Number.isNaN(parseInt(val, 10)) ? parseInt(val, 10) : 100) / 100));
      const label = document.getElementById('detPatStrVal' + index);
      if (label) label.textContent = Math.round(zone.patternSpecMult * 100) + '%';
      preview();
    };

    window.stepZonePatternSpecMult = function stepZonePatternSpecMult(index, delta) {
      const cur = Math.round((getZones()[index].patternSpecMult ?? 1) * 100);
      window.setZonePatternSpecMult(index, Math.max(0, Math.min(200, cur + delta * 5)));
    };

    window.setZonePatternOpacity = function setZonePatternOpacity(index, val) {
      if (typeof index !== 'number' || index < 0 || index >= getZones().length) return;
      pushZoneUndo('Pattern opacity', true);
      const parsed = parseInt(val, 10);
      const v = Math.max(0, Math.min(100, Number.isFinite(parsed) ? parsed : 100));
      getZones()[index].patternOpacity = v;
      const label = document.getElementById('detPatOpVal' + index) || document.getElementById('patOpVal' + index);
      if (label) label.textContent = v + '%';
      preview();
    };

    window.stepZonePatternOpacity = function stepZonePatternOpacity(index, delta) {
      const cur = getZones()[index].patternOpacity ?? 100;
      window.setZonePatternOpacity(index, Math.max(0, Math.min(100, cur + delta * 5)));
    };

    window.setZonePatternOffsetX = function setZonePatternOffsetX(index, val) {
      pushZoneUndo('Set pattern offset X', true);
      const v = Math.max(0, Math.min(1, Number(val) / 100));
      getZones()[index].patternOffsetX = v;
      const pct = Math.round(v * 100) + '%';
      const label = document.getElementById('patPosXVal' + index);
      if (label) label.textContent = pct;
      const panel = document.getElementById('zoneEditorFloat');
      if (panel) {
        const span = panel.querySelector('#detPatPosXVal' + index);
        if (span) span.textContent = pct;
      }
      preview();
      placement();
    };

    window.setZonePatternOffsetY = function setZonePatternOffsetY(index, val) {
      pushZoneUndo('Set pattern offset Y', true);
      const v = Math.max(0, Math.min(1, Number(val) / 100));
      getZones()[index].patternOffsetY = v;
      const pct = Math.round(v * 100) + '%';
      const label = document.getElementById('patPosYVal' + index);
      if (label) label.textContent = pct;
      const panel = document.getElementById('zoneEditorFloat');
      if (panel) {
        const span = panel.querySelector('#detPatPosYVal' + index);
        if (span) span.textContent = pct;
      }
      preview();
      placement();
    };

    window.stepZonePatternOffsetX = function stepZonePatternOffsetX(index, delta) {
      const cur = Math.round((getZones()[index].patternOffsetX ?? 0.5) * 100);
      window.setZonePatternOffsetX(index, Math.max(0, Math.min(100, cur + delta)));
    };

    window.stepZonePatternOffsetY = function stepZonePatternOffsetY(index, delta) {
      const cur = Math.round((getZones()[index].patternOffsetY ?? 0.5) * 100);
      window.setZonePatternOffsetY(index, Math.max(0, Math.min(100, cur + delta)));
    };

    window.setZonePatternFlipH = function setZonePatternFlipH(index, val) {
      pushZoneUndo('Set pattern flip H', true);
      getZones()[index].patternFlipH = !!val;
      preview();
      placement();
    };

    window.setZonePatternFlipV = function setZonePatternFlipV(index, val) {
      pushZoneUndo('Set pattern flip V', true);
      getZones()[index].patternFlipV = !!val;
      preview();
      placement();
    };

    window.setZoneScale = function setZoneScale(index, val) {
      if (typeof index !== 'number' || index < 0 || index >= getZones().length) {
        console.warn('[SPB] setZoneScale: invalid zone index', index);
        return;
      }
      pushZoneUndo('Set scale', true);
      const zone = getZones()[index];
      let v = parseFloat(val) || 1.0;
      if (Number.isNaN(v)) v = 1.0;
      v = roundToStep(v, SCALE_STEP);
      zone.scale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
      const label = document.getElementById('detScaleVal' + index) || document.getElementById('scaleVal' + index);
      if (label) label.textContent = zone.scale.toFixed(2) + 'x';
      syncRangeStarts('setZoneScale', index, Math.round(zone.scale * 100));
      preview();
      placement();
    };

    window.stepZoneScale = function stepZoneScale(index, delta) {
      const cur = getZones()[index].scale || 1.0;
      window.setZoneScale(index, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
    };

    window.resetZoneScale = function resetZoneScale(index) {
      pushZoneUndo('Reset scale');
      getZones()[index].scale = 1.0;
      render();
      preview();
    };

    window.setZoneRotation = function setZoneRotation(index, val) {
      pushZoneUndo('Set rotation', true);
      const v = Math.max(0, Math.min(359, parseInt(val, 10) || 0));
      getZones()[index].rotation = v;
      ['detRotVal', 'rotVal'].forEach(prefix => {
        const el = document.getElementById(prefix + index);
        if (el) el.value = v;
      });
      syncRangeStarts('setZoneRotation', index, v);
      preview();
      placement();
    };

    window.stepZoneRotation = function stepZoneRotation(index, delta) {
      const cur = getZones()[index].rotation || 0;
      window.setZoneRotation(index, Math.max(0, Math.min(359, cur + delta)));
    };

    window.resetZoneRotation = function resetZoneRotation(index) {
      pushZoneUndo('Reset pattern rotation');
      getZones()[index].rotation = 0;
      render();
      preview();
    };

    window.addPatternLayer = function addPatternLayer(zoneIdx) {
      pushZoneUndo('Add pattern layer');
      const zone = getZones()[zoneIdx];
      if (!zone) return;
      if (!zone.patternStack) zone.patternStack = [];
      if (zone.patternStack.length >= MAX_PATTERN_STACK_LAYERS) {
        if (typeof showToast === 'function') showToast(`Max ${MAX_PATTERN_LAYERS_PER_ZONE} patterns (Pattern 1 + ${MAX_PATTERN_STACK_LAYERS} layers)`, true);
        return;
      }
      zone.patternStack.push({ id: 'none', opacity: 100, scale: 1.0, rotation: 0, blendMode: 'normal', offsetX: 0.5, offsetY: 0.5 });
      render();
      preview();
    };

    window.removePatternLayer = function removePatternLayer(zoneIdx, layerIdx) {
      pushZoneUndo('Remove pattern layer ' + (layerIdx + 1));
      const zone = getZones()[zoneIdx];
      if (!zone || !zone.patternStack) return;
      zone.patternStack.splice(layerIdx, 1);
      render();
      preview();
    };

    window.setPatternLayerId = function setPatternLayerId(zoneIdx, layerIdx, val) {
      pushZoneUndo('Set pattern layer ' + (layerIdx + 1) + ': ' + val);
      const layer = patternLayer(getZones()[zoneIdx], layerIdx);
      if (!layer) return;
      layer.id = val;
      render();
      preview();
    };

    window.setPatternLayerOpacity = function setPatternLayerOpacity(zoneIdx, layerIdx, val) {
      pushZoneUndoCoalesced('Pattern layer opacity ' + (layerIdx + 1));
      const layer = patternLayer(getZones()[zoneIdx], layerIdx);
      if (!layer) return;
      const parsed = parseInt(val, 10);
      const v = Math.max(0, Math.min(100, Number.isFinite(parsed) ? parsed : 100));
      layer.opacity = v;
      const row = patternLayerRow(zoneIdx, layerIdx);
      const span = row && row.querySelectorAll('.stack-control-group')[0]?.querySelector('.stack-val');
      if (span) span.textContent = v + '%';
      preview();
    };

    window.stepPatternLayerOpacity = function stepPatternLayerOpacity(zoneIdx, layerIdx, delta) {
      const cur = patternLayer(getZones()[zoneIdx], layerIdx)?.opacity ?? 100;
      window.setPatternLayerOpacity(zoneIdx, layerIdx, Math.max(0, Math.min(100, cur + delta * 5)));
    };

    window.setPatternLayerScale = function setPatternLayerScale(zoneIdx, layerIdx, val) {
      pushZoneUndoCoalesced('Pattern layer scale ' + (layerIdx + 1));
      const layer = patternLayer(getZones()[zoneIdx], layerIdx);
      if (!layer) return;
      let v = parseFloat(val) || 1.0;
      v = roundToStep(v, SCALE_STEP);
      layer.scale = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, v));
      const row = patternLayerRow(zoneIdx, layerIdx);
      const scaleGroup = row && row.querySelectorAll('.stack-control-group')[1];
      if (scaleGroup) {
        const span = scaleGroup.querySelector('.stack-val');
        if (span) span.textContent = layer.scale.toFixed(2) + 'x';
        const scaleInput = scaleGroup.querySelector('input[type="range"]');
        if (scaleInput) scaleInput.value = Math.round(layer.scale * 100);
      }
      preview();
    };

    window.stepPatternLayerScale = function stepPatternLayerScale(zoneIdx, layerIdx, delta) {
      const cur = patternLayer(getZones()[zoneIdx], layerIdx)?.scale || 1.0;
      window.setPatternLayerScale(zoneIdx, layerIdx, roundToStep(cur, SCALE_STEP) + delta * SCALE_STEP);
    };

    window.setPatternLayerRotation = function setPatternLayerRotation(zoneIdx, layerIdx, val) {
      pushZoneUndoCoalesced('Rotate pattern layer ' + (layerIdx + 1));
      const layer = patternLayer(getZones()[zoneIdx], layerIdx);
      if (!layer) return;
      const intVal = parseInt(val, 10) || 0;
      layer.rotation = intVal;
      const row = patternLayerRow(zoneIdx, layerIdx);
      const rotGroup = row && row.querySelectorAll('.stack-control-group')[2];
      if (rotGroup) {
        const slider = rotGroup.querySelector('input[type="range"]');
        const numInput = rotGroup.querySelector('input[type="number"]');
        if (slider && slider !== document.activeElement) slider.value = intVal;
        if (numInput && numInput !== document.activeElement) numInput.value = intVal;
      }
      preview();
    };

    window.stepPatternLayerRotation = function stepPatternLayerRotation(zoneIdx, layerIdx, delta) {
      const cur = patternLayer(getZones()[zoneIdx], layerIdx)?.rotation || 0;
      window.setPatternLayerRotation(zoneIdx, layerIdx, Math.max(0, Math.min(359, cur + delta)));
    };

    window.setPatternLayerBlend = function setPatternLayerBlend(zoneIdx, layerIdx, val) {
      pushZoneUndoCoalesced('Pattern layer blend ' + (layerIdx + 1));
      const layer = patternLayer(getZones()[zoneIdx], layerIdx);
      if (!layer) return;
      layer.blendMode = val;
      preview();
    };
  }

  window.SPBZonePatternTransformControls = { install, installMaterialControls };

  // Owner 2026-09-08: the live page loads this module but still uses legacy
  // transform setters. Install the new material handlers without replacing those.
  function installLiveMaterialControls() {
    installMaterialControls({ getZones: () => zones, pushZoneUndo: (...args) => pushZoneUndo(...args) });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installLiveMaterialControls, { once: true });
  } else {
    installLiveMaterialControls();
  }
})();
