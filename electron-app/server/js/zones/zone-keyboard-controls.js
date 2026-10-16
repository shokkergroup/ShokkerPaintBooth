(function(global) {
  'use strict';

  // ===== [SPB-TICKETS-2 2026-10-10 T-11] stray-key gate =====================
  // Before: `n` (add zone), Shift+M (mute), Shift+Delete (delete zone) and Ctrl+A (select
  // the whole canvas into the active zone, a red draft region) fired from anywhere the
  // page had no text field focused: with a dialog, popover, menu or panel open, with a
  // scrim over the canvas, with focus inside a floating panel, or from a held key.
  // Painters hit them by accident (s72 "red Source pane"). Now they fire only when the
  // editor workspace owns the keyboard. Shortcuts are kept; the gate only says NO when:
  //   field    a text field / select / contenteditable has the key
  //   dialog   SpbDialog is showing a prompt or confirm
  //   overlay  a modal, menu, popover or dropdown is visible (curated list, no wildcards)
  //   scrim    a big fixed layer outside the workspace covers the canvas
  //   focus    focus sits on a control outside the workspace (toolbar and header count as workspace)
  //   repeat   the key is being held (only `n`; one press = one zone)
  // Kill switches: window.SPB_TICKETS2_OFF / window.SPB_T2_T11_OFF (or localStorage '1').
  var T2_OVERLAY_SEL = [
    'dialog[open]', '[role="dialog"]', '[role="alertdialog"]', '[aria-modal="true"]',
    '[role="menu"]', '[role="listbox"]', '#spbProjectsModal', '.modal-overlay',
    '.preset-gallery-overlay', '.finish-browser-overlay', '.finish-compare-overlay',
    '.dual-shift-overlay', '.tmpl-name-overlay', '.file-picker-overlay', '.placement-map-overlay',
    '.spb-tb-pop', '.spb-pf-more-pop', '.settings-dropdown.open', '.recent-paths-dropdown',
    '.finish-popup', '.spb-render-modal'
  ].join(',');
  // ids ending Modal / Overlay count only while they are a fixed full layer (a modal), never a canvas overlay.
  var T2_FIXED_SEL = '[id$="Modal"],[id$="Overlay"]';
  var T2_WORKSPACE_SEL = 'main.main-container,#spbTopToolbar,nav.header,#toast';

  function t2off(id) {
    try {
      if (global.SPB_TICKETS2_OFF || global['SPB_T2_' + id + '_OFF']) return true;
      var ls = global.localStorage;
      return !!(ls && (ls.getItem('SPB_TICKETS2_OFF') === '1' || ls.getItem('SPB_T2_' + id + '_OFF') === '1'));
    } catch (_) { return !!(global.SPB_TICKETS2_OFF || global['SPB_T2_' + id + '_OFF']); }
  }

  function shown(el) {
    try {
      if (!el || !el.getClientRects || !el.getClientRects().length) return false;
      var n = el;
      for (var depth = 0; n && n.nodeType === 1 && depth < 8; depth++, n = n.parentElement) {
        var cs = global.getComputedStyle(n);
        if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false;
      }
      var r = el.getBoundingClientRect();
      return r.width > 1 && r.height > 1;
    } catch (_) { return false; }
  }

  function isFieldLike(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.isContentEditable) return true;
    var tag = String(el.tagName || '').toLowerCase();
    if (tag === 'textarea' || tag === 'select') return true;
    var role = el.getAttribute && el.getAttribute('role');
    if (role === 'textbox' || role === 'combobox' || role === 'searchbox' || role === 'spinbutton') return true;
    if (tag !== 'input') return false;
    var type = String(el.type || '').toLowerCase();
    return !type || ['text', 'search', 'email', 'url', 'tel', 'password', 'number', 'date',
      'datetime-local', 'month', 'time', 'week'].indexOf(type) >= 0;
  }

  function strayReason(e) {
    var doc = global.document;
    if (!doc) return '';
    var ae = doc.activeElement;
    if (isFieldLike(e && e.target) || isFieldLike(ae)) return 'field';
    var SD = global.SpbDialog;
    if (SD && typeof SD.isOpen === 'function' && SD.isOpen()) return 'dialog';
    var i, list = doc.querySelectorAll(T2_OVERLAY_SEL);
    for (i = 0; i < list.length; i++) if (shown(list[i])) return 'overlay';
    list = doc.querySelectorAll(T2_FIXED_SEL);
    for (i = 0; i < list.length; i++) {
      var f = list[i];
      if (!shown(f)) continue;
      var pos = global.getComputedStyle(f).position;
      if (pos === 'fixed' || pos === 'sticky') {
        var fr = f.getBoundingClientRect();
        if (fr.width * fr.height > 0.15 * global.innerWidth * global.innerHeight) return 'overlay';
      }
    }
    var ws = doc.querySelector('main.main-container');
    if (ws) {
      // scrim: whatever sits at the middle of the screen must belong to the workspace
      var hit = doc.elementFromPoint(Math.floor(global.innerWidth / 2), Math.floor(global.innerHeight / 2));
      if (hit && hit !== doc.body && hit !== doc.documentElement && !hit.closest(T2_WORKSPACE_SEL)) {
        for (var a = hit; a && a !== doc.body; a = a.parentElement) {
          var cs = global.getComputedStyle(a);
          if (cs.position === 'fixed' || cs.position === 'absolute') {
            var ar = a.getBoundingClientRect();
            if (ar.width * ar.height > 0.6 * global.innerWidth * global.innerHeight) return 'scrim';
          }
        }
      }
      if (ae && ae !== doc.body && ae !== doc.documentElement && !ae.closest(T2_WORKSPACE_SEL)) return 'focus';
    }
    return '';
  }

  function blocked(e, id) {
    if (t2off(id || 'T11')) return false;
    try { return !!strayReason(e); } catch (_) { return false; }
  }

  // Same check, for shortcuts that would otherwise fall through to the browser: swallow the key (no whole-page text
  // highlight from a native Ctrl+A while a dialog is open) unless a text field owns it. Returns true when blocked.
  function swallow(e, id) {
    if (t2off(id || 'T11')) return false;
    var r = '';
    try { r = strayReason(e); } catch (_) { return false; }
    if (!r) return false;
    if (r !== 'field') { try { e.preventDefault(); } catch (_) {} }
    return true;
  }

  // Toast with an Undo button for a keyboard action that just changed the document.
  // The button is live for 8 s and only while nothing else was added to the undo history.
  function undoSig() {
    var s = '';
    try {
      if (typeof global.getUnifiedUndoHistoryEntries === 'function') s += JSON.stringify(global.getUnifiedUndoHistoryEntries(1));
      if (typeof zoneUndoStack !== 'undefined') s += '|z' + zoneUndoStack.length;
    } catch (_) {}
    return s;
  }
  function toastWithUndo(msg, sigBefore) {
    var doc = global.document;
    if (typeof global.showToast !== 'function') return;
    global.showToast(msg);
    if (t2off('T11')) return;
    var t = doc && doc.getElementById('toast');
    if (!t) return;
    var sig = undoSig();
    var btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = 'spb-t2-undo';
    btn.textContent = 'Undo';
    btn.title = 'Undo this (same as Ctrl+Z)';
    btn.style.cssText = 'margin-left:10px;padding:2px 10px;border-radius:6px;border:1px solid rgba(255,255,255,.5);background:rgba(255,255,255,.16);color:inherit;font:inherit;font-weight:700;cursor:pointer;flex-shrink:0;';
    btn.addEventListener('mousedown', function(ev) { ev.preventDefault(); });   // never steal canvas focus
    btn.addEventListener('click', function(ev) {
      ev.stopPropagation();
      t.className = 'toast';
      try { clearTimeout(global.showToast._timer); } catch (_) {}
      if (undoSig() !== sig) { global.showToast('Newer edits exist - use Ctrl+Z to step back'); return; }
      if (typeof global.undoDrawStroke === 'function') global.undoDrawStroke();
      else if (typeof global.undoZoneChange === 'function') global.undoZoneChange();
    });
    t.insertBefore(btn, t.lastChild);
    try {
      clearTimeout(global.showToast._timer);
      global.showToast._timer = setTimeout(function() { t.className = 'toast'; }, 8000);
    } catch (_) {}
  }

  global.SPBStrayKeyGate = { reason: strayReason, blocked: blocked, swallow: swallow, toastWithUndo: toastWithUndo, off: t2off };

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
        if (blocked(e)) return;   // [SPB-TICKETS-2 2026-10-10 T-11] dialog / menu / popover / panel focus owns the key
        e.preventDefault();
        if (e.repeat && !t2off('T11')) return;   // holding `n` used to stack a zone per key repeat
        var zonesBefore = (typeof zones !== 'undefined' && zones && zones.length) || 0;
        var undoBefore = undoSig();
        addZone();
        var zonesAfter = (typeof zones !== 'undefined' && zones && zones.length) || 0;
        if (zonesAfter > zonesBefore && undoSig() !== undoBefore) toastWithUndo('Added Zone ' + zonesAfter);
      } else if ((e.key === 'm' || e.key === 'M') && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
        if (blocked(e)) return;
        e.preventDefault();
        toggleZoneMute(getSelectedZoneIndex());
      } else if (e.key === 'Delete' && e.shiftKey) {
        if (blocked(e)) return;
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
