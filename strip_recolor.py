"""
Removes the Recolor feature from paint-booth-v2.html
"""
import re

FILE = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\paint-booth-v2.html'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)
step = 0

def remove_between(c, start, end, include_end=True, label=''):
    global step
    step += 1
    si = c.find(start)
    if si == -1:
        print(f'  STEP {step} [{label}]: START MARKER NOT FOUND - skipping')
        return c
    ei = c.find(end, si + len(start))
    if ei == -1:
        print(f'  STEP {step} [{label}]: END MARKER NOT FOUND - skipping')
        return c
    if include_end:
        ei += len(end)
    removed_chars = ei - si
    print(f'  STEP {step} [{label}]: removed {removed_chars} chars')
    return c[:si] + c[ei:]

def replace_str(c, old, new, label=''):
    global step
    step += 1
    if old not in c:
        print(f'  STEP {step} [{label}]: STRING NOT FOUND - skipping')
        return c
    result = c.replace(old, new, 1)
    print(f'  STEP {step} [{label}]: replaced {len(old)} chars -> {len(new)} chars')
    return result

print('=== STRIPPING RECOLOR FEATURE ===\n')

# ── 1. CSS: recolor styles block ─────────────────────────────────────────────
content = remove_between(content,
    '        .panel-mode-btn.active-recolor {',
    '        .finish-select, .intensity-select {',
    include_end=False,
    label='CSS recolor styles')

# ── 2. HTML: panel mode bar – remove entire bar (only one mode left) ─────────
content = remove_between(content,
    '        <!-- ===== PANEL MODE TOGGLE ===== -->\n        <div class="panel-mode-bar">',
    '</div>\n\n        <!-- ===== SPECMAP MODE CONTENT ===== -->',
    include_end=False,
    label='HTML panel-mode-bar')

# ── 3. HTML: entire recolorModeContent div ───────────────────────────────────
content = remove_between(content,
    '\n        <!-- ===== RECOLOR MODE CONTENT ===== -->',
    '</div><!-- /recolorModeContent -->',
    include_end=True,
    label='HTML recolorModeContent')

# ── 4. HTML: eyedropper recolor bottom bar controls ──────────────────────────
content = remove_between(content,
    '\n                    <!-- === RECOLOR BOTTOM BAR CONTROLS === -->',
    '                    </div>\n\n                </div>',
    include_end=False,
    label='HTML eyedropperRecolorControls')

# ── 5. JS: recolor state variable declarations ───────────────────────────────
content = replace_str(content,
    'let lastOriginalColor = null;  // Eyedropper color from ORIGINAL paint (pre-recolor)\n',
    '',
    label='JS lastOriginalColor var')

content = replace_str(content,
    "\n// ===== PANEL MODE =====\nlet panelMode = 'specmap';          // 'specmap' | 'recolor'\n\n// ===== PAINT RECOLOR STATE =====\nlet originalPaintImageData = null;  // Deep copy of paint pixels on load (never modified)\nlet recolorRules = [];              // [{id, sourceRGB:{r,g,b}, targetRGB:{r,g,b}, tolerance:40, enabled:true}]\nlet recolorNextId = 1;              // Auto-increment for rule IDs\nlet recolorEnabled = true;          // Global live toggle\nlet recolorMask = null;             // Uint8Array: 0=unset, 1=include, 2=exclude\nlet recolorMaskMode = null;         // null | 'include' | 'exclude'\nlet recolorMaskHasInclude = false;  // Quick flag: does mask have any include pixels?\n",
    '\n',
    label='JS recolor state vars block')

# ── 6. JS: loadPaintImageData recolor init lines ─────────────────────────────
content = replace_str(content,
    "    // Store original for recolor (deep copy)\n    originalPaintImageData = new ImageData(new Uint8ClampedArray(paintImageData.data), paintImageData.width, paintImageData.height);\n    recolorRules = []; recolorNextId = 1; recolorMask = null; recolorMaskHasInclude = false; renderRecolorRules();\n\n",
    '',
    label='JS loadPaint recolor init')

# ── 7. JS: setPanelMode + updateBottomBarForMode + updateRecolorBadge + setRecolorMaskMode + clearRecolorMask ──
content = remove_between(content,
    '// ===== PANEL MODE SWITCHING =====\nfunction setPanelMode',
    '\n// ===== PRESETS =====\n',
    include_end=False,
    label='JS panel mode / recolor UI functions')

# ── 8. JS: applyRecolorRules + refreshPaintCanvas + getOriginalColorAt + addRecolor* + toggleRecolor* + resetRecolor + renderRecolorRules ──
content = remove_between(content,
    '\n// ===== PAINT RECOLOR — CORE ALGORITHM =====\n',
    '\n// ===== PAINT PREVIEW & EYEDROPPER =====\n',
    include_end=False,
    label='JS recolor algorithm + UI functions')

# ── 9. JS: _fastRecolorArc function ──────────────────────────────────────────
content = remove_between(content,
    '\n    function _fastRecolorArc(cx, cy, radius, value) {',
    '\n    function paintRegionCircle',
    include_end=False,
    label='JS _fastRecolorArc')

# ── 10. JS: onmousemove recolor mask block ────────────────────────────────────
content = replace_str(content,
    "        // Recolor mask painting (takes priority when active)\n        if (panelMode === 'recolor' && recolorMaskMode && isDrawing) {\n            const radius = getRecolorMaskBrushSize();\n            const val = recolorMaskMode === 'include' ? 1 : 2;\n            paintRecolorMaskCircle(pos.x, pos.y, radius, val);\n            _fastRecolorArc(pos.x, pos.y, radius, val); // fast GPU draw — no full ImageData rebuild\n            return;\n        }\n\n        if (canvasMode === 'eyedropper')",
    "        if (canvasMode === 'eyedropper')",
    label='JS onmousemove recolor block')

# ── 11. JS: onmousedown recolor mask block ────────────────────────────────────
content = replace_str(content,
    "        // Recolor mask painting (takes priority when active)\n        if (panelMode === 'recolor' && recolorMaskMode) {\n            isDrawing = true;\n            const radius = getRecolorMaskBrushSize();\n            paintRecolorMaskCircle(pos.x, pos.y, radius, recolorMaskMode === 'include' ? 1 : 2);\n            renderRecolorMaskOverlay();\n            return;\n        }\n\n        if (canvasMode === 'eyedropper')",
    "        if (canvasMode === 'eyedropper')",
    label='JS onmousedown recolor block')

# ── 12. JS: onmouseup recolor block ──────────────────────────────────────────
content = replace_str(content,
    "        // Recolor mask: full sync + apply rules after mask stroke finishes\n        if (panelMode === 'recolor' && recolorMaskMode && isDrawing) {\n            renderRecolorMaskOverlay(); // Full sync\n            applyRecolorRules();\n        }\n        isDrawing = false;",
    "        isDrawing = false;",
    label='JS onmouseup recolor block')

# ── 13. JS: eyedropper lastOriginalColor call & recolor count update ──────────
content = replace_str(content,
    "            lastOriginalColor = getOriginalColorAt(pos.x, pos.y);  // Pre-recolor color for recolor tool\n",
    '',
    label='JS eyedropper lastOriginalColor call')

content = replace_str(content,
    "            // Update recolor bottom bar count\n            const recolorCountEl = document.getElementById('eyedropperRecolorCount');\n            if (recolorCountEl) recolorCountEl.textContent = recolorRules.length;\n",
    '',
    label='JS eyedropper recolor count update')

# ── 14. JS: _doRenderRegionOverlay recolor check ─────────────────────────────
content = replace_str(content,
    "    // In recolor mode, show recolor mask instead of zone masks\n    if (panelMode === 'recolor' && recolorMask) {\n        renderRecolorMaskOverlay();\n        return;\n    }\n\n    const paintCanvas = document.getElementById('paintCanvas');\n    const regionCanvas = document.getElementById('regionCanvas');",
    "    const paintCanvas = document.getElementById('paintCanvas');\n    const regionCanvas = document.getElementById('regionCanvas');",
    label='JS _doRenderRegionOverlay recolor check')

# ── 15. JS: RECOLOR MASK PAINTING section (paintRecolorMaskCircle + renderRecolorMaskOverlay + toggleRecolorMaskOverlay + getRecolorMaskBrushSize) ──
content = remove_between(content,
    '\n// ===== RECOLOR MASK PAINTING & OVERLAY =====\n',
    '\nfunction renderGradientPreview',
    include_end=False,
    label='JS recolor mask painting section')

# ── REPORT ───────────────────────────────────────────────────────────────────
new_len = len(content)
print(f'\nOriginal: {original_len:,} chars  |  New: {new_len:,} chars  |  Removed: {original_len - new_len:,} chars')

remaining = re.findall(r'recolor', content, re.IGNORECASE)
print(f'Remaining "recolor" occurrences: {len(remaining)}')
if remaining:
    # Find line numbers
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'recolor' in line.lower():
            print(f'  Line {i}: {line.strip()[:100]}')

# Write file
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)
print('\nFile written successfully.')
