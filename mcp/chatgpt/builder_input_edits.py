"""Delegate typing to the current textbox after Full Editor panel rerenders."""
def edits():
    return [
        ("if (ev.target === inp && (ev.key === 'Enter' || ev.keyCode === 13) && !ev.shiftKey) markTyped(inp.value, 'enter');", "var live = p.querySelector('.spb-pai-input'); if (ev.target === live && (ev.key === 'Enter' || ev.keyCode === 13) && !ev.shiftKey) markTyped(live.value, 'enter');", 1),
        ("if (b) markTyped(inp.value, 'send');", "if (b) { var live = p.querySelector('.spb-pai-input'); if (live) markTyped(live.value, 'send'); }", 1),
        ("inp.addEventListener('input', function () { S.liveText = String(inp.value || '').trim() ? inp.value : '';", "p.addEventListener('input', function (ev) { var live = p.querySelector('.spb-pai-input'); if (!live || ev.target !== live) return; S.liveText = String(live.value || '').trim() ? live.value : '';", 1),
    ]
