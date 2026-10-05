(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getBases = deps.getBases || function() { return global.BASES || []; };
    var getPatterns = deps.getPatterns || function() { return global.PATTERNS || []; };
    var getMonolithics = deps.getMonolithics || function() { return global.MONOLITHICS || []; };
    var getFinishTypeById = deps.getFinishTypeById || function() { return global.FINISH_TYPE_BY_ID || {}; };
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value || '').replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch] || ch;
      });
    };
    var getServerBase = deps.getServerBase || function() {
      return (typeof global.ShokkerAPI !== 'undefined' && global.ShokkerAPI.baseUrl)
        ? global.ShokkerAPI.baseUrl
        : 'http://localhost:' + (global._SHOKKER_PORT || 59876);
    };
    var getSwatchVersion = deps.getSwatchVersion || function() {
      return global._SHOKKER_SWATCH_V || 'stable-v1';
    };

    function findById(items, id) {
      return (items || []).find(function(item) { return item && item.id === id; }) || null;
    }

    function getOverlayBaseDisplay(id) {
      if (!id) return null;
      if (typeof id === 'string' && id.startsWith('mono:')) {
        var monoId = id.slice(5);
        var m = findById(getMonolithics(), monoId) || findById(getBases(), monoId);
        return m ? { name: m.name, swatch: m.swatch || '#888' } : { name: id, swatch: '#888' };
      }
      var b = findById(getBases(), id);
      return b ? { name: b.name, swatch: b.swatch || '#888' } : { name: id, swatch: '#888' };
    }

    function _pickerSwatchFinishKey(id, finishType) {
      if (!id || id === 'none') return id;
      var ft = finishType || (typeof getFinishType === 'function' ? getFinishType(id) : null);
      if (ft === 'monolithic' && typeof id === 'string' && !id.startsWith('mono:')) return 'mono:' + id;
      return id;
    }

    function _pickerCatalogItemType(id) {
      if (!id || id === 'none') return null;
      var bare = (typeof id === 'string' && id.startsWith('mono:')) ? id.slice(5) : id;
      if (typeof bare === 'string' && bare.startsWith('pf_')) return 'base';
      var typeMap = getFinishTypeById();
      if (typeMap && typeMap[bare]) return typeMap[bare];
      if (findById(getBases(), bare)) return 'base';
      if (findById(getPatterns(), bare)) return 'pattern';
      if (findById(getMonolithics(), bare)) return 'monolithic';
      return 'monolithic';
    }

    function _pickerSelectValueForItem(id, finishType) {
      var ft = finishType || _pickerCatalogItemType(id);
      if (ft === 'monolithic') return 'mono:' + id;
      return id;
    }

    function getFinishType(id) {
      if (!id || id === 'none') return null;
      if (typeof id === 'string' && id.startsWith('mono:')) {
        var rawId = id.slice(5);
        if (findById(getBases(), rawId)) return 'base';
        return 'monolithic';
      }
      var typeMap = getFinishTypeById();
      if (typeMap && typeMap[id]) return typeMap[id];
      if (findById(getBases(), id)) return 'base';
      if (findById(getPatterns(), id)) return 'pattern';
      return 'monolithic';
    }

    function _normalizeSwatchTintHex(colorHex, fallbackColor) {
      function normalizeOne(raw) {
        if (typeof raw !== 'string') return null;
        var match = raw.trim().match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
        if (!match) return null;
        var s = match[1].toLowerCase();
        return s.length === 3
          ? s.split('').map(function(c) { return c + c; }).join('')
          : s;
      }

      return normalizeOne(colorHex) || normalizeOne(fallbackColor) || '888888';
    }

    function getSwatchUrl(finishId, colorHex, forceSplit, size, forceType) {
      var resolvedId = _pickerSwatchFinishKey(finishId, forceType);
      var effectiveId = (typeof resolvedId === 'string' && resolvedId.startsWith('mono:')) ? resolvedId.slice(5) : resolvedId;
      var type = forceType || _pickerCatalogItemType(resolvedId) || getFinishType(resolvedId);
      if (!type) return null;
      var col = _normalizeSwatchTintHex(colorHex, null);
      var sz = (size != null && size > 0) ? size : (forceSplit === false ? 48 : 256);
      var splitMode = (forceSplit !== false && (type === 'pattern' || type === 'monolithic' || type === 'base')) ? '&mode=split' : '';
      // COLORSHOXX fixes must show the real paint/spec renderer immediately.
      // Static/fallback split cards drift badly and can show obsolete fake spec art.
      // Owner 2026-10-02: picker misses belong to the offline baker, never browsing.
      var prefer = '&prefer=live&source=faithful-v1' + (splitMode ? '&baked=1' : '');
      // Owner 2026-09-17: reopening a category must reuse its baked thumbnails.
      // Boot already fetches this map; preserve its per-finish URL after boot too.
      var fingerprints = global._SHOKKER_SWATCH_FP || {};
      var version = fingerprints[type + ':' + effectiveId] || getSwatchVersion();
      return getServerBase() + '/api/swatch/' + type + '/' + effectiveId + '?color=' + col + '&size=' + sz + splitMode + prefer + '&v=' + version;
    }

    function getOverlaySpecialPickerHtml(zone, i, layer) {
      var key = { second: 'secondBaseColorSource', third: 'thirdBaseColorSource', fourth: 'fourthBaseColorSource', fifth: 'fifthBaseColorSource' }[layer];
      var current = zone[key];
      var isMono = current && current.startsWith('mono:');
      var monoId = isMono ? current.slice(5) : null;
      var selectedMono = monoId ? (findById(getMonolithics(), monoId) || findById(getBases(), monoId) || null) : null;
      var popupType = { second: 'secondBaseColorSource', third: 'thirdBaseColorSource', fourth: 'fourthBaseColorSource', fifth: 'fifthBaseColorSource' }[layer];
      var html = '';
      if (selectedMono) {
        var smallUrl = getSwatchUrl(selectedMono.id, selectedMono.swatch, true, 32, getFinishType(selectedMono.id) || 'monolithic');
        html += '<div class="stack-control-group" style="flex-basis:100%;margin-top:2px;align-items:center;gap:6px;">' +
          '<div style="display:flex;align-items:center;gap:6px;min-width:0;" title="From special - ' + escapeHtml(selectedMono.name || selectedMono.id) + '">' +
          (smallUrl ? '<img src="' + smallUrl + '" alt="" style="width:24px;height:24px;border-radius:3px;border:1px solid var(--border);object-fit:cover;flex-shrink:0;" loading="eager" onerror="this.style.display=\'none\'; this.nextElementSibling && (this.nextElementSibling.style.display=\'block\');">' : '') +
          '<span style="width:24px;height:24px;border-radius:3px;background:#' + String(selectedMono.swatch || '888').replace('#', '') + ';flex-shrink:0;' + (smallUrl ? 'display:none;' : '') + '" class="ov-fb"></span>' +
          '<span style="font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(selectedMono.name || selectedMono.id) + '</span>' +
          '<button type="button" class="btn btn-sm swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, \'' + popupType + '\', ' + i + ');" style="font-size:9px;padding:2px 6px;">Change...</button>' +
          '</div></div>';
      } else {
        html += '<div class="stack-control-group" style="flex-basis:100%;margin-top:4px;">' +
          '<span class="stack-label-mini" style="margin-bottom:4px;">From special</span>' +
          '<button type="button" class="btn btn-sm swatch-trigger" onclick="event.stopPropagation(); openSwatchPicker(this, \'' + popupType + '\', ' + i + ');" style="font-size:9px;padding:2px 8px;">Choose special...</button>' +
          '</div>';
      }
      return html;
    }

    function renderSwatchSquare(finishId, fallbackColor, title, colorHex, forceType) {
      if (!finishId || finishId === 'none') {
        return '<div class="swatch-square" style="background:' + (fallbackColor || '#444') + ';" title="' + (title || '') + '"></div>';
      }
      var resolvedId = _pickerSwatchFinishKey(finishId, forceType);
      var type = forceType || _pickerCatalogItemType(resolvedId) || getFinishType(resolvedId);
      var isSplit = (type === 'pattern' || type === 'monolithic' || type === 'base');
      var tintHex = _normalizeSwatchTintHex(colorHex, fallbackColor);
      var url = getSwatchUrl(resolvedId, tintHex, undefined, undefined, type);
      if (url) {
        var w = isSplit ? 72 : 36;
        var h = 36;
        var titleSafe = (title || '').replace(/"/g, '&quot;');
        var fallback = fallbackColor || '#444';
        if (isSplit) {
          return '<div class="swatch-square swatch-split swatch-split-frame" title="' + titleSafe + '" data-swatch-contract="paint-left-spec-right" data-left-label="Paint" data-right-label="Spec" style="width:' + w + 'px;height:' + h + 'px;">' +
            '<img class="deferred-swatch swatch-split-img" data-swatch-url="' + url + '" alt="" loading="eager" decoding="async" onerror="var frame=this.closest(\'.swatch-split-frame\'); if(frame){frame.classList.add(\'swatch-spec-unavailable\'); frame.style.background=\'' + fallback + '\';} this.remove();">' +
            '<span class="swatch-split-label swatch-split-label-left">Paint</span>' +
            '<span class="swatch-split-label swatch-split-label-right">Spec</span>' +
            '<span class="swatch-split-error">Preview unavailable</span>' +
            '</div>';
        }
        return '<img class="swatch-square deferred-swatch" data-swatch-url="' + url + '" title="' + (title || '') + '" alt="" loading="eager" decoding="async" style="width:' + w + 'px;height:' + h + 'px;border-radius:4px;border:1px solid rgba(255,255,255,0.12);object-fit:cover;" onerror="this.outerHTML=\'<div class=&quot;swatch-square&quot; title=&quot;' + titleSafe + '&quot; style=&quot;width:' + w + 'px;height:' + h + 'px;background:' + fallback + ';&quot;></div>\'">';
      }
      return '<div class="swatch-square" style="background:' + (fallbackColor || '#444') + ';" title="' + (title || '') + '"></div>';
    }

    function renderSwatchDot(finishId, fallbackColor, colorHex) {
      if (!finishId || finishId === 'none') {
        return '<div class="swatch-dot" style="background:' + (fallbackColor || '#444') + ';"></div>';
      }
      var url = getSwatchUrl(finishId, colorHex, false);
      if (url) {
        return '<img class="swatch-dot" src="' + url + '" loading="eager" style="width:14px;height:14px;border-radius:3px;border:1px solid rgba(255,255,255,0.15);flex-shrink:0;object-fit:cover;" onerror="this.outerHTML=\'<div class=&quot;swatch-dot&quot; style=&quot;background:' + (fallbackColor || '#444') + ';&quot;></div>\'">';
      }
      return '<div class="swatch-dot" style="background:' + (fallbackColor || '#444') + ';"></div>';
    }

    function getSwatchColor(zone) {
      if (zone && zone.finish) {
        var m = findById(getMonolithics(), zone.finish);
        return m ? m.swatch : '#444';
      }
      if (zone && zone.base) {
        var b = findById(getBases(), zone.base);
        return b ? b.swatch : '#444';
      }
      return '#333';
    }

    function getPatternSwatchColor(patternId) {
      if (!patternId || patternId === 'none') return 'transparent';
      var p = findById(getPatterns(), patternId);
      return p ? p.swatch : '#444';
    }

    Object.assign(global, {
      getOverlayBaseDisplay: getOverlayBaseDisplay,
      _pickerSwatchFinishKey: _pickerSwatchFinishKey,
      _pickerCatalogItemType: _pickerCatalogItemType,
      _pickerSelectValueForItem: _pickerSelectValueForItem,
      getFinishType: getFinishType,
      _normalizeSwatchTintHex: _normalizeSwatchTintHex,
      getSwatchUrl: getSwatchUrl,
      getOverlaySpecialPickerHtml: getOverlaySpecialPickerHtml,
      renderSwatchSquare: renderSwatchSquare,
      renderSwatchDot: renderSwatchDot,
      getSwatchColor: getSwatchColor,
      getPatternSwatchColor: getPatternSwatchColor
    });
  }

  global.SPBSwatchPopupRenderControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
