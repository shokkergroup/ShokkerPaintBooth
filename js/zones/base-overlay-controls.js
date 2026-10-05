'use strict';

(function () {
  const SCALE_STEP = 0.05;
  const SCALE_PATTERN_MIN = 0.10;
  const SCALE_PATTERN_MAX = 4.0;
  const SCALE_OVERLAY_MIN = 0.10;
  const SCALE_OVERLAY_MAX = 5.0;

  const OVERLAY_SPEC_TIERS = {
    Second: { key: 'secondBaseSpecStrength', label: 'detSBSpecStrVal', name: 'second' },
    Third: { key: 'thirdBaseSpecStrength', label: 'detTBSpecStrVal', name: 'third' },
    Fourth: { key: 'fourthBaseSpecStrength', label: 'detFBSpecStrVal', name: 'fourth' },
    Fifth: { key: 'fifthBaseSpecStrength', label: 'detFifBSpecStrVal', name: 'fifth' },
  };

  const OVERLAY_SCALE_TIERS = {
    Second: {
      base: { key: 'secondBaseScale', label: 'detSBScaleVal', undo: 'Set 2nd overlay scale', unit: '' },
      color: { key: 'secondBaseColorScale', label: 'detSBColorScaleVal', undo: 'Set overlay secondBaseColorScale', unit: 'x' },
      spec: { key: 'secondBaseSpecScale', label: 'detSBSpecScaleVal', undo: 'Set overlay secondBaseSpecScale', unit: 'x' },
    },
    Third: {
      base: { key: 'thirdBaseScale', label: 'detTBScaleVal', undo: 'Set 3rd overlay scale', unit: '' },
      color: { key: 'thirdBaseColorScale', label: 'detTBColorScaleVal', undo: 'Set overlay thirdBaseColorScale', unit: 'x' },
      spec: { key: 'thirdBaseSpecScale', label: 'detTBSpecScaleVal', undo: 'Set overlay thirdBaseSpecScale', unit: 'x' },
    },
    Fourth: {
      base: { key: 'fourthBaseScale', label: 'detFBScaleVal', undo: 'Set 4th overlay scale', unit: '' },
      color: { key: 'fourthBaseColorScale', label: 'detFBColorScaleVal', undo: 'Set overlay fourthBaseColorScale', unit: 'x' },
      spec: { key: 'fourthBaseSpecScale', label: 'detFBSpecScaleVal', undo: 'Set overlay fourthBaseSpecScale', unit: 'x' },
    },
    Fifth: {
      base: { key: 'fifthBaseScale', label: 'detFifScaleVal', undo: 'Set 5th overlay scale', unit: '' },
      color: { key: 'fifthBaseColorScale', label: 'detFifColorScaleVal', undo: 'Set overlay fifthBaseColorScale', unit: 'x' },
      spec: { key: 'fifthBaseSpecScale', label: 'detFifSpecScaleVal', undo: 'Set overlay fifthBaseSpecScale', unit: 'x' },
    },
  };

  const OVERLAY_BASIC_TIERS = {
    Second: {
      name: '2nd',
      strength: { key: 'secondBaseStrength', label: 'detSBStrVal', undo: 'Set overlay strength' },
      blend: { key: 'secondBaseBlendMode', patternKey: 'secondBasePattern', undo: 'Set overlay blend mode' },
      fractal: { key: 'secondBaseFractalScale', label: 'detSBNSVal', undo: 'Set overlay Fractal Detail' },
    },
    Third: {
      name: '3rd',
      strength: { key: 'thirdBaseStrength', label: 'detTBStrVal', undo: 'Set 3rd overlay strength' },
      blend: { key: 'thirdBaseBlendMode', patternKey: 'thirdBasePattern', undo: 'Set 3rd overlay blend mode' },
      fractal: { key: 'thirdBaseFractalScale', label: 'detTBNSVal', undo: 'Set 3rd overlay Fractal Detail' },
    },
    Fourth: {
      name: '4th',
      strength: { key: 'fourthBaseStrength', label: 'detFBStrVal', undo: 'Set 4th overlay strength' },
      blend: { key: 'fourthBaseBlendMode', patternKey: 'fourthBasePattern', undo: 'Set 4th overlay blend' },
      fractal: { key: 'fourthBaseFractalScale', label: 'detFBNSVal', undo: 'Set 4th overlay Fractal Detail' },
    },
    Fifth: {
      name: '5th',
      strength: { key: 'fifthBaseStrength', label: 'detFifStrVal', undo: 'Set 5th overlay strength' },
      blend: { key: 'fifthBaseBlendMode', patternKey: 'fifthBasePattern', undo: 'Set 5th overlay blend' },
      fractal: { key: 'fifthBaseFractalScale', label: 'detFifNSVal', undo: 'Set 5th overlay Fractal Detail' },
    },
  };

  const OVERLAY_COLOR_TIERS = {
    Second: {
      baseUndo: 'Set overlay base',
      patternUndo: 'Set 2nd base pattern',
      baseKey: 'secondBase',
      enabledKey: 'secondBaseEnabled',
      sourceKey: 'secondBaseColorSource',
      colorKey: 'secondBaseColor',
      sourceUndo: 'Overlay color source',
      overlayUndo: 'Overlay color same as base',
      colorUndo: 'Set overlay color',
    },
    Third: {
      baseUndo: 'Set 3rd overlay base',
      patternUndo: 'Set 3rd base pattern',
      baseKey: 'thirdBase',
      enabledKey: 'thirdBaseEnabled',
      sourceKey: 'thirdBaseColorSource',
      colorKey: 'thirdBaseColor',
      sourceUndo: '3rd overlay color from special',
      overlayUndo: '3rd overlay color same as base',
      colorUndo: 'Set 3rd overlay color',
    },
    Fourth: {
      baseUndo: 'Set 4th overlay base',
      patternUndo: 'Set 4th base pattern',
      baseKey: 'fourthBase',
      enabledKey: 'fourthBaseEnabled',
      sourceKey: 'fourthBaseColorSource',
      colorKey: 'fourthBaseColor',
      sourceUndo: '4th overlay color from special',
      overlayUndo: '4th overlay color same as base',
      colorUndo: 'Set 4th overlay color',
    },
    Fifth: {
      baseUndo: 'Set 5th overlay base',
      patternUndo: 'Set 5th base pattern',
      baseKey: 'fifthBase',
      enabledKey: 'fifthBaseEnabled',
      sourceKey: 'fifthBaseColorSource',
      colorKey: 'fifthBaseColor',
      sourceUndo: '5th overlay color from special',
      overlayUndo: '5th overlay color same as base',
      colorUndo: 'Set 5th overlay color',
    },
  };

  const OVERLAY_PATTERN_TIERS = {
    Second: { prefix: 'secondBasePattern', labelPrefix: 'detSBPat' },
    Third: { prefix: 'thirdBasePattern', labelPrefix: 'detTBPat' },
    Fourth: { prefix: 'fourthBasePattern', labelPrefix: 'detFBPat' },
    Fifth: { prefix: 'fifthBasePattern', labelPrefix: 'detFifPat' },
  };

  const OVERLAY_ALIGN_TIERS = {
    Second: { baseKey: 'secondBase', patternKey: 'secondBasePattern', labelPrefix: 'detSBPat' },
    Third: { baseKey: 'thirdBase', patternKey: 'thirdBasePattern', labelPrefix: 'detTBPat' },
    Fourth: { baseKey: 'fourthBase', patternKey: 'fourthBasePattern', labelPrefix: 'detFBPat' },
    Fifth: { baseKey: 'fifthBase', patternKey: 'fifthBasePattern', labelPrefix: 'detFifPat' },
  };

  function clampPct(val, fallback) {
    const pct = !Number.isNaN(parseInt(val, 10)) ? parseInt(val, 10) : fallback;
    return Math.max(0, Math.min(2, pct / 100));
  }

  function roundToStep(val, step) {
    return Math.round(val / step) * step;
  }

  function clampScale(val) {
    const parsed = parseFloat(val);
    const rounded = roundToStep(Number.isFinite(parsed) ? parsed : 1, SCALE_STEP);
    return Math.max(SCALE_OVERLAY_MIN, Math.min(SCALE_OVERLAY_MAX, rounded));
  }

  function clampPatternScale(val) {
    const parsed = parseFloat(val);
    const rounded = roundToStep(Number.isFinite(parsed) ? parsed : 1, SCALE_STEP);
    return Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, rounded));
  }

  function preview() {
    if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
  }

  function updateScopedLabel(index, labelId, value, unit) {
    const text = value.toFixed(2) + unit;
    const card = document.getElementById('zone-card-' + index);
    if (card) {
      const span = card.querySelector('#' + labelId + index);
      if (span) span.textContent = text;
    }
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
      const span = panel.querySelector('#' + labelId + index);
      if (span) span.textContent = text;
    }
  }

  function updateLabelText(index, labelId, text) {
    const label = document.getElementById(labelId + index);
    if (label) label.textContent = text;
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
      const span = panel.querySelector('#' + labelId + index);
      if (span) span.textContent = text;
    }
  }

  function normalizeHex(val) {
    const trimmed = (val || '').trim();
    if (!trimmed) return '';
    return trimmed.startsWith('#') ? trimmed : '#' + trimmed;
  }

  function updateNumericInputPair(index, inputId, rangeId, value) {
    const input = document.getElementById(inputId + index);
    if (input) input.value = value;
    const range = document.getElementById(rangeId + index);
    if (range) range.value = value;
  }

  function overlayBaseSwatch(getOverlayBaseDisplay, zone, tier) {
    const baseId = zone[tier.baseKey] || zone[tier.sourceKey];
    const display = typeof getOverlayBaseDisplay === 'function' ? getOverlayBaseDisplay(baseId) : null;
    const swatch = display && display.swatch ? display.swatch : '';
    return swatch ? (swatch.startsWith('#') ? swatch : '#' + swatch) : '#c9a227';
  }

  function selectedPatternTransform(zone, patternKey) {
    const fallback = {
      sx: zone.scale ?? 1.0,
      rot: zone.rotation ?? 0,
      px: zone.patternOffsetX ?? 0.5,
      py: zone.patternOffsetY ?? 0.5,
    };
    const targetPatId = zone[patternKey] || '';
    if (!targetPatId || targetPatId === 'none') return fallback;
    const stack = zone.patternStack || [];
    const pat = stack.find(p => p.id === targetPatId);
    if (pat) {
      return {
        sx: pat.scale ?? 1.0,
        rot: pat.rotation ?? 0,
        px: pat.offsetX ?? 0.5,
        py: pat.offsetY ?? 0.5,
      };
    }
    if (zone.pattern && zone.pattern === targetPatId) return fallback;
    return fallback;
  }

  function syncAlignLabels(index, tier, zone) {
    const xKey = tier.patternKey + 'OffsetX';
    const yKey = tier.patternKey + 'OffsetY';
    const scaleKey = tier.patternKey + 'Scale';
    const rotationKey = tier.patternKey + 'Rotation';
    const pctX = Math.round(zone[xKey] * 100) + '%';
    const pctY = Math.round(zone[yKey] * 100) + '%';
    const scaleText = zone[scaleKey].toFixed(2) + 'x';

    function updatePosition(root, id, text, value) {
      const span = root ? root.querySelector('#' + id + index) : document.getElementById(id + index);
      if (!span) return;
      span.textContent = text;
      const input = span.previousElementSibling;
      if (input && input.type === 'range') input.value = Math.round(value * 100);
    }

    updatePosition(null, tier.labelPrefix + 'PosXVal', pctX, zone[xKey]);
    updatePosition(null, tier.labelPrefix + 'PosYVal', pctY, zone[yKey]);
    const panel = document.getElementById('zoneEditorFloat');
    if (panel) {
      updatePosition(panel, tier.labelPrefix + 'PosXVal', pctX, zone[xKey]);
      updatePosition(panel, tier.labelPrefix + 'PosYVal', pctY, zone[yKey]);
    }
    updateLabelText(index, tier.labelPrefix + 'ScaleVal', scaleText);
    updateNumericInputPair(index, tier.labelPrefix + 'RotVal', tier.labelPrefix + 'RotRange', zone[rotationKey]);
  }

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const pushZoneUndoCoalesced = deps.pushZoneUndoCoalesced || pushZoneUndo;
    const propagateToLinkedZones = deps.propagateToLinkedZones;
    const renderZoneDetail = deps.renderZoneDetail || window.renderZoneDetail;
    const autoAttachOverlayPatternForBlend = deps.autoAttachOverlayPatternForBlend || window._autoAttachOverlayPatternForBlend;
    const defaultOverlayReactPatternToIndependent = deps.defaultOverlayReactPatternToIndependent || window._defaultOverlayReactPatternToIndependent;
    const normalizeOverlayReactPatternValue = deps.normalizeOverlayReactPatternValue || function normalize(val) { return val || ''; };
    const markUserEdit = deps.markUserEdit || function noop() {};
    const getOverlayBaseDisplay = deps.getOverlayBaseDisplay || window.getOverlayBaseDisplay;
    const showToast = deps.showToast || window.showToast;

    Object.entries(OVERLAY_PATTERN_TIERS).forEach(([suffix, tier]) => {
      window['setZone' + suffix + 'BasePatternOpacity'] = function setOverlayBasePatternOpacity(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.prefix + 'Opacity'] = Math.max(0, Math.min(100, parseInt(val, 10) ?? 100));
        updateLabelText(index, tier.labelPrefix + 'OpVal', zone[tier.prefix + 'Opacity'] + '%');
        preview();
      };

      window['stepZone' + suffix + 'BasePatternOpacity'] = function stepOverlayBasePatternOpacity(index, delta) {
        const zone = getZones()[index];
        if (!zone) return;
        window['setZone' + suffix + 'BasePatternOpacity'](index, Math.max(0, Math.min(100, (zone[tier.prefix + 'Opacity'] ?? 100) + delta * 5)));
      };

      window['setZone' + suffix + 'BasePatternScale'] = function setOverlayBasePatternScale(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.prefix + 'Scale'] = clampPatternScale(val);
        updateLabelText(index, tier.labelPrefix + 'ScaleVal', zone[tier.prefix + 'Scale'].toFixed(2) + 'x');
        preview();
      };

      window['stepZone' + suffix + 'BasePatternScale'] = function stepOverlayBasePatternScale(index, delta) {
        const zone = getZones()[index];
        if (!zone) return;
        window['setZone' + suffix + 'BasePatternScale'](index, clampPatternScale((zone[tier.prefix + 'Scale'] ?? 1) + delta * SCALE_STEP));
      };

      window['setZone' + suffix + 'BasePatternRotation'] = function setOverlayBasePatternRotation(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        const raw = parseInt(val, 10);
        const rotation = ((Number.isFinite(raw) ? raw : 0) % 360 + 360) % 360;
        zone[tier.prefix + 'Rotation'] = rotation;
        updateNumericInputPair(index, tier.labelPrefix + 'RotVal', tier.labelPrefix + 'RotRange', rotation);
        preview();
      };

      window['stepZone' + suffix + 'BasePatternRotation'] = function stepOverlayBasePatternRotation(index, delta) {
        const zone = getZones()[index];
        if (!zone) return;
        window['setZone' + suffix + 'BasePatternRotation'](index, (zone[tier.prefix + 'Rotation'] ?? 0) + delta * 5);
      };

      window['setZone' + suffix + 'BasePatternStrength'] = function setOverlayBasePatternStrength(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.prefix + 'Strength'] = Math.max(0, Math.min(2, (parseInt(val, 10) ?? 100) / 100));
        updateLabelText(index, tier.labelPrefix + 'StrVal', Math.round(zone[tier.prefix + 'Strength'] * 100) + '%');
        preview();
      };

      window['stepZone' + suffix + 'BasePatternStrength'] = function stepOverlayBasePatternStrength(index, delta) {
        const zone = getZones()[index];
        if (!zone) return;
        const cur = Math.round((zone[tier.prefix + 'Strength'] ?? 1) * 100);
        window['setZone' + suffix + 'BasePatternStrength'](index, Math.max(0, Math.min(200, cur + delta * 5)));
      };

      window['setZone' + suffix + 'BasePatternInvert'] = function setOverlayBasePatternInvert(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.prefix + 'Invert'] = !!val;
        preview();
      };

      window['setZone' + suffix + 'BasePatternHarden'] = function setOverlayBasePatternHarden(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.prefix + 'Harden'] = !!val;
        preview();
      };

      window['setZone' + suffix + 'BasePatternOffsetX'] = function setOverlayBasePatternOffsetX(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        const n = Math.max(0, Math.min(1, Number(val) / 100));
        zone[tier.prefix + 'OffsetX'] = n;
        updateLabelText(index, tier.labelPrefix + 'PosXVal', Math.round(n * 100) + '%');
        preview();
      };

      window['setZone' + suffix + 'BasePatternOffsetY'] = function setOverlayBasePatternOffsetY(index, val) {
        pushZoneUndo('', true);
        const zone = getZones()[index];
        if (!zone) return;
        const n = Math.max(0, Math.min(1, Number(val) / 100));
        zone[tier.prefix + 'OffsetY'] = n;
        updateLabelText(index, tier.labelPrefix + 'PosYVal', Math.round(n * 100) + '%');
        preview();
      };
    });

    Object.entries(OVERLAY_ALIGN_TIERS).forEach(([suffix, tier]) => {
      window['align' + suffix + 'BaseOverlayWithSelectedPattern'] = function alignOverlayWithSelectedPattern(index) {
        const zone = getZones()[index];
        if (!zone || !zone[tier.baseKey]) return;
        pushZoneUndo('', true);
        const transform = selectedPatternTransform(zone, tier.patternKey);
        zone[tier.patternKey + 'OffsetX'] = transform.px;
        zone[tier.patternKey + 'OffsetY'] = transform.py;
        zone[tier.patternKey + 'Scale'] = Math.max(SCALE_PATTERN_MIN, Math.min(SCALE_PATTERN_MAX, transform.sx));
        zone[tier.patternKey + 'Rotation'] = ((transform.rot % 360) + 360) % 360;
        syncAlignLabels(index, tier, zone);
        preview();
        if (typeof showToast === 'function') showToast('Overlay aligned with selected pattern (position, scale, rotation)');
      };
    });

    Object.entries(OVERLAY_COLOR_TIERS).forEach(([suffix, tier]) => {
      const basicTier = OVERLAY_BASIC_TIERS[suffix];
      const patternTier = OVERLAY_PATTERN_TIERS[suffix];

      window['setZone' + suffix + 'Base'] = function setOverlayBase(index, val) {
        pushZoneUndo(tier.baseUndo);
        markUserEdit(index);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.baseKey] = val || '';
        if (!val) {
          zone[basicTier.strength.key] = 0;
          zone[tier.sourceKey] = null;
        } else {
          zone[tier.enabledKey] = true;
          const hadSource = !!zone[tier.sourceKey];
          if (!zone[basicTier.strength.key]) zone[basicTier.strength.key] = 1.0;
          const hardenKey = tier.baseKey + 'Harden';
          // [SPB overlay default 2026-06-10 — owner] stacking a 2nd/3rd/4th/5th base
          // overlay: WITH a pattern present default to Pattern Pop + Harden; WITHOUT
          // a pattern default to Tint.
          const _ovPat0 = zone[tier.patternKey];
          const _hasPat0 = !!_ovPat0 && _ovPat0 !== 'none';
          if (!zone[basicTier.blend.key]) zone[basicTier.blend.key] = _hasPat0 ? 'pattern-pop' : 'tint';
          if (zone[hardenKey] === undefined) zone[hardenKey] = _hasPat0;
          if (!hadSource && !zone[tier.sourceKey]) {
            zone[tier.sourceKey] = 'overlay';
            zone[tier.colorKey] = overlayBaseSwatch(getOverlayBaseDisplay, zone, tier);
          }
          if (typeof defaultOverlayReactPatternToIndependent === 'function') {
            defaultOverlayReactPatternToIndependent(index, basicTier.blend.patternKey);
          }
          if (typeof autoAttachOverlayPatternForBlend === 'function') {
            autoAttachOverlayPatternForBlend(index, basicTier.blend.patternKey, zone[basicTier.blend.key]);
          }
        }
        if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
        preview();
      };

      window['setZone' + suffix + 'BasePattern'] = function setOverlayBasePattern(index, val) {
        pushZoneUndo(tier.patternUndo);
        const zone = getZones()[index];
        if (!zone) return;
        zone[patternTier.prefix] = normalizeOverlayReactPatternValue(val);
        // [SPB overlay default 2026-06-10 — owner] keep the auto blend in sync when
        // a pattern is attached/cleared AFTER the overlay was added: pattern present
        // -> Pattern Pop + Harden; none -> Tint. Only when the blend is still one of
        // the auto defaults (never clobber a deliberate blend choice).
        const _ovPatN = zone[patternTier.prefix];
        const _hasPatN = !!_ovPatN && _ovPatN !== 'none';
        const _curBlend = zone[basicTier.blend.key];
        if (!_curBlend || _curBlend === 'tint' || _curBlend === 'pattern-pop') {
          zone[basicTier.blend.key] = _hasPatN ? 'pattern-pop' : 'tint';
          zone[tier.baseKey + 'Harden'] = _hasPatN;
        }
        if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
        preview();
      };

      window['setZone' + suffix + 'BaseColorSource'] = function setOverlayBaseColorSource(index, val) {
        pushZoneUndo(tier.sourceUndo, true);
        markUserEdit(index);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.sourceKey] = val || null;
        if (val) zone[tier.enabledKey] = true;
        if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
        preview();
      };

      window['setZone' + suffix + 'BaseColorSourceToOverlay'] = function setOverlayBaseColorSourceToOverlay(index) {
        pushZoneUndo(tier.overlayUndo, true);
        markUserEdit(index);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.sourceKey] = 'overlay';
        zone[tier.colorKey] = overlayBaseSwatch(getOverlayBaseDisplay, zone, tier);
        if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
        preview();
      };

      window['setZone' + suffix + 'BaseColor'] = function setOverlayBaseColor(index, val) {
        pushZoneUndo(tier.colorUndo, true);
        markUserEdit(index);
        const zone = getZones()[index];
        if (!zone) return;
        const hex = normalizeHex(val);
        if (hex && !/^#[0-9A-Fa-f]{6}$/.test(hex)) {
          if (typeof showToast === 'function') showToast('Enter a valid hex code like #FF3366', true);
          if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
          return;
        }
        zone[tier.colorKey] = hex || '#ffffff';
        zone[tier.sourceKey] = 'solid';
        if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
        preview();
      };
    });

    Object.entries(OVERLAY_BASIC_TIERS).forEach(([suffix, tier]) => {
      window['setZone' + suffix + 'BaseStrength'] = function setOverlayBaseStrength(index, val) {
        pushZoneUndo(tier.strength.undo, true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.strength.key] = (parseInt(val, 10) || 0) / 100;
        updateLabelText(index, tier.strength.label, Math.round(zone[tier.strength.key] * 100) + '%');
        preview();
      };

      window['stepZone' + suffix + 'BaseStrength'] = function stepOverlayBaseStrength(index, delta) {
        const zone = getZones()[index];
        if (!zone) return;
        const cur = Math.round((zone[tier.strength.key] ?? 0) * 100);
        window['setZone' + suffix + 'BaseStrength'](index, Math.max(0, Math.min(100, cur + delta * 5)));
      };

      window['setZone' + suffix + 'BaseBlendMode'] = function setOverlayBaseBlendMode(index, val) {
        pushZoneUndo(tier.blend.undo);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.blend.key] = val || 'noise';
        if (typeof autoAttachOverlayPatternForBlend === 'function') {
          autoAttachOverlayPatternForBlend(index, tier.blend.patternKey, zone[tier.blend.key]);
        }
        if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
        preview();
      };

      window['setZone' + suffix + 'BaseFractalScale'] = function setOverlayBaseFractalScale(index, val) {
        pushZoneUndo(tier.fractal.undo, true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.fractal.key] = Math.max(4, Math.min(128, parseInt(val, 10) || 24));
        updateLabelText(index, tier.fractal.label, zone[tier.fractal.key] + 'px');
        preview();
      };

      window['stepZone' + suffix + 'BaseFractalScale'] = function stepOverlayBaseFractalScale(index, delta) {
        const zone = getZones()[index];
        if (!zone) return;
        window['setZone' + suffix + 'BaseFractalScale'](index, Math.max(4, Math.min(128, (zone[tier.fractal.key] ?? 24) + delta * 4)));
      };
    });

    Object.entries(OVERLAY_SPEC_TIERS).forEach(([suffix, tier]) => {
      window['setZone' + suffix + 'BaseSpecStrength'] = function setOverlayBaseSpecStrength(index, val) {
        pushZoneUndo('Set ' + tier.name + ' base spec strength', true);
        const zone = getZones()[index];
        if (!zone) return;
        zone[tier.key] = clampPct(val, 100);
        const label = document.getElementById(tier.label + index);
        if (label) label.textContent = Math.round(zone[tier.key] * 100) + '%';
        preview();
      };

      window['stepZone' + suffix + 'BaseSpecStrength'] = function stepOverlayBaseSpecStrength(index, delta) {
        const cur = Math.round((getZones()[index][tier.key] ?? 1) * 100);
        window['setZone' + suffix + 'BaseSpecStrength'](index, Math.max(0, Math.min(200, cur + delta * 5)));
      };
    });

    Object.entries(OVERLAY_SCALE_TIERS).forEach(([suffix, tier]) => {
      Object.entries(tier).forEach(([kind, cfg]) => {
        const name = kind === 'base' ? 'BaseScale' : 'Base' + kind.charAt(0).toUpperCase() + kind.slice(1) + 'Scale';
        window['setZone' + suffix + name] = function setOverlayScale(index, val) {
          const zones = getZones();
          if (index < 0 || index >= zones.length) return;
          const n = clampScale(val);
          zones[index][cfg.key] = n;
          if (typeof propagateToLinkedZones === 'function') propagateToLinkedZones(index, [cfg.key]);
          pushZoneUndoCoalesced(cfg.undo);
          updateScopedLabel(index, cfg.label, n, cfg.unit);
          preview();
        };

        window['stepZone' + suffix + name] = function stepOverlayScale(index, delta) {
          const zone = getZones()[index];
          if (!zone) return;
          window['setZone' + suffix + name](index, clampScale((zone[cfg.key] ?? 1) + delta * SCALE_STEP));
        };
      });
    });
  }

  window.SPBZoneBaseOverlayControls = { install };
})();
