(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = global.document;
    if (!doc || typeof doc.addEventListener !== 'function') return;
    if (doc.__spbZoneKeyboardControlsInstalled) return;
    doc.__spbZoneKeyboardControlsInstalled = true;

    var isTextEntryTarget = deps.isTextEntryTarget || function() { return false; };
    var addZone = deps.addZone || function() {};
    var toggleZoneMute = deps.toggleZoneMute || function() {};
    var deleteZone = deps.deleteZone || function() {};
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return 0; };
    var getCanvasMode = deps.getCanvasMode || function() { return ''; };
    var getLassoActive = deps.getLassoActive || function() { return false; };
    var getLassoPoints = deps.getLassoPoints || function() { return []; };
    var setLassoActive = deps.setLassoActive || function() {};
    var setLassoPoints = deps.setLassoPoints || function() {};
    var drawLassoPreview = deps.drawLassoPreview || function() {};
    var updateDrawZoneIndicator = deps.updateDrawZoneIndicator || function() {};
    var hideLassoPreview = deps.hideLassoPreview || function() {};
    var showToast = deps.showToast || function() {};
    var getCompareMode = deps.getCompareMode || function() { return false; };
    var toggleCompareMode = deps.toggleCompareMode || function() {};
    var closeFinishCompare = deps.closeFinishCompare || function() {};
    var closeFinishBrowser = deps.closeFinishBrowser || function() {};
    var closePresetGallery = deps.closePresetGallery || function() {};
    var closeModal = deps.closeModal || function() {};

    function claimEscape(e) {
      e.preventDefault();
      if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
    }

    doc.addEventListener('keydown', function(e) {
      if (e.defaultPrevented) return;
      if (isTextEntryTarget(e.target)) return;
      if (e.key === 'n' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
        e.preventDefault();
        addZone();
      } else if ((e.key === 'm' || e.key === 'M') && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        toggleZoneMute(getSelectedZoneIndex());
      } else if (e.key === 'Delete' && e.shiftKey) {
        e.preventDefault();
        deleteZone(getSelectedZoneIndex());
      }
    });

    doc.addEventListener('keydown', function(e) {
      if (e.defaultPrevented) return;
      var lassoPoints = getLassoPoints();
      if (e.key === 'Backspace' && getCanvasMode() === 'lasso' && getLassoActive() && lassoPoints.length > 0) {
        e.preventDefault();
        lassoPoints.pop();
        setLassoPoints(lassoPoints);
        drawLassoPreview();
        updateDrawZoneIndicator();
        showToast('Removed last vertex (' + lassoPoints.length + ' points remaining)');
        return;
      }
      if (e.key === 'Escape') {
        if (getCanvasMode() === 'lasso' && getLassoActive() && lassoPoints.length > 0) {
          claimEscape(e);
          setLassoActive(false);
          setLassoPoints([]);
          hideLassoPreview();
          showToast('Lasso cancelled');
          return;
        }
        if (getCompareMode()) { claimEscape(e); toggleCompareMode(); return; }
        if (doc.getElementById('finishCompareOverlay')?.classList.contains('active')) { claimEscape(e); closeFinishCompare(); return; }
        if (doc.getElementById('finishBrowserOverlay')?.classList.contains('active')) { claimEscape(e); closeFinishBrowser(); return; }
        if (doc.getElementById('presetGalleryOverlay')?.classList.contains('active')) { claimEscape(e); closePresetGallery(); return; }
        if (doc.getElementById('scriptModal')?.classList.contains('active')) { claimEscape(e); closeModal(); }
      }
    });
  }

  global.SPBZoneKeyboardControls = { install: install };
  if (typeof module === 'object' && module.exports) module.exports = global.SPBZoneKeyboardControls;
})(typeof window !== 'undefined' ? window : globalThis);
