/* ============================================================================
 * SPB EXPERIMENTAL FEATURES MENU — 2026-06-13 (owner: ricky@shokkergroup.com)
 * ----------------------------------------------------------------------------
 * Injects ONE "EXPERIMENTAL FEATURES" dropdown onto the top tool bar tabs row
 * (#spbTopToolbar — the row with HISTORY / SELECT / RETOUCH / MASK / TRANSFORM /
 * ADJUST / FINISHES / MORE). It is pushed to the FAR RIGHT (margin-left:auto)
 * and visually separated from the tool-category tabs with a leading separator,
 * using the empty room to the right of MORE.
 *
 * The dropdown shows a muted disclaimer at the top, then three clickable items:
 *   - Design It        -> window.SPBLiveryDesigner.open()
 *   - Photo -> Livery  -> window.SPBPhotoLivery.open()
 *   - Shokker-ize      -> window.shokkerizeCurrentPaint()  (fallback open APIs)
 *
 * Self-contained: builds its own native-<details> dropdown (matching the app's
 * .spb-tb-menu / .spb-tb-summary / .spb-tb-pop dark-neon look) plus a tiny
 * scoped <style> for the experimental accent + disclaimer. No external CSS or
 * markup edits required. The feature open APIs may not exist yet at load time,
 * so they are looked up LAZILY on click.
 *
 * Guards: window.__SPB_EXPERIMENTAL_MENU_LOADED prevents double-injection.
 * No-ops gracefully if the toolbar row (#spbTopToolbar) is not found.
 * Set window.SPB_EXPERIMENTAL_MENU_DISABLE = true before load to disable.
 * ========================================================================== */
(function () {
  'use strict';

  if (window.__SPB_EXPERIMENTAL_MENU_LOADED) return;
  window.__SPB_EXPERIMENTAL_MENU_LOADED = true;
  if (window.SPB_EXPERIMENTAL_MENU_DISABLE) return;

  var TOOLBAR_ID = 'spbTopToolbar';
  var MENU_ID = 'spbExperimentalMenu';
  var STYLE_ID = 'spbExperimentalMenuStyle';

  var DISCLAIMER =
    'These features are long-term goals and purely being used for ' +
    'Experimental Purposes at this time';

  // Each item resolves its launcher LAZILY (the SPB* APIs are defined by their
  // own feature scripts and may load after this one). `fns` lists candidate
  // expressions in priority order; the first that resolves to a function runs.
  var ITEMS = [
    {
      icon: '✨',
      label: 'Design It',
      title: 'AI Livery Designer — describe a livery and auto-build the zones',
      fns: ['SPBLiveryDesigner.open']
    },
    {
      icon: '🖼️',
      label: 'Photo → Livery',
      title: 'Photo to Livery — turn a reference photo into a zoned livery',
      fns: ['SPBPhotoLivery.open']
    },
    {
      icon: '⚡',
      label: 'Shokker-ize',
      title: 'Shokker-ize — auto-generate an angle-reactive color-shift spec ' +
             'from the current paint',
      // shokkerize.js exposes window.shokkerizeCurrentPaint(); the SPB* forms
      // are accepted as forward-compatible fallbacks if an integrator adds them.
      fns: ['shokkerizeCurrentPaint', 'SPBShokkerize.open', 'SPBShokkerize.run']
    }
  ];

  // Resolve a dotted path ("a.b.c") against window; return the value or undefined.
  function resolve(path) {
    var parts = path.split('.');
    var ctx = window;
    for (var i = 0; i < parts.length; i++) {
      if (ctx == null) return undefined;
      ctx = ctx[parts[i]];
    }
    return ctx;
  }

  // Run the first resolvable launcher for an item; toast/log if none found.
  function launch(item) {
    for (var i = 0; i < item.fns.length; i++) {
      var fn = resolve(item.fns[i]);
      if (typeof fn === 'function') {
        try {
          fn.call(window);
        } catch (e) {
          try { console.error('[experimental-menu] "' + item.label + '" threw:', e); } catch (_) {}
        }
        return true;
      }
    }
    var msg = '“' + item.label + '” is not available yet.';
    try { console.warn('[experimental-menu] ' + msg + ' (tried ' + item.fns.join(', ') + ')'); } catch (_) {}
    if (typeof window.showToast === 'function') {
      try { window.showToast(msg); } catch (_) {}
    }
    return false;
  }

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css =
      // Push the experimental tab to the far right of the (nowrap) tool bar and
      // give it breathing room from the tool-category tabs.
      '#' + MENU_ID + '{margin-left:auto;}' +
      // Subtle "experimental" accent on the summary so it reads as separate.
      '#' + MENU_ID + ' > .spb-tb-summary{' +
        'color:var(--accent-orange,#ff9d4d);' +
        'border-color:rgba(255,157,77,0.35);' +
        'background:rgba(255,157,77,0.06);' +
      '}' +
      '#' + MENU_ID + '[open] > .spb-tb-summary,' +
      '#' + MENU_ID + ' > .spb-tb-summary:hover{' +
        'color:var(--accent-orange,#ff9d4d);' +
        'border-color:rgba(255,157,77,0.6);' +
        'background:rgba(255,157,77,0.12);' +
      '}' +
      // Muted disclaimer block at the top of the dropdown.
      '#' + MENU_ID + ' .spb-exp-note{' +
        'font-size:10px;line-height:1.5;font-weight:600;' +
        'color:var(--text-dim,#6b7787);' +
        'padding:4px 8px 8px;' +
        'max-width:240px;white-space:normal;' +
        'border-bottom:1px solid var(--border,rgba(255,255,255,0.1));' +
        'margin-bottom:4px;text-transform:none;letter-spacing:0;' +
      '}' +
      '#' + MENU_ID + ' .spb-exp-note-tag{' +
        'display:block;font-size:9px;font-weight:800;letter-spacing:0.8px;' +
        'text-transform:uppercase;color:var(--accent-orange,#ff9d4d);' +
        'margin-bottom:3px;' +
      '}';
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
  }

  // Build a single <button class="vtool-btn"> menu row (matches .spb-tb-pop rows).
  function makeRow(item) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'vtool-btn';
    btn.title = item.title;
    btn.setAttribute('aria-label', item.label);

    var ico = document.createElement('span');
    ico.className = 'spb-mi-ico';
    ico.textContent = item.icon;
    btn.appendChild(ico);
    btn.appendChild(document.createTextNode(' ' + item.label));

    btn.addEventListener('click', function () {
      launch(item);
      // Close the dropdown after a choice (mirrors the bar's native behavior).
      var details = document.getElementById(MENU_ID);
      if (details) details.removeAttribute('open');
    });
    return btn;
  }

  function build() {
    var bar = document.getElementById(TOOLBAR_ID);
    if (!bar) {
      try { console.warn('[experimental-menu] toolbar #' + TOOLBAR_ID + ' not found — skipping.'); } catch (_) {}
      return;
    }
    if (document.getElementById(MENU_ID)) return; // already built

    // Visual separator so the experimental tab reads as detached from the tabs.
    var sep = document.createElement('span');
    sep.className = 'spb-tb-sep';
    sep.setAttribute('aria-hidden', 'true');
    // margin-left:auto on the <details> already pushes both to the far right; the
    // separator sits immediately left of the experimental tab.

    var details = document.createElement('details');
    details.className = 'spb-tb-menu spb-tb-menu-right';
    details.id = MENU_ID;

    var summary = document.createElement('summary');
    summary.className = 'spb-tb-summary';
    summary.title = 'Experimental Features — long-term goals, in testing';
    summary.appendChild(document.createTextNode('Experimental Features '));
    var caret = document.createElement('span');
    caret.className = 'spb-tb-caret';
    caret.textContent = '▾';
    summary.appendChild(caret);
    details.appendChild(summary);

    var pop = document.createElement('div');
    pop.className = 'spb-tb-pop';

    var note = document.createElement('div');
    note.className = 'spb-exp-note';
    var tag = document.createElement('span');
    tag.className = 'spb-exp-note-tag';
    tag.textContent = 'Experimental';
    note.appendChild(tag);
    note.appendChild(document.createTextNode(DISCLAIMER));
    pop.appendChild(note);

    for (var i = 0; i < ITEMS.length; i++) {
      pop.appendChild(makeRow(ITEMS[i]));
    }
    details.appendChild(pop);

    // Append at the END of the bar (after MORE) — far right of the tabs row.
    bar.appendChild(sep);
    bar.appendChild(details);

    // The bar's own glue (close-on-outside-click / Escape / one-open-at-a-time)
    // is bound to #spbTopToolbar and operates on `details.spb-tb-menu`, so this
    // dropdown is picked up automatically. Belt-and-suspenders: also close on a
    // document click outside our own element.
    document.addEventListener('click', function (e) {
      if (!details.open) return;
      if (!details.contains(e.target)) details.removeAttribute('open');
    });
  }

  function init() {
    injectStyle();
    build();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
