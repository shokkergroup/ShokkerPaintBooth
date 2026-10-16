"""Explicit target/result adapters around the existing native Color Replace.

SPB-93: same source raster kernel, selection clipping and transactional commit.
No selected-layer switch, flattened paint edit, or new recolouring algorithm.
"""


def canvas_edits(source):
    start = source.index('function autoColorReplace(')
    end = source.index('// 2026-05-29 SPB tool-QA', source.index('\n}', start) + 2)
    before = source[start:end]
    after = before
    swaps = [
        ('function autoColorReplace(targetHex, replacementHex, tolerance) {',
         'window.SPB_AI_EXPLICIT_COLOR_REPLACE = true;\nfunction autoColorReplace(targetHex, replacementHex, tolerance, explicitTarget) {'),
        ("const target = _getAdjustmentTarget('color replace');", "const target = explicitTarget || _getAdjustmentTarget('color replace');"),
        ("        return;\n    }\n    target.ctx.putImageData", "        return { ok: true, unchanged: true, pixels: 0 };\n    }\n    target.ctx.putImageData"),
        ("    if (_commitAdjustment(target) && typeof showToast === 'function') showToast(`Replaced ${count.toLocaleString()} pixels: ${normalizedTarget} -> ${normalizedReplacement}`);",
         "    const committed = _commitAdjustment(target);\n    if (committed && typeof showToast === 'function') showToast(`Replaced ${count.toLocaleString()} pixels: ${normalizedTarget} -> ${normalizedReplacement}`);\n    return { ok: true, unchanged: !committed, pixels: committed ? count : 0 };"),
    ]
    for old,new in swaps:
        assert after.count(old) == 1, old
        after = after.replace(old,new)
    first = (before,after,1)
    start = source.index('function _getAdjustmentTarget()')
    end = source.index('function _commitAdjustment(',start)
    before = source[start:end]
    after = before.replace("const adjustmentLabel = arguments[0] || 'adjust image';", "const adjustmentLabel = arguments[0] || 'adjust image';\n    const adjustmentLayerId = arguments.length > 1 ? arguments[1] : _selectedLayerId;")
    assert before.count('_selectedLayerId') == 2
    # Only target selection changes. Selection mask/lock/stroke/history semantics stay native.
    after = after.replace('if (_selectedLayerId && _psdLayersLoaded)', 'if (adjustmentLayerId && _psdLayersLoaded)').replace('l.id === _selectedLayerId', 'l.id === adjustmentLayerId')
    return [first,(before,after,1)]
