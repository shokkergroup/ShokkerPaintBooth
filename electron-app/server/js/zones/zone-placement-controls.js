(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getDocument = deps.getDocument || function () { return global.document; };
    var getZones = deps.getZones || function () { return []; };
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return -1; };
    var setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
    var getPlacementLayer = deps.getPlacementLayer || function () { return 'none'; };
    var setPlacementLayerValue = deps.setPlacementLayerValue || function () {};
    var getShokkerApi = deps.getShokkerApi || function () { return global.ShokkerAPI; };
    var escapeHtml = deps.escapeHtml || function (value) {
      return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    };
    var pushZoneUndo = deps.pushZoneUndo || function () {};
    var renderZones = deps.renderZones || function () {};
    var triggerPreviewRender = deps.triggerPreviewRender || function () {};
    var activateManualPlacement = deps.activateManualPlacement || function () {};
    var deactivateManualPlacement = deps.deactivateManualPlacement || function () {};

    var placementPatternRefetchTimer = null;
    var placementOverlayDragStart = null;

    function doc() {
      return getDocument() || {};
    }

    function zones() {
      return getZones() || [];
    }

    function isPlacementLayerTarget(layer) {
      return layer === 'pattern' || layer === 'second_base' || layer === 'third_base'
        || layer === 'fourth_base' || layer === 'fifth_base' || layer === 'base'
        || /^spec_pattern_\d+$/.test(String(layer || ''));
    }

    function setPlacementLayer(layer) {
      var nextLayer = isPlacementLayerTarget(layer) ? layer : 'none';
      setPlacementLayerValue(nextLayer);
      updatePlacementBanner();
      var cvs = doc().getElementById && doc().getElementById('paintCanvas');
      if (cvs) cvs.style.cursor = nextLayer !== 'none' ? 'grab' : '';
    }

    function getPlacementMode(zone, target) {
      var allZones = zones();
      var selectedIndex = getSelectedZoneIndex();
      var layer = getPlacementLayer();
      if (!zone) return 'normal';
      var manualActive = layer === target && selectedIndex >= 0 && allZones[selectedIndex] === zone;
      if (target === 'base') return manualActive ? 'manual' : 'normal';
      if (target === 'pattern') {
        if (manualActive) return 'manual';
        return zone.patternPlacement === 'fit' ? 'fit' : 'normal';
      }
      if (manualActive) return 'manual';
      if (target === 'second_base') return zone.secondBaseFitZone ? 'fit' : 'normal';
      if (target === 'third_base') return zone.thirdBaseFitZone ? 'fit' : 'normal';
      if (target === 'fourth_base') return zone.fourthBaseFitZone ? 'fit' : 'normal';
      if (target === 'fifth_base') return zone.fifthBaseFitZone ? 'fit' : 'normal';
      return 'normal';
    }

    function isPlacementOffsetLocked(zone, target) {
      return getPlacementMode(zone, target) === 'fit';
    }

    function placementOffsetControlAttrs(zone, target) {
      return isPlacementOffsetLocked(zone, target) ? 'disabled style="opacity:0.35;pointer-events:none;"' : '';
    }

    function placementOffsetValueAttrs(zone, target) {
      return isPlacementOffsetLocked(zone, target) ? 'style="opacity:0.35;"' : '';
    }

    function clearPlacementEditingState(index, target) {
      var zone = zones()[index];
      if (!zone) return;
      if (target === 'base' && zone.basePlacement === 'manual') zone.basePlacement = 'normal';
      if (target === 'pattern' && zone.patternPlacement === 'manual') zone.patternPlacement = 'normal';
    }

    function setPlacementMode(index, target, mode) {
      var allZones = zones();
      var zone = allZones[index];
      if (!zone) return;
      setSelectedZoneIndex(index);
      var nextMode = (mode === 'manual' || mode === 'fit') ? mode : 'normal';

      if (target === 'base') {
        zone.basePlacement = nextMode === 'manual' ? 'manual' : 'normal';
      } else if (target === 'pattern') {
        zone.patternPlacement = nextMode;
      } else if (target === 'second_base') {
        zone.secondBaseFitZone = nextMode === 'fit';
      } else if (target === 'third_base') {
        zone.thirdBaseFitZone = nextMode === 'fit';
      } else if (target === 'fourth_base') {
        zone.fourthBaseFitZone = nextMode === 'fit';
      } else if (target === 'fifth_base') {
        zone.fifthBaseFitZone = nextMode === 'fit';
      }

      if (nextMode === 'manual') {
        activateManualPlacement(index, target);
      } else {
        clearPlacementEditingState(index, target);
        if (getPlacementLayer() === target) {
          deactivateManualPlacement();
          setPlacementLayer('none');
        }
      }

      renderZones();
      triggerPreviewRender();
    }

    function renderPlacementModeButton(index, target, mode, label, active, title, tone) {
      var palette = {
        neutral: { border: '#3a4357', fg: '#d6dcef', bg: '#141b27' },
        cyan: { border: '#1d8ba3', fg: '#bff7ff', bg: '#0f2830' },
        gold: { border: '#8f6a11', fg: '#ffe7a0', bg: '#2b2210' }
      };
      var swatch = palette[tone] || palette.neutral;
      var border = active ? swatch.border : '#2c3240';
      var fg = active ? swatch.fg : '#9ea8bd';
      var bg = active ? swatch.bg : '#111723';
      return `<button type="button" class="btn btn-sm"
        onclick="event.stopPropagation(); setPlacementMode(${index}, '${target}', '${mode}')"
        title="${escapeHtml(title)}"
        style="padding:2px 7px;font-size:10px;border-color:${border};color:${fg};background:${bg};">${escapeHtml(label)}</button>`;
    }

    function renderPlacementModeControls(index, target, options) {
      var zone = zones()[index];
      if (!zone) return '';
      var opts = options || {};
      var mode = getPlacementMode(zone, target);
      var allowFit = !!opts.allowFit;
      var label = opts.label || 'Placement';
      var targetLabel = opts.targetLabel || 'this target';
      var centeredLabel = opts.centeredLabel || 'Centered';
      var manualLabel = opts.manualLabel || 'Edit on Template';
      var hint = mode === 'manual'
        ? 'Drag directly on the template. Use the top strip for quick rotate/flip while placement is active.'
        : 'Use the numeric X/Y controls below for fine tuning.';
      if (mode === 'fit') {
        hint = 'Fit to Zone is active, so template offsets are locked until you switch back to Centered or Edit on Template.';
      }
      var html = `<div class="zone-target-mode" style="margin: 6px 0; display:flex; gap:6px; align-items:flex-start; flex-wrap:wrap;">
        <label style="color:#aaa; font-size:11px; white-space:nowrap; padding-top:4px;">${escapeHtml(label)}:</label>
        <div style="display:flex; gap:4px; align-items:center; flex-wrap:wrap;">`;
      html += renderPlacementModeButton(index, target, 'normal', centeredLabel, mode === 'normal', `Use centered tiling plus the numeric controls for ${targetLabel}`, 'neutral');
      if (allowFit) {
        html += renderPlacementModeButton(index, target, 'fit', 'Fit to Zone', mode === 'fit', `Constrain ${targetLabel} to the current zone bounds`, 'gold');
      }
      html += renderPlacementModeButton(index, target, 'manual', manualLabel, mode === 'manual', `Drag ${targetLabel} directly on the template`, 'cyan');
      html += `</div>
        <div style="flex-basis:100%; font-size:9px; color:var(--text-dim); line-height:1.35;">${escapeHtml(hint)}</div>
    </div>`;
      return html;
    }

    function buildPlacementPatternUrl(zone, canvas) {
      var pat = zone.pattern && zone.pattern !== 'none' ? zone.pattern : null;
      var api = getShokkerApi();
      if (!pat || !canvas || canvas.width <= 0 || canvas.height <= 0 || !api || !api.baseUrl) return null;
      return api.baseUrl + '/api/pattern-layer?pattern=' + encodeURIComponent(pat)
        + '&w=' + canvas.width + '&h=' + canvas.height
        + '&scale=' + (zone.scale ?? 1) + '&rotation=' + (zone.rotation ?? 0)
        + '&flip_h=' + (zone.patternFlipH ? 1 : 0) + '&flip_v=' + (zone.patternFlipV ? 1 : 0)
        + '&seed=42';
    }

    function applyPlacementPatternTransform() {
      var img = doc().getElementById && doc().getElementById('placementPatternImg');
      var zone = zones()[getSelectedZoneIndex()];
      if (!img || !zone || getPlacementLayer() !== 'pattern') return;

      var ox = (0.5 - (zone.patternOffsetX ?? 0.5)) * 100;
      var oy = (0.5 - (zone.patternOffsetY ?? 0.5)) * 100;
      img.style.transform = `translate(${ox}%, ${oy}%)`;

      var canvas = doc().getElementById && doc().getElementById('paintCanvas');
      var newUrl = buildPlacementPatternUrl(zone, canvas);
      if (!newUrl || img._lastPlacementUrl === newUrl) return;

      clearTimeout(placementPatternRefetchTimer);
      placementPatternRefetchTimer = setTimeout(function () {
        var hint = doc().getElementById && doc().getElementById('placementMapOverlayHint');
        if (hint) {
          hint.style.display = 'flex';
          var msg = hint.querySelector && hint.querySelector('span:first-child');
          if (msg) msg.textContent = 'Loading pattern...';
        }
        img._lastPlacementUrl = newUrl;
        img.onload = function () {
          if (hint) hint.style.display = 'none';
          var activeZone = zones()[getSelectedZoneIndex()];
          if (activeZone) {
            img.style.transform = `translate(${(0.5 - (activeZone.patternOffsetX ?? 0.5)) * 100}%, ${(0.5 - (activeZone.patternOffsetY ?? 0.5)) * 100}%)`;
          }
        };
        img.src = newUrl;
      }, 120);
    }

    function updatePlacementBanner() {
      var d = doc();
      var banner = d.getElementById && d.getElementById('placementBanner');
      var label = d.getElementById && d.getElementById('placementBannerLabel');
      var overlay = d.getElementById && d.getElementById('placementMapOverlay');
      var hint = d.getElementById && d.getElementById('placementMapOverlayHint');
      var patternLayerDiv = d.getElementById && d.getElementById('placementPatternLayer');
      var patternImg = d.getElementById && d.getElementById('placementPatternImg');
      var layer = getPlacementLayer();
      if (!banner || !label) return;
      if (layer === 'none') {
        banner.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
        if (patternLayerDiv) patternLayerDiv.style.display = 'none';
        if (hint) hint.style.display = 'flex';
        return;
      }
      var names = { pattern: 'Primary pattern', second_base: '2nd base overlay', third_base: '3rd base overlay', fourth_base: '4th base overlay', fifth_base: '5th base overlay', base: 'Base (gradient/duo)' };
      label.textContent = names[layer] || layer;
      banner.style.display = 'flex';
      if (overlay) overlay.style.display = 'flex';
      var zone = zones()[getSelectedZoneIndex()];
      if (layer === 'pattern' && patternImg && zone) {
        var pat = zone.pattern && zone.pattern !== 'none' ? zone.pattern : null;
        var canvas = d.getElementById && d.getElementById('paintCanvas');
        var api = getShokkerApi();
        if (pat && canvas && canvas.width > 0 && canvas.height > 0 && api && api.baseUrl) {
          if (hint) {
            hint.style.display = 'flex';
            var loading = hint.querySelector && hint.querySelector('span:first-child');
            if (loading) loading.textContent = 'Loading pattern...';
          }
          if (patternLayerDiv) patternLayerDiv.style.display = 'block';
          var url = buildPlacementPatternUrl(zone, canvas) || (api.baseUrl + '/api/pattern-layer?pattern=' + encodeURIComponent(pat) + '&w=' + canvas.width + '&h=' + canvas.height + '&scale=1&rotation=0&seed=42');
          patternImg._lastPlacementUrl = url;
          patternImg.onload = function () {
            if (hint) hint.style.display = 'none';
            applyPlacementPatternTransform();
            setupPlacementOverlayDrag();
          };
          patternImg.onerror = function () {
            if (hint) {
              var msg = hint.querySelector && hint.querySelector('span:first-child');
              if (msg) msg.textContent = 'Drag on the template to move the selected pattern.';
            }
            if (patternLayerDiv) patternLayerDiv.style.display = 'none';
          };
          patternImg.src = url;
        } else {
          if (hint) {
            hint.style.display = 'flex';
            var hintMsg = hint.querySelector && hint.querySelector('span:first-child');
            if (hintMsg) hintMsg.textContent = 'Load paint first, then drag on the template to move the selected pattern.';
          }
          if (patternLayerDiv) patternLayerDiv.style.display = 'none';
        }
      } else {
        if (hint) {
          hint.style.display = 'flex';
          var moveMsg = hint.querySelector && hint.querySelector('span:first-child');
          if (moveMsg) moveMsg.textContent = 'Drag on the template to move ' + (layer === 'second_base' ? 'the 2nd overlay.' : layer === 'third_base' ? 'the 3rd overlay.' : layer === 'fourth_base' ? 'the 4th overlay.' : layer === 'fifth_base' ? 'the 5th overlay.' : layer === 'base' ? 'the base finish.' : 'the selected target.');
        }
        if (patternLayerDiv) patternLayerDiv.style.display = 'none';
      }
      var sel = d.getElementById && d.getElementById('placementLayerSelect' + getSelectedZoneIndex());
      if (sel && sel.value !== layer) sel.value = layer;
    }

    function setupPlacementOverlayDrag() {
      var d = doc();
      var overlay = d.getElementById && d.getElementById('placementMapOverlay');
      var patternLayerDiv = d.getElementById && d.getElementById('placementPatternLayer');
      if (!overlay || !patternLayerDiv || getPlacementLayer() !== 'pattern') return;
      patternLayerDiv.onmousedown = function (e) {
        var zone = zones()[getSelectedZoneIndex()];
        if (e.button !== 0 || !zone) return;
        e.preventDefault();
        placementOverlayDragStart = {
          clientX: e.clientX,
          clientY: e.clientY,
          offsetX: zone.patternOffsetX ?? 0.5,
          offsetY: zone.patternOffsetY ?? 0.5,
          snapshotPushed: false,
          didMove: false
        };
        d.addEventListener('mousemove', onPlacementOverlayMove);
        d.addEventListener('mouseup', onPlacementOverlayUp);
      };
    }

    function onPlacementOverlayMove(e) {
      if (!placementOverlayDragStart) return;
      var d = doc();
      var overlay = d.getElementById && d.getElementById('placementMapOverlay');
      var zone = zones()[getSelectedZoneIndex()];
      if (!overlay || !zone) return;
      if (!placementOverlayDragStart.snapshotPushed) {
        var screenDistance = Math.hypot(
          e.clientX - placementOverlayDragStart.clientX,
          e.clientY - placementOverlayDragStart.clientY
        );
        if (screenDistance < 4) return;
        pushZoneUndo('', true);
        placementOverlayDragStart.snapshotPushed = true;
        placementOverlayDragStart.didMove = true;
      }
      var rect = overlay.getBoundingClientRect();
      var nx = Math.max(0, Math.min(1, placementOverlayDragStart.offsetX + ((e.clientX - placementOverlayDragStart.clientX) / rect.width)));
      var ny = Math.max(0, Math.min(1, placementOverlayDragStart.offsetY + ((e.clientY - placementOverlayDragStart.clientY) / rect.height)));
      zone.patternOffsetX = nx;
      zone.patternOffsetY = ny;
      var pctX = Math.round(nx * 100) + '%';
      var pctY = Math.round(ny * 100) + '%';
      var vx = Math.round(nx * 100);
      var vy = Math.round(ny * 100);
      ['patPosXVal', 'detPatPosXVal'].forEach(function (id) {
        var el = d.getElementById && d.getElementById(id + getSelectedZoneIndex());
        if (el) {
          el.textContent = pctX;
          var inp = el.previousElementSibling;
          if (inp && inp.type === 'range') inp.value = vx;
        }
      });
      ['patPosYVal', 'detPatPosYVal'].forEach(function (id) {
        var el = d.getElementById && d.getElementById(id + getSelectedZoneIndex());
        if (el) {
          el.textContent = pctY;
          var inp = el.previousElementSibling;
          if (inp && inp.type === 'range') inp.value = vy;
        }
      });
      applyPlacementPatternTransform();
      triggerPreviewRender({ interactive: true });
    }

    function onPlacementOverlayUp() {
      var d = doc();
      var didMove = !!(placementOverlayDragStart && placementOverlayDragStart.didMove);
      if (d.removeEventListener) {
        d.removeEventListener('mousemove', onPlacementOverlayMove);
        d.removeEventListener('mouseup', onPlacementOverlayUp);
      }
      placementOverlayDragStart = null;
      if (didMove) triggerPreviewRender({ interactive: true });
    }

    function setPercentOffset(index, prop, value, live) {
      var zone = zones()[index];
      if (!zone) return;
      var numeric = Number(value);
      if (!Number.isFinite(numeric)) numeric = 50;
      var clamped = Math.max(0, Math.min(100, numeric));
      pushZoneUndo('', true);
      zone[prop] = clamped / 100;
      renderZones();
      if (live !== false) triggerPreviewRender();
    }

    function stepPercentOffset(index, prop, delta, setter) {
      var zone = zones()[index];
      if (!zone) return;
      var cur = Math.round((zone[prop] ?? 0.5) * 100);
      setter(index, Math.max(0, Math.min(100, cur + delta)));
    }

    function stepZoneSecondBasePatternOffset(index, axis, delta) {
      var prop = 'secondBasePatternOffset' + axis;
      stepPercentOffset(index, prop, delta, axis === 'X' ? setZoneSecondBasePatternOffsetX : setZoneSecondBasePatternOffsetY);
    }

    function stepZoneNthBasePatternOffset(index, nth, axis, delta) {
      var prop = nth + 'BasePatternOffset' + axis;
      stepPercentOffset(index, prop, delta, function (zoneIndex, value) { setPercentOffset(zoneIndex, prop, value); });
    }

    function stepZoneBaseOffset(index, axis, delta) {
      var prop = 'baseOffset' + axis;
      stepPercentOffset(index, prop, delta, function (zoneIndex, value) { setPercentOffset(zoneIndex, prop, value); });
    }

    function setZoneSecondBasePatternOffsetX(index, value) { setPercentOffset(index, 'secondBasePatternOffsetX', value); }
    function setZoneSecondBasePatternOffsetY(index, value) { setPercentOffset(index, 'secondBasePatternOffsetY', value); }
    function setZoneThirdBasePatternOffsetX(index, value) { setPercentOffset(index, 'thirdBasePatternOffsetX', value); }
    function setZoneThirdBasePatternOffsetY(index, value) { setPercentOffset(index, 'thirdBasePatternOffsetY', value); }
    function setZoneFourthBasePatternOffsetX(index, value) { setPercentOffset(index, 'fourthBasePatternOffsetX', value); }
    function setZoneFourthBasePatternOffsetY(index, value) { setPercentOffset(index, 'fourthBasePatternOffsetY', value); }
    function setZoneFifthBasePatternOffsetX(index, value) { setPercentOffset(index, 'fifthBasePatternOffsetX', value); }
    function setZoneFifthBasePatternOffsetY(index, value) { setPercentOffset(index, 'fifthBasePatternOffsetY', value); }

    global.setPlacementLayer = setPlacementLayer;
    global.getPlacementMode = getPlacementMode;
    global.isPlacementOffsetLocked = isPlacementOffsetLocked;
    global._placementOffsetControlAttrs = placementOffsetControlAttrs;
    global._placementOffsetValueAttrs = placementOffsetValueAttrs;
    global.clearPlacementEditingState = clearPlacementEditingState;
    global.setPlacementMode = setPlacementMode;
    global.renderPlacementModeControls = renderPlacementModeControls;
    global.applyPlacementPatternTransform = applyPlacementPatternTransform;
    global.updatePlacementBanner = updatePlacementBanner;
    global.setupPlacementOverlayDrag = setupPlacementOverlayDrag;
    global.stepZoneSecondBasePatternOffset = stepZoneSecondBasePatternOffset;
    global.stepZoneNthBasePatternOffset = stepZoneNthBasePatternOffset;
    global.stepZoneBaseOffset = stepZoneBaseOffset;
    global.setZoneSecondBasePatternOffsetX = setZoneSecondBasePatternOffsetX;
    global.setZoneSecondBasePatternOffsetY = setZoneSecondBasePatternOffsetY;
    global.setZoneThirdBasePatternOffsetX = setZoneThirdBasePatternOffsetX;
    global.setZoneThirdBasePatternOffsetY = setZoneThirdBasePatternOffsetY;
    global.setZoneFourthBasePatternOffsetX = setZoneFourthBasePatternOffsetX;
    global.setZoneFourthBasePatternOffsetY = setZoneFourthBasePatternOffsetY;
    global.setZoneFifthBasePatternOffsetX = setZoneFifthBasePatternOffsetX;
    global.setZoneFifthBasePatternOffsetY = setZoneFifthBasePatternOffsetY;
  }

  global.SPBZonePlacementControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
