(function(global) {
  'use strict';

  function installZoneBaseColorControls(deps) {
    deps = deps || {};
    const getZones = deps.getZones || function() { return []; };
    const getDocument = deps.getDocument || function() { return global.document; };
    const pushZoneUndo = deps.pushZoneUndo || function() {};
    const renderZoneDetail = deps.renderZoneDetail || function() {};
    const renderZones = deps.renderZones || function() {};
    const triggerPreviewRender = deps.triggerPreviewRender || function() {};
    const showToast = deps.showToast || function() {};

    function _zone(index) {
      const zones = getZones();
      return zones && zones[index] ? zones[index] : null;
    }

    function setZoneBaseColorMode(index, value) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('Set base color mode', true);
      const mode = (value === 'solid' || value === 'special' || value === 'gradient' || value === 'finish') ? value : 'source';
      zone.baseColorMode = mode;
      zone.baseColorModeExplicit = true; // Match the live Base Color controller.
      zone._autoBaseColorFill = false;
      zone._scopedBrushAutoBaseColor = false;
      if (!zone.baseColor) zone.baseColor = '#ffffff';
      if (zone.baseColorStrength == null) zone.baseColorStrength = 1;
      if (mode !== 'special') zone.baseColorSource = null;
      if (mode === 'gradient' && (!zone.gradientStops || zone.gradientStops.length < 2)) {
        zone.gradientStops = [
          { pos: 0, color: '#000000' },
          { pos: 100, color: '#ffffff' }
        ];
        zone.gradientDirection = 'horizontal';
      }
      renderZoneDetail(index);
      triggerPreviewRender();
    }

    function _normalizeBaseGradientStopColorForPayload(color) {
      if (typeof color === 'string') {
        let hex = color.trim();
        if (/^#[0-9a-fA-F]{3}$/.test(hex)) {
          hex = '#' + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3];
        }
        if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
          return [
            parseInt(hex.slice(1, 3), 16) / 255,
            parseInt(hex.slice(3, 5), 16) / 255,
            parseInt(hex.slice(5, 7), 16) / 255
          ];
        }
        return null;
      }
      if (Array.isArray(color) && color.length >= 3) {
        const rgb = color.slice(0, 3).map(Number);
        if (rgb.some((value) => !Number.isFinite(value))) return null;
        const scale = rgb.some((value) => value > 1) ? 255 : 1;
        return rgb.map((value) => Math.max(0, Math.min(1, value / scale)));
      }
      return null;
    }

    function normalizeBaseGradientStopsForPayload(stops) {
      if (!Array.isArray(stops)) return [];
      return stops.map(function(stop) {
        const rawPos = Number(stop && stop.pos);
        const rawColor = _normalizeBaseGradientStopColorForPayload(stop && stop.color);
        if (!Number.isFinite(rawPos) || !rawColor) return null;
        const pos = rawPos > 1 ? rawPos / 100 : rawPos;
        return {
          pos: Math.max(0, Math.min(1, pos)),
          color: rawColor
        };
      }).filter(Boolean).sort(function(a, b) { return a.pos - b.pos; });
    }

    function _buildGradientEditorHTML(zoneIdx, zone) {
      const stops = zone.gradientStops || [{ pos: 0, color: '#000000' }, { pos: 100, color: '#ffffff' }];
      const dir = zone.gradientDirection || 'horizontal';
      const cssGrad = _buildCSSGradient(stops, dir);
      let stopsHTML = '';
      for (let s = 0; s < stops.length; s += 1) {
        const canDelete = stops.length > 2;
        stopsHTML += `<div class="gradient-stop-row" style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
            <input type="color" value="${stops[s].color}" onchange="setGradientStopColor(${zoneIdx}, ${s}, this.value)" style="width:28px;height:22px;padding:0;border:1px solid var(--border);border-radius:3px;cursor:pointer;">
            <input type="range" min="0" max="100" step="1" value="${stops[s].pos}" oninput="setGradientStopPos(${zoneIdx}, ${s}, this.value)" class="stack-slider" style="width:80px;" title="Position ${stops[s].pos}%">
            <span class="stack-val" style="min-width:28px;font-size:9px;">${stops[s].pos}%</span>
            ${canDelete ? `<button class="btn btn-sm" onclick="event.stopPropagation(); removeGradientStop(${zoneIdx}, ${s})" title="Remove stop" style="padding:0 4px;font-size:9px;color:#ff5555;border-color:#ff555533;">x</button>` : ''}
        </div>`;
      }
      return `</div>
        <div class="gradient-editor" style="width:100%;margin-top:4px;">
            <div class="gradient-bar" id="gradBar_${zoneIdx}" onclick="addGradientStopAtClick(${zoneIdx}, event)" title="Click to add a color stop" style="width:100%;height:20px;border-radius:4px;border:1px solid var(--border);cursor:crosshair;background:${cssGrad};margin-bottom:6px;"></div>
            <div class="gradient-stops">${stopsHTML}</div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:4px;flex-wrap:wrap;">
                <span class="stack-label-mini" style="min-width:55px;">Direction</span>
                <select class="mini-select" style="min-width:140px;flex:1;max-width:180px;" onchange="setGradientDirection(${zoneIdx}, this.value)">
                    <option value="horizontal" ${dir === 'horizontal' ? 'selected' : ''}>Horizontal</option>
                    <option value="vertical" ${dir === 'vertical' ? 'selected' : ''}>Vertical</option>
                    <option value="diagonal_down" ${dir === 'diagonal_down' ? 'selected' : ''}>Diagonal Down</option>
                    <option value="diagonal_up" ${dir === 'diagonal_up' ? 'selected' : ''}>Diagonal Up</option>
                    <option value="radial" ${dir === 'radial' ? 'selected' : ''}>Radial</option>
                    <option value="angular" ${dir === 'angular' ? 'selected' : ''}>Angular</option>
                </select>
                ${stops.length < 10 ? `<button class="btn btn-sm" onclick="event.stopPropagation(); addGradientStop(${zoneIdx})" style="padding:2px 8px;font-size:9px;border-color:var(--accent-blue);color:var(--accent-blue);">+ Add Stop</button>` : ''}
            </div>
        </div>
    <div style="display:flex; align-items:center; gap:8px; width:100%; flex-wrap:wrap;">`;
    }

    function _buildCSSGradient(stops, direction) {
      if (!stops || stops.length < 2) return 'linear-gradient(to right, #000, #fff)';
      const sorted = stops.slice().sort((a, b) => a.pos - b.pos);
      const colorStops = sorted.map((stop) => `${stop.color} ${stop.pos}%`).join(', ');
      if (direction === 'radial') return `radial-gradient(circle, ${colorStops})`;
      if (direction === 'angular') return `conic-gradient(from 0deg, ${colorStops})`;
      const dirMap = {
        horizontal: 'to right',
        vertical: 'to bottom',
        diagonal_down: 'to bottom right',
        diagonal_up: 'to top right'
      };
      return `linear-gradient(${dirMap[direction] || 'to right'}, ${colorStops})`;
    }

    function setGradientStopColor(zoneIdx, stopIdx, color) {
      const zone = _zone(zoneIdx);
      pushZoneUndo('', true);
      if (!zone || !zone.gradientStops || !zone.gradientStops[stopIdx]) return;
      zone.gradientStops[stopIdx].color = color;
      _refreshGradientBar(zoneIdx);
      triggerPreviewRender();
    }

    function setGradientStopPos(zoneIdx, stopIdx, val) {
      const zone = _zone(zoneIdx);
      pushZoneUndo('', true);
      if (!zone || !zone.gradientStops || !zone.gradientStops[stopIdx]) return;
      zone.gradientStops[stopIdx].pos = Math.max(0, Math.min(100, parseInt(val, 10) || 0));
      _refreshGradientBar(zoneIdx);
      triggerPreviewRender();
    }

    function setGradientDirection(zoneIdx, dir) {
      const zone = _zone(zoneIdx);
      if (!zone) return;
      pushZoneUndo('Set gradient direction', true);
      zone.gradientDirection = dir;
      _refreshGradientBar(zoneIdx);
      triggerPreviewRender();
    }

    function addGradientStop(zoneIdx) {
      const zone = _zone(zoneIdx);
      if (!zone) return;
      pushZoneUndo('Add gradient stop', true);
      const stops = zone.gradientStops || [];
      if (stops.length >= 10) {
        showToast('Maximum 10 gradient stops');
        return;
      }
      const last = stops[stops.length - 1] || { pos: 100, color: '#ffffff' };
      const prev = stops.length >= 2 ? stops[stops.length - 2] : { pos: 0, color: '#000000' };
      const midPos = Math.round((prev.pos + last.pos) / 2);
      stops.push({ pos: midPos, color: '#888888' });
      zone.gradientStops = stops;
      renderZoneDetail(zoneIdx);
      triggerPreviewRender();
    }

    function addGradientStopAtClick(zoneIdx, event) {
      const zone = _zone(zoneIdx);
      if (!zone) return;
      const stops = zone.gradientStops || [];
      if (stops.length >= 10) {
        showToast('Maximum 10 gradient stops');
        return;
      }
      const bar = event.currentTarget;
      const rect = bar.getBoundingClientRect();
      const pos = Math.round(Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100)));
      pushZoneUndo('Add gradient stop', true);
      stops.push({ pos: pos, color: '#888888' });
      zone.gradientStops = stops;
      renderZoneDetail(zoneIdx);
      triggerPreviewRender();
    }

    function removeGradientStop(zoneIdx, stopIdx) {
      const zone = _zone(zoneIdx);
      if (!zone) return;
      const stops = zone.gradientStops || [];
      if (stops.length <= 2) return;
      pushZoneUndo('Remove gradient stop', true);
      stops.splice(stopIdx, 1);
      zone.gradientStops = stops;
      renderZoneDetail(zoneIdx);
      triggerPreviewRender();
    }

    function _refreshGradientBar(zoneIdx) {
      const doc = getDocument();
      const zone = _zone(zoneIdx);
      const bar = doc && doc.getElementById ? doc.getElementById('gradBar_' + zoneIdx) : null;
      if (!bar || !zone) return;
      const stops = zone.gradientStops || [];
      const dir = zone.gradientDirection || 'horizontal';
      bar.style.background = _buildCSSGradient(stops, dir);
    }

    function setZoneBaseColor(index, val) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('Set base color', true);
      val = (val || '').trim();
      if (val && !val.startsWith('#')) val = '#' + val;
      if (val && !/^#[0-9A-Fa-f]{6}$/.test(val)) {
        showToast('Enter a valid hex code like #FF3366', true);
        renderZoneDetail(index);
        return;
      }
      zone.baseColor = val || '#ffffff';
      // SPB-BASECOLOR-2026-06-02 (Codex finding): an explicit solid-color pick must
      // switch the zone to solid mode AND drop any auto-assigned "use the finish's
      // own color" source (mono:<finish>). Previously this only upgraded from
      // 'source', so a special/monolithic base — which defaultBaseColorToFinish
      // auto-sets to baseColorMode='special' + baseColorSource='mono:<finish>' — kept
      // rendering its OWN color and silently ignored the solid pick. Gradient mode is
      // left alone (it owns the stop editor, not this single-color field).
      if (zone.baseColorMode !== 'gradient') {
        zone.baseColorMode = 'solid';
        zone.baseColorSource = null;
      }
      zone._autoBaseColorFill = false;
      zone._scopedBrushAutoBaseColor = false;
      renderZoneDetail(index);
      triggerPreviewRender();
    }

    function setZoneBaseColorSource(index, val) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('Set base color source', true);
      const src = val && typeof val === 'string' ? (val.trim() || null) : null;
      zone.baseColorSource = src;
      if (src) zone.baseColorMode = 'special';
      zone._autoBaseColorFill = false;
      zone._scopedBrushAutoBaseColor = false;
      renderZoneDetail(index);
      triggerPreviewRender();
    }

    function setZoneBaseColorStrength(index, val) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('', true);
      const n = Math.max(0, Math.min(100, parseInt(val, 10) || 0));
      zone.baseColorStrength = n / 100;
      _setText('detBaseColorStrVal' + index, Math.round((zone.baseColorStrength ?? 1) * 100) + '%');
      triggerPreviewRender();
    }

    function stepZoneBaseColorStrength(index, delta) {
      const zone = _zone(index);
      if (!zone) return;
      const cur = Math.round((zone.baseColorStrength ?? 1) * 100);
      setZoneBaseColorStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
    }

    function setZoneAlignBaseColorWithBase(index, checked) {
      if (!_zone(index)) return;
      pushZoneUndo('Set align base color with base', true);
      _zone(index).alignBaseColorWithBase = !!checked;
      renderZones();
    }

    function setZoneBaseColorFitZone(index, enabled) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('Set base color fit-to-selection');
      zone.baseColorFitZone = !!enabled;
      triggerPreviewRender();
      showToast(enabled
        ? 'Fit-to-Selection ON - base color and spec will compress into your selected area'
        : 'Fit-to-Selection OFF - base will sample from full canvas');
    }

    function setZoneBaseHueOffset(index, val) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('', true);
      const n = Math.max(-180, Math.min(180, parseInt(val, 10) || 0));
      zone.baseHueOffset = n;
      _setText('detBaseHueVal' + index, n + String.fromCharCode(176));
      triggerPreviewRender();
    }

    function setZoneBaseSaturation(index, val) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('', true);
      const n = Math.max(-100, Math.min(100, parseInt(val, 10) || 0));
      zone.baseSaturationAdjust = n;
      _setText('detBaseSatVal' + index, n);
      triggerPreviewRender();
    }

    function setZoneBaseBrightness(index, val) {
      const zone = _zone(index);
      if (!zone) return;
      pushZoneUndo('', true);
      const n = Math.max(-100, Math.min(100, parseInt(val, 10) || 0));
      zone.baseBrightnessAdjust = n;
      _setText('detBaseBrightVal' + index, n);
      triggerPreviewRender();
    }

    function _setText(id, text) {
      const doc = getDocument();
      const direct = doc && doc.getElementById ? doc.getElementById(id) : null;
      if (direct) direct.textContent = text;
      const panel = doc && doc.getElementById ? doc.getElementById('zoneEditorFloat') : null;
      if (panel && panel.querySelector) {
        const nested = panel.querySelector('#' + id);
        if (nested) nested.textContent = text;
      }
    }

    global.setZoneBaseColorMode = setZoneBaseColorMode;
    global.normalizeBaseGradientStopsForPayload = normalizeBaseGradientStopsForPayload;
    global._buildGradientEditorHTML = _buildGradientEditorHTML;
    global.setGradientStopColor = setGradientStopColor;
    global.setGradientStopPos = setGradientStopPos;
    global.setGradientDirection = setGradientDirection;
    global.addGradientStop = addGradientStop;
    global.addGradientStopAtClick = addGradientStopAtClick;
    global.removeGradientStop = removeGradientStop;
    global.setZoneBaseColor = setZoneBaseColor;
    global.setZoneBaseColorSource = setZoneBaseColorSource;
    global.setZoneBaseColorStrength = setZoneBaseColorStrength;
    global.stepZoneBaseColorStrength = stepZoneBaseColorStrength;
    global.setZoneAlignBaseColorWithBase = setZoneAlignBaseColorWithBase;
    global.setZoneBaseColorFitZone = setZoneBaseColorFitZone;
    global.setZoneBaseHueOffset = setZoneBaseHueOffset;
    global.setZoneBaseSaturation = setZoneBaseSaturation;
    global.setZoneBaseBrightness = setZoneBaseBrightness;
  }

  global.SPBZoneBaseColorControls = {
    install: installZoneBaseColorControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
