        // ============================================================
        // PAINT-BOOTH-3-CANVAS.JS - File picker, paint preview, canvas tools
        // ============================================================
        // Purpose: Script generation, source paint browser, file picker, paint preview canvas,
        //          eyedropper/brush/wand/spatial, mask ops, canvas zoom/pan.
        // Deps:    paint-booth-1-data.js, paint-booth-2-state-zones.js (zones, paintImageData).
        // Edit:    File picker → filePickerNavigate, server file picker. Canvas → setupCanvasHandlers,
        //          canvasMode, magic wand, spatial mask. Zoom/pan → canvasZoom.
        // See:     PROJECT_STRUCTURE.md in this folder.
        // ============================================================

        // ===== SCRIPT GENERATION =====
        function formatColorForPython(color, zone) {
            // Multi-color zone: output a list of selectors
            if (zone && zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
                const selectors = zone.colors.map(c =>
                    `{"color_rgb": [${c.color_rgb[0]}, ${c.color_rgb[1]}, ${c.color_rgb[2]}], "tolerance": ${c.tolerance || 40}}`
                );
                return `[${selectors.join(', ')}]`;
            }
            // If zone has a spatial region but no color, use "everything" as fallback
            // (the region mask will override color detection in the engine)
            if (color === null) {
                if (zone && zone.regionMask && zone.regionMask.some(v => v > 0)) return '"everything"';
                return '"everything"';
            }
            if (typeof color === 'string') return `"${color}"`;
            if (typeof color === 'object' && !Array.isArray(color) && color.color_rgb) {
                return `{"color_rgb": [${color.color_rgb[0]}, ${color.color_rgb[1]}, ${color.color_rgb[2]}], "tolerance": ${color.tolerance || 40}}`;
            }
            if (Array.isArray(color)) {
                // Already an array of selectors
                const selectors = color.map(c =>
                    `{"color_rgb": [${c.color_rgb[0]}, ${c.color_rgb[1]}, ${c.color_rgb[2]}], "tolerance": ${c.tolerance || 40}}`
                );
                return `[${selectors.join(', ')}]`;
            }
            return '"everything"';
        }

        function generateScript() {
            // Validate
            const paintFile = document.getElementById('paintFile').value.trim();
            const outputDir = document.getElementById('outputDir').value.trim();
            const iracingId = document.getElementById('iracingId').value.trim();

            if (!paintFile) { showToast('Set the Source Paint path in the header bar!', true); return; }
            if (!outputDir) { showToast('Set the iRacing Paint Folder path in Car Info!', true); return; }

            const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
            if (validZones.length === 0) { showToast('At least one zone needs a base/finish AND a color or drawn region!', true); return; }

            // Build zones python array, including region mask references
            const canvas = document.getElementById('paintCanvas');
            const canvasW = canvas?.width || 2048;
            const canvasH = canvas?.height || 2048;

            // Encode any region masks
            const regionMasks = {};
            validZones.forEach((z, i) => {
                if (z.regionMask && z.regionMask.some(v => v > 0)) {
                    const rle = encodeRegionMaskRLE(z.regionMask, canvasW, canvasH);
                    regionMasks[z.name] = rle;
                }
            });

            const zonesStr = validZones.map(z => {
                const colorPy = formatColorForPython(z.color, z);
                const hasRegion = regionMasks[z.name] ? 'True' : 'False';
                let finishPart;
                if (z.base) {
                    finishPart = `"base": "${z.base}", "pattern": "${z.pattern || 'none'}"`;
                    if (z.scale && z.scale !== 1.0) finishPart += `, "scale": ${z.scale}`;
                    // Pattern stack
                    if (z.patternStack && z.patternStack.length > 0) {
                        const stack = z.patternStack.filter(l => l.id && l.id !== 'none');
                        if (stack.length > 0) {
                            const stackPy = stack.map(l => `{"id": "${l.id}", "opacity": ${((l.opacity ?? 100) / 100).toFixed(2)}, "scale": ${(l.scale || 1.0).toFixed(2)}}`).join(', ');
                            finishPart += `, "pattern_stack": [${stackPy}]`;
                        }
                    }
                } else {
                    finishPart = `"finish": "${z.finish}"`;
                }
                const customInt = z.customSpec != null ? `, "custom_intensity": {"spec": ${z.customSpec}, "paint": ${z.customPaint}, "bright": ${z.customBright}}` : '';
                return `    {"name": "${z.name.replace(/"/g, '\\"')}", "color": ${colorPy}, ${finishPart}, "intensity": "${z.intensity}"${customInt}, "has_region": ${hasRegion}}`;
            }).join(',\n');

            // SAFETY: Always point PAINT_FILE at the .tga, never a .png/.jpg preview image
            let paintFileSafe = paintFile;
            const previewExts = /\.(png|jpg|jpeg|bmp)$/i;
            if (previewExts.test(paintFileSafe)) {
                const carMatch = paintFileSafe.match(/^(.*[/\\])(car_num_\d+)[\w-]*\.\w+$/i);
                if (carMatch) {
                    paintFileSafe = carMatch[1] + carMatch[2] + '.tga';
                } else {
                    paintFileSafe = paintFileSafe.replace(previewExts, '.tga');
                }
                showToast(`Script targets TGA: ${paintFileSafe.split(/[/\\]/).pop()}`, false);
            }
            const paintFilePy = paintFileSafe.replace(/\\/g, '/');
            const outputDirPy = outputDir.replace(/\\/g, '/');

            // Gather extras for script generation
            const scriptExtras = {};
            const helmetFile = document.getElementById('helmetFile')?.value.trim();
            const suitFile = document.getElementById('suitFile')?.value.trim();
            const wearLevel = parseInt(document.getElementById('wearSlider')?.value || '0', 10);
            const exportZip = document.getElementById('exportZipCheckbox')?.checked || false;
            if (helmetFile) scriptExtras.helmetFile = helmetFile.replace(/\\/g, '/');
            if (suitFile) scriptExtras.suitFile = suitFile.replace(/\\/g, '/');
            if (wearLevel > 0) scriptExtras.wearLevel = wearLevel;
            if (exportZip) scriptExtras.exportZip = true;
            const dualSpec = document.getElementById('dualSpecCheckbox')?.checked || false;
            if (dualSpec) {
                scriptExtras.dualSpec = true;
                scriptExtras.nightBoost = parseFloat(document.getElementById('nightBoostSlider')?.value || '0.7');
            }

            const script = generateFullPythonScript(paintFilePy, outputDirPy, iracingId, zonesStr, regionMasks, scriptExtras);

            document.getElementById('scriptOutput').textContent = script;
            document.getElementById('scriptFilename').value = getAutoScriptName();
            openModal();
        }

        function generateFullPythonScript(paintFile, outputDir, iracingId, zonesStr, regionMasks, extras) {
            // Generate a clean build script that imports from shokker_engine_v2.py
            // The engine file contains ALL proven, tested code

            // Build region mask data block if any regions were drawn
            let regionDataBlock = '';
            const maskNames = Object.keys(regionMasks || {});
            if (maskNames.length > 0) {
                regionDataBlock = `
# ==============================================================================
# SPATIAL REGION MASKS (drawn in Paint Booth)
# RLE encoded: [[value, count], ...] - decode with decode_region_mask()
# ==============================================================================
REGION_MASKS = {
`;
                for (const name of maskNames) {
                    const rle = regionMasks[name];
                    // Compact the runs array for readability
                    const runsStr = rle.runs.map(r => `[${r[0]},${r[1]}]`).join(',');
                    regionDataBlock += `    "${name.replace(/"/g, '\\"')}": {"width": ${rle.width}, "height": ${rle.height}, "runs": [${runsStr}]},\n`;
                }
                regionDataBlock += `}

def decode_region_mask(rle_data, target_h, target_w):
    """Decode RLE region mask and resize to target paint dimensions."""
    import numpy as np
    from PIL import Image
    w, h = rle_data["width"], rle_data["height"]
    mask = np.zeros(w * h, dtype=np.uint8)
    pos = 0
    for val, count in rle_data["runs"]:
        mask[pos:pos+count] = val
        pos += count
    mask = mask.reshape((h, w))
    # Resize to match paint resolution if different
    if h != target_h or w != target_w:
        mask_img = Image.fromarray(mask * 255)
        mask_img = mask_img.resize((target_w, target_h), Image.NEAREST)
        mask = (np.array(mask_img) > 127).astype(np.float32)
    else:
        mask = mask.astype(np.float32)
    return mask
`;
            }

            return `"""
SHOKKER PAINT BOOTH - Base + Pattern Compositing Build Script
Generated: ${new Date().toLocaleString()}

HOW TO RUN:
  1. Double-click the .bat file that came with this script
  2. Or run: python "your_script_name.py"
  3. Or paste this into Claude Code and say "run this"

REQUIRES: numpy, Pillow (pip install numpy Pillow)
NOTE: Do NOT add a shebang line - it breaks Windows py.exe launcher
"""
import sys
import os

# Add the ShokkerEngine folder to Python path so we can import the engine
ENGINE_PATHS = [
    os.path.dirname(os.path.abspath(__file__)),
    r"E:/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/ShokkerEngine",
]
for p in ENGINE_PATHS:
    if p not in sys.path:
        sys.path.insert(0, p)

# ==============================================================================
# CONFIG
# ==============================================================================
PAINT_FILE = r"${paintFile}"
OUTPUT_DIR = r"${outputDir}"
IRACING_ID = "${iracingId}"
SEED = 51
${extras?.helmetFile ? `HELMET_PAINT = r"${extras.helmetFile}"` : '# HELMET_PAINT = None  # Set path to helmet paint TGA for matching spec'}
${extras?.suitFile ? `SUIT_PAINT = r"${extras.suitFile}"` : '# SUIT_PAINT = None  # Set path to suit paint TGA for matching spec'}
WEAR_LEVEL = ${extras?.wearLevel || 0}  # 0=factory new, 100=destroyed
EXPORT_ZIP = ${extras?.exportZip ? 'True' : 'False'}
DUAL_SPEC = ${extras?.dualSpec ? 'True' : 'False'}  # Generate day + night spec maps
NIGHT_BOOST = ${extras?.nightBoost || 0.7}  # 0.0-1.0 night enhancement strength

# ==============================================================================
# ZONES - Color-based zone definitions
# First zone = highest priority. Use "remaining" for catch-all.
# Color can be: "blue", "dark", "gold", "red", "white", "remaining", etc.
# Or a dict: {"color_rgb": [R,G,B], "tolerance": 40}
# Or a LIST of dicts for multi-color zones (all get same finish):
#   [{"color_rgb": [255,170,0], "tolerance": 40}, {"color_rgb": [51,102,255], "tolerance": 40}]
# ==============================================================================
ZONES = [
${zonesStr}
]
${regionDataBlock}
# ==============================================================================
# IMPORT ENGINE & RUN
# ==============================================================================
try:
    from shokker_engine_v2 import build_multi_zone, full_render_pipeline
    print("  Engine loaded from shokker_engine_v2.py")
except ImportError:
    print("  ERROR: Could not find shokker_engine_v2.py!")
    print("  Make sure the file is in one of these locations:")
    for p in ENGINE_PATHS:
        print(f"    - {p}")
    print("\\n  You can get it from: E:/Claude Code Assistant/12-iRacing Misc/Shokker iRacing/ShokkerEngine/")
    sys.exit(1)

if __name__ == '__main__':
    try:
        # Inject spatial region masks into zones if any were drawn
        region_masks = globals().get('REGION_MASKS', {})
        if region_masks:
            from PIL import Image
            import numpy as np
            paint_img = Image.open(PAINT_FILE)
            paint_h, paint_w = paint_img.size[1], paint_img.size[0]
            paint_img.close()
            for zone in ZONES:
                name = zone.get("name", "")
                if name in region_masks:
                    mask = decode_region_mask(region_masks[name], paint_h, paint_w)
                    zone["region_mask"] = mask
                    print(f"  Loaded spatial mask for: {name} ({int(mask.sum())} pixels)")

        # Resolve optional helmet/suit paths
        helmet_file = globals().get('HELMET_PAINT', None)
        if isinstance(helmet_file, str) and helmet_file.startswith('#'):
            helmet_file = None
        suit_file = globals().get('SUIT_PAINT', None)
        if isinstance(suit_file, str) and suit_file.startswith('#'):
            suit_file = None

        # Use full pipeline if extras are configured, otherwise basic build
        if helmet_file or suit_file or WEAR_LEVEL > 0 or EXPORT_ZIP or DUAL_SPEC:
            results = full_render_pipeline(
                car_paint_file=PAINT_FILE,
                output_dir=OUTPUT_DIR,
                zones=ZONES,
                iracing_id=IRACING_ID,
                seed=SEED,
                helmet_paint_file=helmet_file,
                suit_paint_file=suit_file,
                wear_level=WEAR_LEVEL,
                export_zip=EXPORT_ZIP,
                dual_spec=DUAL_SPEC,
                night_boost=NIGHT_BOOST,
            )
            print(f"  Full pipeline complete!")
            if helmet_file:
                print(f"  Helmet spec generated")
            if suit_file:
                print(f"  Suit spec generated")
            if WEAR_LEVEL > 0:
                print(f"  Wear applied: {WEAR_LEVEL}%")
            if EXPORT_ZIP and "export_zip" in results:
                print(f"  ZIP exported: {results['export_zip']}")
        else:
            build_multi_zone(PAINT_FILE, OUTPUT_DIR, ZONES, IRACING_ID, SEED)
    except Exception as e:
        print(f"\\n  ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    input("  Press Enter to close this window...")
`;
        }

        // ===== SOURCE PAINT FILE BROWSER =====
        // ===== PAINT PATH VALIDATION =====
        let _validateTimer = null;
        function debouncedValidatePaintPath() {
            clearTimeout(_validateTimer);
            _validateTimer = setTimeout(validatePaintPath, 600);
        }

        async function validatePaintPath() {
            const input = document.getElementById('paintFile');
            const status = document.getElementById('paintPathStatus');
            const hint = document.getElementById('paintPathHint'); // may not exist in compact header layout
            const path = input.value.trim();

            if (!path) {
                input.classList.remove('path-valid', 'path-invalid');
                status.textContent = '';
                status.className = 'header-path-status';
                if (hint) hint.textContent = 'Paste the FULL Windows path to the paint TGA the engine should read';
                return;
            }

            if (!ShokkerAPI.online) {
                status.textContent = '(server offline)';
                status.className = 'path-status checking';
                return;
            }

            status.textContent = 'checking...';
            status.className = 'path-status checking';

            try {
                const res = await fetch(ShokkerAPI.baseUrl + '/check-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: path }),
                });
                const data = await res.json();

                if (data.is_file) {
                    input.classList.add('path-valid');
                    input.classList.remove('path-invalid');
                    status.textContent = `\u2713 ${data.size_human}`;
                    status.className = 'header-path-status valid';
                    if (hint) { hint.textContent = `File found! (${data.size_human})`; hint.style.color = 'var(--accent-green)'; }
                    addRecentPath(path);
                } else if (data.exists) {
                    input.classList.remove('path-valid');
                    input.classList.add('path-invalid');
                    status.textContent = '\u2717 directory';
                    status.className = 'header-path-status invalid';
                    if (hint) { hint.textContent = 'That path is a directory, not a file.'; hint.style.color = '#ff4444'; }
                } else {
                    input.classList.remove('path-valid');
                    input.classList.add('path-invalid');
                    status.textContent = '\u2717 not found';
                    status.className = 'header-path-status invalid';
                    if (hint) { hint.textContent = 'File not found!'; hint.style.color = '#ff4444'; }
                }
            } catch (e) {
                status.textContent = '(error)';
                status.className = 'header-path-status';
            }
        }

        function browsePaintFile(input) {
            const file = input.files[0];
            if (!file) return;

            // For browser security, we can't get the real path, but we CAN show the filename
            // and auto-load it as the paint preview too
            let fileName = file.name;

            // AUTO-FIX: If user uploaded a PNG/JPG (because browser can't display TGA),
            // convert the path to point to the actual .tga file for the engine.
            // The preview image can still be PNG - only the PAINT_FILE path matters.
            const iracingId = document.getElementById('iracingId').value.trim();
            let tgaFileName = fileName;
            const imgExts = /\.(png|jpg|jpeg|bmp)$/i;
            if (imgExts.test(fileName)) {
                // Check if this looks like a car_num file (with any suffix before extension)
                const carNumMatch = fileName.match(/^(car_num_\d+)[\w-]*\.\w+$/i);
                if (carNumMatch) {
                    // Point to the actual TGA: car_num_XXXXX.tga
                    tgaFileName = carNumMatch[1] + '.tga';
                    showToast(`Preview: ${fileName} | Script will use: ${tgaFileName}`, false);
                } else {
                    // Generic image file - try swapping extension to .tga
                    tgaFileName = fileName.replace(imgExts, '.tga');
                    showToast(`Note: Script will target ${tgaFileName} (TGA). Preview uses ${fileName}`, false);
                }
            }

            // Build a likely path based on driver name - BUT only if paintFile is empty
            // If user already has a path set, don't overwrite it - just update the filename part
            const currentPath = document.getElementById('paintFile').value.trim();
            const driverName = (document.getElementById('driverName')?.value || '').trim();

            if (currentPath) {
                // User already has a path - replace just the filename, keep the directory
                const dir = currentPath.replace(/[/\\][^/\\]+$/, '');
                const newPath = dir + '/' + tgaFileName;
                document.getElementById('paintFile').value = newPath;
                showToast(`Updated filename in existing path: ${tgaFileName}`, false);
            } else if (driverName) {
                const guessedPath = BASE_DRIVER_PATH + "/" + driverName + "/" + tgaFileName;
                document.getElementById('paintFile').value = guessedPath;
            } else {
                // Just show the filename - user can adjust the full path
                document.getElementById('paintFile').value = tgaFileName;
                showToast('Paste the FULL path to the paint TGA - browser can\'t detect it automatically', true);
            }

            // Validate the path against the server
            validatePaintPath();

            // Load the file as paint preview
            if (fileName.toLowerCase().endsWith('.tga')) {
                // TGA: decode with our custom decoder
                const reader = new FileReader();
                reader.onload = function (e) {
                    try {
                        const tga = decodeTGA(e.target.result);
                        loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);
                    } catch (err) {
                        showToast(`TGA decode error: ${err.message}`, true);
                    }
                };
                reader.readAsArrayBuffer(file);
            } else {
                // PNG/JPG/BMP: browser-native decode
                const reader = new FileReader();
                reader.onload = function (e) {
                    const img = new Image();
                    img.onload = function () {
                        const canvas = document.getElementById('paintCanvas');
                        const ctx = canvas.getContext('2d');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        ctx.drawImage(img, 0, 0);
                        paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                        // Also size region canvas
                        const regionCanvas = document.getElementById('regionCanvas');
                        regionCanvas.width = img.width;
                        regionCanvas.height = img.height;

                        // Show/hide elements for 3-column layout
                        const emptyBig = document.getElementById('paintPreviewEmptyBig');
                        if (emptyBig) emptyBig.style.display = 'none';
                        const empty2 = document.getElementById('paintPreviewEmpty2');
                        if (empty2) empty2.style.display = 'none';
                        document.getElementById('paintPreviewLoaded').style.display = 'flex';
                        /* advancedToolbar moved to vertical toolbar */
                        const edInfo2 = document.getElementById('eyedropperInfo'); if (edInfo2) edInfo2.style.display = 'block';
                        document.getElementById('paintDimensions').textContent = `${img.width}x${img.height}`;
                        document.getElementById('paintPreviewStatus').textContent = `(${img.width}x${img.height})`;
                        const canvasInner = document.getElementById('canvasInner');
                        if (canvasInner) canvasInner.style.display = 'block';
                        const zoomCtrl = document.getElementById('zoomControls');
                        if (zoomCtrl) zoomCtrl.style.display = 'flex';

                        setupCanvasHandlers(canvas);
                        canvasZoom('fit');
                        // Auto-enable split view when paint is loaded
                        if (!splitViewActive) {
                            setTimeout(() => toggleSplitView(), 200);
                        }
                        showToast(`Loaded ${fileName} as source paint + preview!`);
                    };
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        }

        function browseOutputFolder(input) {
            // Browser folder picker - extract the folder path from the first file
            const files = input.files;
            if (!files || files.length === 0) return;
            // webkitRelativePath gives us "folderName/filename" - we just need the folder
            const relPath = files[0].webkitRelativePath || '';
            const folderName = relPath.split('/')[0] || '';
            if (folderName) {
                // We can't get the real absolute path from a browser picker, so show a hint
                document.getElementById('outputDir').value = folderName;
                showToast(`Folder selected: "${folderName}" - paste the FULL path (e.g. C:\\Users\\...\\iRacing\\paint\\${folderName})`, true);
            }
        }

        // ===== SERVER-POWERED FILE PICKER =====
        let _filePickerCallback = null;
        let _filePickerFilter = '';
        let _filePickerMode = 'file'; // 'file' or 'folder'
        let _filePickerSelectedPath = '';

        function openFilePicker(options) {
            // options: { title, filter, mode, startPath, onSelect }
            const overlay = document.getElementById('filePickerOverlay');
            document.getElementById('filePickerTitle').textContent = options.title || 'Select File';
            _filePickerCallback = options.onSelect || null;
            _filePickerFilter = options.filter || '';
            _filePickerMode = options.mode || 'file';
            _filePickerSelectedPath = '';
            document.getElementById('filePickerPath').value = '';
            document.getElementById('filePickerSelectBtn').disabled = true;
            overlay.classList.add('active');

            // Set up event delegation for file list clicks (avoids inline onclick escaping issues)
            const _fpList = document.getElementById('filePickerList');
            if (!_fpList._delegated) {
                _fpList._delegated = true;
                _fpList.addEventListener('click', function (e) {
                    const item = e.target.closest('[data-fp-action]');
                    if (!item) return;
                    e.stopPropagation();
                    const action = item.dataset.fpAction;
                    const fpPath = item.dataset.fpPath || '';
                    if (action === 'navigate') filePickerNavigate(fpPath);
                    else if (action === 'select') filePickerSelectItem(item, fpPath);
                });
                _fpList.addEventListener('dblclick', function (e) {
                    const item = e.target.closest('[data-fp-action="select"]');
                    if (!item) return;
                    filePickerDblSelect(item.dataset.fpPath || '');
                });
            }

            // If we have a start path, navigate there; otherwise show root
            const startPath = options.startPath || '';
            filePickerNavigate(startPath);
        }

        function closeFilePicker() {
            document.getElementById('filePickerOverlay').classList.remove('active');
            _filePickerCallback = null;
        }

        function filePickerSelect() {
            const path = _filePickerSelectedPath || document.getElementById('filePickerPath').value;
            if (path && _filePickerCallback) {
                _filePickerCallback(path);
            }
            closeFilePicker();
        }

        async function filePickerNavigate(dirPath) {
            const listEl = document.getElementById('filePickerList');
            const breadcrumbEl = document.getElementById('filePickerBreadcrumb');
            const quickNavEl = document.getElementById('filePickerQuickNav');

            listEl.innerHTML = '<div class="file-picker-loading with-spinner">Scanning folder...</div>';
            _filePickerSelectedPath = '';
            document.getElementById('filePickerPath').value = '';
            document.getElementById('filePickerSelectBtn').disabled = (_filePickerMode === 'file');

            // If mode=folder and we have a dirPath, allow selecting the current folder
            if (_filePickerMode === 'folder' && dirPath) {
                _filePickerSelectedPath = dirPath;
                document.getElementById('filePickerPath').value = dirPath;
                document.getElementById('filePickerSelectBtn').disabled = false;
            }

            try {
                console.log('[FilePicker] navigating to:', dirPath);
                document.title = 'ShokkerPaintBooth - Loading...';
                // Yield to UI thread so spinner paints before we do anything else
                await new Promise(r => setTimeout(r, 0));
                const _t0 = performance.now();
                let data;

                // --- PRIMARY: Electron IPC (direct Node.js fs, no server, no HTTP) ---
                if (window.electronAPI) {
                    console.log('[FilePicker] Using Electron IPC for directory listing');
                    if (!dirPath) {
                        // Root view: get drives + quick navs
                        const navs = await window.electronAPI.getQuickNavs();
                        data = { path: '', drives: navs.drives, quick_navs: navs.quick_navs, items: [] };
                    } else {
                        data = await window.electronAPI.listDir(dirPath, _filePickerFilter);
                    }
                } else {
                    // --- FALLBACK: server fetch (for dev mode without Electron) ---
                    console.log('[FilePicker] Using server fetch (no electronAPI)');
                    const controller = new AbortController();
                    const timeout = setTimeout(() => controller.abort(), 15000);
                    const res = await fetch(ShokkerAPI.baseUrl + '/browse-files', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: dirPath, filter: _filePickerFilter }),
                        signal: controller.signal,
                    });
                    clearTimeout(timeout);
                    data = await res.json();
                }
                console.log('[FilePicker] data ready in', (performance.now() - _t0).toFixed(0), 'ms, items:', data?.items?.length);

                if (data.error) {
                    listEl.innerHTML = `<div class="file-picker-loading" style="color:#ff4444;">${data.error}</div>`;
                    return;
                }

                // Build breadcrumb
                if (data.path) {
                    const parts = data.path.split('/').filter(Boolean);
                    let crumbs = '<span onclick="filePickerNavigate(\'\')" title="Root / Drives">&#128187;</span>';
                    let accumulated = '';
                    for (let i = 0; i < parts.length; i++) {
                        accumulated += parts[i] + '/';
                        const escapedPath = accumulated.replace(/'/g, "\\'");
                        crumbs += `<span class="sep">/</span><span onclick="filePickerNavigate('${escapedPath}')">${parts[i]}</span>`;
                    }
                    breadcrumbEl.innerHTML = crumbs;
                    breadcrumbEl.style.display = 'flex';
                } else {
                    breadcrumbEl.innerHTML = '<span style="color:var(--text-dim);">Select a drive or shortcut to start</span>';
                    breadcrumbEl.style.display = 'flex';
                }

                // Build quick nav buttons (only shown at root)
                if (data.drives || data.quick_navs) {
                    let qhtml = '';
                    if (data.quick_navs) {
                        data.quick_navs.forEach(q => {
                            const ep = q.path.replace(/'/g, "\\'");
                            qhtml += `<button onclick="filePickerNavigate('${ep}')" title="${q.path}">&#9889; ${q.name}</button>`;
                        });
                    }
                    if (data.drives) {
                        data.drives.forEach(d => {
                            const ep = d.path.replace(/'/g, "\\'");
                            qhtml += `<button onclick="filePickerNavigate('${ep}')" title="${d.path}">&#128190; ${d.name}</button>`;
                        });
                    }
                    quickNavEl.innerHTML = qhtml;
                    quickNavEl.style.display = 'flex';
                } else {
                    quickNavEl.style.display = 'none';
                }

                // Build file list
                let html = '';

                // Parent directory link
                if (data.parent) {
                    html += `<div class="file-picker-item folder" data-fp-action="navigate" data-fp-path="${data.parent.replace(/"/g, '&quot;')}">
                <span class="fp-icon">&#128281;</span>
                <span class="fp-name">..</span>
            </div>`;
                }

                if (data.items && data.items.length > 0) {
                    data.items.forEach(item => {
                        const safeP = item.path.replace(/"/g, '&quot;');
                        if (item.type === 'folder' || item.type === 'drive') {
                            html += `<div class="file-picker-item ${item.type}" data-fp-action="navigate" data-fp-path="${safeP}">
                        <span class="fp-icon">${item.type === 'drive' ? '&#128190;' : '&#128193;'}</span>
                        <span class="fp-name">${item.name}</span>
                    </div>`;
                        } else {
                            html += `<div class="file-picker-item file" data-fp-action="select" data-fp-path="${safeP}">
                        <span class="fp-icon">${item.name.toLowerCase().endsWith('.tga') ? '&#127912;' : '&#128196;'}</span>
                        <span class="fp-name">${item.name}</span>
                        <span class="fp-size">${item.size_human || ''}</span>
                    </div>`;
                        }
                    });
                } else if (!data.drives) {
                    html += '<div class="file-picker-loading" style="color:var(--text-dim);">No matching files in this folder</div>';
                }

                // Show overflow warning if server truncated or skipped files
                if (data.large_dir) {
                    html += `<div style="padding:8px 12px;color:#ffaa00;font-size:12px;border-top:1px solid #333;margin-top:4px;">&#128193; Large folder (${data.entry_count?.toLocaleString() || 'many'} entries) - showing folders only. Click a car folder to see paint files.</div>`;
                } else if (data.hidden_files && data.hidden_files > 0) {
                    html += `<div style="padding:8px 12px;color:#ffaa00;font-size:12px;border-top:1px solid #333;margin-top:4px;">&#9888; ${data.hidden_files.toLocaleString()} files not shown (${data.total_files.toLocaleString()} total). Navigate into a car folder to find your paint file.</div>`;
                }

                // Use rAF to render so the browser can paint between fetch and DOM update
                requestAnimationFrame(() => {
                    listEl.innerHTML = html;
                    document.title = 'Shokker Paint Booth';
                });

            } catch (e) {
                console.error('[FilePicker] ERROR:', e.name, e.message);
                document.title = 'Shokker Paint Booth';
                const msg = e.name === 'AbortError'
                    ? 'This folder took too long to load. Try using the Go button to paste a path directly.'
                    : `Server error: ${e.message}`;
                listEl.innerHTML = `<div class="file-picker-loading" style="color:#ff4444;">${msg}</div>`;
            }
        }

        function filePickerSelectItem(el, path) {
            // Deselect previous
            document.querySelectorAll('.file-picker-item.selected').forEach(e => e.classList.remove('selected'));
            el.classList.add('selected');
            _filePickerSelectedPath = path;
            document.getElementById('filePickerPath').value = path;
            document.getElementById('filePickerSelectBtn').disabled = false;
        }

        function filePickerDblSelect(path) {
            _filePickerSelectedPath = path;
            document.getElementById('filePickerPath').value = path;
            filePickerSelect();
        }

        // Convenience wrappers for the Browse buttons
        async function resetSourceBackup() {
            const paintFile = document.getElementById('paintFile').value.trim();
            const iracingId = document.getElementById('iracingId').value.trim();
            if (!paintFile) { showToast('Set the Source Paint path first', true); return; }
            if (!confirm('Reset source backup? This forces the next render to re-read the current source file as the clean original. Use this if renders seem stuck or unchanged.')) return;
            try {
                const result = await ShokkerAPI.resetBackup(paintFile, iracingId);
                if (result.success) {
                    showToast(result.message);
                } else {
                    showToast('Reset failed: ' + (result.error || 'unknown'), true);
                }
            } catch (e) {
                showToast('Reset error: ' + e.message, true);
            }
        }

        function openPaintFilePicker() {
            // Try to start from the current path's directory
            let startPath = '';
            const currentPath = document.getElementById('paintFile').value.trim();
            if (currentPath) {
                const dir = currentPath.replace(/[/\\][^/\\]+$/, '');
                startPath = dir;
            }
            openFilePicker({
                title: 'Select Source Paint TGA',
                filter: '.tga',
                mode: 'file',
                startPath: startPath,
                onSelect: function (path) {
                    document.getElementById('paintFile').value = path;
                    validatePaintPath();
                    // Auto-load the TGA as preview via server conversion
                    loadPaintPreviewFromServer(path);
                    showToast('Source Paint set + loading preview...');
                }
            });
        }

        async function loadPaintPreviewFromServer(tgaPath) {
            /**Load a TGA file from the server as a PNG preview into the canvas.
             * This also sets the preview so the user can eyedrop colors from it.
             */
            try {
                const res = await fetch(ShokkerAPI.baseUrl + '/preview-tga', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: tgaPath }),
                });
                if (!res.ok) {
                    showToast('Could not load preview: ' + res.statusText, true);
                    return;
                }
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const img = new Image();
                img.onload = function () {
                    const canvas = document.getElementById('paintCanvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                    paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                    // Also size region canvas
                    const regionCanvas = document.getElementById('regionCanvas');
                    regionCanvas.width = img.width;
                    regionCanvas.height = img.height;

                    // Show/hide elements
                    const emptyBig = document.getElementById('paintPreviewEmptyBig');
                    if (emptyBig) emptyBig.style.display = 'none';
                    const empty2 = document.getElementById('paintPreviewEmpty2');
                    if (empty2) empty2.style.display = 'none';
                    document.getElementById('paintPreviewLoaded').style.display = 'flex';
                    /* advancedToolbar moved to vertical toolbar */
                    const edInfo3 = document.getElementById('eyedropperInfo'); if (edInfo3) edInfo3.style.display = 'block';
                    document.getElementById('paintDimensions').textContent = `${img.width}x${img.height}`;
                    document.getElementById('paintPreviewStatus').textContent = `(${img.width}x${img.height})`;
                    const canvasInner = document.getElementById('canvasInner');
                    if (canvasInner) canvasInner.style.display = 'block';
                    const zoomCtrl = document.getElementById('zoomControls');
                    if (zoomCtrl) zoomCtrl.style.display = 'flex';

                    setupCanvasHandlers(canvas);
                    canvasZoom('fit');
                    // Auto-enable split view when paint is loaded
                    if (!splitViewActive) {
                        setTimeout(() => toggleSplitView(), 200);
                    }
                    showToast(`Preview loaded: ${img.width}x${img.height}`);
                    URL.revokeObjectURL(url);
                };
                img.onerror = function () {
                    showToast('Failed to decode preview image', true);
                    URL.revokeObjectURL(url);
                };
                img.src = url;
            } catch (e) {
                showToast('Preview load error: ' + e.message, true);
            }
        }

        function openOutputFolderPicker() {
            let startPath = '';
            const currentPath = document.getElementById('outputDir').value.trim();
            if (currentPath) startPath = currentPath;
            openFilePicker({
                title: 'Select iRacing Paint Folder',
                filter: '',
                mode: 'folder',
                startPath: startPath,
                onSelect: function (path) {
                    document.getElementById('outputDir').value = path;
                    updateOutputPath();
                    showToast('iRacing folder set!');
                }
            });
        }

        function openHelmetFilePicker() {
            openFilePicker({
                title: 'Select Helmet Paint TGA',
                filter: '.tga',
                mode: 'file',
                startPath: '',
                onSelect: function (path) {
                    document.getElementById('helmetFile').value = path;
                    showToast('Helmet paint path set!');
                }
            });
        }

        function openSuitFilePicker() {
            openFilePicker({
                title: 'Select Suit Paint TGA',
                filter: '.tga',
                mode: 'file',
                startPath: '',
                onSelect: function (path) {
                    document.getElementById('suitFile').value = path;
                    showToast('Suit paint path set!');
                }
            });
        }

        // ===== PAINT PREVIEW & EYEDROPPER =====

        // Activate Manual Placement mode for a zone — enables drag-to-position on the preview canvas
        function activateManualPlacement(zoneIndex) {
            // Select the zone so placement drag targets it
            if (typeof selectZone === 'function') selectZone(zoneIndex);

            // Set placementLayer so canvas drag handlers know to reposition the pattern
            // Only default to 'pattern' if no explicit layer was set before calling
            if (typeof placementLayer === 'undefined' || placementLayer === 'none') {
                placementLayer = 'pattern';
            }

            // Show visual feedback
            if (typeof showToast === 'function') showToast('Manual Placement active — drag on the preview to position. Scroll to resize. Shift+drag to rotate.');

            // Update canvas cursor
            const canvas = document.getElementById('paintCanvas');
            if (canvas) canvas.style.cursor = 'move';

            // Show the floating tools bar
            const toolsBar = document.getElementById('placement-tools-bar');
            if (toolsBar) toolsBar.style.display = 'flex';

            // Update placement banner if it exists
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();
        }

        // Deactivate Manual Placement mode — hides tools bar and resets cursor
        function deactivateManualPlacement() {
            placementLayer = 'none';
            const toolsBar = document.getElementById('placement-tools-bar');
            if (toolsBar) toolsBar.style.display = 'none';
            const paintCanvas = document.getElementById('paintCanvas');
            if (paintCanvas) paintCanvas.style.cursor = '';
            if (typeof updatePlacementBanner === 'function') updatePlacementBanner();
        }
        window.deactivateManualPlacement = deactivateManualPlacement;

        // ===== FLOATING TOOLS BAR HANDLERS =====
        window.manualPlacementFlipH = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (placementLayer === 'pattern') z.patternFlipH = !z.patternFlipH;
            else if (placementLayer === 'base') z.baseFlipH = !z.baseFlipH;
            else if (placementLayer === 'second_base') z.secondBasePatternFlipH = !z.secondBasePatternFlipH;
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementFlipV = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (placementLayer === 'pattern') z.patternFlipV = !z.patternFlipV;
            else if (placementLayer === 'base') z.baseFlipV = !z.baseFlipV;
            else if (placementLayer === 'second_base') z.secondBasePatternFlipV = !z.secondBasePatternFlipV;
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementRotateCW = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (placementLayer === 'pattern') z.rotation = ((z.rotation || 0) + 90) % 360;
            else if (placementLayer === 'base') z.baseRotation = ((z.baseRotation || 0) + 90) % 360;
            else if (placementLayer === 'second_base') z.secondBasePatternRotation = (((z.secondBasePatternRotation || 0) + 90) % 360);
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementRotateCCW = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (placementLayer === 'pattern') z.rotation = (((z.rotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'base') z.baseRotation = (((z.baseRotation || 0) - 90) + 360) % 360;
            else if (placementLayer === 'second_base') z.secondBasePatternRotation = (((z.secondBasePatternRotation || 0) - 90) + 360) % 360;
            triggerPreviewRender();
            renderZones();
        };

        window.manualPlacementReset = function() {
            const z = zones[selectedZoneIndex];
            if (!z) return;
            if (placementLayer === 'pattern') {
                z.patternOffsetX = 0.5; z.patternOffsetY = 0.5; z.scale = 1.0; z.rotation = 0; z.patternFlipH = false; z.patternFlipV = false;
            } else if (placementLayer === 'base') {
                z.baseOffsetX = 0.5; z.baseOffsetY = 0.5; z.baseScale = 1.0; z.baseRotation = 0; z.baseFlipH = false; z.baseFlipV = false;
            } else if (placementLayer === 'second_base') {
                z.secondBasePatternOffsetX = 0.5; z.secondBasePatternOffsetY = 0.5; z.secondBasePatternScale = 1.0; z.secondBasePatternRotation = 0;
            }
            triggerPreviewRender();
            renderZones();
        };

        // Shared: set up hover + click + draw handlers on the canvas
        function setupCanvasHandlers(canvas) {
            // Placement drag (GIMP/PS-style: drag on map to position pattern/base overlay)
            let placementDragging = false;
            let placementDragStart = null;
            let placementPreviewTimer = null;

            function applyPlacementOffset(i, layer, offsetX, offsetY) {
                const z = zones[i];
                if (!z) return;
                const ox = Math.max(0, Math.min(1, offsetX));
                const oy = Math.max(0, Math.min(1, offsetY));
                const pctX = Math.round(ox * 100) + '%';
                const pctY = Math.round(oy * 100) + '%';
                const vx = Math.round(ox * 100), vy = Math.round(oy * 100);
                if (layer === 'pattern') {
                    z.patternOffsetX = ox; z.patternOffsetY = oy;
                    const xIds = ['patPosXVal', 'detPatPosXVal'], yIds = ['patPosYVal', 'detPatPosYVal'];
                    xIds.forEach(id => { const el = document.getElementById(id + i); if (el) { el.textContent = pctX; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; } });
                    yIds.forEach(id => { const el = document.getElementById(id + i); if (el) { el.textContent = pctY; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; } });
                } else if (layer === 'second_base') {
                    z.secondBasePatternOffsetX = ox; z.secondBasePatternOffsetY = oy;
                    ['detSBPatPosXVal', 'detSBPatPosYVal'].forEach((prefix, idx) => {
                        const el = document.getElementById(prefix + i); if (el) { el.textContent = idx ? pctY : pctX; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? vy : vx; }
                    });
                    const panel = document.getElementById('zoneEditorFloat'); if (panel) {
                        const sx = panel.querySelector('#detSBPatPosXVal' + i); if (sx) { sx.textContent = pctX; const inp = sx.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; }
                        const sy = panel.querySelector('#detSBPatPosYVal' + i); if (sy) { sy.textContent = pctY; const inp = sy.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; }
                    }
                } else if (layer === 'third_base') {
                    z.thirdBasePatternOffsetX = ox; z.thirdBasePatternOffsetY = oy;
                    ['detTBPatPosXVal', 'detTBPatPosYVal'].forEach((prefix, idx) => {
                        const el = document.getElementById(prefix + i); if (el) { el.textContent = idx ? pctY : pctX; const inp = el.previousElementSibling; if (inp && inp.type === 'range') inp.value = idx ? vy : vx; }
                    });
                    const panel = document.getElementById('zoneEditorFloat'); if (panel) {
                        const sx = panel.querySelector('#detTBPatPosXVal' + i); if (sx) { sx.textContent = pctX; const inp = sx.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; }
                        const sy = panel.querySelector('#detTBPatPosYVal' + i); if (sy) { sy.textContent = pctY; const inp = sy.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; }
                    }
                } else if (layer === 'base') {
                    z.baseOffsetX = ox; z.baseOffsetY = oy;
                    const xEl = document.getElementById('detBasePosXVal' + i); if (xEl) { xEl.textContent = pctX; const inp = xEl.previousElementSibling; if (inp && inp.type === 'range') inp.value = vx; }
                    const yEl = document.getElementById('detBasePosYVal' + i); if (yEl) { yEl.textContent = pctY; const inp = yEl.previousElementSibling; if (inp && inp.type === 'range') inp.value = vy; }
                }
                if (typeof triggerPreviewRender === 'function') {
                    clearTimeout(placementPreviewTimer);
                    placementPreviewTimer = setTimeout(triggerPreviewRender, 150);
                }
            }

            function getPixelAt(e) {
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                const x = Math.floor((e.clientX - rect.left) * scaleX);
                const y = Math.floor((e.clientY - rect.top) * scaleY);
                if (x < 0 || x >= canvas.width || y < 0 || y >= canvas.height) return null;
                return { x, y };
            }

            // Like getPixelAt but clamps to canvas edges instead of returning null.
            // Used by rect/gradient drag so the preview stays active when the mouse
            // leaves the canvas - the selection just pins to the nearest edge.
            function getPixelAtClamped(e) {
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                const x = Math.max(0, Math.min(canvas.width - 1, Math.floor((e.clientX - rect.left) * scaleX)));
                const y = Math.max(0, Math.min(canvas.height - 1, Math.floor((e.clientY - rect.top) * scaleY)));
                return { x, y };
            }

            function getColorAt(x, y) {
                const idx = (y * canvas.width + x) * 4;
                return {
                    r: paintImageData.data[idx],
                    g: paintImageData.data[idx + 1],
                    b: paintImageData.data[idx + 2]
                };
            }

            function toHex(r, g, b) {
                return '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
            }


            function getBrushSize() {
                return parseInt(document.getElementById('brushSize')?.value || 20);
            }

            // ── FAST OVERLAY ARC ──────────────────────────────────────────────────────
            // During active brush/erase strokes, drawing a full 2048×2048 ImageData on
            // every mousemove is catastrophically slow (~16 MB alloc + 2 full-canvas
            // scans per frame).  Instead, we paint directly onto regionCanvas with a
            // GPU-accelerated arc() call - O(1) vs O(W×H).  A full renderRegionOverlay()
            // syncs everything correctly once at stroke-start (mousedown) and stroke-end
            // (mouseup), so edges and multi-zone overlaps are always accurate at rest.
            // _rectZoneCache declared at outer scope (before drawRectPreview) so both
            // setupCanvasHandlers internals and drawRectPreview can access it.

            function _fastOverlayArc(cx, cy, radius, value) {
                const paintCanvas = document.getElementById('paintCanvas');
                const regionCanvas = document.getElementById('regionCanvas');
                if (!regionCanvas || !paintCanvas) return;
                // Sync dims here - RAF-throttled renderRegionOverlay() may not have fired yet
                // on first mousemove after mousedown, leaving regionCanvas at default 300×150
                if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
                    regionCanvas.width = paintCanvas.width;
                    regionCanvas.height = paintCanvas.height;
                    regionCanvas.style.width = paintCanvas.style.width;
                    regionCanvas.style.height = paintCanvas.style.height;
                }
                const ctx = regionCanvas.getContext('2d');
                if (value === 0) {
                    // Erase: punch a hole through the overlay
                    ctx.globalCompositeOperation = 'destination-out';
                    ctx.fillStyle = 'rgba(0,0,0,1)';
                } else {
                    // Paint: draw the zone colour circle
                    ctx.globalCompositeOperation = 'source-over';
                    const color = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
                    ctx.fillStyle = `rgba(${color[0]},${color[1]},${color[2]},${(color[3] / 255).toFixed(3)})`;
                }
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.fill();
                ctx.globalCompositeOperation = 'source-over';
            }

            function paintRegionCircle(x, y, radius, value) {
                // Paint into the current zone's regionMask
                const zone = zones[selectedZoneIndex];
                if (!zone) return;
                if (!zone.regionMask) {
                    zone.regionMask = new Uint8Array(canvas.width * canvas.height);
                }
                const r2 = radius * radius;
                for (let dy = -radius; dy <= radius; dy++) {
                    for (let dx = -radius; dx <= radius; dx++) {
                        if (dx * dx + dy * dy > r2) continue;
                        const px = x + dx, py = y + dy;
                        if (px < 0 || px >= canvas.width || py < 0 || py >= canvas.height) continue;
                        zone.regionMask[py * canvas.width + px] = value;
                    }
                }
            }

            // Constrain rect end point so rect becomes a square (Shift held = PS behavior)
            function constrainRectToSquare(start, end) {
                const dx = end.x - start.x;
                const dy = end.y - start.y;
                const size = Math.max(Math.abs(dx), Math.abs(dy));
                return { x: start.x + size * Math.sign(dx || 1), y: start.y + size * Math.sign(dy || 1) };
            }

            function paintRegionRect(x1, y1, x2, y2, value) {
                const zone = zones[selectedZoneIndex];
                if (!zone) return;
                if (!zone.regionMask) {
                    zone.regionMask = new Uint8Array(canvas.width * canvas.height);
                }
                const w = canvas.width;
                const minX = Math.max(0, Math.min(x1, x2));
                const maxX = Math.min(w - 1, Math.max(x1, x2));
                const minY = Math.max(0, Math.min(y1, y2));
                const maxY = Math.min(canvas.height - 1, Math.max(y1, y2));

                // Color-aware rectangle: if eyedropper color is set and paint image is loaded,
                // only fill pixels within the rect that match the eyedropper color (within tolerance).
                // This lets you: eyedrop blue → draw rect → only the blue pixels inside the rect get masked.
                const useColorFilter = (value === 1) && lastEyedropperColor && paintImageData;

                if (useColorFilter) {
                    const data = paintImageData.data;
                    const seedR = lastEyedropperColor.r;
                    const seedG = lastEyedropperColor.g;
                    const seedB = lastEyedropperColor.b;
                    const tolerance = parseInt(document.getElementById('wandTolerance')?.value) || 32;
                    const tolSq = tolerance * tolerance * 3; // Euclidean RGB squared (same as wand/selectAll)
                    let filled = 0;

                    for (let y = minY; y <= maxY; y++) {
                        for (let x = minX; x <= maxX; x++) {
                            const pi = (y * w + x) * 4;
                            const dr = data[pi] - seedR;
                            const dg = data[pi + 1] - seedG;
                            const db = data[pi + 2] - seedB;
                            if ((dr * dr + dg * dg + db * db) <= tolSq) {
                                zone.regionMask[y * w + x] = 1;
                                filled++;
                            }
                        }
                    }
                    showToast(`Rect + Color: ${filled.toLocaleString()} matching pixels selected`);
                } else {
                    // No eyedropper color - fill entire rectangle (legacy behavior)
                    for (let y = minY; y <= maxY; y++) {
                        for (let x = minX; x <= maxX; x++) {
                            zone.regionMask[y * w + x] = value;
                        }
                    }
                }
            }

            canvas.onmousemove = function (e) {
                // Pan mode - don't draw while panning
                if (isPanning || spaceHeld) return;

                // Compare mode intercept
                if (compareMode && compareDragging) { onCompareMouseMove(e); return; }

                // Placement drag: update offset from drag delta
                if (placementDragging && placementDragStart) {
                    const pos = getPixelAtClamped(e);
                    const dx = (pos.x - placementDragStart.x) / canvas.width;
                    const dy = (pos.y - placementDragStart.y) / canvas.height;
                    applyPlacementOffset(selectedZoneIndex, placementLayer, placementDragStart.offsetX + dx, placementDragStart.offsetY + dy);
                    return;
                }

                const pos = getPixelAt(e);
                if (!pos) return;

                if (canvasMode === 'eyedropper') {
                    const px = getColorAt(pos.x, pos.y);
                    const hex = toHex(px.r, px.g, px.b);
                    document.getElementById('hoverInfo').style.display = 'block';
                    document.getElementById('hoverSwatch').style.background = hex;
                    document.getElementById('hoverHex').textContent = hex.toUpperCase();
                    document.getElementById('hoverRGB').textContent = `RGB(${px.r}, ${px.g}, ${px.b})`;
                } else if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {
                    const radius = getBrushSize();
                    const val = canvasMode === 'brush' ? 1 : 0;
                    paintRegionCircle(pos.x, pos.y, radius, val);
                    _fastOverlayArc(pos.x, pos.y, radius, val); // fast GPU draw - no full ImageData rebuild
                } else if ((canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude' || canvasMode === 'spatial-erase') && isDrawing) {
                    const val = canvasMode === 'spatial-include' ? 1 : (canvasMode === 'spatial-exclude' ? 2 : 0);
                    paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);
                    renderRegionOverlay();
                } else if (canvasMode === 'lasso' && isDrawing && lassoMouseDownPos) {
                    const dist = Math.sqrt((pos.x - lassoMouseDownPos.x) ** 2 + (pos.y - lassoMouseDownPos.y) ** 2);
                    if (!lassoFreehandDrawing && dist >= 5) {
                        // Start freehand mode: add the initial mousedown point first
                        lassoFreehandDrawing = true;
                        addLassoPoint(lassoMouseDownPos.x, lassoMouseDownPos.y);
                    }
                    if (lassoFreehandDrawing) {
                        const lastPt = lassoPoints[lassoPoints.length - 1];
                        const ptDist = Math.sqrt((pos.x - lastPt.x) ** 2 + (pos.y - lastPt.y) ** 2);
                        if (ptDist >= 5) { // Add point every 5 pixels
                            addLassoPoint(pos.x, pos.y);
                        }
                    }
                } else if (canvasMode === 'rect' && isDrawing && rectStart) {
                    // Use clamped coords so drag pins to canvas edge instead of dying
                    let cpos = getPixelAtClamped(e);
                    if (e.shiftKey) cpos = constrainRectToSquare(rectStart, cpos);
                    drawRectPreview(rectStart, cpos);
                }
            };

            canvas.onmouseleave = function () {
                document.getElementById('hoverInfo').style.display = 'none';
                if (canvasMode !== 'rect') isDrawing = false;
            };

            canvas.onmousedown = function (e) {
                // Pan mode intercept - space+drag, middle-click, right-click, or active pan
                if (spaceHeld || e.button === 1 || e.button === 2 || isPanning) return;

                // Compare mode intercept
                if (compareMode) { onCompareMouseDown(e); return; }

                // Placement drag (GIMP/PS-style): drag on map to position pattern/base overlay
                if (typeof placementLayer !== 'undefined' && placementLayer !== 'none' && e.button === 0) {
                    const pos = getPixelAt(e);
                    if (pos && zones[selectedZoneIndex]) {
                        const z = zones[selectedZoneIndex];
                        let ox = 0.5, oy = 0.5;
                        if (placementLayer === 'pattern') { ox = z.patternOffsetX ?? 0.5; oy = z.patternOffsetY ?? 0.5; }
                        else if (placementLayer === 'second_base') { ox = z.secondBasePatternOffsetX ?? 0.5; oy = z.secondBasePatternOffsetY ?? 0.5; }
                        else if (placementLayer === 'third_base') { ox = z.thirdBasePatternOffsetX ?? 0.5; oy = z.thirdBasePatternOffsetY ?? 0.5; }
                        else if (placementLayer === 'base') { ox = z.baseOffsetX ?? 0.5; oy = z.baseOffsetY ?? 0.5; }
                        placementDragStart = { x: pos.x, y: pos.y, offsetX: ox, offsetY: oy };
                        placementDragging = true;
                        if (typeof pushZoneUndo === 'function') pushZoneUndo('', true);
                        e.preventDefault();
                        canvas.style.cursor = 'grabbing';
                        return;
                    }
                }

                // Decal interaction: select, move, scale, or rotate on the car map
                const posForDecal = getPixelAt(e);
                if (e.button === 0 && posForDecal && typeof checkDecalDrag === 'function') {
                    var decalResult = checkDecalDrag(posForDecal.x, posForDecal.y);
                    if (decalResult === true) {
                        e.preventDefault();
                        var onDecalMove = function (e2) {
                            var c = document.getElementById('paintCanvas');
                            if (!c) return;
                            var rect = c.getBoundingClientRect();
                            var sx = c.width / rect.width, sy = c.height / rect.height;
                            var x = Math.max(0, Math.min(c.width - 1, Math.floor((e2.clientX - rect.left) * sx)));
                            var y = Math.max(0, Math.min(c.height - 1, Math.floor((e2.clientY - rect.top) * sy)));
                            if (typeof updateDecalDrag === 'function') updateDecalDrag(x, y);
                        };
                        var onDecalUp = function () {
                            if (typeof endDecalDrag === 'function') endDecalDrag();
                            document.removeEventListener('mousemove', onDecalMove);
                            document.removeEventListener('mouseup', onDecalUp);
                        };
                        document.addEventListener('mousemove', onDecalMove);
                        document.addEventListener('mouseup', onDecalUp);
                        return;
                    }
                    if (decalResult === 'scale') {
                        e.preventDefault();
                        var onScaleMove = function (e2) {
                            var c = document.getElementById('paintCanvas');
                            if (!c) return;
                            var rect = c.getBoundingClientRect();
                            var sx = c.width / rect.width, sy = c.height / rect.height;
                            var x = Math.floor((e2.clientX - rect.left) * sx);
                            var y = Math.floor((e2.clientY - rect.top) * sy);
                            if (typeof updateDecalScaleFromMouse === 'function') updateDecalScaleFromMouse(x, y);
                        };
                        var onScaleUp = function () {
                            if (typeof endDecalScale === 'function') endDecalScale();
                            document.removeEventListener('mousemove', onScaleMove);
                            document.removeEventListener('mouseup', onScaleUp);
                        };
                        document.addEventListener('mousemove', onScaleMove);
                        document.addEventListener('mouseup', onScaleUp);
                        return;
                    }
                    if (decalResult === 'rotate') {
                        e.preventDefault();
                        var onRotateMove = function (e2) {
                            var c = document.getElementById('paintCanvas');
                            if (!c) return;
                            var rect = c.getBoundingClientRect();
                            var sx = c.width / rect.width, sy = c.height / rect.height;
                            var x = Math.floor((e2.clientX - rect.left) * sx);
                            var y = Math.floor((e2.clientY - rect.top) * sy);
                            if (typeof updateDecalRotateFromMouse === 'function') updateDecalRotateFromMouse(x, y);
                        };
                        var onRotateUp = function () {
                            if (typeof endDecalRotate === 'function') endDecalRotate();
                            document.removeEventListener('mousemove', onRotateMove);
                            document.removeEventListener('mouseup', onRotateUp);
                        };
                        document.addEventListener('mousemove', onRotateMove);
                        document.addEventListener('mouseup', onRotateUp);
                        return;
                    }
                    // decalResult === false means "no decal was hit" — fall through to tool handling
                }

                // Prevent native canvas image drag for draw tools - without this,
                // the browser can start a drag-and-drop operation that steals mousemove events
                if (['brush', 'rect', 'erase', 'spatial-include', 'spatial-exclude', 'lasso'].includes(canvasMode)) {
                    e.preventDefault();
                }

                const pos = getPixelAt(e);
                if (!pos) return;

                if (canvasMode === 'eyedropper') {
                    const px = getColorAt(pos.x, pos.y);
                    lastEyedropperColor = px;
                    const hex = toHex(px.r, px.g, px.b);
                    document.getElementById('eyedropperSwatch').style.background = hex;
                    document.getElementById('eyedropperRGB').textContent = `RGB: (${px.r}, ${px.g}, ${px.b})`;
                    document.getElementById('eyedropperHex').textContent = hex.toUpperCase();
                    document.getElementById('hoverInfo').style.display = 'none';
                    document.getElementById('eyedropperInfo').style.display = 'block';
                    updateEyedropperZoneSelect();
                } else if (canvasMode === 'brush' || canvasMode === 'erase') {
                    pushUndo(selectedZoneIndex); // Save state before stroke begins
                    isDrawing = true;
                    const radius = getBrushSize();
                    paintRegionCircle(pos.x, pos.y, radius, canvasMode === 'brush' ? 1 : 0);
                    // SYNC render - must complete before first mousemove fires _fastOverlayArc()
                    // (RAF-wrapped renderRegionOverlay() is async and may not run in time,
                    //  leaving regionCanvas at default 300×150 → tiny dots bug)
                    _doRenderRegionOverlay();
                } else if (canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude' || canvasMode === 'spatial-erase') {
                    pushSpatialUndo(selectedZoneIndex);
                    isDrawing = true;
                    const val = canvasMode === 'spatial-include' ? 1 : (canvasMode === 'spatial-exclude' ? 2 : 0);
                    paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);
                    _doRenderRegionOverlay();
                } else if (canvasMode === 'lasso') {
                    // Right-click undoes last lasso point
                    if (e.button === 2) { undoLassoPoint(); return; }
                    // Save mousedown position for drag-vs-click detection
                    lassoMouseDownPos = { x: pos.x, y: pos.y };
                    isDrawing = true;
                    // Freehand mode starts on mousemove (see mousemove handler below)
                    // Click behavior (no drag): handled in mouseup when not freehand
                } else if (canvasMode === 'rect') {
                    pushUndo(selectedZoneIndex); // Save state before rect draw
                    isDrawing = true;
                    rectStart = pos;
                    _rectZoneCache = null;
                    // Eagerly build zone overlay cache synchronously so drawRectPreview()
                    // never needs to call the expensive renderRegionOverlayData() during drag
                    _doRenderRegionOverlay();
                    const _rcPre = document.getElementById('regionCanvas');
                    if (_rcPre && _rcPre.width > 0 && _rcPre.height > 0) {
                        _rectZoneCache = _rcPre.getContext('2d').getImageData(0, 0, _rcPre.width, _rcPre.height);
                    }
                } else if (canvasMode === 'wand' || canvasMode === 'selectall') {
                    pushUndo(selectedZoneIndex); // Save state before wand fill
                    const tolerance = parseInt(document.getElementById('wandTolerance').value) || 32;
                    const selMode = document.getElementById('selectionMode')?.value || 'add';
                    let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
                    let subtractMode = selMode === 'subtract' || e.altKey;
                    let addToExisting = (selMode === 'add') || e.shiftKey;
                    if (replaceMode) addToExisting = false;
                    if (subtractMode) addToExisting = false;

                    const contiguous = document.getElementById('wandContiguous')?.checked ?? (canvasMode === 'wand');
                    if (subtractMode) {
                        subtractWandSelection(pos.x, pos.y, tolerance, contiguous);
                    } else if (contiguous) {
                        magicWandFill(pos.x, pos.y, tolerance, addToExisting);
                    } else {
                        selectAllColor(pos.x, pos.y, tolerance, addToExisting);
                    }
                    renderRegionOverlay();
                } else if (canvasMode === 'edge') {
                    pushUndo(selectedZoneIndex);
                    const tolerance = parseInt(document.getElementById('wandTolerance').value) || 32;
                    const selMode = document.getElementById('selectionMode')?.value || 'add';
                    let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
                    let subtractMode = selMode === 'subtract' || e.altKey;
                    let addToExisting = (selMode === 'add') || e.shiftKey;
                    if (replaceMode) addToExisting = false;
                    if (subtractMode) addToExisting = false;

                    edgeDetectFill(pos.x, pos.y, tolerance, addToExisting, subtractMode);
                    renderRegionOverlay();
                }
            };

            canvas.onmouseup = function (e) {
                if (placementDragging) {
                    placementDragging = false;
                    placementDragStart = null;
                    clearTimeout(placementPreviewTimer);
                    placementPreviewTimer = null;
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    canvas.style.cursor = (typeof placementLayer !== 'undefined' && placementLayer !== 'none') ? 'grab' : '';
                    return;
                }
                if (canvasMode === 'rect' && isDrawing && rectStart) {
                    let pos = getPixelAtClamped(e);
                    if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);

                    const selMode = document.getElementById('selectionMode')?.value || 'add';
                    let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
                    let subtractMode = selMode === 'subtract' || e.altKey;

                    if (replaceMode && zones[selectedZoneIndex]) {
                        const zone = zones[selectedZoneIndex];
                        const canvas = document.getElementById('paintCanvas');
                        if (canvas && zone.regionMask) {
                            zone.regionMask = new Uint8Array(canvas.width * canvas.height);
                        }
                    }

                    const fillVal = subtractMode ? 0 : 1;
                    paintRegionRect(rectStart.x, rectStart.y, pos.x, pos.y, fillVal);
                    rectStart = null;
                    _rectZoneCache = null;
                    hideRectPreview();
                    renderRegionOverlay();
                    // Force immediate overlay re-render (bypass RAF throttle)
                    setTimeout(() => { _doRenderRegionOverlay(); }, 30);
                }
                // Brush/erase: full re-render once at stroke end so edges and multi-zone
                // overlaps are drawn correctly (fast arc path skips those)
                if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {
                    renderRegionOverlay();
                }
                if ((canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude') && isDrawing) {
                    _doRenderRegionOverlay();
                }
                if (canvasMode === 'lasso' && isDrawing) {
                    if (lassoFreehandDrawing) {
                        // Freehand drag completed — auto-close if enough points
                        if (lassoPoints.length >= 3) {
                            closeLasso();
                        }
                        lassoFreehandDrawing = false;
                    } else if (lassoMouseDownPos) {
                        // Click (no drag) — use existing click-by-click behavior
                        const pos2 = getPixelAt(e);
                        if (pos2) {
                            addLassoPoint(pos2.x, pos2.y);
                            // Double-click closes the lasso
                            if (e.detail >= 2 && lassoPoints.length >= 3) {
                                closeLasso();
                            }
                        }
                    }
                    lassoMouseDownPos = null;
                }
                isDrawing = false;
            };

            // Remove old onclick (now handled by onmousedown)
            canvas.onclick = null;

            // Block native canvas image drag - browsers treat <canvas> as a draggable image,
            // which steals mousemove events during drag-to-draw operations
            canvas.addEventListener('dragstart', (e) => e.preventDefault());

            // Document-level mousemove for rect/gradient preview during drag.
            // canvas.onmousemove can miss events if the cursor briefly leaves the canvas
            // element during fast drags, or if the browser's hit-testing is off due to
            // CSS transforms (zoom). This listener ensures preview always updates.
            document.addEventListener('mousemove', function _rectGradDocMove(e) {
                if (isPanning || spaceHeld) return;
                if (canvasMode === 'rect' && isDrawing && rectStart) {
                    // Clamped so drag-to-edge pins to canvas boundary instead of stopping
                    let pos = getPixelAtClamped(e);
                    if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);
                    drawRectPreview(rectStart, pos);
                }
            });

            // Document-level mouseup - commits rect or placement drag even when mouse is
            // released outside the canvas (edge drag scenario). Same selection mode logic as canvas mouseup.
            document.addEventListener('mouseup', function _rectDocUp(e) {
                if (placementDragging) {
                    placementDragging = false;
                    placementDragStart = null;
                    clearTimeout(placementPreviewTimer);
                    placementPreviewTimer = null;
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    const cvs = document.getElementById('paintCanvas');
                    if (cvs) cvs.style.cursor = (typeof placementLayer !== 'undefined' && placementLayer !== 'none') ? 'grab' : '';
                    return;
                }
                if (canvasMode === 'rect' && isDrawing && rectStart) {
                    let pos = getPixelAtClamped(e);
                    if (e.shiftKey) pos = constrainRectToSquare(rectStart, pos);

                    const selMode = document.getElementById('selectionMode')?.value || 'add';
                    let replaceMode = selMode === 'replace' && !e.shiftKey && !e.altKey;
                    let subtractMode = selMode === 'subtract' || e.altKey;

                    if (replaceMode && zones[selectedZoneIndex]) {
                        const zone = zones[selectedZoneIndex];
                        const canvas = document.getElementById('paintCanvas');
                        if (canvas && zone.regionMask) {
                            zone.regionMask = new Uint8Array(canvas.width * canvas.height);
                        }
                    }

                    const fillVal = subtractMode ? 0 : 1;
                    paintRegionRect(rectStart.x, rectStart.y, pos.x, pos.y, fillVal);
                    rectStart = null;
                    _rectZoneCache = null;
                    hideRectPreview();
                    renderRegionOverlay();
                    // Force immediate overlay re-render (bypass RAF throttle)
                    setTimeout(() => { _doRenderRegionOverlay(); }, 30);
                    isDrawing = false;
                }
            });
        }

        function setCanvasMode(mode) {
            canvasMode = mode;
            const canvas = document.getElementById('paintCanvas');

            // Update toolbar button active states (horizontal + vertical toolbar)
            document.querySelectorAll('.draw-tool-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.vtool-btn').forEach(btn => btn.classList.remove('active'));
            const btnId = {
                eyedropper: 'modeEyedropper', brush: 'modeBrush', rect: 'modeRect',
                erase: 'modeErase', wand: 'modeWand', selectall: 'modeSelectAll',
                edge: 'modeEdge', 'spatial-include': 'modeSpatialInclude',
                'spatial-exclude': 'modeSpatialExclude', lasso: 'modeLasso'
            }[mode];
            document.getElementById(btnId)?.classList.add('active');
            const vtBtnId = {
                eyedropper: 'vtModeEyedropper', brush: 'vtModeBrush', rect: 'vtModeRect',
                erase: 'vtModeErase', wand: 'vtModeWand', selectall: 'vtModeSelectAll',
                edge: 'vtModeEdge', 'spatial-include': 'vtModeSpatialInclude',
                'spatial-exclude': 'vtModeSpatialExclude', 'spatial-erase': 'vtModeSpatialErase',
                lasso: 'vtModeLasso'
            }[mode];
            document.getElementById(vtBtnId)?.classList.add('active');
            // Reset lasso state when switching away
            if (mode !== 'lasso' && lassoActive) { lassoActive = false; lassoPoints = []; hideLassoPreview(); }

            // Toggle tool-specific controls
            const showBrush = (mode === 'brush' || mode === 'erase');
            const showWand = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect');
            const showSpatial = (mode === 'spatial-include' || mode === 'spatial-exclude' || mode === 'spatial-erase');
            document.getElementById('brushSizeLabel').style.display = showBrush ? '' : 'none';
            document.getElementById('brushSize').style.display = showBrush ? '' : 'none';
            document.getElementById('brushSizeVal').style.display = showBrush ? '' : 'none';
            document.getElementById('wandToleranceLabel').style.display = showWand ? '' : 'none';
            document.getElementById('wandTolerance').style.display = showWand ? '' : 'none';
            document.getElementById('wandTolVal').style.display = showWand ? '' : 'none';
            // Show selection mode for selection tools
            const showSelMode = (mode === 'wand' || mode === 'selectall' || mode === 'edge' || mode === 'rect' || mode === 'lasso');
            const selModeEl = document.getElementById('selectionMode');
            if (selModeEl) selModeEl.style.display = showSelMode ? '' : 'none';
            // Rect tool defaults to additive so multiple rectangles can be drawn
            if (mode === 'rect') {
                const selMode = document.getElementById('selectionMode');
                if (selMode && selMode.value === 'replace') selMode.value = 'add';
            }
            const modifierHint = document.getElementById('selectionModifierHint');
            if (modifierHint) modifierHint.style.display = showSelMode ? '' : 'none';
            // Contiguous checkbox only for wand/selectall, not edge/rect
            const showContiguous = (mode === 'wand' || mode === 'selectall');
            document.getElementById('wandContiguousLabel').style.display = showContiguous ? '' : 'none';
            const wandHint = document.getElementById('wandSubtractHint');
            if (wandHint) wandHint.style.display = 'none';
            // When switching to selectall, uncheck contiguous; when switching to wand, check it
            if (mode === 'selectall') document.getElementById('wandContiguous').checked = false;
            else if (mode === 'wand') document.getElementById('wandContiguous').checked = true;
            document.getElementById('spatialSizeLabel').style.display = showSpatial ? '' : 'none';
            document.getElementById('spatialBrushSize').style.display = showSpatial ? '' : 'none';
            document.getElementById('spatialSizeVal').style.display = showSpatial ? '' : 'none';
            // Show erase buttons contextually
            const spatialEraseBtn = document.getElementById('spatialEraseBtn');
            if (spatialEraseBtn) spatialEraseBtn.style.display = showSpatial ? '' : 'none';
            const drawEraseBtn = document.getElementById('drawEraseBtn');
            if (drawEraseBtn) drawEraseBtn.style.display = (showWand || mode === 'brush' || mode === 'rect' || mode === 'lasso') ? '' : 'none';

            // Edge preview button: only visible in edge mode
            const edgeBtn = document.getElementById('edgePreviewBtn');
            if (edgeBtn) {
                edgeBtn.style.display = (mode === 'edge') ? '' : 'none';
                if (mode !== 'edge') { clearEdgePreviewOverlay(); edgePreviewActive = false; edgeBtn.style.background = ''; }
            }

            // Update cursor
            const viewport = document.getElementById('canvasViewport');
            if (mode === 'eyedropper') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'none';
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (showSpatial || mode === 'spatial-erase') {
                canvas.style.cursor = 'none'; // Hide native cursor, use brush circle
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (showBrush) {
                canvas.style.cursor = 'none'; // Hide native cursor, use brush circle
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            } else if (mode === 'lasso') {
                canvas.style.cursor = 'crosshair';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
                startLasso();
            } else {
                canvas.style.cursor = (mode === 'wand' || mode === 'selectall' || mode === 'edge') ? 'crosshair' : 'cell';
                if (viewport) viewport.style.cursor = '';
                document.getElementById('drawZoneIndicator').style.display = 'flex';
                updateDrawZoneIndicator();
                document.getElementById('regionCanvas').style.pointerEvents = 'none';
            }
            if (typeof placementLayer !== 'undefined' && placementLayer !== 'none') canvas.style.cursor = 'grab';

            // Show/hide brush cursor circle
            updateBrushCursorVisibility();

            // Re-attach canvas handlers whenever tool changes so Wand/Spatial/Brush/etc. always work
            // (handlers can be missing if paint was shown without going through a load path)
            if (canvas && canvas.width && canvas.height && typeof paintImageData !== 'undefined' && paintImageData) {
                setupCanvasHandlers(canvas);
            }
        }

        function updateDrawZoneIndicator() {
            const zoneColor = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
            document.getElementById('drawZoneName').textContent = `Zone ${selectedZoneIndex + 1}: ${zones[selectedZoneIndex]?.name || '?'}`;
            document.getElementById('drawZoneColorDot').style.background = `rgba(${zoneColor[0]},${zoneColor[1]},${zoneColor[2]},0.8)`;

            // Update label and hint based on mode
            const label = document.getElementById('drawZoneLabel');
            const hint = document.getElementById('drawZoneHint');
            if (canvasMode === 'wand') {
                label.textContent = 'Wand select for:';
                hint.textContent = '(click a number/logo/shape - Shift+click to add more areas)';
            } else if (canvasMode === 'erase') {
                label.textContent = 'Erasing from:';
                hint.textContent = '(paint over drawn areas to remove them)';
            } else if (canvasMode === 'spatial-include') {
                label.textContent = '✅ Including for:';
                label.style.color = 'var(--accent-green)';
                hint.textContent = '(paint green areas to KEEP in this zone\'s color match)';
            } else if (canvasMode === 'spatial-exclude') {
                label.textContent = '❌ Excluding from:';
                label.style.color = '#ff4444';
                hint.textContent = '(paint red areas to REMOVE from this zone\'s color match)';
            } else if (canvasMode === 'lasso') {
                label.textContent = '⬡ Lasso for:';
                label.style.color = 'var(--accent-gold)';
                hint.textContent = `(click to place vertices, double-click to fill - ${lassoPoints.length} points)`;
            } else {
                label.textContent = 'Drawing for:';
                label.style.color = '';
                hint.textContent = '(select a different zone on the left to switch)';
            }
        }

        // ===== BRUSH CURSOR CIRCLE - visible radius indicator =====
        function updateBrushCursorVisibility() {
            const circle = document.getElementById('brushCursorCircle');
            if (!circle) return;
            const showCircle = ['brush', 'erase', 'spatial-include', 'spatial-exclude'].includes(canvasMode);
            circle.style.display = showCircle ? 'block' : 'none';
            if (showCircle) {
                // Color the circle based on mode
                if (canvasMode === 'spatial-include') {
                    circle.style.borderColor = 'rgba(0,200,100,0.8)';
                } else if (canvasMode === 'spatial-exclude') {
                    circle.style.borderColor = 'rgba(220,50,50,0.8)';
                } else if (canvasMode === 'erase') {
                    circle.style.borderColor = 'rgba(255,255,255,0.5)';
                } else {
                    circle.style.borderColor = 'rgba(255,255,255,0.7)';
                }
            }
        }

        function updateBrushCursorPosition(e) {
            const circle = document.getElementById('brushCursorCircle');
            if (!circle || circle.style.display === 'none') return;
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;

            // Get the brush radius in canvas pixels
            let radius;
            if (canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude') {
                radius = spatialBrushRadius;
            } else {
                radius = parseInt(document.getElementById('brushSize')?.value || 20);
            }

            // Convert canvas pixels to screen pixels using current zoom
            const rect = canvas.getBoundingClientRect();
            const scaleX = rect.width / canvas.width;
            const screenRadius = radius * scaleX;
            const diameter = screenRadius * 2;

            circle.style.width = diameter + 'px';
            circle.style.height = diameter + 'px';
            circle.style.left = (e.clientX - screenRadius) + 'px';
            circle.style.top = (e.clientY - screenRadius) + 'px';
        }

        // Attach global mousemove for brush cursor tracking
        document.addEventListener('mousemove', function (e) {
            if (['brush', 'erase', 'spatial-include', 'spatial-exclude'].includes(canvasMode)) {
                updateBrushCursorPosition(e);
            }
        });


        // Cached ImageData of zone overlay for rect preview drag (outer scope so both
        // setupCanvasHandlers internals and drawRectPreview can access it)
        let _rectZoneCache = null;

        // Draw rubber-band rectangle during drag.
        // Uses a plain CSS DIV (rectSelectionBox) for the marching-ants border.
        // CSS borders are always in screen pixels - no canvas scaling issues.
        // Zone-colored fill still drawn on regionCanvas.
        function drawRectPreview(start, end) {
            const paintCanvas = document.getElementById("paintCanvas");
            const regionCanvas = document.getElementById("regionCanvas");
            const selBox = document.getElementById("rectSelectionBox");
            if (!paintCanvas || !regionCanvas || !selBox) return;

            // Ensure regionCanvas matches paintCanvas full resolution
            if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
                regionCanvas.width = paintCanvas.width;
                regionCanvas.height = paintCanvas.height;
                regionCanvas.style.width = paintCanvas.style.width;
                regionCanvas.style.height = paintCanvas.style.height;
                _rectZoneCache = null;
            }

            // Restore zone overlay on regionCanvas (cached for perf)
            const rctx = regionCanvas.getContext("2d");
            if (!_rectZoneCache) {
                const tmpC = document.createElement('canvas');
                tmpC.width = paintCanvas.width;
                tmpC.height = paintCanvas.height;
                renderRegionOverlayData(tmpC.getContext('2d'), paintCanvas);
                _rectZoneCache = tmpC.getContext('2d').getImageData(0, 0, paintCanvas.width, paintCanvas.height);
            }
            rctx.clearRect(0, 0, regionCanvas.width, regionCanvas.height);
            rctx.putImageData(_rectZoneCache, 0, 0);

            // Draw zone-colored fill on regionCanvas (large solid area, visible at any zoom)
            const rx = Math.min(start.x, end.x);
            const ry = Math.min(start.y, end.y);
            const rw = Math.abs(end.x - start.x);
            const rh = Math.abs(end.y - start.y);
            const color = ZONE_OVERLAY_COLORS[selectedZoneIndex % ZONE_OVERLAY_COLORS.length];
            rctx.fillStyle = "rgba(" + color[0] + "," + color[1] + "," + color[2] + ",0.5)";
            rctx.fillRect(rx, ry, rw, rh);

            // Position the CSS selection box in screen-pixel coordinates
            const zoom = currentZoom || 1;
            selBox.style.left = Math.round(rx * zoom) + 'px';
            selBox.style.top = Math.round(ry * zoom) + 'px';
            selBox.style.width = Math.max(1, Math.round(rw * zoom)) + 'px';
            selBox.style.height = Math.max(1, Math.round(rh * zoom)) + 'px';
            selBox.style.display = 'block';
        }

        // Hide the rect selection box (call on mouseup / mode change)
        function hideRectPreview() {
            const selBox = document.getElementById("rectSelectionBox");
            if (selBox) selBox.style.display = 'none';
        }

        // Helper: render region mask overlay pixels onto context (selected zone only)
        function renderRegionOverlayData(ctx, paintCanvas) {
            const imgData = ctx.createImageData(paintCanvas.width, paintCanvas.height);
            const data = imgData.data;
            const zi = selectedZoneIndex;
            const zone = zones[zi];
            if (zone && zone.regionMask) {
                const color = ZONE_OVERLAY_COLORS[zi % ZONE_OVERLAY_COLORS.length];
                for (let i = 0; i < zone.regionMask.length; i++) {
                    if (zone.regionMask[i] > 0) {
                        const pi = i * 4;
                        data[pi] = color[0]; data[pi + 1] = color[1];
                        data[pi + 2] = color[2]; data[pi + 3] = color[3];
                    }
                }
            }
            ctx.putImageData(imgData, 0, 0);
        }

        let _overlayRafPending = false;
        function renderRegionOverlay() {
            // RAF-throttle: coalesce multiple sync calls within the same frame into one
            if (_overlayRafPending) return;
            _overlayRafPending = true;
            requestAnimationFrame(() => {
                _overlayRafPending = false;
                _doRenderRegionOverlay();
            });
        }
        function _doRenderRegionOverlay() {
            const paintCanvas = document.getElementById('paintCanvas');
            const regionCanvas = document.getElementById('regionCanvas');
            if (!paintCanvas || !regionCanvas) return;

            // Only reset canvas dimensions when they actually changed.
            // Setting .width/.height clears the bitmap AND triggers a DOM reflow - very expensive.
            if (regionCanvas.width !== paintCanvas.width || regionCanvas.height !== paintCanvas.height) {
                regionCanvas.width = paintCanvas.width;
                regionCanvas.height = paintCanvas.height;
            }
            if (regionCanvas.style.width !== paintCanvas.style.width) {
                regionCanvas.style.width = paintCanvas.style.width;
                regionCanvas.style.height = paintCanvas.style.height;
            }
            const ctx = regionCanvas.getContext('2d');
            ctx.clearRect(0, 0, regionCanvas.width, regionCanvas.height);
            const imgData = ctx.createImageData(paintCanvas.width, paintCanvas.height);
            const data = imgData.data;

            // Draw ONLY the selected zone's region overlay (other zones' overlays are hidden)
            {
                const zi = selectedZoneIndex;
                const zone = zones[zi];
                if (zone && zone.regionMask) {
                    const color = ZONE_OVERLAY_COLORS[zi % ZONE_OVERLAY_COLORS.length];
                    for (let i = 0; i < zone.regionMask.length; i++) {
                        if (zone.regionMask[i] > 0) {
                            const pi = i * 4;
                            data[pi] = color[0];
                            data[pi + 1] = color[1];
                            data[pi + 2] = color[2];
                            data[pi + 3] = Math.min(255, Math.round(color[3] * overlayOpacityMultiplier));
                        }
                    }
                }
            }

            // ---- SPATIAL MASK OVERLAY: green=include, red=exclude (selected zone only) ----
            {
                const zi = selectedZoneIndex;
                const zone = zones[zi];
                if (zone && zone.spatialMask) {
                    const cw = paintCanvas.width, ch = paintCanvas.height;
                    for (let i = 0; i < zone.spatialMask.length && i < cw * ch; i++) {
                        const v = zone.spatialMask[i];
                        if (v === 0) continue;
                        const pi = i * 4;
                        if (v === 1) {
                            // Include = green overlay
                            data[pi] = 0; data[pi + 1] = 200; data[pi + 2] = 100; data[pi + 3] = 128;
                        } else if (v === 2) {
                            // Exclude = red overlay
                            data[pi] = 220; data[pi + 1] = 50; data[pi + 2] = 50; data[pi + 3] = 128;
                        }
                    }
                }
            }


            // Draw bright edge outlines for the selected zone only
            {
                const zi = selectedZoneIndex;
                const zone = zones[zi];
                if (zone && zone.regionMask) {
                    const color = ZONE_OVERLAY_COLORS[zi % ZONE_OVERLAY_COLORS.length];
                    const cw = paintCanvas.width, ch = paintCanvas.height;
                    for (let y = 0; y < ch; y++) {
                        for (let x = 0; x < cw; x++) {
                            const idx = y * cw + x;
                            if (zone.regionMask[idx] > 0) {
                                const isEdge = (
                                    x === 0 || x === cw - 1 || y === 0 || y === ch - 1 ||
                                    zone.regionMask[idx - 1] === 0 || zone.regionMask[idx + 1] === 0 ||
                                    zone.regionMask[idx - cw] === 0 || zone.regionMask[idx + cw] === 0
                                );
                                if (isEdge) {
                                    const pi = idx * 4;
                                    imgData.data[pi] = 255; imgData.data[pi + 1] = 255;
                                    imgData.data[pi + 2] = 255; imgData.data[pi + 3] = 255;
                                }
                            }
                        }
                    }
                }
            }
            ctx.putImageData(imgData, 0, 0);

            // Draw decals on top of zone overlay (when Decals & Numbers panel is active)
            if (typeof drawDecalsOnContext === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) {
                drawDecalsOnContext(ctx, regionCanvas.width, regionCanvas.height);
            }
            if (typeof drawDecalSelectionBox === 'function') {
                drawDecalSelectionBox(ctx, regionCanvas.width, regionCanvas.height);
            }
        }

        // ===== UNDO SYSTEM =====
        function pushUndo(zoneIndex) {
            const zone = zones[zoneIndex];
            if (!zone) return;
            // Save a copy of the current masks (or null if no mask yet)
            const prevMask = zone.regionMask ? new Uint8Array(zone.regionMask) : null;
            const prevSpatial = zone.spatialMask ? new Uint8Array(zone.spatialMask) : null;
            undoStack.push({ zoneIndex, prevMask, prevSpatial });
            if (typeof redoStack !== 'undefined') redoStack.length = 0; // Clear redo on new action
            // Trim stack if too large
            if (undoStack.length > MAX_UNDO) undoStack.shift();
        }

        function undoDrawStroke() {
            if (undoStack.length === 0) {
                showToast('Nothing to undo');
                return;
            }
            const entry = undoStack.pop();
            const zone = zones[entry.zoneIndex];
            if (!zone) return;
            // Push current state to redo stack before reverting
            if (typeof redoStack !== 'undefined') {
                redoStack.push({
                    zoneIndex: entry.zoneIndex,
                    prevMask: zone.regionMask ? new Uint8Array(zone.regionMask) : null,
                    prevSpatial: zone.spatialMask ? new Uint8Array(zone.spatialMask) : null
                });
            }
            zone.regionMask = entry.prevMask;
            zone.spatialMask = entry.prevSpatial;
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Undo: reverted Zone ${entry.zoneIndex + 1} actions`);
        }

        function redoDrawStroke() {
            if (typeof redoStack === 'undefined' || redoStack.length === 0) {
                showToast('Nothing to redo');
                return;
            }
            const entry = redoStack.pop();
            const zone = zones[entry.zoneIndex];
            if (!zone) return;
            zone.regionMask = entry.prevMask;
            zone.spatialMask = entry.prevSpatial;
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Redo: Zone ${entry.zoneIndex + 1} actions`);
        }

        // ===== MAGIC WAND / FLOOD FILL =====
        function magicWandFill(startX, startY, tolerance, addToExisting) {
            const zone = zones[selectedZoneIndex];
            if (!zone) return;
            if (!paintImageData) {
                showToast('Load a paint image first!');
                return;
            }

            const canvas = document.getElementById('paintCanvas');
            const w = canvas.width;
            const h = canvas.height;
            const data = paintImageData.data; // RGBA pixel data

            // Initialize zone mask if needed
            if (!zone.regionMask) {
                zone.regionMask = new Uint8Array(w * h);
            } else if (!addToExisting) {
                // If not shift+click, replace existing mask
                zone.regionMask = new Uint8Array(w * h);
            }

            // Get seed color
            const seedIdx = (startY * w + startX) * 4;
            const seedR = data[seedIdx];
            const seedG = data[seedIdx + 1];
            const seedB = data[seedIdx + 2];

            // Visited array to avoid revisiting
            const visited = new Uint8Array(w * h);

            // Color distance function (Photoshop Chebyshev Distance)
            function colorMatch(idx) {
                const pi = idx * 4;
                const rDiff = Math.abs(data[pi] - seedR);
                const gDiff = Math.abs(data[pi + 1] - seedG);
                const bDiff = Math.abs(data[pi + 2] - seedB);

                // Chebyshev distance matches exactly how Photoshop's tolerance slider works
                return Math.max(rDiff, gDiff, bDiff) <= tolerance;
            }

            // Stack-based flood fill using 8-connectivity (cardinal + diagonal)
            // 8-connectivity prevents leaking through 1px diagonal gaps (PS behavior)
            let filled = 0;
            const seedPos = startY * w + startX;
            if (!colorMatch(seedPos)) {
                showToast('Clicked pixel doesn\'t match - try a different spot or increase tolerance');
                return;
            }

            const stack = [seedPos];
            visited[seedPos] = 1;

            while (stack.length > 0) {
                const pos = stack.pop();
                zone.regionMask[pos] = 1;
                filled++;

                const px = pos % w;
                const py = (pos - px) / w;

                // 8 neighbors: cardinal + diagonal
                const neighbors = [];
                if (px > 0) neighbors.push(pos - 1);                         // Left
                if (px < w - 1) neighbors.push(pos + 1);                     // Right
                if (py > 0) neighbors.push(pos - w);                         // Up
                if (py < h - 1) neighbors.push(pos + w);                     // Down
                if (px > 0 && py > 0) neighbors.push(pos - w - 1);           // Top-Left
                if (px < w - 1 && py > 0) neighbors.push(pos - w + 1);       // Top-Right
                if (px > 0 && py < h - 1) neighbors.push(pos + w - 1);       // Bottom-Left
                if (px < w - 1 && py < h - 1) neighbors.push(pos + w + 1);   // Bottom-Right

                for (const npos of neighbors) {
                    if (!visited[npos] && colorMatch(npos)) {
                        visited[npos] = 1;
                        stack.push(npos);
                    }
                }
            }

            // Post-fill constrained 1px dilation - captures anti-aliased edge pixels that
            // are blended between the target color and surrounding outlines, but STOPS at
            // dramatically different colors (white, black, blue). Only expands into pixels
            // whose max per-channel diff from the seed is within 5x the tolerance.
            const dilThreshold = tolerance * 5; // generous enough to catch blended anti-aliased edges
            const dilated = new Uint8Array(zone.regionMask);

            function dilatePixel(npos) {
                if (dilated[npos]) return; // already selected
                const pi = npos * 4;
                const rDiff = Math.abs(data[pi] - seedR);
                const gDiff = Math.abs(data[pi + 1] - seedG);
                const bDiff = Math.abs(data[pi + 2] - seedB);
                if (Math.max(rDiff, gDiff, bDiff) <= dilThreshold) {
                    dilated[npos] = 1;
                    filled++;
                }
            }

            for (let pos = 0; pos < w * h; pos++) {
                if (zone.regionMask[pos] !== 1) continue;
                const px = pos % w;
                const py = (pos - px) / w;
                if (px > 0) dilatePixel(pos - 1);
                if (px < w - 1) dilatePixel(pos + 1);
                if (py > 0) dilatePixel(pos - w);
                if (py < h - 1) dilatePixel(pos + w);
                if (px > 0 && py > 0) dilatePixel(pos - w - 1);
                if (px < w - 1 && py > 0) dilatePixel(pos - w + 1);
                if (px > 0 && py < h - 1) dilatePixel(pos + w - 1);
                if (px < w - 1 && py < h - 1) dilatePixel(pos + w + 1);
            }
            zone.regionMask = dilated;

            showToast(`Magic Wand: selected ${filled.toLocaleString()} pixels (Shift=add, Alt=subtract)`);
        }

        // ===== SUBTRACT WAND SELECTION - Alt+click removes matching pixels =====
        function subtractWandSelection(startX, startY, tolerance, contiguous) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !paintImageData) { showToast('Load a paint image first!'); return; }
            if (!zone.regionMask) { showToast('No selection to subtract from'); return; }
            const canvas = document.getElementById('paintCanvas');
            const w = canvas.width, h = canvas.height;
            const data = paintImageData.data;

            const seedIdx = (startY * w + startX) * 4;
            const seedR = data[seedIdx], seedG = data[seedIdx + 1], seedB = data[seedIdx + 2];
            let removed = 0;

            function colorMatch(idx) {
                const pi = idx * 4;
                const rDiff = Math.abs(data[pi] - seedR);
                const gDiff = Math.abs(data[pi + 1] - seedG);
                const bDiff = Math.abs(data[pi + 2] - seedB);
                return Math.max(rDiff, gDiff, bDiff) <= tolerance;
            }

            if (contiguous) {
                // Flood fill subtract - only remove connected matching pixels
                const visited = new Uint8Array(w * h);
                const seedPos = startY * w + startX;
                if (!colorMatch(seedPos)) { showToast('Clicked pixel doesn\'t match'); return; }
                const stack = [seedPos];
                visited[seedPos] = 1;
                while (stack.length > 0) {
                    const pos = stack.pop();
                    if (zone.regionMask[pos] > 0) { zone.regionMask[pos] = 0; removed++; }
                    const px = pos % w, py = (pos - px) / w;
                    const neighbors = [];
                    if (px > 0) neighbors.push(pos - 1);
                    if (px < w - 1) neighbors.push(pos + 1);
                    if (py > 0) neighbors.push(pos - w);
                    if (py < h - 1) neighbors.push(pos + w);
                    if (px > 0 && py > 0) neighbors.push(pos - w - 1);
                    if (px < w - 1 && py > 0) neighbors.push(pos - w + 1);
                    if (px > 0 && py < h - 1) neighbors.push(pos + w - 1);
                    if (px < w - 1 && py < h - 1) neighbors.push(pos + w + 1);
                    for (const npos of neighbors) {
                        if (!visited[npos] && colorMatch(npos)) { visited[npos] = 1; stack.push(npos); }
                    }
                }
            } else {
                // Global subtract - remove ALL matching pixels
                for (let i = 0; i < w * h; i++) {
                    if (zone.regionMask[i] > 0 && colorMatch(i)) { zone.regionMask[i] = 0; removed++; }
                }
            }
            showToast(`Subtracted ${removed.toLocaleString()} pixels from selection`);
        }

        // Select ALL pixels of clicked color everywhere (not just connected)
        function selectAllColor(startX, startY, tolerance, addToExisting) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !paintImageData) { showToast('Load a paint image first!'); return; }
            const canvas = document.getElementById('paintCanvas');
            const w = canvas.width, h = canvas.height;
            const data = paintImageData.data;

            if (!zone.regionMask || !addToExisting) zone.regionMask = new Uint8Array(w * h);

            const seedIdx = (startY * w + startX) * 4;
            const seedR = data[seedIdx], seedG = data[seedIdx + 1], seedB = data[seedIdx + 2];
            let filled = 0;

            for (let i = 0; i < w * h; i++) {
                const pi = i * 4;
                const rDiff = Math.abs(data[pi] - seedR);
                const gDiff = Math.abs(data[pi + 1] - seedG);
                const bDiff = Math.abs(data[pi + 2] - seedB);

                if (Math.max(rDiff, gDiff, bDiff) <= tolerance) {
                    zone.regionMask[i] = 1;
                    filled++;
                }
            }
            showToast(`Select All Color: ${filled.toLocaleString()} pixels (Shift+click to add more)`);
        }

        // Edge-aware flood fill - stops at hard color boundaries. subtractMode: remove from selection (Alt+click).
        function edgeDetectFill(startX, startY, tolerance, addToExisting, subtractMode) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !paintImageData) { showToast('Load a paint image first!'); return; }
            const canvas = document.getElementById('paintCanvas');
            const w = canvas.width, h = canvas.height;
            const data = paintImageData.data;

            if (!zone.regionMask) zone.regionMask = new Uint8Array(w * h);
            else if (!addToExisting && !subtractMode) zone.regionMask = new Uint8Array(w * h);
            if (subtractMode) {
                // Subtract: flood-fill and set matching pixels to 0
                const edgeThreshold = tolerance * 1.5;
                const visited = new Uint8Array(w * h);
                let removed = 0;

                function getGray(x, y) {
                    if (x < 0 || x >= w || y < 0 || y >= h) return 0;
                    const pi = (y * w + x) * 4;
                    return data[pi] * 0.299 + data[pi + 1] * 0.587 + data[pi + 2] * 0.114;
                }
                function isEdge(x, y) {
                    const gx = -getGray(x - 1, y - 1) - 2 * getGray(x - 1, y) - getGray(x - 1, y + 1)
                        + getGray(x + 1, y - 1) + 2 * getGray(x + 1, y) + getGray(x + 1, y + 1);
                    const gy = -getGray(x - 1, y - 1) - 2 * getGray(x, y - 1) - getGray(x + 1, y - 1)
                        + getGray(x - 1, y + 1) + 2 * getGray(x, y + 1) + getGray(x + 1, y + 1);
                    return Math.sqrt(gx * gx + gy * gy) > edgeThreshold;
                }
                const seedPos = startY * w + startX;
                if (isEdge(startX, startY)) { showToast('Clicked on an edge - try inside a region'); return; }
                const stack = [seedPos];
                visited[seedPos] = 1;
                while (stack.length > 0) {
                    const pos = stack.pop();
                    if (zone.regionMask[pos] > 0) { zone.regionMask[pos] = 0; removed++; }
                    const px = pos % w, py = (pos - px) / w;
                    const neighbors = [];
                    if (px > 0) neighbors.push(pos - 1);
                    if (px < w - 1) neighbors.push(pos + 1);
                    if (py > 0) neighbors.push(pos - w);
                    if (py < h - 1) neighbors.push(pos + w);
                    for (const npos of neighbors) {
                        if (visited[npos]) continue;
                        visited[npos] = 1;
                        const nx = npos % w, ny = (npos - nx) / w;
                        if (!isEdge(nx, ny)) stack.push(npos);
                    }
                }
                showToast(`Edge Subtract: removed ${removed.toLocaleString()} pixels`);
                return;
            }

            // Add/replace: flood fill stopping at edges
            const edgeThreshold = tolerance * 1.5; // Edge detection uses tolerance as sensitivity
            const visited = new Uint8Array(w * h);
            let filled = 0;

            function getGray(x, y) {
                if (x < 0 || x >= w || y < 0 || y >= h) return 0;
                const pi = (y * w + x) * 4;
                return data[pi] * 0.299 + data[pi + 1] * 0.587 + data[pi + 2] * 0.114;
            }

            function isEdge(x, y) {
                // Sobel gradient magnitude
                const gx = -getGray(x - 1, y - 1) - 2 * getGray(x - 1, y) - getGray(x - 1, y + 1)
                    + getGray(x + 1, y - 1) + 2 * getGray(x + 1, y) + getGray(x + 1, y + 1);
                const gy = -getGray(x - 1, y - 1) - 2 * getGray(x, y - 1) - getGray(x + 1, y - 1)
                    + getGray(x - 1, y + 1) + 2 * getGray(x, y + 1) + getGray(x + 1, y + 1);
                return Math.sqrt(gx * gx + gy * gy) > edgeThreshold;
            }

            // Flood fill stopping at edges
            const seedPos = startY * w + startX;
            if (isEdge(startX, startY)) {
                showToast('Clicked on an edge - try clicking inside a region');
                return;
            }

            const stack = [seedPos];
            visited[seedPos] = 1;

            while (stack.length > 0) {
                const pos = stack.pop();
                zone.regionMask[pos] = 1;
                filled++;

                const px = pos % w;
                const py = (pos - px) / w;

                const neighbors = [];
                if (px > 0) neighbors.push(pos - 1);
                if (px < w - 1) neighbors.push(pos + 1);
                if (py > 0) neighbors.push(pos - w);
                if (py < h - 1) neighbors.push(pos + w);

                for (const npos of neighbors) {
                    if (visited[npos]) continue;
                    visited[npos] = 1;
                    const nx = npos % w;
                    const ny = (npos - nx) / w;
                    if (!isEdge(nx, ny)) {
                        stack.push(npos);
                    }
                }
            }
            showToast(`Edge Fill: ${filled.toLocaleString()} pixels (bounded by edges, Shift+click to add)`);
        }

        // ===== EDGE DETECTION PREVIEW OVERLAY =====
        let edgePreviewActive = false;
        let edgePreviewImageData = null;  // cached edge map ImageData for overlay

        function toggleEdgePreview() {
            edgePreviewActive = !edgePreviewActive;
            const btn = document.getElementById('edgePreviewBtn');
            if (edgePreviewActive) {
                btn.style.background = 'var(--accent-gold)';
                btn.style.color = '#111';
                computeEdgePreview();
            } else {
                btn.style.background = '';
                btn.style.color = 'var(--accent-gold)';
                clearEdgePreviewOverlay();
            }
        }

        function computeEdgePreview() {
            if (!paintImageData) return;
            const canvas = document.getElementById('paintCanvas');
            const w = canvas.width, h = canvas.height;
            const data = paintImageData.data;
            const tolerance = parseInt(document.getElementById('wandTolerance').value) || 32;
            const edgeThreshold = tolerance * 1.5;

            // Compute Sobel edge map
            function getGray(x, y) {
                if (x < 0 || x >= w || y < 0 || y >= h) return 0;
                const pi = (y * w + x) * 4;
                return data[pi] * 0.299 + data[pi + 1] * 0.587 + data[pi + 2] * 0.114;
            }

            // Create overlay ImageData (RGBA)
            const overlay = new ImageData(w, h);
            const od = overlay.data;

            for (let y = 1; y < h - 1; y++) {
                for (let x = 1; x < w - 1; x++) {
                    const gx = -getGray(x - 1, y - 1) - 2 * getGray(x - 1, y) - getGray(x - 1, y + 1)
                        + getGray(x + 1, y - 1) + 2 * getGray(x + 1, y) + getGray(x + 1, y + 1);
                    const gy = -getGray(x - 1, y - 1) - 2 * getGray(x, y - 1) - getGray(x + 1, y - 1)
                        + getGray(x - 1, y + 1) + 2 * getGray(x, y + 1) + getGray(x + 1, y + 1);
                    const mag = Math.sqrt(gx * gx + gy * gy);

                    if (mag > edgeThreshold) {
                        const pi = (y * w + x) * 4;
                        // Red with intensity based on edge strength (brighter = stronger edge)
                        const intensity = Math.min(255, Math.floor(mag * 2));
                        od[pi] = 255;         // R
                        od[pi + 1] = 40;      // G (slight warmth)
                        od[pi + 2] = 40;      // B
                        od[pi + 3] = Math.min(200, intensity);  // A
                    }
                }
            }
            edgePreviewImageData = overlay;
            renderEdgePreviewOverlay();
        }

        function renderEdgePreviewOverlay() {
            if (!edgePreviewImageData) return;
            // Use a dedicated canvas layer for edge preview
            let edgeCanvas = document.getElementById('edgePreviewCanvas');
            if (!edgeCanvas) {
                edgeCanvas = document.createElement('canvas');
                edgeCanvas.id = 'edgePreviewCanvas';
                edgeCanvas.style.cssText = 'position:absolute; top:0; left:0; pointer-events:none; z-index:15; image-rendering:pixelated;';
                const viewport = document.getElementById('canvasViewport');
                if (viewport) viewport.appendChild(edgeCanvas);
            }
            const paintCanvas = document.getElementById('paintCanvas');
            edgeCanvas.width = paintCanvas.width;
            edgeCanvas.height = paintCanvas.height;
            edgeCanvas.style.width = paintCanvas.style.width;
            edgeCanvas.style.height = paintCanvas.style.height;
            edgeCanvas.style.transform = paintCanvas.style.transform || '';
            // Match paint canvas position
            edgeCanvas.style.transformOrigin = paintCanvas.style.transformOrigin || '';

            const ctx = edgeCanvas.getContext('2d');
            ctx.clearRect(0, 0, edgeCanvas.width, edgeCanvas.height);
            ctx.putImageData(edgePreviewImageData, 0, 0);
        }

        function clearEdgePreviewOverlay() {
            edgePreviewImageData = null;
            const edgeCanvas = document.getElementById('edgePreviewCanvas');
            if (edgeCanvas) {
                const ctx = edgeCanvas.getContext('2d');
                ctx.clearRect(0, 0, edgeCanvas.width, edgeCanvas.height);
            }
        }

        // Hook into tolerance slider to update edge preview live
        (function () {
            const tolSlider = document.getElementById('wandTolerance');
            if (tolSlider) {
                const origOninput = tolSlider.oninput;
                tolSlider.addEventListener('input', function () {
                    if (edgePreviewActive) {
                        // Debounce: delay recompute slightly
                        clearTimeout(tolSlider._edgePreviewTimer);
                        tolSlider._edgePreviewTimer = setTimeout(computeEdgePreview, 80);
                    }
                });
            }
        })();

        function clearZoneRegions(zoneIndex, noToast) {
            if (zones[zoneIndex]) {
                pushUndo(zoneIndex); // Save state before clearing
                zones[zoneIndex].regionMask = null;
                renderRegionOverlay();
                triggerPreviewRender();
                if (!noToast) showToast(`Cleared drawn regions for ${zones[zoneIndex].name}`);
            }
        }

        function clearAllRegions() {
            zones.forEach(z => z.regionMask = null);
            renderRegionOverlay();
            showToast('Cleared all drawn regions');
        }

        // ===== SPATIAL MASK - Include/Exclude refinement for color-based zones =====
        // spatialMask is a Uint8Array: 0=unset, 1=include(green), 2=exclude(red)
        // Unlike regionMask which REPLACES color detection, spatialMask REFINES it.

        function pushSpatialUndo(zoneIndex) {
            pushUndo(zoneIndex); // Forward to unified undo
        }

        function undoSpatialStroke() {
            undoDrawStroke(); // Forward to unified undo
        }

        function paintSpatialCircle(cx, cy, radius, value) {
            const zone = zones[selectedZoneIndex];
            if (!zone) return;
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;

            // Initialize mask if needed
            if (!zone.spatialMask) {
                zone.spatialMask = new Uint8Array(w * h);
            }

            // Paint circle
            const r2 = radius * radius;
            const x0 = Math.max(0, Math.floor(cx - radius));
            const x1 = Math.min(w - 1, Math.ceil(cx + radius));
            const y0 = Math.max(0, Math.floor(cy - radius));
            const y1 = Math.min(h - 1, Math.ceil(cy + radius));
            for (let y = y0; y <= y1; y++) {
                for (let x = x0; x <= x1; x++) {
                    if ((x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2) {
                        zone.spatialMask[y * w + x] = value;
                    }
                }
            }
        }

        function clearSpatialMask(zoneIndex) {
            const zone = zones[zoneIndex];
            if (!zone) return;
            pushSpatialUndo(zoneIndex);
            zone.spatialMask = null;
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Cleared spatial mask for ${zone.name}`);
        }

        function eraseSpatialCircle(cx, cy, radius) {
            // Erase = set to 0 (unset)
            paintSpatialCircle(cx, cy, radius, 0);
        }

        function toggleSpatialMode(mode) {
            // mode: 'include', 'exclude', 'erase-spatial', 'off'
            const cvs = document.getElementById('paintCanvas');
            if (mode === 'include') {
                canvasMode = 'spatial-include';
                if (cvs) cvs.style.cursor = 'crosshair';
                showToast('Spatial Include: paint areas to KEEP in this zone (green)');
            } else if (mode === 'exclude') {
                canvasMode = 'spatial-exclude';
                if (cvs) cvs.style.cursor = 'crosshair';
                showToast('Spatial Exclude: paint areas to REMOVE from this zone (red)');
            } else if (mode === 'erase-spatial') {
                canvasMode = 'spatial-include'; // reuse include but with value=0
                // We'll handle erase by checking dedicated button state
                if (cvs) cvs.style.cursor = 'crosshair';
                showToast('Spatial Eraser: clear include/exclude marks');
            } else {
                canvasMode = 'eyedropper';
                if (cvs) cvs.style.cursor = 'crosshair';
            }
            renderZoneDetail(selectedZoneIndex);
        }

        function hasSpatialMask(zone) {
            return zone && zone.spatialMask && zone.spatialMask.some(v => v > 0);
        }

        // ===== ADVANCED MASK OPERATIONS =====

        // --- INVERT SELECTION --- flip 0↔1 in regionMask
        function invertRegionMask() {
            const zone = zones[selectedZoneIndex];
            if (!zone) return;
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            pushUndo(selectedZoneIndex);
            if (!zone.regionMask) {
                // Invert empty → fill everything
                zone.regionMask = new Uint8Array(w * h).fill(1);
            } else {
                for (let i = 0; i < zone.regionMask.length; i++) {
                    zone.regionMask[i] = zone.regionMask[i] > 0 ? 0 : 1;
                }
            }
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Inverted selection for Zone ${selectedZoneIndex + 1}`);
        }

        // --- GROW SELECTION --- fast BFS morphological dilation
        // Instead of checking every pixel against every neighbor, we do N iterations
        // of single-pixel dilation from the boundary - O(boundary × n) vs O(w×h×n²)
        function growRegionMask(px) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to grow - draw one first'); return; }
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            const n = px || 2;
            pushUndo(selectedZoneIndex);
            const mask = zone.regionMask;

            for (let iter = 0; iter < n; iter++) {
                // Collect current boundary pixels (filled pixels adjacent to empty)
                const boundary = [];
                for (let y = 0; y < h; y++) {
                    for (let x = 0; x < w; x++) {
                        const idx = y * w + x;
                        if (mask[idx] > 0) continue; // already filled
                        // Check 8 neighbors for any filled pixel
                        let adj = false;
                        if (x > 0 && mask[idx - 1] > 0) adj = true;
                        else if (x < w - 1 && mask[idx + 1] > 0) adj = true;
                        else if (y > 0 && mask[idx - w] > 0) adj = true;
                        else if (y < h - 1 && mask[idx + w] > 0) adj = true;
                        else if (x > 0 && y > 0 && mask[idx - w - 1] > 0) adj = true;
                        else if (x < w - 1 && y > 0 && mask[idx - w + 1] > 0) adj = true;
                        else if (x > 0 && y < h - 1 && mask[idx + w - 1] > 0) adj = true;
                        else if (x < w - 1 && y < h - 1 && mask[idx + w + 1] > 0) adj = true;
                        if (adj) boundary.push(idx);
                    }
                }
                // Expand: fill all boundary pixels
                for (const idx of boundary) mask[idx] = 1;
                if (boundary.length === 0) break; // nothing left to grow
            }
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Grew selection by ${n}px`);
        }

        // --- SHRINK SELECTION --- fast BFS morphological erosion
        // N iterations of single-pixel erosion from the boundary
        function shrinkRegionMask(px) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to shrink'); return; }
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            const n = px || 2;
            pushUndo(selectedZoneIndex);
            const mask = zone.regionMask;

            for (let iter = 0; iter < n; iter++) {
                // Collect edge pixels (filled pixels adjacent to empty or image border)
                const edgePixels = [];
                for (let y = 0; y < h; y++) {
                    for (let x = 0; x < w; x++) {
                        const idx = y * w + x;
                        if (mask[idx] === 0) continue; // already empty
                        // Check if on image border or adjacent to empty pixel
                        let onEdge = (x === 0 || x === w - 1 || y === 0 || y === h - 1);
                        if (!onEdge) {
                            if (mask[idx - 1] === 0 || mask[idx + 1] === 0 ||
                                mask[idx - w] === 0 || mask[idx + w] === 0 ||
                                mask[idx - w - 1] === 0 || mask[idx - w + 1] === 0 ||
                                mask[idx + w - 1] === 0 || mask[idx + w + 1] === 0) {
                                onEdge = true;
                            }
                        }
                        if (onEdge) edgePixels.push(idx);
                    }
                }
                // Erode: clear all edge pixels
                for (const idx of edgePixels) mask[idx] = 0;
                if (edgePixels.length === 0) break; // nothing left to shrink
            }
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Shrunk selection by ${n}px`);
        }

        // --- FILL HOLES --- flood fill from edges to find enclosed gaps
        function fillRegionHoles() {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to fill holes in'); return; }
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            pushUndo(selectedZoneIndex);

            // Flood fill from all edge-touching empty pixels
            const visited = new Uint8Array(w * h);
            const stack = [];
            // Seed from all 4 edges
            for (let x = 0; x < w; x++) {
                if (zone.regionMask[x] === 0 && !visited[x]) { stack.push(x); visited[x] = 1; }
                const bot = (h - 1) * w + x;
                if (zone.regionMask[bot] === 0 && !visited[bot]) { stack.push(bot); visited[bot] = 1; }
            }
            for (let y = 0; y < h; y++) {
                const left = y * w;
                if (zone.regionMask[left] === 0 && !visited[left]) { stack.push(left); visited[left] = 1; }
                const right = y * w + w - 1;
                if (zone.regionMask[right] === 0 && !visited[right]) { stack.push(right); visited[right] = 1; }
            }
            // BFS flood
            while (stack.length > 0) {
                const pos = stack.pop();
                const px = pos % w, py = Math.floor(pos / w);
                const neighbors = [];
                if (px > 0) neighbors.push(pos - 1);
                if (px < w - 1) neighbors.push(pos + 1);
                if (py > 0) neighbors.push(pos - w);
                if (py < h - 1) neighbors.push(pos + w);
                for (const nb of neighbors) {
                    if (!visited[nb] && zone.regionMask[nb] === 0) {
                        visited[nb] = 1;
                        stack.push(nb);
                    }
                }
            }
            // Any unvisited empty pixel is an enclosed hole → fill it
            let filled = 0;
            for (let i = 0; i < w * h; i++) {
                if (zone.regionMask[i] === 0 && !visited[i]) {
                    zone.regionMask[i] = 1;
                    filled++;
                }
            }
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Filled ${filled.toLocaleString()} hole pixels`);
        }

        // --- FEATHER SELECTION --- grow then shrink by same amount to soften edges
        function featherRegionMask(px) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to feather - draw one first'); return; }
            const n = Math.max(1, Math.min(8, parseInt(px, 10) || 2));
            pushUndo(selectedZoneIndex);
            growRegionMask(n);
            shrinkRegionMask(n);
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Feathered selection by ${n}px`);
        }

        // --- SMOOTH SELECTION --- shrink 1 then grow 1 to reduce jagged edges
        function smoothRegionMask() {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to smooth'); return; }
            pushUndo(selectedZoneIndex);
            shrinkRegionMask(1);
            growRegionMask(1);
            renderRegionOverlay();
            triggerPreviewRender();
            showToast('Smoothed selection edge');
        }

        // --- DESELECT --- clear current zone's drawn region and switch to Pick
        function deselectRegion() {
            clearZoneRegions(selectedZoneIndex, true);
            if (typeof setCanvasMode === 'function') setCanvasMode('eyedropper');
            showToast('Cleared selection and switched to Pick');
        }

        // --- COPY MASK BETWEEN ZONES ---
        function toggleCopyMaskDropdown(e) {
            if (e) e.stopPropagation();
            const dd = document.getElementById('copyMaskDropdown');
            if (!dd) return;
            if (dd.style.display !== 'none') { dd.style.display = 'none'; return; }
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region mask to copy'); return; }
            // Build dropdown items
            let html = '';
            zones.forEach((z, i) => {
                if (i === selectedZoneIndex) return;
                const color = ZONE_OVERLAY_COLORS[i % ZONE_OVERLAY_COLORS.length];
                const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:rgb(${color[0]},${color[1]},${color[2]});margin-right:5px;vertical-align:middle;"></span>`;
                html += `<div onclick="copyMaskToZone(${i}); document.getElementById('copyMaskDropdown').style.display='none';" 
                    style="padding:4px 10px; cursor:pointer; font-size:10px; color:var(--text); white-space:nowrap; transition:background 0.15s;"
                    onmouseenter="this.style.background='var(--accent-blue-dim)'" 
                    onmouseleave="this.style.background='transparent'">
                    ${dot}Zone ${i + 1}: ${z.name}
                </div>`;
            });
            if (!html) html = '<div style="padding:6px 10px; font-size:10px; color:var(--text-dim);">No other zones</div>';
            dd.innerHTML = html;
            dd.style.display = 'block';
            // Close on outside click
            setTimeout(() => {
                function closeDd(ev) { if (!dd.contains(ev.target)) { dd.style.display = 'none'; document.removeEventListener('mousedown', closeDd); } }
                document.addEventListener('mousedown', closeDd);
            }, 10);
        }

        function copyMaskToZone(targetIndex) {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region mask to copy'); return; }
            if (targetIndex == null || targetIndex < 0 || targetIndex >= zones.length || targetIndex === selectedZoneIndex) {
                showToast('Invalid zone number'); return;
            }
            pushUndo(targetIndex);
            zones[targetIndex].regionMask = new Uint8Array(zone.regionMask);
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Copied mask from Zone ${selectedZoneIndex + 1} → Zone ${targetIndex + 1}`);
        }

        // --- MIRROR/FLIP MASK --- horizontal flip
        function mirrorRegionMask() {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to mirror'); return; }
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            pushUndo(selectedZoneIndex);
            for (let y = 0; y < h; y++) {
                const row = y * w;
                for (let x = 0; x < Math.floor(w / 2); x++) {
                    const left = row + x;
                    const right = row + w - 1 - x;
                    const tmp = zone.regionMask[left];
                    zone.regionMask[left] = zone.regionMask[right];
                    zone.regionMask[right] = tmp;
                }
            }
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Mirrored region mask horizontally for Zone ${selectedZoneIndex + 1}`);
        }

        // --- OVERLAY OPACITY --- adjustable zone overlay transparency
        let overlayOpacityMultiplier = 1.0; // 0.0 - 2.0 range, 1.0 = default

        function setOverlayOpacity(val) {
            overlayOpacityMultiplier = parseFloat(val);
            _doRenderRegionOverlay();
            document.getElementById('overlayOpacityVal').textContent = Math.round(val * 50) + '%';
        }

        // --- ZOOM TO SELECTION --- auto-zoom to fit mask bounding box
        function zoomToSelection() {
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask) { showToast('No region to zoom to'); return; }
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;

            // Find bounding box
            let minX = w, maxX = 0, minY = h, maxY = 0;
            for (let y = 0; y < h; y++) {
                for (let x = 0; x < w; x++) {
                    if (zone.regionMask[y * w + x] > 0) {
                        if (x < minX) minX = x;
                        if (x > maxX) maxX = x;
                        if (y < minY) minY = y;
                        if (y > maxY) maxY = y;
                    }
                }
            }
            if (maxX < minX) { showToast('Selection is empty'); return; }

            // Calculate required zoom to fit bounding box in viewport
            const viewport = document.getElementById('canvasViewport');
            if (!viewport) return;
            const vpW = viewport.clientWidth - 40;
            const vpH = viewport.clientHeight - 40;
            const selW = maxX - minX + 1;
            const selH = maxY - minY + 1;
            const zoomX = vpW / selW;
            const zoomY = vpH / selH;
            const targetZoom = Math.min(zoomX, zoomY, 8.0); // Cap at 8x

            // Apply zoom
            currentZoom = Math.max(0.1, targetZoom);
            applyZoom();

            // Scroll to center of selection
            setTimeout(() => {
                const sc = getScrollContainer();
                if (!sc) return;
                const centerX = (minX + maxX) / 2;
                const centerY = (minY + maxY) / 2;
                sc.scrollLeft = centerX * currentZoom - vpW / 2;
                sc.scrollTop = centerY * currentZoom - vpH / 2;
            }, 50);

            showToast(`Zoomed to selection (${selW}×${selH}px)`);
        }

        // --- LASSO / POLYGON SELECT --- click vertices, fill inside on close
        let lassoPoints = [];
        let lassoActive = false;
        let lassoFreehandDrawing = false;
        let lassoMouseDownPos = null;

        function startLasso() {
            lassoPoints = [];
            lassoActive = true;
        }

        function addLassoPoint(x, y) {
            lassoPoints.push({ x, y });
            drawLassoPreview();
        }

        function closeLasso(e) {
            if (lassoPoints.length < 3) {
                showToast('Need at least 3 points for polygon selection');
                lassoActive = false;
                lassoPoints = [];
                return;
            }
            const zone = zones[selectedZoneIndex];
            if (!zone) return;
            const canvas = document.getElementById('paintCanvas');
            if (!canvas) return;
            const w = canvas.width, h = canvas.height;
            pushUndo(selectedZoneIndex);

            const selMode = document.getElementById('selectionMode')?.value || 'add';
            const eShift = e?.shiftKey || false;
            const eAlt = e?.altKey || false;
            let replaceMode = selMode === 'replace' && !eShift && !eAlt;
            let subtractMode = selMode === 'subtract' || eAlt;

            if (!zone.regionMask || replaceMode) {
                zone.regionMask = new Uint8Array(w * h);
            }

            const fillVal = subtractMode ? 0 : 1;

            // Fill polygon using scanline approach
            // Find bounding box
            let minX = w, maxX = 0, minY = h, maxY = 0;
            for (const p of lassoPoints) {
                if (p.x < minX) minX = Math.floor(p.x);
                if (p.x > maxX) maxX = Math.ceil(p.x);
                if (p.y < minY) minY = Math.floor(p.y);
                if (p.y > maxY) maxY = Math.ceil(p.y);
            }
            minX = Math.max(0, minX); maxX = Math.min(w - 1, maxX);
            minY = Math.max(0, minY); maxY = Math.min(h - 1, maxY);

            // Point-in-polygon test (ray casting)
            const pts = lassoPoints;
            const n = pts.length;
            let filled = 0;
            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    let inside = false;
                    for (let i = 0, j = n - 1; i < n; j = i++) {
                        const xi = pts[i].x, yi = pts[i].y;
                        const xj = pts[j].x, yj = pts[j].y;
                        if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
                            inside = !inside;
                        }
                    }
                    if (inside) {
                        zone.regionMask[y * w + x] = fillVal;
                        filled++;
                    }
                }
            }

            lassoActive = false;
            lassoPoints = [];
            hideLassoPreview();
            renderRegionOverlay();
            triggerPreviewRender();
            showToast(`Lasso: filled ${filled.toLocaleString()} pixels`);
        }

        function drawLassoPreview() {
            const canvas = document.getElementById('paintCanvas');
            const regionCanvas = document.getElementById('regionCanvas');
            if (!canvas || !regionCanvas) return;
            // Draw lasso preview lines on region canvas overlay
            _doRenderRegionOverlay(); // Full redraw since we overlay on top
            if (lassoPoints.length < 2) return;
            const ctx = regionCanvas.getContext('2d');
            ctx.save();
            ctx.strokeStyle = 'rgba(255,255,0,0.9)';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 3]);
            ctx.beginPath();
            ctx.moveTo(lassoPoints[0].x, lassoPoints[0].y);
            for (let i = 1; i < lassoPoints.length; i++) {
                ctx.lineTo(lassoPoints[i].x, lassoPoints[i].y);
            }
            ctx.stroke();
            // Draw vertices
            ctx.fillStyle = 'rgba(255,255,0,1)';
            for (const p of lassoPoints) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
                ctx.fill();
            }
            // Draw closing line (dashed) from last point to first
            if (lassoPoints.length >= 3) {
                ctx.strokeStyle = 'rgba(255,255,0,0.4)';
                ctx.beginPath();
                ctx.moveTo(lassoPoints[lassoPoints.length - 1].x, lassoPoints[lassoPoints.length - 1].y);
                ctx.lineTo(lassoPoints[0].x, lassoPoints[0].y);
                ctx.stroke();
            }
            ctx.restore();
        }

        function hideLassoPreview() {
            _doRenderRegionOverlay();
        }

        function undoLassoPoint() {
            if (lassoPoints.length > 0) {
                lassoPoints.pop();
                drawLassoPreview();
                showToast(`Lasso: ${lassoPoints.length} points (right-click to undo last)`);
            }
        }

        // Expose for Escape key: cancel active lasso (used by cancelCanvasOperation in 2-state-zones)
        window.cancelLasso = function () {
            if (!lassoActive && lassoPoints.length === 0 && !lassoFreehandDrawing) return false;
            lassoActive = false;
            lassoPoints = [];
            lassoFreehandDrawing = false;
            lassoMouseDownPos = null;
            hideLassoPreview();
            return true;
        };
        window.hideRectPreview = hideRectPreview;
        // Expose so tool buttons (Pick, Wand, All, Edge, Draw, Spatial, etc.) and keyboard shortcuts work
        window.setCanvasMode = setCanvasMode;
        // Expose for Photoshop round-trip: Import from Photoshop loads paint from URL
        window.loadPaintImageFromPath = loadPaintImageFromPath;

        function loadPaintImage(input) {
            const file = input.files[0];
            if (!file) return;
            const fileName = file.name;

            if (fileName.toLowerCase().endsWith('.tga')) {
                // TGA: decode with our custom decoder
                const reader = new FileReader();
                reader.onload = function (e) {
                    try {
                        const tga = decodeTGA(e.target.result);
                        loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);
                    } catch (err) {
                        showToast(`TGA decode error: ${err.message}`, true);
                    }
                };
                reader.readAsArrayBuffer(file);
            } else {
                // PNG/JPG/BMP: browser-native decode
                const reader = new FileReader();
                reader.onload = function (e) {
                    const img = new Image();
                    img.onload = function () {
                        const canvas = document.getElementById('paintCanvas');
                        const ctx = canvas.getContext('2d');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        ctx.drawImage(img, 0, 0);
                        paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                        // Also size region canvas
                        const regionCanvas = document.getElementById('regionCanvas');
                        regionCanvas.width = img.width;
                        regionCanvas.height = img.height;

                        // Show/hide elements for new 3-column layout
                        const emptyBig = document.getElementById('paintPreviewEmptyBig');
                        if (emptyBig) emptyBig.style.display = 'none';
                        const empty2 = document.getElementById('paintPreviewEmpty2');
                        if (empty2) empty2.style.display = 'none';
                        document.getElementById('paintPreviewLoaded').style.display = 'flex';
                        /* advancedToolbar moved to vertical toolbar */
                        const edInfo4 = document.getElementById('eyedropperInfo'); if (edInfo4) edInfo4.style.display = 'block';
                        document.getElementById('paintDimensions').textContent = `${img.width}x${img.height}`;
                        document.getElementById('paintPreviewStatus').textContent = `(${img.width}x${img.height})`;
                        const canvasInner = document.getElementById('canvasInner');
                        if (canvasInner) canvasInner.style.display = 'block';
                        const zoomCtrl = document.getElementById('zoomControls');
                        if (zoomCtrl) zoomCtrl.style.display = 'flex';

                        setupCanvasHandlers(canvas);
                        canvasZoom('fit');
                        // Auto-enable split view when paint is loaded
                        if (!splitViewActive) {
                            setTimeout(() => toggleSplitView(), 200);
                        }
                        showToast('Paint loaded! Hover to see colors, click to grab one.');
                    };
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        }

        // SHOKK / programmatic load: from URL (e.g. /api/shokk/extracted/xxx/paint.tga) or from File
        // Returns a Promise so callers can await it
        function loadPaintImageFromPath(urlOrPath) {
            const url = (urlOrPath && (urlOrPath.startsWith('/') || urlOrPath.startsWith('http') || urlOrPath.startsWith('file://'))) ? urlOrPath : null;
            if (!url) return Promise.reject(new Error('Invalid paint URL'));
            return fetch(url).then(function (res) { if (!res.ok) throw new Error(res.statusText); return res.blob(); })
                .then(function (blob) {
                    const name = (url.split('/').pop() || 'paint.tga').split('?')[0] || 'paint.tga';
                    const file = new File([blob], name, { type: blob.type || 'image/tga' });
                    loadPaintImageFromFile(file);
                })
                .catch(function (e) {
                    console.error('[SHOKK] loadPaintImageFromPath failed:', e);
                    if (typeof showToast === 'function') showToast('Failed to load paint from SHOKK: ' + e.message, 4000, true);
                    throw e; // Re-throw so callers' await/catch can handle it
                });
        }

        function loadPaintImageFromFile(file) {
            if (!file || !file.name) return;
            const fileName = file.name;
            if (fileName.toLowerCase().endsWith('.tga')) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    try {
                        const tga = decodeTGA(e.target.result);
                        loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);
                    } catch (err) {
                        if (typeof showToast === 'function') showToast('TGA decode error: ' + err.message, 4000, true);
                    }
                };
                reader.readAsArrayBuffer(file);
            } else {
                const reader = new FileReader();
                reader.onload = function (e) {
                    const img = new Image();
                    img.onload = function () {
                        const canvas = document.getElementById('paintCanvas');
                        const ctx = canvas.getContext('2d');
                        canvas.width = img.width;
                        canvas.height = img.height;
                        ctx.drawImage(img, 0, 0);
                        paintImageData = ctx.getImageData(0, 0, img.width, img.height);
                        const regionCanvas = document.getElementById('regionCanvas');
                        if (regionCanvas) { regionCanvas.width = img.width; regionCanvas.height = img.height; }
                        const emptyBig = document.getElementById('paintPreviewEmptyBig'); if (emptyBig) emptyBig.style.display = 'none';
                        const empty2 = document.getElementById('paintPreviewEmpty2'); if (empty2) empty2.style.display = 'none';
                        document.getElementById('paintPreviewLoaded').style.display = 'flex';
                        /* advancedToolbar moved to vertical toolbar */
                        const edInfo = document.getElementById('eyedropperInfo'); if (edInfo) edInfo.style.display = 'block';
                        document.getElementById('paintDimensions').textContent = img.width + 'x' + img.height;
                        document.getElementById('paintPreviewStatus').textContent = '(' + img.width + 'x' + img.height + ')';
                        const canvasInner = document.getElementById('canvasInner'); if (canvasInner) canvasInner.style.display = 'block';
                        const zoomCtrl = document.getElementById('zoomControls'); if (zoomCtrl) zoomCtrl.style.display = 'flex';
                        setupCanvasHandlers(canvas);
                        canvasZoom('fit');
                        // Auto-enable split view when paint is loaded
                        if (!splitViewActive) {
                            setTimeout(() => toggleSplitView(), 200);
                        }
                        if (typeof showToast === 'function') showToast('Paint loaded!');
                    };
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        }
        window.loadPaintImageFromFile = loadPaintImageFromFile;

        function updateEyedropperZoneSelect() {
            const sel = document.getElementById('eyedropperZoneSelect');
            if (!sel) return;
            sel.innerHTML = zones.map((z, i) =>
                `<option value="${i}"${i === selectedZoneIndex ? ' selected' : ''}>Zone ${i + 1}: ${escapeHtml(z.name)}</option>`
            ).join('');

            // Populate base + pattern dropdowns if not yet done
            const baseSel = document.getElementById('eyedropperBaseSelect');
            if (baseSel && baseSel.options.length <= 1) {
                let html = '<option value="">- Base -</option>';
                BASES.forEach(b => { html += `<option value="${b.id}">${b.name}</option>`; });
                html += '<optgroup label="Special">';
                MONOLITHICS.forEach(m => { html += `<option value="mono:${m.id}">${m.name}</option>`; });
                html += '</optgroup>';
                baseSel.innerHTML = html;
            }
            const patSel = document.getElementById('eyedropperPatternSelect');
            if (patSel && patSel.options.length <= 1) {
                let html = '';
                PATTERNS.forEach(p => { html += `<option value="${p.id}">${p.name}</option>`; });
                patSel.innerHTML = html;
            }

            // ALWAYS sync dropdowns with the selected zone's current values
            syncEyedropperPanel();
        }

        function syncEyedropperPanel() {
            // Sync the bottom-bar dropdowns with the currently selected zone
            const sel = document.getElementById('eyedropperZoneSelect');
            const baseSel = document.getElementById('eyedropperBaseSelect');
            const patSel = document.getElementById('eyedropperPatternSelect');
            const intSel = document.getElementById('eyedropperIntensitySelect');

            if (sel) sel.value = String(selectedZoneIndex);

            const zone = zones[selectedZoneIndex];
            if (!zone) return;

            // Sync base dropdown (monolithics get "mono:" prefix)
            if (baseSel) {
                if (zone.finish && MONOLITHICS.find(m => m.id === zone.finish)) {
                    baseSel.value = 'mono:' + zone.finish;
                } else {
                    baseSel.value = zone.base || '';
                }
            }

            // Sync pattern dropdown (now works for BOTH bases AND monolithics - patterns overlay on top!)
            if (patSel) {
                patSel.value = zone.pattern || 'none';
                patSel.disabled = false;  // Patterns can now overlay on monolithics too
            }

            // Sync intensity dropdown
            if (intSel) intSel.value = zone.intensity || '100';
        }

        function onEyedropperZoneChange(val) {
            // When user picks a different zone in the RIGHT panel dropdown
            const newIndex = parseInt(val);
            if (newIndex >= 0 && newIndex < zones.length) {
                selectedZoneIndex = newIndex;
                renderZones();
                syncEyedropperPanel();
                if (canvasMode !== 'eyedropper') {
                    updateDrawZoneIndicator();
                }
            }
        }

        function onEyedropperBaseChange(val) {
            // When user picks a base (or monolithic) in the bottom bar → apply to selected zone
            const zone = zones[selectedZoneIndex];
            if (!zone || !val) return;
            pushZoneUndo();
            if (val.startsWith('mono:')) {
                const monoId = val.replace('mono:', '');
                zone.finish = monoId;
                zone.base = null;
                zone.pattern = null;
                showToast(`${zone.name}: ${MONOLITHICS.find(m => m.id === monoId)?.name || monoId}`);
            } else {
                zone.base = val;
                zone.finish = null;
                if (!zone.pattern) zone.pattern = 'none';
                showToast(`${zone.name}: base set to ${BASES.find(b => b.id === val)?.name || val}`);
            }
            renderZones();
            syncEyedropperPanel();
        }

        function onEyedropperPatternChange(val) {
            const zone = zones[selectedZoneIndex];
            if (!zone) return;
            pushZoneUndo();
            zone.pattern = val || 'none';
            if (!zone.base) zone.base = 'gloss'; // Need a base for pattern to work
            zone.finish = null;
            renderZones();
            syncEyedropperPanel();
            const patName = PATTERNS.find(p => p.id === val)?.name || val;
            showToast(`${zone.name}: pattern set to ${patName}`);
        }

        function onEyedropperIntensityChange(val) {
            // When user picks intensity in the RIGHT panel → immediately apply to selected zone on LEFT
            const zone = zones[selectedZoneIndex];
            if (zone && val) {
                pushZoneUndo();
                zone.intensity = val;
                renderZones();
                showToast(`${zone.name}: intensity set to ${val}`);
            }
        }

        function quickAssignAll() {
            // Assign color + finish + intensity to the selected zone all at once from the right panel
            pushZoneUndo();
            const sel = document.getElementById('eyedropperZoneSelect');
            const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;
            if (targetIndex < 0 || targetIndex >= zones.length) return;

            const zone = zones[targetIndex];
            const finishSel = document.getElementById('eyedropperFinishSelect');
            const intSel = document.getElementById('eyedropperIntensitySelect');

            // Set color if eyedropper has one
            if (lastEyedropperColor) {
                const { r, g, b } = lastEyedropperColor;
                const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
                const tol = zone.pickerTolerance || 40;
                zone.color = { color_rgb: [r, g, b], tolerance: tol };
                zone.colorMode = 'picker';
                zone.pickerColor = hex;
                zone.colors = [];
            }

            // Set base + pattern from bottom bar dropdowns
            const baseSel = document.getElementById('eyedropperBaseSelect');
            const patSel = document.getElementById('eyedropperPatternSelect');
            if (baseSel && baseSel.value) {
                if (baseSel.value.startsWith('mono:')) {
                    zone.finish = baseSel.value.replace('mono:', '');
                    zone.base = null;
                    zone.pattern = null;
                } else {
                    zone.base = baseSel.value;
                    zone.finish = null;
                    zone.pattern = (patSel && patSel.value) ? patSel.value : 'none';
                }
            }

            // Set intensity
            if (intSel && intSel.value) {
                zone.intensity = intSel.value;
            }

            selectedZoneIndex = targetIndex;
            renderZones();

            const parts = [];
            if (lastEyedropperColor) parts.push(zone.pickerColor?.toUpperCase());
            if (zone.base) {
                parts.push(BASES.find(b => b.id === zone.base)?.name || zone.base);
                if (zone.pattern && zone.pattern !== 'none') parts.push(PATTERNS.find(p => p.id === zone.pattern)?.name || zone.pattern);
            } else if (zone.finish) {
                parts.push(MONOLITHICS.find(m => m.id === zone.finish)?.name || FINISHES.find(f => f.id === zone.finish)?.name || zone.finish);
            }
            if (zone.intensity) parts.push(zone.intensity);
            showToast(`${zone.name}: ${parts.join(' + ')}`);
        }

        function useEyedropperColor() {
            // "Set as Only" - replaces the zone with a single color (clears multi-color stack)
            if (!lastEyedropperColor) return;
            pushZoneUndo();
            const { r, g, b } = lastEyedropperColor;

            const sel = document.getElementById('eyedropperZoneSelect');
            const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;

            if (targetIndex >= 0 && targetIndex < zones.length) {
                const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
                const tol = zones[targetIndex].pickerTolerance || 40;
                zones[targetIndex].color = { color_rgb: [r, g, b], tolerance: tol };
                zones[targetIndex].colorMode = 'picker';
                zones[targetIndex].pickerColor = hex;
                zones[targetIndex].colors = []; // Clear multi-color stack
                selectedZoneIndex = targetIndex;
                renderZones();
                triggerPreviewRender();
                showToast(`Zone ${targetIndex + 1} (${zones[targetIndex].name}): set to ${hex.toUpperCase()} (single color)`);
            }
        }

        function addEyedropperColorToZone() {
            // "+ Add to Zone" - stacks this color into the zone's multi-color array
            if (!lastEyedropperColor) { showToast('Click a color on the paint first!', true); return; }
            pushZoneUndo();
            const { r, g, b } = lastEyedropperColor;

            const sel = document.getElementById('eyedropperZoneSelect');
            const targetIndex = sel ? parseInt(sel.value) : selectedZoneIndex;

            if (targetIndex >= 0 && targetIndex < zones.length) {
                const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
                const tol = zones[targetIndex].pickerTolerance || 40;
                const zone = zones[targetIndex];

                // If zone was in single-color picker mode, migrate that color to the stack first
                if (zone.colorMode === 'picker' && zone.colors.length === 0 && zone.pickerColor) {
                    const existR = parseInt(zone.pickerColor.substr(1, 2), 16);
                    const existG = parseInt(zone.pickerColor.substr(3, 2), 16);
                    const existB = parseInt(zone.pickerColor.substr(5, 2), 16);
                    zone.colors.push({ color_rgb: [existR, existG, existB], tolerance: zone.pickerTolerance || 40, hex: zone.pickerColor });
                }

                // Check for duplicate
                if (zone.colors.some(c => c.hex && c.hex.toUpperCase() === hex.toUpperCase())) {
                    showToast('That color is already in this zone', true);
                    return;
                }

                zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
                zone.colorMode = 'multi';
                zone.color = zone.colors;
                zone.pickerColor = hex; // Update picker display to last-added
                selectedZoneIndex = targetIndex;
                renderZones();
                triggerPreviewRender();
                showToast(`Added ${hex.toUpperCase()} to ${zone.name} (${zone.colors.length} colors stacked)`);
            }
        }

        // ===== USE REGION - commit drawn region (rect/lasso/brush/wand) into the selected zone =====
        // Uses the zone selected in the LEFT panel (same zone the Rect/Lasso/Brush tools draw into).
        // If that zone has no region, uses the first zone that has a drawn region (e.g. after changing selection).
        function useRegionForZone() {
            let targetIndex = selectedZoneIndex;
            if (targetIndex < 0 || targetIndex >= zones.length) targetIndex = 0;
            let zone = zones[targetIndex];
            if (!zone || !zone.regionMask || !zone.regionMask.some(v => v > 0)) {
                const withRegion = zones.findIndex(z => z.regionMask && z.regionMask.some(v => v > 0));
                if (withRegion >= 0) {
                    targetIndex = withRegion;
                    zone = zones[targetIndex];
                    selectedZoneIndex = targetIndex;
                    if (typeof renderZones === 'function') renderZones();
                    if (typeof syncEyedropperPanel === 'function') syncEyedropperPanel();
                } else {
                    showToast('Draw a region first: select a zone on the left, then use Rect, Lasso, Brush, or Wand on the canvas. Then click Use Region.', true);
                    return;
                }
            }
            pushZoneUndo();
            const pixelCount = zone.regionMask.reduce((sum, v) => sum + (v > 0 ? 1 : 0), 0);
            const canvas = document.getElementById('paintCanvas');
            const totalPixels = canvas ? canvas.width * canvas.height : 1;
            const pct = ((pixelCount / totalPixels) * 100).toFixed(1);
            zone.useRegion = true;
            renderZones();
            triggerPreviewRender();
            updateRegionStatus();
            // Keep bottom bar dropdown in sync so +Add/Set apply to same zone
            const sel = document.getElementById('eyedropperZoneSelect');
            if (sel) { sel.value = String(selectedZoneIndex); }
            showToast(`🎯 Region applied to ${zone.name}: ${pixelCount.toLocaleString()} pixels (${pct}%) - set base/finish in the zone panel and Render.`);
        }

        // Nudge the current zone's drawn region by (dx, dy) pixels. Use Alt+Arrow (e.g. in 6-ui-boot).
        function nudgeRegionSelection(dx, dy) {
            const canvas = document.getElementById('paintCanvas');
            if (!canvas || typeof zones === 'undefined' || selectedZoneIndex < 0 || selectedZoneIndex >= zones.length) return false;
            const zone = zones[selectedZoneIndex];
            if (!zone || !zone.regionMask || !zone.regionMask.some(v => v > 0)) return false;
            const w = canvas.width, h = canvas.height;
            const newMask = new Uint8Array(w * h);
            for (let y = 0; y < h; y++) {
                for (let x = 0; x < w; x++) {
                    const idx = y * w + x;
                    if (zone.regionMask[idx] > 0) {
                        const nx = x + dx, ny = y + dy;
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h) newMask[ny * w + nx] = 1;
                    }
                }
            }
            zone.regionMask = newMask;
            if (typeof renderRegionOverlay === 'function') renderRegionOverlay();
            if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            if (typeof renderZones === 'function') renderZones();
            return true;
        }

        // Update the region status indicator in the bottom bar
        function updateRegionStatus() {
            const statusEl = document.getElementById('regionStatus');
            if (!statusEl) return;
            const zone = zones[selectedZoneIndex];
            if (zone && zone.regionMask && zone.regionMask.some(v => v > 0)) {
                const pixelCount = zone.regionMask.reduce((sum, v) => sum + (v > 0 ? 1 : 0), 0);
                statusEl.textContent = `Region: ${pixelCount.toLocaleString()}px ✓`;
                statusEl.style.color = '#cc88ff';
            } else {
                statusEl.textContent = '';
            }
        }

        // ===== LIVE PREVIEW SPLIT VIEW =====
        let splitViewActive = false;
        let previewDebounceTimer = null;
        let previewAbortController = null;
        let previewVersion = 0;           // Monotonic counter for staleness detection
        let previewIsRendering = false;
        let lastPreviewZoneHash = '';

        function toggleSplitView() {
            splitViewActive = !splitViewActive;
            const splitBtn = document.getElementById('btnSplitView');
            const previewPane = document.getElementById('splitPreview');
            const sourceLabel = document.getElementById('sourcePaneLabel');

            if (splitBtn) splitBtn.classList.toggle('split-active', splitViewActive);
            if (previewPane) previewPane.style.display = splitViewActive ? 'flex' : 'none';
            if (sourceLabel) sourceLabel.style.display = splitViewActive ? '' : 'none';

            // Re-fit source canvas to the new (narrower or wider) space
            setTimeout(() => canvasZoom('fit'), 50);

            // Trigger initial preview if zones are configured
            if (splitViewActive) {
                triggerPreviewRender();
            }
        }

        // ===== PREVIEW LIGHTBOX =====
        let lightboxMode = 'paint';

        function openPreviewLightbox(mode) {
            const lb = document.getElementById('previewLightbox');
            if (!lb) return;
            lb.style.display = 'block';
            showLightbox(mode || 'paint');
            document.addEventListener('keydown', lightboxKeyHandler);
        }

        function showLightbox(mode, channel) {
            lightboxMode = mode || 'paint';
            const img = document.getElementById('lightboxImg');
            const paintBtn = document.getElementById('lightboxPaintBtn');
            const specBtn = document.getElementById('lightboxSpecBtn');
            const chBtns = ['lightboxChAll','lightboxChR','lightboxChG','lightboxChB'];

            if (lightboxMode === 'paint') {
                const src = document.getElementById('livePreviewImg');
                if (src) img.src = src.src;
                paintBtn.style.borderColor = '#E87A20';
                paintBtn.style.color = '#E87A20';
                specBtn.style.borderColor = '#333';
                specBtn.style.color = '#00C8C8';
                chBtns.forEach(id => { const b = document.getElementById(id); if (b) b.style.display = 'none'; });
            } else {
                const src = document.getElementById('livePreviewSpecImg');
                if (src) img.src = src.src;
                specBtn.style.borderColor = '#00C8C8';
                specBtn.style.color = '#00C8C8';
                paintBtn.style.borderColor = '#333';
                paintBtn.style.color = '#E87A20';
                chBtns.forEach(id => { const b = document.getElementById(id); if (b) b.style.display = ''; });
            }
        }

        function closePreviewLightbox() {
            const lb = document.getElementById('previewLightbox');
            if (lb) lb.style.display = 'none';
            document.removeEventListener('keydown', lightboxKeyHandler);
        }

        function lightboxKeyHandler(e) {
            if (e.key === 'Escape') closePreviewLightbox();
            if (e.key === 'p' || e.key === 'P') showLightbox('paint');
            if (e.key === 's' || e.key === 'S') showLightbox('spec');
        }

        function getZoneConfigHash() {
            // Hash ALL rendering-relevant zone fields to detect actual changes
            // Must match every field sent to server in doPreviewRender / doRender
            const muteKey = zones.map(z => z.muted ? '1' : '0').join('');
            const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
            if (validZones.length === 0) return muteKey || '';
            const hashData = validZones.map(z => ({
                // Core finish
                base: z.base, pattern: z.pattern, finish: z.finish,
                scale: z.scale, rotation: z.rotation,
                baseRotation: z.baseRotation, baseScale: z.baseScale,
                baseStrength: z.baseStrength, baseSpecStrength: z.baseSpecStrength,
                baseOffsetX: z.baseOffsetX, baseOffsetY: z.baseOffsetY,
                baseFlipH: z.baseFlipH, baseFlipV: z.baseFlipV,
                // Pattern
                patternOpacity: z.patternOpacity, patternStack: z.patternStack,
                patternSpecMult: z.patternSpecMult,
                patternOffsetX: z.patternOffsetX, patternOffsetY: z.patternOffsetY,
                patternFlipH: z.patternFlipH, patternFlipV: z.patternFlipV,
                // Intensity & custom
                intensity: z.intensity, patternIntensity: z.patternIntensity,
                customSpec: z.customSpec, customPaint: z.customPaint, customBright: z.customBright,
                // Color
                color: z.color, colorMode: z.colorMode, colors: z.colors,
                pickerColor: z.pickerColor, pickerTolerance: z.pickerTolerance,
                // Base color system (FROM SPECIAL, solid color, etc.)
                baseColorMode: z.baseColorMode, baseColor: z.baseColor,
                baseColorSource: z.baseColorSource, baseColorStrength: z.baseColorStrength,
                baseHueOffset: z.baseHueOffset, baseSaturationAdjust: z.baseSaturationAdjust,
                baseBrightnessAdjust: z.baseBrightnessAdjust,
                // Paint reactive
                usePaintReactive: z.usePaintReactive, paintReactiveColor: z.paintReactiveColor,
                // Wear & CC
                wear: z.wear, ccQuality: z.ccQuality,
                // Blend
                blendBase: z.blendBase, blendDir: z.blendDir, blendAmount: z.blendAmount,
                // 2nd base overlay
                secondBase: z.secondBase, secondBaseStrength: z.secondBaseStrength,
                secondBaseSpecStrength: z.secondBaseSpecStrength,
                secondBaseBlendMode: z.secondBaseBlendMode, secondBaseNoiseScale: z.secondBaseNoiseScale,
                secondBaseColor: z.secondBaseColor, secondBaseColorSource: z.secondBaseColorSource,
                secondBaseScale: z.secondBaseScale, secondBasePattern: z.secondBasePattern,
                secondBasePatternOpacity: z.secondBasePatternOpacity,
                secondBasePatternScale: z.secondBasePatternScale,
                secondBasePatternRotation: z.secondBasePatternRotation,
                secondBasePatternStrength: z.secondBasePatternStrength,
                secondBasePatternInvert: z.secondBasePatternInvert,
                secondBasePatternHarden: z.secondBasePatternHarden,
                secondBasePatternOffsetX: z.secondBasePatternOffsetX,
                secondBasePatternOffsetY: z.secondBasePatternOffsetY,
                // 3rd base overlay
                thirdBase: z.thirdBase, thirdBaseStrength: z.thirdBaseStrength,
                thirdBaseSpecStrength: z.thirdBaseSpecStrength,
                thirdBaseBlendMode: z.thirdBaseBlendMode, thirdBaseNoiseScale: z.thirdBaseNoiseScale,
                thirdBaseColor: z.thirdBaseColor, thirdBaseColorSource: z.thirdBaseColorSource,
                thirdBaseScale: z.thirdBaseScale, thirdBasePattern: z.thirdBasePattern,
                thirdBasePatternOpacity: z.thirdBasePatternOpacity,
                thirdBasePatternScale: z.thirdBasePatternScale,
                thirdBasePatternRotation: z.thirdBasePatternRotation,
                thirdBasePatternStrength: z.thirdBasePatternStrength,
                thirdBasePatternInvert: z.thirdBasePatternInvert,
                thirdBasePatternHarden: z.thirdBasePatternHarden,
                thirdBasePatternOffsetX: z.thirdBasePatternOffsetX,
                thirdBasePatternOffsetY: z.thirdBasePatternOffsetY,
                // 4th base overlay
                fourthBase: z.fourthBase, fourthBaseStrength: z.fourthBaseStrength,
                fourthBaseSpecStrength: z.fourthBaseSpecStrength,
                fourthBaseBlendMode: z.fourthBaseBlendMode, fourthBaseNoiseScale: z.fourthBaseNoiseScale,
                fourthBaseColor: z.fourthBaseColor, fourthBaseColorSource: z.fourthBaseColorSource,
                fourthBaseScale: z.fourthBaseScale, fourthBasePattern: z.fourthBasePattern,
                fourthBasePatternOpacity: z.fourthBasePatternOpacity,
                fourthBasePatternScale: z.fourthBasePatternScale,
                fourthBasePatternRotation: z.fourthBasePatternRotation,
                fourthBasePatternStrength: z.fourthBasePatternStrength,
                fourthBasePatternInvert: z.fourthBasePatternInvert,
                fourthBasePatternHarden: z.fourthBasePatternHarden,
                fourthBasePatternOffsetX: z.fourthBasePatternOffsetX,
                fourthBasePatternOffsetY: z.fourthBasePatternOffsetY,
                // 5th base overlay
                fifthBase: z.fifthBase, fifthBaseStrength: z.fifthBaseStrength,
                fifthBaseSpecStrength: z.fifthBaseSpecStrength,
                fifthBaseBlendMode: z.fifthBaseBlendMode, fifthBaseNoiseScale: z.fifthBaseNoiseScale,
                fifthBaseColor: z.fifthBaseColor, fifthBaseColorSource: z.fifthBaseColorSource,
                fifthBaseScale: z.fifthBaseScale, fifthBasePattern: z.fifthBasePattern,
                fifthBasePatternOpacity: z.fifthBasePatternOpacity,
                fifthBasePatternScale: z.fifthBasePatternScale,
                fifthBasePatternRotation: z.fifthBasePatternRotation,
                fifthBasePatternStrength: z.fifthBasePatternStrength,
                fifthBasePatternInvert: z.fifthBasePatternInvert,
                fifthBasePatternHarden: z.fifthBasePatternHarden,
                fifthBasePatternOffsetX: z.fifthBasePatternOffsetX,
                fifthBasePatternOffsetY: z.fifthBasePatternOffsetY,
                // Spec pattern overlays
                specPatternStack: z.specPatternStack,
                overlaySpecPatternStack: z.overlaySpecPatternStack,
                // Region mask: track length + sum for change detection
                rmLen: z.regionMask ? z.regionMask.length : 0,
                rmSum: z.regionMask ? z.regionMask.reduce((a, b) => a + b, 0) : 0,
            }));
            return muteKey + JSON.stringify(hashData);
        }

        function triggerPreviewRender() {
            if (!splitViewActive) return;

            const hash = getZoneConfigHash();
            if (hash === lastPreviewZoneHash) return;  // Nothing actually changed
            if (hash === '') {
                // No valid zones - show empty state
                updatePreviewStatus('', '');
                document.getElementById('previewPaintPane').style.display = 'none';
                document.getElementById('previewSpecPane').style.display = 'none';
                document.getElementById('previewSpecPane').classList.remove('spec-expanded');
                specExpanded = false;
                document.getElementById('previewSpinner').style.display = 'none';
                document.getElementById('previewEmpty').style.display = '';
                return;
            }

            // Mark as stale
            updatePreviewStatus('stale', 'Changed');

            // Debounce: clear previous timer, set new 600ms timer
            if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
            previewDebounceTimer = setTimeout(() => {
                doPreviewRender(hash);
            }, 600);
        }

        async function doPreviewRender(zoneHash) {
            const paintFile = document.getElementById('paintFile').value.trim();
            if (!paintFile) return;
            if (!ShokkerAPI.online) return;

            // Abort any in-flight request
            if (previewAbortController) {
                previewAbortController.abort();
            }
            previewAbortController = new AbortController();

            // Increment version to detect stale responses
            previewVersion++;
            const thisVersion = previewVersion;

            // Show spinner
            previewIsRendering = true;
            updatePreviewStatus('rendering', 'Rendering...');
            document.getElementById('previewEmpty').style.display = 'none';
            document.getElementById('previewSpinner').style.display = 'flex';

            // Build server zones (use same builder as full render so live preview paint matches final paint file)
            const serverZones = (typeof window.buildServerZonesForRender === 'function')
                ? window.buildServerZonesForRender(zones)
                : (function () {
                    const validZones = zones.filter(z => !z.muted && (z.base || z.finish) && (z.color !== null || z.colorMode === 'multi' || (z.regionMask && z.regionMask.some(v => v > 0))));
                    return validZones.map(z => {
                        const zoneObj = { name: z.name, color: formatColorForServer(z.color, z), intensity: z.intensity };
                        if (z.customSpec != null) zoneObj.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
                        if ((z.base && z.pattern && z.pattern !== 'none') || (z.finish && z.pattern && z.pattern !== 'none')) zoneObj.pattern_intensity = String(z.patternIntensity ?? '100');
                        if (z.base) {
                            zoneObj.base = z.base; zoneObj.pattern = z.pattern || 'none';
                            if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale;
                            if (z.rotation && z.rotation !== 0) zoneObj.rotation = z.rotation;
                            if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100;
                            if (z.patternStack && z.patternStack.length > 0) {
                                const stack = z.patternStack.filter(l => l.id && l.id !== 'none');
                                if (stack.length > 0) zoneObj.pattern_stack = stack.map(l => ({ id: l.id, opacity: (l.opacity != null ? l.opacity : 100) / 100, scale: l.scale || 1.0, rotation: l.rotation || 0 }));
                            }
                        } else if (z.finish) {
                            zoneObj.finish = z.finish;
                            const _finishRot = z.baseRotation || z.rotation || 0;
                            if (_finishRot && _finishRot !== 0) zoneObj.rotation = _finishRot;
                            const _fMono = typeof MONOLITHICS !== 'undefined' && MONOLITHICS.find(m => m.id === z.finish);
                            let fc = _fMono ? { c1: _fMono.swatch || null, c2: _fMono.swatch2 || null, c3: _fMono.swatch3 || null, ghost: _fMono.ghostPattern || null } : null;
                            if (!fc && typeof getFinishColorsForId === 'function' && /^(grad_|gradm_|grad3_|ghostg_|mc_)/.test(z.finish)) fc = getFinishColorsForId(z.finish);
                            if (fc) zoneObj.finish_colors = fc;
                            if (z.pattern && z.pattern !== 'none') { zoneObj.pattern = z.pattern; if (z.scale && z.scale !== 1.0) zoneObj.scale = z.scale; if ((z.patternOpacity ?? 100) !== 100) zoneObj.pattern_opacity = (z.patternOpacity ?? 100) / 100; }
                        }
                        if (z.baseScale && z.baseScale !== 1.0) zoneObj.base_scale = z.baseScale;
                        if (z.baseStrength != null && z.baseStrength !== 1) zoneObj.base_strength = Number(z.baseStrength);
                        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) zoneObj.base_spec_strength = Number(z.baseSpecStrength);
                        if (z.base || z.finish) {
                            const _bMode = (z.baseColorMode || 'source');
                            zoneObj.base_color_mode = _bMode;
                            zoneObj.base_color_strength = Math.max(0, Math.min(1, Number(z.baseColorStrength ?? 1)));
                            if (z.baseHueOffset) zoneObj.base_hue_offset = Number(z.baseHueOffset);
                            if (z.baseSaturationAdjust) zoneObj.base_saturation_adjust = Number(z.baseSaturationAdjust);
                            if (z.baseBrightnessAdjust) zoneObj.base_brightness_adjust = Number(z.baseBrightnessAdjust);
                            if (_bMode === 'solid' && z.baseColor) {
                                const _bHex = (z.baseColor || '#ffffff').toString();
                                const hex = _bHex.length >= 7 ? _bHex : '#ffffff';
                                zoneObj.base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            } else if (_bMode === 'special' && z.baseColorSource && z.baseColorSource !== 'undefined') {
                                zoneObj.base_color_source = z.baseColorSource;
                            }
                        }
                        if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) {
                            if (z.patternSpecMult != null) zoneObj.pattern_spec_mult = Number(z.patternSpecMult ?? 1);
                            zoneObj.pattern_offset_x = Math.max(0, Math.min(1, Number(z.patternOffsetX ?? 0.5)));
                            zoneObj.pattern_offset_y = Math.max(0, Math.min(1, Number(z.patternOffsetY ?? 0.5)));
                            zoneObj.pattern_flip_h = !!z.patternFlipH;
                            zoneObj.pattern_flip_v = !!z.patternFlipV;
                        }
                        if (z.base || z.finish) {
                            zoneObj.base_offset_x = Math.max(0, Math.min(1, Number(z.baseOffsetX ?? 0.5)));
                            zoneObj.base_offset_y = Math.max(0, Math.min(1, Number(z.baseOffsetY ?? 0.5)));
                            zoneObj.base_rotation = Number(z.baseRotation ?? 0);
                            zoneObj.base_flip_h = !!z.baseFlipH;
                            zoneObj.base_flip_v = !!z.baseFlipV;
                        }
                        if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;
                        if ((z.ccQuality ?? 100) !== 100) zoneObj.cc_quality = (z.ccQuality ?? 100) / 100;
                        if (z.blendBase && z.blendBase !== 'undefined' && z.blendBase !== 'none') {
                            zoneObj.blend_base = z.blendBase;
                            zoneObj.blend_dir = z.blendDir || 'horizontal';
                            zoneObj.blend_amount = (z.blendAmount ?? 50) / 100;
                        }
                        if (z.usePaintReactive && z.paintReactiveColor) { const _pc = z.paintReactiveColor; zoneObj.paint_color = [parseInt(_pc.slice(1, 3), 16) / 255, parseInt(_pc.slice(3, 5), 16) / 255, parseInt(_pc.slice(5, 7), 16) / 255]; }
                        if ((z.secondBase || z.secondBaseColorSource) && (z.secondBaseStrength || 0) > 0) {
                            const _sbColor = z.secondBaseColor || '#ffffff';
                            if (z.secondBase && z.secondBase !== 'undefined') zoneObj.second_base = z.secondBase;
                            zoneObj.second_base_color = [parseInt(_sbColor.slice(1, 3), 16) / 255, parseInt(_sbColor.slice(3, 5), 16) / 255, parseInt(_sbColor.slice(5, 7), 16) / 255];
                            zoneObj.second_base_strength = z.secondBaseStrength || 0;
                            zoneObj.second_base_spec_strength = z.secondBaseSpecStrength ?? 1;
                            if (z.secondBaseColorSource && z.secondBaseColorSource !== 'undefined') zoneObj.second_base_color_source = z.secondBaseColorSource;
                            zoneObj.second_base_blend_mode = z.secondBaseBlendMode || 'noise';
                            zoneObj.second_base_noise_scale = Number(z.secondBaseNoiseScale ?? z.secondBaseFractalScale ?? 24);
                            zoneObj.second_base_scale = Math.max(0.01, Math.min(5, Number(z.secondBaseScale) || 1));
                            if (z.secondBasePattern) zoneObj.second_base_pattern = z.secondBasePattern;
                            if (z.secondBasePatternOpacity != null) zoneObj.second_base_pattern_opacity = (z.secondBasePatternOpacity ?? 100) / 100;
                            if (z.secondBasePatternScale != null) zoneObj.second_base_pattern_scale = Number(z.secondBasePatternScale) || 1;
                            if (z.secondBasePatternRotation != null) zoneObj.second_base_pattern_rotation = Number(z.secondBasePatternRotation) || 0;
                            if (z.secondBasePatternStrength != null) zoneObj.second_base_pattern_strength = Number(z.secondBasePatternStrength) ?? 1;
                            if (z.secondBasePatternInvert != null) zoneObj.second_base_pattern_invert = !!z.secondBasePatternInvert;
                            if (z.secondBasePatternHarden != null) zoneObj.second_base_pattern_harden = !!z.secondBasePatternHarden;
                            if (z.secondBasePatternOffsetX != null) zoneObj.second_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetX)));
                            if (z.secondBasePatternOffsetY != null) zoneObj.second_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.secondBasePatternOffsetY)));
                        }
                        if ((z.thirdBase || z.thirdBaseColorSource) && (z.thirdBaseStrength || 0) > 0) {
                            const _tbColor = (z.thirdBaseColor || '#ffffff').toString();
                            const hex = _tbColor.length >= 7 ? _tbColor : '#ffffff';
                            if (z.thirdBase && z.thirdBase !== 'undefined') zoneObj.third_base = z.thirdBase;
                            zoneObj.third_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            zoneObj.third_base_strength = z.thirdBaseStrength || 0;
                            zoneObj.third_base_spec_strength = z.thirdBaseSpecStrength ?? 1;
                            if (z.thirdBaseColorSource && z.thirdBaseColorSource !== 'undefined') zoneObj.third_base_color_source = z.thirdBaseColorSource;
                            zoneObj.third_base_blend_mode = z.thirdBaseBlendMode || 'noise';
                            zoneObj.third_base_noise_scale = Number(z.thirdBaseNoiseScale ?? z.thirdBaseFractalScale ?? 24);
                            zoneObj.third_base_scale = Math.max(0.01, Math.min(5, Number(z.thirdBaseScale) || 1));
                            if (z.thirdBasePattern) zoneObj.third_base_pattern = z.thirdBasePattern;
                            if (z.thirdBasePatternOpacity != null) zoneObj.third_base_pattern_opacity = (z.thirdBasePatternOpacity ?? 100) / 100;
                            if (z.thirdBasePatternScale != null) zoneObj.third_base_pattern_scale = Number(z.thirdBasePatternScale) || 1;
                            if (z.thirdBasePatternRotation != null) zoneObj.third_base_pattern_rotation = Number(z.thirdBasePatternRotation) || 0;
                            if (z.thirdBasePatternStrength != null) zoneObj.third_base_pattern_strength = Number(z.thirdBasePatternStrength) ?? 1;
                            if (z.thirdBasePatternInvert != null) zoneObj.third_base_pattern_invert = !!z.thirdBasePatternInvert;
                            if (z.thirdBasePatternHarden != null) zoneObj.third_base_pattern_harden = !!z.thirdBasePatternHarden;
                            if (z.thirdBasePatternOffsetX != null) zoneObj.third_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetX ?? 0.5)));
                            if (z.thirdBasePatternOffsetY != null) zoneObj.third_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.thirdBasePatternOffsetY ?? 0.5)));
                        }
                        if ((z.fourthBase || z.fourthBaseColorSource) && (z.fourthBaseStrength || 0) > 0) {
                            const _fbColor = (z.fourthBaseColor || '#ffffff').toString();
                            const hex = _fbColor.length >= 7 ? _fbColor : '#ffffff';
                            if (z.fourthBase && z.fourthBase !== 'undefined') zoneObj.fourth_base = z.fourthBase;
                            zoneObj.fourth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            zoneObj.fourth_base_strength = z.fourthBaseStrength || 0;
                            zoneObj.fourth_base_spec_strength = z.fourthBaseSpecStrength ?? 1;
                            if (z.fourthBaseColorSource && z.fourthBaseColorSource !== 'undefined') zoneObj.fourth_base_color_source = z.fourthBaseColorSource;
                            zoneObj.fourth_base_blend_mode = z.fourthBaseBlendMode || 'noise';
                            zoneObj.fourth_base_noise_scale = Number(z.fourthBaseNoiseScale ?? z.fourthBaseFractalScale ?? 24);
                            zoneObj.fourth_base_scale = Math.max(0.01, Math.min(5, Number(z.fourthBaseScale) || 1));
                            if (z.fourthBasePattern) zoneObj.fourth_base_pattern = z.fourthBasePattern;
                            if (z.fourthBasePatternOpacity != null) zoneObj.fourth_base_pattern_opacity = (z.fourthBasePatternOpacity ?? 100) / 100;
                            if (z.fourthBasePatternScale != null) zoneObj.fourth_base_pattern_scale = Number(z.fourthBasePatternScale) || 1;
                            if (z.fourthBasePatternRotation != null) zoneObj.fourth_base_pattern_rotation = Number(z.fourthBasePatternRotation) || 0;
                            if (z.fourthBasePatternStrength != null) zoneObj.fourth_base_pattern_strength = Number(z.fourthBasePatternStrength) ?? 1;
                            if (z.fourthBasePatternInvert != null) zoneObj.fourth_base_pattern_invert = !!z.fourthBasePatternInvert;
                            if (z.fourthBasePatternHarden != null) zoneObj.fourth_base_pattern_harden = !!z.fourthBasePatternHarden;
                            if (z.fourthBasePatternOffsetX != null) zoneObj.fourth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetX ?? 0.5)));
                            if (z.fourthBasePatternOffsetY != null) zoneObj.fourth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fourthBasePatternOffsetY ?? 0.5)));
                        }
                        if ((z.fifthBase || z.fifthBaseColorSource) && (z.fifthBaseStrength || 0) > 0) {
                            const _fifColor = (z.fifthBaseColor || '#ffffff').toString();
                            const hex = _fifColor.length >= 7 ? _fifColor : '#ffffff';
                            if (z.fifthBase && z.fifthBase !== 'undefined') zoneObj.fifth_base = z.fifthBase;
                            zoneObj.fifth_base_color = [parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255];
                            zoneObj.fifth_base_strength = z.fifthBaseStrength || 0;
                            zoneObj.fifth_base_spec_strength = z.fifthBaseSpecStrength ?? 1;
                            if (z.fifthBaseColorSource && z.fifthBaseColorSource !== 'undefined') zoneObj.fifth_base_color_source = z.fifthBaseColorSource;
                            zoneObj.fifth_base_blend_mode = z.fifthBaseBlendMode || 'noise';
                            zoneObj.fifth_base_noise_scale = Number(z.fifthBaseNoiseScale ?? z.fifthBaseFractalScale ?? 24);
                            zoneObj.fifth_base_scale = Math.max(0.01, Math.min(5, Number(z.fifthBaseScale) || 1));
                            if (z.fifthBasePattern) zoneObj.fifth_base_pattern = z.fifthBasePattern;
                            if (z.fifthBasePatternOpacity != null) zoneObj.fifth_base_pattern_opacity = (z.fifthBasePatternOpacity ?? 100) / 100;
                            if (z.fifthBasePatternScale != null) zoneObj.fifth_base_pattern_scale = Number(z.fifthBasePatternScale) || 1;
                            if (z.fifthBasePatternRotation != null) zoneObj.fifth_base_pattern_rotation = Number(z.fifthBasePatternRotation) || 0;
                            if (z.fifthBasePatternStrength != null) zoneObj.fifth_base_pattern_strength = Number(z.fifthBasePatternStrength) ?? 1;
                            if (z.fifthBasePatternInvert != null) zoneObj.fifth_base_pattern_invert = !!z.fifthBasePatternInvert;
                            if (z.fifthBasePatternHarden != null) zoneObj.fifth_base_pattern_harden = !!z.fifthBasePatternHarden;
                            if (z.fifthBasePatternOffsetX != null) zoneObj.fifth_base_pattern_offset_x = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetX ?? 0.5)));
                            if (z.fifthBasePatternOffsetY != null) zoneObj.fifth_base_pattern_offset_y = Math.max(0, Math.min(1, Number(z.fifthBasePatternOffsetY ?? 0.5)));
                        }
                        const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);
                        if (!hasSpatialRefinement && z.regionMask && z.regionMask.some(v => v > 0)) { const pc = document.getElementById('paintCanvas'); if (pc) zoneObj.region_mask = encodeRegionMaskRLE(z.regionMask, pc.width, pc.height); }
                        if (hasSpatialRefinement) { const pc = document.getElementById('paintCanvas'); if (pc) zoneObj.spatial_mask = encodeRegionMaskRLE(z.spatialMask, pc.width, pc.height); }
                        return zoneObj;
                    });
                })();

            // Build request body
            const body = {
                paint_file: paintFile,
                zones: serverZones,
                seed: 51,
                preview_scale: 0.25,
            };

            // Include imported spec map if active (merge mode)
            if (importedSpecMapPath) {
                body.import_spec_map = importedSpecMapPath;
            }

            try {
                const resp = await fetch(ShokkerAPI.baseUrl + '/preview-render', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    signal: previewAbortController.signal,
                });

                // Check if this response is still current (not superseded)
                if (thisVersion !== previewVersion) return;

                const data = await resp.json();
                if (!data.success) {
                    updatePreviewStatus('error', data.error || 'Failed');
                    document.getElementById('previewSpinner').style.display = 'none';
                    previewIsRendering = false;
                    return;
                }

                // Update preview images (show both paint + spec simultaneously)
                const paintImg = document.getElementById('livePreviewImg');
                const specImg = document.getElementById('livePreviewSpecImg');
                paintImg.src = data.paint_preview;
                if (specImg) specImg.src = data.spec_preview;
                // Show both panes (paint full, spec inset) - reset expanded state
                document.getElementById('previewPaintPane').style.display = '';
                document.getElementById('previewSpecPane').style.display = '';
                document.getElementById('previewSpecPane').classList.remove('spec-expanded');
                specExpanded = false;
                document.getElementById('previewEmpty').style.display = 'none';
                document.getElementById('previewSpinner').style.display = 'none';

                // If server couldn't render spec map (bottom-right corner), show warning
                if (data.spec_warning) {
                    showToast(data.spec_warning, true);
                    const pane = document.getElementById('previewSpecPane');
                    if (pane) pane.title = data.spec_warning;
                } else {
                    const pane = document.getElementById('previewSpecPane');
                    if (pane) pane.title = 'Spec map (click to expand)';
                }

                // Update hash and status
                lastPreviewZoneHash = zoneHash;
                previewIsRendering = false;
                updatePreviewStatus('current', `${data.elapsed_ms}ms`);

                // Show/hide pattern indicator badge
                const patBadge = document.getElementById('patternActiveBadge');
                if (patBadge) {
                    const hasPattern = zones.some(z => z.pattern && z.pattern !== 'none');
                    patBadge.style.display = hasPattern ? '' : 'none';
                }

            } catch (err) {
                if (err.name === 'AbortError') return;  // Expected when superseded
                if (thisVersion !== previewVersion) return;
                previewIsRendering = false;
                updatePreviewStatus('error', 'Error');
                document.getElementById('previewSpinner').style.display = 'none';
                console.warn('[preview] render failed:', err);
            }
        }

        function updatePreviewStatus(state, text) {
            const badge = document.getElementById('previewStatus');
            if (!badge) return;
            badge.className = 'preview-status' + (state ? ' ' + state : '');
            badge.textContent = text || '';
        }

        function forcePreviewRefresh() {
            if (!splitViewActive) return;
            // Clear the hash so it re-renders even if nothing changed
            lastPreviewZoneHash = '';
            triggerPreviewRender();
            showToast('Refreshing preview...');
        }

        // ===== CANVAS ZOOM CONTROLS =====
        let currentZoom = 1;
        const ZOOM_STEPS = [0.1, 0.15, 0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];

        function canvasZoom(action) {
            const canvas = document.getElementById('paintCanvas');
            const inner = document.getElementById('canvasInner');
            const viewport = document.getElementById('canvasViewport');
            if (!canvas || !inner || !viewport || !canvas.width) return;

            if (action === 'fit') {
                // When split view is active, fit within the source pane (half width)
                const fitContainer = splitViewActive ? document.getElementById('splitSource') : viewport;
                const vw = (fitContainer || viewport).clientWidth - 20;
                const vh = (fitContainer || viewport).clientHeight - 20;
                const fitZoom = Math.min(vw / canvas.width, vh / canvas.height);
                currentZoom = Math.min(fitZoom, 1); // Don't upscale past 100%
            } else if (action === '100') {
                currentZoom = 1;
            } else if (action === 'in') {
                const curIdx = ZOOM_STEPS.findIndex(s => s >= currentZoom - 0.01);
                const nextIdx = Math.min(curIdx + 1, ZOOM_STEPS.length - 1);
                currentZoom = ZOOM_STEPS[nextIdx];
            } else if (action === 'out') {
                const curIdx = ZOOM_STEPS.findIndex(s => s >= currentZoom - 0.01);
                const nextIdx = Math.max((curIdx >= 0 ? curIdx : 0) - 1, 0);
                currentZoom = ZOOM_STEPS[nextIdx];
            }

            applyZoom();
        }

        function applyZoom() {
            const canvas = document.getElementById('paintCanvas');
            const regionCanvas = document.getElementById('regionCanvas');
            const inner = document.getElementById('canvasInner');
            const viewport = document.getElementById('canvasViewport');
            if (!canvas || !inner) return;

            const w = Math.round(canvas.width * currentZoom);
            const h = Math.round(canvas.height * currentZoom);
            canvas.style.width = w + 'px';
            canvas.style.height = h + 'px';
            if (regionCanvas) {
                regionCanvas.style.width = w + 'px';
                regionCanvas.style.height = h + 'px';
            }
            // rectSelectionBox is a CSS div - no resize needed, it positions itself via drawRectPreview()
            inner.style.width = w + 'px';
            inner.style.height = h + 'px';

            // Centering: when canvas is smaller than scroll container, center via margin
            const sc = typeof getScrollContainer === 'function' ? getScrollContainer() : viewport;
            if (sc) {
                if (h < sc.clientHeight) {
                    inner.style.marginTop = Math.max(0, Math.floor((sc.clientHeight - h) / 2)) + 'px';
                } else {
                    inner.style.marginTop = '0';
                }
                // Horizontal centering - use JS margin instead of CSS auto
                // (margin:auto + overflow:auto = left side unreachable when content overflows)
                if (w < sc.clientWidth) {
                    inner.style.marginLeft = Math.max(0, Math.floor((sc.clientWidth - w) / 2)) + 'px';
                } else {
                    inner.style.marginLeft = '0';
                }
            }

            document.getElementById('zoomLevel').textContent = Math.round(currentZoom * 100) + '%';

            // Refresh cursor after zoom level changes
            if (viewport && !spaceHeld && !isPanning) {
                viewport.style.cursor = '';
                // Re-apply the mode cursor since zoom level may affect it
                const cvs = document.getElementById('paintCanvas');
                if (cvs && canvasMode === 'eyedropper') {
                    cvs.style.cursor = 'crosshair';
                }
            }
        }

        // ===== CANVAS PAN & ZOOM =====
        let isPanning = false;
        let panStartX = 0, panStartY = 0;
        let panScrollStartX = 0, panScrollStartY = 0;
        let spaceHeld = false;

        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.repeat && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
                spaceHeld = true;
                const viewport = document.getElementById('canvasViewport');
                if (viewport) viewport.style.cursor = 'grab';
                e.preventDefault();
            }
        });
        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space') {
                spaceHeld = false;
                if (!isPanning) {
                    const viewport = document.getElementById('canvasViewport');
                    if (viewport) viewport.style.cursor = '';
                }
            }
        });

        document.addEventListener('DOMContentLoaded', () => {
            const viewport = document.getElementById('canvasViewport');
            if (!viewport) return;

            // If paint is already loaded (e.g. restored state or same-session), ensure canvas has tool handlers
            const canvas = document.getElementById('paintCanvas');
            if (canvas && canvas.width && canvas.height && typeof paintImageData !== 'undefined' && paintImageData) {
                setupCanvasHandlers(canvas);
            }

            // Drag-and-drop paint file loading
            const centerPanel = viewport.closest('.center-panel') || viewport;
            ['dragenter', 'dragover'].forEach(evt => {
                centerPanel.addEventListener(evt, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    centerPanel.style.outline = '2px dashed var(--accent)';
                    centerPanel.style.outlineOffset = '-4px';
                });
            });
            ['dragleave', 'drop'].forEach(evt => {
                centerPanel.addEventListener(evt, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    centerPanel.style.outline = '';
                    centerPanel.style.outlineOffset = '';
                });
            });
            centerPanel.addEventListener('drop', (e) => {
                const file = e.dataTransfer?.files?.[0];
                if (!file) return;
                const name = file.name.toLowerCase();
                if (name.endsWith('.tga') || name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.bmp')) {
                    // Simulate the browsePaintFile flow by creating a synthetic input
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    const fakeInput = document.createElement('input');
                    fakeInput.type = 'file';
                    fakeInput.files = dt.files;
                    browsePaintFile(fakeInput);
                    showToast(`Dropped: ${file.name}`);
                } else {
                    showToast('Drop a paint file (.tga, .png, .jpg)', true);
                }
            });

            // Mouse wheel = ALWAYS zoom (scroll up = zoom in, scroll down = zoom out)
            // Zooms toward the mouse cursor position for intuitive navigation
            viewport.addEventListener('wheel', (e) => {
                if (!document.getElementById('paintCanvas')?.width) return;

                // If Manual Placement is active, scroll adjusts pattern scale instead of zooming
                if (typeof placementLayer !== 'undefined' && placementLayer === 'pattern' &&
                    typeof selectedZoneIndex !== 'undefined' && zones && zones[selectedZoneIndex] &&
                    zones[selectedZoneIndex].patternPlacement === 'manual') {
                    e.preventDefault();
                    const z = zones[selectedZoneIndex];
                    const delta = e.deltaY > 0 ? -0.05 : 0.05;
                    z.scale = Math.max(0.1, Math.min(4.0, (z.scale || 1.0) + delta));
                    if (typeof renderZones === 'function') renderZones();
                    if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
                    return;
                }

                e.preventDefault();

                const oldZoom = currentZoom;
                if (e.deltaY < 0) canvasZoom('in');
                else canvasZoom('out');
                const newZoom = currentZoom;

                // Zoom toward cursor: adjust scroll so the point under the cursor stays fixed
                if (oldZoom !== newZoom) {
                    const sc = getScrollContainer();
                    const rect = sc.getBoundingClientRect();
                    // Mouse position relative to scroll container top-left
                    const mx = e.clientX - rect.left;
                    const my = e.clientY - rect.top;
                    // Point in content that's under the cursor (in un-zoomed coords)
                    const contentX = (sc.scrollLeft + mx) / oldZoom;
                    const contentY = (sc.scrollTop + my) / oldZoom;
                    // After zoom, that same content point should still be under the cursor
                    sc.scrollLeft = contentX * newZoom - mx;
                    sc.scrollTop = contentY * newZoom - my;
                }
            }, { passive: false });

            // ===== PAN SYSTEM =====
            // When zoomed in: left-click DRAG = pan, left-click (no drag) = tool action (eyedropper etc.)
            // Middle-click drag = pan (always)
            // Right-click drag = pan (always when zoomed)
            // Space + left-click = pan (always)
            //
            // The key insight: we intercept mousedown on the VIEWPORT (parent of canvas),
            // and decide whether it's a pan or a tool action based on whether the user drags.
            let pendingPan = false;
            let pendingPanEvent = null;
            let panConsumed = false;  // True if this mousedown became a pan (suppress canvas tool action)

            // Disable right-click context menu on canvas for right-drag panning
            viewport.addEventListener('contextmenu', (e) => {
                e.preventDefault();
            });

            // Capture-phase: run canvas tool logic here so it always runs (event may never reach canvas).
            // 1) Ensure handlers exist. 2) Eyedropper fallback first so Pick + Add always work.
            // 3) Run canvas.onmousedown(e) for Wand/Spatial/Brush/etc. 4) Stop propagation so no double-run.
            viewport.addEventListener('mousedown', (e) => {
                if (e.target.id !== 'paintCanvas' || e.button !== 0) return;
                const canvas = document.getElementById('paintCanvas');
                if (!canvas || !canvas.width || typeof paintImageData === 'undefined' || !paintImageData) return;
                if (typeof canvasMode === 'undefined') return;
                setupCanvasHandlers(canvas);
                // Eyedropper: set lastEyedropperColor first so Pick + Add work even if handler throws
                if (canvasMode === 'eyedropper') {
                    const rect = canvas.getBoundingClientRect();
                    const scaleX = canvas.width / rect.width;
                    const scaleY = canvas.height / rect.height;
                    const x = Math.floor((e.clientX - rect.left) * scaleX);
                    const y = Math.floor((e.clientY - rect.top) * scaleY);
                    if (x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) {
                        const idx = (y * canvas.width + x) * 4;
                        const px = { r: paintImageData.data[idx], g: paintImageData.data[idx + 1], b: paintImageData.data[idx + 2] };
                        lastEyedropperColor = px;
                        const hex = '#' + [px.r, px.g, px.b].map(c => c.toString(16).padStart(2, '0')).join('');
                        const swatch = document.getElementById('eyedropperSwatch');
                        if (swatch) swatch.style.background = hex;
                        const rgbEl = document.getElementById('eyedropperRGB');
                        if (rgbEl) rgbEl.textContent = `RGB: (${px.r}, ${px.g}, ${px.b})`;
                        const hexEl = document.getElementById('eyedropperHex');
                        if (hexEl) hexEl.textContent = hex.toUpperCase();
                        const info = document.getElementById('eyedropperInfo');
                        if (info) info.style.display = 'block';
                        if (typeof updateEyedropperZoneSelect === 'function') updateEyedropperZoneSelect();
                    }
                }
                // Run full tool handler (wand, brush, spatial, rect, lasso, erase)
                try {
                    if (canvas.onmousedown && typeof canvas.onmousedown === 'function') {
                        canvas.onmousedown(e);
                    }
                } catch (err) {
                    console.error('[Canvas] tool handler error:', err);
                }
                e.stopPropagation();
                e.preventDefault();
            }, true);

            viewport.addEventListener('mousedown', (e) => {
                panConsumed = false;

                // Middle button (button 1) always pans immediately
                if (e.button === 1) {
                    e.preventDefault();
                    startPan(e, viewport);
                    panConsumed = true;
                    return;
                }
                // Right button (button 2) pans when zoomed
                if (e.button === 2 && canvasOverflows()) {
                    e.preventDefault();
                    startPan(e, viewport);
                    panConsumed = true;
                    return;
                }
                // Space + left-click pans immediately
                if (spaceHeld && e.button === 0) {
                    e.preventDefault();
                    startPan(e, viewport);
                    panConsumed = true;
                    return;
                }
                // Left-click when zoomed in: DEFER - could be pan (drag) or tool action (click)
                // Short click = tool action (eyedropper, brush dot, etc.)
                // Drag past threshold = pan the view
                // BUT: if user is in a drag-based drawing tool or placement mode, DON'T hijack for pan -
                // they need left-drag for rect, gradient, brush, erase strokes, or place-on-map drag.
                // Pan is still available via space+drag, middle-click, or right-click.
                const placementActive = typeof placementLayer !== 'undefined' && placementLayer !== 'none';
                const drawToolActive = ['brush', 'rect', 'erase', 'spatial-include', 'spatial-exclude', 'lasso'].includes(canvasMode) || placementActive;
                if (e.button === 0 && canvasOverflows() && !drawToolActive) {
                    pendingPan = true;
                    pendingPanEvent = e;
                    return;
                }
            });

            document.addEventListener('mousemove', (e) => {
                // Check if pending left-click should become a pan (drag threshold = 5px)
                if (pendingPan && pendingPanEvent) {
                    const dx = e.clientX - pendingPanEvent.clientX;
                    const dy = e.clientY - pendingPanEvent.clientY;
                    if (dx * dx + dy * dy > 25) {  // 5px threshold
                        startPan(pendingPanEvent, viewport);
                        panConsumed = true;
                        pendingPan = false;
                        pendingPanEvent = null;
                        // Cancel any active drawing operation so pan takes over cleanly
                        isDrawing = false;
                        rectStart = null;
                    }
                }
                if (!isPanning) return;
                const sc = getScrollContainer();
                if (!sc) return;
                sc.scrollLeft = panScrollStartX - (e.clientX - panStartX);
                sc.scrollTop = panScrollStartY - (e.clientY - panStartY);
            });

            document.addEventListener('mouseup', (e) => {
                // If pending pan never started (quick click), just clean up - tool action already happened
                if (pendingPan) {
                    pendingPan = false;
                    pendingPanEvent = null;
                }
                if (isPanning) {
                    isPanning = false;
                    panConsumed = true;  // Keep flag until next mousedown
                    const vp = document.getElementById('canvasViewport');
                    const cvs = document.getElementById('paintCanvas');
                    if (vp) {
                        if (spaceHeld) {
                            vp.style.cursor = 'grab';
                            if (cvs) cvs.style.cursor = 'grab';
                        } else {
                            vp.style.cursor = '';
                            // Restore canvas cursor: placement mode overrides tool cursor
                            if (cvs) {
                                if (typeof placementLayer !== 'undefined' && placementLayer !== 'none') cvs.style.cursor = 'grab';
                                else if (canvasMode === 'eyedropper') cvs.style.cursor = 'crosshair';
                                else if (canvasMode === 'wand' || canvasMode === 'selectall' || canvasMode === 'edge') cvs.style.cursor = 'crosshair';
                                else if (['brush', 'erase', 'spatial-include', 'spatial-exclude'].includes(canvasMode)) cvs.style.cursor = 'none';
                                else cvs.style.cursor = 'cell';
                            }
                        }
                    }
                }
            });
        });

        // Returns the element that actually scrolls when the canvas is zoomed.
        // This is the split-source pane (closest scrollable ancestor of canvasInner).
        function getScrollContainer() {
            return document.getElementById('splitSource') || document.getElementById('canvasViewport');
        }

        function startPan(e, viewport) {
            const sc = getScrollContainer();
            isPanning = true;
            panStartX = e.clientX;
            panStartY = e.clientY;
            panScrollStartX = sc.scrollLeft;
            panScrollStartY = sc.scrollTop;
            viewport.style.cursor = 'grabbing';
            // Also set canvas cursor so it overrides the tool-specific cursor during pan
            const canvas = document.getElementById('paintCanvas');
            if (canvas) canvas.style.cursor = 'grabbing';
            console.log('[PAN] Started pan - scrollStart:', panScrollStartX, panScrollStartY,
                'scrollMax:', sc.scrollWidth - sc.clientWidth, sc.scrollHeight - sc.clientHeight,
                'containerSize:', sc.clientWidth, 'x', sc.clientHeight,
                'scrollSize:', sc.scrollWidth, 'x', sc.scrollHeight,
                'container:', sc.id);
        }

        // Returns true if the zoomed canvas is bigger than the scroll container (scroll needed)
        function canvasOverflows() {
            const sc = getScrollContainer();
            const canvas = document.getElementById('paintCanvas');
            if (!sc || !canvas || !canvas.width) return false;
            const w = Math.round(canvas.width * currentZoom);
            const h = Math.round(canvas.height * currentZoom);
            return w > sc.clientWidth || h > sc.clientHeight;
        }

