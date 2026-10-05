(function(global) {
  'use strict';

  function installZoneSwatchIdentityControls(deps) {
    deps = deps || {};
    const getBases = deps.getBases || function() { return []; };
    const getMonolithics = deps.getMonolithics || function() { return []; };
    const getPatterns = deps.getPatterns || function() { return []; };

    function getZoneColorHex(zone) {
      let rgb = null;
      if (zone && zone.color) {
        if (Array.isArray(zone.color) && zone.color.length > 0) {
          const first = zone.color[0];
          rgb = first && first.color_rgb ? first.color_rgb : null;
        } else if (zone.color.color_rgb) {
          rgb = zone.color.color_rgb;
        }
      }
      if (!rgb || !Array.isArray(rgb) || rgb.length < 3) return '888888';
      const toHex = (value) => Math.round(Math.max(0, Math.min(255, value))).toString(16).padStart(2, '0');
      return toHex(rgb[0]) + toHex(rgb[1]) + toHex(rgb[2]);
    }

    function getBaseName(zone) {
      if (zone && zone.finish) {
        const monolithic = getMonolithics().find((item) => item.id === zone.finish);
        return monolithic ? monolithic.name : '(not set)';
      }
      if (zone && zone.base) {
        const base = getBases().find((item) => item.id === zone.base);
        return base ? base.name : '(not set)';
      }
      return '(not set)';
    }

    function getPatternName(patternId) {
      if (!patternId || patternId === 'none') return 'None (Base Only)';
      const pattern = getPatterns().find((item) => item.id === patternId);
      return pattern ? pattern.name : patternId;
    }

    global.getZoneColorHex = getZoneColorHex;
    global.getBaseName = getBaseName;
    global.getPatternName = getPatternName;
  }

  global.SPBZoneSwatchIdentityControls = {
    install: installZoneSwatchIdentityControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
