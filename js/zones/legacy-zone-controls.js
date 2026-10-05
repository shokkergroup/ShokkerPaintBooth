'use strict';

(function () {
  function preview() {
    if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
  }

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const renderZoneDetail = deps.renderZoneDetail || window.renderZoneDetail;

    window.setZoneCCQuality = function setZoneCCQuality(index, val) {
      pushZoneUndo('Set CC quality', true);
      const zone = getZones()[index];
      if (!zone) return;
      zone.ccQuality = parseInt(val, 10) || 100;
      const label = document.getElementById('detCCQVal' + index);
      if (label) label.textContent = zone.ccQuality + '%';
      preview();
    };

    window.resetZoneCCQuality = function resetZoneCCQuality(index) {
      pushZoneUndo('Reset CC quality');
      const zone = getZones()[index];
      if (!zone) return;
      zone.ccQuality = 100;
      if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
      preview();
    };

    window.setZoneBlendBase = function setZoneBlendBase(index, val) {
      pushZoneUndo('Set blend base');
      const zone = getZones()[index];
      if (!zone) return;
      zone.blendBase = val || '';
      if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
      preview();
    };

    window.setZoneBlendDir = function setZoneBlendDir(index, val) {
      pushZoneUndo('Set blend direction');
      const zone = getZones()[index];
      if (!zone) return;
      zone.blendDir = val || 'horizontal';
      preview();
    };

    window.setZoneBlendAmount = function setZoneBlendAmount(index, val) {
      pushZoneUndo('Set blend amount');
      const zone = getZones()[index];
      if (!zone) return;
      zone.blendAmount = parseInt(val, 10) || 50;
      const label = document.getElementById('detBlendAmtVal' + index);
      if (label) label.textContent = zone.blendAmount + '%';
      preview();
    };

    window.setZonePaintReactiveColor = function setZonePaintReactiveColor(index, val) {
      pushZoneUndo('Set paint-reactive color');
      const zone = getZones()[index];
      if (!zone) return;
      zone.paintReactiveColor = val || '#000000';
      preview();
    };

    window.setZoneUsePaintReactive = function setZoneUsePaintReactive(index, checked) {
      pushZoneUndo('Toggle paint-reactive');
      const zone = getZones()[index];
      if (!zone) return;
      zone.usePaintReactive = !!checked;
      preview();
    };
  }

  window.SPBZoneLegacyControls = { install };
})();
