(function (global) {
  'use strict';

  var expanded = null;

  function install(deps) {
    deps = deps || {};
    var renderZoneDetail = deps.renderZoneDetail || function () {};

    function getOverlaySpecialPickerExpanded() {
      return expanded;
    }

    function setOverlaySpecialPickerExpanded(zoneIndex, layer) {
      expanded = { zoneIndex: zoneIndex, layer: layer };
      return expanded;
    }

    function clearOverlaySpecialPickerExpanded() {
      expanded = null;
    }

    function toggleOverlaySpecialPicker(zoneIndex, layer) {
      if (expanded && expanded.zoneIndex === zoneIndex && expanded.layer === layer) {
        expanded = null;
      } else {
        expanded = { zoneIndex: zoneIndex, layer: layer };
      }
      renderZoneDetail(zoneIndex);
    }

    global.getOverlaySpecialPickerExpanded = getOverlaySpecialPickerExpanded;
    global.setOverlaySpecialPickerExpanded = setOverlaySpecialPickerExpanded;
    global.clearOverlaySpecialPickerExpanded = clearOverlaySpecialPickerExpanded;
    global.toggleOverlaySpecialPicker = toggleOverlaySpecialPicker;
  }

  global.SPBZoneOverlaySpecialPickerControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
