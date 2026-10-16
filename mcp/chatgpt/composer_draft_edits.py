"""Separate an unsent follow-up draft from the current guide/planner state."""

def edits(relative):
    if relative == 'js/spb-pro-ai.js':
        return [
            ('    var _composerFinishing = 0;', '    var _composerFinishing = 0, _composerHeldDraft = false;', 1),
            ('        var pending = composerPending(), checking = !_busy && _composerFinishing > 0;', '''        var pending = composerPending(), checking = !_busy && _composerFinishing > 0;
        var hold = pending || _composerHeldDraft;
        _panel.setAttribute('data-spb-compose-hold', hold ? '1' : '0');
        if (hold) ['.spb-pbn', '.spb-ob'].forEach(function (selector) { var dock = _panel.querySelector(selector); if (dock) dock.hidden = true; });
        Array.prototype.forEach.call(_panel.querySelectorAll('[data-act="undo"],[data-act="refine"],[data-act="another"],[data-act="askai"],[data-act="clear"]'), function (action) {
            if (pending) {
                if (!Object.prototype.hasOwnProperty.call(action, '__spbComposerDisabled')) action.__spbComposerDisabled = !!action.disabled;
                action.disabled = true;
            } else if (Object.prototype.hasOwnProperty.call(action, '__spbComposerDisabled')) {
                action.disabled = action.__spbComposerDisabled; delete action.__spbComposerDisabled;
            }
        });''', 1),
            ('        if (composerPending()) { composerSync(); return; }', '        if (composerPending()) { composerSync(); return; }\n        _composerHeldDraft = false; composerSync();', 1),
            ("        _panel.addEventListener('click', function (ev) {", '''        // An unsent draft is not a new planner turn. Capture before guide listeners.
        _panel.addEventListener('input', function (ev) {
            if (!ev.target || ev.target !== _panel.querySelector('.spb-pai-input')) return;
            if (!composerPending() && !_composerHeldDraft) return;
            _composerHeldDraft = !!String(ev.target.value || '').trim();
            composerSync();
            if (_composerHeldDraft || composerPending()) ev.stopImmediatePropagation();
        }, true);
        _panel.addEventListener('keydown', function (ev) {
            if (ev.target === _panel.querySelector('.spb-pai-input') && (ev.key === 'Enter' || ev.keyCode === 13) && !ev.shiftKey && composerPending()) {
                ev.preventDefault(); ev.stopImmediatePropagation(); composerSync();
            }
        }, true);
        _panel.addEventListener('click', function (ev) {''', 1),
            ("            if (b.hasAttribute('data-say'))", "            if (composerPending() && /^(undo|refine|another|askai|clear)$/.test(b.getAttribute('data-act') || '')) { composerSync(); return; }\n            if (b.hasAttribute('data-say'))", 1),
        ]
    if relative == 'js/spb-pbn.js':
        return [('        var d = ensureDock(); if (!d) return;', "        var d = ensureDock(); if (!d) return;\n        var composerPanel = panel(); if (composerPanel && composerPanel.getAttribute('data-spb-compose-hold') === '1') { d.hidden = true; return; }", 1)]
    if relative == 'js/spb-offline-builder.js':
        return [('        var d = dock(); if (!d) return;', "        var d = dock(); if (!d) return;\n        var composerPanel = panel(); if (composerPanel && composerPanel.getAttribute('data-spb-compose-hold') === '1') { d.hidden = true; return; }", 1)]
    return []
