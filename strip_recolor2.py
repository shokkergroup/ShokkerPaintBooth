"""
Second pass: removes remaining recolor refs from paint-booth-v2.html
"""
import re

FILE = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\paint-booth-v2.html'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

original_len = len(content)
step = 0

def drop(c, old, label=''):
    global step
    step += 1
    if old not in c:
        print(f'  [{step}] SKIP (not found): {label}')
        return c
    result = c.replace(old, '', 1)
    print(f'  [{step}] OK removed {len(old)} chars: {label}')
    return result

def drop_all(c, old, label=''):
    global step
    step += 1
    count = c.count(old)
    if count == 0:
        print(f'  [{step}] SKIP (not found): {label}')
        return c
    result = c.replace(old, '')
    print(f'  [{step}] OK removed {count}x {len(old)} chars each: {label}')
    return result

def remove_between(c, start, end, include_end=True, label=''):
    global step
    step += 1
    si = c.find(start)
    if si == -1:
        print(f'  [{step}] SKIP start not found: {label}')
        return c
    ei = c.find(end, si + len(start))
    if ei == -1:
        print(f'  [{step}] SKIP end not found: {label}')
        return c
    if include_end:
        ei += len(end)
    print(f'  [{step}] OK removed {ei-si} chars: {label}')
    return c[:si] + c[ei:]

print('=== SECOND PASS: STRIP REMAINING RECOLOR REFS ===\n')

# ── 1. autoSave: remove recolor fields from saved state object ────────────────
content = drop(content,
    "        recolorRules: recolorRules.map(r => ({...r})),\n",
    'autoSave: recolorRules field')

content = drop(content,
    "        panelMode: panelMode,\n",
    'autoSave: panelMode field')

content = drop(content,
    "        recolorMask: recolorMask && recolorMask.some(v => v > 0)\n"
    "            ? encodeRegionMaskRLE(recolorMask, document.getElementById('paintCanvas')?.width || 0, document.getElementById('paintCanvas')?.height || 0)\n"
    "            : null,\n"
    "        recolorMaskHasInclude: recolorMaskHasInclude,\n",
    'autoSave: recolorMask + recolorMaskHasInclude fields')

# ── 2. loadCfg: remove recolor restore blocks ─────────────────────────────────
content = drop(content,
    "    // Restore recolor rules if saved\n"
    "    if (cfg.recolorRules && Array.isArray(cfg.recolorRules)) {\n"
    "        recolorRules = cfg.recolorRules.map(r => ({...r}));\n"
    "        recolorNextId = recolorRules.reduce((max, r) => Math.max(max, r.id + 1), 1);\n"
    "        renderRecolorRules();\n"
    "        if (originalPaintImageData) applyRecolorRules();\n"
    "    }\n"
    "    // Restore recolor mask if saved\n"
    "    if (cfg.recolorMask && cfg.recolorMask.runs) {\n"
    "        try {\n"
    "            const runs = cfg.recolorMask.runs;\n"
    "            const total = cfg.recolorMask.width * cfg.recolorMask.height;\n"
    "            recolorMask = new Uint8Array(total);\n"
    "            let idx = 0;\n"
    "            for (const run of runs) {\n"
    "                const val = run[0], count = run[1];\n"
    "                const end = Math.min(idx + count, total);\n"
    "                recolorMask.fill(val, idx, end);\n"
    "                idx = end;\n"
    "            }\n"
    "            recolorMaskHasInclude = cfg.recolorMaskHasInclude || false;\n"
    "        } catch(e) {\n"
    "            recolorMask = null;\n"
    "            recolorMaskHasInclude = false;\n"
    "        }\n"
    "    }\n"
    "    // Restore panel mode\n"
    "    if (cfg.panelMode) setPanelMode(cfg.panelMode);\n",
    'loadCfg: recolor+panelMode restore blocks')

# ── 3. Preset loading: remove recolor rules application ───────────────────────
content = drop(content,
    "\n    // Apply recolor rules if present\n"
    "    if (preset.recolorRules && Array.isArray(preset.recolorRules)) {\n"
    "        recolorRules = preset.recolorRules.map(r => ({...r}));\n"
    "        recolorNextId = recolorRules.reduce((max, r) => Math.max(max, r.id + 1), 1);\n"
    "        renderRecolorRules();\n"
    "        if (originalPaintImageData) applyRecolorRules();\n"
    "    }\n",
    'preset load: apply recolor rules block')

# ── 4. Paint load (3 occurrences): remove recolor init lines ──────────────────
content = drop_all(content,
    "                // Store original for recolor (deep copy)\n"
    "                originalPaintImageData = new ImageData(new Uint8ClampedArray(paintImageData.data), paintImageData.width, paintImageData.height);\n"
    "                recolorRules = []; recolorNextId = 1; recolorMask = null; recolorMaskHasInclude = false; renderRecolorRules();\n\n",
    'paint load (indented x16): recolor init')

content = drop_all(content,
    "            // Store original for recolor (deep copy)\n"
    "            originalPaintImageData = new ImageData(new Uint8ClampedArray(paintImageData.data), paintImageData.width, paintImageData.height);\n"
    "            recolorRules = []; recolorNextId = 1; recolorMask = null; recolorMaskHasInclude = false; renderRecolorRules();\n\n",
    'paint load (indented x12): recolor init')

# ── 5. HSV utility functions (only used by recolor) ──────────────────────────
content = remove_between(content,
    '\n// ===== PAINT RECOLOR — HSV UTILITIES =====\n',
    '\n}\n\n// =====',
    include_end=False,
    label='HSV utility functions')
# Also remove the trailing closing brace of hsvToRgb
content = drop(content,
    "    return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255), b: Math.round((b + m) * 255) };\n}\n\n",
    'HSV hsvToRgb closing brace')

# ── 6. Render API: remove recolor_rules from render body ─────────────────────
content = drop(content,
    "\n    // Include recolor rules if active\n"
    "    if (typeof recolorRules !== 'undefined' && typeof recolorEnabled !== 'undefined' && recolorEnabled && recolorRules.length > 0) {\n"
    "        const activeRules = recolorRules.filter(r => r.enabled);\n"
    "        if (activeRules.length > 0) {\n"
    "            body.recolor_rules = activeRules.map(r => ({\n"
    "                source_rgb: [r.sourceRGB.r, r.sourceRGB.g, r.sourceRGB.b],\n"
    "                target_rgb: [r.targetRGB.r, r.targetRGB.g, r.targetRGB.b],\n"
    "                tolerance: r.tolerance, hue_shift: true\n"
    "            }));\n"
    "        }\n"
    "    }\n",
    'render API body: recolor_rules block')

# ── 7. batch render extras (line ~13893) ─────────────────────────────────────
content = drop(content,
    "            if (extras.recolor_rules && extras.recolor_rules.length > 0) {\n"
    "                body.recolor_rules = extras.recolor_rules;\n"
    "                if (extras.recolor_mask) { body.recolor_mask = extras.recolor_mask; body.recolor_mask_has_include = extras.recolor_mask_has_include || false; }\n"
    "            }\n",
    'batch render: extras recolor_rules pass-through')

# ── 8. render extras builder instance 1 (line ~14218) ────────────────────────
content = drop(content,
    "    if (recolorRules.length > 0 && recolorEnabled) {\n"
    "        const ar = recolorRules.filter(r => r.enabled);\n"
    "        if (ar.length) {\n"
    "            extras.recolor_rules = ar.map(r => ({source_rgb:[r.sourceRGB.r,r.sourceRGB.g,r.sourceRGB.b], target_rgb:[r.targetRGB.r,r.targetRGB.g,r.targetRGB.b], tolerance:r.tolerance, hue_shift:true}));\n"
    "            if (recolorMask && recolorMask.some(v => v > 0)) {\n"
    "                const pc = document.getElementById('paintCanvas');\n"
    "                extras.recolor_mask = encodeRegionMaskRLE(recolorMask, pc.width, pc.height);\n"
    "                extras.recolor_mask_has_include = recolorMaskHasInclude;\n"
    "            }\n"
    "        }\n"
    "    }\n",
    'extras builder 1: recolor_rules block')

# ── 9. render extras builder instance 2 (season render, line ~14339) ─────────
content = drop(content,
    "        if (recolorRules.length > 0 && recolorEnabled) {\n"
    "            const ar = recolorRules.filter(r => r.enabled);\n"
    "            if (ar.length) {\n"
    "                extras.recolor_rules = ar.map(r => ({source_rgb:[r.sourceRGB.r,r.sourceRGB.g,r.sourceRGB.b], target_rgb:[r.targetRGB.r,r.targetRGB.g,r.targetRGB.b], tolerance:r.tolerance, hue_shift:true}));\n"
    "                if (recolorMask && recolorMask.some(v => v > 0)) {\n"
    "                    const pc = document.getElementById('paintCanvas');\n"
    "                    extras.recolor_mask = encodeRegionMaskRLE(recolorMask, pc.width, pc.height);\n"
    "                    extras.recolor_mask_has_include = recolorMaskHasInclude;\n"
    "                }\n"
    "            }\n"
    "        }\n",
    'extras builder 2 (season): recolor_rules block')

# ── 10. render extras builder instance 3 (main render, line ~14530) ───────────
content = drop(content,
    "    // Paint recolor rules\n"
    "    if (recolorRules.length > 0 && recolorEnabled) {\n"
    "        const activeRules = recolorRules.filter(r => r.enabled);\n"
    "        if (activeRules.length > 0) {\n"
    "            extras.recolor_rules = activeRules.map(r => ({\n"
    "                source_rgb: [r.sourceRGB.r, r.sourceRGB.g, r.sourceRGB.b],\n"
    "                target_rgb: [r.targetRGB.r, r.targetRGB.g, r.targetRGB.b],\n"
    "                tolerance: r.tolerance, hue_shift: true\n"
    "            }));\n"
    "            if (recolorMask && recolorMask.some(v => v > 0)) {\n"
    "                const pc = document.getElementById('paintCanvas');\n"
    "                extras.recolor_mask = encodeRegionMaskRLE(recolorMask, pc.width, pc.height);\n"
    "                extras.recolor_mask_has_include = recolorMaskHasInclude;\n"
    "            }\n"
    "        }\n"
    "    }\n",
    'extras builder 3 (main): recolor_rules block')

# ── REPORT ────────────────────────────────────────────────────────────────────
new_len = len(content)
print(f'\nOriginal: {original_len:,}  |  New: {new_len:,}  |  Removed: {original_len - new_len:,} chars')

remaining = [(i+1, line.strip()[:90]) for i, line in enumerate(content.split('\n'))
             if 'recolor' in line.lower()]
print(f'Remaining "recolor" lines: {len(remaining)}')
for lineno, text in remaining:
    print(f'  L{lineno}: {text}')

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)
print('\nFile written.')
