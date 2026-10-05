(function (global) {
  'use strict';

  var renderStartTime = null;
  var renderElapsedTimer = null;

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var setIntervalFn = deps.setInterval || global.setInterval;
    var clearIntervalFn = deps.clearInterval || global.clearInterval;

    function startRenderTimer() {
      // [SPB DOUBLE-RENDER TIMER 2026-08-17] Twin of the paint-booth-2-state-zones.js fix:
      // a second start() leaked the first interval, which then rendered Date.now() - null
      // (~1.79 billion seconds) on the button forever. Self-cleaning start + self-destructing
      // orphan tick. See that file's comment for the full mechanism.
      stopRenderTimer();
      renderStartTime = Date.now();
      var btn = doc && doc.getElementById ? doc.getElementById('btnRender') : null;
      var myTimer = setIntervalFn(function () {
        if (renderStartTime === null || renderElapsedTimer !== myTimer) {
          clearIntervalFn(myTimer);
          return;
        }
        if (!btn) return;
        var elapsed = ((Date.now() - renderStartTime) / 1000).toFixed(0);
        btn.textContent = 'RENDERING... ' + elapsed + 's';
      }, 500);
      renderElapsedTimer = myTimer;
    }

    function stopRenderTimer() {
      if (renderElapsedTimer) {
        clearIntervalFn(renderElapsedTimer);
        renderElapsedTimer = null;
      }
      renderStartTime = null;
    }

    function updateOutputPath() {
      var input = doc && doc.getElementById ? doc.getElementById('iracingId') : null;
      var iracingId = input && input.value ? input.value.trim() : '';
      var preview = doc && doc.getElementById ? doc.getElementById('outputFilenamePreview') : null;
      if (preview) preview.textContent = 'car_num_' + iracingId + '.tga + car_spec_' + iracingId + '.tga';
    }

    global.startRenderTimer = startRenderTimer;
    global.stopRenderTimer = stopRenderTimer;
    global.updateOutputPath = updateOutputPath;
  }

  global.SPBZoneRenderChromeControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
