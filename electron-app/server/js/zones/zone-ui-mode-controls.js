(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var storage = deps.localStorage || global.localStorage;
    var requestFrame = deps.requestAnimationFrame || global.requestAnimationFrame || function (fn) { return setTimeout(fn, 0); };
    var renderZones = deps.renderZones || function () {};
    var mode = readStorage('shokker_ui_mode', 'advanced');
    var scale = parseFloat(readStorage('shokker_ui_scale', '1.0')) || 1.0;
    var scaleSteps = [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4, 1.5];

    function readStorage(key, fallback) {
      try { return storage ? storage.getItem(key) || fallback : fallback; } catch (e) { return fallback; }
    }

    function writeStorage(key, value) {
      try { if (storage) storage.setItem(key, value); } catch (e) {}
    }

    function syncModeGlobals() {
      global._uiMode = mode;
      global.easyMode = mode === 'simple';
    }

    function applyModeClass() {
      if (!doc || !doc.body) return;
      doc.body.classList.toggle('simple-mode', mode === 'simple');
      doc.body.classList.toggle('easy-mode', mode === 'simple');
    }

    function updateModeToggleUI() {
      var toggle = doc && doc.getElementById ? doc.getElementById('ui-mode-toggle') : null;
      if (!toggle) return;
      toggle.querySelectorAll('.ui-mode-option').forEach(function (opt) {
        opt.classList.toggle('active', opt.getAttribute('data-mode') === mode);
      });
    }

    function toggleUIMode() {
      mode = mode === 'advanced' ? 'simple' : 'advanced';
      syncModeGlobals();
      writeStorage('shokker_ui_mode', mode);
      applyModeClass();
      updateModeToggleUI();
      renderZones();
    }

    function updateScaleLabel() {
      var label = doc && doc.getElementById ? doc.getElementById('uiScaleLabel') : null;
      if (label) label.textContent = Math.round(scale * 100) + '%';
    }

    function setUIScale(direction) {
      if (direction === 0) {
        scale = 1.0;
      } else {
        var currentIdx = scaleSteps.indexOf(scale);
        var idx = currentIdx >= 0 ? currentIdx : scaleSteps.findIndex(function (step) { return step >= scale; });
        var newIdx = Math.max(0, Math.min(scaleSteps.length - 1, (idx >= 0 ? idx : 6) + direction));
        scale = scaleSteps[newIdx];
      }
      if (doc && doc.body) doc.body.style.zoom = scale;
      writeStorage('shokker_ui_scale', String(scale));
      updateScaleLabel();
    }

    function onKeydown(e) {
      if (e.defaultPrevented || !e.ctrlKey) return;
      if (e.key === '=' || e.key === '+') { e.preventDefault(); setUIScale(1); }
      else if (e.key === '-') { e.preventDefault(); setUIScale(-1); }
      else if (e.key === '0') { e.preventDefault(); setUIScale(0); }
    }

    syncModeGlobals();
    applyModeClass();
    if (scale !== 1.0 && doc && doc.body) doc.body.style.zoom = scale;
    if (doc && doc.addEventListener) doc.addEventListener('keydown', onKeydown);
    requestFrame(updateModeToggleUI);
    requestFrame(updateScaleLabel);

    global._updateModeToggleUI = updateModeToggleUI;
    global.toggleUIMode = toggleUIMode;
    global.toggleEasyMode = toggleUIMode;
    global.setUIScale = setUIScale;
  }

  global.SPBZoneUiModeControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
